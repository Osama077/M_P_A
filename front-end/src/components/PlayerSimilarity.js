import React, { useEffect, useState } from 'react';
import { Users, Target, UserX } from 'lucide-react';
import { AdvancedAnalysisAPI } from '../api';
import LoadingSpinner from './LoadingSpinner';
import ErrorAlert from './ErrorAlert';

const KNOWN_DIMS = ['passing', 'shooting', 'positioning', 'pressing', 'movement', 'physical', 'behavioral'];

const DIM_LABELS = {
  passing: 'Passing', shooting: 'Shooting', positioning: 'Positioning',
  pressing: 'Pressing', movement: 'Movement', physical: 'Physical', behavioral: 'Behavioral',
};

const PlayerSimilarity = ({ playerId, playerName, onSelectPlayer }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!playerId) return;
    const fetch = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await AdvancedAnalysisAPI.getSimilarPlayers(playerId);
        setData(result);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, [playerId]);

  if (!playerId) {
    return (
      <div className="surface-muted p-8 text-center">
        <UserX className="mx-auto h-10 w-10 text-slate-400" />
        <p className="mt-3 text-sm text-slate-600">Select a player first to see similar players.</p>
      </div>
    );
  }

  if (loading) return <LoadingSpinner message="Finding similar players..." />;
  if (error) return <ErrorAlert message={error} />;
  if (!data || !data.similarity) return <ErrorAlert message="No similarity data" />;

  const sim = data.similarity;
  const target = sim.target_player || {};
  const similar = sim.similar_players || [];

  const getSimilarityColor = (score) => {
    if (score >= 0.95) return 'bg-emerald-500';
    if (score >= 0.90) return 'bg-emerald-400';
    if (score >= 0.85) return 'bg-cyan-400';
    return 'bg-sky-400';
  };

  const getSimilarityWidth = (score) => {
    return Math.max(8, score * 100);
  };

  const renderScores = (scores) => {
    if (!scores) return null;
    return KNOWN_DIMS
      .filter((dim) => scores[dim] !== undefined)
      .map((dim) => (
        <span key={dim} className="color-chip">
          {DIM_LABELS[dim]}: {scores[dim]}
        </span>
      ));
  };

  return (
    <div className="space-y-6 theme-animated">
      <section className="surface p-6 sm:p-8">
        <div className="section-header section-header-animated mb-4">
          <h2 className="text-xl font-semibold">Similar Players</h2>
          <p className="mt-1 text-sm text-white/90">
            Cosine similarity on normalized dimension scores &mdash; compared against {sim.total_players_compared} players
          </p>
        </div>

        <div className="surface-muted p-4 mb-6">
          <div className="flex items-center gap-3">
            <Target className="h-5 w-5 text-brand-600" />
            <div>
              <p className="text-sm font-semibold text-slate-800">
                {target.player_name || playerName}
              </p>
              <p className="text-xs text-slate-500">{target.position || '\u2014'}</p>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {renderScores(target.scores)}
          </div>
        </div>

        {similar.length === 0 ? (
          <div className="text-center p-8 text-slate-500">
            <Users className="mx-auto h-8 w-8 mb-2 opacity-50" />
            <p className="text-sm">No similar players found above the similarity threshold.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {similar.map((p, idx) => (
              <div
                key={p.player_id}
                className="metric-card p-4 transition hover:shadow-md cursor-pointer"
                onClick={() => onSelectPlayer && onSelectPlayer(p.player_name, p.player_id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-cyan-500 to-violet-500 text-xs font-bold text-white">
                      {idx + 1}
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{p.player_name}</p>
                      <p className="text-xs text-slate-500">{p.position || '\u2014'}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-brand-700">
                      {(p.similarity_score * 100).toFixed(1)}%
                    </p>
                    <p className="text-xs text-slate-400">similar</p>
                  </div>
                </div>

                <div className="mt-2 h-2 w-full rounded-full bg-slate-200">
                  <div
                    className={`h-2 rounded-full transition-all ${getSimilarityColor(p.similarity_score)}`}
                    style={{ width: `${getSimilarityWidth(p.similarity_score)}%` }}
                  />
                </div>

                <div className="mt-2 flex flex-wrap gap-1">
                  {renderScores(p.scores)}
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="mt-4 surface p-4">
          <h3 className="mb-2 text-sm font-semibold text-slate-800">How it works</h3>
          <p className="text-sm text-slate-600">
            Similarity is computed using cosine distance between normalized 7-dimension score profiles.
            Scores above 90% indicate highly similar playing profiles; 85-90% indicates meaningful overlap.
            Click a player to open their dashboard.
          </p>
        </div>
      </section>
    </div>
  );
};

export default PlayerSimilarity;
