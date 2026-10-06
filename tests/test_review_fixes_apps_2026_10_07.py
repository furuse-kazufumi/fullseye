# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""2026-10-07 レビューで再現したアプリ系 op の欠陥の回帰テスト(tacsim / segcompare / printpath / driveworld /
roverslip / pxrd / vxcore)。

真値は op と別の経路から取る: 窓ごと平行移動しても値が変わらないこと(並進不変)、正しい a0 で当てた値、
整数の添字 i そのもの、手で数えた線分、総当たりの非極大抑制、Poisson 標本の経験的な標準偏差。
"""
from __future__ import annotations

import numpy as np
import pytest

import driveworld as D
import printpath as P
import pxrd
import roverslip as RS
import segcompare as SC
import tacsim as TS
import vxcore as VX


# --------------------------------------------------------------------------- tacsim
@pytest.fixture(scope="module")
def membrane():
    hz = TS.hertz_sphere(4.0, 3e-3, TS.combined_modulus(0.3e6, 0.49))
    m = TS.membrane_indent_sphere(hz, n=256, fov=16e-3)
    return hz, m


@pytest.mark.parametrize("shift", [(8e-3, 8e-3), (-5e-3, 3e-3)])
def test_tacsim_delta_is_translation_invariant(membrane, shift):
    """X・Y・中心を同じだけずらしても δ と a は変わらない(旧: +8 mm で Boussinesq の δ が 11 % 縮んだ)。"""
    hz, m = membrane
    sx, sy = shift
    for tail in ("boussinesq", "none"):
        d0 = TS.membrane_delta_from_normals(m["normals"], m["X"], m["Y"], m["pitch"], tail=tail, centre_xy=(0.0, 0.0))
        d1 = TS.membrane_delta_from_normals(m["normals"], m["X"] + sx, m["Y"] + sy, m["pitch"], tail=tail,
                                            centre_xy=(sx, sy))
        assert abs(d1 - d0) <= 1e-9 * abs(d0)
    a0 = TS.contact_radius_fit(m["normals"], m["X"], m["Y"], hz["R"], m["pitch"], centre_xy=(0.0, 0.0))["a"]
    a1 = TS.contact_radius_fit(m["normals"], m["X"] + sx, m["Y"] + sy, hz["R"], m["pitch"], centre_xy=(sx, sy))["a"]
    assert abs(a1 - a0) <= 1e-9 * a0
    # 中心が窓の外 → 黙って縮んだ窓で積分せず拒否
    with pytest.raises(ValueError, match="outside the window"):
        TS.membrane_delta_from_normals(m["normals"], m["X"], m["Y"], m["pitch"], centre_xy=(1.0, 0.0))


@pytest.mark.parametrize("fac", [1.5, 0.6, 2.0])
def test_tacsim_pixelwise_fit_leaves_the_bracket_edge(membrane, fac):
    """a0 が 20 % 超ずれても区間の端(0.8·a0 / 1.2·a0)を返さず、正しい a0 で当てた値に戻る。"""
    hz, m = membrane
    ref = TS.contact_radius_fit_pixelwise(m["normals"], m["X"], m["Y"], hz["R"], a0=hz["a"])["a"]
    got = TS.contact_radius_fit_pixelwise(m["normals"], m["X"], m["Y"], hz["R"], a0=hz["a"] / fac)
    assert abs(ref / hz["a"] - 1.0) < 1e-3
    assert abs(got["a"] - ref) <= 1e-6 * ref
    assert got["rms"] < 1e-3


def test_tacsim_pixelwise_fit_refuses_when_no_contact(membrane):
    """接触の無い(平らな)法線場: 端に張り付き続けるので ValueError(旧: 0.8·a0 を黙って返した)。"""
    hz, m = membrane
    flat = np.zeros_like(m["normals"])
    flat[..., 2] = 1.0
    with pytest.raises(ValueError, match="contact_radius_fit_pixelwise"):
        TS.contact_radius_fit_pixelwise(flat, m["X"], m["Y"], hz["R"], a0=hz["a"])


# --------------------------------------------------------------------------- segcompare
@pytest.mark.parametrize("spacing", [0.1, 0.3, 0.7, 1.1])
def test_segcompare_lookup_lands_on_the_integer_voxel(spacing):
    """座標 = i·spacing の点は voxel i に入る(旧: 43*0.1/0.1 = 42.999… を floor して 1 個手前、0.1 で 47/1000 個)。"""
    n = 1000
    lab = (np.arange(n, dtype=np.int64) + 1)[None, :]
    i = np.arange(n)
    pre = np.column_stack([np.zeros(n), i * spacing])
    post = np.column_stack([np.zeros(n), np.minimum(i + 1, n - 1) * spacing])
    r = SC.seg_synapse_partners(lab, {"pre": pre, "post": post}, spacing=(spacing, spacing))
    pre_ids = np.asarray(r["pre_ids"])
    assert pre_ids.shape == (n,)
    np.testing.assert_array_equal(pre_ids, i + 1)
    assert r["n_background"] == 0
    # 半端な座標は従来どおり floor(i + 0.5 → i)
    r2 = SC.seg_synapse_partners(lab, {"pre": pre + [0.0, 0.5 * spacing], "post": post}, spacing=(spacing, spacing))
    np.testing.assert_array_equal(np.asarray(r2["pre_ids"]), i + 1)


# --------------------------------------------------------------------------- printpath
def test_gcode_read_strips_line_numbers_and_checksums(tmp_path):
    """Marlin の N123 … *71 の行を落とさない(旧: 4 行中 2 行が黙って消え、線分 1・E 1)。"""
    p = tmp_path / "n.gcode"
    p.write_text("G1 X0 Y0 Z0.2 F1200\nG1 X10 Y0 E1\nN12 G1 X10 Y10 E2*56\nN13 G1 X0 Y10 E3 *57\nN14\n",
                 encoding="utf-8")
    t = P.gcode_read(str(p))
    assert len(t["e"]) == 3
    assert abs(t["e"].sum() - 3.0) < 1e-12
    assert t["x1"].tolist() == [10.0, 10.0, 0.0] and t["y1"].tolist() == [0.0, 10.0, 10.0]


def test_gcode_read_refuses_unknown_leading_words_but_keeps_comments_and_macros(tmp_path):
    ok = tmp_path / "ok.gcode"
    ok.write_text("; comment\n\nM117 Printing part 1\nSET_VELOCITY_LIMIT ACCEL=500\nT0\n"
                  "G1 X0 Y0 Z0.2 F1200\nG1 X10 E1\n", encoding="utf-8")
    t = P.gcode_read(str(ok))
    assert len(t["e"]) == 1 and t["x1"][0] == 10.0
    modal = tmp_path / "modal.gcode"
    modal.write_text("G1 X0 Y0 Z0.2 F1200\nG1 X10 E1\nX20 E2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="line 3: unsupported leading word"):
        P.gcode_read(str(modal))
    junk = tmp_path / "junk.gcode"
    junk.write_text("G1 X0 Y0 Z0.2 F1200\n#!? 12\n", encoding="utf-8")
    with pytest.raises(ValueError, match="line 2: cannot parse"):
        P.gcode_read(str(junk))


def _old_stroke_gauss(a, sigma):
    """修正前の実装(r < 辺の長さでは正しい)—— 値が変わっていないことの照合用。"""
    r = int(np.ceil(3.0 * sigma))
    x = np.arange(-r, r + 1, dtype=np.float64)
    k = np.exp(-0.5 * (x / sigma) ** 2)
    k /= k.sum()
    pad = lambda v: np.concatenate([v[r:0:-1], v, v[-2:-r - 2:-1]])  # noqa: E731
    out = np.apply_along_axis(lambda v: np.convolve(pad(v), k, mode="valid"), 0, a)
    return np.apply_along_axis(lambda v: np.convolve(pad(v), k, mode="valid"), 1, out)


@pytest.mark.parametrize("shape,sigma", [((8, 12), 3.0), ((1, 5), 2.0), ((3, 3), 4.0), ((2, 40), 1.0)])
def test_stroke_gauss_keeps_the_shape_on_small_images(shape, sigma):
    """r = ⌈3σ⌉ ≥ 辺でも形が保たれ、定数は定数のまま(旧: (8, 12), σ=3 → (4, 12))。"""
    rng = np.random.default_rng(0)
    a = rng.random(shape)
    out = P._stroke_gauss(a, sigma)
    assert out.shape == a.shape
    c = P._stroke_gauss(np.full(shape, 0.7), sigma)
    np.testing.assert_allclose(c, 0.7, atol=1e-12)
    assert a.min() - 1e-12 <= out.min() and out.max() <= a.max() + 1e-12


def test_stroke_gauss_unchanged_when_the_image_is_large_enough():
    rng = np.random.default_rng(1)
    a = rng.random((30, 41))
    np.testing.assert_allclose(P._stroke_gauss(a, 3.0), _old_stroke_gauss(a, 3.0), rtol=0, atol=1e-13)
    img = rng.random((8, 12))
    pts = np.array([[1.0, 1.0], [1.0, 10.0], [6.0, 10.0], [6.0, 1.0]])
    r = P.stroke_tone_error(img, pts, blur_sigma=3.0)
    assert np.isfinite(r["rms"])


# --------------------------------------------------------------------------- driveworld
def test_world_move_is_absolute_in_z():
    """add_asset(z=2) の後の world_move は z を絶対値で置く(旧: 元の z を外さず、z=2 → z=2 で底が 4)。"""
    w0 = D._empty_world()
    k = D.add_asset(w0, "cone", 0.0, 0.0, 0.0)
    base = float(w0["V"][slice(*w0["objects"][k]["verts"]), 2].min())
    for z_add, z_move in [(2.0, 0.0), (2.0, 2.0), (2.0, 5.0), (0.0, 1.5)]:
        w = D._empty_world()
        i = D.add_asset(w, "cone", 0.0, 0.0, 0.0, z=z_add)
        sl = slice(*w["objects"][i]["verts"])
        assert abs(float(w["V"][sl, 2].min()) - (base + z_add)) < 1e-12
        D.world_move(w, i, 1.0, 2.0, 0.3, z=z_move)
        assert abs(float(w["V"][sl, 2].min()) - (base + z_move)) < 1e-12
        D.world_move(w, i, 1.0, 2.0, 0.3, z=z_move)                     # 同じ姿勢へ 2 度目: 動かない
        assert abs(float(w["V"][sl, 2].min()) - (base + z_move)) < 1e-12


# --------------------------------------------------------------------------- roverslip
def test_risk_aware_path_does_not_wrap_around_the_map():
    """負の添字で反対側へ回り込まない(旧: 全部 1 の地図で (0,0)→(9,9) が 1 手・cost 1)。"""
    path = RS.risk_aware_path({"cost": np.ones((8, 10, 10))}, (0, 0), (9, 9))
    P_ = np.asarray(path["path"])
    assert path["reached"] and P_.shape == (10, 2)
    assert P_[0].tolist() == [0, 0] and P_[-1].tolist() == [9, 9]
    assert np.all(np.abs(np.diff(P_, axis=0)).max(axis=1) == 1)
    assert path["cost"] == 9.0
    cost = np.full((8, 5, 5), np.inf)                                    # 動けない地図: 回り込みでも届かない
    r = RS.risk_aware_path({"cost": cost}, (0, 0), (4, 4))
    assert not r["reached"] and r["cost"] == np.inf


# --------------------------------------------------------------------------- pxrd
def test_azimuthal_sigma_carries_the_solid_angle_correction():
    """立体角で割った強度の σ は補正を通す: Poisson 標本の経験的な標準偏差 / 報告した σ ≈ 1 が全ビンで
    (旧: 2θ = 55° で 2.31、理論 2.29)。"""
    g = {"cx": 31.5, "cy": 31.5, "distance": 30.0, "pixel": 1.0, "wavelength": 1.0}
    om = pxrd.detector_two_theta((64, 64), g)["solid_angle"]
    rng = np.random.default_rng(0)
    lam = 1000.0 * om
    outs = [pxrd.azimuthal_integrate(rng.poisson(lam).astype(float), g, n_bins=20, supersample=1) for _ in range(200)]
    I = np.array([o["intensity"] for o in outs])
    S = np.array([o["sigma"] for o in outs])
    ratio = np.std(I, axis=0) / np.mean(S, axis=0)
    assert ratio.shape == (20,) and np.all(np.isfinite(ratio))
    assert np.all((ratio > 0.8) & (ratio < 1.2)), np.round(ratio, 2)
    # 補正なしでは従来どおり: σ = √(Σ 値) / 画素数 = √(平均 / 画素数)
    im = rng.poisson(50.0, (64, 64)).astype(float)
    r = pxrd.azimuthal_integrate(im, g, n_bins=20, supersample=1, solid_angle=False)
    has = r["count"] > 0
    assert int(has.sum()) == 20
    np.testing.assert_allclose(r["sigma"][has], np.sqrt(r["intensity"][has] / r["count"][has]), rtol=1e-12)


# --------------------------------------------------------------------------- vxcore
def _nonmax_brute(img, w):
    h, wd = img.shape
    r = w // 2
    v = img.astype(np.int64)
    out = img.copy()
    for y in range(h):
        for x in range(wd):
            keep = True
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    yy, xx = y + dy, x + dx
                    if (dy == 0 and dx == 0) or not (0 <= yy < h and 0 <= xx < wd):
                        continue
                    before = dy < 0 or (dy == 0 and dx < 0)
                    if not (v[y, x] >= v[yy, xx] if before else v[y, x] > v[yy, xx]):
                        keep = False
            if not keep:
                out[y, x] = 0
    return out


@pytest.mark.parametrize("shape,win", [((2, 2), 7), ((3, 3), 9), ((1, 6), 5), ((2, 5), 7), ((4, 3), 11), ((5, 6), 3)])
def test_nonmax_window_larger_than_image_matches_brute_force(shape, win):
    """窓 > 画像でも、画像の外の隣を比べないだけ(docstring)。旧: (2, 2) / 窓 7 で numpy の broadcast エラー。"""
    rng = np.random.default_rng(shape[0] * 100 + shape[1] * 10 + win)
    for _ in range(5):
        img = rng.integers(0, 4, shape).astype(np.uint8)                 # 同点を多く含める
        got = VX.vx_nonmax_suppression(img, window=win)
        assert got.shape == img.shape
        np.testing.assert_array_equal(got, _nonmax_brute(img, win))
