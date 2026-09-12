# Vollständiger Leitfaden zu Fullseye Studio

[日本語](./STUDIO_GUIDE.md) · [English](./STUDIO_GUIDE.en.md) · [简体中文](./STUDIO_GUIDE.zh.md) · [繁體中文](./STUDIO_GUIDE.tw.md) · [한국어](./STUDIO_GUIDE.ko.md) · **Deutsch**

**Fullseye Studio** ist eine visuelle Pipeline-Werkbank im Stil von HDevelop. Man sucht Operatoren, ordnet sie an,
dreht an zwei Reglern per Schieberegler, verfolgt Zwischenergebnisse mit Zoom/Pan Stufe für Stufe und exportiert die
fertige Pipeline am Ende als `--ops`-String / Python / JSON. Technisch ist es ein schmales GUI-Frontend über der
`fullseye`-API — die Pipeline-Logik (`PipelineModel`), der Inspector (`inspect_result`) und die Beispielsammlung
(`recipes`) sind allesamt unabhängig von Qt und einzeln mit Unit-Tests versehen.

Dieser Leitfaden listet die Funktionen so auf, wie sie durch Abgleich von `studio.py` (`build_window`) mit dem
tatsächlichen Code ermittelt wurden. Die Absicht hinter UX/Design steht in [STUDIO_UX.md](STUDIO_UX.md), der
Hintergrund der Wahrnehmungspanels aus v14 in [V14.md](V14.md) / [PERCEPTION.md](PERCEPTION.md).

---

## Starten

Die GUI-Extras (PySide6) werden benötigt (`pip install -e ".[gui]"`).

```powershell
py -3.11 studio.py          # direkt aus dem Repository-Wurzelverzeichnis
fullseye-studio             # bei bereits erfolgtem pip install -e . über das Konsolen-Skript
```

Beim Start öffnet sich ein Hauptfenster mit 1320×860 (Titel: Fullseye Studio). Existiert `assets/fullseye.ico`, wird
es als Fenster-/Taskleistensymbol verwendet. Im Ausgangszustand ist bereits ein synthetisches Demobild geladen
(`demo_image`, 256×256 mit Kanten, Blobs und Farbverlauf).

---

## Bildschirmaufbau (3 Bereiche)

Oben befinden sich die **Menüleiste** (File / Edit / View / Run / Help) und eine **Marken-Werkzeugleiste**, unten
die **Statusleiste** (Koordinaten + Pixelwert beim Überfahren mit der Maus, temporäre Meldungen von `flash()`). In
der Mitte liegen drei links-rechts geteilte Bereiche.

| Bereich | Abschnitte (QGroupBox) | Aufgabe |
|---|---|---|
| Links | **SAMPLE PIPELINES** / **OPERATORS** | Beispiele laden, Operatoren durchsuchen |
| Mitte | **PIPELINE** / **SELECTED STAGE · KNOBS** / **EXPORT & I/O** | Pipeline aufbauen, Regler einstellen, exportieren |
| Rechts | **IMAGE** / **DISPLAY & PERCEPTION (v14)** / **ANALYSIS** | Ergebnisanzeige, Farbabbildung/Wahrnehmung, Histogramm/Inspector |

Die anfängliche Aufteilungsbreite beträgt 340 / 360 / 640 px, der rechte Bereich ist elastisch.

---

## Linker Bereich: Operators-Browser

### Beispielpipelines (SAMPLE PIPELINES)
Wählt man aus dem Dropdown eines der **20** fertigen Rezepte (`recipes.py`), wird die Pipeline durch dieses Rezept
ersetzt. Beispiele: "Edge — Sobel + Otsu", "Denoise — bilateral + unsharp", "Segment — blob / coin",
"Count — blobs", "Texture — Gabor" und mehr. Ein bequemer Ausgangspunkt, um erst einmal etwas laufen zu sehen und
den Inhalt zu studieren.

### Operator-Browser (OPERATORS)
- **Kategoriefilter**: "all categories" + 31 Kategorien (smoothing / edges / morphology / segmentation / features /
  texture / region / contour / color / frequency / restoration / 3d …).
- **Suchfeld**: Teilstring-Filterung über Operatorname · HALCON-Alias · Kategorie (mit Lösch-Schaltfläche).
- **Liste**: Jede Zeile zeigt `name [in_sort → out_sort]`. **Per Doppelklick einfügen**. Beim Überfahren mit der
  Maus erscheint ein Tooltip mit "Name / HALCON-Alias / Kategorie / sort-Umwandlung / Erklärung der Regler a, b".

Die Einfügeposition ist "direkt nach der ausgewählten Stufe". Ist keine Stufe ausgewählt, wird am Ende angehängt.

---

## Mittlerer Bereich: Pipeline aufbauen und schrittweise ausführen

### PIPELINE (Stufenliste)
Jede Zeile hat die Form `N. op (a=…, b=…) -> Ergebniszusammenfassung`; der Ergebnisstatus bis zu dieser Stufe
(image/region/feature usw.) erscheint rechts.

- **Umsortieren**: Zeilen per Drag & Drop (InternalMove) vertauschen, oder mit den Schaltflächen
  **↑ Up / ↓ Down** · **Strg+↑ / Strg+↓**.
- **Löschen**: Schaltfläche **Remove** · **Entf**.
- **Die drei Schaltflächen für schrittweise Ausführung**:
  - **⏮ Reset (Pos1)** — zeigt das Rohbild vor Anwendung der Pipeline (Ausgangspunkt des Durchsteppens).
  - **Step ▶ (Strg+→)** — geht eine Stufe weiter.
  - **Run all ▶▶ (Strg+Enter)** — zeigt in einem Zug das Endergebnis (primäre Akzentschaltfläche).

Wählt man eine Stufe aus, wird das Zwischenergebnis bis zu dieser Stufe im rechten IMAGE-Bereich dargestellt, und
auch die ANALYSIS darunter (Histogramm / Inspector) wird synchron aktualisiert. Das entspricht einem
"Schritt-für-Schritt-Debugger".

### SELECTED STAGE · KNOBS (Reglereinstellung)
Zeigt die Details der ausgewählten Stufe (`op_detail`: Name · sort von `in → out` · Kategorie · HALCON-Alias) und
erlaubt die Einstellung über **zwei Schieberegler a / b (0,00 bis 1,00)**. Bewegt man den Wert, wird das Ergebnis
sofort neu berechnet. Ist keine Stufe ausgewählt, sind die Schieberegler deaktiviert (ein bewusstes Design, das
einen bedeutungslosen Regler nicht in einem toten Zustand belässt).

Die Bedeutung der Regler unterscheidet sich je nach Operator (Radius / Schwellwert / σ / Richtung usw.). Was gerade
eingestellt wird, lässt sich am Detail-Label der Stufe und am Tooltip ablesen.

### EXPORT & I/O
- **Export (ops string + Python) … (Strg+E)** — gibt die aktuelle Pipeline sowohl als `--ops "…"`-String als auch
  als eigenständig lauffähige Python-Funktion in einem Dialog aus (zum Kopieren).
- **Save pipeline … (Strg+Umschalt+S)** — speichert die Pipeline als JSON
  (`{"fullseye_pipeline": 1, "stages": [...]}`). Dieses JSON ist die Eingabe für `FullseyeEngine.load` /
  `imgevolve.py run`.
- **Open pipeline … (Strg+Umschalt+O)** — lädt ein gespeichertes JSON.

---

## Rechter Bereich: Anzeige, Wahrnehmung, Analyse

### IMAGE (Ergebnisansicht)
- **Load image … (Strg+O)** — lädt eine Bilddatei als Referenzbild (png/jpg/bmp/tif).
- **Synthetic demo (Strg+D)** — lädt das synthetische Demobild.
- **Save result … (Strg+S)** — speichert das aktuell angezeigte Ergebnis als PNG.
- **Zoom**: Mausrad zoomt an der Cursorposition, Ziehen verschiebt (Pan). **Zoom + (Strg+=) / Zoom − (Strg+-) /
  Fit (Strg+0) / 1:1 (Strg+1)**.
- Bei skalaren feature-Ergebnissen, contour-Ergebnissen oder wenn kein Bild geladen ist, zeigt die Mitte der Ansicht
  eine Meldung an (kein leerer Bildschirm).
- Beim Überfahren mit der Maus zeigt die Statusleiste `x, y, value` (bei Farbbildern RGB).

### DISPLAY & PERCEPTION (v14)
- **Display (Farbabbildung)** — koloriert 2D-Ergebnisse für die Anzeige: `gray` / `shaded relief` /
  `height (color)` / diverse Colormaps (jet, viridis, turbo, magma, plasma, inferno …).
- **3D surface (Strg+3)** — zeigt das aktuelle Ergebnis als drehbare 3D-Oberfläche (nur wenn
  `QtDataVisualization` vorhanden ist / best effort). Nützlich zur Kontrolle von Höhen-/Tiefenkarten.
- **Wahrnehmungspanel (2 Frames)** — mit **Load frame B…** ein zweites Bild laden, Modus wählen und **Run**:
  - `optical flow` — visualisiert den dichten optischen Fluss zwischen zwei Bildern über den Farbton.
  - `motion overlay` — legt bewegte Bereiche über das Originalbild.
  - `stereo depth` — schätzt Tiefe aus der Stereo-Disparität und koloriert sie.
  - `stereo terrain` — Stereo → Punktwolke → Geländehöhenkarte, koloriert.

  Fehlt Frame B oder stimmt die Größe nicht überein, zeigt die Statusleiste einen Fehler und bricht sicher ab.

### ANALYSIS
- **Histogram** — Helligkeitshistogramm des aktuellen 2D-Ergebnisses.
- **Inspector (variable / image / region)** — prüft das Ergebnis je nach sort. Bei image/color: Shape ·
  min/max/mean · Anzahl nicht-endlicher Werte; bei region: Anzahl zusammenhängender Komponenten · Fläche · größte
  Region; bei feature: der Wert; bei contour: Anzahl der Konturen. Bei Binärregionen wird zusätzlich eine
  Merkmalstabelle je Region (`detect.feature_table`) angezeigt.

---

## Command Palette (Strg+P)

`Strg+P` öffnet einen Fuzzy-Search-Dialog, mit dem sich **jede Aktion oder jeder Operator per Namen ausführen**
lässt. Das Ranking erfolgt in der Reihenfolge Präfix-Treffer > Wortpräfix-Treffer > Teilstring-Treffer
(`palette_filter`, unabhängig von Qt und mit Unit-Tests versehen). Aktionen (z. B. `▸ Open image`) stehen zuerst,
danach folgen alle Operatoren (z. B. `op: gaussian`); Enter führt aus. Damit lässt sich sogar das Einfügen von
Operatoren allein über die Tastatur erledigen.

---

## Tastenkürzel

In der Anwendung zeigt **Help ▸ Keyboard shortcuts (F1)** die vollständige Liste als Tabelle (selbstdokumentierend).
Die wichtigsten (aus den `act_*`-Definitionen in `studio.py`):

| Aktion | Tastenkürzel | Aktion | Tastenkürzel |
|---|---|---|---|
| Open image | `Ctrl+O` | Remove stage | `Del` |
| Synthetic demo | `Ctrl+D` | Move stage up / down | `Ctrl+↑` / `Ctrl+↓` |
| Save result | `Ctrl+S` | Clear pipeline | `Ctrl+Shift+Backspace` |
| Open pipeline | `Ctrl+Shift+O` | Zoom in / out | `Ctrl+=` / `Ctrl+-` |
| Save pipeline | `Ctrl+Shift+S` | Fit / Actual size (1:1) | `Ctrl+0` / `Ctrl+1` |
| Export | `Ctrl+E` | 3D surface | `Ctrl+3` |
| Quit | `Ctrl+Q` | Reset to start | `Home` |
| Command palette | `Ctrl+P` | Step forward | `Ctrl+→` |
| Keyboard shortcuts | `F1` | Run all | `Ctrl+Enter` |

Jede Aktion ruft, egal ob über Menü, Werkzeugleiste oder Schaltfläche ausgelöst, denselben Handler auf (eine
Aktion, mehrere Zugänge).

---

## HDevelop-Direktiven `dev_*` zur Anzeigesteuerung

Wie in HDevelop lässt sich **das Anzeigeverhalten aus dem Programm heraus steuern**. Schreibt man im
Program-Fenster eine `dev_*`-Zeile, wird sie nicht als Bildverarbeitungsstufe, sondern als
**Anzeigedirektive** interpretiert und bei Apply angewendet (`docs/HDEVELOP_DEV_OPS.md` erfasst alle 43
`dev_*` vollständig).

| Direktive | Wirkung | Entsprechende UI |
|---|---|---|
| `dev_update_window ('off'|'on')` | Schaltet die automatische Aktualisierung des Grafikfensters | View ▸ Display updates ▸ Graphics window |
| `dev_update_var ('off'|'on')` | Schaltet die automatische Aktualisierung des Variablenfensters | dasselbe, Variable window |
| `dev_update_pc ('off'|'on')` | Schaltet die Aktualisierung des Ausführungscursors | dasselbe, Program counter |
| `dev_update_time ('off'|'on')` | Schaltet die Anzeige der Verarbeitungszeit pro Zeile | dasselbe, Operator timings |
| `dev_update_off ()` / `dev_update_on ()` | Schaltet alles Obige gebündelt aus / ein | Umschalter **Auto-update** in der Werkzeugleiste |
| `dev_set_part (Row1, Col1, Row2, Col2)` | Legt den Anzeigebereich (Zoom/Pan) fest · negativ = Gesamtbild | zusammen mit Mausrad/Fit |
| `dev_set_lut ('gray'|'jet'|'viridis'…)` | Wechselt die Farbabbildung (LUT) | View ▸ Display mode |
| `dev_clear_window ()` | Leert das aktuelle Fenster | — |
| `set_system ('thread_num', N)` | Legt die Anzahl der OpenCV-Worker-Threads fest (0 = Standard/alle) | Tools ▸ System settings |
| `set_system ('operator_timeout', ms)` | Weiches Operator-Timeout (warnt bei langsamen Stufen im Run status) | dasselbe |
| `dev_set_draw ('fill'|'margin')` | Wechselt zwischen Füllung (fill) und Kontur (margin) beim region-Overlay | View ▸ Display mode = region overlay |
| `dev_set_color ('red'|'green'…)` | Farbe des region-Overlays | dasselbe |
| `dev_set_line_width (N)` | Konturbreite für margin (px) | dasselbe |
| `dev_disp_text ('label', Row, Col)` | Textannotation über dem Ergebnis (verschwindet bei der nächsten Zeichnung/`dev_clear_window`) | — |
| `dev_open_window (Row, Col, W, H)` | **Öffnet und platziert** ein Grafikfenster und macht es aktuell (erneutes Apply platziert dasselbe Fenster neu = keine Vermehrung) | Strg+G / Window ▸ Graphics |
| `dev_set_window (Handle)` | Wechselt das aktuelle Fenster über sein Handle | Klick auf ein Fenster |
| `dev_set_window_extents (Row, Col, W, H)` | Position · Größe des aktuellen Fensters (-1 = unverändert lassen) | Fenster ziehen |
| `dev_close_window ()` | Schließt das aktuelle Fenster (das dauerhafte Hauptfenster ist geschützt) | × des Fensters |
| `set_system ('max_graphics_windows', N)` | Obergrenze der Fensteranzahl (Standard 256 · auf allen Pfaden fail-closed) | Tools ▸ System settings ▸ Windows |

**Verwendung**: Setzt man `dev_update_off ()` an den Anfang, lassen sich aufwendige Verarbeitungen oder viele
Änderungen **ohne Zeichenaufwand** durchführen; mit `dev_update_on ()` wird anschließend auf einmal auf den
aktuellen Zustand aktualisiert (dieselbe Performance-Technik wie in HDevelop). Solange Aktualisierungen aus sind,
erscheint rechts in der Statusleiste `updates off: …`, sodass der eingefrorene Zustand nicht wie "kaputt" aussieht.
Derselbe Wechsel ist auch über den Umschalter **Auto-update** in der Werkzeugleiste möglich.

**Hinweis** (ehrlich gesagt): Anders als Pipelinestufen folgt `dev_*` **nicht** `if`/`for` und wird
**bedingungslos angewendet** (löst auch innerhalb eines Zweigs aus). Schreiben Sie es auf oberster Ebene. Nicht
unterstützte `dev_*` führen zu einem Fehler.

**Zum Ausprobieren**: Über **File ▸ dev_* visualization demo** lässt sich ein HDevelop-Programm laden und
ausführen, das tatsächlich das coins-Bild sowie die obigen `dev_*` verwendet (Segmentierung → Regionen mit
cyanfarbener Kontur + Beschriftung dargestellt). Die Beispielbilder dafür liegen unter
**File ▸ Sample images** (8 Stück, Herkunft siehe `studio_assets/sample_images/manifest.json`. Synthetische Bilder
= eigene Arbeit / `coins` · `camera` usw. = BSD-/Public-Domain-Material aus skimage.data. Mit
`tools/gen_sample_images.py` neu erzeugbar).

---

## Mehrsprachigkeit (en / ja / zh, tabellengesteuert)

Die Oberflächensprache lässt sich über **Tools ▸ Language / 言語 / 语言** umschalten (wird gespeichert). Die
Übersetzungen sind zentral in **`studio_assets/i18n.json`** als Tabelle abgelegt und können ohne Codeänderung
erweitert werden:

- `languages` — Sprachliste (bei Ergänzung erscheint sie automatisch im Menü; Englisch ist immer die Basis)
- `tooltips` — Übersetzungen der Tooltips (englischer Originaltext als Schlüssel)
- `strings` — **Übersetzungen für Menü-, Schaltflächen- und Dialogbeschriftungen** (englischer Originaltext als
  Schlüssel. Seit 2026-08-30 vorhanden. Über 40 japanische Einträge sind mitgeliefert; nicht übersetzte Strings
  bleiben auf Englisch = graceful fallback)
- `guide` — Text der Kurzanleitung (Umschalt+F2)

Die Operatorhilfe wird sprachspezifisch angezeigt, sofern `op_help/<name>.<lang>.html` existiert. Ehrlich gesagt:
Zur Laufzeit wechselnde Statustexte (`running…` / `PASS` usw.) sowie der Fließtext der Operator-Hinweise sind
derzeit nicht Teil der Übersetzung (die Übersetzung der Operator-Hinweise ins Englische ist eine künftige Aufgabe,
gekoppelt an eine zweisprachige Version der Docstrings).

## Python-Editor und IDE-Funktionen (2026-08-30)

Studio geht über die Phase hinaus, in der "Code nur aus der Pipeline heraus aufgerufen werden kann", und lässt sich
auch als **Python-Entwicklungsumgebung** nutzen.

- **Python Editor** (File ▸ Python Editor… / in der Galerie "Open in editor"): ein **mehrreitriger** Editor mit
  Syntaxhervorhebung, Zeilennummern und automatischer Einrückung (ähnlich dem Haupt- plus Unterskript-Modell von
  HDevelop, mehrere Skripte gleichzeitig bearbeitbar). **F5 / Run** führt den aktuellen Tab in einem Subprozess aus
  (das Repository liegt im PYTHONPATH, sodass `import fullseye` direkt funktioniert; ungespeicherte Puffer laufen
  über eine Scratch-Kopie, ohne Save zu erzwingen). Über **Samples ▾** lassen sich alle mitgelieferten
  Arbeitsbeispiele in einem neuen Tab öffnen (ohne Pfad geöffnet, sodass die mitgelieferten Beispiele nicht
  versehentlich überschrieben werden können). Der ausführende Interpreter kann unter System settings ▸ Editor
  geändert werden.
- **MDI-Codefenster** (in der Galerie "Open in window"): Beispielcode lässt sich als eigenständiges Fenster
  **beliebig oft nebeneinander** anordnen, um Ausschnitte auszuwählen und zu kopieren (Window ▸ Tile/Cascade
  funktioniert ebenfalls).
- **Ausführungssteuerung**: Klick am Gutter setzt einen Haltepunkt (= Pause), die Schaltfläche **Continue** setzt
  die Ausführung von der aktuellen Zeile bis zum nächsten Haltepunkt/Ende fort, ein Rechtsklick auf eine Stufe mit
  **Run from here** startet ab einer beliebigen Zeile neu (das Gegenstück zu **Run to here**).
- **Variablenüberwachung**: Im Fenster Variables lässt sich ein beliebiger Ausdruck registrieren (`v.mean()` /
  `np.percentile(v, 99)` / `(v > 0.5).sum()` usw.; `v` = ausgewählte Variable, `np` = numpy, `img` = Eingabe), der
  bei jeder Auswahl- oder Pipelineänderung **automatisch neu ausgewertet** wird. Ein fehlgeschlagener Ausdruck
  zeigt in seiner Zeile ⚠ (das Panel stürzt dabei nicht ab). Über **Rechtsklick auf eine Variable ▸ Inspect in
  popup…** erscheint sofort eine nach Typ gegliederte Prüfung samt Perzentilen und Wertvorschau. Bekannte
  Einschränkung (ehrlich gesagt): Da Überwachungsausdrücke synchron im GUI-Thread ausgewertet werden, blockiert ein
  **sehr aufwendiger Ausdruck** (etwa das vollständige Durchsuchen eines riesigen Arrays) währenddessen die
  Oberfläche. Aufwendige Auswertungen sollten vereinfacht oder stattdessen im Python Editor ausgeführt werden.
- **System settings** (Tools ▸ System settings… / Strg+,): Kategoriebaum mit Seitenaufbau. Execution
  (Threads/Timeout) · Windows (Fensterobergrenze) · Display (Standard-LUT / region-Darstellung) ·
  Editor (Schriftgröße / ausführender Interpreter).

## Zusammenhang zwischen Export und Save/Open

Eine in Studio aufgebaute Pipeline lässt sich in 3 Formen mitnehmen.

| Form | Ausgabe über | Einsatz |
|---|---|---|
| `--ops`-String | Export (Strg+E) | zum Einfügen in `imgevolve.py pipeline --ops "…"` / `run "…"` der CLI |
| Python-Funktion | Export (Strg+E) | zum Einbetten als `fullseye.run_pipeline(...)` im eigenen Code |
| JSON | Save pipeline (Strg+Umschalt+S) | zur Ausführung mit `FullseyeEngine.load(...)` / `imgevolve.py run pipeline.json` |

Der zu HDevelop→HDevEngine äquivalente Ablauf **"Entwurf in Studio, Ausführung in Code/CLI"** läuft über das JSON.
Für die Seite, die das JSON entgegennimmt und ausführt, siehe [ENGINE.md](ENGINE.md).

---

## Verwandte Dokumente

- [STUDIO_UX.md](STUDIO_UX.md) — Absicht und Hintergrund von Designsystem und UX-Verbesserungen (Design-Perspektive)
- [V14.md](V14.md) / [PERCEPTION.md](PERCEPTION.md) — Inhalt der Wahrnehmungspanels (flow / stereo / terrain)
- [ENGINE.md](ENGINE.md) — exportierte Pipelines ausführen
- [GETTING_STARTED.md](GETTING_STARTED.md) — in 5 Minuten loslegen
