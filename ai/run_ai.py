import os
import sys
import uvicorn

# Fix for DLL load failed: Add Anaconda Library\bin to PATH
anaconda_path = r"C:\Users\WIN10\anaconda3"
library_bin = os.path.join(anaconda_path, "Library", "bin")
if os.path.exists(library_bin):
    os.environ["PATH"] = library_bin + os.pathsep + os.environ["PATH"]

# Set Hugging Face Mirror
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

# Default local LLM runtime
os.environ.setdefault("AI_LLM_PROVIDER", "ollama")
os.environ.setdefault("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
os.environ.setdefault("OLLAMA_MODEL", "qwen3:8b")
os.environ.setdefault("OLLAMA_FALLBACK_MODEL", "qwen3:4b")
os.environ.setdefault("OLLAMA_CONTEXT_WINDOW", "40960")
os.environ.setdefault("AI_CHAT_HISTORY_LIMIT", "16")
os.environ.setdefault("AI_CONTEXT_PAYLOAD_MAX_CHARS", "16000")

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(r"C:\Users\WIN10\Desktop\qd part\drmoto\ai\site-packages")

if __name__ == "__main__":
    print("Starting AI Service on port 8002...")
    # Add site-packages to PYTHONPATH env var for subprocesses
    site_packages = r"C:\Users\WIN10\Desktop\qd part\drmoto\ai\site-packages"
    if site_packages not in os.environ.get("PYTHONPATH", ""):
        os.environ["PYTHONPATH"] = site_packages + os.pathsep + os.environ.get("PYTHONPATH", "")
    
    uvicorn.run("app.main:app", host="0.0.0.0", port=8003, reload=False)
