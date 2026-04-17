@echo off
echo Starting AI Service on port 8003...

:: Fix for DLL load failed (sqlite3, etc.)
set "PATH=C:\Users\WIN10\anaconda3\Library\bin;%PATH%"

:: Environment Variables
set OPENAI_API_KEY=sk-dc16928cf1cd4305b617f34bf122c044
set OPENAI_API_BASE=https://api.deepseek.com
set HF_ENDPOINT=https://hf-mirror.com

:: Set PYTHONPATH to include the project root so imports work correctly
set "PYTHONPATH=%CD%;%PYTHONPATH%"

:: Run the service
echo Running ai/run_ai.py...
C:\Users\WIN10\anaconda3\python.exe ai/run_ai.py
pause
