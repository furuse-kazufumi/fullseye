# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gen_science_gallery — Qiita 記事用「科学館ギャラリー」画像の生成.
Generate "science-museum" gallery images for the Qiita article.

目的(かみくだき) / Purpose:
  子供が見てわくわくする科学画像を fullseye の**登録 op を実際に実行して**作る。
  モックアップ禁止(honest disclosure 規律)。各画像のメタ(使用 op / データ来歴 /
  合成か実データか)を JSON に記録し、記事貼付け用スニペットを自動生成する。

生成物 / Outputs (docs/articles/assets/):
  science_*.png / science_*.gif       -- フルサイズ画像
  science_*_thumb.jpg                 -- 幅 720px サムネ (JPEG q85; GIF はサムネなし)
  _science_gallery_meta.json          -- 使用 op・キャプション・来歴のメタ
  _science_gallery_snippet.md         -- GALLERY.md 追記行 + 記事挿入候補
                                         (GALLERY.md / 記事 md 本体は編集しない)

Run:
  py -3.11 tools/gen_science_gallery.py                    # 全 subject
  py -3.11 tools/gen_science_gallery.py --subjects fourier_stars,alife_worlds
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import fullseye as fs  # noqa: E402

ASSETS_DIR = os.path.join(REPO, "docs", "articles", "assets")
SAMPLES_IMG = os.path.join(REPO, "studio_assets", "sample_images")
SAMPLES_DL = os.path.join(os.environ.get("LOCALAPPDATA", ""), "fullseye", "samples")
META_PATH = os.path.join(ASSETS_DIR, "_science_gallery_meta.json")
SNIPPET_PATH = os.path.join(ASSETS_DIR, "_science_gallery_snippet.md")
RAW_BASE = ("https://raw.githubusercontent.com/furuse-kazufumi/fullseye/"
            "master/docs/articles/assets/")

SEED = 20260830
THUMB_WIDTH = 720
FONT_PATH = r"C:\Windows\Fonts\meiryo.ttc"


# --------------------------------------------------------------------------- #
# 共通ヘルパ / shared helpers                                                   #
# --------------------------------------------------------------------------- #
def _load_gray(name: str) -> np.ndarray:
    """studio_assets/sample_images の画像を float64 [0,1] グレイで読む."""
    img = fs.to_float01(fs.load(os.path.join(SAMPLES_IMG, name)))
    if img.ndim == 3:
        img = fs.apply(img, "rgb1_to_gray")
    return np.asarray(img, np.float64)


def _cmap(gray: np.ndarray, name: str) -> np.ndarray:
    """matplotlib カラーマップで可視化 (処理でなく着色のみ). 戻り HxWx3 [0,1]."""
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import cm
    g = np.clip(np.asarray(gray, np.float64), 0.0, 1.0)
    return np.asarray(cm.get_cmap(name)(g)[..., :3], np.float64)


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


def _save_gif(frames_u8: list, filename: str, fps: int = 8) -> str:
    """PIL でループ GIF. 4MB 目安を超えたら色数を落として再エンコード."""
    from PIL import Image
    path = os.path.join(ASSETS_DIR, filename)
    for colors in (256, 128, 64):
        pil = [Image.fromarray(f, "RGB").convert(
            "P", palette=Image.ADAPTIVE, colors=colors) for f in frames_u8]
        pil[0].save(path, save_all=True, append_images=pil[1:],
                    duration=int(1000 / fps), loop=0, optimize=True)
        if os.path.getsize(path) <= 4 * 1024 * 1024:
            break
    return path


def _font(size: int):
    from PIL import ImageFont
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception:
        return ImageFont.load_default()


def _montage(panels: list, labels: list | None = None, ncols: int = 3,
             pad: int = 10, bg=(12, 12, 20), label_h: int = 34,
             font_size: int = 20) -> np.ndarray:
    """パネル (HxWx3 float [0,1]) をグリッドに並べ、下にラベル帯を付ける.
    戻り HxWx3 float [0,1]."""
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


def _hsv_to_rgb(h: np.ndarray, s: np.ndarray, v: np.ndarray) -> np.ndarray:
    from matplotlib.colors import hsv_to_rgb
    return hsv_to_rgb(np.stack([np.clip(h, 0, 1) % 1.0,
                                np.clip(s, 0, 1), np.clip(v, 0, 1)], axis=-1))


def _load_mesh_sample(which: str):
    """DL 済み samples キャッシュからメッシュを読む.
    GLB (triceratops) のみ trimesh で三角形化 (読取専用; 処理は fullseye op)."""
    path = os.path.join(SAMPLES_DL, which)
    if which.endswith(".glb"):
        import trimesh
        scene = trimesh.load(path)
        mesh = (scene.to_mesh() if hasattr(scene, "to_mesh")
                else scene)
        V = np.asarray(mesh.vertices, np.float64)
        F = np.asarray(mesh.faces, np.int64)
    else:
        V, F = fs.read_mesh(path)
    return V, F


def _lambert(normals: np.ndarray, sil: np.ndarray,
             light=(0.4, 0.5, 0.75), ambient: float = 0.25) -> np.ndarray:
    """render_mesh の法線からシンプルな陰影 (可視化のみ)."""
    L = np.asarray(light, np.float64)
    L = L / np.linalg.norm(L)
    n = np.nan_to_num(np.asarray(normals, np.float64))
    d = np.clip((n * L).sum(axis=-1), 0.0, 1.0)
    shade = ambient + (1.0 - ambient) * d
    return np.where(sil > 0.5, shade, 0.0)


# --------------------------------------------------------------------------- #
# subjects                                                                    #
# --------------------------------------------------------------------------- #
def subject_distance_ripple(log=print) -> dict:
    """距離変換の虹の波紋 — コイン写真の白黒化 → 各点から形までの距離を虹色に."""
    img = _load_gray("coins.png")
    seg = fs.apply(img, "otsu")
    seg = fs.apply(seg, "fill_up")
    dt_in = fs.apply(seg, "distance_transform")          # コイン内部: 中心ほど遠い
    dt_out = fs.apply(1.0 - seg, "distance_transform")   # 背景: コインから離れるほど遠い
    field = np.where(seg > 0.5, dt_in, dt_out)
    # 波紋の等高線: 距離の縞を cos で作り、色の明度を揺らす
    rings = 0.75 + 0.25 * np.cos(field * 24.0 * np.pi)
    color = _cmap(field, "turbo") * rings[..., None]
    panels = [np.stack([img] * 3, -1), np.stack([seg] * 3, -1), color]
    out = _montage(panels, ["元の写真 (コイン)", "白黒に分ける (otsu)",
                            "ふちからの距離を虹色に"], ncols=3)
    _save_png(out, "science_distance_ripple.png")
    _save_thumb("science_distance_ripple.png")
    return {
        "file": "science_distance_ripple.png",
        "title": "距離変換の虹の波紋",
        "ops": ["otsu", "fill_up", "distance_transform"],
        "data": "skimage.data coins (実写真)",
        "synthetic": False,
        "caption": ("コインの写真を白黒に分け、「ふちから何ピクセル離れているか」を"
                    "虹色で塗ると、波紋のような等高線が浮かび上がる。"),
    }


def subject_fourier_stars(log=print) -> dict:
    """フーリエの世界 — 画像を「周波数」で見ると星が現れる."""
    cam = _load_gray("camera.png")
    weave = _load_gray("weave_synth.png")
    spec_cam = fs.apply(cam, "fft_image")
    spec_weave = fs.apply(weave, "fft_image")
    panels = [np.stack([cam] * 3, -1), _cmap(spec_cam, "inferno"),
              np.stack([weave] * 3, -1), _cmap(spec_weave, "inferno")]
    out = _montage(panels, ["ふつうの写真", "その周波数の姿 (fft_image)",
                            "布の織り目 (合成テクスチャ)", "規則的な模様は星になる"],
                   ncols=2)
    _save_png(out, "science_fourier_stars.png")
    _save_thumb("science_fourier_stars.png")
    return {
        "file": "science_fourier_stars.png",
        "title": "フーリエの世界 — 画像を周波数で見る",
        "ops": ["fft_image"],
        "data": "skimage.data camera (実写真) + fullseye synth 織り目 (合成)",
        "synthetic": "織り目パネルのみ合成",
        "caption": ("画像をフーリエ変換すると「どんな細かさの模様がどの向きに入って"
                    "いるか」が光の点になって見える。規則正しい織り目は星座のように光る。"),
    }


def subject_watershed_foam(log=print) -> dict:
    """watershed の色分け — コインの領域が泡のように分かれる."""
    img = _load_gray("coins.png")
    seg = fs.apply(img, "otsu")
    seg = fs.apply(seg, "fill_up")
    dt = fs.apply(1.0 - seg, "distance_transform")   # コインからの距離 (背景側)
    ridges = fs.apply(dt, "watersheds")              # 尾根線 = なわばりの境界
    cells = (ridges < 0.5).astype(np.float64)
    objs = fs.segment_objects(cells, threshold=0.5, min_area=30)
    lab = np.zeros(img.shape, np.int32)
    for i, o in enumerate(objs):
        lab[o["mask"] > 0] = i + 1
    colors = fs.colorize_labels(lab, seed=SEED)
    vis = 0.45 * np.stack([img] * 3, -1) + 0.55 * colors
    vis = np.where((ridges > 0.5)[..., None], 1.0, vis)   # 境界線は白
    panels = [np.stack([img] * 3, -1), vis]
    out = _montage(panels, ["元の写真 (コイン)",
                            "各コインの「なわばり」を watershed で色分け"], ncols=2)
    _save_png(out, "science_watershed_foam.png")
    _save_thumb("science_watershed_foam.png")
    return {
        "file": "science_watershed_foam.png",
        "title": "watershed — コインのなわばり地図",
        "ops": ["otsu", "fill_up", "distance_transform", "watersheds",
                "segment_objects", "colorize_labels"],
        "data": "skimage.data coins (実写真)",
        "synthetic": False,
        "caption": ("水が低いところへ流れて溜まるように領域を分ける watershed 法。"
                    "どのコインに一番近いかで平面が泡のように分割される。"),
    }


def subject_edge_compass(log=print) -> dict:
    """エッジの方位磁針 — 輪郭の向きを色相で塗る."""
    cam = _load_gray("camera.png")
    amp = fs.apply(cam, "sobel_amp")
    direc = fs.apply(cam, "sobel_dir")
    v = np.clip(amp * 3.0, 0.0, 1.0) ** 0.7          # 輪郭の強さ → 明るさ
    rgb = _hsv_to_rgb(direc, np.ones_like(direc), v)
    panels = [np.stack([cam] * 3, -1), rgb]
    out = _montage(panels, ["元の写真", "輪郭の「向き」を色で塗る (sobel_dir)"],
                   ncols=2)
    _save_png(out, "science_edge_compass.png")
    _save_thumb("science_edge_compass.png")
    return {
        "file": "science_edge_compass.png",
        "title": "エッジの方位磁針",
        "ops": ["sobel_amp", "sobel_dir"],
        "data": "skimage.data camera (実写真)",
        "synthetic": False,
        "caption": ("輪郭がどちらを向いているかを色相環の色で塗ると、"
                    "同じ向きの線が同じ色に光り、写真の骨組みが見えてくる。"),
    }


def subject_alife_worlds(log=print) -> dict:
    """人工生命の世界 — セル・オートマトンと反応拡散の 6 つの宇宙."""
    rng = np.random.default_rng(SEED)
    noise = rng.random((320, 320))
    # ウルフラム CA は中央 1 点から成長させるときれいな三角形 (ルール 90 相当)
    point = np.zeros((320, 320))
    point[0, 160] = 1.0
    spec = [
        ("alife_gray_scott", noise, 0.5, 0.5, "magma", "反応拡散 (グレイ=スコット)"),
        ("alife_turing", noise, 0.5, 0.5, "viridis", "チューリング模様"),
        ("alife_lenia", noise, 0.5, 0.5, "cividis", "レニア (連続的な人工生命)"),
        ("alife_dla", noise, 0.5, 0.5, "bone", "結晶成長 (DLA)"),
        ("alife_sandpile", noise, 0.5, 0.5, "plasma", "砂山くずし (自己組織化臨界)"),
        ("alife_wolfram1d", point, 90.0 / 255.0, 0.5, "afmhot",
         "1 次元セル・オートマトン"),
    ]
    panels, labels, ops = [], [], []
    for op, src, a, b, cmap, label in spec:
        res = fs.apply(src, op, a, b)
        panels.append(_cmap(res, cmap))
        labels.append(label)
        ops.append(op)
    out = _montage(panels, labels, ncols=3)
    _save_png(out, "science_alife_worlds.png")
    _save_thumb("science_alife_worlds.png")
    return {
        "file": "science_alife_worlds.png",
        "title": "人工生命の 6 つの宇宙",
        "ops": ops,
        "data": "乱数ノイズ / 1 点から成長 (シミュレーション)",
        "synthetic": True,
        "caption": ("単純なルールを繰り返すだけで、ヒョウ柄・生き物・結晶・雪崩・"
                    "フラクタルが勝手に生まれる。全部 fullseye の op 1 回ずつ。"),
    }


def subject_dino_xray(log=print) -> dict:
    """恐竜のレントゲン — トリケラトプス実スキャンをボクセル化して MIP."""
    V, F = _load_mesh_sample("triceratops.glb")
    # 実寸を [0,1] 立方体に正規化してからボクセル化 (格子を ~256 に抑える)
    V = V - V.min(axis=0)
    V = V / V.max()
    pitch = 1.0 / 240.0
    vol, _origin = fs.voxelize_solid(V, F, pitch)
    vol = np.asarray(vol, np.float64)
    log(f"  voxel grid: {vol.shape}")
    views = []
    for axes, name in [((0, 1, 2), "上から"), ((1, 0, 2), "横から"),
                       ((2, 0, 1), "正面から")]:
        v = np.transpose(vol, axes)
        mip = fs.apply(v, "vol_mip")
        views.append((mip, name))
    # レントゲン風: 白い骨 + 青黒い背景 (bone カラーマップ)
    panels, labels = [], []
    for mip, name in views:
        blur = fs.apply(mip, "gauss_filter", 0.15, 0.5)  # フィルムのにじみ
        x = np.clip(0.35 * blur + 0.65 * mip, 0, 1)
        panels.append(_cmap(x, "bone"))
        labels.append(name)
    out = _montage(panels, labels, ncols=3)
    _save_png(out, "science_dino_xray.png")
    _save_thumb("science_dino_xray.png")
    return {
        "file": "science_dino_xray.png",
        "title": "トリケラトプスのレントゲン写真",
        "ops": ["voxelize_solid", "vol_mip", "gauss_filter"],
        "data": "Smithsonian 3D triceratops 実スキャン (CC0)",
        "synthetic": False,
        "caption": ("スミソニアン博物館の実スキャンをボクセル(3D のピクセル)に詰め、"
                    "最大値投影 (MIP) するとレントゲン写真そっくりになる。"),
    }


def subject_dragon_anaglyph(log=print) -> dict:
    """赤青メガネで飛び出すドラゴン — 2 視点レンダのアナグリフ."""
    V, F = _load_mesh_sample("dragon.ply")
    V = V - V.mean(axis=0)
    scale = np.abs(V).max()
    V = V / scale
    size = 640
    # 左右の目: わずかに横にずらした 2 台のカメラ
    dist = 2.4
    sep = 0.055
    imgs = {}
    for eye, dx in (("L", -sep), ("R", +sep)):
        pose = fs.look_at((dx * dist, -dist, 0.35 * dist), (0.0, 0.0, 0.0),
                          up=(0.0, 0.0, 1.0))
        r = fs.render_mesh(V, F, pose=pose, width=size, height=size)
        shade = _lambert(r["normals"], r["silhouette"])
        imgs[eye] = shade
    ana = np.zeros((size, size, 3))
    ana[..., 0] = imgs["L"]                 # 左目 → 赤
    ana[..., 1] = imgs["R"]                 # 右目 → 緑
    ana[..., 2] = imgs["R"]                 # 右目 → 青 (シアン)
    _save_png(ana, "science_dragon_anaglyph.png")
    _save_thumb("science_dragon_anaglyph.png")
    return {
        "file": "science_dragon_anaglyph.png",
        "title": "赤青メガネで飛び出すドラゴン",
        "ops": ["read_mesh", "look_at", "render_mesh"],
        "data": "Stanford dragon 実スキャン",
        "synthetic": False,
        "caption": ("左目用と右目用、少しずらした 2 枚を赤とシアンで重ねたアナグリフ。"
                    "赤青メガネをかけると龍が画面から浮き上がる。"),
    }


def subject_dino_terrain(log=print) -> dict:
    """恐竜を山脈にする — 点群 → 標高マップ → 地形の陰影着色."""
    V, F = _load_mesh_sample("triceratops.glb")
    V = V - V.min(axis=0)
    V = V / V.max()
    pts = fs.sample_surface(V, F, 400_000, seed=SEED)
    # glTF は y-up なので z-up に回す (高さ = 体の上面)
    pts = pts[:, [0, 2, 1]]
    grid, extent = fs.elevation_map(pts, cell=1.0 / 420.0, agg="max")
    grid = np.nan_to_num(grid, nan=float(np.nanmin(grid)))
    rgb = fs.colorize_height(grid, name="terrain", relief=True)
    _save_png(rgb, "science_dino_terrain.png")
    _save_thumb("science_dino_terrain.png")
    return {
        "file": "science_dino_terrain.png",
        "title": "トリケラトプス山脈 — 恐竜を地図にする",
        "ops": ["sample_surface", "elevation_map", "colorize_height"],
        "data": "Smithsonian 3D triceratops 実スキャン (CC0)",
        "synthetic": False,
        "caption": ("恐竜の実スキャンを 40 万点の点群にして真上から標高地図を作ると、"
                    "背中が山脈、フリルが台地になる。ロボットが地形を読むのと同じ op。"),
    }


def subject_morph_pulse(log=print) -> dict:
    """形が育つ・痩せる — 膨張と収縮のアニメ GIF."""
    img = _load_gray("coins.png")
    seg = fs.apply(img, "otsu")
    seg = fs.apply(seg, "fill_up")
    frames = []
    n_steps = 14
    # 育つ (dilation) → 痩せる (erosion) の往復
    seq = ([("dilation_circle", a) for a in np.linspace(0.02, 0.55, n_steps)]
           + [("erosion_circle", a) for a in np.linspace(0.02, 0.45, n_steps)])
    base = np.stack([img] * 3, -1) * 0.35
    for i, (op, a) in enumerate(seq):
        r = fs.apply(seg, op, float(a), 0.5)
        hue = (0.55 + 0.35 * i / len(seq)) % 1.0
        color = _hsv_to_rgb(np.full(img.shape, hue), np.full(img.shape, 0.85),
                            r)
        vis = np.where((r > 0.5)[..., None], 0.35 * base + 0.85 * color, base)
        frames.append(_to_u8(vis))
    frames += frames[-1:] * 3
    _save_gif(frames, "science_morph_pulse.gif", fps=7)
    return {
        "file": "science_morph_pulse.gif",
        "title": "形が育つ・痩せる (モルフォロジー)",
        "ops": ["otsu", "fill_up", "dilation_circle", "erosion_circle"],
        "data": "skimage.data coins (実写真)",
        "synthetic": False,
        "caption": ("膨張 (dilation) でコインがぷくぷく育って合体し、"
                    "収縮 (erosion) で痩せていく。工場の画像検査でも使う基本の op。"),
    }


def subject_wobble_warp(log=print) -> dict:
    """空間がぐにゃり — 3 種類の変形 op の before/after."""
    cam = _load_gray("camera.png")
    specs = [
        ("deform_tps", 0.85, 0.5, "薄板スプライン (TPS)"),
        ("deform_ffd", 0.85, 0.5, "自由形状変形 (FFD)"),
        ("deform_mls", 0.85, 0.5, "移動最小二乗 (MLS)"),
    ]
    panels = [np.stack([cam] * 3, -1)]
    labels = ["元の写真"]
    ops = []
    for op, a, b, label in specs:
        w = fs.apply(cam, op, a, b)
        panels.append(np.stack([w] * 3, -1))
        labels.append(label)
        ops.append(op)
    out = _montage(panels, labels, ncols=4)
    _save_png(out, "science_wobble_warp.png")
    _save_thumb("science_wobble_warp.png")
    return {
        "file": "science_wobble_warp.png",
        "title": "空間がぐにゃり — 3 つの変形アルゴリズム",
        "ops": ops,
        "data": "skimage.data camera (実写真)",
        "synthetic": False,
        "caption": ("画像の下に見えないゴムのシートがあると思って、"
                    "数学の異なる 3 つの流儀でつまんで引っぱった結果。"),
    }


def subject_dla_skeleton(log=print) -> dict:
    """樹枝状結晶とその骨格 — DLA 成長 + スケルトン抽出."""
    rng = np.random.default_rng(SEED)
    noise = rng.random((480, 480))
    dla = fs.apply(noise, "alife_dla", 0.7, 0.5)
    mask = (dla > 0.2).astype(np.float64)
    grown = fs.apply(mask, "dilation_circle", 0.03, 0.5)
    skel = fs.apply(grown, "sk_skeleton")
    # 氷の結晶 (青白) + 骨格 (金色)
    ice = _cmap(fs.apply(grown, "distance_transform"), "ice"
                if _has_cmap("ice") else "winter")
    vis = np.where((grown > 0.5)[..., None], ice * 0.9 + 0.1, 0.02)
    gold = np.array([1.0, 0.82, 0.25])
    vis = np.where((skel > 0.5)[..., None], gold, vis)
    panels = [_cmap(grown, "bone"), vis]
    out = _montage(panels, ["拡散で育った結晶 (alife_dla)",
                            "その骨格を金色で抽出 (sk_skeleton)"], ncols=2)
    _save_png(out, "science_dla_skeleton.png")
    _save_thumb("science_dla_skeleton.png")
    return {
        "file": "science_dla_skeleton.png",
        "title": "樹枝状結晶とその骨格",
        "ops": ["alife_dla", "dilation_circle", "sk_skeleton",
                "distance_transform"],
        "data": "乱数から DLA 成長 (シミュレーション)",
        "synthetic": True,
        "caption": ("粒子がふらふら漂って張り付くだけで雪の結晶のような枝が育つ "
                    "(DLA)。スケルトン化するとその「骨」が 1 ピクセル幅で取り出せる。"),
    }


def _has_cmap(name: str) -> bool:
    try:
        from matplotlib import cm
        cm.get_cmap(name)
        return True
    except Exception:
        return False


SUBJECTS = {
    "distance_ripple": subject_distance_ripple,
    "fourier_stars": subject_fourier_stars,
    "watershed_foam": subject_watershed_foam,
    "edge_compass": subject_edge_compass,
    "alife_worlds": subject_alife_worlds,
    "dino_xray": subject_dino_xray,
    "dragon_anaglyph": subject_dragon_anaglyph,
    "dino_terrain": subject_dino_terrain,
    "morph_pulse": subject_morph_pulse,
    "wobble_warp": subject_wobble_warp,
    "dla_skeleton": subject_dla_skeleton,
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
        "<!-- gen_science_gallery.py が自動生成。GALLERY.md / 記事 md への",
        "     追記候補 (このファイル自体は記事ではない)。 -->",
        "",
        "# 科学ギャラリー追加分 — GALLERY.md 追記行 + 記事挿入候補",
        "",
        "## GALLERY.md 追記行",
        "",
    ]
    for m in meta:
        thumb = os.path.splitext(m["file"])[0] + "_thumb.jpg"
        is_gif = m["file"].endswith(".gif")
        shown = m["file"] if is_gif else thumb
        lines.append(f"| {m['title']} | ![{m['title']}](assets/{shown}) | "
                     f"{', '.join(m['ops'])} | {m['data']} |")
    lines += ["", "## 記事挿入候補 (raw GitHub URL)", ""]
    for m in meta:
        thumb = os.path.splitext(m["file"])[0] + "_thumb.jpg"
        is_gif = m["file"].endswith(".gif")
        shown = m["file"] if is_gif else thumb
        lines.append(f"### {m['title']}")
        lines.append("")
        lines.append(f"![{m['title']}]({RAW_BASE}{shown})")
        if not is_gif:
            lines.append("")
            lines.append(f"(フル解像度: {RAW_BASE}{m['file']} )")
        lines.append("")
        note = ""
        if m.get("synthetic") is True:
            note = "※シミュレーション画像 (実写ではない)。"
        elif isinstance(m.get("synthetic"), str):
            note = f"※{m['synthetic']}。"
        lines.append(f"{m['caption']}{note} 使用 op: {', '.join(m['ops'])}。"
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
        print(f"[run ] {name}")
        try:
            meta = fn()
            results.append(meta)
            print(f"[done] {name} -> {meta['file']}")
        except Exception as e:  # honest: 失敗は隠さずログ
            import traceback
            traceback.print_exc()
            failures.append((name, str(e)))
            print(f"[FAIL] {name}: {e}")
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
