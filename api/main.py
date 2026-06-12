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
    return {
        "status":  "running",
        "api":     "Match Performance Analysis API",
        "version": "1.0.0",
        "docs":    "/docs",
    }


@app.get("/api/v1/")
def api_v1_health():
    return {
        "status": "running",
        "api": "Match Performance Analysis API",
        "version": "v1",
    }
