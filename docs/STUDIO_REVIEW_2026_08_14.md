# Fullseye Studio — verified UI review (2026-08-14)

Three reviewers (Codex `C#`, Copilot `P#`, a visual pass `V#`) produced findings against
`studio.py`. Every finding below was **re-checked against the real code** — the reviewers'
line numbers were stale, so each verdict quotes the code as it actually stood, and several
findings were measured at runtime (offscreen Qt) rather than argued from static reading.

Two of them did not survive contact with the code. They are marked FALSE-POSITIVE with the
evidence that disproves them.

Line numbers are **pre-fix** (`studio.py` @ 1272 lines).

---

## 1. Verdicts

| # | Finding | Verdict | Evidence |
|---|---|---|---|
| C1 / P1 | Pipeline runs synchronously on the GUI thread | **CONFIRMED** | `studio.py:866` `val = model.result_upto(idx if idx >= 0 else len(model.stages) - 1)` — called straight from the `currentRowChanged` slot. No `QThread`/`QThreadPool`/`QRunnable`/`QtConcurrent`/`threading` token exists anywhere in the file. |
| C2 | Knob slider recomputes quadratically + an extra render | **CONFIRMED (measured)** | `studio.py:934-935` `refresh_stage_list(select=i)` then `show_result()`. `refresh_stage_list` calls `model.step_states()` (`:809`), which re-runs *every prefix* (`:88-95`). Measured: **8 `result_upto()` calls for one knob tick on a 6-stage pipeline** (6 from `step_states` + 2 renders). |
| C3 | Several refresh paths render the result twice | **CONFIRMED (measured)** | `refresh_stage_list` un-blocks signals at `:820` *before* `stage_list.setCurrentRow(select)` at `:824`, so `currentRowChanged → on_stage_selected → show_result` fires, and then the caller renders again. Measured **2 renders** per edit (`move`, `add_op`, `clear_pipe`, `load_sample`, `open_pipe`, `on_rows_moved`, and `build_window`'s own tail at `:1258`). |
| C4 / P2 | Exceptions outside the narrow pipeline `try` can kill the callback | **CONFIRMED** | The `try` at `:862-871` wraps **only** `result_upto`. Everything after runs unguarded on backend output: `inspect_result` (`:872`), `apply_display` (`:884`), `_to_qimage` (`:885`), `imgio.ensure_gray` (`:891`), `histogram_image` (`:892`). Concrete repro: a 0-size 2-D result under the "shaded relief" display raises `ValueError: Shape of array too small to calculate a numerical gradient` from `apply_display`, outside the guard. |
| C5 / P5 | File I/O errors uncaught | **CONFIRMED** | `:981` `model.set_image(imgio.load(path))` — `imgio.load` raises `FileNotFoundError` on a missing/undecodable file (verified). `:992` `imgio.save(...)`. `:1225` `open(path,"w").write(...)`. `:1231` `json.loads(open(path).read())` — raises `JSONDecodeError` (verified). `:1204` `pmodel.set_frame_b(imgio.load(path))`. None had a `try`. |
| C6 / P4 | No dirty-state tracking, no confirmation on destructive edits | **CONFIRMED** | No `dirty` token in the file. `clear_pipe` (`:1000-1003`) does `model.stages = []` unconditionally; `load_sample` (`:958-963`) and `open_pipe` (`:1227-1232`) replace the pipeline outright; `QMainWindow` was used unsubclassed (`:566`) so there was no `closeEvent` at all. |
| C7 | Action/button enabled states don't follow selection/output | **CONFIRMED (measured)** | The only `setEnabled` in the whole window was `:916` `sa.setEnabled(valid); sb.setEnabled(valid)` (the two knobs). Measured on an empty pipeline with no selection: `remove`, `move_up`, `move_down`, `save_result`, `export`, `surface_3d`, `step` **all reported `enabled=True`**. |
| C8 / P10 | Window-wide editing shortcuts fire while typing | **PARTIAL** | Context is real: all actions defaulted to `WindowShortcut` (measured `ShortcutContext.WindowShortcut` for `act_remove`, `:589-599`). But the claim as written is **half wrong** — a focused `QLineEdit` *does* claim `Del`, `Home` and `Ctrl+Right` for itself via `ShortcutOverride` (measured: `True/True/True`), so typing in the search box was never clobbered by those. What genuinely leaked: **`Ctrl+Up` / `Ctrl+Down` (measured `False/False` — not claimed)**, which moved a pipeline stage mid-word; and `Del`/`Home` when focus sat on a non-editable widget (the operator list, the read-only inspector — measured `False/False`), where `Home` reset the pipeline instead of jumping to the first row. |
| C9 / P11 | Command palette may run the chosen command twice | **CONFIRMED (measured)** | `:1145-1146` wired **both** `lst.itemActivated` and `lst.itemDoubleClicked` to `run_sel()`. `QAbstractItemView::mouseDoubleClickEvent` emits `doubleClicked` **and then** `activated` when `SH_ItemView_ActivateItemOnSingleClick` is 0 (measured 0 on this platform). Driving the real palette: selecting `op: gaussian` and delivering that pair took the pipeline from **0 stages to 2**. |
| C10 / P3 | Drag/drop reorder is race-prone | **FALSE-POSITIVE** | Exercised the exact call `QListWidget::dropEvent` makes — `stage_list.model().moveRow(...)`, which is what emits `rowsMoved` — across **all 30 single-row (src, dst) moves on a 5-stage pipeline: 0 mismatches** between the visible order and `model.ops_string()`. The `UserRole` remap at `:854-856` is correct, and multi-row drops (the one case where the mid-drop `refresh_stage_list` could invalidate `dropEvent`'s `QPersistentModelIndex` loop) cannot occur because `stage_list.selectionMode()` is `SingleSelection` (measured), so `dropEvent` issues exactly one `moveRow` per drop. The `state["reordering"]` guard is belt-and-braces: `clear()`/`addItem()` emit `rowsRemoved`/`rowsInserted`, never `rowsMoved`. **No concrete failing sequence could be constructed. Not treated as a bug.** |
| C11 / P5 | Malformed pipeline JSON escapes validation | **CONFIRMED** | `:112` `self.stages = [[s[0], float(s[1]), float(s[2])] for s in d.get("stages", [])]`. Measured: `{"stages":[["gaussian"]]}` → `IndexError`; `{"stages":"abc"}` → `IndexError`; `{"stages":[None]}` → `TypeError` — all uncaught in `open_pipe`. (The reviewers' "breaks list rebuilding" half is overstated: the throw happens inside `load_dict`, before any rebuild; and an *unknown op name* was accepted and did rebuild fine, because the Problems panel flags it.) |
| C12 / V1 | `* { outline:none; }` kills focus indicators globally | **CONFIRMED** | `studio.py:285` — literally the first rule in `THEME`. No `:focus` rule existed for `QPushButton` or `QToolButton` at all. |
| C13 / P8 / P9 | No `accessibleName`, no label buddies; raw error text in tooltips | **CONFIRMED** | Neither `setAccessibleName` nor `setBuddy` appeared anywhere in the file. `:818` `it.setToolTip("runtime error: " + str(st.get("message", "")))` — measured **736-character** tooltip and a **649-character** Problems row for a long op name. |
| C14 / P7 | Hardcoded fixed/min sizes reduce adaptability | **CONFIRMED (not fixed — see §3)** | `:493` `self.setMinimumSize(380, 380)`; `:460` `container.setMinimumSize(560, 460)`; `:713` `problems_list.setFixedHeight(74)`; `:784` `hist_view.setFixedHeight(64)`; `:786` `inspector.setFixedHeight(150)`. |
| C15 | Perception errors only in a transient status message | **CONFIRMED** | `:1211` `flash("perception: " + str(e)); return` — and `flash` is `status.showMessage(msg, 6000)` (`:655`). Nothing reached the Problems list or the Inspector. |
| P6 | Silent `except: pass` swallows detect enrichment errors | **PARTIAL** | The swallow is real (`:880-881`), but it was **never a bare `except:`** as reported — the code already read `except Exception:`. Verdict: real smell, misdescribed severity. |
| V2 | Disabled a/b sliders still render an AMBER (enabled-looking) handle | **CONFIRMED (measured)** | `:335` `QSlider:disabled::handle:horizontal { background:#4a4f5c; }`. Qt QSS requires the **sub-control before the pseudo-state**, so this selector silently never matched. Rendered a themed slider and counted amber (`#f5a524`) pixels: **enabled = 200, disabled = 200** — identical. The reviewer's proposed form `QSlider::handle:horizontal:disabled` is correct. |

**Counts — CONFIRMED 13 · PARTIAL 2 (C8, P6) · FALSE-POSITIVE 1 (C10/P3).**

---

## 2. What was fixed

All fixes are in `studio.py`; every regression test is in `tests/test_studio.py`.

| ID | Fix | Test |
|---|---|---|
| **A** | Deleted the blanket `* { outline:none; }`. Added explicit teal `:focus` borders for `QPushButton`, `QToolButton`, `QListWidget`, `QComboBox`, `QLineEdit`, `QPlainTextEdit`, `QSpinBox` and the slider handle. Button padding is compensated so the 2 px focus border does not shift the layout. The `outline:none` on the combo *popup* is kept — that one was deliberate. | `test_theme_has_visible_focus_indicators` |
| **B** | Corrected the selector to `QSlider::handle:horizontal:disabled` (plus disabled groove/sub-page). | `test_disabled_slider_handle_actually_reads_disabled` — renders the widget and asserts amber pixels **> 0 enabled / == 0 disabled**. Post-fix measurement: `176 / 0`. |
| **C** | `load_image`, `load_frame_b`, `save_result`, `save_pipe`, `open_pipe` each wrap the I/O in `try/except` and route failures through a new `report_error(title, text)` → status flash + `ERROR_HOOK` modal + an entry in `state["errors"]`. Success paths now flash a confirmation too. | `test_file_io_errors_are_reported_not_raised` (missing image, malformed JSON, schema-invalid JSON, save failures) |
| **D** | `state["dirty"]` set by every mutation (`add_op`, `add_op_by_name`, `remove`, `move`, `on_rows_moved`, `on_knob`, `clear_pipe`, `load_sample`, sample dialog, `open_pipe`); cleared by a successful `save_pipe`. `confirm_discard()` gates clear / load-sample / open-pipeline, and `QMainWindow` is now a `StudioWindow` subclass whose `closeEvent` consults a `close_guard`. Both dialogs are module-level hooks (`CONFIRM_HOOK`, `ERROR_HOOK`) so tests stub them. | `test_dirty_flag_and_confirm_before_destructive_replace`, `test_close_event_is_vetoed_while_dirty`, `test_save_pipeline_clears_the_dirty_flag` |
| **E** | New `update_actions()` drives Remove/Up/Down (need a selection; Up/Down additionally respect the ends), Save-result/3D (need a raster result), Export/Save-pipeline/Clear/Step/Run-all (need stages) — for **both** the menu actions and the mirrored buttons. Called from `sync_stage_ui()` and `show_result()`, i.e. after every selection change and mutation. Exposed as `win._update_actions` / `win._buttons`. | `test_actions_track_selection_and_result`, `test_scalar_result_disables_save_and_3d` |
| **F** | Dropped the duplicate `itemDoubleClicked` connection (`itemActivated` already covers Enter *and* double-click) and added a `pal["ran"]` latch so `run_sel` cannot re-enter. Exposed as `win._palette["state"]`. | `test_command_palette_runs_the_command_once` — emits the real `doubleClicked`+`activated` pair *and* an extra explicit run, asserts **exactly +1 stage**. |
| **G** | `act_remove`, `act_up`, `act_down`, `act_step`, `act_reset` get `Qt.WidgetWithChildrenShortcut` and are added to `stage_list`. Menu entries, toolbar and buttons are untouched — only the bare key press is scoped. | `test_editing_shortcuts_are_scoped_to_the_pipeline_list` — also asserts the other actions keep `WindowShortcut`, that the action is still owned by its `QMenu`, and that triggering still removes the stage. |
| **H** | New Qt-free `validate_pipeline_dict(d)` checks structure (object → `stages` list → 3-element rows → numeric knobs) and resolves every op name through `api.find_op`. `PipelineModel.load_dict` builds the full list first and only then assigns, so a bad file leaves the live pipeline untouched; `open_pipe` reports the `ValueError` and keeps going. | `test_validate_pipeline_dict_rejects_malformed_payloads`, `test_load_dict_keeps_current_pipeline_on_bad_payload` |
| **I** | `setAccessibleName` on 32 primary controls (sliders, lists, combos, search, image view, inspector, histogram, every button); `la.setBuddy(sa)` / `lb.setBuddy(sb)`; a fallback tooltip for any control that lacked one. New Qt-free `truncate(text, limit=160)` applied to failing-stage tooltips, Problems messages **and Problems op names**. | `test_primary_controls_have_accessible_names`, `test_truncate_shortens_long_error_text`, `test_failing_stage_tooltip_is_truncated` |
| **J** | `run_perception` records `state["perception_error"]`, writes the failure into the Inspector, and `refresh_problems` renders it as a Problems row. A later successful run clears it. | `test_perception_error_reaches_problems_and_inspector` |
| **P6** | Kept best-effort (documented in-code why: the region table is a *bonus* on a result that is already correct, and `detect`'s backends can raise anything), but no longer silent — the Inspector gains one short line `(region features unavailable: …)`. `except Exception as e` with a four-line comment. | covered indirectly; behaviour asserted by the existing `test_scalar_result_shows_message_not_crash` path |
| **C4** | Split rendering into `_render()` + `show_result()`, and guarded the **whole** body, not just the pipeline call. A display-stage failure now shows "Display error", clears the stale result, and reports — instead of escaping the Qt slot. | `test_show_result_survives_a_display_failure` |
| **C2** (contained) | `on_knob` now updates the model + labels and renders **once**; the expensive `step_states()` summary refresh is debounced onto a single-shot `QTimer` (`KNOB_DEBOUNCE_MS = 160`, exposed as `win._knob_timer`). | `test_knob_tick_costs_one_pipeline_evaluation` — asserts **exactly 1** `result_upto` call per tick (was 8) |
| **C3** (minimal safe dedup) | `refresh_stage_list` now selects the row **inside** the `blockSignals` region and calls a new non-rendering `sync_stage_ui()` (the knob/detail/action half of the old `on_stage_selected`). Every caller then owns exactly one `show_result()`. No selection-signal loop is possible because the signal is never emitted. A `state["renders"]` counter makes this testable. | `test_mutations_render_exactly_once` |
| **C10** | *No change.* Documented as a false positive above, with the drag matrix kept as a standing regression test. | `test_drag_reorder_keeps_model_in_step_with_the_view` (30 (src,dst) moves) |

### Measured before → after

| Metric | Before | After |
|---|---|---|
| `result_upto()` calls per knob tick (6 stages) | 8 | **1** |
| Renders per pipeline edit | 2 | **1** |
| Amber pixels on a *disabled* slider handle | 200 | **0** |
| Actions enabled on an empty pipeline (remove/up/down/export) | all `True` | all `False` |
| Malformed pipeline JSON | `IndexError` / `TypeError` | `ValueError` with a stage-numbered message |

---

## 3. Deferred — recommended, needs your approval

These are **not implemented**. Each is a structural change that would have made the diff
unreviewable or risks behaviour the tests cannot pin down.

1. **Asynchronous pipeline execution (C1 / P1) — the biggest remaining issue.**
   Every evaluation still runs on the GUI thread, so a large image or a slow operator
   freezes the window. The knob debounce (C2) reduced *how often* this happens by ~8x but
   changes nothing about a single slow op. Proper fix: move `result_upto` / `step_states` /
   `PerceptionModel.view` onto a `QThreadPool` worker with a generation counter (drop stale
   results), a busy indicator, and a cancel path. This touches every call site and needs a
   UX decision about what the view shows while computing — worth doing, but as its own task.

2. **`QAbstractListModel` rewrite with stable stage IDs (C10 / P3).**
   Explicitly **not** recommended right now. The current `QListWidget` + `UserRole` remap
   was proven correct across all 30 single-row moves, and `SingleSelection` rules out the
   multi-row hazard. If multi-select drag is ever enabled, this becomes mandatory *first* —
   a multi-row drop issues several `moveRow` calls, and the mid-drop `refresh_stage_list`
   would invalidate `dropEvent`'s `QPersistentModelIndex` loop. Note that as a guard rail.

3. **Hardcoded sizes (C14 / P7).**
   Left alone deliberately. `setFixedHeight` on the Problems list, histogram and Inspector
   is what keeps the right-hand column from collapsing, and swapping them for size policies
   is a layout redesign with no test that can catch a regression. Revisit alongside any
   DPI/small-screen work.

4. **`imgio.save` fails silently.** Not a Studio bug and out of scope, but found while
   testing: `imgio.save` delegates to `cv2.imwrite`, which **returns `False` instead of
   raising** on an unwritable path. Studio's new `try/except` therefore cannot catch that
   case — the user gets a "saved" flash for a file that was never written. Fix belongs in
   `imgio.save` (check the return value and raise). The regression test forces a real
   exception to exercise Studio's wrapper and notes this in a comment.

---

## 4. Test results (honest disclosure)

```
tests/test_studio.py:   50 passed, 44 warnings in 3.35s          (was 30 passed)
tests/ (full suite):  2706 passed, 391 warnings in 116.10s       (0 failed)
```

**No regressions.** One caveat on arithmetic: the session baseline measured **2636 passed**,
and this review adds **20** studio tests (30 → 50), which predicts 2656 — not 2706. The extra
~50 are **not mine**. Other agents edited `tests/test_acquire.py`, `test_comm.py`,
`test_device.py`, `test_dsp.py`, `test_engine.py`, `test_examples.py` and `test_mesh.py`
concurrently (file mtimes 07:34–08:32 on 2026-08-14, i.e. after the baseline run and before
the final run). Collection confirms `test_studio.py` contributes exactly 50 nodes, collected
once. The suite is green either way; the delta is simply not attributable to this change
alone.

**Files changed:** `studio.py`, `tests/test_studio.py`, and this document. No dependencies
added (PySide6 + numpy + scipy only).
