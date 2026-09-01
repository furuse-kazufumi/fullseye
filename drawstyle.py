# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""drawstyle — 描画の「状態」(色・線幅・線種・塗り)を **値** として持つ層。

## なぜグローバルな描画状態にしないのか

HALCON はウィンドウ(装置)に描画状態を持たせる: ``set_color`` / ``set_draw`` /
``set_line_width`` / ``set_line_style`` を呼ぶと、以後その窓への描画がその状態で
出る。対話的な HDevelop では自然な設計だが、**この repo で同じことをすると図が
壊れる**:

* 図の生成は決定的でなければならない。展示画像は再生成して **SHA-256 が一致する**
  ことを要件にしている。可変なモジュールグローバルがあると、「どの図を先に描いたか」
  が結果に混ざり、同じ関数を呼んでも前の図の設定が残る。
* 生成器は並行して走る。スレッド間で 1 つの既定を共有すると、レースで色が入れ替わる。
  これは例外にならず、**もっともらしく間違った図**として出てくる ―― 一番たちが悪い。

そこで正典は **不変値** :class:`DrawStyle` にした。``draw_*`` は ``style=`` で
受け取り、渡さなければ従来どおりの実線・白・幅 1 で描く。状態は引数として流れる
ので、図の見た目はその呼び出しだけで決まる(再現性が呼び出し側の履歴に依存しない)。

## それでも HALCON 流に書きたいとき

:func:`draw_style` はコンテキストマネージャで、**ブロックの中だけ** 既定のスタイルを
差し替える::

    with draw_style(color="wrong", line_style="dashed"):
        img = draw_polyline(img, pts)          # 破線・wrong 色

実体は :class:`contextvars.ContextVar` で、(a) スレッド/タスクごとに独立、
(b) ブロックを抜けると例外経路でも必ず元に戻る、(c) モジュールグローバルの既定
そのものは決して書き換わらない。``with`` の外の描画は影響を受けない。

``set_color`` / ``set_line_width`` / ``set_line_style`` / ``set_draw`` は
**HALCON に実在する演算子名を相互運用のために借りた別名**(``docs/PROVENANCE.md``
の三分法: 向こうに実在するものの識別子)。ただしこちらは装置を書き換えず、
**新しい :class:`DrawStyle` を返す**関数である::

    st = set_line_style(set_color(None, "wrong"), [10, 5])

## 線種

``line_style`` は名前(``"solid"`` / ``"dashed"`` / ``"dotted"`` / ``"dashdot"``)か、
HALCON の ``set_line_style([10,5])`` と同じ **画素長の明示パターン**
``[on, off, on, off, ...]`` を受ける。名前は :data:`LINE_STYLES` の別名にすぎない。

## 色

``color`` は次の 3 通り: float(グレー)/ RGB 三つ組 / :mod:`palette` の **役割名**
(``"right"`` ``"wrong"`` ``"neutral"`` ``"emphasis"`` ``"baseline"`` ``"reference"``)。
役割名で書けば図の作者が色を選ばなくて済み、流儀の変更は ``scheme=`` の 1 か所で済む。
"""
from __future__ import annotations

import contextvars
from contextlib import contextmanager
from dataclasses import dataclass, replace

import numpy as np

import palette

__all__ = [
    "DrawStyle",
    "LINE_STYLES",
    "DRAW_MODES",
    "check_width",
    "draw_style",
    "current_style",
    "resolve_pattern",
    "resolve_color",
    "set_color",
    "set_line_width",
    "set_line_style",
    "set_draw",
]

#: 名前つき線種 → 画素長パターン ``(on, off, ...)``。``"solid"`` だけ ``None``。
#: 値は HALCON のマニュアル例 ``set_line_style([10,5])`` に合わせた実用寄りの既定で、
#: 特別な意味はない ―― 厳密な長さが要るなら明示パターンを渡すこと。
LINE_STYLES: dict[str, tuple[float, ...] | None] = {
    "solid": None,
    "dashed": (10.0, 5.0),
    "dotted": (1.0, 4.0),
    "dashdot": (10.0, 4.0, 1.0, 4.0),
}

#: HALCON の ``set_draw`` に対応する塗りモード。
DRAW_MODES = ("margin", "fill")


def resolve_pattern(line_style) -> tuple[float, ...] | None:
    """線種指定 → ``(on, off, ...)`` の画素長タプル(実線は ``None``)。

    受けるもの: ``"solid"`` / ``"dashed"`` / ``"dotted"`` / ``"dashdot"``、
    ``None``(= 実線)、``[on, off, ...]`` の数値列(長さは偶数、各 run > 0)。

    Raises ValueError:
        未知の名前 / 空のパターン / 奇数長 / 0 以下の run 長 / 非有限値。
        **黙って実線には落とさない** ―― 落とすと「破線を指定したのに実線が出た」図が
        検査を素通りしてしまい、図を見た人しか気づけない。
    """
    if line_style is None:
        return None
    if isinstance(line_style, str):
        if line_style not in LINE_STYLES:
            raise ValueError(
                f"unknown line_style {line_style!r}; known: {', '.join(sorted(LINE_STYLES))} "
                "(or an explicit [on, off, ...] pixel-length pattern)")
        return LINE_STYLES[line_style]
    arr = np.asarray(line_style, dtype=np.float64).ravel()
    if arr.size == 0:
        raise ValueError("line_style pattern is empty; use 'solid' or None for a solid line")
    if arr.size % 2 != 0:
        raise ValueError(
            f"line_style pattern must have an even length (on/off pairs), got {arr.size}: "
            f"{list(arr)}")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"line_style pattern must be finite, got {list(arr)}")
    if np.any(arr <= 0.0):
        raise ValueError(
            f"line_style run lengths must all be > 0 pixels, got {list(arr)} "
            "(a zero-length run makes the phase undefined)")
    return tuple(float(v) for v in arr)


def resolve_color(color, scheme: str = "okabe_ito"):
    """色指定 → float(グレー)か RGB float の 3-タプル。

    * float / int → そのまま float(既存の呼び出しと同じ扱い)
    * 役割名の str → :func:`palette.role_color` を引く
    * シーケンス → float のタプル(長さは呼び出し側=画像のチャンネル数で解釈)

    Raises ValueError: 未知の役割名 / 未知の scheme / 非有限値 / 空のシーケンス。
    """
    if isinstance(color, str):
        try:
            return palette.role_color(color, scheme)
        except ValueError as exc:                      # 役割名も scheme も palette が判定
            raise ValueError(
                f"unknown colour role {color!r} ({exc}); roles: {', '.join(palette.ROLES)}"
            ) from exc
    if np.ndim(color) == 0:                            # float / numpy スカラ / 0-d 配列
        try:
            v = float(color)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"colour must be a number, a role name or a sequence, "
                             f"got {color!r}") from exc
        if not np.isfinite(v):
            raise ValueError(f"colour must be finite, got {color!r}")
        return v
    arr = np.asarray(color, dtype=np.float64).ravel()
    if arr.size == 0:
        raise ValueError("colour sequence is empty")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"colour must be finite, got {list(arr)}")
    return tuple(float(v) for v in arr)


def check_width(width):
    """線幅の検証。**値は丸めずそのまま返す**。

    丸めないのは :func:`imagedraw.draw_circle` が ``width / 2`` を輪郭帯の半幅に
    使うため ―― ここで int に丸めると小数幅の既存呼び出しの結果が変わる。

    Raises ValueError: 非数値 / 非有限 / 1 画素未満。
    """
    if isinstance(width, str) or not np.isscalar(width):
        raise ValueError(f"width must be a finite number of pixels, got {width!r}")
    w = float(width)
    if not np.isfinite(w) or w < 1.0:
        raise ValueError(f"width must be a finite number >= 1 pixel, got {width!r}")
    return width


@dataclass(frozen=True)
class DrawStyle:
    """描画状態の **値**(不変)。``draw_*`` に ``style=`` で渡す。

    Attributes:
        color: 線・輪郭の色。float / RGB 三つ組 / :mod:`palette` の役割名。
        width: 線幅(画素、>= 1)。
        line_style: ``"solid"`` 等の名前か ``[on, off, ...]`` の画素長パターン。
        draw: ``"margin"``(輪郭のみ)か ``"fill"``(塗る)。HALCON の ``set_draw`` 相当。
        fill_color: 塗り色。``None`` なら ``color`` と同じ。輪郭色と塗り色を
            分けたいときだけ指定する(``draw="fill"`` かつ両方指定で「塗り + 縁取り」)。
        scheme: 役割名 → 色の流儀(:mod:`palette` の scheme)。

    構築時に全項目を検証する(fail-closed)。不正な値でスタイルを作れないので、
    図を 1 枚描いてから間違いに気づく、ということが起きない。
    """

    color: object = 1.0
    width: float = 1
    line_style: object = "solid"
    draw: str = "margin"
    fill_color: object = None
    scheme: str = "okabe_ito"

    def __post_init__(self):
        check_width(self.width)
        if self.draw not in DRAW_MODES:
            raise ValueError(f"draw must be one of {DRAW_MODES}, got {self.draw!r}")
        # 検証のみ(正規化した値は保持せず、呼び出し時に解決する ―― 役割名を残す方が
        # スタイルを見たときに「なぜその色か」が分かる)。
        resolve_pattern(self.line_style)
        resolve_color(self.color, self.scheme)
        if self.fill_color is not None:
            resolve_color(self.fill_color, self.scheme)

    # --- 値としての派生(HALCON の set_* に対応するが、装置ではなく値を作る) ---
    def with_(self, **kw) -> "DrawStyle":
        """一部を差し替えた **新しい** スタイルを返す。"""
        return replace(self, **kw)

    def pattern(self) -> tuple[float, ...] | None:
        """``line_style`` を画素長パターンに解決する(実線は ``None``)。"""
        return resolve_pattern(self.line_style)

    def stroke_color(self):
        """線・輪郭の色を数値に解決する。"""
        return resolve_color(self.color, self.scheme)

    def interior_color(self):
        """塗り色を数値に解決する(``fill_color`` 未指定なら線色と同じ)。"""
        src = self.color if self.fill_color is None else self.fill_color
        return resolve_color(src, self.scheme)


_CURRENT: contextvars.ContextVar = contextvars.ContextVar("fullseye_draw_style", default=None)


def current_style() -> DrawStyle | None:
    """いま有効な :func:`draw_style` ブロックのスタイル(無ければ ``None``)。

    ``None`` は「既定に戻す」ではなく「**周囲に状態が無い**」という意味。``draw_*``
    は ``None`` のとき従来どおりの引数既定(白・幅 1・実線)で描く。
    """
    return _CURRENT.get()


@contextmanager
def draw_style(style: "DrawStyle | None" = None, **kw):
    """``with`` ブロックの中だけ ``draw_*`` の既定スタイルを差し替える。

    ``draw_style(color="wrong", line_style="dashed")`` のようにキーワードで作るか、
    出来合いの :class:`DrawStyle` を渡す。ネストすると内側が勝ち、抜けると
    **例外経路でも** 外側へ戻る(:class:`contextvars.ContextVar` のトークン復帰)。

    スレッド/タスクごとに独立なので、生成器を並行に走らせても互いのスタイルは
    混ざらない。モジュールグローバルの既定は書き換わらないため、``with`` の外の
    描画は常に従来どおり ―― これが「図をまたいで状態が漏れない」根拠。

    Raises ValueError: ``style`` と ``**kw`` を同時に渡した場合、または値が不正な場合。
    """
    if style is not None and kw:
        raise ValueError("pass either a DrawStyle or keyword fields, not both")
    st = style if style is not None else DrawStyle(**kw)
    if not isinstance(st, DrawStyle):
        raise ValueError(f"style must be a DrawStyle, got {type(st).__name__}")
    token = _CURRENT.set(st)
    try:
        yield st
    finally:
        _CURRENT.reset(token)


# --- HALCON 相互運用の別名 -------------------------------------------------
# 向こうに実在する演算子名を借りているだけで、意味は「装置の状態を書き換える」では
# なく「新しいスタイル値を作る」。第 1 引数に None を渡すと既定から作り始める。

def set_color(style: "DrawStyle | None", color) -> DrawStyle:
    """HALCON ``set_color`` 相当。色を差し替えた新しいスタイルを返す。"""
    return (style or DrawStyle()).with_(color=color)


def set_line_width(style: "DrawStyle | None", width) -> DrawStyle:
    """HALCON ``set_line_width`` 相当。線幅を差し替えた新しいスタイルを返す。"""
    return (style or DrawStyle()).with_(width=width)


def set_line_style(style: "DrawStyle | None", line_style) -> DrawStyle:
    """HALCON ``set_line_style`` 相当。線種(名前か ``[on,off,...]``)を差し替える。"""
    return (style or DrawStyle()).with_(line_style=line_style)


def set_draw(style: "DrawStyle | None", draw: str) -> DrawStyle:
    """HALCON ``set_draw`` 相当。``"margin"`` / ``"fill"`` を差し替える。"""
    return (style or DrawStyle()).with_(draw=draw)
