"""Tests for menu system."""

import pytest
from pathlib import Path

from stage_cheater.menu import (
    MenuState,
    MenuController,
    MenuItem,
    PlaylistSummary,
)


class TestMenuState:
    """Tests for MenuState enum."""

    def test_states_exist(self):
        """Test all required states exist."""
        assert MenuState.HIDDEN
        assert MenuState.PLAYLIST_SELECT
        assert MenuState.SONG_SELECT


class TestPlaylistSummary:
    """Tests for PlaylistSummary dataclass."""

    def test_creation(self):
        """Test creating a PlaylistSummary."""
        summary = PlaylistSummary(
            name="Jazz Standards",
            path=Path("/music/playlists/jazz.lst"),
            song_count=15
        )
        assert summary.name == "Jazz Standards"
        assert summary.path == Path("/music/playlists/jazz.lst")
        assert summary.song_count == 15


class TestMenuItem:
    """Tests for MenuItem dataclass."""

    def test_regular_item(self):
        """Test creating a regular menu item."""
        item = MenuItem(label="Song Title", value="song1")
        assert item.label == "Song Title"
        assert item.value == "song1"
        assert item.is_back is False

    def test_back_item(self):
        """Test creating a back menu item."""
        item = MenuItem(label="[Zurück]", is_back=True)
        assert item.label == "[Zurück]"
        assert item.is_back is True


class TestMenuController:
    """Tests for MenuController."""

    @pytest.fixture
    def controller(self):
        """Create a MenuController with test data."""
        ctrl = MenuController()
        playlists = [
            PlaylistSummary("All Songs", Path("/music"), 50),
            PlaylistSummary("Jazz", Path("/music/jazz.lst"), 10),
            PlaylistSummary("Rock", Path("/music/rock.lst"), 20),
        ]
        ctrl.set_playlists(playlists)
        return ctrl

    @pytest.fixture
    def controller_single_playlist(self):
        """Create a MenuController with single playlist."""
        ctrl = MenuController()
        playlists = [
            PlaylistSummary("All Songs", Path("/music"), 50),
        ]
        ctrl.set_playlists(playlists)
        return ctrl

    def test_initial_state(self, controller):
        """Test initial state is hidden."""
        assert controller.state == MenuState.HIDDEN
        assert controller.is_active is False

    def test_toggle_menu_opens_playlist_select(self, controller):
        """Test toggle opens playlist menu when multiple playlists."""
        controller.toggle_menu()
        assert controller.state == MenuState.PLAYLIST_SELECT
        assert controller.is_active is True

    def test_toggle_menu_opens_song_select_single_playlist(self, controller_single_playlist):
        """Test toggle opens song menu when only one playlist."""
        controller_single_playlist.toggle_menu()
        assert controller_single_playlist.state == MenuState.SONG_SELECT

    def test_toggle_menu_closes(self, controller):
        """Test toggle closes menu when open."""
        controller.toggle_menu()  # Open
        controller.toggle_menu()  # Close
        assert controller.state == MenuState.HIDDEN
        assert controller.is_active is False

    def test_close(self, controller):
        """Test explicit close."""
        controller.toggle_menu()
        controller.close()
        assert controller.state == MenuState.HIDDEN

    def test_move_up_in_playlist_menu(self, controller):
        """Test moving up in playlist menu."""
        controller.toggle_menu()
        # Start at index 0, move up should do nothing
        controller.move_up()
        assert controller.current_index == 0

        # Move to index 1, then up
        controller.move_down()
        assert controller.current_index == 1
        controller.move_up()
        assert controller.current_index == 0

    def test_move_down_in_playlist_menu(self, controller):
        """Test moving down in playlist menu."""
        controller.toggle_menu()
        assert controller.current_index == 0
        controller.move_down()
        assert controller.current_index == 1
        controller.move_down()
        assert controller.current_index == 2
        # At bottom, should not go further
        controller.move_down()
        assert controller.current_index == 2

    def test_select_playlist(self, controller):
        """Test selecting a playlist transitions to song menu."""
        controller.toggle_menu()
        controller.move_down()  # Select "Jazz"

        new_state, selected = controller.select()

        assert new_state == MenuState.SONG_SELECT
        assert controller.state == MenuState.SONG_SELECT
        assert isinstance(selected, PlaylistSummary)
        assert selected.name == "Jazz"

    def test_song_menu_navigation(self, controller):
        """Test navigation in song menu."""
        controller.toggle_menu()

        # Setup song list
        songs = [
            MenuItem(label="[Zurück]", is_back=True),
            MenuItem(label="Song 1", value=1),
            MenuItem(label="Song 2", value=2),
        ]
        controller._state = MenuState.SONG_SELECT
        controller.set_songs(songs, "Test Playlist")

        assert controller.current_index == 0
        controller.move_down()
        assert controller.current_index == 1
        controller.move_down()
        assert controller.current_index == 2
        controller.move_up()
        assert controller.current_index == 1

    def test_select_back_in_song_menu(self, controller):
        """Test selecting [Back] returns to playlist menu."""
        controller.toggle_menu()
        songs = [
            MenuItem(label="[Zurück]", is_back=True),
            MenuItem(label="Song 1", value=1),
        ]
        controller._state = MenuState.SONG_SELECT
        controller.set_songs(songs, "Test Playlist")

        # Select [Back]
        new_state, selected = controller.select()

        assert new_state == MenuState.PLAYLIST_SELECT
        assert controller.state == MenuState.PLAYLIST_SELECT
        assert selected is None

    def test_select_song(self, controller):
        """Test selecting a song closes menu and returns selection."""
        controller.toggle_menu()
        songs = [
            MenuItem(label="[Zurück]", is_back=True),
            MenuItem(label="Song 1", value=1),
        ]
        controller._state = MenuState.SONG_SELECT
        controller.set_songs(songs, "Test Playlist")

        # Navigate to Song 1
        controller.move_down()
        new_state, selected = controller.select()

        assert new_state == MenuState.HIDDEN
        assert controller.state == MenuState.HIDDEN
        assert isinstance(selected, MenuItem)
        assert selected.value == 1

    def test_go_back_from_song_menu(self, controller):
        """Test go_back from song menu returns to playlist menu."""
        controller.toggle_menu()
        controller._state = MenuState.SONG_SELECT

        controller.go_back()

        assert controller.state == MenuState.PLAYLIST_SELECT

    def test_go_back_from_playlist_menu(self, controller):
        """Test go_back from playlist menu closes menu."""
        controller.toggle_menu()
        assert controller.state == MenuState.PLAYLIST_SELECT

        controller.go_back()

        assert controller.state == MenuState.HIDDEN

    def test_go_back_single_playlist(self, controller_single_playlist):
        """Test go_back with single playlist closes menu directly."""
        controller_single_playlist.toggle_menu()
        assert controller_single_playlist.state == MenuState.SONG_SELECT

        controller_single_playlist.go_back()

        assert controller_single_playlist.state == MenuState.HIDDEN

    def test_items_property_playlist_menu(self, controller):
        """Test items property returns playlists in playlist menu."""
        controller.toggle_menu()
        items = controller.items

        assert len(items) == 3
        assert items[0].label == "All Songs"
        assert items[1].label == "Jazz"
        assert items[2].label == "Rock"

    def test_items_property_song_menu(self, controller):
        """Test items property returns songs in song menu."""
        songs = [
            MenuItem(label="[Zurück]", is_back=True),
            MenuItem(label="Song 1", value=1),
        ]
        controller._state = MenuState.SONG_SELECT
        controller.set_songs(songs, "Test")

        items = controller.items

        assert len(items) == 2
        assert items[0].label == "[Zurück]"
        assert items[1].label == "Song 1"

    def test_title_playlist_menu(self, controller):
        """Test title in playlist menu."""
        controller.toggle_menu()
        assert controller.title == "PLAYLIST AUSWÄHLEN"

    def test_title_song_menu(self, controller):
        """Test title in song menu."""
        controller._state = MenuState.SONG_SELECT
        assert controller.title == "SONG AUSWÄHLEN"

    def test_subtitle_song_menu(self, controller):
        """Test subtitle shows playlist name in song menu."""
        controller._state = MenuState.SONG_SELECT
        controller.set_songs([], "Jazz Standards")
        assert controller.subtitle == "(Jazz Standards)"

    def test_subtitle_playlist_menu(self, controller):
        """Test no subtitle in playlist menu."""
        controller.toggle_menu()
        assert controller.subtitle == ""

    def test_open_playlist_menu(self, controller):
        """Test explicit open_playlist_menu."""
        controller.open_playlist_menu()
        assert controller.state == MenuState.PLAYLIST_SELECT
        assert controller.current_index == 0

    def test_open_song_menu(self, controller):
        """Test explicit open_song_menu."""
        controller.open_song_menu()
        assert controller.state == MenuState.SONG_SELECT
        assert controller.current_index == 0
