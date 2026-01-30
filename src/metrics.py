"""Metric calculations for activation, retention, and conversion."""

from __future__ import annotations

import pandas as pd


def activation_rate(events: pd.DataFrame) -> float:
    """Share of users who activate after signup."""
    signups = set(events.loc[events["event_name"] == "signup", "user_id"])
    activations = set(events.loc[events["event_name"] == "activate", "user_id"])
    return len(activations) / len(signups) if signups else 0.0


def conversion_rate(events: pd.DataFrame) -> float:
    """Share of active users who purchase."""
    active_users = set(events.loc[events["event_name"] == "activate", "user_id"])
    purchasers = set(events.loc[events["event_name"] == "purchase", "user_id"])
    return len(purchasers) / len(active_users) if active_users else 0.0
