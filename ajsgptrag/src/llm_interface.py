"""
Local LLM interface for answer generation.

This module provides a unified interface for interacting with local language models,
supporting both llama-cli (from llama.cpp) and Ollama backends. It handles model
loading, prompt formatting, and response generation with robust error handling
and timeout management.

The interface automatically detects the backend based on the model path format:
- File paths (containing '/') are treated as llama-cli models
- Model names (containing ':') are treated as Ollama models

Key Features:
- Dual backend support (llama-cli and Ollama)
- Automatic GPU acceleration when available
- Robust error handling and timeout management
- Response filtering and cleaning
- Configurable generation parameters

Supported Backends:
1. llama-cli: For local GGUF model files
   - Requires llama-cli executable in PATH
   - Supports GPU acceleration with CUDA
   - Example model path: "/path/to/model.gguf"

2. Ollama: For managed model instances
   - Requires Ollama service running
   - Automatic model management
   - Example model path: "mistral:7b-instruct"

Environment Setup:
- For llama-cli: Ensure llama-cli is compiled with CUDA support and in PATH
- For Ollama: Install and start Ollama service, pull required models
- Set LLM_MODEL_PATH environment variable to your preferred model

Example:
    >>> from src.llm_interface import LLMInterface
    >>> llm = LLMInterface()
    >>> context = "Python is a programming language..."
    >>> question = "What is Python?"
    >>> answer = llm.generate_answer(context, question)
    >>> print(answer)

Dependencies:
    - subprocess: For executing external commands
    - json: For configuration handling
"""

import subprocess
import os
from typing import Dict, Any, Optional
from src.config import LLM_MODEL_PATH, LLM_CONFIG, SYSTEM_PROMPT


class LLMInterface:
    """
    Interface for local LLM interaction supporting multiple backends.
    
    This class provides a unified interface for interacting with local language models
    through different backends. It automatically detects the appropriate backend based
    on the model path format and handles all the complexity of model execution,
    response parsing, and error handling.
    
    Backend Detection:
    - Paths containing '/' are treated as llama-cli model files
    - Names containing ':' without '/' are treated as Ollama models
    
    Attributes:
        model_path (str): Path to model file or Ollama model name
        config (Dict[str, Any]): LLM generation configuration parameters
        
    Example:
        >>> # Using llama-cli with local model file
        >>> llm = LLMInterface("/path/to/model.gguf")
        >>> 
        >>> # Using Ollama with managed model
        >>> llm = LLMInterface("mistral:7b-instruct")
        >>> 
        >>> # Generate answer with context
        >>> context = "Python was created by Guido van Rossum..."
        >>> question = "Who created Python?"
        >>> answer = llm.generate_answer(context, question)
    """
    
    def __init__(self, model_path: str = LLM_MODEL_PATH):
        """
        Initialize the LLM interface.
        
        Sets up the interface with the specified model and configuration.
        The backend (llama-cli or Ollama) is automatically detected based
        on the model path format.
        
        Args:
            model_path (str): Path to the local LLM model file or Ollama model name.
                            Examples:
                            - "/path/to/model.gguf" (llama-cli)
                            - "mistral:7b-instruct" (Ollama)
                            - "llama2:13b" (Ollama)
                            
        Note:
            The configuration is copied from the global LLM_CONFIG to allow
            per-instance modifications without affecting the global settings.
        """
        self.model_path = model_path
        self.config = LLM_CONFIG.copy()
        print(f"Initialized LLM interface with model: {model_path}")
    
    def generate_answer(self, context: str, question: str) -> str:
        """
        Generate an answer using the LLM with provided context.
        
        This method formats the context and question into a prompt using the
        system prompt template, then calls the appropriate LLM backend to
        generate a response. It includes comprehensive error handling for
        common failure modes.
        
        Args:
            context (str): Retrieved context from Wikipedia chunks.
                          Should contain relevant information to answer the question.
                          Example: "Python is a high-level programming language..."
            question (str): User's question that needs to be answered.
                           Example: "What is Python?"
                           
        Returns:
            str: Generated answer from the LLM. In case of errors, returns
                 a user-friendly error message explaining what went wrong.
                 
        Example:
            >>> llm = LLMInterface()
            >>> context = "Python was created by Guido van Rossum in 1991."
            >>> question = "Who created Python?"
            >>> answer = llm.generate_answer(context, question)
            >>> print(answer)  # "Python was created by Guido van Rossum."
            
        Raises:
            No exceptions are raised; all errors are caught and returned
            as user-friendly error messages in the response string.
        """
        # Format the prompt with context and question
        prompt = SYSTEM_PROMPT.format(context=context, question=question)
        
        try:
            answer = self._call_llm(prompt)
            return answer
        except Exception as e:
            print(f"Error generating answer: {e}")
            return f"I apologize, but I encountered an error while generating an answer: {e}"
    
    def _call_llm(self, prompt: str) -> str:
        """
        Call the local LLM with the given prompt.
        
        This method automatically detects the appropriate backend based on the
        model path format and routes the call accordingly. It serves as a
        dispatcher between the two supported backends.
        
        Backend Detection Logic:
        - If model_path contains ':' but no '/', it's treated as an Ollama model
        - Otherwise, it's treated as a llama-cli model file path
        
        Args:
            prompt (str): The formatted prompt containing system instructions,
                         context, and the user's question.
                         
        Returns:
            str: Generated response from the LLM backend.
            
        Raises:
            Exception: Re-raises any exceptions from the backend methods
                      to be handled by the calling method.
                      
        Example:
            >>> llm = LLMInterface("mistral:7b-instruct")  # Will use Ollama
            >>> response = llm._call_llm("What is AI?")
            >>> 
            >>> llm = LLMInterface("/path/to/model.gguf")  # Will use llama-cli
            >>> response = llm._call_llm("What is AI?")
        """
        # Check if model path looks like an Ollama model
        if ":" in self.model_path and not "/" in self.model_path:
            return self._call_ollama(prompt)
        else:
            return self._call_llama_cli(prompt)
    
    def _call_ollama(self, prompt: str) -> str:
        """
        Call Ollama with the given prompt.
        
        This method handles communication with the Ollama service, which manages
        model loading, GPU acceleration, and inference automatically. Ollama
        provides a simple API for running various language models.
        
        Args:
            prompt (str): The complete formatted prompt to send to Ollama.
            
        Returns:
            str: Generated response from the Ollama model.
            
        Raises:
            subprocess.TimeoutExpired: If the generation takes longer than 2 minutes
            FileNotFoundError: If Ollama is not installed or not in PATH
            Exception: For other subprocess-related errors
            
        Note:
            - Ollama handles GPU acceleration automatically
            - The timeout is set to 2 minutes to prevent hanging
            - The model is automatically pulled if not available locally
            
        Example:
            >>> llm = LLMInterface("mistral:7b-instruct")
            >>> response = llm._call_ollama("What is Python?")
        """
        try:
            cmd = [
                "ollama", "run", self.model_path, prompt
            ]
            
            print(f"Calling Ollama with model: {self.model_path}")
            print("Using Ollama with automatic GPU acceleration...")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 minutes should be enough
            )
            
            if result.returncode == 0:
                response = result.stdout.strip()
                if response:
                    return response
                else:
                    return "The model generated an empty response."
            else:
                print(f"Ollama command failed with return code: {result.returncode}")
                print(f"Ollama stderr: {result.stderr}")
                return f"Ollama error (code {result.returncode}): {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return "I apologize, but the response generation timed out after 2 minutes."
        except FileNotFoundError:
            return "Ollama not found. Please install Ollama first: curl -fsSL https://ollama.ai/install.sh | sh"

    def _call_llama_cli(self, prompt: str) -> str:
        """
        Call llama-cli with the given prompt.
        
        This method handles communication with llama-cli (from llama.cpp), which
        provides direct access to GGUF model files with fine-grained control over
        GPU acceleration and generation parameters. It's optimized for single-GPU
        setups and includes sophisticated response filtering.
        
        Args:
            prompt (str): The complete formatted prompt to send to llama-cli.
            
        Returns:
            str: Cleaned and filtered response from the llama-cli model.
                 Technical output and metadata are automatically removed.
            
        Raises:
            subprocess.TimeoutExpired: If generation takes longer than 3 minutes
            FileNotFoundError: If llama-cli is not installed or not in PATH
            Exception: For other subprocess-related errors
            
        Configuration:
            - Uses GPU 0 only (optimized for GTX 1070)
            - Sets CUDA_VISIBLE_DEVICES=0 for memory efficiency
            - Uses 35 GPU layers for optimal performance
            - 3-minute timeout for loading + generation
            
        Note:
            The method includes sophisticated filtering to extract only the
            actual generated answer from llama-cli's verbose output, which
            includes technical metadata, loading information, and performance stats.
            
        Example:
            >>> llm = LLMInterface("/path/to/model.gguf")
            >>> response = llm._call_llama_cli("What is Python?")
        """
        # Check if model file exists first
        import os
        if not os.path.exists(self.model_path):
            return f"Model file not found: {self.model_path}. Please set LLM_MODEL_PATH environment variable to your model file path."
        
        try:
            cmd = [
                "llama-cli",
                "-m", self.model_path,
                "-p", prompt,
                "-n", "100",      # Fixed number of tokens
                "-ngl", "35",     # GPU layers only
                "--split-mode", "none",  # Don't split across GPUs
                "--main-gpu", "0"        # Use only GPU 0 (GTX 1070)
            ]
            
            # Set CUDA_VISIBLE_DEVICES to only use GPU 0
            env = os.environ.copy()
            env["CUDA_VISIBLE_DEVICES"] = "0"
            
            print(f"Calling llama-cli with GPU acceleration (GTX 1070 only)")
            print(f"Model: {self.model_path}")
            print("Loading model on GPU 0 only... this should be much faster!")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                input="",  # Provide empty input to prevent hanging
                timeout=180,  # 3 minutes should be enough for GPU loading + generation
                env=env      # Use modified environment
            )
            
            if result.returncode == 0:
                # Combine all output
                full_output = result.stdout + "\n" + result.stderr
                
                # Split into lines and filter aggressively
                lines = full_output.split('\n')
                
                # Find the actual generated answer
                answer_lines = []
                found_answer_start = False
                collecting_answer = False
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Skip all technical metadata and loading messages
                    if any(pattern in line for pattern in [
                        'ggml_', 'llama_', 'build:', 'main:', 'load_', 'print_info',
                        'Device', 'CUDA', 'VMM:', 'special_eos_id', 'token to piece',
                        'common_init_from_params', 'system_info:', 'sampler',
                        'mirostat', 'generate:', 'repeat_last_n', 'dry_multiplier',
                        'top_k', 'top_p', 'temp =', 'n_threads', 'ARCHS =',
                        'SSE3', 'AVX', 'FMA', 'BMI2', 'LLAMAFILE', 'OPENMP',
                        'load:', 'cache_', 'special_', 'llama_perf', '...'
                    ]):
                        continue
                    
                    # Skip the system prompt echoing and metadata
                    if (any(skip_phrase in line for skip_phrase in [
                        'You are a helpful assistant', 'Instructions:', 'Use ONLY the information',
                        'Context:', 'Question:', '===', '[Source', 'Provide a comprehensive answer',
                        'If the question is general', 'If the question is specific', 'Organize your answer',
                        'If the context doesn', 'acknowledge what you can', 'Source 1 (from', 'Source 2 (from',
                        'Source 3 (from', 'Source 4 (from', 'Source 5 (from', 'Source 6 (from',
                        'Source 7 (from', 'Source 8 (from'
                    ]) or 
                        ('Answer:' in line and len(line) < 30)):
                        if 'Answer:' in line and len(line) < 30:
                            collecting_answer = True
                        continue
                    
                    # Start collecting after we see a substantive line that looks like an answer
                    if not found_answer_start and not collecting_answer:
                        # Look for lines that look like the start of an actual answer
                        if (len(line) > 30 and 
                            not line.startswith('Answer') and
                            not line.startswith('Source') and
                            not line.startswith('Context') and
                            not any(skip_word in line.lower() for skip_word in [
                                'context:', 'question:', 'instruction', 'provide a comprehensive',
                                'if the question', 'organize your answer', 'acknowledge what'
                            ])):
                            found_answer_start = True
                            answer_lines.append(line)
                        continue
                    elif collecting_answer or found_answer_start:
                        # We're collecting the answer, keep adding until we hit garbage or source citations
                        if (len(line) > 10 and 
                            not any(bad in line for bad in ['llama_perf', 'encode:', 'Source ', '(from ']) and
                            not line.startswith('Source')):
                            answer_lines.append(line)
                        else:
                            # Hit garbage or source citation, stop collecting  
                            break
                
                if answer_lines:
                    # Join and clean up the answer
                    response = ' '.join(answer_lines)
                    
                    # Remove common prefixes and suffixes
                    response = response.replace('Answer:', '').strip()
                    response = response.replace('[end of text]', '').strip()
                    response = response.replace('</s>', '').strip()
                    
                    # Remove any remaining system prompt fragments and repetitive content
                    if 'Answer based only on the context above:' in response:
                        parts = response.split('Answer based only on the context above:')
                        if len(parts) > 1 and parts[1].strip():
                            response = parts[1].strip()
                        else:
                            response = parts[0].strip()
                    
                    # Clean up any remaining fragments from the prompt
                    response = response.replace('You are a helpful assistant', '').strip()
                    response = response.replace('Instructions:', '').strip()
                    
                    # Remove leading artifacts
                    while response and (response.startswith('.') or response.startswith('-') or response.startswith(':')):
                        response = response[1:].strip()
                    
                    # Ensure we have a substantial response
                    if len(response) < 20:
                        return "The model generated a very short response. Please try rephrasing your question."
                    
                    # Remove repetitive content - if the same sentence appears multiple times, keep only one
                    sentences = response.split('. ')
                    seen_sentences = set()
                    clean_sentences = []
                    
                    for sentence in sentences:
                        sentence = sentence.strip()
                        if len(sentence) > 10:  # Skip very short fragments
                            # Check for near-duplicates (first 50 chars)
                            sentence_key = sentence[:50].lower()
                            if sentence_key not in seen_sentences:
                                seen_sentences.add(sentence_key)
                                if not sentence.endswith('.') and not sentence.endswith('!') and not sentence.endswith('?'):
                                    sentence += '.'
                                clean_sentences.append(sentence)
                    
                    # Join all unique sentences for a complete response
                    final_response = ' '.join(clean_sentences)
                    
                    return final_response if final_response else "No clear answer generated."
                else:
                    return "No clear answer generated."
            else:
                print(f"LLM command failed with return code: {result.returncode}")
                print(f"LLM stderr: {result.stderr}")
                print(f"LLM stdout: {result.stdout}")
                return f"LLM error (code {result.returncode}): {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return "I apologize, but the response generation timed out after 2 minutes. If your GPU drivers are not properly configured for llama.cpp, try reducing -ngl value or check GPU setup."
        except FileNotFoundError:
            return "LLM executable 'llama-cli' not found. Please ensure llama-cli is installed and in PATH."
        except Exception as e:
            return f"Unexpected error calling LLM: {e}"
        
        # Option 2: Using Ollama
        # Uncomment and modify this section if you're using Ollama
        """
        try:
            cmd = [
                "ollama", "run", self.model_path.split('/')[-1],  # Extract model name
                prompt
            ]
            
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
            return "I apologize, but the response generation timed out after 2 minutes. If your GPU drivers are not properly configured for llama.cpp, try reducing -ngl value or check GPU setup."
        except FileNotFoundError:
            return "Ollama not found. Please ensure Ollama is installed and in PATH."
        """
        
        # If we reach here, something went wrong - return error
        return "LLM configuration error: No valid LLM backend found."
    
    def update_config(self, **kwargs):
        """
        Update LLM configuration parameters.
        
        This method allows dynamic modification of generation parameters without
        recreating the LLMInterface instance. It updates the internal configuration
        dictionary with the provided key-value pairs.
        
        Args:
            **kwargs: Configuration parameters to update.
                     Common parameters include:
                     - temperature (float): Controls randomness (0.0-1.0)
                     - max_new_tokens (int): Maximum tokens to generate
                     - top_p (float): Nucleus sampling parameter
                     - top_k (int): Top-k sampling parameter
                     - do_sample (bool): Whether to use sampling
                     
        Example:
            >>> llm = LLMInterface()
            >>> llm.update_config(temperature=0.5, max_new_tokens=256)
            >>> llm.update_config(top_p=0.8)
            
        Note:
            Changes only affect future generations, not ongoing ones.
            The updated configuration is logged for debugging purposes.
        """
        self.config.update(kwargs)
        print(f"Updated LLM config: {kwargs}")


# Global LLM interface instance (lazy loading)
# This singleton pattern ensures efficient memory usage and avoids reloading models
_llm_interface = None


def get_llm_interface() -> LLMInterface:
    """
    Get the global LLM interface instance (singleton pattern).
    
    This function implements a singleton pattern to ensure that only one
    LLM interface instance is created and reused throughout the application.
    This is important for memory efficiency and avoiding repeated model loading
    overhead.
    
    Returns:
        LLMInterface: The global LLM interface instance.
                     If this is the first call, the interface will be initialized.
                     Subsequent calls return the same instance.
                     
    Example:
        >>> llm1 = get_llm_interface()
        >>> llm2 = get_llm_interface()
        >>> assert llm1 is llm2  # Same instance
        
    Note:
        The first call to this function may take time if it involves
        loading or initializing the LLM backend.
    """
    global _llm_interface
    if _llm_interface is None:
        _llm_interface = LLMInterface()
    return _llm_interface
