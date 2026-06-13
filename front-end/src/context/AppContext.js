import React, { createContext, useContext, useMemo, useState, useCallback } from 'react';

const AppContext = createContext(null);

export const PAGES = {
  OVERVIEW: 'overview',
  PLAYERS: 'players',
  DASHBOARD: 'dashboard',
  ANIMATED: 'animated',
  COMPARISON: 'comparison',
  API_TESTER: 'api_tester',
  FORECAST: 'forecast',
  SIMILARITY: 'similarity',
  MOMENTUM: 'momentum',
  ANOMALIES: 'anomalies',
  CONSISTENCY: 'consistency',
  TOP_PERFORMERS: 'top_performers',
  SQUAD_OVERVIEW: 'squad_overview',
  SEASON_TRENDS: 'season_trends',
  MATCH_LOG: 'match_log',
  WHATS_NEW: 'whats_new',
  COACHING: 'coaching',
  PREDICTION: 'prediction',
  DATA_VALIDATION: 'data_validation',
  POSITION: 'position',
};

export const USER_ROLES = {
  ANALYST: 'analyst',
  COACH: 'coach',
  ADMIN: 'admin',
};

export function AppProvider({ children }) {
  const [currentPage, setCurrentPage] = useState(PAGES.OVERVIEW);
  const [selectedPlayerName, setSelectedPlayerName] = useState('');
  const [selectedPlayerId, setSelectedPlayerId] = useState(null);
  const [selectedMatchId, setSelectedMatchId] = useState(null);
  const [selectedSeason, setSelectedSeason] = useState(null);
  const [seasonOptions, setSeasonOptions] = useState([]);
  const [userRole, setUserRole] = useState(USER_ROLES.ANALYST);

  const navigate = useCallback((page) => setCurrentPage(page), []);

  const openPlayerDashboard = useCallback((playerName, playerId, matchId = null) => {
    setSelectedPlayerName(playerName);
    setSelectedPlayerId(playerId);
    setSelectedMatchId(matchId);
    setCurrentPage(PAGES.DASHBOARD);
  }, []);

  const openAdvancedAnalysis = useCallback((page, playerName, playerId) => {
    setSelectedPlayerName(playerName);
    setSelectedPlayerId(playerId);
    setCurrentPage(page);
  }, []);

  const value = useMemo(
    () => ({
      currentPage,
      selectedPlayerName,
      selectedPlayerId,
      selectedMatchId,
      selectedSeason,
      seasonOptions,
      userRole,
      navigate,
      setUserRole,
      setSelectedMatchId,
      setSelectedSeason,
      setSeasonOptions,
      openPlayerDashboard,
      openAdvancedAnalysis,
    }),
    [currentPage, selectedPlayerName, selectedPlayerId, selectedMatchId, selectedSeason, seasonOptions, userRole, navigate, setUserRole, setSelectedMatchId, setSelectedSeason, setSeasonOptions, openPlayerDashboard, openAdvancedAnalysis]
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useAppContext() {
  const ctx = useContext(AppContext);
  if (!ctx) {
    throw new Error('useAppContext must be used within AppProvider');
  }
  return ctx;
}
