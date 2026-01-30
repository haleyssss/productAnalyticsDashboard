# Product Metrics & Funnel Analytics Dashboard
 
 ## Overview
 
 This project is a **product analytics dashboard** designed to help product and growth teams understand how users move through a product funnel and where opportunities exist to improve activation, retention, and conversion.
 
 The dashboard simulates a real-world **B2C SaaS product** and tracks key user lifecycle events (signup, activation, retention, and conversion). It demonstrates how product metrics are defined, instrumented, queried, and translated into actionable product decisions.
 
 The goal of this project is not just to visualize data, but to show **product thinking** — how metrics inform strategy, experimentation, and prioritization.
 
 ---
 
 ## Business Problem
 
 Many products struggle not because of lack of traffic, but because users fail to:
 
 - Activate (experience the core value)
 - Return after first use
 - Convert into paying customers
 
 Product teams need a clear view of:
 
 - Where users drop off in the funnel
 - How retention changes over time
 - Which behaviors correlate with long-term value
 
 This project answers those questions by building an internal-facing analytics tool that mirrors how modern product teams measure success.
 
 ---
 
 ## Key Metrics Tracked
 
 - **Activation Rate**
   Percentage of users who complete a key action after signup.
 
 - **Retention (Day N)**
   Percentage of users who return after N days.
 
 - **Conversion Rate**
   Percentage of active users who convert to paid users.
 
 - **DAU / MAU**
   Daily and monthly active usage trends.
 
 - **Funnel Drop-Off**
   Where users exit the product lifecycle.
 
 ---
 
 ## Data Model
 
 The project uses an event-based analytics model similar to tools like Segment or Mixpanel.
 
 Each user interaction is stored as an event with:
 
 - `user_id`
 - `event_name` (signup, activate, login, purchase, etc.)
 - `event_time`
 - `platform`
 - `acquisition_source`
 
 Synthetic data is generated to simulate realistic user behavior across thousands of users.
 
 ---
 
 ## Technical Stack
 
 - **Python** – data generation, analysis, and business logic
 - **SQL (SQLite/Postgres)** – querying product metrics
 - **Pandas** – data transformation and aggregation
 - **Streamlit / Dash** – interactive dashboard visualization
 
 The stack is intentionally lightweight and representative of tools commonly used in internal product analytics.
 
 ---
 
 ## Dashboard Features
 
 - KPI summary tiles (Activation, Retention, Conversion)
 - Funnel visualization showing user drop-off
 - Retention curves over time
 - Weekly activity trends
 - Filters for platform and acquisition source

---

## Setup

1. Create and activate a virtual environment (optional).
2. Install dependencies:
   - `pip3 install -r requirements.txt`
3. Generate local data (optional):
   - `python3 src/data_generation.py`

## Run

## Startup

1. Ensure `product_events.csv` exists (or set `MOCKAROO_API_URL` in `.env`).
2. Start the app:
  - `python3 -m streamlit run app.py`
3. Open the local URL shown in the terminal (typically `http://localhost:8501`).

## Node Backend (Render)

This repository also includes a small Node/Express API for hosting on Render.

1. Install dependencies:
   - `npm install`
2. Start the server:
   - `npm start`

The API reads `product_events.csv` by default (or `data/events.csv`), and supports:

- `GET /metrics/summary`
- `GET /metrics/funnel`
- `GET /metrics/retention`
- `GET /metrics/dau`
- `GET /events`

To override the CSV path, set `EVENTS_CSV_PATH`.

## Streamlit on Render (Embed in Webflow)

This repo can be deployed directly to Render as a Streamlit web service.

1. Create a new Render Web Service from this repo.
2. Render will pick up `render.yaml` automatically.
3. Once deployed, use the Render URL in a Webflow Embed element via an iframe.

Example iframe:

```html
<iframe
  src="https://your-render-service.onrender.com"
  width="100%"
  height="800"
  style="border:0;"
></iframe>
```

## Mockaroo API (Optional)

To load live synthetic data from Mockaroo:

1. Put your API URL in `.env`:
   - `MOCKAROO_API_URL="https://api.mockaroo.com/api/<schema>?count=1000&key=<key>"`
2. The app will use the API when available and fall back to local CSV files.

## Screenshots

Add screenshots here once the dashboard is running:

- `docs/screenshots/overview.png`
- `docs/screenshots/funnel.png`
 
 ---
 
 ## Product Insights & Recommendations
 
 Beyond metrics, the dashboard is used to generate product insights such as:
 
 - Identifying onboarding friction when activation rates are low
 - Understanding how early activation impacts long-term retention
 - Prioritizing experiments to improve conversion
 
 Each insight is framed as a **product decision**, not just a data observation.
 
 ---
 
 ## Intended Audience
 
 This project is designed for:
 
 - Product Managers
 - Growth Managers
 - Product Analysts
 - Business Operations / Strategy teams
 
 It reflects how product analytics is used in real companies to guide roadmap decisions and growth initiatives.
 
 ---
 
 ## Outcome
 
 This project demonstrates the ability to:
 
 - Define success metrics
 - Design an event-based data model
 - Query and analyze product behavior
 - Translate data into business and product recommendations
 
 It serves as a portfolio project aligned with **product management, growth, and analytics roles**.
# productAnalyticsDashboard
