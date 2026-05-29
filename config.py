# Module: config | Purpose: Centralized runtime configuration.
# Public API: ACCOUNTS, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, APIFY_API_TOKEN, POST_TIMES, LOOKBACK_DAYS, EC2_PUBLIC_IP

from __future__ import annotations

import os
from typing import Dict, List

from dotenv import load_dotenv

load_dotenv()

ACCOUNTS: Dict[str, List[str]] = {
    "instagram": [
        "codeandcomplexity",
        "rcsnotes",
        # Add more Instagram usernames to monitor:
        # "therock", "selenagomez", etc.
    ],
    "twitter": [
        "shobhittt007",
        "Byte_Nomadd",
        "dharanshi_",
        "KarthikNagpuri",
        "khushiirl",
        "PratikSinhatwt",
        "nick_realm_01",
        "_Chandan_17",
    ],
    "youtube": [
        # Add YouTube usernames or channel handles to monitor:
        "mkbhd",
        "veritasium",
        # "mkbhd", "veritasium", etc.
    ],
}

TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
APIFY_API_TOKEN: str = os.getenv("APIFY_API_TOKEN", "")

EC2_PUBLIC_IP: str = os.getenv("EC2_PUBLIC_IP", "")


def _parse_post_times(value: str) -> List[str]:
    items = [v.strip() for v in (value or "").split(",") if v.strip()]
    return items or ["09:00", "13:00", "18:00", "19:00", "21:00"]


POST_TIMES: List[str] = _parse_post_times(os.getenv("POST_TIMES", ""))
LOOKBACK_DAYS: int = int(os.getenv("LOOKBACK_DAYS", "7") or 7)
