import React, { useEffect, useState } from 'react';
import {
  TrendingUp, TrendingDown, Minus,
  ArrowUpRight, ArrowDownRight
} from 'lucide-react';
import { AdvancedAnalysisAPI } from '../api';
import LoadingSpinner from './LoadingSpinner';
import ErrorAlert from './ErrorAlert';

const PlayerMomentum = ({ playerId, playerName }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetch = async () => {
      try {
        setLoading(true);
        setError(null);
        const result = await AdvancedAnalysisAPI.getMomentum(playerId);
        setData(result);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    if (playerId) fetch();
  }, [playerId]);

  if (loading) return <LoadingSpinner message="Analyzing momentum..." />;
  if (error) return <ErrorAlert message={error} />;
  if (!data || !data.momentum) return <ErrorAlert message="No momentum data" />;

  const m = data.momentum;

  const momentumColors = {
    'Strong Positive': 'emerald',
    'Positive': 'cyan',
    'Neutral': 'amber',
    'Negative': 'rose',
    'Strong Negative': 'red',
  };

  const color = momentumColors[m.momentum_label] || 'slate';

  const momentumPercent = ((m.momentum_score + 1) / 2) * 100;
  const rotation = -90 + (momentumPercent / 100) * 180;

  const gaugeColor = m.momentum_score > 0.3 ? '#10b981' :
    m.momentum_score > 0.1 ? '#06b6d4' :
    m.momentum_score > -0.1 ? '#f59e0b' :
    m.momentum_score > -0.3 ? '#f43f5e' : '#ef4444';

  const dimLabels = {
    passing: 'Passing', shooting: 'Shooting', positioning: 'Positioning',
    pressing: 'Pressing', movement: 'Movement'
  };

  return (
    <div className="space-y-6 theme-animated">
      <section className="surface p-6 sm:p-8">
        <div className="section-header section-header-animated mb-4">
          <h2 className="text-xl font-semibold">Momentum & Form Analysis</h2>
          <p className="mt-1 text-sm text-white/90">
            EWMA-based momentum with streak detection for {playerName || data.player_name}
          </p>
        </div>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          <div className="metric-card p-6 flex flex-col items-center justify-center">
            <svg width="160" height="100" viewBox="0 0 160 100">
              <path d="M 15 85 A 65 65 0 0 1 145 85" fill="none" stroke="#e2e8f0" strokeWidth="12"
                strokeLinecap="round" />
              <path d="M 15 85 A 65 65 0 0 1 145 85"
                fill="none" stroke={gaugeColor} strokeWidth="12" strokeLinecap="round"
                strokeDasharray={`${(momentumPercent / 100) * 204.2} 204.2`} />
              <line x1="80" y1="85" x2={80 + 55 * Math.cos((rotation - 90) * Math.PI / 180)}
                y2={85 + 55 * Math.sin((rotation - 90) * Math.PI / 180)}
                stroke={gaugeColor} strokeWidth="3" strokeLinecap="round" />
              <circle cx="80" cy="85" r="4" fill={gaugeColor} />
              <text x="80" y="45" textAnchor="middle" fontSize="18" fontWeight="bold" fill={gaugeColor}>
                {m.momentum_score > 0 ? '+' : ''}{m.momentum_score.toFixed(2)}
              </text>
              <text x="20" y="98" fontSize="9" fill="#94a3b8">-1.0</text>
              <text x="140" y="98" fontSize="9" fill="#94a3b8">+1.0</text>
            </svg>
            <p className={`mt-2 text-sm font-semibold ${
              color === 'emerald' ? 'text-emerald-600' :
              color === 'cyan' ? 'text-cyan-600' :
              color === 'amber' ? 'text-amber-600' :
              color === 'rose' || color === 'red' ? 'text-rose-600' :
              'text-slate-600'
            }`}>
              {m.momentum_label}
            </p>
          </div>

          <div className="space-y-3">
            <div className="metric-card p-3">
              <p className="text-xs text-slate-500">Recent Avg (last {m.recent_matches})</p>
              <p className="text-lg font-semibold text-slate-900">{m.recent_average}/10</p>
            </div>
            <div className="metric-card p-3">
              <p className="text-xs text-slate-500">Historical Avg</p>
              <p className="text-lg font-semibold text-slate-900">{m.historical_average}/10</p>
            </div>
            <div className="metric-card p-3">
              <p className="text-xs text-slate-500">Overall Avg</p>
              <p className="text-lg font-semibold text-slate-900">{m.overall_average}/10</p>
            </div>
          </div>

          <div className="space-y-3">
            <div className="metric-card p-3">
              <p className="text-xs text-slate-500">Streak Direction</p>
              <div className="flex items-center gap-2 mt-1">
                {m.streak?.direction === 'improving' ? (
                  <ArrowUpRight className="h-4 w-4 text-emerald-500" />
                ) : m.streak?.direction === 'declining' ? (
                  <ArrowDownRight className="h-4 w-4 text-rose-500" />
                ) : (
                  <Minus className="h-4 w-4 text-amber-500" />
                )}
                <span className="text-lg font-semibold text-slate-900 capitalize">
                  {m.streak?.direction || 'stable'}
                </span>
              </div>
            </div>
            <div className="metric-card p-3">
              <p className="text-xs text-slate-500">Streak Length</p>
              <p className="text-lg font-semibold text-slate-900">{m.streak?.length || 0} matches</p>
            </div>
            <div className="metric-card p-3">
              <p className="text-xs text-slate-500">Matches Analyzed</p>
              <p className="text-lg font-semibold text-slate-900">{m.total_matches}</p>
            </div>
          </div>
        </div>

        {m.last_5_scores && m.last_5_scores.length > 0 && (
          <div className="mt-6">
            <h3 className="mb-3 text-sm font-semibold text-slate-800">
              Last {m.last_5_scores.length} Match Scores
            </h3>
            <div className="flex items-end gap-2" style={{ height: '120px' }}>
              {m.last_5_scores.map((score, i) => {
                const barH = Math.max(10, (score / 10) * 100);
                const barColor = score >= m.overall_average ? '#10b981' : '#f43f5e';
                return (
                  <div key={i} className="flex flex-1 flex-col items-center gap-1">
                    <span className="text-xs font-semibold text-slate-700">{score.toFixed(1)}</span>
                    <div
                      className="w-full rounded-t-md transition-all"
                      style={{
                        height: `${barH}px`,
                        backgroundColor: barColor,
                        opacity: 0.7 + (i / m.last_5_scores.length) * 0.3,
                      }}
                    />
                    <span className="text-xs text-slate-400">M{-m.last_5_scores.length + i + 1}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {m.dimension_momentum && Object.keys(m.dimension_momentum).length > 0 && (
          <div className="mt-6">
            <h3 className="mb-3 text-sm font-semibold text-slate-800">Dimension Momentum</h3>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
              {Object.entries(m.dimension_momentum).map(([dim, val]) => (
                <div key={dim} className="metric-card p-3 text-center">
                  <p className="text-xs text-slate-500">{dimLabels[dim] || dim}</p>
                  <div className="flex items-center justify-center gap-1 mt-1">
                    {val > 0.05 ? (
                      <TrendingUp className="h-3 w-3 text-emerald-500" />
                    ) : val < -0.05 ? (
                      <TrendingDown className="h-3 w-3 text-rose-500" />
                    ) : (
                      <Minus className="h-3 w-3 text-amber-500" />
                    )}
                    <span className={`text-sm font-bold ${
                      val > 0.05 ? 'text-emerald-600' : val < -0.05 ? 'text-rose-600' : 'text-amber-600'
                    }`}>
                      {val > 0 ? '+' : ''}{val.toFixed(2)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="mt-4 surface p-4">
          <h3 className="mb-2 text-sm font-semibold text-slate-800">Interpretation</h3>
          <p className="text-sm text-slate-600">
            Momentum score of <strong>{m.momentum_score > 0 ? '+' : ''}{m.momentum_score.toFixed(2)}</strong>
            {' '}indicates <strong>{m.momentum_label}</strong> form.
            Recent average ({m.recent_average}/10) vs historical ({m.historical_average}/10)
            suggests the player is{' '}
            {m.recent_average > m.historical_average ? 'gaining' : 'losing'} form.
          </p>
        </div>
      </section>
    </div>
  );
};

export default PlayerMomentum;
