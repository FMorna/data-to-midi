from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FeatureVector:
    """Normalized behavioral dynamics extracted from raw data.

    All values are normalized to known ranges so mappers never deal with raw units.
    """

    timestamp: float
    change_rate: float  # Speed of change [-1, 1]
    periodicity: float  # Rhythmic regularity [0, 1]
    intensity: float  # Magnitude/energy [0, 1]
    direction: float  # Trend direction [-1 (down), 1 (up)]
    volatility: float  # Variance/turbulence [0, 1]
    density: float  # Event clustering/choppiness [0, 1]
    symbol: str = ""  # Source symbol (e.g. "AAPL") — empty for non-stock sources
