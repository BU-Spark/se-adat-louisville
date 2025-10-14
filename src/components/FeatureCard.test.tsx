import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { FeatureCard } from './FeatureCard';

const baseProps = {
  id: 'test-card',
  icon: '🚀',
  title: 'Test Feature',
  description: 'Short description',
  details: 'Detailed information\nwith multiple lines.',
};

describe('FeatureCard', () => {
  it('renders core content', () => {
    render(<FeatureCard {...baseProps} />);

    expect(screen.getByRole('button', { name: /test feature/i })).toBeInTheDocument();
    expect(screen.getByText(baseProps.icon)).toBeInTheDocument();
    expect(screen.getByText(baseProps.description)).toBeInTheDocument();
    const detailsRegion = screen.getByTestId('feature-details');
    expect(detailsRegion).toHaveTextContent(/Detailed information/);
    expect(detailsRegion).toHaveAttribute('aria-hidden', 'true');
  });

  it('toggles expanded state on click', () => {
    render(<FeatureCard {...baseProps} />);

    const trigger = screen.getByRole('button', { name: /test feature/i });
    const detailsRegion = screen.getByTestId('feature-details');

    fireEvent.click(trigger);
    expect(trigger).toHaveAttribute('aria-expanded', 'true');
    expect(detailsRegion).toHaveAttribute('aria-hidden', 'false');

    fireEvent.click(trigger);
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
    expect(detailsRegion).toHaveAttribute('aria-hidden', 'true');
  });

  it('toggles expanded state with keyboard interaction', () => {
    render(<FeatureCard {...baseProps} />);

    const trigger = screen.getByRole('button', { name: /test feature/i });
    const detailsRegion = screen.getByTestId('feature-details');

    fireEvent.keyDown(trigger, { key: 'Enter' });
    expect(trigger).toHaveAttribute('aria-expanded', 'true');
    expect(detailsRegion).toHaveAttribute('aria-hidden', 'false');

    fireEvent.keyDown(trigger, { key: ' ' });
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
    expect(detailsRegion).toHaveAttribute('aria-hidden', 'true');
  });
});
