"""
Example usage and demonstration of the Wikipedia RAG system.
"""

from src.rag_system import WikipediaRAG


def demo_basic_usage():
    """Demonstrate basic RAG system usage."""
    print("=" * 60)
    print("Wikipedia RAG System - Basic Usage Demo")
    print("=" * 60)
    
    # Initialize the RAG system
    print("\n1. Initializing RAG system...")
    rag = WikipediaRAG()
    
    # Show initial stats
    print("\n2. Initial system stats:")
    stats = rag.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # Ask some questions
    questions = [
        "What is artificial intelligence?",
        "How does DNA replication work?", 
        "What are black holes?"
    ]
    
    print("\n3. Asking questions:")
    for i, question in enumerate(questions, 1):
        print(f"\n   Question {i}: {question}")
        answer = rag.query(question)
        print(f"   Answer: {answer[:200]}...")  # Show first 200 chars
        
        # Show updated stats after indexing
        if i == 1:  # After first question
            updated_stats = rag.get_stats()
            print(f"   → Indexed {updated_stats['vector_store_stats']['total_chunks']} chunks")


def demo_advanced_features():
    """Demonstrate advanced RAG system features."""
    print("\n" + "=" * 60)
    print("Advanced Features Demo")
    print("=" * 60)
    
    rag = WikipediaRAG()
    
    # Pre-index content for a specific topic
    print("\n1. Pre-indexing content for 'quantum physics'...")
    indexed_count = rag.index_query("quantum physics")
    print(f"   Indexed {indexed_count} chunks")
    
    # Ask related questions (should be faster since content is already indexed)
    quantum_questions = [
        "What is quantum entanglement?",
        "Explain the uncertainty principle",
        "What is a quantum computer?"
    ]
    
    print("\n2. Asking quantum physics questions:")
    for question in quantum_questions:
        print(f"\n   Q: {question}")
        
        # Retrieve context to show what was found
        chunks, scores = rag.retrieve_context(question, k=3)
        print(f"   Retrieved {len(chunks)} relevant chunks:")
        for i, (chunk, score) in enumerate(zip(chunks, scores)):
            print(f"     {i+1}. {chunk.title} (score: {score:.3f})")
        
        # Generate answer
        answer = rag.query(question, auto_index=False)  # Don't auto-index since we pre-indexed
        print(f"   A: {answer[:150]}...")
    
    # Show final stats
    print("\n3. Final system stats:")
    final_stats = rag.get_stats()
    for key, value in final_stats.items():
        print(f"   {key}: {value}")


def demo_interactive_session():
    """Simulate an interactive session."""
    print("\n" + "=" * 60)
    print("Interactive Session Simulation")
    print("=" * 60)
    
    rag = WikipediaRAG()
    
    # Simulate a conversation about space exploration
    conversation = [
        "What is the International Space Station?",
        "Who has visited the ISS?", 
        "What experiments are conducted on the ISS?",
        "How is the ISS supplied with resources?"
    ]
    
    print("\nSimulating conversation about space exploration:")
    
    for i, question in enumerate(conversation, 1):
        print(f"\n🤔 User {i}: {question}")
        answer = rag.query(question)
        print(f"🤖 Assistant: {answer[:200]}...")
        
        # Show retrieval info
        chunks, scores = rag.retrieve_context(question, k=2)
        if chunks:
            print(f"   📚 Sources: {', '.join(chunk.title for chunk in chunks)}")


def main():
    """Run all demonstration examples."""
    try:
        demo_basic_usage()
        demo_advanced_features() 
        demo_interactive_session()
        
        print("\n" + "=" * 60)
        print("Demo completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        print("Please ensure all dependencies are installed and models are available.")


if __name__ == "__main__":
    main()
