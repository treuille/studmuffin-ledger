# 📦 GIANT PROMPT — The Land Month-End Automation Skeleton

You are creating a small GitHub repo containing **four files**.
The goal is to present Ross with a **guided, linear walkthrough** of his month-end workflow, backed by a Streamlit app that renders a Markdown document step-by-step.

The Streamlit app is intentionally **low-state, deterministic, and no-op** for now.

---

## FILE 1 — `streamlit_app.py`

**Streamlit skeleton app (guided checklist, top-to-bottom, minimal state)**

```python
# streamlit_app.py
#
# The Land — Month-End Workflow (Skeleton)
#
# Design goals:
# - Single-page, top-to-bottom guided checklist
# - Very little session state (only active_step)
# - No-op actions for now
# - Content is driven entirely by workflow_steps.md
#
# Pages:
# - Workflow (guided steps)
# - Config / Debug (placeholder for secrets, logs, connections)

from pathlib import Path
from dataclasses import dataclass
import re
import streamlit as st

WORKFLOW_MD = Path(__file__).parent / "workflow_steps.md"


@dataclass
class Step:
    number: int
    title: str
    body: str


def load_markdown() -> str:
    if not WORKFLOW_MD.exists():
        return "# Missing workflow_steps.md\n\nPlease create the file."
    return WORKFLOW_MD.read_text(encoding="utf-8")


def parse_steps(md: str):
    """
    Expected format:

    # Title / intro

    ## Step 1: Title
    Body...

    ## Step 2: Title
    Body...
    """
    lines = md.splitlines()
    step_idxs = [i for i, l in enumerate(lines) if l.startswith("## Step")]

    intro = "\n".join(lines[: step_idxs[0]]).strip() if step_idxs else md

    steps = []
    for i, start in enumerate(step_idxs):
        end = step_idxs[i + 1] if i + 1 < len(step_idxs) else len(lines)
        header = lines[start]
        body = "\n".join(lines[start + 1 : end]).strip()

        m = re.match(r"## Step (\d+): (.+)", header)
        if not m:
            continue

        steps.append(
            Step(
                number=int(m.group(1)),
                title=m.group(2),
                body=body,
            )
        )

    return intro, steps


def workflow_page(intro, steps):
    st.title("The Land — Month-End Workflow")

    if "active_step" not in st.session_state:
        st.session_state.active_step = 1

    if intro:
        st.markdown(intro)
        st.divider()

    for step in steps:
        is_active = step.number == st.session_state.active_step
        is_future = step.number > st.session_state.active_step

        # Step header
        if is_active:
            st.subheader(f"➡️ Step {step.number}: {step.title}")
        elif is_future:
            st.subheader(f"🔒 Step {step.number}: {step.title}")
        else:
            st.subheader(f"✅ Step {step.number}: {step.title}")

        # Step body
        if is_active:
            st.markdown(step.body)
            st.button(
                "Next step →",
                key=f"next_{step.number}",
                on_click=lambda n=step.number: setattr(
                    st.session_state, "active_step", n + 1
                ),
            )
        elif not is_future:
            with st.expander("Show details"):
                st.markdown(step.body)
        else:
            st.markdown(
                "<span style='color: #999'>This step will unlock once you complete the previous step.</span>",
                unsafe_allow_html=True,
            )

        st.divider()


def config_page():
    st.title("Config / Debug")

    st.markdown(
        """
This page is intentionally minimal for now.

Later, this is where we will show:
- Which secrets are present
- Whether OAuth connections succeed
- Token expiry / refresh status
- Logs from each step
"""
    )

    st.subheader("Session state (debug)")
    st.json(
        {
            "active_step": st.session_state.get("active_step"),
        }
    )


def main():
    st.set_page_config(layout="wide")

    md = load_markdown()
    intro, steps = parse_steps(md)

    page = st.sidebar.radio("Page", ["Workflow", "Config / Debug"])

    if page == "Workflow":
        workflow_page(intro, steps)
    else:
        config_page()


if __name__ == "__main__":
    main()
```

---

## FILE 2 — `workflow_steps.md`

**Single source of truth for workflow + credentials**

```markdown
# The Land — Month-End Workflow

This document describes Ross’s current workflow and what we want to automate.
It is rendered step-by-step by the Streamlit app.

Assumption:
- Ross continues to manually sync QuickBooks bank feeds.
- Everything after that is deterministic and automatable.

---

## Step 1: Sync bank transactions in QuickBooks (manual)

### What happens
Ross logs into QuickBooks Online and refreshes the bank feed so the latest transactions appear.

### Why this is manual
QuickBooks bank-feed “for review” transactions are not reliably accessible via API.
We treat this as the human “commit” step.

### Automation options (later)
- Post-sync validation and exception flagging
- Full replacement of bank feeds using a bank aggregator (higher risk, not MVP)

### Credentials required
None (QuickBooks UI only)

---

## Step 2: (Optional) Review or fix transaction coding

### What happens
QuickBooks AI + rules usually categorize transactions correctly.
Ross fixes anything unusual.

### Future automation
- Pull posted transactions via API
- Flag anomalies (uncategorized, vendor mismatch, unusual accounts)
- Offer one-click fixes

### Credentials required
QuickBooks Online API (Intuit OAuth)

---

## Step 3: Split loan payment into principal and interest

### What happens today
Ross logs into the lender’s site every month to check the amortization breakdown.

### What we want
- Store the amortization schedule once
- Automatically compute monthly principal vs interest
- Create correct accounting guidance or entries

### Implementation modes
- Assist + match (preferred): create split entry, Ross matches bank feed
- Reporting-only: adjust exported data without touching books

### Credentials required
QuickBooks Online API

### Data required
One-time amortization schedule (CSV or loan parameters)

---

## Step 4: Pull month-end reports from QuickBooks

### Reports
- Profit & Loss
- Balance Sheet
- Statement of Cash Flows

### What we automate
- Fetch reports via QuickBooks Reports API
- Receive structured JSON
- Normalize to a standard internal format

### Credentials required
QuickBooks Online API (OAuth)

---

## Step 5: Update Google Sheets with latest month

### What happens today
Ross copy-pastes values from Excel exports into Google Sheets.

### What we automate
- Write values directly to Google Sheets via API
- Use batch updates for atomic writes

### Credentials required
Google Sheets API

Authentication options:
- Service account (recommended)
- OAuth as Ross

---

## Step 6: Refresh projections / formulas

### What happens today
Ross drags formulas forward to replace projections with actuals.

### Automation options
- Sheets API formula copy
- Sheet redesign to eliminate dragging entirely

### Credentials required
Google Sheets API

---

## Step 7: Review variances and decide on reforecasting

### What happens
Ross analyzes actuals vs projections and plans capital calls.

### What software can help with
- Variance summaries
- Cash runway alerts
- Scenario toggles

### Credentials required
None beyond previous steps

---

## Credential Summary

### QuickBooks (Intuit)
- Client ID
- Client Secret
- OAuth redirect URI
- Persistent token storage (refresh tokens rotate)

### Google Sheets
- Service account JSON key OR OAuth credentials
- Sheet ID and tab mappings

### Hosting
- Streamlit Community Cloud (GitHub-backed deployment)
- Secrets configured in hosting UI
```

---

## FILE 3 — `README.md`

**Minimal project readme**

````markdown
# The Land — Month-End Workflow (Skeleton)

This repository contains a **Streamlit skeleton app** that walks through
Ross’s month-end QuickBooks → Google Sheets workflow.

Nothing is automated yet.
This is a **discussion and alignment tool**.

## Files
- `streamlit_app.py` — Streamlit app (guided checklist)
- `workflow_steps.md` — workflow + credential requirements
- `AGENT_INSTRUCTIONS.md` — engineering plan

## Run locally
```bash
pip install streamlit
streamlit run streamlit_app.py
````

## Deployment

Intended for Streamlit Community Cloud, backed by a GitHub repo.
Secrets will be added later once APIs are wired.

````

---

## FILE 4 — `AGENT_INSTRUCTIONS.md`
**Engineering plan + Ross meeting plan**

```markdown
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
- Numbers match Ross’s manual workflow

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
````

