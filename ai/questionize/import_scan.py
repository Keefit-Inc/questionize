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
import difflib
import io
import itertools
import json
import logging
import os
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

from pydantic import BaseModel, Field, model_validator

from .llm import StructuredLLM
from .schemas import Label, TrapType

REPO = Path(__file__).resolve().parents[2]
RENDER_DPI = 200
AGREEMENT_FLOOR = 0.97
STOP_AFTER_FAILURES = 3
# Line spacing inside a paragraph is about 1.0x; between options about 1.2x; between paragraphs about 1.5x.
PARAGRAPH_GAP = 1.35
# "(A) text", "A. text", "A) text", or the letter alone on its line with the text beside it in another column.
MARKER = re.compile(r"^[(\[]?([A-E])\s*[).:\]]?(?:\s+\S|$)")

STRUCTURE_SYSTEM = """You structure the OCR text of one page from a GMAT/LSAT prep book's answer-explanation section.

Such a page usually holds: a question number and the passage (the argument); the question stem; answer \
options (A) to (E); a reasoning-type banner such as "Argument Construction"; the book's explanation, often \
labelled "Situation" and "Reasoning", then one paragraph per option marked A to E; and "The correct answer \
is X." Chapter titles, introductions, running headers and page numbers are not part of a question.

Copy every field from the OCR text exactly as printed. Join lines broken by hyphenation and drop stray OCR \
marks, but never reword, shorten, summarize or correct the book. If the page holds no question, set kind to \
"not_a_question" and leave the rest empty. If the explanation is cut off at the end of the text, set \
continues_on_next_page.

Finally, in your own words (never quoting the book), give the question's sub-type and, for each option, \
the trap it sets or "correct"."""


class TextChoice(BaseModel):
    label: Label
    text: str


class OptionTrap(BaseModel):
    label: Label
    trap: TrapType


class PageStructure(BaseModel):
    kind: Literal["question", "not_a_question"]
    number: str = ""
    passage: str = ""
    stem: str = ""
    options: list[TextChoice] = []
    answer_key: Label | None = None
    explanation: str = Field("", description="The book's explanation before the per-option paragraphs (Situation, Reasoning)")
    option_explanations: list[TextChoice] = Field([], description="The book's paragraph on each option, A to E")
    subtype: str = Field("", description="weaken, strengthen, assumption, flaw, evaluate, inference, explain, structure")
    option_traps: list[OptionTrap] = []
    continues_on_next_page: bool = False

    @model_validator(mode="after")
    def _complete_question(self) -> PageStructure:
        # Every field defaults so a page without a question can be short; a question must be complete,
        # and a failure here goes back to the model as a correction request.
        if self.kind == "question":
            missing = [name for name in ("passage", "stem") if not getattr(self, name).strip()]
            if sorted(o.label for o in self.options) != ["A", "B", "C", "D", "E"]:
                missing.append("options (one for each of A-E)")
            if self.answer_key is None:
                missing.append("answer_key")
            if missing:
                raise ValueError(f"a question page needs: {', '.join(missing)}")
        return self


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
    return merge_rows([(text, box) for text, _confidence, box in rows])


def merge_rows(boxes: list[tuple[str, list[float]]]) -> list[str]:
    """Vision returns separate boxes for "(A)" and its text, or "Situation" and its paragraph line, in
    normalized coordinates with the origin at the bottom left. Put boxes whose vertical centres fall within
    half a line height of each other on one line, left to right, and order the lines top to bottom. A gap
    clearly wider than the usual line spacing becomes an empty line: a paragraph break."""
    lines: list[tuple[float, float, list[tuple[float, str]]]] = []  # (centre, height, [(x, text)])
    for text, (x, y, _w, h) in sorted(boxes, key=lambda b: -(b[1][1] + b[1][3] / 2)):
        centre = y + h / 2
        if lines and abs(lines[-1][0] - centre) < 0.5 * min(lines[-1][1], h):
            lines[-1][2].append((x, text))
        else:
            lines.append((centre, h, [(x, text)]))
    gaps = sorted(a[0] - b[0] for a, b in itertools.pairwise(lines))
    usual = gaps[len(gaps) // 2] if gaps else 0.0
    out: list[str] = []
    for i, (centre, _, parts) in enumerate(lines):
        if i and usual and lines[i - 1][0] - centre > PARAGRAPH_GAP * usual:
            out.append("")
        out.append(" ".join(text for _, text in sorted(parts)))
    return out


def tesseract_ocr(png: bytes) -> list[str]:
    if not shutil.which("tesseract"):
        raise RuntimeError("tesseract is not installed (brew install tesseract)")
    out = subprocess.run(["tesseract", "stdin", "stdout", "-l", "eng"], input=png, capture_output=True, check=True).stdout.decode()
    # Tesseract marks paragraphs with blank lines already.
    return [line.strip() for line in out.splitlines()]


OCR_ENGINES: dict[str, Callable[[bytes], list[str]]] = {"apple": apple_ocr, "tesseract": tesseract_ocr}


# ------------------------------------------------------------------ assembling text


def has_options(lines: list[str]) -> bool:
    return len({m.group(1) for line in lines if (m := MARKER.match(line.strip()))}) >= 3


def worth_a_call(lines: list[str]) -> bool:
    """A page that starts or explains a question: options, or a printed key."""
    return has_options(lines) or printed_key("\n".join(lines)) is not None


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


KEY_PATTERN = re.compile(r"(?:correct answer is|the answer is|answer:)\s*\(?([A-E])\)?", re.IGNORECASE)


def printed_key(text: str) -> str | None:
    found = KEY_PATTERN.findall(text)
    return found[-1].upper() if found else None


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.replace("\u2019", "'").lower())


def agreement(copied: str, ocr: str) -> float:
    """Share of the model's words that line up, in order, with the OCR text: low when it rewrote or invented."""
    mine, theirs = words(copied), words(join_lines(ocr.splitlines()))
    if not mine:
        return 0.0
    blocks = difflib.SequenceMatcher(None, mine, theirs, autojunk=False).get_matching_blocks()
    return round(sum(b.size for b in blocks) / len(mine), 4)


def check_structure(page: PageStructure, ocr: str) -> tuple[list[str], float]:
    flags: list[str] = []
    copied = "\n".join([page.passage, page.stem, *(o.text for o in page.options)])
    score = agreement(copied, ocr)
    if score < AGREEMENT_FLOOR:
        flags.append("not_as_printed")
    printed = printed_key(ocr)
    if printed and page.answer_key and printed != page.answer_key:
        flags.append("key_mismatch")
    return flags, score


async def structure_pages(model: StructuredLLM, ocr: dict[int, list[str]], concurrency: int = 4) -> dict[int, tuple[PageStructure, str]]:
    """The model's structure of each page that starts a question, with the OCR text it was given."""
    gate = asyncio.Semaphore(concurrency)
    text = {n: "\n".join(lines) for n, lines in ocr.items()}
    tally = {"ok": 0, "failed": 0}

    async def one(n: int, body: str, label: str) -> PageStructure | None:
        async with gate:
            # Credits guard: if the first pages all fail, something systematic is wrong; stop calling.
            if tally["failed"] >= STOP_AFTER_FAILURES and tally["ok"] == 0:
                return None
            started = time.monotonic()
            try:
                page = await model.complete(STRUCTURE_SYSTEM, f"OCR TEXT:\n{body}", PageStructure, temperature=0.0)
            except Exception as e:  # noqa: BLE001 — one unreadable page should not stop the book
                tally["failed"] += 1
                print(f"[scan] page {label}: failed after {time.monotonic() - started:.0f}s: {e}", file=sys.stderr)
                if tally["failed"] == STOP_AFTER_FAILURES and tally["ok"] == 0:
                    print(f"[scan] the first {STOP_AFTER_FAILURES} pages all failed; stopping model calls.", file=sys.stderr)
                return None
            tally["ok"] += 1
            what = f"question {page.number or '?'}" if page.kind == "question" else "no question"
            print(f"[scan] page {label}: {what} ({time.monotonic() - started:.0f}s)", file=sys.stderr)
            return page

    candidates = [n for n in sorted(ocr) if worth_a_call(ocr[n])]
    first = dict(zip(candidates, await asyncio.gather(*(one(n, text[n], str(n)) for n in candidates)), strict=True))
    out: dict[int, tuple[PageStructure, str]] = {}
    for n in candidates:
        page, body = first[n], text[n]
        if page is None or page.kind != "question":
            continue
        if page.continues_on_next_page and n + 1 in text:
            body = f"{text[n]}\n{text[n + 1]}"
            page = await one(n, body, f"{n}+{n + 1}") or page
        out[n] = (page, body)
    return out


def model_dataset(structured: dict[int, tuple[PageStructure, str]], dataset: str, book: str, engine: str) -> dict:
    items = []
    for n, (page, body) in sorted(structured.items()):
        flags, score = check_structure(page, body)
        items.append(
            {
                "entry_id": n * 100,
                "book": book,
                "page": str(n),
                "number": page.number,
                "family": "CR",
                "subtype": page.subtype,
                "answer_key": page.answer_key,
                "key_verdict": "book",
                "question": {"passage": page.passage, "stem": page.stem, "choices": [o.model_dump() for o in sorted(page.options, key=lambda o: o.label)]},
                "official_explanation": "\n\n".join([page.explanation, *(f"{o.label}. {o.text}" for o in sorted(page.option_explanations, key=lambda o: o.label))]).strip(),
                "option_explanations": [o.model_dump() for o in page.option_explanations],
                "option_traps": [t.model_dump() for t in page.option_traps],
                "ocr_agreement": score,
                "flags": flags,
                "flagged": bool(flags),
            }
        )
    return {"dataset": dataset, "source": f"scan+{engine}+model", "exported_at": datetime.now(timezone.utc).isoformat(), "items": items}


# ------------------------------------------------------------------ rule-based layout (no model)

# "1. Text", "1 Text" (OCR can drop the period; the text then starts with a capital), or the number alone.
QUESTION_START = re.compile(r"^(\d{1,3})(?:[.)]\s*(\S.*)?|\s+([A-Z\"\u201c].*))?$")
OPTION = re.compile(r"^[(\[]?([A-E])[)\]]\s*(.*)$")
KEY_LINE = re.compile(r"(?:the\s+)?correct answer is\s*\(?([A-E])\)?", re.IGNORECASE)
BANNER = re.compile(r"^(argument (construction|evaluation)|evaluation of a plan|argument|evaluation|construction)\b", re.IGNORECASE)
TERMINAL = ('.', '?', '!', ':', '"', '\u201d', ')')
SUBTYPE_CUES = [
    ("weaken", r"weaken|undermine|cast(s)? (the most )?doubt|call(s)? into question|counter"),
    ("assumption", r"assum|depends on|relies on|presuppose"),
    ("flaw", r"flaw|vulnerable to (the )?criticism|questionable because|error in"),
    ("evaluate", r"evaluat|useful to (know|determine|establish)|most important to"),
    ("explain", r"explain|resolve|reconcile|discrepancy|paradox"),
    ("structure", r"boldface|role|roles played|play(s)? which"),
    ("strengthen", r"strengthen|support for the|most strongly support(s)? the (argument|claim|conclusion|prediction)|justify"),
    ("inference", r"infer|support(s)? which|most strongly support|conclusion|must (also )?be true|properly drawn"),
]


def structural(line: str) -> bool:
    line = line.strip()
    return bool(KEY_LINE.search(line) or QUESTION_START.match(line) or OPTION.match(line))


def boilerplate(pages: dict[int, list[str]]) -> set[str]:
    """Running titles and headers: top or bottom lines (digits stripped) that recur on many pages."""
    if len(pages) < 4:
        return set()
    seen: dict[str, int] = {}
    for lines in pages.values():
        for key in {re.sub(r"\d+", "#", line.strip().lower()) for line in [x for x in lines if x.strip()][:2] + [x for x in lines if x.strip()][-2:] if not structural(line)}:
            seen[key] = seen.get(key, 0) + 1
    return {k for k, count in seen.items() if count >= max(3, len(pages) // 3) and len(k) < 80}


def guess_subtype(stem: str) -> str:
    low = stem.lower()
    return next((name for name, cue in SUBTYPE_CUES if re.search(cue, low)), "")


def parse_book(pages: dict[int, list[str]]) -> list[dict]:
    """Split OCR lines into questions, assuming the usual answer-section layout: number and passage, stem,
    options (A)-(E), a reasoning-type banner, the explanation, and "The correct answer is X." Questions may
    run across pages."""
    noise = boilerplate(pages)
    stream = []
    for n in sorted(pages):
        lines = [line.strip() for line in pages[n]]
        last = [i for i, line in enumerate(lines) if line][-2:]
        for i, line in enumerate(lines):
            # A bare number among a page's last lines is its page number; elsewhere it may start a question.
            if re.fullmatch(r"\d{1,4}", line) and i in last:
                continue
            # Empty lines are paragraph breaks and are kept.
            if not line or re.sub(r"\d+", "#", line.lower()) not in noise:
                stream.append((n, line))
    items, start = [], 0
    for k, (_, line) in enumerate(stream):
        found = KEY_LINE.search(line)
        if not found:
            continue
        items.append(parse_question(stream[start : k + 1], found.group(1).upper()))
        start = k + 1
    return [i for i in items if i]


def paragraphs(lines: list[str], offset: int = 0) -> list[list[tuple[int, str]]]:
    out: list[list[tuple[int, str]]] = [[]]
    for i, line in enumerate(lines):
        if line:
            out[-1].append((offset + i, line))
        elif out[-1]:
            out.append([])
    return [p for p in out if p]


def split_passage(before_options: list[str]) -> tuple[str, str, str, int]:
    """(number, passage, stem, index of the passage's first line) from the lines before option (A).

    With paragraph breaks: the stem is the last paragraph and the passage the one before it, which leaves
    out chapter titles and introductions above it. The question number opens the passage or stands alone
    just above it. Without breaks: the passage starts at the last numbered line, and the stem is the run of
    lines after the passage's last sentence-ending line."""
    paras = paragraphs(before_options)
    if not paras:
        return "", "", "", 0
    number = ""
    if len(paras) >= 2 and not any(QUESTION_START.match(t) and re.match(r"\d{1,3}[.)]?(\s|$)", t) for _, t in paras[-1]):
        stem_lines, body = [t for _, t in paras[-1]], paras[-2]
        # No break between passage and stem: split the last paragraph at its last sentence end instead.
        cut = len(stem_lines) - 1
        while cut > 0 and not stem_lines[cut - 1].endswith(TERMINAL):
            cut -= 1
        if cut > 0:
            body, stem_lines = paras[-1][:cut], stem_lines[cut:]
            paras = [*paras[:-1], body]
        alone = len(paras) >= 3 and len(paras[-3]) == 1 and re.fullmatch(r"\d{1,3}[.)]?", paras[-3][0][1])
        if alone:
            number = re.match(r"\d+", paras[-3][0][1]).group(0)
        first, text = body[0]
        if not number and (m := QUESTION_START.match(text)):
            number, text = m.group(1), m.group(2) or m.group(3) or ""
        passage_lines = [line for line in [text, *(t for _, t in body[1:])] if line]
        return number, join_lines(passage_lines), join_lines(stem_lines), first

    flat = [(i, t) for p in paras for i, t in p]
    q = max((k for k, (_, t) in enumerate(flat) if QUESTION_START.match(t)), default=0)
    m = QUESTION_START.match(flat[q][1])
    number = m.group(1) if m else ""
    rest = (m.group(2) or m.group(3) or "") if m else flat[q][1]
    body = [line for line in [rest, *(t for _, t in flat[q + 1 :])] if line]
    stem_from = len(body) - 1
    while stem_from > 0 and not body[stem_from - 1].endswith(TERMINAL):
        stem_from -= 1
    return number, join_lines(body[:stem_from]), join_lines(body[stem_from:]), flat[q][0]


def parse_question(segment: list[tuple[int, str]], key: str) -> dict | None:
    lines = [text for _, text in segment]
    first_option = next((i for i, t in enumerate(lines) if (m := OPTION.match(t)) and m.group(1) == "A"), None)
    if first_option is None:
        return None
    number, passage, stem, q = split_passage(lines[:first_option])
    flags: list[str] = []

    # Options (A)-(E) in order; each runs until the next marker; (E) runs until the banner.
    marks: list[tuple[str, int]] = []
    for i in range(first_option, len(lines)):
        m = OPTION.match(lines[i])
        if m and m.group(1) == "ABCDE"[len(marks)]:
            marks.append((m.group(1), i))
            if len(marks) == 5:
                break
    end_e = len(lines) - 1
    if len(marks) == 5:
        e = marks[-1][1]
        end_e = next((i for i in range(e + 1, len(lines)) if BANNER.match(lines[i]) or lines[i].lower().startswith("situation")), e + 1)
    else:
        flags.append("choices_incomplete")
    choices = []
    for j, (label, i) in enumerate(marks):
        stop = marks[j + 1][1] if j + 1 < len(marks) else end_e
        text = join_lines([OPTION.match(lines[i]).group(2), *lines[i + 1 : stop]])
        choices.append({"label": label, "text": text})
    explanation = join_lines(lines[end_e:])
    if not passage or not stem:
        flags.append("missing_text")
    return {
        "page": str(segment[q][0]),
        "number": number,
        "subtype": guess_subtype(stem),
        "answer_key": key,
        "question": {"passage": passage, "stem": stem, "choices": choices},
        "official_explanation": explanation,
        "flags": flags,
    }


def rules_dataset(pages: dict[int, list[str]], dataset: str, book: str, engine: str) -> dict:
    items = []
    parsed_all = parse_book(pages)
    # Questions are numbered in order: a number OCR missed is the one between its neighbours.
    for k, parsed in enumerate(parsed_all):
        if parsed["number"]:
            continue
        before = parsed_all[k - 1]["number"] if k else ""
        after = parsed_all[k + 1]["number"] if k + 1 < len(parsed_all) else ""
        if before.isdigit():
            parsed["number"] = str(int(before) + 1)
        elif after.isdigit() and int(after) > 1:
            parsed["number"] = str(int(after) - 1)
        else:
            parsed["flags"].append("no_number")
    for parsed in parsed_all:
        items.append(
            {
                "entry_id": int(parsed["page"]) * 100 + len([i for i in items if i["page"] == parsed["page"]]),
                "book": book,
                "family": "CR",
                "key_verdict": "book",
                "option_traps": [],
                **parsed,
                "flagged": bool(parsed["flags"]),
            }
        )
    return {"dataset": dataset, "source": f"scan+{engine}+rules", "exported_at": datetime.now(timezone.utc).isoformat(), "items": items}


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
    ap.add_argument("--layout", choices=["rules", "model"], default="rules", help="rules: no model call (default); model: the primary model structures the OCR text, splits the explanation by option and tags traps")
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

    images = render_pages(args.pdf, parse_pages(args.pages))
    started = time.monotonic()
    ocr = {n: OCR_ENGINES[args.ocr](png) for n, png in images.items()}
    print(f"[scan] {len(ocr)} pages read by {args.ocr} OCR in {time.monotonic() - started:.0f}s", file=sys.stderr)
    if args.layout == "rules":
        data = rules_dataset(ocr, args.dataset, args.book, args.ocr)
    else:
        # Retries and schema fallbacks are logged as warnings; show them, and what failed, while a book runs.
        os.environ.setdefault("LOG_INVALID_OUTPUT", "1")
        logging.basicConfig(level=logging.WARNING, format="[%(name)s] %(message)s")
        settings = load_settings()
        model = make_llm(settings.primary, timeout=settings.timeout_seconds)
        # One correction round per page is enough for structuring; more mostly re-sends the same page.
        model._max_retries = 1
        data = model_dataset(asyncio.run(structure_pages(model, ocr)), args.dataset, args.book, args.ocr)
        data["model"] = model.model

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    flagged = [i for i in data["items"] if i["flagged"]]
    print(f"{len(images)} pages → {len(data['items'])} questions, {len(flagged)} flagged → {args.out}")
    for i in data["items"]:
        print(f"  page {i['page']} #{i['number']}: {i['subtype'] or '?'} key {i['answer_key']}, {len(i['question']['choices'])} options, explanation {len(i['official_explanation'])} chars {i['flags'] or ''}")
    if flagged:
        print("Fix each flagged item in the JSON against the page, then set \"flagged\": false.")


if __name__ == "__main__":
    main()
