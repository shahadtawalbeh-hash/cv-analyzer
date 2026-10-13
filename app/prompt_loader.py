from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

_BASE = Path(__file__).resolve().parent.parent
_BUNDLE = _BASE / "data" / "prompt_bundle.enc"


class PromptKeyMissing(RuntimeError):
    pass


def load_prompt_bundle() -> dict[str, Any]:
    key_raw = (os.environ.get("FITBOARD_PROMPT_KEY") or "").strip()
    if not key_raw:
        raise PromptKeyMissing(
            "Set FITBOARD_PROMPT_KEY to the Fernet key from scripts/seal_prompt.py.",
        )
    key = key_raw.encode("utf-8") if isinstance(key_raw, str) else key_raw
    if not _BUNDLE.is_file():
        raise PromptKeyMissing("Missing data/prompt_bundle.enc.")

    try:
        fernet = Fernet(key)
        plain_bytes = fernet.decrypt(_BUNDLE.read_bytes())
    except InvalidToken as exc:
        raise PromptKeyMissing("FITBOARD_PROMPT_KEY does not decrypt the bundle.") from exc

    try:
        data = json.loads(plain_bytes.decode("utf-8"))
    except json.JSONDecodeError:
        return {"system": plain_bytes.decode("utf-8"), "example_urls": []}

    if isinstance(data, str):
        return {"system": data, "example_urls": []}

    system = data.get("system")
    if not isinstance(system, str) or not system.strip():
        raise PromptKeyMissing("Bundle missing system prompt.")

    urls = data.get("example_urls") or []
    if not isinstance(urls, list):
        urls = []
    example_urls = [u for u in urls if isinstance(u, str)]

    return {"system": system.strip(), "example_urls": example_urls}


def load_system_prompt() -> str:
    return load_prompt_bundle()["system"]
