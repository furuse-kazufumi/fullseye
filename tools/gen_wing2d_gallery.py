# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gen_wing2d_gallery — Qiita 記事「紙面の科学館」2D 古典オペレータ・ウィングの展示生成.

Generate the "classic 2-D operator wing" exhibits for the Qiita museum section.

目的(かみくだき) / Purpose:
  既存の「科学館ウィング(11 点)」「博物館ウィング(30 点)」と **題材が重ならない**
  古典的 2-D 画像処理オペレータの展示を作る。すべて Fullseye の**登録 op の実出力**で、
  モックアップは 1 枚もない(honest disclosure 規律)。キャプションに載せる数値は
  すべて生成時の**実測値**で、meta JSON に記録される(創作した数字は 1 つも無い)。

方針 / Policy:
  * **アニメーション優先** —— パラメータ掃引・段階的な処理の進行・モーフ・次数を
    上げていく復元は GIF にする。静止フレーム 1 枚だけ見ても意味が分かる構図にする
    (毎フレームにラベルと実測値を焼き込む)。
  * 描画は Fullseye の op + numpy 合成 + Pillow のテキスト/線描のみ。**matplotlib 不使用**
    (カラーマップも fullseye.apply_cmap を使う)。
  * **決定的** —— 乱数は固定 seed。再生成で PNG/GIF の SHA-256 が一致する。
  * 素材は合成 or skimage.data(BSD / public domain)。CC0/PD 以外の実データは使わない。

生成物 / Outputs:
  docs/articles/assets/wing2d_<name>.png            -- 静止展示 (フル解像度)
  docs/articles/assets/wing2d_<name>_thumb.jpg      -- 幅 720px サムネ (JPEG q85)
  docs/articles/assets/media/wing2d_<name>.gif      -- アニメ展示
  docs/articles/assets/thumbs/wing2d_<name>_720.jpg -- GIF の代表フレームサムネ
  docs/articles/exhibits/wing2d.md                  -- キャプション原稿 (記事 md 本体は編集しない)
  docs/articles/assets/_wing2d_meta.json            -- 使用 op / 実測値 / 来歴のメタ

Run:
  py -3.11 tools/gen_wing2d_gallery.py                       # 全展示
  py -3.11 tools/gen_wing2d_gallery.py --subjects morph_quartet,freq_sweep
  py -3.11 tools/gen_wing2d_gallery.py --list                # 展示名の一覧
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import fullseye as fs  # noqa: E402

ASSETS_DIR = os.path.join(REPO, "docs", "articles", "assets")
MEDIA_DIR = os.path.join(ASSETS_DIR, "media")
THUMBS_DIR = os.path.join(ASSETS_DIR, "thumbs")
EXHIBITS_DIR = os.path.join(REPO, "docs", "articles", "exhibits")
SAMPLES_IMG = os.path.join(REPO, "studio_assets", "sample_images")
META_PATH = os.path.join(ASSETS_DIR, "_wing2d_meta.json")
CAPTIONS_PATH = os.path.join(EXHIBITS_DIR, "wing2d.md")
RAW_BASE = ("https://raw.githubusercontent.com/furuse-kazufumi/fullseye/"
            "master/docs/articles/assets/")

SEED = 20260902
THUMB_WIDTH = 720
GIF_MAX_BYTES = 3 * 1024 * 1024
FONT_PATH = r"C:\Windows\Fonts\meiryo.ttc"

INK = (238, 238, 244)
INK_DIM = (150, 152, 166)
BG = (13, 13, 20)
ACCENT = (255, 196, 80)


# --------------------------------------------------------------------------- #
# I/O ヘルパ / I-O helpers                                                      #
# --------------------------------------------------------------------------- #
def _load_gray(name: str) -> np.ndarray:
    """studio_assets/sample_images の画像を float64 [0,1] グレイで読む."""
    img = fs.to_float01(fs.load(os.path.join(SAMPLES_IMG, name)))
    if img.ndim == 3:
        img = fs.apply(img, "rgb1_to_gray")
    return np.asarray(img, np.float64)


def _to_u8(rgb) -> np.ndarray:
    a = np.asarray(rgb)
    if a.dtype != np.uint8:
        a = np.clip(a * 255.0 + 0.5, 0, 255).astype(np.uint8)
    if a.ndim == 2:
        a = np.stack([a] * 3, axis=-1)
    return a


def _cmap(gray, name: str = "turbo", vmin=None, vmax=None) -> np.ndarray:
    """fullseye 自身のカラーマップで着色 (matplotlib は使わない)."""
    return np.asarray(fs.apply_cmap(np.asarray(gray, np.float64), name,
                                    vmin=vmin, vmax=vmax), np.float64)


def _font(size: int):
    from PIL import ImageFont
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:                              # honest: フォント不在は既定に落とす
        return ImageFont.load_default()


def _save_png(rgb, filename: str) -> str:
    from PIL import Image
    path = os.path.join(ASSETS_DIR, filename)
    Image.fromarray(_to_u8(rgb), "RGB").save(path, optimize=True)
    return path


def _save_thumb(filename: str) -> str:
    from PIL import Image
    src = os.path.join(ASSETS_DIR, filename)
    dst = os.path.join(ASSETS_DIR, os.path.splitext(filename)[0] + "_thumb.jpg")
    with Image.open(src) as im:
        im = im.convert("RGB")
        if im.width > THUMB_WIDTH:
            im = im.resize((THUMB_WIDTH,
                            round(im.height * THUMB_WIDTH / im.width)),
                           Image.LANCZOS)
        im.save(dst, format="JPEG", quality=85, optimize=True)
    return dst


def _save_gif(frames, name: str, fps: float = 6.0, hold_last: int = 0) -> dict:
    """PIL でループ GIF を media/ に書き、代表フレームのサムネを thumbs/ に置く.

    3 MB を超えたら色数を段階的に落として再エンコード(サイズは実測して返す)。
    ``hold_last`` は最終フレームの追加保持数(掃引の終端を読ませるため)。
    """
    from PIL import Image
    os.makedirs(MEDIA_DIR, exist_ok=True)
    os.makedirs(THUMBS_DIR, exist_ok=True)
    arrs = [_to_u8(f) for f in frames]
    if hold_last > 0:
        arrs = arrs + [arrs[-1]] * hold_last
    path = os.path.join(MEDIA_DIR, name + ".gif")
    used, scale = 256, 1.0
    # 色数 -> 解像度 の順に落として 3 MB に収める(横幅は 900px を下回らせない)。
    for scale in (1.0, 0.92, 0.86, 0.80):
        cur = arrs
        if scale < 1.0:
            w = int(round(arrs[0].shape[1] * scale))
            if w < 900:
                break
            h = int(round(arrs[0].shape[0] * scale))
            cur = [_fit(a, w, h) for a in arrs]
        done = False
        for colors in (192, 128, 96, 64, 48):
            pil = [Image.fromarray(a, "RGB").convert(
                "P", palette=Image.ADAPTIVE, colors=colors) for a in cur]
            pil[0].save(path, save_all=True, append_images=pil[1:],
                        duration=int(round(1000.0 / fps)), loop=0, optimize=True)
            used = colors
            if os.path.getsize(path) <= GIF_MAX_BYTES:
                done = True
                break
        if done:
            arrs = cur
            break
    # 代表フレーム (掃引の中ほど) をサムネに
    rep = arrs[len(arrs) // 2]
    tpath = os.path.join(THUMBS_DIR, name + "_720.jpg")
    im = Image.fromarray(rep, "RGB")
    if im.width > THUMB_WIDTH:
        im = im.resize((THUMB_WIDTH, round(im.height * THUMB_WIDTH / im.width)),
                       Image.LANCZOS)
    im.save(tpath, format="JPEG", quality=88, optimize=True)
    return {"path": path, "thumb": tpath, "frames": len(arrs),
            "bytes": os.path.getsize(path), "colors": used,
            "size": (arrs[0].shape[1], arrs[0].shape[0])}


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------- #
# 合成キャンバス / composition helpers (Pillow drawing only)                     #
# --------------------------------------------------------------------------- #
def _fit(rgb, w: int, h: int, resample=None) -> np.ndarray:
    """(H,W[,3]) を w×h にリサイズ. resample 既定は LANCZOS."""
    from PIL import Image
    im = Image.fromarray(_to_u8(rgb), "RGB")
    if resample is None:
        resample = Image.LANCZOS
    if (im.width, im.height) != (w, h):
        im = im.resize((w, h), resample)
    return np.asarray(im, np.uint8)


def _canvas(w: int, h: int):
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (w, h), BG)
    return im, ImageDraw.Draw(im)


def _paste(im, rgb, x: int, y: int, w: int = None, h: int = None,
           border=(58, 60, 76)):
    from PIL import Image, ImageDraw
    a = _to_u8(rgb)
    if w and h:
        a = _fit(a, w, h)
    tile = Image.fromarray(a, "RGB")
    im.paste(tile, (x, y))
    if border:
        ImageDraw.Draw(im).rectangle(
            [x, y, x + tile.width - 1, y + tile.height - 1], outline=border)
    return tile.width, tile.height


def _text(draw, xy, s, size=20, fill=INK, anchor="la"):
    draw.text(xy, s, font=_font(size), fill=fill, anchor=anchor)


def _panel_grid(panels, labels, ncols, tile=(300, 300), pad=12,
                label_h=54, title=None, title_h=52, sub=None,
                resample=None) -> np.ndarray:
    """パネルを格子に並べ、各パネル下に 1〜2 行のラベルを置く. 戻り uint8 RGB."""
    from PIL import Image
    n = len(panels)
    ncols = min(ncols, n)
    nrows = (n + ncols - 1) // ncols
    tw, th = tile
    W = pad + ncols * (tw + pad)
    top = title_h if title else pad
    H = top + nrows * (th + label_h + pad)
    im, draw = _canvas(W, H)
    if title:
        _text(draw, (pad + 2, 12), title, size=26, fill=INK)
        if sub:
            _text(draw, (W - pad - 2, 18), sub, size=18, fill=INK_DIM,
                  anchor="ra")
    for i, p in enumerate(panels):
        r, c = divmod(i, ncols)
        x = pad + c * (tw + pad)
        y = top + r * (th + label_h + pad)
        a = _fit(p, tw, th, resample=resample)
        im.paste(Image.fromarray(a, "RGB"), (x, y))
        draw.rectangle([x, y, x + tw - 1, y + th - 1], outline=(58, 60, 76))
        lab = labels[i] if i < len(labels) else ""
        for k, line in enumerate(str(lab).split("\n")[:2]):
            _text(draw, (x + tw // 2, y + th + 8 + k * 23), line,
                  size=19 if k == 0 else 17,
                  fill=INK if k == 0 else ACCENT, anchor="ma")
    return np.asarray(im, np.uint8)


def _num(v: float) -> str:
    """軸ラベル用の読みやすい数値表記 (指数表記を避ける)."""
    a = abs(v)
    if a >= 1000:
        return f"{v:,.0f}"
    if a >= 10:
        return f"{v:.0f}" if abs(v - round(v)) < 5e-3 else f"{v:.1f}"
    if a >= 1:
        return f"{v:.2f}".rstrip("0").rstrip(".")
    if a == 0:
        return "0"
    return f"{v:.3f}".rstrip("0").rstrip(".")


def _plot(series, w, h, *, xlim=None, ylim=None, xlabel="", ylabel="",
          title="", marks=None, hlines=(), grid_y=4, legend_pos="tr",
          bg=(20, 20, 30)) -> np.ndarray:
    """折れ線グラフを Pillow で描く (matplotlib は使わない).

    series: [{"x": arr, "y": arr, "color": (r,g,b), "label": str,
              "style": "line"|"dots"}]
    marks : [{"x": float, "y": float, "color": (...), "r": int}] 強調点
    """
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(im)
    ml, mr, mt, mb = 62, 14, (30 if title else 12), 40
    pw, ph = w - ml - mr, h - mt - mb
    xs = np.concatenate([np.asarray(s["x"], float) for s in series]) \
        if series else np.array([0.0, 1.0])
    ys = np.concatenate([np.asarray(s["y"], float) for s in series]) \
        if series else np.array([0.0, 1.0])
    x0, x1 = xlim if xlim else (float(xs.min()), float(xs.max()))
    y0, y1 = ylim if ylim else (float(ys.min()), float(ys.max()))
    if x1 <= x0:
        x1 = x0 + 1.0
    if y1 <= y0:
        y1 = y0 + 1.0

    def px(x):
        return ml + (float(x) - x0) / (x1 - x0) * pw

    def py(y):
        return mt + ph - (float(y) - y0) / (y1 - y0) * ph

    draw.rectangle([ml, mt, ml + pw, mt + ph], outline=(64, 66, 84))
    for k in range(grid_y + 1):
        yv = y0 + (y1 - y0) * k / grid_y
        yy = py(yv)
        draw.line([ml, yy, ml + pw, yy], fill=(40, 42, 56))
        _text(draw, (ml - 8, yy), _num(yv), size=14, fill=INK_DIM,
              anchor="rm")
    for k in range(5):
        xv = x0 + (x1 - x0) * k / 4
        xx = px(xv)
        draw.line([xx, mt, xx, mt + ph], fill=(40, 42, 56))
        _text(draw, (xx, mt + ph + 6), _num(xv), size=14, fill=INK_DIM,
              anchor="ma")
    for hv, hc in hlines:
        yy = py(hv)
        for xx in range(ml, ml + pw, 10):
            draw.line([xx, yy, xx + 5, yy], fill=hc)
    if title:
        _text(draw, (ml, 6), title, size=18, fill=INK)
    if xlabel:
        _text(draw, (ml + pw, mt + ph + 22), xlabel, size=15, fill=INK_DIM,
              anchor="ra")
    if ylabel:
        _text(draw, (4, mt - 2), ylabel, size=15, fill=INK_DIM, anchor="la")
    for s in series:
        pts = [(px(a), py(b)) for a, b in zip(s["x"], s["y"])]
        col = s.get("color", INK)
        if s.get("style") == "dots":
            for (a, b) in pts:
                draw.ellipse([a - 2.5, b - 2.5, a + 2.5, b + 2.5], fill=col)
        elif len(pts) >= 2:
            draw.line([c for p in pts for c in p], fill=col,
                      width=s.get("width", 2))
    for m in (marks or []):
        a, b, r = px(m["x"]), py(m["y"]), m.get("r", 5)
        draw.ellipse([a - r, b - r, a + r, b + r],
                     outline=m.get("color", ACCENT), width=2)
    labs = [s for s in series if s.get("label")]
    if labs:
        ly = mt + 6 if legend_pos.startswith("t") else mt + ph - 18 * len(labs)
        lx = ml + pw - 10 if legend_pos.endswith("r") else ml + 10
        anc = "ra" if legend_pos.endswith("r") else "la"
        for i, s in enumerate(labs):
            _text(draw, (lx, ly + i * 19), s["label"], size=15,
                  fill=s.get("color", INK), anchor=anc)
    return np.asarray(im, np.uint8)


def _stack_v(parts, pad=0, bg=BG) -> np.ndarray:
    """複数の RGB ブロックを縦に連結 (幅は最大幅へ中央寄せ)."""
    from PIL import Image
    arrs = [_to_u8(p) for p in parts]
    W = max(a.shape[1] for a in arrs)
    H = sum(a.shape[0] for a in arrs) + pad * (len(arrs) - 1)
    im = Image.new("RGB", (W, H), bg)
    y = 0
    for a in arrs:
        im.paste(Image.fromarray(a, "RGB"), ((W - a.shape[1]) // 2, y))
        y += a.shape[0] + pad
    return np.asarray(im, np.uint8)


def _overlay_mask(gray, mask, color=(255, 96, 96), alpha=0.55) -> np.ndarray:
    """グレイ画像にマスクを半透明で重ねる (float [0,1] RGB)."""
    base = np.asarray(gray, np.float64)
    if base.ndim == 2:
        base = np.stack([base] * 3, -1)
    c = np.asarray(color, np.float64) / 255.0
    m = np.asarray(mask, np.float64)[..., None]
    return np.clip(base * (1 - alpha * m) + c * (alpha * m), 0, 1)


def _psnr(ref, test) -> float:
    """PSNR [dB] (信号レンジ 1.0). 完全一致は inf を返さず 99.0 で頭打ち."""
    mse = float(np.mean((np.asarray(ref, np.float64)
                         - np.asarray(test, np.float64)) ** 2))
    return 99.0 if mse <= 1e-12 else float(10.0 * np.log10(1.0 / mse))


# --------------------------------------------------------------------------- #
# 展示 1: 形態学の 4 兄弟 / morphology quartet                                   #
# --------------------------------------------------------------------------- #
C_ERO, C_DIL, C_OPEN, C_CLOSE = ((255, 122, 122), (120, 190, 255),
                                 (150, 230, 160), (238, 180, 255))
BAR_WIDTHS = (2, 4, 6, 8, 10)
SLIT_WIDTHS = (2, 4, 6)
_A_OF_RADIUS = {1: 0.0, 2: 0.34, 3: 0.67, 4: 1.0}   # _rad(a) = 1 + int(a*3)


def _granulometry_figure() -> tuple:
    """開/閉の効き方を「幅」で読ませるテスト図形を Fullseye の描画 op で作る.

    戻り ``(region, bar_boxes, slit_boxes)``。棒は幅 2/4/6/8/10 px、
    ブロックのスリットは幅 2/4/6 px —— 半径 r の opening は幅 2r 未満の棒を、
    半径 r の closing は幅 2r 未満のスリットを消す(はず)、を実測で確かめる。
    """
    import imagedraw
    H = W = 320
    img = np.zeros((H, W), np.float64)
    img = imagedraw.draw_circle(img, (96, 96), 72, color=1.0, fill=True)
    img = imagedraw.draw_circle(img, (96, 96), 38, color=0.0, fill=True)
    bars = []
    x = 24
    for w in BAR_WIDTHS:
        img[210:300, x:x + w] = 1.0
        bars.append((210, 300, x, x + w, w))
        x += w + 26
    img[196:300, 208:308] = 1.0                      # 塊 (スリットを刻む土台)
    slits, sx = [], 220
    for w in SLIT_WIDTHS:
        img[204:292, sx:sx + w] = 0.0
        slits.append((204, 292, sx, sx + w, w))
        sx += w + 22
    img[36:160, 208:308] = 1.0                       # 太い塊 (基準面積)
    return img, bars, slits


def subject_morph_quartet(log=print) -> dict:
    """収縮/膨張/開/閉を同じ図形に当て、面積 [px]・棒とスリットの生き死にを実測."""
    base, bars, slits = _granulometry_figure()
    src = fs.apply(base, "threshold", 0.25, 1.0)     # image -> region (二値化)
    area0 = float(np.sum(src))
    res = {}
    for r, a in _A_OF_RADIUS.items():
        e = fs.apply(src, "erosion_circle", a)
        d = fs.apply(src, "dilation_circle", a)
        o = fs.apply(src, "opening_circle", a)
        c = fs.apply(src, "closing_circle", a)
        bar_keep = [w for (r0, r1, c0, c1, w) in bars
                    if float(np.sum(o[r0:r1, c0:c1])) > 0.5 * (r1 - r0) * w * 0.5]
        slit_fill = [w for (r0, r1, c0, c1, w) in slits
                     if float(np.sum(c[r0:r1, c0:c1])) > 0.5 * (r1 - r0) * w]
        res[r] = {"ero": e, "dil": d, "open": o, "close": c,
                  "lost": np.clip(src - o, 0, 1), "gain": np.clip(c - src, 0, 1),
                  "area": {"ero": float(np.sum(e)), "dil": float(np.sum(d)),
                           "open": float(np.sum(o)), "close": float(np.sum(c))},
                  "bar_keep": bar_keep, "slit_fill": slit_fill}
    radii = sorted(res)
    frames = []
    for r in radii + radii[-2:0:-1]:
        R = res[r]
        cur = radii.index(r) + 1
        grid = _panel_grid(
            [src, R["ero"], R["dil"], R["open"],
             R["close"], _overlay_mask(src, R["lost"], (255, 96, 96)),
             _overlay_mask(src, R["gain"], (110, 180, 255)),
             fs.apply(src, "morph_grad", 0.0)],
            ["元の図形 (棒 2/4/6/8/10 px)\n%d px" % round(area0),
             "erosion_circle\n%d px" % round(R["area"]["ero"]),
             "dilation_circle\n%d px" % round(R["area"]["dil"]),
             "opening_circle\n%d px" % round(R["area"]["open"]),
             "closing_circle\n%d px" % round(R["area"]["close"]),
             "開で消えた部分 (赤)\n生き残った棒: %s px" % (
                 "/".join(str(w) for w in R["bar_keep"]) or "なし"),
             "閉で埋まった部分 (青)\n埋まったスリット: %s px" % (
                 "/".join(str(w) for w in R["slit_fill"]) or "なし"),
             "morph_grad (輪郭)\n境界だけを 1 px 幅で残す",
             ],
            4, tile=(258, 258), label_h=56,
            title="形態学の 4 兄弟 —— 収縮・膨張・開・閉",
            sub="構造要素 = 半径 %d px の円 (a=%.2f)" % (r, _A_OF_RADIUS[r]))
        plot = _plot(
            [{"x": radii[:cur], "y": [res[k]["area"]["ero"] for k in radii[:cur]],
              "color": C_ERO, "label": "erosion（痩せる）"},
             {"x": radii[:cur], "y": [res[k]["area"]["dil"] for k in radii[:cur]],
              "color": C_DIL, "label": "dilation（太る）"},
             {"x": radii[:cur], "y": [res[k]["area"]["open"] for k in radii[:cur]],
              "color": C_OPEN, "label": "opening（細い棒だけ消える）"},
             {"x": radii[:cur], "y": [res[k]["area"]["close"] for k in radii[:cur]],
              "color": C_CLOSE, "label": "closing（細い隙間だけ埋まる）"}],
            grid.shape[1], 300, xlim=(1, 4), ylim=(24000, 49000),
            hlines=((area0, (130, 132, 150)),),
            title="前景の面積 [px] を半径 1→4 px で追う（点線 = 元図形 %d px）"
                  % round(area0),
            xlabel="構造要素の半径 r [px]", legend_pos="tl")
        frames.append(_stack_v([grid, plot], pad=6))
    info = _save_gif(frames, "wing2d_morph_quartet", fps=1.5, hold_last=1)
    return {
        "name": "morph_quartet", "kind": "gif", "file": info["path"],
        "thumb": info["thumb"], "frames": info["frames"],
        "bytes": info["bytes"], "size": info["size"],
        "title": "形態学の 4 兄弟 —— どれが何を消すのか",
        "ops": ["threshold", "erosion_circle", "dilation_circle",
                "opening_circle", "closing_circle", "morph_grad"],
        "data": "Fullseye の描画 op (imagedraw.draw_circle) で作った合成テスト図形",
        "measured": {
            "area_src_px": round(area0),
            "area_by_radius": {str(r): {k: round(v) for k, v in
                                        res[r]["area"].items()} for r in radii},
            "bar_widths_px": list(BAR_WIDTHS),
            "slit_widths_px": list(SLIT_WIDTHS),
            "bars_surviving_opening": {str(r): res[r]["bar_keep"] for r in radii},
            "slits_filled_by_closing": {str(r): res[r]["slit_fill"] for r in radii},
        },
        "caption": (
            "幅 2/4/6/8/10 px の棒と幅 2/4/6 px のスリットを刻んだ図形に、"
            "4 つの形態学 op を半径 1→4 px で当てた。膨張は面積を %d→%d px に増やし、"
            "収縮は %d→%d px に減らす。開は面積をほぼ保ったまま細い棒だけを落とし "
            "(r=1 で %s px が生き残り、r=4 では %s px だけ)、閉は細い隙間だけを埋める "
            "(r=1 で幅 %s px、r=4 で幅 %s px のスリットが消える)。"
            % (round(res[1]["area"]["dil"]), round(res[4]["area"]["dil"]),
               round(res[1]["area"]["ero"]), round(res[4]["area"]["ero"]),
               "/".join(map(str, res[1]["bar_keep"])) or "なし",
               "/".join(map(str, res[4]["bar_keep"])) or "なし",
               "/".join(map(str, res[1]["slit_fill"])) or "なし",
               "/".join(map(str, res[4]["slit_fill"])) or "なし")),
    }


def _hist_panel(images, labels, colors, w, h, title="", bins=64,
                ylim=None) -> np.ndarray:
    """複数画像の輝度ヒストグラムを重ねて描く (Pillow のみ)."""
    series = []
    edges = np.linspace(0.0, 1.0, bins + 1)
    mid = (edges[:-1] + edges[1:]) / 2.0
    for img, lab, col in zip(images, labels, colors):
        hh, _ = np.histogram(np.clip(np.asarray(img, np.float64), 0, 1),
                             bins, (0.0, 1.0))
        series.append({"x": mid, "y": hh.astype(np.float64) / max(1, hh.sum()),
                       "color": col, "label": lab})
    return _plot(series, w, h, xlim=(0, 1), ylim=ylim, title=title,
                 xlabel="輝度 [0,1]", legend_pos="tr")


# --------------------------------------------------------------------------- #
# 展示 2: 周波数フィルタの効き / frequency filters                               #
# --------------------------------------------------------------------------- #
def _spectrum_rgb(img, cutoff=None, band=None) -> np.ndarray:
    """fft_image のスペクトルを着色し、遮断周波数の円を焼き込む (可視化)."""
    from PIL import Image, ImageDraw
    spec = np.asarray(fs.apply(np.asarray(img, np.float64), "fft_image"), np.float64)
    rgb = _to_u8(_cmap(spec, "inferno"))
    im = Image.fromarray(rgb, "RGB")
    d = ImageDraw.Draw(im)
    H, W = spec.shape
    cy, cx = H / 2.0, W / 2.0                       # fftshift 後の DC 位置
    for rad, col in [(cutoff, (120, 255, 180)), (band, (255, 200, 90))]:
        if rad is None:
            continue
        for rr in (rad if isinstance(rad, (tuple, list)) else (rad,)):
            px = rr * min(H, W)                      # 正規化周波数 -> 画素半径
            d.ellipse([cx - px, cy - px, cx + px, cy + px], outline=col, width=2)
    return np.asarray(im, np.uint8)


def _signed_to_01(x) -> np.ndarray:
    """符号つき出力を 0.5 中心に写像して表示する (負が黒に潰れるのを防ぐ)."""
    a = np.asarray(x, np.float64)
    m = float(np.max(np.abs(a)))
    return 0.5 + 0.5 * (a / m if m > 1e-12 else a)


def _stretch(x, lo_pct=1.0, hi_pct=99.0) -> np.ndarray:
    """パーセンタイルでコントラストを伸ばす **表示専用** の写像.

    highpass の出力は平均 0.5・標準偏差 0.04 程度に収まるため、そのまま貼ると
    一様な灰色にしか見えない。処理の結果を変えるものではなく、見せるための拡大。
    """
    a = np.asarray(x, np.float64)
    lo, hi = np.percentile(a, lo_pct), np.percentile(a, hi_pct)
    return np.clip((a - lo) / (hi - lo), 0, 1) if hi > lo else np.zeros_like(a)


def subject_freq_sweep(log=print) -> dict:
    """ローパス/ハイパス/バンドパスの遮断周波数を掃引し、残る情報量を実測."""
    src = _load_gray("camera.png")
    n = 11
    A = np.linspace(0.0, 1.0, n)
    lo_cut = 0.05 + 0.40 * A                        # lowpass の遮断 (正規化周波数)
    hi_cut = 0.02 + 0.30 * A                        # highpass の遮断
    bp_lo, bp_hi = 0.02 + 0.15 * A, 0.2 + 0.3 * 0.5
    F = np.fft.fftshift(np.fft.fft2(src))
    Etot = float(np.sum(np.abs(F) ** 2))
    H, W = src.shape
    rr = np.sqrt(np.fft.fftshift(np.fft.fftfreq(H))[:, None] ** 2
                 + np.fft.fftshift(np.fft.fftfreq(W))[None, :] ** 2)
    psnr_lo, keep_e = [], []
    lows, highs, bands = [], [], []
    for i, a in enumerate(A):
        lo = np.asarray(fs.apply(src, "lowpass", float(a), 0.5), np.float64)
        hi = np.asarray(fs.apply(src, "highpass", float(a), 0.5), np.float64)
        bp = np.asarray(fs.apply(src, "bandpass_image", float(a), 0.5), np.float64)
        lows.append(lo); highs.append(hi); bands.append(bp)
        psnr_lo.append(_psnr(src, lo))
        keep_e.append(100.0 * float(np.sum(np.abs(F[rr <= lo_cut[i]]) ** 2)) / Etot)
    frames = []
    for i, a in enumerate(A):
        grid = _panel_grid(
            [src, _spectrum_rgb(src, cutoff=lo_cut[i], band=(bp_lo[i], bp_hi)),
             lows[i], _stretch(highs[i]), _stretch(_signed_to_01(bands[i])),
             _cmap(np.abs(src - lows[i]), "magma", vmin=0.0, vmax=0.35)],
            ["元の写真 (camera.png)",
             "スペクトル + 遮断円\n緑=lowpass 橙=bandpass",
             "lowpass (遮断 %.3f)\nPSNR %.2f dB / エネルギー %.1f%%"
             % (lo_cut[i], psnr_lo[i], keep_e[i]),
             "highpass (遮断 %.3f)\n細かい模様だけ残る" % hi_cut[i],
             "bandpass_image (%.3f〜%.3f)\n符号つき出力を 0.5 中心で表示"
             % (bp_lo[i], bp_hi),
             "元 − lowpass の差\n捨てられた高周波"],
            3, tile=(330, 330), label_h=56,
            title="周波数フィルタの効き —— どこで切ると何が消えるか",
            sub="遮断周波数を 0.05 → 0.45 (正規化) で掃引")
        plot = _plot(
            [{"x": lo_cut[:i + 1], "y": psnr_lo[:i + 1], "color": (150, 230, 160),
              "label": "lowpass 後の PSNR [dB]"}],
            grid.shape[1] // 2 - 4, 300, xlim=(0.05, 0.45), ylim=(10, 40),
            title="遮断を上げるほど元に近づく", xlabel="遮断周波数 (正規化)")
        plot2 = _plot(
            [{"x": lo_cut[:i + 1], "y": keep_e[:i + 1], "color": (255, 196, 80),
              "label": "通過帯に残るエネルギー [%]"}],
            grid.shape[1] // 2 - 4, 300, xlim=(0.05, 0.45), ylim=(95, 100.05),
            title="エネルギーはほぼ低周波にある", xlabel="遮断周波数 (正規化)")
        from PIL import Image
        row = Image.new("RGB", (grid.shape[1], 300), BG)
        row.paste(Image.fromarray(plot, "RGB"), (0, 0))
        row.paste(Image.fromarray(plot2, "RGB"), (grid.shape[1] - plot2.shape[1], 0))
        frames.append(_stack_v([grid, np.asarray(row, np.uint8)], pad=6))
    info = _save_gif(frames, "wing2d_freq_sweep", fps=3.0, hold_last=3)
    return {
        "name": "freq_sweep", "kind": "gif", "file": info["path"],
        "thumb": info["thumb"], "frames": info["frames"],
        "bytes": info["bytes"], "size": info["size"],
        "title": "周波数フィルタの効き",
        "ops": ["fft_image", "lowpass", "highpass", "bandpass_image"],
        "data": "skimage.data camera (BSD / public domain)",
        "measured": {
            "cutoff_normalised": [round(float(x), 4) for x in lo_cut],
            "lowpass_psnr_db": [round(float(x), 2) for x in psnr_lo],
            "energy_kept_pct": [round(float(x), 3) for x in keep_e],
        },
        "caption": (
            "同じ写真にローパス・ハイパス・バンドパスを当て、遮断周波数を "
            "0.05→0.45 (正規化) で掃引した。ローパスの遮断を 0.05 から 0.45 へ上げると "
            "元画像との PSNR は %.2f→%.2f dB。一方その通過帯に入っているスペクトル"
            "エネルギーは遮断 0.05 の時点ですでに %.2f%% —— 「エネルギーのほとんどは低周波"
            "にあるのに、見た目は高周波が決めている」という画像の癖がそのまま数字に出る。"
            % (psnr_lo[0], psnr_lo[-1], keep_e[0])),
    }
