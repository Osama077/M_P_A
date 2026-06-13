"""api/routes/squad.py — Squad Overview batch endpoint"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import pandas as pd
import os
from api.routes._shared import _load, _sf, _si, GRANULAR_LABELS, GRANULAR_POSITIONS

router = APIRouter()

TEAM_NAME = os.environ.get("TARGET_TEAM", "Barcelona")

CLUSTER_SHORT = {
    "Creative Playmaker":    "creator",
    "Box-to-Box Midfielder": "engine",
    "Target Forward":        "dribbler",
    "Ball-Playing Defender": "stopper",
    "Pressing Machine":      "presser",
}

POS_LABEL_MAP = {"GK": "GK", "Defender": "DF", "Midfielder": "MF", "Attacker": "FW"}

COARSE_TO_GRANULAR = {
    "GK": "Goalkeeper", "Defender": "Center Back",
    "Midfielder": "Central Midfielder", "Attacker": "Winger",
}


@router.get("/player/squad-scores")
def get_squad_scores(match_id: Optional[int] = Query(None), season: Optional[str] = Query(None)):
    d = _load(season=season)
    sc = d["scores"]
    cf = d["computed"]
    mt = d["matches"]
    pr = d.get("position_kpi", None)

    # Determine match context
    team_col = "team_name" if "team_name" in sc.columns else "team"
    squad_ids = sc.loc[
        sc[team_col].astype(str).str.contains(TEAM_NAME, case=False, na=False),
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

    # Position ratings for this match
    pr_match = pr[pr["match_id"] == match_id] if pr is not None and "match_id" in pr.columns else None

    # Build per-player rows
    players = []
    for pid in squad_ids_this:
        row = squad_ms[squad_ms["player_id"] == pid]
        if not len(row):
            continue
        r = row.iloc[0]
        pname = str(r["player_name"])
        pgroup = str(r.get("position_group", "Unknown"))
        pos_granular = str(r.get("position_granular", ""))
        if not pos_granular or pos_granular == "Unknown":
            pos_granular = COARSE_TO_GRANULAR.get(pgroup, "Central Midfielder")
        pos_short = GRANULAR_LABELS.get(pos_granular, pgroup[:2].upper())

        # Stats (computed features) for this match
        cf_row = cf[(cf["player_id"] == pid) & (cf["match_id"] == match_id)]
        cf_r = cf_row.iloc[0] if len(cf_row) else None

        # Position rating for this match
        pr_row = pr_match[pr_match["player_id"] == pid] if pr_match is not None else None
        pr_r = pr_row.iloc[0] if pr_row is not None and len(pr_row) else None

        # History for last-5 sparkline and trend value
        hist = sc[(sc["player_id"] == pid) & (sc[team_col].astype(str).str.contains(TEAM_NAME, case=False, na=False))]
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
            "position_granular": pos_granular,
            "position_short": pos_short,
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
            "position_kpi": _sf(pr_r.get("position_kpi")) if pr_r is not None else None,
            "position_kpi_label": str(pr_r.get("position_kpi_label", "")) if pr_r is not None else "",
            "position_fit_score": _sf(r.get("position_fit_score")),
            "player_cluster": CLUSTER_SHORT.get(str(r.get("player_cluster", "")), "Unknown"),
            "performance_trend": str(r.get("performance_trend", "Stable")),
            "trend_value": trend_val,
            "last_5_scores": last5,
        })

    if not players:
        raise HTTPException(404, f"No {TEAM_NAME} players found for match {match_id}")

    players.sort(key=lambda p: p["overall_score"] or 0, reverse=True)

    # Team stats
    squad_cf = cf[(cf["match_id"] == match_id) & (cf["player_id"].isin(squad_ids_this))]
    team_stats = {
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

    # Below baseline: recent trend is significantly negative
    insights["below_baseline_count"] = sum(
        1 for p in players if p.get("trend_value", 0) < -0.1
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


@router.get("/player/season-players")
def get_season_players(season: str = Query(..., description="Season label e.g. 2015/2016")):
    d = _load(season=season)
    sc = d["scores"]
    cf = d["computed"]
    kpi = d.get("position_kpi", None)

    # Filter Barcelona players for this season
    squad_ms = sc[sc["team_name"].astype(str).str.contains(TEAM_NAME, case=False, na=False)]
    squad_ms = squad_ms[squad_ms["season_label"] == season]

    if not len(squad_ms):
        raise HTTPException(404, f"No Barcelona players found for season {season}")

    # Build per-player season aggregates
    players = []
    for pid in squad_ms["player_id"].unique():
        p_rows = squad_ms[squad_ms["player_id"] == pid]
        r = p_rows.iloc[0]
        pname = str(r["player_name"])
        pgroup = str(r.get("position_group", "Unknown"))
        pos_granular = str(r.get("position_granular", ""))
        if not pos_granular or pos_granular == "Unknown":
            pos_granular = COARSE_TO_GRANULAR.get(pgroup, "Central Midfielder")
        match_ids = p_rows["match_id"].unique()

        # Season computed features
        cf_season = cf[(cf["player_id"] == pid) & (cf["match_id"].isin(match_ids))]

        # Season position_kpi
        kpi_season = kpi[(kpi["player_id"] == pid) & (kpi["match_id"].isin(match_ids))] if kpi is not None and "player_id" in kpi.columns else pd.DataFrame()

        players.append({
            "player_id": _si(pid),
            "player_name": pname,
            "position_group": pgroup,
            "position_granular": pos_granular,
            "position_short": GRANULAR_LABELS.get(pos_granular, pgroup[:2].upper()),
            "matches_played": _si(len(p_rows)),
            "avg_minutes": _sf(cf_season["minutes_played"].mean()) if len(cf_season) else None,
            "avg_overall_score": _sf(p_rows["overall_score"].mean()),
            "avg_vaep_rating": _sf(p_rows["vaep_rating"].mean()),
            "avg_position_kpi": _sf(kpi_season["position_kpi"].mean()) if len(kpi_season) else None,
            "avg_position_kpi_label": str(kpi_season["position_kpi_label"].mode().iloc[0]) if len(kpi_season) and "position_kpi_label" in kpi_season.columns else "",
            "total_goals": _si(cf_season["goals"].sum()) if len(cf_season) else 0,
            "total_assists": _si(cf_season["assists"].sum()) if len(cf_season) else 0,
            "total_shots": _si(cf_season["total_shots"].sum()) if len(cf_season) else 0,
            "total_key_passes": _si(cf_season["key_passes"].sum()) if len(cf_season) else 0,
            "total_passes": _si(cf_season["total_passes"].sum()) if len(cf_season) else 0,
            "avg_pass_accuracy": _sf(cf_season["pass_accuracy"].mean()) if len(cf_season) else None,
            "avg_dribble_success_rate": _sf(cf_season["dribble_success_rate"].mean()) if len(cf_season) else None,
            "avg_shot_accuracy": _sf(cf_season["shot_accuracy"].mean()) if len(cf_season) else None,
            "total_interceptions": _si(cf_season["interceptions"].sum()) if len(cf_season) else 0,
            "total_clearances": _si(cf_season["clearances"].sum()) if len(cf_season) else 0,
            "total_blocks": _si(cf_season["blocks"].sum()) if len(cf_season) else 0,
            "total_pressures": _si(cf_season["total_pressures"].sum()) if len(cf_season) else 0,
            "total_saves": _si(cf_season["saves"].sum()) if len(cf_season) else 0,
            "avg_save_pct": _sf(cf_season["save_pct"].mean()) if len(cf_season) else None,
            "total_minutes": _sf(cf_season["minutes_played"].sum()) if len(cf_season) else 0,
        })

    players.sort(key=lambda p: p["avg_overall_score"] or 0, reverse=True)

    return {
        "season": season,
        "team": TEAM_NAME,
        "player_count": len(players),
        "players": players,
    }


@router.get("/player/position-stats")
def get_position_stats(
    season: str = Query(..., description="Season label e.g. 2015/2016"),
    position: str = Query(..., description="Position: GK, Defender, Midfielder, Attacker, or 8-position name"),
):
    """Return season-aggregated stats + KPI dimensions for all players in a position."""
    d = _load(season=season)
    sc = d["scores"]
    cf = d["computed"]
    kpi = d.get("position_kpi", None)

    coarse_positions = {"GK", "Defender", "Midfielder", "Attacker"}
    all_valid = list(coarse_positions) + GRANULAR_POSITIONS
    if position not in all_valid:
        raise HTTPException(400, f"Invalid position '{position}'. Choose from: {all_valid}")

    team_col = "team_name" if "team_name" in sc.columns else "team"
    squad_ms = sc[sc[team_col].astype(str).str.contains(TEAM_NAME, case=False, na=False)]
    squad_ms = squad_ms[squad_ms["season_label"] == season]

    if position in coarse_positions:
        squad_ms = squad_ms[squad_ms["position_group"] == position]
        # Map coarse to default granular for KPI dimension lookup
        coarse_to_granular_key = {"GK": "Goalkeeper", "Defender": "Center Back",
                                   "Midfielder": "Central Midfielder", "Attacker": "Winger"}
        granular_key = coarse_to_granular_key.get(position, "Central Midfielder")
    else:
        # Granular position: filter by position_granular
        squad_ms = squad_ms[squad_ms["position_granular"] == position]
        granular_key = position

    if not len(squad_ms):
        raise HTTPException(404, f"No {TEAM_NAME} {position}s found for season {season}")

    # KPI dimension columns — keyed by both coarse and granular position names
    pos_kpi_cols = {
        "GK": ["kpi_save_pct", "kpi_goals_prevented", "kpi_goals_conceded_per90",
               "kpi_pass_accuracy", "kpi_progressive_passes_per90"],
        "Goalkeeper": ["kpi_save_pct", "kpi_goals_prevented", "kpi_goals_conceded_per90",
                       "kpi_pass_accuracy", "kpi_progressive_passes_per90"],
        "Defender": ["kpi_defensive_actions_per90", "kpi_pass_accuracy",
                     "kpi_pressure_regains_per90", "kpi_progressive_carries_per90",
                     "kpi_duels_total_per90", "kpi_progressive_passes_per90"],
        "Center Back": ["kpi_defensive_actions_per90", "kpi_pass_accuracy",
                        "kpi_pressure_regains_per90", "kpi_progressive_carries_per90",
                        "kpi_duels_total_per90", "kpi_progressive_passes_per90"],
        "Full Back": ["kpi_defensive_actions_per90", "kpi_pass_accuracy",
                      "kpi_pressure_regains_per90", "kpi_progressive_carries_per90",
                      "kpi_progressive_passes_per90", "kpi_successful_dribbles_per90"],
        "Midfielder": ["kpi_pass_accuracy", "kpi_pressure_regains_per90",
                       "kpi_progressive_passes_per90", "kpi_total_passes_per90",
                       "kpi_ball_receipts_per90", "kpi_chances_created_per90",
                       "kpi_progressive_carries_per90"],
        "Defensive Midfielder": ["kpi_pass_accuracy", "kpi_pressure_regains_per90",
                                 "kpi_defensive_actions_per90", "kpi_duels_total_per90",
                                 "kpi_progressive_passes_per90", "kpi_ball_receipts_per90"],
        "Central Midfielder": ["kpi_pass_accuracy", "kpi_pressure_regains_per90",
                               "kpi_progressive_passes_per90", "kpi_total_passes_per90",
                               "kpi_ball_receipts_per90", "kpi_chances_created_per90",
                               "kpi_progressive_carries_per90"],
        "Attacking Midfielder": ["kpi_chances_created_per90", "kpi_assists_per90",
                                 "kpi_goals_per90", "kpi_shot_accuracy",
                                 "kpi_successful_dribbles_per90", "kpi_progressive_carries_per90"],
        "Attacker": ["kpi_goals_per90", "kpi_xg_overperformance", "kpi_assists_per90",
                     "kpi_shot_accuracy", "kpi_successful_dribbles_per90",
                     "kpi_chances_created_per90", "kpi_progressive_carries_per90"],
        "Winger": ["kpi_goals_per90", "kpi_xg_overperformance", "kpi_assists_per90",
                   "kpi_shot_accuracy", "kpi_successful_dribbles_per90",
                   "kpi_chances_created_per90", "kpi_progressive_carries_per90"],
        "Striker": ["kpi_goals_per90", "kpi_xg_overperformance", "kpi_assists_per90",
                    "kpi_shot_accuracy", "kpi_successful_dribbles_per90",
                    "kpi_chances_created_per90"],
    }
    kpi_dims = pos_kpi_cols.get(granular_key, pos_kpi_cols.get("Central Midfielder", []))

    # Pre-filter DataFrames to avoid repeated full-table scans
    player_ids = squad_ms["player_id"].unique()
    cf_filtered = cf[cf["player_id"].isin(player_ids)]
    kpi_filtered = kpi[kpi["player_id"].isin(player_ids)] if kpi is not None and "player_id" in kpi.columns else pd.DataFrame()

    def _per90(val, mins):
        return round((val / (mins / 90)), 2) if mins > 0 else None

    players = []
    for pid in player_ids:
        p_rows = squad_ms[squad_ms["player_id"] == pid]
        r = p_rows.iloc[0]
        pname = str(r["player_name"])
        match_ids = p_rows["match_id"].unique()

        cf_season = cf_filtered[cf_filtered["player_id"] == pid]
        kpi_season = kpi_filtered[kpi_filtered["player_id"] == pid] if len(kpi_filtered) else pd.DataFrame()

        mins = float(cf_season["minutes_played"].sum()) if len(cf_season) else 0
        matches = len(p_rows)

        # KPI dimension averages
        kpi_dims_avg = {}
        if len(kpi_season):
            for col in kpi_dims:
                if col in kpi_season.columns:
                    vals = kpi_season[col].dropna()
                    kpi_dims_avg[col.replace("kpi_", "")] = _sf(vals.mean()) if len(vals) else None

        _p90 = lambda v: _per90(v, mins)

        players.append({
            "player_id": _si(pid),
            "player_name": pname,
            "position_granular": str(r.get("position_granular", "")),
            "matches_played": matches,
            "total_minutes": _sf(mins),
            "avg_minutes": _sf(mins / matches) if matches > 0 else None,
            "avg_position_kpi": _sf(kpi_season["position_kpi"].mean()) if len(kpi_season) else None,
            "avg_position_kpi_label": str(kpi_season["position_kpi_label"].mode().iloc[0]) if len(kpi_season) and "position_kpi_label" in kpi_season.columns else "",
            "kpi_dimensions": kpi_dims_avg,
            # Position-specific raw per-90 stats
            "goals_per90": _p90(float(cf_season["goals"].sum())) if len(cf_season) else None,
            "assists_per90": _p90(float(cf_season["assists"].sum())) if len(cf_season) else None,
            "shots_per90": _p90(float(cf_season["total_shots"].sum())) if len(cf_season) else None,
            "passes_per90": _p90(float(cf_season["total_passes"].sum())) if len(cf_season) else None,
            "pass_accuracy": _sf(cf_season["pass_accuracy"].mean()) if len(cf_season) else None,
            "progressive_passes_per90": _p90(float(cf_season["progressive_passes"].sum())) if len(cf_season) else None,
            "progressive_carries_per90": _p90(float(cf_season["progressive_carries"].sum())) if len(cf_season) else None,
            "dribbles_per90": _p90(float(cf_season["successful_dribbles"].sum())) if len(cf_season) else None,
            "pressure_regains_per90": _p90(float(cf_season["pressure_regains"].sum())) if len(cf_season) else None,
            "chances_created_per90": _p90(float(cf_season["chances_created"].sum())) if len(cf_season) else None,
            "ball_receipts_per90": _p90(float(cf_season["ball_receipts"].sum())) if len(cf_season) else None,
            "defensive_actions_per90": _p90(
                float(cf_season["interceptions"].sum() + cf_season["clearances"].sum() + cf_season["blocks"].sum())
            ) if len(cf_season) else None,
            "duels_per90": _p90(float(cf_season["duels_total"].sum())) if len(cf_season) else None,
            "saves_per90": _p90(float(cf_season["saves"].sum())) if len(cf_season) else None,
            "save_pct": _sf(cf_season["save_pct"].mean()) if len(cf_season) else None,
            "goals_conceded_per90": _p90(float(cf_season["goals_conceded"].sum())) if len(cf_season) else None,
            "shot_accuracy": _sf(cf_season["shot_accuracy"].mean()) if len(cf_season) else None,
            "xg_overperformance": _sf(cf_season["xg_overperformance"].mean()) if len(cf_season) else None,
        })

    players.sort(key=lambda p: p["avg_position_kpi"] or 0, reverse=True)

    return {
        "season": season,
        "team": TEAM_NAME,
        "position": position,
        "player_count": len(players),
        "kpi_dimensions": kpi_dims,
        "players": players,
    }
