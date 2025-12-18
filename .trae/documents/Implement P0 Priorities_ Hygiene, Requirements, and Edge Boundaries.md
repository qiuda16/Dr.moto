I will address the P0 priorities you identified to solidify the project foundation for AI Agent implementation and scalable collaboration.

### 1. Repository Hygiene & Governance
- **Create `.gitignore`**: Add comprehensive ignore rules for Python (`__pycache__`, `*.pyc`, `venv`), Node.js (`node_modules`), Docker, and OS files.
- **Cleanup**: Remove all existing `__pycache__` directories and `.pyc` files from the codebase to ensure a clean slate.
- **Minimal CI/Linting**: Create `scripts/lint.sh` (and `lint.ps1` for Windows) with a basic `flake8` or equivalent check to establish a quality gate.

### 2. Requirements & Schema System ("The Missing Link")
- **Establish `docs/requirements/`**: Create the directory structure with levels L1-L4 as requested:
    - `docs/requirements/L1_business_goals/`
    - `docs/requirements/L2_functional/`
    - `docs/requirements/L3_technical_specs/`
    - `docs/requirements/L4_acceptance_criteria/`
- **Define Agent Event Schemas**: Create `docs/schemas/agent_events/` and populate it with JSON schema definitions for key AI events:
    - `tool_detected.json` (CV identification)
    - `hand_action.json` (MediaPipe interaction)
    - `rule_violation.json` (Safety/Process alerts)
    - `voice_command.json` (ASR/TTS intent)
    - `kb_query.json` (RAG lookup)

### 3. Edge Module Engineering (AI Agent Boundaries)
- **Expand `edge/` Structure**: Create dedicated modules with explicit boundaries (README + entry points):
    - **`edge/cv/`**: Computer Vision module (Tool wall, Hand tracking).
    - **`edge/voice/`**: Voice interaction module (STT, TTS, Dialog).
    - **`edge/iot_gateway/`**: IoT Hub (Torque data, Sensor collection).
- **Integration**: Ensure these modules reference the schemas defined in step 2.

### 4. Verification
- Verify the clean file tree (no `__pycache__`).
- Check that the new directories and schema files exist.
- Confirm the structure matches the "Microservices-ready" and "Contract-driven" goals.