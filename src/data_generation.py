"""Generate synthetic event data for the dashboard."""

from __future__ import annotations

import random
from datetime import datetime, timedelta

import pandas as pd

EVENTS = ["signup", "activate", "login", "purchase"]
PLATFORMS = ["web", "ios", "android"]
SOURCES = ["seo", "paid", "referral", "organic"]


def generate_events(num_users: int = 1000, days: int = 60) -> pd.DataFrame:
    """Return a DataFrame of synthetic events."""
    rows = []
    start = datetime.utcnow() - timedelta(days=days)

    for user_id in range(1, num_users + 1):
        signup_time = start + timedelta(days=random.randint(0, days - 1))
        platform = random.choice(PLATFORMS)
        source = random.choice(SOURCES)
        rows.append((user_id, "signup", signup_time, platform, source))

        # Simple behavior model: some users activate, return, and purchase
        if random.random() < 0.7:
            rows.append((user_id, "activate", signup_time + timedelta(days=1), platform, source))
        if random.random() < 0.5:
            rows.append((user_id, "login", signup_time + timedelta(days=7), platform, source))
        if random.random() < 0.2:
            rows.append((user_id, "purchase", signup_time + timedelta(days=10), platform, source))

    return pd.DataFrame(rows, columns=["user_id", "event_name", "event_time", "platform", "acquisition_source"])


if __name__ == "__main__":
    df = generate_events()
    df.to_csv("data/events.csv", index=False)
