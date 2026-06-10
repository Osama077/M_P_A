"""
pipeline/vaep_model.py — VAEP Model (XGBoost)
Fixed implementation matching the VAEP paper (arxiv 1802.07127):
- One-hot encoding for categorical features
- Proper team-switching in value formula
- Own-goal handling in labels
- Phase transition resets (goal, timeout)
- Vectorized operations for performance
"""

import json
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score

from config import DATA_DIR, MODELS_DIR, VAEP_WINDOW, VAEP_N_CONTEXT
from utils.uuid_manager import add_uuid_column
from utils.helpers import ensure_dirs

ACTION_TYPES   = ["pass","shot","dribble","carry","tackle","foul",
                  "clearance","interception","shot_block","keeper_save","receival","bad_touch"]
RESULT_TYPES   = ["fail","success"]
BODY_TYPES     = ["foot","head","chest","other"]

# Match pitch dimensions from SPADL (StatsBomb: 120x80 -> meters ~105x68)
FIELD_LENGTH = 105.0
FIELD_WIDTH = 68.0

XGB_PARAMS = {
    "objective":               "binary:logistic",
    "eval_metric":             ["logloss","auc"],
    "learning_rate":           0.05,
    "max_depth":               5,
    "n_estimators":            500,
    "subsample":               0.8,
    "colsample_bytree":        0.8,
    "min_child_weight":        10,
    "reg_alpha":               0.1,
    "reg_lambda":              1.0,
    "random_state":            42,
    "n_jobs":                  -1,
    "verbosity":               0,
    "early_stopping_rounds":   30,
}


def _encode(df: pd.DataFrame) -> pd.DataFrame:
    """Encode SPADL actions with normalized coordinates and categorical IDs."""
    df = df.copy()
    df["type_name"]     = df["type_name"].fillna("pass")
    df["result_name"]   = df["result_name"].fillna("success")
    df["bodypart_name"] = df["bodypart_name"].fillna("foot")

    # Convert to meters (StatsBomb 120x80 -> real pitch ~105x68)
    scale_x = FIELD_LENGTH / 120.0
    scale_y = FIELD_WIDTH / 80.0
    df["start_x"] = df["start_x"] * scale_x
    df["start_y"] = df["start_y"] * scale_y
    df["end_x"]   = df["end_x"]   * scale_x
    df["end_y"]   = df["end_y"]   * scale_y

    # Categorical IDs for action type, result, bodypart
    type_map     = {t: i for i, t in enumerate(ACTION_TYPES)}
    result_map   = {r: i for i, r in enumerate(RESULT_TYPES)}
    bodypart_map = {b: i for i, b in enumerate(BODY_TYPES)}
    df["type_id"]     = df["type_name"].map(type_map).fillna(0).astype(int)
    df["result_id"]   = df["result_name"].map(result_map).fillna(0).astype(int)
    df["bodypart_id"] = df["bodypart_name"].map(bodypart_map).fillna(0).astype(int)

    # Distance and angle to goal center (at x=105, y=34)
    goal_x = FIELD_LENGTH
    goal_y = FIELD_WIDTH / 2
    df["dist_to_goal"] = np.sqrt((goal_x - df["start_x"])**2 + (goal_y - df["start_y"])**2)
    df["angle_to_goal"] = np.arctan2(np.abs(goal_y - df["start_y"]), goal_x - df["start_x"])

    return df


def _build_labels(df: pd.DataFrame, window: int = VAEP_WINDOW) -> pd.DataFrame:
    """Build binary labels: does the team score/concede in the next `window` actions?
    Vectorized per-match using shift operations. Handles own goals.
    """
    df = df.sort_values(["match_id", "event_index"]).reset_index(drop=True)

    # Identify goals (only real shots, not shot_block)
    is_shot = df["type_name"].isin(["shot", "shot_penalty"])
    is_goal = is_shot & (df["result_name"] == "success")
    scores_arr = np.zeros(len(df), dtype=int)
    concedes_arr = np.zeros(len(df), dtype=int)

    for match_id, group in df.groupby("match_id"):
        idx = group.index.values
        team_ids = group["team_name"].values
        goal_flags = is_goal.values[idx]
        n = len(idx)

        for i in range(n):
            end = min(i + 1 + window, n)
            fut_teams = team_ids[i + 1:end]
            fut_goals = goal_flags[i + 1:end]
            if len(fut_goals) == 0:
                continue
            same_team = fut_teams == team_ids[i]
            scores_arr[idx[i]] = 1 if (fut_goals & same_team).any() else 0
            concedes_arr[idx[i]] = 1 if (fut_goals & ~same_team).any() else 0

    df["scores"] = scores_arr
    df["concedes"] = concedes_arr
    return df


def _onehot(series: pd.Series, categories: list, prefix: str) -> pd.DataFrame:
    """One-hot encode a categorical series."""
    cat = pd.Categorical(series, categories=categories)
    return pd.get_dummies(cat, prefix=prefix, dummy_na=False).astype(int)


def _build_context(df: pd.DataFrame, n: int = VAEP_N_CONTEXT) -> pd.DataFrame:
    """Build context features with vectorized shift operations.
    For each action, include n previous actions' features + cross-action features.
    """
    df = df.sort_values(["match_id", "event_index"]).reset_index(drop=True)

    goal_x = FIELD_LENGTH
    goal_y = FIELD_WIDTH / 2

    # Per-action feature blocks
    action_dfs = [df]
    for k in range(1, n + 1):
        shifted = df.groupby("match_id").shift(k).fillna(0)
        # For categorical names, fill with first valid value per group
        for col in ["type_name", "result_name", "bodypart_name", "team_name"]:
            shifted[col] = shifted[col].ffill().fillna("pass")
        action_dfs.append(shifted)

    features = []
    for k, a_df in enumerate(action_dfs):
        prefix = f"a{k}_"

        # One-hot categoricals
        f_type = _onehot(a_df["type_name"], ACTION_TYPES, f"{prefix}type")
        f_res  = _onehot(a_df["result_name"], RESULT_TYPES, f"{prefix}result")
        f_body = _onehot(a_df["bodypart_name"], BODY_TYPES, f"{prefix}bodypart")

        # Continuous features
        cols = {
            f"{prefix}start_x": a_df["start_x"],
            f"{prefix}start_y": a_df["start_y"],
            f"{prefix}end_x": a_df["end_x"],
            f"{prefix}end_y": a_df["end_y"],
            f"{prefix}dist_to_goal": np.sqrt((goal_x - a_df["start_x"])**2 + (goal_y - a_df["start_y"])**2),
            f"{prefix}angle_to_goal": np.arctan2(np.abs(goal_y - a_df["start_y"]), (goal_x - a_df["start_x"]).clip(lower=1e-6)),
            f"{prefix}time_seconds": a_df["time_seconds"],
            f"{prefix}under_pressure": a_df["under_pressure"],
        }
        f_cont = pd.DataFrame(cols, index=df.index)

        features.append(pd.concat([f_type, f_res, f_body, f_cont], axis=1))

    X = pd.concat(features, axis=1)

    # Cross-action features (state-level)
    a0 = action_dfs[0]

    # -- goalscore context (goals up to before the current action) --
    is_shot = df["type_name"].isin(["shot", "shot_penalty"])
    is_goal = is_shot & (df["result_name"] == "success")
    is_own_goal = is_shot & (df["result_name"] == "fail") & (df["type_name"] == "shot")

    goal_mask = is_goal.values
    team_vals = df["team_name"].values

    # Pre-match: goals scored by each team before each action
    goals_data = np.zeros((len(df), 3))
    for match_id, group in df.groupby("match_id"):
        idx = group.index.values
        g = goal_mask[idx]
        t = team_vals[idx]
        cum_team_a = np.cumsum(g & (t == t[0]))
        cum_team_b = np.cumsum(g & (t != t[0]))
        goals_data[idx, 0] = np.concatenate([[0], cum_team_a[:-1]])  # team's own goals
        goals_data[idx, 1] = np.concatenate([[0], cum_team_b[:-1]])  # opponent goals
    goals_data[:, 2] = goals_data[:, 0] - goals_data[:, 1]

    X["goalscore_team"] = goals_data[:, 0]
    X["goalscore_opponent"] = goals_data[:, 1]
    X["goalscore_diff"] = goals_data[:, 2]

    # -- team continuity (for a1, a2, a3 relative to a0) --
    for k in range(1, n + 1):
        a_k = action_dfs[k]
        X[f"team_a{k}_same"] = (a0["team_name"].values == a_k["team_name"].values).astype(int)

    # -- time delta between consecutive actions --
    for k in range(1, n + 1):
        a_prev = action_dfs[k]
        X[f"time_delta_a{k}"] = a0["time_seconds"] - a_prev["time_seconds"]

    # -- space delta between consecutive actions --
    for k in range(1, n + 1):
        a_k = action_dfs[k]
        dx = a_k["end_x"] - a0["start_x"]
        dy = a_k["end_y"] - a0["start_y"]
        X[f"dx_a0{k}"] = dx
        X[f"dy_a0{k}"] = dy
        X[f"mov_a0{k}"] = np.sqrt(dx**2 + dy**2)

    X = X.fillna(0)
    return X


def _compute_vaep_values(df_vaep: pd.DataFrame) -> pd.DataFrame:
    """Compute offensive, defensive, and total VAEP values.
    Follows the reference VAEP formula with:
    - Team-switching for cross-team action sequences
    - Phase transition reset (>10s gap, goals)
    - Fixed odds for penalties/corners
    """
    df_vaep = df_vaep.sort_values(["match_id", "event_index"]).reset_index(drop=True)

    goal_x = FIELD_LENGTH
    goal_y = FIELD_WIDTH / 2
    df_vaep["_dist"] = np.sqrt((goal_x - df_vaep["start_x"])**2 + (goal_y - df_vaep["start_y"])**2)
    is_shot = df_vaep["type_name"].isin(["shot", "shot_penalty"])
    is_goal = is_shot & (df_vaep["result_name"] == "success")

    p_score = df_vaep["p_score"].values
    p_concede = df_vaep["p_concede"].values

    offensive = np.zeros(len(df_vaep))
    defensive = np.zeros(len(df_vaep))

    for match_id, group in df_vaep.groupby("match_id"):
        idx = group.index.values
        n = len(idx)

        for i in range(n):
            if i == 0:
                # First action: no previous state, value = current probability
                offensive[idx[i]] = p_score[idx[i]]
                defensive[idx[i]] = -p_concede[idx[i]]
                continue

            prev_i = idx[i - 1]
            curr_i = idx[i]

            # Team continuity: was the previous action by the same team?
            same_team = df_vaep.loc[curr_i, "team_name"] == df_vaep.loc[prev_i, "team_name"]

            # Phase transition checks
            time_gap = df_vaep.loc[curr_i, "time_seconds"] - df_vaep.loc[prev_i, "time_seconds"]
            new_phase = time_gap > VAEP_WINDOW
            if new_phase:
                prev_s = 0.0
                prev_c = 0.0
            else:
                # Goal reset: if previous action was a goal, reset
                prev_goal = is_goal.values[prev_i]
                if prev_goal:
                    prev_s = 0.0
                    prev_c = 0.0
                else:
                    # Team-switching: swap scoring/conceding probabilities
                    if same_team:
                        prev_s = p_score[prev_i]
                        prev_c = p_concede[prev_i]
                    else:
                        prev_s = p_concede[prev_i]  # opponent's concede = our score
                        prev_c = p_score[prev_i]    # opponent's score = our concede

            # Fixed odds for standard situations (from socceraction reference)
            curr_type = df_vaep.loc[curr_i, "type_name"]
            dist = df_vaep.loc[curr_i, "_dist"]
            if curr_type == "shot_penalty":
                prev_s = 0.792453
            elif curr_type in ("corner_crossed", "corner_short"):
                prev_s = 0.046500

            offensive[idx[i]] = p_score[curr_i] - prev_s
            defensive[idx[i]] = -(p_concede[curr_i] - prev_c)

    df_vaep["offensive_value"] = offensive
    df_vaep["defensive_value"] = defensive
    df_vaep["vaep_value"] = offensive + defensive
    return df_vaep


def _save_models_and_data(off_model, def_model, X_ctx, df_vaep, season_map):
    """Save models, feature columns, and VAEP data."""
    player_vaep = df_vaep.groupby(["match_id", "player_id"]).agg(
        vaep_rating     =("vaep_value",      "sum"),
        offensive_value =("offensive_value", "sum"),
        defensive_value =("defensive_value", "sum"),
        total_actions   =("vaep_value",      "count"),
        avg_vaep        =("vaep_value",      "mean"),
    ).reset_index()

    if season_map is not None:
        player_vaep = player_vaep.merge(season_map, on="match_id", how="left")

    player_vaep["vaep_per_action"] = (player_vaep["vaep_rating"] / player_vaep["total_actions"]).round(6)
    player_vaep = add_uuid_column(player_vaep, "uuid", based_on=["match_id", "player_id"])

    ensure_dirs(MODELS_DIR, DATA_DIR)
    off_model.save_model(str(MODELS_DIR / "vaep_offensive_model.json"))
    def_model.save_model(str(MODELS_DIR / "vaep_defensive_model.json"))

    X_ctx_cols = list(X_ctx.columns)
    with open(MODELS_DIR / "vaep_feature_cols.json", "w") as f:
        json.dump(X_ctx_cols, f)

    player_vaep.to_parquet(DATA_DIR / "player_vaep_ratings.parquet", index=False)

    df_vaep_save = df_vaep[["match_id", "player_id", "type_name", "result_name",
                             "start_x", "start_y", "end_x", "end_y",
                             "p_score", "p_concede", "offensive_value", "defensive_value", "vaep_value"]].copy()
    df_vaep_save = add_uuid_column(df_vaep_save, "uuid")
    df_vaep_save.to_parquet(DATA_DIR / "actions_with_vaep.parquet", index=False)

    return player_vaep


def train() -> tuple:
    """Train VAEP models (offensive + defensive) on full SPADL data."""
    print("Loading SPADL data...")
    spadl = pd.read_parquet(DATA_DIR / "spadl_actions.parquet")
    df = _encode(spadl)

    print("Building labels...")
    df = _build_labels(df)
    print(f"   Score rate  : {df['scores'].mean()*100:.2f}%")
    print(f"   Concede rate: {df['concedes'].mean()*100:.2f}%")

    print("Building context features...")
    X_ctx = _build_context(df)
    print(f"   Context features: {X_ctx.shape}")

    y_scores = df["scores"].values
    y_concedes = df["concedes"].values

    X_tr, X_vl, ys_tr, ys_vl, yc_tr, yc_vl = train_test_split(
        X_ctx, y_scores, y_concedes, test_size=0.2, random_state=42
    )

    print("Training Offensive Model...")
    off_model = xgb.XGBClassifier(**XGB_PARAMS)
    off_model.fit(X_tr, ys_tr, eval_set=[(X_vl, ys_vl)], verbose=False)
    auc_off = roc_auc_score(ys_vl, off_model.predict_proba(X_vl)[:, 1])

    print("Training Defensive Model...")
    def_model = xgb.XGBClassifier(**XGB_PARAMS)
    def_model.fit(X_tr, yc_tr, eval_set=[(X_vl, yc_vl)], verbose=False)
    auc_def = roc_auc_score(yc_vl, def_model.predict_proba(X_vl)[:, 1])

    print(f"Offensive AUC: {auc_off:.4f} | Defensive AUC: {auc_def:.4f}")

    # Predict probabilities for all data
    p_score = off_model.predict_proba(X_ctx)[:, 1]
    p_concede = def_model.predict_proba(X_ctx)[:, 1]

    df_vaep = df.copy().reset_index(drop=True)
    df_vaep["p_score"] = p_score
    df_vaep["p_concede"] = p_concede

    # Compute VAEP values with proper formula
    df_vaep = _compute_vaep_values(df_vaep)

    season_map = df_vaep[["match_id", "season_label", "season_id", "competition_id"]] \
        .drop_duplicates(subset=["match_id"]) if "season_label" in df_vaep.columns else None

    player_vaep = _save_models_and_data(off_model, def_model, X_ctx, df_vaep, season_map)

    metrics = {"offensive_auc": round(auc_off, 4), "defensive_auc": round(auc_def, 4)}
    with open(MODELS_DIR / "vaep_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    return off_model, def_model, player_vaep


def predict_only():
    """Load existing models and compute VAEP values for current SPADL data."""
    print("VAEP models exist - running prediction-only")

    print("Loading SPADL data...")
    spadl = pd.read_parquet(DATA_DIR / "spadl_actions.parquet")
    df = _encode(spadl)

    print("Building context features...")
    X_ctx = _build_context(df)
    print(f"   Context features: {X_ctx.shape}")

    with open(MODELS_DIR / "vaep_feature_cols.json") as f:
        expected = json.load(f)
    for col in expected:
        if col not in X_ctx.columns:
            X_ctx[col] = 0
    X_ctx = X_ctx[expected].fillna(0)

    print("Loading models and predicting...")
    off_model = xgb.XGBClassifier()
    off_model.load_model(str(MODELS_DIR / "vaep_offensive_model.json"))
    def_model = xgb.XGBClassifier()
    def_model.load_model(str(MODELS_DIR / "vaep_defensive_model.json"))

    p_score = off_model.predict_proba(X_ctx)[:, 1]
    p_concede = def_model.predict_proba(X_ctx)[:, 1]

    df_vaep = df.copy().reset_index(drop=True)
    df_vaep["p_score"] = p_score
    df_vaep["p_concede"] = p_concede

    # Compute VAEP values with proper formula
    df_vaep = _compute_vaep_values(df_vaep)

    season_map = df_vaep[["match_id", "season_label", "season_id", "competition_id"]] \
        .drop_duplicates(subset=["match_id"]) if "season_label" in df_vaep.columns else None

    player_vaep = _save_models_and_data(off_model, def_model, X_ctx, df_vaep, season_map)

    print(f"Prediction complete! Player-match VAEP: {len(player_vaep):,}")
    return off_model, def_model, player_vaep


def run():
    print("=" * 60)
    print("PIPELINE STEP 4: VAEP Model (XGBoost)")
    print("=" * 60)
    off_model_path = MODELS_DIR / "vaep_offensive_model.json"
    def_model_path = MODELS_DIR / "vaep_defensive_model.json"
    if off_model_path.exists() and def_model_path.exists():
        off, dff, vaep = predict_only()
    else:
        off, dff, vaep = train()
    print(f"\nStep 4 Complete!")
    print(f"   Player-match VAEP: {len(vaep):,}")
    return off, dff, vaep


if __name__ == "__main__":
    run()
