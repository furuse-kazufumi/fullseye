# Fullseye Studio — UX & design pass (v15)

A usability + visual-design overhaul of `studio.py`, done from a product-design
perspective. This documents *what changed*, *why* (the design principles behind
each choice), and *how to keep improving* it. Everything below is verifiable:
the logic is Qt-free and unit-tested (`tests/test_studio.py`), and the window is
built head­lessly in the suite.

## Design system (derived from the brand mark)

The palette is taken from the Fullseye icon (`assets/fullseye.ico`) so the app and
its mark read as one product — a deliberate move for brand cohesion:

| role | token | value | used for |
|---|---|---|---|
| ground | `NAVY_0` | `#14161d` | window background |
| surface | `NAVY_1` | `#1b1e28` | section cards (QGroupBox) |
| input | `NAVY_2` | `#232734` | fields, buttons, list rows |
| hairline | `LINE` | `#2c313f` | borders, separators |
| text / muted | `TEXT`/`MUTED` | `#e2e5ec` / `#8b91a0` | primary / secondary text |
| **primary accent** | `TEAL` | `#17b8a6` | interaction, selection, focus, "Run all" |
| **secondary accent** | `AMBER` | `#f5a524` | section titles, knob handles, brand title |
| on-accent ink | `INK` | `#0c1116` | text on teal/amber fills |

Principles applied:
- **One accent for "interactive/selected", one for "identity/highlight".** Teal
  always means *you can act here / this is chosen* (hover borders, selection,
  focus ring, the primary button). Amber is reserved for identity (section
  titles, the knob handle, the brand wordmark). Two accents, two jobs — never
  interchangeable, so colour carries meaning instead of decoration.
- **Contrast & state.** Every control has explicit `:hover`, `:pressed`,
  `:focus`, and `:disabled` styling (the old theme had only hover/pressed). Focus
  rings (teal border) make the app keyboard-navigable and visible.
- **Rounded, layered depth.** 7–10 px radii and a three-step surface ramp
  (ground → card → input) give a flat-but-legible hierarchy without shadows.
- **Type.** A real UI stack (`Segoe UI`/`Yu Gothic UI`/`Meiryo`) for chrome;
  monospace only where values are read (inspector, hover read-out, hints).

## Usability improvements

### 1. Keyboard-first — a menu bar with shortcuts
HDevelop users work by keyboard. Every action is now a `QAction` with a shortcut,
grouped into **File / Edit / View / Run / Help** menus (and mirrored on the
toolbar and buttons — same handler, three entry points).

| action | shortcut | action | shortcut |
|---|---|---|---|
| Open image | `Ctrl+O` | Remove stage | `Del` |
| Synthetic demo | `Ctrl+D` | Move stage up / down | `Ctrl+↑` / `Ctrl+↓` |
| Save result | `Ctrl+S` | Clear pipeline | `Ctrl+Shift+⌫` |
| Open / Save pipeline | `Ctrl+Shift+O/S` | Zoom in / out | `Ctrl+=` / `Ctrl+-` |
| Export | `Ctrl+E` | Fit / 1:1 | `Ctrl+0` / `Ctrl+1` |
| Quit | `Ctrl+Q` | 3-D surface | `Ctrl+3` |
| Reset / Step / Run all | `Home` / `Ctrl+→` / `Ctrl+Enter` | | |

*Principle — recognition over recall + Fitts's law:* the highest-frequency
actions are also large toolbar targets; everything is discoverable in a menu
without hunting through panels. **Help ▸ Keyboard shortcuts (F1)** shows the whole
table in-app, so the bindings are self-documenting.

### 2. Status bar for feedback
Transient results (frame B loaded, perception errors, "pipeline cleared") now go
to a status bar via `win._flash(msg)` instead of overwriting the pixel read-out.
The read-out (`x,y,value` on hover) has a permanent home there too. *Principle —
visibility of system status; one consistent place for ephemeral messages.*

### 3. Titled section cards (QGroupBox)
The three panels are now grouped into labelled cards — **Operators**,
**Pipeline**, **Selected stage · knobs**, **Export & I/O**, **Image**,
**Display & perception (v14)**, **Analysis** — with amber uppercase titles.
*Principle — Gestalt grouping + progressive disclosure:* structure is read at a
glance instead of a flat stack of unlabelled widgets.

### 4. Discoverability & affordances
- **Operator tooltips**: hovering a list item shows name, HALCON alias,
  category, sort transform, and what the two knobs are (`op_tooltip`).
- **Selected-stage detail** (`op_detail`): the knobs card names the selected op,
  its `in → out` sort, category and HALCON alias — so you know *what* you are
  tuning, not just "a" and "b".
- **Knob sliders disable when no stage is selected** (dead controls used to sit
  live), and re-enable with the selection.
- **Tooltips on every button** name the action and its shortcut.
- **Accent hierarchy**: exactly one primary button per context ("Run all",
  dialog "Close") is filled teal; everything else is secondary. *Principle — a
  single, obvious primary action reduces decision load.*

### 5. Identity
The window carries the Fullseye icon (title bar / taskbar); the toolbar shows the
mark + wordmark; an **About** dialog (Help menu) presents the icon, version and a
one-line description. A desktop shortcut (`Fullseye Studio.lnk`, launched via
`pyw.exe` so no console window appears) rounds out the install-level polish.

## Before → after

| | before | after |
|---|---|---|
| chrome | a single coral header label | menu bar + branded toolbar + status bar |
| keyboard | none | 20 actions with shortcuts |
| grouping | flat stacks of labels + widgets | 7 titled section cards |
| feedback | a label buried in the right panel | status bar + `flash()` |
| discoverability | op label `name [in→out]` only | tooltips + selected-stage detail |
| palette | one coral accent | brand teal + amber system, full state styling |
| identity | none | window/taskbar icon, toolbar mark, About, desktop shortcut |

## Review round (honest DoD)

The video/perception code went through a 6-agent adversarial review (findings
verified against the real code, then fixed). The Studio redesign was then given a
second-opinion pass by an **external** model (Codex, read-only), per the project's
"verify with a second AI" rule — it caught two real behaviour bugs this pass had
introduced/left, both now fixed and regression-tested:

- **Remove** left the knob sliders enabled and describing the just-deleted stage
  (selection dropped to −1 with signals blocked, so the refresh never ran) →
  `remove()` now calls `on_stage_selected()` to resync.
- **Reset** showed stage 0's output, not the raw pre-pipeline image its label
  promised → a `view_raw` state now makes Reset show `result_upto(-1)` (and Step
  advances out of it).

Lesson (again): an independent reviewer catches state-consistency bugs that the
author's own tests, written to the author's mental model, miss.

## How to keep improving (backlog / methods)

Ranked by usability payoff; each is a self-contained, testable increment:

1. ~~**Drag-to-reorder stages**~~ **(done this pass)** — the pipeline list is now
   `QListWidget.InternalMove`; a drop permutes `model.stages` via each row's stored
   model index. Up/Down buttons and `Ctrl+↑/↓` still work.
2. **Per-op knob semantics.** The two knobs mean different things per op; surface
   the actual meaning (min/max radius, threshold, sigma) by adding an optional
   `knob_doc` to the `Op` dataclass and showing it under the sliders.
3. ~~**Live thumbnails** of each stage's result in the pipeline rows~~ **(done, Studio
   slice 2, 2026-10-20)** — `PipelineModel.stage_preview(i)` hands the list a small
   (48×36) uint8 picture made from the stage cache, never from a recompute; a stage
   never computed shows "未計算 / not computed", one computed with older knobs / another
   image / another bypass shows "再計算が必要 / recompute needed" (no stale picture).
   Region, contour, table, scalar and series results get a picture or a kind symbol; only
   the small arrays are kept (well under 1 MB for a 2048×2048, 5-stage pipeline).
4. **Recent files / recent pipelines** menu (`QSettings`), and remember window
   geometry + splitter sizes between sessions.
5. **Non-blocking apply** for slow ops (`QThreadPool`) with a busy indicator, so
   knob dragging stays responsive on large images.
6. ~~**Empty/So-what states**~~ **(done this pass)** — a scalar-feature, contour,
   or no-image result now shows a centred message in the image area (via
   `ImageView.set_message`) instead of a blank view.
7. ~~**Command palette** (`Ctrl+P`)~~ **(done this pass)** — a fuzzy-filtered
   dialog to run any action or insert any operator by name (`palette_filter` is a
   Qt-free, unit-tested ranker: prefix > word-start > substring).
8. **Onboarding**: a first-run overlay pointing at the operator browser →
   pipeline → knobs → result loop.

9. ~~**Stage result cache**~~ **(done, Studio slice 1, 2026-10-19)** — `PipelineModel`
   keeps one cached result per stage, keyed by the stage prefix (op, a, b of every stage
   up to it) and the base-image version, so a knob drag recomputes only that stage and
   the ones after it; `step_states` / `step_times` walk the stages once (O(n), not
   O(n²)). The stage list shows `⟳ calc` / `↺ cache` per row (`cache_status()`,
   `stage_marks()`). Still open: a non-blocking apply for slow ops (item 5), and a
   cache that spans several base images.
10. ~~**Validity flag**~~ **(done, Studio slice 1)** — a state now carries `ran` (no
    exception), `valid` (True / False / None = not judged) and `reasons`, kept apart.
    A plain array is judged only when clearly bad (non-finite values, empty, or all
    pixels equal); a result table maps its explicit fields (`converged`, `valid`,
    `guf_valid`, `ok`, `success`, `status`, `n_iter` against `max_iter`). Rows show
    `⚠` (distinct from `✕` errors); the status bar says "Run: done / Result: needs
    review (reason)" or "validity not judged". Studio reports; it does not repair the
    operator's numerics. Still open: a per-op `validity` declaration in the registry
    so ops that return plain arrays can say what "sound" means for them.
11. ~~**Project keeps its input reference**~~ **(done, first part, Studio slice 1)** —
    the saved JSON gains an optional `input` (path as given, sha256 of the file, shape,
    dtype); opening reloads a matching file silently, warns on a changed file, reports
    a missing one in Problems and tries the same file name next to the `.json`. Still
    open: embedding small inputs in the project, and a multi-image project.

12. ~~**Stage in → out panel**~~ **(done, Studio slice 2; A/B compare and synchronised zoom, its two
    open parts, done in slice 3 = item 14)** — a dock that shows the selected
    stage's input and output side by side through the same display mapping, with a
    one-line, kind-dependent summary (`_stage_delta_summary`: regions n → m, image
    mean / σ / min / max, table rows × cols, contour count). The two things this item
    left open are done in Studio slice 3 (item 14): A/B compare and synchronised zoom.
13. ~~**Temporary bypass of a stage**~~ **(done, Studio slice 2)** — `PipelineModel.set_bypass`
    / `toggle_bypass`, Ctrl+B and the stage context menu. A bypassed stage passes its input
    through, is greyed and struck through, is part of the cache key, is saved as a 4th
    stage element `true` only when on (older files are byte-identical), appears as
    `# bypassed: op` in the export and the Program text, and its undo entry is labelled
    "bypass". The Program text writes `# bypassed: op (a, b)` and the parser reads it back
    (Apply round-trips). Still open: bypass has no per-run / per-image scope.

14. ~~**Try values side by side, pin A and compare B, synchronised zoom**~~ **(done, Studio
    slice 3; the old item 12 "still open" and ideas 047 / 057 / 058 / 062 / 065)** — three
    parts. **A knob strip** (`knob_candidates`, `PipelineModel.run_variants`): under the
    knob rows, "Try nearby values" shows the selected stage's result at 3 or 5 values around
    the current one (spec step or 1/10 of the range, geometric for a log spec, neighbouring
    choices for an int / choice knob, never outside the range). Only that stage runs, once per
    candidate, from the cached output of the stage before; only small pixmaps are kept; one
    display range for all (`apply_display(..., vmin, vmax)`, `shared_display_range`); an
    optional Shift+drag region of interest of the main view limits what is drawn; choosing a
    picture changes nothing and "Adopt this value" goes through the normal knob path (one
    undo entry). **Pin A / compare B** (`PinnedSnapshot`, `PipelineModel.pin`, the A / B
    dock): a frozen copy of the stage list, input reference, final output (read-only array)
    and display settings; side by side / swipe / blink / difference (absolute, signed,
    ratio); a "what changed" list (`diff_pipelines`); restore A (one undo entry) / adopt B /
    keep both; at most two pins; saved under `pinned` WITHOUT arrays and recomputed on load
    (a pin that cannot be rebuilt is kept and reported in Problems). **Synchronised views**
    (`ViewSyncGroup`): the Stage in → out panes and the A / B panes (optionally the main
    view) zoom, pan and show a crosshair together. Still open: the strip shows one knob at
    a time (a two-knob grid is not built); a pin keeps the stages and the picture but not
    the input image itself; A / B always compares the FINAL output (no "A at stage 3 versus B
    at stage 5"); the swipe boundary is vertical only.
15. **Work modes** (idea ⑭, still open) — "build the pipeline / compare results / inspect
    numbers / write code" as presets of which panels are big and which are folded, without
    losing the input or the results; a temporary "image only, large" view.
16. **Column wizard for typed ops** (idea ②, still open) — open a CSV, map the file's real
    columns to the op's inputs (part id / operator / measured value), show the checked shape
    of the data (parts, operators, missing, repeats), remember the mapping, and stop before
    running on an unsupported shape.

*Method for each:* keep the logic in a Qt-free helper (like `PipelineModel` /
`PerceptionModel` / `op_detail`), unit-test the helper, and let the widget be a
thin wiring layer — the pattern that makes this file testable head­lessly.
