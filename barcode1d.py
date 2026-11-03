# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""1 次元バーコード —— 生成・走査線の復号・画像からの読み取り(numpy + scipy のみ)。

1-D bar codes for the symbol-reading family: encode (EAN-13 / UPC-A / Code 128 /
Code 39 / ITF), decode a scan reflectance profile, and read a symbol from a 2-D
image at any in-plane angle. The print-quality grade of the same profiles lives in
``symgrade.py``.

なぜ自前か / why self-implemented: 符号表は公開の表で、復号は「要素の幅 → 文字」の
表引きにすぎない。自前なら (1) 生成した既知の文字列が真値になり、(2) 印字品質の
**復号容易度(decodability)** に要る「各文字の判定の余裕」を復号の途中から取り出せる。
既存の読み取り器(zxing-cpp、Apache-2.0)は試験で**独立な第 2 の実装**として使う
(``tests/test_barcode1d.py``)。本モジュールは zxing を import しない。
The tables are public; with our own decoder (1) the encoded string is the truth and
(2) the per-character decode margins that the print-quality *decodability* needs come
out of the decoder itself. zxing-cpp is used only by the tests, as an independent
second implementation.

復号の方式 / decoding scheme:

* EAN-13 / UPC-A / Code 128 は **似た縁どうしの距離**(bar+space、space+bar の和)で
  文字を決める。印字のにじみ(バーが一様に太る)は和の中で打ち消し合うので、
  にじみに強い。EAN の 1/7・2/8 の組だけはバー幅の和で分ける。
  Edge-to-similar-edge measurements (sums of adjacent bar+space); uniform ink spread
  cancels in the sums. EAN's 1/7 and 2/8 pairs are separated by the bar-width sum.
* Code 39 / ITF は 2 値の幅(細 / 太)。文字ごとに太い要素の数が決まっている
  (Code 39 は 9 要素中 3 本、ITF は 5 要素中 2 本)ので、**幅の順位**で太を決める。
  Two-width symbologies: the number of wide elements per character is fixed, so the
  wide ones are chosen by rank, and the threshold margin gives the decodability.

座標の約束 / conventions: 画像は 2-D の float、0 = 黒、1 = 白(反射率)。バーは暗い。
走査線の要素幅は**モジュール(X 寸法)単位**。``widths`` は先頭がバーの交互の列。
Images are reflectance in [0, 1]; bars are dark. Element widths are in modules.

出典(公開文書のみ)/ sources (public only): GS1 General Specifications(EAN/UPC と
GS1-128 の構造、公開)/ R. C. Palmer, *The Bar Code Book*, 5th ed., 2007(各シンボル
体系の表と似た縁の復号)/ ISO/IEC 15417(Code 128)・16388(Code 39)・16390(ITF)・
15420(EAN/UPC)は**番号の参照だけ**で、本文は写していない(表は公開の解説と
zxing-cpp による往復の照合で確かめた)。
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "SYMBOLOGIES_1D", "Barcode1DError", "encode_barcode1d", "decode_barcode_profile",
    "read_barcode1d", "barcode_scan_profiles", "ean_check_digit",
]

SYMBOLOGIES_1D = ("ean13", "upca", "code128", "code39", "itf")


class Barcode1DError(ValueError):
    """読めなかった(どのシンボル体系にも一致しない)/ no symbology matched."""


# --------------------------------------------------------------------------- #
# 符号表 / code tables
# --------------------------------------------------------------------------- #
_EAN_L = ["0001101", "0011001", "0010011", "0111101", "0100011",
          "0110001", "0101111", "0111011", "0110111", "0001011"]
_EAN_R = ["".join("1" if c == "0" else "0" for c in s) for s in _EAN_L]
_EAN_G = [s[::-1] for s in _EAN_R]
_EAN_PARITY = ["LLLLLL", "LLGLGG", "LLGGLG", "LLGGGL", "LGLLGG",
               "LGGLLG", "LGGGLL", "LGLGLG", "LGLGGL", "LGGLGL"]


def _bits_to_runs(bits):
    runs, cur, n = [], bits[0], 0
    for b in bits:
        if b == cur:
            n += 1
        else:
            runs.append(n)
            cur, n = b, 1
    runs.append(n)
    return runs


# 1 文字 = 4 要素(左半分は space から始まる)/ 4 runs per character
_EAN_RUNS = {}
for _d in range(10):
    _EAN_RUNS[("L", _d)] = tuple(_bits_to_runs(_EAN_L[_d]))
    _EAN_RUNS[("G", _d)] = tuple(_bits_to_runs(_EAN_G[_d]))
    _EAN_RUNS[("R", _d)] = tuple(_bits_to_runs(_EAN_R[_d]))

# Code 128: 値 0..105 と停止(106)。要素は bar から始まる 6 本(停止は 7 本)、計 11(停止 13)。
_C128 = (
    "212222 222122 222221 121223 121322 131222 122213 122312 132212 221213 "
    "221312 231212 112232 122132 122231 113222 123122 123221 223211 221132 "
    "221231 213212 223112 312131 311222 321122 321221 312212 322112 322211 "
    "212123 212321 232121 111323 131123 131321 112313 132113 132311 211313 "
    "231113 231311 112133 112331 132131 113123 113321 133121 313121 211331 "
    "231131 213113 213311 213131 311123 311321 331121 312113 312311 332111 "
    "314111 221411 431111 111224 111422 121124 121421 141122 141221 112214 "
    "112412 122114 122411 142112 142211 241211 221114 413111 241112 134111 "
    "111242 121142 121241 114212 124112 124211 411212 421112 421211 212141 "
    "214121 412121 111143 111341 131141 114113 114311 411113 411311 113141 "
    "114131 311141 411131 211412 211214 211232 2331112"
).split()
_C128_RUNS = [tuple(int(c) for c in s) for s in _C128]
_C128_START_A, _C128_START_B, _C128_START_C, _C128_STOP = 103, 104, 105, 106
_C128_FNC1 = 102
# 似た縁の 4 つの和 → 値 / similar-edge key -> value
_C128_KEY = {}
for _v, _r in enumerate(_C128_RUNS[:106]):
    _k = (_r[0] + _r[1], _r[1] + _r[2], _r[2] + _r[3], _r[3] + _r[4])
    _C128_KEY.setdefault(_k, []).append(_v)

# Code 39: 9 要素(bar から、5 bar + 4 space)、太 3 本。'w' = 太。
_C39 = {
    "0": "nnnwwnwnn", "1": "wnnwnnnnw", "2": "nnwwnnnnw", "3": "wnwwnnnnn",
    "4": "nnnwwnnnw", "5": "wnnwwnnnn", "6": "nnwwwnnnn", "7": "nnnwnnwnw",
    "8": "wnnwnnwnn", "9": "nnwwnnwnn", "A": "wnnnnwnnw", "B": "nnwnnwnnw",
    "C": "wnwnnwnnn", "D": "nnnnwwnnw", "E": "wnnnwwnnn", "F": "nnwnwwnnn",
    "G": "nnnnnwwnw", "H": "wnnnnwwnn", "I": "nnwnnwwnn", "J": "nnnnwwwnn",
    "K": "wnnnnnnww", "L": "nnwnnnnww", "M": "wnwnnnnwn", "N": "nnnnwnnww",
    "O": "wnnnwnnwn", "P": "nnwnwnnwn", "Q": "nnnnnnwww", "R": "wnnnnnwwn",
    "S": "nnwnnnwwn", "T": "nnnnwnwwn", "U": "wwnnnnnnw", "V": "nwwnnnnnw",
    "W": "wwwnnnnnn", "X": "nwnnwnnnw", "Y": "wwnnwnnnn", "Z": "nwwnwnnnn",
    "-": "nwnnnnwnw", ".": "wwnnnnwnn", " ": "nwwnnnwnn", "*": "nwnnwnwnn",
    "$": "nwnwnwnnn", "/": "nwnwnnnwn", "+": "nwnnnwnwn", "%": "nnnwnwnwn",
}
_C39_INV = {v: k for k, v in _C39.items()}
_C39_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-. $/+%"

# ITF: 1 桁 = 5 要素、太 2 本。対の 1 桁目はバー、2 桁目は空白に入る。
_ITF = ["nnwwn", "wnnnw", "nwnnw", "wwnnn", "nnwnw",
        "wnwnn", "nwwnn", "nnnww", "wnnwn", "nwnwn"]
_ITF_INV = {v: k for k, v in enumerate(_ITF)}

#: 規格の推奨に沿った静寂域(モジュール数、左, 右)/ quiet zones in modules (left, right).
QUIET = {"ean13": (11, 7), "upca": (9, 9), "code128": (10, 10), "code39": (10, 10), "itf": (10, 10)}


# --------------------------------------------------------------------------- #
# 生成 / encoding
# --------------------------------------------------------------------------- #
def ean_check_digit(digits: str) -> int:
    """EAN/UPC の検査数字(右端の桁から重み 3, 1, 3, …、和を 10 の倍数に)/ EAN/UPC check digit."""
    if not isinstance(digits, str) or not digits.isdigit() or not digits.isascii():
        raise ValueError("ean_check_digit: digits must be a string of ASCII digits, got %r" % (digits,))
    s = 0
    for i, ch in enumerate(reversed(digits)):
        s += int(ch) * (3 if i % 2 == 0 else 1)
    return (10 - s % 10) % 10


def _encode_ean13(data: str):
    if len(data) == 12:
        data = data + str(ean_check_digit(data))
    elif len(data) == 13:
        if int(data[-1]) != ean_check_digit(data[:12]):
            raise ValueError("encode_barcode1d: EAN-13 check digit of %r should be %d"
                             % (data, ean_check_digit(data[:12])))
    else:
        raise ValueError("encode_barcode1d: EAN-13 needs 12 or 13 digits, got %d" % len(data))
    par = _EAN_PARITY[int(data[0])]
    runs = [1, 1, 1]                        # 開始ガード 101(bar から)
    for i in range(6):
        runs += list(_EAN_RUNS[(par[i], int(data[1 + i]))])
    runs += [1, 1, 1, 1, 1]                 # 中央ガード 01010
    for i in range(6):
        runs += list(_EAN_RUNS[("R", int(data[7 + i]))])
    runs += [1, 1, 1]
    return data, runs


def _c128_values(text: str, gs1: bool):
    """Code 128 の値の列(B と C を自動で切り替える)/ values with automatic B/C switching."""
    for ch in text:
        o = ord(ch)
        if not (32 <= o <= 126 or (gs1 and ch == "\x1d")):
            raise ValueError("encode_barcode1d: Code 128 here encodes ASCII 32..126 only "
                             "(plus '\\x1d' as FNC1 when gs1=True), got %r" % ch)

    def digit_run(i):
        j = i
        while j < len(text) and text[j].isdigit():
            j += 1
        return j - i

    vals = []
    i = 0
    run0 = digit_run(0)
    if run0 == len(text) and run0 >= 2 and run0 % 2 == 0 or run0 >= 4:
        cur = "C"
        vals.append(_C128_START_C)
    else:
        cur = "B"
        vals.append(_C128_START_B)
    if gs1:
        vals.append(_C128_FNC1)
    while i < len(text):
        ch = text[i]
        if ch == "\x1d":
            vals.append(_C128_FNC1)
            i += 1
            continue
        if cur == "C":
            if digit_run(i) >= 2:
                vals.append(int(text[i:i + 2]))
                i += 2
                continue
            vals.append(100)                 # Code B へ / CODE B
            cur = "B"
            continue
        r = digit_run(i)
        if r >= 6 or (r >= 4 and i + r == len(text)):
            if r % 2 == 1:                   # 奇数なら 1 桁を B で先に出す
                vals.append(ord(ch) - 32)
                i += 1
            vals.append(99)                  # Code C へ / CODE C
            cur = "C"
            continue
        vals.append(ord(ch) - 32)
        i += 1
    chk = vals[0]
    for k, v in enumerate(vals[1:], start=1):
        chk += k * v
    vals.append(chk % 103)
    vals.append(_C128_STOP)
    return vals


def encode_barcode1d(text, symbology="code128", *, wide_ratio=2.5, check_digit=False, gs1=False):
    """文字列を 1 次元バーコードの要素幅(モジュール単位)へ符号化する(``table``)。

    Encode ``text`` as a 1-D symbol. Returns a table: ``symbology``, ``text`` (the
    human-readable data, e.g. EAN-13 with its check digit), ``widths`` (element widths
    in modules, first element a bar, quiet zones excluded), ``quiet`` (left, right) in
    modules, ``n_modules`` (symbol length without quiet zones), ``edges`` (cumulative
    element boundaries starting at the left quiet-zone edge = 0), ``values`` (symbol
    character values, Code 128 only) and ``wide_ratio`` (two-width symbologies).

    ``symbology``: ``"ean13"`` (12 or 13 digits; the 13th must be the check digit),
    ``"upca"`` (11 or 12 digits), ``"code128"`` (ASCII 32..126, automatic code sets
    B / C; ``gs1=True`` puts FNC1 first and maps ``'\\x1d'`` to FNC1 — GS1-128),
    ``"code39"`` (``0-9 A-Z - . space $ / + %``, start/stop ``*`` added, optional
    mod-43 check with ``check_digit=True``), ``"itf"`` (an even number of digits;
    ``check_digit=True`` appends the GS1 mod-10 check to make the count even).
    ``wide_ratio`` (two-width symbologies) must lie in [2.0, 3.0].

    空の入力(``text == ""``)は ``ValueError``(理由: 符号化する中身が無い)。
    拒否(``ValueError``): 文字列でない、未知のシンボル体系、字種の外の文字、桁数違い、
    検査数字の不一致、``wide_ratio`` が [2.0, 3.0] の外。
    """
    op = "encode_barcode1d"
    if not isinstance(text, str):
        raise ValueError("%s: text must be a str, got %s" % (op, type(text).__name__))
    if text == "":
        raise ValueError("%s: text is empty — nothing to encode" % op)
    if symbology not in SYMBOLOGIES_1D:
        raise ValueError("%s: symbology must be one of %s, got %r" % (op, SYMBOLOGIES_1D, symbology))
    wr = float(wide_ratio)
    if not np.isfinite(wr) or not 2.0 <= wr <= 3.0:
        raise ValueError("%s: wide_ratio must lie in [2.0, 3.0], got %r" % (op, wide_ratio))
    values = None
    if symbology in ("ean13", "upca"):
        if not (text.isascii() and text.isdigit()):
            raise ValueError("%s: %s takes digits only, got %r" % (op, symbology, text))
        if symbology == "upca":
            if len(text) not in (11, 12):
                raise ValueError("%s: UPC-A needs 11 or 12 digits, got %d" % (op, len(text)))
            data, runs = _encode_ean13("0" + text)
            data = data[1:]
        else:
            data, runs = _encode_ean13(text)
        widths = [float(r) for r in runs]
    elif symbology == "code128":
        values = _c128_values(text, bool(gs1))
        widths = []
        for v in values:
            widths += [float(r) for r in _C128_RUNS[v]]
        data = text
    elif symbology == "code39":
        up = text
        bad = [c for c in up if c not in _C39_CHARS]
        if bad:
            raise ValueError("%s: Code 39 cannot encode %r (charset 0-9 A-Z - . space $ / + %%)"
                             % (op, bad[0]))
        if check_digit:
            up = up + _C39_CHARS[sum(_C39_CHARS.index(c) for c in up) % 43]
        full = "*" + up + "*"
        widths = []
        for k, ch in enumerate(full):
            if k:
                widths.append(1.0)           # 文字間の空白(細)/ inter-character gap
            widths += [wr if f == "w" else 1.0 for f in _C39[ch]]
        data = up
    else:  # itf
        if not (text.isascii() and text.isdigit()):
            raise ValueError("%s: ITF takes digits only, got %r" % (op, text))
        d = text
        if check_digit:
            d = d + str(ean_check_digit(d))
        if len(d) % 2:
            raise ValueError("%s: ITF needs an even number of digits (got %d%s)"
                             % (op, len(d), " incl. the check digit" if check_digit else ""))
        widths = [1.0, 1.0, 1.0, 1.0]        # 開始 / start: n n n n
        for i in range(0, len(d), 2):
            pb, ps = _ITF[int(d[i])], _ITF[int(d[i + 1])]
            for j in range(5):
                widths.append(wr if pb[j] == "w" else 1.0)
                widths.append(wr if ps[j] == "w" else 1.0)
        widths += [wr, 1.0, 1.0]            # 停止 / stop: W n n
        data = d
    widths = np.asarray(widths, dtype=np.float64)
    ql, qr = QUIET[symbology]
    edges = ql + np.concatenate([[0.0], np.cumsum(widths)])
    out = {"symbology": symbology, "text": data, "widths": widths, "quiet": (float(ql), float(qr)),
           "n_modules": float(widths.sum()), "edges": edges, "wide_ratio": wr}
    if values is not None:
        out["values"] = list(values)
    return out


# --------------------------------------------------------------------------- #
# 走査線 → 要素 / scan profile -> elements
# --------------------------------------------------------------------------- #
def _profile(p, op):
    a = np.asarray(p, dtype=np.float64)
    if a.ndim != 1:
        raise ValueError("%s: profile must be 1-D, got shape %s" % (op, a.shape))
    if a.size < 16:
        raise ValueError("%s: profile has %d samples — too short to hold a symbol" % (op, a.size))
    if not np.isfinite(a).all():
        raise ValueError("%s: profile has non-finite values" % op)
    return a


def _crossings(p, thr):
    """閾値の交差位置(標本間の線形補間、サブ画素)/ sub-sample threshold crossings."""
    s = p < thr                               # True = バー(暗い)
    idx = np.flatnonzero(s[1:] != s[:-1])
    a, b = p[idx], p[idx + 1]
    t = np.where(np.abs(b - a) > 0, (thr - a) / (b - a), 0.5)
    pos = idx + np.clip(t, 0.0, 1.0)
    return pos, s


def _elements(p, thr):
    """交差から要素(幅と色)の列を作る。両端は静寂域(明)として残す。"""
    pos, dark = _crossings(p, thr)
    # 位置 0 と末尾も境界として加える / add the profile ends as boundaries
    bounds = np.concatenate([[0.0], pos, [float(p.size - 1)]])
    widths = np.diff(bounds)
    first_dark = bool(dark[0])
    colors = np.array([(first_dark if k % 2 == 0 else not first_dark) for k in range(widths.size)])
    return bounds, widths, colors


# --------------------------------------------------------------------------- #
# 文字の判定 / character decoders on element widths (bar first)
# --------------------------------------------------------------------------- #
def _ean_char(w4, left_space_first=True):
    """EAN の 1 文字(4 要素)を似た縁の 2 和で判定。返り: (集合, 値, 余裕)。

    左半分は L / G、右半分は R の表だけを候補にする(R の幅の並びは L と同じなので、
    混ぜると左右の区別が付かない)。"""
    sets = ("L", "G") if left_space_first else ("R",)
    p = float(w4.sum())
    if p <= 0:
        return None
    m = 7.0 / p
    t1 = (w4[0] + w4[1]) * m
    t2 = (w4[1] + w4[2]) * m
    k1, k2 = int(round(t1)), int(round(t2))
    margin = min(0.5 - abs(t1 - k1), 0.5 - abs(t2 - k2)) / 0.5
    cands = []
    for (cs, d), r in _EAN_RUNS.items():
        if cs in sets and (r[0] + r[1], r[1] + r[2]) == (k1, k2):
            cands.append((cs, d, r))
    if not cands:
        return None
    if len(cands) > 1:
        # 1/7・2/8 はバー幅の和で分ける / bar-width sum breaks the 1/7, 2/8 ties
        bar_idx = (1, 3) if left_space_first else (0, 2)
        bsum = (w4[bar_idx[0]] + w4[bar_idx[1]]) * m
        cands.sort(key=lambda c: abs((c[2][bar_idx[0]] + c[2][bar_idx[1]]) - bsum))
        c0, c1 = cands[0], cands[1]
        s0 = c0[2][bar_idx[0]] + c0[2][bar_idx[1]]
        s1 = c1[2][bar_idx[0]] + c1[2][bar_idx[1]]
        mid = 0.5 * (s0 + s1)
        margin = min(margin, abs(bsum - mid) / (0.5 * abs(s1 - s0)))
    return cands[0][0], cands[0][1], max(0.0, float(margin))


def _decode_ean(w):
    """59 要素(先頭バー)から EAN-13 / UPC-A を読む。返り: (13 桁, 余裕の列) または None。"""
    if w.size != 59:
        return None
    unit = w.sum() / 95.0
    guards = [w[0:3], w[27:32], w[56:59]]
    for g in guards:
        if np.any(np.abs(g / unit - 1.0) > 0.75):
            return None
    margins = []
    left = []
    for i in range(6):
        seg = w[3 + 4 * i: 7 + 4 * i]
        r = _ean_char(seg, left_space_first=True)
        if r is None or r[0] == "R":
            return None
        left.append(r)
        margins.append(r[2])
    right = []
    for i in range(6):
        seg = w[32 + 4 * i: 36 + 4 * i]
        r = _ean_char(seg, left_space_first=False)
        if r is None or r[0] != "R":
            return None
        right.append(r)
        margins.append(r[2])
    par = "".join(c[0] for c in left)
    if par not in _EAN_PARITY:
        return None
    first = _EAN_PARITY.index(par)
    digits = str(first) + "".join(str(c[1]) for c in left) + "".join(str(c[1]) for c in right)
    if ean_check_digit(digits[:12]) != int(digits[12]):
        return None
    return digits, margins


def _c128_char(w6):
    p = float(w6.sum())
    if p <= 0:
        return None
    m = 11.0 / p
    ts = [(w6[i] + w6[i + 1]) * m for i in range(4)]
    ks = tuple(int(round(t)) for t in ts)
    vals = _C128_KEY.get(ks)
    if not vals:
        return None
    margin = min(0.5 - abs(t - k) for t, k in zip(ts, ks)) / 0.5
    v = vals[0]
    if len(vals) > 1:                          # 起こらないはず(表は一意)/ table is unique
        return None
    return v, max(0.0, float(margin))


def _decode_c128(w):
    n = w.size
    if n < 6 * 3 + 7 or (n - 7) % 6:
        return None
    nch = (n - 7) // 6
    stop = w[-7:]
    ps = stop.sum()
    if np.any(np.abs(stop * 13.0 / ps - np.array(_C128_RUNS[_C128_STOP])) > 0.75):
        return None
    vals, margins = [], []
    for i in range(nch):
        r = _c128_char(w[6 * i: 6 * i + 6])
        if r is None:
            return None
        vals.append(r[0])
        margins.append(r[1])
    if vals[0] not in (_C128_START_A, _C128_START_B, _C128_START_C):
        return None
    chk = vals[0]
    for k, v in enumerate(vals[1:-1], start=1):
        chk += k * v
    if chk % 103 != vals[-1]:
        return None
    text, gs1 = [], False
    cur = {103: "A", 104: "B", 105: "C"}[vals[0]]
    body = vals[1:-1]
    for k, v in enumerate(body):
        if v == _C128_FNC1:
            if k == 0:
                gs1 = True
            else:
                text.append("\x1d")
            continue
        if cur == "C":
            if v < 100:
                text.append("%02d" % v)
            elif v == 100:
                cur = "B"
            elif v == 101:
                cur = "A"
            else:
                return None
        else:
            if v == 99:
                cur = "C"
            elif v == 100 and cur == "A":
                cur = "B"
            elif v == 101 and cur == "B":
                cur = "A"
            elif v < 96:
                if cur == "B":
                    text.append(chr(v + 32))
                else:
                    text.append(chr(v + 32) if v < 64 else chr(v - 64))
            else:
                return None                    # シフト・FNC2-4 は扱わない / unsupported
    return "".join(text), margins, gs1, vals


def _two_width(ws, n_wide):
    """幅の順位で太を選ぶ。返り: (太の旗, 余裕 V, 太細比)。"""
    order = np.argsort(-ws, kind="stable")
    wide = np.zeros(ws.size, bool)
    wide[order[:n_wide]] = True
    nmean = ws[~wide].mean()
    wmean = ws[wide].mean()
    # 太細比は規格の 2.0..3.0 に測定の余裕を足した 1.8..3.4 の外なら文字ではない
    # (ぼけた他のシンボルの断片を 2 値幅として読まないための門)
    if not 1.8 <= wmean / nmean <= 3.4:
        return None
    rt = 0.5 * (nmean + wmean)
    v = min((rt - ws[~wide].max()) / (rt - nmean), (ws[wide].min() - rt) / (wmean - rt))
    return wide, float(v), float(wmean / nmean)


def _decode_c39(w):
    n = w.size
    if (n + 1) % 10 or n < 29:
        return None
    nch = (n + 1) // 10
    chars, margins = [], []
    for i in range(nch):
        seg = w[10 * i: 10 * i + 9]
        r = _two_width(seg, 3)
        if r is None:
            return None
        key = "".join("w" if f else "n" for f in r[0])
        ch = _C39_INV.get(key)
        if ch is None:
            return None
        if i + 1 < nch:
            gap = w[10 * i + 9]
            if gap > 0.5 * (seg[r[0]].mean() + seg[~r[0]].mean()):
                return None                    # 文字間は細のはず / gap must be narrow
        chars.append(ch)
        margins.append(r[1])
    if chars[0] != "*" or chars[-1] != "*" or "*" in chars[1:-1]:
        return None
    return "".join(chars[1:-1]), margins


def _decode_itf(w):
    n = w.size
    if n < 4 + 10 + 3 or (n - 7) % 10:
        return None
    start, stop = w[:4], w[-3:]
    body = w[4:-3]
    nar = np.median(np.concatenate([start, stop[1:]]))
    if np.any(np.abs(start / nar - 1.0) > 0.6) or stop[0] < 1.5 * nar:
        return None
    digits, margins = [], []
    for i in range(0, body.size, 10):
        seg = body[i:i + 10]
        bars, spaces = seg[0::2], seg[1::2]
        for part in (bars, spaces):
            r = _two_width(part, 2)
            if r is None:
                return None
            key = "".join("w" if f else "n" for f in r[0])
            if key not in _ITF_INV:
                return None
            digits.append(str(_ITF_INV[key]))
            margins.append(r[1])
    return "".join(digits), margins


def _try_runs(w, symbologies, allowed=None, itf_min_length=6):
    """要素列(先頭バー)を各体系で試す。返り: dict or None。"""
    allowed = symbologies if allowed is None else allowed
    for sym in symbologies:
        if sym in ("ean13", "upca"):
            r = _decode_ean(w)
            if r is not None:
                d, mg = r
                # 先頭が 0 の EAN-13 は UPC-A と同じ物(GS1 の約束)。UPC-A を許すときは
                # UPC-A として 12 桁で返す / an EAN-13 with a leading 0 *is* a UPC-A
                if d[0] == "0" and "upca" in allowed:
                    return {"symbology": "upca", "text": d[1:], "margins": mg}
                if sym == "upca":
                    continue
                return {"symbology": "ean13", "text": d, "margins": mg}
        elif sym == "code128":
            r = _decode_c128(w)
            if r is not None:
                return {"symbology": "code128", "text": r[0], "margins": r[1], "gs1": r[2],
                        "values": r[3]}
        elif sym == "code39":
            r = _decode_c39(w)
            if r is not None:
                return {"symbology": "code39", "text": r[0], "margins": r[1]}
        else:
            r = _decode_itf(w)
            if r is not None and len(r[0]) >= itf_min_length:
                return {"symbology": "itf", "text": r[0], "margins": r[1]}
    return None


#: 1 シンボルの要素数で候補の窓を絞る(全体系)。静寂域は X の倍数で確かめる。
_MIN_QUIET_X = 5.0


def decode_barcode_profile(profile, symbologies=None, *, threshold=None, itf_min_length=6):
    """1 本の走査線(反射率の 1-D 列)からシンボルを 1 つ復号する(``table``)。

    Decode one symbol from a scan reflectance profile (1-D, bars dark). The global
    threshold is ``(max + min) / 2`` of the profile unless given (the same threshold
    the print-quality grade uses). Elements come from sub-sample threshold crossings;
    every run of bar-first elements flanked by light zones at least
    ``5 X`` wide (X estimated from the candidate itself) is tried with each symbology,
    in both scan directions. Returns ``symbology``, ``text``, ``margins`` (per
    character decode margin in [0, 1]: 1 = element sums exactly on the module grid,
    0 = on the decision boundary), ``reversed`` (read right-to-left), ``x_dim``
    (estimated module width in samples), ``start`` / ``stop`` (sample positions of
    the first bar's leading edge and the last bar's trailing edge) and
    ``threshold``.

    限界 / limits: 1 本の走査線に 1 シンボル(最初に一致したもの)。静寂域が 5 X より
    狭いと探さない。Code 128 の FNC2-4・シフト・コード A の制御文字は読まない。

    ★ITF は検査数字を持たず、ぼけた他のシンボルの一部が短い ITF に化ける(短読み、
    short read)。``itf_min_length``(既定 6 桁)未満の ITF は返さない。実測: EAN-13 を
    デフォーカスで壊すと、全体系を許した読み取りは 2 桁の ITF などを**誤読**として返した
    (``tests/test_barcode1d.py``)。現場の読み取り器と同じく、``symbologies`` は使う体系
    だけに絞ること。
    ITF has no check digit; fragments of a blurred symbol decode as short ITF. ITF reads
    shorter than ``itf_min_length`` are refused; restrict ``symbologies`` to what the
    line uses.

    空の入力は ``ValueError``(16 標本未満は「シンボルを含めない」)。
    拒否(``ValueError``): 1-D でない、非有限、未知の体系名。どの体系とも一致しなければ
    :class:`Barcode1DError`(``ValueError`` の派生)—— **誤読より読み取り不能を選ぶ**
    (検査数字・開始停止・ガードの照合を全部通ったものだけ返す)。
    """
    op = "decode_barcode_profile"
    p = _profile(profile, op)
    syms = SYMBOLOGIES_1D if symbologies is None else tuple(symbologies)
    for s in syms:
        if s not in SYMBOLOGIES_1D:
            raise ValueError("%s: unknown symbology %r" % (op, s))
    if threshold is None:
        thr = 0.5 * (float(p.max()) + float(p.min()))
    else:
        thr = float(threshold)
        if not np.isfinite(thr):
            raise ValueError("%s: threshold must be finite" % op)
    if float(p.max() - p.min()) <= 1e-6:
        raise Barcode1DError("%s: flat profile — no edges" % op)
    # 体系ごとの要素数 / element counts per symbology
    for rev in (False, True):
        q = p[::-1] if rev else p
        bounds, widths, colors = _elements(q, thr)
        nE = widths.size
        dark_idx = np.flatnonzero(colors)
        for i0 in dark_idx:
            if i0 == 0:
                continue                         # 先頭が端に接するバー = 静寂域なし
            for sym in syms:
                counts = _candidate_counts(sym, widths, colors, i0)
                for cnt in counts:
                    i1 = i0 + cnt                 # 次の要素 = 右の静寂域
                    if i1 >= nE or not colors[i1 - 1]:
                        continue
                    seg = widths[i0:i1]
                    est_x = seg.sum() / _nominal_modules(sym, cnt, seg)
                    if widths[i0 - 1] < _MIN_QUIET_X * est_x or widths[i1] < _MIN_QUIET_X * est_x:
                        continue
                    r = _try_runs(seg, (sym,), syms, itf_min_length)
                    if r is None:
                        continue
                    a, b = bounds[i0], bounds[i1]
                    if rev:
                        a, b = (p.size - 1) - b, (p.size - 1) - a
                    r.update({"reversed": rev, "x_dim": float(est_x), "start": float(a),
                              "stop": float(b), "threshold": thr})
                    return r
    raise Barcode1DError("%s: no symbol of %s found in the profile" % (op, list(syms)))


def _candidate_counts(sym, widths, colors, i0):
    n = widths.size - i0
    if sym in ("ean13", "upca"):
        return [59] if n > 59 else []
    if sym == "code128":
        return [c for c in range(25, n, 6) if (c - 7) % 6 == 0][:40]
    if sym == "code39":
        return [c for c in range(29, n, 10)][:40]
    return [c for c in range(17, n, 10)][:40]


def _nominal_modules(sym, cnt, seg):
    if sym in ("ean13", "upca"):
        return 95.0
    if sym == "code128":
        return 11.0 * (cnt - 7) / 6.0 + 13.0
    # 2 値幅: 細 = 最小側の中央値で X を推す / two-width: X from the narrow median
    nar = np.median(np.sort(seg)[: max(1, seg.size // 2)])
    return seg.sum() / nar


# --------------------------------------------------------------------------- #
# 画像から / from images
# --------------------------------------------------------------------------- #
def _image(img, op):
    a = np.asarray(img, dtype=np.float64)
    if a.ndim != 2:
        raise ValueError("%s: image must be 2-D (gray), got shape %s" % (op, a.shape))
    if min(a.shape) < 8:
        raise ValueError("%s: image %s is too small" % (op, a.shape))
    if not np.isfinite(a).all():
        raise ValueError("%s: image has non-finite values" % op)
    return a


def _dominant_angle(a):
    """構造テンソルで縞の法線方向(rad、x 軸から)を推す / bar-normal direction via the structure tensor."""
    gy, gx = np.gradient(a)
    jxx, jyy, jxy = float((gx * gx).sum()), float((gy * gy).sum()), float((gx * gy).sum())
    theta = 0.5 * np.arctan2(2.0 * jxy, jxx - jyy)
    coh = np.hypot(jxx - jyy, 2.0 * jxy) / max(jxx + jyy, 1e-12)
    return float(theta), float(coh)


def barcode_scan_profiles(image, angle_deg=None, n_lines=10, *, band=(0.1, 0.9), step=0.5):
    """画像から、縞に垂直な平行走査線を ``n_lines`` 本取り出す(``table``)。

    Sample ``n_lines`` parallel scan lines perpendicular to the bars. The bar-normal
    direction is ``angle_deg`` (degrees from the image x axis, counter-clockwise in
    display = row up) or, if None, the dominant gradient direction of the structure
    tensor. Lines are spaced evenly over the ``band`` fraction of the strong-gradient
    region's extent along the bars (ISO-style 10 scans over 10 %..90 % of the height),
    sampled every ``step`` pixels by bilinear interpolation over the whole image width.
    Returns ``profiles`` (n_lines, L), ``angle_deg``, ``coherence`` (0..1, how
    line-like the texture is), ``offsets`` (px across the bars), ``step`` and
    ``origin`` / ``direction`` / ``normal`` (row, col) so a profile sample ``s`` of line
    ``k`` maps to ``origin + offsets[k] * normal + s * step * direction``.

    空の入力(8 画素未満の辺)は ``ValueError``。
    拒否(``ValueError``): 2-D でない、非有限、``n_lines`` < 1、``band`` が (0, 1) の
    昇順でない、``step`` <= 0。勾配の無い画像は :class:`Barcode1DError`。
    """
    op = "barcode_scan_profiles"
    from scipy import ndimage
    a = _image(image, op)
    if isinstance(n_lines, bool) or not isinstance(n_lines, (int, np.integer)) or n_lines < 1:
        raise ValueError("%s: n_lines must be a positive integer, got %r" % (op, n_lines))
    lo, hi = float(band[0]), float(band[1])
    if not 0.0 <= lo < hi <= 1.0:
        raise ValueError("%s: band must be increasing inside [0, 1], got %r" % (op, band))
    step = float(step)
    if not np.isfinite(step) or step <= 0:
        raise ValueError("%s: step must be > 0, got %r" % (op, step))
    if float(a.max() - a.min()) <= 1e-6:
        raise Barcode1DError("%s: flat image — no bars" % op)
    if angle_deg is None:
        theta, coh = _dominant_angle(a)
    else:
        theta, coh = np.deg2rad(float(angle_deg)), float("nan")
        theta = -theta                           # 表示の反時計回り → 画像座標(row 下向き)
    # direction along the scan (across bars) in (row, col)
    d = np.array([np.sin(theta), np.cos(theta)])
    nrm = np.array([d[1], -d[0]])                # 縞に沿う方向 / along the bars
    H, W = a.shape
    c0 = np.array([(H - 1) / 2.0, (W - 1) / 2.0])
    gy, gx = np.gradient(ndimage.gaussian_filter(a, 1.0))
    g = np.abs(gy * d[0] + gx * d[1])
    rr, cc = np.nonzero(g > 0.25 * g.max())
    if rr.size == 0:
        raise Barcode1DError("%s: no gradient — no bars" % op)
    pts = np.stack([rr, cc], 1) - c0
    t_along = pts @ nrm
    t_across = pts @ d
    a0, a1 = np.percentile(t_along, [1, 99])
    centre_across = 0.5 * (t_across.min() + t_across.max())
    origin = c0 + centre_across * d
    offs = a0 + (a1 - a0) * (lo + (hi - lo) * (np.arange(n_lines) + 0.5) / n_lines)
    half = 0.5 * float(np.hypot(H, W))
    s = np.arange(-half, half, step)
    prof = []
    for o in offs:
        r = origin[0] + o * nrm[0] + s * d[0]
        c = origin[1] + o * nrm[1] + s * d[1]
        inside = (r >= 0) & (r <= H - 1) & (c >= 0) & (c <= W - 1)
        v = ndimage.map_coordinates(a, [r, c], order=1, mode="nearest")
        # 画像の外は最も近い縁の明るさで延長しない —— 外は切り捨てる
        prof.append(np.where(inside, v, np.nan))
    prof = np.asarray(prof)
    keep = np.isfinite(prof).all(axis=0)
    if keep.sum() < 16:
        # 斜めの走査は各線で範囲が違う: 共通部分が短ければ線ごとに近傍で埋める
        prof = np.where(np.isfinite(prof), prof, np.nanmax(prof))
    else:
        cols = np.flatnonzero(keep)
        prof = prof[:, cols[0]:cols[-1] + 1]
        s = s[cols[0]:cols[-1] + 1]
    return {"profiles": prof, "angle_deg": float(-np.rad2deg(theta)), "coherence": coh,
            "offsets": offs, "step": step, "origin": origin + s[0] * d, "direction": d,
            "normal": nrm}


def read_barcode1d(image, symbologies=None, *, angle_deg=None, n_lines=10, itf_min_length=6,
                   min_agree=2):
    """画像から 1 次元バーコードを読む(``table``)。

    Read a 1-D symbol from a 2-D reflectance image at any in-plane angle: sample
    ``n_lines`` scan lines across the bars (:func:`barcode_scan_profiles`), decode each
    (:func:`decode_barcode_profile`) and take the majority text. Returns ``text``,
    ``symbology``, ``n_lines``, ``n_decoded`` (lines that decoded), ``n_agree`` (lines
    agreeing with the majority), ``votes`` (text -> count), ``line_results`` (one dict
    or None per line), ``angle_deg``, ``x_dim_px``.

    ★2 本以上の走査線が**違う**文字列で復号したときは多数決の結果に ``conflict = True``
    を立てる(誤読の兆候。検査では読み取り不能と同じに扱うべき)。多数の文字列に同意した
    走査線が ``min_agree``(既定 2)本に満たなければ読み取り不能とする —— 1 本だけの
    偶然の一致(ぼけた断片が検査数字を通る)を返さない。
    Two or more lines decoding to different strings sets ``conflict = True``; fewer than
    ``min_agree`` lines agreeing on the majority text is a no-read.

    空の入力は ``ValueError``。
    拒否(``ValueError``): 2-D でない、非有限、未知の体系名。1 本も読めなければ
    :class:`Barcode1DError`。
    """
    op = "read_barcode1d"
    a = _image(image, op)
    sp = barcode_scan_profiles(a, angle_deg=angle_deg, n_lines=n_lines)
    results, votes = [], {}
    for prof in sp["profiles"]:
        try:
            r = decode_barcode_profile(prof, symbologies, itf_min_length=itf_min_length)
        except Barcode1DError:
            results.append(None)
            continue
        results.append(r)
        key = (r["symbology"], r["text"])
        votes[key] = votes.get(key, 0) + 1
    if not votes:
        raise Barcode1DError("%s: none of the %d scan lines decoded" % (op, len(results)))
    (sym, text), n_agree = max(votes.items(), key=lambda kv: kv[1])
    if n_agree < min(int(min_agree), len(results)):
        raise Barcode1DError("%s: only %d of %d scan lines agree on %r (need %d) — refused as a "
                             "possible misread" % (op, n_agree, len(results), text, min_agree))
    xs = [r["x_dim"] for r in results if r is not None and r["text"] == text]
    return {"text": text, "symbology": sym, "n_lines": len(results),
            "n_decoded": int(sum(votes.values())), "n_agree": int(n_agree),
            "votes": {"%s:%s" % k: v for k, v in votes.items()}, "conflict": len(votes) > 1,
            "line_results": results, "angle_deg": sp["angle_deg"],
            "x_dim_px": float(np.median(xs)) * sp["step"]}
