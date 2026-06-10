import React, { useEffect, useState, useCallback, useRef } from 'react';
import { Loader2, RefreshCw, Grid3X3, GitCompareArrows, Target, Crosshair, Minimize2 } from 'lucide-react';
import { TacticalBoardAPI } from '../api';
import { useAppContext } from '../context/AppContext';
import ErrorAlert from './ErrorAlert';

const TOOL_FORMATION = 'formation';
const TOOL_PASSES = 'passes';
const TOOL_HEATMAP = 'heatmap';
const TOOL_ZONES = 'zones';

const POS_COLORS = {
  Goalkeeper: { bg: 'rgba(0,208,132,0.25)', stroke: '#00D084', text: '#00D084' },
  Defender: { bg: 'rgba(88,166,255,0.2)', stroke: '#58A6FF', text: '#58A6FF' },
  Midfielder: { bg: 'rgba(0,208,132,0.2)', stroke: '#00D084', text: '#00D084' },
  Attacker: { bg: 'rgba(248,81,73,0.2)', stroke: '#F85149', text: '#F85149' },
};

const FORMATIONS = ['4-3-3', '4-4-2', '4-2-3-1', '3-5-2', '5-3-2', '3-4-3'];

const TacticalBoard = () => {
  const { selectedSeason, setSelectedSeason, seasonOptions } = useAppContext();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedMatchId, setSelectedMatchId] = useState(null);
  const [selectedPlayer, setSelectedPlayer] = useState(null);
  const [activeTool, setActiveTool] = useState(TOOL_FORMATION);
  const [passLinesVisible, setPassLinesVisible] = useState(false);
  const [panelTab, setPanelTab] = useState('info');
  const [playerPositions, setPlayerPositions] = useState({});
  const dragRef = useRef(null);
  const svgRef = useRef(null);

  const svgToCoords = useCallback((clientX, clientY) => {
    const rect = svgRef.current.getBoundingClientRect();
    return {
      x: (clientX - rect.left) * (700 / rect.width),
      y: (clientY - rect.top) * (480 / rect.height),
    };
  }, []);

  const handleDragStart = useCallback((e, player) => {
    e.stopPropagation();
    const { x, y } = svgToCoords(e.clientX, e.clientY);
    const pos = playerPositions[player.player_id] || { svg_x: player.svg_x, svg_y: player.svg_y };
    dragRef.current = { playerId: player.player_id, ox: x - pos.svg_x, oy: y - pos.svg_y };
  }, [svgToCoords, playerPositions]);

  const handleDragMove = useCallback((e) => {
    if (!dragRef.current) return;
    const { x, y } = svgToCoords(e.clientX, e.clientY);
    const { playerId, ox, oy } = dragRef.current;
    setPlayerPositions(prev => ({
      ...prev,
      [playerId]: {
        svg_x: Math.max(40, Math.min(660, x - ox)),
        svg_y: Math.max(20, Math.min(460, y - oy)),
      },
    }));
  }, [svgToCoords]);

  const handleDragEnd = useCallback(() => {
    dragRef.current = null;
  }, []);

  const fetchData = useCallback(async (matchId) => {
    setLoading(true);
    setError(null);
    try {
      const result = await TacticalBoardAPI.getTacticalBoard(matchId, selectedSeason);
      setData(result);
      if (result?.match_context?.match_id) setSelectedMatchId(result.match_context.match_id);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [selectedSeason]);

  useEffect(() => { setSelectedMatchId(null); }, [selectedSeason]);

  useEffect(() => {
    fetchData(selectedMatchId);
  }, [selectedMatchId, fetchData, selectedSeason]);

  const selectMatch = (mid) => {
    setSelectedMatchId(mid);
    setSelectedPlayer(null);
  };

  const selectPlayer = (player) => {
    setSelectedPlayer(player);
    setPanelTab('info');
  };

  const changeFormation = (f) => {
    setSelectedPlayer(null);
  };

  const togglePassLines = () => setPassLinesVisible(v => !v);

  const resetView = () => {
    setActiveTool(TOOL_FORMATION);
    setPassLinesVisible(false);
  };

  // Get player position (custom if dragged, otherwise original)
  const getPlayerPos = useCallback((player) => {
    const custom = playerPositions[player.player_id];
    return custom || { svg_x: player.svg_x, svg_y: player.svg_y };
  }, [playerPositions]);

  // Determine player color based on position
  const playerColor = (p) => {
    const g = p.position_group;
    if (g === 'Goalkeeper') return POS_COLORS.Goalkeeper;
    if (g === 'Defender') return POS_COLORS.Defender;
    if (g === 'Midfielder') return POS_COLORS.Midfielder;
    return POS_COLORS.Attacker;
  };

  if (loading) {
    return (
      <div className="surface-muted p-12 text-center">
        <Loader2 className="mx-auto h-6 w-6 animate-spin text-brand-600" />
        <p className="mt-3 text-sm text-slate-600">Loading tactical board...</p>
      </div>
    );
  }
  if (error) return <ErrorAlert message={error} onRetry={() => fetchData(selectedMatchId)} />;
  if (!data) return <ErrorAlert message="No tactical board data available" />;

  const mc = data.match_context;
  const players = data.players || [];
  const passNetwork = data.pass_network || [];
  const heatmapGrid = data.heatmap_grid || [];
  const notes = data.notes || [];
  const availableMatches = data.available_matches || [];

  // Top pass connections for network display (thicker lines for higher counts)
  const maxPassCount = passNetwork.length ? Math.max(...passNetwork.map(p => p.count)) : 1;

  return (
    <div className="animate-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
            <Target className="w-5 h-5 text-brand-600" />
            Tactical Board
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Formation viewer · Pass networks · Positional heatmaps · Tactical notes
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-semibold text-slate-500">Season</span>
          <select
            value={selectedSeason || ''}
            onChange={(e) => { setSelectedSeason(e.target.value || null); setSelectedMatchId(null); }}
            className="field text-xs py-1.5 w-24"
            aria-label="Select season"
          >
            <option value="">All</option>
            {seasonOptions.map((s) => (
              <option key={s.label} value={s.label}>{s.label}</option>
            ))}
          </select>
          <span className="text-[11px] font-semibold text-slate-500">Match</span>
          <select
            className="field text-xs py-1.5"
            value={selectedMatchId || ''}
            onChange={e => selectMatch(Number(e.target.value))}
          >
            {availableMatches.map(am => (
              <option key={am.match_id} value={am.match_id}>{am.label}</option>
            ))}
          </select>
          <button className="btn-secondary text-xs py-1.5 px-3" onClick={() => fetchData(selectedMatchId)}>
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh
          </button>
        </div>
      </div>

      <div className="flex gap-4">
        {/* Pitch Board */}
        <div className="flex-1">
          <div className="surface rounded-xl overflow-hidden">
            {/* Toolbar */}
            <div className="flex items-center gap-1.5 p-2.5 border-b border-slate-200 bg-white/50 flex-wrap">
              <button
                className={`btn-secondary text-[10px] py-1 px-2.5 ${activeTool === TOOL_FORMATION ? 'bg-brand-50 text-brand-700 border-brand-300' : ''}`}
                onClick={() => setActiveTool(TOOL_FORMATION)}
              >
                <Grid3X3 className="w-3 h-3" />
                Formation
              </button>
              <button
                className={`btn-secondary text-[10px] py-1 px-2.5 ${activeTool === TOOL_PASSES ? 'bg-brand-50 text-brand-700 border-brand-300' : ''}`}
                onClick={() => setActiveTool(TOOL_PASSES)}
              >
                <GitCompareArrows className="w-3 h-3" />
                Pass Network
              </button>
              <button
                className={`btn-secondary text-[10px] py-1 px-2.5 ${activeTool === TOOL_HEATMAP ? 'bg-brand-50 text-brand-700 border-brand-300' : ''}`}
                onClick={() => setActiveTool(TOOL_HEATMAP)}
              >
                <Crosshair className="w-3 h-3" />
                Heatmap
              </button>
              <button
                className={`btn-secondary text-[10px] py-1 px-2.5 ${activeTool === TOOL_ZONES ? 'bg-brand-50 text-brand-700 border-brand-300' : ''}`}
                onClick={() => setActiveTool(TOOL_ZONES)}
              >
                <Grid3X3 className="w-3 h-3" />
                Press Zones
              </button>
              <div className="w-px h-4 bg-slate-200 mx-1" />
              <button
                className={`btn-secondary text-[10px] py-1 px-2.5 ${passLinesVisible ? 'bg-brand-50 text-brand-700 border-brand-300' : ''}`}
                onClick={togglePassLines}
              >
                <GitCompareArrows className="w-3 h-3" />
                Pass Lines
              </button>
              <button className="btn-secondary text-[10px] py-1 px-2.5" onClick={resetView}>
                <Minimize2 className="w-3 h-3" />
                Reset
              </button>
              <span className="ml-auto text-[10px] font-mono text-slate-400">
                {data.formation} &middot; {mc.home_team} vs {mc.away_team} &middot; MD{mc.match_week}
              </span>
            </div>

            {/* SVG Pitch */}
            <div className="relative bg-[#0a1a0e]" style={{ minHeight: 420 }}
              onMouseMove={handleDragMove}
              onMouseUp={handleDragEnd}
              onMouseLeave={handleDragEnd}
            >
              <svg ref={svgRef} viewBox="0 0 700 480" className="w-full select-none" xmlns="http://www.w3.org/2000/svg">
                {/* Pitch Background */}
                <rect width="700" height="480" fill="#0a1a0e" />
                {/* Stripes */}
                <g opacity="0.06">
                  {[0, 96, 192, 288, 384].map(y => (
                    <rect key={y} x="0" y={y} width="700" height="48" fill="#00D084" />
                  ))}
                </g>
                {/* Pitch outline */}
                <rect x="40" y="20" width="620" height="440" fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth="1.5" />
                <line x1="40" y1="240" x2="660" y2="240" stroke="rgba(255,255,255,0.18)" strokeWidth="1.2" />
                <circle cx="350" cy="240" r="60" fill="none" stroke="rgba(255,255,255,0.18)" strokeWidth="1.2" />
                <circle cx="350" cy="240" r="3" fill="rgba(255,255,255,0.3)" />
                {/* Penalty areas */}
                <rect x="40" y="150" width="110" height="180" fill="none" stroke="rgba(255,255,255,0.18)" strokeWidth="1.2" />
                <rect x="550" y="150" width="110" height="180" fill="none" stroke="rgba(255,255,255,0.18)" strokeWidth="1.2" />
                <rect x="40" y="190" width="45" height="100" fill="none" stroke="rgba(255,255,255,0.12)" strokeWidth="1" />
                <rect x="615" y="190" width="45" height="100" fill="none" stroke="rgba(255,255,255,0.12)" strokeWidth="1" />
                <rect x="22" y="208" width="18" height="64" fill="none" stroke="rgba(255,255,255,0.3)" strokeWidth="1.5" />
                <rect x="660" y="208" width="18" height="64" fill="none" stroke="rgba(255,255,255,0.3)" strokeWidth="1.5" />
                <circle cx="150" cy="240" r="2.5" fill="rgba(255,255,255,0.3)" />
                <circle cx="550" cy="240" r="2.5" fill="rgba(255,255,255,0.3)" />

                {/* HEATMAP LAYER */}
                {activeTool === TOOL_HEATMAP && heatmapGrid.length > 0 && (
                  <g opacity="0.6">
                    {heatmapGrid.map((col, cx) =>
                      col.map((val, cy) =>
                        val > 0.05 ? (
                          <rect
                            key={`${cx}-${cy}`}
                            x={40 + (cx / 20) * 620}
                            y={20 + (cy / 15) * 440}
                            width={620 / 20}
                            height={440 / 15}
                            fill={val > 0.5 ? '#00D084' : '#58A6FF'}
                            opacity={Math.min(0.5, val * 0.7)}
                          />
                        ) : null
                      )
                    )}
                  </g>
                )}

                {/* PRESS ZONES */}
                {activeTool === TOOL_ZONES && (
                  <g opacity="0.6">
                    <rect x="450" y="20" width="210" height="200" fill="rgba(248,81,73,0.08)" rx="4" />
                    <text x="555" y="65" fill="rgba(248,81,73,0.7)" fontSize="9" fontFamily="Inter, sans-serif" textAnchor="middle" fontWeight="700">HIGH PRESS</text>
                    <rect x="450" y="260" width="210" height="200" fill="rgba(248,81,73,0.08)" rx="4" />
                    <text x="555" y="305" fill="rgba(248,81,73,0.7)" fontSize="9" fontFamily="Inter, sans-serif" textAnchor="middle" fontWeight="700">HIGH PRESS</text>
                    <rect x="220" y="100" width="220" height="280" fill="rgba(88,166,255,0.06)" rx="4" />
                    <text x="330" y="245" fill="rgba(88,166,255,0.5)" fontSize="9" fontFamily="Inter, sans-serif" textAnchor="middle" fontWeight="700">MID BLOCK</text>
                  </g>
                )}

                {/* PASS LINES */}
                {(passLinesVisible || activeTool === TOOL_PASSES) && passNetwork.length > 0 && (
                  <g opacity={0.7}>
                    {passNetwork.slice(0, 30).map((pn, i) => {
                      const fromPlayer = players.find(p => p.player_id === pn.from_player_id);
                      const toPlayer = players.find(p => p.player_id === pn.to_player_id);
                      if (!fromPlayer || !toPlayer) return null;
                      const fp = getPlayerPos(fromPlayer);
                      const tp = getPlayerPos(toPlayer);
                      const thickness = 1 + (pn.count / maxPassCount) * 7;
                      const isHigh = pn.count > maxPassCount * 0.4;
                      return (
                        <line
                          key={i}
                          x1={fp.svg_x} y1={fp.svg_y}
                          x2={tp.svg_x} y2={tp.svg_y}
                          stroke={isHigh ? 'rgba(0,208,132,0.6)' : 'rgba(88,166,255,0.3)'}
                          strokeWidth={thickness}
                          strokeLinecap="round"
                        />
                      );
                    })}
                  </g>
                )}

                {/* PLAYER TOKENS */}
                {players.map(p => {
                  const c = playerColor(p);
                  const isSelected = selectedPlayer?.player_id === p.player_id;
                  const radius = p.position_group === 'Goalkeeper' ? 17 : 15;
                  const pos = getPlayerPos(p);
                  const isDragging = dragRef.current?.playerId === p.player_id;
                  return (
                    <g
                      key={p.player_id}
                      className="transition-opacity hover:opacity-90"
                      style={{ cursor: isDragging ? 'grabbing' : 'grab' }}
                      onMouseDown={(e) => { handleDragStart(e, p); selectPlayer(p); }}
                    >
                      {/* Selection glow */}
                      {isSelected && (
                        <circle cx={pos.svg_x} cy={pos.svg_y} r={radius + 4} fill="none" stroke={c.stroke} strokeWidth="2" opacity="0.5" />
                      )}
                      <circle cx={pos.svg_x} cy={pos.svg_y} r={radius + (isSelected ? 2 : 0)} fill={c.bg} stroke={c.stroke} strokeWidth={isSelected ? 2.5 : 1.5} />
                      <text x={pos.svg_x} y={pos.svg_y - 3} fill={c.text} fontSize="9" fontFamily="Inter, sans-serif" fontWeight="700" textAnchor="middle">
                        {p.initials}
                      </text>
                      <text x={pos.svg_x} y={pos.svg_y + 8} fill="rgba(255,255,255,0.5)" fontSize="7" fontFamily="JetBrains Mono, monospace" textAnchor="middle">
                        {p.jersey_number}
                      </text>
                      <text x={pos.svg_x} y={pos.svg_y + 21} fill="#8B949E" fontSize="7.5" fontFamily="Inter, sans-serif" textAnchor="middle">
                        {p.overall_score?.toFixed(1)}
                      </text>
                    </g>
                  );
                })}

                {/* Direction arrow */}
                <g opacity="0.2">
                  <line x1="300" y1="462" x2="420" y2="462" stroke="white" strokeWidth="1" />
                  <polygon points="420,458 428,462 420,466" fill="white" />
                  <text x="364" y="459" fill="white" fontSize="8" fontFamily="Inter, sans-serif" textAnchor="middle">Attack</text>
                </g>
              </svg>
            </div>

            {/* Footer legend */}
            <div className="flex items-center gap-4 px-3.5 py-2.5 border-t border-slate-200 bg-white/50 flex-wrap">
              <span className="flex items-center gap-1.5 text-[10px] text-slate-500">
                <span className="w-3 h-3 rounded-full inline-block" style={{ background: POS_COLORS.Goalkeeper.bg, border: `1.5px solid ${POS_COLORS.Goalkeeper.stroke}` }} />
                GK / MF
              </span>
              <span className="flex items-center gap-1.5 text-[10px] text-slate-500">
                <span className="w-3 h-3 rounded-full inline-block" style={{ background: POS_COLORS.Defender.bg, border: `1.5px solid ${POS_COLORS.Defender.stroke}` }} />
                Defenders
              </span>
              <span className="flex items-center gap-1.5 text-[10px] text-slate-500">
                <span className="w-3 h-3 rounded-full inline-block" style={{ background: POS_COLORS.Attacker.bg, border: `1.5px solid ${POS_COLORS.Attacker.stroke}` }} />
                Forwards
              </span>
              <span className="flex items-center gap-1.5 text-[10px] text-slate-500">
                <span className="w-5 h-0.5 inline-block" style={{ background: '#00D084' }} />
                Key Passes
              </span>
              <span className="ml-auto text-[10px] font-mono text-slate-400">
                Selected: {selectedPlayer ? `${selectedPlayer.player_name} (#${selectedPlayer.jersey_number})` : 'None'}
              </span>
            </div>
          </div>
        </div>

        {/* Right Panel */}
        <div className="w-72 shrink-0">
          {/* Panel Tabs */}
          <div className="flex gap-1 mb-3">
            {['info', 'formation', 'notes'].map(tab => (
              <button
                key={tab}
                className={`px-3 py-1.5 rounded-md text-[11px] font-semibold transition-colors ${
                  panelTab === tab
                    ? 'bg-brand-50 text-brand-700 border border-brand-200'
                    : 'text-slate-500 hover:bg-slate-100 border border-transparent'
                }`}
                onClick={() => setPanelTab(tab)}
              >
                {tab === 'info' ? 'Player Info' : tab === 'formation' ? 'Formation' : 'Notes'}
              </button>
            ))}
          </div>

          {/* PLAYER INFO PANEL */}
          {panelTab === 'info' && (
            <div>
              {selectedPlayer ? (() => {
                const p = selectedPlayer;
                const c = playerColor(p);
                const st = p.stats || {};
                return (
                  <>
                    <div className="surface rounded-xl p-4 mb-3">
                      <div className="flex items-center gap-3 mb-3">
                        <div
                          className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-black shrink-0"
                          style={{ background: c.bg, color: c.stroke, border: `2px solid ${c.stroke}` }}
                        >
                          {p.initials}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-bold text-slate-800 truncate">{p.player_name}</div>
                          <div className="text-[10px] text-slate-500">#{p.jersey_number} &middot; {p.position_group}</div>
                        </div>
                        <div className="text-right">
                          <div className="text-xl font-black font-mono" style={{ color: c.stroke }}>{p.overall_score?.toFixed(1)}</div>
                          <div className="text-[8px] text-slate-400 uppercase tracking-wider">ML Score</div>
                        </div>
                      </div>

                      {/* Stat bars */}
                      {[
                        { label: 'xG / 90', value: st.total_xg, pct: Math.min((st.total_xg || 0) * 100, 100), color: '#00D084' },
                        { label: 'Pass Acc.', value: st.pass_accuracy ? `${st.pass_accuracy.toFixed(0)}%` : null, pct: Math.min(st.pass_accuracy || 0, 100), color: '#58A6FF' },
                        { label: 'Key Passes', value: st.key_passes, pct: Math.min((st.key_passes || 0) * 20, 100), color: '#BC8CFF' },
                        { label: 'Shots', value: st.shots, pct: Math.min((st.shots || 0) * 20, 100), color: '#FF8C42' },
                        { label: 'Distance (km)', value: st.distance_covered ? (st.distance_covered / 1000).toFixed(1) : null, pct: Math.min((st.distance_covered || 0) / 100, 100), color: '#F85149' },
                      ].map((stat, i) => (
                        stat.value != null ? (
                          <div key={i} className="flex items-center gap-2 mb-1.5">
                            <span className="text-[9px] text-slate-500 w-20 shrink-0">{stat.label}</span>
                            <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                              <div className="h-full rounded-full transition-all" style={{ width: `${stat.pct}%`, background: stat.color }} />
                            </div>
                            <span className="text-[10px] font-mono text-slate-600 w-10 text-right">{stat.value}</span>
                          </div>
                        ) : null
                      ))}

                      <div className="mt-3 p-2.5 bg-slate-50 rounded-lg border-l-2" style={{ borderColor: c.stroke }}>
                        <div className="text-[8px] font-bold uppercase tracking-wider mb-0.5" style={{ color: c.stroke }}>Tactical Role</div>
                        <div className="text-[10px] text-slate-600 leading-relaxed">
                          {p.position_group === 'Goalkeeper' && 'Sweeper keeper — comfortable on the ball. Contributes to build-up.'}
                          {p.position_group === 'Defender' && 'Solid defensive presence. Provides width and supports build-up from the back.'}
                          {p.position_group === 'Midfielder' && 'Controls tempo and links play between defense and attack. Covers significant distance.'}
                          {p.position_group === 'Attacker' && 'Creative force in the final third. Drifts into half-spaces and creates goal-scoring opportunities.'}
                        </div>
                      </div>
                    </div>

                    <div className="surface rounded-xl p-4">
                      <h4 className="text-xs font-bold text-slate-700 mb-2">Match Stats &mdash; MD{mc.match_week}</h4>
                      <div className="grid grid-cols-2 gap-2">
                        {[
                          { label: 'Goals', value: st.goals, color: '#00D084' },
                          { label: 'Passes', value: st.passes, color: '#58A6FF' },
                          { label: 'Dribbles', value: st.successful_dribbles != null ? `${st.successful_dribbles}/${st.total_dribbles}` : null, color: '#BC8CFF' },
                          { label: 'VAEP', value: st.vaep_rating?.toFixed(2), color: '#FF8C42' },
                          { label: 'Pressures', value: st.pressures, color: '#F85149' },
                          { label: 'Ball Receipts', value: st.ball_receipts, color: '#39D0D0' },
                        ].map((s, i) => (
                          s.value != null ? (
                            <div key={i} className="bg-slate-50 rounded-lg p-2.5 text-center">
                              <div className="text-base font-black font-mono" style={{ color: s.color }}>{s.value}</div>
                              <div className="text-[8px] text-slate-500 uppercase tracking-wider">{s.label}</div>
                            </div>
                          ) : null
                        ))}
                      </div>
                    </div>
                  </>
                );
              })() : (
                <div className="surface rounded-xl p-6 text-center">
                  <Target className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                  <p className="text-xs text-slate-500">Select a player on the pitch to view stats</p>
                </div>
              )}
            </div>
          )}

          {/* FORMATION PANEL */}
          {panelTab === 'formation' && (
            <div>
              <div className="surface rounded-xl p-4 mb-3">
                <h4 className="text-xs font-bold text-slate-700 mb-3">Change Formation</h4>
                <div className="grid grid-cols-2 gap-1.5 mb-3">
                  {FORMATIONS.map(f => (
                    <button
                      key={f}
                      className={`py-1.5 px-2 rounded-md text-[11px] font-bold font-mono transition-colors ${
                        data.formation === f
                          ? 'bg-brand-50 text-brand-700 border border-brand-200'
                          : 'bg-slate-100 text-slate-600 hover:bg-slate-200 border border-transparent'
                      }`}
                      onClick={() => changeFormation(f)}
                    >
                      {f}
                    </button>
                  ))}
                </div>
                <div className="p-2.5 bg-slate-50 rounded-lg text-[10px] text-slate-600">
                  Current: <span className="text-brand-600 font-bold font-mono">{data.formation}</span> &middot; Based on match lineup
                </div>
              </div>

              <div className="surface rounded-xl p-4">
                <h4 className="text-xs font-bold text-slate-700 mb-2">Overlay Match</h4>
                <select className="field text-xs py-1.5 w-full mb-2">
                  {availableMatches.slice(0, 5).map(am => (
                    <option key={am.match_id} value={am.match_id}>{am.label}</option>
                  ))}
                  <option disabled>&mdash; More &mdash;</option>
                </select>
                <button className="btn-secondary text-xs py-1.5 w-full justify-center flex items-center gap-1.5">
                  <Target className="w-3 h-3" />
                  Apply Overlay
                </button>
              </div>
            </div>
          )}

          {/* NOTES PANEL */}
          {panelTab === 'notes' && (
            <div>
              {notes.map((n, i) => (
                <div
                  key={i}
                  className="p-3 bg-slate-50 rounded-lg mb-2 border-l-2"
                  style={{
                    borderLeftColor: n.type === 'att' || n.type === 'opp' ? '#00D084' :
                      n.type === 'def' ? '#58A6FF' : '#D29922'
                  }}
                >
                  <div className="text-[8px] font-bold uppercase tracking-wider mb-0.5"
                    style={{
                      color: n.type === 'att' || n.type === 'opp' ? '#00D084' :
                        n.type === 'def' ? '#58A6FF' : '#D29922'
                    }}
                  >
                    {n.icon} {n.title}
                  </div>
                  <div className="text-[10px] text-slate-600 leading-relaxed">{n.text}</div>
                </div>
              ))}
              <button className="btn-secondary text-xs py-1.5 w-full justify-center flex items-center gap-1.5 mt-1">
                <span className="text-lg leading-none">+</span>
                Add Note
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TacticalBoard;
