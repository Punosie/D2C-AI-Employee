from src.config import settings
from .base import NormalizedRecord, make_session


def fetch_meta() -> list[dict]:
    """Fetch last 30 days of campaign insights from Meta Ads."""
    session = make_session()

    resp = session.get(
        f"https://graph.facebook.com/v19.0/act_{settings.META_AD_ACCOUNT_ID}/insights",
        params={
            "access_token": settings.META_ACCESS_TOKEN,
            "fields": "date_start,campaign_name,spend,impressions,clicks,actions",
            "time_increment": 1,        # daily breakdown
            "date_preset": "last_30d",
            "level": "campaign",
            "limit": 500,
        },
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def normalize_meta(raw: list[dict]) -> list[NormalizedRecord]:
    """Map raw Meta Ads insights into NormalizedRecords for the ad_spend table."""
    records = []

    for row in raw:
        purchases = next(
            (int(a["value"]) for a in row.get("actions", []) if a["action_type"] == "purchase"),
            0,
        )
        source_id = f"meta_{row['date_start']}_{row['campaign_name']}"

        records.append(NormalizedRecord(
            table="ad_spend",
            data={
                "date": row["date_start"],
                "platform": "meta",
                "campaign_name": row["campaign_name"],
                "spend": float(row["spend"]),
                "impressions": int(row["impressions"]),
                "clicks": int(row["clicks"]),
                "purchases": purchases,
                "source": "meta",
                "source_id": source_id,
            },
            source="meta",
            source_id=source_id,
        ))

    return records
