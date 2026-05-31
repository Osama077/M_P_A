import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import App from '../App';

jest.mock('../api', () => ({
  HealthAPI: { checkHealth: jest.fn().mockResolvedValue({ status: 'ok' }) },
}));

jest.mock('../components/HomePage', () => function MockHomePage() {
  return <div data-testid="page-overview" />;
});

jest.mock('../components/PlayerList', () => function MockPlayerList({ onSelectPlayer }) {
  return (
    <div data-testid="page-players">
      <button
        data-testid="select-player-btn"
        onClick={() => onSelectPlayer('Test Player', 42)}
      >
        Select Player
      </button>
    </div>
  );
});

jest.mock('../components/PlayerProfile', () => function MockPlayerProfile({ playerName }) {
  return <div data-testid="page-dashboard">{playerName}</div>;
});

jest.mock('../components/PlayerAnimatedAnalysis', () => function MockAnimated({ playerName }) {
  return <div data-testid="page-animated">{playerName}</div>;
});

jest.mock('../components/PlayerComparison', () => function MockComparison() {
  return <div data-testid="page-comparison" />;
});

jest.mock('../components/APITester', () => function MockAPITester() {
  return <div data-testid="page-api-tester" />;
});

jest.mock('../components/PlayerForecast', () => function MockForecast({ playerName }) {
  return <div data-testid="page-forecast">{playerName}</div>;
});

jest.mock('../components/PlayerSimilarity', () => function MockSimilarity({ playerName }) {
  return <div data-testid="page-similarity">{playerName}</div>;
});

jest.mock('../components/PlayerMomentum', () => function MockMomentum({ playerName }) {
  return <div data-testid="page-momentum">{playerName}</div>;
});

jest.mock('../components/PlayerAnomalies', () => function MockAnomalies({ playerName }) {
  return <div data-testid="page-anomalies">{playerName}</div>;
});

jest.mock('../components/PlayerConsistency', () => function MockConsistency({ playerName }) {
  return <div data-testid="page-consistency">{playerName}</div>;
});

jest.mock('../components/TopPerformers', () => function MockTopPerformers() {
  return <div data-testid="page-top-performers" />;
});

describe('App', () => {
  test('renders without crashing', () => {
    render(<App />);
    expect(screen.getByText('Match Performance Workbench')).toBeInTheDocument();
  });

  test('shows Overview page by default', () => {
    render(<App />);
    expect(screen.getByTestId('page-overview')).toBeInTheDocument();
  });

  test('renders footer elements', () => {
    render(<App />);
    expect(screen.getByText('Match Performance Analysis Platform')).toBeInTheDocument();
    expect(screen.getByText(/Production-ready UI/)).toBeInTheDocument();
  });

  test('navigates to Players page', () => {
    render(<App />);
    fireEvent.click(screen.getByText('Players'));
    expect(screen.getByTestId('page-players')).toBeInTheDocument();
  });

  test('navigates to Comparison page', () => {
    render(<App />);
    fireEvent.click(screen.getByText('Comparison'));
    expect(screen.getByTestId('page-comparison')).toBeInTheDocument();
  });

  test('navigates to Top Players page', () => {
    render(<App />);
    fireEvent.click(screen.getByText('Top Players'));
    expect(screen.getByTestId('page-top-performers')).toBeInTheDocument();
  });

  test('navigates to API Tests page', () => {
    render(<App />);
    fireEvent.click(screen.getByText('API Tests'));
    expect(screen.getByTestId('page-api-tester')).toBeInTheDocument();
  });

  test('shows fallback when navigating to Dashboard without selected player', () => {
    render(<App />);
    fireEvent.click(screen.getByText('Dashboard'));
    expect(screen.getByText('Select a player first from the Players section.')).toBeInTheDocument();
  });

  test('shows fallback when navigating to Animated without selected player', () => {
    render(<App />);
    fireEvent.click(screen.getByText('Animated'));
    expect(screen.getByText('Select a player first from the Players section.')).toBeInTheDocument();
  });

  test('navigating back to Overview after switching pages', () => {
    render(<App />);
    fireEvent.click(screen.getByText('Players'));
    expect(screen.getByTestId('page-players')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Overview'));
    expect(screen.getByTestId('page-overview')).toBeInTheDocument();
  });

  test('selecting a player from PlayerList opens dashboard', () => {
    render(<App />);
    fireEvent.click(screen.getByText('Players'));
    fireEvent.click(screen.getByTestId('select-player-btn'));
    expect(screen.getByTestId('page-dashboard')).toBeInTheDocument();
    expect(screen.getByTestId('page-dashboard')).toHaveTextContent('Test Player');
  });

  test('navigates to Forecast page with player context', () => {
    render(<App />);
    fireEvent.click(screen.getByText('Players'));
    fireEvent.click(screen.getByTestId('select-player-btn'));
    fireEvent.click(screen.getByText('Forecast'));
    expect(screen.getByTestId('page-forecast')).toHaveTextContent('Test Player');
  });

  test('navigates to Similarity page', () => {
    render(<App />);
    fireEvent.click(screen.getByText('Players'));
    fireEvent.click(screen.getByTestId('select-player-btn'));
    fireEvent.click(screen.getByText('Similarity'));
    expect(screen.getByTestId('page-similarity')).toHaveTextContent('Test Player');
  });

  test('navigates to Momentum page', () => {
    render(<App />);
    fireEvent.click(screen.getByText('Players'));
    fireEvent.click(screen.getByTestId('select-player-btn'));
    fireEvent.click(screen.getByText('Momentum'));
    expect(screen.getByTestId('page-momentum')).toHaveTextContent('Test Player');
  });

  test('navigates to Anomalies page', () => {
    render(<App />);
    fireEvent.click(screen.getByText('Players'));
    fireEvent.click(screen.getByTestId('select-player-btn'));
    fireEvent.click(screen.getByText('Anomalies'));
    expect(screen.getByTestId('page-anomalies')).toHaveTextContent('Test Player');
  });

  test('navigates to Consistency page', () => {
    render(<App />);
    fireEvent.click(screen.getByText('Players'));
    fireEvent.click(screen.getByTestId('select-player-btn'));
    fireEvent.click(screen.getByText('Consistency'));
    expect(screen.getByTestId('page-consistency')).toHaveTextContent('Test Player');
  });

  test('navigates to Animated page with player shows chart', () => {
    render(<App />);
    fireEvent.click(screen.getByText('Players'));
    fireEvent.click(screen.getByTestId('select-player-btn'));
    fireEvent.click(screen.getByText('Animated'));
    expect(screen.getByTestId('page-animated')).toHaveTextContent('Test Player');
  });
});
