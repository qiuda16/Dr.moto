import os
import sys

# Fix for DLL load failed: Add Anaconda Library\bin to PATH
anaconda_path = r"C:\Users\WIN10\anaconda3"
library_bin = os.path.join(anaconda_path, "Library", "bin")
if os.path.exists(library_bin):
    os.environ["PATH"] = library_bin + os.pathsep + os.environ["PATH"]

# Set Hugging Face Mirror
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.docstore.document import Document

def test_isolation():
    print("1. Initializing Embeddings...")
    try:
        embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        print("Embeddings initialized.")
    except Exception as e:
        print(f"Embeddings failed: {e}")
        return

    print("2. Creating Dummy Document...")
    docs = [Document(page_content="This is a test document.", metadata={"source": "test"})]
    
    print("3. Ingesting into Chroma...")
    try:
        db = Chroma.from_documents(
            documents=docs, 
            embedding=embedding_function, 
            persist_directory="test_chroma_db",
            collection_name="test_collection"
        )
        db.persist()
        print("Chroma ingestion successful.")
    except Exception as e:
        print(f"Chroma failed: {e}")

if __name__ == "__main__":
    test_isolation()
