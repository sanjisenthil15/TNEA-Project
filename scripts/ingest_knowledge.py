"""
=============================================================
TNEA Career Insight Navigator — Knowledge Ingestion Script
=============================================================
CLI command to discover, clean, chunk, embed, and index project
knowledge into the persistent Chroma vector database.

Usage:
    python scripts/ingest_knowledge.py [--reindex]
"""

import sys
import argparse
from pathlib import Path

# Ensure root directory is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from models.rag_engine import ingest_all_knowledge, get_knowledge_collection


def main():
    parser = argparse.ArgumentParser(description="Ingest knowledge sources into persistent vector database.")
    parser.add_argument(
        "--reindex",
        action="store_true",
        help="Force full re-indexing of all knowledge documents."
    )
    args = parser.parse_args()

    print("=" * 60)
    print("TNEA CAREER INSIGHT NAVIGATOR — RAG KNOWLEDGE INGESTION")
    print("=" * 60)
    print(f"Force re-index: {args.reindex}")

    result = ingest_all_knowledge(force_reindex=args.reindex)

    print("\n--- Ingestion Report ---")
    print(f"Status: {result.get('status')}")
    print(f"Collection Name: {result.get('collection_name')}")
    print(f"Total Documents Processed: {result.get('total_documents', 'N/A')}")
    print(f"Total Chunks Indexed: {result.get('total_chunks')}")
    print(f"Embedding Model: {result.get('embedding_model')}")
    print("=" * 60)
    print("Vector database is ready for semantic retrieval.")


if __name__ == "__main__":
    main()
