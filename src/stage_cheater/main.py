"""Main entry point for Stage-Cheater."""

import argparse
import sys
from pathlib import Path

import pygame

from .config import Config
from .display import Display
from .input_handler import InputHandler, Action
from .menu import MenuController, MenuState, MenuItem, PlaylistSummary
from .playlist import PlaylistManager, Playlist
from .usb_mount import find_first_data_source, USBDataSource
from .system_control import SystemControl


class StageCheater:
    """Main application class for Stage-Cheater."""

    def __init__(self, config: Config, data_source: USBDataSource | None = None):
        self.config = config
        self.data_source = data_source
        self.display = Display(config)
        self.input_handler = InputHandler(config)
        self.system_control = SystemControl(
            config,
            on_shutdown_requested=self._on_shutdown,
            on_restart_requested=self._on_restart,
        )
        self.playlist: Playlist | None = None
        self.playlist_manager: PlaylistManager | None = None
        self.menu_controller = MenuController()
        self._playlist_files: list[Path] = []
        self._running = False
        self._shutdown_requested = False
        self._restart_requested = False

    def setup(self) -> None:
        """Initialize the application."""
        # Initialize display
        self.display.init()

        # Setup system control GPIO (if available)
        self.system_control.setup()

        # Load playlist
        self._load_data()

        # Show first song
        if self.playlist and self.playlist.current_song:
            self.display.set_song(self.playlist.current_song)

    def _load_data(self) -> None:
        """Load songs and playlists from data source."""
        if not self.data_source:
            print("No data source available")
            return

        songs_path = self.data_source.songs_path
        if not songs_path:
            print("No songs path in data source")
            return

        self.playlist_manager = PlaylistManager(songs_path)

        # Try to find playlist files
        self._playlist_files = []
        if self.data_source.playlists_path:
            self._playlist_files = self.playlist_manager.find_playlist_files()
            # Also check playlists directory
            for ext in self.playlist_manager.PLAYLIST_EXTENSIONS:
                self._playlist_files.extend(self.data_source.playlists_path.glob(f"*{ext}"))

        # Build playlist summaries for menu
        playlist_summaries = []
        # Always add "All Songs" option first
        all_songs_summary = self.playlist_manager.get_all_songs_summary()
        if all_songs_summary.song_count > 0:
            playlist_summaries.append(all_songs_summary)
        # Add specific playlist files
        playlist_summaries.extend(self.playlist_manager.get_playlist_summaries(self._playlist_files))
        self.menu_controller.set_playlists(playlist_summaries)

        if self._playlist_files:
            # Load first playlist
            self.playlist = self.playlist_manager.load_playlist_file(self._playlist_files[0])
            print(f"Loaded playlist: {self.playlist.name} ({len(self.playlist)} songs)")
        else:
            # Create playlist from all songs in directory
            self.playlist = self.playlist_manager.create_from_directory()
            print(f"Created playlist from directory: {len(self.playlist)} songs")

        # Update menu with current playlist songs
        self._update_song_menu()

    def run(self) -> None:
        """Run the main event loop."""
        self._running = True
        clock = pygame.time.Clock()

        while self._running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                    continue

                action = self.input_handler.handle_event(event)
                self._handle_action(action)

            # Render current state (pass menu controller for overlay)
            self.display.render(self.menu_controller)

            # Cap frame rate
            clock.tick(30)

        self._cleanup()

    def _handle_action(self, action: Action) -> None:
        """Handle a user action with context-sensitive behavior."""
        if action == Action.NONE:
            return

        if action == Action.QUIT:
            if self.menu_controller.is_active:
                self.menu_controller.close()
            else:
                self._running = False
            return

        # Context-sensitive action translation when menu is active
        if self.menu_controller.is_active:
            self._handle_menu_action(action)
        else:
            self._handle_normal_action(action)

    def _handle_normal_action(self, action: Action) -> None:
        """Handle actions in normal display mode."""
        if action == Action.NEXT_PAGE:
            if not self.display.next_page():
                # At last page, try next song
                self._next_song()

        elif action == Action.PREV_PAGE:
            if not self.display.prev_page():
                # At first page, try previous song
                self._prev_song()

        elif action == Action.NEXT_SONG:
            self._next_song()

        elif action == Action.PREV_SONG:
            self._prev_song()

        elif action == Action.ZOOM_IN:
            self.display.zoom_in()

        elif action == Action.ZOOM_OUT:
            self.display.zoom_out()

        elif action == Action.MENU_TOGGLE:
            self.menu_controller.toggle_menu()

    def _handle_menu_action(self, action: Action) -> None:
        """Handle actions when menu is active.

        Maps normal navigation actions to menu navigation.
        """
        # Map PREV_PAGE/NEXT_PAGE to menu navigation (for foot pedals)
        if action in (Action.PREV_PAGE, Action.MENU_UP):
            self.menu_controller.move_up()

        elif action in (Action.NEXT_PAGE, Action.MENU_DOWN):
            self.menu_controller.move_down()

        elif action in (Action.MENU_TOGGLE, Action.MENU_SELECT):
            self._handle_menu_select()

        elif action == Action.MENU_BACK:
            self.menu_controller.go_back()

    def _next_song(self) -> None:
        """Go to next song in playlist."""
        if self.playlist and self.playlist.next_song():
            song = self.playlist.current_song
            if song:
                self.display.set_song(song)
                print(f"Now playing: {song.display_title}")

    def _prev_song(self) -> None:
        """Go to previous song in playlist."""
        if self.playlist and self.playlist.prev_song():
            song = self.playlist.current_song
            if song:
                self.display.set_song(song)
                print(f"Now playing: {song.display_title}")

    def _handle_menu_select(self) -> None:
        """Handle selection in the menu."""
        new_state, selected = self.menu_controller.select()

        if selected is None:
            return

        if isinstance(selected, PlaylistSummary):
            # Playlist was selected, load it and update song menu
            self._load_selected_playlist(selected)
            self._update_song_menu()
        elif isinstance(selected, MenuItem):
            # Song was selected, jump to it
            if selected.value is not None:
                self._jump_to_song(selected.value)

    def _load_selected_playlist(self, summary: PlaylistSummary) -> None:
        """Load a playlist from its summary."""
        if not self.playlist_manager:
            return

        if summary.name == "Alle Songs":
            # Load all songs from directory
            self.playlist = self.playlist_manager.create_from_directory()
        else:
            # Load specific playlist file
            self.playlist = self.playlist_manager.load_playlist_file(summary.path)

        print(f"Loaded playlist: {self.playlist.name} ({len(self.playlist)} songs)")

        # Show first song
        if self.playlist and self.playlist.current_song:
            self.display.set_song(self.playlist.current_song)

    def _update_song_menu(self) -> None:
        """Update the song menu with current playlist entries."""
        if not self.playlist:
            self.menu_controller.set_songs([], "")
            return

        songs = []
        # Add [Back] entry at top (if there are multiple playlists)
        if len(self.menu_controller._playlists) > 1:
            songs.append(MenuItem(label="[Zurück]", is_back=True))

        # Add all songs from playlist
        for entry in self.playlist.entries:
            songs.append(MenuItem(label=entry.display_name, value=entry))

        self.menu_controller.set_songs(songs, self.playlist.name)

    def _jump_to_song(self, entry) -> None:
        """Jump to a specific song in the current playlist."""
        if not self.playlist:
            return

        # Find the entry index
        for i, playlist_entry in enumerate(self.playlist.entries):
            if playlist_entry is entry:
                self.playlist.go_to(i)
                if entry.song:
                    self.display.set_song(entry.song)
                    print(f"Now playing: {entry.display_name}")
                break

    def _on_shutdown(self) -> None:
        """Handle shutdown request."""
        self._running = False
        self._shutdown_requested = True

    def _on_restart(self) -> None:
        """Handle restart request."""
        self._running = False
        self._restart_requested = True

    def _cleanup(self) -> None:
        """Cleanup resources."""
        self.input_handler.cleanup()
        self.system_control.cleanup()
        self.display.quit()

        # Execute system shutdown/restart after cleanup
        if self._shutdown_requested:
            SystemControl.shutdown()
        elif self._restart_requested:
            SystemControl.restart()


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Stage-Cheater: Raspberry Pi stage teleprompter"
    )
    parser.add_argument(
        "-c", "--config",
        type=Path,
        help="Path to config.toml file",
    )
    parser.add_argument(
        "-d", "--data-dir",
        type=Path,
        help="Path to data directory (songs, playlists)",
    )
    parser.add_argument(
        "-f", "--file",
        type=Path,
        help="Path to a single ChordPro file to display",
    )
    parser.add_argument(
        "--no-fullscreen",
        action="store_true",
        help="Run in windowed mode (for testing)",
    )
    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Load configuration
    config: Config
    if args.config and args.config.exists():
        config = Config.load(args.config)
        print(f"Loaded config from: {args.config}")
    else:
        config = Config.load_default()
        print("Using default configuration")

    # Find data source
    data_source: USBDataSource | None = None

    if args.data_dir:
        # Use specified data directory
        from .usb_mount import USBDataSource
        data_source = USBDataSource(args.data_dir)
        print(f"Using data directory: {args.data_dir}")
    else:
        # Try to find USB stick
        data_source = find_first_data_source()
        if data_source:
            print(f"Found USB data source: {data_source.root_path}")

            # Load config from USB if available
            if data_source.config_path:
                config = Config.load(data_source.config_path)
                print(f"Loaded config from USB: {data_source.config_path}")

    # Handle single file mode
    if args.file:
        from .chordpro import ChordProParser
        from .playlist import Playlist, PlaylistEntry

        parser = ChordProParser()
        song = parser.parse_file(args.file)

        # Create a single-song playlist
        entry = PlaylistEntry(filename=args.file.name, path=args.file, song=song)
        single_playlist = Playlist(name="Single Song", entries=[entry])

        # Create app with single song
        app = StageCheater(config, data_source)
        app.setup()
        app.playlist = single_playlist
        app.display.set_song(song)
        app.run()
        return 0

    if not data_source or not data_source.is_valid:
        print("No valid data source found.")
        print("Please provide a data directory with -d or connect a USB stick.")
        print("The data directory should contain ChordPro files (.chopro, .cho, .crd)")
        return 1

    # Create and run application
    app = StageCheater(config, data_source)
    try:
        app.setup()
        app.run()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
