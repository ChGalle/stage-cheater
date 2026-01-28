# Stage-Cheater Image Builder

Erstellt ein fertiges Raspberry Pi Image mit vorinstalliertem Stage-Cheater.

## Voraussetzungen

### Mit Docker (empfohlen)

```bash
sudo apt install docker.io
sudo usermod -aG docker $USER
# Neu einloggen
```

### Ohne Docker

```bash
sudo apt install coreutils quilt parted qemu-user-static debootstrap zerofree zip dosfstools libarchive-tools libcap2-bin rsync grep udev xz-utils curl git
```

## Image bauen

### Raspberry Pi 3/4/5 (64-bit, Standard)

```bash
USE_DOCKER=1 ./build-image.sh
```

### Raspberry Pi 2B (32-bit)

```bash
USE_DOCKER=1 ./build-image.sh --pi2
```

### Ohne Docker (als root)

```bash
sudo ./build-image.sh           # 64-bit
sudo ./build-image.sh --pi2     # 32-bit
```

Der Build dauert ca. 30-60 Minuten.

## Ergebnis

Das fertige Image liegt in `pi-gen/deploy/`:
- `image_stage-cheater.zip` - Komprimiertes Image

## Image auf SD-Karte schreiben

```bash
# Image entpacken
unzip image_stage-cheater.zip

# Auf SD-Karte schreiben (ACHTUNG: richtiges Device!)
sudo dd if=stage-cheater.img of=/dev/sdX bs=4M status=progress
sync
```

Oder mit dem Raspberry Pi Imager:
1. "Use custom" wählen
2. .img Datei auswählen
3. SD-Karte auswählen
4. Schreiben

## Was ist im Image enthalten?

- Raspberry Pi OS Lite (Bookworm)
- Stage-Cheater vorinstalliert
- Autostart beim Booten
- Deutsche Tastatur/Locale
- SSH aktiviert
- USB-Stick Auto-Mount

## Standard-Zugangsdaten

- Benutzer: `pi`
- Passwort: `stagecheater`
- Hostname: `stage-cheater`

## Nutzung

1. SD-Karte in Pi einlegen
2. USB-Stick mit Songs einstecken (optional)
3. Monitor anschließen
4. Einschalten - Stage-Cheater startet automatisch

### USB-Stick Struktur

```
USB-Stick/
├── config.toml      # Optional: Einstellungen
├── songs/
│   └── *.chopro     # ChordPro Dateien
└── playlists/
    └── setlist.txt  # Song-Reihenfolge
```

### Service steuern

```bash
# Status
sudo systemctl status stage-cheater

# Stoppen
sudo systemctl stop stage-cheater

# Starten
sudo systemctl start stage-cheater

# Logs
journalctl -u stage-cheater -f
```

## Anpassungen

### Passwort ändern

Nach dem ersten Boot:
```bash
passwd
```

### WLAN einrichten (optional)

```bash
sudo raspi-config
# -> System Options -> Wireless LAN
```

### SSH-Zugang

SSH ist standardmäßig aktiviert:
```bash
ssh pi@stage-cheater.local
```
