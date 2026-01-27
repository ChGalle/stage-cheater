"""Playlist management for Stage-Cheater."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from .chordpro import ChordProParser, Song


@dataclass
class PlaylistEntry:
    """An entry in a playlist."""
    filename: str
    path: Path | None = None
    song: Song | None = None
    error: str | None = None

    @property
    def is_loaded(self) -> bool:
        return self.song is not None

    @property
    def has_error(self) -> bool:
        return self.error is not None

    @property
    def display_name(self) -> str:
        """Get display name (song title or filename)."""
        if self.song and self.song.title:
            return self.song.title
        return self.filename


@dataclass
class Playlist:
    """A playlist of songs."""
    name: str
    entries: list[PlaylistEntry] = field(default_factory=list)
    _current_index: int = 0

    @property
    def current_index(self) -> int:
        return self._current_index

    @property
    def current_entry(self) -> PlaylistEntry | None:
        if 0 <= self._current_index < len(self.entries):
            return self.entries[self._current_index]
        return None

    @property
    def current_song(self) -> Song | None:
        entry = self.current_entry
        return entry.song if entry else None

    def __len__(self) -> int:
        return len(self.entries)

    def __iter__(self) -> Iterator[PlaylistEntry]:
        return iter(self.entries)

    def next_song(self) -> bool:
        """Go to next song. Returns True if song changed."""
        if self._current_index < len(self.entries) - 1:
            self._current_index += 1
            return True
        return False

    def prev_song(self) -> bool:
        """Go to previous song. Returns True if song changed."""
        if self._current_index > 0:
            self._current_index -= 1
            return True
        return False

    def go_to(self, index: int) -> bool:
        """Go to a specific song index. Returns True if valid."""
        if 0 <= index < len(self.entries):
            self._current_index = index
            return True
        return False

    def first_song(self) -> None:
        """Go to first song."""
        self._current_index = 0

    def last_song(self) -> None:
        """Go to last song."""
        self._current_index = max(0, len(self.entries) - 1)


class PlaylistManager:
    """Manages loading and parsing playlists."""

    PLAYLIST_EXTENSIONS = {".txt", ".lst", ".playlist"}

    def __init__(self, data_path: Path):
        self.data_path = data_path
        self.parser = ChordProParser()

    def load_playlist_file(self, path: Path) -> Playlist:
        """Load a playlist from a text file (one filename per line)."""
        playlist = Playlist(name=path.stem)

        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                entry = PlaylistEntry(filename=line)
                playlist.entries.append(entry)

        # Resolve paths and load songs
        self._resolve_and_load(playlist)

        return playlist

    def create_from_directory(self, directory: Path | None = None) -> Playlist:
        """Create a playlist from all ChordPro files in a directory."""
        if directory is None:
            directory = self.data_path

        playlist = Playlist(name=directory.name or "Songs")

        # Find all ChordPro files
        chordpro_files = []
        for ext in ChordProParser.EXTENSIONS:
            chordpro_files.extend(directory.glob(f"*{ext}"))

        # Sort alphabetically
        chordpro_files.sort(key=lambda p: p.name.lower())

        for file_path in chordpro_files:
            entry = PlaylistEntry(filename=file_path.name, path=file_path)
            playlist.entries.append(entry)

        # Load all songs
        self._load_songs(playlist)

        return playlist

    def _resolve_and_load(self, playlist: Playlist) -> None:
        """Resolve file paths and load songs for a playlist."""
        for entry in playlist.entries:
            if entry.path is None:
                entry.path = self._find_song_file(entry.filename)

        self._load_songs(playlist)

    def _find_song_file(self, filename: str) -> Path | None:
        """Find a song file by filename, trying various extensions."""
        # First, try exact filename
        exact_path = self.data_path / filename
        if exact_path.exists():
            return exact_path

        # Try with ChordPro extensions
        base_name = Path(filename).stem
        for ext in ChordProParser.EXTENSIONS:
            test_path = self.data_path / f"{base_name}{ext}"
            if test_path.exists():
                return test_path

        return None

    def _load_songs(self, playlist: Playlist) -> None:
        """Load songs for all entries in a playlist."""
        for entry in playlist.entries:
            if entry.path is None:
                entry.error = "File not found"
                continue

            if not entry.path.exists():
                entry.error = "File not found"
                continue

            try:
                entry.song = self.parser.parse_file(entry.path)
            except Exception as e:
                entry.error = str(e)

    def find_playlist_files(self) -> list[Path]:
        """Find all playlist files in the data path."""
        files = []
        for ext in self.PLAYLIST_EXTENSIONS:
            files.extend(self.data_path.glob(f"*{ext}"))
        return sorted(files, key=lambda p: p.name.lower())
