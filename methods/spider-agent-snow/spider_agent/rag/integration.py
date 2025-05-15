"""Integration module for Spider-Agent-Snow RAG implementation.

This module provides the interface between the RAG system and the agent,
handling the augmentation of prompts with retrieved context.
"""

import os
import logging
import json
from typing import Dict, List, Optional, Tuple, Union, Any

from spider_agent.agent.agents import PromptAgent
from spider_agent.rag.document_processor import DocumentProcessor
from spider_agent.rag.embeddings import EmbeddingManager
from spider_agent.rag.retriever import RAGRetriever

logger = logging.getLogger("spider_agent.rag")

class RagAugmentedAgent(PromptAgent):
    """Agent enhanced with RAG capabilities."""
    
    def __init__(self, 
                model="gpt-4",
                max_tokens=1500,
                top_p=0.9,
                temperature=0.5,
                max_memory_length=10,
                max_steps=15,
                use_plan=False,
                # RAG-specific parameters
                use_rag=True,
                embedding_model="sentence-transformers/all-MiniLM-L6-v2",
                persist_directory=None,
                schema_dir=None,
                knowledge_dir=None,
                max_tokens_per_source=1000,
                max_total_tokens=3000):
        """Initialize the RAG-augmented agent.
        
        Args:
            model: Model name to use for LLM
            max_tokens: Maximum tokens for LLM responses
            top_p: Top-p parameter for LLM
            temperature: Temperature parameter for LLM
            max_memory_length: Maximum memory length for the agent
            max_steps: Maximum steps for the agent
            use_plan: Whether to use planning
            use_rag: Whether to use RAG
            embedding_model: Model name for embeddings
            persist_directory: Directory to persist vector store
            schema_dir: Directory containing schema files
            knowledge_dir: Directory containing external knowledge
            max_tokens_per_source: Maximum tokens per source type
            max_total_tokens: Maximum total tokens for context
        """
        # Initialize the base agent
        super().__init__(
            model=model,
            max_tokens=max_tokens,
            top_p=top_p,
            temperature=temperature,
            max_memory_length=max_memory_length,
            max_steps=max_steps,
            use_plan=use_plan
        )
        
        # RAG configuration
        self.use_rag = use_rag
        
        if self.use_rag:
            # Initialize RAG components
            self._init_rag_components(
                embedding_model=embedding_model,
                persist_directory=persist_directory,
                schema_dir=schema_dir,
                knowledge_dir=knowledge_dir,
                max_tokens_per_source=max_tokens_per_source,
                max_total_tokens=max_total_tokens
            )
    
    def _init_rag_components(self,
                          embedding_model,
                          persist_directory,
                          schema_dir,
                          knowledge_dir,
                          max_tokens_per_source,
                          max_total_tokens):
        """Initialize RAG components.
        
        Args:
            embedding_model: Model name for embeddings
            persist_directory: Directory to persist vector store
            schema_dir: Directory containing schema files
            knowledge_dir: Directory containing external knowledge
            max_tokens_per_source: Maximum tokens per source type
            max_total_tokens: Maximum total tokens for context
        """
        try:
            # Initialize document processor
            self.document_processor = DocumentProcessor(
                schema_dir=schema_dir,
                knowledge_dir=knowledge_dir
            )
            
            # Initialize embedding manager
            self.embedding_manager = EmbeddingManager(
                model_name=embedding_model,
                persist_directory=persist_directory,
                collection_name="spider_agent_snow"
            )
            
            # Initialize retriever
            self.retriever = RAGRetriever(
                embedding_manager=self.embedding_manager,
                document_processor=self.document_processor,
                max_tokens_per_source=max_tokens_per_source,
                max_total_tokens=max_total_tokens
            )
            
            logger.info("Successfully initialized RAG components")
        except Exception as e:
            logger.error(f"Failed to initialize RAG components: {e}")
            self.use_rag = False
    
    def set_env_and_task(self, env):
        """Set environment and task, augmenting with RAG if enabled.
        
        Overrides the parent method to add RAG-augmented context.
        """
        # Call parent implementation first
        super().set_env_and_task(env)
        
        # If RAG is not enabled, return
        if not self.use_rag:
            return
            
        # Get task information
        self.db_id = env.task_config.get('db_id')
        self.external_knowledge = env.task_config.get('external_knowledge')
        
        # Process schema data if available
        if self.db_id:
            schema_docs = self.document_processor.process_schema_files(self.db_id)
            if schema_docs:
                logger.info(f"Processed {len(schema_docs)} schema documents for {self.db_id}")
                self.embedding_manager.add_documents(schema_docs)
        
        # Process external knowledge if available
        if self.external_knowledge:
            knowledge_docs = self.document_processor.process_external_knowledge(self.external_knowledge)
            if knowledge_docs:
                logger.info(f"Processed {len(knowledge_docs)} knowledge documents from {self.external_knowledge}")
                self.embedding_manager.add_documents(knowledge_docs)
        
        # Augment the system message with RAG context
        self._augment_system_message()
    
    def _augment_system_message(self):
        """Augment the system message with retrieved context."""
        try:
            # Skip if RAG is not enabled
            if not self.use_rag:
                return
                
            # Retrieve relevant context
            context = self.retriever.retrieve(
                query=self.instruction,
                db_id=self.db_id,
                n_results=5
            )
            
            # Format the context into augmentation text
            augmentation_text = self.retriever.get_augmentation_text(context)
            
            # Augment the system message
            augmented_system_message = self.system_message + "\n\n# RETRIEVED CONTEXT #\n" + augmentation_text
            
            # Update the system message in history
            if self.history_messages and self.history_messages[0]["role"] == "system":
                self.history_messages[0]["content"][0]["text"] = augmented_system_message
                self.system_message = augmented_system_message
                
            logger.info("Successfully augmented system message with RAG context")
        except Exception as e:
            logger.error(f"Failed to augment system message with RAG context: {e}")
            
    def predict(self, obs: Dict = None) -> List:
        """Predict the next action with RAG enhancement.
        
        Overrides the parent method to add RAG retrieval for new observations.
        """
        # If RAG is not enabled or no observation, use parent implementation
        if not self.use_rag or obs is None:
            return super().predict(obs)
            
        # Extract the observation text if available
        obs_text = obs.get("output", "") if isinstance(obs, dict) else ""
        
        # If observation contains SQL query results, store them for future reference
        if "SQL" in obs_text and "Result:" in obs_text:
            try:
                # Extract query and result
                query_parts = obs_text.split("Result:", 1)
                query = query_parts[0].strip()
                result = query_parts[1].strip() if len(query_parts) > 1 else ""
                
                # Process as a past query
                query_doc = [{
                    "content": f"SQL Query: {query}\nResult: {result}",
                    "metadata": {
                        "source": "past_query",
                        "db_id": self.db_id,
                        "query_index": len(self.observations)
                    }
                }]
                
                # Add to the embedding store
                self.embedding_manager.add_documents(query_doc)
                logger.info("Added query result to the embedding store")
            except Exception as e:
                logger.error(f"Failed to process query result for embedding: {e}")
        
        # Use parent implementation for prediction
        return super().predict(obs)
