# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ocrclassic —— 限定字種の古典 OCR(学習なし・深層学習なし)。
ocrclassic -- classical OCR for a limited character set (no deep learning).

対象は工業の印字検査: ロット番号・日付コード・品番。字種は ``0-9 A-Z - . / :`` の 40 字。
印字方式は 2 つを内蔵書体で再現する(システムフォントに依存しない —— CI の Linux と
Windows で書体ファイルが違うため):

* ``"dot5x7"`` —— コンティニュアス・インクジェット(CIJ)の 5x7 ドットマトリクス。
  各ドットは円板で、直径はピッチ比 ``dot_diameter``、にじみ(ドットゲイン)を ``ink_gain`` で与える。
  画素の被覆率は超標本化(supersampling)で面積積分する。
* ``"stroke"`` —— 熱転写・レーザーの単線書体。4x6 の設計格子上の折れ線を、線分までの距離が
  ``stroke_width/2`` 未満の点として描く(超標本化で反エイリアス)。

Targets: industrial lot / date / part-number inspection, charset ``0-9 A-Z - . / :``.
Both fonts are defined inside this module (no system fonts).

認識の方式 / Recognition
------------------------
1. 切り出し: 大津で地とインクの代表値を出し、インク量の地図(1 = インク)を作る。字の画素 =
   インク量 >= 0.5。ドット書体は列射影に 1-D closing(ドットピッチ 0.6 倍)をかけて 1 字の
   ドットをまとめ、列射影の切れ目で区間化し、想定送り幅で断片の併合・接触字の分割を行う。
   読み取り時は、接触字の区間を**認識による切り出し**(列射影の極小を候補とする動的計画法、
   各区片の最近傍距離の和 + 等幅の事前を最小化)で切り直す。**等幅(固定ピッチ)印字を前提**とする。
2. 特徴量(Trier, Jain & Taxt, "Feature extraction methods for character recognition —
   a survey", Pattern Recognition 29(4):641, 1996 の古典): 行の高さで大きさ正規化(縦横比保持)した
   字の **区画濃度(zoning)8x8** + **水平・垂直射影 12+12** = 88 次元。切り出しの窓は
   インク重心を中心に送り幅 1 つぶん(隣字のにじみの入り方を学習と読みでそろえるため)。
3. k 最近傍(Cover & Hart, "Nearest neighbor pattern classification",
   IEEE Trans. Inf. Theory 13(1):21, 1967)。距離は各次元をクラス内標準偏差で割った
   対角マハラノビス距離。1 行のぼけは共通なので、**行全体で最もよく合う学習のぼけの帯**を選び、
   その帯の型とだけ照合する(ぼけた別字の型が鮮明な字になりすますのを防ぐ)。
4. **棄却**: 最近傍距離が判定字ごとの ``reject_distance`` を超えるか、距離比(他クラス最近傍 /
   判定クラス最近傍)が ``MIN_MARGIN_RATIO`` 未満ならラベルを ``"?"`` にする。
   ``reject_distance`` は**学習分布から導く**(``ocr_train`` 参照)。検査では**誤読は棄却より
   はるかに危険**なので、``ocr_score`` は両者を決して 1 つの率に畳まない。

既知の限界 / Known limits (measured, see tests)
   学習のぼけ格子(σ <= 0.14 x 字高)を超えるぼけでは、棄却で拾い切れない誤読が出る
   (試験の実測: σ = 0.15h で誤読 3〜4 %、σ = 0.2h で 11〜15 %、雑音 0.05)。ぼけた型どうしの
   距離は小さいため、距離による棄却は学習範囲の外のぼけを検出できない。運用では印字品質(ぼけ)を
   別に監視すること。
   Beyond the training blur range (sigma > 0.14 h) rejection does not catch all misreads
   (measured: 3-4 % misreads at 0.15 h, 11-15 % at 0.2 h, noise 0.05); monitor print sharpness
   separately.

依存 / Dependencies
-------------------
numpy + scipy のみ(Fullseye の core 制約)。``glyphops.normalise_glyph`` は再利用しない:
glyphops は import 時に ``annotate``(→ imagedraw, palette)を読み、normalise_glyph 自体も
Pillow で縮小するため。ここでは scipy.ndimage.map_coordinates で同じ「縦横比保持の正規化」を
小さく書き直した(重心で横位置を決める点が違う —— 下記)。
numpy + scipy only. ``glyphops.normalise_glyph`` is not reused because glyphops imports
``annotate`` at module level and normalise_glyph resizes with Pillow; the aspect-preserving
normalisation is reimplemented here with ``scipy.ndimage.map_coordinates``.

紛らわしい対の設計 / Confusable pairs (design choices)
------------------------------------------------------
* ``0`` は**斜線入り**(dot5x7: 内部に斜めの 3 ドット、stroke: 幅を詰めた楕円 + 対角の斜線)。
  ``O`` は斜線なしで幅いっぱい、``D`` は左辺が直線で角が 2 つ。
* ``1`` は旗(左上へのはね)と幅広の台座、``I`` は上下の横棒(セリフ)。
* ``5`` は平らな上辺と左の縦画、``S`` は上下とも曲線。
* ``8`` は左辺が丸い(くびれあり、stroke は上の輪を細く)、``B`` は左辺が直線。
* ``2`` は上が曲線、``Z`` は上辺が平らな直線。
* 句読点 ``.`` ``:`` の点は大きく(dot5x7: 2x2 ドット、stroke: 小さな正方形の輪郭)。
  単独の 1 ドット / 線幅の丸点は、ぼけ 0.1 x 字高で山が 2 割未満に落ちて消えるため。

既定の単一行仕様 / Scope
------------------------
単一行(1 行)の読み取り。暗いインクを明るい地に想定し、地が暗い場合は縁の中央値で極性を反転する。
空白文字は字種に含まない(等幅の工業印字で空白を読む必要がある場合は呼ぶ側で分割)。
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage

__all__ = [
    "CHARSET", "FONT_NAMES", "FEATURE_GRID", "FEATURE_LENGTH", "REJECT_FACTOR",
    "MIN_MARGIN_RATIO", "ocr_font", "ocr_render_text", "ocr_segment_line",
    "ocr_features", "ocr_train", "ocr_classify", "ocr_read_line", "ocr_score",
]

#: 字種(40 字)。/ The supported character set (40 characters).
CHARSET: str = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-./:"

#: 内蔵書体の名前。/ Built-in font names.
FONT_NAMES: tuple = ("dot5x7", "stroke")

#: 正規化キャンバスの一辺(画素)。/ Side of the normalised canvas (px).
FEATURE_GRID: int = 24
_ZONES: int = 8          # 8x8 区画 / zones
_PROJ_BINS: int = 12     # 射影のビン数 / projection bins
#: 特徴量の長さ = 8*8 区画濃度 + 12 水平射影 + 12 垂直射影 = 88。
#: Feature length = 64 zoning + 12 horizontal projection + 12 vertical projection = 88.
FEATURE_LENGTH: int = _ZONES * _ZONES + 2 * _PROJ_BINS

#: 棄却距離の係数。字ごとに「同クラス・同じぼけ帯の中の最近傍他試料までの(重みつき)距離」の
#: 99 パーセンタイルを取り、これを掛けたものを棄却距離にする(``ocr_train`` の ``reject_distance_by_class``)。
#: 1.5 は「学習試料どうしの隙間の 1.5 倍より遠い入力は、学習した字のどれでもない」とする値。
#: ★正直な開示: 係数 {1.0, 1.25, 1.5, 2.0, 2.5} と下の距離比 {1.05, 1.10, 1.15, 1.20} は、
#: 試験とは別の乱数種(1000, 2000, 11)の開発用掃引で比べて選んだ(試験の乱数種では選んでいない)。
#: (当時の実装で)2.5 では字種外の '#' が単線書体で 30 回中 30 回誤読され、1.5 で 0〜3 回になった。
#: その後、行端の推定を中身に依らない規則にして型の外れ値を除いた結果、係数への依存は小さくなった
#: (現行の試験では '#' と乱数の塊はどちらも 40/40 棄却)。
#: Reject factor applied to the per-blur-level 99th percentile of the within-class, within-band
#: nearest-other-sample (weighted) distance. Honest disclosure: chosen among {1.0..2.5} with a
#: development sweep on seeds disjoint from the test seeds (2.5 let '#' through in 30/30 cases
#: for the stroke font in the implementation of that time; after the content-independent
#: line-edge rule removed template outliers, the result depends little on the factor).
REJECT_FACTOR: float = 1.5

#: 距離比(他クラス最近傍 / 判定クラス最近傍)の下限。これ未満は 2 クラスの境界上なので棄却する。
#: 1.10 = 「他クラスより 10 % 以上近い」。開発用掃引で 1.05 はきれいな印字でも誤読が出た
#: (0.1 %)ので採らず、1.10 は誤読 0 のまま 1.15 より棄却が少なかった。
#: Minimum margin ratio (nearest other-class / nearest own-class distance). 1.05 produced
#: misreads even on clean prints in the development sweep; 1.10 kept them at 0 with fewer
#: rejects than 1.15.
MIN_MARGIN_RATIO: float = 1.10

#: 認識による切り出し(動的計画法)の、区片幅の等幅事前の重み。/ fixed-pitch prior weight in the DP.
_DP_WIDTH_PENALTY: float = 1.0

# 両書体の送り幅 / 字幅(字高に対する比)の既定。dot5x7: 送り 6p, 字幅 (4+d)p, 字高 (6+d)p。
# stroke: 送り 6u, 字幅 4u+sw, 字高 6u+sw(u=(h-sw)/6)。既定値ではどちらも ~0.88h / ~0.71h。
# Default advance / glyph width as a fraction of cap height (both fonts ~0.88 h / ~0.71 h).
_ADV_RATIO: float = 0.88
_WIDTH_RATIO: float = 0.71

# --------------------------------------------------------------------------- #
# 書体の設計 / Font designs                                                     #
# --------------------------------------------------------------------------- #

# 5x7 ドット(行 0 が上)。'#' がドット。自前設計。/ Own 5x7 designs, '#' = dot, row 0 = top.
_DOT5X7_ROWS: dict = {
    "0": [" ### ", "#   #", "#  ##", "# # #", "##  #", "#   #", " ### "],   # slashed zero
    "1": ["  #  ", " ##  ", "# #  ", "  #  ", "  #  ", "  #  ", "#####"],   # flag + wide base
    "2": [" ### ", "#   #", "    #", "   # ", "  #  ", " #   ", "#####"],
    "3": ["#####", "   # ", "  #  ", "   # ", "    #", "#   #", " ### "],
    "4": ["   # ", "  ## ", " # # ", "#  # ", "#####", "   # ", "   # "],
    "5": ["#####", "#    ", "#### ", "    #", "    #", "#   #", " ### "],   # flat top
    "6": ["  ## ", " #   ", "#    ", "#### ", "#   #", "#   #", " ### "],
    "7": ["#####", "    #", "   # ", "  #  ", " #   ", " #   ", " #   "],
    "8": [" ### ", "#   #", "#   #", " ### ", "#   #", "#   #", " ### "],   # round left
    "9": [" ### ", "#   #", "#   #", " ####", "    #", "   # ", " ##  "],
    "A": [" ### ", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
    "B": ["#### ", "#   #", "#   #", "#### ", "#   #", "#   #", "#### "],   # straight left
    "C": [" ### ", "#   #", "#    ", "#    ", "#    ", "#   #", " ### "],
    "D": ["###  ", "#  # ", "#   #", "#   #", "#   #", "#  # ", "###  "],   # straight left
    "E": ["#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#####"],
    "F": ["#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#    "],
    "G": [" ### ", "#   #", "#    ", "# ###", "#   #", "#   #", " ####"],
    "H": ["#   #", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
    "I": [" ### ", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", " ### "],   # serifs
    "J": ["  ###", "   # ", "   # ", "   # ", "   # ", "#  # ", " ##  "],
    "K": ["#   #", "#  # ", "# #  ", "##   ", "# #  ", "#  # ", "#   #"],
    "L": ["#    ", "#    ", "#    ", "#    ", "#    ", "#    ", "#####"],
    "M": ["#   #", "## ##", "# # #", "# # #", "#   #", "#   #", "#   #"],
    "N": ["#   #", "#   #", "##  #", "# # #", "#  ##", "#   #", "#   #"],
    "O": [" ### ", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "],   # no slash
    "P": ["#### ", "#   #", "#   #", "#### ", "#    ", "#    ", "#    "],
    "Q": [" ### ", "#   #", "#   #", "#   #", "# # #", "#  # ", " ## #"],
    "R": ["#### ", "#   #", "#   #", "#### ", "# #  ", "#  # ", "#   #"],
    "S": [" ####", "#    ", "#    ", " ### ", "    #", "    #", "#### "],   # curved top
    "T": ["#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "  #  "],
    "U": ["#   #", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "],
    "V": ["#   #", "#   #", "#   #", "#   #", "#   #", " # # ", "  #  "],
    "W": ["#   #", "#   #", "#   #", "# # #", "# # #", "# # #", " # # "],
    "X": ["#   #", "#   #", " # # ", "  #  ", " # # ", "#   #", "#   #"],
    "Y": ["#   #", "#   #", " # # ", "  #  ", "  #  ", "  #  ", "  #  "],
    "Z": ["#####", "    #", "   # ", "  #  ", " #   ", "#    ", "#####"],   # flat top
    "-": ["     ", "     ", "     ", "#####", "     ", "     ", "     "],
    ".": ["     ", "     ", "     ", "     ", "     ", " ##  ", " ##  "],   # 2x2 dot

    "/": ["    #", "    #", "   # ", "  #  ", " #   ", "#    ", "#    "],
    ":": ["     ", " ##  ", " ##  ", "     ", "     ", " ##  ", " ##  "],   # 2x2 dots
}

# 単線書体: 4x6 設計格子(x 0..4 右へ、y 0..6 下へ)の折れ線。長さ 0 の折れ線は点(円)。
# Stroke font: polylines on a 4x6 design grid (x right 0..4, y down 0..6); a 1-point polyline
# is a round dot.
_OVAL_WIDE = [(1.5, 0), (2.5, 0), (4, 1.5), (4, 4.5), (2.5, 6), (1.5, 6), (0, 4.5), (0, 1.5),
              (1.5, 0)]


def _DOT_BLOB(x, y, r=0.4):
    """句読点の点 = 一辺 2r の小さな正方形の輪郭(太らせた点)。単線の丸点(直径 = 線幅)は
    ぼけ 0.1h で山が 16 % まで下がり消えるため、工業書体と同じく点を大きくする。
    A punctuation dot drawn as a small square outline (fattened dot): a stroke-width round dot
    drops to 16 % peak contrast at blur 0.1 h and disappears."""
    return [(x - r, y - r), (x + r, y - r), (x + r, y + r), (x - r, y + r), (x - r, y - r)]


_STROKE_POLYS: dict = {
    # 0: 幅を詰めた楕円 + 対角の斜線 / narrow oval + corner-to-corner slash
    "0": [[(1.5, 0), (2.5, 0), (3.5, 1), (3.5, 5), (2.5, 6), (1.5, 6), (0.5, 5), (0.5, 1),
           (1.5, 0)], [(3.5, 1), (0.5, 5)]],
    "1": [[(0.8, 1.2), (2, 0), (2, 6)], [(0.8, 6), (3.2, 6)]],          # flag + base
    "2": [[(0, 1), (1, 0), (3, 0), (4, 1), (4, 2), (0, 6), (4, 6)]],     # curved top
    "3": [[(0, 0), (4, 0), (2, 2.5), (3, 2.5), (4, 3.5), (4, 5), (3, 6), (1, 6), (0, 5)]],
    "4": [[(3, 6), (3, 0), (0, 4), (4, 4)]],
    "5": [[(4, 0), (0, 0), (0, 2.5), (3, 2.5), (4, 3.5), (4, 5), (3, 6), (0, 6)]],  # flat top
    "6": [[(3, 0), (1, 0), (0, 1), (0, 5), (1, 6), (3, 6), (4, 5), (4, 3.5), (3, 2.5),
           (0, 2.5)]],
    "7": [[(0, 0), (4, 0), (1.5, 6)]],
    # 8: 上の輪を細く、腰をくびらせる(左辺が直線の B と区別)/ narrow top loop, pinched waist
    "8": [[(1.2, 0), (2.8, 0), (3.6, 0.8), (3.6, 2), (2.8, 2.8), (1.2, 2.8), (0.4, 2),
           (0.4, 0.8), (1.2, 0)],
          [(1, 2.8), (3, 2.8), (4, 3.8), (4, 5), (3, 6), (1, 6), (0, 5), (0, 3.8), (1, 2.8)]],
    "9": [[(4, 3.5), (1, 3.5), (0, 2.5), (0, 1), (1, 0), (3, 0), (4, 1), (4, 5), (3, 6),
           (1, 6)]],
    "A": [[(0, 6), (0, 2), (2, 0), (4, 2), (4, 6)], [(0, 3.5), (4, 3.5)]],
    "B": [[(0, 0), (3, 0), (4, 1), (4, 2), (3, 3), (0, 3)],
          [(3, 3), (4, 4), (4, 5), (3, 6), (0, 6), (0, 0)]],                    # straight left
    "C": [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 5), (1, 6), (3, 6), (4, 5)]],
    "D": [[(0, 0), (2.5, 0), (4, 1.5), (4, 4.5), (2.5, 6), (0, 6), (0, 0)]],  # straight left
    "E": [[(4, 0), (0, 0), (0, 6), (4, 6)], [(0, 3), (3, 3)]],
    "F": [[(4, 0), (0, 0), (0, 6)], [(0, 3), (3, 3)]],
    "G": [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 5), (1, 6), (3, 6), (4, 5), (4, 3.5),
           (2, 3.5)]],
    "H": [[(0, 0), (0, 6)], [(4, 0), (4, 6)], [(0, 3), (4, 3)]],
    "I": [[(0.8, 0), (3.2, 0)], [(2, 0), (2, 6)], [(0.8, 6), (3.2, 6)]],     # serifs
    "J": [[(2, 0), (4, 0)], [(4, 0), (4, 5), (3, 6), (1, 6), (0, 5)]],
    "K": [[(0, 0), (0, 6)], [(4, 0), (0, 3.6)], [(1.4, 2.4), (4, 6)]],
    "L": [[(0, 0), (0, 6), (4, 6)]],
    "M": [[(0, 6), (0, 0), (2, 3), (4, 0), (4, 6)]],
    "N": [[(0, 6), (0, 0), (4, 6), (4, 0)]],
    "O": [_OVAL_WIDE],                                                      # wide, no slash
    "P": [[(0, 6), (0, 0), (3, 0), (4, 1), (4, 2), (3, 3), (0, 3)]],
    "Q": [_OVAL_WIDE, [(2.5, 4.5), (4, 6)]],
    "R": [[(0, 6), (0, 0), (3, 0), (4, 1), (4, 2), (3, 3), (0, 3)], [(2, 3), (4, 6)]],
    "S": [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 2), (1, 3), (3, 3), (4, 4), (4, 5), (3, 6),
           (1, 6), (0, 5)]],                                                # curved
    "T": [[(0, 0), (4, 0)], [(2, 0), (2, 6)]],
    "U": [[(0, 0), (0, 5), (1, 6), (3, 6), (4, 5), (4, 0)]],
    "V": [[(0, 0), (2, 6), (4, 0)]],
    "W": [[(0, 0), (1, 6), (2, 2.5), (3, 6), (4, 0)]],
    "X": [[(0, 0), (4, 6)], [(4, 0), (0, 6)]],
    "Y": [[(0, 0), (2, 3), (4, 0)], [(2, 3), (2, 6)]],
    "Z": [[(0, 0), (4, 0), (0, 6), (4, 6)]],                                # flat top
    "-": [[(0.8, 3), (3.2, 3)]],
    ".": [_DOT_BLOB(2, 5.6)],
    "/": [[(0.5, 6), (3.5, 0)]],
    ":": [_DOT_BLOB(2, 1.6), _DOT_BLOB(2, 5.6)],
}


def _dot_bitmap(rows) -> np.ndarray:
    return np.array([[1 if c == "#" else 0 for c in r] for r in rows], np.uint8)


def ocr_font(name: str = "dot5x7") -> dict:
    """内蔵書体(5x7 ドット / 線)の字種と字形の設計を返す(``table``)。

    Parameters
    ----------
    name : ``"dot5x7"`` か ``"stroke"``。

    Returns
    -------
    dict
        ``name``, ``charset`` (str), ``glyphs`` (char -> design: dot5x7 は (7,5) uint8 のビットマップ、
        stroke は折れ線のリスト ``[[(x, y), ...], ...]``), ``kind`` (``"dot"``/``"stroke"``),
        ``grid`` (設計格子の (行, 列) または (高さ, 幅)), ``advance`` (設計単位の送り幅:
        dot5x7 = 6 ドットピッチ、stroke = 6 格子単位)。
        返す辞書は毎回新しい複製なので、呼ぶ側が字を足して ``ocr_render_text(font=<dict>)`` に
        渡してよい(字種外の試験字を作る用途)。

    Raises
    ------
    ValueError
        未知の書体名。
    """
    if not isinstance(name, str) or name not in FONT_NAMES:
        raise ValueError(f"unknown font {name!r}; expected one of {FONT_NAMES}")
    if name == "dot5x7":
        glyphs = {c: _dot_bitmap(_DOT5X7_ROWS[c]) for c in CHARSET}
        return {"name": name, "kind": "dot", "charset": CHARSET, "glyphs": glyphs,
                "grid": (7, 5), "advance": 6}
    glyphs = {c: [list(map(tuple, p)) for p in _STROKE_POLYS[c]] for c in CHARSET}
    return {"name": name, "kind": "stroke", "charset": CHARSET, "glyphs": glyphs,
            "grid": (6, 4), "advance": 6}


class _Validated:
    """検証済みの書体辞書の包み(学習の内側で毎回の再検証を省く)。/ Already-validated font."""

    __slots__ = ("font",)

    def __init__(self, font: dict):
        self.font = font


def _resolve_font(font) -> dict:
    """書体名か書体辞書を検証して辞書にする。/ Validate a font name or font dict."""
    if isinstance(font, _Validated):
        return font.font
    if isinstance(font, str):
        return ocr_font(font)
    if not isinstance(font, dict):
        raise ValueError("font must be a font name or a dict returned by ocr_font")
    for key in ("kind", "charset", "glyphs"):
        if key not in font:
            raise ValueError(f"font dict is missing key {key!r}")
    if font["kind"] not in ("dot", "stroke"):
        raise ValueError(f"font kind must be 'dot' or 'stroke', got {font['kind']!r}")
    if not isinstance(font["charset"], str) or not font["charset"]:
        raise ValueError("font charset must be a non-empty string")
    for c in font["charset"]:
        if c not in font["glyphs"]:
            raise ValueError(f"font has no glyph for charset member {c!r}")
        g = font["glyphs"][c]
        if font["kind"] == "dot":
            a = np.asarray(g)
            if a.shape != (7, 5):
                raise ValueError(f"dot glyph {c!r} must have shape (7, 5), got {a.shape}")
        else:
            if not isinstance(g, (list, tuple)) or not g:
                raise ValueError(f"stroke glyph {c!r} must be a non-empty list of polylines")
            for poly in g:
                pts = np.asarray(poly, float)
                if pts.ndim != 2 or pts.shape[1] != 2 or len(pts) < 1 \
                        or not np.isfinite(pts).all():
                    raise ValueError(f"stroke glyph {c!r} has an invalid polyline")
    return font


# --------------------------------------------------------------------------- #
# 描画 / Rendering                                                             #
# --------------------------------------------------------------------------- #

def _check_number(name, v, lo=None, hi=None, lo_open=False):
    if isinstance(v, bool) or not isinstance(v, (int, float, np.integer, np.floating)):
        raise ValueError(f"{name} must be a number, got {type(v).__name__}")
    v = float(v)
    if not math.isfinite(v):
        raise ValueError(f"{name} must be finite, got {v}")
    if lo is not None and (v <= lo if lo_open else v < lo):
        raise ValueError(f"{name} must be {'>' if lo_open else '>='} {lo}, got {v}")
    if hi is not None and v > hi:
        raise ValueError(f"{name} must be <= {hi}, got {v}")
    return v


def _glyph_capsules(design, kind, left, top, h, dot_diameter, ink_gain, stroke_width):
    """1 字を「カプセル(線分 + 半径)」の列に直す(ドット = 長さ 0 のカプセル)。

    Convert one glyph into capsules (segment + radius); a dot is a zero-length capsule.
    Returns an array (m, 5): x0, y0, x1, y1, r (pixel coordinates, pixel centres at +0.5).
    """
    caps = []
    if kind == "dot":
        p = h / (6.0 + dot_diameter)                  # ドットピッチ / dot pitch
        r = 0.5 * dot_diameter * (1.0 + ink_gain) * p
        off = 0.5 * dot_diameter * p
        bm = np.asarray(design)
        for i, j in zip(*np.nonzero(bm)):
            x = left + off + j * p
            y = top + off + i * p
            caps.append((x, y, x, y, r))
    else:
        sw = stroke_width * h
        u = (h - sw) / 6.0
        r = 0.5 * sw * (1.0 + ink_gain)
        for poly in design:
            pts = [(left + 0.5 * sw + gx * u, top + 0.5 * sw + gy * u) for gx, gy in poly]
            if len(pts) == 1:
                caps.append((pts[0][0], pts[0][1], pts[0][0], pts[0][1], r))
            for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
                caps.append((x0, y0, x1, y1, r))
    return np.asarray(caps, float).reshape(-1, 5)


def _capsule_coverage(caps, ss):
    """カプセル群の被覆率を、画素格子にそろえた窓の中で超標本化して求める。

    Area-integrated coverage of a union of capsules by ss x ss supersampling.
    Returns (coverage (hh, ww) float, row0, col0) of a pixel-aligned window.
    """
    xmin = float(np.min(np.minimum(caps[:, 0], caps[:, 2]) - caps[:, 4]))
    xmax = float(np.max(np.maximum(caps[:, 0], caps[:, 2]) + caps[:, 4]))
    ymin = float(np.min(np.minimum(caps[:, 1], caps[:, 3]) - caps[:, 4]))
    ymax = float(np.max(np.maximum(caps[:, 1], caps[:, 3]) + caps[:, 4]))
    c0, c1 = int(math.floor(xmin)) - 1, int(math.ceil(xmax)) + 1
    r0, r1 = int(math.floor(ymin)) - 1, int(math.ceil(ymax)) + 1
    hh, ww = r1 - r0, c1 - c0
    ys = r0 + (np.arange(hh * ss) + 0.5) / ss
    xs = c0 + (np.arange(ww * ss) + 0.5) / ss
    mask = np.zeros((hh * ss, ww * ss), bool)
    for x0, y0, x1, y1, rad in caps:
        # カプセル自身の外接窓だけを計算する(速度のため)/ only the capsule's own window
        ia = max(0, int(math.floor((min(y0, y1) - rad - r0) * ss)))
        ib = min(hh * ss, int(math.ceil((max(y0, y1) + rad - r0) * ss)) + 1)
        ja = max(0, int(math.floor((min(x0, x1) - rad - c0) * ss)))
        jb = min(ww * ss, int(math.ceil((max(x0, x1) + rad - c0) * ss)) + 1)
        if ia >= ib or ja >= jb:
            continue
        yy = ys[ia:ib, None]
        xx = xs[None, ja:jb]
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy
        if L2 <= 1e-12:
            d2 = (xx - x0) ** 2 + (yy - y0) ** 2
        else:
            t = np.clip(((xx - x0) * dx + (yy - y0) * dy) / L2, 0.0, 1.0)
            d2 = (xx - (x0 + t * dx)) ** 2 + (yy - (y0 + t * dy)) ** 2
        mask[ia:ib, ja:jb] |= d2 < rad * rad
    cov = mask.reshape(hh, ss, ww, ss).mean(axis=(1, 3))
    return cov, r0, c0


def ocr_render_text(text, font="dot5x7", char_height_px=24, pitch=None, dot_diameter=0.8,
                    ink_gain=0.0, contrast=0.8, background=0.9, supersample=4,
                    stroke_width=0.12, subpixel_offset=(0.0, 0.0)) -> dict:
    """文字列を内蔵書体で描き、字ごとの真値の外接箱と一緒に返す(``table``)。

    Parameters
    ----------
    text : str
        字種内の字だけ(大文字)。空文字・字種外は ValueError。
    font : 書体名 (``"dot5x7"``/``"stroke"``) か ``ocr_font`` の辞書(字を足したもの可)。
    char_height_px : 字高(画素)= 全高の字のインクの縦の広がり。>= 6。
    pitch : 字の送り幅(画素)。None なら書体の既定(~0.88 x 字高)。
    dot_diameter : ドット直径 / ドットピッチ(dot5x7 のみ)。(0, 1.5]。
    ink_gain : にじみ。ドット直径・線幅に ``(1 + ink_gain)`` を掛ける。(-0.9, 2]。
    contrast, background : 地の明るさ ``background``、インクの明るさ ``background - contrast``。
    supersample : 1 画素あたりの超標本数(一辺)。1..16。
    stroke_width : 線幅 / 字高(stroke のみ)。(0, 0.4]。
    subpixel_offset : (dy, dx) 画素。字列全体を小数画素ずらす(学習の撹乱用)。

    Returns
    -------
    dict
        ``image`` 2-D float [0, 1](明るい地に暗いインク), ``boxes`` 字ごとの真値の外接箱
        ``(r0, c0, r1, c1)``(終端は含まない、被覆率 >= 0.5 の画素の外接箱), ``text``,
        ``line_box``(字高の行範囲 x 全幅), ``pitch_px``, ``cells``(各字の設計上の字幅の列範囲
        ``(左, 右)``、小数画素)。周囲に約 1 字高の余白。
    """
    if not isinstance(text, str) or not text:
        raise ValueError("text must be a non-empty string")
    f = _resolve_font(font)
    for c in text:
        if c not in f["charset"]:
            raise ValueError(f"character {c!r} is not in the font charset")
    h = _check_number("char_height_px", char_height_px, lo=6, hi=1024)
    dd = _check_number("dot_diameter", dot_diameter, lo=0.0, hi=1.5, lo_open=True)
    g = _check_number("ink_gain", ink_gain, lo=-0.9, hi=2.0, lo_open=True)
    con = _check_number("contrast", contrast, lo=0.0, hi=1.0, lo_open=True)
    bg = _check_number("background", background, lo=0.0, hi=1.0)
    if bg - con < -1e-12:
        raise ValueError("background - contrast must be >= 0")
    sw = _check_number("stroke_width", stroke_width, lo=0.0, hi=0.4, lo_open=True)
    if isinstance(supersample, bool) or not isinstance(supersample, (int, np.integer)) \
            or not 1 <= int(supersample) <= 16:
        raise ValueError("supersample must be an integer in 1..16")
    ss = int(supersample)
    try:
        dy, dx = (float(subpixel_offset[0]), float(subpixel_offset[1]))
    except (TypeError, IndexError, ValueError) as exc:
        raise ValueError("subpixel_offset must be a pair of numbers") from exc
    if not (math.isfinite(dy) and math.isfinite(dx)) or abs(dy) > 4 or abs(dx) > 4:
        raise ValueError("subpixel_offset must be finite and within +/-4 px")
    if f["kind"] == "dot":
        p = h / (6.0 + dd)
        adv_default, width = 6.0 * p, (4.0 + dd) * p
    else:
        u = (h - sw * h) / 6.0
        adv_default, width = 6.0 * u, 4.0 * u + sw * h
    adv = adv_default if pitch is None else _check_number("pitch", pitch, lo=0.0, lo_open=True)
    m = h                                             # 余白 = 1 字高 / margin = 1 char height
    H = int(math.ceil(2 * m + h))
    W = int(math.ceil(2 * m + (len(text) - 1) * adv + width))
    cov = np.zeros((H, W), float)
    boxes, cells = [], []
    top = m + dy
    for i, c in enumerate(text):
        left = m + dx + i * adv
        cells.append((float(left), float(left + width)))
        caps = _glyph_capsules(f["glyphs"][c], f["kind"], left, top, h, dd, g, sw)
        if len(caps) == 0:
            raise ValueError(f"glyph {c!r} has no ink")
        cv, r0, c0 = _capsule_coverage(caps, ss)
        # キャンバスに合わせて切り詰める / clip window to canvas
        ra, rb = max(r0, 0), min(r0 + cv.shape[0], H)
        ca, cb = max(c0, 0), min(c0 + cv.shape[1], W)
        sub = cv[ra - r0:rb - r0, ca - c0:cb - c0]
        cov[ra:rb, ca:cb] = np.maximum(cov[ra:rb, ca:cb], sub)
        on = sub >= 0.5
        if not on.any():                              # 極小の字: 最大被覆の画素 / tiny glyph
            on = sub >= sub.max()
        rr, cc = np.nonzero(on)
        boxes.append((int(ra + rr.min()), int(ca + cc.min()),
                      int(ra + rr.max() + 1), int(ca + cc.max() + 1)))
    image = np.clip(bg - con * cov, 0.0, 1.0)
    line_box = (int(math.floor(top)), 0, int(math.ceil(top + h)), W)
    return {"image": image, "boxes": boxes, "text": text, "line_box": line_box,
            "pitch_px": float(adv), "cells": cells}


# --------------------------------------------------------------------------- #
# 二値化と切り出し / Binarisation and segmentation                             #
# --------------------------------------------------------------------------- #

def _check_image(image) -> np.ndarray:
    a = np.asarray(image)
    if a.dtype == object or not (np.issubdtype(a.dtype, np.number) or a.dtype == bool):
        raise ValueError("image must be a numeric array")
    if a.ndim != 2:
        raise ValueError(f"image must be 2-D (grey), got ndim={a.ndim}")
    if a.shape[0] < 4 or a.shape[1] < 4:
        raise ValueError(f"image is too small: {a.shape}")
    a = a.astype(np.float64)
    if not np.isfinite(a).all():
        raise ValueError("image contains NaN or inf")
    if np.issubdtype(np.asarray(image).dtype, np.integer) and a.max() > 1.0:
        a = a / 255.0
    return a


def _otsu(values: np.ndarray, nbins: int = 256) -> float:
    lo, hi = float(values.min()), float(values.max())
    if hi - lo < 1e-12:
        return lo
    hist, edges = np.histogram(values, bins=nbins, range=(lo, hi))
    hist = hist.astype(float)
    mids = 0.5 * (edges[:-1] + edges[1:])
    w0 = np.cumsum(hist)
    w1 = w0[-1] - w0
    m0 = np.cumsum(hist * mids)
    mt = m0[-1]
    with np.errstate(divide="ignore", invalid="ignore"):
        mu0 = m0 / w0
        mu1 = (mt - m0) / w1
        between = w0 * w1 * (mu0 - mu1) ** 2
    between[~np.isfinite(between)] = -1
    k = int(np.argmax(between))
    return float(edges[k + 1])


#: 雑音があるときの前置平滑 σ(画素)と、その σ で白色雑音の標準偏差が縮む比 1/(2 sqrt(pi) σ)。
#: Pre-smoothing sigma (px) under noise, and the white-noise std gain 1/(2 sqrt(pi) sigma).
_PRESMOOTH: float = 0.7


def _noise_sigma(g: np.ndarray) -> float:
    """横差分の MAD から加法雑音の標準偏差を推定(地が大半なので頑健)。

    Robust additive-noise sigma from the MAD of horizontal differences.
    """
    d = np.diff(g, axis=1).ravel()
    mad = float(np.median(np.abs(d - np.median(d))))
    return 1.4826 * mad / math.sqrt(2.0)


def _ink_map(g: np.ndarray):
    """大津で二値化し、インク量の地図(1 = インク、0 = 地)を作る。

    地の代表値 = 大津の明るい側の中央値、インクの代表値 = 暗い側の **10 パーセンタイル**(最も濃い部分)。
    暗い側の中央値を使うと、ぼけた画像では暗い側に暈が混ざって代表値が薄くなり、インク量が
    水増しされて字の画素(>= 0.5)が太り、字高が 2 割過大になった(実測: ドット書体、ぼけ 0.1h)。
    Background = median of the bright Otsu class; ink level = 10th percentile of the dark class
    (its darkest part). The dark-class median let the blur halo dilute the ink level, inflating the
    ink map and the char height by ~20 % (measured, dot font, blur 0.1 h).
    雑音が有意(横差分 MAD の σ > 0.01)なら σ=0.7 px の Gaussian で前置平滑してから大津をかける
    (地の雑音分布をインクと誤って二分する大津の失敗を防ぐ。実測: 字高 24 px・ぼけ 0.1h・雑音 0.05 で
    平滑なしの大津は地の雑音を二分し、白紙判定に落ちた)。
    If noise is significant (sigma > 0.01) the image is pre-smoothed (Gaussian 0.7 px) before
    Otsu; without it Otsu splits the background noise when ink contrast is low.
    Returns (binary, ink, threshold, ok). ``ok`` False = no ink (blank image).
    """
    sig = _noise_sigma(g)
    if sig > 0.01:
        gs = ndimage.gaussian_filter(g, _PRESMOOTH, mode="nearest")
        sig_s = sig / (2.0 * math.sqrt(math.pi) * _PRESMOOTH)
    else:
        gs, sig_s = g, sig
    t = _otsu(gs)
    border = np.concatenate([gs[0], gs[-1], gs[:, 0], gs[:, -1]])
    dark_ink = float(np.median(border)) >= t
    B = (gs < t) if dark_ink else (gs > t)
    if not B.any() or B.all():
        return B & False, np.zeros_like(g), t, False
    bg = float(np.median(gs[~B]))
    fg = float(np.percentile(gs[B], 10)) if dark_ink else float(np.percentile(gs[B], 90))
    sep = abs(bg - fg)
    # インクと地の分離が雑音の 4σ 未満なら「インク無し」(白紙は fail-soft で空を返す)。
    # separation below 4 sigma of noise => blank (fail-soft: empty result).
    if sep < max(0.03, 4.0 * sig_s):
        return B & False, np.zeros_like(g), t, False
    ink = np.clip((bg - gs) / (bg - fg), 0.0, 1.0)
    return B, ink, t, True


def _empty_seg(t, shape):
    return {"boxes": [], "threshold": float(t), "line_box": None, "char_height_px": None,
            "pitch_px": None, "dot_font": None, "_ink": np.zeros(shape), "_binary": None}


def _cut_profile(colsum, adv):
    """切れ目探しに使う列射影(σ = 0.05 x 送り幅で平滑)。/ Column profile for cut search."""
    return ndimage.gaussian_filter1d(np.asarray(colsum, float), 0.05 * float(adv),
                                     mode="nearest")


def _profile_minima(prof):
    """列射影の極小(平らな谷はその中央)。/ Local minima of a profile (centre of flat valleys).

    平らな谷の端を取ると、谷の幅が字間より広いとき、字の中の浅い極小のほうが「近い」ことがある
    (実測: きれいな学習試料で '4' の縦画の脇を切り、同じ字の型の 1 % が他字並みに外れた)。
    Taking the end of a flat valley let a shallow minimum inside a glyph look "nearer" (measured:
    1 % of clean '4' templates were cut beside the stem and became outliers).
    """
    out = []
    n = len(prof)
    q = 1
    while q < n - 1:
        if prof[q] < prof[q - 1]:
            e = q
            while e + 1 < n and prof[e + 1] == prof[q]:
                e += 1
            if e + 1 < n and prof[e + 1] > prof[q]:
                out.append((q + e) // 2)
            q = e + 1
        else:
            q += 1
    return out


def _cut_near(prof, x, adv):
    """位置 x の ±0.3 送り幅以内で**最も深い**極小(同じ深さなら x に近い方)。無ければ x。

    The deepest minimum within +/-0.3 pitch of x (ties: nearest to x); x itself if none.
    """
    lo, hi = x - 0.3 * adv, x + 0.3 * adv
    q = [m for m in _profile_minima(prof) if lo <= m <= hi]
    if not q:
        return int(round(x))
    return int(min(q, key=lambda m: (round(float(prof[m]), 9), abs(m - x), m)))


def _line_rows(ink, boxes):
    """行の上端・下端(小数)= 背の高い字(箱の高さが最大の 0.75 倍以上)の上端・下端の中央値。

    各字の縁は、その字の列でのインク量の最大(列方向の max)が 0.5 を横切る位置を、画素中心の
    間で線形補間して小数で出す。行和(行射影)で決めると中身に引きずられる —— 実測: 学習の
    ``"-4W"`` で ``-`` の横画が行和の基準を押し上げ、行が上下 7 px ずつ削られて型が外れ値になった。
    Line top / bottom (fractional) = median top / bottom of the tall glyphs (box height >= 0.75 x
    max). Each edge is the sub-pixel 0.5 crossing of the per-row max ink over the glyph's columns.
    A row-sum (projection) rule is content-dependent: in the training line ``"-4W"`` the bar of
    ``-`` raised the reference and cut 7 px off both ends, making the template an outlier.
    """
    hmax = max(b[2] - b[0] for b in boxes)
    tops, bots = [], []
    H = ink.shape[0]
    for br0, bc0, br1, bc1 in boxes:
        if br1 - br0 < 0.75 * hmax:
            continue
        v = ink[:, bc0:bc1].max(axis=1)
        rt, rl = br0, br1 - 1
        v0 = float(v[rt - 1]) if rt > 0 else 0.0
        v1 = float(v[rt])
        top = (rt - 0.5) + (0.5 - v0) / (v1 - v0) if v1 > v0 else float(rt)
        w1 = float(v[rl])
        w2 = float(v[rl + 1]) if rl + 1 < H else 0.0
        bot = (rl + 0.5) + (w1 - 0.5) / (w1 - w2) if w1 > w2 else float(rl + 1)
        tops.append(min(max(top, rt - 0.5), rt + 0.5))
        bots.append(min(max(bot, rl + 0.5), rl + 1.5))
    return float(np.median(tops)), float(np.median(bots))


def _tight_box(B, rows, s, e):
    """列 [s, e) の中の字の画素の外接箱(無ければ None)。/ Tight box of glyph pixels in [s, e)."""
    ra, rb = rows
    s, e = max(0, int(s)), min(B.shape[1], int(e))
    if e <= s:
        return None
    sub = B[ra:rb, s:e]
    if not sub.any():
        return None
    rr = np.nonzero(sub.any(axis=1))[0]
    cc = np.nonzero(sub.any(axis=0))[0]
    return (ra + int(rr.min()), s + int(cc.min()), ra + int(rr.max() + 1), s + int(cc.max() + 1))


def _segment(image, char_height_px=None, dot_font=None) -> dict:
    g = _check_image(image)
    if char_height_px is not None:
        char_height_px = _check_number("char_height_px", char_height_px, lo=4, hi=4096)
    if dot_font is not None and not isinstance(dot_font, (bool, np.bool_)):
        raise ValueError("dot_font must be None, True or False")
    _, ink, t, ok = _ink_map(g)
    if not ok:
        return _empty_seg(t, g.shape)
    # 字の画素 = インク量が半分以上(地とインクの代表値の中点)。きれいな画像では真値の箱の基準
    # (被覆率 >= 0.5)と一致し、ぼけた画像では大津より外側の暈を拾わない。
    # glyph pixels = ink >= 0.5 (midpoint of background and ink levels): equals the truth-box rule
    # (coverage >= 0.5) on clean images and ignores the blur halo that Otsu would include.
    B = ink >= 0.5
    if not B.any():
        return _empty_seg(t, g.shape)
    rows = np.nonzero(B.any(axis=1))[0]
    if char_height_px is not None:
        h = float(char_height_px)
    else:
        h = float(rows.max() - rows.min() + 1)
    p_dot = h / 6.8                                    # 既定 d=0.8 のドットピッチ / dot pitch
    # 雑音の点を除く(ドット 1 個の 1/4 未満の面積)/ remove specks < 1/4 of one dot area
    lab, n = ndimage.label(B, structure=np.ones((3, 3)))
    areas = np.bincount(lab.ravel(), minlength=n + 1)
    min_area = max(1, int(round(0.25 * math.pi / 4 * (0.8 * p_dot) ** 2)))
    keep = areas >= min_area
    keep[0] = False
    B = keep[lab]
    if not B.any():
        return _empty_seg(t, g.shape)
    rows = np.nonzero(B.any(axis=1))[0]
    cols_all = np.nonzero(B.any(axis=0))[0]
    ra, rb = int(rows.min()), int(rows.max() + 1)
    ca, cb = int(cols_all.min()), int(cols_all.max() + 1)
    # 仮の行範囲 = 字の画素の縦の広がり(送り幅・closing の寸法用)。確定値は字を切った後に
    # 「背の高い字の上端・下端の中央値」で出し直す(下記)。
    # provisional line rows = vertical extent of glyph pixels (for pitch / closing sizes);
    # refined after cutting from the median top / bottom of the tall glyphs (below).
    r0, r1 = ra, rb
    if char_height_px is None:
        h = float(r1 - r0)
        p_dot = h / 6.8
    # ドット書体の判定: 連結成分の中央面積が字高^2 の 4 % 未満(1 ドット ~1 %、単線字 ~30 %)。
    # dot-matrix detection: median component area < 4 % of h^2 (one dot ~1 %, stroke glyph ~30 %).
    if dot_font is None:
        lab, n = ndimage.label(B, structure=np.ones((3, 3)))
        a = np.bincount(lab.ravel())[1:]
        dot_font = bool(n > 0 and float(np.median(a)) < 0.04 * h * h)
    col = B[ra:rb].any(axis=0)
    if dot_font:
        # 列射影に 1-D の closing(横方向だけの異方的 closing)。長さ 0.6p: ドット列の隙間
        # (1-d)p は埋め、字間の隙間 (2-d)p は残す。斜めに並ぶドット(X, /)でも列は埋まる。
        # 1-D closing of the column projection (horizontal-only, anisotropic), length 0.6 p:
        # fills intra-glyph gaps (1-d)p, keeps inter-glyph gaps (2-d)p; works for diagonal dots.
        k = max(2, int(math.ceil(0.6 * p_dot)))
        col = ndimage.binary_closing(np.pad(col, k), structure=np.ones(k, bool))[k:-k] | col
    # 連続するインク列の区間 / runs of ink columns
    d = np.diff(np.concatenate([[0], col.astype(np.int8), [0]]))
    runs = list(zip(np.nonzero(d == 1)[0].tolist(), np.nonzero(d == -1)[0].tolist()))
    adv = _ADV_RATIO * h
    cw = _WIDTH_RATIO * h
    # 送り幅の補正: 字幅らしい区間(中心間隔を字数で割る)の中央値。区間が 3 つ以上あるときだけ。
    # (自己相関による推定も試したが、ぼけ 0.1h で 1 割の行が 17 % 以上外れたので採らない。)
    # pitch refinement: median centre spacing of glyph-like runs divided by slot count (>= 3 runs).
    # (Autocorrelation was tried and rejected: >17 % error on 10 % of lines at blur 0.1 h.)
    good = [(s_ + e_) / 2.0 for s_, e_ in runs if 0.45 * cw <= e_ - s_ <= 1.25 * cw]
    diffs = []
    for a_, b_ in zip(good[:-1], good[1:]):
        q = round((b_ - a_) / adv)
        if q >= 1:
            diffs.append((b_ - a_) / q)
    if len(diffs) >= 2:
        adv = float(np.clip(np.median(diffs), 0.8 * adv, 1.25 * adv))
        cw = adv * _WIDTH_RATIO / _ADV_RATIO
    gap = adv - cw
    # 断片の併合: 併せても字幅の 1.1 倍以内で、隙間が想定字間の 0.6 倍未満。
    # merge fragments: combined width <= 1.1 cw and inner gap < 0.6 x expected gap.
    merged = []
    for s, e in runs:
        if merged and (e - merged[-1][0]) <= 1.1 * cw and (s - merged[-1][1]) < 0.6 * gap:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    # 接触字の分割: 字幅の 1.35 倍を超える区間を、想定境界付近の射影の谷で切る。
    # split touching glyphs: runs wider than 1.35 cw are cut at projection minima near the
    # expected boundaries.
    prof = ink[ra:rb].sum(axis=0)
    final = []                                     # (s, e, 分割元の区間 / source run or None)
    for s, e in merged:
        w = e - s
        if w > 1.35 * cw:
            nseg = max(2, int(round((w + gap) / adv)))
            step = (w + gap) / nseg
            cuts = [s]
            for i in range(1, nseg):
                c = s + i * step - gap / 2.0
                lo = int(max(cuts[-1] + 1, round(c - 0.25 * adv)))
                hi = int(min(e - 1, round(c + 0.25 * adv)))
                if hi <= lo:
                    continue
                cuts.append(lo + int(np.argmin(prof[lo:hi + 1])))
            cuts.append(e)
            final.extend((a_, b_, (s, e)) for a_, b_ in zip(cuts[:-1], cuts[1:]))
        else:
            final.append((s, e, None))
    boxes, sources = [], []
    # 字として小さすぎる区間(字の画素 < 0.02 h^2 = ドット約 2 個)は雑音として捨てる。最小の字
    # '.' はドット 4 個(2x2)なので、きれいな印字では落ちない。
    # drop pieces with fewer than 0.02 h^2 glyph pixels (~2 dots) as noise; the smallest glyph
    # '.' has 4 dots (2x2) so clean prints are unaffected.
    min_glyph = 0.02 * h * h
    for s, e, src in final:
        box = _tight_box(B, (ra, rb), s, e)
        if box is None or int(B[ra:rb, s:e].sum()) < min_glyph:
            continue
        sources.append(src)
        boxes.append(box)
    if not boxes:
        return _empty_seg(t, g.shape)
    top, bottom = _line_rows(ink, boxes)
    r0, r1 = int(math.floor(top)), int(math.ceil(bottom))
    if char_height_px is None:
        h = float(bottom - top)
    line_box = (r0, ca, r1, cb)
    return {"boxes": boxes, "threshold": float(t), "line_box": line_box,
            "char_height_px": float(h), "pitch_px": float(adv), "dot_font": bool(dot_font),
            "_ink": ink, "_binary": B, "_sources": sources, "_rows": (ra, rb),
            "_line_frac": (float(top), float(bottom))}


def ocr_segment_line(image, char_height_px=None, dot_font=None) -> dict:
    """1 行の文字を 1 字ずつの外接箱に切り出す(``table``)。

    手順: 大津で地とインクの代表値(中央値)→ インク量の地図 → 字の画素 = インク量 >= 0.5 →
    雑音点の除去 → (ドット書体なら) 列射影にドットピッチ 0.6 倍の 1-D closing で 1 字のドットを
    まとめる → 列射影の切れ目で区間化 → 想定送り幅で断片を併合・接触字を分割(射影の谷)→
    字の画素が 0.02 h^2 未満の区間を捨てる。等幅(固定ピッチ)印字を前提とする。
    幾何だけの分割なので、ぼけで接触した字は ``ocr_read_line`` が認識で切り直す。
    Otsu class medians -> ink map -> glyph pixels (ink >= 0.5) -> speck removal -> (dot font)
    1-D closing of the column projection (0.6 x dot pitch) -> runs -> merge / split by expected
    pitch -> drop pieces < 0.02 h^2 pixels. Assumes fixed-pitch print.

    Parameters
    ----------
    image : 2-D 灰色(float 0..1 か uint8)。暗いインク・明るい地(逆なら縁から自動反転)。
    char_height_px : 字高の既知値。None なら行のインクの縦幅から推定
        (★行が ``-`` ``.`` だけだと過小推定になる —— 既知なら渡すこと)。
    dot_font : True/False/None(None = 連結成分の大きさで自動判定)。

    Returns
    -------
    dict
        ``boxes`` 左→右の ``(r0, c0, r1, c1)``(終端は含まない), ``threshold``(大津の閾値、
        雑音があれば 0.7 px 平滑後の画像に対する値。字の画素の判定には使わない参考値),
        ``line_box``, ``char_height_px``(使った値), ``pitch_px``(推定送り幅), ``dot_font``。
        白紙(インクと地の分離が雑音 4σ 未満)は **fail-soft で** ``boxes == []``,
        ``line_box is None``。

    Raises
    ------
    ValueError
        NaN/inf、2-D 以外、数値でない、4x4 未満。
    """
    seg = _segment(image, char_height_px, dot_font)
    return {k: v for k, v in seg.items() if not k.startswith("_")}


# --------------------------------------------------------------------------- #
# 特徴量 / Features                                                            #
# --------------------------------------------------------------------------- #

def ocr_features(glyph_image) -> np.ndarray:
    """1 字のインク地図から 88 次元の特徴量(区画の濃度 + 射影)を作る(``signal``)。

    入力の約束 / Input contract
        ``glyph_image`` は**インク量の地図**(1 = インク、0 = 地、float)で、
        **行は字高の範囲(行の上端〜下端)、列はその字を含む範囲**を切り出したもの
        (``ocr_read_line`` はインク重心を中心に送り幅 1 つぶんの幅で切る)。
        行を字高にそろえるので ``.`` ``-`` ``:`` の縦位置と大きさが特徴量に残る
        (インクの外接箱で正規化すると ``.`` は大きな円板になり、何にでも似てしまう)。

    正規化 / Normalisation
        縦: 切り出しの高さを ``FEATURE_GRID`` (24) 画素に拡縮。横: **同じ倍率**(縦横比保持)で、
        インクの重心列をキャンバス中央に置く(字幅を推定しないので、ぼけで箱が太っても位置がずれない)。
        縮小時は先に Gaussian で前置平滑(エイリアス防止)し、map_coordinates(双線形)で標本化。

    構成 / Layout (length ``FEATURE_LENGTH`` = 88)
        [0:64]  8x8 区画濃度(各 3x3 画素の平均インク、0..1)/ zoning densities
        [64:76] 水平射影(行方向の平均インク、12 ビン)/ horizontal projection profile
        [76:88] 垂直射影(列方向の平均インク、12 ビン)/ vertical projection profile

    交差数(crossing count)は使わない: 離散値で、ぼけとドットの途切れに不安定なため。
    Crossing counts are not used: they are discrete and unstable under blur / dot gaps.

    インクが無ければ全 0 を返す。/ Returns zeros for an empty glyph.
    """
    a = np.asarray(glyph_image)
    if a.dtype == object or not (np.issubdtype(a.dtype, np.number) or a.dtype == bool):
        raise ValueError("glyph_image must be a numeric array")
    if a.ndim != 2:
        raise ValueError(f"glyph_image must be 2-D, got ndim={a.ndim}")
    if a.shape[0] < 2 or a.shape[1] < 1:
        raise ValueError(f"glyph_image is too small: {a.shape}")
    a = a.astype(np.float64)
    if not np.isfinite(a).all():
        raise ValueError("glyph_image contains NaN or inf")
    a = np.clip(a, 0.0, 1.0)
    tot = float(a.sum())
    if tot <= 1e-9:
        return np.zeros(FEATURE_LENGTH)
    cx = float((a.sum(axis=0) * (np.arange(a.shape[1]) + 0.5)).sum() / tot)   # 重心(画素端基準)
    return _sample_features(a, 0.0, float(a.shape[0]), cx, None)


def _sample_features(src, top, bottom, cx, half_w):
    """連続座標(画素の端が整数)で指定した窓から 24x24 の正規化キャンバスを標本化し特徴量にする。

    Sample the normalised 24x24 canvas from continuous window geometry (pixel edges at
    integers): rows ``top..bottom`` (fractional), columns centred at ``cx`` with the same scale;
    columns farther than ``half_w`` from ``cx`` are zeroed (``None`` = no limit). 小数の行端を
    使うのは、整数の行端だと字高 16 px で縦の正規化が最大 1.5 キャンバス画素ずれ、同じ字の型どうしの
    距離が字種外の字との距離と同じ桁まで広がったため。
    Fractional row edges are used because integer edges shifted the vertical normalisation by up
    to 1.5 canvas px at 16 px char height, spreading templates of one class as far apart as an
    out-of-charset glyph.
    """
    N = FEATURE_GRID
    Hc = float(bottom - top)
    if Hc <= 0:
        return np.zeros(FEATURE_LENGTH)
    s = N / Hc
    ys = top + (np.arange(N) + 0.5) / s                     # 連続座標 / continuous positions
    xs = cx + (np.arange(N) + 0.5 - N / 2.0) / s
    # 必要な範囲だけ切って前置平滑(縮小時のエイリアス防止)/ local crop + anti-alias prefilter
    sig = 0.5 / s if s < 1.0 else 0.0
    pad = int(math.ceil(3 * sig)) + 2
    r_lo = max(0, int(math.floor(ys[0])) - pad)
    r_hi = min(src.shape[0], int(math.ceil(ys[-1])) + pad + 1)
    c_lo = max(0, int(math.floor(xs[0])) - pad)
    c_hi = min(src.shape[1], int(math.ceil(xs[-1])) + pad + 1)
    if r_hi <= r_lo or c_hi <= c_lo:
        return np.zeros(FEATURE_LENGTH)
    loc = src[r_lo:r_hi, c_lo:c_hi]
    if sig > 0:
        loc = ndimage.gaussian_filter(loc, sigma=sig, mode="constant")
    yy, xx = np.meshgrid(ys - 0.5 - r_lo, xs - 0.5 - c_lo, indexing="ij")
    canvas = ndimage.map_coordinates(loc, [yy, xx], order=1, mode="constant", cval=0.0)
    canvas = np.clip(canvas, 0.0, 1.0)
    if half_w is not None:
        canvas[:, np.abs(xs - cx) > half_w] = 0.0
    z = N // _ZONES
    zoning = canvas.reshape(_ZONES, z, _ZONES, z).mean(axis=(1, 3)).ravel()
    pb = N // _PROJ_BINS
    hproj = canvas.mean(axis=1).reshape(_PROJ_BINS, pb).mean(axis=1)
    vproj = canvas.mean(axis=0).reshape(_PROJ_BINS, pb).mean(axis=1)
    return np.concatenate([zoning, hproj, vproj])


def _crop_features(ink, boxes, line_rows, adv):
    """字ごとに「送り幅 1 つぶんの窓」を切って特徴量を並べる。

    窓 = 行は行範囲 ``line_rows = (上端, 下端)``(小数)、列は箱の中のインク重心を中心に幅
    ``adv``(送り幅)。箱の端(切れ目)を
    そのまま使うと、ぼけで字が接したとき切れ目の位置が雑音で数画素ゆれ、隣字のにじみの
    入り方が学習と読みで食い違う(実測: ぼけ 0.1h・雑音 0.05 のドット書体で、真値の切れ目を
    使っても 91.6 % に留まった)。窓を重心と送り幅で決めると、切れ目は重心を通してしか効かない。
    Window = line rows x (ink centroid inside the box +/- adv/2). Using the cut positions
    directly made the neighbour bleed differ between training and reading when blur makes
    glyphs touch (91.6 % even with true cuts at blur 0.1 h, noise 0.05); with a centroid-centred
    pitch-wide window the cuts only matter through the centroid.
    """
    top, bottom = float(line_rows[0]), float(line_rows[1])
    r0, r1 = int(math.floor(top)), int(math.ceil(bottom))
    out = np.zeros((len(boxes), FEATURE_LENGTH))
    for n, (_, c0, _, c1) in enumerate(boxes):
        sub = ink[r0:r1, c0:c1]
        tot = float(sub.sum())
        if tot <= 1e-9:
            continue
        cx = c0 + float((sub.sum(axis=0) * (np.arange(c1 - c0) + 0.5)).sum() / tot)
        out[n] = _sample_features(ink, top, bottom, cx, 0.5 * float(adv))
    return out


# --------------------------------------------------------------------------- #
# 学習(テンプレート集め)/ Training (collecting templates)                      #
# --------------------------------------------------------------------------- #

#: 学習の既定撹乱。/ Default nuisance variations for training.
_DEFAULT_VARIANTS: dict = {
    "ink_gain": (-0.15, 0.0, 0.25),   # にじみ / dot gain, stroke spread
    "blur": (0.0, 0.02, 0.04, 0.06, 0.08, 0.10, 0.12, 0.14),  # Gaussian sigma / 字高 / blur sigma relative to char height
    "subpixel": True,                 # 乱数(seed 固定)で 0..1 px の小数ずらし / seeded sub-px shift
    "noise": 0.0,                     # 加法 Gaussian 雑音の σ(seed 固定)/ seeded additive noise
}


def _within_class_weights(X, y, bv):
    """特徴の各次元の重み = 1 / (クラス内・ぼけ格子点内の標準偏差の合算)(対角マハラノビス)。

    撹乱(にじみ・小数ずれ・隣字)で大きく揺れる次元ほど軽くする。床は全次元の中央値の 0.25 倍。
    Per-dimension weights = 1 / pooled within-(class, blur level) std (diagonal Mahalanobis);
    floored at 0.25 x the median std so near-constant dimensions do not explode.
    """
    groups = {}
    for i, key in enumerate(zip(y.tolist(), bv.tolist())):
        groups.setdefault(key, []).append(i)
    ss = np.zeros(X.shape[1])
    dof = 0
    for idx in groups.values():
        if len(idx) < 2:
            continue
        G = X[idx]
        ss += ((G - G.mean(axis=0)) ** 2).sum(axis=0)
        dof += len(idx) - 1
    sd = np.sqrt(ss / max(dof, 1))
    floor = 0.25 * float(np.median(sd)) if np.median(sd) > 0 else 1.0
    return 1.0 / np.maximum(sd, floor)


def _model_w(model):
    w = model.get("weights")
    return np.ones(FEATURE_LENGTH) if w is None else np.asarray(w, float)


def _pairwise_sq(a, b):
    d2 = (a * a).sum(1)[:, None] + (b * b).sum(1)[None, :] - 2.0 * a @ b.T
    return np.maximum(d2, 0.0)


def ocr_train(font="dot5x7", char_height_px=(16, 20, 26, 34), variants=None, seed=0,
              neighbour="random") -> dict:
    """書体を撹乱つきで描いてテンプレート(特徴量 + ラベル)と棄却の閾値を集める(``table``)。

    Render every character under a small deterministic set of nuisance variations and collect
    feature templates for k-NN.

    各試料は「乱数(seed 固定)で選んだ隣字 + 字 + 隣字」の 3 字行として描き、撹乱(字高・にじみ・
    ぼけ・小数ずれ)をかけてから、**読み取りと同じ規則**で中央の字を切る: 字間の中点(真値)に最も
    近い列射影の極小を切れ目とし(読みの切れ目候補と同じ規則)、その間の字の画素(ink >= 0.5)の
    外接箱から、重心中心・送り幅の窓で特徴量を取る。隣字を固定(例 ``"H"``)にすると、読みの場で
    隣に来る字のにじみが学習に無く、ぼけ 0.1h で正解率が 2 割落ちた(実測)ので乱数にしている。
    切れなかった試料(字の画素が無い)は真値の箱で代替し、件数を ``n_fallback`` に残す。

    Each sample is a 3-glyph line (seeded random neighbours + glyph + neighbour); the middle glyph
    is cut with the same rule as reading (profile minima nearest to the true gap midpoints) and
    featurised with the centroid-centred pitch-wide window. A fixed neighbour lost ~20 % accuracy
    at blur 0.1 h (measured), hence random neighbours.

    Parameters
    ----------
    font : 書体名か書体辞書。
    char_height_px : 字高の組(各 8..256)。既定 (16, 20, 26, 34)。
    variants : ``{"ink_gain": tuple, "blur": tuple (σ / 字高), "subpixel": bool, "noise": float}``。
        None で既定(にじみ 3 x ぼけ 8 [0..0.14h, 0.02h 刻み] x 字高 4 = 1 字 96 試料、
        40 字で 3840 試料)。
    seed : 小数ずらし・隣字・雑音の乱数種(決定的)。
    neighbour : ``"random"``(既定)か字種内の 1 字。

    Returns
    -------
    dict
        ``features`` (n, 88), ``labels`` (n,) str, ``weights`` (88,) 対角マハラノビスの重み,
        ``blur`` (n,) 各試料のぼけ, ``blur_levels``, ``blur_step``, ``charset``, ``font``,
        ``font_kind``, ``k`` (=1), ``reject_distance``(全体の値、帯を指定しない照合用),
        ``reject_distance_by_class``(字ごと), ``min_margin_ratio``, ``reject_stats``
        (``within_nn_p99``, ``factor``, ``between_nn_min``, ``between_nn_p01``), ``n_fallback``,
        ``heights``。

    棄却距離の導き方 / reject_distance derivation
        各試料について「同クラス・ぼけ帯内(±1 格子点)の最近傍の**他の**試料までの重みつき距離」を
        求め、**字ごとに**その 99 パーセンタイル x ``REJECT_FACTOR`` を棄却距離とする。
        学習分布だけで決まる(係数の選び方は ``REJECT_FACTOR`` の注記を参照)。
        Per class: REJECT_FACTOR x P99 of the within-class, within-band nearest-other-sample
        weighted distance. Derived from the training distribution only.
    """
    f = _resolve_font(font)
    if isinstance(char_height_px, (int, float, np.integer, np.floating)) \
            and not isinstance(char_height_px, bool):
        char_height_px = (char_height_px,)
    try:
        heights = [float(_check_number("char_height_px", v, lo=8, hi=256))
                   for v in char_height_px]
    except TypeError as exc:
        raise ValueError("char_height_px must be a number or a sequence of numbers") from exc
    if not heights:
        raise ValueError("char_height_px must not be empty")
    v = dict(_DEFAULT_VARIANTS)
    if variants is not None:
        if not isinstance(variants, dict):
            raise ValueError("variants must be a dict or None")
        unknown = set(variants) - set(_DEFAULT_VARIANTS)
        if unknown:
            raise ValueError(f"unknown variant keys: {sorted(unknown)}")
        v.update(variants)
    gains = [float(_check_number("ink_gain", x, lo=-0.9, hi=2.0, lo_open=True))
             for x in v["ink_gain"]]
    blurs = [float(_check_number("blur", x, lo=0.0, hi=0.5)) for x in v["blur"]]
    noise_sd = float(_check_number("noise", v["noise"], lo=0.0, hi=0.3))
    if not gains or not blurs:
        raise ValueError("variants ink_gain and blur must be non-empty")
    if neighbour != "random" and (not isinstance(neighbour, str) or len(neighbour) != 1
                                  or neighbour not in f["charset"]):
        raise ValueError("neighbour must be 'random' or a single charset character")
    rng = np.random.default_rng(int(seed))
    dot = f["kind"] == "dot"
    fv = _Validated(f)
    feats, labels, blur_of, meta = [], [], [], []
    n_fallback = 0
    for c in f["charset"]:
        for h in heights:
            for gn in gains:
                for bl in blurs:
                    off = tuple(rng.uniform(0, 1, 2)) if v["subpixel"] else (0.0, 0.0)
                    if neighbour == "random":
                        nb = rng.choice(list(f["charset"]), 2)
                        txt = nb[0] + c + nb[1]
                    else:
                        txt = neighbour + c + neighbour
                    r = ocr_render_text(txt, fv, char_height_px=h,
                                        ink_gain=gn, subpixel_offset=off)
                    img = r["image"]
                    if bl > 0:
                        img = ndimage.gaussian_filter(img, bl * h, mode="nearest")
                    if noise_sd > 0:
                        img = img + rng.normal(0.0, noise_sd, img.shape)
                    seg = _segment(img, dot_font=dot)
                    # 中央の字の切れ目 = 字間の中点(真値)に最も近い列射影の極小(読みの切れ目候補と
                    # 同じ規則)。その間の字の画素の外接列を、読みと同じ規則(ink >= 0.5)で取る。
                    # cuts of the middle glyph = column-profile minima nearest to the true gap
                    # midpoints (the same candidate rule as reading); tight glyph pixels between.
                    cl, cr = r["cells"][1]
                    half_gap = 0.5 * (r["pitch_px"] - (cr - cl))
                    box = None
                    if seg["line_box"] is not None:
                        lb = seg["line_box"]
                        prof = _cut_profile(seg["_ink"][lb[0]:lb[2]].sum(axis=0),
                                            seg["pitch_px"])
                        lo = _cut_near(prof, cl - half_gap, seg["pitch_px"])
                        hi = _cut_near(prof, cr + half_gap, seg["pitch_px"])
                        box = _tight_box(seg["_binary"], seg["_rows"], lo, hi)
                    if box is None:
                        n_fallback += 1
                        ink = np.clip((0.9 - img) / 0.8, 0.0, 1.0)
                        box, adv_s = r["boxes"][1], r["pitch_px"]
                        lrows = (r["line_box"][0], r["line_box"][2])
                    else:
                        ink, adv_s, lrows = seg["_ink"], seg["pitch_px"], seg["_line_frac"]
                    feats.append(_crop_features(ink, [box], lrows, adv_s)[0])
                    labels.append(c)
                    blur_of.append(bl)
                    meta.append((txt, float(h), float(gn), float(bl)))
    X = np.asarray(feats)
    y = np.asarray(labels)
    bv = np.asarray(blur_of, float)
    wts = _within_class_weights(X, y, bv)
    D = np.sqrt(_pairwise_sq(X * wts, X * wts))
    np.fill_diagonal(D, np.inf)
    same = y[:, None] == y[None, :]
    # 同クラス内の最近傍は「ぼけの帯」(読みと同じ: 隣り合う格子点まで)の中で数える。
    # within-class NN is taken inside the blur band, exactly as reading restricts templates.
    blur_levels = np.unique(bv)
    step = float(np.min(np.diff(blur_levels))) if len(blur_levels) > 1 else 0.0
    in_band = np.abs(bv[:, None] - bv[None, :]) <= step * 1.0001
    within = np.where(same & in_band, D, np.inf).min(axis=1)
    between = np.where(~same, D, np.inf).min(axis=1)
    # クラスごとの棄却距離: そのクラスの試料の「同クラス・帯内の最近傍他試料距離」の P99 x 係数。
    # 全クラスで 1 つの閾値にすると、大きさが小さく揺れやすい字('.' ':' '-')の裾が閾値を決め、
    # 形の安定した字(例 '4')のまわりでは緩すぎる(実測: 字種外の '#' が '4' の型から距離 21、
    # 全体の閾値 23 の内側に入り、40 回中 40 回誤読された)。
    # per-class reject distance: REJECT_FACTOR x P99 of that class's within-class, within-band
    # nearest-other-sample distance. A single global threshold is set by the tails of small,
    # unstable glyphs ('.', ':', '-') and is too loose around stable shapes (measured: an
    # out-of-charset '#' at distance 21 from '4' templates passed a global threshold of 23).
    rd_by_class = {}
    for c in f["charset"]:
        w = within[(y == c) & np.isfinite(within)]
        rd_by_class[c] = float(REJECT_FACTOR * np.percentile(w, 99)) if w.size else 0.0
    within = within[np.isfinite(within)]
    p99 = float(np.percentile(within, 99)) if within.size else 0.0
    rd = REJECT_FACTOR * p99
    return {"features": X, "labels": y, "weights": wts, "blur": bv, "blur_levels": blur_levels,
            "blur_step": step, "charset": f["charset"],
            "font": f.get("name", f["kind"]), "font_kind": f["kind"], "k": 1,
            "reject_distance": float(rd), "reject_distance_by_class": rd_by_class,
            "min_margin_ratio": MIN_MARGIN_RATIO,
            "reject_stats": {"within_nn_p99": p99, "factor": REJECT_FACTOR,
                             "between_nn_min": float(between.min()),
                             "between_nn_p01": float(np.percentile(between, 1))},
            "n_fallback": int(n_fallback), "heights": tuple(heights),
            "samples": meta}


def _check_model(model) -> dict:
    if not isinstance(model, dict):
        raise ValueError("model must be a dict returned by ocr_train")
    for key in ("features", "labels", "reject_distance"):
        if key not in model:
            raise ValueError(f"model is missing key {key!r}")
    X = np.asarray(model["features"], float)
    y = np.asarray(model["labels"])
    if X.ndim != 2 or X.shape[1] != FEATURE_LENGTH or X.shape[0] != y.shape[0] or not len(y):
        raise ValueError("model features/labels have inconsistent shapes")
    if not np.isfinite(X).all():
        raise ValueError("model features contain NaN or inf")
    rd = float(model["reject_distance"])
    if not math.isfinite(rd) or rd < 0:
        raise ValueError("model reject_distance must be finite and >= 0")
    if model.get("weights") is not None:
        w = np.asarray(model["weights"], float)
        if w.shape != (FEATURE_LENGTH,) or not np.isfinite(w).all() or (w <= 0).any():
            raise ValueError("model weights must be a finite positive vector of feature length")
    if "blur" in model and np.asarray(model["blur"]).shape != y.shape:
        raise ValueError("model blur must have one entry per template")
    return model


# --------------------------------------------------------------------------- #
# 識別 / Classification                                                        #
# --------------------------------------------------------------------------- #

def _band_mask(model, blur):
    """ぼけ ``blur``(σ/字高)の帯 = 隣り合う格子点までの学習試料。None なら全部。"""
    n = len(model["labels"])
    if blur is None or "blur" not in model:
        return np.ones(n, bool)
    b = _check_number("blur", blur, lo=0.0, hi=1.0)
    bv = np.asarray(model["blur"], float)
    step = float(model.get("blur_step", 0.0))
    m = np.abs(bv - b) <= step * 1.0001
    if not m.any():
        m = np.abs(bv - b) <= np.abs(bv - b).min() * 1.0001
    return m


def ocr_classify(features, model, k=1, blur=None) -> dict:
    """特徴量を k 最近傍で識別し、距離と距離比で棄却する(``table``)。

    Parameters
    ----------
    features : (d,) か (m, d)、d = FEATURE_LENGTH。
    model : ``ocr_train`` の返り値。
    k : 近傍数(奇数推奨)。多数決、同票は最近傍のクラス。
    blur : 既知(または推定済み)のぼけ σ/字高。与えると、学習のぼけ格子でそれと隣り合う
        格子点までの試料だけを照合に使う(``ocr_read_line`` は行全体で推定して渡す)。
        Restrict templates to the blur band around ``blur`` (sigma / char height).

    Returns
    -------
    dict
        ``labels`` (list of str、棄却は ``"?"``), ``raw_labels``(棄却前の判定),
        ``distance``(判定クラスの最近傍距離。``model["weights"]`` で重みづけした対角マハラノビス距離),
        ``margin``(**他クラス最近傍距離 / 判定クラス最近傍距離**、1 に近いほど境界上), ``rejected``。
        棄却条件: ``distance > reject_distance_by_class[判定字]`` または ``margin < min_margin_ratio``。
    """
    _check_model(model)
    if isinstance(k, bool) or not isinstance(k, (int, np.integer)) or k < 1:
        raise ValueError("k must be a positive integer")
    F = np.asarray(features)
    if F.dtype == object or not np.issubdtype(F.dtype, np.number):
        raise ValueError("features must be numeric")
    F = F.astype(float)
    if F.ndim == 1:
        F = F[None, :]
    if F.ndim != 2 or F.shape[1] != FEATURE_LENGTH:
        raise ValueError(f"features must have length {FEATURE_LENGTH}")
    if not np.isfinite(F).all():
        raise ValueError("features contain NaN or inf")
    if F.shape[0] == 0:
        # 空の入力は黙って空の結果を返さない(fail-closed)/ refuse an empty batch
        raise ValueError("features is empty (0 rows) — nothing to classify")
    band = _band_mask(model, blur)
    w = _model_w(model)
    X = np.asarray(model["features"], float)[band] * w
    y = np.asarray(model["labels"])[band]
    F = F * w
    k = int(min(k, len(y)))
    rd_global = float(model["reject_distance"])
    rd_class = model.get("reject_distance_by_class") or {}
    mr = float(model.get("min_margin_ratio", MIN_MARGIN_RATIO))
    D = np.sqrt(_pairwise_sq(F, X))
    labels, raw, dist, margin, rej = [], [], [], [], []
    for row in D:
        order = np.argsort(row, kind="stable")[:k]
        if k == 1:
            lab = str(y[order[0]])
        else:
            votes = {}
            for idx in order:
                votes[str(y[idx])] = votes.get(str(y[idx]), 0) + 1
            best = max(votes.values())
            lab = next(str(y[idx]) for idx in order if votes[str(y[idx])] == best)
        d_own = float(row[y == lab].min())
        other = row[y != lab]
        d_other = float(other.min()) if other.size else math.inf
        ratio = math.inf if d_own <= 1e-12 else d_other / d_own
        rd = float(rd_class.get(lab, rd_global))
        is_rej = bool(d_own > rd or ratio < mr)
        raw.append(lab)
        labels.append("?" if is_rej else lab)
        dist.append(d_own)
        margin.append(float(ratio))
        rej.append(is_rej)
    return {"labels": labels, "raw_labels": raw, "distance": dist, "margin": margin,
            "rejected": rej}


def _estimate_line_blur(F, model):
    """行のぼけを「行全体で最も良く合う学習のぼけ」として推定する(1 行のぼけは共通)。

    各ぼけ格子点 b について、帯(b と隣り合う格子点)の試料に対する各字の最近傍距離の
    中央値を求め、それが最小の b を採る。字ごとに帯を選ばないのは、ぼけた別字が
    鮮明な字に化けるのを防ぐため(帯を限らないと、ぼけた ``8`` の型が鮮明な ``B`` の
    他クラス最近傍になり、距離比が潰れる)。
    The blur of a line is shared by its glyphs: pick the training blur level whose band gives
    the smallest median nearest-neighbour distance over the line. Choosing per glyph would let a
    blurred template of another class impersonate a sharp glyph.
    """
    if "blur_levels" not in model or len(F) == 0:
        return None
    w = _model_w(model)
    X = np.asarray(model["features"], float) * w
    D = np.sqrt(_pairwise_sq(F * w, X))
    best, best_b = math.inf, None
    for b in np.asarray(model["blur_levels"], float):
        m = _band_mask(model, float(b))
        score = float(np.median(D[:, m].min(axis=1)))
        if score < best - 1e-12:
            best, best_b = score, float(b)
    return best_b


def _resegment_touching(seg, model):
    """接触字の区間を「認識による切り出し」で切り直す(動的計画法)。

    Recognition-driven re-segmentation of touching runs (dynamic programming over cut
    candidates; classical "segmentation by recognition", cf. Casey & Lecolinet, IEEE TPAMI
    18(7):690, 1996). 幾何だけの分割(想定ピッチ)はぼけで字高・ピッチの推定が 1 割ずれると
    字数を間違える。そこで、分割元の区間ごとに列射影の極小を切れ目候補とし、
    各区片の最近傍距離の和が最小になる切り方を選ぶ。区片の幅は送り幅の 0.3〜1.4 倍に限る。
    Geometric splitting miscounts glyphs when blur biases the height / pitch estimate by ~10 %;
    here cut candidates are the column-profile minima of each touching run, and the partition
    minimising the sum of nearest-neighbour distances is chosen (piece width 0.3..1.4 x pitch).
    """
    boxes = list(seg["boxes"])
    sources = seg["_sources"]
    if all(src is None for src in sources):
        return boxes
    ink, B, rows, lb = seg["_ink"], seg["_binary"], seg["_rows"], seg["line_box"]
    adv = float(seg["pitch_px"])
    cw = adv * _WIDTH_RATIO / _ADV_RATIO
    wv = _model_w(model)
    X = np.asarray(model["features"], float) * wv
    out = []
    i = 0
    while i < len(boxes):
        src = sources[i]
        if src is None:
            out.append(boxes[i])
            i += 1
            continue
        j = i
        while j < len(boxes) and sources[j] == src:
            j += 1
        s, e = src
        prof = _cut_profile(ink[lb[0]:lb[2]].sum(axis=0), adv)
        cand = [s] + [q for q in _profile_minima(prof) if s < q < e] + [e]
        n = len(cand)
        memo = {}

        def piece_cost(a, b):
            if (a, b) not in memo:
                box = _tight_box(B, rows, cand[a], cand[b])
                if box is None:
                    memo[(a, b)] = (math.inf, None)
                else:
                    f = _crop_features(ink, [box], seg["_line_frac"], adv)
                    d = float(np.sqrt(_pairwise_sq(f * wv, X).min()))
                    memo[(a, b)] = (d, box)
            return memo[(a, b)]

        best = [math.inf] * n
        prev = [-1] * n
        best[0] = 0.0
        for b in range(1, n):
            for a in range(b - 1, -1, -1):
                w = cand[b] - cand[a]
                if w > 1.4 * adv:
                    break
                if w < 0.3 * adv or best[a] == math.inf:
                    continue
                # 等幅の事前: 区片幅の期待値は内側 = 送り幅、端 = (送り幅 + 字幅)/2、
                # 区間がそのまま 1 字 = 字幅。外れの二乗に _DP_WIDTH_PENALTY を掛けて足す。
                # fixed-pitch prior on the piece width (interior adv, end (adv+cw)/2, whole cw).
                ends = (a == 0) + (b == n - 1)
                w_exp = adv if ends == 0 else (0.5 * (adv + cw) if ends == 1 else cw)
                pen = _DP_WIDTH_PENALTY * ((w - w_exp) / adv) ** 2
                c = best[a] + piece_cost(a, b)[0] + pen
                if c < best[b]:
                    best[b], prev[b] = c, a
        if best[n - 1] == math.inf:
            out.extend(boxes[i:j])                      # 切れない: 幾何の分割のまま / keep
        else:
            path, b = [], n - 1
            while b > 0:
                path.append(piece_cost(prev[b], b)[1])
                b = prev[b]
            out.extend(reversed(path))
        i = j
    return out


def ocr_read_line(image, model, char_height_px=None, k=None) -> dict:
    """画像の 1 行を読む: 切り出し + 識別、棄却した字は ``?``(``table``)。

    Returns
    -------
    dict
        ``text``(棄却は ``"?"``), ``chars``(各字の ``label``, ``raw_label``, ``box``,
        ``distance``, ``margin``, ``rejected``), ``n_chars``, ``n_rejected``, ``line_box``。
        白紙は fail-soft で ``text == ""``, ``n_chars == 0``。
    """
    _check_model(model)
    dot = model.get("font_kind")
    dot = None if dot is None else (dot == "dot")
    seg = _segment(image, char_height_px, dot)
    if not seg["boxes"]:
        return {"text": "", "chars": [], "n_chars": 0, "n_rejected": 0, "line_box": None}
    boxes = _resegment_touching(seg, model)
    F = _crop_features(seg["_ink"], boxes, seg["_line_frac"], seg["pitch_px"])
    blur = _estimate_line_blur(F, model)
    res = ocr_classify(F, model, k=int(model.get("k", 1)) if k is None else k, blur=blur)
    chars = []
    for n, box in enumerate(boxes):
        chars.append({"label": res["labels"][n], "raw_label": res["raw_labels"][n],
                      "box": box, "distance": res["distance"][n],
                      "margin": res["margin"][n], "rejected": res["rejected"][n]})
    return {"text": "".join(c["label"] for c in chars), "chars": chars,
            "n_chars": len(chars), "n_rejected": int(sum(res["rejected"])),
            "line_box": seg["line_box"], "blur_estimate": blur}


# --------------------------------------------------------------------------- #
# 採点 / Scoring                                                               #
# --------------------------------------------------------------------------- #

def ocr_score(read_text, true_text) -> dict:
    """読み取り結果を真値と Levenshtein 整列で採点し、誤読と棄却を分けて数える(``table``)。

    整列(置換・挿入・削除の費用 1)の後、整列した各対を数える:

    * ``correct``     —— 同じ字
    * ``rejected``    —— 真値の字に対して ``"?"``(**棄却**: 安全側。人が見れば済む)
    * ``substituted`` —— 真値と違う字(**誤読**: 危険側。検査では見逃しになる)
    * ``inserted``    —— 真値に無い字が読まれた(``"?"`` の挿入も含む)
    * ``deleted``     —— 真値の字が読まれなかった

    誤読と棄却は**決して 1 つの率に畳まない**。率は真値の字数で割る。
    Misreads and rejects are never folded into one rate. Rates are per true character.
    """
    if not isinstance(read_text, str) or not isinstance(true_text, str):
        raise ValueError("read_text and true_text must be strings")
    a, b = read_text, true_text
    n, m = len(a), len(b)
    D = np.zeros((n + 1, m + 1), int)
    D[:, 0] = np.arange(n + 1)
    D[0, :] = np.arange(m + 1)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            D[i, j] = min(D[i - 1, j - 1] + (a[i - 1] != b[j - 1]),
                          D[i - 1, j] + 1, D[i, j - 1] + 1)
    i, j = n, m
    cnt = {"correct": 0, "substituted": 0, "rejected": 0, "inserted": 0, "deleted": 0}
    while i > 0 or j > 0:
        # 対角を優先(決定的な同点処理)/ prefer diagonal on ties (deterministic)
        if i > 0 and j > 0 and D[i, j] == D[i - 1, j - 1] + (a[i - 1] != b[j - 1]):
            if a[i - 1] == b[j - 1]:
                cnt["correct"] += 1
            elif a[i - 1] == "?":
                cnt["rejected"] += 1
            else:
                cnt["substituted"] += 1
            i, j = i - 1, j - 1
        elif i > 0 and D[i, j] == D[i - 1, j] + 1:
            cnt["inserted"] += 1
            i -= 1
        else:
            cnt["deleted"] += 1
            j -= 1
    tot = max(m, 1)
    cnt.update({"n_true": m, "n_read": n, "edit_distance": int(D[n, m]),
                "accuracy": cnt["correct"] / tot if m else (1.0 if n == 0 else 0.0),
                "misread_rate": cnt["substituted"] / tot, "reject_rate": cnt["rejected"] / tot})
    return cnt
