# Store Display Terminal

This is the public-facing display screen for the store.

## Features
- **Queue Board:** Shows "Ready to Pickup" and "In Progress" orders.
- **Auto-Refresh:** Polls BFF every 30s.
- **Privacy:** Masks license plates (e.g., `AB***CD`).

## Setup

```bash
npm install
npm run dev
```

Runs on port 3000 by default.
Proxies `/api` to `http://localhost:8080` (BFF).
