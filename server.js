const fs = require("fs");
const path = require("path");
const express = require("express");
const { parse } = require("csv-parse/sync");

const app = express();
const PORT = process.env.PORT || 3000;

const DEFAULT_CSV_PATHS = ["product_events.csv", "data/events.csv"];

const MS_PER_DAY = 24 * 60 * 60 * 1000;

const cache = {
  filePath: null,
  mtimeMs: 0,
  events: [],
  rawColumns: [],
};

function resolveCsvPath() {
  const envPath = process.env.EVENTS_CSV_PATH;
  if (envPath && fs.existsSync(envPath)) {
    return envPath;
  }
  for (const candidate of DEFAULT_CSV_PATHS) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }
  throw new Error(
    "No events CSV found. Set EVENTS_CSV_PATH or provide product_events.csv."
  );
}

function toDateKey(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function parseDate(value) {
  if (!value) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }
  return parsed;
}

function normalizeEvents(rows) {
  return rows
    .map((row) => {
      const eventTime = parseDate(row.event_time);
      if (!eventTime) {
        return null;
      }
      const normalized = {
        user_id: String(row.user_id ?? "").trim(),
        event_name: String(row.event_name ?? "").trim(),
        event_time: eventTime,
        platform: String(row.platform ?? "").trim(),
        acquisition_source: String(
          row.acquisition_source ?? row.acquisition_ ?? ""
        ).trim(),
      };
      if (!normalized.user_id || !normalized.event_name) {
        return null;
      }
      normalized.event_date = toDateKey(eventTime);
      return normalized;
    })
    .filter(Boolean);
}

function loadEvents() {
  const filePath = resolveCsvPath();
  const stat = fs.statSync(filePath);
  if (cache.filePath === filePath && cache.mtimeMs === stat.mtimeMs) {
    return cache.events;
  }
  const csv = fs.readFileSync(filePath, "utf8");
  const rows = parse(csv, {
    columns: true,
    skip_empty_lines: true,
    trim: true,
  });
  const normalized = normalizeEvents(rows);
  cache.filePath = filePath;
  cache.mtimeMs = stat.mtimeMs;
  cache.events = normalized;
  cache.rawColumns = rows.length ? Object.keys(rows[0]) : [];
  return normalized;
}

function parseListParam(value) {
  if (!value) return null;
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function applyFilters(events, query) {
  const platforms = parseListParam(query.platform);
  const sources = parseListParam(query.source);
  if (!platforms && !sources) {
    return events;
  }
  return events.filter((event) => {
    if (platforms && !platforms.includes(event.platform)) {
      return false;
    }
    if (sources && !sources.includes(event.acquisition_source)) {
      return false;
    }
    return true;
  });
}

function uniqueUsers(events, eventName) {
  const users = new Set();
  events.forEach((event) => {
    if (event.event_name === eventName) {
      users.add(event.user_id);
    }
  });
  return users;
}

function buildSignupMap(events) {
  const signupByUser = new Map();
  events.forEach((event) => {
    if (event.event_name !== "signup") {
      return;
    }
    const current = signupByUser.get(event.user_id);
    if (!current || event.event_time < current) {
      signupByUser.set(event.user_id, event.event_time);
    }
  });
  return signupByUser;
}

function calculateRetention(events, maxDay) {
  const signupByUser = buildSignupMap(events);
  const usersByDay = new Map();

  events.forEach((event) => {
    if (event.event_name !== "login") {
      return;
    }
    const signupTime = signupByUser.get(event.user_id);
    if (!signupTime) {
      return;
    }
    const diffDays = Math.floor(
      (event.event_time.getTime() - signupTime.getTime()) / MS_PER_DAY
    );
    if (diffDays < 0 || diffDays > maxDay) {
      return;
    }
    if (!usersByDay.has(diffDays)) {
      usersByDay.set(diffDays, new Set());
    }
    usersByDay.get(diffDays).add(event.user_id);
  });

  const totalSignups = signupByUser.size;
  const curve = [];
  for (let day = 0; day <= maxDay; day += 1) {
    const users = usersByDay.get(day) || new Set();
    curve.push({
      day,
      returned_users: users.size,
      retention_rate: totalSignups ? users.size / totalSignups : 0,
    });
  }
  return { totalSignups, curve };
}

function calculateDay7Retention(events) {
  const signupByUser = buildSignupMap(events);
  const returned = new Set();

  events.forEach((event) => {
    if (event.event_name !== "login") {
      return;
    }
    const signupTime = signupByUser.get(event.user_id);
    if (!signupTime) {
      return;
    }
    const diffDays = Math.floor(
      (event.event_time.getTime() - signupTime.getTime()) / MS_PER_DAY
    );
    if (diffDays === 7) {
      returned.add(event.user_id);
    }
  });

  return {
    signed_up: signupByUser.size,
    returned_day_7: returned.size,
    retention_day_7_rate: signupByUser.size
      ? returned.size / signupByUser.size
      : 0,
  };
}

function calculateFunnel(events) {
  const order = ["signup", "activate", "login", "purchase"];
  const funnel = order.map((eventName) => ({
    event_name: eventName,
    users: uniqueUsers(events, eventName).size,
  }));
  funnel.forEach((row, index) => {
    const prev = index > 0 ? funnel[index - 1].users : null;
    row.drop_off_pct = prev ? 1 - row.users / prev : 0;
  });
  return funnel;
}

function calculateDailyActive(events) {
  const usersByDate = new Map();
  events.forEach((event) => {
    if (!usersByDate.has(event.event_date)) {
      usersByDate.set(event.event_date, new Set());
    }
    usersByDate.get(event.event_date).add(event.user_id);
  });
  return Array.from(usersByDate.entries())
    .map(([date, users]) => ({ event_date: date, dau: users.size }))
    .sort((a, b) => (a.event_date > b.event_date ? 1 : -1));
}

function calculateSummary(events) {
  const activationUsers = uniqueUsers(events, "activate");
  const signupUsers = uniqueUsers(events, "signup");
  const purchaseUsers = uniqueUsers(events, "purchase");

  const activation_rate = signupUsers.size
    ? activationUsers.size / signupUsers.size
    : 0;
  const conversion_rate = activationUsers.size
    ? purchaseUsers.size / activationUsers.size
    : 0;

  const latestEvent = events.reduce((latest, event) => {
    if (!latest || event.event_time > latest) {
      return event.event_time;
    }
    return latest;
  }, null);

  return {
    rows: events.length,
    unique_users: new Set(events.map((event) => event.user_id)).size,
    activation_rate,
    conversion_rate,
    latest_event_time: latestEvent ? latestEvent.toISOString() : null,
  };
}

app.get("/health", (req, res) => {
  res.json({ ok: true });
});

app.get("/filters", (req, res) => {
  const events = loadEvents();
  const platforms = new Set();
  const sources = new Set();
  events.forEach((event) => {
    if (event.platform) {
      platforms.add(event.platform);
    }
    if (event.acquisition_source) {
      sources.add(event.acquisition_source);
    }
  });
  res.json({
    platforms: Array.from(platforms).sort(),
    acquisition_sources: Array.from(sources).sort(),
  });
});

app.get("/events", (req, res) => {
  const events = applyFilters(loadEvents(), req.query);
  const limit = Math.min(Number(req.query.limit) || 500, 5000);
  const offset = Math.max(Number(req.query.offset) || 0, 0);
  res.json({
    count: events.length,
    offset,
    limit,
    events: events.slice(offset, offset + limit),
  });
});

app.get("/metrics/summary", (req, res) => {
  const events = applyFilters(loadEvents(), req.query);
  const summary = calculateSummary(events);
  const retention = calculateDay7Retention(events);
  res.json({ ...summary, ...retention });
});

app.get("/metrics/funnel", (req, res) => {
  const events = applyFilters(loadEvents(), req.query);
  res.json({ funnel: calculateFunnel(events) });
});

app.get("/metrics/retention", (req, res) => {
  const events = applyFilters(loadEvents(), req.query);
  const maxDay = Math.min(Math.max(Number(req.query.max_day) || 30, 1), 60);
  const retention = calculateRetention(events, maxDay);
  res.json({
    total_signups: retention.totalSignups,
    curve: retention.curve,
  });
});

app.get("/metrics/dau", (req, res) => {
  const events = applyFilters(loadEvents(), req.query);
  res.json({ daily_active: calculateDailyActive(events) });
});

app.get("/", (req, res) => {
  res.json({
    service: "product-analytics-backend",
    endpoints: [
      "/health",
      "/filters",
      "/events",
      "/metrics/summary",
      "/metrics/funnel",
      "/metrics/retention",
      "/metrics/dau",
    ],
  });
});

app.listen(PORT, () => {
  // eslint-disable-next-line no-console
  console.log(`Server listening on port ${PORT}`);
});
