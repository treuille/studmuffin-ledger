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
            st.subheader(f"Step {step.number}: {step.title}")
        elif is_future:
            st.subheader(f"Step {step.number}: {step.title}")
        else:
            st.subheader(f"Step {step.number}: {step.title}")

        # Step body
        if is_active:
            st.markdown(step.body)
            st.button(
                "Next step",
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
