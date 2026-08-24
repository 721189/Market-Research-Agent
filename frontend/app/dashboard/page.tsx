"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  startResearch,
  pollResearch,
  researchPdfUrl,
} from "../lib/api";
import type { PollResponse, ResearchResult } from "../lib/types";

interface JobState {
  product: string;
  mode: "quick" | "deep" | "batch";
  taskId: string | null;
  phase: "idle" | "running" | "done" | "error";
  error?: string;
  result?: ResearchResult | null;
}

const STEPS = [
  { key: "scrape", label: "Competitor Scrape", icon: "🕵️" },
  { key: "financial", label: "Financial Margin", icon: "🧮" },
  { key: "review", label: "Review Gate", icon: "⏸️" },
  { key: "brief", label: "Launch Brief", icon: "📄" },
  { key: "confidence", label: "Confidence", icon: "🎯" },
];

export default function DashboardPage() {
  const [product, setProduct] = useState("");
  const [mode, setMode] = useState<"quick" | "deep">("deep");
  const [job, setJob] = useState<JobState>({
    product: "",
    mode: "deep",
    taskId: null,
    phase: "idle",
  });
  const [currentStep, setCurrentStep] = useState(0);

  const start = async () => {
    if (!product.trim()) return;
    setJob({ product, mode, taskId: null, phase: "running" });
    setCurrentStep(0);
    try {
      const { task_id } = await startResearch(product.trim(), mode);
      setJob((j) => ({ ...j, taskId: task_id }));
    } catch (err) {
      setJob((j) => ({ ...j, phase: "error", error: String(err) }));
    }
  };

  // Poll while running
  useEffect(() => {
    if (job.phase !== "running" || !job.taskId) return;
    const timer = setInterval(async () => {
      try {
        const res: PollResponse = await pollResearch(job.taskId!);
        setJob((j) => {
          const next: JobState = { ...j, result: res.result };
          if (res.status === "SUCCESS" && res.result) {
            next.phase = "done";
          } else if (res.status === "FAILURE") {
            next.phase = "error";
            next.error = res.error ?? "Research failed.";
          }
          return next;
        });
      } catch (err) {
        setJob((j) => ({ ...j, phase: "error", error: String(err) }));
      }
    }, 2500);
    return () => clearInterval(timer);
  }, [job.phase, job.taskId]);

  // Advance the stepper while running (visual pacing).
  useEffect(() => {
    if (job.phase !== "running") return;
    const timer = setInterval(() => {
      setCurrentStep((s) => Math.min(s + 1, STEPS.length - 1));
    }, 1800);
    return () => clearInterval(timer);
  }, [job.phase]);

  return (
    <div className="min-h-screen text-ink">
      <HeaderBar running={job.phase === "running"} />

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

        {job.phase === "running" ? (
          <ProgressCard taskId={job.taskId} currentStep={currentStep} />
        ) : null}

        {job.phase === "done" && job.result ? (
          <ResultsView result={job.result} taskId={job.taskId} />
        ) : null}
      </main>
    </div>
  );
}

function HeaderBar({ running }: { running: boolean }) {
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
          <Link href="/" className="text-muted hover:text-ink text-sm">
            Home
          </Link>
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
          {error ? <p className="mt-3 text-danger">⚠️ {error}</p> : null}
        </div>
      ) : null}
    </section>
  );
}

function ProgressCard({
  taskId,
  currentStep,
}: {
  taskId: string | null;
  currentStep: number;
}) {
  return (
    <div className="glass rounded-xl p-6 mb-12">
      <p className="text-muted mb-5 text-sm">
        Crew is running ·{" "}
        <span className="text-accent font-mono">task {taskId?.slice(0, 8)}</span>
      </p>
      <StepStepper current={currentStep} />
      <div className="mt-5 flex items-center gap-3">
        <span className="w-3 h-3 rounded-full bg-accent animate-pulse" />
        <p className="text-ink font-medium">{STEPS[currentStep]?.label} …</p>
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
}: {
  result: ResearchResult;
  taskId: string | null;
}) {
  const fin = result.financials ?? {};
  const conf = result.confidence ?? {};
  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 className="text-2xl font-bold">
          {fin.product_name ?? result.product_idea}
        </h2>
        {taskId ? (
          <a
            href={researchPdfUrl(taskId)}
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

      {result.launch_brief ? (
        <div className="ink-card rounded-xl p-6">
          <h3 className="text-lg font-semibold mb-3 text-accent">📄 Launch Brief</h3>
          <Markdown text={result.launch_brief} />
        </div>
      ) : null}
    </section>
  );
}

function FinancialPanel({ fin }: { fin: any }) {
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
function ConfidencePanel({ conf }: { conf: any }) {
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
  const lines = text.split("\n").filter(Boolean);
  return (
    <div className="space-y-3 text-sm leading-relaxed text-ink">
      {lines.map((line, i) => {
        if (line.startsWith("## ")) {
          return (
            <h4 className="text-base font-semibold mt-2" key={i}>
              {line.slice(3)}
            </h4>
          );
        }
        if (line.startsWith("- ") || line.startsWith("• ")) {
          return (
            <div className="flex gap-2 text-muted pl-4" key={i}>
              <span className="text-accent">▸</span>
              <span>{line.slice(2)}</span>
            </div>
          );
        }
        return <p className="text-muted" key={i}>{line}</p>;
      })}
    </div>
  );
}