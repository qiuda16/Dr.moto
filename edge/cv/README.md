# Computer Vision Module

This module handles visual perception tasks for the AI Agent.

## Responsibilities
- **Tool Detection**: Identify tools on the shadow board (10 screwdrivers).
- **Hand Tracking**: Track hand movements using MediaPipe to detect pick/place actions.
- **Safety Monitoring**: Detect PPE compliance.

## Events
Emits the following events (see `docs/schemas/agent_events/`):
- `tool_detected`
- `hand_action`
- `rule_violation`

## Integration
- Input: RTSP Stream / Camera Feed
- Output: Event Bus (MQTT/HTTP)
