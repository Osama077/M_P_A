import numpy as np
import pandas as pd
import pytest

from utils.helpers import (
    safe_float, safe_int, df_to_records, ensure_dirs,
    normalize_to_score, load_json, save_json,
)


class TestSafeFloat:
    def test_returns_none_for_none(self):
        assert safe_float(None) is None

    def test_returns_none_for_nan(self):
        assert safe_float(np.nan) is None

    def test_rounds_float_to_4_decimals(self):
        assert safe_float(3.141592) == 3.1416

    def test_passes_int_through(self):
        assert safe_float(42) == 42.0

    def test_floats_are_rounded_not_truncated(self):
        assert safe_float(0.12345) == 0.1235


class TestSafeInt:
    def test_returns_0_for_none(self):
        assert safe_int(None) == 0

    def test_returns_0_for_nan(self):
        assert safe_int(np.nan) == 0

    def test_converts_float(self):
        assert safe_int(42.7) == 42

    def test_converts_int(self):
        assert safe_int(99) == 99


class TestDfToRecords:
    def test_normal_df(self):
        df = pd.DataFrame({"a": [1, 2], "b": [3.5, 4.5]})
        records = df_to_records(df)
        assert records == [{"a": 1, "b": 3.5}, {"a": 2, "b": 4.5}]

    def test_handles_nan_values(self):
        df = pd.DataFrame({"x": [1.0, np.nan]})
        records = df_to_records(df)
        assert records[1]["x"] is None or records[1]["x"] != records[1]["x"]


class TestNormalizeToScore:
    def test_returns_values_between_0_and_10(self):
        s = pd.Series([1, 2, 3, 4, 5])
        result = normalize_to_score(s)
        assert result.min() >= 0
        assert result.max() <= 10

    def test_increasing_input_gives_increasing_score(self):
        s = pd.Series([10, 20, 30, 40])
        result = normalize_to_score(s)
        assert result.is_monotonic_increasing

    def test_uniform_series_returns_midpoint(self):
        s = pd.Series([5, 5, 5])
        result = normalize_to_score(s)
        assert (result >= 0).all() and (result <= 10).all()

    def test_custom_min_max(self):
        s = pd.Series([0, 5, 10])
        result = normalize_to_score(s, min_val=0, max_val=10)
        assert pytest.approx(result.iloc[0]) == 0.0
        assert pytest.approx(result.iloc[2]) == 10.0

    def test_handles_single_value(self):
        s = pd.Series([42.0])
        result = normalize_to_score(s)
        assert 0 <= result.iloc[0] <= 10


class TestEnsureDirs:
    def test_creates_directory(self, tmp_path):
        d = tmp_path / "new_dir" / "sub"
        ensure_dirs(str(d))
        assert d.exists()

    def test_does_not_raise_on_existing(self, tmp_path):
        d = tmp_path / "existing"
        d.mkdir(parents=True)
        ensure_dirs(str(d))


class TestJsonIO:
    def test_roundtrip(self, tmp_path):
        data = {"key": "value", "num": 42}
        path = str(tmp_path / "test.json")
        save_json(data, path)
        loaded = load_json(path)
        assert loaded == data
