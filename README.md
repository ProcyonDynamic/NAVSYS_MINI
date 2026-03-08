# NAVSYS Mini

NAVSYS Mini is an offline-first maritime operational intelligence system designed for bridge use.

## Core modules
- NavWarn Mini
- AstraNav Mini
- Portalis Mini

## Architecture
NAVSYS follows a modular, state-driven architecture inspired by mission-control systems.

- UI shell under `NAVSYS/`
- module logic under `modules/`
- operational data under `data/`
- persistent design memory under `docs/`
- bundled external tools under `tools/`

## Governance
NAVSYS follows the OBERL model:

Observation -> Boundary -> Escalation -> Responsibility -> Loop

The UI should remain calm under normal conditions and surface meaningful deviations when operational boundaries are crossed.

## Current capabilities
### NavWarn Mini
- warning ingestion
- geometry extraction
- route/ship distance logic
- JRC plotting output
- NS-01 register

### AstraNav Mini
- Skyfield celestial engine
- NSC-01 compass/gyro error
- NSC-02 line of position

### Portalis Mini
- vessel/voyage state
- crew registry
- crew document registry
- port requirements
- document generation
- certificate registry

## Deployment
Development mode:

```powershell
python NAVSYS\app\main.py