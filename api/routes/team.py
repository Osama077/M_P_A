"""api/routes/team.py"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from api.routes._shared import _load_data, _sf, _si, _to_records

router = APIRouter()

@router.get("/team/{team_id}/summary")
def team_summary(team_id: str, match_id: Optional[int] = Query(None)):
    d = _load_data()
    sc = d["scores"]
    mask = sc["team_name"].astype(str).str.contains(str(team_id), case=False, na=False) if "team_name" in sc.columns \
           else sc["team"].astype(str).str.contains(str(team_id), case=False, na=False)
    ts = sc[mask & (sc["match_id"] == match_id)] if match_id else sc[mask]
    if not len(ts): raise HTTPException(404, f"Team {team_id} not found")

    top = ts.loc[ts["overall_score"].idxmax()]
    tf  = d["computed"][d["computed"]["player_id"].isin(ts["player_id"].unique())]
    if match_id: tf = tf[tf["match_id"] == match_id]

    return {
        "team_id": str(team_id), "match_id": match_id,
        "team_stats": {
            "avg_overall_score": _sf(ts["overall_score"].mean()),
            "total_xg":          _sf(tf["total_xg"].sum()) if "total_xg" in tf.columns else None,
            "pass_accuracy":     _sf(tf["pass_accuracy"].mean()) if "pass_accuracy" in tf.columns else None,
            "total_pressures":   _si(tf["total_pressures"].sum()) if "total_pressures" in tf.columns else 0,
        },
        "top_performer": {"player_id":_si(top["player_id"]),"player_name":str(top["player_name"]),
                           "overall_score":_sf(top["overall_score"])},
        "players": _to_records(ts[["player_id","player_name","overall_score",
                                    "position_group","performance_trend"]
                                   if all(c in ts.columns for c in ["position_group","performance_trend"])
                                   else ["player_id","player_name","overall_score"]]
                                .sort_values("overall_score", ascending=False)),
    }


@router.get("/team/{team_id}/heatmap")
def team_heatmap(team_id: str, match_id: int = Query(...), player_id: Optional[int] = Query(None)):
    d = _load_data()
    ev = d["events"][(d["events"]["match_id"] == match_id) & d["events"]["location_x"].notna()]
    if player_id:
        ev = ev[ev["player_id"] == player_id]
    else:
        col = "team_name" if "team_name" in ev.columns else "team"
        ev  = ev[ev[col].astype(str).str.contains(str(team_id), case=False, na=False)]
    if not len(ev): raise HTTPException(404, "No events found")
    if len(ev) > 500: ev = ev.sample(500, random_state=42)
    return {"match_id":match_id,"player_id":player_id,"total_points":len(ev),
            "heatmap_data":[{"x":_sf(r["location_x"]),"y":_sf(r["location_y"]),
                              "event_type":str(r["event_type"])} for _,r in ev.iterrows()]}
