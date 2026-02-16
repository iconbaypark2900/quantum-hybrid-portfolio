import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { FaBriefcase } from 'react-icons/fa';
import { MetricCard, SectionTitle, TabButton, Slider, RegimeSelector } from './components';
import ErrorBoundary from './components/ErrorBoundary';

// ─── MetricCard Tests ───

describe('MetricCard', () => {
  test('renders label and value', () => {
    render(<MetricCard label="Sharpe Ratio" value="1.483" />);
    expect(screen.getByText('Sharpe Ratio')).toBeInTheDocument();
    expect(screen.getByText('1.483')).toBeInTheDocument();
  });

  test('renders unit when provided', () => {
    render(<MetricCard label="Return" value="12.5" unit="%" />);
    expect(screen.getByText('%')).toBeInTheDocument();
  });

  test('renders description when provided', () => {
    render(<MetricCard label="VaR" value="0.20" description="Max daily loss" />);
    expect(screen.getByText('Max daily loss')).toBeInTheDocument();
  });

  test('renders positive delta with up arrow', () => {
    render(<MetricCard label="Sharpe" value="1.5" delta={5.2} />);
    expect(screen.getByText(/5\.2% vs benchmark/)).toBeInTheDocument();
  });

  test('renders negative delta with down arrow', () => {
    render(<MetricCard label="Sharpe" value="0.8" delta={-3.1} />);
    expect(screen.getByText(/3\.1% vs benchmark/)).toBeInTheDocument();
  });
});

// ─── SectionTitle Tests ───

describe('SectionTitle', () => {
  test('renders title text', () => {
    render(<SectionTitle>Portfolio Holdings</SectionTitle>);
    expect(screen.getByText('Portfolio Holdings')).toBeInTheDocument();
  });

  test('renders subtitle when provided', () => {
    render(<SectionTitle subtitle="20 positions">Holdings</SectionTitle>);
    expect(screen.getByText('20 positions')).toBeInTheDocument();
  });
});

// ─── TabButton Tests ───

describe('TabButton', () => {
  test('renders label text', () => {
    render(<TabButton active={false} onClick={() => {}}>Holdings</TabButton>);
    expect(screen.getByText('Holdings')).toBeInTheDocument();
  });

  test('calls onClick when clicked', () => {
    const handleClick = jest.fn();
    render(<TabButton active={false} onClick={handleClick}>Holdings</TabButton>);
    fireEvent.click(screen.getByText('Holdings'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  test('renders icon when provided', () => {
    const { container } = render(<TabButton active={true} onClick={() => {}} icon={<FaBriefcase />}>Holdings</TabButton>);
    expect(screen.getByText('Holdings')).toBeInTheDocument();
    expect(container.querySelector('svg')).toBeInTheDocument();
  });
});

// ─── Slider Tests ───

describe('Slider', () => {
  test('renders label and current value', () => {
    render(<Slider label="Omega" value={0.30} onChange={() => {}} min={0.05} max={0.60} step={0.01} />);
    expect(screen.getByText('Omega')).toBeInTheDocument();
    expect(screen.getByText('0.30')).toBeInTheDocument();
  });

  test('renders info text when provided', () => {
    render(<Slider label="Omega" value={0.30} onChange={() => {}} min={0.05} max={0.60} step={0.01} info="Mixing parameter" />);
    expect(screen.getByText('Mixing parameter')).toBeInTheDocument();
  });

  test('calls onChange when slider moved', () => {
    const handleChange = jest.fn();
    render(<Slider label="Omega" value={0.30} onChange={handleChange} min={0.05} max={0.60} step={0.01} />);
    const slider = screen.getByRole('slider');
    fireEvent.change(slider, { target: { value: '0.40' } });
    expect(handleChange).toHaveBeenCalledWith(0.40);
  });
});

// ─── RegimeSelector Tests ───

describe('RegimeSelector', () => {
  test('renders all four regime options', () => {
    render(<RegimeSelector value="normal" onChange={() => {}} />);
    expect(screen.getByText('Normal')).toBeInTheDocument();
    expect(screen.getByText('Bull')).toBeInTheDocument();
    expect(screen.getByText('Bear')).toBeInTheDocument();
    expect(screen.getByText('Volatile')).toBeInTheDocument();
  });

  test('calls onChange when a regime is clicked', () => {
    const handleChange = jest.fn();
    render(<RegimeSelector value="normal" onChange={handleChange} />);
    fireEvent.click(screen.getByText('Bull'));
    expect(handleChange).toHaveBeenCalledWith('bull');
  });
});

// ─── ErrorBoundary Tests ───

describe('ErrorBoundary', () => {
  // Suppress React error boundary console errors in test output
  const originalError = console.error;
  beforeAll(() => { console.error = jest.fn(); });
  afterAll(() => { console.error = originalError; });

  function ProblemChild() {
    throw new Error('Test crash');
  }

  test('renders children when no error', () => {
    render(
      <ErrorBoundary>
        <div>Dashboard Content</div>
      </ErrorBoundary>
    );
    expect(screen.getByText('Dashboard Content')).toBeInTheDocument();
  });

  test('renders fallback UI when child throws', () => {
    render(
      <ErrorBoundary>
        <ProblemChild />
      </ErrorBoundary>
    );
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByText(/Test crash/)).toBeInTheDocument();
    expect(screen.getByText('Try Again')).toBeInTheDocument();
    expect(screen.getByText('Reload Page')).toBeInTheDocument();
  });

  test('recovers when Try Again is clicked', () => {
    let shouldThrow = true;
    function MaybeThrows() {
      if (shouldThrow) throw new Error('Recoverable crash');
      return <div>Recovered</div>;
    }

    render(
      <ErrorBoundary>
        <MaybeThrows />
      </ErrorBoundary>
    );
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();

    shouldThrow = false;
    fireEvent.click(screen.getByText('Try Again'));
    expect(screen.getByText('Recovered')).toBeInTheDocument();
  });
});
