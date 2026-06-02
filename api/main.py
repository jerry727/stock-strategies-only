"""FastAPI 後端

啟動：
  uv run uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from stock_strategies import loader
from stock_strategies.market import get_market_state
from stock_strategies.sheet import read_watchlist
from stock_strategies.run_store import get_run_by_id, latest_run, list_runs
from main import run_pipeline

from api.services.ai_generator import generate_strategy_with_ai

app = FastAPI(title="Stock Strategies API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StrategyIn(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = ""
    source: Optional[str] = "manual"
    params: dict[str, Any] = Field(default_factory=dict)


class AIGenerateIn(BaseModel):
    prompt: str
    name: Optional[str] = None


class RunIn(BaseModel):
    strategy_id: str
    limit: Optional[int] = None
    no_telegram: bool = True
    no_sheet: bool = True
    no_performance: bool = True
    watchlist: Optional[list[dict[str, Any]]] = None


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/strategies")
def list_strategies():
    return {"strategies": loader.list_strategies()}


@app.get("/api/strategies/defaults")
def defaults():
    return {"params": loader.param_defaults()}


@app.get("/api/strategies/{sid}")
def get_strategy(sid: str):
    s = loader.get_strategy(sid)
    if not s:
        raise HTTPException(404, f"找不到策略 {sid}")
    return s


@app.post("/api/strategies")
def save_strategy(payload: StrategyIn):
    try:
        return loader.save_strategy(payload.model_dump())
    except loader.StrategyError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/strategies/{sid}")
def delete_strategy(sid: str):
    if sid in ("default", "conservative"):
        raise HTTPException(400, "預設策略不可刪除")
    ok = loader.delete_strategy(sid)
    if not ok:
        raise HTTPException(404, f"找不到策略 {sid}")
    return {"ok": True}


@app.post("/api/strategies/generate")
def generate_strategy(payload: AIGenerateIn):
    try:
        return generate_strategy_with_ai(payload.prompt, name=payload.name)
    except Exception as e:
        raise HTTPException(500, f"AI 生策略失敗：{e}")


@app.get("/api/market")
def market():
    return get_market_state()


@app.get("/api/watchlist")
def watchlist():
    try:
        return {"items": read_watchlist()}
    except Exception as e:
        return {"items": [], "error": str(e)}


@app.post("/api/run")
def run(payload: RunIn):
    strategy = loader.get_strategy(payload.strategy_id)
    if not strategy:
        raise HTTPException(404, f"找不到策略 {payload.strategy_id}")
    try:
        return run_pipeline(
            strategy_id=payload.strategy_id,
            limit=payload.limit,
            send_notifications=not payload.no_telegram,
            write_sheet_enabled=not payload.no_sheet,
            write_performance_enabled=not payload.no_performance,
            watchlist_override=payload.watchlist,
        )
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/runs/latest")
def api_latest_run(strategy_id: Optional[str] = None):
    data = latest_run(strategy_id=strategy_id)
    if not data:
        raise HTTPException(404, "找不到最新 run")
    return data


@app.get("/api/runs")
def api_list_runs(strategy_id: Optional[str] = None, limit: int = 20):
    return {"runs": list_runs(strategy_id=strategy_id, limit=limit)}


@app.get("/api/runs/{run_id}")
def api_get_run(run_id: str):
    data = get_run_by_id(run_id)
    if not data:
        raise HTTPException(404, f"找不到 run {run_id}")
    return data
