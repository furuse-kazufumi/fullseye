# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""看板(_hero_montage.jpg)は**画素で**同じかを見る —— Pillow の版でバイトが変わっても書き直さない。

2026-10-18: 手元(Pillow 12)で作った看板が、Linux の CI(Pillow 13)の ``regen_all --check`` で
「回し忘れ」と判定された。LANCZOS の丸めと JPEG のバイトが版で違うだけで、絵は同じ
(平均 0.017 段・最大 17 段)。逆に、タイルが 1 枚変われば差は桁で大きいことも確かめる。
"""
from __future__ import annotations

import io
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

Image = pytest.importorskip("PIL.Image")
G = pytest.importorskip("gen_wingpoc_gallery")


def _jpeg(arr: np.ndarray, q: int) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, "JPEG", quality=q, optimize=True)
    return buf.getvalue()


def _scene(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:267, 0:400]
    base = (127 + 100 * np.sin(xx / 17.0) * np.cos(yy / 23.0)).astype(np.uint8)
    noise = rng.integers(-3, 4, size=base.shape)
    g = np.clip(base.astype(int) + noise, 0, 255).astype(np.uint8)
    return np.stack([g, g[::-1], g[:, ::-1]], axis=-1)


def test_same_picture_ignores_encoder_level_differences(tmp_path):
    a = _scene(1)
    p = tmp_path / "m.jpg"
    p.write_bytes(_jpeg(a, 92))
    # 版の違いの代役: 縮小の丸めが 1 段ずれた画素が少し混じった同じ絵(実測の差は平均 0.017 段)
    jitter = np.zeros(a.shape, dtype=int)
    jitter[::7, ::5] = 1
    other = _jpeg(np.clip(a.astype(int) + jitter, 0, 255).astype(np.uint8), 92)
    assert other != p.read_bytes()
    assert G._same_picture(str(p), other)


def test_same_picture_detects_a_changed_tile(tmp_path):
    a = _scene(1)
    b = a.copy()
    b[:, :200] = _scene(2)[:, :200][:, ::-1]      # タイル 1 枚ぶんを別の絵に
    p = tmp_path / "m.jpg"
    p.write_bytes(_jpeg(a, 92))
    assert not G._same_picture(str(p), _jpeg(b, 92))


def test_same_picture_rejects_a_size_change(tmp_path):
    a = _scene(1)
    p = tmp_path / "m.jpg"
    p.write_bytes(_jpeg(a, 92))
    assert not G._same_picture(str(p), _jpeg(a[:, :399], 92))
