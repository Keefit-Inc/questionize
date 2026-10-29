# C1 Capture: extract and reconstruct

**Tasks.**
- *C1.1 Extract.* Find every part of the question in the photo and assign each its role: passage, stem, options, and any figure, table, graph, diagram, worked example or code; plus, when the photo shows them, the book's key and explanation, and which option the learner marked. The parts are not fixed in advance: a math question has a figure, a reading set has a long passage and line numbers, a data question has a table. The model has to know what a question can contain and recognize what this one does.
- *C1.2 Reconstruct.* Rebuild the question so it can be solved again without the photo: text exactly as printed; tables as tables; charts as their data; functions as formulas; geometric figures as the given measures and relations (and a drawing generated from them); anything that cannot be rebuilt faithfully is marked so, not guessed.

**Approach.** The model reads the page and returns the parts as structured fields; OCR, where available (Apple Vision or Tesseract offline), checks the text word by word, and a printed key checks the key. The structure is simple fields, not line coordinates. **Current:** the Snap reader handles text questions; the scan importer extracts text, key and explanation from answer sections; figures, tables and formulas are not yet reconstructed.

**Measures and bars.** Character error rate of the text (≤ 1% printed scans, ≤ 2% phone photos); share of items with every role right (≥ 98%); key read correctly (≥ 99%). For reconstruction, **solvability equivalence**: a solver given the reconstruction reaches the same answer as one given the original image, and a person judges the reconstruction faithful (≥ 95% of items with figures). Reported by element type (text, table, chart, function, geometry) and input (scan, phone photo).

**Where the field is.** Printed-text OCR is close to solved; document models turn academic pages into markup (Nougat, Blecher et al. 2023). Charts and diagrams are the hard part: on ChartQA (Masry et al. 2022) and MathVista (Lu et al., ICLR 2024) models still trail people, and MathVerse (Zhang et al., ECCV 2024) shows multimodal models often answer from the text while ignoring the diagram. Geometry problems can be parsed into a formal language of measures and relations and then solved (Inter-GPS, Lu et al. 2021), which is the form C1.2 targets.

**Experiments.** E4 (see [`../../protocols/`](../../protocols/)).

**Improvement history.** [`HISTORY.md`](HISTORY.md), generated from the ledger: every run that measured this capability, what changed, and the result against the bar.
