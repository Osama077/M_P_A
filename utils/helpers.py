"""
utils/helpers.py — Helper Functions
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Any, Optional


def safe_float(val) -> Optional[float]:
    """تحويل NaN لـ None عشان JSON يقبله"""
    if val is None:
        return None
    if isinstance(val, float) and np.isnan(val):
        return None
    return round(float(val), 4)


def safe_int(val) -> int:
    """تحويل NaN لـ 0"""
    if val is None:
        return 0
    if isinstance(val, float) and np.isnan(val):
        return 0
    return int(val)


def df_to_records(df: pd.DataFrame) -> list:
    """تحويل DataFrame لـ list of dicts مع معالجة NaN"""
    return json.loads(df.to_json(orient="records", default_handler=str))


def ensure_dirs(*paths):
    """إنشاء المجلدات لو مش موجودة"""
    for path in paths:
        Path(path).mkdir(parents=True, exist_ok=True)


def normalize_to_score(series: pd.Series, min_val=None, max_val=None) -> pd.Series:
    """تحويل أي Series لـ 0-10"""
    if min_val is None:
        min_val = series.quantile(0.05)
    if max_val is None:
        max_val = series.quantile(0.95)
    score = (series - min_val) / (max_val - min_val + 1e-10) * 10
    return score.clip(0, 10)


def load_json(path: str) -> Any:
    with open(path, "r") as f:
        return json.load(f)


def save_json(data: Any, path: str):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
