# Project Dashboard

## Purpose
A centralized dashboard to visualize project documentation, requirements status, and system implementation progress.

## Features
- **Documentation Browser**: Auto-scan and render all README.md files in the monorepo.
- **Requirement Analyzer**: Parse checklist items from markdown and verify implementation status (heuristic).
- **Modern UI**: Responsive layout using Tailwind CSS.

## Usage
Serve this folder using a static file server (e.g., `python -m http.server 8001`) and ensure the BFF is running on port 8080.
