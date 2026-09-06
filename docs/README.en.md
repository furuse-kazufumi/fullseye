# Fullseye Documentation Index

**Language:** [日本語](README.md) · [English](README.en.md) · [简体中文](README.zh.md) · [繁體中文](README.tw.md) · [한국어](README.ko.md) · [Deutsch](README.de.md)

> **Please note:** only this index page is translated. The individual documents it links to are, for the moment, available in Japanese only.

**Fullseye** (working name: imgevolve) is a HALCON/HDevelop-class production tool. It combines a numpy-native library of image-processing operators with an HDevelop-style visual pipeline design environment (Fullseye Studio) and an execution runtime (FullseyeEngine). It carries roughly **885** operators (as counted in the registry), provides genuine implementations of **979/2313** actual HALCON operators, and spans 47 categories.

> **Start here → [GETTING_STARTED.md](GETTING_STARTED.md) (up and running in 5 minutes)**

---

## Usage (for users — these four first)

| Document | Contents |
|---|---|
| **[GETTING_STARTED.md](GETTING_STARTED.md)** | Get going in 5 minutes: install → your first pipeline → run it from Studio, the CLI or code → look at the result |
| **[INSTALL.md](INSTALL.md)** | The complete setup guide: prerequisites, `pip install -e .` and which extras to choose, the Windows/Linux installers, minimal and embedded configurations, troubleshooting |
| **[STUDIO_GUIDE.md](STUDIO_GUIDE.md)** | The complete Fullseye Studio guide: the three panels, operator browser, step execution, knobs, Inspector, perception panel, command palette, keyboard shortcuts, export |
| **[ENGINE.md](ENGINE.md)** | FullseyeEngine (design → execution): every method, use from Python, the `run` CLI, calling it from another project |

---

## Operator / API reference

| Document | Contents |
|---|---|
| [OPERATORS.md](OPERATORS.md) | Catalogue of all 521 operators (31 categories, grouped by sort, with the matching HALCON/OpenCV/scikit-image/MATLAB APIs) |
| [EXAMPLES.md](EXAMPLES.md) | Sample code for each operator, with the equivalent call in other libraries |
| [OP_INDEX.json](OP_INDEX.json) | Machine-readable operator index (regenerate it with `imgevolve.py index`) |
| [ADDING_OPS.md](ADDING_OPS.md) | How to add a new operator (evolution, codegen, catalogue and index all follow automatically) |
| [../examples/README.md](../examples/README.md) | Runnable end-to-end example scripts |

## Perception stack (robotics / vision)

| Document | Contents |
|---|---|
| [PERCEPTION.md](PERCEPTION.md) | One-page reference for the perception stack (stereo / terrain / detect / registration / pose / flow / motion) |
| [PERCEPTION_REALDATA.md](PERCEPTION_REALDATA.md) | Measurements on real camera footage (video I/O plus honestly reported figures) |

## HALCON parity / coverage (honest disclosure)

| Document | Contents |
|---|---|
| [HALCON_PARITY.md](HALCON_PARITY.md) | Genuine implementation status (979/2313): whether an operator truly does the same work, rather than merely sharing a name |
| [HALCON_COVERAGE.md](HALCON_COVERAGE.md) | Coverage measured by actually scraping the official reference (v2605) |
| [LIB_COVERAGE.md](LIB_COVERAGE.md) | Cross-library coverage (distinctive operators taken in from beyond HALCON) |
| [PARITY_CROSSBACKEND.md](PARITY_CROSSBACKEND.md) | Parity evidenced by cross-backend agreement between independent implementations (scipy/cv2/skimage) |

## Quality / provenance / reproduction

| Document | Contents |
|---|---|
| [ACCURACY_BENCH.md](ACCURACY_BENCH.md) | The standing accuracy table: evolved champion vs null baseline (holdout) |
| [CHAIN_FUZZ.md](CHAIN_FUZZ.md) | The chain fuzzer — a third quality-assurance layer that shakes operators chained together (diffuse → converge → minimal reproduction) |
| [EVOLUTION_ENVIRONMENT.md](EVOLUTION_ENVIRONMENT.md) | The evolutionary algorithm development environment (diffuse → contract → promote; the counterfactual-utility gate and the bridge between the two operator universes) |
| [PROVENANCE.md](PROVENANCE.md) | Provenance: the record that these are our own work, built from published algorithms |
| [REFERENCES.md](REFERENCES.md) | The literature backing each operator |
| [REPRODUCE.md](REPRODUCE.md) | How to reproduce the figures: seed-driven and deterministic |
| [STATUS.md](STATUS.md) | Where the project stands and what is planned (plan_ref) |

## Release notes / design

| Document | Contents |
|---|---|
| [V13.md](V13.md) | v13 = production readiness + cross-project packaging + the perception stack |
| [V14.md](V14.md) | v14 = the perception stack completed (motion + hardening) |
| [STUDIO_UX.md](STUDIO_UX.md) | The intent and the reasoning behind Fullseye Studio's UX/design improvements |

---

## Quick commands

```powershell
py -3.11 -m pip install -e ".[opencv,gui]"     # install (image I/O + Studio)
py -3.11 studio.py                              # launch Fullseye Studio (= fullseye-studio)
py -3.11 imgevolve.py ops --search edge         # search operators (= fullseye ops --search edge)
py -3.11 imgevolve.py apply gauss_filter in.png out.png --a 0.6
py -3.11 imgevolve.py run pipeline.json in.png --out result.png
py -3.11 imgevolve.py coverage                  # honest coverage figures
```

From Python:

```python
import fullseye, numpy as np
out = fullseye.run_pipeline(frame, ["gaussian", "sobel_amp", "otsu"])
eng = fullseye.FullseyeEngine.load("pipeline.json"); result = eng.run(frame)
```
