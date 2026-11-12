# -*- coding: utf-8 -*-
"""P-02(2026-11-12 の使い勝手点検): 書き出した Python が単体で走る。

以前は ``export_python()`` が関数の定義だけ、``pipeline_script()`` の末尾は存在しない
``your_image.png`` を読む行で、書き出したものを ``py file.py`` で走らせても何も起きない
(サンプル画像のままだと FileNotFoundError)だった。
"""
import os
import subprocess
import sys

import numpy as np
import pytest

import imgio
import sample_images
import studio

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run(script, tmp_path, *args):
    path = tmp_path / "exported.py"
    path.write_text(script, encoding="utf-8", newline="\n")
    env = dict(os.environ, PYTHONPATH=ROOT, PYTHONUTF8="1")
    return subprocess.run([sys.executable, str(path), *args], cwd=str(tmp_path), env=env,
                          capture_output=True, text=True, timeout=180)


def _model(img):
    m = studio.PipelineModel(img)
    m.add_stage("gaussian")
    m.add_stage("otsu")
    return m


def test_sample_image_script_runs_alone_and_matches_the_gui(tmp_path):
    img = sample_images.load("coins")
    m = _model(img)
    proc = _run(m.export_standalone(sample="coins"), tmp_path)
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout.strip().splitlines()
    assert len(out) == 1, "保存先を 1 行だけ表示する: %r" % proc.stdout
    assert os.path.isfile(out[0]) or os.path.isfile(str(tmp_path / out[0]))
    got = imgio.load(str(tmp_path / out[0]))
    want = np.asarray(m.output(), float)
    assert got.shape == want.shape
    assert np.max(np.abs(got - want)) <= 1.0 / 255 + 1e-9      # 8 bit PNG に量子化した分だけ


def test_synthetic_demo_script_runs_alone_and_matches_the_gui(tmp_path):
    m = _model(studio.demo_image())
    proc = _run(m.export_standalone(sample="__demo__"), tmp_path, "demo_out.png")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "demo_out.png"
    got = imgio.load(str(tmp_path / "demo_out.png"))
    assert np.max(np.abs(got - np.asarray(m.output(), float))) <= 1.0 / 255 + 1e-9


def test_own_image_script_takes_the_path_as_an_argument_and_leaks_no_local_path(tmp_path):
    src = tmp_path / "my_input.png"
    imgio.save(str(src), sample_images.load("coins"))
    m = _model(sample_images.load("coins"))
    script = m.export_standalone(input_path=str(src))
    assert str(tmp_path) not in script and tmp_path.name not in script.replace("my_input.png", "")
    assert str(src).replace("\\", "/") not in script
    # 引数なし: 使い方を表示して終了コード 2(何も書かない)
    bad = _run(script, tmp_path)
    assert bad.returncode == 2 and "usage" in bad.stderr and bad.stdout == ""
    ok = _run(script, tmp_path, str(src), "res.png")
    assert ok.returncode == 0, ok.stderr
    assert ok.stdout.strip() == "res.png" and (tmp_path / "res.png").is_file()


def test_window_state_picks_the_right_input_form(tmp_path):
    from PySide6 import QtWidgets
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    win, model = studio.build_window()
    assert "your_image.png" not in win._pipeline_script()
    assert "sample_images" not in win._pipeline_script()          # 起動直後 = 合成デモ(中に生成コード)
    win._load_sample_image("coins")
    assert "sample_images.load('coins')" in win._pipeline_script()
    win._load_sample_image("blobs")
    assert "sample_images.load('blobs')" in win._pipeline_script()
    win.close_guard = lambda: True
    win.quiesce(); win.close()
