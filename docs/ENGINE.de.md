# FullseyeEngine — Laufzeitumgebung zur Ausführung entworfener Pipelines

[日本語](./ENGINE.md) · [English](./ENGINE.en.md) · [简体中文](./ENGINE.zh.md) · [繁體中文](./ENGINE.tw.md) · [한국어](./ENGINE.ko.md) · **Deutsch**

`FullseyeEngine` (`engine.py`) ist eine Laufzeitumgebung, mit der eine in Fullseye Studio **erstellte** Bildoperator-Pipeline aus eigenem Code oder über die CLI **ausgeführt** wird. Sie entspricht der **HDevEngine** von MVTec — der Ablauf wird mit einem visuellen Werkzeug entworfen und anschließend unverändert aus der Anwendung heraus aufgerufen; das ist die zweite Hälfte dieses zweistufigen Modells.

- **Entwurf (author)**: Fullseye Studio → `Save pipeline` exportiert JSON ([STUDIO_GUIDE.md](STUDIO_GUIDE.md)).
- **Ausführung (execute)**: `FullseyeEngine.load("pipeline.json").run(frame)` — **numpy-Array rein, numpy-Array raus**. Weder Datei-I/O noch GUI erforderlich.

Eine Pipeline ist eine Liste von Stufen der Form `(op, a, b)`. Die Engine kann sowohl aus dem JSON von Studio als auch aus einem `--ops`-String oder einer Python-Liste geladen werden, prüft die Ein-/Ausgabe-Sorts, passt die Regler jeder Stufe an und führt sie auf numpy-Frames aus (vollständig, bis zu einer Zwischenstufe oder Stufe für Stufe). Sie führt außerdem eine Strukturprüfung durch (unbekannte Operatoren, inkonsistente Sorts) — dieselbe Prüfung wie im Diagnosepanel von Studio.

---

## Der einfachste Einstieg

```python
import fullseye, numpy as np

frame = np.clip(np.random.default_rng(0).random((64, 64)), 0, 1)   # gray H×W in [0,1]

eng = fullseye.FullseyeEngine.load("edge.json")     # or .from_ops("gaussian,sobel_amp,otsu")
print(eng.input_sort(), "->", eng.output_sort())    # image -> region
out = eng.run(frame)                                # numpy in, numpy out
steps = eng.run_stepwise(frame)                     # Zwischenergebnis jeder Stufe (Liste)
```

`FullseyeEngine` und `diagnose_stages` werden über `fullseye` (und `engine`) exportiert.

---

## Vier Wege zum Laden

| Konstruktionsweg | Signatur | Verwendung |
|---|---|---|
| JSON-Datei | `FullseyeEngine.load(path)` | Liest die `Save pipeline`-Ausgabe von Studio |
| ops-String | `FullseyeEngine.from_ops(ops, a=0.5, b=0.5, name="pipeline")` | kommagetrennt, z. B. `"gaussian,sobel_amp,otsu"` (gemeinsame Regler) |
| dict | `FullseyeEngine.from_dict(d, name="pipeline")` | aus einem Dict mit `{"stages": [...]}` |
| Liste von Stufen | `FullseyeEngine(stages=None, name="pipeline")` | direkt `[("gaussian",0.4,0.5), "otsu"]` (Stufen mit nur einem Namen erhalten a=b=0.5) |

`from_dict` löst ohne den Schlüssel `"stages"` einen `ValueError` aus. `load` liest die JSON-Datei, übergibt sie an `from_dict` und verwendet den Dateinamen (ohne Erweiterung) als `name`.

---

## Methodenübersicht

| Methode | Rückgabewert | Beschreibung |
|---|---|---|
| `load(path)` *(classmethod)* | `FullseyeEngine` | Lädt aus dem JSON von Studio |
| `from_ops(ops, a=0.5, b=0.5, name=…)` *(classmethod)* | `FullseyeEngine` | aus kommagetrenntem ops-String (gemeinsame Regler) |
| `from_dict(d, name=…)` *(classmethod)* | `FullseyeEngine` | lädt aus `{"stages": [...]}` |
| `describe()` | `list[dict]` | pro Stufe `{index, op, a, b, in_sort, out_sort, halcon, known}` |
| `op_names()` | `list[str]` | Operatorname jeder Stufe |
| `input_sort()` | `str \| None` | von der Pipeline erwarteter Eingabe-Sort (in_sort des ersten bekannten op) |
| `output_sort()` | `str \| None` | von der Pipeline gelieferter Ausgabe-Sort (out_sort des letzten bekannten op) |
| `validate()` | `list[dict]` | Strukturprobleme `{index, op, severity, message}`. `[]` bedeutet fehlerfrei |
| `is_runnable()` | `bool` | `True`, wenn sich alle Stufen zu bekannten Operatoren auflösen (kein error) |
| `get_knobs(i)` | `tuple` | Regler `(a, b)` der Stufe `i` |
| `set_knobs(i, a=None, b=None)` | `self` | ändert die Regler der Stufe `i` (verkettbar) |
| `run(image, upto=None, coerce=True)` | ndarray / float / dict | führt die Pipeline aus; `upto` beschränkt auf Stufe 0..upto |
| `run_stepwise(image, coerce=True)` | `list` | Zwischenergebnis nach jeder Stufe (Länge = Anzahl Stufen) |
| `run_file(in_path, out_path=None, upto=None)` | Rohergebnis | liest ein Bild, führt aus und speichert optional Rasterergebnisse |
| `to_dict()` | `dict` | `{"fullseye_pipeline": 1, "name", "stages"}` |
| `to_ops()` | `str` | kommagetrennter ops-String |
| `to_python()` | `str` | Quelltext einer eigenständigen Python-Funktion (identisch zum Export von Studio) |
| `save(path)` | `None` | speichert `to_dict()` als JSON |
| `len(eng)` | `int` | Anzahl der Stufen |

`diagnose_stages(stages)` ist die Funktion, die eine Stufenliste ohne Erzeugung einer Engine validiert — sie ist die eigentliche Implementierung von `validate()`. `severity` ist `"error"` bei unbekannten Operatoren und `"warning"` bei inkonsistenten Sorts zwischen benachbarten Stufen.

### Zum Thema Sort (Typ)

Jeder Operator deklariert einen Ein-/Ausgabe-**Sort**: `image` (gray H×W float64 [0,1]) / `region` (binär {0,1}) / `color` (H×W×3 RGB) / `feature` (Skalar float) / `contour` (XLD dict) / `volume` (3D-Stapel) / `any` (verbindet sich mit allem). `validate()` gibt eine Warnung aus, wenn out→in zwischen benachbarten Stufen nicht übereinstimmt (`any` passt immer).

---

## Anwendungsbeispiele in Python

### Erst validieren, dann ausführen

```python
import fullseye

eng = fullseye.FullseyeEngine.from_ops("gaussian,sobel_amp,otsu")
problems = eng.validate()
if not eng.is_runnable():                      # bei error (unbekannter op) abbrechen
    raise SystemExit(problems)
result = eng.run(frame)                         # liefert region (binär)
```

### Bis zu einer Zwischenstufe / Stufe für Stufe

```python
mid = eng.run(frame, upto=1)                    # bis Stufe 0..1 (gaussian → sobel_amp)
for i, s in enumerate(eng.run_stepwise(frame)):  # Zwischenergebnis jeder Stufe
    print(i, eng.stages[i][0], getattr(s, "shape", s))
```

### Regler anpassen und erneut ausführen

```python
eng.set_knobs(0, a=0.3).set_knobs(2, a=0.4)     # verkettbar
out = eng.run(frame)
```

### Datei-I/O (vollständig im Code)

```python
eng = fullseye.FullseyeEngine.load("edge.json")
result = eng.run_file("in.png", "out.png")      # lesen → ausführen → bei Rasterergebnis speichern
```

### Speichern / Exportieren

```python
eng.save("edge.json")                           # als JSON speichern (in Studio wieder öffnbar)
print(eng.to_ops())                             # "gaussian,sobel_amp,otsu"
print(eng.to_python())                          # als eigenständige Python-Funktion ausgeben
```

Beispielausgabe von `to_python()`:

```python
import fullseye, numpy as np

def pipeline(frame):
    return fullseye.run_pipeline(frame, [
        ('gaussian', 0.500, 0.500),
        ('sobel_amp', 0.500, 0.500),
        ('otsu', 0.500, 0.500),
    ])
```

---

## CLI: `imgevolve.py run`

Eine gespeicherte Pipeline (JSON oder ops-String) lässt sich über die CLI ausführen; intern wird `FullseyeEngine` verwendet.

```
py -3.11 imgevolve.py run <pipeline.json|ops> [inp] [--out PATH]
                          [--upto N] [--stepwise] [--describe] [--to-python] [--a A] [--b B]
```

| Argument / Option | Bedeutung |
|---|---|
| `pipeline` | Pipeline `.json` (Save pipeline aus Studio) oder kommagetrennter ops-String |
| `inp` | Eingabebild (wenn weggelassen, sind nur `--describe` / `--to-python` möglich) |
| `--out PATH` | Speicherziel für das Ergebnis (nur Rasterergebnisse werden gespeichert) |
| `--upto N` | führt Stufe 0..N aus |
| `--stepwise` | meldet das Ergebnis jeder Stufe; mit `--out` werden `PATH_00`, `PATH_01`, … gespeichert |
| `--describe` | zeigt I/O der Pipeline, jede Stufe sowie Validierungsergebnisse (ohne Eingabe endet die Ausgabe hier) |
| `--to-python` | gibt die Pipeline als Python-Funktion aus |
| `--a` / `--b` | gemeinsame Regler beim Aufbau aus einem ops-String (Standard 0,5) |

Beispiele:

```powershell
# nur die Struktur prüfen (kein Bild nötig)
py -3.11 imgevolve.py run edge.json --describe
#   pipeline 'edge': image -> region
#     0. gaussian      a=0.50 b=0.50   [image -> image]
#     1. sobel_amp     a=0.50 b=0.50   [image -> image]
#     2. otsu          a=0.50 b=0.50   [image -> region]

py -3.11 imgevolve.py run edge.json in.png --out result.png       # ausführen und speichern
py -3.11 imgevolve.py run edge.json in.png --stepwise --out step.png  # jede Stufe speichern
py -3.11 imgevolve.py run "gaussian,sobel_amp,otsu" --to-python   # ops-String → Python
```

Eine Pipeline mit unbekannten Operatoren (error) lässt sich mit `--describe` anzeigen, bricht bei der Ausführung jedoch ab und meldet das Problem.

---

## Aufruf aus anderen Projekten (onocollo / evis / hillco usw.)

Da `fullseye` Ein- und Ausgabe vollständig über numpy-Arrays abwickelt, lässt es sich direkt in Robotik-/Vision-Pipelines einbinden. So ist eine Arbeitsteilung **Entwurf in Studio, Ausführung im jeweiligen Projekt** möglich.

```python
import fullseye

# einmalig beim Start laden (leichtgewichtig — hält nur die aufgelösten ops und Regler)
PIPELINE = fullseye.FullseyeEngine.load("assets/segment.json")

def perceive(frame):                            # frame: selbst bereitgestelltes float64 gray [0,1]
    seg = PIPELINE.run(frame)                   # numpy rein, numpy raus (keine Festplatte nötig)
    return seg
```

Wichtige Punkte:

- **Kein Datei-I/O nötig**: numpy-Frames aus Sensor oder Simulator können direkt übergeben werden, das Ergebnis kommt ebenfalls als numpy zurück. Funktioniert auch in eingebetteten oder GPU-Simulationsumgebungen ganz ohne I/O-Backend.
- **Leichtgewichtig**: `load` / `from_ops` halten nur Operatornamen und Regler. Die eigentliche Rechenlast entsteht erst beim Aufruf von `run`.
- **Versionsunabhängig**: Da die Pipeline-JSON reine Daten sind, bleibt der aufrufende Code beim Austausch der Pipeline unverändert. Iterationen in der Forschung (Pipeline in Studio anpassen → JSON aktualisieren) wirken sich nicht auf die Nutzerseite aus.
- **Bei nur einem Operator** kann auch direkt `fullseye.apply(frame, "otsu")` aufgerufen werden, bei mehreren Stufen `fullseye.run_pipeline(frame, [...])` (ein leichterer Pfad ohne die Engine).

Der Wahrnehmungs-Stack (stereo / terrain / flow / detect / registration / pose) arbeitet ebenfalls mit numpy (z. B. `fullseye.disparity_map`). Beispiele finden sich unter `examples/` ([../examples/README.md](../examples/README.md)) sowie in [PERCEPTION.md](PERCEPTION.md) / [PERCEPTION_REALDATA.md](PERCEPTION_REALDATA.md).

---

## Verwandte Dokumente

- [STUDIO_GUIDE.md](STUDIO_GUIDE.md) — Pipeline erstellen und als JSON exportieren
- [GETTING_STARTED.md](GETTING_STARTED.md) — In 5 Minuten loslegen
- [INSTALL.md](INSTALL.md) — Umgebung einrichten (inklusive Embedded und Minimalkonfiguration)
