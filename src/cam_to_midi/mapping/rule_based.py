from __future__ import annotations

import math
from pathlib import Path

from ..config import load_mapping_preset
from ..perception.features import FeatureVector
from .base import BaseMapper
from .musical_params import MusicalEvent


def _apply_curve(value: float, spec: dict) -> float:
    """Apply a mapping curve to a normalized input value."""
    in_lo, in_hi = spec.get("input_range", [0, 1])
    out_lo, out_hi = spec.get("output_range", [0, 1])
    curve = spec.get("curve", "linear")
    invert = spec.get("invert", False)

    # Normalize input to [0, 1]
    if in_hi - in_lo == 0:
        t = 0.5
    else:
        t = (value - in_lo) / (in_hi - in_lo)
    t = max(0.0, min(1.0, t))

    if invert:
        t = 1.0 - t

    # Apply curve
    if curve == "exponential":
        exp = spec.get("exponent", 2.0)
        t = math.pow(t, exp)
    elif curve == "step":
        steps = spec.get("steps", 4)
        t = round(t * steps) / steps

    # Map to output range
    return out_lo + t * (out_hi - out_lo)


class RuleBasedMapper(BaseMapper):
    """Configurable feature-to-music mapping using YAML presets."""

    def __init__(self, preset_name: str = "stock_basic", config_dir: str = "config"):
        self.preset = load_mapping_preset(preset_name, config_dir)

    def map(self, features: FeatureVector) -> MusicalEvent:
        def _get(param_name: str, default: float = 0.5) -> float:
            spec = self.preset.get(param_name)
            if spec is None:
                return default
            source_name = spec.get("source", "intensity")
            value = getattr(features, source_name, 0.5)
            return _apply_curve(value, spec)

        return MusicalEvent(
            pitch_hint=_get("pitch_hint"),
            velocity=_get("velocity"),
            duration_hint=_get("duration_hint"),
            density_hint=_get("density_hint"),
            register_hint=_get("register_hint"),
            urgency=_get("urgency"),
        )
