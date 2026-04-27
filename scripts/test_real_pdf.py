import os
import sys
from pathlib import Path

# Optional: add Anaconda DLL path if present
anaconda_path = Path(r"C:\Users\WIN10\anaconda3")
library_bin = anaconda_path / "Library" / "bin"
if library_bin.exists():
    os.environ["PATH"] = str(library_bin) + os.pathsep + os.environ.get("PATH", "")

# Optional defaults (can be overridden by existing environment variables)
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("OPENAI_API_BASE", "https://api.deepseek.com")

if not os.environ.get("OPENAI_API_KEY"):
    raise SystemExit("OPENAI_API_KEY is required. Please set it in environment before running this script.")

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from ai.app.core.rag import query_kb


def main():
    pdf_path = Path(r"C:\Users\WIN10\Desktop\qd part\1.pdf")
    collection_name = "real_manual_test"

    if not pdf_path.exists():
        print(f"Error: file not found at {pdf_path}")
        return

    print(f"Testing KB query with collection '{collection_name}'")
    queries = [
        "如何更换机油？",
        "总结安全警告要点",
    ]

    for q in queries:
        print(f"\nQ: {q}", flush=True)
        try:
            result = query_kb(q, collection_name=collection_name)
            print(f"A: {result['answer']}", flush=True)
            print(f"Sources: {result['sources']}", flush=True)
        except Exception as exc:
            print(f"Query failed: {exc}", flush=True)


if __name__ == "__main__":
    main()
