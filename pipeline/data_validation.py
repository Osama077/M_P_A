"""
pipeline/data_validation.py — Formula Audit & Data Validation
Reviews all metrics for logical soundness, flags issues, and recommends corrections.
"""


class DataValidator:
    def __init__(self):
        self.findings = []

    def _add(self, metric, severity, finding, recommendation, status):
        self.findings.append({
            "metric": metric,
            "severity": severity,
            "finding": finding,
            "recommendation": recommendation,
            "status": status,
        })

    def validate_all(self) -> dict:
        self.findings = []
        self._validate_passing()
        self._validate_shooting()
        self._validate_positioning()
        self._validate_pressing()
        self._validate_movement()
        self._validate_physical()
        self._validate_behavioral()
        self._validate_overall()
        self._validate_advanced()
        return {
            "summary": {
                "total_findings": len(self.findings),
                "critical_count": sum(1 for f in self.findings if f["severity"] == "critical"),
                "high_count": sum(1 for f in self.findings if f["severity"] == "high"),
                "medium_count": sum(1 for f in self.findings if f["severity"] == "medium"),
                "low_count": sum(1 for f in self.findings if f["severity"] == "low"),
                "fixed_count": sum(1 for f in self.findings if f["status"] == "fixed"),
                "pending_count": sum(1 for f in self.findings if f["status"] == "pending"),
            },
            "findings": self.findings,
        }

    def _validate_passing(self):
        self._add(
            "pass_accuracy", "medium",
            "Small-sample bias: a player with 1/1 passes gets 100% accuracy, same as 80/80. No minimum-pass threshold exists.",
            "Add minimum 5-pass threshold before computing accuracy. Players below threshold should use league-average imputation.",
            "pending",
        )
        self._add(
            "passing_score (weighting)", "medium",
            "Volume (total_passes) and efficiency (pass_accuracy) are both normalized and summed. A player making many safe short passes is rewarded twice — once for volume, once for high accuracy.",
            "Consider replacing total_passes with a more discriminating metric like passes per minute played or pass completion above expected.",
            "pending",
        )
        self._add(
            "progressive_passes", "low",
            "20-unit forward threshold (~17.5m after scaling) is reasonable but arbitrary. Different definitions would meaningfully change rankings.",
            "No change needed — but document the threshold clearly for stakeholders.",
            "pending",
        )
        self._add(
            "passes_under_pressure", "low",
            "Computed but completely unused in the scoring formula. This is a valuable metric wasted.",
            "Consider incorporating into passing score or as a separate dimension modifier.",
            "pending",
        )

    def _validate_shooting(self):
        self._add(
            "shooting_score", "high",
            "Double-counting shot quality: predicted_xG captures location, angle, pressure, body part. Then shot_accuracy rewards quality again, and total_shots rewards volume. Three components all measuring essentially the same thing.",
            "Keep predicted_xG as the primary shooting metric (weight ~0.60). Reduce shot_accuracy to 0.20 and total_shots to 0.20 to reduce multicollinearity.",
            "pending",
        )
        self._add(
            "shot_accuracy (Saved To Post)", "low",
            "'Saved To Post' is counted as on-target. While StatsBomb defines this as keeper-saved-onto-post, it may mislead if confused with hitting the post directly.",
            "Acceptable — the distinction is handled by StatsBomb's event definition. Document for clarity.",
            "pending",
        )
        self._add(
            "predicted_xG vs native xG", "medium",
            "The scorer uses custom LightGBM predicted_xG instead of StatsBomb's native shot_xG. Both exist in the feature dataframe. If the custom model has systematic bias, it propagates into scores.",
            "Add a comparison report between native xG and predicted xG. If divergence > 0.1 on average, recalibrate the xG model.",
            "pending",
        )
        self._add(
            "penalties not separated", "medium",
            "Penalties (~0.79 xG, near-100% on-target) are not differentiated from open-play shots. A penalty-taker gets inflated shooting scores.",
            "Flag penalties in feature engineering and consider either excluding them from shooting score or normalizing separately.",
            "pending",
        )

    def _validate_positioning(self):
        self._add(
            "attacking_tendency", "high",
            "Position bias: attackers naturally score higher because they play farther forward. The dimension score does NOT normalize by position — correction only happens at the overall score level via position weights.",
            "Normalize attacking_tendency within position groups before scoring, or adjust the dimension weights dynamically per position.",
            "pending",
        )
        self._add(
            "position_deviation (inverted)", "medium",
            "Lower deviation is assumed 'better', but box-to-box midfielders who cover the pitch score worse. Substitutes with few events have artificially low deviation.",
            "Add a minimum-events threshold. For box-to-box roles, consider a modified formula that rewards controlled variability.",
            "pending",
        )

    def _validate_pressing(self):
        self._add(
            "pressure_regains definition", "critical",
            "Pressure_regains counted ALL counterpress events (passes, carries, dribbles), not just Pressure events. This caused pressing_efficiency to exceed 100% and inflated pressing scores.",
            "FIXED: Now counts only Pressure events where counterpress == 1. pressing_efficiency capped at 100% by using total_pressures > 0 guard.",
            "fixed",
        )
        self._add(
            "pressing lacks quality context", "medium",
            "Pressure events only indicate 'applied pressure' — not whether it was effective (forced bad pass, caused turnover). counterpress partially addresses this but is too broad.",
            "Consider adding a 'high-pressure regain' metric that counts only pressures leading directly to a turnover within 2 events.",
            "pending",
        )

    def _validate_movement(self):
        self._add(
            "dribble_success_rate = 0 for non-dribblers", "high",
            "Outer merge + fillna(0) means players with 0 dribbles get 0% success rate. This systematically penalizes defenders and midfielders who don't dribble.",
            "FIXED: Players with <2 dribbles now get a neutral 50% baseline in the scoring model instead of 0%.",
            "fixed",
        )
        self._add(
            "progressive carry threshold very small", "low",
            "5-unit threshold (~4.4m forward) means almost any forward carry qualifies. progressive_carries is highly correlated with total_carries.",
            "Consider increasing threshold to 10 units (~8.8m) for a more discriminating metric.",
            "pending",
        )
        self._add(
            "carry distance uses Euclidean distance", "low",
            "Straight-line start-to-end underestimates zigzagging dribbles.",
            "Acceptable limitation — true path data is not available from event data.",
            "pending",
        )
        self._add(
            "total_carry_distance and avg_carry_distance unused", "medium",
            "These metrics are computed but never used in scoring. They could provide better differentiation than raw carry count.",
            "Consider replacing or supplementing total_carries with total_carry_distance in the movement score.",
            "pending",
        )

    def _validate_physical(self):
        self._add(
            "distance_covered * 5.0 multiplier", "critical",
            "Distance_covered had an undocumented * 5.0 multiplier after coordinates were already converted to meters (105x68m pitch scaling). This inflated distances by 5x, making them unrealistic.",
            "FIXED: Removed the * 5.0 multiplier. Distances now reflect actual meters based on coordinate conversion.",
            "fixed",
        )
        self._add(
            "distance_covered NOT used in scoring", "high",
            "Distance_covered is the most important physical metric in football but was completely absent from the physical score. Only total_actions and activity_drop were used.",
            "FIXED: distance_covered now contributes 35% to the physical score alongside total_actions (35%) and activity_drop (30%).",
            "fixed",
        )
        self._add(
            "activity_drop_2nd_half uses abs()", "high",
            "ABS on activity_drop penalized players who had MORE actions in the 2nd half (e.g., substitutes) equally to those who dropped off. This was illogical.",
            "FIXED: Now only penalizes positive drops (fewer 2nd-half actions). Substitutes with negative drops are no longer penalized.",
            "fixed",
        )
        self._add(
            "activity_drop ignores substitutions", "high",
            "A player subbed off at minute 60 naturally has fewer P2 actions. A sub coming on at minute 70 has zero P1 actions. Both distort the metric.",
            "Partial mitigation applied (no more abs(), only penalizing positive drops). Full fix would require substitution-aware normalization (per-minute rates).",
            "pending",
        )
        self._add(
            "total_actions favors full-match players", "medium",
            "A 90-minute player always has far more actions than a substitute regardless of physical output — pure minutes bias.",
            "Consider per-minute action rate rather than raw count. Or include minutes played as a normalizing factor.",
            "pending",
        )
        self._add(
            "segment distance cap of 40m too large", "low",
            "40m between consecutive events is unrealistic for human movement. Many invalid jumps may pass through.",
            "Reduce cap to 20m (still very generous for inter-event movement).",
            "pending",
        )
        self._add(
            "intensity metrics computed but unused", "medium",
            "intensity_p1, intensity_p2, and intensity_drop_pct are all computed but never referenced in scoring. These are potentially valuable metrics.",
            "Consider incorporating intensity_drop_pct alongside activity_drop_2nd_half for a more complete fatigue picture.",
            "pending",
        )

    def _validate_behavioral(self):
        self._add(
            "yellow/red card penalties not normalized", "high",
            "Yellow cards deduct a flat 1.5 points, red cards deduct 3.0. These arbitrary fixed penalties are not normalized to the data distribution, making them disproportionately impactful in low-card environments.",
            "FIXED: Now uses normalize_to_score() for yellow and red cards, weighted at 0.25 and 0.50 respectively. Penalties scale with the data distribution.",
            "fixed",
        )
        self._add(
            "fouls_won computed but unused", "medium",
            "Winning fouls is a positive behavior (drawing dangerous free kicks) but contributes nothing to the score.",
            "FIXED: fouls_won now contributes +0.10 weight to behavioral score, rewarding players who draw fouls.",
            "fixed",
        )
        self._add(
            "ball_retention_rate = 100 for zero receipts", "high",
            "fillna(100) after division-by-zero meant players who never received the ball got perfect retention. This rewarded players who simply didn't participate.",
            "FIXED: Players with 0 ball receipts now get NaN (neutral) instead of 100. The scoring model handles NaN gracefully with fillna(100) only at scoring time.",
            "fixed",
        )
        self._add(
            "high baseline 8.0", "medium",
            "Behavioral starts at 8/10 and is penalized downward, unlike other dimensions that start at 0 and build up. This inflates behavioral relative to other dimensions.",
            "FIXED: Reduced baseline to 5.0 (neutral). Positive behaviors (fouls_won, ball_retention) add, negative behaviors subtract. More consistent with other dimensions.",
            "fixed",
        )
        self._add(
            "no tactical vs reckless foul distinction", "low",
            "A tactical foul in midfield counts the same as a reckless two-footed tackle.",
            "Acceptable — event data does not provide intentionality. Consider adding a 'dangerous foul' flag if tackle type data becomes available.",
            "pending",
        )

    def _validate_overall(self):
        self._add(
            "normalization is dataset-relative", "high",
            "normalize_to_score uses 5th/95th percentiles of current data. Scores shift when new data enters. An 8.5 today could become 7.5 tomorrow. Scores are NOT absolute.",
            "Consider storing normalization parameters (q05, q95 per metric) from training data and applying them consistently at inference time.",
            "pending",
        )
        self._add(
            "position bias in dimension scores", "high",
            "Dimension scores are position-agnostic — an attacker and defender with the same attacking_tendency get the same positioning_score. Position correction only at overall score level.",
            "Normalize each dimension score within position groups before computing overall score, or adjust dimension weights dynamically.",
            "pending",
        )
        self._add(
            "volume metrics dominate", "medium",
            "total_passes, total_shots, total_carries, total_actions — all reward full-match players. Substitutes are systematically disadvantaged in every dimension.",
            "Adopt per-minute rates or include minutes played as an explicit normalizing factor across all volume-based metrics.",
            "pending",
        )

    def _validate_advanced(self):
        self._add(
            "PerformanceForecaster: low sample sensitivity", "medium",
            "Minimum 3 matches for forecasting is too low. With 3-4 data points, trend detection is unreliable and R² values are misleading.",
            "Increase minimum to 5 matches. For players with 3-4 matches, return a simple recent average instead of a regression-based forecast.",
            "pending",
        )
        self._add(
            "AnomalyDetector: Z-score on small samples", "medium",
            "Z-score on <10 matches is unreliable because the mean and std are dominated by the very values being tested.",
            "Use modified Z-score (MAD-based) for small samples, or require minimum 8 matches.",
            "pending",
        )
        self._add(
            "InjuryRiskEstimator: EWMA-ACWR without differentiation", "medium",
            "ACWR uses total_actions as workload proxy. This treats a gentle jog as equal to a sprint. Different action types have vastly different physical loads.",
            "Weight actions by intensity (sprints > passes > carries) using a metabolic power model. Current approach is a simplified proxy.",
            "pending",
        )
        self._add(
            "ConsistencyAnalyzer: consistency_score formula arbitrary", "low",
            "The composite consistency score (0-10) uses weights (0.35 MAD, 0.25 CV, 0.40 autocorr) that are intuitive but not empirically validated.",
            "Validate weights against external consistency measures (e.g., coach ratings, injury rates). Adjust based on correlation analysis.",
            "pending",
        )
