# streamlit_app.py
#
# The Land — Month-End Workflow
#
# Design goals:
# - Multipage app with elegant navigation
# - Password-protected secrets (encrypted at rest, decrypted transiently)
# - Content is driven entirely by workflow_steps.md

from pathlib import Path
from dataclasses import dataclass
import json
import re
import streamlit as st

from secrets_manager import encrypt_secrets, try_decrypt_secrets

WORKFLOW_MD = Path(__file__).parent / "workflow_steps.md"

# Icons for each step (Material icons)
STEP_ICONS = {
    1: ":material/sync:",
    2: ":material/edit_note:",
    3: ":material/call_split:",
    4: ":material/summarize:",
    5: ":material/table_chart:",
    6: ":material/refresh:",
    7: ":material/analytics:",
}


@dataclass
class Step:
    number: int
    title: str
    body: str
    icon: str = ""


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
    step_idxs = [
        i for i, l in enumerate(lines) if re.match(r"## Step \d+:", l)
    ]

    intro = ""

    steps = []
    for i, start in enumerate(step_idxs):
        end = step_idxs[i + 1] if i + 1 < len(step_idxs) else len(lines)
        header = lines[start]
        body = "\n".join(lines[start + 1 : end]).strip()
        # Remove trailing horizontal rules from markdown
        body = body.rstrip("-").rstrip()

        m = re.match(r"## Step (\d+): (.+)", header)
        if not m:
            continue

        step_num = int(m.group(1))
        steps.append(
            Step(
                number=step_num,
                title=m.group(2),
                body=body,
                icon=STEP_ICONS.get(step_num, ":material/check_circle:"),
            )
        )

    return intro, steps


def get_encrypted_blob() -> str | None:
    """Get the encrypted secrets blob from st.secrets or return None."""
    try:
        return st.secrets.get("encrypted_secrets")
    except Exception:
        return None


def unlock_gate():
    """
    Password gate. Shows only a password field, nothing else.
    Returns True if unlocked, False if still locked.
    """
    blob = get_encrypted_blob()

    # No secrets configured - no gate needed
    if not blob:
        return True

    # Already unlocked this session
    if st.session_state.get("unlocked"):
        return True

    # Show only password field - no title, no sidebar, nothing
    st.text_input(
        "Password",
        type="password",
        key="unlock_password",
        on_change=_try_unlock,
    )

    if st.session_state.get("unlock_error"):
        st.error(st.session_state.unlock_error)

    return False


def _try_unlock():
    """Callback to attempt unlock."""
    blob = get_encrypted_blob()
    password = st.session_state.get("unlock_password", "")

    if not password:
        return

    secrets, error = try_decrypt_secrets(blob, password)
    if secrets is not None:
        st.session_state.unlocked = True
        st.session_state.secrets = secrets
        st.session_state.unlock_error = None
    else:
        st.session_state.unlock_error = error


def get_secrets() -> dict:
    """Get decrypted secrets from session state, or empty dict."""
    return st.session_state.get("secrets") or {}


def workflow_page():
    """Main workflow page with step-by-step checklist."""
    md = load_markdown()
    intro, steps = parse_steps(md)

    st.title("Month-End Workflow")

    if "active_step" not in st.session_state:
        st.session_state.active_step = 1

    if intro:
        st.markdown(intro)
        st.divider()

    for step in steps:
        is_active = step.number == st.session_state.active_step
        is_future = step.number > st.session_state.active_step
        is_completed = step.number < st.session_state.active_step

        # Choose icon based on state
        if is_completed:
            display_icon = ":material/check_circle:"
        elif is_future:
            display_icon = ":material/lock:"
        else:
            display_icon = step.icon

        with st.expander(
            f"{display_icon} Step {step.number}: {step.title}",
            expanded=is_active,
        ):
            if is_future:
                st.caption("This step will unlock once you complete the previous step.")
            else:
                st.markdown(step.body)
                if is_active:
                    st.button(
                        "Mark Complete & Continue",
                        key=f"next_{step.number}",
                        type="primary",
                        icon=":material/check:",
                        on_click=lambda n=step.number: setattr(
                            st.session_state, "active_step", n + 1
                        ),
                    )
                elif is_completed:
                    st.button(
                        "Return to this step",
                        key=f"return_{step.number}",
                        icon=":material/undo:",
                        on_click=lambda n=step.number: setattr(
                            st.session_state, "active_step", n
                        ),
                    )


def secrets_page():
    """Secrets management page."""
    st.title("Secrets")

    current = get_secrets()

    st.markdown("Edit secrets below, then encrypt with a password.")

    test_secret = st.text_input(
        "Test Secret",
        value=current.get("test_secret", ""),
        key="test_secret",
    )

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

    google_sa_default = ""
    if current.get("google_service_account"):
        google_sa_default = json.dumps(current["google_service_account"], indent=2)

    google_sa_input = st.text_area(
        "Google Service Account JSON",
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

            encrypted = encrypt_secrets(new_secrets, new_password)

            st.success("Secrets encrypted!")
            st.code(f'encrypted_secrets = "{encrypted}"', language="toml")


def config_page():
    """Config page displaying session state for debugging."""
    st.title("Config")
    st.markdown("Current session state variables:")
    st.json(dict(st.session_state))


def main():
    st.set_page_config(
        page_title="The Land — Month-End",
        page_icon=":material/landscape:",
        layout="wide",
    )

    # Gate: if secrets exist, require password first
    if not unlock_gate():
        st.stop()

    # Define pages with icons
    workflow = st.Page(
        workflow_page,
        title="Workflow",
        icon=":material/checklist:",
        default=True,
    )
    secrets = st.Page(
        secrets_page,
        title="Secrets",
        icon=":material/key:",
    )
    config = st.Page(
        config_page,
        title="Config",
        icon=":material/settings:",
    )

    # Navigation
    nav = st.navigation([workflow, secrets, config])
    nav.run()


if __name__ == "__main__":
    main()
