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
TARGET_TEAM = "Barcelona"

# Multi-season support: (competition_id, season_id, label)
# La Liga = competition 11, Champions League = 16, Copa del Rey = 87
SEASONS_LIST = [
    (11, 22, "2010/2011"), (11, 23, "2011/2012"),
    (11, 24, "2012/2013"), (11, 25, "2013/2014"),
    (11, 26, "2014/2015"), (11, 27, "2015/2016"),
    (11,  2, "2016/2017"), (11,  4, "2017/2018"),
    (11, 42, "2018/2019"), (11, 90, "2019/2020"),
    (11,  1, "2020/2021"),
]

# Default season for backward compatibility (originally 2015/2016)
COMPETITION_ID = 11
SEASON_ID      = 27

# Season label to season_id lookup
SEASON_LABEL_MAP = {label: sid for _, sid, label in SEASONS_LIST}
SEASON_ID_MAP    = {sid: label for _, sid, label in SEASONS_LIST}

# ── VAEP ───────────────────────────────────────────────────────────────────────
VAEP_WINDOW    = 10    # عدد الـ actions للتنبؤ
VAEP_N_CONTEXT = 3     # عدد الـ actions السابقة

# ── Scoring ────────────────────────────────────────────────────────────────────
# Legacy dimension weights (for backward compatibility)
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

# ── V2 Scoring: 4-Pillar Contribution Model ──
# Position weights for the four contribution sub-scores
CONTRIBUTION_WEIGHTS = {
    "Attacker":   {"offensive": 0.50, "defensive": 0.05, "possession": 0.20, "event_value": 0.25},
    "Midfielder": {"offensive": 0.25, "defensive": 0.15, "possession": 0.35, "event_value": 0.25},
    "Defender":   {"offensive": 0.10, "defensive": 0.40, "possession": 0.25, "event_value": 0.25},
    "GK":         {"offensive": 0.02, "defensive": 0.50, "possession": 0.23, "event_value": 0.25},
}

# Feature-level weights within each contribution pillar (per position)
# Each key maps to (feature_name, weight) pairs
OFFENSIVE_FEATURES = {
    "Attacker":   {"total_shots": 0.15, "predicted_xg": 0.25, "shot_accuracy": 0.10, "goals": 0.20, "xg_overperformance": 0.10, "progressive_passes": 0.05, "progressive_carries": 0.05, "successful_dribbles": 0.05, "total_carries": 0.05},
    "Midfielder": {"total_shots": 0.10, "predicted_xg": 0.10, "shot_accuracy": 0.05, "goals": 0.05, "xg_overperformance": 0.05, "progressive_passes": 0.25, "progressive_carries": 0.15, "successful_dribbles": 0.10, "total_carries": 0.10, "passes_under_pressure": 0.05},
    "Defender":   {"total_shots": 0.05, "predicted_xg": 0.05, "goals": 0.05, "progressive_passes": 0.30, "progressive_carries": 0.30, "successful_dribbles": 0.10, "total_carries": 0.15},
    "GK":         {"total_shots": 0.00, "goals": 0.00, "progressive_passes": 0.50, "total_carries": 0.50},
}

DEFENSIVE_FEATURES = {
    "Attacker":   {"total_pressures": 0.40, "pressure_regains": 0.30, "pressing_efficiency": 0.20, "fouls_won": 0.10},
    "Midfielder": {"total_pressures": 0.30, "pressure_regains": 0.25, "pressing_efficiency": 0.15, "fouls_committed": -0.10, "fouls_won": 0.10, "yellow_cards": -0.05, "red_cards": -0.10},
    "Defender":   {"total_pressures": 0.25, "pressure_regains": 0.20, "pressing_efficiency": 0.10, "fouls_committed": -0.10, "fouls_won": 0.15, "yellow_cards": -0.10, "red_cards": -0.15, "miscontrols": -0.05},
    "GK":         {"total_pressures": 0.10, "pressure_regains": 0.10, "fouls_committed": -0.10, "yellow_cards": -0.05, "red_cards": -0.20, "miscontrols": -0.10},
}

POSSESSION_FEATURES = {
    "Attacker":   {"pass_accuracy": 0.25, "total_passes": 0.10, "ball_retention_rate": 0.20, "ball_receipts": 0.15, "miscontrols": -0.10, "progressive_passes": 0.10, "passes_under_pressure": 0.10},
    "Midfielder": {"pass_accuracy": 0.20, "total_passes": 0.20, "ball_retention_rate": 0.15, "ball_receipts": 0.15, "miscontrols": -0.10, "progressive_passes": 0.10, "passes_under_pressure": 0.10},
    "Defender":   {"pass_accuracy": 0.25, "total_passes": 0.15, "ball_retention_rate": 0.20, "ball_receipts": 0.10, "miscontrols": -0.10, "progressive_passes": 0.10, "passes_under_pressure": 0.10},
    "GK":         {"pass_accuracy": 0.30, "total_passes": 0.15, "ball_retention_rate": 0.25, "ball_receipts": 0.10, "miscontrols": -0.10, "progressive_passes": 0.10},
}

# Rating scale labels
RATING_LABELS = {
    (9.0, 10.0): "Exceptional",
    (8.0, 9.0):  "Excellent",
    (7.0, 8.0):  "Very Good",
    (6.0, 7.0):  "Good",
    (5.0, 6.0):  "Average",
    (0.0, 5.0):  "Below Average",
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

# Granular position mapping (8 roles) — Phase 4.5
GRANULAR_POSITION_MAP = {
    "Goalkeeper":            "Goalkeeper",
    "Right Back":            "Full Back",
    "Left Back":             "Full Back",
    "Center Back":           "Center Back",
    "Right Center Back":     "Center Back",
    "Left Center Back":      "Center Back",
    "Right Wing Back":       "Full Back",
    "Left Wing Back":        "Full Back",
    "Defensive Midfield":    "Defensive Midfielder",
    "Center Midfield":       "Central Midfielder",
    "Right Center Midfield": "Central Midfielder",
    "Left Center Midfield":  "Central Midfielder",
    "Attacking Midfield":    "Attacking Midfielder",
    "Right Midfield":        "Winger",
    "Left Midfield":         "Winger",
    "Right Wing":            "Winger",
    "Left Wing":             "Winger",
    "Right Center Forward":  "Striker",
    "Left Center Forward":   "Striker",
    "Center Forward":        "Striker",
    "Secondary Striker":     "Attacking Midfielder",
}

GRANULAR_POSITION_LABELS = {
    "Goalkeeper": "GK", "Center Back": "CB", "Full Back": "FB",
    "Defensive Midfielder": "DMF", "Central Midfielder": "CMF",
    "Attacking Midfielder": "AMF", "Winger": "WG", "Striker": "ST",
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
