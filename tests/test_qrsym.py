# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""qrsym(QR Code の自前符号化・復号・画像読み取り)の検査。

Tests for ``qrsym``. Ground truth is independent of the code under test:

* 公開チュートリアル(thonky.com)の "HELLO WORLD" 1-M の符号語、形式情報の表の値。
  Published codewords of "HELLO WORLD" 1-M and format-information strings (thonky.com).
* 公開表の総符号語数・ブロック構成 / published total-codeword counts and block layouts.
* 独立実装 zxing-cpp との相互読み取り / cross-reading with the independent zxing-cpp.
* 画像試験は試験内で自前に描く(既知のモジュール→画素の写像)/ images are rendered
  here with a known module -> pixel mapping.
"""
from __future__ import annotations

import random
import string
import time

import numpy as np
import pytest
from scipy.ndimage import gaussian_filter

import qrsym
from qrsym import QRDecodeError, qr_decode_modules, qr_encode, qr_locate, qr_read, qr_sample

ALNUM = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:"


# --------------------------------------------------------------------------- #
# 描画(試験専用、qrsym に依存しない)/ rendering, independent of qrsym           #
# --------------------------------------------------------------------------- #
def _homography_4pt(src, dst):
    """4 点対応の射影変換(8 元連立)/ 4-point homography by an 8x8 linear solve."""
    A, b = [], []
    for (x, y), (u, v) in zip(src, dst):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        b.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        b.append(v)
    h = np.linalg.solve(np.asarray(A, float), np.asarray(b, float))
    return np.append(h, 1.0).reshape(3, 3)


def render(mod, ms=5.0, quiet=4, angle=0.0, tilt=0.0, tilt_axis=0.0, blur=0.0, noise=0.0,
           seed=0, dist=3.0):
    """モジュール格子を画像にする。平面(モジュール単位)→ 面内回転 → 傾き(ピンホール)→ 画素。

    Render a module grid: plane (module units) -> tilt about an in-plane axis seen by
    a pinhole camera at ``dist`` x symbol size -> in-plane rotation -> pixels; point
    sampling, then Gaussian blur (sigma = ``blur`` modules) and additive noise.
    Returns (image in [0,1], H_true) where H_true maps module (x=col, y=row) to pixel
    (x, y) with pixel centres at integer coordinates.
    """
    n = mod.shape[0]
    S = n + 2 * quiet
    a = np.pad(np.asarray(mod, np.uint8), quiet)
    th, ta, ax = np.deg2rad(angle), np.deg2rad(tilt), np.deg2rad(tilt_axis)
    D = dist * S

    def fwd(u, v):
        x, y = u - S / 2, v - S / 2
        xr = x * np.cos(ax) + y * np.sin(ax)
        yr = -x * np.sin(ax) + y * np.cos(ax)
        f = D / (D + yr * np.sin(ta))
        xr, yr = xr * f, yr * np.cos(ta) * f
        x = xr * np.cos(ax) - yr * np.sin(ax)
        y = xr * np.sin(ax) + yr * np.cos(ax)
        return (x * np.cos(th) - y * np.sin(th)) * ms, (x * np.sin(th) + y * np.cos(th)) * ms

    cu, cv = np.array([0, S, 0, S], float), np.array([0, 0, S, S], float)
    X, Y = fwd(cu, cv)
    W = int(np.ceil(X.max() - X.min() + 2 * ms))
    Hh = int(np.ceil(Y.max() - Y.min() + 2 * ms))
    X, Y = X - X.min() + ms, Y - Y.min() + ms
    Hp = _homography_4pt(list(zip(cu, cv)), list(zip(X, Y)))      # plane -> pixel
    Hi = np.linalg.inv(Hp)
    rr, cc = np.mgrid[0:Hh, 0:W].astype(float)
    q = Hi @ np.stack([cc.ravel(), rr.ravel(), np.ones(rr.size)])
    u, v = np.floor(q[0] / q[2]).astype(int), np.floor(q[1] / q[2]).astype(int)
    ins = (u >= 0) & (u < S) & (v >= 0) & (v < S)
    val = np.ones(rr.size)
    val[ins] = 1.0 - a[v[ins], u[ins]]
    img = val.reshape(Hh, W)
    if blur:
        img = gaussian_filter(img, blur * ms)
    if noise:
        img = img + np.random.default_rng(seed).normal(0, noise, img.shape)
    T = np.array([[1, 0, quiet], [0, 1, quiet], [0, 0, 1.0]])
    return np.clip(img, 0, 1), Hp @ T


def _rand_text(rng, mode, k):
    if mode == "numeric":
        return "".join(rng.choice(string.digits) for _ in range(k))
    if mode == "alphanumeric":
        return "".join(rng.choice(ALNUM) for _ in range(k))
    pool = string.ascii_letters + string.digits + string.punctuation + " éüß日本語€"
    return "".join(rng.choice(pool) for _ in range(k))


def _encode_fitting(rng, mode, ec, version, mask, kmax):
    """収まる長さまで縮めて符号化 / shrink the text until it fits."""
    k = rng.randint(1, kmax)
    while True:
        t = _rand_text(rng, mode, k)
        try:
            return qr_encode(t, ec, version=version, mask=mask, mode=mode)
        except ValueError:
            if k == 1:
                raise
            k = max(1, k // 2)


# --------------------------------------------------------------------------- #
# 既知の値 / known vectors                                                      #
# --------------------------------------------------------------------------- #
def test_hello_world_1m_codewords_match_published_tutorial():
    e = qr_encode("HELLO WORLD", "M", version=1)
    assert e["mode"] == "alphanumeric"
    assert e["blocks"] == [(16, 10)]
    assert e["codewords"][:16] == [32, 91, 11, 120, 209, 114, 220, 77, 67, 64, 236, 17, 236, 17, 236, 17]
    assert e["codewords"][16:] == [196, 35, 39, 119, 235, 215, 231, 226, 93, 23]


@pytest.mark.parametrize("ec,mask,bits", [
    ("L", 4, "110011000101111"),
    ("L", 0, "111011111000100"),
    ("M", 0, "101010000010010"),
    ("Q", 0, "011010101011111"),
    ("H", 0, "001011010001001"),
])
def test_format_information_placement_matches_published_strings(ec, mask, bits):
    m = qr_encode("A1", ec, version=1, mask=mask)["modules"]
    # 公開の配置: 行 8 の列 0..5,7,8 と列 8 の行 7,5..0 に MSB から / MSB-first placement
    seq = [m[8, c] for c in (0, 1, 2, 3, 4, 5, 7, 8)] + [m[r, 8] for r in (7, 5, 4, 3, 2, 1, 0)]
    assert "".join(str(int(x)) for x in seq) == bits
    n = m.shape[0]
    # 2 つ目の写し: 列 8 の行 n-1..n-7、行 8 の列 n-8..n-1 / second copy
    seq2 = [m[r, 8] for r in range(n - 1, n - 8, -1)] + [m[8, c] for c in range(n - 8, n)]
    assert "".join(str(int(x)) for x in seq2) == bits
    assert m[n - 8, 8] == 1  # 暗モジュール / dark module


def test_version_information_v7_matches_published_string():
    m = qr_encode("VERSION SEVEN", "M", version=7)["modules"]
    n = m.shape[0]
    # 左下の 6x3 区画を、上位 bit から(列 5→0、各列で行 n-9→n-11)/ bottom-left block, MSB first
    seq = [m[n - 11 + r, c] for c in range(5, -1, -1) for r in (2, 1, 0)]
    assert "".join(str(int(x)) for x in seq) == "000111110010010100"


@pytest.mark.parametrize("v,total", [(1, 26), (2, 44), (3, 70), (4, 100), (5, 134), (6, 172),
                                     (7, 196), (8, 242), (9, 292), (10, 346), (40, 3706)])
def test_total_codewords_match_published_table(v, total):
    e = qr_encode("1", "L", version=v)
    assert e["n_data_codewords"] + e["n_ec_codewords"] == total
    assert len(e["codewords"]) == total
    idx = e["codeword_index"]
    counts = np.bincount(idx[idx >= 0].ravel(), minlength=total)
    assert np.all(counts == 8)                          # 1 語 = 8 モジュール
    assert np.all(idx[e["function_mask"]] == -1)
    assert e["modules"].shape == (17 + 4 * v, 17 + 4 * v)


@pytest.mark.parametrize("v,ec,blocks", [
    (1, "L", [(19, 7)]), (1, "M", [(16, 10)]), (1, "Q", [(13, 13)]), (1, "H", [(9, 17)]),
    (2, "M", [(28, 16)]), (5, "Q", [(15, 18), (15, 18), (16, 18), (16, 18)]),
    (3, "H", [(13, 22), (13, 22)]),
])
def test_block_layout_matches_published_table(v, ec, blocks):
    assert qr_encode("1", ec, version=v)["blocks"] == blocks


# --------------------------------------------------------------------------- #
# 往復 / round trip                                                             #
# --------------------------------------------------------------------------- #
def test_round_trip_random_strings_all_modes_levels_versions_masks():
    rng = random.Random(1234)
    seen = set()
    combos = [(v, ec, mask, mode) for v in range(1, 11) for ec in "LMQH" for mask in range(8)
              for mode in ("numeric", "alphanumeric", "byte")]
    rng.shuffle(combos)
    for v, ec, mask, mode in combos[:300]:
        e = _encode_fitting(rng, mode, ec, v, mask, 60)
        d = qr_decode_modules(e["modules"])
        assert d["text"] == e["text"]
        assert d["n_corrected"] == 0
        assert (d["version"], d["ec_level"], d["mask"], d["mode"]) == (v, ec, mask, mode)
        assert d["mirrored"] is False and d["format_distance"] == 0
        assert np.array_equal(d["codeword_index"], e["codeword_index"])
        seen.add((v, ec, mask, mode))
    assert len(seen) >= 200


def test_auto_version_and_mask_and_mirrored_read():
    e = qr_encode("https://example.com/qrsym?x=1")
    assert e["mode"] == "byte" and e["ec_level"] == "M" and e["mask"] in range(8)
    with pytest.raises(ValueError):              # 自動は最小の型番 / smallest version
        qr_encode(e["text"], "M", version=e["version"] - 1)
    d = qr_decode_modules(e["modules"].T)
    assert d["text"] == e["text"] and d["mirrored"] is True


def test_numeric_and_alnum_bit_lengths():
    # 公開の容量: 1-L は数字 41 字・英数字 25 字・バイト 17 字 / published 1-L capacities
    assert qr_encode("1" * 41, "L")["version"] == 1
    assert qr_encode("1" * 42, "L")["version"] == 2
    assert qr_encode("A" * 25, "L")["version"] == 1
    assert qr_encode("A" * 26, "L")["version"] == 2
    assert qr_encode("a" * 17, "L")["version"] == 1
    assert qr_encode("a" * 18, "L")["version"] == 2


# --------------------------------------------------------------------------- #
# 誤り注入 / error injection                                                    #
# --------------------------------------------------------------------------- #
def _block_positions(blocks):
    """インタリーブ後の位置 → ブロックごとの位置の列 / interleaved positions per block."""
    pos = [[] for _ in blocks]
    k = 0
    for i in range(max(nd for nd, _ in blocks)):
        for b, (nd, _ne) in enumerate(blocks):
            if i < nd:
                pos[b].append(k)
                k += 1
    for i in range(blocks[0][1]):
        for b in range(len(blocks)):
            pos[b].append(k)
            k += 1
    return pos


def _inject(e, chosen):
    m = e["modules"].copy()
    idx = e["codeword_index"]
    for cw in chosen:
        m[idx == cw] ^= 1                      # 語の 8 bit をすべて反転 / flip all 8 bits
    return m


CASES = [(1, "L"), (1, "M"), (1, "Q"), (1, "H"), (2, "L"), (3, "L"), (3, "Q"), (5, "H"),
         (7, "M"), (10, "Q")]


@pytest.mark.parametrize("v,ec", CASES)
def test_error_injection_up_to_capacity_is_corrected_and_counted(v, ec):
    rng = random.Random(v * 10 + "LMQH".index(ec))
    e = _encode_fitting(rng, "byte", ec, v, None, 30)
    pos = _block_positions(e["blocks"])
    d0 = qr_decode_modules(e["modules"])
    caps = d0["block_capacity"]
    expected_p = {(1, "L"): 3, (1, "M"): 2, (1, "Q"): 1, (2, "L"): 2, (3, "L"): 1}.get((v, ec), 0)
    assert len(caps) == len(e["blocks"]) >= 1
    for (nd, ne), cap, p in zip(e["blocks"], caps, d0["block_p"]):
        assert p == expected_p and cap == (ne - p) // 2
    assert d0["block_ec"] == [ne for _nd, ne in e["blocks"]]
    for k in range(0, max(caps) + 1):
        chosen, per_block = [], []
        for b, cap in enumerate(caps):
            kb = min(k, cap)
            chosen += rng.sample(pos[b], kb)
            per_block.append(kb)
        d = qr_decode_modules(_inject(e, chosen))
        assert d["text"] == e["text"]
        assert d["n_corrected"] == len(chosen)
        assert d["block_corrected"] == per_block


def test_errors_beyond_capacity_are_rejected_miscorrection_rate_small():
    rng = random.Random(99)
    trials = rejected = miscorrected = 0
    for v, ec in CASES:
        for _ in range(12):
            e = _encode_fitting(rng, "byte", ec, v, None, 30)
            pos = _block_positions(e["blocks"])
            caps = qr_decode_modules(e["modules"])["block_capacity"]
            b = rng.randrange(len(caps))
            chosen = rng.sample(pos[b], caps[b] + 1)
            trials += 1
            try:
                d = qr_decode_modules(_inject(e, chosen))
            except QRDecodeError:
                rejected += 1
                continue
            miscorrected += 1
            assert d["n_corrected"] != len(chosen) or d["text"] != e["text"]
    rate = miscorrected / trials
    print("beyond-capacity: trials=%d rejected=%d miscorrected=%d rate=%.3f"
          % (trials, rejected, miscorrected, rate))
    assert rate <= 0.05


def test_format_info_errors_tolerated_up_to_three_bits():
    e = qr_encode("FORMAT", "Q", version=2, mask=3)
    m = e["modules"].copy()
    for r, c in ((0, 8), (2, 8), (8, 1)):      # 1 つ目の写しに 3 bit / 3 bits in copy 1
        m[r, c] ^= 1
    d = qr_decode_modules(m)
    assert d["text"] == "FORMAT" and d["mask"] == 3 and d["format_distance"] == 0
    n = m.shape[0]
    for r, c in ((8, n - 1), (8, n - 3), (n - 2, 8)):  # 2 つ目にも 3 bit / also copy 2
        m[r, c] ^= 1
    d = qr_decode_modules(m)
    assert d["text"] == "FORMAT" and d["format_distance"] == 3


# --------------------------------------------------------------------------- #
# zxing-cpp との相互読み取り / cross-check with zxing-cpp                        #
# --------------------------------------------------------------------------- #
def _zx_read(zx, modules, scale=3):
    img = np.kron(np.pad((1 - modules) * 255, 4, constant_values=255).astype(np.uint8),
                  np.ones((scale, scale), np.uint8))
    res = zx.read_barcodes(img, formats=zx.BarcodeFormat.QRCode)
    return res[0] if res else None


def test_our_symbols_decode_in_zxing():
    zx = pytest.importorskip("zxingcpp")
    rng = random.Random(7)
    n = 0
    for i in range(60):
        mode = ("numeric", "alphanumeric", "byte")[i % 3]
        ec = "LMQH"[i % 4]
        v = 1 + (i * 3) % 10
        if mode == "byte":   # zxing の推定を避け ASCII に限る / ASCII so no charset guess
            e = None
            k = rng.randint(1, 40)
            while e is None:
                t = "".join(rng.choice(string.ascii_letters + string.digits + " .,:;!?")
                            for _ in range(k))
                try:
                    e = qr_encode(t, ec, version=v, mask=i % 8, mode="byte")
                except ValueError:
                    k = max(1, k // 2)
        else:
            e = _encode_fitting(rng, mode, ec, v, i % 8, 60)
        r = _zx_read(zx, e["modules"])
        assert r is not None and r.text == e["text"], (v, ec, e["text"])
        n += 1
    assert n >= 50


def test_zxing_symbols_decode_in_qrsym():
    zx = pytest.importorskip("zxingcpp")
    rng = random.Random(8)
    texts = ["HELLO WORLD", "0123456789" * 3, "日本語テキスト", "Grüße €", "héllo"]
    pool = string.ascii_letters + string.digits + string.punctuation + " "
    texts += ["".join(rng.choice(pool) for _ in range(rng.randint(1, 120))) for _ in range(35)]
    for i, t in enumerate(texts):
        ec = "LMQH"[i % 4]
        b = zx.create_barcode(t, zx.BarcodeFormat.QRCode, ec_level=ec)
        m = (np.asarray(b.to_image(add_quiet_zones=False)) == 0).astype(np.uint8)
        d = qr_decode_modules(m)
        assert d["text"] == t and d["ec_level"] == ec and d["n_corrected"] == 0
        if i % 4 == 0:
            img = np.kron(np.pad(1.0 - m, 4, constant_values=1.0), np.ones((4, 4)))
            assert qr_read(img)["text"] == t


# --------------------------------------------------------------------------- #
# 画像 / images                                                                 #
# --------------------------------------------------------------------------- #
def test_locate_unwarped_homography_and_finders_accurate():
    e = qr_encode("LOCATE ME", "M", version=3)
    n, ms, q = e["size"], 6, 4
    img = np.kron(np.pad(1.0 - e["modules"], q, constant_values=1.0), np.ones((ms, ms)))
    loc = qr_locate(img)
    assert loc["size"] == n and loc["version"] == 3
    i, j = np.indices((n, n))
    pts = np.c_[j.ravel() + 0.5, i.ravel() + 0.5, np.ones(n * n)] @ loc["homography"].T
    got = pts[:, :2] / pts[:, 2:]
    # kron: モジュール座標 u の画素位置 = (u + q) * ms - 0.5 / pixel of module coordinate u
    want = (np.c_[j.ravel() + 0.5, i.ravel() + 0.5] + q) * ms - 0.5
    assert np.abs(got - want).max() < 0.25 * ms
    fc_want = (np.array([[3.5, 3.5], [3.5, n - 3.5], [n - 3.5, 3.5]]) + q) * ms - 0.5
    assert np.abs(loc["finder_centers"] - fc_want).max() < 0.25 * ms
    assert abs(loc["module_px"] - ms) < 0.1 * ms
    s = qr_sample(img, loc)
    assert np.array_equal(s["modules"], e["modules"])
    assert s["centers"].shape == (n, n, 2) and 0.2 < s["threshold"] < 0.8


@pytest.mark.parametrize("angle", [0, 17, 45, 90, 133, 200])
def test_read_rotation_blur_noise(angle):
    rng = random.Random(angle)
    for v, ec, ms in ((1, "L", 4), (2, "M", 3), (4, "Q", 5), (7, "H", 6), (10, "M", 4)):
        e = _encode_fitting(rng, "byte", ec, v, None, 20)
        img, Ht = render(e["modules"], ms=ms, angle=angle, blur=0.35, noise=0.05, seed=angle + v)
        d = qr_read(img)
        assert d["text"] == e["text"] and d["version"] == v
        # 推定した射影がモジュール中心で真値に一致 / estimated homography matches the truth
        n = e["size"]
        i, j = np.indices((n, n))
        P = np.c_[j.ravel() + 0.5, i.ravel() + 0.5, np.ones(n * n)]
        a, b = P @ d["homography"].T, P @ Ht.T
        err = np.abs(a[:, :2] / a[:, 2:] - b[:, :2] / b[:, 2:]).max()
        assert err < 0.35 * ms, err


@pytest.mark.parametrize("tilt,axis", [(25, 0), (25, 60), (25, 135), (20, 100)])
def test_read_perspective_tilt(tilt, axis):
    rng = random.Random(tilt * 1000 + axis)
    for v, ms in ((1, 5), (3, 4), (6, 5), (9, 4)):
        e = _encode_fitting(rng, "alphanumeric", "M", v, None, 30)
        img, _ = render(e["modules"], ms=ms, angle=rng.uniform(0, 360), tilt=tilt,
                        tilt_axis=axis, blur=0.3, noise=0.05, seed=v)
        assert qr_read(img)["text"] == e["text"]


@pytest.mark.parametrize("ms", [3, 4, 6, 8, 10])
def test_read_module_sizes_and_small_quiet_zone(ms):
    rng = random.Random(ms)
    e = _encode_fitting(rng, "byte", "Q", 3, None, 20)
    img, _ = render(e["modules"], ms=ms, quiet=2, angle=rng.uniform(0, 360),
                    blur=0.3, noise=0.05, seed=ms)
    assert qr_read(img)["text"] == e["text"]


def test_read_random_conditions_sweep():
    rng = random.Random(2026)
    for k in range(40):
        v = rng.randint(1, 10)
        ec = rng.choice("LMQH")
        e = _encode_fitting(rng, "byte", ec, v, None, 10)
        img, _ = render(e["modules"], ms=rng.uniform(3, 10), quiet=rng.choice([3, 4]),
                        angle=rng.uniform(0, 360), tilt=rng.uniform(0, 25),
                        tilt_axis=rng.uniform(0, 180), blur=rng.uniform(0, 0.35),
                        noise=0.05, seed=k)
        assert qr_read(img)["text"] == e["text"], k


def test_read_mirrored_and_inverted():
    e = qr_encode("MIRROR 42", "H", version=2)
    img, _ = render(e["modules"][:, ::-1], ms=5, angle=30, blur=0.2, noise=0.03)
    d = qr_read(img)
    assert d["text"] == "MIRROR 42" and d["mirrored"] is True and d["inverted"] is False
    img, _ = render(e["modules"], ms=5, angle=-20, blur=0.2, noise=0.03)
    d = qr_read(1.0 - img)
    assert d["text"] == "MIRROR 42" and d["inverted"] is True


def test_read_speed_250px():
    e = qr_encode("SPEED TEST 0123456789", "M", version=3)
    img, _ = render(e["modules"], ms=5, angle=17, blur=0.3, noise=0.05)
    assert 220 <= max(img.shape) <= 260
    qr_read(img)
    ts = []
    for _ in range(5):
        t0 = time.perf_counter()
        qr_read(img)
        ts.append(time.perf_counter() - t0)
    print("qr_read %s: median %.4f s" % (img.shape, float(np.median(ts))))
    assert float(np.median(ts)) < 0.2


# --------------------------------------------------------------------------- #
# 失敗は閉じる / fail-closed                                                    #
# --------------------------------------------------------------------------- #
def test_blank_and_noise_images_raise_decode_error():
    with pytest.raises(QRDecodeError):
        qr_read(np.ones((200, 200)))
    with pytest.raises(QRDecodeError):
        qr_locate(np.full((120, 120), 0.5))
    with pytest.raises(QRDecodeError):
        qr_read(np.random.default_rng(0).random((150, 150)))


def test_invalid_images_raise_value_error():
    bad = np.ones((100, 100))
    bad[5, 5] = np.nan
    for f in (qr_read, qr_locate, qr_sample):
        with pytest.raises(ValueError):
            f(bad)
        with pytest.raises(ValueError):
            f(np.ones((50, 50, 3)))
        with pytest.raises(ValueError):
            f(np.full((60, 60), 2.0))
        with pytest.raises(ValueError):
            f(np.ones((10, 10)))
    assert issubclass(QRDecodeError, ValueError)


def test_invalid_encode_arguments():
    with pytest.raises(ValueError):
        qr_encode(b"bytes")
    with pytest.raises(ValueError):
        qr_encode("A", ec_level="X")
    with pytest.raises(ValueError):
        qr_encode("A", version=0)
    with pytest.raises(ValueError):
        qr_encode("A", version=41)
    with pytest.raises(ValueError):
        qr_encode("A", mask=8)
    with pytest.raises(ValueError):
        qr_encode("abc", mode="numeric")
    with pytest.raises(ValueError):
        qr_encode("abc", mode="alphanumeric")
    with pytest.raises(ValueError):
        qr_encode("A", mode="kanji")
    with pytest.raises(ValueError):
        qr_encode("a" * 18, "L", version=1)
    with pytest.raises(ValueError):
        qr_encode("a" * 3000, "H")


def test_invalid_grids():
    with pytest.raises(ValueError):
        qr_decode_modules(np.zeros((22, 22)))
    with pytest.raises(ValueError):
        qr_decode_modules(np.zeros((21, 25)))
    with pytest.raises(ValueError):
        qr_decode_modules(np.full((21, 21), 2))
    g = np.zeros((21, 21))
    g[0, 0] = np.inf
    with pytest.raises(ValueError):
        qr_decode_modules(g)
    with pytest.raises(QRDecodeError):
        qr_decode_modules(np.zeros((21, 21), np.uint8))
    rng = np.random.default_rng(3)
    for _ in range(20):
        with pytest.raises(QRDecodeError):
            qr_decode_modules(rng.integers(0, 2, (25, 25)))


def test_sample_rejects_bad_located():
    img = np.ones((100, 100))
    with pytest.raises(ValueError):
        qr_sample(img, {"homography": np.eye(3)})
    with pytest.raises(ValueError):
        qr_sample(img, {"homography": np.eye(3), "size": 22})
    with pytest.raises(QRDecodeError):
        qr_sample(img, {"homography": np.diag([50.0, 50.0, 1.0]), "size": 21})
