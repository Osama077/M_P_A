import React, { useEffect, useState } from 'react';
import {
  Heart, AlertTriangle, Shield, Activity,
  TrendingUp, Zap, Brain, FileText
} from 'lucide-react';
import { AdvancedAnalysisAPI } from '../api';
import LoadingSpinner from './LoadingSpinner';
import ErrorAlert from './ErrorAlert';

const PlayerInjuryRisk = ({ playerId, playerName }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetch = async () => {
      try {
        setLoading(true);
        setError(null);
        const result = await AdvancedAnalysisAPI.getInjuryRisk(playerId);
        setData(result);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    if (playerId) fetch();
  }, [playerId]);

  if (loading) return <LoadingSpinner message="Estimating injury risk..." />;
  if (error) return <ErrorAlert message={error} />;
  if (!data || !data.injury_risk) return <ErrorAlert message="No injury risk data" />;

  const ir = data.injury_risk;
  const riskPct = (ir.risk_score / 10) * 100;

  const riskColors = {
    High: { text: 'text-rose-600', bg: 'bg-rose-50', border: 'border-rose-300', fill: '#f43f5e', icon: AlertTriangle },
    Moderate: { text: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-300', fill: '#f59e0b', icon: Activity },
    Low: { text: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-300', fill: '#10b981', icon: Shield },
  };

  const rc = riskColors[ir.risk_level] || riskColors.Low;
  const RiskIcon = rc.icon;

  const factorIcons = {
    high_workload: Zap,
    fatigue_drop: TrendingUp,
    high_intensity: Activity,
    behavioral: Brain,
    performance_decline: TrendingUp,
  };

  return (
    <div className="space-y-6 theme-animated">
      <section className="surface p-6 sm:p-8">
        <div className="section-header section-header-animated mb-4">
          <h2 className="text-xl font-semibold">Injury Risk Assessment</h2>
          <p className="mt-1 text-sm text-white/90">
            ML-driven risk estimation for {playerName || data.player_name}
          </p>
        </div>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          <div className={`metric-card p-6 ${rc.bg} ${rc.border} border-2 flex flex-col items-center justify-center`}>
            <div className="relative w-32 h-32">
              <svg viewBox="0 0 120 120" className="w-full h-full">
                <circle cx="60" cy="60" r="50" fill="none" stroke="#e2e8f0" strokeWidth="8" />
                <circle cx="60" cy="60" r="50" fill="none" stroke={rc.fill} strokeWidth="8"
                  strokeDasharray={`${(riskPct / 100) * 314.16} 314.16`}
                  strokeLinecap="round" transform="rotate(-90, 60, 60)" />
                <text x="60" y="50" textAnchor="middle" fontSize="24" fontWeight="bold" fill={rc.fill}>
                  {ir.risk_score.toFixed(1)}
                </text>
                <text x="60" y="68" textAnchor="middle" fontSize="10" fill="#94a3b8">/ 10</text>
              </svg>
            </div>
            <div className="flex items-center gap-2 mt-3">
              <RiskIcon className={`h-5 w-5 ${rc.text}`} />
              <span className={`text-lg font-bold ${rc.text}`}>{ir.risk_level} Risk</span>
            </div>
          </div>

          <div className="space-y-3">
            <div className="metric-card p-3">
              <p className="text-xs text-slate-500">Matches Analyzed</p>
              <p className="text-lg font-semibold text-slate-900">{ir.matches_analyzed}</p>
            </div>
            <div className="metric-card p-3">
              <p className="text-xs text-slate-500">Avg Actions/Match</p>
              <p className="text-lg font-semibold text-slate-900">{ir.total_actions_avg}</p>
            </div>
          </div>

          <div className="space-y-2">
            <p className="text-sm font-semibold text-slate-800 mb-2 flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Risk Factors
            </p>
            {(ir.risk_factors || []).map((rf, i) => {
              const FactorIcon = factorIcons[rf.factor] || Activity;
              const pctOfTotal = ir.risk_score > 0 ? (rf.contribution / ir.risk_score) * 100 : 0;
              return (
                <div key={i} className="metric-card p-2 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <FactorIcon className="h-3.5 w-3.5 text-slate-500" />
                    <span className="text-xs text-slate-700 capitalize">
                      {rf.factor.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <span className="text-xs font-semibold text-slate-800">
                    +{rf.contribution.toFixed(1)} ({pctOfTotal.toFixed(0)}%)
                  </span>
                </div>
              );
            })}
            {(!ir.risk_factors || ir.risk_factors.length === 0) && (
              <p className="text-xs text-slate-400">No significant risk factors identified</p>
            )}
          </div>
        </div>

        {ir.recommendations && ir.recommendations.length > 0 && (
          <div className="mt-6 surface-muted p-4">
            <h3 className="mb-3 text-sm font-semibold text-slate-800 flex items-center gap-2">
              <Heart className="h-4 w-4 text-rose-500" />
              Recommendations
            </h3>
            <ul className="space-y-2">
              {ir.recommendations.map((rec, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                  <span className="mt-0.5 h-5 w-5 flex items-center justify-center rounded-full bg-brand-100 text-brand-700 text-xs font-bold">
                    {i + 1}
                  </span>
                  {rec}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="mt-4 surface p-4">
          <h3 className="mb-2 text-sm font-semibold text-slate-800">Methodology</h3>
          <p className="text-sm text-slate-600">
            Risk score is computed from: workload volume, second-half fatigue drops,
            high-intensity pressing load, behavioral indicators (cards, fouls),
            and performance decline signals. Each factor is normalized and weighted.
            This is a statistical proxy &mdash; not a medical diagnosis.
          </p>
        </div>
      </section>
    </div>
  );
};

export default PlayerInjuryRisk;
