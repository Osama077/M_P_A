"""
visualizations/player_dashboard.py — Player Analysis Dashboard
واجهة تحليل اللاعب الكاملة مع filter باسم اللاعب
"""

import io
import base64
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch
import warnings

warnings.filterwarnings("ignore")

try:
    from mplsoccer import Pitch, VerticalPitch
    HAS_MPLSOCCER = True
except ImportError:
    HAS_MPLSOCCER = False

from config import DATA_DIR, VIZ_COLORS

# ── Load Data (once) ──────────────────────────────────────────────────────────
_cache = {}

def _load():
    if not _cache:
        _cache["scores"]   = pd.read_parquet(DATA_DIR / "model_scores.parquet")
        _cache["computed"] = pd.read_parquet(DATA_DIR / "computed_features.parquet")
        _cache["events"]   = pd.read_parquet(DATA_DIR / "events_clean.parquet")
        _cache["matches"]  = pd.read_parquet(DATA_DIR / "matches.parquet")
        _cache["vaep"]     = pd.read_parquet(DATA_DIR / "player_vaep_ratings.parquet")
    return _cache


def get_player_list() -> list[str]:
    """قائمة بأسماء كل اللاعبين"""
    data = _load()
    names = data["scores"]["player_name"].dropna().unique().tolist()
    return sorted(names)


def _fuzzy_match(name_series: pd.Series, query: str) -> pd.Series:
    """Match if ALL tokens in query appear as substrings in the stored name."""
    tokens = query.strip().lower().split()
    mask = pd.Series(False, index=name_series.index)
    for i, val in enumerate(name_series):
        if pd.isna(val):
            continue
        lower = str(val).lower()
        if all(tok in lower for tok in tokens):
            mask.iloc[i] = True
    return mask

def get_player_data(player_name: str) -> dict:
    """Fetch all data for a given player (fuzzy name matching)."""
    data    = _load()
    scores  = data["scores"]
    computed= data["computed"]
    events  = data["events"]
    matches = data["matches"]
    vaep    = data["vaep"]

    # Filter by player (fuzzy token matching)
    match_mask = _fuzzy_match(scores["player_name"], player_name)
    p_scores  = scores[match_mask]
    p_feats   = computed[computed["player_id"].isin(p_scores["player_id"].unique())]
    p_events  = events[events["player_id"].isin(p_scores["player_id"].unique())]
    p_vaep    = vaep[vaep["player_id"].isin(p_scores["player_id"].unique())]

    if len(p_scores) == 0:
        return None

    # Merge مع التواريخ
    p_scores_dated = p_scores.merge(
        matches[["match_id","match_date","home_team","away_team"]],
        on="match_id", how="left"
    ).sort_values("match_date")

    return {
        "name":           str(p_scores.iloc[0]["player_name"]),
        "player_id":      int(p_scores.iloc[0]["player_id"]),
        "position":       str(p_scores.iloc[0].get("position_group","Unknown")),
        "cluster":        str(p_scores.iloc[0].get("player_cluster","Unknown")),
        "trend":          str(p_scores.iloc[0].get("performance_trend","Stable")),
        "scores":         p_scores_dated,
        "features":       p_feats,
        "events":         p_events,
        "vaep":           p_vaep,
        "avg_overall":    round(float(p_scores["overall_score"].mean()), 2),
        "matches_played": int(p_scores["match_id"].nunique()),
    }


def get_player_chart_data(player_name: str, match_id: int = None) -> dict:
    """
    جيب البيانات الخام للـ Charts (JSON بدل Base64 images)
    للـ Frontend Rendering مع Animation
    """
    player_data = get_player_data(player_name)
    if not player_data:
        return {"error": f"Player '{player_name}' not found"}

    scores = player_data["scores"].sort_values("match_date").reset_index(drop=True)
    dims = ["passing_score", "shooting_score", "positioning_score",
            "pressing_score", "movement_score", "physical_score", "behavioral_score"]
    labels = ["Passing", "Shooting", "Positioning", "Pressing", "Movement", "Physical", "Behavioral"]

    # 1. Radar Chart Data
    radar_vals = [float(scores[d].mean()) if d in scores.columns else 0.0 for d in dims]
    radar_data = {
        "labels": labels,
        "values": [round(v, 2) for v in radar_vals]
    }

    # 2. Trend Chart Data
    trend_data = [
        {
            "idx": int(i),
            "date": str(row.get("match_date", f"M{i+1}")),
            "overall": float(row.get("overall_score", 0)),
            "rolling_avg": float(scores.iloc[:i+1]["overall_score"].tail(3).mean()) if i >= 0 else 0
        }
        for i, (_, row) in enumerate(scores.iterrows())
    ]

    # 3. Score Breakdown Data
    breakdown_data = [
        {"name": label, "value": round(float(scores[dim].mean()) if dim in scores.columns else 0.0, 2)}
        for label, dim in zip(labels, dims)
    ]

    # 4. VAEP Data
    vaep_merged = scores.copy()
    for col in ["vaep_rating", "offensive_value", "defensive_value"]:
        if col not in vaep_merged.columns:
            vaep_merged[col] = 0.0

    vaep_timeline = [
        {
            "idx": int(i),
            "date": str(row.get("match_date", f"M{i+1}")),
            "vaep": float(row.get("vaep_rating", 0))
        }
        for i, (_, row) in enumerate(vaep_merged.iterrows())
    ]

    vaep_totals = {
        "offensive": round(float(vaep_merged["offensive_value"].sum()), 2),
        "defensive": round(float(vaep_merged["defensive_value"].sum()), 2)
    }

    vaep_data = {
        "timeline": vaep_timeline,
        "totals": vaep_totals
    }

    # 5. Position Comparison Data
    data = _load()
    all_scores = data["scores"]
    pos = player_data["position"]
    pos_avg_scores = all_scores[all_scores["position_group"] == pos]

    position_data = [
        {
            "name": label,
            "player": round(float(scores[dim].mean()) if dim in scores.columns else 0.0, 2),
            "position_avg": round(float(pos_avg_scores[dim].mean()) if dim in pos_avg_scores.columns else 0.0, 2)
        }
        for label, dim in zip(labels, dims)
    ]

    # 6. Percentile Data
    percentile_data = {
        "in_team": round(float(scores["percentile_in_team"].mean()) if "percentile_in_team" in scores.columns else 50, 2),
        "in_league": round(float(scores["percentile_in_league"].mean()) if "percentile_in_league" in scores.columns else 50, 2),
        "in_position": round(float(scores["percentile_in_position"].mean()) if "percentile_in_position" in scores.columns else 50, 2)
    }

    return {
        "player_name": player_data["name"],
        "position": player_data["position"],
        "cluster": player_data["cluster"],
        "trend": player_data["trend"],
        "avg_overall": player_data["avg_overall"],
        "matches_played": player_data["matches_played"],
        "charts": {
            "radar": radar_data,
            "trend": trend_data,
            "breakdown": breakdown_data,
            "vaep": vaep_data,
            "position_comparison": position_data,
            "percentiles": percentile_data
        }
    }


def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return f"data:image/png;base64,{encoded}"


# ── Chart 1: Radar Chart ──────────────────────────────────────────────────────

def radar_chart(player_data: dict) -> str:
    scores = player_data["scores"]
    dims   = ["passing_score","shooting_score","positioning_score",
               "pressing_score","movement_score","physical_score","behavioral_score"]
    labels = ["Passing","Shooting","Positioning","Pressing","Movement","Physical","Behavioral"]
    vals   = [round(float(scores[d].mean()), 2) for d in dims if d in scores.columns]
    vals  += vals[:1]

    angles = [n / float(len(labels)) * 2 * np.pi for n in range(len(labels))]
    angles+= angles[:1]

    fig, ax = plt.subplots(figsize=(7,7), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#1a1a2e")

    ax.plot(angles, vals, "o-", linewidth=2.5, color="#00d4ff")
    ax.fill(angles, vals, alpha=0.3, color="#00d4ff")

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=11, color="white")
    ax.set_ylim(0, 10)
    ax.set_yticks([2, 4, 6, 8, 10])
    ax.set_yticklabels(["2","4","6","8","10"], fontsize=8, color="#888888")
    ax.tick_params(colors="white")
    ax.spines["polar"].set_color("#444444")
    ax.grid(color="#333333")

    ax.set_title(f"{player_data['name']}\nPerformance Radar",
                 fontsize=13, fontweight="bold", color="white", pad=20)

    return _fig_to_base64(fig)


# ── Chart 2: Trend Chart ──────────────────────────────────────────────────────

def trend_chart(player_data: dict) -> str:
    scores = player_data["scores"].copy()
    scores = scores.sort_values("match_date").reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(14, 5))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#1a1a2e")

    x = range(len(scores))
    ax.plot(x, scores["overall_score"], "o-",
            color="#00d4ff", linewidth=2, markersize=6, label="Match Score", zorder=3)

    rolling = scores["overall_score"].rolling(3, min_periods=1).mean()
    ax.plot(x, rolling, "--", color="#ff9f43", linewidth=2.5, label="3-Match Avg")

    avg = scores["overall_score"].mean()
    ax.axhline(avg, color="#ff6b6b", linestyle=":", alpha=0.8, label=f"Season Avg ({avg:.2f})")

    ax.fill_between(x, scores["overall_score"], avg, alpha=0.1, color="#00d4ff")

    ax.set_ylim(0, 10)
    ax.set_xlabel("Match Number", color="white")
    ax.set_ylabel("Overall Score (0-10)", color="white")
    ax.set_title(f"{player_data['name']} — Performance Trend",
                 fontsize=13, fontweight="bold", color="white")
    ax.tick_params(colors="white")
    ax.spines["bottom"].set_color("#444444")
    ax.spines["left"].set_color("#444444")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(color="#333333", alpha=0.5)
    ax.legend(facecolor="#2a2a3e", edgecolor="none", labelcolor="white")

    return _fig_to_base64(fig)


# ── Chart 3: Heatmap ──────────────────────────────────────────────────────────

def heatmap_chart(player_data: dict, match_id: int = None) -> str:
    events = player_data["events"]
    if match_id is not None and "match_id" in events.columns:
        events = events[events["match_id"] == match_id]
    events = events[events["location_x"].notna()]

    fig, ax = plt.subplots(figsize=(12, 8))
    fig.patch.set_facecolor("#22312b")

    if HAS_MPLSOCCER:
        pitch = Pitch(pitch_type="statsbomb", pitch_color="#22312b", line_color="white")
        pitch.draw(ax=ax)
        if len(events) > 10:
            pitch.kdeplot(x=events["location_x"], y=events["location_y"],
                          ax=ax, cmap="hot", fill=True, alpha=0.7,
                          shade_lowest=False, cbar=False)
    else:
        ax.set_facecolor("#22312b")
        ax.scatter(events["location_x"], events["location_y"],
                   alpha=0.3, s=5, c="orange")
        ax.set_xlim(0, 120)
        ax.set_ylim(0, 80)

    match_suffix = f" (Match {match_id})" if match_id is not None else " (Season)"
    ax.set_title(f"{player_data['name']} — Position Heatmap{match_suffix}",
                 fontsize=13, fontweight="bold", color="white", pad=15)

    return _fig_to_base64(fig)


# ── Chart 4: Pass Map ─────────────────────────────────────────────────────────

def pass_map_chart(player_data: dict, match_id: int = None) -> str:
    events = player_data["events"]
    passes = events[events["event_type"] == "Pass"].copy()

    if match_id:
        passes = passes[passes["match_id"] == match_id]
    else:
        # أحسن ماتش من ناحية عدد التمريرات
        best_match = passes.groupby("match_id").size().idxmax()
        passes     = passes[passes["match_id"] == best_match]

    complete   = passes[passes["pass_outcome"].isna() | (passes["pass_outcome"] == "Complete")]
    incomplete = passes[~passes.index.isin(complete.index)]

    fig, ax = plt.subplots(figsize=(12, 8))
    fig.patch.set_facecolor("#22312b")

    if HAS_MPLSOCCER:
        pitch = Pitch(pitch_type="statsbomb", pitch_color="#22312b", line_color="white")
        pitch.draw(ax=ax)
        if len(complete):
            pitch.arrows(complete["location_x"], complete["location_y"],
                         complete["pass_end_x"], complete["pass_end_y"],
                         ax=ax, color="#00ff88", width=1.5, headwidth=5, alpha=0.7)
        if len(incomplete):
            pitch.arrows(incomplete["location_x"], incomplete["location_y"],
                         incomplete["pass_end_x"], incomplete["pass_end_y"],
                         ax=ax, color="#ff4444", width=1.5, headwidth=5, alpha=0.7)
    else:
        ax.set_facecolor("#22312b")
        if len(complete):
            ax.quiver(complete["location_x"], complete["location_y"],
                      complete["pass_end_x"] - complete["location_x"],
                      complete["pass_end_y"] - complete["location_y"],
                      color="#00ff88", alpha=0.6, scale=1, scale_units="xy", angles="xy")
        if len(incomplete):
            ax.quiver(incomplete["location_x"], incomplete["location_y"],
                      incomplete["pass_end_x"] - incomplete["location_x"],
                      incomplete["pass_end_y"] - incomplete["location_y"],
                      color="#ff4444", alpha=0.6, scale=1, scale_units="xy", angles="xy")

    ax.set_title(
        f"{player_data['name']} — Pass Map\n"
        f"Complete: {len(complete)}  |  Incomplete: {len(incomplete)}",
        fontsize=12, fontweight="bold", color="white", pad=15
    )
    return _fig_to_base64(fig)


# ── Chart 5: Score Breakdown Bar Chart ────────────────────────────────────────

def score_breakdown_chart(player_data: dict) -> str:
    scores = player_data["scores"]
    dims   = ["passing_score","shooting_score","positioning_score",
               "pressing_score","movement_score","physical_score","behavioral_score"]
    labels = ["Passing","Shooting","Positioning","Pressing","Movement","Physical","Behavioral"]
    vals   = [round(float(scores[d].mean()), 2) for d in dims if d in scores.columns]
    colors = ["#00d4ff","#ff6b6b","#ffd32a","#0be881","#ff9f43","#9b59b6","#2ecc71"]

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#1a1a2e")

    bars = ax.barh(labels, vals, color=colors, edgecolor="none", height=0.6)
    ax.set_xlim(0, 10)

    for bar, val in zip(bars, vals):
        ax.text(val + 0.1, bar.get_y() + bar.get_height()/2,
                f"{val:.1f}", va="center", fontsize=11, color="white", fontweight="bold")

    overall = player_data["avg_overall"]
    ax.axvline(overall, color="white", linestyle="--", alpha=0.5, label=f"Overall: {overall:.2f}")

    ax.set_xlabel("Score (0-10)", color="white")
    ax.set_title(f"{player_data['name']} — Dimension Scores",
                 fontsize=13, fontweight="bold", color="white")
    ax.tick_params(colors="white")
    ax.spines["bottom"].set_color("#444444")
    ax.spines["left"].set_color("#444444")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(facecolor="#2a2a3e", edgecolor="none", labelcolor="white")

    return _fig_to_base64(fig)


# ── Chart 6: VAEP Over Season ─────────────────────────────────────────────────

def vaep_chart(player_data: dict) -> str:
    scores = player_data["scores"].sort_values("match_date")
    vaep   = player_data["vaep"]

    # Start from scores (it already contains VAEP fields in model_scores),
    # then backfill from player_vaep_ratings when needed.
    merged = scores.copy()
    need_cols = ["vaep_rating", "offensive_value", "defensive_value"]
    missing = [c for c in need_cols if c not in merged.columns]

    if missing and {"match_id", "player_id"}.issubset(vaep.columns):
        vaep_subset_cols = ["match_id", "player_id"] + [c for c in need_cols if c in vaep.columns]
        merged = merged.merge(
            vaep[vaep_subset_cols],
            on=["match_id", "player_id"],
            how="left",
            suffixes=("", "_vaep")
        )
        for c in need_cols:
            if c not in merged.columns and f"{c}_vaep" in merged.columns:
                merged[c] = merged[f"{c}_vaep"]

    for c in need_cols:
        if c not in merged.columns:
            merged[c] = 0.0
        merged[c] = merged[c].fillna(0)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.patch.set_facecolor("#1a1a2e")

    # VAEP Timeline
    ax = axes[0]
    ax.set_facecolor("#1a1a2e")
    x = range(len(merged))
    vaep_values = merged["vaep_rating"].fillna(0)
    ax.bar(x, vaep_values,
           color=["#00d4ff" if v >= 0 else "#ff6b6b" for v in vaep_values])
    ax.axhline(0, color="white", linewidth=0.8)
    ax.set_title("VAEP per Match", color="white", fontsize=11)
    ax.tick_params(colors="white")
    ax.set_facecolor("#1a1a2e")
    ax.spines["bottom"].set_color("#444444")
    ax.spines["left"].set_color("#444444")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Offensive vs Defensive
    ax2 = axes[1]
    ax2.set_facecolor("#1a1a2e")
    total_off = merged["offensive_value"].sum()
    total_def = merged["defensive_value"].sum()
    bars = ax2.bar(["Offensive", "Defensive"], [total_off, total_def],
                   color=["#00d4ff","#0be881"], width=0.5)
    ax2.set_title("Total Season VAEP Breakdown", color="white", fontsize=11)
    ax2.tick_params(colors="white")
    ax2.spines["bottom"].set_color("#444444")
    ax2.spines["left"].set_color("#444444")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    for bar in bars:
        h = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2, h + 0.3,
                 f"{h:.2f}", ha="center", color="white", fontweight="bold")

    fig.suptitle(f"{player_data['name']} — VAEP Analysis", color="white",
                 fontsize=13, fontweight="bold")
    return _fig_to_base64(fig)


# ── Chart 7: Comparison with Position Average ────────────────────────────────

def position_comparison_chart(player_data: dict) -> str:
    scores  = player_data["scores"]
    data    = _load()
    all_sc  = data["scores"]
    pos     = player_data["position"]

    pos_avg = all_sc[all_sc["position_group"] == pos]
    dims    = ["passing_score","shooting_score","positioning_score",
                "pressing_score","movement_score","physical_score","behavioral_score"]
    labels  = ["Passing","Shooting","Positioning","Pressing","Movement","Physical","Behavioral"]

    player_vals = [float(scores[d].mean()) for d in dims if d in scores.columns]
    pos_vals    = [float(pos_avg[d].mean()) for d in dims if d in pos_avg.columns]

    x    = np.arange(len(labels))
    width= 0.35

    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#1a1a2e")

    ax.bar(x - width/2, player_vals, width, label=player_data["name"],
           color="#00d4ff", alpha=0.9, edgecolor="none")
    ax.bar(x + width/2, pos_vals,    width, label=f"{pos} Average",
           color="#ff9f43", alpha=0.9, edgecolor="none")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right", color="white")
    ax.set_ylim(0, 10)
    ax.set_ylabel("Score (0-10)", color="white")
    ax.set_title(f"{player_data['name']} vs {pos} Position Average",
                 fontsize=13, fontweight="bold", color="white")
    ax.tick_params(colors="white")
    ax.spines["bottom"].set_color("#444444")
    ax.spines["left"].set_color("#444444")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(facecolor="#2a2a3e", edgecolor="none", labelcolor="white")

    return _fig_to_base64(fig)


# ── Chart 8: Shooting Map (Shot Locations + xG) ──────────────────────────────

def shooting_map_chart(player_data: dict, match_id: int = None) -> str:
    events = player_data["events"]
    shots  = events[events["event_type"] == "Shot"].copy()
    if match_id is not None and "match_id" in shots.columns:
        shots = shots[shots["match_id"] == match_id]

    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor("#22312b")

    if HAS_MPLSOCCER:
        pitch = VerticalPitch(pitch_type="statsbomb", pitch_color="#22312b",
                              line_color="white", half=True)
        pitch.draw(ax=ax)

        if len(shots):
            goals = shots[shots["shot_outcome"] == "Goal"]
            saves = shots[shots["shot_outcome"] != "Goal"]

            if len(saves):
                ax.scatter(saves["location_y"], saves["location_x"],
                           c="#ff6b6b", s=saves["shot_xg"].fillna(0.1) * 1000 + 50,
                           alpha=0.7, zorder=3, label="No Goal")
            if len(goals):
                ax.scatter(goals["location_y"], goals["location_x"],
                           c="#ffd32a", s=goals["shot_xg"].fillna(0.1) * 1000 + 50,
                           alpha=1.0, zorder=4, marker="*", label="Goal", edgecolors="white")
    else:
        ax.set_facecolor("#22312b")
        if len(shots):
            goals = shots[shots["shot_outcome"] == "Goal"]
            saves = shots[shots["shot_outcome"] != "Goal"]
            if len(saves):
                ax.scatter(saves["location_x"], saves["location_y"],
                           c="#ff6b6b", s=50, alpha=0.7, label="No Goal")
            if len(goals):
                ax.scatter(goals["location_x"], goals["location_y"],
                           c="#ffd32a", s=100, marker="*", label="Goal")

    match_suffix = f" (Match {match_id})" if match_id is not None else " (Season)"
    ax.set_title(f"{player_data['name']} — Shot Map{match_suffix}\n"
                 f"(Size = xG value | Star = Goal)",
                 color="white", fontsize=11, fontweight="bold")
    ax.legend(facecolor="#2a2a3e", edgecolor="none", labelcolor="white")
    return _fig_to_base64(fig)


# ── Chart 8b: Saves Map (Goalkeeper — Shots Faced) ──────────────────────────

def saves_map_chart(player_data: dict, match_id: int = None,
                    full_events: pd.DataFrame = None) -> str:
    """Show shots a goalkeeper faced: saves made (green) and goals conceded (red)."""
    pid = player_data["player_id"]

    if full_events is not None:
        events = full_events
    else:
        events = _load()["events"]

    # Filter to match
    if match_id is not None and "match_id" in events.columns:
        events = events[events["match_id"] == match_id]

    # Determine the GK's team from their own events
    gk_events = events[events["player_id"] == pid]
    gk_team_id = None
    if len(gk_events) and "team_id" in gk_events.columns:
        teams = gk_events["team_id"].dropna().unique()
        if len(teams):
            gk_team_id = int(teams[0])

    shots = events[events["event_type"] == "Shot"].copy()
    if not len(shots):
        fig, ax = plt.subplots(figsize=(8, 6))
        fig.patch.set_facecolor("#22312b")
        ax.set_facecolor("#22312b")
        ax.text(0.5, 0.5, "No shot data for this match",
                ha="center", va="center", color="white", fontsize=12)
        return _fig_to_base64(fig)

    saves = shots[(shots["shot_outcome"] == "Saved") & (shots["player_id"] == pid)]

    goals_conceded = pd.DataFrame()
    if gk_team_id is not None:
        goals_conceded = shots[
            (shots["shot_outcome"] == "Goal")
            & (shots["team_id"] != gk_team_id)
            & (shots["team_id"].notna())
        ]

    other_faced = pd.DataFrame()
    if gk_team_id is not None:
        idx = set(saves.index) | set(goals_conceded.index)
        other_faced = shots[
            (shots["team_id"] != gk_team_id)
            & (shots["team_id"].notna())
            & ~shots.index.isin(idx)
        ]

    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor("#22312b")

    if HAS_MPLSOCCER:
        pitch = VerticalPitch(pitch_type="statsbomb", pitch_color="#22312b",
                              line_color="white", half=True)
        pitch.draw(ax=ax)

        if len(saves):
            ax.scatter(saves["location_y"], saves["location_x"],
                       c="#22c55e", s=saves["shot_xg"].fillna(0.1) * 1000 + 50,
                       alpha=0.8, zorder=3, label="Saved", edgecolors="white", linewidth=0.5)
        if len(goals_conceded):
            ax.scatter(goals_conceded["location_y"], goals_conceded["location_x"],
                       c="#ef4444", s=goals_conceded["shot_xg"].fillna(0.1) * 1000 + 80,
                       alpha=1.0, zorder=4, marker="*", label="Goal Conceded", edgecolors="white")
        if len(other_faced):
            ax.scatter(other_faced["location_y"], other_faced["location_x"],
                       c="#94a3b8", s=other_faced["shot_xg"].fillna(0.1) * 500 + 30,
                       alpha=0.5, zorder=2, label="Other Shot Faced")
    else:
        ax.set_facecolor("#22312b")
        if len(saves):
            ax.scatter(saves["location_x"], saves["location_y"],
                       c="#22c55e", s=80, alpha=0.8, label="Saved")
        if len(goals_conceded):
            ax.scatter(goals_conceded["location_x"], goals_conceded["location_y"],
                       c="#ef4444", s=120, marker="*", label="Goal Conceded")
        if len(other_faced):
            ax.scatter(other_faced["location_x"], other_faced["location_y"],
                       c="#94a3b8", s=40, alpha=0.5, label="Other Shot Faced")

    match_suffix = f" (Match {match_id})" if match_id is not None else " (Season)"
    ax.set_title(f"{player_data['name']} — Saves Map{match_suffix}\n"
                 f"(Green = Saved | Red = Goal | Grey = Other)",
                 color="white", fontsize=11, fontweight="bold")
    ax.legend(facecolor="#2a2a3e", edgecolor="none", labelcolor="white")
    return _fig_to_base64(fig)


# ── Chart 9: Percentile Profile ───────────────────────────────────────────────

def percentile_chart(player_data: dict) -> str:
    scores = player_data["scores"]
    percs  = {
        "In Team"    : float(scores["percentile_in_team"].mean())     if "percentile_in_team"     in scores.columns else 50,
        "In League"  : float(scores["percentile_in_league"].mean())   if "percentile_in_league"   in scores.columns else 50,
        "In Position": float(scores["percentile_in_position"].mean()) if "percentile_in_position" in scores.columns else 50,
    }

    fig, ax = plt.subplots(figsize=(8, 4))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#1a1a2e")

    colors = ["#00d4ff","#ff9f43","#0be881"]
    bars   = ax.barh(list(percs.keys()), list(percs.values()),
                     color=colors, height=0.5, edgecolor="none")
    ax.set_xlim(0, 100)
    ax.axvline(50, color="#666666", linestyle="--", alpha=0.5)

    for bar, val in zip(bars, percs.values()):
        ax.text(val + 1, bar.get_y() + bar.get_height()/2,
                f"{val:.1f}%", va="center", color="white", fontweight="bold")

    ax.set_xlabel("Percentile", color="white")
    ax.set_title(f"{player_data['name']} — Percentile Rankings",
                 color="white", fontsize=12, fontweight="bold")
    ax.tick_params(colors="white")
    ax.spines["bottom"].set_color("#444444")
    ax.spines["left"].set_color("#444444")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    return _fig_to_base64(fig)


# ── MAIN: Generate All Charts ─────────────────────────────────────────────────

def generate_all_charts(player_name: str, match_id: int = None) -> dict:
    """
    توليد كل الـ charts للاعب معين
    بيرجع dict فيه base64 images
    """
    player_data = get_player_data(player_name)
    if not player_data:
        return {"error": f"Player '{player_name}' not found"}

    scores = player_data["scores"].sort_values("match_date")
    match_meta = scores[["match_id", "match_date", "home_team", "away_team"]].drop_duplicates(subset=["match_id"]).copy()

    available_matches = []
    for _, row in match_meta.iterrows():
        mid = int(row["match_id"])
        match_date = ""
        if "match_date" in row and pd.notna(row["match_date"]):
            match_date = str(row["match_date"])
        home_team = str(row.get("home_team", "")) if pd.notna(row.get("home_team", None)) else ""
        away_team = str(row.get("away_team", "")) if pd.notna(row.get("away_team", None)) else ""
        label = f"{match_date} | {home_team} vs {away_team}" if (home_team or away_team) else f"Match {mid}"
        available_matches.append({
            "match_id": mid,
            "match_date": match_date,
            "home_team": home_team,
            "away_team": away_team,
            "label": label,
        })

    available_ids = {m["match_id"] for m in available_matches}
    selected_match_id = int(match_id) if match_id is not None and int(match_id) in available_ids else None
    if selected_match_id is None and len(available_matches) > 0:
        selected_match_id = int(available_matches[-1]["match_id"])

    print(f"[CHART] Generating charts for: {player_data['name']} | match_id={selected_match_id}")

    return {
        "player_info": {
            "name":        player_data["name"],
            "position":    player_data["position"],
            "cluster":     player_data["cluster"],
            "trend":       player_data["trend"],
            "avg_overall": player_data["avg_overall"],
            "matches":     player_data["matches_played"],
        },
        "selected_match_id": selected_match_id,
        "available_matches": available_matches,
        "charts": {
            "radar":              radar_chart(player_data),
            "trend":              trend_chart(player_data),
            "heatmap":            heatmap_chart(player_data, selected_match_id),
            "pass_map":           pass_map_chart(player_data, selected_match_id),
            "score_breakdown":    score_breakdown_chart(player_data),
            "vaep":               vaep_chart(player_data),
            "position_comparison":position_comparison_chart(player_data),
            "shooting_map":       shooting_map_chart(player_data, selected_match_id),
            "percentiles":        percentile_chart(player_data),
        }
    }
