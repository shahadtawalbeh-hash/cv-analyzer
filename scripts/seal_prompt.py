from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cryptography.fernet import Fernet

SOURCE = ROOT / "prompt_seal_source.json"


def main() -> None:
    if not SOURCE.is_file():
        raise SystemExit(
            "Create prompt_seal_source.json at the project root with "
            '"system" (string) and "example_urls" (string array). '
            "Keep that file off shared zips.",
        )
    raw = json.loads(SOURCE.read_text(encoding="utf-8"))
    system = raw.get("system")
    urls = raw.get("example_urls") or []
    if not isinstance(system, str) or not system.strip():
        raise SystemExit('prompt_seal_source.json needs a non-empty "system" string.')
    if not isinstance(urls, list):
        raise SystemExit('"example_urls" must be an array of strings.')
    example_urls = [u for u in urls if isinstance(u, str)]

    data_dir = ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    key = Fernet.generate_key()
    blob = json.dumps(
        {"system": system.strip(), "example_urls": example_urls},
        ensure_ascii=False,
    ).encode("utf-8")
    out = data_dir / "prompt_bundle.enc"
    out.write_bytes(Fernet(key).encrypt(blob))
    legacy = data_dir / "prompt.enc"
    if legacy.is_file():
        legacy.unlink()
    print("Wrote", out)
    print("Set this env var on any machine that runs the app (do not commit or zip it):")
    print(f"FITBOARD_PROMPT_KEY={key.decode('ascii')}")


if __name__ == "__main__":
    main()
