#!/usr/bin/env python3
"""
Script to programmatically add new text-to-SQL example pairs to the RAG knowledge base.

This script provides utilities to:
1. Add new example pairs to existing markdown files
2. Validate SQL syntax
3. Format examples consistently
4. Generate new domain-specific knowledge files

Usage:
    python add_example_queries.py --file ecommerce_metrics.md --question "What is the churn rate?" --sql "SELECT..."
    python add_example_queries.py --create-domain "retail_analytics"
    python add_example_queries.py --validate-all
"""

import argparse
import os
import re
from typing import List, Tuple, Dict
from pathlib import Path

class QueryExampleManager:
    """Manages text-to-SQL example pairs in markdown files."""
    
    def __init__(self, documents_dir: str = None):
        if documents_dir is None:
            documents_dir = os.path.dirname(os.path.abspath(__file__))
        self.documents_dir = Path(documents_dir)
        
    def add_example(self, file_name: str, question: str, sql: str, section: str = None) -> bool:
        """Add a new text-to-SQL example to a markdown file."""
        file_path = self.documents_dir / file_name
        
        if not file_path.exists():
            print(f"File {file_name} does not exist. Creating new file.")
            self._create_new_domain_file(file_name, section or "General Examples")
        
        # Format the new example
        formatted_example = self._format_example(question, sql)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # If section specified, try to add under that section
            if section:
                section_pattern = f"## {section}"
                if section_pattern in content:
                    # Add after the section header
                    content = content.replace(
                        section_pattern,
                        f"{section_pattern}\n\n{formatted_example}\n"
                    )
                else:
                    # Add new section at the end
                    content += f"\n\n## {section}\n\n{formatted_example}\n"
            else:
                # Add at the end of file
                content += f"\n{formatted_example}\n"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"Successfully added example to {file_name}")
            return True
            
        except Exception as e:
            print(f"Error adding example to {file_name}: {e}")
            return False
    
    def _format_example(self, question: str, sql: str) -> str:
        """Format a question-SQL pair consistently."""
        # Clean up SQL formatting
        sql = sql.strip()
        if not sql.startswith('```sql'):
            sql = f"```sql\n{sql}\n```"
        
        return f"**Question:** {question}\n**SQL:**\n{sql}"
    
    def validate_all_examples(self) -> Dict[str, List[str]]:
        """Validate all SQL examples in the documents directory."""
        issues = {}
        
        for md_file in self.documents_dir.glob("*.md"):
            if md_file.name == "README.md":
                continue
                
            file_issues = self._validate_file(md_file)
            if file_issues:
                issues[md_file.name] = file_issues
        
        return issues
    
    def _validate_file(self, file_path: Path) -> List[str]:
        """Validate SQL examples in a single file."""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract all SQL code blocks
            sql_blocks = re.findall(r'```sql\n(.*?)\n```', content, re.DOTALL)
            
            for i, sql in enumerate(sql_blocks):
                sql_issues = self._validate_sql(sql)
                if sql_issues:
                    issues.extend([f"SQL block {i+1}: {issue}" for issue in sql_issues])
        
        except Exception as e:
            issues.append(f"Error reading file: {e}")
        
        return issues
    
    def _validate_sql(self, sql: str) -> List[str]:
        """Basic SQL validation checks."""
        issues = []
        sql = sql.strip().upper()
        
        # Check for basic SQL structure
        if not any(keyword in sql for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'WITH']):
            issues.append("No valid SQL statement keyword found")
        
        # Check for common issues
        if sql.count('(') != sql.count(')'):
            issues.append("Mismatched parentheses")
        
        if sql.count("'") % 2 != 0:
            issues.append("Mismatched single quotes")
        
        if sql.count('"') % 2 != 0:
            issues.append("Mismatched double quotes")
        
        # Check for missing semicolon at end (optional but good practice)
        if not sql.rstrip().endswith(';'):
            issues.append("Missing semicolon at end (recommended)")
        
        return issues
    
    def create_domain_file(self, domain_name: str, description: str = None) -> bool:
        """Create a new domain-specific knowledge file."""
        file_name = f"{domain_name.lower().replace(' ', '_')}.md"
        file_path = self.documents_dir / file_name
        
        if file_path.exists():
            print(f"File {file_name} already exists.")
            return False
        
        return self._create_new_domain_file(file_name, description or f"{domain_name} Examples")
    
    def _create_new_domain_file(self, file_name: str, title: str) -> bool:
        """Create a new markdown file with basic structure."""
        file_path = self.documents_dir / file_name
        
        content = f"""# {title} - Text-to-SQL Examples

This document contains common {title.lower()} questions and their corresponding SQL queries for training the RAG system.

## Getting Started

Add your text-to-SQL examples below using this format:

**Question:** [Your natural language question here]
**SQL:**
```sql
-- Your SQL query here
SELECT * FROM table_name;
```

## Examples

Add your examples in logical sections below.
"""
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Created new domain file: {file_name}")
            return True
        except Exception as e:
            print(f"Error creating file {file_name}: {e}")
            return False
    
    def list_examples(self, file_name: str = None) -> None:
        """List all examples in files."""
        if file_name:
            files = [self.documents_dir / file_name]
        else:
            files = [f for f in self.documents_dir.glob("*.md") if f.name != "README.md"]
        
        for file_path in files:
            if not file_path.exists():
                print(f"File {file_path.name} not found.")
                continue
                
            print(f"\n=== {file_path.name} ===")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract questions
                questions = re.findall(r'\*\*Question:\*\* (.+)', content)
                
                for i, question in enumerate(questions, 1):
                    print(f"{i}. {question}")
                    
            except Exception as e:
                print(f"Error reading {file_path.name}: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Manage text-to-SQL examples for RAG knowledge base"
    )
    
    parser.add_argument('--file', help='Markdown file to add example to')
    parser.add_argument('--question', help='Natural language question')
    parser.add_argument('--sql', help='SQL query')
    parser.add_argument('--section', help='Section to add example under')
    parser.add_argument('--create-domain', help='Create new domain file')
    parser.add_argument('--description', help='Description for new domain')
    parser.add_argument('--validate-all', action='store_true', help='Validate all SQL examples')
    parser.add_argument('--list-examples', nargs='?', const='', help='List examples in file (or all files if not specified)')
    parser.add_argument('--documents-dir', help='Documents directory path')
    
    args = parser.parse_args()
    
    manager = QueryExampleManager(args.documents_dir)
    
    if args.validate_all:
        print("Validating all SQL examples...")
        issues = manager.validate_all_examples()
        
        if issues:
            print("\nValidation issues found:")
            for file_name, file_issues in issues.items():
                print(f"\n{file_name}:")
                for issue in file_issues:
                    print(f"  - {issue}")
        else:
            print("All SQL examples are valid!")
    
    elif args.create_domain:
        manager.create_domain_file(args.create_domain, args.description)
    
    elif args.list_examples is not None:
        file_arg = args.list_examples if args.list_examples else None
        manager.list_examples(file_arg)
    
    elif args.file and args.question and args.sql:
        manager.add_example(args.file, args.question, args.sql, args.section)
    
    else:
        print("Please provide valid arguments. Use --help for usage information.")
        print("\nExample usage:")
        print("  python add_example_queries.py --file ecommerce_metrics.md --question 'What is monthly revenue?' --sql 'SELECT SUM(revenue) FROM orders WHERE...'")
        print("  python add_example_queries.py --create-domain 'Healthcare Analytics'")
        print("  python add_example_queries.py --validate-all")
        print("  python add_example_queries.py --list-examples")

if __name__ == "__main__":
    main()