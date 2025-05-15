"""RAG (Retrieval-Augmented Generation) module for Spider-Agent-Snow.

This module provides functionality to enhance SQL query generation
with relevant context from database schema, external knowledge documents, 
and previous examples.
"""

from spider_agent.rag.document_processor import DocumentProcessor
from spider_agent.rag.embeddings import EmbeddingManager
from spider_agent.rag.retriever import RAGRetriever
from spider_agent.rag.integration import RagAugmentedAgent

__all__ = ['DocumentProcessor', 'EmbeddingManager', 'RAGRetriever', 'RagAugmentedAgent']
