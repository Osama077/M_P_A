"""api/routes/analysis.py"""
from fastapi import APIRouter, Query
from typing import Optional
from api.routes._shared import _load
from api.schemas import AnalyzeMatchRequest, AnalyzeSeasonRequest

router = APIRouter()

@router.post("/analyze/match/{match_id}")
def analyze_match(match_id: int, season: Optional[str] = Query(None), req: AnalyzeMatchRequest = AnalyzeMatchRequest()):
    d = _load(season=season)
    if not len(d["matches"][d["matches"]["match_id"] == match_id]):
        from fastapi import HTTPException
        raise HTTPException(404, f"Match {match_id} not found")
    existing = d["scores"][d["scores"]["match_id"] == match_id]
    if len(existing) and not req.force_rerun:
        return {"status":"already_analyzed","match_id":match_id,"players_analyzed":len(existing)}
    return {"status":"success","match_id":match_id,"players_analyzed":len(existing)}

@router.post("/analyze/season")
def analyze_season(req: AnalyzeSeasonRequest, season: Optional[str] = Query(None)):
    d = _load(season=season)
    return {"status":"success","competition_id":req.competition_id,"season_id":req.season_id,
            "matches_analyzed":len(d["matches"]),"total_players":d["scores"]["player_id"].nunique()}
