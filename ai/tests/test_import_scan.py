import asyncio
import json

import pytest
from conftest import ScriptedLLM

from questionize import import_scan
from questionize.eval_e1 import load_dataset
from questionize.import_scan import (
    ScanPage,
    agreement,
    build_dataset,
    check,
    ocr_key,
    parse_pages,
    read_pages,
)

CHOICES = [{"label": label, "text": f"Option {label} about the new bike lanes."} for label in "ABCDE"]
OCR_TEXT = (
    "Questions 12\nAccidents fell after the city opened bike lanes on Main Street.\n"
    "Which of the following most seriously weak-\nens the argument?\n"
    + "\n".join(f"({c['label']}) {c['text']}" for c in CHOICES)
    + "\nThe correct answer is B.\nGMAT Official Guide 2025"
)


def page(**over) -> ScanPage:
    base = {
        "kind": "question",
        "number": "12",
        "family": "CR",
        "subtype": "weaken",
        "passage": "Accidents fell after the city opened bike lanes on Main Street.",
        "stem": "Which of the following most seriously weakens the argument?",
        "choices": CHOICES,
        "answer_key": "B",
        "official_explanation": "Book explanation text.",
        "option_traps": [{"label": "A", "trap": "irrelevant", "why": "Off the causal claim."}],
    }
    return ScanPage.model_validate(base | over)


def test_parse_pages():
    assert parse_pages("3-5, 9") == [3, 4, 5, 9]


def test_agreement_ignores_hyphenation_and_headers_but_catches_invented_text():
    assert agreement(import_scan.question_text(page()), OCR_TEXT) == 1.0
    invented = page(passage="Accidents fell sharply after the city opened protected bike lanes on Main Street last spring.")
    assert agreement(import_scan.question_text(invented), OCR_TEXT) < import_scan.AGREEMENT_FLOOR


def test_check_flags_key_and_transcription_problems():
    assert ocr_key(OCR_TEXT) == "B"
    assert check(page(), OCR_TEXT) == ([], 1.0)
    flags, _ = check(page(answer_key="D"), OCR_TEXT)
    assert flags == ["key_mismatch"]
    flags, score = check(page(answer_key=None, choices=CHOICES[:4]), None)
    assert flags == ["no_key", "choices_incomplete"] and score is None


def test_read_pages_joins_a_question_that_runs_onto_the_next_page():
    joined = page(official_explanation="Explanation across both pages.")
    model = ScriptedLLM(
        ScanPage=[
            page(continues_on_next_page=True),  # page 10, first pass
            page(starts_mid_question=True),  # page 11
            ScanPage(kind="not_a_question"),  # page 12
            joined,  # page 10 with 11
        ]
    )
    images = {10: b"p10", 11: b"p11", 12: b"p12"}
    pages = asyncio.run(read_pages(model, images, concurrency=1))
    assert list(pages) == [10] and pages[10].official_explanation == "Explanation across both pages."
    assert model.images == [import_scan.data_url(b"p10"), import_scan.data_url(b"p11")]


def test_dataset_round_trips_into_e1_and_skips_flagged_items(tmp_path):
    pages = {10: page(), 11: page(answer_key="D")}
    data = build_dataset(pages, {10: b"x", 11: b"y"}, lambda png: OCR_TEXT, "official-cr-v1", "Official Guide")
    assert [i["flags"] for i in data["items"]] == [[], ["key_mismatch"]]
    path = tmp_path / "ds.json"
    path.write_text(json.dumps(data))
    _, _, items, excluded = load_dataset(path)
    assert [i.entry_id for i in items] == [10] and items[0].official_explanation == "Book explanation text."
    assert excluded["flagged_scan"] == 1


def test_refuses_to_write_inside_the_repository():
    with pytest.raises(SystemExit):
        import_scan.main(["book.pdf", "--pages", "1", "--out", str(import_scan.REPO / "ai" / "leak.json")])


def test_render_pages_reads_a_pdf(tmp_path):
    pdfium = pytest.importorskip("pypdfium2")
    doc = pdfium.PdfDocument.new()
    doc.new_page(200, 300)
    doc.new_page(200, 300)
    pdf = tmp_path / "book.pdf"
    doc.save(str(pdf))
    images = import_scan.render_pages(pdf, [1, 2, 3], dpi=72)
    assert sorted(images) == [1, 2] and images[1].startswith(b"\x89PNG")
