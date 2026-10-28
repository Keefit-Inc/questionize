# Questionize — Knowledge Model (draft)

The question bank's primary asset is not questions. It is the knowledge behind them: what learners at each stage need to master, the mistakes they predictably make and why, how good questions are built to reveal those mistakes, and how to teach past them. Questions are instances generated from this model; learner responses are the evidence that keeps it honest.

This document defines that model. `ARCHITECTURE.md` covers the services that run it.

```
            ┌─────────────────────────── evidence updates confidence ───────────────────────────┐
            ▼                                                                                   │
  Knowledge model                     Generation                     Learners                   │
  competencies · objectives   ──►   blueprint + context   ──►   attempts, choices,   ──►   Evidence
  misconceptions · traps            (article, theme)            time, ratings              (per blueprint,
  blueprints · teaching                    │                                                trap, misconception)
  progressions                             ▼
            ▲                         Item versions
            │
  Sources: own items, articles, teacher contributions, scanned print material
  (abstracted on the way in; no source wording, stimulus or answer set is kept)
```

## 1. Principles

1. **Ideas, not expression.** We record what a question measures and how it was designed: the objective, the misconception a distractor targets, the rule that makes the key correct, the features that drive difficulty. We never store a source's wording, stimulus, options or images. Every field is written in our own words at a level general enough that the source item cannot be reconstructed from it (§6).
2. **Hypotheses until evidenced.** Anything inferred by a model starts as a hypothesis with a confidence. It advances only through independent corroboration, expert review, or learner evidence (§5). The model is allowed to be wrong; it is not allowed to hide how sure it is.
3. **A neutral core with crosswalks at the edge.** Competencies sit on one developmental level scale. National curricula, grade systems, language frameworks and exams map onto that scale; none of them is the scale.
4. **Cognition, not just content.** Every misconception names its mechanism: a gap in knowledge, an over-generalized rule, a salience bias, working-memory overload. The same mechanism shows up across subjects, and naming it is what makes teaching transferable.
5. **Versioned, attributed, open.** Every node is versioned, every change has an author (human or agent), and the published model is licensed CC BY-SA 4.0. Numeric data derived from it (aggregate evidence, judge measurements) is released under CC0 so other open datasets can absorb it.
6. **Multilingual by design.** Canonical text is stored per language. Nodes that only exist in one language (a Korean particle rule, an English article rule) are tagged with that language; cross-language transfer errors are first-class misconceptions.

## 2. Level scale

A single ordinal scale of developmental stages. Typical ages are informative only; learners are placed by evidence, not age.

| Level | Typical stage | Typical age |
|---|---|---|
| L1–L2 | Early primary | 5–7 |
| L3–L4 | Primary | 7–9 |
| L5–L6 | Upper primary | 9–11 |
| L7–L8 | Lower secondary | 11–14 |
| L9–L10 | Upper secondary | 14–16 |
| L11–L12 | Pre-university | 16–18 |
| L13 | Undergraduate / general adult | 18+ |
| L14 | Graduate and professional admission (GMAT, LSAT, GRE level) | 21+ |

`framework_mappings` link a level and competency to external codes, for example a Common Core standard, a national curriculum achievement standard, a CEFR band, or an exam's skill area. A competency can map to many frameworks; a framework code can map to many competencies.

## 3. Entities

### 3.1 Subject and strand
`subject` (e.g. *Verbal reasoning*, *Mathematics*, *English as a second language*) → `strand` (e.g. *Argument analysis*, *Reading for detail*, *Proportional reasoning*).

### 3.2 Competency
A unit of capability that can be taught and measured.

| Field | Meaning |
|---|---|
| `key` | Stable slug, e.g. `vr.argument.identify-assumption` |
| `subject`, `strand` | Where it lives |
| `name`, `description` | Per language |
| `level_range` | Levels where it is typically taught and mastered, e.g. `L9–L14` |
| `can_do` | Observable statements per level ("At L11, identifies an unstated premise linking evidence to a causal conclusion in a 100-word argument") |
| `cognitive_process` | Revised Bloom: remember · understand · apply · analyze · evaluate · create |
| `knowledge_type` | factual · conceptual · procedural · metacognitive |
| `prerequisites` | Edges to other competencies, each with a strength (required / helpful) |
| `framework_mappings` | Crosswalk codes (§2) |

Competencies and prerequisite edges form the **competency graph**. A **learning progression** (§3.8) is a path through it.

### 3.3 Learning objective
A competency at a level, stated as a claim about the learner and the evidence that would support it (evidence-centered design).

| Field | Meaning |
|---|---|
| `competency`, `level` | |
| `claim` | "The learner can distinguish a necessary assumption from a merely supporting one" |
| `evidence` | Observable behavior that supports the claim ("rejects an option that strengthens the argument but is not required by it") |
| `success_criteria` | What counts as mastery (e.g. ≥ 70 % on calibrated items at this level) |

### 3.4 Misconception
A predictable way of being wrong, with its cause.

| Field | Meaning |
|---|---|
| `key`, `name` | e.g. `reasoning.necessary-vs-sufficient` |
| `statement` | What the learner does or believes ("treats a condition that would guarantee the conclusion as one the argument depends on") |
| `mechanism` | Family and type from the mechanism taxonomy below |
| `scope` | domain-specific or domain-general |
| `competencies` | Competencies it interferes with |
| `level_window` | Where it typically emerges, peaks and resolves, e.g. `{emerges: L7, peaks: L10, resolves: L13}` |
| `diagnostic_signals` | Response patterns that indicate it (which trap types the learner picks, time patterns) |
| `contrasts` | "Must not confuse" pairs (necessary vs sufficient; correlation vs causation) |
| `remediation` | Links to teaching strategies (§3.7) that address it |

**Mechanism taxonomy** (two levels; extensible):

| Family | Types |
|---|---|
| Knowledge | missing fact or definition · incomplete concept · wrong rule |
| Generalization | over-generalization · under-generalization · surface-feature matching |
| Attention and salience | salient-but-irrelevant detail · first-plausible-option anchoring · keyword matching |
| Logic | necessary/sufficient · converse/inverse · quantifier scope (some/all/most) · negation handling · causal from correlation · part/whole |
| Scope and language | scope shift · degree shift (likely → certain) · hedging ignored · L1 transfer |
| Processing | working-memory overload · procedural slip · reading the question, not the stem |
| Metacognitive | overconfidence · premature closure · not checking against the passage |

### 3.5 Trap pattern
How to build a wrong option that a learner holding a given misconception will choose. This is the reusable "asking know-how".

| Field | Meaning |
|---|---|
| `key`, `name` | e.g. `trap.cr.strengthener-posing-as-assumption` |
| `trap_type` | The item-level tag used on options (`out_of_scope`, `too_extreme`, `reversal`, `half_right`, `unsupported`, `irrelevant`, `distortion`, `grammar_error`, `changes_meaning`) |
| `targets` | Misconceptions it is designed to reveal |
| `construction_rule` | Abstract recipe ("state a fact that makes the conclusion more likely without being required by it; match the vocabulary of the conclusion") |
| `attractiveness_drivers` | What makes it tempting (shared keywords, plausible real-world truth, length parity with the key) |
| `fairness_guard` | What keeps it wrong for a nameable reason (it must not also be a defensible answer) |

### 3.6 Blueprint (task model)
The design of a family of questions. One blueprint generates many items across contexts.

| Field | Meaning |
|---|---|
| `key`, `version` | e.g. `bp.cr.assumption.necessary-gap` v3 |
| `objective` | The learning objective it gathers evidence for |
| `level_band` | e.g. `L11–L14` |
| `format` | Five-option multiple choice, numeric entry, ordering… |
| `stimulus_spec` | Genre, length, required features ("argument with one premise, one conclusion, and a gap between them; conclusion stated, not hedged") |
| `stem_patterns` | Abstract stem forms ("The argument relies on which assumption?") — generic phrasings, never a source's wording |
| `key_rule` | What makes the correct answer correct ("negating it breaks the link between premise and conclusion") |
| `distractor_slots` | Ordered slots, each a trap pattern plus a construction note |
| `difficulty_drivers` | Features with direction and rough effect ("gap phrased abstractly: harder"; "a distractor reuses conclusion wording: harder"; "stimulus > 120 words: harder") |
| `ambiguity_risks` | Known ways the design produces two defensible answers, and the guard against each |
| `variation_axes` | What can vary while staying the same blueprint (topic, polarity, causal vs conditional link) |
| `teaching_notes` | What a teacher should say after the learner answers |
| `prerequisite_blueprints` | Easier blueprints that should be mastered first |

### 3.7 Teaching strategy
How to teach a competency at a level, and how to repair each misconception.

| Field | Meaning |
|---|---|
| `competency`, `level_band` | |
| `sequence` | Ordered steps (concept → worked example → guided practice → mixed practice) |
| `explanation_approach` | e.g. "negation test before formal logic", "contrast pairs" |
| `worked_example_pattern` | The shape of a good worked example, not a specific one |
| `misconception_feedback` | For each misconception: the feedback that addresses its mechanism |
| `practice_progression` | Which blueprints to practice in which order |

### 3.8 Learning progression (roadmap)
An ordered set of milestones for a subject across levels. Each milestone lists competencies, entry criteria (evidence from prerequisite objectives) and exit criteria. A learner's roadmap is the progression with their own evidence overlaid.

### 3.9 Source observation (provenance)
One extraction from one source item. It is the only record that touches a source, and it holds only abstract fields.

| Field | Meaning |
|---|---|
| `source_kind` | `own_item` · `article` · `teacher_contribution` · `print_scan` · `public_domain` |
| `source_ref` | Opaque reference (keyed hash of the bibliographic identifier and position). Not published. Used to count independent sources and to honor removal requests |
| `language`, `region`, `stated_level` | As given by the source (e.g. "Grade 8"), mapped to the level scale |
| `observed` | Abstract fields: objective, blueprint features, misconceptions and trap patterns per option, difficulty drivers |
| `extractor` | Model and prompt version |
| `confidence` | Per field |
| `leak_checks` | Results of the checks in §6 |

### 3.10 Evidence
Aggregated from attempts on items generated from a blueprint (never from a single learner's identity).

| Measure | Used for |
|---|---|
| Item difficulty by learner rating band | Calibrating `difficulty_drivers` and `level_band` |
| Discrimination (do stronger learners get it right more often?) | Detecting broken or ambiguous items |
| Distractor selection rate by rating band | Testing whether a trap pattern attracts the learners it targets |
| Misconception prevalence curve by level | Estimating `level_window` |
| Response time profile | Separating careless slips from real misconceptions |

## 4. How items use the model

An item version records the blueprint version it came from, the objective it measures, and for every option its trap pattern and the misconception it targets. Generation takes a blueprint plus a context (an article, a theme) and produces an item that follows the blueprint's rules; verification (blind solver, critic) checks it before it ships. So every learner choice is also a data point about a misconception, not just a right or wrong answer.

## 5. Lifecycle and evolution

Every knowledge node (competency, misconception, trap pattern, blueprint, strategy) carries a status:

| Status | Advances when |
|---|---|
| `hypothesis` | Created by extraction or proposal |
| `corroborated` | Independently observed in ≥ 3 sources, or approved by a verified educator |
| `evidenced` | Learner data supports it (e.g. a trap pattern's selection rate falls as rating rises, across ≥ 200 attempts on ≥ 5 items) |
| `canonical` | Evidenced and stable across languages or regions |
| `disputed` / `deprecated` | Evidence contradicts it, or it is merged into another node |

Evolution operations, all versioned with redirects:

- **Merge** duplicate nodes found by embedding similarity and confirmed by review.
- **Split** a node when evidence shows two populations (a misconception that peaks at different levels in different languages).
- **Re-level** when the prevalence curve or difficulty calibration moves.
- **Propose** edits as a user; educators and high-rated learners in the competency review them, and the evidence decides disputes.

## 6. Extraction from sources

For any source, including a scanned page:

1. **Hold in memory only.** The image and any transcription live for the duration of the request and are then discarded.
2. **Reject what we never accept.** Live or recalled exam content and personal data stop the run.
3. **Extract abstractly.** Agents infer the objective, blueprint features, the misconception and trap pattern behind each option, and difficulty drivers, writing every field in their own general terms.
4. **Leak checks before anything is stored:**
   - no field shares a run of more than a few consecutive words with the transcription;
   - a reconstruction test: a separate model tries to rebuild the source item from the observation alone; if the result is close to the source, the observation is generalized further or dropped;
   - no proper names, numbers or scenario details from the source stimulus.
5. **Match and merge.** The observation is linked to existing nodes, or proposes new `hypothesis` nodes.
6. **Publish by corroboration.** Nodes derived only from print scans become public when corroborated by independent sources or rewritten through review, so no published node maps one-to-one onto a single source item.
7. **Honor removal.** `source_ref` lets us find and remove every observation from a given source on request.

## 7. Storage (PostgreSQL, owned by Rails)

| Table | Notes |
|---|---|
| `subjects`, `strands` | |
| `levels`, `framework_mappings` | Crosswalk codes per competency and level |
| `competencies`, `competency_edges` | Graph; `kind` = required / helpful |
| `objectives` | |
| `misconceptions`, `misconception_competencies` | |
| `trap_patterns`, `trap_pattern_targets` | |
| `blueprints`, `blueprint_versions` | Structured specs in `jsonb`; `version` increments on change |
| `teaching_strategies`, `progressions`, `progression_milestones` | |
| `source_observations` | Abstract fields only; `source_ref` is a keyed hash |
| `node_status_events` | Status history with reason and evidence snapshot |
| `evidence_snapshots` | Periodic aggregates per blueprint version, trap pattern, misconception |
| `knowledge_proposals`, `knowledge_reviews` | Community edits |
| `translations` | Per-language text for any node |
| embeddings (`pgvector`) | On names and descriptions, for dedupe and retrieval |

`item_versions` gain `blueprint_version_id`, `objective_id`, and per-option `{trap_pattern_id, misconception_id}` inside `rationales`.

## 8. Two domains and their boundary

| | Knowledge domain | Learner domain |
|---|---|---|
| Purpose | Accumulate and validate what is worth learning and how to teach and assess it | Diagnose and grow each learner |
| Holds | Competencies, misconceptions, trap patterns, blueprints, strategies, evidence | Attempts, ratings, trap profiles, roadmaps, rankings, games |
| Data | Shared asset: descriptive content CC BY-SA, numeric data CC0 | Personal, private |
| Receives | Anonymous, aggregated evidence only | Blueprints and items |

The knowledge domain never sees an individual learner. Evidence crosses the boundary only as aggregates over enough learners that no one can be singled out. In Rails the two live in separate namespaces (`Knowledge::`, `Learning::`) and talk through that interface, so the knowledge domain can later be published or hosted on its own.

Learner-domain features are designed to double as measurement. A game where learners name the trap behind each wrong option trains metacognition and, in aggregate, tests whether a trap pattern reads the way the model says it does; rated challenges put many learners on the same items, which calibrates them quickly.

## 9. Error log: personal and commons layers for uploaded material

Learners bring their own study material through an **error log**. While working in a book they own, a learner photographs one question they got wrong (or are stuck on). The original never stays with us; what stays is where the question lives and what went wrong. One pass produces two outputs:

1. **Personal layer**, for that learner only:
   - an error-log entry that records the question's *location* (book title or ISBN, page, question number), the learner's choice, and the diagnosis, but none of the question's text;
   - what the question measures, the trap behind the chosen option and the misconception it points to;
   - new practice items generated from the matching blueprint that target the same trap (never the original item). They are original questions written from the abstract design, so once verified they join the shared bank for everyone, where learners rate them;
   - an updated weakness map and review schedule across everything the learner has logged.

   - on the learner's **own device only**, the question word for word (passage, stem and options), so they can solve it again. The service reads it from the photo, hands it to that device once, and deletes its copy as it is read (it waits in a short-lived cache, never in a table, a log or the run's stored events). The photo itself is not kept anywhere once the question is read.

   Entries are private and never shared or published.
2. **Commons layer:** abstract observations only (§3.9), through the leak checks in §6, entering the knowledge model as hypotheses and published only after corroboration. Questions people actually miss, and the options they actually pick, are the densest evidence the knowledge model gets.

Rules:

- One question per capture, started by the learner on material they own. A capture may hold up to three photos when one question spans pages (a passage on one page, the question on the next); the learner crops each to the question first. There is no bulk or whole-book upload, and the service does not scan or collect material on anyone's behalf.
- The service keeps no copy of the image, transcription or options. The images are deleted as soon as they are read; the transcription goes once to the learner's device and is then deleted. Only the location reference, the learner's answer and the abstract diagnosis are stored on the server.
- Nothing on the service reproduces, re-displays or imitates a specific publication for anyone else (no shared copies, no "more questions like chapter 7 of book X"). The only copy of a question is the one on the device of the learner who photographed it.
- Material from test makers' official guides is flagged and handled conservatively; live or recalled exam content is rejected.
- Contributing observations to the commons is explained up front, and the learner can see the knowledge nodes their contributions helped corroborate.
- Personal data in an image (names, handwriting, school details) is not extracted.
- At launch, captures are available in the United States only, to users 13 and older.

This is the intake pattern for every subject pack (§10): Critical Reasoning first, the same error-log flow for each subject added later.

## 10. Subject packs, with Critical Reasoning as the reference

A subject joins the platform as a pack with a fixed contract. Critical Reasoning is the reference implementation that proves every part of the loop end to end.

| Pack part | Critical Reasoning (reference) | Examples elsewhere |
|---|---|---|
| Competency seed and level crosswalk | Argument analysis, L11–L14 | Proportional reasoning, L5–L9 |
| Subject misconceptions (extending the shared mechanism taxonomy) | Necessary vs sufficient, scope shift | Additive reasoning applied to ratios |
| Item formats | Five-option multiple choice | Numeric entry, worked solution, ordering |
| Verification strategy | Blind solver plus critic | Symbolic check of the answer; for logic games, a program that enumerates every valid arrangement and proves the key is the only answer |
| Rendering components | Passage and options | Math notation, arrangement board |

Verification sits behind one interface so each subject can use the strongest check available to it.

## 11. First slice (hackathon scope)

- **Subject:** verbal reasoning. **Strands:** argument analysis (Critical Reasoning) and reading for inference (Reading Comprehension). **Levels:** L11–L14.
- **Seed:** about 25 competencies with prerequisites, 40 misconceptions, 20 trap patterns, 30 blueprints, written and reviewed by hand with agent assistance.
- **Extraction:** from articles and from questions users write themselves; the print-scan path is demonstrated on our own or public-domain material.
- **Generation:** the pipeline takes a blueprint plus an article instead of a free-form sub-type.
- **Evidence view:** per blueprint and trap pattern, selection rates by rating band as attempts arrive.

## 12. Example (abridged)

```json
{
  "key": "bp.cr.assumption.necessary-gap",
  "version": 1,
  "status": "hypothesis",
  "objective": {
    "competency": "vr.argument.identify-assumption",
    "level": "L13",
    "claim": "Distinguishes an assumption the argument requires from one that merely supports it",
    "evidence": "Rejects an option that strengthens the argument but whose negation leaves it intact"
  },
  "level_band": "L11-L14",
  "stimulus_spec": {
    "genre": "argument",
    "length_words": [60, 120],
    "features": ["one stated conclusion", "one or two premises", "a single gap between premise and conclusion"]
  },
  "stem_patterns": ["The argument relies on which of the following assumptions?"],
  "key_rule": "Negating the correct option breaks the link between the premises and the conclusion",
  "distractor_slots": [
    { "trap_pattern": "trap.cr.strengthener-posing-as-assumption", "targets": ["reasoning.necessary-vs-sufficient"] },
    { "trap_pattern": "trap.generic.conclusion-keyword-echo", "targets": ["attention.keyword-matching"] },
    { "trap_pattern": "trap.generic.degree-shift", "targets": ["scope.degree-shift"] },
    { "trap_pattern": "trap.generic.out-of-scope-comparison", "targets": ["scope.scope-shift"] }
  ],
  "difficulty_drivers": [
    { "feature": "gap stated abstractly rather than concretely", "direction": "harder" },
    { "feature": "strengthener distractor uses the conclusion's vocabulary", "direction": "harder" },
    { "feature": "key phrased as a negative", "direction": "harder" }
  ],
  "ambiguity_risks": [
    { "risk": "a strengthener that is also nearly necessary", "guard": "apply the negation test to every option during review" }
  ],
  "teaching_notes": "Teach the negation test: an assumption is required if denying it makes the argument fall apart."
}
```
