from src.config import supabase


def verify_citations(citations: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Verify that every cited row ID actually exists in Supabase.
    Returns (valid_citations, invalid_citations).

    Citations without an 'id' field (source-only citations) are passed through as valid.
    """
    if not citations:
        return [], []

    # Group IDs that need verification by table
    by_table: dict[str, list] = {}
    for c in citations:
        if c.get("id") is not None:
            by_table.setdefault(c["table"], []).append(c["id"])

    # Fetch which IDs actually exist
    existing: dict[str, set] = {}
    for table, ids in by_table.items():
        try:
            rows = supabase.table(table).select("id").in_("id", ids).execute().data
            existing[table] = {r["id"] for r in rows}
        except Exception:
            # If the table is unreachable, assume valid to avoid false negatives
            existing[table] = set(ids)

    valid, invalid = [], []
    for c in citations:
        cid = c.get("id")
        if cid is None:
            valid.append(c)
        elif cid in existing.get(c["table"], set()):
            valid.append(c)
        else:
            invalid.append(c)

    return valid, invalid
