# ai-game-02 — City Walkthrough

A first-person night-city walking game rendered in full-screen colorful ASCII.
The centerpiece is a lively, atmospheric NIGHT cityscape — buildings lit up at night,
streets, terrain, restaurants with sidewalk tables — with a light survival loop
(slowly decaying hunger/thirst, replenished by eating/drinking at vendors) and a clear
mission to keep you walking.

Status: DESIGN ONLY. This repository currently contains the technical design document;
implementation has not started. See DESIGN.md for the full strategy and architecture.

## The design

DESIGN.md resolves every strategic decision before implementation begins:
- Renderer: 2D-DDA grid raycasting (2.5D heightfield), no SDF raymarching.
- Output: full-screen truecolor cell buffer with 256-color fallback; RLE single-write flush.
- Tech stack: Python 3.10+ standard library only (zero third-party dependencies).
- Build/test/package for both Linux and Windows, including a standalone Windows .exe.

## Run (planned — after implementation)

Linux:
    python3 run.py        # or ./run.sh

Windows:
    run.bat               # or python run.py

Requires Python 3.10+. Recommended Windows host: Windows Terminal.
