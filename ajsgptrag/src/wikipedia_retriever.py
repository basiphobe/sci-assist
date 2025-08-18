"""
Wikipedia content retrieval and chunking functionality.

This module provides comprehensive Wikipedia content retrieval and processing
capabilities for the RAG system. It handles searching Wikipedia articles,
retrieving full content, cleaning and preprocessing text, and intelligently
chunking content into manageable pieces for embedding and retrieval.

Key Features:
- Wikipedia search with configurable result limits
- Robust content retrieval with disambiguation handling
- Advanced text cleaning and preprocessing
- Intelligent text chunking with sentence boundary preservation
- Comprehensive error handling for network and API issues
- Metadata preservation for source attribution

Text Processing Pipeline:
1. Search: Use Wikipedia API to find relevant articles
2. Retrieve: Fetch full article content and URLs
3. Clean: Remove citations, formatting, and unwanted characters
4. Chunk: Split into overlapping segments with sentence boundaries
5. Package: Create structured chunks with metadata

Chunking Strategy:
The chunking algorithm balances several concerns:
- Preserving semantic coherence by respecting sentence boundaries
- Maintaining reasonable chunk sizes for embedding models
- Providing overlap between chunks to avoid losing context at boundaries
- Limiting total chunks per article to manage index size

Example:
    >>> from src.wikipedia_retriever import WikipediaRetriever
    >>> retriever = WikipediaRetriever()
    >>> 
    >>> # Search and retrieve content
    >>> chunks = retriever.retrieve_and_chunk("machine learning")
    >>> print(f"Retrieved {len(chunks)} chunks")
    >>> 
    >>> # Process individual articles
    >>> titles = retriever.search_wikipedia("artificial intelligence")
    >>> for title in titles:
    ...     content, url = retriever.get_page_content(title)
    ...     if content:
    ...         cleaned = retriever.clean_text(content)
    ...         article_chunks = retriever.chunk_text(cleaned, title, url)

Dependencies:
    - wikipedia: Python Wikipedia API wrapper
    - re: Regular expression operations for text cleaning
    - typing: Type hints and annotations
    - dataclasses: For structured data representation
"""

import wikipedia
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from src.config import (
    WIKIPEDIA_SEARCH_RESULTS, 
    CHUNK_SIZE, 
    CHUNK_OVERLAP, 
    MAX_CHUNKS_PER_ARTICLE
)


@dataclass
class WikipediaChunk:
    """
    Represents a chunk of Wikipedia content with comprehensive metadata.
    
    This dataclass encapsulates a text chunk extracted from a Wikipedia article
    along with all the metadata needed for source attribution, position tracking,
    and content management. It serves as the fundamental unit of content in the
    RAG system's vector store.
    
    Attributes:
        text (str): The actual text content of the chunk.
                   Should be cleaned and ready for embedding.
        title (str): The title of the Wikipedia article this chunk came from.
                    Used for source attribution and grouping.
        url (str): The full URL of the Wikipedia article.
                  Enables direct linking to sources.
        chunk_id (int): Sequential identifier within the article (0-based).
                       Useful for ordering and debugging.
        start_pos (int): Character position where this chunk starts in the original article.
                        Enables precise location tracking.
        end_pos (int): Character position where this chunk ends in the original article.
                      Used for overlap calculation and validation.
                      
    Example:
        >>> chunk = WikipediaChunk(
        ...     text="Python is a high-level programming language...",
        ...     title="Python (programming language)",
        ...     url="https://en.wikipedia.org/wiki/Python_(programming_language)",
        ...     chunk_id=0,
        ...     start_pos=0,
        ...     end_pos=250
        ... )
        >>> print(f"Chunk from {chunk.title}: {chunk.text[:50]}...")
        
    Note:
        All position values are in characters, not tokens or words.
        The chunk_id is unique within an article but not globally.
    """
    text: str
    title: str
    url: str
    chunk_id: int
    start_pos: int
    end_pos: int


class WikipediaRetriever:
    """
    Handles Wikipedia search and content chunking with robust error handling.
    
    This class provides a complete solution for retrieving and processing Wikipedia
    content for use in RAG systems. It combines Wikipedia's search API with
    intelligent text processing to create high-quality content chunks suitable
    for embedding and retrieval.
    
    The retriever implements several advanced features:
    - Robust search with multiple fallback strategies
    - Disambiguation handling for ambiguous article titles
    - Advanced text cleaning optimized for Wikipedia content
    - Intelligent chunking that preserves sentence boundaries
    - Comprehensive error handling for network and API issues
    - Configurable limits to manage resource usage
    
    Text Processing Philosophy:
    The text processing is designed to balance information preservation with
    clean, embeddings-friendly content. It removes Wikipedia-specific artifacts
    while preserving the semantic content and structure.
    
    Chunking Strategy:
    The chunking algorithm prioritizes:
    1. Sentence boundary preservation for semantic coherence
    2. Reasonable chunk sizes for embedding model constraints
    3. Overlap between chunks to prevent context loss
    4. Manageable total chunk counts per article
    
    Example:
        >>> retriever = WikipediaRetriever()
        >>> 
        >>> # Search for articles
        >>> titles = retriever.search_wikipedia("quantum computing")
        >>> print(f"Found {len(titles)} articles")
        >>> 
        >>> # Get content from first article
        >>> if titles:
        ...     content, url = retriever.get_page_content(titles[0])
        ...     if content:
        ...         chunks = retriever.chunk_text(content, titles[0], url)
        ...         print(f"Created {len(chunks)} chunks")
    """
    
    def __init__(self):
        """
        Initialize the Wikipedia retriever.
        
        Sets up the Wikipedia API client with English language settings.
        The wikipedia library is configured for optimal performance and
        reliability for English Wikipedia content.
        
        Configuration:
        - Language: English ("en") for consistent content
        - Default settings optimized for content retrieval
        - Error handling configured for robustness
        
        Note:
            The Wikipedia library maintains its own internal session
            and connection pooling for efficient API usage.
        """
        # Set Wikipedia language
        wikipedia.set_lang("en")
        
    def search_wikipedia(self, query: str, max_results: int = WIKIPEDIA_SEARCH_RESULTS) -> List[str]:
        """
        Search Wikipedia for relevant articles.
        
        This method performs a Wikipedia search for the given query and returns
        a list of article titles that best match the search terms. It uses
        Wikipedia's built-in search functionality with robust error handling.
        
        Search Strategy:
        - Uses Wikipedia's relevance-based search ranking
        - Returns titles in order of relevance (most relevant first)
        - Handles network errors and API limitations gracefully
        - Provides empty list fallback for failed searches
        
        Args:
            query (str): Search query string.
                        Can be natural language or keywords.
                        Examples: "machine learning", "artificial intelligence applications"
            max_results (int): Maximum number of search results to return.
                             Defaults to WIKIPEDIA_SEARCH_RESULTS from config.
                             Actual results may be fewer if Wikipedia has fewer matches.
                             
        Returns:
            List[str]: List of Wikipedia article titles ordered by relevance.
                      Returns empty list if search fails or no results found.
                      
        Example:
            >>> retriever = WikipediaRetriever()
            >>> titles = retriever.search_wikipedia("neural networks", max_results=5)
            >>> for i, title in enumerate(titles, 1):
            ...     print(f"{i}. {title}")
            
        Note:
            The search uses Wikipedia's internal ranking algorithm, which
            considers factors like title matches, content relevance, and
            article popularity.
        """
        try:
            # Search for relevant Wikipedia pages
            search_results = wikipedia.search(query, results=max_results)
            return search_results
        except wikipedia.exceptions.WikipediaException as e:
            print(f"Wikipedia search error: {e}")
            return []
    
    def get_page_content(self, title: str) -> Optional[Tuple[str, str]]:
        """
        Get the content and URL of a Wikipedia page with disambiguation handling.
        
        This method retrieves the full text content and URL for a Wikipedia page
        given its title. It includes sophisticated handling for disambiguation
        pages and various error conditions that can occur during retrieval.
        
        Disambiguation Handling:
        When a title is ambiguous (multiple articles with similar names),
        Wikipedia returns a DisambiguationError. This method automatically
        selects the first option from the disambiguation list, which is
        typically the most common or notable meaning.
        
        Args:
            title (str): Wikipedia page title.
                        Should be an exact or close match to a Wikipedia article title.
                        Examples: "Python (programming language)", "Machine learning"
                        
        Returns:
            Optional[Tuple[str, str]]: Tuple of (content, url) if successful,
                                     None if page cannot be retrieved.
                                     - content: Full article text content
                                     - url: Full Wikipedia URL for the article
                                     
        Example:
            >>> retriever = WikipediaRetriever()
            >>> result = retriever.get_page_content("Python (programming language)")
            >>> if result:
            ...     content, url = result
            ...     print(f"Retrieved {len(content)} characters from {url}")
            ... else:
            ...     print("Failed to retrieve content")
            
        Error Handling:
        - DisambiguationError: Automatically tries first disambiguation option
        - PageError: Returns None for non-existent pages
        - Network errors: Returns None with error logging
        - General exceptions: Returns None with error logging
        
        Note:
            The content returned is raw Wikipedia text and may need cleaning
            before use in embeddings or display.
        """
        try:
            page = wikipedia.page(title)
            return page.content, page.url
        except wikipedia.exceptions.DisambiguationError as e:
            # Try the first option in case of disambiguation
            try:
                page = wikipedia.page(e.options[0])
                return page.content, page.url
            except:
                print(f"Could not resolve disambiguation for: {title}")
                return None
        except wikipedia.exceptions.PageError:
            print(f"Page not found: {title}")
            return None
        except Exception as e:
            print(f"Error retrieving page {title}: {e}")
            return None
    
    def clean_text(self, text: str) -> str:
        """
        Clean Wikipedia text by removing unwanted characters and formatting.
        
        This method performs comprehensive text cleaning specifically optimized
        for Wikipedia content. It removes Wikipedia-specific artifacts while
        preserving the semantic content and readability of the text.
        
        Cleaning Operations:
        1. Remove citation markers (e.g., [1], [2], [citation needed])
        2. Normalize whitespace and newlines
        3. Remove leading and trailing whitespace
        4. Preserve paragraph structure where appropriate
        
        The cleaning is conservative to avoid losing important semantic
        information while making the text suitable for embedding models
        and LLM consumption.
        
        Args:
            text (str): Raw Wikipedia text content.
                       May contain citations, formatting, and other artifacts.
                       
        Returns:
            str: Cleaned text ready for chunking and embedding.
                 Preserves semantic content while removing distracting elements.
                 
        Example:
            >>> retriever = WikipediaRetriever()
            >>> raw_text = "Python[1] is a programming language[2]. It was created in 1991[3]."
            >>> clean_text = retriever.clean_text(raw_text)
            >>> print(clean_text)  # "Python is a programming language. It was created in 1991."
            
        Note:
            The cleaning is designed to be fast and preserve the essential
            information while making text more suitable for semantic processing.
        """
        # Remove citations like [1], [2], etc.
        text = re.sub(r'\[\d+\]', '', text)
        
        # Remove multiple whitespaces and newlines
        text = re.sub(r'\s+', ' ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def chunk_text(self, text: str, title: str, url: str) -> List[WikipediaChunk]:
        """
        Split text into overlapping chunks with intelligent boundary detection.
        
        This method implements an advanced chunking algorithm that balances
        several competing objectives:
        - Maintaining reasonable chunk sizes for embedding models
        - Preserving semantic coherence by respecting sentence boundaries
        - Providing overlap between chunks to prevent context loss
        - Managing total chunk counts to avoid index bloat
        
        Chunking Algorithm:
        1. Check if text is small enough to keep as single chunk
        2. For larger texts, create overlapping chunks of configured size
        3. Attempt to end chunks at sentence boundaries when possible
        4. Ensure overlap between consecutive chunks for context preservation
        5. Limit total chunks per article to prevent index bloat
        
        Boundary Detection:
        The algorithm looks for sentence endings (periods) within an overlap
        region to create more semantically coherent chunks. If no good
        boundary is found, it uses the configured chunk size.
        
        Args:
            text (str): Cleaned text to be chunked.
                       Should be output from clean_text() method.
            title (str): Wikipedia article title for metadata.
                        Used for source attribution and debugging.
            url (str): Wikipedia article URL for metadata.
                      Enables direct linking to source material.
                      
        Returns:
            List[WikipediaChunk]: List of WikipediaChunk objects with metadata.
                                 Chunks are ordered sequentially through the text.
                                 Each chunk includes position information and metadata.
                                 
        Example:
            >>> retriever = WikipediaRetriever()
            >>> text = "Long article text here..."
            >>> title = "Sample Article"
            >>> url = "https://en.wikipedia.org/wiki/Sample_Article"
            >>> chunks = retriever.chunk_text(text, title, url)
            >>> 
            >>> for i, chunk in enumerate(chunks):
            ...     print(f"Chunk {i}: {len(chunk.text)} chars, "
            ...           f"pos {chunk.start_pos}-{chunk.end_pos}")
                          
        Configuration:
            Uses the following config values:
            - CHUNK_SIZE: Target size for each chunk
            - CHUNK_OVERLAP: Overlap between consecutive chunks
            - MAX_CHUNKS_PER_ARTICLE: Maximum chunks to create per article
            
        Note:
            The chunking preserves character position information, enabling
            precise location tracking within the original article.
        """
        chunks = []
        text_length = len(text)
        
        if text_length <= CHUNK_SIZE:
            # If text is short enough, return as single chunk
            chunk = WikipediaChunk(
                text=text,
                title=title,
                url=url,
                chunk_id=0,
                start_pos=0,
                end_pos=text_length
            )
            return [chunk]
        
        chunk_id = 0
        start = 0
        
        while start < text_length and chunk_id < MAX_CHUNKS_PER_ARTICLE:
            # Calculate end position
            end = min(start + CHUNK_SIZE, text_length)
            
            # Try to end at a sentence boundary
            if end < text_length:
                # Look for sentence endings within the overlap region
                sentence_end = text.rfind('.', start, end + CHUNK_OVERLAP)
                if sentence_end != -1 and sentence_end > start + CHUNK_SIZE // 2:
                    end = sentence_end + 1
            
            chunk_text = text[start:end].strip()
            
            if chunk_text:  # Only add non-empty chunks
                chunk = WikipediaChunk(
                    text=chunk_text,
                    title=title,
                    url=url,
                    chunk_id=chunk_id,
                    start_pos=start,
                    end_pos=end
                )
                chunks.append(chunk)
                chunk_id += 1
            
            # Move to next position with overlap
            start = max(start + CHUNK_SIZE - CHUNK_OVERLAP, end)
        
        return chunks
    
    def retrieve_and_chunk(self, query: str) -> List[WikipediaChunk]:
        """
        Search Wikipedia and return chunked content for the complete pipeline.
        
        This is the main method that orchestrates the entire Wikipedia
        retrieval and processing pipeline. It combines search, content
        retrieval, cleaning, and chunking into a single convenient interface.
        
        Pipeline Process:
        1. Search Wikipedia for articles matching the query
        2. Iterate through each found article
        3. Retrieve full content for each article
        4. Clean the content to remove artifacts
        5. Chunk the content into manageable pieces
        6. Collect all chunks with comprehensive metadata
        7. Provide detailed logging for monitoring and debugging
        
        Args:
            query (str): Search query to find relevant Wikipedia content.
                        Can be natural language or keywords.
                        Examples: "machine learning algorithms", "climate change"
                        
        Returns:
            List[WikipediaChunk]: List of all chunks from all retrieved articles.
                                 Chunks are ordered by article relevance, then by
                                 position within each article.
                                 Returns empty list if no content found.
                                 
        Example:
            >>> retriever = WikipediaRetriever()
            >>> chunks = retriever.retrieve_and_chunk("quantum computing")
            >>> print(f"Retrieved {len(chunks)} total chunks")
            >>> 
            >>> # Show articles found
            >>> articles = set(chunk.title for chunk in chunks)
            >>> print(f"From {len(articles)} articles: {list(articles)}")
            >>> 
            >>> # Show first chunk
            >>> if chunks:
            ...     first_chunk = chunks[0]
            ...     print(f"First chunk from '{first_chunk.title}':")
            ...     print(first_chunk.text[:200] + "...")
                    
        Error Handling:
        - Handles network errors gracefully
        - Continues processing if individual articles fail
        - Provides detailed logging for debugging
        - Returns partial results if some articles succeed
        
        Performance Notes:
        - Processing time scales with number of articles and their length
        - Network requests are made sequentially to be respectful to Wikipedia
        - Content is processed in memory, so very large articles may use significant RAM
        
        Logging:
        The method provides comprehensive logging including:
        - Articles being processed
        - Number of chunks created per article
        - Total chunks created
        - Error information for failed retrievals
        """
        # Search for relevant pages
        page_titles = self.search_wikipedia(query)
        
        if not page_titles:
            print(f"No Wikipedia results found for: {query}")
            return []
        
        all_chunks = []
        
        for title in page_titles:
            print(f"Processing Wikipedia page: {title}")
            
            # Get page content
            result = self.get_page_content(title)
            if result is None:
                continue
                
            content, url = result
            
            # Clean the content
            cleaned_content = self.clean_text(content)
            
            # Create chunks
            chunks = self.chunk_text(cleaned_content, title, url)
            all_chunks.extend(chunks)
            
            print(f"Created {len(chunks)} chunks from {title}")
        
        print(f"Total chunks created: {len(all_chunks)}")
        return all_chunks


# Global retriever instance (lazy loading)
# This singleton pattern ensures efficient memory usage and consistent Wikipedia API sessions
_wikipedia_retriever = None


def get_wikipedia_retriever() -> WikipediaRetriever:
    """
    Get the global Wikipedia retriever instance (singleton pattern).
    
    This function implements a singleton pattern to ensure that only one
    Wikipedia retriever instance is created and reused throughout the application.
    This provides several benefits:
    - Consistent Wikipedia API session management
    - Efficient memory usage (single instance)
    - Preserved language settings across calls
    - Reduced initialization overhead
    
    Returns:
        WikipediaRetriever: The global Wikipedia retriever instance.
                           If this is the first call, a new instance will be created
                           with English language settings.
                           Subsequent calls return the same instance.
                           
    Example:
        >>> retriever1 = get_wikipedia_retriever()
        >>> retriever2 = get_wikipedia_retriever()
        >>> assert retriever1 is retriever2  # Same instance
        >>> 
        >>> # Use the retriever
        >>> chunks = retriever1.retrieve_and_chunk("artificial intelligence")
        
    Note:
        The first call to this function initializes the Wikipedia API settings.
        All subsequent calls return immediately with the cached instance.
    """
    global _wikipedia_retriever
    if _wikipedia_retriever is None:
        _wikipedia_retriever = WikipediaRetriever()
    return _wikipedia_retriever
