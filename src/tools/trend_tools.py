from datetime import date, timedelta
from src.config import supabase


def query_roas_trend(platform: str | None = None, weeks: int = 4) -> dict:
    """
    Return week-over-week ROAS for the last N weeks, trend direction, consecutive
    declining/improving streak, and total spend erosion. Includes citations.

    spend_erosion = spend that was wasted due to ROAS falling from its peak.
    """
    today = date.today()
    weekly_data = []

    for i in range(weeks - 1, -1, -1):
        week_end = today - timedelta(weeks=i)
        week_start = week_end - timedelta(days=6)

        q = (
            supabase.table("ad_spend")
            .select("id, spend, purchases, source, source_id")
            .gte("date", str(week_start))
            .lte("date", str(week_end))
        )
        if platform:
            q = q.eq("platform", platform)
        rows = q.execute().data

        spend = sum(r["spend"] for r in rows)
        purchases = sum(r["purchases"] for r in rows)
        roas = round(purchases / spend, 4) if spend else 0.0

        weekly_data.append({
            "week_start": str(week_start),
            "week_end":   str(week_end),
            "spend":      round(spend, 2),
            "purchases":  purchases,
            "roas":       roas,
            "citations":  [
                {"table": "ad_spend", "id": r["id"], "source": r["source"], "source_id": r["source_id"]}
                for r in rows
            ],
        })

    direction, streak, spend_erosion = _compute_trend(weekly_data, key="roas")
    all_citations = [c for w in weekly_data for c in w["citations"]]

    return {
        "weeks":          weekly_data,
        "direction":      direction,
        "streak_weeks":   streak,
        "spend_erosion":  spend_erosion,
        "citations":      all_citations,
    }


def query_sales_trend(weeks: int = 4) -> dict:
    """
    Return week-over-week revenue and order count for the last N weeks, plus
    trend direction and streak. Includes citations.
    """
    today = date.today()
    weekly_data = []

    for i in range(weeks - 1, -1, -1):
        week_end = today - timedelta(weeks=i)
        week_start = week_end - timedelta(days=6)

        rows = (
            supabase.table("orders")
            .select("id, total_price, source, source_id")
            .gte("created_at", str(week_start))
            .lte("created_at", str(week_end))
            .execute()
            .data
        )
        revenue = sum(float(r["total_price"]) for r in rows)

        weekly_data.append({
            "week_start":  str(week_start),
            "week_end":    str(week_end),
            "revenue":     round(revenue, 2),
            "order_count": len(rows),
            "citations":   [
                {"table": "orders", "id": r["id"], "source": r["source"], "source_id": r["source_id"]}
                for r in rows
            ],
        })

    direction, streak, _ = _compute_trend(weekly_data, key="revenue")
    all_citations = [c for w in weekly_data for c in w["citations"]]

    return {
        "weeks":        weekly_data,
        "direction":    direction,
        "streak_weeks": streak,
        "citations":    all_citations,
    }


def _compute_trend(weekly_data: list[dict], key: str) -> tuple[str, int, float]:
    """Return (direction, consecutive_streak, spend_erosion)."""
    if len(weekly_data) < 2:
        return "stable", 0, 0.0

    values = [w[key] for w in weekly_data]
    last, prev = values[-1], values[-2]

    if last < prev:
        direction = "declining"
    elif last > prev:
        direction = "improving"
    else:
        return "stable", 0, 0.0

    # Count consecutive weeks in the same direction (from most recent backwards)
    streak = 1
    for i in range(len(values) - 2, 0, -1):
        if direction == "declining" and values[i] < values[i - 1]:
            streak += 1
        elif direction == "improving" and values[i] > values[i - 1]:
            streak += 1
        else:
            break

    # Spend erosion: how much spend was wasted vs peak ROAS efficiency
    spend_erosion = 0.0
    if direction == "declining" and key == "roas":
        peak_roas = max(values)
        total_spend = sum(w.get("spend", 0) for w in weekly_data)
        spend_erosion = round((peak_roas - last) * total_spend, 2)

    return direction, streak, spend_erosion
