"""api/routes/benchmark.py"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from api.routes._shared import _load, _sf

router = APIRouter()

VALID = ["Attacker", "Midfielder", "Defender", "GK"]

@router.get("/benchmark/{position_group}")
def get_benchmark(position_group: str, season: Optional[str] = Query(None)):
    if position_group not in VALID:
        raise HTTPException(400, f"Invalid position. Choose from: {VALID}")
    d       = _load(season=season)
    weights = d["weights"].get(position_group, d["weights"]["Midfielder"])
    bench   = d["bench"]
    pg_col = "position_group" if "position_group" in bench.columns else bench.columns[0]
    row = bench[bench[pg_col].astype(str).str.lower() == position_group.lower()]
    if len(row):
        avgs = {col: _sf(row[col].iloc[0]) for col in bench.columns if col != pg_col}
    return {"position_group": position_group, "averages": avgs, "weights": weights}
