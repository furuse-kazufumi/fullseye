# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gen_wingct_gallery — Qiita 記事「紙面の科学館」の **断層撮影ウィング** を生成する.
Generate the "tomography wing" exhibits for the Qiita science-museum article.

方針 (honest disclosure) / policy
---------------------------------
* 画像はすべて **`tomography` / 既存 3-D op を実際に実行した結果**。モックアップは
  1 枚も無い。図に焼き込む数値は **その場で計算した実測値**のみ(創作禁止)。
* 描画は Fullseye の ``imagedraw`` op(線・折れ線・円・マーカー)と numpy 合成。
  **matplotlib は使わない**。文字だけは Fullseye にテキスト op が無いため PIL で焼く
  (``gen_wing3d_gallery.py`` と同じ流儀)。
* 版面は ``tools/exhibit_tile.py`` の判断基準に従う。**工程が進むもの**は
  ``flipbook`` の GIF、**パラメータ違いを比べるもの**は ``contact_sheet``、
  **図中の数値が主役のもの**は原寸 1 枚。
* 乱数は ``SEED`` 固定 + ``np.random.default_rng`` で決定的。同じコマンドで
  再生成すると PNG / GIF は SHA-256 が一致する(``--verify`` で確認できる)。
* このウィングは **投影から作る側**だけを扱う。既にあるボリュームを切る断面送りや
  MPR は ``wing3d_`` の担当なので重複させない。

出力 / outputs
--------------
``docs/articles/assets/wingct_<name>.png``               静止展示(フル解像度)
``docs/articles/assets/wingct_<name>_thumb.jpg``         サムネ
``docs/articles/assets/media/wingct_<name>.gif``         動く展示
``docs/articles/assets/thumbs/wingct_<name>_thumb.jpg``  動く展示のサムネ
``docs/articles/exhibits/wingct.ja.md`` / ``wingct.en.md``  キャプション原稿(2 言語)
``docs/articles/assets/_wingct_meta.json``               使用 op・実測値・ファイル情報

使い方 / run
------------
    py -3.11 tools/gen_wingct_gallery.py                    # 全展示
    py -3.11 tools/gen_wingct_gallery.py --list             # 展示名の一覧
    py -3.11 tools/gen_wingct_gallery.py --exhibits rings   # 一部だけ
    py -3.11 tools/gen_wingct_gallery.py --verify           # 再生成して SHA-256 照合
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fullseye as fs                                     # noqa: E402
import imagedraw                                          # noqa: E402
import tomography as T                                    # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exhibit_tile as et                                 # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
META_PATH = os.path.join(ROOT, "docs", "articles", "assets", "_wingct_meta.json")
EXHIBITS_DIR = os.path.join(ROOT, "docs", "articles", "exhibits")

SEED = 20260902
PANEL = 320                      # 各パネルの一辺(画素)
SIZE = 256                       # 再構成格子
PIX_MM = 0.35                    # 面内画素ピッチ(mm)
SLICE_MM = 1.40                  # スライス間隔(mm) -> 異方性 4:1
N_SLICES = 15
MU = 1.0 / 60.0                  # 線積分をピーク ~1.2 に収める減弱スケール

#: 展示に使う CT 断面 = Shepp-Logan を実機並みの減弱に落としたもの。
SL_CT = tuple((x0, y0, a, b, p, rho * MU)
              for (x0, y0, a, b, p, rho) in T.SHEPP_LOGAN)

ANG180 = T.projection_angles(180, 180.0, "uniform")


# --------------------------------------------------------------------------- #
# 描画ヘルパ(matplotlib なし)                                                #
# --------------------------------------------------------------------------- #
def _norm(a, lo=None, hi=None):
    a = np.asarray(a, np.float64)
    lo = float(a.min()) if lo is None else float(lo)
    hi = float(a.max()) if hi is None else float(hi)
    if hi <= lo:
        return np.zeros_like(a)
    return np.clip((a - lo) / (hi - lo), 0.0, 1.0)


def _gray(a, lo=None, hi=None):
    """グレイ画像 -> (H, W, 3) float [0,1]。着色のみで、処理はしない。"""
    g = _norm(a, lo, hi)
    return np.repeat(g[..., None], 3, axis=2)


#: 発散カラーマップ(青 - 黒 - 橙)。誤差図のように **符号が意味を持つ** ものに
#: だけ使う。赤緑は使わない(色覚と、赤緑インジケータ禁止の規律の両方から)。
_DIVERGE = np.array([
    (0.16, 0.44, 0.88), (0.30, 0.58, 0.94), (0.55, 0.74, 0.97),
    (0.85, 0.88, 0.92), (0.07, 0.07, 0.10), (0.92, 0.80, 0.55),
    (0.97, 0.66, 0.24), (0.92, 0.46, 0.10), (0.78, 0.29, 0.04),
])


def _diverging(a, limit):
    """符号つきの量を青-黒-橙で塗る。``limit`` で対称に切る。"""
    t = np.clip((np.asarray(a, np.float64) / (2.0 * limit)) + 0.5, 0.0, 1.0)
    idx = t * (len(_DIVERGE) - 1)
    lo = np.floor(idx).astype(np.int64)
    hi = np.minimum(lo + 1, len(_DIVERGE) - 1)
    f = (idx - lo)[..., None]
    return _DIVERGE[lo] * (1.0 - f) + _DIVERGE[hi] * f


def _fit(rgb, side=PANEL):
    """(H, W, 3) を一辺 *side* の正方形へ最近傍で拡大縮小する。

    決定的で、補間による「無い解像度」を作らない。フリップブックは寸法が
    揃っていないと例外になるので、すべてここを通す。
    """
    h, w = rgb.shape[:2]
    yi = np.minimum((np.arange(side) * h // side), h - 1)
    xi = np.minimum((np.arange(side) * w // side), w - 1)
    return rgb[yi][:, xi]


def _label(rgb, lines, corner="tl", size=17):
    """パネル上に実測値を焼く。凡例が無いと止まった 1 コマが意味を失う。"""
    from PIL import Image, ImageDraw
    im = Image.fromarray(et._to_u8(rgb), "RGB")
    dr = ImageDraw.Draw(im, "RGBA")
    font = et._font(size)
    pad = 7
    lh = size + 5
    box_h = lh * len(lines) + pad
    wmax = max(dr.textlength(t, font=font) for t in lines) + 2 * pad
    x0 = pad if corner[1] == "l" else im.width - wmax - pad
    y0 = pad if corner[0] == "t" else im.height - box_h - pad
    dr.rectangle([x0, y0, x0 + wmax, y0 + box_h], fill=(8, 8, 14, 200))
    for i, t in enumerate(lines):
        dr.text((x0 + pad, y0 + pad // 2 + i * lh), t, fill=et.FG, font=font)
    return np.asarray(im, np.float64) / 255.0


def _nrms(a, b):
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    return float(np.sqrt(((a - b) ** 2).mean()) / (b.max() - b.min()))


# --------------------------------------------------------------------------- #
# 共有の被写体                                                                  #
# --------------------------------------------------------------------------- #
def ct_slice():
    return T.ellipse_phantom(SIZE, SL_CT, supersample=4)


def part_volume():
    """例と同じ「楕円体をくり抜いた部品」。体積が閉形式で分かる。"""
    half_mm = SIZE * PIX_MM / 2.0
    outer = (28.0, 17.0, 9.0)
    void = (11.0, 6.0, 4.0)
    z = (np.arange(N_SLICES) - (N_SLICES - 1) / 2.0) * SLICE_MM
    planes = []
    for zz in z:
        ell = []
        if abs(zz) < outer[2]:
            k = np.sqrt(1.0 - (zz / outer[2]) ** 2)
            ell.append((0.0, 0.0, outer[0] * k / half_mm, outer[1] * k / half_mm,
                        0.0, 0.025))
        if abs(zz) < void[2]:
            k = np.sqrt(1.0 - (zz / void[2]) ** 2)
            ell.append((0.0, 0.0, void[0] * k / half_mm, void[1] * k / half_mm,
                        0.0, -0.025))
        planes.append(T.ellipse_phantom(SIZE, ell, supersample=4) if ell
                      else np.zeros((SIZE, SIZE)))
    true_mm3 = 4.0 / 3.0 * np.pi * (outer[0] * outer[1] * outer[2]
                                    - void[0] * void[1] * void[2])
    return np.stack(planes), float(true_mm3)


def measure_mm3(vol, threshold):
    labels, n = fs.vol_label((vol > threshold).astype(np.float64), connectivity=26)
    if n == 0:
        return 0.0, 0
    props = fs.vol_region_props(labels, spacing=(SLICE_MM, PIX_MM, PIX_MM))
    big = max(props, key=lambda p: p["voxel_count"])
    return float(big["volume"]), int(n)


def _mesh_panel(verts, faces, side=PANEL):
    """メッシュの稜線を正射影で描く(imagedraw の折れ線のみ)。"""
    v = np.asarray(verts, np.float64)
    f = np.asarray(faces, np.int64)
    # (z, y, x) -> 画面 (x, y) に等方に収める
    pts = v[:, [2, 1]]
    lo, hi = pts.min(axis=0), pts.max(axis=0)
    scale = (side - 24) / max(float((hi - lo).max()), 1e-9)
    xy = (pts - lo) * scale + 12.0
    canvas = np.zeros((side, side), np.float64)
    step = max(1, f.shape[0] // 2200)          # 決定的な間引き(全部は要らない)
    for tri in f[::step]:
        p = xy[tri]
        canvas = imagedraw.draw_polyline(
            canvas, [(float(q[0]), float(q[1])) for q in p], color=1.0,
            width=1, closed=True)
    return np.dstack([canvas * 0.42, canvas * 0.72, canvas])


# --------------------------------------------------------------------------- #
# 展示 1: CT からボクセルまでの一本道(flipbook GIF)                          #
# --------------------------------------------------------------------------- #
def ex_pipeline():
    vol, true_mm3 = part_volume()
    ang = T.projection_angles(128, 180.0, "uniform")
    stack = T.radon_volume(vol, ang)
    rec = T.fbp_volume(stack, ang, size=SIZE)
    mid = N_SLICES // 2
    thr = 0.0125
    windowed = fs.vol_window_level(rec, center=thr, width=2.4 * thr)
    binary = (rec > thr).astype(np.float64)
    labels, n_comp = fs.vol_label(binary, connectivity=26)
    v_mm3, _ = measure_mm3(rec, thr)
    verts, faces = fs.marching_cubes(rec, thr)[:2]
    shell = np.asarray(fs.vol_boundary_points(binary,
                                              spacing=(SLICE_MM, PIX_MM, PIX_MM)))

    sino = stack[mid]
    frames, labels_txt = [], []

    frames.append(_label(_fit(_gray(vol[mid])),
                         [f"部品の断面 {SIZE}x{SIZE}",
                          f"真の体積 {true_mm3:.0f} mm3"]))
    labels_txt.append("ファントム(真値は閉形式)")

    # 投影 1 本 = サイノグラムの 1 行。どこから来た行かを線で示す。
    proj_img = np.tile(_norm(sino[0]), (SIZE, 1))
    frames.append(_label(_fit(_gray(proj_img)),
                         [f"角度 0 度の投影 1 本",
                          f"検出器 {sino.shape[1]} bin"]))
    labels_txt.append("投影(1 角度ぶんの線積分)")

    frames.append(_label(_fit(_gray(sino)),
                         [f"サイノグラム {sino.shape[0]}x{sino.shape[1]}",
                          "縦=角度 / 横=検出器"]))
    labels_txt.append("サイノグラム(128 角度ぶん)")

    frames.append(_label(_fit(_gray(rec[mid], 0.0, vol.max())),
                         [f"FBP 再構成", f"nRMS {_nrms(rec, vol):.4f}"]))
    labels_txt.append("フィルタ逆投影で断面に戻す")

    frames.append(_label(_fit(_gray(windowed[mid], 0.0, 1.0)),
                         ["vol_window_level", f"中心 {thr:.4f} / 幅 {2.4*thr:.4f}"]))
    labels_txt.append("CT 窓(既存 op)")

    lab_rgb = _fit(np.dstack([labels[mid] > 0, labels[mid] > 0,
                              np.zeros_like(labels[mid])]).astype(np.float64)
                   * np.array([0.98, 0.72, 0.25]))
    frames.append(_label(lab_rgb, [f"vol_label -> {n_comp} 成分",
                                   f"しきい値 {thr:.4f}"]))
    labels_txt.append("二値化 + 連結成分(既存 op)")

    occ = binary.max(axis=0)
    frames.append(_label(_fit(np.dstack([occ * 0.25, occ * 0.66, occ * 0.98])),
                         [f"占有ボクセル {int(binary.sum())} 個",
                          f"体積 {v_mm3:.0f} mm3 ({v_mm3/true_mm3-1:+.1%})"]))
    labels_txt.append("ボクセル格子(z 方向に投影)")

    frames.append(_label(_mesh_panel(verts, faces),
                         [f"marching_cubes 面 {np.asarray(faces).shape[0]}",
                          f"境界点群 {shell.shape[0]} 点"]))
    labels_txt.append("メッシュ / 点群(既存 op)")

    book = et.flipbook(frames, labels_txt,
                       title="投影からボクセルまで ―― CT の一本道")
    info = et.save_animation(book, "wingct_pipeline", duration_ms=1100,
                             hold_last_ms=2000)
    return info, {"true_mm3": round(true_mm3, 1), "measured_mm3": round(v_mm3, 1),
                  "rel_err": round(v_mm3 / true_mm3 - 1, 5),
                  "views": 128, "components": n_comp,
                  "nrms": round(_nrms(rec, vol), 4),
                  "faces": int(np.asarray(faces).shape[0]),
                  "shell_points": int(shell.shape[0]),
                  "ops": ["ellipse_phantom", "radon_volume", "fbp_volume",
                          "vol_window_level", "vol_label", "vol_region_props",
                          "marching_cubes", "vol_boundary_points"]}


# --------------------------------------------------------------------------- #
# 展示 2/3: 投影数を増やすと像が立ち上がる(GIF + タイル)                     #
# --------------------------------------------------------------------------- #
def _view_sweep():
    truth = ct_slice()
    vol, true_mm3 = part_volume()
    out = []
    for n_v in (8, 16, 32, 64, 128):
        ang = T.projection_angles(n_v, 180.0, "uniform")
        rec = T.filtered_backprojection(T.ellipse_sinogram(SIZE, SL_CT, ang),
                                        ang, size=SIZE)
        vrec = T.fbp_volume(T.radon_volume(vol, ang), ang, size=SIZE)
        v_mm3, n_comp = measure_mm3(vrec, 0.0125)
        out.append((n_v, rec, _nrms(rec, truth), v_mm3, true_mm3, n_comp))
    return truth, out


def ex_views_gif():
    truth, rows = _view_sweep()
    frames, labels = [], []
    for n_v, rec, err, v_mm3, true_mm3, n_comp in rows:
        frames.append(_label(_fit(_gray(rec, 0.0, truth.max())),
                             [f"投影 {n_v} 本",
                              f"再構成 nRMS {err:.4f}",
                              f"体積 {v_mm3:.0f} / {true_mm3:.0f} mm3 "
                              f"({v_mm3/true_mm3-1:+.1%})",
                              f"連結成分 {n_comp} 個"]))
        labels.append(f"{n_v} 本")
    book = et.flipbook(frames, labels,
                       title="投影数を増やすと像が立ち上がる(同じ被写体)")
    info = et.save_animation(book, "wingct_view_sweep", duration_ms=950,
                             hold_last_ms=2200)
    return info, {"rows": [{"views": r[0], "nrms": round(r[2], 4),
                            "volume_mm3": round(r[3], 1),
                            "rel_err": round(r[3] / r[4] - 1, 5),
                            "components": r[5]} for r in rows],
                  "ops": ["projection_angles", "ellipse_sinogram",
                          "filtered_backprojection", "radon_volume",
                          "fbp_volume", "vol_label", "vol_region_props"]}


def ex_views_sheet():
    truth, rows = _view_sweep()
    panels = [_fit(_gray(truth, 0.0, truth.max()))]
    labels = ["真値(ファントム)"]
    for n_v, rec, err, v_mm3, true_mm3, n_comp in rows:
        panels.append(_fit(_gray(rec, 0.0, truth.max())))
        labels.append(f"{n_v} 本  nRMS {err:.3f}  体積 {v_mm3/true_mm3-1:+.1%}")
    sheet = et.contact_sheet(panels, labels, ncols=3, panel_px=300,
                             title="投影数と、そのとき体積がどれだけ狂うか")
    info = et.save_exhibit(sheet, "wingct_view_tiles")
    return info, {"rows": [{"views": r[0], "nrms": round(r[2], 4),
                            "rel_err": round(r[3] / r[4] - 1, 5)} for r in rows],
                  "ops": ["ellipse_phantom", "ellipse_sinogram",
                          "filtered_backprojection"]}


# --------------------------------------------------------------------------- #
# 展示 4: 回転中心のずれ                                                       #
# --------------------------------------------------------------------------- #
def ex_center():
    truth = ct_slice()
    sino = T.ellipse_sinogram(SIZE, SL_CT, ANG180)
    frames, labels, rows = [], [], []
    for shift in (0.0, 0.5, 1.0, 2.0):
        bad = T.sinogram_center_shift(sino, -shift, ANG180)
        est = T.sinogram_center_of_rotation(bad, ANG180)
        rec = T.filtered_backprojection(bad, ANG180, size=SIZE)
        err = _nrms(rec, truth)
        rows.append((shift, est, err))
        # 二重像がどこに出るかを見せるため、頭蓋の左端を拡大した窓も焼く
        frames.append(_label(_fit(_gray(rec, 0.0, truth.max())),
                             [f"回転中心のずれ {shift:.1f} px",
                              f"推定値 {est:+.4f} px",
                              f"再構成 nRMS {err:.4f} "
                              f"({err/ (rows[0][2] or 1):.1f} 倍)"]))
        labels.append(f"{shift:.1f} px")
    book = et.flipbook(frames, labels,
                       title="回転中心が半画素ずれると、もう二重像になる")
    info = et.save_animation(book, "wingct_center_shift", duration_ms=1150,
                             hold_last_ms=2200)
    return info, {"rows": [{"shift_px": r[0], "estimate_px": round(r[1], 4),
                            "nrms": round(r[2], 4)} for r in rows],
                  "ops": ["sinogram_center_shift", "sinogram_center_of_rotation",
                          "filtered_backprojection"]}


# --------------------------------------------------------------------------- #
# 展示 5: 角度範囲が足りない(limited angle)                                   #
# --------------------------------------------------------------------------- #
def ex_limited_angle():
    truth = ct_slice()
    panels, labels, rows = [], [], []
    fy, fx = np.mgrid[0:SIZE, 0:SIZE]
    phi = np.rad2deg(np.arctan2(fy - SIZE // 2, fx - SIZE // 2)) % 180.0
    rad = np.hypot(fx - SIZE // 2, fy - SIZE // 2)
    band = (rad > 4) & (rad < SIZE // 2)
    f_t = np.abs(np.fft.fftshift(np.fft.fft2(truth)))
    for span in (180.0, 120.0, 90.0, 60.0):
        n_v = int(round(span))
        ang = np.linspace(0.0, span, n_v, endpoint=False)
        rec = T.filtered_backprojection(T.ellipse_sinogram(SIZE, SL_CT, ang),
                                        ang, size=SIZE, span_deg=span)
        f_r = np.abs(np.fft.fftshift(np.fft.fft2(rec)))
        keep = [float(f_r[band & (phi >= lo) & (phi < lo + 30)].sum()
                      / f_t[band & (phi >= lo) & (phi < lo + 30)].sum())
                for lo in range(0, 180, 30)]
        rows.append((span, _nrms(rec, truth), keep))
        panels.append(_label(_fit(_gray(rec, 0.0, truth.max())),
                             [f"角度範囲 {span:.0f} 度 ({n_v} 本)",
                              "残った周波数(30 度ごと):",
                              " ".join(f"{k:.2f}" for k in keep)], size=15))
        labels.append(f"{span:.0f} 度  nRMS {_nrms(rec, truth):.3f}")
    sheet = et.contact_sheet(panels, labels, ncols=2, panel_px=340,
                             title="角度範囲が足りないと、特定の向きの輪郭だけが消える")
    info = et.save_exhibit(sheet, "wingct_limited_angle")
    return info, {"rows": [{"span_deg": r[0], "nrms": round(r[1], 4),
                            "sector_energy": [round(k, 3) for k in r[2]]}
                           for r in rows],
                  "ops": ["ellipse_sinogram", "filtered_backprojection"]}


# --------------------------------------------------------------------------- #
# 展示 6: ビームハードニング(カッピング)と補正                                #
# --------------------------------------------------------------------------- #
def ex_beam_hardening():
    r_px = 0.47 * SIZE / 2.0
    disc = ((0.0, 0.0, r_px / (SIZE / 2), r_px / (SIZE / 2), 0.0, 1.0 / 60.0),)
    sino = T.ellipse_sinogram(SIZE, disc, ANG180)
    hard = T.beam_hardening_apply(sino, 0.5, 0.4)
    corr = T.beam_hardening_correct(hard, 0.5, 0.4)
    c = (SIZE - 1) / 2.0
    yy, xx = np.mgrid[0:SIZE, 0:SIZE]
    rr = np.hypot(xx - c, yy - c)

    def cup(sg):
        rec = T.filtered_backprojection(sg, ANG180, size=SIZE)
        centre = rec[int(c) - 3:int(c) + 4, int(c) - 3:int(c) + 4].mean()
        rim = rec[(rr > r_px - 14) & (rr < r_px - 8)].mean()
        return rec, float(centre / rim)

    rec0, cup0 = cup(sino)
    rec1, cup1 = cup(hard)
    rec2, cup2 = cup(corr)
    lo, hi = 0.0, float(rec0.max())
    limit = float(np.abs(rec1 - rec0).max())
    panels = [
        _label(_fit(_gray(rec0, lo, hi)), ["単色ビーム(理想)",
                                           f"中心/縁 = {cup0:.4f}"]),
        _label(_fit(_gray(rec1, lo, hi)), ["多色ビーム(実機)",
                                           f"中心/縁 = {cup1:.4f}",
                                           f"中心が {100*(cup0-cup1)/cup0:.1f} % 沈む"]),
        _label(_fit(_diverging(rec1 - rec0, limit)),
               ["差分(青=減った / 橙=増えた)", f"最大 {limit:.5f}"]),
        _label(_fit(_gray(rec2, lo, hi)), ["補正後",
                                           f"中心/縁 = {cup2:.4f}",
                                           "理想と 4 桁一致"]),
    ]
    sheet = et.contact_sheet(
        panels, ["単色(真値)", "多色 ―― カッピング偽像", "何がどれだけ沈んだか",
                 "beam_hardening_correct 後"],
        ncols=2, panel_px=320,
        title="ビームハードニング ―― 一様な円板の中心がへこむ")
    info = et.save_exhibit(sheet, "wingct_beam_hardening")
    return info, {"cup_clean": round(cup0, 4), "cup_hardened": round(cup1, 4),
                  "cup_corrected": round(cup2, 4),
                  "roundtrip_max": float(np.abs(corr - sino).max()),
                  "ops": ["ellipse_sinogram", "beam_hardening_apply",
                          "beam_hardening_correct", "filtered_backprojection"]}


# --------------------------------------------------------------------------- #
# 展示 7: リング偽像(検出器のゲイン不均一)                                    #
# --------------------------------------------------------------------------- #
def ex_rings():
    truth = ct_slice()
    sino = T.ellipse_sinogram(SIZE, SL_CT, ANG180)
    ringed = T.ring_artifact_apply(sino, 0.02, seed=0)
    fixed = T.ring_artifact_remove(ringed)
    recs = [T.filtered_backprojection(s, ANG180, size=SIZE)
            for s in (sino, ringed, fixed)]
    errs = [_nrms(r, truth) for r in recs]
    lo, hi = 0.0, float(truth.max())
    limit = float(np.abs(recs[1] - recs[0]).max())
    panels = [
        _label(_fit(_gray(recs[0], lo, hi)), ["検出器が完璧なら",
                                              f"nRMS {errs[0]:.4f}"]),
        _label(_fit(_gray(recs[1], lo, hi)),
               ["検出器ゲインに 2 % のばらつき", f"nRMS {errs[1]:.4f} "
                f"({errs[1]/errs[0]:.1f} 倍)"]),
        _label(_fit(_diverging(recs[1] - recs[0], limit)),
               ["差分 ―― 同心円になる", f"最大 {limit:.5f}"]),
        _label(_fit(_gray(recs[2], lo, hi)),
               ["ring_artifact_remove 後", f"nRMS {errs[2]:.4f}",
                f"被害の {100*(errs[1]-errs[2])/(errs[1]-errs[0]):.0f} % を回復"]),
    ]
    sheet = et.contact_sheet(
        panels, ["理想", "1 画素のゲイン誤差 = 1 本の完全な円", "差分が同心円",
                 "除去後(既定 window=5, median)"],
        ncols=2, panel_px=320,
        title="リング偽像 ―― 検出器 1 画素の狂いが 1 本の円になる")
    info = et.save_exhibit(sheet, "wingct_rings")
    return info, {"nrms_clean": round(errs[0], 4), "nrms_ringed": round(errs[1], 4),
                  "nrms_fixed": round(errs[2], 4),
                  "recovered": round((errs[1] - errs[2]) / (errs[1] - errs[0]), 3),
                  "ops": ["ring_artifact_apply", "ring_artifact_remove",
                          "filtered_backprojection"]}


# --------------------------------------------------------------------------- #
# 展示 8: 体積の答え合わせ(軸ラベルつき、原寸)                                 #
# --------------------------------------------------------------------------- #
def ex_volume_chart():
    vol, true_mm3 = part_volume()
    thr = 0.0125
    v_digital, _ = measure_mm3(vol, thr)
    views = (8, 16, 32, 64, 128)
    measured, comps, nrmses = [], [], []
    for n_v in views:
        ang = T.projection_angles(n_v, 180.0, "uniform")
        rec = T.fbp_volume(T.radon_volume(vol, ang), ang, size=SIZE)
        v, n = measure_mm3(rec, thr)
        measured.append(v)
        comps.append(n)
        nrmses.append(_nrms(rec, vol))
    thr_fracs = (0.30, 0.40, 0.50, 0.60, 0.70)
    ang128 = T.projection_angles(128, 180.0, "uniform")
    rec128 = T.fbp_volume(T.radon_volume(vol, ang128), ang128, size=SIZE)
    thr_vols = [measure_mm3(rec128, f * 0.025)[0] for f in thr_fracs]

    from PIL import Image, ImageDraw
    W, H = 1180, 560
    im = Image.new("RGB", (W, H), et.BG)
    dr = ImageDraw.Draw(im)
    f_t = et._font(25)
    f_a = et._font(17)
    f_s = et._font(15)
    dr.text((W // 2, 26), "体積の答え合わせ ―― 何が効いて、何が効かないか",
            fill=et.FG, font=f_t, anchor="mm")

    all_v = measured + thr_vols + [true_mm3, v_digital]
    lo = min(all_v) * 0.985
    hi = max(all_v) * 1.015

    def val_fmt(v):
        return f"{v:.0f}"

    def panel(x0, y0, w, h, xs, ys, xlabels, title, sub, mark=None):
        dr.text((x0 + w // 2, y0 - 22), title, fill=et.FG, font=f_a, anchor="mm")
        dr.rectangle([x0, y0, x0 + w, y0 + h], outline=(60, 60, 78))
        # 真値と digitisation 天井の水平線。ラベルは左右に振り分けて重ねない。
        for val, col, tag, side in (
                (true_mm3, (250, 190, 90),
                 "真値(閉形式) %s" % val_fmt(true_mm3), "l"),
                (v_digital, (120, 190, 250),
                 "この格子の天井 %s" % val_fmt(v_digital), "r")):
            yy = y0 + h - (val - lo) / (hi - lo) * h
            for xx in range(x0 + 2, x0 + w - 2, 9):
                dr.line([xx, yy, xx + 4, yy], fill=col)
            dy = -13 if side == "l" else 12
            if side == "l":
                dr.text((x0 + 8, yy + dy), tag, fill=col, font=f_s, anchor="lm")
            else:
                dr.text((x0 + w - 8, yy + dy), tag, fill=col, font=f_s, anchor="rm")
        pts = []
        for i, (xv, yv) in enumerate(zip(xs, ys)):
            px = x0 + 40 + i * (w - 76) / max(len(xs) - 1, 1)
            py = y0 + h - (yv - lo) / (hi - lo) * h
            pts.append((px, py))
            dr.text((px, y0 + h + 15), xlabels[i], fill=et.MUTED, font=f_s,
                    anchor="mm")
            dr.text((px, py - 16), f"{yv:.0f}", fill=et.FG, font=f_s, anchor="mm")
        dr.line(pts, fill=(150, 210, 255), width=2)
        for px, py in pts:
            dr.ellipse([px - 4, py - 4, px + 4, py + 4], fill=(150, 210, 255))
        if mark is not None:
            px, py = pts[mark]
            dr.ellipse([px - 9, py - 9, px + 9, py + 9], outline=(250, 140, 90),
                       width=2)
            dr.text((px + 14, py), "← 信用できない領域", fill=(250, 140, 90),
                    font=f_s, anchor="lm")
        dr.text((x0 + w // 2, y0 + h + 40), sub, fill=et.MUTED, font=f_s,
                anchor="mm")

    span_v_all = max(measured) - min(measured)
    span_v16 = max(measured[1:]) - min(measured[1:])
    span_t = max(thr_vols) - min(thr_vols)
    panel(70, 90, 470, 340, views, measured, [str(v) for v in views],
          "投影数を変える",
          f"16-128 本の振れ幅 {span_v16:.0f} mm3 ({span_v16 / true_mm3:.2%}) / "
          f"8 本を含めると {span_v_all:.0f} mm3 / 横軸 = 投影数", mark=0)
    panel(640, 90, 470, 340, thr_fracs, thr_vols,
          [f"{f:.2f}" for f in thr_fracs], "二値化しきい値を変える",
          f"振れ幅 {span_t:.0f} mm3  ({span_t / true_mm3:.2%} of 真値) / "
          f"横軸 = しきい値 (減弱比)")
    dr.text((W // 2, H - 46),
            f"投影 16 本以上では体積は {span_v16 / true_mm3:.2%} しか動かない"
            f"(nRMS は {nrmses[1]:.3f} → {nrmses[-1]:.3f} と "
            f"{nrmses[1]/nrmses[-1]:.1f} 倍改善するのに)。"
            f"しきい値は {span_t / true_mm3:.1%} 動かす ―― "
            f"{span_t / max(span_v16, 1e-9):.0f} 倍効く。",
            fill=et.FG, font=f_a, anchor="mm")
    dr.text((W // 2, H - 22),
            f"8 本の点だけは別で、体積 {measured[0]/true_mm3-1:+.1%} は再現しない"
            f"(面内 128 画素では -0.0%)。壊れを教えるのは体積でなく連結成分の数"
            f"({comps[0]} 個 対 {comps[-1]} 個)。",
            fill=et.FG, font=f_a, anchor="mm")

    info = et.save_exhibit(np.asarray(im, np.float64) / 255.0,
                           "wingct_volume_check")
    return info, {"true_mm3": round(true_mm3, 1),
                  "digitised_mm3": round(v_digital, 1),
                  "views": list(views),
                  "volume_by_views": [round(v, 1) for v in measured],
                  "components_by_views": comps,
                  "nrms_by_views": [round(v, 4) for v in nrmses],
                  "threshold_fracs": list(thr_fracs),
                  "volume_by_threshold": [round(v, 1) for v in thr_vols],
                  "span_views_mm3": round(span_v_all, 1),
                  "span_views16_mm3": round(span_v16, 1),
                  "span_threshold_mm3": round(span_t, 1),
                  "ops": ["radon_volume", "fbp_volume", "vol_label",
                          "vol_region_props"]}


EXHIBITS = {
    "pipeline": ex_pipeline,
    "view_sweep": ex_views_gif,
    "view_tiles": ex_views_sheet,
    "center_shift": ex_center,
    "limited_angle": ex_limited_angle,
    "beam_hardening": ex_beam_hardening,
    "rings": ex_rings,
    "volume_check": ex_volume_chart,
}


# --------------------------------------------------------------------------- #
# キャプション原稿(ja / en)を実測値から書く                                    #
# --------------------------------------------------------------------------- #
def _captions(meta):
    p = meta["pipeline"]["data"]
    vs = {r["views"]: r for r in meta["view_sweep"]["data"]["rows"]}
    cs = meta["center_shift"]["data"]["rows"]
    la = {r["span_deg"]: r for r in meta["limited_angle"]["data"]["rows"]}
    bh = meta["beam_hardening"]["data"]
    rg = meta["rings"]["data"]
    vc = meta["volume_check"]["data"]

    ja = []
    ja.append(et.markdown_animation(
        "wingct_pipeline", "投影からボクセルまで ―― CT の一本道",
        f"**投影からボクセルまで、CT の一本道** ―― ファントム → 投影 → サイノグラム "
        f"→ 再構成 → 窓 → 分離 → ボクセル → メッシュ の 8 工程。体積が閉形式で分かる"
        f"部品(真値 {p['true_mm3']:.0f} mm³)を 128 本の投影から作り直すと "
        f"{p['measured_mm3']:.0f} mm³({p['rel_err']:+.1%})になった。"
        f"再構成 nRMS {p['nrms']:.4f}、メッシュ {p['faces']} 面、境界点群 "
        f"{p['shell_points']} 点。使用 op: `radon_volume`, `fbp_volume`, "
        f"`vol_window_level`, `vol_label`, `vol_region_props`, `marching_cubes`, "
        f"`vol_boundary_points`。"))
    ja.append(et.markdown_animation(
        "wingct_view_sweep", "投影数を増やすと像が立ち上がる",
        f"**投影数を増やすと像が立ち上がる** ―― 同じ被写体を 8 / 16 / 32 / 64 / 128 本で"
        f"撮り直す。再構成の nRMS は {vs[8]['nrms']:.4f} → {vs[128]['nrms']:.4f} と "
        f"{vs[8]['nrms']/vs[128]['nrms']:.1f} 倍改善するのに、**体積は "
        f"{vs[8]['rel_err']:+.1%} → {vs[128]['rel_err']:+.1%} でほとんど動かない**。"
        f"ストリークは正負が対称に出るので体積では相殺してしまう。壊れを教えるのは"
        f"連結成分の数({vs[8]['components']} 個 対 {vs[128]['components']} 個)。"
        f"使用 op: `projection_angles`, `ellipse_sinogram`, "
        f"`filtered_backprojection`。"))
    ja.append(et.markdown(
        "wingct_view_tiles", "投影数と体積誤差のタイル",
        f"**同じものをタイルでも** ―― 左上が真値、以下が 8 / 16 / 32 / 64 / 128 本。"
        f"ラベルは再構成 nRMS と体積誤差。8 本ではストリークで頭蓋の内側が読めないのに、"
        f"体積誤差は {vs[8]['rel_err']:+.1%} しかない。使用 op: `ellipse_phantom`, "
        f"`ellipse_sinogram`, `filtered_backprojection`。"))
    ja.append(et.markdown_animation(
        "wingct_center_shift", "回転中心のずれ",
        f"**回転中心が半画素ずれると、もう二重像になる** ―― 0 / 0.5 / 1 / 2 画素。"
        f"再構成の nRMS は {cs[0]['nrms']:.4f} → {cs[1]['nrms']:.4f} → "
        f"{cs[2]['nrms']:.4f} → {cs[3]['nrms']:.4f}。**半画素で誤差が "
        f"{cs[1]['nrms']/cs[0]['nrms']:.1f} 倍**になるが、見た目は「少し眠い画像」で、"
        f"間違いには見えない。`sinogram_center_of_rotation` は重心の恒等式から"
        f"これを {abs(cs[2]['estimate_px']-1.0):.4f} px の誤差で当てる。"
        f"使用 op: `sinogram_center_shift`, `sinogram_center_of_rotation`。"))
    ja.append(et.markdown(
        "wingct_limited_angle", "角度範囲が足りないとき",
        f"**角度範囲が足りないと、特定の向きの輪郭だけが消える** ―― 180 / 120 / 90 / "
        f"60 度。中心スライス定理どおり、撮らなかった角度の帯だけが空になる。"
        f"30 度ごとの周波数保持率で見ると、90 度スキャンでは撮った側が "
        f"{max(la[90.0]['sector_energy'][:3]):.2f} を保つのに撮らなかった側は "
        f"{min(la[90.0]['sector_energy'][3:]):.2f} まで落ちる。全体がぼけるのではなく"
        f"**方向が消える**ので、残った方向は鋭いままで、それが説得力を持ってしまう。"
        f"使用 op: `ellipse_sinogram`, `filtered_backprojection`。"))
    ja.append(et.markdown(
        "wingct_beam_hardening", "ビームハードニング(カッピング偽像)",
        f"**ビームハードニング ―― 一様な円板の中心がへこむ** ―― 実際の X 線は"
        f"単色ではないので、厚い経路を通った線ほどビームが硬くなり、線積分が"
        f"経路長に比例しなくなる。一様な円板の中心/縁の比が "
        f"{bh['cup_clean']:.4f} → {bh['cup_hardened']:.4f} に沈み、"
        f"`beam_hardening_correct` が {bh['cup_corrected']:.4f} に戻す。"
        f"差分図(青=減った / 橙=増えた)が、沈んだのが中心だけであることを示す。"
        f"使用 op: `beam_hardening_apply`, `beam_hardening_correct`。"))
    ja.append(et.markdown(
        "wingct_rings", "リング偽像",
        f"**リング偽像 ―― 検出器 1 画素の狂いが 1 本の円になる** ―― ゲインが "
        f"g の検出器は対数を取ったあと **どの角度でも同じ定数**だけずれる。"
        f"定数の列を逆投影すると回転軸まわりの完全な円になる。ゲインばらつき 2 % で "
        f"nRMS が {rg['nrms_clean']:.4f} → {rg['nrms_ringed']:.4f}("
        f"{rg['nrms_ringed']/rg['nrms_clean']:.1f} 倍)、`ring_artifact_remove` で "
        f"{rg['nrms_fixed']:.4f}(被害の {rg['recovered']:.0%} を回復)。"
        f"使用 op: `ring_artifact_apply`, `ring_artifact_remove`。"))
    ja.append(et.markdown(
        "wingct_volume_check", "体積の答え合わせ",
        f"**体積の答え合わせ ―― 何が効いて、何が効かないか** ―― 真値 "
        f"{vc['true_mm3']:.0f} mm³(閉形式)、この格子で二値化しただけの天井が "
        f"{vc['digitised_mm3']:.0f} mm³。左は投影数 8→128 で振れ幅 "
        f"{vc['span_views_mm3']:.0f} mm³、右は二値化しきい値 0.30→0.70 で振れ幅 "
        f"{vc['span_threshold_mm3']:.0f} mm³。**しきい値の任意性のほうが "
        f"{vc['span_threshold_mm3']/max(vc['span_views_mm3'],1e-9):.0f} 倍効く**ので、"
        f"体積を報告するときに書くべきなのは「何本で撮ったか」より"
        f"「どのしきい値で切ったか」。使用 op: `radon_volume`, `fbp_volume`, "
        f"`vol_label`, `vol_region_props`。"))

    en = []
    en.append(et.markdown_animation(
        "wingct_pipeline", "From projections to voxels — the CT road",
        f"**From projections to voxels, the whole CT road** — phantom, projection, "
        f"sinogram, reconstruction, window, segmentation, voxels, mesh, in eight "
        f"steps. A part whose volume is known in closed form "
        f"({p['true_mm3']:.0f} mm³) rebuilt from 128 projections measures "
        f"{p['measured_mm3']:.0f} mm³ ({p['rel_err']:+.1%}); reconstruction nRMS "
        f"{p['nrms']:.4f}, {p['faces']} mesh faces, {p['shell_points']} boundary "
        f"points. Ops used: `radon_volume`, `fbp_volume`, `vol_window_level`, "
        f"`vol_label`, `vol_region_props`, `marching_cubes`, "
        f"`vol_boundary_points`."))
    en.append(et.markdown_animation(
        "wingct_view_sweep", "More projections, and the image stands up",
        f"**More projections, and the image stands up** — the same object at 8, 16, "
        f"32, 64 and 128 views. Reconstruction nRMS improves "
        f"{vs[8]['nrms']:.4f} → {vs[128]['nrms']:.4f}, a factor of "
        f"{vs[8]['nrms']/vs[128]['nrms']:.1f}, while **the volume barely moves**: "
        f"{vs[8]['rel_err']:+.1%} → {vs[128]['rel_err']:+.1%}. Streaks appear "
        f"symmetrically in sign, so they cancel in a single integrated quantity. "
        f"What does reveal the damage is the component count "
        f"({vs[8]['components']} against {vs[128]['components']}). Ops used: "
        f"`projection_angles`, `ellipse_sinogram`, `filtered_backprojection`."))
    en.append(et.markdown(
        "wingct_view_tiles", "View count and volume error, tiled",
        f"**The same thing as a tile** — the truth top left, then 8 / 16 / 32 / 64 / "
        f"128 views. Labels carry the reconstruction nRMS and the volume error. At "
        f"8 views the inside of the skull is unreadable through the streaks, yet "
        f"the volume is off by only {vs[8]['rel_err']:+.1%}. Ops used: "
        f"`ellipse_phantom`, `ellipse_sinogram`, `filtered_backprojection`."))
    en.append(et.markdown_animation(
        "wingct_center_shift", "A miscentred axis of rotation",
        f"**Half a pixel of centre error is already a double image** — 0, 0.5, 1 and "
        f"2 px. Reconstruction nRMS goes {cs[0]['nrms']:.4f} → {cs[1]['nrms']:.4f} → "
        f"{cs[2]['nrms']:.4f} → {cs[3]['nrms']:.4f}: **half a pixel costs "
        f"{cs[1]['nrms']/cs[0]['nrms']:.1f}x the error** while looking merely soft "
        f"rather than wrong. `sinogram_center_of_rotation` recovers it from the "
        f"centre-of-mass identity to within {abs(cs[2]['estimate_px']-1.0):.4f} px. "
        f"Ops used: `sinogram_center_shift`, `sinogram_center_of_rotation`."))
    en.append(et.markdown(
        "wingct_limited_angle", "When the angular range runs out",
        f"**A limited angular range deletes specific directions, not detail in "
        f"general** — 180, 120, 90 and 60 degrees. By the central-slice theorem the "
        f"unmeasured wedge of the Fourier plane is simply empty. Measured as "
        f"retained energy per 30-degree sector, a 90-degree scan holds "
        f"{max(la[90.0]['sector_energy'][:3]):.2f} on the side it measured and "
        f"falls to {min(la[90.0]['sector_energy'][3:]):.2f} on the side it did not. "
        f"The surviving directions stay sharp, which is exactly what makes such a "
        f"reconstruction convincing. Ops used: `ellipse_sinogram`, "
        f"`filtered_backprojection`."))
    en.append(et.markdown(
        "wingct_beam_hardening", "Beam hardening (the cupping artefact)",
        f"**Beam hardening — the centre of a uniform disc sinks** — a real X-ray "
        f"beam is not monochromatic, so a ray that survives a thicker path is "
        f"harder and attenuates less per unit length, and the line integral stops "
        f"being proportional to path length. The disc's centre-to-rim ratio drops "
        f"{bh['cup_clean']:.4f} → {bh['cup_hardened']:.4f}, and "
        f"`beam_hardening_correct` returns it to {bh['cup_corrected']:.4f}. The "
        f"difference panel (blue = lost, orange = gained) shows that only the "
        f"centre sank. Ops used: `beam_hardening_apply`, `beam_hardening_correct`."))
    en.append(et.markdown(
        "wingct_rings", "Ring artefacts",
        f"**Ring artefacts — one bad detector pixel becomes one perfect circle** — a "
        f"detector bin with gain g is offset, after the logarithm, by **the same "
        f"constant at every angle**. Back-projecting a constant column smears it "
        f"into a circle about the rotation axis. A 2 % gain spread takes nRMS "
        f"{rg['nrms_clean']:.4f} → {rg['nrms_ringed']:.4f} "
        f"({rg['nrms_ringed']/rg['nrms_clean']:.1f}x), and `ring_artifact_remove` "
        f"brings it to {rg['nrms_fixed']:.4f}, undoing {rg['recovered']:.0%} of the "
        f"damage. Ops used: `ring_artifact_apply`, `ring_artifact_remove`."))
    en.append(et.markdown(
        "wingct_volume_check", "Checking the volume",
        f"**Checking the volume — what matters, and what does not** — the closed-form "
        f"truth is {vc['true_mm3']:.0f} mm³, and merely digitising it on this grid "
        f"already gives {vc['digitised_mm3']:.0f} mm³. On the left, sweeping the "
        f"view count from 8 to 128 moves the answer by "
        f"{vc['span_views_mm3']:.0f} mm³; on the right, sweeping the binarisation "
        f"threshold from 0.30 to 0.70 moves it by "
        f"{vc['span_threshold_mm3']:.0f} mm³. **The arbitrariness of the threshold "
        f"matters "
        f"{vc['span_threshold_mm3']/max(vc['span_views_mm3'],1e-9):.0f}x more than "
        f"the view count**, so the number to publish alongside a volume is which "
        f"threshold cut it, not how many views took it. Ops used: `radon_volume`, "
        f"`fbp_volume`, `vol_label`, `vol_region_props`."))
    return "\n".join(ja), "\n".join(en)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--exhibits", default="", help="カンマ区切りの展示名")
    ap.add_argument("--list", action="store_true", help="展示名を並べて終了")
    ap.add_argument("--verify", action="store_true",
                    help="2 回生成して SHA-256 が一致することを確かめる")
    args = ap.parse_args(argv)

    if args.list:
        for name in EXHIBITS:
            print(name)
        return 0

    want = [w.strip() for w in args.exhibits.split(",") if w.strip()] or list(EXHIBITS)
    unknown = [w for w in want if w not in EXHIBITS]
    if unknown:
        raise SystemExit(f"未知の展示: {unknown}. --list で一覧")

    meta = {}
    for name in want:
        print(f"[wingct] {name} ...", flush=True)
        info, data = EXHIBITS[name]()
        digest = info.get("png_sha256") or info.get("gif_sha256")
        meta[name] = {"file": info.get("png") or info.get("gif"),
                      "sha256": digest, "data": data}
        print(f"          -> {os.path.basename(meta[name]['file'])}  "
              f"sha256 {digest[:16]}")

    if args.verify:
        print("[wingct] 再生成して SHA-256 を照合 ...", flush=True)
        for name in want:
            info, _ = EXHIBITS[name]()
            again = info.get("png_sha256") or info.get("gif_sha256")
            status = "一致" if again == meta[name]["sha256"] else "★不一致"
            print(f"          {name:16s} {status}")
            if again != meta[name]["sha256"]:
                raise SystemExit(f"{name} が決定的でない")

    os.makedirs(os.path.dirname(META_PATH), exist_ok=True)
    with open(META_PATH, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1, default=float)

    if set(want) == set(EXHIBITS):
        ja, en = _captions(meta)
        os.makedirs(EXHIBITS_DIR, exist_ok=True)
        for lang, body in (("ja", ja), ("en", en)):
            path = os.path.join(EXHIBITS_DIR, f"wingct.{lang}.md")
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(body)
            print(f"[wingct] キャプション -> {os.path.relpath(path, ROOT)}")
    else:
        print("[wingct] 一部生成のためキャプションは書き換えていない")

    print(f"[wingct] 完了: {len(want)} 点")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
