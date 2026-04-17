import os
import sys

# Fix for DLL load failed: Add Anaconda Library\bin to PATH
anaconda_path = r"C:\Users\WIN10\anaconda3"
library_bin = os.path.join(anaconda_path, "Library", "bin")
if os.path.exists(library_bin):
    os.environ["PATH"] = library_bin + os.pathsep + os.environ["PATH"]

# Set Hugging Face Mirror
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

# Set API Key for DeepSeek (provided by user)
os.environ["OPENAI_API_KEY"] = "sk-dc16928cf1cd4305b617f34bf122c044"
os.environ["OPENAI_API_BASE"] = "https://api.deepseek.com"

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.app.core.ingest import ingest_pdf
from ai.app.core.rag import query_kb

def main():
    # The user said the file is at C:\Users\WIN10\Desktop\qd part\1.pdf
    # This script is in C:\Users\WIN10\Desktop\qd part\drmoto\scripts
    # So relative path is ..\..\1.pdf
    
    # Using absolute path for safety as provided by user context
    pdf_path = r"C:\Users\WIN10\Desktop\qd part\1.pdf"
    collection_name = "real_manual_test"

    if not os.path.exists(pdf_path):
        print(f"Error: File not found at {pdf_path}")
        return

    # Clear existing DB to ensure clean test with new dependencies
    # chroma_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ai", "chroma_db")
    # if os.path.exists(chroma_path):
    #     print(f"Removing existing Chroma DB at {chroma_path}...")
    #     import shutil
    #     shutil.rmtree(chroma_path)

    print(f"--- 1. Ingesting {pdf_path} into collection '{collection_name}' ---")
    # try:
    #     # Ingest
    #     count = ingest_pdf(pdf_path, collection_name=collection_name)
    #     print(f"Successfully ingested {count} chunks.")
    # except Exception as e:
    #     print(f"Ingestion failed: {e}")
    #     return
    print("Skipping ingestion to save time (assuming already ingested).")
    
    # 2. Query
    print("\n--- 2. Querying KB ---")
    queries = [
        "如何更换机油?",
        "总结安全警告"
    ]
    
    for q in queries:
        print(f"\nQ: {q}", flush=True)
        try:
            result = query_kb(q, collection_name=collection_name)
            print(f"A: {result['answer']}", flush=True)
            print(f"Sources: {result['sources']}", flush=True)
        except Exception as e:
            print(f"Query failed: {e}", flush=True)

if __name__ == "__main__":
    main()
