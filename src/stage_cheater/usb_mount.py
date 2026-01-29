"""USB stick detection and mounting for Stage-Cheater."""

from pathlib import Path
from typing import Callable
import subprocess
import os


# Common USB mount points on Linux systems
COMMON_MOUNT_POINTS = [
    Path("/media"),
    Path("/mnt"),
    Path("/run/media"),
]

# Files to look for on USB stick
CONFIG_FILENAME = "config.toml"
SONGS_DIRNAME = "songs"
PLAYLISTS_DIRNAME = "playlists"


class USBDataSource:
    """Represents data found on a USB stick or directory."""

    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.config_path: Path | None = None
        self.songs_path: Path | None = None
        self.playlists_path: Path | None = None

        self._scan()

    def _scan(self) -> None:
        """Scan the root path for config, songs, and playlists."""
        # Look for config file
        config_file = self.root_path / CONFIG_FILENAME
        if config_file.exists():
            self.config_path = config_file

        # Look for songs directory
        songs_dir = self.root_path / SONGS_DIRNAME
        if songs_dir.is_dir():
            self.songs_path = songs_dir
        elif self.root_path.is_dir():
            # If no songs dir, use root as songs path
            self.songs_path = self.root_path

        # Look for playlists directory
        playlists_dir = self.root_path / PLAYLISTS_DIRNAME
        if playlists_dir.is_dir():
            self.playlists_path = playlists_dir

    @property
    def is_valid(self) -> bool:
        """Check if this is a valid data source (has songs or config)."""
        return self.songs_path is not None or self.config_path is not None

    def __repr__(self) -> str:
        return f"USBDataSource(root={self.root_path}, config={self.config_path}, songs={self.songs_path})"


def find_usb_mount_points() -> list[Path]:
    """Find all currently mounted USB drives."""
    mount_points = []

    # Check common mount point directories
    for base in COMMON_MOUNT_POINTS:
        if not base.exists():
            continue

        # On systems like Raspberry Pi OS, USB sticks are often mounted
        # under /media/<username>/<device_label>
        for user_dir in base.iterdir():
            if user_dir.is_dir():
                # First check if user_dir itself is a mount point (e.g. /media/usb)
                if _is_likely_usb_mount(user_dir):
                    mount_points.append(user_dir)
                else:
                    # Otherwise check subdirectories (e.g. /media/pi/USBSTICK)
                    for mount in user_dir.iterdir():
                        if mount.is_dir() and _is_likely_usb_mount(mount):
                            mount_points.append(mount)

    return mount_points


def _is_likely_usb_mount(path: Path) -> bool:
    """Check if a path is likely a USB mount (simple heuristic)."""
    if not path.is_dir():
        return False

    # Ignore hidden directories (like .Spotlight-V100, .TemporaryItems)
    if path.name.startswith('.'):
        return False

    # Check if it's a mount point by comparing device IDs
    try:
        path_stat = path.stat()
        parent_stat = path.parent.stat()
        # Different device = mount point
        if path_stat.st_dev != parent_stat.st_dev:
            return True
    except OSError:
        pass

    # Fallback: check if the directory has any files
    try:
        return any(path.iterdir())
    except PermissionError:
        return False


def find_data_sources() -> list[USBDataSource]:
    """Find all valid data sources on USB mounts."""
    sources = []

    for mount_point in find_usb_mount_points():
        source = USBDataSource(mount_point)
        if source.is_valid:
            sources.append(source)

    return sources


def find_first_data_source() -> USBDataSource | None:
    """Find the first valid data source."""
    sources = find_data_sources()
    return sources[0] if sources else None


class USBMonitor:
    """Monitor for USB device insertion/removal (requires pyudev)."""

    def __init__(
        self,
        on_insert: Callable[[Path], None] | None = None,
        on_remove: Callable[[Path], None] | None = None,
    ):
        self._on_insert = on_insert
        self._on_remove = on_remove
        self._monitor = None
        self._observer = None
        self._running = False

    def start(self) -> bool:
        """Start monitoring for USB events. Returns True if successful."""
        try:
            import pyudev
        except ImportError:
            print("Warning: pyudev not available, USB monitoring disabled")
            return False

        context = pyudev.Context()
        self._monitor = pyudev.Monitor.from_netlink(context)
        self._monitor.filter_by(subsystem="block", device_type="partition")

        self._observer = pyudev.MonitorObserver(
            self._monitor,
            callback=self._handle_event,
        )
        self._observer.start()
        self._running = True
        return True

    def stop(self) -> None:
        """Stop monitoring for USB events."""
        if self._observer:
            self._observer.stop()
            self._observer = None
        self._running = False

    def _handle_event(self, action: str, device) -> None:
        """Handle a udev event."""
        # Get mount point from device
        mount_point = self._get_mount_point(device)
        if not mount_point:
            return

        if action == "add" and self._on_insert:
            self._on_insert(mount_point)
        elif action == "remove" and self._on_remove:
            self._on_remove(mount_point)

    def _get_mount_point(self, device) -> Path | None:
        """Get the mount point for a device."""
        # Try to get mount point from device properties
        device_node = device.device_node
        if not device_node:
            return None

        # Read /proc/mounts to find mount point
        try:
            with open("/proc/mounts", "r") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2 and parts[0] == device_node:
                        return Path(parts[1])
        except OSError:
            pass

        return None

    @property
    def running(self) -> bool:
        return self._running
