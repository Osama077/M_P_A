import React from 'react';
import { render, screen } from '@testing-library/react';
import LoadingSpinner from '../components/LoadingSpinner';

describe('LoadingSpinner', () => {
  test('renders default message', () => {
    render(<LoadingSpinner />);
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  test('renders custom message', () => {
    render(<LoadingSpinner message="Fetching player data..." />);
    expect(screen.getByText('Fetching player data...')).toBeInTheDocument();
  });

  test('has aria-live polite', () => {
    render(<LoadingSpinner />);
    expect(screen.getByRole('status')).toHaveAttribute('aria-live', 'polite');
  });
});
