# RAG Knowledge Base for Spider-Agent-Snow

This directory contains text-to-SQL examples and documentation to enhance the RAG (Retrieval-Augmented Generation) system's ability to generate accurate SQL queries.

## Contents

- `ecommerce_metrics.md`: E-commerce business metrics and SQL examples
- `ga4_schema.md`: Google Analytics 4 schema and query patterns
- `add_example_queries.py`: Script to programmatically add new example pairs

## Usage

These documents are automatically processed by the RAG system when using the `--use_rag` flag. The system will retrieve relevant examples based on the input question to provide better context for SQL generation.

## Example Format

Each document contains pairs of natural language questions and their corresponding SQL queries:

```
**Question:** What is the total revenue for last month?
**SQL:**
```sql
SELECT SUM(order_total) as total_revenue
FROM orders 
WHERE order_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
  AND order_date < DATE_TRUNC('month', CURRENT_DATE);
```

## Contributing

When adding new examples, ensure they:
- Cover various SQL complexity levels
- Include common business scenarios
- Use proper SQL formatting
- Provide clear, specific questions