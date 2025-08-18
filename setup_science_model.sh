#!/bin/bash
# Quick setup script for merged-sci-model deployment

set -e

echo "🔬 Discord Science Bot Setup"
echo "=============================="

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

# Check if Ollama is running
echo "🔍 Checking Ollama status..."
if ! curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "❌ Ollama is not running. Please start it first:"
    echo "   ollama serve"
    exit 1
fi

# Check if the model is available
echo "🔍 Checking for merged-sci-model..."
if ! ollama list | grep -q "merged-sci-model-q6_k.gguf"; then
    echo "⚠️  Model not found. Please ensure your model is available in Ollama:"
    echo "   ollama pull merged-sci-model-q6_k.gguf:latest"
    echo "   or if you have the model file locally:"
    echo "   ollama create merged-sci-model-q6_k.gguf:latest -f ./Modelfile"
    exit 1
fi

# Create optimized Modelfile if it doesn't exist
if [ ! -f "Modelfile" ]; then
    echo "📝 Creating optimized Modelfile..."
    cat > Modelfile << 'EOF'
FROM merged-sci-model-q6_k.gguf

# Optimized parameters for 7.2B science model
PARAMETER temperature 0.3
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.1
PARAMETER num_ctx 8192
PARAMETER stop "<|im_start|>"
PARAMETER stop "<|im_end|>"

# Basic system prompt (will be overridden by bot's system_prompt.txt)
SYSTEM """You are a knowledgeable scientific assistant."""
EOF
fi

# Create optimized model
echo "🛠️  Creating optimized sci-assistant model..."
ollama create sci-assistant -f ./Modelfile

# Set up environment variables for optimal performance
echo "⚙️  Setting up environment variables..."
export OLLAMA_GPU_MEMORY=6GB
export OLLAMA_NUM_PARALLEL=1
export OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_KEEP_ALIVE=5m

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📄 Creating .env file..."
    cp .env.example .env
    
    # Update with optimal settings
    sed -i 's|LLM_MODEL_NAME=.*|LLM_MODEL_NAME=sci-assistant|' .env
    sed -i 's|MEMORY_CONTEXT_WINDOW_TOKENS=.*|MEMORY_CONTEXT_WINDOW_TOKENS=8192|' .env
    sed -i 's|MEMORY_MAX_HISTORY_MESSAGES=.*|MEMORY_MAX_HISTORY_MESSAGES=25|' .env
    
    echo ""
    echo "🔑 Please edit .env and add your Discord bot token:"
    echo "   DISCORD_BOT_TOKEN=your_token_here"
    echo ""
else
    echo "✅ .env file already exists"
fi

# Create system prompt file if it doesn't exist
if [ ! -f "system_prompt.txt" ]; then
    echo "📝 Creating system_prompt.txt..."
    cp system_prompt.example.txt system_prompt.txt
    echo "💡 You can customize system_prompt.txt to change the bot's personality"
else
    echo "✅ system_prompt.txt already exists"
fi

# Test the setup
echo "🧪 Testing the configuration..."
if python -c "
import asyncio
from src.discord_llm_bot.config import load_config
try:
    config = load_config()
    print('✅ Configuration loaded successfully')
    print(f'   Model: {config.llm.model_name}')
    print(f'   Context window: {config.memory.context_window_tokens}')
    print(f'   Temperature: {config.llm.temperature}')
except Exception as e:
    print(f'❌ Configuration error: {e}')
    exit(1)
"; then
    echo ""
    echo "🎉 Setup complete!"
    echo ""
    echo "Next steps:"
    echo "1. Add your Discord bot token to .env"
    echo "2. Optional: Add a bot avatar to assets/bot_avatar_no_text.png"
    echo "3. Start the bot: discord-llm-bot"
    echo "4. Invite the bot to your Discord server"
    echo ""
    echo "For monitoring:"
    echo "- GPU usage: nvidia-smi -l 1"
    echo "- Ollama logs: journalctl -u ollama -f"
    echo "- Model status: ollama ps"
else
    echo "❌ Configuration test failed"
    exit 1
fi
