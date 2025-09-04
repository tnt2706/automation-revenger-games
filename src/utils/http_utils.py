import os
import requests
from urllib.parse import urljoin
from typing import Optional
from utils.logger import write_log


def get_token_by_operator_target(
    operator_target: str,
    currency: str = "USD",
    language: str = "en",
    balance: int = 100_000_000,
) -> str:
    url = urljoin(
        operator_target,
        f"/api/internal/players/_new?currency={currency}&balance={balance}&language={language}",
    )
    timeout_sec = int(os.environ.get("timeout", "2"))

    try:
        response = requests.get(url, timeout=timeout_sec)
        response.raise_for_status()
        data = response.json()
        token = data.get("id")
        if not token:
            raise ValueError(f"No token returned from operator API: {data}")

        write_log(
            f"✅ Player token obtained: {{'currency': {currency}, 'balance': {balance}, 'token': {token}}}"
        )
        return token

    except requests.RequestException as e:
        write_log(f"❌ Request failed to {url}: {e}")
        raise
    except ValueError as ve:
        write_log(f"⚠️ Value error: {ve}")
        raise
