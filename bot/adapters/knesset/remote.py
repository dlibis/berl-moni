"""Client for the authenticated Knesset fetch service in Israel."""
from urllib.parse import urlencode
from urllib.request import Request

from pydantic import TypeAdapter
from requests import RequestException, get

from bot.domain.errors import FeedUnreachable
from bot.domain.feed import FeedLetter


class KnessetClient:
    def __init__(self, url: str, token: str):
        if not url.startswith("https://") or not token:
            raise ValueError("Knesset fetch service needs an HTTPS URL and token")
        self.url = url.rstrip("/")
        self.token = token

    def pdf_request(self, source: str) -> Request:
        return Request(f"{self.url}/pdf?{urlencode({'url': source})}",
                       headers={"Authorization": f"Bearer {self.token}"})

    def fetch_letters(self) -> list[FeedLetter]:
        try:
            response = get(f"{self.url}/feed", headers={"Authorization": f"Bearer {self.token}"}, timeout=(10, 290))
            response.raise_for_status()
            return TypeAdapter(list[FeedLetter]).validate_python(response.json())
        except (RequestException, ValueError) as error:
            raise FeedUnreachable(f"Israeli fetch service: {type(error).__name__}") from error
