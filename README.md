# Saarthi — WhatsApp Lead Follow-up for Auto Dealerships

Walk-in customers at a car dealership leave their name and number, and then the
follow-up depends on whoever's free — so leads go cold before anyone notices.
**Saarthi** closes that gap: it imports walk-in leads, follows up automatically on
WhatsApp in the customer's language, answers their questions with a
tool-constrained AI assistant, books test drives, escalates anything sensitive to
a salesperson, and gives managers a live dashboard over the whole funnel.

Built for a real Tata dealership pilot (Hyderabad), and as a from-scratch,
production-shaped reference for an agentic LLM product.

> **Status:** all five milestones complete (M0–M5). Every milestone is a single,
> reviewable commit. ~56 tests, `ruff` + `mypy` clean.

---

## What it does

- **Lead intake** — import the dealership's daily Excel/CSV export; normalize
  phones to E.164 and **dedupe** (within the file and against existing leads).
- **Follow-up cadence** — a Celery-scheduled nudge sequence (Day 0/2/5/9) that
  respects **quiet hours**, **stops the moment a customer replies**, and honors
  **opt-out** — sending Meta-approved templates in **English, Hindi, or Telugu**.
- **AI assistant** — a single tool-constrained **Claude** agent answers from an
  approved FAQ, captures interest and visit feedback, takes test-drive requests,
  and **escalates** price/finance/availability questions to a human.
- **Safety guardrail** — a deterministic check blocks any reply containing a
  price/discount/EMI/percentage **before it can reach a customer**, replacing it
  with a safe message and a human handoff.
- **Manager dashboard** — funnel, headline metrics, the "needs human" queue, and
  per-lead conversation transcripts; plus a browser **WhatsApp simulator** to try
  the assistant with no real WhatsApp.

## Architecture

```
 Excel/CSV ─▶ intake + phone-dedupe ─▶  Lead (lifecycle state machine)
                                          │
                                          ▼
                        Celery beat ─▶ cadence engine ──▶ WhatsAppProvider ──▶ WhatsApp
                        (quiet hours, stop-on-reply,        (Meta Cloud │ Mock)
                         opt-out; approved templates)              ▲
                                                                   │ inbound webhook
                                          ┌────────────────────────┘
                                          ▼
                            intent (opt-out / reply) ──▶ tool-constrained assistant
                                                          (Claude │ Fake LLM)
                                          ┌───────────────┼───────────────┐
                                     search FAQ      request_test_drive   escalate_to_sales
                                   (system prompt)   record_feedback      opt_out
                                          │
                                   pre-send guardrail (no prices ever)
                                          │
                                          ▼
                              Dashboard · transcripts · needs-human queue
```

Vendors live behind **ports** (`app/providers/whatsapp`, `app/providers/llm`),
each with a real and an offline implementation — so the whole system runs and is
tested with **no credentials**, and the pilot swaps in real Meta/Claude via config.

See **[ARCHITECTURE.md](ARCHITECTURE.md)** for flows, the data model, and the
design decisions / trade-offs.

## Tech stack

FastAPI · PostgreSQL (SQLAlchemy 2 + Alembic) · Celery + Redis · Google Gemini
(`gemini-2.5-flash`, configurable; Claude also supported) · Jinja server-rendered
UI · Docker Compose · GitHub Actions (ruff + mypy + pytest).

## Quickstart

```bash
docker compose up --build        # api + worker(+beat) + postgres + redis
docker compose exec api alembic upgrade head
docker compose exec api make demo   # seed + run the full offline scenario
```

Then open:

- **Dashboard** — http://localhost:8000/dashboard
- **Simulator** — http://localhost:8000/simulator (chat with the assistant)

Local (no Docker) needs Postgres + Redis reachable:

```bash
python -m venv .venv && . .venv/Scripts/activate   # Windows; bin/activate on *nix
make install
make test
```

### Going live

Everything defaults to the **mock** WhatsApp provider and works offline. For the
real pilot, set in `.env` (see `.env.example`):

- `WHATSAPP_PROVIDER=meta` + `META_*` (token, phone number id, verify token, app secret)
- `GOOGLE_API_KEY` — the assistant uses `gemini-2.5-flash` by default. (Prefer
  Claude? Set `LLM_PROVIDER=claude` + `ANTHROPIC_API_KEY`.)

Without an LLM key the assistant degrades gracefully — every inbound is escalated
to a human with a safe reply, so nothing breaks.

## How the AI stays safe

- The assistant can only **act through tools**; it cannot change a lead's state
  any other way.
- The system prompt restricts it to an **approved FAQ** and forbids quoting
  prices/finance/availability — those must go through `escalate_to_sales`.
- A **deterministic pre-send guardrail** is the backstop: if a draft reply
  contains a currency figure, a lakh/crore amount, a percentage, or an EMI number,
  it is blocked and replaced with a safe handoff message before sending.

## Testing

```bash
make test     # pytest: phone, state machine, importer, cadence, webhook,
              # Meta provider, assistant (tools + guardrail), dashboard, simulator
make lint     # ruff
make typecheck  # mypy
```

Tests run against in-memory SQLite with the mock providers — no DB or keys needed.

## Project layout

```
app/
  api/         routers: leads, webhook, dashboard, simulator, health
  assistant/   agent loop, prompts, tools, pre-send guardrail
  domain/      enums + Lead lifecycle state machine
  providers/   whatsapp/{meta,mock}, llm/{gemini,claude,fake}
  services/    intake, leads, cadence, inbound, messages, dashboard, templates
  db/          models + Alembic migrations
  demo.py      offline end-to-end scenario
templates/     Jinja dashboard + simulator
seeds/         sample leads, approved FAQ, EN/HI/TE templates
tests/
```

## Roadmap

- **Done:** M0 scaffold · M1 intake+model · M2 cadence+WhatsApp · M3 assistant ·
  M4 dashboard · M5 demo+docs.
- **Deferred (named in the plan):** CRM API connector (LeadSquared/Zoho/Tata DMS),
  workshop/service flows, multi-tenant SaaS, and the optional eval/observability
  harness. The data model leaves room for each.
