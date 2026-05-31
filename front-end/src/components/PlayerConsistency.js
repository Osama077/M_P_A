import React, { useEffect, useState } from 'react';
import {
  TrendingUp, TrendingDown, Minus,
  Layers, CheckCircle2, AlertCircle
} from 'lucide-react';
import { AdvancedAnalysisAPI } from '../api';
import LoadingSpinner from './LoadingSpinner';
import ErrorAlert from './ErrorAlert';

const PlayerConsistency = ({ playerId, playerName }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetch = async () => {
      try {
        setLoading(true);
        setError(null);
        const result = await AdvancedAnalysisAPI.getConsistency(playerId);
        setData(result);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    if (playerId) fetch();
  }, [playerId]);

  const consistencyColors = {
    'Very Consistent': { bg: 'bg-emerald-50 border-emerald-300', text: 'text-emerald-700', icon: CheckCircle2, color: '#10b981' },
    'Consistent': { bg: 'bg-cyan-50 border-cyan-300', text: 'text-cyan-700', icon: CheckCircle2, color: '#06b6d4' },
    'Moderate': { bg: 'bg-amber-50 border-amber-300', text: 'text-amber-700', icon: Minus, color: '#f59e0b' },
    'Inconsistent': { bg: 'bg-rose-50 border-rose-300', text: 'text-rose-700', icon: AlertCircle, color: '#f43f5e' },
  };

  if (loading) return <LoadingSpinner message="Analyzing consistency..." />;
  if (error) return <ErrorAlert message={error} />;
  if (!data || !data.consistency) return <ErrorAlert message="No consistency data" />;

  const c = data.consistency;
  const cc = consistencyColors[c.consistency_label] || consistencyColors['Moderate'];
  const Icon = cc.icon;

  const dimLabels = {
    passing: 'Passing', shooting: 'Shooting', positioning: 'Positioning',
    pressing: 'Pressing', movement: 'Movement', physical: 'Physical', behavioral: 'Behavioral'
  };

  return (
    <div className="space-y-6 theme-animated">
      <section className="surface p-6 sm:p-8">
        <div className="section-header section-header-animated mb-4">
          <h2 className="text-xl font-semibold">Consistency Analysis</h2>
          <p className="mt-1 text-sm text-white/90">
            Coefficient of variation analysis for {playerName || data.player_name}
          </p>
        </div>

        <div className={`metric-card p-6 mb-6 ${cc.bg} border-2`}>
          <div className="flex items-center gap-4">
            <Icon className={`h-10 w-10 ${cc.text}`} />
            <div>
              <p className={`text-2xl font-bold ${cc.text}`}>{c.consistency_label}</p>
              <p className="text-sm text-slate-600 mt-1">
                Consistency Score: {c.consistency_score}/10 &middot;
                CV: {c.coefficient_of_variation} &middot;
                Std Dev: {c.std_dev}
              </p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <div className="metric-card p-4">
            <p className="text-xs text-slate-500">Mean Score</p>
            <p className="text-lg font-semibold text-slate-900">{c.mean_score}/10</p>
          </div>
          <div className="metric-card p-4">
            <p className="text-xs text-slate-500">Std Deviation</p>
            <p className="text-lg font-semibold text-slate-900">{c.std_dev}</p>
          </div>
          <div className="metric-card p-4">
            <p className="text-xs text-slate-500">CV (Coefficient of Variation)</p>
            <p className="text-lg font-semibold text-slate-900">{c.coefficient_of_variation}</p>
          </div>
          <div className="metric-card p-4">
            <p className="text-xs text-slate-500">Matches</p>
            <p className="text-lg font-semibold text-slate-900">{c.matches_analyzed}</p>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-2 gap-4">
          <div className="metric-card p-4">
            <p className="text-xs text-slate-500">First Half CV</p>
            <p className="text-lg font-semibold text-slate-900">{c.first_half_cv}</p>
          </div>
          <div className="metric-card p-4">
            <p className="text-xs text-slate-500">Second Half CV</p>
            <p className="text-lg font-semibold text-slate-900">{c.second_half_cv}</p>
          </div>
        </div>

        <div className="mt-3 surface-muted p-3">
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">Consistency Trend:</span>
            {c.consistency_trend === 'improving' ? (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600">
                <TrendingUp className="h-3 w-3" /> Improving
              </span>
            ) : c.consistency_trend === 'declining' ? (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-rose-600">
                <TrendingDown className="h-3 w-3" /> Declining
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-600">
                <Minus className="h-3 w-3" /> Stable
              </span>
            )}
          </div>
        </div>

        {c.dimension_consistency && Object.keys(c.dimension_consistency).length > 0 && (
          <div className="mt-6">
            <h3 className="mb-3 text-sm font-semibold text-slate-800 flex items-center gap-2">
              <Layers className="h-4 w-4" />
              Dimension Consistency (lower CV = more consistent)
            </h3>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              {Object.entries(c.dimension_consistency)
                .sort(([, a], [, b]) => a - b)
                .map(([dim, cv]) => {
                  const consistency = cv <= 0.1 ? 'High' : cv <= 0.2 ? 'Good' : cv <= 0.35 ? 'Moderate' : 'Variable';
                  return (
                    <div key={dim} className="metric-card p-3">
                      <p className="text-xs text-slate-500">{dimLabels[dim] || dim}</p>
                      <p className="text-base font-semibold text-slate-900">{cv}</p>
                      <span className={`text-xs font-medium ${
                        consistency === 'High' ? 'text-emerald-600' :
                        consistency === 'Good' ? 'text-cyan-600' :
                        consistency === 'Moderate' ? 'text-amber-600' : 'text-rose-600'
                      }`}>
                        {consistency}
                      </span>
                    </div>
                  );
                })}
            </div>
          </div>
        )}

        <div className="mt-4 surface p-4">
          <h3 className="mb-2 text-sm font-semibold text-slate-800">Interpretation</h3>
          <p className="text-sm text-slate-600">
            A CV of <strong>{c.coefficient_of_variation}</strong> means the player&apos;s
            scores vary by <strong>{(c.coefficient_of_variation * 100).toFixed(1)}%</strong> around
            the mean of {c.mean_score}. Lower CV indicates more consistent performances.
            The player is rated as <strong>{c.consistency_label}</strong>.
          </p>
        </div>
      </section>
    </div>
  );
};

export default PlayerConsistency;
