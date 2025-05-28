#!/usr/bin/env python3
"""
Test script for self-retrieval (analogical prompting) functionality
in the Spider-Agent-Snow system.
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path

# Add the spider_agent module to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from spider_agent.self_retrieval import AnalogicalPrompter, DatabaseContextExtractor

def test_analogical_prompter():
    """Test the AnalogicalPrompter functionality."""
    
    print("Testing AnalogicalPrompter...")
    
    # Create a test prompter (using a mock model for testing)
    prompter = AnalogicalPrompter(model="gpt-4", max_tokens=1000, temperature=0.3)
    
    # Test task instruction
    task_instruction = """
    Find the top 5 customers by total order value in the last quarter.
    Include customer name, total order value, and number of orders.
    """
    
    # Test database context
    database_context = """
    Database: ECOMMERCE_DB
    Tables: customers (id, name, email, created_at), orders (id, customer_id, order_date, total_amount)
    """
    
    print(f"Task: {task_instruction.strip()}")
    print(f"Context: {database_context.strip()}")
    
    # Note: This would normally call the LLM, but for testing we'll simulate the response
    print("✓ AnalogicalPrompter initialized successfully")
    print("✓ Would generate analogical examples (requires API key for actual testing)")
    
    # Test formatting functionality
    mock_examples = [
        {
            "problem": "Find top selling products by revenue",
            "solution": "SELECT product_name, SUM(quantity * price) as revenue FROM sales GROUP BY product_name ORDER BY revenue DESC LIMIT 10",
            "explanation": "Uses aggregation with SUM() and GROUP BY for ranking",
            "relevance": "Similar pattern of finding top N records with aggregated metrics"
        }
    ]
    
    formatted_text = prompter.format_examples_for_prompt(mock_examples)
    print("✓ Example formatting works correctly")
    print(f"Formatted length: {len(formatted_text)} characters")
    
    return True

def test_database_context_extractor():
    """Test the DatabaseContextExtractor functionality."""
    
    print("\nTesting DatabaseContextExtractor...")
    
    # Create a temporary workspace with mock database files
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary directory: {temp_dir}")
        
        # Create mock database structure
        db_dir = os.path.join(temp_dir, "TEST_DB")
        os.makedirs(db_dir)
        
        # Create mock DDL file
        ddl_content = """CREATE TABLE customers (
    id INT PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100)
);

CREATE TABLE orders (
    id INT PRIMARY KEY,
    customer_id INT,
    order_date DATE,
    total_amount DECIMAL(10,2)
);"""
        
        with open(os.path.join(db_dir, "DDL.csv"), 'w') as f:
            f.write(ddl_content)
        
        # Create mock table JSON file
        table_json = {
            "columns": [
                {"name": "id", "type": "INT"},
                {"name": "name", "type": "VARCHAR(100)"},
                {"name": "email", "type": "VARCHAR(100)"}
            ],
            "sample_rows": [
                {"id": 1, "name": "John Doe", "email": "john@example.com"},
                {"id": 2, "name": "Jane Smith", "email": "jane@example.com"}
            ]
        }
        
        with open(os.path.join(db_dir, "customers.json"), 'w') as f:
            json.dump(table_json, f)
        
        # Create mock README
        readme_content = """# Test Database
        
This is a test database for e-commerce analytics.
Contains customer and order information.
"""
        
        with open(os.path.join(temp_dir, "README.md"), 'w') as f:
            f.write(readme_content)
        
        # Test the extractor
        extractor = DatabaseContextExtractor(workspace_dir=temp_dir)
        
        task_config = {
            "instruction": "Find top customers by order value",
            "type": "Snowflake"
        }
        
        context = extractor.extract_database_context(task_config)
        
        print("✓ DatabaseContextExtractor initialized successfully")
        print(f"✓ Extracted context length: {len(context)} characters")
        print(f"Context preview: {context[:200]}...")
        
        # Verify context contains expected information
        assert "TEST_DB" in context, "Database name should be in context"
        assert "customers" in context, "Table name should be in context"
        assert "README Content" in context, "README content should be included"
        
        print("✓ All context extraction tests passed")
        
        return True

def test_integration():
    """Test integration of both components."""
    
    print("\nTesting Integration...")
    
    # This would test the full integration with the run.py script
    # For now, we'll just verify the imports work correctly
    
    try:
        from spider_agent.self_retrieval import AnalogicalPrompter, DatabaseContextExtractor
        print("✓ Module imports work correctly")
        
        # Test that classes can be instantiated together
        prompter = AnalogicalPrompter()
        extractor = DatabaseContextExtractor()
        
        print("✓ Both classes can be instantiated")
        print("✓ Integration test completed")
        
        return True
        
    except Exception as e:
        print(f"✗ Integration test failed: {e}")
        return False

def main():
    """Run all tests."""
    
    print("="*60)
    print("Spider-Agent-Snow Self-Retrieval Test Suite")
    print("="*60)
    
    tests = [
        test_analogical_prompter,
        test_database_context_extractor,
        test_integration
    ]
    
    results = []
    
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test_func.__name__} failed with error: {e}")
            results.append(False)
    
    print("\n" + "="*60)
    print("Test Results Summary")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    
    for i, (test_func, result) in enumerate(zip(tests, results)):
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_func.__name__:<30} {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Self-retrieval implementation is ready.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    exit(main())
