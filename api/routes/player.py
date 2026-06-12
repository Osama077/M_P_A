"""api/routes/player.py"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from api.routes._shared import _load, _sf, _si, _to_records, _get_available_seasons, GRANULAR_LABELS
from visualizations.player_dashboard import generate_all_charts, get_player_list, get_player_chart_data

router = APIRouter()


@router.get("/player/list")
def list_players(season: Optional[str] = Query(None)):
    d = _load(season=season)
    scores_df = d["scores"]
    team_col = "team_name" if "team_name" in scores_df.columns else ("team" if "team" in scores_df.columns else None)
    base_cols = ["player_id", "player_name"] + ([team_col] if team_col else [])
    players_df = scores_df[base_cols].dropna(subset=["player_id", "player_name"]).drop_duplicates()
    if team_col:
        players_df = (
            players_df.sort_values("player_id")
            .groupby(["player_id", "player_name"], as_index=False)[team_col]
            .agg(lambda s: s.dropna().astype(str).mode().iat[0] if not s.dropna().empty else "Unknown")
        )
    players_df = players_df.sort_values("player_name")
    player_items = [
        {
            "player_id": _si(r["player_id"]),
            "player_name": str(r["player_name"]),
            "team_name": str(r.get(team_col, "Unknown")) if team_col else "Unknown",
        }
        for _, r in players_df.iterrows()
    ]
    teams = sorted({item["team_name"] for item in player_items if item.get("team_name")})
    return {
        "players": get_player_list(),
        "player_items": player_items,
        "teams": teams,
    }


@router.get("/player/{player_id}/score")
def get_score(player_id: int, match_id: Optional[int] = Query(None), season: Optional[str] = Query(None)):
    d  = _load(season=season)
    ps = d["scores"][d["scores"]["player_id"] == player_id]
    if not len(ps): raise HTTPException(404, f"Player {player_id} not found")

    if match_id:
        row = ps[ps["match_id"] == match_id]
        if not len(row): raise HTTPException(404, f"No data for match {match_id}")
        row = row.iloc[0]
    else:
        row = ps.merge(d["matches"][["match_id","match_date"]], on="match_id", how="left")\
                .sort_values("match_date").iloc[-1]

    pos_group = str(row.get("position_group", "Unknown"))
    pos_granular = str(row.get("position_granular", ""))
    if not pos_granular or pos_granular == "Unknown":
        coarse_map = {"GK": "Goalkeeper", "Defender": "Center Back",
                       "Midfielder": "Central Midfielder", "Attacker": "Winger"}
        pos_granular = coarse_map.get(pos_group, "Central Midfielder")

    return {
        "uuid":        str(row.get("uuid","")),
        "player_id":   _si(row["player_id"]),
        "player_name": str(row["player_name"]),
        "match_id":    _si(row["match_id"]),
        "position":    pos_group,
        "position_granular": pos_granular,
        "position_short": GRANULAR_LABELS.get(pos_granular, pos_group[:2].upper()),
        "position_kpi_label": str(row.get("position_kpi_label", "")),
        "confidence": str(row.get("confidence", "high")),
        "scores": {
            "overall_score":      _sf(row["overall_score"]),
            "passing_score":      _sf(row["passing_score"]),
            "shooting_score":     _sf(row["shooting_score"]),
            "positioning_score":  _sf(row["positioning_score"]),
            "pressing_score":     _sf(row["pressing_score"]),
            "movement_score":     _sf(row["movement_score"]),
            "physical_score":     _sf(row["physical_score"]),
            "behavioral_score":   _sf(row["behavioral_score"]),
            "position_fit_score": _sf(row.get("position_fit_score")),
        },
        "percentiles": {
            "in_team":     _sf(row.get("percentile_in_team")),
            "in_league":   _sf(row.get("percentile_in_league")),
            "in_position": _sf(row.get("percentile_in_position")),
        },
        "vaep": {
            "vaep_rating":     _sf(row.get("vaep_rating")),
            "offensive_value": _sf(row.get("offensive_value")),
            "defensive_value": _sf(row.get("defensive_value")),
        },
        "performance_trend": str(row.get("performance_trend","Stable")),
        "player_cluster":    str(row.get("player_cluster","Unknown")),
    }


@router.get("/player/{player_id}/stats")
def get_stats(player_id: int, match_id: Optional[int] = Query(None), season: Optional[str] = Query(None)):
    d  = _load(season=season)
    pf = d["computed"][d["computed"]["player_id"] == player_id]
    if not len(pf): raise HTTPException(404, f"Player {player_id} not found")
    row = pf[pf["match_id"] == match_id].iloc[0] if match_id else pf.iloc[-1]

    return {
        "uuid":        str(row.get("uuid","")),
        "player_id":   _si(row["player_id"]),
        "player_name": str(row["player_name"]),
        "match_id":    _si(row["match_id"]),
        "passing":    {"total_passes":_si(row.get("total_passes")),
                       "pass_accuracy":_sf(row.get("pass_accuracy")),
                       "progressive_passes":_si(row.get("progressive_passes")),
                       "passes_under_pressure":_si(row.get("passes_under_pressure"))},
        "shooting":   {"total_shots":_si(row.get("total_shots")),
                       "shots_on_target":_si(row.get("shots_on_target")),
                       "goals":_si(row.get("goals")),
                       "total_xg":_sf(row.get("total_xg")),
                       "xg_per_shot":_sf(row.get("xg_per_shot"))},
        "positioning":{"avg_position_x":_sf(row.get("avg_position_x")),
                       "avg_position_y":_sf(row.get("avg_position_y")),
                       "position_deviation":_sf(row.get("position_deviation")),
                       "attacking_tendency":_sf(row.get("attacking_tendency"))},
        "pressing":   {"total_pressures":_si(row.get("total_pressures")),
                       "pressure_regains":_si(row.get("pressure_regains")),
                       "pressing_efficiency":_sf(row.get("pressing_efficiency"))},
        "physical":   {"total_actions":_si(row.get("total_actions")),
                       "distance_covered":_sf(row.get("distance_covered")),
                       "activity_drop_2nd_half":_sf(row.get("activity_drop_2nd_half"))},
        "movement":   {"total_dribbles":_si(row.get("total_dribbles")),
                       "successful_dribbles":_si(row.get("successful_dribbles")),
                       "dribble_success_rate":_sf(row.get("dribble_success_rate"))},
        "behavioral": {"fouls_committed":_si(row.get("fouls_committed")),
                       "yellow_cards":_si(row.get("yellow_cards")),
                       "ball_retention_rate":_sf(row.get("ball_retention_rate"))},
    }


@router.get("/player/{player_id}/history")
def get_history(player_id: int, season_id: Optional[int] = Query(None), season: Optional[str] = Query(None)):
    d  = _load(season=season)
    ps = d["scores"][d["scores"]["player_id"] == player_id]
    if not len(ps): raise HTTPException(404, f"Player {player_id} not found")

    history = ps.merge(
        d["matches"][["match_id","match_date","home_team","away_team"]],
        on="match_id", how="left"
    ).sort_values("match_date")

    return {
        "player_id":   player_id,
        "player_name": str(ps.iloc[0]["player_name"]),
        "matches":     [{"match_id":_si(r["match_id"]),"match_date":str(r.get("match_date","")),
                         "home_team":str(r.get("home_team","")),"away_team":str(r.get("away_team","")),
                         "overall_score":_sf(r["overall_score"]),"vaep_rating":_sf(r.get("vaep_rating"))}
                        for _, r in history.iterrows()],
        "season_avg":  {"overall_score":_sf(ps["overall_score"].mean()),
                         "vaep_rating":_sf(ps["vaep_rating"].mean()) if "vaep_rating" in ps.columns else None},
    }


@router.get("/player/compare")
def compare(player_ids: str = Query(...), match_id: Optional[int] = Query(None), season: Optional[str] = Query(None)):
    d    = _load(season=season)
    # Handle float strings like "4320.0" from frontend
    ids  = [int(float(i.strip())) for i in player_ids.split(",")]
    result = []
    for pid in ids:
        ps = d["scores"][d["scores"]["player_id"] == pid]
        if not len(ps): continue
        row = ps[ps["match_id"]==match_id].iloc[0] if match_id and len(ps[ps["match_id"]==match_id]) \
              else ps.mean(numeric_only=True)
        result.append({
            "player_id":    pid,
            "player_name":  str(ps.iloc[0]["player_name"]),
            "position":     str(ps.iloc[0].get("position_group","Unknown")),
            "overall_score":_sf(row["overall_score"]),
            "scores": {"passing":_sf(row["passing_score"]),"shooting":_sf(row["shooting_score"]),
                       "positioning":_sf(row["positioning_score"]),"pressing":_sf(row["pressing_score"]),
                       "movement":_sf(row["movement_score"]),"physical":_sf(row["physical_score"]),
                       "behavioral":_sf(row["behavioral_score"])},
            "vaep_rating":_sf(row.get("vaep_rating")),
        })
    return {"comparison": result}


@router.get("/player/head-to-head")
def head_to_head(
    p1: int = Query(...),
    p2: int = Query(...),
    match_id: Optional[int] = Query(None),
    context: str = Query("season"),
    season: Optional[str] = Query(None),
):
    d = _load(season=season)
    sc = d["scores"]
    cf = d["computed"]
    mt = d["matches"]
    vaep = d["vaep"]

    def _player_data(pid):
        psc = sc[sc["player_id"] == pid]
        if not len(psc):
            return None
        pcf = cf[cf["player_id"] == pid]
        pvaep = vaep[vaep["player_id"] == pid]

        if context == "match" and match_id:
            row = psc[psc["match_id"] == match_id]
            crow = pcf[pcf["match_id"] == match_id]
            if not len(row):
                row = psc
            if not len(crow):
                crow = pcf
            srow = row.iloc[0] if len(row) else psc.mean(numeric_only=True)
            crow = crow.iloc[0] if len(crow) else pcf.mean(numeric_only=True)
        elif context == "last5":
            merged = psc.merge(mt[["match_id", "match_date"]], on="match_id", how="left").sort_values("match_date")
            last5 = merged.tail(5)
            srow = last5.mean(numeric_only=True) if len(last5) else psc.mean(numeric_only=True)
            last5_ids = last5["match_id"].tolist()
            csub = pcf[pcf["match_id"].isin(last5_ids)] if len(last5_ids) else pcf
            crow = csub.mean(numeric_only=True) if len(csub) else pcf.mean(numeric_only=True)
        else:
            srow = psc.mean(numeric_only=True)
            crow = pcf.mean(numeric_only=True) if len(pcf) else {}

        row0 = psc.iloc[0]
        return {
            "player_id": pid,
            "player_name": str(row0["player_name"]),
            "position_group": str(row0.get("position_group", "Unknown")),
            "player_cluster": str(row0.get("player_cluster", "Unknown")),
            "initials": "".join(w[0].upper() for w in str(row0["player_name"]).split() if w)[:2],
            "overall_score": _sf(srow.get("overall_score")),
            "scores": {
                "passing": _sf(srow.get("passing_score")),
                "shooting": _sf(srow.get("shooting_score")),
                "positioning": _sf(srow.get("positioning_score")),
                "pressing": _sf(srow.get("pressing_score")),
                "movement": _sf(srow.get("movement_score")),
                "physical": _sf(srow.get("physical_score")),
                "behavioral": _sf(srow.get("behavioral_score")),
            },
            "percentile": _sf(row0.get("percentile_in_league")),
            "performance_trend": str(row0.get("performance_trend", "Stable")),
            "vaep_rating": _sf(srow.get("vaep_rating")),
            "stats": {
                "total_passes": _si(crow.get("total_passes")),
                "pass_accuracy": _sf(crow.get("pass_accuracy")),
                "progressive_passes": _si(crow.get("progressive_passes")),
                "total_shots": _si(crow.get("total_shots")),
                "total_xg": _sf(crow.get("total_xg")),
                "xg_per_shot": _sf(crow.get("xg_per_shot")),
                "goals": _si(crow.get("goals")),
                "shots_on_target": _si(crow.get("shots_on_target")),
                "total_dribbles": _si(crow.get("total_dribbles")),
                "successful_dribbles": _si(crow.get("successful_dribbles")),
                "dribble_success_rate": _sf(crow.get("dribble_success_rate")),
                "total_pressures": _si(crow.get("total_pressures")),
                "pressure_regains": _si(crow.get("pressure_regains")),
                "distance_covered": _sf(crow.get("distance_covered")),
                "ball_retention_rate": _sf(crow.get("ball_retention_rate")),
                "fouls_won": _si(crow.get("fouls_won")),
            },
        }

    pd1 = _player_data(p1)
    pd2 = _player_data(p2)
    if pd1 is None or pd2 is None:
        raise HTTPException(404, "One or both players not found")

    # H2H metrics
    h2h_metrics = [
        ("ML Avg Score", pd1["overall_score"], pd2["overall_score"], 10, lambda v: f"{v:.1f}"),
        ("Pass Accuracy", pd1["stats"]["pass_accuracy"], pd2["stats"]["pass_accuracy"], 100, lambda v: f"{v:.1f}%"),
        ("xG per Match", pd1["stats"]["total_xg"], pd2["stats"]["total_xg"], 2.0, lambda v: f"{v:.2f}"),
        ("Dribble Success%", pd1["stats"]["dribble_success_rate"], pd2["stats"]["dribble_success_rate"], 80, lambda v: f"{v:.1f}%"),
        ("Shooting Score", pd1["scores"]["shooting"], pd2["scores"]["shooting"], 10, lambda v: f"{v:.1f}"),
        ("Pressing Score", pd1["scores"]["pressing"], pd2["scores"]["pressing"], 10, lambda v: f"{v:.1f}"),
        ("VAEP Rating", pd1["vaep_rating"], pd2["vaep_rating"], 3.0, lambda v: f"{v:.2f}"),
        ("Progressive Passes", pd1["stats"]["progressive_passes"], pd2["stats"]["progressive_passes"], 20, lambda v: f"{v:.1f}"),
        ("Distance (km)", pd1["stats"]["distance_covered"], pd2["stats"]["distance_covered"], 14, lambda v: f"{v:.1f}km" if pd1["stats"]["distance_covered"] else "N/A"),
        ("Ball Retention%", pd1["stats"]["ball_retention_rate"], pd2["stats"]["ball_retention_rate"], 100, lambda v: f"{v:.1f}%"),
    ]

    h2h_data = []
    for label, v1, v2, mx, fmt in h2h_metrics:
        if v1 is None and v2 is None:
            continue
        v1_safe = v1 if v1 is not None else 0
        v2_safe = v2 if v2 is not None else 0
        h2h_data.append({
            "label": label,
            "val1": v1_safe,
            "val2": v2_safe,
            "max": mx,
            "p1_wins": v1_safe >= v2_safe,
            "formatted1": fmt(v1_safe) if v1 is not None else "N/A",
            "formatted2": fmt(v2_safe) if v2 is not None else "N/A",
        })

    # Insights
    insights = []
    score_dims = [
        ("passing", "Passing", "#3b82f6"),
        ("shooting", "Shooting", "#ef4444"),
        ("positioning", "Positioning", "#22c55e"),
        ("pressing", "Pressing", "#f97316"),
        ("movement", "Movement", "#a855f7"),
        ("physical", "Physical", "#f59e0b"),
        ("behavioral", "Behavioral", "#06b6d4"),
    ]
    # Find biggest advantages
    diffs = []
    for key, label, _ in score_dims:
        v1 = pd1["scores"].get(key, 0) or 0
        v2 = pd2["scores"].get(key, 0) or 0
        diffs.append((label, v1 - v2, v1, v2))
    diffs.sort(key=lambda x: abs(x[1]), reverse=True)

    if diffs:
        top = diffs[0]
        if top[1] > 0:
            insights.append({
                "type": "blue",
                "title": f"{pd1['player_name'].split()[-1]} Advantage: {top[0]}",
                "body": f"{pd1['player_name'].split()[-1]} leads in {top[0]} ({top[2]:.1f} vs {top[3]:.1f}), a gap of +{top[1]:.1f}. This is the largest dimensional advantage in the comparison.",
                "metric_label": f"{top[2]:.1f} vs {top[3]:.1f}",
                "color": "#58A6FF",
            })
        else:
            insights.append({
                "type": "green",
                "title": f"{pd2['player_name'].split()[-1]} Advantage: {top[0]}",
                "body": f"{pd2['player_name'].split()[-1]} dominates in {top[0]} ({top[3]:.1f} vs {top[2]:.1f}), a gap of {abs(top[1]):.1f}. This is the largest dimensional advantage in the comparison.",
                "metric_label": f"{top[3]:.1f} vs {top[2]:.1f}",
                "color": "#00D084",
            })

    # Overall score comparison
    ov1 = pd1["overall_score"] or 0
    ov2 = pd2["overall_score"] or 0
    if ov1 > ov2:
        insights.append({
            "type": "yellow",
            "title": f"{pd1['player_name'].split()[-1]} Higher Overall Score",
            "body": f"{pd1['player_name'].split()[-1]} averages {ov1:.1f} vs {pd2['player_name'].split()[-1]}'s {ov2:.1f} this season. A difference of +{ov1 - ov2:.1f} in overall ML performance.",
            "metric_label": f"+{ov1 - ov2:.1f} gap",
            "color": "#D29922",
        })
    else:
        insights.append({
            "type": "yellow",
            "title": f"{pd2['player_name'].split()[-1]} Higher Overall Score",
            "body": f"{pd2['player_name'].split()[-1]} averages {ov2:.1f} vs {pd1['player_name'].split()[-1]}'s {ov1:.1f} this season. A difference of {ov2 - ov1:.1f} in overall ML performance.",
            "metric_label": f"{ov2 - ov1:.1f} gap",
            "color": "#D29922",
        })

    # Trend comparison
    trend1 = pd1.get("performance_trend", "Stable")
    trend2 = pd2.get("performance_trend", "Stable")
    tr_map = {"Improving": 1, "Stable": 0, "Declining": -1}
    tr_diff = tr_map.get(trend1, 0) - tr_map.get(trend2, 0)
    if tr_diff > 0:
        insights.append({
            "type": "green" if tr_diff > 0 else "red",
            "title": f"{pd1['player_name'].split()[-1]} Better Form Trend",
            "body": f"{pd1['player_name'].split()[-1]} is {trend1.lower()} while {pd2['player_name'].split()[-1]} is {trend2.lower()}. {pd1['player_name'].split()[-1]} has stronger momentum entering the next match.",
            "metric_label": f"{trend1} vs {trend2}",
            "color": "#00D084" if tr_diff > 0 else "#F85149",
        })
    elif tr_diff < 0:
        insights.append({
            "type": "green" if tr_diff < 0 else "red",
            "title": f"{pd2['player_name'].split()[-1]} Better Form Trend",
            "body": f"{pd2['player_name'].split()[-1]} is {trend2.lower()} while {pd1['player_name'].split()[-1]} is {trend1.lower()}. {pd2['player_name'].split()[-1]} has stronger momentum entering the next match.",
            "metric_label": f"{trend2} vs {trend1}",
            "color": "#00D084" if tr_diff < 0 else "#F85149",
        })

    # Shared matches
    p1_scores = sc[sc["player_id"] == p1][["match_id", "overall_score", "performance_trend"]]
    p2_scores = sc[sc["player_id"] == p2][["match_id", "overall_score", "performance_trend"]]
    shared = p1_scores.merge(p2_scores, on="match_id", suffixes=("_p1", "_p2")).merge(
        mt[["match_id", "match_week", "home_team", "away_team", "home_score", "away_score", "match_date"]],
        on="match_id"
    )
    barca_matches = shared[
        shared["home_team"].str.contains("Barcelona", case=False, na=False) |
        shared["away_team"].str.contains("Barcelona", case=False, na=False)
    ]
    shared_matches = []
    for _, r in barca_matches.sort_values("match_week", ascending=False).iterrows():
        is_home = "Barcelona" in str(r.get("home_team", ""))
        opponent = str(r.get("away_team", "")) if is_home else str(r.get("home_team", ""))
        h = int(r.get("home_score", 0))
        a = int(r.get("away_score", 0))
        result = f"W {h}-{a}" if (is_home and h > a) or (not is_home and a > h) else \
                 f"D {h}-{a}" if h == a else f"L {h}-{a}"
        shared_matches.append({
            "match_id": _si(r["match_id"]),
            "match_week": _si(r.get("match_week")),
            "opponent": opponent,
            "result": result,
            "date": str(r.get("match_date", "")),
            "p1_score": _sf(r.get("overall_score_p1")),
            "p2_score": _sf(r.get("overall_score_p2")),
            "p1_trend": str(r.get("performance_trend_p1", "Stable"))[:2],
            "p2_trend": str(r.get("performance_trend_p2", "Stable"))[:2],
        })

    # Available matches
    all_barca = sc[sc["player_id"] == p1].merge(
        mt[["match_id", "match_week", "home_team", "away_team", "home_score", "away_score"]],
        on="match_id"
    )
    all_barca = all_barca[
        all_barca["home_team"].str.contains("Barcelona", case=False, na=False) |
        all_barca["away_team"].str.contains("Barcelona", case=False, na=False)
    ]
    available_matches = [
        {
            "match_id": _si(r["match_id"]),
            "match_week": _si(r.get("match_week")),
            "label": f"W{_si(r.get('match_week'))} — {r['home_team']} {_si(r.get('home_score'))}-{_si(r.get('away_score'))} {r['away_team']}",
        }
        for _, r in all_barca.sort_values("match_week", ascending=False).iterrows()
    ]

    return {
        "player1": pd1,
        "player2": pd2,
        "h2h_data": h2h_data,
        "insights": insights,
        "shared_matches": shared_matches,
        "available_matches": available_matches,
        "context": context,
    }


@router.get("/player/dashboard/{player_name}")
def get_dashboard(player_name: str, match_id: Optional[int] = Query(None)):
    """
    الـ Endpoint الرئيسي للـ Player Dashboard
    بيرجع كل الـ charts كـ base64 images
    """
    result = generate_all_charts(player_name, match_id=match_id)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@router.get("/player/dashboard-data/{player_name}")
def get_dashboard_data(player_name: str, match_id: Optional[int] = Query(None)):
    """
    Endpoint لرجع البيانات الخام للـ Charts (JSON)
    مناسب للـ Frontend Rendering مع Animation
    """
    result = get_player_chart_data(player_name, match_id=match_id)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@router.get("/player/season/list")
def get_season_list():
    """List all available seasons."""
    return {"seasons": _get_available_seasons()}


@router.get("/player/{player_id}/evolution")
def get_player_evolution(player_id: int, season: Optional[str] = Query(None)):
    """Year-over-year evolution of a player's metrics."""
    d = _load(season=season)
    sc = d["scores"]
    ps = sc[sc["player_id"] == player_id]
    if not len(ps):
        raise HTTPException(404, f"Player {player_id} not found")

    if "season_label" in ps.columns:
        yearly = ps.groupby("season_label").agg(
            avg_score=("overall_score", "mean"),
            best_score=("overall_score", "max"),
            matches=("match_id", "count"),
            avg_vaep=("vaep_rating", "mean"),
        ).reset_index().sort_values("season_label")

        return {
            "player_id": player_id,
            "player_name": str(ps.iloc[0]["player_name"]),
            "evolution": [
                {
                    "season_label": r["season_label"],
                    "avg_score": _sf(r["avg_score"]),
                    "best_score": _sf(r["best_score"]),
                    "matches": _si(r["matches"]),
                    "avg_vaep": _sf(r["avg_vaep"]) if r["avg_vaep"] is not None else None,
                }
                for _, r in yearly.iterrows()
            ],
            "trend": _sf(ps["overall_score"].mean()),
        }
    return {
        "player_id": player_id,
        "player_name": str(ps.iloc[0]["player_name"]),
        "evolution": [],
        "trend": _sf(ps["overall_score"].mean()),
    }


@router.get("/player/season-trends")
def get_season_trends(season: Optional[str] = Query(None)):
    import numpy as np

    d = _load(season=season)
    sc = d["scores"]
    cf = d["computed"]
    mt = d["matches"]
    vaep_df = d["vaep"]

    # Filter to Barcelona squad
    is_barca = sc["team_name"].astype(str).str.contains("Barcelona", case=False, na=False)
    barca = sc[is_barca].copy()
    barca_ids = barca["player_id"].unique()

    # All Barcelona matches sorted
    barca_match_ids = barca["match_id"].unique()
    barca_mt = mt[mt["match_id"].isin(barca_match_ids)].sort_values("match_week")
    all_match_ids = barca_mt["match_id"].tolist()
    total_matches = len(all_match_ids)
    match_weeks = barca_mt["match_week"].tolist()

    # Per-player season aggregates
    grouped = barca.groupby("player_id")
    player_avgs = grouped["overall_score"].mean()
    player_counts = grouped["overall_score"].count()

    # Top 15 players by matches played then avg score
    top_players = (
        barca.groupby(["player_id", "player_name", "position_group", "player_cluster"])
        .agg(avg_score=("overall_score", "mean"), matches_played=("overall_score", "count"))
        .reset_index()
        .sort_values(["matches_played", "avg_score"], ascending=[False, False])
        .head(15)
    )

    # Helper to get scores for a player across all Barcelona matches
    def player_match_scores(pid):
        ps = barca[barca["player_id"] == pid].set_index("match_id")
        return [None if mid not in ps.index else (None if np.isnan(float(ps.loc[mid, "overall_score"])) else round(float(ps.loc[mid, "overall_score"]), 2)) for mid in all_match_ids]

    # Helper to get computed stat across Barcelona matches
    def player_computed_stat(pid, col):
        pcf = cf[(cf["player_id"] == pid) & (cf["match_id"].isin(all_match_ids))].set_index("match_id")
        n_col = col if col in pcf.columns else None
        if n_col is None:
            return [None] * len(all_match_ids)
        return [None if mid not in pcf.index else (None if np.isnan(float(pcf.loc[mid, n_col])) else round(float(pcf.loc[mid, n_col]), 3)) for mid in all_match_ids]

    # --- 1. Season Summary KPIs ---
    team_cf = cf[cf["match_id"].isin(all_match_ids) & cf["player_id"].isin(barca_ids)]
    summary = {
        "squad_avg_score": _sf(barca["overall_score"].mean()),
        "total_matches": total_matches,
        "avg_pass_accuracy": _sf(team_cf["pass_accuracy"].mean()) if "pass_accuracy" in team_cf.columns else None,
        "team_xg": _sf(team_cf["total_xg"].sum()) if "total_xg" in team_cf.columns else None,
        "total_goals_scored": _si(barca_mt["home_score"].sum() + barca_mt["away_score"].sum()) if "home_score" in barca_mt.columns else None,
        "goals_per_match": _sf((barca_mt["home_score"].sum() + barca_mt["away_score"].sum()) / len(barca_mt)) if "home_score" in barca_mt.columns else None,
        "total_dribbles": _si(team_cf["total_dribbles"].sum()) if "total_dribbles" in team_cf.columns else None,
        "dribble_success_rate": _sf(
            (team_cf["successful_dribbles"].sum() / team_cf["total_dribbles"].sum() * 100)
            if "successful_dribbles" in team_cf.columns and team_cf["total_dribbles"].sum() > 0 else None
        ),
    }

    # --- 2. Score Evolution (top 5 players) ---
    top5 = top_players.head(5)
    score_evolution = {
        "match_weeks": match_weeks,
        "players": [
            {
                "player_id": _si(r["player_id"]),
                "player_name": r["player_name"],
                "position_group": r.get("position_group", ""),
                "scores": player_match_scores(r["player_id"]),
            }
            for _, r in top5.iterrows()
        ],
        "squad_avg": [round(float(barca[barca["match_id"] == mid]["overall_score"].mean()), 2) for mid in all_match_ids],
    }

    # --- 3. Form Cards (top 10 players, last 10 matches) ---
    top10 = top_players.head(10)
    last10_ids = all_match_ids[-10:] if len(all_match_ids) >= 10 else all_match_ids
    form_cards = []
    for _, r in top10.iterrows():
        pid = r["player_id"]
        ps = barca[barca["player_id"] == pid].set_index("match_id")
        last10_scores = [round(float(ps.loc[mid, "overall_score"]), 2) for mid in last10_ids if mid in ps.index]
        if not last10_scores:
            last10_scores = [round(float(r["avg_score"]), 2)] * len(last10_ids)
        avg = round(float(r["avg_score"]), 2)
        trend_scores = [round(float(ps.loc[mid, "overall_score"]), 2) for mid in all_match_ids if mid in ps.index]
        trend_val = 0.0
        if len(trend_scores) >= 2:
            last_v = trend_scores[-1]
            prev_avg = sum(trend_scores[:-1]) / len(trend_scores[:-1])
            trend_val = round(last_v - prev_avg, 2)
        trend_dir = "up" if trend_val > 0.1 else ("dn" if trend_val < -0.1 else "st")
        form_cards.append({
            "player_id": _si(pid),
            "player_name": r["player_name"],
            "initials": "".join(w[0].upper() for w in str(r["player_name"]).split() if w)[:2],
            "position_group": r.get("position_group", ""),
            "last_10_scores": last10_scores,
            "avg_score": avg,
            "trend": trend_dir,
            "delta": f"{trend_val:+0.1f}",
        })

    # --- 4. Heatmap (top 10 players x last 10 matches) ---
    heatmap = {
        "players": [c["player_name"] for c in form_cards],
        "match_weeks": [int(barca_mt[barca_mt["match_id"] == mid]["match_week"].iloc[0]) for mid in last10_ids],
        "scores": [c["last_10_scores"] for c in form_cards],
    }

    # --- 5. Rankings ---
    rankings = []
    for _, r in top_players.iterrows():
        pid = r["player_id"]
        all_scores = [round(float(s), 2) for s in barca[barca["player_id"] == pid]["overall_score"].tolist()]
        tval = 0.0
        if len(all_scores) >= 2:
            lv = all_scores[-1]
            pa = sum(all_scores[:-1]) / len(all_scores[:-1])
            tval = round(lv - pa, 2)
        tdir = "up" if tval > 0.1 else ("dn" if tval < -0.1 else "st")
        pname = r["player_name"]
        rankings.append({
            "player_name": pname,
            "position_group": r.get("position_group", ""),
            "initials": "".join(w[0].upper() for w in str(pname).split() if w)[:2],
            "avg_score": _sf(r["avg_score"]),
            "matches_played": _si(r["matches_played"]),
            "trend": tdir,
            "trend_value": tval,
        })
    rankings.sort(key=lambda p: p["avg_score"] or 0, reverse=True)
    for i, p in enumerate(rankings):
        p["rank"] = i + 1

    # --- 6. Metric Trends ---
    # Pick specific players for each metric based on position
    def top_by_position(pos_key, n=3):
        subset = top_players[top_players["position_group"].str.contains(pos_key, case=False, na=False)]
        if len(subset) < n:
            subset = top_players.head(n)
        return subset.head(n)

    # xG trend: top 3 forwards
    fw = top_by_position("Attacker", 3)
    pass_mid = top_by_position("Midfielder", 3)

    def metric_trend(players_df, col):
        items = []
        for _, r in players_df.iterrows():
            vals = player_computed_stat(r["player_id"], col)
            items.append({
                "player_name": r["player_name"],
                "values": vals,
            })
        return items

    metric_trends = {
        "xg": {"players": metric_trend(fw, "total_xg")},
        "pass_accuracy": {"players": metric_trend(pass_mid, "pass_accuracy")},
        "dribble": {"players": metric_trend(fw, "dribble_success_rate")},
    }

    # VAEP trend: top 3 by avg vaep (scores data, not computed)
    vaep_avgs = barca.groupby(["player_id", "player_name"])["vaep_rating"].mean().reset_index()
    vaep_top3 = vaep_avgs.sort_values("vaep_rating", ascending=False).head(3)
    vaep_items = []
    for _, r in vaep_top3.iterrows():
        ps = barca[barca["player_id"] == r["player_id"]].set_index("match_id")
        vals = [None if mid not in ps.index else (None if np.isnan(float(ps.loc[mid, "vaep_rating"])) else round(float(ps.loc[mid, "vaep_rating"]), 3)) for mid in all_match_ids]
        vaep_items.append({"player_name": r["player_name"], "values": vals})
    metric_trends["vaep"] = {"players": vaep_items}

    # --- 7. Scatter: VAEP Rating vs Overall Score ---
    scatter = []
    for _, r in top_players.iterrows():
        pid = r["player_id"]
        pvaep = barca[barca["player_id"] == pid]["vaep_rating"].mean()
        scatter.append({
            "player_name": r["player_name"],
            "initials": "".join(w[0].upper() for w in str(r["player_name"]).split() if w)[:2],
            "position_group": r.get("position_group", ""),
            "overall_score": _sf(r["avg_score"]),
            "vaep_rating": _sf(pvaep),
        })

    return {
        "summary": summary,
        "score_evolution": score_evolution,
        "form_cards": form_cards,
        "heatmap": heatmap,
        "rankings": rankings,
        "metric_trends": metric_trends,
        "scatter": scatter,
    }


@router.get("/player/match-log")
def get_match_log(match_id: Optional[int] = Query(None), season: Optional[str] = Query(None)):
    import numpy as np

    d = _load(season=season)
    sc = d["scores"]
    cf = d["computed"]
    mt = d["matches"]
    ev = d["events"]

    is_barca = sc["team_name"].astype(str).str.contains("Barcelona", case=False, na=False)
    barca = sc[is_barca].copy()
    barca_ids = barca["player_id"].unique()
    barca_match_ids = barca["match_id"].unique()
    barca_mt = mt[mt["match_id"].isin(barca_match_ids)].sort_values("match_week").copy()

    # Resolve which match to show detail for
    detail_match_id = match_id
    if detail_match_id is None:
        if len(barca_mt):
            detail_match_id = int(barca_mt["match_id"].iloc[-1])
        else:
            detail_match_id = int(barca_match_ids[0]) if len(barca_match_ids) else None

    # Build match list
    match_list = []
    for _, mr in barca_mt.iterrows():
        mid = int(mr["match_id"])
        ms = sc[sc["match_id"] == mid]
        barca_ms = ms[ms["player_id"].isin(barca_ids)]
        opp_ms = ms[~ms["player_id"].isin(barca_ids)]

        # Squad avg
        squad_avg = _sf(barca_ms["overall_score"].mean()) if len(barca_ms) else None

        # Result
        h_team = str(mr.get("home_team", ""))
        a_team = str(mr.get("away_team", ""))
        h_score = _si(mr.get("home_score"))
        a_score = _si(mr.get("away_score"))
        is_home = "Barcelona" in h_team
        opp = a_team if is_home else h_team
        if is_home:
            result = "W" if h_score > a_score else ("D" if h_score == a_score else "L")
        else:
            result = "W" if a_score > h_score else ("D" if a_score == h_score else "L")

        # Compute stats from computed features
        barca_cf = cf[(cf["match_id"] == mid) & (cf["player_id"].isin(barca_ids))]
        total_xg = _sf(barca_cf["total_xg"].sum()) if "total_xg" in barca_cf.columns else None
        total_shots = _si(barca_cf["total_shots"].sum()) if "total_shots" in barca_cf.columns else None
        barca_passes = float(barca_cf["total_passes"].sum()) if "total_passes" in barca_cf.columns else 1

        # Possession estimate: total-action ratio (passes + carries + dribbles + shots)
        opp_cf = cf[(cf["match_id"] == mid) & (cf["player_id"].isin(opp_ms["player_id"].unique()))]
        def _total_actions(df):
            return float(df["total_passes"].sum() + df["total_carries"].sum() + df["total_dribbles"].sum() + df["total_shots"].sum()) if all(c in df.columns for c in ["total_passes","total_carries","total_dribbles","total_shots"]) else None
        barca_acts = _total_actions(barca_cf)
        opp_acts = _total_actions(opp_cf)
        possession = round((barca_acts / (barca_acts + opp_acts)) * 100, 1) if barca_acts is not None and opp_acts is not None and (barca_acts + opp_acts) > 0 else None

        # Goals scored / conceded
        goals_for = h_score if is_home else a_score
        goals_against = a_score if is_home else h_score

        match_list.append({
            "match_id": mid,
            "match_week": _si(mr.get("match_week")),
            "date": str(mr.get("match_date", "")),
            "opponent": opp,
            "result": result,
            "score": f"{h_score}-{a_score}",
            "home_team": h_team,
            "away_team": a_team,
            "home_score": h_score,
            "away_score": a_score,
            "is_home": is_home,
            "squad_avg_score": squad_avg,
            "possession": possession,
            "total_xg": total_xg,
            "total_shots": total_shots,
            "goals_for": goals_for,
            "goals_against": goals_against,
        })

    # Build match detail
    detail = None
    if detail_match_id is not None:
        mr = barca_mt[barca_mt["match_id"] == detail_match_id]
        if len(mr):
            mr = mr.iloc[0]
            mid = detail_match_id
            ms = sc[sc["match_id"] == mid]
            barca_ms = ms[ms["player_id"].isin(barca_ids)]
            opp_ms = ms[~ms["player_id"].isin(barca_ids)]

            h_team = str(mr.get("home_team", ""))
            a_team = str(mr.get("away_team", ""))
            h_score = _si(mr.get("home_score"))
            a_score = _si(mr.get("away_score"))
            is_home = "Barcelona" in h_team
            opp = a_team if is_home else h_team
            if is_home:
                result = "W" if h_score > a_score else ("D" if h_score == a_score else "L")
            else:
                result = "W" if a_score > h_score else ("D" if a_score == h_score else "L")

            squad_avg = _sf(barca_ms["overall_score"].mean()) if len(barca_ms) else None

            barca_cf = cf[(cf["match_id"] == mid) & (cf["player_id"].isin(barca_ids))]
            total_xg = _sf(barca_cf["total_xg"].sum()) if "total_xg" in barca_cf.columns else None
            total_shots = _si(barca_cf["total_shots"].sum()) if "total_shots" in barca_cf.columns else None
            opp_cf = cf[(cf["match_id"] == mid) & (cf["player_id"].isin(opp_ms["player_id"].unique()))]
            def _total_actions(df):
                return float(df["total_passes"].sum() + df["total_carries"].sum() + df["total_dribbles"].sum() + df["total_shots"].sum()) if all(c in df.columns for c in ["total_passes","total_carries","total_dribbles","total_shots"]) else None
            barca_acts = _total_actions(barca_cf)
            opp_acts = _total_actions(opp_cf)
            possession = round((barca_acts / (barca_acts + opp_acts)) * 100, 1) if barca_acts is not None and opp_acts is not None and (barca_acts + opp_acts) > 0 else None

            goals_for = h_score if is_home else a_score
            goals_against = a_score if is_home else h_score

            # Players
            players = []
            for _, pr in barca_ms.sort_values("overall_score", ascending=False).iterrows():
                pid = pr["player_id"]
                pcf = cf[(cf["player_id"] == pid) & (cf["match_id"] == mid)]
                pcf_r = pcf.iloc[0] if len(pcf) else None
                initials = "".join(w[0].upper() for w in str(pr.get("player_name", "")).split() if w)[:2]
                players.append({
                    "player_id": _si(pid),
                    "player_name": str(pr.get("player_name", "")),
                    "initials": initials,
                    "position_group": str(pr.get("position_group", "")),
                    "overall_score": _sf(pr.get("overall_score")),
                    "vaep_rating": _sf(pr.get("vaep_rating")),
                    "passes": _si(pcf_r.get("total_passes")) if pcf_r is not None and "total_passes" in pcf_r else None,
                    "pass_accuracy": _sf(pcf_r.get("pass_accuracy")) if pcf_r is not None and "pass_accuracy" in pcf_r else None,
                    "shots": _si(pcf_r.get("total_shots")) if pcf_r is not None and "total_shots" in pcf_r else None,
                    "xg": _sf(pcf_r.get("total_xg")) if pcf_r is not None and "total_xg" in pcf_r else None,
                    "dribbles": f"{_si(pcf_r.get('successful_dribbles'))}/{_si(pcf_r.get('total_dribbles'))}" if pcf_r is not None and "successful_dribbles" in pcf_r and "total_dribbles" in pcf_r else None,
                    "dribble_success_rate": _sf(pcf_r.get("dribble_success_rate")) if pcf_r is not None and "dribble_success_rate" in pcf_r else None,
                })

            # Events with xG and VAEP
            match_events = ev[ev["match_id"] == mid].sort_values(["period", "minute"]).copy()
            barca_event_df = match_events[match_events["team_name"].astype(str).str.contains("Barcelona", case=False, na=False)]
            events_list = []
            for _, er in barca_event_df.iterrows():
                ev_xg = _sf(er.get("shot_xg"))
                events_list.append({
                    "minute": _si(er.get("minute")),
                    "period": _si(er.get("period")),
                    "event_type": str(er.get("event_type", "")),
                    "player_name": str(er.get("player_name", "")),
                    "outcome": str(er.get("shot_outcome", er.get("pass_outcome", er.get("dribble_outcome", "")))),
                    "xg": ev_xg,
                })

            # xG flow: cumulative xG per minute across all Barcelona events with shots
            xg_flow_minutes = [0.0] * 121
            for _, er in barca_event_df.iterrows():
                ev_xg = er.get("shot_xg")
                minute = int(er.get("minute", 0))
                if ev_xg is not None and not (isinstance(ev_xg, float) and np.isnan(ev_xg)):
                    if minute < len(xg_flow_minutes):
                        xg_flow_minutes[minute] += float(ev_xg)
            cum = 0.0
            xg_flow = []
            for v in xg_flow_minutes:
                cum += v
                xg_flow.append(round(cum, 4))

            detail = {
                "match_id": mid,
                "match_week": _si(mr.get("match_week")),
                "date": str(mr.get("match_date", "")),
                "home_team": h_team,
                "away_team": a_team,
                "home_score": h_score,
                "away_score": a_score,
                "score": f"{h_score}-{a_score}",
                "result": result,
                "is_home": is_home,
                "opponent": opp,
                "squad_avg_score": squad_avg,
                "possession": possession,
                "total_shots": total_shots,
                "total_xg": total_xg,
                "goals_for": goals_for,
                "goals_against": goals_against,
                "players": players,
                "events": events_list,
                "xg_flow": xg_flow,
            }

    return {
        "matches": match_list,
        "detail": detail,
    }


@router.get("/player/tactical-board")
def get_tactical_board(match_id: Optional[int] = Query(None), season: Optional[str] = Query(None)):
    import numpy as np
    d = _load(season=season)
    sc = d["scores"]
    cf = d["computed"]
    ev = d["events"]
    mt = d["matches"]
    li = d["lineups"]

    is_barca = sc["team_name"].astype(str).str.contains("Barcelona", case=False, na=False)
    barca = sc[is_barca]
    barca_ids = barca["player_id"].unique()
    barca_match_ids = barca["match_id"].unique()

    # Determine match
    barca_mt = mt[mt["match_id"].isin(barca_match_ids)].sort_values("match_week")
    if match_id is None or match_id not in barca_match_ids:
        match_id = int(barca_mt["match_id"].iloc[-1]) if len(barca_mt) else int(barca_match_ids[0])
    match_id = int(match_id)

    # Match context
    mr = barca_mt[barca_mt["match_id"] == match_id]
    if not len(mr):
        raise HTTPException(404, f"Match {match_id} not found")
    mr = mr.iloc[0]
    h_team = str(mr.get("home_team", ""))
    a_team = str(mr.get("away_team", ""))
    h_score = _si(mr.get("home_score"))
    a_score = _si(mr.get("away_score"))
    is_home = "Barcelona" in h_team

    # Players with positions (filter to Starting XI only)
    ms = sc[sc["match_id"] == match_id]
    barca_ms = ms[ms["player_id"].isin(barca_ids)]

    # Determine starters from lineups data
    barca_li = li[(li["match_id"] == match_id) & (li["team_name"].astype(str).str.contains("Barcelona", case=False, na=False))]
    def _is_starter(pos_val):
        if pos_val is None or (isinstance(pos_val, float) and np.isnan(pos_val)):
            return False
        try:
            for item in pos_val if hasattr(pos_val, '__iter__') else []:
                if isinstance(item, dict) and item.get("start_reason") == "Starting XI":
                    return True
            return False
        except Exception:
            return False
    starter_ids = set(int(r["player_id"]) for _, r in barca_li.iterrows() if _is_starter(r.get("positions")))
    if starter_ids:
        barca_ms = barca_ms[barca_ms["player_id"].isin(starter_ids)]

    players = []
    for _, pr in barca_ms.iterrows():
        pid = int(pr["player_id"])
        pcf = cf[(cf["player_id"] == pid) & (cf["match_id"] == match_id)]
        pli = li[(li["player_id"] == pid) & (li["match_id"] == match_id)]
        jersey = int(pli["jersey_number"].iloc[0]) if len(pli) else None

        avg_x = float(pcf["avg_position_x"].iloc[0]) if len(pcf) and "avg_position_x" in pcf.columns else 60.0
        avg_y = float(pcf["avg_position_y"].iloc[0]) if len(pcf) and "avg_position_y" in pcf.columns else 40.0
        svg_x = round(40 + (avg_x / 120 * 620))
        svg_y = round(460 - (avg_y / 80 * 440))

        initials = "".join(w[0].upper() for w in str(pr.get("player_name", "")).split() if w)[:2]
        pcf_r = pcf.iloc[0] if len(pcf) else {}
        pos_group = str(pr.get("position_group", ""))

        players.append({
            "player_id": pid,
            "player_name": str(pr.get("player_name", "")),
            "initials": initials,
            "jersey_number": jersey,
            "position_group": pos_group,
            "overall_score": _sf(pr.get("overall_score")),
            "svg_x": max(50, min(650, svg_x)),
            "svg_y": max(30, min(450, svg_y)),
            "stats": {
                "goals": _si(pcf_r.get("goals")),
                "passes": _si(pcf_r.get("total_passes")),
                "pass_accuracy": _sf(pcf_r.get("pass_accuracy")),
                "dribble_success": _sf(pcf_r.get("dribble_success_rate")),
                "total_xg": _sf(pcf_r.get("total_xg")),
                "shots": _si(pcf_r.get("total_shots")),
                "key_passes": _si(pcf_r.get("progressive_passes")),
                "distance_covered": _sf(pcf_r.get("distance_covered")),
                "pressures": _si(pcf_r.get("total_pressures")),
                "carries": _si(pcf_r.get("total_carries")),
                "fouls_won": _si(pcf_r.get("fouls_won")),
                "vaep_rating": _sf(pr.get("vaep_rating")),
                "complete_passes": _si(pcf_r.get("complete_passes")),
                "successful_dribbles": _si(pcf_r.get("successful_dribbles")),
                "total_dribbles": _si(pcf_r.get("total_dribbles")),
                "ball_receipts": _si(pcf_r.get("ball_receipts")),
            },
        })

    # Formation from position_group counts
    pos_counts = {"GK": 0, "DF": 0, "MF": 0, "FW": 0}
    for p in players:
        g = p["position_group"]
        if "Keeper" in g or g == "GK":
            pos_counts["GK"] += 1
        elif "Defend" in g or g == "DF":
            pos_counts["DF"] += 1
        elif "Midfield" in g or g == "MF":
            pos_counts["MF"] += 1
        elif "Attack" in g or g == "FW":
            pos_counts["FW"] += 1
    formation = f"{pos_counts['DF']}-{pos_counts['MF']}-{pos_counts['FW']}"
    standard_formations = {"4-3-3": "4-3-3", "4-4-2": "4-4-2", "4-2-3-1": "4-2-3-1", "3-5-2": "3-5-2",
                           "5-3-2": "5-3-2", "3-4-3": "3-4-3", "4-1-4-1": "4-1-4-1", "4-3-2-1": "4-3-2-1"}
    display_formation = standard_formations.get(formation, formation)

    # Pass network
    match_events = ev[ev["match_id"] == match_id].sort_values("event_index").copy()
    barca_ev = match_events[match_events["team_name"].astype(str).str.contains("Barcelona", case=False, na=False)]
    barca_ev_list = barca_ev.to_dict("records")
    pass_pairs = {}
    for i, row in enumerate(barca_ev_list):
        if row.get("event_type") != "Pass":
            continue
        passer_id = row.get("player_id")
        pex = row.get("pass_end_x")
        pey = row.get("pass_end_y")
        if passer_id is None or pex is None or pey is None:
            continue
        for j in range(i + 1, min(i + 8, len(barca_ev_list))):
            nr = barca_ev_list[j]
            nr_id = nr.get("player_id")
            nr_type = nr.get("event_type", "")
            if nr_id is not None and nr_id != passer_id and nr_type not in ("Half Start", "Half End", "Starting XI", "Player Off", "Player On"):
                rx = nr.get("location_x")
                ry = nr.get("location_y")
                if rx is not None and ry is not None:
                    dist = ((float(pex) - float(rx))**2 + (float(pey) - float(ry))**2)**0.5
                    if dist < 15:
                        key = (int(passer_id), int(nr_id))
                        pass_pairs[key] = pass_pairs.get(key, 0) + 1
                break

    # Map player_id to initials
    pid_initials = {p["player_id"]: p["initials"] for p in players}
    pass_network = [
        {"from_player_id": f, "to_player_id": t, "count": c,
         "from_initials": pid_initials.get(f, "?"), "to_initials": pid_initials.get(t, "?")}
        for (f, t), c in sorted(pass_pairs.items(), key=lambda x: -x[1])
    ]

    # Heatmap grid (20×15 cells)
    heatmap_grid = [[0.0] * 15 for _ in range(20)]
    for _, er in barca_ev.iterrows():
        lx = er.get("location_x")
        ly = er.get("location_y")
        if lx is not None and ly is not None and not (isinstance(lx, float) and np.isnan(lx)) and not (isinstance(ly, float) and np.isnan(ly)):
            cx = min(19, max(0, int(float(lx) / 120 * 20)))
            cy = min(14, max(0, int(float(ly) / 80 * 15)))
            heatmap_grid[cx][cy] += 1.0

    # Scale grid to 0-1
    max_val = max(max(row) for row in heatmap_grid) if any(any(v for v in row) for row in heatmap_grid) else 1
    if max_val > 0:
        heatmap_grid = [[round(v / max_val, 4) for v in row] for row in heatmap_grid]

    # Tactical notes · generated from match data
    total_passes = _si(sum(p["stats"]["passes"] for p in players))
    total_shots = _si(sum(p["stats"]["shots"] for p in players))
    total_pressures = _si(sum(p["stats"]["pressures"] for p in players))
    total_xg = _sf(sum(p["stats"]["total_xg"] for p in players if p["stats"]["total_xg"] is not None))
    avg_acc = _sf(np.mean([p["stats"]["pass_accuracy"] for p in players if p["stats"]["pass_accuracy"] is not None])) if any(p["stats"]["pass_accuracy"] is not None for p in players) else None

    notes = []
    if total_xg and total_xg > 1.5:
        notes.append({"type": "att", "icon": "⚡", "title": "Attacking Pattern",
                      "text": f"Barcelona generated {total_xg:.2f} total xG from {total_shots} shots. High chance-creation volume through positional attacks."})
    else:
        notes.append({"type": "att", "icon": "⚡", "title": "Attacking Pattern",
                      "text": f"Barcelona had {total_shots} shots ({total_xg:.2f} xG). Build-up focused on maintaining possession and probing the final third."})
    if total_pressures > 80:
        notes.append({"type": "def", "icon": "🛡", "title": "Defensive Shape",
                      "text": f"High-intensity pressing ({total_pressures} pressures). Team engaged aggressively after losing possession, forcing opponent errors."})
    else:
        notes.append({"type": "def", "icon": "🛡", "title": "Defensive Shape",
                      "text": f"Compact mid-block with {total_pressures} pressures. Prioritized defensive structure over aggressive counter-pressing."})
    if total_passes > 500:
        notes.append({"type": "trn", "icon": "↔", "title": "Build-Up Play",
                      "text": f"Possession-dominant ({total_passes} passes completed). Patient build-up with full-backs providing width in the final third."})
    else:
        notes.append({"type": "trn", "icon": "↔", "title": "Transition",
                      "text": f"Direct transitions ({total_passes} passes). Quick vertical passes to exploit space behind the opponent defensive line."})
    avg_score_vals = [p["overall_score"] for p in players if p["overall_score"] is not None]
    avg_score = _sf(np.mean(avg_score_vals)) if avg_score_vals else None
    if avg_score is not None:
        notes.append({"type": "opp", "icon": "🔴", "title": "Opponent Weakness",
                      "text": f"Squad ML score {avg_score:.2f}. Exploit half-spaces and create overloads on the flanks to break through the opponent's defensive block."})

    return {
        "match_context": {
            "match_id": match_id,
            "match_week": _si(mr.get("match_week")),
            "match_date": str(mr.get("match_date", "")),
            "home_team": h_team,
            "away_team": a_team,
            "home_score": h_score,
            "away_score": a_score,
            "score": f"{h_score}-{a_score}",
            "result": "W" if (h_score > a_score if is_home else a_score > h_score) else ("D" if h_score == a_score else "L"),
            "is_home": is_home,
            "opponent": a_team if is_home else h_team,
        },
        "formation": display_formation,
        "formation_raw": formation,
        "players": players,
        "pass_network": pass_network,
        "heatmap_grid": heatmap_grid,
        "notes": notes,
        "available_matches": [
            {
                "match_id": _si(r["match_id"]),
                "match_week": _si(r.get("match_week")),
                "label": f"MD{_si(r.get('match_week'))} — {r.get('home_team','')} {_si(r.get('home_score'))}-{_si(r.get('away_score'))} {r.get('away_team','')}",
            }
            for _, r in barca_mt.iterrows()
        ],
    }
