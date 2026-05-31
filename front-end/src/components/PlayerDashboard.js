import React, { useEffect, useState } from 'react';
import { Bot, CalendarDays, LayoutGrid, ListFilter } from 'lucide-react';
import { PlayerAPI } from '../api';
import LoadingSpinner from './LoadingSpinner';
import ErrorAlert from './ErrorAlert';

const PlayerDashboard = ({ playerName, initialMatchId }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedMatchId, setSelectedMatchId] = useState(initialMatchId || null);

  useEffect(() => {
    setSelectedMatchId(initialMatchId || null);
  }, [playerName, initialMatchId]);

  useEffect(() => {
    const fetchDashboard = async () => {
      if (!playerName) {
        setError('Player name is required');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        const response = await PlayerAPI.getPlayerDashboard(playerName, selectedMatchId);
        setData(response);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboard();
  }, [playerName, selectedMatchId]);

  if (loading) return <LoadingSpinner message={`Loading dashboard for ${playerName}...`} />;
  if (error) return <ErrorAlert message={error} />;
  if (!data) return <ErrorAlert message="No data available" />;

  const playerInfo = data?.player_info || {};
  const charts = data?.charts || {};
  const availableMatches = data?.available_matches || [];
  const activeMatchId = selectedMatchId || data?.selected_match_id || null;
  const activeMatch = availableMatches.find((m) => m.match_id === activeMatchId) || null;

  const seasonCharts = [
    { key: 'radar', label: 'Radar Chart' },
    { key: 'trend', label: 'Trend Chart' },
    { key: 'score_breakdown', label: 'Score Breakdown' },
    { key: 'vaep', label: 'VAEP Analysis' },
    { key: 'position_comparison', label: 'Position Comparison' },
    { key: 'percentiles', label: 'Percentile Rankings' },
  ];

  const matchCharts = [
    { key: 'heatmap', label: 'Heatmap (Selected Match)' },
    { key: 'pass_map', label: 'Pass Map (Selected Match)' },
    { key: 'shooting_map', label: 'Shooting Map (Selected Match)' },
  ];

  const formatMatchLabel = (match) => {
    if (!match) return '';
    const home = match.home_team || 'Unknown Home';
    const away = match.away_team || 'Unknown Away';
    const datePrefix = match.match_date ? `${match.match_date} | ` : '';
    return `${datePrefix}${home} vs ${away}`;
  };

  const renderChartCard = (item, colorClass) => (
    <article key={item.key} className="chart-frame">
      <div className={`${colorClass} px-4 py-3`}>
        <h3 className="text-sm font-semibold text-white">{item.label}</h3>
      </div>
      <div className="backend-chart-canvas p-4">
        {charts[item.key] ? (
          <img
            src={charts[item.key]}
            alt={item.label}
            className="h-full w-full rounded-lg object-contain"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-500">
            Chart unavailable for this context.
          </div>
        )}
      </div>
    </article>
  );

  return (
    <div className="space-y-4">
      <div className="theme-dashboard">
        <section className="surface p-6 sm:p-8">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <div className="section-header section-header-dashboard">
                <h2 className="text-2xl font-semibold sm:text-3xl">{playerInfo.name || playerName}</h2>
                <p className="mt-1 text-sm text-white/90">
                  Backend image dashboard with unified sizing for all charts and maps.
                </p>
              </div>
            </div>
            <div className="metric-card metric-active animate-shimmer px-4 py-3 text-right">
              <p className="text-xs uppercase tracking-wide text-brand-700">Season score</p>
              <p className="text-2xl font-semibold text-brand-800">
                {typeof playerInfo.avg_overall === 'number' ? playerInfo.avg_overall.toFixed(1) : 'N/A'}/10
              </p>
            </div>
          </div>

          <div className="mt-5 grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
            <div className="metric-card metric-active">
              <p className="text-slate-500">Position</p>
              <p className="mt-1 text-base font-semibold text-slate-900">{playerInfo.position || 'N/A'}</p>
            </div>
            <div className="metric-card metric-active">
              <p className="text-slate-500">Matches</p>
              <p className="mt-1 text-base font-semibold text-slate-900">{playerInfo.matches || 'N/A'}</p>
            </div>
            <div className="metric-card">
              <p className="text-slate-500">Cluster</p>
              <p className="mt-1 text-base font-semibold text-slate-900">{playerInfo.cluster || 'N/A'}</p>
            </div>
            <div className="metric-card">
              <p className="text-slate-500">Trend</p>
              <p className="mt-1 text-base font-semibold text-slate-900">{playerInfo.trend || 'N/A'}</p>
            </div>
          </div>

          <div className="mt-5 surface-muted p-4">
            <div className="flex items-start gap-3">
              <div className="rounded-lg bg-slate-900 p-2 text-white">
                <Bot className="h-4 w-4" />
              </div>
              <p className="text-sm text-slate-600">
                For animated, frontend-rendered analysis, open the new Animated page from the top navigation.
              </p>
            </div>
          </div>
        </section>
      </div>

      {availableMatches.length > 0 ? (
        <div className="theme-dashboard">
          <section className="surface p-6">
            <div className="mb-3 flex items-center gap-2 text-slate-800">
              <ListFilter className="h-4 w-4" />
              <h3 className="text-base font-semibold">Match selector</h3>
            </div>
            <p className="mb-3 text-sm text-slate-600">
              Select a match to refresh match-specific maps (Heatmap, Pass Map, Shooting Map).
            </p>
            <select
              value={activeMatchId || ''}
              onChange={(e) => setSelectedMatchId(Number(e.target.value))}
              className="field"
              aria-label="Select match for match-specific charts"
            >
              {availableMatches.map((m) => (
                <option key={m.match_id} value={m.match_id}>
                  {formatMatchLabel(m)}
                </option>
              ))}
            </select>
            {activeMatch ? (
              <p className="mt-3 inline-flex items-center gap-2 text-sm text-slate-700">
                <CalendarDays className="h-4 w-4" />
                {formatMatchLabel(activeMatch)}
              </p>
            ) : null}
          </section>
        </div>
      ) : null}

      <section>
        <div className="section-header section-header-dashboard mb-4 flex items-center gap-2">
          <LayoutGrid className="h-5 w-5" />
          <h3 className="text-xl font-semibold">Season-level charts</h3>
        </div>
        <p className="mb-5 text-sm text-slate-600">
          These backend-generated charts now use a consistent frame and unified rendering size.
        </p>
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">{seasonCharts.map((item) => renderChartCard(item, 'bg-indigo-600'))}</div>
      </section>

      <section>
        <div className="section-header section-header-dashboard mb-4 flex items-center gap-2">
          <LayoutGrid className="h-5 w-5" />
          <h3 className="text-xl font-semibold">Match-specific charts</h3>
        </div>
        <p className="mb-5 text-sm text-slate-600">These charts represent only the selected match from the dropdown.</p>
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">{matchCharts.map((item) => renderChartCard(item, 'bg-emerald-600'))}</div>
      </section>
    </div>
  );
};

export default PlayerDashboard;
