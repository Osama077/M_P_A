"""
api/routes/coaching.py — Coaching Decision Support Endpoints
Provides tactical advice, match predictions, and data validation reports.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import os
import numpy as np
import pandas as pd
from api.routes._shared import _load, _sf, _si
from pipeline.coaching_guidance import CoachingGuidanceEngine
from pipeline.match_prediction import MatchPredictor
from pipeline.data_validation import DataValidator
from pipeline.advanced_analysis import (
    PerformanceForecaster, ConsistencyAnalyzer, MomentumAnalyzer,
    InjuryRiskEstimator, AnomalyDetector
)

router = APIRouter()
guidance_engine = CoachingGuidanceEngine()
predictor = MatchPredictor()
validator = DataValidator()

TEAM_NAME = os.environ.get("TARGET_TEAM", "Barcelona")
BARCA_MATCH_IDS_CACHE = {}


def _get_barca_match_ids(d):
    scores = d["scores"]
    key = (TEAM_NAME, id(scores), scores.shape[0], scores["match_id"].iloc[0] if len(scores) else 0)
    if key not in BARCA_MATCH_IDS_CACHE:
        is_barca = scores["team_name"].astype(str).str.contains(TEAM_NAME, case=False, na=False)
        BARCA_MATCH_IDS_CACHE[key] = scores[is_barca]["match_id"].unique()
    return BARCA_MATCH_IDS_CACHE[key]


def _get_squad_players(d):
    barca_ids = _get_barca_match_ids(d)
    squad_ms = d["scores"][d["scores"]["match_id"].isin(barca_ids)]
    is_barca = squad_ms["team_name"].astype(str).str.contains(TEAM_NAME, case=False, na=False)
    return squad_ms[is_barca]["player_id"].unique()


def _get_player_name(scores, player_id):
    match = scores[scores["player_id"] == player_id]
    if len(match):
        return str(match.iloc[0].get("player_name", f"Player {player_id}"))
    return f"Player {player_id}"


@router.get("/coaching/squad")
def get_overall_squad_coaching(season: Optional[str] = Query(None)):
    """Tactical advice for the overall squad (no specific match required)."""
    d = _load(season=season)
    sc = d["scores"]
    cf = d["computed"]

    squad_ids = _get_squad_players(d)
    barca_ms = sc[(sc["player_id"].isin(squad_ids)) & (sc["team_name"].astype(str).str.contains(TEAM_NAME, case=False, na=False))]
    if not len(barca_ms):
        raise HTTPException(404, "No squad data found")

    latest_match_id = int(barca_ms["match_id"].max())
    barca_ms_latest = barca_ms[barca_ms["match_id"] == latest_match_id]
    barca_cf = cf[(cf["match_id"] == latest_match_id) & (cf["player_id"].isin(squad_ids))]

    team_stats = {
        "avg_overall_score": _sf(barca_ms["overall_score"].mean()),
        "total_passes": _si(barca_cf["total_passes"].sum()) if "total_passes" in barca_cf.columns else None,
        "total_shots": _si(barca_cf["total_shots"].sum()) if "total_shots" in barca_cf.columns else None,
        "total_xg": _sf(barca_cf["total_xg"].sum()) if "total_xg" in barca_cf.columns else None,
        "pass_accuracy": _sf(barca_cf["pass_accuracy"].mean()) if "pass_accuracy" in barca_cf.columns else None,
        "total_pressures": _si(barca_cf["total_pressures"].sum()) if "total_pressures" in barca_cf.columns else None,
    }
    players = [
        {"player_name": str(r["player_name"]), "overall_score": _sf(r.get("overall_score"))}
        for _, r in barca_ms_latest.iterrows()
    ]

    squad_advice = guidance_engine.generate_squad_guidance({}, team_stats, players, {})

    return {
        "team": TEAM_NAME,
        "squad_insights": squad_advice,
        "validation_findings": validator.validate_all()["findings"],
    }


@router.get("/coaching/squad/{match_id}")
def get_squad_coaching(match_id: int, season: Optional[str] = Query(None)):
    """Tactical advice for a specific match / squad performance."""
    d = _load(season=season)
    sc = d["scores"]
    cf = d["computed"]

    squad_ids = _get_squad_players(d)
    match_scores = sc[sc["match_id"] == match_id]
    squad_ms = match_scores[match_scores["player_id"].isin(squad_ids)]
    if not len(squad_ms):
        raise HTTPException(404, f"No squad data for match {match_id}")

    squad_cf = cf[(cf["match_id"] == match_id) & (cf["player_id"].isin(squad_ids))]

    is_barca = squad_ms["team_name"].astype(str).str.contains(TEAM_NAME, case=False, na=False)
    barca_ms = squad_ms[is_barca]
    opp_ms = squad_ms[~is_barca]

    match_row = d["matches"][d["matches"]["match_id"] == match_id]
    gf = None
    ga = None
    if len(match_row):
        mr = match_row.iloc[0]
        is_home = TEAM_NAME in str(mr.get("home_team", ""))
        gf = _si(mr.get("home_score")) if is_home else _si(mr.get("away_score"))
        ga = _si(mr.get("away_score")) if is_home else _si(mr.get("home_score"))

    barca_cf = squad_cf[is_barca.values] if len(is_barca) == len(squad_cf) else squad_cf
    opp_cf = cf[(cf["match_id"] == match_id) & (cf["player_id"].isin(opp_ms["player_id"].unique()))]

    def _total_actions(df):
        cols = ["total_passes", "total_carries", "total_dribbles", "total_shots"]
        if all(c in df.columns for c in cols):
            return float(df[cols].sum().sum())
        return None

    barca_acts = _total_actions(barca_cf)
    opp_acts = _total_actions(opp_cf)
    possession = None
    if barca_acts is not None and opp_acts is not None and (barca_acts + opp_acts) > 0:
        possession = round((barca_acts / (barca_acts + opp_acts)) * 100, 1)

    match_context = {"match_id": match_id}
    team_stats = {
        "avg_overall_score": _sf(barca_ms["overall_score"].mean()),
        "total_passes": _si(barca_cf["total_passes"].sum()) if "total_passes" in barca_cf.columns else None,
        "total_shots": _si(barca_cf["total_shots"].sum()) if "total_shots" in barca_cf.columns else None,
        "total_xg": _sf(barca_cf["total_xg"].sum()) if "total_xg" in barca_cf.columns else None,
        "pass_accuracy": _sf(barca_cf["pass_accuracy"].mean()) if "pass_accuracy" in barca_cf.columns else None,
        "total_pressures": _si(barca_cf["total_pressures"].sum()) if "total_pressures" in barca_cf.columns else None,
        "possession_pct": possession,
        "goals_for": gf,
        "goals_against": ga,
    }
    players = [
        {"player_name": str(r["player_name"]), "overall_score": _sf(r.get("overall_score"))}
        for _, r in barca_ms.iterrows()
    ]

    squad_advice = guidance_engine.generate_squad_guidance(match_context, team_stats, players, {})

    return {
        "match_id": match_id,
        "team": TEAM_NAME,
        "squad_insights": squad_advice,
    }


@router.get("/coaching/player/{player_id}")
def get_player_coaching(player_id: int, season: Optional[str] = Query(None)):
    """Tactical advice for an individual player."""
    d = _load(season=season)
    sc = d["scores"]
    cf = d["computed"]

    ps = sc[sc["player_id"] == player_id]
    if not len(ps):
        raise HTTPException(404, f"Player {player_id} not found")

    pname = str(ps.iloc[0].get("player_name", "Unknown"))
    pgroup = str(ps.iloc[0].get("position_group", "Unknown"))
    pcluster = str(ps.iloc[0].get("player_cluster", "Unknown"))

    player_info = {
        "player_id": player_id,
        "player_name": pname,
        "position_group": pgroup,
        "player_cluster": pcluster,
        "performance_trend": str(ps.iloc[0].get("performance_trend", "Stable")),
        "season_avg": _sf(ps["overall_score"].mean()),
        "total_matches": len(ps),
    }

    latest_match = ps.sort_values("match_id").iloc[-1] if len(ps) else None
    match_scores = {}
    match_stats = {}
    if latest_match is not None:
        for dim in ["passing_score", "shooting_score", "positioning_score",
                     "pressing_score", "movement_score", "physical_score", "behavioral_score"]:
            match_scores[dim] = _sf(latest_match.get(dim))
        lid = int(latest_match["match_id"])
        cf_row = cf[(cf["player_id"] == player_id) & (cf["match_id"] == lid)]
        if len(cf_row):
            cr = cf_row.iloc[0]
            for k in ["total_passes", "pass_accuracy", "progressive_passes",
                       "total_shots", "total_xg", "goals", "distance_covered",
                       "total_pressures", "dribble_success_rate"]:
                if k in cr:
                    match_stats[k] = _sf(cr[k]) if "rate" in k or "xg" in k or "distance" in k or "accuracy" in k else _si(cr[k])

    season_stats = {
        "season_avg": _sf(ps["overall_score"].mean()),
        "total_matches": len(ps),
    }

    trend_data = ps.sort_values("match_id")["overall_score"].tolist()

    player_advice = guidance_engine.generate_player_guidance(
        player_info, match_scores, match_stats, [], season_stats, trend_data
    )

    return {
        "player_id": player_id,
        "player_name": pname,
        "player_insights": player_advice,
    }


@router.get("/coaching/player/{player_id}/comprehensive")
def get_comprehensive_coaching(player_id: int, season: Optional[str] = Query(None)):
    """All-in-one coaching guidance: player + momentum + consistency + injury + forecast."""
    d = _load(season=season)
    sc = d["scores"]
    cf = d["computed"]
    ev = d["events"]

    ps = sc[sc["player_id"] == player_id]
    if not len(ps):
        raise HTTPException(404, f"Player {player_id} not found")

    pname = str(ps.iloc[0].get("player_name", "Unknown"))
    pgroup = str(ps.iloc[0].get("position_group", "Unknown"))

    if "match_date" in ps.columns:
        ps_sorted = ps.sort_values("match_date")
    else:
        md = d["matches"][["match_id", "match_date"]].copy()
        md["match_date"] = pd.to_datetime(md["match_date"], errors="coerce")
        ps_sorted = ps.merge(md, on="match_id", how="left")
    merged_scores = d["scores"].copy()
    if "match_date" not in merged_scores.columns:
        md2 = d["matches"][["match_id", "match_date"]].copy()
        md2["match_date"] = pd.to_datetime(md2["match_date"], errors="coerce")
        merged_scores = merged_scores.merge(md2, on="match_id", how="left")

    player_scores = merged_scores[merged_scores["player_id"] == player_id]

    forecast = PerformanceForecaster().forecast(player_scores)
    consistency = ConsistencyAnalyzer().analyze(player_scores)
    momentum = MomentumAnalyzer().analyze(player_scores)
    injury = InjuryRiskEstimator().estimate(player_id, merged_scores, cf, ev)
    anomaly = AnomalyDetector().detect(player_scores, cf)

    guidance = guidance_engine.generate_all_guidance(
        context="player_comprehensive",
        player={
            "player_info": {
                "player_id": player_id, "player_name": pname, "position_group": pgroup,
                "performance_trend": str(ps.iloc[0].get("performance_trend", "Stable")),
                "trend_value": 0,
            },
            "match_scores": {},
            "match_stats": {},
            "percentiles": [],
            "season_stats": {},
            "trend_data": [],
        },
        momentum=momentum if "error" not in momentum else None,
        consistency=consistency if "error" not in consistency else None,
        injury=injury if "error" not in injury else None,
        anomaly=anomaly if "error" not in anomaly else None,
        forecast=forecast if "error" not in forecast else None,
        player_name=pname,
    )

    return {
        "player_id": player_id,
        "player_name": pname,
        "position": pgroup,
        "guidance": guidance,
        "modules": {
            "forecast": forecast if "error" not in forecast else None,
            "consistency": consistency if "error" not in consistency else None,
            "momentum": momentum if "error" not in momentum else None,
            "injury_risk": injury if "error" not in injury else None,
            "anomalies": anomaly if "error" not in anomaly else None,
        },
    }


@router.get("/predict/player/{player_id}")
def get_player_prediction(player_id: int, season: Optional[str] = Query(None)):
    """Predict a player's technical and physical performance for the next match."""
    d = _load(season=season)
    result = predictor.predict_player_next_match(d["scores"], d["computed"], d["events"], player_id)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.get("/predict/squad")
def get_squad_prediction(season: Optional[str] = Query(None)):
    """Predict the entire squad's performance for the next match."""
    d = _load(season=season)
    squad_ids = _get_squad_players(d)
    result = predictor.predict_squad_next_match(d["scores"], d["computed"], d["events"], squad_ids)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.get("/validate/metrics")
def get_validation_report():
    """Full formula audit and data validation report."""
    report = validator.validate_all()
    return report


@router.get("/validate/formulas")
def get_formula_details():
    """Detailed breakdown of every formula used in the system."""
    return {
        "passing_score": {
            "formula": "normalize(acc)*0.40 + normalize(prog_passes)*0.35 + normalize(total_passes)*0.25",
            "inputs": ["pass_accuracy", "progressive_passes", "total_passes"],
            "range": "0-10",
            "notes": ["No min-pass threshold for accuracy", "Volume+Efficiency double-counting"],
        },
        "shooting_score": {
            "formula": "normalize(predicted_xg)*0.40 + normalize(shot_accuracy)*0.35 + normalize(total_shots)*0.25",
            "inputs": ["predicted_xg (LightGBM)", "shot_accuracy", "total_shots"],
            "range": "0-10",
            "notes": ["Custom xG model used, not native StatsBomb xG", "Penalties not separated"],
        },
        "positioning_score": {
            "formula": "normalize(attacking_tendency)*0.50 + (10 - normalize(position_deviation))*0.50",
            "inputs": ["attacking_tendency (avg_x/120*100)", "position_deviation (sqrt(std_x^2 + std_y^2))"],
            "range": "0-10",
            "notes": ["Attacking tendency has severe position bias", "Deviation inverted — penalizes box-to-box players"],
        },
        "pressing_score": {
            "formula": "normalize(total_pressures)*0.50 + normalize(pressure_regains)*0.30 + normalize(pressing_efficiency)*0.20",
            "inputs": ["total_pressures", "pressure_regains", "pressing_efficiency"],
            "range": "0-10",
            "notes": ["FIXED: pressure_regains now counts only Pressure+Counterpress events"],
        },
        "movement_score": {
            "formula": "normalize(total_carries)*0.35 + normalize(progressive_carries)*0.35 + normalize(dribble_success_rate)*0.30",
            "inputs": ["total_carries", "progressive_carries", "dribble_success_rate"],
            "range": "0-10",
            "notes": ["FIXED: Non-dribblers get 50% baseline instead of 0%"],
        },
        "physical_score": {
            "formula": "normalize(total_actions)*0.35 + normalize(distance_covered)*0.35 + (10 - normalize(drop))*0.30",
            "inputs": ["total_actions", "distance_covered", "activity_drop_2nd_half"],
            "range": "0-10",
            "notes": ["FIXED: distance_covered added (was unused)", "FIXED: *5.0 multiplier removed", "FIXED: abs() removed from drop"],
        },
        "behavioral_score": {
            "formula": "5.0 - normalize(fouls)*0.30 + normalize(fouls_won)*0.10 - normalize(yellow)*0.25 - normalize(red)*0.50 + normalize(retention)*0.25",
            "inputs": ["fouls_committed", "fouls_won", "yellow_cards", "red_cards", "ball_retention_rate"],
            "range": "0-10",
            "notes": ["FIXED: Baseline 8→5.0", "FIXED: Cards now normalized", "FIXED: fouls_won now included"],
        },
        "overall_score": {
            "formula": "position_weighted_sum of 7 dimension scores",
            "inputs": ["7 dim scores + position_group"],
            "range": "0-10",
            "notes": ["Weights differ by position group", "Normalization is dataset-relative"],
        },
        "position_fit_score": {
            "formula": "(overall_score / position_group_mean) * 5",
            "range": "0-10",
            "notes": ["How player performs relative to position average", "Clipped to 0-10"],
        },
        "performance_trend": {
            "formula": "linregress(overall_score ~ match_sequence)",
            "range": "Improving | Stable | Declining",
            "notes": ["p<0.10 and |slope|>0.01 required for significance", "Minimum 4 matches"],
        },
        "player_cluster": {
            "formula": "GMM(5 components) on position-normalized z-scores of 7 dim averages",
            "labels": ["Creative Playmaker", "Box-to-Box Midfielder", "Target Forward", "Ball-Playing Defender", "Pressing Machine"],
            "notes": ["GMM replaced KMeans for soft clustering", "Position-normalized before clustering"],
        },
    }
