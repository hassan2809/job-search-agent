from datetime import datetime, timezone

import httpx

ARBEITNOW_API_URL = "https://www.arbeitnow.com/api/job-board-api"


def fetch_postings() -> list[dict]:
    response = httpx.get(ARBEITNOW_API_URL, timeout=15)
    response.raise_for_status()
    payload = response.json()

    postings = []
    for entry in payload.get("data", []):
        posted_at = None
        if entry.get("created_at"):
            try:
                posted_at = datetime.fromtimestamp(entry["created_at"], tz=timezone.utc)
            except (ValueError, OSError, OverflowError):
                posted_at = None

        postings.append(
            {
                "source": "arbeitnow",
                "external_id": entry.get("slug", ""),
                "title": entry.get("title", ""),
                "company": entry.get("company_name", ""),
                "location": entry.get("location", ""),
                "description": entry.get("description", ""),
                "url": entry.get("url", ""),
                "posted_at": posted_at,
            }
        )
    return postings
