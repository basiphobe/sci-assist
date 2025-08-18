#!/usr/bin/env fish

# Test both Ollama and llama-cli setups

echo "🧪 Testing LLM backends..."
echo "=========================="

# Test Ollama
echo "1. Testing Ollama..."
if command -v ollama >/dev/null
    echo "✅ Ollama is installed"
    
    # Check if mistral model is available
    if ollama list | grep -q mistral
        echo "✅ Mistral model is available"
        echo "🧪 Testing Ollama with quick prompt..."
        ollama run mistral:7b-instruct "What is 2+2? Answer with just the number."
    else
        echo "📥 Mistral model not found, pulling it..."
        ollama pull mistral:7b-instruct
    end
else
    echo "❌ Ollama not installed"
end

echo ""
echo "2. Testing llama-cli..."
if command -v llama-cli >/dev/null
    echo "✅ llama-cli is installed"
    llama-cli --version
    
    if set -q LLM_MODEL_PATH; and test -f $LLM_MODEL_PATH
        echo "✅ Model file exists: $LLM_MODEL_PATH"
        echo "🧪 Testing llama-cli with quick prompt..."
        llama-cli -m $LLM_MODEL_PATH -p "What is 2+2? Answer with just the number." -n 5 --log-disable --no-display-prompt
    else
        echo "❌ LLM_MODEL_PATH not set or model file not found"
    end
else
    echo "❌ llama-cli not found"
end

echo ""
echo "📋 Recommendations:"
if command -v ollama >/dev/null; and ollama list | grep -q mistral
    echo "✅ Use Ollama: set -x LLM_MODEL_PATH 'mistral:7b-instruct'"
else if command -v llama-cli >/dev/null; and set -q LLM_MODEL_PATH; and test -f $LLM_MODEL_PATH
    echo "✅ Use llama-cli: Current setup should work"
else
    echo "🔧 Install Ollama for easiest setup: fish setup_ollama.fish"
end
