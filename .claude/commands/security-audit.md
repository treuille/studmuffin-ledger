# Security Audit Command

You are a hardnosed security expert conducting a thorough security audit of this application's secrets management. Your job is to be critical, skeptical, and identify every possible flaw, weakness, or concern.

## Audit Scope

Focus on these core security claims:
1. **Password is never stored** - Verify the password is only used transiently for key derivation
2. **Secrets are never stored at rest in plaintext** - Verify encryption at rest
3. **General security posture** - Identify any design flaws, vulnerabilities, or weaknesses

## Required Analysis

Read and analyze these files thoroughly:
- `streamlit_app.py` - Main application, unlock gate, session state handling
- `secrets_manager.py` - Encryption/decryption implementation

## Evaluation Criteria (Be Ruthless)

### Cryptographic Analysis
- Is the key derivation function appropriate? (scrypt parameters)
- Is the encryption scheme secure? (Fernet = AES-128-CBC + HMAC-SHA256)
- Are there any crypto anti-patterns?
- Is the salt generation secure?
- Are there timing attacks possible?

### Password Security
- Is the password ever logged, stored, or persisted?
- Could the password leak through error messages?
- Is the password properly cleared from memory?
- Are there brute-force protections?

### Secrets Handling
- Where do decrypted secrets exist? For how long?
- Could secrets leak through session state serialization?
- Are secrets exposed in debug pages?
- Could secrets appear in logs, stack traces, or error messages?

### Application Security
- CSRF/XSRF vulnerabilities in the unlock flow
- Session fixation or hijacking risks
- Information disclosure through error messages
- Rate limiting on password attempts

### Deployment Concerns
- How are encrypted secrets stored? (st.secrets)
- Trust model for Streamlit Community Cloud
- Key rotation strategy
- Incident response (what if blob is compromised?)

## Output Format

Provide your findings in this structure:

### Executive Summary
A brief overall security assessment (PASS/FAIL/CONDITIONAL)

### Critical Issues
Issues that must be fixed immediately (if any)

### High-Severity Concerns
Significant weaknesses that should be addressed

### Medium-Severity Concerns
Design decisions that could be improved

### Low-Severity / Informational
Minor nitpicks, recommendations, hardening suggestions

### Security Claims Verification
For each core claim, explicitly state:
- VERIFIED: Evidence supports the claim
- PARTIALLY VERIFIED: Claim is mostly true but with caveats
- NOT VERIFIED: Evidence contradicts or doesn't support the claim

Be specific. Cite line numbers. Don't sugarcoat. If something is bad, say so clearly.
