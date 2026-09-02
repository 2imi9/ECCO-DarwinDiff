"""Earth2Studio adapters for the DarwinDiff ocean-BGC emulator.

This package makes the FNO/SFNO emulator conform to the NVIDIA Earth2Studio
model interface so it can plug into that stack as the *first ocean-BGC
PrognosticModel* (the Earth-2 / PhysicsNeMo stack has zero ocean/BGC models —
verified whitespace; see docs/research_notes/2026-07-23_3d_emulator_earth2studio_design.md).

Everything is import-guarded: earth2studio is a cluster-only dependency, so on a
laptop / CI these classes still import and run against light fallback shims.
"""
from darwindiff.e2s.datasource import EccoDarwinV05
from darwindiff.e2s.prognostic import E2S_AVAILABLE, DarwinBGCPrognostic

__all__ = ["E2S_AVAILABLE", "DarwinBGCPrognostic", "EccoDarwinV05"]
