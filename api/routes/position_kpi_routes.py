"""api/routes/position_kpi_routes.py — Granular Position KPI endpoints (Phase 4.5-4.8)."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import pandas as pd
import numpy as np
from api.routes._shared import _load, _sf, _si

router = APIRouter()

GRANULAR_POSITIONS = [
    "Goalkeeper", "Center Back", "Full Back",
    "Defensive Midfielder", "Central Midfielder", "Attacking Midfielder",
    "Winger", "Striker",
]

GRANULAR_LABELS = {
    "Goalkeeper": "GK", "Center Back": "CB", "Full Back": "FB",
    "Defensive Midfielder": "DMF", "Central Midfielder": "CMF",
    "Attacking Midfielder": "AMF", "Winger": "WG", "Striker": "ST",
}


@router.get("/position-kpi/positions")
def list_granular_positions():
    """List all granular positions with short labels."""
    return {
        "positions": [
            {"position": p, "short": GRANULAR_LABELS.get(p, p[:2].upper())}
            for p in GRANULAR_POSITIONS
        ]
    }


@router.get("/position-kpi/player/{player_id}")
def get_player_position_kpi(
    player_id: int,
    match_id: Optional[int] = Query(None),
    season: Optional[str] = Query(None),
):
    """Get granular position KPI for a player, optionally for a specific match."""
    d = _load(season=season)
    kpi = d.get("position_kpi", pd.DataFrame())
    if not len(kpi):
        raise HTTPException(404, "Position KPI data not available")

    pk = kpi[kpi["player_id"] == player_id]
    if not len(pk):
        raise HTTPException(404, f"Player {player_id} not found in KPI data")

    if match_id:
        pk = pk[pk["match_id"] == match_id]
        if not len(pk):
            raise HTTPException(404, f"No KPI data for match {match_id}")

    rows = []
    for _, r in pk.iterrows():
        dims = {c: _sf(r[c]) for c in r.index if c.startswith("kpi_")}
        rows.append({
            "match_id": _si(r["match_id"]),
            "player_id": _si(r["player_id"]),
            "position_granular": str(r.get("position_granular", "Unknown")),
            "position_short": GRANULAR_LABELS.get(str(r.get("position_granular", "")), "?"),
            "position_kpi": _sf(r.get("position_kpi")),
            "position_kpi_label": str(r.get("position_kpi_label", "")),
            "confidence": str(r.get("confidence", "high")),
            "minutes_played": _si(r.get("minutes_played", 0)),
            "dimensions": dims,
        })

    return {"player_id": player_id, "kpi_records": rows}


@router.get("/position-kpi/compare")
def compare_position_kpi(
    player_ids: str = Query(..., description="Comma-separated player IDs"),
    match_id: Optional[int] = Query(None),
    season: Optional[str] = Query(None),
):
    """Compare position KPI across multiple players for a match."""
    d = _load(season=season)
    kpi = d.get("position_kpi", pd.DataFrame())
    if not len(kpi):
        raise HTTPException(404, "Position KPI data not available")

    ids = [int(float(i.strip())) for i in player_ids.split(",")]
    result = []
    for pid in ids:
        pk = kpi[kpi["player_id"] == pid]
        if not len(pk):
            result.append({"player_id": pid, "error": "No KPI data found"})
            continue
        if match_id:
            pk = pk[pk["match_id"] == match_id]
        if not len(pk):
            result.append({"player_id": pid, "match_id": match_id, "error": "No KPI data for this match"})
            continue
        r = pk.iloc[0]
        dims = {c: _sf(r[c]) for c in r.index if c.startswith("kpi_")}
        result.append({
            "player_id": pid,
            "position_granular": str(r.get("position_granular", "Unknown")),
            "position_kpi": _sf(r.get("position_kpi")),
            "position_kpi_label": str(r.get("position_kpi_label", "")),
            "confidence": str(r.get("confidence", "high")),
            "dimensions": dims,
        })

    return {"comparison": result}


@router.get("/position-kpi/distribution/{position}")
def get_position_distribution(
    position: str,
    season: Optional[str] = Query(None),
):
    """Get KPI distribution statistics for a granular position."""
    if position not in GRANULAR_POSITIONS:
        raise HTTPException(400, f"Invalid position. Choose from: {GRANULAR_POSITIONS}")

    d = _load(season=season)
    kpi = d.get("position_kpi", pd.DataFrame())
    if not len(kpi):
        raise HTTPException(404, "Position KPI data not available")

    pk = kpi[kpi["position_granular"] == position]
    if not len(pk):
        raise HTTPException(404, f"No data for position {position}")

    scores = pk["position_kpi"].dropna()
    dist = {
        "position": position,
        "count": len(scores),
        "mean": _sf(scores.mean()),
        "median": _sf(scores.median()),
        "std": _sf(scores.std()),
        "min": _sf(scores.min()),
        "max": _sf(scores.max()),
        "p10": _sf(np.percentile(scores, 10)),
        "p25": _sf(np.percentile(scores, 25)),
        "p75": _sf(np.percentile(scores, 75)),
        "p90": _sf(np.percentile(scores, 90)),
        "label_distribution": pk["position_kpi_label"].value_counts().to_dict(),
    }

    # Per-dimension distributions
    dim_cols = [c for c in pk.columns if c.startswith("kpi_")]
    dim_dist = {}
    for c in dim_cols:
        v = pk[c].dropna()
        if len(v) == 0:
            continue
        dim_dist[c.replace("kpi_", "")] = {
            "mean": _sf(v.mean()), "median": _sf(v.median()),
            "std": _sf(v.std()),
            "p25": _sf(np.percentile(v, 25)) if len(v) >= 4 else _sf(v.quantile(0.25)),
            "p75": _sf(np.percentile(v, 75)) if len(v) >= 4 else _sf(v.quantile(0.75)),
        }

    return {"distribution": dist, "dimension_distributions": dim_dist}


@router.get("/position-kpi/rankings")
def get_position_kpi_rankings(
    position: Optional[str] = Query(None),
    min_matches: int = Query(3, ge=1),
    limit: int = Query(20, ge=1, le=100),
    season: Optional[str] = Query(None),
):
    """Rank players by season-average position KPI within a position."""
    d = _load(season=season)
    kpi = d.get("position_kpi", pd.DataFrame())
    if not len(kpi):
        raise HTTPException(404, "Position KPI data not available")

    pk = kpi.copy()
    if position:
        if position not in GRANULAR_POSITIONS:
            raise HTTPException(400, f"Invalid position. Choose from: {GRANULAR_POSITIONS}")
        pk = pk[pk["position_granular"] == position]

    # Aggregate per player
    agg = pk.groupby(["player_id", "position_granular"]).agg(
        avg_kpi=("position_kpi", "mean"),
        max_kpi=("position_kpi", "max"),
        matches=("match_id", "count"),
        confidence=("confidence", lambda x: x.mode().iloc[0] if len(x) else "high"),
    ).reset_index()

    agg = agg[agg["matches"] >= min_matches]
    agg = agg.sort_values("avg_kpi", ascending=False).head(limit)

    # Get player names from scores
    sc = d["scores"]
    name_map = sc[["player_id", "player_name"]].drop_duplicates().set_index("player_id")["player_name"].to_dict()

    rankings = []
    for _, r in agg.iterrows():
        pid = int(r["player_id"])
        rankings.append({
            "player_id": pid,
            "player_name": name_map.get(pid, f"Player {pid}"),
            "position_granular": str(r["position_granular"]),
            "avg_kpi": _sf(r["avg_kpi"]),
            "max_kpi": _sf(r["max_kpi"]),
            "matches": _si(r["matches"]),
            "confidence": str(r["confidence"]),
        })

    return {
        "position": position or "all",
        "min_matches": min_matches,
        "total_players": len(rankings),
        "rankings": rankings,
    }
