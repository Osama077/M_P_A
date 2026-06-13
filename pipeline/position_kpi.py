"""pipeline/position_kpi.py — Position-specific KPI ratings (Phase 4.5-4.8)."""

import pandas as pd
import numpy as np
from pathlib import Path
from config import DATA_DIR


# ── 8-Position hierarchy ───────────────────────────────────────────────────────
GRANULAR_POSITIONS = [
    "Goalkeeper", "Center Back", "Full Back",
    "Defensive Midfielder", "Central Midfielder", "Attacking Midfielder",
    "Winger", "Striker",
]

POSITION_MAP = {
    "Goalkeeper": "Goalkeeper",
    "Right Back": "Full Back", "Left Back": "Full Back",
    "Right Wing Back": "Full Back", "Left Wing Back": "Full Back",
    "Center Back": "Center Back", "Right Center Back": "Center Back",
    "Left Center Back": "Center Back",
    "Center Defensive Midfield": "Defensive Midfielder",
    "Right Defensive Midfield": "Defensive Midfielder",
    "Left Defensive Midfield": "Defensive Midfielder",
    "Center Midfield": "Central Midfielder",
    "Right Midfield": "Central Midfielder", "Left Midfield": "Central Midfielder",
    "Right Center Midfield": "Central Midfielder", "Left Center Midfield": "Central Midfielder",
    "Center Attacking Midfield": "Attacking Midfielder",
    "Right Attacking Midfield": "Attacking Midfielder",
    "Left Attacking Midfield": "Attacking Midfielder",
    "Right Wing": "Winger", "Left Wing": "Winger",
    "Center Forward": "Striker", "Secondary Striker": "Striker",
    "Right Center Forward": "Striker", "Left Center Forward": "Striker",
}

COARSE_TO_GRANULAR = {"GK": "Goalkeeper", "Defender": "Center Back",
                       "Midfielder": "Central Midfielder", "Attacker": "Striker"}

# Features where lower values are better (percentile is inverted)
LOWER_IS_BETTER = {"goals_conceded_per90"}


# ── Percentile-based scoring ───────────────────────────────────────────────────
def _percentile_score(value, dist_series, invert=False):
    """Map a value to [0, 10] via its percentile rank (avg rank for ties).
    If invert=True, lower values score higher."""
    if pd.isna(value):
        return 5.0
    total = len(dist_series)
    if total == 0:
        return 5.0
    n_below = int((dist_series < value).sum())
    n_equal = int((dist_series == value).sum())
    avg_rank = n_below + 0.5 * n_equal
    pct = (avg_rank / total) * 100
    score = np.clip(pct / 10, 0.0, 10.0)
    return 10.0 - score if invert else score


# ── Hybrid weights per position (Phase 4.7) ────────────────────────────────────
# (feature_name, weight) — weights sum to 1.0 per position
KPI_WEIGHTS = {
    "Goalkeeper": [
        ("save_pct", 0.35), ("goals_prevented", 0.25),
        ("goals_conceded_per90", 0.15), ("pass_accuracy", 0.15),
        ("progressive_passes_per90", 0.10),
    ],
    "Center Back": [
        ("defensive_actions_per90", 0.30), ("pass_accuracy", 0.25),
        ("progressive_passes_per90", 0.15), ("progressive_carries_per90", 0.15),
        ("duels_total_per90", 0.10), ("pressure_regains_per90", 0.05),
    ],
    "Full Back": [
        ("progressive_carries_per90", 0.25), ("chances_created_per90", 0.20),
        ("defensive_actions_per90", 0.20), ("pass_accuracy", 0.15),
        ("successful_dribbles_per90", 0.10), ("progressive_passes_per90", 0.10),
    ],
    "Defensive Midfielder": [
        ("pressure_regains_per90", 0.25), ("pass_accuracy", 0.20),
        ("progressive_passes_per90", 0.20), ("defensive_actions_per90", 0.15),
        ("total_passes_per90", 0.10), ("ball_receipts_per90", 0.10),
    ],
    "Central Midfielder": [
        ("progressive_passes_per90", 0.20), ("pass_accuracy", 0.20),
        ("total_passes_per90", 0.15), ("pressure_regains_per90", 0.15),
        ("progressive_carries_per90", 0.15), ("chances_created_per90", 0.10),
        ("ball_receipts_per90", 0.05),
    ],
    "Attacking Midfielder": [
        ("chances_created_per90", 0.25), ("goals_per90", 0.20),
        ("progressive_passes_per90", 0.20), ("shot_accuracy", 0.15),
        ("successful_dribbles_per90", 0.10), ("progressive_carries_per90", 0.10),
    ],
    "Winger": [
        ("successful_dribbles_per90", 0.25), ("goals_per90", 0.20),
        ("chances_created_per90", 0.20), ("assists_per90", 0.15),
        ("progressive_carries_per90", 0.10), ("shot_accuracy", 0.10),
    ],
    "Striker": [
        ("goals_per90", 0.30), ("shot_accuracy", 0.20),
        ("assists_per90", 0.15), ("chances_created_per90", 0.10),
        ("successful_dribbles_per90", 0.10), ("xg_overperformance", 0.10),
        ("progressive_carries_per90", 0.05),
    ],
}

# Features needed for each position (for per-90 computation and scoring)
POSITION_FEATURES = {
    "Goalkeeper": ["save_pct", "goals_prevented", "goals_conceded_per90",
                   "pass_accuracy", "progressive_passes_per90"],
    "Center Back": ["defensive_actions_per90", "pass_accuracy",
                    "progressive_passes_per90", "progressive_carries_per90",
                    "duels_total_per90", "pressure_regains_per90"],
    "Full Back": ["progressive_carries_per90", "chances_created_per90",
                   "defensive_actions_per90", "pass_accuracy",
                   "successful_dribbles_per90", "progressive_passes_per90"],
    "Defensive Midfielder": ["pressure_regains_per90", "pass_accuracy",
                              "progressive_passes_per90", "defensive_actions_per90",
                              "total_passes_per90", "ball_receipts_per90"],
    "Central Midfielder": ["progressive_passes_per90", "pass_accuracy",
                            "total_passes_per90", "pressure_regains_per90",
                            "progressive_carries_per90", "chances_created_per90",
                            "ball_receipts_per90"],
    "Attacking Midfielder": ["chances_created_per90", "goals_per90",
                              "progressive_passes_per90", "shot_accuracy",
                              "successful_dribbles_per90", "progressive_carries_per90"],
    "Winger": ["successful_dribbles_per90", "goals_per90", "chances_created_per90",
                "assists_per90", "progressive_carries_per90", "shot_accuracy"],
    "Striker": ["goals_per90", "shot_accuracy", "assists_per90",
                 "chances_created_per90", "successful_dribbles_per90",
                 "xg_overperformance", "progressive_carries_per90"],
}

PER90_COLS = [
    "goals", "assists", "total_shots", "shots_on_target",
    "total_passes", "complete_passes", "total_pressures",
    "pressure_regains", "total_carries", "progressive_carries",
    "total_dribbles", "successful_dribbles", "interceptions",
    "clearances", "blocks", "duels_total", "ball_receipts",
    "saves", "shots_faced", "goals_conceded", "progressive_passes",
    "chances_created", "key_passes", "fouls_committed", "fouls_won",
    "miscontrols", "passes_under_pressure",
]

LABELS = [
    (9.0, "Exceptional"), (7.5, "Excellent"), (6.0, "Good"),
    (4.5, "Average"), (3.0, "Below Average"),
]


def _label(score):
    for threshold, name in LABELS:
        if score >= threshold:
            return name
    return "Poor"


def _clip(x):
    return max(0.0, min(10.0, x))


def build_distribution_cache(computed, lineups):
    """Pre-compute percentile distributions for each position x feature."""
    df = computed.merge(
        lineups[["match_id", "player_id", "position_granular"]],
        on=["match_id", "player_id"], how="left"
    )
    df["position_granular"] = df["position_granular"].fillna("Central Midfielder")

    # Per-90
    mp = df["minutes_played"].replace(0, np.nan)
    for c in PER90_COLS:
        if c in df.columns:
            df[c + "_per90"] = df[c] / (mp / 90)

    # Derived
    df["defensive_actions_per90"] = (
        df["interceptions_per90"].fillna(0)
        + df["clearances_per90"].fillna(0)
        + df["blocks_per90"].fillna(0)
    )

    cache = {}
    for pos in GRANULAR_POSITIONS:
        subset = df[df["position_granular"] == pos]
        features = [f for f in POSITION_FEATURES.get(pos, []) if f in subset.columns]
        cache[pos] = {feat: subset[feat].dropna() for feat in features}
    return cache


def compute_kpi_ratings(computed, lineups, dist_cache=None):
    """Compute position-specific KPI ratings for every player-match pair."""
    df = computed.copy()

    # Merge granular positions from lineups
    df = df.merge(
        lineups[["match_id", "player_id", "position_granular"]],
        on=["match_id", "player_id"], how="left"
    )
    df["position_granular"] = df["position_granular"].fillna("Central Midfielder")

    # Per-90
    mp = df["minutes_played"].replace(0, np.nan)
    for c in PER90_COLS:
        if c in df.columns:
            df[c + "_per90"] = df[c] / (mp / 90)

    # Derived
    df["defensive_actions_per90"] = (
        df["interceptions_per90"].fillna(0)
        + df["clearances_per90"].fillna(0)
        + df["blocks_per90"].fillna(0)
    )

    # Build cache if not provided
    if dist_cache is None:
        dist_cache = build_distribution_cache(computed, lineups)

    results = []
    for _, row in df.iterrows():
        pos = str(row.get("position_granular", "Central Midfielder"))
        if pos not in KPI_WEIGHTS:
            pos = "Central Midfielder"

        dims = {}
        weighted_sum = 0.0
        total_weight = 0.0
        missing_weight = 0.0

        for feat, weight in KPI_WEIGHTS[pos]:
            raw = row.get(feat, np.nan)
            dist = dist_cache.get(pos, {}).get(feat, pd.Series(dtype=float))
            invert = feat in LOWER_IS_BETTER
            s = _percentile_score(raw, dist, invert=invert) if len(dist) > 0 else 5.0
            dims[feat] = _clip(s)
            if not pd.isna(raw):
                weighted_sum += dims[feat] * weight
                total_weight += weight
            else:
                missing_weight += weight

        # Adjust for missing features
        if total_weight > 0:
            kpi_total = weighted_sum / total_weight
        else:
            kpi_total = 5.0

        # Minutes-played confidence
        mp_val = row.get("minutes_played", 90) or 0
        if mp_val < 15:
            kpi_total *= 0.5
            confidence = "low"
        elif mp_val < 30:
            kpi_total *= 0.75
            confidence = "medium"
        else:
            confidence = "high"

        kpi_total = _clip(kpi_total)

        results.append({
            "match_id": row["match_id"],
            "player_id": row["player_id"],
            "position_granular": pos,
            "position_kpi": round(kpi_total, 2),
            "position_kpi_label": _label(kpi_total),
            "confidence": confidence,
            "minutes_played": mp_val,
            **{f"kpi_{feat}": round(dims[feat], 2) for feat, _ in KPI_WEIGHTS[pos]},
        })

    return pd.DataFrame(results)


def run():
    """Pipeline step 7: compute KPI ratings with granular positions and save."""
    print("\n=== Step 7: Position KPI Ratings (Granular, Percentile-Based) ===")

    computed = pd.read_parquet(DATA_DIR / "computed_features.parquet")
    lineups = pd.read_parquet(DATA_DIR / "lineups.parquet")

    # Extract granular positions from lineups
    def _extract_granular(positions_arr):
        if positions_arr is None or (hasattr(positions_arr, 'size') and positions_arr.size == 0) or len(positions_arr) == 0:
            return "Unknown"
        pos = positions_arr[0]
        if isinstance(pos, dict):
            raw = pos.get("position", "Unknown")
            return POSITION_MAP.get(raw, "Unknown")
        return "Unknown"

    lineups["position_granular"] = lineups["positions"].apply(_extract_granular)

    ratings = compute_kpi_ratings(computed, lineups)
    ratings.to_parquet(DATA_DIR / "position_kpi.parquet", index=False)

    print(f"  KPI ratings computed: {len(ratings)} player-matches")
    dist = ratings["position_kpi_label"].value_counts()
    for label_name in ["Exceptional", "Excellent", "Good", "Average", "Below Average", "Poor"]:
        cnt = dist.get(label_name, 0)
        print(f"    {label_name}: {cnt} ({cnt/len(ratings)*100:.1f}%)" if len(ratings) > 0 else f"    {label_name}: 0")

    pos_dist = ratings["position_granular"].value_counts()
    print("\n  Per position:")
    for pos in GRANULAR_POSITIONS:
        cnt = pos_dist.get(pos, 0)
        print(f"    {pos:30s}: {cnt}")

    print(f"  Saved -> data/position_kpi.parquet")


if __name__ == "__main__":
    run()
