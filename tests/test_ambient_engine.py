import mido

from data_to_midi.config import EngineConfig, ChannelConfig
from data_to_midi.engine.ambient_engine import AmbientStockEngine
from data_to_midi.engine.theory import get_scale_notes
from data_to_midi.mapping.musical_params import MusicalEvent


def _make_engine(symbols=None, key="C", scale="dorian"):
    symbols = symbols or ["AAPL", "GOOGL", "MSFT"]
    config = EngineConfig(
        bpm=75, key=key, scale=scale, mode="ambient_stock",
        velocity_range=[20, 80],
        channels={
            "lead": ChannelConfig(0, 81),
            "pad": ChannelConfig(1, 89),
            "bass": ChannelConfig(2, 39),
            "atmosphere": ChannelConfig(3, 92),
        },
    )
    return AmbientStockEngine(config, symbols)


def _make_event(symbol="AAPL", pitch=0.5, vel=0.5, dur=0.7, density=0.1, reg=0.5, urg=0.2):
    return MusicalEvent(
        pitch_hint=pitch, velocity=vel, duration_hint=dur,
        density_hint=density, register_hint=reg, urgency=urg,
        symbol=symbol,
    )


class TestAmbientStockEngine:
    def test_produces_midi_messages(self):
        engine = _make_engine()
        all_msgs = []
        for _ in range(10):
            msgs = engine.process(_make_event("AAPL"))
            all_msgs.extend(msgs)
        assert len(all_msgs) > 0
        assert all(isinstance(m, mido.Message) for m in all_msgs)

    def test_symbol_routes_to_correct_channel(self):
        engine = _make_engine(["AAPL", "GOOGL", "MSFT"])
        # Run many ticks per symbol (probability gate may skip some)
        for sym, expected_ch in [("AAPL", 0), ("GOOGL", 1), ("MSFT", 2)]:
            sym_notes = []
            for _ in range(20):
                msgs = engine.process(_make_event(sym))
                note_ons = [m for m in msgs if m.type == "note_on"]
                sym_notes.extend(m for m in note_ons if m.channel == expected_ch)
            assert len(sym_notes) > 0, f"{sym} should produce notes on channel {expected_ch}"

    def test_no_drums(self):
        engine = _make_engine()
        for _ in range(20):
            msgs = engine.process(_make_event("AAPL", density=0.9))
            for m in msgs:
                if m.type == "note_on":
                    assert m.channel != 9, "Ambient engine should never produce drums"

    def test_notes_in_scale(self):
        engine = _make_engine(key="C", scale="dorian")
        scale_pcs = set(get_scale_notes("C", "dorian"))
        for _ in range(20):
            msgs = engine.process(_make_event("AAPL"))
            for m in msgs:
                if m.type == "note_on" and m.channel in (0, 1, 2):
                    assert m.note % 12 in scale_pcs, (
                        f"Note {m.note} (pc={m.note % 12}) not in C dorian"
                    )

    def test_velocity_in_ambient_range(self):
        engine = _make_engine()
        for _ in range(20):
            msgs = engine.process(_make_event("AAPL"))
            for m in msgs:
                if m.type == "note_on":
                    assert 1 <= m.velocity <= 80, f"Velocity {m.velocity} outside ambient range"

    def test_atmosphere_fires_periodically(self):
        engine = _make_engine()
        atm_notes = []
        for i in range(8):
            msgs = engine.process(_make_event("AAPL"))
            for m in msgs:
                if m.type == "note_on" and m.channel == 3:
                    atm_notes.append(m)
        # Atmosphere fires every 4th tick, so in 8 ticks we should get some
        assert len(atm_notes) > 0, "Atmosphere channel should fire periodically"

    def test_set_key_changes_notes(self):
        engine = _make_engine(key="C", scale="dorian")
        engine.set_key("A", "minor")
        a_minor_pcs = set(get_scale_notes("A", "minor"))
        for _ in range(10):
            msgs = engine.process(_make_event("AAPL"))
            for m in msgs:
                if m.type == "note_on" and m.channel == 0:
                    assert m.note % 12 in a_minor_pcs


class TestChordStockEngine:
    def _make_chord_engine(self, symbols=None, key="C", scale="dorian"):
        from data_to_midi.engine.ambient_engine import ChordStockEngine
        symbols = symbols or ["AAPL", "GOOGL", "MSFT"]
        config = EngineConfig(
            bpm=75, key=key, scale=scale, mode="chord_stock",
            velocity_range=[25, 65],
            channels={
                "chord": ChannelConfig(0, 89),
                "bass": ChannelConfig(1, 39),
                "atmosphere": ChannelConfig(2, 92),
            },
        )
        return ChordStockEngine(config, symbols)

    def test_produces_chords_after_warmup(self):
        engine = self._make_chord_engine()
        all_msgs = []
        # Feed all 3 symbols to build up features, then keep ticking
        for _ in range(30):
            for sym in ["AAPL", "GOOGL", "MSFT"]:
                msgs = engine.process(_make_event(sym, pitch=0.3 + 0.2 * ["AAPL", "GOOGL", "MSFT"].index(sym)))
                all_msgs.extend(msgs)
        note_ons = [m for m in all_msgs if m.type == "note_on"]
        assert len(note_ons) > 0, "Chord engine should produce notes"

    def test_notes_in_scale(self):
        engine = self._make_chord_engine(key="C", scale="dorian")
        scale_pcs = set(get_scale_notes("C", "dorian"))
        all_msgs = []
        for _ in range(30):
            for sym in ["AAPL", "GOOGL", "MSFT"]:
                all_msgs.extend(engine.process(_make_event(sym)))
        for m in all_msgs:
            if m.type == "note_on":
                assert m.note % 12 in scale_pcs, f"Note {m.note} not in C dorian"

    def test_no_drums(self):
        engine = self._make_chord_engine()
        for _ in range(30):
            for sym in ["AAPL", "GOOGL", "MSFT"]:
                msgs = engine.process(_make_event(sym))
                for m in msgs:
                    if m.type == "note_on":
                        assert m.channel != 9, "Chord engine should never use drums"

    def test_chord_uses_single_channel(self):
        """Main chord voices should all be on the chord channel (0)."""
        engine = self._make_chord_engine()
        chord_notes = []
        for _ in range(30):
            for sym in ["AAPL", "GOOGL", "MSFT"]:
                msgs = engine.process(_make_event(sym))
                for m in msgs:
                    if m.type == "note_on" and m.channel == 0:
                        chord_notes.append(m)
        assert len(chord_notes) > 0, "Should produce chord notes on channel 0"


class TestMultiSymbolPerceptor:
    def test_routes_by_symbol(self):
        from data_to_midi.config import PerceptionConfig
        from data_to_midi.perception.multi_symbol import MultiSymbolPerceptor
        from data_to_midi.sources.base import SourceSample

        perc = MultiSymbolPerceptor(PerceptionConfig(window_size=5), ["AAPL", "GOOGL"])

        # Feed 5 samples for AAPL
        for i in range(5):
            result = perc.update(SourceSample(
                timestamp=float(i), values={"price": 100.0 + i},
                metadata={"symbol": "AAPL"},
            ))
        assert result is not None
        assert result.symbol == "AAPL"

        # GOOGL should still be None (not enough data)
        result2 = perc.update(SourceSample(
            timestamp=6.0, values={"price": 200.0},
            metadata={"symbol": "GOOGL"},
        ))
        assert result2 is None

    def test_price_history_tracked(self):
        from data_to_midi.config import PerceptionConfig
        from data_to_midi.perception.multi_symbol import MultiSymbolPerceptor
        from data_to_midi.sources.base import SourceSample

        perc = MultiSymbolPerceptor(PerceptionConfig(window_size=5), ["AAPL"])
        perc.update(SourceSample(
            timestamp=1.0, values={"price": 150.0},
            metadata={"symbol": "AAPL"},
        ))

        latest = perc.get_latest_prices()
        assert "AAPL" in latest
        assert latest["AAPL"] == (1.0, 150.0)

    def test_unknown_symbol_ignored(self):
        from data_to_midi.config import PerceptionConfig
        from data_to_midi.perception.multi_symbol import MultiSymbolPerceptor
        from data_to_midi.sources.base import SourceSample

        perc = MultiSymbolPerceptor(PerceptionConfig(window_size=5), ["AAPL"])
        result = perc.update(SourceSample(
            timestamp=1.0, values={"price": 100.0},
            metadata={"symbol": "UNKNOWN"},
        ))
        assert result is None
