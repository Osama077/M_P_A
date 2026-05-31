import React, { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import { Activity, Download, TrendingUp, TrendingDown } from 'lucide-react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { PlayerAPI } from '../api';
import LoadingSpinner from './LoadingSpinner';
import ErrorAlert from './ErrorAlert';

const CHART_COLORS = {
  indigo: '#6366f1',
  indigoLight: '#a5b4fc',
  cyan: '#06b6d4',
  cyanLight: '#67e8f9',
  emerald: '#10b981',
  emeraldLight: '#6ee7b7',
  teal: '#0d9488',
  tealLight: '#5eead4',
  amber: '#f59e0b',
  rose: '#f43f5e',
  slate: '#94a3b8',
  slateDark: '#475569',
  violet: '#8b5cf6',
  sky: '#0ea5e9',
  orange: '#f97316',
};

const DIM_COLORS = [
  '#6366f1', '#f43f5e', '#f59e0b', '#10b981',
  '#f97316', '#8b5cf6', '#06b6d4',
];

const CustomTooltip = ({ active, payload, label, formatter, labelFormatter }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-white/70 bg-white/95 px-4 py-3 shadow-xl backdrop-blur">
      <p className="mb-1.5 text-xs font-medium text-slate-500">
        {labelFormatter ? labelFormatter(label) : label}
      </p>
      {payload.map((entry, i) => (
        <div key={i} className="flex items-center gap-2 text-sm">
          <span
            className="inline-block h-2.5 w-2.5 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-slate-600">{entry.name}:</span>
          <span className="font-semibold text-slate-900">
            {formatter ? formatter(entry.value) : entry.value?.toFixed(2)}
          </span>
        </div>
      ))}
    </div>
  );
};

const StaggerCard = ({ index, children, className = '' }) => (
  <article
    className={`chart-frame ${className}`}
    style={{ animation: `fadeSlideIn 400ms ease-out ${index * 80}ms both` }}
  >
    {children}
  </article>
);

const ExportButtons = ({ containerRef, baseName }) => {
  const [message, setMessage] = useState('');

  const downloadFromUrl = (url, filename) => {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  const handleExport = useCallback(async (format) => {
    try {
      setMessage('');
      const container = containerRef.current;
      const svgElement = container?.querySelector('svg');
      if (!svgElement) { setMessage('No chart to export.'); return; }

      const serializer = new XMLSerializer();
      const svgString = serializer.serializeToString(svgElement);
      const svgBlob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });

      if (format === 'svg') {
        const svgUrl = URL.createObjectURL(svgBlob);
        downloadFromUrl(svgUrl, `${baseName}.svg`);
        URL.revokeObjectURL(svgUrl);
        setMessage('SVG exported');
        return;
      }

      const canvas = document.createElement('canvas');
      const bounds = svgElement.getBoundingClientRect();
      canvas.width = Math.max(900, Math.floor(bounds.width || 900));
      canvas.height = Math.max(520, Math.floor(bounds.height || 520));
      const ctx = canvas.getContext('2d');
      if (!ctx) { setMessage('Export failed'); return; }

      const svgUrl = URL.createObjectURL(svgBlob);
      const img = new Image();
      img.onload = () => {
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        URL.revokeObjectURL(svgUrl);
        downloadFromUrl(canvas.toDataURL('image/png'), `${baseName}.png`);
        setMessage('PNG exported');
      };
      img.onerror = () => { URL.revokeObjectURL(svgUrl); setMessage('Export failed'); };
      img.src = svgUrl;
    } catch { setMessage('Export failed'); }
  }, [containerRef, baseName]);

  return (
    <div className="flex items-center gap-1">
      <button
        type="button"
        className="btn-secondary px-2 py-1 text-xs"
        onClick={() => handleExport('png')}
        title="Export as PNG"
      >
        <Download className="mr-1 h-3 w-3" />
        PNG
      </button>
      <button
        type="button"
        className="btn-secondary px-2 py-1 text-xs"
        onClick={() => handleExport('svg')}
        title="Export as SVG"
      >
        <Download className="mr-1 h-3 w-3" />
        SVG
      </button>
      {message && <span className="ml-2 text-[10px] text-emerald-600">{message}</span>}
    </div>
  );
};

const TrendSummaryCard = ({ label, value, icon: Icon, color }) => (
  <div className="metric-card metric-active flex items-center gap-4 p-4">
    <div
      className="flex h-10 w-10 items-center justify-center rounded-xl"
      style={{ backgroundColor: `${color}18` }}
    >
      <Icon className="h-5 w-5" style={{ color }} />
    </div>
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-0.5 text-2xl font-bold" style={{ color }}>
        {value !== null ? value.toFixed(2) : 'N/A'}
      </p>
    </div>
  </div>
);

const PlayerAnimatedAnalysis = ({ playerName }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [historySeries, setHistorySeries] = useState([]);
  const [dashboardData, setDashboardData] = useState(null);
  const [historyWindow, setHistoryWindow] = useState(10);

  const overallChartRef = useRef(null);
  const vaepChartRef = useRef(null);

  useEffect(() => {
    const fetchData = async () => {
      if (!playerName) return;
      try {
        setLoading(true);
        setError(null);

        const listResponse = await PlayerAPI.getPlayerList();
        const matched = (listResponse.player_items || []).find(
          (item) => String(item.player_name).toLowerCase() === String(playerName).toLowerCase()
        );

        if (!matched?.player_id) {
          setHistorySeries([]);
          setDashboardData(null);
          return;
        }

        const [historyResponse, dashboardResponse] = await Promise.all([
          PlayerAPI.getPlayerHistory(Number(matched.player_id)),
          PlayerAPI.getPlayerDashboardData(playerName),
        ]);

        const matches = historyResponse.matches || [];
        const normalized = matches
          .map((m, idx) => {
            const date = String(m.match_date || 'Unknown');
            const shortDate = date !== 'Unknown' ? date.slice(5, 10) : `M${idx + 1}`;
            return {
              id: m.match_id,
              label: shortDate,
              fullDate: date,
              overall: Number(m.overall_score ?? 0),
              vaep: Number(m.vaep_rating ?? 0),
            };
          })
          .slice(-20);

        setHistorySeries(normalized);
        setDashboardData(dashboardResponse || null);
      } catch (err) {
        setError(err.message || 'Failed to load animated analysis.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [playerName]);

  const historySeriesFiltered = useMemo(
    () => historySeries.slice(-historyWindow),
    [historySeries, historyWindow]
  );

  const historySummary = useMemo(() => {
    if (!historySeriesFiltered.length) {
      return { bestOverall: null, avgVaep: null };
    }
    const bestOverall = Math.max(...historySeriesFiltered.map((d) => d.overall));
    const avgVaep = historySeriesFiltered.reduce((acc, d) => acc + d.vaep, 0) / historySeriesFiltered.length;
    return { bestOverall, avgVaep };
  }, [historySeriesFiltered]);

  if (loading) return <LoadingSpinner message={`Loading animated analysis for ${playerName}...`} />;
  if (error) return <ErrorAlert message={error} />;

  const trendData = dashboardData?.charts?.trend || [];
  const radarData = dashboardData?.charts?.radar || { labels: [], values: [] };
  const breakdownData = dashboardData?.charts?.breakdown || [];
  const vaepData = dashboardData?.charts?.vaep || { timeline: [], totals: { offensive: 0, defensive: 0 } };
  const positionData = dashboardData?.charts?.position_comparison || [];
  const percentiles = dashboardData?.charts?.percentiles || {
    in_team: 0,
    in_league: 0,
    in_position: 0,
  };

  const radarChartData = radarData.labels.map((label, idx) => ({
    name: label,
    value: Number(radarData.values[idx] || 0),
  }));

  const percentileChartData = [
    { name: 'In Team', value: Number(percentiles.in_team || 0) },
    { name: 'In League', value: Number(percentiles.in_league || 0) },
    { name: 'In Position', value: Number(percentiles.in_position || 0) },
  ];

  return (
    <div className="space-y-4">
      <div className="theme-animated">
        <section className="surface p-6 sm:p-8">
          <div className="section-header section-header-animated mb-6 flex items-center gap-2">
            <Activity className="h-5 w-5" />
            <h2 className="text-2xl font-semibold">Animated Analysis — {playerName}</h2>
          </div>

          <div className="mb-6 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white/80 px-3 py-2">
              <span className="text-sm font-medium text-slate-600">Recent matches</span>
              {[5, 10, 20].map((window) => (
                <button
                  key={window}
                  type="button"
                  onClick={() => setHistoryWindow(window)}
                  className={`rounded-md px-2.5 py-1 text-xs font-semibold transition-all ${
                    historyWindow === window
                      ? 'bg-gradient-to-r from-teal-600 to-cyan-600 text-white shadow-sm'
                      : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }`}
                >
                  {window}
                </button>
              ))}
            </div>
            {historySummary.bestOverall !== null && (
              <div className="text-xs text-slate-500">
                Showing last {historySeriesFiltered.length} matches
              </div>
            )}
          </div>

          <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <TrendSummaryCard
              label="Best Overall (Recent)"
              value={historySummary.bestOverall}
              icon={TrendingUp}
              color={CHART_COLORS.indigo}
            />
            <TrendSummaryCard
              label="Average VAEP (Recent)"
              value={historySummary.avgVaep}
              icon={TrendingDown}
              color={CHART_COLORS.emerald}
            />
          </div>

          <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
            <StaggerCard index={0}>
              <div className="flex items-center justify-between gap-2 px-5 pt-5">
                <h3 className="text-sm font-semibold text-slate-800">Overall vs VAEP Trend</h3>
                <ExportButtons containerRef={overallChartRef} baseName={`${playerName}-overall-vaep`} />
              </div>
              <div className="h-[280px] w-full px-2 pb-2" ref={overallChartRef}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={historySeriesFiltered} margin={{ top: 12, right: 12, left: 0, bottom: 8 }}>
                    <defs>
                      <linearGradient id="overallGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={CHART_COLORS.indigo} stopOpacity={0.15} />
                        <stop offset="100%" stopColor={CHART_COLORS.indigo} stopOpacity={0.01} />
                      </linearGradient>
                      <linearGradient id="vaepGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={CHART_COLORS.emerald} stopOpacity={0.12} />
                        <stop offset="100%" stopColor={CHART_COLORS.emerald} stopOpacity={0.01} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis
                      dataKey="label"
                      tick={{ fill: '#64748b', fontSize: 11 }}
                      axisLine={{ stroke: '#e2e8f0' }}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fill: '#64748b', fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                      domain={[0, 'auto']}
                    />
                    <Tooltip
                      content={<CustomTooltip />}
                      cursor={{ stroke: '#cbd5e1', strokeDasharray: '4 4' }}
                    />
                    <Legend
                      verticalAlign="bottom"
                      iconType="circle"
                      iconSize={8}
                      wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
                    />
                    <Area
                      type="monotone"
                      dataKey="overall"
                      fill="url(#overallGrad)"
                      stroke="none"
                    />
                    <Line
                      type="monotone"
                      dataKey="overall"
                      name="Overall"
                      stroke={CHART_COLORS.indigo}
                      strokeWidth={2.5}
                      dot={{ r: 2, fill: CHART_COLORS.indigo, strokeWidth: 0 }}
                      activeDot={{ r: 5, stroke: '#fff', strokeWidth: 2, fill: CHART_COLORS.indigo }}
                      isAnimationActive
                      animationDuration={800}
                    />
                    <Area
                      type="monotone"
                      dataKey="vaep"
                      fill="url(#vaepGrad)"
                      stroke="none"
                    />
                    <Line
                      type="monotone"
                      dataKey="vaep"
                      name="VAEP"
                      stroke={CHART_COLORS.emerald}
                      strokeWidth={2.5}
                      dot={{ r: 2, fill: CHART_COLORS.emerald, strokeWidth: 0 }}
                      activeDot={{ r: 5, stroke: '#fff', strokeWidth: 2, fill: CHART_COLORS.emerald }}
                      isAnimationActive
                      animationDuration={800}
                      animationBegin={150}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </StaggerCard>

            <StaggerCard index={1}>
              <div className="flex items-center justify-between gap-2 px-5 pt-5">
                <h3 className="text-sm font-semibold text-slate-800">VAEP Area Flow</h3>
                <ExportButtons containerRef={vaepChartRef} baseName={`${playerName}-vaep-flow`} />
              </div>
              <div className="h-[280px] w-full px-2 pb-2" ref={vaepChartRef}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={historySeriesFiltered} margin={{ top: 12, right: 12, left: 0, bottom: 8 }}>
                    <defs>
                      <linearGradient id="vaepFlowGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={CHART_COLORS.cyan} stopOpacity={0.45} />
                        <stop offset="100%" stopColor={CHART_COLORS.cyan} stopOpacity={0.04} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis
                      dataKey="label"
                      tick={{ fill: '#64748b', fontSize: 11 }}
                      axisLine={{ stroke: '#e2e8f0' }}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fill: '#64748b', fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip
                      content={<CustomTooltip />}
                      cursor={{ stroke: '#cbd5e1', strokeDasharray: '4 4' }}
                    />
                    <ReferenceLine y={0} stroke="#cbd5e1" strokeDasharray="3 3" />
                    <Area
                      type="monotone"
                      dataKey="vaep"
                      name="VAEP"
                      stroke={CHART_COLORS.cyan}
                      strokeWidth={2.5}
                      fill="url(#vaepFlowGrad)"
                      isAnimationActive
                      animationDuration={900}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </StaggerCard>
          </div>

          <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
            <StaggerCard index={2}>
              <h3 className="px-5 pt-5 text-sm font-semibold text-slate-800">Dimension Scores</h3>
              <div className="h-[310px] w-full px-2 pb-2">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={radarChartData} layout="vertical" margin={{ top: 8, right: 16, left: 90, bottom: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
                    <XAxis
                      type="number"
                      domain={[0, 10]}
                      tick={{ fill: '#64748b', fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      dataKey="name"
                      type="category"
                      tick={{ fill: '#475569', fontSize: 11 }}
                      width={85}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip
                      content={<CustomTooltip />}
                      cursor={{ fill: '#f1f5f9' }}
                    />
                    <Bar
                      dataKey="value"
                      name="Score"
                      radius={[0, 4, 4, 0]}
                      minPointSize={3}
                      isAnimationActive
                      animationDuration={1000}
                      animationBegin={200}
                    >
                      {radarChartData.map((_, idx) => (
                        <Cell key={idx} fill={DIM_COLORS[idx % DIM_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </StaggerCard>

            <StaggerCard index={3}>
              <h3 className="px-5 pt-5 text-sm font-semibold text-slate-800">Performance Trend</h3>
              <div className="h-[310px] w-full px-2 pb-2">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={trendData} margin={{ top: 12, right: 12, left: 0, bottom: 8 }}>
                    <defs>
                      <linearGradient id="trendFlowGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={CHART_COLORS.sky} stopOpacity={0.4} />
                        <stop offset="100%" stopColor={CHART_COLORS.sky} stopOpacity={0.03} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis
                      dataKey="date"
                      tick={{ fill: '#64748b', fontSize: 10 }}
                      axisLine={{ stroke: '#e2e8f0' }}
                      tickLine={false}
                    />
                    <YAxis
                      domain={[0, 10]}
                      tick={{ fill: '#64748b', fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip
                      content={<CustomTooltip labelFormatter={(l) => `Date: ${l}`} />}
                      cursor={{ stroke: '#cbd5e1', strokeDasharray: '4 4' }}
                    />
                    <Legend
                      verticalAlign="bottom"
                      iconType="circle"
                      iconSize={8}
                      wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
                    />
                    <Area
                      type="monotone"
                      dataKey="overall"
                      name="Score"
                      stroke={CHART_COLORS.sky}
                      strokeWidth={2.5}
                      fill="url(#trendFlowGrad)"
                      isAnimationActive
                      animationDuration={1000}
                    />
                    <Line
                      type="monotone"
                      dataKey="rolling_avg"
                      name="3-Match Avg"
                      stroke={CHART_COLORS.amber}
                      strokeWidth={2}
                      strokeDasharray="5 3"
                      dot={false}
                      isAnimationActive
                      animationDuration={1000}
                      animationBegin={200}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </StaggerCard>

            <StaggerCard index={4}>
              <h3 className="px-5 pt-5 text-sm font-semibold text-slate-800">Score Breakdown</h3>
              <div className="h-[310px] w-full px-2 pb-2">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={breakdownData} layout="vertical" margin={{ top: 8, right: 16, left: 90, bottom: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
                    <XAxis
                      type="number"
                      domain={[0, 10]}
                      tick={{ fill: '#64748b', fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      dataKey="name"
                      type="category"
                      tick={{ fill: '#475569', fontSize: 11 }}
                      width={85}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip
                      content={<CustomTooltip />}
                      cursor={{ fill: '#f1f5f9' }}
                    />
                    <Bar
                      dataKey="value"
                      name="Score"
                      radius={[0, 4, 4, 0]}
                      minPointSize={3}
                      isAnimationActive
                      animationDuration={1100}
                      animationBegin={100}
                    >
                      {breakdownData.map((_, idx) => (
                        <Cell key={idx} fill={DIM_COLORS[idx % DIM_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </StaggerCard>

            <StaggerCard index={5}>
              <h3 className="px-5 pt-5 text-sm font-semibold text-slate-800">VAEP Analysis</h3>
              <div className="grid grid-cols-1 gap-4 p-4 md:grid-cols-2">
                <div className="h-[260px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={vaepData.timeline} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis
                        dataKey="date"
                        tick={{ fill: '#64748b', fontSize: 10 }}
                        axisLine={{ stroke: '#e2e8f0' }}
                        tickLine={false}
                      />
                      <YAxis
                        tick={{ fill: '#64748b', fontSize: 11 }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <Tooltip
                        content={<CustomTooltip />}
                        cursor={{ fill: '#f1f5f9' }}
                      />
                      <Bar
                        dataKey="vaep"
                        name="VAEP"
                        radius={[3, 3, 0, 0]}
                        minPointSize={2}
                        isAnimationActive
                        animationDuration={1200}
                        animationBegin={150}
                      >
                        {vaepData.timeline.map((entry, idx) => (
                          <Cell
                            key={idx}
                            fill={entry.vaep >= 0 ? CHART_COLORS.cyan : CHART_COLORS.rose}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div className="flex flex-col items-center justify-center rounded-xl border border-slate-100 bg-gradient-to-br from-slate-50 to-white p-4">
                  <h4 className="mb-4 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Season Totals
                  </h4>
                  <div className="grid w-full grid-cols-2 gap-4 text-center">
                    <div className="rounded-xl bg-gradient-to-br from-cyan-50 to-cyan-100/60 p-4 shadow-sm">
                      <p className="text-xs font-medium text-cyan-700">Offensive</p>
                      <p className="mt-1 text-xl font-bold text-cyan-800">
                        {Number(vaepData.totals.offensive || 0).toFixed(2)}
                      </p>
                    </div>
                    <div className="rounded-xl bg-gradient-to-br from-emerald-50 to-emerald-100/60 p-4 shadow-sm">
                      <p className="text-xs font-medium text-emerald-700">Defensive</p>
                      <p className="mt-1 text-xl font-bold text-emerald-800">
                        {Number(vaepData.totals.defensive || 0).toFixed(2)}
                      </p>
                    </div>
                  </div>
                  <div className="mt-4 w-full rounded-lg bg-slate-50 p-3 text-center">
                    <p className="text-xs text-slate-500">Total VAEP</p>
                    <p className="text-lg font-bold text-slate-800">
                      {(Number(vaepData.totals.offensive || 0) + Number(vaepData.totals.defensive || 0)).toFixed(2)}
                    </p>
                  </div>
                </div>
              </div>
            </StaggerCard>

            <StaggerCard index={6}>
              <h3 className="px-5 pt-5 text-sm font-semibold text-slate-800">Position Comparison</h3>
              <div className="h-[310px] w-full px-2 pb-2">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={positionData} layout="vertical" margin={{ top: 8, right: 16, left: 90, bottom: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
                    <XAxis
                      type="number"
                      domain={[0, 10]}
                      tick={{ fill: '#64748b', fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      dataKey="name"
                      type="category"
                      tick={{ fill: '#475569', fontSize: 11 }}
                      width={85}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip
                      content={<CustomTooltip />}
                      cursor={{ fill: '#f1f5f9' }}
                    />
                    <Legend
                      verticalAlign="bottom"
                      iconType="circle"
                      iconSize={8}
                      wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
                    />
                    <Bar
                      dataKey="player"
                      name={playerName}
                      fill={CHART_COLORS.violet}
                      radius={[0, 4, 4, 0]}
                      minPointSize={3}
                      isAnimationActive
                      animationDuration={1000}
                      animationBegin={100}
                    />
                    <Bar
                      dataKey="position_avg"
                      name="Position Avg"
                      fill={CHART_COLORS.slate}
                      radius={[0, 4, 4, 0]}
                      minPointSize={3}
                      isAnimationActive
                      animationDuration={1000}
                      animationBegin={250}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </StaggerCard>

            <StaggerCard index={7}>
              <h3 className="px-5 pt-5 text-sm font-semibold text-slate-800">Percentile Rankings</h3>
              <div className="h-[310px] w-full px-2 pb-2">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={percentileChartData} layout="vertical" margin={{ top: 8, right: 16, left: 110, bottom: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
                    <XAxis
                      type="number"
                      domain={[0, 100]}
                      tick={{ fill: '#64748b', fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      dataKey="name"
                      type="category"
                      tick={{ fill: '#475569', fontSize: 11 }}
                      width={100}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip
                      content={<CustomTooltip formatter={(v) => `${v}%`} />}
                      cursor={{ fill: '#f1f5f9' }}
                    />
                    <Bar
                      dataKey="value"
                      name="Percentile"
                      radius={[0, 4, 4, 0]}
                      minPointSize={3}
                      isAnimationActive
                      animationDuration={1000}
                      animationBegin={150}
                    >
                      {percentileChartData.map((_, idx) => (
                        <Cell
                          key={idx}
                          fill={[CHART_COLORS.teal, CHART_COLORS.amber, CHART_COLORS.emerald][idx]}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </StaggerCard>
          </div>
        </section>
      </div>
    </div>
  );
};

export default PlayerAnimatedAnalysis;
