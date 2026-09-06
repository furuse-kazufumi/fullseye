# Fullseye Dokumentationsindex

**Language:** [日本語](README.md) · [English](README.en.md) · [简体中文](README.zh.md) · [繁體中文](README.tw.md) · [한국어](README.ko.md) · [Deutsch](README.de.md)

> **Hinweis:** Übersetzt ist bisher nur diese Indexseite. Die einzelnen Dokumente, auf die sie verweist, liegen vorerst ausschließlich auf Japanisch vor.

**Fullseye** (Arbeitsname imgevolve) ist ein Werkzeug auf HALCON-/HDevelop-Niveau: eine numpy-native Bibliothek von Bildverarbeitungs-Operatoren, dazu eine visuelle Pipeline-Entwurfsumgebung im Stil von HDevelop (Fullseye Studio) und eine ausführende Laufzeitumgebung (FullseyeEngine). Es umfasst rund **521** Operatoren (gezählt in der Registry), bietet für **269/2313** tatsächliche HALCON-Operatoren eine genuine (wirklich gleichwertige) Implementierung und deckt 31 Kategorien ab.

> **Fangen Sie hier an → [GETTING_STARTED.md](GETTING_STARTED.md) (in 5 Minuten lauffähig)**

---

## Benutzung (für Anwender — zuerst diese vier)

| Dokument | Inhalt |
|---|---|
| **[GETTING_STARTED.md](GETTING_STARTED.md)** | In 5 Minuten loslegen: Installation → erste Pipeline → Ausführung aus Studio, CLI oder Code → Ergebnis ansehen |
| **[INSTALL.md](INSTALL.md)** | Vollständige Anleitung zur Einrichtung: Voraussetzungen, `pip install -e .` und die Wahl der passenden Extras, Installer für Windows/Linux, Minimalaufbau und Einbettung, Fehlerbehebung |
| **[STUDIO_GUIDE.md](STUDIO_GUIDE.md)** | Vollständiger Leitfaden zu Fullseye Studio: die drei Panels, Operator-Browser, schrittweise Ausführung, Regler, Inspector, Perception-Panel, Befehlspalette, Tastenkürzel, Export |
| **[ENGINE.md](ENGINE.md)** | FullseyeEngine (Entwurf → Ausführung): sämtliche Methoden, Verwendung aus Python, das CLI-Kommando `run`, Aufruf aus anderen Projekten |

---

## Operator- / API-Referenz

| Dokument | Inhalt |
|---|---|
| [OPERATORS.md](OPERATORS.md) | Katalog aller 521 Operatoren (31 Kategorien, nach sort gegliedert, mit den entsprechenden APIs von HALCON/OpenCV/scikit-image/MATLAB) |
| [EXAMPLES.md](EXAMPLES.md) | Beispielcode je Operator, samt dem äquivalenten Aufruf in anderen Bibliotheken |
| [OP_INDEX.json](OP_INDEX.json) | Maschinenlesbarer Operatorindex (neu erzeugen mit `imgevolve.py index`) |
| [ADDING_OPS.md](ADDING_OPS.md) | Wie man einen neuen Operator hinzufügt (Evolution, Codegen, Katalog und Index ziehen automatisch nach) |
| [../examples/README.md](../examples/README.md) | Lauffähige Ende-zu-Ende-Beispielskripte |

## Perception-Stack (Robotik / Vision)

| Dokument | Inhalt |
|---|---|
| [PERCEPTION.md](PERCEPTION.md) | Einseitige Referenz zum Perception-Stack (stereo / terrain / detect / registration / pose / flow / motion) |
| [PERCEPTION_REALDATA.md](PERCEPTION_REALDATA.md) | Messungen an realen Videoclips (Video-I/O und ehrlich ausgewiesene Messwerte) |

## HALCON-Parität / Abdeckung (ehrliche Offenlegung, honest disclosure)

| Dokument | Inhalt |
|---|---|
| [HALCON_PARITY.md](HALCON_PARITY.md) | Stand der genuine (wirklich gleichwertigen) Implementierungen (269/2313) — ob ein Operator tatsächlich dasselbe leistet und nicht bloß denselben Namen trägt |
| [HALCON_COVERAGE.md](HALCON_COVERAGE.md) | Abdeckung, gemessen durch tatsächliches Scrapen der offiziellen Referenz (v2605) |
| [LIB_COVERAGE.md](LIB_COVERAGE.md) | Bibliotheksübergreifende Abdeckung (Aufnahme markanter Operatoren jenseits von HALCON) |
| [PARITY_CROSSBACKEND.md](PARITY_CROSSBACKEND.md) | Parität, belegt durch die Übereinstimmung unabhängiger Implementierungen (scipy/cv2/skimage) über die Backends hinweg |

## Qualität / Provenienz / Reproduktion

| Dokument | Inhalt |
|---|---|
| [ACCURACY_BENCH.md](ACCURACY_BENCH.md) | Ständige Genauigkeitstabelle: evolvierter Champion gegen Null-Baseline (Holdout) |
| [CHAIN_FUZZ.md](CHAIN_FUZZ.md) | Der Chain-Fuzzer — eine dritte Schicht der Qualitätssicherung, die zu Ketten verbundene Operatoren durchrüttelt (Diffusion → Konvergenz → minimale Reproduktion) |
| [EVOLUTION_ENVIRONMENT.md](EVOLUTION_ENVIRONMENT.md) | Entwicklungsumgebung für evolutionäre Algorithmen (Diffusion → Kontraktion → Promotion; das Counterfactual-Utility-Gate und die Brücke zwischen den beiden Operatoruniversen) |
| [PROVENANCE.md](PROVENANCE.md) | Provenienz: der Nachweis, dass alles auf Basis veröffentlichter Algorithmen selbst gebaut wurde |
| [REFERENCES.md](REFERENCES.md) | Die Literatur, die jeden einzelnen Operator belegt |
| [REPRODUCE.md](REPRODUCE.md) | Wie sich die Zahlen reproduzieren lassen: seed-gesteuert und deterministisch |
| [STATUS.md](STATUS.md) | Wo das Projekt steht und was geplant ist (plan_ref) |

## Release Notes / Design

| Dokument | Inhalt |
|---|---|
| [V13.md](V13.md) | v13 = Praxistauglichkeit + projektübergreifendes Packaging + Perception-Stack |
| [V14.md](V14.md) | v14 = Perception-Stack fertiggestellt (Motion + Härtung) |
| [STUDIO_UX.md](STUDIO_UX.md) | Absicht und Hintergrund der UX- und Design-Verbesserungen an Fullseye Studio |

---

## Schnellbefehle

```powershell
py -3.11 -m pip install -e ".[opencv,gui]"     # Installation (Bild-I/O + Studio)
py -3.11 studio.py                              # Fullseye Studio starten (= fullseye-studio)
py -3.11 imgevolve.py ops --search edge         # Operatoren suchen (= fullseye ops --search edge)
py -3.11 imgevolve.py apply gauss_filter in.png out.png --a 0.6
py -3.11 imgevolve.py run pipeline.json in.png --out result.png
py -3.11 imgevolve.py coverage                  # ehrliche Abdeckungszahlen
```

Aus Python heraus:

```python
import fullseye, numpy as np
out = fullseye.run_pipeline(frame, ["gaussian", "sobel_amp", "otsu"])
eng = fullseye.FullseyeEngine.load("pipeline.json"); result = eng.run(frame)
```
