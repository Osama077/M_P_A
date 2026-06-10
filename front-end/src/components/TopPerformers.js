import React, { useEffect, useState } from 'react';
import {
  Trophy, TrendingUp, Target, Filter,
  BarChart3, Award
} from 'lucide-react';
import { AdvancedAnalysisAPI } from '../api';
import { useAppContext } from '../context/AppContext';
import LoadingSpinner from './LoadingSpinner';
import ErrorAlert from './ErrorAlert';

const sortOptions = [
  { value: 'overall_score', label: 'Overall Score', icon: BarChart3 },
  { value: 'momentum', label: 'Momentum', icon: TrendingUp },
  { value: 'consistency', label: 'Consistency', icon: Target },
];

const positions = ['All', 'Attacker', 'Midfielder', 'Defender', 'GK'];

const TopPerformers = ({ onSelectPlayer }) => {
  const { selectedSeason } = useAppContext();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sortBy, setSortBy] = useState('overall_score');
  const [position, setPosition] = useState('All');
  const [minMatches, setMinMatches] = useState(5);

  useEffect(() => {
    const fetch = async () => {
      try {
        setLoading(true);
        setError(null);
        const pos = position === 'All' ? null : position;
        const result = await AdvancedAnalysisAPI.getTopPerformers(sortBy, pos, minMatches, selectedSeason);
        setData(result);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, [sortBy, position, minMatches, selectedSeason]);

  const results = data?.results || [];

  const getRankColor = (idx) => {
    if (idx === 0) return 'from-amber-400 to-yellow-500 text-yellow-900';
    if (idx === 1) return 'from-slate-300 to-slate-400 text-slate-700';
    if (idx === 2) return 'from-amber-600 to-orange-700 text-orange-900';
    return 'from-slate-100 to-slate-200 text-slate-600';
  };

  const getScoreValue = (item) => {
    if (sortBy === 'momentum') return item.momentum_score;
    if (sortBy === 'consistency') return item.consistency_score;
    return item.overall_score;
  };

  const formatScore = (val) => {
    if (val === undefined || val === null) return 'N/A';
    if (sortBy === 'momentum') return val > 0 ? `+${val.toFixed(2)}` : val.toFixed(2);
    return val.toFixed(2);
  };

  return (
    <div className="space-y-6 theme-animated">
      <section className="surface p-6 sm:p-8">
        <div className="section-header section-header-animated mb-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold">Top Performers</h2>
              <p className="mt-1 text-sm text-white/90">
                League-wide rankings sorted by {sortBy.replace('_', ' ')}
              </p>
            </div>
            <Trophy className="h-8 w-8 text-white/70" />
          </div>
        </div>

        <div className="flex flex-wrap gap-3 mb-6">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-slate-500" />
            <span className="text-xs text-slate-500">Sort:</span>
            <div className="flex gap-1">
              {sortOptions.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setSortBy(opt.value)}
                  className={`inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                    sortBy === opt.value
                      ? 'bg-brand-600 text-white'
                      : 'bg-white/70 text-slate-600 hover:bg-white'
                  }`}
                >
                  <opt.icon className="h-3 w-3" />
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">Position:</span>
            <select
              value={position}
              onChange={(e) => setPosition(e.target.value)}
              className="field w-auto text-xs py-1"
            >
              {positions.map(p => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">Min Matches:</span>
            <input
              type="number"
              min="1"
              max="38"
              value={minMatches}
              onChange={(e) => setMinMatches(Math.max(1, Math.min(38, parseInt(e.target.value) || 1)))}
              className="field w-16 text-xs py-1 text-center"
            />
          </div>
        </div>

        {loading ? (
          <LoadingSpinner message="Loading rankings..." />
        ) : error ? (
          <ErrorAlert message={error} />
        ) : results.length === 0 ? (
          <div className="text-center p-8 text-slate-500">
            <Award className="mx-auto h-8 w-8 mb-2 opacity-50" />
            <p className="text-sm">No players match the current filters.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {results.map((item, idx) => {
              const scoreVal = getScoreValue(item);
              const isTop3 = idx < 3;
              return (
                <div
                  key={item.player_id}
                  className={`metric-card p-3 flex items-center justify-between transition hover:shadow-md cursor-pointer ${
                    isTop3 ? 'border-l-4 border-l-amber-400' : ''
                  }`}
                  onClick={() => onSelectPlayer && onSelectPlayer(item.player_name, item.player_id)}
                >
                  <div className="flex items-center gap-3">
                    <div className={`flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br ${getRankColor(idx)} text-xs font-bold shadow`}>
                      {idx + 1}
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{item.player_name}</p>
                      <p className="text-xs text-slate-500">
                        {item.position} &middot; {item.matches_played} matches
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    {sortBy !== 'overall_score' && (
                      <span className="text-xs text-slate-400">
                        Score: {item.overall_score?.toFixed(2) || 'N/A'}
                      </span>
                    )}
                    <div className="text-right">
                      <p className={`text-lg font-bold ${
                        sortBy === 'momentum' && scoreVal > 0 ? 'text-emerald-600' :
                        sortBy === 'momentum' && scoreVal < 0 ? 'text-rose-600' :
                        'text-brand-700'
                      }`}>
                        {formatScore(scoreVal)}
                      </p>
                      <p className="text-xs text-slate-400 capitalize">{sortBy.replace('_', ' ')}</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <p className="mt-4 text-xs text-slate-400 text-center">
          {results.length > 0 ? `Showing ${results.length} players — click a player to open their dashboard` : ''}
        </p>
      </section>
    </div>
  );
};

export default TopPerformers;
