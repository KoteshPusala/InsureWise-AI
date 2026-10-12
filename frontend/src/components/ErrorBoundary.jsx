import React from 'react';
import { AlertTriangle, RefreshCw, RotateCcw, Home } from 'lucide-react';

// Technical details are only shown in development so users never see stack traces.
const SHOW_ERROR_DETAILS = Boolean(import.meta.env?.DEV);

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  // Clears the error and re-renders the children without a full page reload.
  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    return (
      <div className="flex min-h-screen items-center justify-center bg-gradient-to-b from-slate-50 to-white p-4 sm:p-6">
        <div
          role="alert"
          className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 text-center shadow-lg sm:p-8"
        >
          <span className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-rose-50 text-rose-600 ring-1 ring-rose-100">
            <AlertTriangle className="h-7 w-7" aria-hidden="true" />
          </span>

          <h2 className="text-xl font-extrabold tracking-tight text-slate-900">
            Something went wrong
          </h2>
          <p className="mt-1.5 text-sm text-slate-500">
            An unexpected error occurred while displaying this page. You can try
            again, or reload the application.
          </p>

          {SHOW_ERROR_DETAILS && (
            <pre className="mt-4 max-h-32 overflow-auto rounded-xl border border-slate-200 bg-slate-50 p-3 text-left font-mono text-[11px] leading-relaxed text-slate-600">
              {this.state.error?.toString() || 'Unknown rendering error'}
            </pre>
          )}

          <div className="mt-6 grid grid-cols-1 gap-2 sm:grid-cols-3">
            <button
              onClick={this.handleRetry}
              className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-semibold text-white shadow-sm transition hover:bg-indigo-700 focus:outline-none focus:ring-4 focus:ring-indigo-200"
            >
              <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
              Try again
            </button>

            <button
              onClick={this.handleReload}
              className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-slate-100"
            >
              <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
              Reload
            </button>

            {/* Plain anchor: this boundary sits outside <BrowserRouter>, so router links are unavailable. */}
            <a
              href="/"
              className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-slate-100"
            >
              <Home className="h-3.5 w-3.5" aria-hidden="true" />
              Home
            </a>
          </div>
        </div>
      </div>
    );
  }
}