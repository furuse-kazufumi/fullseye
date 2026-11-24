# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Studio P-08〜P-19 の残りを確認する回帰テスト。

P-08/09/13/17/19 は 1.1.1 で既に直った。ここでは 20 語の利用者向け順位、`for N` の
上限と安全な未適用状態、段キャッシュ、高 DPI の offscreen 観測を固定する。GUI の待機は
固定 sleep ではなく、表示準備という条件で行う。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import numpy as np
import pytest

import engine
import fssystem
import studio
import studio_search
from fullseye.mcp import server as mcp_server


ROOT = Path(__file__).resolve().parents[1]


# 利用者が最初に入れる代表語。`staples` は検索結果の前に表示されるので、画面で見える
# 上位 5 件を作るときは先に重複なしで足す。
SEARCH_TOP_FIVE = (
    ("blur", "gaussian"), ("edge", "sobel_amp"), ("threshold", "threshold"),
    ("circle detection", "cv_hough_circles"), ("noise", "median"),
    ("rotate", "rotate_image"), ("binarize", "otsu"),
    ("connected components", "connect_and_holes"), ("sharpen", "unsharp"),
    ("dimension", "annotate_dimension"),
    ("ぼかし", "gaussian"), ("エッジ", "sobel_amp"), ("しきい値", "otsu"),
    ("円検出", "cv_hough_circles"), ("ノイズ", "median"),
    ("回転", "rotate_image"), ("二値化", "otsu"), ("ラベリング", "connect_and_holes"),
    ("シャープ", "unsharp"), ("寸法", "annotate_dimension"),
)


def _displayed_names(result):
    """画面の定番→適用可→前処理→その他という表示順を重複なしで返す。

    Return the visible Studio search order without duplicates: staples, applicable,
    preprocessing, then other. This is intentionally a test helper; it does not rank.
    """
    names = []
    for rows in (result["staples"], result["applicable"],
                 result["needs_preprocessing"], result["other"]):
        for row in rows:
            if row["name"] not in names:
                names.append(row["name"])
    return names


@pytest.mark.parametrize("query,expected", SEARCH_TOP_FIVE)
def test_twenty_common_japanese_and_english_searches_show_the_expected_op_in_top_five(query, expected):
    """日英 20 語で、利用者が期待する定番 op が画面上位 5 件に残る。

    For twenty common Japanese/English intents, the expected familiar op remains
    in the first five rows the Studio actually displays.
    """
    result = studio_search.search_grouped(query, current_sort="image", k=20)
    shown = _displayed_names(result)[:5]
    assert expected in shown, (query, expected, shown)


def test_search_top_five_probe_is_not_empty_or_one_language_only():
    """順位の門が空・片言語だけにならないことを、表の構成で先に止める。

    Stop this ranking gate becoming vacuous or silently dropping either language.
    """
    assert len(SEARCH_TOP_FIVE) == 20
    assert sum(query.isascii() for query, _expected in SEARCH_TOP_FIVE) == 10
    assert sum(not query.isascii() for query, _expected in SEARCH_TOP_FIVE) == 10


def test_program_for_limit_refuses_before_list_multiplication_and_keeps_the_actionable_facts():
    """513 回の `for` は 512 段上限で止まり、値・理由・次の手を英語で返す。

    A 513-repeat ``for`` is refused at the 512-stage bound with the actual value,
    the memory/responsiveness reason and usable next actions.
    """
    count = studio.MAX_PROGRAM_STAGES + 1
    text = "for %d\ngaussian (0.5, 0.5)\nendfor" % count
    stages, errors, lines = studio.parse_hdev_program_lines(text, {"gaussian"})
    assert stages == [] and lines == []
    assert len(errors) == 1
    message = errors[0]
    assert str(count) in message and str(studio.MAX_PROGRAM_STAGES) in message
    assert "cached result" in message and "smaller N" in message and "batch/CLI" in message


def test_program_for_limit_is_localised_in_japanese_with_value_reason_and_next_action():
    """日本語 UI の拒否文にも値・理由・次の手が揃う。

    The Japanese UI refusal contains the actual values, reason and next action too.
    """
    previous = studio._UI_LANG["code"]
    studio._UI_LANG["code"] = "ja"
    try:
        message = studio._program_stage_limit_message(7, 513, 513)
    finally:
        studio._UI_LANG["code"] = previous
    assert "行 7" in message and "513" in message and "512" in message
    assert "メモリ" in message and "N を小さく" in message and "CLI" in message


def test_loaded_pipeline_limit_refuses_before_stage_normalisation_and_keeps_the_current_pipeline(tmp_path, monkeypatch):
    """513 段の JSON は Studio/engine とも段リストを組み立てる前に日英で拒否する。

    A 513-stage saved pipeline is rejected before either reader normalises a
    stage, with the observed count, cap, reason and practical next action.
    """
    count = studio.MAX_PROGRAM_STAGES + 1
    path = tmp_path / "too-many-stages.json"
    path.write_text(json.dumps({"fullseye_pipeline": 1,
                                "stages": [["gaussian", 0.5, 0.5]] * count}), encoding="utf-8")
    payload = json.loads(path.read_text(encoding="utf-8"))
    model = studio.PipelineModel(studio.demo_image(16))
    model.stages = [["gaussian", 0.2, 0.3]]
    before = [list(stage) for stage in model.stages]

    def should_not_normalise(_stage):
        pytest.fail("the oversized file must be rejected before stage normalisation")

    monkeypatch.setattr(studio, "_normalise_stage", should_not_normalise)
    with pytest.raises(ValueError) as studio_error:
        model.load_dict(payload, recompute_pins=False)
    assert [list(stage) for stage in model.stages] == before

    with pytest.raises(ValueError) as engine_error:
        engine.FullseyeEngine.load(str(path))
    for message in (str(studio_error.value), str(engine_error.value)):
        assert str(count) in message and str(studio.MAX_PROGRAM_STAGES) in message
        assert "memory" in message and "split the pipeline" in message
        assert "パイプライン" in message and "処理列を分ける" in message


def test_program_plain_lines_are_limited_incrementally_with_an_actionable_message():
    """513 行の素の Program は 513 行目を積む前に止め、英語で直し方を示す。"""
    count = studio.MAX_PROGRAM_STAGES + 1
    text = "\n".join(["gaussian (0.5, 0.5)"] * count)
    stages, errors, lines = studio.parse_hdev_program_lines(text, {"gaussian"})
    assert len(stages) == len(lines) == studio.MAX_PROGRAM_STAGES
    assert len(errors) == 1
    message = errors[0]
    assert str(count) in message and str(studio.MAX_PROGRAM_STAGES) in message
    assert "cached result" in message and "Remove stages" in message and "batch/CLI" in message


def test_program_nested_loop_checks_the_product_before_unrolling():
    """入れ子の 257×2 段は、展開配列を作る前に 514 段として拒否する。"""
    text = "for 2\n  for 257\n    gaussian (0.5, 0.5)\n  endfor\nendfor"
    stages, errors, lines = studio.parse_hdev_program_lines(text, {"gaussian"})
    assert stages == [] and lines == [] and len(errors) == 1
    message = errors[0]
    assert "514" in message and str(studio.MAX_PROGRAM_STAGES) in message
    assert "smaller N" in message and "batch/CLI" in message


def test_stage_limit_is_one_constant_for_studio_engine_and_mcp_schemas():
    """Studio/engine/MCP の上限は正本 fssystem の 512 から分岐しない。"""
    assert fssystem.MAX_PROGRAM_STAGES == studio.MAX_PROGRAM_STAGES == engine.MAX_PROGRAM_STAGES == 512
    for tool in ("fullseye_validate_pipeline", "fullseye_pipeline"):
        stages = mcp_server.TOOLS[tool]["inputSchema"]["properties"]["stages"]
        assert stages["maxItems"] == fssystem.MAX_PROGRAM_STAGES


def test_accepted_for_reuses_the_stage_cache_incrementally():
    """上限内の Program は各段を一度だけ計算し、末段の変更後は先行段を使い回す。

    An accepted Program computes each stage once and reuses preceding cached stages
    after only the last knob changes.
    """
    stages, errors, _lines = studio.parse_hdev_program_lines(
        "for 3\ngaussian (0.5, 0.5)\nendfor", {"gaussian"})
    assert not errors and len(stages) == 3
    model = studio.PipelineModel(np.linspace(0.0, 1.0, 64).reshape(8, 8))
    model.stages = stages
    first = model.output()
    assert model.cache_len() == 3
    model.set_knobs(2, a=0.4)
    second = model.output()
    assert model.last_cache_hits == (True, True, False)
    assert first.shape == second.shape == (8, 8)


def test_program_for_limit_leaves_the_current_pipeline_unchanged_in_the_offscreen_gui(tmp_path, monkeypatch):
    """Apply の拒否は処理列を壊さず、日本語の親切な文を Program 欄へ出す。

    A rejected Apply leaves the current pipeline intact and puts the Japanese
    actionable message in the Program status field.
    """
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", str(tmp_path / "studio.ini"))
    from PySide6 import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(32)))
    previous = studio._UI_LANG["code"]
    studio._UI_LANG["code"] = "ja"
    try:
        program = win._program
        program["edit"].setPlainText(
            "for %d\ngaussian (0.5, 0.5)\nendfor" % (studio.MAX_PROGRAM_STAGES + 1))
        program["apply"]()
        status = program["status"]().text()
        assert model.stages == []
        assert "513" in status and "512" in status and "メモリ" in status and "N を小さく" in status
    finally:
        studio._UI_LANG["code"] = previous
        win.close_guard = lambda: True
        win.quiesce()
        win.close()
        app.processEvents()


def test_program_apply_computes_the_new_pipeline_in_the_existing_worker(tmp_path, monkeypatch):
    """Program Apply は新しい段を GUI スレッドで同期実行せず、既存 worker に渡す。"""
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("FULLSEYE_STUDIO_SETTINGS", str(tmp_path / "studio.ini"))
    from PySide6 import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    win, model = studio.build_window(studio.PipelineModel(studio.demo_image(32)))
    entered, release = threading.Event(), threading.Event()
    thread_ids = []
    gui_thread = threading.get_ident()

    def slow(value, _stages, **_kwargs):
        thread_ids.append(threading.get_ident())
        entered.set()
        assert release.wait(5)
        return value

    monkeypatch.setattr(studio.api, "run_pipeline", slow)
    try:
        program = win._program
        program["edit"].setPlainText("gaussian (0.5, 0.5)")
        program["apply"]()
        deadline = time.monotonic() + 5.0
        while not entered.is_set() and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
        assert entered.is_set()
        assert thread_ids == [thread_ids[0]] and thread_ids[0] != gui_thread
    finally:
        release.set()
        deadline = time.monotonic() + 5.0
        while win._run_controller.running and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
        win.quiesce()
        win.close_guard = lambda: True
        win.close()
        app.processEvents()


_DPI_PROBE = r'''
import json
import time
from PySide6 import QtCore, QtWidgets
import studio

app = QtWidgets.QApplication([])
win, _model = studio.build_window()
win.resize(1280, 860)
win.show()
deadline = time.monotonic() + 8.0
while not (win.isVisible() and win._search_ui["list"].viewport().width() > 0):
    app.processEvents(QtCore.QEventLoop.AllEvents, 50)
    if time.monotonic() >= deadline:
        raise RuntimeError("Studio did not become visible before the condition timeout")
pixmap = win.grab()
search = win._search_ui["edit"]
bottom_right = search.mapTo(win, search.rect().bottomRight())
print(json.dumps({
    "dpr": pixmap.devicePixelRatio(),
    "image": [pixmap.width(), pixmap.height()],
    "window": [win.width(), win.height()],
    "search_viewport": win._search_ui["list"].viewport().width(),
    "search_bottom_right": [bottom_right.x(), bottom_right.y()],
    "icon_sizes": [[s.width(), s.height()] for s in win.windowIcon().availableSizes()],
}))
win.close_guard = lambda: True
win.quiesce()
win.close()
'''


@pytest.mark.parametrize("scale", ("1.5", "2"))
def test_offscreen_high_dpi_keeps_the_search_visible_and_uses_a_high_resolution_icon(tmp_path, scale):
    """150%/200% offscreen で撮った画面が論理倍率・検索欄・256 px icon を保つ。

    Capture Studio in fresh 150%/200% offscreen processes and check the reported
    scale, visible search controls and high-resolution application icon. Waiting is
    conditional in the child process, never a fixed sleep.
    """
    pytest.importorskip("PySide6")
    env = os.environ.copy()
    env.update({
        "QT_QPA_PLATFORM": "offscreen",
        "QT_SCALE_FACTOR": scale,
        "FULLSEYE_STUDIO_SETTINGS": str(tmp_path / ("dpi-" + scale + ".ini")),
        "PYTHONPATH": str(ROOT) + os.pathsep + env.get("PYTHONPATH", ""),
    })
    completed = subprocess.run(
        [sys.executable, "-c", _DPI_PROBE], cwd=ROOT, env=env,
        text=True, capture_output=True, timeout=30, check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    observed = json.loads(completed.stdout)
    dpr = float(observed["dpr"])
    width, height = observed["image"]
    logical_width, logical_height = observed["window"]
    assert dpr == pytest.approx(float(scale))
    assert abs(width - logical_width * dpr) <= 2
    assert abs(height - logical_height * dpr) <= 2
    assert observed["search_viewport"] > 0
    x, y = observed["search_bottom_right"]
    assert 0 < x <= logical_width and 0 < y <= logical_height
    assert (256, 256) in {tuple(size) for size in observed["icon_sizes"]}
