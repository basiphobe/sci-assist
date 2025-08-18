#!/bin/bash

# Wikipedia RAG System Setup Script
# This script helps set up the Wikipedia RAG system

set -e  # Exit on any error

echo "🚀 Setting up Wikipedia RAG System..."
echo "======================================"

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    echo "✅ Python $python_version is compatible (>= $required_version)"
else
    echo "❌ Python $python_version is not compatible. Please install Python >= $required_version"
    exit 1
fi

# Create virtual environment
echo "🐍 Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

echo "✅ Dependencies installed successfully!"

# Create data directories
echo "📁 Creating data directories..."
mkdir -p data models .cache
echo "✅ Directories created"

# Download embedding model (optional)
echo "🤖 Pre-downloading embedding model (optional)..."
python3 -c "
try:
    from sentence_transformers import SentenceTransformer
    print('Downloading intfloat/e5-base-v2...')
    model = SentenceTransformer('intfloat/e5-base-v2')
    print('✅ Embedding model downloaded successfully!')
except Exception as e:
    print(f'⚠️  Could not download embedding model: {e}')
    print('   Model will be downloaded automatically on first use.')
"

# Check if tests pass
echo "🧪 Running tests..."
python3 -m pytest tests/ -v --tb=short || echo "⚠️  Some tests failed, but installation continues..."

echo ""
echo "🎉 Setup completed!"
echo "==================="
echo ""
echo "Next steps:"
echo "1. Configure your LLM in src/llm_interface.py (see llm_config_examples.py)"
echo "2. Set LLM_MODEL_PATH environment variable:"
echo "   export LLM_MODEL_PATH='/path/to/your/Mistral-7B-Instruct-v0.3-Q6_K.gguf'"
echo ""
echo "Quick start:"
echo "  python3 cli.py                    # Interactive mode"
echo "  python3 cli.py -q 'What is AI?'   # Single query"
echo "  python3 examples/demo.py          # Run demo"
echo ""
echo "Documentation:"
echo "  README.md                         # Full documentation"
echo "  llm_config_examples.py           # LLM configuration examples"
echo ""
echo "Happy querying! 🚀"
