import React, { useState, useEffect, useMemo } from 'react';
import {
  Users, TrendingUp, Target, Crosshair, Footprints, Eye,
  Shield, Zap, Repeat, Gauge, Swords, ArrowLeftRight,
  Search, Filter, ChevronDown, ChevronUp, BarChart3,
  Activity, HandMetal,
} from 'lucide-react';
import { useAppContext } from '../context/AppContext';
import { SeasonAPI, PositionStatsAPI } from '../api';

const POSITIONS = [
  { id: 'Attacker',    label: 'FW', icon: Target,    color: 'from-rose-500 to-pink-600' },
  { id: 'Midfielder',  label: 'MF', icon: Repeat,    color: 'from-cyan-500 to-blue-600' },
  { id: 'Defender',    label: 'DF', icon: Shield,    color: 'from-emerald-500 to-teal-600' },
  { id: 'GK',          label: 'GK', icon: HandMetal, color: 'from-violet-500 to-purple-600' },
];

const POSITION_KPI_META = {
  Attacker: [
    { key: 'goals_per90',       label: 'Goals p90',        desc: 'Goals scored per 90 minutes',                      icon: Crosshair,  unit: 'p90' },
    { key: 'xg_overperformance', label: 'xG Overperform',  desc: 'Actual goals minus expected goals',                  icon: TrendingUp, unit: '' },
    { key: 'assists_per90',     label: 'Assists p90',      desc: 'Assists per 90 minutes',                            icon: Eye,        unit: 'p90' },
    { key: 'shot_accuracy',     label: 'Shot Accuracy',    desc: 'Percentage of shots on target',                     icon: Target,     unit: '%' },
    { key: 'successful_dribbles_per90', label: 'Dribbles p90', desc: 'Successful dribbles per 90 minutes',             icon: Footprints, unit: 'p90' },
    { key: 'chances_created_per90',     label: 'Chances p90',   desc: 'Key passes leading to shots per 90',            icon: Zap,        unit: 'p90' },
    { key: 'progressive_carries_per90', label: 'Prog Carries p90', desc: 'Progressive ball carries per 90 minutes',   icon: ArrowLeftRight, unit: 'p90' },
  ],
  Midfielder: [
    { key: 'pass_accuracy',             label: 'Pass Acc',     desc: 'Pass completion percentage',                   icon: Target,      unit: '%' },
    { key: 'total_passes_per90',        label: 'Passes p90',   desc: 'Total passes per 90 minutes',                   icon: Repeat,      unit: 'p90' },
    { key: 'progressive_passes_per90',  label: 'Prog Pass p90', desc: 'Line-breaking passes per 90 minutes',          icon: ArrowLeftRight, unit: 'p90' },
    { key: 'pressure_regains_per90',    label: 'Regains p90',  desc: 'Ball regains after pressure per 90',            icon: Gauge,       unit: 'p90' },
    { key: 'ball_receipts_per90',       label: 'Receipts p90', desc: 'Times receiving the ball per 90 minutes',       icon: Activity,    unit: 'p90' },
    { key: 'chances_created_per90',     label: 'Chances p90',  desc: 'Key passes leading to shots per 90',            icon: Zap,         unit: 'p90' },
    { key: 'progressive_carries_per90', label: 'Carries p90',  desc: 'Progressive carries per 90 minutes',            icon: Footprints,  unit: 'p90' },
  ],
  Defender: [
    { key: 'defensive_actions_per90',   label: 'Def Actions p90', desc: 'Interceptions + clearances + blocks p90',    icon: Shield,      unit: 'p90' },
    { key: 'pass_accuracy',             label: 'Pass Acc',        desc: 'Pass completion percentage',                 icon: Target,      unit: '%' },
    { key: 'pressure_regains_per90',    label: 'Regains p90',     desc: 'Ball regains after pressure per 90',         icon: Gauge,       unit: 'p90' },
    { key: 'progressive_carries_per90', label: 'Carries p90',     desc: 'Progressive carries per 90 minutes',         icon: Footprints,  unit: 'p90' },
    { key: 'duels_per90',               label: 'Duels p90',       desc: 'Aerial and ground duels per 90 minutes',     icon: Swords,      unit: 'p90' },
    { key: 'progressive_passes_per90',  label: 'Prog Pass p90',   desc: 'Line-breaking passes per 90 minutes',        icon: ArrowLeftRight, unit: 'p90' },
  ],
  GK: [
    { key: 'save_pct',                 label: 'Save %',          desc: 'Saves as percentage of shots on target faced', icon: Shield,      unit: '%' },
    { key: 'goals_conceded_per90',     label: 'Goals Conceded p90', desc: 'Goals conceded per 90 minutes',            icon: Crosshair,   unit: 'p90' },
    { key: 'goals_prevented',          label: 'Goals Prevented', desc: 'xG saved vs actual goals conceded',           icon: TrendingUp,  unit: '' },
    { key: 'pass_accuracy',            label: 'Pass Acc',        desc: 'Distribution accuracy',                        icon: Target,      unit: '%' },
    { key: 'progressive_passes_per90', label: 'Prog Pass p90',   desc: 'Progressive passes per 90 minutes',           icon: ArrowLeftRight, unit: 'p90' },
  ],
};

const POSITION_STAT_COLS = {
  Attacker: ['goals_per90','assists_per90','shots_per90','shot_accuracy','dribbles_per90','chances_created_per90','progressive_carries_per90'],
  Midfielder: ['passes_per90','pass_accuracy','progressive_passes_per90','pressure_regains_per90','ball_receipts_per90','chances_created_per90','progressive_carries_per90'],
  Defender: ['defensive_actions_per90','pass_accuracy','pressure_regains_per90','progressive_carries_per90','duels_per90','progressive_passes_per90'],
  GK: ['save_pct','goals_conceded_per90','saves_per90','pass_accuracy','progressive_passes_per90'],
};

const STAT_LABELS = {
  goals_per90: 'Goals p90', assists_per90: 'Assists p90', shots_per90: 'Shots p90',
  shot_accuracy: 'Shot Acc %', dribbles_per90: 'Dribbles p90',
  chances_created_per90: 'Chances p90', progressive_carries_per90: 'Carries p90',
  passes_per90: 'Passes p90', pass_accuracy: 'Pass Acc %',
  progressive_passes_per90: 'Prog Pass p90', pressure_regains_per90: 'Regains p90',
  ball_receipts_per90: 'Receipts p90', defensive_actions_per90: 'Def Act p90',
  duels_per90: 'Duels p90', save_pct: 'Save %', goals_conceded_per90: 'GC p90',
  saves_per90: 'Saves p90', goals_prevented: 'G Prevented',
};

function kpiBarColor(score) {
  if (score === null || score === undefined) return 'bg-slate-300';
  if (score >= 8) return 'bg-gradient-to-r from-amber-400 to-amber-500';
  if (score >= 6) return 'bg-gradient-to-r from-emerald-400 to-emerald-500';
  if (score >= 4) return 'bg-gradient-to-r from-amber-400 to-yellow-500';
  if (score >= 2) return 'bg-gradient-to-r from-orange-400 to-orange-500';
  return 'bg-gradient-to-r from-red-400 to-red-500';
}

function kpiBadgeColor(label) {
  switch (label) {
    case 'Exceptional':    return 'bg-amber-100 text-amber-800 border-amber-300';
    case 'Excellent':      return 'bg-emerald-100 text-emerald-800 border-emerald-300';
    case 'Good':           return 'bg-blue-100 text-blue-800 border-blue-300';
    case 'Average':        return 'bg-slate-100 text-slate-700 border-slate-300';
    case 'Below Average':  return 'bg-orange-100 text-orange-800 border-orange-300';
    case 'Poor':           return 'bg-red-100 text-red-800 border-red-300';
    default:               return 'bg-slate-100 text-slate-600 border-slate-200';
  }
}

export default function PositionDashboard({ onSelectPlayer }) {
  const { selectedSeason, setSelectedSeason } = useAppContext();
  const [activePos, setActivePos] = useState('Attacker');
  const [season, setSeason] = useState(selectedSeason || '2015/2016');
  const [seasonOptions, setSeasonOptions] = useState([]);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sortKey, setSortKey] = useState('kpi');
  const [sortAsc, setSortAsc] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [minMatches, setMinMatches] = useState(1);

  useEffect(() => {
    SeasonAPI.listSeasons()
      .then(res => { if (res?.seasons) setSeasonOptions(res.seasons); })
      .catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    setError(null);
    PositionStatsAPI.getPositionStats(season, activePos)
      .then(d => { setData(d); setLoading(false); })
      .catch(e => { setError(String(e)); setLoading(false); });
  }, [season, activePos]);

  const filteredPlayers = useMemo(() => {
    if (!data?.players) return [];
    return data.players
      .filter(p => {
        if (searchTerm) return p.player_name.toLowerCase().includes(searchTerm.toLowerCase());
        return true;
      })
      .filter(p => (p.matches_played || 0) >= minMatches)
      .sort((a, b) => {
        let va, vb;
        if (sortKey === 'kpi') { va = a.avg_position_kpi || 0; vb = b.avg_position_kpi || 0; }
        else if (sortKey === 'name') { va = a.player_name; vb = b.player_name; return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va); }
        else if (sortKey === 'matches') { va = a.matches_played || 0; vb = b.matches_played || 0; }
        else if (sortKey === 'minutes') { va = a.total_minutes || 0; vb = b.total_minutes || 0; }
        else { va = a.kpi_dimensions?.[sortKey] ?? 0; vb = b.kpi_dimensions?.[sortKey] ?? 0; }
        return sortAsc ? va - vb : vb - va;
      });
  }, [data, sortKey, sortAsc, searchTerm, minMatches]);

  const handleSort = (key) => {
    if (sortKey === key) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(false); }
  };

  const posMeta = POSITIONS.find(p => p.id === activePos);
  const kpiMetas = POSITION_KPI_META[activePos] || [];
  const statCols = POSITION_STAT_COLS[activePos] || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className={`rounded-2xl bg-gradient-to-r ${posMeta?.color || 'from-slate-700 to-slate-800'} p-6 text-white shadow-xl`}>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-white/15 p-2.5 backdrop-blur">
              {posMeta && <posMeta.icon className="h-6 w-6" />}
            </div>
            <div>
              <h1 className="text-2xl font-bold">{activePos === 'GK' ? 'Goalkeeper' : activePos} Performance Dashboard</h1>
              <p className="text-sm text-white/70">{season} &middot; {data?.player_count || 0} players</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={season}
              onChange={e => { setSeason(e.target.value); if (setSelectedSeason) setSelectedSeason(e.target.value); }}
              className="rounded-lg border border-white/20 bg-white/10 px-3 py-1.5 text-sm text-white backdrop-blur"
            >
              {seasonOptions.map(s => <option key={s.label || s} value={s.label || s}>{s.label || s}</option>)}
            </select>
          </div>
        </div>
      </div>

      {/* Position Tabs */}
      <div className="flex gap-3" role="tablist">
        {POSITIONS.map(p => (
          <button
            key={p.id}
            onClick={() => setActivePos(p.id)}
            className={`inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-medium transition ${
              activePos === p.id
                ? `bg-gradient-to-r ${p.color} text-white shadow-lg`
                : 'surface text-slate-600 hover:bg-slate-100'
            }`}
            role="tab"
            aria-selected={activePos === p.id}
          >
            <p.icon className="h-4 w-4" />
            {p.label}
          </button>
        ))}
      </div>

      {/* Search + Filter */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search players..."
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            className="w-full rounded-lg border border-slate-200 bg-white py-2 pl-9 pr-3 text-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>
        <div className="flex items-center gap-2 text-sm text-slate-600">
          <Filter className="h-4 w-4" />
          <span>Min matches:</span>
          <select
            value={minMatches}
            onChange={e => setMinMatches(Number(e.target.value))}
            className="rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-sm"
          >
            {[1, 2, 3, 5, 10].map(n => <option key={n} value={n}>{n}+</option>)}
          </select>
        </div>
        {loading && <div className="text-sm text-slate-500">Loading...</div>}
        {error && <div className="text-sm text-red-500">{error}</div>}
      </div>

      {/* KPI Dimension Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {kpiMetas.map(meta => {
          const avgScore = data?.players?.length
            ? data.players.reduce((s, p) => s + (p.kpi_dimensions?.[meta.key] ?? 0), 0) / data.players.length
            : null;
          const best = data?.players?.length
            ? data.players.reduce((a, b) => ((a.kpi_dimensions?.[meta.key] ?? 0) > (b.kpi_dimensions?.[meta.key] ?? 0) ? a : b))
            : null;
          const bestName = best?.player_name || '—';
          const bestVal = best?.kpi_dimensions?.[meta.key];
          return (
            <div key={meta.key} className="surface overflow-hidden rounded-xl p-4">
              <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-slate-500">
                <meta.icon className="h-3.5 w-3.5" />
                {meta.label}
              </div>
              <div className="text-xs text-slate-400 mb-2">{meta.desc}</div>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-bold text-slate-800">
                  {avgScore !== null ? (meta.unit === '%' ? avgScore.toFixed(1) : avgScore.toFixed(2)) : '—'}
                </span>
                <span className="text-sm text-slate-400">{meta.unit === 'p90' ? '/90' : meta.unit}</span>
              </div>
              <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
                <div
                  className={`h-full rounded-full transition-all ${kpiBarColor(avgScore)}`}
                  style={{ width: `${Math.min(100, ((avgScore || 0) / 10) * 100)}%` }}
                />
              </div>
              {bestName !== '—' && (
                <div className="mt-1 text-xs text-slate-400 truncate">
                  Best: <span className="font-medium text-slate-600">{bestName}</span> {bestVal?.toFixed(2)}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Player Ranking Table */}
      <div className="surface overflow-hidden rounded-xl">
        <div className="border-b border-slate-200 px-5 py-3">
          <h2 className="text-base font-semibold text-slate-800">
            <Users className="mr-2 inline h-4 w-4 text-slate-500" />
            Player Rankings
            <span className="ml-2 text-sm font-normal text-slate-400">({filteredPlayers.length} players)</span>
          </h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase tracking-wider text-slate-500">
                <th className="sticky left-0 bg-slate-50 px-4 py-3">
                  <button onClick={() => handleSort('name')} className="flex items-center gap-1 hover:text-slate-700">
                    Player {sortKey === 'name' && (sortAsc ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />)}
                  </button>
                </th>
                <th className="px-4 py-3">
                  <button onClick={() => handleSort('matches')} className="flex items-center gap-1 hover:text-slate-700">
                    MP {sortKey === 'matches' && (sortAsc ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />)}
                  </button>
                </th>
                <th className="px-4 py-3">
                  <button onClick={() => handleSort('minutes')} className="flex items-center gap-1 hover:text-slate-700">
                    Min {sortKey === 'minutes' && (sortAsc ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />)}
                  </button>
                </th>
                <th className="px-4 py-3">
                  <button onClick={() => handleSort('kpi')} className="flex items-center gap-1 hover:text-slate-700">
                    KPI {sortKey === 'kpi' && (sortAsc ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />)}
                  </button>
                </th>
                {statCols.map(col => (
                  <th key={col} className="px-4 py-3">
                    <button onClick={() => handleSort(col)} className="flex items-center gap-1 whitespace-nowrap hover:text-slate-700">
                      {STAT_LABELS[col] || col} {sortKey === col && (sortAsc ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />)}
                    </button>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredPlayers.length === 0 && (
                <tr><td colSpan={4 + statCols.length} className="px-4 py-8 text-center text-sm text-slate-400">No players found</td></tr>
              )}
              {filteredPlayers.map((p, i) => (
                <tr
                  key={p.player_id}
                  className="border-b border-slate-100 transition hover:bg-slate-50 cursor-pointer"
                  onClick={() => onSelectPlayer && onSelectPlayer(p.player_name, p.player_id)}
                >
                  <td className="sticky left-0 bg-white px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-400 w-5">{i + 1}</span>
                      <span className="font-medium text-slate-800">{p.player_name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{p.matches_played}</td>
                  <td className="px-4 py-3 text-slate-600">{p.total_minutes?.toFixed(0) || '—'}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${kpiBadgeColor(p.avg_position_kpi_label)}`}>
                        {p.avg_position_kpi?.toFixed(2) || '—'}
                      </span>
                      {p.avg_position_kpi_label && (
                        <span className="text-xs text-slate-400">{p.avg_position_kpi_label}</span>
                      )}
                    </div>
                  </td>
                  {statCols.map(col => {
                    const val = p[col] ?? p.kpi_dimensions?.[col] ?? null;
                    return (
                      <td key={col} className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="h-1.5 w-12 overflow-hidden rounded-full bg-slate-200">
                            <div
                              className={`h-full rounded-full ${kpiBarColor(val)}`}
                              style={{ width: `${Math.min(100, ((val || 0) / 10) * 100)}%` }}
                            />
                          </div>
                          <span className="text-xs font-mono text-slate-600">
                            {val !== null ? (typeof val === 'number' ? val.toFixed(val > 10 ? 1 : 2) : val) : '—'}
                          </span>
                        </div>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Squad Comparison Summary */}
      {data?.players?.length > 1 && (
        <div className="surface rounded-xl p-5">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">
            <BarChart3 className="mr-1.5 inline h-4 w-4 text-slate-500" />
            Squad Range: {activePos === 'GK' ? 'Goalkeeper' : activePos} Group
          </h3>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {kpiMetas.slice(0, 6).map(meta => {
              const vals = data.players.map(p => p.kpi_dimensions?.[meta.key]).filter(v => v !== null && v !== undefined);
              if (!vals.length) return null;
              const min = Math.min(...vals);
              const max = Math.max(...vals);
              const avg = vals.reduce((s, v) => s + v, 0) / vals.length;
              const bestName = data.players.reduce((a, b) => ((a.kpi_dimensions?.[meta.key] ?? -1) > (b.kpi_dimensions?.[meta.key] ?? -1) ? a : b)).player_name;
              return (
                <div key={meta.key} className="rounded-lg bg-slate-50 p-3">
                  <div className="mb-1 text-xs font-medium text-slate-500">{meta.label}</div>
                  <div className="flex items-baseline justify-between">
                    <span className="text-lg font-bold text-slate-800">{avg.toFixed(2)}</span>
                    <span className="text-xs text-slate-400">avg</span>
                  </div>
                  <div className="mt-1 flex justify-between text-xs text-slate-400">
                    <span>min: {min.toFixed(2)}</span>
                    <span>max: {max.toFixed(2)}</span>
                  </div>
                  <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
                    <div className="h-full rounded-full bg-brand-500" style={{ width: `${(avg / max) * 100}%` }} />
                  </div>
                  <div className="mt-0.5 text-xs text-slate-400 truncate">Best: {bestName}</div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
