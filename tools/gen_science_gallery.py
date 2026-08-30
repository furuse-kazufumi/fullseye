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


def _resize_rgb(rgb: np.ndarray, size: int) -> np.ndarray:
    from PIL import Image
    im = Image.fromarray(_to_u8(rgb if rgb.ndim == 3
                                else np.stack([rgb] * 3, -1)), "RGB")
    im = im.resize((size, size), Image.LANCZOS)
    return np.asarray(im, np.float64) / 255.0


def subject_fourier_stars(log=print) -> dict:
    """フーリエの世界 — 画像を「周波数」で見ると星が現れる."""
    cam = _load_gray("camera.png")
    weave = _load_gray("weave_synth.png")
    spec_cam = fs.apply(cam, "fft_image")
    spec_weave = fs.apply(weave, "fft_image")
    S = 512
    panels = [_resize_rgb(np.stack([cam] * 3, -1), S),
              _resize_rgb(_cmap(spec_cam, "inferno"), S),
              _resize_rgb(np.stack([weave] * 3, -1), S),
              _resize_rgb(_cmap(spec_weave, "inferno"), S)]
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
    """watershed の色分け — コインを 1 枚ずつ切り分けてぬりえにする."""
    img = _load_gray("coins.png")[60:, :]     # 上端は照明ムラで二値化が荒れるため除外
    seg = fs.apply(img, "otsu")
    seg = fs.apply(seg, "fill_up")
    dt = fs.apply(1.0 - seg, "distance_transform")   # コインからの距離 (背景側)
    # dt をガンマ強調してからマーカー式 watershed: コインごとに独立の水源になる
    ridges = fs.apply(dt ** 0.3, "watersheds", 0.0, 0.5)
    cells = (ridges < 0.5).astype(np.float64) * seg   # コイン内部のみ色を塗る
    objs = fs.segment_objects(cells, threshold=0.5, min_area=80)
    lab = np.zeros(img.shape, np.int32)
    for i, o in enumerate(objs):
        lab[o["mask"] > 0] = i + 1
    colors = fs.colorize_labels(lab, seed=3)
    base = np.stack([img] * 3, -1)
    vis = np.where((lab > 0)[..., None], 0.45 * base + 0.65 * colors, base * 0.8)
    vis = np.where((ridges > 0.5)[..., None] & (seg > 0.5)[..., None], 1.0, vis)
    panels = [base, np.clip(vis, 0, 1)]
    out = _montage(panels, ["元の写真 (コイン)",
                            f"watershed で {len(objs)} 枚に切り分けて色分け"],
                   ncols=2)
    _save_png(out, "science_watershed_foam.png")
    _save_thumb("science_watershed_foam.png")
    return {
        "file": "science_watershed_foam.png",
        "title": "watershed — コインのぬりえ分割",
        "ops": ["otsu", "fill_up", "distance_transform", "watersheds",
                "segment_objects", "colorize_labels"],
        "data": "skimage.data coins (実写真)",
        "synthetic": False,
        "caption": ("水が低い所へ流れて溜まる様子をまねて領域を分ける watershed 法。"
                    "写真のコインが 1 枚ずつ別の色に塗り分けられる。"),
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


def _grow_dla(size: int, iters: int, rng) -> tuple[np.ndarray, np.ndarray]:
    """中央 1 点から DLA 樹枝を育てる (op を反復適用)。戻り (cluster, age)."""
    food = 0.28 * rng.random((size, size))     # 周囲の「栄養」= 拡散源
    cl = np.zeros((size, size))
    cl[size // 2, size // 2] = 1.0
    age = np.full((size, size), np.nan)
    age[cl > 0.5] = 0.0
    for i in range(1, iters + 1):
        inp = np.maximum(cl, food * (cl < 0.5))
        new = fs.apply(inp, "alife_dla", 1.0, 1.0)
        fresh = (new > 0.5) & (cl <= 0.5)
        age[fresh] = float(i)
        cl = new
    return cl, age


def subject_alife_worlds(log=print) -> dict:
    """人工生命の世界 — セル・オートマトン/自己組織化の 6 つの宇宙.

    honest note: alife op は 1 回の適用が数十ステップ相当なので、
    ここでは同じ op を**反復適用**して十分に発達させている (それでも
    「登録 op しか使わない」は守られる)。gray_scott / turing は反復しても
    このサイズでは絵にならなかったため不採用 (数合わせで載せない)。
    """
    rng = np.random.default_rng(SEED)
    S = 320
    zeros = np.zeros((S, S))
    # ルール 90 (index 1) = シェルピンスキー / ルール 30 (index 0) = カオス
    wolf90 = fs.apply(zeros, "alife_wolfram1d", 0.125, 0.0)
    wolf30 = fs.apply(zeros, "alife_wolfram1d", 0.0, 0.0)
    # 砂山くずし: 中央のなだらかな砂の山が、くずれて幾何学模様になる
    yy, xx = np.mgrid[0:S, 0:S]
    bump = np.exp(-(((yy - S / 2) ** 2 + (xx - S / 2) ** 2)
                    / (2 * (S / 5.0) ** 2)))
    sand = bump
    for _ in range(10):
        sand = fs.apply(sand, "alife_sandpile", 1.0, 1.0)
    # DLA 樹枝 (成長の順番で着色)。小さい格子で育てて 2 倍に拡大 = 枝が太く見える
    cl, age = _grow_dla(S // 2, 130, rng)
    cl = np.kron(cl, np.ones((2, 2)))
    age = np.kron(np.nan_to_num(age, nan=0.0), np.ones((2, 2)))
    t = age / max(1.0, float(age.max()))
    dla_rgb = _cmap(0.15 + 0.85 * t, "plasma") * (cl > 0.5)[..., None]
    # レニア: なめらかノイズから珊瑚状の微細組織へ
    lenia = fs.apply(rng.random((S, S)), "gauss_filter", 0.5, 0.5)
    for _ in range(15):
        lenia = fs.apply(lenia, "alife_lenia", 0.5, 1.0)
    # サイクリック CA: 色相環を「次の色に食べられる」ルール
    cyc = rng.random((S, S))
    for _ in range(120):
        cyc = fs.apply(cyc, "alife_cyclic_ca", 1.0, 1.0)
    panels = [
        _cmap(wolf90, "afmhot"),
        _cmap(wolf30, "GnBu_r"),
        _cmap(sand, "magma"),
        dla_rgb,
        _cmap(lenia, "viridis"),
        _hsv_to_rgb(cyc, np.full_like(cyc, 0.75), 0.35 + 0.65 * cyc),
    ]
    labels = ["ルール 90 → フラクタル", "ルール 30 → カオス",
              "砂山くずし (自己組織化臨界)", "拡散で育つ樹枝 (DLA)",
              "レニア (連続ライフゲーム)", "サイクリック CA"]
    out = _montage(panels, labels, ncols=3)
    _save_png(out, "science_alife_worlds.png")
    _save_thumb("science_alife_worlds.png")
    return {
        "file": "science_alife_worlds.png",
        "title": "単純ルールから生まれる 6 つの宇宙",
        "ops": ["alife_wolfram1d", "alife_sandpile", "alife_dla",
                "alife_lenia", "alife_cyclic_ca", "gauss_filter"],
        "data": "0 と乱数の初期値から反復シミュレーション",
        "synthetic": True,
        "caption": ("となりのマスを見て自分の色を決める——それだけのルールを"
                    "繰り返すと、フラクタル・カオス・結晶・珊瑚もようが勝手に生まれる。"),
    }


def subject_dino_xray(log=print) -> dict:
    """恐竜のレントゲン — トリケラトプス実スキャンをボクセル化して MIP."""
    V, F = _load_mesh_sample("triceratops.glb")
    # 実寸を単位箱に正規化してから骨の表面をボクセル化
    # (骨格標本なので表面ボクセル ≈ 骨そのもの)
    V = V - V.min(axis=0)
    V = V / V.max()
    pitch = 1.0 / 400.0
    vol, _origin = fs.voxelize(V, F, pitch)
    vol = np.asarray(vol, np.float64)
    log(f"  voxel grid: {vol.shape}")
    # 骨に厚みのにじみを与えてから最大値投影 → 濃淡のあるレントゲン調
    vol = fs.apply(vol, "vol_gaussian", 0.25, 0.5)
    # 格子は (z, y, x)。y-up モデルなので:
    #   横から = x 方向に投影 → (y, z)  /  上から = y 方向に投影 → (z, x)
    side = fs.apply(np.transpose(vol, (2, 1, 0)), "vol_mip")
    top = fs.apply(np.transpose(vol, (1, 0, 2)), "vol_mip")
    panels, labels = [], []
    for mip, name in [(side, "横から (X 線写真ふう)"), (top, "上から")]:
        x = np.clip(mip * 1.6, 0, 1) ** 0.8
        panels.append(_cmap(x, "bone"))
        labels.append(name)
    out = _montage(panels, labels, ncols=2)
    _save_png(out, "science_dino_xray.png")
    _save_thumb("science_dino_xray.png")
    return {
        "file": "science_dino_xray.png",
        "title": "トリケラトプスのレントゲン写真",
        "ops": ["voxelize", "vol_gaussian", "vol_mip"],
        "data": "Smithsonian 3D triceratops 骨格標本の実スキャン (CC0)",
        "synthetic": False,
        "caption": ("スミソニアン博物館の骨格標本スキャンをボクセル (3D のピクセル) に"
                    "詰め、最大値投影 (vol_mip) するとレントゲン写真そっくりになる。"),
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
        # Stanford メッシュは y-up。少し上から見下ろす正面ビュー
        pose = fs.look_at((dx * dist, 0.3 * dist, dist), (0.0, 0.0, 0.0),
                          up=(0.0, 1.0, 0.0))
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
    pts = fs.sample_surface(V, F, 600_000, seed=SEED)
    # glTF は y-up なので z-up に回す (高さ = 体の上面)。長軸を x に置いて横長の地図に
    pts = pts[:, [2, 0, 1]]
    grid, extent = fs.elevation_map(pts, cell=1.0 / 640.0, agg="max")
    grid = np.nan_to_num(grid, nan=float(np.nanmin(grid)))
    rgb = fs.colorize_height(grid, name="terrain", relief=True)
    rgb = np.kron(rgb, np.ones((2, 2, 1)))          # 表示用に 2 倍拡大
    _save_png(rgb, "science_dino_terrain.png")
    _save_thumb("science_dino_terrain.png")
    return {
        "file": "science_dino_terrain.png",
        "title": "トリケラトプス山脈 — 恐竜を地図にする",
        "ops": ["sample_surface", "elevation_map", "colorize_height"],
        "data": "Smithsonian 3D triceratops 骨格標本の実スキャン (CC0)",
        "synthetic": False,
        "caption": ("骨格標本の実スキャンを 60 万点の点群にして真上から標高地図を作る"
                    "と、背骨が山脈、ろっ骨が尾根になる。ロボットが地形を読むのと同じ op。"),
    }


def subject_morph_pulse(log=print) -> dict:
    """形が育つ・痩せる — 膨張と収縮のアニメ GIF."""
    img = _load_gray("coins.png")[60:, :]   # 上端の照明ムラを除外
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


def subject_dino_skeleton(log=print) -> dict:
    """恐竜の影絵と針金の骨格 — シルエット → スケルトン抽出."""
    V, F = _load_mesh_sample("triceratops.glb")
    V = V - V.mean(axis=0)
    V = V / np.abs(V).max()
    size = 720
    # glTF は y-up・長軸 z。真横 (+x) から見ると骨格標本の側面像になる
    pose = fs.look_at((2.6, 0.35, 0.0), (0.0, 0.0, 0.0), up=(0.0, 1.0, 0.0))
    r = fs.render_mesh(V, F, pose=pose, width=size, height=size)
    bones = np.asarray(r["silhouette"], np.float64)
    # 骨のすき間を閉じて「体の輪郭」にしてから中心線を取る
    sil = fs.apply(bones, "closing_circle", 0.10, 0.5)
    sil = fs.apply(sil, "fill_up")
    skel = fs.apply(sil, "sk_skeleton")
    skel_bold = fs.apply(skel, "dilation_circle", 0.010, 0.5)
    dt = fs.apply(sil, "distance_transform")
    body = _cmap(dt * 0.9, "bone")                  # 厚みで淡く光る影絵
    vis = np.where((sil > 0.5)[..., None], body * 0.45 + 0.06, 0.02)
    vis = np.where((bones > 0.5)[..., None],
                   np.array([0.55, 0.65, 0.85]), vis)   # 実際の骨は青白く
    gold = np.array([1.0, 0.8, 0.2])
    vis = np.where((skel_bold > 0.5)[..., None], gold, vis)
    panels = [np.where((bones > 0.5)[..., None],
                       np.array([0.85, 0.90, 1.0]), 0.03) * np.ones((1, 1, 3)),
              np.clip(vis, 0, 1)]
    out = _montage(panels, ["骨格標本スキャンの影絵 (render_mesh)",
                            "輪郭の中心線を金色で抽出 (sk_skeleton)"], ncols=2)
    _save_png(out, "science_dino_skeleton.png")
    _save_thumb("science_dino_skeleton.png")
    return {
        "file": "science_dino_skeleton.png",
        "title": "恐竜の影絵から骨格を取り出す",
        "ops": ["read_mesh", "look_at", "render_mesh", "closing_circle",
                "fill_up", "sk_skeleton", "dilation_circle",
                "distance_transform"],
        "data": "Smithsonian 3D triceratops 骨格標本の実スキャン (CC0)",
        "synthetic": False,
        "caption": ("トリケラトプス骨格標本の影絵から、形の中心線 (スケルトン) を"
                    "1 ピクセル幅で抽出。足・角・しっぽが針金細工のように残る。"),
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
    "dino_skeleton": subject_dino_skeleton,
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
