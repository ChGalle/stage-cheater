"""Menu system for playlist and song selection in Stage-Cheater."""

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

import pygame

from .config import hex_to_rgb


class MenuState(Enum):
    """States of the navigation menu."""
    HIDDEN = auto()
    PLAYLIST_SELECT = auto()
    SONG_SELECT = auto()


@dataclass
class PlaylistSummary:
    """Lightweight playlist information for menu display."""
    name: str
    path: Path
    song_count: int


@dataclass
class MenuItem:
    """A selectable item in a menu."""
    label: str
    value: any = None
    is_back: bool = False


class MenuController:
    """Manages menu state and navigation."""

    def __init__(self):
        self._state = MenuState.HIDDEN
        self._playlists: list[PlaylistSummary] = []
        self._songs: list[MenuItem] = []
        self._playlist_index = 0
        self._song_index = 0
        self._current_playlist_name = ""

    @property
    def state(self) -> MenuState:
        return self._state

    @property
    def is_active(self) -> bool:
        return self._state != MenuState.HIDDEN

    @property
    def current_index(self) -> int:
        if self._state == MenuState.PLAYLIST_SELECT:
            return self._playlist_index
        elif self._state == MenuState.SONG_SELECT:
            return self._song_index
        return 0

    @property
    def items(self) -> list[MenuItem]:
        """Get current menu items based on state."""
        if self._state == MenuState.PLAYLIST_SELECT:
            return [MenuItem(label=p.name, value=p) for p in self._playlists]
        elif self._state == MenuState.SONG_SELECT:
            return self._songs
        return []

    @property
    def item_count(self) -> int:
        return len(self.items)

    @property
    def title(self) -> str:
        """Get menu title based on state."""
        if self._state == MenuState.PLAYLIST_SELECT:
            return "PLAYLIST AUSWÄHLEN"
        elif self._state == MenuState.SONG_SELECT:
            return "SONG AUSWÄHLEN"
        return ""

    @property
    def subtitle(self) -> str:
        """Get menu subtitle (e.g., current playlist name in song menu)."""
        if self._state == MenuState.SONG_SELECT and self._current_playlist_name:
            return f"({self._current_playlist_name})"
        return ""

    def set_playlists(self, playlists: list[PlaylistSummary]) -> None:
        """Set available playlists."""
        self._playlists = playlists

    def set_songs(self, songs: list[MenuItem], playlist_name: str = "") -> None:
        """Set available songs for current playlist with optional [Back] entry."""
        self._songs = songs
        self._current_playlist_name = playlist_name
        self._song_index = 0

    def toggle_menu(self) -> None:
        """Toggle menu visibility. Opens to appropriate menu based on playlist count."""
        if self._state == MenuState.HIDDEN:
            if len(self._playlists) > 1:
                self._state = MenuState.PLAYLIST_SELECT
                self._playlist_index = 0
            else:
                self._state = MenuState.SONG_SELECT
                self._song_index = 0
        else:
            self._state = MenuState.HIDDEN

    def open_playlist_menu(self) -> None:
        """Open playlist selection menu."""
        self._state = MenuState.PLAYLIST_SELECT
        self._playlist_index = 0

    def open_song_menu(self) -> None:
        """Open song selection menu."""
        self._state = MenuState.SONG_SELECT
        self._song_index = 0

    def close(self) -> None:
        """Close the menu."""
        self._state = MenuState.HIDDEN

    def move_up(self) -> None:
        """Move selection up."""
        if self._state == MenuState.PLAYLIST_SELECT:
            if self._playlist_index > 0:
                self._playlist_index -= 1
        elif self._state == MenuState.SONG_SELECT:
            if self._song_index > 0:
                self._song_index -= 1

    def move_down(self) -> None:
        """Move selection down."""
        if self._state == MenuState.PLAYLIST_SELECT:
            if self._playlist_index < len(self._playlists) - 1:
                self._playlist_index += 1
        elif self._state == MenuState.SONG_SELECT:
            if self._song_index < len(self._songs) - 1:
                self._song_index += 1

    def select(self) -> tuple[MenuState, MenuItem | PlaylistSummary | None]:
        """
        Select current item.

        Returns:
            Tuple of (new_state, selected_item).
            selected_item is PlaylistSummary for playlist selection,
            MenuItem for song selection.
        """
        if self._state == MenuState.PLAYLIST_SELECT:
            if 0 <= self._playlist_index < len(self._playlists):
                playlist = self._playlists[self._playlist_index]
                # After selecting playlist, transition to song menu
                self._state = MenuState.SONG_SELECT
                self._song_index = 0
                return (MenuState.SONG_SELECT, playlist)
        elif self._state == MenuState.SONG_SELECT:
            if 0 <= self._song_index < len(self._songs):
                item = self._songs[self._song_index]
                if item.is_back:
                    # Go back to playlist menu if multiple playlists
                    if len(self._playlists) > 1:
                        self._state = MenuState.PLAYLIST_SELECT
                        return (MenuState.PLAYLIST_SELECT, None)
                    else:
                        # Close menu if only one playlist
                        self._state = MenuState.HIDDEN
                        return (MenuState.HIDDEN, None)
                else:
                    # Song selected, close menu
                    self._state = MenuState.HIDDEN
                    return (MenuState.HIDDEN, item)
        return (self._state, None)

    def go_back(self) -> None:
        """Go back to previous menu or close if at top level."""
        if self._state == MenuState.SONG_SELECT:
            if len(self._playlists) > 1:
                self._state = MenuState.PLAYLIST_SELECT
            else:
                self._state = MenuState.HIDDEN
        elif self._state == MenuState.PLAYLIST_SELECT:
            self._state = MenuState.HIDDEN


class MenuRenderer:
    """Renders menu overlay using Pygame."""

    # Colors
    OVERLAY_COLOR = (0, 0, 0, 200)  # Semi-transparent black
    SELECTED_BG_COLOR = (60, 60, 100)
    TEXT_COLOR = (255, 255, 255)
    SELECTED_TEXT_COLOR = (255, 255, 100)
    HINT_COLOR = (150, 150, 150)
    TITLE_COLOR = (255, 255, 255)
    SUBTITLE_COLOR = (180, 180, 180)

    # Layout
    ITEM_HEIGHT = 50
    VISIBLE_ITEMS = 8
    PADDING = 20

    def __init__(self):
        self._font: pygame.font.Font | None = None
        self._title_font: pygame.font.Font | None = None
        self._hint_font: pygame.font.Font | None = None
        self._initialized = False

    def _init_fonts(self, base_size: int = 32) -> None:
        """Initialize fonts if not already done."""
        if self._initialized:
            return
        self._font = pygame.font.Font(None, base_size)
        self._title_font = pygame.font.Font(None, int(base_size * 1.3))
        self._hint_font = pygame.font.Font(None, int(base_size * 0.75))
        self._initialized = True

    def render(
        self,
        surface: pygame.Surface,
        controller: MenuController,
        width: int,
        height: int,
        font_size: int = 32
    ) -> None:
        """Render menu overlay on given surface."""
        if not controller.is_active:
            return

        self._init_fonts(font_size)

        # Create semi-transparent overlay
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill(self.OVERLAY_COLOR)
        surface.blit(overlay, (0, 0))

        items = controller.items
        if not items:
            self._render_empty_message(surface, width, height)
            return

        current_index = controller.current_index

        # Calculate menu dimensions
        menu_width = min(600, width - 80)
        menu_height = min(
            self.ITEM_HEIGHT * min(len(items), self.VISIBLE_ITEMS) + 150,
            height - 80
        )
        menu_x = (width - menu_width) // 2
        menu_y = (height - menu_height) // 2

        # Draw menu background
        menu_rect = pygame.Rect(menu_x, menu_y, menu_width, menu_height)
        pygame.draw.rect(surface, (30, 30, 40), menu_rect, border_radius=10)
        pygame.draw.rect(surface, (80, 80, 100), menu_rect, width=2, border_radius=10)

        # Draw title
        y = menu_y + self.PADDING
        title_surface = self._title_font.render(controller.title, True, self.TITLE_COLOR)
        title_x = menu_x + (menu_width - title_surface.get_width()) // 2
        surface.blit(title_surface, (title_x, y))
        y += title_surface.get_height() + 5

        # Draw subtitle if present
        if controller.subtitle:
            subtitle_surface = self._hint_font.render(controller.subtitle, True, self.SUBTITLE_COLOR)
            subtitle_x = menu_x + (menu_width - subtitle_surface.get_width()) // 2
            surface.blit(subtitle_surface, (subtitle_x, y))
            y += subtitle_surface.get_height() + 10
        else:
            y += 10

        # Calculate scrolling
        visible_start = 0
        visible_count = min(len(items), self.VISIBLE_ITEMS)
        if current_index >= visible_count:
            visible_start = current_index - visible_count + 1
        visible_end = visible_start + visible_count

        # Draw items
        item_y = y + 5
        for i in range(visible_start, min(visible_end, len(items))):
            item = items[i]
            is_selected = (i == current_index)
            self._render_item(surface, item, menu_x + 10, item_y, menu_width - 20, is_selected)
            item_y += self.ITEM_HEIGHT

        # Draw scroll indicators if needed
        if visible_start > 0:
            indicator = self._hint_font.render("▲", True, self.HINT_COLOR)
            surface.blit(indicator, (menu_x + menu_width - 30, y))
        if visible_end < len(items):
            indicator = self._hint_font.render("▼", True, self.HINT_COLOR)
            surface.blit(indicator, (menu_x + menu_width - 30, item_y - 10))

        # Draw hint bar at bottom
        hint_y = menu_y + menu_height - 30
        hint_text = "[SW1: Hoch]  [SW2: Wählen]  [SW3: Runter]"
        hint_surface = self._hint_font.render(hint_text, True, self.HINT_COLOR)
        hint_x = menu_x + (menu_width - hint_surface.get_width()) // 2
        surface.blit(hint_surface, (hint_x, hint_y))

    def _render_item(
        self,
        surface: pygame.Surface,
        item: MenuItem,
        x: int,
        y: int,
        width: int,
        selected: bool
    ) -> None:
        """Render a single menu item."""
        # Draw selection background
        if selected:
            bg_rect = pygame.Rect(x, y, width, self.ITEM_HEIGHT - 5)
            pygame.draw.rect(surface, self.SELECTED_BG_COLOR, bg_rect, border_radius=5)

        # Format label
        if selected:
            label = f">> {item.label} <<"
            color = self.SELECTED_TEXT_COLOR
        else:
            label = f"   {item.label}"
            color = self.TEXT_COLOR

        # Render text
        text_surface = self._font.render(label, True, color)
        text_y = y + (self.ITEM_HEIGHT - 5 - text_surface.get_height()) // 2
        surface.blit(text_surface, (x + 10, text_y))

    def _render_empty_message(self, surface: pygame.Surface, width: int, height: int) -> None:
        """Render message when menu is empty."""
        self._init_fonts()
        text = "Keine Einträge verfügbar"
        text_surface = self._font.render(text, True, self.TEXT_COLOR)
        x = (width - text_surface.get_width()) // 2
        y = (height - text_surface.get_height()) // 2
        surface.blit(text_surface, (x, y))
