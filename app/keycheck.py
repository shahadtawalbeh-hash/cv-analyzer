from openai import OpenAI


def ping_openai_key(api_key: str) -> tuple[bool, str]:
    if not api_key or len(api_key) < 20:
        return False, "That key looks too short."
    try:
        client = OpenAI(api_key=api_key)
        client.models.list()
        return True, "Key checks out."
    except Exception as exc:
        return False, f"OpenAI rejected the key: {exc}"
