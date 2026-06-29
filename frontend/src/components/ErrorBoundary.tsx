"use client";

import { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[TPT ErrorBoundary]", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        this.props.fallback ?? (
          <div className="flex flex-col items-center justify-center h-full min-h-[200px] p-8 text-center">
            <div className="text-4xl mb-4 text-accent-red">⚠</div>
            <h2 className="text-sm font-bold text-accent-red mb-2">COMPONENT ERROR</h2>
            <p className="text-xs text-text-secondary mb-4 font-mono max-w-md">
              {this.state.error.message}
            </p>
            <button
              onClick={() => this.setState({ error: null })}
              className="px-4 py-1.5 rounded bg-bg-tertiary text-text-secondary hover:text-text-primary text-xs border border-border"
            >
              Reload component
            </button>
          </div>
        )
      );
    }
    return this.props.children;
  }
}
