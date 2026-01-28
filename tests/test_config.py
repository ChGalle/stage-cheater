"""Tests for configuration loading."""

import pytest
import tempfile
from pathlib import Path

from stage_cheater.config import (
    Config,
    DisplayConfig,
    KeyboardInputConfig,
    GPIOInputConfig,
    InputConfig,
    SystemGPIOConfig,
    hex_to_rgb,
)


class TestHexToRgb:
    """Tests for hex_to_rgb function."""

    def test_hex_with_hash(self):
        """Test conversion with # prefix."""
        assert hex_to_rgb("#FFFFFF") == (255, 255, 255)
        assert hex_to_rgb("#000000") == (0, 0, 0)
        assert hex_to_rgb("#FF0000") == (255, 0, 0)
        assert hex_to_rgb("#00FF00") == (0, 255, 0)
        assert hex_to_rgb("#0000FF") == (0, 0, 255)

    def test_hex_without_hash(self):
        """Test conversion without # prefix."""
        assert hex_to_rgb("FFFFFF") == (255, 255, 255)
        assert hex_to_rgb("000000") == (0, 0, 0)

    def test_hex_mixed_case(self):
        """Test conversion with mixed case."""
        assert hex_to_rgb("#ffffff") == (255, 255, 255)
        assert hex_to_rgb("#FfFfFf") == (255, 255, 255)

    def test_hex_custom_color(self):
        """Test conversion of custom colors."""
        assert hex_to_rgb("#FFFF00") == (255, 255, 0)  # Yellow
        assert hex_to_rgb("#808080") == (128, 128, 128)  # Gray


class TestDisplayConfig:
    """Tests for DisplayConfig defaults."""

    def test_defaults(self):
        """Test default values."""
        config = DisplayConfig()
        assert config.zoom == 1.0
        assert config.font_size == 32
        assert config.font_color == "#FFFFFF"
        assert config.background_color == "#000000"
        assert config.chord_color == "#FFFF00"


class TestKeyboardInputConfig:
    """Tests for KeyboardInputConfig defaults."""

    def test_defaults(self):
        """Test default key mappings."""
        config = KeyboardInputConfig()
        assert "RIGHT" in config.next_page
        assert "PAGEDOWN" in config.next_page
        assert "SPACE" in config.next_page
        assert "LEFT" in config.prev_page
        assert "ESCAPE" in config.quit


class TestGPIOInputConfig:
    """Tests for GPIOInputConfig defaults."""

    def test_defaults(self):
        """Test default GPIO settings."""
        config = GPIOInputConfig()
        assert config.enabled is False
        assert config.next_page_pin == 17
        assert config.prev_page_pin == 27


class TestSystemGPIOConfig:
    """Tests for SystemGPIOConfig defaults."""

    def test_defaults(self):
        """Test default system GPIO settings."""
        config = SystemGPIOConfig()
        assert config.shutdown_pin == 22
        assert config.restart_pin == 23


class TestConfig:
    """Tests for main Config class."""

    def test_load_default(self):
        """Test loading default configuration."""
        config = Config.load_default()
        assert config.display.zoom == 1.0
        assert config.input.gpio.enabled is False

    def test_from_dict_empty(self):
        """Test creating config from empty dict."""
        config = Config.from_dict({})
        # Should have all defaults
        assert config.display.zoom == 1.0

    def test_from_dict_partial_display(self):
        """Test creating config with partial display settings."""
        data = {
            "display": {
                "zoom": 1.5,
                "font_size": 48,
            }
        }
        config = Config.from_dict(data)
        assert config.display.zoom == 1.5
        assert config.display.font_size == 48
        # Unspecified values should have defaults
        assert config.display.font_color == "#FFFFFF"

    def test_from_dict_full_display(self):
        """Test creating config with full display settings."""
        data = {
            "display": {
                "zoom": 2.0,
                "font_size": 64,
                "font_color": "#00FF00",
                "background_color": "#333333",
                "chord_color": "#FF00FF",
            }
        }
        config = Config.from_dict(data)
        assert config.display.zoom == 2.0
        assert config.display.font_size == 64
        assert config.display.font_color == "#00FF00"
        assert config.display.background_color == "#333333"
        assert config.display.chord_color == "#FF00FF"

    def test_from_dict_keyboard_input(self):
        """Test creating config with keyboard input settings."""
        data = {
            "input": {
                "keyboard": {
                    "next_page": ["RIGHT", "SPACE"],
                    "quit": ["q"],
                }
            }
        }
        config = Config.from_dict(data)
        assert config.input.keyboard.next_page == ["RIGHT", "SPACE"]
        assert config.input.keyboard.quit == ["q"]
        # Unspecified should have defaults
        assert "LEFT" in config.input.keyboard.prev_page

    def test_from_dict_gpio_input(self):
        """Test creating config with GPIO input settings."""
        data = {
            "input": {
                "gpio": {
                    "enabled": True,
                    "next_page_pin": 5,
                    "prev_page_pin": 6,
                }
            }
        }
        config = Config.from_dict(data)
        assert config.input.gpio.enabled is True
        assert config.input.gpio.next_page_pin == 5
        assert config.input.gpio.prev_page_pin == 6

    def test_from_dict_system_gpio(self):
        """Test creating config with system GPIO settings."""
        data = {
            "system": {
                "gpio": {
                    "shutdown_pin": 10,
                    "restart_pin": 11,
                }
            }
        }
        config = Config.from_dict(data)
        assert config.system_gpio.shutdown_pin == 10
        assert config.system_gpio.restart_pin == 11

    def test_load_toml_file(self):
        """Test loading config from a TOML file."""
        toml_content = """
[display]
zoom = 1.5
font_size = 40
font_color = "#AABBCC"

[input.keyboard]
next_page = ["RIGHT", "n"]
quit = ["ESCAPE"]

[input.gpio]
enabled = true
next_page_pin = 18

[system.gpio]
shutdown_pin = 25
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            f.flush()
            temp_path = Path(f.name)

        try:
            config = Config.load(temp_path)
            assert config.display.zoom == 1.5
            assert config.display.font_size == 40
            assert config.display.font_color == "#AABBCC"
            assert config.input.keyboard.next_page == ["RIGHT", "n"]
            assert config.input.keyboard.quit == ["ESCAPE"]
            assert config.input.gpio.enabled is True
            assert config.input.gpio.next_page_pin == 18
            assert config.system_gpio.shutdown_pin == 25
            assert config.data_path == temp_path.parent
        finally:
            temp_path.unlink()

    def test_load_nonexistent_file(self):
        """Test loading from nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            Config.load(Path("/nonexistent/config.toml"))
