"""Studio 018: the operator browser shows only the ops that take the previous stage's output.

The rule is the runtime's own chain rule (``api._check_chain_sorts``): an op hidden by the
filter is exactly an op the pipeline would refuse before running, and a shown op is one it
accepts. The filter hides only (nothing is converted) and has an off switch.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import api  # noqa: E402
import engine  # noqa: E402
import studio  # noqa: E402


def _registry_rows():
    return [r for r in api.list_ops(include_algo=True) if api.find_op(r["name"]) is not None]


def _chain_ok(names):
    try:
        api._check_chain_sorts([api.find_op(n) for n in names])
    except ValueError:
        return False
    return True


# --------------------------------------------------------------------------- #
# Qt-free helpers                                                              #
# --------------------------------------------------------------------------- #
def test_upstream_sort_entry_and_chain():
    assert studio._upstream_sort([], 0) == (None, None)
    stages = [["gaussian", 0.5, 0.5], ["threshold", 0.5, 0.5]]
    assert studio._upstream_sort(stages, 0) == (None, None)        # first stage: not narrowed
    assert studio._upstream_sort(stages, 1) == ("image", (0, "gaussian"))
    assert studio._upstream_sort(stages, 2) == ("region", (1, "threshold"))


def test_upstream_sort_skips_bypassed_threads_identity_and_opens_on_unknown():
    byp = studio._normalise_stage(["threshold", 0.5, 0.5, True])
    assert studio._is_bypassed(byp)
    assert studio._upstream_sort([["gaussian", 0.5, 0.5], byp], 2) == ("image", (0, "gaussian"))
    # identity (out 'any') keeps the incoming sort, as engine._thread_sort does
    got = studio._upstream_sort([["threshold", 0.5, 0.5], ["identity", 0.5, 0.5]], 2)
    assert got == ("region", (1, "identity"))
    # an unknown op threads 'any': nothing after it is narrowed (engine.diagnose_stages does the same)
    assert studio._upstream_sort([["no_such_op_xyz", 0.5, 0.5]], 1)[0] == engine._ANY
    rows = _registry_rows()
    assert len(studio._ops_accepting(rows, engine._ANY)) == len(rows)


@pytest.mark.parametrize("bad", [-1, 3, 1.0, True, None])
def test_upstream_sort_rejects_bad_positions(bad):
    with pytest.raises(ValueError):
        studio._upstream_sort([["gaussian", 0.5, 0.5]] * 2, bad)


@pytest.mark.parametrize("upstream", [["gaussian"], ["threshold"], ["threshold", "blob_count"]])
def test_hidden_is_exactly_refused_by_the_runtime(upstream):
    """For EVERY registry op: shown <=> api._check_chain_sorts accepts upstream + [op]."""
    rows = _registry_rows()
    assert len(rows) > 500                      # the gate must not silently shrink
    sort, _prev = studio._upstream_sort([[n, 0.5, 0.5] for n in upstream], len(upstream))
    shown = {r["name"] for r in studio._ops_accepting(rows, sort)}
    assert 0 < len(shown) < len(rows)
    mismatched = [r["name"] for r in rows if (r["name"] in shown) != _chain_ok(upstream + [r["name"]])]
    assert mismatched == []


def test_ops_accepting_hides_only_and_keeps_rows_untouched():
    rows = _registry_rows()
    before = [dict(r) for r in rows]
    shown = studio._ops_accepting(rows, "region")
    assert rows == before                       # nothing converted or rewritten
    assert all(r in rows for r in shown)
    assert studio._ops_accepting(rows, None) == rows


# --------------------------------------------------------------------------- #
# Qt wiring                                                                    #
# --------------------------------------------------------------------------- #
def _window(stages=()):
    QtWidgets = pytest.importorskip("PySide6.QtWidgets")
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    studio.ERROR_HOOK = lambda *_args: None
    studio.CONFIRM_HOOK = lambda *_args: True      # closing a dirty window must not open a modal
    studio._UI_LANG["code"] = "en"
    model = studio.PipelineModel(studio.demo_image(32))
    for name in stages:
        model.add_stage(name, 0.5, 0.5)
    return studio.build_window(model)


def _listed(win):
    from PySide6 import QtCore
    ol = win._op_list
    return [ol.item(i).data(QtCore.Qt.UserRole) for i in range(ol.count())
            if ol.item(i).data(QtCore.Qt.UserRole)]


def test_browser_follows_the_selected_stage_and_switch_turns_it_off():
    win, model = _window(["gaussian", "threshold"])
    fit = win._ops_fit
    assert fit["check"].isChecked()                            # on by default
    stage_list = win._stage_list
    stage_list.setCurrentRow(1)                                # insert after threshold -> region
    assert fit["insert_at"]() == 2
    names = _listed(win)
    rows = {r["name"]: r for r in api.list_ops(include_algo=True)}
    assert names and all(engine._compatible("region", rows[n]["in_sort"]) for n in names)
    assert "remove_small" in names and "gaussian" not in names
    note = fit["note"].text()
    assert "'region'" in note and "stage 2" in note and "threshold" in note
    assert ("Showing %d of %d" % (len(names), len(rows))) in note

    stage_list.setCurrentRow(0)                                # insert after gaussian -> image
    names_img = _listed(win)
    assert "gaussian" in names_img and "remove_small" not in names_img

    fit["check"].setChecked(False)                             # the off switch: every operator again
    assert len(_listed(win)) == len(rows)
    assert "filter is off" in fit["note"].text()
    fit["check"].setChecked(True)
    assert _listed(win) == names_img
    win.close()


def test_first_stage_is_not_narrowed_and_category_counts_agree():
    win, _model = _window()
    fit = win._ops_fit
    rows = api.list_ops(include_algo=True)
    assert len(_listed(win)) == len(rows)
    assert "First stage" in fit["note"].text()
    win.close()

    win, _model = _window(["threshold"])
    fit = win._ops_fit
    cat = fit["category"]
    cat.setCurrentIndex(cat.findText("region"))
    in_cat = [r for r in rows if r["category"] == "region"]
    shown = _listed(win)
    expect = [r["name"] for r in studio._ops_accepting(in_cat, "region")]
    assert sorted(shown) == sorted(expect)
    assert ("Showing %d of %d" % (len(expect), len(in_cat))) in fit["note"].text()
    win.close()


def test_insert_follows_the_filter_and_typed_search_is_not_narrowed():
    from PySide6 import QtCore
    win, model = _window(["gaussian"])
    win._stage_list.setCurrentRow(0)
    ol = win._op_list
    idx = _listed(win).index("threshold")
    item = next(ol.item(i) for i in range(ol.count()) if ol.item(i).data(QtCore.Qt.UserRole) == "threshold")
    assert idx >= 0
    ol.setCurrentItem(item)
    win._op_buttons["insert"].click()
    assert [s[0] for s in model.stages] == ["gaussian", "threshold"]
    # the new stage is selected -> the browser now lists region consumers
    assert win._ops_fit["upstream"]()[0] == "region"
    assert "remove_small" in _listed(win) and "gaussian" not in _listed(win)
    # a typed query keeps its own grouping (by the current value), not the browse filter
    win._search_ui["search_now"]("gaussian")
    found = [r["name"] for g in win._search_ui["rows"]().values() for r in g]
    assert "gaussian" in found
    win.close()


def test_switch_label_and_notes_are_translated():
    keys = ["Only operators that take the previous stage's output",
            "Showing every operator (the type filter is off).",
            "First stage: every operator is listed (the input image is matched at the entry).",
            "The previous stage's output type is open ('any'), so every operator is listed.",
            "Showing %d of %d operators that take '%s' (the output of stage %d, %s). "
            "The others would be refused before running."]
    for k in keys:
        row = studio.STRINGS_I18N.get(k)
        assert row and set(row) >= {"ja", "zh", "tw", "ko", "de", "hi"}, k
        for t in row.values():
            assert t.count("%d") == k.count("%d") and t.count("%s") == k.count("%s")


def test_highlighted_op_survives_the_refill_after_insert():
    """The list refills when the insertion point moves (right after Insert): the op the user
    picked stays highlighted when it is still listed, so Run once / Insert again still work."""
    from PySide6 import QtCore
    win, model = _window(["gaussian"])
    win._stage_list.setCurrentRow(0)
    ol = win._op_list
    item = next(ol.item(i) for i in range(ol.count()) if ol.item(i).data(QtCore.Qt.UserRole) == "median")
    ol.setCurrentItem(item)
    win._op_buttons["insert"].click()
    assert [s[0] for s in model.stages] == ["gaussian", "median"]
    cur = win._op_list.currentItem()
    assert cur is not None and cur.data(QtCore.Qt.UserRole) == "median"
    assert win._op_buttons["run_once"].isEnabled() and win._op_buttons["insert"].isEnabled()
    win.close()
