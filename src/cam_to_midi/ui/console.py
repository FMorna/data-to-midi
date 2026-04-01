from __future__ import annotations

"""Rich-based live terminal dashboard showing features, notes, and status."""

from collections import deque

from ..mapping.musical_params import MusicalEvent
from ..perception.features import FeatureVector


class ConsoleDashboard:
    """Live terminal display of pipeline state."""

    def __init__(self, max_history: int = 20):
        self._history: deque[str] = deque(maxlen=max_history)
        self._event_count = 0
        self._console = None
        self._live = None
        self._setup()

    def _setup(self) -> None:
        try:
            from rich.console import Console

            self._console = Console()
        except ImportError:
            pass

    def update(self, features: FeatureVector, event: MusicalEvent, messages: list) -> None:
        self._event_count += 1
        if self._console is None:
            return

        # Format feature bars
        bars = self._format_features(features)

        # Format MIDI activity
        note_names = []
        for msg in messages:
            if msg.type == "note_on" and msg.velocity > 0:
                name = _midi_to_name(msg.note)
                note_names.append(f"ch{msg.channel}:{name}")

        notes_str = " ".join(note_names[:8]) if note_names else "---"
        self._history.append(notes_str)

        # Print update
        if self._event_count % 4 == 0:  # Throttle output
            self._console.clear()
            self._console.print(f"[bold cyan]cam_to_midi[/] | tick #{self._event_count}")
            self._console.print()
            self._console.print(bars)
            self._console.print()
            self._console.print("[bold]Recent notes:[/]")
            for line in list(self._history)[-8:]:
                self._console.print(f"  {line}")

    def _format_features(self, f: FeatureVector) -> str:
        lines = []
        features = [
            ("change_rate", f.change_rate, -1, 1),
            ("periodicity", f.periodicity, 0, 1),
            ("intensity  ", f.intensity, 0, 1),
            ("direction  ", f.direction, -1, 1),
            ("volatility ", f.volatility, 0, 1),
            ("density    ", f.density, 0, 1),
        ]
        for name, val, lo, hi in features:
            normalized = (val - lo) / (hi - lo) if hi != lo else 0.5
            bar_len = int(normalized * 30)
            bar = "#" * bar_len + "." * (30 - bar_len)
            lines.append(f"  {name} [{bar}] {val:+.2f}")
        return "\n".join(lines)


NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _midi_to_name(note: int) -> str:
    octave = note // 12 - 1
    name = NOTE_NAMES[note % 12]
    return f"{name}{octave}"
