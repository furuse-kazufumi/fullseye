# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""annotate — 図注(figure annotation)の層。図に「意味」を焼き込む op。

## なぜ op にするのか

この repo は 141 点の図を持っているが、その図を作る 6 本の生成器
(``tools/gen_*_gallery.py`` ほか)は、**同じものを何度も手書き**していた。
実測(``grep "def _" tools/gen_*.py`` の重複数):

    _font 16 / _to_u8 11 / _text 7 / _canvas 6 / _fill 5 / _cmap 4 /
    _fit 3 / _dashed 3 / _legend 2 / _label 2 / _panel 2

つまり「文字の下敷き」「矢印」「凡例の箱」「カラーバー」「目盛り」「拡大の
差し込み」「マスクの重ね」「パネルの枠」が、生成器ごとに別実装で散らばって
いた。**同じコードが複数の生成器にあるのは、op にすべきという証拠**なので、
ここに 1 か所へ集める。

## 三つの規律

1. **色は自分で選ばない** — ``color=`` は :mod:`palette` の**役割名**
   (``"right"``/``"wrong"``/``"neutral"``/``"emphasis"``/``"baseline"``/
   ``"reference"``)を文字列で受ける。生の RGB も受けるが、図のコードは
   役割で指すのが本筋(既定の scheme は Okabe–Ito)。

2. **文字は幅を測ってから描く** — 入り切らないなら**縮めて収める**か、
   収まらなければ**例外**。黙って切るのは禁止。機械検査は文字切れを検出
   できない(壊れていない画像として通ってしまう)ので、ここで止めるしかない。
   実際この repo で文字切れが 6 件出ている。

3. **低レベルの線引きは :mod:`imagedraw` を呼ぶ** — 線の描き方を二重に
   持たない。線種(破線・点線)の引数が増えたときに追従できるよう、
   ``style=`` に渡された辞書は **そのまま ``imagedraw`` へ素通し**する
   (``annotate`` 側は中身を解釈しない)。

## 規約(imagedraw / imagemorph と同じ)

* 画像は ``(H,W)`` か ``(H,W,C)``、値域 [0,1] の float。
* **点は (x,y) = (col,row)**、**矩形は (x,y,w,h) で (x,y) は左上**。
  row は下向きなので、``y`` が増えると画面では**下**へ動く。
  (データ座標を使う :func:`axes_transform` だけが上向き ``y`` を扱い、
  その反転はここで 1 か所に閉じ込めてある。)
* 全 op は**入力を破壊せず新しい配列を返す**。
* **決定的** — 乱数もタイムスタンプも使わない。同じ入力・同じフォントなら
  同じバイト列。フォントは ``font_path=`` を明示すれば機械間でも一致する
  (省略時は環境にある候補から**固定順**で選ぶ)。

  フォントが 1 つも見つからなければ Pillow の既定フォントに落ちる ―― ただし
  **落ちても版が壊れない**のは、この層が字幅を決め打ちの係数ではなく
  ``textlength`` の実測で決めているから(生成器のいくつかは「1 文字 3.2 px」の
  ような定数で位置を決めていて、フォントが変わると静かにずれる)。
  日本語が豆腐になるのは環境の問題なので、機械間で絵を一致させたい用途では
  ``font_path=`` を必ず渡すこと。

## 依存

numpy + scipy(+ 文字を描く op だけ Pillow)。**matplotlib は使わない** ――
だから軸・目盛り・格子・折れ線を描くのもこの層の仕事
(:func:`axes_transform` / :func:`axes_frame` / :func:`grid_lines` /
:func:`ticks` / :func:`plot_series`)。
"""
from __future__ import annotations

import functools
import math

import numpy as np

import imagedraw
import palette

__all__ = [
    # 文字
    "measure_text", "text_box",
    # 指し示す
    "arrow", "leader_line", "label_points", "crosshair",
    # 図の備品
    "legend_box", "color_bar", "scale_bar",
    # グラフ(matplotlib を使わない)
    "axes_transform", "data_to_pixel", "nice_ticks",
    "axes_frame", "grid_lines", "ticks", "plot_series",
    # 重ね
    "overlay_mask", "overlay_labels",
    # 組み立て
    "zoom_inset", "compare_frame", "panel_grid",
    # 図形
    "rounded_rect", "filled_polygon", "arc", "ellipse",
    # 学術図の作法(2026-09-03): 引き出し線 / 番号 + 凡例 / 寸法 / 角度 /
    # 切りのよいスケールバー / 方位 / 隅の拡大 / 輪郭 / 経路文字 / 色分け /
    # パネル文字 / 図の組版。``*_layout`` は幾何だけを table で返す
    "annotate_leader_layout", "annotate_leader",
    "annotate_markers", "annotate_legend",
    "annotate_dimension_layout", "annotate_dimension",
    "annotate_angle_layout", "annotate_angle",
    "annotate_scale_bar_layout", "annotate_scale_bar",
    "annotate_orientation",
    "annotate_inset_layout", "annotate_inset",
    "annotate_outline_layout", "annotate_outline",
    "annotate_text_path_layout", "annotate_text_path",
    "annotate_colorbar",
    "annotate_panel_label",
    "annotate_figure_grid_layout", "annotate_figure_grid",
]

#: フォント候補。**固定順**で探すので、同じ機械なら同じフォントが選ばれる
#: (機械をまたいでバイト一致させたいときは ``font_path=`` を明示する)。
#: 日本語を含むラベルがあるので CJK を持つものを先に置く。
FONT_CANDIDATES = (
    r"C:\Windows\Fonts\meiryo.ttc",
    r"C:\Windows\Fonts\YuGothM.ttc",
    r"C:\Windows\Fonts\msgothic.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
)

#: :func:`text_box` の既定の下敷き色(暗い板)と文字色。役割色ではないのは、
#: 「板」と「文字」は図の**意味**ではなく**読ませるための地と図**だから。
_PLATE_RGB = (0.05, 0.05, 0.08)
_INK_RGB = (0.94, 0.94, 0.96)

#: 文字と、その下に実際に出る色との最小コントラスト比(WCAG の式)。
#: 既定を 2.0 にしてあるのは「読めない」を捕まえるためで、装飾の禁止では
#: ない。背景と同化した文字は**例外なく黙って消える**ので機械では気づけない。
DEFAULT_MIN_CONTRAST = 2.0

_ANCHORS = ("lt", "ct", "rt", "lm", "cm", "rm", "lb", "cb", "rb")


# ------------------------------------------------------------------ #
# 下ごしらえ(fail-closed)
# ------------------------------------------------------------------ #

def _prep(img):
    """画像を float64 [0,1] の複製にする。非有限は**黙って直さず例外**。

    Raises ValueError: 次元・空・非有限。
    """
    a = np.array(img, dtype=np.float64)
    if a.ndim not in (2, 3):
        raise ValueError(f"img must be (H,W) or (H,W,C) (got: {a.shape})")
    if a.size == 0 or a.shape[0] == 0 or a.shape[1] == 0:
        raise ValueError("img is empty")
    if a.ndim == 3 and a.shape[2] not in (1, 3, 4):
        raise ValueError(f"img channels must be 1, 3 or 4 (got: {a.shape[2]})")
    if not np.all(np.isfinite(a)):
        n = int(np.count_nonzero(~np.isfinite(a)))
        raise ValueError(
            f"img holds {n} non-finite value(s); NaN drawn as black looks like a dark "
            "region in the figure and nobody notices — fix the data, not the picture")
    return np.clip(a, 0.0, 1.0)


def _finite(name, *vals):
    for v in vals:
        if not np.all(np.isfinite(np.asarray(v, dtype=np.float64))):
            raise ValueError(f"{name} must be finite (got: {v!r})")


def _rgb(color, scheme="okabe_ito"):
    """``color`` を RGB float [0,1] の三つ組にする。

    文字列は :mod:`palette` の**役割名**として解決する(未知なら ValueError)。
    数値/シーケンスはそのまま(長さ 1 は灰色として 3 本に展開)。
    """
    if isinstance(color, str):
        return tuple(float(c) for c in palette.role_color(color, scheme))
    c = np.asarray(color, dtype=np.float64).ravel()
    if c.size == 1:
        c = np.repeat(c, 3)
    if c.size < 3:
        raise ValueError(f"color needs 1 or >=3 components (got: {c.size})")
    if not np.all(np.isfinite(c)):
        raise ValueError(f"color must be finite (got: {color!r})")
    if np.any(c < 0.0) or np.any(c > 1.0):
        raise ValueError(f"color components must be within [0,1] (got: {color!r})")
    return tuple(float(v) for v in c[:3])


def _channel_color(a, color, scheme="okabe_ito"):
    """画像のチャンネル数に合わせた描画色。

    グレースケール(``(H,W)``)では :mod:`imagedraw` と同じ **平均**で 1 値に
    落とす(同じ色指定が両モジュールで同じ濃さになるように)。
    """
    rgb = _rgb(color, scheme)
    if a.ndim == 2:
        return float(np.mean(rgb))
    c = a.shape[2]
    if c == 1:
        return np.array([np.mean(rgb)], dtype=np.float64)
    if c == 3:
        return np.asarray(rgb, dtype=np.float64)
    return np.asarray(tuple(rgb) + (1.0,) * (c - 3), dtype=np.float64)[:c]


def _relative_luminance(rgb):
    """WCAG の相対輝度(sRGB 逆ガンマつき)。"""
    out = 0.0
    for c, w in zip(rgb, (0.2126, 0.7152, 0.0722)):
        c = float(c)
        lin = c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
        out += w * lin
    return out


def _contrast_ratio(rgb_a, rgb_b):
    """WCAG のコントラスト比 (L1+0.05)/(L2+0.05) ∈ [1, 21]。"""
    la, lb = _relative_luminance(rgb_a), _relative_luminance(rgb_b)
    hi, lo = (la, lb) if la >= lb else (lb, la)
    return (hi + 0.05) / (lo + 0.05)


def _style(style, width=None):
    """``imagedraw`` へ**素通し**する追加引数。中身は解釈しない。

    線種(破線・点線)の引数が ``imagedraw`` 側に増えたとき、この層を
    変更せずに ``style={"dash": (6, 3)}`` のように渡せる。
    """
    if style is None:
        kw = {}
    elif isinstance(style, dict):
        kw = dict(style)
    else:
        raise ValueError(f"style must be a dict of imagedraw keyword arguments (got: {type(style).__name__})")
    for k in kw:
        if not isinstance(k, str):
            raise ValueError(f"style keys must be strings (got: {k!r})")
    if "color" in kw:
        raise ValueError("style must not carry 'color' — pass color= so the palette role is resolved")
    if width is not None:
        kw.setdefault("width", int(width))
    return kw


def _rect(rect, name="rect"):
    """``(x,y,w,h)`` を検算して int 四つ組にする。w/h は正でなければならない。"""
    r = np.asarray(rect, dtype=np.float64).ravel()
    if r.size != 4:
        raise ValueError(f"{name} must be (x, y, w, h) (got {r.size} values)")
    _finite(name, r)
    x, y, w, h = (int(round(v)) for v in r)
    if w <= 0 or h <= 0:
        raise ValueError(f"{name} width/height must be positive (got: w={w}, h={h})")
    return x, y, w, h


def _check_inside(a, rect, name="rect", what="rectangle"):
    """矩形が画像の中に完全に収まっていることを確認する(はみ出しは例外)。"""
    H, W = a.shape[:2]
    x, y, w, h = rect
    over = []
    if x < 0:
        over.append(f"left by {-x}px")
    if y < 0:
        over.append(f"top by {-y}px")
    if x + w > W:
        over.append(f"right by {x + w - W}px")
    if y + h > H:
        over.append(f"bottom by {y + h - H}px")
    if over:
        raise ValueError(
            f"{what} {name}=({x},{y},{w},{h}) does not fit in the {W}x{H} image — "
            f"it overflows {', '.join(over)}; move it or shrink it "
            "(clipping it silently would hide part of the figure's meaning)")


def _blend(a, weight, color, alpha=1.0):
    """``out = w*color + (1-w)*a``(w = weight*alpha)。**この順が正典**。"""
    w = np.clip(np.asarray(weight, dtype=np.float64) * float(alpha), 0.0, 1.0)
    if a.ndim == 2:
        return a * (1.0 - w) + float(np.mean(color) if np.ndim(color) else color) * w
    col = np.asarray(color, dtype=np.float64).reshape(1, 1, -1)
    return a * (1.0 - w)[..., None] + col * w[..., None]


# ------------------------------------------------------------------ #
# 文字 —— 幅を測ってから描く
# ------------------------------------------------------------------ #

def _pil():
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:                                   # pragma: no cover
        raise ImportError(
            "drawing text needs Pillow (pip install 'fullseye[pil]'); the non-text "
            "annotate ops (arrow / overlay_mask / plot_series / shapes) work without it"
        ) from exc
    return Image, ImageDraw, ImageFont


@functools.lru_cache(maxsize=64)
def _font(size, font_path=None):
    """サイズとパスからフォントを引く(固定順・キャッシュつき=決定的)。"""
    _, _, ImageFont = _pil()
    size = int(size)
    if size < 1:
        raise ValueError(f"font size must be >= 1 (got: {size})")
    if font_path is not None:
        return ImageFont.truetype(font_path, size)               # 見つからなければ例外(黙って代替しない)
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size)
    except TypeError:                                            # pragma: no cover (Pillow < 10.1)
        return ImageFont.load_default()


@functools.lru_cache(maxsize=8)
def _measurer():
    Image, ImageDraw, _ = _pil()
    return ImageDraw.Draw(Image.new("L", (1, 1)))


def _text_width(text, font):
    return float(_measurer().textlength(text, font=font))


def _line_height(font):
    try:
        ascent, descent = font.getmetrics()
        return int(ascent + descent)
    except AttributeError:                                       # pragma: no cover
        box = font.getbbox("Ag")
        return int(box[3] - box[1])


def _wrap(text, font, max_width):
    """幅に収まるよう折り返す。**黙って切らない**。

    日本語には空白が無いので単語境界ではなく 1 文字ずつ詰めて測る。1 文字すら
    入らない極端な幅のときだけ、そのまま 1 行にする(無限ループにしない)。
    """
    lines = []
    for para in str(text).split("\n"):
        if not para:
            lines.append("")
            continue
        cur = ""
        for ch in para:
            trial = cur + ch
            if _text_width(trial, font) <= max_width or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = ch
        if cur:
            lines.append(cur)
    return lines or [""]


def measure_text(text, font_size=14, font_path=None, max_width=None,
                 min_font_size=9, line_spacing=1.15, wrap=True):
    """文字を**描く前に**測る。収まらないなら折り返すか縮め、駄目なら例外。

    Parameters
    ----------
    text : str
        測る文字列(``\\n`` で改行)。
    font_size : int
        希望のサイズ。``max_width`` に入らなければ 1pt ずつ縮める。
    font_path : str or None
        明示すると機械をまたいでも同じ結果になる。None は :data:`FONT_CANDIDATES`
        を固定順で探す。
    max_width : int or None
        入れたい幅[px]。None なら縮小も折り返しもしない。
    min_font_size : int
        ここまで縮めても入らなければ **ValueError**(黙って切らない)。
    line_spacing : float
        行送り係数。
    wrap : bool
        True(既定)なら ``max_width`` で**折り返す**。False なら折り返さず
        **行を増やさずフォントを縮めて**収める(格子のラベルのように、2 行に
        なると版が崩れる場所で使う ―― ``exhibit_tile._fit_label`` と同じ流儀)。
        どちらでも ``min_font_size`` まで来て入らなければ例外。
        ``\n`` の改行は ``max_width`` の有無・``wrap`` の値に**よらず常に**効く
        (幅を与えないと 1 行に潰れる、という事故は起きない)。

    Returns
    -------
    dict
        ``{"lines", "font", "font_size", "width", "height", "line_height"}``。
        ``width``/``height`` は実測[px]。

    Raises
    ------
    ValueError
        ``max_width`` が非正 / ``min_font_size`` まで縮めても 1 行が入らない。
    """
    if not isinstance(text, str):
        text = str(text)
    font_size = int(font_size)
    min_font_size = int(min_font_size)
    if font_size < 1 or min_font_size < 1:
        raise ValueError(f"font sizes must be >= 1 (got: {font_size}, {min_font_size})")
    if min_font_size > font_size:
        raise ValueError(f"min_font_size {min_font_size} > font_size {font_size}")
    if max_width is not None:
        max_width = int(max_width)
        if max_width <= 0:
            raise ValueError(f"max_width must be positive (got: {max_width})")
    if not (line_spacing > 0.0) or not math.isfinite(line_spacing):
        raise ValueError(f"line_spacing must be positive and finite (got: {line_spacing})")

    for size in range(font_size, min_font_size - 1, -1):
        font = _font(size, font_path)
        # 改行(``\n``)は max_width / wrap と**無関係に常に**効く。PIL の textlength
        # は複数行を測れないので、ここで分けないと "a\nb" は幅なしで例外になる。
        # 折り返し(幅で切る)だけが「幅あり かつ wrap=True」に限られる。
        if max_width is None or not wrap:
            lines = text.split("\n")
        else:
            lines = _wrap(text, font, max_width)
        widths = [_text_width(s, font) for s in lines]
        w = max(widths) if widths else 0.0
        if max_width is None or w <= max_width:
            lh = int(round(_line_height(font) * line_spacing))
            return {"lines": lines, "font": font, "font_size": size,
                    "width": int(math.ceil(w)), "height": int(lh * len(lines)),
                    "line_height": lh}
    raise ValueError(
        f"text {text!r} does not fit in {max_width}px even at font size {min_font_size} "
        "— shorten it, widen the box, or lower min_font_size (truncating it silently is "
        "not an option: a machine check cannot see clipped text)")


def _text_mask(shape, lines, font, x, y, line_height):
    """文字を [0,1] のマスクとして焼く(アンチエイリアスを重みとして使う)。"""
    Image, ImageDraw, _ = _pil()
    im = Image.new("L", (int(shape[1]), int(shape[0])), 0)
    d = ImageDraw.Draw(im)
    for i, line in enumerate(lines):
        if line:
            d.text((int(x), int(y + i * line_height)), line, fill=255, font=font)
    return np.asarray(im, dtype=np.float64) / 255.0


def _anchor_origin(anchor, x, y, w, h):
    """アンカー名と基準点から矩形左上を求める。``anchor`` は 'lt'…'rb'。"""
    if anchor not in _ANCHORS:
        raise ValueError(f"anchor must be one of {_ANCHORS} (got: {anchor!r})")
    hx, vy = anchor[0], anchor[1]
    ox = x if hx == "l" else (x - w // 2 if hx == "c" else x - w)
    oy = y if vy == "t" else (y - h // 2 if vy == "m" else y - h)
    return int(ox), int(oy)


def text_box(img, text, xy, color="neutral", text_color=None, box_color=None,
             box_alpha=0.72, anchor="lt", pad=5, font_size=14, min_font_size=9,
             max_width=None, font_path=None, line_spacing=1.15, scheme="okabe_ito",
             min_contrast=DEFAULT_MIN_CONTRAST, border=0, border_color=None,
             style=None, wrap=True):
    """下敷き(半透明の板)つきの文字。**はみ出しは黙って切らず例外**。

    Parameters
    ----------
    img : ndarray
        ``(H,W)`` か ``(H,W,C)``、float [0,1]。
    text : str
        描く文字列。
    xy : (x, y)
        アンカーの位置(**x=col, y=row**、row は下向き)。
    color : str or sequence
        役割名または RGB。``text_color`` 未指定ならこれが**枠の色**として
        使われ、文字は読みやすい既定色になる。
    text_color, box_color : str/sequence or None
        文字色・板の色。None なら既定(明るい文字 × 暗い板)。文字色が None の
        ときは、**実際に下に出る色**に対して明るい既定色が ``min_contrast`` を
        割る場合に限り、暗い文字(板の色)へ自動で切り替える ―― 板なし
        (``box_alpha=0``)で白地に置く目盛り・カラーバー・凡例のラベルが
        白に溶けないため。``text_color`` を明示したときは切り替えない
        (色は図の意味なので勝手に変えず、読めなければ例外にする)。
    box_alpha : float
        板の不透明度 [0,1]。``0`` なら板を描かない(目盛りラベル向け)。
    anchor : str
        ``'lt','ct','rt','lm','cm','rm','lb','cb','rb'`` の 9 通り。
    pad : int
        板の内側余白[px]。
    max_width : int or None
        文字の折り返し幅。None なら 1 行のまま。
    wrap : bool
        False なら折り返さず 1 行のまま縮めて ``max_width`` に収める。
    min_contrast : float
        文字と「実際にその下に出る色」のコントラスト比の下限。下回れば
        **ValueError**(背景と同化した文字は誰も気づけないので通さない)。
        **限界(正直に)**: 比べる相手は板の下の**平均色**なので、
        白と黒が半々に混じった写真の上に ``box_alpha=0`` で置くと、平均は
        中間灰になり検査を通ってしまう(白い部分の上の文字は読めない)。
        地が荒れている場所では ``box_alpha`` を上げて板を効かせること ――
        この検査は「板を忘れた」を捕まえるためのもので、
        「板があっても読めない」まで保証はしない。
    border : int
        板の枠線の太さ(0 で枠なし)。色は ``border_color`` か ``color``。
    style : dict or None
        枠線を引く :func:`imagedraw.draw_polyline` へ**素通し**する引数。

    Returns
    -------
    ndarray
        同じ shape の新しい配列。

    Raises
    ------
    ValueError
        板が画像からはみ出す / 文字が収まらない / コントラスト不足 /
        未知の役割名・アンカー / 負の余白。
    """
    a = _prep(img)
    if pad < 0:
        raise ValueError(f"pad must be >= 0 (got: {pad})")
    if not (0.0 <= float(box_alpha) <= 1.0):
        raise ValueError(f"box_alpha must be within [0,1] (got: {box_alpha})")
    if border < 0:
        raise ValueError(f"border must be >= 0 (got: {border})")
    _finite("xy", xy)

    ink = None if text_color is None else _rgb(text_color, scheme)
    plate = _rgb(_PLATE_RGB if box_color is None else box_color, scheme)
    edge = _rgb(color if border_color is None else border_color, scheme)

    inner_max = None if max_width is None else int(max_width) - 2 * pad
    if inner_max is not None and inner_max <= 0:
        raise ValueError(f"max_width {max_width} leaves no room for text after pad={pad}")
    m = measure_text(text, font_size=font_size, font_path=font_path,
                     max_width=inner_max, min_font_size=min_font_size,
                     line_spacing=line_spacing, wrap=wrap)
    bw, bh = m["width"] + 2 * pad, m["height"] + 2 * pad
    x0, y0 = _anchor_origin(anchor, int(round(xy[0])), int(round(xy[1])), bw, bh)
    _check_inside(a, (x0, y0, bw, bh), name="text box", what="text plate")

    # 板 → 文字 の順で重ねる(逆にすると文字が板の下に沈む)。
    if box_alpha > 0.0:
        w = np.zeros(a.shape[:2], dtype=np.float64)
        w[y0:y0 + bh, x0:x0 + bw] = 1.0
        a = _blend(a, w, _channel_color(a, plate, scheme), box_alpha)

    # 実際に文字の下に出る色でコントラストを測る(板が半透明なら下地が透ける)。
    under = a[y0:y0 + bh, x0:x0 + bw]
    under_rgb = (float(np.mean(under)),) * 3 if a.ndim == 2 else \
        tuple(float(v) for v in np.mean(under.reshape(-1, under.shape[-1]), axis=0)[:3])
    if len(under_rgb) < 3:
        under_rgb = (under_rgb[0],) * 3
    if ink is None:
        # 既定は明るい文字。ただし板が無い/薄い/明るい場所ではそれが地に溶ける
        # ので、既定色が min_contrast を割るときだけ暗い文字へ切り替える(両方
        # 駄目なら良い方を選び、下の検査が例外にする)。既定色が読める限り
        # 従来と同じ色を出すので、通っていた絵はバイト単位で変わらない。
        light, dark = _rgb(_INK_RGB, scheme), _rgb(_PLATE_RGB, scheme)
        ink = light
        if (_contrast_ratio(light, under_rgb) < float(min_contrast)
                and _contrast_ratio(dark, under_rgb) > _contrast_ratio(light, under_rgb)):
            ink = dark
    ratio = _contrast_ratio(ink, under_rgb)
    if ratio < float(min_contrast):
        raise ValueError(
            f"text colour {tuple(round(c, 3) for c in ink)} sits at contrast {ratio:.2f} "
            f"against what is actually under it {tuple(round(c, 3) for c in under_rgb)} "
            f"(minimum {min_contrast}) — the label would be there but unreadable; "
            "raise box_alpha, darken the plate, or pick a lighter text colour")

    mask = _text_mask(a.shape[:2], m["lines"], m["font"], x0 + pad, y0 + pad, m["line_height"])
    a = _blend(a, mask, _channel_color(a, ink, scheme), 1.0)

    if border > 0:
        pts = [(x0, y0), (x0 + bw - 1, y0), (x0 + bw - 1, y0 + bh - 1), (x0, y0 + bh - 1)]
        a = imagedraw.draw_polyline(a, pts, color=_channel_color(a, edge, scheme),
                                    closed=True, **_style(style, border))
    return a


# ------------------------------------------------------------------ #
# 指し示す
# ------------------------------------------------------------------ #

def _head_polygon(p0, p1, head_len, head_width):
    """p1 を先端とする矢じり三角形の 3 点(x,y)。"""
    dx, dy = float(p1[0] - p0[0]), float(p1[1] - p0[1])
    n = math.hypot(dx, dy)
    if n < 1e-12:
        raise ValueError("arrow endpoints coincide — direction is undefined")
    ux, uy = dx / n, dy / n
    bx, by = p1[0] - ux * head_len, p1[1] - uy * head_len
    px, py = -uy, ux
    return [(p1[0], p1[1]),
            (bx + px * head_width / 2.0, by + py * head_width / 2.0),
            (bx - px * head_width / 2.0, by - py * head_width / 2.0)], (bx, by)


def arrow(img, p0, p1, color="emphasis", width=2, head_len=12.0, head_width=9.0,
          scheme="okabe_ito", style=None):
    """``p0`` から ``p1`` へ矢印(軸は :func:`imagedraw.draw_line`、矢じりは塗り)。

    Parameters
    ----------
    p0, p1 : (x, y)
        起点・先端。**x=col, y=row**。
    head_len, head_width : float
        矢じりの長さ・幅[px]。``0`` で線分のみ。軸より矢じりが長い短距離の
        矢印では、矢じりを軸長の 8 割まで**相似に縮める**(そうしないと
        矢じりの根元が起点の手前に来て、軸が逆向きに描かれる)。
    style : dict or None
        軸線を引く :func:`imagedraw.draw_line` への素通し引数(破線など)。

    Returns
    -------
    ndarray

    Raises
    ------
    ValueError
        端点が非有限/一致、負の太さ・矢じり寸法、両端とも画像の外。
    """
    a = _prep(img)
    _finite("p0/p1", p0, p1)
    if width < 1:
        raise ValueError(f"width must be >= 1 (got: {width})")
    if head_len < 0 or head_width < 0:
        raise ValueError(f"head_len/head_width must be >= 0 (got: {head_len}, {head_width})")
    if float(p0[0]) == float(p1[0]) and float(p0[1]) == float(p1[1]):
        raise ValueError(
            f"arrow endpoints coincide at {tuple(p0)} — an arrow with no direction points at "
            "nothing; it would be drawn as a dot and read as a marker")
    H, W = a.shape[:2]
    inside = [(0 <= p[0] <= W - 1 and 0 <= p[1] <= H - 1) for p in (p0, p1)]
    if not any(inside):
        raise ValueError(
            f"arrow {tuple(p0)}->{tuple(p1)} lies entirely outside the {W}x{H} image "
            "(imagedraw would clamp it to the border and draw a wrong line)")
    col = _channel_color(a, color, scheme)
    if head_len > 0.0 and head_width > 0.0:
        # 矢じりが軸より長いと、根元が起点の**手前**に来て軸が逆向きに描かれる。
        # 短い矢印では矢じりを相似に縮める(絵は「p0 から p1 への矢印」のまま)。
        span = math.hypot(float(p1[0] - p0[0]), float(p1[1] - p0[1]))
        if head_len > 0.8 * span:
            k = (0.8 * span) / head_len
            head_len, head_width = head_len * k, head_width * k
        tri, base = _head_polygon(p0, p1, head_len, head_width)
        a = imagedraw.draw_line(a, p0, base, color=col, **_style(style, width))
        a = filled_polygon(a, tri, color=color, scheme=scheme)
    else:
        a = imagedraw.draw_line(a, p0, p1, color=col, **_style(style, width))
    return a


def leader_line(img, anchor_xy, target_xy, text=None, color="emphasis", width=2,
                cap="dot", cap_size=4, elbow=True, scheme="okabe_ito",
                style=None, **text_kw):
    """引き出し線 —— 注記の位置(``anchor_xy``)から対象(``target_xy``)へ。

    ``elbow=True`` なら水平 → 斜めの 2 折れで引く(注記が本体に被りにくい)。
    端点には ``cap`` の印(``'dot'``/``'arrow'``/``'cross'``/``'none'``)を置く。
    ``text`` を渡すと ``anchor_xy`` 側に :func:`text_box` を置く。
    追加の ``**text_kw`` は :func:`text_box` へそのまま渡す。

    Raises
    ------
    ValueError
        未知の ``cap``、非有限な座標、線が画像の外。
    """
    a = _prep(img)
    _finite("anchor_xy/target_xy", anchor_xy, target_xy)
    if cap not in ("dot", "arrow", "cross", "none"):
        raise ValueError(f"cap must be 'dot'|'arrow'|'cross'|'none' (got: {cap!r})")
    H, W = a.shape[:2]
    for name, p in (("anchor_xy", anchor_xy), ("target_xy", target_xy)):
        if not (0 <= p[0] <= W - 1 and 0 <= p[1] <= H - 1):
            raise ValueError(f"{name}={tuple(p)} is outside the {W}x{H} image")
    col = _channel_color(a, color, scheme)
    ax, ay = float(anchor_xy[0]), float(anchor_xy[1])
    tx, ty = float(target_xy[0]), float(target_xy[1])
    if elbow and abs(tx - ax) > 1.0:
        mid = (ax + (tx - ax) * 0.35, ay)
        a = imagedraw.draw_polyline(a, [(ax, ay), mid, (tx, ty)], color=col,
                                    **_style(style, width))
        prev = mid
    else:
        a = imagedraw.draw_line(a, (ax, ay), (tx, ty), color=col, **_style(style, width))
        prev = (ax, ay)
    if cap == "dot":
        a = imagedraw.draw_circle(a, (tx, ty), cap_size, color=col, fill=True)
    elif cap == "cross":
        a = imagedraw.draw_markers(a, [(tx, ty)], color=col, size=cap_size,
                                   shape="cross", width=width)
    elif cap == "arrow":
        a = arrow(a, prev, (tx, ty), color=color, width=width,
                  head_len=max(6.0, 2.0 * cap_size), head_width=max(5.0, 1.6 * cap_size),
                  scheme=scheme, style=style)
    if text is not None:
        anchor = text_kw.pop("anchor", "rm" if tx >= ax else "lm")
        a = text_box(a, text, (ax, ay), color=color, anchor=anchor, scheme=scheme, **text_kw)
    return a


#: :func:`label_points` が試す配置候補(**固定順** = 決定的)。
_LABEL_OFFSETS = ((9, -9), (9, 9), (-9, -9), (-9, 9), (0, -16), (0, 16), (18, 0), (-18, 0))


def label_points(img, points, labels=None, color="reference", font_size=12,
                 pad=3, marker_size=0, scheme="okabe_ito", allow_overlap=False,
                 **text_kw):
    """点群に番号や値を振る。**重なりを避けて置く**(避けられなければ例外)。

    Parameters
    ----------
    points : (N,2)
        **(x,y)** の点列。
    labels : sequence or None
        各点の文字。None なら 1 始まりの番号。
    marker_size : int
        0 より大きければ各点に十字マーカーも打つ。
    allow_overlap : bool
        True なら重なりを許して最初の候補に置く(既定は False = 例外)。

    Returns
    -------
    ndarray

    Raises
    ------
    ValueError
        点が空 / 非有限 / labels の数が合わない / どの候補位置でも
        既存のラベルと重なる(``allow_overlap=False`` のとき)。
    """
    a = _prep(img)
    pts = np.asarray(points, dtype=np.float64).reshape(-1, 2)
    if pts.shape[0] == 0:
        raise ValueError("points is empty — nothing to label")
    _finite("points", pts)
    if labels is None:
        labels = [str(i + 1) for i in range(pts.shape[0])]
    labels = [str(s) for s in labels]
    if len(labels) != pts.shape[0]:
        raise ValueError(f"labels has {len(labels)} entries for {pts.shape[0]} points")

    taken = []
    for (x, y), text in zip(pts, labels):
        m = measure_text(text, font_size=font_size, min_font_size=text_kw.get("min_font_size", 9),
                         font_path=text_kw.get("font_path"))
        bw, bh = m["width"] + 2 * pad, m["height"] + 2 * pad
        placed = None
        for dx, dy in _LABEL_OFFSETS:
            anchor = ("l" if dx >= 0 else "r") + ("b" if dy < 0 else ("t" if dy > 0 else "m"))
            ox, oy = _anchor_origin(anchor, int(round(x + dx)), int(round(y + dy)), bw, bh)
            if ox < 0 or oy < 0 or ox + bw > a.shape[1] or oy + bh > a.shape[0]:
                continue
            box = (ox, oy, bw, bh)
            if allow_overlap or not any(_overlaps(box, t) for t in taken):
                placed = (x + dx, y + dy, anchor, box)
                break
        if placed is None:
            raise ValueError(
                f"label {text!r} for point ({x:.1f},{y:.1f}) has no free spot: every one of "
                f"the {len(_LABEL_OFFSETS)} candidate offsets either leaves the image or "
                "collides with an already placed label — thin the points, shrink the font, "
                "or pass allow_overlap=True if a pile-up is acceptable")
        px, py, anchor, box = placed
        taken.append(box)
        if marker_size > 0:
            a = imagedraw.draw_markers(a, [(x, y)], color=_channel_color(a, color, scheme),
                                       size=marker_size, shape="cross", width=1)
        a = text_box(a, text, (px, py), color=color, anchor=anchor, pad=pad,
                     font_size=font_size, scheme=scheme, **text_kw)
    return a


def _overlaps(r0, r1):
    return not (r0[0] + r0[2] <= r1[0] or r1[0] + r1[2] <= r0[0] or
                r0[1] + r0[3] <= r1[1] or r1[1] + r1[3] <= r0[1])


def crosshair(img, xy, color="emphasis", width=1, gap=6, extent=None,
              scheme="okabe_ito", style=None):
    """断面の交差線(MPR で使う)。``gap`` だけ中心を空けて視点を隠さない。

    Parameters
    ----------
    xy : (x, y)
        交点。
    gap : int
        中心を空ける半径 [px] (0 で全通し)。
    extent : int or None
        中心からの腕の長さ[px]。None なら画像の端まで。

    Raises
    ------
    ValueError
        交点が画像の外、負の gap/extent。
    """
    a = _prep(img)
    _finite("xy", xy)
    H, W = a.shape[:2]
    x, y = float(xy[0]), float(xy[1])
    if not (0 <= x <= W - 1 and 0 <= y <= H - 1):
        raise ValueError(f"crosshair centre {(x, y)} is outside the {W}x{H} image")
    if gap < 0:
        raise ValueError(f"gap must be >= 0 (got: {gap})")
    if extent is not None and extent <= 0:
        raise ValueError(f"extent must be positive (got: {extent})")
    x0, x1 = (0.0, W - 1.0) if extent is None else (max(0.0, x - extent), min(W - 1.0, x + extent))
    y0, y1 = (0.0, H - 1.0) if extent is None else (max(0.0, y - extent), min(H - 1.0, y + extent))
    col = _channel_color(a, color, scheme)
    kw = _style(style, width)
    for p, q in (((x0, y), (x - gap, y)), ((x + gap, y), (x1, y)),
                 ((x, y0), (x, y - gap)), ((x, y + gap), (x, y1))):
        if q[0] >= p[0] and q[1] >= p[1]:
            a = imagedraw.draw_line(a, p, q, color=col, **kw)
    return a


# ------------------------------------------------------------------ #
# 図の備品(凡例 / カラーバー / スケールバー)
# ------------------------------------------------------------------ #

def legend_box(img, entries, xy, anchor="lt", swatch=14, row_gap=4, pad=8,
               font_size=13, box_color=None, box_alpha=0.72, markers=False,
               scheme="okabe_ito", font_path=None, min_font_size=9, style=None,
               border=1, border_color="neutral"):
    """色 × 説明の凡例。**箱の高さは要素数から閉形式で決まる**。

    ``height = 2*pad + n*row_h + (n-1)*row_gap`` (``row_h = max(swatch, 文字高))。

    Parameters
    ----------
    entries : sequence
        ``(color, text)`` の並び。``color`` は役割名でも RGB でもよい。
    markers : bool
        True なら役割名に対応する :data:`palette.ROLE_MARKERS` の記号を
        説明の前に付ける(**色だけに意味を載せない**ため)。役割名でない
        要素には記号が無いので付かない。

    Returns
    -------
    ndarray

    Raises
    ------
    ValueError
        entries が空 / 形が ``(color, text)`` でない / 箱が画像からはみ出す /
        未知の役割名。
    """
    a = _prep(img)
    items = list(entries)
    if not items:
        raise ValueError("entries is empty — a legend with no rows is a lie about the figure")
    rows = []
    for i, ent in enumerate(items):
        if not (isinstance(ent, (tuple, list)) and len(ent) == 2):
            raise ValueError(f"entries[{i}] must be a (color, text) pair (got: {ent!r})")
        col, text = ent
        text = str(text)
        if markers and isinstance(col, str) and col in palette.ROLE_MARKERS:
            text = f"{palette.ROLE_MARKERS[col]} {text}"
        rows.append((col, text))
    if pad < 0 or row_gap < 0 or swatch < 1:
        raise ValueError(f"pad/row_gap must be >= 0 and swatch >= 1 (got: {pad}, {row_gap}, {swatch})")

    ms = [measure_text(t, font_size=font_size, font_path=font_path,
                       min_font_size=min_font_size) for _, t in rows]
    row_h = max(int(swatch), max(m["height"] for m in ms))
    text_w = max(m["width"] for m in ms)
    bw = 2 * pad + int(swatch) + 8 + text_w
    bh = 2 * pad + len(rows) * row_h + (len(rows) - 1) * int(row_gap)
    x0, y0 = _anchor_origin(anchor, int(round(xy[0])), int(round(xy[1])), bw, bh)
    _check_inside(a, (x0, y0, bw, bh), name="legend", what="legend box")

    plate = _rgb(_PLATE_RGB if box_color is None else box_color, scheme)
    if box_alpha > 0.0:
        w = np.zeros(a.shape[:2], dtype=np.float64)
        w[y0:y0 + bh, x0:x0 + bw] = 1.0
        a = _blend(a, w, _channel_color(a, plate, scheme), box_alpha)
    if border > 0:
        pts = [(x0, y0), (x0 + bw - 1, y0), (x0 + bw - 1, y0 + bh - 1), (x0, y0 + bh - 1)]
        a = imagedraw.draw_polyline(a, pts, color=_channel_color(a, border_color, scheme),
                                    closed=True, **_style(style, border))
    for i, ((col, text), m) in enumerate(zip(rows, ms)):
        ry = y0 + pad + i * (row_h + int(row_gap))
        sw = np.zeros(a.shape[:2], dtype=np.float64)
        sy = ry + (row_h - int(swatch)) // 2
        sw[sy:sy + int(swatch), x0 + pad:x0 + pad + int(swatch)] = 1.0
        a = _blend(a, sw, _channel_color(a, col, scheme), 1.0)
        a = text_box(a, text, (x0 + pad + int(swatch) + 8, ry + row_h // 2), anchor="lm",
                     pad=0, box_alpha=0.0, font_size=m["font_size"], font_path=font_path,
                     min_font_size=min_font_size, scheme=scheme)
    return a


def color_bar(img, lut, rect, vmin=0.0, vmax=1.0, unit="", label_fmt="{:g}",
              orientation="vertical", font_size=12, font_path=None,
              scheme="okabe_ito", border=1, border_color="neutral",
              text_color=None, style=None):
    """LUT の凡例(カラーバー)。最小・最大・単位のラベルつき。

    Parameters
    ----------
    lut : (n,3) or (n,)
        色対応表。float [0,1]。:func:`palette.diverging_lut` の出力をそのまま。
    rect : (x, y, w, h)
        バーの矩形(左上基準)。
    vmin, vmax : float
        両端の値。``vmin == vmax`` は**目盛りの意味が消える**ので ValueError。
    orientation : {'vertical','horizontal'}
        ``'vertical'`` は **上が vmax**(row は下向きなので LUT を反転する)。

    Returns
    -------
    ndarray

    Raises
    ------
    ValueError
        LUT の形/値域、矩形のはみ出し、vmin==vmax、未知の orientation。
    """
    a = _prep(img)
    t = np.asarray(lut, dtype=np.float64)
    if t.ndim == 1:
        t = np.repeat(t[:, None], 3, axis=1)
    if t.ndim != 2 or t.shape[1] < 3 or t.shape[0] < 2:
        raise ValueError(f"lut must be (n>=2, 3) float in [0,1] (got: {t.shape})")
    if not np.all(np.isfinite(t)) or t.min() < 0.0 or t.max() > 1.0:
        raise ValueError("lut values must be finite and within [0,1]")
    if orientation not in ("vertical", "horizontal"):
        raise ValueError(f"orientation must be 'vertical'|'horizontal' (got: {orientation!r})")
    _finite("vmin/vmax", vmin, vmax)
    if float(vmin) == float(vmax):
        raise ValueError(f"vmin == vmax == {vmin} — a colour bar over a zero range says nothing")
    x, y, w, h = _rect(rect)
    _check_inside(a, (x, y, w, h), name="color bar", what="colour bar")

    n = t.shape[0]
    if orientation == "vertical":
        idx = np.clip(((h - 1 - np.arange(h)) * (n - 1) // max(1, h - 1)), 0, n - 1)
        band = t[idx][:, None, :].repeat(w, axis=1)
    else:
        idx = np.clip((np.arange(w) * (n - 1) // max(1, w - 1)), 0, n - 1)
        band = t[idx][None, :, :].repeat(h, axis=0)
    if a.ndim == 2:
        a[y:y + h, x:x + w] = band.mean(axis=2)
    else:
        c = a.shape[2]
        blk = band[:, :, :3]
        if c == 1:
            a[y:y + h, x:x + w, 0] = blk.mean(axis=2)
        else:
            a[y:y + h, x:x + w, :3] = blk
            if c == 4:
                a[y:y + h, x:x + w, 3] = 1.0
    if border > 0:
        pts = [(x, y), (x + w - 1, y), (x + w - 1, y + h - 1), (x, y + h - 1)]
        a = imagedraw.draw_polyline(a, pts, color=_channel_color(a, border_color, scheme),
                                    closed=True, **_style(style, border))

    hi = label_fmt.format(float(vmax)) + (f" {unit}" if unit else "")
    lo = label_fmt.format(float(vmin)) + (f" {unit}" if unit else "")
    if orientation == "vertical":
        a = text_box(a, hi, (x + w + 4, y), anchor="lt", pad=2, box_alpha=0.0,
                     font_size=font_size, font_path=font_path, text_color=text_color,
                     scheme=scheme)
        a = text_box(a, lo, (x + w + 4, y + h), anchor="lb", pad=2, box_alpha=0.0,
                     font_size=font_size, font_path=font_path, text_color=text_color,
                     scheme=scheme)
    else:
        a = text_box(a, lo, (x, y + h + 4), anchor="lt", pad=2, box_alpha=0.0,
                     font_size=font_size, font_path=font_path, text_color=text_color,
                     scheme=scheme)
        a = text_box(a, hi, (x + w, y + h + 4), anchor="rt", pad=2, box_alpha=0.0,
                     font_size=font_size, font_path=font_path, text_color=text_color,
                     scheme=scheme)
    return a


def scale_bar(img, length, units_per_pixel, unit="µm", xy=None, anchor="rb",
              color="neutral", thickness=5, margin=14, font_size=13, label=True,
              label_fmt="{:g}", font_path=None, scheme="okabe_ito", text_color=None):
    """物理長のスケールバー。**画素↔物理の換算は引数で受ける**(勝手に決めない)。

    バーの画素長は ``round(length / units_per_pixel)`` ―― これが構成的な真値で、
    :mod:`tests.test_annotate` はこの一致を数字で確かめている。

    Parameters
    ----------
    length : float
        バーが表す物理長(``unit`` の単位で)。
    units_per_pixel : float
        1 画素が何 ``unit`` に相当するか。倍率ではなく**分解能**を渡す。
    unit : str
        単位の表記(``'µm'``, ``'mm'``, ``'px'`` など)。
    xy : (x,y) or None
        バーの基準点。None なら ``anchor`` 側の隅から ``margin`` 内側。
    label : bool
        ``"200 µm"`` のラベルを併記するか。

    Returns
    -------
    ndarray

    Raises
    ------
    ValueError
        length / units_per_pixel が非正・非有限、画素長が 1 未満、
        バー(とラベル)が画像に収まらない。
    """
    a = _prep(img)
    _finite("length/units_per_pixel", length, units_per_pixel)
    if float(length) <= 0.0 or float(units_per_pixel) <= 0.0:
        raise ValueError(f"length and units_per_pixel must be positive "
                         f"(got: {length}, {units_per_pixel})")
    if thickness < 1 or margin < 0:
        raise ValueError(f"thickness must be >= 1 and margin >= 0 (got: {thickness}, {margin})")
    px = int(round(float(length) / float(units_per_pixel)))
    if px < 1:
        raise ValueError(
            f"{length} {unit} is {float(length) / float(units_per_pixel):.3f} px at "
            f"{units_per_pixel} {unit}/px — a bar shorter than one pixel cannot be read; "
            "pick a longer length")
    H, W = a.shape[:2]
    if px > W:
        raise ValueError(f"the bar is {px}px but the image is only {W}px wide")
    if xy is None:
        if anchor not in _ANCHORS:
            raise ValueError(f"anchor must be one of {_ANCHORS} (got: {anchor!r})")
        bx = margin if anchor[0] == "l" else (W - margin if anchor[0] == "r" else W // 2)
        by = margin if anchor[1] == "t" else (H - margin if anchor[1] == "b" else H // 2)
    else:
        _finite("xy", xy)
        bx, by = int(round(xy[0])), int(round(xy[1]))
    x0, y0 = _anchor_origin(anchor, bx, by, px, int(thickness))
    _check_inside(a, (x0, y0, px, int(thickness)), name="scale bar", what="scale bar")

    w = np.zeros(a.shape[:2], dtype=np.float64)
    w[y0:y0 + int(thickness), x0:x0 + px] = 1.0
    a = _blend(a, w, _channel_color(a, color, scheme), 1.0)
    if label:
        a = text_box(a, f"{label_fmt.format(float(length))} {unit}",
                     (x0 + px // 2, y0 - 3), anchor="cb", pad=3, box_alpha=0.55,
                     font_size=font_size, font_path=font_path, text_color=text_color,
                     scheme=scheme)
    return a


# ------------------------------------------------------------------ #
# グラフ(matplotlib を使わない)
# ------------------------------------------------------------------ #

def axes_transform(rect, xlim, ylim, invert_y=True, xscale="linear", yscale="linear"):
    """データ座標 → 画素座標の対応(**閉形式**)を作る。

    ``row は下向き`` という画像の事実と、``y は上向き`` というグラフの慣習の
    ずれを、**この 1 か所だけ**で吸収する。図のコードはこの辞書を持ち回る。

        px = x0 + (x - xmin)/(xmax - xmin) * (w - 1)
        py = y0 + (h - 1) - (y - ymin)/(ymax - ymin) * (h - 1)     # invert_y

    Parameters
    ----------
    rect : (x, y, w, h)
        描画域(左上基準、画素)。
    xlim, ylim : (lo, hi)
        データ範囲。lo == hi は**傾きが無限大**になるので ValueError。
        **lo > hi(反転軸)も許す** ―― 深度やランクを上下逆に描くため。
    invert_y : bool
        True(既定)なら ``ylim[0]`` が**下端**に来る = 普通のグラフ。
        False なら画像そのままの向き(上端が ``ylim[0]``)。
    xscale, yscale : {'linear','log'}
        ``'log'`` は常用対数。範囲に 0 以下が入れば ValueError
        (log 軸に 0 を渡して -inf を「端」として描く図は嘘になる)。

    Returns
    -------
    dict
        ``{"rect", "xlim", "ylim", "invert_y", "xscale", "yscale"}``。

    Raises
    ------
    ValueError
        矩形が不正、範囲が非有限か幅ゼロ、w か h が 2 未満、
        未知の scale、log 軸で範囲に 0 以下。
    """
    x, y, w, h = _rect(rect)
    if w < 2 or h < 2:
        raise ValueError(f"axes rect must be at least 2x2 px (got: {w}x{h})")
    _finite("xlim/ylim", xlim, ylim)
    x0, x1 = float(xlim[0]), float(xlim[1])
    y0, y1 = float(ylim[0]), float(ylim[1])
    if x0 == x1 or y0 == y1:
        raise ValueError(f"xlim/ylim must span a non-zero range (got: {xlim}, {ylim})")
    for nm, sc, lim in (("xscale", xscale, (x0, x1)), ("yscale", yscale, (y0, y1))):
        if sc not in ("linear", "log"):
            raise ValueError(f"{nm} must be 'linear'|'log' (got: {sc!r})")
        if sc == "log" and min(lim) <= 0.0:
            raise ValueError(f"a log {nm[0]} axis needs a strictly positive range (got: {lim})")
    return {"rect": (x, y, w, h), "xlim": (x0, x1), "ylim": (y0, y1),
            "invert_y": bool(invert_y), "xscale": xscale, "yscale": yscale}


def _axis_fraction(v, lim, scale):
    """データ値 → [0,1] の位置。``lim`` は反転(lo > hi)していてもよい。"""
    lo, hi = float(lim[0]), float(lim[1])
    v = np.asarray(v, dtype=np.float64)
    if scale == "log":
        if np.any(v <= 0.0):
            raise ValueError("a log axis cannot place values <= 0")
        return (np.log10(v) - math.log10(lo)) / (math.log10(hi) - math.log10(lo))
    return (v - lo) / (hi - lo)


def data_to_pixel(axes, x, y):
    """:func:`axes_transform` の対応でデータ点を画素 (x,y) に写す。

    **クリップしない** ―― ``np.clip(v, lo, hi)`` は ``lo > hi``(反転軸)の
    とき黙って ``hi`` を返し、全点が端に貼り付いた「もっともらしい嘘の図」に
    なる(この repo の生成器で実際に一度騙されている)。範囲外を弾くのは
    :func:`plot_series` の ``clip=True`` の仕事で、そこでは**例外**にする。

    Returns
    -------
    (ndarray, ndarray)
        ``px``, ``py``(float、丸めない ―― 丸めは描画側の仕事)。

    Raises
    ------
    ValueError
        log 軸に 0 以下の値を渡したとき(-inf を「端」として描く図は嘘になる)。
        ``x`` と ``y`` の長さが違うとき(下記)。

    Notes
    -----
    **長さの不一致を拒否するのは 2026-09-02 に足した**。連鎖ファザーがこの op を
    実行できるようになった直後、長さの違う 2 本の signal を渡す経路で採掘器が
    ``np.stack`` の生の ValueError で落ちて発覚した。それまでは ``x`` 7 点・
    ``y`` 3 点でも**例外を出さず、長さの違う 2 本をそのまま返していた**。

    危ないのは落ちることではなく、落ちないこと ―― 返った 2 本を ``zip`` すると
    **3 点だけが、x の先頭 3 つの位置に**描かれる。点が消えたことも、x が
    ずれたことも図からは分からない。兄弟の :func:`plot_series` は同じ状況を
    ``"x and y must have the same length"`` で拒否していたので、**同じ族の中で
    規律が割れていた**(片方だけ直しても再発する型なので、文言も揃えてある)。
    """
    rx, ry, rw, rh = axes["rect"]
    n_x = np.size(np.asarray(x))
    n_y = np.size(np.asarray(y))
    if n_x != n_y:
        raise ValueError(
            f"x and y must have the same length (got: {n_x} and {n_y}); "
            "returning two arrays of different lengths would let the caller zip them "
            "and silently plot the shorter one against the wrong coordinates"
        )
    fx = _axis_fraction(x, axes["xlim"], axes.get("xscale", "linear"))
    fy = _axis_fraction(y, axes["ylim"], axes.get("yscale", "linear"))
    px = rx + fx * (rw - 1)
    py = ry + (rh - 1) - fy * (rh - 1) if axes["invert_y"] else ry + fy * (rh - 1)
    return px, py


def nice_ticks(lo, hi, n=5, scale="linear"):
    """[lo, hi] を覆う「切りのよい」目盛り値(1/2/5 × 10^k、**閉形式**)。

    端は**含める**(``lo`` や ``hi`` がちょうど目盛りに乗るなら必ず出る)。
    浮動小数の丸めで端が 1 個落ちる off-by-one を避けるため、判定には
    ``step*1e-9`` の許容を使う。

    ``scale='log'`` では 1/2/5 × 10^k の**十進の刻み**を返す(等間隔の刻みを
    log 軸に置くと、目盛りが右へ行くほど潰れて読めなくなる)。

    Raises
    ------
    ValueError
        lo == hi、非有限、n < 1、log で lo か hi が 0 以下。
    """
    _finite("lo/hi", lo, hi)
    lo, hi = float(lo), float(hi)
    if lo == hi:
        raise ValueError(f"lo == hi == {lo} — no tick spacing exists for a zero range")
    if lo > hi:
        lo, hi = hi, lo
    n = int(n)
    if n < 1:
        raise ValueError(f"n must be >= 1 (got: {n})")
    if scale not in ("linear", "log"):
        raise ValueError(f"scale must be 'linear'|'log' (got: {scale!r})")
    if scale == "log":
        if lo <= 0.0:
            raise ValueError(f"log ticks need a strictly positive range (got: {(lo, hi)})")
        out = []
        for k in range(int(math.floor(math.log10(lo))), int(math.floor(math.log10(hi))) + 1):
            for m in (1.0, 2.0, 5.0):
                v = m * 10.0 ** k
                if lo * (1 - 1e-9) <= v <= hi * (1 + 1e-9):
                    out.append(v)
        return np.asarray(out, dtype=np.float64)
    raw = (hi - lo) / n
    mag = 10.0 ** math.floor(math.log10(raw))
    norm = raw / mag
    step = mag * (1.0 if norm <= 1.0 else (2.0 if norm <= 2.0 else (5.0 if norm <= 5.0 else 10.0)))
    eps = step * 1e-9
    first = math.ceil(lo / step - 1e-9)
    k = int(math.floor(hi / step + 1e-9) - first) + 1
    if k < 1:
        return np.array([], dtype=np.float64)
    vals = (first + np.arange(k)) * step
    return vals[(vals >= lo - eps) & (vals <= hi + eps)]


def _auto_ticks(axes, which):
    """軸の scale に合った既定の目盛り(``ticks``/``grid_lines`` が使う)。"""
    lim = axes["xlim"] if which == "x" else axes["ylim"]
    scale = axes.get("xscale" if which == "x" else "yscale", "linear")
    return nice_ticks(lim[0], lim[1], scale=scale)


def axes_frame(img, axes, color="neutral", width=1, box=True, scheme="okabe_ito",
               style=None):
    """軸の枠(``box=True`` で四辺、False で左と下の 2 辺だけ)。

    ``style`` は :func:`imagedraw.draw_polyline` / :func:`imagedraw.draw_line`
    へ素通し。

    Raises
    ------
    ValueError
        枠が画像からはみ出す。
    """
    a = _prep(img)
    x, y, w, h = axes["rect"]
    _check_inside(a, (x, y, w, h), name="axes rect", what="axes frame")
    col = _channel_color(a, color, scheme)
    kw = _style(style, width)
    if box:
        pts = [(x, y), (x + w - 1, y), (x + w - 1, y + h - 1), (x, y + h - 1)]
        return imagedraw.draw_polyline(a, pts, color=col, closed=True, **kw)
    a = imagedraw.draw_line(a, (x, y), (x, y + h - 1), color=col, **kw)
    return imagedraw.draw_line(a, (x, y + h - 1), (x + w - 1, y + h - 1), color=col, **kw)


def grid_lines(img, axes, xticks=None, yticks=None, color="neutral", width=1,
               alpha=0.35, scheme="okabe_ito", style=None):
    """格子。目盛り値を渡さなければ :func:`nice_ticks` が決める。

    ``alpha`` は格子を薄く敷くための重み(データ線より前に出ないように)。

    Raises
    ------
    ValueError
        alpha が [0,1] の外。
    """
    a = _prep(img)
    if not (0.0 <= float(alpha) <= 1.0):
        raise ValueError(f"alpha must be within [0,1] (got: {alpha})")
    x, y, w, h = axes["rect"]
    _check_inside(a, (x, y, w, h), name="axes rect", what="grid")
    xt = _auto_ticks(axes, "x") if xticks is None else np.asarray(xticks, dtype=np.float64)
    yt = _auto_ticks(axes, "y") if yticks is None else np.asarray(yticks, dtype=np.float64)
    col = _channel_color(a, color, scheme)
    kw = _style(style, width)
    base = a
    over = a.copy()
    for v in np.atleast_1d(xt):
        px, _ = data_to_pixel(axes, v, axes["ylim"][0])
        over = imagedraw.draw_line(over, (float(px), y), (float(px), y + h - 1), color=col, **kw)
    for v in np.atleast_1d(yt):
        _, py = data_to_pixel(axes, axes["xlim"][0], v)
        over = imagedraw.draw_line(over, (x, float(py)), (x + w - 1, float(py)), color=col, **kw)
    # **線が乗った画素だけ**を混ぜる。全面に ``base*(1-a) + over*a`` を掛けると、
    # 線の無いところも ``base*0.65 + base*0.35`` を通って 1 ulp 動き、格子を
    # 重ねるたびに絵がじりじり変わる(重ねても等しいことを test が確かめている)。
    touched = np.any(over != base, axis=-1) if base.ndim == 3 else (over != base)
    if not touched.any():
        return base.copy()
    sel = touched[..., None] if base.ndim == 3 else touched
    return np.where(sel, base * (1.0 - alpha) + over * alpha, base)


def ticks(img, axes, xticks=None, yticks=None, color="neutral", width=1,
          tick_len=5, label=True, label_fmt="{:g}", font_size=11, font_path=None,
          scheme="okabe_ito", text_color=None, style=None):
    """目盛りとその数値。**位置は閉形式**(:func:`data_to_pixel` そのもの)。

    目盛りは枠の**外側**へ ``tick_len`` px 出す。ラベルは目盛りの外側に置くので、
    軸の周りに余白が無ければ :func:`text_box` の境界検査が例外にする
    (= 図の外に文字が消える事故が起きない)。

    Raises
    ------
    ValueError
        tick_len が負、ラベルが画像に収まらない。
    """
    a = _prep(img)
    if tick_len < 0:
        raise ValueError(f"tick_len must be >= 0 (got: {tick_len})")
    x, y, w, h = axes["rect"]
    xt = _auto_ticks(axes, "x") if xticks is None else np.asarray(xticks, dtype=np.float64)
    yt = _auto_ticks(axes, "y") if yticks is None else np.asarray(yticks, dtype=np.float64)
    col = _channel_color(a, color, scheme)
    kw = _style(style, width)
    for v in np.atleast_1d(xt):
        px, _ = data_to_pixel(axes, float(v), axes["ylim"][0])
        a = imagedraw.draw_line(a, (float(px), y + h - 1), (float(px), y + h - 1 + tick_len),
                                color=col, **kw)
        if label:
            a = text_box(a, label_fmt.format(float(v)), (float(px), y + h + tick_len + 2),
                         anchor="ct", pad=1, box_alpha=0.0, font_size=font_size,
                         font_path=font_path, text_color=text_color, scheme=scheme)
    for v in np.atleast_1d(yt):
        _, py = data_to_pixel(axes, axes["xlim"][0], float(v))
        a = imagedraw.draw_line(a, (x - tick_len, float(py)), (x, float(py)), color=col, **kw)
        if label:
            a = text_box(a, label_fmt.format(float(v)), (x - tick_len - 3, float(py)),
                         anchor="rm", pad=1, box_alpha=0.0, font_size=font_size,
                         font_path=font_path, text_color=text_color, scheme=scheme)
    return a


def plot_series(img, axes, x, y, kind="line", color="reference", width=2,
                marker_size=3, baseline=None, bar_width=0.7, clip=True,
                scheme="okabe_ito", style=None):
    """折れ線・散布・棒を描く。**データ座標**で受ける(画素は axes が決める)。

    Parameters
    ----------
    axes : dict
        :func:`axes_transform` の返り。
    x, y : 1-D
        同じ長さの系列。**空は ValueError**(空のグラフは「データが無い」のか
        「描き忘れ」なのか区別がつかない)。
    kind : {'line','scatter','bar'}
    baseline : float or None
        ``kind='bar'`` の基準値。None なら ``ylim`` の下端。
    bar_width : float
        棒の幅(隣り合う x 間隔に対する比 ∈ (0,1])。
    clip : bool
        True なら描画域の外に出る点を**例外**にする(黙って端に張り付く
        :mod:`imagedraw` のクランプは、嘘の折れ線を描いてしまう)。

    Raises
    ------
    ValueError
        長さ不一致 / 空 / 非有限 / 未知の kind / clip=True で範囲外。
    """
    a = _prep(img)
    xa = np.asarray(x, dtype=np.float64).ravel()
    ya = np.asarray(y, dtype=np.float64).ravel()
    if xa.size == 0 or ya.size == 0:
        raise ValueError("x/y is empty — an empty series draws nothing and hides the fact")
    if xa.size != ya.size:
        raise ValueError(f"x and y must have the same length (got: {xa.size} and {ya.size})")
    _finite("x/y", xa, ya)
    if kind not in ("line", "scatter", "bar"):
        raise ValueError(f"kind must be 'line'|'scatter'|'bar' (got: {kind!r})")
    if kind == "line" and xa.size < 2:
        raise ValueError("kind='line' needs at least 2 points (use kind='scatter' for one)")
    if not (0.0 < float(bar_width) <= 1.0):
        raise ValueError(f"bar_width must be within (0,1] (got: {bar_width})")
    rx, ry, rw, rh = axes["rect"]
    _check_inside(a, (rx, ry, rw, rh), name="axes rect", what="plot area")
    if clip:
        xlo, xhi = sorted(axes["xlim"])
        ylo, yhi = sorted(axes["ylim"])
        bad = int(np.count_nonzero((xa < xlo) | (xa > xhi) | (ya < ylo) | (ya > yhi)))
        if bad:
            raise ValueError(
                f"{bad} of {xa.size} points fall outside xlim={axes['xlim']} / "
                f"ylim={axes['ylim']}; they would be clamped onto the frame and read as "
                "real data — widen the limits or pass clip=False on purpose")
    px, py = data_to_pixel(axes, xa, ya)
    col = _channel_color(a, color, scheme)
    if kind == "line":
        return imagedraw.draw_polyline(a, np.stack([px, py], axis=1), color=col,
                                       **_style(style, width))
    if kind == "scatter":
        return imagedraw.draw_markers(a, np.stack([px, py], axis=1), color=col,
                                      size=marker_size, shape="dot", width=width)
    base = float(axes["ylim"][0]) if baseline is None else float(baseline)
    _, pb = data_to_pixel(axes, axes["xlim"][0], base)
    step = float(np.min(np.diff(np.sort(px)))) if xa.size > 1 else float(rw)
    bw = max(1, int(round(step * float(bar_width))))
    H, W = a.shape[:2]
    for cx, cy in zip(px, py):
        x0 = int(round(cx - bw / 2.0))
        y0, y1 = sorted((int(round(cy)), int(round(float(pb)))))
        x0 = max(rx, min(x0, rx + rw - 1))
        x1 = min(rx + rw, x0 + bw)
        y0 = max(ry, min(y0, ry + rh - 1))
        y1 = max(y0 + 1, min(y1 + 1, ry + rh))
        w = np.zeros((H, W), dtype=np.float64)
        w[y0:y1, x0:x1] = 1.0
        a = _blend(a, w, col, 1.0)
    return a


# ------------------------------------------------------------------ #
# 重ね(α 合成)
# ------------------------------------------------------------------ #

def overlay_mask(img, mask, color="wrong", alpha=0.45, outline=0,
                 outline_color=None, scheme="okabe_ito", style=None):
    """2 値マスクを α で重ねる。**厳密に ``a*f + (1-a)*b``**。

    Parameters
    ----------
    mask : (H,W)
        画像と同じ大きさの真偽(または [0,1] の重み)。
        **形が違えば例外** ―― (row,col) と (x,y) の取り違えはここで死ぬ。
    alpha : float
        マスク側の重み。
    outline : int
        0 より大きければマスクの輪郭を太さ ``outline`` で描く。

    Raises
    ------
    ValueError
        形の不一致 / alpha が [0,1] の外 / mask に非有限。
    """
    a = _prep(img)
    m = np.asarray(mask)
    if m.shape != a.shape[:2]:
        raise ValueError(
            f"mask shape {m.shape} does not match the image {a.shape[:2]} — if you passed "
            "an (x,y)-shaped array, transpose it: masks are indexed [row, col]")
    if m.dtype == bool:
        wgt = m.astype(np.float64)
    else:
        wgt = np.asarray(m, dtype=np.float64)
        if not np.all(np.isfinite(wgt)):
            raise ValueError("mask holds non-finite values")
        if wgt.min() < 0.0 or wgt.max() > 1.0:
            raise ValueError(f"mask weights must be within [0,1] (got: [{wgt.min()}, {wgt.max()}])")
    if not (0.0 <= float(alpha) <= 1.0):
        raise ValueError(f"alpha must be within [0,1] (got: {alpha})")
    col = _channel_color(a, color, scheme)
    out = _blend(a, wgt, col, alpha)
    if outline > 0:
        from scipy import ndimage
        b = wgt > 0.5
        edge = b ^ ndimage.binary_erosion(b)
        oc = _channel_color(a, color if outline_color is None else outline_color, scheme)
        out = _blend(out, edge.astype(np.float64), oc, 1.0)
        if outline > 1:
            out = _blend(out, ndimage.binary_dilation(edge, iterations=int(outline) - 1
                                                      ).astype(np.float64), oc, 1.0)
    return out


def overlay_labels(img, labels, alpha=0.5, colors=None, scheme="okabe_ito",
                   background=0):
    """色ラベル図を α で重ねる。**同じラベル番号には常に同じ色**。

    Parameters
    ----------
    labels : (H,W) int
        ラベル番号の地図。``background``(既定 0)は透明。
    colors : (k,3) or None
        番号 → 色。None なら Okabe–Ito 8 色を番号順に周回する
        (乱数を使わないので、同じラベル図なら常に同じ絵になる)。

    Raises
    ------
    ValueError
        形の不一致 / 負のラベル / alpha が [0,1] の外 / colors の形。
    """
    a = _prep(img)
    lab = np.asarray(labels)
    if lab.shape != a.shape[:2]:
        raise ValueError(f"labels shape {lab.shape} does not match the image {a.shape[:2]}")
    if not np.issubdtype(lab.dtype, np.integer):
        if not np.all(np.isfinite(lab)) or not np.all(lab == np.round(lab)):
            raise ValueError("labels must be integers (a label map is a set of ids, not a picture)")
        lab = lab.astype(np.int64)
    if lab.min() < 0:
        raise ValueError(f"labels must be >= 0 (got min {lab.min()})")
    if not (0.0 <= float(alpha) <= 1.0):
        raise ValueError(f"alpha must be within [0,1] (got: {alpha})")
    if colors is None:
        cyc = np.asarray([palette._OKABE_ITO[k] for k in
                          ("blue", "orange", "green", "purple", "sky", "vermillion",
                           "yellow", "black")], dtype=np.float64)
    else:
        cyc = np.asarray(colors, dtype=np.float64)
        if cyc.ndim != 2 or cyc.shape[1] < 3 or cyc.shape[0] < 1:
            raise ValueError(f"colors must be (k>=1, 3) (got: {cyc.shape})")
        if not np.all(np.isfinite(cyc)) or cyc.min() < 0.0 or cyc.max() > 1.0:
            raise ValueError("colors must be finite and within [0,1]")
    out = a
    for v in np.unique(lab):
        if int(v) == int(background):
            continue
        col = cyc[(int(v) - 1) % cyc.shape[0]]
        out = _blend(out, (lab == v).astype(np.float64), _channel_color(a, col, scheme), alpha)
    return out


# ------------------------------------------------------------------ #
# 組み立て(拡大の差し込み / 並べて比較)
# ------------------------------------------------------------------ #

def zoom_inset(img, src_rect, dst_xy, factor=3, color="emphasis", width=2,
               connect=True, scheme="okabe_ito", style=None):
    """拡大の差し込み ―― 元図に**枠**と**引き出し線**を付ける。

    拡大は ``np.repeat`` の**最近傍**(整数倍)。補間しないのは、拡大図が
    「元の画素そのもの」であることを保証するため(滑らかにすると、無かった
    構造が生まれたように見える)。

    Parameters
    ----------
    src_rect : (x, y, w, h)
        拡大元。
    dst_xy : (x, y)
        差し込み先の**左上**。
    factor : int
        整数の拡大率(>= 1)。
    connect : bool
        True なら元枠と差し込み枠の対応する角を 2 本の線で結ぶ。

    Raises
    ------
    ValueError
        factor が 1 未満か非整数、元枠/差し込みが画像からはみ出す。
    """
    a = _prep(img)
    f = int(factor)
    if f != factor or f < 1:
        raise ValueError(f"factor must be an integer >= 1 (got: {factor!r})")
    sx, sy, sw, sh = _rect(src_rect, "src_rect")
    _check_inside(a, (sx, sy, sw, sh), name="src_rect", what="zoom source")
    _finite("dst_xy", dst_xy)
    dx, dy = int(round(dst_xy[0])), int(round(dst_xy[1]))
    dw, dh = sw * f, sh * f
    _check_inside(a, (dx, dy, dw, dh), name="inset", what="zoom inset")

    crop = a[sy:sy + sh, sx:sx + sw]
    big = np.repeat(np.repeat(crop, f, axis=0), f, axis=1)
    a[dy:dy + dh, dx:dx + dw] = big
    col = _channel_color(a, color, scheme)
    kw = _style(style, width)
    for (x, y, w, h) in ((sx, sy, sw, sh), (dx, dy, dw, dh)):
        pts = [(x, y), (x + w - 1, y), (x + w - 1, y + h - 1), (x, y + h - 1)]
        a = imagedraw.draw_polyline(a, pts, color=col, closed=True, **kw)
    if connect:
        # 対応する角を結ぶ(差し込みが右にあるなら左上-左上 / 左下-左下)。
        if dx >= sx:
            pairs = (((sx + sw - 1, sy), (dx, dy)), ((sx + sw - 1, sy + sh - 1), (dx, dy + dh - 1)))
        else:
            pairs = (((sx, sy), (dx + dw - 1, dy)), ((sx, sy + sh - 1), (dx + dw - 1, dy + dh - 1)))
        for p, q in pairs:
            a = imagedraw.draw_line(a, p, q, color=col, **_style(style, max(1, width - 1)))
    return a


def compare_frame(left, right, layout="h", labels=None, divider=3, gap=0,
                  divider_color="neutral", background=0.0, label_anchor="lt",
                  label_margin=8, scheme="okabe_ito", **text_kw):
    """2 枚を並べ、境界に**仕切り**と**ラベル**を置く。

    Parameters
    ----------
    left, right : ndarray
        比べる 2 枚。大きさが違ってもよい(足りない側は ``background`` で埋める)。
        チャンネル数は揃っていること。
    layout : {'h','v'}
        ``'h'`` = 左右、``'v'`` = 上下。
    labels : (str, str) or None
        それぞれの見出し。
    divider : int
        仕切りの太さ [px] (0 で無し)。
    gap : int
        仕切りの両側に空ける余白[px]。

    Returns
    -------
    ndarray
        新しい合成画像。

    Raises
    ------
    ValueError
        チャンネル数の不一致 / 未知の layout / 負の divider・gap /
        labels が 2 要素でない。
    """
    a = _prep(left)
    b = _prep(right)
    if a.ndim != b.ndim or (a.ndim == 3 and a.shape[2] != b.shape[2]):
        raise ValueError(f"left/right channel layout differs ({a.shape} vs {b.shape})")
    if layout not in ("h", "v"):
        raise ValueError(f"layout must be 'h'|'v' (got: {layout!r})")
    if divider < 0 or gap < 0:
        raise ValueError(f"divider/gap must be >= 0 (got: {divider}, {gap})")
    if labels is not None and len(labels) != 2:
        raise ValueError(f"labels must hold exactly 2 strings (got: {len(labels)})")
    bgv = float(background)
    if not math.isfinite(bgv) or not (0.0 <= bgv <= 1.0):
        raise ValueError(f"background must be a finite value within [0,1] (got: {background})")

    sep = int(divider) + 2 * int(gap)
    if layout == "h":
        H = max(a.shape[0], b.shape[0])
        W = a.shape[1] + sep + b.shape[1]
        shape = (H, W) if a.ndim == 2 else (H, W, a.shape[2])
        out = np.full(shape, bgv, dtype=np.float64)
        if a.ndim == 3 and a.shape[2] == 4:
            out[..., 3] = 1.0                        # RGBA: keep the gutter opaque
        out[:a.shape[0], :a.shape[1]] = a
        bx = a.shape[1] + sep
        out[:b.shape[0], bx:bx + b.shape[1]] = b
        if divider > 0:
            out[:, a.shape[1] + gap:a.shape[1] + gap + divider] = _channel_color(
                out, divider_color, scheme)
        pos = ((label_margin, label_margin), (bx + label_margin, label_margin))
    else:
        H = a.shape[0] + sep + b.shape[0]
        W = max(a.shape[1], b.shape[1])
        shape = (H, W) if a.ndim == 2 else (H, W, a.shape[2])
        out = np.full(shape, bgv, dtype=np.float64)
        if a.ndim == 3 and a.shape[2] == 4:
            out[..., 3] = 1.0                        # RGBA: keep the gutter opaque (same as layout='h')
        out[:a.shape[0], :a.shape[1]] = a
        by = a.shape[0] + sep
        out[by:by + b.shape[0], :b.shape[1]] = b
        if divider > 0:
            out[a.shape[0] + gap:a.shape[0] + gap + divider, :] = _channel_color(
                out, divider_color, scheme)
        pos = ((label_margin, label_margin), (label_margin, by + label_margin))
    if labels is not None:
        for text, xy in zip(labels, pos):
            out = text_box(out, str(text), xy, anchor=label_anchor, scheme=scheme, **text_kw)
    return out


def panel_grid(panels, labels=None, ncols=3, pad=10, label_h=32, background=0.05,
               title=None, title_h=0, font_size=15, min_font_size=9, font_path=None,
               text_color=None, border=0, border_color="neutral", scheme="okabe_ito",
               style=None):
    """パネルを格子に並べ、各枠の下にラベルを敷く(montage / contact sheet)。

    生成器 6 本がそれぞれ別実装を持っていた、**この repo で最も重複していた図の
    部品**。ここでの流儀:

    * **拡大しない** ―― 小さいパネルは中央に置いて余白で埋める。引き伸ばすと
      「無い解像度がある」ように見える。
    * **ラベルは測ってから描く** ―― 入らなければ縮め、駄目なら例外
      (:func:`text_box` の境界検査に載る)。
    * セルの大きさは全パネルの最大寸で、**格子は常に矩形**。

    Parameters
    ----------
    panels : sequence of ndarray
        並べる画像(``(H,W)`` / ``(H,W,C)``、大きさはばらばらでよい)。
        チャンネルの並びは揃っていること。
    labels : sequence of str or None
        各パネルの見出し。``label_h`` が 0 なら描かない。
    ncols : int
        列数。行数は ``ceil(n/ncols)``。
    title : str or None
        全体の表題(``title_h`` が 0 なら ``font_size+14`` を自動で確保)。

    Returns
    -------
    ndarray
        新しい合成画像(float [0,1])。大きさは
        ``W = 2*pad + ncols*cw + (ncols-1)*pad``、
        ``H = title_h + 2*pad + nrows*(ch+label_h) + (nrows-1)*pad``。

    Raises
    ------
    ValueError
        panels が空 / チャンネル不一致 / ncols < 1 / 負の余白 /
        labels の数が合わない。
    """
    ps = [_prep(p) for p in panels]
    if not ps:
        raise ValueError("panels is empty — an empty contact sheet says nothing")
    ncols = int(ncols)
    if ncols < 1:
        raise ValueError(f"ncols must be >= 1 (got: {ncols})")
    if pad < 0 or label_h < 0 or title_h < 0:
        raise ValueError(f"pad/label_h/title_h must be >= 0 (got: {pad}, {label_h}, {title_h})")
    nd = ps[0].ndim
    nc = ps[0].shape[2] if nd == 3 else 0
    for i, p in enumerate(ps):
        if p.ndim != nd or (nd == 3 and p.shape[2] != nc):
            raise ValueError(f"panels[{i}] has shape {p.shape}, incompatible with {ps[0].shape}")
    if labels is not None:
        labels = [str(s) for s in labels]
        if len(labels) != len(ps):
            raise ValueError(f"labels has {len(labels)} entries for {len(ps)} panels")
    bgv = float(background)
    if not math.isfinite(bgv) or not (0.0 <= bgv <= 1.0):
        raise ValueError(f"background must be a finite value within [0,1] (got: {background})")
    cw = max(p.shape[1] for p in ps)
    ch = max(p.shape[0] for p in ps)
    nrows = (len(ps) + ncols - 1) // ncols
    W = 2 * pad + ncols * cw + (ncols - 1) * pad

    # ラベル帯・表題帯の高さは**測ってから**決める。決め打ちの高さに測っていない
    # 文字を流し込むのが、この repo で文字が隣とぶつかっていた原因。
    if labels is not None and label_h > 0:
        need = max(measure_text(s, font_size=font_size, font_path=font_path,
                                min_font_size=min_font_size, max_width=cw - 4,
                                wrap=False)["height"]
                   for s in labels) + 4
        if need > label_h:
            raise ValueError(
                f"the labels need {need}px but label_h is {label_h} — they would spill into "
                "the panel above or below; raise label_h or lower font_size")
    if title is not None:
        tm = measure_text(title, font_size=int(font_size) + 3, font_path=font_path,
                          min_font_size=min_font_size, max_width=W - 2 * pad)
        need_t = tm["height"] + 2 * 2 + 6
        if title_h <= 0:
            title_h = need_t
        elif title_h < need_t:
            raise ValueError(
                f"the title needs {need_t}px but title_h is {title_h} — raise title_h")
    cell_h = ch + int(label_h)
    H = int(title_h) + 2 * pad + nrows * cell_h + (nrows - 1) * pad
    out = np.full((H, W) if nd == 2 else (H, W, nc), bgv, dtype=np.float64)
    if nd == 3 and nc == 4:
        out[..., 3] = 1.0        # RGBA: background fills colour only — a transparent
                                 # gutter would let whatever is composited underneath
                                 # show through the padding (color_bar does the same).

    for i, p in enumerate(ps):
        r, c = divmod(i, ncols)
        x0 = pad + c * (cw + pad)
        y0 = int(title_h) + pad + r * (cell_h + pad)
        ox = x0 + (cw - p.shape[1]) // 2                      # 拡大せず中央に置く
        oy = y0 + (ch - p.shape[0]) // 2
        out[oy:oy + p.shape[0], ox:ox + p.shape[1]] = p
        if border > 0:
            pts = [(x0, y0), (x0 + cw - 1, y0), (x0 + cw - 1, y0 + ch - 1), (x0, y0 + ch - 1)]
            out = imagedraw.draw_polyline(out, pts, color=_channel_color(out, border_color, scheme),
                                          closed=True, **_style(style, int(border)))
        if labels is not None and label_h > 0:
            out = text_box(out, labels[i], (x0 + cw // 2, y0 + ch + int(label_h) // 2),
                           anchor="cm", pad=2, box_alpha=0.0, font_size=font_size,
                           min_font_size=min_font_size, font_path=font_path,
                           text_color=text_color, max_width=cw, scheme=scheme, wrap=False)
    if title is not None:
        out = text_box(out, title, (W // 2, int(title_h) // 2), anchor="cm", pad=2,
                       box_alpha=0.0, font_size=font_size + 3, min_font_size=min_font_size,
                       font_path=font_path, text_color=text_color, max_width=W - 2 * pad,
                       scheme=scheme)
    return out


# ------------------------------------------------------------------ #
# 図形(下敷き・囲み・角度)
# ------------------------------------------------------------------ #

def _grid(shape):
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    return xx.astype(np.float64), yy.astype(np.float64)


def rounded_rect(img, rect, radius=8, color="neutral", width=2, fill=False,
                 alpha=1.0, scheme="okabe_ito"):
    """角丸の矩形(``fill=True`` で塗り)。下敷きや囲みに使う。

    Raises
    ------
    ValueError
        矩形が画像の外、radius が負か辺の半分を超える、alpha が [0,1] の外。
    """
    a = _prep(img)
    x, y, w, h = _rect(rect)
    _check_inside(a, (x, y, w, h), name="rect", what="rounded rectangle")
    r = float(radius)
    if r < 0:
        raise ValueError(f"radius must be >= 0 (got: {radius})")
    if r > min(w, h) / 2.0:
        raise ValueError(f"radius {r} exceeds half of the shorter side ({min(w, h) / 2.0})")
    if not (0.0 <= float(alpha) <= 1.0):
        raise ValueError(f"alpha must be within [0,1] (got: {alpha})")
    xx, yy = _grid(a.shape[:2])
    x1, y1 = x + w - 1.0, y + h - 1.0
    cx = np.clip(xx, x + r, x1 - r)
    cy = np.clip(yy, y + r, y1 - r)
    d = np.hypot(xx - cx, yy - cy)
    inside = (xx >= x) & (xx <= x1) & (yy >= y) & (yy <= y1) & (d <= r + 1e-9)
    m = inside if fill else (inside & (d >= r - max(1.0, float(width)) + 1e-9)) | (
        inside & _rect_ring(xx, yy, x, y, x1, y1, width, r))
    return _blend(a, m.astype(np.float64), _channel_color(a, color, scheme), alpha)


def _rect_ring(xx, yy, x0, y0, x1, y1, width, r):
    """角丸の直線部分の枠(角の弧は距離条件が拾う)。"""
    w = max(1.0, float(width))
    near_v = ((np.abs(xx - x0) < w) | (np.abs(xx - x1) < w)) & (yy >= y0 + r) & (yy <= y1 - r)
    near_h = ((np.abs(yy - y0) < w) | (np.abs(yy - y1) < w)) & (xx >= x0 + r) & (xx <= x1 - r)
    return near_v | near_h


def filled_polygon(img, points, color="neutral", alpha=1.0, scheme="okabe_ito"):
    """多角形の塗り(偶奇規則の交差判定 ―― :mod:`imagedraw` は輪郭のみ)。

    Parameters
    ----------
    points : (N,2)
        **(x,y)** の頂点列(自動的に閉じる)。3 点未満は ValueError。

    Raises
    ------
    ValueError
        点が 3 未満 / 非有限 / alpha が [0,1] の外。
    """
    a = _prep(img)
    p = np.asarray(points, dtype=np.float64).reshape(-1, 2)
    if p.shape[0] < 3:
        raise ValueError(f"a polygon needs at least 3 points (got: {p.shape[0]})")
    _finite("points", p)
    if not (0.0 <= float(alpha) <= 1.0):
        raise ValueError(f"alpha must be within [0,1] (got: {alpha})")
    xx, yy = _grid(a.shape[:2])
    inside = np.zeros(a.shape[:2], dtype=bool)
    n = p.shape[0]
    for i in range(n):
        x0, y0 = p[i]
        x1, y1 = p[(i + 1) % n]
        if y0 == y1:
            continue
        crosses = ((yy >= np.minimum(y0, y1)) & (yy < np.maximum(y0, y1)))
        xint = x0 + (yy - y0) * (x1 - x0) / (y1 - y0)
        inside ^= crosses & (xx < xint)
    return _blend(a, inside.astype(np.float64), _channel_color(a, color, scheme), alpha)


def arc(img, center, radius, start_deg, end_deg, color="neutral", width=2,
        alpha=1.0, scheme="okabe_ito"):
    """円弧。角度は**画面の x 軸から時計回り**(row が下向きだから)で度。

    Raises
    ------
    ValueError
        radius が非正、角度が非有限、start == end、alpha が [0,1] の外。
    """
    a = _prep(img)
    _finite("center/angles", center, start_deg, end_deg)
    r = float(radius)
    if r <= 0:
        raise ValueError(f"radius must be positive (got: {radius})")
    if float(start_deg) == float(end_deg):
        raise ValueError("start_deg == end_deg — a zero-length arc draws nothing")
    if not (0.0 <= float(alpha) <= 1.0):
        raise ValueError(f"alpha must be within [0,1] (got: {alpha})")
    xx, yy = _grid(a.shape[:2])
    cx, cy = float(center[0]), float(center[1])
    d = np.hypot(xx - cx, yy - cy)
    ang = np.degrees(np.arctan2(yy - cy, xx - cx)) % 360.0
    s = float(start_deg) % 360.0
    span = (float(end_deg) - float(start_deg)) % 360.0
    span = span if span > 0 else 360.0
    within = ((ang - s) % 360.0) <= span
    m = (np.abs(d - r) <= max(0.6, float(width) / 2.0)) & within
    return _blend(a, m.astype(np.float64), _channel_color(a, color, scheme), alpha)


def ellipse(img, center, radii, angle_deg=0.0, color="neutral", width=2,
            fill=False, alpha=1.0, scheme="okabe_ito"):
    """楕円(``angle_deg`` で回転、``fill=True`` で塗り)。

    Raises
    ------
    ValueError
        半径が非正、非有限、alpha が [0,1] の外。
    """
    a = _prep(img)
    _finite("center/radii/angle", center, radii, angle_deg)
    ra, rb = float(radii[0]), float(radii[1])
    if ra <= 0 or rb <= 0:
        raise ValueError(f"radii must be positive (got: {radii})")
    if not (0.0 <= float(alpha) <= 1.0):
        raise ValueError(f"alpha must be within [0,1] (got: {alpha})")
    xx, yy = _grid(a.shape[:2])
    cx, cy = float(center[0]), float(center[1])
    th = math.radians(float(angle_deg))
    u = (xx - cx) * math.cos(th) + (yy - cy) * math.sin(th)
    v = -(xx - cx) * math.sin(th) + (yy - cy) * math.cos(th)
    q = (u / ra) ** 2 + (v / rb) ** 2
    if fill:
        m = q <= 1.0
    else:
        t = max(1.0, float(width)) / (2.0 * min(ra, rb))
        m = np.abs(np.sqrt(q) - 1.0) <= t
    return _blend(a, m.astype(np.float64), _channel_color(a, color, scheme), alpha)


# ------------------------------------------------------------------ #
# 学術図(paper figure)の図注 —— 2026-09-03
#
# 「どこに何があるかを矢印や線で示す」のが学術図の作法。上の 25 op は
# **部品**(文字・矢印・凡例・軸)で、ここから下は**作法そのもの**を op に
# する: 引き出し線(衝突回避つき)/ 番号マーカー + 凡例 / 寸法線 / 角度 /
# 切りのよいスケールバー / 方位矢印 / 隅の拡大差し込み / マスクの輪郭 /
# 経路に沿う文字 / 色分け重ね + カラーバー / パネル文字 / 図の組版。
#
# 規律(上と同じ + 2 つ):
# * **幾何は layout op が閉形式で決め、draw op はそれを描くだけ** ――
#   ``annotate_*_layout`` は table(dict)を返し、tests はその数字を検算する。
#   描く op に ``layout=`` で渡せば、同じ配置を別の絵にも使い回せる。
# * **線はアンチエイリアス** ―― :mod:`imagedraw` の 1 画素線ではなく、線分
#   までの距離から被覆率を出して α で載せる(:func:`_aa_polyline`)。破線は
#   弧長で区切る。文字は従来どおり Pillow の AA マスク。
# ------------------------------------------------------------------ #

_CORNERS = ("lt", "rt", "lb", "rb")
_LETTERS = "abcdefghijklmnopqrstuvwxyz"


def _num(v, name, lo=None, hi=None, integer=False):
    """数値引数の検算。**bool と str は黙って数に変換しない**(例外)。"""
    if isinstance(v, (bool, np.bool_)) or isinstance(v, (str, bytes)):
        raise ValueError(f"{name} must be a number (got {type(v).__name__}: {v!r})")
    try:
        f = float(v)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number (got {v!r})") from exc
    if not math.isfinite(f):
        raise ValueError(f"{name} must be finite (got {v!r})")
    if integer and f != math.floor(f):
        raise ValueError(f"{name} must be an integer (got {v!r})")
    if lo is not None and f < lo:
        raise ValueError(f"{name} must be >= {lo} (got {v!r})")
    if hi is not None and f > hi:
        raise ValueError(f"{name} must be <= {hi} (got {v!r})")
    return int(f) if integer else f


def _flag(v, name):
    """真偽値引数の検算。``"false"`` のような文字列は真になってしまうので拒否。"""
    if not isinstance(v, (bool, np.bool_)):
        raise ValueError(f"{name} must be True or False (got {type(v).__name__}: {v!r})")
    return bool(v)


def _pt(p, name="point"):
    q = np.asarray(p, dtype=np.float64).ravel()
    if q.size != 2:
        raise ValueError(f"{name} must be (x, y) (got {q.size} values)")
    _finite(name, q)
    return float(q[0]), float(q[1])


def _pts(points, name="points", min_n=1):
    p = np.asarray(points, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] != 2:
        raise ValueError(f"{name} must be (N, 2) (x, y) pairs (got shape {p.shape})")
    if p.shape[0] < min_n:
        raise ValueError(f"{name} needs at least {min_n} point(s) (got {p.shape[0]})")
    _finite(name, p)
    return p


def _shape2(shape, name="shape"):
    s = tuple(int(v) for v in np.asarray(shape).ravel()[:2]) if np.ndim(shape) else None
    if s is None or len(s) != 2 or s[0] < 1 or s[1] < 1:
        raise ValueError(f"{name} must be (H, W) with positive sizes (got {shape!r})")
    return s


def _corner_xy(corner, W, H, margin):
    if corner not in _CORNERS:
        raise ValueError(f"corner must be one of {_CORNERS} (got: {corner!r})")
    x = margin if corner[0] == "l" else W - 1 - margin
    y = margin if corner[1] == "t" else H - 1 - margin
    return int(x), int(y)


def _segment_coverage(shape, p0, p1, width):
    """線分 p0→p1(太さ width)の画素被覆率 [0,1](距離ベースの AA)。"""
    H, W = shape
    x0, y0 = p0
    x1, y1 = p1
    r = width / 2.0 + 0.5
    xa, xb = int(math.floor(min(x0, x1) - r - 1)), int(math.ceil(max(x0, x1) + r + 1))
    ya, yb = int(math.floor(min(y0, y1) - r - 1)), int(math.ceil(max(y0, y1) + r + 1))
    xa, xb = max(0, xa), min(W - 1, xb)
    ya, yb = max(0, ya), min(H - 1, yb)
    out = np.zeros((H, W), dtype=np.float64)
    if xa > xb or ya > yb:
        return out
    yy, xx = np.mgrid[ya:yb + 1, xa:xb + 1]
    dx, dy = x1 - x0, y1 - y0
    l2 = dx * dx + dy * dy
    if l2 < 1e-18:
        t = np.zeros_like(xx, dtype=np.float64)
    else:
        t = np.clip(((xx - x0) * dx + (yy - y0) * dy) / l2, 0.0, 1.0)
    d = np.hypot(xx - (x0 + t * dx), yy - (y0 + t * dy))
    out[ya:yb + 1, xa:xb + 1] = np.clip(r - d, 0.0, 1.0)
    return out


def _dash_pieces(pts, closed, dash):
    """折れ線を弧長で ``(on, off)`` の破線片に切る(位相は頂点をまたいで連続)。"""
    p = [tuple(map(float, q)) for q in pts]
    if closed and len(p) > 1:
        p = p + [p[0]]
    if dash is None:
        return [(p[i], p[i + 1]) for i in range(len(p) - 1)]
    on, off = float(dash[0]), float(dash[1])
    if on <= 0 or off < 0:
        raise ValueError(f"dash must be (on > 0, off >= 0) pixel lengths (got: {dash!r})")
    period = on + off
    pieces = []
    s = 0.0
    for i in range(len(p) - 1):
        a, b = p[i], p[i + 1]
        seg = math.hypot(b[0] - a[0], b[1] - a[1])
        if seg < 1e-12:
            continue
        t = 0.0
        while t < seg:
            phase = (s + t) % period
            if phase < on:
                run = min(on - phase, seg - t)
                u0, u1 = t / seg, (t + run) / seg
                pieces.append(((a[0] + (b[0] - a[0]) * u0, a[1] + (b[1] - a[1]) * u0),
                               (a[0] + (b[0] - a[0]) * u1, a[1] + (b[1] - a[1]) * u1)))
                t += run
            else:
                t += period - phase
        s += seg
    return pieces


def _aa_polyline(a, pts, color, width=1.5, closed=False, dash=None, alpha=1.0,
                 scheme="okabe_ito"):
    """アンチエイリアスの折れ線(距離被覆率 → α 合成)。``dash=(on, off)`` で破線。"""
    w = _num(width, "width", lo=0.5)
    m = np.zeros(a.shape[:2], dtype=np.float64)
    for p, q in _dash_pieces(pts, closed, dash):
        m = np.maximum(m, _segment_coverage(a.shape[:2], p, q, w))
    return _blend(a, m, _channel_color(a, color, scheme), alpha)


def _aa_disk(a, center, radius, color, alpha=1.0, scheme="okabe_ito", ring=0.0):
    """アンチエイリアスの円板(``ring>0`` なら太さ ring の輪)。"""
    xx, yy = _grid(a.shape[:2])
    d = np.hypot(xx - center[0], yy - center[1])
    if ring > 0:
        m = np.clip(ring / 2.0 + 0.5 - np.abs(d - radius), 0.0, 1.0)
    else:
        m = np.clip(radius + 0.5 - d, 0.0, 1.0)
    return _blend(a, m, _channel_color(a, color, scheme), alpha)


def _aa_arc(a, center, radius, start_deg, end_deg, color, width=1.5, alpha=1.0,
            scheme="okabe_ito"):
    """アンチエイリアスの円弧(角度は画面 x 軸から時計回り、度)。"""
    xx, yy = _grid(a.shape[:2])
    d = np.hypot(xx - center[0], yy - center[1])
    ang = np.degrees(np.arctan2(yy - center[1], xx - center[0])) % 360.0
    s = float(start_deg) % 360.0
    span = (float(end_deg) - float(start_deg)) % 360.0
    span = span if span > 0 else 360.0
    within = ((ang - s) % 360.0) <= span
    m = np.clip(width / 2.0 + 0.5 - np.abs(d - radius), 0.0, 1.0) * within
    return _blend(a, m, _channel_color(a, color, scheme), alpha)


def _text_anchor_for_direction(nx, ny):
    """法線 (nx,ny) の側に置く文字のアンカー(文字が線に食い込まない向き)。"""
    if abs(ny) >= abs(nx):
        return "cb" if ny < 0 else "ct"
    return "lm" if nx > 0 else "rm"


# ---------------------------------------------------------------- 引き出し線

#: 引き出し線の候補配置(**固定順** = 決定的)。(sx, sy) は肘の向き。
_LEADER_SIDES = ((1, -1), (1, 1), (-1, -1), (-1, 1), (0, -1), (0, 1))


def annotate_leader_layout(shape, points, labels=None, font_size=12, pad=4, gap=22,
                           side="auto", font_path=None, min_font_size=9):
    """table(dict)を返す: 引き出し線の配置(肘・文字位置・板の矩形)を閉形式で決める。

    各点について候補側を固定順に試し、**板が画像に収まり・他の板と重ならず・
    他の点を覆わない**最初の候補を採る。どの候補も駄目なら肘を 1.6 倍、2.4 倍に
    伸ばして再試行し、それでも駄目なら **ValueError**(黙って重ねない)。

    Parameters
    ----------
    shape : (H, W)
        描く画像の大きさ。
    points : (N, 2)
        指す点 **(x, y)**。
    labels : sequence of str or None
        各点の文字。None なら 1 始まりの番号。
    gap : float
        肘の長さ[px]。斜め腕 = gap、水平腕 = 0.6*gap。
    side : {'auto','left','right'}
        ``'auto'`` は画像中心から**遠ざかる**側を先に試す(対象の上に文字を
        載せないため)。

    Returns
    -------
    dict
        ``{"n", "gap", "items": [{"point", "elbow", "text_xy", "anchor",
        "box", "side"}]}``。``box`` は板の ``(x, y, w, h)``。

    Raises
    ------
    ValueError
        点が空・非有限、labels の数が合わない、未知の side、配置できない点。
    """
    H, W = _shape2(shape)
    pts = _pts(points)
    n = pts.shape[0]
    if labels is None:
        labels = [str(i + 1) for i in range(n)]
    labels = [str(s) for s in labels]
    if len(labels) != n:
        raise ValueError(f"labels has {len(labels)} entries for {n} points")
    if side not in ("auto", "left", "right"):
        raise ValueError(f"side must be 'auto'|'left'|'right' (got: {side!r})")
    g0 = _num(gap, "gap", lo=1.0)
    pad = _num(pad, "pad", lo=0, integer=True)
    for x, y in pts:
        if not (0 <= x <= W - 1 and 0 <= y <= H - 1):
            raise ValueError(f"point ({x:g},{y:g}) lies outside the {W}x{H} image")

    items, taken = [], []
    for i, ((x, y), text) in enumerate(zip(pts, labels)):
        m = measure_text(text, font_size=font_size, font_path=font_path,
                         min_font_size=min_font_size)
        bw, bh = m["width"] + 2 * pad, m["height"] + 2 * pad
        if side == "auto":
            first = 1 if x >= (W - 1) / 2.0 else -1
        else:
            first = 1 if side == "right" else -1
        order = sorted(_LEADER_SIDES, key=lambda sxy: (0 if sxy[0] == first else
                                                        (2 if sxy[0] == 0 else 1)))
        placed = None
        for scale in (1.0, 1.6, 2.4):
            g = g0 * scale
            for sx, sy in order:
                if sx != 0:
                    elbow = (x + sx * g, y + sy * g)
                    txy = (elbow[0] + sx * 0.6 * g, elbow[1])
                    anchor = "lm" if sx > 0 else "rm"
                else:
                    elbow = (x, y + sy * g)
                    txy = (x, elbow[1] + sy * 3.0)
                    anchor = "cb" if sy < 0 else "ct"
                ox, oy = _anchor_origin(anchor, int(round(txy[0])), int(round(txy[1])), bw, bh)
                box = (ox, oy, bw, bh)
                if ox < 0 or oy < 0 or ox + bw > W or oy + bh > H:
                    continue
                if any(_overlaps(box, t) for t in taken):
                    continue
                covers = any(ox <= px <= ox + bw - 1 and oy <= py <= oy + bh - 1
                             for j, (px, py) in enumerate(pts) if j != i)
                if covers:
                    continue
                placed = {"point": (float(x), float(y)), "elbow": (float(elbow[0]), float(elbow[1])),
                          "text_xy": (float(txy[0]), float(txy[1])), "anchor": anchor,
                          "box": box, "side": (int(sx), int(sy)), "label": text}
                break
            if placed is not None:
                break
        if placed is None:
            raise ValueError(
                f"leader label {text!r} for point ({x:g},{y:g}) cannot be placed: every "
                f"candidate side at gap {g0:g}/{1.6 * g0:g}/{2.4 * g0:g} leaves the image, "
                "overlaps another label or covers another point — thin the points, "
                "shrink the font, or enlarge the image")
        taken.append(placed["box"])
        items.append(placed)
    return {"n": n, "gap": float(g0), "items": items}


def annotate_leader(img, points, labels=None, color="emphasis", width=1.5, cap_size=3.0,
                    font_size=12, pad=4, gap=22, side="auto", box_alpha=0.72,
                    text_color=None, scheme="okabe_ito", font_path=None,
                    min_font_size=9, layout=None):
    """画像(image2d)を返す: 肘つき引き出し線 + 文字(複数点の衝突回避つき)。

    配置は :func:`annotate_leader_layout` が決める(``layout=`` に渡せば再利用)。
    線はアンチエイリアス、対象側の端には点、文字は :func:`text_box`。

    Raises
    ------
    ValueError
        :func:`annotate_leader_layout` と同じ + 太さ・cap_size が非正。
    """
    a = _prep(img)
    w = _num(width, "width", lo=0.5)
    cap = _num(cap_size, "cap_size", lo=0.0)
    if layout is None:
        layout = annotate_leader_layout(a.shape[:2], points, labels, font_size=font_size,
                                        pad=pad, gap=gap, side=side, font_path=font_path,
                                        min_font_size=min_font_size)
    elif not (isinstance(layout, dict) and "items" in layout):
        raise ValueError("layout must be the dict returned by annotate_leader_layout")
    for it in layout["items"]:
        a = _aa_polyline(a, [it["point"], it["elbow"], it["text_xy"]], color, width=w,
                         scheme=scheme)
        if cap > 0:
            a = _aa_disk(a, it["point"], cap, color, scheme=scheme)
        a = text_box(a, it["label"], it["text_xy"], color=color, anchor=it["anchor"],
                     pad=pad, font_size=font_size, box_alpha=box_alpha,
                     text_color=text_color, font_path=font_path,
                     min_font_size=min_font_size, scheme=scheme)
    return a


# ---------------------------------------------------------------- 番号マーカー + 凡例

def _numbered_marker(a, xy, text, radius, color, text_color, font_size, font_path,
                     scheme, min_contrast):
    a = _aa_disk(a, xy, radius, color, scheme=scheme)
    plate = _rgb(color, scheme)
    if text_color is None:
        light, dark = _rgb(_INK_RGB, scheme), _rgb(_PLATE_RGB, scheme)
        ink = light if _contrast_ratio(light, plate) >= _contrast_ratio(dark, plate) else dark
    else:
        ink = _rgb(text_color, scheme)
    if _contrast_ratio(ink, plate) < float(min_contrast):
        raise ValueError(
            f"marker text colour has contrast {_contrast_ratio(ink, plate):.2f} against the "
            f"marker colour (minimum {min_contrast}) — the number would be invisible")
    # 文字の**インクの箱**(行送りではなく実際に塗られる範囲)が円に入るか。
    Image, ImageDraw, _ = _pil()
    font = _font(int(font_size), font_path)
    l, t, r, b = font.getbbox(text)
    iw, ih = float(r - l), float(b - t)
    if math.hypot(iw, ih) / 2.0 > radius + 0.5:
        raise ValueError(
            f"marker text {text!r} ({iw:g}x{ih:g}px of ink) does not fit in a radius "
            f"{radius:g} disk — enlarge radius or lower font_size")
    im = Image.new("L", (int(a.shape[1]), int(a.shape[0])), 0)
    ImageDraw.Draw(im).text((xy[0] - (l + r) / 2.0, xy[1] - (t + b) / 2.0), text,
                            fill=255, font=font)
    mask = np.asarray(im, dtype=np.float64) / 255.0
    return _blend(a, mask, _channel_color(a, ink, scheme), 1.0)


def annotate_markers(img, points, labels=None, start=1, radius=9.0, color="emphasis",
                     text_color=None, font_size=11, scheme="okabe_ito", font_path=None,
                     min_contrast=DEFAULT_MIN_CONTRAST):
    """画像(image2d)を返す: 番号(または短い文字)入りの丸いマーカーを各点に置く。

    :func:`annotate_legend` と同じ ``start`` / ``labels`` を渡せば、図中の番号と
    凡例の番号が必ず一致する。

    Parameters
    ----------
    points : (N, 2)
        **(x, y)**。画像の外の点は ValueError。
    labels : sequence of str or None
        None なら ``start`` から連番。
    radius : float
        円の半径[px]。文字が入らなければ ValueError。

    Raises
    ------
    ValueError
        点が空・非有限・画像外、labels の数不一致、文字が円に入らない、
        文字色と円色のコントラスト不足。
    """
    a = _prep(img)
    pts = _pts(points)
    r = _num(radius, "radius", lo=1.0)
    start = _num(start, "start", integer=True)
    H, W = a.shape[:2]
    if labels is None:
        labels = [str(start + i) for i in range(pts.shape[0])]
    labels = [str(s) for s in labels]
    if len(labels) != pts.shape[0]:
        raise ValueError(f"labels has {len(labels)} entries for {pts.shape[0]} points")
    for (x, y), text in zip(pts, labels):
        if not (r <= x <= W - 1 - r and r <= y <= H - 1 - r):
            raise ValueError(f"marker at ({x:g},{y:g}) with radius {r:g} does not fit in the "
                             f"{W}x{H} image")
        a = _numbered_marker(a, (x, y), text, r, color, text_color, font_size, font_path,
                             scheme, min_contrast)
    return a


def annotate_legend(img, labels, xy, anchor="lt", start=1, radius=7.0, color="emphasis",
                    text_color=None, font_size=12, pad=8, row_gap=4, box_color=None,
                    box_alpha=0.72, border=1, border_color="neutral", scheme="okabe_ito",
                    font_path=None, min_font_size=9, numbers=None):
    """画像(image2d)を返す: 番号つき丸マーカー × 説明の凡例(:func:`annotate_markers` の対)。

    箱の高さは閉形式 ``2*pad + n*row_h + (n-1)*row_gap``(``row_h = max(2r, 文字高)``)。

    Parameters
    ----------
    labels : sequence of str
        各行の説明。
    numbers : sequence of str or None
        各行のマーカー文字。None なら ``start`` から連番。

    Raises
    ------
    ValueError
        labels が空、箱が画像からはみ出す、負の余白。
    """
    a = _prep(img)
    rows = [str(s) for s in labels]
    if not rows:
        raise ValueError("labels is empty — a legend with no rows says nothing")
    r = _num(radius, "radius", lo=1.0)
    pad = _num(pad, "pad", lo=0, integer=True)
    row_gap = _num(row_gap, "row_gap", lo=0, integer=True)
    start = _num(start, "start", integer=True)
    if numbers is None:
        numbers = [str(start + i) for i in range(len(rows))]
    numbers = [str(s) for s in numbers]
    if len(numbers) != len(rows):
        raise ValueError(f"numbers has {len(numbers)} entries for {len(rows)} labels")
    ms = [measure_text(t, font_size=font_size, font_path=font_path,
                       min_font_size=min_font_size) for t in rows]
    d = int(math.ceil(2 * r))
    row_h = max(d, max(m["height"] for m in ms))
    bw = 2 * pad + d + 8 + max(m["width"] for m in ms)
    bh = 2 * pad + len(rows) * row_h + (len(rows) - 1) * row_gap
    _finite("xy", xy)
    x0, y0 = _anchor_origin(anchor, int(round(xy[0])), int(round(xy[1])), bw, bh)
    _check_inside(a, (x0, y0, bw, bh), name="legend", what="legend box")
    plate = _rgb(_PLATE_RGB if box_color is None else box_color, scheme)
    if box_alpha > 0.0:
        w = np.zeros(a.shape[:2], dtype=np.float64)
        w[y0:y0 + bh, x0:x0 + bw] = 1.0
        a = _blend(a, w, _channel_color(a, plate, scheme), box_alpha)
    if border > 0:
        a = _aa_polyline(a, [(x0, y0), (x0 + bw - 1, y0), (x0 + bw - 1, y0 + bh - 1),
                             (x0, y0 + bh - 1)], border_color, width=border, closed=True,
                         scheme=scheme)
    for i, (text, num, m) in enumerate(zip(rows, numbers, ms)):
        ry = y0 + pad + i * (row_h + row_gap)
        cy = ry + row_h / 2.0
        cx = x0 + pad + r
        a = _numbered_marker(a, (cx, cy), num, r, color, text_color, max(6, font_size - 1),
                             font_path, scheme, DEFAULT_MIN_CONTRAST)
        a = text_box(a, text, (x0 + pad + d + 8, int(round(cy))), anchor="lm", pad=0,
                     box_alpha=0.0, font_size=m["font_size"], font_path=font_path,
                     min_font_size=min_font_size, scheme=scheme)
    return a


# ---------------------------------------------------------------- 寸法線

def annotate_dimension_layout(p0, p1, offset=20.0, extension=6.0, text_gap=8.0):
    """table(dict)を返す: 寸法線の幾何(寸法線・補助線・文字位置)を閉形式で決める。

    ``n`` を p0→p1 の左法線(画面座標)として、寸法線は ``p + n*offset``、補助線は
    ``p`` から ``p + n*(offset+extension)``、文字は寸法線の中点から ``n*text_gap``。
    ``offset`` の符号で側を選ぶ。

    Returns
    -------
    dict
        ``{"p0","p1","line":(q0,q1),"ext0","ext1","text_xy","normal",
        "angle_deg","length_px"}``。

    Raises
    ------
    ValueError
        2 点が一致(向きが無い)、非有限、offset が 0。
    """
    a = _pt(p0, "p0")
    b = _pt(p1, "p1")
    off = _num(offset, "offset")
    ext = _num(extension, "extension", lo=0.0)
    tg = _num(text_gap, "text_gap", lo=0.0)
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    if length < 1e-9:
        raise ValueError("p0 and p1 coincide — a dimension of zero length has no direction")
    if off == 0.0:
        raise ValueError("offset must be non-zero (the dimension line would sit on the "
                         "measured edge and hide it)")
    ux, uy = dx / length, dy / length
    nx, ny = -uy, ux
    s = 1.0 if off > 0 else -1.0
    q0 = (a[0] + nx * off, a[1] + ny * off)
    q1 = (b[0] + nx * off, b[1] + ny * off)
    e0 = (a, (a[0] + nx * (off + s * ext), a[1] + ny * (off + s * ext)))
    e1 = (b, (b[0] + nx * (off + s * ext), b[1] + ny * (off + s * ext)))
    mid = ((q0[0] + q1[0]) / 2.0, (q0[1] + q1[1]) / 2.0)
    txy = (mid[0] + s * nx * tg, mid[1] + s * ny * tg)
    return {"p0": a, "p1": b, "line": (q0, q1), "ext0": e0, "ext1": e1, "text_xy": txy,
            "normal": (s * nx, s * ny), "angle_deg": math.degrees(math.atan2(uy, ux)),
            "length_px": length}


def annotate_dimension(img, p0, p1, units_per_pixel=1.0, unit="px", offset=20.0,
                       extension=6.0, color="neutral", width=1.5, head_len=9.0,
                       head_width=6.0, label_fmt="{:.1f}", font_size=11, box_alpha=0.6,
                       text_color=None, scheme="okabe_ito", font_path=None, layout=None):
    """画像(image2d)を返す: 寸法線(両端矢じり + 補助線 + 値と単位)。

    値は ``|p1-p0| * units_per_pixel``(閉形式)。幾何は
    :func:`annotate_dimension_layout`。

    Raises
    ------
    ValueError
        :func:`annotate_dimension_layout` と同じ + units_per_pixel が非正、
        寸法線が画像の外、文字が収まらない。
    """
    a = _prep(img)
    upp = _num(units_per_pixel, "units_per_pixel", lo=1e-300)
    w = _num(width, "width", lo=0.5)
    hl = _num(head_len, "head_len", lo=0.0)
    hw = _num(head_width, "head_width", lo=0.0)
    if layout is None:
        layout = annotate_dimension_layout(p0, p1, offset=offset, extension=extension)
    q0, q1 = layout["line"]
    H, W = a.shape[:2]
    for name, q in (("q0", q0), ("q1", q1)):
        if not (0 <= q[0] <= W - 1 and 0 <= q[1] <= H - 1):
            raise ValueError(f"dimension line end {tuple(round(v, 1) for v in q)} is outside "
                             f"the {W}x{H} image — reduce offset or move the points")
    a = _aa_polyline(a, list(layout["ext0"]), color, width=w, scheme=scheme)
    a = _aa_polyline(a, list(layout["ext1"]), color, width=w, scheme=scheme)
    span = layout["length_px"]
    if hl > 0 and hw > 0:
        if 2 * hl > 0.8 * span:
            k = 0.4 * span / hl
            hl, hw = hl * k, hw * k
        mid = ((q0[0] + q1[0]) / 2.0, (q0[1] + q1[1]) / 2.0)
        tri0, base0 = _head_polygon(mid, q0, hl, hw)
        tri1, base1 = _head_polygon(mid, q1, hl, hw)
        a = _aa_polyline(a, [base0, base1], color, width=w, scheme=scheme)
        a = filled_polygon(a, tri0, color=color, scheme=scheme)
        a = filled_polygon(a, tri1, color=color, scheme=scheme)
    else:
        a = _aa_polyline(a, [q0, q1], color, width=w, scheme=scheme)
    nx, ny = layout["normal"]
    text = f"{label_fmt.format(span * upp)} {unit}".rstrip()
    a = text_box(a, text, layout["text_xy"], color=color,
                 anchor=_text_anchor_for_direction(nx, ny), pad=3, font_size=font_size,
                 box_alpha=box_alpha, text_color=text_color, font_path=font_path,
                 scheme=scheme)
    return a


# ---------------------------------------------------------------- 角度

def annotate_angle_layout(a, vertex, b, radius=30.0, text_gap=12.0):
    """table(dict)を返す: 3 点 ``a, vertex, b`` のなす角(小さい方)の弧と文字位置。

    角度は画面座標(x 右・y 下)で ``atan2`` から出すので、``start_deg``/``end_deg``
    は :func:`arc` と同じ「x 軸から時計回り」の度。

    Returns
    -------
    dict
        ``{"vertex","angle_deg","start_deg","end_deg","radius","text_xy",
        "bisector_deg"}``。

    Raises
    ------
    ValueError
        a か b が vertex と一致、非有限、radius が非正。
    """
    pa, pv, pb = _pt(a, "a"), _pt(vertex, "vertex"), _pt(b, "b")
    r = _num(radius, "radius", lo=1e-9)
    tg = _num(text_gap, "text_gap", lo=0.0)
    if math.hypot(pa[0] - pv[0], pa[1] - pv[1]) < 1e-9 or \
            math.hypot(pb[0] - pv[0], pb[1] - pv[1]) < 1e-9:
        raise ValueError("a and b must differ from vertex — a ray of zero length has no angle")
    ta = math.degrees(math.atan2(pa[1] - pv[1], pa[0] - pv[0])) % 360.0
    tb = math.degrees(math.atan2(pb[1] - pv[1], pb[0] - pv[0])) % 360.0
    span = (tb - ta) % 360.0
    if span <= 180.0:
        start, end = ta, tb
    else:
        start, end, span = tb, ta, 360.0 - span
    bis = (start + span / 2.0) % 360.0
    txy = (pv[0] + (r + tg) * math.cos(math.radians(bis)),
           pv[1] + (r + tg) * math.sin(math.radians(bis)))
    return {"vertex": pv, "angle_deg": span, "start_deg": start, "end_deg": end,
            "radius": r, "text_xy": txy, "bisector_deg": bis}


def annotate_angle(img, a, vertex, b, radius=30.0, color="emphasis", width=1.5,
                   draw_rays=True, label_fmt="{:.1f}°", font_size=11, box_alpha=0.6,
                   text_color=None, scheme="okabe_ito", font_path=None, layout=None):
    """画像(image2d)を返す: 3 点のなす角を弧と値で示す(必要なら 2 本の腕も)。

    Raises
    ------
    ValueError
        :func:`annotate_angle_layout` と同じ + 頂点が画像の外、文字が収まらない。
    """
    im = _prep(img)
    w = _num(width, "width", lo=0.5)
    rays = _flag(draw_rays, "draw_rays")
    if layout is None:
        layout = annotate_angle_layout(a, vertex, b, radius=radius)
    pv = layout["vertex"]
    H, W = im.shape[:2]
    if not (0 <= pv[0] <= W - 1 and 0 <= pv[1] <= H - 1):
        raise ValueError(f"vertex {pv} is outside the {W}x{H} image")
    if rays:
        im = _aa_polyline(im, [_pt(a, "a"), pv], color, width=w, scheme=scheme)
        im = _aa_polyline(im, [_pt(b, "b"), pv], color, width=w, scheme=scheme)
    im = _aa_arc(im, pv, layout["radius"], layout["start_deg"], layout["end_deg"], color,
                 width=w, scheme=scheme)
    im = text_box(im, label_fmt.format(layout["angle_deg"]), layout["text_xy"], color=color,
                  anchor="cm", pad=3, font_size=font_size, box_alpha=box_alpha,
                  text_color=text_color, font_path=font_path, scheme=scheme)
    return im


# ---------------------------------------------------------------- スケールバー(切りのよい長さ)

def _nice_floor(v):
    """v 以下で最大の 1/2/5 × 10^k。"""
    if v <= 0:
        raise ValueError("value must be positive")
    mag = 10.0 ** math.floor(math.log10(v))
    norm = v / mag
    return mag * (5.0 if norm >= 5.0 else (2.0 if norm >= 2.0 else 1.0))


def annotate_scale_bar_layout(shape, units_per_pixel, unit="µm", corner="rb",
                              target_fraction=0.2, margin=14, thickness=5):
    """table(dict)を返す: 画像幅の ``target_fraction`` 以下で**切りのよい**長さのバー。

    長さは ``1/2/5 × 10^k`` のうち ``target_fraction * W * units_per_pixel`` 以下の
    最大値。画素長 = ``round(length / units_per_pixel)``。

    Returns
    -------
    dict
        ``{"length","px","rect":(x,y,w,h),"unit","corner","label"}``。

    Raises
    ------
    ValueError
        units_per_pixel / target_fraction が非正、未知の corner、
        バーが 1 画素未満か画像に収まらない。
    """
    H, W = _shape2(shape)
    upp = _num(units_per_pixel, "units_per_pixel", lo=1e-300)
    frac = _num(target_fraction, "target_fraction", lo=1e-9, hi=1.0)
    margin = _num(margin, "margin", lo=0, integer=True)
    th = _num(thickness, "thickness", lo=1, integer=True)
    if corner not in _CORNERS:
        raise ValueError(f"corner must be one of {_CORNERS} (got: {corner!r})")
    target = frac * (W - 2 * margin) * upp
    if target <= 0:
        raise ValueError(f"margin {margin} leaves no room for a bar in a {W}px wide image")
    length = _nice_floor(target)
    px = int(round(length / upp))
    if px < 1:
        raise ValueError(f"{length:g} {unit} is under one pixel at {upp:g} {unit}/px")
    x0 = margin if corner[0] == "l" else W - margin - px
    y0 = margin if corner[1] == "t" else H - margin - th
    if x0 < 0 or y0 < 0 or y0 + th > H:
        raise ValueError(f"a {px}px bar does not fit in the {W}x{H} image with margin {margin}")
    return {"length": float(length), "px": px, "rect": (int(x0), int(y0), px, th),
            "unit": str(unit), "corner": corner, "label": f"{length:g} {unit}".rstrip()}


def annotate_scale_bar(img, units_per_pixel, unit="µm", corner="rb", target_fraction=0.2,
                       margin=14, color="neutral", thickness=5, font_size=13,
                       box_alpha=0.55, text_color=None, scheme="okabe_ito", font_path=None,
                       layout=None):
    """画像(image2d)を返す: 隅に置く切りのよい長さのスケールバー(値と単位つき)。

    :func:`scale_bar` は長さを**呼び手が決める**のに対し、こちらは画素分解能から
    長さを選ぶ(:func:`annotate_scale_bar_layout`)。上隅では文字をバーの下に、
    下隅では上に置く。

    Raises
    ------
    ValueError
        :func:`annotate_scale_bar_layout` と同じ + 文字が画像に収まらない。
    """
    a = _prep(img)
    if layout is None:
        layout = annotate_scale_bar_layout(a.shape[:2], units_per_pixel, unit=unit,
                                           corner=corner, target_fraction=target_fraction,
                                           margin=margin, thickness=thickness)
    x0, y0, px, th = layout["rect"]
    _check_inside(a, (x0, y0, px, th), name="scale bar", what="scale bar")
    w = np.zeros(a.shape[:2], dtype=np.float64)
    w[y0:y0 + th, x0:x0 + px] = 1.0
    a = _blend(a, w, _channel_color(a, color, scheme), 1.0)
    if layout["corner"][1] == "t":
        txy, anchor = (x0 + px // 2, y0 + th + 3), "ct"
    else:
        txy, anchor = (x0 + px // 2, y0 - 3), "cb"
    return text_box(a, layout["label"], txy, anchor=anchor, pad=3, box_alpha=box_alpha,
                    font_size=font_size, font_path=font_path, text_color=text_color,
                    scheme=scheme)


# ---------------------------------------------------------------- 方位矢印

def annotate_orientation(img, angle_deg=0.0, corner="rt", xy=None, size=26.0, margin=16,
                         label="N", color="neutral", width=2, font_size=12, box_alpha=0.0,
                         text_color=None, scheme="okabe_ito", font_path=None):
    """画像(image2d)を返す: 方位(北)や向きを示す矢印 + 文字。

    ``angle_deg`` は **画面の上を 0、時計回りが正**(地図の方位と同じ)。矢印は
    ``xy``(中心)か ``corner`` の隅に置く。

    Raises
    ------
    ValueError
        size が非正、矢印が画像に収まらない、未知の corner。
    """
    a = _prep(img)
    ang = _num(angle_deg, "angle_deg")
    sz = _num(size, "size", lo=2.0)
    H, W = a.shape[:2]
    if xy is None:
        margin = _num(margin, "margin", lo=0, integer=True)
        # 矢印 + 文字がまとめて隅に収まるよう、文字の分だけ内側に寄せる
        cx, cy = _corner_xy(corner, W, H, margin)
        reach = sz / 2.0 + (float(font_size) if label else 0.0)
        cx = cx + (reach if corner[0] == "l" else -reach)
        cy = cy + (reach if corner[1] == "t" else -reach)
    else:
        cx, cy = _pt(xy, "xy")
    dx, dy = math.sin(math.radians(ang)), -math.cos(math.radians(ang))
    tip = (cx + dx * sz / 2.0, cy + dy * sz / 2.0)
    tail = (cx - dx * sz / 2.0, cy - dy * sz / 2.0)
    for name, p in (("tip", tip), ("tail", tail)):
        if not (0 <= p[0] <= W - 1 and 0 <= p[1] <= H - 1):
            raise ValueError(f"orientation arrow {name} {tuple(round(v, 1) for v in p)} is "
                             f"outside the {W}x{H} image — reduce size or move it")
    a = arrow(a, tail, tip, color=color, width=int(max(1, round(width))),
              head_len=0.45 * sz, head_width=0.35 * sz, scheme=scheme)
    if label:
        txy = (tip[0] + dx * (font_size * 0.8), tip[1] + dy * (font_size * 0.8))
        a = text_box(a, str(label), txy, color=color, anchor="cm", pad=2, font_size=font_size,
                     box_alpha=box_alpha, text_color=text_color, font_path=font_path,
                     scheme=scheme)
    return a


# ---------------------------------------------------------------- 隅の拡大差し込み

def annotate_inset_layout(shape, src_rect, corner="rt", factor=None, margin=10,
                          max_fraction=0.4):
    """table(dict)を返す: 拡大差し込みの置き場所と倍率を閉形式で決める。

    ``factor=None`` なら「幅・高さとも画像の ``max_fraction`` 以下」で最大の
    整数倍率。差し込みが元枠に重なる隅は ValueError(自分の元を隠す)。

    Returns
    -------
    dict
        ``{"src_rect","dst_rect","factor","corner"}``。

    Raises
    ------
    ValueError
        元枠が画像外、倍率 < 1 か非整数、差し込みが収まらない/元枠と重なる。
    """
    H, W = _shape2(shape)
    sx, sy, sw, sh = _rect(src_rect, "src_rect")
    if sx < 0 or sy < 0 or sx + sw > W or sy + sh > H:
        raise ValueError(f"src_rect {(sx, sy, sw, sh)} is not inside the {W}x{H} image")
    margin = _num(margin, "margin", lo=0, integer=True)
    frac = _num(max_fraction, "max_fraction", lo=1e-9, hi=1.0)
    if corner not in _CORNERS:
        raise ValueError(f"corner must be one of {_CORNERS} (got: {corner!r})")
    if factor is None:
        f = int(min((frac * W) // sw, (frac * H) // sh))
        if f < 1:
            raise ValueError(f"src_rect {sw}x{sh} is too large for a {max_fraction:g}-fraction "
                             f"inset in a {W}x{H} image")
    else:
        f = _num(factor, "factor", lo=1, integer=True)
    dw, dh = sw * f, sh * f
    dx = margin if corner[0] == "l" else W - margin - dw
    dy = margin if corner[1] == "t" else H - margin - dh
    if dx < 0 or dy < 0 or dx + dw > W or dy + dh > H:
        raise ValueError(f"a x{f} inset ({dw}x{dh}) does not fit in the {corner} corner of a "
                         f"{W}x{H} image with margin {margin}")
    if _overlaps((sx, sy, sw, sh), (dx, dy, dw, dh)):
        raise ValueError(f"the inset in corner {corner!r} would cover its own source "
                         f"{(sx, sy, sw, sh)} — pick another corner")
    return {"src_rect": (sx, sy, sw, sh), "dst_rect": (int(dx), int(dy), int(dw), int(dh)),
            "factor": int(f), "corner": corner}


def annotate_inset(img, src_rect, corner="rt", factor=None, margin=10, color="emphasis",
                   width=2, connect=True, label=None, font_size=11, scheme="okabe_ito",
                   font_path=None, style=None, layout=None):
    """画像(image2d)を返す: 元枠の拡大を隅に差し込み、対応する角を線で結ぶ。

    倍率と位置は :func:`annotate_inset_layout`、描画は :func:`zoom_inset`
    (最近傍の整数倍 = 元の画素そのもの)。

    Raises
    ------
    ValueError
        :func:`annotate_inset_layout` と同じ。
    """
    a = _prep(img)
    if layout is None:
        layout = annotate_inset_layout(a.shape[:2], src_rect, corner=corner, factor=factor,
                                       margin=margin)
    dx, dy, dw, dh = layout["dst_rect"]
    a = zoom_inset(a, layout["src_rect"], (dx, dy), factor=layout["factor"], color=color,
                   width=width, connect=_flag(connect, "connect"), scheme=scheme, style=style)
    if label is not None:
        a = text_box(a, str(label), (dx + 3, dy + 3), color=color, anchor="lt", pad=2,
                     font_size=font_size, font_path=font_path, scheme=scheme)
    return a


# ---------------------------------------------------------------- マスクの輪郭

def annotate_outline_layout(mask):
    """table(dict)を返す: 2 値マスクの境界ループ(画素の辺に沿う閉多角形)と重心。

    輪郭は :func:`contours_xld._trace_mask_boundaries`(外側 + 穴、成分ごと)。
    多角形の面積はマスクの画素数と厳密に一致する。

    Returns
    -------
    dict
        ``{"contours": [(K,2) の (x,y)], "centroid": (x,y), "area": int,
        "bbox": (x,y,w,h), "n_loops": int}``。

    Raises
    ------
    ValueError
        mask が 2-D でない、真の画素が無い、非有限。
    """
    import contours_xld
    m = np.asarray(mask)
    if m.ndim != 2:
        raise ValueError(f"mask must be 2-D (H,W) (got shape {m.shape})")
    if m.dtype != bool:
        mm = np.asarray(m, dtype=np.float64)
        if not np.all(np.isfinite(mm)):
            raise ValueError("mask holds non-finite values")
        m = mm > 0.5
    if not m.any():
        raise ValueError("mask has no true pixel — there is no region to outline")
    loops = contours_xld._trace_mask_boundaries(m)
    contours = [np.ascontiguousarray(lp[:, ::-1]) for lp in loops]        # (row,col) -> (x,y)
    rr, cc = np.nonzero(m)
    return {"contours": contours, "centroid": (float(cc.mean()), float(rr.mean())),
            "area": int(rr.size),
            "bbox": (int(cc.min()), int(rr.min()), int(cc.max() - cc.min() + 1),
                     int(rr.max() - rr.min() + 1)),
            "n_loops": len(contours)}


def annotate_outline(img, mask, label=None, color="emphasis", width=1.5, alpha=1.0,
                     dash=None, font_size=12, label_offset=(0, 0), box_alpha=0.6,
                     text_color=None, scheme="okabe_ito", font_path=None, layout=None):
    """画像(image2d)を返す: マスクの輪郭を(AA の)閉折れ線で描き、重心に文字を置く。

    Raises
    ------
    ValueError
        mask の形が画像と違う、真の画素が無い、alpha が [0,1] の外。
    """
    a = _prep(img)
    m = np.asarray(mask)
    if m.shape != a.shape[:2]:
        raise ValueError(f"mask shape {m.shape} does not match the image {a.shape[:2]} — "
                         "masks are indexed [row, col]")
    al = _num(alpha, "alpha", lo=0.0, hi=1.0)
    w = _num(width, "width", lo=0.5)
    if layout is None:
        layout = annotate_outline_layout(m)
    for c in layout["contours"]:
        a = _aa_polyline(a, c, color, width=w, closed=True, dash=dash, alpha=al, scheme=scheme)
    if label is not None:
        ox, oy = _pt(label_offset, "label_offset")
        cx, cy = layout["centroid"]
        a = text_box(a, str(label), (cx + ox, cy + oy), color=color, anchor="cm", pad=3,
                     font_size=font_size, box_alpha=box_alpha, text_color=text_color,
                     font_path=font_path, scheme=scheme)
    return a


# ---------------------------------------------------------------- 経路に沿う文字

def annotate_text_path_layout(text, path, font_size=13, font_path=None, spacing=1.0,
                              start=0.0):
    """table(dict)を返す: 折れ線に沿って 1 文字ずつ置く位置と傾き(弧長で決める)。

    文字 i の中心は弧長 ``s_i = start + Σ_{j<i} w_j*spacing + w_i/2``、傾きは
    その位置の線分の接線角(画面座標、度)。経路より長い文字列は ValueError。

    Returns
    -------
    dict
        ``{"chars": [{"char","s","xy","angle_deg","width"}], "length": 経路長,
        "used": 文字が占める弧長}``。

    Raises
    ------
    ValueError
        文字が空、経路が 2 点未満か長さゼロ、非有限、文字列が経路より長い。
    """
    text = str(text)
    if not text:
        raise ValueError("text is empty")
    p = _pts(path, "path", min_n=2)
    seg = np.hypot(np.diff(p[:, 0]), np.diff(p[:, 1]))
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    total = float(cum[-1])
    if total < 1e-9:
        raise ValueError("path has zero length")
    sp = _num(spacing, "spacing", lo=0.1)
    s0 = _num(start, "start", lo=0.0)
    m = measure_text("x", font_size=font_size, font_path=font_path, min_font_size=1)
    font = m["font"]
    chars, s = [], s0
    for ch in text:
        w = _text_width(ch, font) if ch != " " else _text_width("n", font)
        mid = s + w / 2.0
        if s + w > total + 1e-9:
            raise ValueError(
                f"text {text!r} needs {s + w - s0:.1f}px of path from start={s0:g} but the "
                f"path is {total:.1f}px long — shorten the text, lower font_size or "
                "lengthen the path (letters piling up at the end would be unreadable)")
        k = int(np.searchsorted(cum, mid, side="right") - 1)
        k = min(max(k, 0), len(seg) - 1)
        t = 0.0 if seg[k] < 1e-12 else (mid - cum[k]) / seg[k]
        xy = (float(p[k, 0] + t * (p[k + 1, 0] - p[k, 0])),
              float(p[k, 1] + t * (p[k + 1, 1] - p[k, 1])))
        ang = math.degrees(math.atan2(p[k + 1, 1] - p[k, 1], p[k + 1, 0] - p[k, 0]))
        chars.append({"char": ch, "s": float(mid), "xy": xy, "angle_deg": ang,
                      "width": float(w)})
        s += w * sp
    return {"chars": chars, "length": total, "used": float(s - s0)}


def annotate_text_path(img, text, path, font_size=13, color="neutral", spacing=1.0,
                       start=0.0, draw_path=False, width=1.0, scheme="okabe_ito",
                       font_path=None, layout=None):
    """画像(image2d)を返す: 折れ線に沿って文字を置く(各字を接線角に回転)。

    文字の板は敷かない(経路の上に載せる用途なので)。配置は
    :func:`annotate_text_path_layout`。

    Raises
    ------
    ValueError
        :func:`annotate_text_path_layout` と同じ + 回転した字が画像の外に出る。
    """
    a = _prep(img)
    if layout is None:
        layout = annotate_text_path_layout(text, path, font_size=font_size,
                                           font_path=font_path, spacing=spacing, start=start)
    Image, ImageDraw, _ = _pil()
    font = _font(int(font_size), font_path)
    H, W = a.shape[:2]
    if _flag(draw_path, "draw_path"):
        a = _aa_polyline(a, _pts(path, "path", 2), color, width=width, scheme=scheme)
    mask = np.zeros((H, W), dtype=np.float64)
    lh = _line_height(font)
    for it in layout["chars"]:
        ch = it["char"]
        if ch.strip() == "":
            continue
        cw = max(1, int(math.ceil(_text_width(ch, font))))
        glyph = Image.new("L", (cw + 4, lh + 4), 0)
        ImageDraw.Draw(glyph).text((2, 2), ch, fill=255, font=font)
        rot = glyph.rotate(-it["angle_deg"], expand=True, resample=Image.BICUBIC)
        g = np.asarray(rot, dtype=np.float64) / 255.0
        gh, gw = g.shape
        x0 = int(round(it["xy"][0] - gw / 2.0))
        y0 = int(round(it["xy"][1] - gh / 2.0))
        if x0 < 0 or y0 < 0 or x0 + gw > W or y0 + gh > H:
            raise ValueError(f"character {ch!r} at {tuple(round(v, 1) for v in it['xy'])} "
                             f"leaves the {W}x{H} image once rotated — move the path inward")
        mask[y0:y0 + gh, x0:x0 + gw] = np.maximum(mask[y0:y0 + gh, x0:x0 + gw], g)
    return _blend(a, mask, _channel_color(a, color, scheme), 1.0)


# ---------------------------------------------------------------- 色分け重ね + カラーバー

def annotate_colorbar(img, field, rect, lut=None, vmin=None, vmax=None, alpha=0.6,
                      mask=None, unit="", label_fmt="{:.3g}", orientation="vertical",
                      font_size=12, scheme="okabe_ito", font_path=None, text_color=None,
                      nan_transparent=False):
    """画像(image2d)を返す: スカラ場を LUT で色分けして重ね、カラーバーを添える。

    ``t = (field - vmin)/(vmax - vmin)`` を [0,1] に**クリップ**し ``lut[round(t*(n-1))]``
    で色にする(範囲外の値は端の色 —— カラーバーの端と同じなので嘘にならない)。
    重ねは ``alpha`` の α 合成、``mask`` を渡せばその画素だけ。

    Parameters
    ----------
    field : (H, W)
        画像と同じ大きさのスカラ場。非有限は ``nan_transparent=True`` のときだけ
        透明として許す(既定は ValueError)。
    lut : (n, 3) or None
        None なら :func:`palette.diverging_lut` の 256 段。
    vmin, vmax : float or None
        None なら場の(有限値の)最小・最大。等しければ ValueError。

    Raises
    ------
    ValueError
        形の不一致、非有限(許可なし)、vmin == vmax、alpha が [0,1] の外、
        バーの矩形が画像外、LUT の形。
    """
    a = _prep(img)
    f = np.asarray(field, dtype=np.float64)
    if f.shape != a.shape[:2]:
        raise ValueError(f"field shape {f.shape} does not match the image {a.shape[:2]}")
    al = _num(alpha, "alpha", lo=0.0, hi=1.0)
    finite = np.isfinite(f)
    if not finite.all():
        if not _flag(nan_transparent, "nan_transparent"):
            raise ValueError(f"field holds {int((~finite).sum())} non-finite value(s); pass "
                             "nan_transparent=True to leave them uncoloured on purpose")
    if not finite.any():
        raise ValueError("field has no finite value to colour")
    t_lut = palette.diverging_lut(256) if lut is None else np.asarray(lut, dtype=np.float64)
    if t_lut.ndim != 2 or t_lut.shape[1] < 3 or t_lut.shape[0] < 2:
        raise ValueError(f"lut must be (n>=2, 3) (got: {t_lut.shape})")
    lo = float(np.min(f[finite])) if vmin is None else _num(vmin, "vmin")
    hi = float(np.max(f[finite])) if vmax is None else _num(vmax, "vmax")
    if lo == hi:
        raise ValueError(f"vmin == vmax == {lo:g} — a colour scale over a zero range says nothing")
    t = np.clip((np.where(finite, f, lo) - lo) / (hi - lo), 0.0, 1.0)
    idx = np.round(t * (t_lut.shape[0] - 1)).astype(int)
    rgb = t_lut[idx][..., :3]
    wgt = finite.astype(np.float64)
    if mask is not None:
        m = np.asarray(mask)
        if m.shape != a.shape[:2]:
            raise ValueError(f"mask shape {m.shape} does not match the image {a.shape[:2]}")
        wgt = wgt * (m.astype(np.float64) > 0.5)
    w = np.clip(wgt * al, 0.0, 1.0)
    if a.ndim == 2:
        a = a * (1.0 - w) + rgb.mean(axis=2) * w
    else:
        c = a.shape[2]
        col = rgb if c >= 3 else rgb.mean(axis=2)[..., None]
        if c == 4:
            col = np.concatenate([rgb, np.ones(rgb.shape[:2] + (1,))], axis=2)
        a = a * (1.0 - w)[..., None] + col * w[..., None]
    return color_bar(a, t_lut, rect, vmin=lo, vmax=hi, unit=unit, label_fmt=label_fmt,
                     orientation=orientation, font_size=font_size, font_path=font_path,
                     scheme=scheme, text_color=text_color)


# ---------------------------------------------------------------- パネル文字と図の組版

def _panel_letter(i, style):
    if i < 0 or i >= len(_LETTERS):
        raise ValueError(f"panel index {i} has no single letter (a-z); split the figure")
    ch = _LETTERS[i]
    if style == "paren":
        return f"({ch})"
    if style == "half":
        return f"{ch})"
    if style == "plain":
        return ch
    if style == "upper":
        return ch.upper()
    raise ValueError(f"letter style must be 'paren'|'half'|'plain'|'upper' (got: {style!r})")


def annotate_panel_label(img, letter="a", corner="lt", margin=8, style="paren", font_size=16,
                         color="neutral", box_alpha=0.72, text_color=None, box_color=None,
                         scheme="okabe_ito", font_path=None):
    """画像(image2d)を返す: パネル文字 ``(a)``/``(b)`` を隅に置く。

    ``letter`` は 1 文字(``'a'``)か 0 始まりの番号(``0`` → a)。``style`` で
    ``(a)`` / ``a)`` / ``a`` / ``A`` を選ぶ。

    Raises
    ------
    ValueError
        未知の corner / style、文字が画像に収まらない。
    """
    a = _prep(img)
    H, W = a.shape[:2]
    margin = _num(margin, "margin", lo=0, integer=True)
    if isinstance(letter, str):
        if len(letter) != 1 or letter.lower() not in _LETTERS:
            raise ValueError(f"letter must be a single a-z letter or an index (got: {letter!r})")
        idx = _LETTERS.index(letter.lower())
    else:
        idx = _num(letter, "letter", lo=0, integer=True)
    text = _panel_letter(idx, style)
    x, y = _corner_xy(corner, W, H, margin)
    return text_box(a, text, (x, y), color=color, anchor=corner, pad=4, font_size=font_size,
                    box_alpha=box_alpha, text_color=text_color, box_color=box_color,
                    font_path=font_path, scheme=scheme)


def annotate_figure_grid_layout(shapes, ncols=2, pad=10, caption_h=32, title_h=0,
                                letter_style="paren"):
    """table(dict)を返す: 多パネル図の組版(セル・パネル・見出し帯の矩形)を閉形式で。

    :func:`panel_grid` と同じ式: ``cw/ch`` は最大パネル寸、
    ``W = 2*pad + ncols*cw + (ncols-1)*pad``、
    ``H = title_h + 2*pad + nrows*(ch+caption_h) + (nrows-1)*pad``。
    パネルは拡大せずセルの中央に置く。

    Returns
    -------
    dict
        ``{"size":(H,W), "cells":[(x,y,cw,ch)], "panels":[(x,y,w,h)],
        "captions":[(x,y,cw,caption_h)], "letters":[str], "ncols", "nrows"}``。

    Raises
    ------
    ValueError
        shapes が空、ncols < 1、負の余白、26 枚を超える。
    """
    shp = [_shape2(s, f"shapes[{i}]") for i, s in enumerate(shapes)]
    if not shp:
        raise ValueError("shapes is empty")
    ncols = _num(ncols, "ncols", lo=1, integer=True)
    pad = _num(pad, "pad", lo=0, integer=True)
    cap = _num(caption_h, "caption_h", lo=0, integer=True)
    th = _num(title_h, "title_h", lo=0, integer=True)
    cw = max(w for _, w in shp)
    ch = max(h for h, _ in shp)
    n = len(shp)
    nrows = (n + ncols - 1) // ncols
    W = 2 * pad + ncols * cw + (ncols - 1) * pad
    H = th + 2 * pad + nrows * (ch + cap) + (nrows - 1) * pad
    cells, panels, caps, letters = [], [], [], []
    for i, (h, w) in enumerate(shp):
        r, c = divmod(i, ncols)
        x0 = pad + c * (cw + pad)
        y0 = th + pad + r * (ch + cap + pad)
        cells.append((x0, y0, cw, ch))
        panels.append((x0 + (cw - w) // 2, y0 + (ch - h) // 2, w, h))
        caps.append((x0, y0 + ch, cw, cap))
        letters.append(_panel_letter(i, letter_style))
    return {"size": (H, W), "cells": cells, "panels": panels, "captions": caps,
            "letters": letters, "ncols": ncols, "nrows": nrows}


def annotate_figure_grid(panels, captions=None, ncols=2, pad=10, caption_h=32, letters=True,
                         letter_style="paren", title=None, font_size=14, min_font_size=9,
                         background=1.0, border=1, border_color="neutral",
                         text_color=None, scheme="okabe_ito", font_path=None):
    """画像(image2d)を返す: 画像 + 見出しを一枚の図に組む(余白一定・パネル文字つき)。

    見出しは ``"(a) caption"``(``letters=True``)。白地(``background=1.0``)が既定
    なので文字は自動で暗色になる(:func:`text_box` のコントラスト規則)。
    幾何は :func:`annotate_figure_grid_layout`(``title`` があるときの ``title_h``
    は :func:`measure_text` から同じ式で決まる)。

    Raises
    ------
    ValueError
        panels が空、captions の数不一致、見出しが帯に収まらない、26 枚超。
    """
    ps = [_prep(p) for p in panels]
    if not ps:
        raise ValueError("panels is empty")
    if captions is not None:
        captions = [str(s) for s in captions]
        if len(captions) != len(ps):
            raise ValueError(f"captions has {len(captions)} entries for {len(ps)} panels")
    use_letters = _flag(letters, "letters")
    lay = annotate_figure_grid_layout([p.shape[:2] for p in ps], ncols=ncols, pad=pad,
                                      caption_h=caption_h, letter_style=letter_style)
    labels = None
    if use_letters or captions is not None:
        labels = []
        for i in range(len(ps)):
            parts = []
            if use_letters:
                parts.append(lay["letters"][i])
            if captions is not None and captions[i]:
                parts.append(captions[i])
            labels.append(" ".join(parts))
    return panel_grid(ps, labels=labels, ncols=lay["ncols"], pad=pad, label_h=caption_h,
                      background=background, title=title, font_size=font_size,
                      min_font_size=min_font_size, font_path=font_path,
                      text_color=text_color, border=border, border_color=border_color,
                      scheme=scheme)
