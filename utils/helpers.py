"""
utils/helpers.py — Helper Functions
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Any, Optional


def safe_float(val) -> Optional[float]:
    """Convert NaN to None for JSON compatibility."""
    if val is None:
        return None
    if isinstance(val, float) and np.isnan(val):
        return None
    return round(float(val), 4)


def safe_int(val) -> int:
    """Convert NaN to 0."""
    if val is None:
        return 0
    if isinstance(val, float) and np.isnan(val):
        return 0
    return int(val)


def df_to_records(df: pd.DataFrame) -> list:
    """Convert DataFrame to list of dicts with NaN handling."""
    return json.loads(df.to_json(orient="records", default_handler=str))


def ensure_dirs(*paths):
    """Create directories if they don't exist."""
    for path in paths:
        Path(path).mkdir(parents=True, exist_ok=True)


def normalize_to_score(series: pd.Series, min_val=None, max_val=None) -> pd.Series:
    """Normalize any Series to 0-10 scale using quantile-based bounds."""
    if min_val is None:
        min_val = series.quantile(0.05)
    if max_val is None:
        max_val = series.quantile(0.95)
    if max_val == min_val:
        return pd.Series(5.0, index=series.index)
    score = (series - min_val) / (max_val - min_val) * 10
    return score.clip(0, 10)


def zscore_to_score(series: pd.Series, cap: float = 2.5) -> pd.Series:
    """Convert Series to 0-10 using z-score (default position-wide)."""
    z = (series - series.mean()) / (series.std() + 1e-10)
    return (z / cap * 5 + 5).clip(0, 10).round(2)


def load_json(path: str) -> Any:
    with open(path, "r") as f:
        return json.load(f)


def save_json(data: Any, path: str):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
