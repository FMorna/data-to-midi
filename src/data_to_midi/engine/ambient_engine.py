from __future__ import annotations

"""Ambient stock engine: drone/pad instruments, one per symbol, no drums."""

import random
from collections import deque

import mido
import numpy as np

from ..config import ChannelConfig, EngineConfig
from ..mapping.musical_params import MusicalEvent
from ..perception.features import FeatureVector
from .base import BaseMusicEngine
from .sequencer import Sequencer
from .theory import build_chord, get_scale_notes, quantize_to_scale


# Default ambient instrument assignments
DEFAULT_SYMBOL_PROGRAMS = [
    ChannelConfig(channel=0, program=89),  # Warm Pad — sustained, lush
    ChannelConfig(channel=1, program=51),  # Synth Strings — wide, evolving
    ChannelConfig(channel=2, program=39),  # Synth Bass — deep foundation
]
ATMOSPHERE_CHANNEL = ChannelConfig(channel=3, program=92)  # Spacey Pad — background wash

MAX_CONCURRENT_NOTES = 20


class AmbientStockEngine(BaseMusicEngine):
    """Ambient/drone engine for stock market mode.

    Each symbol maps to a separate instrument channel.
    Produces sustained, overlapping notes with breathing room.
    Musical decisions are driven by market data but filtered through
    probability gates and voice leading for a harmonious result.
    """

    def __init__(self, config: EngineConfig, symbols: list = None):
        self.config = config
        self.root = config.key
        self.scale = config.scale
        self.vel_lo, self.vel_hi = config.velocity_range

        self.sequencer = Sequencer(
            bpm=config.bpm,
            beats_per_bar=config.time_signature[0],
            root=self.root,
            scale=self.scale,
        )

        # Map symbol names to channel configs
        symbols = symbols or []
        self._symbol_order = list(symbols)
        self._symbol_channels: dict = {}
        for i, sym in enumerate(symbols[:3]):
            if i < len(DEFAULT_SYMBOL_PROGRAMS):
                self._symbol_channels[sym] = DEFAULT_SYMBOL_PROGRAMS[i]

        self._atmosphere = ATMOSPHERE_CHANNEL

        # Override from config if provided
        channel_configs = list(config.channels.values())
        for i, sym in enumerate(symbols[:3]):
            if i < len(channel_configs):
                self._symbol_channels[sym] = channel_configs[i]
        if len(channel_configs) > 3:
            self._atmosphere = channel_configs[3]

        # State
        self._last_notes: dict = {}  # channel -> last note
        self._active_notes: deque = deque()  # (channel, note, remaining_beats)
        self._latest_features: dict = {}  # symbol -> MusicalEvent
        self._tick_count = 0
        self._last_play_tick: dict = {}  # symbol -> last tick that produced a note

        # Mood tracking
        self._direction_history: deque = deque(maxlen=16)
        self._volatility_history: deque = deque(maxlen=16)

    @property
    def channels(self) -> dict:
        """Return all channel configs for program setup."""
        result = {}
        for sym, cfg in self._symbol_channels.items():
            result[sym] = cfg
        result["atmosphere"] = self._atmosphere
        return result

    def set_key(self, root: str, scale: str) -> None:
        self.root = root
        self.scale = scale
        self.sequencer.set_key(root, scale)

    def set_tempo(self, bpm: float) -> None:
        self.sequencer.set_tempo(bpm)

    def feed_mood(self, direction: float, volatility: float) -> None:
        self._direction_history.append(direction)
        self._volatility_history.append(volatility)

    def _should_play(self, event: MusicalEvent, symbol: str) -> bool:
        """Probability gate: decide whether this tick produces a note.

        Higher volatility/urgency → more likely to play.
        Ensures minimum spacing between notes for breathing room.
        """
        # Minimum 2 ticks between notes per symbol (breathing room)
        last = self._last_play_tick.get(symbol, -10)
        if self._tick_count - last < 2:
            return False

        # Base probability: 40-75% depending on urgency + volatility
        base_prob = 0.40 + event.urgency * 0.20 + event.velocity * 0.15
        # Downbeat bias: slightly more likely to play on beat 1
        if self.sequencer.current_beat == 0:
            base_prob += 0.10

        return random.random() < base_prob

    def process(self, event: MusicalEvent) -> list:
        messages = []
        self._tick_count += 1

        # Store latest features per symbol
        if event.symbol:
            self._latest_features[event.symbol] = event

        # Advance sequencer (once per tick)
        timing = self.sequencer.tick()

        # Release expired notes
        messages.extend(self._release_expired_notes())

        # Enforce max concurrent notes — fade out oldest gracefully
        while len(self._active_notes) > MAX_CONCURRENT_NOTES:
            ch, note, _ = self._active_notes.popleft()
            messages.append(mido.Message("note_off", channel=ch, note=note, velocity=0))

        # Very gentle tempo drift: ±3 BPM max
        target_bpm = self.config.bpm + (event.urgency - 0.5) * 6
        smoothed = self.sequencer.bpm * 0.97 + target_bpm * 0.03
        self.sequencer.set_tempo(smoothed)

        # Auto-progression every 16 ticks
        if self.config.auto_key_change and self._tick_count % 16 == 0:
            self._update_mood_progression()

        # --- Per-symbol instrument (with probability gate) ---
        sym_ch_config = self._symbol_channels.get(event.symbol)
        if sym_ch_config and self._should_play(event, event.symbol):
            ch = sym_ch_config.channel

            # Compute the note first, then decide whether to play
            note = self._compute_ambient_note(event, timing, ch)

            # Skip if same note as last — let the previous one sustain
            if note == self._last_notes.get(ch):
                pass  # no new note, existing one keeps ringing
            else:
                self._last_play_tick[event.symbol] = self._tick_count

                # Velocity — soft, narrow range for evenness
                velocity = int(self.vel_lo + event.velocity * (self.vel_hi - self.vel_lo))
                velocity = max(1, min(127, velocity))

                # Long sustain: 4-16 beats so notes overlap and blend
                beat_dur = self.sequencer.beat_duration
                duration_beats = 4 + event.duration_hint * 12
                note_duration = duration_beats * beat_dur

                messages.append(
                    mido.Message("note_on", channel=ch, note=note, velocity=velocity)
                )
                self._active_notes.append((ch, note, note_duration))
                self._last_notes[ch] = note

                # Harmonic interval: sometimes add a 3rd, 5th, or octave
                # Higher density_hint or downbeat → more likely to add harmony
                harmony_prob = 0.25 + event.density_hint * 0.25
                if timing["is_downbeat"]:
                    harmony_prob += 0.15
                if random.random() < harmony_prob:
                    interval = random.choice([3, 4, 5, 7])  # minor 3rd, major 3rd, 4th, 5th
                    harm_note = quantize_to_scale(note + interval, self.root, self.scale)
                    harm_note = max(36, min(84, harm_note))
                    harm_vel = max(1, int(velocity * 0.6))  # softer than main note
                    messages.append(
                        mido.Message("note_on", channel=ch, note=harm_note, velocity=harm_vel)
                    )
                    self._active_notes.append((ch, harm_note, note_duration * 0.75))

        # --- Atmosphere pad (every 6th tick — slower, more spacious) ---
        if self._tick_count % 6 == 0 and len(self._latest_features) > 0:
            atm_ch = self._atmosphere.channel
            # Very soft atmosphere
            avg_vel = sum(
                e.velocity for e in self._latest_features.values()
            ) / len(self._latest_features)
            atm_vel = max(1, min(60, int(self.vel_lo + avg_vel * (self.vel_hi - self.vel_lo) * 0.35)))

            beat_dur = self.sequencer.beat_duration
            atm_duration = beat_dur * 12  # long wash

            chord_notes = build_chord(timing["chord_root"] + 12, timing["chord_quality"])
            for cn in chord_notes:
                cn = quantize_to_scale(cn, self.root, self.scale)
                cn = max(48, min(78, cn))  # keep atmosphere in mid-range
                messages.append(
                    mido.Message("note_on", channel=atm_ch, note=cn, velocity=atm_vel)
                )
                self._active_notes.append((atm_ch, cn, atm_duration))

        return messages

    def _compute_ambient_note(self, event: MusicalEvent, timing: dict, channel: int) -> int:
        """Compute a drone-appropriate note with slow voice leading."""
        scale_notes = get_scale_notes(self.root, self.scale)

        # Map pitch_hint to scale degree
        degree_idx = int(event.pitch_hint * (len(scale_notes) - 1))
        degree_idx = max(0, min(len(scale_notes) - 1, degree_idx))
        pitch_class = scale_notes[degree_idx]

        # Register: spread symbols across octaves for width
        # Channel 0 (pad) → octave 3-4, Channel 1 (strings) → octave 3-5, Channel 2 (bass) → octave 2-3
        base_octave = max(2, 4 - channel)
        octave = base_octave + int(event.register_hint * 1.5)
        octave = max(2, min(5, octave))
        target_note = octave * 12 + pitch_class

        # Very gentle voice leading — prefer stepwise motion (max 2-4 semitones)
        last = self._last_notes.get(channel)
        if last is not None:
            max_interval = 2 + int(event.urgency * 2)  # 2-4 semitones max
            diff = target_note - last
            if abs(diff) > max_interval:
                direction = 1 if diff > 0 else -1
                step = random.choice([1, 2]) * direction
                target_note = last + step
                target_note = quantize_to_scale(target_note, self.root, self.scale)

        # Strong chord-tone bias for consonance
        chord_notes = build_chord(timing["chord_root"], timing["chord_quality"])
        chord_pcs = set(n % 12 for n in chord_notes)
        scale_pcs = set(get_scale_notes(self.root, self.scale))
        valid_chord = [pc for pc in chord_pcs if pc in scale_pcs]
        if valid_chord and target_note % 12 not in valid_chord and random.random() < 0.75:
            best = min(valid_chord, key=lambda pc: abs((target_note % 12) - pc))
            target_note = (target_note // 12) * 12 + best

        target_note = quantize_to_scale(target_note, self.root, self.scale)
        return max(24, min(84, target_note))

    def _release_expired_notes(self) -> list:
        messages = []
        remaining = deque()
        beat_dur = self.sequencer.beat_duration
        for ch, note, duration in self._active_notes:
            if duration <= 0:
                messages.append(
                    mido.Message("note_off", channel=ch, note=note, velocity=0)
                )
            else:
                remaining.append((ch, note, duration - beat_dur))
        self._active_notes = remaining
        return messages

    def _update_mood_progression(self) -> None:
        if not self._direction_history:
            return
        avg_dir = float(np.mean(list(self._direction_history)))
        avg_vol = float(np.mean(list(self._volatility_history)))
        self.sequencer.select_progression_by_mood(avg_dir, avg_vol)


# --- Chord mode defaults ---
CHORD_CHANNEL = ChannelConfig(channel=0, program=89)       # Warm Pad for unified chord
CHORD_BASS_CHANNEL = ChannelConfig(channel=1, program=39)  # Synth Bass — root note
CHORD_ATM_CHANNEL = ChannelConfig(channel=2, program=92)   # Spacey Pad — atmosphere


class ChordStockEngine(BaseMusicEngine):
    """Chord engine: fuses all symbols into one 3-note chord per tick.

    Each symbol contributes one voice to a unified chord played on a single
    pad instrument. The result is inherently harmonious — every tick is a
    proper chord shaped by market data.
    """

    def __init__(self, config: EngineConfig, symbols: list = None):
        self.config = config
        self.root = config.key
        self.scale = config.scale
        self.vel_lo, self.vel_hi = config.velocity_range

        self.sequencer = Sequencer(
            bpm=config.bpm,
            beats_per_bar=config.time_signature[0],
            root=self.root,
            scale=self.scale,
        )

        symbols = symbols or []
        self._symbol_order = list(symbols)

        # Channel configs — overridable from config
        self._chord_ch = CHORD_CHANNEL
        self._bass_ch = CHORD_BASS_CHANNEL
        self._atm_ch = CHORD_ATM_CHANNEL
        channel_configs = list(config.channels.values())
        if len(channel_configs) > 0:
            self._chord_ch = channel_configs[0]
        if len(channel_configs) > 1:
            self._bass_ch = channel_configs[1]
        if len(channel_configs) > 2:
            self._atm_ch = channel_configs[2]

        # State
        self._latest_features: dict = {}  # symbol -> MusicalEvent
        self._active_notes: deque = deque()
        self._last_chord: tuple = ()  # last chord as sorted tuple of MIDI notes
        self._last_bass: int = -1
        self._tick_count = 0
        self._last_play_tick = 0

        # Mood tracking
        self._direction_history: deque = deque(maxlen=16)
        self._volatility_history: deque = deque(maxlen=16)

    @property
    def channels(self) -> dict:
        return {
            "chord": self._chord_ch,
            "bass": self._bass_ch,
            "atmosphere": self._atm_ch,
        }

    def set_key(self, root: str, scale: str) -> None:
        self.root = root
        self.scale = scale
        self.sequencer.set_key(root, scale)

    def set_tempo(self, bpm: float) -> None:
        self.sequencer.set_tempo(bpm)

    def feed_mood(self, direction: float, volatility: float) -> None:
        self._direction_history.append(direction)
        self._volatility_history.append(volatility)

    def process(self, event: MusicalEvent) -> list:
        messages = []
        self._tick_count += 1

        # Accumulate latest data per symbol
        if event.symbol:
            self._latest_features[event.symbol] = event

        timing = self.sequencer.tick()
        messages.extend(self._release_expired_notes())

        # Cap concurrent notes
        while len(self._active_notes) > 16:
            ch, note, _ = self._active_notes.popleft()
            messages.append(mido.Message("note_off", channel=ch, note=note, velocity=0))

        # Gentle tempo drift
        target_bpm = self.config.bpm + (event.urgency - 0.5) * 6
        self.sequencer.set_tempo(self.sequencer.bpm * 0.97 + target_bpm * 0.03)

        # Auto-progression
        if self.config.auto_key_change and self._tick_count % 16 == 0:
            self._update_mood_progression()

        # Need at least 2 symbols' data to build a chord
        if len(self._latest_features) < 2:
            return messages

        avg_urgency = sum(e.urgency for e in self._latest_features.values()) / len(self._latest_features)
        avg_vel = sum(e.velocity for e in self._latest_features.values()) / len(self._latest_features)

        # Probability gate: 65-90% — higher than ambient to keep chords flowing
        ticks_since = self._tick_count - self._last_play_tick
        play_prob = 0.65 + avg_urgency * 0.15 + avg_vel * 0.10
        if timing["is_downbeat"]:
            play_prob += 0.10
        # If it's been a while (4+ ticks), force play to avoid silence gaps
        if ticks_since >= 4:
            play_prob = 1.0
        if random.random() > play_prob:
            return messages

        # --- Build chord from all symbols' pitch hints ---
        scale_notes = get_scale_notes(self.root, self.scale)
        chord_pcs = build_chord(timing["chord_root"], timing["chord_quality"])
        chord_pc_set = set(n % 12 for n in chord_pcs)

        voices = []
        for i, sym in enumerate(self._symbol_order):
            feat = self._latest_features.get(sym)
            if feat is None:
                continue

            # Each symbol's pitch_hint selects a scale degree
            degree_idx = int(feat.pitch_hint * (len(scale_notes) - 1))
            degree_idx = max(0, min(len(scale_notes) - 1, degree_idx))
            pc = scale_notes[degree_idx]

            # Bias toward chord tones for consonance
            valid_chord = [p for p in chord_pc_set if p in set(scale_notes)]
            if valid_chord and pc not in valid_chord and random.random() < 0.7:
                pc = min(valid_chord, key=lambda p: abs(pc - p))

            # Spread voices: voice 0 → octave 4, voice 1 → octave 4, voice 2 → octave 3
            octave = 4 if i < 2 else 3
            # Shift by register_hint for slight variation
            octave += int(feat.register_hint * 0.8)
            octave = max(3, min(5, octave))
            note = octave * 12 + pc
            note = quantize_to_scale(note, self.root, self.scale)
            note = max(48, min(84, note))
            voices.append(note)

        if not voices:
            return messages

        # Sort and deduplicate, ensure proper voicing (no clusters)
        voices = sorted(set(voices))
        # If we have 3+ voices crammed within 3 semitones, spread them
        if len(voices) >= 2:
            for i in range(1, len(voices)):
                if voices[i] - voices[i - 1] < 3:
                    voices[i] = quantize_to_scale(voices[i] + 3, self.root, self.scale)
            voices = sorted(set(voices))

        chord_tuple = tuple(voices)

        # Don't repeat identical chord unless it's been 6+ ticks (avoid silence)
        if chord_tuple == self._last_chord and ticks_since < 6:
            return messages

        self._last_play_tick = self._tick_count
        self._last_chord = chord_tuple

        # Velocity from average of all symbols
        velocity = int(self.vel_lo + avg_vel * (self.vel_hi - self.vel_lo))
        velocity = max(1, min(127, velocity))

        # Duration: 6-16 beats
        avg_dur = sum(e.duration_hint for e in self._latest_features.values()) / len(self._latest_features)
        beat_dur = self.sequencer.beat_duration
        duration = (6 + avg_dur * 10) * beat_dur

        # Play the chord on the pad channel
        ch = self._chord_ch.channel
        for note in voices:
            messages.append(mido.Message("note_on", channel=ch, note=note, velocity=velocity))
            self._active_notes.append((ch, note, duration))

        # Bass note: root of the chord (lowest voice dropped an octave)
        bass_note = min(voices) - 12
        bass_note = quantize_to_scale(bass_note, self.root, self.scale)
        bass_note = max(28, min(60, bass_note))
        if bass_note != self._last_bass:
            bass_ch = self._bass_ch.channel
            bass_vel = max(1, int(velocity * 0.5))
            messages.append(mido.Message("note_on", channel=bass_ch, note=bass_note, velocity=bass_vel))
            self._active_notes.append((bass_ch, bass_note, duration * 1.5))
            self._last_bass = bass_note

        # Atmosphere: every 8th tick, very soft progression chord
        if self._tick_count % 8 == 0:
            atm_ch = self._atm_ch.channel
            atm_vel = max(1, int(velocity * 0.25))
            prog_notes = build_chord(timing["chord_root"] + 24, timing["chord_quality"])
            for cn in prog_notes:
                cn = quantize_to_scale(cn, self.root, self.scale)
                cn = max(60, min(84, cn))
                messages.append(mido.Message("note_on", channel=atm_ch, note=cn, velocity=atm_vel))
                self._active_notes.append((atm_ch, cn, duration * 2))

        return messages

    def _release_expired_notes(self) -> list:
        messages = []
        remaining = deque()
        beat_dur = self.sequencer.beat_duration
        for ch, note, duration in self._active_notes:
            if duration <= 0:
                messages.append(mido.Message("note_off", channel=ch, note=note, velocity=0))
            else:
                remaining.append((ch, note, duration - beat_dur))
        self._active_notes = remaining
        return messages

    def _update_mood_progression(self) -> None:
        if not self._direction_history:
            return
        avg_dir = float(np.mean(list(self._direction_history)))
        avg_vol = float(np.mean(list(self._volatility_history)))
        self.sequencer.select_progression_by_mood(avg_dir, avg_vol)
