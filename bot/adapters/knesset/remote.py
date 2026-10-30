"""Client for the authenticated Knesset fetch service in Israel."""
from urllib.parse import urlencode
from urllib.request import Request

from pydantic import TypeAdapter
from requests import RequestException, Session
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

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
        response = None
        # Budget per-attempt timeouts and capped waits for Vercel's 300-second limit.
        retries = Retry(total=4, connect=0, read=0, other=0, allowed_methods={"GET"},
                        status_forcelist={429, 502, 503, 504}, backoff_factor=2,
                        backoff_jitter=1, backoff_max=10, retry_after_max=10,
                        raise_on_status=False)
        try:
            with Session() as session:
                session.mount(f"{self.url}/", HTTPAdapter(max_retries=retries))
                response = session.get(f"{self.url}/feed", headers={"Authorization": f"Bearer {self.token}"},
                                       timeout=(5, 40), allow_redirects=False)
            response.raise_for_status()
            return TypeAdapter(list[FeedLetter]).validate_python(response.json())
        except (RequestException, ValueError) as error:
            detail = f" (HTTP {response.status_code})" if response is not None else ""
            raise FeedUnreachable(f"Israeli fetch service: {type(error).__name__}{detail}") from error
