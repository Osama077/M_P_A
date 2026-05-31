import pandas as pd
import pytest

from pipeline.feature_engineering import (
    compute_passing_features, compute_shooting_features,
    compute_positioning_features, compute_pressing_features,
    compute_movement_features, compute_physical_features,
    compute_behavioral_features, merge_all_features,
)


@pytest.fixture
def events():
    return pd.DataFrame([
        # Player 201 - Passes
        {"match_id": 1001, "player_id": 201, "player_name": "Messi",
         "team_name": "Barcelona", "event_type": "Pass",
         "pass_outcome": None, "is_progressive_pass": 1,
         "under_pressure": 1, "pass_length": 12.0},
        {"match_id": 1001, "player_id": 201, "player_name": "Messi",
         "team_name": "Barcelona", "event_type": "Pass",
         "pass_outcome": "Complete", "is_progressive_pass": 0,
         "under_pressure": 0, "pass_length": 8.0},
        {"match_id": 1001, "player_id": 201, "player_name": "Messi",
         "team_name": "Barcelona", "event_type": "Pass",
         "pass_outcome": "Incomplete", "is_progressive_pass": 0,
         "under_pressure": 0, "pass_length": 15.0},
        # Player 201 - Shot
        {"match_id": 1001, "player_id": 201, "player_name": "Messi",
         "team_name": "Barcelona", "event_type": "Shot",
         "shot_outcome": "Goal", "shot_xg": 0.45,
         "distance_to_goal": 15.0},
        {"match_id": 1001, "player_id": 201, "player_name": "Messi",
         "team_name": "Barcelona", "event_type": "Shot",
         "shot_outcome": "Off Target", "shot_xg": 0.12,
         "distance_to_goal": 22.0},
        # Player 201 - Carry
        {"match_id": 1001, "player_id": 201, "player_name": "Messi",
         "team_name": "Barcelona", "event_type": "Carry",
         "carry_end_x": 100.0, "location_x": 90.0,
         "carry_end_y": 35.0, "location_y": 32.0},
        # Player 201 - Dribble
        {"match_id": 1001, "player_id": 201, "player_name": "Messi",
         "team_name": "Barcelona", "event_type": "Dribble",
         "dribble_outcome": "Complete"},
        {"match_id": 1001, "player_id": 201, "player_name": "Messi",
         "team_name": "Barcelona", "event_type": "Dribble",
         "dribble_outcome": "Incomplete"},
        # Player 201 - Location events
        {"match_id": 1001, "player_id": 201, "player_name": "Messi",
         "team_name": "Barcelona", "event_type": "Pass",
         "location_x": 85.0, "location_y": 38.0},
        # Player 201 - Pressure
        {"match_id": 1001, "player_id": 201, "player_name": "Messi",
         "team_name": "Barcelona", "event_type": "Pressure",
         "duration": 2.0, "counterpress": 1},
        {"match_id": 1001, "player_id": 201, "player_name": "Messi",
         "team_name": "Barcelona", "event_type": "Pressure",
         "duration": 1.5, "counterpress": 0},
        # Player 201 - Behavioral
        {"match_id": 1001, "player_id": 201, "player_name": "Messi",
         "team_name": "Barcelona", "event_type": "Foul Committed",
         "foul_card": "Yellow Card"},
        {"match_id": 1001, "player_id": 201, "player_name": "Messi",
         "team_name": "Barcelona", "event_type": "Ball Receipt*"},
        {"match_id": 1001, "player_id": 201, "player_name": "Messi",
         "team_name": "Barcelona", "event_type": "Ball Receipt*"},
        {"match_id": 1001, "player_id": 201, "player_name": "Messi",
         "team_name": "Barcelona", "event_type": "Miscontrol"},
        # Player 202 - Passes
        {"match_id": 1001, "player_id": 202, "player_name": "Suarez",
         "team_name": "Barcelona", "event_type": "Pass",
         "pass_outcome": None, "is_progressive_pass": 0,
         "under_pressure": 0, "pass_length": 10.0},
        # Player 202 - Shot
        {"match_id": 1001, "player_id": 202, "player_name": "Suarez",
         "team_name": "Barcelona", "event_type": "Shot",
         "shot_outcome": "Goal", "shot_xg": 0.30,
         "distance_to_goal": 12.0},
        # Player 202 - Carry
        {"match_id": 1001, "player_id": 202, "player_name": "Suarez",
         "team_name": "Barcelona", "event_type": "Carry",
         "carry_end_x": 95.0, "location_x": 88.0,
         "carry_end_y": 36.0, "location_y": 34.0},
        # Player 202 - Period events for physical features
        {"match_id": 1001, "player_id": 202, "player_name": "Suarez",
         "team_name": "Barcelona", "event_type": "Pass",
         "period": 1, "location_x": 80.0, "location_y": 35.0,
         "under_pressure": 0, "counterpress": 0},
        {"match_id": 1001, "player_id": 202, "player_name": "Suarez",
         "team_name": "Barcelona", "event_type": "Pass",
         "period": 2, "location_x": 70.0, "location_y": 30.0,
         "under_pressure": 0, "counterpress": 0},
    ])


class TestComputePassingFeatures:
    def test_returns_expected_columns(self, events):
        result = compute_passing_features(events)
        expected = {"match_id", "player_id", "total_passes",
                     "complete_passes", "progressive_passes",
                     "passes_under_pressure", "avg_pass_length",
                     "pass_accuracy"}
        assert expected.issubset(set(result.columns))

    def test_aggregates_by_match_and_player(self, events):
        result = compute_passing_features(events)
        assert len(result) == 2

    def test_computes_accuracy(self, events):
        result = compute_passing_features(events)
        messi = result[result["player_id"] == 201].iloc[0]
        assert messi["total_passes"] == 4
        assert messi["complete_passes"] == 3
        assert messi["pass_accuracy"] == pytest.approx(75.0, rel=0.01)


class TestComputeShootingFeatures:
    def test_returns_expected_columns(self, events):
        result = compute_shooting_features(events)
        expected = {"match_id", "player_id", "total_shots",
                     "goals", "shots_on_target", "total_xg",
                     "avg_distance", "shot_accuracy", "xg_per_shot",
                     "xg_overperformance"}
        assert expected.issubset(set(result.columns))

    def test_calculates_shots(self, events):
        result = compute_shooting_features(events)
        messi = result[result["player_id"] == 201].iloc[0]
        assert messi["total_shots"] == 2

    def test_goal_count(self, events):
        result = compute_shooting_features(events)
        messi = result[result["player_id"] == 201].iloc[0]
        assert messi["goals"] == 1

    def test_xg_overperformance(self, events):
        result = compute_shooting_features(events)
        messi = result[result["player_id"] == 201].iloc[0]
        expected_over = 1 - (0.45 + 0.12)
        assert messi["xg_overperformance"] == pytest.approx(expected_over, rel=0.01)


class TestComputePositioningFeatures:
    def test_returns_expected_columns(self, events):
        result = compute_positioning_features(events)
        expected = {"match_id", "player_id", "avg_position_x",
                     "avg_position_y", "attacking_tendency"}
        assert expected.issubset(set(result.columns))


class TestComputePressingFeatures:
    def test_returns_expected_columns(self):
        df = pd.DataFrame([
            {"match_id": 1001, "player_id": 201,
             "event_type": "Pressure", "duration": 2.0,
             "counterpress": 1},
            {"match_id": 1001, "player_id": 201,
             "event_type": "Pressure", "duration": 1.0,
             "counterpress": 0},
        ])
        result = compute_pressing_features(df)
        assert "total_pressures" in result.columns
        assert result["total_pressures"].iloc[0] == 2

    def test_pressing_efficiency(self):
        df = pd.DataFrame([
            {"match_id": 1001, "player_id": 201,
             "event_type": "Pressure", "duration": 2.0,
             "counterpress": 1},
            {"match_id": 1001, "player_id": 201,
             "event_type": "Pressure", "duration": 1.5,
             "counterpress": 0},
        ])
        result = compute_pressing_features(df)
        assert result["pressing_efficiency"].iloc[0] == 50.0


class TestComputeMovementFeatures:
    def test_returns_carry_and_dribble_columns(self, events):
        result = compute_movement_features(events)
        expected = {"match_id", "player_id", "total_carries",
                     "total_carry_distance", "progressive_carries",
                     "total_dribbles", "successful_dribbles",
                     "dribble_success_rate"}
        assert expected.issubset(set(result.columns))

    def test_carry_distance_calculated(self, events):
        result = compute_movement_features(events)
        messi = result[result["player_id"] == 201].iloc[0]
        assert messi["total_carries"] > 0

    def test_dribble_success_rate(self, events):
        result = compute_movement_features(events)
        messi = result[result["player_id"] == 201].iloc[0]
        assert messi["dribble_success_rate"] == 50.0


class TestComputePhysicalFeatures:
    def test_returns_expected_columns(self, events):
        result = compute_physical_features(events)
        assert "total_actions" in result.columns
        assert "distance_covered" in result.columns
        assert "activity_drop_2nd_half" in result.columns


class TestComputeBehavioralFeatures:
    def test_returns_expected_columns(self, events):
        result = compute_behavioral_features(events)
        expected = {"match_id", "player_id", "fouls_committed",
                     "ball_receipts", "miscontrols",
                     "ball_retention_rate"}
        assert expected.issubset(set(result.columns))

    def test_ball_retention_rate(self, events):
        result = compute_behavioral_features(events)
        messi = result[result["player_id"] == 201].iloc[0]
        assert messi["ball_receipts"] == 2
        assert messi["ball_retention_rate"] == 50.0

    def test_card_counts(self, events):
        result = compute_behavioral_features(events)
        messi = result[result["player_id"] == 201].iloc[0]
        assert messi["yellow_cards"] == 1


class TestMergeAllFeatures:
    def test_returns_all_player_match_pairs(self, events):
        result = merge_all_features(events)
        assert len(result) == 2

    def test_includes_uuid(self, events):
        result = merge_all_features(events)
        assert "uuid" in result.columns

    def test_player_name_team_name_preserved(self, events):
        result = merge_all_features(events)
        assert "player_name" in result.columns
        assert "team_name" in result.columns

    def test_count_cols_are_integers(self, events):
        result = merge_all_features(events)
        for col in ["total_passes", "total_shots", "total_carries",
                     "total_dribbles", "fouls_committed"]:
            if col in result.columns:
                assert result[col].dtype == int or result[col].dtype == "int64"
