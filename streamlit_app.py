# streamlit_app.py
#
# The Land — Month-End Workflow
#
# Design goals:
# - Single-page, top-to-bottom guided checklist
# - Password-protected secrets (encrypted at rest, decrypted transiently)
# - Content is driven entirely by workflow_steps.md
#
# Pages:
# - Workflow (guided steps)
# - Config (secrets management)

from pathlib import Path
from dataclasses import dataclass
import json
import re
import streamlit as st

from secrets_manager import encrypt_secrets, try_decrypt_secrets

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

    Only numbered steps (## Step N: ...) are extracted.
    The intro/meta content at the top is ignored since we use st.title().
    """
    lines = md.splitlines()
    # Only match numbered steps like "## Step 1:", "## Step 2:", etc.
    step_idxs = [
        i for i, l in enumerate(lines) if re.match(r"## Step \d+:", l)
    ]

    # No intro - we use st.title() for the heading and skip meta content
    intro = ""

    steps = []
    for i, start in enumerate(step_idxs):
        # End at the next step header or end of file
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


def get_encrypted_blob() -> str | None:
    """Get the encrypted secrets blob from st.secrets or return None."""
    try:
        return st.secrets.get("encrypted_secrets")
    except Exception:
        return None


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

        st.subheader(f"Step {step.number}: {step.title}")

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
    st.title("Config")

    blob = get_encrypted_blob()
    has_secrets = bool(blob)

    st.markdown(
        """
Secrets are stored encrypted. Enter your password to decrypt, edit, and re-encrypt.
"""
    )

    # Initialize form state
    if "decrypted_secrets" not in st.session_state:
        st.session_state.decrypted_secrets = None
    if "decrypt_error" not in st.session_state:
        st.session_state.decrypt_error = None

    # Decrypt section (only if blob exists)
    if has_secrets and st.session_state.decrypted_secrets is None:
        st.subheader("Decrypt Existing Secrets")

        with st.form("decrypt_form"):
            decrypt_password = st.text_input("Current Password", type="password")
            if st.form_submit_button("Decrypt"):
                secrets, error = try_decrypt_secrets(blob, decrypt_password)
                if secrets is not None:
                    st.session_state.decrypted_secrets = secrets
                    st.session_state.decrypt_error = None
                    st.rerun()
                else:
                    st.session_state.decrypt_error = error

        if st.session_state.decrypt_error:
            st.error(st.session_state.decrypt_error)

        st.divider()
        st.markdown("**Or start fresh:**")

    # Edit section
    st.subheader("Edit Secrets")

    # Use decrypted secrets as defaults, or empty
    current = st.session_state.decrypted_secrets or {}

    # Debug/test secret (any string)
    test_secret = st.text_input(
        "Test Secret (any string)",
        value=current.get("test_secret", ""),
        key="test_secret",
        help="For testing encryption. Set to any value.",
    )

    st.divider()

    qbo_client_id = st.text_input(
        "QuickBooks Client ID",
        value=current.get("qbo_client_id", ""),
        key="qbo_client_id",
    )

    qbo_client_secret = st.text_input(
        "QuickBooks Client Secret",
        value=current.get("qbo_client_secret", ""),
        type="password",
        key="qbo_client_secret",
    )

    st.markdown("**Google Service Account JSON**")
    google_sa_default = ""
    if current.get("google_service_account"):
        google_sa_default = json.dumps(current["google_service_account"], indent=2)

    google_sa_input = st.text_area(
        "Paste the full JSON content",
        value=google_sa_default,
        height=150,
        key="google_sa",
    )

    st.divider()

    st.subheader("Encrypt with Password")

    new_password = st.text_input(
        "Password",
        type="password",
        key="new_password",
        help="This password will be required to decrypt secrets later",
    )
    confirm_password = st.text_input(
        "Confirm Password",
        type="password",
        key="confirm_password",
    )

    if st.button("Encrypt & Generate Blob", type="primary"):
        errors = []

        if not new_password:
            errors.append("Password is required.")
        elif new_password != confirm_password:
            errors.append("Passwords do not match.")
        elif len(new_password) < 8:
            errors.append("Password must be at least 8 characters.")

        # Parse Google SA JSON
        google_sa = None
        if google_sa_input.strip():
            try:
                google_sa = json.loads(google_sa_input)
            except json.JSONDecodeError as e:
                errors.append(f"Invalid Google SA JSON: {e}")

        if errors:
            for error in errors:
                st.error(error)
        else:
            # Build secrets dict
            new_secrets = {}
            if test_secret:
                new_secrets["test_secret"] = test_secret
            if qbo_client_id:
                new_secrets["qbo_client_id"] = qbo_client_id
            if qbo_client_secret:
                new_secrets["qbo_client_secret"] = qbo_client_secret
            if google_sa:
                new_secrets["google_service_account"] = google_sa

            # Encrypt (even if empty - user might want to clear secrets)
            encrypted = encrypt_secrets(new_secrets, new_password)

            st.success("Secrets encrypted!")

            st.markdown("**Copy this into your secrets.toml or Community Cloud secrets:**")
            st.code(f'encrypted_secrets = "{encrypted}"', language="toml")

            # Clear decrypted state
            st.session_state.decrypted_secrets = None

    # Debug section
    with st.expander("Debug Info"):
        st.json({
            "has_encrypted_blob": has_secrets,
            "secrets_decrypted": st.session_state.decrypted_secrets is not None,
            "active_step": st.session_state.get("active_step"),
        })


def main():
    st.set_page_config(page_title="The Land — Month-End", layout="wide")

    page = st.sidebar.radio("Page", ["Workflow", "Config"])

    md = load_markdown()
    intro, steps = parse_steps(md)

    if page == "Config":
        config_page()
    else:
        workflow_page(intro, steps)


if __name__ == "__main__":
    main()
