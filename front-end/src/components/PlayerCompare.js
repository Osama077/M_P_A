import React, { useEffect, useState, useMemo, useCallback } from 'react';
import {
  Loader2, TrendingUp,
  Zap, Crosshair, Target
} from 'lucide-react';
import {
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  Tooltip, ResponsiveContainer
} from 'recharts';
import { PlayerAPI, CompareAPI } from '../api';
import ErrorAlert from './ErrorAlert';

const DIM_CONFIG = [
  { key: 'passing', label: 'Passing', color: '#3b82f6' },
  { key: 'shooting', label: 'Shooting', color: '#ef4444' },
  { key: 'positioning', label: 'Positioning', color: '#22c55e' },
  { key: 'pressing', label: 'Pressing', color: '#f97316' },
  { key: 'movement', label: 'Movement', color: '#a855f7' },
  { key: 'physical', label: 'Physical', color: '#f59e0b' },
  { key: 'behavioral', label: 'Behavioral', color: '#06b6d4' },
];

const P1_COLOR = '#3b82f6';
const P2_COLOR = '#22c55e';

function initials(name) {
  const parts = (name || '').split(' ');
  if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  return (name || '?')[0].toUpperCase();
}

function resultBadge(result) {
  if (!result) return '';
  if (result.startsWith('W')) return 'bg-emerald-500/10 text-emerald-500';
  if (result.startsWith('D')) return 'bg-amber-500/10 text-amber-500';
  if (result.startsWith('L')) return 'bg-red-500/10 text-red-500';
  return 'bg-slate-500/10 text-slate-500';
}

const INSIGHT_ICONS = {
  blue: <Zap className="w-3 h-3" />,
  green: <Target className="w-3 h-3" />,
  yellow: <TrendingUp className="w-3 h-3" />,
  red: <Crosshair className="w-3 h-3" />,
};

const INSIGHT_BG = {
  blue: 'bg-blue-500/10',
  green: 'bg-emerald-500/10',
  yellow: 'bg-amber-500/10',
  red: 'bg-red-500/10',
};

const INSIGHT_TEXT = {
  blue: 'text-blue-500',
  green: 'text-emerald-500',
  yellow: 'text-amber-500',
  red: 'text-red-500',
};

const PlayerCompare = () => {
  const [players, setPlayers] = useState([]);
  const [p1Id, setP1Id] = useState(null);
  const [p2Id, setP2Id] = useState(null);
  const [context, setContext] = useState('season');
  const [selectedMatchId, setSelectedMatchId] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [listLoading, setListLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch player list
  useEffect(() => {
    const fetchPlayers = async () => {
      try {
        const res = await PlayerAPI.getPlayerList();
        setPlayers(res.player_items || []);
      } catch (err) {
        setError(err.message);
      } finally {
        setListLoading(false);
      }
    };
    fetchPlayers();
  }, []);

  // Auto-set first two players when list loads
  useEffect(() => {
    if (players.length >= 2 && !p1Id && !p2Id) {
      setP1Id(players[0].player_id);
      setP2Id(players[1].player_id);
    }
  }, [players, p1Id, p2Id]);

  // Fetch comparison data
  const fetchComparison = useCallback(async (p1, p2, ctx, mid) => {
    if (!p1 || !p2 || p1 === p2) return;
    setLoading(true);
    setError(null);
    try {
      const res = await CompareAPI.getHeadToHead(p1, p2, ctx, ctx === 'match' ? mid : null);
      setData(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (p1Id && p2Id && p1Id !== p2Id) {
      fetchComparison(p1Id, p2Id, context, selectedMatchId);
    }
  }, [p1Id, p2Id, context, selectedMatchId, fetchComparison]);

  const p1 = data?.player1;
  const p2 = data?.player2;

  // Radar data
  const radarData = useMemo(() => {
    if (!p1 || !p2) return [];
    return DIM_CONFIG.map(dim => ({
      metric: dim.label,
      [p1.player_name]: p1.scores?.[dim.key] ?? 0,
      [p2.player_name]: p2.scores?.[dim.key] ?? 0,
    }));
  }, [p1, p2]);

  const availableMatches = data?.available_matches || [];

  // Context label
  const contextLabel = context === 'season' ? 'Season Average' : context === 'last5' ? 'Last 5 Avg' : 'Match';

  return (
    <div className="space-y-5">

      {/* ── Player Selectors ── */}
      <div className="flex flex-wrap items-center gap-3 p-3 bg-white rounded-xl border border-slate-200">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <span className="text-[10px] font-bold text-blue-600 uppercase tracking-wider">Player 1</span>
          <select
            value={p1Id || ''}
            onChange={(e) => setP1Id(Number(e.target.value))}
            className="field text-xs py-1.5 flex-1 border-blue-300"
          >
            {players.map(p => (
              <option key={p.player_id} value={p.player_id}>{p.player_name}</option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2 px-3">
          <span className="text-sm font-black text-slate-400">VS</span>
        </div>
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <span className="text-[10px] font-bold text-emerald-600 uppercase tracking-wider">Player 2</span>
          <select
            value={p2Id || ''}
            onChange={(e) => setP2Id(Number(e.target.value))}
            className="field text-xs py-1.5 flex-1 border-emerald-300"
          >
            {players.map(p => (
              <option key={p.player_id} value={p.player_id}>{p.player_name}</option>
            ))}
          </select>
        </div>
        <select
          value={context}
          onChange={(e) => setContext(e.target.value)}
          className="field text-xs py-1.5 w-36"
        >
          <option value="season">Season Average</option>
          <option value="last5">Last 5 Matches</option>
          <option value="match">Specific Match</option>
        </select>
        {context === 'match' && (
          <select
            value={selectedMatchId || ''}
            onChange={(e) => setSelectedMatchId(Number(e.target.value))}
            className="field text-xs py-1.5 w-52"
          >
            {availableMatches.map(m => (
              <option key={m.match_id} value={m.match_id}>{m.label}</option>
            ))}
          </select>
        )}
      </div>

      {listLoading && (
        <div className="surface-muted p-12 text-center">
          <Loader2 className="mx-auto h-5 w-5 animate-spin text-brand-600" />
          <p className="mt-2 text-sm text-slate-500">Loading players...</p>
        </div>
      )}

      {error && <ErrorAlert message={error} onRetry={() => fetchComparison(p1Id, p2Id, context, selectedMatchId)} />}

      {loading && !data && (
        <div className="surface-muted p-12 text-center">
          <Loader2 className="mx-auto h-6 w-6 animate-spin text-brand-600" />
          <p className="mt-3 text-sm text-slate-600">Loading comparison...</p>
        </div>
      )}

      {data && p1 && p2 && (
        <>
          {/* ── Compare Header Banner ── */}
          <div className="relative overflow-hidden rounded-xl border border-blue-500/20"
            style={{ background: 'linear-gradient(135deg, #040e1e, #07111f)' }}>
            <div className="absolute inset-0 pointer-events-none"
              style={{ background: 'repeating-linear-gradient(135deg, rgba(88,166,255,0.02) 0px, rgba(88,166,255,0.02) 1px, transparent 1px, transparent 28px)' }} />
            <div className="grid grid-cols-[1fr_auto_1fr] gap-0 relative z-10">
              {/* P1 */}
              <div className="p-4 md:p-5 border-r border-slate-700/50">
                <div className="flex items-center gap-3 mb-3">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full text-sm font-black border-2"
                    style={{ background: '#1a6be022', color: P1_COLOR, borderColor: '#1a6be044' }}>
                    {p1.initials || initials(p1.player_name)}
                  </div>
                  <div>
                    <div className="text-base font-black text-white">{p1.player_name}</div>
                    <div className="text-[10px] text-slate-400">{p1.position_group} · #{p1.player_id}</div>
                  </div>
                </div>
                <div className="flex gap-1.5 flex-wrap mb-3">
                  <span className="px-2 py-0.5 rounded-full text-[9px] font-bold"
                    style={{ background: '#ef444422', color: '#ef4444' }}>{p1.position_group}</span>
                  <span className="px-2 py-0.5 rounded-full text-[9px] font-bold"
                    style={{ background: '#3b82f622', color: '#3b82f6' }}>{p1.player_cluster}</span>
                </div>
                <div className="flex gap-4 flex-wrap">
                  <div className="text-center">
                    <div className="text-xl font-black font-mono" style={{ color: P1_COLOR }}>{p1.overall_score?.toFixed(1)}</div>
                    <div className="text-[8px] text-slate-500 uppercase tracking-wider">ML Avg</div>
                  </div>
                  <div className="text-center">
                    <div className="text-xl font-black font-mono text-amber-500">P{p1.percentile || 50}</div>
                    <div className="text-[8px] text-slate-500 uppercase tracking-wider">League %ile</div>
                  </div>
                  <div className="text-center">
                    <div className="text-xl font-black font-mono" style={{ color: p1.performance_trend === 'Improving' ? '#22c55e' : p1.performance_trend === 'Declining' ? '#ef4444' : '#94a3b8' }}>
                      {p1.performance_trend === 'Improving' ? '↑' : p1.performance_trend === 'Declining' ? '↓' : '→'} {p1.performance_trend === 'Improving' ? '+0.1' : p1.performance_trend === 'Declining' ? '-0.1' : '0.0'}
                    </div>
                    <div className="text-[8px] text-slate-500 uppercase tracking-wider">Trend</div>
                  </div>
                </div>
                {/* 7-dim scores P1 */}
                <div className="grid grid-cols-7 gap-1.5 mt-3">
                  {DIM_CONFIG.map(dim => {
                    const val = p1.scores?.[dim.key] || 0;
                    return (
                      <div key={dim.key} className="bg-[#161B2288] rounded-md p-1.5 text-center border border-[#30363D44]">
                        <div className="text-[11px] font-black font-mono" style={{ color: dim.color }}>{val.toFixed(1)}</div>
                        <div className="h-1 rounded-full overflow-hidden bg-slate-700 my-0.5">
                          <div className="h-full rounded-full" style={{ width: `${Math.min(val * 10, 100)}%`, background: dim.color }} />
                        </div>
                        <div className="text-[7px] text-slate-500">{dim.label.slice(0, 3)}</div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* VS Column */}
              <div className="flex flex-col items-center justify-center px-4 md:px-6 gap-2">
                <div className="text-lg font-black text-slate-600">VS</div>
                <div className="text-[9px] text-slate-600 text-center">{contextLabel}</div>
              </div>

              {/* P2 */}
              <div className="p-4 md:p-5 border-l border-slate-700/50">
                <div className="flex items-center gap-3 mb-3 justify-end">
                  <div className="text-right">
                    <div className="text-base font-black text-white">{p2.player_name}</div>
                    <div className="text-[10px] text-slate-400">{p2.position_group} · #{p2.player_id}</div>
                  </div>
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full text-sm font-black border-2"
                    style={{ background: '#22c55e22', color: P2_COLOR, borderColor: '#22c55e44' }}>
                    {p2.initials || initials(p2.player_name)}
                  </div>
                </div>
                <div className="flex gap-1.5 flex-wrap mb-3 justify-end">
                  <span className="px-2 py-0.5 rounded-full text-[9px] font-bold"
                    style={{ background: '#ef444422', color: '#ef4444' }}>{p2.position_group}</span>
                  <span className="px-2 py-0.5 rounded-full text-[9px] font-bold"
                    style={{ background: '#22c55e22', color: '#22c55e' }}>{p2.player_cluster}</span>
                </div>
                <div className="flex gap-4 flex-wrap justify-end">
                  <div className="text-center">
                    <div className="text-xl font-black font-mono" style={{ color: P2_COLOR }}>{p2.overall_score?.toFixed(1)}</div>
                    <div className="text-[8px] text-slate-500 uppercase tracking-wider">ML Avg</div>
                  </div>
                  <div className="text-center">
                    <div className="text-xl font-black font-mono text-emerald-500">P{p2.percentile || 50}</div>
                    <div className="text-[8px] text-slate-500 uppercase tracking-wider">League %ile</div>
                  </div>
                  <div className="text-center">
                    <div className="text-xl font-black font-mono" style={{ color: p2.performance_trend === 'Improving' ? '#22c55e' : p2.performance_trend === 'Declining' ? '#ef4444' : '#94a3b8' }}>
                      {p2.performance_trend === 'Improving' ? '↑' : p2.performance_trend === 'Declining' ? '↓' : '→'} {p2.performance_trend === 'Improving' ? '+0.1' : p2.performance_trend === 'Declining' ? '-0.1' : '0.0'}
                    </div>
                    <div className="text-[8px] text-slate-500 uppercase tracking-wider">Trend</div>
                  </div>
                </div>
                {/* 7-dim scores P2 */}
                <div className="grid grid-cols-7 gap-1.5 mt-3">
                  {DIM_CONFIG.map(dim => {
                    const val = p2.scores?.[dim.key] || 0;
                    return (
                      <div key={dim.key} className="bg-[#161B2288] rounded-md p-1.5 text-center border border-[#30363D44]">
                        <div className="text-[11px] font-black font-mono" style={{ color: dim.color }}>{val.toFixed(1)}</div>
                        <div className="h-1 rounded-full overflow-hidden bg-slate-700 my-0.5">
                          <div className="h-full rounded-full" style={{ width: `${Math.min(val * 10, 100)}%`, background: dim.color }} />
                        </div>
                        <div className="text-[7px] text-slate-500">{dim.label.slice(0, 3)}</div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>

          {/* ── H2H Bars + Radar + Insights ── */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4" style={{ alignItems: 'start' }}>

            {/* H2H Bars */}
            <div className="surface">
              <div className="ch border-b border-slate-200 px-4 py-3">
                <div className="flex items-center gap-2 text-xs">
                  <span className="font-bold text-blue-600">{p1.player_name.split(' ').pop()}</span>
                  <span className="text-sm font-bold text-slate-900">H2H</span>
                  <span className="font-bold text-emerald-600">{p2.player_name.split(' ').pop()}</span>
                </div>
                <span className="text-[10px] text-slate-500">{contextLabel}</span>
              </div>
              <div className="p-3 space-y-0">
                {(data.h2h_data || []).map((h, i) => {
                  const p1Pct = h.max > 0 ? (h.val1 / h.max) * 100 : 0;
                  const p2Pct = h.max > 0 ? (h.val2 / h.max) * 100 : 0;
                  return (
                    <div key={i} className="py-2 border-b border-slate-100 last:border-0">
                      <div className="text-[10px] text-slate-500 text-center mb-1.5">{h.label}</div>
                      <div className="grid grid-cols-[1fr_50px_1fr] gap-1.5 items-center">
                        <div className="flex items-center gap-1.5 justify-end">
                          {h.p1_wins && <div className="w-1.5 h-1.5 rounded-full bg-blue-500" />}
                          <span className={`font-mono text-[11px] font-bold text-right ${h.p1_wins ? 'text-blue-600' : 'text-slate-700'}`}>{h.formatted1}</span>
                          <div className="h-1.5 bg-slate-200 rounded-full overflow-hidden" style={{ width: 60 }}>
                            <div className="h-full rounded-full bg-blue-500" style={{ width: `${p1Pct}%` }} />
                          </div>
                        </div>
                        <div className="text-center text-[9px] text-slate-400">|</div>
                        <div className="flex items-center gap-1.5">
                          <div className="h-1.5 bg-slate-200 rounded-full overflow-hidden" style={{ width: 60 }}>
                            <div className="h-full rounded-full bg-emerald-500" style={{ width: `${p2Pct}%` }} />
                          </div>
                          <span className={`font-mono text-[11px] font-bold ${!h.p1_wins ? 'text-emerald-600' : 'text-slate-700'}`}>{h.formatted2}</span>
                          {!h.p1_wins && <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Radar */}
            <div className="surface">
              <div className="ch border-b border-slate-200 px-4 py-3">
                <span className="text-sm font-bold text-slate-900">Skill Radar</span>
                <div className="flex gap-3 text-[10px]">
                  <span><span className="text-blue-500">●</span> {p1.player_name.split(' ').pop()}</span>
                  <span><span className="text-emerald-500">●</span> {p2.player_name.split(' ').pop()}</span>
                </div>
              </div>
              <div className="p-2">
                {radarData.length > 0 && (
                  <ResponsiveContainer width="100%" height={280}>
                    <RadarChart data={radarData}>
                      <PolarGrid stroke="#e2e8f0" />
                      <PolarAngleAxis dataKey="metric" tick={{ fontSize: 9, fill: '#64748b' }} />
                      <PolarRadiusAxis angle={90} domain={[0, 10]} tick={{ fontSize: 8, fill: '#cbd5e1' }} tickCount={6} />
                      <Tooltip contentStyle={{ fontSize: 11, borderRadius: 8 }} />
                      <Radar dataKey={p1.player_name} stroke={P1_COLOR} fill={P1_COLOR} fillOpacity={0.08} strokeWidth={2} />
                      <Radar dataKey={p2.player_name} stroke={P2_COLOR} fill={P2_COLOR} fillOpacity={0.08} strokeWidth={2} />
                    </RadarChart>
                  </ResponsiveContainer>
                )}
              </div>
              <div className="grid grid-cols-2 gap-3 p-3 pt-0">
                <div className="bg-slate-50 rounded-lg p-2.5 text-center border border-blue-200">
                  <div className="text-base font-black font-mono text-blue-600">{p1.overall_score?.toFixed(1)}</div>
                  <div className="text-[9px] text-slate-500">{p1.player_name.split(' ').pop()} Avg</div>
                </div>
                <div className="bg-slate-50 rounded-lg p-2.5 text-center border border-emerald-200">
                  <div className="text-base font-black font-mono text-emerald-600">{p2.overall_score?.toFixed(1)}</div>
                  <div className="text-[9px] text-slate-500">{p2.player_name.split(' ').pop()} Avg</div>
                </div>
              </div>
            </div>

            {/* Insights */}
            <div className="flex flex-col gap-2.5">
              {(data.insights || []).map((ins, i) => (
                <div key={i} className="bg-white rounded-lg p-3 border border-slate-200"
                  style={{ borderLeftColor: ins.color, borderLeftWidth: 3 }}>
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className={`w-4 h-4 rounded flex items-center justify-center text-[9px] ${INSIGHT_BG[ins.type] || 'bg-blue-500/10'} ${INSIGHT_TEXT[ins.type] || 'text-blue-500'}`}>
                      {INSIGHT_ICONS[ins.type] || '★'}
                    </span>
                    <span className="text-[11px] font-bold text-slate-900">{ins.title}</span>
                  </div>
                  <p className="text-[10px] text-slate-600 leading-relaxed">{ins.body}</p>
                  <div className="font-mono text-sm font-black mt-1.5" style={{ color: ins.color }}>{ins.metric_label}</div>
                </div>
              ))}
            </div>
          </div>

          {/* ── Full Statistical Breakdown ── */}
          <div className="flex items-center gap-2 mb-2">
            <div className="w-1.5 h-1.5 rounded-full bg-purple-500" />
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Full Statistical Breakdown</span>
            <div className="flex-1 h-px bg-slate-200" />
          </div>
          <div className="surface overflow-hidden">
            <div className="ch border-b border-slate-200 px-4 py-3">
              <div className="flex items-center gap-3 text-xs">
                <span className="flex items-center gap-1.5 font-bold text-blue-600">
                  <div className="w-2 h-2 rounded-full bg-blue-500" />{p1.player_name.split(' ').pop()}
                </span>
                <span className="text-sm font-bold text-slate-900">Season Stat Comparison</span>
                <span className="flex items-center gap-1.5 font-bold text-emerald-600">
                  <div className="w-2 h-2 rounded-full bg-emerald-500" />{p2.player_name.split(' ').pop()}
                </span>
              </div>
              <span className="text-[10px] text-slate-500">{contextLabel}</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50">
                    <th className="px-4 py-2.5 text-left font-bold text-slate-600 w-44">Metric</th>
                    <th className="px-4 py-2.5 text-center font-bold text-blue-600">{p1.player_name.split(' ').pop()}</th>
                    <th className="px-4 py-2.5 text-center font-bold text-slate-500">Winner</th>
                    <th className="px-4 py-2.5 text-center font-bold text-emerald-600">{p2.player_name.split(' ').pop()}</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    ['ML Overall Score', p1.overall_score, p2.overall_score, (v) => v?.toFixed(1)],
                    ['Passing Score', p1.scores?.passing, p2.scores?.passing, (v) => v?.toFixed(1)],
                    ['Shooting Score', p1.scores?.shooting, p2.scores?.shooting, (v) => v?.toFixed(1)],
                    ['Positioning Score', p1.scores?.positioning, p2.scores?.positioning, (v) => v?.toFixed(1)],
                    ['Pressing Score', p1.scores?.pressing, p2.scores?.pressing, (v) => v?.toFixed(1)],
                    ['Movement Score', p1.scores?.movement, p2.scores?.movement, (v) => v?.toFixed(1)],
                    ['Physical Score', p1.scores?.physical, p2.scores?.physical, (v) => v?.toFixed(1)],
                    ['Behavioral Score', p1.scores?.behavioral, p2.scores?.behavioral, (v) => v?.toFixed(1)],
                    ['VAEP Rating', p1.vaep_rating, p2.vaep_rating, (v) => v?.toFixed(2)],
                    ['Pass Accuracy', p1.stats?.pass_accuracy, p2.stats?.pass_accuracy, (v) => v?.toFixed(1) + '%'],
                    ['Progressive Passes', p1.stats?.progressive_passes, p2.stats?.progressive_passes, (v) => v?.toFixed(1)],
                    ['Total xG', p1.stats?.total_xg, p2.stats?.total_xg, (v) => v?.toFixed(2)],
                    ['xG per Shot', p1.stats?.xg_per_shot, p2.stats?.xg_per_shot, (v) => v?.toFixed(2)],
                    ['Total Shots', p1.stats?.total_shots, p2.stats?.total_shots, (v) => v?.toFixed(1)],
                    ['Dribble Success%', p1.stats?.dribble_success_rate, p2.stats?.dribble_success_rate, (v) => v?.toFixed(1) + '%'],
                    ['Total Pressures', p1.stats?.total_pressures, p2.stats?.total_pressures, (v) => v?.toFixed(1)],
                    ['Distance Covered (km)', p1.stats?.distance_covered ? (p1.stats.distance_covered / 1000).toFixed(1) + 'km' : 'N/A', p2.stats?.distance_covered ? (p2.stats.distance_covered / 1000).toFixed(1) + 'km' : 'N/A', null],
                    ['Ball Retention%', p1.stats?.ball_retention_rate, p2.stats?.ball_retention_rate, (v) => v?.toFixed(1) + '%'],
                    ['Fouls Won', p1.stats?.fouls_won, p2.stats?.fouls_won, (v) => v?.toFixed(1)],
                  ].filter(r => r[1] !== undefined || r[2] !== undefined).map((row, i) => {
                    const [label, v1Raw, v2Raw, fmt] = row;
                    const v1 = typeof v1Raw === 'number' ? v1Raw : (typeof v1Raw === 'string' ? v1Raw : null);
                    const v2 = typeof v2Raw === 'number' ? v2Raw : (typeof v2Raw === 'string' ? v2Raw : null);
                    const v1Num = typeof v1 === 'number' ? v1 : null;
                    const v2Num = typeof v2 === 'number' ? v2 : null;
                    const p1Wins = v1Num !== null && v2Num !== null ? v1Num >= v2Num : null;
                    return (
                      <tr key={i} className="border-b border-slate-100 hover:bg-slate-50">
                        <td className="px-4 py-2.5 text-slate-600 font-medium">{label}</td>
                        <td className={`px-4 py-2.5 text-center font-mono text-sm font-black ${p1Wins === null ? 'text-slate-700' : p1Wins ? 'text-blue-600' : 'text-slate-700'}`}>
                          {fmt && v1Num !== null ? fmt(v1Num) : (v1 ?? '—')}
                        </td>
                        <td className="px-4 py-2.5 text-center">
                          {p1Wins !== null && (
                            <div className={`w-2 h-2 rounded-full mx-auto ${p1Wins ? 'bg-blue-500' : 'bg-emerald-500'}`} />
                          )}
                        </td>
                        <td className={`px-4 py-2.5 text-center font-mono text-sm font-black ${p1Wins === null ? 'text-slate-700' : !p1Wins ? 'text-emerald-600' : 'text-slate-700'}`}>
                          {fmt && v2Num !== null ? fmt(v2Num) : (v2 ?? '—')}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* ── Parallel Match Log ── */}
          <div className="flex items-center gap-2 mb-2">
            <div className="w-1.5 h-1.5 rounded-full bg-cyan-500" />
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Parallel Match Log</span>
            <div className="flex-1 h-px bg-slate-200" />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="surface overflow-hidden">
              <div className="ch border-b border-slate-200 px-4 py-3">
                <span className="text-sm font-bold text-blue-600">{p1.player_name.split(' ').pop()} — Match by Match</span>
              </div>
              <div className="overflow-y-auto" style={{ maxHeight: 360 }}>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50 sticky top-0">
                      <th className="px-3 py-2 text-left font-bold text-slate-600">Week</th>
                      <th className="px-3 py-2 text-left font-bold text-slate-600">Opponent</th>
                      <th className="px-3 py-2 text-left font-bold text-slate-600">Result</th>
                      <th className="px-3 py-2 text-left font-bold text-slate-600">Score</th>
                      <th className="px-3 py-2 text-left font-bold text-slate-600">Trend</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(data.shared_matches || []).map((m, i) => {
                      const prev = i < (data.shared_matches || []).length - 1 ? (data.shared_matches || [])[i + 1].p1_score : m.p1_score;
                      const diff = (m.p1_score || 0) - (prev || 0);
                      const sc = m.p1_score >= 7.5 ? '#22c55e' : m.p1_score >= 7 ? '#3b82f6' : m.p1_score >= 6 ? '#f59e0b' : '#ef4444';
                      const tc = diff > 0 ? '#22c55e' : diff < 0 ? '#ef4444' : '#94a3b8';
                      return (
                        <tr key={m.match_id || i} className="border-b border-slate-100 hover:bg-slate-50">
                          <td className="px-3 py-2 font-mono text-[10px] text-slate-500">W{m.match_week}</td>
                          <td className="px-3 py-2 font-semibold text-slate-900">{m.opponent}</td>
                          <td className="px-3 py-2"><span className={`inline-block px-1.5 py-0.5 rounded-full text-[9px] font-bold font-mono ${resultBadge(m.result)}`}>{m.result}</span></td>
                          <td className="px-3 py-2">
                            <div className="flex items-center gap-1.5">
                              <span className="font-mono text-sm font-black" style={{ color: sc }}>{m.p1_score?.toFixed(1)}</span>
                              <div className="w-6 h-1 bg-slate-200 rounded-full overflow-hidden">
                                <div className="h-full rounded-full" style={{ width: `${Math.min((m.p1_score || 0) * 10, 100)}%`, background: sc }} />
                              </div>
                            </div>
                          </td>
                          <td className="px-3 py-2 font-mono text-[10px]" style={{ color: tc }}>
                            {diff > 0 ? '↑' : diff < 0 ? '↓' : '→'}{diff > 0 ? '+' : ''}{diff.toFixed(1)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
            <div className="surface overflow-hidden">
              <div className="ch border-b border-slate-200 px-4 py-3">
                <span className="text-sm font-bold text-emerald-600">{p2.player_name.split(' ').pop()} — Match by Match</span>
              </div>
              <div className="overflow-y-auto" style={{ maxHeight: 360 }}>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50 sticky top-0">
                      <th className="px-3 py-2 text-left font-bold text-slate-600">Week</th>
                      <th className="px-3 py-2 text-left font-bold text-slate-600">Opponent</th>
                      <th className="px-3 py-2 text-left font-bold text-slate-600">Result</th>
                      <th className="px-3 py-2 text-left font-bold text-slate-600">Score</th>
                      <th className="px-3 py-2 text-left font-bold text-slate-600">Trend</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(data.shared_matches || []).map((m, i) => {
                      const prev = i < (data.shared_matches || []).length - 1 ? (data.shared_matches || [])[i + 1].p2_score : m.p2_score;
                      const diff = (m.p2_score || 0) - (prev || 0);
                      const sc = m.p2_score >= 7.5 ? '#22c55e' : m.p2_score >= 7 ? '#3b82f6' : m.p2_score >= 6 ? '#f59e0b' : '#ef4444';
                      const tc = diff > 0 ? '#22c55e' : diff < 0 ? '#ef4444' : '#94a3b8';
                      return (
                        <tr key={m.match_id || i} className="border-b border-slate-100 hover:bg-slate-50">
                          <td className="px-3 py-2 font-mono text-[10px] text-slate-500">W{m.match_week}</td>
                          <td className="px-3 py-2 font-semibold text-slate-900">{m.opponent}</td>
                          <td className="px-3 py-2"><span className={`inline-block px-1.5 py-0.5 rounded-full text-[9px] font-bold font-mono ${resultBadge(m.result)}`}>{m.result}</span></td>
                          <td className="px-3 py-2">
                            <div className="flex items-center gap-1.5">
                              <span className="font-mono text-sm font-black" style={{ color: sc }}>{m.p2_score?.toFixed(1)}</span>
                              <div className="w-6 h-1 bg-slate-200 rounded-full overflow-hidden">
                                <div className="h-full rounded-full" style={{ width: `${Math.min((m.p2_score || 0) * 10, 100)}%`, background: sc }} />
                              </div>
                            </div>
                          </td>
                          <td className="px-3 py-2 font-mono text-[10px]" style={{ color: tc }}>
                            {diff > 0 ? '↑' : diff < 0 ? '↓' : '→'}{diff > 0 ? '+' : ''}{diff.toFixed(1)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default PlayerCompare;