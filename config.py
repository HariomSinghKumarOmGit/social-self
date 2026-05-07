# Module: config | Purpose: Centralized runtime configuration.
# Public API: ACCOUNTS, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, APIFY_API_TOKEN, POST_TIMES, LOOKBACK_DAYS

from __future__ import annotations

import os
from typing import Dict, List

from dotenv import load_dotenv

load_dotenv()

ACCOUNTS: Dict[str, List[str]] = {
    "instagram": [
        "codeandcomplexity",
        # Add more Instagram usernames to monitor:
        # "therock", "selenagomez", etc.
    ],
    "twitter": [
        "PratikSinhatwt",
        # Add more Twitter/X usernames to monitor:
        # "elonmusk", "naval", etc.
    ],
    "youtube": [
        # Add YouTube usernames or channel handles to monitor:
        # "mkbhd", "veritasium", etc.
    ],
}

TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
APIFY_API_TOKEN: str = os.getenv("APIFY_API_TOKEN", "")

POST_TIMES: List[str] = ["09:00", "13:00", "18:00", "21:00"]
LOOKBACK_DAYS: int = 7
