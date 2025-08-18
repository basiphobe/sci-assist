#!/usr/bin/env fish

# Alternative: Set up Ollama for easier LLM management

echo "🦙 Setting up Ollama as an alternative to llama.cpp..."
echo "====================================================="

# Check if Ollama is already installed
if command -v ollama >/dev/null
    echo "✅ Ollama is already installed"
    ollama --version
else
    echo "📥 Installing Ollama..."
    curl -fsSL https://ollama.ai/install.sh | sh
end

echo ""
echo "🤖 Pulling Mistral 7B model for Ollama..."
echo "   This will download about 4GB of data..."

# Pull the Mistral model
ollama pull mistral:7b-instruct

echo ""
echo "🧪 Testing Ollama with a quick prompt..."
echo "Question: What is 2+2?"
ollama run mistral:7b-instruct "What is 2+2? Answer briefly."

echo ""
echo "✅ Ollama setup completed!"
echo ""
echo "📋 To use Ollama with the RAG system:"
echo "1. Set environment variable:"
echo "   set -x LLM_MODEL_PATH 'mistral:7b-instruct'"
echo ""
echo "2. Update src/llm_interface.py to use Ollama instead of llama-cli"
echo "   (uncomment the Ollama section and comment out llama-cli section)"
echo ""
echo "3. Test the RAG system:"
echo "   python cli.py -q 'What is quantum computing?'"
