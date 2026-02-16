import React from 'react';
import { FaExclamationTriangle } from 'react-icons/fa';

/**
 * React Error Boundary - catches unhandled errors in the component tree
 * and renders a fallback UI instead of crashing the whole app.
 */
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#0a0e1a',
          color: '#e2e8f0',
          fontFamily: "'Space Grotesk', -apple-system, sans-serif",
          padding: 40,
        }}>
          <div style={{
            maxWidth: 560,
            textAlign: 'center',
            background: '#111827',
            border: '1px solid #1e293b',
            borderRadius: 12,
            padding: 40,
          }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}><FaExclamationTriangle /></div>
            <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 }}>
              Something went wrong
            </h1>
            <p style={{ color: '#94a3b8', fontSize: 14, lineHeight: 1.6, marginBottom: 24 }}>
              The dashboard encountered an unexpected error. You can try reloading or resetting the view.
            </p>
            {this.state.error && (
              <pre style={{
                background: '#1e1e2e',
                border: '1px solid #334155',
                borderRadius: 8,
                padding: 16,
                fontSize: 12,
                color: '#f87171',
                textAlign: 'left',
                overflow: 'auto',
                maxHeight: 160,
                marginBottom: 24,
                fontFamily: "'JetBrains Mono', monospace",
              }}>
                {this.state.error.toString()}
              </pre>
            )}
            <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
              <button
                onClick={this.handleReset}
                style={{
                  padding: '10px 24px',
                  background: '#6366f1',
                  color: 'white',
                  border: 'none',
                  borderRadius: 8,
                  fontSize: 14,
                  cursor: 'pointer',
                  fontWeight: 600,
                }}
              >
                Try Again
              </button>
              <button
                onClick={() => window.location.reload()}
                style={{
                  padding: '10px 24px',
                  background: 'transparent',
                  color: '#94a3b8',
                  border: '1px solid #334155',
                  borderRadius: 8,
                  fontSize: 14,
                  cursor: 'pointer',
                }}
              >
                Reload Page
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
