<!-- i18n-source-sha: fb18d30eac9c -->
# Installation / Environment Setup — Complete Guide

[日本語](./INSTALL.md) · **English**

A guide to setting up Fullseye (working name imgevolve) for any purpose, from a development
machine to embedded Linux. If you only want it running in five minutes,
[GETTING_STARTED.md](GETTING_STARTED.en.md) is the shortcut.

Fullseye's design principle is **"a core that runs on numpy + scipy alone" + "every heavy
dependency is optional."** Without an extra backend, only the operators specific to that backend
are disabled; the core always runs (graceful degradation).

---

## (a) Prerequisites

| Item | Requirement |
|---|---|
| Python | **3.11** (`pyproject.toml` sets `requires-python = ">=3.10"`; development and testing use 3.11) |
| Run command | Windows: `py -3.11` / Linux: `python3.11` |
| Core dependencies | `numpy>=1.23`, `scipy>=1.9` (pulled in automatically by `pip install -e .`) |
| OS | Windows 10/11, Linux (embedded included). macOS works too, wherever Python runs |

---

## (b) pip install (what the extras mean and when to use them)

Do an editable install from the repository root.

```powershell
cd <path-to-fullseye>
py -3.11 -m pip install -e .            # core only (numpy + scipy, ~885 operators)
```

Additional backends are selected through **extras** (defined in `pyproject.toml`'s
`[project.optional-dependencies]`).

| extras | Dependencies added | What it enables |
|---|---|---|
| `opencv` | `opencv-python>=4.6` | image file I/O (required by the `apply`/`pipeline` CLI), the `cv_*` operators |
| `skimage` | `scikit-image>=0.20` | the `sk_*` / `xsk_*` families (the base for many auto-generated operators) |
| `pil` | `Pillow>=9` | image I/O fallback, the `xpil_*` family (emboss/posterize/solarize, etc.) |
| `wavelets` | `PyWavelets>=1.4` | the wavelet family (VisuShrink / subbands / packets, etc.) |
| `gpu` | `torch>=2.0`, `kornia>=0.7` | the GPU batch backend (`accel.py`/`bench.py`), the `xkor_*` (kornia) family |
| `extra` | `mahotas>=1.4`, `SimpleITK>=2.2` | `xsitk_*` (curvature flow, etc.), mahotas-derived (Zernike / pftas, etc.) |
| `gui` | `PySide6>=6.5` | **Fullseye Studio** (`studio.py` / `fullseye-studio`) |
| `all` | everything above except GUI (opencv, skimage, pil, wavelets, gpu, extra) | all operators and backends |

Rules of thumb:

```powershell
# the common minimum for real work + image I/O (no GUI, code/CLI-centric)
py -3.11 -m pip install -e ".[opencv]"

# also use the GUI (Studio)
py -3.11 -m pip install -e ".[opencv,gui]"

# fully loaded (GUI included; since `all` does not include GUI, add `gui`)
py -3.11 -m pip install -e ".[all,gui]"

# also try the GPU batch path (needs a CUDA-capable torch)
py -3.11 -m pip install -e ".[gpu]"
```

> `all` does **not** include `gui` (the GUI is kept separate because it serves a distinct purpose).
> If you use Studio, always add `gui` explicitly.

A successful install gives you the following **two console scripts** (`[project.scripts]`).

| Command | Backing entry point | Equivalent direct invocation |
|---|---|---|
| `fullseye` | `imgevolve:main` (CLI) | `py -3.11 imgevolve.py ...` |
| `fullseye-studio` | `studio:main` (GUI) | `py -3.11 studio.py` |

To try it without installing, put the repository root on `PYTHONPATH` and `import fullseye` works
(the console scripts will not be available).

```powershell
$env:PYTHONPATH = "<path-to-fullseye>"
py -3.11 -c "import fullseye; print(fullseye.version())"      # 0.1.0
```

---

## (c) Windows installer

Running `install\install.ps1` performs the environment setup and desktop integration in one shot
(PowerShell).

```powershell
cd <path-to-fullseye>
powershell -ExecutionPolicy Bypass -File install\install.ps1
```

Running this installer does roughly the following.

- Checks that Python 3.11 is present
- Installs Fullseye via `pip install -e .` (with the necessary extras)
- **Creates a Fullseye Studio shortcut (`Fullseye Studio.lnk`)** — registered through `pyw.exe` so it
  launches without a console window, with the `assets\fullseye.ico` icon attached

From then on you can launch Studio from the Start menu / desktop shortcut.

> If the execution policy blocks it, add `-ExecutionPolicy Bypass` (already included in the command
> above).

---

## (d) Linux installer + `.desktop` launcher

Running `install/install.sh` performs the equivalent setup on Linux.

```bash
cd /path/to/imgevolve
bash install/install.sh
```

Running this script does roughly the following.

- Checks that `python3.11` is present
- `pip install -e .` (with the necessary extras)
- **Creates a `.desktop` launcher** — a desktop entry with `assets/fullseye.ico` as its icon is
  registered so you can launch Fullseye Studio from the application menu

From then on you can launch Studio from your desktop environment's app list.

---

## (e) Minimal setup / embedded (embedded Linux)

Fullseye's core is built to run on **numpy + scipy alone**. For embedded uses that need no GUI, no
GPU, and no heavy backends, installing just the core is enough.

```bash
python3.11 -m pip install -e .        # numpy + scipy only. No GUI/torch/opencv needed
```

Key points for embedded use:

- **Input and output complete as numpy arrays.** You can pass numpy frames obtained from a
  sensor/camera directly, without going through any file I/O.

  ```python
  import fullseye, numpy as np
  frame = get_camera_frame()                       # your own float64 gray [0,1]
  seg = fullseye.apply(frame, "otsu")              # no disk write needed
  out = fullseye.run_pipeline(frame, ["gaussian", "sobel_amp", "otsu"])
  ```

- **When you do need file I/O** (`fullseye.load` / `fullseye.save`, `imgevolve.py run`, examples), it
  works if you have **either OpenCV or Pillow** (`imgio` falls back automatically). If you want to
  keep an embedded footprint small, Pillow (`[pil]`) is the lighter of the two.
- You can split the work as **design on the dev machine, execution on the embedded machine.** Build
  the pipeline in Studio on the dev machine and export the JSON; on the embedded machine you just run
  `FullseyeEngine.load("pipeline.json").run(frame)` (no GUI). See [ENGINE.md](ENGINE.md) for details.
- **The perception stack** (stereo / terrain / flow / detect / registration / pose) also runs on
  numpy + scipy (`fullseye.disparity_map`, etc.). It is usable for robotics/vision without extra
  dependencies.

> The GPU (`torch`) path is strictly an **opt-in for batch speedup.** It is unnecessary for
> single-image processing on embedded devices; without it, every operator still runs on the CPU.

---

## (f) Common troubles

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'fullseye'` | not installed / path not set | `pip install -e .`, or add the repository root to `PYTHONPATH` |
| `fullseye` / `fullseye-studio` command not found | console scripts not registered | run `pip install -e .`. If not installed, use `py -3.11 imgevolve.py` / `py -3.11 studio.py` |
| PySide6 ImportError when launching Studio | GUI extras not installed | `pip install -e ".[gui]"` |
| `cannot read <path>` on `apply` / `pipeline` | no image I/O backend | `pip install -e ".[opencv]"` (or `[pil]`) |
| cv2 ImportError from `read_image` / `write_image` (API) | these are **OpenCV-only** | `pip install -e ".[opencv]"`. If you want to get by with Pillow, use `fullseye.load` / `fullseye.save` |
| An operator you expected is missing from `list_ops` / `has` returns unknown | the relevant backend is not installed | add the matching extras (`skimage`/`wavelets`/`extra`, etc.) |
| GPU batch (`accel`/`bench`) is slow on the CPU | `torch` is the CPU build | on GPU use `--device cuda`. On CPU, trivially pointwise work loses to the conversion cost (by design) |
| Studio's 3D surface won't open | `QtDataVisualization` absent | a best-effort feature. It depends on the PySide6 version/build and is silently skipped if absent |

### Image I/O dependencies (important)

The backend required for reading and writing files differs by path.

| Path | Required backend |
|---|---|
| `fullseye.load` / `fullseye.save` (= `imgio`), `imgevolve.py run`, examples | **OpenCV or Pillow** (either one works / automatic fallback) |
| `imgevolve.py apply` / `pipeline` | **OpenCV required** |
| `fullseye.read_image` / `fullseye.write_image` (API) | **OpenCV required** |

`apply` / `run_pipeline` / `FullseyeEngine.run`, which take a numpy array directly, need **no image
I/O backend at all** (they run on the core numpy + scipy alone).

---

## Sanity check

```powershell
py -3.11 imgevolve.py coverage        # honest coverage count (979/2313 HALCON ops genuinely implemented)
py -3.11 imgevolve.py ops --search edge
py -3.11 -c "import fullseye; print(fullseye.version(), len(fullseye.op_names()), 'ops')"
```

`fullseye.version()` returns `0.1.0`, and `op_names()` returns the 860 registry operators
(as of 2026-09-03).
