# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""dmsym(Data Matrix ECC200)の検査 —— 真値は独立に持つ。

Tests for ``dmsym``. Independent truth:

* 往復: 符号化した文字列そのもの / round trip against the source text;
* 誤りの注入: ``codeword_index`` で選んだ符号語の module を反転し、直した語数 = 注入数;
* zxing-cpp(別実装、Apache-2.0)で双方向に読み合わせ、行列が一致するかも見る;
* 画像: テスト内で描いた記号(射影・ぼけ・雑音・打刻の丸点)。真の角は描画側の射影から。
"""
from __future__ import annotations

import time

import numpy as np
import pytest
from scipy import ndimage

import dmsym
from dmsym import DMDecodeError, DM_SIZES, dm_decode_modules, dm_encode, dm_locate, dm_read, dm_sample

SQUARE = [s for s in DM_SIZES if s[0] == s[1]]
RECT = [s for s in DM_SIZES if s[0] != s[1]]


# ---------------------------------------------------------------------------------------------
# 描画(テスト側の独立実装)/ test-side renderer, independent of dmsym
# ---------------------------------------------------------------------------------------------
def _dlt(src, dst):
    A = []
    for (x, y), (u, v) in zip(src, dst):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y, -u])
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y, -v])
    H = np.linalg.svd(np.asarray(A, float))[2][-1].reshape(3, 3)
    return H / H[2, 2]


def render(modules, m=5.0, quiet=2.0, angle=0.0, tilt=0.0, blur=0.0, noise=0.0, dot=False,
           seed=0, dark=0.1, light=0.9, mirror=False, ss=3):
    """module 行列を画像へ(回転・3-D 傾き・ぼけ・雑音・丸点)。戻り値 (画像, 真の射影)。

    Render a module matrix: in-plane rotation ``angle``, plane tilted by ``tilt``
    degrees about the image's vertical axis seen through a pinhole (f = 3 x symbol
    size), ``ss``x``ss`` supersampling, Gaussian blur ``blur`` (in modules), additive
    noise. ``dot`` draws each dark module as a disc of diameter 0.8 module.
    Returns (image, H) with H mapping module space (x=col, y=row) to pixel-centre
    image coordinates (x=col, y=row).
    """
    R, C = modules.shape
    cm = np.array([[0, 0], [C, 0], [C, R], [0, R]], float)
    W = np.c_[cm[:, 0] - C / 2, cm[:, 1] - R / 2]
    if mirror:
        W[:, 0] = -W[:, 0]
    th = np.radians(angle)
    rot = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    P = W @ rot.T * m
    tt = np.radians(tilt)
    f = 3.0 * max(R, C) * m
    Xr, Zr = P[:, 0] * np.cos(tt), P[:, 0] * np.sin(tt)
    ic = np.c_[f * Xr / (f + Zr), f * P[:, 1] / (f + Zr)]
    pad = quiet * m + 1
    ic = ic - ic.min(0) + pad
    Wd, Hd = (ic.max(0) + pad).astype(int) + 1
    H = _dlt(cm, ic)
    Hi = np.linalg.inv(H)
    yy, xx = np.mgrid[0:Hd, 0:Wd].astype(float)
    acc = np.zeros_like(xx)
    for dy in range(ss):
        for dx in range(ss):
            px = xx + (dx + 0.5) / ss - 0.5
            py = yy + (dy + 0.5) / ss - 0.5
            q = np.stack([px, py, np.ones_like(px)], -1) @ Hi.T
            mx, my = q[..., 0] / q[..., 2], q[..., 1] / q[..., 2]
            j, i = np.floor(mx).astype(int), np.floor(my).astype(int)
            inside = (i >= 0) & (i < R) & (j >= 0) & (j < C)
            val = np.zeros_like(mx, bool)
            val[inside] = modules[i[inside], j[inside]] == 1
            if dot:
                val &= np.hypot(mx - j - 0.5, my - i - 0.5) < 0.4
            acc += np.where(val, dark, light)
    img = acc / ss ** 2
    if blur > 0:
        img = ndimage.gaussian_filter(img, blur * m)
    if noise > 0:
        img = img + np.random.default_rng(seed).normal(0, noise, img.shape)
    return np.clip(img, 0, 1), H


def _true_corners(H, R, C):
    p = np.c_[np.array([[0, 0], [C, 0], [C, R], [0, R]], float), np.ones(4)] @ H.T
    return (p[:, :2] / p[:, 2:])[:, ::-1]


def _random_text(rng, n, alphabet):
    if alphabet == "digits":
        pool = [ord(c) for c in "0123456789"]
    elif alphabet == "upper":
        pool = [ord(c) for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "]
    elif alphabet == "lower":
        pool = [ord(c) for c in "abcdefghijklmnopqrstuvwxyz0123456789 "]
    elif alphabet == "ascii":
        pool = list(range(1, 128))
    else:
        pool = list(range(0, 256))
    return "".join(chr(pool[k]) for k in rng.integers(0, len(pool), n))


def _block_of(index, n_data, nb):
    return index % nb if index < n_data else (index - n_data) % nb


# ---------------------------------------------------------------------------------------------
# 表と配置 / tables and placement
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("rc", DM_SIZES)
def test_layout_every_codeword_has_eight_modules(rc):
    e = dm_encode("", size=rc)
    ci, fm = e["codeword_index"], e["function_mask"]
    total = e["n_data_codewords"] + e["n_ec_codewords"]
    assert len(e["codewords"]) == total
    counts = np.bincount(ci[ci >= 0], minlength=total)
    assert counts.shape == (total,) and np.all(counts == 8)
    assert np.all(ci[fm] == -1)
    # 機能 module = L 字と交互のクロック / finder L solid, clock alternating
    m = e["modules"]
    R, C = rc
    assert np.all(m[:, 0] == 1) and np.all(m[R - 1, :] == 1)
    assert np.array_equal(m[0, :], (np.arange(C) % 2 == 0).astype(np.uint8))
    assert np.array_equal(m[:, C - 1], ((R - 1 - np.arange(R)) % 2 == 0).astype(np.uint8))
    nonfunc = (~fm) & (ci < 0)
    assert nonfunc.sum() == e["fixed_mask"].sum() and nonfunc.sum() in (0, 4)
    assert sum(b[0] for b in e["blocks"]) == e["n_data_codewords"]
    assert sum(b[1] for b in e["blocks"]) == e["n_ec_codewords"]


# ---------------------------------------------------------------------------------------------
# 往復 / round trip
# ---------------------------------------------------------------------------------------------
def test_round_trip_random_all_sizes():
    rng = np.random.default_rng(20261103)
    n_cases = 0
    alphabets = ["digits", "upper", "lower", "ascii", "latin1"]
    for rc in DM_SIZES:
        cap = dmsym._SPEC[rc][4]
        for rep in range(8):
            alpha = alphabets[rep % len(alphabets)]
            enc = ["auto", "ascii", "c40", "text", "base256"][rep % 5]
            for _ in range(20):
                n = int(rng.integers(0, max(2, cap)))
                txt = _random_text(rng, n, alpha)
                try:
                    e = dm_encode(txt, size=rc, encodation=enc)
                except ValueError:
                    continue
                break
            else:
                txt = _random_text(rng, 1, "digits")
                e = dm_encode(txt, size=rc, encodation=enc)
            d = dm_decode_modules(e["modules"])
            assert d["text"] == txt, (rc, enc, txt)
            assert d["n_corrected"] == 0 and d["finder_errors"] == 0
            assert (d["rows"], d["cols"]) == rc
            assert d["codewords"] == e["codewords"]
            n_cases += 1
    assert n_cases >= 200


def test_auto_size_is_smallest_and_shapes():
    for txt in ["1", "123456", "HELLO WORLD", "x" * 100]:
        e = dm_encode(txt, encodation="ascii")
        need = len(dmsym._enc_ascii(txt.encode("latin-1")))
        smaller = [s for s in SQUARE if dmsym._SPEC[s][4] < dmsym._SPEC[(e["rows"], e["cols"])][4]]
        assert dmsym._SPEC[(e["rows"], e["cols"])][4] >= need
        # 小さい側が空(最小の記号)でも意味のある形: 小さい記号の容量の最大 < 必要量
        assert max((dmsym._SPEC[s][4] for s in smaller), default=-1) < need
    r = dm_encode("ABC123", shape="rectangle")
    assert r["rows"] != r["cols"]
    assert dm_decode_modules(r["modules"])["text"] == "ABC123"


def test_ascii_digit_pairs_and_pad_values():
    e = dm_encode("123456", size=12, encodation="ascii")
    # 3 語の数字対 + 129 + 253 状態の乱数化パッド(位置 5: 129 + (149*5 % 253) + 1 = 369 - 254)
    assert e["data_codewords"][:4] == [142, 164, 186, 129]
    assert e["data_codewords"][4] == 129 + ((149 * 5) % 253) + 1 - 254
    u = dm_encode("\xe9", size=10, encodation="ascii")
    assert u["data_codewords"][:2] == [235, 0xE9 - 128 + 1]


# ---------------------------------------------------------------------------------------------
# 誤りの注入 / error injection
# ---------------------------------------------------------------------------------------------
def _inject(e, per_block, rng):
    m = e["modules"].copy()
    ci = e["codeword_index"]
    nd = e["n_data_codewords"]
    nb = len(e["blocks"])
    total = nd + e["n_ec_codewords"]
    blk = np.array([_block_of(i, nd, nb) for i in range(total)])
    for b in range(nb):
        chosen = rng.choice(np.nonzero(blk == b)[0], size=per_block, replace=False)
        for c in chosen:
            pos = np.argwhere(ci == c)
            k = int(rng.integers(1, 9))
            sel = pos[rng.choice(8, size=k, replace=False)]
            m[sel[:, 0], sel[:, 1]] ^= 1
    return m


INJECT_SIZES = [s for s in DM_SIZES if s[0] * s[1] <= 52 * 52] + [(64, 64), (144, 144)]


@pytest.mark.parametrize("rc", INJECT_SIZES)
def test_error_injection_up_to_capacity(rc):
    rng = np.random.default_rng(rc[0] * 1000 + rc[1])
    txt = _random_text(rng, max(1, dmsym._SPEC[rc][4] // 2), "ascii")
    e = dm_encode(txt, size=rc, encodation="ascii")
    cap = e["blocks"][0][1] // 2
    ks = range(cap + 1) if rc[0] * rc[1] <= 26 * 26 else sorted({0, 1, cap // 2, cap})
    for k in ks:
        d = dm_decode_modules(_inject(e, k, rng))
        assert d["text"] == txt
        assert d["block_corrected"] == [k] * len(e["blocks"])
        assert d["n_corrected"] == k * len(e["blocks"])
        assert d["block_capacity"] == [cap] * len(e["blocks"])


def test_error_injection_beyond_capacity_rate():
    """訂正能力 + 1 語: 拒否されるか、まれに誤訂正。率を測り上限を置く。

    capacity + 1 errors per block must be rejected, or (rarely) miscorrected into a
    different valid codeword. We measure the miscorrection rate honestly.
    """
    rng = np.random.default_rng(7)
    raised = miscorrected = 0
    trials = 0
    for rc in [(10, 10), (12, 12), (14, 14), (16, 16), (18, 18), (22, 22), (8, 18), (12, 26)]:
        cap_cw = dmsym._SPEC[rc][4]
        for _ in range(25):
            txt = _random_text(rng, max(1, cap_cw // 2), "upper")
            e = dm_encode(txt, size=rc, encodation="ascii")
            cap = e["blocks"][0][1] // 2
            trials += 1
            try:
                d = dm_decode_modules(_inject(e, cap + 1, rng))
            except DMDecodeError:
                raised += 1
                continue
            assert d["text"] != txt or d["n_corrected"] != (cap + 1) * len(e["blocks"])
            miscorrected += 1
    rate = miscorrected / trials
    print("beyond-capacity: %d trials, %d rejected, %d miscorrected (%.1f %%)"
          % (trials, raised, miscorrected, 100 * rate))
    assert raised + miscorrected == trials
    assert rate <= 0.10


# ---------------------------------------------------------------------------------------------
# 向き / orientation
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize("rc", [(10, 10), (16, 16), (32, 32), (8, 18), (16, 48)])
def test_rotations_and_mirror(rc):
    txt = "ORIENT-%dx%d" % rc
    e = dm_encode(txt, size=rc, encodation="ascii") if dmsym._SPEC[rc][4] >= 12 else \
        dm_encode("12345", size=rc)
    truth = dm_decode_modules(e["modules"])["text"]
    for mir in (False, True):
        for k in range(4):
            g = np.rot90(np.fliplr(e["modules"]) if mir else e["modules"], k)
            d = dm_decode_modules(g)
            assert d["text"] == truth
            assert d["n_corrected"] == 0
            assert np.array_equal(d["modules"], e["modules"])
            # 記録した正規化で元へ戻る / the reported transform normalises the input
            back = np.rot90(np.fliplr(g) if d["mirrored"] else g, d["rotation"] // 90)
            assert np.array_equal(back, e["modules"])


def test_finder_errors_counted():
    e = dm_encode("FINDER", size=16)
    m = e["modules"].copy()
    m[3, 0] ^= 1
    m[0, 5] ^= 1
    m[15, 7] ^= 1
    d = dm_decode_modules(m)
    assert d["finder_errors"] == 3 and d["text"] == "FINDER"


# ---------------------------------------------------------------------------------------------
# zxing-cpp との突き合わせ / cross-check with zxing-cpp
# ---------------------------------------------------------------------------------------------
def _to_u8(modules, scale, quiet):
    img = np.kron(1 - modules, np.ones((scale, scale))) * 255
    return np.pad(img, quiet * scale, constant_values=255).astype(np.uint8)


def test_zxing_reads_our_symbols():
    zx = pytest.importorskip("zxingcpp")
    rng = np.random.default_rng(99)
    cases = 0
    for rc in DM_SIZES:
        reps = 2 if rc[0] <= 52 else 1
        for rep in range(reps):
            cap = dmsym._SPEC[rc][4]
            alpha = ["upper", "ascii", "latin1", "digits", "lower"][(cases + rep) % 5]
            enc = ["auto", "ascii", "c40", "text", "base256"][cases % 5]
            for _ in range(30):
                txt = _random_text(rng, int(rng.integers(1, cap + 1)), alpha)
                try:
                    e = dm_encode(txt, size=rc, encodation=enc)
                    break
                except ValueError:
                    continue
            else:
                e = dm_encode("7", size=rc)
                txt = "7"
            scale = 3 if rc[0] <= 52 else 2
            res = zx.read_barcodes(_to_u8(e["modules"], scale, 2),
                                   formats=zx.BarcodeFormat.DataMatrix)
            assert len(res) == 1, (rc, enc)
            assert res[0].bytes == txt.encode("latin-1"), (rc, enc, txt)
            cases += 1
    assert cases >= 50


def test_our_decoder_reads_zxing_symbols_and_matrices_match():
    zx = pytest.importorskip("zxingcpp")
    rng = np.random.default_rng(5)
    decoded = matrix_equal = dmre_skipped = ascii_compared = ascii_equal = 0
    sizes_seen = set()
    for n in list(range(1, 60)) + [80, 120, 200, 300, 500, 800, 1100, 1500]:
        alpha = ["upper", "ascii", "digits", "lower"][n % 4]
        txt = _random_text(rng, n, alpha)
        b = zx.create_barcode(txt, zx.BarcodeFormat.DataMatrix)
        a = (np.asarray(zx.write_barcode_to_image(b, add_quiet_zones=False)) < 128).astype(np.uint8)
        if tuple(a.shape) not in dmsym._SPEC:
            dmre_skipped += 1           # zxing は DMRE(ISO/IEC 21471)の長方形も作る / DMRE
            continue
        d = dm_decode_modules(a)
        assert d["text"] == txt and d["n_corrected"] == 0
        decoded += 1
        sizes_seen.add(a.shape)
        # 同じデータ符号語から RS・配置を組み直すと zxing の行列と完全一致するか
        nd = d["rows"] and (len(d["codewords"]) - sum(d["block_ec"]))
        ours, _ = dmsym._symbol_from_data_codewords(d["codewords"][:nd], *a.shape)
        matrix_equal += int(np.array_equal(ours, a))
        # ASCII だけで同じ符号語になる場合は dm_encode の行列ごと比べる
        mine = dm_encode(txt, size=a.shape, encodation="ascii") if d["encodations"] == ["ascii"] else None
        if mine is not None:
            ascii_compared += 1
            if mine["data_codewords"] == d["codewords"][:nd]:
                ascii_equal += 1
                assert np.array_equal(mine["modules"], a)
    print("zxing-made: decoded %d, matrix-identical %d, DMRE skipped %d, ascii-compared %d, "
          "ascii-identical %d, sizes %s" % (decoded, matrix_equal, dmre_skipped, ascii_compared,
                                             ascii_equal, sorted(sizes_seen)))
    assert decoded >= 40 and matrix_equal == decoded
    assert ascii_compared >= 5 and ascii_equal == ascii_compared


def test_dm_read_on_zxing_rendered_image():
    zx = pytest.importorskip("zxingcpp")
    b = zx.create_barcode("FULLSEYE-DPM-0001", zx.BarcodeFormat.DataMatrix)
    img = np.asarray(zx.write_barcode_to_image(b, scale=5, add_quiet_zones=True)).astype(float) / 255
    r = dm_read(img)
    assert r["text"] == "FULLSEYE-DPM-0001" and r["n_corrected"] == 0


# ---------------------------------------------------------------------------------------------
# 画像 / images
# ---------------------------------------------------------------------------------------------
IMAGE_CASES = [
    dict(m=5), dict(m=3), dict(m=10), dict(m=5, angle=17), dict(m=4, angle=45), dict(m=5, angle=90),
    dict(m=5, angle=133), dict(m=5, angle=200), dict(m=5, tilt=20), dict(m=5, angle=133, tilt=20),
    dict(m=4, angle=200, tilt=-20), dict(m=5, blur=0.3), dict(m=5, noise=0.05, seed=3),
    dict(m=6, angle=17, tilt=15, blur=0.3, noise=0.05, seed=4),
    dict(m=8, dot=True), dict(m=6, dot=True, angle=45), dict(m=6, dot=True, angle=30, tilt=15, blur=0.2,
                                                           noise=0.05, seed=5),
    dict(m=5, quiet=1.0, angle=10), dict(m=5, mirror=True, angle=70),
]


@pytest.mark.parametrize("kw", IMAGE_CASES, ids=lambda kw: ",".join("%s=%s" % kv for kv in kw.items()))
@pytest.mark.parametrize("rc", [(16, 16), (26, 26), (12, 36)])
def test_dm_read_images(kw, rc):
    txt = {(16, 16): "PART-0042-XYZ", (26, 26): "LOT 2026-11-03 SN 000123 FULLSEYE",
           (12, 36): "RECT 12x36 OK"}[rc]
    e = dm_encode(txt, size=rc)
    img, H = render(e["modules"], **kw)
    r = dm_read(img)
    assert r["text"] == txt
    assert (r["rows"], r["cols"]) == rc
    assert r["inverted"] is False
    assert r["image_mirrored"] == bool(kw.get("mirror", False))
    # 角の位置: 真の射影との差 < 0.35 module(打刻は丸点の縁が 0.1 module 内側なので 0.4)
    tc = _true_corners(H, *rc)
    err = np.hypot(*(r["corners"] - tc).T) / kw["m"]
    assert err.max() < (0.4 if kw.get("dot") else 0.35), err
    loc = dm_locate(img)
    assert (loc["rows"], loc["cols"]) in (rc, rc[::-1])


def test_dm_read_bigger_symbols():
    for rc, m in [((32, 32), 4), ((48, 48), 3), ((64, 64), 3), ((16, 48), 4)]:
        rng = np.random.default_rng(rc[0])
        txt = _random_text(rng, dmsym._SPEC[rc][4] - 2, "upper")
        e = dm_encode(txt, size=rc, encodation="ascii")
        img, _ = render(e["modules"], m=m, angle=12, tilt=10, blur=0.2, noise=0.03, seed=rc[0])
        r = dm_read(img)
        assert r["text"] == txt and (r["rows"], r["cols"]) == rc


def test_dm_read_inverted_light_on_dark():
    e = dm_encode("INVERTED 01", size=16)
    img, _ = render(e["modules"], m=5, angle=25, dark=0.9, light=0.1)
    r = dm_read(img)
    assert r["text"] == "INVERTED 01" and r["inverted"] is True


def test_dm_sample_matches_truth_and_threshold():
    e = dm_encode("SAMPLE", size=14)
    img, H = render(e["modules"], m=6, angle=33, tilt=12, blur=0.2, noise=0.02, seed=1)
    s = dm_sample(img)
    assert s["modules"].shape == (14, 14) and s["centers"].shape == (14, 14, 2)
    dec = dm_decode_modules(s["modules"])
    canon = np.rot90(np.fliplr(s["modules"]) if dec["mirrored"] else s["modules"], dec["rotation"] // 90)
    assert np.array_equal(canon, e["modules"])
    assert 0.3 < s["threshold"] < 0.7
    r = dm_read(img)
    jj, ii = np.meshgrid(np.arange(14) + 0.5, np.arange(14) + 0.5)
    p = np.c_[jj.ravel(), ii.ravel(), np.ones(196)]
    got = p @ r["homography"].T
    want = p @ H.T
    d = np.hypot(*(got[:, :2] / got[:, 2:] - want[:, :2] / want[:, 2:]).T)
    assert d.max() < 0.3 * 6           # 正規化後の射影で module 中心が真値と 0.3 module 以内
    assert r["reflectance"].shape == (14, 14)


def test_dm_read_speed():
    e = dm_encode("SPEED TEST 123456", size=20)
    img, _ = render(e["modules"], m=7, angle=30, blur=0.2, noise=0.03, seed=2)
    assert 150 <= img.shape[0] <= 260
    dm_read(img)
    best = min(_timed(dm_read, img) for _ in range(3))
    print("dm_read on %s: %.1f ms" % (img.shape, 1000 * best))
    assert best < 0.2


def _timed(f, x):
    t0 = time.perf_counter()
    f(x)
    return time.perf_counter() - t0


# ---------------------------------------------------------------------------------------------
# 失敗は閉じる / fail-closed
# ---------------------------------------------------------------------------------------------
def test_fail_closed_images():
    with pytest.raises(DMDecodeError):
        dm_read(np.full((120, 120), 0.8))
    with pytest.raises(DMDecodeError):
        dm_read(np.random.default_rng(0).random((120, 120)))
    with pytest.raises(DMDecodeError):
        dm_locate(np.full((64, 64), 0.5))
    bad = np.full((64, 64), 0.5)
    bad[3, 3] = np.nan
    for f in (dm_read, dm_locate, dm_sample):
        with pytest.raises(ValueError):
            f(bad)
        with pytest.raises(ValueError):
            f(np.zeros((40, 40, 3)))
    with pytest.raises(ValueError):
        dm_sample(np.full((64, 64), 0.5), located={"nope": 1})
    assert issubclass(DMDecodeError, ValueError)


def test_fail_closed_modules_and_encode():
    with pytest.raises(DMDecodeError):
        dm_decode_modules(np.zeros((11, 11), np.uint8))           # 対応しない大きさ
    with pytest.raises(DMDecodeError):
        dm_decode_modules(np.zeros((16, 16), np.uint8))           # 機能パターン無し
    with pytest.raises(ValueError):
        dm_decode_modules(np.full((16, 16), 2))
    with pytest.raises(ValueError):
        dm_decode_modules(np.full((16, 16), np.nan))
    with pytest.raises(ValueError):
        dm_decode_modules(np.zeros((2, 16, 16)))
    with pytest.raises(ValueError):
        dm_encode("あ")                                       # > U+00FF
    with pytest.raises(ValueError):
        dm_encode("x" * 3000)
    with pytest.raises(ValueError):
        dm_encode("x", size=11)
    with pytest.raises(ValueError):
        dm_encode("x", shape="round")
    with pytest.raises(ValueError):
        dm_encode("x", encodation="edifact")
    with pytest.raises(ValueError):
        dm_encode(123)
    with pytest.raises(ValueError):
        dm_encode("x" * 20, size=10)
    # データを全部消した記号は拒否 / all data modules wiped -> rejected
    e = dm_encode("WIPE ME 0123", size=16)
    m = e["modules"].copy()
    m[e["codeword_index"] >= 0] = 0
    with pytest.raises(DMDecodeError):
        dm_decode_modules(m)


# ---------------------------------------------------------------------------------------------
# 回帰: 画素に揃った鋭い打刻(パイプラインの描画器 symrender)/ regression: sharp pixel-aligned dots
# ---------------------------------------------------------------------------------------------
# 原因: 背景が広く濃淡が数段しかない画像で Otsu の閾値がインクの濃度の直上に落ち、
# 完全に塗れた画素だけが暗になって縁が約 1 px 内側へ寄り、module 中心の標本が閾値すれすれになった
# (0 / 90 / 180 / 270 度・5 px で再現)。閾値を暗/明の平均の中点へ寄せて解消。
# Cause: on few-level images with a large background, Otsu sat just above the ink level.
def _symrender():
    return pytest.importorskip("symrender")


@pytest.mark.parametrize("module_px", list(range(3, 11)))
def test_dot_peen_sweep_symrender(module_px):
    SR = _symrender()
    dm = dm_encode("PN12345-LOT2611A")
    fails = []
    for ang in range(0, 360, 15):
        img = SR.render_symbol(dm, float(module_px), rotate_deg=ang, dot=0.8, dark=0.30,
                               light=0.65, supersample=2)
        try:
            ok = dm_read(img)["text"] == dm["text"]
        except DMDecodeError:
            ok = False
        if not ok:
            fails.append(ang)
    assert not fails, "module %d px fails at angles %s" % (module_px, fails)


def test_dot_peen_axis_aligned_exact_report():
    """報告どおりの設定(既定の supersample=4)/ the configuration as reported."""
    SR = _symrender()
    dm = dm_encode("PN12345-LOT2611A")
    for ang in (0, 90, 180, 270, 45):
        img = SR.render_symbol(dm, 5.0, rotate_deg=ang, dot=0.8, dark=0.30, light=0.65)
        assert dm_read(img)["text"] == "PN12345-LOT2611A", ang
