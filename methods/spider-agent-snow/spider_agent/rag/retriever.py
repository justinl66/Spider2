"""Retriever for Spider-Agent-Snow RAG implementation.

This module implements the retrieval functionality of the RAG system,
providing methods to retrieve relevant context for the agent's prompts.
"""

import logging
from typing import Dict, List, Optional, Tuple, Union, Any

from spider_agent.rag.embeddings import EmbeddingManager
from spider_agent.rag.document_processor import DocumentProcessor

logger = logging.getLogger("spider_agent.rag")

class RAGRetriever:
    """Retriever for RAG implementation."""
    
    def __init__(self, 
                embedding_manager: EmbeddingManager,
                document_processor: DocumentProcessor,
                max_tokens_per_source: int = 1000,
                max_total_tokens: int = 3000):
        """Initialize the RAG retriever.
        
        Args:
            embedding_manager: EmbeddingManager instance
            document_processor: DocumentProcessor instance
            max_tokens_per_source: Maximum tokens to include per source type
            max_total_tokens: Maximum total tokens across all sources
        """
        self.embedding_manager = embedding_manager
        self.document_processor = document_processor
        self.max_tokens_per_source = max_tokens_per_source
        self.max_total_tokens = max_total_tokens
    
    def retrieve(self, 
                query: str, 
                db_id: str = None,
                n_results: int = 5) -> Dict[str, Any]:
        """Retrieve relevant context for a query.
        
        Args:
            query: Query string
            db_id: Database identifier to filter results
            n_results: Number of results to retrieve
            
        Returns:
            Dict containing retrieved context information
        """
        results = {
            "schema_context": "",
            "knowledge_context": "",
            "query_examples": ""
        }
        
        # Apply filter for database if provided
        filter_dict = {"db_id": db_id} if db_id else None
        
        # Retrieve schema information
        schema_results = self._retrieve_by_source(
            query=query, 
            source="schema", 
            n_results=n_results, 
            filter_dict=filter_dict
        )
        
        # Retrieve external knowledge
        knowledge_results = self._retrieve_by_source(
            query=query, 
            source="external_knowledge", 
            n_results=n_results
        )
        
        # Retrieve past query examples
        query_results = self._retrieve_by_source(
            query=query, 
            source="past_query", 
            n_results=n_results, 
            filter_dict=filter_dict
        )
        
        # Format results
        results["schema_context"] = self._format_schema_context(schema_results)
        results["knowledge_context"] = self._format_knowledge_context(knowledge_results)
        results["query_examples"] = self._format_query_examples(query_results)
        
        return results
    
    def _retrieve_by_source(self, 
                          query: str, 
                          source: str, 
                          n_results: int = 5, 
                          filter_dict: Dict = None) -> Dict:
        """Retrieve documents by source type.
        
        Args:
            query: Query string
            source: Source type to filter by
            n_results: Number of results to retrieve
            filter_dict: Additional filter to apply
            
        Returns:
            Dict containing retrieval results
        """
        # Combine source filter with additional filter
        where_filter = {"source": {"$contains": source}}
        if filter_dict:
            where_filter.update(filter_dict)
        
        # Perform search
        try:
            results = self.embedding_manager.search(
                query=query,
                n_results=n_results,
                filter=where_filter
            )
            return results
        except Exception as e:
            logger.error(f"Failed to retrieve by source {source}: {e}")
            return {"ids": [[]], "distances": [[]], "metadatas": [[]], "documents": [[]]}
    
    def _format_schema_context(self, results: Dict) -> str:
        """Format schema context from retrieval results.
        
        Args:
            results: Schema retrieval results
            
        Returns:
            Formatted schema context string
        """
        if not results or not results["documents"] or not results["documents"][0]:
            return ""
            
        context_parts = []
        total_tokens = 0
        
        for doc, metadata in zip(results["documents"][0], results["metadatas"][0]):
            # Rough token estimation (about 4 characters per token)
            doc_tokens = len(doc) // 4
            
            if total_tokens + doc_tokens > self.max_tokens_per_source:
                break
                
            source_info = f"From table: {metadata.get('table', 'unknown')}"
            context_parts.append(f"--- {source_info} ---\n{doc}\n")
            total_tokens += doc_tokens
            
        return "\n".join(context_parts)
    
    def _format_knowledge_context(self, results: Dict) -> str:
        """Format knowledge context from retrieval results.
        
        Args:
            results: Knowledge retrieval results
            
        Returns:
            Formatted knowledge context string
        """
        if not results or not results["documents"] or not results["documents"][0]:
            return ""
            
        context_parts = []
        total_tokens = 0
        
        for doc, metadata in zip(results["documents"][0], results["metadatas"][0]):
            # Rough token estimation (about 4 characters per token)
            doc_tokens = len(doc) // 4
            
            if total_tokens + doc_tokens > self.max_tokens_per_source:
                break
                
            file_path = metadata.get('file_path', 'unknown')
            file_name = file_path.split('/')[-1] if '/' in file_path else file_path
            source_info = f"From document: {file_name}"
            context_parts.append(f"--- {source_info} ---\n{doc}\n")
            total_tokens += doc_tokens
            
        return "\n".join(context_parts)
    
    def _format_query_examples(self, results: Dict) -> str:
        """Format query examples from retrieval results.
        
        Args:
            results: Query retrieval results
            
        Returns:
            Formatted query examples string
        """
        if not results or not results["documents"] or not results["documents"][0]:
            return ""
            
        context_parts = []
        total_tokens = 0
        
        for doc, metadata in zip(results["documents"][0], results["metadatas"][0]):
            # Rough token estimation (about 4 characters per token)
            doc_tokens = len(doc) // 4
            
            if total_tokens + doc_tokens > self.max_tokens_per_source:
                break
                
            index = metadata.get('query_index', 'unknown')
            source_info = f"Example query {index}"
            context_parts.append(f"--- {source_info} ---\n{doc}\n")
            total_tokens += doc_tokens
            
        return "\n".join(context_parts)
    
    def get_augmentation_text(self, context_dict: Dict[str, str]) -> str:
        """Create text to augment the agent's prompt with retrieved context.
        
        Args:
            context_dict: Dict containing different types of context
            
        Returns:
            Formatted augmentation text
        """
        sections = []
        
        # Add schema context if available
        if context_dict.get("schema_context"):
            sections.append("# RELEVANT SCHEMA INFORMATION\n" + context_dict["schema_context"])
        
        # Add knowledge context if available
        if context_dict.get("knowledge_context"):
            sections.append("# RELEVANT EXTERNAL KNOWLEDGE\n" + context_dict["knowledge_context"])
        
        # Add query examples if available
        if context_dict.get("query_examples"):
            sections.append("# RELEVANT EXAMPLE QUERIES\n" + context_dict["query_examples"])
        
        # Join sections with separators
        augmentation_text = "\n\n" + "\n\n".join(sections) + "\n\n"
        
        return augmentation_text
