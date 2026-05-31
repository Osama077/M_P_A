import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AppProvider, PAGES, USER_ROLES } from '../context/AppContext';
import { HealthAPI } from '../api';
import Navigation from '../components/Navigation';

jest.mock('../api', () => ({
  HealthAPI: { checkHealth: jest.fn() },
}));

function renderNav() {
  return render(
    <AppProvider>
      <Navigation />
    </AppProvider>
  );
}

const navLabels = [
  'Overview', 'Players', 'Dashboard', 'Animated', 'Comparison',
  'Forecast', 'Similarity', 'Momentum', 'Anomalies', 'Consistency',
  'Top Players', 'API Tests',
];

describe('Navigation', () => {
  beforeEach(() => {
    HealthAPI.checkHealth.mockReset();
  });

  test('renders all navigation items', () => {
    HealthAPI.checkHealth.mockResolvedValue({ status: 'ok' });
    renderNav();
    navLabels.forEach((label) => {
      expect(screen.getByText(label)).toBeInTheDocument();
    });
  });

  test('renders home button as first item', () => {
    HealthAPI.checkHealth.mockResolvedValue({ status: 'ok' });
    renderNav();
    const buttons = screen.getAllByRole('tab');
    expect(buttons[0]).toHaveTextContent('Overview');
  });

  test('Overview is active by default', () => {
    HealthAPI.checkHealth.mockResolvedValue({ status: 'ok' });
    renderNav();
    const overviewBtn = screen.getByText('Overview');
    expect(overviewBtn.closest('[role="tab"]')).toHaveAttribute('aria-selected', 'true');
  });

  test('clicking a nav item navigates', async () => {
    HealthAPI.checkHealth.mockResolvedValue({ status: 'ok' });
    renderNav();
    const playersBtn = screen.getByText('Players');
    fireEvent.click(playersBtn);
    expect(playersBtn.closest('[role="tab"]')).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByText('Overview').closest('[role="tab"]')).toHaveAttribute('aria-selected', 'false');
  });

  test('renders role selector', () => {
    HealthAPI.checkHealth.mockResolvedValue({ status: 'ok' });
    renderNav();
    expect(screen.getByLabelText('Select user role')).toBeInTheDocument();
    expect(screen.getByText('Analyst')).toBeInTheDocument();
    expect(screen.getByText('Coach')).toBeInTheDocument();
    expect(screen.getByText('Admin')).toBeInTheDocument();
  });

  test('shows API Tests for analyst role', () => {
    HealthAPI.checkHealth.mockResolvedValue({ status: 'ok' });
    renderNav();
    expect(screen.getByText('API Tests')).toBeInTheDocument();
  });

  test('hides API Tests when role is Coach', () => {
    HealthAPI.checkHealth.mockResolvedValue({ status: 'ok' });
    renderNav();
    const select = screen.getByLabelText('Select user role');
    fireEvent.change(select, { target: { value: USER_ROLES.COACH } });
    expect(screen.queryByText('API Tests')).not.toBeInTheDocument();
  });

  test('shows API Tests when role is Admin', () => {
    HealthAPI.checkHealth.mockResolvedValue({ status: 'ok' });
    renderNav();
    const select = screen.getByLabelText('Select user role');
    fireEvent.change(select, { target: { value: USER_ROLES.ADMIN } });
    expect(screen.getByText('API Tests')).toBeInTheDocument();
  });

  test('shows API Tests when role is Analyst', () => {
    HealthAPI.checkHealth.mockResolvedValue({ status: 'ok' });
    renderNav();
    const select = screen.getByLabelText('Select user role');
    fireEvent.change(select, { target: { value: USER_ROLES.ANALYST } });
    expect(screen.getByText('API Tests')).toBeInTheDocument();
  });

  test('shows checking status initially', () => {
    HealthAPI.checkHealth.mockReturnValue(new Promise(() => {}));
    renderNav();
    expect(screen.getByText('Checking API')).toBeInTheDocument();
  });

  test('shows online status when health check succeeds', async () => {
    HealthAPI.checkHealth.mockResolvedValue({ status: 'ok' });
    renderNav();
    await waitFor(() => {
      expect(screen.getByText('API online')).toBeInTheDocument();
    });
  });

  test('shows offline status when health check fails', async () => {
    HealthAPI.checkHealth.mockRejectedValue(new Error('fail'));
    renderNav();
    await waitFor(() => {
      expect(screen.getByText('API offline')).toBeInTheDocument();
    });
  });

  test('renders the title', () => {
    HealthAPI.checkHealth.mockResolvedValue({ status: 'ok' });
    renderNav();
    expect(screen.getByText('Match Performance Workbench')).toBeInTheDocument();
  });

  test('renders the subtitle', () => {
    HealthAPI.checkHealth.mockResolvedValue({ status: 'ok' });
    renderNav();
    expect(screen.getByText('AI-ready analytics interface for football operations')).toBeInTheDocument();
  });
});
