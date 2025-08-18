# Wikipedia-Powered RAG System

A Retrieval-Augmented Generation (RAG) pipeline that searches Wikipedia, retrieves relevant content, and uses a local LLM to generate contextual answers.

## Features

- **Text Embedding**: Uses `intfloat/e5-base-v2` for high-quality text embeddings
- **Vector Search**: FAISS-powered similarity search for fast retrieval
- **Wikipedia Integration**: Live Wikipedia search and content chunking
- **Local LLM**: Mistral-7B-Instruct-v0.3-Q6_K for answer generation
- **Modular Design**: Clean, testable, and extensible architecture

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the RAG system:
```python
from src.rag_system import WikipediaRAG

# Initialize the RAG system
rag = WikipediaRAG()

# Ask a question
answer = rag.query("What is quantum computing?")
print(answer)
```

## Architecture

```
User Query → Embedding Model → Vector Search → Context Retrieval → LLM → Answer
```

## Components

- `src/embeddings.py` - Text embedding functionality
- `src/vector_store.py` - FAISS vector database operations
- `src/wikipedia_retriever.py` - Wikipedia search and chunking
- `src/llm_interface.py` - Local LLM integration
- `src/rag_system.py` - Main RAG pipeline
- `src/config.py` - Configuration settings

## Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd ajsgptrag
```

2. **Set up the environment:**
```bash
# Using the setup script
bash setup.sh
# or for Fish shell users
fish setup.fish
```

3. **Set environment variables:**
```bash
# For llama.cpp
export LLM_MODEL_PATH="/path/to/your/model.gguf"

# For Ollama
export LLM_MODEL_PATH="mistral:7b-instruct"
```

## Usage

### Command Line Interface
```bash
# Interactive mode
python cli.py

# Single query
python cli.py -q "What is quantum computing?"

# Show system statistics  
python cli.py --stats

# Clear vector index
python cli.py --clear
```

### Python API
```python
from src.rag_system import WikipediaRAG

# Initialize the system
rag = WikipediaRAG()

# Ask questions
answer = rag.query("What is machine learning?")
print(answer)

# Get system stats
stats = rag.get_stats()
print(f"Indexed {stats['vector_store_stats']['total_chunks']} chunks")
```

## System Requirements

- **Python**: 3.8+
- **Memory**: 4GB+ RAM (8GB+ recommended)
- **Storage**: 2GB+ free space for models and indices
- **GPU** (optional): NVIDIA GPU with CUDA for faster inference

## Testing

Run the test suite to ensure everything works correctly:

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src
```

The test suite includes:
- Unit tests for all major components
- Integration tests for the RAG pipeline
- Isolated testing with temporary vector stores
- Mock testing for external dependencies

## Documentation

- **[Usage Guide](USAGE.md)** - Comprehensive usage instructions
- **[API Documentation](docs/API_DOCUMENTATION.md)** - Complete API reference
- **[Configuration Examples](llm_config_examples.py)** - LLM setup examples

## License

MIT License - see [LICENSE](LICENSE) file for details.
