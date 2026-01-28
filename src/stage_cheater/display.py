"""Pygame-based display for Stage-Cheater."""

import pygame
from dataclasses import dataclass

from .config import Config, DisplayConfig, hex_to_rgb
from .chordpro import Song, SongLine


@dataclass
class Page:
    """A page of content to display."""
    start_line: int
    end_line: int


class Display:
    """Pygame-based fullscreen display for songs."""

    def __init__(self, config: Config):
        self.config = config
        self.display_config = config.display
        self._zoom = self.display_config.zoom
        self._rotation = self.display_config.rotation
        self._screen: pygame.Surface | None = None
        self._render_surface: pygame.Surface | None = None  # Surface to render content to
        self._font: pygame.font.Font | None = None
        self._chord_font: pygame.font.Font | None = None
        self._title_font: pygame.font.Font | None = None
        self._width = 0  # Logical width (after rotation)
        self._height = 0  # Logical height (after rotation)
        self._screen_width = 0  # Physical screen width
        self._screen_height = 0  # Physical screen height
        self._line_height = 0
        self._chord_height = 0
        self._margin = 40
        self._current_song: Song | None = None
        self._pages: list[Page] = []
        self._current_page = 0

    @property
    def zoom(self) -> float:
        return self._zoom

    @zoom.setter
    def zoom(self, value: float) -> None:
        self._zoom = max(0.5, min(3.0, value))  # Clamp between 0.5 and 3.0
        self._update_fonts()
        if self._current_song:
            self._calculate_pages()

    def init(self) -> None:
        """Initialize Pygame and create fullscreen display."""
        pygame.init()
        pygame.font.init()
        pygame.mouse.set_visible(False)

        # Get display info for fullscreen
        info = pygame.display.Info()
        self._screen_width = info.current_w
        self._screen_height = info.current_h

        # Create fullscreen display
        self._screen = pygame.display.set_mode(
            (self._screen_width, self._screen_height),
            pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF
        )
        pygame.display.set_caption("Stage-Cheater")

        # Set logical dimensions based on rotation
        if self._rotation in (90, 270):
            # Swap width and height for 90/270 degree rotation
            self._width = self._screen_height
            self._height = self._screen_width
        else:
            self._width = self._screen_width
            self._height = self._screen_height

        # Create render surface with logical dimensions
        self._render_surface = pygame.Surface((self._width, self._height))

        self._update_fonts()

    def _update_fonts(self) -> None:
        """Update fonts based on current zoom level."""
        base_size = self.display_config.font_size
        scaled_size = int(base_size * self._zoom)

        self._font = pygame.font.Font(None, scaled_size)
        self._chord_font = pygame.font.Font(None, int(scaled_size * 0.9))
        self._title_font = pygame.font.Font(None, int(scaled_size * 1.5))

        # Calculate line heights
        self._line_height = self._font.get_linesize()
        self._chord_height = self._chord_font.get_linesize()

    def quit(self) -> None:
        """Shutdown Pygame."""
        pygame.quit()

    def set_song(self, song: Song) -> None:
        """Set the current song to display."""
        self._current_song = song
        self._current_page = 0
        self._calculate_pages()

    def _calculate_pages(self) -> None:
        """Calculate page breaks based on screen height."""
        if not self._current_song:
            self._pages = []
            return

        self._pages = []
        available_height = self._height - 2 * self._margin
        # Reserve space for title only on first page
        title_space = int(self._title_font.get_linesize() * 1.5) if self._current_song.title else 0
        first_page_height = available_height - title_space
        other_page_height = available_height

        current_height = 0
        page_start = 0
        is_first_page = True

        for i, line in enumerate(self._current_song.lines):
            line_total_height = self._get_line_height(line)
            content_height = first_page_height if is_first_page else other_page_height

            if current_height + line_total_height > content_height and i > page_start:
                # Start new page
                self._pages.append(Page(start_line=page_start, end_line=i))
                page_start = i
                current_height = line_total_height
                is_first_page = False
            else:
                current_height += line_total_height

        # Add final page
        if page_start < len(self._current_song.lines):
            self._pages.append(Page(start_line=page_start, end_line=len(self._current_song.lines)))

        # Ensure at least one page
        if not self._pages:
            self._pages.append(Page(start_line=0, end_line=0))

    def _get_line_height(self, line: SongLine) -> int:
        """Get total height needed for a line (chords + lyrics)."""
        if line.is_empty:
            return int(self._line_height * 1.2)  # Extra space between stanzas
        if line.has_chords:
            return self._chord_height + self._line_height
        return self._line_height

    def render(self) -> None:
        """Render the current page of the song."""
        if not self._screen or not self._render_surface:
            return

        # Clear render surface
        bg_color = hex_to_rgb(self.display_config.background_color)
        self._render_surface.fill(bg_color)

        if not self._current_song:
            self._render_no_song()
            self._apply_rotation_and_display()
            return

        y = self._margin

        # Render title only on first page
        if self._current_song.title and self._current_page == 0:
            y = self._render_title(y)

        # Render page indicator
        self._render_page_indicator()

        # Get current page
        if self._current_page < len(self._pages):
            page = self._pages[self._current_page]
            for i in range(page.start_line, page.end_line):
                if i < len(self._current_song.lines):
                    y = self._render_line(self._current_song.lines[i], y)

        self._apply_rotation_and_display()

    def _apply_rotation_and_display(self) -> None:
        """Apply rotation to render surface and display on screen."""
        if self._rotation == 0:
            self._screen.blit(self._render_surface, (0, 0))
        else:
            rotated = pygame.transform.rotate(self._render_surface, -self._rotation)
            self._screen.blit(rotated, (0, 0))
        pygame.display.flip()

    def _render_no_song(self) -> None:
        """Render message when no song is loaded."""
        text_color = hex_to_rgb(self.display_config.font_color)
        text = self._font.render("No song loaded", True, text_color)
        x = (self._width - text.get_width()) // 2
        y = (self._height - text.get_height()) // 2
        self._render_surface.blit(text, (x, y))

    def _render_title(self, y: int) -> int:
        """Render song title and return new y position."""
        text_color = hex_to_rgb(self.display_config.font_color)

        title_text = self._current_song.display_title
        if self._current_song.artist:
            title_text += f" - {self._current_song.artist}"

        title_surface = self._title_font.render(title_text, True, text_color)
        x = self._margin
        self._render_surface.blit(title_surface, (x, y))

        # Add key/capo info if available
        info_parts = []
        if self._current_song.key:
            info_parts.append(f"Key: {self._current_song.key}")
        if self._current_song.capo:
            info_parts.append(f"Capo: {self._current_song.capo}")

        if info_parts:
            info_text = " | ".join(info_parts)
            info_surface = self._font.render(info_text, True, text_color)
            self._render_surface.blit(info_surface, (x, y + self._title_font.get_linesize()))
            return y + int(self._title_font.get_linesize() * 1.5) + self._line_height

        return y + int(self._title_font.get_linesize() * 1.5)

    def _render_line(self, line: SongLine, y: int) -> int:
        """Render a single line and return new y position."""
        if line.is_empty:
            return y + int(self._line_height * 1.2)  # Extra space between stanzas

        text_color = hex_to_rgb(self.display_config.font_color)
        chord_color = hex_to_rgb(self.display_config.chord_color)
        x = self._margin

        # Render chords first (above lyrics)
        if line.has_chords:
            for chord_pos in line.chords:
                # Calculate x position based on character position
                prefix = line.lyrics[:chord_pos.position]
                chord_x = x + self._font.size(prefix)[0]
                chord_surface = self._chord_font.render(chord_pos.chord, True, chord_color)
                self._render_surface.blit(chord_surface, (chord_x, y))
            y += self._chord_height

        # Render lyrics
        if line.lyrics.strip():
            lyrics_surface = self._font.render(line.lyrics, True, text_color)
            self._render_surface.blit(lyrics_surface, (x, y))

        return y + self._line_height

    def _render_page_indicator(self) -> None:
        """Render page number indicator in corner."""
        if len(self._pages) <= 1:
            return

        text_color = hex_to_rgb(self.display_config.font_color)
        indicator = f"{self._current_page + 1}/{len(self._pages)}"
        indicator_surface = self._font.render(indicator, True, text_color)

        x = self._width - self._margin - indicator_surface.get_width()
        y = self._margin
        self._render_surface.blit(indicator_surface, (x, y))

    def next_page(self) -> bool:
        """Go to next page. Returns True if page changed."""
        if self._current_page < len(self._pages) - 1:
            self._current_page += 1
            return True
        return False

    def prev_page(self) -> bool:
        """Go to previous page. Returns True if page changed."""
        if self._current_page > 0:
            self._current_page -= 1
            return True
        return False

    def first_page(self) -> None:
        """Go to first page."""
        self._current_page = 0

    def last_page(self) -> None:
        """Go to last page."""
        self._current_page = max(0, len(self._pages) - 1)

    @property
    def page_count(self) -> int:
        """Get total number of pages."""
        return len(self._pages)

    @property
    def current_page(self) -> int:
        """Get current page number (0-indexed)."""
        return self._current_page

    def zoom_in(self, step: float = 0.1) -> None:
        """Increase zoom level."""
        self.zoom = self._zoom + step

    def zoom_out(self, step: float = 0.1) -> None:
        """Decrease zoom level."""
        self.zoom = self._zoom - step
