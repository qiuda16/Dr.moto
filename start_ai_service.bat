@echo off
setlocal
echo Starting AI Service on port 8003...

:: Fix for DLL load failed (sqlite3, etc.)
set "PATH=C:\Users\WIN10\anaconda3\Library\bin;%PATH%"

:: Optional defaults (can be overridden by existing environment variables)
if "%OPENAI_API_BASE%"=="" set "OPENAI_API_BASE=https://api.deepseek.com"
if "%HF_ENDPOINT%"=="" set "HF_ENDPOINT=https://hf-mirror.com"

:: Require user-provided API key via environment variable (do not hardcode secret in scripts)
if "%OPENAI_API_KEY%"=="" (
  echo ERROR: OPENAI_API_KEY is not set.
  echo Please set it first, for example:
  echo   set OPENAI_API_KEY=your_api_key_here
  exit /b 1
)

:: Set PYTHONPATH to include the project root so imports work correctly
set "PYTHONPATH=%CD%;%PYTHONPATH%"

:: Run the service
echo Running ai/run_ai.py...
C:\Users\WIN10\anaconda3\python.exe ai/run_ai.py
pause
