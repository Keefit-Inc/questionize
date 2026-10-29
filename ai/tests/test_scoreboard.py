import json

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
    assert c3.index("baseline") < c3.index("memory from train split") and "B0+M 0.85" in c3
    assert "not measured yet" in (tmp_path / "capabilities" / "C1-capture" / "HISTORY.md").read_text()
