"""
Interactive command-line interface for the Wikipedia RAG system.
"""

import argparse
import sys
from pathlib import Path
from src.rag_system import WikipediaRAG


def print_banner():
    """Print the application banner."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                    Wikipedia RAG System                      ║
║              Retrieval-Augmented Generation                  ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def interactive_mode(rag: WikipediaRAG):
    """Run the RAG system in interactive mode."""
    print("Interactive mode started. Type 'quit' or 'exit' to stop.")
    print("Type 'stats' to see system statistics.")
    print("Type 'clear' to clear the vector index.")
    print("-" * 60)
    
    while True:
        try:
            question = input("\n🤔 Ask a question: ").strip()
            
            if not question:
                continue
                
            if question.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            elif question.lower() == 'stats':
                stats = rag.get_stats()
                print("\n📊 System Statistics:")
                print(f"  Embedding Model: {stats['embedding_model']}")
                print(f"  Embedding Dimension: {stats['embedding_dimension']}")
                print(f"  Total Chunks: {stats['vector_store_stats']['total_chunks']}")
                print(f"  Unique Articles: {stats['vector_store_stats']['unique_articles']}")
                print(f"  LLM Model: {stats['llm_model']}")
                continue
            elif question.lower() == 'clear':
                rag.clear_index()
                print("🗑️ Vector index cleared!")
                continue
            
            print("\n🔍 Searching and generating answer...")
            answer = rag.query(question)
            
            print(f"\n💡 Answer:\n{answer}")
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


def single_query_mode(rag: WikipediaRAG, question: str):
    """Process a single query and exit."""
    print(f"Processing query: {question}")
    answer = rag.query(question)
    print(f"\nAnswer:\n{answer}")


def main():
    """Main CLI application."""
    parser = argparse.ArgumentParser(
        description="Wikipedia-powered RAG system for question answering",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py                                    # Interactive mode
  python cli.py -q "What is quantum computing?"    # Single query
  python cli.py --stats                           # Show system stats
  python cli.py --clear                           # Clear vector index
        """
    )
    
    parser.add_argument(
        "-q", "--query",
        type=str,
        help="Single query to process (non-interactive mode)"
    )
    
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show system statistics and exit"
    )
    
    parser.add_argument(
        "--clear",
        action="store_true", 
        help="Clear the vector index and exit"
    )
    
    parser.add_argument(
        "--no-banner",
        action="store_true",
        help="Don't show the banner"
    )
    
    args = parser.parse_args()
    
    # Show banner unless disabled
    if not args.no_banner:
        print_banner()
    
    try:
        # Initialize RAG system
        print("🚀 Initializing RAG system...")
        rag = WikipediaRAG()
        print("✅ RAG system ready!")
        
    except Exception as e:
        print(f"❌ Failed to initialize RAG system: {e}")
        sys.exit(1)
    
    # Handle different modes
    if args.stats:
        stats = rag.get_stats()
        print("\n📊 System Statistics:")
        print(f"  Embedding Model: {stats['embedding_model']}")
        print(f"  Embedding Dimension: {stats['embedding_dimension']}")
        print(f"  Total Chunks: {stats['vector_store_stats']['total_chunks']}")
        print(f"  Unique Articles: {stats['vector_store_stats']['unique_articles']}")
        print(f"  LLM Model: {stats['llm_model']}")
        
    elif args.clear:
        rag.clear_index()
        print("🗑️ Vector index cleared!")
        
    elif args.query:
        single_query_mode(rag, args.query)
        
    else:
        interactive_mode(rag)


if __name__ == "__main__":
    main()
