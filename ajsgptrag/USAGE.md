# Wikipedia RAG System - Usage Guide

## Quick Start

### 1. Installation
```fish
# Clone and setup (Fish shell)
git clone <your-repo-url>
cd ajsgptrag
fish setup.fish
```

For bash/zsh users:
```bash
# Clone and setup (Bash/Zsh)
git clone <your-repo-url>
cd ajsgptrag
bash setup.sh
```

### 2. Configure LLM
The system is configured via environment variables. See `llm_config_examples.py` for reference configurations.

### 3. Set Environment Variables
```fish
# For llama.cpp
set -x LLM_MODEL_PATH "/path/to/Mistral-7B-Instruct-v0.3-Q6_K.gguf"

# For Ollama  
set -x LLM_MODEL_PATH "mistral:7b-instruct"
```

For bash/zsh users:
```bash
# For llama.cpp
export LLM_MODEL_PATH="/path/to/Mistral-7B-Instruct-v0.3-Q6_K.gguf"

# For Ollama
export LLM_MODEL_PATH="mistral:7b-instruct"
```

### 4. Run the System
```fish
# Interactive mode
python cli.py

# Single query
python cli.py -q "What is quantum computing?"

# Run demo
python examples/demo.py
```

## Detailed Usage

### Command Line Interface

The CLI provides several modes of operation:

```fish
# Interactive mode (default)
python cli.py

# Single query mode
python cli.py -q "Your question here"

# Show system statistics
python cli.py --stats

# Clear vector index
python cli.py --clear

# Help
python cli.py --help
```

### Python API

```python
from src.rag_system import WikipediaRAG

# Initialize
rag = WikipediaRAG()

# Ask questions
answer = rag.query("What is machine learning?")
print(answer)

# Get system statistics
stats = rag.get_stats()
print(stats)
```

### Advanced Usage

#### Custom Configuration
```python
from src.config import LLM_CONFIG

# Modify LLM settings
LLM_CONFIG.update({
    "temperature": 0.5,
    "max_new_tokens": 256
})
```

#### Batch Processing
```python
questions = [
    "What is photosynthesis?",
    "How do vaccines work?",
    "What causes climate change?"
]

for question in questions:
    answer = rag.query(question)
    print(f"Q: {question}")
    print(f"A: {answer}\n")
```

#### Context Inspection
```python
# See what context was retrieved
chunks, scores = rag.retrieve_context("quantum computing")

for chunk, score in zip(chunks, scores):
    print(f"Title: {chunk.title}")
    print(f"Score: {score:.3f}")
    print(f"Text: {chunk.text[:100]}...")
    print("-" * 40)
```

## System Architecture

```
User Query
    ↓
[Embedding Model] ← intfloat/e5-base-v2
    ↓
[Vector Search] ← FAISS
    ↓
[Wikipedia Retrieval] ← wikipedia package
    ↓
[Context Formatting]
    ↓
[LLM Generation] ← Mistral-7B-Instruct-v0.3-Q6_K
    ↓
Generated Answer
```

## Configuration Files

- `src/config.py` - Main configuration settings
- `llm_config_examples.py` - LLM integration examples
- `requirements.txt` - Python dependencies

## Data Storage

- `data/wikipedia_index.faiss` - FAISS vector index
- `data/wikipedia_metadata.json` - Chunk metadata
- `.cache/` - Model cache directory

## Troubleshooting

### Common Issues

1. **ImportError: No module named 'sentence_transformers'**
   ```fish
   pip install sentence-transformers
   ```

2. **FAISS installation issues**
   ```fish
   # CPU version
   pip install faiss-cpu
   
   # GPU version (if you have CUDA)
   pip install faiss-gpu
   ```

3. **Wikipedia search failures**
   - Check internet connection
   - Try different search terms
   - Wikipedia API might be temporarily unavailable

4. **LLM not responding or hanging**
   - Verify `LLM_MODEL_PATH` environment variable points to your model file
   - Check if model file exists and is readable
   - Ensure llama.cpp/Ollama is properly installed with GPU support
   - **GPU Setup for llama.cpp**: Ensure llama.cpp was compiled with CUDA support for NVIDIA GPUs
   - **GTX 1070 Users**: System is configured for 35 GPU layers (-ngl 35). Adjust in `src/llm_interface.py` if needed
   - **Model loading timeout**: GPU models should load in 30-60 seconds. CPU models (7B+) can take 2-5 minutes
   - Try a smaller model first (3B or 1B) to test the system
   - Use `llama-cli -m /path/to/model.gguf -p "test" -n 10 -ngl 35` to test GPU acceleration directly

5. **Slow model inference**
   - Models run much faster on GPU - consider GPU acceleration
   - Use quantized models (Q4_K_M is good balance of speed/quality)
   - Reduce `max_new_tokens` in config for faster responses
   - Use more CPU threads: models benefit from 4-8 threads

6. **GPU acceleration not working**
   - Check if llama.cpp was compiled with CUDA support: `llama-cli --version` should mention CUDA
   - Test GPU directly: `llama-cli -m /path/to/model.gguf -p "test" -n 10 -ngl 35`
   - If GPU out of memory, reduce `-ngl` value (try 20, 15, 10)
   - Ensure NVIDIA drivers are properly installed: `nvidia-smi` should work

7. **Out of memory errors**
   - Reduce `CHUNK_SIZE` in config
   - Reduce `TOP_K_RETRIEVAL` 
   - Use smaller embedding model

### Performance Tips

1. **Faster inference**: Use vLLM or Ollama for better performance
2. **Smaller memory footprint**: Use quantized models (Q4_K_M, Q6_K)
3. **Faster embedding**: Use GPU if available
4. **Efficient storage**: Periodically clean old indices

### Custom Extensions

#### Adding New Retrievers
```python
from src.wikipedia_retriever import WikipediaRetriever

class CustomRetriever(WikipediaRetriever):
    def retrieve_and_chunk(self, query):
        # Your custom retrieval logic
        pass
```

#### Custom Embedding Models
```python
from src.embeddings import EmbeddingModel

class CustomEmbedding(EmbeddingModel):
    def __init__(self, model_name):
        # Your custom embedding model
        pass
```

## Testing

```fish
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=src

# Run specific test
python -m pytest tests/test_rag_system.py::TestRAGSystem::test_init
```

## Development

### Code Structure
```
src/
├── __init__.py           # Package initialization
├── config.py             # Configuration settings
├── embeddings.py         # Text embedding functionality
├── wikipedia_retriever.py # Wikipedia search and chunking
├── vector_store.py       # FAISS vector operations
├── llm_interface.py      # LLM integration
└── rag_system.py         # Main RAG pipeline

tests/                    # Test suite
examples/                 # Usage examples
cli.py                   # Command-line interface
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure code passes `black` formatting
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
