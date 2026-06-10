import React, { useEffect, useState, useMemo } from 'react';
import {
  Loader2, Search
} from 'lucide-react';
import {
  AreaChart, Area, XAxis, YAxis, ResponsiveContainer, Tooltip
} from 'recharts';
import { MatchLogAPI } from '../api';
import { useAppContext } from '../context/AppContext';
import ErrorAlert from './ErrorAlert';

const FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'W', label: 'Wins' },
  { key: 'D', label: 'Draws' },
  { key: 'L', label: 'Losses' },
  { key: 'high', label: 'Score ≥ 7' },
];

const EVENT_COLORS = {
  goal: '#22c55e',
  shot: '#58A6FF',
  dribble: '#a855f7',
  pass: '#39D0D0',
  carry: '#8B949E',
  foul: '#f85149',
  pressure: '#ff8c42',
};
const EVENT_LABELS = {
  goal: '⚽ Goal',
  shot: 'Shot',
  dribble: 'Dribble',
  pass: 'Pass',
  carry: 'Carry',
  foul: 'Foul',
  pressure: 'Pressure',
};

function scoreChipClass(v) {
  if (v >= 7.5) return 'bg-emerald-100 text-emerald-700';
  if (v >= 7.0) return 'bg-blue-100 text-blue-700';
  if (v >= 6.5) return 'bg-amber-100 text-amber-700';
  if (v >= 6.0) return 'bg-slate-100 text-slate-500';
  return 'bg-red-100 text-red-700';
}

function xgBadgeClass(v) {
  if (v == null) return 'bg-slate-100 text-slate-500';
  if (v >= 0.3) return 'bg-emerald-100 text-emerald-700';
  if (v >= 0.15) return 'bg-amber-100 text-amber-700';
  return 'bg-red-100 text-red-700';
}

const MatchLog = () => {
  const { selectedSeason } = useAppContext();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');
  const [selectedMatchId, setSelectedMatchId] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    MatchLogAPI.getMatchLog(null, selectedSeason)
      .then(d => {
        if (!cancelled) {
          setData(d);
          if (d.matches?.length && !selectedMatchId) {
            setSelectedMatchId(d.matches[0].match_id);
          } else if (d.detail) {
            setSelectedMatchId(d.detail.match_id);
          }
          setLoading(false);
        }
      })
      .catch(e => { if (!cancelled) { setError(e.message); setLoading(false); } });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSeason]);

  const filteredMatches = useMemo(() => {
    if (!data?.matches) return [];
    let m = data.matches;
    if (filter === 'W') m = m.filter(x => x.result === 'W');
    else if (filter === 'D') m = m.filter(x => x.result === 'D');
    else if (filter === 'L') m = m.filter(x => x.result === 'L');
    else if (filter === 'high') m = m.filter(x => (x.squad_avg_score || 0) >= 7);
    if (search) {
      const q = search.toLowerCase();
      m = m.filter(x =>
        x.opponent?.toLowerCase().includes(q) ||
        x.date?.includes(q) ||
        String(x.match_id).includes(q)
      );
    }
    return m.sort((a, b) => (b.match_week || 0) - (a.match_week || 0));
  }, [data, filter, search]);

  const [fetchedDetail, setFetchedDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const selectMatch = (matchId) => {
    setSelectedMatchId(matchId);
  };

  useEffect(() => {
    if (!selectedMatchId) return;
    if (data?.detail?.match_id === selectedMatchId) {
      setFetchedDetail(data.detail);
      return;
    }
    setDetailLoading(true);
    MatchLogAPI.getMatchLog(selectedMatchId)
      .then(d => {
        if (d.detail) setFetchedDetail(d.detail);
        setDetailLoading(false);
      })
      .catch(() => setDetailLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedMatchId]);

  if (loading) return <div className="flex items-center justify-center py-20"><Loader2 className="h-8 w-8 animate-spin text-brand-600" /></div>;
  if (error) return <ErrorAlert message={error} />;
  if (!data) return <ErrorAlert message="No match log data available" />;

  const md = fetchedDetail;

  const renderMatchList = () => (
    <div className="w-[350px] shrink-0 border-r border-slate-200 bg-white/80 flex flex-col">
      {/* Search & Filters */}
      <div className="p-3 border-b border-slate-200 space-y-2">
        <div className="flex items-center gap-2 bg-slate-100 rounded-lg px-3 py-2">
          <Search className="w-3.5 h-3.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search opponent, date, ID..."
            className="bg-transparent text-xs text-slate-700 outline-none w-full placeholder:text-slate-400"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <div className="flex gap-1.5 flex-wrap">
          {FILTERS.map(f => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={`px-2.5 py-1 rounded-md text-[10px] font-semibold transition-colors ${
                filter === f.key
                  ? 'bg-emerald-100 text-emerald-700 border border-emerald-200'
                  : 'bg-slate-100 text-slate-500 border border-slate-200 hover:bg-slate-200'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Match List */}
      <div className="flex-1 overflow-y-auto" style={{ scrollbarWidth: 'thin' }}>
        {filteredMatches.map(m => {
          const isActive = m.match_id === selectedMatchId;
          const rc = m.result === 'W' ? 'bg-emerald-100 text-emerald-700' :
                     m.result === 'D' ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-700';
          const sc = (m.squad_avg_score || 0) >= 7.5 ? 'text-emerald-600' :
                     (m.squad_avg_score || 0) >= 7.0 ? 'text-blue-600' :
                     (m.squad_avg_score || 0) >= 6.5 ? 'text-amber-600' : 'text-red-500';
          return (
            <div
              key={m.match_id}
              onClick={() => selectMatch(m.match_id)}
              className={`flex items-center gap-2.5 px-3.5 py-2.5 border-b border-slate-100 cursor-pointer transition-colors ${
                isActive ? 'bg-emerald-50 border-l-3 border-l-emerald-500' : 'hover:bg-slate-50'
              }`}
            >
              <div className="font-mono text-[10px] text-slate-400 w-[30px] shrink-0">W{m.match_week}</div>
              <div className="flex-1 min-w-0">
                <div className="text-xs font-bold text-slate-800 truncate">{m.is_home ? 'vs' : '@'} {m.opponent}</div>
                <div className="text-[9px] text-slate-500 mt-0.5">{m.date} · {m.total_shots} shots</div>
              </div>
              <div className="flex flex-col items-end gap-1">
                <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold font-mono ${rc}`}>{m.result} {m.score}</span>
                <span className={`font-mono text-xs font-black ${sc}`}>{m.squad_avg_score?.toFixed(1)}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );

  const renderMatchDetail = () => {
    if (!md) {
      return (
        <div className="flex items-center justify-center h-full text-sm text-slate-400">
          Select a match to view details
        </div>
      );
    }

    const rc = md.result === 'W' ? 'bg-emerald-100 text-emerald-700' :
               md.result === 'D' ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-700';
    const avgColor = (md.squad_avg_score || 0) >= 7.5 ? 'text-emerald-600' :
                     (md.squad_avg_score || 0) >= 7.0 ? 'text-blue-600' :
                     (md.squad_avg_score || 0) >= 6.5 ? 'text-amber-600' : 'text-red-500';

    // xG flow chart data
    const xgFlowData = md.xg_flow?.map((v, i) => ({ minute: i, xg: v })) || [];

    // KPI cards
    const kpis = [
      { label: 'Squad ML Score', value: md.squad_avg_score?.toFixed(1), color: avgColor },
      { label: 'Possession', value: `${md.possession}%`, color: 'text-blue-600' },
      { label: 'Total Shots', value: md.total_shots, color: 'text-rose-600' },
      { label: 'Team xG', value: md.total_xg?.toFixed(2), color: 'text-amber-600' },
      { label: 'Goals Scored', value: md.goals_for, color: 'text-emerald-600' },
    ];

    return (
      <div className="p-5 space-y-4 overflow-y-auto h-full" style={{ scrollbarWidth: 'thin' }}>
        {/* Match Banner */}
        <div className="rounded-xl border border-slate-200 bg-gradient-to-br from-slate-50 to-white shadow-sm p-4 relative overflow-hidden">
          <div className="absolute -top-10 -right-10 w-[200px] h-[200px] rounded-full bg-emerald-500/5" />
          <div className="flex items-center gap-3 relative z-10">
            <div className="w-9 h-9 rounded-lg flex items-center justify-center text-[9px] font-black shrink-0"
              style={{ background: 'linear-gradient(135deg, #003f7f, #a50044)', color: '#fff' }}>
              FCB
            </div>
            <div>
              <div className="text-sm font-bold text-slate-800">FC Barcelona</div>
              <div className="text-[10px] text-slate-500">{md.is_home ? 'Home · Camp Nou' : 'Away'}</div>
            </div>
            <div className="text-2xl font-black font-mono px-3 py-1 rounded-lg"
              style={{ background: 'linear-gradient(135deg, #22c55e, #58A6FF)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              {md.score}
            </div>
            <div className="text-right">
              <div className="text-sm font-bold text-slate-800">{md.opponent}</div>
              <div className="text-[10px] text-slate-500">{md.date} · Week {md.match_week}</div>
            </div>
            <div className="w-9 h-9 rounded-lg flex items-center justify-center text-[9px] font-black bg-slate-200 text-slate-600 shrink-0">
              {md.opponent?.slice(0, 3).toUpperCase()}
            </div>
            <div className="ml-auto flex items-center gap-2">
              <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold font-mono ${rc}`}>{md.result} {md.score}</span>
            </div>
          </div>
          <div className="flex gap-5 mt-3 relative z-10">
            <div className="text-center"><div className={`text-base font-black font-mono ${avgColor}`}>{md.squad_avg_score?.toFixed(1)}</div><div className="text-[9px] text-slate-500">Squad Avg ML</div></div>
            <div className="text-center"><div className="text-base font-black font-mono text-blue-600">{md.possession}%</div><div className="text-[9px] text-slate-500">Possession</div></div>
            <div className="text-center"><div className="text-base font-black font-mono text-rose-600">{md.total_shots}</div><div className="text-[9px] text-slate-500">Shots</div></div>
            <div className="text-center"><div className="text-base font-black font-mono text-amber-600">{md.total_xg?.toFixed(2)}</div><div className="text-[9px] text-slate-500">Team xG</div></div>
            <div className="text-center"><div className="text-base font-black font-mono text-slate-400">{md.match_id}</div><div className="text-[9px] text-slate-500">Match ID</div></div>
          </div>
        </div>

        {/* Possession Bar */}
        <div>
          <div className="flex justify-between text-[9px] text-slate-500 mb-1">
            <span>FCB {md.possession}%</span>
            <span>Possession</span>
            <span>{100 - (md.possession || 0)}% {md.opponent}</span>
          </div>
          <div className="h-2.5 bg-slate-200 rounded-full overflow-hidden flex">
            <div className="h-full rounded-full" style={{ width: `${md.possession}%`, background: 'linear-gradient(90deg, #22c55e, #58A6FF)' }} />
          </div>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-5 gap-2">
          {kpis.map((k, i) => (
            <div key={i} className="rounded-lg border border-slate-200 bg-white/80 p-3 text-center">
              <div className={`text-base font-black font-mono leading-none ${k.color}`}>{k.value}</div>
              <div className="text-[9px] text-slate-500 mt-1">{k.label}</div>
            </div>
          ))}
        </div>

        {/* xG Flow */}
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="px-4 py-2.5 border-b border-slate-100 flex justify-between items-center">
            <span className="text-xs font-bold text-slate-700">Cumulative xG Flow</span>
            <span className="text-[10px] text-slate-400">Total: {md.total_xg?.toFixed(2)} xG</span>
          </div>
          <div className="p-3">
            <ResponsiveContainer width="100%" height={80}>
              <AreaChart data={xgFlowData} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
                <defs>
                  <linearGradient id="xgGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#22c55e" stopOpacity={0.25} />
                    <stop offset="100%" stopColor="#22c55e" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="minute" hide />
                <YAxis hide domain={[0, 'auto']} />
                <Tooltip contentStyle={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 10 }}
                  formatter={(v) => [v?.toFixed(3), 'xG']} />
                <Area type="monotone" dataKey="xg" stroke="#22c55e" strokeWidth={1.5} fill="url(#xgGrad)" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
            <div className="flex justify-between text-[9px] text-slate-400 mt-1">
              <span>0'</span><span>15'</span><span>30'</span><span>45' HT</span><span>60'</span><span>75'</span><span>90'</span>
            </div>
          </div>
        </div>



        {/* Player Ratings */}
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="px-4 py-2.5 border-b border-slate-100 flex justify-between items-center">
            <span className="text-xs font-bold text-slate-700">Player ML Ratings — This Match</span>
          </div>
          <div className="p-3">
            <div className="grid grid-cols-4 gap-2">
              {md.players?.map(p => {
                const scoreColor = (p.overall_score || 0) >= 7.5 ? 'text-emerald-600' :
                                   (p.overall_score || 0) >= 7.0 ? 'text-blue-600' :
                                   (p.overall_score || 0) >= 6.5 ? 'text-amber-600' : 'text-red-500';
                return (
                  <div key={p.player_id} className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50/50 p-2 cursor-pointer transition-colors hover:border-emerald-300">
                    <div className="w-7 h-7 rounded-full flex items-center justify-center text-[8px] font-bold shrink-0"
                      style={{ background: '#1a6be022', color: '#1a6be0', border: '1.5px solid #1a6be044' }}>
                      {p.initials}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-[10px] font-bold text-slate-700 truncate">{p.player_name}</div>
                      <div className="text-[9px] text-slate-500">{p.position_group}</div>
                    </div>
                    <span className={`font-mono text-sm font-black shrink-0 ${scoreColor}`}>{p.overall_score?.toFixed(1)}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Player Stats Table */}
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="px-4 py-2.5 border-b border-slate-100">
            <span className="text-xs font-bold text-slate-700">Computed Features & Model Scores</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-xs" style={{ minWidth: 700 }}>
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-[9px] text-slate-500 font-bold uppercase tracking-wider">
                  <th className="text-left py-2 px-2.5">Player</th>
                  <th className="text-center py-2 px-2.5">ML Score</th>
                  <th className="text-center py-2 px-2.5">Passes</th>
                  <th className="text-center py-2 px-2.5">Acc%</th>
                  <th className="text-center py-2 px-2.5">Shots</th>
                  <th className="text-center py-2 px-2.5">xG</th>
                  <th className="text-center py-2 px-2.5">Drb</th>
                  <th className="text-center py-2 px-2.5">VAEP</th>
                </tr>
              </thead>
              <tbody>
                {md.players?.map(p => {
                  const accColor = (p.pass_accuracy || 0) >= 85 ? 'text-emerald-600' :
                                   (p.pass_accuracy || 0) >= 75 ? 'text-blue-600' : 'text-amber-600';
                  const vaepColor = (p.vaep_rating || 0) >= 1.5 ? 'text-emerald-600' :
                                    (p.vaep_rating || 0) >= 1.0 ? 'text-blue-600' : 'text-amber-600';
                  return (
                    <tr key={p.player_id} className="border-b border-slate-100 hover:bg-sky-50/50 cursor-pointer transition-colors">
                      <td className="py-2 px-2.5">
                        <div className="flex items-center gap-1.5">
                          <div className="w-6 h-6 rounded-full flex items-center justify-center text-[7px] font-bold shrink-0"
                            style={{ background: '#1a6be022', color: '#1a6be0', border: '1.5px solid #1a6be044' }}>
                            {p.initials}
                          </div>
                          <div>
                            <div className="text-[11px] font-bold text-slate-800">{p.player_name}</div>
                            <div className="text-[9px] text-slate-500">{p.position_group}</div>
                          </div>
                        </div>
                      </td>
                      <td className="text-center"><span className={`px-1.5 py-0.5 rounded text-[10px] font-bold font-mono ${scoreChipClass(p.overall_score)}`}>{p.overall_score?.toFixed(1)}</span></td>
                      <td className="text-center font-mono text-[11px] text-slate-700">{p.passes ?? '—'}</td>
                      <td className={`text-center font-mono text-[11px] ${accColor}`}>{p.pass_accuracy != null ? `${p.pass_accuracy.toFixed(1)}%` : '—'}</td>
                      <td className="text-center font-mono text-[11px] text-slate-700">{p.shots ?? '—'}</td>
                      <td className="text-center"><span className={`px-1.5 py-0.5 rounded text-[10px] font-bold font-mono ${xgBadgeClass(p.xg)}`}>{p.xg != null ? p.xg.toFixed(2) : '—'}</span></td>
                      <td className="text-center font-mono text-[11px] text-purple-600">{p.dribbles || '—'}</td>
                      <td className={`text-center font-mono text-xs font-bold ${vaepColor}`}>{p.vaep_rating?.toFixed(2) ?? '—'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Event Log */}
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="px-4 py-2.5 border-b border-slate-100 flex justify-between items-center">
            <span className="text-xs font-bold text-slate-700">Key Event Log</span>
            <span className="text-[10px] text-slate-400">Sorted by impact (xG)</span>
          </div>
          <div className="overflow-y-auto max-h-[280px]" style={{ scrollbarWidth: 'thin' }}>
            <table className="w-full border-collapse text-xs">
              <thead>
                <tr className="text-[9px] text-slate-500 font-bold uppercase tracking-wider border-b border-slate-200 bg-slate-50 sticky top-0">
                  <th className="text-left py-2 px-2.5">Min</th>
                  <th className="text-left py-2 px-2.5">Event</th>
                  <th className="text-left py-2 px-2.5">Player</th>
                  <th className="text-left py-2 px-2.5">Outcome</th>
                  <th className="text-left py-2 px-2.5">xG</th>
                </tr>
              </thead>
              <tbody>
                {md.events
                  ?.filter(e => ['goal','shot','dribble','foul','carry','pressure','pass'].includes(e.event_type?.toLowerCase()))
                  ?.sort((a, b) => (b.xg || 0) - (a.xg || 0))
                  ?.slice(0, 50)
                  ?.sort((a, b) => (a.period - b.period) || (a.minute - b.minute))
                  ?.map((e, i) => {
                  const et = e.event_type?.toLowerCase();
                  const ec = EVENT_COLORS[et] || '#8B949E';
                  return (
                    <tr key={i} className="border-b border-slate-100 hover:bg-sky-50/50">
                      <td className="py-1.5 px-2.5 font-mono text-[10px] text-slate-500">{e.minute}'<span className="ml-0.5 text-[8px] text-slate-400">{e.period === 1 ? '1H' : '2H'}</span></td>
                      <td className="py-1.5 px-2.5">
                        <span className="px-1.5 py-0.5 rounded text-[9px] font-bold" style={{ background: `${ec}22`, color: ec }}>
                          {EVENT_LABELS[et] || e.event_type}
                        </span>
                      </td>
                      <td className="py-1.5 px-2.5 text-[11px] font-semibold text-slate-700">{e.player_name}</td>
                      <td className="py-1.5 px-2.5 text-[10px] text-slate-500">{e.outcome || '—'}</td>
                      <td className="py-1.5 px-2.5">
                        {e.xg != null ? (
                          <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold font-mono ${xgBadgeClass(e.xg)}`}>
                            {e.xg.toFixed(2)}
                          </span>
                        ) : '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="flex h-[calc(100vh-120px)] rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      {renderMatchList()}
      <div className="flex-1 overflow-hidden bg-gradient-to-br from-slate-50/50 to-white">
        {detailLoading ? (
          <div className="flex items-center justify-center h-full"><Loader2 className="h-6 w-6 animate-spin text-brand-600" /></div>
        ) : renderMatchDetail()}
      </div>
    </div>
  );
};

export default MatchLog;
