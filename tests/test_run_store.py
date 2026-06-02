from pathlib import Path

from stock_strategies.run_store import (
    get_run_by_id,
    latest_run,
    list_runs,
    load_run_result,
    save_run_result,
)


def test_save_and_load_run_result(tmp_path, monkeypatch):
    monkeypatch.setenv("RUN_ARTIFACT_DIR", str(tmp_path))
    payload = {
        "run_id": "2026-06-02T14-30-00_default",
        "created_at": "2026-06-02T14:30:00+08:00",
        "strategy": {"id": "default", "name": "Default"},
        "summary": {"buy": 1, "watch": 2, "skip": 3, "error": 0, "total": 6},
        "results": [],
    }
    path = save_run_result(payload)
    loaded = load_run_result(path)
    assert Path(path).exists()
    assert loaded["run_id"] == payload["run_id"]
    assert loaded["artifacts"]["json_path"] == path


def test_latest_and_list_runs(tmp_path, monkeypatch):
    monkeypatch.setenv("RUN_ARTIFACT_DIR", str(tmp_path))
    save_run_result({
        "run_id": "run-1",
        "created_at": "2026-06-01T14:30:00+08:00",
        "strategy": {"id": "default", "name": "Default"},
        "summary": {},
        "results": [],
    })
    save_run_result({
        "run_id": "run-2",
        "created_at": "2026-06-02T14:30:00+08:00",
        "strategy": {"id": "default", "name": "Default"},
        "summary": {},
        "results": [],
    })
    latest = latest_run("default")
    runs = list_runs("default", limit=10)
    by_id = get_run_by_id("run-2")
    assert latest is not None
    assert latest["run_id"] == "run-2"
    assert len(runs) == 2
    assert by_id is not None
    assert by_id["run_id"] == "run-2"
