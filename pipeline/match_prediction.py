"""
pipeline/match_prediction.py — Match & Player Performance Prediction
Predicts technical and physical performance for upcoming matches
using historical trends, current form, and workload patterns.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge, LinearRegression
from scipy import stats as scipy_stats
from typing import Optional


class MatchPredictor:
    """
    Predicts player technical and physical performance for upcoming matches.
    Combines trend projection, recent form weighting, and workload context.
    """

    def __init__(self):
        pass

    def predict_player_next_match(self, scores: pd.DataFrame,
                                    computed: pd.DataFrame,
                                    events: pd.DataFrame,
                                    player_id: int) -> dict:
        ps = scores[scores["player_id"] == player_id].copy()
        if len(ps) < 3:
            return {"error": "Not enough matches for prediction (minimum 3)"}

        if "match_date" in ps.columns and ps["match_date"].notna().any():
            ps = ps.sort_values("match_date").reset_index(drop=True)
        else:
            ps = ps.reset_index(drop=True)

        pc = computed[computed["player_id"] == player_id].copy()
        pe = events[events["player_id"] == player_id].copy()

        # ── Technical Score Prediction ──
        n = len(ps)
        X = np.arange(n).reshape(-1, 1)
        y_score = ps["overall_score"].values
        ridge = Ridge(alpha=1.0)
        ridge.fit(X, y_score)
        trend_pred = float(ridge.predict([[n]])[0])

        recent = y_score[-min(5, n):]
        ewma_w = np.exp(np.linspace(0, 1, len(recent)))
        ewma_w = ewma_w / ewma_w.sum()
        recent_avg = float(np.average(recent, weights=ewma_w))

        predicted_score = trend_pred * 0.3 + recent_avg * 0.7
        predicted_score = max(0, min(10, predicted_score))

        residuals = y_score - ridge.predict(X)
        residual_std = np.std(residuals) if len(residuals) > 1 else 0.5
        ci_80 = 1.28 * residual_std

        # ── Dimension Score Predictions ──
        dims = ["passing_score", "shooting_score", "positioning_score",
                "pressing_score", "movement_score", "physical_score", "behavioral_score"]
        dim_predictions = {}
        for dim in dims:
            if dim in ps.columns:
                vals = ps[dim].values
                if len(vals) >= 3:
                    lr = LinearRegression()
                    lr.fit(X[:len(vals)], vals)
                    dim_pred = float(lr.predict([[n]])[0])
                    dim_predictions[dim.replace("_score", "")] = {
                        "predicted": round(max(0, min(10, dim_pred)), 2),
                        "trend_slope": round(float(lr.coef_[0]), 4),
                    }

        # ── Physical Output Prediction ──
        physical_pred = {}
        if len(pc) >= 2:
            pc_sorted = pc.sort_values("match_id") if "match_id" in pc.columns else pc

            if "total_actions" in pc_sorted.columns:
                acts = pc_sorted["total_actions"].values
                if len(acts) >= 3:
                    Xp = np.arange(len(acts)).reshape(-1, 1)
                    lr = LinearRegression()
                    lr.fit(Xp, acts)
                    pred_acts = float(lr.predict([[len(acts)]])[0])
                    recent_acts = np.mean(acts[-min(3, len(acts)):])
                    physical_pred["total_actions"] = {
                        "predicted": round(max(20, pred_acts * 0.3 + recent_acts * 0.7), 0),
                        "trend_slope": round(float(lr.coef_[0]), 4),
                    }

            if "distance_covered" in pc_sorted.columns:
                dist = pc_sorted["distance_covered"].values
                if len(dist) >= 3:
                    Xp = np.arange(len(dist)).reshape(-1, 1)
                    lr = LinearRegression()
                    lr.fit(Xp, dist)
                    pred_dist = float(lr.predict([[len(dist)]])[0])
                    recent_dist = np.mean(dist[-min(3, len(dist)):])
                    physical_pred["distance_covered"] = {
                        "predicted": round(max(5, pred_dist * 0.3 + recent_dist * 0.7), 1),
                        "trend_slope": round(float(lr.coef_[0]), 4),
                    }

            if "total_pressures" in pc_sorted.columns:
                press = pc_sorted["total_pressures"].values
                if len(press) >= 3:
                    Xp = np.arange(len(press)).reshape(-1, 1)
                    lr = LinearRegression()
                    lr.fit(Xp, press)
                    pred_press = float(lr.predict([[len(press)]])[0])
                    recent_press = np.mean(press[-min(3, len(press)):])
                    physical_pred["total_pressures"] = {
                        "predicted": round(max(0, pred_press * 0.3 + recent_press * 0.7), 0),
                        "trend_slope": round(float(lr.coef_[0]), 4),
                    }

        # ── Fatigue & Risk Context for Next Match ──
        fatigue_context = {}
        if len(pc) >= 2:
            if "activity_drop_2nd_half" in pc.columns:
                avg_drop = float(pc["activity_drop_2nd_half"].mean())
                fatigue_context["avg_second_half_drop"] = round(avg_drop, 1)
                fatigue_context["fatigue_concern"] = bool(avg_drop > 20)

            if len(ps) >= 5:
                recent_stretch = ps.tail(3)
                fatigue_context["consecutive_matches_strain"] = bool(
                    recent_stretch["overall_score"].std() > 1.5
                )

            if physical_pred and "total_actions" in physical_pred:
                pred_acts = physical_pred["total_actions"]["predicted"]
                avg_acts = float(pc["total_actions"].mean()) if "total_actions" in pc.columns else 50
                fatigue_context["workload_spike_risk"] = bool(
                    pred_acts > avg_acts * 1.3
                )

        # ── Coaching-relevant summary ──
        direction = "improving" if ridge.coef_[0] > 0.02 else (
            "declining" if ridge.coef_[0] < -0.02 else "stable"
        )

        high_intensity_concern = False
        if physical_pred and "total_pressures" in physical_pred:
            avg_p = float(pc["total_pressures"].mean()) if "total_pressures" in pc.columns else 0
            if physical_pred["total_pressures"]["predicted"] > avg_p * 1.2:
                high_intensity_concern = True

        narrative_parts = []

        if direction == "declining":
            narrative_parts.append(
                f"Projected to underperform season average based on declining trend."
            )
        elif direction == "improving":
            narrative_parts.append(
                f"Momentum is positive — expected to perform near or above season average."
            )

        if fatigue_context.get("fatigue_concern"):
            narrative_parts.append(
                f"Fatigue concern: second-half activity drop averages "
                f"{fatigue_context['avg_second_half_drop']:.0f}%. Consider managing minutes."
            )

        if fatigue_context.get("workload_spike_risk"):
            narrative_parts.append(
                f"Workload spike predicted — projected actions significantly above "
                f"season average. Rotation may be warranted."
            )

        if high_intensity_concern:
            narrative_parts.append(
                f"Pressing volume predicted to exceed normal range — monitor "
                f"recovery between matches."
            )

        if not narrative_parts:
            narrative_parts.append(
                f"Expected performance within normal range. Continue current regimen."
            )

        return {
            "player_id": int(player_id),
            "player_name": str(ps.iloc[0].get("player_name", "Unknown")),
            "position": str(ps.iloc[0].get("position_group", "Unknown")),
            "technical_prediction": {
                "predicted_overall_score": round(predicted_score, 2),
                "confidence_interval_80": round(ci_80, 2),
                "predicted_range": {
                    "lower": round(max(0, predicted_score - ci_80), 2),
                    "upper": round(min(10, predicted_score + ci_80), 2),
                },
                "current_season_avg": round(float(np.mean(y_score)), 2),
                "trend_direction": direction,
                "trend_slope": round(float(ridge.coef_[0]), 4),
                "dimension_predictions": dim_predictions,
                "matches_used": n,
            },
            "physical_prediction": physical_pred,
            "fatigue_context": fatigue_context,
            "narrative": " ".join(narrative_parts),
        }

    def predict_squad_next_match(self, scores: pd.DataFrame,
                                   computed: pd.DataFrame,
                                   events: pd.DataFrame,
                                   squad_ids: list) -> dict:
        predictions = []
        for pid in squad_ids:
            pred = self.predict_player_next_match(scores, computed, events, pid)
            if "error" not in pred:
                predictions.append(pred)

        if not predictions:
            return {"error": "No valid predictions for any squad player"}

        avg_predicted = np.mean([p["technical_prediction"]["predicted_overall_score"]
                                 for p in predictions if "technical_prediction" in p])
        avg_season = np.mean([p["technical_prediction"]["current_season_avg"]
                              for p in predictions if "technical_prediction" in p])

        declining = [p for p in predictions
                     if p.get("technical_prediction", {}).get("trend_direction") == "declining"]
        improving = [p for p in predictions
                     if p.get("technical_prediction", {}).get("trend_direction") == "improving"]
        fatigue_concerns = [p for p in predictions
                            if p.get("fatigue_context", {}).get("fatigue_concern")]

        return {
            "total_players_predicted": len(predictions),
            "squad_predicted_avg": round(avg_predicted, 2),
            "squad_season_avg": round(avg_season, 2),
            "trend_summary": {
                "improving_count": len(improving),
                "declining_count": len(declining),
                "stable_count": len(predictions) - len(improving) - len(declining),
            },
            "fatigue_concern_count": len(fatigue_concerns),
            "top_3_improving": [
                {"player_name": p["player_name"], "predicted_score": p["technical_prediction"]["predicted_overall_score"]}
                for p in sorted(improving, key=lambda x: x["technical_prediction"]["predicted_overall_score"], reverse=True)[:3]
            ] if improving else [],
            "top_3_declining": [
                {"player_name": p["player_name"], "predicted_score": p["technical_prediction"]["predicted_overall_score"]}
                for p in sorted(declining, key=lambda x: x["technical_prediction"]["predicted_overall_score"])[:3]
            ] if declining else [],
            "fatigue_concern_players": [
                {"player_name": p["player_name"], "drop_pct": p["fatigue_context"].get("avg_second_half_drop", 0)}
                for p in fatigue_concerns[:5]
            ] if fatigue_concerns else [],
            "narrative": self._build_squad_narrative(avg_predicted, avg_season,
                                                       improving, declining, fatigue_concerns),
        }

    def _build_squad_narrative(self, avg_predicted, avg_season,
                                improving, declining, fatigue_concerns) -> str:
        parts = []
        diff = avg_predicted - avg_season
        if diff > 0.3:
            parts.append(f"The squad is projected to outperform its season average "
                         f"(predicted {avg_predicted:.2f} vs {avg_season:.2f}), "
                         f"suggesting upward momentum across the team.")
        elif diff < -0.3:
            parts.append(f"The squad is projected to underperform its season average "
                         f"(predicted {avg_predicted:.2f} vs {avg_season:.2f}). "
                         f"Review tactical setup and consider changes to reverse the trend.")
        else:
            parts.append(f"The squad is projected to perform near its season average "
                         f"({avg_predicted:.2f}).")

        if declining:
            names = ", ".join(p["player_name"] for p in declining[:3])
            parts.append(f"{len(declining)} player(s) in decline: {names}. "
                         f"Consider reduced minutes or positional changes.")

        if fatigue_concerns:
            names = ", ".join(p["player_name"] for p in fatigue_concerns[:3])
            parts.append(f"Fatigue concerns for {len(fatigue_concerns)} player(s): {names}. "
                         f"Rotation recommended.")

        return " ".join(parts)
