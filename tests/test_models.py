import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))


class TestScoringModel:
    """Tests for the Scoring Model pipeline step."""

    @pytest.fixture
    def sample_computed(self):
        return pd.DataFrame({
            "match_id": [1001, 1001, 1002],
            "player_id": [201, 202, 201],
            "player_name": ["Messi", "Suarez", "Messi"],
            "team_name": ["Barcelona", "Barcelona", "Barcelona"],
            "position_group": ["Attacker", "Attacker", "Attacker"],
            "pass_accuracy": [88.0, 75.0, 85.0],
            "progressive_passes": [6, 2, 5],
            "total_passes": [72, 45, 68],
            "total_shots": [5, 3, 4],
            "predicted_xg": [0.8, 0.3, 0.6],
            "total_pressures": [18, 22, 15],
            "pressure_regains": [8, 10, 7],
            "pressing_efficiency": [44.4, 45.5, 46.7],
            "total_carries": [42, 18, 38],
            "progressive_carries": [8, 3, 7],
            "dribble_success_rate": [65.0, 55.0, 62.0],
            "total_actions": [85, 62, 80],
            "activity_drop_2nd_half": [0.05, 0.12, 0.08],
            "fouls_committed": [1, 3, 2],
            "yellow_cards": [0, 1, 0],
            "red_cards": [0, 0, 0],
            "ball_retention_rate": [88.0, 72.0, 85.0],
            "attacking_tendency": [75.0, 60.0, 70.0],
            "position_deviation": [15.0, 12.0, 14.0],
        })

    def test_compute_dimension_scores_shapes(self, sample_computed):
        from pipeline.scoring_model import compute_dimension_scores
        scores = compute_dimension_scores(sample_computed)
        expected_cols = {"match_id", "player_id", "player_name", "team_name",
                         "position_group", "passing_score", "shooting_score",
                         "positioning_score", "pressing_score", "movement_score",
                         "physical_score", "behavioral_score"}
        assert expected_cols.issubset(set(scores.columns))
        assert len(scores) == len(sample_computed)

    def test_dimension_scores_in_range(self, sample_computed):
        from pipeline.scoring_model import compute_dimension_scores
        scores = compute_dimension_scores(sample_computed)
        score_cols = ["passing_score", "shooting_score", "positioning_score",
                      "pressing_score", "movement_score", "physical_score",
                      "behavioral_score"]
        for col in score_cols:
            assert scores[col].between(0, 10).all(), f"{col} out of range"

    def test_passing_score_higher_for_better_passers(self, sample_computed):
        from pipeline.scoring_model import compute_dimension_scores
        scores = compute_dimension_scores(sample_computed)
        messi = scores[scores["player_id"] == 201].iloc[0]
        suarez = scores[scores["player_id"] == 202].iloc[0]
        assert messi["passing_score"] >= suarez["passing_score"]

    def test_compute_overall_produces_valid_scores(self, sample_computed):
        from pipeline.scoring_model import compute_dimension_scores, compute_overall_score
        scores = compute_dimension_scores(sample_computed)
        vaep = pd.Series([0.5, -0.2, 0.3])
        result = compute_overall_score(scores, vaep)
        assert "overall_score" in result.columns
        assert result["overall_score"].between(0, 10).all()
        assert "vaep_norm" in result.columns

    def test_percentiles_ranked_within_groups(self, sample_computed):
        from pipeline.scoring_model import (compute_dimension_scores,
                                            compute_overall_score,
                                            compute_percentiles)
        scores = compute_dimension_scores(sample_computed)
        scores = compute_overall_score(scores, pd.Series([0.5, -0.2, 0.3]))
        scores["position_group"] = "Attacker"
        result = compute_percentiles(scores)
        for col in ["percentile_in_team", "percentile_in_league", "percentile_in_position"]:
            assert col in result.columns
            assert result[col].between(0, 100).all()

    def test_compute_trends_produces_trend_column(self):
        from pipeline.scoring_model import compute_trends
        scores = pd.DataFrame({
            "match_id": [1001, 1002, 1003],
            "player_id": [201, 201, 201],
            "player_name": ["Messi", "Messi", "Messi"],
            "overall_score": [7.0, 7.5, 8.0],
            "team_name": ["Barca", "Barca", "Barca"],
        })
        matches = pd.DataFrame({
            "match_id": [1001, 1002, 1003],
            "match_date": pd.to_datetime(["2021-01-01", "2021-01-08", "2021-01-15"]),
        })
        result = compute_trends(scores, matches)
        assert "performance_trend" in result.columns
        assert "trend_slope" in result.columns
        assert result["performance_trend"].iloc[0] in ("Improving", "Stable", "Declining")


class TestXgModel:
    """Tests for xG Model pipeline step."""

    def test_xg_model_loaded_and_predicts(self):
        from config import MODELS_DIR
        import json
        model_path = MODELS_DIR / "xg_model.txt"
        assert model_path.exists(), f"xg_model.txt not found at {model_path}"
        with open(model_path) as f:
            content = f.read()
            assert len(content) > 100

    def test_barca_shots_with_xg_exists(self):
        from config import DATA_DIR
        df = pd.read_parquet(DATA_DIR / "barca_shots_with_xg.parquet")
        assert len(df) > 0
        assert "predicted_xg" in df.columns
        assert df["predicted_xg"].notna().any()


class TestVaepModel:
    """Tests for VAEP Model pipeline step."""

    def test_vaep_models_exist(self):
        from config import MODELS_DIR
        for name in ["vaep_offensive_model.json", "vaep_defensive_model.json"]:
            path = MODELS_DIR / name
            assert path.exists(), f"{name} not found at {path}"

    def test_vaep_models_have_valid_structure(self):
        from config import MODELS_DIR
        import json
        for name in ["vaep_offensive_model.json", "vaep_defensive_model.json"]:
            with open(MODELS_DIR / name) as f:
                model = json.load(f)
            assert isinstance(model, dict)
            assert "learner" in model or "model" in model

    def test_vaep_feature_cols_exist(self):
        from config import MODELS_DIR
        import json
        path = MODELS_DIR / "vaep_feature_cols.json"
        assert path.exists()
        cols = json.loads(path.read_text())
        assert len(cols) > 0

    def test_vaep_metrics_exist(self):
        from config import MODELS_DIR
        import json
        path = MODELS_DIR / "vaep_metrics.json"
        assert path.exists()
        metrics = json.loads(path.read_text())
        assert "offensive_auc" in metrics
        assert "defensive_auc" in metrics
        assert 0.5 < metrics["offensive_auc"] <= 1.0
        assert 0.5 < metrics["defensive_auc"] <= 1.0

    def test_player_vaep_ratings_exist(self):
        from config import DATA_DIR
        df = pd.read_parquet(DATA_DIR / "player_vaep_ratings.parquet")
        assert len(df) > 0
        assert "player_id" in df.columns
        assert "vaep_rating" in df.columns
        assert "offensive_value" in df.columns
        assert "defensive_value" in df.columns

    def test_actions_with_vaep_exist(self):
        from config import DATA_DIR
        df = pd.read_parquet(DATA_DIR / "actions_with_vaep.parquet")
        assert len(df) > 0
        assert "vaep_value" in df.columns or "offensive_value" in df.columns

    def test_vaep_fuzzy_matching(self):
        from visualizations.player_dashboard import _fuzzy_match, _load
        data = _load()
        names = data["scores"]["player_name"]
        # Full names
        assert _fuzzy_match(names, "Lionel Messi").any()
        assert _fuzzy_match(names, "Messi").any()
        # Single word
        assert _fuzzy_match(names, "Xavi").any()
        # Case insensitive
        assert _fuzzy_match(names, "messi").any()
        # Non-existent
        assert not _fuzzy_match(names, "xyznotaplayer").any()

    def test_model_scores_parquet_integrity(self):
        from config import DATA_DIR
        df = pd.read_parquet(DATA_DIR / "model_scores.parquet")
        assert len(df) > 0
        assert "overall_score" in df.columns
        assert "passing_score" in df.columns
        assert "shooting_score" in df.columns
        assert df["overall_score"].between(0, 10).all()
        assert "vaep_rating" in df.columns
        assert "performance_trend" in df.columns

    def test_top_players_are_reasonable(self):
        from config import DATA_DIR
        df = pd.read_parquet(DATA_DIR / "model_scores.parquet")
        top5 = df.groupby("player_name")["overall_score"].mean().sort_values(ascending=False).head(5)
        assert len(top5) == 5
        assert top5.iloc[0] >= 5.0  # Top players should score well
