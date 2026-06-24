# Architecture

A deeper look at how Saarthi is put together and the decisions behind it. For
setup and feature overview see [README.md](README.md).

## Components

| Layer | Module | Responsibility |
|---|---|---|
| API | `app/api/` | HTTP surface: lead intake, WhatsApp webhook, dashboard, simulator |
| Domain | `app/domain/` | Enums and the **Lead lifecycle state machine** (pure, no I/O) |
| Services | `app/services/` | Use cases: intake/dedupe, lead ops, cadence, inbound, message status, dashboard reads |
| Assistant | `app/assistant/` | Agent loop, system prompt, tools, pre-send guardrail |
| Providers | `app/providers/` | Ports + adapters for WhatsApp and the LLM |
| Data | `app/db/` | SQLAlchemy models + Alembic migrations |
| Jobs | `app/celery_app.py`, `app/tasks.py` | Celery worker + beat for the cadence sweep |

Everything external is a **port with two adapters** — a real one and an offline
one (`MetaCloudProvider`/`MockWhatsAppProvider`, `ClaudeClient`/`FakeLLMClient`).
The core never imports a vendor SDK directly; it depends on the interface. That's
what makes the system clone-and-run and fully testable without credentials.

## The two main flows

### 1. Outbound cadence (scheduled, code-controlled)

```
lead created/imported ─▶ schedule_cadence() writes ScheduledTouch rows (Day 0/2/5/9)
Celery beat (every 60s) ─▶ process_due_touches():
    skip if within quiet hours (IST)
    for each PENDING touch due now:
        if lead opted out / no longer in nudge phase  → cancel
        else  render template (EN/HI/TE) → provider.send_template() → log Message → mark SENT
              NEW → CONTACTED on the first touch
```

It's **DB-driven**, not in-memory timers: each nudge is a `ScheduledTouch` row, so
the schedule survives restarts, is inspectable, and the worker is stateless. The
function is pure enough to unit-test by passing an explicit `now` and a recording
provider.

### 2. Inbound assistant (event-driven, model-controlled)

```
Meta webhook (POST) ─▶ verify HMAC signature ─▶ for each message:
    handle_inbound(): persist inbound, detect opt-out, STOP the cadence, mark ENGAGED
    respond_to_inbound():
        build context = recent transcript (+ open_question carried forward)
        run_agent(): Claude tool loop ─ search FAQ / request_test_drive /
                     record_feedback / escalate_to_sales / opt_out
        guardrail_check(reply): block prices/EMI/% ─▶ escalate + safe fallback
        provider.send_text(reply) → log Message
```

Delivery-status callbacks (`sent`/`delivered`/`read`/`failed`) update the stored
`Message` by `provider_message_id`. The same `respond_to_inbound` powers the
browser simulator — it just receives the inbound from a form instead of a webhook.

## Data model

`Location` · `StaffMember` · `Lead` · `Conversation`-less by design (the 24h
window is implicit: the assistant only free-form-replies to an inbound, which
opens the window) · `Message` (full in/out audit trail) · `ScheduledTouch`
(one row per cadence step) · `Feedback` · `Event` (append-only lifecycle log).

Enums are stored as `VARCHAR + CHECK` (`native_enum=False`) so migrations stay
simple and the schema is identical on Postgres (prod) and SQLite (tests).

### Lead lifecycle state machine

```
NEW → CONTACTED → ENGAGED → {TEST_DRIVE_REQUESTED, FEEDBACK_GIVEN} → HANDED_OFF → {WON, LOST}
  (+ side exits from most states: OPTED_OUT, UNREACHABLE)
```

Transitions are a guarded map in `app/domain/lead_state.py`. Services call
`set_status`/`try_set_status` (no-commit, used inside the agent loop) or
`change_status` (commits). Illegal transitions raise `InvalidTransition`; the
agent's tools use the `try_*` variant so a model mistake degrades to a no-op
rather than a crash.

## Key design decisions & trade-offs

- **Lean by intent.** Scoped to the signed pilot — no multi-agent coordinator, no
  vector DB. The approved content is ~20 Q&As, so the FAQ lives in the system
  prompt; a single tool-constrained agent is the right size for the problem.
- **Guardrail is deterministic, not a second model.** Prompts can be coaxed; a
  regex backstop on the *outgoing* text cannot. Cheap, and it's the thing that
  protects the dealer from an embarrassing wrong price.
- **Graceful degradation.** Any LLM/transport failure (including a missing API
  key) escalates the lead to a human with a safe reply, so the pilot never just
  drops a customer.
- **WhatsApp reality designed in.** First touch / re-engagement after 24h silence
  uses approved **templates**; free-form replies only happen inside the open 24h
  window (i.e., right after an inbound). Quiet hours, opt-out, and stop-on-reply
  are enforced at send time.
- **Ports over vendors.** Swapping Meta↔mock or Claude↔fake is a config change;
  tests and the offline demo use the mocks.

## Testing strategy

~56 tests against in-memory SQLite (shared via `StaticPool`) with the mock
providers — no DB or keys required. Coverage spans the pure units (phone
normalization, state machine, guardrail), the services (dedupe, cadence with a
controlled clock, inbound rules), the agent (each tool path + guardrail block via
a scripted `FakeLLMClient`), and the HTTP surface (webhook, dashboard, simulator).
CI (`.github/workflows/ci.yml`) runs ruff + mypy + pytest.

## Deferred (room left in the model)

CRM API connector (LeadSquared/Zoho/Tata DMS), workshop/service follow-up flows,
multi-tenant SaaS, and an optional LLM-as-judge eval + trace-observability harness.
