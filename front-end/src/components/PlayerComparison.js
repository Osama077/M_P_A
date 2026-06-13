import React, { useEffect, useState } from 'react';
import {
  BarChart3, GitCompareArrows, Loader2, Search, Users, X
} from 'lucide-react';
import useDebouncedValue from '../hooks/useDebouncedValue';
import {
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  Radar, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import { PlayerAPI } from '../api';
import ErrorAlert from './ErrorAlert';

const PlayerComparison = () => {
  const [players, setPlayers] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [listLoading, setListLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const debouncedSearch = useDebouncedValue(searchTerm, 200);

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

  const togglePlayer = (id) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
    setComparison(null);
  };

  const runComparison = async () => {
    if (selectedIds.length < 2) return;
    setLoading(true);
    setError(null);
    try {
      const res = await PlayerAPI.comparePlayer(selectedIds);
      setComparison(res.comparison || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const PLAYER_COLORS = [
    '#1F4E79', '#E67E22', '#27AE60', '#C0392B',
    '#8E44AD', '#2980B9', '#D35400', '#16A085',
  ];

  const dimensions = ['passing', 'shooting', 'positioning', 'pressing', 'movement', 'physical', 'behavioral'];

  const radarData = comparison
    ? dimensions.map((dim) => ({
        metric: dim.charAt(0).toUpperCase() + dim.slice(1),
        ...Object.fromEntries(
          comparison.map((p, i) => [p.player_name || `Player ${i}`, p.scores?.[dim] ?? 0])
        ),
      }))
    : [];

  const selectedPlayers = players.filter((p) => selectedIds.includes(p.player_id));

  const filteredPlayers = players.filter((p) =>
    String(p.player_name || '').toLowerCase().includes(debouncedSearch.toLowerCase())
  );

  const maxScore = comparison
    ? Math.max(...comparison.map((p) => p.overall_score || 0), 10)
    : 10;

  return (
    <div className="space-y-6">
      {comparison && comparison.length > 0 && (
        <section className="surface p-6">
          <h3 className="mb-4 text-lg font-semibold text-slate-900">Comparison Results</h3>

          {comparison.length >= 2 && (
            <div className="mb-8">
              <h4 className="mb-3 text-sm font-semibold text-slate-700">Radar Overlay</h4>
              <ResponsiveContainer width="100%" height={360}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="#e2e8f0" />
                  <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11, fill: '#64748b' }} />
                  <PolarRadiusAxis angle={90} domain={[0, 10]} tick={{ fontSize: 10, fill: '#94a3b8' }} tickCount={6} />
                  <Tooltip
                    contentStyle={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 12 }}
                  />
                  <Legend
                    wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
                    iconType="circle"
                    formatter={(value) => <span className="text-slate-700">{value}</span>}
                  />
                  {comparison.map((p, i) => (
                    <Radar
                      key={p.player_id}
                      name={p.player_name}
                      dataKey={p.player_name}
                      stroke={PLAYER_COLORS[i % PLAYER_COLORS.length]}
                      fill={PLAYER_COLORS[i % PLAYER_COLORS.length]}
                      fillOpacity={0.08}
                      strokeWidth={2}
                    />
                  ))}
                </RadarChart>
              </ResponsiveContainer>
            </div>
          )}

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="py-3 pr-4 font-semibold text-slate-700">Metric</th>
                  {comparison.map((p) => (
                    <th key={p.player_id} className="px-4 py-3 font-semibold text-slate-700">
                      {p.player_name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {['overall_score', ...dimensions].map(
                  (metric) => (
                    <tr key={metric} className="border-b border-slate-100">
                      <td className="py-3 pr-4 font-medium text-slate-600">{metric === 'overall_score' ? 'KPI Rating' : metric.charAt(0).toUpperCase() + metric.slice(1).replace('_', ' ')}</td>
                      {comparison.map((p) => {
                        const val = metric === 'overall_score' ? p.overall_score : p.scores?.[metric];
                        const pct = maxScore > 0 ? ((val || 0) / maxScore) * 100 : 0;
                        return (
                          <td key={p.player_id} className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <div className="h-2 w-24 overflow-hidden rounded-full bg-slate-200">
                                <div
                                  className="h-full rounded-full bg-gradient-to-r from-brand-500 to-cyan-500"
                                  style={{ width: `${pct}%` }}
                                />
                              </div>
                              <span className="text-xs font-medium text-slate-700">
                                {typeof val === 'number' ? val.toFixed(1) : 'N/A'}
                              </span>
                            </div>
                          </td>
                        );
                      })}
                    </tr>
                  )
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {comparison && comparison.length === 0 && (
        <section className="surface-muted p-6 text-center text-sm text-slate-600">
          <Users className="mx-auto h-8 w-8 text-slate-400" />
          <p className="mt-2">No comparison data available for the selected players.</p>
        </section>
      )}

      <section className="surface p-6 sm:p-8">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h2 className="flex items-center gap-2 text-2xl font-semibold text-slate-900">
              <GitCompareArrows className="h-6 w-6 text-brand-600" />
              {comparison ? 'Select Different Players' : 'Player Comparison'}
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              Select 2 or more players to compare their performance scores side by side.
            </p>
          </div>
          <button
            className="btn-primary"
            onClick={runComparison}
            disabled={selectedIds.length < 2 || loading}
          >
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <BarChart3 className="mr-2 h-4 w-4" />}
            {comparison ? 'Re-run' : 'Compare'} ({selectedIds.length})
          </button>
        </div>

        {error && <div className="mt-4"><ErrorAlert message={error} /></div>}

        {selectedPlayers.length > 0 && (
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-slate-500">Selected:</span>
            {selectedPlayers.map((p) => (
              <span
                key={p.player_id}
                className="inline-flex items-center gap-1.5 rounded-full bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700"
              >
                {p.player_name}
                <button onClick={() => togglePlayer(p.player_id)} className="hover:text-brand-900">
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
          </div>
        )}

        <div className="relative mt-4">
          <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="search"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="field w-full pl-9"
            placeholder="Search players by name..."
            aria-label="Search players by name"
          />
        </div>

        {listLoading ? (
          <div className="mt-6 surface-muted p-6 text-center text-sm text-slate-600">
            <Loader2 className="mx-auto h-5 w-5 animate-spin" />
            <p className="mt-2">Loading players...</p>
          </div>
        ) : (
          <>
            {filteredPlayers.length === 0 && !listLoading && (
              <p className="mt-4 text-center text-sm text-slate-500">No players match your search.</p>
            )}
            <div className="mt-4 grid gap-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
              {filteredPlayers.map((player) => {
                const isSelected = selectedIds.includes(player.player_id);
                return (
                  <button
                    key={player.player_id}
                    onClick={() => togglePlayer(player.player_id)}
                    className={`flex items-center gap-3 rounded-lg border px-3 py-2 text-left transition ${
                      isSelected
                        ? 'border-brand-500 bg-brand-50 ring-1 ring-brand-500'
                        : 'surface-muted border-transparent hover:border-slate-300'
                    }`}
                  >
                    <div
                      className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-xs font-bold ${
                        isSelected ? 'bg-brand-600 text-white' : 'bg-slate-200 text-slate-600'
                      }`}
                    >
                      {player.player_name?.charAt(0) || '?'}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-slate-900">{player.player_name}</p>
                      <p className="truncate text-xs text-slate-500">{player.team_name || 'Unknown'}</p>
                    </div>
                    {isSelected && <X className="h-3 w-3 shrink-0 text-brand-600" />}
                  </button>
                );
              })}
            </div>
          </>
        )}
      </section>
    </div>
  );
};

export default PlayerComparison;
