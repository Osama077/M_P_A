"""
api/main.py — FastAPI Application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import player, team, match, benchmark, analysis, advanced_analysis, squad, player_profile, metadata, coaching, position_kpi_routes

app = FastAPI(
    title       ="Match Performance Analysis API",
    description ="Sports Performance Management Platform — ML API",
    version     ="1.0.0",
    docs_url    ="/docs",
    redoc_url   ="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     =["*"],
    allow_credentials =True,
    allow_methods     =["*"],
    allow_headers     =["*"],
)

# Register routes
app.include_router(analysis.router,        prefix="/api/v1", tags=["Analysis"])
app.include_router(player.router,          prefix="/api/v1", tags=["Player"])
app.include_router(team.router,            prefix="/api/v1", tags=["Team"])
app.include_router(match.router,           prefix="/api/v1", tags=["Match"])
app.include_router(benchmark.router,       prefix="/api/v1", tags=["Benchmark"])
app.include_router(advanced_analysis.router, prefix="/api/v1", tags=["Advanced Analysis"])
app.include_router(squad.router,           prefix="/api/v1", tags=["Squad"])
app.include_router(player_profile.router,  prefix="/api/v1", tags=["Player Profile"])
app.include_router(metadata.router,         prefix="/api/v1", tags=["Metadata"])
app.include_router(coaching.router,         prefix="/api/v1", tags=["Coaching"])
app.include_router(position_kpi_routes.router, prefix="/api/v1", tags=["Position KPI"])


@app.get("/")
def health_check():
    from pathlib import Path
    from config import DATA_DIR
    required_files = ["events_clean.parquet", "computed_features.parquet", "model_scores.parquet", "matches.parquet"]
    missing = [f for f in required_files if not (DATA_DIR / f).exists()]
    status = "degraded" if missing else "running"
    return {
        "status":  status,
        "api":     "Match Performance Analysis API",
        "version": "1.0.0",
        "docs":    "/docs",
        "data_files_ok": len(missing) == 0,
        "missing_files": missing if missing else None,
    }


@app.get("/api/v1/")
def api_v1_health():
    return {
        "status": "running",
        "api": "Match Performance Analysis API",
        "version": "v1",
    }
