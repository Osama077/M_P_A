"""api/routes/player_profile.py — Comprehensive Player Profile endpoint"""
import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import numpy as np
import pandas as pd
from api.routes._shared import _load, _sf, _si

logger = logging.getLogger(__name__)

try:
    from visualizations.player_dashboard import heatmap_chart, pass_map_chart, shooting_map_chart, get_player_data
    HAS_VIZ = True
except ImportError as e:
    logger.warning("visualizations.player_dashboard not available: %s", e)
    HAS_VIZ = False

router = APIRouter()

CLUSTER_SHORT = {
    "Creative Playmaker": "creator",
    "Box-to-Box Midfielder": "engine",
    "Target Forward": "dribbler",
    "Ball-Playing Defender": "stopper",
    "Pressing Machine": "presser",
}

POS_GROUP_LABEL = {"GK": "GK", "Defender": "DF", "Midfielder": "MF", "Attacker": "FW"}

SHOT_OUTCOME_MAP = {
    "Goal": "goal", "Saved": "saved", "Blocked": "blocked",
    "Off T": "missed", "Post": "post", "Saved to Post": "saved",
    "Saved Off Target": "saved", "Wayward": "missed",
}


def _pct_rank(val, series):
    if len(series) == 0:
        return 50
    raw = (series < val).sum() / len(series) * 100
    # Bayesian shrinkage: pull low-sample players toward positional mean
    n = len(series)
    prior = 50.0
    k = 5.0
    shrunk = (n / (n + k)) * raw + (k / (n + k)) * prior
    return int(round(shrunk))


def _initials(name):
    parts = name.split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper()


def _player_color(pid):
    colors = ["#1a6be0", "#22c55e", "#f59e0b", "#7c3aed", "#e05c1a",
              "#06b6d4", "#84cc16", "#f43f5e", "#1d4ed8", "#dc2626",
              "#0891b2", "#059669", "#b45309", "#6d28d9"]
    return colors[pid % len(colors)]


@router.get("/player/profile/{player_name}")
def get_player_profile(player_name: str, match_id: Optional[int] = Query(None), season: Optional[str] = Query(None)):
    d = _load(season=season)
    sc = d["scores"]
    cf = d["computed"]
    mt = d["matches"]
    ev = d["events"]
    vaep = d["vaep"]

    # Find player (fuzzy token matching)
    tokens = player_name.strip().lower().split()
    def _match(val):
        if pd.isna(val): return False
        return all(tok in str(val).lower() for tok in tokens)
    player_rows = sc[sc["player_name"].apply(_match)]
    if not len(player_rows):
        raise HTTPException(404, f"Player '{player_name}' not found")
    pid = int(player_rows["player_id"].iloc[0])
    pname = str(player_rows["player_name"].iloc[0])
    pgroup = str(player_rows["position_group"].iloc[0])

    # All matches this player played for Barcelona
    player_sc = sc[(sc["player_id"] == pid)]
    player_match_ids = sorted(player_sc["match_id"].unique().tolist())

    # Determine match context
    squad_match_ids = sc.loc[
        sc["team_name"].astype(str).str.contains("Barcelona", case=False, na=False),
        "match_id"
    ].unique()
    barca_player_match_ids = sorted(set(player_match_ids) & set(squad_match_ids))

    if match_id is None or int(match_id) not in barca_player_match_ids:
        # Default to the player's latest match by week
        pm = mt[mt["match_id"].isin(barca_player_match_ids)]
        if not len(pm):
            # Fallback to player's latest match
            match_id = barca_player_match_ids[-1] if barca_player_match_ids else player_match_ids[-1]
        else:
            max_week = int(pm["match_week"].max())
            best = pm[pm["match_week"] == max_week]
            match_id = int(best["match_id"].iloc[0]) if len(best) else int(barca_player_match_ids[-1])
    else:
        match_id = int(match_id)

    # Match context
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

    # Player info
    p_row = player_sc[player_sc["match_id"] == match_id]
    has_match_data = len(p_row) > 0
    if not has_match_data:
        p_row = player_sc.iloc[[-1]]

    r = p_row.iloc[0]
    cluster_raw = str(r.get("player_cluster", "Unknown"))
    cluster_short = CLUSTER_SHORT.get(cluster_raw, cluster_raw.lower().replace(" ", "-"))

    # Season averages
    season_avg_overall = _sf(player_sc["overall_score"].mean())
    season_best = _sf(player_sc["overall_score"].max())
    season_worst = _sf(player_sc["overall_score"].min())
    matches_above_7 = int((player_sc["overall_score"] >= 7).sum())
    total_matches = len(player_sc)
    match_score = _sf(r.get("overall_score")) if has_match_data else None
    delta_vs_avg = round((match_score or season_avg_overall or 0) - (season_avg_overall or 0), 2)

    player_info = {
        "player_id": pid,
        "player_name": pname,
        "initials": _initials(pname),
        "position_group": pgroup,
        "position_label": POS_GROUP_LABEL.get(pgroup, pgroup[:2].upper()),
        "player_cluster": cluster_short,
        "performance_trend": str(r.get("performance_trend", "Stable")),
        "season_avg": season_avg_overall,
        "total_matches": total_matches,
        "match_score": match_score,
        "trend_value": delta_vs_avg,
    }

    # Match scores (7 dims)
    s = p_row.iloc[0]
    match_scores = {}
    dim_keys = ["passing_score", "shooting_score", "positioning_score",
                "pressing_score", "movement_score", "physical_score", "behavioral_score"]
    dim_labels = ["passing", "shooting", "positioning", "pressing", "movement", "physical", "behavioral"]
    match_scores_dict = {}
    for dl, dk in zip(dim_labels, dim_keys):
        match_scores_dict[dl] = _sf(s.get(dk))

    # Squad mates for player selector
    squad_ms = sc[(sc["match_id"] == match_id) & (sc["team_name"].astype(str).str.contains("Barcelona", case=False, na=False))]
    squad_mates = []
    for _, sr in squad_ms.iterrows():
        spid = int(sr["player_id"])
        squad_mates.append({
            "player_id": spid,
            "player_name": str(sr["player_name"]),
            "initials": _initials(str(sr["player_name"])),
            "overall_score": _sf(sr.get("overall_score")),
            "color": _player_color(spid),
            "position_group": str(sr.get("position_group", "")),
            "is_current": spid == pid,
        })
    squad_mates.sort(key=lambda x: x["overall_score"] or 0, reverse=True)

    # Match stats from computed features
    cf_row = cf[(cf["player_id"] == pid) & (cf["match_id"] == match_id)]
    has_cf = len(cf_row) > 0
    cf_r = cf_row.iloc[0] if has_cf else None

    match_stats = {}
    if cf_r is not None:
        match_stats = {
            "total_passes": _si(cf_r.get("total_passes")),
            "complete_passes": _si(cf_r.get("complete_passes")),
            "pass_accuracy": _sf(cf_r.get("pass_accuracy")),
            "progressive_passes": _si(cf_r.get("progressive_passes")),
            "passes_under_pressure": _si(cf_r.get("passes_under_pressure")),
            "total_shots": _si(cf_r.get("total_shots")),
            "shots_on_target": _si(cf_r.get("shots_on_target")),
            "goals": _si(cf_r.get("goals")),
            "total_xg": _sf(cf_r.get("total_xg")),
            "xg_per_shot": _sf(cf_r.get("xg_per_shot")),
            "dribble_success_rate": _sf(cf_r.get("dribble_success_rate")),
            "total_dribbles": _si(cf_r.get("total_dribbles")),
            "successful_dribbles": _si(cf_r.get("successful_dribbles")),
            "total_pressures": _si(cf_r.get("total_pressures")),
            "pressure_regains": _si(cf_r.get("pressure_regains")),
            "distance_covered": _sf(cf_r.get("distance_covered")),
            "fouls_won": _si(cf_r.get("fouls_won")),
            "fouls_committed": _si(cf_r.get("fouls_committed")),
            "ball_receipts": _si(cf_r.get("ball_receipts")),
        }

    # Percentiles vs position (use season averages for all players in same position)
    pos_players = sc[sc["position_group"] == pgroup]
    pos_avgs = pos_players.groupby("player_id").agg(
        overall_score=("overall_score", "mean"),
        passing_score=("passing_score", "mean"),
        shooting_score=("shooting_score", "mean"),
        positioning_score=("positioning_score", "mean"),
        pressing_score=("pressing_score", "mean"),
        movement_score=("movement_score", "mean"),
        vaep_rating=("vaep_rating", "mean"),
        position_fit_score=("position_fit_score", "mean"),
    ).reset_index()

    # Compute percentiles for the player's season avg
    p_avg = player_sc.mean(numeric_only=True)
    p_passing = _sf(p_avg.get("passing_score"))
    p_shooting = _sf(p_avg.get("shooting_score"))
    p_positioning = _sf(p_avg.get("positioning_score"))
    p_pressing = _sf(p_avg.get("pressing_score"))
    p_movement = _sf(p_avg.get("movement_score"))
    p_vaep = _sf(p_avg.get("vaep_rating"))
    p_fit = _sf(p_avg.get("position_fit_score"))

    # Compute percentile values from computed features
    all_cf = cf[cf["player_id"].isin(pos_avgs["player_id"].unique())]
    player_cf_avg = cf[cf["player_id"] == pid].mean(numeric_only=True)

    percentile_items = []
    pct_config = [
        ("xG per Shot", "xg_per_shot", "grn", lambda: _sf(player_cf_avg.get("xg_per_shot", 0))),
        ("Pass Accuracy", "pass_accuracy", "blu", lambda: _sf(player_cf_avg.get("pass_accuracy", 0))),
        ("Prog. Passes", "progressive_passes", "blu", lambda: _si(player_cf_avg.get("progressive_passes", 0))),
        ("Dribble Success%", "dribble_success_rate", "pur", lambda: _sf(player_cf_avg.get("dribble_success_rate", 0))),
        ("VAEP Rating", "vaep_rating", "grn", lambda: _sf(p_vaep)),
        ("Pressures/Gm", "total_pressures", "red", lambda: _si(player_cf_avg.get("total_pressures", 0))),
        ("Distance/Gm", "distance_covered", "yel", lambda: _sf(player_cf_avg.get("distance_covered", 0))),
        ("Position Fit", "position_fit_score", "grn", lambda: _sf(p_fit)),
    ]

    for label, col, color_cls, val_fn in pct_config:
        val = val_fn()
        if col in pos_avgs.columns:
            pct = _pct_rank(p_avg.get(col, 0) if col in dim_labels or col in pos_avgs.columns else 0, pos_avgs[col])
        elif col in all_cf.columns:
            pos_cf_avgs = all_cf.groupby("player_id")[col].mean()
            pct = _pct_rank(player_cf_avg.get(col, 0), pos_cf_avgs)
        else:
            pct = 50
        percentile_items.append({
            "label": label,
            "value": val,
            "percentile": pct,
            "color": color_cls,
        })

    # Radar data (season avg values vs this match)
    season_avg_dims = [float(player_sc[dk].mean()) if dk in player_sc.columns else 0.0 for dk in dim_keys]
    match_dims = [float(s.get(dk, 0) or 0) for dk in dim_keys]
    radar_data = {
        "labels": [dl.capitalize() for dl in dim_labels],
        "season_values": [round(v, 2) for v in season_avg_dims],
        "match_values": [round(v, 2) for v in match_dims],
    }

    # Trend data
    trend_sc = player_sc.sort_values("match_id")
    player_matches = mt[mt["match_id"].isin(trend_sc["match_id"].unique())][["match_id", "match_week", "match_date"]]
    trend_data = []
    for _, tr in trend_sc.iterrows():
        mid = int(tr["match_id"])
        mrow = player_matches[player_matches["match_id"] == mid]
        week = int(mrow["match_week"].iloc[0]) if len(mrow) else None
        date = str(mrow["match_date"].iloc[0]) if len(mrow) else ""
        trend_data.append({
            "match_id": mid,
            "week": week,
            "date": date,
            "overall_score": _sf(tr.get("overall_score")),
            "passing_score": _sf(tr.get("passing_score")),
            "shooting_score": _sf(tr.get("shooting_score")),
            "positioning_score": _sf(tr.get("positioning_score")),
            "pressing_score": _sf(tr.get("pressing_score")),
            "movement_score": _sf(tr.get("movement_score")),
            "physical_score": _sf(tr.get("physical_score")),
            "behavioral_score": _sf(tr.get("behavioral_score")),
            "position_fit_score": _sf(tr.get("position_fit_score")),
            "is_current": mid == match_id,
        })

    # Rolling avg
    scores_list = [t["overall_score"] for t in trend_data]
    for i, t in enumerate(trend_data):
        window = scores_list[max(0, i - 2):i + 1]
        t["rolling_avg"] = round(sum(window) / len(window), 2) if window else None

    # Season stats
    season_stats = {
        "season_avg": season_avg_overall,
        "best_match": season_best,
        "worst_match": season_worst,
        "matches_above_7": matches_above_7,
        "total_matches": total_matches,
        "delta_vs_avg": delta_vs_avg,
        "current_score": match_score,
    }

    # Match log
    match_log = []
    for _, tr in trend_sc.iterrows():
        mid = int(tr["match_id"])
        mrow = mt[mt["match_id"] == mid]
        if not len(mrow):
            continue
        mr = mrow.iloc[0]
        is_barca_home = str(mr.get("home_team", "")).lower().__contains__("barcelona")
        opponent = str(mr.get("away_team", "")) if is_barca_home else str(mr.get("home_team", ""))
        h_score = int(mr.get("home_score", 0))
        a_score = int(mr.get("away_score", 0))
        if is_barca_home:
            result = f"W {h_score}-{a_score}" if h_score > a_score else f"D {h_score}-{a_score}" if h_score == a_score else f"L {h_score}-{a_score}"
        else:
            result = f"W {a_score}-{h_score}" if a_score > h_score else f"D {h_score}-{a_score}" if h_score == a_score else f"L {a_score}-{h_score}"

        cf_r2 = cf[(cf["player_id"] == pid) & (cf["match_id"] == mid)]
        cf_r2 = cf_r2.iloc[0] if len(cf_r2) else None
        trend_label = str(tr.get("performance_trend", "Stable")).lower()[:2]

        log_entry = {
            "match_id": mid,
            "week": _si(mr.get("match_week")),
            "opponent": opponent,
            "date": str(mr.get("match_date", "")),
            "result": result,
            "ml_score": _sf(tr.get("overall_score")),
            "delta_vs_avg": round(float(tr.get("overall_score", 0) or 0) - (season_avg_overall or 0), 2),
            "trend": trend_label,
            "is_current": mid == match_id,
        }
        if cf_r2 is not None:
            log_entry.update({
                "total_passes": _si(cf_r2.get("total_passes")),
                "pass_accuracy": _sf(cf_r2.get("pass_accuracy")),
                "total_shots": _si(cf_r2.get("total_shots")),
                "total_xg": _sf(cf_r2.get("total_xg")),
                "dribble_success_rate": _sf(cf_r2.get("dribble_success_rate")),
                "progressive_passes": _si(cf_r2.get("progressive_passes")),
                "vaep_rating": _sf(tr.get("vaep_rating")),
                "distance_covered": _sf(cf_r2.get("distance_covered")),
                "total_pressures": _si(cf_r2.get("total_pressures")),
            })
        match_log.append(log_entry)

    # Timeline events for this match
    player_events = ev[(ev["match_id"] == match_id) & (ev["player_id"] == pid)]
    timeline_events = []
    for _, er in player_events.iterrows():
        minute = int(er.get("minute", 0))
        etype = str(er.get("event_type", ""))
        outcome = str(er.get("shot_outcome", ""))
        xg = float(er.get("shot_xg", 0) or 0) if not pd.isna(er.get("shot_xg")) else None
        do = str(er.get("dribble_outcome", ""))
        is_prog = bool(er.get("is_progressive_pass", False))
        is_prog_carry = bool(er.get("is_progressive_carry", False))
        under_press = bool(er.get("under_pressure", False))

        event_item = None
        if etype == "Shot":
            mapped = SHOT_OUTCOME_MAP.get(outcome, "missed")
            event_item = {"minute": minute, "type": "shot", "outcome": mapped, "xg": round(xg, 2) if xg else None}
        elif etype == "Dribble":
            event_item = {"minute": minute, "type": "dribble", "outcome": "complete" if do == "Complete" else "incomplete"}
        elif etype == "Carry" and is_prog_carry:
            event_item = {"minute": minute, "type": "progressive_carry"}
        elif etype == "Foul Won":
            event_item = {"minute": minute, "type": "foul_won"}
        elif etype == "Pass" and is_prog:
            event_item = {"minute": minute, "type": "key_pass"}
        elif etype == "Goal Keeper":
            continue
        elif etype in ("Half Start", "Half End", "Starting XI", "Player Off", "Player On", "Substitution", "Tactical Shift", "Injury Stoppage", "Referee Ball-Drop", "Bad Behaviour"):
            continue

        if event_item is None:
            continue

        # Deduplicate events at same minute
        if not any(e["minute"] == minute and e["type"] == event_item["type"] for e in timeline_events):
            timeline_events.append(event_item)

    timeline_events.sort(key=lambda e: e["minute"])

    # Available matches for selector
    avail = mt[mt["match_id"].isin(barca_player_match_ids)].sort_values("match_week", ascending=False)
    available_matches = [
        {
            "match_id": _si(r["match_id"]),
            "match_week": _si(r.get("match_week")),
            "label": f"W{_si(r.get('match_week'))} — {r.get('home_team','')} {_si(r.get('home_score'))}-{_si(r.get('away_score'))} {r.get('away_team','')}",
        }
        for _, r in avail.iterrows()
    ]

    # Spatial / Season-level chart images (base64)
    charts = {}
    if HAS_VIZ:
        try:
            viz_player_data = get_player_data(player_name)
            if viz_player_data is not None:
                charts["heatmap"] = heatmap_chart(viz_player_data, match_id)
                charts["pass_map"] = pass_map_chart(viz_player_data, match_id)
                charts["shot_map"] = shooting_map_chart(viz_player_data, match_id)
        except Exception as e:
            logger.warning("Failed to generate chart images: %s", e)

    return {
        "player_info": player_info,
        "match_context": match_context,
        "match_scores": match_scores_dict,
        "match_stats": match_stats,
        "percentiles": percentile_items,
        "season_stats": season_stats,
        "squad_mates": squad_mates,
        "radar_data": radar_data,
        "trend_data": trend_data,
        "charts": charts,
        "match_log": match_log,
        "timeline_events": timeline_events,
        "available_matches": available_matches,
    }
