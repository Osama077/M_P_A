"""
pipeline/coaching_guidance.py — Decision Support Engine
Translates raw metrics into plain-language tactical advice for coaches.
"""

import numpy as np
import pandas as pd
from typing import Optional

SCORE_DIMS = [
    "passing_score", "shooting_score", "positioning_score",
    "pressing_score", "movement_score", "physical_score", "behavioral_score"
]
DIM_LABELS = {
    "passing_score": "Passing", "shooting_score": "Shooting",
    "positioning_score": "Positioning", "pressing_score": "Pressing",
    "movement_score": "Movement", "physical_score": "Physical",
    "behavioral_score": "Behavioral"
}


class CoachingGuidanceEngine:
    def __init__(self):
        pass

    def generate_squad_guidance(self, match_context: dict, team_stats: dict,
                                  players: list, season_stats: dict) -> list:
        advices = []

        # Attacking efficiency
        if team_stats.get("total_xg") and team_stats.get("goals_for") is not None:
            xg = team_stats["total_xg"]
            gf = team_stats["goals_for"]
            if gf is not None and xg > 1.5:
                diff = gf - xg
                if diff > 1.0:
                    advices.append({
                        "category": "attacking",
                        "priority": "high",
                        "suggestion": (f"The team overperformed xG by {diff:.1f} ({gf} goals from {xg:.1f} xG). "
                                       f"Clinical finishing masks potential chance-creation issues — "
                                       f"if finishing regresses to mean, scoring could drop. "
                                       f"Consider drilling high-volume chance creation in training."),
                        "metric": f"Goals {gf} vs xG {xg:.1f}",
                        "icon": "goal",
                    })
                elif diff < -0.5:
                    advices.append({
                        "category": "attacking",
                        "priority": "high",
                        "suggestion": (f"The team underperformed xG by {abs(diff):.1f} ({gf} goals from {xg:.1f} xG). "
                                       f"Finishing efficiency needs attention — review shot placement and "
                                       f"composure drills in training."),
                        "metric": f"Goals {gf} vs xG {xg:.1f}",
                        "icon": "goal",
                    })

        if team_stats.get("pass_accuracy"):
            pa = team_stats["pass_accuracy"]
            if pa and pa > 88:
                advices.append({
                    "category": "build_up",
                    "priority": "medium",
                    "suggestion": (f"Pass accuracy at {pa:.1f}% shows strong ball retention. "
                                   f"Consider increasing tempo and forward penetration — "
                                   f"safe possession alone does not create chances."),
                    "metric": f"Pass accuracy {pa:.1f}%",
                    "icon": "pass",
                })
            elif pa and pa < 78:
                advices.append({
                    "category": "build_up",
                    "priority": "high",
                    "suggestion": (f"Pass accuracy at {pa:.1f}% is below competitive threshold. "
                                   f"Focus on short-pass patterns under pressure in training. "
                                   f"Consider simplifying the build-up structure."),
                    "metric": f"Pass accuracy {pa:.1f}%",
                    "icon": "pass",
                })

        # Pressing intensity
        if team_stats.get("total_pressures"):
            tp = team_stats["total_pressures"]
            if tp and tp > 70:
                advices.append({
                    "category": "defensive",
                    "priority": "medium",
                    "suggestion": (f"High pressing volume ({tp} pressures). "
                                   f"Effective for disrupting opponent build-up but requires "
                                   f"excellent fitness. Monitor second-half drop-off in press intensity."),
                    "metric": f"{tp} pressures",
                    "icon": "pressure",
                })
            elif tp and tp < 40:
                advices.append({
                    "category": "defensive",
                    "priority": "high",
                    "suggestion": (f"Low pressing output ({tp} pressures). "
                                   f"The team may be sitting too deep or failing to trigger "
                                   f"counter-press after turnovers. Consider a structured pressing trigger."),
                    "metric": f"{tp} pressures",
                    "icon": "pressure",
                })

        # Possession
        if team_stats.get("possession_pct"):
            pos = team_stats["possession_pct"]
            if pos and pos > 65:
                advices.append({
                    "category": "build_up",
                    "priority": "low",
                    "suggestion": (f"Dominant possession ({pos:.0f}%). Ensure possession translates "
                                   f"to territory and chances — sterile dominance without penetration "
                                   f"leaves the team vulnerable to counters."),
                    "metric": f"{pos:.0f}% possession",
                    "icon": "possession",
                })
            elif pos and pos < 45:
                advices.append({
                    "category": "build_up",
                    "priority": "high",
                    "suggestion": (f"Low possession ({pos:.0f}%). The team struggles to retain the ball. "
                                   f"Consider adjusting build-up structure or adding a midfield "
                                   f"option to improve ball retention under pressure."),
                    "metric": f"{pos:.0f}% possession",
                    "icon": "possession",
                })

        # Squad score
        if team_stats.get("avg_overall_score"):
            avg = team_stats["avg_overall_score"]
            if avg and avg > 7.5:
                advices.append({
                    "category": "morale",
                    "priority": "low",
                    "suggestion": (f"The squad averaged {avg:.2f}/10 — a strong collective performance. "
                                   f"Maintain current tactical setup and squad morale."),
                    "metric": f"Squad avg {avg:.2f}",
                    "icon": "performance",
                })
            elif avg and avg < 6.0:
                advices.append({
                    "category": "morale",
                    "priority": "high",
                    "suggestion": (f"The squad averaged only {avg:.2f}/10 — well below typical performance. "
                                   f"Consider tactical adjustments or personnel changes for the next match."),
                    "metric": f"Squad avg {avg:.2f}",
                    "icon": "performance",
                })

        return advices

    def generate_player_guidance(self, player_info: dict, match_scores: dict,
                                   match_stats: dict, percentiles: list,
                                   season_stats: dict, trend_data: list) -> list:
        advices = []
        pname = player_info.get("player_name", "Player")
        pgroup = player_info.get("position_group", "")

        # Trend-based
        trend = player_info.get("performance_trend", "Stable")
        trend_val = player_info.get("trend_value", 0)
        if trend == "Declining" and trend_val and trend_val < -0.3:
            advices.append({
                "category": "form",
                "priority": "high",
                "suggestion": (f"{pname} is in a significant decline (delta {trend_val:.2f}). "
                               f"Review recent training load, tactical role, or personal factors. "
                               f"Consider reduced minutes or positional adjustment to regain confidence."),
                "metric": f"Trend delta {trend_val:.2f}",
                "icon": "trending-down",
            })
        elif trend == "Improving" and trend_val and trend_val > 0.3:
            advices.append({
                "category": "form",
                "priority": "medium",
                "suggestion": (f"{pname} is in strong upward form (+{trend_val:.2f}). "
                               f"Capitalize on this momentum — consider giving more responsibility "
                               f"in the upcoming match."),
                "metric": f"Trend delta +{trend_val:.2f}",
                "icon": "trending-up",
            })

        # Dimension-specific
        if match_scores:
            dims_sorted = sorted(match_scores.items(), key=lambda x: x[1] or 0)
            lowest_dim = dims_sorted[0] if dims_sorted else (None, None)
            highest_dim = dims_sorted[-1] if dims_sorted else (None, None)

            if lowest_dim[1] is not None and lowest_dim[1] < 5.0:
                label = lowest_dim[0].replace("_score", "").capitalize()
                advices.append({
                    "category": "weakness",
                    "priority": "high",
                    "suggestion": (f"{pname}'s {label} score is only {lowest_dim[1]:.1f}/10 — "
                                   f"the weakest dimension. {'For a ' + pgroup + ', ' if pgroup else ''}"
                                   f"this is a critical area to address in individual training."),
                    "metric": f"{label} {lowest_dim[1]:.1f}",
                    "icon": "alert-triangle",
                })

            if highest_dim[1] is not None and highest_dim[1] > 8.0:
                label = highest_dim[0].replace("_score", "").capitalize()
                advices.append({
                    "category": "strength",
                    "priority": "low",
                    "suggestion": (f"{pname} excels in {label} ({highest_dim[1]:.1f}/10). "
                                   f"Design attacking patterns that leverage this strength."),
                    "metric": f"{label} {highest_dim[1]:.1f}",
                    "icon": "award",
                })

        # Performance relative to position average
        if season_stats.get("season_avg") and player_info.get("season_avg"):
            sa = season_stats["season_avg"]
            pa = player_info["season_avg"]
            if pa and sa:
                diff = pa - sa
                if diff > 1.0:
                    advices.append({
                        "category": "performance",
                        "priority": "low",
                        "suggestion": (f"{pname} averages {pa:.2f} vs squad average {sa:.2f} — "
                                       f"a top performer. Key player to build around tactically."),
                        "metric": f"+{diff:.1f} above squad avg",
                        "icon": "star",
                    })

        # xG analysis
        if match_stats:
            goal_stat = match_stats.get("goals", 0)
            xg_stat = match_stats.get("total_xg", 0)
            if xg_stat and goal_stat is not None:
                xg_diff = goal_stat - xg_stat
                if xg_diff > 0.5:
                    advices.append({
                        "category": "finishing",
                        "priority": "medium",
                        "suggestion": (f"{pname} scored {goal_stat} from {xg_stat:.2f} xG "
                                       f"(overperformance of +{xg_diff:.2f}). Clinical finishing "
                                       f"but may not be sustainable — expect regression."),
                        "metric": f"Goals {goal_stat} vs xG {xg_stat:.2f}",
                        "icon": "target",
                    })
                elif xg_diff < -0.5:
                    advices.append({
                        "category": "finishing",
                        "priority": "medium",
                        "suggestion": (f"{pname} scored {goal_stat} from {xg_stat:.2f} xG "
                                       f"(underperformance of {xg_diff:.2f}). Finishing form should "
                                       f"improve — chances are being created."),
                        "metric": f"Goals {goal_stat} vs xG {xg_stat:.2f}",
                        "icon": "target",
                    })

        # Distance covered (physical output)
        if match_stats and match_stats.get("distance_covered"):
            dc = match_stats["distance_covered"]
            if dc and dc > 10:
                advices.append({
                    "category": "physical",
                    "priority": "low",
                    "suggestion": (f"{pname} covered {dc:.1f}km — high work rate. "
                                   f"Monitor recovery if this is sustained across consecutive matches."),
                    "metric": f"{dc:.1f}km distance",
                    "icon": "activity",
                })
            elif dc and dc < 7:
                advices.append({
                    "category": "physical",
                    "priority": "medium",
                    "suggestion": (f"{pname} covered only {dc:.1f}km — below expected output "
                                   f"for {'a ' + pgroup if pgroup else 'the position'}."
                                   f"Assess fitness or tactical discipline."),
                    "metric": f"{dc:.1f}km distance",
                    "icon": "activity",
                })

        return advices

    def generate_momentum_guidance(self, momentum_data: dict) -> list:
        advices = []
        if "error" in momentum_data:
            return advices

        ms = momentum_data.get("momentum_score", 0)
        label = momentum_data.get("momentum_label", "Neutral")
        sig = momentum_data.get("statistical_significant", False)

        if label == "Strong Negative" and sig:
            advices.append({
                "category": "momentum",
                "priority": "high",
                "suggestion": (f"Strong negative momentum detected (score {ms:.2f}). "
                               f"The player's recent performances are significantly below their usual standard. "
                               f"Consider a break from starting XI or a positional change."),
                "metric": f"Momentum {ms:.2f}",
                "icon": "trending-down",
            })
        elif label == "Strong Positive" and sig:
            advices.append({
                "category": "momentum",
                "priority": "medium",
                "suggestion": (f"Strong positive momentum (score {ms:.2f}). "
                               f"The player is in career-best form — maximize minutes "
                               f"and design attacking patterns around them."),
                "metric": f"Momentum {ms:.2f}",
                "icon": "trending-up",
            })

        streak = momentum_data.get("streak", {})
        if streak.get("direction") == "declining" and streak.get("length", 0) >= 3:
            advices.append({
                "category": "streak",
                "priority": "medium",
                "suggestion": (f"The player is on a {streak['length']}-match declining streak. "
                               f"Performance analysis shows a pattern — intervene before confidence drops further."),
                "metric": f"{streak['length']}-match decline",
                "icon": "trending-down",
            })

        return advices

    def generate_consistency_guidance(self, consistency_data: dict) -> list:
        advices = []
        if "error" in consistency_data:
            return advices

        cs = consistency_data.get("consistency_score", 5)
        cv = consistency_data.get("coefficient_of_variation", 0)
        label = consistency_data.get("consistency_label", "Moderate")

        if label == "Inconsistent":
            advices.append({
                "category": "consistency",
                "priority": "high",
                "suggestion": (f"Highly inconsistent performer (score {cs:.1f}/10, CV {cv:.3f}). "
                               f"Performance fluctuates significantly match-to-match. "
                               f"Identify environmental factors (home/away, opponent strength, "
                               f"tactical role) that correlate with good vs bad performances."),
                "metric": f"Consistency {cs:.1f}",
                "icon": "activity",
            })
        elif label == "Very Consistent":
            advices.append({
                "category": "consistency",
                "priority": "low",
                "suggestion": (f"Very consistent performer (score {cs:.1f}/10). "
                               f"Reliable player who delivers predictable output — ideal for "
                               f"roles requiring tactical discipline."),
                "metric": f"Consistency {cs:.1f}",
                "icon": "check-circle",
            })

        dim_cons = consistency_data.get("dimension_consistency", {})
        if dim_cons:
            most_var = max(dim_cons, key=dim_cons.get)
            if dim_cons[most_var] > 0.3:
                advices.append({
                    "category": "consistency",
                    "priority": "medium",
                    "suggestion": (f"Most variable dimension: {most_var.capitalize()} "
                                   f"(CV {dim_cons[most_var]:.3f}). "
                                   f"This fluctuates heavily — investigate whether tactical role "
                                   f"changes or opponent quality drives the variance."),
                    "metric": f"{most_var.capitalize()} var {dim_cons[most_var]:.3f}",
                    "icon": "bar-chart",
                })

        return advices

    def generate_injury_guidance(self, injury_data: dict) -> list:
        advices = []
        if "error" in injury_data:
            return advices

        risk = injury_data.get("risk_score", 0)
        level = injury_data.get("risk_level", "Low")

        if level == "High":
            advices.append({
                "category": "injury",
                "priority": "high",
                "suggestion": (f"High injury risk detected (score {risk:.1f}/10). "
                               f"ACWR imbalance suggests the player's acute workload exceeds "
                               f"chronic capacity. Immediate load management recommended — "
                               f"consider reduced minutes or rest for the next match."),
                "metric": f"Risk {risk:.1f}/10",
                "icon": "alert-triangle",
            })

            factors = injury_data.get("risk_factors", [])
            for f in factors[:2]:
                if "fatigue" in f.get("factor", ""):
                    advices.append({
                        "category": "injury",
                        "priority": "medium",
                        "suggestion": (f"Fatigue indicator flagged (contribution {f['contribution']:.1f}). "
                                       f"Second-half performance drop-off suggests fitness or "
                                       f"recovery issue — review sleep, nutrition, and training load."),
                        "metric": f"Fatigue +{f['contribution']:.1f}",
                        "icon": "clock",
                    })

        elif level == "Moderate":
            advices.append({
                "category": "injury",
                "priority": "medium",
                "suggestion": (f"Moderate injury risk ({risk:.1f}/10). "
                               f"Monitor training intensity and consider proactive rotation "
                               f"before the workload becomes problematic."),
                "metric": f"Risk {risk:.1f}/10",
                "icon": "alert-circle",
            })

        return advices

    def generate_anomaly_guidance(self, anomaly_data: dict) -> list:
        advices = []
        if "error" in anomaly_data:
            return advices

        overall = anomaly_data.get("overall_anomalies", [])
        contextual = anomaly_data.get("contextual_anomalies", [])
        rate = anomaly_data.get("anomaly_rate", 0)

        if rate > 0.2:
            advices.append({
                "category": "anomaly",
                "priority": "medium",
                "suggestion": (f"High anomaly rate ({rate:.0%} of matches are anomalous). "
                               f"The player's performance is erratic with frequent outliers. "
                               f"Investigate whether external factors (injury, tactical changes, "
                               f"opponent quality) explain these swings."),
                "metric": f"Anomaly rate {rate:.0%}",
                "icon": "activity",
            })

        underperformances = [a for a in overall if a.get("type") == "underperformance"]
        if len(underperformances) >= 2:
            advices.append({
                "category": "anomaly",
                "priority": "high",
                "suggestion": (f"{len(underperformances)} underperformance anomalies detected. "
                               f"Pattern suggests the player may be struggling against specific "
                               f"opponent types or tactical setups. Review opposition quality "
                               f"correlation."),
                "metric": f"{len(underperformances)} underperf.",
                "icon": "trending-down",
            })

        return advices

    def generate_comparison_guidance(self, comparison_data: dict,
                                      dims_p1: dict, dims_p2: dict,
                                      p1_name: str, p2_name: str) -> list:
        advices = []
        diffs = []
        for key, label in [("passing", "Passing"), ("shooting", "Shooting"),
                           ("positioning", "Positioning"), ("pressing", "Pressing"),
                           ("movement", "Movement"), ("physical", "Physical"),
                           ("behavioral", "Behavioral")]:
            v1 = dims_p1.get(key, 0) or 0
            v2 = dims_p2.get(key, 0) or 0
            diffs.append((label, v1 - v2, v1, v2))

        diffs.sort(key=lambda x: abs(x[1]), reverse=True)

        if diffs:
            top_label, top_diff, v1, v2 = diffs[0]
            if abs(top_diff) > 1.5:
                winner = p1_name if top_diff > 0 else p2_name
                loser = p2_name if top_diff > 0 else p1_name
                advices.append({
                    "category": "comparison",
                    "priority": "high",
                    "suggestion": (f"When choosing between {p1_name} and {p2_name}, the decisive "
                                   f"factor is {top_label} ({winner}: {max(v1,v2):.1f} vs {loser}: {min(v1,v2):.1f}, "
                                   f"gap of {abs(top_diff):.1f}). {'Start ' + winner if abs(top_diff) > 2.0 else 'Consider ' + winner + ' if ' + top_label.lower() + ' is critical for the game plan.'}"),
                    "metric": f"{top_label} gap {abs(top_diff):.1f}",
                    "icon": "users",
                })

        return advices

    def generate_forecast_guidance(self, forecast_data: dict, player_name: str) -> list:
        advices = []
        if "error" in forecast_data:
            return advices

        direction = forecast_data.get("trend_direction", "stable")
        predicted = forecast_data.get("predicted_next")
        current = forecast_data.get("current_avg")
        r2 = forecast_data.get("r_squared", 0)

        if direction == "declining" and r2 > 0.3:
            advices.append({
                "category": "forecast",
                "priority": "high",
                "suggestion": (f"{player_name}'s performance trend is declining (R²={r2:.2f}). "
                               f"Model predicts next match score of {predicted:.2f} vs current avg {current:.2f}. "
                               f"Consider tactical adjustment or reduced role to arrest the decline."),
                "metric": f"Predicted {predicted:.2f}",
                "icon": "trending-down",
            })
        elif direction == "improving" and r2 > 0.3:
            advices.append({
                "category": "forecast",
                "priority": "medium",
                "suggestion": (f"{player_name} is on an upward trajectory (R²={r2:.2f}). "
                               f"Projected next score {predicted:.2f} vs current avg {current:.2f}. "
                               f"Give increased minutes to capitalize on rising form."),
                "metric": f"Predicted {predicted:.2f}",
                "icon": "trending-up",
            })

        return advices

    def generate_all_guidance(self, context: str, **kwargs) -> dict:
        squad = kwargs.get("squad")
        player = kwargs.get("player")
        momentum = kwargs.get("momentum")
        consistency = kwargs.get("consistency")
        injury = kwargs.get("injury")
        anomaly = kwargs.get("anomaly")
        comparison = kwargs.get("comparison")
        forecast = kwargs.get("forecast")

        all_advice = []

        if squad:
            all_advice.extend(self.generate_squad_guidance(**squad))
        if player:
            all_advice.extend(self.generate_player_guidance(**player))
        if momentum:
            all_advice.extend(self.generate_momentum_guidance(momentum))
        if consistency:
            all_advice.extend(self.generate_consistency_guidance(consistency))
        if injury:
            all_advice.extend(self.generate_injury_guidance(injury))
        if anomaly:
            all_advice.extend(self.generate_anomaly_guidance(anomaly))
        if comparison:
            all_advice.extend(self.generate_comparison_guidance(**comparison))
        if forecast:
            all_advice.extend(self.generate_forecast_guidance(forecast, kwargs.get("player_name", "Player")))

        return {
            "context": context,
            "total_insights": len(all_advice),
            "high_priority_count": sum(1 for a in all_advice if a["priority"] == "high"),
            "insights": all_advice,
        }
