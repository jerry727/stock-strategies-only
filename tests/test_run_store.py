import importlib
import sys
import types
from pathlib import Path


def _install_main_stubs():
    if "gspread" not in sys.modules:
        sys.modules["gspread"] = types.SimpleNamespace(service_account_from_dict=lambda *_args, **_kwargs: None)

    if "google.oauth2.service_account" not in sys.modules:
        service_account_module = types.ModuleType("google.oauth2.service_account")

        class _Credentials:
            @classmethod
            def from_service_account_info(cls, *_args, **_kwargs):
                return cls()

            def with_scopes(self, _scopes):
                return self

        service_account_module.Credentials = _Credentials
        sys.modules["google.oauth2.service_account"] = service_account_module
        google_oauth2_module = types.ModuleType("google.oauth2")
        google_oauth2_module.service_account = service_account_module
        sys.modules.setdefault("google.oauth2", google_oauth2_module)
        google_module = sys.modules.setdefault("google", types.ModuleType("google"))
        google_module.oauth2 = google_oauth2_module

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


_install_main_stubs()
main_module = importlib.import_module("main")

save_run_result = main_module.save_run_result
load_run_result = importlib.import_module("stock_strategies.run_store").load_run_result
latest_run = importlib.import_module("stock_strategies.run_store").latest_run
list_runs = importlib.import_module("stock_strategies.run_store").list_runs
get_run_by_id = importlib.import_module("stock_strategies.run_store").get_run_by_id
run_pipeline = main_module.run_pipeline


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


def test_run_pipeline_without_google_creds_when_side_effects_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("RUN_ARTIFACT_DIR", str(tmp_path))
    monkeypatch.delenv("GOOGLE_CREDS_JSON", raising=False)
    monkeypatch.delenv("GOOGLE_SHEET_ID", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.delenv("FINMIND_TOKEN", raising=False)

    import main as main_module

    monkeypatch.setattr(main_module.loader, "get_strategy", lambda strategy_id: {"id": strategy_id, "name": strategy_id, "params": {}})
    monkeypatch.setattr(main_module, "read_watchlist", lambda: [{"stock_id": "2330", "name": "台積電", "category": "AI", "enabled": True}])
    monkeypatch.setattr(main_module, "get_market_state", lambda: {"bullish": True, "note": "測試模式"})
    monkeypatch.setattr(main_module, "apply_market_filter", lambda results, market: 0)
    monkeypatch.setattr(main_module, "evaluate", lambda stock_id, name, strategy=None: {
        "stock_id": stock_id,
        "name": name,
        "date": "2026-06-02",
        "strategy_id": strategy["id"],
        "strategy_meta": {"id": strategy["id"], "name": strategy["name"], "params": strategy.get("params", {})},
        "risk_notes": [],
        "action": "BUY",
        "signal_score": 72.5,
        "components": {"fundamental_pass": True, "tech_score": 75, "tech_signals": [], "backtest_winrate": 0.68, "backtest_samples": 12, "volume_patterns": [], "volume_details": {}, "volume_bonus": 0, "volume_verdict": "量價健康"},
        "explain": {"gate_checks": {"fundamental_pass": True, "tech_score_pass": True, "total_score_pass": True}, "buy_reasons": ["基本面達標"], "watch_reasons": [], "skip_reasons": []},
        "trend": {"chg_5d": 3.8, "chg_20d": 8.2, "vol_ratio": 1.3, "pct_from_high": -5.0, "above_ma20": True, "above_ma60": True},
        "entry_price": 1000,
        "stop_loss_price": 920,
        "target_price": 1100,
        "risk_reward_ratio": 1.25,
        "position_size_pct": 20.0,
        "entry_rule": "明日以開盤價進場",
    })

    result = run_pipeline(
        strategy_id="default",
        limit=1,
        send_notifications=False,
        write_sheet_enabled=False,
        write_performance_enabled=False,
        watchlist_override=[{"stock_id": "2330", "name": "台積電", "category": "AI", "enabled": True}],
    )
    assert result["summary"]["total"] == 1
    assert result["summary"]["buy"] == 1
    assert Path(result["artifacts"]["json_path"]).exists()
