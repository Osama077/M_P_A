import React, { useEffect, useState } from 'react';
import {
  TrendingUp, TrendingDown, Minus, BarChart3,
} from 'lucide-react';
import { AdvancedAnalysisAPI } from '../api';
import { useAppContext } from '../context/AppContext';
import LoadingSpinner from './LoadingSpinner';
import ErrorAlert from './ErrorAlert';

const colorStyles = {
  brand: { icon: 'text-brand-500', value: 'text-brand-800' },
  emerald: { icon: 'text-emerald-500', value: 'text-emerald-800' },
  rose: { icon: 'text-rose-500', value: 'text-rose-800' },
  amber: { icon: 'text-amber-500', value: 'text-amber-800' },
  cyan: { icon: 'text-cyan-500', value: 'text-cyan-800' },
  violet: { icon: 'text-violet-500', value: 'text-violet-800' },
};

const ForecastCard = ({ label, value, suffix, icon: Icon, color }) => {
  const cs = colorStyles[color] || colorStyles.brand;
  return (
    <div className="metric-card metric-active p-4">
      <div className="flex items-center gap-2 text-sm text-slate-500">
        <Icon className={`h-4 w-4 ${cs.icon}`} />
        <span>{label}</span>
      </div>
      <p className={`mt-1 text-xl font-semibold ${cs.value}`}>
        {value}{suffix || ''}
      </p>
    </div>
  );
};

const PlayerForecast = ({ playerId, playerName }) => {
  const { selectedSeason } = useAppContext();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetch = async () => {
      try {
        setLoading(true);
        setError(null);
        const result = await AdvancedAnalysisAPI.getForecast(playerId, selectedSeason);
        setData(result);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    if (playerId) fetch();
  }, [playerId, selectedSeason]);

  if (loading) return <LoadingSpinner message="Computing performance forecast..." />;
  if (error) return <ErrorAlert message={error} />;
  if (!data || !data.forecast) return <ErrorAlert message="No forecast data available" />;

  const f = data.forecast;

  const trendIcon = f.trend_direction === 'improving' ? TrendingUp :
    f.trend_direction === 'declining' ? TrendingDown : Minus;

  const trendColor = f.trend_direction === 'improving' ? 'emerald' :
    f.trend_direction === 'declining' ? 'rose' : 'amber';

  const chartWidth = 600;
  const chartHeight = 250;
  const padding = { top: 20, right: 20, bottom: 30, left: 40 };
  const plotW = chartWidth - padding.left - padding.right;
  const plotH = chartHeight - padding.top - padding.bottom;

  const allValues = [...(f.actual_values || []), f.predicted_next];
  const yMin = Math.max(0, Math.min(...allValues) - 0.5);
  const yMax = Math.min(10, Math.max(...allValues) + 0.5);

  const xScale = (i) => padding.left + (i / Math.max(1, allValues.length - 1)) * plotW;
  const yScale = (v) => padding.top + plotH - ((v - yMin) / (yMax - yMin)) * plotH;

  const actualPoints = (f.actual_values || []).map((v, i) =>
    `${xScale(i)},${yScale(v)}`
  ).join(' ');

  const trendPoints = (f.trend_line || []).map((v, i) =>
    `${xScale(i)},${yScale(v)}`
  ).join(' ');

  const predX = xScale(allValues.length - 1);
  const predY = yScale(f.predicted_next);
  const ciLow = yScale(Math.max(0, f.predicted_range?.lower || 0));
  const ciHigh = yScale(Math.min(10, f.predicted_range?.upper || 10));

  return (
    <div className="space-y-6 theme-animated">
      <section className="surface p-6 sm:p-8">
        <div className="section-header section-header-animated mb-4">
          <h2 className="text-xl font-semibold">Performance Forecast</h2>
          <p className="mt-1 text-sm text-white/90">
            ML-driven prediction for {playerName || data.player_name}
          </p>
        </div>

        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <ForecastCard
            label="Predicted Next"
            value={f.predicted_next}
            suffix="/10"
            icon={BarChart3}
            color="brand"
          />
          <ForecastCard
            label="Trend"
            value={f.trend_direction}
            icon={trendIcon}
            color={trendColor}
          />
          <ForecastCard
            label="Slope"
            value={f.trend_slope}
            icon={TrendingUp}
            color="cyan"
          />
          <ForecastCard
            label="R² Fit"
            value={f.r_squared}
            icon={BarChart3}
            color="violet"
          />
        </div>

        <div className="mt-6 grid grid-cols-2 gap-4 md:grid-cols-3">
          <div className="metric-card p-4">
            <p className="text-sm text-slate-500">Current Average</p>
            <p className="text-lg font-semibold text-slate-900">{f.current_avg}/10</p>
          </div>
          <div className="metric-card p-4">
            <p className="text-sm text-slate-500">Predicted Range</p>
            <p className="text-lg font-semibold text-slate-900">
              {f.predicted_range?.lower} – {f.predicted_range?.upper}
            </p>
          </div>
          <div className="metric-card p-4">
            <p className="text-sm text-slate-500">Confidence (±)</p>
            <p className="text-lg font-semibold text-slate-900">{f.confidence_interval}</p>
          </div>
        </div>

        <div className="mt-6 surface-muted p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-800">
            Performance Trajectory
            <span className="ml-2 text-xs font-normal text-slate-500">
              (Blue = Actual, Orange = Trend, Star = Predicted)
            </span>
          </h3>
          <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} className="w-full" style={{ maxHeight: '300px' }}>
            <line x1={padding.left} y1={yScale(0)} x2={chartWidth - padding.right} y2={yScale(0)}
              stroke="#ddd" strokeWidth="1" />
            {[2, 4, 6, 8].map(v => (
              <g key={v}>
                <line x1={padding.left} y1={yScale(v)} x2={chartWidth - padding.right} y2={yScale(v)}
                  stroke="#eee" strokeWidth="1" strokeDasharray="4,4" />
                <text x={padding.left - 5} y={yScale(v) + 4} textAnchor="end" fontSize="10" fill="#999">
                  {v}
                </text>
              </g>
            ))}
            <polyline points={actualPoints} fill="none" stroke="#3b82f6" strokeWidth="2.5"
              strokeLinejoin="round" strokeLinecap="round" />
            <polyline points={trendPoints} fill="none" stroke="#f97316" strokeWidth="2"
              strokeDasharray="6,3" strokeLinejoin="round" strokeLinecap="round" />
            <circle cx={predX} cy={predY} r="6" fill="#8b5cf6" stroke="white" strokeWidth="2" />
            <rect x={predX - 20} y={predY - 30} width="40" height="22" rx="4" fill="#8b5cf6" />
            <text x={predX} y={predY - 15} textAnchor="middle" fontSize="10" fill="white" fontWeight="bold">
              {f.predicted_next}
            </text>
            <line x1={predX} y1={ciLow} x2={predX} y2={ciHigh} stroke="#8b5cf6" strokeWidth="2"
              strokeDasharray="3,2" opacity="0.6" />
            <line x1={predX - 4} y1={ciLow} x2={predX + 4} y2={ciLow} stroke="#8b5cf6" strokeWidth="1.5"
              opacity="0.6" />
            <line x1={predX - 4} y1={ciHigh} x2={predX + 4} y2={ciHigh} stroke="#8b5cf6" strokeWidth="1.5"
              opacity="0.6" />
          </svg>
        </div>

        <div className="mt-4 surface p-4">
          <h3 className="mb-2 text-sm font-semibold text-slate-800">Interpretation</h3>
          <p className="text-sm text-slate-600">
            Based on {f.matches_used} matches, the predicted next score is <strong>{f.predicted_next}/10</strong>
            {' '}({f.predicted_range?.lower}–{f.predicted_range?.upper} at 80% confidence).
            The trend is <strong>{f.trend_direction}</strong> (slope: {f.trend_slope}).
            {f.r_squared > 0.3
              ? ' The linear model explains a meaningful portion of variance.'
              : ' The trend explains limited variance — individual matches vary significantly.'}
          </p>
        </div>
      </section>
    </div>
  );
};

export default PlayerForecast;
