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
import time
import pandas as pd
import streamlit as st

from secrets_manager import encrypt_secrets, try_decrypt_secrets

WORKFLOW_MD = Path(__file__).parent / "workflow_steps.md"

# Security settings
SESSION_TIMEOUT_SECONDS = 30 * 60  # 30 minutes of inactivity
LOCKOUT_DELAYS = [0, 0, 5, 15, 30, 60]  # Escalating delays after failed attempts

# Icons for each step (Material icons)
STEP_ICONS = {
    1: ":material/sync:",
    2: ":material/upload_file:",
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


def _check_session_timeout() -> bool:
    """Check if session has timed out. Returns True if still valid."""
    last_activity = st.session_state.get("last_activity")
    if last_activity is None:
        return True  # No activity yet, consider valid

    elapsed = time.time() - last_activity
    if elapsed > SESSION_TIMEOUT_SECONDS:
        # Session expired - clear secrets
        st.session_state.pop("secrets", None)
        st.session_state.pop("last_activity", None)
        return False
    return True


def _update_activity():
    """Update last activity timestamp."""
    st.session_state.last_activity = time.time()


def _get_lockout_remaining() -> float:
    """Get seconds remaining in lockout, or 0 if not locked out."""
    lockout_until = st.session_state.get("lockout_until", 0)
    remaining = lockout_until - time.time()
    return max(0, remaining)


def _record_failed_attempt():
    """Record a failed login attempt and set lockout if needed."""
    attempts = st.session_state.get("failed_attempts", 0) + 1
    st.session_state.failed_attempts = attempts

    # Determine lockout duration based on attempt count
    delay_index = min(attempts, len(LOCKOUT_DELAYS) - 1)
    delay = LOCKOUT_DELAYS[delay_index]

    if delay > 0:
        st.session_state.lockout_until = time.time() + delay


def _clear_failed_attempts():
    """Clear failed attempt tracking after successful login."""
    st.session_state.pop("failed_attempts", None)
    st.session_state.pop("lockout_until", None)


def unlock_gate():
    """
    Password gate. Shows only a password field, nothing else.
    Returns True if unlocked, False if still locked.

    Security features:
    - Password is never stored in session state
    - Unlocked state = presence of decrypted secrets
    - Session timeout after inactivity
    - Rate limiting with escalating delays
    """
    blob = get_encrypted_blob()

    # No secrets configured - no gate needed
    if not blob:
        return True

    # Check session timeout
    if not _check_session_timeout():
        st.warning("Session expired due to inactivity. Please log in again.")

    # Already unlocked (secrets exist in session state)
    if st.session_state.get("secrets"):
        _update_activity()
        return True

    # Check if locked out
    lockout_remaining = _get_lockout_remaining()
    if lockout_remaining > 0:
        st.error(f"Too many failed attempts. Please wait {int(lockout_remaining)} seconds.")
        st.stop()

    # Use a form so password is submitted but not stored in session state
    with st.form("unlock_form", clear_on_submit=True):
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Unlock")

        if submitted and password:
            secrets, error = try_decrypt_secrets(blob, password)
            if secrets is not None:
                st.session_state.secrets = secrets
                _update_activity()
                _clear_failed_attempts()
                st.rerun()
            else:
                _record_failed_attempt()
                lockout = _get_lockout_remaining()
                if lockout > 0:
                    st.error(f"{error} Please wait {int(lockout)} seconds before trying again.")
                else:
                    st.error(error)

    return False


def get_secrets() -> dict:
    """Get decrypted secrets from session state, or empty dict."""
    return st.session_state.get("secrets") or {}


REPORT_TYPES = [
    ("balance_sheet", "Balance Sheet"),
    ("cash_flows", "Cash Flows"),
    ("profit_and_loss", "Profit and Loss"),
]


def _all_reports_uploaded() -> bool:
    """Return True if all three QuickBooks report CSVs are in session state."""
    return all(f"df_{key}" in st.session_state for key, _ in REPORT_TYPES)


def _read_upload(uploaded) -> pd.DataFrame:
    """Read a CSV or Excel upload into a DataFrame."""
    name = uploaded.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded)
    return pd.read_excel(uploaded)


def render_step_2_uploads():
    """Show file uploaders side-by-side, previews stacked below."""
    cols = st.columns(len(REPORT_TYPES))
    for col, (key, label) in zip(cols, REPORT_TYPES):
        with col:
            uploaded = st.file_uploader(
                f"LV Capital Holdings {label}",
                type=["csv", "xls", "xlsx"],
                key=f"upload_{key}",
            )
            if uploaded is not None:
                try:
                    df = _read_upload(uploaded)
                    st.session_state[f"df_{key}"] = df
                except Exception as e:
                    st.error(f"Could not read {label} file: {e}")

    for key, label in REPORT_TYPES:
        if f"df_{key}" in st.session_state:
            st.subheader(label)
            st.dataframe(st.session_state[f"df_{key}"], use_container_width=True)


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
                if is_active and step.number == 2:
                    render_step_2_uploads()
                if is_active:
                    disabled = (
                        step.number == 2 and not _all_reports_uploaded()
                    )
                    st.button(
                        "Mark Complete & Continue",
                        key=f"next_{step.number}",
                        type="primary",
                        icon=":material/check:",
                        disabled=disabled,
                        on_click=lambda n=step.number: setattr(
                            st.session_state, "active_step", n + 1
                        ),
                    )
                    if disabled:
                        st.caption(
                            "Upload all three reports to continue."
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

    # Celebration when all steps are done
    if steps and st.session_state.active_step > len(steps):
        st.balloons()
        st.success("Congrats, you did it! Go Muffin! 🧁")


def secrets_page():
    """Secrets management page."""
    st.title("Secrets")

    current = get_secrets()

    st.markdown("Edit secrets below, then encrypt with a password.")

    # All secret fields are hidden by default for security
    test_secret = st.text_input(
        "Test Secret",
        value=current.get("test_secret", ""),
        type="password",
        key="test_secret",
    )

    qbo_client_id = st.text_input(
        "QuickBooks Client ID",
        value=current.get("qbo_client_id", ""),
        type="password",
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

    # Note: text_area doesn't support type="password", but the value is still
    # pre-populated from session state (not visible in page source until rendered)
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

    # Filter out sensitive data from display
    SENSITIVE_KEYS = {"secrets", "unlock_password"}
    safe_state = {}
    for key, value in st.session_state.items():
        if key in SENSITIVE_KEYS:
            safe_state[key] = "[REDACTED]"
        else:
            safe_state[key] = value

    st.json(safe_state)


def main():
    st.set_page_config(
        page_title="The Land — Month-End",
        page_icon="stud-muffin.jpg",
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
