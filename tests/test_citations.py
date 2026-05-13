"""Unit tests for citation verification logic."""
from unittest.mock import MagicMock, patch
from src.agent.citations import verify_citations


def _mock_supabase(existing_ids: dict[str, list]):
    """Build a supabase mock that returns given IDs per table."""
    mock_sb = MagicMock()

    def table_side_effect(name):
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_in = MagicMock()
        mock_execute = MagicMock()

        ids = existing_ids.get(name, [])
        mock_execute.data = [{"id": i} for i in ids]
        mock_in.execute.return_value = mock_execute
        mock_select.in_.return_value = mock_in
        mock_table.select.return_value = mock_select
        return mock_table

    mock_sb.table.side_effect = table_side_effect
    return mock_sb


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_verify_empty_returns_empty():
    valid, invalid = verify_citations([])
    assert valid == []
    assert invalid == []


def test_verify_all_valid():
    citations = [
        {"table": "orders", "id": 1, "source": "shopify"},
        {"table": "orders", "id": 2, "source": "shopify"},
    ]
    mock_sb = _mock_supabase({"orders": [1, 2]})
    with patch("src.agent.citations.supabase", mock_sb):
        valid, invalid = verify_citations(citations)
    assert len(valid) == 2
    assert len(invalid) == 0


def test_verify_some_invalid():
    citations = [
        {"table": "orders", "id": 1, "source": "shopify"},
        {"table": "orders", "id": 999, "source": "shopify"},  # doesn't exist
    ]
    mock_sb = _mock_supabase({"orders": [1]})
    with patch("src.agent.citations.supabase", mock_sb):
        valid, invalid = verify_citations(citations)
    assert len(valid) == 1
    assert valid[0]["id"] == 1
    assert len(invalid) == 1
    assert invalid[0]["id"] == 999


def test_verify_citation_without_id_passes_through():
    """Source-only citations (no row id) should be treated as valid."""
    citations = [{"table": "orders", "source": "shopify", "source_id": "5001"}]
    mock_sb = _mock_supabase({})
    with patch("src.agent.citations.supabase", mock_sb):
        valid, invalid = verify_citations(citations)
    assert len(valid) == 1
    assert len(invalid) == 0


def test_verify_multiple_tables():
    citations = [
        {"table": "orders",   "id": 1},
        {"table": "ad_spend", "id": 10},
        {"table": "ad_spend", "id": 11},  # doesn't exist
    ]
    mock_sb = _mock_supabase({"orders": [1], "ad_spend": [10]})
    with patch("src.agent.citations.supabase", mock_sb):
        valid, invalid = verify_citations(citations)
    assert len(valid) == 2
    assert len(invalid) == 1
    assert invalid[0]["id"] == 11


def test_verify_supabase_error_treats_as_valid():
    """If Supabase is unreachable, all citations should pass to avoid false negatives."""
    citations = [{"table": "orders", "id": 1}]
    mock_sb = MagicMock()
    mock_sb.table.side_effect = Exception("connection error")
    with patch("src.agent.citations.supabase", mock_sb):
        valid, invalid = verify_citations(citations)
    assert len(valid) == 1
    assert len(invalid) == 0
