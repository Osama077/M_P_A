import React, { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  CheckCircle2,
  Clock3,
  FlaskConical,
  ListChecks,
  Play,
  RotateCcw,
  ShieldAlert,
  XCircle,
} from 'lucide-react';
import apiClient, {
  AnalysisAPI,
  BenchmarkAPI,
  HealthAPI,
  MatchAPI,
  PlayerAPI,
  TeamAPI,
} from '../api';
import ErrorAlert from './ErrorAlert';

const APITester = () => {
  const [playerItems, setPlayerItems] = useState([]);
  const [selectedPlayerId, setSelectedPlayerId] = useState('');
  const [selectedMatchId, setSelectedMatchId] = useState('');
  const [selectedTeamFilter, setSelectedTeamFilter] = useState('');
  const [selectedBenchmark, setSelectedBenchmark] = useState('Attacker');
  const [seasonId, setSeasonId] = useState('106');
  const [competitionId, setCompetitionId] = useState('43');

  const [results, setResults] = useState([]);
  const [running, setRunning] = useState(false);
  const [bootstrapLoading, setBootstrapLoading] = useState(true);
  const [bootstrapError, setBootstrapError] = useState(null);

  const deriveHomeTeamFilter = (match) => {
    if (match?.home_team) {
      return String(match.home_team).trim();
    }
    const label = String(match?.match_label || '').trim();
    if (!label) return '';
    const afterPipe = label.includes('|') ? label.split('|').pop().trim() : label;
    const beforeVs = afterPipe.includes(' vs ') ? afterPipe.split(' vs ')[0] : afterPipe;
    return beforeVs.trim();
  };

  useEffect(() => {
    const bootstrap = async () => {
      try {
        setBootstrapLoading(true);
        setBootstrapError(null);

        const listResponse = await PlayerAPI.getPlayerList();
        const items = listResponse.player_items || [];
        setPlayerItems(items);

        if (items.length > 0) {
          const firstPlayer = items[0];
          setSelectedPlayerId(String(firstPlayer.player_id));

          const dashboard = await PlayerAPI.getPlayerDashboard(firstPlayer.player_name);
          const availableMatches = dashboard.available_matches || [];
          if (availableMatches.length > 0) {
            const firstMatch = availableMatches[0];
            setSelectedMatchId(String(firstMatch.match_id));
            setSelectedTeamFilter(deriveHomeTeamFilter(firstMatch));
          }
        }
      } catch (error) {
        setBootstrapError(error.message || 'Failed to load API tester inputs.');
      } finally {
        setBootstrapLoading(false);
      }
    };

    bootstrap();
  }, []);

  const selectedPlayer = useMemo(
    () => playerItems.find((p) => String(p.player_id) === String(selectedPlayerId)) || null,
    [playerItems, selectedPlayerId]
  );

  const compareIds = useMemo(
    () => playerItems.slice(0, 3).map((p) => Number(p.player_id)).filter((id) => Number.isFinite(id)),
    [playerItems]
  );

  const endpointDefinitions = useMemo(
    () => [
      {
        name: 'Health Check',
        description: 'Check whether the API base endpoint is reachable.',
        run: () => HealthAPI.checkHealth(),
      },
      {
        name: 'Player List',
        description: 'Fetch all available player names and ID mappings.',
        run: () => PlayerAPI.getPlayerList(),
      },
      {
        name: 'Player Dashboard',
        description: 'Load dashboard payload and chart metadata for selected player.',
        run: () => {
          if (!selectedPlayer?.player_name) throw new Error('Select a player first.');
          return PlayerAPI.getPlayerDashboard(
            selectedPlayer.player_name,
            selectedMatchId ? Number(selectedMatchId) : null
          );
        },
      },
      {
        name: 'Player Score',
        description: 'Fetch aggregated scoring model output for selected player.',
        run: () => {
          if (!selectedPlayerId) throw new Error('Select a player first.');
          return PlayerAPI.getPlayerScore(Number(selectedPlayerId));
        },
      },
      {
        name: 'Player Stats',
        description: 'Fetch engineered statistics for selected player.',
        run: () => {
          if (!selectedPlayerId) throw new Error('Select a player first.');
          return PlayerAPI.getPlayerStats(Number(selectedPlayerId));
        },
      },
      {
        name: 'Player History',
        description: 'Fetch historical match-by-match trend for selected player.',
        run: () => {
          if (!selectedPlayerId) throw new Error('Select a player first.');
          return PlayerAPI.getPlayerHistory(Number(selectedPlayerId));
        },
      },
      {
        name: 'Player Comparison',
        description: 'Compare top three available player IDs from current dataset.',
        run: () => {
          if (compareIds.length < 2) throw new Error('Need at least two players to compare.');
          return PlayerAPI.comparePlayer(compareIds);
        },
      },
      {
        name: 'Team Summary',
        description: 'Fetch team-level rollup for the provided team text filter.',
        run: () => {
          if (!selectedTeamFilter.trim()) throw new Error('Team filter is required.');
          return TeamAPI.getTeamSummary(selectedTeamFilter.trim());
        },
      },
      {
        name: 'Match Report',
        description: 'Fetch report payload for selected match.',
        run: () => {
          if (!selectedMatchId) throw new Error('Select a match first.');
          return MatchAPI.getMatchReport(Number(selectedMatchId));
        },
      },
      {
        name: 'Match Events',
        description: 'Fetch paginated match events feed for selected match.',
        run: () => {
          if (!selectedMatchId) throw new Error('Select a match first.');
          return MatchAPI.getMatchEvents(Number(selectedMatchId));
        },
      },
      {
        name: 'Benchmark',
        description: 'Fetch benchmark profile for role group.',
        run: () => BenchmarkAPI.getBenchmark(selectedBenchmark),
      },
      {
        name: 'Analyze Match',
        description: 'Trigger analysis workflow for selected match.',
        run: () => {
          if (!selectedMatchId) throw new Error('Select a match first.');
          return AnalysisAPI.analyzeMatch(Number(selectedMatchId));
        },
      },
      {
        name: 'Analyze Season',
        description: 'Trigger season-wide analysis endpoint with explicit request body.',
        run: () =>
          apiClient.post('/analyze/season', {
            competition_id: Number(competitionId),
            season_id: Number(seasonId),
            force_rerun: false,
          }),
        transform: (response) => response.data,
      },
    ],
    [
      compareIds,
      competitionId,
      seasonId,
      selectedBenchmark,
      selectedMatchId,
      selectedPlayer,
      selectedPlayerId,
      selectedTeamFilter,
    ]
  );

  const summarizeData = (payload) => {
    if (payload === null || payload === undefined) {
      return { type: 'null', keys: [], preview: 'No payload returned.' };
    }
    const type = Array.isArray(payload) ? 'array' : typeof payload;
    const keys = type === 'object' ? Object.keys(payload).slice(0, 8) : [];
    let preview = '';
    try {
      preview = JSON.stringify(payload).slice(0, 180);
    } catch {
      preview = 'Payload preview unavailable.';
    }
    return { type, keys, preview: preview.length === 180 ? `${preview}...` : preview };
  };

  const runSingleTest = async (endpoint) => {
    setRunning(true);
    try {
      const startTime = performance.now();
      const raw = await endpoint.run();
      const endTime = performance.now();
      const duration = (endTime - startTime).toFixed(2);
      const data = endpoint.transform ? endpoint.transform(raw) : raw;

      setResults((prev) => [
        {
          name: endpoint.name,
          status: 'success',
          durationMs: Number(duration),
          summary: summarizeData(data),
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        },
        ...prev,
      ]);
    } catch (error) {
      setResults((prev) => [
        {
          name: endpoint.name,
          status: 'error',
          error: error?.response?.data?.detail || error.message || 'Unknown error',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        },
        ...prev,
      ]);
    } finally {
      setRunning(false);
    }
  };

  const runAllTests = async () => {
    setResults([]);
    setRunning(true);

    for (const endpoint of endpointDefinitions) {
      try {
        const startTime = performance.now();
        const raw = await endpoint.run();
        const endTime = performance.now();
        const duration = (endTime - startTime).toFixed(2);
        const data = endpoint.transform ? endpoint.transform(raw) : raw;

        setResults((prev) => [
          {
            name: endpoint.name,
            status: 'success',
            durationMs: Number(duration),
            summary: summarizeData(data),
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
          },
          ...prev,
        ]);
      } catch (error) {
        setResults((prev) => [
          {
            name: endpoint.name,
            status: 'error',
            error: error?.response?.data?.detail || error.message || 'Unknown error',
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
          },
          ...prev,
        ]);
      }

      await new Promise((resolve) => setTimeout(resolve, 250));
    }

    setRunning(false);
  };

  const successCount = results.filter((r) => r.status === 'success').length;
  const failCount = results.filter((r) => r.status === 'error').length;
  const avgDuration =
    results.filter((r) => r.durationMs).reduce((acc, r) => acc + r.durationMs, 0) /
    (results.filter((r) => r.durationMs).length || 1);

  if (bootstrapLoading) {
    return (
      <div className="surface p-8 text-center">
        <div className="mx-auto inline-flex rounded-full bg-brand-50 p-3 text-brand-600">
          <FlaskConical className="h-5 w-5" />
        </div>
        <p className="mt-3 text-sm text-slate-600">Preparing API test inputs from live data...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section className="surface p-6 sm:p-8">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-slate-900">API Validation Console</h2>
            <p className="mt-1 text-sm text-slate-600">
              Run real endpoint tests with dataset-aware IDs and inspect payload integrity and latency.
            </p>
          </div>
          <div className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
            <ListChecks className="h-4 w-4" />
            {endpointDefinitions.length} endpoint checks
          </div>
        </div>

        {bootstrapError ? <div className="mt-5"><ErrorAlert message={bootstrapError} /></div> : null}

        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <label className="text-sm text-slate-700">
            Player
            <select
              className="field mt-2"
              value={selectedPlayerId}
              onChange={(e) => setSelectedPlayerId(e.target.value)}
            >
              <option value="">Select player</option>
              {playerItems.map((player) => (
                <option key={player.player_id} value={String(player.player_id)}>
                  {player.player_name} ({player.player_id})
                </option>
              ))}
            </select>
          </label>

          <label className="text-sm text-slate-700">
            Match ID
            <input
              className="field mt-2"
              value={selectedMatchId}
              onChange={(e) => setSelectedMatchId(e.target.value)}
              placeholder="e.g. 3775648"
            />
          </label>

          <label className="text-sm text-slate-700">
            Team Filter
            <input
              className="field mt-2"
              value={selectedTeamFilter}
              onChange={(e) => setSelectedTeamFilter(e.target.value)}
              placeholder="e.g. Barcelona"
            />
          </label>

          <label className="text-sm text-slate-700">
            Benchmark Role
            <select
              className="field mt-2"
              value={selectedBenchmark}
              onChange={(e) => setSelectedBenchmark(e.target.value)}
            >
              <option value="Attacker">Attacker</option>
              <option value="Midfielder">Midfielder</option>
              <option value="Defender">Defender</option>
              <option value="GK">GK</option>
            </select>
          </label>

          <label className="text-sm text-slate-700">
            Competition ID
            <input
              className="field mt-2"
              value={competitionId}
              onChange={(e) => setCompetitionId(e.target.value)}
              placeholder="43"
            />
          </label>

          <label className="text-sm text-slate-700">
            Season ID
            <input
              className="field mt-2"
              value={seasonId}
              onChange={(e) => setSeasonId(e.target.value)}
              placeholder="106"
            />
          </label>
        </div>

        <div className="mt-6 flex flex-wrap gap-3">
          <button type="button" className="btn-primary" onClick={runAllTests} disabled={running}>
            <Play className="mr-2 h-4 w-4" />
            {running ? 'Running checks...' : 'Run all endpoint checks'}
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => setResults([])}
            disabled={running || results.length === 0}
          >
            <RotateCcw className="mr-2 h-4 w-4" />
            Clear results
          </button>
        </div>
      </section>

      <section className="surface p-6">
        <h3 className="text-lg font-semibold text-slate-900">Run Individual Tests</h3>
        <p className="mt-1 text-sm text-slate-600">Use this list for focused validation while troubleshooting.</p>
        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {endpointDefinitions.map((endpoint) => (
            <button
              key={endpoint.name}
              type="button"
              onClick={() => runSingleTest(endpoint)}
              disabled={running}
              className="surface-muted flex items-start justify-between gap-3 p-4 text-left transition hover:border-brand-200 hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
              title={endpoint.description}
            >
              <div>
                <p className="text-sm font-semibold text-slate-900">{endpoint.name}</p>
                <p className="mt-1 text-xs text-slate-500">{endpoint.description}</p>
              </div>
              <Activity className="mt-0.5 h-4 w-4 text-slate-400" />
            </button>
          ))}
        </div>
      </section>

      <section className="surface p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h3 className="text-lg font-semibold text-slate-900">Execution Results</h3>
          <div className="text-sm text-slate-500">{results.length} recorded runs</div>
        </div>

        {results.length === 0 ? (
          <div className="mt-6 surface-muted p-10 text-center text-sm text-slate-600">
            No results yet. Run all checks or execute a single endpoint test.
          </div>

        ) : (
          <div className="mt-6 space-y-3">
            {results.map((result, index) => (
              <article
                key={`${result.name}-${index}`}
                className={`rounded-xl border p-4 ${
                  result.status === 'success'
                    ? 'border-emerald-200 bg-emerald-50/60'
                    : 'border-red-200 bg-red-50/60'
                }`}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="flex items-start gap-2">
                    {result.status === 'success' ? (
                      <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-600" />
                    ) : (
                      <XCircle className="mt-0.5 h-4 w-4 text-red-600" />
                    )}
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{result.name}</p>
                      <p className="text-xs text-slate-500">{result.timestamp}</p>
                    </div>
                  </div>
                  <div className="inline-flex items-center gap-1 rounded-md bg-white px-2 py-1 text-xs font-medium text-slate-600">
                    <Clock3 className="h-3.5 w-3.5" />
                    {result.durationMs ? `${result.durationMs.toFixed(0)} ms` : 'Failed'}
                  </div>
                </div>

                {result.status === 'success' ? (
                  <div className="mt-3 space-y-1 text-xs text-slate-700">
                    <p>
                      <span className="font-semibold">Type:</span> {result.summary.type}
                    </p>
                    <p>
                      <span className="font-semibold">Top keys:</span>{' '}
                      {result.summary.keys.length > 0 ? result.summary.keys.join(', ') : 'N/A'}
                    </p>
                    <p className="rounded-md bg-white p-2 text-[11px] text-slate-600">{result.summary.preview}</p>
                  </div>
                ) : (
                  <div className="mt-3 flex items-start gap-2 rounded-md border border-red-200 bg-white p-2 text-xs text-red-700">
                    <ShieldAlert className="mt-0.5 h-3.5 w-3.5" />
                    <p>{result.error}</p>
                  </div>
                )}
              </article>
            ))}
          </div>
        )}
      </section>

      {results.length > 0 ? (
        <section className="grid gap-4 sm:grid-cols-3">
          <div className="surface-muted p-5">
            <p className="text-xs uppercase tracking-wide text-slate-500">Successful</p>
            <p className="mt-2 text-2xl font-semibold text-emerald-700">{successCount}</p>
          </div>
          <div className="surface-muted p-5">
            <p className="text-xs uppercase tracking-wide text-slate-500">Failed</p>
            <p className="mt-2 text-2xl font-semibold text-red-700">{failCount}</p>
          </div>
          <div className="surface-muted p-5">
            <p className="text-xs uppercase tracking-wide text-slate-500">Average latency</p>
            <p className="mt-2 text-2xl font-semibold text-slate-900">{avgDuration.toFixed(0)} ms</p>
          </div>
        </section>
      ) : null}
    </div>
  );
};

export default APITester;
