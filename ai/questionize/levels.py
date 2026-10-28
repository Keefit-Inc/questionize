"""Learner levels: who a question, explanation or diagnosis is written for (docs/LEARNING_MODEL.md §4).

A level sets the language (vocabulary, sentence length, passage length), which sub-types are in
scope, how distractors are built, and how explanations talk to the learner. The reasoning stays
the same kind at every level: a claim, its support, and what would make it stronger or weaker.
Grade-band levels point at the Common Core reading standard for evaluating arguments (RI.x.8),
which is publicly licensed; the test-prep levels follow each test's official question types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

LevelId = Literal["elementary", "middle", "high", "college", "gmat", "lsat", "gre"]
DEFAULT_LEVEL: LevelId = "gmat"


@dataclass(frozen=True)
class Level:
    id: str
    label: str
    audience: str
    language: str
    cr_words: tuple[int, int]
    rc_words: tuple[int, int]
    subtypes: dict[str, list[str]]
    distractors: str
    explain: str
    standards: list[str] = field(default_factory=list)
    stems: str = ""


_ALL = {
    "RC": ["main_idea", "detail", "inference", "author_purpose", "structure"],
    "CR": ["weaken", "strengthen", "assumption", "flaw", "evaluate", "inference"],
}

LEVELS: dict[str, Level] = {
    "elementary": Level(
        id="elementary",
        label="Grades 3-5",
        audience="children aged 8 to 11 (US grades 3-5), with a parent or teacher",
        language="Everyday words a 4th grader knows; sentences under 15 words; no idioms or sarcasm; concrete, familiar situations (school, family, pets, sports, the neighborhood).",
        cr_words=(40, 70),
        rc_words=(80, 140),
        subtypes={"CR": ["strengthen", "weaken", "inference"], "RC": ["main_idea", "detail", "inference"]},
        distractors="Wrong options are clearly wrong for one simple reason (off topic, not stated, or the opposite), never trick wording.",
        explain="Talk to the child directly and warmly, in 2-3 short sentences. Name the reason, not the jargon (say 'a different reason' rather than 'alternative cause').",
        standards=["CCSS.ELA-LITERACY.RI.3.8", "CCSS.ELA-LITERACY.RI.4.8", "CCSS.ELA-LITERACY.RI.5.8"],
        stems="Use plain stems such as 'Which fact would make Maya's idea stronger?' or 'What is this story mostly about?'",
    ),
    "middle": Level(
        id="middle",
        label="Grades 6-8",
        audience="students aged 11 to 14 (US grades 6-8)",
        language="Grade 6-8 vocabulary; sentences under 20 words; topics from school subjects and teen life.",
        cr_words=(50, 90),
        rc_words=(120, 200),
        subtypes={"CR": ["strengthen", "weaken", "assumption", "inference"], "RC": ["main_idea", "detail", "inference", "author_purpose"]},
        distractors="One or two distractors may be tempting (on topic but irrelevant, or too strong); avoid double negatives.",
        explain="Explain in 3-4 sentences in plain words; introduce one term (claim, evidence, assumption) and say what it means.",
        standards=["CCSS.ELA-LITERACY.RI.6.8", "CCSS.ELA-LITERACY.RI.7.8", "CCSS.ELA-LITERACY.RI.8.8"],
        stems="Stems name the speaker and the claim, e.g. 'Which of these, if true, would most weaken the principal's argument?'",
    ),
    "high": Level(
        id="high",
        label="Grades 9-12 · SAT/ACT",
        audience="high school students (US grades 9-12), including SAT and ACT preparation",
        language="High school vocabulary; clear academic register like SAT Reading and Writing passages.",
        cr_words=(60, 110),
        rc_words=(150, 250),
        subtypes=_ALL,
        distractors="Distractors use common traps (too extreme, out of scope, half right) at moderate subtlety.",
        explain="Explain in 3-5 sentences; name the reasoning move and the trap in standard terms.",
        standards=["CCSS.ELA-LITERACY.RI.9-10.8", "CCSS.ELA-LITERACY.RI.11-12.8"],
        stems="Stems follow SAT-style phrasing: 'Which finding, if true, would most directly support the researcher's claim?'",
    ),
    "college": Level(
        id="college",
        label="College & adult",
        audience="college students and adults building general critical-thinking skills",
        language="Educated general-audience English, like a quality newspaper.",
        cr_words=(60, 120),
        rc_words=(150, 300),
        subtypes=_ALL,
        distractors="Standard traps at moderate to high subtlety.",
        explain="Explain concisely (3-5 sentences) using standard argument terms.",
    ),
    "gmat": Level(
        id="gmat",
        label="GMAT",
        audience="GMAT test-takers (graduate business school admissions)",
        language="GMAT Critical Reasoning and Reading Comprehension register: business, economics, science and policy topics.",
        cr_words=(60, 120),
        rc_words=(150, 300),
        subtypes=_ALL,
        distractors="Official-test subtlety: close distractors that differ in scope, strength or direction.",
        explain="Explain like an expert tutor: the argument's core, the gap, why the key closes or widens it, and why each trap fails.",
        stems="Use official GMAT stem phrasing.",
    ),
    "lsat": Level(
        id="lsat",
        label="LSAT",
        audience="LSAT test-takers (law school admissions)",
        language="LSAT Logical Reasoning register: precise, formal, with careful quantifiers and conditional language.",
        cr_words=(60, 130),
        rc_words=(200, 320),
        subtypes=_ALL,
        distractors="LSAT subtlety: necessary vs sufficient, scope shifts, quantifier changes, plausible but unsupported claims.",
        explain="Explain like an LSAT tutor: conclusion, premises, the gap, and the exact wording that makes each wrong answer fail.",
        stems="Use LSAT Logical Reasoning stem phrasing, e.g. 'The argument is most vulnerable to criticism on the grounds that it...'",
    ),
    "gre": Level(
        id="gre",
        label="GRE",
        audience="GRE test-takers (graduate school admissions)",
        language="GRE Verbal register: academic topics from the sciences, humanities and social sciences.",
        cr_words=(60, 110),
        rc_words=(150, 300),
        subtypes=_ALL,
        distractors="GRE subtlety: options that echo the passage's words but change its meaning.",
        explain="Explain concisely like a GRE tutor, naming the reasoning move and each trap.",
        stems="Use GRE argument-question phrasing.",
    ),
}


def level(level_id: str | None) -> Level:
    return LEVELS.get(level_id or DEFAULT_LEVEL, LEVELS[DEFAULT_LEVEL])


def brief(level_id: str | None) -> str:
    """The audience block added to writer, critic, reviser and diagnosis prompts."""
    lv = level(level_id)
    lines = [
        f"AUDIENCE LEVEL: {lv.label} — {lv.audience}.",
        f"- Language: {lv.language}",
        f"- Length: CR stimulus {lv.cr_words[0]}-{lv.cr_words[1]} words; RC passage {lv.rc_words[0]}-{lv.rc_words[1]} words.",
        f"- Distractors: {lv.distractors}",
        f"- Explanations and rationales: {lv.explain}",
    ]
    if lv.stems:
        lines.append(f"- Stems: {lv.stems}")
    if lv.standards:
        lines.append(f"- Aligned to: {', '.join(lv.standards)} (evaluate an argument's reasons and evidence).")
    return "\n".join(lines)


def subtypes(level_id: str | None, family: str) -> list[str]:
    return list(level(level_id).subtypes.get(family, _ALL.get(family, [])))
