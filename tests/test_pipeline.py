"""Integration test: run full pipeline with RandomWalkSource."""

import asyncio

import pytest

from cam_to_midi.config import (
    AppConfig,
    EngineConfig,
    MappingConfig,
    PerceptionConfig,
    RandomWalkConfig,
    SourceConfig,
)
from cam_to_midi.engine.engine import MusicEngine
from cam_to_midi.engine.theory import get_scale_notes
from cam_to_midi.mapping.registry import MapperRegistry
from cam_to_midi.perception.windowed import WindowedPerceptor
from cam_to_midi.pipeline import Pipeline
from cam_to_midi.sources.random_walk import RandomWalkSource


class CollectorSynth:
    """Test synth that collects messages instead of playing audio."""

    def __init__(self):
        self.messages = []

    def start(self): ...
    def stop(self): ...

    def send(self, msg):
        self.messages.append(msg)

    def set_instrument(self, ch, prog): ...


@pytest.mark.asyncio
async def test_full_pipeline():
    """Run the complete pipeline and verify musical output."""
    source_cfg = SourceConfig(
        type="random_walk",
        random_walk=RandomWalkConfig(tick_interval_sec=0.001),
    )
    source = RandomWalkSource(source_cfg.random_walk)
    perceptor = WindowedPerceptor(PerceptionConfig(window_size=10))
    mapper = MapperRegistry.create(MappingConfig(type="rule_based", preset="stock_basic"))
    engine = MusicEngine(EngineConfig(key="C", scale="major"))
    synth = CollectorSynth()

    pipeline = Pipeline(source, perceptor, mapper, engine, synth)

    await source.start()

    count = 0
    # Run manually instead of pipeline.run() to control iteration count
    async for sample in source.stream():
        features = perceptor.update(sample)
        if features is not None:
            engine.feed_mood(features.direction, features.volatility)
            event = mapper.map(features)
            messages = engine.process(event)
            for msg in messages:
                synth.send(msg)
            count += 1
        if count >= 50:
            await source.stop()
            break

    # Verify we got MIDI output
    assert len(synth.messages) > 0

    note_ons = [m for m in synth.messages if m.type == "note_on"]
    note_offs = [m for m in synth.messages if m.type == "note_off"]

    assert len(note_ons) > 0, "No note_on messages generated"

    # Verify all notes are in valid MIDI range
    for m in synth.messages:
        if hasattr(m, "note"):
            assert 0 <= m.note <= 127

    # Verify melody notes are in C major scale
    scale_pcs = set(get_scale_notes("C", "major"))
    melody_notes = [m for m in note_ons if m.channel == 0]
    for m in melody_notes:
        assert m.note % 12 in scale_pcs, f"Melody note {m.note} not in C major"
