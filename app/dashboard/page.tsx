"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import {
  startResearch,
  researchPdfUrl,
} from "@/app/lib/api";
import type { ResearchResult } from "@/app/lib/types";
import { useAuth } from "@/app/lib/AuthProvider";

interface JobState {
  product: string;
  mode: "quick" | "deep" | "batch";
  taskId: string | null;
  phase: "idle" | "running" | "done" | "error";
  error?: string;
  result?: ResearchResult | null;
  progress?: number;
}

const STEPS = [
  { key: "scrape", label: "Competitor Scrape", icon: "🕵️" },
  { key: "financial", label: "Financial Margin", icon: "🧮" },
  { key: "review", label: "Review Gate", icon: "⏸️" },
  { key: "brief", label: "Launch Brief", icon: "📄" },
  { key: "confidence", label: "Confidence", icon: "🎯" },
];

export default function DashboardPage() {
  const { user, orgId, loading: authLoading, login, logout } = useAuth();
  const [product, setProduct] = useState("");
  const [mode, setMode] = useState<"quick" | "deep">("deep");
  const [job, setJob] = useState<JobState>({
    product: "",
    mode: "deep",
    taskId: null,
    phase: "idle",
    progress: 0,
  });
  const [currentStep, setCurrentStep] = useState(0);
  const eventSourceRef = useRef<EventSource | null>(null);

  const start = async () => {
    if (!product.trim() || !orgId) return;
    setJob({ product, mode, taskId: null, phase: "running", progress: 0 });
    setCurrentStep(0);
    try {
      const idempotencyKey = `req-${Date.now()}`;
      const { task_id } = await startResearch(orgId, product.trim(), mode, idempotencyKey);
      setJob((j) => ({ ...j, taskId: task_id }));
    } catch (err) {
      setJob((j) => ({ ...j, phase: "error", error: String(err) }));
    }
  };

  // SSE Real-time Updates
  useEffect(() => {
    if (job.phase !== "running" || !job.taskId || !orgId) return;

    const path =
      process.env.NEXT_PUBLIC_API_BASE && process.env.NEXT_PUBLIC_API_BASE.length > 0
        ? `${process.env.NEXT_PUBLIC_API_BASE}/api/v1/research/${encodeURIComponent(job.taskId)}/events?orgId=${orgId}`
        : `/api/v1/research/${encodeURIComponent(job.taskId)}/events?orgId=${orgId}`;

    const es = new EventSource(path);
    eventSourceRef.current = es;

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setJob((j) => {
          const next: JobState = { ...j, result: data.result, progress: data.progress };
          if (data.status === "COMPLETED" && data.result) {
            next.phase = "done";
            es.close();
          } else if (data.status === "FAILED") {
            next.phase = "error";
            next.error = data.error ?? "Research failed.";
            es.close();
          }
          return next;
        });
        
        // Approximate step based on progress
        if (data.progress) {
          const step = Math.min(Math.floor((data.progress / 100) * STEPS.length), STEPS.length - 1);
          setCurrentStep(step);
        }
      } catch (err) {
        console.error("Failed to parse SSE", err);
      }
    };

    es.onerror = () => {
      es.close();
      setJob((j) => ({ ...j, phase: "error", error: "Connection to real-time events lost." }));
    };

    return () => {
      es.close();
    };
  }, [job.phase, job.taskId, orgId]);

  if (authLoading) {
    return <div className="min-h-screen flex items-center justify-center text-ink">Loading...</div>;
  }

  if (!user) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center text-ink gap-4">
        <h1 className="text-3xl font-bold font-display">Welcome to MarketAI</h1>
        <p className="text-muted">Sign in to start researching.</p>
        <button onClick={login} className="bg-accent text-canvas px-6 py-2 rounded-lg font-medium hover:scale-105 transition">
          Sign In with Google
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen text-ink">
      <HeaderBar running={job.phase === "running"} user={user} onLogout={logout} />

      <main className="container mx-auto px-6 pt-14">
        <QueryHero
          product={product}
          setProduct={setProduct}
          mode={mode}
          setMode={setMode}
          onStart={start}
          phase={job.phase}
          error={job.error}
        />

        {job.phase === "error" ? (
          <div className="glass border border-danger/30 rounded-xl p-6 mb-12 flex items-start gap-4">
            <div className="w-10 h-10 rounded-full bg-danger/10 flex items-center justify-center text-danger shrink-0 mt-1">
              <span className="text-xl">⚠️</span>
            </div>
            <div>
              <h3 className="text-lg font-bold text-danger mb-1">Research Failed</h3>
              <p className="text-muted leading-relaxed">{job.error}</p>
              <button 
                onClick={() => setJob({ ...job, phase: "idle" })}
                className="mt-4 text-sm font-medium text-accent hover:underline"
              >
                Try a different query
              </button>
            </div>
          </div>
        ) : null}

        {job.phase === "running" ? (
          <ProgressCard taskId={job.taskId} currentStep={currentStep} progress={job.progress} />
        ) : null}

        {job.phase === "done" && job.result && orgId ? (
          <ResultsView result={job.result} taskId={job.taskId} orgId={orgId} />
        ) : null}
      </main>
    </div>
  );
}

interface UserLike {
  email?: string | null;
  uid?: string;
}

function HeaderBar({ running, user, onLogout }: { running: boolean; user: UserLike; onLogout: () => void }) {
  return (
    <nav className="glass sticky top-0 z-20">
      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
        <Link href="/" className="font-bold text-lg text-ink">
          <span className="text-accent">◈</span> MarketAI
        </Link>
        <div className="flex items-center gap-4">
          {running && (
            <span className="inline-flex items-center gap-2 text-mint text-xs">
              <span className="w-2 h-2 rounded-full bg-mint animate-pulse" /> live
            </span>
          )}
          <span className="text-sm text-muted">{user.email}</span>
          <button onClick={onLogout} className="text-muted hover:text-ink text-sm">
            Logout
          </button>
        </div>
      </div>
    </nav>
  );
}
function QueryHero({
  product,
  setProduct,
  mode,
  setMode,
  onStart,
  phase,
  error,
}: {
  product: string;
  setProduct: (v: string) => void;
  mode: "quick" | "deep";
  setMode: (m: "quick" | "deep") => void;
  onStart: () => void;
  phase: string;
  error?: string;
}) {
  return (
    <section className="mb-12">
      <h1 className="font-display text-4xl md:text-5xl font-bold mb-2">
        Market <span className="text-accent">Intelligence</span>, on demand
      </h1>
      <p className="text-muted max-w-2xl mb-8 leading-relaxed">
        Describe a product idea. Our agent crew scrapes competitors, models
        unit economics, and hands you a confidence-scored launch brief in under
        a minute.
      </p>

      {error ? (
        <div className="p-4 mb-6 rounded-xl bg-danger/10 border border-danger/30 text-danger text-sm">
          {error}
        </div>
      ) : null}

      {phase === "idle" || phase === "error" ? (
        <div className="glass rounded-xl p-6">
          <textarea
            value={product}
            onChange={(e) => setProduct(e.target.value)}
            placeholder="e.g. Smart hydration bottle with UV self-clean"
            rows={3}
            className="w-full bg-surface border border-border rounded-lg px-4 py-3 text-ink placeholder:text-faint focus:outline-none focus:ring-1 focus:ring-accent"
          />
          <div className="mt-4 flex flex-wrap gap-3 items-center">
            <div className="flex gap-2">
              {(["quick", "deep"] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  className={`px-4 py-2 rounded-lg border font-medium text-sm transition ${
                    mode === m
                      ? "bg-accent text-canvas"
                      : "bg-surface text-muted border-border hover:text-ink"
                  }`}
                >
                  {m === "quick" ? "⚡ Quick" : "🚀 Deep"}
                </button>
              ))}
            </div>
            <button
              onClick={onStart}
              disabled={!product.trim()}
              className="bg-accent text-canvas font-semibold px-6 py-2.5 rounded-lg lime-glow transition hover:scale-[1.03] disabled:opacity-40 disabled:hover:scale-100"
            >
              Launch Research →
            </button>
          </div>
        </div>
      ) : null}
    </section>
  );
}

function ProgressCard({
  taskId,
  currentStep,
  progress,
}: {
  taskId: string | null;
  currentStep: number;
  progress?: number;
}) {
  return (
    <div className="glass rounded-xl p-8 mb-12 shadow-xl border border-accent/20 relative overflow-hidden">
      {/* Background sweep animation */}
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-accent/5 to-transparent w-[200%] animate-sweep pointer-events-none" />
      
      <div className="flex justify-between items-center mb-6 relative z-10">
        <div className="flex flex-col gap-1">
          <h3 className="text-xl font-bold font-display text-ink">Analyzing Market</h3>
          <p className="text-muted text-sm flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-accent animate-pulse" />
            Live Task ID: <span className="font-mono text-xs">{taskId?.slice(0, 8) || "..."}</span>
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <p className="text-accent font-mono text-2xl font-bold">{progress}%</p>
          <p className="text-muted text-xs uppercase tracking-wider">Complete</p>
        </div>
      </div>
      
      <div className="relative z-10 bg-surface-2 rounded-xl p-6">
        <StepStepper current={currentStep} />
        <div className="mt-6 flex items-center gap-3">
          <div className="w-5 h-5 rounded-full border-2 border-accent border-t-transparent animate-spin" />
          <p className="text-ink font-medium tracking-wide">
            {STEPS[currentStep]?.label || "Finalizing"}...
          </p>
        </div>
      </div>
    </div>
  );
}

function StepStepper({ current }: { current: number }) {
  const icons = ["🕵️", "🧮", "⏸️", "📄", "🎯"];
  return (
    <div className="flex items-center gap-2">
      {icons.map((icon, i) => {
        const active = i === current;
        const done = i < current;
        return (
          <div key={i} className="flex items-center gap-2">
            <div
              className={`w-9 h-9 rounded-full flex items-center justify-center text-base transition ${
                done
                  ? "bg-mint text-canvas"
                  : active
                  ? "bg-accent text-canvas scale-110"
                  : "bg-surface-2 text-muted"
              }`}
            >
              {done ? "✓" : icon}
            </div>
            {i < icons.length - 1 ? (
              <div className={`w-6 h-0.5 ${done || active ? "bg-accent" : "bg-border"}`} />
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
function ResultsView({
  result,
  taskId,
  orgId,
}: {
  result: ResearchResult;
  taskId: string | null;
  orgId: string;
}) {
  const fin = result.financials ?? {};
  const conf = result.confidence ?? {};
  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 className="text-2xl font-bold">
          {fin.pricing_basis ?? result.product_idea}
        </h2>
        {taskId ? (
          <a
            href={researchPdfUrl(orgId, taskId)}
            className="bg-surface-2 text-ink border border-border px-4 py-2 rounded-lg text-sm font-medium hover:ring-1 hover:ring-accent transition"
          >
            ⬇ Download PDF Report
          </a>
        ) : null}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <FinancialPanel fin={fin} />
        <ConfidencePanel conf={conf} />
      </div>

      {result.executive_summary ? (
        <div className="ink-card rounded-xl p-6">
          <h3 className="text-lg font-semibold mb-3 text-accent">📄 Launch Brief</h3>
          <Markdown text={result.executive_summary} />
        </div>
      ) : null}
    </section>
  );
}

interface FinancialData {
  estimated_cogs?: number;
  suggested_retail_price?: number;
  projected_margin_percentage?: number;
  key_competitor_prices?: string[];
}

function FinancialPanel({ fin }: { fin: FinancialData | null | undefined }) {
  const cogs = fin?.estimated_cogs;
  const retail = fin?.suggested_retail_price;
  const margin = fin?.projected_margin_percentage;
  const prices: string[] = fin?.key_competitor_prices ?? [];

  const metric = (label: string, value: string, sub: string, tone = "text-ink") => (
    <div className="ink-card rounded-xl p-5">
      <p className="text-xs uppercase tracking-wide text-muted">{label}</p>
      <p className={`text-3xl font-bold font-mono ${tone}`}>{value}</p>
      <p className="text-xs text-faint">{sub}</p>
    </div>
  );

  return (
    <div>
      <h3 className="text-lg font-semibold mb-3 text-accent">🧮 Unit Economics</h3>
      <div className="grid grid-cols-2 gap-4">
        {cogs ? metric("COGS", `$ ${cogs.toFixed(2)}`, "per unit") : null}
        {retail ? metric("Retail", `$ ${retail.toFixed(2)}`, "per unit") : null}
        {margin ? metric(
          "Gross Margin",
          `${margin.toFixed(1)}%`,
          "implied",
          margin >= 50 ? "text-mint" : margin >= 30 ? "text-accent" : "text-danger"
        ) : null}
      </div>
      {prices?.length ? (
        <div className="mt-4 ink-card rounded-xl p-5">
          <p className="text-xs uppercase text-muted mb-3">Competitor Pricing</p>
          <ul className="space-y-2 text-sm">
            {prices.map((p, i) => (
              <li key={i} className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-accent" />
                <span className="text-ink">{p}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

interface ConfidenceData {
  overall_score?: number;
  source_reliability?: number;
  evidence_coverage?: number;
  consistency?: number;
  summary?: string;
}

function ConfidencePanel({ conf }: { conf: ConfidenceData | null | undefined }) {
  const score = conf?.overall_score ?? 0;
  const color = score >= 75 ? "#2ee67f" : score >= 50 ? "#c8ff3c" : "#ff4d5d";
  const subs: [string, number][] = [
    ["Source Reliability", conf?.source_reliability ?? 0],
    ["Evidence Coverage", conf?.evidence_coverage ?? 0],
    ["Consistency", conf?.consistency ?? 0],
  ];
  return (
    <div className="ink-card rounded-xl p-6">
      <h3 className="text-lg font-semibold mb-3 text-accent">🎯 Confidence</h3>
      <div className="flex items-center gap-5">
        <Ring score={score} color={color} />
        <div className="flex-1 space-y-3">
          {subs.map(([label, val]) => (
            <div key={label}>
              <div className="flex justify-between text-xs">
                <span className="text-muted">{label}</span>
                <span className="font-mono text-ink">{val}/100</span>
              </div>
              <div className="h-2 rounded-full bg-surface-2 mt-1">
                <div
                  className="h-2 rounded-full"
                  style={{ width: `${val}%`, backgroundColor: color }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
      {conf?.summary ? (
        <p className="mt-4 text-sm text-muted leading-relaxed">{conf.summary}</p>
      ) : null}
    </div>
  );
}

function Ring({ score, color }: { score: number; color: string }) {
  const r = 34;
  const c = 2 * Math.PI * r;
  const off = c - (Math.min(score, 100) / 100) * c;
  return (
    <div className="relative w-24 h-24">
      <svg width="24" height="24" viewBox="0 0 80 80" className="w-full h-full">
        <circle cx="40" cy="40" r={r} fill="none" stroke="rgba(154,167,188,0.2)" strokeWidth="8" />
        <circle
          cx="40"
          cy="40"
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={`${c}`}
          strokeDashoffset={off}
          className="ring-fill"
          transform="rotate(-90 40 40)"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="font-mono font-bold text-xl" style={{ color }}>
          {score}
        </span>
      </div>
    </div>
  );
}

function Markdown({ text }: { text: string }) {
  const lines = text.split("\n");
  const rendered: React.ReactNode[] = [];
  
  let inList = false;
  let listItems: React.ReactNode[] = [];

  const parseInline = (str: string) => {
    // Bold: **text**
    const parts = str.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={i} className="font-semibold text-ink">{part.slice(2, -2)}</strong>;
      }
      return part;
    });
  };

  const flushList = () => {
    if (inList && listItems.length > 0) {
      rendered.push(<ul key={`ul-${rendered.length}`} className="list-none space-y-2 mb-4">{listItems}</ul>);
      listItems = [];
      inList = false;
    }
  };

  lines.forEach((line, index) => {
    const l = line.trim();
    if (!l) {
      flushList();
      rendered.push(<div key={index} className="h-2" />);
      return;
    }

    if (l.startsWith("### ")) {
      flushList();
      rendered.push(<h3 key={index} className="text-lg font-bold mt-4 mb-2 text-ink">{parseInline(l.slice(4))}</h3>);
    } else if (l.startsWith("## ")) {
      flushList();
      rendered.push(<h2 key={index} className="text-xl font-bold font-display mt-6 mb-3 text-accent">{parseInline(l.slice(3))}</h2>);
    } else if (l.startsWith("# ")) {
      flushList();
      rendered.push(<h1 key={index} className="text-2xl font-bold font-display mt-8 mb-4 text-ink">{parseInline(l.slice(2))}</h1>);
    } else if (l.startsWith("- ") || l.startsWith("* ")) {
      inList = true;
      listItems.push(
        <li key={index} className="flex gap-2 text-muted leading-relaxed">
          <span className="text-accent shrink-0 mt-0.5">▸</span>
          <span>{parseInline(l.slice(2))}</span>
        </li>
      );
    } else {
      flushList();
      rendered.push(<p key={index} className="text-muted leading-relaxed mb-3">{parseInline(l)}</p>);
    }
  });

  flushList();

  return <div className="text-sm leading-relaxed text-ink">{rendered}</div>;
}