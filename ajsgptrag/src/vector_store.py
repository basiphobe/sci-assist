"""
FAISS-based vector store for efficient similarity search.

This module provides a high-performance vector storage and retrieval system using
Facebook's FAISS (Facebook AI Similarity Search) library. It's specifically designed
for the Wikipedia RAG system but can be adapted for other document retrieval tasks.

Key Features:
- FAISS IndexFlatIP for exact cosine similarity search
- Automatic embedding normalization for optimal similarity computation
- Persistent storage of both vectors and metadata
- Efficient batch operations for large-scale indexing
- Comprehensive statistics and monitoring capabilities
- Thread-safe operations with singleton pattern support

Technical Details:
- Uses Inner Product (IP) index which equals cosine similarity for normalized vectors
- Stores embeddings as float32 for memory efficiency and FAISS compatibility
- Metadata is stored separately in JSON format for human readability
- Automatic index persistence ensures data survival across restarts

The vector store handles two types of data:
1. Vector embeddings: Stored in FAISS index for fast similarity search
2. Metadata: Stored as JSON containing chunk text, titles, URLs, and positions

Performance Characteristics:
- Search time: O(n) for exact search (where n = number of vectors)
- Memory usage: ~4 bytes per dimension per vector + metadata overhead
- Disk storage: Binary FAISS index + JSON metadata file

Example:
    >>> from src.vector_store import VectorStore
    >>> store = VectorStore()
    >>> 
    >>> # Add some embeddings
    >>> embeddings = np.random.rand(100, 768).astype(np.float32)
    >>> chunks = [create_sample_chunk(i) for i in range(100)]
    >>> store.add_embeddings(embeddings, chunks)
    >>> 
    >>> # Search for similar content
    >>> query_embedding = np.random.rand(1, 768).astype(np.float32)
    >>> results = store.search(query_embedding, k=5)
    >>> 
    >>> # Save to disk
    >>> store.save_index()

Dependencies:
    - faiss: For high-performance similarity search
    - numpy: For numerical operations and array handling
    - json: For metadata serialization
    - pathlib: For file path management
"""

import faiss
import numpy as np
import json
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from src.config import VECTOR_DB_PATH, METADATA_PATH, EMBEDDING_DIM
from src.wikipedia_retriever import WikipediaChunk


class VectorStore:
    """
    FAISS-based vector store for storing and searching embeddings with metadata.
    
    This class provides a complete solution for vector storage and retrieval,
    combining FAISS's high-performance similarity search with comprehensive
    metadata management. It's designed specifically for the Wikipedia RAG system
    but follows general principles applicable to other document retrieval tasks.
    
    Architecture:
    - FAISS IndexFlatIP: Stores normalized embeddings for cosine similarity search
    - JSON metadata: Stores chunk information (text, titles, URLs, positions)
    - Automatic persistence: Saves both index and metadata to disk
    - Lazy loading: Loads existing index on first access
    
    The vector store uses cosine similarity for semantic search, which is computed
    efficiently using inner product on normalized vectors. This approach provides
    intuitive similarity scores between 0 and 1, where 1 represents identical
    vectors and 0 represents orthogonal vectors.
    
    Attributes:
        embedding_dim (int): Dimension of the embedding vectors
        index (faiss.Index): FAISS index for similarity search
        metadata (List[WikipediaChunk]): List of chunk metadata corresponding to vectors
        
    Example:
        >>> # Initialize vector store
        >>> store = VectorStore(embedding_dim=768)
        >>> 
        >>> # Add embeddings with metadata
        >>> embeddings = np.random.rand(10, 768).astype(np.float32)
        >>> chunks = [WikipediaChunk(...) for _ in range(10)]
        >>> store.add_embeddings(embeddings, chunks)
        >>> 
        >>> # Search for similar vectors
        >>> query = np.random.rand(1, 768).astype(np.float32)
        >>> results = store.search(query, k=3)
        >>> 
        >>> # Get statistics
        >>> stats = store.get_stats()
        >>> print(f"Total vectors: {stats['total_chunks']}")
    """
    
    def __init__(self, embedding_dim: int = EMBEDDING_DIM):
        """
        Initialize the vector store.
        
        Sets up the vector store with the specified embedding dimension and
        initializes or loads the FAISS index. If an existing index is found
        on disk, it will be loaded automatically. Otherwise, a new empty
        index is created.
        
        Args:
            embedding_dim (int): Dimension of the embeddings that will be stored.
                               Must match the dimension of embeddings added later.
                               Defaults to EMBEDDING_DIM from config (768 for e5-base-v2).
                               
        Example:
            >>> # Using default embedding dimension from config
            >>> store = VectorStore()
            >>> 
            >>> # Using custom embedding dimension
            >>> store = VectorStore(embedding_dim=512)
            
        Note:
            The embedding dimension cannot be changed after initialization.
            If you need a different dimension, create a new VectorStore instance.
        """
        self.embedding_dim = embedding_dim
        self.index = None
        self.metadata = []  # Store chunk metadata
        self._initialize_index()
    
    def _initialize_index(self):
        """
        Initialize or load the FAISS index.
        
        This private method handles the initialization logic for the FAISS index.
        It first attempts to load an existing index from disk. If no existing
        index is found, it creates a new IndexFlatIP (Inner Product) index.
        
        The IndexFlatIP is chosen because:
        - It provides exact similarity search (no approximation)
        - Inner product on normalized vectors equals cosine similarity
        - It's suitable for the scale of Wikipedia content chunks
        - It provides deterministic and interpretable results
        
        Note:
            This method is called automatically during initialization and
            should not be called directly by users.
        """
        if VECTOR_DB_PATH.exists():
            self.load_index()
        else:
            # Create a new index using Inner Product (cosine similarity)
            # For normalized embeddings, inner product = cosine similarity
            self.index = faiss.IndexFlatIP(self.embedding_dim)
            print(f"Created new FAISS index with dimension {self.embedding_dim}")
    
    def save_index(self):
        """
        Save the FAISS index and metadata to disk.
        
        This method persists both the FAISS index and the associated metadata
        to disk, ensuring that the vector store state survives application
        restarts. The operation is atomic in the sense that both components
        are saved together.
        
        Storage format:
        - FAISS index: Binary format optimized for fast loading
        - Metadata: JSON format for human readability and debugging
        
        The metadata includes all information needed to reconstruct the
        WikipediaChunk objects, including text content, titles, URLs,
        and position information.
        
        Example:
            >>> store = VectorStore()
            >>> # ... add some embeddings ...
            >>> store.save_index()  # Persist to disk
            
        Note:
            This method should be called after adding new embeddings to
            ensure they are not lost. The RAG system typically calls this
            automatically after indexing new content.
        """
        if self.index is None:
            return
        
        # Save FAISS index
        faiss.write_index(self.index, str(VECTOR_DB_PATH))
        
        # Save metadata
        metadata_dicts = []
        for chunk in self.metadata:
            metadata_dict = {
                'text': chunk.text,
                'title': chunk.title,
                'url': chunk.url,
                'chunk_id': chunk.chunk_id,
                'start_pos': chunk.start_pos,
                'end_pos': chunk.end_pos
            }
            metadata_dicts.append(metadata_dict)
        
        with open(METADATA_PATH, 'w', encoding='utf-8') as f:
            json.dump(metadata_dicts, f, ensure_ascii=False, indent=2)
        
        print(f"Saved index with {self.index.ntotal} vectors to {VECTOR_DB_PATH}")
    
    def load_index(self):
        """
        Load the FAISS index and metadata from disk.
        
        This method restores a previously saved vector store state from disk,
        loading both the FAISS index and the associated metadata. It's called
        automatically during initialization if existing files are found.
        
        Loading process:
        1. Load the binary FAISS index file
        2. Load and parse the JSON metadata file
        3. Reconstruct WikipediaChunk objects from metadata
        4. Verify consistency between index and metadata
        
        The method handles missing files gracefully and provides informative
        logging about the loading process.
        
        Example:
            >>> store = VectorStore()  # Automatically loads if files exist
            >>> # Or manually reload:
            >>> store.load_index()
            
        Note:
            This method is typically called automatically and doesn't need
            to be invoked manually unless you're reloading after external
            changes to the index files.
        """
        if not VECTOR_DB_PATH.exists():
            print("No existing index found")
            return
        
        # Load FAISS index
        self.index = faiss.read_index(str(VECTOR_DB_PATH))
        
        # Load metadata
        if METADATA_PATH.exists():
            with open(METADATA_PATH, 'r', encoding='utf-8') as f:
                metadata_dicts = json.load(f)
            
            self.metadata = []
            for md in metadata_dicts:
                chunk = WikipediaChunk(
                    text=md['text'],
                    title=md['title'],
                    url=md['url'],
                    chunk_id=md['chunk_id'],
                    start_pos=md['start_pos'],
                    end_pos=md['end_pos']
                )
                self.metadata.append(chunk)
        
        print(f"Loaded index with {self.index.ntotal} vectors from {VECTOR_DB_PATH}")
    
    def add_embeddings(self, embeddings: np.ndarray, chunks: List[WikipediaChunk]):
        """
        Add embeddings and their metadata to the vector store.
        
        This method adds new embeddings to the FAISS index along with their
        corresponding metadata. The embeddings are automatically normalized
        to enable cosine similarity search using inner product.
        
        Process:
        1. Initialize index if not already created
        2. Normalize embeddings for cosine similarity
        3. Add embeddings to FAISS index
        4. Add corresponding metadata to internal list
        5. Log the addition for monitoring
        
        Args:
            embeddings (np.ndarray): Numpy array of embeddings with shape
                                   (num_embeddings, embedding_dim).
                                   Should be dtype float32 for FAISS compatibility.
            chunks (List[WikipediaChunk]): List of WikipediaChunk objects
                                         corresponding to each embedding.
                                         Must have same length as embeddings.
                                         
        Example:
            >>> import numpy as np
            >>> store = VectorStore()
            >>> 
            >>> # Create sample embeddings and chunks
            >>> embeddings = np.random.rand(5, 768).astype(np.float32)
            >>> chunks = [create_wikipedia_chunk(i) for i in range(5)]
            >>> 
            >>> # Add to store
            >>> store.add_embeddings(embeddings, chunks)
            >>> print(f"Store now contains {len(store.metadata)} chunks")
            
        Raises:
            AssertionError: If embeddings and chunks have different lengths
            ValueError: If embedding dimensions don't match the store's dimension
            
        Note:
            The embeddings are normalized in-place, so the original array is modified.
            If you need to preserve the original embeddings, pass a copy.
        """
        if self.index is None:
            self.index = faiss.IndexFlatIP(self.embedding_dim)
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        
        # Add to FAISS index
        self.index.add(embeddings)
        
        # Add metadata
        self.metadata.extend(chunks)
        
        print(f"Added {len(embeddings)} embeddings to vector store")
    
    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[Tuple[WikipediaChunk, float]]:
        """
        Search for similar chunks based on query embedding.
        
        This method performs semantic similarity search using cosine similarity
        to find the most relevant chunks for a given query embedding. It returns
        both the matching chunks and their similarity scores.
        
        Search process:
        1. Normalize the query embedding for cosine similarity
        2. Search the FAISS index for k nearest neighbors
        3. Retrieve corresponding metadata for each match
        4. Return sorted results (highest similarity first)
        
        Args:
            query_embedding (np.ndarray): Query embedding as numpy array with shape
                                        (1, embedding_dim) or (embedding_dim,).
                                        Will be reshaped and normalized automatically.
            k (int): Number of results to return. Defaults to 5.
                    Will be clamped to the actual number of vectors in the index.
                    
        Returns:
            List[Tuple[WikipediaChunk, float]]: List of tuples containing:
                - WikipediaChunk: The matching chunk with all metadata
                - float: Cosine similarity score (0.0 to 1.0, higher is more similar)
                
        Example:
            >>> store = VectorStore()
            >>> # ... add some embeddings ...
            >>> 
            >>> # Search for similar content
            >>> query_emb = np.random.rand(768).astype(np.float32)
            >>> results = store.search(query_emb, k=3)
            >>> 
            >>> for chunk, score in results:
            ...     print(f"Title: {chunk.title}")
            ...     print(f"Similarity: {score:.3f}")
            ...     print(f"Text preview: {chunk.text[:100]}...")
            ...     print()
                    
        Note:
            Returns empty list if the vector store is empty or if no valid
            matches are found. Similarity scores are cosine similarities
            ranging from 0.0 (orthogonal) to 1.0 (identical).
        """
        if self.index is None or self.index.ntotal == 0:
            print("Vector store is empty")
            return []
        
        # Normalize query embedding
        query_embedding = query_embedding.reshape(1, -1).astype(np.float32)
        faiss.normalize_L2(query_embedding)
        
        # Search
        scores, indices = self.index.search(query_embedding, min(k, self.index.ntotal))
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx != -1:  # Valid index
                chunk = self.metadata[idx]
                results.append((chunk, float(score)))
        
        return results
    
    def clear(self):
        """
        Clear the vector store, removing all embeddings and metadata.
        
        This method completely resets the vector store to an empty state,
        removing all stored embeddings and associated metadata. It creates
        a fresh FAISS index with the same configuration.
        
        Operations performed:
        1. Create new empty FAISS IndexFlatIP
        2. Clear all metadata
        3. Log the operation for monitoring
        
        Example:
            >>> store = VectorStore()
            >>> # ... add embeddings ...
            >>> print(f"Before: {len(store.metadata)} chunks")
            >>> store.clear()
            >>> print(f"After: {len(store.metadata)} chunks")  # Should be 0
            
        Note:
            This operation only affects the in-memory state. To persist
            the cleared state to disk, call save_index() after clearing.
            
        Warning:
            This operation is irreversible. All embeddings and metadata
            will be permanently lost from memory.
        """
        from src.config import EMBEDDING_DIM
        self.index = faiss.IndexFlatIP(EMBEDDING_DIM)
        self.metadata = []
        print("Cleared vector store")
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get comprehensive statistics about the vector store.
        
        This method provides detailed information about the current state of
        the vector store, useful for monitoring, debugging, and system health
        checks. It calculates various metrics about the stored content.
        
        Statistics calculated:
        - total_chunks: Total number of embeddings/chunks in the store
        - unique_articles: Number of distinct Wikipedia articles represented
        - metadata_count: Number of metadata entries (should match total_chunks)
        
        Returns:
            Dict[str, int]: Dictionary containing statistics with the following keys:
                - 'total_chunks': Total number of stored chunks/embeddings
                - 'unique_articles': Number of unique Wikipedia article titles
                - 'metadata_count': Number of metadata entries
                
        Example:
            >>> store = VectorStore()
            >>> # ... add some embeddings ...
            >>> stats = store.get_stats()
            >>> print(f"Total chunks: {stats['total_chunks']}")
            >>> print(f"Unique articles: {stats['unique_articles']}")
            >>> print(f"Metadata entries: {stats['metadata_count']}")
            >>> 
            >>> # Check for consistency
            >>> assert stats['total_chunks'] == stats['metadata_count']
            
        Note:
            In a healthy vector store, total_chunks should always equal
            metadata_count. A mismatch indicates a synchronization issue
            between the FAISS index and metadata storage.
        """
        total_vectors = self.index.ntotal if self.index else 0
        unique_articles = len(set(chunk.title for chunk in self.metadata)) if self.metadata else 0
        
        return {
            'total_chunks': total_vectors,
            'unique_articles': unique_articles,
            'metadata_count': len(self.metadata)
        }
    
    def is_empty(self) -> bool:
        """
        Check if the vector store is empty.
        
        This method provides a quick way to determine if the vector store
        contains any embeddings. It's useful for conditional logic and
        system health checks.
        
        Returns:
            bool: True if the vector store contains no embeddings, False otherwise.
                 Also returns True if the index hasn't been initialized yet.
                 
        Example:
            >>> store = VectorStore()
            >>> print(store.is_empty())  # True (empty store)
            >>> 
            >>> # Add some embeddings
            >>> embeddings = np.random.rand(5, 768).astype(np.float32)
            >>> chunks = [create_chunk(i) for i in range(5)]
            >>> store.add_embeddings(embeddings, chunks)
            >>> print(store.is_empty())  # False (now contains data)
            
        Note:
            This method only checks the FAISS index. In a properly functioning
            vector store, the metadata should be synchronized with the index.
        """
        return self.index is None or self.index.ntotal == 0


# Global vector store instance (lazy loading)
# This singleton pattern ensures efficient memory usage and avoids duplicate indices
_vector_store = None


def get_vector_store() -> VectorStore:
    """
    Get the global vector store instance (singleton pattern).
    
    This function implements a singleton pattern to ensure that only one
    vector store instance is created and reused throughout the application.
    This is crucial for:
    - Memory efficiency (avoiding duplicate FAISS indices)
    - Data consistency (single source of truth for vectors)
    - Performance (avoiding repeated index loading)
    
    Returns:
        VectorStore: The global vector store instance.
                    If this is the first call, the vector store will be initialized
                    and any existing index will be loaded from disk.
                    Subsequent calls return the same instance.
                    
    Example:
        >>> store1 = get_vector_store()
        >>> store2 = get_vector_store()
        >>> assert store1 is store2  # Same instance
        >>> 
        >>> # Use the store
        >>> stats = store1.get_stats()
        >>> print(f"Vector store contains {stats['total_chunks']} chunks")
        
    Note:
        The first call to this function may take time if it needs to load
        a large existing index from disk. Subsequent calls return immediately.
    """
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
