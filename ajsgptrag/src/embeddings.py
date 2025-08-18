"""
Text embedding functionality using sentence-transformers.

This module provides text embedding capabilities using the sentence-transformers library,
specifically optimized for the e5-base-v2 model. The module handles both query and passage
embeddings with appropriate prefixes for optimal retrieval performance.

The EmbeddingModel class provides:
- Query embedding for user questions
- Passage embedding for Wikipedia content chunks
- Batch processing for efficient embedding generation
- GPU acceleration when available

Key Features:
- Automatic GPU detection and utilization
- Model-specific prefixes for e5-base-v2 optimization
- Efficient batch processing for large document collections
- Numpy array output for FAISS compatibility

Example:
    >>> from src.embeddings import EmbeddingModel
    >>> model = EmbeddingModel()
    >>> query_emb = model.embed_query("What is machine learning?")
    >>> passages = ["Machine learning is...", "AI is a field..."]
    >>> passage_embs = model.embed_passages(passages)

Dependencies:
    - torch: For GPU acceleration
    - sentence-transformers: For embedding model
    - numpy: For array operations
"""

import torch
from sentence_transformers import SentenceTransformer
from typing import List, Union
import numpy as np
from src.config import EMBEDDING_MODEL, EMBEDDING_DIM, QUERY_PREFIX, PASSAGE_PREFIX


class EmbeddingModel:
    """
    Handles text embedding using the e5-base-v2 model.
    
    This class provides a unified interface for generating embeddings from text,
    with specialized methods for queries and passages. It automatically handles
    model loading, GPU acceleration, and the specific prefixes required by the
    e5-base-v2 model for optimal retrieval performance.
    
    The e5-base-v2 model is specifically designed for retrieval tasks and requires
    different prefixes for queries and passages to achieve optimal performance:
    - Queries should be prefixed with "query: "
    - Passages should be prefixed with "passage: "
    
    Attributes:
        model_name (str): Name of the sentence transformer model
        device (str): Device used for inference ('cuda' or 'cpu')
        model (SentenceTransformer): The loaded embedding model
        embedding_dim (int): Dimension of the output embeddings
    
    Example:
        >>> embedding_model = EmbeddingModel()
        >>> query_embedding = embedding_model.embed_query("What is Python?")
        >>> print(f"Query embedding shape: {query_embedding.shape}")
        >>> 
        >>> passages = ["Python is a programming language", "Python was created in 1991"]
        >>> passage_embeddings = embedding_model.embed_passages(passages)
        >>> print(f"Passage embeddings shape: {passage_embeddings.shape}")
    """
    
    def __init__(self, model_name: str = EMBEDDING_MODEL):
        """
        Initialize the embedding model.
        
        Loads the specified sentence transformer model and configures it for
        the available hardware (GPU if available, otherwise CPU). The model
        is downloaded automatically if not present locally.
        
        Args:
            model_name (str): Name of the sentence transformer model to use.
                            Defaults to the value from config.EMBEDDING_MODEL.
                            Examples: "intfloat/e5-base-v2", "all-MiniLM-L6-v2"
        
        Raises:
            Exception: If the model cannot be loaded or is not found.
            
        Note:
            The first run may take time as the model needs to be downloaded.
            Subsequent runs will use the cached model.
        """
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading embedding model: {model_name} on {self.device}")
        
        self.model = SentenceTransformer(model_name, device=self.device)
        self.embedding_dim = EMBEDDING_DIM
        
    def embed_query(self, query: str) -> np.ndarray:
        """
        Embed a user query for retrieval.
        
        This method processes a user's question or query by adding the appropriate
        prefix and generating an embedding vector that can be used for similarity
        search against passage embeddings.
        
        Args:
            query (str): The user's question or search query.
                        Example: "What is machine learning?"
            
        Returns:
            np.ndarray: Query embedding as a 1D numpy array of shape (embedding_dim,).
                       The embedding is normalized and ready for cosine similarity
                       comparison with passage embeddings.
                       
        Example:
            >>> model = EmbeddingModel()
            >>> embedding = model.embed_query("What is Python?")
            >>> print(f"Embedding shape: {embedding.shape}")  # (768,)
            >>> print(f"Embedding type: {type(embedding)}")   # <class 'numpy.ndarray'>
        """
        # Add query prefix for e5 model
        prefixed_query = QUERY_PREFIX + query
        embedding = self.model.encode(prefixed_query, convert_to_numpy=True)
        return embedding.astype(np.float32)
    
    def embed_passages(self, passages: List[str]) -> np.ndarray:
        """
        Embed multiple text passages for storage in the vector database.
        
        This method efficiently processes multiple text passages (such as Wikipedia
        chunks) by adding appropriate prefixes and generating embedding vectors in
        batches for optimal performance.
        
        Args:
            passages (List[str]): List of text passages to embed.
                                 Each passage should be a meaningful chunk of text.
                                 Example: ["Python is a programming language...", 
                                          "Machine learning is a subset of AI..."]
            
        Returns:
            np.ndarray: Passage embeddings as a 2D numpy array of shape 
                       (num_passages, embedding_dim). Each row represents
                       the embedding for one passage.
                       
        Example:
            >>> model = EmbeddingModel()
            >>> passages = [
            ...     "Python is a high-level programming language.",
            ...     "Machine learning uses statistical techniques."
            ... ]
            >>> embeddings = model.embed_passages(passages)
            >>> print(f"Embeddings shape: {embeddings.shape}")  # (2, 768)
            
        Note:
            - Uses batch processing for efficiency
            - Shows progress bar for large batches
            - Automatically handles GPU memory management
        """
        # Add passage prefix for e5 model
        prefixed_passages = [PASSAGE_PREFIX + passage for passage in passages]
        embeddings = self.model.encode(
            prefixed_passages, 
            convert_to_numpy=True,
            show_progress_bar=True,
            batch_size=32
        )
        return embeddings.astype(np.float32)
    
    def embed_single_passage(self, passage: str) -> np.ndarray:
        """
        Embed a single text passage.
        
        This method is optimized for embedding individual passages without the
        overhead of batch processing. It's useful for real-time embedding of
        single documents or when processing passages one at a time.
        
        Args:
            passage (str): Text passage to embed.
                          Should be a meaningful chunk of text.
                          Example: "Python is a versatile programming language..."
            
        Returns:
            np.ndarray: Passage embedding as a 1D numpy array of shape (embedding_dim,).
                       The embedding is normalized and ready for similarity comparison.
                       
        Example:
            >>> model = EmbeddingModel()
            >>> passage = "Natural language processing is a subfield of AI."
            >>> embedding = model.embed_single_passage(passage)
            >>> print(f"Single passage embedding shape: {embedding.shape}")  # (768,)
            
        Note:
            For multiple passages, use embed_passages() for better efficiency.
        """
        prefixed_passage = PASSAGE_PREFIX + passage
        embedding = self.model.encode(prefixed_passage, convert_to_numpy=True)
        return embedding.astype(np.float32)
    
    def get_embedding_dim(self) -> int:
        """
        Get the dimension of the embeddings produced by this model.
        
        Returns:
            int: The embedding dimension (e.g., 768 for e5-base-v2).
                 This value is used to initialize the FAISS vector store
                 with the correct dimensionality.
                 
        Example:
            >>> model = EmbeddingModel()
            >>> dim = model.get_embedding_dim()
            >>> print(f"Embedding dimension: {dim}")  # 768
        """
        return self.embedding_dim


# Global embedding model instance (lazy loading)
# This singleton pattern ensures efficient memory usage and avoids reloading the model
_embedding_model = None


def get_embedding_model() -> EmbeddingModel:
    """
    Get the global embedding model instance (singleton pattern).
    
    This function implements a singleton pattern to ensure that only one
    embedding model instance is created and reused throughout the application.
    This is important for memory efficiency, as loading multiple instances
    of the same model would waste significant GPU/CPU memory.
    
    Returns:
        EmbeddingModel: The global embedding model instance.
                       If this is the first call, the model will be loaded.
                       Subsequent calls return the same instance.
                       
    Example:
        >>> model1 = get_embedding_model()
        >>> model2 = get_embedding_model()
        >>> assert model1 is model2  # Same instance
        
    Note:
        The first call to this function may take time as it loads the model.
        All subsequent calls return immediately with the cached instance.
    """
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = EmbeddingModel()
    return _embedding_model
