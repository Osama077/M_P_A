import axios from 'axios';

jest.mock('axios', () => {
  const instance = {
    get: jest.fn(),
    post: jest.fn(),
    interceptors: { request: { use: jest.fn() }, response: { use: jest.fn() } },
  };
  return { create: jest.fn(() => instance), isCancel: jest.fn(() => false) };
});

const mockAxiosInstance = axios.create();

import {
  PlayerAPI, TeamAPI, MatchAPI, AnalysisAPI, BenchmarkAPI,
  AdvancedAnalysisAPI, HealthAPI,
} from '../api';

beforeEach(() => {
  mockAxiosInstance.get.mockReset();
  mockAxiosInstance.post.mockReset();
});

describe('PlayerAPI', () => {
  test('getPlayerList returns data on success', async () => {
    const players = { player_items: [{ player_id: 1, player_name: 'Test' }] };
    mockAxiosInstance.get.mockResolvedValue({ data: players });
    const result = await PlayerAPI.getPlayerList();
    expect(result).toEqual(players);
    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/player/list');
  });

  test('getPlayerList throws on error', async () => {
    mockAxiosInstance.get.mockRejectedValue(new Error('Network error'));
    await expect(PlayerAPI.getPlayerList()).rejects.toThrow('Failed to fetch player list');
  });

  test('getPlayerDashboard calls without matchId', async () => {
    mockAxiosInstance.get.mockResolvedValue({ data: { charts: {} } });
    const result = await PlayerAPI.getPlayerDashboard('Messi');
    expect(result).toEqual({ charts: {} });
    expect(mockAxiosInstance.get).toHaveBeenCalledWith(
      '/player/dashboard/Messi', { timeout: 180000 }
    );
  });

  test('getPlayerDashboard calls with matchId', async () => {
    mockAxiosInstance.get.mockResolvedValue({ data: { charts: {} } });
    await PlayerAPI.getPlayerDashboard('Messi', 42);
    expect(mockAxiosInstance.get).toHaveBeenCalledWith(
      '/player/dashboard/Messi?match_id=42', { timeout: 180000 }
    );
  });

  test('getPlayerDashboard throws on error', async () => {
    mockAxiosInstance.get.mockRejectedValue(new Error('Not found'));
    await expect(PlayerAPI.getPlayerDashboard('Nemo')).rejects.toThrow(
      'Failed to fetch player dashboard for Nemo'
    );
  });

  test('getPlayerDashboardData calls with and without matchId', async () => {
    mockAxiosInstance.get.mockResolvedValue({ data: { charts: {} } });
    await PlayerAPI.getPlayerDashboardData('Ronaldo');
    expect(mockAxiosInstance.get).toHaveBeenCalledWith(
      '/player/dashboard-data/Ronaldo', { timeout: 180000 }
    );
    mockAxiosInstance.get.mockResolvedValue({ data: { charts: {} } });
    await PlayerAPI.getPlayerDashboardData('Ronaldo', 99);
    expect(mockAxiosInstance.get).toHaveBeenCalledWith(
      '/player/dashboard-data/Ronaldo?match_id=99', { timeout: 180000 }
    );
  });

  test('getPlayerScore succeeds', async () => {
    mockAxiosInstance.get.mockResolvedValue({ data: { score: 8.5 } });
    const result = await PlayerAPI.getPlayerScore(1);
    expect(result).toEqual({ score: 8.5 });
    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/player/1/score');
  });

  test('getPlayerScore throws on error', async () => {
    mockAxiosInstance.get.mockRejectedValue(new Error('fail'));
    await expect(PlayerAPI.getPlayerScore(1)).rejects.toThrow('Failed to fetch player score');
  });

  test('getPlayerStats succeeds', async () => {
    mockAxiosInstance.get.mockResolvedValue({ data: { goals: 10 } });
    const result = await PlayerAPI.getPlayerStats(1);
    expect(result).toEqual({ goals: 10 });
  });

  test('getPlayerHistory succeeds', async () => {
    mockAxiosInstance.get.mockResolvedValue({ data: { matches: [] } });
    const result = await PlayerAPI.getPlayerHistory(1);
    expect(result).toEqual({ matches: [] });
    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/player/1/history');
  });

  test('comparePlayer joins ids with comma', async () => {
    mockAxiosInstance.get.mockResolvedValue({ data: { comparison: [] } });
    await PlayerAPI.comparePlayer([1, 2, 3]);
    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/player/compare?player_ids=1,2,3');
  });

  test('comparePlayer throws on error', async () => {
    mockAxiosInstance.get.mockRejectedValue(new Error('fail'));
    await expect(PlayerAPI.comparePlayer([1, 2])).rejects.toThrow('Failed to compare players');
  });
});

describe('TeamAPI', () => {
  test('getTeamSummary succeeds', async () => {
    mockAxiosInstance.get.mockResolvedValue({ data: { team_name: 'Barca' } });
    const result = await TeamAPI.getTeamSummary('Barcelona');
    expect(result).toEqual({ team_name: 'Barca' });
    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/team/Barcelona/summary');
  });

  test('getTeamHeatmap with matchId only', async () => {
    mockAxiosInstance.get.mockResolvedValue({ data: {} });
    await TeamAPI.getTeamHeatmap('Barcelona', 42);
    expect(mockAxiosInstance.get).toHaveBeenCalledWith(
      '/team/Barcelona/heatmap?match_id=42'
    );
  });

  test('getTeamHeatmap with matchId and playerId', async () => {
    mockAxiosInstance.get.mockResolvedValue({ data: {} });
    await TeamAPI.getTeamHeatmap('Barcelona', 42, 7);
    expect(mockAxiosInstance.get).toHaveBeenCalledWith(
      '/team/Barcelona/heatmap?match_id=42&player_id=7'
    );
  });

  test('getTeamHeatmap throws when matchId missing', async () => {
    await expect(TeamAPI.getTeamHeatmap('Barcelona', null)).rejects.toThrow(
      'matchId is required for team heatmap'
    );
    expect(mockAxiosInstance.get).not.toHaveBeenCalled();
  });
});

describe('MatchAPI', () => {
  test('getMatchReport succeeds', async () => {
    mockAxiosInstance.get.mockResolvedValue({ data: { report: {} } });
    const result = await MatchAPI.getMatchReport(42);
    expect(result).toEqual({ report: {} });
    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/match/42/report');
  });

  test('getMatchEvents succeeds', async () => {
    mockAxiosInstance.get.mockResolvedValue({ data: { events: [] } });
    const result = await MatchAPI.getMatchEvents(42);
    expect(result).toEqual({ events: [] });
  });

  test('MatchAPI throws on error', async () => {
    mockAxiosInstance.get.mockRejectedValue(new Error('fail'));
    await expect(MatchAPI.getMatchReport(1)).rejects.toThrow('Failed to fetch match report');
    await expect(MatchAPI.getMatchEvents(1)).rejects.toThrow('Failed to fetch match events');
  });
});

describe('AnalysisAPI', () => {
  test('analyzeMatch calls POST', async () => {
    mockAxiosInstance.post.mockResolvedValue({ data: { status: 'done' } });
    const result = await AnalysisAPI.analyzeMatch(42);
    expect(result).toEqual({ status: 'done' });
    expect(mockAxiosInstance.post).toHaveBeenCalledWith('/analyze/match/42');
  });

  test('analyzeSeason calls POST', async () => {
    mockAxiosInstance.post.mockResolvedValue({ data: { season: '2024' } });
    const result = await AnalysisAPI.analyzeSeason();
    expect(result).toEqual({ season: '2024' });
    expect(mockAxiosInstance.post).toHaveBeenCalledWith('/analyze/season');
  });
});

describe('BenchmarkAPI', () => {
  test('getBenchmark calls with position', async () => {
    mockAxiosInstance.get.mockResolvedValue({ data: { percentile: 90 } });
    const result = await BenchmarkAPI.getBenchmark('Attacker');
    expect(result).toEqual({ percentile: 90 });
    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/benchmark/Attacker');
  });
});

describe('AdvancedAnalysisAPI', () => {
  const methods = [
    { name: 'getAdvancedAnalysis', endpoint: '/player/1/advanced' },
    { name: 'getForecast', endpoint: '/player/1/forecast' },
    { name: 'getAnomalies', endpoint: '/player/1/anomalies' },
    { name: 'getConsistency', endpoint: '/player/1/consistency' },
    { name: 'getMomentum', endpoint: '/player/1/momentum' },
    { name: 'getInjuryRisk', endpoint: '/player/1/injury-risk' },
  ];

  methods.forEach(({ name, endpoint }) => {
    test(`${name} succeeds`, async () => {
      mockAxiosInstance.get.mockResolvedValue({ data: { result: 'ok' } });
      const result = await AdvancedAnalysisAPI[name](1);
      expect(result).toEqual({ result: 'ok' });
      expect(mockAxiosInstance.get).toHaveBeenCalledWith(endpoint);
    });

    test(`${name} throws on error`, async () => {
      mockAxiosInstance.get.mockRejectedValue(new Error('fail'));
      await expect(AdvancedAnalysisAPI[name](1)).rejects.toThrow();
    });
  });

  test('getSimilarPlayers with default topN', async () => {
    mockAxiosInstance.get.mockResolvedValue({ data: { similar: [] } });
    await AdvancedAnalysisAPI.getSimilarPlayers(1);
    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/player/1/similar?top_n=8');
  });

  test('getSimilarPlayers with custom topN', async () => {
    mockAxiosInstance.get.mockResolvedValue({ data: { similar: [] } });
    await AdvancedAnalysisAPI.getSimilarPlayers(1, 5);
    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/player/1/similar?top_n=5');
  });

  test('getTopPerformers with default params', async () => {
    mockAxiosInstance.get.mockResolvedValue({ data: { players: [] } });
    await AdvancedAnalysisAPI.getTopPerformers();
    expect(mockAxiosInstance.get).toHaveBeenCalledWith(
      '/analysis/top-performers?sort_by=overall_score&min_matches=5'
    );
  });

  test('getTopPerformers with position', async () => {
    mockAxiosInstance.get.mockResolvedValue({ data: { players: [] } });
    await AdvancedAnalysisAPI.getTopPerformers('momentum', 'Forward', 10);
    expect(mockAxiosInstance.get).toHaveBeenCalledWith(
      '/analysis/top-performers?sort_by=momentum&min_matches=10&position=Forward'
    );
  });

  test('getTopPerformers throws on error', async () => {
    mockAxiosInstance.get.mockRejectedValue(new Error('fail'));
    await expect(AdvancedAnalysisAPI.getTopPerformers()).rejects.toThrow(
      'Failed to fetch top performers'
    );
  });
});

describe('HealthAPI', () => {
  test('checkHealth returns data on success', async () => {
    mockAxiosInstance.get.mockResolvedValue({ data: { status: 'ok' } });
    const result = await HealthAPI.checkHealth();
    expect(result).toEqual({ status: 'ok' });
    expect(mockAxiosInstance.get).toHaveBeenCalledWith('/');
  });

  test('checkHealth returns null on error', async () => {
    mockAxiosInstance.get.mockRejectedValue(new Error('down'));
    const result = await HealthAPI.checkHealth();
    expect(result).toBeNull();
  });
});
