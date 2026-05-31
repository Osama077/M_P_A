"""
pipeline/advanced_analysis.py — ML-Driven Advanced Player Analysis
Provides forecasting, anomaly detection, similarity matching, consistency scoring,
momentum analysis, and injury risk estimation.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity
from scipy import stats as scipy_stats
from typing import Optional
from config import DATA_DIR
from utils.helpers import normalize_to_score

SCORE_DIMS = [
    "passing_score", "shooting_score", "positioning_score",
    "pressing_score", "movement_score", "physical_score", "behavioral_score"
]


class PerformanceForecaster:
    """
    Predicts future player performance using linear trend + exponential smoothing.
    Returns forecasted score with confidence intervals.
    """

    def __init__(self, confidence: float = 0.80):
        self.confidence = confidence

    def forecast(self, scores: pd.DataFrame) -> dict:
        if len(scores) < 3:
            return {"error": "Not enough matches for forecasting (minimum 3)"}

        df = scores.copy()
        if "match_date" in df.columns and df["match_date"].notna().any():
            df = df.sort_values("match_date").reset_index(drop=True)
        else:
            df = df.reset_index(drop=True)
        X = np.arange(len(df)).reshape(-1, 1)
        y = df["overall_score"].values

        model = Ridge(alpha=1.0)
        model.fit(X, y)
        trend = model.predict(X)

        residuals = y - trend
        residual_std = np.std(residuals) if len(residuals) > 1 else 0.5
        z = scipy_stats.norm.ppf(1 - (1 - self.confidence) / 2)

        next_idx = np.array([[len(df)]])
        predicted = float(model.predict(next_idx)[0])
        ci = z * residual_std

        recent = df.tail(5)
        ewma_weights = np.exp(np.linspace(0, 1, len(recent)))
        ewma_weights = ewma_weights / ewma_weights.sum()
        smoothed_recent = float(np.average(recent["overall_score"].values, weights=ewma_weights))

        blend = predicted * 0.4 + smoothed_recent * 0.6

        return {
            "current_avg": round(float(y.mean()), 4),
            "trend_slope": round(float(model.coef_[0]), 4),
            "trend_direction": "improving" if model.coef_[0] > 0.03 else ("declining" if model.coef_[0] < -0.03 else "stable"),
            "predicted_next": round(max(0, min(10, blend)), 4),
            "confidence_interval": round(ci, 4),
            "predicted_range": {
                "lower": round(max(0, blend - ci), 4),
                "upper": round(min(10, blend + ci), 4)
            },
            "matches_used": len(df),
            "r_squared": round(float(model.score(X, y)), 4),
            "trend_line": [round(float(v), 4) for v in trend],
            "actual_values": [round(float(v), 4) for v in y],
        }


class AnomalyDetector:
    """
    Detects anomalous performances using Z-score and Isolation Forest.
    Flags outlier matches and contextual anomalies.
    """

    def __init__(self, z_threshold: float = 2.0, contamination: float = 0.1):
        self.z_threshold = z_threshold
        self.contamination = contamination

    def detect(self, scores: pd.DataFrame, computed: pd.DataFrame = None) -> dict:
        if len(scores) < 4:
            return {"error": "Not enough matches for anomaly detection (minimum 4)"}

        df = scores.copy()
        if "match_date" in df.columns and df["match_date"].notna().any():
            df = df.sort_values("match_date").reset_index(drop=True)
        else:
            df = df.reset_index(drop=True)

        overall = df["overall_score"].values
        z_scores = np.abs(scipy_stats.zscore(overall, nan_policy="omit"))

        anomalies_overall = []
        for i, (_, row) in enumerate(df.iterrows()):
            if z_scores[i] > self.z_threshold:
                anomalies_overall.append({
                    "match_id": int(row["match_id"]) if pd.notna(row.get("match_id")) else None,
                    "match_date": str(row.get("match_date", "")),
                    "overall_score": float(row["overall_score"]),
                    "z_score": round(float(z_scores[i]), 4),
                    "type": "outlier" if row["overall_score"] > df["overall_score"].mean() else "underperformance",
                    "severity": "high" if z_scores[i] > 2.5 else "medium",
                })

        multi_dim_anomalies = []
        if computed is not None and len(computed) >= 5:
            merged = df.merge(
                computed[["match_id", "player_id", "total_actions", "distance_covered",
                          "pass_accuracy", "total_pressures", "activity_drop_2nd_half"]],
                on=["match_id", "player_id"], how="left"
            ).fillna(0)

            feature_cols = ["overall_score", "total_actions", "distance_covered",
                            "pass_accuracy", "total_pressures"]
            available = [c for c in feature_cols if c in merged.columns]
            if len(available) >= 3 and len(merged) >= 5:
                X = MinMaxScaler().fit_transform(merged[available].values)
                iso = IsolationForest(
                    contamination=self.contamination,
                    random_state=42,
                    n_estimators=50
                )
                preds = iso.fit_predict(X)

                for i, (_, row) in enumerate(merged.iterrows()):
                    if preds[i] == -1:
                        multi_dim_anomalies.append({
                            "match_id": int(row["match_id"]) if pd.notna(row.get("match_id")) else None,
                            "match_date": str(row.get("match_date", "")),
                            "overall_score": float(row["overall_score"]),
                            "total_actions": int(row.get("total_actions", 0)),
                            "anomaly_type": "contextual_anomaly",
                        })

        return {
            "total_matches": len(df),
            "overall_anomalies_count": len(anomalies_overall),
            "contextual_anomalies_count": len(multi_dim_anomalies),
            "anomaly_rate": round((len(anomalies_overall) + len(multi_dim_anomalies)) / len(df), 4),
            "overall_anomalies": anomalies_overall[:10],
            "contextual_anomalies": multi_dim_anomalies[:10],
            "z_score_summary": {
                "mean": round(float(np.mean(z_scores)), 4),
                "max": round(float(np.max(z_scores)), 4),
                "threshold": self.z_threshold,
            }
        }


class PlayerSimilarityEngine:
    """
    Finds similar players using cosine similarity on normalized dimension scores.
    """

    def __init__(self, top_n: int = 10):
        self.top_n = top_n

    def find_similar(self, player_id: int, scores_df: pd.DataFrame) -> dict:
        dims = [c for c in SCORE_DIMS if c in scores_df.columns]
        if len(dims) < 3:
            return {"error": "Not enough dimension columns for similarity"}

        season_avg = scores_df.groupby(["player_id", "player_name", "position_group"])[dims].mean().reset_index()
        dim_data = season_avg[dims].fillna(0).values
        scaler = MinMaxScaler()
        dim_norm = scaler.fit_transform(dim_data)

        target_mask = season_avg["player_id"] == player_id
        if not target_mask.any():
            return {"error": f"Player {player_id} not found"}

        target_vec = dim_norm[target_mask.values].reshape(1, -1)
        sims = cosine_similarity(target_vec, dim_norm).flatten()

        similar_indices = np.argsort(sims)[::-1]
        results = []
        for idx in similar_indices:
            if sims[idx] >= 0.85 or len(results) < 3:
                pid = season_avg.iloc[idx]["player_id"]
                if pid != player_id:
                    player_dims = {}
                    for d in dims:
                        val = season_avg.iloc[idx][d]
                        player_dims[d.replace("_score", "")] = round(float(val) if pd.notna(val) else 0, 4)

                    results.append({
                        "player_id": int(pid),
                        "player_name": str(season_avg.iloc[idx]["player_name"]),
                        "position": str(season_avg.iloc[idx].get("position_group", "Unknown")),
                        "similarity_score": round(float(sims[idx]), 4),
                        "scores": player_dims,
                    })
            if len(results) >= self.top_n:
                break

        target_dims = {}
        target_row = season_avg[target_mask].iloc[0]
        for d in dims:
            val = target_row[d]
            target_dims[d.replace("_score", "")] = round(float(val) if pd.notna(val) else 0, 4)

        return {
            "target_player": {
                "player_id": int(player_id),
                "player_name": str(target_row["player_name"]),
                "position": str(target_row.get("position_group", "Unknown")),
                "scores": target_dims,
            },
            "similar_players": results,
            "total_players_compared": len(season_avg),
        }


class ConsistencyAnalyzer:
    """
    Measures performance consistency across matches using coefficient of variation.
    """

    def analyze(self, scores: pd.DataFrame) -> dict:
        if len(scores) < 3:
            return {"error": "Not enough matches (minimum 3)"}

        df = scores.copy()
        if "match_date" in df.columns and df["match_date"].notna().any():
            df = df.sort_values("match_date").reset_index(drop=True)
        else:
            df = df.reset_index(drop=True)
        overall = df["overall_score"].values

        mean_score = np.mean(overall)
        std_score = np.std(overall)
        cv = std_score / mean_score if mean_score > 0 else 1.0

        half = len(df) // 2
        first_half = df["overall_score"].iloc[:half].values
        second_half = df["overall_score"].iloc[half:].values

        cv_first = np.std(first_half) / np.mean(first_half) if np.mean(first_half) > 0 else 1.0
        cv_second = np.std(second_half) / np.mean(second_half) if np.mean(second_half) > 0 else 1.0

        dim_consistency = {}
        for dim in SCORE_DIMS:
            if dim in df.columns:
                vals = df[dim].dropna().values
                if len(vals) >= 3:
                    d_cv = np.std(vals) / np.mean(vals) if np.mean(vals) > 0 else 1.0
                    dim_consistency[dim.replace("_score", "")] = round(float(d_cv), 4)

        consistency_score = max(0, min(10, 10 - cv * 5))

        return {
            "consistency_score": round(float(consistency_score), 4),
            "coefficient_of_variation": round(float(cv), 4),
            "std_dev": round(float(std_score), 4),
            "mean_score": round(float(mean_score), 4),
            "matches_analyzed": len(df),
            "first_half_cv": round(float(cv_first), 4),
            "second_half_cv": round(float(cv_second), 4),
            "consistency_trend": "improving" if cv_second < cv_first * 0.85 else (
                "declining" if cv_second > cv_first * 1.15 else "stable"),
            "dimension_consistency": dim_consistency,
            "consistency_label": "Very Consistent" if consistency_score >= 8 else (
                "Consistent" if consistency_score >= 6 else (
                    "Moderate" if consistency_score >= 4 else "Inconsistent")),
        }


class MomentumAnalyzer:
    """
    Analyzes player momentum using exponentially weighted moving averages.
    Compares recent form against historical baseline.
    """

    def analyze(self, scores: pd.DataFrame) -> dict:
        if len(scores) < 5:
            return {"error": "Not enough matches for momentum analysis (minimum 5)"}

        df = scores.copy()
        if "match_date" in df.columns and df["match_date"].notna().any():
            df = df.sort_values("match_date").reset_index(drop=True)
        else:
            df = df.reset_index(drop=True)
        values = df["overall_score"].values
        weights = np.exp(np.linspace(0, 2, len(values)))
        weights = weights / weights.sum()
        ewma = np.sum(values * weights)

        recent_n = min(5, len(values))
        recent_avg = np.mean(values[-recent_n:])
        early_avg = np.mean(values[:recent_n]) if len(values) >= recent_n * 2 else np.mean(values[:-recent_n])

        momentum_raw = (recent_avg - early_avg) / (early_avg + 0.01)
        momentum_score = max(-1, min(1, momentum_raw))

        dim_momentum = {}
        for dim in ["passing_score", "shooting_score", "positioning_score",
                     "pressing_score", "movement_score"]:
            if dim in df.columns:
                vals = df[dim].values
                d_recent = np.mean(vals[-recent_n:])
                d_early = np.mean(vals[:recent_n]) if len(vals) >= recent_n * 2 else np.mean(vals[:-recent_n])
                if d_early > 0:
                    dim_momentum[dim.replace("_score", "")] = round(float((d_recent - d_early) / d_early), 4)

        streak = self._compute_streak(values)

        return {
            "momentum_score": round(float(momentum_score), 4),
            "momentum_label": "Strong Positive" if momentum_score > 0.3 else (
                "Positive" if momentum_score > 0.1 else (
                    "Neutral" if momentum_score > -0.1 else (
                        "Negative" if momentum_score > -0.3 else "Strong Negative"))),
            "recent_average": round(float(recent_avg), 4),
            "historical_average": round(float(early_avg), 4),
            "overall_average": round(float(np.mean(values)), 4),
            "recent_matches": recent_n,
            "total_matches": len(df),
            "last_5_scores": [round(float(v), 4) for v in values[-recent_n:]],
            "dimension_momentum": dim_momentum,
            "streak": streak,
        }

    def _compute_streak(self, values: np.ndarray) -> dict:
        if len(values) < 3:
            return {"direction": "stable", "length": 0}

        recent = values[-3:]
        if all(recent[i] >= recent[i - 1] for i in range(1, len(recent))):
            direction = "improving"
        elif all(recent[i] <= recent[i - 1] for i in range(1, len(recent))):
            direction = "declining"
        else:
            direction = "mixed"

        streak_len = 0
        for i in range(len(values) - 1, 0, -1):
            if (direction == "improving" and values[i] >= values[i - 1]) or \
               (direction == "declining" and values[i] <= values[i - 1]):
                streak_len += 1
            else:
                break

        return {
            "direction": direction,
            "length": streak_len,
        }


class InjuryRiskEstimator:
    """
    Estimates injury risk proxy based on physical load, activity patterns,
    behavioral flags, and accumulated fatigue indicators.
    """

    def estimate(self, player_id: int, scores: pd.DataFrame, computed: pd.DataFrame,
                 events: pd.DataFrame) -> dict:
        if len(scores) < 3:
            return {"error": "Not enough data for risk estimation"}

        player_scores = scores[scores["player_id"] == player_id].copy()
        player_computed = computed[computed["player_id"] == player_id].copy()
        player_events = events[events["player_id"] == player_id].copy()

        if len(player_scores) == 0:
            return {"error": f"No data for player {player_id}"}

        risk_factors = []

        total_actions_avg = player_computed["total_actions"].mean() if "total_actions" in player_computed.columns else 50
        total_actions_norm = min(1, total_actions_avg / 80)
        risk_factors.append(("high_workload", total_actions_norm * 3))

        if "activity_drop_2nd_half" in player_computed.columns:
            drop_avg = player_computed["activity_drop_2nd_half"].mean()
            drop_risk = min(1, max(0, drop_avg / 50))
            risk_factors.append(("fatigue_drop", drop_risk * 2.5))

        if "total_pressures" in player_computed.columns:
            press_avg = player_computed["total_pressures"].mean()
            press_risk = min(1, press_avg / 30)
            risk_factors.append(("high_intensity", press_risk * 2))

        behavioral_risk = 0
        if "yellow_cards" in player_computed.columns:
            yc = player_computed["yellow_cards"].sum()
            behavioral_risk += min(2, yc * 0.5)
        if "red_cards" in player_computed.columns:
            rc = player_computed["red_cards"].sum()
            behavioral_risk += min(3, rc * 1.5)
        if "fouls_committed" in player_computed.columns:
            fouls = player_computed["fouls_committed"].sum()
            behavioral_risk += min(2, fouls * 0.1)
        risk_factors.append(("behavioral", min(3, behavioral_risk)))

        if len(player_scores) >= 5:
            ps_sorted = player_scores.copy()
            if "match_date" in ps_sorted.columns and ps_sorted["match_date"].notna().any():
                ps_sorted = ps_sorted.sort_values("match_date")
            recent_scores = ps_sorted.tail(5)
            score_drop = recent_scores["overall_score"].iloc[-1] - recent_scores["overall_score"].iloc[0]
            if score_drop < -1.5:
                risk_factors.append(("performance_decline", 1.5))

        total_risk = sum(v for _, v in risk_factors)
        risk_score = min(10, max(0, total_risk))

        return {
            "risk_score": round(risk_score, 2),
            "risk_level": "High" if risk_score >= 7 else (
                "Moderate" if risk_score >= 4 else "Low"),
            "risk_factors": [
                {"factor": name, "contribution": round(val, 2)}
                for name, val in sorted(risk_factors, key=lambda x: x[1], reverse=True)
            ],
            "total_actions_avg": round(float(total_actions_avg), 1),
            "matches_analyzed": len(player_scores),
            "recommendations": self._generate_recommendations(risk_score, risk_factors),
        }

    def _generate_recommendations(self, risk_score: float, risk_factors: list) -> list:
        recs = []
        if risk_score >= 7:
            recs.append("Consider load management and reduced training intensity")
        if risk_score >= 5:
            recs.append("Monitor playing time and watch for fatigue indicators")
        if any(name == "high_workload" for name, _ in risk_factors):
            recs.append("High match workload detected — consider rotation")
        if any(name == "fatigue_drop" for name, _ in risk_factors):
            recs.append("Significant second-half drop-off — assess fitness levels")
        if any(name == "behavioral" for name, _ in risk_factors):
            recs.append("Behavioral risks (cards/fouls) — review discipline")
        if not recs:
            recs.append("Low risk profile — continue current regime")
        return recs


class AdvancedAnalysisEngine:
    """
    Orchestrates all analysis modules for a given player.
    """

    def __init__(self):
        self.forecaster = PerformanceForecaster()
        self.anomaly_detector = AnomalyDetector()
        self.similarity_engine = PlayerSimilarityEngine()
        self.consistency = ConsistencyAnalyzer()
        self.momentum = MomentumAnalyzer()
        self.injury_risk = InjuryRiskEstimator()

    def analyze_all(self, player_id: int, scores: pd.DataFrame, computed: pd.DataFrame,
                    events: pd.DataFrame) -> dict:
        player_scores = scores[scores["player_id"] == player_id].copy()

        if len(player_scores) == 0:
            return {"error": f"Player {player_id} not found"}

        forecast = self.forecaster.forecast(player_scores)
        anomalies = self.anomaly_detector.detect(player_scores, computed)
        similarity = self.similarity_engine.find_similar(player_id, scores)
        consistency = self.consistency.analyze(player_scores)
        momentum = self.momentum.analyze(player_scores)
        injury = self.injury_risk.estimate(player_id, scores, computed, events)

        player_name = str(player_scores.iloc[0].get("player_name", "Unknown"))

        return {
            "player_id": int(player_id),
            "player_name": player_name,
            "position": str(player_scores.iloc[0].get("position_group", "Unknown")),
            "matches_played": len(player_scores),
            "forecast": forecast,
            "anomalies": anomalies,
            "similar_players": similarity,
            "consistency": consistency,
            "momentum": momentum,
            "injury_risk": injury,
        }
