import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
}

/**
 * Catches render-time errors anywhere in the component tree below it and shows
 * a readable message instead of a blank screen.
 *
 * Error boundaries MUST be class components — React has no hook equivalent for
 * `componentDidCatch` / `getDerivedStateFromError`.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    // Called during render when a child throws → switch to the fallback UI.
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Side-effect place to log the error (console now; a real logger in prod).
    console.error('ErrorBoundary caught an error:', error, info);
  }

  handleReload = (): void => {
    this.setState({ error: null });
    window.location.reload();
  };

  render(): ReactNode {
    if (this.state.error) {
      return (
        <div
          role="alert"
          style={{
            maxWidth: 640,
            margin: '3rem auto',
            padding: '1.5rem',
            border: '1px solid #e0b4b4',
            borderRadius: 12,
            background: '#fff6f6',
          }}
        >
          <h2 style={{ marginTop: 0 }}>Algo salió mal</h2>
          <p>La aplicación encontró un error inesperado y no pudo continuar.</p>
          <pre
            style={{
              whiteSpace: 'pre-wrap',
              background: '#fbeaea',
              padding: '0.75rem',
              borderRadius: 8,
              fontSize: '0.85rem',
            }}
          >
            {this.state.error.message}
          </pre>
          <button type="button" onClick={this.handleReload}>
            Recargar la aplicación
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
