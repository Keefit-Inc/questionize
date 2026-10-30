import json

import pytest

from questionize.sync_cycles import append_records


def test_cycle_sync_is_append_only_idempotent_and_rejects_changed_published_records(tmp_path):
    path = tmp_path / "ledger.jsonl"
    original = '{"run_id":"old","protocol":"E1"}\n'
    path.write_text(original)
    row = {"run_id": "cycle-first", "protocol": "E8", "evaluation_scope": "regression", "summary": {}}
    assert append_records(path, [row]) == 1
    assert path.read_text().startswith(original)
    saved = path.read_bytes()
    assert append_records(path, [row]) == 0
    assert path.read_bytes() == saved
    with pytest.raises(ValueError, match="changed"):
        append_records(path, [dict(row, summary={"candidate": {"accuracy": 1}})])
    assert path.read_bytes() == saved


def test_cycle_sync_validates_every_row_before_writing(tmp_path):
    path = tmp_path / "ledger.jsonl"
    valid = {"run_id": "cycle-first", "protocol": "E8", "evaluation_scope": "regression"}
    with pytest.raises(ValueError):
        append_records(path, [valid, {"run_id": "not-a-cycle", "protocol": "E1"}])
    assert not path.exists()
