import asyncio
import json

import pytest
from conftest import ScriptedLLM

from questionize import import_scan
from questionize.eval_e1 import load_dataset
from questionize.import_scan import (
    ScanLayout,
    assemble,
    build_dataset,
    has_options,
    join_lines,
    lay_out,
    parse_pages,
)

PAGE = [
    "Critical Reasoning Answer Explanations",  # 1 running title
    "12. Accidents fell after the city opened bike",  # 2
    "lanes on Main Street.",  # 3
    "Which of the following most seriously weak-",  # 4
    "ens the argument?",  # 5
    "(A) Bike sales rose.",  # 6
    "(B) Speed cameras were installed the same year.",  # 7
    "(C) The lanes are painted green.",  # 8
    "(D) Other cities built lanes.",  # 9
    "(E) Some drivers dislike the lanes.",  # 10
    "Speed cameras offer another cause for the drop.",  # 11
    "The correct answer is B.",  # 12
]


def layout(**over) -> ScanLayout:
    base = {
        "kind": "question",
        "number": "12",
        "family": "CR",
        "subtype": "weaken",
        "passage": {"first": 2, "last": 3},
        "stem": {"first": 4, "last": 5},
        "choices": [{"label": label, "first": 6 + i, "last": 6 + i} for i, label in enumerate("ABCDE")],
        "explanation": {"first": 11, "last": 12},
        "answer_key": "B",
        "option_traps": [{"label": "A", "trap": "irrelevant", "why": "Off the causal claim."}],
    }
    return ScanLayout.model_validate(base | over)


def test_parse_pages():
    assert parse_pages("3-5, 9") == [3, 4, 5, 9]


def test_join_lines_undoes_hyphenation():
    assert join_lines(["most seriously weak-", "ens the argument?"]) == "most seriously weakens the argument?"
    assert join_lines(["a well-", "Known case"]) == "a well- Known case"


def test_assemble_takes_the_printed_text_by_line_number():
    fields, flags = assemble(layout(), PAGE)
    assert flags == []
    q = fields["question"]
    assert q["passage"] == "12. Accidents fell after the city opened bike lanes on Main Street."
    assert q["stem"] == "Which of the following most seriously weakens the argument?"
    assert q["choices"][1] == {"label": "B", "text": "Speed cameras were installed the same year."}
    assert fields["official_explanation"].endswith("The correct answer is B.")


def test_assemble_flags_bad_layouts():
    _, flags = assemble(layout(answer_key="D"), PAGE)
    assert flags == ["key_mismatch"]
    _, flags = assemble(layout(answer_key=None, stem={"first": 4, "last": 99}, choices=[]), PAGE)
    assert flags == ["missing_text", "choices_incomplete", "no_key"]


def test_lay_out_skips_pages_without_options_and_joins_continuations():
    intro = ["Chapter 7", "Critical Reasoning Answer Explanations"]
    tail = ["of the drop, so the conclusion does not follow."]
    model = ScriptedLLM(
        ScanLayout=[
            layout(continues_on_next_page=True),  # page 2, first pass
            layout(explanation={"first": 11, "last": 13}),  # page 2 with 3
        ]
    )
    out = asyncio.run(lay_out(model, {1: intro, 2: PAGE, 3: tail}, concurrency=1))
    assert list(out) == [2]
    chosen, lines = out[2]
    assert len(lines) == len(PAGE) + 1 and chosen.explanation.last == 13
    # Only OCR'd text goes to the model, as numbered lines; never an image.
    assert len(model.calls) == 2 and model.calls[0][1].startswith("[1] Critical Reasoning")
    assert not hasattr(model, "images")
    assert has_options(PAGE) and not has_options(intro)


def test_option_markers_in_other_layouts():
    assert has_options(["A. Bike sales rose.", "B. Cameras.", "C. Paint."])
    assert has_options(["A", "B", "C", "D", "E"])  # letters in their own column
    assert not has_options(["A city opened lanes.", "Because of this, accidents fell."])
    # A page with only the key printed still gets a call.
    assert import_scan.worth_a_call(["Speed cameras offer another cause.", "The correct answer is B."])


def test_dataset_round_trips_into_e1_and_skips_flagged_items(tmp_path):
    data = build_dataset({10: (layout(), PAGE), 11: (layout(answer_key="D"), PAGE)}, "official-cr-v1", "Official Guide", "apple")
    assert [i["flags"] for i in data["items"]] == [[], ["key_mismatch"]]
    path = tmp_path / "ds.json"
    path.write_text(json.dumps(data))
    _, _, items, excluded = load_dataset(path)
    assert [i.entry_id for i in items] == [10] and items[0].official_explanation.endswith("answer is B.")
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
