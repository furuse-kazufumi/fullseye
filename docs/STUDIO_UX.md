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
without hunting through panels.

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
3. **Live thumbnails** of each stage's result in the pipeline rows (`QListWidget`
   item icons) — turns the list into a visual filmstrip.
4. **Recent files / recent pipelines** menu (`QSettings`), and remember window
   geometry + splitter sizes between sessions.
5. **Non-blocking apply** for slow ops (`QThreadPool`) with a busy indicator, so
   knob dragging stays responsive on large images.
6. **Empty/So-what states**: when a result is a scalar feature or an empty
   region, show a friendly message in the image area instead of a blank view.
7. **Command palette** (`Ctrl+P`) to run any op/action by name — the fastest path
   for power users once the op count grows.
8. **Onboarding**: a first-run overlay pointing at the operator browser →
   pipeline → knobs → result loop.

*Method for each:* keep the logic in a Qt-free helper (like `PipelineModel` /
`PerceptionModel` / `op_detail`), unit-test the helper, and let the widget be a
thin wiring layer — the pattern that makes this file testable head­lessly.
