# Projektbeschreibung
Ein Raspberry-Pi basierter Bühnen-Teleprompter zur Anzeige von Songtexten und Akkorden. Das Gerät kann ChordPro-Dateien anzeigen. 
Gesteuert wird es via Fußpedal. Es kann ein Zoomfaktor eingestellt werden. Außerdem kann dann mit dem Fußpedal geblättert werden. 
Die Chordpro-Dateien können über eine Playlist-Datei in einer Reihenfolge angeordnet werden. Die Daten werden beim Start von einem angeschlossenen
USB-Stick geladen. Dieser wird automatisch gemountet. Das Fußpedal kann entweder als Bluetooth-Tastatur angeschlossen werden und verhält sich identisch zu einem Powerpoint Presenter,
alternativ kann ein Fußpedal an die GPIO-Pins des Pi angeschlossen werden. Die Belegung und Funktion kann in einer Config-Datei konfiguriert werden, die ebenfalls beim Start vom USB-Stick gelesen wird. 
Außerdem kann das System über einen GPIO-Pin sauber heruntergefahren oder neugestartet werden. :
