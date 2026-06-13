"""
pipeline/scoring_model.py — V2 Professional Player Match Rating System

Architecture:
  1. Event Value Model (simplified OBV / expected threat style)
  2. Four Contribution Sub-Scores (z-score normalized within position)
     - Offensive Contribution  (shooting, chance creation, progression)
     - Defensive Contribution  (ball recovery, duels, prevention)
     - Possession Contribution (retention, build-up, tempo)
     - Event Value Score       (aggregated per-match from event values)
  3. Position-specific weighting of sub-scores
  4. Final Rating (0–10) with playing-time & match-context adjustments
  5. Percentiles, trends, clustering (carried forward)
"""

import json
import pickle
import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

from config import (
    DATA_DIR, MODELS_DIR, POSITION_WEIGHTS, POSITION_MAP, CLUSTER_NAMES,
    CONTRIBUTION_WEIGHTS, OFFENSIVE_FEATURES, DEFENSIVE_FEATURES,
    POSSESSION_FEATURES, RATING_LABELS,
)
from utils.uuid_manager import add_uuid_column
from utils.helpers import normalize_to_score, ensure_dirs

SCORE_COLS = [
    "passing_score","shooting_score","positioning_score","pressing_score",
    "movement_score","physical_score","behavioral_score"
]

PITCH_LENGTH = 120.0
PITCH_WIDTH  = 80.0
PITCH_M_LENGTH = 105.0
PITCH_M_WIDTH  = 68.0


# ═══════════════════════════════════════════════════════════════════════════════
# 1.  EVENT VALUE MODEL  (simplified OBV / expected threat)
# ═══════════════════════════════════════════════════════════════════════════════

def _pitch_to_zone(x, y, nx=12, ny=8):
    """Map pitch coordinates (120x80) to zone indices."""
    x = np.nan_to_num(x, nan=PITCH_LENGTH / 2)
    y = np.nan_to_num(y, nan=PITCH_WIDTH  / 2)
    zi = np.clip(np.floor(x / PITCH_LENGTH * nx).astype(int), 0, nx - 1)
    zj = np.clip(np.floor(y / PITCH_WIDTH  * ny).astype(int), 0, ny - 1)
    return zi, zj


def build_xT_grid(events: pd.DataFrame, nx: int = 12, ny: int = 8,
                  min_actions: int = 50) -> np.ndarray:
    """Build expected threat grid from event sequences.
    
    For each possession, track location transitions and whether they
    eventually lead to a shot.  xT(zone) = P(shot eventually | zone).
    """
    grid = np.zeros((nx, ny))
    count = np.zeros((nx, ny))
    
    if "possession" not in events.columns:
        return grid
    
    for poss_id, group in events.groupby("possession"):
        group = group.sort_values("event_index")
        coords = group[["location_x", "location_y"]].values
        if len(coords) < 2:
            continue
        zi, zj = _pitch_to_zone(coords[:, 0], coords[:, 1], nx, ny)
        zones = np.stack([zi, zj], axis=1)
        shots = (group["event_type"] == "Shot").values
        # For each event, check if a shot occurs later in this possession
        for i in range(len(zones)):
            zi, zj = zones[i]
            if 0 <= zi < nx and 0 <= zj < ny:
                count[zi, zj] += 1
                if shots[i:].any():
                    grid[zi, zj] += 1
    
    # Normalise: xT(z) = shots_from_z / total_actions_from_z
    with np.errstate(divide="ignore", invalid="ignore"):
        xT = np.divide(grid, count, where=count >= min_actions)
        xT = np.nan_to_num(xT, nan=0.0)
    return xT


def compute_event_values(events: pd.DataFrame,
                         shots_with_xg: pd.DataFrame = None,
                         xT: np.ndarray = None) -> pd.DataFrame:
    """Assign OBV-style value to every event.
    
    Returns DataFrame with per-event columns:
      - event_value: net contribution (+ = offensive gain, - = defensive error)
      - offensive_value: positive contributions (shots, key passes, progressive)
      - defensive_value: positive contributions (interceptions, clearances)
    """
    if xT is None:
        xT = build_xT_grid(events)
    
    ev = events.copy()
    nx, ny = xT.shape
    
    # Zone indices for each event's start location
    zi, zj = _pitch_to_zone(
        ev["location_x"].values, ev["location_y"].values, nx, ny
    )
    start_xT = xT[zi, zj]
    
    # For events with end location, compute end_xT
    end_xT = np.zeros(len(ev))
    for c in ["carry_end_x", "pass_end_x"]:
        if c in ev.columns:
            ok = ev[c].notna()
            ezi, ezj = _pitch_to_zone(
                ev.loc[ok, c].values,
                ev.loc[ok, "carry_end_y" if "carry" in c else "pass_end_y"].values,
                nx, ny
            )
            end_xT[ok.values] = xT[ezi, ezj]
    
    # Baseline xT value of each event (location -> location delta)
    ev["xT_delta"] = end_xT - start_xT
    
    # ── Assign event values based on type ──
    conditions = {
        "Shot": lambda r: r.get("shot_xg", 0) if r.get("shot_xg", 0) > 0
                          else r.get("predicted_xg", 0.02),
        "Goal": lambda r: 1.0,
        "Pass":  lambda r: r["xT_delta"],
        "Carry": lambda r: r["xT_delta"] * 0.5,
        "Dribble": lambda r: r["xT_delta"] * 0.6,
        "Pressure": lambda r: abs(r["xT_delta"]) * 0.3,
        "Interception": lambda r: abs(r["xT_delta"]) * 0.5 + 0.02,
        "Clearance": lambda r: abs(r["xT_delta"]) * 0.4,
        "Block": lambda r: abs(r["xT_delta"]) * 0.7 + 0.03,
        "Foul Won": lambda r: 0.02,
        "Foul Committed": lambda r: -0.05,
        "Ball Receipt*": lambda r: 0.01,
        "Miscontrol": lambda r: -0.02,
    }
    
    raw_val = np.zeros(len(ev))
    for etype, fn in conditions.items():
        mask = ev["event_type"] == etype
        if mask.any():
            raw_val[mask] = ev[mask].apply(fn, axis=1)
    
    # Separate offensive (+) and defensive (-) contributions
    ev["event_value"] = raw_val
    ev["offensive_value"] = raw_val.clip(0)
    ev["defensive_value"] = (-raw_val).clip(0)
    
    return ev


def aggregate_event_values(ev: pd.DataFrame) -> pd.DataFrame:
    """Sum event values per player per match."""
    agg = ev.groupby(["match_id", "player_id"]).agg(
        event_value_sum      =("event_value",       "sum"),
        offensive_event_value=("offensive_value",   "sum"),
        defensive_event_value=("defensive_value",   "sum"),
        event_count          =("event_value",       "count"),
    ).reset_index()
    agg["event_value_per_action"] = (
        agg["event_value_sum"] / agg["event_count"].replace(0, np.nan)
    ).fillna(0)
    return agg


# ═══════════════════════════════════════════════════════════════════════════════
# 2.  POSITION ASSIGNMENT
# ═══════════════════════════════════════════════════════════════════════════════

def assign_positions(computed: pd.DataFrame, lineups: pd.DataFrame) -> pd.DataFrame:
    lineups = lineups.copy()
    
    def _extract_primary_position(positions):
        if isinstance(positions, np.ndarray):
            positions = positions.tolist()
        if isinstance(positions, (list, tuple)) and len(positions) > 0 and isinstance(positions[0], dict):
            return positions[0].get("position", "Unknown")
        return "Unknown"
    
    if "positions" in lineups.columns:
        lineups["position"] = lineups["positions"].apply(_extract_primary_position)
    elif "position" not in lineups.columns:
        lineups["position"] = "Unknown"
    
    lineups["position_group"] = lineups["position"].map(POSITION_MAP)
    player_pos = lineups.groupby("player_id")["position_group"].agg(
        lambda x: x.dropna().mode()[0] if len(x.dropna()) > 0 else "Midfielder"
    ).reset_index()
    
    return computed.merge(player_pos, on="player_id", how="left").assign(
        position_group=lambda d: d["position_group"].fillna("Midfielder")
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 3.  WITHIN-POSITION Z-SCORE NORMALISATION
# ═══════════════════════════════════════════════════════════════════════════════

def _robust_zscore(series: pd.Series) -> pd.Series:
    """Robust z-score using median & MAD (less sensitive to outliers)."""
    med = series.median()
    mad = (series - med).abs().median()
    if mad == 0:
        return pd.Series(0.0, index=series.index)
    return (series - med) / (mad * 1.4826)


def _zscore_within_position(df: pd.DataFrame, feat: str,
                             pos_col: str = "position_group",
                             robust: bool = True) -> pd.Series:
    """Compute position-specific z-scores for a feature column."""
    result = pd.Series(np.nan, index=df.index)
    for pos in df[pos_col].unique():
        mask = df[pos_col] == pos
        if mask.sum() < 2:
            result.loc[mask] = 0.0
            continue
        vals = df.loc[mask, feat].fillna(df[feat].median())
        result.loc[mask] = _robust_zscore(vals) if robust else (
            (vals - vals.mean()) / vals.std().clip(0.001)
        )
    return result.fillna(0.0)


# ═══════════════════════════════════════════════════════════════════════════════
# 4.  CONTRIBUTION SUB-SCORES  (each 0–10)
# ═══════════════════════════════════════════════════════════════════════════════

def _feature_subscore(df: pd.DataFrame, per_position_features: dict,
                      pos_col: str = "position_group") -> pd.Series:
    """Compute a weighted sub-score from position-specific z-scored features.
    
    per_position_features: position -> {feature: weight}
    Each player uses the feature set & weights for their own position.
    """
    score = pd.Series(0.0, index=df.index)
    for pos in df[pos_col].unique():
        mask = df[pos_col] == pos
        if not mask.any():
            continue
        fw = per_position_features.get(pos, per_position_features.get("Midfielder", {}))
        pos_score = pd.Series(0.0, index=df.index)
        wsum = 0.0
        for feat, w in fw.items():
            if feat not in df.columns:
                continue
            z = _zscore_within_position(df, feat, pos_col)
            z_clipped = z.clip(-3, 3)
            scaled = (z_clipped * 2.0 + 5.0).clip(0, 10)
            if w >= 0:
                pos_score += scaled * w
            else:
                pos_score -= scaled * abs(w)
            wsum += abs(w)
        if wsum > 0:
            pos_score = pos_score / wsum
        score.loc[mask] = pos_score.loc[mask].clip(0, 10)
    return score.clip(0, 10)


def compute_contribution_scores(df: pd.DataFrame,
                                pos_col: str = "position_group") -> pd.DataFrame:
    """Compute four contribution sub-scores for each player-match."""
    contrib = df[["match_id","player_id","player_name","team_name",
                   pos_col]].copy()
    if "season_label" in df.columns:
        contrib["season_label"] = df["season_label"]
    
    # Ensure we have the needed derived features
    work = df.copy()
    if "xg_overperformance" not in work.columns:
        work["xg_overperformance"] = (
            work.get("goals", 0) - work.get("predicted_xg", work.get("total_xg", 0))
        ).fillna(0)
    if "ball_retention_rate" not in work.columns:
        work["ball_retention_rate"] = 100.0
    
    # ── Offensive Contribution ──
    contrib["offensive_contribution"] = _feature_subscore(
        work, OFFENSIVE_FEATURES, pos_col
    ) if "total_shots" in work.columns else 5.0
    
    # ── Defensive Contribution ──
    contrib["defensive_contribution"] = _feature_subscore(
        work, DEFENSIVE_FEATURES, pos_col
    ) if "total_pressures" in work.columns else 5.0
    
    # ── Possession Contribution ──
    contrib["possession_contribution"] = _feature_subscore(
        work, POSSESSION_FEATURES, pos_col
    ) if "pass_accuracy" in work.columns else 5.0
    
    # ── Event Value Score ──
    # This is added later from the event value model
    contrib["event_value_score"] = 5.0  # placeholder, filled by run()
    
    # ── Physical / Contextual adjustments ──
    if "distance_covered" in work.columns:
        dz = _zscore_within_position(work, "distance_covered", pos_col)
        contrib["physical_adjustment"] = ((dz.clip(-2, 2) * 2.0 + 5.0).clip(0, 10))
    else:
        contrib["physical_adjustment"] = 5.0
    
    if "activity_drop_2nd_half" in work.columns:
        drop = work["activity_drop_2nd_half"].fillna(0).clip(0)
        dz = _zscore_within_position(work.assign(_d=drop), "_d", pos_col)
        contrib["fatigue_penalty"] = ((dz.clip(-2, 2) * 0.5).clip(-3, 0))
    else:
        contrib["fatigue_penalty"] = 0.0
    
    return contrib


# ═══════════════════════════════════════════════════════════════════════════════
# 5.  FINAL RATING  (0–10)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_final_rating(contrib: pd.DataFrame,
                         pos_col: str = "position_group") -> pd.DataFrame:
    """Positive-only rating: every player starts at 6.0 and can only improve.
    
    Only the excess above the neutral baseline (5.0) of each sub-score
    contributes upward.  Below-baseline performance does not reduce the
    rating — it simply provides no boost.  No fatigue penalty is applied.
    
    Final = 6.0 + Σ(max(0, contribution_i − 5.0) × weight_i)
            + max(0, physical_adjust − 5.0) × 0.05
    Clipped to [0, 10].
    """
    rating = pd.Series(6.0, index=contrib.index)

    for pos in contrib[pos_col].unique():
        mask = contrib[pos_col] == pos
        cw = CONTRIBUTION_WEIGHTS.get(pos, CONTRIBUTION_WEIGHTS["Midfielder"])
        for component, w in cw.items():
            col = f"{component}_contribution" if component != "event_value" else "event_value_score"
            if col in contrib.columns:
                excess = (contrib.loc[mask, col].fillna(5.0) - 5.0).clip(lower=0)
                rating.loc[mask] += excess * w

    if "physical_adjustment" in contrib.columns:
        excess = (contrib["physical_adjustment"].fillna(5.0) - 5.0).clip(lower=0)
        rating += excess * 0.05

    contrib["overall_score"] = rating.clip(0, 10).round(2)
    return contrib


def rating_label(score: float) -> str:
    for (lo, hi), label in RATING_LABELS.items():
        if lo <= score < hi:
            return label
    return "Below Average"


# ═══════════════════════════════════════════════════════════════════════════════
# 6.  LEGACY DIMENSION SCORES  (for backward compatibility)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_dimension_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Original 7-dimension scoring (kept for existing API consumers)."""
    meta_cols = ["match_id","player_id","player_name","team_name","position_group"]
    for c in ["season_label","season_id","competition_id"]:
        if c in df.columns:
            meta_cols.append(c)
    scores = df[meta_cols].copy()
    
    p = pd.Series(0.0, index=df.index)
    if "pass_accuracy"       in df.columns: p += normalize_to_score(df["pass_accuracy"].fillna(0))       * 0.40
    if "progressive_passes"  in df.columns: p += normalize_to_score(df["progressive_passes"].fillna(0))  * 0.35
    if "total_passes"        in df.columns: p += normalize_to_score(df["total_passes"].fillna(0))        * 0.25
    scores["passing_score"] = p.clip(0, 10).round(2)
    
    s = pd.Series(0.0, index=df.index)
    if "predicted_xg"  in df.columns: s += normalize_to_score(df["predicted_xg"].fillna(0))  * 0.40
    if "shot_accuracy" in df.columns: s += normalize_to_score(df["shot_accuracy"].fillna(0)) * 0.35
    if "total_shots"   in df.columns: s += normalize_to_score(df["total_shots"].fillna(0))   * 0.25
    scores["shooting_score"] = s.clip(0, 10).round(2)
    
    pos = pd.Series(5.0, index=df.index)
    if "attacking_tendency" in df.columns:
        pos = normalize_to_score(df["attacking_tendency"].fillna(50)) * 0.50
    if "position_deviation" in df.columns:
        pos += (10 - normalize_to_score(df["position_deviation"].fillna(0))) * 0.50
    scores["positioning_score"] = pos.clip(0, 10).round(2)
    
    pr = pd.Series(0.0, index=df.index)
    if "total_pressures"     in df.columns: pr += normalize_to_score(df["total_pressures"].fillna(0))     * 0.50
    if "pressure_regains"    in df.columns: pr += normalize_to_score(df["pressure_regains"].fillna(0))    * 0.30
    if "pressing_efficiency" in df.columns: pr += normalize_to_score(df["pressing_efficiency"].fillna(0)) * 0.20
    scores["pressing_score"] = pr.clip(0, 10).round(2)
    
    mv = pd.Series(0.0, index=df.index)
    if "total_carries"       in df.columns: mv += normalize_to_score(df["total_carries"].fillna(0))       * 0.35
    if "progressive_carries" in df.columns: mv += normalize_to_score(df["progressive_carries"].fillna(0)) * 0.35
    if "dribble_success_rate"in df.columns:
        dr = df["dribble_success_rate"].fillna(0)
        dr_adj = dr.where(df.get("total_dribbles", pd.Series(0, index=df.index)) >= 2, 50.0)
        mv += normalize_to_score(dr_adj) * 0.30
    scores["movement_score"] = mv.clip(0, 10).round(2)
    
    ph = pd.Series(0.0, index=df.index)
    if "total_actions"            in df.columns: ph += normalize_to_score(df["total_actions"].fillna(0)) * 0.35
    if "distance_covered"         in df.columns: ph += normalize_to_score(df["distance_covered"].fillna(0)) * 0.35
    if "activity_drop_2nd_half"   in df.columns:
        drop = df["activity_drop_2nd_half"].fillna(0)
        drop = drop.clip(lower=0)
        ph += (10 - normalize_to_score(drop)) * 0.30
    scores["physical_score"] = ph.clip(0, 10).round(2)
    
    bh = pd.Series(5.0, index=df.index)
    if "fouls_committed"    in df.columns: bh -= normalize_to_score(df["fouls_committed"].fillna(0))    * 0.30
    if "fouls_won"          in df.columns: bh += normalize_to_score(df["fouls_won"].fillna(0))          * 0.10
    if "yellow_cards"       in df.columns: bh -= normalize_to_score(df["yellow_cards"].fillna(0))       * 0.25
    if "red_cards"          in df.columns: bh -= normalize_to_score(df["red_cards"].fillna(0))          * 0.50
    if "ball_retention_rate"in df.columns: bh += normalize_to_score(df["ball_retention_rate"].fillna(100)) * 0.25
    scores["behavioral_score"] = bh.clip(0, 10).round(2)
    
    return scores


# ═══════════════════════════════════════════════════════════════════════════════
# 7.  PERCENTILES, TRENDS, CLUSTERING  (carried forward)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_overall_score(scores: pd.DataFrame, vaep_col: pd.Series) -> pd.DataFrame:
    def _weighted(row):
        pos     = row["position_group"]
        weights = POSITION_WEIGHTS.get(pos, POSITION_WEIGHTS["Midfielder"])
        return sum(row[c] * weights.get(c, 0) for c in SCORE_COLS)
    scores["overall_score"] = scores.apply(_weighted, axis=1).clip(0, 10).round(2)
    scores["vaep_norm"] = normalize_to_score(vaep_col.fillna(0))
    return scores


def compute_percentiles(scores: pd.DataFrame) -> pd.DataFrame:
    scores["percentile_in_team"]     = scores.groupby(["match_id","team_name"])["overall_score"]\
                                              .rank(pct=True).mul(100).round(1)
    scores["percentile_in_league"]   = scores.groupby("match_id")["overall_score"]\
                                              .rank(pct=True).mul(100).round(1)
    scores["percentile_in_position"] = scores.groupby(["match_id","position_group"])["overall_score"]\
                                              .rank(pct=True).mul(100).round(1)
    pos_avg = scores.groupby("position_group")["overall_score"].mean()
    scores["position_fit_score"] = (
        scores["overall_score"] / scores["position_group"].map(pos_avg) * 5
    ).clip(0, 10).round(2)
    return scores


def compute_trends(scores: pd.DataFrame, matches: pd.DataFrame) -> pd.DataFrame:
    match_dates = matches[["match_id","match_date"]].copy()
    match_dates["match_date"] = pd.to_datetime(match_dates["match_date"])
    tmp = scores.merge(match_dates, on="match_id", how="left").sort_values(["player_id","match_date"])

    def get_trend(s):
        n = len(s)
        if n < 4:
            return "Stable", 0.0
        x = np.arange(n)
        slope, _, _, p_val, _ = scipy_stats.linregress(x, s.values)
        if p_val < 0.10 and slope > 0.01:
            return "Improving", round(slope, 4)
        if p_val < 0.10 and slope < -0.01:
            return "Declining", round(slope, 4)
        return "Stable", round(slope, 4)

    def get_trend_row(s):
        return get_trend(s)

    tmp2 = tmp.groupby("player_id")["overall_score"].apply(get_trend_row)
    tmp2 = tmp2.reset_index()
    tmp2[["performance_trend", "trend_slope"]] = pd.DataFrame(
        tmp2["overall_score"].tolist(), index=tmp2.index
    )
    trends = tmp2.drop(columns=["overall_score"])
    return scores.merge(trends, on="player_id", how="left").assign(
        performance_trend=lambda d: d["performance_trend"].fillna("Stable"),
        trend_slope=lambda d: d["trend_slope"].fillna(0.0),
    )


def cluster_players(scores: pd.DataFrame) -> pd.DataFrame:
    season_avg = scores.groupby(["player_id","player_name","position_group"]).agg(
        **{f"avg_{c.replace('_score','')}": (c,"mean") for c in SCORE_COLS},
        matches=("match_id","count")
    ).reset_index()

    filtered = season_avg[season_avg["matches"] >= 3].copy()
    feats    = [c for c in filtered.columns if c.startswith("avg_")]

    normalized = filtered[feats].copy()
    for pos in filtered["position_group"].unique():
        mask = filtered["position_group"] == pos
        if mask.sum() < 2:
            continue
        for col in feats:
            mean = filtered.loc[mask, col].mean()
            std  = filtered.loc[mask, col].std()
            if std > 0:
                normalized.loc[mask, col] = (filtered.loc[mask, col] - mean) / std

    X  = normalized[feats].fillna(0).values
    gmm = GaussianMixture(n_components=5, random_state=42, n_init=10, covariance_type="full")
    filtered["cluster_id"]     = gmm.fit_predict(X)
    filtered["player_cluster"] = filtered["cluster_id"].map(CLUSTER_NAMES)

    ensure_dirs(MODELS_DIR)
    with open(MODELS_DIR / "gmm_model.pkl","wb") as f:
        pickle.dump(gmm, f)

    return scores.merge(
        filtered[["player_id","player_cluster"]], on="player_id", how="left"
    ).assign(player_cluster=lambda d: d["player_cluster"].fillna("Unknown"))


# ═══════════════════════════════════════════════════════════════════════════════
# 8.  RUN
# ═══════════════════════════════════════════════════════════════════════════════

def run():
    print("=" * 60)
    print("SCORING PIPELINE STEP 5: Player Scoring Model (V2)")
    print("=" * 60)

    computed    = pd.read_parquet(DATA_DIR / "computed_features.parquet")
    vaep        = pd.read_parquet(DATA_DIR / "player_vaep_ratings.parquet")
    barca_shots = pd.read_parquet(DATA_DIR / "barca_shots_with_xg.parquet")
    matches     = pd.read_parquet(DATA_DIR / "matches.parquet")
    lineups     = pd.read_parquet(DATA_DIR / "lineups.parquet")
    events_clean = None
    ev_agg      = None
    try:
        events_clean = pd.read_parquet(DATA_DIR / "events_clean.parquet")
    except FileNotFoundError:
        print("  [WARN] events_clean.parquet not found — event value model skipped")

    # ── Event Value Model ──
    if events_clean is not None and len(events_clean):
        print("  Computing event value model...")
        # Merge xG into events
        xg_map = barca_shots.groupby(["match_id","player_id","event_id"]).agg(
            predicted_xg=("predicted_xg","first")
        ).reset_index()
        events_with_xg = events_clean.merge(
            xg_map, on=["match_id","player_id","event_id"], how="left"
        )
        # Build expected threat grid
        xT = build_xT_grid(events_with_xg)
        # Compute event values
        ev = compute_event_values(events_with_xg, barca_shots, xT)
        ev_agg = aggregate_event_values(ev)
        print(f"    Processed {len(ev):,} events -> {len(ev_agg):,} player-match aggregations")

    # ── Merge data ──
    xg_per = barca_shots.groupby(["match_id","player_id"]).agg(
        predicted_xg=("predicted_xg","sum")
    ).reset_index()
    df = computed.merge(
        vaep[["match_id","player_id","vaep_rating","offensive_value","defensive_value"]],
        on=["match_id","player_id"], how="left"
    )
    df = df.merge(xg_per, on=["match_id","player_id"], how="left")
    df["vaep_rating"]     = df["vaep_rating"].fillna(0)
    df["predicted_xg"]    = df["predicted_xg"].fillna(0)
    df["offensive_value"] = df["offensive_value"].fillna(0)
    df["defensive_value"] = df["defensive_value"].fillna(0)

    df = assign_positions(df, lineups)

    # ── Contribution Scores (V2) ──
    contrib = compute_contribution_scores(df)
    
    # Merge event value scores
    if ev_agg is not None and len(ev_agg):
        contrib = contrib.merge(
            ev_agg[["match_id","player_id","event_value_sum",
                     "offensive_event_value","defensive_event_value",
                     "event_value_per_action"]],
            on=["match_id","player_id"], how="left"
        )
        # Normalize event_value_sum within position to 0–10
        contrib["event_value_score"] = (
            _zscore_within_position(
                contrib.assign(_ev=contrib["event_value_sum"].fillna(0)),
                "_ev", "position_group"
            ).clip(-2.5, 2.5) * 2.0 + 5.0
        ).clip(0, 10)
    else:
        contrib["event_value_score"] = 5.0
    
    contrib = compute_final_rating(contrib)

    # ── Legacy dimension scores (for backward compat) ──
    legacy_scores = compute_dimension_scores(df)
    legacy_scores["vaep_rating"]     = df["vaep_rating"].values
    legacy_scores["offensive_value"] = df["offensive_value"].values
    legacy_scores["defensive_value"] = df["defensive_value"].values
    legacy_scores = compute_overall_score(legacy_scores, df["vaep_rating"])
    
    # Merge legacy scores into contrib (keeps all columns)
    merge_keys = ["match_id","player_id","player_name","team_name","position_group"]
    for c in SCORE_COLS + ["overall_score","vaep_norm","vaep_rating",
                            "offensive_value","defensive_value"]:
        if c in legacy_scores.columns and c not in contrib.columns:
            contrib[c] = legacy_scores[c].values
        elif c in legacy_scores.columns:
            contrib[f"legacy_{c}"] = legacy_scores[c].values

    # ── Finalise ──
    scores = compute_percentiles(contrib)
    scores = compute_trends(scores, matches)
    scores = cluster_players(scores)
    scores = add_uuid_column(scores, "uuid", based_on=["match_id","player_id"])

    ensure_dirs(DATA_DIR)
    scores.to_parquet(DATA_DIR / "model_scores.parquet", index=False)
    scores.to_csv(DATA_DIR / "model_scores.csv", index=False)

    # Position Benchmarks
    bench_cols = [c for c in computed.columns if c in [
        "pass_accuracy","progressive_passes","total_passes",
        "total_shots","total_xg","goals","total_pressures",
        "pressure_regains","distance_covered","total_carries",
        "total_actions","fouls_committed","vaep_rating",
    ]]
    merged_bench = computed.merge(
        df[["match_id","player_id","position_group","vaep_rating"]],
        on=["match_id","player_id"], how="left"
    )
    benchmarks = merged_bench.groupby("position_group")[bench_cols].mean().round(4).reset_index()
    benchmarks.to_parquet(DATA_DIR / "position_benchmarks.parquet")

    with open(MODELS_DIR / "position_weights.json","w") as f:
        json.dump(POSITION_WEIGHTS, f, indent=2)

    print(f"\nStep 5 Complete!")
    print(f"   Player-match scores: {len(scores):,}")
    print(f"   Columns: {list(scores.columns)}")
    
    # Summary of new rating distribution
    print(f"\nRating distribution:")
    for label in ["Exceptional", "Excellent", "Very Good", "Good", "Average", "Below Average"]:
        count = scores["overall_score"].apply(
            lambda s: rating_label(s) == label
        ).sum()
        print(f"   {label:20s}: {count}")
    
    top5 = scores.groupby("player_name")["overall_score"].mean().sort_values(ascending=False).head(5)
    print(f"\nTop 5:\n{top5.round(2).to_string()}")
    return scores


if __name__ == "__main__":
    run()
