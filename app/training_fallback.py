from __future__ import annotations

CURATED: list[dict[str, str]] = [
    {
        "title": "SQLBolt lessons",
        "url": "https://sqlbolt.com/lesson/introduction",
        "why": "Hands-on SQL for analyst and backend-type roles.",
    },
    {
        "title": "Python beginner path (Microsoft Learn)",
        "url": "https://learn.microsoft.com/en-us/training/paths/python-first-steps/",
        "why": "Python baseline for ML and engineering tracks.",
    },
    {
        "title": "MDN Learn web",
        "url": "https://developer.mozilla.org/en-US/docs/Learn",
        "why": "HTML and browser basics toward frontend work.",
    },
    {
        "title": "freeCodeCamp JavaScript",
        "url": "https://www.freecodecamp.org/learn/javascript-algorithms-and-data-structures/",
        "why": "JavaScript practice before React-type roles.",
    },
    {
        "title": "Statistics and probability (Khan Academy)",
        "url": "https://www.khanacademy.org/math/statistics-probability",
        "why": "Stats language for data analyst expectations.",
    },
    {
        "title": "Google UX design certificate hub",
        "url": "https://grow.google/certificates/ux-design/",
        "why": "Structured intro to UX when Figma and research matter.",
    },
    {
        "title": "Windows help and how-to",
        "url": "https://support.microsoft.com/en-us/windows",
        "why": "Troubleshooting mindset for support-style roles.",
    },
]


def ensure_minimum_training(
    training: list[dict],
    matches: list[dict],
    threshold: int,
    minimum: int = 3,
) -> list[dict]:
    if not any(int(m.get("score") or 0) < threshold for m in matches):
        return training
    if len(training) >= minimum:
        return training[:8]

    seen_urls = {item["url"].split("?", 1)[0].rstrip("/") for item in training}
    out = list(training)
    for row in CURATED:
        if len(out) >= minimum:
            break
        u = row["url"]
        key = u.split("?", 1)[0].rstrip("/")
        if key in seen_urls:
            continue
        seen_urls.add(key)
        out.append(dict(row))
    return out[:8]
