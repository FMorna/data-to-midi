from __future__ import annotations

"""Application orchestrator: builds and runs the full pipeline."""

import asyncio
import signal

from .config import AppConfig
from .engine.engine import MusicEngine
from .mapping.registry import MapperRegistry
from .perception.windowed import WindowedPerceptor
from .pipeline import Pipeline
from .sources.registry import SourceRegistry
from .synth.registry import SynthRegistry


class App:
    def __init__(self, config: AppConfig):
        self.config = config
        self.source = SourceRegistry.create(config.source)
        self.perceptor = WindowedPerceptor(config.perception)
        self.mapper = MapperRegistry.create(config.mapping)
        self.engine = MusicEngine(config.engine)
        self.synth = SynthRegistry.create(config.synth)
        self.pipeline = Pipeline(
            self.source, self.perceptor, self.mapper, self.engine, self.synth
        )
        self._dashboard = None

    async def run(self) -> None:
        """Start all components and run the pipeline."""
        print(f"Starting data_to_midi...")
        print(f"  Source: {self.config.source.type}")
        print(f"  Mapper: {self.config.mapping.type} ({self.config.mapping.preset})")
        print(f"  Key: {self.config.engine.key} {self.config.engine.scale}")
        print(f"  BPM: {self.config.engine.bpm}")
        print(f"  Synth: {self.config.synth.backend}")
        print()

        # Start synth
        try:
            self.synth.start()
        except (ImportError, FileNotFoundError, RuntimeError) as e:
            print(f"Synth error: {e}")
            print("Continuing without audio output (MIDI messages will be generated but silent).")
            self.synth = _NullSynth()

        # Set up UI dashboard if available
        if self.config.ui.show_dashboard:
            self._setup_dashboard()

        # Start source
        await self.source.start()

        # Handle Ctrl+C gracefully
        loop = asyncio.get_event_loop()
        stop_event = asyncio.Event()

        def _signal_handler():
            print("\nStopping...")
            stop_event.set()

        try:
            loop.add_signal_handler(signal.SIGINT, _signal_handler)
        except NotImplementedError:
            pass  # Windows doesn't support add_signal_handler

        try:
            # Run pipeline until stopped
            pipeline_task = asyncio.create_task(self.pipeline.run())

            # Wait for stop signal
            await stop_event.wait()
            await self.source.stop()
            pipeline_task.cancel()
            try:
                await pipeline_task
            except asyncio.CancelledError:
                pass
        finally:
            self.synth.stop()
            print("Stopped.")

    def _setup_dashboard(self) -> None:
        """Try to set up the Rich terminal dashboard."""
        try:
            from .ui.console import ConsoleDashboard

            self._dashboard = ConsoleDashboard()
            self.pipeline.set_event_callback(self._dashboard.update)
        except ImportError:
            print("Install 'rich' for live dashboard: pip install data-to-midi[ui]")


class _NullSynth:
    """Silent fallback when no synth backend is available."""

    def start(self): ...
    def stop(self): ...
    def send(self, msg): ...
    def set_instrument(self, ch, prog): ...
