"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/AuthProvider";

export default function LoginPage() {
  const router = useRouter();
  const { user, loginWithGoogle, loginWithEmail, registerWithEmail, loginAsDemo } = useAuth();
  
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // If user is already authenticated (and not in demo guest mode), redirect to dashboard
  useEffect(() => {
    if (user && user.uid !== "demo_user_123") {
      router.push("/dashboard");
    }
  }, [user, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email || !password) {
      setError("Please fill in all fields.");
      return;
    }

    if (isRegister && !name) {
      setError("Please provide your name.");
      return;
    }

    setSubmitting(true);
    try {
      if (isRegister) {
        await registerWithEmail(email, password, name);
      } else {
        await loginWithEmail(email, password);
      }
      router.push("/dashboard");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      if (msg.includes("auth/invalid-credential") || msg.includes("auth/wrong-password")) {
        setError("Invalid email or password. Please try again.");
      } else if (msg.includes("auth/email-already-in-use")) {
        setError("This email is already registered. Please login instead.");
      } else if (msg.includes("auth/weak-password")) {
        setError("Password should be at least 6 characters.");
      } else {
        setError(msg.replace("Firebase:", "").trim());
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleGoogleSignIn = async () => {
    setError(null);
    setSubmitting(true);
    try {
      await loginWithGoogle();
      router.push("/dashboard");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg.replace("Firebase:", "").trim());
    } finally {
      setSubmitting(false);
    }
  };

  const handleDemoSignIn = () => {
    loginAsDemo();
    router.push("/dashboard");
  };

  return (
    <div className="min-h-screen bg-canvas text-ink flex flex-col justify-center items-center px-6 relative overflow-hidden">
      <div className="absolute inset-0 pointer-events-none hero-grid opacity-30" />
      
      {/* Back to Home Link */}
      <div className="absolute top-8 left-8">
        <Link href="/" className="font-bold text-lg hover:opacity-85 transition flex items-center gap-2">
          <span className="text-accent">◈</span> MarketAI
        </Link>
      </div>

      <div className="w-full max-w-md bg-surface border border-border rounded-2xl shadow-xl p-8 z-10 relative">
        <div className="text-center mb-8">
          <h1 className="font-display text-3xl font-bold tracking-tight">
            {isRegister ? "Create Account" : "Welcome Back"}
          </h1>
          <p className="text-sm text-muted mt-2">
            {isRegister 
              ? "Sign up to track and organize your custom market intelligence" 
              : "Sign in to access your personal workspace and reports"}
          </p>
        </div>

        {error && (
          <div className="mb-6 p-3 bg-danger/10 border border-danger/30 text-danger text-xs rounded-lg flex items-center gap-2">
            <span>⚠️</span>
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {isRegister && (
            <div>
              <label className="block text-xs uppercase tracking-wider text-muted mb-1 font-semibold">
                Your Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Shivam Singh"
                className="w-full bg-surface-2 border border-border rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-accent transition"
                required
              />
            </div>
          )}

          <div>
            <label className="block text-xs uppercase tracking-wider text-muted mb-1 font-semibold">
              Email Address
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@company.com"
              className="w-full bg-surface-2 border border-border rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-accent transition"
              required
            />
          </div>

          <div>
            <label className="block text-xs uppercase tracking-wider text-muted mb-1 font-semibold">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full bg-surface-2 border border-border rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-accent transition"
              required
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-accent text-canvas font-semibold py-2.5 rounded-lg hover:opacity-90 transition shadow-md lime-glow mt-2 flex items-center justify-center gap-2"
          >
            {submitting ? (
              <span className="w-4 h-4 border-2 border-canvas border-t-transparent rounded-full animate-spin" />
            ) : isRegister ? (
              "Sign Up & Register"
            ) : (
              "Sign In to Workspace"
            )}
          </button>
        </form>

        <div className="relative my-6 flex items-center justify-center">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-border" />
          </div>
          <span className="relative bg-surface px-3 text-xs uppercase tracking-wider text-muted font-mono z-10">
            or connect with
          </span>
        </div>

        <div className="space-y-3">
          <button
            onClick={handleGoogleSignIn}
            disabled={submitting}
            className="w-full bg-surface-2 hover:bg-surface border border-border text-ink font-medium py-2.5 rounded-lg transition flex items-center justify-center gap-2 text-sm cursor-pointer"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24">
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
              />
            </svg>
            Continue with Google
          </button>

          <button
            onClick={handleDemoSignIn}
            className="w-full bg-transparent hover:bg-surface-2 text-muted hover:text-ink font-medium py-2 rounded-lg transition text-xs border border-transparent hover:border-border mt-1"
          >
            ⚡ Continue as Guest (Bypass Demo Mode)
          </button>
        </div>

        <div className="mt-6 text-center text-xs">
          <button
            onClick={() => {
              setIsRegister(!isRegister);
              setError(null);
            }}
            className="text-accent hover:underline focus:outline-none"
          >
            {isRegister ? "Already have an account? Sign In" : "Don't have an account? Sign Up"}
          </button>
        </div>
      </div>
    </div>
  );
}
