"""
Configuration settings for the Wikipedia RAG system.

This module contains all configuration constants, paths, and settings for the
Wikipedia-based Retrieval-Augmented Generation (RAG) system. It centralizes
configuration management and provides default values for all system components.

The configuration includes:
- File paths and directory structure
- Model specifications and parameters
- Embedding and vector store settings
- Wikipedia retrieval parameters
- RAG pipeline configuration
- LLM settings and prompt templates

Environment Variables:
    LLM_MODEL_PATH: Path to the LLM model file or Ollama model name
                   Examples: "/path/to/model.gguf" or "mistral:7b-instruct"

Example:
    >>> from src.config import EMBEDDING_MODEL, TOP_K_RETRIEVAL
    >>> print(f"Using embedding model: {EMBEDDING_MODEL}")
    >>> print(f"Retrieving top {TOP_K_RETRIEVAL} chunks")

Note:
    All paths are automatically created if they don't exist.
    Model paths should be adjusted based on your local setup.
"""

import os
from pathlib import Path
from typing import Dict, Any

# Project paths
# These paths define the directory structure for the RAG system
PROJECT_ROOT = Path(__file__).parent.parent  # Root directory of the project
DATA_DIR = PROJECT_ROOT / "data"              # Directory for storing indices and metadata
MODELS_DIR = PROJECT_ROOT / "models"          # Directory for local model files
CACHE_DIR = PROJECT_ROOT / ".cache"           # Directory for temporary cache files

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

# Model configurations
# Default embedding model for generating text embeddings
# intfloat/e5-base-v2 is optimized for retrieval tasks with good performance/speed balance
EMBEDDING_MODEL = "intfloat/e5-base-v2"

# LLM model path - can be a local GGUF file path or Ollama model name
# Examples: "/path/to/model.gguf" for llama-cli, "mistral:7b-instruct" for Ollama
LLM_MODEL_PATH = os.getenv("LLM_MODEL_PATH", "Mistral-7B-Instruct-v0.3-Q6_K")

# Embedding settings
EMBEDDING_DIM = 768  # e5-base-v2 embedding dimension (fixed for this model)
MAX_SEQUENCE_LENGTH = 512  # Maximum input sequence length for the embedding model

# Vector store settings
# File paths for FAISS index and associated metadata
VECTOR_DB_PATH = DATA_DIR / "wikipedia_index.faiss"  # FAISS index file location
METADATA_PATH = DATA_DIR / "wikipedia_metadata.json"  # Chunk metadata storage

# Wikipedia retrieval settings
WIKIPEDIA_SEARCH_RESULTS = 8  # Number of Wikipedia articles to search (increased for better coverage)
CHUNK_SIZE = 600  # Characters per chunk (slightly larger for more context)
CHUNK_OVERLAP = 100  # Overlap between chunks (increased for better continuity)
MAX_CHUNKS_PER_ARTICLE = 15  # Maximum number of chunks to create per Wikipedia article

# RAG settings
TOP_K_RETRIEVAL = 8  # Number of most similar chunks to retrieve for context generation
MIN_SIMILARITY_THRESHOLD = 0.6  # Minimum cosine similarity score to consider a chunk relevant
MAX_CONTEXT_LENGTH = 2000  # Maximum total character length for LLM context (prevents memory issues)

# LLM settings
# Configuration parameters for local language model inference
LLM_CONFIG: Dict[str, Any] = {
    "temperature": 0.7,        # Controls randomness in generation (0.0 = deterministic, 1.0 = very random)
    "max_new_tokens": 512,     # Maximum number of new tokens to generate
    "do_sample": True,         # Whether to use sampling (vs greedy decoding)
    "top_p": 0.9,             # Nucleus sampling parameter (cumulative probability threshold)
    "top_k": 50,              # Top-k sampling parameter (consider only top k tokens)
}

# Prompt templates
# Main system prompt template for the RAG system
# This prompt instructs the LLM on how to use the retrieved context to answer questions
SYSTEM_PROMPT = """You are a helpful assistant that provides clear, informative answers based on the given context. 

Instructions:
1. Use ONLY the information provided in the Context below
2. Provide a comprehensive answer that directly addresses the question
3. If the question is general (like "What is X?"), provide a clear explanation using the available context
4. If the question is specific (asking for dates, names, events), focus on those specific details
5. Organize your answer clearly and avoid being overly wordy
6. If the context doesn't contain enough information to fully answer the question, acknowledge what you can and cannot answer based on the provided information

Context: {context}

Question: {question}

Answer:"""

# Prefixes for the e5 embedding model
# These prefixes help the model distinguish between queries and passages for better retrieval performance
QUERY_PREFIX = "query: "      # Prefix added to user questions before embedding
PASSAGE_PREFIX = "passage: "  # Prefix added to Wikipedia text chunks before embedding
