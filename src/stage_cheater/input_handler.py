"""Input handling for Stage-Cheater (Keyboard + GPIO)."""

from enum import Enum, auto
from typing import Callable
import pygame

from .config import Config


class Action(Enum):
    """Possible user actions."""
    NONE = auto()
    NEXT_PAGE = auto()
    PREV_PAGE = auto()
    NEXT_SONG = auto()
    PREV_SONG = auto()
    ZOOM_IN = auto()
    ZOOM_OUT = auto()
    QUIT = auto()


# Mapping of key name strings to Pygame key constants
KEY_MAP = {
    "RIGHT": pygame.K_RIGHT,
    "LEFT": pygame.K_LEFT,
    "UP": pygame.K_UP,
    "DOWN": pygame.K_DOWN,
    "SPACE": pygame.K_SPACE,
    "PAGEUP": pygame.K_PAGEUP,
    "PAGEDOWN": pygame.K_PAGEDOWN,
    "ESCAPE": pygame.K_ESCAPE,
    "RETURN": pygame.K_RETURN,
    "ENTER": pygame.K_RETURN,
    "TAB": pygame.K_TAB,
    "PLUS": pygame.K_PLUS,
    "MINUS": pygame.K_MINUS,
    "KP_PLUS": pygame.K_KP_PLUS,
    "KP_MINUS": pygame.K_KP_MINUS,
    "EQUALS": pygame.K_EQUALS,  # Often used for + without shift
    "q": pygame.K_q,
    "Q": pygame.K_q,
    "a": pygame.K_a,
    "d": pygame.K_d,
    "w": pygame.K_w,
    "s": pygame.K_s,
}


class KeyboardHandler:
    """Handle keyboard input via Pygame events."""

    def __init__(self, config: Config):
        self.config = config
        self._key_actions: dict[int, Action] = {}
        self._setup_key_mappings()

    def _setup_key_mappings(self) -> None:
        """Setup key to action mappings from config."""
        kbd_config = self.config.input.keyboard

        for key_name in kbd_config.next_page:
            if key_name in KEY_MAP:
                self._key_actions[KEY_MAP[key_name]] = Action.NEXT_PAGE

        for key_name in kbd_config.prev_page:
            if key_name in KEY_MAP:
                self._key_actions[KEY_MAP[key_name]] = Action.PREV_PAGE

        for key_name in kbd_config.next_song:
            if key_name in KEY_MAP:
                self._key_actions[KEY_MAP[key_name]] = Action.NEXT_SONG

        for key_name in kbd_config.prev_song:
            if key_name in KEY_MAP:
                self._key_actions[KEY_MAP[key_name]] = Action.PREV_SONG

        for key_name in kbd_config.quit:
            if key_name in KEY_MAP:
                self._key_actions[KEY_MAP[key_name]] = Action.QUIT

        for key_name in kbd_config.zoom_in:
            if key_name in KEY_MAP:
                self._key_actions[KEY_MAP[key_name]] = Action.ZOOM_IN

        for key_name in kbd_config.zoom_out:
            if key_name in KEY_MAP:
                self._key_actions[KEY_MAP[key_name]] = Action.ZOOM_OUT

    def handle_event(self, event: pygame.event.Event) -> Action:
        """Handle a Pygame event and return the corresponding action."""
        if event.type == pygame.KEYDOWN:
            return self._key_actions.get(event.key, Action.NONE)
        return Action.NONE


class GPIOHandler:
    """Handle GPIO input for foot pedals (Raspberry Pi only)."""

    def __init__(self, config: Config, on_action: Callable[[Action], None]):
        self.config = config
        self._on_action = on_action
        self._buttons: dict[int, "Button"] = {}
        self._enabled = config.input.gpio.enabled

        if self._enabled:
            self._setup_gpio()

    def _setup_gpio(self) -> None:
        """Setup GPIO buttons."""
        try:
            from gpiozero import Button
        except ImportError:
            print("Warning: gpiozero not available, GPIO input disabled")
            self._enabled = False
            return

        gpio_config = self.config.input.gpio

        # Setup next page button
        next_btn = Button(gpio_config.next_page_pin, bounce_time=0.1)
        next_btn.when_pressed = lambda: self._on_action(Action.NEXT_PAGE)
        self._buttons[gpio_config.next_page_pin] = next_btn

        # Setup prev page button
        prev_btn = Button(gpio_config.prev_page_pin, bounce_time=0.1)
        prev_btn.when_pressed = lambda: self._on_action(Action.PREV_PAGE)
        self._buttons[gpio_config.prev_page_pin] = prev_btn

    def cleanup(self) -> None:
        """Cleanup GPIO resources."""
        for button in self._buttons.values():
            button.close()
        self._buttons.clear()

    @property
    def enabled(self) -> bool:
        return self._enabled


class InputHandler:
    """Combined input handler for keyboard and GPIO."""

    def __init__(self, config: Config):
        self.config = config
        self.keyboard = KeyboardHandler(config)
        self._pending_gpio_actions: list[Action] = []
        self.gpio: GPIOHandler | None = None

        # GPIO handler will call this when a button is pressed
        if config.input.gpio.enabled:
            self.gpio = GPIOHandler(config, self._queue_gpio_action)

    def _queue_gpio_action(self, action: Action) -> None:
        """Queue a GPIO action for processing in the main loop."""
        self._pending_gpio_actions.append(action)
        # Post a custom event to wake up the Pygame event loop
        pygame.event.post(pygame.event.Event(pygame.USEREVENT, {"gpio_action": action}))

    def handle_event(self, event: pygame.event.Event) -> Action:
        """Handle an event and return the corresponding action."""
        # Check for GPIO action
        if event.type == pygame.USEREVENT and hasattr(event, "gpio_action"):
            return event.gpio_action

        # Handle keyboard event
        return self.keyboard.handle_event(event)

    def get_pending_gpio_action(self) -> Action:
        """Get and clear any pending GPIO action."""
        if self._pending_gpio_actions:
            return self._pending_gpio_actions.pop(0)
        return Action.NONE

    def cleanup(self) -> None:
        """Cleanup resources."""
        if self.gpio:
            self.gpio.cleanup()
