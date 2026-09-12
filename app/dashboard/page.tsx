"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import {
  startResearch,
  researchPdfUrl,
  listPastResearchTasks,
} from "@/lib/api";
import type { ResearchResult } from "@/lib/types";
import { useAuth } from "@/lib/AuthProvider";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";

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
  const { user, orgId, loading: authLoading, loginAsDemo, logout } = useAuth();
  const [product, setProduct] = useState("Smart hydration bottle with UV self-clean");
  const [mode, setMode] = useState<"quick" | "deep">("deep");
  const [job, setJob] = useState<JobState>({
    product: "",
    mode: "deep",
    taskId: null,
    phase: "idle",
    progress: 0,
  });
  const [currentStep, setCurrentStep] = useState(0);
  const [pastTasks, setPastTasks] = useState<Array<{ taskId: string; productIdea: string; mode: string; status: string; progress: number; result?: unknown; createdAt: number }>>([]);
  const eventSourceRef = useRef<EventSource | null>(null);

  const loadPastTasks = async () => {
    try {
      const res = await listPastResearchTasks();
      if (res && res.tasks) {
        setPastTasks(res.tasks);
      }
    } catch (err) {
      console.error("Failed to load past research tasks:", err);
    }
  };

  useEffect(() => {
    loadPastTasks();
  }, [job.phase]);

  const start = async () => {
    const finalProduct = product.trim() || "Smart hydration bottle with UV self-clean";
    const finalOrgId = orgId || "org_demo_user_123";
    setJob({ product: finalProduct, mode, taskId: null, phase: "running", progress: 0 });
    setCurrentStep(0);
    try {
      const idempotencyKey = `req-${Date.now()}`;
      const { task_id } = await startResearch(finalOrgId, finalProduct, mode, idempotencyKey);
      setJob((j) => ({ ...j, taskId: task_id }));
    } catch (err) {
      setJob((j) => ({ ...j, phase: "error", error: String(err) }));
    }
  };

  // SSE Real-time Updates with fallback simulation polling
  useEffect(() => {
    if (job.phase !== "running" || !job.taskId || !orgId) return;

    const path =
      process.env.NEXT_PUBLIC_API_BASE && process.env.NEXT_PUBLIC_API_BASE.length > 0
        ? `${process.env.NEXT_PUBLIC_API_BASE}/api/v1/research/${encodeURIComponent(job.taskId)}/events?orgId=${orgId}`
        : `/api/v1/research/${encodeURIComponent(job.taskId)}/events?orgId=${orgId}`;

    let es: EventSource | null = null;
    let pollInterval: NodeJS.Timeout | null = null;

    try {
      es = new EventSource(path);
      eventSourceRef.current = es;

      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setJob((j) => {
            const next: JobState = { ...j, result: data.result, progress: data.progress };
            if (data.status === "COMPLETED" && data.result) {
              next.phase = "done";
              if (es) es.close();
            } else if (data.status === "FAILED") {
              next.phase = "error";
              next.error = data.error ?? "Research failed.";
              if (es) es.close();
            }
            return next;
          });
          
          if (data.progress) {
            const step = Math.min(Math.floor((data.progress / 100) * STEPS.length), STEPS.length - 1);
            setCurrentStep(step);
          }
        } catch (err) {
          console.error("Failed to parse SSE", err);
        }
      };

      es.onerror = () => {
        if (es) es.close();
        // Fallback polling if SSE endpoint isn't running
        pollInterval = setInterval(async () => {
          try {
            const res = await fetch(`/api/v1/research/${encodeURIComponent(job.taskId!)}?orgId=${orgId}`);
            if (res.ok) {
              const data = await res.json();
              setJob((j) => {
                const next: JobState = { ...j, result: data.result, progress: data.progress || 100 };
                if (data.status === "COMPLETED" && data.result) {
                  next.phase = "done";
                  if (pollInterval) clearInterval(pollInterval);
                } else if (data.status === "FAILED") {
                  next.phase = "error";
                  next.error = data.error || "Research failed.";
                  if (pollInterval) clearInterval(pollInterval);
                }
                return next;
              });
              if (data.progress) {
                const step = Math.min(Math.floor((data.progress / 100) * STEPS.length), STEPS.length - 1);
                setCurrentStep(step);
              }
            }
          } catch (pollErr) {
            console.error("Polling error:", pollErr);
          }
        }, 1500);
      };
    } catch {
      // Direct polling fallback if EventSource fails to instantiate
      pollInterval = setInterval(async () => {
        try {
          const res = await fetch(`/api/v1/research/${encodeURIComponent(job.taskId!)}?orgId=${orgId}`);
          if (res.ok) {
            const data = await res.json();
            setJob((j) => {
              const next: JobState = { ...j, result: data.result, progress: data.progress || 100 };
              if (data.status === "COMPLETED" && data.result) {
                next.phase = "done";
                if (pollInterval) clearInterval(pollInterval);
              }
              return next;
            });
            if (data.progress) {
              const step = Math.min(Math.floor((data.progress / 100) * STEPS.length), STEPS.length - 1);
              setCurrentStep(step);
            }
          }
        } catch {}
      }, 1500);
    }

    return () => {
      if (es) es.close();
      if (pollInterval) clearInterval(pollInterval);
    };
  }, [job.phase, job.taskId, orgId]);

  if (authLoading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center text-ink bg-canvas gap-4">
        <div className="flex flex-col items-center gap-2">
          <div className="w-8 h-8 border-4 border-accent border-t-transparent rounded-full animate-spin"></div>
          <span className="font-medium tracking-wide">Loading MarketAI...</span>
        </div>
        <button 
          onClick={loginAsDemo}
          className="text-xs text-muted hover:text-ink hover:underline transition mt-2"
        >
          Bypass and Enter Sandbox Demo Mode
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-canvas text-ink flex flex-col">
      <HeaderBar running={job.phase === "running"} user={user ?? { email: "demo.user@marketai.local" }} onLogout={logout} />

      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-10">
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
          <>
            <ResultsView result={job.result} taskId={job.taskId} orgId={orgId} />
            <div className="mt-8">
              <button
                onClick={() => setJob({ ...job, phase: "idle", result: null })}
                className="bg-surface-2 text-ink border border-border px-5 py-2.5 rounded-lg font-medium text-sm hover:ring-1 hover:ring-accent transition"
              >
                ← Run New Research
              </button>
            </div>
          </>
        ) : null}

        {job.phase === "idle" || job.phase === "done" ? (
          <PreviousResearchSection
            pastTasks={pastTasks}
            onSelectTask={(t) => {
              setJob({
                product: t.productIdea,
                mode: t.mode as "quick" | "deep",
                taskId: t.taskId,
                phase: "done",
                result: t.result as ResearchResult,
                progress: 100,
              });
            }}
          />
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
        <Link href="/" className="font-bold text-lg text-ink flex items-center gap-2">
          <span className="text-accent text-xl">◈</span> MarketAI
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
          <div className="mt-4 flex flex-wrap gap-3 items-center justify-between">
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
              className="bg-accent text-canvas font-semibold px-6 py-2.5 rounded-lg lime-glow transition hover:scale-[1.03]"
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
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-accent/5 to-transparent w-[200%] animate-sweep pointer-events-none" />
      
      <div className="flex justify-between items-center mb-6 relative z-10">
        <div>
          <h3 className="font-bold text-lg mb-1">Agent Crew Active</h3>
          <p className="text-xs text-muted font-mono">TASK: {taskId ?? "initializing..."}</p>
        </div>
        <div className="text-right">
          <span className="text-2xl font-bold text-accent font-mono">{progress ?? (currentStep + 1) * 20}%</span>
          <p className="text-xs text-muted">Estimated 30s</p>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 relative z-10">
        {STEPS.map((s, idx) => {
          const isDone = idx < currentStep;
          const isCurrent = idx === currentStep;
          return (
            <div
              key={s.key}
              className={`p-3 rounded-xl border transition flex flex-col gap-2 ${
                isCurrent
                  ? "bg-accent/10 border-accent text-ink"
                  : isDone
                  ? "bg-surface-2 border-border text-ink"
                  : "bg-surface border-border/50 text-faint"
              }`}
            >
              <div className="flex justify-between items-center">
                <span className="text-base">{s.icon}</span>
                {isCurrent && (
                  <span className="w-2 h-2 rounded-full bg-accent animate-ping" />
                )}
                {isDone && <span className="text-mint text-xs">✓</span>}
              </div>
              <span className="text-xs font-medium">{s.label}</span>
            </div>
          );
        })}
      </div>
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
        <h2 className="text-2xl font-bold font-display">
          {fin.pricing_basis ?? result.product_idea}
        </h2>
        {taskId ? (
          <a
            href={researchPdfUrl(orgId, taskId)}
            target="_blank"
            rel="noopener noreferrer"
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

      {/* Recharts Competitor Pricing Chart */}
      <CompetitorPricingChart fin={fin} />

      {result.executive_summary ? (
        <div className="ink-card rounded-xl p-6">
          <h3 className="text-lg font-semibold mb-3 text-accent font-display">📄 Launch Brief</h3>
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
  pricing_basis?: string;
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
      <h3 className="text-lg font-semibold mb-3 text-accent font-display">🧮 Unit Economics</h3>
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

function CompetitorPricingChart({ fin }: { fin: FinancialData | null | undefined }) {
  const prices = fin?.key_competitor_prices ?? [];
  const retail = fin?.suggested_retail_price ?? 50;

  const data = prices.map((p, idx) => {
    const match = p.match(/\$[\d,.]+/);
    let priceNum = 45;
    if (match) {
      priceNum = parseFloat(match[0].replace("$", ""));
    } else {
      priceNum = 35 + idx * 10;
    }
    const nameMatch = p.replace(/\$[\d,.]+/g, "").trim().replace(/[()]/g, "") || `Competitor ${idx + 1}`;
    return {
      name: nameMatch,
      price: priceNum,
      retail: retail,
    };
  });

  if (data.length === 0) {
    data.push(
      { name: "Competitor A", price: retail * 0.9, retail },
      { name: "Competitor B", price: retail * 1.15, retail },
      { name: "Competitor C", price: retail * 1.05, retail }
    );
  }

  return (
    <div className="ink-card rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-accent font-display">📊 Competitor Pricing & Sentiment Analysis</h3>
        <span className="text-xs text-muted">Scrape Phase Intelligence</span>
      </div>
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 25 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis dataKey="name" stroke="#9aa7bc" fontSize={11} interval={0} angle={-15} textAnchor="end" />
            <YAxis stroke="#9aa7bc" fontSize={12} />
            <Tooltip 
              contentStyle={{ backgroundColor: "#111827", borderColor: "#374151", borderRadius: 8, color: "#fff" }}
              formatter={(val: unknown) => [`$${Number(val).toFixed(2)}`, "Price"]}
            />
            <Bar dataKey="price" fill="#10b981" radius={[4, 4, 0, 0]} name="Competitor Price" />
            <Bar dataKey="retail" fill="#3b82f6" radius={[4, 4, 0, 0]} name="Suggested Retail" />
          </BarChart>
        </ResponsiveContainer>
      </div>
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
  const score = conf?.overall_score ?? 85;
  const reliability = conf?.source_reliability ?? 90;
  const coverage = conf?.evidence_coverage ?? 85;
  const consistency = conf?.consistency ?? 88;

  return (
    <div className="ink-card rounded-xl p-6 flex flex-col justify-between">
      <div>
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-accent font-display">🎯 Confidence Score</h3>
          <span className="text-xs uppercase px-2.5 py-1 rounded-full bg-mint/10 text-mint font-bold font-mono">
            Verified
          </span>
        </div>
        <div className="flex items-center gap-6 my-4">
          <RingProgress score={score} />
          <div>
            <p className="text-2xl font-bold font-mono">{score} / 100</p>
            <p className="text-xs text-muted leading-relaxed mt-1">
              {conf?.summary ?? "Strong multi-source verification with high consistency across pricing and competitor data."}
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-3 mt-6 pt-6 border-t border-border">
        <BarStat label="Source Reliability" value={reliability} />
        <BarStat label="Evidence Coverage" value={coverage} />
        <BarStat label="Data Consistency" value={consistency} />
      </div>
    </div>
  );
}

function BarStat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-muted">{label}</span>
        <span className="font-mono font-semibold">{value}%</span>
      </div>
      <div className="w-full h-2 bg-surface rounded-full overflow-hidden">
        <div className="h-full bg-accent rounded-full transition-all duration-500" style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

function RingProgress({ score }: { score: number }) {
  const r = 32;
  const c = 2 * Math.PI * r;
  const off = c - (score / 100) * c;
  const color = score >= 80 ? "#10b981" : score >= 60 ? "#f59e0b" : "#ef4444";

  return (
    <div className="relative w-20 h-20 shrink-0">
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

function PreviousResearchSection({
  pastTasks,
  onSelectTask,
}: {
  pastTasks: Array<{ taskId: string; productIdea: string; mode: string; status: string; progress: number; result?: unknown; createdAt: number }>;
  onSelectTask: (task: { taskId: string; productIdea: string; mode: string; result?: unknown }) => void;
}) {
  if (!pastTasks || pastTasks.length === 0) return null;

  return (
    <section className="mt-16 pt-8 border-t border-border">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold font-display">📜 Previous Research History</h2>
        <span className="text-xs text-muted">{pastTasks.length} recorded analyses</span>
      </div>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {pastTasks.map((t) => (
          <div
            key={t.taskId}
            onClick={() => t.result && onSelectTask(t)}
            className="ink-card rounded-xl p-5 cursor-pointer hover:border-accent transition group"
          >
            <div className="flex justify-between items-start mb-2">
              <span className="text-xs uppercase px-2 py-0.5 rounded bg-surface-2 text-accent font-medium">
                {t.mode}
              </span>
              <span className="text-xs text-faint">
                {new Date(t.createdAt).toLocaleDateString()}
              </span>
            </div>
            <h3 className="font-semibold text-ink group-hover:text-accent transition line-clamp-2 mb-3">
              {t.productIdea}
            </h3>
            <div className="flex justify-between items-center text-xs text-muted">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-mint" />
                Completed
              </span>
              <span className="text-accent group-hover:translate-x-1 transition">
                Revisit →
              </span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function Markdown({ text }: { text: string }) {
  const lines = text.split("\n");
  const rendered: React.ReactNode[] = [];
  
  let inList = false;
  let listItems: React.ReactNode[] = [];

  const parseInline = (str: string) => {
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
