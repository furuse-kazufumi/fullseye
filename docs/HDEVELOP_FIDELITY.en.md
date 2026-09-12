<!-- i18n-source-sha: 66216f7cdde8 -->
# Fullseye Studio — HDevelop Fidelity Spec (North Star)

[日本語](./HDEVELOP_FIDELITY.md) · **English**

> Goal = make Fullseye Studio (`studio.py`) an **image-processing IDE faithful to MVTec HDevelop**.
> Principle = **"the IDE screen is simple yet multifunctional," "high information density"** (user, 2026-08-15, [[feedback_ide_design_simple_multifunctional]]).
> This document is an implementation spec spanning multiple sessions. Each session reads this and continues implementing.

## Primary sources (always corroborate against these)
- Official documentation: <https://docs.mvtec.com/hdevelopevo/24.11-preview/index.html>
  - UI / Rapid Prototyping: `content/ide/index.html`
  - Execution / Debugging: `content/ide/debugging/index.html`
  - **HALCON Script Reference (syntax)**: `content/halcon_script/index.html`
  - Operators / Reference: `content/reference/index.html`
- Supplementary research (Perplexity, summarized below. **Corroborate claims against the official docs**).

## HDevelop model (Perplexity research summary; verify against official docs)
### Windows (each functions as "one self-contained piece of software"; buttons are compact icons; right-click for a context menu)
- **Graphics Window**: the drawing target for iconics (image/region/XLD). Multiple can be created. `dev_display`/`dev_set_color`/`dev_set_draw`/`dev_set_colored`/`dev_set_lut` act on the current active window.
- **Variable Window**: separates variables into **iconic (thumbnail display so the shape is visible)** and **control (numeric/string text, editable)**. Double-clicking an iconic **displays it in the active Graphics Window** (= `dev_display`). Double-clicking a control opens Variable Inspection. **Variable state updates in sync with step execution.**
- **Program Window**: 1 line = 1 operator call / control statement / assignment. Line numbers, execution cursor (yellow arrow), breakpoints, Step Into/Over/Out/Run.
- **Operator Window**: **operator-selection combo box (autocomplete)** + category tree + search. 1 parameter = 1 line with **name / type / direction (iconic|control × in|out) / default / candidate-value dropdown / min-max / inline doc**. **You can even enter arguments.** Both **inserting into code** and **single-shot execution** are possible, and **the result can be checked in the Graphics Window**.

### How iconics are produced and checked
- An operator's **output parameters** produce iconics: `read_image`→Image, `threshold`→Region, `connection`→ConnectedRegions, `edges_sub_pix`→XLD.
- Checking = the Variable-window thumbnail, double-click display, or `dev_display`. A region is **color-overlaid** on the image (`margin`/`fill` of `dev_set_draw`, multiple colors via `dev_set_colored`).

### Control flow / script syntax (HALCON Script)
- `if / elseif / else / endif`, `for / endfor`, `while / endwhile`, `repeat / until`, `break / continue / return / stop / exit`, assignment `:=`.
- Conditions = boolean expressions. Comparisons `< > <= >= = #`, logic `and / or / xor / not`. Tuples `[1,2,3]`.
- Insertion = Edit▸Insert / toolbar / operator window (inserts the keyword into the program text).
- Comment notation and operator-call notation `operator (Params)` should be **confirmed in the official Script Reference** before implementation.

### Menus (HDevelop)
- File / Edit / Execute / Visualization / Operators / Suggestions / Assistants / Procedures / Window / Help.

## Current Studio → HDevelop gap & roadmap
Evolve in stages from the linear a/b pipeline (a sequence of op,a,b) toward the HDevelop model of variables + control statements + typed arguments.

- **P1 Menu restructuring — done (v18.7)**: standard IDE layout, Window folded into Panels/Graphics/Layout submenus, View with Display mode, Command palette/Language moved to Tools, fixed the vanishing-submenu bug.
- **P2a Operator-argument visualization — done (v18.7)**: `op_arg_roles`/`op_impl_source`/`op_signature_detail` show the knob a/b roles + implementation expression at high density (resolving "can't tell what the argument is").
- **P2b Operator window (HDevelop model) — next**: turn op selection into an **autocomplete combo box** (making better use of the screen) + **argument-input widgets** (name/type/default/candidates/range) + both **code insertion** and **single-shot execution** + **checking the result in a Graphics window**.
- **P3 Sample/script loading path**: a single "Load" flow + preview + description.
- **P4 iconic variable model + panel overhaul**: split the Variable window into **iconic (thumbnails) / control (editable)**, **double-click → Graphics display**, **step-synced updates**, **region color-overlay display**. Make each panel a **self-contained piece of software**, **compact with an icon toolbar**, **high information density**, **right-click → context menu** (throughout).
- **P5 HDevelop script syntax + control flow**: make the Program window support HDevelop syntax (`op (params)`, `:=`, comments, if/else/for/while). Execution model (step/breakpoint/execution cursor) with Variable/Graphics linkage.

## Implementation discipline
- Changes are additive, do not break any op contract, and keep the full suite green (studio tests run offscreen).
- Test each UI behavior headlessly (`QT_QPA_PLATFORM=offscreen`) via the build_window handle.
- Build submenus/QMenus with **an explicit parent** (`QMenu(title, parent)`) to prevent shiboken garbage-collecting them (discovered in v18.7).
- Corroborate HDevelop behavior against the **official documentation** before implementing (Perplexity is supplementary).

## Top priority for next session (found during the live GUI review, 2026-08-15)
1. **★Autonomous UI-operation debug harness**: use QTest to inject real mouse click/press/move/release into every button/drag, automatically catching operational crashes and defects without making the user touch them. Procedure: build_window(offscreen) → QTest.mouseClick every QPushButton/QAction → dock drag → screenshot + state assert at each stage. Calling handlers directly misses bugs specific to real events (e.g., the old GroupedDragging segfault).
2. **Current-image display-window model (HDevelop)**: at least one image display window is always resident (the last one cannot be closed) = the "current window." Double-click display of a variable/object goes **to the current window** (currently new window/main are separate). Unify new_graphics_window/display_variable under the current-window concept.
3. **Fixed (this session)**: the bug where step execution did not update the display (step_to made self-healing). HDevelop-style default layout. Button icon + label. Persistent crash log.
4. **Verification discipline**: before making the user test manually, **I verify e2e in a sandbox (QTest + screenshots)** (explicit user instruction).
   - Note (HDevelop): each Graphics window has a **handle number** (the WindowHandle of `open_window`/`dev_open_window`). The `dev_*` operators (dev_display/dev_set_color/dev_set_draw/dev_clear_window, etc.) draw to the **current window**. `dev_set_window(Handle)` switches the current one. → Studio implementation: a handle number per graphics window + a current-window pointer + variable double-click = draw to the current window + a current-switching UI (click a window or specify a handle).

---

## Implementation record: v18.8 (2026-08-15, Opus5[1m]/ultracode) = autonomous UI-operation debug harness + 3 crash-class bug fixes

**★Implemented the autonomous UI-operation harness** (`tools/studio_ui_harness.py`). It launches Studio in an offscreen subprocess and injects **real mouse events** (`QMouseEvent` sent directly = drag keeps buttons=LeftButton) into every QPushButton / every QAction / **every dock drag** / the variable list / right-click context menus (183 steps across P0–P9). Design:
- **Crash attribution** = each phase start is recorded ahead of time in a JSONL step-log + `faulthandler`. A hard C++ segfault is attributed by the parent via exit code + the last `phase_start` in the step-log + the native traceback.
- **Hang avoidance** = modals (`QDialog.exec`) get a CONFIRM/ERROR stub + `QFileDialog` monkeypatch + a **watchdog QTimer** (closes both `activeModalWidget` **and** `activePopupWidget` = `QMenu.exec` too).
- **Slot-exception capture** = `sys.excepthook` records asynchronous exceptions inside queued signals, tagged with the phase.
- **Resident-window probe** = after each phase, record the survival of `graphics_primary` + whether it is in-MDI.

**★The harness auto-detected → I fixed 3 crashes that only appear under real event injection** (all in `studio.py`, with regression tests in `tests/test_studio.py`):
1. **[High] Access violation (segfault) on the 3D surface button.** `Q3DSurface()` in `show_3d_surface` (formerly line 737) native-segfaults when no OpenGL context exists (offscreen / **Remote Desktop / software GL**); the `try/except` only caught import failures. → Gate it with `_opengl_available()` (a `QOffscreenSurface`+`QOpenGLContext` probe; offscreen is immediately False), and `open_3d` flashes "3-D surface needs OpenGL" when it is None. **It works if GL is present / degrades harmlessly if not / never crashes.**
2. **[High] update_actions raised RuntimeError on a deleted widget.** `b_save` (Save result) lives inside `image_panel` (= the primary Graphics window) and is deleted when the window is destroyed, but a queued `currentRowChanged`→`update_actions` hits `setEnabled` with `RuntimeError: Internal C++ object already deleted`. → An `_enable(cond, *widgets)` helper skips deleted ones (state sync continues for the survivors).
3. **[High] The primary Graphics window was closed, destroying the resident view + global operation buttons** (= the real crash of Codex #2 below, "no resident model where the last window can't be closed"). Closing an MDI subwindow (close button / system-menu "Close" / Ctrl+W) destroyed `view`/`b_save` along with `image_panel`. → A **close-rejecting event filter** on the primary subwindow (`_ResidentCloseGuard`) + `detach_graphics` refusing to detach the primary (`objectName == "graphics_primary"`). **The first step toward the resident current-window model.**

**Verification** = re-running the harness: all 183 steps OK, 0 slot exceptions, 0 crashes, and the primary window stayed alive+in-MDI across all 10 phases (before the fix, the MDI "Close" in P2 made in-MDI=False → deleted in P9 → crash). Studio tests 69 → **72** (updated the detach test to the resident spec + added 3 regressions for resident/update_actions/3D). **Dock drag (suspected GroupedDragging) did not crash across all 25 patterns** (the automated proxy passes; since it differs from the real windowing-system native drag, on-device confirmation is separate).

## Operation-model spec and deliberation (2026-08-15, external AI = Codex read-only; user instruction: "have it critique while considering the use case")

**Use case** = design work to "interactively compose an image-processing algorithm, tune parameters, and validate on holdout" (an HDevelop-experienced user expects an equivalent feel). I had Codex read `studio.py` + this doc and obtained 12 code-backed critiques limited to operation flow (I verified each against the primary code. **Discipline = no blind acceptance [[feedback_external_ai_verify]]**). Adopted points (★ = next implementation target):

- **★[High] No current-Graphics-window state** (`new_graphics_window` 1550– only adds a window; `_render` always goes to a fixed `view`) = **matches this doc's north star, "current-window model."** The operation target and the result-display target diverge. → **P4-current: current-window pointer + handle number + a `dev_set_window`-equivalent switch UI + route `_render`/`display_variable`/`run_op_once` to the current window.** Fix 3 above (resident) is its foundation.
- **★[High] Variable double-click proliferates new windows** (`display_variable(True)` → always a new window). HDevelop displays to the active window. → double-click = to the current window, Shift/button for a new window.
- **★[High] Run once always uses a new window and the input is always the original image** (`run_op_once` 1861–, input fixed to `model.image`). You can't use an intermediate result or a selected variable as input. → current-window display + let the input choose the result of a selected stage/variable.
- **[High] The operator-argument UI is generic a/b** (0..1, fixed 0.5; type/range/candidates/default/name don't change per op) = the unfinished part of P2b in this doc.
- **[High] Variable iconic/control split is by string test only**; contours aren't thumbnailed (`_var_icon` handles only 2D/3D ndarrays).
- **[High] Step execution and the Variable window's "live variables" aren't linked** (`step_to` doesn't call `refresh_variables`; because all stages are precomputed, even not-yet-executed later ones appear to exist).
- **[High] Unapplied edits in the Program window vanish without confirmation** (`confirm_discard` covers only the Pipeline; `code_edit` changes aren't tracked; `sync_program` overwrites).
- **[Medium] No Undo for delete/reorder/Program apply** / **selection always disappears after deletion** (`remove` refreshes without specifying a selection).
- **[High] No operation path to holdout validation within Studio** (`load_image` is single-image only; `load_frame_b` is for 2-frame perception) = the final step of the use case is unfinished. **Needs user judgment (large scope).**

**Deliberated implementation order**: (P4-current) the current-window model ← foundation already laid by the resident work, threading the largest cluster (Codex #1–5) at once → (P2b') per-op argument UI → (step linkage) → (Program dirty tracking). Undo / holdout path are large-scope, so after user confirmation.

### Addendum: current-Graphics-window model (P4-current) implemented (v18.8, this session)
- Assign a **handle number** (`_fs_handle`, a never-reused running counter `_gfx_handle_seq`) to each graphics window. primary=1, new/reattach increment.
- **Current-window pointer** `win._current_gfx` (default = the resident primary) + **`mdi.subWindowActivated`→follow** (clicking a window switches the current one = `dev_set_window`) + a persistent "current: Graphics N" display at the right of the status bar.
- **Variable double-click → current window** (resolves Codex #3; old = always a new window, proliferating). `display_variable(target)` becomes 3-way `"current"`/`"new"`/`"main"` (keeps the old bool compatibility). `v_disp` = new window / `v_here` "Display → current" / right-click also current/new.
- **Run once → current window** (Codex #4) = if current is the primary (default) use a new scratch window (so the result window isn't polluted); if a secondary window is active reuse it (avoiding a new window on every adjustment).
- Helper `_current_view()` (the current window's ImageView; self-heals to the primary when closed) / `_current_handle()`. Regression `test_current_graphics_window_model`. **Harness measurement = window proliferation from variable operations dropped from 8 → 5.** Remaining (Codex #1) = the idea of sending the pipeline result `_render` itself to the current window is a large change to the meaning of result display, so it stays fixed to the primary for now (needs consideration). Next = P2b' per-op argument UI.

### Addendum: per-op argument UI (P2b', Codex #6) implemented
- On op selection, update the a/b labels to role names (e.g. gaussian → "a · blur amount"); a curated and empty = truly unused knob gets the label "(–)" + a disabled spin box. **Non-curated ops keep "a"/"b" (don't falsely claim they're unused).** `_ARG_ROLES` (the existing curated table) + a `_knob_label` helper. Public `win._op_arg_labels`. Regression `test_operator_arg_labels_reflect_selected_op`.

### Addendum: default layout toward image-first (user guidance 2026-08-15)
User guidance = "the image is largest / then the script code / op-selection and variable windows are vertically small / mostly undocked, shown only when needed."
- **Image (central MDI) = largest** (top-left, maximized) / **Program (script code) = a wide strip at the bottom = second** (code needs width, so a narrow right column won't do; avoids the measured problem where minW=916 inflates the right column) / **Operators = a compact right column** (op_hint wraps + category/sample combos minimized in content length so minW goes 850 → 460) / **Variables & Objects, Pipeline·Params, Display, Analysis = hidden by default (on-demand)**, shown via the toolbar + Window▸Panels toggles. `setCorner` confines the bottom Program to below the image only. `layout_version` 2 → 3 (invalidates existing saves to reflect the new default). Regression `test_default_layout_is_image_dominant`. The "Balanced (default)" preset still shows everything as before (reset shows all).

### Addendum: implementing the remaining Codex findings (user chose all 4 items, 2026-08-15)
- **#11 Keep an adjacent selection after deletion** (remove selects min(i, n-1)) / **#9 Protect unapplied Program edits** (track state["code_dirty"], sync doesn't overwrite, apply/Reset clears it, confirm_discard extended) / **#8 Variable-window frontier on step execution** (gray out stages later than the current step as pending).
- **#10 Undo/Redo**: pipeline-edit history (insert/delete/move/reorder/apply/clear/load push a push_undo() snapshot, two-stack swap, Ctrl+Z/Ctrl+Shift+Z, Edit menu, cap 100). Knob adjustments are excluded this time since coalescing is complex.
- **#12 Holdout-validation path**: `run_holdout(stages, image_paths, gt_paths=None)` (Qt-free; api.run_pipeline batch-runs a validation-image folder → per-image ran/failed + timing; if a GT folder exists, `holdout_metric` = IoU(binary)/PSNR(intensity) per-image + mean; honest = no metric emitted without GT) + Studio "Validate on holdout…" (Ctrl+H, Run menu) = folder selection → result table + aggregation + honest note. Connects the imgevolve north star (holdout gate) to the UI. **Remaining (Codex #1) = only the idea of sending the pipeline result `_render` itself to the current window is unimplemented (large semantic change, needs consideration).** Regressions `test_undo_redo_pipeline_edits` / `test_program_editor_tracks_unapplied_edits` / `test_step_through_marks_variable_frontier` / `test_remove_keeps_a_neighbour_selected` / `test_holdout_*`. Studio tests 69 → **82**, full suite 4300 → (next measurement), harness 192 steps, fail0, slot0.
