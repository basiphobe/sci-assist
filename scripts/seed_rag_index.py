#!/usr/bin/env python3
"""
Seed the RAG index with SCI-specific Wikipedia content.

This script pre-indexes Wikipedia articles relevant to spinal cord injury,
assistive technology, and accessibility so the daily message generator has
a rich pool of varied content to draw from.
"""

import sys
import os
from pathlib import Path

# Set up paths
RAG_SYSTEM_PATH = Path(__file__).parent.parent / "ajsgptrag"
sys.path.insert(0, str(RAG_SYSTEM_PATH))

os.environ['CUDA_VISIBLE_DEVICES'] = '0'
os.environ['RAG_DEVICE'] = 'cpu'

# Fix Wikipedia API user-agent and add retry logic for rate limits
import wikipedia
import wikipedia.wikipedia as wp
import requests
import time as _time

wikipedia.set_user_agent('SCI-Assist-Bot/1.0 (sci-assist research project; contact@example.com)')

# Patch _wiki_request to handle 429 rate limits with retry
_original_wiki_request = wp._wiki_request

def _wiki_request_with_retry(params):
    """Wrapper around wikipedia's _wiki_request that retries on 429."""
    for attempt in range(5):
        try:
            return _original_wiki_request(params)
        except (requests.exceptions.JSONDecodeError, Exception) as e:
            if '429' in str(e) or 'Expecting value' in str(e):
                wait = 5 * (attempt + 1)
                print(f"\n    Rate limited, waiting {wait}s...", end="", flush=True)
                _time.sleep(wait)
            else:
                raise
    raise RuntimeError("Wikipedia API rate limit exceeded after retries")

wp._wiki_request = _wiki_request_with_retry

from src.embeddings import EmbeddingModel
from src.vector_store import VectorStore
from src.wikipedia_retriever import WikipediaRetriever

# SCI-specific topics to index
TOPICS = [
    # Core SCI
    "Spinal cord injury",
    "Paraplegia",
    "Tetraplegia",
    "Quadriplegia",
    "Brown-Séquard syndrome",
    "Central cord syndrome",
    "Anterior cord syndrome",
    "Cauda equina syndrome",
    "Neurogenic shock",
    "Spinal shock",
    
    # Medical/health
    "Pressure ulcer",
    "Neurogenic bladder",
    "Autonomic dysreflexia",
    "Spasticity",
    "Neuropathic pain",
    "Deep vein thrombosis",
    "Heterotopic ossification",
    "Respiratory management spinal cord injury",
    "Functional electrical stimulation",
    "Epidural stimulation",
    
    # Mobility/equipment
    "Wheelchair",
    "Power wheelchair",
    "Standing wheelchair",
    "Wheelchair racing",
    "Hand cycle",
    "Transfer (disability)",
    "Wheelchair ramp",
    "Curb cut",
    "Wheelchair accessible van",
    
    # Assistive technology
    "Assistive technology",
    "Screen reader",
    "Voice control",
    "Eye tracking",
    "Sip-and-puff",
    "Environmental control system",
    "Brain-computer interface",
    "Exoskeleton (disability)",
    "Robotic arm",
    "Adaptive controller",
    "Head mouse",
    
    # Daily living
    "Activities of daily living",
    "Adaptive clothing",
    "Occupational therapy",
    "Physical therapy",
    "Rehabilitation medicine",
    "Independent living",
    
    # Sports/recreation
    "Wheelchair basketball",
    "Wheelchair rugby",
    "Wheelchair tennis",
    "Adaptive skiing",
    "Adaptive surfing",
    "Paralympic Games",
    "Wheelchair fencing",
    "Handcycling",
    
    # Rights/accessibility
    "Americans with Disabilities Act of 1990",
    "Universal design",
    "Web accessibility",
    "Accessible housing",
    "Disability rights movement",
    "Section 504",
    
    # People/organizations
    "Christopher Reeve",
    "National Spinal Cord Injury Association",
    "Model Systems Knowledge Translation Center",
    "Paralyzed Veterans of America",
    
    # Mental health/wellness
    "Chronic pain management",
    "Peer support",
    "Caregiver stress",
    "Adaptive yoga",
    "Mindfulness-based stress reduction",
]


def main():
    print(f"Seeding RAG index with {len(TOPICS)} SCI-specific topics...")
    print()
    
    # Initialize components
    embedding_model = EmbeddingModel()
    vector_store = VectorStore()
    retriever = WikipediaRetriever()
    
    initial_count = vector_store.index.ntotal if vector_store.index else 0
    print(f"Current index size: {initial_count} vectors")
    print()
    
    total_chunks = 0
    successful = 0
    failed = []
    
    import time
    
    for i, topic in enumerate(TOPICS, 1):
        print(f"[{i}/{len(TOPICS)}] Indexing: {topic}...", end=" ", flush=True)
        
        try:
            chunks = retriever.retrieve_and_chunk(topic)
            if chunks:
                chunk_texts = [chunk.text for chunk in chunks]
                embeddings = embedding_model.embed_passages(chunk_texts)
                vector_store.add_embeddings(embeddings, chunks)
                total_chunks += len(chunks)
                successful += 1
                print(f"✓ {len(chunks)} chunks")
            else:
                failed.append(topic)
                print("✗ no content found")
        except Exception as e:
            failed.append(topic)
            print(f"✗ error: {e}")
        
        # Rate limit: pause between requests to avoid 429s
        time.sleep(5)
    
    # Save the index
    print()
    print("Saving index...")
    vector_store.save_index()
    
    final_count = vector_store.index.ntotal if vector_store.index else 0
    
    print()
    print(f"Done!")
    print(f"  Topics indexed: {successful}/{len(TOPICS)}")
    print(f"  Chunks added: {total_chunks}")
    print(f"  Index size: {initial_count} → {final_count} vectors")
    
    if failed:
        print(f"\n  Failed topics ({len(failed)}):")
        for t in failed:
            print(f"    - {t}")


if __name__ == "__main__":
    main()
