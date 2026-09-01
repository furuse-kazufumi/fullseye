# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""drawlist — 描画を **ためてから一度に流す**(遅延描画)層。

即時描画(``imagedraw.draw_line(img, ...)`` が絵の付いた配列をその場で返す)は、
呼んだ瞬間に絵になる。速いし分かりやすいが、**絵になってしまうと検査できない**。
本モジュールは同じ描画を **コマンドの列**として持ち、``flush()`` で初めてラスタ化する。

## なぜ列にするのか(この repo に固有の 3 つの理由)

1. **フラッシュ前に検査できる。** この repo では過去に、機械検査が「公開不可 0 件」を
   返した図に、目視で 6 件の不具合(文字のはみ出し・ラベルどうしの衝突・真っ黒な
   パネル)が残っていた。**文字がはみ出したかどうかは、ラスタ化した後の画素からは
   判定できない** ―― 出来上がった画素は「切れた文字」と「元々そういう形」を区別
   しない。ところがコマンドの上なら、位置・文字数・字送りから箱の大きさが計算でき、
   画像に収まるかを**描く前に**判定できる。:meth:`DrawList.inspect` がそれを返し、
   :meth:`DrawList.flush` は該当コマンドの **添字と種別を添えて**例外にする。
2. **図の差分が「なぜ違うか」で取れる。** これまで図の同一性は SHA-256 だけで見て
   いた。ハッシュは「変わった」ことしか言わないので、変わった理由は人が絵を見比べる
   しかない。コマンド列は JSON になるので、``3 番目の text_box の文字列が変わった``
   という**構造の差分**が取れる(:func:`diff_command_lists`)。
3. **同じ列を別の解像度へ流せる。** :meth:`DrawList.scale` は座標と寸法を一括で
   変換するので、サムネイルと原寸を**同じ記述から**出せる。

## 即時描画は既定のまま

本モジュールは **足すだけ**である。``imagedraw`` 等の既存の呼び出しは 1 ビットも
変わらない。同じ描画を即時方式と蓄積方式の両方で行うと **画素が完全一致**する
(``tests/test_drawlist.py::test_deferred_matches_immediate_bit_for_bit``)。

## 状態をモジュールに置かない

:mod:`drawstyle` と同じ理由で、**モジュールグローバルな可変状態を持たない**。
描画状態を装置(窓)側に持たせる対話的な方式は、対話の場では自然だが、ここでは
図の再生成で SHA-256 一致を要件にしており、生成器は並行して走る。共有された既定が
あると「どの図を先に描いたか」が結果に混ざり、それは例外にならず**もっともらしく
間違った図**として出てくる。よってコマンド列は :class:`DrawList` インスタンスが
所有し、``flush`` の結果はそのインスタンスの中身だけで決まる。

## ハンドラは名前で遅延解決する

各コマンドは他の描画層の関数へ委譲する。委譲先は **import 時に固定しない** ――
``flush`` の時点で ``importlib`` により解決し、見つからなければ **その op だけ**
明示エラーで落ちる。描画層が並行して育っている最中でも、本モジュール単体で動く。
解決順は (1) インスタンスの ``handlers`` → (2) 層のモジュール → (3) ``fullseye``
facade。ハンドラの契約は ``fn(img, **args) -> img`` のみ。

委譲表(:data:`COMMAND_SPECS`)には **引数がそのまま JSON になるコマンドだけ**を
置く。画像を作って返す種類(タイル生成・パーティクルの状態更新・光源マップ生成)は
``fn(img, ...) -> img`` でもなく、引数に配列を要るので「列を JSON で差分する」という
要件と噛み合わない。使いたければ ``handlers=`` で束ねる ―― 表に載せて呼び出し時に
失敗させるより、載せないほうが正直である。

## 用語

``flush_buffer`` は、蓄積した描画をまとめて表示側へ流す操作の一般的な呼び名で、
別ツールから来た利用者が引けるように :meth:`DrawList.flush` の別名として置いてある
(``docs/PROVENANCE.md`` の三分法でいう「lookup のための別名」)。
"""
from __future__ import annotations

import dataclasses
import importlib
import json
import math
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np

__all__ = [
    "DrawList",
    "DrawListError",
    "CommandSpec",
    "COMMAND_SPECS",
    "TEXT_ADVANCE_RATIO",
    "default_text_metrics",
    "measured_text_metrics",
    "diff_command_lists",
    "format_diff",
    "flush_buffer",
]

#: 文字幅の見積りに使う **字送り比**(1 文字の送り幅 / 文字の高さ)。
#:
#: 値は実測から取った: PIL の既定ビットマップフォントは 1 文字の送りが 9 px、
#: 行の高さ(ascent 10 + descent 3)が 13 px なので 9/13 = 0.692。それを **切り上げて
#: 0.70** にしてある ―― 検査は「収まらない」側に倒れるべきで、収まると判定して
#: 実際にははみ出すのが最悪だからである。
#:
#: これは *見積り* であって、実際に描かれる字形の実測ではない。実測が使えるときは
#: :func:`measured_text_metrics`(:class:`DrawList` の既定)がそちらを優先し、
#: 本値は退避先として残る。任意の計測器を ``text_metrics=`` で差し込むこともできる。
TEXT_ADVANCE_RATIO = 0.70


def default_text_metrics(text: str, size: float) -> tuple[float, float]:
    """文字列の外接箱 ``(幅, 高さ)`` を画素で見積もる(等幅モデル)。

    Args:
        text: 描く文字列。改行を含むと行数ぶん高さが増える。
        size: 文字の高さ(画素)。

    Returns:
        ``(w, h)``。``w = TEXT_ADVANCE_RATIO * size * 最長行の文字数``、
        ``h = size * 行数``。
    """
    lines = str(text).split("\n")
    longest = max((len(ln) for ln in lines), default=0)
    return (TEXT_ADVANCE_RATIO * float(size) * longest, float(size) * max(1, len(lines)))


def measured_text_metrics(text: str, size: float) -> tuple[float, float]:
    """本物の文字計測が使えるならそれを、駄目なら :func:`default_text_metrics` を使う。

    :class:`DrawList` の既定。文字を実際に描く層に計測関数(``measure_text``)が
    あればそれを引く ―― 見積りより実測のほうが、はみ出し判定が正確になる。
    層がまだ無い / その文字列を測れない(改行つきなど)ときは、黙って落ちるのではなく
    等幅の見積りへ退く。**退いたこと自体は結果を甘くしない**: 見積りは切り上げ側の
    比を使っているので、判定は「収まらない」側に倒れる。
    """
    try:
        annotate = importlib.import_module("annotate")
        m = annotate.measure_text(str(text), font_size=int(round(float(size))))
        return (float(m["width"]), float(m["height"]))
    except Exception:
        return default_text_metrics(text, size)


class DrawListError(ValueError):
    """フラッシュ前検査 / 委譲先解決 / 委譲先の実行で起きた失敗。

    メッセージには必ず **どのコマンドか(添字と種別)** が入る。列のどこが悪いのか
    分からない例外は、絵を見るまで原因が分からないのと同じで役に立たない。

    Attributes:
        index: コマンドの添字(列の外で起きた失敗は ``-1``)。
        kind: コマンドの種別(列の外で起きた失敗は ``"<drawlist>"``)。
        code: 機械可読な理由コード(:meth:`DrawList.inspect` の ``code`` と同じ)。
    """

    def __init__(self, index: int, kind: str, message: str, code: str = "error"):
        self.index = int(index)
        self.kind = str(kind)
        self.code = str(code)
        super().__init__(f"drawlist command[{self.index}] {self.kind}: {message} [{self.code}]")


@dataclass(frozen=True)
class CommandSpec:
    """1 つのコマンド種別が「どこへ委譲し、どの引数が幾何量か」の定義。

    Attributes:
        kind: コマンド種別名(コマンド列に入る文字列)。
        module: 委譲先モジュール名(``flush`` 時に遅延 import する)。
        candidates: 試す関数名。層ごとに名前が確定していないので複数許す。
            先頭から順に探し、どれも無ければその op だけ明示エラー。
        points: ``(x, y)`` か ``(N, 2)`` の点を持つ引数名。:meth:`DrawList.scale`
            で倍率を掛け、はみ出し検査の対象になる。
        lengths: 画素長のスカラ引数名(線幅・半径・文字高など)。``scale`` で倍率を掛ける。
        paths: 点の入れ子(輪郭・矩形など)。``scale`` では中の数値を一律に掛ける。
        inverse: **画素あたりの量**の引数名(``units_per_pixel`` など)。``scale`` では
            倍率で **割る** ―― 画素が細かくなれば 1 画素あたりの物理長は縮むので、
            ここを掛けてしまうと図に書かれた寸法が静かに間違う。
    """

    kind: str
    module: str
    candidates: tuple[str, ...]
    points: tuple[str, ...] = ()
    lengths: tuple[str, ...] = ()
    paths: tuple[str, ...] = ()
    inverse: tuple[str, ...] = ()


def _specs() -> dict[str, CommandSpec]:
    """委譲表。**画素になる引数だけ**を持つコマンドをここに置く。

    画像そのものを引数に取る合成系(タイル生成・パーティクルの状態・光源マップの
    生成など、``fn(img, ...) -> img`` ではなく **画像を作って返す** 種類)は、
    JSON で差分を取るという要件と噛み合わないので表には入れない。使いたければ
    :class:`DrawList` の ``handlers=`` で束ねる。
    """
    raw = [
        # --- プリミティブ(imagedraw + drawstyle) ---
        ("line", "imagedraw", ("draw_line",), ("p0", "p1"), ("width",), (), ()),
        ("polyline", "imagedraw", ("draw_polyline",), ("points",), ("width",), (), ()),
        ("circle", "imagedraw", ("draw_circle",), ("center",), ("radius", "width"), (), ()),
        ("markers", "imagedraw", ("draw_markers",), ("points",), ("size", "width"), (), ()),
        ("contour", "imagedraw", ("draw_contour",), (), ("width",), ("contour",), ()),
        # --- 図注(annotate 層) ---
        ("text_box", "annotate", ("text_box", "draw_text_box", "annotate_text_box"),
         ("xy",), ("font_size", "pad", "border", "min_font_size", "max_width"), (), ()),
        ("arrow", "annotate", ("arrow", "draw_arrow", "annotate_arrow"),
         ("p0", "p1"), ("width", "head_len", "head_width"), (), ()),
        ("legend", "annotate", ("legend_box", "legend", "draw_legend"),
         ("xy",), ("swatch", "row_gap", "pad", "font_size", "border"), (), ()),
        ("colorbar", "annotate", ("color_bar", "colorbar", "draw_colorbar"),
         (), ("font_size", "border"), ("rect",), ()),
        # scale_bar の ``length`` は **物理量**(µm など)なので倍率を掛けない。
        # 代わりに ``units_per_pixel`` を **割る** ―― 画素が細かくなれば 1 画素あたりの
        # 物理長は縮む。ここを間違えると図のスケールが静かに嘘になる。
        ("scalebar", "annotate", ("scale_bar", "scalebar", "draw_scalebar"),
         ("xy",), ("thickness", "margin", "font_size"), (), ("units_per_pixel",)),
        # ``axes`` は「画素の枠 + データ範囲」の複合記述なので、数値を一律に倍すると
        # データ範囲まで倍になる。よって scale では触らない(組み直して渡すこと)。
        ("axes", "annotate", ("axes_frame", "axes", "draw_axes"), (), ("width",), (), ()),
        ("inset", "annotate", ("zoom_inset", "inset", "draw_inset"),
         ("dst_xy",), ("width",), ("src_rect",), ()),
        # --- 2-D グラフィックス(gfx2d 層) ---
        ("sprite", "gfx2d", ("sprite_blit", "blit_sprite", "draw_sprite"),
         (), ("x", "y"), (), ()),
        ("vignette", "gfx2d", ("vignette",), (), (), (), ()),
        ("bloom", "gfx2d", ("bloom",), (), ("sigma",), (), ()),
        ("color_grade", "gfx2d", ("color_grade",), (), (), (), ()),
    ]
    return {r[0]: CommandSpec(*r) for r in raw}


#: 種別 → :class:`CommandSpec`。**読み取り専用として扱うこと**(実行中に書き換えると
#: 図の結果が「どの図を先に描いたか」に依存し始める)。差し替えたいときは
#: :class:`DrawList` の ``handlers=`` を使う。
COMMAND_SPECS: dict[str, CommandSpec] = _specs()

_STYLE_TAG = "__drawstyle__"


# --------------------------------------------------------------------------- #
# 値の正規化 ―― コマンド列は「JSON にできる素の値」だけで出来ている               #
# --------------------------------------------------------------------------- #
def _norm(v: Any) -> Any:
    """引数を JSON 化できる素の値へ落とす(numpy / タプル / DrawStyle を含む)。

    正規化を **追加時に** 行うのが要点。ここで正規化しておけば ``to_json`` →
    ``from_json`` が **完全に同じコマンド列**を返す(タプルが list に化けて
    往復が壊れる、ということが起きない)。
    """
    if v is None or isinstance(v, (bool, str)):
        return v
    if isinstance(v, (int, float, np.integer, np.floating)):
        f = float(v)
        return f
    if dataclasses.is_dataclass(v) and type(v).__name__ == "DrawStyle":
        return {_STYLE_TAG: {k: _norm(val) for k, val in dataclasses.asdict(v).items()}}
    if isinstance(v, np.ndarray):
        return _norm(v.tolist())
    if isinstance(v, dict):
        return {str(k): _norm(val) for k, val in v.items()}
    if isinstance(v, (list, tuple)):
        return [_norm(x) for x in v]
    raise TypeError(
        f"drawlist arguments must be JSON-representable (numbers, strings, bools, None, "
        f"sequences, dicts, DrawStyle); got {type(v).__name__}. "
        "画像そのものを引数に渡したい場合は handlers= 側で束ねること "
        "(列は JSON で差分が取れることを要件にしている)")


def _denorm(v: Any) -> Any:
    """``_norm`` の逆。``DrawStyle`` のタグを実体へ戻す(遅延 import)。"""
    if isinstance(v, dict):
        if _STYLE_TAG in v and len(v) == 1:
            drawstyle = importlib.import_module("drawstyle")
            fields = {k: (tuple(x) if isinstance(x, list) else x)
                      for k, x in v[_STYLE_TAG].items()}
            return drawstyle.DrawStyle(**fields)
        return {k: _denorm(val) for k, val in v.items()}
    if isinstance(v, list):
        return [_denorm(x) for x in v]
    return v


def _scale_numbers(v: Any, factor: float) -> Any:
    """入れ子の中の数値だけを一律に倍する(bool と文字列には触れない)。"""
    if isinstance(v, bool) or v is None or isinstance(v, str):
        return v
    if isinstance(v, float):
        return v * factor
    if isinstance(v, dict):
        return {k: _scale_numbers(x, factor) for k, x in v.items()}
    if isinstance(v, list):
        return [_scale_numbers(x, factor) for x in v]
    return v


def _as_points(v: Any) -> list[tuple[float, float]]:
    """``[x, y]`` か ``[[x, y], ...]`` を ``(x, y)`` の並びへ均す(解釈できなければ空)。"""
    if not isinstance(v, list) or not v:
        return []
    if all(isinstance(x, float) for x in v):
        return [(v[0], v[1])] if len(v) >= 2 else []
    out: list[tuple[float, float]] = []
    for row in v:
        if isinstance(row, list) and len(row) >= 2 \
                and isinstance(row[0], float) and isinstance(row[1], float):
            out.append((row[0], row[1]))
    return out


def _luma(color: Any) -> float | None:
    """色を明度スカラへ(数値でなければ ``None``)。"""
    if isinstance(color, float):
        return color
    if isinstance(color, (list, tuple)) and color and all(isinstance(c, float) for c in color):
        return float(np.mean(color[:3]))
    return None


# --------------------------------------------------------------------------- #
# DrawList                                                                     #
# --------------------------------------------------------------------------- #
@dataclass
class DrawList:
    """描画コマンドの列。``flush()`` で初めて画素になる。

    使い方::

        dl = DrawList((180, 240, 3))
        dl.line((10, 10), (200, 150), color="wrong", width=2)
        dl.circle((120, 90), 40, color="right", z=1.0)
        img = dl.flush()

    Attributes:
        shape: ``(H, W)`` か ``(H, W, C)``。フラッシュ先の大きさ。
        background: 下地の色(``None`` なら描画層の既定 = 黒)。
        handlers: 種別 → ``fn(img, **args) -> img``。**最優先で使われる**。
            委譲先の関数名や引数名が :data:`COMMAND_SPECS` の想定と違うとき、
            あるいは層がまだ無いときの逃げ道。
        text_metrics: ``fn(text, size) -> (w, h)``。既定は
            :func:`default_text_metrics`。
        allow_clip: ``True`` にすると、画像の外を指すコマンドを例外にせず
            警告に落とす(端で切れる図を意図して作るとき)。

    列そのものは :attr:`commands` で読める(常に複製を返すので、外から書き換えても
    列は汚れない)。
    """

    shape: tuple[int, ...]
    background: Any = None
    handlers: dict[str, Callable[..., Any]] = field(default_factory=dict)
    text_metrics: Callable[[str, float], tuple[float, float]] = measured_text_metrics
    allow_clip: bool = False
    _cmds: list[dict] = field(default_factory=list, repr=False)

    def __post_init__(self):
        dims = tuple(self.shape)
        if len(dims) not in (2, 3):
            raise ValueError(f"shape must be (H,W) or (H,W,C) (got: {dims})")
        for v in dims:
            if isinstance(v, bool) or not float(v).is_integer() or int(v) < 1:
                raise ValueError(f"shape entries must be integers >= 1 (got: {dims})")
        self.shape = tuple(int(v) for v in dims)
        self.handlers = dict(self.handlers)
        self._cmds = [dict(c) for c in self._cmds]

    # -- 列の中身 ----------------------------------------------------------- #
    @property
    def commands(self) -> list[dict]:
        """コマンド列の複製。``[{"kind":..., "z":..., "args":{...}}, ...]``。"""
        return json.loads(json.dumps(self._cmds))

    def __len__(self) -> int:
        return len(self._cmds)

    def add(self, kind: str, z: float = 0.0, **args) -> "DrawList":
        """任意の種別のコマンドを積む(名前つきメソッドはこれの薄い包み)。

        Args:
            kind: :data:`COMMAND_SPECS` の種別名、または ``handlers`` に持たせた名前。
            z: 重ね順。小さいほど先に(下に)描く。**同じ z は積んだ順**を保つ。
            **args: 委譲先へそのまま渡る引数。JSON 化できる値と ``DrawStyle`` のみ。

        Returns:
            自分自身(連鎖できる)。

        Raises TypeError: JSON 化できない引数。
        """
        self._cmds.append({"kind": str(kind), "z": _norm(z), "args": {k: _norm(v)
                                                                     for k, v in args.items()}})
        return self

    # -- プリミティブ ------------------------------------------------------- #
    def line(self, p0, p1, z: float = 0.0, **kw) -> "DrawList":
        """``(x,y)=p0`` から ``p1`` への直線(``imagedraw.draw_line`` へ委譲)。"""
        return self.add("line", z, p0=p0, p1=p1, **kw)

    def polyline(self, points, z: float = 0.0, **kw) -> "DrawList":
        """点列 ``(N,2)`` の折れ線(``closed=True`` で多角形)。"""
        return self.add("polyline", z, points=points, **kw)

    def circle(self, center, radius, z: float = 0.0, **kw) -> "DrawList":
        """中心 ``(x,y)``・半径 ``radius`` の円(``fill=True`` で塗り潰し)。"""
        return self.add("circle", z, center=center, radius=radius, **kw)

    def markers(self, points, z: float = 0.0, **kw) -> "DrawList":
        """点列の各点へマーカー(``shape='cross'|'square'|'dot'``)。"""
        return self.add("markers", z, points=points, **kw)

    def contour(self, contour, z: float = 0.0, **kw) -> "DrawList":
        """輪郭 ``{"cs": [(row,col)...]}`` か ``(N,2)`` を閉じて描く。"""
        return self.add("contour", z, contour=contour, **kw)

    # -- 図注 --------------------------------------------------------------- #
    def text_box(self, xy, text, font_size: float = 14.0, z: float = 0.0, **kw) -> "DrawList":
        """下敷き付きの文字。``xy`` は ``anchor`` が指す隅、``font_size`` は文字高(画素)。

        フラッシュ前に、``text_metrics`` で測った箱が画像に収まるかを検査する。
        収まらなければ **描かずに** :class:`DrawListError` になる。``anchor`` は
        ``"lt"``(左上、既定)のように「横 ``l|c|r`` + 縦 ``t|c|b``」で書く。
        """
        return self.add("text_box", z, text=text, xy=xy, font_size=font_size, **kw)

    def arrow(self, p0, p1, z: float = 0.0, **kw) -> "DrawList":
        """``p0`` から ``p1`` への矢印。"""
        return self.add("arrow", z, p0=p0, p1=p1, **kw)

    def legend(self, xy, entries, z: float = 0.0, **kw) -> "DrawList":
        """凡例(``entries`` は ``[[色または役割名, ラベル], ...]``)。"""
        return self.add("legend", z, entries=entries, xy=xy, **kw)

    def colorbar(self, lut, rect, z: float = 0.0, **kw) -> "DrawList":
        """カラーバー(``lut`` は ``(N,3)``、``rect`` は画素の矩形)。"""
        return self.add("colorbar", z, lut=lut, rect=rect, **kw)

    def scalebar(self, length, units_per_pixel, z: float = 0.0, **kw) -> "DrawList":
        """スケールバー。``length`` は **物理量**、``units_per_pixel`` が画素との橋。"""
        return self.add("scalebar", z, length=length, units_per_pixel=units_per_pixel, **kw)

    def axes(self, axes, z: float = 0.0, **kw) -> "DrawList":
        """軸と目盛り(``axes`` は画素の枠とデータ範囲の複合記述)。"""
        return self.add("axes", z, axes=axes, **kw)

    def inset(self, src_rect, dst_xy, z: float = 0.0, **kw) -> "DrawList":
        """拡大の差し込み(``src_rect`` を ``dst_xy`` へ拡大して置く)。"""
        return self.add("inset", z, src_rect=src_rect, dst_xy=dst_xy, **kw)

    # -- 2-D グラフィックス -------------------------------------------------- #
    def sprite(self, sprite, x: float = 0.0, y: float = 0.0, z: float = 0.0,
               **kw) -> "DrawList":
        """スプライト合成(``sprite`` は入れ子リストの画素)。"""
        return self.add("sprite", z, sprite=sprite, x=x, y=y, **kw)

    def vignette(self, z: float = 0.0, **kw) -> "DrawList":
        """周辺減光(ポスト処理)。"""
        return self.add("vignette", z, **kw)

    def bloom(self, z: float = 0.0, **kw) -> "DrawList":
        """高輝度のにじみ(ポスト処理)。"""
        return self.add("bloom", z, **kw)

    def color_grade(self, z: float = 0.0, **kw) -> "DrawList":
        """色調整(ポスト処理)。"""
        return self.add("color_grade", z, **kw)

    # -- 幾何 --------------------------------------------------------------- #
    def _spec(self, kind: str) -> CommandSpec | None:
        return COMMAND_SPECS.get(kind)

    def _anchor_points(self, cmd: dict) -> list[tuple[float, float]]:
        """そのコマンドが「どこを指しているか」の代表点(``(x, y)``)。"""
        kind, args = cmd["kind"], cmd["args"]
        spec = self._spec(kind)
        pts: list[tuple[float, float]] = []
        if spec is not None:
            for name in spec.points:
                pts.extend(_as_points(args.get(name)))
            for name in spec.paths:
                v = args.get(name)
                if isinstance(v, dict):                       # 輪郭は (row, col)
                    for arr in v.get("cs", []):
                        pts.extend((c, r) for r, c in _as_points(arr))
                else:
                    pts.extend(_as_points(v))
        return pts

    def _extent(self, cmd: dict) -> tuple[float, float, float, float] | None:
        """描画がおよぶ外接箱 ``(x0, y0, x1, y1)``(分からなければ ``None``)。"""
        kind, args = cmd["kind"], cmd["args"]
        if kind == "text_box":
            box = self._text_box_extent(cmd)
            return box
        pts = self._anchor_points(cmd)
        if not pts:
            return None
        pad = 0.0
        if kind == "circle":
            pad = float(args.get("radius", 0.0) or 0.0)
        elif kind in ("markers", "particles"):
            pad = float(args.get("size", 4.0) or 0.0)
        pad += float(args.get("width", 1.0) or 0.0) / 2.0
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)

    def _text_box_extent(self, cmd: dict) -> tuple[float, float, float, float] | None:
        """文字の箱 ``(x0, y0, x1, y1)``。``anchor`` を解いて実際に占める矩形を返す。"""
        args = cmd["args"]
        xy = _as_points(args.get("xy"))
        if not xy or not isinstance(args.get("text"), str):
            return None
        w, h = self.text_metrics(args["text"], float(args.get("font_size", 14.0)))
        pad = float(args.get("pad", 5.0) or 0.0)
        w, h = w + 2 * pad, h + 2 * pad
        anchor = str(args.get("anchor", "lt"))
        ax = anchor[0] if anchor else "l"
        ay = anchor[1] if len(anchor) > 1 else "t"
        x, y = xy[0]
        x0 = x - (0.0 if ax == "l" else w / 2.0 if ax == "c" else w)
        y0 = y - (0.0 if ay == "t" else h / 2.0 if ay == "c" else h)
        return (x0, y0, x0 + w, y0 + h)

    # -- 検査 --------------------------------------------------------------- #
    def inspect(self) -> list[dict]:
        """**ラスタ化する前に**列を検査し、問題の一覧を返す。

        Returns:
            ``{"index", "kind", "severity", "code", "message"}`` の並び。
            ``severity`` は ``"error"``(:meth:`flush` が既定で落ちる)か
            ``"warning"``(``strict=True`` のときだけ落ちる)。

        検査の中身は :func:`DrawList.check_codes` を参照。
        """
        H, W = self.shape[0], self.shape[1]
        issues: list[dict] = []

        def add(i, kind, sev, code, msg):
            issues.append({"index": i, "kind": kind, "severity": sev, "code": code,
                           "message": msg})

        text_boxes: list[tuple[int, tuple[float, float, float, float]]] = []
        for i, cmd in enumerate(self._cmds):
            kind, args = cmd["kind"], cmd["args"]
            z = cmd["z"]
            if not isinstance(z, float) or not math.isfinite(z):
                add(i, kind, "error", "z_not_finite",
                    f"z must be a finite number (got {z!r}); a non-finite z has no place in a "
                    "stable sort, so the stacking order would silently depend on the input order")
            if kind not in self.handlers and self._spec(kind) is None:
                add(i, kind, "error", "unknown_command",
                    f"unknown command kind; known: {', '.join(sorted(COMMAND_SPECS))} "
                    "(or pass handlers={...})")
                continue
            issues.extend(self._check_colors(i, kind, args))
            if kind == "text_box":
                box = self._text_box_extent(cmd)
                if box is None:
                    add(i, kind, "error", "text_unmeasurable",
                        "text_box needs pos=(x,y) and a string text to be measurable "
                        "before rasterisation")
                else:
                    text_boxes.append((i, box))
                    w, h = box[2] - box[0], box[3] - box[1]
                    if w > W or h > H:
                        add(i, kind, "error", "text_does_not_fit",
                            f"text box is {w:.1f}x{h:.1f} px but the image is {W}x{H} px "
                            f"(text={args['text']!r}); it can never fit")
                    elif box[0] < 0 or box[1] < 0 or box[2] > W or box[3] > H:
                        over = (max(0.0, -box[0]), max(0.0, -box[1]),
                                max(0.0, box[2] - W), max(0.0, box[3] - H))
                        add(i, kind, "error", "text_does_not_fit",
                            f"text box {tuple(round(v, 1) for v in box)} runs off the "
                            f"{W}x{H} image by (left, top, right, bottom) = "
                            f"{tuple(round(v, 1) for v in over)} px (text={args['text']!r})")
            for (x, y) in self._anchor_points(cmd):
                if not (math.isfinite(x) and math.isfinite(y)):
                    add(i, kind, "error", "point_not_finite",
                        f"anchor point ({x}, {y}) is not finite")
                elif not (0 <= x <= W - 1 and 0 <= y <= H - 1):
                    add(i, kind, "error" if not self.allow_clip else "warning",
                        "out_of_bounds",
                        f"anchor point ({x:g}, {y:g}) is outside the {W}x{H} image; the "
                        "raster layer clamps silently, so the figure would look plausible "
                        "and be wrong (pass allow_clip=True to demote this to a warning)")
            ext = self._extent(cmd)
            if ext is not None and kind != "text_box":
                if ext[0] < 0 or ext[1] < 0 or ext[2] > W or ext[3] > H:
                    add(i, kind, "warning", "extent_clipped",
                        f"drawing extends to {tuple(round(v, 1) for v in ext)}, outside the "
                        f"{W}x{H} image; part of it will be clipped")

        for a in range(len(text_boxes)):
            for b in range(a + 1, len(text_boxes)):
                ia, ba = text_boxes[a]
                ib, bb = text_boxes[b]
                ox = min(ba[2], bb[2]) - max(ba[0], bb[0])
                oy = min(ba[3], bb[3]) - max(ba[1], bb[1])
                if ox > 0 and oy > 0:
                    add(ib, "text_box", "warning", "label_collision",
                        f"label box overlaps command[{ia}] by {ox:.1f}x{oy:.1f} px; "
                        "overlapping labels are unreadable and a pixel check cannot tell "
                        "them from a deliberate overlay")
        return issues

    def _check_colors(self, i: int, kind: str, args: dict) -> list[dict]:
        """役割名・スキームが引けるか、文字と下敷きの明度差があるかを見る。"""
        out: list[dict] = []
        try:
            drawstyle = importlib.import_module("drawstyle")
        except ImportError:                                  # 層が無ければ検査は棄権する
            return out
        scheme = "okabe_ito"
        style = args.get("style")
        if isinstance(style, dict) and _STYLE_TAG in style:
            scheme = style[_STYLE_TAG].get("scheme", scheme) or scheme
        scheme = args.get("scheme", scheme) or scheme
        names = ("color", "fill_color", "bg", "background", "text_color", "box_color",
                 "border_color")
        pairs = [(k, args.get(k)) for k in names]
        if isinstance(style, dict) and _STYLE_TAG in style:
            pairs += [(f"style.{k}", style[_STYLE_TAG].get(k))
                      for k in ("color", "fill_color")]
        resolved: dict[str, Any] = {}
        for name, val in pairs:
            if val is None:
                continue
            try:
                resolved[name] = drawstyle.resolve_color(val, scheme)
            except ValueError as exc:
                out.append({"index": i, "kind": kind, "severity": "error",
                            "code": "unknown_role",
                            "message": f"argument {name}={val!r} is not a usable colour: {exc}"})
        fg = _luma(resolved.get("text_color", resolved.get("color")))
        bg = _luma(resolved.get("box_color",
                                resolved.get("bg", resolved.get("background"))))
        if fg is not None and bg is not None and abs(fg - bg) < 0.15:
            out.append({"index": i, "kind": kind, "severity": "warning", "code": "low_contrast",
                        "message": f"foreground luma {fg:.3f} and background luma {bg:.3f} differ "
                                   f"by {abs(fg - bg):.3f} (< 0.15); the panel will read as a "
                                   "flat block and the content will be invisible"})
        return out

    @staticmethod
    def check_codes() -> dict[str, str]:
        """検査の理由コード → 意味(何を捕まえるか)。"""
        return {
            "unknown_command": "種別が未知(誤字・未実装の層)。error",
            "z_not_finite": "z が NaN/inf。安定ソートの意味が消える。error",
            "point_not_finite": "座標が NaN/inf。error",
            "out_of_bounds": "指し先が画像の外。ラスタ層は黙ってクランプする。error",
            "text_does_not_fit": "文字の箱が画像に入らない/端からはみ出す。error",
            "text_unmeasurable": "pos か text が無く、描く前に測れない。error",
            "unknown_role": "色の役割名か scheme が引けない。error",
            "extent_clipped": "図形の広がりが端で切れる。warning",
            "label_collision": "ラベルの箱どうしが重なる。warning",
            "low_contrast": "文字と下敷きの明度差が小さい(真っ黒なパネル)。warning",
        }

    # -- 別解像度へ --------------------------------------------------------- #
    def scale(self, factor: float) -> "DrawList":
        """座標と寸法を ``factor`` 倍した **新しい列**を返す(自分は変わらない)。

        サムネイルと原寸を同じ記述から出すための操作。``z``・真偽値・文字列・
        色は変換しない(倍率は幾何量にだけ意味がある)。

        Raises ValueError: ``factor`` が有限の正数でない、または倍した大きさが
            1 画素未満になる。
        """
        f = float(factor)
        if not math.isfinite(f) or f <= 0:
            raise ValueError(f"factor must be a finite positive number, got {factor!r}")
        dims = list(self.shape)
        dims[0] = int(round(dims[0] * f))
        dims[1] = int(round(dims[1] * f))
        if dims[0] < 1 or dims[1] < 1:
            raise ValueError(
                f"scaling {self.shape[:2]} by {f} gives {tuple(dims[:2])}, which has no pixels")
        out = DrawList(tuple(dims), background=self.background, handlers=dict(self.handlers),
                       text_metrics=self.text_metrics, allow_clip=self.allow_clip)
        for cmd in self._cmds:
            spec = self._spec(cmd["kind"])
            args = dict(cmd["args"])
            if spec is not None:
                for name in spec.points + spec.paths:
                    if name in args:
                        args[name] = _scale_numbers(args[name], f)
                for name in spec.lengths:
                    if name in args and isinstance(args[name], float):
                        args[name] = args[name] * f
                for name in spec.inverse:                 # 1 画素あたりの物理量は縮む
                    if name in args and isinstance(args[name], float):
                        args[name] = args[name] / f
            out._cmds.append({"kind": cmd["kind"], "z": cmd["z"], "args": args})
        return out

    # -- JSON --------------------------------------------------------------- #
    def to_json(self, indent: int | None = None) -> str:
        """列を JSON 文字列にする(``shape`` と下地の色も含む)。"""
        return json.dumps({"version": 1, "shape": list(self.shape),
                           "background": _norm(self.background), "commands": self._cmds},
                          ensure_ascii=False, indent=indent)

    @classmethod
    def from_json(cls, text: str, handlers=None, text_metrics=None,
                  allow_clip: bool = False) -> "DrawList":
        """:meth:`to_json` の出力から列を戻す。

        ``handlers`` / ``text_metrics`` は関数なので JSON には入らない ―― 戻すときに
        渡す。**コマンド列は往復で完全に一致する**
        (``tests/test_drawlist.py::test_json_round_trip_is_exact``)。
        """
        d = json.loads(text)
        if not isinstance(d, dict) or "commands" not in d or "shape" not in d:
            raise DrawListError(-1, "<drawlist>", "JSON must be an object with 'shape' and "
                                                  "'commands'", "bad_json")
        if d.get("version") != 1:
            raise DrawListError(-1, "<drawlist>",
                                f"unsupported drawlist version {d.get('version')!r} (expected 1)",
                                "bad_json")
        out = cls(tuple(d["shape"]), background=d.get("background"),
                  handlers=handlers or {},
                  text_metrics=text_metrics or measured_text_metrics, allow_clip=allow_clip)
        for j, cmd in enumerate(d["commands"]):
            if not isinstance(cmd, dict) or set(cmd) != {"kind", "z", "args"}:
                raise DrawListError(j, "<unknown>",
                                    "each command must be {'kind','z','args'}", "bad_json")
            out._cmds.append({"kind": str(cmd["kind"]), "z": _norm(cmd["z"]),
                              "args": {str(k): v for k, v in cmd["args"].items()}})
        return out

    # -- 委譲先の解決 -------------------------------------------------------- #
    def resolve(self, kind: str, index: int = -1) -> Callable[..., Any]:
        """種別 → ハンドラ関数。**呼ばれた時点で**解決する(import 時に固定しない)。

        順序: ``handlers`` → 層のモジュール → ``fullseye`` facade。

        Raises DrawListError: どこにも無い(その op だけが落ちる。列の他のコマンドや
            他の層には影響しない)。
        """
        if kind in self.handlers:
            return self.handlers[kind]
        spec = self._spec(kind)
        if spec is None:
            raise DrawListError(index, kind, "unknown command kind; known: "
                                             f"{', '.join(sorted(COMMAND_SPECS))}",
                                "unknown_command")
        tried: list[str] = []
        for source in (spec.module, "fullseye"):
            try:
                mod = importlib.import_module(source)
            except Exception:                                # 層がまだ無い / 壊れている
                tried.append(f"{source} (not importable)")
                continue
            for name in spec.candidates:
                if hasattr(mod, name):
                    return getattr(mod, name)
            tried.append(f"{source} (has none of {', '.join(spec.candidates)})")
        raise DrawListError(
            index, kind,
            f"no handler found — tried {'; '.join(tried)}. Pass handlers={{{kind!r}: fn}} "
            "with fn(img, **args) -> img, or install the drawing layer that provides it",
            "handler_missing")

    # -- フラッシュ ---------------------------------------------------------- #
    def flush(self, base=None, strict: bool = False, check: bool = True):
        """列を検査してからラスタ化する。

        Args:
            base: 下地の画像。``None`` なら ``shape`` と ``background`` から作る。
                渡した配列は **破壊しない**(複製に描く)。
            strict: ``True`` で警告(ラベル衝突・低コントラスト・端の切れ)も例外にする。
            check: ``False`` で検査を飛ばす(検査が重い巨大な列を、既に検査済みで
                流し直すときだけ)。

        Returns:
            ``[0,1]`` の float64 配列。

        Raises DrawListError: 検査に引っかかった / 委譲先が無い / 委譲先が失敗した。
            いずれも **どのコマンドか** がメッセージに入る。
        """
        if check:
            bad = [it for it in self.inspect()
                   if it["severity"] == "error" or (strict and it["severity"] == "warning")]
            if bad:
                first = bad[0]
                extra = f" (+{len(bad) - 1} more)" if len(bad) > 1 else ""
                raise DrawListError(first["index"], first["kind"],
                                    first["message"] + extra, first["code"])
        if base is None:
            imagedraw = importlib.import_module("imagedraw")
            img = (imagedraw.new_canvas(self.shape) if self.background is None
                   else imagedraw.new_canvas(self.shape, _denorm(self.background)))
        else:
            img = np.array(base, dtype=np.float64)
        order = sorted(range(len(self._cmds)), key=lambda i: self._cmds[i]["z"])
        for i in order:
            cmd = self._cmds[i]
            fn = self.resolve(cmd["kind"], i)
            args = {k: _denorm(v) for k, v in cmd["args"].items()}
            try:
                img = fn(img, **args)
            except DrawListError:
                raise
            except Exception as exc:
                raise DrawListError(i, cmd["kind"],
                                    f"{type(exc).__name__} from {getattr(fn, '__name__', fn)}: "
                                    f"{exc}", "handler_failed") from exc
        return img

    def flush_buffer(self, base=None, strict: bool = False, check: bool = True):
        """:meth:`flush` の別名(蓄積したものをまとめて流す、の一般的な呼び名)。"""
        return self.flush(base=base, strict=strict, check=check)


def flush_buffer(drawlist: DrawList, base=None, strict: bool = False, check: bool = True):
    """関数形の :meth:`DrawList.flush`(``flush_buffer(dl)``)。"""
    return drawlist.flush(base=base, strict=strict, check=check)


# --------------------------------------------------------------------------- #
# 構造の差分                                                                    #
# --------------------------------------------------------------------------- #
def _walk(prefix: str, a: Any, b: Any, out: list[tuple[str, Any, Any]]) -> None:
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            _walk(f"{prefix}.{k}" if prefix else str(k), a.get(k, "<missing>"),
                  b.get(k, "<missing>"), out)
        return
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for j, (x, y) in enumerate(zip(a, b)):
            _walk(f"{prefix}[{j}]", x, y, out)
        return
    if a != b:
        out.append((prefix, a, b))


def diff_command_lists(before: DrawList, after: DrawList) -> list[dict]:
    """2 つの列の **構造の差分**を返す。

    ハッシュは「変わった」としか言わないが、これは「``3 番目の text_box`` の
    ``args.text`` が ``'A'`` から ``'B'`` になった」まで言える。

    Returns:
        ``{"index", "change", "kind", "field", "old", "new"}`` の並び。
        ``change`` は ``"added"`` / ``"removed"`` / ``"changed"``。
        ``shape`` や下地の違いは ``index=-1`` の ``"changed"`` として出る。
    """
    a, b = before.commands, after.commands
    recs: list[dict] = []
    if tuple(before.shape) != tuple(after.shape):
        recs.append({"index": -1, "change": "changed", "kind": "<drawlist>", "field": "shape",
                     "old": list(before.shape), "new": list(after.shape)})
    if _norm(before.background) != _norm(after.background):
        recs.append({"index": -1, "change": "changed", "kind": "<drawlist>", "field": "background",
                     "old": _norm(before.background), "new": _norm(after.background)})
    for i in range(max(len(a), len(b))):
        if i >= len(b):
            recs.append({"index": i, "change": "removed", "kind": a[i]["kind"], "field": "",
                         "old": a[i], "new": None})
            continue
        if i >= len(a):
            recs.append({"index": i, "change": "added", "kind": b[i]["kind"], "field": "",
                         "old": None, "new": b[i]})
            continue
        if a[i]["kind"] != b[i]["kind"]:
            recs.append({"index": i, "change": "changed", "kind": b[i]["kind"], "field": "kind",
                         "old": a[i]["kind"], "new": b[i]["kind"]})
        fields: list[tuple[str, Any, Any]] = []
        _walk("z", a[i]["z"], b[i]["z"], fields)
        _walk("args", a[i]["args"], b[i]["args"], fields)
        for name, old, new in fields:
            recs.append({"index": i, "change": "changed", "kind": b[i]["kind"], "field": name,
                         "old": old, "new": new})
    return recs


def format_diff(records: list[dict]) -> list[str]:
    """:func:`diff_command_lists` の記録を 1 行ずつの読める文にする。"""
    out = []
    for r in records:
        head = f"command[{r['index']}] {r['kind']}"
        if r["change"] == "changed":
            out.append(f"{head}: {r['field']} {r['old']!r} -> {r['new']!r}")
        elif r["change"] == "added":
            out.append(f"{head}: added {r['new']!r}")
        else:
            out.append(f"{head}: removed {r['old']!r}")
    return out
