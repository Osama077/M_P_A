"""pipeline/metadata_loader.py — Build player metadata from StatsBomb data"""

import pandas as pd
import numpy as np
from pathlib import Path
from config import DATA_DIR, POSITION_MAP
from utils.uuid_manager import add_uuid_column
from utils.helpers import ensure_dirs

METADATA_DIR = DATA_DIR / "metadata"


def build_player_metadata():
    """Extract player identity info from lineups, events, and scores data."""
    ensure_dirs(METADATA_DIR)

    lineups = pd.read_parquet(DATA_DIR / "lineups.parquet")
    events = pd.read_parquet(DATA_DIR / "events_clean.parquet")
    scores = pd.read_parquet(DATA_DIR / "model_scores.parquet")
    computed = pd.read_parquet(DATA_DIR / "computed_features.parquet")

    # 1. Base identity from lineups
    base = lineups[["player_id", "player_name"]].drop_duplicates(subset="player_id").copy()
    base = base.rename(columns={"player_name": "full_name"})

    # 2. Primary position (mode across all seasons)
    def _extract_position(positions):
        if isinstance(positions, np.ndarray):
            positions = positions.tolist()
        if isinstance(positions, (list, tuple)) and len(positions) > 0 and isinstance(positions[0], dict):
            return positions[0].get("position", "Unknown")
        return "Unknown"

    if "positions" in lineups.columns:
        lineups["position"] = lineups["positions"].apply(_extract_position)
    lineups["position_group"] = lineups["position"].map(POSITION_MAP)
    player_pos = lineups.groupby("player_id")["position_group"].agg(
        lambda x: x.dropna().mode()[0] if len(x.dropna().mode()) > 0 else "Midfielder"
    ).reset_index().rename(columns={"position_group": "primary_position"})

    # 3. Preferred foot from pass body part usage
    pass_events = events[events["event_type"] == "Pass"].copy()
    pass_events = pass_events[pass_events["bodypart"].isin(["Left Foot", "Right Foot", "Head", "Foot"])]
    foot_usage = pass_events.groupby("player_id")["bodypart"].agg(
        lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else None
    ).reset_index().rename(columns={"bodypart": "preferred_foot"})

    def _map_foot(v):
        if v is None:
            return None
        if "Left" in str(v):
            return "left"
        if "Right" in str(v):
            return "right"
        return None

    foot_usage["preferred_foot"] = foot_usage["preferred_foot"].apply(_map_foot)

    # 4. Career stats
    career = scores.groupby("player_id").agg(
        total_appearances=("match_id", "count"),
        career_avg_score=("overall_score", "mean"),
        career_avg_vaep=("vaep_rating", "mean"),
    ).reset_index()

    # 5. Season-level stats
    if "season_label" in scores.columns:
        season_stats = scores.groupby(["player_id", "season_label"]).agg(
            appearances=("match_id", "count"),
            avg_season_score=("overall_score", "mean"),
            avg_season_vaep=("vaep_rating", "mean"),
        ).reset_index()
        season_list = season_stats.groupby("player_id").apply(
            lambda g: [{"season_label": r["season_label"],
                        "appearances": int(r["appearances"]),
                        "avg_score": round(float(r["avg_season_score"]), 2),
                        "avg_vaep": round(float(r["avg_season_vaep"]), 2)}
                       for _, r in g.iterrows()]
        ).reset_index().rename(columns={0: "season_summaries"})
    else:
        season_list = pd.DataFrame(columns=["player_id", "season_summaries"])

    # 6. Jersey numbers by season
    if "season_label" in lineups.columns and "jersey_number" in lineups.columns:
        jersey = lineups[lineups["jersey_number"].notna()].groupby(
            ["player_id", "season_label"]
        )["jersey_number"].first().reset_index()
        jersey_map = jersey.groupby("player_id").apply(
            lambda g: {r["season_label"]: int(r["jersey_number"]) for _, r in g.iterrows()}
        ).reset_index().rename(columns={0: "jersey_numbers"})
    else:
        jersey_map = pd.DataFrame(columns=["player_id", "jersey_numbers"])

    # 7. Merge everything
    meta = base.merge(player_pos, on="player_id", how="left") \
              .merge(foot_usage, on="player_id", how="left") \
              .merge(career, on="player_id", how="left") \
              .merge(season_list, on="player_id", how="left") \
              .merge(jersey_map, on="player_id", how="left")

    meta["primary_position"] = meta["primary_position"].fillna("Midfielder")
    meta["total_appearances"] = meta["total_appearances"].fillna(0).astype(int)
    meta["season_summaries"] = meta["season_summaries"].apply(
        lambda x: x if isinstance(x, list) else []
    )
    meta["jersey_numbers"] = meta["jersey_numbers"].apply(
        lambda x: x if isinstance(x, dict) else {}
    )

    meta = add_uuid_column(meta, "uuid", based_on=["player_id"])

    meta.to_parquet(METADATA_DIR / "player_info.parquet", index=False)
    meta.to_csv(METADATA_DIR / "player_info.csv", index=False)
    print(f"Player metadata built: {len(meta)} players")
    return meta


def run():
    print("=" * 60)
    print("METADATA LOADER: Building Player Metadata")
    print("=" * 60)
    return build_player_metadata()


if __name__ == "__main__":
    run()
