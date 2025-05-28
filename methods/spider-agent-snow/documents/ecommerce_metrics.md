# E-commerce Metrics - Text-to-SQL Examples

This document contains common e-commerce business questions and their corresponding SQL queries for training the RAG system.

## Revenue and Sales Metrics

**Question:** What is the total revenue for the current month?
**SQL:**
```sql
SELECT SUM(order_total) as total_revenue
FROM orders 
WHERE order_date >= DATE_TRUNC('month', CURRENT_DATE)
  AND order_date < DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month';
```

**Question:** Show me the daily revenue for the last 30 days
**SQL:**
```sql
SELECT 
    DATE(order_date) as date,
    SUM(order_total) as daily_revenue
FROM orders 
WHERE order_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(order_date)
ORDER BY date DESC;
```

**Question:** What are the top 10 best-selling products by quantity?
**SQL:**
```sql
SELECT 
    p.product_name,
    SUM(oi.quantity) as total_quantity_sold
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
GROUP BY p.product_id, p.product_name
ORDER BY total_quantity_sold DESC
LIMIT 10;
```

**Question:** Calculate the average order value for each month this year
**SQL:**
```sql
SELECT 
    DATE_TRUNC('month', order_date) as month,
    AVG(order_total) as avg_order_value,
    COUNT(*) as order_count
FROM orders 
WHERE EXTRACT(YEAR FROM order_date) = EXTRACT(YEAR FROM CURRENT_DATE)
GROUP BY DATE_TRUNC('month', order_date)
ORDER BY month;
```

## Customer Analytics

**Question:** How many new customers did we acquire last month?
**SQL:**
```sql
SELECT COUNT(DISTINCT customer_id) as new_customers
FROM customers 
WHERE created_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
  AND created_date < DATE_TRUNC('month', CURRENT_DATE);
```

**Question:** What is the customer lifetime value for customers who joined this year?
**SQL:**
```sql
SELECT 
    c.customer_id,
    c.email,
    SUM(o.order_total) as lifetime_value,
    COUNT(o.order_id) as total_orders
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE EXTRACT(YEAR FROM c.created_date) = EXTRACT(YEAR FROM CURRENT_DATE)
GROUP BY c.customer_id, c.email
ORDER BY lifetime_value DESC;
```

**Question:** Show customer retention rate by cohort month
**SQL:**
```sql
WITH cohort_data AS (
    SELECT 
        customer_id,
        DATE_TRUNC('month', MIN(order_date)) as cohort_month
    FROM orders
    GROUP BY customer_id
),
customer_activities AS (
    SELECT 
        cd.cohort_month,
        DATE_TRUNC('month', o.order_date) as order_month,
        COUNT(DISTINCT o.customer_id) as customers
    FROM cohort_data cd
    JOIN orders o ON cd.customer_id = o.customer_id
    GROUP BY cd.cohort_month, DATE_TRUNC('month', o.order_date)
)
SELECT 
    cohort_month,
    order_month,
    customers,
    EXTRACT(MONTH FROM AGE(order_month, cohort_month)) as period_number
FROM customer_activities
ORDER BY cohort_month, period_number;
```

## Product Performance

**Question:** Which product categories have the highest profit margins?
**SQL:**
```sql
SELECT 
    p.category,
    SUM(oi.quantity * (oi.unit_price - p.cost_price)) as total_profit,
    SUM(oi.quantity * oi.unit_price) as total_revenue,
    (SUM(oi.quantity * (oi.unit_price - p.cost_price)) / SUM(oi.quantity * oi.unit_price)) * 100 as profit_margin_pct
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
GROUP BY p.category
ORDER BY profit_margin_pct DESC;
```

**Question:** Find products that are frequently bought together
**SQL:**
```sql
SELECT 
    p1.product_name as product_1,
    p2.product_name as product_2,
    COUNT(*) as times_bought_together
FROM order_items oi1
JOIN order_items oi2 ON oi1.order_id = oi2.order_id 
    AND oi1.product_id < oi2.product_id
JOIN products p1 ON oi1.product_id = p1.product_id
JOIN products p2 ON oi2.product_id = p2.product_id
GROUP BY p1.product_id, p1.product_name, p2.product_id, p2.product_name
HAVING COUNT(*) >= 5
ORDER BY times_bought_together DESC
LIMIT 20;
```

## Inventory and Stock

**Question:** Which products are running low on inventory?
**SQL:**
```sql
SELECT 
    product_name,
    current_stock,
    reorder_level,
    (current_stock - reorder_level) as stock_difference
FROM products 
WHERE current_stock <= reorder_level
ORDER BY stock_difference ASC;
```

**Question:** Calculate inventory turnover rate for each product category
**SQL:**
```sql
SELECT 
    p.category,
    SUM(oi.quantity) as units_sold,
    AVG(p.current_stock) as avg_inventory,
    CASE 
        WHEN AVG(p.current_stock) > 0 
        THEN SUM(oi.quantity) / AVG(p.current_stock)
        ELSE 0 
    END as turnover_rate
FROM products p
LEFT JOIN order_items oi ON p.product_id = oi.product_id
JOIN orders o ON oi.order_id = o.order_id
WHERE o.order_date >= CURRENT_DATE - INTERVAL '365 days'
GROUP BY p.category
ORDER BY turnover_rate DESC;
```

## Geographic Analysis

**Question:** What are the top 5 states by total revenue?
**SQL:**
```sql
SELECT 
    shipping_state,
    SUM(order_total) as total_revenue,
    COUNT(*) as order_count,
    AVG(order_total) as avg_order_value
FROM orders 
WHERE shipping_state IS NOT NULL
GROUP BY shipping_state
ORDER BY total_revenue DESC
LIMIT 5;
```

**Question:** Compare revenue growth between regions year over year
**SQL:**
```sql
SELECT 
    shipping_region,
    EXTRACT(YEAR FROM order_date) as year,
    SUM(order_total) as revenue,
    LAG(SUM(order_total)) OVER (PARTITION BY shipping_region ORDER BY EXTRACT(YEAR FROM order_date)) as prev_year_revenue,
    ((SUM(order_total) - LAG(SUM(order_total)) OVER (PARTITION BY shipping_region ORDER BY EXTRACT(YEAR FROM order_date))) / 
     LAG(SUM(order_total)) OVER (PARTITION BY shipping_region ORDER BY EXTRACT(YEAR FROM order_date))) * 100 as growth_rate_pct
FROM orders 
WHERE shipping_region IS NOT NULL
GROUP BY shipping_region, EXTRACT(YEAR FROM order_date)
ORDER BY shipping_region, year;
```