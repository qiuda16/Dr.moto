# Edge Computing Layer

This directory contains the Edge modules for the DrMoto AI Agent system.

## Modules

- **cv/**: Computer Vision (Camera, MediaPipe, Tool Detection)
- **voice/**: Voice Interaction (ASR, TTS, Dialog)
- **iot_gateway/**: Sensor Aggregation (Torque, Environmental)
- **jarvis/**: Local Logic/Orchestration (Legacy/Placeholder)
- **rules/**: Local Rule Engine (Legacy/Placeholder)
- **vid/**: Vehicle ID / ALPR (Legacy/Placeholder)

## Architecture

Edge modules run locally on the workbench hardware (e.g., NVIDIA Jetson, Raspberry Pi, Industrial PC). They communicate via a local Event Bus (MQTT) and sync with the Cloud/On-Prem BFF.

## Event Schemas

All modules must adhere to the schemas defined in `docs/schemas/agent_events/`.
