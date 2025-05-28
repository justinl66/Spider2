#!/usr/bin/env python3
"""
Demo script showing self-retrieval functionality for spider-agent-snow
"""

import os
import sys
import tempfile
import json

# Add the spider_agent module to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from spider_agent.self_retrieval import AnalogicalPrompter, DatabaseContextExtractor

def demo_self_retrieval():
    """Demonstrate self-retrieval functionality with a real example."""
    
    print("🚀 Spider-Agent-Snow Self-Retrieval Demo")
    print("=" * 60)
    
    # Example task from spider2-snow.jsonl
    task_config = {
        "instance_id": "demo_example",
        "instruction": "Find the top 5 customers by total purchase amount in the last year, including their email addresses and registration dates.",
        "db_id": "ECOMMERCE",
        "type": "Snowflake"
    }
    
    print("📋 Task Configuration:")
    print(f"   Instruction: {task_config['instruction']}")
    print(f"   Database: {task_config['db_id']}")
    print(f"   Type: {task_config['type']}")
    print()
    
    # Create mock database context for demo
    with tempfile.TemporaryDirectory() as workspace_dir:
        print("🗄️  Setting up mock database context...")
        
        # Create database directory structure
        db_dir = os.path.join(workspace_dir, f"{task_config['db_id']}_DB")
        os.makedirs(db_dir, exist_ok=True)
        
        # Create mock DDL
        ddl_content = """CREATE TABLE customers (
    customer_id INT PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20),
    registration_date DATE NOT NULL,
    last_login_date TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active'
);

CREATE TABLE orders (
    order_id INT PRIMARY KEY,
    customer_id INT NOT NULL,
    order_date DATE NOT NULL,
    order_total DECIMAL(10,2) NOT NULL,
    order_status VARCHAR(20) DEFAULT 'pending',
    shipping_address TEXT,
    payment_method VARCHAR(30),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE order_items (
    item_id INT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(8,2) NOT NULL,
    discount_amount DECIMAL(6,2) DEFAULT 0.00,
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);

CREATE TABLE products (
    product_id INT PRIMARY KEY,
    product_name VARCHAR(200) NOT NULL,
    category VARCHAR(50),
    price DECIMAL(8,2) NOT NULL,
    stock_quantity INT DEFAULT 0,
    description TEXT
);"""
        
        with open(os.path.join(db_dir, "DDL.csv"), 'w') as f:
            f.write(ddl_content)
        
        # Create mock README
        readme_content = """# E-commerce Database Schema

## Overview
This database contains customer transaction data for an online retail platform.

## Key Tables

### customers
- Contains customer profile information
- Primary key: customer_id
- Includes contact details and registration info

### orders
- Main transaction records
- Links to customers via customer_id
- Contains order totals and status

### order_items
- Individual line items for each order
- Contains product details and pricing
- Enables detailed sales analysis

### products
- Product catalog information
- Contains pricing and inventory data

## Common Queries
- Customer analysis: JOIN customers with orders
- Sales reporting: Aggregate order_total by time periods
- Product performance: Analyze order_items with products

## Date Ranges
- Historical data from 2020-present
- Most analysis focuses on recent 12-month periods
- Use order_date for temporal filtering
"""
        
        with open(os.path.join(workspace_dir, "README.md"), 'w') as f:
            f.write(readme_content)
        
        print("   ✅ Database schema and documentation created")
        print()
        
        # Initialize components
        print("🤖 Initializing Self-Retrieval Components...")
        extractor = DatabaseContextExtractor(workspace_dir=workspace_dir)
        prompter = AnalogicalPrompter(model="gpt-4", max_tokens=2000, temperature=0.3)
        print("   ✅ Components initialized")
        print()
        
        # Extract database context
        print("📊 Extracting Database Context...")
        db_context = extractor.extract_database_context(task_config)
        print(f"   ✅ Extracted {len(db_context)} characters of context")
        print()
        
        # Show context preview
        print("📋 Database Context Preview:")
        print("-" * 40)
        context_preview = db_context[:500] + "..." if len(db_context) > 500 else db_context
        print(context_preview)
        print("-" * 40)
        print()
        
        # Create analogical prompt
        print("🎯 Creating Analogical Prompt...")
        analogical_prompt = prompter._create_analogical_prompt(
            task_config["instruction"], 
            db_context, 
            num_examples=3
        )
        print(f"   ✅ Created prompt ({len(analogical_prompt)} characters)")
        print()
        
        # Show prompt preview
        print("📝 Analogical Prompt Preview:")
        print("-" * 40)
        prompt_preview = analogical_prompt[:800] + "..." if len(analogical_prompt) > 800 else analogical_prompt
        print(prompt_preview)
        print("-" * 40)
        print()
        
        # Simulate example generation (without actual LLM call)
        print("🔄 Simulating Example Generation...")
        mock_examples = [
            {
                "problem": "Find the top 10 products by total sales revenue in the current year",
                "solution": """SELECT p.product_name, 
       SUM(oi.quantity * oi.unit_price) as total_revenue
FROM products p
JOIN order_items oi ON p.product_id = oi.product_id  
JOIN orders o ON oi.order_id = o.order_id
WHERE YEAR(o.order_date) = YEAR(CURRENT_DATE)
GROUP BY p.product_id, p.product_name
ORDER BY total_revenue DESC
LIMIT 10""",
                "explanation": "Uses JOINs to connect products with sales data, aggregates revenue with SUM, filters by current year, and limits results",
                "relevance": "Similar pattern: aggregation of financial data with TOP N ranking and date filtering"
            },
            {
                "problem": "Get the highest spending customers in each quarter of 2023",
                "solution": """SELECT QUARTER(o.order_date) as quarter,
       c.customer_id,
       CONCAT(c.first_name, ' ', c.last_name) as customer_name,
       c.email,
       SUM(o.order_total) as total_spent
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE YEAR(o.order_date) = 2023
GROUP BY QUARTER(o.order_date), c.customer_id, c.first_name, c.last_name, c.email
ORDER BY quarter, total_spent DESC""",
                "explanation": "Joins customers with orders, aggregates spending by customer and quarter, includes customer details",
                "relevance": "Directly relevant: customer spending analysis with contact information and temporal filtering"
            },
            {
                "problem": "Find customers who have made purchases in the last 30 days along with their total order count",
                "solution": """SELECT c.customer_id,
       c.first_name,
       c.last_name, 
       c.email,
       c.registration_date,
       COUNT(o.order_id) as total_orders,
       SUM(o.order_total) as total_spent
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.order_date >= CURRENT_DATE - INTERVAL 30 DAY
GROUP BY c.customer_id, c.first_name, c.last_name, c.email, c.registration_date
ORDER BY total_spent DESC""",
                "explanation": "Uses date arithmetic for recent purchases, aggregates both count and sum metrics, includes full customer profile",
                "relevance": "Very relevant: recent customer activity analysis with profile information and spending aggregation"
            }
        ]
        
        print("   ✅ Generated 3 analogical examples")
        print()
        
        # Format examples
        print("📋 Formatting Examples for Prompt...")
        formatted_examples = prompter.format_examples_for_prompt(mock_examples)
        print(f"   ✅ Formatted examples ({len(formatted_examples)} characters)")
        print()
        
        # Show formatted examples preview
        print("📝 Formatted Examples Preview:")
        print("-" * 40)
        examples_preview = formatted_examples[:1000] + "..." if len(formatted_examples) > 1000 else formatted_examples
        print(examples_preview)
        print("-" * 40)
        print()
        
        # Create enhanced instruction
        print("🚀 Creating Enhanced Instruction...")
        analogical_section = f"\n\nRelevant Examples for Analogical Reasoning:\n{formatted_examples}\n"
        enhanced_instruction = analogical_section + task_config["instruction"]
        
        print(f"   ✅ Enhanced instruction created ({len(enhanced_instruction)} characters)")
        print()
        
        # Summary
        print("📊 Self-Retrieval Demo Summary:")
        print("-" * 40)
        print(f"✅ Database context extracted: {len(db_context)} chars")
        print(f"✅ Analogical prompt created: {len(analogical_prompt)} chars") 
        print(f"✅ Examples generated: {len(mock_examples)} examples")
        print(f"✅ Enhanced instruction: {len(enhanced_instruction)} chars")
        print()
        
        print("🎯 The enhanced instruction would now be sent to the spider agent")
        print("   with relevant SQL examples to guide the solution process.")
        print()
        
        print("🚀 Self-retrieval demo completed successfully!")
        print("   Use: python3 run.py --multi_loop --self_retrieval --model gpt-4o")

if __name__ == "__main__":
    demo_self_retrieval()
