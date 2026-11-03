# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""1-D バーコード(barcode1d)と撮像シミュレーション(symrender)の門。

真値の出どころ / where the truth comes from:
  * 符号化した既知の文字列そのもの(往復で全件戻ること)
  * 公開の検査数字の例(EAN-13 4006381333931、UPC-A 036000291452)
  * **独立な第 2 の実装** zxing-cpp(Apache-2.0、optional)で、こちらの描いた記号を
    読ませ、zxing が作った記号をこちらで読む(どちらかの表の 1 文字の誤りで落ちる)
  * にじみに対する閉形式(似た縁の和はバーの太りで動かない)
"""
from __future__ import annotations

import os
import random
import sys
import zlib

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import barcode1d as B  # noqa: E402
import symrender as SR  # noqa: E402

_C39_PLAIN = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-. "


def _rand_text(rng, sym):
    if sym == "ean13":
        return "".join(rng.choice("0123456789") for _ in range(12))
    if sym == "upca":
        return "".join(rng.choice("0123456789") for _ in range(11))
    if sym == "code128":
        if rng.random() < 0.5:
            return "".join(chr(rng.randint(32, 126)) for _ in range(rng.randint(1, 20)))
        return "".join(rng.choice("0123456789") for _ in range(rng.randint(2, 20)))
    if sym == "code39":
        return "".join(rng.choice(_C39_PLAIN) for _ in range(rng.randint(1, 12)))
    return "".join(rng.choice("0123456789") for _ in range(2 * rng.randint(3, 8)))


# --------------------------------------------------------------------------- #
# 公開の例 / published examples
# --------------------------------------------------------------------------- #
def test_check_digits_match_published_examples():
    assert B.ean_check_digit("400638133393") == 1          # EAN-13 4006381333931
    assert B.ean_check_digit("03600029145") == 2           # UPC-A 036000291452
    e = B.encode_barcode1d("400638133393", "ean13")
    assert e["text"] == "4006381333931"
    assert e["n_modules"] == 95.0                          # 3 + 42 + 5 + 42 + 3
    u = B.encode_barcode1d("03600029145", "upca")
    assert u["text"] == "036000291452"


def test_tables_are_self_consistent():
    # Code 128: 106 文字 × 11 モジュール、停止 13、似た縁の 4 和は一意
    assert all(sum(r) == 11 for r in B._C128_RUNS[:106])
    assert sum(B._C128_RUNS[106]) == 13
    assert all(len(v) == 1 for v in B._C128_KEY.values()) and len(B._C128_KEY) == 106
    # Code 39: 44 文字、どれも太 3 本、パターンは一意
    assert len(B._C39) == 44 and len(set(B._C39.values())) == 44
    assert all(p.count("w") == 3 for p in B._C39.values())
    # ITF: 10 桁、太 2 本、一意
    assert len(set(B._ITF)) == 10 and all(p.count("w") == 2 for p in B._ITF)


# --------------------------------------------------------------------------- #
# 往復 / round trip
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("sym", B.SYMBOLOGIES_1D)
def test_round_trip_at_any_angle(sym):
    # 種は決まった値に(hash(str) は PYTHONHASHSEED でプロセスごとに変わり、CI で毎回違う入力になった)
    rng = random.Random(zlib.crc32(sym.encode("ascii")) & 0xFFFF)
    for _ in range(12):
        enc = B.encode_barcode1d(_rand_text(rng, sym), sym)
        img = SR.render_symbol(enc, module_px=rng.choice([2.0, 3.0, 4.5]),
                               rotate_deg=rng.uniform(-180, 180))
        r = B.read_barcode1d(img, (sym,) if sym != "upca" else ("ean13", "upca"))
        assert r["text"] == enc["text"], (sym, enc["text"], r["text"])
        assert r["symbology"] == sym
        assert not r["conflict"]


def test_scan_direction_is_refined_so_lines_do_not_leave_the_symbol():
    """構造テンソルの向きは 2〜6° ずれ、ずれた走査線が長い ITF の途中で抜けて先頭の 6 桁を
    読んでいた(CI 赤 2026-11-04、"62138232"・2 px・17.9° で votes に 'itf:621382': 1)。
    最初のバーの縁から向きを当て直すと、全走査線が同じ文字列を読み、向きの誤差は 0.1° 未満。"""
    enc = B.encode_barcode1d("62138232", "itf")
    r = B.read_barcode1d(SR.render_symbol(enc, module_px=2.0, rotate_deg=17.9), ("itf",))
    assert r["text"] == "62138232" and not r["conflict"]
    assert r["votes"] == {"itf:62138232": r["n_lines"]}
    errs = []
    for ang in np.linspace(-170.0, 170.0, 18):
        rr = B.read_barcode1d(SR.render_symbol(enc, module_px=2.0, rotate_deg=float(ang)), ("itf",))
        errs.append(abs((rr["angle_deg"] + ang + 90.0) % 180.0 - 90.0))   # render は逆回り
    assert len(errs) == 18 and max(errs) < 0.1, max(errs)


def test_gs1_128_fnc1_round_trip():
    enc = B.encode_barcode1d("0109501101530003\x1d10ABC123", "code128", gs1=True)
    assert enc["values"][1] == 102                          # FNC1 が先頭
    r = B.decode_barcode_profile(SR.render_symbol(enc, 3.0)[30])
    assert r["gs1"] is True and r["text"] == "0109501101530003\x1d10ABC123"


def test_profile_read_reports_direction_and_margins():
    enc = B.encode_barcode1d("FULLSEYE", "code128")
    img = SR.render_symbol(enc, 4.0)
    row = img[img.shape[0] // 2]
    fwd = B.decode_barcode_profile(row)
    rev = B.decode_barcode_profile(row[::-1])
    assert fwd["text"] == rev["text"] == "FULLSEYE"
    assert fwd["reversed"] is False and rev["reversed"] is True
    assert min(fwd["margins"]) > 0.9                        # 理想の描画は判定境界から遠い
    assert abs(fwd["x_dim"] - 4.0) < 0.05


# --------------------------------------------------------------------------- #
# 独立な第 2 の実装 / independent second implementation (zxing-cpp, optional)
# --------------------------------------------------------------------------- #
_ZX = {"ean13": "EAN13", "upca": "UPCA", "code128": "Code128", "code39": "Code39Std", "itf": "ITF"}


@pytest.mark.parametrize("sym", B.SYMBOLOGIES_1D)
def test_zxing_reads_our_symbols(sym):
    zx = pytest.importorskip("zxingcpp")
    rng = random.Random(7 + len(sym))
    for _ in range(12):
        enc = B.encode_barcode1d(_rand_text(rng, sym), sym)
        u8 = (np.clip(SR.render_symbol(enc, 3.0), 0, 1) * 255).astype(np.uint8)
        res = zx.read_barcodes(u8, formats=getattr(zx.BarcodeFormat, _ZX[sym]))
        assert res, (sym, enc["text"])
        t = res[0].text
        if sym == "upca" and len(t) == 13:
            t = t[1:]
        assert t == enc["text"], (sym, enc["text"], t)


@pytest.mark.parametrize("sym", ["ean13", "code128", "code39", "itf"])
def test_we_read_zxing_symbols(sym):
    zx = pytest.importorskip("zxingcpp")
    rng = random.Random(11 + len(sym))
    for _ in range(10):
        txt = _rand_text(rng, sym)
        if sym == "ean13":
            txt = txt + str(B.ean_check_digit(txt))
        bc = zx.create_barcode(txt, getattr(zx.BarcodeFormat, _ZX[sym]))
        img = np.asarray(bc.to_image(scale=3), dtype=np.float64) / 255.0
        img = np.pad(img, 20, constant_values=1.0) * 0.8 + 0.05
        r = B.read_barcode1d(img, (sym,))
        assert r["text"] == bc.text, (sym, bc.text, r["text"])


# --------------------------------------------------------------------------- #
# にじみ(閉形式)/ ink spread
# --------------------------------------------------------------------------- #
def test_similar_edge_decoding_is_immune_to_uniform_ink_spread():
    """似た縁の和(バー + 空白)はバーが一様に g 太っても動かない → Code 128 の余裕は
    ほぼ 1 のまま。2 値幅の Code 39 は閉形式どおりに余裕が減る。"""
    enc = B.encode_barcode1d("LOT2026", "code128")
    for g in (-0.3, 0.0, 0.3):
        row = SR.render_symbol(enc, 10.0, ink_gain=g, supersample=8)
        r = B.decode_barcode_profile(row[row.shape[0] // 2])
        assert r["text"] == "LOT2026" and min(r["margins"]) > 0.9, (g, min(r["margins"]))
    # Code 39, 太細比 N, 太り g: 太 2 本がバーの文字では
    #   細の平均 = 1, 太の平均 = (2(N+g) + (N−g))/3, 閾値 rt = 中点,
    #   V = min((rt − (1+g))/(rt − 1), ((N−g) − rt)/(wmean − rt))
    N, g = 2.5, 0.3
    wmean = (2 * (N + g) + (N - g)) / 3.0
    rt = 0.5 * (1.0 + wmean)
    v_closed = min((rt - (1 + g)) / (rt - 1.0), ((N - g) - rt) / (wmean - rt))
    enc39 = B.encode_barcode1d("TEST", "code39")              # T,E,S,T と * はどれも太バー 2 本
    for ch in "*TES":
        assert sum(1 for k in (0, 2, 4, 6, 8) if B._C39[ch][k] == "w") == 2
    row = SR.render_symbol(enc39, 12.0, ink_gain=g, supersample=8)
    r = B.decode_barcode_profile(row[row.shape[0] // 2])
    assert r["text"] == "TEST"
    assert abs(min(r["margins"]) - v_closed) < 0.05, (min(r["margins"]), v_closed)


def test_short_reads_are_refused():
    """ぼけた EAN-13 を全体系で読んでも、短い ITF 等の誤読を返さない(実測で見つかった穴)。"""
    enc = B.encode_barcode1d("4901234567894", "ean13")
    wrong = 0
    for k, d in enumerate(np.linspace(6.6, 7.6, 12)):
        img = SR.capture_degrade(SR.render_symbol(enc, 3.0, offset_px=(0.1 * k, 0.0)),
                                 defocus_px=float(d), full_well_e=20000, read_noise_e=10, seed=k)
        try:
            r = B.read_barcode1d(img)                          # 全体系を許す
        except B.Barcode1DError:
            continue
        wrong += r["text"] != enc["text"]
    assert wrong == 0


# --------------------------------------------------------------------------- #
# 撮像シミュレーション / capture model
# --------------------------------------------------------------------------- #
def test_render_reflectance_and_area_coverage():
    enc = B.encode_barcode1d("12345678", "itf")
    img = SR.render_symbol(enc, 4.0, dark=0.1, light=0.9)
    assert abs(img.max() - 0.9) < 1e-12 and abs(img.min() - 0.1) < 1e-12
    # 1 行の暗さの総量 = バーの総幅(モジュール)× module_px × (light − dark)
    row = img[img.shape[0] // 2]
    bar_modules = float(enc["widths"][0::2].sum())
    assert abs(float((0.9 - row).sum()) - bar_modules * 4.0 * 0.8) < 1e-6
    g = SR.render_symbol(enc, 4.0, return_geometry=True)
    H = g["homography"]
    p = H @ np.array([enc["edges"][0], 5.0, 1.0])
    assert abs(p[0] / p[2] - (2.0 + enc["edges"][0]) * 4.0) < 1e-6   # 余白 2 モジュール


def test_capture_degrade_physics():
    a = np.full((40, 40), 0.5)
    # 照明の傾き: 左右の端で 1 ± slope/2
    e = SR.capture_degrade(a, illum_slope=0.4)
    assert abs(e[20, -1] / e[20, 0] - 1.2 / 0.8) < 1e-9
    # ぼけは平均を保つ(境界は複製)/ blur conserves the mean of a flat field
    b = SR.capture_degrade(a, defocus_px=5.0, motion_px=4.0, gauss_px=1.0)
    assert np.allclose(b, 0.5)
    # ショット雑音の分散 = 平均 / full_well(電子数で Poisson)
    n = SR.capture_degrade(np.full((200, 200), 0.5), full_well_e=1000.0, seed=3)
    assert abs(n.var() - 0.5 / 1000.0) / (0.5 / 1000.0) < 0.05
    # 同じ種 → 同じ結果
    assert np.array_equal(n, SR.capture_degrade(np.full((200, 200), 0.5), full_well_e=1000.0, seed=3))


def test_fail_closed():
    with pytest.raises(ValueError):
        B.encode_barcode1d("", "ean13")
    with pytest.raises(ValueError):
        B.encode_barcode1d("4006381333932", "ean13")        # 検査数字の不一致
    with pytest.raises(ValueError):
        B.encode_barcode1d("123", "itf")                    # 奇数桁
    with pytest.raises(ValueError):
        B.encode_barcode1d("abc", "code39")                 # 小文字は字種の外
    with pytest.raises(ValueError):
        B.encode_barcode1d("A", "pdf417")
    with pytest.raises(ValueError):
        B.decode_barcode_profile(np.full(10, 0.5))
    with pytest.raises(B.Barcode1DError):
        B.decode_barcode_profile(np.full(100, 0.5))
    with pytest.raises(ValueError):
        B.read_barcode1d(np.full((20, 20, 3), 0.5))
    with pytest.raises(ValueError):
        B.read_barcode1d(np.full((20, 20), np.nan))
    with pytest.raises(B.Barcode1DError):
        B.read_barcode1d(np.random.default_rng(0).random((60, 60)))
    with pytest.raises(ValueError):
        SR.render_symbol({"foo": 1})
    with pytest.raises(ValueError):
        SR.render_symbol(B.encode_barcode1d("1", "code39"), dark=0.9, light=0.1)
    with pytest.raises(ValueError):
        SR.capture_degrade(np.ones((5, 5)), read_noise_e=3.0)       # 電子数が無いのに雑音
