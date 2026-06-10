"""api/routes/metadata.py — Player metadata endpoints"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import pandas as pd
import numpy as np
from pathlib import Path
from config import DATA_DIR

router = APIRouter()

METADATA_DIR = DATA_DIR / "metadata"
PLAYER_INFO_PATH = METADATA_DIR / "player_info.parquet"


def _load_metadata():
    if not PLAYER_INFO_PATH.exists():
        return pd.DataFrame()
    return pd.read_parquet(PLAYER_INFO_PATH)


def _sf(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    return round(float(v), 4)


def _si(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return 0
    return int(v)


def _initials(name):
    parts = str(name).split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return str(name)[:2].upper()


@router.get("/metadata/players")
def list_players_metadata(
    position: Optional[str] = Query(None),
    min_age: Optional[int] = Query(None, ge=0),
    max_age: Optional[int] = Query(None, ge=0),
    season: Optional[str] = Query(None),
):
    """List all players with metadata, with optional filters."""
    meta = _load_metadata()
    if meta.empty:
        raise HTTPException(404, "No metadata found. Run pipeline/metadata_loader.py first.")

    if position:
        meta = meta[meta["primary_position"].str.contains(position, case=False, na=False)]

    result = []
    for _, r in meta.iterrows():
        foot = r.get("preferred_foot")
        if isinstance(foot, float) and np.isnan(foot):
            foot = None
        player = {
            "player_id": _si(r["player_id"]),
            "full_name": str(r.get("full_name", "")),
            "initials": _initials(r.get("full_name", "")),
            "primary_position": str(r.get("primary_position", "Unknown")),
            "preferred_foot": foot,
            "total_appearances": _si(r.get("total_appearances")),
            "career_avg_score": _sf(r.get("career_avg_score")),
            "career_avg_vaep": _sf(r.get("career_avg_vaep")),
        }

        season_summaries = r.get("season_summaries")
        if isinstance(season_summaries, np.ndarray):
            season_summaries = season_summaries.tolist()
        if isinstance(season_summaries, list) and season:
            filtered = [s for s in season_summaries if s.get("season_label") == season]
            if filtered:
                player["season"] = filtered[0]

        result.append(player)

    return {"players": result, "total": len(result)}


@router.get("/metadata/players/{player_id}")
def get_player_metadata(player_id: int):
    """Full metadata for a single player."""
    meta = _load_metadata()
    if meta.empty:
        raise HTTPException(404, "No metadata found")

    row = meta[meta["player_id"] == player_id]
    if not len(row):
        raise HTTPException(404, f"Player {player_id} not found")

    r = row.iloc[0]
    season_summaries = r.get("season_summaries")
    if isinstance(season_summaries, np.ndarray):
        season_summaries = season_summaries.tolist()
    if isinstance(season_summaries, list):
        season_summaries = [s for s in season_summaries if isinstance(s, dict)]
    else:
        season_summaries = []

    jersey_numbers = r.get("jersey_numbers")
    if isinstance(jersey_numbers, dict):
        jersey_numbers = {str(k): int(v) for k, v in jersey_numbers.items()}
    else:
        jersey_numbers = {}

    return {
        "player_id": _si(r["player_id"]),
        "full_name": str(r.get("full_name", "")),
        "initials": _initials(r.get("full_name", "")),
        "primary_position": str(r.get("primary_position", "Unknown")),
        "preferred_foot": r.get("preferred_foot"),
        "total_appearances": _si(r.get("total_appearances")),
        "career_avg_score": _sf(r.get("career_avg_score")),
        "career_avg_vaep": _sf(r.get("career_avg_vaep")),
        "season_summaries": season_summaries,
        "jersey_numbers": jersey_numbers,
        "uuid": str(r.get("uuid", "")),
    }


@router.get("/metadata/player/search")
def search_players(query: str = Query(min_length=1)):
    """Search players by name."""
    meta = _load_metadata()
    if meta.empty:
        raise HTTPException(404, "No metadata found")

    mask = meta["full_name"].str.contains(query, case=False, na=False)
    results = meta[mask].head(20)

    return {
        "results": [
            {
                "player_id": _si(r["player_id"]),
                "full_name": str(r.get("full_name", "")),
                "initials": _initials(r.get("full_name", "")),
                "primary_position": str(r.get("primary_position", "Unknown")),
            }
            for _, r in results.iterrows()
        ],
        "total": len(results),
    }
