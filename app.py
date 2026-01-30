import os
import logging
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

import altair as alt
import streamlit as st
import pandas as pd

from src import metrics
from src import sqlite_layer

logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

st.set_page_config(page_title="Product Metrics & Funnel Analytics", layout="wide")

st.title("Product Metrics & Funnel Analytics Dashboard")
st.caption("Synthetic event data to explore activation, retention, and conversion.")

st.markdown("""
This is a scaffolded Streamlit app. KPI tiles are backed by `src/metrics.py`.
""")


def load_env(path: str = ".env") -> None:
    """Load simple KEY=VALUE pairs into os.environ if not already set."""
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            value = value.strip().strip("\"'")
            os.environ.setdefault(key.strip(), value)


load_env()

@st.cache_data(ttl=300)
def fetch_events_from_api(api_url: str, retries: int = 2, timeout: int = 10) -> pd.DataFrame:
    """Fetch events from API with basic retries."""
    last_error = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(api_url, timeout=timeout) as response:
                payload = response.read().decode("utf-8")
            try:
                return pd.read_json(payload)
            except ValueError:
                from io import StringIO

                return pd.read_csv(StringIO(payload))
        except (urllib.error.URLError, ValueError) as exc:
            logging.warning("API fetch failed on attempt %s: %s", attempt + 1, exc)
            last_error = exc
            time.sleep(1 + attempt)
    raise RuntimeError(f"API fetch failed: {last_error}")


st.sidebar.header("Data Source")
api_url = st.sidebar.text_input(
    "Mockaroo API URL",
    value=os.getenv("MOCKAROO_API_URL", ""),
    help="Paste the full Mockaroo API URL including the key.",
)
data_source = st.sidebar.selectbox(
    "Source",
    [
        "Auto (API -> product_events.csv -> data/events.csv)",
        "API",
        "product_events.csv",
        "data/events.csv",
    ],
)

events = None
if data_source in ("Auto (API -> product_events.csv -> data/events.csv)", "API") and api_url:
    try:
        events = fetch_events_from_api(api_url)
    except RuntimeError as exc:
        st.warning(str(exc))

if events is None:
    if data_source == "API":
        st.warning("API URL missing or failed; falling back to local CSV.")
    fallback = "product_events.csv" if os.path.exists("product_events.csv") else "data/events.csv"
    if data_source in ("product_events.csv", "data/events.csv"):
        fallback = data_source
    events = pd.read_csv(fallback)

events["event_time"] = pd.to_datetime(events["event_time"], errors="coerce")
events = events.dropna(subset=["event_time"])
events["event_date"] = events["event_time"].dt.date
if "acquisition_source" not in events.columns and "acquisition_" in events.columns:
    events = events.rename(columns={"acquisition_": "acquisition_source"})

required_columns = {"user_id", "event_name", "event_time", "platform", "acquisition_source"}
missing_columns = required_columns - set(events.columns)
if missing_columns:
    st.error(f"Missing required columns: {sorted(missing_columns)}")
    st.stop()

non_null_counts = {
    "event_name": events["event_name"].notna().sum(),
    "platform": events["platform"].notna().sum(),
    "acquisition_source": events["acquisition_source"].notna().sum(),
}
if any(count == 0 for count in non_null_counts.values()):
    st.error(
        "Data is missing values for event fields. Check your Mockaroo schema lists "
        "for event_name, platform, and acquisition_source."
    )
    st.stop()

latest_event = events["event_time"].max()
if pd.notna(latest_event):
    latest_event = latest_event.to_pydatetime()
    if latest_event.tzinfo is None:
        latest_event = latest_event.replace(tzinfo=timezone.utc)
    age_days = (datetime.now(timezone.utc) - latest_event).days
else:
    age_days = None

st.sidebar.metric("Rows", f"{len(events):,}")
st.sidebar.metric(
    "Data freshness (days)",
    "--" if age_days is None else str(age_days),
)

st.sidebar.header("Self-Check")
issues = []
if missing_columns:
    issues.append(f"Missing columns: {sorted(missing_columns)}")
if any(count == 0 for count in non_null_counts.values()):
    issues.append("Event fields are empty; check Mockaroo custom lists.")
if events["user_id"].nunique() == len(events):
    issues.append("Each user_id is unique; retention will be empty.")

db_path = "data/events.sqlite"
if os.path.exists(db_path):
    db_mtime = datetime.fromtimestamp(os.path.getmtime(db_path), tz=timezone.utc)
    csv_source = (
        "product_events.csv" if os.path.exists("product_events.csv") else "data/events.csv"
    )
    csv_mtime = datetime.fromtimestamp(os.path.getmtime(csv_source), tz=timezone.utc)
    if db_mtime < csv_mtime:
        issues.append("SQLite DB is older than CSV; rebuild recommended.")

if issues:
    st.sidebar.error("Readiness issues detected")
    for item in issues:
        st.sidebar.write(f"- {item}")
else:
    st.sidebar.success("Data checks passed")

if st.sidebar.button("Rebuild SQLite DB"):
    if os.path.exists(db_path):
        os.remove(db_path)
    st.sidebar.success("SQLite DB removed. Reload to rebuild.")

use_sql = st.checkbox("Use SQLite queries", value=True)
retention_day_7_rate = None
funnel_data = None
retention_counts = None

st.sidebar.header("Filters")
platforms = sorted(events["platform"].dropna().unique())
sources = sorted(events["acquisition_source"].dropna().unique())
selected_platforms = st.sidebar.multiselect("Platform", platforms, default=platforms)
selected_sources = st.sidebar.multiselect("Acquisition Source", sources, default=sources)

filtered_events = events[
    events["platform"].isin(selected_platforms)
    & events["acquisition_source"].isin(selected_sources)
]

sql_allowed = use_sql and len(filtered_events) == len(events)
if use_sql and not sql_allowed:
    st.info("SQL mode is disabled when filters are applied. Using in-memory metrics.")

if sql_allowed:
    api_csv_path = "data/events_api.csv"
    if data_source in ("Auto (API -> product_events.csv -> data/events.csv)", "API") and api_url:
        filtered_events.to_csv(api_csv_path, index=False)
        sqlite_layer.ensure_db(api_csv_path)
    else:
        source = "product_events.csv" if os.path.exists("product_events.csv") else "data/events.csv"
        if data_source in ("product_events.csv", "data/events.csv"):
            source = data_source
        sqlite_layer.ensure_db(source)
    funnel_sql, retention_sql, retention_curve_sql = sqlite_layer.run_queries("src/queries.sql")
    funnel_data = funnel_sql
    signed_up = int(retention_sql.loc[0, "signed_up"])
    returned_day_7 = int(retention_sql.loc[0, "returned_day_7"])
    retention_day_7_rate = returned_day_7 / signed_up if signed_up else 0.0
    retention_counts = retention_curve_sql
    retention_counts["retention_rate"] = (
        retention_counts["returned_users"] / signed_up if signed_up else 0
    )
else:
    signup_dates = (
        filtered_events.loc[filtered_events["event_name"] == "signup", ["user_id", "event_time"]]
        .rename(columns={"event_time": "signup_time"})
    )
    logins = filtered_events.loc[filtered_events["event_name"] == "login", ["user_id", "event_time"]]
    retention_day_7 = logins.merge(signup_dates, on="user_id", how="inner")
    retention_day_7["day"] = (retention_day_7["event_time"] - retention_day_7["signup_time"]).dt.days
    returned_day_7 = retention_day_7[retention_day_7["day"] == 7]["user_id"].nunique()
    signed_up = signup_dates["user_id"].nunique()
    retention_day_7_rate = returned_day_7 / signed_up if signed_up else 0.0

# KPI tiles
col1, col2, col3 = st.columns(3)
col1.metric("Activation Rate", f"{metrics.activation_rate(filtered_events):.1%}")
col2.metric(
    "Retention (Day 7)",
    f"{retention_day_7_rate:.1%}" if retention_day_7_rate is not None else "--",
)
col3.metric("Conversion Rate", f"{metrics.conversion_rate(filtered_events):.1%}")

st.subheader("Funnel Drop-Off")
funnel_order = ["signup", "activate", "login", "purchase"]
if funnel_data is None:
    funnel = (
        filtered_events[filtered_events["event_name"].isin(funnel_order)]
        .groupby("event_name")["user_id"]
        .nunique()
        .reindex(funnel_order)
        .reset_index()
        .rename(columns={"user_id": "users"})
    )
else:
    funnel = (
        funnel_data.set_index("event_name")
        .reindex(funnel_order)
        .fillna(0)
        .reset_index()
    )
    if "users" not in funnel.columns:
        funnel = funnel.rename(columns={funnel.columns[-1]: "users"})

funnel["users"] = funnel["users"].fillna(0).astype(int)
funnel["prev_users"] = funnel["users"].shift(1)
funnel["drop_off_pct"] = (
    1 - (funnel["users"] / funnel["prev_users"])
).where(funnel["prev_users"].notna(), 0.0)
funnel_chart = (
    alt.Chart(funnel)
    .mark_bar()
    .encode(
        x=alt.X("users:Q", title="Users"),
        y=alt.Y("event_name:N", sort=funnel_order, title=None),
        color=alt.Color("event_name:N", legend=None),
        tooltip=["event_name", "users"],
    )
)
st.altair_chart(funnel_chart, use_container_width=True)
st.caption("Funnel counts by event stage; drop-off shown below.")

dropoff_table = funnel[["event_name", "users", "drop_off_pct"]].copy()
dropoff_table["drop_off_pct"] = dropoff_table["drop_off_pct"].map(lambda x: f"{x:.1%}")
st.dataframe(dropoff_table, use_container_width=True)

st.subheader("Retention Curves")
if retention_counts is None:
    signup_dates = (
        filtered_events.loc[filtered_events["event_name"] == "signup", ["user_id", "event_time"]]
        .rename(columns={"event_time": "signup_time"})
    )
    logins = filtered_events.loc[filtered_events["event_name"] == "login", ["user_id", "event_time"]]
    retention = logins.merge(signup_dates, on="user_id", how="inner")
    retention["day"] = (retention["event_time"] - retention["signup_time"]).dt.days
    retention = retention[(retention["day"] >= 0) & (retention["day"] <= 30)]

    retention_counts = (
        retention.groupby("day")["user_id"].nunique().reset_index(name="returned_users")
    )
    total_signups = signup_dates["user_id"].nunique()
    retention_counts["retention_rate"] = (
        retention_counts["returned_users"] / total_signups if total_signups else 0
    )

max_retention_day = int(retention_counts["day"].max()) if not retention_counts.empty else 0
max_retention_day = max(1, max_retention_day)
retention_window = st.slider(
    "Retention window (days)",
    min_value=1,
    max_value=max_retention_day,
    value=min(14, max_retention_day),
)
retention_counts = retention_counts[retention_counts["day"].between(0, retention_window)]

retention_chart = (
    alt.Chart(retention_counts)
    .mark_line(point=True)
    .encode(
        x=alt.X("day:Q", title="Days since signup"),
        y=alt.Y("retention_rate:Q", title="Retention rate", axis=alt.Axis(format="%")),
        tooltip=[
            "day",
            "returned_users",
            alt.Tooltip("retention_rate:Q", format=".1%"),
        ],
    )
)
st.altair_chart(retention_chart, use_container_width=True)
st.caption("Retention curve for days since signup within the selected window.")

st.subheader("Weekly Activity Trends")
daily_active = (
    filtered_events.groupby("event_date")["user_id"]
    .nunique()
    .reset_index(name="dau")
    .sort_values("event_date")
)
activity_chart = (
    alt.Chart(daily_active)
    .mark_line()
    .encode(
        x=alt.X("event_date:T", title="Date"),
        y=alt.Y("dau:Q", title="Daily Active Users"),
        tooltip=["event_date", "dau"],
    )
)
st.altair_chart(activity_chart, use_container_width=True)
st.caption("Daily active users over time for the filtered segment.")

st.subheader("Product Insights & Recommendations")
activation = metrics.activation_rate(filtered_events)
conversion = metrics.conversion_rate(filtered_events)
dau_latest = int(daily_active["dau"].iloc[-1]) if not daily_active.empty else 0

insights = []
if activation < 0.5:
    insights.append(
        "Activation is low. Focus on onboarding clarity and the first-time user experience."
    )
if conversion < 0.15:
    insights.append(
        "Conversion is soft. Test pricing page messaging and trial-to-paid nudges."
    )
if dau_latest < daily_active["dau"].mean() if not daily_active.empty else False:
    insights.append(
        "Recent activity is below average. Re-engage users with lifecycle messaging."
    )

if not insights:
    insights = [
        "Metrics look healthy. Prioritize retention experiments to lock in long-term value."
    ]

for item in insights:
    st.write(f"- {item}")
