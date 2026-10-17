# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""optscene の波長積分(2026-10-15)と、棚卸しの束 2 で見つかった「黙って間違う」7 件の門。

外部真値: Planck の式(SI 2019 の定数)と Wien の変位則(CODATA b)、Green 2008 の Si の吸収係数の公表値
(1000 nm で 64 /cm、1100 nm で 3.5 /cm、CC0)、台帳の出典の EMVA1288 data overview(QE は 545 nm で測った値)と
別の会社の EMVA1288 公表値(同じ型番を 525 nm で 63.93 %)、薄肉レンズの錯乱円を直接解いた近点・遠点
(Greivenkamp OPTI-201/202 第 17 講と同じ幾何)、Rayleigh の λ/4 の焦点深度 ±2λN²、ハーフミラーの往復 R·T。
どの門にも、直し方を戻す探針を添える(探針で門が赤になることを確かめる)。
"""
import math

import numpy as np
import pytest

import illumdesign
import materials as MT
import opsoptics
import optscene as OS
import visiondesign as VD

# --------------------------------------------------------------------------- 共通の小さな構成
LENS = dict(focal_mm=25.0, f_number=4.0, working_distance_mm=200.0)
M = 25.0 / 175.0                                   # 薄肉レンズを WD 200 mm に合焦: m = f/(WD − f)


def _small_sensor(**kw):
    return OS.sensor_spec(pixel_um=13.8, resolution=(64, 48), **kw)


def _plate(z=0.0, material=None):
    return OS.scene_box((0.0, 0.0, z + 0.05), (6.0, 4.0, 0.05), material)


def _dome(lam=550.0, **kw):
    return OS.light_spec("dome", wavelength_nm=lam, radius_mm=80.0, height_mm=70.0, n=24, **kw)


# =========================================================================== 1. QE が波長で変わる
def test_spectral_mode_radiance_follows_qe_times_photon_ratio():
    """灰色の lambert をドームで撮る: 分光の経路の像の比 = QE(λ)·λ の比(材質・幾何は波長によらない)。"""
    sensor = _small_sensor()
    lens = OS.lens_spec(**LENS)
    got = {}
    for lam in (550.0, 940.0, 1100.0):
        lay = OS.vision_layout(sensor, lens, [_dome(lam, source="laser")], scene=[_plate()])
        r = OS.layout_capture(lay, supersample=1, apply_diffraction=False, raw=True, mode="spectral")
        got[lam] = float(r["radiance"].mean())
    for lam in (940.0, 1100.0):
        want = OS._sensor_qe(sensor, lam) * lam / (OS._sensor_qe(sensor, 550.0) * 550.0)
        assert got[lam] / got[550.0] == pytest.approx(want, rel=1e-9)
    assert got[1100.0] < 0.01 * got[550.0]          # Si は 1100 nm でほとんど感じない


def test_rgb_mode_is_unchanged_and_qe_does_not_move_it():
    """既定の RGB の経路は波長によらない(後方互換)—— 分光にしたいなら mode を選ぶ。"""
    sensor = _small_sensor()
    lens = OS.lens_spec(**LENS)
    vals = []
    for lam in (550.0, 1100.0):
        lay = OS.vision_layout(sensor, lens, [_dome(lam, source="laser")], scene=[_plate()])
        vals.append(float(OS.layout_capture(lay, supersample=1, apply_diffraction=False, raw=True)["radiance"].mean()))
    assert vals[0] == pytest.approx(vals[1], rel=1e-12)


def test_spectral_equals_rgb_for_550nm_flat_qe_grey_lambert():
    """後方互換の門: 550 nm の単色・平らな QE・平らな透過率・灰色の lambert なら 2 つの経路は同じ数。"""
    sensor = _small_sensor(qe_curve=[(300.0, 0.6), (1200.0, 0.6)])
    lay = OS.vision_layout(sensor, OS.lens_spec(**LENS), [_dome(550.0, source="laser")], scene=[_plate()])
    a = OS.layout_capture(lay, supersample=1, raw=True, mode="spectral")["radiance"]
    b = OS.layout_capture(lay, supersample=1, raw=True, mode="rgb")["radiance"]
    assert np.max(np.abs(a - b)) <= 1e-12 * float(b.max())


def test_silicon_qe_at_published_green_2008_absorption():
    """Green 2008 の公表値(Si の吸収係数 1000 nm で 64 /cm、1100 nm で 3.5 /cm)から QE の比を閉形式で。

    QE ∝ (1 − R)(1 − e^{−αW})。R は空気/Si の Fresnel(n は公表値 3.57 / 3.54)。模型の基準波長の倍率は比で消える。
    """
    sensor = _small_sensor(si_collection_um=3.0)
    W = 3e-4                                                     # cm
    pub = {1000.0: (64.0, 3.5720), 1100.0: (3.5, 3.5420)}

    def qe_closed(lam):
        a, n = pub[lam]
        R = ((n - 1.0) / (n + 1.0)) ** 2
        return (1.0 - R) * (1.0 - math.exp(-a * W))

    got = OS._sensor_qe(sensor, 1100.0) / OS._sensor_qe(sensor, 1000.0)
    assert got == pytest.approx(qe_closed(1100.0) / qe_closed(1000.0), rel=0.03)
    # 1100 nm の QE は 550 nm の 0.2 % 未満(集める深さ 3 µm)。10 µm でも 0.5 % 未満 —— 吸収長 1/α ≈ 2.9 mm
    assert OS._sensor_qe(sensor, 1100.0) < 0.002 * OS._sensor_qe(sensor, 550.0)
    deep = _small_sensor(si_collection_um=10.0)
    assert OS._sensor_qe(deep, 1100.0) < 0.005 * OS._sensor_qe(deep, 550.0)


def test_catalog_qe_is_anchored_at_545nm_and_near_a_second_published_emva_point():
    """台帳の QE は 545 nm の値(出典の表に All measurements have been taken at 545 nm とある)。

    別の会社が同じ型番を 525 nm で 63.93 % と公表している(EMVA1288)。模型(形は Si の n,k、倍率は 545 nm)は
    525 nm で 72 % を出す —— 公表値との差 13 % は、2 社の値の差(69 % と 63.93 %、波長 20 nm 違い)と同じ桁で、
    **模型が可視の青側の落ち込みを持たない**ことを示す(未解決として残す)。門は 15 % の帯。
    """
    s = OS.sensor_spec(model="IMX252")
    assert s["qe_reference_nm"] == 545.0
    assert OS._sensor_qe(s, 545.0) == pytest.approx(0.69, rel=1e-12)
    assert OS._sensor_qe(s, 525.0) == pytest.approx(0.6393, rel=0.15)


def test_qe_curve_is_not_extrapolated():
    s = _small_sensor(qe_curve=[(400.0, 0.5), (1000.0, 0.1)])
    with pytest.raises(ValueError, match="not extrapolated"):
        OS._sensor_qe(s, 1100.0)
    with pytest.raises(ValueError):
        _small_sensor(qe_curve=[(400.0, 0.5), (1000.0, 1.5)])


def test_metal_colour_follows_the_material_table_in_spectral_mode():
    """Al の 800 nm の谷: 分光の経路の金属の明るさの比 = materials の Fresnel(別の実装)の垂直入射の比。"""
    al = OS.scene_material("conductor", metal="al", finish="random", roughness_um=0.01)
    scene = [OS.scene_box((0.0, 0.0, 0.5), (30.0, 30.0, 0.5), al)]
    cam = OS.optical_camera(focal_mm=25.0, pixel_um=13.8, resolution=(8, 8), working_distance_mm=200.0,
                            image_distance_mm=OS._thin_lens_image_distance(25.0, 200.0))
    light = OS.light_spec("coaxial", radius_mm=60.0, height_mm=200.0, n=64, source="laser")
    v = {}
    for lam in (600.0, 800.0):
        v[lam] = float(OS.render_optscene(scene, cam, [light], wavelength_nm=lam, spectral=True)[3:5, 3:5].mean())
    R = {lam: float(MT.material_reflectance("AL", lam - 1.0, lam + 1.0, 3)[1, 1]) for lam in (600.0, 800.0)}
    assert v[800.0] / v[600.0] == pytest.approx(R[800.0] / R[600.0], rel=0.01)
    assert R[800.0] < R[600.0]                                    # 谷が本当にある(門が空でない)


# =========================================================================== 2. テレセン
def _imaged_width(telecentric, z):
    sensor = OS.sensor_spec(pixel_um=13.8, resolution=(256, 192))
    lens = OS.lens_spec(**LENS, telecentric=telecentric)
    lay = OS.vision_layout(sensor, lens, [_dome()], scene=[_plate(z)])
    mask = np.asarray(OS.layout_capture(lay, supersample=1, apply_diffraction=False)["part_mask"], bool)
    return int(mask[mask.shape[0] // 2].sum())


def test_telecentric_magnification_does_not_change_with_height():
    want = 12.0 * M / 13.8e-3                                     # 124.2 px
    assert abs(_imaged_width(True, 0.0) - want) <= 1.0
    assert abs(_imaged_width(True, 20.0) - want) <= 1.0
    # 透視は 20 mm 持ち上げると WD/(WD − 20) 倍(この門が素通りでないことの確認)
    assert abs(_imaged_width(False, 20.0) - want * 200.0 / 180.0) <= 1.5


def test_probe_dropping_the_telecentric_flag_turns_the_gate_red(monkeypatch):
    real = OS.optical_camera
    monkeypatch.setattr(OS, "optical_camera", lambda *a, **k: real(*a, **dict(k, telecentric=False)))
    assert abs(_imaged_width(True, 20.0) - 12.0 * M / 13.8e-3) > 5.0


def test_telecentric_rays_are_parallel_and_spaced_by_the_object_pixel():
    cam = OS.optical_camera(focal_mm=25.0, pixel_um=13.8, resolution=(4, 3), working_distance_mm=200.0,
                            image_distance_mm=OS._thin_lens_image_distance(25.0, 200.0), telecentric=True)
    o, d = OS.camera_rays(cam)
    assert np.allclose(d, cam["forward"][None, :], atol=0.0)
    assert np.linalg.norm(o[1] - o[0]) == pytest.approx(13.8e-3 / M, rel=1e-12)
    assert cam["projection"] == "orthographic"


# =========================================================================== 3. 明示した値を捨てない
def test_explicit_values_survive_a_catalog_model():
    s = OS.sensor_spec(model="PYTHON 1300", quantum_efficiency=0.6, read_noise_e=2.5)
    assert s["read_noise_e"] == 2.5 and s["quantum_efficiency"] == 0.6
    assert set(s["explicit_overrides"]) == {"quantum_efficiency", "read_noise_e"}
    t = OS.sensor_spec(model="PYTHON 1300")
    assert t["read_noise_e"] == 11.0 and t["quantum_efficiency"] == 0.53 and t["explicit_overrides"] == ()
    with pytest.raises(ValueError, match="contradicts"):
        OS.sensor_spec(model="PYTHON 1300", pixel_um=3.45)
    with pytest.raises(ValueError, match="contradicts"):
        OS.lens_spec(model="Fujinon HF25XA-1", focal_mm=35.0)
    lit = OS.light_spec(model="generic ring-70", wavelength_nm=850.0)
    assert lit["wavelength_nm"] == 850.0 and lit["kind"] == "ring"
    assert OS.sensor_spec(model="EV76C570")["shutter"] == "switchable"   # 台帳に在る型番が組める


# =========================================================================== 4. 光源のスペクトル
def _planck(lam_nm, T):
    h, c, k = 6.62607015e-34, 299792458.0, 1.380649e-23
    lam = lam_nm * 1e-9
    return 2 * h * c * c / lam ** 5 / math.expm1(h * c / (lam * k * T))


def test_halogen_weights_are_planck_energy_in_each_bin():
    """ハロゲンの重み = 黒体 3000 K のエネルギーを 380〜1100 nm の等幅 5 区間で積分した割合(独立の Simpson)。"""
    light = OS.light_spec("ring", source="halogen")
    lams, w = OS.light_wavelengths(light, 5)
    edges = np.linspace(380.0, 1100.0, 6)
    e = []
    for a, b in zip(edges[:-1], edges[1:]):
        x = np.linspace(a, b, 2001)
        y = np.array([_planck(v, 3000.0) for v in x])
        e.append(float(np.sum((y[:-1] + y[1:]) * 0.5 * np.diff(x))))
    want = np.array(e) / sum(e)
    assert np.allclose(w, want, rtol=2e-4, atol=0.0)
    assert lams[-1] > 1000.0                                     # 近赤外を落としていない
    # 峰は Wien の変位則(b = 2897.771955 µm·K)
    peak = OS._light_spectrum(dict(light, band_nm=(300.0, 3000.0)), n_points=27001)
    assert peak[int(np.argmax(peak[:, 1])), 0] == pytest.approx(2897771.955 / 3000.0, abs=0.2)


def test_led_weights_keep_the_peak_and_sum_to_one():
    lams, w = OS.light_wavelengths(OS.light_spec("ring", wavelength_nm=850.0, bandwidth_nm=40.0), 5)
    assert float(np.sum(w)) == pytest.approx(1.0, abs=1e-12)
    assert float(np.sum(lams * w)) == pytest.approx(850.0, abs=0.5)   # Ohno の形は左右対称
    assert lams[2] == pytest.approx(850.0, abs=1e-6)


def test_light_wavelengths_has_the_pairs_adapter():
    r = opsoptics.call("light_wavelengths", OS.light_spec("ring", source="halogen"), 5)
    assert isinstance(r, np.ndarray) and r.shape == (5, 2)
    raw = OS.light_wavelengths(OS.light_spec("ring", source="halogen"), 5)
    assert isinstance(raw, tuple)                                 # 素の関数は後方互換のタプル


# =========================================================================== 5. 被写界深度と回折(式は 1 本)
def _greivenkamp_dof_mm(f, wd, N, c_mm):
    """薄肉レンズの錯乱円を直接解く: 像 v' = f s'/(s' − f)、ぼけ径 D|v' − v|/v' = c、D = f/N。"""
    D = f / N
    v = f * wd / (wd - f)
    obj = lambda vp: f * vp / (vp - f)
    return obj(v * D / (D + c_mm)) - obj(v * D / (D - c_mm))      # 遠点(像が手前)− 近点(像が奥)


def test_two_entry_points_agree_name_by_name_and_match_closed_forms():
    fe = VD.system_feasibility(defect_um=50.0, focal_mm=25.0, working_distance_mm=200.0,
                               pixel_pitch_um=3.45, f_number=4.0, wavelength_um=0.55)
    lay = OS.vision_layout(OS.sensor_spec(), OS.lens_spec(**LENS), [OS.light_spec(wavelength_nm=550.0)])
    b = lay["budget"]
    nw = 4.0 * (1.0 + M)
    geo = _greivenkamp_dof_mm(25.0, 200.0, 4.0, 3.45e-3)
    diff = 4.0 * 0.55e-3 * nw * nw / (M * M)                      # Rayleigh λ/4: 像側 ±2λN_w²、全幅 4λN_w²
    assert fe["depth_of_field_geometric_mm"] == pytest.approx(geo, rel=1e-9)
    assert b["dof_geometric_um"] * 1e-3 == pytest.approx(geo, rel=1e-9)
    assert fe["depth_of_field_diffraction_mm"] == pytest.approx(diff, rel=1e-12)
    assert b["dof_diffraction_um"] * 1e-3 == pytest.approx(diff, rel=1e-12)
    assert b["dof_um"] * 1e-3 == pytest.approx(fe["depth_of_field_combined_mm"], rel=1e-12)
    assert fe["depth_of_field_mm"] == pytest.approx(1.5456, abs=1e-4)          # 幾何(判定に使う側)は動かない
    # エアリー: 径 2.44λN_w と半径 1.22λN_w を名前で。律速の判定は両入口とも径
    assert b["airy_diameter_um"] == pytest.approx(fe["airy_diameter_um"], rel=1e-12)
    assert b["airy_radius_um"] == pytest.approx(1.22 * 0.55 * nw, rel=1e-12)
    assert b["airy_diameter_um"] == pytest.approx(2.44 * 0.55 * nw, rel=1e-12)
    assert b["diffraction_criterion"] == fe["diffraction_criterion"] == "airy_diameter"
    rp = VD.resolving_power(3.45, 4.0, M, 0.55)
    assert b["limit_um"] == pytest.approx(rp["resolution_object_um"], rel=1e-12)
    assert b["limited_by"] == rp["limited_by"]


def test_probe_half_diffraction_term_turns_the_closed_form_gate_red(monkeypatch):
    real = VD._depth_of_field

    def old(*a):
        r = dict(real(*a))
        r["diffraction_mm"] *= 0.5                                # 2026-10-15 までの optscene の係数
        r["combined_mm"] = r["geometric_mm"] + r["diffraction_mm"]
        return r
    monkeypatch.setattr(VD, "_depth_of_field", old)
    b = OS.optical_budget(**LENS, pixel_um=3.45, wavelength_nm=550.0)
    nw = 4.0 * (1.0 + M)
    assert abs(b["dof_diffraction_um"] * 1e-3 - 4.0 * 0.55e-3 * nw * nw / (M * M)) > 0.5


# =========================================================================== 6. 同軸の往復 R·T
def test_coaxial_round_trip_is_r_times_t():
    cam = OS.optical_camera(focal_mm=25.0, pixel_um=13.8, resolution=(16, 12), working_distance_mm=200.0,
                            image_distance_mm=OS._thin_lens_image_distance(25.0, 200.0))
    scene = [_plate()]
    co = OS.light_spec("coaxial", radius_mm=40.0, height_mm=110.0, n=24,
                       splitter_reflectance=0.4, splitter_transmittance=0.55)
    bare = illumdesign.light_source(kind="coaxial", radius_mm=40.0, height_mm=110.0, n=24)
    a = OS.render_optscene(scene, cam, [co])
    b = OS.render_optscene(scene, cam, [bare])
    assert float(a.sum() / b.sum()) == pytest.approx(0.4 * 0.55, rel=1e-12)
    with pytest.raises(ValueError, match="energy conservation"):
        OS.light_spec("coaxial", splitter_reflectance=0.7, splitter_transmittance=0.7)


def test_coaxial_splitter_also_dims_the_other_lights_in_a_layout():
    """カメラは同軸ユニットのハーフミラー越しに見るので、同じレイアウトのドームの光も T 倍になる。"""
    sensor, lens = _small_sensor(), OS.lens_spec(**LENS)
    dome = _dome()
    co = OS.light_spec("coaxial", radius_mm=40.0, height_mm=110.0, n=24)
    one = OS.layout_capture(OS.vision_layout(sensor, lens, [dome], scene=[_plate()]),
                            supersample=1, apply_diffraction=False, raw=True)["radiance"]
    co_only = OS.layout_capture(OS.vision_layout(sensor, lens, [co], scene=[_plate()]),
                                supersample=1, apply_diffraction=False, raw=True)["radiance"]
    both = OS.layout_capture(OS.vision_layout(sensor, lens, [dome, co], scene=[_plate()]),
                             supersample=1, apply_diffraction=False, raw=True)["radiance"]
    assert np.allclose(both, 0.5 * one + co_only, rtol=1e-12, atol=1e-30)


def test_probe_lossless_splitter_turns_the_coaxial_gate_red(monkeypatch):
    monkeypatch.setattr(OS, "_splitter_transmittance", lambda lights: 1.0)
    cam = OS.optical_camera(focal_mm=25.0, pixel_um=13.8, resolution=(16, 12), working_distance_mm=200.0,
                            image_distance_mm=OS._thin_lens_image_distance(25.0, 200.0))
    co = OS.light_spec("coaxial", radius_mm=40.0, height_mm=110.0, n=24)
    bare = illumdesign.light_source(kind="coaxial", radius_mm=40.0, height_mm=110.0, n=24)
    ratio = float(OS.render_optscene([_plate()], cam, [co]).sum() / OS.render_optscene([_plate()], cam, [bare]).sum())
    assert abs(ratio - 0.25) > 0.1


# =========================================================================== 7. 回折は光源ごとの λ
def test_two_light_capture_is_the_sum_of_single_light_captures():
    """2 色の光源(450 / 900 nm)の像 = 1 色ずつ撮った像の和(各々は自分の λ で回折ぼけ)。

    2026-10-15 まではバジェットの平均の 675 nm で両方をぼかしていたので、和が合わなかった。
    """
    sensor = OS.sensor_spec(pixel_um=1.0, resolution=(48, 48))
    lens = OS.lens_spec(focal_mm=25.0, f_number=16.0, working_distance_mm=50.0)
    part = OS.scene_box((0.0, 0.0, 0.05), (0.01, 0.01, 0.05))     # 20 µm 角(エアリー半径 18 / 35 µm と同じ桁)
    blue, nir = _dome(450.0, source="laser"), _dome(900.0, source="laser")
    cap = lambda ls: OS.layout_capture(OS.vision_layout(sensor, lens, ls, scene=[part]), supersample=1,
                                       raw=True)["radiance"]
    both, a, b = cap([blue, nir]), cap([blue]), cap([nir])
    assert np.allclose(both, a + b, rtol=1e-9, atol=1e-30)
    old = OS.diffraction_blur(OS.layout_capture(OS.vision_layout(sensor, lens, [blue, nir], scene=[part]),
                                                supersample=1, raw=True, apply_diffraction=False)["radiance"],
                              OS.vision_layout(sensor, lens, [blue, nir], scene=[part])["camera"],
                              f_number=16.0 * (1.0 + 25.0 / 25.0), wavelength_nm=675.0)
    assert float(np.max(np.abs(old - (a + b)))) > 1e-3 * float(np.max(a + b))   # 探針: 1 波長のぼけは合わない


# =========================================================================== 透明体越しのバックライト
def test_backlight_through_a_glass_plate_is_fresnel_times_open():
    """N-BK7 の板越しのバックライト = 開けた所の (1 − R)²(R は垂直入射の Fresnel)。2026-10-15 まで黒かった。"""
    cam = OS.optical_camera(focal_mm=25.0, pixel_um=13.8, resolution=(32, 8), working_distance_mm=200.0,
                            image_distance_mm=OS._thin_lens_image_distance(25.0, 200.0))
    glass = OS.scene_material("dielectric", glass="N-BK7")
    plate = OS.scene_box((-6.0, 0.0, 1.0), (6.0, 30.0, 1.0), glass)          # 左半分だけ板
    bl = OS.light_spec("backlight", radius_mm=60.0, height_mm=30.0, n=24, source="laser")
    img = OS.render_optscene([plate], cam, [bl], wavelength_nm=550.0, spectral=True)
    n = OS._dielectric_n("N-BK7", 550.0)
    R = ((n - 1.0) / (n + 1.0)) ** 2
    through, open_ = float(img[4, 6].mean()), float(img[4, 26].mean())
    assert through / open_ == pytest.approx((1.0 - R) ** 2, rel=0.01)


def test_silicon_wafer_is_opaque_at_850_and_clear_at_1100():
    """Si の板(0.5 mm、材料表の k)越しのバックライト: 1100 nm は (1 − R)² e^{−αt}、850 nm は 1e-10 未満。"""
    cam = OS.optical_camera(focal_mm=25.0, pixel_um=13.8, resolution=(32, 8), working_distance_mm=200.0,
                            image_distance_mm=OS._thin_lens_image_distance(25.0, 200.0))
    si = OS.scene_material("dielectric", glass="SI", absorption_from_k=True)
    plate = OS.scene_box((-6.0, 0.0, 1.0), (6.0, 30.0, 0.25), si)
    bl = OS.light_spec("backlight", radius_mm=60.0, height_mm=30.0, n=24, source="laser")
    ratio = {}
    for lam in (850.0, 1100.0):
        img = OS.render_optscene([plate], cam, [bl], wavelength_nm=lam, spectral=True)
        ratio[lam] = float(img[4, 6].mean()) / float(img[4, 26].mean())
    c = MT.material_optical_constants("SI", 1100.0)
    want = (1.0 - c["reflectance_normal"]) ** 2 * math.exp(-c["alpha_per_cm"] * 0.05)
    assert ratio[1100.0] == pytest.approx(want, rel=0.01)
    assert ratio[850.0] < 1e-10
