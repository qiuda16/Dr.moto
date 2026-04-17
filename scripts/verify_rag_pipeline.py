import sys
import os

# Add the project root to sys.path so we can import from ai.app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai.app.core.ingest import ingest_pdf, clear_db
from ai.app.core.rag import query_kb

def main():
    pdf_path = "Ducati_Monster_Manual_Mock.pdf"
    
    # 1. Check if PDF exists
    if not os.path.exists(pdf_path):
        print(f"Error: {pdf_path} not found. Please run scripts/create_mock_pdf.py first.")
        return

    print(f"--- 1. Ingesting {pdf_path} ---")
    try:
        # Clear existing DB to start fresh for test
        # clear_db() 
        count = ingest_pdf(pdf_path)
        print(f"Successfully ingested {count} chunks.")
    except Exception as e:
        print(f"Ingestion failed: {e}")
        return

    print("\n--- 2. Querying Knowledge Base ---")
    questions = [
        "How much oil does the Ducati Monster 937 take?",
        "What is the torque setting for the drain plug?",
        "How do I change the tires?" # This info is NOT in the mock PDF
    ]

    for q in questions:
        print(f"\nQ: {q}")
        try:
            result = query_kb(q)
            if isinstance(result, dict):
                print(f"A: {result['answer']}")
                print(f"Sources: {result['sources']}")
            else:
                print(f"A: {result}")
        except Exception as e:
            print(f"Query failed: {e}")

if __name__ == "__main__":
    main()
