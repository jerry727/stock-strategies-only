from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


ARTIFACT_DIR = Path(
    os.environ.get(
        "RUN_ARTIFACT_DIR",
        str(Path(__file__).resolve().parent.parent / "runs"),
    )
)


def artifact_dir() -> Path:
    path = Path(os.environ.get("RUN_ARTIFACT_DIR", str(ARTIFACT_DIR)))
    path.mkdir(parents=True, exist_ok=True)
    return path


def _artifact_path_for(result: dict) -> Path:
    created_at = result.get("created_at") or datetime.now().isoformat()
    try:
        day = datetime.fromisoformat(created_at.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except ValueError:
        day = datetime.now().strftime("%Y-%m-%d")
    run_id = result.get("run_id", f"run-{datetime.now().strftime('%Y%m%d%H%M%S')}")
    return artifact_dir() / day / f"{run_id}.json"


def save_run_result(result: dict) -> str:
    path = _artifact_path_for(result)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(result)
    payload.setdefault("artifacts", {})
    payload["artifacts"]["json_path"] = str(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return str(path)


def load_run_result(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_runs(strategy_id: Optional[str] = None, limit: int = 20) -> list[dict]:
    base = artifact_dir()
    files = sorted(base.glob("**/*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    out = []
    for p in files:
        try:
            data = load_run_result(str(p))
        except Exception:
            continue
        if strategy_id and data.get("strategy", {}).get("id") != strategy_id:
            continue
        out.append(data)
        if len(out) >= limit:
            break
    return out


def latest_run(strategy_id: Optional[str] = None) -> Optional[dict]:
    runs = list_runs(strategy_id=strategy_id, limit=1)
    return runs[0] if runs else None


def get_run_by_id(run_id: str) -> Optional[dict]:
    base = artifact_dir()
    for p in base.glob(f"**/{run_id}.json"):
        try:
            return load_run_result(str(p))
        except Exception:
            return None
    return None
