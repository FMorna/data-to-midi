from __future__ import annotations

"""Pygame MIDI backend — fallback synth using the OS default MIDI synthesizer."""

import mido

from .base import BaseSynth


class PygameSynth(BaseSynth):
    """Routes MIDI to the system's default MIDI synthesizer via pygame."""

    def __init__(self):
        self._output = None

    def start(self) -> None:
        try:
            import pygame
            import pygame.midi
        except ImportError:
            raise ImportError("pygame not installed. Run: pip install pygame")

        pygame.init()
        pygame.midi.init()

        # Use the default output device
        device_id = pygame.midi.get_default_output_id()
        if device_id < 0:
            raise RuntimeError("No MIDI output device found")
        self._output = pygame.midi.Output(device_id)

    def stop(self) -> None:
        if self._output:
            self._output.close()
            self._output = None
            import pygame.midi

            pygame.midi.quit()

    def send(self, message: mido.Message) -> None:
        if self._output is None:
            return

        if message.type == "note_on":
            self._output.note_on(message.note, message.velocity, message.channel)
        elif message.type == "note_off":
            self._output.note_off(message.note, message.velocity, message.channel)
        elif message.type == "program_change":
            self._output.set_instrument(message.program, message.channel)

    def set_instrument(self, channel: int, program: int) -> None:
        if self._output:
            self._output.set_instrument(program, channel)
