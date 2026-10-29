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

from pydantic import BaseModel, Field, model_validator

from .llm import StructuredLLM
from .schemas import Label, TrapType

REPO = Path(__file__).resolve().parents[2]
RENDER_DPI = 200
# "(A) text", "A. text", "A) text", or the letter alone on its line with the text beside it in another column.
MARKER = re.compile(r"^[(\[]?([A-E])\s*[).:\]]?(?:\s+\S|$)")

LAYOUT_SYSTEM = """You lay out one OCR'd page of a GMAT/LSAT prep book's answer-explanation section.

The page is given as numbered lines. Do not copy any text: answer with line numbers only. Give the first \
and last line of the passage (the argument), of the question stem, of each answer option A-E, and of the \
book's explanation. Leave out page headers, footers, running titles and question-type banners. Record the \
letter the book gives as the correct answer, the question number, and the sub-type.

In this kind of book a page usually reads: the question number and the passage; the question stem; options \
marked (A) to (E); a reasoning-type banner (for example "Argument Construction"); the explanation, often \
with labels such as "Situation" and "Reasoning" and a line per option marked A to E; and "The correct \
answer is X." The explanation runs from the banner to that sentence.

For every option, give the trap it sets (or "correct") and a short reason in your own words (at most 15 \
words, never quoting the book).

If the page holds no question (a title page, an introduction, an answer grid), set kind to "not_a_question". \
If the explanation runs past the last line shown, set continues_on_next_page. If the page begins in the \
middle of the previous page's question, set starts_mid_question."""


class Span(BaseModel):
    first: int = Field(..., description="Number of the first line, as shown in [brackets]")
    last: int = Field(..., description="Number of the last line, inclusive")


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

    @model_validator(mode="after")
    def _complete_question(self) -> ScanLayout:
        # Every field defaults so that "not_a_question" can be short; a question page must be complete,
        # and a failure here goes back to the model as a correction request.
        if self.kind == "question" and not self.starts_mid_question:
            missing = [name for name in ("passage", "stem", "explanation", "answer_key") if getattr(self, name) is None]
            if not self.number:
                missing.append("number")
            if sorted(c.label for c in self.choices) != ["A", "B", "C", "D", "E"]:
                missing.append("choices (one line range for each of A-E)")
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
    half a line height of each other on one line, left to right, and order the lines top to bottom."""
    lines: list[tuple[float, float, list[tuple[float, str]]]] = []  # (centre, height, [(x, text)])
    for text, (x, y, _w, h) in sorted(boxes, key=lambda b: -(b[1][1] + b[1][3] / 2)):
        centre = y + h / 2
        if lines and abs(lines[-1][0] - centre) < 0.5 * min(lines[-1][1], h):
            lines[-1][2].append((x, text))
        else:
            lines.append((centre, h, [(x, text)]))
    return [" ".join(text for _, text in sorted(parts)) for _, _, parts in lines]


def tesseract_ocr(png: bytes) -> list[str]:
    if not shutil.which("tesseract"):
        raise RuntimeError("tesseract is not installed (brew install tesseract)")
    out = subprocess.run(["tesseract", "stdin", "stdout", "-l", "eng"], input=png, capture_output=True, check=True).stdout.decode()
    return [line for line in out.splitlines() if line.strip()]


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

    candidates = [n for n in order if worth_a_call(ocr[n])]
    for n in order:
        if n not in candidates:
            print(f"[scan] page {n}: no options or key found by OCR, skipped", file=sys.stderr)
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
                # Line numbers only, for checking a flagged item against the page.
                "layout": layout.model_dump(include={"passage", "stem", "choices", "explanation"}),
                "lines": len(lines),
                "flags": flags,
                "flagged": bool(flags),
            }
        )
    return {"dataset": dataset, "source": f"scan+{engine}", "exported_at": datetime.now(timezone.utc).isoformat(), "items": items}


# ------------------------------------------------------------------ rule-based layout (no model)

QUESTION_START = re.compile(r"^(\d{1,3})[.)]\s+(\S.*)$")
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
        for key in {re.sub(r"\d+", "#", line.strip().lower()) for line in lines[:2] + lines[-2:] if not structural(line)}:
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
    stream = [
        (n, line.strip())
        for n in sorted(pages)
        for line in pages[n]
        if line.strip() and not re.fullmatch(r"\d{1,4}", line.strip()) and re.sub(r"\d+", "#", line.strip().lower()) not in noise
    ]
    items, start = [], 0
    for k, (_, line) in enumerate(stream):
        found = KEY_LINE.search(line)
        if not found:
            continue
        items.append(parse_question(stream[start : k + 1], found.group(1).upper()))
        start = k + 1
    return [i for i in items if i]


def parse_question(segment: list[tuple[int, str]], key: str) -> dict | None:
    lines = [text for _, text in segment]
    first_option = next((i for i, t in enumerate(lines) if (m := OPTION.match(t)) and m.group(1) == "A"), None)
    if first_option is None:
        return None
    q = max((i for i in range(first_option) if QUESTION_START.match(lines[i])), default=None)
    flags: list[str] = []
    if q is None:
        flags.append("no_number")
        q = 0
    number = QUESTION_START.match(lines[q]).group(1) if QUESTION_START.match(lines[q]) else ""
    body = [QUESTION_START.match(lines[q]).group(2) if number else lines[q], *lines[q + 1 : first_option]]

    # The stem is the run of lines after the passage's last sentence-ending line.
    stem_from = len(body) - 1
    while stem_from > 0 and not body[stem_from - 1].endswith(TERMINAL):
        stem_from -= 1
    passage, stem = join_lines(body[:stem_from]), join_lines(body[stem_from:])

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
    for parsed in parse_book(pages):
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
    ap.add_argument("--layout", choices=["rules", "model"], default="rules", help="rules: no model call (default); model: the primary model picks line ranges and trap tags")
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
        # Retries and schema fallbacks are logged as warnings; show them while a long book runs.
        logging.basicConfig(level=logging.WARNING, format="[%(name)s] %(message)s")
        settings = load_settings()
        model = make_llm(settings.primary, timeout=settings.timeout_seconds)
        data = build_dataset(asyncio.run(lay_out(model, ocr)), args.dataset, args.book, args.ocr)

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
