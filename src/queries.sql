-- Funnel counts by event
SELECT event_name, COUNT(DISTINCT user_id) AS users
FROM events
GROUP BY event_name
ORDER BY users DESC;

-- Day N retention (example: day 7)
WITH signups AS (
  SELECT user_id, DATE(event_time) AS signup_date
  FROM events
  WHERE event_name = 'signup'
),
returns AS (
  SELECT user_id, DATE(event_time) AS return_date
  FROM events
  WHERE event_name = 'login'
)
SELECT
  COUNT(DISTINCT s.user_id) AS signed_up,
  COUNT(DISTINCT r.user_id) AS returned_day_7
FROM signups s
LEFT JOIN returns r
  ON s.user_id = r.user_id
 AND r.return_date = DATE(s.signup_date, '+7 day');

-- Retention curve (days since signup, 0-14)
WITH signups AS (
  SELECT user_id, DATE(event_time) AS signup_date
  FROM events
  WHERE event_name = 'signup'
),
logins AS (
  SELECT user_id, DATE(event_time) AS login_date
  FROM events
  WHERE event_name = 'login'
),
joined AS (
  SELECT
    s.user_id,
    CAST(julianday(l.login_date) - julianday(s.signup_date) AS INTEGER) AS day
  FROM signups s
  JOIN logins l ON s.user_id = l.user_id
)
SELECT
  day,
  COUNT(DISTINCT user_id) AS returned_users
FROM joined
GROUP BY day
ORDER BY day;
