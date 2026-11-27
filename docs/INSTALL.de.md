---
title: "Installations- und Einrichtungshandbuch"
description: "Installationswege, optionale Abhängigkeiten und Prüfschritte für Fullseye."
lang: de
---
<!-- i18n-source-sha: 9f0dbf51f0cb -->
# Installations- und Einrichtungshandbuch

<!-- i18n-switcher -->
[日本語](./INSTALL.md) · [English](./INSTALL.en.md) · [简体中文](./INSTALL.zh.md) · [繁體中文](./INSTALL.tw.md) · [한국어](./INSTALL.ko.md) · **Deutsch** · [हिन्दी](./INSTALL.hi.md)


Dieses Handbuch beschreibt, wie Fullseye (Arbeitstitel imgevolve) je nach Einsatzzweck eingerichtet wird — von der Entwicklungsmaschine bis zu eingebettetem Linux. Wer es nur in 5 Minuten zum Laufen bringen möchte, findet in [GETTING_STARTED.md](GETTING_STARTED.de.md) den schnelleren Weg.

Der Python-API-Kern von Fullseye läuft mit **numpy + scipy**. Ein normales `pip install fullseye` installiert außerdem Studio (PySide6-Essentials) und Pillow; die schweren Bildverarbeitungs-Backends bleiben optional. Fehlt ein zusätzliches Backend, werden nur dessen spezifische Operatoren deaktiviert (graceful degradation).

---

## (a) Voraussetzungen

| Punkt | Anforderung |
|---|---|
| Python | **3.11** (`requires-python = ">=3.11"` in `pyproject.toml`; Entwicklung und Verifikation erfolgen mit 3.11) |
| Ausführungsbefehl | Windows: `py -3.11` / Linux: `python3.11` |
| Standardabhängigkeiten | `numpy>=1.23`, `scipy>=1.10`, `PySide6-Essentials>=6.5,!=6.12.0`, `Pillow>=13.0` (werden durch `pip install -e .` automatisch installiert) |
| Betriebssystem | Windows 10/11, Linux (auch eingebettet). Auch macOS funktioniert, solange Python läuft |

---

## (b) pip install (Bedeutung und Verwendung der Extras)

Die editierbare Installation (editable install) erfolgt im Wurzelverzeichnis des Repositorys.

```powershell
cd <path-to-fullseye>
py -3.11 -m pip install -e .            # Standard: Python-API + Studio + Pillow; ein Op mit optionalem Backend nennt beim Aufruf das fehlende Extra
```

Zusätzliche Backends werden über **Extras** ausgewählt (definiert unter `[project.optional-dependencies]` in `pyproject.toml`).

<!-- extras-table:start -->
| Extra | Von pyproject.toml hinzugefügte Abhängigkeiten |
|---|---|
| `native` | — |
| `opencv` | `opencv-python>=4.8.1.78` |
| `skimage` | — |
| `pil` | — |
| `yaml` | `PyYAML>=6.0` |
| `wavelets` | `PyWavelets>=1.4` |
| `gpu` | `torch>=2.13`<br>`kornia>=0.9`<br>`cupy-cuda12x>=14; platform_system != 'Darwin'` |
| `gi` | `mitsuba>=3.5` |
| `extra` | `mahotas>=1.4`<br>`SimpleITK>=2.2` |
| `gui` | — |
| `handpose` | `mediapipe>=0.10` |
| `video` | — |
| `audio` | — |
| `volume` | `SimpleITK>=2.2` |
| `raster` | — |
| `gltf` | — |
| `lidar` | — |
| `pcd` | — |
| `xlsx` | — |
| `e57` | `pye57>=0.4` |
| `export-verify` | `pye57>=0.4`<br>`astropy>=7.0`<br>`plyfile>=1.0` |
| `polygon` | — |
| `threed` | `torch>=2.13`<br>`SimpleITK>=2.2` |
| `serial` | — |
| `modbus` | — |
| `symbols` | — |
| `mqtt` | — |
| `opcua` | — |
| `dev` | `pytest>=9.0.3`<br>`pytest-cov>=4`<br>`ruff>=0.4`<br>`pytest-timeout>=2.3`<br>`hypothesis>=6.100`<br>`pytest-randomly>=3.15`<br>`pytest-xdist>=3.5`<br>`pip-audit>=2.7` |
| `all-cpu` | `opencv-python>=4.8.1.78`<br>`PyWavelets>=1.4`<br>`mitsuba>=3.5`<br>`mahotas>=1.4`<br>`SimpleITK>=2.2`<br>`mediapipe>=0.10`<br>`pye57>=0.4`<br>`astropy>=7.0` |
| `all` | `opencv-python>=4.8.1.78`<br>`PyWavelets>=1.4`<br>`torch>=2.13`<br>`kornia>=0.9`<br>`cupy-cuda12x>=14; platform_system != 'Darwin'`<br>`mitsuba>=3.5`<br>`mahotas>=1.4`<br>`SimpleITK>=2.2`<br>`mediapipe>=0.10`<br>`pye57>=0.4`<br>`astropy>=7.0` |
<!-- extras-table:end -->


Die Standardanforderung von Studio ist `PySide6-Essentials>=6.5,!=6.12.0`. Version 6.12.0 ist ausgeschlossen, da sie unter Linux reproduzierbar SIGABRT verursacht.

Empfehlung zur Auswahl:

```powershell
# in der Praxis häufig genutzte Minimalausstattung + Bild-I/O (Studio ist bereits Standard)
py -3.11 -m pip install -e ".[opencv]"

# die bisherige Schreibweise bleibt kompatibel (`gui` ist ein leerer Alias)
py -3.11 -m pip install -e ".[opencv,gui]"

# volle Ausstattung (Studio ist bereits Standard)
py -3.11 -m pip install -e ".[all]"

# auch den GPU-Batch-Pfad ausprobieren (benötigt CUDA-fähiges torch)
py -3.11 -m pip install -e ".[gpu]"
```

> Studio und Pillow sind Standardabhängigkeiten. `gui` und `pil` sind leere Kompatibilitätsaliase für vorhandene Installationsbefehle.

Nach erfolgreicher Installation stehen die folgenden **zwei Konsolenskripte** zur Verfügung (`[project.scripts]`).

| Befehl | Implementierung | entsprechende direkte Ausführung |
|---|---|---|
| `fullseye` | `imgevolve:main` (CLI) | `py -3.11 imgevolve.py ...` |
| `fullseye-studio` | `studio:main` (GUI) | `py -3.11 studio.py` |

Wer es ohne Installation ausprobieren möchte: Wird das Wurzelverzeichnis des Repositorys zu `PYTHONPATH` hinzugefügt, funktioniert `import fullseye` (die Konsolenskripte stehen dann jedoch nicht zur Verfügung).

```powershell
$env:PYTHONPATH = "<path-to-fullseye>"
py -3.11 -c "import fullseye; print(fullseye.version())"      # 0.1.0
```

Nach `pip install fullseye` registriert die erste interaktive Ausführung von `fullseye` oder `fullseye-studio` **Fullseye Studio** einmalig im Windows-Startmenü beziehungsweise im Linux-Anwendungsmenü. Ein Eintrag aus einer virtuellen Umgebung startet deren Python. Wird der Eintrag später gelöscht, erstellt ein normaler Befehl ihn nicht erneut. Bei Erfolg gibt das Programm derzeit die folgende japanische Zeile aus; sie bestätigt die Registrierung und nennt den Befehl zum Entfernen:

`スタートメニューに Fullseye Studio を登録しました(外す: fullseye-studio --remove-shortcuts)` _(ja)_

Zum Unterdrücken `FULLSEYE_NO_SHORTCUTS=1` setzen oder diesen Wert in die durch `FULLSEYE_STUDIO_SETTINGS` benannte INI schreiben (unter Linux normalerweise `~/.config/Fullseye/Studio.conf`). CI, Befehle ohne Terminal und eine Windows-Administratorrichtlinie, die Startmenüprogramme ausblendet, erstellen keinen Eintrag. Für die detaillierte optionale Einrichtung dient `fullseye setup`.

```ini
[shortcuts]
auto_register=false
```

---

## (c) Windows-Installationsprogramm

Das Ausführen von `install\install.ps1` erledigt Einrichtung und Desktop-Integration in einem Schritt (PowerShell).

```powershell
cd <path-to-fullseye>
powershell -ExecutionPolicy Bypass -File install\install.ps1
```

Beim Ausführen dieses Installationsprogramms geschieht ungefähr Folgendes:

- Prüfung, ob Python 3.11 vorhanden ist
- Installation von Fullseye per `pip install -e .` (inklusive benötigter Extras)
- **Erstellung einer Verknüpfung für Fullseye Studio (`Fullseye Studio.lnk`)** — sie wird über `pyw.exe` registriert, sodass der Start ohne sichtbares Konsolenfenster erfolgt, und erhält das Symbol `assets\fullseye.ico`

Anschließend lässt sich Studio über das Startmenü bzw. die Desktop-Verknüpfung starten.

> Falls die Ausführungsrichtlinie den Start blockiert, `-ExecutionPolicy Bypass` anhängen (im obigen Befehl bereits enthalten).

---

## (d) Linux-Installationsskript + `.desktop`-Starter

Das Ausführen von `install/install.sh` richtet unter Linux eine gleichwertige Umgebung ein.

```bash
cd /path/to/imgevolve
bash install/install.sh
```

Beim Ausführen dieses Skripts geschieht ungefähr Folgendes:

- Prüfung, ob `python3.11` vorhanden ist
- `pip install -e .` (inklusive benötigter Extras)
- **Erstellung eines `.desktop`-Starters** — ein Desktop-Eintrag mit dem Symbol `assets/fullseye.ico` wird registriert, damit sich Fullseye Studio aus dem Anwendungsmenü starten lässt

Anschließend lässt sich Studio über die Anwendungsliste der Desktop-Umgebung starten.

---

## (e) Minimalkonfiguration / Embedded (eingebettetes Linux)

Der Python-API-Kern von Fullseye ist so gestaltet, dass er **allein mit numpy + scipy** läuft; die Standardinstallation enthält zusätzlich Studio und Pillow. Bei eingebetteten Anwendungen ohne GUI, GPU und schwere Backends kann weiterhin nur dieser API-Teil genutzt werden.

```bash
python3.11 -m pip install -e .        # Standardinstallation enthält Studio/Pillow; kein torch/opencv nötig
```

Wichtige Punkte für den Einsatz im eingebetteten Umfeld:

- **Ein- und Ausgabe erfolgen vollständig über numpy-Arrays.** Ganz ohne Datei-I/O lassen sich numpy-Frames direkt übergeben, die von Sensor oder Kamera stammen.

  ```python
  import fullseye, numpy as np
  frame = get_camera_frame()                       # selbst beschafftes float64 gray [0,1]
  seg = fullseye.apply(frame, "otsu")              # kein Schreiben auf die Festplatte nötig
  out = fullseye.run_pipeline(frame, ["gaussian", "sobel_amp", "otsu"])
  ```

- **Wird Datei-I/O benötigt** (`fullseye.load` / `fullseye.save`, `imgevolve.py run`, examples), genügt **entweder OpenCV oder Pillow** (`imgio` wählt automatisch das verfügbare aus). Pillow ist bereits Standardabhängigkeit.
- Eine Arbeitsteilung **Entwurf auf der Entwicklungsmaschine, Ausführung auf dem eingebetteten Gerät** ist möglich. Auf der Entwicklungsmaschine wird die Pipeline in Studio erstellt und als JSON exportiert; auf dem eingebetteten Gerät genügt `FullseyeEngine.load("pipeline.json").run(frame)` zur Ausführung (keine GUI nötig). Details siehe [ENGINE.md](ENGINE.de.md).
- **Der Wahrnehmungs-Stack** (stereo / terrain / flow / detect / registration / pose) läuft ebenfalls allein mit numpy + scipy (z. B. `fullseye.disparity_map`). Für Robotik-/Vision-Anwendungen ohne zusätzliche Abhängigkeiten nutzbar.

> GPU (`torch`) ist ausschließlich eine **optionale Beschleunigung für Batch-Verarbeitung**. Für die Verarbeitung einzelner Bilder im eingebetteten Umfeld wird sie nicht benötigt — auch ohne Installation laufen alle Operatoren auf der CPU.

---

## (f) Häufige Probleme

| Symptom | Ursache | Abhilfe |
|---|---|---|
| `ModuleNotFoundError: No module named 'fullseye'` | nicht installiert / Pfad nicht gesetzt | `pip install -e .` ausführen oder das Repository-Wurzelverzeichnis zu `PYTHONPATH` hinzufügen |
| Befehl `fullseye` / `fullseye-studio` wird nicht gefunden | Konsolenskripte nicht registriert | `pip install -e .` ausführen. Ohne Installation: `py -3.11 imgevolve.py` / `py -3.11 studio.py` |
| ImportError für PySide6 beim Start von Studio | Standardabhängigkeit beschädigt | `pip install --force-reinstall fullseye` |
| `ImportError: libEGL.so.1` o. Ä. beim Start von Studio unter Linux | von Qt benötigte Systembibliotheken fehlen (pip kann sie nicht installieren) | Debian/Ubuntu: `sudo apt-get install -y libegl1 libgl1 libxkbcommon-x11-0 libdbus-1-3 libxcb-cursor0` (`libxcb-cursor0` wird benötigt, um das Fenster über xcb auf dem Bildschirm anzuzeigen; CI prüft den Offscreen-Start mit den übrigen vier). Andere Distributionen: die entsprechenden Pakete |
| `cannot read <path>` bei `apply` / `pipeline` | Standardabhängigkeit Pillow beschädigt oder Bild beschädigt | `pip install --force-reinstall fullseye`; falls das nicht hilft, Bild prüfen |
| ImportError für cv2 bei `read_image` / `write_image` (API) | diese sind **ausschließlich für OpenCV** | `pip install -e ".[opencv]"`. Wer stattdessen Pillow nutzen möchte, verwendet `fullseye.load` / `fullseye.save` |
| erwarteter Operator fehlt in `list_ops` / `has` liefert unknown | zugehöriges Backend nicht installiert | passendes Extra hinzufügen (`skimage`/`wavelets`/`extra` usw.) |
| GPU-Batch (`accel`/`bench`) ist auf der CPU langsam | `torch` ist die CPU-Version | auf der GPU `--device cuda` verwenden. Auf der CPU sind einfache elementweise Operationen wegen der Konvertierungskosten im Nachteil (so vorgesehen) |
| die 3D-Surface in Studio öffnet sich nicht | `QtDataVisualization` fehlt | Best-Effort-Funktion. Hängt von Version/Konfiguration von PySide6 ab und wird bei Fehlen stillschweigend übersprungen |

### Abhängigkeiten der Bild-I/O (wichtig)

Welches Backend zum Lesen/Schreiben von Dateien benötigt wird, hängt vom jeweiligen Pfad ab.

| Pfad | benötigtes Backend |
|---|---|
| `fullseye.load` / `fullseye.save` (= `imgio`), `imgevolve.py run`, examples | **OpenCV oder Pillow** (eines von beiden genügt / automatischer Fallback) |
| `imgevolve.py apply` / `pipeline` | **OpenCV erforderlich** |
| `fullseye.read_image` / `fullseye.write_image` (API) | **OpenCV erforderlich** |

`apply` / `run_pipeline` / `FullseyeEngine.run`, die numpy-Arrays direkt übergeben, **benötigen überhaupt kein Bild-I/O-Backend** (laufen allein mit dem Kern aus numpy + scipy).

---

## Funktionsprüfung

```powershell
py -3.11 imgevolve.py coverage        # ehrliche Abdeckungszahl (979/2313 HALCON-Operatoren echt implementiert)
py -3.11 imgevolve.py ops --search edge
py -3.11 -c "import fullseye; print(fullseye.version(), len(fullseye.op_names()), 'ops')"
```

`fullseye.version()` liefert `0.1.0`, `op_names()` gibt 860 registrierte Operatoren zurück (Stand 2026-09-03).
