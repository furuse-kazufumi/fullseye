<!-- i18n-source-sha: a77086926760 -->
# The complete guide to Fullseye Studio

[日本語](./STUDIO_GUIDE.md) · **English**

**Fullseye Studio** is an HDevelop-style visual pipeline workbench. You search for operators and
line them up, turn two knobs with sliders, run one stage at a time while looking at the
intermediate results with zoom/pan, and export the assembled pipeline as an `--ops` string /
Python / JSON. Underneath it is a thin GUI front end to the `fullseye` API; the pipeline logic
(`PipelineModel`), the Inspector (`inspect_result`), and the sample set (`recipes`) are all
Qt-independent and unit-tested.

This guide enumerates the features by checking `studio.py` (`build_window`) against the actual
code. The UX/design intent is in [STUDIO_UX.md](STUDIO_UX.md), and the background of the v14
perception panel is in [V14.md](V14.md) / [PERCEPTION.md](PERCEPTION.md).

---

## How to launch

You need the GUI extras (PySide6) (`pip install -e ".[gui]"`).

```powershell
py -3.11 studio.py          # directly from the repository root
fullseye-studio             # if you have run pip install -e ., via the console script
```

On launch a 1320×860 main window opens (title: Fullseye Studio). If `assets/fullseye.ico` is
present it is used as the window/taskbar icon. Initially a synthetic demo image is loaded
(`demo_image`, a 256×256 that includes edges, blobs and a gradient).

---

## Screen layout (3 panels)

At the top there is a **menu bar** (File / Edit / View / Run / Help) and a **brand toolbar**, and
at the bottom a **status bar** (coordinates + pixel value on hover, and the transient messages of
`flash()`). The centre is three panels in a left/right split.

| Panel | Section (QGroupBox) | Role |
|---|---|---|
| Left | **SAMPLE PIPELINES** / **OPERATORS** | Loading samples and the operator browser |
| Centre | **PIPELINE** / **SELECTED STAGE · KNOBS** / **EXPORT & I/O** | Building the pipeline, adjusting knobs, exporting |
| Right | **IMAGE** / **DISPLAY & PERCEPTION (v14)** / **ANALYSIS** | Result display, colour map/perception, histogram/Inspector |

The initial split widths are 340 / 360 / 640 px, and the right panel stretches.

---

## Left panel: the Operators browser

### Sample pipelines (SAMPLE PIPELINES)
Choosing one of the **20** ready-made recipes (`recipes.py`) from the dropdown replaces the
pipeline with that recipe. Examples: "Edge — Sobel + Otsu", "Denoise — bilateral + unsharp",
"Segment — blob / coin", "Count — blobs", "Texture — Gabor", and so on. Handy as a starting point
to run something first and then look at what it does.

### The operator browser (OPERATORS)
- **Category filter**: "all categories" plus 31 categories (smoothing / edges / morphology /
  segmentation / features / texture / region / contour / color / frequency / restoration / 3d …).
- **Search box**: filters operator names, HALCON aliases and categories by substring match (with a
  clear button).
- **List**: each row shows `name [in_sort → out_sort]`. **Double-click to insert.** On hover a
  tooltip shows "name / HALCON alias / category / sort conversion / description of the knobs a,b".

The insertion position is "right after the selected stage". If no stage is selected, it is added
at the end.

---

## Centre panel: building the pipeline and step execution

### PIPELINE (the list of stages)
Each row is of the form `N. op (a=…, b=…) -> summary of the result`, with the state of the result
of running up to that stage (image/region/feature, etc.) shown on the right.

- **Reorder**: swap by dragging a row (InternalMove), or with **↑ Up / ↓ Down** buttons /
  **Ctrl+↑ / Ctrl+↓**.
- **Delete**: the **Remove** button / **Del**.
- **The three step-execution buttons**:
  - **⏮ Reset (Home)** — show the raw image before the pipeline is applied (the origin of a
    step-through).
  - **Step ▶ (Ctrl+→)** — advance one stage.
  - **Run all ▶▶ (Ctrl+Enter)** — jump straight to the final result (the primary accent button).

Selecting a stage draws the intermediate result up to that stage in the IMAGE panel on the right,
and the ANALYSIS below (histogram / Inspector) syncs too. This is what amounts to a "step-through
debugger".

### SELECTED STAGE · KNOBS (knob adjustment)
Shows the details of the selected stage (`op_detail`: name, `in → out` sort, category, HALCON
alias) and adjusts it with **two sliders a / b (0.00–1.00)**. Moving a value recomputes the result
immediately. When no stage is selected the sliders are disabled (a design that doesn't leave a
meaningless knob in a live state).

The meaning of the knobs differs per operator (radius / threshold / σ / direction, etc.). What you
are adjusting can be confirmed in the stage's detail label and the tooltip.

### EXPORT & I/O
- **Export (ops string + Python)… (Ctrl+E)** — output the current pipeline into a dialog (for
  copying) both as an `--ops "…"` string and as a standalone Python function.
- **Save pipeline… (Ctrl+Shift+S)** — save the pipeline as JSON
  (`{"fullseye_pipeline": 1, "stages": [...]}`). This JSON is the input to `FullseyeEngine.load` /
  `imgevolve.py run`.
- **Open pipeline… (Ctrl+Shift+O)** — load a saved JSON.

---

## Right panel: display, perception, analysis

### IMAGE (the result view)
- **Load image… (Ctrl+O)** — load an image file as the reference frame (png/jpg/bmp/tif).
- **Synthetic demo (Ctrl+D)** — load the synthetic demo image.
- **Save result… (Ctrl+S)** — save the displayed result as PNG.
- **Zoom**: cursor-position zoom with the mouse wheel, pan by dragging. **Zoom + (Ctrl+=) / Zoom −
  (Ctrl+-) / Fit (Ctrl+0) / 1:1 (Ctrl+1)**.
- For a scalar feature result, a contour result, or when no image is loaded, a message is shown in
  the centre of the view (never a blank display).
- On hover, the status bar shows `x, y, value` (RGB for colour).

### DISPLAY & PERCEPTION (v14)
- **Display (colour map)** — colour a 2D result for display: `gray` / `shaded relief` / `height
  (color)` / each colour map (jet, viridis, turbo, magma, plasma, inferno …).
- **3D surface (Ctrl+3)** — show the current result as a rotatable 3D surface (only when
  `QtDataVisualization` is present / best-effort). For inspecting a height/depth map.
- **The perception panel (2 frames)** — with **Load frame B…** load a second frame, pick a mode
  and press **Run**:
  - `optical flow` — visualise the dense optical flow between the two frames as hue.
  - `motion overlay` — overlay the moving regions on the original image.
  - `stereo depth` — estimate depth from stereo disparity and colour it.
  - `stereo terrain` — stereo → point cloud → terrain height map, coloured.

  When frame B is missing or the size doesn't match, it shows an error in the status bar and
  safely aborts.

### ANALYSIS
- **Histogram** — the intensity histogram of the current 2D result.
- **Inspector (variable / image / region)** — inspect the result according to its sort. For
  image/color: shape, min/max/mean, non-finite counts; for region: number of connected components,
  area, largest region; for feature: the value; for contour: the number of contours. For a binary
  region it also shows a per-region feature table (`detect.feature_table`).

---

## Command palette (Ctrl+P)

`Ctrl+P` opens a fuzzy-search dialog that lets you **run any action or any operator by name**. It
ranks prefix match > word-start match > substring match (`palette_filter`, unit-tested
Qt-independently). Actions (like `▸ Open image`) come first, then all operators (like
`op: gaussian`), and Enter runs it. You can go all the way to inserting an operator with the
keyboard alone.

---

## Keyboard shortcuts

Inside the app, **Help ▸ Keyboard shortcuts (F1)** shows the full list in a table
(self-documenting). The main ones (from the `act_*` definitions in `studio.py`):

| Action | Shortcut | Action | Shortcut |
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

Each action is invoked by the same handler whether from the menu, the toolbar or a button (one
action, several entry points).

---

## HDevelop `dev_*` display-control directives

As in HDevelop, you can **control the display behaviour from the program**. Writing a `dev_*` line
in the Program window's script is interpreted not as an image stage but as a **display directive**,
applied on Apply (a complete grasp of all 43 `dev_*` is in `docs/HDEVELOP_DEV_OPS.md`).

| Directive | Effect | Corresponding UI |
|---|---|---|
| `dev_update_window ('off'|'on')` | Toggle auto-update of the graphics window | View ▸ Display updates ▸ Graphics window |
| `dev_update_var ('off'|'on')` | Toggle auto-update of the variable window | ditto Variable window |
| `dev_update_pc ('off'|'on')` | Toggle updating the execution cursor | ditto Program counter |
| `dev_update_time ('off'|'on')` | Toggle the per-line processing-time display | ditto Operator timings |
| `dev_update_off ()` / `dev_update_on ()` | Turn all of the above off / on at once | the toolbar **Auto-update** toggle |
| `dev_set_part (Row1, Col1, Row2, Col2)` | Set the display range (zoom/pan); a negative value = whole | use together with mouse wheel / Fit |
| `dev_set_lut ('gray'|'jet'|'viridis'…)` | Switch the colour map (LUT) | View ▸ Display mode |
| `dev_clear_window ()` | Clear the current window | — |
| `set_system ('thread_num', N)` | Set the number of OpenCV worker threads (0 = default/all) | Tools ▸ System settings |
| `set_system ('operator_timeout', ms)` | A soft operator timeout (warns about a slow stage in Run status) | ditto |
| `dev_set_draw ('fill'|'margin')` | Toggle a region overlay between fill and outline (margin) | View ▸ Display mode = region overlay |
| `dev_set_color ('red'|'green'…)` | The colour of the region overlay | ditto |
| `dev_set_line_width (N)` | The outline width of the margin (px) | ditto |
| `dev_disp_text ('label', Row, Col)` | A text annotation over the result (cleared on the next draw / `dev_clear_window`) | — |
| `dev_open_window (Row, Col, W, H)` | **Open, place and make current** a graphics window (re-Apply re-places the same window = doesn't multiply) | Ctrl+G / Window ▸ Graphics |
| `dev_set_window (Handle)` | Switch the current window by handle | click the window |
| `dev_set_window_extents (Row, Col, W, H)` | Position/size of the current window (-1 = keep as is) | drag the window |
| `dev_close_window ()` | Close the current window (the resident main window is protected) | the window's × |
| `set_system ('max_graphics_windows', N)` | The cap on the number of windows (default 256, fail-closed on every path) | Tools ▸ System settings ▸ Windows |

**Use**: putting `dev_update_off ()` at the top lets you do heavy processing or many edits **at no
drawing cost**, then bring the display to the current state all at once with `dev_update_on ()`
(the same performance technique as in HDevelop). While updates are off, `updates off: …` appears at
the right of the status bar, so the frozen state never "looks broken". The toolbar **Auto-update**
toggle does the same switch.

**Note** (honest): unlike a pipeline stage, `dev_*` does not obey `if`/`for` and is applied
**unconditionally** (it fires even placed inside a branch). Write them at the top level. An
unsupported `dev_*` is an error.

**Try it out**: **File ▸ dev_* visualization demo** loads and applies an HDevelop program that
actually uses the `dev_*` above on the coins image (segment → show the regions with a cyan outline
+ labels). The working sample images are **File ▸ Sample images** (8 images; provenance is in
`studio_assets/sample_images/manifest.json`. synthetic = own work / `coins`, `camera`, etc. =
skimage.data's BSD/public-domain. Regenerated with `tools/gen_sample_images.py`).

---

## Multi-language support (en / ja / zh, table-driven)

The UI language is switched at **Tools ▸ Language / 言語 / 语言** (it is remembered). The
translations are a table **centralised in `studio_assets/i18n.json`**, and can be added without a
code change:

- `languages` — the list of languages (add one and it lines up in the menu automatically; English
  is always the base)
- `tooltips` — tooltip translations (the English original is the key)
- `strings` — **the label translations of menus, buttons and dialogs** (the English original is the
  key; added 2026-08-30. Ships with 40+ Japanese items; an untranslated string stays English =
  graceful fallback)
- `guide` — the quick guide text (Shift+F2)

Op help appears per language if `op_help/<name>.<lang>.html` exists. Honest disclosure: the status
wording that changes during a run (`running…` / `PASS`, etc.) and the body of the op notes are for
now not translated (making the op notes English is a future task, paired with making the docstrings
bilingual).

## The Python Editor and IDE features (2026-08-30)

Studio goes beyond the stage where "you can only call code from a pipeline" and can also be used as
a **Python development environment**.

- **Python Editor** (File ▸ Python Editor… / the gallery's "Open in editor"): a **multi-tab** editor
  with syntax highlighting + line numbers + auto-indent (like HDevelop's main + sub scripts, editing
  several scripts at once). **F5 / Run** runs the current tab in a subprocess (the repo is on
  PYTHONPATH so `import fullseye` works as is; an unsaved buffer runs from a scratch copy and doesn't
  force a Save). From **Samples ▾** you can open every worked example in a new tab (it opens without a
  path so you can't accidentally overwrite a shipped sample). The interpreter to run with can be
  changed in System settings ▸ Editor.
- **MDI code windows** (the gallery's "Open in window"): line up sample code as independent windows,
  **as many as you like**, and copy a selected fragment (Window ▸ Tile/Cascade work too).
- **Execution control**: click the gutter for a breakpoint (= a pause), the **Continue** button
  resumes from the running line to the next breakpoint / the end, and a stage's right-click **Run
  from here** restarts from any line (paired with **Run to here**).
- **Variable watch**: register any expression in the Variables window (`v.mean()` /
  `np.percentile(v, 99)` / `(v > 0.5).sum()`, etc.; `v` = the selected variable, `np` = numpy, `img`
  = the input) and it is **re-evaluated automatically** on every selection change / pipeline change.
  A failed expression shows a ⚠ on its row (the panel doesn't crash). A variable's **right-click ▸
  Inspect in popup…** immediately shows a per-type inspection + percentile + value preview. Known
  limitation (honest): a watch expression is evaluated synchronously on the GUI thread, so a **very
  heavy expression** (a full sweep of a huge array, etc.) makes the UI wait during it. Make the
  expression lighter, or run heavy aggregation in the Python Editor.
- **System settings** (Tools ▸ System settings… / Ctrl+,): a category tree + paged layout. Execution
  (threads / timeout), Windows (window cap), Display (default LUT / region drawing), Editor (font
  size / interpreter to run with).

## The relationship between Export and Save/Open

A pipeline built in Studio can be taken out in three forms.

| Form | How to produce it | Where to use it |
|---|---|---|
| `--ops` string | Export (Ctrl+E) | paste into the CLI's `imgevolve.py pipeline --ops "…"` / `run "…"` |
| Python function | Export (Ctrl+E) | embed in your own code as `fullseye.run_pipeline(...)` |
| JSON | Save pipeline (Ctrl+Shift+S) | run with `FullseyeEngine.load(...)` / `imgevolve.py run pipeline.json` |

The HDevelop→HDevEngine-equivalent flow of **design in Studio, execute in code/CLI** is done via
the JSON. For the side that receives and executes the JSON, see [ENGINE.md](ENGINE.md).

---

## Related documents

- [STUDIO_UX.md](STUDIO_UX.md) — the intent and background of the design system and UX improvements (the design view)
- [V14.md](V14.md) / [PERCEPTION.md](PERCEPTION.md) — what's inside the perception panel (flow / stereo / terrain)
- [ENGINE.md](ENGINE.md) — execute the pipeline you exported
- [GETTING_STARTED.md](GETTING_STARTED.md) — get going in 5 minutes
