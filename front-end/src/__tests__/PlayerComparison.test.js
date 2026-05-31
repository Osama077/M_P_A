import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { PlayerAPI } from '../api';
import PlayerComparison from '../components/PlayerComparison';

jest.mock('../api', () => ({
  PlayerAPI: {
    getPlayerList: jest.fn(),
    comparePlayer: jest.fn(),
  },
}));

const mockPlayers = [
  { player_id: 1, player_name: 'Alice', team_name: 'Team A' },
  { player_id: 2, player_name: 'Bob', team_name: 'Team B' },
  { player_id: 3, player_name: 'Charlie', team_name: 'Team A' },
];

const mockComparison = [
  { player_id: 1, player_name: 'Alice', overall_score: 8.5, scores: { passing: 7.5, shooting: 9.0, positioning: 8.0, pressing: 6.5, movement: 7.0, physical: 8.0, behavioral: 7.5 } },
  { player_id: 2, player_name: 'Bob', overall_score: 7.2, scores: { passing: 6.0, shooting: 8.5, positioning: 7.0, pressing: 7.5, movement: 6.5, physical: 7.0, behavioral: 8.0 } },
];

beforeEach(() => {
  jest.clearAllMocks();
});

describe('PlayerComparison', () => {
  test('shows loading state while fetching players', () => {
    PlayerAPI.getPlayerList.mockReturnValue(new Promise(() => {}));
    render(<PlayerComparison />);
    expect(screen.getByText('Loading players...')).toBeInTheDocument();
  });

  test('renders player list after load', async () => {
    PlayerAPI.getPlayerList.mockResolvedValue({ player_items: mockPlayers });
    render(<PlayerComparison />);
    await waitFor(() => {
      expect(screen.getByText('Alice')).toBeInTheDocument();
    });
    expect(screen.getByText('Bob')).toBeInTheDocument();
    expect(screen.getByText('Charlie')).toBeInTheDocument();
    expect(screen.getAllByText('Team A')).toHaveLength(2);
    expect(screen.getByText('Team B')).toBeInTheDocument();
  });

  test('selects and deselects a player', async () => {
    PlayerAPI.getPlayerList.mockResolvedValue({ player_items: mockPlayers });
    render(<PlayerComparison />);
    await waitFor(() => expect(screen.getByText('Alice')).toBeInTheDocument());

    const aliceBtn = screen.getByText('Alice').closest('button');
    fireEvent.click(aliceBtn);
    expect(screen.getByText('Compare (1)')).toBeInTheDocument();

    fireEvent.click(aliceBtn);
    expect(screen.getByText('Compare (0)')).toBeInTheDocument();
  });

  test('compare button enabled only with 2+ players', async () => {
    PlayerAPI.getPlayerList.mockResolvedValue({ player_items: mockPlayers });
    render(<PlayerComparison />);
    await waitFor(() => expect(screen.getByText('Alice')).toBeInTheDocument());

    const compareBtn = screen.getByText(/Compare/);
    expect(compareBtn).toBeDisabled();

    const alice = screen.getByText('Alice').closest('button');
    const bob = screen.getByText('Bob').closest('button');
    fireEvent.click(alice);
    fireEvent.click(bob);
    expect(compareBtn).not.toBeDisabled();
  });

  test('runs comparison and displays results', async () => {
    PlayerAPI.getPlayerList.mockResolvedValue({ player_items: mockPlayers });
    PlayerAPI.comparePlayer.mockResolvedValue({ comparison: mockComparison });

    render(<PlayerComparison />);
    await waitFor(() => expect(screen.getByText('Alice')).toBeInTheDocument());

    const alice = screen.getByText('Alice').closest('button');
    const bob = screen.getByText('Bob').closest('button');
    fireEvent.click(alice);
    fireEvent.click(bob);
    fireEvent.click(screen.getByText(/Compare/));

    await waitFor(() => {
      expect(screen.getByText('Comparison Results')).toBeInTheDocument();
    });

    expect(screen.getByText('passing')).toBeInTheDocument();
    expect(screen.getByText('shooting')).toBeInTheDocument();
    expect(screen.getByText('overall score')).toBeInTheDocument();
    expect(screen.getByText('positioning')).toBeInTheDocument();
  });

  test('shows empty state when comparison has no items', async () => {
    PlayerAPI.getPlayerList.mockResolvedValue({ player_items: mockPlayers });
    PlayerAPI.comparePlayer.mockResolvedValue({ comparison: [] });

    render(<PlayerComparison />);
    await waitFor(() => expect(screen.getByText('Alice')).toBeInTheDocument());

    const alice = screen.getByText('Alice').closest('button');
    const bob = screen.getByText('Bob').closest('button');
    fireEvent.click(alice);
    fireEvent.click(bob);
    fireEvent.click(screen.getByText(/Compare/));

    await waitFor(() => {
      expect(screen.getByText('No comparison data available for the selected players.')).toBeInTheDocument();
    });
  });

  test('shows error state when fetch fails', async () => {
    PlayerAPI.getPlayerList.mockRejectedValue(new Error('Failed to load'));
    render(<PlayerComparison />);
    await waitFor(() => {
      expect(screen.getByText('Failed to load')).toBeInTheDocument();
    });
  });

  test('shows error when comparison fails', async () => {
    PlayerAPI.getPlayerList.mockResolvedValue({ player_items: mockPlayers });
    PlayerAPI.comparePlayer.mockRejectedValue(new Error('Compare failed'));

    render(<PlayerComparison />);
    await waitFor(() => expect(screen.getByText('Alice')).toBeInTheDocument());

    const alice = screen.getByText('Alice').closest('button');
    const bob = screen.getByText('Bob').closest('button');
    fireEvent.click(alice);
    fireEvent.click(bob);
    fireEvent.click(screen.getByText(/Compare/));

    await waitFor(() => {
      expect(screen.getByText('Compare failed')).toBeInTheDocument();
    });
  });
});
