from src.config import settings
from .base import NormalizedRecord, make_session


def fetch_meta(access_token: str | None = None, account_id: str | None = None) -> list[dict]:
    """Fetch last 30 days of campaign insights from Meta Ads."""
    _token   = access_token or settings.META_ACCESS_TOKEN or ""
    _acct_id = account_id   or settings.META_AD_ACCOUNT_ID or ""

    session = make_session()
    resp = session.get(
        f"https://graph.facebook.com/v19.0/act_{_acct_id}/insights",
        params={
            "access_token": _token,
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


def sync(merchant_id: str = "default") -> list[NormalizedRecord]:
    """Reads credentials fresh from DB — no restart needed."""
    from src.credentials import get_credentials

    creds        = get_credentials(merchant_id).get("meta_ads", {})
    access_token = creds.get("access_token") or settings.META_ACCESS_TOKEN
    account_id   = creds.get("account_id")   or settings.META_AD_ACCOUNT_ID

    if not (access_token and account_id):
        raise ValueError(
            "Meta Ads not connected. Go to Settings and add your Meta Ads details."
        )
    return normalize_meta(fetch_meta(access_token, account_id))
