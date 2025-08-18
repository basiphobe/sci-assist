"""
RAG system integration for enhanced Discord bot responses.

This module provides the integration layer between the Discord bot and the
Wikipedia RAG system, handling query detection, response enhancement, and
source attribution.
"""

import sys
import os
from pathlib import Path
from typing import Optional, List, Tuple
import logging

# Force use of only GTX 1070 (device 0), hide GTX 960
os.environ['CUDA_VISIBLE_DEVICES'] = '0'

# Add the RAG system to the Python path
RAG_SYSTEM_PATH = Path(__file__).parent.parent.parent.parent / "ajsgptrag"
sys.path.insert(0, str(RAG_SYSTEM_PATH))

try:
    from src.rag_system import WikipediaRAG, RAGResponse
except ImportError as e:
    logging.warning(f"Could not import RAG system: {e}")
    WikipediaRAG = None
    RAGResponse = None

from discord_llm_bot.config import RAGConfig
from discord_llm_bot.utils.logging import get_logger


class RAGIntegration:
    """
    Integration layer for Wikipedia RAG system.
    
    This class provides the interface between the Discord bot and the
    Wikipedia RAG system, handling query detection, response enhancement,
    and proper error handling.
    """
    
    def __init__(self, config: RAGConfig):
        """
        Initialize RAG integration.
        
        Args:
            config: RAG configuration settings
        """
        self.config = config
        self.logger = get_logger(__name__)
        self._rag_system: Optional[WikipediaRAG] = None
        
                # Initialize RAG system if available and enabled
        if self.config.enabled and WikipediaRAG is not None:
            try:
                # Check GPU compatibility and fallback to CPU if needed
                import torch
                device = 'cpu'  # Default to CPU for compatibility
                
                if torch.cuda.is_available():
                    try:
                        # Test if CUDA actually works with our GPU
                        test_tensor = torch.tensor([1.0]).cuda()
                        del test_tensor
                        device = 'cuda:0'  # GTX 1070
                        self.logger.info(f"RAG system will use GPU: {torch.cuda.get_device_name(0)}")
                    except Exception as cuda_err:
                        self.logger.warning(f"CUDA test failed, falling back to CPU: {cuda_err}")
                        device = 'cpu'
                else:
                    self.logger.info("CUDA not available, using CPU")
                
                # Force CPU for now due to PyTorch/CUDA compatibility issues
                device = 'cpu'
                self.logger.info("RAG system using CPU (PyTorch 2.8 + GTX 1070 compatibility)")
                
                # Set environment variable for the RAG system
                os.environ['RAG_DEVICE'] = device
                
                self._rag_system = WikipediaRAG()
                self.logger.info("RAG system initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize RAG system: {e}")
                self._rag_system = None
        else:
            if not self.config.enabled:
                self.logger.info("RAG system disabled in configuration")
            else:
                self.logger.warning("RAG system not available - WikipediaRAG could not be imported")
    
    def is_available(self) -> bool:
        """Check if RAG system is available and ready to use."""
        return self._rag_system is not None
    
    def should_use_rag(self, query: str) -> bool:
        """
        Determine if a query should be enhanced with RAG.
        
        Args:
            query: User query to analyze
            
        Returns:
            True if RAG should be used for this query
        """
        if not self.is_available():
            return False
            
        query_lower = query.lower()
        
        # Be more conservative - don't trigger RAG for very short messages or conversation flow
        if len(query) < 20:  # Too short to benefit from RAG
            return False
            
        # Don't trigger on conversational elements
        conversational_patterns = [
            "thanks", "thank you", "ok", "okay", "yeah", "yes", "no", "lol", "haha",
            "i think", "i agree", "that's", "that is", "good point", "interesting"
        ]
        
        if any(pattern in query_lower for pattern in conversational_patterns):
            return False
        
        # Check for trigger keywords (be more specific)
        for keyword in self.config.trigger_keywords:
            if keyword.lower() in query_lower:
                self.logger.debug(f"RAG triggered by keyword: {keyword}")
                return True
        
        # Check for question patterns that benefit from factual information
        question_indicators = [
            "what is", "what are", "how does", "how do", "why does", "why do",
            "when was", "when did", "where is", "where does", "who is", "who was",
            "tell me about", "explain", "describe", "definition of", "information about"
        ]
        
        for indicator in question_indicators:
            if indicator in query_lower:
                self.logger.debug(f"RAG triggered by question pattern: {indicator}")
                return True
        
        return False
    
    async def enhance_response(self, query: str) -> Optional[Tuple[str, List[str]]]:
        """
        Get enhanced context from RAG system.
        
        Args:
            query: User query to enhance
            
        Returns:
            Tuple of (enhanced_context, sources) if successful, None otherwise
        """
        if not self.is_available():
            return None
            
        try:
            self.logger.info(f"Querying RAG system for: {query[:100]}...")
            
            # Get chunks and scores from the RAG system retrieval
            chunks, scores = self._rag_system.retrieve_context(query)
            
            if not chunks:
                self.logger.warning("RAG system returned no relevant chunks")
                return None
            
            # Format the context from retrieved chunks
            context_parts = []
            sources = []
            
            for i, (chunk, score) in enumerate(zip(chunks, scores)):
                if hasattr(chunk, 'title') and hasattr(chunk, 'text'):
                    # Add source to list
                    if hasattr(chunk, 'source_url') and chunk.source_url:
                        sources.append(chunk.source_url)
                    elif hasattr(chunk, 'title'):
                        sources.append(f"Wikipedia: {chunk.title}")
                    
                    # Format chunk for context
                    context_parts.append(f"Source {i+1}: {chunk.title}\n{chunk.text}")
            
            if not context_parts:
                self.logger.warning("No usable chunks found in RAG results")
                return None
            
            # Combine context (limit length to avoid overwhelming the prompt)
            full_context = "\n\n".join(context_parts)
            if len(full_context) > 4000:  # Reasonable limit for context
                full_context = full_context[:4000] + "..."
            
            # Remove duplicate sources
            sources = list(dict.fromkeys(sources))[:5]  # Limit to 5 sources
            
            self.logger.info(f"RAG system returned {len(chunks)} chunks, {len(context_parts)} usable")
            
            return full_context, sources
            
        except Exception as e:
            self.logger.error(f"Error querying RAG system: {e}")
            return None
    
    def format_enhanced_prompt(self, original_query: str, user_context: str, rag_context: str, sources: List[str]) -> str:
        """
        Format an enhanced prompt that combines user context with RAG context.
        
        Args:
            original_query: The original user question
            user_context: Context from the conversation (original system prompt)
            rag_context: Enhanced context from RAG system
            sources: List of Wikipedia source URLs
            
        Returns:
            Formatted prompt for the LLM
        """
        # Preserve the original conversation context and enhance it
        enhanced_prompt = user_context
        
        # Add RAG enhancement as supplementary information
        rag_supplement = [
            "",
            "Additional factual context from Wikipedia:",
            rag_context,
            "",
            "Use this Wikipedia information to enhance your response if relevant, but maintain your conversational style and respond to the actual conversation context."
        ]
        
        if sources and self.config.include_sources:
            rag_supplement.extend([
                "",
                f"Wikipedia sources: {', '.join(sources[:3])}"
            ])
        
        return enhanced_prompt + "\n".join(rag_supplement)
    
    def get_stats(self) -> dict:
        """
        Get RAG system statistics.
        
        Returns:
            Dictionary with RAG system stats
        """
        if not self.is_available():
            return {"available": False, "reason": "RAG system not initialized"}
        
        try:
            rag_stats = self._rag_system.get_stats()
            return {
                "available": True,
                "rag_stats": rag_stats,
                "config": {
                    "enabled": self.config.enabled,
                    "trigger_keywords_count": len(self.config.trigger_keywords),
                    "confidence_threshold": self.config.confidence_threshold,
                    "include_sources": self.config.include_sources
                }
            }
        except Exception as e:
            return {"available": False, "error": str(e)}
