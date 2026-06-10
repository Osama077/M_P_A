"""api/routes/squad.py — Squad Overview batch endpoint"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from api.routes._shared import _load, _sf, _si

router = APIRouter()

TEAM_NAME = "Barcelona"

CLUSTER_SHORT = {
    "Creative Playmaker":    "creator",
    "Box-to-Box Midfielder": "engine",
    "Target Forward":        "dribbler",
    "Ball-Playing Defender": "stopper",
    "Pressing Machine":      "presser",
}

POS_LABEL_MAP = {"GK": "GK", "Defender": "DF", "Midfielder": "MF", "Attacker": "FW"}


@router.get("/player/squad-scores")
def get_squad_scores(match_id: Optional[int] = Query(None), season: Optional[str] = Query(None)):
    d = _load(season=season)
    sc = d["scores"]
    cf = d["computed"]
    mt = d["matches"]

    # Determine match context
    squad_ids = sc.loc[
        sc["team_name"].astype(str).str.contains(TEAM_NAME, case=False, na=False),
        "player_id"
    ].unique()
    squad_match_ids = sc["match_id"][sc["player_id"].isin(squad_ids)].unique()

    if match_id is None:
        match_candidates = sorted(set(squad_match_ids) & set(mt["match_id"].unique()))
        if match_candidates:
            max_week = int(mt.loc[mt["match_id"].isin(match_candidates), "match_week"].max())
            best = mt[(mt["match_id"].isin(match_candidates)) & (mt["match_week"] == max_week)]
            match_id = int(best["match_id"].iloc[0]) if len(best) else int(match_candidates[-1])
        else:
            match_id = int(sc["match_id"].max())

    # Verify match exists in scores
    match_scores = sc[sc["match_id"] == match_id]
    if not len(match_scores):
        raise HTTPException(404, f"Match {match_id} not found in score data")

    # Match context from matches table
    match_row = mt[mt["match_id"] == match_id]
    match_context = {}
    if len(match_row):
        r = match_row.iloc[0]
        match_context = {
            "match_id": int(match_id),
            "match_date": str(r.get("match_date", "")),
            "home_team": str(r.get("home_team", "")),
            "away_team": str(r.get("away_team", "")),
            "home_score": _si(r.get("home_score")),
            "away_score": _si(r.get("away_score")),
            "match_week": _si(r.get("match_week")),
        }

    # Squad players for this match
    squad_ms = match_scores[match_scores["player_id"].isin(squad_ids)]
    squad_ids_this = squad_ms["player_id"].unique()

    # Build per-player rows
    players = []
    for pid in squad_ids_this:
        row = squad_ms[squad_ms["player_id"] == pid]
        if not len(row):
            continue
        r = row.iloc[0]
        pname = str(r["player_name"])
        pgroup = str(r.get("position_group", "Unknown"))

        # Stats (computed features) for this match
        cf_row = cf[(cf["player_id"] == pid) & (cf["match_id"] == match_id)]
        cf_r = cf_row.iloc[0] if len(cf_row) else None

        # History for last-5 sparkline and trend value
        hist = sc[(sc["player_id"] == pid) & (sc["team_name"].astype(str).str.contains(TEAM_NAME, case=False, na=False))]
        hist_sorted = hist.sort_values("match_id")
        last5 = [round(float(x), 2) for x in hist_sorted["overall_score"].tail(5).tolist()]

        # Trend value: compare last score to average of previous 3
        trend_scores = hist_sorted["overall_score"].tolist()
        trend_val = 0.0
        if len(trend_scores) >= 2:
            last_val = trend_scores[-1]
            prev_avg = sum(trend_scores[:-1]) / len(trend_scores[:-1])
            trend_val = round(last_val - prev_avg, 2)

        players.append({
            "player_id": _si(pid),
            "player_name": pname,
            "team_name": str(r.get("team_name", "")),
            "position_group": pgroup,
            "position_label": POS_LABEL_MAP.get(pgroup, pgroup[:2].upper()) if pgroup != "Unknown" else "—",
            "overall_score": _sf(r.get("overall_score")),
            "scores": {
                "passing": _sf(r.get("passing_score")),
                "shooting": _sf(r.get("shooting_score")),
                "positioning": _sf(r.get("positioning_score")),
                "pressing": _sf(r.get("pressing_score")),
                "movement": _sf(r.get("movement_score")),
            },
            "vaep_rating": _sf(r.get("vaep_rating")),
            "total_xg": _sf(cf_r.get("total_xg")) if cf_r is not None else None,
            "pass_accuracy": _sf(cf_r.get("pass_accuracy")) if cf_r is not None else None,
            "dribble_success_rate": _sf(cf_r.get("dribble_success_rate")) if cf_r is not None else None,
            "position_fit_score": _sf(r.get("position_fit_score")),
            "player_cluster": CLUSTER_SHORT.get(str(r.get("player_cluster", "")), "Unknown"),
            "performance_trend": str(r.get("performance_trend", "Stable")),
            "trend_value": trend_val,
            "last_5_scores": last5,
        })

    players.sort(key=lambda p: p["overall_score"] or 0, reverse=True)

    # Team stats
    squad_cf = cf[(cf["match_id"] == match_id) & (cf["player_id"].isin(squad_ids_this))]
    team_stats = {
        "avg_overall_score": _sf(squad_ms["overall_score"].mean()),
        "total_passes": _si(squad_cf["total_passes"].sum()) if "total_passes" in squad_cf.columns else None,
        "total_shots": _si(squad_cf["total_shots"].sum()) if "total_shots" in squad_cf.columns else None,
        "shots_on_target": _si(squad_cf["shots_on_target"].sum()) if "shots_on_target" in squad_cf.columns else None,
        "total_xg": _sf(squad_cf["total_xg"].sum()) if "total_xg" in squad_cf.columns else None,
        "pass_accuracy": _sf(squad_cf["pass_accuracy"].mean()) if "pass_accuracy" in squad_cf.columns else None,
        "total_pressures": _si(squad_cf["total_pressures"].sum()) if "total_pressures" in squad_cf.columns else None,
        "pressure_regains": _si(squad_cf["pressure_regains"].sum()) if "pressure_regains" in squad_cf.columns else None,
        "total_dribbles": _si(squad_cf["total_dribbles"].sum()) if "total_dribbles" in squad_cf.columns else None,
        "dribble_success_pct": _sf(
            (squad_cf["successful_dribbles"].sum() / squad_cf["total_dribbles"].sum() * 100)
            if "successful_dribbles" in squad_cf.columns and squad_cf["total_dribbles"].sum() > 0
            else None
        ),
        "team_vaep": _sf(squad_ms["vaep_rating"].sum()) if "vaep_rating" in squad_ms.columns else None,
        "possession_pct": None,
    }

    # Possession estimate: total-action ratio (passes + carries + dribbles + shots)
    opp_ms = match_scores[~match_scores["player_id"].isin(squad_ids)]
    if len(opp_ms):
        opp_cf = cf[(cf["match_id"] == match_id) & (cf["player_id"].isin(opp_ms["player_id"].unique()))]
        def _total_actions(df):
            return float(df["total_passes"].sum() + df["total_carries"].sum() + df["total_dribbles"].sum() + df["total_shots"].sum()) if all(c in df.columns for c in ["total_passes","total_carries","total_dribbles","total_shots"]) else None
        squad_acts = _total_actions(squad_cf)
        opp_acts = _total_actions(opp_cf)
        total_a = (squad_acts or 0) + (opp_acts or 0)
        if squad_acts is not None and opp_acts is not None and total_a > 0:
            team_stats["possession_pct"] = round((squad_acts / total_a) * 100, 1)

    # Insights
    top = max(players, key=lambda p: p["overall_score"] or 0) if players else None
    insights = {"top_performer": None, "most_improved": None, "declining": None, "below_baseline_count": 0}

    if top:
        insights["top_performer"] = {
            "player_name": top["player_name"],
            "score": top["overall_score"],
        }

    # Most improved: highest trend_value
    improved = max(players, key=lambda p: p["trend_value"]) if players else None
    if improved and improved["trend_value"] > 0:
        insights["most_improved"] = {
            "player_name": improved["player_name"],
            "delta": improved["trend_value"],
        }

    # Declining: lowest trend_value
    declining = min(players, key=lambda p: p["trend_value"]) if players else None
    if declining and declining["trend_value"] < 0:
        insights["declining"] = {
            "player_name": declining["player_name"],
            "delta": declining["trend_value"],
        }

    # Below baseline: performance_trend == "Declining"
    insights["below_baseline_count"] = sum(
        1 for p in players if p["performance_trend"] == "Declining"
    )

    # Available matches for selector (most recent first by season week)
    avail = mt[mt["match_id"].isin(squad_match_ids)].sort_values("match_week", ascending=False)
    available_matches = [
        {
            "match_id": _si(r["match_id"]),
            "match_date": str(r.get("match_date", "")),
            "home_team": str(r.get("home_team", "")),
            "away_team": str(r.get("away_team", "")),
            "home_score": _si(r.get("home_score")),
            "away_score": _si(r.get("away_score")),
            "match_week": _si(r.get("match_week")),
        }
        for _, r in avail.iterrows()
    ]

    # Season stats
    squad_history = sc[sc["player_id"].isin(squad_ids)]
    season_stats = {}
    if len(squad_history):
        match_avgs = squad_history.groupby("match_id")["overall_score"].mean()
        if len(match_avgs):
            weekly = [round(float(v), 2) for v in match_avgs.sort_index().tolist()]
            season_stats["season_avg"] = _sf(squad_history["overall_score"].mean())
            season_stats["best_match_avg"] = _sf(match_avgs.max())
            season_stats["worst_match_avg"] = _sf(match_avgs.min())
            season_stats["weekly_averages"] = weekly

            # Score distribution: % of player-match scores in each bucket
            all_scores = squad_history["overall_score"].dropna()
            total = len(all_scores)
            if total > 0:
                dist = {}
                for lo, hi, label in [(3, 5, "3-5"), (5, 6, "5-6"), (6, 7, "6-7"),
                                       (7, 8, "7-8"), (8, 9, "8-9"), (9, 11, "9+")]:
                    cnt = ((all_scores >= lo) & (all_scores < hi)).sum()
                    dist[label] = round(cnt / total * 100, 1)
                season_stats["score_distribution"] = dist

    return {
        "match_context": match_context,
        "team_stats": team_stats,
        "players": players,
        "insights": insights,
        "season_stats": season_stats,
        "available_matches": available_matches,
    }
