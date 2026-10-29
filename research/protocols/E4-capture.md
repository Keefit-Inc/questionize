# E4: Capturing questions from photos and scans (v1)

- **Capability:** C1.1 extract, C1.2 reconstruct
- **Hypotheses:** H4a: structuring the page with the model from OCR text (or from the image where no OCR is available) gets every role of a text question right at least as often as layout rules, while also splitting the book's explanation by option. H4b: reading a phone photo directly with the model keeps the text within 2% character error. H4c (when figure items exist): a reconstruction of tables, charts, functions and geometric figures is solvable to the same answer as the original image for at least 95% of items.
- **Registered:** 2026-10-30, before any results were seen

## Dataset
- *Scan set:* the CR answer section of a prep book owned by the team, scanned (dataset `official-cr-v1`). Reference text: layout rules over Apple Vision OCR, with every field checked by a person on a random 20%, and all items flagged by either condition checked.
- *Photo set:* 30 of the same pages photographed on a phone, at an angle and in ordinary light.
- *Figure set (later):* 30 math or data items with a table, chart, function graph or geometric figure, from books the team owns.
No item text in the repository.

## Conditions
- **R:** OCR + layout rules (no model).
- **M-text:** OCR text → the primary model returns the structure as text fields.
- **M-image:** the image → the primary model returns the structure directly (what Snap does on a phone).
Same model, prompt hash and temperature in M conditions.

## Metrics
- **Primary:** share of items with every role correct (passage, stem, five options, key).
- **Secondary:** character error rate per field against the reference; key accuracy; explanation split by option correct; seconds and calls per page; for figures, solvability equivalence (same answer from the reconstruction as from the image, by the solver and by a person) and a faithfulness rating per element type.

## Analysis
Per-condition rates with Wilson 95% intervals; McNemar on paired item outcomes between conditions; CER as median and 90th percentile. Results reported separately for scans and photos.

## Human judgments
Andrew checks the reference on the sampled and flagged items against the printed page, and rates figure reconstructions (faithful / partly / not) blind to condition.

## Stopping rule and budget
One pass per condition over the scan set; the photo and figure sets when collected.

## Changes
