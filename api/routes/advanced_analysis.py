"""
api/routes/advanced_analysis.py — ML-Driven Advanced Analysis Endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import pandas as pd
from api.routes._shared import _load_data, _sf, _si
from pipeline.advanced_analysis import (
    PerformanceForecaster, AnomalyDetector, PlayerSimilarityEngine,
    ConsistencyAnalyzer, MomentumAnalyzer, InjuryRiskEstimator,
    AdvancedAnalysisEngine
)

router = APIRouter()

engine = AdvancedAnalysisEngine()


def _get_player_name(scores, player_id: int) -> str:
    match = scores[scores["player_id"] == player_id]
    if len(match):
        return str(match.iloc[0].get("player_name", f"Player {player_id}"))
    return f"Player {player_id}"


def _merge_match_dates(scores: pd.DataFrame, matches: pd.DataFrame) -> pd.DataFrame:
    """Merge match_date into scores for time-based analysis."""
    if "match_date" in scores.columns:
        return scores
    md = matches[["match_id", "match_date"]].copy()
    md["match_date"] = pd.to_datetime(md["match_date"], errors="coerce")
    result = scores.merge(md, on="match_id", how="left")
    result["match_date"] = result["match_date"].ffill()
    return result


def _get_player_scores(d: dict, player_id: int) -> pd.DataFrame:
    """Get player scores with match_date merged in."""
    ps = d["scores"][d["scores"]["player_id"] == player_id].copy()
    if len(ps):
        ps = _merge_match_dates(ps, d["matches"])
    return ps


@router.get("/player/{player_id}/advanced")
def get_advanced_analysis(player_id: int):
    d = _load_data()
    player_scores = _get_player_scores(d, player_id)
    if not len(player_scores):
        raise HTTPException(404, f"Player {player_id} not found")

    merged_scores = _merge_match_dates(d["scores"], d["matches"])
    result = engine.analyze_all(
        player_id, merged_scores, d["computed"], d["events"]
    )
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@router.get("/player/{player_id}/forecast")
def get_forecast(player_id: int):
    d = _load_data()
    ps = _get_player_scores(d, player_id)
    if not len(ps):
        raise HTTPException(404, f"Player {player_id} not found")

    result = PerformanceForecaster().forecast(ps)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return {
        "player_id": player_id,
        "player_name": _get_player_name(d["scores"], player_id),
        "forecast": result,
    }


@router.get("/player/{player_id}/anomalies")
def get_anomalies(player_id: int):
    d = _load_data()
    ps = _get_player_scores(d, player_id)
    if not len(ps):
        raise HTTPException(404, f"Player {player_id} not found")

    result = AnomalyDetector().detect(ps, d["computed"])
    if "error" in result:
        raise HTTPException(400, result["error"])
    return {
        "player_id": player_id,
        "player_name": _get_player_name(d["scores"], player_id),
        "anomalies": result,
    }


@router.get("/player/{player_id}/similar")
def get_similar_players(
    player_id: int,
    top_n: int = Query(8, ge=1, le=20),
):
    d = _load_data()
    ps = d["scores"][d["scores"]["player_id"] == player_id]
    if not len(ps):
        raise HTTPException(404, f"Player {player_id} not found")

    result = PlayerSimilarityEngine(top_n=top_n).find_similar(player_id, d["scores"])
    if "error" in result:
        raise HTTPException(400, result["error"])
    return {
        "player_id": player_id,
        "player_name": _get_player_name(d["scores"], player_id),
        "similarity": result,
    }


@router.get("/player/{player_id}/consistency")
def get_consistency(player_id: int):
    d = _load_data()
    ps = _get_player_scores(d, player_id)
    if not len(ps):
        raise HTTPException(404, f"Player {player_id} not found")

    result = ConsistencyAnalyzer().analyze(ps)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return {
        "player_id": player_id,
        "player_name": _get_player_name(d["scores"], player_id),
        "consistency": result,
    }


@router.get("/player/{player_id}/momentum")
def get_momentum(player_id: int):
    d = _load_data()
    ps = _get_player_scores(d, player_id)
    if not len(ps):
        raise HTTPException(404, f"Player {player_id} not found")

    result = MomentumAnalyzer().analyze(ps)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return {
        "player_id": player_id,
        "player_name": _get_player_name(d["scores"], player_id),
        "momentum": result,
    }


@router.get("/player/{player_id}/injury-risk")
def get_injury_risk(player_id: int):
    d = _load_data()
    ps = _get_player_scores(d, player_id)
    if not len(ps):
        raise HTTPException(404, f"Player {player_id} not found")

    merged_scores = _merge_match_dates(d["scores"], d["matches"])
    result = InjuryRiskEstimator().estimate(player_id, merged_scores, d["computed"], d["events"])
    if "error" in result:
        raise HTTPException(400, result["error"])
    return {
        "player_id": player_id,
        "player_name": _get_player_name(d["scores"], player_id),
        "injury_risk": result,
    }


@router.get("/analysis/top-performers")
def get_top_performers(
    min_matches: int = Query(5, ge=1),
    position: Optional[str] = Query(None),
    sort_by: str = Query("overall_score", regex="^(overall_score|momentum|consistency)$"),
    limit: int = Query(20, ge=1, le=100),
):
    d = _load_data()
    sc = d["scores"]

    if position:
        sc = sc[sc["position_group"].str.lower() == position.lower()]

    player_avgs = sc.groupby(["player_id", "player_name", "position_group"]).agg(
        overall_score=("overall_score", "mean"),
        matches_played=("match_id", "nunique"),
    ).reset_index()

    player_avgs = player_avgs[player_avgs["matches_played"] >= min_matches]

    if sort_by == "momentum":
        rankings = []
        for _, row in player_avgs.iterrows():
            ps = _get_player_scores(d, row["player_id"])
            mom = MomentumAnalyzer().analyze(ps)
            momentum_score = mom.get("momentum_score", 0) if "error" not in mom else 0
            rankings.append((row, momentum_score))
        rankings.sort(key=lambda x: x[1], reverse=True)
        result = [
            {
                "player_id": int(r[0]["player_id"]),
                "player_name": str(r[0]["player_name"]),
                "position": str(r[0]["position_group"]),
                "matches_played": int(r[0]["matches_played"]),
                "momentum_score": round(float(r[1]), 4),
                "overall_score": round(float(r[0]["overall_score"]), 4),
            }
            for r in rankings[:limit]
        ]
        return {"sort_by": "momentum", "results": result}

    elif sort_by == "consistency":
        rankings = []
        merged_scores = _merge_match_dates(d["scores"], d["matches"])
        for _, row in player_avgs.iterrows():
            ps = merged_scores[merged_scores["player_id"] == row["player_id"]]
            con = ConsistencyAnalyzer().analyze(ps)
            con_score = con.get("consistency_score", 0) if "error" not in con else 0
            rankings.append((row, con_score))
        rankings.sort(key=lambda x: x[1], reverse=True)
        result = [
            {
                "player_id": int(r[0]["player_id"]),
                "player_name": str(r[0]["player_name"]),
                "position": str(r[0]["position_group"]),
                "matches_played": int(r[0]["matches_played"]),
                "consistency_score": round(float(r[1]), 4),
                "overall_score": round(float(r[0]["overall_score"]), 4),
            }
            for r in rankings[:limit]
        ]
        return {"sort_by": "consistency", "results": result}

    else:
        player_avgs = player_avgs.sort_values("overall_score", ascending=False).head(limit)
        result = [
            {
                "player_id": int(row["player_id"]),
                "player_name": str(row["player_name"]),
                "position": str(row["position_group"]),
                "matches_played": int(row["matches_played"]),
                "overall_score": round(float(row["overall_score"]), 4),
            }
            for _, row in player_avgs.iterrows()
        ]
        return {"sort_by": "overall_score", "results": result}
