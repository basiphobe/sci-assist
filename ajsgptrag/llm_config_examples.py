"""
LLM Configuration Guide

This file contains examples for configuring different local LLM backends.
Copy the relevant section to src/llm_interface.py based on your setup.
"""

# =============================================================================
# LLAMA.CPP CONFIGURATION
# =============================================================================
"""
For llama.cpp (recommended), replace the _call_llm method in src/llm_interface.py:

def _call_llm(self, prompt: str) -> str:
    try:
        cmd = [
            "llama-cli",  # or "llama-cpp-python" if using Python bindings
            "-m", self.model_path,
            "-p", prompt,
            "-n", str(self.config["max_new_tokens"]),
            "--temp", str(self.config["temperature"]),
            "--top-p", str(self.config["top_p"]),
            "--top-k", str(self.config["top_k"]),
            "--no-display-prompt",
            "--silent"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"LLM error: {result.stderr}")
            return "I apologize, but I couldn't generate a response."
            
    except subprocess.TimeoutExpired:
        return "I apologize, but the response generation timed out."
    except FileNotFoundError:
        return "LLM executable not found. Please ensure llama-cli is installed and in PATH."
"""

# =============================================================================
# OLLAMA CONFIGURATION  
# =============================================================================
"""
For Ollama, replace the _call_llm method in src/llm_interface.py:

def _call_llm(self, prompt: str) -> str:
    try:
        # Extract model name from path (e.g., "mistral:7b-instruct")
        model_name = "mistral:7b-instruct"  # Adjust based on your Ollama model name
        
        cmd = ["ollama", "run", model_name, prompt]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"Ollama error: {result.stderr}")
            return "I apologize, but I couldn't generate a response."
            
    except subprocess.TimeoutExpired:
        return "I apologize, but the response generation timed out."
    except FileNotFoundError:
        return "Ollama not found. Please ensure Ollama is installed and in PATH."
"""

# =============================================================================
# TRANSFORMERS (HUGGING FACE) CONFIGURATION
# =============================================================================
"""
For direct Transformers library usage, replace the _call_llm method:

def _call_llm(self, prompt: str) -> str:
    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM
        import torch
        
        # Load model and tokenizer (do this in __init__ for better performance)
        if not hasattr(self, 'tokenizer'):
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                torch_dtype=torch.float16,
                device_map="auto"
            )
        
        # Tokenize input
        inputs = self.tokenizer.encode(prompt, return_tensors="pt")
        
        # Generate response
        with torch.no_grad():
            outputs = self.model.generate(
                inputs,
                max_new_tokens=self.config["max_new_tokens"],
                temperature=self.config["temperature"],
                top_p=self.config["top_p"],
                top_k=self.config["top_k"],
                do_sample=self.config["do_sample"],
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        # Decode response
        response = self.tokenizer.decode(outputs[0][inputs.shape[1]:], skip_special_tokens=True)
        return response.strip()
        
    except Exception as e:
        print(f"Transformers error: {e}")
        return f"I apologize, but I encountered an error: {e}"
"""

# =============================================================================
# VLLM CONFIGURATION
# =============================================================================
"""
For vLLM (high performance inference), replace the _call_llm method:

def _call_llm(self, prompt: str) -> str:
    try:
        from vllm import LLM, SamplingParams
        
        # Initialize vLLM (do this in __init__ for better performance)
        if not hasattr(self, 'vllm_model'):
            self.vllm_model = LLM(model=self.model_path)
        
        # Set sampling parameters
        sampling_params = SamplingParams(
            temperature=self.config["temperature"],
            top_p=self.config["top_p"],
            top_k=self.config["top_k"],
            max_tokens=self.config["max_new_tokens"]
        )
        
        # Generate response
        outputs = self.vllm_model.generate([prompt], sampling_params)
        response = outputs[0].outputs[0].text
        
        return response.strip()
        
    except Exception as e:
        print(f"vLLM error: {e}")
        return f"I apologize, but I encountered an error: {e}"
"""

# =============================================================================
# OPENAI API CONFIGURATION (for comparison/testing)
# =============================================================================
"""
For OpenAI API (or compatible APIs like LocalAI), replace the _call_llm method:

def _call_llm(self, prompt: str) -> str:
    try:
        import openai
        
        # Configure client (do this in __init__)
        if not hasattr(self, 'openai_client'):
            self.openai_client = openai.OpenAI(
                base_url="http://localhost:8080/v1",  # LocalAI or other compatible endpoint
                api_key="sk-dummy"  # Dummy key for local APIs
            )
        
        response = self.openai_client.chat.completions.create(
            model="mistral-7b-instruct",  # Model name on your local API
            messages=[{"role": "user", "content": prompt}],
            temperature=self.config["temperature"],
            max_tokens=self.config["max_new_tokens"],
            top_p=self.config["top_p"]
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return f"I apologize, but I encountered an error: {e}"
"""

# =============================================================================
# ENVIRONMENT VARIABLES
# =============================================================================
"""
Set these environment variables for your specific setup:

Fish shell:
# For local model files
set -x LLM_MODEL_PATH "/path/to/your/Mistral-7B-Instruct-v0.3-Q6_K.gguf"

# For Ollama
set -x LLM_MODEL_PATH "mistral:7b-instruct"

# For Hugging Face models
set -x LLM_MODEL_PATH "mistralai/Mistral-7B-Instruct-v0.3"

# For API endpoints
set -x LLM_MODEL_PATH "http://localhost:8080/v1"
set -x OPENAI_API_KEY "your-api-key"

Bash/Zsh:
# For local model files
export LLM_MODEL_PATH="/path/to/your/Mistral-7B-Instruct-v0.3-Q6_K.gguf"

# For Ollama
export LLM_MODEL_PATH="mistral:7b-instruct"

# For Hugging Face models
export LLM_MODEL_PATH="mistralai/Mistral-7B-Instruct-v0.3" 

# For API endpoints
export LLM_MODEL_PATH="http://localhost:8080/v1"
export OPENAI_API_KEY="your-api-key"
"""
