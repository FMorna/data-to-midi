from __future__ import annotations

"""Music engine: transforms MusicalEvents into MIDI messages with musical structure."""

import random
from collections import deque

import mido

from ..config import EngineConfig
from ..mapping.musical_params import MusicalEvent
from .base import BaseMusicEngine
from .sequencer import Sequencer
from .theory import build_chord, get_scale_notes, quantize_to_scale


class MusicEngine(BaseMusicEngine):
    """Enforces musical structure: scale quantization, voice leading, chords, timing."""

    def __init__(self, config: EngineConfig | None = None):
        config = config or EngineConfig()
        self.config = config
        self.root = config.key
        self.scale = config.scale
        self.vel_lo, self.vel_hi = config.velocity_range
        self.channels = config.channels

        self.sequencer = Sequencer(
            bpm=config.bpm,
            beats_per_bar=config.time_signature[0],
            root=self.root,
            scale=self.scale,
        )

        # Voice leading state: last notes per channel
        self._last_notes: dict[int, int] = {}
        # Track active notes for proper note-off
        self._active_notes: deque[tuple[int, int, float]] = deque()  # (channel, note, off_time)

        # Mood tracking for auto-progression
        self._direction_history: deque[float] = deque(maxlen=16)
        self._volatility_history: deque[float] = deque(maxlen=16)
        self._event_count = 0

    def set_key(self, root: str, scale: str) -> None:
        self.root = root
        self.scale = scale
        self.sequencer.set_key(root, scale)

    def set_tempo(self, bpm: float) -> None:
        self.sequencer.set_tempo(bpm)

    def process(self, event: MusicalEvent) -> list[mido.Message]:
        """Process a MusicalEvent into MIDI messages."""
        messages = []
        self._event_count += 1

        # Advance sequencer
        timing = self.sequencer.tick()

        # Release expired notes
        messages.extend(self._release_expired_notes())

        # Tempo micro-adjustment based on urgency
        target_bpm = self.config.bpm + (event.urgency - 0.5) * 30
        current_bpm = self.sequencer.bpm
        smoothed_bpm = current_bpm * 0.9 + target_bpm * 0.1
        self.sequencer.set_tempo(smoothed_bpm)

        # Auto-progression every 16 events
        if self.config.auto_key_change and self._event_count % 16 == 0:
            self._update_mood_progression()

        # Compute MIDI velocity
        velocity = int(self.vel_lo + event.velocity * (self.vel_hi - self.vel_lo))
        velocity = max(1, min(127, velocity))

        note_duration = self.sequencer.get_note_duration(event.duration_hint)

        # --- Melody (channel 0) ---
        melody_ch = self.channels.get("melody")
        if melody_ch:
            ch = melody_ch.channel
            note = self._compute_melody_note(event, timing)
            messages.append(mido.Message("note_on", channel=ch, note=note, velocity=velocity))
            self._active_notes.append((ch, note, note_duration))
            self._last_notes[ch] = note

        # --- Bass (channel 1) ---
        bass_ch = self.channels.get("bass")
        if bass_ch:
            ch = bass_ch.channel
            bass_note = timing["chord_root"]
            bass_note = quantize_to_scale(bass_note, self.root, self.scale)
            bass_vel = max(1, min(127, int(velocity * 0.7)))
            messages.append(
                mido.Message("note_on", channel=ch, note=bass_note, velocity=bass_vel)
            )
            self._active_notes.append((ch, bass_note, note_duration * 2))
            self._last_notes[ch] = bass_note

        # --- Pad/Harmony (channel 2) — only on downbeats or high density ---
        pad_ch = self.channels.get("pad")
        if pad_ch and (timing["is_downbeat"] or event.density_hint > 0.6):
            ch = pad_ch.channel
            chord_notes = build_chord(timing["chord_root"] + 12, timing["chord_quality"])
            pad_vel = max(1, min(127, int(velocity * 0.5)))
            for cn in chord_notes:
                cn = quantize_to_scale(cn, self.root, self.scale)
                messages.append(
                    mido.Message("note_on", channel=ch, note=cn, velocity=pad_vel)
                )
                self._active_notes.append((ch, cn, note_duration * 4))

        # --- Drums (channel 9) — driven by density ---
        drums_ch = self.channels.get("drums")
        if drums_ch and event.density_hint > 0.3:
            ch = drums_ch.channel
            drum_vel = max(1, min(127, int(velocity * 0.6)))
            # Kick on downbeats, hi-hat on all, snare on 2 and 4
            if timing["is_downbeat"]:
                messages.append(
                    mido.Message("note_on", channel=ch, note=36, velocity=drum_vel)
                )
                self._active_notes.append((ch, 36, 0.1))
            if timing["beat"] in (1, 3):
                messages.append(
                    mido.Message("note_on", channel=ch, note=38, velocity=drum_vel)
                )
                self._active_notes.append((ch, 38, 0.1))
            # Hi-hat
            messages.append(
                mido.Message("note_on", channel=ch, note=42, velocity=int(drum_vel * 0.7))
            )
            self._active_notes.append((ch, 42, 0.05))

        return messages

    def _compute_melody_note(self, event: MusicalEvent, timing: dict) -> int:
        """Compute a melody note with voice leading."""
        scale_notes = get_scale_notes(self.root, self.scale)

        # Map pitch_hint to a scale degree
        degree_idx = int(event.pitch_hint * (len(scale_notes) - 1))
        degree_idx = max(0, min(len(scale_notes) - 1, degree_idx))
        pitch_class = scale_notes[degree_idx]

        # Map register_hint to octave (3-6)
        octave = int(3 + event.register_hint * 3)
        octave = max(3, min(6, octave))
        target_note = octave * 12 + pitch_class

        # Voice leading: prefer small intervals from last note
        melody_ch = self.channels.get("melody")
        ch = melody_ch.channel if melody_ch else 0
        last = self._last_notes.get(ch)
        if last is not None:
            # Allow wider leaps when urgency is high
            max_interval = 4 + int(event.urgency * 8)  # 4-12 semitones
            diff = target_note - last
            if abs(diff) > max_interval:
                # Step toward target instead of leaping
                direction = 1 if diff > 0 else -1
                step = random.choice([1, 2, 3]) * direction
                target_note = last + step
                target_note = quantize_to_scale(target_note, self.root, self.scale)

        # Bias toward chord tones on strong beats
        if timing["is_downbeat"]:
            chord_notes = build_chord(timing["chord_root"], timing["chord_quality"])
            chord_pcs = [n % 12 for n in chord_notes]
            # Only snap to chord tones that are also in the scale
            scale_pcs = set(get_scale_notes(self.root, self.scale))
            valid_chord_pcs = [pc for pc in chord_pcs if pc in scale_pcs]
            if valid_chord_pcs and target_note % 12 not in valid_chord_pcs:
                best = min(valid_chord_pcs, key=lambda pc: abs((target_note % 12) - pc))
                target_note = (target_note // 12) * 12 + best

        # Final safety: ensure note is in scale
        target_note = quantize_to_scale(target_note, self.root, self.scale)

        return max(36, min(96, target_note))

    def _release_expired_notes(self) -> list[mido.Message]:
        """Generate note-off messages for expired notes."""
        messages = []
        remaining = deque()
        for ch, note, duration in self._active_notes:
            if duration <= 0:
                messages.append(
                    mido.Message("note_off", channel=ch, note=note, velocity=0)
                )
            else:
                # Decrement duration by one beat
                remaining.append((ch, note, duration - self.sequencer.beat_duration))
        self._active_notes = remaining
        return messages

    def _update_mood_progression(self) -> None:
        """Update chord progression based on recent mood."""
        if not self._direction_history:
            return
        import numpy as np

        avg_dir = float(np.mean(list(self._direction_history)))
        avg_vol = float(np.mean(list(self._volatility_history)))
        self.sequencer.select_progression_by_mood(avg_dir, avg_vol)

    def feed_mood(self, direction: float, volatility: float) -> None:
        """Feed mood data from the perception layer for auto-progression."""
        self._direction_history.append(direction)
        self._volatility_history.append(volatility)
