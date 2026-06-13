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


def compute_defensive_action_features(events_clean: pd.DataFrame) -> pd.DataFrame:
    intercept = events_clean[events_clean["event_type"] == "Interception"]\
        .groupby(["match_id","player_id"]).agg(interceptions=("event_type","count")).reset_index()
    clear = events_clean[events_clean["event_type"] == "Clearance"]\
        .groupby(["match_id","player_id"]).agg(clearances=("event_type","count")).reset_index()
    block = events_clean[events_clean["event_type"] == "Block"]\
        .groupby(["match_id","player_id"]).agg(blocks=("event_type","count")).reset_index()
    duel = events_clean[events_clean["event_type"] == "Duel"]\
        .groupby(["match_id","player_id"]).agg(duels_total=("event_type","count")).reset_index()

    feat = intercept.merge(clear, on=["match_id","player_id"], how="outer")\
                    .merge(block,  on=["match_id","player_id"], how="outer")\
                    .merge(duel,   on=["match_id","player_id"], how="outer").fillna(0)
    return feat


def _ts_to_mins(val):
    """Convert 'MM:SS' string to minutes float. Returns 0 if None/invalid."""
    if val is None:
        return 0
    try:
        parts = str(val).split(":")
        return int(parts[0]) + int(parts[1]) / 60.0 if len(parts) >= 2 else float(parts[0])
    except (ValueError, IndexError, TypeError):
        return 0

def compute_minutes_played(lineups: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in lineups.iterrows():
        positions = r.get("positions")
        if positions is None or not isinstance(positions, (list, np.ndarray)):
            continue
        total = 0.0
        for seg in positions:
            if isinstance(seg, dict):
                fr = _ts_to_mins(seg.get("from"))
                to = seg.get("to")
                if to is not None:
                    mins = _ts_to_mins(to)
                else:
                    mins = 90.0  # played until end of match
                total += max(0, mins - fr)
        rows.append({"match_id": r["match_id"], "player_id": r["player_id"], "minutes_played": round(total, 1)})
    return pd.DataFrame(rows).drop_duplicates(subset=["match_id","player_id"])


def compute_key_pass_features(events_clean: pd.DataFrame) -> pd.DataFrame:
    events = events_clean[events_clean["player_id"].notna()].sort_values(["match_id","event_index"]).copy()
    events["shot_idx"] = events.groupby("match_id")["event_index"].shift(-1)

    key_pass_records = []
    assist_records = []

    for (mid, team), grp in events.groupby(["match_id","team_name"]):
        grp = grp.sort_values("event_index")
        pass_indices = grp[grp["event_type"] == "Pass"].index
        shot_indices = grp[grp["event_type"] == "Shot"].index

        for si in shot_indices:
            prior_passes = pass_indices[pass_indices < si]
            if len(prior_passes) == 0:
                continue
            last_pass_idx = prior_passes[-1]
            shot_row = grp.loc[si]
            pass_row = grp.loc[last_pass_idx]
            key_pass_records.append({
                "match_id": mid,
                "player_id": pass_row["player_id"],
            })
            if shot_row["shot_outcome"] == "Goal":
                assist_records.append({
                    "match_id": mid,
                    "player_id": pass_row["player_id"],
                })

    kp_df = pd.DataFrame(key_pass_records) if key_pass_records else pd.DataFrame(columns=["match_id","player_id"])
    ast_df = pd.DataFrame(assist_records) if assist_records else pd.DataFrame(columns=["match_id","player_id"])

    key_passes = kp_df.groupby(["match_id","player_id"]).agg(
        key_passes=("player_id","count")
    ).reset_index() if len(kp_df) > 0 else pd.DataFrame(columns=["match_id","player_id","key_passes"])

    assist_passes = ast_df.groupby(["match_id","player_id"]).agg(
        assists=("player_id","count")
    ).reset_index() if len(ast_df) > 0 else pd.DataFrame(columns=["match_id","player_id","assists"])

    key_passes["chances_created"] = key_passes["key_passes"]

    result = key_passes.merge(assist_passes, on=["match_id","player_id"], how="outer")
    return result.fillna(0)


def compute_gk_features(events_clean: pd.DataFrame, lineups: pd.DataFrame) -> pd.DataFrame:
    # Goal Keeper events = saves
    gk_events = events_clean[events_clean["event_type"] == "Goal Keeper"].copy()
    saves = gk_events.groupby(["match_id","player_id"]).agg(
        saves=("event_type","count")
    ).reset_index()

    # Compute opponent shots and goals while GK is on pitch
    gk_mins = compute_minutes_played(lineups)
    gk_mins = gk_mins[gk_mins["minutes_played"] >= 1].copy()

    # Get GK identity: which players are GK in each match
    gk_players = lineups[lineups["player_id"].notna()].copy()
    def _is_gk(pos):
        if pos is None or not isinstance(pos, (list, np.ndarray)):
            return False
        return any(isinstance(seg, dict) and seg.get("position") == "Goalkeeper" for seg in pos)
    if "positions" in gk_players.columns:
        gk_players["is_gk"] = gk_players["positions"].apply(_is_gk)
    else:
        gk_players["is_gk"] = False
    gk_ids = gk_players[gk_players["is_gk"] == True][["match_id","player_id"]].drop_duplicates()

    # Opponent shots while GK is on pitch
    shots = events_clean[events_clean["event_type"] == "Shot"].copy()
    shots["is_on_target"] = shots["shot_outcome"].isin(["Goal","Saved","Saved To Post"]).astype(int)
    shots["is_goal"] = (shots["shot_outcome"] == "Goal").astype(int)

    rows = []
    for _, gk in gk_ids.iterrows():
        mid, gid = gk["match_id"], gk["player_id"]
        gk_team = gk_players[gk_players["player_id"] == gid]["team_name"].values
        if not len(gk_team):
            continue
        gk_team = gk_team[0]
        opp_shots = shots[(shots["match_id"] == mid) & (shots["team_name"] != gk_team)]
        if len(gk_mins[(gk_mins["match_id"] == mid) & (gk_mins["player_id"] == gid)]):
            rows.append({
                "match_id": mid,
                "player_id": gid,
                "shots_faced": int(opp_shots["is_on_target"].sum()),
                "goals_conceded": int(opp_shots["is_goal"].sum()),
                "xG_conceded": round(float(opp_shots["shot_xg"].sum()), 4),
            })

    opp_feat = pd.DataFrame(rows) if rows else pd.DataFrame(columns=[
        "match_id","player_id","shots_faced","goals_conceded","xG_conceded"
    ])

    feat = saves.merge(opp_feat, on=["match_id","player_id"], how="outer").fillna(0)
    feat["save_pct"] = (
        (feat["shots_faced"] - feat["goals_conceded"]) / feat["shots_faced"].replace(0, np.nan) * 100
    ).round(2).fillna(0)
    feat["goals_prevented"] = (feat["xG_conceded"] - feat["goals_conceded"]).round(4)
    return feat


def merge_all_features(events_clean: pd.DataFrame, lineups: pd.DataFrame = None) -> pd.DataFrame:
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
        compute_defensive_action_features(events_clean),
    ]

    # Key passes and assists
    kp = compute_key_pass_features(events_clean)
    dfs.append(kp)

    # GK features require lineups
    if lineups is not None:
        gk = compute_gk_features(events_clean, lineups)
        dfs.append(gk)
        mp = compute_minutes_played(lineups)
        dfs.append(mp)

    result = base.copy()
    for df in dfs:
        result = result.merge(df, on=["match_id","player_id"], how="left")

    count_cols = [
        "total_passes","complete_passes","progressive_passes","passes_under_pressure",
        "total_shots","goals","shots_on_target","total_pressures","pressure_regains",
        "total_carries","progressive_carries","total_dribbles","successful_dribbles",
        "total_actions","fouls_committed","fouls_won","yellow_cards","red_cards",
        "ball_receipts","miscontrols","interceptions","clearances","blocks",
        "saves","shots_faced","goals_conceded","duels_total",
        "key_passes","assists","chances_created",
    ]
    for col in count_cols:
        if col in result.columns:
            result[col] = result[col].fillna(0).astype(int)

    float_cols = ["minutes_played","xG_conceded","goals_prevented","save_pct"]
    for col in float_cols:
        if col in result.columns:
            result[col] = result[col].fillna(0)

    result = add_uuid_column(result, "uuid", based_on=["match_id","player_id"])
    print(f"✅ computed_features: {result.shape}")
    return result


def run():
    print("=" * 60)
    print("⚙️  PIPELINE STEP 2: Feature Engineering")
    print("=" * 60)

    events_clean = pd.read_parquet(DATA_DIR / "events_clean.parquet")
    lineups_path = DATA_DIR / "lineups.parquet"
    lineups = pd.read_parquet(lineups_path) if lineups_path.exists() else None
    computed     = merge_all_features(events_clean, lineups=lineups)

    ensure_dirs(DATA_DIR)
    computed.to_parquet(DATA_DIR / "computed_features.parquet", index=False)
    computed.to_csv(DATA_DIR / "computed_features.csv", index=False)

    print(f"\n✅ Step 2 Complete!")
    print(f"   Player-match pairs : {len(computed):,}")
    print(f"   Features           : {len(computed.columns)}")
    return computed


if __name__ == "__main__":
    run()
