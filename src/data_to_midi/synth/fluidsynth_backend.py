from __future__ import annotations

"""FluidSynth backend for high-quality audio output using SoundFont files."""

from pathlib import Path

import mido

from .base import BaseSynth


class FluidSynthBackend(BaseSynth):
    """Renders MIDI to audio using FluidSynth and a SoundFont (.sf2) file."""

    def __init__(self, soundfont_path: str = "soundfonts/FluidR3_GM.sf2", gain: float = 0.8):
        self.soundfont_path = soundfont_path
        self.gain = gain
        self._fs = None
        self._sfid = None

    def start(self) -> None:
        try:
            import fluidsynth
        except ImportError:
            raise ImportError(
                "pyfluidsynth not installed. Run: pip install pyfluidsynth\n"
                "Also install FluidSynth: brew install fluidsynth (macOS)"
            )

        sf_path = Path(self.soundfont_path)
        if not sf_path.exists():
            raise FileNotFoundError(
                f"SoundFont not found: {sf_path}\n"
                "Download a GM SoundFont (e.g., FluidR3_GM.sf2) and place it in soundfonts/"
            )

        self._fs = fluidsynth.Synth(gain=self.gain)
        self._fs.start(driver="coreaudio")  # macOS; use "alsa" on Linux
        self._sfid = self._fs.sfload(str(sf_path))

    def stop(self) -> None:
        if self._fs:
            self._fs.delete()
            self._fs = None

    def send(self, message: mido.Message) -> None:
        if self._fs is None:
            return

        if message.type == "note_on":
            self._fs.noteon(message.channel, message.note, message.velocity)
        elif message.type == "note_off":
            self._fs.noteoff(message.channel, message.note)
        elif message.type == "program_change":
            self._fs.program_select(message.channel, self._sfid, 0, message.program)
        elif message.type == "control_change":
            self._fs.cc(message.channel, message.control, message.value)

    def set_instrument(self, channel: int, program: int) -> None:
        if self._fs and self._sfid is not None:
            self._fs.program_select(channel, self._sfid, 0, program)
