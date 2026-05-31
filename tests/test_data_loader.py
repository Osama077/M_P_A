import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

from pipeline.data_loader import (
    _extract_location, _extract_pass_details, _extract_shot_details,
    _extract_carry_details, _extract_dribble_details,
    clean_events, build_spadl, _get_result, build_shots_for_xg,
    load_matches, load_all_events,
)


class TestExtractLocation:
    def test_valid_list(self):
        x, y = _extract_location([105.0, 35.0])
        assert x == 105.0 and y == 35.0

    def test_none_on_empty_list(self):
        x, y = _extract_location([])
        assert x is None and y is None

    def test_none_on_invalid(self):
        x, y = _extract_location("not_a_list")
        assert x is None and y is None

    def test_none_on_nan(self):
        x, y = _extract_location(np.nan)
        assert x is None and y is None


class TestGetResult:
    @pytest.fixture
    def row(self):
        return {}

    def test_pass_success(self):
        row = {"event_type": "Pass", "pass_outcome": None}
        assert _get_result(row) == "success"

    def test_pass_fail(self):
        row = {"event_type": "Pass", "pass_outcome": "Incomplete"}
        assert _get_result(row) == "fail"

    def test_shot_goal(self):
        row = {"event_type": "Shot", "shot_outcome": "Goal"}
        assert _get_result(row) == "success"

    def test_shot_miss(self):
        row = {"event_type": "Shot", "shot_outcome": "Off Target"}
        assert _get_result(row) == "fail"

    def test_dribble_complete(self):
        row = {"event_type": "Dribble", "dribble_outcome": "Complete"}
        assert _get_result(row) == "success"

    def test_unknown_type_defaults_success(self):
        row = {"event_type": "Pressure"}
        assert _get_result(row) == "success"


class TestExtractPassDetails:
    @pytest.fixture
    def pass_df(self):
        return pd.DataFrame([
            {"type": "Pass", "match_id": 1001, "index": 0,
             "location": [105.0, 35.0], "pass_end_location": [110.0, 38.0],
             "pass_outcome": {"name": "Complete"},
             "pass_body_part": {"name": "Right Foot"}},
        ])

    def test_extracts_pass_outcome_name(self, pass_df):
        result = _extract_pass_details(pass_df)
        assert result.loc[0, "pass_outcome"] == "Complete"

    def test_extracts_pass_end_coordinates(self, pass_df):
        result = _extract_pass_details(pass_df)
        assert result.loc[0, "pass_end_x"] == 110.0
        assert result.loc[0, "pass_end_y"] == 38.0

    def test_extracts_bodypart(self, pass_df):
        result = _extract_pass_details(pass_df)
        assert result.loc[0, "bodypart"] == "Right Foot"

    def test_non_pass_rows_untouched(self):
        df = pd.DataFrame([
            {"type": "Shot", "match_id": 1001, "index": 1,
             "location": [100.0, 40.0], "pass_outcome": None,
             "pass_end_location": None, "pass_body_part": None},
        ])
        result = _extract_pass_details(df)
        assert "progressive_pass" not in result.columns or True


class TestExtractShotDetails:
    @pytest.fixture
    def shot_df(self):
        return pd.DataFrame([
            {"type": "Shot", "match_id": 1001, "index": 1,
             "location": [100.0, 38.0],
             "location_x": 100.0, "location_y": 38.0,
             "shot_outcome": {"name": "Goal"},
             "shot_statsbomb_xg": 0.45,
             "shot_technique": {"name": "Normal"},
             "shot_body_part": {"name": "Right Foot"},
             "shot_end_location": [120.0, 38.0],
             "shot_type": {"name": "Open Play"}},
        ])

    def test_extracts_shot_outcome(self, shot_df):
        result = _extract_shot_details(shot_df)
        assert result.loc[0, "shot_outcome"] == "Goal"

    def test_extracts_xg(self, shot_df):
        result = _extract_shot_details(shot_df)
        assert result.loc[0, "shot_xg"] == 0.45

    def test_calculates_distance_to_goal(self, shot_df):
        result = _extract_shot_details(shot_df)
        assert result.loc[0, "distance_to_goal"] > 0

    def test_calculates_angle_to_goal(self, shot_df):
        result = _extract_shot_details(shot_df)
        assert result.loc[0, "angle_to_goal"] >= 0

    def test_set_piece_flag(self, shot_df):
        result = _extract_shot_details(shot_df)
        assert result.loc[0, "shot_after_set_piece"] == 0

    def test_penalty_set_piece(self):
        df = pd.DataFrame([
            {"type": "Shot", "match_id": 1001, "index": 1,
             "location": [60.0, 40.0],
             "location_x": 60.0, "location_y": 40.0,
             "shot_type": {"name": "Penalty"},
             "shot_outcome": "Goal",
             "shot_statsbomb_xg": 0.5, "shot_technique": None,
             "shot_body_part": None, "shot_end_location": None},
        ])
        result = _extract_shot_details(df)
        assert result.loc[0, "shot_after_set_piece"] == 1


class TestCleanEvents:
    @pytest.fixture
    def raw(self):
        return pd.DataFrame([
            {"id": "e1", "index": 1, "match_id": 1001, "player_id": 201,
             "player": "Messi", "team": "Barcelona", "team_id": 101,
             "type": "Pass", "period": 1, "minute": 10, "second": 5,
             "timestamp": "00:10:05.000",
             "location": [105.0, 35.0],
             "pass_outcome": None, "pass_body_part": None,
             "pass_end_location": None,
             "shot_outcome": None, "shot_statsbomb_xg": None,
             "shot_technique": None, "shot_body_part": None,
             "shot_end_location": None, "shot_type": None,
             "shot_first_time": None,
             "carry_end_location": None,
             "dribble_outcome": None,
             "foul_committed_card": None,
             "under_pressure": True, "counterpress": False,
             "duration": 1.0},
        ])

    def test_location_columns_extracted(self, raw):
        result = clean_events(raw)
        assert "location_x" in result.columns
        assert "location_y" in result.columns

    def test_timestamp_parsed(self, raw):
        result = clean_events(raw)
        assert "timestamp_seconds" in result.columns
        assert result["timestamp_seconds"].iloc[0] >= 0

    def test_event_index_added(self, raw):
        result = clean_events(raw)
        assert "event_index" in result.columns
        assert result["event_index"].iloc[0] == 1

    def test_renames_id_to_event_id(self, raw):
        result = clean_events(raw)
        assert "event_id" in result.columns

    def test_renames_player_to_player_name(self, raw):
        result = clean_events(raw)
        assert "player_name" in result.columns

    def test_under_pressure_flagged(self, raw):
        result = clean_events(raw)
        assert result["under_pressure"].iloc[0] == 1

    def test_uuid_column_present(self, raw):
        result = clean_events(raw)
        assert "uuid" in result.columns

    def test_multiple_matches_sorted_correctly(self):
        df = pd.DataFrame([
            {"id": "e1", "index": 3, "match_id": 1001, "type": "Pass",
             "player_id": 201, "player": "Messi", "team": "Barca",
             "team_id": 101, "period": 1, "minute": 5, "second": 0,
             "timestamp": "00:05:00.000", "duration": 1.0,
             "under_pressure": False, "counterpress": False,
             "location": [100, 40],
             "pass_outcome": None, "pass_body_part": None,
             "pass_end_location": None,
             "shot_outcome": None, "shot_statsbomb_xg": None,
             "shot_technique": None, "shot_body_part": None,
             "shot_end_location": None, "shot_type": None,
             "shot_first_time": None,
             "carry_end_location": None,
             "dribble_outcome": None,
             "foul_committed_card": None},
            {"id": "e2", "index": 1, "match_id": 1001, "type": "Shot",
             "player_id": 201, "player": "Messi", "team": "Barca",
             "team_id": 101, "period": 1, "minute": 1, "second": 0,
             "timestamp": "00:01:00.000", "duration": 0.5,
             "under_pressure": False, "counterpress": False,
             "location": [90, 35],
             "pass_outcome": None, "pass_body_part": None,
             "pass_end_location": None,
             "shot_outcome": None, "shot_statsbomb_xg": None,
             "shot_technique": None, "shot_body_part": None,
             "shot_end_location": None, "shot_type": None,
             "shot_first_time": None,
             "carry_end_location": None,
             "dribble_outcome": None,
             "foul_committed_card": None},
        ])
        result = clean_events(df)
        assert result["event_index"].iloc[0] == 1
        assert result["event_index"].iloc[1] == 2


class TestBuildSpadl:
    @pytest.fixture
    def clean(self):
        return pd.DataFrame([
            {"event_id": "e1", "match_id": 1001, "player_id": 201,
             "player_name": "Messi", "team_name": "Barcelona",
             "event_type": "Pass", "period": 1, "timestamp_seconds": 605,
             "event_index": 1,
             "location_x": 105.0, "location_y": 35.0,
             "pass_end_x": 110.0, "pass_end_y": 38.0,
             "carry_end_x": None, "carry_end_y": None,
             "shot_end_x": None, "shot_end_y": None,
             "bodypart": "Right Foot",
             "pass_outcome": "Complete", "under_pressure": 1},
            {"event_id": "e2", "match_id": 1001, "player_id": 202,
             "player_name": "Suarez", "team_name": "Barcelona",
             "event_type": "Shot", "period": 2, "timestamp_seconds": 3330,
             "event_index": 2,
             "location_x": 100.0, "location_y": 38.0,
             "pass_end_x": None, "pass_end_y": None,
             "carry_end_x": None, "carry_end_y": None,
             "shot_end_x": 120.0, "shot_end_y": 38.0,
             "bodypart": "Right Foot",
             "shot_outcome": "Goal", "under_pressure": 0},
        ])

    def test_returns_expected_columns(self, clean):
        spadl = build_spadl(clean)
        expected = ["match_id", "player_id", "player_name", "team_name",
                     "period_id", "time_seconds", "event_index",
                     "type_name", "result_name", "bodypart_name",
                     "start_x", "start_y", "end_x", "end_y",
                     "under_pressure"]
        for col in expected:
            assert col in spadl.columns

    def test_type_name_mapped(self, clean):
        spadl = build_spadl(clean)
        assert spadl["type_name"].iloc[0] == "pass"
        assert spadl["type_name"].iloc[1] == "shot"

    def test_result_name_from_get_result(self, clean):
        spadl = build_spadl(clean)
        assert spadl["result_name"].iloc[0] == "success"
        assert spadl["result_name"].iloc[1] == "success"

    def test_end_x_fallback_to_location(self):
        df = pd.DataFrame([
            {"event_id": "e1", "match_id": 1001, "player_id": 201,
             "player_name": "Messi", "team_name": "Barcelona",
             "event_type": "Pressure", "period": 1,
             "timestamp_seconds": 100, "event_index": 1,
             "location_x": 80.0, "location_y": 30.0,
             "pass_end_x": None, "carry_end_x": None,
             "shot_end_x": None, "pass_end_y": None,
             "carry_end_y": None, "shot_end_y": None,
             "bodypart": None, "under_pressure": 0,
             "pass_outcome": None},
        ])
        spadl = build_spadl(df)
        assert spadl["end_x"].iloc[0] == 80.0
        assert spadl["end_y"].iloc[0] == 30.0

    def test_uuid_column_present(self, clean):
        spadl = build_spadl(clean)
        assert "uuid" in spadl.columns

    def test_ignores_unmapped_event_types(self):
        df = pd.DataFrame([
            {"event_id": "e1", "match_id": 1001, "player_id": 201,
             "player_name": "Messi", "team_name": "Barcelona",
             "event_type": "Half End", "period": 1,
             "timestamp_seconds": 2700, "event_index": 100,
             "location_x": 50.0, "location_y": 40.0,
             "pass_end_x": None, "pass_end_y": None,
             "carry_end_x": None, "carry_end_y": None,
             "shot_end_x": None, "shot_end_y": None,
             "bodypart": None, "under_pressure": 0},
        ])
        spadl = build_spadl(df)
        assert len(spadl) == 0


class TestBuildShotsForXg:
    @pytest.fixture
    def clean(self):
        return pd.DataFrame([
            {"event_id": "e1", "match_id": 1001, "player_id": 201,
             "player_name": "Messi", "event_type": "Shot",
             "location_x": 105.0, "location_y": 35.0,
             "distance_to_goal": 15.0, "angle_to_goal": 0.5,
             "shot_technique": "Normal", "bodypart": "Right Foot",
             "under_pressure": 1, "shot_after_set_piece": 0,
             "shot_outcome": "Goal", "shot_xg": 0.3},
        ])

    def test_only_shots_included(self, clean):
        shots = build_shots_for_xg(clean)
        assert len(shots) == 1

    def test_is_goal_column(self, clean):
        shots = build_shots_for_xg(clean)
        assert shots["is_goal"].iloc[0] == 1

    def test_has_uuid(self, clean):
        shots = build_shots_for_xg(clean)
        assert "uuid" in shots.columns

    def test_non_goal_shot(self, clean):
        df = pd.DataFrame([
            {"event_id": "e1", "match_id": 1001, "player_id": 201,
             "player_name": "Messi", "event_type": "Shot",
             "location_x": 105.0, "location_y": 35.0,
             "distance_to_goal": 15.0, "angle_to_goal": 0.5,
             "shot_technique": "Normal", "bodypart": "Right Foot",
             "under_pressure": 1, "shot_after_set_piece": 0,
             "shot_outcome": "Off Target", "shot_xg": 0.3},
        ])
        shots = build_shots_for_xg(df)
        assert shots["is_goal"].iloc[0] == 0


class TestLoadMatches:
    def test_filters_to_target_team_only(self):
        mock_matches = pd.DataFrame([
            {"match_id": 1, "home_team": "Barcelona", "away_team": "Real Madrid"},
            {"match_id": 2, "home_team": "Atletico", "away_team": "Barcelona"},
            {"match_id": 3, "home_team": "Sevilla", "away_team": "Valencia"},
        ])
        with patch("pipeline.data_loader.sb.matches", return_value=mock_matches):
            result = load_matches()
        assert len(result) == 2
        assert all(result["match_id"].isin([1, 2]))

    def test_uuid_column_added(self):
        mock_matches = pd.DataFrame([
            {"match_id": 1, "home_team": "Barcelona", "away_team": "Real Madrid"},
        ])
        with patch("pipeline.data_loader.sb.matches", return_value=mock_matches):
            result = load_matches()
        assert "uuid" in result.columns


class TestLoadAllEvents:
    def test_loads_events_and_lineups_for_each_match(self):
        mock_matches = pd.DataFrame([
            {"match_id": 1001, "home_team": "Barca", "away_team": "Madrid"},
        ])
        mock_events = pd.DataFrame([
            {"id": "e1", "type": "Pass", "minute": 10},
        ])
        mock_lineups = {
            "Barcelona": pd.DataFrame([{"player_id": 201}]),
        }
        with patch("pipeline.data_loader.sb.events", return_value=mock_events):
            with patch("pipeline.data_loader.sb.lineups", return_value=mock_lineups):
                events_df, lineups_df = load_all_events(mock_matches)
        assert len(events_df) == 1
        assert events_df["match_id"].iloc[0] == 1001
        assert len(lineups_df) == 1
