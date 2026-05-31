"""
pipeline/vaep_model.py — VAEP Model (XGBoost)
يقابل Notebook 04
"""

import json
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, brier_score_loss

from config import DATA_DIR, MODELS_DIR, VAEP_WINDOW, VAEP_N_CONTEXT
from utils.uuid_manager import add_uuid_column
from utils.helpers import ensure_dirs

ACTION_TYPES   = ["pass","shot","dribble","carry","tackle","foul",
                  "clearance","interception","shot_block","keeper_save","receival","bad_touch"]
RESULT_TYPES   = ["success","fail"]
BODY_TYPES     = ["foot","head","chest","other"]
BASE_FEATURES  = ["type_id","result_id","bodypart_id",
                  "start_x_norm","start_y_norm","end_x_norm","end_y_norm",
                  "dist_to_goal","under_pressure"]

XGB_PARAMS = {
    "objective":            "binary:logistic",
    "eval_metric":          ["logloss","auc"],
    "learning_rate":        0.05,
    "max_depth":            5,
    "n_estimators":         500,
    "subsample":            0.8,
    "colsample_bytree":     0.8,
    "min_child_weight":     10,
    "reg_alpha":            0.1,
    "reg_lambda":           1.0,
    "random_state":         42,
    "n_jobs":               -1,
    "verbosity":            0,
}

XGB_EARLY_STOPPING = 30


def _encode(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["type_name"]     = df["type_name"].fillna("pass")
    df["result_name"]   = df["result_name"].fillna("success")
    df["bodypart_name"] = df["bodypart_name"].fillna("foot")

    df["type_id"]     = pd.Categorical(df["type_name"],     categories=ACTION_TYPES).codes
    df["result_id"]   = pd.Categorical(df["result_name"],   categories=RESULT_TYPES).codes
    df["bodypart_id"] = pd.Categorical(df["bodypart_name"], categories=BODY_TYPES).codes

    df["start_x_norm"] = df["start_x"] / 120
    df["start_y_norm"] = df["start_y"] / 80
    df["end_x_norm"]   = df["end_x"]   / 120
    df["end_y_norm"]   = df["end_y"]   / 80
    df["dist_to_goal"] = np.sqrt((1 - df["start_x_norm"])**2 + (0.5 - df["start_y_norm"])**2)
    return df


def _build_labels(df: pd.DataFrame, window: int = VAEP_WINDOW) -> pd.DataFrame:
    df = df.sort_values(["match_id","event_index"]).copy()
    df["is_goal_action"] = ((df["type_name"] == "shot") & (df["result_name"] == "success")).astype(int)

    scores, concedes = [], []
    for _, group in df.groupby("match_id"):
        group = group.reset_index(drop=True)
        n     = len(group)
        for i in range(n):
            ct   = group.iloc[i]["team_name"] if "team_name" in group.columns else group.iloc[i].get("team","")
            fut  = group.iloc[i+1: i+1+window]
            sc   = fut[(fut.get("team_name", fut.get("team","")) == ct) & (fut["is_goal_action"] == 1)]
            co   = fut[(fut.get("team_name", fut.get("team","")) != ct) & (fut["is_goal_action"] == 1)]
            scores.append(1 if len(sc) > 0 else 0)
            concedes.append(1 if len(co) > 0 else 0)

    df["scores"]   = scores
    df["concedes"] = concedes
    return df


def _build_context(df: pd.DataFrame, n: int = VAEP_N_CONTEXT) -> pd.DataFrame:
    rows = []
    for _, group in df.groupby("match_id"):
        group = group.sort_values("event_index").reset_index(drop=True)
        for i in range(len(group)):
            r = {}
            for feat in BASE_FEATURES:
                r[f"a0_{feat}"] = group.iloc[i][feat]
            for k in range(1, n + 1):
                for feat in BASE_FEATURES:
                    r[f"a{k}_{feat}"] = group.iloc[i-k][feat] if i - k >= 0 else 0
            rows.append(r)
    return pd.DataFrame(rows)


def train() -> tuple:
    print("🔄 Loading SPADL data...")
    spadl = pd.read_parquet(DATA_DIR / "spadl_actions.parquet")
    df    = _encode(spadl)

    print("🔄 Building labels...")
    df    = _build_labels(df)
    print(f"   Score rate  : {df['scores'].mean()*100:.2f}%")
    print(f"   Concede rate: {df['concedes'].mean()*100:.2f}%")

    print("🔄 Building context features...")
    X_ctx = _build_context(df)

    y_scores  = df["scores"].values
    y_concedes= df["concedes"].values

    X_tr, X_vl, ys_tr, ys_vl, yc_tr, yc_vl = train_test_split(
        X_ctx, y_scores, y_concedes, test_size=0.2, random_state=42
    )

    print("🔄 Training Offensive Model...")
    off_model = xgb.XGBClassifier(**XGB_PARAMS)
    off_model.fit(X_tr, ys_tr, eval_set=[(X_vl, ys_vl)], verbose=False,
                  early_stopping_rounds=XGB_EARLY_STOPPING)
    auc_off   = roc_auc_score(ys_vl, off_model.predict_proba(X_vl)[:,1])

    print("🔄 Training Defensive Model...")
    def_model = xgb.XGBClassifier(**XGB_PARAMS)
    def_model.fit(X_tr, yc_tr, eval_set=[(X_vl, yc_vl)], verbose=False,
                  early_stopping_rounds=XGB_EARLY_STOPPING)
    auc_def   = roc_auc_score(yc_vl, def_model.predict_proba(X_vl)[:,1])

    print(f"✅ Offensive AUC: {auc_off:.4f} | Defensive AUC: {auc_def:.4f}")

    # VAEP calculation
    p_score   = off_model.predict_proba(X_ctx)[:,1]
    p_concede = def_model.predict_proba(X_ctx)[:,1]

    df_vaep = df.copy().reset_index(drop=True)
    df_vaep["p_score"]   = p_score
    df_vaep["p_concede"] = p_concede
    df_vaep = df_vaep.sort_values(["match_id","event_index"]).reset_index(drop=True)
    df_vaep["p_score_before"]   = df_vaep.groupby("match_id")["p_score"].shift(1).fillna(df_vaep["p_score"].mean())
    df_vaep["p_concede_before"] = df_vaep.groupby("match_id")["p_concede"].shift(1).fillna(df_vaep["p_concede"].mean())
    df_vaep["offensive_value"]  = df_vaep["p_score"]   - df_vaep["p_score_before"]
    df_vaep["defensive_value"]  = -(df_vaep["p_concede"] - df_vaep["p_concede_before"])
    df_vaep["vaep_value"]       = df_vaep["offensive_value"] + df_vaep["defensive_value"]

    player_vaep = df_vaep.groupby(["match_id","player_id"]).agg(
        vaep_rating     =("vaep_value",      "sum"),
        offensive_value =("offensive_value", "sum"),
        defensive_value =("defensive_value", "sum"),
        total_actions   =("vaep_value",      "count"),
        avg_vaep        =("vaep_value",      "mean"),
    ).reset_index()
    player_vaep["vaep_per_action"] = (player_vaep["vaep_rating"] / player_vaep["total_actions"]).round(6)
    player_vaep = add_uuid_column(player_vaep, "uuid", based_on=["match_id","player_id"])

    ensure_dirs(MODELS_DIR, DATA_DIR)
    off_model.save_model(str(MODELS_DIR / "vaep_offensive_model.json"))
    def_model.save_model(str(MODELS_DIR / "vaep_defensive_model.json"))
    with open(MODELS_DIR / "vaep_feature_cols.json","w") as f:
        json.dump(list(X_ctx.columns), f)

    player_vaep.to_parquet(DATA_DIR / "player_vaep_ratings.parquet", index=False)

    df_vaep_save = df_vaep[["match_id","player_id","type_name","result_name",
                             "start_x","start_y","end_x","end_y",
                             "p_score","p_concede","offensive_value","defensive_value","vaep_value"]].copy()
    df_vaep_save = add_uuid_column(df_vaep_save, "uuid")
    df_vaep_save.to_parquet(DATA_DIR / "actions_with_vaep.parquet", index=False)

    metrics = {"offensive_auc": round(auc_off,4), "defensive_auc": round(auc_def,4)}
    with open(MODELS_DIR / "vaep_metrics.json","w") as f:
        json.dump(metrics, f, indent=2)

    return off_model, def_model, player_vaep


def run():
    print("=" * 60)
    print("🤖 PIPELINE STEP 4: VAEP Model (XGBoost)")
    print("=" * 60)
    off, dff, vaep = train()
    print(f"\n✅ Step 4 Complete!")
    print(f"   Player-match VAEP: {len(vaep):,}")
    return off, dff, vaep


if __name__ == "__main__":
    run()
