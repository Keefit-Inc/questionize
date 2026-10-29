# Learning model

How Questionize measures a learner's reasoning, finds strengths and weaknesses, chooses what they practice next, adapts to their age or target test, and how we check that each part works. It builds on the knowledge model (`KNOWLEDGE_MODEL.md`: competencies, misconceptions, trap patterns, blueprints, evidence) and the item pipeline (`ARCHITECTURE.md`).

Status markers: **[built]** is in the code today, **[next]** is designed and scheduled, **[later]** is designed but waits on data or partners.

## 1. Principles

1. **Measure reasoning moves, not topics.** A learner who misses a weaken question about bike lanes and one about vaccines has the same gap. Skills are the unit of measurement; topics are only context.
2. **Every claim about a learner needs evidence.** We say "weak at assumptions" only with enough rated answers to back it, and we show how sure we are.
3. **Practice where it stretches.** Questions are pitched so a learner gets about seven in ten right: hard enough to learn from, easy enough to keep going.
4. **Mistakes are the richest signal.** A missed question tells us which trap worked and which belief made it work. Snap (the error log) exists to capture exactly that.
5. **Same reasoning, different language.** A fourth grader and an LSAT candidate both learn to ask "what else could explain this?" The level changes the words, the length and the subtlety, not the kind of thinking.

## 2. Competency framework

Four layers, from coarse to fine:

| Layer | Example | Where it lives |
|---|---|---|
| Subject | Critical Reasoning (CR), Reading Comprehension (RC) | `items.family` |
| Skill (sub-type) | CR · weaken, CR · assumption, RC · inference | `items.subtype`; ratings key `CR:weaken` |
| Competency | "Recognize an alternative cause for a claimed effect" | `competencies` (KNOWLEDGE_MODEL §3.2) |
| Trap and misconception | trap `irrelevant`; misconception `keyword_matching` | rationales' `trap` tags; `misconceptions`, `trap_patterns` |

The skill list combines three public sources, so a learner's profile reads the same way their teacher or test does:

- **Test makers' question types.** GMAT Critical Reasoning (weaken, strengthen, assumption, flaw, evaluate, inference) and Reading Comprehension (main idea, detail, inference, purpose, structure); LSAT Logical Reasoning and GRE argument questions map onto the same skills.
- **Common Core, Reading Informational Text, standard 8** ("delineate and evaluate the argument and specific claims in a text"), which grows by grade: RI.3.8–RI.5.8 (how reasons support points), RI.6.8–RI.8.8 (trace and evaluate claims, sufficiency of evidence), RI.9-10.8 and RI.11-12.8 (validity, relevance, fallacious reasoning).
- **Our knowledge model**, which adds what the standards leave out: the specific traps and misconceptions that make options tempting, measured from real answers.

## 3. Assessment

### 3.1 Ratings [built]

- An Elo rating per skill (`CR:weaken`), rolled up to the subject and overall. Items have ratings too, so a hard question that a learner gets right moves them more.
- Only the first answer to a question is rated; later answers count toward crowd statistics only.
- A rating is **provisional** below 10 rated answers and labelled so.

### 3.2 Strengths and weaknesses

- **Skill strength [built for ratings, next for labels].** Compare each skill rating with the learner's own overall rating. A skill at least 100 points below it, with 5 or more rated answers, is a weakness; 100 above is a strength. The gap and the answer count are shown, so the label can be judged.
- **Trap profile [built for counts, next for rates].** Today: how often each trap caught the learner in snapped questions. Next: a rate per trap, *times chosen ÷ times it was offered* across all answers (every option carries a trap tag), with a Wilson 80% interval. A trap is flagged only when the interval's low end is above the learner's base error rate.
- **Misconceptions [built].** From snapped questions, the diagnosis names the belief behind the choice (`keyword_matching`, `necessary_vs_sufficient`, …). Me → Analysis shows the recurring ones.
- **Mastery [next].** A skill is mastered at a level when its rating is above that level's target and the last five rated answers on it include at least four right. Mastered skills drop out of recommendations except for spaced review.

### 3.3 Calibration [later]

Elo is good online. Once items have enough answers (around 100), a nightly job fits a Rasch model per level to re-estimate item difficulty and learner ability together, and flags items whose difficulty differs from their Elo rating by more than 1 logit.

## 4. Levels

A learner chooses who they study as. From then on everything written for them is pitched at that level: new questions, explanations, Snap analyses, practice questions; and the Bank opens on that level. Levels map onto the knowledge model's developmental scale (KNOWLEDGE_MODEL §2).

| Level | Scale | Passages (CR / RC words) | Skills in scope | Language and explanations | Standards |
|---|---|---|---|---|---|
| Grades 3–5 | L4–L6 | 40–70 / 80–140 | CR strengthen, weaken, inference; RC main idea, detail, inference | Everyday words, short sentences; warm 2–3 sentence explanations; no jargon | RI.3.8–RI.5.8 |
| Grades 6–8 | L7–L8 | 50–90 / 120–200 | adds assumption, author's purpose | Plain words; introduces one term at a time | RI.6.8–RI.8.8 |
| Grades 9–12 · SAT/ACT | L9–L12 | 60–110 / 150–250 | all | SAT-style academic register | RI.9-10.8, RI.11-12.8 |
| College & adult | L13 | 60–120 / 150–300 | all | Newspaper register | |
| GMAT | L14 | 60–120 / 150–300 | all | Official GMAT stems; expert-tutor explanations | GMAT CR / RC |
| LSAT | L14 | 60–130 / 200–320 | all | Formal, careful quantifiers and conditionals | LSAT Logical Reasoning |
| GRE | L14 | 60–110 / 150–300 | all | GRE Verbal register | GRE argument questions |

**How it is enforced [built].** `ai/questionize/levels.py` turns the level into an audience brief (language, lengths, distractor style, explanation voice, standards) that goes to the writer, the critic (who must report a level mismatch), the reviser, the Snap reader and the practice writer. The slot planner only picks skills in scope for the level. Items store their level; the Bank filters by it.

**Filling every level [built].** Two sources of questions for levels nobody is snapping at yet:

- *Fan-out.* When a snapped question's abstract design passes the leak checks, background jobs can write one practice question from the same design for each level in `PRACTICE_FANOUT_LEVELS` (for example Grades 6–8, Grades 9–12, College & adult), besides the learner's own level. It is off by default: designs are learned first, and level-wide generation waits until a design is corroborated by several independent sources (DECISIONS R3). A design whose skill is out of scope for a level (an LSAT flaw question for Grades 3–5) is skipped, not forced. So a GMAT or LSAT learner's misses also stock the school levels.
- *Seed designs.* `api/db/seeds/designs.json` holds twelve abstract designs written for Questionize from the Common Core RI.x.8 progression, with the reasoning patterns and traps typical of younger readers (one example taken as a rule, an on-topic but irrelevant fact, a vivid detail mistaken for the main idea). `bin/rails questionize:seed_designs` queues practice for each design at each of its levels (`LEVELS=` to limit, `COUNT=` per design and level).

Designs taken only from adult tests carry adult traps; the seed designs cover what younger readers get wrong until their own answers can be measured. Released NAEP reading items (public domain) are the next source of school-level designs **[later]**.

**Age.** Questionize is for people 13 and older. Grades 3–5 is offered for a parent or teacher using it with a child. Accounts for children under 13 need verifiable parental consent (COPPA) and wait for teacher and parent accounts **[later]**.

**What a level does not change yet.** Every question still has five options. Three options for Grades 3–5 and four for SAT-style items need a schema change across the pipeline and the judge **[next]**.

## 5. Personalization

1. **For you [built].** `GET /api/v1/recommendations`: unanswered bank questions at the learner's level, on their two weakest skills, ordered by closeness to an item rating 150 below the learner's (about 70% expected success under Elo); new learners get questions near their overall rating. Each pick says why it was chosen.
2. **Practice on the same trap [built].** Every snapped question produces new questions built from its abstract design that set the same trap.
3. **Review list [built].** First misses on bank questions and snapped questions collect in My misses until archived.
4. **Spaced review [next].** A missed question comes back after 1, 3, 7 and 21 days; two spaced right answers archive it automatically.
5. **Level up [next].** When most skills at a level are mastered, suggest the next level, with a short placement set to confirm.

## 6. Quality measurement

What we measure, how, and the bar each part must clear. Most measures come from data the app already stores.

### 6.1 Items

| Measure | How | Bar |
|---|---|---|
| Verification | Blind solver agrees with the key; critic passes; Argument Judge ranks the key first in ≥ 90% of resamples with margin ≥ 0.15 | Required to publish **[built]** |
| Originality | Longest run copied from the source ≤ 12 words (8 for Snap fields) | Required **[built]** |
| Difficulty in use | Correct rate per item, by level | 30%–90% after 20 rated answers |
| Discrimination | Point-biserial between correctness and learners' skill ratings | ≥ 0.15 after 30 answers |
| Distractor health | Share of answers on each wrong option | Every distractor ≥ 3%; none above the key |
| Learner signal | Report rate and thumbs-down share | Reports trigger re-review **[built]**; thumbs-down > 40% after 10 votes queues review **[next]** |

### 6.2 Argument Judge

A gold set of questions adjudicated by people (`ai/eval/`). We report the judge's top-option accuracy against the key, agreement between the two judge models, and calibration (expected calibration error of the first-rate). Bar: ≥ 90% top-option accuracy on the gold set.

### 6.3 Snap (diagnosis)

On a sample of photographed questions checked by a person:

- transcription accuracy (character error rate of passage, stem and options) ≤ 2%;
- the likely answer matches the book's key ≥ 95%;
- the trap and misconception named are judged right ≥ 80%;
- practice questions set the same trap ≥ 80%.

### 6.4 Level fit

Readability (Flesch–Kincaid grade) of passages and explanations, computed per level, must fall in the level's band; the critic's level-mismatch reports per 100 items are tracked. Bar: ≥ 90% of items inside the band.

### 6.5 Personalization and learning

- Success rate on recommended questions: 60%–80%.
- Same-trap retest: on a learner's next question that offers the trap they fell for, the trap is chosen less often than their earlier rate.
- Skill rating change over 2 weeks for active learners, compared with learners who don't use recommendations.

## 7. Data and modeling approach

Psychometrics before machine learning: Elo now, Rasch / IRT per level offline when items have enough answers, Bayesian Knowledge Tracing per skill once answer sequences exist; recommendation rules evaluated by observed success before any learned recommender. The knowledge graph stays in PostgreSQL tables, similarity search uses pgvector in the same database, and generation improves through measured prompt and memory changes before any fine-tuning. Reasons in `DECISIONS.md` D1–D6; experiments in `research/`.

## 8. What is built and what is next

| Area | Built | Next | Later |
|---|---|---|---|
| Assessment | Elo per skill, provisional flags, trap and misconception counts | Strength/weakness labels with evidence, trap rates with intervals, mastery | Rasch calibration per level |
| Personalization | For you, same-trap practice, review list | Spaced review, level-up placement | Teacher-assigned sets |
| Levels | 7 levels in prompts, item level, Bank filter, level choice, fan-out from snapped designs, K-12 seed designs | 3- and 4-option formats | NAEP-derived designs; under-13 accounts with parental consent |
| Quality | Pipeline gates, reports, re-review, votes | Item statistics dashboard, readability check, gold-set report | Cross-level equating |
