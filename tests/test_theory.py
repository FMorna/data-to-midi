from cam_to_midi.engine.theory import (
    build_chord,
    get_scale_notes,
    note_name_to_midi,
    quantize_to_scale,
    resolve_progression,
)


class TestNoteConversion:
    def test_c4_is_60(self):
        assert note_name_to_midi("C", 4) == 60

    def test_a4_is_69(self):
        assert note_name_to_midi("A", 4) == 69

    def test_middle_c(self):
        assert note_name_to_midi("C", 4) == 60


class TestScales:
    def test_c_major_notes(self):
        notes = get_scale_notes("C", "major")
        assert notes == [0, 2, 4, 5, 7, 9, 11]

    def test_a_minor_notes(self):
        notes = get_scale_notes("A", "minor")
        # A=9, so offset each interval by 9
        expected = [(9 + i) % 12 for i in [0, 2, 3, 5, 7, 8, 10]]
        assert notes == expected

    def test_pentatonic_has_5_notes(self):
        notes = get_scale_notes("C", "pentatonic_major")
        assert len(notes) == 5


class TestQuantization:
    def test_in_scale_unchanged(self):
        # C4 (60) is in C major
        assert quantize_to_scale(60, "C", "major") == 60

    def test_out_of_scale_snapped(self):
        # C#4 (61) should snap to C or D in C major
        result = quantize_to_scale(61, "C", "major")
        assert result in (60, 62)  # C4 or D4

    def test_result_in_range(self):
        for note in range(128):
            result = quantize_to_scale(note, "C", "major")
            assert 0 <= result <= 127

    def test_all_quantized_notes_in_scale(self):
        scale_pcs = set(get_scale_notes("C", "major"))
        for note in range(36, 96):
            result = quantize_to_scale(note, "C", "major")
            assert result % 12 in scale_pcs


class TestChords:
    def test_c_major_chord(self):
        chord = build_chord(60, "major")
        assert chord == [60, 64, 67]

    def test_a_minor_chord(self):
        chord = build_chord(69, "minor")
        assert chord == [69, 72, 76]

    def test_seventh_chord_has_4_notes(self):
        chord = build_chord(60, "major7")
        assert len(chord) == 4


class TestProgression:
    def test_resolve_basic(self):
        prog = resolve_progression(["I", "V", "vi", "IV"], "C", "major")
        assert len(prog) == 4
        # Each is a (root_note, quality) tuple
        for root, quality in prog:
            assert isinstance(root, int)
            assert quality in ("major", "minor", "diminished")

    def test_i_v_vi_iv_qualities(self):
        prog = resolve_progression(["I", "V", "vi", "IV"], "C", "major")
        qualities = [q for _, q in prog]
        assert qualities == ["major", "major", "minor", "major"]
