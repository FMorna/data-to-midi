import mido

from cam_to_midi.engine.engine import MusicEngine
from cam_to_midi.engine.theory import get_scale_notes
from cam_to_midi.mapping.musical_params import MusicalEvent


class TestMusicEngine:
    def _make_engine(self, key="C", scale="major"):
        from cam_to_midi.config import EngineConfig
        config = EngineConfig(key=key, scale=scale)
        return MusicEngine(config)

    def test_produces_midi_messages(self, sample_musical_event):
        engine = self._make_engine()
        messages = engine.process(sample_musical_event)
        assert len(messages) > 0
        assert all(isinstance(m, mido.Message) for m in messages)

    def test_note_on_messages_present(self, sample_musical_event):
        engine = self._make_engine()
        messages = engine.process(sample_musical_event)
        note_ons = [m for m in messages if m.type == "note_on"]
        assert len(note_ons) > 0

    def test_melody_notes_in_scale(self):
        engine = self._make_engine(key="C", scale="major")
        scale_pcs = set(get_scale_notes("C", "major"))

        event = MusicalEvent(
            pitch_hint=0.5, velocity=0.6, duration_hint=0.5,
            density_hint=0.1, register_hint=0.5, urgency=0.3,
        )

        for _ in range(20):
            messages = engine.process(event)
            for m in messages:
                if m.type == "note_on" and m.channel == 0:  # Melody channel
                    assert m.note % 12 in scale_pcs, (
                        f"Note {m.note} (pc={m.note % 12}) not in C major scale"
                    )

    def test_velocity_in_range(self, sample_musical_event):
        engine = self._make_engine()
        messages = engine.process(sample_musical_event)
        for m in messages:
            if m.type == "note_on":
                assert 1 <= m.velocity <= 127

    def test_notes_in_midi_range(self, sample_musical_event):
        engine = self._make_engine()
        for _ in range(50):
            messages = engine.process(sample_musical_event)
            for m in messages:
                if m.type in ("note_on", "note_off"):
                    assert 0 <= m.note <= 127

    def test_set_key_changes_output(self):
        engine = self._make_engine(key="C", scale="major")
        event = MusicalEvent(
            pitch_hint=0.5, velocity=0.6, duration_hint=0.5,
            density_hint=0.1, register_hint=0.5, urgency=0.3,
        )

        # Collect some notes in C major
        c_notes = set()
        for _ in range(10):
            for m in engine.process(event):
                if m.type == "note_on" and m.channel == 0:
                    c_notes.add(m.note % 12)

        # Switch to A minor
        engine.set_key("A", "minor")
        a_notes = set()
        for _ in range(10):
            for m in engine.process(event):
                if m.type == "note_on" and m.channel == 0:
                    a_notes.add(m.note % 12)

        # A minor pitch classes should be in A minor scale
        a_minor_pcs = set(get_scale_notes("A", "minor"))
        for pc in a_notes:
            assert pc in a_minor_pcs


class TestSequencer:
    def test_beat_advances(self):
        from cam_to_midi.engine.sequencer import Sequencer
        seq = Sequencer(bpm=120)
        t1 = seq.tick()
        assert t1["beat"] == 0
        t2 = seq.tick()
        assert t2["beat"] == 1

    def test_bar_advances(self):
        from cam_to_midi.engine.sequencer import Sequencer
        seq = Sequencer(bpm=120, beats_per_bar=4)
        for _ in range(4):
            seq.tick()
        assert seq.current_bar == 1

    def test_chord_changes_per_bar(self):
        from cam_to_midi.engine.sequencer import Sequencer
        seq = Sequencer(bpm=120)
        chord1 = seq.current_chord
        for _ in range(4):
            seq.tick()
        chord2 = seq.current_chord
        # After one bar, chord should have advanced
        assert chord1 != chord2 or len(seq._resolved_progression) == 1
