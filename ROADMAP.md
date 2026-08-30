# Modernization Roadmap

Goal: evolve this prototype into a production-grade showcase of modern AI engineering — while keeping it genuinely useful as a booking tool. Ordered by signal-per-effort; each phase is a self-contained, demonstrable skill.

*Last reviewed: July 2026. Model/tooling recommendations date quickly — re-verify before starting each phase.*

## Status

| Phase | State |
|---|---|
| 0. CI + coverage reporting | ✅ Done (Codecov, badges; backend ~61%, frontend ~24%) |
| 1. Emergency model migration | ✅ Done (July 2026) |
| 2. Observability & tracing | 🔜 Next |
| 3. Eval harness | Planned |
| 4. Data-driven model migration | Planned — **hard deadline Oct 16, 2026** |
| 5. Database layer | Planned |
| 6. Streaming responses | Planned |
| 7. Agent rewrite (LangChain 1.0) | Planned |
| 8. MCP server | Planned |

### Known issues

- ~~Retry gap~~ fixed Aug 2026: parse now runs inside the attempt loop; the retry fires on any unusable output (empty or unparseable). Same pass fixed the telemetry audit findings: LLM API exceptions now fall back gracefully instead of 500ing, all-slots-invalid is scored as failure (`all_slots_invalid`), error details are recorded in span/trace outputs, taxonomy is open-world (`unexpected_error:<Type>`), and LLM internals are omitted from production API responses.

- **Feedback flow parse failure** (July 2026): submitting feedback triggers the round-2 agent path (`ai_service.py`), which sometimes returns unparseable output with `gemini-2.5-flash-lite`. Deliberately deferred — this is the first test case for the eval harness (phase 3), not a one-off patch.
- Python 3.9 is past EOL; Google client libraries emit deprecation warnings. Bump CI + venv to 3.12 (no code changes required).
- `react-scripts` (Create React App) is deprecated and unmaintained; frontend build tooling should eventually move to Vite (folded into phase 6).

---

## Phase 1: Emergency model migration ✅

**What happened:** Google shut down `gemini-2.0-flash` on June 1, 2026. The SDK's ~62s retry backoff exceeded Heroku's 30s router timeout, so the frontend surfaced misleading CORS errors. Two fixes shipped:

1. Model is now the `GEMINI_MODEL` setting (env-overridable), defaulting to `gemini-2.5-flash-lite` — chosen as the cheapest baseline ($0.10/$0.40 per M tokens, same price as the dead model) while eval infrastructure gets built. `max_retries=2` so dead models fail fast.
2. Parser hardened: 2.5-flash-lite prefixes JSON with prose, which the old code-fence stripping missed.

**Lesson that motivates everything below:** one model deprecation broke prod twice, in two different ways (dead model ID, changed output format), with zero advance warning from our side. Phases 2–4 make model changes observable, measurable, and routine.

## Phase 2: Observability & tracing (next)

Add [Langfuse](https://langfuse.com) tracing to the agent pipeline.

- **Why Langfuse over LangSmith:** MIT-licensed core, self-hostable, framework-neutral, OpenTelemetry-native, generous free cloud tier. Acquired by ClickHouse in Jan 2026 with the open-source license explicitly unchanged. LangSmith is tightly coupled to the LangChain platform and has no free self-host path.
- **Scope:** instrument `AIService.rank_slots` (traces, latency, token counts, cost per request); tag traces with round-1 vs round-2 (feedback) flow; capture the parse-failure cases currently invisible in logs.
- **Effort:** ~1 session. LangChain callback integration is a few lines.

**Skills demonstrated:** LLM observability, cost accounting, production debugging of nondeterministic systems.

## Phase 3: Eval harness

Build a golden dataset (~30 cases) of `(user_feedback, expected slot properties)` pairs — e.g. "next Tuesday morning" → all returned slots are Tuesday, before noon.

- Deterministic checks: slot legality (already enforced in code), date/time constraints matched, count in 5–10 range, valid JSON.
- LLM-as-judge for the `message` field (tone, relevance).
- Runner: pytest-based, tagged separately from unit tests (`pytest -m eval`); scheduled weekly in CI, not per-PR (cost control).
- Store datasets/runs in Langfuse (its eval primitives are the reason it was picked over standalone tools).
- **First test case:** the known feedback-flow parse failure.

**Skills demonstrated:** LLM evals — the highest-demand, lowest-supply AI engineering skill right now.

## Phase 4: Data-driven model migration — deadline Oct 16, 2026

`gemini-2.5-flash-lite` shuts down October 16, 2026. Migrate *through* the eval harness:

- Candidates (July 2026 pricing, per M tokens in/out): `gemini-3.1-flash-lite` (~$0.25/$1.50), DeepSeek V4 Flash ($0.14/$0.28), GPT-5 mini ($0.25/$2.00). Re-check pricing and availability at migration time.
- Use LangChain's `init_chat_model()` so provider swaps are config-only.
- Run all candidates against the eval suite; pick the winner on pass-rate, latency, and cost; document the comparison in the README.

**Skills demonstrated:** model selection with data instead of vibes; multi-provider architecture. At this app's volume (fractions of a cent per booking), quality and deprecation-runway matter more than price.

## Phase 5: Database layer

Replace `preferences.json` / `tokens.json` with Heroku Postgres + SQLModel + Alembic migrations.

- Current state is a real bug: Heroku's filesystem is ephemeral, so preference writes vanish on dyno restart; tokens survive only via a custom Heroku-API config-var hack.
- Also enables booking history, which the eval harness and future features can use.

**Skills demonstrated:** schema design, migrations, replacing prototype shortcuts with real persistence.

## Phase 6: Streaming responses + frontend modernization

- Convert `/booking/suggest-ai` to SSE (FastAPI `StreamingResponse` + LangChain `astream_events`); render progress/slots incrementally instead of blocking 5–10s.
- Fold in the frontend tooling migration: `react-scripts` → Vite (CRA is dead), and consider TypeScript at the same time since the build config is being touched anyway.

**Skills demonstrated:** async generators, event-driven UI, modern frontend tooling.

## Phase 7: Agent rewrite on LangChain 1.0

Current code uses `AgentExecutor` + `create_tool_calling_agent` — deprecated since LangChain 1.0 (Oct 2025), maintenance-only until December 2026.

- Migrate to `langchain.agents.create_agent`, which runs on the LangGraph runtime — structured output support built in (should eliminate the prose-prefixed-JSON parser hacks entirely).
- Model the two-round flow (round 1: pre-loaded slots; round 2: tool-driven fetch) as explicit graph state instead of prompt branching.
- Requires the Python 3.12 bump and dependency updates (`langchain>=1.0`).
- Eval harness (phase 3) verifies the rewrite changes nothing behaviorally — that's the payoff of doing evals first.

**Skills demonstrated:** agent architecture, framework migration under test coverage.

## Phase 7b: Eval iteration two (after migration)

- LLM-as-judge scorer for the `message` field (tone, relevance).
- Push runs to Langfuse experiments — native dashboards for cross-run/cross-model comparison instead of hand-built visualization.
- Weekly scheduled run of the evals workflow (on-demand `workflow_dispatch` exists now) as drift detection — Google has silently degraded models twice.
- Cost/token metrics per case (already queryable in Langfuse via the run's session id, recorded in each scorecard).

## Phase 7c: Public write-up

Once the eval-driven migration is complete: extend the README and write a standalone post — "one model deprecation broke prod twice, so I built observability, evals, and a measured migration." Scorecard diffs (baseline → post-migration → model bake-off) are the exhibits. Strong portfolio artifact.

## Phase 8: MCP server

Expose slot search + booking as a [Model Context Protocol](https://modelcontextprotocol.io) server, so any MCP client (Claude, IDEs, other agents) can book meetings directly.

- Reuses the existing service layer; the MCP server is a thin adapter.
- Needs auth design (API key at minimum) before exposing booking as a tool.

**Skills demonstrated:** MCP — the emerging standard for agent-tool interop; a strong conversation-starter.

---

## Deliberately not doing

- **Chasing coverage %** — evals over unit-test coverage; one Playwright E2E booking test would beat 20 component tests if frontend confidence is ever needed.
- **Microservices / k8s / Terraform** — wrong scale for a single-tenant app; reads as résumé-driven engineering.
- **Framework swaps** (Next.js etc.) — depth over breadth.
