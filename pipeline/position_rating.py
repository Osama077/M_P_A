"""
pipeline/position_rating.py — Position-Aware Player Rating Engine

Architecture:
  All players start at 5.0. Rating changes are driven by position-specific
  dimension metrics (success rates, per-90 rates) with confidence-based
  adjustment for low-volume samples. Final scores are comparable across
  positions via calibrated baseline+range parameters per dimension.

  Note: Position_group values in the data use the full names:
        ('GK','Defender','Midfielder','Attacker') — NOT the short codes.
"""

import numpy as np
import pandas as pd
from config import DATA_DIR
from utils.helpers import ensure_dirs


# ── Dimension definitions ─────────────────────────────────────────────────────
# Each position has 3-4 dimensions. Each dimension defines:
#   metric_fn : callable(row) -> rate value
#   baseline  : population mean rate
#   range_    : distance from baseline to ≈95th percentile (drives 5.0→10.0)
#   min_samp  : minimum attempts for full confidence
#   weight    : contribution weight within position (sums to 1.0 per position)

DIMENSIONS = {

    "GK": [
        {
            "name": "Shot Stopping",
            "weight": 0.40,
            "metric_fn": lambda r: r.get("save_pct", 0) / 100.0,
            "attempts_fn": lambda r: r.get("shots_faced", 0),
            "baseline": 0.70,
            "range_": 0.15,
            "min_samp": 3,
        },
        {
            "name": "Distribution",
            "weight": 0.25,
            "metric_fn": lambda r: r.get("pass_accuracy", 75) / 100.0,
            "attempts_fn": lambda r: r.get("total_passes", 0),
            "baseline": 0.75,
            "range_": 0.12,
            "min_samp": 10,
        },
        {
            "name": "Match Impact",
            "weight": 0.20,
            "metric_fn": lambda r: min(max(r.get("goals_prevented", 0) / 1.5, -1.0), 1.0),
            "attempts_fn": lambda r: 5 if r.get("shots_faced", 0) > 0 else 0,
            "baseline": 0.0,
            "range_": 1.0,
            "min_samp": 1,
        },
        {
            "name": "Command",
            "weight": 0.15,
            "metric_fn": lambda r: min(r.get("interceptions", 0) / max(r.get("shots_faced", 1), 1), 1.0),
            "attempts_fn": lambda r: r.get("shots_faced", 0) + r.get("interceptions", 0),
            "baseline": 0.10,
            "range_": 0.10,
            "min_samp": 2,
        },
    ],

    "Defender": [
        {
            "name": "Defensive Solidity",
            "weight": 0.35,
            "metric_fn": lambda r: min(
                (r.get("pressure_regains", 0) + r.get("interceptions", 0)) /
                max(r.get("total_pressures", 1) + r.get("interceptions", 0) + r.get("clearances", 0) + r.get("blocks", 0), 1),
                1.0
            ),
            "attempts_fn": lambda r: r.get("total_pressures", 0) + r.get("interceptions", 0) + r.get("clearances", 0) + r.get("blocks", 0),
            "baseline": 0.25,
            "range_": 0.15,
            "min_samp": 5,
        },
        {
            "name": "Build-up Play",
            "weight": 0.25,
            "metric_fn": lambda r: (
                r.get("pass_accuracy", 75) / 100.0 * 0.70 +
                min(r.get("progressive_passes", 0) / max(r.get("total_passes", 1), 1), 0.30)
            ),
            "attempts_fn": lambda r: r.get("total_passes", 0),
            "baseline": 0.60,
            "range_": 0.15,
            "min_samp": 15,
        },
        {
            "name": "Defensive Awareness",
            "weight": 0.25,
            "metric_fn": lambda r: min(
                (r.get("interceptions", 0) + r.get("blocks", 0) + r.get("clearances", 0)) /
                max(r.get("total_pressures", 1) + r.get("interceptions", 1) + r.get("clearances", 1) + r.get("blocks", 1), 1),
                1.0
            ),
            "attempts_fn": lambda r: r.get("total_pressures", 0) + r.get("interceptions", 0) + r.get("clearances", 0) + r.get("blocks", 0),
            "baseline": 0.20,
            "range_": 0.12,
            "min_samp": 4,
        },
        {
            "name": "Aerial & Duels",
            "weight": 0.15,
            "metric_fn": lambda r: min(
                r.get("duels_total", 0) / max(r.get("duels_total", 1) + r.get("miscontrols", 0), 1),
                1.0
            ),
            "attempts_fn": lambda r: r.get("duels_total", 0) + r.get("miscontrols", 0),
            "baseline": 0.30,
            "range_": 0.15,
            "min_samp": 3,
        },
    ],

    "Midfielder": [
        {
            "name": "Passing & Creativity",
            "weight": 0.30,
            "metric_fn": lambda r: (
                r.get("pass_accuracy", 75) / 100.0 * 0.60 +
                min(r.get("progressive_passes", 0) / max(r.get("total_passes", 1), 1), 0.20)
            ),
            "attempts_fn": lambda r: r.get("total_passes", 0),
            "baseline": 0.65,
            "range_": 0.12,
            "min_samp": 20,
        },
        {
            "name": "Possession Retention",
            "weight": 0.25,
            "metric_fn": lambda r: r.get("ball_retention_rate", 85) / 100.0,
            "attempts_fn": lambda r: r.get("ball_receipts", 0),
            "baseline": 0.85,
            "range_": 0.10,
            "min_samp": 10,
        },
        {
            "name": "Defensive Work Rate",
            "weight": 0.20,
            "metric_fn": lambda r: min(
                r.get("pressure_regains", 0) / max(r.get("total_pressures", 1), 1),
                1.0
            ),
            "attempts_fn": lambda r: r.get("total_pressures", 0),
            "baseline": 0.20,
            "range_": 0.12,
            "min_samp": 5,
        },
        {
            "name": "Attacking Contribution",
            "weight": 0.25,
            "metric_fn": lambda r: min(
                (r.get("total_shots", 0) + r.get("key_passes", 0) + r.get("progressive_passes", 0)) /
                max(r.get("minutes_played", 90), 1) * 90 / 12.0,
                1.0
            ),
            "attempts_fn": lambda r: r.get("total_shots", 0) + r.get("key_passes", 0) + r.get("progressive_passes", 0),
            "baseline": 0.12,  # 1.5 / 12 actions per 90
            "range_": 0.20,    # 3.0 / 15 per 90
            "min_samp": 3,
        },
    ],

    "Attacker": [
        {
            "name": "Finishing",
            "weight": 0.30,
            "metric_fn": lambda r: min(max(
                r.get("xg_overperformance", 0) / max(r.get("total_shots", 1), 1) * 5 + 0.5,
                0.0
            ), 1.0),
            "attempts_fn": lambda r: r.get("total_shots", 0),
            "baseline": 0.50,
            "range_": 0.20,
            "min_samp": 2,
        },
        {
            "name": "Creation",
            "weight": 0.25,
            "metric_fn": lambda r: min(
                (r.get("key_passes", 0) + r.get("chances_created", 0) + r.get("assists", 0)) /
                max(r.get("minutes_played", 90), 1) * 90 / 8.0,
                1.0
            ),
            "attempts_fn": lambda r: r.get("key_passes", 0) + r.get("chances_created", 0) + r.get("assists", 0),
            "baseline": 0.12,  # 1.0 / 8 per 90
            "range_": 0.25,    # 3.0 / 12 per 90
            "min_samp": 1,
        },
        {
            "name": "Dribbling & 1v1",
            "weight": 0.20,
            "metric_fn": lambda r: r.get("dribble_success_rate", 50) / 100.0,
            "attempts_fn": lambda r: r.get("total_dribbles", 0),
            "baseline": 0.55,
            "range_": 0.20,
            "min_samp": 3,
        },
        {
            "name": "Offensive Pressure",
            "weight": 0.25,
            "metric_fn": lambda r: min(
                r.get("total_pressures", 0) / max(r.get("minutes_played", 90), 1) * 90 / 15.0,
                1.0
            ),
            "attempts_fn": lambda r: r.get("total_pressures", 0),
            "baseline": 0.15,  # 2.0 / 13 per 90
            "range_": 0.20,    # 5.0 / 25 per 90
            "min_samp": 3,
        },
    ],
}

# Post-processing penalties
PENALTIES = {
    "red_card": -1.5,
    "own_goal": -1.0,
    "yellow_card_over_1": -0.3,
    "yellow_card_1": -0.1,
}

RATING_LABELS = [
    (9.0, 10.0, "Exceptional"),
    (8.0, 9.0, "Excellent"),
    (7.0, 8.0, "Very Good"),
    (6.0, 7.0, "Good"),
    (5.0, 6.0, "Average"),
    (0.0, 5.0, "Below Average"),
]


def _clamp(v, lo=0.0, hi=10.0):
    return max(lo, min(hi, v))


def _compute_dimension_score(row: pd.Series, dim: dict) -> float:
    rate = dim["metric_fn"](row)
    attempts = dim["attempts_fn"](row)

    raw = 5.0 + (rate - dim["baseline"]) / max(dim["range_"], 0.01) * 5.0
    raw = _clamp(raw, 0.0, 10.0)

    confidence = min(attempts / max(dim["min_samp"], 1), 1.0)
    return 5.0 + (raw - 5.0) * confidence


def compute_position_rating(row: pd.Series, position: str) -> dict:
    dims = DIMENSIONS.get(position, [])
    if not dims:
        return {"raw_score": 5.0, "position_rating": 5.0, "dimension_scores": {}}

    dim_scores = {}
    total_weight = 0.0
    for dim in dims:
        score = _compute_dimension_score(row, dim)
        dim_scores[dim["name"]] = score
        total_weight += dim["weight"]

    base = 5.0
    if total_weight > 0:
        weighted_sum = sum(dim_scores[d["name"]] * d["weight"] for d in dims)
        base = weighted_sum / total_weight

    # Apply penalties
    if row.get("red_card", 0) >= 1:
        base += PENALTIES["red_card"]
    if row.get("own_goal", 0) > 0:
        base += PENALTIES["own_goal"]

    final = _clamp(base)

    dl = {d["name"]: round(dim_scores.get(d["name"], 5.0), 2) for d in dims}
    return {"position_rating": round(final, 2), "dimension_scores": dl}


def rating_label(score: float) -> str:
    for lo, hi, label in RATING_LABELS:
        if lo <= score < hi:
            return label
    return "Below Average" if score < 5.0 else "Exceptional"


def run():
    print("=" * 60)
    print("⚙️  PIPELINE STEP 7: Position-Aware Rating Engine")
    print("=" * 60)

    computed = pd.read_parquet(DATA_DIR / "computed_features.parquet")
    scores = pd.read_parquet(DATA_DIR / "model_scores.parquet")

    # Merge position_group from scores if not in computed
    if "position_group" not in computed.columns or computed["position_group"].isna().all():
        computed = computed.merge(
            scores[["match_id", "player_id", "position_group"]],
            on=["match_id", "player_id"], how="left", suffixes=("", "_sc")
        )
        pg = computed.get("position_group", None)
        if pg is not None and pg.isna().any():
            computed["position_group"] = computed.get("position_group_sc", computed.get("position_group"))

    results = []
    for _, row in computed.iterrows():
        pos = str(row.get("position_group", "Midfielder"))
        # Map short codes used in some data
        if pos in ("GK", "DF", "MF", "FW"):
            pos_map = {"GK": "GK", "DF": "Defender", "MF": "Midfielder", "FW": "Attacker"}
            pos = pos_map.get(pos, "Midfielder")
        # Accept both full and short names
        if pos == "Attacker" or pos == "FW":
            pos = "Attacker"
        elif pos == "Midfielder" or pos == "MF":
            pos = "Midfielder"
        elif pos == "Defender" or pos == "DF":
            pos = "Defender"
        elif pos == "GK":
            pos = "GK"

        result = compute_position_rating(row, pos)
        dim_scores = result["dimension_scores"]
        results.append({
            "match_id": row["match_id"],
            "player_id": row["player_id"],
            "position_group": pos,
            "position_rating": result["position_rating"],
            "rating_label": rating_label(result["position_rating"]),
            **{f"pos_dim_{k.lower().replace(' ','_').replace('&','and')}": v
               for k, v in dim_scores.items()},
        })

    pos_ratings = pd.DataFrame(results)

    out_path = DATA_DIR / "position_ratings.parquet"
    pos_ratings.to_parquet(out_path, index=False)

    print(f"   Player-match ratings: {len(pos_ratings):,}")
    print(f"   Rating distribution:")
    for lo, hi, label in RATING_LABELS:
        c = ((pos_ratings["position_rating"] >= lo) & (pos_ratings["position_rating"] < hi)).sum()
        print(f"      {label:20s}: {c}")

    top5 = pos_ratings.groupby("player_id")["position_rating"].mean().sort_values(ascending=False).head(5)
    print(f"\n   Top 5 players by avg position rating:")
    print(f"   {top5.round(2).to_string()}")

    print(f"\n✅ Step 7 Complete!")
    print(f"   Saved to {out_path}")
    return pos_ratings


if __name__ == "__main__":
    run()
