<!-- i18n-source-sha: d72686b2f766 -->
# Erste Schritte (in 5 Minuten startklar)

[日本語](./GETTING_STARTED.md) · [English](./GETTING_STARTED.en.md) · [简体中文](./GETTING_STARTED.zh.md) · [繁體中文](./GETTING_STARTED.tw.md) · [한국어](./GETTING_STARTED.ko.md) · **Deutsch**

## Welcher Einstieg passt zu Ihnen (3 Einstiegspunkte)

Fullseye ist breit angelegt — wenn man nicht zuerst entscheidet, "was man als Erstes öffnet", bleibt man stecken.
Was hier aufgeführt ist, sind keine neu geschriebenen Demos, sondern **Beispiele, die bereits jedes Mal von einem Gate
ausgeführt werden** (schlägt eines fehl, wird die CI rot).

| Einstieg | Zielgruppe | 5 Min: erst mal laufen lassen | 30 Min: dem Inneren folgen | Halber Tag: mit eigenen Daten |
|---|---|---|---|---|
| **Erklärbare Sichtprüfung** | Prüfung · Qualitätssicherung | `py -3.11 examples/poc_solder_fillet_aoi.py` — AOI für Lötstellen (Fillet) | `py -3.11 examples/poc_fabric_defect.py` — verpasste und falsche Treffer getrennt gezählt | [CAPABILITIES.md](CAPABILITIES.md), Abschnitt "Finden" → in Studio mit eigenen Bildern |
| **3-D für Robotik** | Robotik · 3-D-Messung | `py -3.11 examples/perception_pipeline.py` — Stereo → Tiefe → Punktwolke → Begehbarkeit | `py -3.11 examples/grasp_pose.py` — Punktwolke auf ein Modell ausgerichtet, 6-DoF-Pose und Greifrichtung | [EXAMPLES_3D.md](EXAMPLES_3D.md) → eigene Punktwolken/Meshes einspeisen |
| **Physikbasierte zerstörungsfreie Prüfung** | Röntgen · Optik · Messtechnik | `py -3.11 examples/ct_reconstruction.py` — Projektion → Rekonstruktion → Abmessung in mm und Fehleranzahl | `py -3.11 examples/poc_ct_void_morphology.py` — warum eine einzelne Pass/Fail-Zahl blind für die Form ist | [CAPABILITIES.md](CAPABILITIES.md), Abschnitt "Formgebung" → mit eigenen Volumendaten |

Jedes Beispiel besitzt einen **Referenzwert (Ground Truth)** (geschlossene Lösung oder synthetische Daten). Der
Nullpunkt (Ergebnis bei Untätigkeit) wird immer mit angegeben, sodass Sie selbst prüfen können, ob etwas wirklich
"gewirkt" hat. Wie weit die Validierung jeweils reicht, steht im Verzeichnis [MATURITY.md](MATURITY.md) — nicht von
Hand geschrieben, sondern automatisch aus den tatsächlich laufenden Gates und dem Vorhandensein echter Daten ermittelt.

---

Dies ist die Anleitung, um Fullseye (Arbeitsname imgevolve) auf dem kürzesten Weg zum Laufen zu bringen. In der
Reihenfolge **Installation → erste Pipeline bauen → ausführen → Ergebnis ansehen** geht es einen Weg ohne
Stolperfallen. Eine ausführlichere Einrichtung findet sich in [INSTALL.md](INSTALL.md), sämtliche Funktionen von
Studio in [STUDIO_GUIDE.md](STUDIO_GUIDE.md), die Ausführung aus eigenem Code in [ENGINE.md](ENGINE.md).

Fullseye ist eine **Bildverarbeitungs-Operatorbibliothek, die numpy-Arrays als Ein- und Ausgabe verwendet**, auf der
eine **visuelle Pipeline-Entwurfsumgebung im Stil von HDevelop (Fullseye Studio)** sowie eine
**Ausführungs-Laufzeitumgebung (FullseyeEngine)** aufsetzen. In der Sprache von HALCON/HDevelop entspricht das dem
zweistufigen Aufbau "in HDevelop den Ablauf entwerfen, in HDevEngine aus der eigenen Anwendung heraus aufrufen" —
unverändert mit Python + numpy nachgebildet.

---

## 1. Installation (1 Minute)

Voraussetzung: **Python 3.11** (unter Windows `py -3.11`, unter Linux `python3.11`).

```powershell
cd <path-to-fullseye>
py -3.11 -m pip install -e .          # nur der Kern aus numpy + scipy (rund 885 Operatoren)
```

Der Kern läuft **allein mit numpy und scipy**. Zusätzliche Backends wie OpenCV / scikit-image / Pillow sind optional;
fehlen sie, werden lediglich die für dieses Backend spezifischen Operatoren deaktiviert (graceful degradation). In der
Praxis braucht man mindestens OpenCV oder Pillow zum Lesen/Schreiben von Bilddateien — es lohnt sich also, eines der
folgenden zusätzlich zu installieren.

```powershell
py -3.11 -m pip install -e ".[opencv]"    # Bild-I/O + Operatoren auf Basis von OpenCV
py -3.11 -m pip install -e ".[all]"       # alle Backends (opencv, skimage, pil, wavelets, gpu, extra)
py -3.11 -m pip install -e ".[gui]"       # falls Fullseye Studio (PySide6) genutzt werden soll
```

Die Liste der Extras samt Bedeutung ist in [INSTALL.md](INSTALL.md) zusammengefasst. Für die GUI wird `[gui]`
(oder `[all]` + `[gui]`) benötigt.

> Man kann es auch ohne Installation ausprobieren. Setzen Sie das Repository-Wurzelverzeichnis
> (`<path-to-fullseye>`) als Arbeitsverzeichnis und tragen Sie diesen Pfad in die Umgebungsvariable `PYTHONPATH`
> ein — dann funktioniert `import fullseye`. Die Befehle `fullseye` / `fullseye-studio` (Konsolen-Skripte) stehen
> allerdings erst nach einem Durchlauf von `pip install -e .` zur Verfügung.

---

## 2. Zunächst einen einzelnen Operator ausführen (Python)

```python
import fullseye, numpy as np

frame = np.clip(np.random.default_rng(0).random((64, 64)), 0, 1)   # gray H×W in [0,1]

edges = fullseye.apply(frame, "sobel_amp")     # image → image (Gradientenstärke)
seg   = fullseye.apply(frame, "otsu")          # image → region (0/1-Binärbild)
n     = fullseye.apply(seg,   "count_obj")     # region → feature (Objektanzahl = Python float)
print(n)                                       # z. B.: 316.0
```

> **Die Argumentreihenfolge lautet `apply(image, name, a, b)`** — das erste Argument ist das Array, das zweite der
> Operatorname. Vertauscht man sie, bricht der Aufruf ab 0.1.9 mit `TypeError: ... arguments look swapped` ab
> (bis einschließlich 0.1.8 erschien stattdessen der unzusammenhängende numpy-Fehler
> "truth value of an array is ambiguous").
> `a`/`b` müssen endliche Werte im Bereich 0..1 sein. Strings, `None` und NaN lösen sofort `TypeError`/`ValueError`
> aus; Werte außerhalb des Bereichs werden abgeschnitten und im Verzeichnis protokolliert.

- `apply(image, name, a=0.5, b=0.5)` wendet **einen einzelnen Operator** an. `name` wird sowohl als
  **Operatorname** (z. B. `gaussian`) als auch als **HALCON-Alias** (z. B. `gauss_filter`) aufgelöst.
- `a` und `b` sind die **zwei Regler (0,0 bis 1,0)**, die jeder Operator besitzt. Ihre Bedeutung unterscheidet sich
  je nach Operator (Radius, Schwellwert, σ usw.).
- Der Ausgabetyp (sort) wird vom Operator bestimmt: `image` (Graustufen) / `region` (binär) /
  `feature` (skalarer float) / `color` (RGB) / `contour` (XLD) / `volume` (3D).
- **Was bei einem Fehler passiert** (seit 2026-09-03): Mit der Voreinstellung `on_error="fallback"` liefert ein
  intern fehlgeschlagener Operator einen zum Typ passenden, unschädlichen Wert zurück (bei Bildern z. B. eine Kopie
  der Eingabe), und es erscheint **pro Operator nur einmal** die Warnung `FullseyeFallbackWarning`. Was wie oft in
  einen Fallback gelaufen ist, lässt sich mit `fullseye.fallbacks()` / `fullseye.fallback_counts()` einsehen. Wird
  `on_error="raise"` übergeben (oder die Umgebungsvariable `FULLSEYE_ON_ERROR=raise` gesetzt), gilt **fail-closed**:
  die tatsächliche Ausnahme des Operators, Verstöße gegen den dtype-Vertrag (Integer-/Bool-Bilder) und Fehler des
  GPU-Kernels werden unverändert weitergereicht. **Eine falsche sort wird nur teilweise erkannt** (übergibt man
  z. B. ein RGB-Bild `(H,W,3)` an einen 2-D-Operator, wird es als Volumen behandelt — auch mit `raise` gibt es keine
  Ausnahme; siehe `docs/KNOWN_ISSUES.md` #32-4). Für CI und Validierung wird `raise` empfohlen.
- **Operatoren mit mehreren Eingaben** (`add_image` / `union2` usw., in `list_ops()` an `tier == "nary"` erkennbar)
  erhalten die Eingaben **als Liste**: `fullseye.apply([img1, img2], "add_image")`.
- **Template-Matching** (`ncc_locate` / `shape_locate`) übergibt das zu suchende Bild über `template=`:
  `corr, row, col = fullseye.apply(img, "ncc_locate", template=patch)` (die zurückgegebenen row/col sind das
  **Zentrum** der Trefferposition). Ohne Template liefert es `[0, 0, 0]` als "kein Treffer".

Welche Operatoren es gibt, lässt sich so herausfinden:

```python
fullseye.op_names()                 # alle registrierten Operatornamen (860 Stück, Stand 2026-09-03)
fullseye.list_ops(search="edge")    # Teilstring-Suche über Name / HALCON-Name / Kategorie
fullseye.list_ops(sort="region")    # Filterung nach Eingabe-sort
fullseye.categories()               # 47 Kategorien
```

---

## 3. Eine Pipeline aufbauen (mehrere Operatoren verketten)

Mehrere Operatoren nacheinander zu durchlaufen ergibt eine "Pipeline". Das Array wird durch jede Stufe
hindurchgereicht, das Endergebnis wird zurückgegeben.

```python
# Alle Stufen verwenden dieselben a, b (dieselbe Form wie in der CLI)
out = fullseye.run_pipeline(frame, ["gaussian", "sobel_amp", "otsu"])

# Wenn jede Stufe eigene Regler haben soll (mit Tupeln (name, a, b) angeben)
out = fullseye.run_pipeline(frame, [("gaussian", 0.3, 0.5), ("otsu", 0.4, 0.5)])
```

Das ist "Smoothing (Glättung) → Kantenstärke → Otsu-Binarisierung", ein typisches Beispiel dafür, wie aus einem
Bild eine binäre Kantenkarte erzeugt wird. **20 sofort einsatzbereite Kombinationen** (Rezepte) sind bereits
mitgeliefert.

```python
import recipes
recipes.names()                                   # Liste der Rezeptnamen
stages = recipes.stages("Edge — Sobel + Otsu")    # [(op, a, b), ...]
out = fullseye.run_pipeline(frame, stages)
```

---

## 4. Visuell aufbauen (Fullseye Studio)

Ohne eine Zeile Code zu schreiben: Operatoren suchen und anordnen, Regler per Schieberegler drehen, Stufe für Stufe
ausführen und die Zwischenergebnisse direkt betrachten. Dafür werden die GUI-Extras benötigt
(`pip install -e ".[gui]"` = PySide6).

```powershell
py -3.11 studio.py          # oder, falls installiert: fullseye-studio
```

Der Aufbau besteht aus 3 Bereichen.

- **Links (Operators)**: Operatoren nach Kategorie / Suche eingrenzen, **per Doppelklick einfügen**
  (Edit ▸ Focus operator search = **Strg+F** springt ins Suchfeld). Beispielpipelines lassen sich ebenfalls von hier
  laden. **Insert (＋) funktioniert wie das Operatorfenster in HDevelop**: Beim Hinzufügen einer Stufe zur Pipeline
  wird gleichzeitig an der Cursorposition im Program-Fenster eine Zeile `op (a, b)` geschrieben (Werte in der vollen
  Genauigkeit von `repr`. Gibt es im Program-Fenster noch nicht angewendete manuelle Änderungen, wird nur diese Zeile
  eingefügt; erst Apply übernimmt sie).
- **Mitte (Pipeline)**: Liste der angeordneten Stufen. Reihenfolge per Drag & Drop oder mit Strg+↑/↓ ändern, an der
  ausgewählten Stufe die **Regler a / b** einstellen. Die Regler liegen stets im Bereich 0..1, doch **bei
  Operatoren mit eigener Anzeigespezifikation (`param_specs.py`) lässt sich in der realen Einheit arbeiten** —
  bei `gaussian` etwa σ in px (Schieberegler + Spinbox mit Einheit), bei `median` die Kerngröße als 3/5/7/9-Auswahl,
  bei `reg_erode` die Anzahl der Iterationen als Ganzzahl-Spinbox, beim b-Parameter von `aug_barrel` als
  "pincushion"-Kontrollkästchen. Die Spinbox am rechten Rand zeigt immer den Rohwert 0..1 (für exakte Eingaben). Die
  Spezifikationen wurden von Hand aus den Umrechnungsformeln in ops.py (z. B. `0,3 + 2,7·a`) abgeleitet und werden
  per Test gegen die Implementierung geprüft (`tests/test_studio_params.py`). Operatoren ohne Spezifikation
  behalten wie bisher die zwei 0..1-Schieberegler. Auch die Stufenliste wird in der Anzeigeeinheit geschrieben
  (`gaussian (blur σ=1.08 px, b=–)`). Mit **Reset (Pos1) → Step (Strg+→) → Run all (Strg+Enter)** lässt sich Stufe
  für Stufe oder in einem Zug ausführen.
- **Rechts (Image / Perception / Analysis)**: Ergebnisbild mit Zoom/Pan, Histogramm, Inspector (Prüfung von
  image-/region-/feature-Werten), das Wahrnehmungspanel aus v14 (optischer Fluss / Stereo-Tiefe usw.). **Rechtsklick
  in der Bildansicht** öffnet Fit / 1:1 / Zoom / Save result / Save view as shown / Copy / Display mode /
  3D surface (dieselben Aktionen wie im Menü). Zusätzlich geöffnete Grafikfenster besitzen ebenfalls eine kleine
  Leiste mit Fit·1:1·±·Save und dasselbe Rechtsklickmenü; der 3-D-Viewer (Strg+4) bietet per Rechtsklick
  Reset view / Wechsel in die Ich-Perspektive (perspektivisch) / Wireframe / Save screenshot.

Die aufgebaute Pipeline lässt sich mit **Export (Strg+E)** als `--ops`-String oder als Python-Code exportieren und
mit **Save pipeline (Strg+Umschalt+S)** als JSON speichern. Sämtliche Funktionen und Tastenkürzel finden sich in
[STUDIO_GUIDE.md](STUDIO_GUIDE.md), innerhalb der Anwendung zeigt **F1** eine Übersicht.

---

## 5. Eine gespeicherte Pipeline ausführen (CLI / Code)

Das in Studio per `Save pipeline` erzeugte JSON (oder ein `--ops`-String) lässt sich unverändert auf eine Datei
anwenden. Das ist der zu HDevEngine äquivalente Weg, "das Entworfene auszuführen, ohne es neu zu schreiben".

```powershell
# I/O und Stufen des gespeicherten JSON prüfen (Strukturprüfung ohne Bild)
py -3.11 imgevolve.py run edge.json --describe

# Auf ein Bild anwenden und das Ergebnis speichern
py -3.11 imgevolve.py run edge.json in.png --out result.png

# Ergebnisse stufenweise speichern (result_00.png, result_01.png, ...)
py -3.11 imgevolve.py run edge.json in.png --stepwise --out step.png

# Die Pipeline als eigenständige Python-Funktion exportieren
py -3.11 imgevolve.py run "gaussian,sobel_amp,otsu" --to-python
```

Zur Ausführung aus Code wird `FullseyeEngine` verwendet (Details in [ENGINE.md](ENGINE.md)).

```python
import fullseye
eng = fullseye.FullseyeEngine.load("edge.json")     # or .from_ops("gaussian,sobel_amp,otsu")
print(eng.input_sort(), "->", eng.output_sort())    # image -> region
out = eng.run(frame)                                # numpy in, numpy out
steps = eng.run_stepwise(frame)                     # Zwischenergebnisse jeder Stufe (Liste)
```

---

## 6. Einzeln per CLI anwenden

Wenn man Bilddateien direkt bearbeiten möchte, ist die CLI die bequemste Wahl (für Bild-I/O werden OpenCV oder
Pillow benötigt).

```powershell
py -3.11 imgevolve.py ops --search edge                    # Operatoren durchsuchen
py -3.11 imgevolve.py has gauss_filter                      # prüfen, ob der HALCON-Name implementiert ist + Aufrufform
py -3.11 imgevolve.py apply gauss_filter in.png out.png --a 0.6
py -3.11 imgevolve.py pipeline in.png out.png --ops "gaussian,sobel_amp,otsu"
```

`apply` / `pipeline` verwenden in jeder Stufe dieselben `--a` / `--b`. Wenn jede Stufe eigene Regler benötigt,
verwenden Sie stattdessen `run_pipeline` (Python) oder Studio, wie oben beschrieben.

---

## Wenn es hakt

| Symptom | Abhilfe |
|---|---|
| `ModuleNotFoundError: No module named 'fullseye'` | `pip install -e .` ausführen oder das Repository-Wurzelverzeichnis in `PYTHONPATH` eintragen |
| Kein Befehl `fullseye` / `fullseye-studio` vorhanden | Die Konsolen-Skripte werden erst durch `pip install -e .` registriert. Ohne Installation `py -3.11 imgevolve.py ...` bzw. `py -3.11 studio.py` verwenden |
| Studio startet nicht | GUI-Extras nicht installiert. `pip install -e ".[gui]"` (PySide6) |
| `apply` / `pipeline` meldet `cannot read ...` | Für Bild-I/O OpenCV (`[opencv]`) oder Pillow (`[pil]`) installieren |
| Operatoren eines zusätzlichen Backends erscheinen als "unknown" | Das betreffende Backend ist nicht installiert. `.[skimage]`, `.[wavelets]`, `.[extra]` usw. ergänzen |

Eine ausführlichere Fehlersuche findet sich in [INSTALL.md](INSTALL.md).

## Weiterführende Lektüre

- **[INSTALL.md](INSTALL.md)** — vollständiger Leitfaden zur Einrichtung (Einsatz der Extras, Installationsprogramme für Windows/Linux, Minimalkonfiguration · Einbettung)
- **[STUDIO_GUIDE.md](STUDIO_GUIDE.md)** — vollständiger Leitfaden zu Fullseye Studio
- **[ENGINE.md](ENGINE.md)** — Leitfaden zu FullseyeEngine (Entwurf → Ausführung)
- **[README.md](README.md)** — Dokumentationsindex
