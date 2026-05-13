from typing import NamedTuple
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class NormalizedRecord(NamedTuple):
    table: str
    data: dict
    source: str
    source_id: str


def make_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session
