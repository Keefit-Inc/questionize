"""Turn a scanned answer-and-explanation section of a prep book you own into a private E1 dataset.

    python -m questionize.import_scan ~/private/og.pdf --pages 520-640 --book "Official Guide" \\
        --out ~/private/official-cr-v1.json [--ocr apple|tesseract|none] [--dataset official-cr-v1]

Each page is read by the primary (vision) model into the question, the book's key letter, the book's
explanation and a trap tag per option. The same page is read again by an on-device OCR engine (Apple's
Vision framework on a Mac, or Tesseract), and the model's transcription is checked against it word by
word: a page where they disagree, or where the key letter in the OCR text differs, is flagged for a
person to look at. E1 skips flagged items until the flag is cleared in the JSON.

Everything this writes quotes the book. The output must live outside the repository (it refuses a path
inside it), and the scan never leaves this machine except as page images sent to the model.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import difflib
import io
import json
import logging
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from .llm import StructuredLLM
from .schemas import Choice, Label, TrapType

REPO = Path(__file__).resolve().parents[2]
AGREEMENT_FLOOR = 0.97
RENDER_DPI = 200

SCAN_SYSTEM = """You transcribe one page of a GMAT/LSAT prep book's answer-explanation section.

Copy the question exactly as printed: passage, question stem and every answer option, word for word, \
keeping the book's punctuation. Do not correct, shorten or paraphrase. Leave out page headers, footers, \
running titles and question-type banners.

Then copy the book's explanation exactly, and record the letter the book gives as the correct answer. \
For every option, give the trap it sets (or "correct") and a short reason in your own words (at most 15 \
words, never quoting the book).

If the page holds no question (a title page, a chapter introduction, an answer grid), set kind to \
"not_a_question". If the question or its explanation runs onto the next page, set continues_on_next_page; \
if this page begins in the middle of the previous page's question, set starts_mid_question."""


class OptionTrap(BaseModel):
    label: Label
    trap: TrapType
    why: str = Field(..., max_length=160)


class ScanPage(BaseModel):
    kind: Literal["question", "not_a_question"]
    number: str = ""
    family: Literal["CR", "RC", "other"] = "other"
    subtype: str = Field("", description="weaken, strengthen, assumption, flaw, evaluate, inference (CR); main_idea, detail, inference, author_purpose, structure (RC)")
    passage: str = ""
    stem: str = ""
    choices: list[Choice] = []
    answer_key: Label | None = None
    official_explanation: str = ""
    option_traps: list[OptionTrap] = []
    continues_on_next_page: bool = False
    starts_mid_question: bool = False


# ------------------------------------------------------------------ pages and OCR


def parse_pages(spec: str) -> list[int]:
    """'520-525,530' -> [520, ..., 525, 530] (1-based, as printed by a PDF viewer)."""
    pages: list[int] = []
    for part in spec.split(","):
        a, _, b = part.strip().partition("-")
        pages.extend(range(int(a), int(b or a) + 1))
    return pages


def render_pages(pdf: Path, pages: list[int], dpi: int = RENDER_DPI) -> dict[int, bytes]:
    import pypdfium2 as pdfium  # research extra (requirements-research.txt)

    doc = pdfium.PdfDocument(str(pdf))
    out: dict[int, bytes] = {}
    for n in pages:
        if 1 <= n <= len(doc):
            buf = io.BytesIO()
            doc[n - 1].render(scale=dpi / 72).to_pil().convert("L").save(buf, format="PNG", optimize=True)
            out[n] = buf.getvalue()
    return out


def apple_ocr(png: bytes) -> str:
    """macOS Vision framework (the engine behind Live Text), accurate mode, on device."""
    from ocrmac import ocrmac  # pip install ocrmac (macOS only)

    with tempfile.NamedTemporaryFile(suffix=".png") as f:
        f.write(png)
        f.flush()
        rows = ocrmac.OCR(f.name, recognition_level="accurate", language_preference=["en-US"]).recognize()
    # Vision returns lines bottom-up in normalized coordinates; sort top to bottom, then left to right.
    rows.sort(key=lambda r: (-round(r[2][1] + r[2][3], 2), r[2][0]))
    return "\n".join(r[0] for r in rows)


def tesseract_ocr(png: bytes) -> str:
    if not shutil.which("tesseract"):
        raise RuntimeError("tesseract is not installed (brew install tesseract)")
    return subprocess.run(["tesseract", "stdin", "stdout", "-l", "eng"], input=png, capture_output=True, check=True).stdout.decode()


OCR_ENGINES: dict[str, Callable[[bytes], str]] = {"apple": apple_ocr, "tesseract": tesseract_ocr}


# ------------------------------------------------------------------ checks


def words(text: str) -> list[str]:
    # Hyphenation at line ends and curly quotes are the usual OCR-vs-model differences that mean nothing.
    text = text.replace("-\n", "").replace("’", "'").replace("“", '"').replace("”", '"')
    return re.findall(r"[a-z0-9']+", text.lower())


def agreement(transcribed: str, ocr: str) -> float:
    """Share of the model's words that line up, in order, with the OCR text. Invented or dropped text lowers it."""
    mine, theirs = words(transcribed), words(ocr)
    if not mine:
        return 0.0
    matcher = difflib.SequenceMatcher(None, mine, theirs, autojunk=False)
    return round(sum(b.size for b in matcher.get_matching_blocks()) / len(mine), 4)


KEY_PATTERN = re.compile(r"(?:correct answer is|the answer is|answer:)\s*\(?([A-E])\)?", re.IGNORECASE)


def ocr_key(ocr: str) -> str | None:
    found = KEY_PATTERN.findall(ocr)
    return found[-1].upper() if found else None


def question_text(p: ScanPage) -> str:
    return "\n".join([p.passage, p.stem, *(c.text for c in p.choices)])


def check(page: ScanPage, ocr: str | None) -> tuple[list[str], float | None]:
    flags: list[str] = []
    if not page.answer_key:
        flags.append("no_key")
    if sorted(c.label for c in page.choices) != ["A", "B", "C", "D", "E"]:
        flags.append("choices_incomplete")
    score = None
    if ocr is not None:
        score = agreement(question_text(page), ocr)
        if score < AGREEMENT_FLOOR:
            flags.append("transcription_mismatch")
        printed = ocr_key(ocr)
        if printed and page.answer_key and printed != page.answer_key:
            flags.append("key_mismatch")
    return flags, score


# ------------------------------------------------------------------ run


def data_url(png: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png).decode()


async def read_pages(model: StructuredLLM, images: dict[int, bytes], concurrency: int = 4) -> dict[int, ScanPage]:
    gate = asyncio.Semaphore(concurrency)
    order = sorted(images)

    async def one(n: int, with_next: bool = False) -> ScanPage | None:
        shots = [data_url(images[n])] + ([data_url(images[n + 1])] if with_next and n + 1 in images else [])
        note = "The question continues on the second image; read both as one page." if len(shots) > 1 else "Read this page."
        async with gate:
            started = time.monotonic()
            try:
                page = await model.complete(SCAN_SYSTEM, note, ScanPage, temperature=0.0, images=shots)
            except Exception as e:  # noqa: BLE001 — one unreadable page should not stop the book
                print(f"[scan] page {n}: failed after {time.monotonic() - started:.0f}s: {e}", file=sys.stderr)
                return None
            what = f"question {page.number or '?'}" if page.kind == "question" else "no question"
            print(f"[scan] page {n}{'+' + str(n + 1) if len(shots) > 1 else ''}: {what} ({time.monotonic() - started:.0f}s)", file=sys.stderr)
            return page

    first = dict(zip(order, await asyncio.gather(*(one(n) for n in order)), strict=True))
    out: dict[int, ScanPage] = {}
    for n in order:
        page = first[n]
        if page is None or page.kind != "question" or page.starts_mid_question:
            continue
        if page.continues_on_next_page and n + 1 in images:
            page = await one(n, with_next=True) or page
        out[n] = page
    return out


def build_dataset(
    pages: dict[int, ScanPage], images: dict[int, bytes], ocr: Callable[[bytes], str] | None, dataset: str, book: str
) -> dict:
    items = []
    for n, page in sorted(pages.items()):
        text = None
        if ocr is not None:
            text = ocr(images[n]) + ("\n" + ocr(images[n + 1]) if page.continues_on_next_page and n + 1 in images else "")
        flags, score = check(page, text)
        items.append(
            {
                "entry_id": n,
                "book": book,
                "page": str(n),
                "number": page.number,
                "family": page.family,
                "subtype": page.subtype,
                "answer_key": page.answer_key,
                "key_verdict": "book",
                "question": {"passage": page.passage, "stem": page.stem, "choices": [c.model_dump() for c in page.choices]},
                "official_explanation": page.official_explanation,
                "option_traps": [t.model_dump() for t in page.option_traps],
                "ocr_agreement": score,
                "flags": flags,
                "flagged": bool(flags),
            }
        )
    return {"dataset": dataset, "source": "scan", "exported_at": datetime.now(timezone.utc).isoformat(), "items": items}


def inside_repo(path: Path) -> bool:
    try:
        path.resolve().relative_to(REPO)
        return True
    except ValueError:
        return False


def main(argv: list[str] | None = None) -> None:
    from .config import load_settings
    from .llm import make_llm

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--pages", required=True, help="e.g. 520-640 or 520-560,600-640")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--book", default="")
    ap.add_argument("--dataset", default="official-cr-v1")
    ap.add_argument("--ocr", choices=["apple", "tesseract", "none"], default="apple" if sys.platform == "darwin" else "tesseract")
    args = ap.parse_args(argv)
    if inside_repo(args.out):
        sys.exit("Refusing to write book text inside the repository; choose a path outside it.")

    # Retries and schema fallbacks are logged as warnings; show them while a long book runs.
    logging.basicConfig(level=logging.WARNING, format="[%(name)s] %(message)s")
    settings = load_settings()
    model = make_llm(settings.primary, timeout=settings.timeout_seconds)
    images = render_pages(args.pdf, parse_pages(args.pages))
    print(f"[scan] {len(images)} pages rendered; reading them with {model.model} (4 at a time)…", file=sys.stderr)
    pages = asyncio.run(read_pages(model, images))
    data = build_dataset(pages, images, None if args.ocr == "none" else OCR_ENGINES[args.ocr], args.dataset, args.book)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    flagged = [i for i in data["items"] if i["flagged"]]
    print(f"{len(images)} pages → {len(data['items'])} questions, {len(flagged)} flagged → {args.out}")
    for i in flagged:
        print(f"  page {i['page']} #{i['number']}: {', '.join(i['flags'])} (agreement {i['ocr_agreement']})")
    if flagged:
        print("Fix each flagged item in the JSON against the page, then set \"flagged\": false.")


if __name__ == "__main__":
    main()
