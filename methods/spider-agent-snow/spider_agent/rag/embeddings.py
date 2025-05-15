"""Embedding manager for Spider-Agent-Snow RAG implementation.

This module handles the creation and management of embeddings
for documents processed by the DocumentProcessor.
"""

import os
import logging
import json
import uuid
from typing import Dict, List, Optional, Tuple, Union, Any

import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger("spider_agent.rag")

class EmbeddingManager:
    """Manage embeddings for RAG system."""
    
    def __init__(self, 
                model_name: str = "sentence-transformers/all-MiniLM-L6-v2", 
                persist_directory: str = None,
                collection_name: str = "spider_agent_snow"):
        """Initialize the embedding manager.
        
        Args:
            model_name: Name of the sentence transformer model to use
            persist_directory: Directory to persist vector store
            collection_name: Name of the collection in the vector store
        """
        self.model_name = model_name
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        # Initialize the embedding model
        self._init_embedding_model()
        
        # Initialize the vector store
        self._init_vector_store()
        
    def _init_embedding_model(self):
        """Initialize the embedding model."""
        try:
            # For production, you might want to use a custom path or a local model
            # You could load your own model here
            self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=self.model_name
            )
            logger.info(f"Initialized embedding model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            # Fallback to a simpler model if available
            try:
                self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="sentence-transformers/all-mpnet-base-v2"
                )
                logger.info("Initialized fallback embedding model")
            except Exception as e2:
                logger.error(f"Failed to initialize fallback embedding model: {e2}")
                raise RuntimeError("Failed to initialize embedding model")
    
    def _init_vector_store(self):
        """Initialize the vector store."""
        try:
            # If persist_directory is provided, use a persistent ChromaDB store
            if self.persist_directory and not os.path.exists(self.persist_directory):
                os.makedirs(self.persist_directory)
                
            client_settings = {}
            if self.persist_directory:
                client_settings["persist_directory"] = self.persist_directory
                
            self.client = chromadb.PersistentClient(**client_settings) if self.persist_directory else chromadb.Client()
            
            # Create or get the collection
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function
            )
            
            logger.info(f"Initialized vector store collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            raise RuntimeError("Failed to initialize vector store")
    
    def add_documents(self, docs: List[Dict[str, Any]], batch_size: int = 32) -> List[str]:
        """Add documents to the vector store.
        
        Args:
            docs: List of processed documents with content and metadata
            batch_size: Size of batches for adding documents
            
        Returns:
            List of document IDs
        """
        if not docs:
            return []
            
        doc_ids = []
        
        # Process in batches
        for i in range(0, len(docs), batch_size):
            batch = docs[i:i+batch_size]
            
            contents = [doc["content"] for doc in batch]
            metadatas = [doc["metadata"] for doc in batch]
            ids = [str(uuid.uuid4()) for _ in batch]
            
            try:
                self.collection.add(
                    documents=contents,
                    metadatas=metadatas,
                    ids=ids
                )
                doc_ids.extend(ids)
                logger.info(f"Added batch of {len(batch)} documents to the vector store")
            except Exception as e:
                logger.error(f"Failed to add batch to vector store: {e}")
        
        return doc_ids
    
    def delete_documents(self, ids: List[str] = None, filter: Dict = None):
        """Delete documents from the vector store.
        
        Args:
            ids: List of document IDs to delete
            filter: Filter to apply for deletion
        """
        try:
            if ids:
                self.collection.delete(ids=ids)
                logger.info(f"Deleted {len(ids)} documents from the vector store")
            elif filter:
                self.collection.delete(where=filter)
                logger.info(f"Deleted documents matching filter {filter} from the vector store")
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
    
    def search(self, 
              query: str, 
              n_results: int = 5, 
              filter: Dict = None) -> Dict[str, List]:
        """Search for similar documents in the vector store.
        
        Args:
            query: Query string
            n_results: Number of results to return
            filter: Filter to apply to the search
            
        Returns:
            Dict containing query results
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=filter
            )
            return results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {"ids": [[]], "distances": [[]], "metadatas": [[]], "documents": [[]]}
    
    def get_document_by_id(self, doc_id: str) -> Dict[str, Any]:
        """Get a document by its ID.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Dict containing the document
        """
        try:
            result = self.collection.get(ids=[doc_id])
            if result and result["documents"]:
                return {
                    "content": result["documents"][0],
                    "metadata": result["metadatas"][0] if result["metadatas"] else {}
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get document by ID {doc_id}: {e}")
            return None
