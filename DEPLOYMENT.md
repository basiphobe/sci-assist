# Discord LLM Bot Deployment Guide

## O### 4. Get Discord Bot Token

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Give it a name and create
4. **Optional: Upload bot avatar/logo**
   - In "General Information", upload an App Icon (512x512px recommended)
   - This will be your bot's profile picture
5. Go to "Bot" section
6. Click "Add Bot"
7. Copy the token and add it to your `.env` file as `DISCORD_BOT_TOKEN`
8. Enable these intents:
   - Message Content Intent
   - Server Members Intent
   - Guild Messagess guide will help you deploy your Discord LLM bot that can interact with self-hosted language models.

## Prerequisites

- Python 3.11 or higher
- A Discord application/bot token
- A running LLM API server (Ollama, Oobabooga, LM Studio, etc.)
- Git (for cloning/updating)

## Shell Support

This project includes support for multiple shells:

- **Bash/Zsh**: Standard shell scripts with `.sh` extension
- **Fish Shell**: Dedicated fish scripts with `.fish` extension
- **Windows**: Both CMD and PowerShell activation commands provided

The setup will automatically detect your shell and provide appropriate commands.

## Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/basiphobe/sci-assist.git
cd sci-assist

# Create virtual environment
python -m venv .venv

# Activate virtual environment (choose your shell)
source .venv/bin/activate        # bash/zsh
source .venv/bin/activate.fish   # fish shell  
.venv\Scripts\activate           # Windows CMD
.venv\Scripts\Activate.ps1       # Windows PowerShell

# Install dependencies
pip install -e .
```

### 2. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your values
nano .env  # or use your preferred editor
```

**Fish shell users** can also use:
```fish
# Fish shell commands
cp .env.example .env
nano .env  # or: code .env, vim .env, etc.
```

### 3. Get Discord Bot Token

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Give it a name and create
4. Go to "Bot" section
5. Click "Add Bot"
6. Copy the token and add it to your `.env` file as `DISCORD_BOT_TOKEN`
7. Enable these intents:
   - Message Content Intent
   - Server Members Intent
   - Guild Messages

### 4. Invite Bot to Server

Generate an invite link with these permissions:
- Send Messages
- Read Message History
- Use Slash Commands
- Embed Links

URL format:
```
https://discord.com/api/oauth2/authorize?client_id=YOUR_BOT_CLIENT_ID&permissions=2147551296&scope=bot%20applications.commands
```

### 5. Run the Bot

```bash
# Make sure your LLM server is running first!
# Then start the bot
discord-llm-bot
```

## LLM Server Setup

### Option 1: Ollama (Recommended for beginners)

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# For your specific model (merged science model)
ollama pull merged-sci-model-q6_k.gguf:latest

# Or if you have the model file locally:
ollama create merged-sci-model-q6_k.gguf:latest -f ./Modelfile

# Run with optimized settings for 8GB GPU
OLLAMA_GPU_MEMORY=6GB ollama serve
```

#### Configuring Ollama for LAN Access

By default, Ollama only accepts connections from localhost. To make it accessible from other machines on your LAN:

**Method 1: Environment Variable (Temporary)**
```bash
# Stop Ollama if running
sudo systemctl stop ollama

# Start with LAN access
OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

**Method 2: systemd Service Configuration (Permanent)**
```bash
# Create or edit the systemd override file
sudo systemctl edit ollama

# Add this content to the editor that opens:
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"

# Save and exit, then reload and restart
sudo systemctl daemon-reload
sudo systemctl restart ollama

# Verify it's listening on all interfaces
sudo netstat -tlnp | grep 11434
# Should show: 0.0.0.0:11434 instead of 127.0.0.1:11434
```

**Method 3: Environment File (Alternative)**
```bash
# Create environment file
sudo mkdir -p /etc/ollama
echo 'OLLAMA_HOST=0.0.0.0:11434' | sudo tee /etc/ollama/ollama.env

# Edit the systemd service to use the environment file
sudo systemctl edit ollama

# Add this content:
[Service]
EnvironmentFile=/etc/ollama/ollama.env

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

**Security Considerations for LAN Access:**
- Only enable LAN access on trusted networks
- Consider setting up authentication if available
- Use firewall rules to restrict access if needed:
```bash
# Example: Allow only specific IP range
sudo ufw allow from 192.168.1.0/24 to any port 11434
```

**Testing LAN Access:**
```bash
# From another machine on your LAN, test the connection
curl http://192.168.1.128:11434/api/tags

# Update your bot configuration to use the LAN IP
LLM_API_URL=http://192.168.1.128:11434/v1/chat/completions
```

Configuration in `.env`:
```env
LLM_API_URL=http://localhost:11434/v1/chat/completions
LLM_MODEL_NAME=merged-sci-model-q6_k.gguf:latest
LLM_TIMEOUT=45  # Science models may need more time
```

**Ollama Performance Tips for 8GB GPU:**
- Reserve ~6GB VRAM for model, 2GB for system
- Use `OLLAMA_NUM_PARALLEL=1` for single-threaded inference
- Set `OLLAMA_MAX_LOADED_MODELS=1` to avoid memory fragmentation
- Monitor with `nvidia-smi` during operation

**Optimal Settings for 7.2B ChatML Models:**
```bash
# Environment variables for optimal performance
export OLLAMA_GPU_MEMORY=6GB
export OLLAMA_NUM_PARALLEL=1
export OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_KEEP_ALIVE=5m
```

### Option 2: Oobabooga Text Generation WebUI

```bash
# Clone and setup
git clone https://github.com/oobabooga/text-generation-webui
cd text-generation-webui
./start_linux.sh  # or start_windows.bat

# Start with API enabled
python server.py --api --listen
```

Configuration in `.env`:
```env
LLM_API_URL=http://localhost:5000/v1/chat/completions
LLM_MODEL_NAME=your-loaded-model
```

### Option 3: LM Studio

1. Download and install [LM Studio](https://lmstudio.ai/)
2. Download a model
3. Start the local server
4. Use the provided endpoint

Configuration in `.env`:
```env
LLM_API_URL=http://localhost:1234/v1/chat/completions
LLM_MODEL_NAME=local-model
```

## Database Setup

The bot uses SQLite by default, but you can use PostgreSQL for production:

### SQLite (Default)
```env
DATABASE_URL=sqlite:///./conversations.db
```

### PostgreSQL (Production)
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost/botdb
```

### Initialize Database

```bash
# Run database migrations
discord-llm-bot migrate

# Or let the bot auto-create tables on first run
```

## Configuration Options

### Memory Management
```env
MEMORY_CONTEXT_WINDOW_TOKENS=4096  # Adjust based on your model
MEMORY_MAX_HISTORY_MESSAGES=50     # How many messages to keep
```

### Rate Limiting
```env
RATE_LIMIT_PER_USER=20      # Messages per minute per user
RATE_LIMIT_PER_CHANNEL=100  # Messages per minute per channel
```

### Logging
```env
LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT=json             # json or text
```

## Bot Customization

### Avatar/Logo Setup

**Method 1: Discord Developer Portal (Recommended)**
1. Go to your app in [Discord Developer Portal](https://discord.com/developers/applications)
2. Under "General Information", upload an App Icon
3. Requirements: 512x512px minimum, PNG/JPG/GIF, max 10MB

**Method 2: Programmatic (Advanced)**
```env
# Add to your .env file
DISCORD_AVATAR_PATH=assets/bot_avatar_no_text.png
```

The bot will automatically update its avatar on startup if the file exists.

**Science Bot Logo Ideas:**
- 🧬 DNA helix design
- ⚛️ Atom with orbiting electrons
- 🔬 Modern microscope icon
- 📊 Scientific data visualization
- 🌌 Space/cosmos theme

See `assets/README.md` for detailed design guidelines.

### Bot Presence

The bot automatically sets its status to "Listening to your questions | /help". You can customize this in the bot client code.

## Production Deployment

### Using Docker

Create a `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install -e .

CMD ["discord-llm-bot"]
```

Build and run:
```bash
docker build -t discord-llm-bot .
docker run -d --env-file .env discord-llm-bot
```

### Using systemd (Recommended)

**Automated Setup:**
The project includes scripts to automatically set up the bot as a system service:

```bash
# Choose your shell
./setup_service.sh      # Bash/Zsh users
./setup_service.fish    # Fish shell users
```

This will:
- Install the bot package
- Create and install the systemd service
- Enable auto-start on boot
- Optionally start the service immediately

**Manual Service Management:**
```bash
# Easy management with included scripts (choose your shell)
./bot_control.sh start      # Bash/Zsh users
./bot_control.fish start    # Fish shell users

# Available commands for both scripts:
# start, stop, restart, status, logs, enable, disable
```

**Examples:**
```bash
# Bash/Zsh
./bot_control.sh start    # Start the bot
./bot_control.sh stop     # Stop the bot
./bot_control.sh logs     # View live logs
```

```fish
# Fish shell
./bot_control.fish start    # Start the bot
./bot_control.fish stop     # Stop the bot
./bot_control.fish logs     # View live logs
```

**Manual systemd commands:**
```bash
sudo systemctl start sci-assist-bot     # Start now
sudo systemctl stop sci-assist-bot      # Stop
sudo systemctl restart sci-assist-bot   # Restart
sudo systemctl status sci-assist-bot    # Check status
sudo systemctl enable sci-assist-bot    # Enable auto-start
sudo systemctl disable sci-assist-bot   # Disable auto-start
sudo journalctl -u sci-assist-bot -f    # View logs
```

### Using PM2

```bash
npm install -g pm2

# Create ecosystem file
cat > ecosystem.config.js << 'EOF'
module.exports = {
  apps: [{
    name: 'discord-llm-bot',
    cmd: 'discord-llm-bot',
    cwd: '/path/to/sci-assist-bot',
    interpreter: '/path/to/sci-assist-bot/.venv/bin/python',
    env: {
      NODE_ENV: 'production'
    }
  }]
}
EOF

pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

## Monitoring and Maintenance

### Logs

```bash
# View logs
tail -f logs/bot.log

# Or if using systemd
journalctl -u discord-bot -f
```

### Database Maintenance

```bash
# Backup database
cp conversations.db conversations.db.backup

# Clean old conversations (if implemented)
discord-llm-bot cleanup --days 30
```

### Health Checks

The bot includes health check endpoints:
- Database connectivity
- LLM API availability
- Memory usage

```bash
# Check bot status
discord-llm-bot status
```

## Troubleshooting

### Common Issues

1. **Bot not responding**
   - Check if the bot is online in Discord
   - Verify token is correct
   - Check bot permissions

2. **LLM not working**
   - Verify LLM server is running
   - Check API URL and model name
   - Test endpoint manually: `curl -X POST your-llm-url`

3. **Database errors**
   - Check file permissions for SQLite
   - Verify connection string for PostgreSQL
   - Run migrations

4. **Memory issues**
   - Reduce `MEMORY_CONTEXT_WINDOW_TOKENS`
   - Lower `MEMORY_MAX_HISTORY_MESSAGES`
   - Clean up old conversations

### Debug Mode

Enable debug logging:
```env
LOG_LEVEL=DEBUG
```

### Test Installation

```bash
# Run the test suite
python test_setup.py

# Test specific components
pytest tests/
```

## Security Considerations

1. **Never commit `.env` files**
2. **Use environment variables in production**
3. **Restrict bot permissions to minimum required**
4. **Keep dependencies updated**
5. **Monitor logs for suspicious activity**
6. **Use rate limiting**

## Performance Tips

1. **Use PostgreSQL for high-traffic bots**
2. **Enable database connection pooling**
3. **Monitor memory usage**
4. **Use efficient models for your hardware**
5. **Implement message queuing for heavy loads**

## Updates

```bash
# Update the bot
git pull origin main
pip install -e . --upgrade

# Run any new migrations
discord-llm-bot migrate

# Restart the service
sudo systemctl restart discord-bot
```

## Support

- Check the logs first
- Review configuration
- Test individual components
- Open an issue with reproduction steps

## Science Model Optimization

### For Merged Science Models (7.2B Parameters, 32K Context)

Your model has excellent capabilities - here's the optimal configuration:

```env
# Optimized settings for 7.2B science model with 32K context
LLM_MODEL_NAME=merged-sci-model-q6_k.gguf:latest
LLM_MAX_TOKENS=1024           # Balanced response length
LLM_TEMPERATURE=0.3           # Lower for scientific accuracy
LLM_TIMEOUT=60                # More time for complex reasoning
LLM_SYSTEM_PROMPT_FILE=system_prompt.txt  # Load from file for easy editing
MEMORY_CONTEXT_WINDOW_TOKENS=8192  # Use the large context efficiently
MEMORY_MAX_HISTORY_MESSAGES=25     # Longer scientific discussions
```

### System Prompt Management

The bot uses a file-based system prompt for easy customization:

```bash
# Copy the example system prompt
cp system_prompt.example.txt system_prompt.txt

# Edit your custom prompt
nano system_prompt.txt

# The bot will automatically load this file on startup
```

**Benefits of file-based prompts:**
- ✅ Multi-line prompts with proper formatting
- ✅ Easy editing without environment variable hassles  
- ✅ Version control friendly
- ✅ Can be hot-reloaded (future feature)
- ✅ Shareable between deployments

**Example customizations:**
```bash
# Create domain-specific variants
cp system_prompt.example.txt system_prompt_physics.txt
cp system_prompt.example.txt system_prompt_biology.txt

# Switch prompts by changing the env var
LLM_SYSTEM_PROMPT_FILE=system_prompt_physics.txt
```

### ChatML Template Configuration

Since your model uses ChatML format, it will automatically handle the proper message formatting with `<|im_start|>` and `<|im_end|>` tokens.

### Model-Specific Ollama Settings

For your specific merged science model, create an optimized Modelfile:

```dockerfile
# Modelfile for merged-sci-model-q6_k.gguf
FROM merged-sci-model-q6_k.gguf

# Optimized parameters for 7.2B science model
PARAMETER temperature 0.3
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.1
PARAMETER num_ctx 8192        # Use 8K context for efficiency
PARAMETER stop "<|im_start|>"
PARAMETER stop "<|im_end|>"

# Science-focused system prompt (will be overridden by bot config)
SYSTEM """You are a knowledgeable scientific assistant with expertise across multiple scientific disciplines. Provide accurate, well-reasoned responses based on established scientific principles."""
```

Create and test the optimized model:
```bash
# Create the optimized model
ollama create sci-assistant -f ./Modelfile

# Test it
ollama run sci-assistant "Explain the difference between DNA and RNA"

# Use in your bot
LLM_MODEL_NAME=sci-assistant
```

### Performance Monitoring

Monitor your setup with:
```bash
# Check GPU usage
nvidia-smi -l 1

# Monitor Ollama logs
journalctl -u ollama -f

# Check model memory usage
ollama ps
```

## NVIDIA GPU Setup

Here are 8GB GPU-specific tips:

### CUDA Setup
```bash
# Install CUDA toolkit (adjust version as needed)
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/cuda-ubuntu2004.pin
sudo mv cuda-ubuntu2004.pin /etc/apt/preferences.d/cuda-repository-pin-600
wget https://developer.download.nvidia.com/compute/cuda/12.0.0/local_installers/cuda-repo-ubuntu2004-12-0-local_12.0.0-525.60.13-1_amd64.deb
sudo dpkg -i cuda-repo-ubuntu2004-12-0-local_12.0.0-525.60.13-1_amd64.deb
sudo cp /var/cuda-repo-ubuntu2004-12-0-local/cuda-*-keyring.gpg /usr/share/keyrings/
sudo apt-get update
sudo apt-get -y install cuda
```

### GPU Memory Management
For 8GB, consider these model sizes:
- 7B models: Should run comfortably
- 13B models: May need quantization (4-bit)
- Larger models: Use CPU offloading

### Recommended Settings
```env
# Adjust based on available VRAM
LLM_MAX_TOKENS=1024  # Reduce if getting OOM errors
MEMORY_CONTEXT_WINDOW_TOKENS=2048
```
