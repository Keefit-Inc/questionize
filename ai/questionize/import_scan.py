"""Turn a scanned answer-and-explanation section of a prep book you own into a private E1 dataset.

    python -m questionize.import_scan ~/private/og.pdf --pages 1-120 --book "Official Guide" \\
        --out ~/private/official-cr-v1.json [--ocr apple|tesseract] [--dataset official-cr-v1]

OCR first, model second. An on-device engine (Apple's Vision framework on a Mac, Tesseract elsewhere)
reads every page into numbered lines; pages with no answer options are skipped without a model call.
The primary model then sees only the numbered lines and answers with line ranges (which lines are the
passage, the stem, each option, the explanation), the key letter, the sub-type and a trap tag per option.
It never retypes the book, so the text is exactly what was printed, the calls are short and cheap, and
no page image leaves the machine. Items with a missing key, a missing option, an empty field, or a key
that differs from the one printed on the page are flagged; E1 skips them until the flag is cleared.

Everything this writes quotes the book. The output must live outside the repository (it refuses a path
inside it).
"""

from __future__ import annotations

import argparse
import asyncio
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
from .schemas import Label, TrapType

REPO = Path(__file__).resolve().parents[2]
RENDER_DPI = 200
MARKER = re.compile(r"^\(?([A-E])[).]?\s+\S")

LAYOUT_SYSTEM = """You lay out one OCR'd page of a GMAT/LSAT prep book's answer-explanation section.

The page is given as numbered lines. Do not copy any text: answer with line numbers only. Give the first \
and last line of the passage (the argument), of the question stem, of each answer option A-E, and of the \
book's explanation. Leave out page headers, footers, running titles and question-type banners. Record the \
letter the book gives as the correct answer, the question number, and the sub-type.

For every option, give the trap it sets (or "correct") and a short reason in your own words (at most 15 \
words, never quoting the book).

If the page holds no question (a title page, an introduction, an answer grid), set kind to "not_a_question". \
If the explanation runs past the last line shown, set continues_on_next_page. If the page begins in the \
middle of the previous page's question, set starts_mid_question."""


class Span(BaseModel):
    first: int
    last: int


class ChoiceSpan(Span):
    label: Label


class OptionTrap(BaseModel):
    label: Label
    trap: TrapType
    why: str = Field(..., max_length=160)


class ScanLayout(BaseModel):
    kind: Literal["question", "not_a_question"]
    number: str = ""
    family: Literal["CR", "RC", "other"] = "other"
    subtype: str = Field("", description="weaken, strengthen, assumption, flaw, evaluate, inference (CR); main_idea, detail, inference, author_purpose, structure (RC)")
    passage: Span | None = None
    stem: Span | None = None
    choices: list[ChoiceSpan] = []
    explanation: Span | None = None
    answer_key: Label | None = None
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


def apple_ocr(png: bytes) -> list[str]:
    """macOS Vision framework (the engine behind Live Text), accurate mode, on device."""
    from ocrmac import ocrmac  # pip install ocrmac (macOS only)

    with tempfile.NamedTemporaryFile(suffix=".png") as f:
        f.write(png)
        f.flush()
        rows = ocrmac.OCR(f.name, recognition_level="accurate", language_preference=["en-US"]).recognize()
    # Vision returns lines bottom-up in normalized coordinates; sort top to bottom, then left to right.
    rows.sort(key=lambda r: (-round(r[2][1] + r[2][3], 2), r[2][0]))
    return [r[0] for r in rows]


def tesseract_ocr(png: bytes) -> list[str]:
    if not shutil.which("tesseract"):
        raise RuntimeError("tesseract is not installed (brew install tesseract)")
    out = subprocess.run(["tesseract", "stdin", "stdout", "-l", "eng"], input=png, capture_output=True, check=True).stdout.decode()
    return [line for line in out.splitlines() if line.strip()]


OCR_ENGINES: dict[str, Callable[[bytes], list[str]]] = {"apple": apple_ocr, "tesseract": tesseract_ocr}


# ------------------------------------------------------------------ assembling text


def has_options(lines: list[str]) -> bool:
    return len({m.group(1) for line in lines if (m := MARKER.match(line.strip()))}) >= 3


def join_lines(lines: list[str]) -> str:
    """Rejoin OCR lines into running text, undoing end-of-line hyphenation."""
    text = ""
    for line in (line.strip() for line in lines):
        if not line:
            continue
        if text.endswith("-") and line[:1].islower():
            text = text[:-1] + line
        else:
            text = f"{text} {line}" if text else line
    return text


def take(lines: list[str], span: Span | None) -> str | None:
    """Lines first..last (1-based, inclusive), or None when the span is missing or out of range."""
    if span is None or not 1 <= span.first <= span.last <= len(lines):
        return None
    return join_lines(lines[span.first - 1 : span.last])


KEY_PATTERN = re.compile(r"(?:correct answer is|the answer is|answer:)\s*\(?([A-E])\)?", re.IGNORECASE)


def printed_key(text: str) -> str | None:
    found = KEY_PATTERN.findall(text)
    return found[-1].upper() if found else None


def assemble(layout: ScanLayout, lines: list[str]) -> tuple[dict, list[str]]:
    flags: list[str] = []
    passage, stem, explanation = take(lines, layout.passage), take(lines, layout.stem), take(lines, layout.explanation)
    choices = []
    for c in sorted(layout.choices, key=lambda c: c.label):
        text = take(lines, c)
        if text is None:
            continue
        choices.append({"label": c.label, "text": re.sub(r"^\(?[A-E]\)?[.)]?\s+", "", text)})
    if not passage or not stem:
        flags.append("missing_text")
    if [c["label"] for c in choices] != ["A", "B", "C", "D", "E"]:
        flags.append("choices_incomplete")
    if not layout.answer_key:
        flags.append("no_key")
    printed = printed_key("\n".join(lines))
    if printed and layout.answer_key and printed != layout.answer_key:
        flags.append("key_mismatch")
    question = {"passage": passage or "", "stem": stem or "", "choices": choices}
    return {"question": question, "official_explanation": explanation or ""}, flags


# ------------------------------------------------------------------ run


def numbered(lines: list[str]) -> str:
    return "\n".join(f"[{i}] {line}" for i, line in enumerate(lines, 1))


async def lay_out(model: StructuredLLM, ocr: dict[int, list[str]], concurrency: int = 4) -> dict[int, tuple[ScanLayout, list[str]]]:
    """A layout and the lines it refers to, for each page that starts a question."""
    gate = asyncio.Semaphore(concurrency)
    order = sorted(ocr)

    async def one(n: int, lines: list[str], label: str) -> ScanLayout | None:
        async with gate:
            started = time.monotonic()
            try:
                layout = await model.complete(LAYOUT_SYSTEM, numbered(lines), ScanLayout, temperature=0.0)
            except Exception as e:  # noqa: BLE001 — one unreadable page should not stop the book
                print(f"[scan] page {label}: failed after {time.monotonic() - started:.0f}s: {e}", file=sys.stderr)
                return None
            what = f"question {layout.number or '?'}" if layout.kind == "question" else "no question"
            print(f"[scan] page {label}: {what} ({time.monotonic() - started:.0f}s)", file=sys.stderr)
            return layout

    candidates = [n for n in order if has_options(ocr[n])]
    for n in order:
        if n not in candidates:
            print(f"[scan] page {n}: no options found by OCR, skipped", file=sys.stderr)
    first = dict(zip(candidates, await asyncio.gather(*(one(n, ocr[n], str(n)) for n in candidates)), strict=True))
    out: dict[int, tuple[ScanLayout, list[str]]] = {}
    for n in candidates:
        layout, lines = first[n], ocr[n]
        if layout is None or layout.kind != "question" or layout.starts_mid_question:
            continue
        if layout.continues_on_next_page and n + 1 in ocr:
            lines = ocr[n] + ocr[n + 1]
            layout = await one(n, lines, f"{n}+{n + 1}") or layout
        out[n] = (layout, lines)
    return out


def build_dataset(layouts: dict[int, tuple[ScanLayout, list[str]]], dataset: str, book: str, engine: str) -> dict:
    items = []
    for n, (layout, lines) in sorted(layouts.items()):
        fields, flags = assemble(layout, lines)
        items.append(
            {
                "entry_id": n,
                "book": book,
                "page": str(n),
                "number": layout.number,
                "family": layout.family,
                "subtype": layout.subtype,
                "answer_key": layout.answer_key,
                "key_verdict": "book",
                **fields,
                "option_traps": [t.model_dump() for t in layout.option_traps],
                "flags": flags,
                "flagged": bool(flags),
            }
        )
    return {"dataset": dataset, "source": f"scan+{engine}", "exported_at": datetime.now(timezone.utc).isoformat(), "items": items}


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
    ap.add_argument("--ocr-only", action="store_true", help="run OCR and report what it found, without any model call")
    ap.add_argument("--ocr", choices=sorted(OCR_ENGINES), default="apple" if sys.platform == "darwin" else "tesseract")
    args = ap.parse_args(argv)
    if inside_repo(args.out):
        sys.exit("Refusing to write book text inside the repository; choose a path outside it.")

    if args.ocr_only:
        for n, png in render_pages(args.pdf, parse_pages(args.pages)).items():
            started = time.monotonic()
            lines = OCR_ENGINES[args.ocr](png)
            found = "options found" if has_options(lines) else "no options"
            print(f"page {n}: {len(lines)} lines, {found}, key {printed_key(chr(10).join(lines)) or '-'} ({time.monotonic() - started:.1f}s)")
        return

    # Retries and schema fallbacks are logged as warnings; show them while a long book runs.
    logging.basicConfig(level=logging.WARNING, format="[%(name)s] %(message)s")
    settings = load_settings()
    model = make_llm(settings.primary, timeout=settings.timeout_seconds)
    images = render_pages(args.pdf, parse_pages(args.pages))
    started = time.monotonic()
    ocr = {n: OCR_ENGINES[args.ocr](png) for n, png in images.items()}
    print(f"[scan] {len(ocr)} pages read by {args.ocr} OCR in {time.monotonic() - started:.0f}s; laying them out with {model.model}…", file=sys.stderr)
    data = build_dataset(asyncio.run(lay_out(model, ocr)), args.dataset, args.book, args.ocr)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    flagged = [i for i in data["items"] if i["flagged"]]
    print(f"{len(images)} pages → {len(data['items'])} questions, {len(flagged)} flagged → {args.out}")
    for i in flagged:
        print(f"  page {i['page']} #{i['number']}: {', '.join(i['flags'])}")
    if flagged:
        print("Fix each flagged item in the JSON against the page, then set \"flagged\": false.")


if __name__ == "__main__":
    main()
