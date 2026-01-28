#!/bin/bash
#
# Stage-Cheater Image Builder
#
# Erstellt ein fertiges Raspberry Pi Image mit Stage-Cheater
#
# Voraussetzungen:
#   - Docker oder: sudo apt install coreutils quilt parted qemu-user-static debootstrap zerofree zip
#   - ca. 10GB freier Speicherplatz
#
# Verwendung:
#   ./build-image.sh              # 64-bit für Pi 3/4/5 (Standard)
#   ./build-image.sh --pi2        # 32-bit für Pi 2B
#   ./build-image.sh --clean      # Build-Verzeichnis löschen
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$SCRIPT_DIR/pi-gen"

# Default: 64-bit für Pi 3/4/5
PI_BRANCH="arm64"
PI_ARCH="arm64"
IMG_SUFFIX=""

echo "==================================="
echo " Stage-Cheater Image Builder"
echo "==================================="
echo

# Handle arguments
for arg in "$@"; do
    case $arg in
        --clean)
            echo "Lösche pi-gen Verzeichnis..."
            rm -rf "$BUILD_DIR"
            echo "Fertig. Starte Build erneut ohne --clean"
            exit 0
            ;;
        --pi2|--armhf|--32bit)
            PI_BRANCH="master"
            PI_ARCH="armhf"
            IMG_SUFFIX="-pi2"
            echo "Build für Raspberry Pi 2B (32-bit armhf)"
            ;;
        --pi3|--pi4|--pi5|--arm64|--64bit)
            PI_BRANCH="arm64"
            PI_ARCH="arm64"
            IMG_SUFFIX=""
            echo "Build für Raspberry Pi 3/4/5 (64-bit arm64)"
            ;;
        --help|-h)
            echo "Verwendung: ./build-image.sh [OPTION]"
            echo
            echo "Optionen:"
            echo "  --pi2, --armhf, --32bit   32-bit Image für Pi 2B"
            echo "  --pi3, --arm64, --64bit   64-bit Image für Pi 3/4/5 (Standard)"
            echo "  --clean                    Build-Verzeichnis löschen"
            echo
            echo "Umgebungsvariablen:"
            echo "  USE_DOCKER=1              Mit Docker bauen (empfohlen)"
            exit 0
            ;;
    esac
done

echo "Architektur: $PI_ARCH"
echo

# Check if running as root for non-docker build
if [ "$USE_DOCKER" != "1" ] && [ "$EUID" -ne 0 ]; then
    echo "Für Build ohne Docker: sudo ./build-image.sh"
    echo "Für Build mit Docker:  USE_DOCKER=1 ./build-image.sh"
    exit 1
fi

# Clone pi-gen if not exists or wrong branch
if [ ! -d "$BUILD_DIR" ]; then
    echo "Klone pi-gen ($PI_BRANCH branch)..."
    git clone --branch "$PI_BRANCH" https://github.com/RPi-Distro/pi-gen.git "$BUILD_DIR"
else
    # Check if correct branch
    cd "$BUILD_DIR"
    CURRENT_BRANCH=$(git branch --show-current)
    if [ "$CURRENT_BRANCH" != "$PI_BRANCH" ]; then
        echo "Wechsle pi-gen Branch zu $PI_BRANCH..."
        git fetch origin
        git checkout "$PI_BRANCH"
        git pull
    fi
    cd "$SCRIPT_DIR"
fi

cd "$BUILD_DIR"

# Clean previous build
if [ -d "work" ]; then
    echo "Räume vorherigen Build auf..."
    rm -rf work
fi

# Create config (ohne RELEASE - pi-gen nutzt den Default des Branches)
echo "Erstelle Konfiguration..."
cat > config <<EOF
IMG_NAME=stage-cheater${IMG_SUFFIX}
DEPLOY_ZIP=1
LOCALE_DEFAULT=de_DE.UTF-8
KEYBOARD_KEYMAP=de
KEYBOARD_LAYOUT="German"
TIMEZONE_DEFAULT=Europe/Berlin
FIRST_USER_NAME=pi
FIRST_USER_PASS=stagecheater
ENABLE_SSH=1
TARGET_HOSTNAME=stage-cheater
APT_PROXY=""
DEBOOTSTRAP_KEYRING=/usr/share/keyrings/raspberrypi-archive-keyring.gpg
EOF

# Skip stages we don't need (desktop etc.)
touch ./stage3/SKIP ./stage4/SKIP ./stage5/SKIP
touch ./stage4/SKIP_IMAGES ./stage5/SKIP_IMAGES

# Create custom stage
STAGE_DIR="./stage2-stage-cheater"
rm -rf "$STAGE_DIR"
mkdir -p "$STAGE_DIR"

# Copy project files
echo "Kopiere Projektdateien..."
mkdir -p "$STAGE_DIR/files/stage-cheater"
cp -r "$PROJECT_DIR/src" "$STAGE_DIR/files/stage-cheater/"
cp -r "$PROJECT_DIR/examples" "$STAGE_DIR/files/stage-cheater/"
cp -r "$PROJECT_DIR/tests" "$STAGE_DIR/files/stage-cheater/"
cp "$PROJECT_DIR/pyproject.toml" "$STAGE_DIR/files/stage-cheater/"
cp "$PROJECT_DIR/install.sh" "$STAGE_DIR/files/stage-cheater/"
cp "$PROJECT_DIR/README.md" "$STAGE_DIR/files/stage-cheater/" 2>/dev/null || true

# Create package list
cat > "$STAGE_DIR/00-packages" <<EOF
python3
python3-venv
python3-pip
python3-pygame
python3-gpiozero
python3-lgpio
python3-rpi.gpio
python3-pigpio
libsdl2-2.0-0
libsdl2-ttf-2.0-0
libsdl2-image-2.0-0
git
EOF

# Create install script
cat > "$STAGE_DIR/01-install.sh" <<'INSTALL_SCRIPT'
#!/bin/bash -e

# Install Stage-Cheater
on_chroot <<CHROOT
# Copy files to home directory
cp -r /tmp/files/stage-cheater /home/pi/stage-cheater
chown -R pi:pi /home/pi/stage-cheater

# Create virtual environment with system packages
sudo -u pi python3 -m venv --system-site-packages /home/pi/stage-cheater/.venv

# Install package
cd /home/pi/stage-cheater
sudo -u pi /home/pi/stage-cheater/.venv/bin/pip install -e . --quiet

# Create start script
cat > /home/pi/stage-cheater/start.sh <<'STARTSCRIPT'
#!/bin/bash
SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
export SDL_VIDEODRIVER=kmsdrm
export SDL_RENDER_DRIVER=opengles2
source "\$SCRIPT_DIR/.venv/bin/activate"
exec stage-cheater "\$@"
STARTSCRIPT
chmod +x /home/pi/stage-cheater/start.sh

# Create systemd service for autostart
cat > /etc/systemd/system/stage-cheater.service <<'SERVICE'
[Unit]
Description=Stage-Cheater Teleprompter
After=multi-user.target
Wants=multi-user.target

[Service]
Type=simple
User=pi
Group=pi
Environment=SDL_VIDEODRIVER=kmsdrm
Environment=SDL_RENDER_DRIVER=opengles2
WorkingDirectory=/home/pi/stage-cheater
ExecStart=/home/pi/stage-cheater/start.sh
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICE

# Enable autostart
systemctl enable stage-cheater.service

# Add user to required groups
usermod -aG video,render,input,gpio pi

# Configure for console boot (no desktop)
systemctl set-default multi-user.target

# Disable screen blanking
cat >> /etc/rc.local <<'RCLOCAL'
# Disable screen blanking
setterm -blank 0 -powerdown 0 -powersave off </dev/tty1
RCLOCAL

# Create udev rule for USB auto-mount
cat > /etc/udev/rules.d/99-usb-mount.rules <<'UDEV'
ACTION=="add", KERNEL=="sd[a-z][0-9]", TAG+="systemd", ENV{SYSTEMD_WANTS}="usb-mount@%k.service"
ACTION=="remove", KERNEL=="sd[a-z][0-9]", TAG+="systemd"
UDEV

# Create USB mount service
cat > /etc/systemd/system/usb-mount@.service <<'USBMOUNT'
[Unit]
Description=Mount USB Drive %i
After=multi-user.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/mkdir -p /media/usb-%i
ExecStart=/bin/mount /dev/%i /media/usb-%i -o uid=pi,gid=pi,umask=0022
ExecStop=/bin/umount /media/usb-%i
ExecStop=/bin/rmdir /media/usb-%i
USBMOUNT

# Reload systemd
systemctl daemon-reload

CHROOT
INSTALL_SCRIPT

chmod +x "$STAGE_DIR/01-install.sh"

# Create stage dependencies
echo "stage2" > "$STAGE_DIR/depends"

# Copy files to tmp in stage
cat > "$STAGE_DIR/00-copy-files.sh" <<'COPY_SCRIPT'
#!/bin/bash -e
install -d "${ROOTFS_DIR}/tmp/files"
cp -r "${STAGE_DIR}/files/"* "${ROOTFS_DIR}/tmp/files/"
COPY_SCRIPT
chmod +x "$STAGE_DIR/00-copy-files.sh"

# Fix GPG key issue in Docker build
if [ "$USE_DOCKER" = "1" ]; then
    echo "Patche Dockerfile für aktuelle GPG-Keys..."

    # Create custom Dockerfile that updates keyrings
    if [ ! -f Dockerfile.orig ]; then
        cp Dockerfile Dockerfile.orig
    fi

    cat > Dockerfile <<'DOCKERFILE'
ARG BASE_IMAGE=debian:bookworm
FROM ${BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies
RUN apt-get -y update && \
    apt-get -y install --no-install-recommends \
        git vim parted \
        quilt coreutils qemu-user-static debootstrap zerofree zip dosfstools e2fsprogs\
        libarchive-tools libcap2-bin rsync grep udev xz-utils curl xxd file kmod bc \
        binfmt-support ca-certificates fdisk gpg pigz arch-test \
    && rm -rf /var/lib/apt/lists/*

# Download and install latest Raspberry Pi keyring and make it available everywhere
RUN curl -fsSL http://archive.raspberrypi.com/debian/pool/main/r/raspberrypi-archive-keyring/raspberrypi-archive-keyring_2025.1+rpt1_all.deb -o /tmp/keyring.deb && \
    dpkg -i /tmp/keyring.deb && \
    rm /tmp/keyring.deb && \
    # Create symlinks for all possible keyring names debootstrap might look for
    ln -sf /usr/share/keyrings/raspberrypi-archive-keyring.gpg /usr/share/keyrings/raspbian-archive-keyring.gpg && \
    cp /usr/share/keyrings/raspberrypi-archive-keyring.gpg /etc/apt/trusted.gpg.d/ && \
    # Also import into apt keyring
    gpg --no-default-keyring --keyring /usr/share/keyrings/raspbian-archive-keyring.gpg --export | apt-key add - 2>/dev/null || true

COPY . /pi-gen/

# Workaround: Add --no-check-gpg to BOOTSTRAP_ARGS (Raspbian key issue)
RUN sed -i '/BOOTSTRAP_ARGS+=(--keyring/a\    BOOTSTRAP_ARGS+=(--no-check-gpg)' /pi-gen/scripts/common

VOLUME [ "/pi-gen/work", "/pi-gen/deploy"]
DOCKERFILE

    # Force rebuild of Docker image
    docker rmi pi-gen 2>/dev/null || true
fi

# Build
echo
echo "Starte Image-Build..."
echo "Dies kann 30-60 Minuten dauern..."
echo

if [ "$USE_DOCKER" = "1" ]; then
    ./build-docker.sh
else
    ./build.sh
fi

echo
echo "==================================="
echo " Build abgeschlossen!"
echo "==================================="
echo
echo "Image: $BUILD_DIR/deploy/"
ls -la "$BUILD_DIR/deploy/"*.zip 2>/dev/null || echo "Siehe deploy/ Verzeichnis"
