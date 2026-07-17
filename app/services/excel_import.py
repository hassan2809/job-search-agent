from io import BytesIO

import openpyxl

# Maps a normalized header name to the possible header text found in the sheet.
# "c-suite" is the header used in the existing sheet for the person's own LinkedIn URL.
# "company"/"company url" (a column being added going forward) is the URL of their company.
HEADER_ALIASES = {
    "name": ("name",),
    "url": ("url", "linkedin url", "linkedin", "c-suite"),
    "event": ("event", "events"),
    "company_url": ("company", "company url", "company name"),
}


def _normalize_header(value: object) -> str:
    return str(value or "").strip().lower()


def _build_column_map(header_row: tuple) -> dict[str, int]:
    normalized = [_normalize_header(cell) for cell in header_row]
    column_map: dict[str, int] = {}
    for field, aliases in HEADER_ALIASES.items():
        for index, header in enumerate(normalized):
            if header in aliases:
                column_map[field] = index
                break
    return column_map


def parse_leads_xlsx(file_bytes: bytes) -> list[dict]:
    """Parses a weekly LinkedIn tracking sheet (name, url, event, company_url columns) into lead dicts."""
    workbook = openpyxl.load_workbook(BytesIO(file_bytes), data_only=True)
    sheet = workbook.active

    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return []

    column_map = _build_column_map(rows[0])
    if "name" not in column_map or "url" not in column_map:
        raise ValueError("Sheet must have at least a 'Name' column and a person-URL column (e.g. 'C-suite' or 'URL')")

    leads: dict[str, dict] = {}
    for row in rows[1:]:
        def get(field: str) -> str:
            index = column_map.get(field)
            if index is None or index >= len(row):
                return ""
            return str(row[index] or "").strip()

        url = get("url")
        name = get("name")
        if not url or not name:
            continue

        event = get("event")
        company_url = get("company_url")

        description_parts = [f"Name: {name}"]
        if company_url:
            description_parts.append(f"Company URL: {company_url}")
        if event:
            description_parts.append(f"Connected via: {event}")
        description = "\n".join(description_parts)

        # Later rows win on duplicate URLs (same person listed more than once in the sheet).
        leads[url] = {
            "source": "linkedin_manual",
            "external_id": url,
            "title": name,
            "description": description,
            "url": url,
            "author": name,
            "contact_email": None,
            "is_manual": True,
            "origin_type": "prospected",
            "posted_at": None,
        }

    return list(leads.values())
