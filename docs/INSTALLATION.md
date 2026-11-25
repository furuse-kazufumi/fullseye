# Portable full installation (2026-11-24 wheel audit)

`pip install fullseye` is deliberately useful on its own: Studio, common image I/O,
3-D interchange, reports, device adapters and the C/C++ header are standard
dependencies.  To add every remaining backend that this particular machine can
accept, run:

```bash
fullseye setup --yes
```

The command prints each `pip` command and its direct-wheel download estimate before
running it.  It installs one extra at a time, so a failed backend is reported in the
result table and does not prevent the others or RAG setup from completing.  It does
not start Studio with `--yes`.

## Wheel audit

On 2026-11-24 we queried the PyPI JSON release files for the latest release of every
runtime extra in `pyproject.toml`. “All” means a wheel exists for every cell in this
matrix: CPython 3.11, 3.12, 3.13 and 3.14 × `win_amd64`, manylinux `x86_64`,
manylinux `aarch64`, and macOS `arm64`. `py3-none-any` counts as all platforms.
The size is the largest direct wheel observed; it is an estimate, not the transitive
install size.

| extra / direct package | latest checked | max MiB | all 16 targets | default decision |
|---|---:|---:|---|---|
| `opencv` / opencv-python | 5.1.0.95 | 79.2 | no | setup only: current latest has no target in this matrix |
| `skimage` / scikit-image | 0.26.0 | 14.8 | yes | standard |
| `pil` / Pillow | 13.0+ | — | yes | standard (already) |
| `wavelets` / PyWavelets | 1.10.0 | 4.5 | no | setup only: CPython 3.11 missing |
| `gpu` / torch | 2.15.0 | 539.2 | yes | CUDA-only setup group; above the 200 MiB threshold |
| `gpu` / kornia | 0.9.2 | 2.2 | yes | CUDA-only setup group because it requires torch |
| `gpu` / cupy-cuda12x | 14.2.0 | 148.2 | no | setup only: macOS wheel missing |
| `gi` / mitsuba | 3.9.1 | 62.7 | yes | setup only: specialised renderer/runtime |
| `extra` / mahotas | 1.4.19 | 2.0 | no | setup only: Linux aarch64 wheel missing |
| `extra`, `volume`, `threed` / SimpleITK | 2.5.8 | 52.8 | no | setup only: current 3.12–3.14 wheels missing |
| `handpose` / mediapipe | 1.2.3 | 43.3 | yes | setup only: specialised model/runtime |
| `video`, `raster` / imageio | 2.38.2 | 0.3 | yes | standard |
| `video` / imageio-ffmpeg | 0.8.1 | 68.0 | yes | standard |
| `audio` / soundfile | 0.14.0 | 1.3 | yes | standard |
| `volume`, `raster` / tifffile | 2026.11.16 | 0.3 | yes | standard |
| `gltf` / pygltflib | 1.16.5 | <0.1 | yes | standard |
| `lidar` / laspy, lazrs | 2.7.0, 0.9.0 | 0.7 | yes | standard |
| `pcd` / pypcd4 | 1.5.1 | <0.1 | yes | standard |
| `xlsx` / openpyxl | 3.1.5 | 0.3 | yes | standard |
| `e57` / pye57 | 0.4.19 | 17.3 | no | setup only: Linux aarch64 wheel missing |
| `export-verify` / pandas | 3.1.1 | 13.4 | yes | standard |
| `export-verify` / trimesh, numpy-stl | 5.2.2, 4.1.4 | 0.8 | yes | standard |
| `export-verify` / astropy | 8.0.3 | 10.4 | no | setup only: current CPython 3.11 wheel missing |
| `export-verify` / plyfile | 1.1.5 | <0.1 | yes | never default: GPL-3.0-or-later test-only reader |
| `export-verify` / mrcfile, pynrrd, nibabel | 1.5.4, 1.1.4, 5.5.0 | 3.3 | yes | standard |
| `polygon` / matplotlib | 3.11.2 | 11.0 | yes | standard |
| `serial`, `modbus` / pyserial, pymodbus | 3.5, 3.16.2 | 0.2 | yes | standard |
| `symbols` / zxing-cpp | 3.1.1 | 1.1 | yes | standard |
| `mqtt`, `opcua` / paho-mqtt, asyncua | 2.2.0, 2.1.0 | 0.9 | yes | standard |
| `dev` | — | — | n/a | never a runtime default |
| `all` | aggregate | — | mixed | compatibility aggregate; `setup --yes` is failure-isolated |

`export-verify` is deliberately excluded from the default all-in plan because it
contains the GPL-3.0-or-later `plyfile` test reader.  This prevents an accidental
strong-copyleft dependency in a product installation; add it only with
`fullseye setup --include export-verify`.

The C/C++ SDK header is installed at
`<site-packages>/fullseye/include/fullseye_abi.h`; obtain the exact path with:

```bash
python -c "import fullseye, pathlib; print(pathlib.Path(fullseye.__file__).parent / 'include' / 'fullseye_abi.h')"
```

## RAG and Claude Code

`fullseye setup --yes` also installs the `fullseye-ops` Claude skill.  The installer
writes `RAG_MANIFEST.json` alongside `SKILL.md`; it is the inventory of the content
actually available to the skill.  A checkout provides operator notes, capability
recipes, examples, exhibits and literature.  A PyPI wheel provides the compact
catalog and retrieval indexes, packaged examples and Studio help; clone the repository
when the full per-operator note corpus is needed.

When the `claude` command is on `PATH`, setup registers MCP by default.  It uses
`claude mcp add fullseye -- fullseye-mcp` if that console script is installed; until
then it uses the safe fallback `claude mcp add fullseye -- python -P -m fullseye.mcp`.
`-P` prevents a project-local directory named `fullseye/` from taking over the import.
If Claude Code is not installed, setup prints that command and changes no Claude
configuration.
