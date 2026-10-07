# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""物理計測まわりのレビュー指摘(2026-10-07)の回帰テスト。

各指摘につき「反例がいまは正しい」と「直していない側の振る舞いは変わらない」を
1 本ずつ。どれも小さな合成データで決定的に走る(乱数は seed 固定)。
"""
from __future__ import annotations

import base64
import json
import struct

import numpy as np
import pytest


# --------------------------------------------------------------------------- #
# 1. lensimage._integrate_pixels —— 偶数倍のピッチで PSF が 1/4 画素ずれた        #
# --------------------------------------------------------------------------- #
def _centred_gauss(m=256, s=6.0):
    x = np.arange(m) - m // 2
    g = np.exp(-(x[:, None] ** 2 + x[None, :] ** 2) / (2 * s * s))
    return g / g.sum()


@pytest.mark.parametrize("mult", [1.0, 2.0, 4.0, 2.5])
def test_lensimage_binning_is_centred_for_any_pitch(mult):
    import lensimage as LI
    psf = _centred_gauss()
    out = LI._integrate_pixels(psf, 1.0, mult)
    K = out.shape[0]
    c = K // 2
    y, x = np.mgrid[:K, :K]
    assert abs(out.sum() - 1.0) < 1e-12
    assert abs((out * x).sum() - c) < 1e-9          # 以前は mult=2 で +0.249 px
    assert abs((out * y).sum() - c) < 1e-9
    assert np.abs(out - out[::-1, ::-1]).max() <= 1e-12 * out.max()


def test_lensimage_binning_unnormalised_keeps_energy():
    import lensimage as LI
    psf = 3.0 * _centred_gauss()
    out = LI._integrate_pixels(psf, 1.0, 2.0, normalise=False)
    assert abs(out.sum() - 3.0) < 1e-9
    with pytest.raises(ValueError):
        LI._integrate_pixels(np.zeros((8, 8)), 1.0, 2.0)
    with pytest.raises(ValueError):
        LI._integrate_pixels(psf, 3.0, 2.0)          # 標本間隔 > ピッチ は従来どおり拒否


def test_optics_bin_to_pixels_identity_at_unit_ratio():
    import optics
    psf = _centred_gauss(64, 3.0)
    out = optics._bin_to_pixels(psf, 1.0, 1.0)
    # ピッチ = 標本間隔なら素通し(丸めで隣へ漏れていた)
    m = psf.shape[0]
    core = out[out.shape[0] // 2 - m // 2: out.shape[0] // 2 - m // 2 + m,
               out.shape[1] // 2 - m // 2: out.shape[1] // 2 - m // 2 + m]
    assert np.allclose(core, psf / psf.sum(), atol=1e-15)


# --------------------------------------------------------------------------- #
# 2. pivops._regrid —— 最近傍でなく「右隣」を取っていた                          #
# --------------------------------------------------------------------------- #
def test_piv_regrid_takes_the_nearest_coarse_vector():
    import pivops as P
    shape = (256, 256)
    info = {"rows": np.array([31.5, 95.5, 159.5, 223.5]),
            "cols": np.array([31.5, 95.5, 159.5, 223.5])}
    R, C = np.meshgrid(info["rows"], info["cols"], indexing="ij")
    out = P._regrid(np.stack([R, C]), info, 16, 0.5, shape)
    fine = np.arange(0, 256 - 16 + 1, 8) + 7.5
    nearest = info["rows"][np.abs(info["rows"][None, :] - fine[:, None]).argmin(1)]
    assert fine.size
    assert np.array_equal(out[0][:, 0], nearest)
    assert np.array_equal(out[1][0, :], nearest)


def test_piv_regrid_same_grid_is_identity():
    import pivops as P
    shape = (256, 256)
    rows = np.arange(0, 256 - 64 + 1, 32) + 31.5
    info = {"rows": rows, "cols": rows}
    flow = np.random.default_rng(0).normal(size=(2, rows.size, rows.size))
    out = P._regrid(flow, info, 64, 0.5, shape)
    assert np.array_equal(out, flow)


# --------------------------------------------------------------------------- #
# 3/4. astrostack —— MAD = 0 の画素                                            #
# --------------------------------------------------------------------------- #
def _int_frames_with_cr():
    rng = np.random.default_rng(1)
    frames = [np.round(100 + 0.4 * rng.standard_normal((32, 32))) for _ in range(9)]
    frames[3][10, 10] += 5000.0
    return frames


def test_sigma_clip_stack_rejects_cr_where_mad_is_zero():
    import astrostack as A
    st, acc = A.sigma_clip_stack(_int_frames_with_cr(), mode="sigma_clip", kappa=3.0)
    assert not acc[3, 10, 10]                       # 以前は全 9 枚を採用
    assert abs(st[10, 10] - 100.0) < 0.5            # 以前は 655.7
    # 1 DN の読み出し揺らぎ(真の 2.5σ)は落とさない
    assert acc.mean() > 0.99


def test_sigma_clip_stack_float_path_does_not_use_the_floor(monkeypatch):
    import astrostack as A
    rng = np.random.default_rng(2)
    frames = [100 + 2.0 * rng.standard_normal((16, 16)) for _ in range(8)]

    def boom(_):
        raise AssertionError("pooled floor used on data with MAD > 0")
    monkeypatch.setattr(A, "_pooled_residual_sigma", boom)
    st, acc = A.sigma_clip_stack(frames, mode="sigma_clip", kappa=3.0)
    assert st.shape == (16, 16) and np.isfinite(st).all()


def test_cosmic_ray_reject_stack_zero_mad_uses_pooled_sigma():
    import astrostack as A
    frames = _int_frames_with_cr()
    _, m = A.cosmic_ray_reject_stack(frames, kappa=5.0)
    assert int(m.sum()) == 1 and m[3, 10, 10]       # 以前は 871 画素


def test_cosmic_ray_reject_stack_refuses_without_any_noise_scale():
    import astrostack as A
    frames = [np.full((8, 8), 100.0) for _ in range(5)]
    frames[2][3, 3] = 900.0
    with pytest.raises(ValueError):
        A.cosmic_ray_reject_stack(frames)
    _, m = A.cosmic_ray_reject_stack(frames, read_sigma=1.0)   # 床を渡せば動く
    assert m[2, 3, 3] and int(m.sum()) == 1


def test_cosmic_ray_reject_stack_float_path_unchanged(monkeypatch):
    import astrostack as A
    rng = np.random.default_rng(3)
    frames = [100 + 2.0 * rng.standard_normal((16, 16)) for _ in range(8)]

    def boom(_):
        raise AssertionError("pooled floor used on data with MAD > 0")
    monkeypatch.setattr(A, "_pooled_residual_sigma", boom)
    cl, m = A.cosmic_ray_reject_stack(frames)
    assert len(cl) == 8


# --------------------------------------------------------------------------- #
# 5. backends_tomo —— 非正方の像が radon(circle=True) で欠けた                  #
# --------------------------------------------------------------------------- #
def test_radon_forward_keeps_off_centre_content_of_non_square_slice():
    import backends_tomo as B
    a = np.zeros((48, 96))
    a[20:28, 4:12] = 1.0                            # 左端の物体(中央の円の外)
    s = B.tm_radon_forward(a, 1.0, 0.5)
    assert s.shape == (48, 96)
    assert s.max() > 0.5                            # 以前は全部 0


def test_radon_forward_square_input_not_padded():
    import backends_tomo as B
    x = np.random.default_rng(0).random((32, 32))
    assert B._pad_to_diagonal_square(x) is x
    y = np.ones((10, 30))
    p = B._pad_to_diagonal_square(y)
    assert p.shape[0] == p.shape[1] == int(np.ceil(np.hypot(10, 30)))
    assert p.sum() == y.sum()


# --------------------------------------------------------------------------- #
# 6. optscene.diffraction_blur —— σ = 0.42·λN(1.22 を掛けていた)              #
# --------------------------------------------------------------------------- #
def test_diffraction_blur_sigma_is_042_lambda_n(monkeypatch):
    import optscene
    cam = optscene.optical_camera(pixel_um=1.0)
    seen = []
    real = optscene._gauss_blur

    def spy(img, sigma):
        seen.append(float(sigma))
        return real(img, sigma)
    monkeypatch.setattr(optscene, "_gauss_blur", spy)
    optscene.diffraction_blur(np.zeros((16, 16)), cam, f_number=8.0, wavelength_nm=550.0)
    assert seen
    assert abs(seen[0] - 0.42 * 0.55 * 8.0 / 1.0) < 1e-12
    # 画素より十分小さい σ は従来どおり何もしない
    out = optscene.diffraction_blur(np.eye(4), optscene.optical_camera(pixel_um=50.0), f_number=1.0)
    assert np.array_equal(out, np.eye(4))


# --------------------------------------------------------------------------- #
# 7. glassmirror —— 偏光ごとの多重反射 / プリズムの n < 1                       #
# --------------------------------------------------------------------------- #
def test_slab_transmittance_sums_per_polarisation():
    import glassmirror as g
    for deg in (30.0, 60.0, 80.0):
        ci = np.cos(np.radians(deg))
        rs = g.fresnel_dielectric(ci, 1.0, 1.5, "s")
        rp = g.fresnel_dielectric(ci, 1.0, 1.5, "p")
        want = 0.5 * ((1 - rs) / (1 + rs) + (1 - rp) / (1 + rp))
        assert abs(float(g.slab_transmittance(ci, 1.0, 1.5, 3.0, 0.0)) - want) < 1e-12
    # 垂直入射は従来値 2n/(n²+1)
    assert abs(float(g.slab_transmittance(1.0, 1.0, 1.5, 3.0, 0.0)) - 3.0 / 3.25) < 1e-12


def test_prism_refuses_index_below_one():
    import glassmirror as g
    with pytest.raises(ValueError):
        g.prism_min_deviation_deg(550.0, 60.0, 0.5)
    d = float(g.prism_min_deviation_deg(587.56, 60.0, "N-BK7"))
    assert abs(d - 38.65) < 0.02                    # docstring も 38.6° に


# --------------------------------------------------------------------------- #
# 8. spc MT 法 —— ばらつき 0 の特徴量が生の単位で距離に入った                    #
# --------------------------------------------------------------------------- #
def test_mt_flat_feature_contributes_nothing_in_any_unit():
    import spc
    rng = np.random.default_rng(0)
    X = np.column_stack([rng.normal(0, 1, (200, 2)), np.full(200, 4.2)])
    new = np.array([[0.0, 0.0, 4.2], [0.0, 0.0, 7.2]])
    mds = []
    for scale in (1.0, 1000.0):
        Xs, ns = X.copy(), new.copy()
        Xs[:, 2] *= scale
        ns[:, 2] *= scale
        u = spc.spc_mt_unit_space(Xs)
        assert u["flat_features"] == 1
        mds.append(spc.spc_mt_distance(ns, u["mean"], u["std"], u["inv_corr"])["md"])
    assert np.allclose(mds[0], mds[1])
    assert abs(mds[0][0] - mds[0][1]) < 1e-12       # 以前は 1.73 / 1732


def test_mt_without_flat_features_unchanged():
    import spc
    X = np.random.default_rng(1).normal(size=(50, 3))
    u = spc.spc_mt_unit_space(X)
    assert u["flat_features"] == 0
    assert np.allclose(u["inv_corr"], np.linalg.inv(u["corr"]))
    assert abs(u["md_sq_mean"] - u["md_sq_mean_exact"]) < 1e-9


# --------------------------------------------------------------------------- #
# 9. imgio / raster —— 符号付き整数を iinfo.max で割っていた                     #
# --------------------------------------------------------------------------- #
def test_signed_int_normalisation_matches_to_float01():
    import imgio
    import raster
    a = np.array([[-32768, -1000, 0, 32767]], np.int16)
    want = imgio.to_float01(a)
    for got in (imgio._to01_by_depth(a), raster.to01(a)):
        assert got.min() >= 0.0 and got.max() <= 1.0
        assert np.array_equal(got, want)
    u = np.array([[0, 1000, 65535]], np.uint16)
    assert np.array_equal(raster.to01(u), u / 65535.0)
    assert np.array_equal(imgio._to01_by_depth(u), u / 65535.0)
    f = np.array([[-0.5, 0.25, 1.5]])
    assert np.array_equal(raster.to01(f), np.clip(f, 0, 1))


# --------------------------------------------------------------------------- #
# 10. motionio._guess_columns —— 掃く縁の x を時刻と読んだ                      #
# --------------------------------------------------------------------------- #
def test_read_events_does_not_take_a_sweeping_x_for_time(tmp_path):
    import motionio
    n = 200
    t = np.linspace(0.0, 0.1, n)
    x = np.floor(np.linspace(0, 239, n))
    y = (np.arange(n) * 37) % 180
    p = np.arange(n) % 2
    f = tmp_path / "sweep.txt"
    np.savetxt(f, np.column_stack([t, x, y, p]), fmt="%.9f %d %d %d")
    ev = motionio.read_events(f)
    assert ev["columns"] == {"x": 1, "y": 2, "t": 0, "p": 3}
    assert ev["shape"] == (180, 240)


def test_read_events_integer_time_and_ambiguity(tmp_path):
    import motionio
    rng = np.random.default_rng(0)
    n = 100
    x = rng.integers(0, 64, n)
    y = rng.integers(0, 48, n)
    t = np.cumsum(rng.integers(1, 50, n))           # µs の整数時刻(従来の典型)
    p = rng.integers(0, 2, n)
    f = tmp_path / "us.txt"
    np.savetxt(f, np.column_stack([x, y, t, p]), fmt="%d")
    ev = motionio.read_events(f)
    assert ev["columns"]["t"] == 2
    # 整数の単調列が 2 本(掃く x と µs 時刻)では決められない → 拒否
    g = tmp_path / "amb.txt"
    np.savetxt(g, np.column_stack([np.sort(x), y, t, p]), fmt="%d")
    with pytest.raises(ValueError):
        motionio.read_events(g)


# --------------------------------------------------------------------------- #
# 11. meshio_opt._scale_rgb —— チャネルごとに 8/16 bit を決めていた             #
# --------------------------------------------------------------------------- #
def test_las_rgb_bit_depth_decided_once():
    import meshio_opt
    r = np.array([65535, 60000])
    g = np.array([32768, 30000])
    b = np.array([200, 100])
    C = meshio_opt._scale_rgb([r, g, b], "x")
    assert np.allclose(C, np.column_stack([r, g, b]) / 65535.0)
    C8 = meshio_opt._scale_rgb([np.array([255, 10]), np.array([128, 0]), np.array([0, 3])], "x")
    assert np.allclose(C8, np.array([[255, 128, 0], [10, 0, 3]]) / 255.0)


# --------------------------------------------------------------------------- #
# 12. imgforensics._ijg_table —— libjpeg の整数除算                             #
# --------------------------------------------------------------------------- #
def test_ijg_table_matches_libjpeg_integer_scaling():
    import imgforensics as F
    base = np.asarray(F.JPEG_LUMA_Q, dtype=np.int64)
    qs = list(range(1, 101))
    assert qs
    for q in qs:
        s = 5000 // q if q < 50 else 200 - 2 * q
        want = np.clip((base * s + 50) // 100, 1, 255)
        assert np.array_equal(F._ijg_table(q), want), q


# --------------------------------------------------------------------------- #
# 13. optics.fourier_plane_filter —— 奇数次微分のナイキスト                      #
# --------------------------------------------------------------------------- #
def test_odd_derivative_filter_has_no_unpaired_nyquist():
    import optics as o
    n = 64
    u = np.random.default_rng(0).random((n, n))
    for kind in ("derivative_x", "derivative_y"):
        H = o.fourier_plane_filter(n, kind, order=1)
        out = o.four_f_filter(u, H, invert=False)
        assert np.abs(out.imag).max() < 1e-12       # 以前は 0.34
    H2 = o.fourier_plane_filter(n, "derivative_x", order=2)
    assert H2[0, n // 2] != 0                       # 偶数次は従来どおり残す
    H_odd_n = o.fourier_plane_filter(63, "derivative_x", order=1)
    ref = (2j * np.pi * np.fft.fftfreq(63, d=1.0))[None, :] * np.ones((63, 1))
    assert np.array_equal(H_odd_n, ref.astype(np.complex128))


# --------------------------------------------------------------------------- #
# 14/15. mesh —— 小数点カンマ・コメント中の end_header・solid で始まる binary STL #
# --------------------------------------------------------------------------- #
def test_xyz_decimal_comma_refused_and_csv_still_read(tmp_path):
    import mesh
    p = tmp_path / "comma.xyz"
    p.write_text("1,5 2,5 3,5\n4,0 5,0 6,0\n")
    with pytest.raises(ValueError):
        mesh.read_points(str(p), with_colors=True)
    q = tmp_path / "csv.xyz"
    q.write_text("1,2,3\n4, 5, 6\n")
    P = mesh.read_points(str(q))
    assert np.array_equal(np.asarray(P), [[1, 2, 3], [4, 5, 6]])
    m = tmp_path / "mixed.xyz"
    m.write_text("1,2,3\n4 5 6\n")
    with pytest.raises(ValueError):
        mesh.read_points(str(m))
    s = tmp_path / "space.xyz"
    s.write_text("1 2 3\n4 5 6\n")
    assert np.array_equal(np.asarray(mesh.read_points(str(s))), [[1, 2, 3], [4, 5, 6]])


def test_ply_comment_mentioning_end_header(tmp_path):
    import mesh
    hdr = (b"ply\nformat binary_little_endian 1.0\nelement vertex 2\nproperty float x\n"
           b"property float y\nproperty float z\ncomment see end_header below\nend_header\n")
    body = np.array([[1, 2, 3], [4, 5, 6]], "<f4").tobytes()
    p = tmp_path / "c.ply"
    p.write_bytes(hdr + body)
    assert np.array_equal(np.asarray(mesh.read_points(str(p))), [[1, 2, 3], [4, 5, 6]])


def test_binary_stl_with_solid_header(tmp_path):
    import mesh
    head = b"solid part exported with facet normals".ljust(80, b" ")
    tri = struct.pack("<12fH", 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0)
    p = tmp_path / "s.stl"
    p.write_bytes(head + struct.pack("<I", 1) + tri)
    V, F = mesh.read_mesh(str(p))
    assert V.shape == (3, 3) and F.shape == (1, 3)
    a = tmp_path / "a.stl"
    a.write_text("solid t\nfacet normal 0 0 1\nouter loop\nvertex 0 0 0\nvertex 1 0 0\n"
                 "vertex 0 1 0\nendloop\nendfacet\nendsolid t\n")
    V2, F2 = mesh.read_mesh(str(a))
    assert V2.shape == (3, 3) and F2.shape == (1, 3)


# --------------------------------------------------------------------------- #
# 16-20. fullseye.jsonio                                                       #
# --------------------------------------------------------------------------- #
def test_jsonio_readable_nonfinite_falls_back_to_bytes():
    from fullseye import jsonio as J
    img = np.array([[1.0, np.nan], [-np.inf, 2.0]])
    s = J.to_json(img, "image", readable=True)
    env = json.loads(s)
    assert env["nonfinite"] is True and env["payload"]["encoding"] == "b64f64"
    back = J.from_json(s)[0]
    assert np.array_equal(back, img, equal_nan=True)
    ok = J.to_jsonable(np.array([[1.5, 2.0]]), "image", readable=True)
    assert ok["payload"]["encoding"] == "list"      # 有限なら従来どおり list


def test_jsonio_refuses_complex():
    from fullseye import jsonio as J
    with pytest.raises(ValueError):
        J.to_json(np.array([1 + 2j, 3 - 4j]), "signal")
    with pytest.raises(ValueError):
        J.to_jsonable({"shape": (4, 4), "cs": [np.zeros((3, 2), complex)]}, "contour")


def test_jsonio_contour_decode_checks_shape():
    from fullseye import jsonio as J
    env = J.to_jsonable({"shape": (4, 4), "cs": [np.zeros((3, 2))]}, "contour")
    env["payload"]["cs"][0] = J._encode_array(np.arange(9.).reshape(3, 3), False)
    with pytest.raises(ValueError):
        J.from_jsonable(env)
    good = J.to_jsonable({"shape": (4, 4), "cs": [np.ones((3, 2))]}, "contour")
    v, s = J.from_jsonable(good)
    assert s == "contour" and v["shape"] == (4, 4) and np.array_equal(v["cs"][0], np.ones((3, 2)))


def _sig(payload):
    return {"fullseye_sort": "signal", "version": 1, "payload": payload}


@pytest.mark.parametrize("payload", [
    {"encoding": "list", "dtype": "float64", "shape": [2], "data": ["1.5", "nan"]},
    {"encoding": "list", "dtype": "float16", "shape": [1], "data": [0.1]},
    {"encoding": "list", "dtype": "uint8", "shape": [1], "data": [300]},
    {"encoding": "list", "dtype": "object", "shape": [1], "data": [{"a": 1}]},
    {"encoding": "list", "dtype": "U3", "shape": [1], "data": ["abc"]},
    {"encoding": "b64i64", "dtype": "uint8", "shape": [2],
     "data": base64.b64encode(np.array([300, -1], "<i8").tobytes()).decode()},
    {"encoding": "b64u8", "dtype": "bool", "shape": [3],
     "data": base64.b64encode(np.array([0, 2, 255], "u1").tobytes()).decode()},
    {"encoding": "b64f64", "dtype": "int64", "shape": [1],
     "data": base64.b64encode(np.array([1.0], "<f8").tobytes()).decode()},
])
def test_jsonio_decoder_whitelists_dtype(payload):
    from fullseye import jsonio as J
    with pytest.raises(ValueError):
        J.from_jsonable(_sig(payload))


def test_jsonio_round_trips_unchanged_dtypes():
    from fullseye import jsonio as J
    arrs = [np.array([1.5, -2.0]), np.array([1, -2, 3], np.int32), np.array([True, False]),
            np.array([0.1, 0.2], np.float32), np.array([2 ** 63 + 5], np.uint64),
            np.zeros((0,))]
    assert arrs
    for a in arrs:
        for readable in (False, True):
            b = J.from_json(J.to_json(a, "signal", readable=readable))[0]
            assert np.array_equal(a, b), (a, readable)
            # b64f64 は従来から float64 で返す(float32 も)。それ以外は dtype まで戻る
            if readable or a.dtype.kind != "f":
                assert b.dtype == a.dtype, (a, readable)


@pytest.mark.parametrize("env", [
    {"fullseye_sort": "region", "version": 1, "payload": {"encoding": "rle", "shape": [2, 2]}},
    {"fullseye_sort": "region", "version": 1,
     "payload": {"encoding": "rle", "shape": [2, 2, 7], "runs": [1, 3]}},
    {"fullseye_sort": "region", "version": 1,
     "payload": {"encoding": "rle", "shape": [2, 2], "runs": [1.9, 2.9]}},
    {"fullseye_sort": "feature", "version": 1, "payload": {}},
    {"fullseye_sort": "feature", "version": 1, "payload": {"value": True}},
    {"fullseye_sort": "feature", "version": True, "payload": {"value": 1}},
])
def test_jsonio_malformed_envelopes_raise_valueerror(env):
    from fullseye import jsonio as J
    with pytest.raises(ValueError):
        J.from_jsonable(env)
    with pytest.raises(ValueError):
        J.as_value(env)


def test_jsonio_region_and_feature_round_trip_unchanged():
    from fullseye import jsonio as J
    m = np.array([[0, 1, 1], [1, 0, 0]], float)
    assert np.array_equal(J.from_json(J.to_json(m, "region"))[0], m)
    assert J.from_json(J.to_json(2.5, "feature"))[0] == 2.5
    v = J.from_json(J.to_json(float("nan"), "feature"))[0]
    assert np.isnan(v)


# --------------------------------------------------------------------------- #
# 21/22. fullseye.xlsxio                                                        #
# --------------------------------------------------------------------------- #
def test_xlsx_dict_table_and_numpy_scalars(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    from fullseye import xlsxio as X
    p = tmp_path / "d.xlsx"
    X.save_xlsx_report([("t", {"area": 12.5, "perimeter": 14.0}, "table")], str(p))
    rows = [[c.value for c in r] for r in openpyxl.load_workbook(p).active.iter_rows()]
    assert ["key", "value"] in [r[:2] for r in rows]
    assert ["area", 12.5] in [r[:2] for r in rows]
    q = tmp_path / "n.xlsx"
    X.save_xlsx_report([("t", [{"id": np.int64(3), "v": np.float32(0.5)}], "table")], str(q))
    vals = [c.value for r in openpyxl.load_workbook(q).active.iter_rows() for c in r]
    assert 3 in vals and 0.5 in vals and "3" not in vals


def test_xlsx_thumb_levels_and_longest():
    pytest.importorskip("openpyxl")
    from fullseye import xlsxio as X
    ramp = np.tile(np.arange(256, dtype=np.uint8), (8, 1))
    th = X._thumb(ramp)
    assert np.unique(th).size == 256                # 以前は 0/1 の 2 値
    big = np.zeros((1000, 300))
    assert max(X._thumb(big, longest=256).shape) <= 256
    small = np.random.default_rng(0).random((40, 30))
    assert np.array_equal(X._thumb(small), small)   # 小さい float は素通し


# --------------------------------------------------------------------------- #
# 23. spc.gum_expanded —— NaN の自由度を無限大と扱っていた                       #
# --------------------------------------------------------------------------- #
def test_gum_expanded_rejects_nan_dof():
    import spc
    with pytest.raises(ValueError):
        spc.gum_expanded({"u": [1.0, 1.0], "sensitivity": [1.0, 1.0], "dof": [4.0, np.nan]})
    r = spc.gum_expanded({"u": [1.0, 1.0], "sensitivity": [1.0, 1.0], "dof": [4.0, np.inf]})
    assert float(np.asarray(r["dof_effective"]).ravel()[0]) == pytest.approx(16.0)


# --------------------------------------------------------------------------- #
# 24. astrostack.aperture_photometry —— 画像外の中心・欠けた開口                 #
# --------------------------------------------------------------------------- #
def test_aperture_photometry_off_image_and_truncated():
    import astrostack as A
    img = np.full((64, 64), 10.0)
    yy, xx = np.mgrid[:64, :64]
    for rc, trunc in (((32.0, 32.0), False), ((1.0, 32.0), True)):
        star = img + 1000 * np.exp(-((yy - rc[0]) ** 2 + (xx - rc[1]) ** 2) / (2 * 1.5 ** 2)) \
            / (2 * np.pi * 1.5 ** 2)
        r = A.aperture_photometry(star, [rc], r_aperture=5.0)[0]
        assert r["truncated"] is trunc
        if not trunc:
            assert r["flux"] == pytest.approx(995.26, abs=0.01)   # 中央は従来値のまま
    for rc in ((-3.0, 32.0), (-100.0, -100.0), (32.0, 64.0)):
        with pytest.raises(ValueError):
            A.aperture_photometry(img, [rc])


# --------------------------------------------------------------------------- #
# 25. backends_measure1d —— 0..255 の float が 1 に潰れていた                   #
# --------------------------------------------------------------------------- #
def test_measure1d_refuses_0_255_float():
    import backends_measure1d as B
    img = np.full((64, 64), 50.0)
    img[:, 20:40] = 200.0
    with pytest.raises(ValueError):
        B.m1_measure_pos(img, 0.0, 0.1)
    a = B.m1_measure_pairs(img / 255.0, 0.0, 0.1)
    b = B.m1_measure_pairs(img.astype(np.uint8), 0.0, 0.1)
    assert float(a) == float(b) == 1.0


# --------------------------------------------------------------------------- #
# 26. optscene の諸元ビルダ —— NaN / 負の値                                     #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("call", [
    lambda s: s.optical_camera(azimuth_deg=float("nan")),
    lambda s: s.sensor_spec(read_noise_e=-1.0),
    lambda s: s.sensor_spec(read_noise_e=float("nan")),
    lambda s: s.light_spec(wavelength_nm=-1.0),
    lambda s: s.light_spec(wavelength_nm=0.0),
    lambda s: s.light_spec(wavelength_nm=float("nan")),
    lambda s: s.light_spec(size_mm=-5.0),
])
def test_optscene_builders_refuse_bad_physics(call):
    import optscene
    with pytest.raises(ValueError):
        call(optscene)


def test_optscene_builders_defaults_unchanged():
    import optscene as s
    assert s.light_spec()["wavelength_nm"] == 550.0
    assert s.sensor_spec()["read_noise_e"] == 2.5
    assert s.sensor_spec(read_noise_e=0.0)["read_noise_e"] == 0.0
    cam = s.optical_camera(azimuth_deg=30.0, tilt_deg=20.0)
    assert np.isfinite(cam["R"]).all()


# --------------------------------------------------------------------------- #
# 27. matappear.thin_film_reflectance —— cos_theta の範囲外を clip していた      #
# --------------------------------------------------------------------------- #
def test_thin_film_refuses_out_of_range_cos():
    import matappear as m
    for c in (5.0, -0.5, float("nan")):
        with pytest.raises(ValueError):
            m.thin_film_reflectance([550.0], cos_theta=c)
    r1 = m.thin_film_reflectance([550.0], cos_theta=1.0)
    r2 = m.thin_film_reflectance([550.0], cos_theta=1.0 + 1e-15)   # 丸めの屑は許す
    assert np.array_equal(r1, r2)
    N = np.zeros((4, 4, 3))
    N[..., 2] = 1.0
    assert np.isfinite(m.thin_film_rgb(N)).all()


# --------------------------------------------------------------------------- #
# 28. imgforensics._as_image —— complex を実部で受け取っていた                   #
# --------------------------------------------------------------------------- #
def test_imgforensics_refuses_complex_and_strings():
    import imgforensics as F
    x = np.random.default_rng(0).random((64, 64))
    with pytest.raises(ValueError):
        F.perceptual_hash(x + 1j * x)
    with pytest.raises(ValueError):
        F._as_image(np.array([["a", "b"], ["c", "d"]]))
    assert F._as_image(x.astype(np.float32)).dtype == np.float64
    assert F._as_image((x > 0.5)).dtype == np.float64
