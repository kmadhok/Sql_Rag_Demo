# UI Improvement Plan — SQL RAG Demo

_Written 2026-09-29 after reviewing the live site (desktop 1440px + mobile 390px) and the `main` source._

## Deployment status

- Live frontend revision `sql-rag-frontend-simple-00008-7kl` and backend `sql-rag-api-simple-00017-2qx` were deployed 2026-01-31.
- **They match `main`.** No app source changed after `3b0aaf568` (Jan 24); later commits only touched `dist/`, `node_modules/.vite`, docs and deploy scripts. Rebuilding `main` with the prod `VITE_API_BASE_URL` gives a bundle with identical UI strings (±9 bytes of chunk hashes).
- **The live demo is broken:** every `/query/search` returns 500 because the Gemini API key is invalid (`400 API key not valid` from `utils/embedding_provider.py:297` during query embedding). The UI shows `Error: {"detail":"RAG pipeline returned no result."}`.

## Who this is for

This is a portfolio piece. The visitor is a hiring manager or engineer who gives it about 30 seconds. They don't know the `thelook_ecommerce` schema. They need to see **question → SQL → results → chart** succeed on the first click, plus a glimpse of how it works under the hood. Every recommendation below follows from that.

## Findings (ranked by impact)

| # | Issue | Evidence | Root cause |
|---|---|---|---|
| 1 | Every query fails | Live test of "Top users" chip | Invalid Gemini key on the backend |
| 2 | Layout and spacing broken throughout | Misplaced "U"/"A" avatars, options panel can't collapse, dead space below footer | The markup uses Tailwind utility classes (`h-screen`, `p-4`, `mb-2`, `max-h-0`, `opacity-0`, `rounded-full`, `md:p-6`…) but **Tailwind isn't installed**. `styles.css` hand-defines only some of them, and ≥51 used in `App.jsx`, `ChatInput.jsx` and `ChatMessage.jsx` alone are defined nowhere |
| 3 | Visitors see internal knobs first | "Documents: 20", "Auto Weights", "Query Rewrite" are always visible (`ChatInput.jsx:121`) | The collapse depends on the missing Tailwind classes |
| 4 | Errors are raw JSON, shown twice | Assistant bubble plus a pink alert both print `{"detail":...}` (`App.jsx:343`) | `err.message` is the raw response body; the message and the alert both render it |
| 5 | ~~Horizontal scroll on mobile~~ **Retracted** | The 500px `scrollWidth` came from Chrome's minimum window width during the review; with real device emulation (390×844) there is no horizontal scroll | n/a |
| 6 | Dashboard shows test junk to every visitor | "My Dashboard Test", chart titled "Use @create find the users", "count by id" (every bar = 1, y-axis clipped at 0.5), one chart rendering empty | Dashboards live in shared Firestore with no seeded or read-only demo state |
| 7 | Dead controls | The "Settings" button has no handler (`App.jsx:521`) | Leftover placeholder |
| 8 | Visitors have to learn a magic syntax | Placeholder says "use @create for SQL"; chips prefill `@create …` | SQL generation is opt-in through a prefix instead of being the default intent |
| 9 | Clashing visual language | Light-blue info alert and pink error alert on a dark theme, an unstyled "Options ▼" button, rainbow bar colors, a Send button that looks enabled when it's disabled | Three styling systems in use (MUI, hand-rolled CSS, phantom Tailwind) with no shared tokens |
| 10 | Weak first screen | A generic hero ("Explore Data with Natural Language") takes about 250px, with no dataset context and only 2 examples | Written for the author, not the visitor |

## Plan

### Phase 0: Make it work on OpenRouter (backend, ~0.5 day, blocks everything else)
Replaces the dead Gemini key with a single `OPENROUTER_API_KEY`. OpenRouter serves both chat models and embeddings through an OpenAI-compatible API (`https://openrouter.ai/api/v1`).
1. `openrouter_client.py`: same interface as `gemini_client.py` (`invoke`, `invoke_structured`, `test_connection`), built on the `openai` SDK with OpenRouter's `base_url`. `invoke_structured` uses `response_format` `json_schema` generated from the Pydantic model.
2. `llm_registry.py`: `LLM_PROVIDER=openrouter|gemini` (default stays `gemini`, so existing setups don't break). Model IDs become OpenRouter slugs; start with the same models to keep SQL quality unchanged (`google/gemini-2.5-pro` for generation, `google/gemini-2.5-flash-lite` for parse/rewrite/chat). Switching models afterwards is an env-var change.
3. `utils/embedding_provider.py`: add an `openrouter` provider (OpenAI embeddings client with OpenRouter's `base_url`, model from `OPENROUTER_EMBEDDING_MODEL`). `query_rewriter.py` calls `genai` directly, so route it through the registry.
4. Rebuild the FAISS index with the new embedding model. The prod index (`index_sample_queries_with_metadata_recovered`: 139 vectors, 768 dims, Gemini embeddings) only exists inside the deployed source bundle, so restore it from `gs://run-sources-brainrot-453319-us-central1/…` and commit a reproducible build script. Re-embedding 139 docs costs < $0.01.
5. Put `OPENROUTER_API_KEY` in Secret Manager and bind it with `--set-secrets`. Remove the plain-text `GEMINI_API_KEY` / `OPENAI_API_KEY` env vars from `deploy_api_simple.sh:165`. Restrict `CORS_ORIGINS` from `*` to the real frontend origin.
6. Make `/health` run a one-token embed call, so a dead key reports unhealthy instead of 200.
7. **Verify:** the "Top users" chip returns SQL plus result rows on the live URL; add unit tests for the provider switch and for structured output.

### Hosting on kanumadhok.com — ✅ done 2026-09-29
- Served at **kanumadhok.com/sql-rag**: `my_website/next.config.ts` rewrites `/sql-rag/*` to the Cloud Run frontend, Vite builds with `base: /sql-rag/`, and nginx strips the prefix so the service's own URL keeps working.
- The backend stays on Cloud Run (BigQuery and Firestore credentials come for free there). CORS allows kanumadhok.com, www.kanumadhok.com and the old frontend URL.
- Phase 0 shipped the same day: OpenRouter for LLM + embeddings, key in Secret Manager `openrouter-api-key`, index `index_sample_queries_openrouter`. Still open from Phase 0: the deep `/health` check (step 6).

### Phase 1: Fix the foundation (styling system) — ✅ done 2026-09-29
What shipped and what differed from the plan:
- Tailwind v4 via `@tailwindcss/vite`, imported **without preflight** (`src/tailwind.css`: theme + utilities only), so the existing base styles and MUI are untouched.
- The spacing tokens were **not** mapped into `@theme`: registering `--spacing-sm/md/lg/xl` also redefines `max-w-sm/md/lg/xl` (it made the message bubble 28px wide). The five named classes actually used (`gap-md`, `p-lg`, `space-x-sm`, `space-y-md`, `space-y-lg`) are defined as `@utility` rules instead.
- Removed about 100 lines of hand-written utilities from `styles.css`. As unlayered CSS they would have overridden Tailwind's responsive variants (e.g. `.hidden` beating `md:block`). `.container` was renamed to `.app-container`.
- Classes that were dead before now take effect. On desktop the app is a fixed-height shell (input pinned, chat and dashboard scroll inside their panels); below `md` the page scrolls normally, because the hero leaves no room for a fixed shell on phones.
- Flex fixes surfaced by the change: `min-w-0` on the message column (long SQL no longer widens the row) and `min-h-0` on `TabPanel` (the dashboard panel scrolls instead of being clipped).
- Verified with before/after screenshots at 1440×900 and an emulated 390×844 phone: the full ask → answer flow, the Options panel collapsing, no horizontal scroll, and dashboard scrolling.

Original plan:
Decision: **install Tailwind v4** (`@tailwindcss/vite`) rather than keep hand-writing utilities in `styles.css`.
- Why: the markup already uses Tailwind vocabulary, so installing it makes every existing class name work at once without touching markup. The alternative is adding each missing utility by hand indefinitely.
- Map the existing `:root` CSS variables into `@theme`, so colors and spacing stay the same.
- Delete the hand-rolled utilities in `styles.css` that Tailwind now provides (`.flex`, `.gap-*`, `.grid-cols-*`, `.h-*`…). Rename the custom ones that clash (`gap-md`, `space-x-sm`, `.container`) to Tailwind equivalents. Keep the component classes (`.card`, `.btn-*`, `.dashboard-*`).
- Leave MUI in place for now (8 files). Removing it is a separate, optional cleanup.
- **Verify:** screenshots at 1440px and 390px; the Options panel collapses; `document.documentElement.scrollWidth === innerWidth` on mobile.

### Redesign: Analyst workspace (direction B) — ✅ built 2026-09-30
Chosen from three mockups (answer page, analyst workspace, SQL notebook). Replaces the old Chat tab and covers most of Phase 2 below.
- Layout: a thread on the left (question + one-line result per turn) and a canvas on the right with Result / SQL / How it worked tabs. Phones show one pane at a time with a Chat / Answer switch.
- Every question generates SQL (no `@create`) and runs it automatically. Follow-ups carry the previous questions, summaries and SQL as context.
- Result: headline numbers, an automatic chart (bar for label + measure, line for time series, including split year/month columns), and the table. Column roles, summaries and formatting live in `src/workspace/analyzeResult.js`.
- "How it worked": the real pipeline (retrieval time, example count, tables, schema tokens, model, tokens, generation time, validation, BigQuery time/bytes/rows), the example queries the model saw, and the old Options panel as retrieval settings.
- Empty state from direction A: example questions (all six verified against the live pipeline), what's in the data, and what happens when you ask.
- Errors are plain language with Try again; BigQuery `success: false` is now treated as a failure (the old UI showed it as an empty success).
- Tests: `npm test` (Vitest), 45 tests over result analysis, SQL tokenizing and the ask flow.
- Not done yet: similarity scores for retrieved examples (the API doesn't return them), the dashboard's own redesign (Phase 3), removing the now-unused old chat components.

### Phase 2: Chat experience (~1 day)
1. **Make SQL generation the default.** Treat every question as a SQL request; `@create` becomes optional (still accepted). New placeholder: "Ask a question about orders, users, or products…".
2. **Empty state that teaches the dataset:** one line on what `thelook_ecommerce` is, a compact list of its tables (orders, order_items, users, products, …), and 4–6 example questions that are known to work, as chips.
3. **One answer card per response,** in this order: brief explanation → SQL block (syntax-highlighted, with copy and "Run" buttons) → results table (sticky header, row count, runtime) → optional "Chart this" / "Save to dashboard".
4. **"How this answer was made" disclosure,** collapsed by default: the retrieved example queries, tables used, model, and latency. This is where the RAG work is shown off; move the retrieval knobs (documents, hybrid, rewrite, validate) in here too, as "Advanced".
5. **Progress states** during the 5–20s wait: "Finding similar queries → Writing SQL → Validating". The backend already runs these steps; even step labels on a timer beat a blank screen.
6. **Readable errors:** parse `detail`, map known cases to plain language ("The AI service is unavailable — try again shortly"), render once as a dark-theme alert with a Retry button.
7. Remove the letter avatars; use alignment and background color for the user and assistant roles.

### Phase 3: Dashboard (~0.5–1 day)
1. **Seed a curated, read-only "Demo" dashboard** (e.g. revenue by month, top categories, orders by status, users by country) and show it by default. Let visitors create their own dashboards in `localStorage`, or behind a flag, so shared Firestore state can't get polluted again. Delete the current test dashboards.
2. **Chart defaults that make sense:** pick the x-axis from the first dimension column and y from the first numeric one; never default to "count by id". Use one accent color for single-series bars (reserve the categorical palette for multi-series). Start the y-axis at 0.
3. Fix empty-chart rendering, and show "No data" in place of a blank card.
4. Fill the grid width: the current layout leaves the right third empty.

### Phase 4: Shell and polish (~0.5 day)
1. Header: product name, a one-line value proposition, and a GitHub link. Delete the dead "Settings" button. Remove the large hero, or shrink it to one line, so the input sits above the fold.
2. Keep the tabs, but style them as a standard segmented control, left-aligned with the content.
3. Make the footer sticky to the page bottom (fixes the dead area once `h-screen` / `min-h-screen` works). Add an "About / architecture" link to a small diagram: React → FastAPI → FAISS + Gemini → BigQuery.
4. Accessibility: visible focus rings, a disabled style on Send, `aria-label`s on icon buttons, contrast ≥ 4.5:1 on secondary text.
5. Keep dark as the default and check light mode after the token mapping.

### Phase 5: Guard it
- Add a Playwright smoke test (or the existing test setup) that loads the page, clicks the first example chip, and asserts that SQL and at least one result row render. Run it after each deploy.
- Redeploy frontend and backend with `deploy_all.sh`, then re-run the smoke test against prod.
- Update `SQL_RAG/CLAUDE.md`: it says production runs from `feature/2-tab-ui` and that embeddings use OpenAI, but prod is on `main` and uses Gemini embeddings.

## Out of scope (YAGNI)
- Removing MUI entirely, migrating to TypeScript, or rebuilding the Playground / Data Overview tabs.
- Auth and multi-user dashboards.

## Order and effort
Phase 0 → 1 → 2 → 3 → 4 → 5, about 3–4 focused days in total. Phases 0–2 alone turn it from "broken" into "impressive", which is where most of the portfolio value is.
