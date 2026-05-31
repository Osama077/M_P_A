"""
api/schemas.py — Pydantic Models
"""
from pydantic import BaseModel
from typing import Optional

class AnalyzeMatchRequest(BaseModel):
    force_rerun: bool = False

class AnalyzeSeasonRequest(BaseModel):
    competition_id: int
    season_id: int
