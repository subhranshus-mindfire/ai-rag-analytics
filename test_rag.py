"""
CLI Test Script for RAG Pipeline.
Runs ingestion of sample documents, vector embedding, and query retrieval.
"""
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.rag.pipeline import rag_pipeline
from app.config import settings

def main():
    print("=" * 60)
    print("🚀 Testing RAG Pipeline (Document Ingestion & Retrieval)")
    print("=" * 60)
    
    sample_file = "data/docs/company_policies.txt"
    print(f"\n1. Ingesting document: {sample_file}")
    result = rag_pipeline.ingest_document(sample_file)
    print(f"   Indexed Chunks: {result['chunks_indexed']}")
    print(f"   Total in Store: {result['total_documents']}")
    
    test_queries = [
        "What is the refund policy for annual subscriptions?",
        "What are the SLA response times for Enterprise customers?",
        "How much does the Cloud Vector Engine Pro cost per month?"
    ]

    for q in test_queries:
        print("\n" + "-" * 60)
        print(f"❓ Query: {q}")
        response = rag_pipeline.ask(q, top_k=2)
        print(f"🤖 Answer ({response['provider']}):")
        print(f"   {response['answer']}")
        print(f"📚 Sources: {response['sources']}")
        print("🔍 Top Retrieved Chunk Preview:")
        if response["retrieved_chunks"]:
            preview = response["retrieved_chunks"][0]["content"][:150].replace("\n", " ")
            print(f"   \"{preview}...\" (Score: {response['retrieved_chunks'][0]['score']:.2f})")
    
    print("\n" + "=" * 60)
    print("✅ RAG Pipeline test completed successfully.")
    print("=" * 60)

if __name__ == "__main__":
    main()
