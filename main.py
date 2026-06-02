import argparse
import json
import os
import sys
import time
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from stock_strategies.sheet import (
    read_watchlist,
    append_signals,
    read_performance,
    write_performance,
)
from stock_strategies.evaluate import evaluate
from stock_strategies.notify import send_telegram, format_messages
from stock_strategies.market import get_market_state, apply_market_filter
from stock_strategies.performance import update_performance, summary as perf_summary
from stock_strategies import loader
from stock_strategies.run_store import save_run_result


REQUIRED_ENV = [
    "FINMIND_TOKEN",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "GOOGLE_SHEET_ID",
    "GOOGLE_CREDS_JSON",
]


def run_pipeline(
    strategy_id: str = "default",
    limit: int | None = None,
    send_notifications: bool = True,
    write_sheet_enabled: bool = True,
    write_performance_enabled: bool = True,
    json_out: str | None = None,
) -> dict:
    strategy = loader.get_strategy(strategy_id) or {"id": strategy_id, "name": strategy_id, "params": {}}
    needs_sheet = write_sheet_enabled or write_performance_enabled or send_notifications
    missing = [k for k in REQUIRED_ENV if not os.environ.get(k)] if needs_sheet else []
    if missing:
        raise RuntimeError(f"缺少環境變數: {missing}")

    if needs_sheet:
        watchlist = read_watchlist()
    else:
        watchlist = []
    if limit:
        watchlist = watchlist[:limit]

    market = get_market_state()
    results = []
    for row in watchlist:
        sid = str(row["stock_id"])
        name = row.get("name", "")
        r = evaluate(sid, name, strategy=strategy)
        if r:
            results.append(r)
        time.sleep(0.1)

    downgraded = apply_market_filter(results, market)
    order = {"BUY": 0, "WATCH": 1, "SKIP": 2, "ERROR": 3}
    results.sort(key=lambda x: (order.get(x.get("action"), 4), -x.get("signal_score", 0)))

    run_id = f"{datetime.now().strftime('%Y-%m-%dT%H-%M-%S')}_{strategy_id}"
    created_at = datetime.now().isoformat()

    performance_stats = None
    if write_sheet_enabled:
        append_signals(results)
    if write_performance_enabled:
        existing_perf = read_performance()
        updated_perf = update_performance(existing_perf, results)
        write_performance(updated_perf)
        performance_stats = perf_summary(updated_perf)

    if send_notifications:
        for msg in format_messages(results, watchlist, market=market):
            send_telegram(msg)
            time.sleep(0.1)

    payload = {
        "run_id": run_id,
        "created_at": created_at,
        "strategy": {"id": strategy.get("id", strategy_id), "name": strategy.get("name", strategy_id)},
        "inputs": {"limit": limit, "strategy_id": strategy_id},
        "market": market,
        "downgraded": downgraded,
        "summary": {
            "total": len(results),
            "buy": sum(1 for r in results if r.get("action") == "BUY"),
            "watch": sum(1 for r in results if r.get("action") == "WATCH"),
            "skip": sum(1 for r in results if r.get("action") == "SKIP"),
            "error": sum(1 for r in results if r.get("action") == "ERROR"),
        },
        "results": results,
        "performance_summary": performance_stats,
        "artifacts": {},
    }

    artifact_path = save_run_result(payload)
    payload["artifacts"]["json_path"] = artifact_path
    if json_out:
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        payload["artifacts"]["explicit_json_path"] = json_out
    return payload


def main():
    parser = argparse.ArgumentParser(description="V3.2 每日選股訊號系統")
    parser.add_argument("--strategy-id", default="default")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--json-out", default=None)
    parser.add_argument("--no-telegram", action="store_true")
    parser.add_argument("--no-sheet", action="store_true")
    parser.add_argument("--no-performance", action="store_true")
    args = parser.parse_args()

    try:
        result = run_pipeline(
            strategy_id=args.strategy_id,
            limit=args.limit,
            send_notifications=not args.no_telegram,
            write_sheet_enabled=not args.no_sheet,
            write_performance_enabled=not args.no_performance,
            json_out=args.json_out,
        )
    except Exception as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)

    print(
        f"✅ 完成 | strategy={result['strategy']['id']} | total={result['summary']['total']} | "
        f"BUY={result['summary']['buy']} WATCH={result['summary']['watch']} | artifact={result['artifacts'].get('json_path')}"
    )


if __name__ == "__main__":
    main()
