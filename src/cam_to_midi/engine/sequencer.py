from __future__ import annotations

"""Timing grid: BPM clock, beat tracking, bar structure, chord progression."""

import time

from .theory import resolve_progression


class Sequencer:
    """Maintains musical time: beat position, bar number, current chord."""

    def __init__(
        self,
        bpm: float = 120,
        beats_per_bar: int = 4,
        root: str = "C",
        scale: str = "major",
    ):
        self.bpm = bpm
        self.beats_per_bar = beats_per_bar
        self.root = root
        self.scale = scale

        self._start_time = time.time()
        self._beat_count = 0
        self._bar_count = 0

        # Default progression
        self._progression_names = ["I", "V", "vi", "IV"]
        self._resolved_progression = resolve_progression(
            self._progression_names, root, scale
        )
        self._chord_index = 0

    @property
    def beat_duration(self) -> float:
        """Duration of one beat in seconds."""
        return 60.0 / self.bpm

    @property
    def bar_duration(self) -> float:
        return self.beat_duration * self.beats_per_bar

    @property
    def current_beat(self) -> int:
        """Current beat within the bar (0-indexed)."""
        return self._beat_count % self.beats_per_bar

    @property
    def current_bar(self) -> int:
        return self._bar_count

    @property
    def current_chord(self) -> tuple[int, str]:
        """Current (root_midi_note, quality) from the progression."""
        if not self._resolved_progression:
            return (48, "major")
        return self._resolved_progression[self._chord_index]

    def set_progression(self, progression: list[str]) -> None:
        self._progression_names = progression
        self._resolved_progression = resolve_progression(
            progression, self.root, self.scale
        )
        self._chord_index = 0

    def set_key(self, root: str, scale: str) -> None:
        self.root = root
        self.scale = scale
        self._resolved_progression = resolve_progression(
            self._progression_names, root, scale
        )

    def set_tempo(self, bpm: float) -> None:
        self.bpm = max(60.0, min(180.0, bpm))

    def tick(self) -> dict:
        """Advance the sequencer by one beat. Returns timing context."""
        beat_in_bar = self.current_beat
        is_downbeat = beat_in_bar == 0
        chord = self.current_chord

        self._beat_count += 1

        # Advance chord on new bar
        if self._beat_count % self.beats_per_bar == 0:
            self._bar_count += 1
            if self._resolved_progression:
                self._chord_index = (
                    self._chord_index + 1
                ) % len(self._resolved_progression)

        return {
            "beat": beat_in_bar,
            "bar": self._bar_count,
            "is_downbeat": is_downbeat,
            "chord_root": chord[0],
            "chord_quality": chord[1],
            "beat_duration": self.beat_duration,
        }

    def get_note_duration(self, duration_hint: float) -> float:
        """Convert a duration hint [0,1] to seconds.

        0.0 -> sixteenth note, 0.5 -> eighth note, 1.0 -> half note
        """
        beat = self.beat_duration
        if duration_hint < 0.25:
            return beat * 0.25  # Sixteenth
        elif duration_hint < 0.5:
            return beat * 0.5  # Eighth
        elif duration_hint < 0.75:
            return beat  # Quarter
        else:
            return beat * 2.0  # Half note

    def select_progression_by_mood(self, avg_direction: float, avg_volatility: float) -> None:
        """Auto-select chord progression based on perceived mood."""
        if avg_volatility > 0.7:
            prog = ["i", "iv", "V", "i"]  # dramatic
        elif avg_direction < -0.3:
            prog = ["vi", "IV", "I", "V"]  # melancholic
        elif avg_direction > 0.3:
            prog = ["I", "IV", "V", "V"]  # rising
        else:
            prog = ["I", "V", "vi", "IV"]  # calm
        self.set_progression(prog)
