"""Tests for ChordPro parser."""

import pytest
from stage_cheater.chordpro import ChordProParser, Song, SongLine, ChordPosition


class TestChordProParser:
    """Tests for ChordProParser."""

    def setup_method(self):
        self.parser = ChordProParser()

    def test_parse_empty_content(self):
        """Test parsing empty content."""
        song = self.parser.parse("")
        assert song.title == ""
        assert len(song.lines) == 0

    def test_parse_title_directive(self):
        """Test parsing title directive."""
        content = "{title: Amazing Grace}"
        song = self.parser.parse(content)
        assert song.title == "Amazing Grace"

    def test_parse_title_directive_short(self):
        """Test parsing short title directive."""
        content = "{t: Amazing Grace}"
        song = self.parser.parse(content)
        assert song.title == "Amazing Grace"

    def test_parse_artist_directive(self):
        """Test parsing artist directive."""
        content = "{artist: John Newton}"
        song = self.parser.parse(content)
        assert song.artist == "John Newton"

    def test_parse_key_directive(self):
        """Test parsing key directive."""
        content = "{key: G}"
        song = self.parser.parse(content)
        assert song.key == "G"

    def test_parse_capo_directive(self):
        """Test parsing capo directive."""
        content = "{capo: 2}"
        song = self.parser.parse(content)
        assert song.capo == "2"

    def test_parse_multiple_directives(self):
        """Test parsing multiple directives."""
        content = """{title: Amazing Grace}
{artist: John Newton}
{key: G}
{capo: 2}"""
        song = self.parser.parse(content)
        assert song.title == "Amazing Grace"
        assert song.artist == "John Newton"
        assert song.key == "G"
        assert song.capo == "2"

    def test_parse_line_without_chords(self):
        """Test parsing a line without chords."""
        content = "Amazing grace how sweet the sound"
        song = self.parser.parse(content)
        assert len(song.lines) == 1
        assert song.lines[0].lyrics == "Amazing grace how sweet the sound"
        assert not song.lines[0].has_chords

    def test_parse_line_with_single_chord(self):
        """Test parsing a line with a single chord."""
        content = "[G]Amazing grace"
        song = self.parser.parse(content)
        assert len(song.lines) == 1
        line = song.lines[0]
        assert line.lyrics == "Amazing grace"
        assert line.has_chords
        assert len(line.chords) == 1
        assert line.chords[0].chord == "G"
        assert line.chords[0].position == 0

    def test_parse_line_with_multiple_chords(self):
        """Test parsing a line with multiple chords."""
        content = "[G]Amazing [C]grace how [D]sweet"
        song = self.parser.parse(content)
        line = song.lines[0]
        assert line.lyrics == "Amazing grace how sweet"
        assert len(line.chords) == 3
        assert line.chords[0].chord == "G"
        assert line.chords[1].chord == "C"
        assert line.chords[2].chord == "D"

    def test_parse_line_with_chord_at_end(self):
        """Test parsing a line with chord at end."""
        content = "Amazing grace[G]"
        song = self.parser.parse(content)
        line = song.lines[0]
        assert line.lyrics == "Amazing grace"
        assert len(line.chords) == 1
        assert line.chords[0].position == 13  # After "Amazing grace"

    def test_parse_complex_chords(self):
        """Test parsing complex chord names."""
        content = "[Am7]First [Cmaj7]second [F#m]third"
        song = self.parser.parse(content)
        line = song.lines[0]
        assert line.chords[0].chord == "Am7"
        assert line.chords[1].chord == "Cmaj7"
        assert line.chords[2].chord == "F#m"

    def test_parse_empty_line(self):
        """Test parsing empty lines."""
        content = "Line one\n\nLine two"
        song = self.parser.parse(content)
        assert len(song.lines) == 3
        assert song.lines[0].lyrics == "Line one"
        assert song.lines[1].is_empty
        assert song.lines[2].lyrics == "Line two"

    def test_parse_full_song(self):
        """Test parsing a complete song."""
        content = """{title: Amazing Grace}
{artist: John Newton}
{key: G}

[G]Amazing [G7]grace how [C]sweet the [G]sound
That [G]saved a [Em]wretch like [D]me
[G]I once was [G7]lost but [C]now I'm [G]found
Was [G]blind but [D]now I [G]see"""

        song = self.parser.parse(content)
        assert song.title == "Amazing Grace"
        assert song.artist == "John Newton"
        assert song.key == "G"
        # One empty line after directives, then 4 lyric lines
        assert len(song.lines) == 5
        assert song.lines[0].is_empty
        assert song.lines[1].has_chords

    def test_chord_position_calculation(self):
        """Test that chord positions are calculated correctly."""
        content = "[G]A [C]B [D]C"
        song = self.parser.parse(content)
        line = song.lines[0]
        # Lyrics: "A B C"
        # G at position 0, C at position 2, D at position 4
        assert line.chords[0].position == 0
        assert line.chords[1].position == 2
        assert line.chords[2].position == 4

    def test_display_title_fallback(self):
        """Test display_title falls back to 'Untitled'."""
        song = Song()
        assert song.display_title == "Untitled"

        song.title = "My Song"
        assert song.display_title == "My Song"


class TestSongLine:
    """Tests for SongLine dataclass."""

    def test_has_chords_false(self):
        """Test has_chords is False for line without chords."""
        line = SongLine(lyrics="Hello world")
        assert not line.has_chords

    def test_has_chords_true(self):
        """Test has_chords is True for line with chords."""
        line = SongLine(
            lyrics="Hello",
            chords=[ChordPosition(chord="G", position=0)]
        )
        assert line.has_chords

    def test_is_empty(self):
        """Test is_empty flag."""
        empty_line = SongLine(lyrics="", is_empty=True)
        assert empty_line.is_empty

        normal_line = SongLine(lyrics="Text")
        assert not normal_line.is_empty
