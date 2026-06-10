import React, { useEffect, useState } from 'react';
import {
  Target, Users, Activity, Sparkles, Lightbulb, Crosshair
} from 'lucide-react';
import { CoachingAPI } from '../api';
import { useAppContext } from '../context/AppContext';
import LoadingSpinner from './LoadingSpinner';
import ErrorAlert from './ErrorAlert';

const colorStyles = {
  brand: { icon: 'text-brand-500', value: 'text-brand-800', bg: 'bg-brand-50' },
  emerald: { icon: 'text-emerald-500', value: 'text-emerald-800', bg: 'bg-emerald-50' },
  rose: { icon: 'text-rose-500', value: 'text-rose-800', bg: 'bg-rose-50' },
  amber: { icon: 'text-amber-500', value: 'text-amber-800', bg: 'bg-amber-50' },
  cyan: { icon: 'text-cyan-500', value: 'text-cyan-800', bg: 'bg-cyan-50' },
  violet: { icon: 'text-violet-500', value: 'text-violet-800', bg: 'bg-violet-50' },
  blue: { icon: 'text-blue-500', value: 'text-blue-800', bg: 'bg-blue-50' },
  orange: { icon: 'text-orange-500', value: 'text-orange-800', bg: 'bg-orange-50' },
};

const GuidanceCard = ({ guidance }) => {
  const priColor = guidance.priority === 'high' ? 'rose' :
    guidance.priority === 'medium' ? 'amber' : 'blue';
  const cs = colorStyles[priColor] || colorStyles.brand;
  const priorityLabel = guidance.priority === 'high' ? 'High Priority' :
    guidance.priority === 'medium' ? 'Medium' : 'Suggestion';
  const adviceText = guidance.advice || guidance.suggestion || '';
  return (
    <div className={`surface border-l-4 ${guidance.priority === 'high' ? 'border-l-rose-500' : guidance.priority === 'medium' ? 'border-l-amber-500' : 'border-l-blue-500'} p-4`}>
      <div className="flex items-start gap-3">
        <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${cs.bg}`}>
          <Lightbulb className={`h-4 w-4 ${cs.icon}`} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-bold ${cs.bg} ${cs.value}`}>
              {priorityLabel}
            </span>
            {guidance.category && (
              <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wider">{guidance.category}</span>
            )}
          </div>
          <p className="mt-1 text-sm font-semibold text-slate-900">{adviceText}</p>
          {guidance.explanation && (
            <p className="mt-1 text-xs text-slate-600">{guidance.explanation}</p>
          )}
          {guidance.metric && (
            <div className="mt-2 flex flex-wrap gap-2 text-[10px] text-slate-500">
              <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono">{guidance.metric}</span>
              {guidance.current_value && <span>Current: <strong>{guidance.current_value}</strong></span>}
              {guidance.target_value && <span>Target: <strong>{guidance.target_value}</strong></span>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const CoachingInsights = ({ playerId, playerName }) => {
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
          const result = await CoachingAPI.getPlayerComprehensive(playerId, selectedSeason);
          setData(result);
        } else {
          const result = await CoachingAPI.getSquadInsights();
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

  if (loading) return <LoadingSpinner message="Analyzing coaching insights..." />;
  if (error) return <ErrorAlert message={error} />;

  if (viewMode === 'squad') {
    const sd = squadData;
    if (!sd) return <ErrorAlert message="No squad coaching data available" />;

    const insights = sd.squad_insights || {};
    const guidanceItems = insights.guidance || [];
    const narrative = insights.narrative || insights.message || sd.narrative || 'Squad analysis available.';
    const findings = sd.validation_findings || [];

    return (
      <div className="space-y-6 theme-animated">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-slate-900">Coaching Insights</h2>
            <p className="text-sm text-slate-500">Tactical guidance & performance analysis</p>
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
            <h2 className="text-xl font-semibold">Squad Coaching Guidance</h2>
            <p className="mt-1 text-sm text-white/90">Team-level tactical advice for {sd.team || 'the squad'}</p>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            <div className="metric-card p-4">
              <div className="flex items-center gap-2 text-sm text-slate-500">
                <Users className="h-4 w-4 text-brand-500" />
                <span>Team</span>
              </div>
              <p className="mt-1 text-xl font-semibold text-slate-800">{sd.team || '—'}</p>
              <p className="text-xs text-slate-400">Coaching analysis target</p>
            </div>
            <div className="metric-card p-4">
              <div className="flex items-center gap-2 text-sm text-slate-500">
                <Sparkles className="h-4 w-4 text-emerald-500" />
                <span>Insights</span>
              </div>
              <p className="mt-1 text-xl font-semibold text-emerald-600">{guidanceItems.length}</p>
              <p className="text-xs text-slate-400">Actionable recommendations</p>
            </div>
            <div className="metric-card p-4">
              <div className="flex items-center gap-2 text-sm text-slate-500">
                <Crosshair className="h-4 w-4 text-violet-500" />
                <span>Findings</span>
              </div>
              <p className="mt-1 text-xl font-semibold text-violet-600">{findings.length}</p>
              <p className="text-xs text-slate-400">Data validation findings</p>
            </div>
          </div>

          {narrative && (
            <div className="mt-6 surface-muted p-4 border-l-4 border-l-amber-500">
              <div className="flex items-center gap-2 mb-2">
                <Sparkles className="h-4 w-4 text-amber-500" />
                <span className="text-sm font-semibold text-slate-800">Squad Narrative</span>
              </div>
              <p className="text-sm text-slate-600 leading-relaxed">{narrative}</p>
            </div>
          )}

          {guidanceItems.length > 0 && (
            <div className="mt-6">
              <div className="flex items-center gap-2 mb-3">
                <Lightbulb className="h-4 w-4 text-brand-500" />
                <span className="text-sm font-semibold text-slate-800">Recommendations</span>
              </div>
              <div className="grid grid-cols-1 gap-3">
                {guidanceItems.map((g, i) => (
                  <GuidanceCard key={i} guidance={g} />
                ))}
              </div>
            </div>
          )}

          {findings.length > 0 && (
            <div className="mt-6">
              <div className="flex items-center gap-2 mb-3">
                <Crosshair className="h-4 w-4 text-violet-500" />
                <span className="text-sm font-semibold text-slate-800">Data Validation ({findings.length} findings)</span>
              </div>
              <div className="grid grid-cols-1 gap-2">
                {findings.map((f, i) => (
                  <div key={i} className={`rounded-lg border p-3 text-xs ${f.severity === 'critical' ? 'border-rose-200 bg-rose-50' : f.severity === 'high' ? 'border-amber-200 bg-amber-50' : 'border-slate-200 bg-slate-50'}`}>
                    <div className="flex items-center gap-2">
                      <span className={`font-bold uppercase tracking-wider ${f.severity === 'critical' ? 'text-rose-600' : f.severity === 'high' ? 'text-amber-600' : 'text-slate-600'}`}>
                        {f.severity}
                      </span>
                      <span className={`ml-auto ${f.status === 'fixed' ? 'text-emerald-600' : 'text-slate-500'}`}>
                        [{f.status}]
                      </span>
                    </div>
                    <p className="mt-1 text-slate-700">{f.finding}</p>
                    {f.recommendation && <p className="mt-1 text-slate-500 italic">→ {f.recommendation}</p>}
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
              <h2 className="text-xl font-bold text-slate-900">Coaching Insights</h2>
              <p className="text-sm text-slate-500">Tactical guidance & performance analysis</p>
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
    return <ErrorAlert message="No coaching data available" />;
  }

  const guidance = data.guidance || {};
  const guidanceItems = guidance.insights || data.insights || [];
  const allGuidance = Array.isArray(guidanceItems) ? guidanceItems :
    Object.values(guidance).filter(v => typeof v === 'object' && v !== null && !Array.isArray(v) && (v.advice || v.suggestion));
  const mods = data.modules || {};
  const m = mods.momentum || {};

  return (
    <div className="space-y-6 theme-animated">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Coaching Insights</h2>
          <p className="text-sm text-slate-500">Tactical guidance & performance analysis</p>
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
          <h2 className="text-xl font-semibold">Player Coaching Guidance</h2>
          <p className="mt-1 text-sm text-white/90">
            {playerName || data.player_name} — tactical recommendations
          </p>
        </div>

        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <div className="metric-card p-4">
            <p className="text-sm text-slate-500">Position</p>
            <p className="text-lg font-semibold text-slate-900">{data.position || '—'}</p>
          </div>
          <div className="metric-card p-4">
            <p className="text-sm text-slate-500">Insights</p>
            <p className="text-lg font-semibold text-slate-900">{guidance.total_insights || allGuidance.length}</p>
          </div>
          <div className="metric-card p-4">
            <p className="text-sm text-slate-500">High Priority</p>
            <p className="text-lg font-semibold text-rose-600">{guidance.high_priority_count || 0}</p>
          </div>
          <div className="metric-card p-4">
            <p className="text-sm text-slate-500">Momentum</p>
            <p className="text-lg font-semibold text-slate-900 capitalize">{m.momentum_label || m.label || '—'}</p>
          </div>
        </div>

        {m.momentum_label && (
          <div className="mt-6 surface-muted p-4 border-l-4 border-l-cyan-500">
            <div className="flex items-center gap-2 mb-2">
              <Activity className="h-4 w-4 text-cyan-500" />
              <span className="text-sm font-semibold text-slate-800">Momentum</span>
            </div>
            <p className="text-sm text-slate-600">
              {m.momentum_label} momentum (score: {m.momentum_score?.toFixed(2) || '—'})
              — Recent avg: {m.recent_average?.toFixed(2) || '—'} vs overall: {m.overall_average?.toFixed(2) || '—'}
            </p>
          </div>
        )}

        {mods.forecast && (
          <div className="mt-6 surface-muted p-4 border-l-4 border-l-violet-500">
            <div className="flex items-center gap-2 mb-2">
              <Target className="h-4 w-4 text-violet-500" />
              <span className="text-sm font-semibold text-slate-800">Forecast</span>
            </div>
            <p className="text-sm text-slate-600">
              Predicted next score: {mods.forecast.predicted_next?.toFixed(2) || '—'}/10
              (trend: {mods.forecast.trend_direction || '—'})
              — Based on {mods.forecast.matches_used || '—'} matches
            </p>
          </div>
        )}

        {mods.injury_risk && (
          <div className="mt-6 surface-muted p-4 border-l-4 border-l-amber-500">
            <div className="flex items-center gap-2 mb-2">
              <Activity className="h-4 w-4 text-amber-500" />
              <span className="text-sm font-semibold text-slate-800">Injury Risk</span>
            </div>
            <p className="text-sm text-slate-600">
              Risk level: {mods.injury_risk.risk_level || '—'} ({mods.injury_risk.risk_score?.toFixed(1) || '—'}/10)
              — ACWR: {mods.injury_risk.acwr || '—'}
            </p>
          </div>
        )}

        {allGuidance.length > 0 && (
          <div className="mt-6">
            <div className="flex items-center gap-2 mb-3">
              <Lightbulb className="h-4 w-4 text-brand-500" />
              <span className="text-sm font-semibold text-slate-800">Recommendations ({allGuidance.length})</span>
            </div>
            <div className="grid grid-cols-1 gap-3">
              {allGuidance.map((g, i) => (
                <GuidanceCard key={i} guidance={g} />
              ))}
            </div>
          </div>
        )}

        <div className="mt-6 surface p-4 bg-gradient-to-r from-slate-50 to-slate-100">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="h-4 w-4 text-brand-500" />
            <span className="text-sm font-semibold text-slate-800">AI Analysis Summary</span>
          </div>
          <p className="text-sm text-slate-600 leading-relaxed">
            {guidance.context === 'player_comprehensive'
              ? `Comprehensive analysis for ${playerName || data.player_name} with ${guidance.total_insights || 0} actionable insights. ${guidance.high_priority_count || 0} high-priority items require attention.`
              : 'Coaching insights generated from match performance data. Recommendations are based on statistical analysis of player actions, physical output, and positional context.'}
          </p>
        </div>
      </section>
    </div>
  );
};

export default CoachingInsights;
