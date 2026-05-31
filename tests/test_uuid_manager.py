import pandas as pd
import pytest
import uuid as uuid_lib

from utils.uuid_manager import (
    generate_uuid, deterministic_uuid, add_uuid_column,
    add_uuids_to_all, get_uuid_for_record,
)


class TestGenerateUuid:
    def test_returns_valid_uuid_string(self):
        u = generate_uuid()
        uuid_lib.UUID(u)

    def test_returns_different_values(self):
        assert generate_uuid() != generate_uuid()


class TestDeterministicUuid:
    def test_same_inputs_produce_same_uuid(self):
        a = deterministic_uuid("match_1", "player_42")
        b = deterministic_uuid("match_1", "player_42")
        assert a == b

    def test_different_inputs_produce_different_uuids(self):
        a = deterministic_uuid("match_1", "player_42")
        b = deterministic_uuid("match_1", "player_43")
        assert a != b

    def test_works_with_ints(self):
        u = deterministic_uuid(1001, 201)
        uuid_lib.UUID(u)

    def test_returns_valid_uuid_object(self):
        u = deterministic_uuid("test")
        assert str(uuid_lib.UUID(u)) == u


class TestAddUuidColumn:
    def test_random_uuid_column_added(self):
        df = pd.DataFrame({"x": [1, 2]})
        result = add_uuid_column(df, "uuid")
        assert "uuid" in result.columns
        assert result.columns[0] == "uuid"
        assert result["uuid"].iloc[0] != result["uuid"].iloc[1]

    def test_deterministic_uuid_based_on_columns(self):
        df = pd.DataFrame({"match_id": [1001, 1001], "player_id": [201, 202]})
        result = add_uuid_column(df, "uuid", based_on=["match_id", "player_id"])
        assert result["uuid"].iloc[0] != result["uuid"].iloc[1]
        same = add_uuid_column(df.iloc[:1], "uuid", based_on=["match_id", "player_id"])
        assert same["uuid"].iloc[0] == result["uuid"].iloc[0]

    def test_original_column_order_preserved_except_uuid_first(self):
        df = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
        result = add_uuid_column(df, "uuid")
        assert list(result.columns) == ["uuid", "a", "b", "c"]


class TestAddUuidsToAll:
    @pytest.fixture
    def dataframes(self):
        return {
            "events_df":       pd.DataFrame({"event_id": ["e1", "e2"]}),
            "matches_df":      pd.DataFrame({"match_id": [1001]}),
            "lineups_df":      pd.DataFrame({"match_id": [1001], "player_id": [201]}),
            "computed_df":     pd.DataFrame({"match_id": [1001], "player_id": [201]}),
            "model_scores_df": pd.DataFrame({"match_id": [1001], "player_id": [201]}),
            "player_vaep_df":  pd.DataFrame({"match_id": [1001], "player_id": [201]}),
            "spadl_df":        pd.DataFrame({"match_id": [1001], "event_index": [1]}),
        }

    def test_all_dataframes_get_uuids(self, dataframes):
        result = add_uuids_to_all(**dataframes)
        for key in ["events", "matches", "lineups", "computed",
                     "model_scores", "player_vaep", "spadl"]:
            assert "uuid" in result[key].columns

    def test_deterministic_on_match_id_plus_player(self, dataframes):
        result = add_uuids_to_all(**dataframes)
        assert result["computed"]["uuid"].iloc[0] == result["model_scores"]["uuid"].iloc[0]

    def test_deterministic_on_event_id(self, dataframes):
        result = add_uuids_to_all(**dataframes)
        expected = deterministic_uuid("e1")
        assert result["events"]["uuid"].iloc[0] == expected


class TestGetUuidForRecord:
    def test_returns_consistent_uuid(self):
        a = get_uuid_for_record("match_player", match_id=1001, player_id=201)
        b = get_uuid_for_record("match_player", match_id=1001, player_id=201)
        assert a == b

    def test_different_tables_give_different_uuids(self):
        a = get_uuid_for_record("match_player", match_id=1001, player_id=201)
        b = get_uuid_for_record("player_rating", match_id=1001, player_id=201)
        assert a != b
