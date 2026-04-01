from __future__ import annotations

from ..config import SynthConfig
from .base import BaseSynth


class SynthRegistry:
    @classmethod
    def create(cls, config: SynthConfig) -> BaseSynth:
        if config.backend == "fluidsynth":
            from .fluidsynth_backend import FluidSynthBackend

            return FluidSynthBackend(config.soundfont, config.gain)
        elif config.backend == "pygame":
            from .pygame_synth import PygameSynth

            return PygameSynth()
        else:
            raise ValueError(
                f"Unknown synth backend: {config.backend}. Available: fluidsynth, pygame"
            )
