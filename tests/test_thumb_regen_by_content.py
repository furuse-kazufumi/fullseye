"""サムネ(<図>_720.jpg)を書き直すかは中身で決め、更新時刻では決めない(2026-10-31)。

CI の checkout で図の PNG の mtime がサムネより新しくなると、Linux の Pillow で作り直されて
バイト列が変わり `regen_all --check` が落ちた。ここでは時刻を逆転させても書き直さないこと、
図の中身が変わったら書き直すことを確かめる。
"""
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

PIL = pytest.importorskip("PIL")
from PIL import Image  # noqa: E402

import gen_wingpoc_gallery as G  # noqa: E402


def _png(path, seed):
    rng = np.random.default_rng(seed)
    Image.fromarray(rng.integers(0, 255, (60, 90, 3), dtype=np.uint8)).save(path)


@pytest.fixture
def poc(tmp_path, monkeypatch):
    d = tmp_path / "poc_x"
    d.mkdir()
    monkeypatch.setattr(G, "ASSETS", str(tmp_path))
    monkeypatch.setattr(G, "_DIRTY_CACHE", {"set": None})   # git の外として扱う
    _png(str(d / "01_a.png"), 0)
    return d


def test_newer_png_mtime_alone_does_not_rewrite(poc):
    name = G._thumb("poc_x", "01_a.png")
    dst = poc / name
    before = dst.read_bytes()
    t = os.path.getmtime(dst)
    os.utime(poc / "01_a.png", (t + 100, t + 100))          # CI の checkout で起きる逆転
    dst.write_bytes(before)
    os.utime(dst, (t, t))
    G._thumb("poc_x", "01_a.png")
    assert dst.read_bytes() == before


def test_changed_png_rewrites(poc):
    name = G._thumb("poc_x", "01_a.png")
    dst = poc / name
    before = dst.read_bytes()
    _png(str(poc / "01_a.png"), 1)
    t = os.path.getmtime(dst)
    os.utime(poc / "01_a.png", (t - 100, t - 100))          # 時刻は古く見せても中身で気づく
    G._thumb("poc_x", "01_a.png")
    assert dst.read_bytes() != before


def test_legacy_thumb_without_hash_follows_git_dirty_state(poc, monkeypatch):
    src = poc / "01_a.png"
    dst = poc / "01_a_720.jpg"
    Image.open(src).convert("RGB").save(dst, "JPEG", quality=92)   # 記録の無い既存のサムネ
    legacy = dst.read_bytes()
    t = os.path.getmtime(dst)
    os.utime(src, (t + 100, t + 100))
    monkeypatch.setattr(G, "_DIRTY_CACHE", {"set": set()})          # git で clean
    G._thumb("poc_x", "01_a.png")
    assert dst.read_bytes() == legacy
    monkeypatch.setattr(G, "_DIRTY_CACHE",
                        {"set": {os.path.normcase(os.path.normpath(str(src)))}})   # 図が変更済み
    G._thumb("poc_x", "01_a.png")
    assert dst.read_bytes() != legacy
