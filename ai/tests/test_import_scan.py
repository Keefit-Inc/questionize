import asyncio
import json

import pytest
from conftest import ScriptedLLM

from questionize import import_scan
from questionize.eval_e1 import load_dataset
from questionize.import_scan import PageStructure, has_options, join_lines, parse_pages

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


def structure(**over) -> PageStructure:
    base = {
        "kind": "question",
        "number": "12",
        "passage": "Accidents fell after the city opened bike lanes on Main Street.",
        "stem": "Which of the following most seriously weakens the argument?",
        **{f"option_{line[1].lower()}": line[4:] for line in PAGE[5:10]},
        "answer_key": "B",
        "explanation": "Speed cameras offer another cause for the drop.",
        "explanation_a": "Sales do not bear on the cause.",
        "subtype": "weaken",
        "trap_a": "irrelevant",
        "trap_b": "a made-up trap",
    }
    return PageStructure.model_validate(base | over)


def test_parse_pages():
    assert parse_pages("3-5, 9") == [3, 4, 5, 9]


def test_join_lines_undoes_hyphenation():
    assert join_lines(["most seriously weak-", "ens the argument?"]) == "most seriously weakens the argument?"
    assert join_lines(["a well-", "Known case"]) == "a well- Known case"


def test_an_incomplete_question_is_sent_back_to_the_model():
    with pytest.raises(ValueError, match="passage, stem, option_a, option_b, option_c, option_d, option_e, answer_key"):
        PageStructure.model_validate({"kind": "question"})
    assert PageStructure.model_validate({"kind": "not_a_question"}).options == []


def test_structure_is_checked_against_the_ocr_text():
    ocr = "\n".join(PAGE)
    assert import_scan.check_structure(structure(), ocr) == ([], 1.0)
    reworded = structure(passage="After protected bike lanes opened downtown last spring, crashes dropped sharply.")
    flags, score = import_scan.check_structure(reworded, ocr)
    assert flags == ["not_as_printed"] and score < import_scan.AGREEMENT_FLOOR
    assert import_scan.check_structure(structure(answer_key="D"), ocr)[0] == ["key_mismatch"]


def test_the_model_gets_the_ocr_text_and_continuations():
    intro = ["Chapter 7", "Critical Reasoning Answer Explanations"]
    tail = ["of the drop, so the conclusion does not follow."]
    model = ScriptedLLM(PageStructure=[structure(continues_on_next_page=True), structure()])
    out = asyncio.run(import_scan.structure_pages(model, {1: intro, 2: PAGE, 3: tail}, concurrency=1))
    assert list(out) == [2] and out[2][1].endswith("does not follow.")
    # Only OCR text goes to the model; never an image. The intro page is skipped without a call.
    assert len(model.calls) == 2 and model.calls[0][1].startswith("OCR TEXT:\nCritical Reasoning")
    assert not hasattr(model, "images")
    data = import_scan.model_dataset(out, "official-cr-v1", "Guide", "apple")
    (item,) = data["items"]
    assert item["question"]["choices"][1]["text"] == "Speed cameras were installed the same year."
    assert item["official_explanation"].startswith("Speed cameras offer") and "A. Sales do not" in item["official_explanation"]
    assert item["flags"] == [] and item["option_traps"] == [{"label": "A", "trap": "irrelevant"}]


def test_option_markers_in_other_layouts():
    assert has_options(["A. Bike sales rose.", "B. Cameras.", "C. Paint."])
    assert has_options(["A", "B", "C", "D", "E"])  # letters in their own column
    assert not has_options(["A city opened lanes.", "Because of this, accidents fell."])
    # A page with only the key printed still gets a call.
    assert import_scan.worth_a_call(["Speed cameras offer another cause.", "The correct answer is B."])


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


def test_merge_rows_puts_markers_and_labels_on_their_lines():
    # Two-column rows as Vision reports them: separate boxes, slightly different heights, any order.
    boxes = [
        ("At least some animals recall every detail.", [0.16, 0.648, 0.70, 0.014]),
        ("(A)", [0.12, 0.6485, 0.02, 0.013]),
        ("The neuroscientist's statements most strongly support which?", [0.12, 0.672, 0.70, 0.014]),
        ("(B)", [0.12, 0.627, 0.02, 0.013]),
        ("Perfectly recalling every detail could help", [0.16, 0.626, 0.70, 0.014]),
        ("some animals react more appropriately.", [0.16, 0.609, 0.70, 0.014]),
    ]
    assert import_scan.merge_rows(boxes) == [
        "The neuroscientist's statements most strongly support which?",
        "(A) At least some animals recall every detail.",
        "(B) Perfectly recalling every detail could help",
        "some animals react more appropriately.",
    ]


def book_page(number: int, key: str, header: bool = True) -> list[str]:
    """A page laid out like a prep book's answer section, in our own words."""
    return [
        *(["The Study Guide for Tests Review 2016"] if header else []),
        f"{number}. Planner: Accidents fell after the city opened bike lanes on",
        "Main Street, so bike lanes make streets safer.",
        "Which of the following, if true, most seriously weak-",
        "ens the planner's argument?",
        "(A) Bike sales rose.",
        "(B) Speed cameras were installed on Main Street the",
        "same year.",
        "(C) The lanes are painted green.",
        "(D) Other cities built lanes.",
        "(E) Some drivers dislike the lanes.",
        "Argument Evaluation",
        "Situation The planner credits the lanes for the drop.",
        "A This does not bear on the cause.",
        f"The correct answer is {key}.",
        f"{540 + number}",
    ]


def test_rules_parse_a_book_page_without_any_model():
    pages = {n: book_page(n, "B") for n in range(1, 5)}
    items = import_scan.parse_book(pages)
    assert len(items) == 4
    first = items[0]
    assert first["number"] == "1" and first["answer_key"] == "B" and first["subtype"] == "weaken" and first["flags"] == []
    q = first["question"]
    assert q["passage"] == "Planner: Accidents fell after the city opened bike lanes on Main Street, so bike lanes make streets safer."
    assert q["stem"] == "Which of the following, if true, most seriously weakens the planner's argument?"
    assert q["choices"][1] == {"label": "B", "text": "Speed cameras were installed on Main Street the same year."}
    assert q["choices"][4]["text"] == "Some drivers dislike the lanes."
    assert first["official_explanation"].startswith("Argument Evaluation Situation") and first["official_explanation"].endswith("answer is B.")


def test_rules_follow_a_question_across_pages_and_skip_an_intro():
    page = book_page(7, "D")
    pages = {1: ["Answer Explanations", "The following discussion explains each question."] + page[:9], 2: page[9:]}
    (item,) = import_scan.parse_book(pages)
    assert item["page"] == "1" and item["number"] == "7" and item["answer_key"] == "D"
    assert [c["label"] for c in item["question"]["choices"]] == list("ABCDE")


def test_rules_dataset_feeds_e1(tmp_path):
    data = import_scan.rules_dataset({n: book_page(n, "B") for n in range(1, 5)}, "official-cr-v1", "Guide", "apple")
    path = tmp_path / "ds.json"
    path.write_text(json.dumps(data))
    _, _, items, excluded = load_dataset(path)
    assert len(items) == 4 and excluded["flagged_scan"] == 0


def test_rules_accept_a_number_without_its_period_or_on_its_own_line():
    no_period = book_page(1, "E", header=False)
    no_period[0] = "1 Planner: Accidents fell after the city opened bike lanes on"
    alone = book_page(2, "C", header=False)
    alone[0:1] = ["2", "Planner: Accidents fell after the city opened bike lanes on"]
    items = import_scan.parse_book({1: no_period, 2: alone})
    assert [(i["number"], i["flags"]) for i in items] == [("1", []), ("2", [])]
    assert items[1]["question"]["passage"].startswith("Planner: Accidents")
    # "30 percent of..." in a passage is not a question number.
    assert not import_scan.QUESTION_START.match("30 percent of riders")


def test_merge_rows_marks_paragraph_breaks():
    # Lines 0.017 apart inside a paragraph, 0.025 between paragraphs.
    ys = [0.80, 0.783, 0.766, 0.741, 0.724]
    boxes = [(f"line {i}", [0.1, y, 0.7, 0.012]) for i, y in enumerate(ys)]
    assert import_scan.merge_rows(boxes) == ["line 0", "line 1", "line 2", "", "line 3", "line 4"]


def test_paragraphs_separate_the_passage_from_titles_and_an_introduction():
    page = book_page(1, "E", header=False)
    lines = [
        "8.6 Answer Explanations",
        "",
        "The following discussion is intended to help you. Remember the strategy,",
        "not the details.",
        "",
        page[0].removeprefix("1. "),  # OCR missed the number in the margin
        page[1],
        "",
        page[2],
        page[3],
        "",
        *page[4:],
    ]
    second = book_page(2, "C", header=False)
    (first, nxt) = import_scan.rules_dataset({1: lines, 2: second}, "d", "b", "apple")["items"]
    assert first["question"]["passage"] == "Planner: Accidents fell after the city opened bike lanes on Main Street, so bike lanes make streets safer."
    assert first["question"]["stem"].startswith("Which of the following")
    # The missing number is filled in from its neighbour, so the item is not flagged.
    assert first["number"] == "1" and first["flags"] == [] and nxt["number"] == "2"


def test_paragraph_split_when_passage_and_stem_run_together():
    page = book_page(3, "A", header=False)
    lines = ["Introduction text for the chapter.", "", page[0], page[1], page[2], page[3], "", *page[4:]]
    (item,) = import_scan.parse_book({1: lines})
    assert item["number"] == "3" and item["question"]["stem"].startswith("Which of the following")
    assert item["question"]["passage"].startswith("Planner:")


def test_model_calls_stop_when_the_first_pages_all_fail():
    class Failing:
        model = "m"
        calls = 0

        async def complete(self, *a, **kw):
            Failing.calls += 1
            raise RuntimeError("bad output")

    pages = {n: PAGE for n in range(1, 11)}
    out = asyncio.run(import_scan.structure_pages(Failing(), pages, concurrency=1))
    assert out == {} and Failing.calls == import_scan.STOP_AFTER_FAILURES
