import React, { useMemo, useState, useEffect } from 'react';
import { ArrowRight, Search, Users } from 'lucide-react';
import { PlayerAPI } from '../api';
import { useAppContext } from '../context/AppContext';
import LoadingSpinner from './LoadingSpinner';
import ErrorAlert from './ErrorAlert';
import useDebouncedValue from '../hooks/useDebouncedValue';

const PlayerList = ({ onSelectPlayer }) => {
  const { selectedSeason } = useAppContext();
  const [playerItems, setPlayerItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTeam, setSelectedTeam] = useState('all');
  const [visibleCount, setVisibleCount] = useState(60);
  const debouncedSearch = useDebouncedValue(searchTerm, 250);

  useEffect(() => {
    const fetchPlayers = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await PlayerAPI.getPlayerList(selectedSeason);
        setPlayerItems(response.player_items || []);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchPlayers();
  }, [selectedSeason]);

  const teamOptions = useMemo(() => {
    const source = playerItems.map((item) => item.team_name || 'Unknown');
    return ['all', ...Array.from(new Set(source)).sort((a, b) => a.localeCompare(b))];
  }, [playerItems]);

  const filteredPlayers = useMemo(
    () =>
      playerItems.filter((item) => {
        const nameMatch = String(item.player_name || '')
          .toLowerCase()
          .includes(debouncedSearch.toLowerCase());
        const teamMatch = selectedTeam === 'all' || (item.team_name || 'Unknown') === selectedTeam;
        return nameMatch && teamMatch;
      }),
    [playerItems, debouncedSearch, selectedTeam]
  );

  const visiblePlayers = filteredPlayers.slice(0, visibleCount);

  const clearSearch = () => {
    setSearchTerm('');
    setSelectedTeam('all');
    setVisibleCount(60);
  };

  if (loading) return <LoadingSpinner message="Loading players..." />;

  return (
    <div className="space-y-4">
      {error ? <ErrorAlert message={error} /> : null}

      <div className="theme-players">
      <section className="surface p-6 sm:p-8">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="section-header section-header-players">
              <h2 className="text-2xl font-semibold">Player Directory</h2>
              <p className="mt-1 text-sm text-white/90">
                Search quickly across the full squad dataset and open dashboards with one click.
              </p>
            </div>
          </div>
          <div className="color-chip animate-shimmer">
            <Users className="h-4 w-4" />
            {filteredPlayers.length} results
          </div>
        </div>

        <div className="mt-6 grid grid-cols-1 gap-3 md:grid-cols-[minmax(0,1fr)_220px_auto]">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input
              type="search"
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setVisibleCount(60);
              }}
              className="field pl-9"
              placeholder="Search by player name"
              aria-label="Search players by name"
            />
          </div>
          <select
            value={selectedTeam}
            onChange={(e) => {
              setSelectedTeam(e.target.value);
              setVisibleCount(60);
            }}
            className="field"
            aria-label="Filter players by team"
          >
            {teamOptions.map((team) => (
              <option key={team} value={team}>
                {team === 'all' ? 'All teams' : team}
              </option>
            ))}
          </select>
          <button type="button" className="btn-secondary" onClick={clearSearch}>
            Clear
          </button>
        </div>

        {filteredPlayers.length === 0 ? (
          <div className="mt-6 surface-muted p-10 text-center">
            <p className="text-sm text-slate-600">No players matched your search query.</p>
          </div>
        ) : (
          <>
            <div className="mt-6 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
              {visiblePlayers.map((player) => (
                <button
                  key={`${player.player_id}-${player.player_name}`}
                  type="button"
                  onClick={() => onSelectPlayer(player.player_name, player.player_id)}
                  className={`surface group p-4 text-left transition hover:-translate-y-0.5 hover:shadow-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 ${
                    visiblePlayers.indexOf(player) < 6 ? 'metric-active' : ''
                  }`}
                >
                  <p className="text-sm font-semibold text-slate-900">{player.player_name}</p>
                  <p className="mt-1 text-xs text-slate-500">{player.team_name || 'Unknown team'}</p>
                  <p className="mt-2 inline-flex items-center gap-2 text-xs font-medium text-brand-700">
                    Open dashboard
                    <ArrowRight className="h-3.5 w-3.5" />
                  </p>
                </button>
              ))}
            </div>

            {visiblePlayers.length < filteredPlayers.length && (
              <div className="mt-6 flex justify-center">
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => setVisibleCount((v) => v + 60)}
                >
                  Load more players
                </button>
              </div>
            )}
          </>
        )}
      </section>
      </div>
    </div>
  );
};

export default PlayerList;
