#!/bin/bash
#
# Stage-Cheater Installation Script
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN} Stage-Cheater Installation${NC}"
echo -e "${GREEN}================================${NC}"
echo

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

# Install package
install_package() {
    echo
    echo -e "${YELLOW}Installiere Stage-Cheater...${NC}"

    source "$VENV_DIR/bin/activate"

    if is_raspberry_pi; then
        echo -e "${YELLOW}Raspberry Pi erkannt - installiere mit GPIO-Unterstützung${NC}"
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
    echo "Steuerung:"
    echo "  Pfeiltasten / Space / PageUp/Down - Navigation"
    echo "  +/- - Zoom"
    echo "  ESC/q - Beenden"
    echo
}

# Main installation
main() {
    cd "$SCRIPT_DIR"

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

main "$@"
