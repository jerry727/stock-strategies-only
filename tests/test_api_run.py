from fastapi.testclient import TestClient

import api.main as api_main


client = TestClient(api_main.app)


def test_api_run_returns_run_id(monkeypatch):
    monkeypatch.setattr(
        api_main.loader,
        "get_strategy",
        lambda sid: {"id": sid, "name": sid, "params": {}},
    )
    monkeypatch.setattr(
        api_main,
        "run_pipeline",
        lambda **kwargs: {
            "run_id": "run-123",
            "artifacts": {"json_path": "/tmp/run-123.json"},
            "summary": {"total": 0, "buy": 0, "watch": 0, "skip": 0, "error": 0},
            "strategy": {"id": kwargs["strategy_id"], "name": kwargs["strategy_id"]},
            "results": [],
        },
    )
    response = client.post("/api/run", json={"strategy_id": "default", "limit": 1})
    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == "run-123"
    assert data["artifacts"]["json_path"] == "/tmp/run-123.json"


def test_api_latest_run(monkeypatch):
    monkeypatch.setattr(api_main, "latest_run", lambda strategy_id=None: {"run_id": "latest-1"})
    response = client.get("/api/runs/latest")
    assert response.status_code == 200
    assert response.json()["run_id"] == "latest-1"
