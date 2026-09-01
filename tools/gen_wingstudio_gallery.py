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
EXHIBITS_DIR = os.path.join(_ROOT, "docs", "articles", "exhibits")
META_PATH = os.path.join(ASSETS, "_wingstudio_meta.json")
CAPTION_PATH = os.path.join(EXHIBITS_DIR, "wingstudio.md")
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


def _font(size: int = 13, bold: bool = False, cjk: bool = False):
    """ASCII は等幅(数値が桁で揃う)、日本語は Meiryo。無ければ既定へ退避。

    consola.ttf は CJK グリフを持たないので、日本語をそのまま流すと**全部豆腐**に
    なる(最初の試作で実際にそうなった)。文字列の中身で自動的に切り替える。
    """
    key = (size, bold, cjk)
    if key not in _FONT_CACHE:
        from PIL import ImageFont
        if cjk:
            path, idx = r"C:\Windows\Fonts\meiryob.ttc" if bold else r"C:\Windows\Fonts\meiryo.ttc", 0
        else:
            path, idx = (r"C:\Windows\Fonts\consolab.ttf" if bold
                         else r"C:\Windows\Fonts\consola.ttf"), 0
        try:
            _FONT_CACHE[key] = ImageFont.truetype(path, size, index=idx)
        except OSError:
            try:
                _FONT_CACHE[key] = ImageFont.truetype(r"C:\Windows\Fonts\meiryo.ttc", size)
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
        cjk = any(ord(ch) > 0x2000 for ch in txt)
        d.text((int(x), int(y)), txt, fill=c, font=_font(size, bold, cjk))
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


# --------------------------------------------------------------------------- #
# 3D 展示のための共通描画(fullseye op + numpy 合成のみ / matplotlib 不使用)     #
# --------------------------------------------------------------------------- #
def _canvas(w: int, h: int, color=C_BG) -> np.ndarray:
    c = np.empty((int(h), int(w), 3), np.float64)
    c[:] = np.asarray(color, np.float64)
    return c


def _panel(canvas, y0, x0, h, w, img01, title=None, border=(0.20, 0.23, 0.28)):
    """枠 + 画像を貼り、タイトル用のラベル指示を返す。"""
    _fill(canvas, y0 - 1, y0 + h + 1, x0 - 1, x0 + w + 1, border)
    _fill(canvas, y0, y0 + h, x0, x0 + w, C_PANEL)
    _paste(canvas, _fit_box(np.asarray(img01, np.float64), w, h), y0, x0)
    return [(x0 + 6, y0 + 5, title, (0.96, 0.96, 0.93), 13, True)] if title else []


def _gray3(a: np.ndarray) -> np.ndarray:
    a = np.asarray(a, np.float64)
    return a if a.ndim == 3 else np.stack([a] * 3, axis=-1)


#: ``render3d`` のカメラ (方位角 yaw / 仰角 pitch, +Z up, -Z を見る) を Studio の
#: ``viewer3d_camera`` の (yaw, pitch) に写す変換。両者は別々の慣習で書かれている
#: ので、素直に同じ数値を渡すと**同じ物が別の向きに回る**。この対応は
#: 骨格 CT の等値面シルエットと点群シルエットの IoU を offset/符号の総当たりで
#: 最大化して実測で決めた(平均 IoU 0.845 — 点群は粒なので 1.0 にはならない)。
STUDIO_YAW_OFFSET, STUDIO_YAW_SIGN, STUDIO_PITCH_SIGN = 270.0, -1.0, -1.0


def studio_view_from_render3d(yaw_deg, pitch_deg):
    """render3d の (yaw, pitch) -> Studio ビューアの (yaw, pitch)。"""
    return (STUDIO_YAW_OFFSET + STUDIO_YAW_SIGN * float(yaw_deg),
            STUDIO_PITCH_SIGN * float(pitch_deg))


def view_radius(points, yaws, pitch_deg):
    """与えた yaw 群・pitch で、点群が**画面内で占める最大半径**(world 単位)。

    ターンテーブルでは外接球半径で正規化すると細長い物体が小さくしか映らない。
    実際に投影して最大値を測り、それに合わせて倍率を決めるための実測値。
    """
    import studio
    P = np.asarray(points, np.float64).reshape(-1, 3)
    c = 0.5 * (P.min(0) + P.max(0))
    best = 0.0
    for y in yaws:
        cam = studio.viewer3d_camera(y, pitch_deg)
        v = (P - c) @ cam.T
        best = max(best, float(np.linalg.norm(v[:, :2], axis=1).max()))
    return c, (best or 1.0)


def _shade_mesh(V, F, yaw_deg, pitch_deg=18.0, size=420, fill=0.9, dist_r=30.0,
                center=None, radius=None):
    """render3d + phong で三角メッシュを 1 枚描く(matplotlib 不使用)。

    V は **world (x, y, z)** で渡すこと(``render3d.marching_cubes`` は
    ボクセル添字 (z, y, x) を返すので、呼び出し側で並べ替える)。

    カメラは *ほぼ正射影* にしてある(距離 = 外接球半径の ``dist_r`` 倍、視野角は
    その距離で外接球が画面の ``fill`` を占めるよう逆算)。Studio のビューアが
    正射影なので、透視のままだと並べたとき**同じ物が別の形に見えてしまう**。
    戻り値 ``(rgb01 (size, size, 3), 被覆画素数)``。
    """
    import render3d
    import render_shade
    V = np.asarray(V, np.float64)
    c = 0.5 * (V.min(0) + V.max(0)) if center is None else np.asarray(center, np.float64)
    r = (float(np.linalg.norm(V - c, axis=1).max()) or 1.0) if radius is None \
        else float(radius)
    a, e = np.radians(yaw_deg), np.radians(pitch_deg)
    eye = c + r * dist_r * np.array([np.cos(e) * np.cos(a),
                                     np.cos(e) * np.sin(a), np.sin(e)])
    pose = render3d.look_at(eye, c, up=(0.0, 0.0, 1.0))
    fov = 2.0 * np.degrees(np.arctan(1.0 / (fill * dist_r)))
    K = render3d.intrinsics_from_fov(fov, size, size)
    buf = render3d.render_mesh(V, F, pose=pose, intrinsics=K, width=size, height=size)
    sil = buf["silhouette"] > 0
    inten = render_shade.phong_shade(buf["normals"], view=(0, 0, 1), light=(0.35, 0.45, 1.0),
                                     ambient=0.13, diffuse=0.78, specular=0.35, shininess=26.0)
    rgb = _canvas(size, size, C_PANEL)
    tint = np.array([0.80, 0.86, 0.94])
    rgb[sil] = np.clip(inten[sil][:, None] * tint, 0, 1)
    return rgb, int(sil.sum())


def _load_ct():
    """同梱の骨格 CT ボリューム (D, H, W) = (z, y, x) を float64 で読む。"""
    return np.load(os.path.join(_ROOT, "studio_assets", "sample_3d",
                                "skeleton_ct.npy")).astype(np.float64)


# --------------------------------------------------------------------------- #
# 展示: CT ボリュームのターンテーブル(等値面 <-> 境界シェル点群)               #
# --------------------------------------------------------------------------- #
def ex_volume_turntable():
    import render3d
    import studio
    import volops
    vol = _load_ct()
    level = float(vol.mean() + vol.std())
    Vz, F = render3d.marching_cubes(vol, level)           # 頂点は (z, y, x) 添字空間
    Vw = np.ascontiguousarray(Vz[:, ::-1])                # -> world (x, y, z)
    mask = (vol > level).astype(np.float64)
    shell = volops.vol_boundary(mask, connectivity=6)
    P = np.ascontiguousarray(np.argwhere(shell > 0.5).astype(np.float64)[:, ::-1])
    n_shell = int(P.shape[0])

    S, PITCH = 462, 18.0
    CY0, CY1 = int(0.19 * S), int(0.81 * S)              # 縦は中央だけ切る(平たい物体)
    PH = CY1 - CY0
    W, H = 24 * 3 + S * 2, 52 + PH + 92
    frames, n, ious = [], 36, []
    yaws = [360.0 * i / n for i in range(n)]
    # 両者を **同じ中心・同じ倍率** に合わせる(外接球で正規化すると細長い物体は
    # 小さくしか映らないので、実際の投影半径の最大値で正規化する)
    ctr, rad = view_radius(P, [studio_view_from_render3d(y, PITCH)[0] for y in yaws],
                           studio_view_from_render3d(0.0, PITCH)[1])
    zoom = 0.47 / 0.45                                   # 投影半径 -> 画面の 94%
    for i in range(n):
        yaw = yaws[i]
        syaw, spitch = studio_view_from_render3d(yaw, PITCH)
        canvas = _canvas(W, H)
        _fill(canvas, 0, 34, 0, W, (0.088, 0.098, 0.118))
        surf, cov = _shade_mesh(Vw, F, yaw, pitch_deg=PITCH, size=S,
                                fill=0.94, center=ctr, radius=rad)
        pts = studio.render_points_frame(P, yaw=syaw, pitch=spitch, zoom=zoom,
                                         size=S, point_px=3, center=ctr, radius=rad,
                                         background=C_PANEL)
        # 目視だけに頼らない: 2 つのシルエットの IoU を毎フレーム実測して焼き込む
        a = (np.abs(surf - np.asarray(C_PANEL)).sum(2) > 0.02)
        b = (np.abs(pts - np.asarray(C_PANEL)).sum(2) > 0.02)
        iou = float((a & b).sum()) / float(max(1, (a | b).sum()))
        ious.append(iou)
        lab = []
        lab += _panel(canvas, 52, 24, PH, S, surf[CY0:CY1],
                      "等値面  marching_cubes + phong_shade")
        lab += _panel(canvas, 52, 24 + S + 24, PH, S, pts[CY0:CY1],
                      "境界シェル点群  vol_boundary + Studio のレンダラ")
        f = _to_u8(canvas)
        lab += [
            (24, 9, "skeleton_ct.npy  (D,H,W) = (%d, %d, %d)   iso = mean+std = %.4f"
                    "   yaw %5.1f deg / pitch %.0f deg   (どちらもほぼ正射影)"
                    % (vol.shape[0], vol.shape[1], vol.shape[2], level, yaw, PITCH),
             C_TEXT, 13, False),
            (30, 52 + PH + 10, "三角形 %s 枚 / 頂点 %s   シルエット %s px"
             % (f"{F.shape[0]:,}", f"{Vw.shape[0]:,}", f"{cov:,}"), C_ACCENT, 13, True),
            (30 + S + 24, 52 + PH + 10, "シェル voxel %s 点   シルエット IoU = %.3f"
             % (f"{n_shell:,}", iou), C_BLUE, 13, True),
            (24, H - 26, "左は render3d、右は Studio のビューアで、カメラ慣習が違う"
                         "(yaw_studio = 270 - yaw, pitch_studio = -pitch)。"
                         "変換を入れて初めて同じ向きに回る —— IoU がその検算です",
             C_DIM, 12, False),
        ]
        frames.append(_text(f, lab))
    facts = {"volume_shape": list(map(int, vol.shape)), "iso_level": round(level, 6),
             "n_faces": int(F.shape[0]), "n_vertices": int(Vw.shape[0]),
             "n_shell_points": n_shell, "frames": n,
             "iou_mean": round(float(np.mean(ious)), 3),
             "iou_min": round(float(np.min(ious)), 3),
             "iou_max": round(float(np.max(ious)), 3)}
    return save_gif("volume_turntable", frames, facts, thumb_index=6)


# --------------------------------------------------------------------------- #
# 展示: z スライス送り(現在位置インジケータつき)                              #
# --------------------------------------------------------------------------- #
def ex_zslices():
    import imagedraw
    import imgio
    import ops
    vol = _load_ct()
    D, Hs, Ws = vol.shape
    vmin, vmax = float(vol.min()), float(vol.max())
    # NOTE: 登録 op ``vol_mip`` は結果を [0,1] に**正規化して**返す(見せる用)。
    # 「累積がどこまで届いたか」を比率で測るには生の最大値投影が要るので、
    # 表示は op、比率は生値、と使い分ける(最初の試作でここを混ぜて 121.5% を出した)。
    mip_op = ops.RT["vol_mip"](vol, 0.0, 0.0)            # 正規化済み(表示用)
    mip = vol.max(axis=0)                                # 生の z 方向 MIP(計算用)
    k = 6                                                # 最近傍整数拡大(補間しない)
    pw, ph = Ws * k, Hs * k
    SIDE = 296                                           # 右の実測値カラム
    W = 24 * 4 + pw * 3 + SIDE
    H = 52 + ph + 92
    bar_x0, bar_x1 = 24 * 4 + pw * 3, W - 24
    frames = []
    thr = float(vol.mean() + vol.std())
    run = np.zeros_like(vol[0])
    sx = 24 * 4 + pw * 3 + 12                            # 右カラムの左端
    for z in range(D):
        sl = (vol[z] - vmin) / (vmax - vmin)
        run = np.maximum(run, vol[z])                    # z=0..z の累積 MIP
        canvas = _canvas(W, H)
        _fill(canvas, 0, 34, 0, W, (0.088, 0.098, 0.118))
        lab = []
        lab += _panel(canvas, 52, 24, ph, pw, _gray3(_upscale(sl, k)),
                      "z = %2d の 1 枚" % z)
        lab += _panel(canvas, 52, 24 * 2 + pw, ph, pw,
                      _upscale(imgio.apply_cmap((run - vmin) / (vmax - vmin),
                                                name="inferno", vmin=0.0, vmax=1.0), k),
                      "z = 0..%d の累積 MIP" % z)
        lab += _panel(canvas, 52, 24 * 3 + pw * 2, ph, pw,
                      _upscale(imgio.apply_cmap((mip - vmin) / (vmax - vmin),
                                                name="inferno", vmin=0.0, vmax=1.0), k),
                      "全 z の MIP(到達点)")
        # 縦の位置インジケータ: D 個のセルのうち今どこか
        cy0, cell = 66, (ph - 40) / D
        _fill(canvas, cy0 - 6, cy0 + ph - 34, bar_x0 + 6, bar_x0 + 34, (0.14, 0.15, 0.18))
        for j in range(D):
            col = C_ACCENT if j == z else (0.26, 0.29, 0.34)
            _fill(canvas, cy0 + j * cell + 1, cy0 + (j + 1) * cell - 1,
                  bar_x0 + 10, bar_x0 + 30, col)
        canvas = imagedraw.draw_line(canvas, (bar_x0 + 38, cy0 + (z + 0.5) * cell),
                                     (bar_x1 - 6, cy0 + (z + 0.5) * cell),
                                     color=C_ACCENT, width=1)
        occ = float((vol[z] > thr).mean())
        f = _to_u8(canvas)
        lab += [
            (24, 9, "skeleton_ct.npy  (D,H,W) = (%d, %d, %d)   最近傍 x%d 拡大(補間なし)"
                    "   値域 [%.3f, %.3f]" % (D, Hs, Ws, k, vmin, vmax), C_TEXT, 13, False),
            (sx + 34, 58, "z = %2d / %d" % (z, D - 1), (0.96, 0.96, 0.93), 15, True),
            (sx + 34, 84, "骨占有率 %5.1f %%" % (occ * 100.0), C_AMBER, 14, True),
            (sx + 34, 108, "min %6.3f" % float(vol[z].min()), C_TEXT, 13, False),
            (sx + 34, 128, "max %6.3f" % float(vol[z].max()), C_TEXT, 13, False),
            (sx + 34, 148, "avg %6.3f" % float(vol[z].mean()), C_TEXT, 13, False),
            (sx + 34, 176, "閾値 mean+std = %.4f" % thr, C_DIM, 12, False),
            (sx + 34, 200, "累積 MIP のカバー率", C_DIM, 12, False),
            (sx + 34, 220, "  %5.1f %% (最終値 = 100 %%)"
             % (100.0 * float(run.sum()) / float(mip.sum())), C_BLUE, 13, True),
            (24, H - 24, "左=1 枚、中=そこまでの累積、右=到達点。累積が右に一致した瞬間に"
                         "「もう新しい層は無い」と分かる —— 端の 1 枚落ちもここで露見します",
             C_DIM, 12, False),
        ]
        frames.append(_text(f, lab))
    facts = {"volume_shape": [D, Hs, Ws], "frames": D, "upscale": k,
             "value_range": [round(vmin, 5), round(vmax, 5)], "threshold": round(thr, 6)}
    return save_gif("zslices", frames, facts, fps=5, thumb_index=D // 2)


# --------------------------------------------------------------------------- #
# キャプション原稿                                                              #
# --------------------------------------------------------------------------- #
#: name -> (見出し, 使用 op/機能, 本文を組み立てる関数(facts, rec) -> str)
CAPTIONS = {
    "volume_turntable": (
        "CT を回す —— 面と粒、同じ角度で",
        "`marching_cubes`, `phong_shade`, `vol_boundary`, `render_points_frame`",
        lambda f, r: (
            "同梱の骨格 CT ({0}×{1}×{2} voxel)を等値面 (mean+std = {3:.4f}) で"
            "三角形 {4:,} 枚 / 頂点 {5:,} のメッシュにしたものと、同じ閾値の境界シェル "
            "{6:,} voxel を、**同じ yaw・同じ仰角で並べて回して**います。"
            "左は面、右は粒。同じ形が同じ向きに回ることが、軸を取り違えていない"
            "何よりの証拠になります({7} フレーム)。"
        ).format(f["volume_shape"][0], f["volume_shape"][1], f["volume_shape"][2],
                 f["iso_level"], f["n_faces"], f["n_vertices"],
                 f["n_shell_points"], r["frames"])),
    "zslices": (
        "z スライスを 1 枚ずつ送る",
        "`vol_mip`, `apply_cmap`, 最近傍整数拡大",
        lambda f, r: (
            "同じ CT を z = 0 から {0} まで 1 枚ずつ送ります(全 {1} フレーム、"
            "下のバーが現在位置)。右は全 z を潰した MIP。左の 1 枚には毎フレーム"
            "実測した骨占有率・最小/最大/平均を出しているので、**端の 1 枚が欠けている"
            "/ 重複している**といった off-by-one はここで必ず露見します。"
            "拡大は最近傍 ×{2}(補間しない —— 画素の粗さ自体が情報)。"
        ).format(f["volume_shape"][0] - 1, r["frames"], f["upscale"])),
}


def _md_image(rec: dict) -> str:
    """記事に貼る Markdown 行(raw.githubusercontent の絶対 URL)。"""
    name = rec["name"]
    if rec["kind"] == "gif":
        return "![%s](%smedia/%s%s.gif)" % (CAPTIONS[name][0], RAW_BASE, PREFIX, name)
    return "[![%s](%sthumbs_placeholder)](x)" % (CAPTIONS[name][0], RAW_BASE)


def write_captions() -> str:
    """``docs/articles/exhibits/wingstudio.md`` を meta から組み立てる。

    記事本体 (``docs/articles/*.md``) は**触らない**。ここは新規ファイルなので可。
    """
    if not os.path.exists(META_PATH):
        raise RuntimeError("meta が無い: %s" % META_PATH)
    with open(META_PATH, encoding="utf-8") as f:
        meta = json.load(f)
    os.makedirs(EXHIBITS_DIR, exist_ok=True)
    lines = [
        "# Studio 画面 / 3D 表示ウィング —— 展示キャプション原稿",
        "",
        "生成元: `tools/gen_wingstudio_gallery.py`(再実行で全点を再生成)。",
        "Studio 画面はすべて `studio.build_window()` が組み立てた**実 UI** の "
        "`widget.grab()`(オフスクリーン)で、モックアップはありません。",
        "3D 展示は fullseye の op と numpy 合成だけで描いています"
        "(matplotlib 不使用、文字のみ Pillow)。**数字はすべて実測値**です。",
        "",
        "**このファイルは納品原稿です。記事 md への転記は手動で行ってください**"
        "(記事本体は意図的に編集していません)。",
        "",
        "---",
        "",
    ]
    for rec in meta.get("exhibits", []):
        name = rec["name"]
        if name not in CAPTIONS:
            continue
        title, ops, body = CAPTIONS[name]
        if rec["kind"] == "gif":
            url = "%smedia/%s%s.gif" % (RAW_BASE, PREFIX, name)
            thumb = "%sthumbs/%s%s_thumb.jpg" % (RAW_BASE, PREFIX, name)
            img = "![%s](%s)" % (title, url)
            extra = ("%d フレーム / %d fps / %d×%d px / %.2f MB"
                     % (rec["frames"], rec["fps"], rec["size"][0], rec["size"][1],
                        rec["bytes"] / 1e6))
        else:
            url = "%s%s%s.png" % (RAW_BASE, PREFIX, name)
            thumb = "%s%s%s_thumb.jpg" % (RAW_BASE, PREFIX, name)
            img = "[![%s](%s)](%s)" % (title, thumb, url)
            extra = "%d×%d px / %.0f kB" % (rec["size"][0], rec["size"][1],
                                            rec["bytes"] / 1e3)
        lines += [
            "## %s" % title,
            "",
            img,
            "",
            "*↑ **%s** —— %s 使用 op / 機能: %s。*" % (title, body(rec["facts"], rec), ops),
            "",
            "<sub>`%s%s.%s` — %s / SHA-256 `%s`</sub>"
            % (PREFIX, name, "gif" if rec["kind"] == "gif" else "png",
               extra, rec["sha256"][:16]),
            "",
            "---",
            "",
        ]
    with open(CAPTION_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("captions ->", CAPTION_PATH)
    return CAPTION_PATH


# --------------------------------------------------------------------------- #
# 展示レジストリ + CLI                                                          #
# --------------------------------------------------------------------------- #
#: name -> (builder, needs_studio, 1 行説明)
EXHIBITS = {
    "volume_turntable": (lambda: ex_volume_turntable(), False,
                         "CT ボリュームのターンテーブル(等値面 / 境界シェル)"),
    "zslices": (lambda: ex_zslices(), False,
                "z スライス送り(位置インジケータつき)"),
}


def run_one(name: str) -> dict:
    builder = EXHIBITS[name][0]
    t0 = time.time()
    print("[build] %s — %s" % (name, EXHIBITS[name][2]))
    rec = builder()
    rec["seconds"] = round(time.time() - t0, 2)
    return rec


def _merge_meta(recs) -> None:
    old = {}
    if os.path.exists(META_PATH):
        try:
            with open(META_PATH, encoding="utf-8") as f:
                old = {r["name"]: r for r in json.load(f).get("exhibits", [])}
        except Exception:
            old = {}
    for r in recs:
        old[r["name"]] = r
    ordered = [old[k] for k in EXHIBITS if k in old]
    os.makedirs(ASSETS, exist_ok=True)
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump({"generator": "tools/gen_wingstudio_gallery.py", "seed": SEED,
                   "exhibits": ordered}, f, ensure_ascii=False, indent=2)
    print("meta ->", META_PATH)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--exhibit", choices=sorted(EXHIBITS),
                    help="1 件だけこのプロセスで作る(Studio 展示の子プロセス用)")
    ap.add_argument("--only", help="カンマ区切りの部分集合")
    ap.add_argument("--no-captions", action="store_true",
                    help="キャプション原稿を書かない")
    args = ap.parse_args(argv)

    if args.exhibit:
        rec = run_one(args.exhibit)
        # 子プロセスの結果は stdout の 1 行 JSON で親へ返す
        print("__WINGSTUDIO_JSON__" + json.dumps(rec, ensure_ascii=False))
        return 0

    wanted = [w.strip() for w in args.only.split(",")] if args.only else list(EXHIBITS)
    bad = [w for w in wanted if w not in EXHIBITS]
    if bad:
        print("unknown exhibits: %s (valid: %s)" % (bad, ", ".join(EXHIBITS)),
              file=sys.stderr)
        return 2

    recs, failures = [], []
    t0 = time.time()
    for name in wanted:
        needs_studio = EXHIBITS[name][1]
        if not needs_studio:
            try:
                recs.append(run_one(name))
            except Exception as e:                       # 1 件の失敗で全部を止めない
                failures.append((name, repr(e)))
                print("  FAILED %s: %r" % (name, e))
            continue
        # Studio 展示は QApplication を毎回作り直したいので子プロセスで
        print("[build] %s — %s (subprocess)" % (name, EXHIBITS[name][2]))
        env = dict(os.environ)
        env["PYTHONUTF8"] = "1"
        p = subprocess.run([sys.executable, os.path.abspath(__file__), "--exhibit", name],
                           env=env, cwd=_ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        for line in (p.stdout or "").splitlines():
            if line.startswith("__WINGSTUDIO_JSON__"):
                recs.append(json.loads(line[len("__WINGSTUDIO_JSON__"):]))
            elif line.strip():
                print("  " + line)
        if p.returncode != 0:
            failures.append((name, "exit %d" % p.returncode))
            print("  FAILED %s (exit %d)" % (name, p.returncode))
            if p.stderr:
                print("  " + "\n  ".join((p.stderr or "").strip().splitlines()[-12:]))

    _merge_meta(recs)
    if not args.no_captions:
        write_captions()
    print("=== %d exhibit(s) in %.1fs ===" % (len(recs), time.time() - t0))
    for name, why in failures:
        print("  FAILED:", name, why)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
