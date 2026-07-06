from datetime import datetime

import httpx

REMOTEOK_API_URL = "https://remoteok.com/api"


def fetch_postings() -> list[dict]:
    response = httpx.get(
        REMOTEOK_API_URL,
        headers={"User-Agent": "job-search-agent/0.1 (personal learning project)"},
        timeout=15,
    )
    response.raise_for_status()
    raw_postings = response.json()

    postings = []
    for entry in raw_postings:
        # RemoteOK's first array element is a legal/metadata notice, not a job.
        if "id" not in entry or "position" not in entry:
            continue

        posted_at = None
        if entry.get("date"):
            try:
                posted_at = datetime.fromisoformat(entry["date"])
            except ValueError:
                posted_at = None

        postings.append(
            {
                "source": "remoteok",
                "external_id": str(entry["id"]),
                "title": entry.get("position", ""),
                "company": entry.get("company", ""),
                "location": entry.get("location", ""),
                "description": entry.get("description", ""),
                "url": entry.get("url", ""),
                "posted_at": posted_at,
            }
        )
    return postings
