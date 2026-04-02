from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MusicalEvent:
    """Musical parameter hints passed from mapper to engine.

    All values are [0, 1] — the engine interprets them in musical context.
    """

    pitch_hint: float  # Engine maps to scale degree
    velocity: float  # Engine maps to MIDI 0-127
    duration_hint: float  # Note length relative to beat
    density_hint: float  # Simultaneous notes: 0=single, 1=full chord
    register_hint: float  # Low (0) to high (1) octave preference
    urgency: float  # Influences tempo micro-adjustments and leap probability
    symbol: str = ""  # Source symbol — used by ambient engine for channel routing
