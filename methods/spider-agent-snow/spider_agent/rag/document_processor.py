"""Document processor for Spider-Agent-Snow RAG implementation.

This module provides functionality to process different types of documents
into a format suitable for embedding and retrieval:
1. Database schema files (DDL.csv and JSON files)
2. External knowledge documents (markdown files)
3. Previous SQL queries and results
"""

import os
import json
import csv
import logging
import re
from typing import Dict, List, Optional, Tuple, Union, Any

logger = logging.getLogger("spider_agent.rag")

class DocumentProcessor:
    """Process documents for RAG implementation."""
    
    def __init__(self, 
                chunk_size: int = 512, 
                chunk_overlap: int = 50,
                schema_dir: str = None,
                knowledge_dir: str = None):
        """Initialize the document processor.
        
        Args:
            chunk_size: Size of chunks for text splitting
            chunk_overlap: Overlap between chunks
            schema_dir: Directory containing schema files
            knowledge_dir: Directory containing external knowledge documents
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.schema_dir = schema_dir
        self.knowledge_dir = knowledge_dir

    def process_schema_files(self, db_id: str) -> List[Dict[str, Any]]:
        """Process schema files for a specific database.
        
        Args:
            db_id: Database identifier
            
        Returns:
            List of processed schema documents with metadata
        """
        schema_docs = []
        
        # Path to database schema directory
        db_schema_dir = os.path.join(self.schema_dir, db_id) if self.schema_dir else None
        
        if not db_schema_dir or not os.path.exists(db_schema_dir):
            logger.warning(f"Schema directory for {db_id} not found at {db_schema_dir}")
            return schema_docs
        
        # Process DDL file
        ddl_path = os.path.join(db_schema_dir, "DDL.csv")
        if os.path.exists(ddl_path):
            schema_docs.extend(self._process_ddl_file(ddl_path, db_id))
        
        # Process table JSON files
        json_files = [f for f in os.listdir(db_schema_dir) if f.endswith('.json')]
        for json_file in json_files:
            json_path = os.path.join(db_schema_dir, json_file)
            schema_docs.extend(self._process_table_json(json_path, db_id))
        
        return schema_docs
    
    def _process_ddl_file(self, ddl_path: str, db_id: str) -> List[Dict[str, Any]]:
        """Process a DDL file into document chunks.
        
        Args:
            ddl_path: Path to DDL file
            db_id: Database identifier
            
        Returns:
            List of processed DDL chunks with metadata
        """
        try:
            docs = []
            with open(ddl_path, 'r') as f:
                reader = csv.reader(f)
                headers = next(reader)  # Skip headers
                for row in reader:
                    if row:  # Skip empty rows
                        # Extract table name and DDL statement
                        table_name = row[0] if len(row) > 0 else "unknown"
                        ddl_stmt = row[1] if len(row) > 1 else ""
                        
                        # Create document with metadata
                        doc = {
                            "content": ddl_stmt,
                            "metadata": {
                                "source": "schema_ddl",
                                "db_id": db_id,
                                "table": table_name,
                                "file_path": ddl_path
                            }
                        }
                        docs.append(doc)
            return docs
        except Exception as e:
            logger.error(f"Error processing DDL file {ddl_path}: {e}")
            return []
    
    def _process_table_json(self, json_path: str, db_id: str) -> List[Dict[str, Any]]:
        """Process a table JSON file into document chunks.
        
        Args:
            json_path: Path to JSON file
            db_id: Database identifier
            
        Returns:
            List of processed JSON chunks with metadata
        """
        try:
            docs = []
            with open(json_path, 'r') as f:
                table_data = json.load(f)
            
            table_name = os.path.basename(json_path).replace('.json', '')
            
            # Process table metadata
            table_info = self._get_table_representation(table_data, table_name)
            
            doc = {
                "content": table_info,
                "metadata": {
                    "source": "schema_table",
                    "db_id": db_id,
                    "table": table_name,
                    "file_path": json_path
                }
            }
            docs.append(doc)
            
            return docs
        except Exception as e:
            logger.error(f"Error processing table JSON {json_path}: {e}")
            return []
    
    def _get_table_representation(self, table_data: Dict, table_name: str) -> str:
        """Create a textual representation of a table schema.
        
        Args:
            table_data: Table schema data
            table_name: Name of the table
            
        Returns:
            String representation of the table schema
        """
        columns = table_data.get('columns', [])
        column_types = table_data.get('column_types', [])
        column_descriptions = table_data.get('column_descriptions', [])
        
        # Build the table representation
        lines = [f"Table: {table_name}"]
        
        for i, (col, col_type) in enumerate(zip(columns, column_types)):
            desc = column_descriptions[i] if i < len(column_descriptions) else ""
            lines.append(f"- {col} ({col_type}): {desc}")
        
        # Add sample rows if available
        sample_rows = table_data.get('sample_rows', [])
        if sample_rows:
            lines.append("\nSample data:")
            for row in sample_rows[:3]:  # Limit to 3 sample rows
                lines.append(f"- {str(row)}")
        
        return "\n".join(lines)
    
    def process_external_knowledge(self, file_path: str) -> List[Dict[str, Any]]:
        """Process external knowledge document.
        
        Args:
            file_path: Path to the external knowledge file
            
        Returns:
            List of processed document chunks with metadata
        """
        if not os.path.exists(file_path):
            full_path = os.path.join(self.knowledge_dir, file_path) if self.knowledge_dir else None
            if not full_path or not os.path.exists(full_path):
                logger.warning(f"External knowledge file not found at {file_path} or {full_path}")
                return []
            file_path = full_path
            
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Split the document into chunks
            chunks = self._chunk_text(content)
            
            docs = []
            for i, chunk in enumerate(chunks):
                doc = {
                    "content": chunk,
                    "metadata": {
                        "source": "external_knowledge",
                        "file_path": file_path,
                        "chunk_index": i
                    }
                }
                docs.append(doc)
                
            return docs
        except Exception as e:
            logger.error(f"Error processing external knowledge file {file_path}: {e}")
            return []
    
    def process_past_queries(self, queries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process past SQL queries and results.
        
        Args:
            queries: List of past queries with results
            
        Returns:
            List of processed query documents with metadata
        """
        docs = []
        
        for i, query_data in enumerate(queries):
            query = query_data.get('query', '')
            result = query_data.get('result', '')
            db_id = query_data.get('db_id', '')
            
            if query:
                doc_content = f"SQL Query: {query}\n"
                if result:
                    doc_content += f"Result: {result}\n"
                
                doc = {
                    "content": doc_content,
                    "metadata": {
                        "source": "past_query",
                        "db_id": db_id,
                        "query_index": i
                    }
                }
                docs.append(doc)
                
        return docs
    
    def _chunk_text(self, text: str) -> List[str]:
        """Split text into chunks of specified size with overlap.
        
        Args:
            text: Text to split
            
        Returns:
            List of text chunks
        """
        if not text:
            return []
            
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # If we're not at the beginning, start this chunk at the chunk_overlap point
            if start > 0:
                start = start - self.chunk_overlap
                
            # Add the chunk to our list
            chunks.append(text[start:end])
            
            # Move to the next chunk
            start = end
            
        return chunks
