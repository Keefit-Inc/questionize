import json

import pytest

from questionize import scoreboard


def test_scoreboard_shows_the_latest_valid_run_per_capability(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    runs = [
        {"run_id": "r1", "protocol": "E1", "capabilities": ["C3.1"], "started_at": "2026-10-31T01", "models": {"primary": "m"},
         "summary": {"B0": {"accuracy": 0.8, "ci95": [0.7, 0.9], "n": 60}}},
        {"run_id": "r2", "protocol": "E1", "capabilities": ["C3.1"], "started_at": "2026-10-31T02", "models": {"primary": "m"},
         "summary": {"B0": {"accuracy": 0.5, "n": 60}}},
        {"invalidates": "r2", "reason": "wrong dataset"},
    ]
    ledger.write_text("\n".join(json.dumps(r) for r in runs) + "\n")
    board = scoreboard.render(scoreboard.load(ledger))
    row = next(line for line in board.splitlines() if line.startswith("| C3.1"))
    assert "B0 0.80 [0.70, 0.90] (n=60)" in row and "r1" in row
    assert "| C1.1 Capture: extract |" in board and "not measured yet" in board


def test_histories_are_written_per_capability_folder(tmp_path):
    (tmp_path / "results").mkdir()
    for name in ("C1-capture", "C3-solve-explain"):
        (tmp_path / "capabilities" / name).mkdir(parents=True)
    rows = [
        {"run_id": "a", "protocol": "E1", "capabilities": ["C3.1", "C3.2"], "started_at": "2026-10-31T01", "models": {"p": "m"},
         "note": "baseline", "summary": {"B0": {"accuracy": 0.8, "n": 40}}},
        {"run_id": "b", "protocol": "E1", "capabilities": ["C3.1"], "started_at": "2026-10-31T02", "models": {"p": "m"},
         "note": "memory from train split", "summary": {"B0+M": {"accuracy": 0.85, "n": 40}}},
    ]
    scoreboard.write_all(rows, tmp_path)
    c3 = (tmp_path / "capabilities" / "C3-solve-explain" / "HISTORY.md").read_text()
    assert c3.index("baseline") < c3.index("memory from train split") and "B0+M 0.85" in c3 and "| CR |" in c3
    assert "not measured yet" in (tmp_path / "capabilities" / "C1-capture" / "HISTORY.md").read_text()


def test_scoreboard_keeps_subjects_apart():
    rows = [
        {"run_id": "cr", "protocol": "E1", "capabilities": ["C3.1"], "started_at": "1", "models": {}, "summary": {"B0": {"accuracy": 0.9}}},
        {"run_id": "geo", "protocol": "E1", "subject": "math-geometry", "capabilities": ["C3.1"], "started_at": "2", "models": {},
         "summary": {"B0": {"accuracy": 0.6}}},
    ]
    board = scoreboard.render(rows)
    assert "| C3.1 Solve | CR |" in board and "| C3.1 Solve | math-geometry |" in board and "B0 0.90" in board


def test_explanation_accuracy_is_not_inferred_from_solving_accuracy():
    run = {"run_id": "solve", "protocol": "E1", "capabilities": ["C3.1", "C3.2"], "started_at": "1",
           "summary": {"B0": {"accuracy": 1.0, "n": 5, "ci95": [0.57, 1.0]}}}
    board = scoreboard.render([run])
    solve = next(line for line in board.splitlines() if line.startswith("| C3.1"))
    explain = next(line for line in board.splitlines() if line.startswith("| C3.2"))
    assert "B0 1.00" in solve
    assert "not measured yet" in explain and "B0 1.00" not in explain
    assert scoreboard.render_data([run])["runs"][0]["measured_capabilities"] == ["C3.1"]


def test_trials_do_not_replace_full_evaluations_and_both_remain_in_history():
    full = {"run_id": "full", "protocol": "E1", "capabilities": ["C3.1"], "started_at": "1",
            "n_items": 39, "note": "baseline, test split", "summary": {"B0": {"accuracy": 0.9487, "n": 39}}}
    trial = {"run_id": "trial", "protocol": "E1", "capabilities": ["C3.1"], "started_at": "2",
             "n_items": 5, "note": "trial: memory from train split", "summary": {"B0+M": {"accuracy": 1.0, "n": 5}}}
    board = scoreboard.render([trial, full])
    assert "| C3.1 Solve | CR | full |" in board
    assert "| C3.1 Solve | CR | trial |" in board
    assert board.index("B0 0.9487") < board.index("B0+M 1.00")
    assert "B0 0.95 " not in board  # 37/39 must not round up to the 95% bar
    history = scoreboard.history([trial, full], "C3")
    assert history.index("| full | full |") < history.index("| trial | trial |")
    assert scoreboard.scope_of({"note": "trial", "evaluation_scope": "full"}) == "full"
    assert scoreboard.scope_of({"n_items": 3}) == "full"


def test_explanation_metrics_keep_their_own_rated_count_and_interval():
    summary = {"B0": {"accuracy": 1.0, "n": 39, "ci95": [0.9, 1.0],
                       "explanation_correctness": 0.8, "explanation_correctness_n": 10,
                       "explanation_correctness_ci95": [0.5, 0.95]}}
    assert scoreboard.headline(summary, "C3.2") == "B0 0.80 [0.50, 0.95] (n=10)"
    del summary["B0"]["explanation_correctness_n"]
    del summary["B0"]["explanation_correctness_ci95"]
    assert scoreboard.headline(summary, "C3.2") == "B0 0.80 (n=?)"


def test_scoped_primary_metric_is_allowed_but_ambiguous_primary_is_not():
    result = {"primary": 0.99, "accuracy": 0.8, "n": 39,
              "capability_metrics": {"C3.2": {"value": 0.7, "n": 20, "ci95": [0.5, 0.85]}}}
    assert scoreboard.metric_for(result, "C3.1")["value"] == 0.8
    assert scoreboard.metric_for(result, "C3.2")["value"] == 0.7
    assert scoreboard.metric_for(result, "C4") is None
    result["capability_metrics"] = None
    assert scoreboard.metric_for(result, "C3.2") is None


def test_dashboard_export_is_deterministic_aggregate_only_and_preserves_comparison_context():
    baseline = {"run_id": "baseline", "protocol": "E1", "protocol_version": 2, "started_at": "1",
                "capabilities": ["C3.1", "C3.2"], "dataset_id": "d", "dataset_hash": "dataset-a",
                "prompts_hash": "prompts-a", "split": "test", "n_items": 39, "models": {"primary": "model-a"},
                "summary": {"B0": {"accuracy": 0.9, "n": 39, "calls": 39, "ece": 0.04}}}
    memory = {"run_id": "memory", "protocol": "E1", "protocol_version": 2, "started_at": "2",
              "capabilities": ["C3.1", "C3.2"], "dataset_id": "d", "dataset_hash": "dataset-a",
              "prompts_hash": "prompts-b", "split": "test", "n_items": 39, "models": {"primary": "model-a"},
              "memory": {"hash": "memory-a", "lessons": 48, "rules": ["PRIVATE RULE"]}, "baseline_run": "baseline",
              "results": [{"question": "PRIVATE QUESTION"}], "path": "/private/outputs", "token": "PRIVATE TOKEN",
              "summary": {"B0+M": {"accuracy": 0.95, "n": 38, "calls": 38,
                                      "explanation": "PRIVATE EXPLANATION",
                                      "vs_baseline": {"b": 1, "c": 2, "p": 1.0, "baseline_accuracy": 0.9,
                                                      "diff_ci95": [-0.05, 0.1], "private": "PRIVATE COMPARISON"}}}}
    data = scoreboard.render_data([memory, baseline])
    assert data == scoreboard.render_data([baseline, memory])
    assert data["schema_version"] == 1 and data["subjects"] == ["CR"]
    assert [r["run_id"] for r in data["runs"]] == ["baseline", "memory"]
    assert data["runs"][1]["prompts_hash"] == "prompts-b"
    assert data["runs"][1]["memory"] == {"hash": "memory-a", "lessons": 48}
    result = data["records"][1]
    assert result["n"] == 38 and result["expected_n"] == 39 and result["complete"] is False
    assert result["vs_baseline"] == {"b": 1, "c": 2, "p": 1.0, "baseline_accuracy": 0.9, "diff_ci95": [-0.05, 0.1]}
    assert all(r["capability"] == "C3.1" for r in data["records"])
    serialized = json.dumps(data)
    assert "PRIVATE" not in serialized and "/private/outputs" not in serialized


def test_dashboard_json_is_generated_with_reports(tmp_path):
    files = scoreboard.write_all([], tmp_path)
    assert tmp_path / "results" / "dashboard.json" in files
    data = json.loads((tmp_path / "results" / "dashboard.json").read_text())
    assert data["schema_version"] == 1 and data["runs"] == [] and data["updated_at"] is None


def test_command_typo_cannot_replace_reports_with_an_empty_ledger(tmp_path, monkeypatch):
    def should_not_write(*args):
        pytest.fail("An invalid ledger path must not rewrite the existing reports")

    monkeypatch.setattr(scoreboard, "write_all", should_not_write)
    with pytest.raises(SystemExit, match="Usage"):
        scoreboard.main(["cd", ".."])
    with pytest.raises(SystemExit, match="reports were not changed"):
        scoreboard.main([str(tmp_path / "missing.jsonl")])


def test_qualifications_match_dataset_and_exact_protocol_version_without_changing_results():
    definitions = {"schema_version": 1, "qualifications": [
        {"id": "capture", "applies_to": {"dataset_hash": "dataset-a"}, "summary": "Capture verification pending."},
        {"id": "method", "applies_to": {"protocol": "E1", "protocol_version": 2}, "summary": "Method requires review."},
    ]}
    base = {"run_id": "baseline", "protocol": "E1", "protocol_version": 2, "dataset_hash": "dataset-a",
            "capabilities": ["C3.1"], "n_items": 39, "summary": {"B0": {"n": 39, "accuracy": .9487}}}
    memory = base | {"run_id": "memory", "summary": {"B0+M": {"n": 39, "accuracy": .9487, "vs_baseline": {"b": 0, "c": 0, "p": 1, "diff_ci95": [0, 0]}}}}
    rows = [base, memory, base | {"run_id": "v3", "protocol_version": 3}, base | {"run_id": "new-data", "dataset_hash": "dataset-b"}]
    data = scoreboard.render_data(rows, definitions)
    by_id = {r["run_id"]: r for r in data["runs"]}
    assert [q["id"] for q in by_id["baseline"]["qualifications"]] == ["capture", "method"]
    assert [q["id"] for q in by_id["v3"]["qualifications"]] == ["capture"]
    assert [q["id"] for q in by_id["new-data"]["qualifications"]] == ["method"]
    record = next(r for r in data["records"] if r["run_id"] == "memory")
    assert record["value"] == .9487 and record["vs_baseline"]["diff_ci95"] == [0, 0]
    assert len(data["runs"]) == len(rows)


def test_qualifications_are_explicit_deterministic_and_safely_projected(monkeypatch):
    from pathlib import Path

    def no_reads(*args, **kwargs):
        pytest.fail("render_data must not read annotation or private files")

    monkeypatch.setattr(Path, "read_text", no_reads)
    run = {"run_id": "run", "protocol": "E1", "protocol_version": 2, "dataset_hash": "dataset-a",
           "capabilities": ["C3.1"], "qualifications": [{"summary": "PRIVATE ROW QUALIFICATION"}],
           "summary": {"B0": {"n": 39, "accuracy": .9487}}}
    report = "https://github.com/Keefit-Inc/questionize/blob/main/research/results/E1.md"
    entries = [
        {"id": "z", "applies_to": {"protocol": "E1", "protocol_version": 2}, "summary": "Public method note.", "report_url": report,
         "path": "/private/report", "question": "PRIVATE QUESTION"},
        {"id": "a", "applies_to": {"dataset_hash": "dataset-a"}, "summary": "Public capture note.", "report_url": "file:///private/report"},
        {"id": "bad-selector", "applies_to": {"protocol": "E1"}, "summary": "PRIVATE UNDERQUALIFIED NOTE"},
    ]
    assert scoreboard.render_data([run])["runs"][0]["qualifications"] == []
    data = scoreboard.render_data([run], {"schema_version": 1, "qualifications": entries})
    assert data == scoreboard.render_data([run], {"schema_version": 1, "qualifications": list(reversed(entries))})
    assert data["runs"][0]["qualifications"] == [
        {"id": "a", "summary": "Public capture note."},
        {"id": "z", "summary": "Public method note.", "report_url": report},
    ]
    assert "PRIVATE" not in json.dumps(data) and "/private/" not in json.dumps(data)


def test_public_qualification_file_is_loaded_for_generated_reports_and_dashboard(tmp_path):
    definitions = {"schema_version": 1, "qualifications": [
        {"id": "capture", "applies_to": {"dataset_hash": "dataset-a"}, "summary": "Capture verification pending."},
    ]}
    qualification_file = tmp_path / "qualifications.json"
    qualification_file.write_text(json.dumps(definitions))
    source = qualification_file.read_bytes()
    (tmp_path / "capabilities/C3-solve-explain").mkdir(parents=True)
    rows = [{"run_id": "run", "protocol": "E1", "dataset_hash": "dataset-a", "capabilities": ["C3.1"], "summary": {"B0": {"accuracy": .9487, "n": 39}}}]
    scoreboard.write_all(rows, tmp_path)
    assert qualification_file.read_bytes() == source
    data = json.loads((tmp_path / "results/dashboard.json").read_text())
    assert data["runs"][0]["qualifications"] == [{"id": "capture", "summary": "Capture verification pending."}]
    board = (tmp_path / "results/SCOREBOARD.md").read_text()
    history = (tmp_path / "capabilities/C3-solve-explain/HISTORY.md").read_text()
    assert "provisional" in board and "Capture verification pending." in board
    assert "B0 0.9487" in board and "provisional" in history


def test_invalid_qualification_schema_cannot_replace_existing_reports(tmp_path):
    (tmp_path / "results").mkdir()
    target = tmp_path / "results/SCOREBOARD.md"
    target.write_text("Existing report")
    (tmp_path / "qualifications.json").write_text('{"schema_version": 99, "qualifications": []}')
    with pytest.raises(ValueError, match="Unsupported qualifications schema"):
        scoreboard.write_all([], tmp_path)
    assert target.read_text() == "Existing report"
