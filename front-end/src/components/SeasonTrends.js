import React, { useEffect, useState } from 'react';
import {
  Loader2, TrendingUp, TrendingDown, Minus
} from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ScatterChart, Scatter, Cell, ReferenceLine
} from 'recharts';
import { SeasonTrendsAPI } from '../api';
import { useAppContext } from '../context/AppContext';
import ErrorAlert from './ErrorAlert';

const COLORS = ['#f59e0b', '#22c55e', '#ff8c42', '#a855f7', '#3b82f6', '#06b6d4', '#84cc16', '#ef4444', '#1d4ed8', '#6d28d9'];
const TREND_ICONS = { up: TrendingUp, dn: TrendingDown, st: Minus };

function heatColor(v) {
  if (v >= 7.8) return '#00d084';
  if (v >= 7.4) return '#2ecc71';
  if (v >= 7.0) return '#3498db';
  if (v >= 6.6) return '#f39c12';
  if (v >= 6.2) return '#e67e22';
  return '#e74c3c';
}

const SeasonTrends = () => {
  const { selectedSeason } = useAppContext();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    SeasonTrendsAPI.getSeasonTrends(selectedSeason)
      .then(d => { if (!cancelled) { setData(d); setLoading(false); } })
      .catch(e => { if (!cancelled) { setError(e.message); setLoading(false); } });
    return () => { cancelled = true; };
  }, [selectedSeason]);

  if (loading) return <div className="flex items-center justify-center py-20"><Loader2 className="h-8 w-8 animate-spin text-brand-600" /></div>;
  if (error) return <ErrorAlert message={error} />;
  if (!data) return <ErrorAlert message="No season trends data available" />;

  const { summary, score_evolution, form_cards, heatmap, rankings, metric_trends, scatter } = data;

  const statCards = [
    { label: 'Squad Avg Score', value: summary.squad_avg_score?.toFixed(1), sub: `${summary.total_matches || 0} matches`, color: 'text-emerald-600', border: 'border-l-emerald-500' },
    { label: 'Avg Pass Accuracy', value: summary.avg_pass_accuracy ? `${summary.avg_pass_accuracy.toFixed(1)}%` : '—', sub: 'Season average', color: 'text-blue-600', border: 'border-l-blue-500' },
    { label: 'Total Goals', value: summary.total_goals_scored ?? '—', sub: summary.goals_per_match ? `${summary.goals_per_match.toFixed(1)}/match` : '', color: 'text-red-600', border: 'border-l-red-500' },
    { label: 'Team xG (Season)', value: summary.team_xg?.toFixed(1), sub: 'Expected goals', color: 'text-amber-600', border: 'border-l-amber-500' },
    { label: 'Total Dribbles', value: summary.total_dribbles ?? '—', sub: summary.dribble_success_rate ? `${summary.dribble_success_rate.toFixed(1)}% success` : '', color: 'text-purple-600', border: 'border-l-purple-500' },
  ];

  const scoreEvoData = score_evolution?.match_weeks?.map((w, i) => {
    const row = { week: `W${w}` };
    score_evolution.players?.forEach(p => { row[p.player_name] = p.scores?.[i]; });
    row['Squad Avg'] = score_evolution.squad_avg?.[i];
    return row;
  }) || [];

  const formCardGrid = form_cards?.map(p => {
    const TrendIcon = TREND_ICONS[p.trend] || Minus;
    const maxS = Math.max(...(p.last_10_scores || []), 1);
    const scoreColor = p.avg_score >= 7.5 ? 'text-emerald-600' : p.avg_score >= 7.0 ? 'text-blue-600' : p.avg_score >= 6.5 ? 'text-amber-600' : 'text-red-500';
    return (
      <div key={p.player_id} className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0 bg-sky-100 text-sky-700 border border-sky-200">
            {p.initials}
          </div>
          <div className="min-w-0">
            <div className="text-xs font-bold text-slate-800 truncate">{p.player_name}</div>
            <div className="text-[10px] text-slate-500">{p.position_group}</div>
          </div>
          <span className={`ml-auto font-mono font-black text-sm ${scoreColor}`}>{p.avg_score.toFixed(1)}</span>
        </div>
        <div className="flex gap-[2px] items-end h-7">
          {(p.last_10_scores || []).map((s, j) => {
            const h = Math.max(Math.round((s / maxS) * 26), 4);
            const c = j === p.last_10_scores.length - 1 ? '#22c55e' : s >= 7.5 ? '#22c55e' : s >= 7 ? '#3b82f6' : s >= 6.5 ? '#f59e0b' : '#ef4444';
            return <div key={j} className="flex-1 rounded-t-sm" style={{ height: `${h}px`, background: c, opacity: j === p.last_10_scores.length - 1 ? 1 : 0.6 }} title={`${p.player_name}: ${s}`} />;
          })}
        </div>
        <div className="flex justify-between items-center">
          <span className="text-[9px] text-slate-400">Last 10</span>
          <span className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-[9px] font-mono font-bold ${
            p.trend === 'up' ? 'bg-emerald-100 text-emerald-700' : p.trend === 'dn' ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-500'
          }`}>
            <TrendIcon className="w-2.5 h-2.5" />{p.delta}
          </span>
        </div>
      </div>
    );
  });

  const metricChart = (title, players, subtitle) => {
    const allVals = players?.flatMap(p => p.values?.filter(v => v != null) || []) || [];
    const yMin = allVals.length ? Math.min(...allVals) * 0.9 : 0;
    const yMax = allVals.length ? Math.max(...allVals) * 1.1 : 10;
    const chartData = score_evolution?.match_weeks?.map((w, i) => {
      const row = { week: `W${w}` };
      players?.forEach(p => { row[p.player_name] = p.values?.[i]; });
      return row;
    }) || [];
    const lineColors = [COLORS[0], COLORS[1], COLORS[2]];

    return (
      <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="px-4 py-2.5 border-b border-slate-100 flex justify-between items-center">
          <span className="text-xs font-bold text-slate-700">{title}</span>
          {subtitle && <span className="text-[10px] text-slate-400">{subtitle}</span>}
        </div>
        <div className="p-3">
          <ResponsiveContainer width="100%" height={130}>
            <LineChart data={chartData} margin={{ top: 5, right: 8, bottom: 5, left: 0 }}>
              <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
              <XAxis dataKey="week" tick={{ fontSize: 9, fill: '#94a3b8' }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
              <YAxis domain={[yMin, yMax]} tick={{ fontSize: 9, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={30} />
              <Tooltip contentStyle={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 11 }} />
              {players?.map((p, i) => (
                <Line key={p.player_name} type="monotone" dataKey={p.player_name} stroke={lineColors[i]} strokeWidth={2} dot={false} connectNulls />
              ))}
            </LineChart>
          </ResponsiveContainer>
          <div className="flex gap-3 mt-1 text-[10px] text-slate-400">
            {players?.map((p, i) => <span key={p.player_name}><span style={{ color: lineColors[i] }}>━</span> {p.player_name}</span>)}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-slate-900">Season Trends</h1>
          <p className="text-xs text-slate-500">FC Barcelona · La Liga 2015/16 · {summary.total_matches || 0} Matches</p>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-5 gap-3">
        {statCards.map((s, i) => (
          <div key={i} className={`rounded-xl border border-slate-200 bg-white p-3.5 shadow-sm ${s.border} border-l-4`}>
            <div className={`text-xl font-black font-mono leading-none ${s.color}`}>{s.value}</div>
            <div className="text-[10px] text-slate-500 mt-1">{s.label}</div>
            {s.sub && <div className="text-[9px] text-slate-400 mt-0.5">{s.sub}</div>}
          </div>
        ))}
      </div>

      {/* Score Evolution */}
      <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="px-4 py-2.5 border-b border-slate-100 flex justify-between items-center">
          <span className="text-xs font-bold text-slate-700">ML Score Evolution — All Matches</span>
          <div className="flex gap-2 text-[10px] text-slate-400">
            {score_evolution?.players?.map((p, i) => (
              <span key={p.player_name}><span style={{ color: COLORS[i] }}>━</span> {p.player_name.split(' ').slice(-1)[0]}</span>
            ))}
            <span><span className="text-slate-300">━</span> Squad Avg</span>
          </div>
        </div>
        <div className="p-4">
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={scoreEvoData} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
              <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
              <XAxis dataKey="week" tick={{ fontSize: 9, fill: '#94a3b8' }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
              <YAxis domain={[3, 10]} tick={{ fontSize: 9, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={30} />
              <Tooltip contentStyle={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 11 }} />
              {score_evolution?.players?.map((p, i) => (
                <Line key={p.player_name} type="monotone" dataKey={p.player_name} stroke={COLORS[i]} strokeWidth={2} dot={false} connectNulls />
              ))}
              <Line type="monotone" dataKey="Squad Avg" stroke="#94a3b8" strokeWidth={1.5} strokeDasharray="4 3" dot={false} connectNulls />
              <ReferenceLine y={7.0} stroke="#f85149" strokeDasharray="5 3" strokeOpacity={0.4} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Form Cards */}
      <div>
        <div className="flex items-center gap-2 mb-2.5">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Player Form Cards — Last 10 Matches</span>
          <div className="flex-1 h-px bg-slate-200" />
        </div>
        <div className="grid grid-cols-5 gap-3">
          {formCardGrid}
        </div>
      </div>

      {/* Heatmap + Rankings */}
      <div className="grid grid-cols-2 gap-3.5">
        {/* Heatmap */}
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="px-4 py-2.5 border-b border-slate-100 flex justify-between items-center">
            <span className="text-xs font-bold text-slate-700">Player × Match Score Heatmap</span>
            <span className="text-[10px] text-slate-400">Last 10 matches · Colored by score</span>
          </div>
          <div className="overflow-x-auto max-h-[360px]" style={{ scrollbarWidth: 'thin' }}>
            <table className="w-full border-collapse text-xs">
              <thead>
                <tr className="sticky top-0 bg-white border-b border-slate-100">
                  <th className="text-left py-2 px-2.5 text-[9px] text-slate-400 font-bold uppercase w-[140px]">Player</th>
                  {heatmap?.match_weeks?.map(w => (
                    <th key={w} className="py-2 px-0.5 text-center text-[9px] text-slate-400 font-bold uppercase w-[34px]">W{w}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {heatmap?.players?.map((name, pi) => (
                  <tr key={name} className="border-b border-slate-50 hover:bg-sky-50/50">
                    <td className="py-1.5 px-2.5 text-[10px] text-slate-600 font-semibold truncate">{name}</td>
                    {heatmap.scores[pi]?.map((v, mi) => (
                      <td key={mi} className="py-1 px-0.5">
                        <div className="h-5 w-[28px] mx-auto rounded-sm flex items-center justify-center text-[8px] font-mono font-bold"
                          style={{ background: heatColor(v), color: v >= 6.8 ? '#0D1117' : '#fff' }}
                          title={`${name}: ${v}`}>
                          {v.toFixed(1)}
                        </div>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-end gap-1.5 px-4 pb-3 pt-1">
            <span className="text-[9px] text-slate-400">Low</span>
            <div className="w-[100px] h-1.5 rounded-sm" style={{ background: 'linear-gradient(90deg, #ef4444, #f39c12, #00d084)' }} />
            <span className="text-[9px] text-slate-400">High</span>
          </div>
        </div>

        {/* Rankings */}
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="px-4 py-2.5 border-b border-slate-100 flex justify-between items-center">
            <span className="text-xs font-bold text-slate-700">Season Rankings — By ML Score</span>
          </div>
          <div className="overflow-y-auto max-h-[340px]" style={{ scrollbarWidth: 'thin' }}>
            <table className="w-full border-collapse">
              <thead>
                <tr className="text-[9px] text-slate-400 font-bold uppercase tracking-wider border-b border-slate-100">
                  <th className="text-left py-2 px-2.5">#</th>
                  <th className="text-left py-2 px-2.5">Player</th>
                  <th className="text-left py-2 px-2.5">Avg Score</th>
                  <th className="text-left py-2 px-2.5">GP</th>
                  <th className="text-left py-2 px-2.5">Trend</th>
                </tr>
              </thead>
              <tbody>
                {rankings?.map((r, i) => {
                  const TrendIcon = TREND_ICONS[r.trend] || Minus;
                  const scoreColor = r.avg_score >= 7.5 ? 'text-emerald-600' : r.avg_score >= 7.0 ? 'text-blue-600' : r.avg_score >= 6.5 ? 'text-amber-600' : 'text-red-500';
                  return (
                    <tr key={r.player_name} className="border-b border-slate-100 hover:bg-sky-50 transition-colors">
                      <td className="py-2 px-2.5 font-mono text-xs text-slate-400 font-bold w-6">{r.rank}</td>
                      <td className="py-2 px-2.5">
                        <div className="flex items-center gap-1.5">
                          <div className="w-6 h-6 rounded-full flex items-center justify-center text-[8px] font-bold shrink-0 bg-sky-100 text-sky-700 border border-sky-200">
                            {r.initials}
                          </div>
                          <div>
                            <div className="text-[11px] font-bold text-slate-800">{r.player_name}</div>
                            <div className="text-[9px] text-slate-500">{r.position_group}</div>
                          </div>
                        </div>
                      </td>
                      <td className={`py-2 px-2.5 font-mono text-xs font-bold ${scoreColor}`}>{r.avg_score?.toFixed(1)}</td>
                      <td className="py-2 px-2.5 font-mono text-xs text-slate-400">{r.matches_played}</td>
                      <td className="py-2 px-2.5">
                        <span className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-[9px] font-bold font-mono ${
                          r.trend === 'up' ? 'bg-emerald-100 text-emerald-700' : r.trend === 'dn' ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-500'
                        }`}>
                          <TrendIcon className="w-2.5 h-2.5" />
                          {r.trend_value > 0 ? '+' : ''}{r.trend_value?.toFixed(2)}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Metric Trend Charts */}
      <div>
        <div className="flex items-center gap-2 mb-2.5">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Key Metric Trends — Season</span>
          <div className="flex-1 h-px bg-slate-200" />
        </div>
        <div className="grid grid-cols-2 gap-3.5">
          {metric_trends?.xg && metricChart('xG per Match — Top 3', metric_trends.xg.players, 'Season rolling')}
          {metric_trends?.pass_accuracy && metricChart('Pass Accuracy — Midfielders', metric_trends.pass_accuracy.players, 'Season rolling')}
          {metric_trends?.vaep && metricChart('VAEP Rating — Squad Leaders', metric_trends.vaep.players, 'Value Added per Event')}
          {metric_trends?.dribble && metricChart('Dribble Success% — Forwards', metric_trends.dribble.players, 'Season rolling')}
        </div>
      </div>

      {/* Scatter */}
      <div>
        <div className="flex items-center gap-2 mb-2.5">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">VAEP Rating vs ML Season Average — Scatter</span>
          <div className="flex-1 h-px bg-slate-200" />
        </div>
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="px-4 py-2.5 border-b border-slate-100 flex justify-between items-center">
            <span className="text-xs font-bold text-slate-700">Expected (VAEP) vs Actual (ML) Performance</span>
            <span className="text-[10px] text-slate-400">Above diagonal = overperforming</span>
          </div>
          <div className="p-4">
            <ResponsiveContainer width="100%" height={300}>
              <ScatterChart margin={{ top: 10, right: 20, bottom: 25, left: 10 }}>
                <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
                <XAxis dataKey="vaep_rating" name="VAEP Rating" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false}
                  label={{ value: 'VAEP Rating (Season Avg)', position: 'bottom', offset: 10, style: { fontSize: 10, fill: '#94a3b8' } }} />
                <YAxis dataKey="overall_score" name="ML Score" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false}
                  label={{ value: 'ML Overall Score', angle: -90, position: 'insideLeft', offset: 0, style: { fontSize: 10, fill: '#94a3b8' } }} />
                <Tooltip contentStyle={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 11 }}
                  formatter={(value, name) => [value?.toFixed(2), name]} />
                <ReferenceLine segment={[{ x: -1.5, y: 5 }, { x: 2.5, y: 9 }]} stroke="#94a3b8" strokeDasharray="5 3" strokeOpacity={0.5} />
                <Scatter data={scatter} fill="#58A6FF">
                  {scatter?.map((p, i) => (
                    <Cell key={p.player_name} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SeasonTrends;
