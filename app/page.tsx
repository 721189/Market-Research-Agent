import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen text-ink overflow-hidden">
      {/* Nav */}
      <nav className="glass sticky top-0 z-20">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="font-bold text-lg">
            <span className="text-accent">◈</span> MarketAI
          </Link>
          <Link
            href="/dashboard"
            className="bg-accent text-canvas font-semibold px-5 py-2 rounded-lg lime-glow hover:scale-[1.03] transition"
          >
            Open Dashboard →
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative max-w-6xl mx-auto px-6 pt-20 pb-16 text-center">
        <div className="absolute inset-0 pointer-events-none hero-grid" />
        <p className="inline-flex items-center gap-2 text-mint text-sm border border-border rounded-full px-4 py-1.5">
          <span className="w-2 h-2 rounded-full bg-mint animate-pulse" />
          Three AI agents · one confidence-scored brief
        </p>
        <h1 className="font-display text-5xl md:text-7xl font-bold leading-tight mt-6">
          Market intelligence,
          <br />
          <span className="text-accent">without the agency</span>
        </h1>
        <p className="text-lg text-muted max-w-2xl mx-auto mt-6 leading-relaxed">
          Describe any product idea. We scrape your competitors, model realistic
          unit economics, and generate a stakeholder-ready launch plan — with a
          transparent confidence score. In under a minute.
        </p>
        <div className="mt-8 flex flex-wrap gap-4">
          <Link
            href="/dashboard"
            className="bg-accent text-canvas font-semibold px-8 py-3 rounded-lg lime-glow text-lg hover:scale-[1.04] transition"
          >
            Launch Market Research →
          </Link>
          <a
            href="#how"
            className="text-ink border border-border px-8 py-3 rounded-lg text-lg font-medium hover:bg-surface-2 transition"
          >
            See how it works
          </a>
        </div>
        <p className="text-xs text-faint mt-6 max-w-xl mx-auto">
          No credit card. Works with your OpenAI-compatible LLM key. Free-tier friendly.
        </p>
      </section>

      {/* How it works */}
      <section id="how" className="max-w-6xl mx-auto px-6 py-20">
        <h2 className="text-3xl font-bold mb-2">From idea to thesis in 4 steps</h2>
        <p className="text-muted max-w-xl mb-12">
          A deterministic agent crew runs your query end-to-end. You stay in
          control at the one human checkpoint.
        </p>
        <div className="grid md:grid-cols-4 gap-6">
          <Step n="01" emoji="🕵️" title="Scrape competitors" desc="Top 5 rivals, their products & live pricing pulled from the web." />
          <Step n="02" emoji="🧮" title="Model economics" desc="COGS, suggested retail, and gross margin — priced and structured." />
          <Step n="03" emoji="⏸️" title="Human review" desc="Approve, edit, or reject the numbers before anything ships." />
          <Step n="04" emoji="🎯" title="Score & brief" desc="A confidence-scored launch brief you can export to PDF." />
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-3xl mx-auto px-6 py-24 text-center">
        <h2 className="font-display text-4xl md:text-5xl font-bold">
          Stop guessing. <span className="text-accent">Start evidence.</span>
        </h2>
        <Link
          href="/dashboard"
          className="mt-8 inline-block bg-accent text-canvas font-semibold px-8 py-3 rounded-lg lime-glow text-lg hover:scale-[1.04] transition"
        >
          Research a product →
        </Link>
      </section>
    </div>
  );
}

function Step({
  n,
  emoji,
  title,
  desc,
}: {
  n: string;
  emoji: string;
  title: string;
  desc: string;
}) {
  return (
    <div className="ink-card rounded-xl p-6">
      <div className="flex items-center justify-between">
        <span className="text-2xl">{emoji}</span>
        <span className="font-mono text-xs text-faint">{n}</span>
      </div>
      <h3 className="text-lg font-semibold mt-3">{title}</h3>
      <p className="text-sm text-muted mt-2 leading-relaxed">{desc}</p>
    </div>
  );
}