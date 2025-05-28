# Database context extraction for self-retrieval functionality

import os
import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("spider_agent")

class DatabaseContextExtractor:
    """
    Extracts relevant database schema and context information 
    to support analogical prompting in SQL problem solving.
    """
    
    def __init__(self, workspace_dir: str = "/workspace"):
        self.workspace_dir = workspace_dir
    
    def extract_database_context(self, task_config: Dict[str, Any]) -> str:
        """
        Extract database context from the task environment.
        
        Args:
            task_config: The task configuration containing database information
            
        Returns:
            Formatted string containing relevant database context
        """
        
        context_parts = []
        
        # Extract basic task information
        if 'instruction' in task_config:
            context_parts.append(f"Task Type: {task_config.get('type', 'Unknown')}")
        
        # Look for database schema information in workspace
        schema_info = self._extract_schema_info()
        if schema_info:
            context_parts.append("Database Schema Information:")
            context_parts.append(schema_info)
        
        # Look for README or documentation files
        doc_info = self._extract_documentation()
        if doc_info:
            context_parts.append("Documentation Context:")
            context_parts.append(doc_info)
        
        # Combine all context information
        if context_parts:
            return "\n\n".join(context_parts)
        else:
            return "No specific database context available."
    
    def _extract_schema_info(self) -> str:
        """Extract database schema information from workspace files."""
        
        schema_info = []
        
        # Look for database schema directories
        for item in os.listdir(self.workspace_dir):
            item_path = os.path.join(self.workspace_dir, item)
            if os.path.isdir(item_path):
                # Check if this looks like a database schema directory
                ddl_file = os.path.join(item_path, "DDL.csv")
                if os.path.exists(ddl_file):
                    schema_info.append(f"Database: {item}")
                    
                    # Read DDL information
                    try:
                        with open(ddl_file, 'r') as f:
                            ddl_content = f.read()[:500]  # First 500 chars
                            schema_info.append(f"DDL Preview: {ddl_content}...")
                    except Exception as e:
                        logger.warning(f"Could not read DDL file {ddl_file}: {e}")
                    
                    # List available tables
                    json_files = [f for f in os.listdir(item_path) if f.endswith('.json')]
                    if json_files:
                        table_names = [f.replace('.json', '') for f in json_files[:10]]  # First 10 tables
                        schema_info.append(f"Available Tables: {', '.join(table_names)}")
                        
                        # Sample one table for structure
                        if json_files:
                            sample_table = json_files[0]
                            table_info = self._extract_table_info(os.path.join(item_path, sample_table))
                            if table_info:
                                schema_info.append(f"Sample Table Structure ({sample_table.replace('.json', '')}):")
                                schema_info.append(table_info)
        
        return "\n".join(schema_info) if schema_info else ""
    
    def _extract_table_info(self, table_json_path: str) -> str:
        """Extract information from a single table JSON file."""
        
        try:
            with open(table_json_path, 'r') as f:
                table_data = json.load(f)
            
            info_parts = []
            
            # Extract column information
            if 'columns' in table_data:
                columns = table_data['columns']
                if isinstance(columns, list) and len(columns) > 0:
                    col_info = []
                    for col in columns[:5]:  # First 5 columns
                        if isinstance(col, dict):
                            col_name = col.get('name', 'Unknown')
                            col_type = col.get('type', 'Unknown')
                            col_info.append(f"{col_name} ({col_type})")
                        else:
                            col_info.append(str(col))
                    info_parts.append(f"Columns: {', '.join(col_info)}")
            
            # Extract sample data if available
            if 'sample_rows' in table_data:
                sample_rows = table_data['sample_rows']
                if isinstance(sample_rows, list) and len(sample_rows) > 0:
                    info_parts.append(f"Sample rows available: {len(sample_rows)} rows")
            
            return " | ".join(info_parts)
            
        except Exception as e:
            logger.warning(f"Could not extract table info from {table_json_path}: {e}")
            return ""
    
    def _extract_documentation(self) -> str:
        """Extract relevant documentation from README and other markdown files."""
        
        doc_info = []
        
        # Look for README files
        readme_files = ['README.md', 'readme.md', 'README.txt', 'readme.txt']
        for readme_file in readme_files:
            readme_path = os.path.join(self.workspace_dir, readme_file)
            if os.path.exists(readme_path):
                try:
                    with open(readme_path, 'r') as f:
                        content = f.read()[:1000]  # First 1000 characters
                        doc_info.append(f"README Content: {content}...")
                    break  # Only read one README file
                except Exception as e:
                    logger.warning(f"Could not read README file {readme_path}: {e}")
        
        # Look for other markdown files
        try:
            md_files = [f for f in os.listdir(self.workspace_dir) 
                       if f.endswith('.md') and not f.lower().startswith('readme')]
            if md_files:
                doc_info.append(f"Additional documentation files: {', '.join(md_files[:5])}")
        except Exception as e:
            logger.warning(f"Could not list markdown files: {e}")
        
        return "\n".join(doc_info) if doc_info else ""
    
    def get_table_details(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific table."""
        
        # Search for the table JSON file in database directories
        for item in os.listdir(self.workspace_dir):
            item_path = os.path.join(self.workspace_dir, item)
            if os.path.isdir(item_path):
                table_file = os.path.join(item_path, f"{table_name}.json")
                if os.path.exists(table_file):
                    try:
                        with open(table_file, 'r') as f:
                            return json.load(f)
                    except Exception as e:
                        logger.warning(f"Could not read table file {table_file}: {e}")
        
        return None
