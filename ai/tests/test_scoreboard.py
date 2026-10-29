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
