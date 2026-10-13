from __future__ import annotations

import base64
import os

from starlette.requests import Request

_SALT = b"cvfb-v1-k"
_BLOB = (
    "EB1LEl8ZWwAlUkAPCWE0UGANITcvKGMQZn8BGlspCUMTR3sEKyJVEGAleRxbOQ8/K2oxU24/C0YNEhVOAUs5"
    "WjolNHckZUASNwYuT2Yxa0kyBiJVIEEUWmshUSYTIF8bfXkDNiwkD1cbfBodKEcQUUYQXXkeJDwOUkMGYh0h"
    "Ah8qMhQ1RBUkBh43Fms6a2wYKgEBU0Y9e2knCEUlDEAOSHQJBDc="
)


def get_embedded_openai_key() -> str | None:
    if os.environ.get("FITBOARD_DISABLE_EMBEDDED_OPENAI_KEY", "").strip() in (
        "1",
        "true",
        "yes",
    ):
        return None
    try:
        raw = base64.b64decode(_BLOB, validate=True)
    except (ValueError, TypeError):
        return None
    s = (_SALT * ((len(raw) // len(_SALT)) + 1))[: len(raw)]
    out = bytes(a ^ b for a, b in zip(raw, s))
    if not out.startswith(b"sk-"):
        return None
    try:
        return out.decode("ascii")
    except UnicodeDecodeError:
        return None


def resolve_openai_api_key(request: Request) -> str | None:
    env_k = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if env_k:
        return env_k
    session_k = request.session.get("openai_api_key")
    if isinstance(session_k, str) and session_k.strip():
        return session_k.strip()
    return get_embedded_openai_key()
