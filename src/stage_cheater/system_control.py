"""System control (shutdown/restart) via GPIO for Stage-Cheater."""

import subprocess
import sys
from typing import Callable

from .config import Config


class SystemControl:
    """Handle system shutdown and restart via GPIO buttons."""

    def __init__(
        self,
        config: Config,
        on_shutdown_requested: Callable[[], None] | None = None,
        on_restart_requested: Callable[[], None] | None = None,
    ):
        self.config = config
        self._on_shutdown_requested = on_shutdown_requested
        self._on_restart_requested = on_restart_requested
        self._buttons: dict[str, "Button"] = {}
        self._enabled = False

    def setup(self) -> bool:
        """Setup GPIO buttons for system control. Returns True if successful."""
        try:
            from gpiozero import Button
        except ImportError:
            print("Warning: gpiozero not available, system GPIO control disabled")
            return False

        gpio_config = self.config.system_gpio

        # Setup shutdown button (long press detection)
        shutdown_btn = Button(
            gpio_config.shutdown_pin,
            hold_time=3,  # Require 3 second hold for shutdown
            bounce_time=0.1,
        )
        shutdown_btn.when_held = self._handle_shutdown
        self._buttons["shutdown"] = shutdown_btn

        # Setup restart button (long press detection)
        restart_btn = Button(
            gpio_config.restart_pin,
            hold_time=3,  # Require 3 second hold for restart
            bounce_time=0.1,
        )
        restart_btn.when_held = self._handle_restart
        self._buttons["restart"] = restart_btn

        self._enabled = True
        return True

    def _handle_shutdown(self) -> None:
        """Handle shutdown button press."""
        print("Shutdown requested via GPIO")
        if self._on_shutdown_requested:
            self._on_shutdown_requested()
        else:
            self.shutdown()

    def _handle_restart(self) -> None:
        """Handle restart button press."""
        print("Restart requested via GPIO")
        if self._on_restart_requested:
            self._on_restart_requested()
        else:
            self.restart()

    def cleanup(self) -> None:
        """Cleanup GPIO resources."""
        for button in self._buttons.values():
            button.close()
        self._buttons.clear()
        self._enabled = False

    @staticmethod
    def shutdown() -> None:
        """Shutdown the system."""
        print("Shutting down system...")
        try:
            subprocess.run(["sudo", "shutdown", "-h", "now"], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Shutdown failed: {e}")
        except FileNotFoundError:
            print("Shutdown command not found")

    @staticmethod
    def restart() -> None:
        """Restart the system."""
        print("Restarting system...")
        try:
            subprocess.run(["sudo", "reboot"], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Restart failed: {e}")
        except FileNotFoundError:
            print("Reboot command not found")

    @staticmethod
    def restart_application() -> None:
        """Restart the Stage-Cheater application."""
        print("Restarting application...")
        import os
        os.execv(sys.executable, [sys.executable] + sys.argv)

    @property
    def enabled(self) -> bool:
        return self._enabled
