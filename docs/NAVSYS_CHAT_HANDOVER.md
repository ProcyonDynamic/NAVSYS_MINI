# NAVSYS MINI — Chat Continuation Handover

This document exists to continue development in new ChatGPT sessions without losing system context.

---

# Current Architecture State

NAVSYS MINI is a USB-first maritime operations system containing three primary modules:

- NavWarn Mini
- AstraNav Mini
- Portalis Mini

All modules run inside a unified Flask browser shell.

Repository root:

NAVSYS_USB/

---

# Core System Architecture

NAVSYS follows a layered design:

User Interface Layer  
Operational State Layer  
Module Engines  
Knowledge Layer  
Temporal Context Engine (TCE)

---

# Modules

## NavWarn Mini
Functions:
- ingest NAVAREA warnings
- interpret message text
- detect coordinates
- infer geometry
- compute route proximity
- export JRC CSV objects

Architecture now includes a **Warning Interpretation Layer**:

Normalize  
→ classify warning type  
→ detect coordinate format  
→ parse geometry phrases  
→ produce structured warning model  
→ geometry inference

Important future components:

- NavWarn Plotting Editor
- JRC CSV dictionary
- Context Map
- Route Manager integration

---

## AstraNav Mini

Features:

- NSC-01 Compass error
- NSC-02 Line of position
- Skyfield celestial engine

Future:

- map + route selection
- LOP visualization

---

## Portalis Mini

Purpose:

Automated port documentation system.

Data domains:

- vessel master data
- voyage state
- crew records
- certificates
- port requirements
- document generator
- arrival package generator

---

# Knowledge Layer

Separate from TCE.

Contains:

- coastlines
- maritime gazetteer
- sea areas (IHO S-23)
- chart context regions
- dialect dictionaries
- plotting policies

Used by NavWarn to resolve place names.

---

# Temporal Context Engine (TCE)

TCE records historical interpretation context.

Stores:

- raw warning text
- normalized text
- warning type
- coordinate format
- phrase interpretation
- generated geometry
- manual edits

Allows reconstruction of decisions.

---

# Coordinate System Governance

Canonical internal format:
Decimal degrees.

User formats allowed:
- Degrees + Decimal Minutes
- DMS
- NSEW formats

TCE stores both canonical coordinates and original text.

---

# Rendering Governance

Plot objects follow:

LINE_AGGREGATE doctrine.

Future configuration:

Policy file controlling:
- line thickness
- color
- style
- scaling behavior

---

# Future UI

NAVSYS Mini Shell contains:

Dashboard  
NavWarn  
AstraNav  
Portalis  
System

Dashboard will show:

- vessel state
- voyage state
- nearest active warning
- alerts
- tasks

---

# Development Rule

Before creating new files or modules:

Check repository structure first.

Avoid recreating components that already exist.
