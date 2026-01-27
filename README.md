# Stage-Cheater

Raspberry Pi-basierter Bühnen-Teleprompter für Songtexte und Akkorde im ChordPro-Format.

## Features

- **ChordPro-Unterstützung**: Lädt `.chopro`, `.cho`, `.crd` Dateien
- **Akkord-Anzeige**: Akkorde werden farbig über dem Text positioniert
- **Fußpedal-Steuerung**: Via Bluetooth-Keyboard oder GPIO-Pins
- **Playlist-Support**: Setlists als einfache Textdateien
- **USB-Stick**: Automatische Erkennung und Laden von Songs/Config
- **Zoom**: Einstellbare Textgröße
- **Display-Rotation**: 0°, 90°, 180°, 270° für verschiedene Monitor-Ausrichtungen
- **GPIO-Steuerung**: Shutdown/Restart über Hardware-Buttons

## Installation

### Voraussetzungen

- Python 3.11 oder höher
- Linux (getestet auf Raspberry Pi OS)

### Schnelle Installation (empfohlen)

```bash
# Repository klonen
git clone <repository-url>
cd stage-cheater

# Installationsscript ausführen
./install.sh
```

Das Script erkennt automatisch ob es auf einem Raspberry Pi läuft und installiert
entsprechend GPIO-Unterstützung. Auf dem Pi wird optional ein Systemd-Service
für Autostart angeboten.

Nach der Installation:
```bash
./start.sh -d examples/songs
```

### Manuelle Installation

```bash
# Virtuelle Umgebung erstellen und aktivieren
python3 -m venv .venv
source .venv/bin/activate

# Installieren
pip install -e .
```

### Raspberry Pi (mit GPIO-Unterstützung)

```bash
pip install -e ".[pi]"
```

### Entwicklung (mit Test-Tools)

```bash
pip install -e ".[dev]"
```

## Nutzung

### Schnellstart

```bash
# Virtuelle Umgebung aktivieren
source .venv/bin/activate

# Mit Beispieldaten starten
stage-cheater -d examples/songs

# Einzelne Datei anzeigen
stage-cheater -f examples/songs/amazing_grace.chopro
```

### Kommandozeilen-Optionen

| Option | Beschreibung |
|--------|--------------|
| `-d, --data-dir PATH` | Pfad zum Datenverzeichnis (Songs, Playlists) |
| `-f, --file PATH` | Einzelne ChordPro-Datei anzeigen |
| `-c, --config PATH` | Pfad zur config.toml |

### USB-Stick vorbereiten

Beispieldaten auf USB-Stick kopieren (erkennt USB-Sticks automatisch):

```bash
./install.sh --usb
```

Oder in ein bestimmtes Verzeichnis:

```bash
./install.sh --usb /media/user/USB-STICK
```

### USB-Stick Nutzung

Stage-Cheater erkennt automatisch USB-Sticks mit folgender Struktur:

```
USB-Stick/
├── config.toml          # Optional: Konfiguration
├── songs/               # ChordPro-Dateien
│   ├── song1.chopro
│   ├── song2.cho
│   └── ...
└── playlists/           # Optional: Setlists
    └── setlist.txt
```

Einfach USB-Stick einstecken und starten:

```bash
stage-cheater
```

## Steuerung

### Tastatur

| Taste | Funktion |
|-------|----------|
| → / Space / Page Down | Nächste Seite |
| ← / Page Up | Vorherige Seite |
| ↓ | Nächster Song |
| ↑ | Vorheriger Song |
| + | Zoom vergrößern |
| - | Zoom verkleinern |
| ESC / q | Beenden |

### GPIO (Raspberry Pi)

Standardmäßig deaktiviert. In `config.toml` aktivieren:

```toml
[input.gpio]
enabled = true
next_page_pin = 17
prev_page_pin = 27
```

## Konfiguration

Erstelle eine `config.toml` Datei (siehe `examples/config.toml`):

```toml
[display]
zoom = 1.0
font_size = 32
font_color = "#FFFFFF"
background_color = "#000000"
chord_color = "#FFFF00"
rotation = 0  # 0, 90, 180, 270 Grad

[input.keyboard]
next_page = ["RIGHT", "PAGEDOWN", "SPACE"]
prev_page = ["LEFT", "PAGEUP"]
next_song = ["DOWN"]
prev_song = ["UP"]
quit = ["ESCAPE", "q"]

[input.gpio]
enabled = false
next_page_pin = 17
prev_page_pin = 27

[system.gpio]
shutdown_pin = 22
restart_pin = 23
```

## ChordPro-Format

Stage-Cheater unterstützt das ChordPro-Format:

```
{title: Amazing Grace}
{artist: John Newton}
{key: G}

[G]Amazing [G7]grace how [C]sweet the [G]sound
That [G]saved a [Em]wretch like [D]me
```

### Unterstützte Direktiven

| Direktive | Kurzform | Beschreibung |
|-----------|----------|--------------|
| `{title: ...}` | `{t: ...}` | Songtitel |
| `{artist: ...}` | `{a: ...}` | Interpret |
| `{key: ...}` | `{k: ...}` | Tonart |
| `{capo: ...}` | - | Kapodaster-Position |
| `{tempo: ...}` | - | Tempo |

## Playlist-Format

Einfache Textdatei mit einem Dateinamen pro Zeile:

```
# Kommentare mit #
amazing_grace.chopro
house_of_the_rising_sun.chopro
```

## Autostart auf Raspberry Pi

### Systemd-Service einrichten

```bash
sudo nano /etc/systemd/system/stage-cheater.service
```

```ini
[Unit]
Description=Stage-Cheater Teleprompter
After=graphical.target

[Service]
User=pi
Environment=DISPLAY=:0
WorkingDirectory=/home/pi/stage-cheater
ExecStart=/home/pi/stage-cheater/.venv/bin/stage-cheater
Restart=on-failure

[Install]
WantedBy=graphical.target
```

```bash
# Service aktivieren und starten
sudo systemctl enable stage-cheater
sudo systemctl start stage-cheater

# Status prüfen
sudo systemctl status stage-cheater

# Logs anzeigen
journalctl -u stage-cheater -f
```

## Tests

```bash
source .venv/bin/activate
pytest tests/ -v
```

## Lizenz

MIT
