import React, { useEffect, useState, useMemo, useCallback } from 'react';
import {
  AlertTriangle, Award,
  Loader2, Search, TrendingDown, TrendingUp, Minus
} from 'lucide-react';
import { SquadAPI } from '../api';
import { useAppContext } from '../context/AppContext';
import ErrorAlert from './ErrorAlert';
import useDebouncedValue from '../hooks/useDebouncedValue';

const POS_GROUPS = ['all', 'GK', 'DF', 'MF', 'FW'];
const POS_LABELS = { all: 'All Positions', GK: 'GK', DF: 'Defenders', MF: 'Midfielders', FW: 'Forwards' };
const POS_COLORS = { GK: 'text-orange-500', DF: 'text-blue-500', MF: 'text-green-500', FW: 'text-red-500' };
const POS_BG_COLORS = { GK: 'bg-orange-500/10', DF: 'bg-blue-500/10', MF: 'bg-green-500/10', FW: 'bg-red-500/10' };

const DIM_COLORS = {
  passing: { bar: '#3b82f6', text: 'text-blue-500' },
  shooting: { bar: '#ef4444', text: 'text-red-500' },
  positioning: { bar: '#22c55e', text: 'text-green-500' },
  pressing: { bar: '#f97316', text: 'text-orange-500' },
  movement: { bar: '#a855f7', text: 'text-purple-500' },
};

const KPI_CONFIG = [
  { key: 'avg_overall_score', label: 'Squad Avg Score', suffix: '', color: 'emerald', badge: null },
  { key: 'total_passes', label: 'Total Passes', color: 'blue', badge: (d) => `${d?.pass_accuracy?.toFixed(1) || '—'}% acc` },
  { key: 'total_shots', label: 'Total Shots', color: 'red', badge: (d) => `${d?.shots_on_target || 0} on target` },
  { key: 'total_xg', label: 'Team xG', color: 'emerald', badge: null },
  { key: 'total_dribbles', label: 'Dribbles', color: 'purple', badge: (d) => `${d?.dribble_success_pct?.toFixed(1) || '—'}% success` },
  { key: 'team_vaep', label: 'Team VAEP', color: 'orange', badge: null },
  { key: 'possession_pct', label: 'Possession', color: 'amber', badge: (d) => 'vs opponent' },
  { key: 'total_pressures', label: 'Pressures', color: 'teal', badge: (d) => `${d?.pressure_regains || 0} regains` },
];

const KPI_BAR_COLORS = {
  emerald: 'from-emerald-500', blue: 'from-blue-500', red: 'from-red-500',
  purple: 'from-purple-500', orange: 'from-orange-500', amber: 'from-amber-500', teal: 'from-teal-500',
};

function formatKpi(key, val, teamStats) {
  if (val === null || val === undefined) return '—';
  if (key === 'possession_pct') return `${val.toFixed(1)}%`;
  if (key === 'avg_overall_score') return val.toFixed(1);
  if (key === 'total_xg' || key === 'team_vaep') return val.toFixed(2);
  if (key === 'total_passes' || key === 'total_shots' || key === 'total_dribbles' || key === 'total_pressures') return Math.round(val);
  return val;
}

const SquadOverview = () => {
  const { openPlayerDashboard } = useAppContext();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [posFilter, setPosFilter] = useState('all');
  const [trendFilter, setTrendFilter] = useState('all');
  const [sortKey, setSortKey] = useState('overall_score');
  const [sortAsc, setSortAsc] = useState(false);
  const [selectedSquadMatchId, setSelectedSquadMatchId] = useState(null);
  const debouncedSearch = useDebouncedValue(searchTerm, 200);

  const fetchData = useCallback(async (matchId) => {
    setLoading(true);
    setError(null);
    try {
      const result = await SquadAPI.getSquadOverview(matchId);
      setData(result);
      if (result?.match_context?.match_id) {
        setSelectedSquadMatchId(result.match_context.match_id);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleMatchChange = useCallback((mid) => {
    setSelectedSquadMatchId(mid);
    fetchData(mid);
  }, [fetchData]);

  const filteredPlayers = useMemo(() => {
    if (!data?.players) return [];
    return data.players
      .filter(p => {
        if (posFilter !== 'all' && p.position_group !== posFilter) return false;
        if (trendFilter === 'up' && p.performance_trend !== 'Improving') return false;
        if (trendFilter === 'dn' && p.performance_trend !== 'Declining') return false;
        if (debouncedSearch && !p.player_name.toLowerCase().includes(debouncedSearch.toLowerCase())) return false;
        return true;
      })
      .sort((a, b) => {
        const va = a[sortKey] ?? 0;
        const vb = b[sortKey] ?? 0;
        return sortAsc ? va - vb : vb - va;
      });
  }, [data, posFilter, trendFilter, debouncedSearch, sortKey, sortAsc]);

  const toggleSort = (key) => {
    if (sortKey === key) setSortAsc(p => !p);
    else { setSortKey(key); setSortAsc(false); }
  };

  const sortIcon = (key) => {
    if (sortKey !== key) return <span className="ml-1 opacity-30">↕</span>;
    return <span className="ml-1 text-green-400">{sortAsc ? '↑' : '↓'}</span>;
  };

  const groupedPlayers = useMemo(() => {
    const groups = { FW: [], MF: [], DF: [], GK: [] };
    filteredPlayers.forEach(p => {
      const g = p.position_group === 'Attacker' ? 'FW' : p.position_group === 'Midfielder' ? 'MF' : p.position_group === 'Defender' ? 'DF' : 'GK';
      if (groups[g]) groups[g].push(p);
    });
    return groups;
  }, [filteredPlayers]);

  const trendIcon = (trend) => {
    if (trend === 'Improving') return <TrendingUp className="h-3 w-3" />;
    if (trend === 'Declining') return <TrendingDown className="h-3 w-3" />;
    return <Minus className="h-3 w-3" />;
  };

  const playerColor = (pid) => {
    const colors = ['#1a6be0', '#22c55e', '#f59e0b', '#7c3aed', '#e05c1a', '#06b6d4', '#84cc16', '#f43f5e', '#1d4ed8', '#dc2626', '#0891b2', '#059669', '#b45309', '#6d28d9'];
    return colors[pid % colors.length];
  };

  const { team_stats: ts, match_context: mc, insights, season_stats: ss } = data || {};

  if (loading) {
    return (
      <div className="surface-muted p-12 text-center">
        <Loader2 className="mx-auto h-6 w-6 animate-spin text-brand-600" />
        <p className="mt-3 text-sm text-slate-600">Loading squad overview...</p>
      </div>
    );
  }
  if (error) return <ErrorAlert message={error} onRetry={() => fetchData()} />;
  if (!data) return <ErrorAlert message="No squad data available" />;

  return (
    <div className="space-y-5">

      {/* ── Match Banner + Selector ── */}
      {mc && (
        <div className="surface overflow-hidden">
          <div className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-wrap items-center gap-4">
              <div>
                <span className="text-2xl font-black tracking-widest text-slate-900">
                  {mc.home_team || 'Home'}
                </span>
                <span className="mx-3 text-2xl font-black text-brand-600">
                  {mc.home_score} — {mc.away_score}
                </span>
                <span className="text-2xl font-black text-slate-900">
                  {mc.away_team || 'Away'}
                </span>
              </div>
              <div className="hidden h-10 w-px bg-slate-200 sm:block" />
              <div className="flex gap-4 text-xs text-slate-500">
                {mc.match_date && <span>{mc.match_date}</span>}
                {mc.match_week && <span>Week {mc.match_week}</span>}
                <span className="font-mono text-brand-600">ID {mc.match_id}</span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-semibold text-slate-500">Match</span>
              <select
                value={selectedSquadMatchId || ''}
                onChange={(e) => handleMatchChange(Number(e.target.value))}
                className="field text-xs py-1.5 w-52"
                aria-label="Select match"
              >
                {(data?.available_matches || []).map((m) => (
                  <option key={m.match_id} value={m.match_id}>
                    W{m.match_week} — {m.home_team} {m.home_score}-{m.away_score} {m.away_team}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      )}

      {/* ── KPI Strip ── */}
      {ts && (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-8">
          {KPI_CONFIG.map((k) => {
            const val = ts[k.key];
            return (
              <div key={k.key} className={`surface p-3 border-t-2 ${KPI_BAR_COLORS[k.color] || 'from-slate-400'}`}>
                <div className="text-lg font-black font-mono text-slate-900">{formatKpi(k.key, val, ts)}</div>
                <div className="text-[10px] font-medium text-slate-500 mt-0.5">{k.label}</div>
                {k.badge && ts && (
                  <div className="text-[10px] font-mono text-slate-400 mt-0.5">{k.badge(ts)}</div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* ── AI Insights ── */}
      {insights && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {insights.top_performer && (
            <div className="surface p-4 border-l-4 border-l-emerald-500">
              <div className="flex items-center gap-2 mb-1">
                <Award className="h-4 w-4 text-emerald-500" />
                <span className="text-xs font-bold text-slate-700">Top Performer</span>
              </div>
              <p className="text-xs text-slate-500 leading-relaxed">
                {insights.top_performer.player_name} leads this match with a score of {insights.top_performer.score}.
              </p>
              <div className="mt-1 font-mono text-lg font-black text-emerald-600">
                {insights.top_performer.score} / 10
              </div>
            </div>
          )}
          {insights.most_improved && (
            <div className="surface p-4 border-l-4 border-l-blue-500">
              <div className="flex items-center gap-2 mb-1">
                <TrendingUp className="h-4 w-4 text-blue-500" />
                <span className="text-xs font-bold text-slate-700">Improved vs Last Match</span>
              </div>
              <p className="text-xs text-slate-500 leading-relaxed">
                {insights.most_improved.player_name} improved by +{insights.most_improved.delta} vs recent average.
              </p>
              <div className="mt-1 font-mono text-lg font-black text-blue-600">
                +{insights.most_improved.delta} pts
              </div>
            </div>
          )}
          {insights.declining && (
            <div className="surface p-4 border-l-4 border-l-amber-500">
              <div className="flex items-center gap-2 mb-1">
                <TrendingDown className="h-4 w-4 text-amber-500" />
                <span className="text-xs font-bold text-slate-700">Declining Player</span>
              </div>
              <p className="text-xs text-slate-500 leading-relaxed">
                {insights.declining.player_name} shows a {insights.declining.delta} drop vs recent average.
              </p>
              <div className="mt-1 font-mono text-lg font-black text-amber-600">
                {insights.declining.delta} trend
              </div>
            </div>
          )}
          <div className="surface p-4 border-l-4 border-l-red-500">
            <div className="flex items-center gap-2 mb-1">
              <AlertTriangle className="h-4 w-4 text-red-500" />
              <span className="text-xs font-bold text-slate-700">Declining Players</span>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">
              {insights.below_baseline_count || 0} player{(insights.below_baseline_count || 0) !== 1 ? 's' : ''} trending downward.
            </p>
            <div className="mt-1 font-mono text-lg font-black text-red-600">
              {insights.below_baseline_count || 0} player{(insights.below_baseline_count || 0) !== 1 ? 's' : ''}
            </div>
          </div>
        </div>
      )}

      {/* ── Filters ── */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative">
          <Search className="pointer-events-none absolute left-2.5 top-2 h-3.5 w-3.5 text-slate-400" />
          <input
            type="search"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="field w-44 pl-8 text-xs"
            placeholder="Search player..."
          />
        </div>
        <div className="h-5 w-px bg-slate-200" />
        {POS_GROUPS.map((g) => (
          <button
            key={g}
            onClick={() => setPosFilter(g)}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
              posFilter === g
                ? 'bg-brand-600 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            {POS_LABELS[g]}
          </button>
        ))}
        <div className="h-5 w-px bg-slate-200" />
        <button
          onClick={() => setTrendFilter(trendFilter === 'up' ? 'all' : 'up')}
          className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition inline-flex items-center gap-1 ${
            trendFilter === 'up'
              ? 'bg-emerald-100 text-emerald-700'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          <TrendingUp className="h-3 w-3" /> Improving
        </button>
        <button
          onClick={() => setTrendFilter(trendFilter === 'dn' ? 'all' : 'dn')}
          className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition inline-flex items-center gap-1 ${
            trendFilter === 'dn'
              ? 'bg-red-100 text-red-700'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          <TrendingDown className="h-3 w-3" /> Declining
        </button>
        <div className="ml-auto text-xs text-slate-500">
          {filteredPlayers.length} player{filteredPlayers.length !== 1 ? 's' : ''}
        </div>
      </div>

      {/* ── Squad Table ── */}
      <div className="surface overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50">
              <th className="sticky left-0 z-10 bg-slate-50 px-3 py-2.5 text-left font-bold text-slate-600 cursor-pointer select-none whitespace-nowrap" style={{ minWidth: 160 }} onClick={() => toggleSort('player_name')}>
                Player {sortIcon('player_name')}
              </th>
              <th className="px-3 py-2.5 text-left font-bold text-slate-600 cursor-pointer select-none whitespace-nowrap" onClick={() => toggleSort('position_group')}>
                Pos {sortIcon('position_group')}
              </th>
              <th className="px-3 py-2.5 text-left font-bold text-slate-600 cursor-pointer select-none whitespace-nowrap" onClick={() => toggleSort('overall_score')}>
                ML Score {sortIcon('overall_score')}
              </th>
              <th className="px-3 py-2.5 text-left font-bold text-slate-600 cursor-pointer select-none whitespace-nowrap" onClick={() => toggleSort('position_fit_score')}>
                Fit {sortIcon('position_fit_score')}
              </th>
              <th className="px-3 py-2.5 text-left font-bold text-slate-600 cursor-pointer select-none whitespace-nowrap" onClick={() => toggleSort('performance_trend')}>
                Trend {sortIcon('performance_trend')}
              </th>
              <th className="px-3 py-2.5 text-left font-bold text-slate-600 cursor-pointer select-none">Passing</th>
              <th className="px-3 py-2.5 text-left font-bold text-slate-600 cursor-pointer select-none">Shooting</th>
              <th className="px-3 py-2.5 text-left font-bold text-slate-600 cursor-pointer select-none">Positioning</th>
              <th className="px-3 py-2.5 text-left font-bold text-slate-600 cursor-pointer select-none">Pressing</th>
              <th className="px-3 py-2.5 text-left font-bold text-slate-600 cursor-pointer select-none">Movement</th>
              <th className="px-3 py-2.5 text-left font-bold text-slate-600 cursor-pointer select-none whitespace-nowrap" onClick={() => toggleSort('vaep_rating')}>
                VAEP {sortIcon('vaep_rating')}
              </th>
              <th className="px-3 py-2.5 text-left font-bold text-slate-600 cursor-pointer select-none whitespace-nowrap" onClick={() => toggleSort('total_xg')}>
                xG {sortIcon('total_xg')}
              </th>
              <th className="px-3 py-2.5 text-left font-bold text-slate-600 cursor-pointer select-none whitespace-nowrap">Pass%</th>
              <th className="px-3 py-2.5 text-left font-bold text-slate-600 cursor-pointer select-none whitespace-nowrap">Drib%</th>
              <th className="px-3 py-2.5 text-left font-bold text-slate-600 cursor-pointer select-none">Cluster</th>
              <th className="px-3 py-2.5 text-left font-bold text-slate-600 cursor-pointer select-none whitespace-nowrap" style={{ minWidth: 70 }}>Last 5</th>
            </tr>
          </thead>
          <tbody>
            {['FW', 'MF', 'DF', 'GK'].map((grp) => {
              const items = groupedPlayers[grp] || [];
              if (!items.length) return null;
              return (
                <React.Fragment key={grp}>
                  <tr className="border-b border-slate-100">
                    <td
                      colSpan={16}
                      className={`px-3 py-1.5 text-[10px] font-black uppercase tracking-wider ${POS_COLORS[grp] || 'text-slate-500'} bg-slate-50`}
                    >
                      {POS_LABELS[grp]} ({items.length})
                    </td>
                  </tr>
                  {items.map((p) => (
                    <tr
                      key={p.player_id}
                      className="border-b border-slate-100 cursor-pointer hover:bg-slate-50 transition"
                      onClick={() => openPlayerDashboard(p.player_name, p.player_id, selectedSquadMatchId)}
                    >
                      <td className="sticky left-0 z-10 bg-white px-3 py-2 hover:bg-slate-50">
                        <div className="flex items-center gap-2.5">
                          <div
                            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[9px] font-black"
                            style={{ background: `${playerColor(p.player_id)}22`, color: playerColor(p.player_id), border: `1.5px solid ${playerColor(p.player_id)}44` }}
                          >
                            {p.player_name?.split(' ').pop()?.charAt(0) || p.player_name?.charAt(0) || '?'}
                          </div>
                          <div className="min-w-0">
                            <div className="truncate text-xs font-bold text-slate-900">{p.player_name}</div>
                            <div className="text-[10px] text-slate-500">{p.position_label}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-3 py-2">
                        <span className={`inline-block rounded px-1.5 py-0.5 text-[9px] font-black ${POS_BG_COLORS[grp] || ''} ${POS_COLORS[grp] || ''}`}>
                          {grp}
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex items-center gap-2">
                          <span className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-black font-mono ${
                            p.overall_score >= 8 ? 'bg-emerald-100 text-emerald-700' :
                            p.overall_score >= 7 ? 'bg-blue-100 text-blue-700' :
                            p.overall_score >= 6 ? 'bg-amber-100 text-amber-700' :
                            p.overall_score >= 5 ? 'bg-orange-100 text-orange-700' :
                            'bg-red-100 text-red-700'
                          }`}>
                            {p.overall_score?.toFixed(1) || '—'}
                          </span>
                          <div className="h-1.5 w-12 rounded-full bg-slate-200 overflow-hidden">
                            <div
                              className="h-full rounded-full"
                              style={{ width: `${(p.overall_score || 0) * 10}%`, background: p.overall_score >= 7 ? '#22c55e' : p.overall_score >= 6 ? '#f59e0b' : '#ef4444' }}
                            />
                          </div>
                        </div>
                      </td>
                      <td className="px-3 py-2 font-mono text-xs font-bold" style={{ color: p.position_fit_score >= 7 ? '#22c55e' : p.position_fit_score >= 5 ? '#f59e0b' : '#ef4444' }}>
                        {p.position_fit_score?.toFixed(1) || '—'}
                      </td>
                      <td className="px-3 py-2">
                        <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold font-mono ${
                          p.performance_trend === 'Improving' ? 'bg-emerald-100 text-emerald-700' :
                          p.performance_trend === 'Declining' ? 'bg-red-100 text-red-700' :
                          'bg-slate-100 text-slate-600'
                        }`}>
                          {trendIcon(p.performance_trend)} {p.trend_value > 0 ? '+' : ''}{p.trend_value?.toFixed(1)}
                        </span>
                      </td>
                      {['passing', 'shooting', 'positioning', 'pressing', 'movement'].map((dim) => (
                        <td key={dim} className="px-3 py-2">
                          <div className="flex items-center gap-1.5">
                            <span className={`text-[10px] font-bold font-mono ${DIM_COLORS[dim].text}`}>
                              {p.scores?.[dim]?.toFixed(1) || '—'}
                            </span>
                            <div className="h-1 w-10 rounded-full bg-slate-200 overflow-hidden">
                              <div
                                className="h-full rounded-full"
                                style={{ width: `${(p.scores?.[dim] || 0) * 10}%`, background: DIM_COLORS[dim].bar }}
                              />
                            </div>
                          </div>
                        </td>
                      ))}
                      <td className="px-3 py-2 font-mono text-xs font-bold" style={{ color: p.vaep_rating >= 1.5 ? '#22c55e' : p.vaep_rating >= 0.8 ? '#3b82f6' : '#f59e0b' }}>
                        {p.vaep_rating?.toFixed(2) || '—'}
                      </td>
                      <td className="px-3 py-2">
                        <span className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-mono font-bold ${
                          p.total_xg >= 0.5 ? 'bg-emerald-100 text-emerald-700' :
                          p.total_xg >= 0.1 ? 'bg-amber-100 text-amber-700' :
                          'bg-slate-100 text-slate-500'
                        }`}>
                          {p.total_xg?.toFixed(2) || '—'}
                        </span>
                      </td>
                      <td className="px-3 py-2 font-mono text-xs text-cyan-600">{p.pass_accuracy?.toFixed(1) || '—'}%</td>
                      <td className="px-3 py-2 font-mono text-xs text-purple-600">{p.dribble_success_rate?.toFixed(1) || '—'}%</td>
                      <td className="px-3 py-2">
                        <span className={`inline-block rounded px-1.5 py-0.5 text-[9px] font-bold font-mono ${
                          p.player_cluster === 'creator' ? 'bg-blue-500/10 text-blue-600' :
                          p.player_cluster === 'presser' ? 'bg-red-500/10 text-red-600' :
                          p.player_cluster === 'engine' ? 'bg-green-500/10 text-green-600' :
                          p.player_cluster === 'anchor' ? 'bg-purple-500/10 text-purple-600' :
                          p.player_cluster === 'dribbler' ? 'bg-orange-500/10 text-orange-600' :
                          p.player_cluster === 'stopper' ? 'bg-amber-500/10 text-amber-600' :
                          'bg-slate-100 text-slate-500'
                        }`}>
                          {p.player_cluster?.toUpperCase() || '—'}
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        {p.last_5_scores?.length > 0 ? (
                          <div className="flex items-end gap-px h-5">
                            {p.last_5_scores.map((s, i) => {
                              const max = Math.max(...p.last_5_scores);
                              const h = Math.round((s / (max || 1)) * 18) + 2;
                              return (
                                <div
                                  key={i}
                                  className="w-[5px] rounded-sm"
                                  style={{ height: h, background: s >= (p.last_5_scores[i - 1] || s) ? '#22c55e' : '#ef4444', opacity: 0.6 + (i / p.last_5_scores.length) * 0.4 }}
                                  title={`${s.toFixed(1)}`}
                                />
                              );
                            })}
                          </div>
                        ) : <span className="text-slate-400">—</span>}
                      </td>
                    </tr>
                  ))}
                </React.Fragment>
              );
            })}
            {filteredPlayers.length === 0 && (
              <tr>
                <td colSpan={16} className="px-3 py-8 text-center text-sm text-slate-500">
                  No players match the current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* ── Bottom Grid: Benchmarks + Season Overview ── */}
      <TeamInfoCard ts={ts} matchContext={mc} seasonStats={ss} insights={insights} />

    </div>
  );
};

const TeamInfoCard = ({ ts, matchContext: mc, seasonStats: ss, insights }) => (
  <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
    {/* Benchmarks */}
    <div className="surface">
      <div className="ch border-b border-slate-200 px-4 py-3">
        <span className="text-sm font-bold text-slate-900">Team Performance</span>
        {mc && <span className="text-xs text-slate-500">Match {mc.match_id}</span>}
      </div>
      <div className="p-4 space-y-4">
        {[
          { label: 'Squad Avg Score', val: ts?.avg_overall_score, max: 10, color: '#22c55e' },
          { label: 'Pass Accuracy', val: ts?.pass_accuracy, max: 100, suffix: '%', color: '#3b82f6' },
          { label: 'Team xG', val: ts?.total_xg, max: 5, color: '#f59e0b' },
          { label: 'Shots on Target', val: ts?.shots_on_target, max: Math.max(ts?.shots_on_target || 1, 1), color: '#ef4444' },
          { label: 'Dribble Success', val: ts?.dribble_success_pct, max: 100, suffix: '%', color: '#a855f7' },
          { label: 'Possession', val: ts?.possession_pct, max: 100, suffix: '%', color: '#06b6d4' },
        ].map((row) => (
          <div key={row.label} className="flex items-center gap-3">
            <span className="text-[11px] text-slate-500 w-28 shrink-0">{row.label}</span>
            <div className="flex-1 h-1.5 rounded-full bg-slate-200 overflow-hidden">
              <div
                className="h-full rounded-full"
                style={{ width: `${Math.min((row.val || 0) / row.max * 100, 100)}%`, background: row.color }}
              />
            </div>
            <span className="font-mono text-[11px] font-bold text-slate-700 w-12 text-right">
              {row.val?.toFixed?.(1) ?? row.val ?? '—'}{row.suffix || ''}
            </span>
          </div>
        ))}
      </div>
    </div>

    {/* Season Overview */}
    <div className="surface">
      <div className="ch border-b border-slate-200 px-4 py-3">
        <span className="text-sm font-bold text-slate-900">Season Overview</span>
        <span className="text-xs text-slate-500">{ss?.weekly_averages?.length || '?'} matches</span>
      </div>
      <div className="p-4">
        {ss?.score_distribution && (
          <div className="mb-4">
            <div className="text-[11px] text-slate-500 mb-2">Score Distribution (0–10)</div>
            <div className="flex items-end gap-1 h-16">
              {Object.entries(ss.score_distribution).map(([label, pct]) => {
                const maxPct = Math.max(...Object.values(ss.score_distribution));
                const h = Math.round((pct / (maxPct || 1)) * 56);
                const barColor =
                  label === '3-5' ? '#ef4444' :
                  label === '5-6' ? '#f59e0b' :
                  label === '6-7' ? '#f97316' :
                  label === '7-8' ? '#3b82f6' :
                  '#22c55e';
                return (
                  <div key={label} className="flex-1 flex flex-col items-center gap-1">
                    <span className="text-[8px] text-slate-400">{pct}%</span>
                    <div className="w-full rounded-sm" style={{ height: h, background: barColor, opacity: 0.85 }} />
                  </div>
                );
              })}
            </div>
            <div className="flex justify-between text-[8px] text-slate-400 mt-1">
              <span>3.0</span><span>5.0</span><span>6.0</span><span>7.0</span><span>8.0</span><span>9.0</span>
            </div>
          </div>
        )}

        {ss?.weekly_averages && (
          <div className="mb-4 border-t border-slate-100 pt-3">
            <div className="text-[11px] text-slate-500 mb-2">Squad Score Over Season</div>
            <div className="flex items-end gap-px h-12">
              {ss.weekly_averages.map((avg, i) => {
                const maxA = Math.max(...ss.weekly_averages);
                const h = Math.round((avg / (maxA || 1)) * 44) + 2;
                const isLast = i === ss.weekly_averages.length - 1;
                return (
                  <div
                    key={i}
                    className="flex-1 rounded-sm"
                    style={{
                      height: h,
                      background: avg >= 7.5 ? '#22c55e' : avg >= 7 ? '#3b82f6' : avg >= 6.5 ? '#f59e0b' : '#ef4444',
                      opacity: isLast ? 1 : 0.6,
                    }}
                    title={`Week ${i + 1}: ${avg}`}
                  />
                );
              })}
            </div>
            <div className="flex justify-between text-[8px] text-slate-400 mt-1">
              <span>W1</span><span>W{Math.round((ss.weekly_averages.length || 1) / 2)}</span><span>W{ss.weekly_averages.length}</span>
            </div>
          </div>
        )}

        <div className="grid grid-cols-3 gap-3 border-t border-slate-100 pt-3">
          <div className="bg-slate-50 rounded-lg p-3 text-center">
            <div className="text-base font-black font-mono text-amber-600">{ss?.season_avg?.toFixed(1) || '—'}</div>
            <div className="text-[9px] text-slate-500 mt-0.5">SEASON AVG</div>
          </div>
          <div className="bg-slate-50 rounded-lg p-3 text-center">
            <div className="text-base font-black font-mono text-emerald-600">{ss?.best_match_avg?.toFixed(1) || '—'}</div>
            <div className="text-[9px] text-slate-500 mt-0.5">BEST MATCH</div>
          </div>
          <div className="bg-slate-50 rounded-lg p-3 text-center">
            <div className="text-base font-black font-mono text-red-600">{ss?.worst_match_avg?.toFixed(1) || '—'}</div>
            <div className="text-[9px] text-slate-500 mt-0.5">WORST MATCH</div>
          </div>
        </div>
      </div>
    </div>
  </div>
);

export default SquadOverview;
