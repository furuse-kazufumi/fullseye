# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gen_wingstudio_gallery — Qiita 記事の「Studio 画面 / 3D 表示ウィング」展示を作る。

狙いは 2 つある。**見せる**ことと、**見て気づく**こと。表に並べた数字では
「軸が入れ替わっている」「端が 1 画素欠けている」は絶対に見つからないが、
回転させれば 1 秒で分かる。だからこのスクリプトは記事の挿絵生成器であると同時に
デバッグ道具でもある(実際に本ファイルの作成中に見つかった不具合は
``docs/articles/exhibits/wingstudio.md`` 末尾に列挙してある)。

規律(honest disclosure):

* **Studio 画面はすべて本物**。``studio.build_window()`` が組み立てた実 UI を
  ``QT_QPA_PLATFORM=offscreen`` で ``widget.grab()`` したもの。モックアップは無い。
  一人称ウォークスルーもターンテーブルも、記事用の別実装ではなく **アプリが
  毎フレーム呼んでいるのと同じ** ``studio.render_points_frame`` /
  ``studio.render_points_frame_fp`` を通っている(F キー・WASD は本物の
  ``QKeyEvent`` を送っている)。
* **3D 展示は fullseye の op と numpy 合成のみ**。matplotlib は使わない
  (カラーマップは ``imgio.apply_cmap``)。文字だけは fullseye にテキスト描画 op が
  無いため Pillow の ``ImageDraw.text`` を使う。
* **数字は実測のみ**。キャプションに出る値は実行時に計算した値を整形しただけで、
  手で書いた数字は 1 つも無い。
* **決定的**。乱数は seed 固定、Studio のダイアログは掴む前に明示 resize する。
  書き出したファイルは必ず**読み戻して**フレーム数・寸法・SHA-256 を実測する。

出力:

* ``docs/articles/assets/wingstudio_<name>.png``      + ``_thumb.jpg``
* ``docs/articles/assets/media/wingstudio_<name>.gif``
* ``docs/articles/assets/thumbs/wingstudio_<name>_thumb.jpg``
* ``docs/articles/exhibits/wingstudio.md``            キャプション原稿
* ``docs/articles/assets/_wingstudio_meta.json``      実測値 + SHA-256

使い方::

    py -3.11 tools/gen_wingstudio_gallery.py                  # 全展示
    py -3.11 tools/gen_wingstudio_gallery.py --only walk,turntable
    py -3.11 tools/gen_wingstudio_gallery.py --exhibit walk   # 1 件をこのプロセスで
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

ASSETS = os.path.join(_ROOT, "docs", "articles", "assets")
MEDIA = os.path.join(ASSETS, "media")
THUMBS = os.path.join(ASSETS, "thumbs")
EXHIBITS = os.path.join(_ROOT, "docs", "articles", "exhibits")
META_PATH = os.path.join(ASSETS, "_wingstudio_meta.json")
CAPTION_PATH = os.path.join(EXHIBITS, "wingstudio.md")
RAW_BASE = ("https://raw.githubusercontent.com/furuse-kazufumi/fullseye/"
            "master/docs/articles/assets/")

PREFIX = "wingstudio_"
SEED = 20260902
GIF_FPS = 12
THUMB_W = 720

# 配色 — 赤緑の対で意味を担わせない(色覚に依らず読める)
C_BG = (0.055, 0.062, 0.075)
C_PANEL = (0.098, 0.107, 0.129)
C_TEXT = (0.87, 0.89, 0.90)
C_DIM = (0.52, 0.55, 0.60)
C_ACCENT = (0.13, 0.85, 0.80)      # teal
C_AMBER = (0.96, 0.65, 0.14)
C_VIOLET = (0.66, 0.55, 0.95)
C_BLUE = (0.35, 0.72, 1.00)


# --------------------------------------------------------------------------- #
# 小道具(描画は numpy 合成 + fullseye op、文字だけ Pillow)                     #
# --------------------------------------------------------------------------- #
_FONT_CACHE: dict = {}


def _font(size: int = 13, bold: bool = False):
    """等幅フォント(数値が桁で揃う)。無ければ既定へ退避。"""
    key = (size, bold)
    if key not in _FONT_CACHE:
        from PIL import ImageFont
        path = r"C:\Windows\Fonts\consolab.ttf" if bold else r"C:\Windows\Fonts\consola.ttf"
        try:
            _FONT_CACHE[key] = ImageFont.truetype(path, size)
        except OSError:
            _FONT_CACHE[key] = ImageFont.load_default()
    return _FONT_CACHE[key]


def _to_u8(rgb) -> np.ndarray:
    a = np.asarray(rgb, np.float64)
    if a.ndim == 2:
        a = np.stack([a] * 3, axis=-1)
    return np.clip(a * 255.0 + 0.5, 0, 255).astype(np.uint8)


def _text(frame_u8: np.ndarray, labels) -> np.ndarray:
    """labels = [(x, y, text, color01, size, bold), ...] を焼き込む。"""
    from PIL import Image, ImageDraw
    im = Image.fromarray(np.ascontiguousarray(frame_u8))
    d = ImageDraw.Draw(im)
    for x, y, txt, col, size, bold in labels:
        c = tuple(int(round(v * 255)) for v in col)
        d.text((int(x), int(y)), txt, fill=c, font=_font(size, bold))
    return np.asarray(im)


def _fill(canvas: np.ndarray, y0, y1, x0, x1, color) -> None:
    canvas[int(y0):int(y1), int(x0):int(x1), :] = np.asarray(color, np.float64)


def _paste(canvas: np.ndarray, img01: np.ndarray, y0: int, x0: int) -> None:
    a = np.asarray(img01, np.float64)
    if a.ndim == 2:
        a = np.stack([a] * 3, axis=-1)
    h, w = a.shape[:2]
    canvas[y0:y0 + h, x0:x0 + w, :] = np.clip(a[..., :3], 0.0, 1.0)


def _upscale(a: np.ndarray, k: int) -> np.ndarray:
    """最近傍の整数倍拡大 — 補間しない(画素の粗さ自体が情報)。"""
    return np.repeat(np.repeat(a, k, axis=0), k, axis=1)


def _fit_box(a: np.ndarray, w: int, h: int) -> np.ndarray:
    """アスペクトを保って (h, w) 箱に収める(最近傍。整数拡大/縮小のみ)。"""
    a = np.asarray(a, np.float64)
    ah, aw = a.shape[:2]
    ys = (np.arange(h) * ah / h).astype(int).clip(0, ah - 1)
    xs = (np.arange(w) * aw / w).astype(int).clip(0, aw - 1)
    return a[np.ix_(ys, xs)] if a.ndim == 2 else a[np.ix_(ys, xs, np.arange(a.shape[2]))]


def _qimage_to_rgb_u8(qimg) -> np.ndarray:
    """QPixmap/QImage -> (H, W, 3) uint8。Qt のパディング(bytesPerLine)を必ず外す。"""
    from PySide6 import QtGui
    img = qimg.toImage() if hasattr(qimg, "toImage") else qimg
    img = img.convertToFormat(QtGui.QImage.Format_RGB888)
    w, h, bpl = img.width(), img.height(), img.bytesPerLine()
    buf = np.frombuffer(img.constBits(), np.uint8, count=bpl * h)
    return buf.reshape(h, bpl)[:, : w * 3].reshape(h, w, 3).copy()


def _sha256(path: str) -> str:
    hh = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            hh.update(chunk)
    return hh.hexdigest()


# --------------------------------------------------------------------------- #
# 書き出しと読み戻し検証                                                        #
# --------------------------------------------------------------------------- #
def save_png(name: str, rgb01_or_u8, facts: dict) -> dict:
    """PNG + 幅 720px サムネを書き、読み戻して寸法と SHA-256 を実測する。"""
    from PIL import Image
    os.makedirs(ASSETS, exist_ok=True)
    arr = np.asarray(rgb01_or_u8)
    if arr.dtype != np.uint8:
        arr = _to_u8(arr)
    path = os.path.join(ASSETS, PREFIX + name + ".png")
    Image.fromarray(arr, "RGB").save(path)

    back = np.asarray(Image.open(path).convert("RGB"))
    if back.shape != arr.shape:
        raise RuntimeError("%s: read back %s, wrote %s" % (path, back.shape, arr.shape))
    if float(back.std()) < 4.0:
        raise RuntimeError("%s: near-uniform image (std=%.2f) — refusing to ship"
                           % (path, back.std()))
    im = Image.fromarray(back, "RGB")
    tw = min(THUMB_W, im.size[0])
    th = max(1, round(im.size[1] * tw / im.size[0]))
    tpath = os.path.join(ASSETS, PREFIX + name + "_thumb.jpg")
    im.resize((tw, th), Image.LANCZOS).save(tpath, "JPEG", quality=88)

    rec = {"kind": "png", "name": name, "path": path, "thumb": tpath,
           "size": [int(back.shape[1]), int(back.shape[0])],
           "bytes": os.path.getsize(path), "thumb_bytes": os.path.getsize(tpath),
           "std": round(float(back.std()), 2),
           "sha256": _sha256(path), "thumb_sha256": _sha256(tpath),
           "facts": facts}
    print("  PNG  %s  %dx%d  %.0f kB  std=%.1f  sha=%s"
          % (os.path.basename(path), rec["size"][0], rec["size"][1],
             rec["bytes"] / 1e3, rec["std"], rec["sha256"][:12]))
    return rec


def save_gif(name: str, frames, facts: dict, fps: int = GIF_FPS,
             thumb_index: int = 0) -> dict:
    """GIF を書き、**読み戻して**フレーム数・寸法を実測する(捏造禁止)。"""
    import imageio.v2 as imageio
    from PIL import Image
    import video
    os.makedirs(MEDIA, exist_ok=True)
    os.makedirs(THUMBS, exist_ok=True)
    seq = [f if np.asarray(f).dtype == np.uint8 else _to_u8(f) for f in frames]
    if not seq:
        raise RuntimeError("%s: no frames" % name)
    shapes = {np.asarray(f).shape for f in seq}
    if len(shapes) != 1:
        raise RuntimeError("%s: ragged frames %s" % (name, shapes))
    # フレームが 1 枚も動いていない GIF は「アニメ」ではない — 落とす
    diffs = [float(np.abs(np.asarray(seq[i], np.int32)
                          - np.asarray(seq[i - 1], np.int32)).mean())
             for i in range(1, len(seq))]
    if diffs and max(diffs) < 0.05:
        raise RuntimeError("%s: frames are effectively identical (max mean|Δ|=%.4f)"
                           % (name, max(diffs)))
    path = os.path.join(MEDIA, PREFIX + name + ".gif")
    video.write_video(path, seq, fps=fps)

    reader = imageio.get_reader(path)
    n, shape = 0, None
    try:
        for fr in reader:
            if shape is None:
                shape = tuple(np.asarray(fr).shape)
            n += 1
    finally:
        reader.close()
    if n != len(seq):
        raise RuntimeError("%s: read back %d frames, wrote %d" % (path, n, len(seq)))

    idx = int(np.clip(thumb_index, 0, len(seq) - 1))
    im = Image.fromarray(np.asarray(seq[idx]), "RGB")
    tw = min(THUMB_W, im.size[0])
    th = max(1, round(im.size[1] * tw / im.size[0]))
    tpath = os.path.join(THUMBS, PREFIX + name + "_thumb.jpg")
    im.resize((tw, th), Image.LANCZOS).save(tpath, "JPEG", quality=88)

    size_mb = os.path.getsize(path) / 1e6
    rec = {"kind": "gif", "name": name, "path": path, "thumb": tpath,
           "frames": n, "size": [int(shape[1]), int(shape[0])], "fps": fps,
           "bytes": os.path.getsize(path), "thumb_bytes": os.path.getsize(tpath),
           "thumb_frame": idx, "mean_abs_delta": round(float(np.mean(diffs)), 3),
           "sha256": _sha256(path), "thumb_sha256": _sha256(tpath),
           "facts": facts}
    flag = "  ** OVER 3 MB **" if size_mb > 3.0 else ""
    print("  GIF  %s  %dx%d  %d frames @ %d fps  %.2f MB  sha=%s%s"
          % (os.path.basename(path), rec["size"][0], rec["size"][1], n, fps,
             size_mb, rec["sha256"][:12], flag))
    return rec


# --------------------------------------------------------------------------- #
# Studio をオフスクリーンで組み立てる                                            #
# --------------------------------------------------------------------------- #
def _studio_app():
    """本物の Studio ウィンドウをオフスクリーンで組む(モーダルは無効化)。"""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    # offscreen プラットフォームはシステムフォントを持たない(全部豆腐になる)ので
    # freetype のフォント DB を実 Windows フォントへ向ける
    os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
    from PySide6 import QtWidgets
    import studio
    studio.CONFIRM_HOOK = lambda *a, **k: True
    studio.ERROR_HOOK = lambda parent, title, text: print("  STUDIO ERROR:", title, text)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    win, model = studio.build_window()
    return app, win, model


def _pump(n: int = 6, ms: int = 20) -> None:
    from PySide6 import QtCore, QtWidgets
    for _ in range(n):
        QtWidgets.QApplication.processEvents(QtCore.QEventLoop.AllEvents, ms)


def _grab(widget) -> np.ndarray:
    _pump(3)
    return _qimage_to_rgb_u8(widget.grab())


def _tap(widget, key, mods=None) -> None:
    """本物の QKeyEvent を press+release で 1 回送る。

    press だけだと Studio 側の連続移動タイマー(30 ms)が走り続けて
    フレーム数が実時間依存になる。release まで送ることで **1 タップ = 1 歩**
    に固定され、GIF が決定的になる。
    """
    from PySide6 import QtCore, QtGui, QtWidgets
    m = QtCore.Qt.NoModifier if mods is None else mods
    QtWidgets.QApplication.sendEvent(
        widget, QtGui.QKeyEvent(QtGui.QKeyEvent.KeyPress, key, m))
    QtWidgets.QApplication.sendEvent(
        widget, QtGui.QKeyEvent(QtGui.QKeyEvent.KeyRelease, key, m))


def _drag(widget, x0, y0, x1, y1, steps=1, button=None, mods=None) -> None:
    """本物のマウスドラッグ(press → move… → release)。"""
    from PySide6 import QtCore, QtGui, QtWidgets
    btn = QtCore.Qt.LeftButton if button is None else button
    m = QtCore.Qt.NoModifier if mods is None else mods

    def _ev(kind, x, y, buttons):
        return QtGui.QMouseEvent(kind, QtCore.QPointF(x, y), QtCore.QPointF(x, y),
                                 btn, buttons, m)
    QtWidgets.QApplication.sendEvent(widget, _ev(QtCore.QEvent.MouseButtonPress, x0, y0, btn))
    for i in range(1, steps + 1):
        x = x0 + (x1 - x0) * i / steps
        y = y0 + (y1 - y0) * i / steps
        QtWidgets.QApplication.sendEvent(widget, _ev(QtCore.QEvent.MouseMove, x, y, btn))
    QtWidgets.QApplication.sendEvent(
        widget, _ev(QtCore.QEvent.MouseButtonRelease, x1, y1, QtCore.Qt.NoButton))
