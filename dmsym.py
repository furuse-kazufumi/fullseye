# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Data Matrix ECC200 の符号化・復号・画像からの読み取り(訂正の内訳と module→符号語の地図つき)。

Data Matrix ECC200 encoder + decoder, with the per-block correction counts and
the module -> codeword map that print-quality grading needs.

なぜ自前か / why not a library
    直接部品マーキング(DPM)の読み取りと ISO/IEC 15415 流の印字品質の格付け
    (未使用の誤り訂正 UEC・符号語ごとの modulation・固定パターンの損傷)には、
    「ブロックごとに何語を直したか」と「どの module がどの符号語の何ビット目か」が
    要る。既存の読み取り器は文字列を返すだけでこれを出さない。
    Grading needs the corrected-codeword count per Reed-Solomon block and the
    module -> codeword map; off-the-shelf readers return only the text.

構成 / structure (ISO/IEC 16022 (structure as publicly described); libdmtx /
zxing のソース構成や Wikipedia "Data Matrix" などの公開記述に基づく自前実装)
    * 記号 = 1 個以上のデータ領域。各領域は左列(実線)・下行(実線)の L 字ファインダと、
      上行・右列の交互のクロック(タイミング)で囲まれる。
      A symbol is one or more data regions, each framed by a solid L (left column,
      bottom row) and an alternating clock track (top row, right column).
    * 領域の内側をつないだ「写像行列」に、符号語 8 bit を "utah" 形(と 4 つの角の特例)で
      斜めに敷く。余った右下 2x2 は固定の市松。
      Codewords are placed into the mapping matrix by the diagonal "utah" walk with
      four corner special cases; an unused bottom-right 2x2 gets a fixed pattern.
    * 誤り訂正は GF(256)(x^8+x^5+x^3+x^2+1)の Reed-Solomon、根 α^1..α^n(``symrs``)。
      大きな記号はブロックに分けて 1 語ずつ交互に並べる(interleave)。
    * データの符号化: ASCII(数字 2 桁圧縮・上位シフト 235)、C40、Text、Base256 を
      符号化と復号の両方、X12・EDIFACT は復号だけ。パッドは 129 + 253 状態の乱数化。

公開 API / public API
    ``dm_encode`` / ``dm_decode_modules`` / ``dm_locate`` / ``dm_sample`` / ``dm_read``。
    入力が不正なら ``ValueError``、読めなければ ``DMDecodeError``(``ValueError`` の子)。
    Invalid input raises ``ValueError``; a read failure raises ``DMDecodeError``.

座標の約束 / coordinate conventions
    画像座標は画素中心が整数(画素 (r, c) の中心 = (row=r, col=c)、``map_coordinates``
    と同じ)。module 空間は x = 列, y = 行、module (i, j) の中心は (j+0.5, i+0.5)、
    記号は 0..C × 0..R を占める。行 0 = 上のクロック、列 0 = L 字の縦棒、行 R-1 = L 字の横棒。
    Image coordinates put pixel centres on integers. Module space has x = column,
    y = row; module (i, j) is centred at (j + 0.5, i + 0.5); the symbol spans
    0..C x 0..R. ``homography`` maps module space [x, y, 1] to image [col, row, w].
"""
from __future__ import annotations

import functools

import numpy as np
from scipy import ndimage

from symrs import DM_FIELD, RSDecodeError, rs_decode, rs_encode

__all__ = ["DMDecodeError", "DM_SIZES", "dm_encode", "dm_decode_modules",
           "dm_locate", "dm_sample", "dm_read"]


class DMDecodeError(ValueError):
    """読み取り失敗(記号が見つからない・訂正能力超え・符号化の矛盾)/ the symbol could not be read."""


# ---------------------------------------------------------------------------------------------
# 記号の大きさの表 / symbol size table
# (rows, cols, regions_vertical, regions_horizontal, data codewords, EC codewords, RS blocks)
# ---------------------------------------------------------------------------------------------
_SQUARE = [
    (10, 10, 1, 1, 3, 5, 1), (12, 12, 1, 1, 5, 7, 1), (14, 14, 1, 1, 8, 10, 1),
    (16, 16, 1, 1, 12, 12, 1), (18, 18, 1, 1, 18, 14, 1), (20, 20, 1, 1, 22, 18, 1),
    (22, 22, 1, 1, 30, 20, 1), (24, 24, 1, 1, 36, 24, 1), (26, 26, 1, 1, 44, 28, 1),
    (32, 32, 2, 2, 62, 36, 1), (36, 36, 2, 2, 86, 42, 1), (40, 40, 2, 2, 114, 48, 1),
    (44, 44, 2, 2, 144, 56, 1), (48, 48, 2, 2, 174, 68, 1), (52, 52, 2, 2, 204, 84, 2),
    (64, 64, 4, 4, 280, 112, 2), (72, 72, 4, 4, 368, 144, 4), (80, 80, 4, 4, 456, 192, 4),
    (88, 88, 4, 4, 576, 224, 4), (96, 96, 4, 4, 696, 272, 4), (104, 104, 4, 4, 816, 336, 6),
    (120, 120, 6, 6, 1050, 408, 6), (132, 132, 6, 6, 1304, 496, 8), (144, 144, 6, 6, 1558, 620, 10),
]
_RECT = [
    (8, 18, 1, 1, 5, 7, 1), (8, 32, 1, 2, 10, 11, 1), (12, 26, 1, 1, 16, 14, 1),
    (12, 36, 1, 2, 22, 18, 1), (16, 36, 1, 2, 32, 24, 1), (16, 48, 1, 2, 49, 28, 1),
]
_SPEC = {(s[0], s[1]): s for s in _SQUARE + _RECT}

#: 対応する記号の大きさ (rows, cols) / every supported symbol size (rows, cols).
DM_SIZES = tuple(sorted(_SPEC, key=lambda rc: (_SPEC[rc][4], rc[0] * rc[1])))

_ENCODATIONS = ("ascii", "c40", "text", "base256")

# C40 / Text の集合 / C40 and Text character sets
_SHIFT2 = [ord(ch) for ch in "!\"#$%&'()*+,-./:;<=>?@[\\]^_"]          # values 0..26
_TEXT_SHIFT3 = [96] + list(range(65, 91)) + [123, 124, 125, 126, 127]    # values 0..31


# ---------------------------------------------------------------------------------------------
# 配置(utah 形)/ module placement
# ---------------------------------------------------------------------------------------------
@functools.lru_cache(maxsize=None)
def _placement(nrow: int, ncol: int):
    """写像行列 (nrow, ncol) の各 module が何番目の符号語の何ビット目か。

    Returns ``(cw, bit, n_codewords)``: ``cw`` (nrow, ncol) int32 = codeword index
    (0-based, -1 = unused corner), ``bit`` = bit index 0..7 with 0 = most significant.
    The diagonal walk and its four corner cases follow the publicly described ECC200
    placement (see module docstring).
    """
    cw = np.full((nrow, ncol), -1, np.int32)
    bit = np.full((nrow, ncol), -1, np.int8)

    def module(r, c, k, b):
        # 範囲外は反対側へ巻き込む / wrap around the edges
        if r < 0:
            r += nrow
            c += 4 - ((nrow + 4) % 8)
        if c < 0:
            c += ncol
            r += 4 - ((ncol + 4) % 8)
        cw[r, c] = k
        bit[r, c] = b

    def utah(r, c, k):
        for b, (dr, dc) in enumerate(((-2, -2), (-2, -1), (-1, -2), (-1, -1),
                                      (-1, 0), (0, -2), (0, -1), (0, 0))):
            module(r + dr, c + dc, k, b)

    def corner(cells, k):
        for b, (r, c) in enumerate(cells):
            module(r, c, k, b)

    n1, c1 = nrow - 1, ncol - 1
    k = 0
    r, c = 4, 0
    while True:
        if r == nrow and c == 0:
            corner(((n1, 0), (n1, 1), (n1, 2), (0, c1 - 1), (0, c1), (1, c1), (2, c1), (3, c1)), k)
            k += 1
        if r == nrow - 2 and c == 0 and ncol % 4:
            corner(((n1 - 2, 0), (n1 - 1, 0), (n1, 0), (0, c1 - 3), (0, c1 - 2), (0, c1 - 1),
                    (0, c1), (1, c1)), k)
            k += 1
        if r == nrow - 2 and c == 0 and ncol % 8 == 4:
            corner(((n1 - 2, 0), (n1 - 1, 0), (n1, 0), (0, c1 - 1), (0, c1), (1, c1), (2, c1),
                    (3, c1)), k)
            k += 1
        if r == nrow + 4 and c == 2 and ncol % 8 == 0:
            corner(((n1, 0), (n1, c1), (0, c1 - 2), (0, c1 - 1), (0, c1), (1, c1 - 2), (1, c1 - 1),
                    (1, c1)), k)
            k += 1
        # 右上へ / sweep up and to the right
        while True:
            if r < nrow and c >= 0 and cw[r, c] < 0:
                utah(r, c, k)
                k += 1
            r -= 2
            c += 2
            if not (r >= 0 and c < ncol):
                break
        r += 1
        c += 3
        # 左下へ / sweep down and to the left
        while True:
            if r >= 0 and c < ncol and cw[r, c] < 0:
                utah(r, c, k)
                k += 1
            r += 2
            c -= 2
            if not (r < nrow and c >= 0):
                break
        r += 3
        c += 1
        if not (r < nrow or c < ncol):
            break
    cw.setflags(write=False)
    bit.setflags(write=False)
    return cw, bit, k


@functools.lru_cache(maxsize=None)
def _layout(rows: int, cols: int):
    """記号 1 種の固定情報(機能 module・符号語の地図・ブロック構成)/ per-size static layout."""
    spec = _SPEC.get((rows, cols))
    if spec is None:
        raise ValueError("unsupported Data Matrix size %dx%d" % (rows, cols))
    _, _, nv, nh, n_data, n_ec, nb = spec
    rh = (rows - 2 * nv) // nv
    rw = (cols - 2 * nh) // nh
    nrow, ncol = nv * rh, nh * rw
    cw, bit, n_cw = _placement(nrow, ncol)
    if n_cw != n_data + n_ec:
        raise RuntimeError("placement of %dx%d produced %d codewords, expected %d"
                           % (rows, cols, n_cw, n_data + n_ec))
    # 写像行列の行・列 → 記号の行・列 / mapping row/col -> symbol row/col
    map_r = np.array([(r // rh) * (rh + 2) + 1 + r % rh for r in range(nrow)])
    map_c = np.array([(c // rw) * (rw + 2) + 1 + c % rw for c in range(ncol)])
    li = np.arange(rows) % (rh + 2)
    lj = np.arange(cols) % (rw + 2)
    LI, LJ = np.meshgrid(li, lj, indexing="ij")
    fmask = (LI == 0) | (LI == rh + 1) | (LJ == 0) | (LJ == rw + 1)
    fexp = np.zeros((rows, cols), np.uint8)
    fexp[(LI == 0) & (LJ % 2 == 0)] = 1                 # 上のクロック / top clock
    fexp[(LJ == rw + 1) & (LI % 2 == 1)] = 1            # 右のクロック / right clock
    fexp[LJ == 0] = 1                                    # L の縦 / solid left
    fexp[LI == rh + 1] = 1                               # L の横 / solid bottom
    cw_sym = np.full((rows, cols), -1, np.int16)
    bit_sym = np.full((rows, cols), -1, np.int8)
    cw_sym[np.ix_(map_r, map_c)] = cw
    bit_sym[np.ix_(map_r, map_c)] = bit
    # 固定の右下 2x2(余り)/ fixed bottom-right corner when 4 bits are left over
    fixed_mask = np.zeros((rows, cols), bool)
    fixed_val = np.zeros((rows, cols), np.uint8)
    if cw[nrow - 1, ncol - 1] < 0:
        for (r, c), v in (((nrow - 1, ncol - 1), 1), ((nrow - 2, ncol - 2), 1),
                          ((nrow - 1, ncol - 2), 0), ((nrow - 2, ncol - 1), 0)):
            fixed_mask[map_r[r], map_c[c]] = True
            fixed_val[map_r[r], map_c[c]] = v
    blocks = []
    for b in range(nb):
        blocks.append((len(range(b, n_data, nb)), n_ec // nb))
    for a in (fmask, fexp, cw_sym, bit_sym, fixed_mask, fixed_val):
        a.setflags(write=False)
    return dict(rows=rows, cols=cols, nv=nv, nh=nh, rh=rh, rw=rw, n_data=n_data, n_ec=n_ec,
                nb=nb, blocks=blocks, map_r=map_r, map_c=map_c, fmask=fmask, fexp=fexp,
                cw=cw_sym, bit=bit_sym, fixed_mask=fixed_mask, fixed_val=fixed_val,
                f_idx=np.argwhere(fmask), f_val=fexp[fmask])


# ---------------------------------------------------------------------------------------------
# 符号化 / encodation
# ---------------------------------------------------------------------------------------------
def _to_bytes(text):
    if isinstance(text, (bytes, bytearray)):
        return bytes(text), bytes(text).decode("latin-1")
    if not isinstance(text, str):
        raise ValueError("dm_encode: text must be str or bytes, got %s" % type(text).__name__)
    try:
        return text.encode("latin-1"), text
    except UnicodeEncodeError as exc:
        raise ValueError("dm_encode: text must contain only characters U+0000..U+00FF "
                         "(ECI is not supported): %s" % exc) from None


def _enc_ascii(data: bytes):
    out = []
    i, n = 0, len(data)
    while i < n:
        c = data[i]
        if 48 <= c <= 57 and i + 1 < n and 48 <= data[i + 1] <= 57:
            out.append(130 + (c - 48) * 10 + data[i + 1] - 48)    # 数字 2 桁 / digit pair
            i += 2
        elif c < 128:
            out.append(c + 1)
            i += 1
        else:
            out.extend((235, c - 128 + 1))                         # 上位シフト / upper shift
            i += 1
    return out


def _c40_values(c: int, text_mode: bool):
    """1 文字の C40 / Text の値の並び / C40 or Text values of one byte."""
    if c >= 128:
        return [1, 30] + _c40_values(c - 128, text_mode)
    if c == 32:
        return [3]
    if 48 <= c <= 57:
        return [c - 48 + 4]
    if text_mode and 97 <= c <= 122:
        return [c - 97 + 14]
    if not text_mode and 65 <= c <= 90:
        return [c - 65 + 14]
    if c < 32:
        return [0, c]
    if c in _SHIFT2:
        return [1, _SHIFT2.index(c)]
    if text_mode:
        return [2, _TEXT_SHIFT3.index(c)]
    return [2, c - 96]


def _enc_c40_parts(data: bytes, text_mode: bool):
    """(3 値ずつの組の符号語, ASCII で書く尻尾の符号語) / (triplet codewords, ASCII tail)."""
    chars = [_c40_values(c, text_mode) for c in data]
    tail = []
    while chars:
        total = sum(len(v) for v in chars)
        if total % 3 != 1:
            break
        tail.insert(0, data[len(chars) - 1])    # 1 値だけ余る → 最後の文字を ASCII へ
        chars.pop()
    vals = [v for vs in chars for v in vs]
    if len(vals) % 3 == 2:
        vals.append(0)                           # Shift 1 で埋める / pad with Shift 1
    cws = []
    for i in range(0, len(vals), 3):
        v = 1600 * vals[i] + 40 * vals[i + 1] + vals[i + 2] + 1
        cws.extend((v >> 8, v & 0xFF))
    return cws, _enc_ascii(bytes(tail))


def _enc_fit(data: bytes, mode: str, cap: int):
    """容量 ``cap`` に収まる符号語列(パッド前)、収まらなければ None。"""
    if mode == "ascii":
        cws = _enc_ascii(data)
    elif mode in ("c40", "text"):
        trip, tail = _enc_c40_parts(data, mode == "text")
        head = [230 if mode == "c40" else 239] + trip
        if not tail and len(head) == cap:
            cws = head                                   # 記号の終わり = 暗黙の解除
        elif len(tail) == 1 and len(head) + 1 == cap:
            cws = head + tail                            # 1 語だけ残れば ASCII に戻る
        else:
            cws = head + [254] + tail
    elif mode == "base256":
        n = len(data)
        if n == 0:
            return []           # 長さ 0 は「記号の終わりまで」の意味なので latch しない
        if n <= 249:            # (length 0 means "to the end of the symbol": never latch)
            field = [n]
        elif n <= 1555:
            field = [n // 250 + 249, n % 250]
        else:
            return None
        raw = field + list(data)
        cws = [231]
        for v in raw:
            pos = len(cws) + 1
            r = v + ((149 * pos) % 255) + 1
            cws.append(r if r <= 255 else r - 256)
    else:
        raise ValueError("dm_encode: encodation must be one of %s or 'auto', got %r"
                         % (_ENCODATIONS, mode))
    return cws if len(cws) <= cap else None


def _pad(cws, cap):
    out = list(cws)
    if len(out) < cap:
        out.append(129)
    while len(out) < cap:
        pos = len(out) + 1
        v = 129 + ((149 * pos) % 253) + 1
        out.append(v if v <= 254 else v - 254)
    return out


def _interleave_ec(L, data_cw):
    """ブロックごとに RS を付けて送出順に並べる / RS per block, interleaved as transmitted."""
    nb, n_data, n_ec = L["nb"], L["n_data"], L["n_ec"]
    ec_per = n_ec // nb
    out = list(data_cw) + [0] * n_ec
    for b in range(nb):
        ec = rs_encode(DM_FIELD, data_cw[b::nb], ec_per, fcr=1)
        for j, v in enumerate(ec):
            out[n_data + j * nb + b] = v
    return out


def _render(L, codewords):
    """符号語列 → module 行列(機能パターン込み)/ codewords -> full module matrix."""
    vals = np.asarray(codewords, np.int32)
    m = L["fexp"].copy()
    m[~L["fmask"]] = 0
    sel = L["cw"] >= 0
    m[sel] = (vals[L["cw"][sel]] >> (7 - L["bit"][sel].astype(np.int32))) & 1
    m[L["fixed_mask"]] = L["fixed_val"][L["fixed_mask"]]
    return m.astype(np.uint8)


def _symbol_from_data_codewords(data_cw, rows: int, cols: int):
    """データ符号語(パッド込み)から記号を組む(検証用)/ build a symbol from final data codewords."""
    L = _layout(rows, cols)
    data_cw = [int(v) for v in data_cw]
    if len(data_cw) != L["n_data"] or any(not 0 <= v <= 255 for v in data_cw):
        raise ValueError("need exactly %d data codewords in 0..255 for %dx%d"
                         % (L["n_data"], rows, cols))
    cws = _interleave_ec(L, data_cw)
    return _render(L, cws), cws


def _sizes_for_shape(shape):
    if shape == "square":
        return [s for s in DM_SIZES if s[0] == s[1]]
    if shape in ("rect", "rectangle"):
        return [s for s in DM_SIZES if s[0] != s[1]]
    if shape == "any":
        return list(DM_SIZES)
    raise ValueError("dm_encode: shape must be 'square', 'rectangle' or 'any', got %r" % (shape,))


def dm_encode(text, size=None, shape: str = "square", encodation: str = "auto") -> dict:
    """文字列を Data Matrix ECC200 のモジュール格子と符号語の対応に符号化する(``table``)。

    Encode ``text`` (str with code points <= 255, or bytes) as an ECC200 symbol.

    Parameters
    ----------
    text : str | bytes
        U+0000..U+00FF のみ(Latin-1 の 1 バイト)。ECI は扱わない。
    size : None | int | (rows, cols)
        None なら ``shape`` の中で収まる最小の記号。int は正方形 N×N。
    shape : {"square", "rectangle", "any"}
        ``size`` が None のときの候補。"rect" も "rectangle" と同じ。
    encodation : {"auto", "ascii", "c40", "text", "base256"}
        "auto" は各記号の大きさで ascii → c40 → text → base256 の順に試し、
        最小の記号に収まる最初のもの(文書全体を 1 つの符号化で書く。区間ごとの最適化はしない)。

    Returns
    -------
    dict
        ``modules`` (R, C) uint8 1 = 暗(L 字・クロック・領域の区切り込み)、``rows``, ``cols``,
        ``text``, ``encodation``, ``blocks`` [(n_data, n_ec)], ``n_data_codewords``,
        ``n_ec_codewords``, ``function_mask`` (R, C) bool, ``fixed_mask``(右下の固定 2x2),
        ``codeword_index`` (R, C) int16(送出順の符号語番号、機能 module と固定角は -1)、
        ``bit_index``(0 = 最上位ビット、-1 = 対象外)、``codewords``(送出順の全符号語)、
        ``data_codewords``(パッド込み)。
    """
    data, text_str = _to_bytes(text)
    if not isinstance(encodation, str):
        raise ValueError("dm_encode: encodation must be a string")
    enc = encodation.lower()
    modes = list(_ENCODATIONS) if enc == "auto" else [enc]
    if enc != "auto" and enc not in _ENCODATIONS:
        raise ValueError("dm_encode: encodation must be one of %s or 'auto', got %r"
                         % (_ENCODATIONS, encodation))
    if size is None:
        cands = _sizes_for_shape(shape)
    else:
        if isinstance(size, (int, np.integer)) and not isinstance(size, bool):
            rc = (int(size), int(size))
        elif isinstance(size, (tuple, list)) and len(size) == 2 and all(
                isinstance(v, (int, np.integer)) and not isinstance(v, bool) for v in size):
            rc = (int(size[0]), int(size[1]))
        else:
            raise ValueError("dm_encode: size must be None, an int or a (rows, cols) pair, got %r"
                             % (size,))
        if rc not in _SPEC:
            raise ValueError("dm_encode: unsupported size %dx%d (supported: %s)"
                             % (rc[0], rc[1], ", ".join("%dx%d" % s for s in DM_SIZES)))
        cands = [rc]
    chosen = None
    for rc in cands:
        cap = _SPEC[rc][4]
        for mode in modes:
            cws = _enc_fit(data, mode, cap)
            if cws is not None:
                chosen = (rc, mode, cws)
                break
        if chosen:
            break
    if chosen is None:
        raise ValueError("dm_encode: %d bytes do not fit in the %s (encodation %r)"
                         % (len(data), "requested size" if size is not None else
                            "largest %s symbol" % shape, encodation))
    (rows, cols), mode, cws = chosen
    L = _layout(rows, cols)
    data_cw = _pad(cws, L["n_data"])
    codewords = _interleave_ec(L, data_cw)
    modules = _render(L, codewords)
    return {
        "modules": modules, "rows": rows, "cols": cols, "text": text_str, "encodation": mode,
        "blocks": list(L["blocks"]), "n_data_codewords": L["n_data"],
        "n_ec_codewords": L["n_ec"], "function_mask": L["fmask"].copy(),
        "fixed_mask": L["fixed_mask"].copy(), "codeword_index": L["cw"].copy(),
        "bit_index": L["bit"].copy(), "codewords": codewords, "data_codewords": data_cw,
    }


# ---------------------------------------------------------------------------------------------
# データの復号 / data decoding
# ---------------------------------------------------------------------------------------------
def _unrand255(v, pos):
    t = v - (((149 * pos) % 255) + 1)
    return t if t >= 0 else t + 256


def _dec_c40(cws, i, out, text_mode):
    n = len(cws)
    shift, upper = 0, False
    while i < n:
        if n - i == 1:
            return i                      # 1 語だけ残る → ASCII / single codeword left: ASCII
        if cws[i] == 254:
            return i + 1
        v = cws[i] * 256 + cws[i + 1] - 1
        i += 2
        if not 0 <= v < 64000:
            raise DMDecodeError("invalid C40/Text codeword pair")
        for x in (v // 1600, (v // 40) % 40, v % 40):
            if shift == 0:
                if x < 3:
                    shift = x + 1
                    continue
                if x == 3:
                    ch = 32
                elif x < 14:
                    ch = 48 + x - 4
                else:
                    ch = (97 if text_mode else 65) + x - 14
            elif shift == 1:
                ch = x
            elif shift == 2:
                shift = 0
                if x < 27:
                    ch = _SHIFT2[x]
                elif x == 27:
                    ch = 29                # FNC1 → GS
                elif x == 30:
                    upper = True
                    continue
                else:
                    raise DMDecodeError("invalid C40/Text shift-2 value %d" % x)
            else:
                if text_mode:
                    if x >= 32:
                        raise DMDecodeError("invalid Text shift-3 value %d" % x)
                    ch = _TEXT_SHIFT3[x]
                else:
                    ch = 96 + x
            shift = 0
            if upper:
                ch += 128
                upper = False
            if ch > 255:
                raise DMDecodeError("C40/Text value out of range")
            out.append(ch)
    return i


def _dec_x12(cws, i, out):
    n = len(cws)
    while i < n:
        if n - i == 1:
            return i
        if cws[i] == 254:
            return i + 1
        v = cws[i] * 256 + cws[i + 1] - 1
        i += 2
        if not 0 <= v < 64000:
            raise DMDecodeError("invalid X12 codeword pair")
        for x in (v // 1600, (v // 40) % 40, v % 40):
            if x == 0:
                out.append(13)
            elif x == 1:
                out.append(42)
            elif x == 2:
                out.append(62)
            elif x == 3:
                out.append(32)
            elif x < 14:
                out.append(48 + x - 4)
            else:
                out.append(65 + x - 14)
    return i


def _dec_edifact(cws, i, out):
    n = len(cws)
    while i < n:
        if n - i <= 2:
            return i                     # 2 語以下 → ASCII / <= 2 codewords left: ASCII
        w = (cws[i] << 16) | (cws[i + 1] << 8) | cws[i + 2]
        for k in range(4):
            x = (w >> (18 - 6 * k)) & 0x3F
            if x == 0x1F:                # 解除 / unlatch: drop the rest of this byte
                return i + ((k + 1) * 6 + 7) // 8
            out.append(x if x & 0x20 else x | 0x40)
        i += 3
    return i


def _dec_base256(cws, i, out):
    n = len(cws)
    if i >= n:
        raise DMDecodeError("Base256 segment without length")
    d1 = _unrand255(cws[i], i + 1)
    i += 1
    if d1 == 0:
        count = n - i
    elif d1 < 250:
        count = d1
    else:
        if i >= n:
            raise DMDecodeError("truncated Base256 length")
        count = 250 * (d1 - 249) + _unrand255(cws[i], i + 1)
        i += 1
    if i + count > n:
        raise DMDecodeError("Base256 length %d runs past the data codewords" % count)
    for _ in range(count):
        out.append(_unrand255(cws[i], i + 1))
        i += 1
    return i


def _decode_data(cws):
    """データ符号語 → (文字列, 使った符号化の並び)/ data codewords -> (text, encodations)."""
    out = []
    modes = []
    upper = False
    prefix, suffix = "", ""
    i, n = 0, len(cws)
    while i < n:
        c = cws[i]
        i += 1
        if c == 0:
            raise DMDecodeError("codeword 0 is not valid in ASCII encodation")
        if c <= 128:
            out.append(c - 1 + (128 if upper else 0))
            upper = False
            _note(modes, "ascii")
        elif c == 129:
            break                                      # パッド = データの終わり / pad
        elif c <= 229:
            d = c - 130
            out.extend((48 + d // 10, 48 + d % 10))
            _note(modes, "ascii")
        elif c == 230:
            i = _dec_c40(cws, i, out, False)
            _note(modes, "c40")
        elif c == 231:
            i = _dec_base256(cws, i, out)
            _note(modes, "base256")
        elif c == 232:
            if i != 1:
                out.append(29)                          # FNC1 → GS
            _note(modes, "fnc1")
        elif c == 235:
            upper = True
        elif c in (236, 237):
            if i != 1:
                raise DMDecodeError("Macro 05/06 is only valid as the first codeword")
            prefix = "[)>\x1e05\x1d" if c == 236 else "[)>\x1e06\x1d"
            suffix = "\x1e\x04"
        elif c == 238:
            i = _dec_x12(cws, i, out)
            _note(modes, "x12")
        elif c == 239:
            i = _dec_c40(cws, i, out, True)
            _note(modes, "text")
        elif c == 240:
            i = _dec_edifact(cws, i, out)
            _note(modes, "edifact")
        elif c == 254 and i == n:
            break                                      # 末尾の解除は無害 / harmless final unlatch
        elif c in (233, 234, 241):
            raise DMDecodeError("unsupported Data Matrix feature (codeword %d: structured "
                                "append / reader programming / ECI)" % c)
        else:
            raise DMDecodeError("invalid ASCII codeword %d" % c)
    return prefix + "".join(map(chr, out)) + suffix, modes


def _note(modes, m):
    if not modes or modes[-1] != m:
        modes.append(m)


# ---------------------------------------------------------------------------------------------
# module 行列の復号 / decoding a module matrix
# ---------------------------------------------------------------------------------------------
def _transform(g, k, mirrored):
    """正規化 = rot90(fliplr(g) if mirrored else g, k) / the normalising transform."""
    return np.rot90(np.fliplr(g) if mirrored else g, k)


def _check_modules(modules):
    a = np.asarray(modules)
    if a.ndim != 2:
        raise ValueError("dm_decode_modules: modules must be a 2-D array, got shape %s" % (a.shape,))
    if a.dtype == bool:
        a = a.astype(np.uint8)
    if not (np.issubdtype(a.dtype, np.integer) or np.issubdtype(a.dtype, np.floating)):
        raise ValueError("dm_decode_modules: modules must be numeric 0/1, got dtype %s" % a.dtype)
    if np.issubdtype(a.dtype, np.floating) and not np.all(np.isfinite(a)):
        raise ValueError("dm_decode_modules: modules contain NaN or inf")
    if a.size and not np.all((a == 0) | (a == 1)):
        raise ValueError("dm_decode_modules: modules must contain only 0 and 1")
    return a.astype(np.uint8)


def _decode_oriented(g, L):
    """向きを決めた記号を RS 訂正して復号 / RS-correct and decode a normalised grid."""
    sel = L["cw"] >= 0
    n_total = L["n_data"] + L["n_ec"]
    raw = np.zeros(n_total, np.int64)
    np.add.at(raw, L["cw"][sel].astype(np.int64),
              g[sel].astype(np.int64) << (7 - L["bit"][sel].astype(np.int64)))
    raw = [int(v) for v in raw]
    nb, n_data = L["nb"], L["n_data"]
    ec_per = L["n_ec"] // nb
    corrected = list(raw)
    block_corr = []
    for b in range(nb):
        di = list(range(b, n_data, nb))
        ei = [n_data + j * nb + b for j in range(ec_per)]
        word = [raw[k] for k in di + ei]
        try:
            fixed, nfix = rs_decode(DM_FIELD, word, ec_per, fcr=1)
        except RSDecodeError as exc:
            raise DMDecodeError("Reed-Solomon block %d of %d is uncorrectable: %s"
                                % (b, nb, exc)) from None
        for k, v in zip(di + ei, fixed):
            corrected[k] = v
        block_corr.append(int(nfix))
    text, modes = _decode_data(corrected[:n_data])
    return raw, corrected, block_corr, text, modes


def dm_decode_modules(modules) -> dict:
    """Data Matrix のモジュール格子(L 字とクロック込み、0/1)を復号し、訂正語数を返す(``table``)。

    Decode an (R, C) 0/1 module matrix that includes the finder L and the clock track.
    The grid may be given in any of the 4 rotations, optionally mirrored; the
    orientation is found from the function pattern (solid L + clock) and, when the
    pattern alone is ambiguous (a square symbol and its anti-diagonal mirror share
    it), from which orientation passes Reed-Solomon.

    Returns
    -------
    dict
        ``text``, ``rows``, ``cols``, ``n_corrected``, ``block_corrected`` [int],
        ``block_ec`` [EC 語数], ``block_capacity`` [floor(n_ec/2)], ``finder_errors``
        (機能 module の不一致数), ``codeword_index``(正規化後の向き)、``rotation``
        (度、0/90/180/270)と ``mirrored``: 正規化 =
        ``np.rot90(np.fliplr(g) if mirrored else g, rotation // 90)``、``modules``(正規化後)、
        ``codewords_raw`` / ``codewords``(訂正前後、送出順)、``encodations``、
        ``fixed_errors``(右下固定 2x2 の不一致数、無ければ 0)。

    Raises
    ------
    ValueError
        2-D でない・0/1 以外・NaN。
    DMDecodeError
        どの向きでも対応する大きさにならない、機能パターンが崩れすぎ、RS 訂正不能、符号化の矛盾。
    """
    g0 = _check_modules(modules)
    cands = []
    for mirrored in (False, True):
        for k in range(4):
            g = _transform(g0, k, mirrored)
            if (g.shape[0], g.shape[1]) not in _SPEC:
                continue
            L = _layout(g.shape[0], g.shape[1])
            fe = int(np.count_nonzero(g[L["fmask"]] != L["fexp"][L["fmask"]]))
            cands.append((fe, mirrored, k, g, L))
    if not cands:
        raise DMDecodeError("module matrix %dx%d is not a Data Matrix ECC200 size in any orientation"
                            % g0.shape)
    cands.sort(key=lambda t: (t[0], t[1], t[2]))
    n_func = int(cands[0][4]["fmask"].sum())
    limit = max(2, int(0.25 * n_func))
    last = None
    for fe, mirrored, k, g, L in cands:
        if fe > limit:
            break
        try:
            raw, corr, bc, text, modes = _decode_oriented(g, L)
        except DMDecodeError as exc:
            last = exc
            continue
        nb = L["nb"]
        ec_per = L["n_ec"] // nb
        fm = L["fixed_mask"]
        return {
            "text": text, "rows": L["rows"], "cols": L["cols"], "n_corrected": int(sum(bc)),
            "block_corrected": bc, "block_ec": [ec_per] * nb,
            "block_capacity": [ec_per // 2] * nb, "finder_errors": fe,
            "fixed_errors": int(np.count_nonzero(g[fm] != L["fixed_val"][fm])),
            "codeword_index": L["cw"].copy(), "bit_index": L["bit"].copy(),
            "function_mask": L["fmask"].copy(), "rotation": 90 * k, "mirrored": bool(mirrored),
            "modules": np.ascontiguousarray(g), "codewords_raw": raw, "codewords": corr,
            "encodations": modes, "blocks": list(L["blocks"]),
        }
    if last is None:
        raise DMDecodeError("finder pattern not found: %d of %d function modules wrong (limit %d)"
                            % (cands[0][0], n_func, limit))
    raise last


# ---------------------------------------------------------------------------------------------
# 画像からの位置決め / locating in an image
# ---------------------------------------------------------------------------------------------
def _check_image(image, op):
    a = np.asarray(image)
    if a.ndim != 2:
        raise ValueError("%s: image must be a 2-D grey array, got shape %s" % (op, a.shape))
    if not (np.issubdtype(a.dtype, np.number) or a.dtype == bool) or np.iscomplexobj(a):
        raise ValueError("%s: image must be real numeric, got dtype %s" % (op, a.dtype))
    a = a.astype(np.float64)
    if not np.all(np.isfinite(a)):
        raise ValueError("%s: image contains NaN or inf" % op)
    if min(a.shape) < 8:
        raise ValueError("%s: image too small %s" % (op, a.shape))
    return a


def _otsu(a):
    lo, hi = float(a.min()), float(a.max())
    if hi - lo < 1e-9:
        return None
    hist, edges = np.histogram(a, bins=256, range=(lo, hi))
    p = hist.astype(np.float64) / hist.sum()
    mids = 0.5 * (edges[:-1] + edges[1:])
    w0 = np.cumsum(p)
    m0 = np.cumsum(p * mids)
    mt = m0[-1]
    w1 = 1.0 - w0
    with np.errstate(divide="ignore", invalid="ignore"):
        sb = (mt * w0 - m0) ** 2 / (w0 * w1)
    sb[~np.isfinite(sb)] = -1
    k = int(np.argmax(sb))
    return float(edges[k + 1])


def _global_threshold(a):
    """Otsu で初期分割し、暗/明の平均の中点へ 2 回寄せた大域閾値(isodata)。

    Otsu alone is unsafe on few-level images: with a large light background and
    sharp, pixel-aligned dots (levels ink / near-ink / partial / substrate) it can
    land just above the ink level, so only fully inked pixels count as dark, edges
    move ~1 px inward and module-centre samples sit on the threshold. The midpoint
    of the class means (refined twice) is the conventional global threshold and
    keeps partial-coverage pixels on the side they are nearer to.
    """
    t = _otsu(a)
    if t is None:
        return None
    for _ in range(2):
        d, l = a[a < t], a[a >= t]
        if d.size == 0 or l.size == 0:
            break
        t = 0.5 * (float(d.mean()) + float(l.mean()))
    return t


def _homography(src, dst):
    """4 点以上の対応から射影変換(Hartley 正規化 DLT)/ normalised DLT homography src -> dst."""
    src = np.asarray(src, float)
    dst = np.asarray(dst, float)

    def norm(p):
        c = p.mean(0)
        s = np.sqrt(2) / max(np.sqrt(((p - c) ** 2).sum(1)).mean(), 1e-12)
        return np.array([[s, 0, -s * c[0]], [0, s, -s * c[1]], [0, 0, 1]])

    Ts, Td = norm(src), norm(dst)
    ps = (Ts @ np.c_[src, np.ones(len(src))].T).T
    pd = (Td @ np.c_[dst, np.ones(len(dst))].T).T
    A = []
    for (x, y, _), (u, v, _) in zip(ps, pd):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y, -u])
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y, -v])
    _, _, vt = np.linalg.svd(np.asarray(A))
    H = vt[-1].reshape(3, 3)
    H = np.linalg.inv(Td) @ H @ Ts
    return H / H[2, 2]


def _apply_h(H, xy):
    xy = np.asarray(xy, float)
    p = np.c_[xy, np.ones(len(xy))] @ H.T
    return p[:, :2] / p[:, 2:3]


def _sample_at(img, xy):
    return ndimage.map_coordinates(img, [xy[..., 1].ravel(), xy[..., 0].ravel()], order=1,
                                   mode="nearest").reshape(xy.shape[:-1])


def _initial_quad(pts):
    """暗画素の凸包に内接する面積最大に近い四角形 / near max-area quadrilateral in the hull."""
    from scipy.spatial import ConvexHull, QhullError
    try:
        hull = ConvexHull(pts)
    except (QhullError, ValueError):
        return None
    hv = pts[hull.vertices]
    h = len(hv)
    if h < 4:
        return None
    d2 = ((hv[:, None, :] - hv[None, :, :]) ** 2).sum(-1)
    a, b = np.unravel_index(int(np.argmax(d2)), d2.shape)
    a, b = int(min(a, b)), int(max(a, b))

    def far(i0, i1, idxs):
        if not idxs:
            return None
        p, q = hv[i0], hv[i1]
        d = q - p
        cr = np.abs(d[0] * (hv[idxs, 1] - p[1]) - d[1] * (hv[idxs, 0] - p[0]))
        return idxs[int(np.argmax(cr))]

    c1 = far(a, b, list(range(a + 1, b)))
    c2 = far(b, a, [i % h for i in range(b + 1, a + h)])
    if c1 is None or c2 is None:
        return None
    idx = [a, c1, b, c2]
    for _ in range(3):
        for k in range(4):
            prev, nxt = idx[k - 1], idx[(k + 1) % 4]
            between = []
            i = (prev + 1) % h
            while i != nxt:
                between.append(i)
                i = (i + 1) % h
            best = far(prev, nxt, between)
            if best is not None:
                idx[k] = best
    # 各辺 = 角の間の凸包の辺のうち最長のもの(右上の明 module で欠けた角を交点で補う)
    # each side = the longest hull edge between its two corners; intersecting them restores
    # the corner cut off by the light top-right clock module
    lines = []
    for k in range(4):
        i, end = idx[k], idx[(k + 1) % 4]
        best, bl = None, -1.0
        while i != end:
            j = (i + 1) % h
            ln = float(np.hypot(*(hv[j] - hv[i])))
            if ln > bl:
                best, bl = (hv[i], hv[j]), ln
            i = j
        if best is None or bl < 2:
            return hv[idx].astype(float)
        lines.append((best[0].astype(float), (best[1] - best[0]) / bl))
    corners = []
    for k in range(4):
        (ca, da), (cb, db) = lines[k - 1], lines[k]
        M = np.array([da, -db]).T
        if abs(np.linalg.det(M)) < 1e-3:
            return hv[idx].astype(float)
        ab = np.linalg.solve(M, cb - ca)
        corners.append(ca + ab[0] * da)
    return np.asarray(corners)


def _fit_line_outer(E, nrm, tol=0.8):
    """外側の縁の点に直線を当てる(内側へ外れた点を繰り返し捨てる)/ outer-edge robust line."""
    keep = np.ones(len(E), bool)
    c = d = None
    for _ in range(8):
        if keep.sum() < 4:
            return None
        P = E[keep]
        c = P.mean(0)
        _, _, vt = np.linalg.svd(P - c)
        d = vt[0]
        n = np.array([-d[1], d[0]])
        if n @ nrm < 0:
            n = -n
        r = (E - c) @ n
        # 当てた線より内側へ tol 以上の点を捨てる / drop points well inside the fitted edge
        new = r > -tol
        if np.array_equal(new, keep):
            break
        keep = new
    return c, d


def _refine_quad(img, t, quad, passes=2, ns=48):
    """濃淡の閾値横断で 4 辺を直線当てし、その交点を角にする / sub-pixel edge lines -> corners."""
    for _ in range(passes):
        cen = quad.mean(0)
        lines = []
        for k in range(4):
            p0, p1 = quad[k], quad[(k + 1) % 4]
            dv = p1 - p0
            Ls = float(np.hypot(*dv))
            if Ls < 4:
                return None
            u = dv / Ls
            nrm = np.array([-u[1], u[0]])
            if nrm @ (0.5 * (p0 + p1) - cen) < 0:
                nrm = -nrm
            s_in = float(np.clip(0.25 * Ls, 4.0, 80.0))
            s = np.arange(2.5, -s_in, -0.25)
            ts = np.linspace(0.06, 0.94, ns)
            base = p0 + ts[:, None] * dv
            P = base[:, None, :] + s[None, :, None] * nrm
            v = _sample_at(img, P)
            dark = v < t
            first = np.argmax(dark, axis=1)
            ok = dark.any(1) & (first > 0)
            if ok.sum() < 6:
                return None
            r = np.nonzero(ok)[0]
            f = first[r]
            va, vb = v[r, f - 1], v[r, f]
            frac = np.clip((va - t) / np.maximum(va - vb, 1e-12), 0, 1)
            sc = s[f - 1] + frac * (s[f] - s[f - 1])
            E = base[r] + sc[:, None] * nrm
            fit = _fit_line_outer(E, nrm)
            if fit is None:
                return None
            lines.append(fit)
        corners = []
        for k in range(4):
            (ca, da), (cb, db) = lines[k - 1], lines[k]
            M = np.array([da, -db]).T
            if abs(np.linalg.det(M)) < 1e-6:
                return None
            ab = np.linalg.solve(M, cb - ca)
            corners.append(ca + ab[0] * da)
        quad = np.asarray(corners)
    return quad


def _identify(img, t, quad, min_score):
    """どの角が L の角か・記号の大きさを機能パターンの一致率で決める / pick size + correspondence."""
    best = None
    unit = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], float)
    for d in (1, -1):
        for s0 in range(4):
            Q = np.array([quad[(s0 + d * k) % 4] for k in range(4)])
            # 単位正方形 → 画像を 1 回だけ解き、大きさごとに diag(1/C, 1/R) を掛ける
            # one unit-square homography per correspondence; per size H = Hu diag(1/C, 1/R, 1)
            Hu = _homography(unit, Q)
            top = np.hypot(*(Q[1] - Q[0]))
            left = np.hypot(*(Q[3] - Q[0]))
            for rc in DM_SIZES:
                R, C = rc
                mx, my = top / C, left / R
                if min(mx, my) < 1.0 or not 0.5 <= mx / my <= 2.0:
                    continue
                L = _layout(R, C)
                fpts = L["f_idx"][:, ::-1] + 0.5       # (x, y) of function module centres
                H = Hu @ np.diag([1.0 / C, 1.0 / R, 1.0])
                H = H / H[2, 2]
                v = _sample_at(img, _apply_h(H, fpts))
                score = float(np.mean((v < t) == (L["f_val"] == 1)))
                a = Q[1] - Q[0]
                b = Q[3] - Q[0]
                hand = 1 if a[0] * b[1] - a[1] * b[0] > 0 else 0
                key = (round(score, 9), hand, -R * C)
                if best is None or key > best[0]:
                    best = (key, score, H, Q, R, C, 0.5 * (mx + my))
    if best is None or best[1] < min_score:
        return None
    _, score, H, Q, R, C, mpx = best
    return {"homography": H, "rows": R, "cols": C, "corners": Q[:, ::-1].copy(),
            "module_px": float(mpx), "score": score, "threshold": float(t)}


_RADII = (1.0, 2.0, 3.0, 4.5, 6.5)


def _iter_candidates(img, min_score=0.8):
    """位置候補を(膨張半径の小さい順に)生成 / yield located candidates, smallest radius first."""
    t = _global_threshold(img)
    if t is None:
        return
    dark = img < t
    nd = int(dark.sum())
    if nd < 16 or nd > dark.size - 16:
        return
    dist = ndimage.distance_transform_edt(~dark)
    seen = []
    H_, W_ = img.shape
    for rad in _RADII:
        grown = dist <= rad
        lab, n = ndimage.label(grown, structure=np.ones((3, 3), bool))
        if n == 0:
            continue
        counts = np.bincount(lab[dark], minlength=n + 1)
        counts[0] = 0
        for l in np.argsort(counts)[::-1][:2]:
            if counts[l] < 16:
                break
            rr, cc = np.nonzero(dark & (lab == l))
            if rr.min() <= 0 or cc.min() <= 0 or rr.max() >= H_ - 1 or cc.max() >= W_ - 1:
                continue                                 # 枠に触れる = 背景 / touches the border
            key = (rr.min(), rr.max(), cc.min(), cc.max(), len(rr))
            if key in seen:
                continue
            seen.append(key)
            q0 = _initial_quad(np.c_[cc, rr].astype(float))
            if q0 is None:
                continue
            q = _refine_quad(img, t, q0)
            if q is None:
                continue
            if not (np.all(np.isfinite(q)) and np.all(q > -0.25 * max(H_, W_))
                    and np.all(q < 1.25 * max(H_, W_))):
                continue
            cand = _identify(img, t, q, min_score)
            if cand is not None:
                yield cand


def dm_locate(image) -> dict:
    """画像から Data Matrix を見つけ、モジュール空間 → 画像の射影変換を推定する(``table``)。

    Locate a dark-on-light ECC200 symbol (quiet zone >= 1 module). Global
    binarisation (Otsu start, then the midpoint of the dark/light means), dark pixels grouped after a distance-based closing at several
    radii (so separated dot-peen dots join), near max-area quadrilateral in the
    convex hull, sub-pixel edge lines (grey-level threshold crossings, inward
    outliers from the clock gaps trimmed), corners = line intersections, then the
    size and which corner is the L corner are chosen by the agreement of the
    sampled function pattern (finder + clock + alignment) for every supported size
    and corner correspondence.

    Returns
    -------
    dict
        ``homography`` 3x3(module 空間 [x=列, y=行, 1] → 画像 [列, 行, w])、``rows``, ``cols``,
        ``corners`` (4, 2) 画素の (行, 列)、順は module 空間の (0,0), (C,0), (C,R), (0,R)、
        ``module_px``, ``score``(機能パターンの一致率), ``threshold``(大域閾値 / global threshold)。

    Raises
    ------
    ValueError
        2-D でない・NaN/inf・小さすぎる。
    DMDecodeError
        記号が見つからない。
    """
    img = _check_image(image, "dm_locate")
    best = None
    for cand in _iter_candidates(img):
        if best is None or cand["score"] > best["score"]:
            best = cand
        if best["score"] >= 0.97:
            break
    if best is None:
        raise DMDecodeError("dm_locate: no Data Matrix finder pattern found")
    return best


def dm_sample(image, located=None) -> dict:
    """Data Matrix のモジュール中心の反射率を双一次補間で取り、大域しきい値で 2 値化する(``table``)。

    Sample every module centre (bilinear) through the located homography and
    threshold globally at the midpoint of the dark and light means (initial split
    at the midpoint of the 5th/95th percentiles, then two mean-midpoint updates).

    Returns ``reflectance`` (R, C), ``modules`` (R, C) uint8 dark = 1,
    ``threshold``, ``homography``, ``centers`` (R, C, 2) px (row, col).
    """
    img = _check_image(image, "dm_sample")
    if located is None:
        located = dm_locate(img)
    if not isinstance(located, dict) or "homography" not in located:
        raise ValueError("dm_sample: located must be a dict from dm_locate")
    H = np.asarray(located["homography"], float)
    R, C = int(located["rows"]), int(located["cols"])
    if H.shape != (3, 3) or not np.all(np.isfinite(H)) or (R, C) not in _SPEC:
        raise ValueError("dm_sample: invalid located dict (homography 3x3 and a supported size)")
    jj, ii = np.meshgrid(np.arange(C) + 0.5, np.arange(R) + 0.5)
    xy = _apply_h(H, np.c_[jj.ravel(), ii.ravel()]).reshape(R, C, 2)
    refl = _sample_at(img, xy)
    v = refl.ravel()
    lo, hi = np.percentile(v, [5, 95])
    thr = 0.5 * (lo + hi)
    for _ in range(2):
        d, l = v[v < thr], v[v >= thr]
        if len(d) == 0 or len(l) == 0:
            break
        thr = 0.5 * (d.mean() + l.mean())
    return {"reflectance": refl, "modules": (refl < thr).astype(np.uint8), "threshold": float(thr),
            "homography": H, "centers": xy[..., ::-1].copy()}


def _grid_affine(shape, k, mirrored):
    """正規化後の module 空間 → 標本化した格子の module 空間 / canonical -> sampled module space."""
    R0, C0 = shape
    I, J = np.indices(shape)
    Ic, Jc = _transform(I, k, mirrored), _transform(J, k, mirrored)
    R, C = Ic.shape
    src, dst = [], []
    for a, b in ((0, 0), (0, C - 1), (R - 1, C - 1), (R - 1, 0)):
        src.append((b + 0.5, a + 0.5))
        dst.append((Jc[a, b] + 0.5, Ic[a, b] + 0.5))
    return _homography(src, dst)


def dm_read(image) -> dict:
    """画像から Data Matrix を読む: 位置決め → 標本化 → 復号、明暗を反転して再試行(``table``)。

    Read a symbol from a grey image: locate + sample + decode, retrying on the
    inverted image (light-on-dark marks) — ``inverted`` reports which succeeded.
    The result holds every key of :func:`dm_decode_modules` plus ``homography``
    (for the normalised grid), ``reflectance`` (normalised orientation),
    ``threshold``, ``corners``, ``module_px``, ``locate_score``, ``inverted``,
    ``angle_deg`` (direction of the module +x axis in the image, degrees,
    atan2(d_row, d_col)) and ``image_mirrored`` (the symbol appears mirrored).
    """
    img = _check_image(image, "dm_read")
    last = None
    for inverted in (False, True):
        im = (img.max() + img.min()) - img if inverted else img
        for cand in _iter_candidates(im):
            samp = dm_sample(im, cand)
            try:
                dec = dm_decode_modules(samp["modules"])
            except DMDecodeError as exc:
                last = exc
                continue
            k, mir = dec["rotation"] // 90, dec["mirrored"]
            A = _grid_affine(samp["modules"].shape, k, mir)
            H = cand["homography"] @ A
            H = H / H[2, 2]
            R, C = dec["rows"], dec["cols"]
            c0 = _apply_h(H, np.array([[0.5 * C, 0.5 * R], [0.5 * C + 1, 0.5 * R],
                                       [0.5 * C, 0.5 * R + 1]]))
            ex, ey = c0[1] - c0[0], c0[2] - c0[0]
            corners = _apply_h(H, np.array([[0, 0], [C, 0], [C, R], [0, R]], float))
            out = dict(dec)
            out.update({
                "homography": H, "reflectance": _transform(samp["reflectance"], k, mir).copy(),
                "threshold": samp["threshold"], "corners": corners[:, ::-1].copy(),
                "module_px": cand["module_px"], "locate_score": cand["score"],
                "inverted": inverted, "angle_deg": float(np.degrees(np.arctan2(ex[1], ex[0]))),
                "image_mirrored": bool(ex[0] * ey[1] - ex[1] * ey[0] < 0),
            })
            return out
    if last is not None:
        raise DMDecodeError("dm_read: symbol found but not decodable: %s" % last)
    raise DMDecodeError("dm_read: no Data Matrix found (normal or inverted)")
