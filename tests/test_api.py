import pytest
from fastapi import status


class TestHealth:
    def test_root_health(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "running"
        assert data["api"] == "Match Performance Analysis API"
        assert data["version"] == "1.0.0"

    def test_api_v1_health(self, client):
        resp = client.get("/api/v1/")
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"


class TestAnalysisRoutes:
    def test_analyze_match_not_found(self, client):
        resp = client.post("/api/v1/analyze/match/9999")
        assert resp.status_code == 404

    def test_analyze_match_success(self, client):
        resp = client.post("/api/v1/analyze/match/1001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["match_id"] == 1001

    def test_analyze_season(self, client):
        payload = {"competition_id": 11, "season_id": 27}
        resp = client.post("/api/v1/analyze/season", json=payload)
        assert resp.status_code == 200
        assert resp.json()["competition_id"] == 11
        assert resp.json()["season_id"] == 27


class TestPlayerRoutes:
    def test_list_players(self, client):
        resp = client.get("/api/v1/player/list")
        assert resp.status_code == 200
        data = resp.json()
        assert "player_items" in data
        assert len(data["player_items"]) > 0

    def test_get_player_score(self, client):
        resp = client.get("/api/v1/player/201/score")
        assert resp.status_code == 200
        data = resp.json()
        assert data["player_id"] == 201
        assert "scores" in data
        assert "overall_score" in data["scores"]

    def test_get_player_score_not_found(self, client):
        resp = client.get("/api/v1/player/9999/score")
        assert resp.status_code == 404

    def test_get_player_score_with_match_id(self, client):
        resp = client.get("/api/v1/player/201/score?match_id=1001")
        assert resp.status_code == 200
        assert resp.json()["match_id"] == 1001

    def test_get_player_stats(self, client):
        resp = client.get("/api/v1/player/201/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "passing" in data
        assert "shooting" in data
        assert "physical" in data

    def test_get_player_history(self, client):
        resp = client.get("/api/v1/player/201/history")
        assert resp.status_code == 200
        data = resp.json()
        assert "matches" in data
        assert "season_avg" in data

    def test_compare_players(self, client):
        resp = client.get("/api/v1/player/compare?player_ids=201,202")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["comparison"]) == 2

    def test_compare_single_player(self, client):
        resp = client.get("/api/v1/player/compare?player_ids=201")
        assert resp.status_code == 200
        assert len(resp.json()["comparison"]) == 1


class TestTeamRoutes:
    def test_team_summary_found(self, client):
        resp = client.get("/api/v1/team/Barcelona/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "team_stats" in data
        assert "players" in data

    def test_team_summary_not_found(self, client):
        resp = client.get("/api/v1/team/UnknownTeam/summary")
        assert resp.status_code == 404

    def test_team_heatmap(self, client):
        resp = client.get("/api/v1/team/Barcelona/heatmap?match_id=1001")
        assert resp.status_code == 200
        data = resp.json()
        assert "heatmap_data" in data


class TestMatchRoutes:
    def test_match_report_found(self, client):
        resp = client.get("/api/v1/match/1001/report")
        assert resp.status_code == 200
        data = resp.json()
        assert data["match_id"] == 1001
        assert "home_team" in data
        assert "away_team" in data
        assert "all_players" in data

    def test_match_report_not_found(self, client):
        resp = client.get("/api/v1/match/9999/report")
        assert resp.status_code == 404

    def test_match_events(self, client):
        resp = client.get("/api/v1/match/1001/events")
        assert resp.status_code == 200
        data = resp.json()
        assert data["match_id"] == 1001
        assert "events" in data
        assert "total_events" in data

    def test_match_events_with_filters(self, client):
        resp = client.get(
            "/api/v1/match/1001/events?player_id=201&event_type=Pass&period=1&limit=10"
        )
        assert resp.status_code == 200

    def test_match_events_pagination(self, client):
        resp = client.get("/api/v1/match/1001/events?limit=5&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert data["limit"] == 5
        assert data["offset"] == 0


class TestBenchmarkRoutes:
    def test_benchmark_valid_position(self, client):
        resp = client.get("/api/v1/benchmark/Attacker")
        assert resp.status_code == 200
        data = resp.json()
        assert data["position_group"] == "Attacker"

    def test_benchmark_invalid_position(self, client):
        resp = client.get("/api/v1/benchmark/Invalid")
        assert resp.status_code == 400

    def test_benchmark_midfielder(self, client):
        resp = client.get("/api/v1/benchmark/Midfielder")
        assert resp.status_code == 200


class TestAdvancedAnalysisRoutes:
    def test_forecast_found(self, client):
        resp = client.get("/api/v1/player/201/forecast")
        assert resp.status_code == 200
        data = resp.json()
        assert "forecast" in data
        assert data["player_id"] == 201

    def test_forecast_not_found(self, client):
        resp = client.get("/api/v1/player/9999/forecast")
        assert resp.status_code == 404

    def test_anomalies_found(self, client):
        resp = client.get("/api/v1/player/201/anomalies")
        assert resp.status_code == 200
        data = resp.json()
        assert "anomalies" in data

    def test_similar_players_found(self, client):
        resp = client.get("/api/v1/player/201/similar")
        assert resp.status_code == 200
        data = resp.json()
        assert "similarity" in data

    def test_consistency_found(self, client):
        resp = client.get("/api/v1/player/201/consistency")
        assert resp.status_code == 200
        data = resp.json()
        assert "consistency" in data

    def test_momentum_found(self, client):
        resp = client.get("/api/v1/player/201/momentum")
        assert resp.status_code == 200
        data = resp.json()
        assert "momentum" in data

    def test_injury_risk_found(self, client):
        resp = client.get("/api/v1/player/201/injury-risk")
        assert resp.status_code == 200

    def test_top_performers_default(self, client):
        resp = client.get("/api/v1/analysis/top-performers")
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert data["sort_by"] == "overall_score"

    def test_top_performers_by_position(self, client):
        resp = client.get("/api/v1/analysis/top-performers?position=attacker")
        assert resp.status_code == 200

    def test_top_performers_by_momentum(self, client):
        resp = client.get("/api/v1/analysis/top-performers?sort_by=momentum&min_matches=1")
        assert resp.status_code == 200

    def test_top_performers_by_consistency(self, client):
        resp = client.get("/api/v1/analysis/top-performers?sort_by=consistency&min_matches=1")
        assert resp.status_code == 200

    def test_advanced_endpoint_found(self, client):
        resp = client.get("/api/v1/player/201/advanced")
        assert resp.status_code == 200
        data = resp.json()
        assert "forecast" in data or "error" in data
