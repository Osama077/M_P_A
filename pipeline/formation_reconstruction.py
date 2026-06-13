"""
pipeline/formation_reconstruction.py — Formation & Tactical Analysis Engine

Reconstructs actual team formation from event data using average player positions,
line detection via clustering, and tactical shape analysis.

References:
  - Karun Singh's "Expected Threat" model
  - Friends of Tracking positional data analysis
  - StatsBomb open-data tactical conventions
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans


PITCH_LENGTH = 120.0
PITCH_WIDTH  = 80.0

STANDARD_FORMATIONS = {
    "4-3-3": "4-3-3", "4-4-2": "4-4-2", "4-2-3-1": "4-2-3-1",
    "3-5-2": "3-5-2", "5-3-2": "5-3-2", "3-4-3": "3-4-3",
    "4-1-4-1": "4-1-4-1", "4-3-2-1": "4-3-2-1", "3-4-1-2": "3-4-1-2",
    "4-5-1": "4-5-1", "5-4-1": "5-4-1", "3-6-1": "3-6-1",
}


# ═══════════════════════════════════════════════════════════════════════════════
# 1. PLAYER AVERAGE POSITION ESTIMATION
# ═══════════════════════════════════════════════════════════════════════════════

def compute_avg_positions(events: pd.DataFrame, match_id: int,
                          team_name: str = None) -> pd.DataFrame:
    """Compute average position for each player from event location data.
    
    Uses only positional event types (pass, carry, ball receipt, pressure, shot,
    dribble, ball recovery, interception) — excludes fouls, cards, substitutions.
    """
    position_events = events[
        (events["match_id"] == match_id)
        & (events["player_id"].notna())
        & (events["location_x"].notna())
        & (events["location_y"].notna())
        & (events["event_type"].isin([
            "Pass", "Carry", "Ball Receipt*", "Pressure", "Shot",
            "Dribble", "Ball Recovery", "Interception", "Block",
            "Clearance", "Shield", "Duel", "Miscontrol",
        ]))
    ].copy()
    
    if team_name:
        position_events = position_events[
            position_events["team_name"].astype(str).str.contains(team_name, case=False, na=False)
        ]
    
    agg = position_events.groupby("player_id").agg(
        avg_x=("location_x", "mean"),
        avg_y=("location_y", "mean"),
        event_count=("event_index", "count"),
        team_name=("team_name", "first"),
        player_name=("player_name", "first"),
    ).reset_index()
    
    return agg


# ═══════════════════════════════════════════════════════════════════════════════
# 2. LINE DETECTION VIA CLUSTERING
# ═══════════════════════════════════════════════════════════════════════════════

def detect_lines(avg_x_values: np.ndarray, n_lines: int = 3) -> np.ndarray:
    """Cluster outfield players into vertical lines based on avg_position_x.
    
    Uses KMeans on the x-coordinate to identify defensive, midfield,
    and attacking lines. Returns cluster labels (0 = most defensive).
    """
    if len(avg_x_values) < n_lines:
        return np.zeros(len(avg_x_values), dtype=int)
    
    X = avg_x_values.reshape(-1, 1)
    kmeans = KMeans(n_clusters=n_lines, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X)
    
    # Map cluster labels so 0 = lowest avg_x (most defensive)
    centers = kmeans.cluster_centers_.flatten()
    order = np.argsort(centers)
    remap = {old: new for new, old in enumerate(order)}
    return np.array([remap[l] for l in labels])


def classify_formation(player_counts: dict) -> str:
    """Classify formation from player counts per line.
    
    player_counts: {"defenders": N, "midfielders": N, "forwards": N}
    Returns formation string like "4-3-3".
    """
    d, m, f = player_counts["defenders"], player_counts["midfielders"], player_counts["forwards"]
    key = f"{d}-{m}-{f}"
    return STANDARD_FORMATIONS.get(key, key)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. FORMATION RECONSTRUCTION (PER TEAM)
# ═══════════════════════════════════════════════════════════════════════════════

def reconstruct_team_formation(events: pd.DataFrame, lineups: pd.DataFrame,
                                match_id: int, team_name: str,
                                starter_ids: set = None,
                                position_map: dict = None) -> dict:
    """Reconstruct a team's actual formation from event data.
    
    Uses position_group from lineups → POSITION_MAP for reliable line
    assignment, and avg positions from events for SVG positioning.
    
    Steps:
      1. Compute average positions for each player from positional events
      2. Assign nominal line (GK/DF/MF/FW) from lineup position_group
      3. Sort by avg_x for positioning within each line
      4. Classify formation from DF/MF/FW counts
      5. Return player positions + formation info
    """
    if position_map is None:
        position_map = {
            "Goalkeeper": "GK", "Right Back": "DF", "Left Back": "DF",
            "Center Back": "DF", "Right Center Back": "DF", "Left Center Back": "DF",
            "Right Wing Back": "DF", "Left Wing Back": "DF",
            "Defensive Midfield": "MF", "Center Midfield": "MF",
            "Center Defensive Midfield": "MF", "Left Midfield": "MF", "Right Midfield": "MF",
            "Attacking Midfield": "MF", "Left Center Midfield": "MF",
            "Right Center Midfield": "MF",
            "Right Wing": "FW", "Left Wing": "FW",
            "Center Forward": "FW", "Right Center Forward": "FW",
            "Left Center Forward": "FW",
        }
    
    # Get avg positions from events
    pos_df = compute_avg_positions(events, match_id, team_name)
    if len(pos_df) == 0:
        return {"formation": "Unknown", "players": [], "line_counts": {}}
    
    if starter_ids:
        pos_df = pos_df[pos_df["player_id"].isin(starter_ids)]
    
    if len(pos_df) < 4:
        return {"formation": "Unknown", "players": [], "line_counts": {}}
    
    # Assign position_group from lineups
    team_li = lineups[
        (lineups["match_id"] == match_id)
        & (lineups["team_name"].astype(str).str.contains(team_name, case=False, na=False))
    ]
    
    def _get_pos_group(pid):
        pr = team_li[team_li["player_id"] == pid]
        if not len(pr):
            return "MF"
        try:
            positions_list = pr.iloc[0].get("positions")
            if positions_list is None or (isinstance(positions_list, float) and np.isnan(positions_list)):
                return "MF"
            for item in positions_list if hasattr(positions_list, "__iter__") else []:
                if isinstance(item, dict):
                    pos_name = item.get("position", "")
                    pg = position_map.get(pos_name)
                    if pg:
                        return pg
            return "MF"
        except Exception:
            return "MF"
    
    pos_df["position_group"] = pos_df["player_id"].apply(_get_pos_group)
    
    # Sort: GK (avg_x<25), then DF, MF, FW by avg_x within group
    def _sort_key(row):
        pg_order = {"GK": 0, "DF": 1, "MF": 2, "FW": 3}
        return (pg_order.get(row["position_group"], 4), row["avg_x"])
    
    pos_df = pos_df.sort_values("avg_x").reset_index(drop=True)
    pos_df["sort_key"] = pos_df.apply(_sort_key, axis=1)
    pos_df = pos_df.sort_values("sort_key").reset_index(drop=True)
    
    # Count per line
    gk_count = int((pos_df["position_group"] == "GK").sum())
    def_count = int((pos_df["position_group"] == "DF").sum())
    mid_count = int((pos_df["position_group"] == "MF").sum())
    fw_count = int((pos_df["position_group"] == "FW").sum())
    
    line_counts = {"defenders": def_count, "midfielders": mid_count, "forwards": fw_count}
    formation = classify_formation(line_counts)
    
    # Build jersey number lookup from lineups
    jersey_map = {}
    for _, lr in team_li.iterrows():
        jersey_map[int(lr["player_id"])] = str(lr.get("jersey_number", ""))

    # Build player list with SVG coordinates
    svg_players = []
    for _, row in pos_df.iterrows():
        pg = row["position_group"]
        label = {"GK": "GK", "DF": "DF", "MF": "MF", "FW": "FW"}.get(pg, "MF")
        p = _player_to_svg(row, 0, label)
        p["jersey_number"] = jersey_map.get(int(row["player_id"]), "")
        svg_players.append(p)
    
    return {
        "formation": formation,
        "line_counts": line_counts,
        "players": svg_players,
    }


def _player_to_svg(row, line_idx: int, position_label: str) -> dict:
    """Convert a player row to SVG coordinate format.
    
    Maps StatsBomb 120x80 pitch → 700×480 SVG viewBox.
    Y is flipped so 0 (pitch bottom) → SVG top (defensive).
    """
    avg_x = float(row["avg_x"])
    avg_y = float(row["avg_y"])
    
    svg_x = round(40 + (avg_x / PITCH_LENGTH * 620))
    svg_y = round(460 - (avg_y / PITCH_WIDTH * 440))
    
    pid = int(row["player_id"])
    pname = str(row.get("player_name", ""))
    initials = "".join(w[0].upper() for w in pname.split() if w)[:2] or "??"
    
    return {
        "player_id": pid,
        "player_name": pname,
        "initials": initials,
        "position_group": position_label,
        "position_label": position_label,
        "avg_x": round(avg_x, 1),
        "avg_y": round(avg_y, 1),
        "svg_x": max(40, min(660, svg_x)),
        "svg_y": max(20, min(460, svg_y)),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 4. MATCH STATS FOR BOTH TEAMS
# ═══════════════════════════════════════════════════════════════════════════════

def compute_team_stats(events: pd.DataFrame, match_id: int,
                       team_names: list) -> dict:
    """Compute main match statistics for both teams."""
    match_events = events[events["match_id"] == match_id].copy()
    stats = {}
    
    for team in team_names:
        te = match_events[
            match_events["team_name"].astype(str).str.contains(team, case=False, na=False)
        ]
        
        total_passes = int((te["event_type"] == "Pass").sum())
        complete_passes = int(
            ((te["event_type"] == "Pass") & (te["pass_outcome"].isna())).sum()
        )
        pass_acc = round(complete_passes / max(total_passes, 1) * 100, 1)
        
        shots = te[te["event_type"] == "Shot"]
        total_shots = len(shots)
        shots_on_target = int((shots["shot_outcome"] == "Goal").sum() +
                              (shots["shot_outcome"] == "Saved").sum())
        goals = int((shots["shot_outcome"] == "Goal").sum())
        total_xg = round(float(shots["shot_xg"].sum()), 2) if len(shots) else 0.0
        
        total_pressures = int((te["event_type"] == "Pressure").sum())
        fouls = int((te["event_type"] == "Foul Committed").sum())
        fouls_won = int((te["event_type"] == "Foul Won").sum())
        yellow_cards = int((te["event_type"] == "Bad Behaviour").sum())  # approximate
        
        carries = int((te["event_type"] == "Carry").sum())
        progressive_passes = int(te["is_progressive_pass"].sum())
        
        stats[team] = {
            "possession_pct": 0.0,  # filled below
            "total_passes": total_passes,
            "complete_passes": complete_passes,
            "pass_accuracy": pass_acc,
            "total_shots": total_shots,
            "shots_on_target": shots_on_target,
            "goals": goals,
            "total_xg": total_xg,
            "total_pressures": total_pressures,
            "fouls": fouls,
            "fouls_won": fouls_won,
            "carries": carries,
            "progressive_passes": progressive_passes,
            "yellow_cards": yellow_cards,
        }
    
    # Compute possession from pass counts
    if len(team_names) == 2:
        p1 = stats.get(team_names[0], {}).get("total_passes", 0)
        p2 = stats.get(team_names[1], {}).get("total_passes", 0)
        total = max(p1 + p2, 1)
        stats[team_names[0]]["possession_pct"] = round(p1 / total * 100, 1)
        stats[team_names[1]]["possession_pct"] = round(p2 / total * 100, 1)
    
    return stats


# ═══════════════════════════════════════════════════════════════════════════════
# 5. PASS NETWORK
# ═══════════════════════════════════════════════════════════════════════════════

def compute_pass_network(events: pd.DataFrame, match_id: int,
                          team_name: str, player_ids: list) -> list:
    """Compute pass connections between players of the same team."""
    match_events = events[events["match_id"] == match_id].sort_values("event_index")
    team_ev = match_events[
        match_events["team_name"].astype(str).str.contains(team_name, case=False, na=False)
    ]
    ev_list = team_ev.to_dict("records")
    
    pid_set = set(player_ids)
    pass_pairs = {}
    
    for i, row in enumerate(ev_list):
        if row.get("event_type") != "Pass":
            continue
        passer_id = row.get("player_id")
        pex = row.get("pass_end_x")
        pey = row.get("pass_end_y")
        if passer_id is None or pex is None or pey is None:
            continue
        
        for j in range(i + 1, min(i + 8, len(ev_list))):
            nr = ev_list[j]
            nr_id = nr.get("player_id")
            nr_type = nr.get("event_type", "")
            if nr_id is not None and nr_id != passer_id and nr_id in pid_set:
                rx = nr.get("location_x")
                ry = nr.get("location_y")
                if rx is not None and ry is not None:
                    dist = ((float(pex) - float(rx))**2 + (float(pey) - float(ry))**2)**0.5
                    if dist < 15:
                        key = (int(passer_id), int(nr_id))
                        pass_pairs[key] = pass_pairs.get(key, 0) + 1
                break
    
    return [
        {"from_player_id": f, "to_player_id": t, "count": c}
        for (f, t), c in sorted(pass_pairs.items(), key=lambda x: -x[1])
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# 6. FULL MATCH ANALYSIS (BOTH TEAMS)
# ═══════════════════════════════════════════════════════════════════════════════

def full_match_analysis(events: pd.DataFrame, lineups: pd.DataFrame,
                         match_id: int, home_team: str, away_team: str,
                         position_map: dict = None) -> dict:
    """Complete tactical analysis for both teams in a match."""
    
    def _get_starter_ids(li_df, match, team_str):
        """Get set of starting XI player IDs from lineups."""
        team_li = li_df[
            (li_df["match_id"] == match)
            & (li_df["team_name"].astype(str).str.contains(team_str, case=False, na=False))
        ]
        starter_ids = set()
        for _, r in team_li.iterrows():
            pos_val = r.get("positions")
            if pos_val is None or (isinstance(pos_val, float) and np.isnan(pos_val)):
                continue
            try:
                for item in pos_val if hasattr(pos_val, "__iter__") else []:
                    if isinstance(item, dict) and item.get("start_reason") == "Starting XI":
                        starter_ids.add(int(r["player_id"]))
            except Exception:
                continue
        return starter_ids
    
    home_starters = _get_starter_ids(lineups, match_id, home_team)
    away_starters = _get_starter_ids(lineups, match_id, away_team)
    
    home_analysis = reconstruct_team_formation(
        events, lineups, match_id, home_team, home_starters, position_map
    )
    away_analysis = reconstruct_team_formation(
        events, lineups, match_id, away_team, away_starters, position_map
    )
    
    # Pass networks
    home_player_ids = [p["player_id"] for p in home_analysis["players"]]
    away_player_ids = [p["player_id"] for p in away_analysis["players"]]
    
    home_pn = compute_pass_network(events, match_id, home_team, home_player_ids)
    away_pn = compute_pass_network(events, match_id, away_team, away_player_ids)
    
    # Map player_id to initials for pass network
    home_initials = {p["player_id"]: p["initials"] for p in home_analysis["players"]}
    away_initials = {p["player_id"]: p["initials"] for p in away_analysis["players"]}
    
    for link in home_pn:
        link["from_initials"] = home_initials.get(link["from_player_id"], "?")
        link["to_initials"] = home_initials.get(link["to_player_id"], "?")
    for link in away_pn:
        link["from_initials"] = away_initials.get(link["from_player_id"], "?")
        link["to_initials"] = away_initials.get(link["to_player_id"], "?")
    
    # Team stats
    team_stats = compute_team_stats(events, match_id, [home_team, away_team])
    
    return {
        "home": {
            "team_name": home_team,
            "formation": home_analysis["formation"],
            "line_counts": home_analysis["line_counts"],
            "players": home_analysis["players"],
            "pass_network": home_pn,
            "stats": team_stats.get(home_team, {}),
        },
        "away": {
            "team_name": away_team,
            "formation": away_analysis["formation"],
            "line_counts": away_analysis["line_counts"],
            "players": away_analysis["players"],
            "pass_network": away_pn,
            "stats": team_stats.get(away_team, {}),
        },
    }
