"""ChordPro file parser for Stage-Cheater."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


@dataclass
class ChordPosition:
    """A chord at a specific position in a line."""
    chord: str
    position: int  # Character position in the lyrics line


@dataclass
class SongLine:
    """A single line of a song with lyrics and chord positions."""
    lyrics: str
    chords: list[ChordPosition] = field(default_factory=list)
    is_empty: bool = False

    @property
    def has_chords(self) -> bool:
        return len(self.chords) > 0


@dataclass
class Song:
    """A complete song parsed from ChordPro format."""
    title: str = ""
    artist: str = ""
    key: str = ""
    tempo: str = ""
    capo: str = ""
    lines: list[SongLine] = field(default_factory=list)
    raw_directives: dict[str, str] = field(default_factory=dict)

    @property
    def display_title(self) -> str:
        """Get title for display, fallback to 'Untitled'."""
        return self.title or "Untitled"


class ChordProParser:
    """Parser for ChordPro format files."""

    # Supported file extensions
    EXTENSIONS = {".chopro", ".cho", ".crd", ".chordpro"}

    # Regex patterns
    DIRECTIVE_PATTERN = re.compile(r"\{(\w+)(?::\s*(.+?))?\}")
    CHORD_PATTERN = re.compile(r"\[([^\]]+)\]")

    # Known directives and their aliases
    DIRECTIVE_ALIASES = {
        "t": "title",
        "st": "subtitle",
        "su": "subtitle",
        "artist": "artist",
        "a": "artist",
        "key": "key",
        "k": "key",
        "tempo": "tempo",
        "capo": "capo",
        "comment": "comment",
        "c": "comment",
        "comment_italic": "comment_italic",
        "ci": "comment_italic",
        "comment_box": "comment_box",
        "cb": "comment_box",
        "start_of_chorus": "start_of_chorus",
        "soc": "start_of_chorus",
        "end_of_chorus": "end_of_chorus",
        "eoc": "end_of_chorus",
        "start_of_verse": "start_of_verse",
        "sov": "start_of_verse",
        "end_of_verse": "end_of_verse",
        "eov": "end_of_verse",
        "start_of_bridge": "start_of_bridge",
        "sob": "start_of_bridge",
        "end_of_bridge": "end_of_bridge",
        "eob": "end_of_bridge",
    }

    @classmethod
    def is_chordpro_file(cls, path: Path) -> bool:
        """Check if a file has a ChordPro extension."""
        return path.suffix.lower() in cls.EXTENSIONS

    def parse_file(self, path: Path) -> Song:
        """Parse a ChordPro file and return a Song object."""
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return self.parse(content)

    def parse(self, content: str) -> Song:
        """Parse ChordPro content string and return a Song object."""
        song = Song()
        lines = content.splitlines()

        for line in lines:
            line = line.rstrip()

            # Check for directives
            directive_match = self.DIRECTIVE_PATTERN.match(line.strip())
            if directive_match and line.strip().startswith("{"):
                self._handle_directive(song, directive_match.group(1), directive_match.group(2))
                continue

            # Parse line with potential chords
            song_line = self._parse_line(line)
            song.lines.append(song_line)

        return song

    def _handle_directive(self, song: Song, directive: str, value: str | None) -> None:
        """Handle a ChordPro directive."""
        # Normalize directive name
        directive = directive.lower()
        directive = self.DIRECTIVE_ALIASES.get(directive, directive)

        value = value.strip() if value else ""

        # Store in raw directives
        song.raw_directives[directive] = value

        # Handle known directives
        if directive == "title":
            song.title = value
        elif directive == "subtitle" or directive == "artist":
            song.artist = value
        elif directive == "key":
            song.key = value
        elif directive == "tempo":
            song.tempo = value
        elif directive == "capo":
            song.capo = value

    def _parse_line(self, line: str) -> SongLine:
        """Parse a single line, extracting chords and lyrics."""
        if not line.strip():
            return SongLine(lyrics="", is_empty=True)

        chords: list[ChordPosition] = []
        lyrics_parts: list[str] = []
        current_pos = 0
        last_end = 0

        for match in self.CHORD_PATTERN.finditer(line):
            # Add text before this chord
            lyrics_parts.append(line[last_end:match.start()])
            current_pos += match.start() - last_end

            # Record chord position
            chords.append(ChordPosition(
                chord=match.group(1),
                position=current_pos
            ))

            last_end = match.end()

        # Add remaining text after last chord
        lyrics_parts.append(line[last_end:])

        lyrics = "".join(lyrics_parts)

        return SongLine(lyrics=lyrics, chords=chords)


def find_chordpro_files(directory: Path) -> Iterator[Path]:
    """Find all ChordPro files in a directory (non-recursive)."""
    if not directory.is_dir():
        return

    for ext in ChordProParser.EXTENSIONS:
        yield from directory.glob(f"*{ext}")


def find_chordpro_files_recursive(directory: Path) -> Iterator[Path]:
    """Find all ChordPro files in a directory (recursive)."""
    if not directory.is_dir():
        return

    for ext in ChordProParser.EXTENSIONS:
        yield from directory.rglob(f"*{ext}")
