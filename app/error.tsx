"use client";

import { useEffect } from "react";
import Link from "next/link";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("App Error Boundary Caught:", error);
  }, [error]);

  return (
    <div className="min-h-screen bg-canvas text-ink flex items-center justify-center p-6">
      <div className="max-w-md w-full glass rounded-2xl p-8 text-center shadow-lg border border-danger/20">
        <div className="w-16 h-16 bg-danger/10 text-danger rounded-full flex items-center justify-center mx-auto mb-6">
          <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <h1 className="text-2xl font-bold font-display mb-3">Something went wrong</h1>
        <p className="text-muted text-sm leading-relaxed mb-8">
          We encountered an unexpected error while processing your request. Please try again or return to the dashboard.
        </p>
        <div className="flex flex-col gap-3">
          <button
            onClick={reset}
            className="w-full bg-accent text-canvas py-3 rounded-xl font-medium hover:scale-[1.02] transition"
          >
            Try Again
          </button>
          <Link
            href="/"
            className="w-full inline-block bg-surface-2 text-ink py-3 rounded-xl font-medium hover:bg-surface border border-border transition"
          >
            Return Home
          </Link>
        </div>
      </div>
    </div>
  );
}
