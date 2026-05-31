"""
config.py — Project Configuration
Match Performance Analysis — Sports Performance Management Platform
"""

import os
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
DATA_DIR   = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"

# ── StatsBomb ──────────────────────────────────────────────────────────────────
COMPETITION_ID = 11    # La Liga
SEASON_ID      = 27    # 2015/16
TARGET_TEAM    = "Barcelona"

# ── VAEP ───────────────────────────────────────────────────────────────────────
VAEP_WINDOW    = 10    # عدد الـ actions للتنبؤ
VAEP_N_CONTEXT = 3     # عدد الـ actions السابقة

# ── Scoring ────────────────────────────────────────────────────────────────────
POSITION_WEIGHTS = {
    "Attacker": {
        "passing_score":     0.15,
        "shooting_score":    0.30,
        "positioning_score": 0.20,
        "pressing_score":    0.10,
        "movement_score":    0.10,
        "physical_score":    0.08,
        "behavioral_score":  0.07,
    },
    "Midfielder": {
        "passing_score":     0.28,
        "shooting_score":    0.12,
        "positioning_score": 0.18,
        "pressing_score":    0.18,
        "movement_score":    0.12,
        "physical_score":    0.07,
        "behavioral_score":  0.05,
    },
    "Defender": {
        "passing_score":     0.18,
        "shooting_score":    0.05,
        "positioning_score": 0.25,
        "pressing_score":    0.22,
        "movement_score":    0.10,
        "physical_score":    0.12,
        "behavioral_score":  0.08,
    },
    "GK": {
        "passing_score":     0.20,
        "shooting_score":    0.02,
        "positioning_score": 0.30,
        "pressing_score":    0.15,
        "movement_score":    0.08,
        "physical_score":    0.15,
        "behavioral_score":  0.10,
    },
}

POSITION_MAP = {
    "Goalkeeper":            "GK",
    "Right Back":            "Defender",
    "Left Back":             "Defender",
    "Center Back":           "Defender",
    "Right Center Back":     "Defender",
    "Left Center Back":      "Defender",
    "Right Wing Back":       "Defender",
    "Left Wing Back":        "Defender",
    "Defensive Midfield":    "Midfielder",
    "Center Midfield":       "Midfielder",
    "Right Center Midfield": "Midfielder",
    "Left Center Midfield":  "Midfielder",
    "Attacking Midfield":    "Midfielder",
    "Right Midfield":        "Midfielder",
    "Left Midfield":         "Midfielder",
    "Right Wing":            "Attacker",
    "Left Wing":             "Attacker",
    "Right Center Forward":  "Attacker",
    "Left Center Forward":   "Attacker",
    "Center Forward":        "Attacker",
    "Secondary Striker":     "Attacker",
}

ACTION_TYPE_MAP = {
    "Pass":           "pass",
    "Shot":           "shot",
    "Dribble":        "dribble",
    "Carry":          "carry",
    "Pressure":       "tackle",
    "Foul Committed": "foul",
    "Clearance":      "clearance",
    "Interception":   "interception",
    "Block":          "shot_block",
    "Goal Keeper":    "keeper_save",
    "Ball Receipt*":  "receival",
    "Miscontrol":     "bad_touch",
}

CLUSTER_NAMES = {
    0: "Creative Playmaker",
    1: "Box-to-Box Midfielder",
    2: "Target Forward",
    3: "Ball-Playing Defender",
    4: "Pressing Machine",
}

# ── API ────────────────────────────────────────────────────────────────────────
API_HOST    = "0.0.0.0"
API_PORT    = 8000
API_VERSION = "v1"
API_PREFIX  = f"/api/{API_VERSION}"

# ── Colors (for visualizations) ───────────────────────────────────────────────
VIZ_COLORS = {
    "primary":    "#1F4E79",
    "secondary":  "#2E75B6",
    "accent":     "#E67E22",
    "success":    "#27AE60",
    "danger":     "#C0392B",
    "pitch_dark": "#22312b",
    "pitch_light": "grass",
}
