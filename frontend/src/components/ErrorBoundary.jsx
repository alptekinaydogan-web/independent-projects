import React from "react";

/**
 * Isolates a subtree so a runtime error inside a page or widget never takes
 * down the entire shell. The user still sees the sidebar + can navigate; only
 * the failing region shows a graceful "Something went wrong" panel with a
 * recovery button.
 *
 * Usage:
 *   <ErrorBoundary label="Reports">
 *     <ReportsPage />
 *   </ErrorBoundary>
 */
export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    // Surfaced in dev overlay + browser console. We keep it minimal here since
    // getDerivedStateFromError already captures the error object.
    // eslint-disable-next-line no-console
    console.warn(`[ErrorBoundary${this.props.label ? ` · ${this.props.label}` : ""}]`, error, info?.componentStack);
  }

  reset = () => this.setState({ error: null });

  render() {
    if (this.state.error) {
      return (
        <div className="p-10" data-testid="error-boundary">
          <div className="imh-card p-8 max-w-2xl">
            <div className="imh-eyebrow" style={{ color: "#991B1B" }}>Section unavailable</div>
            <h2 className="font-editorial text-2xl mt-2">
              {this.props.label ? `${this.props.label} temporarily unavailable` : "Something went wrong"}
            </h2>
            <p className="text-sm text-[#52525B] mt-3 max-w-lg">
              This section could not render. Other parts of Independent Projects remain fully operational.
              You can retry the section below or use the navigation on the left to continue working.
            </p>
            <pre className="mt-4 p-3 bg-[#F9F9F6] border border-[#E4E4E1] text-[11px] text-[#52525B] font-mono-imh overflow-auto max-h-32">
              {String(this.state.error?.message || this.state.error)}
            </pre>
            <button onClick={this.reset} data-testid="error-boundary-retry"
                    className="mt-4 h-9 px-4 border border-[#0033A0] text-[#0033A0] text-[11px] uppercase tracking-widest hover:bg-[#0033A0] hover:text-white"
                    style={{ transition: "background 120ms, color 120ms" }}>
              Try again
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
