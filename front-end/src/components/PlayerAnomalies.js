import React, { useEffect, useState } from 'react';
import {
  AlertTriangle, TrendingUp, TrendingDown,
  AlertCircle, CheckCircle2
} from 'lucide-react';
import { AdvancedAnalysisAPI } from '../api';
import { useAppContext } from '../context/AppContext';
import LoadingSpinner from './LoadingSpinner';
import ErrorAlert from './ErrorAlert';

const PlayerAnomalies = ({ playerId, playerName }) => {
  const { selectedSeason } = useAppContext();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetch = async () => {
      try {
        setLoading(true);
        setError(null);
        const result = await AdvancedAnalysisAPI.getAnomalies(playerId, selectedSeason);
        setData(result);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    if (playerId) fetch();
  }, [playerId, selectedSeason]);

  if (loading) return <LoadingSpinner message="Scanning for anomalies..." />;
  if (error) return <ErrorAlert message={error} />;
  if (!data || !data.anomalies) return <ErrorAlert message="No anomaly data" />;

  const a = data.anomalies;
  const totalAnomalies = (a.overall_anomalies_count || 0) + (a.contextual_anomalies_count || 0);

  return (
    <div className="space-y-6 theme-animated">
      <section className="surface p-6 sm:p-8">
        <div className="section-header section-header-animated mb-4">
          <h2 className="text-xl font-semibold">Anomaly Detection</h2>
          <p className="mt-1 text-sm text-white/90">
            Z-score outliers & Isolation Forest contextual anomalies for {playerName || data.player_name}
          </p>
        </div>

        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <div className="metric-card p-4">
            <p className="text-xs text-slate-500">Matches Analyzed</p>
            <p className="text-xl font-semibold text-slate-900">{a.total_matches}</p>
          </div>
          <div className="metric-card p-4">
            <div className="flex items-center gap-2">
              <AlertCircle className={`h-4 w-4 ${totalAnomalies > 0 ? 'text-rose-500' : 'text-emerald-500'}`} />
              <p className="text-xs text-slate-500">Total Anomalies</p>
            </div>
            <p className={`text-xl font-semibold ${totalAnomalies > 0 ? 'text-rose-600' : 'text-emerald-600'}`}>
              {totalAnomalies}
            </p>
          </div>
          <div className="metric-card p-4">
            <p className="text-xs text-slate-500">Anomaly Rate</p>
            <p className="text-xl font-semibold text-slate-900">
              {(a.anomaly_rate * 100).toFixed(1)}%
            </p>
          </div>
          <div className="metric-card p-4">
            <p className="text-xs text-slate-500">Max Z-Score</p>
            <p className="text-xl font-semibold text-slate-900">
              {a.z_score_summary?.max?.toFixed(2) || 'N/A'}
            </p>
          </div>
        </div>

        {a.overall_anomalies && a.overall_anomalies.length > 0 && (
          <div className="mt-6">
            <h3 className="mb-3 text-sm font-semibold text-slate-800">
              Score Outliers ({a.overall_anomalies_count})
            </h3>
            <div className="space-y-2">
              {a.overall_anomalies.map((anom, i) => (
                <div key={i} className={`metric-card p-3 border-l-4 ${
                  anom.type === 'underperformance' ? 'border-l-rose-500' : 'border-l-emerald-500'
                }`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {anom.type === 'underperformance' ? (
                        <TrendingDown className="h-5 w-5 text-rose-500" />
                      ) : (
                        <TrendingUp className="h-5 w-5 text-emerald-500" />
                      )}
                      <div>
                        <p className="text-sm font-semibold text-slate-900 capitalize">
                          {anom.type === 'underperformance' ? 'Underperformance' : 'Outstanding Performance'}
                        </p>
                        <p className="text-xs text-slate-500">
                          {anom.match_date || `Match ${anom.match_id}`}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className={`text-lg font-bold ${
                        anom.type === 'underperformance' ? 'text-rose-600' : 'text-emerald-600'
                      }`}>
                        {anom.overall_score}/10
                      </p>
                      <p className="text-xs text-slate-400">Z: {anom.z_score}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {a.contextual_anomalies && a.contextual_anomalies.length > 0 && (
          <div className="mt-6">
            <h3 className="mb-3 text-sm font-semibold text-slate-800">
              Contextual Anomalies ({a.contextual_anomalies_count})
            </h3>
            <p className="mb-3 text-xs text-slate-500">
              Multi-dimensional anomalies detected by Isolation Forest (actions, distance, passes, pressure)
            </p>
            <div className="space-y-2">
              {a.contextual_anomalies.map((anom, i) => (
                <div key={i} className="metric-card p-3 border-l-4 border-l-amber-500">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <AlertTriangle className="h-5 w-5 text-amber-500" />
                      <div>
                        <p className="text-sm font-semibold text-slate-900">
                          Unusual Performance Profile
                        </p>
                        <p className="text-xs text-slate-500">
                          {anom.match_date || `Match ${anom.match_id}`}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold text-slate-900">{anom.overall_score}/10</p>
                      <p className="text-xs text-slate-400">{anom.total_actions} actions</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {totalAnomalies === 0 && (
          <div className="mt-6 surface-muted p-6 text-center">
            <CheckCircle2 className="mx-auto h-8 w-8 text-emerald-500 mb-2" />
            <p className="text-sm font-medium text-slate-700">No anomalies detected</p>
            <p className="text-xs text-slate-500 mt-1">
              All performances fall within expected range (Z-score threshold: {a.z_score_summary?.threshold || 2.0})
            </p>
          </div>
        )}

        <div className="mt-4 surface p-4">
          <h3 className="mb-2 text-sm font-semibold text-slate-800">Methodology</h3>
          <p className="text-sm text-slate-600">
            Outliers are detected using Z-scores on overall_score (|Z| &gt; {a.z_score_summary?.threshold || 2.0}).
            Contextual anomalies use Isolation Forest on multi-dimensional features
            (score, actions, distance, accuracy, pressure) to find unusual performance patterns.
          </p>
        </div>
      </section>
    </div>
  );
};

export default PlayerAnomalies;
