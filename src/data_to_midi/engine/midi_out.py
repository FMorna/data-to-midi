from __future__ import annotations

"""MIDI output utilities for program changes and control messages."""

import mido


def program_change(channel: int, program: int) -> mido.Message:
    """Create a MIDI program change message."""
    return mido.Message("program_change", channel=channel, program=program)


def control_change(channel: int, control: int, value: int) -> mido.Message:
    """Create a MIDI control change message."""
    return mido.Message("control_change", channel=channel, control=control, value=value)


def all_notes_off(channel: int) -> mido.Message:
    """Send all-notes-off on a channel."""
    return mido.Message("control_change", channel=channel, control=123, value=0)


def setup_channels(channel_configs: dict) -> list[mido.Message]:
    """Generate program change messages for all configured channels."""
    messages = []
    for name, cfg in channel_configs.items():
        messages.append(program_change(cfg.channel, cfg.program))
    return messages
