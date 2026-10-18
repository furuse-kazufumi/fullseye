# OSS landscape notes (verified 2026-09-21)

Data file: `oss_landscape.json` (85 rows, 84 verified, 1 unverified). Sources: GitHub REST API
(`gh api repos/<owner>/<repo>`, authenticated, fields `license.spdx_id`, `pushed_at`,
`stargazers_count`, `description`, `language`), `repos/<r>/license` and `repos/<r>/readme` for
repos where GitHub reports `NOASSERTION`, GitLab API v4 (`?license=true`), PyPI JSON, and the
official sites listed in each row's `source`. Star counts and dates are as returned on 2026-09-21.

## Not verified / verification caveats

- **PrePoMax (GitHub `PrePoMax/PrePoMax`)** — GitHub API returned 404. The canonical repo is
  `gitlab.com/MatejB/PrePoMax` (verified: GPL-3.0-or-later, last activity 2026-09-19, 63 stars).
  The GitHub row is kept with `verified=false` so the wrong URL is not reused.
- **ros2/ros2** — meta-repository; no LICENSE file at root (`repos/ros2/ros2/license` → 404).
  Licence recorded from `ros2/rclcpp` (Apache-2.0). Treat "ROS 2 is Apache-2.0" as true for the
  core packages, not as a statement about every package in a distribution.
- **ngspice** — `github.com/ngspice/ngspice` (last push 2024-06-09) is not the primary hosting;
  the official site points to SourceForge. Licence text in COPYING is mixed (modified BSD for the
  Berkeley core, other terms for specific parts); no single SPDX id.
- **KiCad** — GitLab's auto-detected licence says Boost-1.0 (a bundled file); kicad.org/about/licenses
  says GPL-3.0-or-later for the source. The GitHub mirror API says GPL-3.0. Use GPL-3.0-or-later.
- **libigl** — GitHub API `license.spdx_id` = GPL-3.0, but the repo ships both LICENSE.MPL2 and
  LICENSE.GPL; core headers (e.g. `include/igl/cotmatrix.h`) carry MPL-2.0 headers and the GPL
  code is isolated under `include/igl/copyleft/`. Recorded as MPL-2.0 core + GPL copyleft subdir.
- **py2DIC** — no licence detected by GitHub (`license: null`); do not assume it is redistributable.
- **MeshLib** — source is on GitHub but the LICENSE is a proprietary non-commercial/education
  agreement; commercial use is paid (meshlib.io/license). Not OSI open source.
- **SLStudio** — dual GPL / commercial (LICENSE text).
- **Language field** — taken verbatim from GitHub's language detection. Known oddities:
  ImplicitCAD reports "JavaScript" (the project is Haskell), Robotics Toolbox for Python reports
  "C++", tsfresh/OpenPIV report "Jupyter Notebook". Do not use this field as a hard fact.
- Rows for official sites (OCCT, LinuxCNC, OpenFOAM, ngspice) have no `pushed_at`/`stars`; the
  matching GitHub row carries those.
- Elmer official page (csc.fi/web/elmer) does not state the licence; taken from the GitHub
  LICENSE.md (GPL-2.0, some libraries LGPL). code-aster.org homepage does not state the licence;
  taken from the GitLab API (GPL-3.0).

## Licence classes (Fullseye = Apache-2.0; interop only, never vendoring)

Interop through file formats, subprocess, or an optional `import` does not create a derivative
work in the permissive cases and is the normal way to use the copyleft tools without licence
coupling. The classes below matter for (1) what may be *linked into* a Fullseye process and
(2) what an AI assistant may recommend for a commercial user.

### Permissive (MIT / BSD / Apache / MPL / Boost) — safe to import optionally
CadQuery (Apache-2.0), build123d (Apache-2.0), Manifold (Apache-2.0), sdf/fogleman (MIT),
libfive core + Python bindings (MPL-2.0; Studio/guile are GPL), trimesh (MIT), Open3D (MIT),
PCL (BSD-3), PyVista (MIT), Draco (Apache-2.0), lib3mf (BSD-2), OpenCV (Apache-2.0),
scikit-image (BSD-3), anomalib (Apache-2.0), DICe (BSD-3-style), muDIC (MIT), TIGRE (BSD-3),
tomopy (BSD-3-style), Kalibr (BSD-3-style), ROS 2 core (Apache-2.0), MoveIt 2 (BSD-3),
Drake (BSD-3), MuJoCo (Apache-2.0), Robotics Toolbox for Python (MIT), KISS-ICP (MIT),
Cartographer (Apache-2.0), PX4 (BSD-3), ODrive (MIT), SimpleFOC (MIT), tsfresh (MIT),
PyOD (BSD-2), river (BSD-3), DaSPi (BSD-3 per GitHub / MIT per PyPI), SfePy (BSD-3),
open62541 (MPL-2.0), pymodbus (BSD-3), ngspice core (modified BSD, mixed).

### Weak copyleft (LGPL) — dynamic linking / import is fine, do not copy code
OCCT (LGPL-2.1 + exception), pythonocc-core (LGPL-3.0), FreeCAD and its CAM workbench
(LGPL-2.1), opencamlib (LGPL-2.1), FEniCSx/DOLFINx (LGPL-3.0), CGAL kernel/support
(LGPL-3.0-or-later; most algorithms are GPL — check per header).

### Strong copyleft (GPL) — use via subprocess / files only
OpenSCAD (GPL-2.0-or-later), MeshLab and PyMeshLab (GPL-3.0), libigl `include/igl/copyleft/`
only (cgal, tetgen, quadprog, marching_cubes — GPL; the core headers carry MPL-2.0 headers and
belong in the permissive class even though the GitHub API reports GPL-3.0 for the repo),
CGAL algorithms (GPL-3.0-or-later), Klipper (GPL-3.0),
Marlin (GPL-3.0), pygcode (GPL-3.0), grbl / grblHAL (GPL-3.0-or-later), LinuxCNC (GPL-2.0),
pycam (GPL-3.0-or-later), ASTRA (GPL-3.0), OpenPIV (GPL-3.0), SLStudio (GPL or commercial),
OpenPnP (GPL-3.0), pyspc (GPL-3.0), CalculiX (GPL-2.0), Elmer (GPL-2.0), OpenFOAM (GPL-3.0),
code_aster (GPL-3.0), PrePoMax (GPL-3.0-or-later), KiCad (GPL-3.0-or-later), OpenPLC v3
(GPL-3.0), SOEM (GPL-3.0), IgH EtherCAT (GPL-2.0-or-later).

Note: importing a GPL Python package (e.g. `pyspc`, `pygcode`, `pymeshlab`, `openpiv`) into an
Apache-2.0 process is the contested case; keep these behind subprocess or do not recommend them
for commercial users. Format-level interop (STL/3MF/G-code/PLY/OBJ/STEP files) is unaffected.

### Network copyleft (AGPL) — subprocess / HTTP API only
CuraEngine, PrusaSlicer, OrcaSlicer, Slic3r, OctoPrint, Obico server, ImplicitCAD (all AGPL-3.0).

### Not open source
MeshLib (source-available, non-commercial free, commercial paid).

## Gap observations (areas where no maintained, permissive OSS was found in this survey)

1. **SPC in Python.** `pyspc` is GPL-3.0 and last pushed 2023-01-12; PyPI `spc` last released
   2009-01-26; `DaSPi` (BSD-3/MIT, 7 stars, 2.2.0 on 2026-09-04) is the only actively released
   package found and it is a single-maintainer project. A numpy-first, permissively licensed
   control-chart / capability / Western-Electric-rules module is not established. The GitHub
   search for "spc statistical process control python" returns mostly student and one-off
   notebooks (0–7 stars). This is a positioning opportunity for Fullseye's `spc` family.
2. **Surface roughness parameters (ISO 4287/25178: Ra, Rz, Sa, Sq, Sdr, filtering with
   Gaussian ISO 16610).** None of the surveyed mesh/point-cloud libraries (trimesh, Open3D, PCL,
   PyVista, MeshLab) expose roughness parameters as a documented feature; no dedicated maintained
   Python package was found in this survey (not searched exhaustively — verify before claiming
   "none exists").
3. **Layer-camera print inspection.** Obico (AGPL) covers spaghetti/failure detection from a webcam
   as a server product; no permissive library-level component for per-layer image vs. slice
   comparison (G-code layer ↔ camera frame registration) was found. Interop route: G-code from
   CuraEngine/PrusaSlicer/OrcaSlicer (AGPL, subprocess) → Fullseye `printpath` for layer geometry
   → camera comparison ops.
4. **Weld bead / seam inspection.** Not covered by any surveyed project; anomalib (Apache-2.0)
   provides generic unsupervised anomaly detection and is the closest reusable component
   (image-level, learned), not a geometric bead-profile measurement.
5. **DIC.** DICe (BSD-3-style) is a C++ application last pushed 2024-03-11; muDIC (MIT) last
   pushed 2022-02-08; py2DIC has no licence. There is no actively maintained permissive Python DIC
   library, so a Fullseye DIC op is not displacing anything current.
6. **Structured light.** SLStudio is GPL/commercial and C++/Qt. No permissive Python structured
   light (phase-shift / Gray-code decoding + calibration) library appeared in this survey.
7. **CT reconstruction is well covered**, all permissive except ASTRA: TIGRE (BSD-3, GPU),
   tomopy (BSD-3-style), ASTRA (GPL-3.0). A Fullseye CT op should position as "numpy-only
   fallback / small-scale teaching path; hand off to TIGRE/tomopy for production volumes".
8. **Mesh booleans / implicit modelling are well covered** by Manifold (Apache-2.0), libfive
   core (MPL-2.0), sdf (MIT, last push 2024-08-10), CadQuery/build123d (Apache-2.0 on OCCT
   LGPL). Fullseye SDF/CSG ops should interoperate (mesh in/out via trimesh, STEP via CadQuery)
   rather than compete.
9. **Slicing / G-code.** All full slicers are AGPL-3.0; lib3mf (BSD-2, C with bindings) is the
   permissive path for 3MF; `pygcode` is GPL-3.0 and last pushed 2022-09-19, so a permissive
   G-code parser/writer in Python is a gap that Fullseye `printpath` fills.
10. **Sensor-level simulation (dToF, FMCW radar, light-field) and bearing/acoustic diagnosis**
    were not covered by any project in the requested categories; no maintained permissive
    Python package was surveyed for them (outside the scope of the requested list — verify
    separately before claiming a gap).
11. **Industrial protocols are covered and mostly permissive**: open62541 (MPL-2.0), pymodbus
    (BSD-3). EtherCAT masters (SOEM GPL-3.0, IgH GPL-2.0-or-later) are copyleft, so recommend
    them as separate processes bridging to Fullseye via OPC UA / Modbus / files.

## Follow-up (2026-09-21): the four areas first flagged as uncovered

26 rows appended (25 GitHub-verified via `gh api repos/<r>` + `repos/<r>/license`, 1 official
site: gwyddion.net + SourceForge). Categories used: `roughness`, `sensors`, `diagnosis`.
Motion-magnification rows are filed under `diagnosis` (name suffix `[motion magnification]`)
because only three category values were requested and the tools are used for vibration/structural
diagnosis. Existing rows untouched (85 -> 111 total, 110 verified, 1 unverified).

### Surface roughness / texture — NOT a gap for ISO 25178 field parameters
- **surfalize** (GPL-3.0, Python, 69 stars, push 2026-08-07, PyPI 0.18.3 2026-08-07): README states it
  aims to implement all ISO 25178-2:2021 field parameters (Sa, Sq, Sdr ..., with a cross-check table
  against Gwyddion/MountainsMap), Wolf pruning per ISO 25178-3, ISO 4287 profile sections.
  Copyleft, so subprocess/optional-import only for an Apache-2.0 library.
- **SurfaceTopography** (MIT, Python, 33 stars, push 2026-09-20, PyPI 1.24.0 2026-08-26): rms height,
  power spectrum, plus readers for `gwy`, Mitutoyo, Wyko OPD/OPDx, ISO 25178-71 SDF. Permissive —
  the natural interop target for file formats. README does not list the full ISO 25178 parameter set.
- **Gwyddion** (GPL-2.0, C + Python; 2.71 released 2026-04-14): SPM/profilometry analysis GUI.
  **gwyfile** (MIT) reads/writes its `.gwy` format from pure Python.
- PyPI package named `roughness`: does not exist (HTTP 404 on pypi.org/pypi/roughness/json).
- Remaining gap: a *permissive* (non-GPL) Python implementation of the ISO 25178 parameter set and
  ISO 16610 Gaussian/robust filters was not found; surfalize is the only one and it is GPL-3.0.

### dToF / SPAD / FMCW radar / light-field / TCSPC — partly covered
- Light-field: **plenopticam** (GPL-3.0, PyPI 0.9.3 2022-07-04, push 2025-09-10),
  **Plenoptic Toolbox 2.0** (GPL-3.0, focused plenoptic cameras, push 2024-12-06),
  **LFToolbox** (MATLAB, BSD-style COPYING). No permissive Python light-field library found;
  note that PyPI/GitHub `plenoptic` (plenoptic-org, MIT) is a perceptual-model package, not light-field.
- FMCW/mmWave radar: **radarsimpy** (GPL-3.0, 577 stars, push 2026-09-17; pre-built module from
  radarsimx.com, not on PyPI), **OpenRadar** (Apache-2.0, push 2024-04-30, PyPI 2019-10-31),
  **pymmw** (MIT, push 2021-11-11). The permissive ones are stale; the maintained one is GPL.
- TCSPC/FLIM: **PhasorPy** (MIT, PyPI 0.12 2026-07-20, push 2026-09-08), **ptufile** (BSD-3, PicoQuant
  PTU reader), **napari-flim-phasor-plotter** (BSD-3), **FLIMfit** (GPL-2.0, MATLAB). Well covered
  for phasor/lifetime analysis; these are biology-oriented, not industrial dToF.
- dToF/SPAD depth: only research code found (**dToF-DMDC**, MIT, CVPR 2026, sparse dToF depth
  completion). No maintained library for SPAD histogram → depth (peak finding, pile-up correction,
  multi-return) was found in GitHub search — this remains a gap.

### Bearing / rotating-machinery diagnosis — still a gap at library level
- GitHub search for "bearing fault diagnosis" returns deep-learning paper code (MCNN-LSTM, few-shot,
  transfer learning; 100–450 stars, mostly no licence). Searches for "kurtogram spectral kurtosis
  python", "order tracking vibration rotating machinery", "cepstrum envelope bearing python package"
  returned zero repositories.
- Closest maintained permissive libraries: **endaq-python** (MIT, `endaq.calc` vibration backend:
  PSD/shock, push 2026-08-04), **vibration_toolbox** (MIT, educational, push 2021-07-15),
  **pyOMA2** (MIT, operational modal analysis, push 2026-08-17). **pyvib** (pawsen) is nonlinear
  vibration identification, not bearing diagnosis. **predictive-maintenance-mcp** (MIT, 88 stars,
  push 2026-09-17) is an MCP server exposing envelope-analysis style diagnosis to AI assistants —
  relevant as a positioning reference for Fullseye's RAG, not as a library.
- Gap confirmed: no maintained, permissive Python package for envelope spectrum + bearing fault
  frequencies (BPFO/BPFI/BSF/FTF) + order tracking (tacho resampling) + kurtogram was found.

### Motion magnification — NOT a gap (many implementations), but licence/maintenance issues
- Linear EVM in Python: **eulerian-magnification** (MIT, 503 stars, push 2020-09-20, PyPI 0.22 2017),
  **PyEVM** (no LICENSE file, push 2022-05-05), **hbenbel/Eulerian-Video-Magnification** (MIT,
  push 2023-12-12). Real-time C++: **Live-Video-Magnification** (AGPL-3.0, push 2026-08-01).
- Phase-based: **pbMoMa** (no LICENSE file, push 2017-08-08). Learning-based: **deep_motion_mag**
  (MIT, TensorFlow, push 2018-10-12) and PyTorch re-implementations.
- Everything permissive is 3–9 years unmaintained and the only maintained one is AGPL; the phase-based
  reference has no licence. A maintained, numpy-first linear + phase-based magnifier is therefore a
  reasonable Fullseye position, with interop = plain video/array in, video out.
