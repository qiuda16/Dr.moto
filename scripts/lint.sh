#!/bin/bash
echo "Running lint checks..."

if command -v flake8 &> /dev/null; then
    echo "Running flake8..."
    flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
    flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
else
    echo "flake8 not found. Please install it (pip install flake8) to run lint checks."
fi

echo "Lint check complete."
