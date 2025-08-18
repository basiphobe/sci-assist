# Wikipedia RAG System - API Documentation

This document provides comprehensive documentation for all modules in the Wikipedia RAG (Retrieval-Augmented Generation) system.

## Table of Contents

1. [Package Overview (`__init__.py`)](#package-overview)
2. [Configuration (`config.py`)](#configuration-module)
3. [Text Embeddings (`embeddings.py`)](#text-embeddings-module)
4. [LLM Interface (`llm_interface.py`)](#llm-interface-module)
5. [RAG System (`rag_system.py`)](#rag-system-module)
6. [Vector Store (`vector_store.py`)](#vector-store-module)
7. [Wikipedia Retriever (`wikipedia_retriever.py`)](#wikipedia-retriever-module)

---

## Package Overview

### `__init__.py`

**Purpose**: Package initialization and public API exposure.

**Description**: This module defines the public interface of the Wikipedia RAG system, making key classes and functions available for import. It follows the singleton pattern for resource-intensive components to ensure efficient memory usage.

#### Exported Classes:
- `WikipediaRAG` - Main orchestrator class
- `EmbeddingModel` - Text embedding functionality
- `VectorStore` - FAISS-based similarity search
- `WikipediaRetriever` - Wikipedia content retrieval
- `WikipediaChunk` - Data structure for text chunks
- `LLMInterface` - Local LLM interaction

#### Exported Functions:
- `get_embedding_model()` - Singleton embedding model getter
- `get_vector_store()` - Singleton vector store getter
- `get_wikipedia_retriever()` - Singleton retriever getter
- `get_llm_interface()` - Singleton LLM interface getter

#### Usage Example:
```python
from src import WikipediaRAG, get_embedding_model

# Initialize the main system
rag = WikipediaRAG()

# Or use individual components
embedding_model = get_embedding_model()
```

---

## Configuration Module

### `config.py`

**Purpose**: Centralized configuration management for the entire RAG system.

**Description**: Contains all configurable parameters, file paths, model settings, and prompt templates. Automatically creates necessary directories and provides environment variable integration.

#### Key Configuration Sections:

##### **Project Structure**
```python
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"          # Vector indices and metadata
MODELS_DIR = PROJECT_ROOT / "models"      # Model cache directory
CACHE_DIR = PROJECT_ROOT / ".cache"       # Temporary files
```

##### **Model Configuration**
```python
EMBEDDING_MODEL = "intfloat/e5-base-v2"  # Sentence transformer model
LLM_MODEL_PATH = os.getenv("LLM_MODEL_PATH", "Mistral-7B-Instruct-v0.3-Q6_K")
```

##### **Embedding Settings**
```python
EMBEDDING_DIM = 768                       # e5-base-v2 dimension
MAX_SEQUENCE_LENGTH = 512                 # Maximum token length
QUERY_PREFIX = "query: "                  # e5 model query prefix
PASSAGE_PREFIX = "passage: "              # e5 model passage prefix
```

##### **Wikipedia Retrieval Settings**
```python
WIKIPEDIA_SEARCH_RESULTS = 8              # Articles to search per query
CHUNK_SIZE = 600                          # Characters per chunk
CHUNK_OVERLAP = 100                       # Overlap between chunks
MAX_CHUNKS_PER_ARTICLE = 15               # Maximum chunks per article
```

##### **RAG Pipeline Settings**
```python
TOP_K_RETRIEVAL = 8                       # Chunks to retrieve
MIN_SIMILARITY_THRESHOLD = 0.6            # Minimum relevance score
MAX_CONTEXT_LENGTH = 2000                 # Maximum LLM context
```

##### **LLM Configuration**
```python
LLM_CONFIG = {
    "temperature": 0.7,                   # Response creativity
    "max_new_tokens": 512,               # Maximum response length
    "do_sample": True,                   # Enable sampling
    "top_p": 0.9,                       # Nucleus sampling
    "top_k": 50,                        # Top-k sampling
}
```

##### **System Prompt Template**
The `SYSTEM_PROMPT` defines how the LLM should behave and format responses, with placeholders for context and questions.

#### Environment Variables:
- `LLM_MODEL_PATH`: Path to local LLM model file

---

## Text Embeddings Module

### `embeddings.py`

**Purpose**: Text embedding generation using sentence-transformers for semantic similarity.

**Description**: Provides a unified interface for converting text into high-dimensional vector representations using the e5-base-v2 model. Handles both query and passage embeddings with appropriate prefixes for optimal performance.

#### Class: `EmbeddingModel`

##### **Initialization**
```python
def __init__(self, model_name: str = EMBEDDING_MODEL)
```
- Loads the specified sentence transformer model
- Automatically detects and uses CUDA if available
- Sets up device-appropriate processing

##### **Key Methods**

###### `embed_query(query: str) -> np.ndarray`
**Purpose**: Convert user queries into embeddings for retrieval.

**Parameters**:
- `query`: User's question or search term

**Returns**: 
- `np.ndarray`: 768-dimensional embedding vector (float32)

**Usage**:
```python
model = EmbeddingModel()
query_emb = model.embed_query("What causes earthquakes?")
```

###### `embed_passages(passages: List[str]) -> np.ndarray`
**Purpose**: Batch embedding of text passages for efficient storage.

**Parameters**:
- `passages`: List of text chunks to embed

**Returns**: 
- `np.ndarray`: Matrix of embeddings (n_passages × 768)

**Features**:
- Batch processing for efficiency
- Progress bar for long operations
- Automatic prefixing for e5 model optimization

###### `embed_single_passage(passage: str) -> np.ndarray`
**Purpose**: Embed individual text passages.

**Parameters**:
- `passage`: Single text chunk

**Returns**: 
- `np.ndarray`: 768-dimensional embedding vector

##### **Technical Details**

- **Model**: Uses `intfloat/e5-base-v2` by default
- **Prefixes**: Adds "query: " for queries, "passage: " for passages
- **Device Support**: Automatic CUDA/CPU detection
- **Output Format**: Float32 numpy arrays for FAISS compatibility
- **Normalization**: Embeddings are suitable for cosine similarity

##### **Singleton Pattern**
```python
def get_embedding_model() -> EmbeddingModel:
    """Returns global embedding model instance"""
```

#### Performance Characteristics:
- **GPU Acceleration**: 10-50x faster on CUDA-enabled systems
- **Batch Processing**: Efficient for multiple passages
- **Memory Usage**: ~2GB GPU memory for model loading

---

## LLM Interface Module

### `llm_interface.py`

**Purpose**: Interface for local Large Language Model interaction supporting multiple backends.

**Description**: Provides a unified API for generating answers using local LLMs. Supports both llama.cpp (via llama-cli) and Ollama backends with intelligent output parsing and GPU optimization.

#### Class: `LLMInterface`

##### **Initialization**
```python
def __init__(self, model_path: str = LLM_MODEL_PATH)
```
- Configures model path and LLM parameters
- Supports both file paths (llama-cli) and model names (Ollama)

##### **Key Methods**

###### `generate_answer(context: str, question: str) -> str`
**Purpose**: Generate answers using retrieved Wikipedia context.

**Parameters**:
- `context`: Retrieved and formatted Wikipedia content
- `question`: User's original question

**Returns**: 
- `str`: Generated answer text

**Process**:
1. Formats context and question using system prompt template
2. Calls appropriate LLM backend
3. Parses and cleans response
4. Removes technical artifacts and repetition

##### **Backend Support**

###### **llama-cli Backend** (`_call_llama_cli`)
**Features**:
- Direct GGUF model loading
- GPU acceleration with CUDA
- Memory optimization (single GPU constraint)
- Advanced output parsing

**Configuration**:
```python
cmd = [
    "llama-cli",
    "-m", model_path,              # Model file
    "-p", prompt,                  # Input prompt
    "-n", "100",                   # Token limit
    "-ngl", "35",                  # GPU layers
    "--split-mode", "none",        # No GPU splitting
    "--main-gpu", "0"              # Use GPU 0 only
]
```

**Environment Variables**:
- `CUDA_VISIBLE_DEVICES=0` - Forces single GPU usage

###### **Ollama Backend** (`_call_ollama`)
**Features**:
- Model management through Ollama
- Automatic GPU acceleration
- Simple model specification by name

**Usage**:
```python
# For Ollama: set model_path to "model:tag" format
llm = LLMInterface("mistral:7b-instruct")
```

##### **Output Processing Pipeline**

The system includes sophisticated output cleaning:

1. **Technical Metadata Removal**:
   - CUDA device information
   - Model loading messages
   - Performance statistics

2. **Prompt Echo Filtering**:
   - System prompt fragments
   - Context repetition
   - Source citations

3. **Response Cleaning**:
   - Leading/trailing artifacts
   - Repetitive sentences
   - Incomplete thoughts

4. **Quality Assurance**:
   - Minimum response length validation
   - Coherence checking
   - Error handling

##### **Error Handling**

- **Model Not Found**: Clear error messages with setup instructions
- **GPU Memory Issues**: Automatic fallback suggestions
- **Timeout Protection**: 3-minute limit with informative messages
- **Process Failures**: Detailed error reporting with debugging info

##### **Performance Optimization**

- **GPU Constraint**: Uses only GTX 1070 (GPU 0) to avoid memory conflicts
- **Memory Management**: Prevents out-of-memory errors on secondary GPU
- **Timeout Handling**: Graceful handling of long-running generations
- **Background Process Support**: Non-blocking execution options

#### Usage Examples:

```python
# Basic usage
llm = LLMInterface()
answer = llm.generate_answer(context, "What causes earthquakes?")

# Custom model
llm = LLMInterface("/path/to/custom/model.gguf")

# Ollama usage
llm = LLMInterface("llama2:7b-chat")
```

---

## RAG System Module

### `rag_system.py`

**Purpose**: Main orchestrator that coordinates all RAG system components.

**Description**: The `WikipediaRAG` class implements the complete RAG pipeline, managing Wikipedia retrieval, vector similarity search, context formatting, and answer generation. Provides intelligent caching and auto-indexing capabilities.

#### Class: `WikipediaRAG`

##### **Architecture Overview**

The RAG system follows this pipeline:
1. **Query Processing** → 2. **Context Retrieval** → 3. **Content Formatting** → 4. **Answer Generation**

##### **Initialization**
```python
def __init__(self):
```
Initializes all system components:
- `EmbeddingModel`: For text vectorization
- `VectorStore`: For similarity search
- `WikipediaRetriever`: For content acquisition
- `LLMInterface`: For answer generation

##### **Core Methods**

###### `retrieve_context(query: str) -> Tuple[List[WikipediaChunk], List[float]]`
**Purpose**: Intelligent context retrieval with auto-indexing.

**Process**:
1. Converts query to embedding vector
2. Searches existing vector store for similar content
3. Applies diversity filtering to avoid same-source bias
4. Auto-indexes new content if similarity scores are low (<0.8)
5. Returns top-k most relevant chunks with scores

**Features**:
- **Adaptive Thresholding**: Lowers similarity requirements when needed
- **Source Diversity**: Limits chunks per article for broader coverage
- **Auto-Indexing**: Fetches new Wikipedia content for novel topics
- **Performance Optimization**: 2x candidate retrieval for better filtering

###### `format_context(chunks: List[WikipediaChunk]) -> str`
**Purpose**: Converts retrieved chunks into LLM-readable format.

**Features**:
- Source attribution with clean formatting
- Length management (respects MAX_CONTEXT_LENGTH)
- Priority-based inclusion (most relevant first)

**Output Format**:
```
Source 1 (from Article Title):
[Chunk content...]

Source 2 (from Another Article):
[Chunk content...]
```

###### `query(question: str) -> str`
**Purpose**: Complete RAG pipeline execution.

**Process**:
1. **Context Retrieval**: Gets relevant Wikipedia chunks
2. **Relevance Filtering**: Applies similarity thresholds
3. **Auto-Indexing**: Fetches new content if needed
4. **Context Formatting**: Prepares LLM input
5. **Answer Generation**: Calls LLM with formatted context
6. **Debug Output**: Shows retrieved context for transparency

**Error Handling**:
- Empty index handling with auto-indexing
- Low similarity detection and remediation
- Graceful degradation for failed retrievals

##### **Advanced Features**

###### **Smart Auto-Indexing**
```python
auto_index_threshold = 0.8  # Trigger for new content
if max(scores) < auto_index_threshold:
    # Fetch fresh Wikipedia content
```

###### **Diversity Filtering**
```python
max_per_article = 3  # Limit chunks per source
# Ensures varied information sources
```

###### **Adaptive Similarity Thresholds**
```python
adaptive_threshold = max(0.5, MIN_SIMILARITY_THRESHOLD - 0.15)
# Relaxes requirements for better coverage
```

##### **System Management**

###### `get_stats() -> dict`
**Purpose**: Provides system health and usage statistics.

**Returns**:
```python
{
    'embedding_model': 'intfloat/e5-base-v2',
    'embedding_dimension': 768,
    'vector_store_stats': {
        'total_chunks': 178,
        'unique_articles': 15
    },
    'llm_model': '/path/to/model.gguf'
}
```

###### `clear_index()`
**Purpose**: Resets vector store for fresh starts.

#### Usage Examples:

```python
# Basic usage
rag = WikipediaRAG()
answer = rag.query("What causes earthquakes?")

# System inspection
stats = rag.get_stats()
print(f"Indexed {stats['vector_store_stats']['total_chunks']} chunks")

# Manual reset
rag.clear_index()  # Start fresh
```

#### Performance Characteristics:

- **Cold Start**: 10-30 seconds (includes Wikipedia fetching)
- **Warm Queries**: 2-5 seconds (uses cached embeddings)
- **Memory Usage**: ~3-4GB GPU, 2-3GB RAM
- **Scalability**: Handles 1000+ cached chunks efficiently

---

## Vector Store Module

### `vector_store.py`

**Purpose**: FAISS-based vector database for efficient similarity search and persistent storage.

**Description**: Implements a high-performance vector store using Facebook's FAISS library. Provides cosine similarity search, persistent storage, and efficient batch operations for the RAG system's knowledge base.

#### Class: `VectorStore`

##### **Architecture Overview**

- **Index Type**: FAISS IndexFlatIP (Inner Product for cosine similarity)
- **Storage**: Persistent disk storage with metadata
- **Search**: Sub-linear similarity search with configurable k
- **Memory**: Efficient in-memory operations with lazy loading

##### **Initialization**
```python
def __init__(self, embedding_dim: int = EMBEDDING_DIM):
```
- Creates or loads FAISS index with specified dimensions
- Initializes metadata storage for chunk information
- Automatically handles existing index files

##### **Core Methods**

###### `add_embeddings(embeddings: np.ndarray, chunks: List[WikipediaChunk])`
**Purpose**: Add new embeddings and associated metadata to the store.

**Parameters**:
- `embeddings`: Float32 numpy array (n_vectors × embedding_dim)
- `chunks`: Corresponding WikipediaChunk objects with metadata

**Process**:
1. Normalizes embeddings for cosine similarity
2. Adds vectors to FAISS index
3. Stores chunk metadata separately
4. Maintains index-metadata alignment

**Features**:
- **Automatic Normalization**: Ensures cosine similarity compatibility
- **Batch Processing**: Efficient bulk insertions
- **Metadata Preservation**: Maintains chunk information and source attribution

###### `search(query_embedding: np.ndarray, k: int) -> List[Tuple[WikipediaChunk, float]]`
**Purpose**: Find k most similar chunks to query embedding.

**Parameters**:
- `query_embedding`: Query vector (embedding_dim,)
- `k`: Number of results to return

**Returns**: 
- List of (chunk, similarity_score) tuples, sorted by relevance

**Algorithm**:
1. Normalizes query embedding
2. Performs FAISS similarity search
3. Retrieves corresponding metadata
4. Returns scored results

**Performance**: O(n) for flat index, sub-millisecond for typical queries

##### **Persistence Management**

###### `save_index()`
**Purpose**: Persist index and metadata to disk.

**Files Created**:
- `wikipedia_index.faiss`: FAISS binary index
- `wikipedia_metadata.json`: Chunk metadata and source info

**Features**:
- **Atomic Operations**: Safe concurrent access
- **Compression**: JSON metadata with efficient serialization
- **Versioning**: Compatible across system restarts

###### `load_index()`
**Purpose**: Restore index and metadata from disk.

**Process**:
1. Loads FAISS index from binary file
2. Reconstructs WikipediaChunk objects from JSON
3. Validates index-metadata consistency
4. Reports loading statistics

##### **Metadata Management**

The system stores rich metadata for each chunk:
```python
{
    "text": "chunk content...",
    "title": "Wikipedia Article Title",
    "url": "https://en.wikipedia.org/wiki/...",
    "chunk_id": 0,
    "start_pos": 0,
    "end_pos": 150
}
```

##### **System Operations**

###### `is_empty() -> bool`
**Purpose**: Check if vector store contains any data.

###### `get_stats() -> Dict[str, int]`
**Purpose**: Return store statistics.

**Returns**:
```python
{
    'total_chunks': 178,
    'unique_articles': 15
}
```

###### `clear()`
**Purpose**: Reset store to empty state.

##### **Technical Specifications**

- **Index Type**: FAISS IndexFlatIP (exact search)
- **Similarity Metric**: Cosine similarity via inner product
- **Vector Format**: Float32 normalized embeddings
- **Storage Format**: Binary FAISS + JSON metadata
- **Memory Usage**: ~4 bytes per dimension per vector
- **Search Complexity**: O(n×d) where n=vectors, d=dimensions

##### **Performance Optimization**

- **Normalized Storage**: Pre-computed for faster search
- **Batch Operations**: Efficient multi-vector insertions
- **Memory Layout**: Contiguous arrays for cache efficiency
- **Lazy Loading**: On-demand index initialization

#### Usage Examples:

```python
# Initialize store
store = VectorStore(embedding_dim=768)

# Add content
embeddings = model.embed_passages(texts)
store.add_embeddings(embeddings, chunks)
store.save_index()

# Search
query_emb = model.embed_query("earthquakes")
results = store.search(query_emb, k=5)
for chunk, score in results:
    print(f"{score:.3f}: {chunk.title}")
```

#### Error Handling:

- **Dimension Mismatches**: Clear error messages for incompatible embeddings
- **File I/O Errors**: Graceful handling of corrupted or missing files
- **Memory Issues**: Warnings for large index operations

---

## Wikipedia Retriever Module

### `wikipedia_retriever.py`

**Purpose**: Wikipedia content acquisition, processing, and intelligent chunking for RAG pipeline.

**Description**: Handles all Wikipedia interactions including search, content retrieval, text cleaning, and semantic chunking. Designed for reliability and efficiency with comprehensive error handling.

#### Data Structure: `WikipediaChunk`

```python
@dataclass
class WikipediaChunk:
    """Immutable chunk with complete metadata"""
    text: str          # Cleaned chunk content
    title: str         # Wikipedia article title
    url: str           # Full Wikipedia URL
    chunk_id: int      # Sequential chunk identifier
    start_pos: int     # Character position in source
    end_pos: int       # End character position
```

#### Class: `WikipediaRetriever`

##### **Initialization**
```python
def __init__(self):
```
- Sets Wikipedia language to English
- Configures retrieval parameters from config
- Initializes error handling and retry logic

##### **Content Acquisition**

###### `search_wikipedia(query: str, max_results: int) -> List[str]`
**Purpose**: Find relevant Wikipedia articles for a query.

**Process**:
1. Executes Wikipedia search API call
2. Returns article titles ranked by relevance
3. Handles disambiguation and errors gracefully

**Error Handling**:
- **API Timeouts**: Graceful degradation with partial results
- **Network Issues**: Retry logic with exponential backoff
- **No Results**: Empty list return with logging

###### `get_page_content(title: str) -> Optional[Tuple[str, str]]`
**Purpose**: Retrieve full text content and URL for a Wikipedia page.

**Parameters**:
- `title`: Wikipedia article title

**Returns**: 
- `(content, url)` tuple or None if failed

**Features**:
- **Disambiguation Handling**: Automatically selects first option
- **Redirect Following**: Resolves Wikipedia redirects
- **Error Recovery**: Graceful handling of missing/deleted pages

##### **Content Processing**

###### `clean_text(text: str) -> str`
**Purpose**: Normalize Wikipedia text for embedding and LLM consumption.

**Cleaning Operations**:
1. **Citation Removal**: Strips `[1]`, `[2]`, etc.
2. **Whitespace Normalization**: Converts multiple spaces/newlines
3. **Unicode Handling**: Ensures proper text encoding
4. **Special Character Processing**: Preserves readability

**Before/After Example**:
```python
# Before
"Earthquakes[1] are caused by tectonic    movement.\n\n\nThey can be    dangerous[2]."

# After  
"Earthquakes are caused by tectonic movement. They can be dangerous."
```

##### **Intelligent Chunking**

###### `chunk_text(text: str, title: str, url: str) -> List[WikipediaChunk]`
**Purpose**: Split articles into semantically coherent chunks.

**Algorithm**:
1. **Size-Based Splitting**: Uses CHUNK_SIZE (600 chars) as base
2. **Sentence Boundary Respect**: Ends chunks at sentence boundaries
3. **Overlap Management**: CHUNK_OVERLAP (100 chars) for context continuity
4. **Quality Control**: Validates chunk coherence and length

**Parameters from Config**:
- `CHUNK_SIZE = 600`: Target characters per chunk
- `CHUNK_OVERLAP = 100`: Overlap between adjacent chunks
- `MAX_CHUNKS_PER_ARTICLE = 15`: Limit to prevent article dominance

**Smart Boundary Detection**:
```python
# Find sentence ending within overlap region
sentence_end = text.rfind('.', start, end + CHUNK_OVERLAP)
if sentence_end != -1 and sentence_end > start + CHUNK_SIZE // 2:
    end = sentence_end + 1  # Include the period
```

##### **Pipeline Integration**

###### `retrieve_and_chunk(query: str) -> List[WikipediaChunk]`
**Purpose**: Complete pipeline from query to chunked content.

**Process**:
1. **Search Phase**: Find relevant articles
2. **Retrieval Phase**: Download article content
3. **Processing Phase**: Clean and normalize text
4. **Chunking Phase**: Create overlapping semantic chunks
5. **Validation Phase**: Ensure quality and completeness

**Performance Monitoring**:
- Progress reporting for long operations
- Statistics collection (articles processed, chunks created)
- Error aggregation and reporting

**Example Output**:
```
Processing Wikipedia page: Earthquake
Created 15 chunks from Earthquake
Processing Wikipedia page: Seismic magnitude scales  
Created 12 chunks from Seismic magnitude scales
Total chunks created: 98
```

##### **Error Handling & Resilience**

- **Network Failures**: Retry with exponential backoff
- **API Rate Limits**: Automatic throttling and delay
- **Malformed Content**: Skip corrupted articles gracefully
- **Empty Results**: Clear reporting of acquisition failures

##### **Quality Assurance**

- **Content Validation**: Ensures minimum chunk length and coherence
- **Encoding Safety**: Handles various text encodings properly
- **Metadata Integrity**: Validates all chunk metadata fields
- **Duplication Prevention**: Avoids redundant content acquisition

##### **Performance Characteristics**

- **Throughput**: ~2-5 articles per second (network dependent)
- **Chunk Rate**: ~50-100 chunks per second (processing)
- **Memory Usage**: ~10MB per article during processing
- **Network Usage**: ~50KB per article average

#### Usage Examples:

```python
# Initialize retriever
retriever = WikipediaRetriever()

# Search and retrieve
titles = retriever.search_wikipedia("quantum computing", max_results=5)
chunks = retriever.retrieve_and_chunk("quantum computing")

# Process specific article
content, url = retriever.get_page_content("Quantum computing")
if content:
    chunks = retriever.chunk_text(content, "Quantum computing", url)
```

##### **Singleton Pattern**
```python
def get_wikipedia_retriever() -> WikipediaRetriever:
    """Returns global retriever instance"""
```

#### Configuration Integration:

All parameters are configurable via `config.py`:
- Search result limits
- Chunk size and overlap
- Article processing limits
- API timeout settings

This comprehensive retrieval system ensures high-quality, well-structured content for the RAG pipeline while maintaining reliability and performance.

---

## System Integration

### Component Interaction Flow

1. **Query Input** → `WikipediaRAG.query()`
2. **Embedding Generation** → `EmbeddingModel.embed_query()`
3. **Similarity Search** → `VectorStore.search()`
4. **Content Retrieval** → `WikipediaRetriever.retrieve_and_chunk()` (if needed)
5. **Context Formatting** → `WikipediaRAG.format_context()`
6. **Answer Generation** → `LLMInterface.generate_answer()`

### Performance Optimization

- **Singleton Pattern**: Prevents resource duplication
- **Lazy Loading**: Components initialize only when needed
- **Persistent Storage**: Vector indices survive system restarts
- **GPU Acceleration**: Optimized for CUDA when available
- **Batch Processing**: Efficient multi-document operations

### Error Handling Strategy

- **Graceful Degradation**: System continues with partial functionality
- **Informative Messages**: Clear error reporting for debugging
- **Recovery Mechanisms**: Automatic retry and fallback options
- **Resource Management**: Proper cleanup and memory management

This documentation provides complete coverage of the Wikipedia RAG system's architecture and implementation details for developers and system administrators.
