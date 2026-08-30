# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gen_industrial_gallery — Qiita 記事用「工業用途 + Physical AI」画像の生成.
Generate industrial-inspection + Physical-AI gallery images for the Qiita article.

目的(かみくだき) / Purpose:
  fullseye が **産業画像処理(HALCON 系譜)と Physical AI の両方で実際に使える**
  ことを、登録 op / facade API を実行して示す素材を作る。モックアップ禁止
  (honest disclosure 規律)。各素材の使用 op・データ来歴(合成/シミュレーション)
  を JSON に記録し、記事貼付け用スニペットを自動生成する。検出結果は既知の
  真値(配置数・描画寸法・配置姿勢)と突き合わせて検算してから納品する。

生成物 / Outputs (docs/articles/assets/):
  industrial_*.png / phai_*.png        -- フルサイズ画像
  *_thumb.jpg                          -- 幅 720px サムネ (JPEG q85)
  media/phai_bin_pick.mp4              -- bin picking 実機シーケンス (H.264)
  _industrial_gallery_meta.json        -- 使用 op・キャプション・来歴のメタ
  _industrial_snippet.md               -- 記事挿入候補 (raw GitHub URL)
                                          (GALLERY.md / 記事 md 本体は編集しない)

Run:
  py -3.11 tools/gen_industrial_gallery.py                       # 全 subject
  py -3.11 tools/gen_industrial_gallery.py --subjects defect_metal,metrology
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import fullseye as fs  # noqa: E402

ASSETS_DIR = os.path.join(REPO, "docs", "articles", "assets")
MEDIA_DIR = os.path.join(ASSETS_DIR, "media")
META_PATH = os.path.join(ASSETS_DIR, "_industrial_gallery_meta.json")
SNIPPET_PATH = os.path.join(ASSETS_DIR, "_industrial_snippet.md")
RAW_BASE = ("https://raw.githubusercontent.com/furuse-kazufumi/fullseye/"
            "master/docs/articles/assets/")

SEED = 20260830
THUMB_WIDTH = 720
FONT_PATH = r"C:\Windows\Fonts\meiryo.ttc"


# --------------------------------------------------------------------------- #
# 共通ヘルパ / shared helpers                                                   #
# --------------------------------------------------------------------------- #
def _to_u8(rgb: np.ndarray) -> np.ndarray:
    return np.clip(np.asarray(rgb) * 255.0 + 0.5, 0, 255).astype(np.uint8)


def _save_png(rgb: np.ndarray, filename: str) -> str:
    from PIL import Image
    path = os.path.join(ASSETS_DIR, filename)
    arr = _to_u8(rgb)
    if arr.ndim == 2:
        arr = np.stack([arr] * 3, axis=-1)
    Image.fromarray(arr, "RGB").save(path)
    return path


def _save_thumb(filename: str) -> None:
    """フル PNG から幅 720px の JPEG q85 サムネを同ディレクトリに作る."""
    from PIL import Image
    src = os.path.join(ASSETS_DIR, filename)
    stem = os.path.splitext(filename)[0]
    dst = os.path.join(ASSETS_DIR, stem + "_thumb.jpg")
    with Image.open(src) as im:
        im = im.convert("RGB")
        if im.width > THUMB_WIDTH:
            h = round(im.height * THUMB_WIDTH / im.width)
            im = im.resize((THUMB_WIDTH, h), Image.LANCZOS)
        im.save(dst, format="JPEG", quality=85, optimize=True)


def _font(size: int):
    from PIL import ImageFont
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        return ImageFont.load_default()


def _montage(panels: list, labels: list | None = None, ncols: int = 3,
             pad: int = 10, bg=(14, 15, 22), label_h: int = 34,
             font_size: int = 20) -> np.ndarray:
    """パネル (HxWx3 float [0,1]) をグリッドに並べ、下にラベル帯を付ける."""
    from PIL import Image, ImageDraw
    imgs = []
    for p in panels:
        a = _to_u8(p)
        if a.ndim == 2:
            a = np.stack([a] * 3, axis=-1)
        imgs.append(Image.fromarray(a, "RGB"))
    n = len(imgs)
    ncols = min(ncols, n)
    nrows = (n + ncols - 1) // ncols
    cw = max(im.width for im in imgs)
    ch = max(im.height for im in imgs)
    lh = label_h if labels else 0
    W = ncols * cw + (ncols + 1) * pad
    H = nrows * (ch + lh) + (nrows + 1) * pad
    canvas = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(canvas)
    font = _font(font_size)
    for i, im in enumerate(imgs):
        r, c = divmod(i, ncols)
        x = pad + c * (cw + pad) + (cw - im.width) // 2
        y = pad + r * (ch + lh + pad)
        canvas.paste(im, (x, y))
        if labels and i < len(labels) and labels[i]:
            tx = pad + c * (cw + pad) + cw // 2
            ty = y + ch + lh // 2
            draw.text((tx, ty), labels[i], fill=(235, 235, 240),
                      font=font, anchor="mm")
    return np.asarray(canvas, np.float64) / 255.0


def _pil_of(gray_or_rgb: np.ndarray):
    from PIL import Image
    a = _to_u8(gray_or_rgb)
    if a.ndim == 2:
        a = np.stack([a] * 3, axis=-1)
    return Image.fromarray(a, "RGB")


def _np_of(pil_img) -> np.ndarray:
    return np.asarray(pil_img, np.float64) / 255.0


def _blur(img: np.ndarray, sigma: float) -> np.ndarray:
    from scipy.ndimage import gaussian_filter
    return gaussian_filter(np.asarray(img, np.float64), sigma)


# --------------------------------------------------------------------------- #
# 工業 1: 欠陥検出 / surface defect detection                                    #
# --------------------------------------------------------------------------- #
def _synth_brushed_metal(rng, H=520, W=720):
    """ヘアライン仕上げ金属面(合成)。横方向に流れる筋 + ゆるい照明ムラ."""
    streaks = _blur(rng.standard_normal((H, W)), (0.6, 14.0))
    streaks = streaks / (np.abs(streaks).max() + 1e-9)
    yy, xx = np.mgrid[0:H, 0:W]
    shade = 0.04 * np.cos((xx / W - 0.4) * 2.2) * np.cos((yy / H - 0.5) * 1.8)
    return np.clip(0.56 + 0.055 * streaks + shade, 0.0, 1.0)


def subject_defect_metal(log=print) -> dict:
    """欠陥検出 — 合成金属面の傷/打痕/異物を median 差分 + blob で検出し枠を描く."""
    from PIL import ImageDraw
    rng = np.random.default_rng(SEED)
    img = _synth_brushed_metal(rng)
    H, W = img.shape

    # 既知の欠陥 6 件を描き込む(真値): 傷 3 / 打痕 2 / 異物(明) 1
    truth = []
    pil = _pil_of(img)
    draw = ImageDraw.Draw(pil)
    scratches = [((120, 90), (240, 150)), ((430, 380), (560, 330)),
                 ((580, 120), (660, 190))]
    for (x0, y0), (x1, y1) in scratches:
        draw.line([(x0, y0), (x1, y1)], fill=(70, 70, 74), width=2)
        truth.append(("scratch", ((x0 + x1) / 2, (y0 + y1) / 2)))
    img = np.asarray(pil, np.float64)[..., 0] / 255.0
    for (cx, cy, r, dv) in [(210, 400, 2.4, -0.34), (520, 240, 2.8, -0.32)]:
        yy, xx = np.mgrid[0:H, 0:W]
        blob = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * r * r)))
        img = img + dv * blob
        truth.append(("dent", (cx, cy)))
    cx, cy, r = 330, 130, 2.2
    yy, xx = np.mgrid[0:H, 0:W]
    img = img + 0.30 * np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * r * r)))
    truth.append(("particle", (cx, cy)))
    img = np.clip(_blur(img, 0.7), 0.0, 1.0)

    # 検出: median_image で背景(地合い)を推定 → 差分 → しきい値 → blob 解析
    bg = fs.apply(img, "median_image", 1.0, 0.5)          # a=1.0 → 最大カーネル
    diff = np.abs(img - bg)
    seg = (diff > 0.055).astype(np.float64)
    seg = fs.apply(seg, "dilation_circle", 0.05, 0.5)     # 断片化した傷を繋ぐ
    objs = fs.segment_objects(seg, threshold="none", min_area=25)
    log(f"  defects known={len(truth)} detected={len(objs)}")
    if len(objs) != len(truth):
        raise RuntimeError(f"defect count mismatch: {len(objs)} != {len(truth)}")

    # オーバーレイ: 欠陥ごとに枠 + 面積スコア
    vis = _pil_of(img)
    d2 = ImageDraw.Draw(vis)
    font = _font(16)
    for i, o in enumerate(objs):
        y0, x0, y1, x1 = o["bbox"]
        m = 6
        d2.rectangle([x0 - m, y0 - m, x1 + m, y1 + m],
                     outline=(255, 90, 60), width=2)
        d2.text((x0 - m, max(2, y0 - m - 20)), f"NG{i + 1}  area={o['area']}px",
                fill=(255, 200, 80), font=font)
    panels = [np.stack([_synth_brushed_metal(np.random.default_rng(SEED))] * 3, -1),
              np.stack([np.clip(diff * 6.0, 0, 1)] * 3, -1), _np_of(vis)]
    out = _montage(panels, ["良品面 (合成ヘアライン金属)",
                            "median 背景差分 |img − median|",
                            f"欠陥 {len(objs)} 件検出 (枠 + 面積)"], ncols=3)
    _save_png(out, "industrial_defect.png")
    _save_thumb("industrial_defect.png")
    return {
        "file": "industrial_defect.png",
        "title": "表面欠陥検査 — 背景差分 + blob 解析",
        "ops": ["median_image", "dilation_circle", "segment_objects"],
        "data": "合成ヘアライン金属面 + 描き込み欠陥 6 件 (真値既知)",
        "synthetic": True,
        "caption": ("合成した金属面に入れた傷 3・打痕 2・異物 1 を、median フィルタで"
                    "地合いを推定して差分を取り、blob 解析で 6/6 件検出。"
                    "面積スコア付きで枠表示する定番の外観検査パイプライン。"),
        "verify": f"既知 6 欠陥に対し検出 {len(objs)} 件 (一致を assert 済)",
    }


# --------------------------------------------------------------------------- #
# 工業 2: 寸法計測 / metrology (1D measuring, sub-pixel calipers)                #
# --------------------------------------------------------------------------- #
def subject_metrology(log=print) -> dict:
    """寸法計測 — 段付きシャフトの各径を measure_pairs(サブピクセル)で測る."""
    from PIL import ImageDraw
    import measuring1d as m1
    H, W = 420, 760
    MM_PER_PX = 0.05
    # 段付きシャフト(合成): 3 区間の径(px)は真値
    sections = [(60, 260, 90), (260, 500, 130), (500, 700, 66)]  # x0, x1, dia_px
    img = np.full((H, W), 0.86)
    cy = H // 2
    for x0, x1, dia in sections:
        img[cy - dia // 2: cy + dia // 2, x0:x1] = 0.18
    img = _blur(img, 1.2)                                # 実画像らしいエッジのなまり
    rng = np.random.default_rng(SEED)
    img = np.clip(img + 0.01 * rng.standard_normal(img.shape), 0, 1)

    # 各区間の中央に垂直の測定矩形を置き、エッジ対で径を測る
    results = []
    for x0, x1, dia in sections:
        mx = (x0 + x1) // 2
        meas = m1.gen_measure_rectangle2(cy, mx, math.pi / 2, 110, 5, img.shape)
        pairs = m1.measure_pairs(img, meas, sigma=1.0, threshold=0.05)
        if len(pairs) != 1:
            raise RuntimeError(f"metrology: expected 1 pair at x={mx}, got {len(pairs)}")
        w_px = pairs[0]["width"]
        err = abs(w_px - dia)
        log(f"  x={mx}: true={dia}px measured={w_px:.2f}px err={err:.2f}px")
        if err > 1.0:
            raise RuntimeError(f"metrology error {err:.2f}px > 1px at x={mx}")
        results.append((mx, pairs[0], w_px, dia))

    # キャリパー矢印 + 実測値を描き込む
    vis = _pil_of(img)
    d = ImageDraw.Draw(vis)
    font = _font(19)
    fsmall = _font(14)
    for mx, pair, w_px, dia in results:
        # pair の pos は測定線に沿ったサンプル index (0..2*length1)。中心が cy。
        y_a = cy + (pair["first"] - 110)
        y_b = cy + (pair["second"] - 110)
        col = (30, 200, 255)
        d.line([(mx, y_a), (mx, y_b)], fill=col, width=2)
        for y, s in ((y_a, 1), (y_b, -1)):
            d.polygon([(mx, y), (mx - 5, y + 8 * s), (mx + 5, y + 8 * s)], fill=col)
            d.line([(mx - 14, y), (mx + 14, y)], fill=(255, 220, 60), width=1)
        d.text((mx + 12, cy - 14), f"{w_px * MM_PER_PX:.3f} mm",
               fill=(0, 90, 140), font=font)
        d.text((mx + 12, cy + 8), f"({w_px:.2f} px)", fill=(90, 110, 130),
               font=fsmall)
    out = _montage([np.stack([img] * 3, -1), _np_of(vis)],
                   ["段付きシャフト (合成, 0.05 mm/px)",
                    "measure_pairs のサブピクセル径計測"], ncols=2)
    _save_png(out, "industrial_metrology.png")
    _save_thumb("industrial_metrology.png")
    max_err = max(abs(w - dia) for _, _, w, dia in results)
    return {
        "file": "industrial_metrology.png",
        "title": "寸法計測 — 1D measuring サブピクセルキャリパー",
        "ops": ["gen_measure_rectangle2 (m1_*)", "measure_pairs (m1_measure_pairs)"],
        "data": "合成段付きシャフト (描画径 = 真値、0.05 mm/px)",
        "synthetic": True,
        "caption": ("測定矩形に沿ってグレープロファイルを取り、微分の極値をサブピクセル"
                    "補間してエッジ対を抽出。3 段の径を実測し、描画寸法との誤差は最大 "
                    f"{max_err:.2f}px。HALCON の 1D Measuring と同じ流儀。"),
        "verify": f"3 区間とも |実測 − 真値| ≤ {max_err:.2f}px (1px 未満を assert 済)",
    }


# --------------------------------------------------------------------------- #
# 工業 3: 位置決め / alignment by shape matching                                 #
# --------------------------------------------------------------------------- #
def _bracket_template(size=90):
    """L 字ブラケット風の白いワーク(穴 1 つ)テンプレート."""
    t = np.full((size, size), 0.15)
    t[12:78, 12:34] = 0.9                      # 縦腕
    t[56:78, 12:78] = 0.9                      # 横腕
    yy, xx = np.mgrid[0:size, 0:size]
    hole = ((yy - 23) ** 2 + (xx - 23) ** 2) < 7 ** 2
    t[hole] = 0.15
    return _blur(t, 0.8)


def subject_align_shapematch(log=print) -> dict:
    """位置決め — 回転したワーク 3 個を shape matching で検出し姿勢マーカー表示."""
    from PIL import Image, ImageDraw
    import shapematch as sm
    rng = np.random.default_rng(SEED)
    H, W = 480, 720
    size = 90
    tpl = _bracket_template(size)

    scene = np.full((H, W), 0.15)
    scene += 0.02 * rng.standard_normal((H, W))
    # 既知の姿勢でワークを 3 個配置(真値)
    poses = [(70, 80, 0.0), (160, 420, 25.0), (300, 180, -40.0)]  # top, left, deg
    tpl_img = Image.fromarray(_to_u8(tpl), "L")
    for top, left, ang in poses:
        rot = tpl_img.rotate(ang, resample=Image.BICUBIC, expand=True,
                             fillcolor=int(0.15 * 255))
        a = np.asarray(rot, np.float64) / 255.0
        h, w = a.shape
        region = scene[top:top + h, left:left + w]
        scene[top:top + h, left:left + w] = np.maximum(region, a)
    # 紛らわしい別部品(円板 + 長方形)も置く
    yy, xx = np.mgrid[0:H, 0:W]
    scene[((yy - 380) ** 2 + (xx - 560) ** 2) < 40 ** 2] = 0.85
    scene[60:100, 580:690] = 0.8
    scene = np.clip(_blur(scene, 0.6), 0, 1)

    model = sm.create_shape_model(tpl, min_grad=0.15)
    found = []
    work = scene.copy()
    for k in range(3):
        r = sm.find_shape_model(model, work, min_score=0.45,
                                angles=np.arange(-50.0, 51.0, 2.5))
        if not r["found"]:
            raise RuntimeError(f"shape match #{k + 1} not found")
        found.append(r)
        # 見つけた領域を消して次のインスタンスを探す(row/col は実測でモデル中心)
        rr, cc = r["row"], r["col"]
        h2 = size // 2 + 12
        work[max(0, rr - h2):rr + h2, max(0, cc - h2):cc + h2] = 0.15
        log(f"  match#{k + 1}: row={r['row']} col={r['col']} "
            f"angle={r['angle']:.1f} score={r['score']:.2f}")

    # 真値との突き合わせ(検算): 各検出は最寄りの真値と ±4px / ±5deg
    centers_true = []
    for top, left, ang in poses:
        rot = tpl_img.rotate(ang, resample=Image.BICUBIC, expand=True,
                             fillcolor=int(0.15 * 255))
        h, w = rot.size[1], rot.size[0]
        centers_true.append((top + h / 2, left + w / 2, ang))
    for r in found:
        cy_f, cx_f = r["row"], r["col"]            # 実測: 返り値はモデル中心
        best = min(centers_true,
                   key=lambda t: (t[0] - cy_f) ** 2 + (t[1] - cx_f) ** 2)
        dpos = math.hypot(best[0] - cy_f, best[1] - cx_f)
        dang = abs(r["angle"] - best[2])           # angles は PIL rotate と同符号
        log(f"    vs truth: dpos={dpos:.1f}px dang={dang:.1f}deg")
        if dpos > 6.0 or dang > 5.0:
            raise RuntimeError(f"pose error too large: {dpos:.1f}px / {dang:.1f}deg")

    vis = _pil_of(scene)
    d = ImageDraw.Draw(vis)
    font = _font(17)
    for i, r in enumerate(found):
        cy_f, cx_f = r["row"], r["col"]
        a = math.radians(r["angle"])               # PIL の CCW 回転 (y は下向き)
        ux, uy = math.cos(a), -math.sin(a)         # テンプレ x 軸の向き
        L = 34
        d.line([(cx_f - L * ux, cy_f - L * uy), (cx_f + L * ux, cy_f + L * uy)],
               fill=(30, 220, 120), width=2)
        d.line([(cx_f + L * uy, cy_f - L * ux), (cx_f - L * uy, cy_f + L * ux)],
               fill=(30, 220, 120), width=2)
        d.ellipse([cx_f - 5, cy_f - 5, cx_f + 5, cy_f + 5],
                  outline=(255, 220, 60), width=2)
        d.text((cx_f + 12, cy_f + 10),
               f"#{i + 1} θ={r['angle']:.1f}°  s={r['score']:.2f}",
               fill=(255, 220, 60), font=font)
    panels = [np.stack([tpl] * 3, -1), np.stack([scene] * 3, -1), _np_of(vis)]
    out = _montage(panels, ["テンプレート (ブラケット)",
                            "シーン (回転ワーク 3 + 別部品)",
                            "shape matching で位置 + 角度を検出"], ncols=3)
    _save_png(out, "industrial_align.png")
    _save_thumb("industrial_align.png")
    return {
        "file": "industrial_align.png",
        "title": "位置決め — 回転探索つき shape matching",
        "ops": ["create_shape_model", "find_shape_model (angles 探索)"],
        "data": "合成ブラケット 3 個 (配置姿勢 = 真値) + 距離部品",
        "synthetic": True,
        "caption": ("エッジ勾配ベースの形状モデルをピラミッド探索で照合し、"
                    "回転したワーク 3 個の位置と角度を検出。円板や長方形の別部品には"
                    "反応しない。ばら積みピッキングや組立の前段になる位置決め。"),
        "verify": "3 検出とも真値と位置 ≤6px・角度 ≤5° (assert 済)",
    }


# --------------------------------------------------------------------------- #
# 工業 4: ブロブ解析 / blob counting + size distribution                          #
# --------------------------------------------------------------------------- #
def subject_blob_pellets(log=print) -> dict:
    """ブロブ解析 — 樹脂ペレット 60 粒を watershed で切り分けて計数 + サイズ分布."""
    from PIL import ImageDraw
    rng = np.random.default_rng(SEED + 1)
    H, W = 480, 640
    N = 60
    # ペレット配置: 最小間隔を保った 60 点 (真値)。うち数点はほぼ接触。
    centers = []
    tries = 0
    while len(centers) < N and tries < 40000:
        tries += 1
        p = (rng.uniform(30, H - 30), rng.uniform(30, W - 30))
        if all((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 > 30 ** 2 for q in centers):
            centers.append(p)
    if len(centers) < N:
        raise RuntimeError("pellet placement failed")
    img = np.full((H, W), 0.10)
    yy, xx = np.mgrid[0:H, 0:W]
    radii = rng.uniform(8.5, 13.0, N)
    for (cy, cx), r in zip(centers, radii):
        e = rng.uniform(0.75, 1.0)
        th = rng.uniform(0, math.pi)
        dy, dx = yy - cy, xx - cx
        u = dy * math.cos(th) + dx * math.sin(th)
        v = -dy * math.sin(th) + dx * math.cos(th)
        mask = (u / r) ** 2 + (v / (r * e)) ** 2 < 1.0
        img[mask] = rng.uniform(0.62, 0.88)
    img = np.clip(_blur(img, 0.8) + 0.015 * rng.standard_normal((H, W)), 0, 1)

    # 検出: otsu → 穴埋め → 距離変換 watershed で接触粒を切る → blob 計数
    seg = fs.apply(img, "otsu")
    seg = fs.apply(seg, "fill_up")
    dt = fs.apply(1.0 - seg, "distance_transform")
    ridges = fs.apply(dt ** 0.3, "watersheds", 0.0, 0.5)
    cells = (ridges < 0.5).astype(np.float64) * seg
    objs = fs.segment_objects(cells, threshold="none", min_area=60)
    log(f"  pellets known={N} counted={len(objs)}")
    if len(objs) != N:
        raise RuntimeError(f"pellet count mismatch: {len(objs)} != {N}")

    areas = np.array([o["area"] for o in objs], float)
    lo, hi = np.percentile(areas, [20, 80])
    vis = _pil_of(img)
    d = ImageDraw.Draw(vis)
    font = _font(13)
    for o in objs:
        y0, x0, y1, x1 = o["bbox"]
        if o["area"] < lo:
            col = (90, 170, 255)          # 小粒
        elif o["area"] > hi:
            col = (255, 120, 70)          # 大粒
        else:
            col = (60, 220, 120)          # 標準
        d.rectangle([x0 - 2, y0 - 2, x1 + 2, y1 + 2], outline=col, width=2)
    d.text((10, 8), f"count = {len(objs)}", fill=(255, 230, 90), font=_font(22))

    # 面積ヒストグラム(matplotlib, 着色は可視化のみ)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    figbg = "#0e0f16"
    fig, ax = plt.subplots(figsize=(4.4, 3.3), facecolor=figbg)
    ax.set_facecolor(figbg)
    ax.hist(areas, bins=14, color="#37c774", edgecolor="#0e0f16")
    ax.axvline(lo, color="#5aaaff", ls="--", lw=1)
    ax.axvline(hi, color="#ff7846", ls="--", lw=1)
    ax.set_title("area distribution (px)", color="#e2e5ec", fontsize=11)
    ax.tick_params(colors="#8b91a0")
    for s in ax.spines.values():
        s.set_color("#3a3f4e")
    fig.tight_layout()
    fig.canvas.draw()
    hist = np.asarray(fig.canvas.buffer_rgba())[..., :3].astype(np.float64) / 255.0
    plt.close(fig)

    panels = [np.stack([img] * 3, -1), _np_of(vis), hist]
    out = _montage(panels, ["樹脂ペレット (合成, 60 粒)",
                            f"watershed 分離 + 計数 = {len(objs)}",
                            "面積分布 (20/80 パーセンタイル)"], ncols=3)
    _save_png(out, "industrial_blobs.png")
    _save_thumb("industrial_blobs.png")
    return {
        "file": "industrial_blobs.png",
        "title": "ブロブ解析 — 粒子計数とサイズ分布",
        "ops": ["otsu", "fill_up", "distance_transform", "watersheds",
                "segment_objects"],
        "data": "合成樹脂ペレット 60 粒 (配置数 = 真値)",
        "synthetic": True,
        "caption": ("60 粒を配置した合成画像を otsu 二値化し、距離変換 + watershed で"
                    "接触粒を切り分けて計数 60/60。面積の 20/80 パーセンタイルで"
                    "小粒(青)・標準(緑)・大粒(橙)に色分け。粉粒体の品質検査の型。"),
        "verify": f"配置 60 粒に対し計数 {len(objs)} (一致を assert 済)",
    }


# --------------------------------------------------------------------------- #
# 工業 5: コード読取り / barcode bar detection                                   #
# --------------------------------------------------------------------------- #
def subject_barcode(log=print) -> dict:
    """コード読取り — 合成バーコードのバーをエッジ対で検出し本数を op で計数."""
    from PIL import ImageDraw
    import measuring1d as m1
    rng = np.random.default_rng(SEED + 2)
    H, W = 300, 700
    module = 3
    img = np.full((H, W), 0.95)
    x = 50                                     # クワイエットゾーン
    bars = []                                  # (x0, x1) 真値
    while True:
        bw = int(rng.integers(1, 5)) * module
        gw = int(rng.integers(1, 4)) * module
        if x + bw > W - 50:
            break
        img[60:220, x:x + bw] = 0.05
        bars.append((x, x + bw))
        x += bw + gw
    n_true = len(bars)
    img = np.clip(_blur(img, 0.7) + 0.01 * rng.standard_normal((H, W)), 0, 1)

    # 登録 op decode_barcode: 中央走査線上の暗バー本数を返す
    n_op = int(fs.apply(img, "decode_barcode", 0.5, 0.5))
    # 1D measuring: 走査線に沿ってバーのエッジ対(幅つき)を抽出
    meas = m1.gen_measure_rectangle2(140, W // 2, 0.0, W // 2 - 10, 9, img.shape)
    pairs = m1.measure_pairs(img, meas, sigma=1.0, threshold=0.08)
    log(f"  bars true={n_true} decode_barcode={n_op} measure_pairs={len(pairs)}")
    if not (n_true == n_op == len(pairs)):
        raise RuntimeError(f"bar count mismatch: true={n_true} op={n_op} "
                           f"pairs={len(pairs)}")
    # 各バー幅の検算: 真値と ±1px
    x0_line = W // 2 - (W // 2 - 10)
    for (bx0, bx1), p in zip(bars, pairs):
        mx0 = x0_line + p["first"]
        mx1 = x0_line + p["second"]
        if abs(mx0 - bx0) > 1.5 or abs(mx1 - bx1) > 1.5:
            raise RuntimeError(f"bar edge off: true=({bx0},{bx1}) "
                               f"meas=({mx0:.1f},{mx1:.1f})")

    vis = _pil_of(img)
    d = ImageDraw.Draw(vis)
    for p in pairs:
        for pos, col in ((p["first"], (30, 200, 90)), (p["second"], (255, 120, 60))):
            px = x0_line + pos
            d.line([(px, 40), (px, 240)], fill=col, width=1)
    d.line([(x0_line, 140), (x0_line + 2 * (W // 2 - 10), 140)],
           fill=(60, 140, 255), width=1)
    d.text((14, 250), f"bars: decode_barcode = {n_op} / measure_pairs = "
           f"{len(pairs)} / truth = {n_true}", fill=(20, 60, 160), font=_font(18))

    # 走査線プロファイル(下段)
    prof = img[140]
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7.0, 1.9), facecolor="#0e0f16")
    ax.set_facecolor("#0e0f16")
    ax.plot(prof, color="#37c774", lw=1.2)
    ax.set_xlim(0, W)
    ax.set_title("scanline gray profile (row 140)", color="#e2e5ec", fontsize=10)
    ax.tick_params(colors="#8b91a0")
    for s in ax.spines.values():
        s.set_color("#3a3f4e")
    fig.tight_layout()
    fig.canvas.draw()
    profimg = np.asarray(fig.canvas.buffer_rgba())[..., :3].astype(np.float64) / 255.0
    plt.close(fig)

    out = _montage([_np_of(vis), profimg],
                   ["バーエッジ検出 (緑=立下り, 橙=立上り)", None], ncols=1,
                   label_h=30)
    _save_png(out, "industrial_barcode.png")
    _save_thumb("industrial_barcode.png")
    return {
        "file": "industrial_barcode.png",
        "title": "コード読取りの土台 — 走査線エッジ対によるバー検出",
        "ops": ["decode_barcode", "gen_measure_rectangle2 (m1_*)",
                "measure_pairs (m1_measure_pairs)"],
        "data": f"合成バーコード ({n_true} 本, バー位置 = 真値)",
        "synthetic": True,
        "caption": ("実際のバーコードリーダーと同じく走査線のグレープロファイルから"
                    f"バーのエッジ対を検出。{n_true} 本のバー全ての両端を ±1.5px 以内で"
                    "特定し、登録 op decode_barcode(簡易バー計数)とも本数が一致。"
                    "※フル復号器ではなくバー検出・幅計測の素材。"),
        "verify": (f"真値 {n_true} 本 = decode_barcode = measure_pairs、"
                   "全エッジ ±1.5px (assert 済)"),
    }


# --------------------------------------------------------------------------- #
# Physical AI 1: bin picking (深度 → セグメント → 把持候補)                       #
# --------------------------------------------------------------------------- #
def subject_binpick_depth(log=print) -> dict:
    """bin picking — MuJoCo のばら積みを深度で見てセグメントし把持候補を採点."""
    from PIL import ImageDraw
    import mujoco
    import bin_pick as BP
    m, _ = BP._build(10, seed=3)
    d = mujoco.MjData(m)
    d.ctrl[:7] = BP._HOME_ARM
    d.ctrl[7] = BP._GRIP_OPEN
    for _ in range(int(2.0 / m.opt.timestep)):     # 部品が山なりに落ち着くまで
        mujoco.mj_step(m, d)

    res_h, res_w = 480, 480
    ren = mujoco.Renderer(m, height=res_h, width=res_w)
    cam = mujoco.MjvCamera()
    cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    cx, cy = BP._BIN_C
    cam.lookat[:] = [cx, cy, BP._TABLE_TOP]
    cam.distance = 0.62
    cam.azimuth = 90
    cam.elevation = -90                            # 真上から
    ren.update_scene(d, camera=cam)
    rgb = np.asarray(ren.render()).astype(np.float64) / 255.0
    ren.enable_depth_rendering()
    ren.update_scene(d, camera=cam)
    depth = np.asarray(ren.render()).copy()
    ren.disable_depth_rendering()
    ren.close()

    # 真上視なので平面深度 ≈ カメラ高さ − 物体高さ。テーブル面より 2cm 以上
    # 高いものが部品。ビン壁は内側領域マスクで除外(壁位置は既知の設計値)。
    fovy = math.radians(45.0)
    f_px = (res_h / 2) / math.tan(fovy / 2)
    d_table = cam.distance                         # lookat がテーブル面
    inner_px = int((BP._BIN_HALF - 0.012) * f_px / (d_table - 0.05))
    mask = (depth < d_table - 0.02).astype(np.float64)
    inner = np.zeros_like(mask)
    ic, jc = res_h // 2, res_w // 2
    inner[ic - inner_px:ic + inner_px, jc - inner_px:jc + inner_px] = 1.0
    mask *= inner
    objs = fs.segment_objects(mask, threshold="none", min_area=120)
    log(f"  parts dropped=10 segments={len(objs)}")
    if not (5 <= len(objs) <= 10):
        raise RuntimeError(f"unexpected segment count {len(objs)}")

    # 把持候補の採点: 周囲クリアランス(距離変換) + 高さ(深度が小さい=上)
    from scipy.ndimage import distance_transform_edt
    scores = []
    for i, o in enumerate(objs):
        others = (mask > 0.5) & ~o["mask"]
        dt = distance_transform_edt(~others)
        cyx = tuple(int(v) for v in o["centroid"])
        clearance = float(dt[cyx])
        top = float(d_table - depth[o["mask"]].min())
        scores.append(clearance + 250.0 * top)
        log(f"    part{i}: clearance={clearance:.0f}px top={top * 100:.1f}cm "
            f"score={scores[-1]:.0f}")
    best = int(np.argmax(scores))

    vis = _pil_of(rgb)
    dr = ImageDraw.Draw(vis)
    font = _font(15)
    order = np.argsort(scores)[::-1]
    for rank, i in enumerate(order):
        o = objs[i]
        ycen, xcen = o["centroid"]
        col = (40, 255, 120) if i == best else (255, 200, 60)
        pts = np.argwhere(o["mask"])               # (row, col)
        rect = fs.fit_rectangle2(pts)              # 最小面積の有向長方形
        ang = math.radians(rect["angle_deg"])      # 長軸角 (y 下向き, PIL と同系)
        jaw = 26
        # 把持ジョー: 長軸に直交する 2 本の平行線
        nx, ny = -math.sin(ang), math.cos(ang)
        tx, ty = math.cos(ang), math.sin(ang)
        for s in (-1, 1):
            ox, oy = xcen + s * jaw * nx, ycen + s * jaw * ny
            dr.line([(ox - 10 * tx, oy - 10 * ty), (ox + 10 * tx, oy + 10 * ty)],
                    fill=col, width=3)
        dr.ellipse([xcen - 4, ycen - 4, xcen + 4, ycen + 4], fill=col)
        dr.text((xcen + 8, ycen - 20), f"{rank + 1}", fill=col, font=font)
    panels = [rgb, fs.colorize_depth(np.where(inner > 0.5, depth, np.nan)),
              _np_of(vis)]
    out = _montage(panels, ["ばら積み (MuJoCo 物理落下)",
                            "深度画像 (真上カメラ)",
                            f"把持候補 {len(objs)} 件 (緑=最良)"], ncols=3)
    _save_png(out, "phai_binpick.png")
    _save_thumb("phai_binpick.png")
    return {
        "file": "phai_binpick.png",
        "title": "bin picking — 深度セグメントと把持候補の採点",
        "ops": ["segment_objects", "fit_rectangle2", "colorize_depth",
                "(scipy distance_transform_edt)"],
        "data": "MuJoCo 物理シミュレーション (部品 10 個を実際に落下・堆積)",
        "synthetic": True,
        "caption": ("部品 10 個を物理シミュレーションで箱に落とし、真上の深度カメラで"
                    "観測。深度しきい値でセグメントした各部品を「周囲クリアランス + "
                    "高さ」で採点し、把持ジョーの向きは長方形フィットの長軸から決める。"
                    "緑が最優先候補。実機ビンピッキングの前段そのもの。"),
        "verify": ("10 個投入で可視セグメント数が 5〜10 に入ることを assert "
                   "(重なりで隠れる分は正直に減る)"),
    }


# --------------------------------------------------------------------------- #
# Physical AI 2: LIDAR 投影 → クラスタリング                                     #
# --------------------------------------------------------------------------- #
def subject_lidar_clusters(log=print) -> dict:
    """LIDAR — 実レイキャストの点群を地面除去 + クラスタリングして物体を数える."""
    import mujoco
    import lidar_sim as LS
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    m = mujoco.MjModel.from_xml_string(LS._SCENE)
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    origin = (0.0, 0.0, 0.9)
    pts, hit_ratio = LS._scan(m, d, origin, channels=48, az_steps=480)
    log(f"  rays={48 * 480} points={len(pts)} hit={hit_ratio * 100:.0f}%")

    nonground, gmask = fs.remove_ground(pts, thresh=0.03)
    clusters = fs.euclidean_clusters(nonground, tol=0.28, min_size=12)
    log(f"  ground removed {int(gmask.sum())} pts -> clusters={len(clusters)}")
    if len(clusters) != 6:                    # シーンの物体は 6 個 (真値)
        raise RuntimeError(f"cluster count {len(clusters)} != 6 objects")

    # 参照ビュー
    ren = mujoco.Renderer(m, height=480, width=640)
    cam = mujoco.MjvCamera()
    cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    cam.lookat[:] = [0, 0, 0.25]
    cam.distance = 4.6
    cam.azimuth = 130
    cam.elevation = -28
    ren.update_scene(d, camera=cam)
    ref = np.asarray(ren.render()).copy()
    ren.close()

    bg, fg, muted = "#12141b", "#e2e5ec", "#8b91a0"
    fig = plt.figure(figsize=(12.6, 5.4), facecolor=bg)
    ax0 = fig.add_subplot(1, 2, 1)
    ax0.imshow(ref)
    ax0.axis("off")
    ax0.set_title("シーン (MuJoCo, 物体 6 個)", color=fg, fontsize=12)
    ax1 = fig.add_subplot(1, 2, 2, facecolor=bg)
    gpts = pts[gmask]
    ax1.scatter(gpts[:, 0], gpts[:, 1], s=1.5, c="#2a2e3a")
    cmap = plt.get_cmap("turbo")
    for i, idx in enumerate(clusters):
        c = cmap(0.1 + 0.8 * i / max(1, len(clusters) - 1))
        P = nonground[idx]
        ax1.scatter(P[:, 0], P[:, 1], s=4, color=c)
        box = fs.obb(P)
        # OBB の上面 4 角を xy 平面へ投影して枠を描く
        corners = box["corners"]
        top4 = corners[np.argsort(corners[:, 2])[-4:]][:, :2]
        centre = top4.mean(axis=0)
        angs = np.arctan2(top4[:, 1] - centre[1], top4[:, 0] - centre[0])
        poly = top4[np.argsort(angs)]
        poly = np.vstack([poly, poly[:1]])
        ax1.plot(poly[:, 0], poly[:, 1], color=c, lw=1.4)
        ax1.text(centre[0], centre[1] + 0.28, f"obj{i + 1}\n{len(P)}pt",
                 color=c, fontsize=8, ha="center")
    ax1.scatter([origin[0]], [origin[1]], c="red", s=60, marker="^",
                label="LIDAR")
    ax1.legend(loc="lower right", facecolor=bg, labelcolor=fg, edgecolor=muted)
    ax1.set_aspect("equal")
    ax1.set_title(f"鳥瞰図: 地面除去 + クラスタ {len(clusters)} 個 + OBB",
                  color=fg, fontsize=12)
    ax1.tick_params(colors=muted)
    for s in ax1.spines.values():
        s.set_color("#3a3f4e")
    fig.tight_layout()
    path = os.path.join(ASSETS_DIR, "phai_lidar_clusters.png")
    fig.savefig(path, dpi=120, facecolor=bg)
    plt.close(fig)
    _save_thumb("phai_lidar_clusters.png")
    return {
        "file": "phai_lidar_clusters.png",
        "title": "LIDAR 点群 → 地面除去 → クラスタリング",
        "ops": ["remove_ground", "euclidean_clusters", "obb",
                "(mj_ray 実レイキャスト)"],
        "data": "MuJoCo シーンへの実レイキャスト (48ch × 480 方位, 物体 6 個 = 真値)",
        "synthetic": True,
        "caption": ("リング型 LIDAR を模して 2 万本超のレイを実際に飛ばし、"
                    "返ってきた点群から RANSAC で地面を除去、ユークリッド距離で"
                    "クラスタリングすると物体 6 個が 6 クラスタに分かれる。"
                    "各クラスタに OBB(有向バウンディングボックス)を当てて鳥瞰表示。"
                    "自律移動ロボットの障害物認識の型。"),
        "verify": "シーンの物体 6 個 = クラスタ 6 個 (assert 済)",
    }


# --------------------------------------------------------------------------- #
# Physical AI 3: ステレオ視差 → 障害物マップ                                      #
# --------------------------------------------------------------------------- #
def subject_stereo_obstacles(log=print) -> dict:
    """ステレオ — 視差から奥行きを復元し、鳥瞰の障害物マップまで通す."""
    import stereo
    import stereo_sim as SS
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    left, right, depth_gt, f_px = SS._render(res=360)
    gl = left.mean(axis=2)
    gr = right.mean(axis=2)
    disp = stereo.disparity_subpixel(gl, gr, max_disp=48, block=9)
    valid = disp > 0.5
    depth_est = np.where(valid, f_px * SS._BASELINE / np.maximum(disp, 1e-6),
                         np.nan)

    # 左カメラの姿勢 (シーン XML の既知値) で 3D 復元し世界座標へ
    res = gl.shape[0]
    x_ax = np.array([1.0, 0.0, 0.0])
    y_ax = np.array([0.0, 0.35, 0.94])
    y_ax = y_ax / np.linalg.norm(y_ax)
    z_ax = np.cross(x_ax, y_ax)
    cam_pos = np.array([-SS._BASELINE / 2, -0.6, 0.6])
    vv, uu = np.mgrid[0:res, 0:res]
    cx = cy = res / 2
    Z = depth_est
    X = (uu - cx) * Z / f_px
    Y = (cy - vv) * Z / f_px
    P = (cam_pos[None, :] + X.reshape(-1, 1) * x_ax + Y.reshape(-1, 1) * y_ax
         - Z.reshape(-1, 1) * z_ax)
    ok = np.isfinite(P).all(axis=1) & (Z.reshape(-1) < 4.5)
    P = P[ok]
    # 検算: 地面点 (z≈0) が本当に 0 付近に写ることを確認してから使う
    ground_med = float(np.median(np.abs(P[P[:, 2] < 0.12][:, 2])))
    log(f"  reconstructed {len(P)} pts, ground |z| median={ground_med:.3f}m")
    if ground_med > 0.06:
        raise RuntimeError(f"ground plane off: {ground_med:.3f}m")

    obst = P[P[:, 2] > 0.10]
    clusters = fs.euclidean_clusters(obst, tol=0.16, min_size=60)
    log(f"  obstacle clusters={len(clusters)} (scene objects=4)")
    if len(clusters) != 4:
        raise RuntimeError(f"obstacle clusters {len(clusters)} != 4")

    bg, fg, muted = "#12141b", "#e2e5ec", "#8b91a0"
    fig, ax = plt.subplots(1, 3, figsize=(15.2, 5.0), facecolor=bg)
    ax[0].imshow(np.clip(left, 0, 1))
    ax[0].axis("off")
    ax[0].set_title("左カメラ (MuJoCo, 物体 4 個)", color=fg, fontsize=12)
    dd = np.where(valid, disp, np.nan)
    ax[1].imshow(fs.colorize_disparity(np.nan_to_num(dd)), interpolation="nearest")
    ax[1].axis("off")
    ax[1].set_title("視差 (block matching, サブピクセル)", color=fg, fontsize=12)
    ax[2].set_facecolor(bg)
    gnd = P[P[:, 2] <= 0.10]
    sub = gnd[:: max(1, len(gnd) // 4000)]
    ax[2].scatter(sub[:, 0], sub[:, 1], s=1, c="#2a2e3a")
    cmapo = plt.get_cmap("turbo")
    for i, idx in enumerate(clusters):
        c = cmapo(0.15 + 0.7 * i / max(1, len(clusters) - 1))
        Q = obst[idx]
        ax[2].scatter(Q[:, 0], Q[:, 1], s=3, color=c)
        box = fs.obb(Q)
        corners = box["corners"]
        top4 = corners[np.argsort(corners[:, 2])[-4:]][:, :2]
        centre = top4.mean(axis=0)
        angs = np.arctan2(top4[:, 1] - centre[1], top4[:, 0] - centre[0])
        poly = top4[np.argsort(angs)]
        poly = np.vstack([poly, poly[:1]])
        ax[2].plot(poly[:, 0], poly[:, 1], color=c, lw=1.4)
    ax[2].scatter([cam_pos[0]], [cam_pos[1]], c="red", marker="^", s=60,
                  label="camera")
    ax[2].legend(loc="lower right", facecolor=bg, labelcolor=fg, edgecolor=muted)
    ax[2].set_aspect("equal")
    ax[2].set_title(f"鳥瞰の障害物マップ ({len(clusters)} クラスタ)", color=fg,
                    fontsize=12)
    ax[2].tick_params(colors=muted)
    for s in ax[2].spines.values():
        s.set_color("#3a3f4e")
    fig.tight_layout()
    path = os.path.join(ASSETS_DIR, "phai_stereo_obstacles.png")
    fig.savefig(path, dpi=120, facecolor=bg)
    plt.close(fig)
    _save_thumb("phai_stereo_obstacles.png")
    return {
        "file": "phai_stereo_obstacles.png",
        "title": "ステレオ視差 → 3D 復元 → 鳥瞰障害物マップ",
        "ops": ["disparity_subpixel (stereo)", "colorize_disparity",
                "euclidean_clusters", "obb"],
        "data": "MuJoCo レンダのステレオペア (基線 12cm, 物体 4 個 = 真値)",
        "synthetic": True,
        "caption": ("2 台のカメラ画像のズレ(視差)をブロックマッチングで求め、"
                    "Z = f·b/d で奥行きに変換して 3D 点群へ。高さ 10cm 超の点を"
                    "クラスタリングすると 4 物体が 4 クラスタに分かれ、鳥瞰の"
                    "障害物マップができる。移動ロボットの視覚の最短経路。"),
        "verify": ("復元地面の |z| 中央値 <6cm と障害物クラスタ数 = 物体数 4 を "
                   "assert 済"),
    }


# --------------------------------------------------------------------------- #
# Physical AI 4: 焦点合成 / focus stacking                                       #
# --------------------------------------------------------------------------- #
def subject_focus_stack(log=print) -> dict:
    """焦点合成 — 浅い被写界深度 7 枚から全焦点画像を合成(既存 suite 流用)."""
    import focus_stack as FSK
    path = os.path.join(ASSETS_DIR, "phai_focus_stack.png")
    r = FSK.run_focus_stack_demo(out_png=path, log=log)
    _save_thumb("phai_focus_stack.png")
    return {
        "file": "phai_focus_stack.png",
        "title": "焦点合成 — ボケた 7 枚から全焦点 1 枚を作る",
        "ops": ["focus_stack suite (ラプラシアン鮮鋭度で最良フォーカスを選択)"],
        "data": "MuJoCo レンダ + 被写界深度シミュレーション (7 焦点)",
        "synthetic": True,
        "caption": ("手前・中間・奥にピントを振った 7 枚を撮り、各画素で最も"
                    "シャープな 1 枚を選んで合成すると、全体にピントの合った 1 枚に"
                    "なる。顕微鏡検査や基板検査で使う焦点合成と同じ仕組み。"
                    f"鮮鋭度スコアは単写比 {r.get('sharpness_gain', 0):.2f} 倍。"
                    if isinstance(r, dict) and "sharpness_gain" in r else
                    "手前・中間・奥にピントを振った 7 枚を撮り、各画素で最も"
                    "シャープな 1 枚を選んで合成。顕微鏡・基板検査の焦点合成と同じ。"),
        "verify": "run_focus_stack_demo の自己スコア (画像内に実測値表示)",
    }


# --------------------------------------------------------------------------- #
# Physical AI 5: bin picking 実機シーケンス mp4                                  #
# --------------------------------------------------------------------------- #
def subject_binpick_motion(log=print) -> dict:
    """bin picking の実動作 mp4 — 既存 bin_pick suite の GIF を mp4 化."""
    import bin_pick as BP
    from PIL import Image
    os.makedirs(MEDIA_DIR, exist_ok=True)
    scratch_gif = os.path.join(ASSETS_DIR, "media", "_phai_bin_pick_tmp.gif")
    r = BP.render_bin_pick_gif(scratch_gif, n_cubes=8, n_picks=3, seed=1,
                               log=log)
    if r.get("n_picked", 0) < 2:
        raise RuntimeError(f"bin pick only picked {r.get('n_picked')} — 素材不採用")
    # GIF と同一フレームを mp4 化(でっち上げ禁止: フレームは GIF から読む)
    frames = []
    with Image.open(scratch_gif) as im:
        try:
            while True:
                frames.append(np.asarray(im.convert("RGB")).copy())
                im.seek(im.tell() + 1)
        except EOFError:
            pass
    import imageio.v2 as imageio
    mp4_path = os.path.join(MEDIA_DIR, "phai_bin_pick.mp4")
    imageio.mimwrite(mp4_path, frames, fps=30, codec="libx264", quality=8,
                     macro_block_size=1, pixelformat="yuv420p")
    # 静的サムネ: シーケンス中盤(把持中)のフレーム
    thumb_frame = frames[len(frames) // 2]
    _save_png(thumb_frame.astype(np.float64) / 255.0, "phai_bin_pick_still.png")
    _save_thumb("phai_bin_pick_still.png")
    os.remove(scratch_gif)
    # 検証: mp4 を開き直してフレーム数を実測
    reader = imageio.get_reader(mp4_path)
    n = sum(1 for _ in reader)
    reader.close()
    log(f"  mp4 frames={n} picked={r['n_picked']}")
    if n <= 1:
        raise RuntimeError("mp4 has <=1 frame")
    return {
        "file": "media/phai_bin_pick.mp4",
        "still": "phai_bin_pick_still.png",
        "title": "bin picking 実動作 — 探索・把持・搬出のフルサイクル",
        "ops": ["bin_pick suite (6-DOF IK + 把持候補採点 + MuJoCo 物理)"],
        "data": ("MuJoCo 物理シミュレーション (Franka Panda + 部品 8 個、"
                 f"{r['n_picked']} 個の搬出成功を実測)"),
        "synthetic": True,
        "caption": ("箱に落とした部品 8 個から把持候補を採点して選び、6 自由度 IK で"
                    "真上から掴んで搬出する実動作。接着なしの素の物理で、箱の外に"
                    f"出た部品だけを成功と数えて {r['n_picked']} 個成功。"),
        "verify": f"搬出成功 {r['n_picked']} 個 (高さ実測でカウント)・mp4 {n} フレーム",
    }


SUBJECTS = {
    "defect_metal": subject_defect_metal,
    "metrology": subject_metrology,
    "align_shapematch": subject_align_shapematch,
    "blob_pellets": subject_blob_pellets,
    "barcode": subject_barcode,
    "binpick_depth": subject_binpick_depth,
    "lidar_clusters": subject_lidar_clusters,
    "stereo_obstacles": subject_stereo_obstacles,
    "focus_stack": subject_focus_stack,
    "binpick_motion": subject_binpick_motion,
}


# --------------------------------------------------------------------------- #
# メタ + スニペット                                                             #
# --------------------------------------------------------------------------- #
def _merge_meta(new_items: list) -> list:
    old = []
    if os.path.exists(META_PATH):
        with open(META_PATH, encoding="utf-8") as f:
            old = json.load(f)
    by_file = {m["file"]: m for m in old}
    for m in new_items:
        by_file[m["file"]] = m
    merged = list(by_file.values())
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    return merged


def _write_snippet(meta: list) -> None:
    lines = [
        "<!-- gen_industrial_gallery.py が自動生成。記事 md への挿入候補",
        "     (このファイル自体は記事ではない。GALLERY.md も編集しない)。 -->",
        "",
        "# 工業用途 + Physical AI ギャラリー — 記事挿入候補",
        "",
        "すべて合成データ / シミュレーション上の実処理(モックアップなし)。",
        "検出・計測結果は既知の真値(配置数・描画寸法・配置姿勢)と照合済み。",
        "",
    ]
    for m in meta:
        is_mp4 = m["file"].endswith(".mp4")
        lines.append(f"## {m['title']}")
        lines.append("")
        if is_mp4:
            lines.append(f"動画: {RAW_BASE}{m['file']}")
            lines.append("(GitHub blob ページでインライン再生可。静止サムネ: "
                         f"{RAW_BASE}{m['still'].replace('.png', '_thumb.jpg')} )")
        else:
            thumb = os.path.splitext(m["file"])[0] + "_thumb.jpg"
            lines.append(f"![{m['title']}]({RAW_BASE}{thumb})")
            lines.append("")
            lines.append(f"(フル解像度: {RAW_BASE}{m['file']} )")
        lines.append("")
        lines.append(f"{m['caption']} 使用 op: {', '.join(m['ops'])}。"
                     f"データ: {m['data']}。")
        lines.append("")
    with open(SNIPPET_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subjects", default="",
                    help="comma-separated subject names (default: all)")
    args = ap.parse_args()
    os.makedirs(ASSETS_DIR, exist_ok=True)
    wanted = ([s.strip() for s in args.subjects.split(",") if s.strip()]
              or list(SUBJECTS))
    results, failures = [], []
    for name in wanted:
        fn = SUBJECTS.get(name)
        if fn is None:
            print(f"[skip] unknown subject: {name}")
            continue
        print(f"[run ] {name}", flush=True)
        try:
            meta = fn()
            results.append(meta)
            print(f"[done] {name} -> {meta['file']}", flush=True)
        except Exception as e:  # honest: 失敗は隠さずログ
            import traceback
            traceback.print_exc()
            failures.append((name, str(e)))
            print(f"[FAIL] {name}: {e}", flush=True)
    if results:
        merged = _merge_meta(results)
        _write_snippet(merged)
        print(f"meta: {META_PATH}\nsnippet: {SNIPPET_PATH}")
    if failures:
        print("failures:", failures)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
