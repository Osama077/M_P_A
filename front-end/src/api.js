/**
 * API Client for Match Performance Analysis Backend
 * Communicates with FastAPI server at http://localhost:8000/api/v1
 */

import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Error interceptor for consistent error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

/**
 * PLAYER ENDPOINTS
 */
export const PlayerAPI = {
  // Get list of all players
  getPlayerList: async (season = null) => {
    try {
      const params = new URLSearchParams();
      if (season) params.set('season', season);
      const qs = params.toString();
      const response = await apiClient.get(`/player/list${qs ? '?' + qs : ''}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch player list: ${error.message}`);
    }
  },

  // Get player dashboard with 9 charts
  getPlayerDashboard: async (playerName, matchId = null, season = null) => {
    try {
      const params = new URLSearchParams();
      if (matchId) params.set('match_id', matchId);
      if (season) params.set('season', season);
      const qs = params.toString();
      const response = await apiClient.get(
        `/player/dashboard/${encodeURIComponent(playerName)}${qs ? '?' + qs : ''}`,
        { timeout: 180000 }
      );
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch player dashboard for ${playerName}: ${error.message}`);
    }
  },

  // Get player dashboard raw data for frontend rendering with animation
  getPlayerDashboardData: async (playerName, matchId = null, season = null) => {
    try {
      const params = new URLSearchParams();
      if (matchId) params.set('match_id', matchId);
      if (season) params.set('season', season);
      const qs = params.toString();
      const response = await apiClient.get(
        `/player/dashboard-data/${encodeURIComponent(playerName)}${qs ? '?' + qs : ''}`,
        { timeout: 180000 }
      );
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch player dashboard data for ${playerName}: ${error.message}`);
    }
  },

  // Get player score
  getPlayerScore: async (playerId) => {
    try {
      const response = await apiClient.get(`/player/${playerId}/score`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch player score: ${error.message}`);
    }
  },

  // Get player stats
  getPlayerStats: async (playerId) => {
    try {
      const response = await apiClient.get(`/player/${playerId}/stats`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch player stats: ${error.message}`);
    }
  },

  // Get player history
  getPlayerHistory: async (playerId) => {
    try {
      const response = await apiClient.get(`/player/${playerId}/history`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch player history: ${error.message}`);
    }
  },

  // Compare multiple players
  comparePlayer: async (playerIds) => {
    try {
      // Format: "1,2,3"
      const queryString = playerIds.join(',');
      const response = await apiClient.get(`/player/compare?player_ids=${queryString}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to compare players: ${error.message}`);
    }
  },
};

/**
 * TEAM ENDPOINTS
 */
export const TeamAPI = {
  // Get team summary
  getTeamSummary: async (teamId) => {
    try {
      const response = await apiClient.get(`/team/${encodeURIComponent(teamId)}/summary`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch team summary: ${error.message}`);
    }
  },

  // Get team heatmap data
  getTeamHeatmap: async (teamId, matchId, playerId = null) => {
    try {
      if (!matchId) {
        throw new Error('matchId is required for team heatmap');
      }
      const params = new URLSearchParams({ match_id: String(matchId) });
      if (playerId !== null && playerId !== undefined) {
        params.append('player_id', String(playerId));
      }
      const response = await apiClient.get(
        `/team/${encodeURIComponent(teamId)}/heatmap?${params.toString()}`
      );
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch team heatmap: ${error.message}`);
    }
  },
};

/**
 * MATCH ENDPOINTS
 */
export const MatchAPI = {
  // Get match report
  getMatchReport: async (matchId) => {
    try {
      const response = await apiClient.get(`/match/${matchId}/report`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch match report: ${error.message}`);
    }
  },

  // Get match events
  getMatchEvents: async (matchId) => {
    try {
      const response = await apiClient.get(`/match/${matchId}/events`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch match events: ${error.message}`);
    }
  },
};

/**
 * ANALYSIS ENDPOINTS
 */
export const AnalysisAPI = {
  // Analyze specific match
  analyzeMatch: async (matchId) => {
    try {
      const response = await apiClient.post(`/analyze/match/${matchId}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to analyze match: ${error.message}`);
    }
  },

  // Analyze season
  analyzeSeason: async () => {
    try {
      const response = await apiClient.post('/analyze/season');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to analyze season: ${error.message}`);
    }
  },
};

/**
 * BENCHMARK ENDPOINTS
 */
export const BenchmarkAPI = {
  // Get benchmark for position
  getBenchmark: async (position) => {
    try {
      const response = await apiClient.get(`/benchmark/${position}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch benchmark for ${position}: ${error.message}`);
    }
  },
};

/**
 * ADVANCED ANALYSIS ENDPOINTS
 */
export const AdvancedAnalysisAPI = {
  getAdvancedAnalysis: async (playerId, season = null) => {
    try {
      const params = season ? `?season=${encodeURIComponent(season)}` : '';
      const response = await apiClient.get(`/player/${playerId}/advanced${params}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch advanced analysis: ${error.message}`);
    }
  },

  getForecast: async (playerId, season = null) => {
    try {
      const params = season ? `?season=${encodeURIComponent(season)}` : '';
      const response = await apiClient.get(`/player/${playerId}/forecast${params}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch forecast: ${error.message}`);
    }
  },

  getAnomalies: async (playerId, season = null) => {
    try {
      const params = season ? `?season=${encodeURIComponent(season)}` : '';
      const response = await apiClient.get(`/player/${playerId}/anomalies${params}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch anomalies: ${error.message}`);
    }
  },

  getSimilarPlayers: async (playerId, topN = 8, season = null) => {
    try {
      const params = new URLSearchParams({ top_n: topN });
      if (season) params.set('season', season);
      const response = await apiClient.get(`/player/${playerId}/similar?${params.toString()}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch similar players: ${error.message}`);
    }
  },

  getConsistency: async (playerId, season = null) => {
    try {
      const params = season ? `?season=${encodeURIComponent(season)}` : '';
      const response = await apiClient.get(`/player/${playerId}/consistency${params}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch consistency: ${error.message}`);
    }
  },

  getMomentum: async (playerId, season = null) => {
    try {
      const params = season ? `?season=${encodeURIComponent(season)}` : '';
      const response = await apiClient.get(`/player/${playerId}/momentum${params}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch momentum: ${error.message}`);
    }
  },

  getInjuryRisk: async (playerId, season = null) => {
    try {
      const params = season ? `?season=${encodeURIComponent(season)}` : '';
      const response = await apiClient.get(`/player/${playerId}/injury-risk${params}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch injury risk: ${error.message}`);
    }
  },

  getTopPerformers: async (sortBy = 'overall_score', position = null, minMatches = 5, season = null) => {
    try {
      const params = new URLSearchParams({ sort_by: sortBy, min_matches: minMatches });
      if (position) params.set('position', position);
      if (season) params.set('season', season);
      const response = await apiClient.get(`/analysis/top-performers?${params.toString()}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch top performers: ${error.message}`);
    }
  },
};

/**
 * SQUAD ENDPOINTS
 */
export const SquadAPI = {
  getSquadOverview: async (matchId = null, season = null) => {
    try {
      const params = new URLSearchParams();
      if (matchId) params.set('match_id', matchId);
      if (season) params.set('season', season);
      const qs = params.toString();
      const response = await apiClient.get(`/player/squad-scores${qs ? '?' + qs : ''}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch squad overview: ${error.message}`);
    }
  },
};

/**
 * HEAD-TO-HEAD COMPARISON ENDPOINT
 */
export const CompareAPI = {
  getHeadToHead: async (p1Id, p2Id, context = 'season', matchId = null, season = null) => {
    try {
      const params = new URLSearchParams({ p1: p1Id, p2: p2Id, context });
      if (matchId) params.set('match_id', matchId);
      if (season) params.set('season', season);
      const response = await apiClient.get(`/player/head-to-head?${params.toString()}`, { timeout: 120000 });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch comparison: ${error.message}`);
    }
  },
};

/**
 * PLAYER PROFILE ENDPOINT
 */
export const PlayerProfileAPI = {
  getPlayerProfile: async (playerName, matchId = null, season = null) => {
    try {
      const params = new URLSearchParams();
      if (matchId) params.set('match_id', matchId);
      if (season) params.set('season', season);
      const qs = params.toString();
      const response = await apiClient.get(`/player/profile/${encodeURIComponent(playerName)}${qs ? '?' + qs : ''}`, { timeout: 180000 });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch player profile: ${error.message}`);
    }
  },
};

/**
 * SEASON TRENDS ENDPOINT
 */
export const SeasonTrendsAPI = {
  getSeasonTrends: async (season = null) => {
    try {
      const params = season ? `?season=${encodeURIComponent(season)}` : '';
      const response = await apiClient.get(`/player/season-trends${params}`, { timeout: 120000 });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch season trends: ${error.message}`);
    }
  },
};

/**
 * MATCH LOG ENDPOINT
 */
export const MatchLogAPI = {
  getMatchLog: async (matchId = null, season = null) => {
    try {
      const params = new URLSearchParams();
      if (matchId) params.set('match_id', matchId);
      if (season) params.set('season', season);
      const qs = params.toString();
      const response = await apiClient.get(`/player/match-log${qs ? '?' + qs : ''}`, { timeout: 120000 });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch match log: ${error.message}`);
    }
  },
};

/**
 * TACTICAL BOARD ENDPOINT
 */
export const TacticalBoardAPI = {
  getTacticalBoard: async (matchId = null, season = null) => {
    try {
      const params = new URLSearchParams();
      if (matchId) params.set('match_id', matchId);
      if (season) params.set('season', season);
      const qs = params.toString();
      const response = await apiClient.get(`/player/tactical-board${qs ? '?' + qs : ''}`, { timeout: 120000 });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch tactical board: ${error.message}`);
    }
  },
};

/**
 * Health Check
 */
/**
 * NEW FEATURES ENDPOINTS
 */
export const MetadataAPI = {
  listPlayers: async (season) => {
    try {
      const query = season ? `?season=${encodeURIComponent(season)}` : '';
      const response = await apiClient.get(`/metadata/players${query}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch metadata: ${error.message}`);
    }
  },
  getPlayer: async (playerId) => {
    try {
      const response = await apiClient.get(`/metadata/players/${playerId}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch player metadata: ${error.message}`);
    }
  },
  searchPlayers: async (query) => {
    try {
      const response = await apiClient.get(`/metadata/player/search?query=${encodeURIComponent(query)}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to search metadata: ${error.message}`);
    }
  },
};

export const SeasonAPI = {
  listSeasons: async () => {
    try {
      const response = await apiClient.get('/player/season/list');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch seasons: ${error.message}`);
    }
  },
};

export const EvolutionAPI = {
  getEvolution: async (playerId, season) => {
    try {
      const query = season ? `?season=${encodeURIComponent(season)}` : '';
      const response = await apiClient.get(`/player/${playerId}/evolution${query}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch evolution: ${error.message}`);
    }
  },
};

export const HealthAPI = {
  checkHealth: async () => {
    try {
      const response = await apiClient.get('/');
      return response.data;
    } catch (error) {
      console.error('API health check failed:', error.message);
      return null;
    }
  },
};

/**
 * COACHING INSIGHTS ENDPOINTS
 */
export const CoachingAPI = {
  getSquadInsights: async () => {
    try {
      const response = await apiClient.get('/coaching/squad', { timeout: 120000 });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch squad coaching insights: ${error.message}`);
    }
  },

  getPlayerCoaching: async (playerId, season = null) => {
    try {
      const params = season ? `?season=${encodeURIComponent(season)}` : '';
      const response = await apiClient.get(`/coaching/player/${playerId}${params}`, { timeout: 120000 });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch player coaching advice: ${error.message}`);
    }
  },

  getPlayerComprehensive: async (playerId, season = null) => {
    try {
      const params = season ? `?season=${encodeURIComponent(season)}` : '';
      const response = await apiClient.get(`/coaching/player/${playerId}/comprehensive${params}`, { timeout: 120000 });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch comprehensive player insights: ${error.message}`);
    }
  },
};

/**
 * MATCH PREDICTION ENDPOINTS
 */
export const PredictionAPI = {
  getPlayerPrediction: async (playerId, season = null) => {
    try {
      const params = season ? `?season=${encodeURIComponent(season)}` : '';
      const response = await apiClient.get(`/predict/player/${playerId}${params}`, { timeout: 120000 });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch player prediction: ${error.message}`);
    }
  },

  getSquadPrediction: async () => {
    try {
      const response = await apiClient.get('/predict/squad', { timeout: 120000 });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch squad prediction: ${error.message}`);
    }
  },
};

/**
 * DATA VALIDATION ENDPOINTS
 */
export const ValidationAPI = {
  getMetricsValidation: async () => {
    try {
      const response = await apiClient.get('/validate/metrics', { timeout: 120000 });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch validation findings: ${error.message}`);
    }
  },

  getFormulasValidation: async () => {
    try {
      const response = await apiClient.get('/validate/formulas', { timeout: 120000 });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch formula validation: ${error.message}`);
    }
  },
};

export default apiClient;
