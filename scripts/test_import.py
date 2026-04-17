import os
import sys

print(f"Python Executable: {sys.executable}")
print(f"Sys Path: {sys.path}")

# Fix for DLL load failed: Add Anaconda Library\\bin to PATH
anaconda_path = r"C:\Users\WIN10\anaconda3"
library_bin = os.path.join(anaconda_path, "Library", "bin")
if os.path.exists(library_bin):
    print(f"Adding {library_bin} to PATH")
    os.environ["PATH"] = library_bin + os.pathsep + os.environ["PATH"]
else:
    print(f"Warning: {library_bin} does not exist")

try:
    import sentence_transformers
    print("Success: sentence_transformers imported")
except ImportError as e:
    print(f"Failed to import sentence_transformers: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
