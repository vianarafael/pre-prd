---
format: Technical Design Document
author: Your Name
product: PRD++ (pre_prod)
audience: Solo builders & small teams shipping MVPs with Cursor
---

# PRD++ (pre_prod)

## Product Overview

### Purpose

Provide a single-page app where builders draft a strong-enough spec and instantly materialize five artifacts:

1. **Script** (PRD/TDD in Markdown + YAML front-matter)
2. **Rules** (.cursor/rules packs)
3. **Scenes** (Epics JSON)
4. **Shots** (Tickets JSON)

The goal is to **guide** Cursor—not replace thinking—so codegen follows explicit acceptance criteria and house rules.

### Target Audience

- Indie devs, tech leads, early teams using Cursor.
- Pain points: blank-page PRDs, ad-hoc rules, drift between stories ↔ tickets, slow scaffolding.

### Expected Outcomes (KPIs)

- Time-to-first-artifact (TTFA) ≤ **5 minutes**.
- PRD lint passes with **≥ 90%** sections “non-empty + measurable”.
- “Export all” produces **4 files** + tree every time.
- Epics ↔ Features & Tickets ↔ AC stay in sync (≤ **1** pending sync at a time).

**What**: Single-page app to draft a strong spec and emit 5 artifacts  
**For**: Indie devs & small teams using Cursor  
**Win**: Clear PRD + rules → better codegen, zero SPA overhead

**MVP scope**

- Script (PRD/TDD editor)
- Rules packs (Core, Opinionated; Strict later)
- Scenes (Epics) editor
- Shots (Tickets) editor
- Exporter (PRD.md, instructions.mdc, epics.json, tickets.json)

**Stack**

- Python 3.12, FastAPI, Jinja2, HTMX, DaisyUI, SQLite

**Non-negotiables**

- Server-rendered HTMX
- No raw SQL in handlers (repo layer only)
- Tests from AC first; ruff + mypy on CI

**KPIs**

- Time-to-first-artifact ≤ 5 min
- PRD lint sections “filled & measurable” ≥ 90%
- p95 route latency < 200 ms (@ 50 rps synthetic)

**Out of scope (MVP)**

- Auth/multi-user, Cursor API calls, cloud storage

---

## Design Details

### Architectural Overview

- **Stack:** FastAPI + HTMX + DaisyUI + SQLite.
- **Pattern:** Server-rendered pages; HTMX for partial updates; zero SPA framework.
- **Modules:**
  - `routes/` (view + JSON export),
  - `services/` (linting, packing, sync),
  - `repo/` (SQLite persistence, row_factory=sqlite3.Row),
  - `templates/` (DaisyUI components).
- **Sync engine:** Keeps Script↔Scenes↔Shots mappings consistent; shows “Sync pending” when divergence detected.

### Data Structures & Algorithms

- **Epic:** `{id, title, goal, success_metric, risk, status}`
- **Ticket:** `{id, epic_id, title, acceptance_criteria[], priority, effort, status}`
- **RulesPack:** `{core:bool, opinionated:bool, strict:bool, body:string}`
- Lightweight lint passes:
  - AC lint: starts with verb, includes a negative path, no duplicates.
  - PRD lint: required sections present; KPIs numeric.

### System Interfaces

- `GET /` — main page (wizard left, preview right)
- `POST /export` — returns `artifacts.json` (PRD.md, rules, epics.json, tickets.json)
- `POST /rules/pack` — toggles Core/Opinionated/Strict -> Markdown
- `POST /sync` — applies Story/AC ↔ Ticket changes (returns diffs)
- **No direct Cursor API calls** in MVP; Cursor consumes files in repo.

### User Interfaces

- **Left:** wizard tabs (Script, Rules, Scenes, Shots).
- **Right:** live preview tabs (PRD.md, Rules, epics.json, tickets.json, Scaffold).
- **Affordances:** copy/download buttons, “Sync pending” badge, readiness bar, lint hints.

### Hardware Interfaces

- None.

---

## Testing Plan

### Test Strategies

- Unit (services: lint, pack, sync), integration (routes), e2e happy paths + error paths.
- Golden-file tests for `PRD.md`, `instructions.mdc`, `epics.json`, `tickets.json`.

### Testing Tools

- `pytest`, `mypy`, `ruff`; `httpx.TestClient` for FastAPI; optional Playwright for e2e.

### Environments

- Dev: SQLite (`app.db`); Staging/Prod: SQLite + daily backup.

### Test Cases (samples)

- Export with all packs ON contains three concatenated rule sections.
- Creating tickets from a Story yields T-cards whose AC mirror the story; editing a T-card triggers “Sync pending”.
- Lint flags AC without a negative case; passes after adding one.

### Reporting & Metrics

- CI summary: test counts, coverage ≥ 80%, lint/mypy status; p95 route latency.

---

## Deployment Plan

### Environment

- FastAPI (uvicorn). SQLite persisted to volume. `.env` for secrets.

### Tools

- GitHub Actions: ruff + mypy + pytest; build & push container; deploy to your platform of choice.

### Steps

1. Seed default Rules packs.
2. Health check `/` and `/export` (dry run).
3. Enable backups of SQLite file.

### Post-Deployment Verification

- Generate sample artifacts; compare to goldens; check logs for HTMX errors.

### Continuous Deployment

- On `main` green CI, auto-deploy; keep a one-step rollback to prior image.

---

## Constraints / Non-Negotiables

- Python **3.12**; server-rendered HTMX; **no raw SQL** in handlers (repo layer only).
- Secrets from `.env`; commit `.env.example`; never commit real secrets.
- Performance: p95 **< 200ms** on `/` and `/export` at 50 RPS synthetic.

## Out of Scope (MVP)

- OAuth, multi-user accounts, real Cursor API integration, cloud storage.
