from __future__ import annotations

"""Core pipeline: Source -> Perception -> Mapping -> Engine -> Synth."""

import asyncio

from .engine.engine import MusicEngine
from .engine.midi_out import setup_channels
from .mapping.base import BaseMapper
from .perception.windowed import WindowedPerceptor
from .sources.base import BaseSource
from .synth.base import BaseSynth


class Pipeline:
    """Wires all stages together and runs the real-time loop."""

    def __init__(
        self,
        source: BaseSource,
        perceptor: WindowedPerceptor,
        mapper: BaseMapper,
        engine: MusicEngine,
        synth: BaseSynth,
    ):
        self.source = source
        self.perceptor = perceptor
        self.mapper = mapper
        self.engine = engine
        self.synth = synth
        self._on_event = None  # Optional callback for UI

    def set_event_callback(self, callback) -> None:
        """Set a callback that receives (features, event, messages) each tick."""
        self._on_event = callback

    async def run(self) -> None:
        """Run the pipeline loop until the source stops."""
        # Set up instrument programs
        for msg in setup_channels(self.engine.channels):
            self.synth.send(msg)

        async for sample in self.source.stream():
            features = self.perceptor.update(sample)
            if features is None:
                continue

            # Feed mood data for auto-progression
            self.engine.feed_mood(features.direction, features.volatility)

            event = self.mapper.map(features)
            messages = self.engine.process(event)

            for msg in messages:
                self.synth.send(msg)

            if self._on_event:
                self._on_event(features, event, messages)

            # Yield control to allow other tasks (UI, etc.)
            await asyncio.sleep(0)
