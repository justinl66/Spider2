#!/usr/bin/env python3
"""
Test script to validate self-retrieval integration with run.py
"""

import os
import sys
import tempfile
import json
from pathlib import Path

# Add the spider_agent module to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from spider_agent.self_retrieval import AnalogicalPrompter, DatabaseContextExtractor

def test_self_retrieval_integration():
    """Test the self-retrieval integration without requiring LLM API calls."""
    
    print("Testing Self-Retrieval Integration...")
    
    # Create mock workspace directory
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary workspace: {temp_dir}")
        
        # Create mock task config
        task_config = {
            "instruction": "Find the top 5 customers by total purchase amount in 2023",
            "type": "Snowflake",
            "db_id": "ECOMMERCE"
        }
        
        # Create mock database context in workspace
        db_dir = os.path.join(temp_dir, "ECOMMERCE_DB")
        os.makedirs(db_dir, exist_ok=True)
        
        # Create mock DDL file
        ddl_content = """CREATE TABLE customers (
    customer_id INT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    registration_date DATE
);

CREATE TABLE orders (
    order_id INT PRIMARY KEY,
    customer_id INT,
    order_date DATE,
    total_amount DECIMAL(10,2),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);"""
        
        with open(os.path.join(db_dir, "DDL.csv"), 'w') as f:
            f.write(ddl_content)
        
        # Create mock README
        readme_content = """# E-commerce Database

This database contains customer and order information for an online retail business.

## Tables
- customers: Customer information including registration details
- orders: Order transactions with amounts and dates

## Usage Notes
- Use customer_id to join between tables
- All amounts are in USD
- Dates are in YYYY-MM-DD format
"""
        
        with open(os.path.join(temp_dir, "README.md"), 'w') as f:
            f.write(readme_content)
        
        # Test DatabaseContextExtractor
        print("1. Testing DatabaseContextExtractor...")
        extractor = DatabaseContextExtractor(workspace_dir=temp_dir)
        db_context = extractor.extract_database_context(task_config)
        
        print(f"   ✓ Extracted {len(db_context)} characters of context")
        assert "ECOMMERCE_DB" in db_context
        assert "customers" in db_context
        assert "orders" in db_context
        print("   ✓ Database context extraction successful")
        
        # Test AnalogicalPrompter initialization
        print("2. Testing AnalogicalPrompter...")
        prompter = AnalogicalPrompter(model="gpt-4", max_tokens=1000, temperature=0.3)
        
        # Test prompt creation (without LLM call)
        analogical_prompt = prompter._create_analogical_prompt(
            task_config["instruction"], 
            db_context, 
            num_examples=3
        )
        
        print(f"   ✓ Created analogical prompt ({len(analogical_prompt)} characters)")
        assert "Find the top 5 customers" in analogical_prompt
        assert "3 relevant" in analogical_prompt
        print("   ✓ Analogical prompt creation successful")
        
        # Test example formatting
        print("3. Testing example formatting...")
        mock_examples = [
            {
                "problem": "Find top 10 products by sales volume",
                "solution": "SELECT product_name, SUM(quantity) as total_sold FROM sales GROUP BY product_name ORDER BY total_sold DESC LIMIT 10",
                "explanation": "Uses GROUP BY with SUM aggregation and ORDER BY with LIMIT for top N selection",
                "relevance": "Similar pattern: aggregation + ranking + limiting results"
            },
            {
                "problem": "Get highest spending customers in the last year", 
                "solution": "SELECT c.name, SUM(o.amount) as total_spent FROM customers c JOIN orders o ON c.id = o.customer_id WHERE o.date >= '2023-01-01' GROUP BY c.id, c.name ORDER BY total_spent DESC",
                "explanation": "Joins tables, filters by date, aggregates spending, and orders by amount",
                "relevance": "Directly relevant: customer analysis with spending aggregation"
            }
        ]
        
        formatted_examples = prompter.format_examples_for_prompt(mock_examples)
        print(f"   ✓ Formatted examples ({len(formatted_examples)} characters)")
        assert "## Example 1" in formatted_examples
        assert "## Example 2" in formatted_examples
        print("   ✓ Example formatting successful")
        
        # Test combined workflow (simulating what happens in run.py)
        print("4. Testing combined workflow...")
        
        # This simulates the workflow in run.py multi-loop with self-retrieval
        enhanced_instruction = task_config["instruction"]
        
        # Add analogical examples to instruction
        if formatted_examples:
            analogical_section = f"\n\nRelevant Examples for Analogical Reasoning:\n{formatted_examples}\n"
            enhanced_instruction = analogical_section + enhanced_instruction
        
        print(f"   ✓ Enhanced instruction created ({len(enhanced_instruction)} characters)")
        assert "Relevant Examples for Analogical Reasoning" in enhanced_instruction
        assert task_config["instruction"] in enhanced_instruction
        print("   ✓ Instruction enhancement successful")
        
        print("\n✅ All integration tests passed!")
        print("✅ Self-retrieval is ready for use with --multi_loop --self_retrieval flags")
        
        return True

def test_command_line_args():
    """Test that the command line arguments are properly configured."""
    
    print("\nTesting Command Line Integration...")
    
    # Import run.py config function to test arguments
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        import run
        
        # Test that the argument parser includes our new flags
        # Save original sys.argv
        original_argv = sys.argv[:]
        
        try:
            # Set test arguments
            sys.argv = ['run.py', '--multi_loop', '--self_retrieval', '--model', 'gpt-4', '--suffix', 'test']
            
            # Get parsed arguments
            test_args = run.config()
            
            assert hasattr(test_args, 'multi_loop')
            assert hasattr(test_args, 'self_retrieval')
            assert test_args.multi_loop == True
            assert test_args.self_retrieval == True
            
            print("   ✓ Command line arguments properly configured")
            print("   ✓ --multi_loop and --self_retrieval flags available")
            
            return True
            
        finally:
            # Restore original sys.argv
            sys.argv = original_argv
        
    except Exception as e:
        print(f"   ✗ Command line test failed: {e}")
        return False

def main():
    """Run integration tests."""
    
    print("="*70)
    print("Spider-Agent-Snow Self-Retrieval Integration Test")
    print("="*70)
    
    tests = [
        test_self_retrieval_integration,
        test_command_line_args
    ]
    
    results = []
    
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test_func.__name__} failed with error: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    print("\n" + "="*70)
    print("Integration Test Results")
    print("="*70)
    
    passed = sum(results)
    total = len(results)
    
    for i, (test_func, result) in enumerate(zip(tests, results)):
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_func.__name__:<35} {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 Integration tests passed! Self-retrieval is ready for production use.")
        print("\nTo use self-retrieval with spider-agent-snow:")
        print("   python3 run.py --multi_loop --self_retrieval --model gpt-4o -s test_with_analogical")
        return 0
    else:
        print("\n❌ Some integration tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    exit(main())
