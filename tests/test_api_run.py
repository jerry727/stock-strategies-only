import importlib
import sys
import types

from fastapi.testclient import TestClient


def _install_api_stubs():
    if "stock_strategies.evaluate" not in sys.modules:
        evaluate_module = types.ModuleType("stock_strategies.evaluate")
        evaluate_module.evaluate = lambda *_args, **_kwargs: None
        sys.modules["stock_strategies.evaluate"] = evaluate_module

    if "stock_strategies.notify" not in sys.modules:
        notify_module = types.ModuleType("stock_strategies.notify")
        notify_module.send_telegram = lambda *_args, **_kwargs: None
        notify_module.format_messages = lambda *_args, **_kwargs: []
        notify_module.build_notification_payload = lambda *_args, **_kwargs: {}
        notify_module.render_telegram_messages = lambda *_args, **_kwargs: []
        sys.modules["stock_strategies.notify"] = notify_module

    if "stock_strategies.loader" not in sys.modules:
        loader_module = types.ModuleType("stock_strategies.loader")
        loader_module.get_strategy = lambda strategy_id: {"id": strategy_id, "name": strategy_id, "params": {}}
        sys.modules["stock_strategies.loader"] = loader_module

    if "stock_strategies.performance" not in sys.modules:
        performance_module = types.ModuleType("stock_strategies.performance")
        performance_module.record_predictions = lambda *_args, **_kwargs: None
        performance_module.update_closed_positions = lambda *_args, **_kwargs: None
        performance_module.update_performance = lambda *_args, **_kwargs: None
        performance_module.summary = lambda *_args, **_kwargs: {}
        sys.modules["stock_strategies.performance"] = performance_module

    if "stock_strategies.market" not in sys.modules:
        market_module = types.ModuleType("stock_strategies.market")
        market_module.get_market_state = lambda: {"bullish": True}
        market_module.apply_market_filter = lambda results, market: 0
        sys.modules["stock_strategies.market"] = market_module

    if "stock_strategies.sheet" not in sys.modules:
        sheet_module = types.ModuleType("stock_strategies.sheet")
        sheet_module.read_watchlist = lambda: []
        sheet_module.append_signals = lambda *_args, **_kwargs: None
        sheet_module.write_results = lambda *_args, **_kwargs: None
        sheet_module.add_to_watchlist = lambda *_args, **_kwargs: None
        sheet_module.remove_from_watchlist = lambda *_args, **_kwargs: None
        sheet_module.read_latest_signals = lambda *_args, **_kwargs: []
        sheet_module.read_performance = lambda *_args, **_kwargs: []
        sheet_module.write_performance = lambda *_args, **_kwargs: None
        sys.modules["stock_strategies.sheet"] = sheet_module


_install_api_stubs()
api_main = importlib.import_module("api.main")
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


def test_api_run_accepts_watchlist_override(monkeypatch):
    monkeypatch.setattr(
        api_main.loader,
        "get_strategy",
        lambda sid: {"id": sid, "name": sid, "params": {}},
    )

    captured = {}

    def _fake_run_pipeline(**kwargs):
        captured.update(kwargs)
        return {
            "run_id": "run-override",
            "artifacts": {"json_path": "/tmp/run-override.json"},
            "summary": {"total": 1, "buy": 1, "watch": 0, "skip": 0, "error": 0},
            "strategy": {"id": kwargs["strategy_id"], "name": kwargs["strategy_id"]},
            "results": [],
        }

    monkeypatch.setattr(api_main, "run_pipeline", _fake_run_pipeline)
    response = client.post(
        "/api/run",
        json={
            "strategy_id": "default",
            "limit": 1,
            "watchlist": [{"stock_id": "2330", "name": "台積電", "category": "AI", "enabled": True}],
        },
    )
    assert response.status_code == 200
    assert captured["watchlist_override"][0]["stock_id"] == "2330"


def test_api_latest_run(monkeypatch):
    monkeypatch.setattr(api_main, "latest_run", lambda strategy_id=None: {"run_id": "latest-1"})
    response = client.get("/api/runs/latest")
    assert response.status_code == 200
    assert response.json()["run_id"] == "latest-1"
