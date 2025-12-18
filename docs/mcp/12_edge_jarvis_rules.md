# MCP Team 11 — Edge JARVIS + RULES

> Updated: 2025-12-17  
> Role: On-site orchestration + completeness/risk rules; retry-safe write-back to BFF.

## Inputs
- WO state mapping
- VID APIs
- BFF write-back APIs
- rules definitions

## Outputs
- step state machine mapped to WO
- rule evaluation output
- structured inspection results
- offline queue + replay

## MUST
- all write-backs through BFF
- blocking rules explainable
