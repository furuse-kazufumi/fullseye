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


def _plot_axes(canvas, x0, x1, y0, y1):
    """左と下だけの座標軸(imagedraw の実 op で引く)。"""
    import imagedraw
    canvas = imagedraw.draw_line(canvas, (x0, y1), (x1, y1), color=C_DIM, width=1)
    return imagedraw.draw_line(canvas, (x0, y0), (x0, y1), color=C_DIM, width=1)


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
                      _upscale(imgio.apply_cmap(mip_op, name="inferno",
                                                vmin=0.0, vmax=1.0), k),
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
# 展示: 点群レジストレーション(初期ずれ -> 収束、RMSE を焼き込む)             #
# --------------------------------------------------------------------------- #
def ex_registration():
    import imagedraw
    import registration
    import studio
    rng = np.random.default_rng(SEED)
    dst = np.load(os.path.join(_ROOT, "studio_assets", "sample_3d",
                               "itokawa_points.npy")).astype(np.float64)
    c0 = dst.mean(0)
    scale = float(np.linalg.norm(dst - c0, axis=1).max())
    # 既知の剛体変換で「ずらした」観測を作る(seed 固定 = 決定的)
    ang = np.radians(22.0)
    axis = np.array([0.22, -0.35, 0.91]); axis /= np.linalg.norm(axis)
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    R_gt = np.eye(3) + np.sin(ang) * K + (1 - np.cos(ang)) * (K @ K)
    t_gt = np.array([0.11, -0.07, 0.05]) * scale
    noise = rng.normal(0.0, 0.004 * scale, dst.shape)
    src0 = (dst - c0) @ R_gt.T + c0 + t_gt + noise

    n_iter = 48
    R, t = np.eye(3), np.zeros(3)
    hist = []
    for _ in range(n_iter):
        R, t, aligned, rmse = registration.icp(src0, dst, max_iter=1, tol=0.0,
                                               init=(R, t), trim=0.15)
        hist.append((float(rmse), aligned))
    rmses = [h[0] for h in hist]
    rmse0 = float(np.sqrt(((src0 - dst) ** 2).sum(1)).mean())

    S = 470
    PW, PH = S, 356
    W = 24 * 2 + PW + 24 + 430
    H = 52 + PH + 92
    px0, px1 = 24 * 2 + PW + 24, W - 28
    py0, py1 = 96, 96 + 214
    lo, hi = float(min(rmses)), float(max(rmses + [rmse0]))
    ctr, rad = view_radius(np.vstack([dst, src0]), [40.0], 20.0)

    def _plot_y(v):
        return py1 - (py1 - py0) * (v - lo) / max(hi - lo, 1e-12)

    frames = []
    for i in range(n_iter):
        rmse, aligned = hist[i]
        canvas = _canvas(W, H)
        _fill(canvas, 0, 34, 0, W, (0.088, 0.098, 0.118))
        P = np.vstack([dst, aligned])
        C = np.vstack([np.tile([0.30, 0.55, 0.92], (len(dst), 1)),
                       np.tile([0.98, 0.72, 0.22], (len(aligned), 1))])
        view = studio.render_points_frame(P, colors=C, yaw=40.0, pitch=20.0, zoom=1.02,
                                          size=S, point_px=2, center=ctr, radius=rad,
                                          background=C_PANEL)
        lab = _panel(canvas, 52, 24, PH, PW, view[(S - PH) // 2:(S - PH) // 2 + PH],
                     "reference(青) と観測(橙)")
        # RMSE 曲線
        _fill(canvas, py0 - 30, py1 + 44, px0 - 12, px1 + 12, C_PANEL)
        canvas = _plot_axes(canvas, px0, px1, py0, py1)
        pts = [(px0 + (px1 - px0) * j / max(n_iter - 1, 1), _plot_y(rmses[j]))
               for j in range(i + 1)]
        if len(pts) >= 2:
            canvas = imagedraw.draw_polyline(canvas, pts, color=C_AMBER, width=2)
        canvas = imagedraw.draw_markers(canvas, [pts[-1]], color=(1.0, 1.0, 1.0),
                                        size=5, shape="cross", width=2)
        f = _to_u8(canvas)
        lab += [
            (24, 9, "itokawa_points.npy %s 点 / 既知の剛体ずれ %.1f deg + 並進 %.3f "
                    "+ 等方ノイズ sigma = %.4f(seed %d)"
             % (f"{len(dst):,}", np.degrees(ang), float(np.linalg.norm(t_gt)),
                float(0.004 * scale), SEED), C_TEXT, 12, False),
            (px0 - 4, py0 - 26, "trimmed ICP の RMSE(1 反復ずつ実行して実測)",
             (0.96, 0.96, 0.93), 13, True),
            (px0 - 4, py1 + 8, "iteration %2d / %d" % (i + 1, n_iter), C_DIM, 12, False),
            (px1 - 120, py1 + 8, "trim = 0.15", C_DIM, 12, False),
            (px0 - 4, py1 + 30, "RMSE  %8.4f   (初期 %.4f -> 最終 %.4f、%.1f 倍改善)"
             % (rmse, rmses[0], rmses[-1], rmses[0] / max(rmses[-1], 1e-12)),
             C_AMBER, 13, True),
            (px0 - 4, py1 + 52, "注入ノイズ sigma = %.4f(RMSE の下限)"
             % float(0.004 * scale), C_DIM, 12, False),
            (30, 52 + PH + 10, "対応づけ前の素の点間距離平均 = %.4f" % rmse0,
             C_BLUE, 13, True),
            (24, H - 26, "橙が青に吸い付いていく。曲線が下がりきっても橙が青に乗って"
                         "いなければ「収束したのに合っていない」—— 数字だけでは"
                         "見えない失敗が絵では一目で分かります", C_DIM, 12, False),
        ]
        frames.append(_text(f, lab))
    facts = {"n_points": int(len(dst)), "n_iter": n_iter,
             "rotation_deg": 22.0, "translation": round(float(np.linalg.norm(t_gt)), 5),
             "noise_sigma": round(float(0.004 * scale), 5),
             "rmse_first": round(rmses[0], 5), "rmse_last": round(rmses[-1], 5),
             "rmse_raw_before": round(rmse0, 5),
             "improve_x": round(rmses[0] / max(rmses[-1], 1e-12), 2)}
    return save_gif("registration", frames, facts, fps=6, thumb_index=n_iter - 1)


# --------------------------------------------------------------------------- #
# 展示: メッシュと法線(向きを色で / 裏面が見える視点も)                       #
# --------------------------------------------------------------------------- #
def ex_normals():
    import mesh as meshmod
    import render3d
    import render_shade
    stl = os.path.join(_ROOT, "data", "sample_3d_cache", "itokawa_f0049152.stl")
    if os.path.exists(stl):
        V, F = meshmod.read_mesh(stl)
        src = "itokawa_f0049152.stl (JAXA はやぶさ Gaskell 形状モデル)"
    else:                                            # キャッシュが無い環境では CT から
        vol = _load_ct()
        lvl = float(vol.mean() + vol.std())
        Vz, F = render3d.marching_cubes(vol, lvl)
        V = np.ascontiguousarray(Vz[:, ::-1])
        src = "skeleton_ct.npy の等値面"
    V = np.asarray(V, np.float64)
    c = 0.5 * (V.min(0) + V.max(0))
    r = float(np.linalg.norm(V - c, axis=1).max())

    # 面の向きが外向きに揃っているか(巻き方向の健全性)を実測する
    tri = V[np.asarray(F, int)]
    fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    area2 = np.linalg.norm(fn, axis=1)
    fn_u = fn / np.where(area2[:, None] > 1e-15, area2[:, None], 1.0)
    fc = tri.mean(1)
    outward = (fn_u * (fc - c)).sum(1) > 0.0
    frac_out = float(outward.mean())
    total_area = float(0.5 * area2.sum())

    S = 430
    def shot(yaw, pitch):
        a, e = np.radians(yaw), np.radians(pitch)
        eye = c + r * 30.0 * np.array([np.cos(e) * np.cos(a),
                                       np.cos(e) * np.sin(a), np.sin(e)])
        pose = render3d.look_at(eye, c, up=(0.0, 0.0, 1.0))
        Kk = render3d.intrinsics_from_fov(2 * np.degrees(np.arctan(1.0 / (0.92 * 30.0))),
                                          S, S)
        buf = render3d.render_mesh(V, F, pose=pose, intrinsics=Kk, width=S, height=S)
        sil = buf["silhouette"] > 0
        ncam = buf["normals"]
        nworld = ncam @ pose[:3, :3]                 # cam -> world (R^T n を行ベクトルで)
        shade = render_shade.phong_shade(ncam, view=(0, 0, 1), light=(0.3, 0.4, 1.0),
                                         ambient=0.12, diffuse=0.8, specular=0.3)
        gray = _canvas(S, S, C_PANEL)
        gray[sil] = np.clip(shade[sil][:, None] * np.array([0.82, 0.86, 0.92]), 0, 1)
        cam_rgb = _canvas(S, S, C_PANEL)
        cam_rgb[sil] = np.clip(ncam[sil] * 0.5 + 0.5, 0, 1)
        w_rgb = _canvas(S, S, C_PANEL)
        w_rgb[sil] = np.clip(nworld[sil] * 0.5 + 0.5, 0, 1)
        return gray, cam_rgb, w_rgb, int(sil.sum())

    g1, c1, w1, cov1 = shot(35.0, 20.0)
    g2, c2, w2, cov2 = shot(215.0, 20.0)               # ちょうど裏側

    W = 24 * 5 + S * 4
    H = 52 + S + 118
    canvas = _canvas(W, H)
    _fill(canvas, 0, 34, 0, W, (0.088, 0.098, 0.118))
    lab = []
    for j, (img, title) in enumerate((
            (g1, "① 表 yaw 35°  phong_shade"),
            (w1, "② 表  world 法線を RGB に"),
            (g2, "③ 裏 yaw 215°  phong_shade"),
            (w2, "④ 裏  world 法線を RGB に"))):
        lab += _panel(canvas, 52, 24 + j * (S + 24), S, S, img, title)
    f = _to_u8(canvas)
    lab += [
        (24, 9, "%s   三角形 %s 枚 / 頂点 %s   表面積 %.4f"
         % (src, f"{len(F):,}", f"{len(V):,}", total_area), C_TEXT, 13, False),
        (30, 52 + S + 10, "被覆 %s px" % f"{cov1:,}", C_DIM, 12, False),
        (30 + 2 * (S + 24), 52 + S + 10, "被覆 %s px" % f"{cov2:,}", C_DIM, 12, False),
        (24, 52 + S + 36,
         "②と④は **同じ色が同じ向き** を意味する world 法線。裏返しても地面向きは"
         "同じ色のまま —— ここがまだらになっていたら巻き方向(向き付け)が壊れています。",
         C_TEXT, 13, False),
        (24, 52 + S + 60,
         "実測: 面法線が外向き(重心から外を向く)なのは %d / %d = %.2f %%。"
         "①③の陰影は視線に対する向きなので、裏に回れば当然変わります。"
         % (int(outward.sum()), len(F), frac_out * 100.0), C_AMBER, 13, True),
        (24, H - 26, "「法線の色」は 3D のデバッグで最初に見るべき絵です。"
                     "軸の入れ替わりも面の裏返りも、陰影より先に色に出ます。",
         C_DIM, 12, False),
    ]
    facts = {"source": src, "n_faces": int(len(F)), "n_vertices": int(len(V)),
             "outward_fraction": round(frac_out, 5),
             "outward_faces": int(outward.sum()),
             "surface_area": round(total_area, 5),
             "coverage_front_px": cov1, "coverage_back_px": cov2}
    return save_png("normals", _text(f, lab), facts)


# --------------------------------------------------------------------------- #
# 展示: ライトフィールドの視点移動((V, U) を動かすと視差が出る)               #
# --------------------------------------------------------------------------- #
def ex_lightfield():
    import imagedraw
    import imgio
    import lightfield as lf
    AV, AU = 7, 7
    field, slope_gt = lf.lf_synthesize(slopes=(-2.0, 0.0, 3.0), angular=(AV, AU),
                                       shape=(128, 128), occlusion=True,
                                       coverage=0.55, texture_sigma=2.0, seed=SEED)
    st = lf.lf_stats(field)
    vc, uc = st["center_v"], st["center_u"]
    center = lf.lf_center_view(field)
    epi_row = 64
    epi = lf.lf_epi(field, axis="u", index=epi_row)          # (U, W)
    refocus0 = lf.lf_refocus(field, slope=0.0)
    refocus3 = lf.lf_refocus(field, slope=3.0)

    # (v, u) をアパーチャの周を 1 周させる(整数格子だけを踏む = 補間なし)
    ring = []
    for u in range(AU):
        ring.append((0, u))
    for v in range(1, AV):
        ring.append((v, AU - 1))
    for u in range(AU - 2, -1, -1):
        ring.append((AV - 1, u))
    for v in range(AV - 2, 0, -1):
        ring.append((v, 0))

    S = 300
    k = 2
    pw = 128 * k
    W = 24 * 4 + pw * 3
    H = 52 + pw + 250
    frames = []
    for (v, u) in ring:
        view = lf.lf_subaperture(field, v=v, u=u)
        diff = np.abs(view - center)
        canvas = _canvas(W, H)
        _fill(canvas, 0, 34, 0, W, (0.088, 0.098, 0.118))
        lab = []
        lab += _panel(canvas, 52, 24, pw, pw, _gray3(_upscale(view, k)),
                      "サブアパーチャ像 (v, u) = (%d, %d)" % (v, u))
        lab += _panel(canvas, 52, 24 * 2 + pw, pw, pw,
                      _upscale(imgio.apply_cmap(diff, name="magma",
                                                vmin=0.0, vmax=float(np.abs(field - center).max())), k),
                      "中央視点との差 = 視差")
        lab += _panel(canvas, 52, 24 * 3 + pw * 2, pw, pw,
                      _upscale(imgio.apply_cmap(slope_gt, name="viridis"), k),
                      "真値の傾き slope [px/step]")
        # アパーチャ図(どの視点を見ているか)
        ax0, ay0, cell = 24, 52 + pw + 26, 18
        for vv in range(AV):
            for uu in range(AU):
                on = (vv == v and uu == u)
                col = C_ACCENT if on else (0.24, 0.27, 0.32)
                _fill(canvas, ay0 + vv * cell + 2, ay0 + (vv + 1) * cell - 2,
                      ax0 + uu * cell + 2, ax0 + (uu + 1) * cell - 2, col)
        # EPI(u 対 x)と現在の u
        ex0, ey0 = 24 * 2 + pw, 52 + pw + 26
        eh = AU * 10
        _paste(canvas, _gray3(np.repeat(np.repeat(epi, 10, 0), pw / epi.shape[1], 1)
                              [:eh, :pw]), ey0, ex0)
        canvas = imagedraw.draw_line(canvas, (ex0, ey0 + u * 10 + 5),
                                     (ex0 + pw - 1, ey0 + u * 10 + 5),
                                     color=C_AMBER, width=1)
        f = _to_u8(canvas)
        lab += [
            (24, 9, "lf_synthesize  slopes = (-2, 0, 3) px/step  angular = %dx%d  "
                    "spatial = %dx%d  seed = %d  (occlusion あり)"
             % (AV, AU, field.shape[2], field.shape[3], SEED), C_TEXT, 12, False),
            (ax0, ay0 - 20, "アパーチャ上の位置", (0.96, 0.96, 0.93), 12, True),
            (ex0, ey0 - 20, "EPI  行 y = %d(u 対 x)—— 傾きが奥行き" % epi_row,
             (0.96, 0.96, 0.93), 12, True),
            (24 * 3 + pw * 2, ay0 - 20, "実測値", (0.96, 0.96, 0.93), 12, True),
            (24 * 3 + pw * 2, ay0 + 2, "最大視差  %.2f px" % st["max_slope_px"],
             C_AMBER, 13, True),
            (24 * 3 + pw * 2, ay0 + 24, "この視点の差 平均 %.4f / 最大 %.4f"
             % (float(diff.mean()), float(diff.max())), C_TEXT, 12, False),
            (24 * 3 + pw * 2, ay0 + 44, "視点数 %d(中心は %s)"
             % (st["n_views"], "実在" if st["center_is_a_view"] else "補間"),
             C_TEXT, 12, False),
            (24 * 3 + pw * 2, ay0 + 64, "slope=0 で再合焦した分散 %.5f"
             % float(refocus0.var()), C_TEXT, 12, False),
            (24 * 3 + pw * 2, ay0 + 84, "slope=3 で再合焦した分散 %.5f"
             % float(refocus3.var()), C_TEXT, 12, False),
            (24, H - 26, "同じ被写体を 49 個のカメラで撮ったのと同じこと。近いものほど"
                         "大きく動く —— 差の絵が「どこが手前か」をそのまま描きます",
             C_DIM, 12, False),
        ]
        frames.append(_text(f, lab))
    facts = {"angular": [AV, AU], "spatial": [int(field.shape[2]), int(field.shape[3])],
             "n_views": int(st["n_views"]), "max_slope_px": round(float(st["max_slope_px"]), 4),
             "frames": len(ring), "epi_row": epi_row,
             "refocus_var_slope0": round(float(refocus0.var()), 6),
             "refocus_var_slope3": round(float(refocus3.var()), 6)}
    return save_gif("lightfield", frames, facts, fps=8, thumb_index=3)


# --------------------------------------------------------------------------- #
# 展示: 深度マップ -> 3D(持ち上げる過程)                                      #
# --------------------------------------------------------------------------- #
def ex_depth3d():
    import camera
    import imgio
    import mesh as meshmod
    import render3d
    import studio
    stl = os.path.join(_ROOT, "data", "sample_3d_cache", "itokawa_f0049152.stl")
    if os.path.exists(stl):
        V, F = meshmod.read_mesh(stl)
        src = "itokawa_f0049152.stl"
    else:
        vol = _load_ct()
        Vz, F = render3d.marching_cubes(vol, float(vol.mean() + vol.std()))
        V = np.ascontiguousarray(Vz[:, ::-1]); src = "skeleton_ct.npy 等値面"
    RES = 200
    pose, K = render3d.auto_view(V, width=RES, height=RES)
    buf = render3d.render_mesh(V, F, pose=pose, intrinsics=K, width=RES, height=RES)
    depth = np.asarray(buf["depth"], np.float64)
    valid = np.isfinite(depth)
    dmin, dmax = float(depth[valid].min()), float(depth[valid].max())
    # 背景 (inf) は持ち上げない: 有効画素だけを 3D にする
    d_fill = np.where(valid, depth, dmax)
    P_full = camera.depth_to_points(d_fill, K, organized=True)     # (H, W, 3)
    P_valid = P_full[valid]
    n_pts = int(P_valid.shape[0])
    # 「平らな板」から「本当の奥行き」へ補間する(0 -> 1)
    P_flat = camera.depth_to_points(np.full_like(d_fill, 0.5 * (dmin + dmax)),
                                    K, organized=True)[valid]
    gray = (d_fill - dmin) / max(dmax - dmin, 1e-12)
    colors = imgio.apply_cmap(1.0 - gray, name="viridis")[valid]

    S = 440
    PW = S
    W = 24 * 3 + 300 + PW
    H = 52 + S + 128
    ctr, rad = view_radius(P_valid, [30.0, 90.0], 18.0)
    frames, n = [], 30
    for i in range(n):
        tt = i / (n - 1)
        s = 0.5 - 0.5 * np.cos(np.pi * min(1.0, tt * 1.25))     # ease-in-out
        Q = P_flat * (1.0 - s) + P_valid * s
        yaw = 30.0 + 60.0 * tt
        canvas = _canvas(W, H)
        _fill(canvas, 0, 34, 0, W, (0.088, 0.098, 0.118))
        lab = []
        lab += _panel(canvas, 52, 24, 300, 300,
                      imgio.apply_cmap(np.where(valid, depth, np.nan), name="viridis"),
                      "深度マップ (H, W) = (%d, %d)" % (RES, RES))
        view = studio.render_points_frame(Q, colors=colors, yaw=yaw, pitch=18.0,
                                          zoom=0.95, size=S, point_px=2,
                                          center=ctr, radius=rad, background=C_PANEL)
        lab += _panel(canvas, 52, 24 * 2 + 300, S, PW, view,
                      "持ち上げた点群  lift = %3.0f %%" % (s * 100.0))
        f = _to_u8(canvas)
        lab += [
            (24, 9, "%s を render_mesh で深度化 -> camera.depth_to_points で逆投影"
             % src, C_TEXT, 13, False),
            (30, 52 + 300 + 14, "有効画素 %s / %s (%.1f %%)"
             % (f"{n_pts:,}", f"{RES * RES:,}", 100.0 * n_pts / (RES * RES)),
             C_ACCENT, 13, True),
            (30, 52 + 300 + 36, "深度 %.4f .. %.4f" % (dmin, dmax), C_TEXT, 12, False),
            (30, 52 + 300 + 56, "背景 (inf) は持ち上げない", C_DIM, 12, False),
            (30, 52 + 300 + 84, "lift = 0 %% は全画素を同じ深さに", C_DIM, 12, False),
            (30, 52 + 300 + 104, "置いた「板」。1 枚の絵が", C_DIM, 12, False),
            (30, 52 + 300 + 124, "立体になる瞬間が見える。", C_DIM, 12, False),
            (24, H - 26, "深度マップは「画素ごとの距離」でしかない。逆投影して回すと、"
                         "焦点距離や主点がずれていれば形が歪んで即座に分かります",
             C_DIM, 12, False),
        ]
        frames.append(_text(f, lab))
    facts = {"source": src, "resolution": RES, "n_points": n_pts,
             "valid_fraction": round(n_pts / (RES * RES), 5),
             "depth_min": round(dmin, 6), "depth_max": round(dmax, 6), "frames": n}
    return save_gif("depth3d", frames, facts, fps=10, thumb_index=n - 1)


# --------------------------------------------------------------------------- #
# 展示: 欠陥の CAD 面への逆写像(遮蔽・可視面カバレッジ)                       #
# --------------------------------------------------------------------------- #
def _cad_part(res=64):
    """検査対象らしい段付き部品を SDF から作る(決定的・外部データ不要)。"""
    import meshrepair
    import render3d
    import sdf_ops
    grid, _ext = sdf_ops.grid_coords((-40.0, 40.0, -40.0, 40.0, -14.0, 46.0), res)
    base = sdf_ops.box_sdf(grid, (0.0, 0.0, 0.0), (30.0, 30.0, 6.0))
    tower = sdf_ops.box_sdf(grid, (6.0, -4.0, 16.0), (10.0, 10.0, 16.0))
    boss = sdf_ops.sphere_sdf(grid, (-17.0, 14.0, 6.0), 9.0)
    hole = sdf_ops.sphere_sdf(grid, (-17.0, 14.0, 12.0), 5.0)
    part = sdf_ops.sdf_subtract(sdf_ops.sdf_union(sdf_ops.sdf_smooth_union(base, tower, 3.0),
                                                  boss), hole)
    vol = np.transpose(part, (2, 1, 0))               # (nx,ny,nz) -> (D,H,W)=(z,y,x)
    Vz, F = render3d.marching_cubes(vol, 0.0)
    V = np.ascontiguousarray(Vz[:, ::-1])             # -> world (x, y, z) 添字空間
    V, F = meshrepair.decimate_qem(V, F, 1400)        # レイキャストが現実的な面数へ
    return np.asarray(V, np.float64), np.asarray(F, int)


def ex_cadmap():
    import cadmap
    import camera
    import imgio
    import mesh as meshmod
    import render3d
    import render_shade
    import studio
    V, F = _cad_part()
    c = 0.5 * (V.min(0) + V.max(0))
    r = float(np.linalg.norm(V - c, axis=1).max())
    tri = V[F]
    face_area = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0],
                                              tri[:, 2] - tri[:, 0]), axis=1)
    total_area = float(face_area.sum())

    # --- 検査カメラ(固定)。camera.py の慣習: +Z 前方 ------------------------ #
    RES = 240
    fx = fy = 1.35 * RES
    Kk = camera.intrinsic_matrix(fx, fy, (RES - 1) / 2.0, (RES - 1) / 2.0)
    az, el = np.radians(38.0), np.radians(34.0)
    eye = c + 3.1 * r * np.array([np.cos(el) * np.cos(az),
                                  np.cos(el) * np.sin(az), np.sin(el)])
    fwd = c - eye; fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, np.array([0.0, 0.0, 1.0])); right /= np.linalg.norm(right)
    down = np.cross(fwd, right)
    Rw = np.stack([right, down, fwd])                 # world -> camera (行が基底)
    tw = -Rw @ eye

    # 検査カメラの深度画像(render3d は -Z 前方なので、こちらは cadmap のレイで作る)
    vv, uu = np.mgrid[0:RES, 0:RES]
    pix = np.stack([uu.ravel(), vv.ravel()], 1).astype(np.float64)
    hit = cadmap.cad_pixel_to_surface((V, F), pix, K=Kk, R=Rw, t=tw,
                                      image_size=(RES, RES))
    fid = hit["face_id"].reshape(RES, RES)
    depth = hit["depth"].reshape(RES, RES)
    nrm = hit["normal"].reshape(RES, RES, 3)
    mask = fid >= 0
    n_hit = int(mask.sum())

    # 面 ID の色分け(隣り合う面が別色になるよう ID をハッシュ)
    hue = ((fid.astype(np.int64) * 2654435761) % 997) / 997.0
    fid_rgb = imgio.apply_cmap(np.where(mask, hue, 0.0), name="turbo", vmin=0.0, vmax=1.0)
    fid_rgb[~mask] = np.asarray(C_PANEL)

    # 陰影(法線 -> ランバート)
    L = np.array([0.35, 0.35, -0.87]); L /= np.linalg.norm(L)
    lam = np.clip(-(nrm @ L), 0.0, 1.0) * 0.8 + 0.18
    shaded = _canvas(RES, RES, C_PANEL)
    shaded[mask] = np.clip(lam[mask][:, None] * np.array([0.80, 0.85, 0.92]), 0, 1)

    # --- 画像上に欠陥ラベルを描く -> CAD 面へ逆写像 --------------------------- #
    labels = np.zeros((RES, RES), np.int32)
    yy, xx = np.mgrid[0:RES, 0:RES]
    blobs = [(1, 96, 104, 11), (2, 150, 78, 8), (3, 70, 160, 9), (4, 30, 34, 7)]
    for lid, cy, cx, rad in blobs:
        labels[((yy - cy) ** 2 + (xx - cx) ** 2) <= rad * rad] = lid
    table = cadmap.cad_defect_to_cad((V, F), labels, K=Kk, R=Rw, t=tw,
                                     image_size=(RES, RES))
    defect_rgb = shaded.copy()
    pal = {1: (0.98, 0.72, 0.22), 2: (0.13, 0.85, 0.80),
           3: (0.66, 0.55, 0.95), 4: (0.95, 0.45, 0.45)}
    for lid, col in pal.items():
        defect_rgb[labels == lid] = np.asarray(col)

    # --- 検査カメラから見えた面 = 可視面カバレッジ ---------------------------- #
    seen = cadmap.cad_visible_faces((V, F), K=Kk, R=Rw, t=tw,
                                    width=RES, height=RES)
    seen_mask = np.zeros(len(F), bool)
    seen_mask[seen] = True
    cov_faces = float(seen_mask.mean())
    cov_area = float(face_area[seen_mask].sum() / total_area)

    # 表面点を撒いて「検査カメラから見えたか」を点ごとに判定(遮蔽つき)
    SP = 26000
    pts = meshmod.sample_surface(V, F, SP, seed=SEED)
    proj = cadmap.cad_surface_to_pixel((V, F), pts, K=Kk, R=Rw, t=tw,
                                       image_size=(RES, RES))
    vis = np.asarray(proj["visible"], bool)
    occl = np.asarray(proj["occluded"], bool)
    pt_col = np.where(vis[:, None], np.array([0.20, 0.72, 0.62]),
                      np.array([0.92, 0.42, 0.36]))
    pt_vis_frac = float(vis.mean())

    S = 330
    W = 24 * 5 + S * 4
    H = 52 + S + 190
    ctr, rad3 = view_radius(pts, [0.0, 90.0, 180.0, 270.0], 22.0)
    frames, n = [], 24
    for i in range(n):
        yaw = 360.0 * i / n
        canvas = _canvas(W, H)
        _fill(canvas, 0, 34, 0, W, (0.088, 0.098, 0.118))
        lab = []
        lab += _panel(canvas, 52, 24, S, S, shaded, "① 検査カメラの見え方(固定)")
        lab += _panel(canvas, 52, 24 * 2 + S, S, S, fid_rgb, "② 画素 -> CAD 面 ID")
        lab += _panel(canvas, 52, 24 * 3 + S * 2, S, S, defect_rgb,
                      "③ 画像上の欠陥ラベル 4 件")
        v3 = studio.render_points_frame(pts, colors=pt_col, yaw=yaw, pitch=22.0,
                                        zoom=0.98, size=S, point_px=2,
                                        center=ctr, radius=rad3, background=C_PANEL)
        lab += _panel(canvas, 52, 24 * 4 + S * 3, S, S, v3,
                      "④ 見えた面(緑)/ 見えない面(赤)  yaw %3.0f°" % yaw)
        f = _to_u8(canvas)
        y0 = 52 + S + 14
        lab += [
            (24, 9, "SDF から作った段付き部品  三角形 %s 枚 / 頂点 %s  表面積 %.1f   "
                    "検査カメラ %dx%d px, fx = fy = %.0f"
             % (f"{len(F):,}", f"{len(V):,}", total_area, RES, RES, fx),
             C_TEXT, 12, False),
            (30, y0, "命中画素 %s / %s (%.1f %%)"
             % (f"{n_hit:,}", f"{RES * RES:,}", 100.0 * n_hit / (RES * RES)),
             C_ACCENT, 12, True),
            (24 * 2 + S, y0, "到達した面 %s 種"
             % f"{len(np.unique(fid[mask])):,}", C_ACCENT, 12, True),
            (24 * 3 + S * 2, y0, "欠陥の逆写像(cad_defect_to_cad)",
             (0.96, 0.96, 0.93), 12, True),
            (24 * 4 + S * 3, y0, "可視面カバレッジ", (0.96, 0.96, 0.93), 12, True),
            (24 * 4 + S * 3, y0 + 22, "面数 %d / %d = %.1f %%"
             % (int(seen_mask.sum()), len(F), cov_faces * 100.0), C_AMBER, 13, True),
            (24 * 4 + S * 3, y0 + 44, "面積比 %.1f %%" % (cov_area * 100.0),
             C_AMBER, 13, True),
            (24 * 4 + S * 3, y0 + 66, "表面点 %s のうち可視 %.1f %%(うち遮蔽 %.1f %%)"
             % (f"{SP:,}", pt_vis_frac * 100.0, 100.0 * float(occl.mean())),
             C_TEXT, 12, False),
        ]
        for j, rec in enumerate(table[:4]):
            lab.append((24 * 3 + S * 2, y0 + 22 + j * 20,
                        "#%d  画素 %3d  命中 %3d (%3.0f%%)  面 %2d 枚  実面積 %7.2f  深さ %6.2f"
                        % (rec["label"], rec["n_pixels"], rec["n_hit"],
                           100.0 * rec["hit_fraction"], len(rec["face_ids"]),
                           rec["area"], rec["depth_mean"]),
                        pal.get(rec["label"], C_TEXT), 12, False))
        lab.append((24, H - 26,
                    "④ を回すと、検査カメラから **物理的に見えていない面** が赤で残ります。"
                    "「撮ったのに欠陥ゼロ」は、見えていないだけかもしれない —— "
                    "カバレッジを 3D で見る意味はそこにあります", C_DIM, 12, False))
        frames.append(_text(f, lab))
    facts = {"n_faces": int(len(F)), "n_vertices": int(len(V)),
             "surface_area": round(total_area, 3), "image": [RES, RES],
             "hit_pixels": n_hit, "hit_fraction": round(n_hit / (RES * RES), 5),
             "faces_seen": int(seen_mask.sum()),
             "coverage_faces": round(cov_faces, 5),
             "coverage_area": round(cov_area, 5),
             "sample_points": SP, "point_visible_fraction": round(pt_vis_frac, 5),
             "point_occluded_fraction": round(float(occl.mean()), 5),
             "defects": [{"label": int(t["label"]), "n_pixels": int(t["n_pixels"]),
                          "n_hit": int(t["n_hit"]),
                          "hit_fraction": round(float(t["hit_fraction"]), 4),
                          "n_faces": int(len(t["face_ids"])),
                          "area": round(float(t["area"]), 4),
                          "area_naive": round(float(t["area_naive"]), 4),
                          "depth_mean": round(float(t["depth_mean"]), 4)}
                         for t in table],
             "frames": n}
    return save_gif("cadmap", frames, facts, fps=10, thumb_index=5)


# --------------------------------------------------------------------------- #
# 展示: 3D の処理領域 crop -> 処理 -> 貼り戻し                                  #
# --------------------------------------------------------------------------- #
def ex_crop3d():
    import studio
    import volops
    vol = _load_ct()
    thr = float(vol.mean() + vol.std())
    domain = np.zeros_like(vol)
    D, Hh, Ww = vol.shape
    domain[:, 20:56, :] = 1.0                      # 「ここだけ処理する」領域
    part, off = volops.vol_crop_domain(vol, domain=domain, margin=2)
    grad = volops.vol_gradient_magnitude(part)
    full = volops.vol_uncrop(grad, off, vol.shape, fill=0.0)

    def shell_pts(v, thresh, origin=(0, 0, 0)):
        m = (v > thresh).astype(np.float64)
        b = volops.vol_boundary(m, connectivity=6)
        idx = np.argwhere(b > 0.5).astype(np.float64) + np.asarray(origin, np.float64)
        return np.ascontiguousarray(idx[:, ::-1])   # (z,y,x) -> world (x,y,z)

    P_all = shell_pts(vol, thr)
    P_part = shell_pts(part, thr, origin=off)
    gthr = float(grad[grad > 0].mean()) if (grad > 0).any() else 0.0
    P_proc = shell_pts(grad, gthr, origin=off)
    P_back = shell_pts(full, gthr)

    stages = [
        ("① 元のボリューム全体", P_all, np.array([0.42, 0.47, 0.55])),
        ("② 処理領域だけを切り出す vol_crop_domain", P_part, np.array([0.13, 0.85, 0.80])),
        ("③ 切り出した中だけ処理 vol_gradient_magnitude", P_proc, np.array([0.96, 0.65, 0.14])),
        ("④ 元の座標系へ貼り戻す vol_uncrop", P_back, np.array([0.66, 0.55, 0.95])),
    ]
    ctr, rad = view_radius(P_all, [0.0, 60.0, 120.0, 180.0, 240.0, 300.0], 20.0)

    S = 452
    CY0, CY1 = int(0.18 * S), int(0.82 * S)
    PH = CY1 - CY0
    W = 24 * 3 + S * 2
    H = 52 + PH + 150
    frames, per = [], 9
    same_shape = (full.shape == vol.shape)
    n_back, n_proc = len(P_back), len(P_proc)
    for si, (title, P, col) in enumerate(stages):
        for j in range(per):
            yaw = 360.0 * (si * per + j) / (len(stages) * per)
            canvas = _canvas(W, H)
            _fill(canvas, 0, 34, 0, W, (0.088, 0.098, 0.118))
            ref = studio.render_points_frame(
                P_all, colors=np.tile([0.26, 0.29, 0.35], (len(P_all), 1)),
                yaw=yaw, pitch=20.0, zoom=1.0, size=S, point_px=2,
                center=ctr, radius=rad, background=C_PANEL)
            cur = studio.render_points_frame(
                P, colors=np.tile(col, (len(P), 1)), yaw=yaw, pitch=20.0, zoom=1.0,
                size=S, point_px=2, center=ctr, radius=rad, background=C_PANEL)
            over = np.maximum(ref, cur)              # 全体を薄く、当該段を強く
            lab = []
            lab += _panel(canvas, 52, 24, PH, S, cur[CY0:CY1], title)
            lab += _panel(canvas, 52, 24 * 2 + S, PH, S, over[CY0:CY1],
                          "元の全体(灰)に重ねる = 位置がずれていないか")
            f = _to_u8(canvas)
            lab += [
                (24, 9, "skeleton_ct.npy (%d,%d,%d)  処理領域 = y ∈ [20, 56)  margin = 2  "
                        "-> 切り出し %s  offset (z,y,x) = %s"
                 % (D, Hh, Ww, "x".join(str(s) for s in part.shape),
                    "(%d, %d, %d)" % tuple(int(o) for o in off)), C_TEXT, 12, False),
                (30, 52 + PH + 14, "この段の点数 %s" % f"{len(P):,}", col, 13, True),
                (24, 52 + PH + 40,
                 "貼り戻し後の形状 = %s(元と一致: %s)   貼り戻し前後の点数 %s -> %s"
                 % ("x".join(str(s) for s in full.shape), "はい" if same_shape else "いいえ",
                    f"{n_proc:,}", f"{n_back:,}"),
                 C_ACCENT if same_shape else C_AMBER, 13, True),
                (24, 52 + PH + 62,
                 "貼り戻した外側が完全にゼロか: %s(領域外の最大値 %.6g)"
                 % ("はい" if float(full[domain < 0.5].max()) == 0.0 else "いいえ",
                    float(full[domain < 0.5].max())), C_TEXT, 12, False),
                (24, H - 26, "切り出して処理して戻す —— 戻す時に 1 voxel ずれても "
                             "2D の表では気づけません。元の全体に重ねて回せば一発です",
                 C_DIM, 12, False),
            ]
            frames.append(_text(f, lab))
    facts = {"volume_shape": [D, Hh, Ww], "crop_shape": [int(s) for s in part.shape],
             "offset": [int(o) for o in off], "domain": "y in [20, 56)",
             "uncrop_shape_matches": bool(same_shape),
             "outside_max_after_uncrop": float(full[domain < 0.5].max()),
             "n_points": {"all": int(len(P_all)), "crop": int(len(P_part)),
                          "processed": int(n_proc), "pasted": int(n_back)},
             "frames": len(stages) * per}
    return save_gif("crop3d", frames, facts, fps=8, thumb_index=per * 3 + 4)


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
    "registration": (lambda: ex_registration(), False,
                     "点群レジストレーション(初期ずれ -> 収束、RMSE つき)"),
    "normals": (lambda: ex_normals(), False,
                "メッシュと法線(向きを色で / 裏面も)"),
    "lightfield": (lambda: ex_lightfield(), False,
                   "ライトフィールドの視点移動(視差)"),
    "depth3d": (lambda: ex_depth3d(), False,
                "深度マップ -> 3D(持ち上げる過程)"),
    "cadmap": (lambda: ex_cadmap(), False,
               "欠陥の CAD 面への逆写像 + 可視面カバレッジ"),
    "crop3d": (lambda: ex_crop3d(), False,
               "3D の処理領域 crop -> 処理 -> 貼り戻し"),
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
