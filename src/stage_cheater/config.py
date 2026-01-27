"""Configuration management for Stage-Cheater using TOML."""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class DisplayConfig:
    """Display-related configuration."""
    zoom: float = 1.0
    font_size: int = 32
    font_color: str = "#FFFFFF"
    background_color: str = "#000000"
    chord_color: str = "#FFFF00"
    rotation: int = 0  # 0, 90, 180, 270 degrees


@dataclass
class KeyboardInputConfig:
    """Keyboard input configuration."""
    next_page: list[str] = field(default_factory=lambda: ["RIGHT", "PAGEDOWN", "SPACE"])
    prev_page: list[str] = field(default_factory=lambda: ["LEFT", "PAGEUP"])
    next_song: list[str] = field(default_factory=lambda: ["DOWN"])
    prev_song: list[str] = field(default_factory=lambda: ["UP"])
    quit: list[str] = field(default_factory=lambda: ["ESCAPE", "q"])
    zoom_in: list[str] = field(default_factory=lambda: ["PLUS", "KP_PLUS"])
    zoom_out: list[str] = field(default_factory=lambda: ["MINUS", "KP_MINUS"])


@dataclass
class GPIOInputConfig:
    """GPIO input configuration for foot pedals."""
    enabled: bool = False
    next_page_pin: int = 17
    prev_page_pin: int = 27


@dataclass
class InputConfig:
    """Combined input configuration."""
    keyboard: KeyboardInputConfig = field(default_factory=KeyboardInputConfig)
    gpio: GPIOInputConfig = field(default_factory=GPIOInputConfig)


@dataclass
class SystemGPIOConfig:
    """GPIO configuration for system control."""
    shutdown_pin: int = 22
    restart_pin: int = 23


@dataclass
class Config:
    """Main configuration container."""
    display: DisplayConfig = field(default_factory=DisplayConfig)
    input: InputConfig = field(default_factory=InputConfig)
    system_gpio: SystemGPIOConfig = field(default_factory=SystemGPIOConfig)
    data_path: Path | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Create Config from a dictionary (parsed TOML)."""
        config = cls()

        if "display" in data:
            display_data = data["display"]
            rotation = display_data.get("rotation", config.display.rotation)
            # Normalize rotation to 0, 90, 180, 270
            rotation = int(rotation) % 360
            if rotation not in (0, 90, 180, 270):
                rotation = 0
            config.display = DisplayConfig(
                zoom=display_data.get("zoom", config.display.zoom),
                font_size=display_data.get("font_size", config.display.font_size),
                font_color=display_data.get("font_color", config.display.font_color),
                background_color=display_data.get("background_color", config.display.background_color),
                chord_color=display_data.get("chord_color", config.display.chord_color),
                rotation=rotation,
            )

        if "input" in data:
            input_data = data["input"]

            keyboard_data = input_data.get("keyboard", {})
            config.input.keyboard = KeyboardInputConfig(
                next_page=keyboard_data.get("next_page", config.input.keyboard.next_page),
                prev_page=keyboard_data.get("prev_page", config.input.keyboard.prev_page),
                next_song=keyboard_data.get("next_song", config.input.keyboard.next_song),
                prev_song=keyboard_data.get("prev_song", config.input.keyboard.prev_song),
                quit=keyboard_data.get("quit", config.input.keyboard.quit),
                zoom_in=keyboard_data.get("zoom_in", config.input.keyboard.zoom_in),
                zoom_out=keyboard_data.get("zoom_out", config.input.keyboard.zoom_out),
            )

            gpio_data = input_data.get("gpio", {})
            config.input.gpio = GPIOInputConfig(
                enabled=gpio_data.get("enabled", config.input.gpio.enabled),
                next_page_pin=gpio_data.get("next_page_pin", config.input.gpio.next_page_pin),
                prev_page_pin=gpio_data.get("prev_page_pin", config.input.gpio.prev_page_pin),
            )

        if "system" in data and "gpio" in data["system"]:
            system_gpio_data = data["system"]["gpio"]
            config.system_gpio = SystemGPIOConfig(
                shutdown_pin=system_gpio_data.get("shutdown_pin", config.system_gpio.shutdown_pin),
                restart_pin=system_gpio_data.get("restart_pin", config.system_gpio.restart_pin),
            )

        return config

    @classmethod
    def load(cls, path: Path) -> "Config":
        """Load configuration from a TOML file."""
        with open(path, "rb") as f:
            data = tomllib.load(f)
        config = cls.from_dict(data)
        config.data_path = path.parent
        return config

    @classmethod
    def load_default(cls) -> "Config":
        """Load default configuration."""
        return cls()


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color string to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
