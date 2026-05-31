"""
pipeline/data_loader.py — Data Loading & Preprocessing
يقابل Notebook 01
"""

import pandas as pd
import numpy as np
import warnings
from pathlib import Path
from statsbombpy import sb

from config import (
    COMPETITION_ID, SEASON_ID, TARGET_TEAM,
    ACTION_TYPE_MAP, DATA_DIR
)
from utils.uuid_manager import add_uuid_column, add_uuids_to_all
from utils.helpers import ensure_dirs

warnings.filterwarnings("ignore")


# ──────────────────────────────────────────────────────────────────────────────
# 1. LOAD RAW DATA
# ──────────────────────────────────────────────────────────────────────────────

def load_matches() -> pd.DataFrame:
    """تحميل ماتشات Barcelona في La Liga 2015/16"""
    all_matches = sb.matches(
        competition_id=COMPETITION_ID,
        season_id=SEASON_ID
    )
    barca = all_matches[
        (all_matches["home_team"] == TARGET_TEAM) |
        (all_matches["away_team"] == TARGET_TEAM)
    ].reset_index(drop=True)

    barca = add_uuid_column(barca, "uuid", based_on=["match_id"])
    print(f"✅ Matches loaded: {len(barca)}")
    return barca


def load_all_events(matches_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """تحميل Events وLineups لكل الماتشات"""
    all_events, all_lineups = [], []

    for idx, row in matches_df.iterrows():
        match_id = row["match_id"]
        events   = sb.events(match_id=match_id)
        events["match_id"] = match_id
        all_events.append(events)

        lineups = sb.lineups(match_id=match_id)
        for team_name, lineup_df in lineups.items():
            lineup_df["match_id"]  = match_id
            lineup_df["team_name"] = team_name
            all_lineups.append(lineup_df)

        if (idx + 1) % 5 == 0:
            print(f"  Loaded {idx + 1}/{len(matches_df)} matches...")

    events_df  = pd.concat(all_events,  ignore_index=True)
    lineups_df = pd.concat(all_lineups, ignore_index=True)

    print(f"✅ Events loaded : {len(events_df):,}")
    print(f"✅ Lineups loaded: {len(lineups_df):,}")
    return events_df, lineups_df


# ──────────────────────────────────────────────────────────────────────────────
# 2. CLEAN EVENTS
# ──────────────────────────────────────────────────────────────────────────────

def _extract_location(loc):
    if isinstance(loc, list) and len(loc) >= 2:
        return loc[0], loc[1]
    return None, None


def _extract_pass_details(df: pd.DataFrame) -> pd.DataFrame:
    pass_mask = df["type"] == "Pass"

    df.loc[pass_mask, "pass_outcome"] = df.loc[pass_mask, "pass_outcome"].apply(
        lambda x: x.get("name", "Complete") if isinstance(x, dict)
        else (x if pd.notna(x) else "Complete")
    )
    df.loc[pass_mask, "pass_end_x"] = df.loc[pass_mask, "pass_end_location"].apply(
        lambda x: x[0] if isinstance(x, list) else None
    )
    df.loc[pass_mask, "pass_end_y"] = df.loc[pass_mask, "pass_end_location"].apply(
        lambda x: x[1] if isinstance(x, list) else None
    )
    df.loc[pass_mask, "bodypart"] = df.loc[pass_mask, "pass_body_part"].apply(
        lambda x: x.get("name", None) if isinstance(x, dict) else x
    )

    def is_progressive(row):
        try:
            s = np.sqrt((120 - row["location_x"])**2 + (40 - row["location_y"])**2)
            e = np.sqrt((120 - row["pass_end_x"])**2 + (40 - row["pass_end_y"])**2)
            return int(e < s * 0.75)
        except:
            return 0

    df.loc[pass_mask, "is_progressive_pass"] = df[pass_mask].apply(is_progressive, axis=1)
    df["is_progressive_pass"] = df["is_progressive_pass"].fillna(0).astype(int)
    return df


def _extract_shot_details(df: pd.DataFrame) -> pd.DataFrame:
    shot_mask = df["type"] == "Shot"

    df.loc[shot_mask, "shot_outcome"] = df.loc[shot_mask, "shot_outcome"].apply(
        lambda x: x.get("name", None) if isinstance(x, dict) else x
    )
    df.loc[shot_mask, "shot_xg"]       = df.loc[shot_mask, "shot_statsbomb_xg"]
    df.loc[shot_mask, "shot_technique"] = df.loc[shot_mask, "shot_technique"].apply(
        lambda x: x.get("name", None) if isinstance(x, dict) else x
    )
    df.loc[shot_mask, "shot_end_x"] = df.loc[shot_mask, "shot_end_location"].apply(
        lambda x: x[0] if isinstance(x, list) else None
    )
    df.loc[shot_mask, "shot_end_y"] = df.loc[shot_mask, "shot_end_location"].apply(
        lambda x: x[1] if isinstance(x, list) else None
    )
    df.loc[shot_mask, "bodypart"] = df.loc[shot_mask, "shot_body_part"].apply(
        lambda x: x.get("name", None) if isinstance(x, dict) else x
    )
    df.loc[shot_mask, "shot_type_name"] = df.loc[shot_mask, "shot_type"].apply(
        lambda x: x.get("name", None) if isinstance(x, dict) else x
    )
    set_pieces = ["Free Kick", "Corner", "Penalty", "Kick Off"]
    df["shot_after_set_piece"] = df["shot_type_name"].isin(set_pieces).astype(int)

    df.loc[shot_mask, "distance_to_goal"] = np.sqrt(
        (120 - df.loc[shot_mask, "location_x"])**2 +
        (40  - df.loc[shot_mask, "location_y"])**2
    )
    df.loc[shot_mask, "angle_to_goal"] = np.abs(
        np.arctan2(df.loc[shot_mask, "location_y"] - 40,
                   120 - df.loc[shot_mask, "location_x"])
    )
    return df


def _extract_carry_details(df: pd.DataFrame) -> pd.DataFrame:
    carry_mask = df["type"] == "Carry"
    df.loc[carry_mask, "carry_end_x"] = df.loc[carry_mask, "carry_end_location"].apply(
        lambda x: x[0] if isinstance(x, list) else None
    )
    df.loc[carry_mask, "carry_end_y"] = df.loc[carry_mask, "carry_end_location"].apply(
        lambda x: x[1] if isinstance(x, list) else None
    )
    return df


def _extract_dribble_details(df: pd.DataFrame) -> pd.DataFrame:
    dribble_mask = df["type"] == "Dribble"
    df.loc[dribble_mask, "dribble_outcome"] = df.loc[dribble_mask, "dribble_outcome"].apply(
        lambda x: x.get("name", None) if isinstance(x, dict) else x
    )
    return df


def clean_events(events_df: pd.DataFrame) -> pd.DataFrame:
    """تنظيف وتحضير الـ events"""
    print("🔄 Cleaning events...")
    df = events_df.copy()

    # Location
    df["location_x"], df["location_y"] = zip(*df["location"].apply(_extract_location))

    # Timestamp
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="%H:%M:%S.%f", errors="coerce")
    df["timestamp_seconds"] = (
        df["timestamp"].dt.hour * 3600 +
        df["timestamp"].dt.minute * 60 +
        df["timestamp"].dt.second
    )

    # Flags
    df["under_pressure"] = df["under_pressure"].fillna(False).astype(bool).astype(int)
    df["counterpress"]   = df["counterpress"].fillna(False).astype(bool).astype(int)

    # Event Index
    df = df.sort_values(["match_id", "index"]).reset_index(drop=True)
    df["event_index"] = df.groupby("match_id").cumcount() + 1

    # Details
    df = _extract_pass_details(df)
    df = _extract_shot_details(df)
    df = _extract_carry_details(df)
    df = _extract_dribble_details(df)

    # Foul cards
    foul_mask = df["type"] == "Foul Committed"
    if foul_mask.any():
        df.loc[foul_mask, "foul_card"] = df.loc[foul_mask, "foul_committed_card"].apply(
            lambda x: x.get("name", None) if isinstance(x, dict) else x
        )

    # Final clean table
    keep_cols = [
        "id", "match_id", "player_id", "player", "team", "team_id",
        "type", "period", "minute", "second", "timestamp_seconds", "event_index",
        "location_x", "location_y", "under_pressure", "counterpress",
        "pass_length", "pass_angle", "pass_outcome", "pass_end_x", "pass_end_y",
        "is_progressive_pass", "bodypart",
        "shot_outcome", "shot_xg", "shot_technique", "shot_end_x", "shot_end_y",
        "shot_after_set_piece", "distance_to_goal", "angle_to_goal",
        "carry_end_x", "carry_end_y", "dribble_outcome",
        "duration",
    ]
    available = [c for c in keep_cols if c in df.columns]
    events_clean = df[available].copy()

    # Rename
    events_clean = events_clean.rename(columns={
        "id":     "event_id",
        "player": "player_name",
        "team":   "team_name",
        "type":   "event_type",
    })

    # UUID
    if "event_id" in events_clean.columns:
        events_clean = add_uuid_column(events_clean, "uuid", based_on=["event_id"])
    else:
        events_clean = add_uuid_column(events_clean, "uuid")

    print(f"✅ Events cleaned: {events_clean.shape}")
    return events_clean


# ──────────────────────────────────────────────────────────────────────────────
# 3. SPADL CONVERSION
# ──────────────────────────────────────────────────────────────────────────────

def build_spadl(events_clean: pd.DataFrame) -> pd.DataFrame:
    """تحويل Events لـ SPADL-like format"""
    print("🔄 Building SPADL actions...")

    df = events_clean[
        events_clean["event_type"].isin(ACTION_TYPE_MAP.keys())
    ].copy()

    df["type_name"]     = df["event_type"].map(ACTION_TYPE_MAP)
    df["result_name"]   = df.apply(_get_result, axis=1)
    df["bodypart_name"] = df["bodypart"].fillna("foot")
    df["period_id"]     = df["period"]
    df["time_seconds"]  = df["timestamp_seconds"]
    df["start_x"]       = df["location_x"]
    df["start_y"]       = df["location_y"]
    df["end_x"]         = df["pass_end_x"].fillna(
                           df["carry_end_x"].fillna(
                           df["shot_end_x"].fillna(df["location_x"])))
    df["end_y"]         = df["pass_end_y"].fillna(
                           df["carry_end_y"].fillna(
                           df["shot_end_y"].fillna(df["location_y"])))

    spadl = df[[
        "match_id", "player_id", "player_name", "team_name",
        "period_id", "time_seconds", "event_index",
        "type_name", "result_name", "bodypart_name",
        "start_x", "start_y", "end_x", "end_y",
        "under_pressure"
    ]].reset_index(drop=True)

    spadl = add_uuid_column(spadl, "uuid", based_on=["match_id", "event_index"])
    print(f"✅ SPADL actions: {len(spadl):,}")
    return spadl


def _get_result(row) -> str:
    etype = row["event_type"]
    if etype == "Pass":
        return "fail" if row.get("pass_outcome") not in [None, "Complete"] else "success"
    if etype == "Shot":
        return "success" if row.get("shot_outcome") == "Goal" else "fail"
    if etype == "Dribble":
        return "success" if row.get("dribble_outcome") == "Complete" else "fail"
    return "success"


# ──────────────────────────────────────────────────────────────────────────────
# 4. SHOTS FOR xG
# ──────────────────────────────────────────────────────────────────────────────

def build_shots_for_xg(events_clean: pd.DataFrame) -> pd.DataFrame:
    """استخراج Shot events جاهزة للـ xG Model"""
    shots = events_clean[events_clean["event_type"] == "Shot"][[
        "event_id", "match_id", "player_id", "player_name",
        "location_x", "location_y", "distance_to_goal", "angle_to_goal",
        "shot_technique", "bodypart", "under_pressure",
        "shot_after_set_piece", "shot_outcome", "shot_xg"
    ]].copy()

    shots["is_goal"] = (shots["shot_outcome"] == "Goal").astype(int)
    shots = add_uuid_column(shots, "uuid", based_on=["event_id"])
    print(f"✅ Shots for xG: {len(shots):,}")
    return shots


# ──────────────────────────────────────────────────────────────────────────────
# 5. SAVE & LOAD
# ──────────────────────────────────────────────────────────────────────────────

def save_all(matches, events_clean, lineups, spadl, shots_xg):
    ensure_dirs(DATA_DIR)
    matches.to_parquet(DATA_DIR / "matches.parquet",         index=False)
    events_clean.to_parquet(DATA_DIR / "events_clean.parquet", index=False)
    lineups.to_parquet(DATA_DIR / "lineups.parquet",         index=False)
    spadl.to_parquet(DATA_DIR / "spadl_actions.parquet",     index=False)
    shots_xg.to_parquet(DATA_DIR / "shots_for_xg.parquet",  index=False)
    print("✅ All data saved to data/")


def load_all() -> dict:
    return {
        "matches":       pd.read_parquet(DATA_DIR / "matches.parquet"),
        "events_clean":  pd.read_parquet(DATA_DIR / "events_clean.parquet"),
        "lineups":       pd.read_parquet(DATA_DIR / "lineups.parquet"),
        "spadl":         pd.read_parquet(DATA_DIR / "spadl_actions.parquet"),
        "shots_for_xg":  pd.read_parquet(DATA_DIR / "shots_for_xg.parquet"),
    }


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

def run():
    print("=" * 60)
    print("📊 PIPELINE STEP 1: Data Loading & Preprocessing")
    print("=" * 60)

    matches       = load_matches()
    events_df, lineups_df = load_all_events(matches)
    events_clean  = clean_events(events_df)
    lineups_df    = add_uuid_column(lineups_df, "uuid",
                        based_on=["match_id", "player_id"]
                        if "player_id" in lineups_df.columns else None)
    spadl         = build_spadl(events_clean)
    shots_xg      = build_shots_for_xg(events_clean)

    save_all(matches, events_clean, lineups_df, spadl, shots_xg)

    print("\n✅ Step 1 Complete!")
    print(f"   Matches      : {len(matches)}")
    print(f"   Events       : {len(events_clean):,}")
    print(f"   SPADL Actions: {len(spadl):,}")
    print(f"   Shots for xG : {len(shots_xg):,}")

    return {
        "matches":      matches,
        "events_clean": events_clean,
        "lineups":      lineups_df,
        "spadl":        spadl,
        "shots_xg":     shots_xg,
    }


if __name__ == "__main__":
    run()
