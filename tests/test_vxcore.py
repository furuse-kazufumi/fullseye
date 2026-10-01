# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""vxcore の門: OpenVX 1.3.1 の規範文 [REQ-NNNN] を、規格の書いた式どおりの別実装(画素ごとの素朴なループ)と突き合わせる。"""
import math

import numpy as np
import pytest
from scipy import ndimage

import vxcore as V

RNG = np.random.default_rng(1)
IMG = RNG.integers(0, 256, (23, 31), dtype=np.uint8)
IMG[5:9, 7:12] = 200                                  # 構造(平らな台と段差)を混ぜる —— 一様乱数だけでは境界と平坦部が試されない


@pytest.mark.parametrize("border,mode", [("replicate", "nearest"), ("constant", "constant")])
def test_sobel_is_the_req_0415_kernel(border, mode):
    r = V.vx_sobel3x3(IMG, border=border, constant_value=17)
    a = IMG.astype(np.int32)
    gx = ndimage.correlate(a, V.GX, mode=mode, cval=17)
    gy = ndimage.correlate(a, V.GY, mode=mode, cval=17)
    assert r["gx"].dtype == np.int16 and r["gy"].dtype == np.int16
    assert np.array_equal(r["gx"], gx) and np.array_equal(r["gy"], gy)
    assert r["valid"] == (0, 23, 0, 31)


def test_sobel_undefined_border_reports_the_valid_region():
    r = V.vx_sobel3x3(IMG, border="undefined")
    y0, y1, x0, x1 = r["valid"]
    assert (y0, y1, x0, x1) == (1, 22, 1, 30)
    gx = ndimage.correlate(IMG.astype(np.int32), V.GX, mode="nearest")
    assert np.array_equal(r["gx"][y0:y1, x0:x1], gx[y0:y1, x0:x1])
    assert not r["gx"][0].any() and not r["gx"][:, -1].any()


def _req_0270(x, y):
    """REQ-0270 の C の概念定義を、画素ごとにそのまま写した第 2 実装。"""
    xx = (int(x) * int(x)) & 0xFFFFFFFF
    yy = (int(y) * int(y)) & 0xFFFFFFFF
    z = int(math.sqrt(float(xx) + float(yy)) + 0.5) & 0xFFFF
    return 32767 if z > 32767 else z


def test_magnitude_follows_req_0270_including_saturation():
    gx = np.array([[0, 3, -32768, 32767, 1, -5]], np.int16)
    gy = np.array([[0, 4, -32768, 32767, 1, 12]], np.int16)
    big = RNG.integers(-32768, 32768, (8, 9)).astype(np.int16)
    big2 = RNG.integers(-32768, 32768, (8, 9)).astype(np.int16)
    for a, b in ((gx, gy), (big, big2)):
        m = V.vx_magnitude(a, b)
        want = np.array([[_req_0270(p, q) for p, q in zip(ra, rb)] for ra, rb in zip(a, b)], np.int16)
        assert m.dtype == np.int16 and np.array_equal(m, want)
    assert V.vx_magnitude(gx, gy)[0, 1] == 5 and V.vx_magnitude(gx, gy)[0, 2] == 32767


def test_phase_maps_0_to_2pi_onto_0_to_255():
    axes_x = np.array([[1, 0, -1, 0, 1, -1, -1, 1, 0]], np.int16)
    axes_y = np.array([[0, 1, 0, -1, 1, 1, -1, -1, 0]], np.int16)
    f = V.vx_phase(axes_x, axes_y, mapping="floor")
    assert f.tolist() == [[0, 64, 128, 192, 32, 96, 160, 224, 0]]
    gx = RNG.integers(-1000, 1001, (40, 40)).astype(np.int16)
    gy = RNG.integers(-1000, 1001, (40, 40)).astype(np.int16)
    for mapping in ("floor", "round"):
        p = V.vx_phase(gx, gy, mapping=mapping)
        assert p.dtype == np.uint8
        want = []
        for a, b in zip(gx.ravel(), gy.ravel()):                    # 第 2 実装: math.atan2 を画素ごとに
            phi = math.atan2(float(b), float(a)) % (2 * math.pi)
            u = phi * 256 / (2 * math.pi)
            want.append(int(math.floor(u if mapping == "floor" else u + 0.5)) % 256)
        assert np.array_equal(p.ravel(), np.array(want, np.uint8))
    # 2π の直前(gy が −0 側から近づく)は floor では 255、round では 0 に巻く
    near = (np.array([[1000]], np.int16), np.array([[-1]], np.int16))
    assert V.vx_phase(*near, mapping="floor")[0, 0] == 255 and V.vx_phase(*near, mapping="round")[0, 0] == 0


def test_table_lookup_u8_and_s16():
    ident = np.arange(256, dtype=np.uint8)
    assert np.array_equal(V.vx_table_lookup(IMG, ident), IMG)
    inv = (255 - np.arange(256)).astype(np.uint8)
    assert np.array_equal(V.vx_table_lookup(IMG, inv), 255 - IMG)
    s = np.array([[-32768, -1, 0, 1, 32767]], np.int16)
    tab = (np.arange(65536) - 32768).astype(np.int16)                # 恒等表(中央が 0)
    assert np.array_equal(V.vx_table_lookup(s, tab, offset=32768), s)
    with pytest.raises(ValueError, match="outside the table"):
        V.vx_table_lookup(s, tab, offset=0)


def test_histogram_follows_req_0230():
    for nb, off, rg in ((16, 0, 256), (10, 20, 200), (7, 3, 100)):
        h = V.vx_histogram(IMG, num_bins=nb, offset=off, range_=rg)
        want = np.zeros(nb, np.int64)
        for v in IMG.ravel():                                        # 第 2 実装: 規格の式を画素ごとに
            v = int(v)
            if off <= v < off + rg:
                want[(v - off) * nb // rg] += 1
        assert h.shape == (nb, 2) and np.array_equal(h[:, 1].astype(np.int64), want)
    full = V.vx_histogram(IMG, num_bins=256, offset=0, range_=256)
    assert full[:, 1].sum() == IMG.size
    assert np.array_equal(full[:, 1], np.bincount(IMG.ravel(), minlength=256))


def _nms_by_the_text(p, window, ign):
    """REQ-0337 の不等式を画素ごとに書いた第 2 実装(前の隣は ≥、後ろの隣は >、マスクの画素は比べない)。"""
    h, w = p.shape
    r = window // 2
    keep = np.zeros_like(ign)
    for y in range(h):
        for x in range(w):
            if ign[y, x]:
                continue
            ok = True
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    yy, xx = y + dy, x + dx
                    if (dy, dx) == (0, 0) or not (0 <= yy < h and 0 <= xx < w) or ign[yy, xx]:
                        continue
                    before = dy < 0 or (dy == 0 and dx < 0)
                    if (p[y, x] < p[yy, xx]) if before else (p[y, x] <= p[yy, xx]):
                        ok = False
            keep[y, x] = ok
    return keep


@pytest.mark.parametrize("window", [3, 5])
def test_nonmax_suppression_follows_req_0337_and_0336(window):
    mask = np.zeros(IMG.shape, bool)
    mask[10:14, 2:6] = True
    for img, sup in ((IMG, 0), (IMG.astype(np.int16) - 100, V.INT16_MIN)):
        out = V.vx_nonmax_suppression(img, window=window, mask=mask)
        keep = _nms_by_the_text(img.astype(np.int64), window, mask)
        assert np.array_equal(out[keep], img[keep])
        assert np.array_equal(out[mask], img[mask])                  # REQ-0336: マスクの画素は抑制しない
        assert (out[~(keep | mask)] == sup).all()                    # REQ-0335: S16 は INT16_MIN
        assert 0 < keep.sum() < img.size


def test_a_flat_plateau_keeps_exactly_one_pixel():
    """≥ と > の非対称のため、平らな頂上(2×3)からは 1 画素だけ残る(右下の 1 つ)。"""
    p = np.zeros((7, 8), np.uint8)
    p[2:4, 3:6] = 9
    out = V.vx_nonmax_suppression(p, window=3)
    kept = np.argwhere(out == 9)
    assert kept.tolist() == [[3, 5]]


def test_fail_closed():
    with pytest.raises(ValueError, match="dtype"):
        V.vx_sobel3x3(IMG.astype(np.float64), border="replicate")
    with pytest.raises(ValueError, match="border"):
        V.vx_sobel3x3(IMG, border="wrap")
    with pytest.raises(ValueError, match="shape"):
        V.vx_magnitude(np.zeros((2, 2), np.int16), np.zeros((2, 3), np.int16))
    with pytest.raises(ValueError, match="mapping"):
        V.vx_phase(np.zeros((2, 2), np.int16), np.zeros((2, 2), np.int16), mapping="nearest")
    with pytest.raises(ValueError, match="exceed"):
        V.vx_histogram(IMG, num_bins=300, offset=0, range_=256)
    with pytest.raises(ValueError, match="odd"):
        V.vx_nonmax_suppression(IMG, window=4)
    with pytest.raises(ValueError, match="1-D integer"):
        V.vx_table_lookup(IMG, np.zeros((16, 16), np.uint8))


def test_the_ledger_is_wired():
    import fullseye as fs
    import opsvx
    import typed_catalog
    assert opsvx.missing() == []
    assert set(opsvx.OPSVX) == set(V.__all__)
    for n in V.__all__:
        assert callable(getattr(fs.ledger, n))
    h = fs.ledger.vx_histogram(IMG, num_bins=8, offset=0, range_=256)
    assert np.array_equal(h, V.vx_histogram(IMG, num_bins=8, offset=0, range_=256))
    declared = {name for name, _fam, _ins, _out, _fn in typed_catalog.catalog()}
    assert set(V.__all__) <= declared
    from tools.chain_fuzz import OP_ARG_BUILDERS
    assert set(V.__all__) <= set(OP_ARG_BUILDERS)
