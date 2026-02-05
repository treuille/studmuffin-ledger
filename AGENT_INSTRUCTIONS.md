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
- Encrypted secrets management
- No API automation yet

### Phase 1: Reports → Sheets (highest ROI)
Implement:
- QuickBooks OAuth via `streamlit-oauth` component
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

## Authentication Architecture

### Threat model
- We don't trust Streamlit Community Cloud with plaintext secrets
- Secrets should only exist decrypted in memory
- Password required to unlock the app

### What we store (encrypted blob)

Static secrets only — no rotating tokens:

| Secret | Source | Rotates? |
|--------|--------|----------|
| QBO Client ID | Intuit Developer Portal | No |
| QBO Client Secret | Intuit Developer Portal | No |
| Google Service Account JSON | Google Cloud Console | No |

### What we DON'T store

OAuth tokens — obtained fresh each session:

| Token | How obtained | Lifetime |
|-------|--------------|----------|
| QBO Access Token | `streamlit-oauth` popup | 1 hour |
| QBO Refresh Token | Not persisted | N/A |

### Why this works for monthly workflow

1. Ross opens app → enters password → decrypts static secrets
2. Ross clicks "Connect to QuickBooks" → OAuth popup → authenticates
3. Access token stored in `st.session_state` (ephemeral)
4. Ross completes all QBO work within 1 hour
5. App sleeps → tokens gone → no problem, it's monthly

### Encrypted blob design

```
secrets.toml (or Community Cloud secrets):
┌─────────────────────────────────────────────────┐
│ encrypted_secrets = "base64-encoded-blob..."    │
└─────────────────────────────────────────────────┘
                    ↓
            [password prompt]
                    ↓
            scrypt KDF → AES key
                    ↓
            Fernet decrypt
                    ↓
┌─────────────────────────────────────────────────┐
│ {                                               │
│   "qbo_client_id": "...",                       │
│   "qbo_client_secret": "...",                   │
│   "google_service_account": { ... }             │
│ }                                               │
└─────────────────────────────────────────────────┘
```

### Crypto choices
- Key derivation: scrypt (memory-hard, resists GPU attacks)
- Encryption: Fernet (AES-128-CBC + HMAC-SHA256)
- Encoding: base64
- Library: `cryptography` (audited, battle-tested)

### UX flow

```
App start (no secrets configured):
┌─────────────────────────────────────────┐
│  Workflow page loads normally           │
│  Config page lets you add secrets       │
└─────────────────────────────────────────┘

Config page:
┌─────────────────────────────────────────┐
│  [If blob exists]                       │
│  Current Password: [••••••••]           │
│  [Decrypt] → fills form with values     │
│                                         │
│  ─────────────────────────────────────  │
│                                         │
│  QBO Client ID:     [          ]        │
│  QBO Client Secret: [••••••••]          │
│  Google SA JSON:    [textarea]          │
│                                         │
│  Password:          [••••••••]          │
│  Confirm Password:  [••••••••]          │
│                                         │
│  [Encrypt & Generate Blob]              │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │ encrypted_secrets = "gAAA..."  │    │
│  │                                 │    │
│  │ Copy to secrets.toml or        │    │
│  │ Community Cloud secrets UI     │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

Secrets are only decrypted transiently when needed — never persisted in session state.

---

## QuickBooks OAuth (Phase 1)

### Component
`streamlit-oauth` — https://github.com/dnplus/streamlit-oauth

### Redirect URI
```
https://studmuf-ledger.streamlit.app/component/streamlit_oauth.authorize_button
```

### Scopes needed
```
com.intuit.quickbooks.accounting
```

### Flow
1. Ross clicks "Connect to QuickBooks"
2. Popup opens → Intuit login
3. Authorization code returned to app
4. App exchanges code for access token (using Client ID + Secret)
5. Access token stored in `st.session_state`
6. App calls QBO APIs until token expires or session ends

---

## Google Sheets (Phase 1)

### Auth model
Service account (recommended over OAuth)

### Why service account?
- No refresh token rotation
- No user interaction required
- JSON key is static
- Just share the target spreadsheet with the service account email

### Setup
1. Create service account in Google Cloud Console
2. Download JSON key
3. Share target spreadsheet with service account email
4. Store JSON in encrypted blob

---

## Ross meeting agenda
1. Confirm workflow boundaries
2. Inspect Google Sheet structure
3. Get QBO Client ID + Secret from Intuit Developer Portal
4. Create Google service account and share spreadsheet
5. Test encrypted secrets + OAuth flow
6. Define Phase-1 success criteria

---

## Success metric
Ross can finish month-end in minutes instead of hours,
with confidence that the numbers are correct.
