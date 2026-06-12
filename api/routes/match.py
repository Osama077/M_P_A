"""api/routes/match.py"""
import logging
import numpy as np
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from api.routes._shared import _load, _load_data, _sf, _si, _to_records

logger = logging.getLogger(__name__)

try:
    from pipeline.formation_reconstruction import full_match_analysis
    HAS_FORMATION = True
except ImportError as e:
    logger.warning("formation_reconstruction not available: %s", e)
    HAS_FORMATION = False

router = APIRouter()

@router.get("/match/{match_id}/analysis-complete")
def match_analysis_complete(match_id: int, season: Optional[str] = Query(None)):
    """Combined match analysis: formation, stats, timeline, ratings for both teams."""
    d = _load(season=season)
    mi = d["matches"][d["matches"]["match_id"] == match_id]
    if not len(mi):
        raise HTTPException(404, f"Match {match_id} not found")
    m = mi.iloc[0]
    sc = d["scores"][d["scores"]["match_id"] == match_id]
    ev = d["events"]
    li = d["lineups"]
    mt = d["matches"]

    home_team = str(m["home_team"])
    away_team = str(m["away_team"])
    home_score = _si(m.get("home_score"))
    away_score = _si(m.get("away_score"))

    # ── Match context ──
    match_context = {
        "match_id": match_id,
        "match_date": str(m.get("match_date", "")),
        "match_week": _si(m.get("match_week")),
        "home_team": home_team,
        "away_team": away_team,
        "home_score": home_score,
        "away_score": away_score,
        "score": f"{home_score}-{away_score}",
        "stadium": str(m.get("stadium", "")),
        "competition": str(m.get("competition", "")),
        "season_label": str(m.get("season_label", "")),
    }

    # ── Tactical / Formation analysis ──
    tactical = {}
    if HAS_FORMATION:
        try:
            tactical = full_match_analysis(ev, li, match_id, home_team, away_team)
        except Exception as e:
            logger.warning("Formation analysis failed: %s", e)
            tactical = {"error": str(e)}
    
    # Fallback: simple counts from position_group
    if not tactical or "home" not in tactical:
        tactical = _simple_formation_fallback(sc, home_team, away_team)

    # ── Team stats (possession from events) ──
    match_events = ev[ev["match_id"] == match_id]
    team_stats = {}
    for team, label in [(home_team, "home"), (away_team, "away")]:
        te = match_events[match_events["team_name"].astype(str).str.contains(team, case=False, na=False)]
        shots = te[te["event_type"] == "Shot"]
        passes = te[te["event_type"] == "Pass"]
        complete_passes = passes[passes["pass_outcome"] == "Complete"]
        
        team_stats[label] = {
            "possession_pct": 50.0,
            "total_passes": int(len(passes)),
            "pass_accuracy": round(len(complete_passes) / max(len(passes), 1) * 100, 1),
            "total_shots": int(len(shots)),
            "shots_on_target": int(((shots["shot_outcome"] == "Goal") | (shots["shot_outcome"] == "Saved")).sum()),
            "goals": int((shots["shot_outcome"] == "Goal").sum()),
            "total_xg": round(float(shots["shot_xg"].sum()), 2) if len(shots) else 0.0,
            "total_pressures": int((te["event_type"] == "Pressure").sum()),
            "fouls": int((te["event_type"] == "Foul Committed").sum()),
            "fouls_won": int((te["event_type"] == "Foul Won").sum()),
            "total_carries": int((te["event_type"] == "Carry").sum()),
            "progressive_passes": int(te["is_progressive_pass"].sum()) if "is_progressive_pass" in te.columns else 0,
            "ball_recoveries": int((te["event_type"] == "Ball Recovery").sum()),
            "interceptions": int((te["event_type"] == "Interception").sum()),
            "clearances": int((te["event_type"] == "Clearance").sum()),
            "blocks": int((te["event_type"] == "Block").sum()),
            "aerial_duels_won": int((te["event_type"] == "Duel").sum()),
        }
    
    # Possession from pass counts
    hp = team_stats.get("home", {}).get("total_passes", 0)
    ap = team_stats.get("away", {}).get("total_passes", 0)
    total = max(hp + ap, 1)
    if "home" in team_stats:
        team_stats["home"]["possession_pct"] = round(hp / total * 100, 1)
    if "away" in team_stats:
        team_stats["away"]["possession_pct"] = round(ap / total * 100, 1)

    # ── Timeline events ──
    timeline = []
    for _, er in match_events.iterrows():
        etype = str(er.get("event_type", ""))
        if etype in ("Half Start", "Half End", "Starting XI", "Player Off", "Player On", "Substitution", "Tactical Shift", "Injury Stoppage", "Referee Ball-Drop", "Bad Behaviour", "Camera off", "Camera On", "50/50"):
            continue
        timeline.append({
            "minute": _si(er.get("minute")),
            "period": _si(er.get("period")),
            "event_type": etype,
            "player_name": str(er.get("player_name", "")),
            "team": str(er.get("team_name", "")),
            "outcome": str(er.get("shot_outcome", er.get("pass_outcome", er.get("dribble_outcome", "")))),
            "xg": _sf(er.get("shot_xg")),
            "location_x": _sf(er.get("location_x")),
            "location_y": _sf(er.get("location_y")),
        })
    timeline.sort(key=lambda e: (e.get("minute") or 0, e.get("period") or 1))

    # ── Player ratings + match stats + position ratings ──
    comp = d["computed"]
    comp_match = comp[comp["match_id"] == match_id] if "match_id" in comp.columns else None
    pos_kpi_data = d.get("position_kpi", None)
    pos_match = pos_kpi_data[pos_kpi_data["match_id"] == match_id] if pos_kpi_data is not None and "match_id" in pos_kpi_data.columns else None

    def _team_players(team_name):
        col = "team_name" if "team_name" in sc.columns else "team"
        ts = sc[sc[col].astype(str).str.contains(team_name, case=False, na=False)].sort_values("overall_score", ascending=False)
        if comp_match is not None and len(comp_match):
            ts = ts.merge(comp_match[[
                "player_id", "goals", "total_passes", "pass_accuracy",
                "total_shots", "shots_on_target", "total_xg", "total_carries",
                "progressive_passes", "total_pressures", "fouls_committed", "fouls_won",
                "distance_covered", "total_dribbles", "successful_dribbles",
                "dribble_success_rate", "ball_receipts", "ball_retention_rate",
                "interceptions", "clearances", "blocks", "duels_total",
                "saves", "shots_faced", "goals_conceded", "save_pct", "goals_prevented",
                "key_passes", "assists", "chances_created", "minutes_played",
            ]], on="player_id", how="left")
        if pos_match is not None and len(pos_match):
            ts = ts.merge(pos_match[["player_id", "position_kpi", "position_kpi_label"]],
                on="player_id", how="left")
        return [
            {
                "player_id": _si(r.get("player_id")),
                "player_name": str(r.get("player_name", "")),
                "position_group": str(r.get("position_group", "")),
                "overall_score": _sf(r.get("overall_score")),
                "position_kpi": _sf(r.get("position_kpi")),
                "position_kpi_label": str(r.get("position_kpi_label", "")),
                "vaep_rating": _sf(r.get("vaep_rating")),
                "offensive_contribution": _sf(r.get("offensive_contribution")),
                "defensive_contribution": _sf(r.get("defensive_contribution")),
                "possession_contribution": _sf(r.get("possession_contribution")),
                "event_value_score": _sf(r.get("event_value_score")),
                # Match summary stats
                "goals": _si(r.get("goals")),
                "total_passes": _si(r.get("total_passes")),
                "pass_accuracy": _sf(r.get("pass_accuracy")),
                "total_shots": _si(r.get("total_shots")),
                "shots_on_target": _si(r.get("shots_on_target")),
                "total_xg": _sf(r.get("total_xg")),
                "total_carries": _si(r.get("total_carries")),
                "progressive_passes": _si(r.get("progressive_passes")),
                "total_pressures": _si(r.get("total_pressures")),
                "fouls_committed": _si(r.get("fouls_committed")),
                "fouls_won": _si(r.get("fouls_won")),
                "distance_covered": _sf(r.get("distance_covered")),
                "total_dribbles": _si(r.get("total_dribbles")),
                "successful_dribbles": _si(r.get("successful_dribbles")),
                "dribble_success_rate": _sf(r.get("dribble_success_rate")),
                "ball_receipts": _si(r.get("ball_receipts")),
                "ball_retention_rate": _sf(r.get("ball_retention_rate")),
                # New defensive action stats
                "interceptions": _si(r.get("interceptions")),
                "clearances": _si(r.get("clearances")),
                "blocks": _si(r.get("blocks")),
                "duels_total": _si(r.get("duels_total")),
                # GK stats
                "saves": _si(r.get("saves")),
                "shots_faced": _si(r.get("shots_faced")),
                "goals_conceded": _si(r.get("goals_conceded")),
                "save_pct": _sf(r.get("save_pct")),
                "goals_prevented": _sf(r.get("goals_prevented")),
                # Key pass / chance creation
                "key_passes": _si(r.get("key_passes")),
                "assists": _si(r.get("assists")),
                "chances_created": _si(r.get("chances_created")),
                "minutes_played": _sf(r.get("minutes_played")),
            }
            for _, r in ts.iterrows()
        ]

    # ── Match analysis for Barcelona ──
    barca_side = None
    if "barcelona" in home_team.lower():
        barca_side = "home"
    elif "barcelona" in away_team.lower():
        barca_side = "away"
    else:
        barca_side = "home"

    barca_players = _team_players(home_team) if barca_side == "home" else _team_players(away_team)
    opp_players = _team_players(away_team) if barca_side == "home" else _team_players(home_team)
    barca_ts = team_stats.get(barca_side, {})
    opp_ts = team_stats.get("away" if barca_side == "home" else "home", {})

    barca_goals = barca_ts.get("goals", 0) or 0
    opp_goals = opp_ts.get("goals", 0) or 0
    if barca_goals > opp_goals:
        result = "W"
    elif barca_goals < opp_goals:
        result = "L"
    else:
        result = "D"

    # Best/worst Barcelona player (min 15 min played)
    valid = [p for p in barca_players if (p.get("minutes_played") or 0) >= 15]
    best = max(valid, key=lambda p: p.get("position_kpi") or p.get("overall_score") or 0) if valid else (barca_players[0] if barca_players else None)
    worst = min(valid, key=lambda p: p.get("position_kpi") or p.get("overall_score") or 0) if valid else (barca_players[-1] if barca_players else None)

    # Generate reasons
    reasons = []
    barca_shots = barca_ts.get("total_shots", 0) or 0
    barca_sot = barca_ts.get("shots_on_target", 0) or 0
    barca_xg = barca_ts.get("total_xg", 0) or 0
    opp_shots = opp_ts.get("total_shots", 0) or 0
    opp_sot = opp_ts.get("shots_on_target", 0) or 0
    opp_xg = opp_ts.get("total_xg", 0) or 0
    barca_poss = barca_ts.get("possession_pct", 50) or 50
    barca_passes = barca_ts.get("total_passes", 0) or 0
    opp_passes = opp_ts.get("total_passes", 0) or 0

    if result == "W":
        conv = round(barca_goals / max(barca_shots, 1) * 100, 1)
        reasons.append(f"Clinic attack: {barca_goals} goal{'s' if barca_goals!=1 else ''} from {barca_shots} shots ({conv}% conversion)")
        if barca_poss >= 55:
            reasons.append(f"Possession control: {barca_poss}% of the ball")
        else:
            reasons.append(f"Efficient play: only {barca_poss}% possession but created more chances")
        if opp_goals <= 1:
            reasons.append(f"Defensive solidity: conceded just {opp_goals} goal{'s' if opp_goals!=1 else ''}")
        overperf = round(barca_goals - barca_xg, 2)
        if overperf > 0.5:
            reasons.append(f"Clinical finishing: {barca_goals} goals from {barca_xg:.2f} xG (+{overperf} overperformance)")
        if best:
            reasons.append(f"Star performer: {best['player_name']} ({best.get('position_kpi') or best.get('overall_score') or 0:.1f})")
    elif result == "L":
        conv = round(barca_goals / max(barca_shots, 1) * 100, 1)
        reasons.append(f"Missed chances: {barca_shots} shots, only {barca_goals} goal{'s' if barca_goals!=1 else ''} ({conv}% conversion)")
        if barca_poss >= 55 and barca_shots <= opp_shots:
            reasons.append(f"Sterile possession: {barca_poss}% ball but fewer shots than opponent ({barca_shots} vs {opp_shots})")
        if opp_goals >= 2:
            reasons.append(f"Defensive lapses: conceded {opp_goals} goal{'s' if opp_goals!=1 else ''}")
        overperf = round(opp_goals - opp_xg, 2)
        if overperf > 0.5:
            reasons.append(f"Opponent clinical: they scored {opp_goals} from {opp_xg:.2f} xG")
        if worst:
            reasons.append(f"Off day: {worst['player_name']} struggled ({worst.get('position_kpi') or worst.get('overall_score') or 0:.1f})")
    else:
        reasons.append("Even contest: both teams matched across the pitch")
        if barca_xg > opp_xg + 0.5:
            reasons.append(f"Should have won: {barca_xg:.2f} xG vs {opp_xg:.2f} — wasteful finishing")
        elif opp_xg > barca_xg + 0.5:
            reasons.append(f"Fortunate point: opponent created {opp_xg:.2f} xG vs {barca_xg:.2f}")
        if barca_poss >= 55:
            reasons.append(f"Dominant possession ({barca_poss}%) but couldn't break through")

    match_analysis = {
        "barcelona_side": barca_side,
        "result": result,
        "barcelona_goals": barca_goals,
        "opponent_goals": opp_goals,
        "best_player": {
            "player_name": best["player_name"],
            "position_kpi": best.get("position_kpi"),
            "overall_score": best.get("overall_score"),
            "position_group": best.get("position_group"),
        } if best else None,
        "worst_player": {
            "player_name": worst["player_name"],
            "position_kpi": worst.get("position_kpi"),
            "overall_score": worst.get("overall_score"),
            "position_group": worst.get("position_group"),
        } if worst else None,
        "reasons": reasons,
    }

    return {
        "match_context": match_context,
        "tactical": tactical,
        "team_stats": team_stats,
        "timeline": timeline,
        "players": {
            "home": _team_players(home_team),
            "away": _team_players(away_team),
        },
        "match_analysis": match_analysis,
    }


def _simple_formation_fallback(sc, home_team, away_team):
    """Fallback: estimate formation from position_group counts."""
    def _process(team_name):
        col = "team_name" if "team_name" in sc.columns else "team"
        ts = sc[sc[col].astype(str).str.contains(team_name, case=False, na=False)]
        pos_counts = {"GK": 0, "DF": 0, "MF": 0, "FW": 0}
        for _, r in ts.iterrows():
            g = str(r.get("position_group", ""))
            if "Keeper" in g or g == "GK": pos_counts["GK"] += 1
            elif "Defend" in g or g == "DF": pos_counts["DF"] += 1
            elif "Midfield" in g or g == "MF": pos_counts["MF"] += 1
            elif "Attack" in g or g == "FW": pos_counts["FW"] += 1
        formation = f"{pos_counts['DF']}-{pos_counts['MF']}-{pos_counts['FW']}"
        return {"formation": formation, "line_counts": pos_counts,
                "players": [], "pass_network": [], "stats": {}}
    return {"home": _process(home_team), "away": _process(away_team)}


@router.get("/match/list")
def match_list(season: Optional[str] = Query(None)):
    d = _load(season=season)
    df = d["matches"].copy()
    df = df.sort_values("match_date", ascending=False)
    cols = ["match_id", "match_date", "home_team", "away_team",
            "home_score", "away_score", "match_week", "competition",
            "season", "stadium", "season_label"]
    available = [c for c in cols if c in df.columns]
    return {"matches": _to_records(df[available])}

@router.get("/match/{match_id}/report")
def match_report(match_id: int, season: Optional[str] = Query(None)):
    d  = _load(season=season)
    mi = d["matches"][d["matches"]["match_id"] == match_id]
    if not len(mi): raise HTTPException(404, f"Match {match_id} not found")
    m  = mi.iloc[0]
    sc = d["scores"][d["scores"]["match_id"] == match_id]
    ht = str(m["home_team"]); at = str(m["away_team"])

    def team_scores(name):
        col = "team_name" if "team_name" in sc.columns else "team"
        return sc[sc[col].astype(str).str.contains(name, case=False, na=False)]

    hs = team_scores(ht); as_ = team_scores(at)
    return {
        "match_id":   match_id,
        "match_date": str(m.get("match_date","")),
        "home_team":  ht, "away_team": at,
        "score": f"{_si(m.get('home_score',0))}-{_si(m.get('away_score',0))}",
        "home_team_summary": {"avg_overall_score":_sf(hs["overall_score"].mean()),
                               "top_player":str(hs.loc[hs["overall_score"].idxmax(),"player_name"]) if len(hs) else None},
        "away_team_summary": {"avg_overall_score":_sf(as_["overall_score"].mean()),
                               "top_player":str(as_.loc[as_["overall_score"].idxmax(),"player_name"]) if len(as_) else None},
        "all_players": _to_records(sc[["uuid","player_id","player_name","overall_score","vaep_rating"]
                                      if "vaep_rating" in sc.columns else
                                      ["uuid","player_id","player_name","overall_score"]]
                                    .sort_values("overall_score", ascending=False)),
    }


@router.get("/match/{match_id}/events")
def match_events(match_id: int,
                 player_id:  Optional[int] = Query(None),
                 event_type: Optional[str] = Query(None),
                 period:     Optional[int] = Query(None),
                 season:     Optional[str] = Query(None),
                 limit: int = Query(100), offset: int = Query(0)):
    d  = _load(season=season)
    ev = d["events"][d["events"]["match_id"] == match_id].copy()
    if not len(ev): raise HTTPException(404, f"Match {match_id} not found")
    if player_id:  ev = ev[ev["player_id"] == player_id]
    if event_type: ev = ev[ev["event_type"].str.lower() == event_type.lower()]
    if period:     ev = ev[ev["period"] == period]
    total = len(ev); ev = ev.iloc[offset: offset + limit]
    return {
        "match_id":    match_id, "total_events": total,
        "limit": limit, "offset": offset,
        "events": [{"uuid":str(r.get("uuid","")),"event_id":str(r.get("event_id","")),
                    "minute":_si(r.get("minute")), "period":_si(r.get("period")),
                    "event_type":str(r.get("event_type","")),
                    "player_name":str(r.get("player_name","")),
                    "team":str(r.get("team_name", r.get("team",""))),
                    "location":{"x":_sf(r.get("location_x")),"y":_sf(r.get("location_y"))},
                    "outcome":str(r.get("shot_outcome", r.get("pass_outcome",""))),
                    "xg":_sf(r.get("shot_xg"))}
                   for _, r in ev.iterrows()],
    }
