"""api/routes/player.py"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from api.routes._shared import _load_data, _sf, _si, _to_records
from visualizations.player_dashboard import generate_all_charts, get_player_list, get_player_chart_data

router = APIRouter()


@router.get("/player/list")
def list_players():
    """قائمة بأسماء كل اللاعبين المتاحين"""
    d = _load_data()
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
def get_score(player_id: int, match_id: Optional[int] = Query(None)):
    d  = _load_data()
    ps = d["scores"][d["scores"]["player_id"] == player_id]
    if not len(ps): raise HTTPException(404, f"Player {player_id} not found")

    if match_id:
        row = ps[ps["match_id"] == match_id]
        if not len(row): raise HTTPException(404, f"No data for match {match_id}")
        row = row.iloc[0]
    else:
        row = ps.merge(d["matches"][["match_id","match_date"]], on="match_id", how="left")\
                .sort_values("match_date").iloc[-1]

    return {
        "uuid":        str(row.get("uuid","")),
        "player_id":   _si(row["player_id"]),
        "player_name": str(row["player_name"]),
        "match_id":    _si(row["match_id"]),
        "position":    str(row.get("position_group","Unknown")),
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
def get_stats(player_id: int, match_id: Optional[int] = Query(None)):
    d  = _load_data()
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
def get_history(player_id: int, season_id: Optional[int] = Query(None)):
    d  = _load_data()
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
def compare(player_ids: str = Query(...), match_id: Optional[int] = Query(None)):
    d    = _load_data()
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
):
    """Head-to-head comparison between two players"""
    d = _load_data()
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
