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
  getPlayerList: async () => {
    try {
      const response = await apiClient.get('/player/list');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch player list: ${error.message}`);
    }
  },

  // Get player dashboard with 9 charts
  getPlayerDashboard: async (playerName, matchId = null) => {
    try {
      const query = matchId ? `?match_id=${encodeURIComponent(matchId)}` : '';
      const response = await apiClient.get(
        `/player/dashboard/${encodeURIComponent(playerName)}${query}`,
        { timeout: 180000 }
      );
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch player dashboard for ${playerName}: ${error.message}`);
    }
  },

  // Get player dashboard raw data for frontend rendering with animation
  getPlayerDashboardData: async (playerName, matchId = null) => {
    try {
      const query = matchId ? `?match_id=${encodeURIComponent(matchId)}` : '';
      const response = await apiClient.get(
        `/player/dashboard-data/${encodeURIComponent(playerName)}${query}`,
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
  getAdvancedAnalysis: async (playerId) => {
    try {
      const response = await apiClient.get(`/player/${playerId}/advanced`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch advanced analysis: ${error.message}`);
    }
  },

  getForecast: async (playerId) => {
    try {
      const response = await apiClient.get(`/player/${playerId}/forecast`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch forecast: ${error.message}`);
    }
  },

  getAnomalies: async (playerId) => {
    try {
      const response = await apiClient.get(`/player/${playerId}/anomalies`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch anomalies: ${error.message}`);
    }
  },

  getSimilarPlayers: async (playerId, topN = 8) => {
    try {
      const response = await apiClient.get(`/player/${playerId}/similar?top_n=${topN}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch similar players: ${error.message}`);
    }
  },

  getConsistency: async (playerId) => {
    try {
      const response = await apiClient.get(`/player/${playerId}/consistency`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch consistency: ${error.message}`);
    }
  },

  getMomentum: async (playerId) => {
    try {
      const response = await apiClient.get(`/player/${playerId}/momentum`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch momentum: ${error.message}`);
    }
  },

  getInjuryRisk: async (playerId) => {
    try {
      const response = await apiClient.get(`/player/${playerId}/injury-risk`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch injury risk: ${error.message}`);
    }
  },

  getTopPerformers: async (sortBy = 'overall_score', position = null, minMatches = 5) => {
    try {
      let query = `/analysis/top-performers?sort_by=${sortBy}&min_matches=${minMatches}`;
      if (position) query += `&position=${encodeURIComponent(position)}`;
      const response = await apiClient.get(query);
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
  getSquadOverview: async (matchId = null) => {
    try {
      const query = matchId ? `?match_id=${encodeURIComponent(matchId)}` : '';
      const response = await apiClient.get(`/player/squad-scores${query}`);
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
  getHeadToHead: async (p1Id, p2Id, context = 'season', matchId = null) => {
    try {
      let query = `?p1=${p1Id}&p2=${p2Id}&context=${context}`;
      if (matchId) query += `&match_id=${matchId}`;
      const response = await apiClient.get(`/player/head-to-head${query}`, { timeout: 120000 });
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
  getPlayerProfile: async (playerName, matchId = null) => {
    try {
      const query = matchId ? `?match_id=${encodeURIComponent(matchId)}` : '';
      const response = await apiClient.get(`/player/profile/${encodeURIComponent(playerName)}${query}`, { timeout: 180000 });
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch player profile: ${error.message}`);
    }
  },
};

/**
 * Health Check
 */
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

export default apiClient;
