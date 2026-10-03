# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""結果ビューが「描けない結果」を描くこと(2026-10-03)。

発端: ``(2, h, w)`` の flow2d を "color" と判定し、``_to_qimage`` が None を返して
**前の画像が残ったまま**になっていた。1-D 系列と表は「Nothing to display」だった。
台帳の op の多くは系列か表を返すので、Studio で op の結果を見る入口が無かった。
"""
import os

import numpy as np
import pytest

import studio

_R, _C = np.mgrid[0:24, 0:24].astype(np.float64)
FLOW = np.stack([_C - 11.5, -(_R - 11.5)])           # 画面上で時計回り


def test_a_flow2d_is_its_own_kind_not_a_colour_image():
    d = studio.inspect_result(FLOW)
    assert d["kind"] == "flow2d"
    assert d["speed_max"] == pytest.approx(float(np.hypot(*FLOW).max()), rel=1e-4)
    assert "flow2d" in studio.image_info_summary(d)
    # (h, w, 3) の画像や、2 行の RGB 画像は flow2d にしない
    assert studio.inspect_result(np.zeros((8, 8, 3)))["kind"] == "color"
    assert studio.inspect_result(np.zeros((2, 5, 3)))["kind"] == "color"


def test_a_flow2d_preview_is_a_colour_wheel_with_arrows():
    p = studio.result_preview(FLOW)
    img = p["image"]
    assert img.ndim == 3 and img.shape[2] == 3 and img.shape[0] >= 24 * 2
    assert 0.0 <= img.min() and img.max() <= 1.0
    # 矢印(墨色)が描かれている
    assert np.count_nonzero(img.max(axis=2) < 0.2) > 200
    # 上辺の中央は右向き → 色相図の「右」= 赤が勝つ(矢印を避けて端の列で見る)
    top = img[: img.shape[0] // 8, :, :].reshape(-1, 3)
    top = top[top.max(axis=1) > 0.3]
    assert top.size
    assert top[:, 0].mean() > top[:, 2].mean()


def test_a_still_flow_says_so_instead_of_drawing_nothing():
    p = studio.result_preview(np.zeros((2, 6, 6)))
    assert "zero everywhere" in p["note"] and p["image"].shape[2] == 3


def test_a_series_and_a_table_become_line_plots():
    y = np.sin(np.linspace(0, 6, 80))
    p = studio.result_preview(y)
    assert p["image"].shape == (360, 560, 3) and "80" in p["note"]
    t = np.linspace(0, 1, 40)
    tab = {"t": t, "x": np.cos(6 * t), "v": np.sin(6 * t), "ok": True, "n": 3}
    q = studio.result_preview(tab)
    assert q["image"].shape == (360, 560, 3)
    assert q["note"].startswith("2 1-D columns")       # x と v(t は横軸)
    # 描く物の無い表・スカラーは None(呼び手が文字で説明する)
    assert studio.result_preview({"a": 1.0}) is None
    assert studio.result_preview(3.5) is None
    assert studio.result_preview({"cs": [1, 2]}) is None


def test_empty_and_high_dimensional_arrays_are_named_not_misread():
    e = studio.inspect_result(np.zeros((0, 3)))
    assert e["kind"] == "empty" and e["shape"] == (0, 3)
    v4 = studio.inspect_result(np.arange(24.0).reshape(1, 2, 3, 4))
    assert v4["kind"] == "array" and "1×2×3×4" in studio.image_info_summary(v4)


def test_other_array_shapes_are_shown_as_images():
    rgba = np.zeros((5, 7, 4))
    rgba[..., 0] = 1.0
    rgba[..., 3] = 0.5                                  # 半透明の赤 → 白地に合成でピンク
    p = studio.result_preview(rgba)
    assert p["image"].shape == (5, 7, 3)
    assert np.allclose(p["image"][0, 0], [1.0, 0.5, 0.5])
    assert studio.result_preview(np.ones((5, 7, 1)))["image"].shape == (5, 7)
    z = np.fft.fft2(np.ones((8, 8)))
    assert studio.result_preview(z)["image"].max() == pytest.approx(1.0)
    d = studio.inspect_result(z)
    assert d["max"] == pytest.approx(64.0) and d["values"].startswith("|z|")


def test_the_window_draws_a_flow2d_result_instead_of_keeping_the_old_image():
    """Qt 込み: 前の画像が残らず、flow の絵と説明が出ること。"""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6 import QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    m = studio.PipelineModel(studio.demo_image(48))
    m.add_stage("gaussian")
    win, model = studio.build_window(m)
    for value, kind in ((FLOW, "flow2d"), (np.sin(np.linspace(0, 6, 50)), "series"),
                        ({"t": np.arange(9.0), "y": np.arange(9.0) ** 2}, "table")):
        model.result_upto = lambda idx, v=value: v
        win._stage_list.setCurrentRow(-1)
        win._stage_list.setCurrentRow(0)
        app.processEvents()
        assert win._state["raw"] is value, kind
        assert win._state["result"] is not None and win._state["result"].ndim in (2, 3), kind
        assert "Preview:" in win._inspector.toPlainText(), kind
