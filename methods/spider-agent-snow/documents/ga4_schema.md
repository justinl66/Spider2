# Google Analytics 4 (GA4) Schema - Text-to-SQL Examples

This document contains common Google Analytics 4 questions and their corresponding SQL queries for BigQuery exports.

## Event Tracking and User Behavior

**Question:** How many page views did we have in the last 7 days?
**SQL:**
```sql
SELECT 
    COUNT(*) as total_page_views
FROM `project.dataset.events_*`
WHERE event_name = 'page_view'
  AND _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY))
  AND FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY));
```

**Question:** What are the top 10 most viewed pages this month?
**SQL:**
```sql
SELECT 
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_location') as page_url,
    COUNT(*) as page_views
FROM `project.dataset.events_*`
WHERE event_name = 'page_view'
  AND _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', DATE_TRUNC(CURRENT_DATE(), MONTH))
  AND FORMAT_DATE('%Y%m%d', CURRENT_DATE())
GROUP BY page_url
ORDER BY page_views DESC
LIMIT 10;
```

**Question:** Calculate the average session duration by traffic source
**SQL:**
```sql
WITH session_data AS (
  SELECT 
    user_pseudo_id,
    ga_session_id,
    traffic_source.source as source,
    MIN(event_timestamp) as session_start,
    MAX(event_timestamp) as session_end
  FROM `project.dataset.events_*`
  WHERE _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY))
    AND FORMAT_DATE('%Y%m%d', CURRENT_DATE())
  GROUP BY user_pseudo_id, ga_session_id, source
)
SELECT 
    source,
    AVG((session_end - session_start) / 1000000) as avg_session_duration_seconds,
    COUNT(*) as total_sessions
FROM session_data
WHERE source IS NOT NULL
GROUP BY source
ORDER BY avg_session_duration_seconds DESC;
```

## E-commerce Tracking

**Question:** What is the total revenue from purchases this month?
**SQL:**
```sql
SELECT 
    SUM((SELECT value.double_value FROM UNNEST(event_params) WHERE key = 'value')) as total_revenue
FROM `project.dataset.events_*`
WHERE event_name = 'purchase'
  AND _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', DATE_TRUNC(CURRENT_DATE(), MONTH))
  AND FORMAT_DATE('%Y%m%d', CURRENT_DATE());
```

**Question:** Show daily conversion rate from add_to_cart to purchase
**SQL:**
```sql
WITH daily_events AS (
  SELECT 
    PARSE_DATE('%Y%m%d', event_date) as date,
    event_name,
    user_pseudo_id
  FROM `project.dataset.events_*`
  WHERE event_name IN ('add_to_cart', 'purchase')
    AND _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY))
    AND FORMAT_DATE('%Y%m%d', CURRENT_DATE())
),
daily_metrics AS (
  SELECT 
    date,
    COUNTIF(event_name = 'add_to_cart') as add_to_cart_events,
    COUNTIF(event_name = 'purchase') as purchase_events
  FROM daily_events
  GROUP BY date
)
SELECT 
    date,
    add_to_cart_events,
    purchase_events,
    SAFE_DIVIDE(purchase_events, add_to_cart_events) * 100 as conversion_rate_pct
FROM daily_metrics
ORDER BY date DESC;
```

**Question:** Which products generate the most revenue?
**SQL:**
```sql
SELECT 
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'item_name') as product_name,
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'item_category') as category,
    SUM((SELECT value.double_value FROM UNNEST(event_params) WHERE key = 'value')) as total_revenue,
    COUNT(*) as purchase_events
FROM `project.dataset.events_*`
WHERE event_name = 'purchase'
  AND _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY))
  AND FORMAT_DATE('%Y%m%d', CURRENT_DATE())
GROUP BY product_name, category
HAVING product_name IS NOT NULL
ORDER BY total_revenue DESC
LIMIT 20;
```

## User Acquisition and Demographics

**Question:** What are our top traffic sources by user count?
**SQL:**
```sql
SELECT 
    traffic_source.source,
    traffic_source.medium,
    COUNT(DISTINCT user_pseudo_id) as unique_users,
    COUNT(*) as total_events
FROM `project.dataset.events_*`
WHERE _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY))
  AND FORMAT_DATE('%Y%m%d', CURRENT_DATE())
GROUP BY traffic_source.source, traffic_source.medium
ORDER BY unique_users DESC
LIMIT 15;
```

**Question:** Show user demographics breakdown by country and device
**SQL:**
```sql
SELECT 
    geo.country,
    device.category as device_category,
    COUNT(DISTINCT user_pseudo_id) as unique_users,
    COUNTIF(event_name = 'first_visit') as new_users
FROM `project.dataset.events_*`
WHERE _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY))
  AND FORMAT_DATE('%Y%m%d', CURRENT_DATE())
GROUP BY geo.country, device.category
ORDER BY unique_users DESC
LIMIT 20;
```

**Question:** Calculate new vs returning user ratio by week
**SQL:**
```sql
WITH user_first_seen AS (
  SELECT 
    user_pseudo_id,
    MIN(PARSE_DATE('%Y%m%d', event_date)) as first_seen_date
  FROM `project.dataset.events_*`
  WHERE _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY))
    AND FORMAT_DATE('%Y%m%d', CURRENT_DATE())
  GROUP BY user_pseudo_id
),
weekly_users AS (
  SELECT 
    DATE_TRUNC(PARSE_DATE('%Y%m%d', e.event_date), WEEK) as week,
    e.user_pseudo_id,
    CASE 
      WHEN ufs.first_seen_date = PARSE_DATE('%Y%m%d', e.event_date) THEN 'New'
      ELSE 'Returning'
    END as user_type
  FROM `project.dataset.events_*` e
  JOIN user_first_seen ufs ON e.user_pseudo_id = ufs.user_pseudo_id
  WHERE e._TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY))
    AND FORMAT_DATE('%Y%m%d', CURRENT_DATE())
  GROUP BY week, e.user_pseudo_id, user_type
)
SELECT 
    week,
    COUNTIF(user_type = 'New') as new_users,
    COUNTIF(user_type = 'Returning') as returning_users,
    SAFE_DIVIDE(COUNTIF(user_type = 'New'), COUNT(*)) * 100 as new_user_percentage
FROM weekly_users
GROUP BY week
ORDER BY week DESC;
```

## Custom Events and Conversions

**Question:** What is the completion rate for our signup funnel?
**SQL:**
```sql
WITH funnel_events AS (
  SELECT 
    user_pseudo_id,
    COUNTIF(event_name = 'signup_start') as signup_starts,
    COUNTIF(event_name = 'signup_complete') as signup_completions
  FROM `project.dataset.events_*`
  WHERE event_name IN ('signup_start', 'signup_complete')
    AND _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY))
    AND FORMAT_DATE('%Y%m%d', CURRENT_DATE())
  GROUP BY user_pseudo_id
)
SELECT 
    SUM(signup_starts) as total_signup_starts,
    SUM(signup_completions) as total_signup_completions,
    SAFE_DIVIDE(SUM(signup_completions), SUM(signup_starts)) * 100 as completion_rate_pct
FROM funnel_events;
```

**Question:** Track video engagement metrics by video title
**SQL:**
```sql
SELECT 
    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'video_title') as video_title,
    COUNTIF(event_name = 'video_start') as video_starts,
    COUNTIF(event_name = 'video_complete') as video_completions,
    AVG(CASE 
      WHEN event_name = 'video_progress' 
      THEN (SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'video_percent')
    END) as avg_completion_percentage
FROM `project.dataset.events_*`
WHERE event_name IN ('video_start', 'video_complete', 'video_progress')
  AND _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY))
  AND FORMAT_DATE('%Y%m%d', CURRENT_DATE())
GROUP BY video_title
HAVING video_title IS NOT NULL
ORDER BY video_starts DESC;
```

## Advanced Analytics

**Question:** Calculate user cohort retention rates by registration month
**SQL:**
```sql
WITH user_cohorts AS (
  SELECT 
    user_pseudo_id,
    DATE_TRUNC(MIN(PARSE_DATE('%Y%m%d', event_date)), MONTH) as cohort_month
  FROM `project.dataset.events_*`
  WHERE event_name = 'first_visit'
    AND _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 365 DAY))
    AND FORMAT_DATE('%Y%m%d', CURRENT_DATE())
  GROUP BY user_pseudo_id
),
user_activities AS (
  SELECT 
    uc.cohort_month,
    uc.user_pseudo_id,
    DATE_TRUNC(PARSE_DATE('%Y%m%d', e.event_date), MONTH) as activity_month
  FROM user_cohorts uc
  JOIN `project.dataset.events_*` e ON uc.user_pseudo_id = e.user_pseudo_id
  WHERE e._TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 365 DAY))
    AND FORMAT_DATE('%Y%m%d', CURRENT_DATE())
  GROUP BY uc.cohort_month, uc.user_pseudo_id, activity_month
)
SELECT 
    cohort_month,
    activity_month,
    COUNT(DISTINCT user_pseudo_id) as active_users,
    DATE_DIFF(activity_month, cohort_month, MONTH) as month_number
FROM user_activities
GROUP BY cohort_month, activity_month
ORDER BY cohort_month, month_number;
```

**Question:** Find the most common user journey paths (top 3 events sequence)
**SQL:**
```sql
WITH user_sessions AS (
  SELECT 
    user_pseudo_id,
    ga_session_id,
    event_name,
    event_timestamp,
    ROW_NUMBER() OVER (PARTITION BY user_pseudo_id, ga_session_id ORDER BY event_timestamp) as event_order
  FROM `project.dataset.events_*`
  WHERE _TABLE_SUFFIX BETWEEN FORMAT_DATE('%Y%m%d', DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY))
    AND FORMAT_DATE('%Y%m%d', CURRENT_DATE())
    AND event_name NOT IN ('session_start', 'first_visit')
),
event_sequences AS (
  SELECT 
    user_pseudo_id,
    ga_session_id,
    STRING_AGG(event_name, ' -> ' ORDER BY event_order) as event_sequence
  FROM user_sessions
  WHERE event_order <= 3
  GROUP BY user_pseudo_id, ga_session_id
)
SELECT 
    event_sequence,
    COUNT(*) as frequency
FROM event_sequences
WHERE event_sequence IS NOT NULL
GROUP BY event_sequence
ORDER BY frequency DESC
LIMIT 20;
```