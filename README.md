# Saarthi — WhatsApp Lead Follow-up for Auto Dealerships

Walk-in leads at a car dealership get captured and then forgotten. **Saarthi**
automatically re-engages them on WhatsApp: it follows up after a showroom visit,
answers approved questions, captures interest and feedback, takes test-drive
requests, and hands hot leads to a salesperson — while a manager watches every
lead's status on a dashboard.

> Status: **work in progress**, built milestone by milestone. This commit is
> **M0 — scaffold** (runnable skeleton, no business logic yet).

## Architecture (target)

```
Excel/Sheet ─▶ import+dedupe ─▶ Lead (state machine) ─▶ Celery nudge cadence ─▶ WhatsApp
                                      ▲                                            │ (templates / 24h window)
                                      └────────── inbound webhook ◀────────────────┘
                                                       │
                                       single tool-constrained assistant
                                       (FAQ + capture interest/feedback/test-drive,
                                        escalate price/availability to a human)
                                                       │
                                              Dashboard + handoff queue
```

WhatsApp lives behind a provider port (`app/providers/whatsapp`) with a **mock**
implementation, so the whole system runs offline for demos and tests; the **Meta
Cloud API** provider is wired in M2.

## Quickstart

```bash
docker compose up --build     # api on http://localhost:8000  (mock provider, no creds)
curl http://localhost:8000/health
```

Local dev without Docker:

```bash
python -m venv .venv && . .venv/Scripts/activate   # Windows; use bin/activate on *nix
make install
make test
make run        # needs Postgres + Redis reachable (or just use `make up`)
```

## Tech stack

FastAPI · PostgreSQL (SQLAlchemy 2 + Alembic) · Celery + Redis · Anthropic Claude
(assistant, added in M3) · Docker. See `app/config.py` for settings.

## Layout

```
app/
  api/          # routers (health now; webhook/dashboard later)
  config.py     # settings (pydantic-settings)
  db/           # Base, session, Alembic migrations
  providers/    # whatsapp/{base,mock,meta}, llm/ (later)
  celery_app.py # Celery app + tasks (cadence in M2)
tests/          # pytest
```

## Roadmap

- **M0 — Scaffold** ✅ (this commit)
- M1 — Sheet import + dedupe, Lead model + lifecycle, seed FAQ/templates
- M2 — Cadence engine + Meta Cloud API provider + webhook
- M3 — Inbound assistant (FAQ, tools, pre-send guardrail)
- M4 — Dashboard + handoff queue
- M5 — Demo simulator + docs
