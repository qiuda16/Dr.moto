import sys
import os
import traceback

# Fix for DLL load failed: Add Anaconda Library\bin to PATH
anaconda_path = r"C:\Users\WIN10\anaconda3"
library_bin = os.path.join(anaconda_path, "Library", "bin")
if os.path.exists(library_bin):
    os.environ["PATH"] = library_bin + os.pathsep + os.environ["PATH"]
    # Also add it to sys.path just in case, though PATH is what matters for DLLs
    print(f"Added {library_bin} to PATH")

try:
    import sentence_transformers
    print("sentence_transformers imported successfully!")
    print(f"Version: {sentence_transformers.__version__}")
except ImportError:
    print("Failed to import sentence_transformers")
    traceback.print_exc()
except Exception:
    print("An error occurred during import")
    traceback.print_exc()
