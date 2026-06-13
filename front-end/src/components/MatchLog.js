import React, { useEffect, useState, useMemo, useCallback } from 'react';
import {
  Loader2, Search, Target
} from 'lucide-react';
import {
  AreaChart, Area, XAxis, YAxis, ResponsiveContainer, Tooltip
} from 'recharts';
import { MatchLogAPI, MatchAnalysisAPI } from '../api';
import { useAppContext } from '../context/AppContext';
import ErrorAlert from './ErrorAlert';

const FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'W', label: 'Wins' },
  { key: 'D', label: 'Draws' },
  { key: 'L', label: 'Losses' },
  { key: 'high', label: 'Score \u2265 7' },
];

const EVENT_COLORS = {
  goal: '#22c55e', shot: '#58A6FF', dribble: '#a855f7',
  pass: '#39D0D0', carry: '#8B949E', foul: '#f85149', pressure: '#ff8c42',
  'ball receipt*': '#f472b6', block: '#f97316', clearance: '#14b8a6',
  duel: '#eab308', interception: '#0ea5e9', 'ball recovery': '#6366f1',
  'goal keeper': '#06b6d4', shield: '#a1a1aa', miscontrol: '#fb923c',
  error: '#ef4444', dispossessed: '#a855f7',
};
const EVENT_LABELS = {
  goal: 'Goal', shot: 'Shot', dribble: 'Dribble', pass: 'Pass',
  carry: 'Carry', foul: 'Foul', pressure: 'Pressure',
  'ball receipt*': 'Receipt', block: 'Block', clearance: 'Clearance',
  duel: 'Duel', interception: 'Int.', 'ball recovery': 'Recovery',
  'goal keeper': 'GK Save', shield: 'Shield', miscontrol: 'Miss',
  error: 'Error', dispossessed: 'Lost',
};
const EVENT_ICONS = {
  goal: '\u26BD', shot: '\uD83C\uDFAF', dribble: '\uD83D\uDCA8',
  pass: '\u27A1\uFE0F', carry: '\uD83C\uDFC3', foul: '\uD83D\uDEAB',
  pressure: '\uD83D\uDD25', 'ball receipt*': '\uD83D\uDCE9',
  block: '\uD83D\uDEE1\uFE0F', clearance: '\uD83D\uDD04',
  duel: '\u2694\uFE0F', interception: '\u270B',
  'ball recovery': '\uD83D\uDD19', 'goal keeper': '\uD83E\uDDE4',
  shield: '\uD83D\uDEF0\uFE0F', miscontrol: '\uD83D\uDCA5',
  error: '\u26A0\uFE0F', dispossessed: '\u2B07\uFE0F',
};

const POS_COLORS = {
  GK: { bg: 'rgba(168,85,247,0.25)', stroke: '#A855F7', text: '#A855F7' },
  DF: { bg: 'rgba(88,166,255,0.2)', stroke: '#58A6FF', text: '#58A6FF' },
  MF: { bg: 'rgba(0,208,132,0.2)', stroke: '#00D084', text: '#00D084' },
  FW: { bg: 'rgba(248,81,73,0.2)', stroke: '#F85149', text: '#F85149' },
};

const POS_X = { GK: 80, DF: 220, MF: 360, FW: 500 };

function scoreChipClass(v) {
  if (v >= 7.5) return 'bg-emerald-100 text-emerald-700';
  if (v >= 7.0) return 'bg-blue-100 text-blue-700';
  if (v >= 6.5) return 'bg-amber-100 text-amber-700';
  if (v >= 6.0) return 'bg-slate-100 text-slate-500';
  return 'bg-red-100 text-red-700';
}




function initials(name) {
  return (name || '??').split(' ').map(s => s[0]).filter(Boolean).slice(0, 2).join('').toUpperCase();
}

function spreadVert(index, total) {
  if (total <= 1) return 250;
  const spacing = 420 / total;
  return 40 + spacing * (index + 0.5);
}

const PitchSVG = ({ players, width, height, attackLabel, onPlayerClick, selectedPlayerId }) => {
  const vw = 700, vh = 500;

  const grouped = useMemo(() => {
    const g = { GK: [], DF: [], MF: [], FW: [] };
    (players || []).forEach(p => {
      const pg = p.position_group || 'MF';
      if (g[pg]) g[pg].push(p);
    });
    Object.values(g).forEach(arr => arr.sort((a, b) => (a.avg_y || 0) - (b.avg_y || 0)));
    return g;
  }, [players]);

  return (
    <svg viewBox={`0 0 ${vw} ${vh}`} className="w-full select-none" xmlns="http://www.w3.org/2000/svg">
      <rect width={vw} height={vh} fill="#0a1a0e" />
      <g opacity="0.06">
        {[0, 96, 192, 288, 384].map(x => (
          <rect key={x} x={x} y="0" width="48" height={vh} fill="#00D084" />
        ))}
      </g>
      <rect x="30" y="20" width="640" height="460" fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth="1.5" />
      <line x1="350" y1="20" x2="350" y2="480" stroke="rgba(255,255,255,0.18)" strokeWidth="1.2" />
      <circle cx="350" cy="250" r="55" fill="none" stroke="rgba(255,255,255,0.18)" strokeWidth="1.2" />
      <circle cx="350" cy="250" r="3" fill="rgba(255,255,255,0.3)" />
      <rect x="30" y="130" width="90" height="240" fill="none" stroke="rgba(255,255,255,0.18)" strokeWidth="1.2" />
      <rect x="580" y="130" width="90" height="240" fill="none" stroke="rgba(255,255,255,0.18)" strokeWidth="1.2" />
      <rect x="30" y="175" width="40" height="150" fill="none" stroke="rgba(255,255,255,0.12)" strokeWidth="1" />
      <rect x="630" y="175" width="40" height="150" fill="none" stroke="rgba(255,255,255,0.12)" strokeWidth="1" />

      {Object.entries(grouped).map(([pg, arr]) =>
        arr.map((p, i) => {
          const c = POS_COLORS[pg] || POS_COLORS.MF;
          const sx = POS_X[pg] || 350;
          const sy = spreadVert(i, arr.length);
          const sel = selectedPlayerId === p.player_id;
          return (
            <g key={p.player_id} onClick={() => onPlayerClick?.(p)} style={{ cursor: 'pointer' }}>
              <circle cx={sx} cy={sy} r={sel ? 20 : 16} fill={c.bg} stroke={sel ? '#fff' : c.stroke} strokeWidth={sel ? 2.5 : 1.5} />
              <text x={sx} y={sy - 3} fill={c.text} fontSize="9" fontFamily="Inter, sans-serif" fontWeight="700" textAnchor="middle">
                {p.initials}
              </text>
              <text x={sx} y={sy + 8} fill="rgba(255,255,255,0.4)" fontSize="7" fontFamily="JetBrains Mono, monospace" textAnchor="middle">
                {p.jersey_number || ''}
              </text>
              <text x={sx} y={sy + 22} fill="#8B949E" fontSize="7.5" fontFamily="Inter, sans-serif" textAnchor="middle">
                {(p.overall_score || 0) > 0 ? p.overall_score?.toFixed(1) : ''}
              </text>
            </g>
          );
        })
      )}

      {attackLabel && (
        <g opacity="0.15">
          <line x1="520" y1="472" x2="620" y2="472" stroke="white" strokeWidth="1" />
          <polygon points="620,468 630,472 620,476" fill="white" />
          <text x="575" y="469" fill="white" fontSize="8" fontFamily="Inter, sans-serif" textAnchor="middle">{attackLabel}</text>
        </g>
      )}
    </svg>
  );
};

const PlayerDetailCard = ({ player, allPlayers }) => {
  if (!player) return null;
  const p = allPlayers?.find(x => x.player_id === player.player_id) || player;

  const statRow = (label, val, fmt) => (
    <div className="flex justify-between items-center text-xs">
      <span className="text-slate-500 text-[10px]">{label}</span>
      <span className="font-mono font-bold text-slate-700">{val != null ? fmt(val) : '\u2014'}</span>
    </div>
  );

  return (
    <div className="h-full flex flex-col">
      <div className="px-3 py-2 border-b border-slate-100 bg-slate-50/50 flex items-center gap-2">
        <span className="text-[10px] font-bold text-slate-700">Match Stats</span>
      </div>
      <div className="p-3 space-y-2.5 flex-1 overflow-y-auto" style={{ scrollbarWidth: 'thin' }}>
        <div className="flex items-center gap-2 pb-2 border-b border-slate-100">
          <div className="w-8 h-8 rounded-full flex items-center justify-center text-[9px] font-bold shrink-0"
            style={{ background: '#1a6be022', color: '#1a6be0', border: '1.5px solid #1a6be044' }}>
            {initials(p.player_name)}
          </div>
          <div className="min-w-0">
            <div className="text-xs font-bold text-slate-800 truncate">{p.player_name}</div>
            <div className="text-[9px] text-slate-500">{p.position_group} &middot; #{player.jersey_number}</div>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-1 py-1.5 border-b border-slate-100">
          <div className="text-center">
            <div className="text-lg font-black font-mono">{p.overall_score?.toFixed(1)}</div>
            <div className="text-[7px] text-slate-500">ML Score</div>
          </div>
          <div className="text-center border-l border-slate-200">
            <div className="text-lg font-black font-mono" style={{ color: '#7c3aed' }}>
              {p.position_kpi != null ? p.position_kpi.toFixed(1) : '\u2014'}
            </div>
            <div className="text-[7px] text-slate-500">Position</div>
          </div>
        </div>
        <div className="text-[10px] font-semibold text-slate-600 uppercase tracking-wider">Attacking</div>
        {statRow('Goals', p.goals, v => v)}
        {statRow('Shots', p.total_shots, v => v)}
        {statRow('Shots on Target', p.shots_on_target, v => v)}
        {statRow('xG', p.total_xg, v => v.toFixed(2))}
        <div className="text-[10px] font-semibold text-slate-600 uppercase tracking-wider pt-1">Passing</div>
        {statRow('Passes', p.total_passes, v => v)}
        {statRow('Accuracy', p.pass_accuracy, v => `${v}%`)}
        {statRow('Progressive', p.progressive_passes, v => v)}
        <div className="text-[10px] font-semibold text-slate-600 uppercase tracking-wider pt-1">Movement</div>
        {statRow('Carries', p.total_carries, v => v)}
        {statRow('Dribbles', p.total_dribbles, v => v)}
        {statRow('Dribble Success', p.dribble_success_rate, v => `${v}%`)}
        {statRow('Distance', p.distance_covered, v => `${v?.toFixed(1)}m`)}
        <div className="text-[10px] font-semibold text-slate-600 uppercase tracking-wider pt-1">Other</div>
        {statRow('Pressures', p.total_pressures, v => v)}
        {statRow('Fouls', p.fouls_committed, v => v)}
        {statRow('Fouls Drawn', p.fouls_won, v => v)}
        {statRow('Ball Receipts', p.ball_receipts, v => v)}
        {statRow('Ball Retention', p.ball_retention_rate, v => `${v}%`)}
      </div>
    </div>
  );
};

const TacticalBoardSection = ({ analysis, width, height, onPlayerClick, selectedPlayerId, allPlayers }) => {
  if (!analysis) return null;
  const home = analysis.tactical?.home;
  const away = analysis.tactical?.away;
  const mc = analysis.match_context || {};
  const hName = mc.home_team || 'Home';
  const aName = mc.away_team || 'Away';
  const hFormation = home?.formation || '';
  const aFormation = away?.formation || '';

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      <div className="px-4 py-2.5 border-b border-slate-100 flex items-center gap-3">
        <Target className="w-4 h-4 text-brand-600" />
        <span className="text-xs font-bold text-slate-700">Tactical Board — Formation View</span>
        <span className="text-[10px] font-mono text-slate-400 ml-auto">
          {hName} {hFormation} &middot; {aName} {aFormation}
        </span>
      </div>
      <div className="flex">
        <div className="flex-1 border-r border-slate-200">
          <div className="px-3 py-1.5 bg-slate-50/50 border-b border-slate-100 text-[10px] font-semibold text-slate-600">
            {hName} — {hFormation}
          </div>
          <PitchSVG players={home?.players} width={width / 2} height={height} attackLabel="Attack \u2192"
            onPlayerClick={onPlayerClick} selectedPlayerId={selectedPlayerId} />
        </div>
        <div className="flex-1 border-r border-slate-200">
          <div className="px-3 py-1.5 bg-slate-50/50 border-b border-slate-100 text-[10px] font-semibold text-slate-600">
            {aName} — {aFormation}
          </div>
          <PitchSVG players={away?.players} width={width / 2} height={height} attackLabel="\u2190 Attack"
            onPlayerClick={onPlayerClick} selectedPlayerId={selectedPlayerId} />
        </div>
        {selectedPlayerId && (
          <div className="w-56 shrink-0 border-l border-slate-200">
            <PlayerDetailCard player={home?.players?.find(p => p.player_id === selectedPlayerId) || away?.players?.find(p => p.player_id === selectedPlayerId)} allPlayers={allPlayers} />
          </div>
        )}
      </div>
    </div>
  );
};

const TeamStatsTable = ({ analysis }) => {
  const ts = analysis?.team_stats || {};
  const hs = ts?.home;
  const as = ts?.away;
  const ht = analysis?.match_context?.home_team || 'Home';
  const at = analysis?.match_context?.away_team || 'Away';

  const rows = useMemo(() => {
    if (!hs || !as) return [];
    const keys = [
      { key: 'possession_pct', label: 'Possession', fmt: v => `${v}%` },
      { key: 'total_passes', label: 'Passes', fmt: v => String(v) },
      { key: 'pass_accuracy', label: 'Pass Accuracy', fmt: v => `${v}%` },
      { key: 'total_shots', label: 'Shots', fmt: v => String(v) },
      { key: 'shots_on_target', label: 'Shots on Target', fmt: v => String(v) },
      { key: 'total_xg', label: 'xG', fmt: v => v?.toFixed(2) },
      { key: 'goals', label: 'Goals', fmt: v => String(v) },
      { key: 'total_pressures', label: 'Pressures', fmt: v => String(v) },
      { key: 'fouls', label: 'Fouls', fmt: v => String(v) },
    ];
    return keys.map(k => {
      const hv = hs[k.key];
      const av = as[k.key];
      const total = (hv ?? 0) + (av ?? 0);
      const pct = total > 0 ? ((hv ?? 0) / total) * 100 : 50;
      return { ...k, homeValue: k.fmt(hv), awayValue: k.fmt(av), pct };
    });
  }, [hs, as]);

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="px-4 py-2.5 border-b border-slate-100">
        <span className="text-xs font-bold text-slate-700">Team Stats Comparison</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-xs">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200 text-[9px] text-slate-500 font-bold uppercase tracking-wider">
              <th className="text-left py-2 px-2.5">{ht}</th>
              <th className="text-center py-2 px-2.5 w-1/3">Stat</th>
              <th className="text-right py-2 px-2.5">{at}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="border-b border-slate-100">
                <td className="py-1.5 px-2.5 text-right">
                  <span className="font-mono text-sm font-bold" style={{ color: '#22c55e' }}>{r.homeValue}</span>
                </td>
                <td className="py-1.5 px-2.5 text-center">
                  <div className="flex items-center gap-1 justify-center">
                    <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden flex-1 max-w-[80px]">
                      <div className="h-full rounded-full" style={{ width: `${r.pct}%`, background: '#22c55e' }} />
                    </div>
                    <span className="text-[10px] font-semibold text-slate-600 min-w-[60px] text-center">{r.label}</span>
                    <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden flex-1 max-w-[80px]">
                      <div className="h-full rounded-full float-right" style={{ width: `${100 - r.pct}%`, background: '#58A6FF' }} />
                    </div>
                  </div>
                </td>
                <td className="py-1.5 px-2.5 text-left">
                  <span className="font-mono text-sm font-bold" style={{ color: '#58A6FF' }}>{r.awayValue}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const MatchLog = () => {
  const { selectedSeason } = useAppContext();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');
  const [selectedMatchId, setSelectedMatchId] = useState(null);
  const [selectedPitchPlayerId, setSelectedPitchPlayerId] = useState(null);
  const [keyEventsOnly, setKeyEventsOnly] = useState(true);

  const isKeyEvent = (e) => {
    const et = (e.event_type || '').toLowerCase();
    const out = (e.outcome || '');
    if (et === 'shot' && out === 'Goal') return true;
    if (et === 'own goal against' || et === 'own goal for') return true;
    if (et === 'substitution' || et === 'player on' || et === 'player off') return true;
    if (et === 'shot') {
      if (out === 'Saved') return true;
      if ((e.xg || 0) > 0.25) return true;
      if (out === 'Post') return true;
    }
    if (et === 'goal keeper') return true;
    return false;
  };

  const handlePlayerClick = useCallback((player) => {
    setSelectedPitchPlayerId(prev => prev === player.player_id ? null : player.player_id);
  }, []);

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

  const [analysis, setAnalysis] = useState(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);

  useEffect(() => {
    if (!selectedMatchId) return;
    setAnalysisLoading(true);
    MatchAnalysisAPI.getAnalysis(selectedMatchId, selectedSeason)
      .then(d => { setAnalysis(d); setAnalysisLoading(false); })
      .catch(() => setAnalysisLoading(false));
  }, [selectedMatchId, selectedSeason]);

  const xgFlowData = useMemo(() => {
    if (!analysis?.timeline) return [];
    const minuteMap = {};
    analysis.timeline.forEach(e => {
      const m = e.minute || 0;
      if (m > 120) return;
      const xg = e.xg || 0;
      minuteMap[m] = (minuteMap[m] || 0) + xg;
    });
    let cum = 0;
    const result = [];
    for (let i = 0; i <= 90; i++) {
      cum += minuteMap[i] || 0;
      result.push({ minute: i, xg: Math.round(cum * 1000) / 1000 });
    }
    return result;
  }, [analysis]);

  const totalXg = useMemo(() => {
    if (!analysis?.timeline) return 0;
    return analysis.timeline.reduce((s, e) => s + (e.xg || 0), 0);
  }, [analysis]);

  const possession = useMemo(() => {
    const barcaSide = analysis?.match_analysis?.barcelona_side || 'home';
    return analysis?.team_stats?.[barcaSide]?.possession_pct || 50;
  }, [analysis]);

  const totalShots = useMemo(() => {
    const h = analysis?.team_stats?.home?.total_shots || 0;
    const a = analysis?.team_stats?.away?.total_shots || 0;
    return h + a;
  }, [analysis]);

  const allPlayerRatings = useMemo(() => {
    if (!analysis?.players) return [];
    const all = [...(analysis.players.home || []), ...(analysis.players.away || [])];
    return all.sort((a, b) => (b.overall_score || 0) - (a.overall_score || 0));
  }, [analysis]);

  const selectMatch = (matchId) => {
    setSelectedMatchId(matchId);
  };

  if (loading) return <div className="flex items-center justify-center py-20"><Loader2 className="h-8 w-8 animate-spin text-brand-600" /></div>;
  if (error) return <ErrorAlert message={error} />;
  if (!data) return <ErrorAlert message="No match log data available" />;

  const renderMatchList = () => (
    <div className="w-[320px] shrink-0 border-r border-slate-200 bg-white/80 flex flex-col">
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

      <div className="flex-1 overflow-y-auto" style={{ scrollbarWidth: 'thin' }}>
        {filteredMatches.map(m => {
          const isActive = m.match_id === selectedMatchId;
          const rc = m.result === 'W' ? 'bg-emerald-100 text-emerald-700' :
                     m.result === 'D' ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-700';
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
                <div className="text-[9px] text-slate-500 mt-0.5">{m.date} &middot; {m.total_shots} shots</div>
              </div>
              <div className="flex flex-col items-end gap-1">
                <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold font-mono ${rc}`}>{m.result} {m.score}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );

  const renderDetail = () => {
    if (analysisLoading) {
      return <div className="flex items-center justify-center h-full"><Loader2 className="h-6 w-6 animate-spin text-brand-600" /></div>;
    }
    if (!analysis) {
      return (
        <div className="flex items-center justify-center h-full text-sm text-slate-400">
          Select a match to view details
        </div>
      );
    }

    const mc = analysis.match_context || {};
    const homeTeam = mc.home_team || 'Home';
    const awayTeam = mc.away_team || 'Away';
    const hs = analysis.team_stats?.home || {};
    const as = analysis.team_stats?.away || {};
    const avgScore = allPlayerRatings.length > 0 ? allPlayerRatings.reduce((s, p) => s + (p.overall_score || 0), 0) / allPlayerRatings.length : 0;
    const avgColor = avgScore >= 7.5 ? 'text-emerald-600' : avgScore >= 7.0 ? 'text-blue-600' : avgScore >= 6.5 ? 'text-amber-600' : 'text-red-500';

    const filteredTimeline = !analysis?.timeline ? [] :
      [...analysis.timeline].sort((a, b) => (a.period - b.period) || (a.minute - b.minute));

    return (
      <div className="p-5 space-y-5 overflow-y-auto h-full" style={{ scrollbarWidth: 'thin' }}>
        {/* ═══ MATCH BANNER ═══ */}
        <div className="rounded-xl border border-slate-200 bg-gradient-to-br from-slate-50 to-white shadow-sm p-4 relative overflow-hidden">
          <div className="absolute -top-10 -right-10 w-[200px] h-[200px] rounded-full bg-emerald-500/5" />
          <div className="flex items-center gap-3 relative z-10">
            <div className="w-9 h-9 rounded-lg flex items-center justify-center text-[9px] font-black shrink-0"
              style={{ background: 'linear-gradient(135deg, #003f7f, #a50044)', color: '#fff' }}>
              {homeTeam.slice(0, 3).toUpperCase()}
            </div>
            <div>
              <div className="text-sm font-bold text-slate-800">{homeTeam}</div>
              <div className="text-[10px] text-slate-500">{mc.stadium}</div>
            </div>
            <div className="text-2xl font-black font-mono px-3 py-1 rounded-lg"
              style={{ background: 'linear-gradient(135deg, #22c55e, #58A6FF)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              {mc.home_score}–{mc.away_score}
            </div>
            <div className="text-right">
              <div className="text-sm font-bold text-slate-800">{awayTeam}</div>
              <div className="text-[10px] text-slate-500">{mc.match_date} &middot; Week {mc.match_week}</div>
            </div>
            <div className="w-9 h-9 rounded-lg flex items-center justify-center text-[9px] font-black bg-slate-200 text-slate-600 shrink-0">
              {awayTeam.slice(0, 3).toUpperCase()}
            </div>
          </div>
          <div className="flex gap-5 mt-3 relative z-10">
            <div className="text-center">
              <div className="text-base font-black font-mono text-blue-600">{possession}%</div>
              <div className="text-[9px] text-slate-500">Possession</div>
            </div>
            <div className="text-center">
              <div className="text-base font-black font-mono text-rose-600">{totalShots}</div>
              <div className="text-[9px] text-slate-500">Total Shots</div>
            </div>
            <div className="text-center">
              <div className="text-base font-black font-mono text-amber-600">{totalXg.toFixed(2)}</div>
              <div className="text-[9px] text-slate-500">Total xG</div>
            </div>
            <div className="text-center">
              <div className="text-base font-black font-mono text-emerald-600">{hs.goals || 0} – {as.goals || 0}</div>
              <div className="text-[9px] text-slate-500">Goals</div>
            </div>
            <div className="text-center">
              <div className="text-base font-black font-mono text-slate-400">{mc.match_id}</div>
              <div className="text-[9px] text-slate-500">Match ID</div>
            </div>
          </div>
        </div>

        {/* ═══ MATCH ANALYSIS ═══ */}
        {analysis.match_analysis && (
          <div className="rounded-xl border border-slate-200 bg-white shadow-sm p-4">
            <div className="flex items-center gap-3 mb-3">
              <span className="text-xs font-bold text-slate-700">Match Analysis — Barcelona</span>
              {(() => {
                const r = analysis.match_analysis.result;
                const rc = r === 'W' ? 'bg-emerald-100 text-emerald-700 border-emerald-200' :
                           r === 'L' ? 'bg-red-100 text-red-700 border-red-200' :
                           'bg-amber-100 text-amber-700 border-amber-200';
                const rl = r === 'W' ? 'WIN' : r === 'L' ? 'LOSS' : 'DRAW';
                return <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${rc}`}>{rl}</span>;
              })()}
              <span className="text-[10px] font-mono text-slate-400 ml-auto">
                {analysis.match_analysis.barcelona_goals} – {analysis.match_analysis.opponent_goals}
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div className="text-[10px] font-semibold text-slate-600 uppercase tracking-wider mb-2">Key Factors</div>
                <ul className="space-y-1">
                  {analysis.match_analysis.reasons.map((r, i) => (
                    <li key={i} className="text-[11px] text-slate-700 flex items-start gap-1.5">
                      <span className="text-slate-400 mt-0.5 shrink-0">•</span>
                      <span>{r}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <div className="text-[10px] font-semibold text-slate-600 uppercase tracking-wider mb-2">Best &amp; Worst</div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="rounded-lg border border-emerald-200 bg-emerald-50/50 p-2.5">
                    <div className="text-[8px] text-slate-500 uppercase font-semibold mb-1">Best</div>
                    <div className="text-[11px] font-bold text-slate-800 truncate">{analysis.match_analysis.best_player?.player_name}</div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-[10px] font-mono text-emerald-600 font-bold">
                        {analysis.match_analysis.best_player?.position_kpi?.toFixed(1) || analysis.match_analysis.best_player?.overall_score?.toFixed(1)}
                      </span>
                      <span className="text-[8px] text-slate-400">{analysis.match_analysis.best_player?.position_group}</span>
                    </div>
                  </div>
                  <div className="rounded-lg border border-red-200 bg-red-50/50 p-2.5">
                    <div className="text-[8px] text-slate-500 uppercase font-semibold mb-1">Worst</div>
                    <div className="text-[11px] font-bold text-slate-800 truncate">{analysis.match_analysis.worst_player?.player_name}</div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-[10px] font-mono text-red-600 font-bold">
                        {analysis.match_analysis.worst_player?.position_kpi?.toFixed(1) || analysis.match_analysis.worst_player?.overall_score?.toFixed(1)}
                      </span>
                      <span className="text-[8px] text-slate-400">{analysis.match_analysis.worst_player?.position_group}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ═══ POSSESSION BAR ═══ */}
        {(() => {
          const barcaSide = analysis.match_analysis?.barcelona_side || 'home';
          const oppSide = barcaSide === 'home' ? 'away' : 'home';
          const barcaName = mc?.[`${barcaSide}_team`] || 'Barcelona';
          const oppName = mc?.[`${oppSide}_team`] || 'Opponent';
          return (
            <div>
              <div className="flex justify-between text-[9px] text-slate-500 mb-1">
                <span className="font-semibold text-emerald-700">{barcaName} {possession}%</span>
                <span>Possession</span>
                <span>{100 - possession}% {oppName}</span>
              </div>
              <div className="h-2.5 bg-slate-200 rounded-full overflow-hidden flex">
                <div className="h-full rounded-full" style={{ width: `${possession}%`, background: 'linear-gradient(90deg, #22c55e, #059669)' }} />
              </div>
            </div>
          );
        })()}

        {/* ═══ KPI CARDS ═══ */}
        {(() => {
          const posAvg = allPlayerRatings.length > 0
            ? allPlayerRatings.reduce((s, p) => s + (p.position_kpi || p.overall_score || 0), 0) / allPlayerRatings.length
            : 0;
          const posAvgColor = posAvg >= 7.5 ? 'text-violet-600' : posAvg >= 7.0 ? 'text-violet-500' : posAvg >= 6.5 ? 'text-violet-400' : 'text-red-500';
          return (
            <div className="grid grid-cols-6 gap-2">
              {[
                { label: 'Squad ML', value: avgScore.toFixed(1), color: avgColor },
                { label: 'Pos. Rating', value: posAvg.toFixed(1), color: posAvgColor },
                { label: 'Possession', value: `${possession}%`, color: 'text-blue-600' },
                { label: 'Total Shots', value: totalShots, color: 'text-rose-600' },
                { label: 'Total xG', value: totalXg.toFixed(2), color: 'text-amber-600' },
                { label: 'Goals', value: `${hs.goals || 0} – ${as.goals || 0}`, color: 'text-emerald-600' },
              ].map((k, i) => (
                <div key={i} className="rounded-lg border border-slate-200 bg-white/80 p-3 text-center">
                  <div className={`text-base font-black font-mono leading-none ${k.color}`}>{k.value}</div>
                  <div className="text-[9px] text-slate-500 mt-1">{k.label}</div>
                </div>
              ))}
            </div>
          );
        })()}

        {/* ═══ TACTICAL BOARD ═══ */}
        <TacticalBoardSection analysis={analysis} width={700} height={400}
          onPlayerClick={handlePlayerClick} selectedPlayerId={selectedPitchPlayerId} allPlayers={allPlayerRatings} />

        {/* ═══ TEAM STATS COMPARISON ═══ */}
        <TeamStatsTable analysis={analysis} />

        {/* ═══ xG FLOW ═══ */}
        {xgFlowData.length > 0 && (
          <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="px-4 py-2.5 border-b border-slate-100 flex justify-between items-center">
              <span className="text-xs font-bold text-slate-700">Cumulative xG Flow</span>
              <span className="text-[10px] text-slate-400">Total: {totalXg.toFixed(2)} xG</span>
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
                <span>0&rsquo;</span><span>15&rsquo;</span><span>30&rsquo;</span><span>45&rsquo; HT</span><span>60&rsquo;</span><span>75&rsquo;</span><span>90&rsquo;</span>
              </div>
            </div>
          </div>
        )}

        {/* ═══ PLAYER RATINGS — TWO COLUMNS ═══ */}
        {(() => {
          const barcaSide = analysis.match_analysis?.barcelona_side || 'home';
          const oppSide = barcaSide === 'home' ? 'away' : 'home';
          const barcaPlayers = analysis.players?.[barcaSide] || [];
          const oppPlayers = analysis.players?.[oppSide] || [];
          const barcaName = barcaSide === 'home' ? (analysis.match_context?.home_team || 'Barcelona') : (analysis.match_context?.away_team || 'Barcelona');
          const oppName = oppSide === 'home' ? (analysis.match_context?.home_team || 'Opponent') : (analysis.match_context?.away_team || 'Opponent');

          const renderColumn = (players, teamName, isBarca) => (
            <div className="flex-1 min-w-0">
              <div className={`px-3 py-1.5 border-b border-slate-100 text-[10px] font-semibold flex items-center gap-2 ${isBarca ? 'bg-emerald-50/50' : 'bg-blue-50/50'}`}>
                <span className={`w-2 h-2 rounded-full ${isBarca ? 'bg-emerald-500' : 'bg-blue-500'}`} />
                {teamName}
                <span className="text-[9px] text-slate-400 ml-auto">{players.length} players</span>
              </div>
              <div className="p-2 space-y-1.5">
                {players.sort((a, b) => (b.overall_score || 0) - (a.overall_score || 0)).map(p => {
                  const sc = (p.overall_score || 0) >= 7.5 ? 'text-emerald-600' :
                             (p.overall_score || 0) >= 7.0 ? 'text-blue-600' :
                             (p.overall_score || 0) >= 6.5 ? 'text-amber-600' : 'text-red-500';
                  const pc = (p.position_kpi || 0) >= 7.5 ? 'text-violet-600' :
                             (p.position_kpi || 0) >= 7.0 ? 'text-violet-500' :
                             (p.position_kpi || 0) >= 6.5 ? 'text-violet-400' : 'text-red-500';
                  return (
                    <div key={p.player_id} className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50/50 p-2 transition-colors hover:border-emerald-300">
                      <div className="w-7 h-7 rounded-full flex items-center justify-center text-[8px] font-bold shrink-0"
                        style={{ background: '#1a6be022', color: '#1a6be0', border: '1.5px solid #1a6be044' }}>
                        {initials(p.player_name)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-[10px] font-bold text-slate-700 truncate">{p.player_name}</div>
                        <div className="text-[9px] text-slate-500">{p.position_group}</div>
                      </div>
                      <div className="flex flex-col items-end gap-0.5">
                        <span className={`font-mono text-sm font-black leading-none shrink-0 ${sc}`}>{p.overall_score?.toFixed(1)}</span>
                        <span className={`font-mono text-[10px] font-bold leading-none ${pc}`}>
                          {p.position_kpi != null ? p.position_kpi.toFixed(1) : '\u2014'}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );

          return (
            <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
              <div className="px-4 py-2.5 border-b border-slate-100">
                <span className="text-xs font-bold text-slate-700">Player Ratings — This Match</span>
              </div>
              <div className="flex divide-x divide-slate-200">
                <div className="flex-1 min-w-0 border-r border-slate-200">
                  {renderColumn(barcaPlayers, barcaName, true)}
                </div>
                <div className="flex-1 min-w-0">
                  {renderColumn(oppPlayers, oppName, false)}
                </div>
              </div>
            </div>
          );
        })()}

        {/* ═══ PLAYER STATS TABLE ═══ */}
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="px-4 py-2.5 border-b border-slate-100">
            <span className="text-xs font-bold text-slate-700">Computed Features &amp; KPI Ratings</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-xs" style={{ minWidth: 700 }}>
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-[9px] text-slate-500 font-bold uppercase tracking-wider">
                  <th className="text-left py-2 px-2.5">Player</th>
                  <th className="text-center py-2 px-2.5">Team</th>
                  <th className="text-center py-2 px-2.5">ML</th>
                  <th className="text-center py-2 px-2.5">Pos.</th>
                  <th className="text-center py-2 px-2.5">Off.</th>
                  <th className="text-center py-2 px-2.5">Def.</th>
                  <th className="text-center py-2 px-2.5">Poss.</th>
                  <th className="text-center py-2 px-2.5">Event</th>
                  <th className="text-center py-2 px-2.5">VAEP</th>
                </tr>
              </thead>
              <tbody>
                {allPlayerRatings.map(p => (
                  <tr key={p.player_id} className="border-b border-slate-100 hover:bg-sky-50/50 cursor-pointer transition-colors">
                    <td className="py-2 px-2.5">
                      <div className="flex items-center gap-1.5">
                        <div className="w-6 h-6 rounded-full flex items-center justify-center text-[7px] font-bold shrink-0"
                          style={{ background: '#1a6be022', color: '#1a6be0', border: '1.5px solid #1a6be044' }}>
                          {initials(p.player_name)}
                        </div>
                        <div>
                          <div className="text-[11px] font-bold text-slate-800">{p.player_name}</div>
                          <div className="text-[9px] text-slate-500">{p.position_group}</div>
                        </div>
                      </div>
                    </td>
                    <td className="text-center text-[9px] text-slate-500 font-mono">
                      {p.team_name ? p.team_name.slice(0, 3).toUpperCase() : ''}
                    </td>
                    <td className="text-center">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold font-mono ${scoreChipClass(p.overall_score)}`}>
                        {p.overall_score?.toFixed(1)}
                      </span>
                    </td>
                    <td className="text-center">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold font-mono ${scoreChipClass(p.position_kpi || p.overall_score)}`}
                        style={{ color: '#7c3aed', background: '#7c3aed22' }}>
                        {p.position_kpi != null ? p.position_kpi.toFixed(1) : '\u2014'}
                      </span>
                    </td>
                    <td className="text-center font-mono text-[11px] text-slate-700">
                      {p.offensive_contribution != null ? p.offensive_contribution.toFixed(2) : '\u2014'}
                    </td>
                    <td className="text-center font-mono text-[11px] text-slate-700">
                      {p.defensive_contribution != null ? p.defensive_contribution.toFixed(2) : '\u2014'}
                    </td>
                    <td className="text-center font-mono text-[11px] text-slate-700">
                      {p.possession_contribution != null ? p.possession_contribution.toFixed(2) : '\u2014'}
                    </td>
                    <td className="text-center font-mono text-[11px] text-slate-700">
                      {p.event_value_score != null ? p.event_value_score.toFixed(2) : '\u2014'}
                    </td>
                    <td className="text-center font-mono text-xs font-bold text-amber-600">
                      {p.vaep_rating != null ? p.vaep_rating.toFixed(2) : '\u2014'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

          {/* ═══ EVENT TIMELINE — HORIZONTAL FLOWLINE ═══ */}
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="px-4 py-2.5 border-b border-slate-100 flex justify-between items-center">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-slate-700">Match Flow</span>
              <button
                onClick={() => setKeyEventsOnly(v => !v)}
                className={`text-[9px] font-semibold px-2 py-0.5 rounded-full border transition-all ${
                  keyEventsOnly
                    ? 'bg-brand-50 text-brand-600 border-brand-200'
                    : 'bg-slate-50 text-slate-400 border-slate-200'
                }`}
              >
                {keyEventsOnly ? 'Key Events' : 'All Events'}
              </button>
            </div>
            <span className="text-[10px] text-slate-400">{filteredTimeline.length} events</span>
          </div>
          {filteredTimeline.length === 0 ? (
            <div className="p-6 text-center text-[11px] text-slate-400">No events available</div>
          ) : (() => {
            const barcaTeam = mc[`${analysis.match_analysis?.barcelona_side || 'home'}_team`] || 'Barcelona';
            const DOT = 5; // dot diameter
            const GAP = 3; // gap between stacked dots
            const MAX_STACK = 10; // max dots per side per minute before "+N"

            // Group events by minute (filtered by keyEventsOnly toggle)
            const byMinute = {};
            const timelineForFlow = keyEventsOnly ? filteredTimeline.filter(isKeyEvent) : filteredTimeline;
            timelineForFlow.forEach(e => {
              const m = e.minute;
              if (!byMinute[m]) byMinute[m] = [];
              byMinute[m].push(e);
            });

            // Detect goals: shot + outcome=Goal
            const goals = timelineForFlow.filter(e => e.event_type?.toLowerCase() === 'shot' && e.outcome === 'Goal');

            const normEventType = (raw) => {
              if (!raw) return 'pass';
              const lc = raw.toLowerCase();
              if (lc.includes('foul')) return 'foul';
              if (lc.includes('ball receipt')) return 'ball receipt*';
              if (lc.includes('ball recovery')) return 'ball recovery';
              if (lc.includes('goal keeper')) return 'goal keeper';
              if (lc.includes('dribbled past')) return 'dispossessed';
              if (lc === 'error') return 'error';
              if (lc === 'shield') return 'shield';
              if (lc === 'miscontrol') return 'miscontrol';
              return lc;
            };

            const lineH = 170;
            const pxPerMin = 14;
            const totalW = 95 * pxPerMin + 40;

            return (
              <div className="overflow-x-auto" style={{ scrollbarWidth: 'thin' }}>
                <div className="relative select-none" style={{ height: lineH, minWidth: totalW, padding: '0 20px' }}>
                  {/* ── Main horizontal line ── */}
                  <div className="absolute left-5 right-5 top-1/2 h-[2px] bg-slate-300 rounded-full" style={{ top: '50%' }} />

                  {/* ── Density flow bars (background) ── */}
                  {Array.from({ length: 95 }, (_, i) => {
                    const evs = byMinute[i] || [];
                    if (evs.length === 0) return null;
                    const barcaCount = evs.filter(e => e.team === barcaTeam).length;
                    const oppCount = evs.length - barcaCount;
                    const maxH = 32;
                    const barcaH = Math.min(barcaCount / 8, 1) * maxH;
                    const oppH = Math.min(oppCount / 8, 1) * maxH;
                    const l = 20 + i * pxPerMin;
                    return (
                      <div key={`bar-${i}`}>
                        {barcaCount > 0 && (
                          <div className="absolute bottom-1/2 rounded-t-sm opacity-30" style={{
                            left: l, width: pxPerMin - 2, height: barcaH,
                            bottom: '50%', background: '#22c55e',
                          }} />
                        )}
                        {oppCount > 0 && (
                          <div className="absolute top-1/2 rounded-b-sm opacity-30" style={{
                            left: l, width: pxPerMin - 2, height: oppH,
                            top: '50%', background: '#58A6FF',
                          }} />
                        )}
                      </div>
                    );
                  })}

                  {/* ── Minute markers ── */}
                  {[0,5,10,15,20,25,30,35,40,45,50,55,60,65,70,75,80,85,90].map(m => {
                    const l = 20 + m * pxPerMin;
                    const isHT = m === 45;
                    return (
                      <div key={`m-${m}`} className="absolute" style={{ left: l, top: '50%', transform: 'translate(-50%, -50%)' }}>
                        <div className={`mx-auto ${isHT ? 'h-4 w-0.5 bg-slate-400' : 'h-2 w-px bg-slate-300'}`} />
                        <span className={`block text-center text-[7px] font-mono ${isHT ? 'font-bold text-slate-500' : 'text-slate-400'}`} style={{ marginTop: 3 }}>
                          {isHT ? 'HT' : `${m}'`}
                        </span>
                      </div>
                    );
                  })}

                  {/* ── Goal markers (always visible) ── */}
                  {goals.map((g, i) => {
                    const isBarca = g.team === barcaTeam;
                    const l = 20 + Math.min(g.minute, 90) * pxPerMin;
                    return (
                      <div key={`goal-${i}`} className="absolute z-20" style={{
                        left: l, top: isBarca ? 'calc(50% - 7px)' : 'calc(50% + 7px)',
                        transform: isBarca ? 'translate(-50%, -100%)' : 'translate(-50%, 0)',
                      }}>
                        <div className={`flex flex-col items-center gap-0.5 ${isBarca ? '' : 'flex-col-reverse'}`}>
                          <span className="text-[16px] drop-shadow-md" style={{ lineHeight: 1 }}>{'\u26BD'}</span>
                          <span className={`text-[8px] font-bold whitespace-nowrap px-1.5 py-0.5 rounded ${isBarca ? 'bg-emerald-100 text-emerald-700' : 'bg-blue-100 text-blue-700'}`}>
                            {g.player_name}
                          </span>
                          <span className="text-[7px] font-mono font-bold text-slate-500">{g.minute}'</span>
                        </div>
                      </div>
                    );
                  })}

                  {/* ── Event dots ── */}
                  {Object.entries(byMinute).map(([minStr, evs]) => {
                    const min = Number(minStr);
                    const l = 20 + Math.min(min, 90) * pxPerMin;
                    const barcaEvs = evs.filter(e => e.team === barcaTeam);
                    const oppEvs = evs.filter(e => e.team !== barcaTeam);

                    const renderStack = (events, isBarca) => {
                      const slice = events.slice(0, MAX_STACK);
                      const overflow = events.length - MAX_STACK;
                      return (
                        <div className={`absolute flex flex-col items-center ${isBarca ? 'bottom-full mb-1' : 'top-full mt-1'}`}
                          style={{ left: '50%', transform: 'translateX(-50%)' }}>
                          {slice.map((e, j) => {
                            const et = normEventType(e.event_type);
                            const isGoal = e.outcome === 'Goal' && et === 'shot';
                            const dt = isGoal ? 'goal' : et;
                            const ec = EVENT_COLORS[dt] || '#8B949E';
                            const isKey = ['shot','foul','block','clearance','duel','interception','miscontrol','error','goal keeper'].includes(et);
                            const size = isGoal ? 8 : (isKey ? 6 : DOT);
                            const d = isGoal ? 0 : GAP;
                            return (
                              <div key={j} className="group relative" style={{ marginTop: isBarca ? -d : 0, marginBottom: isBarca ? 0 : -d }}>
                                <div className="rounded-full border transition-all duration-150 hover:scale-150 cursor-pointer"
                                  style={{
                                    width: size, height: size,
                                    background: isBarca ? `${ec}88` : `${ec}66`,
                                    borderColor: ec,
                                    borderWidth: isGoal ? 2 : 1.5,
                                  }}>
                                  {/* Tooltip */}
                                  <div className={`absolute pointer-events-none z-30 whitespace-nowrap transition-all duration-100 opacity-0 group-hover:opacity-100 ${isBarca ? 'bottom-full mb-1.5' : 'top-full mt-1.5'} left-1/2 -translate-x-1/2`}>
                                    <div className="bg-slate-800 text-white text-[8px] rounded-lg px-2 py-1.5 shadow-xl flex items-center gap-1.5 leading-tight">
                                      <span>{EVENT_ICONS[dt] || '\u2022'}</span>
                                      <span className="font-semibold">{EVENT_LABELS[dt] || e.event_type}</span>
                                      <span className="w-px h-2.5 bg-white/20" />
                                      <span className="truncate max-w-[80px]">{e.player_name}</span>
                                      {e.outcome && !isGoal && (
                                        <>
                                          <span className="w-px h-2.5 bg-white/20" />
                                          <span>{e.outcome}</span>
                                        </>
                                      )}
                                      {e.xg != null && (et === 'shot') && (
                                        <>
                                          <span className="w-px h-2.5 bg-white/20" />
                                          <span className="font-mono">{e.xg.toFixed(2)}</span>
                                        </>
                                      )}
                                    </div>
                                    <div className={`absolute left-1/2 -translate-x-1/2 w-1.5 h-1.5 bg-slate-800 rotate-45 ${isBarca ? 'top-full -mt-[3px]' : 'bottom-full mb-[3px]'}`} />
                                  </div>
                                </div>
                              </div>
                            );
                          })}
                          {overflow > 0 && (
                            <span className={`text-[6px] font-mono text-slate-400 leading-tight ${isBarca ? '-mt-0.5' : '-mb-0.5'}`}>
                              +{overflow}
                            </span>
                          )}
                        </div>
                      );
                    };

                    return (
                      <div key={min} className="absolute" style={{ left: l, top: '50%', transform: 'translate(-50%, -50%)', zIndex: 5 }}>
                        {barcaEvs.length > 0 && renderStack(barcaEvs, true)}
                        {oppEvs.length > 0 && renderStack(oppEvs, false)}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })()}
        </div>
      </div>
    );
  };

  return (
    <div className="flex h-[calc(100vh-120px)] rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      {renderMatchList()}
      <div className="flex-1 overflow-hidden bg-gradient-to-br from-slate-50/50 to-white">
        {renderDetail()}
      </div>
    </div>
  );
};

export default MatchLog;