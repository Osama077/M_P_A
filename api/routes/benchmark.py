"""api/routes/benchmark.py"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from api.routes._shared import _load, _sf, GRANULAR_POSITIONS, GRANULAR_LABELS

router = APIRouter()

VALID = ["Attacker", "Midfielder", "Defender", "GK"] + GRANULAR_POSITIONS

@router.get("/benchmark/{position_group}")
def get_benchmark(position_group: str, season: Optional[str] = Query(None)):
    if position_group not in VALID:
        raise HTTPException(400, f"Invalid position. Choose from: {VALID}")
    d       = _load(season=season)
    weights = d["weights"].get(position_group, d["weights"]["Midfielder"])
    bench   = d["bench"]
    pg_col = "position_group" if "position_group" in bench.columns else bench.columns[0]
    row = bench[bench[pg_col].astype(str).str.lower() == position_group.lower()]

    # If granular position not in old bench table, map to coarse group
    if not len(row) and position_group in GRANULAR_POSITIONS:
        coarse_map = {
            "Goalkeeper": "GK", "Center Back": "Defender", "Full Back": "Defender",
            "Defensive Midfielder": "Midfielder", "Central Midfielder": "Midfielder",
            "Attacking Midfielder": "Midfielder", "Winger": "Attacker", "Striker": "Attacker",
        }
        coarse = coarse_map.get(position_group, "Midfielder")
        row = bench[bench[pg_col].astype(str).str.lower() == coarse.lower()]

    if len(row):
        avgs = {col: _sf(row[col].iloc[0]) for col in bench.columns if col != pg_col}
    else:
        avgs = {}

    is_granular = position_group in GRANULAR_POSITIONS
    return {
        "position_group": position_group,
        "short_label": GRANULAR_LABELS.get(position_group, position_group[:2].upper()) if is_granular else position_group[:2].upper(),
        "is_granular": is_granular,
        "averages": avgs,
        "weights": weights,
    }
