import json
import os
import re
from dataclasses import dataclass

from openai import OpenAI

from app.prompt_loader import PromptKeyMissing, load_prompt_bundle
from app.training_fallback import ensure_minimum_training

MATCH_THRESHOLD = 70

ALLOWED_HOST_SUFFIXES = (
    "coursera.org",
    "edx.org",
    "freecodecamp.org",
    "khanacademy.org",
    "microsoft.com",
    "mozilla.org",
    "developer.mozilla.org",
    "w3.org",
    "learn.microsoft.com",
    "grow.google",
    "cloud.google.com",
    "numpy.org",
    "python.org",
    "sqlbolt.com",
    "sqlzoo.net",
)


def _url_allowed(url: str) -> bool:
    if not url.startswith("https://"):
        return False
    try:
        host = url.split("/")[2].lower()
    except IndexError:
        return False
    return any(host == s or host.endswith("." + s) for s in ALLOWED_HOST_SUFFIXES)


def _scrub_training(entries: list[dict]) -> list[dict]:
    clean: list[dict] = []
    for item in entries:
        url = (item.get("url") or "").strip()
        title = (item.get("title") or "").strip()
        why = (item.get("why") or "").strip()
        if not title or not why:
            continue
        if not url or not _url_allowed(url):
            continue
        clean.append({"title": title, "url": url, "why": why})
    return clean[:8]


@dataclass
class AnalysisResult:
    raw_profile: dict
    matches: list[dict]
    training: list[dict]


def run_cv_analysis(api_key: str, cv_text: str, jobs_payload: list[dict]) -> AnalysisResult:
    try:
        bundle = load_prompt_bundle()
        system = bundle["system"]
        example_urls = bundle.get("example_urls") or []
    except PromptKeyMissing as exc:
        raise RuntimeError(str(exc)) from exc

    client = OpenAI(api_key=api_key)
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    user = json.dumps(
        {
            "cv_text": cv_text[:16000],
            "jobs": jobs_payload,
            "threshold": MATCH_THRESHOLD,
            "allowed_training_hosts": list(ALLOWED_HOST_SUFFIXES),
            "urls_that_pass_the_filter": example_urls,
            "output_schema": {
                "profile": {
                    "headline": "string",
                    "skills": ["string"],
                    "education": ["string"],
                    "experience_highlights": ["string"],
                    "reading_notes": "string, empty if nothing odd",
                },
                "matches": [{"job_id": 0, "score": 0, "summary": "string"}],
                "training": [{"title": "string", "url": "https://...", "why": "string"}],
            },
        },
        ensure_ascii=False,
    )

    completion = client.chat.completions.create(
        model=model,
        temperature=0.15,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    text = completion.choices[0].message.content or "{}"
    text = re.sub(r"[\u2013\u2014]", "-", text)
    payload = json.loads(text)

    profile = payload.get("profile") or {}
    matches_raw = payload.get("matches") or []
    training_raw = payload.get("training") or []

    matches: list[dict] = []
    seen: set[int] = set()
    for row in matches_raw:
        try:
            jid = int(row.get("job_id"))
            score = int(row.get("score"))
        except (TypeError, ValueError):
            continue
        if jid in seen:
            continue
        score = max(0, min(100, score))
        summary = str(row.get("summary") or "").strip()
        matches.append({"job_id": jid, "score": score, "summary": summary})
        seen.add(jid)

    for job in jobs_payload:
        jid = int(job["id"])
        if jid not in seen:
            matches.append(
                {
                    "job_id": jid,
                    "score": 0,
                    "summary": "Row missing from model output.",
                }
            )

    matches.sort(key=lambda r: r["job_id"])
    training = _scrub_training(training_raw if isinstance(training_raw, list) else [])
    training = ensure_minimum_training(training, matches, MATCH_THRESHOLD)

    return AnalysisResult(raw_profile=profile, matches=matches, training=training)
