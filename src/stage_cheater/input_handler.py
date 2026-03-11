"""Input handling for Stage-Cheater (Keyboard + GPIO)."""

import threading
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


# Map action strings to Action enum
ACTION_MAP = {
    "next_page": Action.NEXT_PAGE,
    "prev_page": Action.PREV_PAGE,
    "next_song": Action.NEXT_SONG,
    "prev_song": Action.PREV_SONG,
    "zoom_in": Action.ZOOM_IN,
    "zoom_out": Action.ZOOM_OUT,
}


class GPIOHandler:
    """Handle GPIO input for foot pedals (Raspberry Pi only).

    Supports two modes:
    - Simple mode: Two independent buttons with callbacks
    - Diode matrix mode: TC Helicon Switch 3 style, polling-based detection
    """

    POLL_INTERVAL = 0.02  # 20ms = 50 Hz

    def __init__(self, config: Config, on_action: Callable[[Action], None]):
        self.config = config
        self._on_action = on_action
        self._buttons: dict[int, "Button"] = {}
        self._enabled = config.input.gpio.enabled
        self._diode_matrix = config.input.gpio.diode_matrix

        # For diode matrix mode
        self._pin_a = None
        self._pin_b = None
        self._last_state: tuple[bool, bool] = (False, False)
        self._poll_thread: threading.Thread | None = None
        self._stop_polling = threading.Event()

        # Map config action strings to Action enum
        gpio_config = config.input.gpio
        self._switch1_action = ACTION_MAP.get(gpio_config.switch1_action, Action.NEXT_PAGE)
        self._switch2_action = ACTION_MAP.get(gpio_config.switch2_action, Action.PREV_PAGE)
        self._switch3_action = ACTION_MAP.get(gpio_config.switch3_action, Action.NEXT_SONG)

        if self._enabled:
            if self._diode_matrix:
                self._setup_diode_matrix()
            else:
                self._setup_simple_buttons()

    def _setup_simple_buttons(self) -> None:
        """Setup simple two-button mode (legacy)."""
        try:
            from gpiozero import Button
        except ImportError:
            print("Warning: gpiozero not available, GPIO input disabled")
            self._enabled = False
            return

        gpio_config = self.config.input.gpio

        # Setup button A (switch1 action)
        btn_a = Button(gpio_config.pin_a, bounce_time=0.1)
        btn_a.when_pressed = lambda: self._on_action(self._switch1_action)
        self._buttons[gpio_config.pin_a] = btn_a

        # Setup button B (switch2 action)
        btn_b = Button(gpio_config.pin_b, bounce_time=0.1)
        btn_b.when_pressed = lambda: self._on_action(self._switch2_action)
        self._buttons[gpio_config.pin_b] = btn_b

    def _setup_diode_matrix(self) -> None:
        """Setup for TC Helicon Switch 3 (diode matrix mode)."""
        try:
            from gpiozero import Button
        except ImportError:
            print("Warning: gpiozero not available, GPIO input disabled")
            self._enabled = False
            return

        gpio_config = self.config.input.gpio

        # Setup buttons without callbacks - we poll the state
        self._pin_a = Button(gpio_config.pin_a, pull_up=True, bounce_time=0.05)
        self._pin_b = Button(gpio_config.pin_b, pull_up=True, bounce_time=0.05)

        # Start polling thread
        self._stop_polling.clear()
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def _poll_loop(self) -> None:
        """Polling loop for diode matrix mode."""
        import time

        while not self._stop_polling.is_set():
            self._poll_diode_matrix()
            time.sleep(self.POLL_INTERVAL)

    def _poll_diode_matrix(self) -> None:
        """Check both pins and detect which switch was pressed."""
        if self._pin_a is None or self._pin_b is None:
            return

        a_pressed = self._pin_a.is_pressed
        b_pressed = self._pin_b.is_pressed
        current = (a_pressed, b_pressed)

        # Only react on state change (edge detection)
        if current != self._last_state:
            # Detect press (transition from released to pressed)
            was_pressed = self._last_state
            self._last_state = current

            # Only trigger on button press, not release
            if current == (True, True) and was_pressed != (True, True):
                # Both pressed = Switch 3
                self._on_action(self._switch3_action)
            elif current == (True, False) and not was_pressed[0]:
                # Only A pressed (and A was not pressed before) = Switch 1
                self._on_action(self._switch1_action)
            elif current == (False, True) and not was_pressed[1]:
                # Only B pressed (and B was not pressed before) = Switch 2
                self._on_action(self._switch2_action)

    def cleanup(self) -> None:
        """Cleanup GPIO resources."""
        # Stop polling thread
        self._stop_polling.set()
        if self._poll_thread is not None:
            self._poll_thread.join(timeout=0.1)

        # Cleanup diode matrix pins
        if self._pin_a is not None:
            self._pin_a.close()
            self._pin_a = None
        if self._pin_b is not None:
            self._pin_b.close()
            self._pin_b = None

        # Cleanup simple button mode
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
