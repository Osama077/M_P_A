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
from config import DATA_DIR, MODELS_DIR

@lru_cache(maxsize=1)
def _load_data():
    return {
        "events":    pd.read_parquet(DATA_DIR / "events_clean.parquet"),
        "computed":  pd.read_parquet(DATA_DIR / "computed_features.parquet"),
        "scores":    pd.read_parquet(DATA_DIR / "model_scores.parquet"),
        "vaep":      pd.read_parquet(DATA_DIR / "player_vaep_ratings.parquet"),
        "matches":   pd.read_parquet(DATA_DIR / "matches.parquet"),
        "lineups":   pd.read_parquet(DATA_DIR / "lineups.parquet"),
        "bench":     pd.read_parquet(DATA_DIR / "position_benchmarks.parquet"),
        "weights":   json.loads((MODELS_DIR / "position_weights.json").read_text(encoding="utf-8")),
    }

def _sf(v):
    if v is None or (isinstance(v, float) and np.isnan(v)): return None
    return round(float(v), 4)

def _si(v):
    if v is None or (isinstance(v, float) and np.isnan(v)): return 0
    return int(v)

def _to_records(df):
    return json.loads(df.to_json(orient="records", default_handler=str))
