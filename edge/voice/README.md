# Voice Interaction Module

This module handles audio input/output for the AI Agent.

## Responsibilities
- **ASR (Automatic Speech Recognition)**: Convert voice commands to text.
- **TTS (Text-to-Speech)**: Announce alerts, instructions, and feedback.
- **Wake Word**: Detect activation phrases (e.g., "Hey Jarvis").

## Events
Emits:
- `voice_command`

Subscribes to:
- `rule_violation` (to announce warnings)
- `chat_response` (from AI Service)

## Integration
- Input: Microphone
- Output: Speaker
