import os
import sys

# Fix for DLL load failed: Add Anaconda Library\bin to PATH
anaconda_path = r"C:\Users\WIN10\anaconda3"
library_bin = os.path.join(anaconda_path, "Library", "bin")
if os.path.exists(library_bin):
    os.environ["PATH"] = library_bin + os.pathsep + os.environ["PATH"]

print("Importing SentenceTransformer...", flush=True)
from sentence_transformers import SentenceTransformer
print("Imported SentenceTransformer.", flush=True)

try:
    import torch
    print(f"Torch version: {torch.__version__}")
    x = torch.rand(5, 3)
    print(x)
    print("Torch works.")

    import transformers
    print(f"Transformers version: {transformers.__version__}")

    # from sentence_transformers import SentenceTransformer
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_OFFLINE"] = "1"
    
    model_path = r"C:\Users\WIN10\.cache\huggingface\hub\models--sentence-transformers--all-MiniLM-L6-v2\snapshots\c9745ed1d9f207416be6d2e6f8de32d1f16199bf"
    print(f"Loading SentenceTransformer from {model_path}...", flush=True)
    model = SentenceTransformer(model_path, device="cpu")
    print("SentenceTransformer loaded.", flush=True)
    
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")
