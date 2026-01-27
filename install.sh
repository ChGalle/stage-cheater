#!/bin/bash
#
# Stage-Cheater Installation Script
#
# Usage:
#   ./install.sh          - Full installation
#   ./install.sh --usb    - Copy example data to USB stick
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# Check Python version
check_python() {
    echo -e "${YELLOW}Prüfe Python-Version...${NC}"

    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
        PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

        if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 11 ]; then
            echo -e "${GREEN}✓ Python $PYTHON_VERSION gefunden${NC}"
            return 0
        else
            echo -e "${RED}✗ Python $PYTHON_VERSION gefunden, aber 3.11+ wird benötigt${NC}"
            return 1
        fi
    else
        echo -e "${RED}✗ Python3 nicht gefunden${NC}"
        return 1
    fi
}

# Check if running on Raspberry Pi
is_raspberry_pi() {
    if [ -f /proc/device-tree/model ]; then
        grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null
        return $?
    fi
    return 1
}

# Create virtual environment
create_venv() {
    echo
    echo -e "${YELLOW}Erstelle virtuelle Umgebung...${NC}"

    if [ -d "$VENV_DIR" ]; then
        echo -e "${YELLOW}Virtuelle Umgebung existiert bereits${NC}"
        read -p "Neu erstellen? (j/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Jj]$ ]]; then
            rm -rf "$VENV_DIR"
            python3 -m venv "$VENV_DIR"
        fi
    else
        python3 -m venv "$VENV_DIR"
    fi

    echo -e "${GREEN}✓ Virtuelle Umgebung erstellt${NC}"
}

# Install system dependencies on Raspberry Pi
install_pi_system_deps() {
    echo
    echo -e "${YELLOW}Installiere System-Abhängigkeiten für Raspberry Pi...${NC}"

    # Install build dependencies and GPIO packages
    echo -e "${YELLOW}Installiere System-Pakete (benötigt sudo)...${NC}"
    sudo apt-get update -qq
    sudo apt-get install -y -qq \
        swig \
        python3-dev \
        python3-lgpio \
        python3-rpi-lgpio \
        libgpiod-dev \
        2>/dev/null || true

    echo -e "${GREEN}✓ System-Pakete installiert${NC}"
}

# Install package
install_package() {
    echo
    echo -e "${YELLOW}Installiere Stage-Cheater...${NC}"

    source "$VENV_DIR/bin/activate"

    if is_raspberry_pi; then
        echo -e "${YELLOW}Raspberry Pi erkannt - installiere mit GPIO-Unterstützung${NC}"
        install_pi_system_deps
        pip install -e ".[pi]" --quiet
    else
        pip install -e "." --quiet
    fi

    echo -e "${GREEN}✓ Stage-Cheater installiert${NC}"
}

# Create launcher script
create_launcher() {
    echo
    echo -e "${YELLOW}Erstelle Starter-Script...${NC}"

    cat > "$SCRIPT_DIR/start.sh" << 'LAUNCHER'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/.venv/bin/activate"
exec stage-cheater "$@"
LAUNCHER

    chmod +x "$SCRIPT_DIR/start.sh"
    echo -e "${GREEN}✓ start.sh erstellt${NC}"
}

# Setup systemd service (optional, Raspberry Pi only)
setup_systemd() {
    if ! is_raspberry_pi; then
        return
    fi

    echo
    read -p "Systemd-Service für Autostart einrichten? (j/N) " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Jj]$ ]]; then
        return
    fi

    SERVICE_FILE="/etc/systemd/system/stage-cheater.service"
    CURRENT_USER=$(whoami)

    echo -e "${YELLOW}Erstelle Systemd-Service...${NC}"

    sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=Stage-Cheater Teleprompter
After=graphical.target

[Service]
User=$CURRENT_USER
Environment=DISPLAY=:0
WorkingDirectory=$SCRIPT_DIR
ExecStart=$SCRIPT_DIR/start.sh
Restart=on-failure
RestartSec=5

[Install]
WantedBy=graphical.target
EOF

    sudo systemctl daemon-reload

    read -p "Service jetzt aktivieren (startet bei Boot)? (j/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Jj]$ ]]; then
        sudo systemctl enable stage-cheater
        echo -e "${GREEN}✓ Autostart aktiviert${NC}"
    fi

    echo -e "${GREEN}✓ Systemd-Service erstellt${NC}"
    echo
    echo "Service-Befehle:"
    echo "  sudo systemctl start stage-cheater   # Starten"
    echo "  sudo systemctl stop stage-cheater    # Stoppen"
    echo "  sudo systemctl status stage-cheater  # Status"
    echo "  journalctl -u stage-cheater -f       # Logs"
}

# Find mounted USB sticks
find_usb_sticks() {
    local usb_sticks=()

    # Check common mount points
    for base in /media /mnt /run/media; do
        if [ -d "$base" ]; then
            # Look for mounted directories
            for user_dir in "$base"/*; do
                if [ -d "$user_dir" ]; then
                    # Check if it's a mount point with different device
                    for mount_dir in "$user_dir"/*; do
                        if [ -d "$mount_dir" ] && mountpoint -q "$mount_dir" 2>/dev/null; then
                            usb_sticks+=("$mount_dir")
                        fi
                    done
                    # Also check if user_dir itself is a mount
                    if mountpoint -q "$user_dir" 2>/dev/null; then
                        usb_sticks+=("$user_dir")
                    fi
                fi
            done
        fi
    done

    printf '%s\n' "${usb_sticks[@]}"
}

# Copy example data to USB stick
copy_to_usb() {
    echo -e "${GREEN}================================${NC}"
    echo -e "${GREEN} Beispieldaten auf USB kopieren${NC}"
    echo -e "${GREEN}================================${NC}"
    echo

    # Find USB sticks
    mapfile -t usb_sticks < <(find_usb_sticks)

    if [ ${#usb_sticks[@]} -eq 0 ]; then
        echo -e "${RED}Kein USB-Stick gefunden!${NC}"
        echo
        echo "Bitte USB-Stick einstecken und erneut versuchen."
        echo "Oder Zielpfad direkt angeben:"
        echo "  ./install.sh --usb /pfad/zum/ziel"
        exit 1
    fi

    local target=""

    if [ ${#usb_sticks[@]} -eq 1 ]; then
        target="${usb_sticks[0]}"
        echo -e "Gefundener USB-Stick: ${BLUE}$target${NC}"
        read -p "Beispieldaten hierhin kopieren? (J/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            echo "Abgebrochen."
            exit 0
        fi
    else
        echo "Mehrere USB-Sticks gefunden:"
        echo
        for i in "${!usb_sticks[@]}"; do
            echo "  $((i+1))) ${usb_sticks[$i]}"
        done
        echo
        read -p "Auswahl (1-${#usb_sticks[@]}): " choice

        if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le ${#usb_sticks[@]} ]; then
            target="${usb_sticks[$((choice-1))]}"
        else
            echo -e "${RED}Ungültige Auswahl${NC}"
            exit 1
        fi
    fi

    copy_examples_to "$target"
}

# Copy example files to target directory
copy_examples_to() {
    local target="$1"

    echo
    echo -e "${YELLOW}Kopiere Beispieldaten nach: $target${NC}"

    # Create directory structure
    mkdir -p "$target/songs"
    mkdir -p "$target/playlists"

    # Copy example songs
    if [ -d "$SCRIPT_DIR/examples/songs" ]; then
        cp "$SCRIPT_DIR/examples/songs"/*.chopro "$target/songs/" 2>/dev/null || true
        echo -e "${GREEN}✓ Beispiel-Songs kopiert${NC}"
    fi

    # Copy example playlist
    if [ -f "$SCRIPT_DIR/examples/setlist.txt" ]; then
        cp "$SCRIPT_DIR/examples/setlist.txt" "$target/playlists/"
        echo -e "${GREEN}✓ Beispiel-Playlist kopiert${NC}"
    fi

    # Copy example config
    if [ -f "$SCRIPT_DIR/examples/config.toml" ]; then
        cp "$SCRIPT_DIR/examples/config.toml" "$target/"
        echo -e "${GREEN}✓ Beispiel-Konfiguration kopiert${NC}"
    fi

    echo
    echo -e "${GREEN}================================${NC}"
    echo -e "${GREEN} Fertig!${NC}"
    echo -e "${GREEN}================================${NC}"
    echo
    echo "USB-Stick Struktur:"
    echo
    echo "  $target/"
    echo "  ├── config.toml        <- Einstellungen anpassen"
    echo "  ├── songs/"
    echo "  │   ├── amazing_grace.chopro"
    echo "  │   └── house_of_the_rising_sun.chopro"
    echo "  └── playlists/"
    echo "      └── setlist.txt    <- Song-Reihenfolge anpassen"
    echo
    echo "Nächste Schritte:"
    echo "  1. Eigene .chopro Dateien in songs/ ablegen"
    echo "  2. setlist.txt mit gewünschter Reihenfolge anpassen"
    echo "  3. Optional: config.toml für Display-Einstellungen"
    echo
}

# Print usage info
print_usage() {
    echo
    echo -e "${GREEN}================================${NC}"
    echo -e "${GREEN} Installation abgeschlossen!${NC}"
    echo -e "${GREEN}================================${NC}"
    echo
    echo "Nutzung:"
    echo
    echo "  1. Direkt starten:"
    echo "     ./start.sh -d examples/songs"
    echo
    echo "  2. Mit eigenen Songs:"
    echo "     ./start.sh -d /pfad/zu/songs"
    echo
    echo "  3. Mit USB-Stick (wird automatisch erkannt):"
    echo "     ./start.sh"
    echo
    echo "  4. Einzelne Datei:"
    echo "     ./start.sh -f /pfad/zu/song.chopro"
    echo
    echo "  5. Beispieldaten auf USB-Stick kopieren:"
    echo "     ./install.sh --usb"
    echo
    echo "Steuerung:"
    echo "  Pfeiltasten / Space / PageUp/Down - Navigation"
    echo "  +/- - Zoom"
    echo "  ESC/q - Beenden"
    echo
}

# Show help
show_help() {
    echo "Stage-Cheater Installations-Script"
    echo
    echo "Verwendung:"
    echo "  ./install.sh              Vollständige Installation"
    echo "  ./install.sh --usb        Beispieldaten auf USB-Stick kopieren"
    echo "  ./install.sh --usb PATH   Beispieldaten in Verzeichnis kopieren"
    echo "  ./install.sh --help       Diese Hilfe anzeigen"
    echo
}

# Main installation
main_install() {
    echo -e "${GREEN}================================${NC}"
    echo -e "${GREEN} Stage-Cheater Installation${NC}"
    echo -e "${GREEN}================================${NC}"
    echo

    if ! check_python; then
        echo
        echo -e "${RED}Bitte installiere Python 3.11 oder höher:${NC}"
        echo "  sudo apt update && sudo apt install python3.11 python3.11-venv"
        exit 1
    fi

    create_venv
    install_package
    create_launcher
    setup_systemd
    print_usage
}

# Main entry point
main() {
    cd "$SCRIPT_DIR"

    case "${1:-}" in
        --help|-h)
            show_help
            ;;
        --usb)
            if [ -n "${2:-}" ] && [ -d "$2" ]; then
                copy_examples_to "$2"
            else
                copy_to_usb
            fi
            ;;
        "")
            main_install
            ;;
        *)
            echo -e "${RED}Unbekannte Option: $1${NC}"
            echo
            show_help
            exit 1
            ;;
    esac
}

main "$@"
