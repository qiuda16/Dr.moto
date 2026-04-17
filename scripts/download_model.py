import os
import sys

# Fix for DLL load failed: Add Anaconda Library\bin to PATH
anaconda_path = r"C:\Users\WIN10\anaconda3"
library_bin = os.path.join(anaconda_path, "Library", "bin")
if os.path.exists(library_bin):
    os.environ["PATH"] = library_bin + os.pathsep + os.environ["PATH"]

# Set Hugging Face Mirror
# os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from huggingface_hub import snapshot_download

def download():
    print("Downloading model all-MiniLM-L6-v2...")
    try:
        path = snapshot_download(
            repo_id="sentence-transformers/all-MiniLM-L6-v2",
            allow_patterns=["*.json", "*.txt", "*.safetensors", "*.bin"],
            ignore_patterns=["*.onnx", "*.h5", "*.ot", "*.msgpack"]
        )
        print(f"Model downloaded to: {path}")
    except Exception as e:
        print(f"Download failed: {e}")

if __name__ == "__main__":
    download()
