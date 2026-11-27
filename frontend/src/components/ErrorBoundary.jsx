import React from 'react';
import { ShieldAlert, RefreshCw } from 'lucide-react';

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Unhandled UI Render Error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-white text-black flex items-center justify-center p-6">
          <div className="max-w-md w-full border border-neutral-300 p-8 space-y-4 bg-neutral-50 shadow-sm">
            <div className="flex items-center gap-3 text-red-600">
              <ShieldAlert className="w-8 h-8 shrink-0" />
              <div>
                <h2 className="text-sm font-mono uppercase font-bold tracking-wider text-black">
                  Interface Error Encountered
                </h2>
                <span className="text-xs font-mono text-neutral-500">Rendering Exception</span>
              </div>
            </div>
            <p className="text-xs font-mono text-neutral-700 bg-white border border-neutral-200 p-3 break-words whitespace-pre-wrap">
              {this.state.error?.message || 'An unknown render error occurred.'}
            </p>
            <button
              onClick={() => {
                this.setState({ hasError: false, error: null });
                window.location.reload();
              }}
              className="w-full flex items-center justify-center gap-2 py-2.5 bg-black text-white text-xs font-mono uppercase font-semibold hover:bg-neutral-800 transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Reload Interface</span>
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
