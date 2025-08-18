"""
Wikipedia RAG (Retrieval-Augmented Generation) System

This module provides the main RAG system that combines Wikipedia retrieval,
vector similarity search, and LLM generation for answering questions. It serves
as the orchestrator that coordinates all components of the RAG pipeline.

The RAG system implements a sophisticated workflow:
1. Query Processing: Converts user questions into embeddings for semantic search
2. Context Retrieval: Searches existing vector store for relevant content
3. Dynamic Indexing: Automatically indexes new Wikipedia content when needed
4. Context Formatting: Prepares retrieved content for LLM consumption
5. Answer Generation: Uses LLM to generate contextually relevant answers

Key Features:
- Intelligent context retrieval with similarity thresholding
- Automatic Wikipedia content indexing for missing information
- Dynamic context length management to fit LLM constraints
- Comprehensive error handling and fallback mechanisms
- Detailed logging and debugging information
- Source attribution and metadata tracking

Architecture:
The system follows a modular architecture where each component has a specific
responsibility:
- EmbeddingModel: Converts text to vector representations
- VectorStore: Manages FAISS index for efficient similarity search
- WikipediaRetriever: Fetches and chunks Wikipedia content
- LLMInterface: Handles language model interaction

Example:
    >>> from src.rag_system import WikipediaRAG
    >>> rag = WikipediaRAG()
    >>> answer = rag.query("What is machine learning?")
    >>> print(answer)

Dependencies:
    - logging: For comprehensive system logging
    - dataclasses: For structured response objects
    - typing: For type hints and documentation
"""

import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass

from .config import (
    TOP_K_RETRIEVAL, 
    MIN_SIMILARITY_THRESHOLD,
    MAX_CONTEXT_LENGTH,
    SYSTEM_PROMPT
)
from .embeddings import EmbeddingModel
from .vector_store import VectorStore
from .wikipedia_retriever import WikipediaRetriever, WikipediaChunk
from .llm_interface import LLMInterface

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RAGResponse:
    """
    Response from RAG system containing answer and metadata.
    
    This dataclass encapsulates the complete response from a RAG query,
    including not just the generated answer but also all the metadata
    needed for transparency, debugging, and source attribution.
    
    Attributes:
        answer (str): The generated answer from the LLM
        sources (List[str]): List of Wikipedia URLs used as sources
        chunks_used (List[WikipediaChunk]): The actual chunks used for context
        similarities (List[float]): Similarity scores for each chunk used
        
    Example:
        >>> response = rag.query_detailed("What is Python?")
        >>> print(f"Answer: {response.answer}")
        >>> print(f"Sources: {response.sources}")
        >>> print(f"Used {len(response.chunks_used)} chunks")
        >>> print(f"Best similarity: {max(response.similarities):.3f}")
    """
    answer: str
    sources: List[str]
    chunks_used: List[WikipediaChunk]
    similarities: List[float]


class WikipediaRAG:
    """
    Main RAG system that orchestrates Wikipedia retrieval, vector search, and LLM generation.
    
    This class serves as the central coordinator for the entire RAG pipeline. It manages
    the interaction between different components and implements the core RAG workflow
    including intelligent context retrieval, dynamic content indexing, and answer generation.
    
    The system implements several advanced features:
    - Semantic similarity search with configurable thresholds
    - Automatic Wikipedia content discovery and indexing
    - Context length management for optimal LLM performance
    - Comprehensive error handling and recovery mechanisms
    - Detailed logging for debugging and monitoring
    
    Architecture:
    The RAG system follows a pipeline architecture:
    Query → Embedding → Vector Search → (Optional) Auto-Indexing → 
    Context Formatting → LLM Generation → Response
    
    Attributes:
        embedding_model (EmbeddingModel): Handles text-to-vector conversion
        vector_store (VectorStore): Manages FAISS index for similarity search
        wikipedia_retriever (WikipediaRetriever): Fetches Wikipedia content
        llm_interface (LLMInterface): Handles language model interaction
        
    Example:
        >>> # Initialize the RAG system
        >>> rag = WikipediaRAG()
        >>> 
        >>> # Ask a question
        >>> answer = rag.query("What is quantum computing?")
        >>> print(answer)
        >>> 
        >>> # Get system statistics
        >>> stats = rag.get_stats()
        >>> print(f"Index contains {stats['vector_store_stats']['total_chunks']} chunks")
    """
    
    def __init__(self):
        """
        Initialize the RAG system with all components.
        
        This method sets up all the required components for the RAG system:
        - Embedding model for converting text to vectors
        - Vector store for efficient similarity search
        - Wikipedia retriever for content fetching
        - LLM interface for answer generation
        
        The initialization process includes loading pre-trained models and
        existing vector indices if available. This may take some time on
        the first run as models need to be downloaded.
        
        Raises:
            Exception: If any component fails to initialize properly.
                      Common causes include missing dependencies, network
                      issues for model downloads, or insufficient GPU memory.
                      
        Note:
            The initialization is logged to help with debugging and monitoring.
            All components use singleton patterns to ensure efficient resource usage.
        """
        print("Initializing Wikipedia RAG system...")
        
        # Initialize components
        self.embedding_model = EmbeddingModel()
        self.vector_store = VectorStore()
        self.wikipedia_retriever = WikipediaRetriever()
        self.llm_interface = LLMInterface()
        
        print("RAG system initialized successfully!")
    
    def retrieve_context(self, query: str) -> Tuple[List[WikipediaChunk], List[float]]:
        """
        Retrieve relevant context chunks for a query with intelligent auto-indexing.
        
        This method implements a sophisticated context retrieval strategy that first
        searches the existing vector store and then automatically indexes new Wikipedia
        content if the existing results are not sufficiently relevant.
        
        The retrieval process:
        1. Convert query to embedding vector
        2. Search existing vector store for similar chunks
        3. Evaluate relevance of results using similarity thresholds
        4. If results are insufficient, automatically index new Wikipedia content
        5. Re-search with the expanded index
        6. Filter results by minimum similarity threshold
        
        Args:
            query (str): The search query or question.
                        Should be a natural language question or topic.
                        Example: "What is machine learning?"
            
        Returns:
            Tuple[List[WikipediaChunk], List[float]]: A tuple containing:
                - chunks: List of relevant Wikipedia chunks
                - scores: Corresponding similarity scores (0.0-1.0)
                
        Example:
            >>> rag = WikipediaRAG()
            >>> chunks, scores = rag.retrieve_context("quantum computing applications")
            >>> for chunk, score in zip(chunks, scores):
            ...     print(f"Similarity: {score:.3f}, Title: {chunk.title}")
            
        Note:
            The auto-indexing feature means this method may trigger Wikipedia
            searches and content processing, which can take additional time
            but ensures comprehensive coverage of the topic.
        """
        # Generate query embedding first
        query_embedding = self.embedding_model.embed_query(query)
        
        # Try to find relevant chunks in existing index
        results = self.vector_store.search(query_embedding, k=TOP_K_RETRIEVAL)
        
        if results:
            chunks, scores = zip(*results)
            chunks, scores = list(chunks), list(scores)
        else:
            chunks, scores = [], []
        
        # Check if we have relevant results - use a higher threshold for auto-indexing
        auto_index_threshold = 0.8  # If best result is below this, try to get better content
        if not chunks or (scores and max(scores) < auto_index_threshold):
            print(f"Low similarity (max: {max(scores) if scores else 0:.3f}), trying to index new content...")
            
            # Auto-index new content for this query
            new_chunks = self.wikipedia_retriever.retrieve_and_chunk(query)
            if new_chunks:
                # Add new chunks to vector store
                chunk_texts = [chunk.text for chunk in new_chunks]
                embeddings = self.embedding_model.embed_passages(chunk_texts)
                self.vector_store.add_embeddings(embeddings, new_chunks)
                self.vector_store.save_index()
                
                print(f"Successfully indexed {len(new_chunks)} chunks")
                # Try search again after indexing
                results = self.vector_store.search(query_embedding, k=TOP_K_RETRIEVAL)
                if results:
                    chunks, scores = zip(*results)
                    chunks, scores = list(chunks), list(scores)
            else:
                print("No new content could be indexed for this query")
        
        # Filter by minimum similarity threshold
        if chunks and scores:
            filtered_results = [
                (chunk, score) for chunk, score in zip(chunks, scores)
                if score >= MIN_SIMILARITY_THRESHOLD
            ]
            if filtered_results:
                chunks, scores = zip(*filtered_results)
                chunks, scores = list(chunks), list(scores)
            else:
                chunks, scores = [], []
        
        return chunks, scores
    
    def format_context(self, chunks: List[WikipediaChunk]) -> str:
        """
        Format retrieved chunks into context for the LLM.
        
        This method takes the retrieved Wikipedia chunks and formats them into
        a coherent context string that the LLM can use to generate answers.
        It handles context length management, source attribution, and proper
        formatting for optimal LLM performance.
        
        Context Management:
        - Adds source attribution for each chunk
        - Manages total context length to fit LLM constraints
        - Preserves chunk order (most relevant first)
        - Provides fallback for empty context
        
        Args:
            chunks (List[WikipediaChunk]): List of Wikipedia chunks to format.
                                          Should be ordered by relevance (most relevant first).
            
        Returns:
            str: Formatted context string ready for LLM consumption.
                 Includes source attributions and proper formatting.
                 Returns fallback message if no chunks provided.
                 
        Example:
            >>> chunks = [chunk1, chunk2, chunk3]  # Retrieved chunks
            >>> context = rag.format_context(chunks)
            >>> print(context)
            [Source 1: Python (programming language)]
            Python is a high-level programming language...
            
            [Source 2: Machine Learning]
            Machine learning is a subset of artificial intelligence...
            
        Note:
            The method respects the MAX_CONTEXT_LENGTH configuration to ensure
            the formatted context fits within LLM constraints. Chunks are added
            in order until the limit is reached.
        """
        if not chunks:
            return "No relevant context available."
        
        context_parts = []
        total_length = 0
        
        for i, chunk in enumerate(chunks, 1):
            source_info = f"[Source {i}: {chunk.title}]"
            chunk_content = f"{source_info}\n{chunk.text}\n"
            
            # Check if adding this chunk would exceed max context length
            if total_length + len(chunk_content) > MAX_CONTEXT_LENGTH:
                break
                
            context_parts.append(chunk_content)
            total_length += len(chunk_content)
        
        return "\n".join(context_parts)
    
    def query(self, question: str) -> str:
        """
        Process a query through the complete RAG pipeline.
        
        This is the main entry point for the RAG system. It orchestrates the
        entire pipeline from query processing to answer generation, providing
        comprehensive logging and error handling throughout the process.
        
        Pipeline Steps:
        1. Context Retrieval: Find relevant Wikipedia chunks
        2. Context Formatting: Prepare content for LLM
        3. Answer Generation: Generate response using LLM
        4. Error Handling: Provide fallback responses when needed
        
        Args:
            question (str): The question to answer.
                           Should be a clear, well-formed question.
                           Examples: "What is machine learning?",
                                   "How does photosynthesis work?",
                                   "Who invented the telephone?"
            
        Returns:
            str: Generated answer to the question.
                 Returns error message if no relevant context found
                 or if generation fails.
                 
        Example:
            >>> rag = WikipediaRAG()
            >>> answer = rag.query("What is artificial intelligence?")
            >>> print(answer)
            
            >>> # More specific question
            >>> answer = rag.query("When was Python programming language created?")
            >>> print(answer)
            
        Note:
            The method includes comprehensive logging that shows:
            - Retrieved context information
            - Wikipedia sources being used
            - Similarity scores for debugging
            - Generation process status
        """
        print(f"\nProcessing query: '{question}'")
        
        # Step 1: Retrieve relevant context
        print("Retrieving relevant context...")
        chunks, scores = self.retrieve_context(question)
        
        if not chunks:
            return "I couldn't find relevant information to answer your question. Please try rephrasing or asking about a different topic."
        
        print(f"Retrieved {len(chunks)} relevant chunks")
        
        # Debug: Show what context is being used
        print("\n" + "="*60)
        print("📚 WIKIPEDIA CONTEXT BEING USED:")
        print("="*60)
        print()
        for i, (chunk, score) in enumerate(zip(chunks, scores), 1):
            print(f"📄 Chunk {i} (similarity: {score:.3f}):")
            print(f"   Title: {chunk.title}")
            # Show first 200 chars of content for debugging
            content_preview = chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text
            print(f"   Content: WikipediaChunk(text='{content_preview}')")
            print()
        print("="*60)
        
        # Step 2: Format context for LLM
        context = self.format_context(chunks)
        
        # Step 3: Generate answer using LLM
        print("Generating answer...")
        answer = self.llm_interface.generate_answer(context, question)
        
        return answer
    
    def get_stats(self) -> dict:
        """
        Get comprehensive system statistics.
        
        This method provides detailed information about the current state of the
        RAG system, including model information, vector store statistics, and
        configuration details. It's useful for monitoring, debugging, and
        system health checks.
        
        Returns:
            dict: Dictionary containing system statistics with the following keys:
                - embedding_model: Name of the embedding model being used
                - embedding_dimension: Dimension of the embedding vectors
                - vector_store_stats: Statistics from the vector store
                  - total_chunks: Number of chunks in the index
                  - unique_articles: Number of unique Wikipedia articles
                  - metadata_count: Number of metadata entries
                - llm_model: Path/name of the LLM model
                
        Example:
            >>> rag = WikipediaRAG()
            >>> stats = rag.get_stats()
            >>> print(f"Model: {stats['embedding_model']}")
            >>> print(f"Index size: {stats['vector_store_stats']['total_chunks']} chunks")
            >>> print(f"Articles: {stats['vector_store_stats']['unique_articles']}")
            >>> print(f"LLM: {stats['llm_model']}")
            
        Note:
            This method is non-destructive and can be called safely at any time
            without affecting system performance or state.
        """
        vector_stats = self.vector_store.get_stats()
        stats = {
            "embedding_model": self.embedding_model.model_name,
            "embedding_dimension": self.embedding_model.embedding_dim,
            "vector_store_stats": vector_stats,
            "llm_model": self.llm_interface.model_path,
        }
        return stats
    
    def clear_index(self):
        """
        Clear the vector store index and save the empty state.
        
        This method completely clears the vector store index, removing all
        stored embeddings and associated metadata. It's useful for:
        - Resetting the system to a clean state
        - Clearing outdated or corrupted index data
        - Starting fresh with new content
        
        The method ensures that:
        - All embeddings are removed from the FAISS index
        - All metadata is cleared
        - The empty state is persisted to disk
        - The operation is logged for tracking
        
        Example:
            >>> rag = WikipediaRAG()
            >>> rag.clear_index()  # Removes all indexed content
            >>> stats = rag.get_stats()
            >>> print(stats['vector_store_stats']['total_chunks'])  # Should be 0
            
        Warning:
            This operation is irreversible. All previously indexed Wikipedia
            content will be lost and will need to be re-indexed on future
            queries. Consider backing up the index files if you might want
            to restore the current state later.
            
        Note:
            After clearing the index, the system will automatically re-index
            content as needed when processing new queries.
        """
        self.vector_store.clear()
        self.vector_store.save_index()
        print("Vector store index cleared.")
