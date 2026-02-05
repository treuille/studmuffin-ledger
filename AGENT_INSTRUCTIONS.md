# Agent Instructions — The Land Month-End Automation

## Objective
Turn the skeleton Streamlit app into a deterministic month-end automation tool,
while keeping human checkpoints where appropriate.

Avoid brittle agentic behavior.

---

## Design principles
- Linear, top-to-bottom flow
- Completion derived from outputs, not flags
- Explicit user actions for anything that mutates data
- Logs and previews everywhere

---

## Phase plan

### Phase 0 (current)
- Guided checklist UI
- Markdown-driven steps
- No automation

### Phase 1: Reports → Sheets (highest ROI)
Implement:
- Intuit OAuth
- Persistent token storage
- Pull P&L / BS / Cash Flow via Reports API
- Write latest month into Google Sheets

Acceptance criteria:
- One click updates Sheets
- Numbers match Ross's manual workflow

### Phase 2: Loan split automation
Implement:
- Loan schedule storage
- Monthly principal/interest computation
- QBO entry or matching helper

### Phase 3: Optional coding QA
Implement:
- Transaction scans
- Exception queue
- One-click fixes

---

## Non-goals
- No headless browser automation
- No fully automatic bank ingestion (unless explicitly requested)

---

## Secrets & storage
- OAuth tokens must be persisted and rotated
- Use a real database (Supabase, Neon, etc.)
- Never store tokens only in Streamlit session state

---

## Ross meeting agenda
1. Confirm workflow boundaries
2. Inspect Google Sheet structure
3. Decide Google auth model
4. Decide loan accounting approach
5. Define Phase-1 success

---

## Success metric
Ross can finish month-end in minutes instead of hours,
with confidence that the numbers are correct.
