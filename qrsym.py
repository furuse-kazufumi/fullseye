# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""QR Code(Model 2)の自前符号化・復号・画像からの読み取り。

Self-contained QR Code (Model 2) encoder, module-grid decoder and image reader.

なぜ自前か / why not a library
-------------------------------
印字品質の評価(ISO/IEC 15415 流の「未使用の誤り訂正」や符号語ごとの変調)には、
ブロックごとに **何語を直したか** と **どのモジュールがどの符号語に属するか**
(モジュール→符号語の対応表)が要る。既存の読み取り器は文字列を返すが、これらを返さない。
Print-quality grading (ISO/IEC 15415-style "unused error correction", modulation per
codeword) needs per-block corrected-codeword counts and the module -> codeword map.
Off-the-shelf readers return the decoded text only.

範囲 / scope
------------
* 型番(version)1..40、誤り訂正レベル L/M/Q/H、8 種のマスク。
  Versions 1..40, EC levels L/M/Q/H, all 8 masks.
* 符号化: 数字 / 英数字 / 8 bit バイト(1 セグメント)。バイトは **UTF-8**(ECI を付けない。
  多くの読み取り器が UTF-8 を推定する慣行に合わせる)。
  Encoding: numeric / alphanumeric / byte, one segment. Byte mode stores **UTF-8**
  without an ECI header (common practice; most readers guess UTF-8).
* 復号: 数字 / 英数字 / バイト / 漢字(Shift JIS)/ ECI(3=ISO-8859-1, 20=Shift JIS,
  26=UTF-8 ほか公開の割り当て)。ECI なしのバイトは UTF-8 として読み、不正なら ISO-8859-1。
  構造的連接・FNC1 は未対応(明示的に拒否)。
  Decoding: numeric / alphanumeric / byte / kanji / ECI (3, 20, 26 and the other public
  assignments, e.g. ISO-8859-x, cp125x, Big5, GB18030, EUC-KR). Bytes without ECI
  are read as UTF-8, falling back to ISO-8859-1. Structured append and FNC1 are
  rejected explicitly (unsupported).
* Micro QR・Model 1・rMQR は対象外 / Micro QR, Model 1 and rMQR are out of scope.

画像座標の約束 / image coordinate convention
--------------------------------------------
画素 (r, c) の中心を座標 (行=r, 列=c) とする(``scipy.ndimage`` と同じ)。
モジュール空間は x=列, y=行 で、モジュール (i, j) の中心は (j+0.5, i+0.5)、格子は 0..N。
``homography`` は斉次 [x, y, 1](モジュール空間)→ [x=列px, y=行px, w](画像)。
Pixel (r, c) has its centre at (row=r, col=c) as in ``scipy.ndimage``. Module space is
x=col, y=row; module (i, j) centre is (j+0.5, i+0.5), the grid spans 0..N.

出典(公開記述のみ)/ sources (public descriptions only)
-------------------------------------------------------
ISO/IEC 18004 の構造(公開されている説明として)、thonky.com の QR Code Tutorial、
Reed–Solomon 符号 (I. S. Reed & G. Solomon, 1960) は ``symrs.py`` を使う。
Structure of ISO/IEC 18004 as publicly described; the thonky.com QR Code Tutorial;
Reed-Solomon (Reed & Solomon 1960) via ``symrs.py``. No standard text is copied.

失敗は閉じる / fail-closed
--------------------------
不正な入力は ``ValueError``、読めない・直せない符号は ``QRDecodeError``(``ValueError`` の
派生)。誤り訂正が能力(誤復号保護語 p を差し引いた値)を超えたら拒否する。
Invalid input raises ``ValueError``; unreadable / uncorrectable symbols raise
``QRDecodeError`` (a ``ValueError``). Corrections beyond the block capacity (after
removing the misdecode-protection codewords p) are rejected.
"""
from __future__ import annotations

from functools import lru_cache
import math

import numpy as np

from symrs import QR_FIELD, RSDecodeError, rs_decode, rs_encode

__all__ = ["QRDecodeError", "qr_encode", "qr_decode_modules", "qr_locate",
           "qr_sample", "qr_read"]


class QRDecodeError(ValueError):
    """QR を見つけられない・読めない・直せない / the QR symbol cannot be found or decoded."""


# --------------------------------------------------------------------------- #
# 表 / tables                                                                  #
# --------------------------------------------------------------------------- #
_EC_LEVELS = ("L", "M", "Q", "H")
#: 形式情報の 2 bit(L=01, M=00, Q=11, H=10)/ format-info EC bits.
_EC_FORMAT_BITS = {"L": 1, "M": 0, "Q": 3, "H": 2}
_FORMAT_BITS_EC = {v: k for k, v in _EC_FORMAT_BITS.items()}

# ブロックあたりの誤り訂正語数(index = 型番、0 は未使用)/ EC codewords per block.
_ECC_PER_BLOCK = {
    "L": (-1, 7, 10, 15, 20, 26, 18, 20, 24, 30, 18, 20, 24, 26, 30, 22, 24, 28, 30, 28, 28,
          28, 28, 30, 30, 26, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30),
    "M": (-1, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26, 30, 22, 22, 24, 24, 28, 28, 26, 26, 26,
          26, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28),
    "Q": (-1, 13, 22, 18, 26, 18, 24, 18, 22, 20, 24, 28, 26, 24, 20, 30, 24, 28, 28, 26, 30,
          28, 30, 30, 30, 30, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30),
    "H": (-1, 17, 28, 22, 16, 22, 28, 26, 26, 24, 28, 24, 28, 22, 24, 24, 30, 28, 28, 26, 28,
          30, 24, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30),
}
# ブロック数 / number of RS blocks.
_NUM_BLOCKS = {
    "L": (-1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 4, 4, 4, 4, 4, 6, 6, 6, 6, 7, 8,
          8, 9, 9, 10, 12, 12, 12, 13, 14, 15, 16, 17, 18, 19, 19, 20, 21, 22, 24, 25),
    "M": (-1, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5, 5, 8, 9, 9, 10, 10, 11, 13, 14, 16,
          17, 17, 18, 20, 21, 23, 25, 26, 28, 29, 31, 33, 35, 37, 38, 40, 43, 45, 47, 49),
    "Q": (-1, 1, 1, 2, 2, 4, 4, 6, 6, 8, 8, 8, 10, 12, 16, 12, 17, 16, 18, 21, 20,
          23, 23, 25, 27, 29, 34, 34, 35, 38, 40, 43, 45, 48, 51, 53, 56, 59, 62, 65, 68),
    "H": (-1, 1, 1, 2, 4, 4, 4, 5, 6, 8, 8, 11, 11, 16, 16, 18, 16, 19, 21, 25, 25,
          25, 34, 30, 32, 35, 37, 40, 42, 45, 48, 51, 54, 57, 60, 63, 66, 70, 74, 77, 81),
}
#: 誤復号保護語 p(訂正能力 = floor((n_ec - p) / 2))。公開表で能力が floor(n_ec/2) より
#: 小さい組だけを載せる。1-H 等の奇数 n_ec は p=1 でも floor(n_ec/2) と同じなので省く。
#: Misdecode-protection codewords p: capacity = floor((n_ec - p) / 2). Only the
#: combinations whose capacity is below floor(n_ec/2) are listed (odd n_ec with p=1
#: gives the same capacity as p=0).
_P_MISDECODE = {(1, "L"): 3, (1, "M"): 2, (1, "Q"): 1, (2, "L"): 2, (3, "L"): 1}

_ALNUM = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:"
_ALNUM_INDEX = {c: i for i, c in enumerate(_ALNUM)}
_MODE_BITS = {"numeric": 0b0001, "alphanumeric": 0b0010, "byte": 0b0100, "kanji": 0b1000}
_MODES = ("numeric", "alphanumeric", "byte")


def _count_bits(mode: str, version: int) -> int:
    """文字数指示子の bit 数 / character-count field width."""
    idx = 0 if version <= 9 else (1 if version <= 26 else 2)
    return {"numeric": (10, 12, 14), "alphanumeric": (9, 11, 13),
            "byte": (8, 16, 16), "kanji": (8, 10, 12)}[mode][idx]


def _num_raw_modules(version: int) -> int:
    """データ+訂正語に使えるモジュール数(余りビット込み)/ data modules incl. remainder."""
    r = (16 * version + 128) * version + 64
    if version >= 2:
        na = version // 7 + 2
        r -= (25 * na - 10) * na - 55
        if version >= 7:
            r -= 36
    return r


def _block_layout(version: int, ec: str):
    """ブロック順の (データ語数, 訂正語数) / (n_data, n_ec) per block, block order."""
    total = _num_raw_modules(version) // 8
    nb = _NUM_BLOCKS[ec][version]
    ne = _ECC_PER_BLOCK[ec][version]
    short_len = total // nb
    n_short = nb - total % nb
    return [(short_len - ne, ne)] * n_short + [(short_len + 1 - ne, ne)] * (nb - n_short)


def _alignment_positions(version: int):
    """位置合わせパターン中心の行/列座標 / alignment-pattern centre coordinates."""
    if version == 1:
        return []
    na = version // 7 + 2
    size = 17 + 4 * version
    step = 26 if version == 32 else (version * 8 + na * 3 + 5) // (na * 4 - 4) * 2
    pos = [size - 7 - i * step for i in range(na - 1)]
    return [6] + sorted(pos)


def _bch_format(data5: int) -> int:
    """形式情報 BCH(15,5)+ マスク 0x5412 / format-information codeword."""
    rem = data5 << 10
    for i in range(14, 9, -1):
        if (rem >> i) & 1:
            rem ^= 0x537 << (i - 10)
    return ((data5 << 10) | rem) ^ 0x5412


def _bch_version(v: int) -> int:
    """型番情報 BCH(18,6) / version-information codeword."""
    rem = v << 12
    for i in range(17, 11, -1):
        if (rem >> i) & 1:
            rem ^= 0x1F25 << (i - 12)
    return (v << 12) | rem


_FORMAT_TABLE = {(ec, m): _bch_format((_EC_FORMAT_BITS[ec] << 3) | m)
                 for ec in _EC_LEVELS for m in range(8)}
_VERSION_TABLE = {v: _bch_version(v) for v in range(7, 41)}


def _popcount(x: int) -> int:
    return bin(x).count("1")


def _format_coords(n: int):
    """形式情報 bit i(LSB=0)の 2 か所 / both copies' (row, col) per bit, LSB first."""
    a = [(i, 8) for i in range(6)] + [(7, 8), (8, 8), (8, 7)] + [(8, 14 - i) for i in range(9, 15)]
    b = [(8, n - 1 - i) for i in range(8)] + [(n - 15 + i, 8) for i in range(8, 15)]
    return a, b


def _version_coords(n: int):
    """型番情報 bit i の 2 か所(右上 / 左下)/ both version-info copies per bit."""
    a = [(i // 3, n - 11 + i % 3) for i in range(18)]
    b = [(n - 11 + i % 3, i // 3) for i in range(18)]
    return a, b


@lru_cache(maxsize=64)
def _function_layout(version: int):
    """機能パターンの (mask, 固定値, データ配置順) / function mask, fixed values, data order.

    Returns read-only arrays: ``fmask`` (N,N) bool, ``base`` (N,N) uint8 with the
    function-pattern values (format/version areas left 0) and ``order`` (K,2) int —
    the (row, col) of every data module in zig-zag placement order.
    """
    n = 17 + 4 * version
    fmask = np.zeros((n, n), bool)
    base = np.zeros((n, n), np.uint8)
    # ファインダー + 分離帯 / finders + separators
    fp = np.zeros((7, 7), np.uint8)
    fp[:, :] = 1
    fp[1:6, 1:6] = 0
    fp[2:5, 2:5] = 1
    for r0, c0 in ((0, 0), (0, n - 7), (n - 7, 0)):
        base[r0:r0 + 7, c0:c0 + 7] = fp
    fmask[0:9, 0:9] = True             # TL finder + separator + format
    fmask[0:9, n - 8:n] = True         # TR finder + separator + format row 8
    fmask[n - 8:n, 0:9] = True         # BL finder + separator + format col 8
    # タイミング / timing
    t = (np.arange(n) % 2 == 0).astype(np.uint8)
    base[6, 8:n - 8] = t[8:n - 8]
    base[8:n - 8, 6] = t[8:n - 8]
    fmask[6, :] = True
    fmask[:, 6] = True
    # 位置合わせ / alignment
    ap = _alignment_positions(version)
    al = np.ones((5, 5), np.uint8)
    al[1:4, 1:4] = 0
    al[2, 2] = 1
    for r in ap:
        for c in ap:
            if (r == 6 and c == 6) or (r == 6 and c == ap[-1]) or (r == ap[-1] and c == 6):
                continue
            base[r - 2:r + 3, c - 2:c + 3] = al
            fmask[r - 2:r + 3, c - 2:c + 3] = True
    # 暗モジュール / dark module
    base[n - 8, 8] = 1
    # 型番情報 / version information
    if version >= 7:
        fmask[0:6, n - 11:n - 8] = True
        fmask[n - 11:n - 8, 0:6] = True
    # ジグザグ配置順 / zig-zag placement order
    order = []
    for right in range(n - 1, 0, -2):
        if right <= 6:
            right -= 1
        upward = ((right + 1) & 2) == 0
        for vert in range(n):
            y = n - 1 - vert if upward else vert
            for j in range(2):
                x = right - j
                if not fmask[y, x]:
                    order.append((y, x))
    order = np.asarray(order, np.int64)
    if len(order) != _num_raw_modules(version):
        raise AssertionError("internal: data module count mismatch for version %d" % version)
    for a in (fmask, base, order):
        a.setflags(write=False)
    return fmask, base, order


@lru_cache(maxsize=64)
def _mask_patterns(n: int):
    """8 種のマスク(True で反転)/ the 8 data masks (True = invert)."""
    i, j = np.indices((n, n))
    pats = np.stack([
        (i + j) % 2 == 0,
        i % 2 == 0,
        j % 3 == 0,
        (i + j) % 3 == 0,
        (i // 2 + j // 3) % 2 == 0,
        (i * j) % 2 + (i * j) % 3 == 0,
        ((i * j) % 2 + (i * j) % 3) % 2 == 0,
        ((i + j) % 2 + (i * j) % 3) % 2 == 0,
    ])
    pats.setflags(write=False)
    return pats


def _codeword_index_map(version: int):
    """モジュール→最終符号語列の添字(機能・余りは -1)/ module -> codeword index map."""
    fmask, _base, order = _function_layout(version)
    n = fmask.shape[0]
    total = _num_raw_modules(version) // 8
    idx = np.full((n, n), -1, np.int16)
    k = np.arange(len(order))
    cw = np.where(k < total * 8, k // 8, -1).astype(np.int16)
    idx[order[:, 0], order[:, 1]] = cw
    return idx


# --------------------------------------------------------------------------- #
# 符号化 / encoding                                                            #
# --------------------------------------------------------------------------- #
class _BitBuffer:
    def __init__(self):
        self.bits = []

    def put(self, value: int, nbits: int):
        for i in range(nbits - 1, -1, -1):
            self.bits.append((value >> i) & 1)


def _segment_payload(text: str, mode: str):
    """(文字数, データ bit 列) / (char count, data bits) for one segment."""
    bb = _BitBuffer()
    if mode == "numeric":
        for k in range(0, len(text), 3):
            g = text[k:k + 3]
            bb.put(int(g), {3: 10, 2: 7, 1: 4}[len(g)])
        return len(text), bb.bits
    if mode == "alphanumeric":
        for k in range(0, len(text) - 1, 2):
            bb.put(_ALNUM_INDEX[text[k]] * 45 + _ALNUM_INDEX[text[k + 1]], 11)
        if len(text) % 2:
            bb.put(_ALNUM_INDEX[text[-1]], 6)
        return len(text), bb.bits
    data = text.encode("utf-8")
    for b in data:
        bb.put(b, 8)
    return len(data), bb.bits


def _auto_mode(text: str) -> str:
    if text and all("0" <= c <= "9" for c in text):
        return "numeric"
    if text and all(c in _ALNUM_INDEX for c in text):
        return "alphanumeric"
    return "byte"


def _check_mode_fits(text: str, mode: str):
    if mode == "numeric" and not all("0" <= c <= "9" for c in text):
        raise ValueError("qr_encode: numeric mode accepts only digits 0-9")
    if mode == "alphanumeric" and not all(c in _ALNUM_INDEX for c in text):
        raise ValueError("qr_encode: alphanumeric mode accepts only 0-9 A-Z space $%*+-./:")


def _penalty(m: np.ndarray) -> int:
    """マスク評価の 4 規則(公開記述の重み 3/3/40/10)/ the 4 mask penalty rules."""
    n = m.shape[0]
    score = 0
    for a in (m, m.T):
        # 規則 1: 同色 5 連以上 / runs >= 5
        d = np.diff(a.astype(np.int8), axis=1) != 0
        starts = np.zeros((n, n + 1), bool)
        starts[:, 0] = True
        starts[:, 1:n] = d
        starts[:, n] = True
        rr, cc = np.nonzero(starts)
        lens = np.diff(cc)
        same = rr[1:] == rr[:-1]
        lens = lens[same]
        long = lens[lens >= 5]
        score += int(np.sum(long - 2))
        # 規則 3: ファインダー様 1011101 + 4 明 / finder-like patterns
        w = np.lib.stride_tricks.sliding_window_view(a, 11, axis=1)
        p1 = np.array([1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0], np.uint8)
        score += 40 * int(np.sum(np.all(w == p1, axis=2)) + np.sum(np.all(w == p1[::-1], axis=2)))
    # 規則 2: 2x2 同色 / 2x2 blocks
    blk = (m[:-1, :-1] == m[1:, :-1]) & (m[:-1, :-1] == m[:-1, 1:]) & (m[:-1, :-1] == m[1:, 1:])
    score += 3 * int(blk.sum())
    # 規則 4: 暗の比率 / dark proportion
    dark = int(m.sum())
    k = abs(dark * 20 - n * n * 10) // (n * n)
    score += 10 * int(k)
    return score


def _place_format(m: np.ndarray, ec: str, mask: int):
    n = m.shape[0]
    bits = _FORMAT_TABLE[(ec, mask)]
    a, b = _format_coords(n)
    for i in range(15):
        v = (bits >> i) & 1
        m[a[i]] = v
        m[b[i]] = v
    m[n - 8, 8] = 1


def _place_version(m: np.ndarray, version: int):
    if version < 7:
        return
    n = m.shape[0]
    bits = _VERSION_TABLE[version]
    a, b = _version_coords(n)
    for i in range(18):
        v = (bits >> i) & 1
        m[a[i]] = v
        m[b[i]] = v


def qr_encode(text, ec_level="M", version=None, mask=None, mode=None) -> dict:
    """文字列を QR Code(Model 2)のモジュール格子に符号化する。

    Encode ``text`` as a QR Code (Model 2) module grid.

    Parameters
    ----------
    text : str
        符号化する文字列 / the text. Byte mode stores UTF-8 (no ECI).
    ec_level : {"L", "M", "Q", "H"}
        誤り訂正レベル / error-correction level.
    version : int or None
        1..40。None なら収まる最小 / 1..40, or None for the smallest that fits.
    mask : int or None
        0..7。None なら 4 規則の減点が最小のもの / 0..7, or None to pick by penalty.
    mode : {"numeric", "alphanumeric", "byte"} or None
        None なら文字種から自動 / None to choose from the characters.

    Returns
    -------
    dict
        ``modules`` (N,N) uint8 (1=暗/dark), ``size``, ``version``, ``ec_level``, ``mask``,
        ``mode``, ``text``, ``blocks`` [(n_data, n_ec)…], ``n_data_codewords``,
        ``n_ec_codewords``, ``function_mask`` (N,N) bool, ``codeword_index`` (N,N) int16
        (-1 = 機能/余り / function or remainder), ``codewords`` (interleaved list).
    """
    op = "qr_encode"
    if not isinstance(text, str):
        raise ValueError("%s: text must be str, got %s" % (op, type(text).__name__))
    if not isinstance(ec_level, str) or ec_level.upper() not in _EC_LEVELS:
        raise ValueError("%s: ec_level must be one of L/M/Q/H, got %r" % (op, ec_level))
    ec = ec_level.upper()
    if version is not None and (isinstance(version, bool) or not isinstance(version, (int, np.integer))
                                or not 1 <= int(version) <= 40):
        raise ValueError("%s: version must be an integer in 1..40 or None, got %r" % (op, version))
    if mask is not None and (isinstance(mask, bool) or not isinstance(mask, (int, np.integer))
                             or not 0 <= int(mask) <= 7):
        raise ValueError("%s: mask must be an integer in 0..7 or None, got %r" % (op, mask))
    if mode is None:
        mode = _auto_mode(text)
    if mode not in _MODES:
        raise ValueError("%s: mode must be one of %s or None, got %r" % (op, _MODES, mode))
    _check_mode_fits(text, mode)
    count, payload = _segment_payload(text, mode)

    def fits(v):
        cb = _count_bits(mode, v)
        if count >= (1 << cb):
            return False
        nd = sum(b[0] for b in _block_layout(v, ec))
        return 4 + cb + len(payload) <= nd * 8

    if version is None:
        for v in range(1, 41):
            if fits(v):
                version = v
                break
        else:
            raise ValueError("%s: text too long for any version at EC level %s" % (op, ec))
    version = int(version)
    if not fits(version):
        raise ValueError("%s: text does not fit version %d-%s" % (op, version, ec))

    blocks = _block_layout(version, ec)
    n_data = sum(b[0] for b in blocks)
    bb = _BitBuffer()
    bb.put(_MODE_BITS[mode], 4)
    bb.put(count, _count_bits(mode, version))
    bb.bits.extend(payload)
    cap = n_data * 8
    bb.bits.extend([0] * min(4, cap - len(bb.bits)))       # 終端 / terminator
    bb.bits.extend([0] * ((-len(bb.bits)) % 8))             # バイト境界 / byte align
    data = [int("".join(map(str, bb.bits[k:k + 8])), 2) for k in range(0, len(bb.bits), 8)]
    pad = (0xEC, 0x11)
    k = 0
    while len(data) < n_data:
        data.append(pad[k % 2])
        k += 1

    # ブロック分割 + RS + インタリーブ / split, RS, interleave
    dblocks, eblocks, p = [], [], 0
    for nd, ne in blocks:
        d = data[p:p + nd]
        p += nd
        dblocks.append(d)
        eblocks.append(rs_encode(QR_FIELD, d, ne, 0))
    codewords = []
    for i in range(max(b[0] for b in blocks)):
        for d in dblocks:
            if i < len(d):
                codewords.append(d[i])
    for i in range(blocks[0][1]):
        for e in eblocks:
            codewords.append(e[i])

    fmask, base, order = _function_layout(version)
    n = fmask.shape[0]
    bits = np.unpackbits(np.asarray(codewords, np.uint8))
    allbits = np.zeros(len(order), np.uint8)
    allbits[:len(bits)] = bits                               # 余りビットは 0 / remainder = 0
    raw = base.copy()
    raw[order[:, 0], order[:, 1]] = allbits
    pats = _mask_patterns(n)

    def build(mk):
        m = raw.copy()
        m[~fmask] ^= pats[mk][~fmask].astype(np.uint8)
        _place_format(m, ec, mk)
        _place_version(m, version)
        return m

    if mask is None:
        best = None
        for mk in range(8):
            m = build(mk)
            s = _penalty(m)
            if best is None or s < best[0]:
                best = (s, mk, m)
        mask, modules = best[1], best[2]
    else:
        mask = int(mask)
        modules = build(mask)
    return {
        "modules": modules, "size": n, "version": version, "ec_level": ec, "mask": mask,
        "mode": mode, "text": text, "blocks": list(blocks), "n_data_codewords": n_data,
        "n_ec_codewords": sum(b[1] for b in blocks), "function_mask": fmask.copy(),
        "codeword_index": _codeword_index_map(version), "codewords": codewords,
    }


# --------------------------------------------------------------------------- #
# モジュール格子の復号 / decoding a module grid                                #
# --------------------------------------------------------------------------- #
class _BitReader:
    def __init__(self, data):
        self.data = data
        self.pos = 0
        self.n = len(data) * 8

    def left(self):
        return self.n - self.pos

    def get(self, k):
        if k > self.left():
            raise QRDecodeError("qr_decode_modules: bit stream ended inside a segment")
        v = 0
        for _ in range(k):
            v = (v << 1) | ((self.data[self.pos >> 3] >> (7 - (self.pos & 7))) & 1)
            self.pos += 1
        return v


#: ECI 指示子 → Python の文字コード名(公開されている割り当て)/ ECI designator -> codec.
_ECI_CODECS = {0: "cp437", 1: "latin-1", 2: "cp437", 3: "latin-1", 4: "iso8859-2",
               5: "iso8859-3", 6: "iso8859-4", 7: "iso8859-5", 8: "iso8859-6", 9: "iso8859-7",
               10: "iso8859-8", 11: "iso8859-9", 12: "iso8859-10", 13: "iso8859-11",
               15: "iso8859-13", 16: "iso8859-14", 17: "iso8859-15", 18: "iso8859-16",
               20: "shift_jis", 21: "cp1250", 22: "cp1251", 23: "cp1252", 24: "cp1256",
               25: "utf-16-be", 26: "utf-8", 27: "ascii", 28: "big5", 29: "gb18030", 30: "euc_kr"}


def _bytes_to_text(raw: bytes, eci):
    if eci is not None:
        codec = _ECI_CODECS.get(eci)
        if codec is None:
            raise QRDecodeError("qr_decode_modules: unsupported ECI designator %d" % eci)
        try:
            return raw.decode(codec)
        except UnicodeDecodeError as e:
            raise QRDecodeError("qr_decode_modules: byte segment is not valid %s" % codec) from e
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def _parse_segments(data, version):
    """データ語列 → (文字列, モード名の列) / data codewords -> (text, modes)."""
    rd = _BitReader(data)
    parts, modes = [], []
    eci = None
    while rd.left() >= 4:
        mi = rd.get(4)
        if mi == 0:
            break
        if mi == 0b0001:
            cnt = rd.get(_count_bits("numeric", version))
            s = []
            k = cnt
            while k >= 3:
                v = rd.get(10)
                if v >= 1000:
                    raise QRDecodeError("qr_decode_modules: invalid numeric triple %d" % v)
                s.append("%03d" % v)
                k -= 3
            if k == 2:
                v = rd.get(7)
                if v >= 100:
                    raise QRDecodeError("qr_decode_modules: invalid numeric pair %d" % v)
                s.append("%02d" % v)
            elif k == 1:
                v = rd.get(4)
                if v >= 10:
                    raise QRDecodeError("qr_decode_modules: invalid numeric digit %d" % v)
                s.append("%d" % v)
            parts.append("".join(s))
            modes.append("numeric")
        elif mi == 0b0010:
            cnt = rd.get(_count_bits("alphanumeric", version))
            s = []
            for _ in range(cnt // 2):
                v = rd.get(11)
                if v >= 45 * 45:
                    raise QRDecodeError("qr_decode_modules: invalid alphanumeric pair %d" % v)
                s.append(_ALNUM[v // 45] + _ALNUM[v % 45])
            if cnt % 2:
                v = rd.get(6)
                if v >= 45:
                    raise QRDecodeError("qr_decode_modules: invalid alphanumeric char %d" % v)
                s.append(_ALNUM[v])
            parts.append("".join(s))
            modes.append("alphanumeric")
        elif mi == 0b0100:
            cnt = rd.get(_count_bits("byte", version))
            raw = bytes(rd.get(8) for _ in range(cnt))
            parts.append(_bytes_to_text(raw, eci))
            modes.append("byte")
        elif mi == 0b1000:
            cnt = rd.get(_count_bits("kanji", version))
            raw = bytearray()
            for _ in range(cnt):
                v = rd.get(13)
                c = ((v // 0xC0) << 8) | (v % 0xC0)
                c += 0x8140 if c < 0x1F00 else 0xC140
                raw += bytes(((c >> 8) & 0xFF, c & 0xFF))
            try:
                parts.append(bytes(raw).decode("shift_jis"))
            except UnicodeDecodeError as e:
                raise QRDecodeError("qr_decode_modules: invalid kanji segment") from e
            modes.append("kanji")
        elif mi == 0b0111:
            b0 = rd.get(8)
            if b0 & 0x80 == 0:
                eci = b0
            elif b0 & 0xC0 == 0x80:
                eci = ((b0 & 0x3F) << 8) | rd.get(8)
            elif b0 & 0xE0 == 0xC0:
                eci = ((b0 & 0x1F) << 16) | rd.get(16)
            else:
                raise QRDecodeError("qr_decode_modules: invalid ECI designator")
            modes.append("eci")
        elif mi in (0b0011, 0b0101, 0b1001):
            raise QRDecodeError("qr_decode_modules: structured append / FNC1 are unsupported")
        else:
            raise QRDecodeError("qr_decode_modules: invalid mode indicator %d" % mi)
    return "".join(parts), modes


def _read_format(m: np.ndarray):
    """形式情報を読む → (ec, mask, 距離) / read format info -> (ec, mask, distance)."""
    n = m.shape[0]
    a, b = _format_coords(n)
    va = sum(int(m[a[i]]) << i for i in range(15))
    vb = sum(int(m[b[i]]) << i for i in range(15))
    best = None
    for (ec, mk), code in _FORMAT_TABLE.items():
        d = min(_popcount(code ^ va), _popcount(code ^ vb))
        if best is None or d < best[0]:
            best = (d, ec, mk)
    if best[0] > 3:
        raise QRDecodeError("qr_decode_modules: format information unreadable (distance %d > 3)" % best[0])
    return best[1], best[2], best[0]


def _read_version_info(m: np.ndarray):
    """型番情報を読む → (型番, 距離) / read version info -> (version, distance)."""
    n = m.shape[0]
    a, b = _version_coords(n)
    va = sum(int(m[a[i]]) << i for i in range(18))
    vb = sum(int(m[b[i]]) << i for i in range(18))
    best = None
    for v, code in _VERSION_TABLE.items():
        d = min(_popcount(code ^ va), _popcount(code ^ vb))
        if best is None or d < best[0]:
            best = (d, v)
    return best[1], best[0]


def _decode_grid(m: np.ndarray) -> dict:
    n = m.shape[0]
    version = (n - 17) // 4
    if version >= 7:
        vi, vd = _read_version_info(m)
        if vd > 3:
            raise QRDecodeError("qr_decode_modules: version information unreadable (distance %d > 3)" % vd)
        if vi != version:
            raise QRDecodeError("qr_decode_modules: version information says %d but the grid is %d" % (vi, version))
    ec, mask, fdist = _read_format(m)
    fmask, _base, order = _function_layout(version)
    um = m.copy()
    um[~fmask] ^= _mask_patterns(n)[mask][~fmask].astype(np.uint8)
    blocks = _block_layout(version, ec)
    total = sum(nd + ne for nd, ne in blocks)
    bits = um[order[:total * 8, 0], order[:total * 8, 1]]
    cws = np.packbits(bits).tolist()
    # デインタリーブ / de-interleave
    nb = len(blocks)
    bdata = [[] for _ in range(nb)]
    k = 0
    for i in range(max(b[0] for b in blocks)):
        for bi, (nd, _ne) in enumerate(blocks):
            if i < nd:
                bdata[bi].append(cws[k])
                k += 1
    becc = [[] for _ in range(nb)]
    for i in range(blocks[0][1]):
        for bi in range(nb):
            becc[bi].append(cws[k])
            k += 1
    p = _P_MISDECODE.get((version, ec), 0)
    data, corrected, capacity = [], [], []
    for bi, (nd, ne) in enumerate(blocks):
        cap = (ne - p) // 2
        try:
            fixed, nchg = rs_decode(QR_FIELD, bdata[bi] + becc[bi], ne, 0)
        except RSDecodeError as e:
            raise QRDecodeError("qr_decode_modules: block %d uncorrectable (%s)" % (bi, e)) from e
        if nchg > cap:
            raise QRDecodeError("qr_decode_modules: block %d needed %d corrections > capacity %d"
                                % (bi, nchg, cap))
        data.extend(fixed[:nd])
        corrected.append(nchg)
        capacity.append(cap)
    text, modes = _parse_segments(data, version)
    return {
        "text": text, "version": version, "ec_level": ec, "mask": mask,
        "mode": next((x for x in modes if x != "eci"), "none"), "modes": modes,
        "n_corrected": int(sum(corrected)), "block_corrected": corrected,
        "block_ec": [ne for _nd, ne in blocks], "block_capacity": capacity,
        "block_p": [p] * nb, "blocks": list(blocks), "format_distance": fdist,
        "codeword_index": _codeword_index_map(version),
    }


def _check_grid(modules) -> np.ndarray:
    op = "qr_decode_modules"
    a = np.asarray(modules)
    if a.ndim != 2 or a.shape[0] != a.shape[1]:
        raise ValueError("%s: modules must be a square 2-D array, got shape %s" % (op, a.shape))
    n = a.shape[0]
    if n < 21 or n > 177 or (n - 17) % 4:
        raise ValueError("%s: grid size must be 17+4v for v in 1..40, got %d" % (op, n))
    if a.dtype.kind not in "biuf":
        raise ValueError("%s: modules must be numeric or bool, got dtype %s" % (op, a.dtype))
    if a.dtype.kind == "f" and not np.all(np.isfinite(a)):
        raise ValueError("%s: modules contain non-finite values" % op)
    if not np.all((a == 0) | (a == 1)):
        raise ValueError("%s: modules must contain only 0/1" % op)
    return a.astype(np.uint8)


def qr_decode_modules(modules) -> dict:
    """モジュール格子(静寂帯なし、1=暗)を復号する。読めなければ転置(鏡像)も試す。

    Decode an (N,N) 0/1 module grid (1 = dark, no quiet zone). The transposed
    (mirrored) grid is tried when the direct read fails.

    Returns a dict with ``text``, ``version``, ``ec_level``, ``mask``, ``mode``,
    ``modes``, ``n_corrected``, ``block_corrected``, ``block_ec``, ``block_capacity``
    (= floor((n_ec - p)/2)), ``block_p`` (誤復号保護語 / misdecode-protection codewords),
    ``blocks``, ``mirrored``, ``format_distance`` and ``codeword_index``. In the
    mirrored case ``codeword_index`` refers to the transposed (read) grid; transpose
    it to index the input grid.

    Raises ``QRDecodeError`` when neither orientation decodes.
    """
    m = _check_grid(modules)
    try:
        out = _decode_grid(m)
        out["mirrored"] = False
        return out
    except QRDecodeError as e1:
        first = e1
    try:
        out = _decode_grid(np.ascontiguousarray(m.T))
        out["mirrored"] = True
        return out
    except QRDecodeError:
        raise first


# --------------------------------------------------------------------------- #
# 画像からの位置検出 / locating the symbol in an image                         #
# --------------------------------------------------------------------------- #
def _check_image(image, op) -> np.ndarray:
    a = np.asarray(image)
    if a.ndim != 2:
        raise ValueError("%s: image must be a 2-D array, got ndim=%d" % (op, a.ndim))
    if a.dtype.kind not in "biuf":
        raise ValueError("%s: image must be numeric, got dtype %s" % (op, a.dtype))
    a = a.astype(np.float64)
    if a.shape[0] < 21 or a.shape[1] < 21:
        raise ValueError("%s: image must be at least 21x21, got %s" % (op, a.shape))
    if not np.all(np.isfinite(a)):
        raise ValueError("%s: image contains non-finite values" % op)
    if a.min() < -1e-6 or a.max() > 1 + 1e-6:
        raise ValueError("%s: image values must lie in [0, 1]" % op)
    return a


def _otsu(img: np.ndarray) -> float:
    hist, edges = np.histogram(img, bins=256, range=(0.0, 1.0))
    hist = hist.astype(np.float64)
    centers = (edges[:-1] + edges[1:]) / 2
    w0 = np.cumsum(hist)
    w1 = w0[-1] - w0
    s0 = np.cumsum(hist * centers)
    mu0 = s0 / np.maximum(w0, 1e-12)
    mu1 = (s0[-1] - s0) / np.maximum(w1, 1e-12)
    between = w0 * w1 * (mu0 - mu1) ** 2
    k = int(np.argmax(between[:-1]))
    return float(edges[k + 1])


def _runs_rows(b: np.ndarray):
    """各行の連長 → (行, 開始列, 長さ, 色) / row runs (row, start, length, colour)."""
    h, w = b.shape
    starts = np.zeros((h, w), bool)
    starts[:, 0] = True
    starts[:, 1:] = b[:, 1:] != b[:, :-1]
    rr, cc = np.nonzero(starts)
    nxt = np.empty_like(cc)
    nxt[:-1] = cc[1:]
    nxt[-1] = w
    brk = np.nonzero(rr[1:] != rr[:-1])[0]
    nxt[brk] = w
    return rr, cc, nxt - cc, b[rr, cc]


def _runs_1d(line: np.ndarray):
    n = line.shape[0]
    st = np.concatenate(([0], np.nonzero(line[1:] != line[:-1])[0] + 1))
    ln = np.diff(np.concatenate((st, [n])))
    return st, ln, line[st]


_TOL = 0.6   # 1:1:3:1:1 の 1 単位の連の許容 / tolerance of the 1-unit runs (fraction of unit)
_TOLC = 0.4  # 中央 3 単位の許容(位置合わせパターン 1:1:1:1:1 を弾く)/ centre-run tolerance


def _ratio_ok(l5) -> bool:
    tot = float(sum(l5))
    if tot < 7:
        return False
    u = tot / 7.0
    t = _TOL * u
    return (abs(l5[0] - u) < t and abs(l5[1] - u) < t and abs(l5[2] - 3 * u) < 3 * _TOLC * u
            and abs(l5[3] - u) < t and abs(l5[4] - u) < t)


def _cross_check(st, ln, col, pos):
    """pos を含む暗い連の周りが 1:1:3:1:1 か → (中心, 総長) / check runs around ``pos``."""
    idx = int(np.searchsorted(st, pos, side="right")) - 1
    if idx < 2 or idx + 2 >= len(st) or col[idx] != 1:
        return None
    l5 = ln[idx - 2:idx + 3]
    if not _ratio_ok(l5):
        return None
    return st[idx] + (ln[idx] - 1) / 2.0, float(l5.sum())


def _finder_candidates(b: np.ndarray):
    """1:1:3:1:1 走査 + 縦・横の再確認 → 候補 (row, col, 横総長, 縦総長)。"""
    rr, cc, L, col = _runs_rows(b)
    if len(L) < 5:
        return []
    k = np.arange(len(L) - 4)
    ok = (rr[k] == rr[k + 4]) & (col[k] == 1)
    l5 = np.stack([L[k + i] for i in range(5)], 1).astype(np.float64)
    tot = l5.sum(1)
    u = tot / 7.0
    t = _TOL * u
    ok &= tot >= 7
    ok &= (np.abs(l5[:, 0] - u) < t) & (np.abs(l5[:, 1] - u) < t) & (np.abs(l5[:, 2] - 3 * u) < 3 * _TOLC * u)
    ok &= (np.abs(l5[:, 3] - u) < t) & (np.abs(l5[:, 4] - u) < t)
    sel = np.nonzero(ok)[0]
    h, w = b.shape
    row_ptr = np.searchsorted(rr, np.arange(h + 1))
    col_cache = {}
    out = []
    for kk in sel:
        r = int(rr[kk])
        cx = cc[kk + 2] + (L[kk + 2] - 1) / 2.0
        th = tot[kk]
        c = int(round(cx))
        if c not in col_cache:
            col_cache[c] = _runs_1d(b[:, c])
        res = _cross_check(*col_cache[c], r)
        if res is None:
            continue
        cy, tv = res
        if not 0.5 < tv / th < 2.0:
            continue
        r2 = int(round(cy))
        a0, a1 = row_ptr[r2], row_ptr[r2 + 1]
        res = _cross_check(cc[a0:a1], L[a0:a1], col[a0:a1], cx)
        if res is None:
            continue
        cx2, th2 = res
        if not 0.5 < th2 / tv < 2.0:
            continue
        out.append((cy, cx2, th2, tv))
    return out


def _cluster(cands):
    clusters = []  # [sum_r, sum_c, sum_h, sum_v, count]
    for r, c, th, tv in cands:
        ms = (th + tv) / 14.0
        for cl in clusters:
            n = cl[4]
            if math.hypot(cl[0] / n - r, cl[1] / n - c) < 2.0 * max(ms, (cl[2] + cl[3]) / (14.0 * n)):
                cl[0] += r
                cl[1] += c
                cl[2] += th
                cl[3] += tv
                cl[4] += 1
                break
        else:
            clusters.append([r, c, th, tv, 1])
    return [(cl[0] / cl[4], cl[1] / cl[4], cl[2] / cl[4], cl[3] / cl[4], cl[4]) for cl in clusters]


def _pick_finders(clusters):
    """直角二等辺に近い 3 つ → (TL, TR, BL) / choose and order the three finders."""
    cl = sorted(clusters, key=lambda x: -x[4])
    strong = [x for x in cl if x[4] >= 2]
    pool = (strong if len(strong) >= 3 else cl)[:12]
    if len(pool) < 3:
        raise QRDecodeError("qr_locate: fewer than 3 finder patterns found")
    best = None
    from itertools import combinations
    for tri in combinations(pool, 3):
        sizes = [(t[2] + t[3]) / 2 for t in tri]
        if max(sizes) / min(sizes) > 1.8:
            continue
        pts = [np.array([t[1], t[0]]) for t in tri]  # (x, y)
        d = {(i, j): float(np.linalg.norm(pts[i] - pts[j])) for i, j in ((0, 1), (0, 2), (1, 2))}
        (i, j), hyp = max(d.items(), key=lambda kv: kv[1])
        corner = 3 - i - j
        a = d[tuple(sorted((corner, i)))]
        bb = d[tuple(sorted((corner, j)))]
        if min(a, bb) < 1e-6:
            continue
        ms = np.mean(sizes) / 7.0
        if min(a, bb) / ms < 7:
            continue
        err = abs(a - bb) / max(a, bb) + 2 * abs(hyp / math.hypot(a, bb) - 1)
        if err > 0.6:
            continue
        score = err + 0.5 / math.sqrt(min(t[4] for t in tri))
        if best is None or score < best[0]:
            best = (score, corner, i, j, tri)
    if best is None:
        raise QRDecodeError("qr_locate: no finder triple forms a plausible QR geometry")
    _s, corner, i, j, tri = best
    tl, p1, p2 = tri[corner], tri[i], tri[j]
    v1 = (p1[1] - tl[1], p1[0] - tl[0])
    v2 = (p2[1] - tl[1], p2[0] - tl[0])
    cross = v1[0] * v2[1] - v1[1] * v2[0]
    tr, bl = (p1, p2) if cross > 0 else (p2, p1)
    return tl, tr, bl


def _hmap(H, pts):
    """モジュール (x, y) → 画像 (x, y) / map module points to image points."""
    pts = np.asarray(pts, np.float64)
    q = np.c_[pts, np.ones(len(pts))] @ H.T
    return q[:, :2] / q[:, 2:3]


def _fit_homography(src, dst):
    """3 点はアフィン、4 点以上は正規化 DLT / affine for 3 points, normalised DLT for >= 4."""
    src = np.asarray(src, np.float64)
    dst = np.asarray(dst, np.float64)
    if len(src) == 3:
        A = np.c_[src, np.ones(3)]
        sol = np.linalg.solve(A, dst)  # (3,2)
        H = np.eye(3)
        H[:2, :] = sol.T
        return H

    def norm(p):
        c = p.mean(0)
        s = math.sqrt(2) / max(np.sqrt(((p - c) ** 2).sum(1)).mean(), 1e-12)
        T = np.array([[s, 0, -s * c[0]], [0, s, -s * c[1]], [0, 0, 1]])
        return T, (np.c_[p, np.ones(len(p))] @ T.T)[:, :2]

    Ts, s = norm(src)
    Td, d = norm(dst)
    rows = []
    for (x, y), (u, v) in zip(s, d):
        rows.append([-x, -y, -1, 0, 0, 0, u * x, u * y, u])
        rows.append([0, 0, 0, -x, -y, -1, v * x, v * y, v])
    _u, _s, vt = np.linalg.svd(np.asarray(rows))
    Hn = vt[-1].reshape(3, 3)
    H = np.linalg.inv(Td) @ Hn @ Ts
    return H / H[2, 2]


def _bilinear(img, rows, cols):
    from scipy.ndimage import map_coordinates
    return map_coordinates(img, [np.ravel(rows), np.ravel(cols)], order=1, mode="nearest").reshape(np.shape(rows))


def _match_template(img, H, center_mod, tmpl, radius_mod):
    """予測位置の周りで型板と相関最大の画素位置 → ((x, y), 相関)。

    Search around the predicted position for the pixel offset maximising the Pearson
    correlation between the module template (dark=1) and the darkness of the image
    sampled at the module offsets (via the local Jacobian of ``H``).
    """
    cx, cy = center_mod
    p0, px1, py1 = _hmap(H, [(cx, cy), (cx + 1, cy), (cx, cy + 1)])
    ex, ey = px1 - p0, py1 - p0
    if not (np.all(np.isfinite(p0)) and np.all(np.isfinite(ex)) and np.all(np.isfinite(ey))):
        return p0, -1.0
    h, w = img.shape
    if not (-0.5 <= p0[0] <= w - 0.5 and -0.5 <= p0[1] <= h - 0.5):
        return p0, -1.0
    if not 0.5 <= max(float(np.hypot(*ex)), float(np.hypot(*ey))) <= max(h, w) / 7.0:
        return p0, -1.0
    off = np.array([[dx, dy] for dx, dy, _v in tmpl], np.float64)
    tv = np.array([v for _dx, _dy, v in tmpl])
    tv = (tv - tv.mean()) / tv.std()
    rel = off[:, 0:1] * ex + off[:, 1:2] * ey          # (T,2) px offsets (x,y)
    mod_px = max(float(np.hypot(*ex)), float(np.hypot(*ey)), 1e-6)
    R = radius_mod * mod_px
    step = max(0.5, mod_px / 4.0)

    def search(center, rad, stp):
        g = np.arange(-rad, rad + 1e-9, stp)
        gx, gy = np.meshgrid(g, g)
        cand = np.c_[gx.ravel(), gy.ravel()] + center    # (P,2)
        xs = cand[:, 0:1] + rel[None, :, 0]
        ys = cand[:, 1:2] + rel[None, :, 1]
        vals = -_bilinear(img, ys, xs)                   # darkness
        vals = vals - vals.mean(1, keepdims=True)
        sd = vals.std(1)
        corr = (vals @ tv) / (len(tv) * np.maximum(sd, 1e-9))
        corr[sd < 1e-6] = -1
        k = int(np.argmax(corr))
        # 鋭い画像では相関が台地になる → 台地(最大の近く)の重心 / plateau centroid
        near = (corr >= corr[k] - 0.01) & (np.hypot(*(cand - cand[k]).T) <= 0.75 * mod_px)
        return cand[near].mean(0), float(corr[k])

    c1, _s1 = search(p0, R, step)
    c2, s2 = search(c1, step, step / 4.0)
    return c2, s2


def _timing_score(img, H, n, thr):
    k = np.arange(8, n - 8)
    pts_row = np.c_[k + 0.5, np.full(len(k), 6.5)]     # row 6
    pts_col = np.c_[np.full(len(k), 6.5), k + 0.5]     # col 6
    q = _hmap(H, np.r_[pts_row, pts_col])
    v = _bilinear(img, q[:, 1], q[:, 0]) < thr
    expect = np.r_[k % 2 == 0, k % 2 == 0]
    return float(np.mean(v == expect))


def _sample_grid(img, H, n, thr):
    i, j = np.indices((n, n))
    q = _hmap(H, np.c_[j.ravel() + 0.5, i.ravel() + 0.5])
    return (_bilinear(img, q[:, 1], q[:, 0]) < thr).reshape(n, n).astype(np.uint8)


@lru_cache(maxsize=64)
def _known_pattern(version: int):
    """既知のモジュール値(静寂帯 4 を含む、未知は -1)/ known module values incl. quiet zone.

    Function patterns whose value does not depend on the content (finders,
    separators, timing, alignment) plus a 4-module light quiet zone; format and
    version areas and the dark module are unknown (-1) so that the pattern is
    symmetric under transposition (mirrored symbols).
    """
    fmask, base, _order = _function_layout(version)
    n = fmask.shape[0]
    k = np.full((n + 8, n + 8), 0, np.int8)  # quiet zone = light (0)
    inner = np.where(fmask, base.astype(np.int8), -1)
    a, b = _format_coords(n)
    for rc in a + b + [(n - 8, 8), (8, n - 8)]:
        inner[rc] = -1
    if version >= 7:
        inner[0:6, n - 11:n - 8] = -1
        inner[n - 11:n - 8, 0:6] = -1
    k[4:n + 4, 4:n + 4] = inner
    k.setflags(write=False)
    return k


def _anchor_template(version: int, r: int, c: int, half: int):
    """モジュール (r, c) 周りの既知値で作る型板 / template of known values around (r, c)."""
    k = _known_pattern(version)
    out = []
    for dy in range(-half, half + 1):
        for dx in range(-half, half + 1):
            rr, cc = r + dy + 4, c + dx + 4
            if 0 <= rr < k.shape[0] and 0 <= cc < k.shape[1] and k[rr, cc] >= 0:
                out.append((dx, dy, float(k[rr, cc])))
    return out


def _anchors(version: int):
    """射影推定に使う既知点(ファインダーの中心と四隅、位置合わせパターン)。

    Anchor points (module (row, col)) used to fit the homography: finder centres and
    corners, and every alignment-pattern centre.
    """
    n = 17 + 4 * version
    pts = []
    for r0, c0 in ((0, 0), (0, n - 7), (n - 7, 0)):
        pts.append((r0 + 3, c0 + 3, 4))
        for dr in (0, 6):
            for dc in (0, 6):
                pts.append((r0 + dr, c0 + dc, 2))
    ap = _alignment_positions(version)
    for r in ap:
        for c in ap:
            if (r == 6 and c == 6) or (r == 6 and c == ap[-1]) or (r == ap[-1] and c == 6):
                continue
            pts.append((r, c, 2))
    return pts


def _homography_ok(H, n, shape) -> bool:
    """有限・格子の四隅が同じ側(地平線を跨がない)・画像の近く / sanity of a homography."""
    if H is None or not np.all(np.isfinite(H)):
        return False
    c = np.array([[0, 0, 1], [n, 0, 1], [0, n, 1], [n, n, 1], [n / 2, n / 2, 1]], np.float64) @ H.T
    if not (np.all(c[:, 2] > 1e-9) or np.all(c[:, 2] < -1e-9)):
        return False
    xy = c[:, :2] / c[:, 2:3]
    h, w = shape
    span = max(h, w)
    return bool(np.all(xy > -span) and np.all(xy[:, 0] < w + span) and np.all(xy[:, 1] < h + span))


def _robust_fit(S, D, H_prev, n, shape, tol_px):
    """外れ点を 1 つずつ除きながら当てはめる / fit, dropping the worst outlier until consistent."""
    S, D = list(S), list(D)
    while len(S) >= 4:
        try:
            Hn = _fit_homography(S, D)
        except np.linalg.LinAlgError:
            return H_prev
        if not _homography_ok(Hn, n, shape):
            return H_prev
        res = np.hypot(*(_hmap(Hn, S) - np.asarray(D)).T)
        k = int(np.argmax(res))
        if res[k] <= tol_px:
            return Hn
        del S[k], D[k]
    return H_prev


def _hypothesis(img, fc, v, thr):
    """型番 v を仮定した変換を求める → (H, timing) / homography for version ``v``."""
    n = 17 + 4 * v
    src = [(3.5, 3.5), (n - 3.5, 3.5), (3.5, n - 3.5)]
    dst = [(f[1], f[0]) for f in fc]
    try:
        H = _fit_homography(src, dst)
    except np.linalg.LinAlgError:
        return None, 0.0
    if not _homography_ok(H, n, img.shape):
        return None, 0.0
    mod_px = math.hypot(dst[1][0] - dst[0][0], dst[1][1] - dst[0][1]) / (n - 7)
    if v >= 2:
        br = (n - 6.5, n - 6.5)
        p, s = _match_template(img, H, br, _anchor_template(v, n - 7, n - 7, 2), max(3.0, 0.12 * n))
        if s > 0.6:
            H = _robust_fit(src + [br], dst + [tuple(p)], H, n, img.shape, 1e9)
    # 既知点で反復的に微調整 / iterative refinement on the anchors
    for rad in (1.5, 1.0, 0.6):
        S, D = [], []
        for r, c, half in _anchors(v):
            p, s = _match_template(img, H, (c + 0.5, r + 0.5), _anchor_template(v, r, c, half), rad)
            if s > 0.6:
                S.append((c + 0.5, r + 0.5))
                D.append(tuple(p))
        H = _robust_fit(S, D, H, n, img.shape, max(1.0, 0.5 * mod_px))
    return H, _timing_score(img, H, n, thr)


def _finders(img):
    """ファインダーを探す。大域 Otsu の 2 値化を素の画像と軽く平滑化した画像の両方で走査し、
    候補を合わせて束ねる。見つからなければ局所平均しきい値で再試行。

    Find the 3 finders. Runs are scanned on two global-Otsu binarisations (raw image
    and a lightly Gaussian-smoothed one, which suppresses noise specks that split
    runs) and the candidates are clustered together; a local-mean threshold is the
    fallback.
    """
    from scipy.ndimage import gaussian_filter, uniform_filter
    thr = _otsu(img)
    sm = gaussian_filter(img, 1.0, mode="nearest")
    last = None
    for kind in ("global", "local"):
        if kind == "global":
            lo, hi = np.percentile(img, (2, 98))
            mid = 0.5 * (lo + hi)
            bins = [(img < thr), (sm < thr)]
            if abs(mid - thr) > 0.03:
                bins += [(img < mid), (sm < mid)]
        else:
            w = max(15, (min(img.shape) // 8) | 1)
            bins = [(sm < uniform_filter(sm, w, mode="nearest") - 0.02)]
        cands = []
        for b in bins:
            cands.extend(_finder_candidates(b.astype(np.uint8)))
        try:
            return _pick_finders(_cluster(cands)), thr
        except QRDecodeError as e:
            last = e
    raise last


def _locate_hypotheses(img, max_hyp=6):
    fc, thr = _finders(img)
    tl, tr, bl = fc
    vx = (tr[1] - tl[1], tr[0] - tl[0])
    theta = math.atan2(vx[1], vx[0])
    fold = max(abs(math.cos(theta)), abs(math.sin(theta)))
    ms = float(np.mean([(f[2] + f[3]) / 2 for f in fc])) / 7.0 * fold
    d = (math.hypot(tr[0] - tl[0], tr[1] - tl[1]) + math.hypot(bl[0] - tl[0], bl[1] - tl[1])) / 2
    n_est = d / ms + 7
    v0 = int(min(40, max(1, round((n_est - 17) / 4))))
    centers = [(f[0], f[1]) for f in fc]
    tried = {}

    def evaluate(v):
        if v not in tried:
            H, ts = _hypothesis(img, centers, v, thr)
            tried[v] = (ts, H)
            if H is None:
                return 0.0, None
        return tried[v]

    order = sorted({min(40, max(1, v0 + dv)) for dv in (0, -1, 1, -2, 2)}, key=lambda v: abs(v - v0))
    extra = []
    for v in order:
        ts, H = evaluate(v)
        if H is None:
            continue
        if v < 7:
            if ts >= 0.97:
                break
            continue
        # 型番情報が読めればそれも候補に / a readable version info adds a candidate
        g = _sample_grid(img, H, 17 + 4 * v, thr)
        vi, vd = _read_version_info(g)
        if vd <= 3 and vi == v and ts >= 0.9:
            break
        if vd <= 3 and vi != v and vi not in extra:
            extra.append(vi)
    for vi in extra:
        if abs(vi - v0) <= 6:
            evaluate(vi)
    hyps = sorted(((v, th) for v, th in tried.items() if th[1] is not None),
                  key=lambda kv: (-kv[1][0], abs(kv[0] - v0)))
    if not hyps:
        raise QRDecodeError("qr_locate: no consistent grid hypothesis")
    out = []
    for v, (ts, H) in hyps[:max_hyp]:
        n = 17 + 4 * v
        fxy = _hmap(H, [(3.5, 3.5), (n - 3.5, 3.5), (3.5, n - 3.5)])   # refined (x, y)
        # 1 モジュールの画素長 = 中心付近の局所ヤコビアンの平均 / local module pitch
        c0, cx1, cy1 = _hmap(H, [(n / 2, n / 2), (n / 2 + 1, n / 2), (n / 2, n / 2 + 1)])
        mpx = 0.5 * (float(np.hypot(*(cx1 - c0))) + float(np.hypot(*(cy1 - c0))))
        out.append({"homography": H, "size": n, "version": v,
                    "finder_centers": fxy[:, ::-1].copy(), "module_px": mpx,
                    "timing_score": ts, "threshold_hint": thr})
    return out


def qr_locate(image) -> dict:
    """画像から QR を見つけ、モジュール空間→画像の射影変換を推定する。

    Locate a QR symbol (dark modules on a light background) in a 2-D float image in
    [0, 1]. Returns ``homography`` (module [x=col, y=row, 1] -> image [x=col_px,
    y=row_px, w]), ``size``, ``version``, ``finder_centers`` (3,2) (row, col) px in
    TL/TR/BL order, ``module_px`` and ``timing_score`` (fraction of timing modules
    read as expected, a sanity measure). Raises ``QRDecodeError`` if not found.
    """
    img = _check_image(image, "qr_locate")
    hyps = _locate_hypotheses(img)
    out = dict(hyps[0])
    out.pop("threshold_hint", None)
    return out


def qr_sample(image, located=None) -> dict:
    """モジュール中心の反射率を双一次補間で取り、大域しきい値で 2 値化する。

    Sample module-centre reflectance (bilinear) and binarise with one global threshold
    midway between the dark- and light-module means (refined iteratively).
    Returns ``reflectance`` (N,N), ``modules`` (N,N) uint8 (dark=1), ``threshold``,
    ``homography`` and ``centers`` (N,N,2) pixel (row, col).
    """
    img = _check_image(image, "qr_sample")
    if located is None:
        located = qr_locate(img)
    if not isinstance(located, dict) or "homography" not in located or "size" not in located:
        raise ValueError("qr_sample: located must be a dict from qr_locate")
    H = np.asarray(located["homography"], np.float64)
    n = int(located["size"])
    if H.shape != (3, 3) or not np.all(np.isfinite(H)):
        raise ValueError("qr_sample: homography must be a finite 3x3 array")
    if n < 21 or n > 177 or (n - 17) % 4:
        raise ValueError("qr_sample: size must be 17+4v for v in 1..40, got %d" % n)
    i, j = np.indices((n, n))
    q = np.c_[j.ravel() + 0.5, i.ravel() + 0.5, np.ones(n * n)] @ H.T
    if np.any(np.abs(q[:, 2]) < 1e-12):
        raise QRDecodeError("qr_sample: degenerate homography")
    xy = q[:, :2] / q[:, 2:3]
    h, w = img.shape
    if (xy[:, 0].min() < -0.5 or xy[:, 0].max() > w - 0.5 or xy[:, 1].min() < -0.5
            or xy[:, 1].max() > h - 0.5):
        raise QRDecodeError("qr_sample: module centres fall outside the image")
    refl = _bilinear(img, xy[:, 1], xy[:, 0]).reshape(n, n)
    t = float(refl.mean())
    for _ in range(3):
        lo = refl[refl < t]
        hi = refl[refl >= t]
        if lo.size == 0 or hi.size == 0:
            raise QRDecodeError("qr_sample: no contrast between modules")
        t = float((lo.mean() + hi.mean()) / 2)
    centers = np.stack([xy[:, 1].reshape(n, n), xy[:, 0].reshape(n, n)], -1)
    return {"reflectance": refl, "modules": (refl < t).astype(np.uint8), "threshold": t,
            "homography": H, "centers": centers}


def qr_read(image) -> dict:
    """位置検出 → 標本化 → 復号。失敗したら明暗反転画像でも試す(``inverted``)。

    Locate, sample and decode; if that fails, retry on the inverted image
    (light-on-dark symbols) and report ``inverted``. Returns the decode dict plus
    ``homography``, ``reflectance``, ``threshold`` and ``inverted``.
    """
    img = _check_image(image, "qr_read")
    errors = []
    for inverted in (False, True):
        src = 1.0 - img if inverted else img
        try:
            hyps = _locate_hypotheses(src)
        except QRDecodeError as e:
            errors.append(str(e))
            continue
        for loc in hyps:
            try:
                s = qr_sample(src, loc)
                d = qr_decode_modules(s["modules"])
            except QRDecodeError as e:
                errors.append(str(e))
                continue
            d.update({"homography": s["homography"], "reflectance": s["reflectance"],
                      "threshold": s["threshold"], "inverted": inverted})
            return d
    raise QRDecodeError("qr_read: no QR symbol decoded (%s)" % "; ".join(errors[:4]))
