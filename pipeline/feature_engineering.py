"""
pipeline/feature_engineering.py — Feature Engineering
يقابل Notebook 02
"""

import pandas as pd
import numpy as np
import warnings
from config import DATA_DIR
from utils.uuid_manager import add_uuid_column
from utils.helpers import normalize_to_score, ensure_dirs

warnings.filterwarnings("ignore")


def compute_passing_features(events_clean: pd.DataFrame) -> pd.DataFrame:
    pass_events = events_clean[events_clean["event_type"] == "Pass"].copy()
    pass_events["is_complete"] = (
        pass_events["pass_outcome"].isna() |
        (pass_events["pass_outcome"] == "Complete")
    ).astype(int)

    feat = pass_events.groupby(["match_id", "player_id"]).agg(
        total_passes          =("event_type",          "count"),
        complete_passes       =("is_complete",          "sum"),
        progressive_passes    =("is_progressive_pass",  "sum"),
        passes_under_pressure =("under_pressure",       "sum"),
        avg_pass_length       =("pass_length",          "mean"),
    ).reset_index()

    feat["pass_accuracy"] = (
        feat["complete_passes"] / feat["total_passes"] * 100
    ).round(2)
    return feat


def compute_shooting_features(events_clean: pd.DataFrame) -> pd.DataFrame:
    shot_events = events_clean[events_clean["event_type"] == "Shot"].copy()
    shot_events["is_goal"]      = (shot_events["shot_outcome"] == "Goal").astype(int)
    shot_events["is_on_target"] = shot_events["shot_outcome"].isin(
        ["Goal", "Saved", "Saved To Post"]
    ).astype(int)

    feat = shot_events.groupby(["match_id", "player_id"]).agg(
        total_shots     =("event_type",      "count"),
        goals           =("is_goal",          "sum"),
        shots_on_target =("is_on_target",     "sum"),
        total_xg        =("shot_xg",          "sum"),
        avg_distance    =("distance_to_goal", "mean"),
    ).reset_index()

    feat["shot_accuracy"]      = (feat["shots_on_target"] / feat["total_shots"] * 100).round(2)
    feat["xg_per_shot"]        = (feat["total_xg"] / feat["total_shots"]).round(4)
    feat["xg_overperformance"] = (feat["goals"] - feat["total_xg"]).round(4)
    return feat


def compute_positioning_features(events_clean: pd.DataFrame) -> pd.DataFrame:
    loc = events_clean[
        events_clean["location_x"].notna() & events_clean["player_id"].notna()
    ].copy()

    feat = loc.groupby(["match_id", "player_id"]).agg(
        avg_position_x =("location_x", "mean"),
        avg_position_y =("location_y", "mean"),
        std_position_x =("location_x", "std"),
        std_position_y =("location_y", "std"),
    ).reset_index()

    feat["position_deviation"]  = np.sqrt(
        feat["std_position_x"]**2 + feat["std_position_y"]**2
    ).round(2)
    feat["attacking_tendency"] = (feat["avg_position_x"] / 120 * 100).round(2)
    return feat


def compute_pressing_features(events_clean: pd.DataFrame) -> pd.DataFrame:
    pressure = events_clean[events_clean["event_type"] == "Pressure"].copy()

    feat = pressure.groupby(["match_id", "player_id"]).agg(
        total_pressures    =("event_type", "count"),
        avg_pressure_dur   =("duration",   "mean"),
        total_pressure_dur =("duration",   "sum"),
    ).reset_index()

    # FIX: pressure_regains counts only Pressure events where counterpress == 1,
    # not ALL events with counterpress. This prevents pressing_efficiency > 100%.
    cp = pressure[pressure["counterpress"] == 1].groupby(
        ["match_id", "player_id"]
    ).agg(pressure_regains=("event_type", "count")).reset_index()

    feat = feat.merge(cp, on=["match_id", "player_id"], how="left")
    feat["pressure_regains"]    = feat["pressure_regains"].fillna(0).astype(int)
    feat["pressing_efficiency"] = (
        feat["pressure_regains"] / feat["total_pressures"].replace(0, np.nan) * 100
    ).round(2).fillna(0)
    return feat


def compute_movement_features(events_clean: pd.DataFrame) -> pd.DataFrame:
    carry = events_clean[events_clean["event_type"] == "Carry"].copy()
    carry["carry_distance"] = np.sqrt(
        (carry["carry_end_x"] - carry["location_x"])**2 +
        (carry["carry_end_y"] - carry["location_y"])**2
    )
    carry["is_progressive_carry"] = (
        carry["carry_end_x"] > carry["location_x"] + 5
    ).astype(int)

    carry_feat = carry.groupby(["match_id", "player_id"]).agg(
        total_carries          =("event_type",            "count"),
        total_carry_distance   =("carry_distance",        "sum"),
        avg_carry_distance     =("carry_distance",        "mean"),
        progressive_carries    =("is_progressive_carry",  "sum"),
    ).reset_index()

    dribble = events_clean[events_clean["event_type"] == "Dribble"].copy()
    dribble["is_complete"] = (dribble["dribble_outcome"] == "Complete").astype(int)

    drib_feat = dribble.groupby(["match_id", "player_id"]).agg(
        total_dribbles      =("event_type",  "count"),
        successful_dribbles =("is_complete", "sum"),
    ).reset_index()
    drib_feat["dribble_success_rate"] = (
        drib_feat["successful_dribbles"] / drib_feat["total_dribbles"] * 100
    ).round(2)

    feat = carry_feat.merge(drib_feat, on=["match_id", "player_id"], how="outer").fillna(0)
    return feat


def compute_physical_features(events_clean: pd.DataFrame) -> pd.DataFrame:
    # Estimate distance from consecutive event positions
    # StatsBomb pitch: 120x80 units -> FIFA regulation: ~105m x 68m
    events = events_clean[
        events_clean["player_id"].notna() & events_clean["location_x"].notna()
    ].copy()
    events = events.sort_values(["match_id", "player_id", "event_index"])
    events["loc_x_m"] = events["location_x"] * 105.0 / 120.0
    events["loc_y_m"] = events["location_y"] * 68.0 / 80.0
    events["prev_x_m"] = events.groupby(["match_id", "player_id"])["loc_x_m"].shift(1)
    events["prev_y_m"] = events.groupby(["match_id", "player_id"])["loc_y_m"].shift(1)
    events["segment_dist"] = np.sqrt(
        (events["loc_x_m"] - events["prev_x_m"])**2 +
        (events["loc_y_m"] - events["prev_y_m"])**2
    )
    events["segment_dist"] = events["segment_dist"].where(events["segment_dist"] < 40, 0)

    dist = events.groupby(["match_id", "player_id"]).agg(
        distance_covered=("segment_dist", "sum")
    ).reset_index()
    # FIX: Remove undocumented * 5.0 multiplier — coordinates are already converted to meters
    dist["distance_covered"] = (dist["distance_covered"]).round(0)

    actions = events_clean[events_clean["player_id"].notna()].groupby(
        ["match_id", "player_id"]
    ).agg(total_actions=("event_type", "count")).reset_index()

    period_act = events_clean[
        events_clean["player_id"].notna() & events_clean["period"].isin([1, 2])
    ].groupby(["match_id", "player_id", "period"]).agg(
        actions=("event_type", "count")
    ).reset_index()

    p1 = period_act[period_act["period"] == 1][["match_id","player_id","actions"]]\
         .rename(columns={"actions": "actions_p1"})
    p2 = period_act[period_act["period"] == 2][["match_id","player_id","actions"]]\
         .rename(columns={"actions": "actions_p2"})

    drop = p1.merge(p2, on=["match_id","player_id"], how="outer").fillna(0)
    drop["activity_drop_2nd_half"] = (
        (drop["actions_p1"] - drop["actions_p2"]) /
        drop["actions_p1"].replace(0, np.nan) * 100
    ).round(2).fillna(0)

    # Relative intensity: actions per minute per period
    drop["intensity_p1"] = (drop["actions_p1"] / 45).round(2)
    drop["intensity_p2"] = (drop["actions_p2"] / 45).round(2)
    drop["intensity_drop_pct"] = (
        (drop["intensity_p1"] - drop["intensity_p2"]) /
        drop["intensity_p1"].replace(0, np.nan) * 100
    ).round(2).fillna(0)

    feat = actions.merge(dist,  on=["match_id","player_id"], how="left")\
                  .merge(drop[["match_id","player_id","actions_p1","actions_p2",
                               "activity_drop_2nd_half","intensity_p1","intensity_p2",
                               "intensity_drop_pct"]],
                         on=["match_id","player_id"], how="left").fillna(0)
    return feat


def compute_behavioral_features(events_clean: pd.DataFrame) -> pd.DataFrame:
    fouls   = events_clean[events_clean["event_type"] == "Foul Committed"]\
              .groupby(["match_id","player_id"]).agg(fouls_committed=("event_type","count")).reset_index()
    f_won   = events_clean[events_clean["event_type"] == "Foul Won"]\
              .groupby(["match_id","player_id"]).agg(fouls_won=("event_type","count")).reset_index()
    receipt = events_clean[events_clean["event_type"] == "Ball Receipt*"]\
              .groupby(["match_id","player_id"]).agg(ball_receipts=("event_type","count")).reset_index()
    misc    = events_clean[events_clean["event_type"] == "Miscontrol"]\
              .groupby(["match_id","player_id"]).agg(miscontrols=("event_type","count")).reset_index()

    yellow = pd.DataFrame(columns=["match_id","player_id","yellow_cards"])
    red    = pd.DataFrame(columns=["match_id","player_id","red_cards"])
    if "foul_card" in events_clean.columns:
        yellow = events_clean[events_clean["foul_card"] == "Yellow Card"]\
                 .groupby(["match_id","player_id"]).agg(yellow_cards=("event_type","count")).reset_index()
        red    = events_clean[events_clean["foul_card"].isin(["Red Card","Second Yellow"])]\
                 .groupby(["match_id","player_id"]).agg(red_cards=("event_type","count")).reset_index()

    feat = fouls.merge(f_won,   on=["match_id","player_id"], how="outer")\
                .merge(yellow,  on=["match_id","player_id"], how="outer")\
                .merge(red,     on=["match_id","player_id"], how="outer")\
                .merge(receipt, on=["match_id","player_id"], how="outer")\
                .merge(misc,    on=["match_id","player_id"], how="outer").fillna(0)

    # FIX: Players with 0 ball receipts get ball_retention_rate = NaN (neutral),
    # not 100 (which would reward never touching the ball).
    feat["ball_retention_rate"] = (
        (feat["ball_receipts"] - feat["miscontrols"]) /
        feat["ball_receipts"].replace(0, np.nan) * 100
    ).round(2)
    return feat


def merge_all_features(events_clean: pd.DataFrame) -> pd.DataFrame:
    print("🔄 Computing all features...")

    season_cols = [c for c in ["season_label","season_id","competition_id"]
                   if c in events_clean.columns]
    base_cols = ["match_id","player_id","player_name","team_name"] + season_cols
    base = events_clean[
        events_clean["player_id"].notna()
    ][base_cols].drop_duplicates()

    dfs = [
        compute_passing_features(events_clean),
        compute_shooting_features(events_clean),
        compute_positioning_features(events_clean),
        compute_pressing_features(events_clean),
        compute_movement_features(events_clean),
        compute_physical_features(events_clean),
        compute_behavioral_features(events_clean),
    ]

    result = base.copy()
    for df in dfs:
        result = result.merge(df, on=["match_id","player_id"], how="left")

    count_cols = [
        "total_passes","complete_passes","progressive_passes","passes_under_pressure",
        "total_shots","goals","shots_on_target","total_pressures","pressure_regains",
        "total_carries","progressive_carries","total_dribbles","successful_dribbles",
        "total_actions","fouls_committed","fouls_won","yellow_cards","red_cards",
        "ball_receipts","miscontrols",
    ]
    for col in count_cols:
        if col in result.columns:
            result[col] = result[col].fillna(0).astype(int)

    result = add_uuid_column(result, "uuid", based_on=["match_id","player_id"])
    print(f"✅ computed_features: {result.shape}")
    return result


def run():
    print("=" * 60)
    print("⚙️  PIPELINE STEP 2: Feature Engineering")
    print("=" * 60)

    events_clean = pd.read_parquet(DATA_DIR / "events_clean.parquet")
    computed     = merge_all_features(events_clean)

    ensure_dirs(DATA_DIR)
    computed.to_parquet(DATA_DIR / "computed_features.parquet", index=False)
    computed.to_csv(DATA_DIR / "computed_features.csv", index=False)

    print(f"\n✅ Step 2 Complete!")
    print(f"   Player-match pairs : {len(computed):,}")
    print(f"   Features           : {len(computed.columns)}")
    return computed


if __name__ == "__main__":
    run()
