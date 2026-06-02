from stock_strategies.notify import build_notification_payload, render_telegram_messages


def test_build_notification_payload_returns_structured_summary():
    signals = [
        {"stock_id": "2330", "name": "台積電", "action": "BUY", "signal_score": 72, "components": {}, "trend": {}},
        {"stock_id": "2308", "name": "台達電", "action": "WATCH", "signal_score": 58, "components": {}, "trend": {}},
    ]
    payload = build_notification_payload(signals, watchlist=[], market={"note": "大盤偏多"})
    assert payload["summary"]["buy"] == 1
    assert payload["summary"]["watch"] == 1
    assert "top_buys" in payload
    assert payload["market"]["note"] == "大盤偏多"


def test_render_telegram_messages_returns_list_of_strings():
    payload = {
        "date": "2026/06/02",
        "signals": [
            {"stock_id": "2330", "name": "台積電", "action": "BUY", "signal_score": 72, "components": {"tech_signals": [], "backtest_winrate": 0.7}, "trend": {"chg_5d": 1.0, "chg_20d": 2.0, "pct_from_high": -3.0, "above_ma20": True, "above_ma60": True, "vol_ratio": 1.2}, "entry_price": 100, "stop_loss_price": 92, "target_price": 110, "risk_reward_ratio": 1.25, "position_size_pct": 20},
        ],
        "watchlist": [],
        "market": {"note": "大盤偏多"},
        "summary": {"total": 1, "buy": 1, "watch": 0, "skip": 0},
        "top_buys": [
            {"stock_id": "2330", "name": "台積電", "action": "BUY", "signal_score": 72, "components": {"tech_signals": [], "backtest_winrate": 0.7}, "trend": {"chg_5d": 1.0, "chg_20d": 2.0, "pct_from_high": -3.0, "above_ma20": True, "above_ma60": True, "vol_ratio": 1.2}, "entry_price": 100, "stop_loss_price": 92, "target_price": 110, "risk_reward_ratio": 1.25, "position_size_pct": 20}
        ],
    }
    msgs = render_telegram_messages(payload)
    assert isinstance(msgs, list)
    assert msgs
    assert all(isinstance(x, str) for x in msgs)
