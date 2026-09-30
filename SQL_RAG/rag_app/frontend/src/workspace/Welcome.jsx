export const EXAMPLE_QUESTIONS = [
  "Top 10 customers by total order value",
  "Monthly revenue in 2025",
  "Which product categories have the most returns?",
  "Average order value by country",
  "Best-selling brands by revenue",
  "How many new users signed up each month this year?",
];

const TABLES = [
  ["orders", "One row per order, with status and timestamps"],
  ["order_items", "Line items with sale price and status"],
  ["users", "Customers with age, gender and location"],
  ["products", "Catalog: category, brand, cost, retail price"],
  ["inventory_items", "Stock units with cost and sold date"],
  ["events", "Website sessions and page views"],
  ["distribution_centers", "Warehouse locations"],
];

const STEPS = ["Retrieve similar example queries", "Pick the relevant schema", "Write SQL with Gemini 2.5 Pro", "Check it is read-only", "Run it on BigQuery"];

export default function Welcome({ onAsk, busy }) {
  return (
    <div className="mx-auto max-w-3xl px-5 py-10 md:py-16">
      <p className="text-xs font-medium uppercase tracking-wider text-emerald-400">Natural-language SQL · RAG</p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight text-white md:text-4xl">Ask anything about 125k orders.</h1>
      <p className="mt-3 max-w-2xl leading-relaxed text-zinc-400">
        Every answer is SQL written by an LLM that first retrieves similar example queries, then runs live and read-only on
        BigQuery's public <span className="font-mono text-zinc-300">thelook_ecommerce</span> dataset.
      </p>

      <h2 className="mt-8 text-sm font-medium text-zinc-300">Try one</h2>
      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        {EXAMPLE_QUESTIONS.map((q) => (
          <button
            key={q}
            type="button"
            disabled={busy}
            onClick={() => onAsk(q)}
            className="rounded-lg border border-line bg-panel px-4 py-3 text-left text-sm text-zinc-200 transition-colors hover:border-emerald-400/50 hover:text-white focus-visible:outline-2 focus-visible:outline-emerald-400 disabled:opacity-50"
          >
            {q}
          </button>
        ))}
      </div>

      <div className="mt-10 grid gap-8 md:grid-cols-[1fr_1fr]">
        <section>
          <h2 className="text-sm font-medium text-zinc-300">What's in the data</h2>
          <dl className="mt-3 space-y-2 text-sm">
            {TABLES.map(([name, desc]) => (
              <div key={name} className="flex gap-3">
                <dt className="w-40 shrink-0 font-mono text-[13px] text-zinc-300">{name}</dt>
                <dd className="text-zinc-500">{desc}</dd>
              </div>
            ))}
          </dl>
        </section>
        <section>
          <h2 className="text-sm font-medium text-zinc-300">What happens when you ask</h2>
          <ol className="mt-3 space-y-2 text-sm text-zinc-500">
            {STEPS.map((step, i) => (
              <li key={step} className="flex gap-3">
                <span className="grid size-5 shrink-0 place-items-center rounded-full border border-line text-[11px] text-zinc-400">{i + 1}</span>
                {step}
              </li>
            ))}
          </ol>
        </section>
      </div>
    </div>
  );
}
