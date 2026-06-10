import React, { useState, useEffect } from 'react';
import { MetadataAPI, SeasonAPI, EvolutionAPI } from '../api';
import LoadingSpinner from './LoadingSpinner';
import ErrorAlert from './ErrorAlert';

const FeatureCard = ({ icon, title, desc, children }) => (
  <div className="surface overflow-hidden">
    <div className="border-b border-slate-100 bg-gradient-to-r from-brand-50 to-cyan-50 px-5 py-4">
      <div className="flex items-center gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white text-lg shadow-sm">{icon}</span>
        <div>
          <h3 className="font-semibold text-slate-800">{title}</h3>
          <p className="text-xs text-slate-500">{desc}</p>
        </div>
      </div>
    </div>
    <div className="px-5 py-4">{children}</div>
  </div>
);

const Badge = ({ children, color = "bg-brand-100 text-brand-700" }) => (
  <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${color}`}>{children}</span>
);

export default function WhatsNewPage() {
  const [metadata, setMetadata] = useState(null);
  const [seasons, setSeasons] = useState(null);
  const [evolution, setEvolution] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetch = async () => {
      try {
        setLoading(true);
        const [meta, seasonList] = await Promise.all([
          MetadataAPI.listPlayers(),
          SeasonAPI.listSeasons(),
        ]);
        setMetadata(meta);
        setSeasons(seasonList);

        if (meta?.players?.length) {
          const p = meta.players[Math.floor(Math.random() * meta.players.length)];
          try {
            const ev = await EvolutionAPI.getEvolution(p.player_id);
            setEvolution(ev);
          } catch {}
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, []);

  if (loading) return <LoadingSpinner message="Loading release notes..." />;
  if (error) return <ErrorAlert message={error} />;

  const seasonCount = seasons?.seasons?.length || 0;
  const playerCount = metadata?.total || 0;

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-8">
        <div className="flex items-center gap-3">
          <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 text-2xl text-white shadow-lg">+</span>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">What's New</h1>
            <p className="text-sm text-slate-500">Multi-season support, metadata pipeline & season-aware API</p>
          </div>
        </div>
      </div>

      <div className="mb-8 grid gap-4 sm:grid-cols-3">
        <div className="surface flex items-center gap-3 px-5 py-4">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-100 text-lg text-blue-600 font-bold">{seasonCount}</span>
          <div>
            <p className="text-xs text-slate-500">La Liga Seasons</p>
            <p className="font-semibold text-slate-800">2004–2021</p>
          </div>
        </div>
        <div className="surface flex items-center gap-3 px-5 py-4">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-100 text-lg text-emerald-600 font-bold">{playerCount}</span>
          <div>
            <p className="text-xs text-slate-500">Players Indexed</p>
            <p className="font-semibold text-slate-800">With Metadata</p>
          </div>
        </div>
        <div className="surface flex items-center gap-3 px-5 py-4">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-100 text-lg text-violet-600 font-bold">+26</span>
          <div>
            <p className="text-xs text-slate-500">Endpoints</p>
            <p className="font-semibold text-slate-800">With Season Filter</p>
          </div>
        </div>
      </div>

      <div className="mb-8 grid gap-5 md:grid-cols-2">
        <FeatureCard icon="📅" title="Multi-Season Support" desc="17 La Liga seasons from StatsBomb">
          <ul className="space-y-2 text-sm text-slate-600">
            <li className="flex items-start gap-2">
              <span className="mt-0.5 text-emerald-500">+</span>
              <span><strong>SEASONS_LIST</strong> in <code>config.py</code> — 17 seasons (2004/2005 through 2020/2021)</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="mt-0.5 text-emerald-500">+</span>
              <span><strong>--seasons</strong> flag on <code>run_pipeline.py</code> — select which seasons to process</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="mt-0.5 text-emerald-500">+</span>
              <span><strong>Two-level caching</strong> in <code>_shared.py</code> — per-season parquet files with fallback to combined data</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="mt-0.5 text-emerald-500">+</span>
              <span><strong>season_label</strong> column preserved across all pipeline steps (VAEP, xG, scoring)</span>
            </li>
          </ul>
          {seasons && (
            <details className="mt-3">
              <summary className="cursor-pointer text-xs font-medium text-brand-600">View seasons</summary>
              <div className="mt-2 flex flex-wrap gap-1">
                {seasons.seasons.map(s => (
                  <Badge key={s.label}>{s.label}</Badge>
                ))}
              </div>
            </details>
          )}
        </FeatureCard>

        <FeatureCard icon="🔎" title="Season Filter on All Endpoints" desc="Every API route accepts ?season=...">
          <p className="mb-3 text-sm text-slate-600">All major endpoints now support an optional <code>season</code> query parameter for filtering data by season:</p>
          <div className="mb-3 grid grid-cols-2 gap-1 text-xs">
            {[
              "player/list", "player/{id}/score", "player/{id}/stats",
              "player/{id}/history", "player/compare", "player/head-to-head",
              "player/season-trends", "player/match-log", "player/tactical-board",
              "player/{id}/evolution", "team/{id}/summary", "team/{id}/heatmap",
              "match/list", "match/{id}/report", "match/{id}/events",
              "benchmark/{pos}", "analyze/match/{id}", "analyze/season",
              "player/squad-scores", "player/profile/{name}",
              "player/{id}/advanced", "player/{id}/forecast",
              "player/{id}/anomalies", "player/{id}/similar",
              "player/{id}/consistency", "player/{id}/momentum",
            ].map(e => <span key={e} className="rounded bg-slate-50 px-2 py-1 font-mono text-slate-600">/{e}</span>)}
          </div>
          <p className="text-xs text-slate-400">26 endpoints with season filtering support</p>
        </FeatureCard>

        <FeatureCard icon="🧑" title="Metadata Pipeline" desc="Player info indexed from StatsBomb">
          <div className="mb-3 flex items-center justify-around text-center text-sm">
            <div>
              <p className="text-2xl font-bold text-slate-800">{playerCount}</p>
              <p className="text-xs text-slate-500">Total Players</p>
            </div>
            <div className="h-10 w-px bg-slate-200" />
            <div>
              <p className="text-2xl font-bold text-slate-800">{metadata?.players?.filter(p => p.primary_position).length || 0}</p>
              <p className="text-xs text-slate-500">With Position</p>
            </div>
            <div className="h-10 w-px bg-slate-200" />
            <div>
              <p className="text-2xl font-bold text-slate-800">{metadata?.players?.filter(p => p.preferred_foot).length || 0}</p>
              <p className="text-xs text-slate-500">With Preferred Foot</p>
            </div>
          </div>
          {metadata && (
            <div className="rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
              <p className="mb-2 font-medium text-slate-700">Sample players:</p>
              <div className="grid gap-1">
                {metadata.players.slice(0, 5).map(p => (
                  <div key={p.player_id} className="flex items-center gap-2">
                    <span className="font-medium">{p.full_name}</span>
                    <Badge>{p.primary_position}</Badge>
                    {p.preferred_foot && <Badge color="bg-amber-100 text-amber-700">{p.preferred_foot}</Badge>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </FeatureCard>

        <FeatureCard icon="📊" title="New API Endpoints" desc="5 new routes for richer data">
          <ul className="space-y-3 text-sm text-slate-600">
            <li className="flex items-start gap-2">
              <Badge color="bg-blue-100 text-blue-700">GET</Badge>
              <div><code className="font-semibold">/api/v1/player/season/list</code><br /><span className="text-xs">List all available seasons with competition/season IDs</span></div>
            </li>
            <li className="flex items-start gap-2">
              <Badge color="bg-blue-100 text-blue-700">GET</Badge>
              <div><code className="font-semibold">/api/v1/player/{'{id}'}/evolution</code><br /><span className="text-xs">Year-over-year evolution of player metrics (avg_score, vaep per season)</span></div>
            </li>
            <li className="flex items-start gap-2">
              <Badge color="bg-green-100 text-green-700">GET</Badge>
              <div><code className="font-semibold">/api/v1/metadata/players</code><br /><span className="text-xs">List all players with position, foot, appearances, career averages</span></div>
            </li>
            <li className="flex items-start gap-2">
              <Badge color="bg-green-100 text-green-700">GET</Badge>
              <div><code className="font-semibold">/api/v1/metadata/players/{'{id}'}</code><br /><span className="text-xs">Full player metadata with season summaries and jersey numbers</span></div>
            </li>
            <li className="flex items-start gap-2">
              <Badge color="bg-green-100 text-green-700">GET</Badge>
              <div><code className="font-semibold">/api/v1/metadata/player/search?query=...</code><br /><span className="text-xs">Name-based player search (fuzzy, case-insensitive)</span></div>
            </li>
          </ul>
        </FeatureCard>

        <FeatureCard icon="🛠" title="Pipeline Improvements" desc="Faster reloads & data integrity fixes">
          <ul className="space-y-2 text-sm text-slate-600">
            <li className="flex items-start gap-2">
              <span className="mt-0.5 rounded-full bg-green-100 px-1.5 text-xs text-green-700 font-medium">FIX</span>
              <span><strong>xG Model</strong> — skips full retrain if model file exists; runs prediction-only (saves hours)</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="mt-0.5 rounded-full bg-green-100 px-1.5 text-xs text-green-700 font-medium">FIX</span>
              <span><strong>Position Benchmarks</strong> — added <code>.reset_index()</code> so <code>position_group</code> is a proper column (was index-only, caused 500 errors)</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="mt-0.5 rounded-full bg-green-100 px-1.5 text-xs text-green-700 font-medium">FIX</span>
              <span><strong>Season Labels</strong> — back-filled <code>season_label</code> on VAEP ratings & model scores for correct season filtering</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="mt-0.5 rounded-full bg-green-100 px-1.5 text-xs text-green-700 font-medium">FIX</span>
              <span><strong>Metadata Serialization</strong> — handles NaN values and numpy arrays in player metadata (was crashing with 500)</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="mt-0.5 rounded-full bg-blue-100 px-1.5 text-xs text-blue-700 font-medium">NEW</span>
              <span><strong>Data Loader</strong> — saves per-season + combined parquet files; supports two-level cache in API</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="mt-0.5 rounded-full bg-blue-100 px-1.5 text-xs text-blue-700 font-medium">NEW</span>
              <span><strong>Metadata Pipeline</strong> — <code>pipeline/metadata_loader.py</code> builds player info from lineups, events, and scores</span>
            </li>
          </ul>
        </FeatureCard>

        <FeatureCard icon="📈" title="Player Evolution (Example)" desc={`${evolution?.player_name || "Random player"} — season-over-season`}>
          {evolution ? (
            <div>
              {evolution.evolution?.length > 0 ? (
                <div className="space-y-2">
                  {evolution.evolution.map(e => (
                    <div key={e.season_label} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm">
                      <span className="font-medium">{e.season_label}</span>
                      <div className="flex items-center gap-4">
                        <span>Score: <strong>{e.avg_score}</strong></span>
                        <span>VAEP: <strong>{e.avg_vaep ?? 'N/A'}</strong></span>
                        <span className="text-xs text-slate-400">{e.matches} matches</span>
                      </div>
                    </div>
                  ))}
                  <p className="text-xs text-slate-400">Trend: {evolution.trend}</p>
                </div>
              ) : (
                <p className="text-sm text-slate-500">No evolution data yet — run the pipeline for multiple seasons.</p>
              )}
            </div>
          ) : (
            <p className="text-sm text-slate-500">Could not load example.</p>
          )}
        </FeatureCard>

        <FeatureCard icon="⚡" title="Under the Hood" desc="Architecture & caching improvements">
          <ul className="space-y-2 text-sm text-slate-600">
            <li className="flex items-start gap-2">
              <span className="mt-0.5 text-emerald-500">+</span>
              <span><strong>Two-level caching</strong> — <code>_load_data()</code> (LRU, combined) + <code>_load_season_cached()</code> (LRU, per-season with fallback)</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="mt-0.5 text-emerald-500">+</span>
              <span><strong>Per-season parquet files</strong> in <code>data/seasons/{'{label}'}/</code> — enables fast single-season API response without filtering combined data</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="mt-0.5 text-emerald-500">+</span>
              <span><strong>Graceful fallback</strong> — when per-season file doesn't exist, falls back to filtering combined data by <code>season_label</code></span>
            </li>
          </ul>
          <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs font-medium text-slate-700">Architecture</p>
            <pre className="mt-1 overflow-x-auto text-xs text-slate-500">
{`API Request
  + season? → _load_season(label)
    ├── reads data/seasons/{label}/file.parquet
    └── fallback: filter combined data by season_label
  + no season → _load_data()
    └── reads combined parquet from data/*.parquet`}
            </pre>
          </div>
        </FeatureCard>
      </div>

      <div className="surface px-5 py-4 text-center text-xs text-slate-400">
        <p>System updated June 2026 · {seasonCount} seasons indexed · {playerCount} players with metadata</p>
      </div>
    </div>
  );
}
