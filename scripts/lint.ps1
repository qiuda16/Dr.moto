Write-Host "Running lint checks..."

if (Get-Command flake8 -ErrorAction SilentlyContinue) {
    Write-Host "Running flake8..."
    flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
    flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
} else {
    Write-Host "flake8 not found. Please install it (pip install flake8) to run lint checks."
}

Write-Host "Lint check complete."
