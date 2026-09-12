<!-- i18n-source-sha: b9433dbfb62f -->
# HDevelop `dev_*` operator family — the UI/display control surface (Studio north star)

[日本語](./HDEVELOP_DEV_OPS.md) · **English**

> User note (2026-08-16): "In HALCON, **whether the display updates or not** can also be controlled by op" and "the **display range of the image** can likewise be handled by op" → HDevelop controls **the entire display (graphics windows, variable windows, execution cursor, display range, drawing style) through `dev_*` operators**. Fullseye Studio (`studio.py`) should stay faithful to this HDevelop model.
>
> Primary source = the actual scrape of the MVTec official Operator Reference, `data/halcon_operators.json` (HALCON 26.05, **43 `dev_*` ops** / Graphics chapter 174 ops). Verification URLs are in each op's `url`.

## Why it matters (why it should take priority over async threading)
For Studio's outstanding issue "the GUI freezes on large images / heavy ops," HDevelop has an op-level solution: **`dev_update_off` (turn off all updates) = drives the drawing cost to zero during a loop**. This is **lower risk and more HDevelop-faithful** than a threading change to a shared mutable model (high risk, and regressions are hard to catch with the harness/tests). The display range (`dev_set_part`) is likewise controlled by op.

## Classification of the 43 `dev_*` ops and their Studio implementation status

Legend: ✔ = implemented (an equivalent feature exists) / △ = partial / UI only / ★ = target of this track / ○ = future / — = IDE-specific, out of scope

### A. Drawing-update control (★ user note ①, top priority)
| op | Description | Studio |
|---|---|---|
| `dev_update_window` | on/off for automatically displaying iconic output to the graphics window during execution (default on) | ★ |
| `dev_update_var` | on/off for updating the variable window on every variable change (off = no update until stop) | ★ |
| `dev_update_pc` | on/off for updating the program counter (execution cursor) | ★ |
| `dev_update_time` | on/off for operator time measurement | ★ |
| (`dev_update_off`/`dev_update_on`) | batch toggle of the above (HDevelop library procedure, for performance/timing) | ★ |

### B. Display range / windows (★ user note ②)
| op | Description | Studio |
|---|---|---|
| `dev_set_part` | **change the displayed image part (zoom/pan range)** | ★ |
| `dev_set_window` / `dev_get_window` | switch the active window / get a handle | ✔ (UI current-window model + **program directive**: `dev_set_window (handle)`) |
| `dev_open_window` / `dev_close_window` | open / close a window | ✔ (UI + **program directive**: `dev_open_window (row, col, w, h)` opens, positions, and makes current / `dev_close_window` closes the current one. The resident primary window is protected from close. Re-Apply **repositions the same window** (source-order slot key) and does not multiply them. Limit = `set_system('max_graphics_windows')` (default 256, changeable in System settings, fail-closed on every path)) |
| `dev_clear_window` | clear the active window | ✔ (script directive) |
| `dev_set_window_extents` | position/size of a floating graphics window | ✔ (**program directive**: `dev_set_window_extents (row, col, w, h)`, -1 keeps the current value) |

### C. Iconic display / drawing style
| op | Description | Studio |
|---|---|---|
| `dev_display` | display an image object in the current window | ✔ (display_variable) |
| `dev_disp_text` | display text | ✔ (ImageView.disp_text, script directive) |
| `dev_set_lut` | lookup table (color map) | ✔ (script + 18 display modes) |
| `dev_set_draw` | region fill mode (margin/fill) | ✔ (script directive, overlay_mask mode) |
| `dev_set_color` / `dev_set_colored` | output color | ✔ dev_set_color (script, color name → RGB) / △ colored |
| `dev_set_line_width` | line width (margin outline width) | ✔ (script directive) |
| `dev_set_shape` | region output shape | ○ |
| `dev_set_paint` | gray value output mode | ○ |
| `dev_set_contour_style` | contour fill style | ○ |
| `dev_clear_obj` | remove an iconic object from the DB | — |

### D. Variable / inspection windows
| op | Description | Studio |
|---|---|---|
| `dev_map_var` / `dev_unmap_var` | show/hide the variable window | ✔ (Window▸Panels) |
| `dev_inspect_ctrl` / `dev_close_inspect_ctrl` | inspection window for a control variable | △ (Inspector) |
| `dev_map_prog` / `dev_unmap_prog` | show/hide the main window | — |
| `dev_map_par` / `dev_unmap_par` | visualization parameter dialog | — |

### E. Tools / dialogs / system / errors (HDevelop-IDE specific, out of scope)
`dev_open_tool` `dev_close_tool` `dev_show_tool` `dev_set_tool_geometry` `dev_open_dialog`
`dev_open_file_dialog` `dev_get_system` `dev_set_system` `dev_get_preferences`
`dev_set_preferences` `dev_set_check` `dev_error_var` `dev_get_exception_data` — all of these
are internal controls of the HDevelop IDE and are unnecessary for Fullseye Studio's design-demo purposes (—).

## Reference: the low-level Graphics ops that dev_ wraps (165, non-dev_)
`set_part` / `set_lut` / `set_color` / `set_draw` / `set_paint` / `disp_obj` / `disp_image` /
`disp_region` / `disp_xld` / `get_mbutton` / `get_mposition` (mouse), etc. HDevelop scripts
normally use `dev_*` (which includes the current window and error handling), so Studio also
prioritizes implementing the `dev_*` surface.

## Implementation plan (this track)
1. **Phase A = `dev_update_window/var/pc/time` + `dev_update_off/on`**: `state["dev_update"]`
   (window/var/pc/time, default on) + a checkable toggle in the Visualization menu + toolbar +
   the Program parser recognizes `dev_update_*` as a **directive** (not an image stage) and
   applies it in run_program. While off, the corresponding drawing (show_result / refresh_variables /
   execution cursor) is skipped, and a final update happens on stop. → Achieves op/UI control of
   drawing updates (= the HDevelop-style solution to easing GUI freeze).
2. **Phase B = `dev_set_part(Row1,Col1,Row2,Col2)`**: add `set_part` to ImageView (zoom/pan to a
   rectangle in image coordinates), `dev_set_part(0,0,-1,-1)` = whole. Program parser + application.
3. Future (○) = drawing-style ops such as `dev_clear_window` / `dev_disp_text` / `dev_set_line_width`.

Each stage is regression-checked with offscreen tests + `tools/studio_ui_harness.py` (192 steps).

**Implementation status (2026-08-16)**: Phase A (`dev_update_window/var/pc/time` + `dev_update_off/on`) = **done**
(`state["dev_update"]` / View▸Display updates / toolbar Auto-update / Program directive).
Phase B (`dev_set_part`) = **done** (`ImageView.set_part` / `win._set_part` / directive).
The Program parser recognizes `dev_*` as directives (an unsupported dev_ is an error), collects them
in source order with `extract_dev_directives`, and `apply_program` applies them from the original text.
studio 88 passed / harness 202, 0 fail.
Next (○) = wiring `dev_clear_window` / `dev_disp_text` / `dev_set_lut` (display mode) / `dev_set_draw`
(region overlay) into the script-directive surface (already supported in the UI).

## F. System / settings ops (user note, System chapter 140 ops)
HALCON sets global settings with `set_system`/`get_system` (parameter name + value). HDevelop uses
`dev_set_system`/`dev_get_system` (IDE runtime) + `dev_set_preferences`/`dev_get_preferences`
(IDE settings). The settings that connect directly to Fullseye are:

| op | Setting | Fullseye counterpart |
|---|---|---|
| `set_system('thread_num', N)` / `get_system` | number of parallel threads | the `cv2_threads` knob in `fsruntime` (N1b tail mitigation) / `scale.process_tiled_mt` |
| `set_check('on'/'off')` / `get_check` | error-check control mode (whether fail-closed is enabled) | fail-closed discipline (never break the default on). The runtime is always fail-closed |
| `set_operator_timeout` | per-operator timeout | `FullseyeRuntime(deadline_ms=...)` → TIMEOUT verdict |
| `get_system_info` | license-free system information | environment report (capabilities) |
| `init_compute_device` / `set_compute_device_param` / `optimize_aop` | GPU/compute device, automatic parallelization | future (GPU port, NAS sweep) |

**Implementation status (2026-08-16) = done**: a **Tools ▸ System settings** dialog + `state["system"]` +
QSettings persistence. `thread_num` (OpenCV `cv2.setNumThreads`, directly tied to interactive op speed) /
`operator_timeout` (soft = a slow stage is warned in Run status; native ops cannot be hard-interrupted,
an honest limit) / `check` = fail-closed display. **`set_system(param, value)` was turned into a Program
directive** (HALCON-faithful, in the non-dev_ `_CONFIG_DIRECTIVES`). `get_system` is not supported
because the flat pipeline has no variable model to store return values (honest). The runtime-distribution
settings deadline_ms/high_priority are consolidated into the existing knobs on the fsruntime side (we do
not build an excessive settings surface = the "the IDE is simple yet full-featured" principle).
studio 89→92 / harness 202→204.

## G. `disp_*` display ops (Graphics chapter, implemented 2026-08-30)
HALCON's Graphics chapter has a family of `disp_*` operators that draw directly to a window. Studio does
not mix display ops into the pure-transform `ops.REGISTRY` (they have side effects = a UI); instead it
offers them on two faces, the same as `dev_*`: a **Program directive layer** (`_DISP_DIRECTIVES`) + a
**Python API** (`studio.disp_points3d` / `studio.disp_mesh3d`, the same implementation as the directive's
viewer). Every `disp_*` is recorded in `state["disp_log"]` (testable headless), and failures flash + log
rather than raise (fail-soft).

| directive | HALCON actual op (verification) | Studio behavior |
|---|---|---|
| `disp_image (n)` | `disp_image` | draw the output of stage n (1-based, omitted = final) into the **current graphics window** in the current display mode |
| `disp_region (n)` | `disp_region` | the same as a region overlay (dev_set_draw/color/line_width style) |
| `disp_points3d ('file')` | equivalent to `disp_object_model_3d` (point-cloud face) | open an interactive 3-D viewer window (mesh.read_points formats: ply/pcd/xyz/npy/npz/obj/stl/off) |
| `disp_mesh3d ('file')` | equivalent to `disp_object_model_3d` (mesh face) | same, for a mesh (Lambert splat at the vertices + face centroids, W = wireframe) |
| `disp_object_model_3d ('file')` | `disp_object_model_3d` | HALCON-parity alias: dispatch as a mesh if faces exist, otherwise as a point cloud |

Honest framing: HALCON's `disp_object_model_3d` is a rich op that takes a window handle + camera parameters
+ genParam, while the Studio version is a minimal mapping of "file → viewer window" (equivalent / workalike).
Window management rides on the same handle system as `dev_open_window` (selectable with `dev_set_window`,
sharing the `max_graphics_windows` limit), and re-Apply **reuses the same window** via the source-order slot
key. Calling the 2-D `disp_image` while a 3-D viewer window is current safely redirects to the primary
window (honest limit). Based on measurements, the viewer is a software rasterizer (the same path even
offscreen / over RDP). **Measured performance** (re-measured 2026-08-30, size=480, steady-state median):
200k pts ≈ 66 ms/frame (≈15 fps), 1M pts ≈ 350 ms/frame — **1M cannot be called interactive at full
resolution**, so during drag/wheel it uniformly subsamples down to `DRAG_BUDGET` (250k) points (honestly
showing "preview N pts" in the HUD) and redraws at full resolution on release. The wireframe overlay is
capped at **60,000 edges** (`mesh_edges(cap=60000)`; when exceeded, the overlay itself is skipped). The
headless camera math (`viewer3d_camera`/`viewer3d_project`) is numerically pinned in pytest (depth is
"larger = farther" — occlusion via the painter's algorithm far→near, with a visible-face regression test on
a UV sphere). Like `dev_*`, these are not registered in the per-op note system under docs/ops (for
pure-transform ops), so as not to disturb that system.

## Sources
Primary source = `data/halcon_operators.json` (actual scrape of the MVTec Operator Reference, HALCON 26.05).
Per-op verification examples: [dev_update_window](https://www.mvtec.com/doc/halcon/13/en/dev_update_window.html) /
[dev_set_part](https://www.mvtec.com/doc/halcon/2411/en/dev_set_part.html) /
[set_system](https://www.mvtec.com/doc/halcon/2411/en/set_system.html).
