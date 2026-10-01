"""
Interactive Chat Interface for RAG Assistant.
Run this script to chat directly with your ingested documents from the terminal.
Usage:
    .venv/bin/python chat.py
"""
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.rag.pipeline import rag_pipeline
from app.config import settings

def main():
    print("=" * 65)
    print("🤖 Welcome to the AI RAG Assistant CLI")
    print(f"📌 Active Provider: {settings.LLM_PROVIDER.upper()}")
    print("💡 Ingesting sample documents into knowledge base...")
    
    sample_file = "data/docs/company_policies.txt"
    if Path(sample_file).exists():
        result = rag_pipeline.ingest_document(sample_file)
        print(f"✅ Ingested '{sample_file}' ({result.get('chunks_indexed', 0)} chunks indexed).")
    
    print("=" * 65)
    print("Ask any question about company policies, SLAs, or pricing.")
    print("Type 'exit' or 'quit' to stop.\n")

    while True:
        try:
            question = input("\n👤 You: ").strip()
            if not question:
                continue
            if question.lower() in ["exit", "quit", "q"]:
                print("👋 Goodbye!")
                break

            print("\n🔍 Retrieving context & thinking...")
            response = rag_pipeline.ask(question, top_k=2)

            print(f"\n🤖 Assistant ({response['provider']}):")
            print(response["answer"])

            if response.get("sources"):
                print(f"\n📄 Sources: {', '.join(response['sources'])}")

        except (KeyboardInterrupt, EOFError):
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
