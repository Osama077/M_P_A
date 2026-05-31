"""api/routes/match.py"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from api.routes._shared import _load_data, _sf, _si, _to_records

router = APIRouter()

@router.get("/match/{match_id}/report")
def match_report(match_id: int):
    d  = _load_data()
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
                 limit: int = Query(100), offset: int = Query(0)):
    d  = _load_data()
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
