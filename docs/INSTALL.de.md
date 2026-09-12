# Installations- und Einrichtungshandbuch

[日本語](./INSTALL.md) · [English](./INSTALL.en.md) · [简体中文](./INSTALL.zh.md) · [繁體中文](./INSTALL.tw.md) · [한국어](./INSTALL.ko.md) · **Deutsch**

Dieses Handbuch beschreibt, wie Fullseye (Arbeitstitel imgevolve) je nach Einsatzzweck eingerichtet wird — von der Entwicklungsmaschine bis zu eingebettetem Linux. Wer es nur in 5 Minuten zum Laufen bringen möchte, findet in [GETTING_STARTED.md](GETTING_STARTED.md) den schnelleren Weg.

Das Designprinzip von Fullseye lautet: **"ein Kern, der allein mit numpy + scipy läuft" plus "alle schweren Abhängigkeiten sind optional"**. Fehlt ein zusätzliches Backend, werden lediglich die dafür spezifischen Operatoren deaktiviert — der Kern funktioniert immer weiter (graceful degradation).

---

## (a) Voraussetzungen

| Punkt | Anforderung |
|---|---|
| Python | **3.11** (`requires-python = ">=3.10"` in `pyproject.toml`; Entwicklung und Verifikation erfolgen mit 3.11) |
| Ausführungsbefehl | Windows: `py -3.11` / Linux: `python3.11` |
| Kernabhängigkeiten | `numpy>=1.23`, `scipy>=1.9` (werden durch `pip install -e .` automatisch installiert) |
| Betriebssystem | Windows 10/11, Linux (auch eingebettet). Auch macOS funktioniert, solange Python läuft |

---

## (b) pip install (Bedeutung und Verwendung der Extras)

Die editierbare Installation (editable install) erfolgt im Wurzelverzeichnis des Repositorys.

```powershell
cd <path-to-fullseye>
py -3.11 -m pip install -e .            # nur der Kern (numpy + scipy, rund 885 Operatoren)
```

Zusätzliche Backends werden über **Extras** ausgewählt (definiert unter `[project.optional-dependencies]` in `pyproject.toml`).

| Extra | zusätzliche Abhängigkeit | was dadurch aktiviert wird |
|---|---|---|
| `opencv` | `opencv-python>=4.6` | Datei-I/O für Bilder (von der CLI `apply`/`pipeline` vorausgesetzt), `cv_*`-Operatoren |
| `skimage` | `scikit-image>=0.20` | `sk_*` / `xsk_*`-Reihen (Grundlage vieler automatisch generierter Operatoren) |
| `pil` | `Pillow>=9` | Fallback für Bild-I/O, `xpil_*`-Reihe (emboss/posterize/solarize usw.) |
| `wavelets` | `PyWavelets>=1.4` | Wavelet-Verfahren (VisuShrink/Subband/Packet usw.) |
| `gpu` | `torch>=2.0`, `kornia>=0.7` | GPU-Batch-Backend (`accel.py`/`bench.py`), `xkor_*`(kornia)-Reihe |
| `extra` | `mahotas>=1.4`, `SimpleITK>=2.2` | `xsitk_*` (curvature flow usw.), von mahotas abgeleitet (Zernike/pftas usw.) |
| `gui` | `PySide6>=6.5` | **Fullseye Studio** (`studio.py` / `fullseye-studio`) |
| `all` | alles Obige außer GUI (opencv, skimage, pil, wavelets, gpu, extra) | alle Operatoren und Backends |

Empfehlung zur Auswahl:

```powershell
# in der Praxis häufig genutzte Minimalausstattung + Bild-I/O (keine GUI, Fokus auf Code/CLI)
py -3.11 -m pip install -e ".[opencv]"

# auch die GUI (Studio) verwenden
py -3.11 -m pip install -e ".[opencv,gui]"

# volle Ausstattung (inklusive GUI; da "all" die GUI nicht enthält, wird "gui" separat angegeben)
py -3.11 -m pip install -e ".[all,gui]"

# auch den GPU-Batch-Pfad ausprobieren (benötigt CUDA-fähiges torch)
py -3.11 -m pip install -e ".[gpu]"
```

> `all` **enthält kein `gui`** (die GUI ist ein eigener Anwendungsfall und daher separat). Wer Studio nutzen möchte, muss `gui` unbedingt explizit angeben.

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

Der Kern von Fullseye ist so gestaltet, dass er **allein mit numpy + scipy** läuft. Für eingebettete Anwendungsfälle, die weder GUI noch GPU noch schwere Backends benötigen, genügt es, nur den Kern zu installieren.

```bash
python3.11 -m pip install -e .        # nur numpy + scipy. Kein GUI/torch/opencv nötig
```

Wichtige Punkte für den Einsatz im eingebetteten Umfeld:

- **Ein- und Ausgabe erfolgen vollständig über numpy-Arrays.** Ganz ohne Datei-I/O lassen sich numpy-Frames direkt übergeben, die von Sensor oder Kamera stammen.

  ```python
  import fullseye, numpy as np
  frame = get_camera_frame()                       # selbst beschafftes float64 gray [0,1]
  seg = fullseye.apply(frame, "otsu")              # kein Schreiben auf die Festplatte nötig
  out = fullseye.run_pipeline(frame, ["gaussian", "sobel_amp", "otsu"])
  ```

- **Wird Datei-I/O benötigt** (`fullseye.load` / `fullseye.save`, `imgevolve.py run`, examples), genügt **entweder OpenCV oder Pillow** (`imgio` wählt automatisch das verfügbare aus). Wer im eingebetteten Umfeld Leichtgewichtigkeit bevorzugt, ist mit Pillow (`[pil]`) besser bedient, da es kleiner ausfällt.
- Eine Arbeitsteilung **Entwurf auf der Entwicklungsmaschine, Ausführung auf dem eingebetteten Gerät** ist möglich. Auf der Entwicklungsmaschine wird die Pipeline in Studio erstellt und als JSON exportiert; auf dem eingebetteten Gerät genügt `FullseyeEngine.load("pipeline.json").run(frame)` zur Ausführung (keine GUI nötig). Details siehe [ENGINE.md](ENGINE.md).
- **Der Wahrnehmungs-Stack** (stereo / terrain / flow / detect / registration / pose) läuft ebenfalls allein mit numpy + scipy (z. B. `fullseye.disparity_map`). Für Robotik-/Vision-Anwendungen ohne zusätzliche Abhängigkeiten nutzbar.

> GPU (`torch`) ist ausschließlich eine **optionale Beschleunigung für Batch-Verarbeitung**. Für die Verarbeitung einzelner Bilder im eingebetteten Umfeld wird sie nicht benötigt — auch ohne Installation laufen alle Operatoren auf der CPU.

---

## (f) Häufige Probleme

| Symptom | Ursache | Abhilfe |
|---|---|---|
| `ModuleNotFoundError: No module named 'fullseye'` | nicht installiert / Pfad nicht gesetzt | `pip install -e .` ausführen oder das Repository-Wurzelverzeichnis zu `PYTHONPATH` hinzufügen |
| Befehl `fullseye` / `fullseye-studio` wird nicht gefunden | Konsolenskripte nicht registriert | `pip install -e .` ausführen. Ohne Installation: `py -3.11 imgevolve.py` / `py -3.11 studio.py` |
| ImportError für PySide6 beim Start von Studio | GUI-Extras nicht installiert | `pip install -e ".[gui]"` |
| `cannot read <path>` bei `apply` / `pipeline` | kein Bild-I/O-Backend vorhanden | `pip install -e ".[opencv]"` (oder `[pil]`) |
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
