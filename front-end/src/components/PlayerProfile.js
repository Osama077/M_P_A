import React, { useEffect, useState, useMemo, useCallback } from 'react';
import {
  Activity, Loader2, Target, Footprints
} from 'lucide-react';
import {
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts';
import { PlayerProfileAPI } from '../api';
import { useAppContext } from '../context/AppContext';
import ErrorAlert from './ErrorAlert';

const DIM_CONFIG = [
  { key: 'passing', label: 'Passing', color: '#3b82f6', bg: 'bg-blue-500' },
  { key: 'shooting', label: 'Shooting', color: '#ef4444', bg: 'bg-red-500' },
  { key: 'positioning', label: 'Positioning', color: '#22c55e', bg: 'bg-green-500' },
  { key: 'pressing', label: 'Pressing', color: '#f97316', bg: 'bg-orange-500' },
  { key: 'movement', label: 'Movement', color: '#a855f7', bg: 'bg-purple-500' },
  { key: 'physical', label: 'Physical', color: '#f59e0b', bg: 'bg-amber-500' },
  { key: 'behavioral', label: 'Behavioral', color: '#06b6d4', bg: 'bg-cyan-500' },
];

const PCT_COLORS = {
  grn: { text: 'text-emerald-500', bg: 'bg-emerald-500', fill: '#22c55e' },
  blu: { text: 'text-blue-500', bg: 'bg-blue-500', fill: '#3b82f6' },
  pur: { text: 'text-purple-500', bg: 'bg-purple-500', fill: '#a855f7' },
  red: { text: 'text-red-500', bg: 'bg-red-500', fill: '#ef4444' },
  yel: { text: 'text-amber-500', bg: 'bg-amber-500', fill: '#f59e0b' },
};

const TIMELINE_TYPES = [
  { type: 'goal', color: '#22c55e', label: 'Goal', icon: '⚽' },
  { type: 'shot', color: '#3b82f6', label: 'Shot', icon: '' },
  { type: 'save', color: '#22c55e', label: 'Save', icon: '' },
  { type: 'key_pass', color: '#f59e0b', label: 'Key Pass', icon: '' },
  { type: 'dribble', color: '#a855f7', label: 'Dribble', icon: '' },
  { type: 'progressive_carry', color: '#06b6d4', label: 'Prog. Carry', icon: '' },
  { type: 'foul_won', color: '#ef4444', label: 'Foul Won', icon: '' },
];

function resultBadge(result) {
  if (!result) return 'rb-s';
  if (result.startsWith('W')) return 'bg-emerald-500/10 text-emerald-500';
  if (result.startsWith('D')) return 'bg-amber-500/10 text-amber-500';
  if (result.startsWith('L')) return 'bg-red-500/10 text-red-500';
  return 'bg-slate-500/10 text-slate-500';
}

function initials(name) {
  const parts = (name || '').split(' ');
  if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  return (name || '?')[0].toUpperCase();
}

const PlayerProfile = ({ playerName, initialMatchId }) => {
  const { openPlayerDashboard, selectedSeason, setSelectedSeason, seasonOptions } = useAppContext();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedMatchId, setSelectedMatchId] = useState(initialMatchId || null);
  const [viewMode, setViewMode] = useState('match');
  const [logSortKey, setLogSortKey] = useState('week');
  const [logSortAsc, setLogSortAsc] = useState(false);

  const fetchData = useCallback(async (name, matchId) => {
    if (!name) return;
    setLoading(true);
    setError(null);
    try {
      const result = await PlayerProfileAPI.getPlayerProfile(name, matchId, selectedSeason);
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [selectedSeason]);

  useEffect(() => {
    setSelectedMatchId(initialMatchId || null);
  }, [playerName, initialMatchId]);

  useEffect(() => { setSelectedMatchId(null); }, [selectedSeason]);

  useEffect(() => {
    fetchData(playerName, selectedMatchId);
  }, [playerName, selectedMatchId, fetchData, selectedSeason]);

  const handlePlayerClick = (pid, pname) => {
    openPlayerDashboard(pname, pid, selectedMatchId);
  };

  const contextScores = useMemo(() => {
    if (!data) return null;
    const rd = data.radar_data || {};

    if (viewMode === 'season') {
      const labels = rd.labels || ['Passing', 'Shooting', 'Positioning', 'Pressing', 'Movement', 'Physical', 'Behavioral'];
      const values = rd.season_values || [0, 0, 0, 0, 0, 0, 0, 0];
      return { labels, values };
    }
    if (viewMode === 'last5') {
      const td = data.trend_data || [];
      const last5 = td.slice(-5);
      const dimKeys = ['passing', 'shooting', 'positioning', 'pressing', 'movement', 'physical', 'behavioral'];
      const values = dimKeys.map(key => {
        const scores = last5.map(t => t[key + '_score'] || 0);
        return scores.length ? parseFloat((scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(2)) : 0;
      });
      const labels = rd.labels || ['Passing', 'Shooting', 'Positioning', 'Pressing', 'Movement', 'Physical', 'Behavioral'];
      return { labels, values };
    }

    const labels = rd.labels || ['Passing', 'Shooting', 'Positioning', 'Pressing', 'Movement', 'Physical', 'Behavioral'];
    const values = rd.match_values || [0, 0, 0, 0, 0, 0, 0, 0];
    return { labels, values };
  }, [data, viewMode]);

  const sortedLog = useMemo(() => {
    if (!data?.match_log) return [];
    return [...data.match_log].sort((a, b) => {
      const va = a[logSortKey] ?? '';
      const vb = b[logSortKey] ?? '';
      const cmp = typeof va === 'string' ? va.localeCompare(vb) : va - vb;
      return logSortAsc ? cmp : -cmp;
    });
  }, [data, logSortKey, logSortAsc]);

  const toggleLogSort = (key) => {
    if (logSortKey === key) setLogSortAsc(p => !p);
    else { setLogSortKey(key); setLogSortAsc(true); }
  };

  const logSortIcon = (key) => {
    if (logSortKey !== key) return <span className="ml-0.5 opacity-30">↕</span>;
    return <span className="ml-0.5">{logSortAsc ? '↑' : '↓'}</span>;
  };

  if (loading) {
    return (
      <div className="surface-muted p-12 text-center">
        <Loader2 className="mx-auto h-6 w-6 animate-spin text-brand-600" />
        <p className="mt-3 text-sm text-slate-600">Loading player profile...</p>
      </div>
    );
  }
  if (error) return <ErrorAlert message={error} onRetry={() => fetchData(playerName, selectedMatchId)} />;
  if (!data) return <ErrorAlert message="No player data available" />;

  const { player_info: pi, match_context: mc, squad_mates, match_stats: mstats,
          percentiles, season_stats: ss, radar_data: rd, trend_data: td,
          timeline_events, available_matches, charts } = data;

  const contextLabel = viewMode === 'match' ? 'This Match' : viewMode === 'season' ? 'Season Avg' : 'Last 5 Avg';

  return (
    <div className="space-y-5">

      {/* ── Player Selector ── */}
      {squad_mates && squad_mates.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 p-3 bg-white rounded-xl border border-slate-200">
          <span className="text-[11px] font-semibold text-slate-500 mr-1">Players:</span>
          {squad_mates.map((sm) => (
            <button
              key={sm.player_id}
              onClick={() => handlePlayerClick(sm.player_id, sm.player_name)}
              className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer border ${
                sm.is_current
                  ? 'bg-brand-600 text-white border-brand-600'
                  : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
              }`}
            >
              <span
                className="flex h-5 w-5 items-center justify-center rounded-full text-[8px] font-black"
                style={{ background: sm.is_current ? '#ffffff22' : sm.color + '22', color: sm.is_current ? '#fff' : sm.color }}
              >
                {sm.initials || initials(sm.player_name)}
              </span>
              <span className="truncate max-w-[100px]">{sm.player_name.split(' ').pop()}</span>
              <span className="font-mono text-[11px] font-bold">{sm.overall_score?.toFixed(1)}</span>
            </button>
          ))}
          <div className="ml-auto flex items-center gap-2">
            <span className="text-[11px] text-slate-500">Season</span>
            <select
              value={selectedSeason || ''}
              onChange={(e) => { setSelectedSeason(e.target.value || null); setSelectedMatchId(null); }}
              className="field text-xs py-1.5 w-24"
              aria-label="Select season"
            >
              <option value="">All</option>
              {seasonOptions.map((s) => (
                <option key={s.label} value={s.label}>{s.label}</option>
              ))}
            </select>
            <span className="text-[11px] text-slate-500">Match</span>
            <select
              value={selectedMatchId || ''}
              onChange={(e) => setSelectedMatchId(Number(e.target.value))}
              className="field text-xs py-1.5 w-48"
              aria-label="Select match"
            >
              {(available_matches || []).map((m) => (
                <option key={m.match_id} value={m.match_id}>
                  {m.label}
                </option>
              ))}
            </select>
            <select
              value={viewMode}
              onChange={(e) => setViewMode(e.target.value)}
              className="field text-xs py-1.5 w-28"
              aria-label="View mode"
            >
              <option value="match">This Match</option>
              <option value="season">Season Avg</option>
              <option value="last5">Last 5</option>
            </select>
          </div>
        </div>
      )}

      {/* ── Player Hero ── */}
      <div className="relative overflow-hidden rounded-xl border border-blue-500/20"
        style={{ background: 'linear-gradient(135deg, #040e1e, #07111f)' }}>
        <div className="absolute inset-0 pointer-events-none"
          style={{ background: 'repeating-linear-gradient(135deg, rgba(88,166,255,0.02) 0px, rgba(88,166,255,0.02) 1px, transparent 1px, transparent 28px)' }} />
        <div className="absolute -top-5 -right-5 w-60 h-60 rounded-full pointer-events-none"
          style={{ background: 'radial-gradient(circle, rgba(88,166,255,0.12), transparent 65%)' }} />
        <div className="relative z-10 flex flex-col md:flex-row items-start gap-5 p-5">
          <div className="flex items-center gap-4 flex-1">
            <div
              className="flex h-16 w-16 shrink-0 items-center justify-center rounded-full text-xl font-black border-[3px]"
              style={{ background: 'linear-gradient(135deg, #1a6be0, #0a4ab0)', color: '#fff', borderColor: 'rgba(88,166,255,0.3)' }}
            >
              {pi.initials || initials(pi.player_name)}
            </div>
            <div>
              <div className="text-xl font-black text-white">{pi.player_name}</div>
              <div className="text-xs text-slate-400 mt-0.5">
                {pi.position_label} · FC Barcelona · {pi.total_matches} matches
              </div>
              <div className="flex gap-1.5 mt-2 flex-wrap">
                <span className="px-2 py-0.5 rounded-full text-[9px] font-bold"
                  style={{ background: '#ef444422', color: '#ef4444' }}>{pi.position_label}</span>
                <span className="px-2 py-0.5 rounded-full text-[9px] font-bold"
                  style={{ background: '#22c55e22', color: '#22c55e' }}>
                  {pi.performance_trend === 'Improving' ? '↑ Improving' : pi.performance_trend === 'Declining' ? '↓ Declining' : '→ Stable'}
                </span>
                <span className="px-2 py-0.5 rounded-full text-[9px] font-bold"
                  style={{ background: '#3b82f622', color: '#3b82f6' }}>
                  {pi.player_cluster?.toUpperCase() || '—'}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-0 border-l border-slate-700 pl-5">
            <div className="text-center px-4 border-r border-slate-700">
              <div className="text-3xl font-black font-mono" style={{ color: pi.match_score >= 7 ? '#22c55e' : pi.match_score >= 6 ? '#f59e0b' : '#ef4444' }}>
                {pi.match_score?.toFixed(1) || '—'}
              </div>
              <div className="text-[9px] text-slate-500 uppercase tracking-wider mt-1">ML Score</div>
              <div className="text-[10px] text-amber-500">{contextLabel}</div>
            </div>
            <div className="text-center px-4 border-r border-slate-700">
              <div className="text-3xl font-black font-mono text-emerald-500">P{ss?.matches_above_7 || 0 > 20 ? (ss.matches_above_7 > 25 ? 99 : 90) : 70}</div>
              <div className="text-[9px] text-slate-500 uppercase tracking-wider mt-1">Percentile</div>
              <div className="text-[10px] text-slate-500">vs {pi.position_label}</div>
            </div>
            <div className="text-center px-4">
              <div className="text-3xl font-black font-mono" style={{ color: ss?.delta_vs_avg >= 0 ? '#22c55e' : '#ef4444' }}>
                {ss?.delta_vs_avg >= 0 ? '+' : ''}{ss?.delta_vs_avg?.toFixed(1) || '0.0'}
              </div>
              <div className="text-[9px] text-slate-500 uppercase tracking-wider mt-1">Trend</div>
              <div className="text-[10px]" style={{ color: ss?.delta_vs_avg >= 0 ? '#22c55e' : '#ef4444' }}>
                {ss?.delta_vs_avg >= 0 ? '↑ Improving' : '↓ Declining'}
              </div>
            </div>
          </div>
        </div>

        {/* 7-dim scores */}
        <div className="px-5 pb-4 relative z-10">
          <div className="grid grid-cols-7 gap-2">
            {DIM_CONFIG.map((dim) => {
              const val = viewMode === 'match' ? data.match_scores?.[dim.key] : viewMode === 'season' ? rd.season_values?.[DIM_CONFIG.indexOf(dim)] : contextScores?.values?.[DIM_CONFIG.indexOf(dim)] || 0;
              return (
                <div key={dim.key} className="bg-[#161B2288] rounded-lg p-2 text-center border border-[#30363D44]">
                  <div className="text-lg font-black font-mono" style={{ color: dim.color }}>{val.toFixed(1)}</div>
                  <div className="h-1 rounded-full overflow-hidden bg-slate-700 my-1.5">
                    <div className="h-full rounded-full" style={{ width: `${Math.min(val * 10, 100)}%`, background: dim.color }} />
                  </div>
                  <div className="text-[8px] text-slate-500">{dim.label}</div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* ── Season-Level ML Analysis (Recharts animated) ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="surface">
          <div className="ch border-b border-slate-200 px-4 py-3">
            <span className="text-sm font-bold text-slate-900">Performance Radar — {contextLabel}</span>
            <span className="text-xs text-slate-500">ML Model · 7 Dimensions</span>
          </div>
          <div className="p-4">
            {contextScores && (
              <ResponsiveContainer width="100%" height={280}>
                <RadarChart data={contextScores.labels.map((label, i) => ({ label, value: contextScores.values[i] }))}>
                  <PolarGrid stroke="#e2e8f0" />
                  <PolarAngleAxis dataKey="label" tick={{ fontSize: 10, fill: '#64748b' }} />
                  <PolarRadiusAxis angle={90} domain={[0, 10]} tick={{ fontSize: 9, fill: '#cbd5e1' }} tickCount={6} />
                  <Radar dataKey="value" stroke="#1a6be0" fill="#1a6be0" fillOpacity={0.2} strokeWidth={2} />
                </RadarChart>
              </ResponsiveContainer>
            )}
            <div className="grid grid-cols-7 gap-2 mt-3 text-center">
              {DIM_CONFIG.map((dim) => {
                const val = contextScores?.values?.[DIM_CONFIG.indexOf(dim)] || 0;
                return (
                  <div key={dim.key}>
                    <div className="text-sm font-black font-mono" style={{ color: dim.color }}>{val.toFixed(1)}</div>
                    <div className="text-[8px] text-slate-400 uppercase">{dim.label.slice(0, 3)}</div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        <div className="surface">
          <div className="ch border-b border-slate-200 px-4 py-3">
            <span className="text-sm font-bold text-slate-900">Score Trend — {td?.length || 0} matches</span>
            <div className="flex gap-3 text-[10px] text-slate-500">
              <span><span className="text-blue-500">●</span> Score</span>
              <span><span className="text-amber-500">—</span> 3-Match Avg</span>
            </div>
          </div>
          <div className="p-4">
            {td && td.length > 0 && (
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={td}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="week" tick={{ fontSize: 9, fill: '#94a3b8' }} />
                  <YAxis domain={[0, 10]} tick={{ fontSize: 9, fill: '#94a3b8' }} />
                  <Tooltip contentStyle={{ fontSize: 11, borderRadius: 8 }} />
                  <Line type="monotone" dataKey="overall_score" stroke="#3b82f6" strokeWidth={2} dot={false} name="Score" />
                  <Line type="monotone" dataKey="rolling_avg" stroke="#f59e0b" strokeWidth={1.5} strokeDasharray="4 3" dot={false} name="3-Match Avg" />
                  <ReferenceLine y={ss?.season_avg || 7} stroke="#94a3b8" strokeDasharray="3 3" label={{ value: 'Avg', fontSize: 9, fill: '#94a3b8', position: 'right' }} />
                </LineChart>
              </ResponsiveContainer>
            )}
            <div className="grid grid-cols-5 gap-3 mt-3">
              <div className="bg-slate-50 rounded-lg p-2.5 text-center">
                <div className="text-base font-black font-mono text-amber-600">{ss?.season_avg?.toFixed(1) || '—'}</div>
                <div className="text-[9px] text-slate-500">Season Avg</div>
              </div>
              <div className="bg-slate-50 rounded-lg p-2.5 text-center">
                <div className="text-base font-black font-mono text-emerald-600">{ss?.best_match?.toFixed(1) || '—'}</div>
                <div className="text-[9px] text-slate-500">Best Match</div>
              </div>
              <div className="bg-slate-50 rounded-lg p-2.5 text-center">
                <div className="text-base font-black font-mono text-red-600">{ss?.worst_match?.toFixed(1) || '—'}</div>
                <div className="text-[9px] text-slate-500">Worst Match</div>
              </div>
              <div className="bg-slate-50 rounded-lg p-2.5 text-center">
                <div className="text-base font-black font-mono text-blue-600">{ss?.matches_above_7 || 0}</div>
                <div className="text-[9px] text-slate-500">≥ 7.0</div>
              </div>
              <div className="bg-slate-50 rounded-lg p-2.5 text-center">
                <div className="text-base font-black font-mono" style={{ color: ss?.delta_vs_avg >= 0 ? '#22c55e' : '#ef4444' }}>
                  {ss?.delta_vs_avg >= 0 ? '+' : ''}{ss?.delta_vs_avg?.toFixed(1) || '0.0'}
                </div>
                <div className="text-[9px] text-slate-500">This Match</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Match Activity Timeline ── */}
      {timeline_events && timeline_events.length > 0 && (
        <div className="surface">
          <div className="ch border-b border-slate-200 px-4 py-3">
            <span className="text-sm font-bold text-slate-900">Match Activity Timeline</span>
            <span className="text-xs text-slate-500">{mc?.home_team} vs {mc?.away_team}</span>
          </div>
          <div className="p-4">
            <div className="relative h-14 bg-slate-100 rounded-lg overflow-hidden">
              <div className="absolute top-1/2 left-0 right-0 h-px bg-slate-300" />
              <div className="absolute top-0 left-1/2 w-px h-full bg-slate-300 opacity-50" />
              <span className="absolute top-1 left-1/2 -translate-x-1/2 text-[8px] text-slate-400">HT</span>
              {timeline_events.map((e, i) => {
                const cfg = TIMELINE_TYPES.find(t => t.type === e.type) || TIMELINE_TYPES[1];
                const size = e.type === 'goal' ? 12 : 8;
                return (
                  <div
                    key={i}
                    className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full cursor-pointer transition hover:scale-150 z-10"
                    style={{
                      left: `${(e.minute / 90) * 100}%`,
                      width: size, height: size,
                      background: cfg.color,
                      boxShadow: e.type === 'goal' ? `0 0 8px ${cfg.color}` : 'none',
                    }}
                    title={`${e.minute}' — ${cfg.label}${e.xg ? ` (xG: ${e.xg})` : ''}`}
                  />
                );
              })}
            </div>
            <div className="flex justify-between text-[9px] text-slate-400 px-0.5 mt-1">
              <span>0'</span><span>15'</span><span>30'</span><span>45'</span><span>60'</span><span>75'</span><span>90'</span>
            </div>
            <div className="flex gap-4 mt-2 flex-wrap">
              {TIMELINE_TYPES.map((t) => (
                <div key={t.type} className="flex items-center gap-1.5 text-[9px] text-slate-500">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ background: t.color }} />
                  {t.label}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── Spatial Analysis — heatmap / pass map / shot map ── */}
      {charts && (charts.heatmap || charts.pass_map || charts.shot_map) && (
        <div className="surface">
          <div className="ch border-b border-slate-200 px-4 py-3">
            <span className="text-sm font-bold text-slate-900">Spatial Analysis — {mc?.home_team} vs {mc?.away_team}</span>
            <span className="text-xs text-slate-500">ML-generated heatmap, pass & shot maps</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 p-3">
            <div className="bg-slate-50 rounded-lg overflow-hidden border border-slate-200">
              <div className="px-3 py-2 bg-slate-100 border-b border-slate-200 flex items-center gap-2">
                <Activity className="w-3.5 h-3.5 text-orange-500" />
                <span className="text-[11px] font-bold text-slate-700">Position Heatmap</span>
              </div>
              <div className="p-2">
                {charts.heatmap ? (
                  <img src={charts.heatmap} alt="Position Heatmap" className="w-full rounded" />
                ) : (
                  <div className="h-40 flex items-center justify-center text-[10px] text-slate-400">N/A</div>
                )}
              </div>
            </div>
            <div className="bg-slate-50 rounded-lg overflow-hidden border border-slate-200">
              <div className="px-3 py-2 bg-slate-100 border-b border-slate-200 flex items-center gap-2">
                <Footprints className="w-3.5 h-3.5 text-blue-500" />
                <span className="text-[11px] font-bold text-slate-700">Pass Map</span>
              </div>
              <div className="p-2">
                {charts.pass_map ? (
                  <img src={charts.pass_map} alt="Pass Map" className="w-full rounded" />
                ) : (
                  <div className="h-40 flex items-center justify-center text-[10px] text-slate-400">N/A</div>
                )}
              </div>
            </div>
            <div className="bg-slate-50 rounded-lg overflow-hidden border border-slate-200">
              <div className="px-3 py-2 bg-slate-100 border-b border-slate-200 flex items-center gap-2">
                <Target className={`w-3.5 h-3.5 ${pi?.position_group === 'GK' ? 'text-green-500' : 'text-red-500'}`} />
                <span className="text-[11px] font-bold text-slate-700">
                  {pi?.position_group === 'GK' ? 'Saves Map' : 'Shot Map'}
                </span>
              </div>
              <div className="p-2">
                {charts.shot_map ? (
                  <img src={charts.shot_map} alt={pi?.position_group === 'GK' ? 'Saves Map' : 'Shot Map'} className="w-full rounded" />
                ) : (
                  <div className="h-40 flex items-center justify-center text-[10px] text-slate-400">N/A</div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Percentiles ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 surface">
          <div className="ch border-b border-slate-200 px-4 py-3">
            <span className="text-sm font-bold text-slate-900">Percentile Rankings vs {pi.position_label}</span>
            <span className="text-xs text-slate-500">vs position avg</span>
          </div>
          <div className="p-4 space-y-1">
            {percentiles.map((pct) => {
              const c = PCT_COLORS[pct.color] || PCT_COLORS.grn;
              return (
                <div key={pct.label} className="flex items-center gap-3 py-1.5 border-b border-slate-100 last:border-0">
                  <span className="text-[11px] text-slate-600 w-28 shrink-0">{pct.label}</span>
                  <div className="flex-1 h-2 bg-slate-200 rounded-full overflow-hidden relative">
                    <div className="h-full rounded-full transition-all" style={{ width: `${pct.percentile}%`, background: c.fill }} />
                    <div className="absolute top-0 h-full w-0.5 bg-white/30 left-1/2" />
                  </div>
                  <span className={`text-[11px] font-bold font-mono w-14 text-right ${c.text}`}>
                    {typeof pct.value === 'number' ? (pct.label.includes('%') ? pct.value.toFixed(1) + '%' : pct.label.includes('Gm') ? pct.value.toFixed(1) : pct.value > 10 ? pct.value : pct.value.toFixed(2)) : pct.value}
                  </span>
                  <span className="text-[10px] text-slate-400 w-10 text-right font-mono">P{pct.percentile}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* ── Match Stats Summary ── */}
        <div className="surface">
          <div className="ch border-b border-slate-200 px-4 py-3">
            <span className="text-sm font-bold text-slate-900">Match Stats</span>
            <span className="text-xs text-slate-500">{contextLabel}</span>
          </div>
          <div className="p-4 grid grid-cols-2 gap-3">
            {(pi?.position_group === 'GK' ? [
              { label: 'Saves', val: mstats?.saves, color: '#22c55e' },
              { label: 'Save %', val: mstats?.save_pct, suffix: '%', color: '#3b82f6' },
              { label: 'Goals Conceded', val: mstats?.goals_conceded, color: '#ef4444' },
              { label: 'Shots Faced', val: mstats?.shots_faced, color: '#f59e0b' },
              { label: 'Passes', val: mstats?.total_passes, color: '#3b82f6' },
              { label: 'Accuracy', val: mstats?.pass_accuracy, suffix: '%', color: '#22c55e' },
              { label: 'Progress. Passes', val: mstats?.progressive_passes, color: '#06b6d4' },
              { label: 'Distance', val: mstats?.distance_covered ? (mstats.distance_covered / 1000).toFixed(1) + 'km' : null, color: '#1d4ed8' },
              { label: 'Fouls Won', val: mstats?.fouls_won, color: '#84cc16' },
            ] : [
              { label: 'Passes', val: mstats?.total_passes, color: '#3b82f6' },
              { label: 'Accuracy', val: mstats?.pass_accuracy, suffix: '%', color: '#22c55e' },
              { label: 'Shots', val: mstats?.total_shots, color: '#ef4444' },
              { label: 'xG', val: mstats?.total_xg, color: '#f59e0b' },
              { label: 'Dribble%', val: mstats?.dribble_success_rate, suffix: '%', color: '#a855f7' },
              { label: 'Progress. Passes', val: mstats?.progressive_passes, color: '#06b6d4' },
              { label: 'Pressures', val: mstats?.total_pressures, color: '#f97316' },
              { label: 'Fouls Won', val: mstats?.fouls_won, color: '#84cc16' },
              { label: 'Distance', val: mstats?.distance_covered ? (mstats.distance_covered / 1000).toFixed(1) + 'km' : null, color: '#1d4ed8' },
            ]).filter(s => s.val !== undefined && s.val !== null).map((s) => (
              <div key={s.label} className="bg-slate-50 rounded-lg p-2.5 text-center border border-slate-200">
                <div className="text-lg font-black font-mono" style={{ color: s.color }}>
                  {typeof s.val === 'number' ? (s.suffix ? s.val.toFixed(1) + s.suffix : s.val) : s.val}
                </div>
                <div className="text-[9px] text-slate-500 mt-0.5">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Full Season Match Log ── */}
      <div className="surface">
        <div className="ch border-b border-slate-200 px-4 py-3">
          <span className="text-sm font-bold text-slate-900">Full Season Match Log — {ss?.total_matches || '?'} Matches</span>
          <select className="field text-xs py-1 px-2"
            onChange={(e) => {
              const v = e.target.value;
              if (v === 'all') setLogSortKey('week');
              else if (v === 'high') toggleLogSort('ml_score');
            }}
          >
            <option value="all">All Matches</option>
            <option value="high">Highest Score</option>
          </select>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50">
                <th className="px-3 py-2 text-left font-bold text-slate-600 cursor-pointer select-none whitespace-nowrap" onClick={() => toggleLogSort('week')}>Week {logSortIcon('week')}</th>
                <th className="px-3 py-2 text-left font-bold text-slate-600 cursor-pointer select-none" onClick={() => toggleLogSort('opponent')}>Opponent {logSortIcon('opponent')}</th>
                <th className="px-3 py-2 text-left font-bold text-slate-600 cursor-pointer select-none" onClick={() => toggleLogSort('result')}>Result {logSortIcon('result')}</th>
                <th className="px-3 py-2 text-left font-bold text-slate-600 cursor-pointer select-none" onClick={() => toggleLogSort('ml_score')}>ML Score {logSortIcon('ml_score')}</th>
                <th className="px-3 py-2 text-left font-bold text-slate-600 cursor-pointer select-none" onClick={() => toggleLogSort('delta_vs_avg')}>Δ Avg {logSortIcon('delta_vs_avg')}</th>
                <th className="px-3 py-2 text-left font-bold text-slate-600 cursor-pointer select-none" onClick={() => toggleLogSort('trend')}>Trend {logSortIcon('trend')}</th>
                <th className="px-3 py-2 text-left font-bold text-slate-600 cursor-pointer select-none" onClick={() => toggleLogSort('total_passes')}>Passes {logSortIcon('total_passes')}</th>
                <th className="px-3 py-2 text-left font-bold text-slate-600 cursor-pointer select-none" onClick={() => toggleLogSort('pass_accuracy')}>Acc% {logSortIcon('pass_accuracy')}</th>
                <th className="px-3 py-2 text-left font-bold text-slate-600 cursor-pointer select-none" onClick={() => toggleLogSort('total_shots')}>Shots {logSortIcon('total_shots')}</th>
                <th className="px-3 py-2 text-left font-bold text-slate-600 cursor-pointer select-none" onClick={() => toggleLogSort('total_xg')}>xG {logSortIcon('total_xg')}</th>
                <th className="px-3 py-2 text-left font-bold text-slate-600 cursor-pointer select-none" onClick={() => toggleLogSort('dribble_success_rate')}>Drb% {logSortIcon('dribble_success_rate')}</th>
                <th className="px-3 py-2 text-left font-bold text-slate-600 cursor-pointer select-none" onClick={() => toggleLogSort('progressive_passes')}>Prog P. {logSortIcon('progressive_passes')}</th>
                <th className="px-3 py-2 text-left font-bold text-slate-600 cursor-pointer select-none" onClick={() => toggleLogSort('vaep_rating')}>VAEP {logSortIcon('vaep_rating')}</th>
                <th className="px-3 py-2 text-left font-bold text-slate-600 cursor-pointer select-none" onClick={() => toggleLogSort('distance_covered')}>Dist {logSortIcon('distance_covered')}</th>
                <th className="px-3 py-2 text-left font-bold text-slate-600 cursor-pointer select-none" onClick={() => toggleLogSort('total_pressures')}>Press {logSortIcon('total_pressures')}</th>
              </tr>
            </thead>
            <tbody>
              {sortedLog.map((m, i) => (
                <tr key={m.match_id || i}
                  className={`border-b border-slate-100 cursor-pointer hover:bg-slate-50 transition ${m.is_current ? 'bg-emerald-500/5' : ''}`}
                  onClick={() => setSelectedMatchId(m.match_id)}
                >
                  <td className="px-3 py-2 font-mono text-[11px] text-slate-500">W{m.week}</td>
                  <td className={`px-3 py-2 font-semibold ${m.is_current ? 'text-emerald-600' : 'text-slate-900'}`}>
                    {m.opponent}{m.is_current ? ' ◄' : ''}
                  </td>
                  <td className="px-3 py-2">
                    <span className={`inline-block px-1.5 py-0.5 rounded-full text-[9px] font-bold font-mono ${resultBadge(m.result)}`}>{m.result}</span>
                  </td>
                  <td className="px-3 py-2">
                    <span className="font-mono text-sm font-black" style={{
                      color: m.ml_score >= 7.5 ? '#22c55e' : m.ml_score >= 7 ? '#3b82f6' : m.ml_score >= 6 ? '#f59e0b' : m.ml_score >= 5 ? '#f97316' : '#ef4444'
                    }}>{m.ml_score?.toFixed(1)}</span>
                  </td>
                  <td className="px-3 py-2 font-mono text-xs font-bold" style={{ color: m.delta_vs_avg >= 0.3 ? '#22c55e' : m.delta_vs_avg >= -0.3 ? '#94a3b8' : '#ef4444' }}>
                    {m.delta_vs_avg > 0 ? '+' : ''}{m.delta_vs_avg?.toFixed(1)}
                  </td>
                  <td className="px-3 py-2">
                    <span className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-[9px] font-bold font-mono ${
                      m.trend === 'up' ? 'bg-emerald-100 text-emerald-700' :
                      m.trend === 'dn' ? 'bg-red-100 text-red-700' :
                      'bg-slate-100 text-slate-600'
                    }`}>
                      {m.trend === 'up' ? '↑' : m.trend === 'dn' ? '↓' : '→'} {m.trend === 'up' ? 'Imp' : m.trend === 'dn' ? 'Dec' : 'Stbl'}
                    </span>
                  </td>
                  <td className="px-3 py-2 font-mono">{m.total_passes}</td>
                  <td className="px-3 py-2 font-mono" style={{ color: m.pass_accuracy >= 85 ? '#22c55e' : m.pass_accuracy >= 75 ? '#3b82f6' : '#f59e0b' }}>
                    {m.pass_accuracy?.toFixed(1)}%
                  </td>
                  <td className="px-3 py-2 font-mono">{m.total_shots}</td>
                  <td className="px-3 py-2">
                    <span className={`inline-block px-1 py-0.5 rounded text-[9px] font-bold font-mono ${
                      m.total_xg >= 0.8 ? 'bg-emerald-100 text-emerald-700' :
                      m.total_xg >= 0.4 ? 'bg-amber-100 text-amber-700' :
                      'bg-red-100 text-red-700'
                    }`}>{m.total_xg?.toFixed(2)}</span>
                  </td>
                  <td className="px-3 py-2 font-mono text-purple-600">{m.dribble_success_rate?.toFixed(0)}%</td>
                  <td className="px-3 py-2 font-mono text-cyan-600">{m.progressive_passes}</td>
                  <td className="px-3 py-2 font-mono font-bold" style={{ color: m.vaep_rating >= 1.5 ? '#22c55e' : m.vaep_rating >= 1 ? '#3b82f6' : '#f59e0b' }}>
                    {m.vaep_rating?.toFixed(2)}
                  </td>
                  <td className="px-3 py-2 font-mono text-slate-500">{m.distance_covered ? (m.distance_covered / 1000).toFixed(1) + 'km' : '—'}</td>
                  <td className="px-3 py-2 font-mono" style={{ color: m.total_pressures <= 8 ? '#ef4444' : m.total_pressures <= 12 ? '#f59e0b' : '#22c55e' }}>
                    {m.total_pressures}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {sortedLog.length === 0 && (
            <div className="text-center py-8 text-sm text-slate-500">No match data available.</div>
          )}
        </div>
      </div>

    </div>
  );
};

export default PlayerProfile;
