# The Land — Month-End Workflow

This document describes your current workflow and what we want to automate.
It is rendered step-by-step by the Streamlit app.

Assumption:
- You continue to manually sync QuickBooks bank feeds.
- Everything after that is deterministic and automatable.

---

## Step 1: Sync bank transactions in QuickBooks (manual)

### What happens
Log into QuickBooks Online and refresh the bank feed so the latest transactions appear.

### Why this is manual
QuickBooks bank-feed "for review" transactions are not reliably accessible via API.
We treat this as the human "commit" step.

### Automation options (later)
- Post-sync validation and exception flagging
- Full replacement of bank feeds using a bank aggregator (higher risk, not MVP)

### Credentials required
None (QuickBooks UI only)

---

## Step 2: Upload QuickBooks reports

### What happens
Export and upload three QuickBooks report CSVs (in any order):

1. **LV Capital Holdings Balance Sheet**
2. **LV Capital Holdings Cash Flows**
3. **LV Capital Holdings Profit and Loss**

Each file is previewed inline after upload.

### Why CSVs instead of API
QuickBooks' transaction categorization AI is good enough that we don't need
to automate review/fix of transaction coding. Exporting these three reports
manually is fast and avoids OAuth complexity for MVP.

### Credentials required
None (manual CSV export from QuickBooks UI)

---

## Step 3: Split loan payment into principal and interest

### What happens today
Log into the lender's site every month to check the amortization breakdown.

### What we want
- Store the amortization schedule once
- Automatically compute monthly principal vs interest
- Create correct accounting guidance or entries

### Implementation modes
- Assist + match (preferred): create split entry, you match bank feed
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
Copy-paste values from Excel exports into Google Sheets.

### What we automate
- Write values directly to Google Sheets via API
- Use batch updates for atomic writes

### Credentials required
Google Sheets API

Authentication options:
- Service account (recommended)
- User OAuth

---

## Step 6: Refresh projections / formulas

### What happens today
Drag formulas forward to replace projections with actuals.

### Automation options
- Sheets API formula copy
- Sheet redesign to eliminate dragging entirely

### Credentials required
Google Sheets API

---

## Step 7: Review variances and decide on reforecasting

### What happens
Analyze actuals vs projections and plan capital calls.

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
