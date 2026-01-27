"""Tests for playlist management."""

import pytest
import tempfile
from pathlib import Path

from stage_cheater.playlist import Playlist, PlaylistEntry, PlaylistManager
from stage_cheater.chordpro import Song


class TestPlaylistEntry:
    """Tests for PlaylistEntry."""

    def test_is_loaded_false(self):
        """Test is_loaded when song is None."""
        entry = PlaylistEntry(filename="test.chopro")
        assert not entry.is_loaded

    def test_is_loaded_true(self):
        """Test is_loaded when song is set."""
        entry = PlaylistEntry(filename="test.chopro", song=Song())
        assert entry.is_loaded

    def test_has_error_false(self):
        """Test has_error when no error."""
        entry = PlaylistEntry(filename="test.chopro")
        assert not entry.has_error

    def test_has_error_true(self):
        """Test has_error when error is set."""
        entry = PlaylistEntry(filename="test.chopro", error="File not found")
        assert entry.has_error

    def test_display_name_from_song(self):
        """Test display_name uses song title."""
        song = Song(title="Amazing Grace")
        entry = PlaylistEntry(filename="test.chopro", song=song)
        assert entry.display_name == "Amazing Grace"

    def test_display_name_fallback(self):
        """Test display_name falls back to filename."""
        entry = PlaylistEntry(filename="test.chopro")
        assert entry.display_name == "test.chopro"

        # Also test with song but no title
        song = Song()
        entry = PlaylistEntry(filename="test.chopro", song=song)
        assert entry.display_name == "test.chopro"


class TestPlaylist:
    """Tests for Playlist."""

    def test_empty_playlist(self):
        """Test empty playlist."""
        playlist = Playlist(name="Test")
        assert len(playlist) == 0
        assert playlist.current_entry is None
        assert playlist.current_song is None

    def test_single_entry(self):
        """Test playlist with single entry."""
        song = Song(title="Test Song")
        entry = PlaylistEntry(filename="test.chopro", song=song)
        playlist = Playlist(name="Test", entries=[entry])

        assert len(playlist) == 1
        assert playlist.current_index == 0
        assert playlist.current_entry is entry
        assert playlist.current_song is song

    def test_next_song(self):
        """Test next_song navigation."""
        entries = [
            PlaylistEntry(filename="1.chopro", song=Song(title="Song 1")),
            PlaylistEntry(filename="2.chopro", song=Song(title="Song 2")),
            PlaylistEntry(filename="3.chopro", song=Song(title="Song 3")),
        ]
        playlist = Playlist(name="Test", entries=entries)

        assert playlist.current_index == 0
        assert playlist.next_song() is True
        assert playlist.current_index == 1
        assert playlist.next_song() is True
        assert playlist.current_index == 2
        # At end, should return False
        assert playlist.next_song() is False
        assert playlist.current_index == 2

    def test_prev_song(self):
        """Test prev_song navigation."""
        entries = [
            PlaylistEntry(filename="1.chopro", song=Song(title="Song 1")),
            PlaylistEntry(filename="2.chopro", song=Song(title="Song 2")),
        ]
        playlist = Playlist(name="Test", entries=entries)
        playlist._current_index = 1

        assert playlist.prev_song() is True
        assert playlist.current_index == 0
        # At start, should return False
        assert playlist.prev_song() is False
        assert playlist.current_index == 0

    def test_go_to(self):
        """Test go_to specific index."""
        entries = [
            PlaylistEntry(filename=f"{i}.chopro") for i in range(5)
        ]
        playlist = Playlist(name="Test", entries=entries)

        assert playlist.go_to(3) is True
        assert playlist.current_index == 3

        # Invalid indices
        assert playlist.go_to(-1) is False
        assert playlist.go_to(10) is False
        assert playlist.current_index == 3  # Unchanged

    def test_first_last_song(self):
        """Test first_song and last_song."""
        entries = [
            PlaylistEntry(filename=f"{i}.chopro") for i in range(5)
        ]
        playlist = Playlist(name="Test", entries=entries)
        playlist._current_index = 2

        playlist.first_song()
        assert playlist.current_index == 0

        playlist.last_song()
        assert playlist.current_index == 4

    def test_iteration(self):
        """Test iterating over playlist."""
        entries = [
            PlaylistEntry(filename=f"{i}.chopro") for i in range(3)
        ]
        playlist = Playlist(name="Test", entries=entries)

        iterated = list(playlist)
        assert len(iterated) == 3
        assert iterated == entries


class TestPlaylistManager:
    """Tests for PlaylistManager."""

    def test_create_from_directory(self):
        """Test creating playlist from directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create some ChordPro files
            (tmppath / "song1.chopro").write_text("{title: Song 1}\n[G]Hello")
            (tmppath / "song2.cho").write_text("{title: Song 2}\n[C]World")
            (tmppath / "not_a_song.txt").write_text("Random text")

            manager = PlaylistManager(tmppath)
            playlist = manager.create_from_directory()

            # Should only include ChordPro files
            assert len(playlist) == 2
            # Should be sorted alphabetically
            assert playlist.entries[0].filename == "song1.chopro"
            assert playlist.entries[1].filename == "song2.cho"
            # Songs should be loaded
            assert playlist.entries[0].song.title == "Song 1"
            assert playlist.entries[1].song.title == "Song 2"

    def test_load_playlist_file(self):
        """Test loading playlist from text file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create ChordPro files
            (tmppath / "song1.chopro").write_text("{title: Song 1}")
            (tmppath / "song2.chopro").write_text("{title: Song 2}")

            # Create playlist file
            playlist_file = tmppath / "setlist.txt"
            playlist_file.write_text("song1.chopro\nsong2.chopro\n# comment\n")

            manager = PlaylistManager(tmppath)
            playlist = manager.load_playlist_file(playlist_file)

            assert playlist.name == "setlist"
            assert len(playlist) == 2
            assert playlist.entries[0].song.title == "Song 1"

    def test_load_playlist_with_missing_files(self):
        """Test loading playlist with missing files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create one file, leave one missing
            (tmppath / "exists.chopro").write_text("{title: Exists}")

            playlist_file = tmppath / "playlist.txt"
            playlist_file.write_text("exists.chopro\nmissing.chopro\n")

            manager = PlaylistManager(tmppath)
            playlist = manager.load_playlist_file(playlist_file)

            assert len(playlist) == 2
            assert playlist.entries[0].is_loaded
            assert not playlist.entries[1].is_loaded
            assert playlist.entries[1].has_error

    def test_find_song_file_with_extension(self):
        """Test finding song files with different extensions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create file with .cho extension
            (tmppath / "mysong.cho").write_text("{title: My Song}")

            manager = PlaylistManager(tmppath)

            # Should find with explicit extension
            path = manager._find_song_file("mysong.cho")
            assert path is not None
            assert path.name == "mysong.cho"

            # Should find by stem name alone
            path = manager._find_song_file("mysong")
            assert path is not None
            assert path.name == "mysong.cho"

    def test_find_playlist_files(self):
        """Test finding playlist files in directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            (tmppath / "setlist.txt").write_text("song1")
            (tmppath / "gig.playlist").write_text("song2")
            (tmppath / "other.md").write_text("# Not a playlist")

            manager = PlaylistManager(tmppath)
            files = manager.find_playlist_files()

            names = [f.name for f in files]
            assert "setlist.txt" in names
            assert "gig.playlist" in names
            assert "other.md" not in names
