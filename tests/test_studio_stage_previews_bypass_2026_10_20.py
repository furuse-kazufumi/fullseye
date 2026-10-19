"""Studio slice 2 (2026-10-20): 途中結果が見える。

A: 段の一覧に、キャッシュから作った小さなサムネイル(未計算 / 再計算が必要 の印つき)。
B: 選んだ段の入力と出力を並べ、種類ごとの 1 行の差分(領域数 128 → 37 など)を出すパネル。
C: 段を消さずに一時的に素通しにする bypass(保存・書き出し・キャッシュ・undo)。
"""
import json
import os
import subprocess
import sys

import numpy as np
import pytest

import api
import studio

_OPS4 = ["gaussian", "sobel_amp", "invert", "otsu"]


def _counting(monkeypatch, names):
    """``ops.RT`` の各 op を呼び出し回数つきの包みに差し替える(本物の計算はそのまま)。"""
    counts = {n: 0 for n in names}
    for n in names:
        real = api._ops.RT[n]

        def wrap(v, a, b, _real=real, _n=n):
            counts[_n] += 1
            return _real(v, a, b)
        monkeypatch.setitem(api._ops.RT, n, wrap)
    return counts


def _app():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _model4():
    m = studio.PipelineModel(studio.demo_image(48))
    for n in _OPS4:
        m.add_stage(n, 0.4, 0.5)
    return m


def _blobs():
    """6 x 6 の小さな四角(大きさ 2〜6 画素)。erosion_circle(0.5) で 36 個 → 14 個に減る。"""
    img = np.zeros((120, 120))
    k = 0
    for r in range(6):
        for c in range(6):
            s = 2 + (k % 5)
            k += 1
            img[r * 20 + 4:r * 20 + 4 + s, c * 20 + 4:c * 20 + 4 + s] = 1.0
    return img


@pytest.fixture(autouse=True)
def _no_modal_confirm(monkeypatch):
    monkeypatch.setattr(studio, "CONFIRM_HOOK", lambda parent, title, text: True)


def _display_combo(win):
    from PySide6 import QtWidgets
    for cb in win.findChildren(QtWidgets.QComboBox):
        items = [cb.itemText(i) for i in range(cb.count())]
        if "gray" in items and "region overlay" in items:
            return cb
    raise AssertionError("display combo not found")


# ------------------------------ A: thumbnails ------------------------------ #
def test_a1_previews_uncomputed_then_ready_and_small():
    m = _model4()
    assert [p["status"] for p in m.stage_previews()] == ["uncomputed"] * 4
    assert m.thumb_bytes() == 0
    m.result_upto(3)
    pv = m.stage_previews()
    assert [p["status"] for p in pv] == ["ready"] * 4
    kinds = [p["kind"] for p in pv]
    assert kinds[0] == "image" and kinds[3] == "region"
    assert len(pv) == 4
    for p in pv:
        t = p["thumb"]
        assert t.dtype == np.uint8 and t.ndim == 3 and t.shape[2] == 3
        assert t.shape[0] <= 36 and t.shape[1] <= 48
    assert pv[0]["thumb"].std() > 0                      # a real picture, not a flat fill


def test_a2_thumbnails_never_compute_and_old_ones_are_not_shown_as_current(monkeypatch):
    m = _model4()
    counts = _counting(monkeypatch, _OPS4)
    m.result_upto(3)
    m.stage_previews()
    before = dict(counts)
    m.set_knobs(1, a=0.7)                                # knob change, nothing run yet
    pv = m.stage_previews()
    assert counts == before                               # building the previews ran no op
    assert [p["status"] for p in pv] == ["ready", "stale", "stale", "stale"]
    assert len(pv) == 4
    assert all(p["thumb"] is None for p in pv[1:])        # no old picture is passed off as current
    assert pv[1]["kind"] == "image"                       # (it still knows what kind it was)
    m.result_upto(3)                                      # the user runs
    assert [p["status"] for p in m.stage_previews()] == ["ready"] * 4
    assert counts["sobel_amp"] == before["sobel_amp"] + 1


def test_a2b_new_stage_is_uncomputed_and_a_new_image_is_stale():
    m = _model4()
    m.result_upto(3)
    m.stage_previews()
    m.add_stage("invert", 0.5, 0.5)
    assert m.stage_preview(4)["status"] == "uncomputed"
    m.set_image(studio.demo_image(48) * 0.5)
    assert [p["status"] for p in m.stage_previews()[:4]] == ["stale"] * 4
    with pytest.raises(IndexError):
        m.stage_preview(9)


def test_a2c_direct_edit_of_an_earlier_stage_is_not_ready():
    m = _model4()
    m.result_upto(3)
    m.stage_previews()
    m.stages[0][1] = 0.9                                  # bypasses set_knobs: the cache is not cleared yet
    pv = m.stage_previews()
    assert [p["status"] for p in pv] == ["stale"] * 4


def test_a3_memory_one_full_array_per_stage_and_a_small_thumbnail_store():
    img = np.random.default_rng(3).random((2048, 2048))
    m = studio.PipelineModel(img)
    for n in ["invert", "gaussian", "invert", "sobel_amp", "otsu"]:
        m.add_stage(n, 0.1, 0.5)
    m.result_upto(4)
    m.stage_previews()
    assert m.cache_len() == 5                             # one cached result per stage, no second copy
    full = [v for (_k, v, _ms) in m._cache if isinstance(v, np.ndarray) and v.size >= 2048 * 2048]
    assert len(full) == 5
    assert len({id(v) for v in full}) == 5                # five distinct arrays: nothing kept twice
    assert 0 < m.thumb_bytes() < 1_000_000
    assert m.thumb_bytes() <= 5 * 48 * 36 * 3
    thumbs = [r[2] for r in m._thumbs.values() if r[2] is not None]
    assert len(thumbs) == 5
    assert all(t.nbytes <= 48 * 36 * 3 for t in thumbs)


def test_a4_kinds_region_contour_table_feature_series_color():
    reg = (np.random.default_rng(1).random((60, 80)) > 0.5).astype(np.float64)
    t, k = studio._result_thumbnail(reg)
    assert k == "region" and t.shape[0] <= 36 and t.shape[1] <= 48
    cs = {"shape": (50, 50), "cs": [np.array([[5, 5], [5, 44], [44, 44], [44, 5], [5, 5]], float)]}
    t, k = studio._result_thumbnail(cs)
    assert k == "contour" and t.shape == (36, 48, 3)
    teal = np.all(t == (23, 184, 166), axis=2)
    assert teal.sum() > 40                                # the polyline is drawn
    assert studio._result_thumbnail({"distance": np.arange(5.0), "t": np.arange(5.0)}) == (None, "table")
    assert studio._result_thumbnail(3.5) == (None, "feature")
    assert studio._result_thumbnail(np.arange(9.0)) == (None, "series")
    rgb = np.random.default_rng(2).random((40, 30, 3))
    t, k = studio._result_thumbnail(rgb)
    assert k == "color" and t.shape[2] == 3
    nan_img = np.full((20, 20), np.nan)
    t, k = studio._result_thumbnail(nan_img)              # a NaN picture is shown (black), not a crash
    assert t is not None and t.max() == 0


def test_a5_stage_list_rows_have_icons_and_placeholders_offscreen(monkeypatch):
    from PySide6 import QtCore
    _app()
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    for n in _OPS4:
        model.add_stage(n, 0.4, 0.5)
    win._refresh_stage_list(select=3)
    sl = win._stage_list
    assert sl.count() == 4
    assert sl.iconSize() == QtCore.QSize(48, 36)
    for i in range(4):
        it = sl.item(i)
        assert not it.icon().isNull()
        assert it.data(QtCore.Qt.UserRole + 2) == "ready"
        assert "ms" in it.text() and ("cache" in it.text() or "calc" in it.text())
        assert _OPS4[i] in it.text()
    counts = _counting(monkeypatch, _OPS4)
    model.set_knobs(1, a=0.8)                             # changed, not yet run
    win._update_stage_icons()
    assert counts == {n: 0 for n in _OPS4}                # the icons read the cache only
    assert [sl.item(i).data(QtCore.Qt.UserRole + 2) for i in range(4)] == ["ready", "stale", "stale", "stale"]
    assert "再計算が必要 / recompute needed" in sl.item(1).toolTip()
    assert "recompute needed" not in sl.item(0).toolTip()
    model.add_stage("invert", 0.5, 0.5)
    sl.addItem("x")                                       # a row for the new stage, built by hand
    win._update_stage_icons()
    assert sl.item(4).data(QtCore.Qt.UserRole + 2) == "uncomputed"
    assert "未計算 / not computed" in sl.item(4).toolTip()
    assert counts == {n: 0 for n in _OPS4}
    win.close()


# ------------------------------ B: before / after ----------------------------- #
def test_b1_delta_summary_by_kind():
    studio._UI_LANG["code"] = "en"
    reg_a = np.zeros((40, 40))
    reg_b = np.zeros((40, 40))
    for k in range(5):
        reg_a[2 + 7 * k, 2:6] = 1.0
    reg_b[2, 2:6] = 1.0
    reg_b[9, 2:6] = 1.0
    s = studio._stage_delta_summary(reg_a, reg_b)
    assert "5" in s and "2" in s and "→" in s
    assert studio._stage_delta_summary(np.zeros((8, 8)), reg_b).endswith("2")      # image -> region: "- -> 2"
    img_a, img_b = np.full((8, 8), 0.25), np.linspace(0, 1, 64).reshape(8, 8)
    s = studio._stage_delta_summary(img_a, img_b)
    for word in ("mean", "σ", "min", "max"):
        assert word in s
    assert "0.25" in s and "0.5" in s
    s = studio._stage_delta_summary(img_a, {"x": np.arange(7.0), "y": np.arange(7.0), "z": 1.0})
    assert "7" in s and "3" in s                                                    # rows / cols
    cs = {"shape": (9, 9), "cs": [np.zeros((3, 2)), np.ones((4, 2))]}
    assert "2" in studio._stage_delta_summary(img_a, cs)
    assert "4" in studio._stage_delta_summary(2.0, 4.0)


def test_b2_select_a_stage_shows_input_and_output_side_by_side_offscreen():
    from PySide6 import QtGui
    _app()
    try:
        win, model = studio.build_window(studio.PipelineModel(_blobs()))
        studio._UI_LANG["code"] = "ja"                     # after the build: it may read the saved language
        for n, a in [("gaussian", 0.0), ("otsu", 0.5), ("erosion_circle", 0.5)]:
            model.add_stage(n, a, 0.5)
        win._refresh_stage_list(select=0)
        win._docks["compare"].show()
        win._stage_list.setCurrentRow(2)                    # stage 3: 36 regions -> 14
        cmp_ = win._compare
        mode = _display_combo(win).currentText()

        def shown(val):
            sh = studio.apply_display(val, mode, base=model.image, draw=win._state["draw"])
            return QtGui.QPixmap.fromImage(studio._to_qimage(sh, QtGui)).toImage()
        assert cmp_["left"].pixmap().toImage() == shown(model.result_upto(1))
        assert cmp_["right"].pixmap().toImage() == shown(model.result_upto(2))
        assert cmp_["left"].pixmap().toImage() != cmp_["right"].pixmap().toImage()
        txt = cmp_["summary"].text()
        assert "36" in txt and "14" in txt and "領域数" in txt          # 領域数 36 → 14
        win._stage_list.setCurrentRow(0)                    # stage 1: its input is the raw image
        assert cmp_["left"].pixmap().toImage() == shown(model.image)
        assert "mean" in cmp_["summary"].text()
        win.close()
    finally:
        studio._UI_LANG["code"] = "en"


def test_b3_hidden_panel_costs_nothing_and_table_results_say_no_picture():
    _app()
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    model.add_stage("gaussian", 0.3, 0.5)
    win._refresh_stage_list(select=0)
    assert win._docks["compare"].isHidden()
    assert win._compare["left"].pixmap() is None            # never filled while hidden
    win._docks["compare"].show()
    win._update_stage_compare()
    assert win._compare["left"].pixmap() is not None
    win.close()


# ------------------------------ C: bypass ------------------------------------ #
def test_c1_bypassed_stage_passes_its_input_through_and_equals_removal():
    m = _model4()
    m.set_bypass(2, True)
    assert m.is_bypassed(2)
    assert np.array_equal(m.result_upto(2), m.result_upto(1))      # invert switched off
    ref = studio.PipelineModel(studio.demo_image(48))
    for n in ("gaussian", "sobel_amp", "otsu"):
        ref.add_stage(n, 0.4, 0.5)
    assert np.array_equal(m.output(), ref.output())
    m.set_bypass(2, False)
    assert not np.array_equal(m.result_upto(2), m.result_upto(1))


def test_c1b_bypass_first_and_all_stages():
    m = _model4()
    img = m.image
    m.set_bypass(0, True)
    r = m.result_upto(3)
    ref = studio.PipelineModel(img)
    for n in _OPS4[1:]:
        ref.add_stage(n, 0.4, 0.5)
    assert np.array_equal(r, ref.output())                          # stage 0 off == stage 0 absent
    for i in range(4):
        m.set_bypass(i, True)
    assert np.array_equal(m.output(), img)


def test_c2_bypass_is_part_of_the_cache_key(monkeypatch):
    m = _model4()
    counts = _counting(monkeypatch, _OPS4)
    m.result_upto(3)
    assert counts == {n: 1 for n in _OPS4}
    m.set_bypass(2, True)
    m.result_upto(3)
    assert m.cache_status() == ["cached", "cached", "computed", "computed"]
    assert counts == {"gaussian": 1, "sobel_amp": 1, "invert": 1, "otsu": 2}   # invert not run, otsu re-run
    m.set_bypass(2, False)
    m.result_upto(3)
    assert counts == {"gaussian": 1, "sobel_amp": 1, "invert": 2, "otsu": 3}
    m.result_upto(3)
    assert counts == {"gaussian": 1, "sobel_amp": 1, "invert": 2, "otsu": 3}   # settled: all cached
    m.stages[1].bypass = True                                                    # direct edit is also caught
    m.result_upto(3)
    assert counts["gaussian"] == 1 and counts["otsu"] == 4
    pv = m.stage_previews()
    assert pv[1]["bypass"] is True and all(p["status"] == "ready" for p in pv)


def test_c3_roundtrip_is_backward_compatible_and_written_only_when_on(tmp_path):
    m = _model4()
    plain = json.dumps(m.to_dict(), sort_keys=True)
    stages0 = m.to_dict()["stages"]
    assert len(stages0) == 4
    assert all(len(st) == 3 for st in stages0)
    expected_old = json.dumps({"fullseye_pipeline": 1, "stages": [[n, 0.4, 0.5] for n in _OPS4]}, sort_keys=True)
    assert plain == expected_old                                    # byte-identical to what a file without bypass was
    m.set_bypass(1, True)
    d = m.to_dict()
    assert d["stages"][1] == ["sobel_amp", 0.4, 0.5, True]
    assert [len(s) for s in d["stages"]] == [3, 4, 3, 3]
    m2 = studio.PipelineModel(m.image)
    m2.load_dict(json.loads(json.dumps(d)))
    assert [m2.is_bypassed(i) for i in range(4)] == [False, True, False, False]
    assert np.array_equal(m2.output(), m.output())
    m2.set_bypass(1, False)
    assert json.dumps(m2.to_dict(), sort_keys=True) == plain        # switching it back restores the old bytes
    old = studio.PipelineModel(m.image)
    old.load_dict({"fullseye_pipeline": 1, "stages": [["gaussian", 0.4, 0.5]]})
    assert not old.is_bypassed(0)
    for bad in ([["gaussian", 0.4, 0.5, 1]], [["gaussian", 0.4, 0.5, "yes"]], [["gaussian", 0.4, 0.5, True, 1]]):
        with pytest.raises(ValueError):
            studio.validate_pipeline_dict({"stages": bad})
    assert studio.validate_pipeline_dict({"stages": [["gaussian", 0.4, 0.5, False]]}) == [["gaussian", 0.4, 0.5]]


def test_c4_export_python_skips_the_bypassed_stage_and_equals_the_model(tmp_path):
    m = _model4()
    m.set_bypass(2, True)
    src = m.export_python()
    assert "# bypassed: invert" in src
    assert "('invert'" not in src and "'gaussian'" in src
    ns = {}
    exec(compile(src, "<export>", "exec"), ns)
    assert np.array_equal(ns["pipeline"](m.image), m.output())
    for i in range(4):
        m.set_bypass(i, True)
    ns = {}
    exec(compile(m.export_python(), "<export>", "exec"), ns)
    assert np.array_equal(ns["pipeline"](m.image), m.image)         # nothing left: the frame comes back as it is


def test_c5_copies_keep_the_flag_and_duplicate_stage():
    m = _model4()
    m.set_bypass(1, True)
    j = m.duplicate_stage(1)
    assert m.is_bypassed(j) and m.is_bypassed(1)
    cp = studio._copy_stage(m.stages[1])
    assert cp.bypass is True and list(cp) == list(m.stages[1])
    a, b, c = m.stages[0]                                           # still unpackable as [op, a, b]
    assert (a, b, c) == ("gaussian", 0.4, 0.5)
    m.stages = [studio._copy_stage(s) for s in m.stages]
    assert m.is_bypassed(1) and m.is_bypassed(j)


def test_c6_window_toggle_greyed_struck_undo_says_bypass_and_not_remove():
    from PySide6 import QtCore
    _app()
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    for n in _OPS4:
        model.add_stage(n, 0.4, 0.5)
    win._refresh_stage_list(select=2)
    ref_out = model.output().copy()
    assert not win._actions["bypass"].shortcut().isEmpty()
    win._actions["bypass"].trigger()
    assert model.is_bypassed(2) and len(model.stages) == 4          # still there: not a removal
    it = win._stage_list.item(2)
    assert it.font().strikeOut() and "bypass" in it.text()
    assert not win._stage_list.item(1).font().strikeOut()
    assert "bypassed" in it.toolTip()
    assert win._undo_stack[-1].label == "bypass"
    assert not np.array_equal(model.output(), ref_out)
    program = win._code_edit.toPlainText() if hasattr(win, "_code_edit") else None
    if program is not None:
        assert "# bypassed: invert" in program
    win._undo()
    assert not model.is_bypassed(2) and np.array_equal(model.output(), ref_out)
    assert "undo bypass" in win.statusBar().currentMessage()
    win._redo()
    assert model.is_bypassed(2)
    assert "redo bypass" in win.statusBar().currentMessage()
    win._stage_list.setCurrentRow(1)
    win._buttons["remove"].click()                                  # a real removal says 'remove'
    assert win._undo_stack[-1].label == "remove"
    win._undo()
    assert model.is_bypassed(2) and len(model.stages) == 4          # the undo snapshot kept the flag
    assert dict(win._ctx)["pipeline"] is not None
    labels = [lbl for lbl, _cb in win._ctx["pipeline"]()]
    assert any("ypass" in lbl for lbl in labels)
    win.close()


def test_c7_run_program_and_problems_ignore_the_bypassed_stage():
    _app()
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    for n in ("gaussian", "invert", "otsu"):
        model.add_stage(n, 0.4, 0.5)
    model.set_bypass(1, True)
    win._refresh_stage_list(select=2)
    assert win._problems_list.item(0).text() == "no problems"
    win._stage_list.setCurrentRow(0)                        # so that Run all really changes the row
    win._do_run_all()
    assert np.array_equal(win._state["raw"], model.output())
    win.close()


def test_c8_holdout_skips_bypassed_stages(tmp_path):
    img = studio.demo_image(32)
    m = studio.PipelineModel(img)
    for n in ("gaussian", "invert"):
        m.add_stage(n, 0.4, 0.5)
    m.set_bypass(1, True)
    seen = []
    real = api.run_pipeline

    def spy(image, stages, *a, **k):
        seen.append([s[0] for s in stages])
        return real(image, stages, *a, **k)
    import unittest.mock as um
    with um.patch.object(api, "run_pipeline", spy):
        from PIL import Image
        p = tmp_path / "a.png"
        Image.fromarray((img * 255).astype(np.uint8)).save(p)
        studio.run_holdout(m.stages, [str(p)])
    assert seen and all(names == ["gaussian"] for names in seen)


# ------------------------------ D: slice 1 stays intact ----------------------- #
def test_d1_slice1_state_and_cache_marks_still_there_offscreen():
    _app()
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(48)))
    for n in _OPS4:
        model.add_stage(n, 0.4, 0.5)
    win._refresh_stage_list(select=0)
    st = model.step_states()
    assert len(st) == 4
    assert all(s["state"]["ran"] is True and "valid" in s["state"] and "reasons" in s["state"] for s in st)
    assert [s["bypass"] for s in st] == [False] * 4
    assert model.cache_status() == ["cached"] * 4
    assert win._problems_list.item(0).text() == "no problems"
    win.close()
