import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, showDetails: false };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  handleClearAndReload = () => {
    // Clear service worker caches and reload
    if ('caches' in window) {
      caches.keys().then(names => {
        for (const name of names) caches.delete(name);
      });
    }
    if (navigator.serviceWorker) {
      navigator.serviceWorker.getRegistrations().then(regs => {
        for (const reg of regs) reg.unregister();
      });
    }
    setTimeout(() => window.location.reload(true), 500);
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 p-6">
          <div className="max-w-md text-center">
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Something went wrong</h2>
            <p className="text-gray-500 mb-4 text-sm">An unexpected error occurred. Try clearing cache first.</p>
            <div className="flex gap-2 justify-center mb-4">
              <button
                onClick={this.handleClearAndReload}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm"
                data-testid="error-boundary-reload"
              >
                Clear Cache & Reload
              </button>
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 text-sm"
              >
                Quick Reload
              </button>
            </div>
            <button
              onClick={() => this.setState({ showDetails: !this.state.showDetails })}
              className="text-xs text-gray-400 underline"
            >
              {this.state.showDetails ? 'Hide' : 'Show'} error details
            </button>
            {this.state.showDetails && this.state.error && (
              <pre className="mt-3 text-left text-xs bg-gray-100 p-3 rounded-lg overflow-auto max-h-40 text-red-600">
                {this.state.error.toString()}
                {this.state.error.stack && '\n\n' + this.state.error.stack.substring(0, 500)}
              </pre>
            )}
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
