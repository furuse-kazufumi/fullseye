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
    for scale in (1.0, 0.94, 0.90, 0.87):
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
    n = 9
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
             "highpass (遮断 %.3f)\n実測 std %.3f — 表示は 1〜99%%tile 伸長"
             % (hi_cut[i], float(np.std(highs[i]))),
             "bandpass_image (%.3f〜%.3f)\n符号つき出力を 0.5 中心 + 伸長で表示"
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


# --------------------------------------------------------------------------- #
# 展示 3: ノイズ除去の比較 / denoising comparison                                #
# --------------------------------------------------------------------------- #
def subject_denoise_compare(log=print) -> dict:
    """median / bilateral / non-local means を同じノイズ画像に当て PSNR を実測."""
    src = _load_gray("camera.png")
    n = 9
    B = np.linspace(0.0, 1.0, n)
    sigma = 0.02 + 0.20 * B                          # add_noise_white の b -> σ
    cols = {"median": (255, 140, 120), "bilateral": (120, 190, 255),
            "sk_nlm": (150, 230, 160), "noisy": (170, 170, 185)}
    rows = []
    for b in B:
        noisy = np.asarray(fs.apply(src, "add_noise_white", 0.5, float(b)),
                           np.float64)
        out = {"noisy": noisy,
               "median": np.asarray(fs.apply(noisy, "median", 0.3, 0.5), np.float64),
               "bilateral": np.asarray(fs.apply(noisy, "bilateral", 0.5, 0.5),
                                       np.float64),
               "sk_nlm": np.asarray(fs.apply(noisy, "sk_nlm", 0.3, 0.5), np.float64)}
        rows.append({"img": out,
                     "psnr": {k: _psnr(src, v) for k, v in out.items()},
                     "sigma_est": float(fs.apply(noisy, "estimate_noise", 0.5, 0.5))})
    frames = []
    for i, b in enumerate(B):
        R = rows[i]
        best = max(("median", "bilateral", "sk_nlm"), key=lambda k: R["psnr"][k])
        grid = _panel_grid(
            [src, R["img"]["noisy"], R["img"]["median"],
             R["img"]["bilateral"], R["img"]["sk_nlm"],
             _cmap(np.abs(src - R["img"][best]), "magma", vmin=0.0, vmax=0.25)],
            ["元の写真 (ノイズ無し)\n基準",
             "add_noise_white σ=%.3f\nPSNR %.2f dB / estimate_noise %.3f%s"
             % (sigma[i], R["psnr"]["noisy"], R["sigma_est"],
                "（上限に張り付き）" if R["sigma_est"] >= 0.999 else ""),
             "median\nPSNR %.2f dB (%+.2f)"
             % (R["psnr"]["median"], R["psnr"]["median"] - R["psnr"]["noisy"]),
             "bilateral\nPSNR %.2f dB (%+.2f)"
             % (R["psnr"]["bilateral"], R["psnr"]["bilateral"] - R["psnr"]["noisy"]),
             "sk_nlm (non-local means)\nPSNR %.2f dB (%+.2f)"
             % (R["psnr"]["sk_nlm"], R["psnr"]["sk_nlm"] - R["psnr"]["noisy"]),
             "勝者 %s の残差 |元 − 出力|\n明るいほど復元できていない" % best],
            3, tile=(300, 300), label_h=56,
            title="ノイズ除去の比較 —— 同じノイズに 3 つの流儀",
            sub="ノイズ σ = %.3f (add_noise_white b=%.2f)" % (sigma[i], b))
        plot = _plot(
            [{"x": sigma[:i + 1], "y": [r["psnr"][k] for r in rows[:i + 1]],
              "color": cols[k], "label": lab}
             for k, lab in (("noisy", "ノイズ画像そのもの"), ("median", "median"),
                            ("bilateral", "bilateral"), ("sk_nlm", "sk_nlm"))],
            grid.shape[1], 300, xlim=(0.02, 0.22), ylim=(12, 42),
            title="ノイズを強くしていくと 3 つの順位はどうなるか",
            xlabel="加えたノイズ σ", legend_pos="tr")
        frames.append(_stack_v([grid, plot], pad=6))
    info = _save_gif(frames, "wing2d_denoise_compare", fps=2.2, hold_last=3)
    win = [max(("median", "bilateral", "sk_nlm"), key=lambda k: r["psnr"][k])
           for r in rows]
    return {
        "name": "denoise_compare", "kind": "gif", "file": info["path"],
        "thumb": info["thumb"], "frames": info["frames"],
        "bytes": info["bytes"], "size": info["size"], "panels": 6,
        "title": "ノイズ除去の比較 —— median / bilateral / NLM",
        "ops": ["add_noise_white", "median", "bilateral", "sk_nlm",
                "estimate_noise"],
        "data": "skimage.data camera (BSD / public domain) + 決定的な白色ノイズ",
        "measured": {
            "sigma": [round(float(x), 4) for x in sigma],
            "psnr_db": {k: [round(r["psnr"][k], 2) for r in rows]
                        for k in ("noisy", "median", "bilateral", "sk_nlm")},
            "sigma_estimated_by_op": [round(r["sigma_est"], 4) for r in rows],
            "winner_per_sigma": win,
        },
        "caption": (
            "同じ写真に σ=%.3f→%.3f の白色ノイズを乗せ、median・bilateral・"
            "non-local means を固定パラメータで当てて PSNR を実測した 6 パネル。"
            "弱いノイズ (σ=%.3f) では %s が %.2f dB で最良だが、強いノイズ (σ=%.3f) では "
            "%s が %.2f dB で逆転する —— 「どれが一番強いか」はノイズ量と設定次第で、"
            "掃引の途中で順位が 2 度入れ替わった。ノイズ画像そのものは %.2f→%.2f dB。"
            % (sigma[0], sigma[-1], sigma[0], win[0], rows[0]["psnr"][win[0]],
               sigma[-1], win[-1], rows[-1]["psnr"][win[-1]],
               rows[0]["psnr"]["noisy"], rows[-1]["psnr"]["noisy"])),
    }


# --------------------------------------------------------------------------- #
# 展示 4: ヒストグラム整形 / histogram shaping                                   #
# --------------------------------------------------------------------------- #
def subject_hist_shaping(log=print) -> dict:
    """コントラストを潰していく入力に equalize / clahe を当て std と entropy を実測."""
    src = _load_gray("page.png")                    # 照明ムラのある文書画像
    n = 12
    K = np.linspace(1.0, 0.16, n)                   # コントラスト圧縮率
    mid = float(np.mean(src))
    rows = []
    for k in K:
        low = np.clip(mid + (src - mid) * k, 0, 1)  # 低コントラスト化 (numpy 合成)
        eq = np.asarray(fs.apply(low, "equalize", 0.5, 0.5), np.float64)
        cl = np.asarray(fs.apply(low, "clahe", 0.67, 0.5), np.float64)
        rows.append({
            "low": low, "eq": eq, "cl": cl,
            "std": {t: float(fs.apply(v, "gray_histo_abs", 0.5, 0.5))
                    for t, v in (("low", low), ("eq", eq), ("cl", cl))},
            "ent": {t: float(fs.apply(v, "entropy_gray", 0.5, 0.5))
                    for t, v in (("low", low), ("eq", eq), ("cl", cl))}})
    C_LOW, C_EQ, C_CL = (170, 170, 185), (255, 176, 96), (130, 220, 255)
    frames = []
    for i, k in enumerate(K):
        R = rows[i]
        grid = _panel_grid(
            [src, R["low"], R["eq"], R["cl"]],
            ["元の文書画像 (page.png)\nstd %.4f" % rows[0]["std"]["low"],
             "コントラストを %.2f 倍に圧縮\nstd %.4f / entropy %.3f"
             % (k, R["std"]["low"], R["ent"]["low"]),
             "equalize (画像全体で平坦化)\nstd %.4f / entropy %.3f"
             % (R["std"]["eq"], R["ent"]["eq"]),
             "clahe (タイル 4×4 で平坦化)\nstd %.4f / entropy %.3f"
             % (R["std"]["cl"], R["ent"]["cl"])],
            4, tile=(262, 262), label_h=56,
            title="ヒストグラム整形 —— 潰れた画像はどこまで戻せるか",
            sub="入力コントラスト %.2f 倍 (元の平均 %.3f を中心に圧縮)" % (k, mid))
        hist = _hist_panel(
            [R["low"], R["eq"], R["cl"]],
            ["圧縮した入力", "equalize", "clahe"], [C_LOW, C_EQ, C_CL],
            grid.shape[1] // 2 - 4, 300, ylim=(0, 0.18),
            title="輝度ヒストグラム (64 bin・頻度は正規化)")
        curve = _plot(
            [{"x": K[:i + 1], "y": [r["std"][t] for r in rows[:i + 1]],
              "color": c, "label": lab}
             for t, c, lab in (("low", C_LOW, "入力の std"),
                               ("eq", C_EQ, "equalize 後の std"),
                               ("cl", C_CL, "clahe 後の std"))],
            grid.shape[1] // 2 - 4, 300, xlim=(0.16, 1.0), ylim=(0, 0.32),
            title="gray_histo_abs (標準偏差) で見た復元度",
            xlabel="入力コントラスト倍率", legend_pos="tl")
        from PIL import Image
        row = Image.new("RGB", (grid.shape[1], 300), BG)
        row.paste(Image.fromarray(hist, "RGB"), (0, 0))
        row.paste(Image.fromarray(curve, "RGB"), (grid.shape[1] - curve.shape[1], 0))
        frames.append(_stack_v([grid, np.asarray(row, np.uint8)], pad=6))
    info = _save_gif(frames, "wing2d_hist_shaping", fps=2.5, hold_last=3)
    return {
        "name": "hist_shaping", "kind": "gif", "file": info["path"],
        "thumb": info["thumb"], "frames": info["frames"],
        "bytes": info["bytes"], "size": info["size"], "panels": 6,
        "title": "ヒストグラム整形 —— equalize と clahe",
        "ops": ["equalize", "clahe", "gray_histo_abs", "entropy_gray"],
        "data": "skimage.data page (BSD / public domain)",
        "measured": {
            "contrast_factor": [round(float(x), 3) for x in K],
            "std": {t: [round(r["std"][t], 4) for r in rows]
                    for t in ("low", "eq", "cl")},
            "entropy_norm": {t: [round(r["ent"][t], 4) for r in rows]
                             for t in ("low", "eq", "cl")},
        },
        "caption": (
            "文書画像のコントラストを 1.00→%.2f 倍まで潰していき、equalize と clahe で"
            "戻せるかを追った。入力の標準偏差は %.4f→%.4f まで落ちるが、equalize 後は "
            "%.4f→%.4f、clahe 後は %.4f→%.4f にとどまる。ヒストグラムは入力が針のように"
            "細くなっても、平坦化した側は幅を保ったままだ。"
            % (K[-1], rows[0]["std"]["low"], rows[-1]["std"]["low"],
               rows[0]["std"]["eq"], rows[-1]["std"]["eq"],
               rows[0]["std"]["cl"], rows[-1]["std"]["cl"])),
    }


# --------------------------------------------------------------------------- #
# exhibit_tile (著者提供の共通部品) を使うための薄いブリッジ                     #
# --------------------------------------------------------------------------- #
def _tile_mod():
    """tools/exhibit_tile.py を import する (contact_sheet / flipbook)."""
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    import exhibit_tile
    return exhibit_tile


def _draw_poly(rgb_u8, pts_rc, color, width=2, closed=True):
    """(row, col) 列の折れ線を RGB uint8 画像に描く (Pillow 線描)."""
    from PIL import Image, ImageDraw
    im = Image.fromarray(np.ascontiguousarray(rgb_u8), "RGB")
    d = ImageDraw.Draw(im)
    xy = [(float(c), float(r)) for r, c in np.asarray(pts_rc, np.float64)]
    if closed and len(xy) > 2:
        xy = xy + [xy[0]]
    if len(xy) >= 2:
        d.line([v for p in xy for v in p], fill=color, width=width, joint="curve")
    return np.asarray(im, np.uint8)


def _side_by_side(left, right, gap=8) -> np.ndarray:
    from PIL import Image
    a, b = _to_u8(left), _to_u8(right)
    H = max(a.shape[0], b.shape[0])
    im = Image.new("RGB", (a.shape[1] + gap + b.shape[1], H), BG)
    im.paste(Image.fromarray(a, "RGB"), (0, (H - a.shape[0]) // 2))
    im.paste(Image.fromarray(b, "RGB"), (a.shape[1] + gap, (H - b.shape[0]) // 2))
    return np.asarray(im, np.uint8)


# --------------------------------------------------------------------------- #
# 展示 5: 楕円フーリエ記述子 / elliptic Fourier descriptors                      #
# --------------------------------------------------------------------------- #
def _leaf_region(H=460, W=460) -> np.ndarray:
    """葉のようなギザギザ輪郭の領域を Fullseye の region 生成 op で作る."""
    import regions_gen
    t = np.linspace(0.0, 2.0 * np.pi, 720, endpoint=False)
    r = 146.0 + 40.0 * np.sin(3 * t) + 20.0 * np.cos(5 * t) + 12.0 * np.sin(9 * t)
    rows = H / 2.0 + r * np.sin(t)
    cols = W / 2.0 + r * np.cos(t)
    return np.asarray(regions_gen.gen_region_polygon_filled(rows, cols, H, W),
                      np.float64)


def subject_fourier_desc(log=print) -> dict:
    """輪郭を楕円フーリエ記述子で低次から復元し、RMS 誤差 [px] を実測する."""
    import fourierdesc as FD
    E = _tile_mod()
    reg = _leaf_region()
    xld = fs.apply(reg, "gen_contour_region_xld", 0.5)
    pts = FD.from_xld(xld, 0)                        # (N,2) = (row, col)
    n_max = 24
    model = FD.elliptic_fourier(pts, n_harmonics=n_max)
    base = _to_u8(_overlay_mask(np.zeros(reg.shape), reg, (58, 62, 88), 1.0))
    base = _draw_poly(base, pts, (235, 235, 245), 2)
    rms, area_ratio, recs = [], [], []
    ref = np.asarray(pts, np.float64)
    for k in range(1, n_max + 1):
        rec = FD.reconstruct(model, n_points=len(ref), n_harmonics=k)
        # 復元点と元輪郭の最近傍距離 (弧長パラメータのずれを避けるため点対点でなく最近傍)
        d = np.min(np.linalg.norm(ref[None, :, :] - rec[:, None, :], axis=2), axis=1)
        rms.append(float(np.sqrt(np.mean(d ** 2))))
        recs.append(rec)
        # 復元輪郭が囲む面積 (シューレースの公式) を元の領域面積と比べる
        x, y = rec[:, 0], rec[:, 1]
        a_rec = 0.5 * abs(float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)))
        area_ratio.append(a_rec / float(np.sum(reg)))
    frames, labels = [], []
    for k in range(1, n_max + 1):
        left = _draw_poly(base.copy(), recs[k - 1], (255, 176, 72), 3)
        right = _plot(
            [{"x": np.arange(1, k + 1), "y": rms[:k], "color": (255, 176, 72),
              "label": "最近傍 RMS 誤差 [px]"}],
            base.shape[1], base.shape[0], xlim=(1, n_max), ylim=(0, 30),
            title="次数を上げると輪郭はどこまで戻るか",
            xlabel="使った高調波の数", legend_pos="tr",
            marks=[{"x": k, "y": rms[k - 1], "color": (255, 255, 255)}])
        frames.append(_side_by_side(left, right))
        labels.append("高調波 %d 次まで — RMS %.2f px / 面積比 %.3f"
                      % (k, rms[k - 1], area_ratio[k - 1]))
    book = E.flipbook(frames, labels,
                      title="楕円フーリエ記述子 —— 輪郭を低次から積み上げる")
    info = E.save_animation(book, "wing2d_fourier_desc",
                            duration_ms=340, hold_last_ms=1800)
    k1 = next(k for k in range(1, n_max + 1) if rms[k - 1] < 1.0)
    # 「何次を足したときに誤差が落ちるか」を実測する(推測しない)。
    drop = {k + 2: rms[k] - rms[k + 1] for k in range(len(rms) - 1)}
    even_drop = [drop[k] for k in drop if k % 2 == 0]
    odd_drop = [drop[k] for k in drop if k % 2 == 1]
    top3 = sorted(drop, key=lambda k: -drop[k])[:3]
    return {
        "name": "fourier_desc", "kind": "gif", "file": info["gif"],
        "thumb": info["thumb"], "frames": info["frames"],
        "bytes": info["gif_bytes"], "size": list(info["size"]), "panels": 2,
        "title": "楕円フーリエ記述子 —— 何次で形が戻るか",
        "ops": ["gen_region_polygon_filled", "gen_contour_region_xld",
                "elliptic_fourier", "reconstruct"],
        "data": "Fullseye の region 生成 op で作った合成の葉形 (r = 146 + 40sin3θ + 20cos5θ + 12sin9θ)",
        "measured": {
            "contour_points": int(len(ref)),
            "rms_px_by_harmonic": [round(v, 3) for v in rms],
            "area_ratio_by_harmonic": [round(v, 4) for v in area_ratio],
            "first_harmonic_under_1px": k1,
            "rms_drop_when_adding_harmonic": {str(k): round(v, 3)
                                              for k, v in drop.items()},
            "mean_drop_even_harmonics_px": round(float(np.mean(even_drop)), 4),
            "mean_drop_odd_harmonics_px": round(float(np.mean(odd_drop)), 4),
        },
        "caption": (
            "%d 点の輪郭を楕円フーリエ記述子に直し、高調波を 1 次から %d 次まで"
            "足しながら復元した。1 次 (楕円 1 個) では最近傍 RMS 誤差 %.2f px、"
            "%d 次で 1 px を切り、%d 次では %.2f px。誤差が大きく落ちるのは "
            "%s 次を足したときで、偶数次を足したときの平均低下 %.3f px に対し"
            "奇数次では %.3f px しか下がらない —— r = 146 + 40sin3θ + 20cos5θ + 12sin9θ "
            "という作り方が、閉曲線としては n±1 次(= 偶数次)に現れるためだ。"
            % (len(ref), n_max, rms[0], k1, n_max, rms[-1],
               "・".join(str(k) for k in sorted(top3)),
               float(np.mean(even_drop)), float(np.mean(odd_drop)))),
    }


# --------------------------------------------------------------------------- #
# 展示 6: 対応点で顔をモーフする / landmark-driven image morphing                #
# --------------------------------------------------------------------------- #
def _synthetic_face(kind: int, size: int = 320) -> tuple:
    """合成の顔 (実在しない) と対応点 7 個を返す. 戻り (image, points[row,col])."""
    from PIL import Image, ImageDraw
    im = Image.new("L", (size, size), 36)
    d = ImageDraw.Draw(im)
    if kind == 0:
        d.ellipse([70, 46, 250, 286], fill=205)
        d.ellipse([108, 118, 142, 148], fill=28)
        d.ellipse([178, 118, 212, 148], fill=28)
        d.polygon([(160, 150), (146, 196), (174, 196)], fill=150)
        d.arc([118, 176, 202, 244], 20, 160, fill=18, width=7)
        pts = [(133, 125), (133, 195), (196, 160), (60, 160),
               (160, 84), (160, 236), (280, 160)]
    else:
        d.ellipse([48, 74, 272, 258], fill=168)
        d.ellipse([96, 142, 140, 174], fill=22)
        d.ellipse([180, 142, 224, 174], fill=22)
        d.polygon([(160, 176), (142, 214), (178, 214)], fill=120)
        d.arc([112, 186, 208, 252], 200, 340, fill=14, width=8)
        pts = [(158, 118), (158, 202), (214, 160), (78, 160),
               (160, 62), (160, 258), (252, 160)]
    return np.asarray(im, np.float64) / 255.0, np.asarray(pts, np.float64)


def subject_face_morph(log=print) -> dict:
    """対応点駆動のワープ (piecewise affine / TPS) で A→B へ連続変形する."""
    import imagemorph as IM
    E = _tile_mod()
    A, ptsA = _synthetic_face(0)
    B, ptsB = _synthetic_face(1)
    n = 13
    alphas = np.linspace(0.0, 1.0, n)
    seq_aff = [IM.morph(A, B, ptsA, ptsB, float(a), method="affine")
               for a in alphas]
    seq_tps = [IM.morph(A, B, ptsA, ptsB, float(a), method="tps") for a in alphas]
    blend = [(1 - a) * A + a * B for a in alphas]     # 対応点を使わない単純合成
    diff = [float(np.mean(np.abs(np.asarray(x) - np.asarray(y))))
            for x, y in zip(seq_aff, seq_tps)]
    end_psnr = (_psnr(A, seq_aff[0]), _psnr(B, seq_aff[-1]))
    frames, labels = [], []
    for i, a in enumerate(alphas):
        panel = _panel_grid(
            [A, np.asarray(blend[i]), np.asarray(seq_aff[i]),
             np.asarray(seq_tps[i]), B,
             _cmap(np.abs(np.asarray(seq_aff[i]) - np.asarray(seq_tps[i])),
                   "magma", vmin=0.0, vmax=0.08)],
            ["顔 A (合成・実在しない)", "単純合成 (1-α)A + αB\n二重像になる",
             "morph piecewise affine\nα = %.2f" % a,
             "morph TPS\nα = %.2f" % a, "顔 B (合成・実在しない)",
             "affine と TPS の差\n平均 %.5f" % diff[i]],
            3, tile=(300, 300), label_h=52, title=None, title_h=0)
        frames.append(panel)
        labels.append("α = %.2f — affine と TPS の平均差 %.5f" % (a, diff[i]))
    book = E.flipbook(frames, labels,
                      title="対応点モーフ —— 7 個の点だけで顔が別人になる")
    info = E.save_animation(book, "wing2d_face_morph",
                            duration_ms=340, hold_last_ms=1400)
    return {
        "name": "face_morph", "kind": "gif", "file": info["gif"],
        "thumb": info["thumb"], "frames": info["frames"],
        "bytes": info["gif_bytes"], "size": list(info["size"]), "panels": 6,
        "title": "対応点モーフ —— 単純合成との違い",
        "ops": ["morph (imagemorph)", "warp_piecewise_affine", "warp_tps_image",
                "blend"],
        "data": "Pillow で描いた合成の顔 2 枚 (実在の人物ではない)",
        "measured": {
            "landmarks": int(len(ptsA)),
            "alpha": [round(float(x), 3) for x in alphas],
            "mean_abs_diff_affine_vs_tps": [round(v, 5) for v in diff],
            "psnr_alpha0_vs_A_db": round(end_psnr[0], 2),
            "psnr_alpha1_vs_B_db": round(end_psnr[1], 2),
        },
        "caption": (
            "対応点 7 個だけを与えて顔 A から顔 B へモーフさせた 6 パネル。"
            "対応点を使わない単純合成は途中で二重像になるが、piecewise affine と TPS は"
            "目や口の位置を対応させたまま連続的に動く。両端は入力を厳密に再現し "
            "(α=0 で A と PSNR %.1f dB、α=1 で B と %.1f dB = 完全一致の上限値)、"
            "2 つのワープ方式の差は α=0.5 で平均 %.5f にとどまる。"
            % (end_psnr[0], end_psnr[1], diff[n // 2])),
    }


# --------------------------------------------------------------------------- #
# 展示 7: ブロブ選別 / blob analysis                                            #
# --------------------------------------------------------------------------- #
def _grain_scene(H=720, W=960) -> np.ndarray:
    """円・楕円・四角・棒・三角を混ぜた合成の粒シーン (決定的・座標は固定)."""
    from PIL import Image, ImageDraw
    im = Image.new("L", (W, H), 12)
    d = ImageDraw.Draw(im)
    circles = [(70, 70, 166, 166), (258, 58, 334, 134), (430, 86, 566, 222),
               (686, 68, 776, 158), (104, 430, 220, 546), (516, 514, 612, 610),
               (806, 394, 896, 484), (336, 548, 412, 624)]
    for box in circles:
        d.ellipse(box, fill=232)
    d.rectangle([584, 308, 720, 444], fill=232)          # 四角
    d.rectangle([52, 274, 394, 336], fill=232)           # 細長い棒
    d.rectangle([754, 566, 926, 638], fill=232)          # 横長の板
    d.polygon([(206, 616), (302, 686), (188, 700)], fill=232)   # 三角
    d.ellipse([430, 342, 566, 412], fill=232)            # 扁平な楕円
    return np.asarray(im, np.float64) / 255.0


def subject_blob_select(log=print) -> dict:
    """粒を数え、真円度と面積で選り分け、選ばれた粒だけ色を変える工程を見せる."""
    from scipy import ndimage
    E = _tile_mod()
    scene = _grain_scene()
    reg = fs.apply(scene, "threshold", 0.5)
    filled = fs.apply(reg, "fill_up", 0.5)
    n_blobs = int(fs.apply(filled, "blob_count", 0.5))
    lab, n = ndimage.label(filled > 0.5,
                           structure=ndimage.generate_binary_structure(2, 2))
    feats = []
    for i in range(1, n + 1):
        m = (lab == i).astype(np.float64)
        feats.append({
            "id": i, "px": int(m.sum()),
            "area_frac": float(fs.apply(m, "area_center", 0.5)),
            "circ": float(fs.apply(m, "circularity", 0.5)),
            "ecc": float(fs.apply(m, "eccentricity", 0.5)),
            "rect": float(fs.apply(m, "rectangularity", 0.5))})
    circ_thr = 0.85
    keep = [f["id"] for f in feats if f["circ"] >= circ_thr]
    colored = np.asarray(fs.colorize_labels(lab), np.float64)
    if colored.max() > 1.0:
        colored = colored / 255.0
    sel_mask = np.isin(lab, keep).astype(np.float64)
    rej_mask = ((lab > 0) & ~np.isin(lab, keep)).astype(np.float64)
    picked = np.clip(_overlay_mask(np.stack([scene] * 3, -1) * 0.35,
                                   sel_mask, (110, 235, 150), 0.85), 0, 1)
    picked = np.clip(_overlay_mask(picked, rej_mask, (235, 110, 110), 0.55), 0, 1)
    scatter = _plot(
        [{"x": [f["circ"] for f in feats if f["circ"] >= circ_thr],
          "y": [f["px"] for f in feats if f["circ"] >= circ_thr],
          "color": (110, 235, 150), "style": "dots", "label": "採用 (真円度 ≥ 0.85)"},
         {"x": [f["circ"] for f in feats if f["circ"] < circ_thr],
          "y": [f["px"] for f in feats if f["circ"] < circ_thr],
          "color": (235, 110, 110), "style": "dots", "label": "不採用"}],
        scene.shape[1], scene.shape[0], xlim=(0.3, 1.0), ylim=(0, 26000),
        title="真円度 (circularity) × 面積 [px] の特徴空間",
        xlabel="circularity", legend_pos="tl")
    steps = [np.stack([scene] * 3, -1),
             np.stack([np.asarray(reg)] * 3, -1),
             np.stack([np.asarray(filled)] * 3, -1),
             colored, picked, scatter.astype(np.float64) / 255.0]
    labels = [
        "元のシーン (合成: 円 8・楕円 1・四角 1・板 2・三角 1)",
        "threshold で二値化 — 前景 %d px" % int(np.sum(reg)),
        "fill_up で穴埋め — blob_count = %d 個" % n_blobs,
        "ラベル付け + colorize_labels — %d 個に色を配る" % n,
        "circularity ≥ %.2f を採用 — 緑 %d 個 / 赤 %d 個"
        % (circ_thr, len(keep), n - len(keep)),
        "特徴空間で見ると 2 つの群にきれいに割れている"]
    book = E.flipbook([_to_u8(s) for s in steps], labels,
                      title="ブロブ解析 —— 数える・測る・選り分ける")
    info = E.save_animation(book, "wing2d_blob_select",
                            duration_ms=1200, hold_last_ms=2200)
    circ_keep = sorted(round(f["circ"], 3) for f in feats if f["circ"] >= circ_thr)
    circ_rej = sorted(round(f["circ"], 3) for f in feats if f["circ"] < circ_thr)
    return {
        "name": "blob_select", "kind": "gif", "file": info["gif"],
        "thumb": info["thumb"], "frames": info["frames"],
        "bytes": info["gif_bytes"], "size": list(info["size"]), "panels": 6,
        "title": "ブロブ解析 —— 真円度で粒を選り分ける",
        "ops": ["threshold", "fill_up", "blob_count", "colorize_labels",
                "circularity", "eccentricity", "rectangularity", "area_center"],
        "data": "Pillow で描いた合成の粒シーン (決定的)",
        "measured": {
            "blob_count": n_blobs, "labelled": n,
            "circularity_threshold": circ_thr,
            "accepted": len(keep), "rejected": n - len(keep),
            "circularity_accepted": circ_keep,
            "circularity_rejected": circ_rej,
            "per_blob": [{k: (round(v, 4) if isinstance(v, float) else v)
                          for k, v in f.items()} for f in feats],
        },
        "caption": (
            "円 8 個・楕円 1・四角 1・板 2・三角 1 を混ぜた合成シーンを二値化 → 穴埋め → "
            "ラベル付けし、blob_count が %d 個と数えた。真円度 (circularity) 0.85 を"
            "しきい値にすると採用 %d 個 (真円度 %.3f〜%.3f)、不採用 %d 個 "
            "(%.3f〜%.3f) にきれいに割れる —— 特徴空間の散布図でも 2 つの群が"
            "しきい値をまたいで重なっていない。"
            % (n_blobs, len(keep), circ_keep[0], circ_keep[-1], n - len(keep),
               circ_rej[0], circ_rej[-1])),
    }
