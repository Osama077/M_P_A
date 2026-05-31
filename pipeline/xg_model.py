"""
pipeline/xg_model.py — xG Model (LightGBM)
يقابل Notebook 03
"""

import json
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, brier_score_loss
from statsbombpy import sb

from config import DATA_DIR, MODELS_DIR
from utils.uuid_manager import add_uuid_column
from utils.helpers import ensure_dirs

FEATURE_COLS = [
    "x", "y", "distance_to_goal", "dist_squared",
    "angle_to_goal", "goal_angle", "x_squared",
    "under_pressure", "is_header", "is_penalty",
    "is_free_kick", "is_first_time",
]

LGB_PARAMS = {
    "objective":        "binary",
    "metric":           ["binary_logloss", "auc"],
    "learning_rate":    0.05,
    "num_leaves":       31,
    "max_depth":        6,
    "min_child_samples":20,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq":     5,
    "reg_alpha":        0.1,
    "reg_lambda":       0.1,
    "verbose":          -1,
    "random_state":     42,
}


def _engineer_shot_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = df.copy()

    def extract_loc(loc):
        if isinstance(loc, list) and len(loc) >= 2:
            return loc[0], loc[1]
        return None, None

    if "location" in df.columns:
        df["x"], df["y"] = zip(*df["location"].apply(extract_loc))
    elif "location_x" in df.columns:
        df["x"] = df["location_x"]
        df["y"] = df["location_y"]

    df["distance_to_goal"] = np.sqrt((120 - df["x"])**2 + (40 - df["y"])**2)
    df["angle_to_goal"]    = np.abs(np.arctan2(np.abs(df["y"] - 40), 120 - df["x"]))
    df["goal_angle"]       = np.abs(
        np.arctan2(44 - df["y"], 120 - df["x"]) -
        np.arctan2(36 - df["y"], 120 - df["x"])
    )
    df["x_squared"]    = df["x"] ** 2
    df["dist_squared"] = df["distance_to_goal"] ** 2

    def get_name(v, default="Normal"):
        if isinstance(v, dict): return v.get("name", default)
        return v if pd.notna(v) else default

    if "shot_technique" in df.columns:
        df["technique"] = df["shot_technique"].apply(lambda x: get_name(x))
    if "shot_body_part" in df.columns:
        df["body_part"]  = df["shot_body_part"].apply(lambda x: get_name(x, "Foot"))
    elif "bodypart" in df.columns:
        df["body_part"]  = df["bodypart"].fillna("foot")

    if "shot_type" in df.columns:
        df["shot_type_name"] = df["shot_type"].apply(lambda x: get_name(x, "Open Play"))
    elif "shot_type_name" in df.columns:
        pass
    else:
        df["shot_type_name"] = "Open Play"

    df["under_pressure"] = df["under_pressure"].fillna(False).astype(int) \
        if "under_pressure" in df.columns else 0
    df["is_header"]      = (df.get("body_part", pd.Series(["foot"]*len(df))) == "Head").astype(int)
    df["is_penalty"]     = (df.get("shot_type_name", pd.Series(["Open Play"]*len(df))) == "Penalty").astype(int)
    df["is_free_kick"]   = (df.get("shot_type_name", pd.Series(["Open Play"]*len(df))) == "Free Kick").astype(int)
    df["is_first_time"]  = df["shot_first_time"].fillna(False).astype(int) \
        if "shot_first_time" in df.columns else 0

    if "shot_outcome" in df.columns:
        if df["shot_outcome"].dtype == object:
            df["shot_outcome_name"] = df["shot_outcome"].apply(lambda x: get_name(x, ""))
        else:
            df["shot_outcome_name"] = df["shot_outcome"]
    else:
        df["shot_outcome_name"] = ""

    df["is_goal"]       = (df["shot_outcome_name"] == "Goal").astype(int)
    df["statsbomb_xg"]  = df.get("shot_statsbomb_xg", df.get("shot_xg", np.nan))

    technique_dummies = pd.get_dummies(df.get("technique", pd.Series(["Normal"]*len(df))),
                                       prefix="tech", drop_first=True)
    X = pd.concat([df[FEATURE_COLS], technique_dummies], axis=1).fillna(0)
    return df, X


def load_all_shots() -> pd.DataFrame:
    """تحميل كل الـ shots من StatsBomb Open Data"""
    print("📥 Loading all shots from StatsBomb...")
    comps = sb.competitions()
    all_shots = []

    for _, row in comps.iterrows():
        try:
            matches = sb.matches(competition_id=row["competition_id"],
                                 season_id=row["season_id"])
            for _, m in matches.iterrows():
                try:
                    evts  = sb.events(match_id=m["match_id"])
                    shots = evts[evts["type"] == "Shot"].copy()
                    if len(shots):
                        shots["match_id"] = m["match_id"]
                        all_shots.append(shots)
                except:
                    continue
        except:
            continue

    df = pd.concat(all_shots, ignore_index=True)
    print(f"✅ Total shots: {len(df):,}")
    return df


def train(shots_df: pd.DataFrame = None) -> lgb.Booster:
    if shots_df is None:
        shots_df = load_all_shots()

    shots_df, X = _engineer_shot_features(shots_df)
    y = shots_df["is_goal"]

    # استبعاد الـ Penalties من التدريب
    mask    = shots_df["is_penalty"] == 0
    X_train, X_val, y_train, y_val = train_test_split(
        X[mask], y[mask], test_size=0.2, random_state=42, stratify=y[mask]
    )

    train_set = lgb.Dataset(X_train, label=y_train)
    val_set   = lgb.Dataset(X_val,   label=y_val, reference=train_set)

    model = lgb.train(
        LGB_PARAMS, train_set,
        num_boost_round=1000,
        valid_sets=[train_set, val_set],
        valid_names=["train", "val"],
        callbacks=[
            lgb.early_stopping(50, verbose=False),
            lgb.log_evaluation(100),
        ]
    )

    y_pred = model.predict(X_val)
    auc    = roc_auc_score(y_val, y_pred)
    brier  = brier_score_loss(y_val, y_pred)
    print(f"✅ xG Model — AUC: {auc:.4f} | Brier: {brier:.4f}")

    ensure_dirs(MODELS_DIR)
    model.save_model(str(MODELS_DIR / "xg_model.txt"))
    with open(MODELS_DIR / "xg_feature_cols.json", "w") as f:
        json.dump(list(X.columns), f)
    with open(MODELS_DIR / "xg_metrics.json", "w") as f:
        json.dump({"auc_val": round(auc,4), "brier_val": round(brier,4)}, f, indent=2)

    return model


def predict_on_barca(model: lgb.Booster = None) -> pd.DataFrame:
    if model is None:
        model = lgb.Booster(model_file=str(MODELS_DIR / "xg_model.txt"))

    with open(MODELS_DIR / "xg_feature_cols.json") as f:
        feature_cols = json.load(f)

    barca = pd.read_parquet(DATA_DIR / "shots_for_xg.parquet")
    _, X  = _engineer_shot_features(barca)

    for col in feature_cols:
        if col not in X.columns:
            X[col] = 0
    X = X[feature_cols].fillna(0)

    barca["predicted_xg"] = model.predict(X)
    barca = add_uuid_column(barca, "uuid", based_on=["event_id"]
                            if "event_id" in barca.columns else None)

    barca.to_parquet(DATA_DIR / "barca_shots_with_xg.parquet", index=False)
    print(f"✅ Barcelona shots predicted: {len(barca):,}")
    return barca


def run():
    print("=" * 60)
    print("🎯 PIPELINE STEP 3: xG Model (LightGBM)")
    print("=" * 60)
    model = train()
    barca = predict_on_barca(model)
    print(f"\n✅ Step 3 Complete! AUC metrics saved.")
    return model, barca


if __name__ == "__main__":
    run()
