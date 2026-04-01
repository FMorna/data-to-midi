from __future__ import annotations

"""Music theory primitives: scales, chords, quantization, key management."""

from pathlib import Path

from ..config import load_scales_config

# Note name -> semitone offset
NOTE_MAP = {
    "C": 0, "Cs": 1, "Db": 1, "D": 2, "Ds": 3, "Eb": 3,
    "E": 4, "F": 5, "Fs": 6, "Gb": 6, "G": 7, "Gs": 8,
    "Ab": 8, "A": 9, "As": 10, "Bb": 10, "B": 11,
}

# Common scales as semitone intervals from root
SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
    "pentatonic_major": [0, 2, 4, 7, 9],
    "pentatonic_minor": [0, 3, 5, 7, 10],
    "blues": [0, 3, 5, 6, 7, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "whole_tone": [0, 2, 4, 6, 8, 10],
}

CHORD_INTERVALS = {
    "major": [0, 4, 7],
    "minor": [0, 3, 7],
    "diminished": [0, 3, 6],
    "augmented": [0, 4, 8],
    "major7": [0, 4, 7, 11],
    "minor7": [0, 3, 7, 10],
    "dominant7": [0, 4, 7, 10],
}

# Roman numeral -> (scale_degree_index, chord_quality)
# Uppercase = major, lowercase = minor
NUMERAL_MAP = {
    "I": (0, "major"), "II": (1, "major"), "III": (2, "major"),
    "IV": (3, "major"), "V": (4, "major"), "VI": (5, "major"), "VII": (6, "major"),
    "i": (0, "minor"), "ii": (1, "minor"), "iii": (2, "minor"),
    "iv": (3, "minor"), "v": (4, "minor"), "vi": (5, "minor"), "vii": (6, "diminished"),
}


def note_name_to_midi(name: str, octave: int = 4) -> int:
    """Convert note name + octave to MIDI note number. C4 = 60."""
    semitone = NOTE_MAP.get(name, 0)
    return 12 * (octave + 1) + semitone


def get_scale_notes(root: str, scale_name: str) -> list[int]:
    """Get semitone offsets for a scale relative to root."""
    intervals = SCALES.get(scale_name, SCALES["major"])
    root_offset = NOTE_MAP.get(root, 0)
    return [(root_offset + i) % 12 for i in intervals]


def quantize_to_scale(midi_note: int, root: str, scale_name: str) -> int:
    """Snap a MIDI note to the nearest note in the given scale."""
    scale_pcs = get_scale_notes(root, scale_name)
    pc = midi_note % 12
    octave = midi_note // 12

    # Find nearest scale pitch class
    min_dist = 12
    best_pc = pc
    for spc in scale_pcs:
        dist = min(abs(pc - spc), 12 - abs(pc - spc))
        if dist < min_dist:
            min_dist = dist
            best_pc = spc

    result = octave * 12 + best_pc
    # Ensure we stay close to the original note
    if result > midi_note + 6:
        result -= 12
    elif result < midi_note - 6:
        result += 12
    return max(0, min(127, result))


def build_chord(root_note: int, quality: str = "major") -> list[int]:
    """Build a chord from a root MIDI note and quality."""
    intervals = CHORD_INTERVALS.get(quality, CHORD_INTERVALS["major"])
    return [min(127, root_note + i) for i in intervals]


def resolve_progression(
    progression: list[str], root: str, scale_name: str
) -> list[tuple[int, str]]:
    """Resolve a Roman numeral progression to (root_midi_note, quality) pairs.

    Returns notes in octave 3 (bass register).
    """
    scale_notes = get_scale_notes(root, scale_name)
    result = []
    for numeral in progression:
        degree_idx, quality = NUMERAL_MAP.get(numeral, (0, "major"))
        if degree_idx < len(scale_notes):
            root_pc = scale_notes[degree_idx]
        else:
            root_pc = scale_notes[0]
        # Place in octave 3
        midi_root = 36 + root_pc  # C3 = 48, but bass at 36 = C2
        result.append((midi_root, quality))
    return result
