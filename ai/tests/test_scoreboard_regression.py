from questionize import scoreboard


def test_regression_cycles_do_not_replace_fresh_full_evaluations():
    full = {"run_id": "full", "protocol": "E1", "started_at": "1", "capabilities": ["C3.1"],
            "subject": "CR", "evaluation_scope": "full", "summary": {"B0": {"accuracy": .9, "n": 39}}}
    cycle = {"run_id": "cycle-test", "protocol": "E8", "started_at": "2", "capabilities": ["C3.1"],
             "subject": "CR", "evaluation_scope": "regression", "summary": {"candidate": {"accuracy": 1.0, "n": 35}}}
    board = scoreboard.render([full, cycle])
    assert "| C3.1 Solve | CR | full |" in board
    assert "| C3.1 Solve | CR | regression |" in board
    assert scoreboard.render_data([cycle])["runs"][0]["scope"] == "regression"
