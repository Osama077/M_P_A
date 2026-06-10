import React, { useEffect, useState } from 'react';
import {
  TrendingUp, TrendingDown, Minus, BarChart3, Users, Activity, AlertTriangle
} from 'lucide-react';
import { PredictionAPI } from '../api';
import { useAppContext } from '../context/AppContext';
import LoadingSpinner from './LoadingSpinner';
import ErrorAlert from './ErrorAlert';

const colorStyles = {
  brand: { icon: 'text-brand-500', value: 'text-brand-800' },
  emerald: { icon: 'text-emerald-500', value: 'text-emerald-800' },
  rose: { icon: 'text-rose-500', value: 'text-rose-800' },
  amber: { icon: 'text-amber-500', value: 'text-amber-800' },
  cyan: { icon: 'text-cyan-500', value: 'text-cyan-800' },
  violet: { icon: 'text-violet-500', value: 'text-violet-800' },
  blue: { icon: 'text-blue-500', value: 'text-blue-800' },
};

const StatCard = ({ label, value, suffix, icon: Icon, color }) => {
  const cs = colorStyles[color] || colorStyles.brand;
  return (
    <div className="metric-card metric-active p-4">
      <div className="flex items-center gap-2 text-sm text-slate-500">
        <Icon className={`h-4 w-4 ${cs.icon}`} />
        <span>{label}</span>
      </div>
      <p className={`mt-1 text-xl font-semibold ${cs.value}`}>
        {typeof value === 'number' ? value.toFixed(1) : value}{suffix || ''}
      </p>
    </div>
  );
};

const MatchPrediction = ({ playerId, playerName }) => {
  const { selectedSeason } = useAppContext();
  const [data, setData] = useState(null);
  const [squadData, setSquadData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [viewMode, setViewMode] = useState(playerId ? 'player' : 'squad');

  useEffect(() => {
    const fetch = async () => {
      try {
        setLoading(true);
        setError(null);
        if (playerId && viewMode === 'player') {
          const result = await PredictionAPI.getPlayerPrediction(playerId, selectedSeason);
          setData(result);
        } else {
          const result = await PredictionAPI.getSquadPrediction();
          setSquadData(result);
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, [playerId, selectedSeason, viewMode]);

  if (loading) return <LoadingSpinner message="Computing match predictions..." />;
  if (error) return <ErrorAlert message={error} />;

  if (viewMode === 'squad') {
    const sd = squadData;
    if (!sd) return <ErrorAlert message="No squad prediction data available" />;

    return (
      <div className="space-y-6 theme-animated">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-slate-900">Match Predictions</h2>
            <p className="text-sm text-slate-500">Next-match performance forecasting</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setViewMode('player')}
              className="btn-secondary text-xs"
            >
              Player View
            </button>
            <button
              onClick={() => setViewMode('squad')}
              className="btn-primary text-xs"
            >
              Squad View
            </button>
          </div>
        </div>

        <section className="surface p-6 sm:p-8">
          <div className="section-header section-header-animated mb-4">
            <h2 className="text-xl font-semibold">Squad Next-Match Prediction</h2>
            <p className="mt-1 text-sm text-white/90">Aggregate forecast across all players</p>
          </div>

          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <StatCard label="Squad Avg Prediction" value={sd.squad_predicted_avg} suffix="/10" icon={Users} color="brand" />
            <StatCard label="Season Avg" value={sd.squad_season_avg} suffix="/10" icon={BarChart3} color="cyan" />
            <StatCard label="Players Predicted" value={sd.total_players_predicted} icon={Users} color="blue" />
            <StatCard label="Fatigue Concerns" value={sd.fatigue_concern_count} icon={AlertTriangle} color="rose" />
          </div>

          <div className="mt-6 grid grid-cols-3 gap-4">
            <div className="metric-card p-4 text-center">
              <div className="flex items-center justify-center gap-2 mb-1">
                <TrendingUp className="h-4 w-4 text-emerald-500" />
                <span className="text-sm font-semibold text-emerald-600">Improving</span>
              </div>
              <p className="text-2xl font-bold text-emerald-700">{sd.trend_summary?.improving_count || 0}</p>
              <p className="text-xs text-slate-500">players</p>
            </div>
            <div className="metric-card p-4 text-center">
              <div className="flex items-center justify-center gap-2 mb-1">
                <Minus className="h-4 w-4 text-amber-500" />
                <span className="text-sm font-semibold text-amber-600">Stable</span>
              </div>
              <p className="text-2xl font-bold text-amber-700">{sd.trend_summary?.stable_count || 0}</p>
              <p className="text-xs text-slate-500">players</p>
            </div>
            <div className="metric-card p-4 text-center">
              <div className="flex items-center justify-center gap-2 mb-1">
                <TrendingDown className="h-4 w-4 text-rose-500" />
                <span className="text-sm font-semibold text-rose-600">Declining</span>
              </div>
              <p className="text-2xl font-bold text-rose-700">{sd.trend_summary?.declining_count || 0}</p>
              <p className="text-xs text-slate-500">players</p>
            </div>
          </div>

          {sd.narrative && (
            <div className="mt-6 surface-muted p-4 border-l-4 border-l-brand-500">
              <div className="flex items-center gap-2 mb-2">
                <Activity className="h-4 w-4 text-brand-500" />
                <span className="text-sm font-semibold text-slate-800">Forecast Narrative</span>
              </div>
              <p className="text-sm text-slate-600 leading-relaxed">{sd.narrative}</p>
            </div>
          )}

          {sd.top_3_improving?.length > 0 && (
            <div className="mt-6">
              <h3 className="text-sm font-semibold text-emerald-700 mb-2 flex items-center gap-2">
                <TrendingUp className="h-4 w-4" /> Top Improving Players
              </h3>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                {sd.top_3_improving.map((p, i) => (
                  <div key={i} className="rounded-lg bg-emerald-50 p-3 border border-emerald-100">
                    <p className="text-xs font-semibold text-emerald-800">{p.player_name}</p>
                    <p className="text-lg font-bold text-emerald-600">{p.predicted_score?.toFixed(1)}/10</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {sd.top_3_declining?.length > 0 && (
            <div className="mt-6">
              <h3 className="text-sm font-semibold text-rose-700 mb-2 flex items-center gap-2">
                <TrendingDown className="h-4 w-4" /> Top Declining Players
              </h3>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                {sd.top_3_declining.map((p, i) => (
                  <div key={i} className="rounded-lg bg-rose-50 p-3 border border-rose-100">
                    <p className="text-xs font-semibold text-rose-800">{p.player_name}</p>
                    <p className="text-lg font-bold text-rose-600">{p.predicted_score?.toFixed(1)}/10</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {sd.fatigue_concern_players?.length > 0 && (
            <div className="mt-6">
              <h3 className="text-sm font-semibold text-amber-700 mb-2 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4" /> Fatigue Concerns — Rotation Recommended
              </h3>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                {sd.fatigue_concern_players.slice(0, 6).map((p, i) => (
                  <div key={i} className="rounded-lg bg-amber-50 p-3 border border-amber-100">
                    <p className="text-xs font-semibold text-amber-800">{p.player_name}</p>
                    <p className="text-sm font-bold text-amber-600">Drop: {p.drop_pct?.toFixed(1)}%</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      </div>
    );
  }

  if (!data) {
    if (!playerId) {
      return (
        <div className="space-y-6 theme-animated">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Match Predictions</h2>
              <p className="text-sm text-slate-500">Next-match performance forecasting</p>
            </div>
            <div className="flex gap-2">
              <button onClick={() => setViewMode('squad')} className="btn-primary text-xs">Squad View</button>
            </div>
          </div>
          <div className="surface p-8 text-center">
            <p className="text-sm text-slate-600">Select a player first from the Players section, or switch to Squad View.</p>
          </div>
        </div>
      );
    }
    return <ErrorAlert message="No prediction data available" />;
  }

  const pred = data.prediction || data;
  const hasFeatures = pred.technical_features || pred.physical_features;

  return (
    <div className="space-y-6 theme-animated">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Match Predictions</h2>
          <p className="text-sm text-slate-500">Next-match performance forecasting</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setViewMode('player')}
            className="btn-primary text-xs"
          >
            Player View
          </button>
          <button
            onClick={() => setViewMode('squad')}
            className="btn-secondary text-xs"
          >
            Squad View
          </button>
        </div>
      </div>

      <section className="surface p-6 sm:p-8">
        <div className="section-header section-header-animated mb-4">
          <h2 className="text-xl font-semibold">Player Next-Match Prediction</h2>
          <p className="mt-1 text-sm text-white/90">
            {playerName || data.player_name} — forecasted performance
          </p>
        </div>

        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <StatCard label="Predicted Score" value={pred.predicted_technical_score ?? pred.predicted_score} suffix="/10" icon={BarChart3} color="brand" />
          <StatCard label="Season Avg" value={pred.season_avg ?? pred.current_avg} suffix="/10" icon={BarChart3} color="cyan" />
          <StatCard label="Trend" value={pred.trend_direction || 'stable'} icon={pred.trend_direction === 'improving' ? TrendingUp : pred.trend_direction === 'declining' ? TrendingDown : Minus} color={pred.trend_direction === 'improving' ? 'emerald' : pred.trend_direction === 'declining' ? 'rose' : 'amber'} />
          <StatCard label="Fatigue Concern" value={pred.fatigue_context?.fatigue_drop_percent ? `${pred.fatigue_context.fatigue_drop_percent.toFixed(1)}%` : (pred.fatigue_concern ? 'Yes' : 'No')} icon={AlertTriangle} color={pred.fatigue_context?.fatigue_drop_percent > 20 ? 'rose' : 'emerald'} />
        </div>

        {pred.physical_prediction && (
          <div className="mt-6">
            <h3 className="mb-3 text-sm font-semibold text-slate-800">Physical Forecast</h3>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
              <div className="metric-card p-3">
                <p className="text-xs text-slate-500">Actions Predicted</p>
                <p className="text-base font-semibold text-slate-800">{Math.round(pred.physical_prediction.total_actions_predicted)}</p>
              </div>
              <div className="metric-card p-3">
                <p className="text-xs text-slate-500">Distance</p>
                <p className="text-base font-semibold text-slate-800">{Math.round(pred.physical_prediction.distance_predicted)}m</p>
              </div>
              <div className="metric-card p-3">
                <p className="text-xs text-slate-500">Pressures</p>
                <p className="text-base font-semibold text-slate-800">{Math.round(pred.physical_prediction.pressures_predicted)}</p>
              </div>
              <div className="metric-card p-3">
                <p className="text-xs text-slate-500">Activity Drop</p>
                <p className={`text-base font-semibold ${(pred.physical_prediction.activity_drop_predicted || 0) > 0 ? 'text-rose-600' : 'text-emerald-600'}`}>
                  {pred.physical_prediction.activity_drop_predicted?.toFixed(1) || '0'}%
                </p>
              </div>
            </div>
          </div>
        )}

        {pred.fatigue_context && (
          <div className="mt-6 surface-muted p-4 border-l-4 border-l-amber-500">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="h-4 w-4 text-amber-500" />
              <span className="text-sm font-semibold text-slate-800">Fatigue Context</span>
            </div>
            <p className="text-sm text-slate-600">
              Recent workload: <strong>{pred.fatigue_context.recent_workload || '—'}</strong> actions/match
              {pred.fatigue_context.fatigue_drop_percent > 20
                ? ' — High fatigue risk: >20% drop in activity. Consider rotation.'
                : pred.fatigue_context.fatigue_drop_percent > 10
                  ? ' — Moderate fatigue: 10–20% drop. Monitor closely.'
                  : ' — Normal fatigue levels.'}
            </p>
            {pred.fatigue_context.weekly_load && (
              <div className="mt-2 flex gap-2 text-xs text-slate-500">
                <span>Weekly: {Math.round(pred.fatigue_context.weekly_load)}</span>
                <span>7d Avg: {Math.round(pred.fatigue_context.rolling_7d_avg)}</span>
                <span>28d Avg: {Math.round(pred.fatigue_context.rolling_28d_avg)}</span>
              </div>
            )}
          </div>
        )}

        {hasFeatures && (
          <div className="mt-6">
            <h3 className="mb-3 text-sm font-semibold text-slate-800">Prediction Features</h3>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
              {pred.technical_features && Object.entries(pred.technical_features).slice(0, 6).map(([key, val]) => (
                <div key={key} className="rounded-lg bg-slate-50 p-2 text-xs">
                  <span className="text-slate-500">{key.replace(/_/g, ' ')}</span>
                  <p className="font-semibold text-slate-800">{typeof val === 'number' ? val.toFixed(2) : val}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="mt-6 surface p-4">
          <h3 className="mb-2 text-sm font-semibold text-slate-800">Prediction Methodology</h3>
          <p className="text-xs text-slate-600 leading-relaxed">
            Technical score predicted using Ridge regression with EWMA features (30% trend weight, 70% smoothed average).
            Physical metrics forecasted per-dimension using match-level regression.
            Fatigue context compares 7-day rolling workload vs 28-day baseline.
            Predictions degrade with fewer data points — minimum 3 matches required.
          </p>
        </div>
      </section>
    </div>
  );
};

export default MatchPrediction;
