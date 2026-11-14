# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""``pip install fullseye`` だけ(cv2 無し)で ``fullseye apply`` / ``pipeline`` が生の traceback で落ちた
(2026-11-13、配布物の検証 M2)。

``imgevolve._imread`` / ``_imwrite`` が cv2 を直に import していたので、``[pil]`` や ``[gui]`` を入れても直らなかった。
cv2 が無ければ Pillow で読み書きし、どちらも無ければ、どの extra を入れればよいかを 1 行で言って非 0 で止める。
cv2 / PIL を import できない状態は ``sys.modules[name] = None`` で作る(import が ImportError になる)。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

import imgevolve

ROOT = Path(__file__).resolve().parents[1]


def _pgm(path: Path, a8: np.ndarray) -> Path:
    """復号器を使わずに 8 bit の PGM を書く(読む側だけを試すため)。"""
    h, w = a8.shape
    path.write_bytes(b"P5\n%d %d\n255\n" % (w, h) + np.ascontiguousarray(a8, np.uint8).tobytes())
    return path


def _gray(h=12, w=16) -> np.ndarray:
    return (np.arange(h * w).reshape(h, w) * 7 % 256).astype(np.uint8)


def test_without_cv2_images_are_read_and_written_through_pillow(tmp_path, monkeypatch):
    pytest.importorskip("PIL.Image")
    from PIL import Image
    monkeypatch.setitem(sys.modules, "cv2", None)
    assert imgevolve._image_codec() == "pil"
    a8 = _gray()
    src = _pgm(tmp_path / "in.pgm", a8)
    g = imgevolve._imread(str(src), "image")
    assert g.shape == a8.shape and g.dtype == np.float64
    assert np.array_equal(g, a8 / 255.0)
    c = imgevolve._imread(str(src), "color")
    assert c.shape == a8.shape + (3,) and np.array_equal(c[:, :, 1], a8 / 255.0)
    r = imgevolve._imread(str(src), "region")
    assert np.array_equal(r, (a8 / 255.0 > 0.5).astype(np.float64))
    # 16 bit の灰は標本を保つ(cv2 の IMREAD_ANYDEPTH と同じ約束)
    a16 = (np.arange(12 * 16).reshape(12, 16) * 341).astype(np.uint16)
    Image.fromarray(a16).save(tmp_path / "in16.png")
    g16 = imgevolve._imread(str(tmp_path / "in16.png"), "image")
    assert np.array_equal(g16, a16 / 65535.0)
    # 書く: 灰と RGB(RGB の並びのまま。cv2 の BGR に入れ替えない)
    imgevolve._imwrite(str(tmp_path / "g.png"), g)
    assert np.array_equal(np.asarray(Image.open(tmp_path / "g.png")), a8)
    rgb = np.stack([g, np.zeros_like(g), np.ones_like(g)], axis=-1)
    imgevolve._imwrite(str(tmp_path / "c.png"), rgb)
    back = np.asarray(Image.open(tmp_path / "c.png"))
    assert back.shape == a8.shape + (3,) and np.array_equal(back[:, :, 0], a8) and (back[:, :, 2] == 255).all()


def test_without_cv2_an_unreadable_file_is_a_one_line_exit(tmp_path, monkeypatch):
    pytest.importorskip("PIL.Image")
    monkeypatch.setitem(sys.modules, "cv2", None)
    bad = tmp_path / "not_an_image.png"
    bad.write_bytes(b"this is not a png")
    with pytest.raises(SystemExit) as ei:
        imgevolve._imread(str(bad), "image")
    assert "cannot read" in str(ei.value.code) and "not_an_image.png" in str(ei.value.code)


@pytest.mark.parametrize("argv", [
    ["fullseye", "apply", "gauss_filter", "IN", "OUT", "--a", "0.6"],
    ["fullseye", "pipeline", "IN", "OUT", "--ops", "gauss_filter"],
    ["fullseye", "run", "gauss_filter", "IN", "--out", "OUT"],
])
def test_without_any_decoder_the_cli_names_the_extra_in_one_line(tmp_path, monkeypatch, argv):
    monkeypatch.setitem(sys.modules, "cv2", None)
    monkeypatch.setitem(sys.modules, "PIL", None)
    src = _pgm(tmp_path / "in.pgm", _gray())
    out = tmp_path / "out.pgm"
    monkeypatch.setattr(sys, "argv", [str(src) if a == "IN" else str(out) if a == "OUT" else a for a in argv])
    with pytest.raises(SystemExit) as ei:
        imgevolve.main()
    msg = ei.value.code
    assert isinstance(msg, str), msg                                # 文字列の SystemExit = rc 1 + その 1 行
    assert 'pip install "fullseye[opencv]"' in msg and 'pip install "fullseye[pil]"' in msg, msg
    assert msg.startswith("fullseye:") and "\n" not in msg, msg
    assert not out.exists()


def test_without_any_decoder_apply_exits_non_zero_without_a_traceback(tmp_path):
    """プロセスの外から: rc が非 0、標準エラーは 1 行の案内、traceback は無い。"""
    src = _pgm(tmp_path / "in.pgm", _gray())
    code = ("import sys; sys.modules['cv2'] = None; sys.modules['PIL'] = None; "
            "sys.argv = ['fullseye', 'apply', 'gauss_filter', sys.argv[1], sys.argv[2], '--a', '0.6']; "
            "import imgevolve; sys.exit(imgevolve.main())")
    env = dict(os.environ, PYTHONUTF8="1", PYTHONPATH=str(ROOT))
    p = subprocess.run([sys.executable, "-c", code, str(src), str(tmp_path / "out.pgm")], cwd=str(ROOT),
                       stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=600, env=env)
    assert p.returncode == 1, (p.returncode, p.stderr[-800:])
    assert "Traceback" not in p.stderr and "ModuleNotFoundError" not in p.stderr, p.stderr[-800:]
    lines = [ln for ln in p.stderr.splitlines() if ln.strip()]
    assert lines and 'pip install "fullseye[opencv]"' in lines[-1], p.stderr[-800:]
