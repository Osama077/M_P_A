"""
api/routes/analysis.py
api/routes/player.py
api/routes/team.py
api/routes/match.py
api/routes/benchmark.py
"""

# ── Shared data loader ────────────────────────────────────────────────────────
import json
import numpy as np
import pandas as pd
from pathlib import Path
from functools import lru_cache
from config import DATA_DIR, MODELS_DIR, SEASONS_LIST

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

SEASONS_DIR = DATA_DIR / "seasons"


def _alias_overall_score_to_kpi(sc: pd.DataFrame, kpi: pd.DataFrame) -> pd.DataFrame:
    """Replace overall_score values with position_kpi where available.
    Also adds position_granular column for backward compatibility."""
    if kpi is None or "position_kpi" not in kpi.columns or not len(kpi):
        return sc
    merge_cols = ["match_id", "player_id", "position_kpi", "position_kpi_label",
                  "position_granular", "confidence"]
    avail = [c for c in merge_cols if c in kpi.columns]
    sc = sc.merge(kpi[avail], on=["match_id", "player_id"], how="left")
    sc["overall_score"] = sc["position_kpi"].fillna(sc["overall_score"])
    # Fill granular position from KPI data
    if "position_granular" in sc.columns:
        sc["position_granular"] = sc["position_granular"].fillna(
            sc.get("position_group", "").map(
                {"GK": "Goalkeeper", "Defender": "Center Back",
                 "Midfielder": "Central Midfielder", "Attacker": "Winger"}
            ).fillna("Central Midfielder")
        )
    # Keep position_granular, position_kpi_label, confidence; drop position_kpi (aliased to overall_score)
    sc = sc.drop(columns=["position_kpi"], errors="ignore")
    return sc


@lru_cache(maxsize=1)
def _load_data():
    """Load combined data from all seasons (single parquet files)."""
    kpi_path = DATA_DIR / "position_kpi.parquet"
    d = {
        "events":    pd.read_parquet(DATA_DIR / "events_clean.parquet"),
        "computed":  pd.read_parquet(DATA_DIR / "computed_features.parquet"),
        "scores":    pd.read_parquet(DATA_DIR / "model_scores.parquet"),
        "vaep":      pd.read_parquet(DATA_DIR / "player_vaep_ratings.parquet"),
        "matches":   pd.read_parquet(DATA_DIR / "matches.parquet"),
        "lineups":   pd.read_parquet(DATA_DIR / "lineups.parquet"),
        "bench":     pd.read_parquet(DATA_DIR / "position_benchmarks.parquet"),
        "weights":   json.loads((MODELS_DIR / "position_weights.json").read_text(encoding="utf-8")),
        "position_kpi": pd.read_parquet(kpi_path) if kpi_path.exists() else pd.DataFrame(),
    }
    d["scores"] = _alias_overall_score_to_kpi(d["scores"], d["position_kpi"])
    return d


def _load_season(season_label: str) -> dict:
    """Load a single season from per-season parquet files.
    Falls back to filtering combined data if per-season files don't exist."""
    season_dir = SEASONS_DIR / season_label.replace("/", "_")

    def _try_read(path, fallback_key=None, filter_col="season_label"):
        if path.exists():
            return pd.read_parquet(path)
        if fallback_key:
            combined = _load_data()[fallback_key]
            if filter_col and filter_col in combined.columns:
                return combined[combined[filter_col] == season_label].copy()
            return combined.copy()
        return pd.DataFrame()

    result = {
        "events":    _try_read(season_dir / "events_clean.parquet",          "events"),
        "computed":  _try_read(season_dir / "computed_features.parquet",     "computed"),
        "scores":    _try_read(season_dir / "model_scores.parquet",          "scores"),
        "vaep":      _try_read(season_dir / "player_vaep_ratings.parquet",   "vaep"),
        "matches":   _try_read(season_dir / "matches.parquet",               "matches"),
        "lineups":   _try_read(season_dir / "lineups.parquet",               "lineups"),
        "bench":     _try_read(season_dir / "position_benchmarks.parquet",   "bench", filter_col=None),
        "weights":   json.loads((MODELS_DIR / "position_weights.json").read_text(encoding="utf-8")),
    }
    # Include position_kpi filtered by this season's match IDs
    kpi_path = DATA_DIR / "position_kpi.parquet"
    if kpi_path.exists():
        kpi_all = pd.read_parquet(kpi_path)
        scores_season = result.get("scores")
        if scores_season is not None and "match_id" in scores_season.columns:
            season_mids = scores_season["match_id"].unique()
            result["position_kpi"] = kpi_all[kpi_all["match_id"].isin(season_mids)]
        else:
            result["position_kpi"] = kpi_all
    else:
        result["position_kpi"] = pd.DataFrame()
    return result


@lru_cache(maxsize=32)
def _load_season_cached(season_label: str):
    """Cached wrapper for _load_season."""
    return _load_season(season_label)


def _load(season: str = None):
    """
    Load data for a specific season or all seasons combined.
    If season is None, returns combined data (all seasons).
    """
    if season is not None:
        return _load_season_cached(season)
    return _load_data()


def _get_available_seasons():
    """Return list of available seasons from config."""
    from config import SEASONS_LIST
    return [{"competition_id": c, "season_id": s, "label": l} for c, s, l in SEASONS_LIST]


def _sf(v):
    if v is None or (isinstance(v, float) and np.isnan(v)): return None
    return round(float(v), 4)

def _si(v):
    if v is None or (isinstance(v, float) and np.isnan(v)): return 0
    return int(v)

def _to_records(df):
    return json.loads(df.to_json(orient="records", default_handler=str))
