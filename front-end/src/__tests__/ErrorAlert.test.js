import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import ErrorAlert from '../components/ErrorAlert';

describe('ErrorAlert', () => {
  test('renders error message', () => {
    render(<ErrorAlert message="Something went wrong" />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Error')).toBeInTheDocument();
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  test('has dismiss button', () => {
    render(<ErrorAlert message="Test error" />);
    expect(screen.getByLabelText('Dismiss error')).toBeInTheDocument();
  });

  test('dismiss button hides the alert', () => {
    render(<ErrorAlert message="Dismiss me" />);
    fireEvent.click(screen.getByLabelText('Dismiss error'));
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  test('calls onDismiss callback when dismissed', () => {
    const onDismiss = jest.fn();
    render(<ErrorAlert message="Callback test" onDismiss={onDismiss} />);
    fireEvent.click(screen.getByLabelText('Dismiss error'));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  test('sets aria-live assertive', () => {
    render(<ErrorAlert message="Aria test" />);
    expect(screen.getByRole('alert')).toHaveAttribute('aria-live', 'assertive');
  });
});
