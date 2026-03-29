# TODO: Per-User BYOK (Bring Your Own Key) API Keys

Allow authenticated users to store their own `GOOGLE_API_KEY` so each person pays for their own Gemini usage rather than drawing from a shared key.

---

## Security model

Encrypting API keys at rest with Python's `cryptography` Fernet library protects against a **raw database dump** but does **not** protect against full server compromise (an attacker with access to the Railway environment gets both the encryption key and the data). For a small internal team app this tradeoff is generally acceptable.

If stronger isolation is needed, use Railway's native secret management or a dedicated secrets manager (e.g. HashiCorp Vault), but that is significant added complexity.

---

## Implementation plan

### 1. New environment variable

```
ENCRYPTION_KEY=<base64-urlsafe 32-byte key>
```

Generate once and store in Railway:

```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

### 2. New dependency

```
cryptography>=42.0.0
```

### 3. Database schema change

Add an `api_key` column to the existing `auth_sessions` table:

```sql
ALTER TABLE auth_sessions ADD COLUMN api_key TEXT;
```

Or handle it in the `CREATE TABLE` statement in `src/auth.py`:

```sql
CREATE TABLE IF NOT EXISTS auth_sessions (
    token      TEXT    PRIMARY KEY,
    email      TEXT    NOT NULL,
    name       TEXT    NOT NULL,
    picture    TEXT,
    api_key    TEXT,                -- Fernet-encrypted GOOGLE_API_KEY, nullable
    created_at INTEGER NOT NULL
)
```

### 4. Encryption helpers (`src/auth.py` or a new `src/crypto.py`)

```python
import os
from cryptography.fernet import Fernet

def _fernet() -> Fernet:
    key = os.environ.get("ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("ENCRYPTION_KEY env var is not set")
    return Fernet(key.encode())

def encrypt_api_key(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()

def decrypt_api_key(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()
```

### 5. Key entry UI (first login / settings)

After the user authenticates and before the main app renders, check whether they have a stored key. If not, show a one-time entry form:

```python
# In require_auth() or a new setup_user_key() helper called from app.py

if not user.get("api_key"):
    st.title("One more step")
    st.markdown("Enter your [Google AI Studio](https://aistudio.google.com/app/apikey) API key. It is encrypted and stored for your account only.")
    with st.form("byok_form"):
        raw_key = st.text_input("GOOGLE_API_KEY", type="password")
        if st.form_submit_button("Save key"):
            if raw_key.strip():
                encrypted = encrypt_api_key(raw_key.strip())
                _store_user_api_key(session_token, encrypted)
                st.session_state["_auth_user"]["api_key"] = raw_key.strip()
                st.rerun()
    st.stop()
```

### 6. Key retrieval for generation

In `app.py`, replace the env-var lookup with the user's stored key when available:

```python
# current
api_key_input = get_provider_api_key(provider)

# new
user = get_user()
api_key_input = (user or {}).get("api_key") or get_provider_api_key(provider)
```

### 7. Key rotation / removal UI

Add a small section in the sidebar (or a Settings tab) to let users view the last 4 characters of their stored key and replace or remove it:

```python
user = get_user()
if user and user.get("api_key"):
    st.caption(f"API key: ...{user['api_key'][-4:]}")
    if st.button("Replace key"):
        # clear stored key, trigger re-entry on next load
        _clear_user_api_key(session_token)
        st.session_state["_auth_user"].pop("api_key", None)
        st.rerun()
```

---

## Files to touch

| File | Change |
|---|---|
| `requirements.txt` | Add `cryptography>=42.0.0` |
| `.env.example` | Document `ENCRYPTION_KEY` |
| `src/auth.py` | Add `api_key` column, encrypt/decrypt helpers, key-entry gate |
| `app.py` | Prefer user's stored key over env-var key |

---

## Decision deferred

Skipped in favour of a **shared `GOOGLE_API_KEY`** env var for now. Revisit if:
- The team grows and per-user billing isolation is needed, or
- Usage costs become a concern with a shared key.
