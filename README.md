# The Land — Month-End Workflow (Skeleton)

This repository contains a **Streamlit skeleton app** that walks through
Ross's month-end QuickBooks → Google Sheets workflow.

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
```

## Deployment

Intended for Streamlit Community Cloud, backed by a GitHub repo.
Secrets will be added later once APIs are wired.
