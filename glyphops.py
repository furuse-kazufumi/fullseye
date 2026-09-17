# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""グリフ照合 —— 画像に書かれた字が、**指定した字と合っているか**を測る。

★設計の要は「**認識をしない**」こと。画像生成 AI が壊した字を直す場面では、
**本当はこう書いてあるべき文字列**を人が持っている。だから 6000 通りの多クラス
分類(OCR)は要らず、各マスについて「この 1 字と合っているか」の 1 対 1 照合で済む。
分類器も学習も要らず、外れたときに**なぜ外れたか**を追える。

この方針の実測的な裏づけ(2026-09-17、Meiryo / MS ゴシック / 游ゴシック、26 字、
距離は骨格 chamfer の 99 パーセンタイル):

===============================  ======  ==========  ==========
量                               中央     95 %        最大
===============================  ======  ==========  ==========
書体雑音(同じ字・別書体)         0.0451   0.0668      0.0846
別字信号(別の字・同書体)         0.1542   ―           0.0734(最小)
===============================  ======  ==========  ==========

別字 378 対のうち**床(0.0668)を下回るものは 0 %**。閾値は勘で置かず、
:func:`typeface_noise_floor` が**書体雑音から導く**。

もう 1 つの要は **地域(日本/簡体/繁体)を推定しないこと**。同一設計の地域違い
(Noto Sans JP ↔ SC)で測ると、地域信号が書体雑音の 2 倍を超える字は常用漢字 93 字中
**ゼロ**で、``黄`` ``温`` ``戸`` などは**同一グリフ**を持つ(Unicode 統合の結果、
フォント側に区別が無い)。だから地域は**入力で受け取る**。検出側に地域推定は要らない
—— 「間違っているか」は指定ロケールの正しい描画と比べれば済む。

Pillow が要る(optional extra ``pil``)。フォントの解決と**豆腐(.notdef)の検出**は
:mod:`annotate` の実績のある実装を使い回す(私用領域 2 点で判定、追加依存なし)。
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

import annotate

__all__ = [
    "FONT_CANDIDATES", "available_fonts", "render_glyph", "render_text",
    "normalise_glyph", "skeleton_chamfer", "glyph_distance",
    "typeface_noise_floor", "rendering_noise_floor", "ink_colors",
    "edge_transition_width",
    "stroke_thickness", "match_stroke_weight", "replace_glyph",
    # ★2026-09-18: ここまで __all__ に無かった(api 側は名前で import していたので
    #   気づけなかった)。一次情報は __all__ なので、公開するものは全部書く。
    "split_cells", "correct_spec", "find_plate", "rewrite_line",
]

#: :mod:`annotate` と同じ探索順(CJK を持つものが先)。
FONT_CANDIDATES = annotate.FONT_CANDIDATES

#: 正規化したグリフの一辺。距離はこの一辺で割って返すので、値は解像度に依らない。
_NORM = 96


def available_fonts(paths=None) -> list:
    """実際に開けて **CJK が描ける**フォントだけを返す。

    ★「開けた」は「描ける」ではない —— 欠字は例外を出さず ``.notdef``(豆腐)を
    返す。実測では ``mingliub.ttc`` が index 0 で全部の漢字を豆腐にしており、
    それに気づいたのは 2 つの字の統計が**完全に一致**したからだった。
    """
    from PIL import ImageFont
    out = []
    for p in (FONT_CANDIDATES if paths is None else tuple(paths)):
        try:
            font = ImageFont.truetype(p, 48)
        except OSError:
            continue
        if not annotate._missing_glyphs(font, "山直電"):
            out.append(p)
    return out


def render_glyph(ch: str, font_path=None, size: int = 128, index: int = 0,
                 pad: float = 0.12) -> np.ndarray:
    """1 字を alpha (0..1, float64) で描く。中央合わせ。

    描けない字は**豆腐を返さず例外**にする(:func:`annotate._require_glyphs` と
    同じ方針)。黙って □ を返すと、下流の距離が「それらしい値」になって嘘をつく。
    """
    from PIL import Image, ImageDraw, ImageFont
    if len(ch) != 1:
        raise ValueError(f"render_glyph takes exactly one character (got {ch!r})")
    if font_path is None:
        cands = available_fonts()
        if not cands:
            raise RuntimeError(
                "no font on this machine can draw CJK — install one "
                "(Debian/Ubuntu: apt-get install fonts-noto-cjk) or pass font_path=")
        font_path = cands[0]
    font = ImageFont.truetype(font_path, int(size), index=int(index))
    annotate._require_glyphs(font, ch, font_path=font_path)
    canvas = int(size * (1.0 + 2.0 * pad))
    img = Image.new("L", (canvas, canvas), 0)
    ImageDraw.Draw(img).text((canvas / 2, canvas / 2), ch, fill=255, font=font, anchor="mm")
    return np.asarray(img, dtype=np.float64) / 255.0


def render_text(text: str, font_path=None, size: int = 128, index: int = 0) -> list:
    """文字列を**1 字 1 枚**で描く。空白は飛ばす(マスを持たないため)。"""
    return [render_glyph(c, font_path, size, index) for c in text if not c.isspace()]


def normalise_glyph(alpha: np.ndarray, out: int = _NORM, thresh: float = 0.5) -> np.ndarray:
    """外接箱で切り出し、**縦横比を保ったまま** ``out`` 角の中央に置く。

    ★比を潰してはいけない —— 潰すと「細長い字」と「正方の字」が同じ形になる。
    """
    from PIL import Image
    ink = np.asarray(alpha, np.float64) > thresh
    if not ink.any():
        return np.zeros((out, out), bool)
    ys, xs = np.where(ink)
    crop = np.asarray(alpha, np.float64)[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = crop.shape
    s = (out * 0.86) / max(h, w)
    im = Image.fromarray((np.clip(crop, 0, 1) * 255).astype(np.uint8)).resize(
        (max(1, int(round(w * s))), max(1, int(round(h * s)))), Image.BILINEAR)
    a = np.asarray(im, np.float64) / 255.0
    canvas = np.zeros((out, out), np.float64)
    y0, x0 = (out - a.shape[0]) // 2, (out - a.shape[1]) // 2
    canvas[y0:y0 + a.shape[0], x0:x0 + a.shape[1]] = a
    return canvas > thresh


def skeleton_chamfer(a: np.ndarray, b: np.ndarray, quantile: float = 0.99) -> float:
    """骨格どうしの**対称** chamfer 距離(画素単位)。

    ★生の IoU や相関は**線の太さに支配される**。書体間でインク率が 0.053〜0.157
    (約 3 倍)違うため、太さ込みで比べると「同一地域の書体差 > 同一書体の地域差」
    という**結論の反転**が起きた(2026-09-17 実測)。必ず骨格で比べる。

    片方向だけだと「部分集合」を距離 0 と言ってしまう(``口`` は ``回`` の部分)。
    両方向の**分位点**を取る。

    ★``quantile`` を**平均にしてはいけない**。生成 AI の取り違えは
    **部首を共有したまま一部だけ入れ替わる**(``検``→``横``、``設``→``登``、
    ``備``→``偣``)ので、違いは骨格の**一部**に集中する。平均はそれを薄めてしまい、
    実測では ``検`` と ``横`` の距離が 0.0171 = **書体雑音の床 0.0245 より下**に
    なった(= 原理的に検出できない)。99 パーセンタイルにすると 0.083 対 床 0.0668
    で 1.24 倍の余裕が出る。「どこかが大きく違う」を測るのであって、
    「全体としてどれくらい違う」を測るのではない。
    """
    from skimage.morphology import skeletonize
    sa, sb = skeletonize(np.asarray(a, bool)), skeletonize(np.asarray(b, bool))
    if not sa.any() or not sb.any():
        return float("inf")
    da = ndimage.distance_transform_edt(~sa)
    db = ndimage.distance_transform_edt(~sb)
    q = float(np.clip(quantile, 0.0, 1.0))
    return float(0.5 * (np.quantile(db[sa], q) + np.quantile(da[sb], q)))


def glyph_distance(a_alpha: np.ndarray, b_alpha: np.ndarray, out: int = _NORM,
                   quantile: float = 0.99) -> float:
    """2 枚のグリフの距離。大きさ・位置・太さを揃えてから比べ、一辺で割って返す。

    同じ字なら 0 近く、別の字なら :func:`typeface_noise_floor` が返す床より大きい。
    既定が 99 パーセンタイルなのは :func:`skeleton_chamfer` の理由による。
    """
    return skeleton_chamfer(normalise_glyph(a_alpha, out),
                            normalise_glyph(b_alpha, out), quantile) / out


def typeface_noise_floor(chars: str, fonts=None, size: int = 128,
                         quantile: float = 0.95, out: int = _NORM,
                         distance_quantile: float = 0.99) -> dict:
    """**閾値を勘で置かない**ための道具 —— 書体の違いだけで出る距離を測る。

    「同じ字を別の書体で描いたときの距離」の分布が、判定の**雑音の床**になる。
    これより大きい距離だけを「別の字」と呼ぶ。返り値には床だけでなく
    ``n_fonts`` と分布の要約も入れる —— 床が 1 つの数字で独り歩きすると、
    **何本の書体で測ったのか**が失われるため(書体が 2 本の床は狭すぎる)。
    """
    fonts = available_fonts() if fonts is None else [f for f in fonts if f]
    if len(fonts) < 2:
        raise RuntimeError(
            f"typeface_noise_floor needs at least 2 usable fonts (found {len(fonts)}) — "
            "the floor is the spread ACROSS typefaces, so one typeface cannot show it")
    d = []
    for ch in chars:
        if ch.isspace():
            continue
        gs = [render_glyph(ch, f, size) for f in fonts]
        for i in range(len(gs)):
            for j in range(i + 1, len(gs)):
                d.append(glyph_distance(gs[i], gs[j], out, distance_quantile))
    d = np.asarray(d, np.float64)
    return {"floor": float(np.quantile(d, quantile)), "median": float(np.median(d)),
            "max": float(d.max()), "n_pairs": int(d.size), "n_fonts": len(fonts),
            "quantile": float(quantile), "fonts": list(fonts)}


def rendering_noise_floor(chars: str, font_path=None, size: int = 128,
                          quantile: float = 0.95, out: int = _NORM,
                          distance_quantile: float = 0.99, index: int = 0) -> dict:
    """書体が **1 本しか無い**環境でも床を測る —— 既知の妨害で同じ字を揺らす。

    ★``typeface_noise_floor`` は書体 2 本以上が要るが、素の Linux には CJK が
    **1 本しか入らない**ことがある(実測: CI が ``fonts-noto-cjk`` だけで、
    PoC が丸ごと skip して落ちた)。「同じ字なのに絵が違う」を作れるのは書体だけ
    ではない —— ぼけ・線幅・わずかな回転・再標本化でも同じことが起きる。

    測るものが違うので**名前を分けてある**。返り値の ``source`` が ``"nuisance"``
    なのはそのため。書体が 2 本以上あるなら :func:`typeface_noise_floor` のほうが
    実態に近い(書体差は妨害より大きい)。
    """
    from PIL import Image
    fonts = available_fonts()
    if font_path is None:
        if not fonts:
            raise RuntimeError("no font on this machine can draw CJK")
        font_path = fonts[0]
    d = []
    for ch in chars:
        if ch.isspace():
            continue
        g = render_glyph(ch, font_path, size, index)
        base = normalise_glyph(g, out)
        for var in _nuisance_variants(g, Image):
            d.append(skeleton_chamfer(base, normalise_glyph(var, out),
                                      distance_quantile) / out)
    d = np.asarray(d, np.float64)
    return {"floor": float(np.quantile(d, quantile)), "median": float(np.median(d)),
            "max": float(d.max()), "n_pairs": int(d.size), "n_fonts": 1,
            "quantile": float(quantile), "fonts": [font_path], "source": "nuisance"}


def _nuisance_variants(alpha: np.ndarray, Image):
    """同じ字の「別の描かれ方」。★字を変えない妨害だけを並べる。"""
    out = [ndimage.gaussian_filter(alpha, 1.5),          # ぼけ
           ndimage.grey_dilation(alpha, size=3),         # 太らせ
           ndimage.grey_erosion(alpha, size=3),          # 細らせ
           ndimage.rotate(alpha, 2.0, reshape=False, order=1),    # わずかな回転
           ndimage.rotate(alpha, -2.0, reshape=False, order=1)]
    h, w = alpha.shape                                   # 再標本化(解像度の往復)
    small = np.asarray(Image.fromarray((np.clip(alpha, 0, 1) * 255).astype(np.uint8))
                       .resize((max(8, w // 4), max(8, h // 4)), Image.BILINEAR)
                       .resize((w, h), Image.BILINEAR), np.float64) / 255.0
    out.append(small)
    return out


def ink_colors(rgb: np.ndarray, mask: np.ndarray, erode: int = 2, ring: int = 4,
               levels: int = 16, min_share: float = 0.75, far: int = 10,
               halo_tol: float = 0.08, tol: float = 0.06,
               inner: int = 1) -> dict:
    """前景色 = マスクの**芯**の最頻色、背景色 = **外周リング**の最頻色。

    ★``unimodal`` が False のときは**置換してはいけない**。縁取り・影・グラデ・
    半透明では色が多峰になり、平均や単一色で塗ると**確実に汚す**。
    「できない」と返せることが、黙って壊すより価値が高い。
    """
    rgb = np.asarray(rgb, np.float64)
    if rgb.ndim == 2:
        rgb = rgb[..., None]
    mask = np.asarray(mask, bool)
    core = ndimage.binary_erosion(mask, np.ones((erode * 2 + 1,) * 2))
    if not core.any():
        core = mask
    # ★リングの**内径**は字のにじみの外に置く。にじみ(アンチエイリアスやぼけ)の
    #   中を背景として数えると、地色と文字色の中間が混ざって多峰に見える ——
    #   実測で、ぼけ σ=1.2 の合成看板が背景の集中度 0.52〜0.60 になり、
    #   平坦な単色の地なのに「置換できない」と断った。内径は呼び出し側が
    #   ``edge_transition_width`` から決められる。
    inner = max(1, int(inner))
    out = (ndimage.binary_dilation(mask, np.ones((ring * 2 + 1,) * 2))
           & ~ndimage.binary_dilation(mask, np.ones((inner * 2 + 1,) * 2)))

    def _mode(sel):
        px = rgb[sel]
        if px.size == 0:
            return np.zeros(rgb.shape[-1]), 0.0
        q = np.round(px * levels).astype(int)
        keys, counts = np.unique(q, axis=0, return_counts=True)
        top = keys[counts.argmax()] / float(levels)
        # ★「同じ量子化ビンに入った割合」で集中度を測ってはいけない —— 実写では
        #   最頻色がビンの境目にまたがって割合が半分になり、平坦な看板の地色まで
        #   多峰と判定した(実測で前景の占有率 0.31〜0.64、閾値 0.5 では全滅)。
        #   **最頻色からの距離が許容幅に入る割合**で測る。同じ実写で 0.87〜1.00、
        #   合成した赤い縁取りでは 0.63 と、はっきり分かれる。
        within = np.abs(px - top).max(axis=1) <= tol
        if not within.any():
            return px.mean(0), 0.0
        return px[within].mean(0), float(within.mean())

    far_ring = (ndimage.binary_dilation(mask, np.ones((far * 2 + 1,) * 2))
                & ~ndimage.binary_dilation(mask, np.ones((ring * 2 + 1,) * 2)))
    if not out.any():                              # 内径を広げ過ぎたら元に戻す
        out = (ndimage.binary_dilation(mask, np.ones((ring * 2 + 1,) * 2))
               & ~ndimage.binary_dilation(mask, np.ones((3, 3))))
    fg, fg_share = _mode(core)
    bg, bg_share = _mode(out)
    far_c, far_share = _mode(far_ring)
    # ★縁取りは**最頻色の占有率では捕まらない** ——
    #   縁が太ければ字のすぐ外は「縁の色一色」で
    #   立派に単峰になる(実測で赤い縁取りを単峰と
    #   判定した)。**近いリングと遠いリングの色が
    #   違うか**で見る。違えば背景は 1 色では書けない。
    halo = float(np.abs(np.asarray(bg) - np.asarray(far_c)).max()) if far_ring.any() else 0.0
    return {"fg": fg, "bg": bg, "far": far_c, "halo": halo,
            "fg_share": fg_share, "bg_share": bg_share, "far_share": far_share,
            "unimodal": bool(fg_share >= min_share and bg_share >= min_share
                             and halo <= halo_tol)}


def stroke_thickness(mask) -> float:
    """線の太さ(画素)。骨格の上での距離変換の中央値 x 2 = 最大内接円の直径。"""
    from skimage.morphology import skeletonize
    m = np.asarray(mask, bool)
    if not m.any():
        return 0.0
    v = ndimage.distance_transform_edt(m)[skeletonize(m)]
    return float(2.0 * np.median(v)) if v.size else 0.0


def match_stroke_weight(alpha: np.ndarray, target: float) -> np.ndarray:
    """描いた字を、周囲と**同じ線幅**まで太らせる。

    ★書体は選べないが、太さは合わせられる。合わせないと直した字だけ細くて
    一目で浮く(実測: 看板の太いゴシックに Meiryo Regular を貼った状態)。
    細くする方向には**やらない** —— 収縮は画をちぎるので、足りないときは諦める。
    """
    a = np.asarray(alpha, np.float64)
    t = stroke_thickness(a > 0.5)
    if t <= 0 or target <= t + 0.5:
        return a
    r = int(round((target - t) / 2.0))
    return ndimage.grey_dilation(a, size=2 * r + 1) if r >= 1 else a


def edge_transition_width(v: np.ndarray, window: int = 7, rel_floor: float = 1e-3,
                          abs_floor: float = 1e-6) -> np.ndarray:
    """局所の**エッジ遷移幅**(= 実効 PSF の広がり)を画素単位で返す。

    幅 ≒ 局所の振幅 ÷ 局所の最大勾配。合成した字を周囲と同じだけ鈍らせるために要る
    —— これをしないと数値は合っているのに「貼った感」が出る。

    ★床を相対量で置く**だけでは足りない**。基準を画像自身の振幅に取ると、
    一様な画像では基準まで丸め屑になり、屑どうしの比が構造に化ける —— 実測で、
    0.5 一色に 1e-12 の雑音を乗せただけの画像が幅 3.49 を返した。
    **振幅そのものが ``abs_floor`` に届かない画像には端が無い**と言い切る。
    """
    x = np.asarray(v, np.float64)
    gy, gx = np.gradient(x)
    grad = np.hypot(gy, gx)
    k = int(window) | 1
    amp = ndimage.maximum_filter(x, size=k) - ndimage.minimum_filter(x, size=k)
    gmax = ndimage.maximum_filter(grad, size=k)
    scale = float(np.ptp(x))                       # 画像全体の振幅が基準
    if scale < abs_floor:                          # 平坦な画像に端は無い
        return np.zeros_like(x)
    floor = rel_floor * scale
    w = np.where(gmax > floor, amp / np.maximum(gmax, floor), 0.0)
    return np.clip(w, 0.0, float(k))


def replace_glyph(rgb: np.ndarray, mask: np.ndarray, ch: str, font_path=None,
                  target_thickness: float = 0.0, index: int = 0,
                  grow: int = 1, ideal_edge: float = 2.0, seed: int = 20260917):
    """1 マスの誤字を正しい字に**実際に置き換える**。

    返り値は ``(置換後の画素, None)`` か ``(None, 断る理由)``。
    **直せないときに直せないと返せる**ことが設計の中心で、黙って壊れた絵を返さない。

    段取りは 4 つ:

    1. **色を決める** —— 前景 = マスクの芯の最頻色、背景 = 外周リング。多峰なら断る。
    2. **消す** —— 誤字のインクを少し膨らませて背景色で塗る。
    3. **合わせる** —— 正しい字をマスクの外接箱に入れ、線幅を周囲に合わせ、
       周囲の実効 PSF と同じだけ鈍らせる。★この 3 つ目をやらないと、
       数値は合っているのに「貼った感」が出る。
    4. **貼る** —— 前景色でアルファ合成。
    """
    from PIL import Image
    rgb = np.asarray(rgb, np.float64)
    mask = np.asarray(mask, bool)
    if mask.sum() < 20:
        return None, "マスが空(インクが 20 画素未満)"
    gray0 = rgb.mean(axis=-1) if rgb.ndim == 3 else rgb
    edge = float(np.median(edge_transition_width(gray0)[mask])) if mask.any() else 2.0
    inner = max(1, int(np.ceil(edge)))             # にじみの外からリングを取る
    ring = max(inner + 3, 4)
    col = ink_colors(rgb, mask, ring=ring, far=ring + 6, inner=inner)
    if not col["unimodal"]:
        return None, ("色が単峰でない(前景 %.2f / 背景 %.2f / 縁 %.3f) —— "
                      "縁取り・影・グラデの疑い"
                      % (col["fg_share"], col["bg_share"], col["halo"]))
    ys, xs = np.where(mask)
    h, w = int(ys.max() - ys.min() + 1), int(xs.max() - xs.min() + 1)
    glyph = render_glyph(ch, font_path, 256, index)
    gy, gx = np.where(glyph > 0.5)
    crop = glyph[gy.min():gy.max() + 1, gx.min():gx.max() + 1]
    im = Image.fromarray((np.clip(crop, 0, 1) * 255).astype(np.uint8)).resize(
        (w, h), Image.BILINEAR)
    a = np.asarray(im, np.float64) / 255.0
    a = match_stroke_weight(a, target_thickness or stroke_thickness(mask))

    alpha = np.zeros(mask.shape, np.float64)
    y0, x0 = int(ys.min()), int(xs.min())
    a = a[:alpha.shape[0] - y0, :alpha.shape[1] - x0]
    alpha[y0:y0 + a.shape[0], x0:x0 + a.shape[1]] = a

    sigma = max(0.0, (edge - ideal_edge) / 2.0)
    if sigma > 0:
        alpha = ndimage.gaussian_filter(alpha, sigma)

    out = rgb.copy()
    # ★消す範囲も**にじみの幅から**決める。2 値マスクは字の芯しか覆わないので、
    #   固定の 1 画素だけ広げて塗ると、旧字の灰色の縁が**幽霊**として残る
    #   (実測: 置換した字の周りに旧字の輪郭がうっすら見えた)。
    grow = max(int(grow), int(np.ceil(edge)))
    fill = ndimage.binary_dilation(mask, np.ones((2 * grow + 1,) * 2))
    out[fill] = col["bg"]
    # ★平均色で塗るだけでは**継ぎ目が見える**。地にはノイズと量子化のざらつきが
    #   あり、塗った面だけが滑らかだと矩形が浮く(実測: 置換した字の周りに
    #   はっきりした四角が出た)。地の**ばらつきも測って合わせる**。
    ring = (ndimage.binary_dilation(mask, np.ones((2 * (grow + 6) + 1,) * 2)) & ~fill)
    if ring.any():
        sigma_bg = float(np.std(rgb[ring], axis=0).mean()) if rgb.ndim == 3             else float(np.std(rgb[ring]))
        if sigma_bg > 0:
            rng = np.random.default_rng(seed)
            out[fill] = np.clip(out[fill] + rng.normal(0.0, sigma_bg, out[fill].shape),
                                0.0, 1.0)
    a3 = alpha[..., None] if out.ndim == 3 else alpha
    out = out * (1.0 - a3) + np.asarray(col["fg"]) * a3

    # ★**触る必要のある画素だけ**に限る。塗った面の外は入力のまま残す ——
    #   でないと、消去した矩形の縁が地のざらつきと食い違って**四角い継ぎ目**が
    #   見える(実測: 置換した字の周りにはっきりした枠が出た)。
    #   境目は少しぼかして、切り替わりを見えなくする。
    touch = fill | (alpha > 0.05)
    soft = ndimage.gaussian_filter(touch.astype(np.float64), 1.0)
    soft = np.clip(soft / max(soft.max(), 1e-12), 0.0, 1.0)
    s3 = soft[..., None] if rgb.ndim == 3 else soft
    out = rgb * (1.0 - s3) + out * s3
    return np.clip(out, 0.0, 1.0), None


def _ink_mask(gray: np.ndarray) -> np.ndarray:
    """濃淡から**字のインク**を取る。閾値は大津法で画像に決めさせる。

    ★中央値から標準偏差を引く式にしてはいけない。白地に黒文字だと中央値が
    ほぼ 1.0、標準偏差が 0.35 なので閾値が 0.825 まで上がり、**アンチエイリアスの
    縁と背景の雑音まで拾う** —— その状態で背景色を測ると多峰と判定され、
    直せる字まで断られる(実測 2026-09-17: 壊れた 4 字のうち 3 字)。
    固定値(0.35 等)も駄目 —— 照明や明暗の極性で外れる。
    """
    from skimage.filters import threshold_otsu
    g = np.asarray(gray, np.float64)
    if float(np.ptp(g)) < 1e-6:
        return np.zeros(g.shape, bool)
    t = float(threshold_otsu(g))
    # ★極性は**多数決で決めてはいけない**。行に密着した帯では字が 57 % を占める
    #   ことがあり(実測 2026-09-17、合成の掲示の 1 行目)、「インクは少数派」と
    #   すると白黒が丸ごと反転して距離が 0.025 -> 0.121 に跳ねた。
    #   **外周は背景**という事実で決める —— 字は縁まで届かない。
    border = np.concatenate([g[0], g[-1], g[:, 0], g[:, -1]])
    return (g < t) if float(np.median(border)) >= t else (g > t)


def split_cells(ink: np.ndarray, n: int, snap: float = 0.15) -> list:
    """一行ぶんのインクを **n 等分**し、切れ目をインクの**谷**に吸着させる。

    等幅を仮定できるのは CJK の掲示だからで、欧文では成り立たない。字数は
    **与えられた文字列から**来る —— ここでも「読む」必要は無い。
    ★等分だけだと、細い字と太い字が混ざったときに切れ目が字に食い込む
    (実測: 素の等分だと無事な字まで咎めた)。谷に寄せると直る。

    ★``snap`` の既定は **0.15**。0.25 だと切れ目が字の画に食い込む —— 実測
    2026-09-17: ``小`` の右払いが隣のマスに取られてマス幅が 70 px に痩せ、
    **無事な字の距離が 0.0556 から 0.1938 に跳ねて誤検出**になった
    (隣の ``学`` も 109 px に太って 0.1608)。正規化後のタイルでは拡大されるので
    **欠けが見えなくなる** —— 切り出しの検分は元の解像度で行うこと。
    実写 5 枚 45 字で 0.05〜0.20 は同じ結果(誤検出 4/14、正解率 91.1 %)、
    0.25 だけ悪い(6/14、86.7 %)。値を当て込んだのではなく、機構のある不具合。
    """
    ink = np.asarray(ink, bool)
    w = ink.shape[1] / float(max(n, 1))
    cuts = [i * w for i in range(n + 1)]
    if n > 1:
        prof = ink.sum(axis=0).astype(float)
        r = max(1, int(round(snap * w)))
        for i in range(1, n):
            c = int(round(cuts[i]))
            lo, hi = max(0, c - r), min(len(prof), c + r + 1)
            if hi > lo:
                cuts[i] = lo + int(np.argmin(prof[lo:hi]))
    return [(int(round(cuts[i])), int(round(cuts[i + 1]))) for i in range(n)]


# --------------------------------------------------------------------------- #
# 実写の版面 —— 看板の板を見つけて正面に起こす                                #
# --------------------------------------------------------------------------- #
def _plate_components(small, quantiles=(0.25, 0.35, 0.5, 0.65)):
    """平滑な領域の連結成分。順位づけはしない(選ぶのは :func:`find_plate`)。"""
    k = 5
    m = ndimage.uniform_filter(small, k)
    v = ndimage.uniform_filter(small * small, k) - m * m
    std = np.sqrt(np.clip(v, 0.0, None))
    total = small.size
    seen, out = set(), []
    for q in quantiles:
        mk = std <= float(np.quantile(std, q))
        mk = ndimage.binary_closing(mk, np.ones((5, 5)))
        mk = ndimage.binary_fill_holes(mk)
        lab, n = ndimage.label(mk)
        objs = ndimage.find_objects(lab)
        for i in range(1, n + 1):
            sl = objs[i - 1]
            if sl is None:
                continue
            comp = lab == i
            area = int(comp.sum())
            frac = area / total
            if not (0.02 <= frac <= 0.95):
                continue
            h = sl[0].stop - sl[0].start
            w = sl[1].stop - sl[1].start
            if area / max(h * w, 1) < 0.70:          # 穴だらけの塊は板ではない
                continue
            key = (sl[0].start // 2, sl[0].stop // 2, sl[1].start // 2, sl[1].stop // 2)
            if key in seen:
                continue
            seen.add(key)
            out.append((frac, comp, sl))
    return out


def _glyph_blobs(small, comp, sl):
    """候補の内側の「字らしい塊」の個数と高さの中央値(小さい写しの画素)。"""
    sub, msk = small[sl], comp[sl]
    vals = sub[msk]
    if vals.size < 64:
        return 0, 0.0
    from skimage.filters import threshold_otsu
    t = float(threshold_otsu(vals))
    ink = ((sub < t) if float(np.median(vals)) >= t else (sub > t)) & msk
    lab, n = ndimage.label(ink)
    if n == 0:
        return 0, 0.0
    ch = sl[0].stop - sl[0].start
    hs = []
    for o in ndimage.find_objects(lab):
        if o is None:
            continue
        h = o[0].stop - o[0].start
        w = o[1].stop - o[1].start
        if not (0.08 * ch <= h <= 0.60 * ch):        # 埃でも枠でもない大きさ
            continue
        if not (0.25 <= w / max(h, 1) <= 4.0):       # 極端に細長い罫線は字でない
            continue
        hs.append(h)
    return (len(hs), float(np.median(hs))) if hs else (0, 0.0)


def _refine_quad(gray, box, margin=0.25):
    """粗い箱の周りで**上下左右の縁に当たる直線**を 1 本ずつ探し、交点を四隅にする。

    平滑領域の外接箱は、局所標準偏差のしきい値が文字の近くで板を削るので内側に
    寄る。看板には暗い縁があり壁との境界も強いので、そちらに乗せ直す。
    """
    ys, xs = box
    h, w = ys.stop - ys.start, xs.stop - xs.start
    my, mx = int(h * margin), int(w * margin)
    y0, y1 = max(0, ys.start - my), min(gray.shape[0], ys.stop + my)
    x0, x1 = max(0, xs.start - mx), min(gray.shape[1], xs.stop + mx)
    sub = gray[y0:y1, x0:x1]
    if min(sub.shape) < 32:
        return None
    gy, gx = np.gradient(sub)
    E = np.hypot(gy, gx)
    H, W = sub.shape
    yy, xx = np.mgrid[0:H, 0:W]
    lines = []
    for side in ("top", "bottom", "left", "right"):
        horiz = side in ("top", "bottom")
        best = (-1.0, None)
        for a in np.deg2rad(np.linspace(-20, 20, 41)):
            m = np.tan(a)
            proj = (yy - m * xx) if horiz else (xx - m * yy)
            lo, hi = proj.min(), proj.max()
            bins = int(hi - lo) + 1
            if bins < 8:
                continue
            idx = np.clip((proj - lo).astype(int), 0, bins - 1)
            acc = np.bincount(idx.ravel(), weights=E.ravel(), minlength=bins)
            k = max(4, bins // 4)
            seg, off = (acc[:k], 0) if side in ("top", "left") else (acc[-k:], bins - k)
            j = int(np.argmax(seg))
            if float(seg[j]) > best[0]:
                best = (float(seg[j]), (m, lo + off + j, horiz))
        if best[1] is None:
            return None
        lines.append(best[1])

    def inter(l1, l2):
        m1, b1, h1 = l1
        m2, b2, h2 = l2
        if h1 == h2 or abs(1.0 - m1 * m2) < 1e-9:
            return None
        if h1:
            x = (m2 * b1 + b2) / (1.0 - m1 * m2)
            return (x + x0, m1 * x + b1 + y0)
        y = (m2 * b1 + b2) / (1.0 - m1 * m2)
        return (m1 * y + b1 + x0, y + y0)

    top, bot, left, right = lines
    pts = [inter(top, left), inter(top, right), inter(bot, right), inter(bot, left)]
    if any(p is None for p in pts):
        return None
    return np.asarray(pts, np.float64)


def find_plate(rgb: np.ndarray, max_frac: float = 0.60,
               min_glyphs: int = 2) -> tuple:
    """写真の中の**看板の板を 1 枚見つけて正面に起こす**。返り ``(起こした画像 or None, 報告)``。

    実写の文字は、板が斜めから写っているだけで判定が壊れる。この関数は板の四隅を
    取って射影変換で正面に直し、**直せなければ ``None`` を返す**(黙って歪んだ絵を
    返さない)。報告の ``status`` は:

    ``found``              板が見つかり起こした。
    ``no_candidate``       看板らしい候補が無い(平滑な塊が無い / 字らしい塊が足りない)。
    ``no_quad``            候補はあるが四隅が取れない(縁が弱い)。

    **候補の選び方**(面積順ではない): ``max_frac`` を超える塊は地とみなして捨て、
    内側に**字らしい塊が ``min_glyphs`` 個以上**あるものだけを残し、**縁の強さ**
    (輪郭上の勾配の中央値 ÷ 画像全体の中央値)で並べる。
    ★**順位そのものは効かない**(2026-09-17 実測: 面積順に戻しても結果は 1 文字も
    変わらない。呼ぶ側は受理されるまで候補を順に試すため)。この並べ替えは
    「最初に正しい板を見る」ための速さの話で、正しさの話ではない。

    **四隅**は平滑領域の外接箱ではなく**縁の直線 4 本の交点**で取る。実測で
    誤検出が 20/33 → 11/28 に減り、看板 12 枚での正解率が 75.0 → 82.4 % に上がった。

    ★**縁の強さで断ってはいけない**(実測で無効): 四辺の勾配で閾値を掃いても
    結果は平坦で、**いちばん縁が強い板がいちばん誤検出を出した**(信頼度 19.05 の
    板が誤検出あり、3.31 の板が誤検出 1)。効くのは**字の大きさ**のほうである。

    **字の大きさで断るのは呼ぶ側の仕事**。実測の動作点は「**マスの幅の中央値
    90 px**」で、そこでは見逃し 0 のまま壊れた字の検出が 31 → 36 本に増え、誤検出は
    4 → 5 本の 1 本増だった。正解率(90.7 %)は板を使わない場合(91.1 %)をわずかに
    下回るが、それは**受理する画像が増えて分母が育つ**ためで、既存の画像は 1 文字も
    悪くなっていない。見逃しのほうが高くつく用途ではこの動作点を使うこと ——
    マス幅は :func:`split_cells` で測れる(期待文字列を知っている側が測る)。

    ★**この関数は大きさで断らない。** 期待文字数を知らずに測れる「字の塊の高さ」で
    代用できるか測ったら、マス幅との比が **0.00〜10.21** まで暴れた(1 行だけの板では
    行全体が 1 個の塊につながり、絞ると 1 個も残らない)。**同じつもりの量が 2 桁
    違う**ので、その上に閾値は置けない。掃引したのはマス幅なので、閾値もマス幅の
    上にだけ置く。報告の ``glyph_blobs`` は候補の選別に使った個数で、**大きさの
    物差しではない**。

    ★**小さい字は解像度を合わせても直らない**(実測): マス 42〜46 px の板では、
    比べる解像度を 48 / 80 / 160 px のどれにしても「壊れた字のほうが遠い」が
    58〜62 % しか成り立たない(当てずっぽうが 50 %)。引き伸ばしのぼけではなく、
    **その写真では距離が信号を運んでいない**。だから直すのではなく断る。
    """
    from skimage import transform as _sktf

    rgb = np.asarray(rgb, np.float64)
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError("find_plate は RGB 画像を取る(HxWx3)")
    gray = rgb.mean(axis=-1)
    step = max(1, int(max(gray.shape) / 256))
    small = gray[::step, ::step]
    gy, gx = np.gradient(small)
    e = np.hypot(gy, gx)
    base = float(np.median(e))

    scored = []
    for frac, comp, sl in _plate_components(small):
        if frac > max_frac:
            continue
        n_glyph, h_glyph = _glyph_blobs(small, comp, sl)
        if n_glyph < min_glyphs:
            continue
        edge = comp ^ ndimage.binary_erosion(comp, np.ones((3, 3)))
        strength = (float(np.median(e[edge])) / max(base, 1e-9)) if edge.sum() >= 16 else 0.0
        scored.append((strength, frac, comp, sl, n_glyph, h_glyph))
    if not scored:
        return None, {"status": "no_candidate", "reason": "看板らしい候補が無い"}
    scored.sort(key=lambda t: -t[0])

    last = "no_quad"
    for strength, frac, comp, sl, n_glyph, h_glyph in scored:
        box = (slice(int(sl[0].start * step), int(min(gray.shape[0], sl[0].stop * step))),
               slice(int(sl[1].start * step), int(min(gray.shape[1], sl[1].stop * step))))
        quad = _refine_quad(gray, box)
        if quad is None:
            continue
        ctr = quad.mean(axis=0)
        q = ctr + (quad - ctr) * 1.04                    # 縁で切れないよう少し外へ
        wa = np.linalg.norm(q[1] - q[0]); wb = np.linalg.norm(q[2] - q[3])
        ha = np.linalg.norm(q[3] - q[0]); hb = np.linalg.norm(q[2] - q[1])
        W, H = int(round(max(wa, wb))), int(round(max(ha, hb)))
        if not (48 <= W <= 4000 and 24 <= H <= 4000):
            continue
        t = _sktf.ProjectiveTransform()
        if not t.estimate(np.array([[0, 0], [W, 0], [W, H], [0, H]], np.float64), q):
            continue
        out = np.clip(_sktf.warp(rgb, t, output_shape=(H, W), order=1, mode="edge"),
                      0.0, 1.0)
        # 起こした後の実寸に直した字の高さ(小さい写しで測ったので step 倍、
        # さらに起こしで伸び縮みするぶんを幅の比で補正する)。
        return out, {"status": "found", "quad": q.tolist(),
                     "area_frac": round(float(frac), 4),
                     "border": round(float(strength), 3),
                     "glyph_blobs": int(n_glyph), "size": [W, H]}
    return None, {"status": last, "reason": "候補はあるが四隅が取れない(縁が弱い)"}


def _fit_alpha(alpha: np.ndarray, h: int, w: int) -> np.ndarray:
    """アルファ (a,b) を (h,w) に**等方**で収める(中央寄せ)。歪ませない。"""
    from skimage.transform import resize
    ah, aw = alpha.shape
    if ah == 0 or aw == 0 or h <= 0 or w <= 0:
        return np.zeros((max(h, 0), max(w, 0)))
    s = min(h / ah, w / aw)
    nh, nw = max(1, int(round(ah * s))), max(1, int(round(aw * s)))
    small = resize(alpha, (nh, nw), order=1, anti_aliasing=True, preserve_range=True)
    out = np.zeros((h, w))
    y0, x0 = (h - nh) // 2, (w - nw) // 2
    out[y0:y0 + nh, x0:x0 + nw] = small
    return out


def rewrite_line(rgb: np.ndarray, text: str, font_path=None, size: int = 256) -> tuple:
    """1 行ぶんの画像を、**意図した文字列で丸ごと描き直す**。返り ``(画像, 報告)``。

    「壊れた字だけ直す」(:func:`replace_glyph`)だと、検出の見逃し・誤検出が結果に
    残る。正しい字も含めて書体の変更を許すなら、行を丸ごと描き直せば**見逃しは
    構造的に起きない**(2026-09-18、ユーザー提案)。字数が違う生成結果(1 字の
    挿入・欠落)も、位置合わせをしないので自然に直る。

    手順: (1) 行のインクを背景色で消す(縁のアンチエイリアス分だけ膨らませる)
    (2) 各字を**元のマスのインク幅・行のインク高さ**に等方で収めて 1 枚のアルファに
    並べる —— 箱いっぱいに収めると描画の余白ぶん小さく見える(実測)
    (3) 太さは**行全体に 1 回だけ**合わせる —— 字ごとだと密な字が太りすぎる(実測「賞」)
    (4) 前景色で合成。色は :func:`ink_colors` で行全体から 1 回測る。

    ★色が単峰でなければ描かない(縁取り・影・グラデ)。``ok=False`` と理由を返す。
    ★書体は 1 本を渡す。同じ画像の複数行は**同じ書体**で呼ぶこと(行ごとに違うと不自然)。

    **検証について**: 描いた字は分かっているので距離は正しさの門にならない。
    実測では、比較に使った書体そのもので描いた字を画像から取り直しても距離が
    0.037〜0.081 出る(抽出経路自体の雑音 ≒ 0.05、床と同程度)。確かめるべきは
    **マスの位置**であり、それは呼ぶ側が bbox で与える。
    """
    rgb = np.asarray(rgb, np.float64)
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError("rewrite_line は RGB 画像を取る(HxWx3)")
    chars = [c for c in str(text) if not c.isspace()]
    if not chars:
        return rgb.copy(), {"ok": False, "reason": "text が空"}
    font = font_path or (available_fonts() or [None])[0]
    if font is None:
        return rgb.copy(), {"ok": False, "reason": "CJK を描ける書体が無い"}
    gray = rgb.mean(axis=-1)
    ink = _ink_mask(gray)
    if ink.sum() < 20:
        return rgb.copy(), {"ok": False, "reason": "行にインクが無い"}
    col = ink_colors(rgb, ink)
    if not col.get("unimodal", True):
        return rgb.copy(), {"ok": False, "reason": "色が単峰でない(縁取り・影・グラデの疑い)"}
    H, W = gray.shape
    out = rgb.copy()
    # (1) 消す。周囲の雑音を乗せて継ぎ目を弱める(replace_glyph と同じ考え方)。
    wipe = ndimage.binary_dilation(ink, iterations=2)
    ring = ndimage.binary_dilation(wipe, iterations=6) & ~wipe
    bg = np.asarray(col["bg"], np.float64)
    out[wipe] = bg
    if ring.sum() > 16:
        sigma = float(np.std(rgb[ring], axis=0).mean())
        if sigma > 0:
            rng = np.random.default_rng(20260918)
            out[wipe] = np.clip(out[wipe] + rng.normal(0.0, sigma, out[wipe].shape), 0.0, 1.0)
    # (2) 並べる。
    spans = split_cells(ink, len(chars))
    ys_ink = np.where(ink.any(axis=1))[0]
    gh = int(ys_ink.max() - ys_ink.min() + 1) if ys_ink.size else H
    top = int(ys_ink.min()) if ys_ink.size else 0
    line_alpha = np.zeros((H, W))
    for ch, (cx0, cx1) in zip(chars, spans):
        a = render_glyph(ch, font, size)
        nz = np.where(a > 0.05)
        if nz[0].size:
            a = a[nz[0].min():nz[0].max() + 1, nz[1].min():nz[1].max() + 1]
        xs_ink = np.where(ink[:, cx0:cx1].any(axis=0))[0]
        gw = int(xs_ink.max() - xs_ink.min() + 1) if xs_ink.size else (cx1 - cx0)
        gw = max(1, min(gw, cx1 - cx0))
        fitted = _fit_alpha(a, gh, gw)
        ox = cx0 + ((cx1 - cx0) - gw) // 2
        tgt = line_alpha[top:top + gh, ox:ox + gw]
        tgt[...] = np.maximum(tgt, fitted[:tgt.shape[0], :tgt.shape[1]])
    # (3) 太さを行で 1 回。
    line_alpha = match_stroke_weight(line_alpha, stroke_thickness(ink))
    # (4) 合成。
    a3 = line_alpha[..., None]
    out = np.clip(out * (1.0 - a3) + np.asarray(col["fg"], np.float64) * a3, 0.0, 1.0)
    return out, {"ok": True, "chars": len(chars),
                 "fg": [round(float(v), 3) for v in np.atleast_1d(col["fg"])],
                 "bg": [round(float(v), 3) for v in np.atleast_1d(col["bg"])]}


def correct_spec(rgb: np.ndarray, spec: dict) -> tuple:
    """**画像 + 「本当はこう書いてあるべき文字列」を JSON 一枚で受けて直す入口。**

    使う側が欲しいのは「op を 7 個つなぐ手順」ではなく、画像と正しい文字列を
    渡すと直った画像が返ること。``spec`` は次の形(必要なのは ``items`` だけ)::

        {"locale": "ja-JP",
         "font": "<描くのに使う書体ファイル。省略すればこの環境のものを探す>",
         "items": [{"text": "電気設備", "bbox": [x, y, w, h]},
                   {"text": "点検中",   "bbox": [x, y, w, h],
                    "codepoints": ["U+70B9", "U+691C", "U+4E2D"]}],
         "policy": {"threshold": 0.0, "mode": "repair_flagged"}}

    ``policy.mode`` は 2 値:

    ``repair_flagged``(既定)
        床を超えた字だけ置き換える。**正しい字には触らない**(原本保全向け)。
    ``rewrite_line``
        bbox の行を**意図した文字列で丸ごと描き直す**(:func:`rewrite_line`)。
        検出の見逃し・誤検出が結果に残らず、字数の違い(挿入・欠落)も直る。
        生成 AI がレポート・資料用に出した画像の誤字を、再生成せずに直す用途向け。
        各マスの ``distance_before`` は情報として残す(何が壊れていたかの報告)。

    返り値は ``(直した画像, 報告)``。報告の ``status`` は 4 値:

    ``ok``
        床より近い。直す必要が無い。
    ``replaced``
        床より遠かったので置き換え、置換後は床より近くなった。
    ``failed_verification``
        置き換えたが床より近くならなかった。**その字は元に戻す。**
    ``skipped``
        置き換えられない(色が多峰 = 縁取り・影・グラデ、マスが空、等)。

    ★**「直せなかった」を返せることが設計の中心**。黙って壊れた絵を返さない。
    ``failed_verification`` で元に戻すのは、数値で確かめられない置換を残すと
    「直った」と誤解されるため —— 検証を通らない修正は修正ではない。

    ★閾値は勘で置かない。``policy.threshold`` が無ければ、``items`` に出てくる
    字を**その環境にある書体で描き分けた距離**の 95 % 点を使う
    (:func:`typeface_noise_floor`。書体が 1 本しか無い環境では
    :func:`rendering_noise_floor` に落ちる)。**測っているものが違うので、
    報告の ``floor_source`` にどちらかを書く。**

    ★``codepoints`` は ``text`` と食い違っていたら**例外にする**。片方だけ直した
    指示書が回ってくると、静かに違う字に置き換わる —— 一致の検査は入口で行う。
    """
    rgb = np.asarray(rgb, np.float64)
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError("correct_spec は RGB 画像を取る(HxWx3)")
    items = spec.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("spec['items'] が要る(空でないリスト)")

    fonts = available_fonts()
    if spec.get("font"):
        import os as _os
        if not _os.path.exists(spec["font"]):
            raise FileNotFoundError("spec['font'] が見つからない: %s" % spec["font"])
        fonts = [spec["font"]] + [f for f in fonts if f != spec["font"]]
    if not fonts:
        raise RuntimeError("CJK を描ける書体がこの環境に無い")

    for it in items:
        cps = it.get("codepoints")
        if cps is None:
            continue
        want = "".join(chr(int(str(c).upper().replace("U+", ""), 16)) for c in cps)
        if want != it.get("text", ""):
            raise ValueError("codepoints と text が食い違っている: %r と %r"
                             % (want, it.get("text")))

    chars = "".join(str(it.get("text", "")) for it in items)
    chars = "".join(sorted(set(c for c in chars if not c.isspace())))
    policy = spec.get("policy") or {}
    thr = policy.get("threshold")
    if thr is None:
        if len(fonts) >= 2:
            nf = typeface_noise_floor(chars, fonts, size=160, out=160)
            source = "typeface"
        else:
            nf = rendering_noise_floor(chars, fonts[0], size=160, out=160)
            source = "rendering"
        thr = nf["floor"]
    else:
        thr, source = float(thr), "policy"

    mode = str(policy.get("mode", "repair_flagged"))
    if mode not in ("repair_flagged", "rewrite_line"):
        raise ValueError("policy.mode は repair_flagged か rewrite_line: %r" % mode)
    out = rgb.copy()
    report = {"threshold": float(thr), "floor_source": source,
              "fonts": len(fonts), "mode": mode, "items": []}

    for it in items:
        text = "".join(c for c in str(it.get("text", "")) if not c.isspace())
        bbox = it.get("bbox")
        entry = {"text": it.get("text", ""), "cells": []}
        report["items"].append(entry)
        if not text or not bbox or len(bbox) != 4:
            entry["status"] = "skipped"
            entry["reason"] = "text か bbox が無い"
            continue
        x, y, w, h = (int(round(v)) for v in bbox)
        y0, y1 = max(0, y), min(out.shape[0], y + h)
        x0, x1 = max(0, x), min(out.shape[1], x + w)
        if y1 - y0 < 8 or x1 - x0 < 8 * len(text):
            entry["status"] = "skipped"
            entry["reason"] = "bbox が小さすぎる"
            continue
        crop = out[y0:y1, x0:x1]
        gray = crop.mean(axis=-1)
        ink = _ink_mask(gray)
        spans = split_cells(ink, len(text))
        if mode == "rewrite_line":
            # 何が壊れていたかは情報として残す(門には使わない)。
            for k, ch in enumerate(text):
                cx0, cx1 = spans[k]
                cell = ink[:, cx0:cx1]
                rec = {"char": ch}
                if cell.sum() >= 20:
                    rec["distance_before"] = round(float(min(
                        glyph_distance(cell.astype(np.float64), render_glyph(ch, f, 160), 160)
                        for f in fonts)), 4)
                entry["cells"].append(rec)
            fixed, info = rewrite_line(crop, text, fonts[0])
            if not info.get("ok"):
                entry["status"] = "skipped"
                entry["reason"] = info.get("reason", "描き直せない")
                for rec in entry["cells"]:
                    rec["status"] = "skipped"
                continue
            out[y0:y1, x0:x1] = fixed
            entry["status"] = "rewritten"
            for rec in entry["cells"]:
                rec["status"] = "rewritten"
            continue
        statuses = []
        for k, ch in enumerate(text):
            cx0, cx1 = spans[k]
            cell = ink[:, cx0:cx1]
            rec = {"char": ch}
            entry["cells"].append(rec)
            if cell.sum() < 20:
                rec["status"] = "skipped"
                rec["reason"] = "マスにインクが無い"
                statuses.append("skipped")
                continue
            before = min(glyph_distance(cell.astype(np.float64),
                                        render_glyph(ch, f, 160), 160) for f in fonts)
            rec["distance_before"] = round(float(before), 4)
            if before <= thr:
                rec["status"] = "ok"
                statuses.append("ok")
                continue
            # ★マスを**少し広げて**切り出し、その中で「このマスに属する成分」だけを
            #   マスクにする。マスちょうどで切ると、外周リングが**隣の字のインク**を
            #   拾って「色が多峰」と誤判定し、直せるものまで断ってしまう
            #   (実測 2026-09-17: 壊れた 4 字のうち 3 字がこれで断られた)。
            #   また隣の字のはみ出しが消し残り、置換後に旧字の切れ端が浮く。
            # ★**上下左右に余白を付けて**切り出し、その中で「このマスに属する成分」だけを
            #   マスクにする。bbox ちょうどで切ると、背景色を測る外周リングが
            #   隣の字のインクと字の縁を拾い、「色が多峰」と誤判定して
            #   **直せるものまで断る**(実測 2026-09-17: 壊れた 4 字のうち 3 字が
            #   これで断られ、背景色の占有率が 0.49〜0.57 に落ちていた)。
            #   余白は画像そのものから取る —— 行の bbox は字に密着しているので、
            #   bbox の中だけでは純粋な背景が手に入らない。
            pad = max(6, int(0.20 * (cx1 - cx0)))
            ay0, ay1 = max(0, y0 - pad), min(out.shape[0], y1 + pad)
            ax0, ax1 = max(0, x0 + cx0 - pad), min(out.shape[1], x0 + cx1 + pad)
            wide_ink = _ink_mask(out[ay0:ay1, ax0:ax1].mean(axis=-1))
            lab, nlab = ndimage.label(wide_ink)
            keep_mask = np.zeros_like(wide_ink)
            for m in range(1, nlab + 1):
                _ys, _xs = np.nonzero(lab == m)
                if cx0 <= (ax0 - x0) + _xs.mean() < cx1:
                    keep_mask[lab == m] = True
            sub = out[ay0:ay1, ax0:ax1]
            keep = sub.copy()
            fixed, why = replace_glyph(sub, keep_mask, ch, fonts[0],
                                       target_thickness=stroke_thickness(ink))
            if fixed is None:
                rec["status"] = "skipped"
                rec["reason"] = why
                statuses.append("skipped")
                continue
            sub[...] = fixed
            ink2 = _ink_mask(out[y0:y1, x0 + cx0:x0 + cx1].mean(axis=-1))
            after = (min(glyph_distance(ink2.astype(np.float64),
                                        render_glyph(ch, f, 160), 160) for f in fonts)
                     if ink2.sum() >= 20 else float("inf"))
            rec["distance_after"] = round(float(after), 4)
            if after <= thr:
                rec["status"] = "replaced"
                statuses.append("replaced")
            else:
                sub[...] = keep                       # ★検証を通らない修正は残さない
                rec["status"] = "failed_verification"
                statuses.append("failed_verification")
        for s in ("failed_verification", "skipped", "replaced", "ok"):
            if s in statuses:
                entry["status"] = s
                break
        else:
            entry["status"] = "skipped"
    return out, report
