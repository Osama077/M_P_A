"""
pipeline/scoring_model.py — Player Scoring Model
يقابل Notebook 05
"""

import json
import pickle
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.cluster import KMeans

from config import DATA_DIR, MODELS_DIR, POSITION_WEIGHTS, POSITION_MAP, CLUSTER_NAMES
from utils.uuid_manager import add_uuid_column
from utils.helpers import normalize_to_score, ensure_dirs

SCORE_COLS = [
    "passing_score","shooting_score","positioning_score","pressing_score",
    "movement_score","physical_score","behavioral_score"
]


def assign_positions(computed: pd.DataFrame, lineups: pd.DataFrame) -> pd.DataFrame:
    lineups = lineups.copy()

    def _extract_primary_position(positions):
        # StatsBomb lineups may store positions as list, tuple, or numpy array of dicts.
        if isinstance(positions, np.ndarray):
            positions = positions.tolist()
        if isinstance(positions, (list, tuple)) and len(positions) > 0 and isinstance(positions[0], dict):
            return positions[0].get("position", "Unknown")
        return "Unknown"

    if "positions" in lineups.columns:
        lineups["position"] = lineups["positions"].apply(_extract_primary_position)
    elif "position" not in lineups.columns:
        lineups["position"] = "Unknown"

    lineups["position_group"] = lineups["position"].map(POSITION_MAP).fillna("Midfielder")
    player_pos = lineups.groupby("player_id")["position_group"].agg(
        lambda x: x.mode()[0] if len(x) > 0 else "Midfielder"
    ).reset_index()

    return computed.merge(player_pos, on="player_id", how="left").assign(
        position_group=lambda d: d["position_group"].fillna("Midfielder")
    )


def compute_dimension_scores(df: pd.DataFrame) -> pd.DataFrame:
    scores = df[["match_id","player_id","player_name","team_name","position_group"]].copy()

    # Passing
    p = pd.Series(0.0, index=df.index)
    if "pass_accuracy"       in df.columns: p += normalize_to_score(df["pass_accuracy"].fillna(0))       * 0.40
    if "progressive_passes"  in df.columns: p += normalize_to_score(df["progressive_passes"].fillna(0))  * 0.35
    if "total_passes"        in df.columns: p += normalize_to_score(df["total_passes"].fillna(0))        * 0.25
    scores["passing_score"] = p.clip(0, 10).round(2)

    # Shooting
    s = pd.Series(0.0, index=df.index)
    if "predicted_xg"  in df.columns: s += normalize_to_score(df["predicted_xg"].fillna(0))  * 0.40
    if "shot_accuracy" in df.columns: s += normalize_to_score(df["shot_accuracy"].fillna(0)) * 0.35
    if "total_shots"   in df.columns: s += normalize_to_score(df["total_shots"].fillna(0))   * 0.25
    scores["shooting_score"] = s.clip(0, 10).round(2)

    # Positioning
    pos = pd.Series(5.0, index=df.index)
    if "attacking_tendency" in df.columns:
        pos = normalize_to_score(df["attacking_tendency"].fillna(50)) * 0.50
    if "position_deviation" in df.columns:
        pos += (10 - normalize_to_score(df["position_deviation"].fillna(0))) * 0.50
    scores["positioning_score"] = pos.clip(0, 10).round(2)

    # Pressing
    pr = pd.Series(0.0, index=df.index)
    if "total_pressures"     in df.columns: pr += normalize_to_score(df["total_pressures"].fillna(0))     * 0.50
    if "pressure_regains"    in df.columns: pr += normalize_to_score(df["pressure_regains"].fillna(0))    * 0.30
    if "pressing_efficiency" in df.columns: pr += normalize_to_score(df["pressing_efficiency"].fillna(0)) * 0.20
    scores["pressing_score"] = pr.clip(0, 10).round(2)

    # Movement
    mv = pd.Series(0.0, index=df.index)
    if "total_carries"       in df.columns: mv += normalize_to_score(df["total_carries"].fillna(0))       * 0.35
    if "progressive_carries" in df.columns: mv += normalize_to_score(df["progressive_carries"].fillna(0)) * 0.35
    if "dribble_success_rate"in df.columns: mv += normalize_to_score(df["dribble_success_rate"].fillna(0))* 0.30
    scores["movement_score"] = mv.clip(0, 10).round(2)

    # Physical
    ph = pd.Series(0.0, index=df.index)
    if "total_actions"          in df.columns: ph += normalize_to_score(df["total_actions"].fillna(0)) * 0.50
    if "activity_drop_2nd_half" in df.columns:
        ph += (10 - normalize_to_score(df["activity_drop_2nd_half"].fillna(0).abs())) * 0.50
    scores["physical_score"] = ph.clip(0, 10).round(2)

    # Behavioral
    bh = pd.Series(8.0, index=df.index)
    if "fouls_committed"    in df.columns: bh -= normalize_to_score(df["fouls_committed"].fillna(0))    * 0.40
    if "yellow_cards"       in df.columns: bh -= df["yellow_cards"].fillna(0) * 1.5
    if "red_cards"          in df.columns: bh -= df["red_cards"].fillna(0) * 3.0
    if "ball_retention_rate"in df.columns: bh += normalize_to_score(df["ball_retention_rate"].fillna(0)) * 0.30
    scores["behavioral_score"] = bh.clip(0, 10).round(2)

    return scores


def compute_overall_score(scores: pd.DataFrame, vaep_col: pd.Series) -> pd.DataFrame:
    def _weighted(row):
        pos     = row["position_group"]
        weights = POSITION_WEIGHTS.get(pos, POSITION_WEIGHTS["Midfielder"])
        return sum(row[c] * weights.get(c, 0) for c in SCORE_COLS)

    scores["overall_score"] = scores.apply(_weighted, axis=1)
    vaep_norm = normalize_to_score(vaep_col.fillna(0))
    scores["overall_score"] = (scores["overall_score"] * 0.80 + vaep_norm * 0.20).clip(0, 10).round(2)
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
        if len(s) < 4: return "Stable"
        recent = s.tail(3).mean()
        before = s.iloc[-6:-3].mean() if len(s) >= 6 else s.head(3).mean()
        diff   = recent - before
        if diff > 0.3:  return "Improving"
        if diff < -0.3: return "Declining"
        return "Stable"

    trends = tmp.groupby("player_id")["overall_score"].apply(get_trend).reset_index()
    trends.columns = ["player_id","performance_trend"]
    return scores.merge(trends, on="player_id", how="left").assign(
        performance_trend=lambda d: d["performance_trend"].fillna("Stable")
    )


def cluster_players(scores: pd.DataFrame) -> pd.DataFrame:
    season_avg = scores.groupby(["player_id","player_name","position_group"]).agg(
        **{f"avg_{c.replace('_score','')}": (c,"mean") for c in SCORE_COLS},
        matches=("match_id","count")
    ).reset_index()

    filtered = season_avg[season_avg["matches"] >= 3].copy()
    feats    = [c for c in filtered.columns if c.startswith("avg_")]
    X        = MinMaxScaler().fit_transform(filtered[feats])
    km       = KMeans(n_clusters=5, random_state=42, n_init=10)
    filtered["cluster_id"]     = km.fit_predict(X)
    filtered["player_cluster"] = filtered["cluster_id"].map(CLUSTER_NAMES)

    ensure_dirs(MODELS_DIR)
    with open(MODELS_DIR / "kmeans_model.pkl","wb") as f:
        pickle.dump(km, f)

    return scores.merge(
        filtered[["player_id","player_cluster"]], on="player_id", how="left"
    ).assign(player_cluster=lambda d: d["player_cluster"].fillna("Unknown"))


def run():
    print("=" * 60)
    print("🏆 PIPELINE STEP 5: Player Scoring Model")
    print("=" * 60)

    computed   = pd.read_parquet(DATA_DIR / "computed_features.parquet")
    vaep       = pd.read_parquet(DATA_DIR / "player_vaep_ratings.parquet")
    barca_shots= pd.read_parquet(DATA_DIR / "barca_shots_with_xg.parquet")
    matches    = pd.read_parquet(DATA_DIR / "matches.parquet")
    lineups    = pd.read_parquet(DATA_DIR / "lineups.parquet")

    # Merge xG
    xg_per = barca_shots.groupby(["match_id","player_id"]).agg(
        predicted_xg=("predicted_xg","sum")
    ).reset_index()
    df = computed.merge(vaep[["match_id","player_id","vaep_rating","offensive_value","defensive_value"]],
                        on=["match_id","player_id"], how="left")
    df = df.merge(xg_per, on=["match_id","player_id"], how="left")
    df["vaep_rating"]    = df["vaep_rating"].fillna(0)
    df["predicted_xg"]   = df["predicted_xg"].fillna(0)
    df["offensive_value"]= df["offensive_value"].fillna(0)
    df["defensive_value"]= df["defensive_value"].fillna(0)

    df = assign_positions(df, lineups)

    scores  = compute_dimension_scores(df)
    scores["vaep_rating"]     = df["vaep_rating"].values
    scores["offensive_value"] = df["offensive_value"].values
    scores["defensive_value"] = df["defensive_value"].values
    scores  = compute_overall_score(scores, df["vaep_rating"])
    scores  = compute_percentiles(scores)
    scores  = compute_trends(scores, matches)
    scores  = cluster_players(scores)
    scores  = add_uuid_column(scores, "uuid", based_on=["match_id","player_id"])

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
    benchmarks = merged_bench.groupby("position_group")[bench_cols].mean().round(4)
    benchmarks.to_parquet(DATA_DIR / "position_benchmarks.parquet")

    with open(MODELS_DIR / "position_weights.json","w") as f:
        json.dump(POSITION_WEIGHTS, f, indent=2)

    print(f"\n✅ Step 5 Complete!")
    print(f"   Player-match scores: {len(scores):,}")
    top5 = scores.groupby("player_name")["overall_score"].mean().sort_values(ascending=False).head(5)
    print(f"\n📊 Top 5:\n{top5.round(2).to_string()}")
    return scores


if __name__ == "__main__":
    run()
