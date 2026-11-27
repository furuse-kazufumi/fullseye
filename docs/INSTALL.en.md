---
title: "Installation / Environment Setup — Complete Guide"
description: "Fullseye installation options, optional dependencies, and verification steps."
lang: en
---
<!-- i18n-source-sha: 9f0dbf51f0cb -->
# Installation / Environment Setup — Complete Guide

[日本語](./INSTALL.md) · **English** · [简体中文](./INSTALL.zh.md) · [繁體中文](./INSTALL.tw.md) · [한국어](./INSTALL.ko.md) · [Deutsch](./INSTALL.de.md) · [हिन्दी](./INSTALL.hi.md)

A guide to setting up Fullseye (working name imgevolve) for any purpose, from a development
machine to embedded Linux. If you only want it running in five minutes,
[GETTING_STARTED.md](GETTING_STARTED.en.md) is the shortcut.

Fullseye's Python API core runs on **numpy + scipy**. A standard `pip install fullseye` also
installs Studio (PySide6-Essentials) and Pillow; the heavy image-processing backends remain
optional. Without an extra backend, only the operators specific to that backend are disabled
(graceful degradation).

---

## (a) Prerequisites

| Item | Requirement |
|---|---|
| Python | **3.11** (`pyproject.toml` sets `requires-python = ">=3.11"`; development and testing use 3.11) |
| Run command | Windows: `py -3.11` / Linux: `python3.11` |
| Standard dependencies | `numpy>=1.23`, `scipy>=1.10`, `PySide6-Essentials>=6.5,!=6.12.0`, `Pillow>=13.0` (pulled in automatically by `pip install -e .`) |
| OS | Windows 10/11, Linux (embedded included). macOS works too, wherever Python runs |

---

## (b) pip install (what the extras mean and when to use them)

Do an editable install from the repository root.

```powershell
cd <path-to-fullseye>
py -3.11 -m pip install -e .            # standard: Python API + Studio + Pillow; an op that needs an optional backend names the missing extra when called
```

Additional backends are selected through **extras** (defined in `pyproject.toml`'s
`[project.optional-dependencies]`).

<!-- extras-table:start -->
| Extra | Dependencies added by pyproject.toml |
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


Studio's standard requirement is `PySide6-Essentials>=6.5,!=6.12.0`. Version 6.12.0 is excluded because it reproducibly causes SIGABRT on Linux.

Rules of thumb:

```powershell
# the common minimum for real work + image I/O (Studio is already standard)
py -3.11 -m pip install -e ".[opencv]"

# the former spelling remains compatible (`gui` is an empty alias)
py -3.11 -m pip install -e ".[opencv,gui]"

# fully loaded (Studio is already standard)
py -3.11 -m pip install -e ".[all]"

# also try the GPU batch path (needs a CUDA-capable torch)
py -3.11 -m pip install -e ".[gpu]"
```

> Studio and Pillow are standard dependencies. `gui` and `pil` are empty compatibility aliases
> for existing install commands.

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

After `pip install fullseye`, the first interactive execution of `fullseye` or
`fullseye-studio` registers **Fullseye Studio** once in the Windows Start menu or Linux
application menu. A virtual environment's menu entry starts that environment's Python. Deleting
the entry later does not cause an ordinary command to recreate it. The successful registration
prints this one line:

```text
Registered Fullseye Studio in the Start menu (remove: fullseye-studio --remove-shortcuts)
```

Set `FULLSEYE_NO_SHORTCUTS=1` to suppress it, or add this setting to the INI named by
`FULLSEYE_STUDIO_SETTINGS` (the normal Linux Studio file is `~/.config/Fullseye/Studio.conf`).
CI, commands without a terminal, and a Windows administrator policy that hides Start-menu
programs do not create an entry. Use `fullseye setup` for detailed optional configuration.

```ini
[shortcuts]
auto_register=false
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

- **When you do need file I/O** (`fullseye.load` / `fullseye.save`, `imgevolve.py run`, examples),
  the standard Pillow dependency is available. OpenCV is needed only for `read_image` / `write_image`
  and the `cv_*` family.
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
| PySide6 ImportError when launching Studio | broken standard dependency | `pip install --force-reinstall fullseye` |
| `ImportError: libEGL.so.1` (or similar) when launching Studio on Linux | system libraries Qt needs are missing (pip cannot install them) | Debian/Ubuntu: `sudo apt-get install -y libegl1 libgl1 libxkbcommon-x11-0 libdbus-1-3 libxcb-cursor0` (`libxcb-cursor0` is needed to show the window on screen via xcb; CI checks the offscreen start with the other four). Other distributions: the corresponding packages |
| `cannot read <path>` on `apply` / `pipeline` | broken standard Pillow dependency, or a damaged image | `pip install --force-reinstall fullseye`; if that does not help, inspect the image |
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
