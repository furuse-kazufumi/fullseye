# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""tacscalib の門(視触覚センサの照明を既知球で較正し、勾配 LUT を第 2 実装にする: 真値 = 球の半径の閉形式)。

numpy だけの門(常に走る、合成 120×160・球 R 34 px・接触 a 25 px):
 1. 較正パックの読み込みは fail-closed(綴りを壊した鍵・半径 0・形の不一致・ピッチ 0・無いパス)、中心は (x, y) → (行, 列)
 2. 既知球の法線の閉形式(単位長・傾き = atan2(r, √(R² − r²))・マスク r < min(a, R)・外は (0, 0, 1))
 3. 照明の較正の往復(12 パラメタ・72 パラメタとも 1e-9)、photometric_stereo の逆算 ≤ 1e-3°、1 枚の 72 パラメタは退化で ValueError
 4. 位置で利得が変わる非 Lambertian の合成で、位置つき LUT が位置なしより 2° 以上良い
 5. 不感帯: 位置の項を当てたビンだけで引くと傾き < 15° が寄る、行の少ないビンが近いビンの位置の項を借りると消える
 6. 粗 → 細の逆引きが総当たりと 97 % 以上同じビン、角誤差の中央値の差 ≤ 0.05°
 7. アダプタ: 位置の基底を画素へ閉形式で写した外部書式の表で、同じ逆引きが同じ答え
 8. 角誤差は atan2(1e-7° を 1 % で)、球冠の高さの勾配 = 既知球の法線、位置の掃引の傾きと順位相関
 9. 入力の検査(形・綴り・非有限)
データ門(環境変数 FULLSEYE_TAXIM_DATA があるときだけ): 実機の較正パックで線形 vs 位置つき LUT の順位と hold-out 残差。
"""
from __future__ import annotations

import math
import os

import numpy as np
import pytest

import tacscalib as T

H, W, R, A = 120, 160, 34.0, 25.0
_LD = np.array([[0.0, 1.0, 1.0], [0.87, -0.5, 1.0], [-0.87, -0.5, 1.0]])
_LD /= np.linalg.norm(_LD, axis=1, keepdims=True)
# 中心に副画素のずれ(全部整数だと球ごとの画素の法線が同じになり、どのビンも「球の数 × 同じ行数」になって行の少ないビンが生まれない)
_C = [(26 + 19 * i + 0.37 * ((3 * i + j) % 5), 26 + 17 * j + 0.29 * ((i + 2 * j) % 7)) for i in range(4) for j in range(7)]
TRAIN, TEST = _C[::2], _C[1::4]


def _render(normals, amp):
    yy, xx = np.mgrid[0:H, 0:W]
    Xn, Yn = (xx - W / 2) / W, (yy - H / 2) / H
    return np.stack([np.maximum(normals @ _LD[c], 0.0) ** 1.5 * 60.0 * (1.0 + 2.0 * amp * (Xn * _LD[c, 0] + Yn * _LD[c, 1]))
                     for c in range(3)], axis=-1)


def _raises(fn, exc=ValueError):
    try:
        fn()
    except exc:
        return True
    return False


@pytest.fixture(scope="module")
def scene():
    rgb, nrm, pos = [], [], []
    assert len(TRAIN) >= 8 and len(TEST) >= 3 and set(TRAIN).isdisjoint(TEST)
    for c in TRAIN:
        s = T.sphere_normals_known((H, W), c, A, R)
        rgb.append(_render(s["normals"], 0.4)[s["mask"]])
        nrm.append(s["normals"][s["mask"]])
        pos.append(np.argwhere(s["mask"]))
    rgb, nrm, pos = np.concatenate(rgb), np.concatenate(nrm), np.concatenate(pos)
    pooled = T.gradient_lut_build(rgb, nrm, 125, positions=pos, image_shape=(H, W), min_rows_poly=8)
    nopool = T.gradient_lut_build(rgb, nrm, 125, positions=pos, image_shape=(H, W), min_rows_poly=8, pool=False)
    plain = T.gradient_lut_build(rgb, nrm, 125)
    tests = []
    for c in TEST:
        s = T.sphere_normals_known((H, W), c, A, R)
        tests.append((s, _render(s["normals"], 0.4)))
    return {"pooled": pooled, "nopool": nopool, "plain": plain, "tests": tests, "rows": len(rgb)}


# ── 1〜2 ───────────────────────────────────────────────────────────────────────
def test_calib_pack_load_is_fail_closed(tmp_path):
    z = np.zeros((4, 5, 3), np.uint8)
    np.savez(tmp_path / "bad_key.npz", f0=z, imgs=z[None], touch_centre=np.zeros((1, 2)), touch_radius=np.ones(1))
    np.savez(tmp_path / "zero_r.npz", f0=z, imgs=z[None], touch_center=np.zeros((1, 2)), touch_radius=np.zeros(1))
    np.savez(tmp_path / "bad_n.npz", f0=z, imgs=z[None], touch_center=np.zeros((2, 2)), touch_radius=np.ones(2))
    np.savez(tmp_path / "ok.npz", f0=z, imgs=np.stack([z, z]), touch_center=np.array([[1.0, 2.0], [3.0, 1.5]]), touch_radius=np.array([2.0, 3.0]))
    with pytest.raises(ValueError, match="touch_center"):
        T.calib_pack_load(str(tmp_path / "bad_key.npz"), 0.03, 2.0)
    assert _raises(lambda: T.calib_pack_load(str(tmp_path / "zero_r.npz"), 0.03, 2.0))
    assert _raises(lambda: T.calib_pack_load(str(tmp_path / "bad_n.npz"), 0.03, 2.0))
    assert _raises(lambda: T.calib_pack_load(str(tmp_path / "ok.npz"), 0.0, 2.0))
    assert _raises(lambda: T.calib_pack_load(str(tmp_path / "ok.npz"), 0.03, float("nan")))
    assert _raises(lambda: T.calib_pack_load(123, 0.03, 2.0))
    assert _raises(lambda: T.calib_pack_load(str(tmp_path / "none.npz"), 0.03, 2.0), FileNotFoundError)
    pk = T.calib_pack_load(str(tmp_path / "ok.npz"), 0.03, 2.0)
    assert pk["n"] == 2 and pk["centers"].tolist() == [[2.0, 1.0], [1.5, 3.0]]
    assert abs(pk["R_px"] - 2.0 / 0.03) < 1e-12 and abs(pk["pitch"] - 3e-5) < 1e-18


def test_sphere_normals_closed_form():
    s = T.sphere_normals_known((H, W), (60.3, 80.7), A, R)
    n, m, r = s["normals"], s["mask"], s["r"]
    assert np.abs(np.linalg.norm(n, axis=-1) - 1.0).max() < 1e-12
    assert np.array_equal(m, r < A)
    assert np.all(n[~m] == [0.0, 0.0, 1.0])
    th = np.arcsin(np.clip(r / R, 0, 1))
    assert np.abs(s["theta"][m] - th[m]).max() < 1e-12
    # 中心から列方向(+x)に離れた点の法線は −x を向く(へこみの壁は中心を向く)
    assert n[60, 90, 0] < 0 and abs(n[60, 90, 1] - (-(60 - 60.3) / R)) < 1e-12
    big = T.sphere_normals_known((H, W), (60, 80), 50.0, R)        # a > R はマスクが R で切れる
    assert big["mask"].sum() == (big["r"] < R).sum()
    for bad in (lambda: T.sphere_normals_known((H,), (1, 1), A, R), lambda: T.sphere_normals_known((H, W), (1, float("inf")), A, R),
                lambda: T.sphere_normals_known((H, W), (1, 1), 0.0, R), lambda: T.sphere_normals_known((H, W), (1, 1), A, R, inner=1.5)):
        assert _raises(bad)


# ── 3 ─────────────────────────────────────────────────────────────────────────
def test_lights_fit_round_trip_and_degenerate():
    rng = np.random.default_rng(3)
    L = np.array([[30.0, -41.0, 9.5], [22.0, 44.0, 7.4], [-69.0, 2.0, 21.5]]) + rng.normal(0, 1, (3, 3))
    amb = np.array([-8.5, -11.4, -23.9])
    sc = [T.sphere_normals_known((H, W), c, 30.0, R) for c in ((45, 40), (70, 120), (60, 80))]
    d = [T.membrane_predict_rgb(s["normals"], {"L": L, "ambient": amb}) for s in sc]
    fit = T.lights_fit_from_sphere(d[:2], [s["normals"] for s in sc[:2]], [s["mask"] for s in sc[:2]])
    assert np.abs(fit["L"] - L).max() < 1e-9 * np.abs(L).max() and np.abs(fit["ambient"] - amb).max() < 1e-9 * 30
    assert fit["n_rows"] == int(sc[0]["mask"].sum() + sc[1]["mask"].sum())
    back = T.linear_invert(d[2], fit)
    assert T.normal_error_map(back, sc[2]["normals"])[sc[2]["mask"]].max() < 1e-3      # photometric_stereo は float32
    coef = rng.normal(0, 3, (4, 6, 3))
    f2t = {"order": 2, "coef": coef, "image_shape": (H, W), "L": L, "ambient": amb}
    d2 = [T.membrane_predict_rgb(s["normals"], f2t) for s in sc]
    f2 = T.lights_fit_from_sphere(d2, [s["normals"] for s in sc], [s["mask"] for s in sc], order=2)
    assert np.abs(f2["coef"] - coef).max() < 1e-9 * np.abs(coef).max()
    # 1 枚では球の中の n_x が x の 1 次式 → 位置の項と同じ向きで退化(推測で解かない)
    assert _raises(lambda: T.lights_fit_from_sphere(d2[0], sc[0]["normals"], sc[0]["mask"], order=2))
    assert _raises(lambda: T.lights_fit_from_sphere(d[0], sc[0]["normals"], sc[0]["mask"], order=1))
    assert _raises(lambda: T.lights_fit_from_sphere(d[:2], [sc[0]["normals"]], [sc[0]["mask"]]))
    flat = np.zeros((H, W, 3))
    flat[..., 2] = 1.0
    assert _raises(lambda: T.lights_fit_from_sphere(d[0], flat, np.ones((H, W), bool)))      # 法線が全部同じ = 退化
    assert _raises(lambda: T.membrane_predict_rgb(sc[0]["normals"][:10], f2))                # 位置つきは画像の大きさが固定


# ── 4〜7 ───────────────────────────────────────────────────────────────────────
def test_positional_lut_beats_the_plain_lut(scene):
    e_pos, e_plain = [], []
    for s, img in scene["tests"]:
        m = s["mask"]
        assert int(m.sum()) >= 1000
        e_pos.append(T.normal_error_map(T.gradient_lut_invert(img, scene["pooled"], m), s["normals"])[m])
        e_plain.append(T.normal_error_map(T.gradient_lut_invert(img, scene["plain"], m), s["normals"])[m])
    mp, mn = float(np.median(np.concatenate(e_pos))), float(np.median(np.concatenate(e_plain)))
    assert mp < 1.5 and mn - mp > 2.0, (mp, mn)
    assert scene["rows"] >= 15000 and int((scene["pooled"]["count"] > 0).sum()) >= 2000


def test_borrowed_position_terms_close_the_small_tilt_dead_band(scene):
    band = {"poly_only": [], "pooled": []}
    for s, img in scene["tests"]:
        mb = s["mask"] & (s["theta"] < math.radians(15.0))
        assert int(mb.sum()) >= 200
        for key, tab, mc in (("poly_only", scene["nopool"], 8), ("pooled", scene["pooled"], 1)):
            th = T.normals_to_angles(T.gradient_lut_invert(img, tab, mb, min_count=mc))[0][mb]
            band[key].append(np.degrees(np.abs(th - s["theta"][mb])))
    b = {k: float(np.median(np.concatenate(v))) for k, v in band.items()}
    assert b["pooled"] < 1.5 and b["poly_only"] - b["pooled"] > 5.0, b
    assert scene["pooled"]["pooled_bins"] > 0 and scene["nopool"]["pooled_bins"] == 0


def test_coarse_to_fine_agrees_with_exact(scene):
    same, dmed = [], []
    for s, img in scene["tests"]:
        m = s["mask"]
        ne = T.gradient_lut_invert(img, scene["pooled"], m, method="exact")
        nc = T.gradient_lut_invert(img, scene["pooled"], m)
        same.append(T.normal_error_map(ne, nc)[m] < 1e-9)
        dmed.append(abs(np.median(T.normal_error_map(nc, s["normals"])[m]) - np.median(T.normal_error_map(ne, s["normals"])[m])))
    fs_ = float(np.mean(np.concatenate(same)))
    assert fs_ >= 0.97 and max(dmed) <= 0.05, (fs_, dmed)
    s, img = scene["tests"][0]
    plain_e = T.gradient_lut_invert(img, scene["plain"], s["mask"], method="exact")
    plain_c = T.gradient_lut_invert(img, scene["plain"], s["mask"])
    # 位置なしの表は色の近いビンが多く(多峰)、同じビンは 8 割台 —— それでも角誤差の中央値はほとんど変わらない
    m = s["mask"]
    same_p = float(np.mean(T.normal_error_map(plain_e, plain_c)[m] < 1e-9))
    dm_p = abs(np.median(T.normal_error_map(plain_c, s["normals"])[m]) - np.median(T.normal_error_map(plain_e, s["normals"])[m]))
    assert same_p >= 0.8 and dm_p <= 0.2, (same_p, dm_p)


def _unit_to_pixel(coef):
    ax, bx, ay, by = 2.0 / (W - 1.0), -1.0, 2.0 / (H - 1.0), -1.0
    c0, c1, c2, c3, c4, c5 = (coef[..., k, :] for k in range(6))
    return np.stack([c0 * ax * ax, c1 * ay * ay, c2 * ax * ay, 2 * c0 * ax * bx + c2 * ax * by + c3 * ax,
                     2 * c1 * ay * by + c2 * bx * ay + c4 * ay, c0 * bx * bx + c1 * by * by + c2 * bx * by + c3 * bx + c4 * by + c5], axis=-2)


def test_external_format_adapter_after_a_closed_form_basis_change(scene):
    P = _unit_to_pixel(scene["pooled"]["coef"])
    poly = {"bins": np.array(125), "grad_r": P[..., 0], "grad_g": P[..., 1], "grad_b": P[..., 2]}
    s, img = scene["tests"][1]
    m = s["mask"]
    na = T.gradient_lut_invert(img, dict(scene["pooled"], count=np.ones((125, 125))), m, method="exact")
    nb = T.poly_lut_invert(img, poly, m, method="exact")
    assert float(np.mean(T.normal_error_map(na, nb)[m] < 1e-9)) >= 0.999
    assert _raises(lambda: T.poly_lut_invert(img, {"bins": np.array(125), "grad_r": P[..., 0]}, m))
    assert _raises(lambda: T.poly_lut_invert(img, dict(poly, grad_g=P[..., 1][:, :, :4]), m))
    assert _raises(lambda: T.poly_lut_invert(img, dict(poly, grad_b=np.full_like(P[..., 2], np.nan)), m))


# ── 8 ─────────────────────────────────────────────────────────────────────────
def test_angles_heights_and_the_position_sweep():
    for ang in (1e-7, 1e-3, 30.0, 179.0):
        n1 = np.array([0.0, 0.0, 1.0])
        n2 = np.array([math.sin(math.radians(ang)), 0.0, math.cos(math.radians(ang))]) * 3.0      # 長さは atan2 の比で消える
        assert abs(float(T.normal_error_map(n1, n2)) - ang) <= 0.01 * ang
    pitch = 3e-5
    cap = T.sphere_cap_height((H, W), (60.3, 80.7), A, R, pitch)
    s = T.sphere_normals_known((H, W), (60.3, 80.7), A, R)
    gy, gx = np.gradient(cap["h"] / pitch)
    inner = s["mask"] & (s["r"] < A - 2.0)
    assert np.abs(gx + s["normals"][..., 0] / s["normals"][..., 2])[inner].max() < 0.02
    assert np.abs(gy + s["normals"][..., 1] / s["normals"][..., 2])[inner].max() < 0.02
    assert abs(cap["delta"] - (R - math.sqrt(R * R - A * A)) * pitch) < 1e-15
    assert np.nanmax(cap["shape_rel"]) <= cap["delta"] + 1e-15 and np.all(cap["h"][~s["mask"]] == 0.0)
    cen = np.array([[59.5 + 10 * k, 79.5] for k in range(5)])
    sw = T.field_position_sweep(cen, 1.0 + 0.3 * np.arange(5), (H, W))
    assert abs(sw["slope_per_100px"] - 3.0) < 1e-9 and abs(sw["spearman"] - 1.0) < 1e-12 and sw["n"] == 5
    from scipy.stats import spearmanr                                                          # 同順位の扱いを第 2 実装と
    e_t = np.array([2.0, 2.0, 2.0, 1.0, 0.0])
    assert abs(T.field_position_sweep(cen, e_t, (H, W))["spearman"] - spearmanr(np.arange(5.0), e_t)[0]) < 1e-12
    assert _raises(lambda: T.field_position_sweep(cen[:2], np.ones(2), (H, W)))
    assert _raises(lambda: T.field_position_sweep(cen, np.array([1, 2, np.nan, 4, 5.0]), (H, W)))


# ── 9 ─────────────────────────────────────────────────────────────────────────
def test_inputs_are_checked(scene):
    s, img = scene["tests"][0]
    tab = scene["pooled"]
    assert _raises(lambda: T.gradient_lut_invert(img, tab, s["mask"], method="exactly"))
    assert _raises(lambda: T.gradient_lut_invert(img[..., :2], tab, s["mask"]))
    assert _raises(lambda: T.gradient_lut_invert(img, tab, s["mask"][:10]))
    assert _raises(lambda: T.gradient_lut_invert(img[:60], tab, s["mask"][:60]))                 # 位置つきは画像の大きさが固定
    assert _raises(lambda: T.gradient_lut_invert(img, tab, s["mask"], min_count=10 ** 9))       # 使えるビンが 0
    assert _raises(lambda: T.gradient_lut_invert(img, {"bins": 125}, s["mask"]))
    rows = np.ones((5, 3))
    assert _raises(lambda: T.gradient_lut_build(rows, rows[:4]))
    assert _raises(lambda: T.gradient_lut_build(rows, rows, bins=3))
    assert _raises(lambda: T.gradient_lut_build(rows, rows, positions=np.zeros((5, 2))))         # image_shape が無い
    assert _raises(lambda: T.gradient_lut_build(np.full((5, 3), np.nan), rows))
    assert _raises(lambda: T.gradient_lut_build(rows, rows, positions=np.zeros((5, 2)), image_shape=(H, W), flat_rgb=rows))
    assert _raises(lambda: T.gradient_lut_build(rows, rows, min_rows_poly=5))
    assert _raises(lambda: T.gradient_lut_build(rows, rows, flat_rgb=rows, flat_positions=np.zeros((5, 2))))
    assert _raises(lambda: T.gradient_lut_invert(img, tab, s["mask"], topk=0))
    assert _raises(lambda: T.normal_error_map(np.ones((3, 3)), np.ones((3, 2))))
    assert _raises(lambda: T.sphere_cap_height((H, W), (1, 1), A, R, 0.0))
    out = T.gradient_lut_invert(img, tab, np.zeros((H, W), bool))                                 # 空のマスクは全部 (0, 0, 1)
    assert np.all(out[..., 2] == 1.0)


# ── データ門 ───────────────────────────────────────────────────────────────────
_DATA = os.environ.get("FULLSEYE_TAXIM_DATA", "").strip()


@pytest.mark.skipif(not (_DATA and os.path.isfile(os.path.join(_DATA, "calibs", "dataPack.npz"))),
                    reason="FULLSEYE_TAXIM_DATA が無い(実機の較正パック)")
def test_real_pack_linear_vs_positional_lut():
    pk = T.calib_pack_load(os.path.join(_DATA, "calibs", "dataPack.npz"), 0.0295, 2.0)
    f0 = pk["f0"].astype(np.float64)
    Hh, Ww = f0.shape[:2]
    train, test = list(range(0, pk["n"], 4))[:8], list(range(1, pk["n"], 8))[:3]
    assert len(train) >= 8 and len(test) >= 3 and set(train).isdisjoint(test)

    def item(i):
        return pk["imgs"][i].astype(np.float64) - f0, T.sphere_normals_known((Hh, Ww), pk["centers"][i], pk["radii"][i], pk["R_px"])

    items = [item(i) for i in train]
    fit = T.lights_fit_from_sphere([d for d, _ in items], [s["normals"] for _, s in items], [s["mask"] for _, s in items])
    lut = T.gradient_lut_build(np.concatenate([d[s["mask"]] for d, s in items]), np.concatenate([s["normals"][s["mask"]] for _, s in items]),
                               125, positions=np.concatenate([np.argwhere(s["mask"]) for _, s in items]), image_shape=(Hh, Ww), min_rows_poly=10)
    e_lin, e_pos, res = [], [], []
    for i in test:
        d, s = item(i)
        m = s["mask"].copy()
        m[1::3, :] = False
        m[2::3, :] = False
        m[:, 1::3] = False
        m[:, 2::3] = False
        e_lin.append(np.median(T.normal_error_map(T.linear_invert(d, fit), s["normals"])[m]))
        e_pos.append(np.median(T.normal_error_map(T.gradient_lut_invert(d, lut, m, min_count=3), s["normals"])[m]))
        res.append(np.mean((T.membrane_predict_rgb(s["normals"], fit) - d)[s["mask"]] ** 2))
    assert float(np.sqrt(np.mean(res))) < 9.5
    assert float(np.median(e_lin)) - float(np.median(e_pos)) > 4.0, (e_lin, e_pos)
