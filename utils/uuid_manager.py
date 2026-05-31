"""
utils/uuid_manager.py — UUID Management
كل البيانات في النظام بتاخد UUID فريد عشان تتخزن في الداتابيز
"""

import uuid
import hashlib
import pandas as pd
from typing import Optional


def generate_uuid() -> str:
    """توليد UUID جديد عشوائي"""
    return str(uuid.uuid4())


def deterministic_uuid(*args) -> str:
    """
    توليد UUID ثابت من قيم محددة
    نفس المدخلات دايماً بتدي نفس الـ UUID
    مفيد لـ: match_id + player_id → نفس الـ feature_id دايماً
    """
    combined = "_".join(str(a) for a in args)
    hashed   = hashlib.md5(combined.encode()).hexdigest()
    return str(uuid.UUID(hashed))


def add_uuid_column(df: pd.DataFrame, col_name: str = "uuid",
                    based_on: Optional[list] = None) -> pd.DataFrame:
    """
    إضافة UUID column للـ DataFrame
    
    Args:
        df: الـ DataFrame
        col_name: اسم الـ column الجديدة
        based_on: لو محدد، بيعمل deterministic UUID من الـ columns دي
                  لو None، بيعمل random UUID لكل صف
    
    Returns:
        DataFrame مع UUID column جديدة في الأول
    """
    df = df.copy()
    
    if based_on:
        # Deterministic UUID من columns محددة
        df[col_name] = df.apply(
            lambda row: deterministic_uuid(*[row[c] for c in based_on]),
            axis=1
        )
    else:
        # Random UUID لكل صف
        df[col_name] = [generate_uuid() for _ in range(len(df))]
    
    # حط الـ UUID في الأول
    cols = [col_name] + [c for c in df.columns if c != col_name]
    return df[cols]


def add_uuids_to_all(
    events_df:       pd.DataFrame,
    matches_df:      pd.DataFrame,
    lineups_df:      pd.DataFrame,
    computed_df:     pd.DataFrame,
    model_scores_df: pd.DataFrame,
    player_vaep_df:  pd.DataFrame,
    spadl_df:        pd.DataFrame,
) -> dict:
    """
    إضافة UUIDs لكل الجداول في الـ pipeline
    
    Returns:
        dict فيه كل الـ DataFrames مع UUIDs
    """
    print("🔑 Adding UUIDs to all DataFrames...")

    # Events: UUID فريد لكل event (بناءً على event_id الأصلي من StatsBomb)
    if "event_id" in events_df.columns:
        events_df = add_uuid_column(
            events_df, "uuid",
            based_on=["event_id"]
        )
    else:
        events_df = add_uuid_column(events_df, "uuid")
    print(f"  ✅ events_df        : {len(events_df):,} UUIDs")

    # Matches: UUID بناءً على match_id
    matches_df = add_uuid_column(
        matches_df, "uuid",
        based_on=["match_id"]
    )
    print(f"  ✅ matches_df       : {len(matches_df):,} UUIDs")

    # Lineups: UUID بناءً على match_id + player_id
    if "player_id" in lineups_df.columns:
        lineups_df = add_uuid_column(
            lineups_df, "uuid",
            based_on=["match_id", "player_id"]
        )
    else:
        lineups_df = add_uuid_column(lineups_df, "uuid")
    print(f"  ✅ lineups_df       : {len(lineups_df):,} UUIDs")

    # Computed Features: UUID بناءً على match_id + player_id
    computed_df = add_uuid_column(
        computed_df, "uuid",
        based_on=["match_id", "player_id"]
    )
    print(f"  ✅ computed_df      : {len(computed_df):,} UUIDs")

    # Model Scores: UUID بناءً على match_id + player_id
    model_scores_df = add_uuid_column(
        model_scores_df, "uuid",
        based_on=["match_id", "player_id"]
    )
    print(f"  ✅ model_scores_df  : {len(model_scores_df):,} UUIDs")

    # Player VAEP: UUID بناءً على match_id + player_id
    player_vaep_df = add_uuid_column(
        player_vaep_df, "uuid",
        based_on=["match_id", "player_id"]
    )
    print(f"  ✅ player_vaep_df   : {len(player_vaep_df):,} UUIDs")

    # SPADL Actions: UUID بناءً على match_id + event_index
    if "event_index" in spadl_df.columns:
        spadl_df = add_uuid_column(
            spadl_df, "uuid",
            based_on=["match_id", "event_index"]
        )
    else:
        spadl_df = add_uuid_column(spadl_df, "uuid")
    print(f"  ✅ spadl_df         : {len(spadl_df):,} UUIDs")

    print("✅ All UUIDs added successfully!")

    return {
        "events":        events_df,
        "matches":       matches_df,
        "lineups":       lineups_df,
        "computed":      computed_df,
        "model_scores":  model_scores_df,
        "player_vaep":   player_vaep_df,
        "spadl":         spadl_df,
    }


def get_uuid_for_record(table: str, **kwargs) -> str:
    """
    جيب UUID لـ record معين بناءً على الـ table واسم والقيم

    مثال:
        get_uuid_for_record("match_player", match_id=123, player_id=456)
    """
    return deterministic_uuid(table, *kwargs.values())
