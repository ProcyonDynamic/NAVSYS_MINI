
## Core Architecture

NAVSYS uses a state-driven architecture inspired by mission control systems.

Modules read/write shared operational state:

- nav_state
- voyage_state
- vessel_state
- compliance_state
- environment_state

The UI visualizes state rather than running logic directly.