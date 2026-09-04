# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""optscene(物理空間の光学シーン)の検証。

方針: **閉じた式か、同じ量を別経路で出した値**とだけ突き合わせる。絵が「それらしい」
ことは検証にしない ―― 外観検査の学習データを作る層なので、真値がずれたまま
もっともらしい画像が出るのが一番まずい。
"""
import numpy as np
import pytest

import illumdesign
import optscene as OS


def _cam(**kw):
    kw.setdefault("focal_mm", 8.0)
    kw.setdefault("pixel_um", 3.45)
    kw.setdefault("resolution", (160, 160))
    kw.setdefault("working_distance_mm", 300.0)
    return OS.optical_camera(**kw)


def _point_light(pos, aim=(0.0, 0.0, -1.0), intensity=1.0, cos_exponent=1.0):
    """発光点 1 つだけの光源(閉じた式と突き合わせるため)。"""
    return {"kind": "point", "emitters": np.array([pos], float),
            "directions": np.array([aim], float),
            "intensity": float(intensity), "cos_exponent": float(cos_exponent)}


# --------------------------------------------------------------------------- #
# カメラ・光線
# --------------------------------------------------------------------------- #
def test_camera_rays_reproject_to_the_originating_pixel():
    """交点を K で再投影したら元の画素に戻る(往復が閉じていなければ真値は信用できない)。"""
    cam = _cam(resolution=(64, 48), tilt_deg=20.0, azimuth_deg=35.0)
    o, d = OS.camera_rays(cam)
    hit = OS.trace_rays([OS.scene_plane(0.0)], o, d)
    m = hit["index"] >= 0
    pc = hit["point"][m] @ cam["R"].T + cam["t"]
    uv = (pc / pc[:, 2:3]) @ cam["K"].T
    vv, uu = np.mgrid[0:cam["height"], 0:cam["width"]]
    px = np.stack([uu.ravel(), vv.ravel()], -1)[m]
    assert np.abs(uv[:, :2] - px).max() < 1e-9


def test_field_of_view_matches_the_thin_lens_relation():
    cam = _cam(resolution=(200, 100), focal_mm=12.0, working_distance_mm=250.0)
    w = 200 * 3.45e-3 * 250.0 / 12.0
    assert cam["fov_mm"][0] == pytest.approx(w, rel=1e-12)
    assert cam["fov_mm"][1] == pytest.approx(w / 2.0, rel=1e-12)


def test_reflect_rays_preserves_angle_and_plane():
    rng = np.random.default_rng(0)
    d = rng.normal(size=(64, 3))
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    n = rng.normal(size=(64, 3))
    n /= np.linalg.norm(n, axis=1, keepdims=True)
    r = OS.reflect_rays(d, n)
    assert np.allclose(np.linalg.norm(r, axis=1), 1.0, atol=1e-12)
    # 入射角 = 反射角、かつ 3 本は同一平面
    assert np.allclose((d * n).sum(1), -(r * n).sum(1), atol=1e-12)
    assert np.abs((np.cross(d, n) * r).sum(1)).max() < 1e-12


def test_reflect_rays_is_independent_of_the_normal_sign():
    d = np.array([[0.3, 0.0, -0.954]])
    d /= np.linalg.norm(d)
    n = np.array([[0.0, 0.0, 1.0]])
    assert np.allclose(OS.reflect_rays(d, n), OS.reflect_rays(d, -n), atol=1e-15)


# --------------------------------------------------------------------------- #
# 幾何の真値
# --------------------------------------------------------------------------- #
def test_depth_of_a_sphere_apex_is_the_working_distance_minus_its_height():
    cam = _cam(resolution=(161, 161))                # 奇数 = 光軸をちょうど 1 画素が通る
    sph = OS.scene_sphere((0.0, 0.0, 5.0), 5.0)
    d = OS.optscene_depth([sph], cam)
    assert np.nanmin(d) == pytest.approx(300.0 - 10.0, abs=1e-9)


def test_depth_is_nan_where_nothing_is_hit():
    """背景を 0 で埋めない(「距離 0 の面」と区別できなくなる)。"""
    cam = _cam(resolution=(32, 32))
    d = OS.optscene_depth([OS.scene_sphere((0.0, 0.0, 3.0), 1.0)], cam)
    assert np.isnan(d).any() and np.isfinite(d).any()


def test_silhouette_area_matches_pi_r_squared():
    """真上から見た円柱のマスク面積 = πr²/画素実寸²(1% 以内)。"""
    cam = _cam(resolution=(240, 240))
    cyl = OS.scene_cylinder((0.0, 0.0, 4.0), 8.0, 4.0)
    m = OS.optscene_mask([cyl], cam, 0)
    mm_px = cam["pixel_mm"] * (300.0 - 8.0) / cam["focal_mm"]
    assert int(m.sum()) == pytest.approx(np.pi * 8.0 ** 2 / mm_px ** 2, rel=0.01)


def test_backlight_silhouette_is_exactly_dark_and_the_area_is_closed_form():
    """透過照明: 部品はちょうど 0、背景は光源。面積は πr² と 1% 以内で一致。"""
    cam = _cam(resolution=(200, 200))
    cyl = OS.scene_cylinder((0.0, 0.0, 4.0), 8.0, 4.0, OS.scene_material("lambert", 0.5))
    bl = illumdesign.light_source(kind="backlight", radius_mm=40.0, height_mm=60.0, n=40)
    img = OS.render_optscene([cyl], cam, [bl]).mean(-1)
    m = OS.optscene_mask([cyl], cam, 0)
    assert img[m].max() == 0.0                      # 上から当たる光が無い = 真っ黒
    assert img[~m].mean() > 0.0
    mm_px = cam["pixel_mm"] * (300.0 - 8.0) / cam["focal_mm"]
    assert int(m.sum()) == pytest.approx(np.pi * 64.0 / mm_px ** 2, rel=0.01)


# --------------------------------------------------------------------------- #
# CSG(中空の部品)
# --------------------------------------------------------------------------- #
def _cup(coincident_rim):
    """コップ: 外径 20 / 高さ 30 / 内径 17 / 底 6 mm。口が外筒上面と一致する版も作る。"""
    outer = OS.scene_cylinder((0.0, 0.0, 15.0), 10.0, 15.0)
    top = 15.0 if coincident_rim else 16.0          # 一致 / わずかに突き出す
    inner = OS.scene_cylinder((0.0, 0.0, 6.0 + top), 8.5, top)
    return OS.scene_difference(outer, inner)


@pytest.mark.parametrize("coincident", [True, False])
def test_csg_cup_is_actually_hollow(coincident):
    """同一平面の面(口が外筒の上面とちょうど同じ高さ)でも穴が塞がらない。

    塞がるのが CSG の古典的な罠で、塞がったまま画像を作ると「コップの中の異物」を
    永久に生成できない ―― 見た目は正しいのでレビューでも気づけない。
    """
    cam = _cam(resolution=(240, 240))
    cup = _cup(coincident)
    d = OS.optscene_depth([cup], cam)
    # 光軸方向の z なので、縁も底も高さだけで決まる(斜距離だとここが視野端でずれる)
    assert np.nanmin(d) == pytest.approx(300.0 - 30.0, abs=1e-6)     # 縁
    assert np.nanmax(d) == pytest.approx(300.0 - 6.0, abs=1e-6)      # 底
    inner = np.isfinite(d) & (d > 300.0 - 30.0 + 20.0)
    assert inner.sum() > 0.3 * OS.optscene_mask([cup], cam, 0).sum()


def test_csg_outer_silhouette_is_unchanged_by_the_cavity():
    cam = _cam(resolution=(240, 240))
    solid = OS.scene_cylinder((0.0, 0.0, 15.0), 10.0, 15.0)
    a = OS.optscene_mask([solid], cam, 0).sum()
    b = OS.optscene_mask([_cup(False)], cam, 0).sum()
    assert int(a) == int(b)


def test_csg_rejects_a_plane_because_it_encloses_no_volume():
    with pytest.raises(ValueError, match="encloses no volume"):
        OS.scene_difference(OS.scene_plane(0.0), OS.scene_sphere((0, 0, 1), 1.0))


# --------------------------------------------------------------------------- #
# 測光(閉じた式)
# --------------------------------------------------------------------------- #
def test_lambert_radiance_matches_the_closed_form():
    """1 点光源 + 完全拡散面: L = a/π · I·cos^c(θ_s)·cos(θ_r)/r²(厳密一致)。"""
    cam = _cam(resolution=(9, 9))
    albedo, h, inten, cexp = 0.42, 120.0, 3.0, 2.0
    plane = OS.scene_plane(0.0, OS.scene_material("lambert", albedo))
    light = _point_light((0.0, 0.0, h), intensity=inten, cos_exponent=cexp)
    img = OS.render_optscene([plane], cam, [light], shadows=False)

    o, d = OS.camera_rays(cam)
    p = OS.trace_rays([plane], o, d)["point"]
    r = np.linalg.norm(np.array([0.0, 0.0, h]) - p, axis=1)
    cos = h / r
    want = albedo / np.pi * inten * cos ** cexp * cos / r ** 2
    assert np.allclose(img.reshape(-1, 3)[:, 0], want, rtol=1e-12)


def test_illumination_visibility_is_zero_in_the_shadow_and_one_outside():
    sph = OS.scene_sphere((0.0, 0.0, 10.0), 4.0)
    light = _point_light((0.0, 0.0, 120.0))
    below = np.array([[0.0, 0.0, 0.0]])
    beside = np.array([[40.0, 0.0, 0.0]])
    assert OS.illumination_visibility([sph], below, light)[0] == 0.0
    assert OS.illumination_visibility([sph], beside, light)[0] == 1.0


def test_all_zero_render_is_refused_instead_of_returned():
    """真っ黒を黙って返さない(後段が「検出ゼロ = 頑健」と誤読するため)。"""
    cam = _cam(resolution=(32, 32))
    scene = [OS.scene_cylinder((0.0, 0.0, 4.0), 8.0, 4.0), OS.scene_plane(0.0)]
    bl = illumdesign.light_source(kind="backlight", radius_mm=40.0, height_mm=60.0, n=16)
    with pytest.raises(ValueError, match="all-zero image"):
        OS.render_optscene(scene, cam, [bl])


# --------------------------------------------------------------------------- #
# 欠陥(外観検査の学習データ)
# --------------------------------------------------------------------------- #
def _scratched(height_um=25.0):
    """色は一切変わらず、深さだけがある傷(地形欠陥)。"""
    img = np.zeros((128, 128))
    mask = np.zeros((128, 128), bool)
    mask[60:66, 20:108] = True
    height = np.where(mask, -1.0, 0.0)
    disc = OS.scene_cylinder((0.0, 0.0, 2.0), 9.0, 2.0, OS.scene_material("lambert", 0.55))
    return OS.surface_defect(disc, img, mask, uv_size_mm=(18.0, 18.0),
                             height_um=height_um, height_field=height)


def _contrast(part, cam, light):
    img = OS.render_optscene([part], cam, [light]).mean(-1)
    lab = OS.optscene_defect_mask([part], cam)
    good = OS.optscene_mask([part], cam, 0) & ~lab
    return abs(float(img[lab].mean() - img[good].mean())) / max(float(img[good].mean()), 1e-30)


def test_topographic_defect_needs_dark_field_illumination():
    """凹凸だけの欠陥はドーム照明で消え、低角(暗視野)で立つ。

    これが照明を選ぶ理由そのもので、この差が出ない生成器で学習させても、実機で
    照明を変えた瞬間に破綻する。
    """
    cam = _cam(resolution=(200, 200))
    part = _scratched()
    dome = illumdesign.light_source(kind="dome", radius_mm=70.0, height_mm=70.0, n=96)
    dark = illumdesign.light_source(kind="ring", radius_mm=90.0, height_mm=6.0, n=64)
    assert _contrast(part, cam, dark) > 10.0 * _contrast(part, cam, dome)


def test_defect_label_does_not_depend_on_whether_it_is_visible():
    """見えない照明でも真値は同じ画素数(「見えない = 欠陥が無い」にしない)。"""
    cam = _cam(resolution=(200, 200))
    part = _scratched()
    a = OS.optscene_defect_mask([part], cam)
    assert a.sum() > 0
    assert int(a.sum()) == int(OS.optscene_defect_mask([part], cam, 0).sum())


def test_defect_height_zero_leaves_the_surface_untouched():
    cam = _cam(resolution=(64, 64))
    light = illumdesign.light_source(kind="dome", radius_mm=70.0, height_mm=70.0, n=32)
    flat = OS.scene_cylinder((0.0, 0.0, 2.0), 9.0, 2.0, OS.scene_material("lambert", 0.55))
    same = OS.surface_defect(flat, np.zeros((64, 64)), np.zeros((64, 64), bool),
                             uv_size_mm=(18.0, 18.0), height_um=0.0)
    assert np.allclose(OS.render_optscene([flat], cam, [light]),
                       OS.render_optscene([same], cam, [light]), atol=1e-15)


def test_surface_defect_refuses_a_shape_it_cannot_unwrap():
    cup = _cup(False)
    with pytest.raises(ValueError, match="no unambiguous surface parameterisation"):
        OS.surface_defect(cup, np.zeros((8, 8)))


def test_surface_defect_does_not_mutate_the_original_primitive():
    disc = OS.scene_cylinder((0.0, 0.0, 2.0), 9.0, 2.0)
    OS.surface_defect(disc, np.zeros((8, 8)))
    assert "defect" not in disc


# --------------------------------------------------------------------------- #
# センサ
# --------------------------------------------------------------------------- #
def test_sensor_capture_saturates_without_wrapping():
    out = OS.sensor_capture(np.full((4, 4), 1e6), full_well_e=1e4, bit_depth=8,
                            read_noise_e=0.0, seed=0)
    assert out.max() == 255 and out.min() == 255       # 白飛びは白のまま(折り返さない)


def test_sensor_capture_is_deterministic_for_a_fixed_seed():
    r = np.full((8, 8), 0.05)
    assert np.array_equal(OS.sensor_capture(r, seed=3), OS.sensor_capture(r, seed=3))
    assert not np.array_equal(OS.sensor_capture(r, seed=3), OS.sensor_capture(r, seed=4))


def test_sensor_shot_noise_variance_tracks_the_mean():
    """ショット雑音は Poisson: 電子数の分散 = 平均(±5%、10⁵ 標本)。"""
    r = np.full(100000, 4.0e-3)
    e = OS.sensor_capture(r, exposure_ms=10.0, gain_e_per_unit=5.0e4, read_noise_e=0.0,
                          full_well_e=1e9, bit_depth=16, seed=1).astype(float)
    scale = 1e9 / (2 ** 16 - 1)                        # 量子化の刻み [e-]
    assert (e.var() * scale ** 2) == pytest.approx(e.mean() * scale, rel=0.05)


def test_sensor_capture_rejects_negative_radiance():
    with pytest.raises(ValueError, match="non-negative"):
        OS.sensor_capture(np.array([-1.0, 0.0]))


# --------------------------------------------------------------------------- #
# データセット
# --------------------------------------------------------------------------- #
def test_inspection_dataset_is_deterministic_and_carries_its_labels():
    cam = _cam(resolution=(48, 48))
    part = _scratched()
    lights = [illumdesign.light_source(kind=k, radius_mm=80.0, height_mm=20.0, n=24)
              for k in ("ring", "dome")]
    a = OS.inspection_dataset([part], cam, lights, n=4, seed=5, jitter_mm=1.5,
                              intensity_jitter=0.2)
    b = OS.inspection_dataset([part], cam, lights, n=4, seed=5, jitter_mm=1.5,
                              intensity_jitter=0.2)
    assert len(a) == 4
    for x, y in zip(a, b):
        assert np.array_equal(x["image"], y["image"])
        assert set(x) == {"image", "defect_mask", "part_mask", "depth_mm", "meta"}
        assert x["defect_mask"].shape == x["part_mask"].shape == (48, 48)
    assert {x["meta"]["light"] for x in a} == {"ring", "dome"}       # 照明を巡回している


def test_inspection_dataset_moves_the_part_between_frames():
    cam = _cam(resolution=(64, 64))
    part = OS.scene_cylinder((0.0, 0.0, 4.0), 6.0, 4.0, OS.scene_material("lambert", 0.5))
    light = illumdesign.light_source(kind="dome", radius_mm=70.0, height_mm=70.0, n=24)
    ds = OS.inspection_dataset([part], cam, [light], n=3, seed=2, jitter_mm=3.0)
    centres = [np.argwhere(d["part_mask"]).mean(0) for d in ds]
    assert np.abs(np.diff(np.stack(centres), axis=0)).max() > 1.0


# --------------------------------------------------------------------------- #
# 見せる絵(別経路)
# --------------------------------------------------------------------------- #
def test_env_studio_is_brightest_towards_the_key_light():
    key = np.array([[np.sin(-0.85) * np.cos(0.66), np.cos(-0.85) * np.cos(0.66), np.sin(0.66)]])
    down = np.array([[0.0, 0.0, -1.0]])
    assert OS.env_studio(key)[0] > 10.0 * OS.env_studio(down)[0]


def test_render_studio_gets_metal_colour_from_the_fresnel_data_alone():
    """環境は無彩色なのに金は R>G>B、銀はほぼ中性 ―― 色は n,k からしか来ていない。"""
    cam = _cam(resolution=(48, 48), tilt_deg=35.0)
    def one(metal):
        obj = OS.scene_sphere((0.0, 0.0, 6.0), 6.0,
                              OS.scene_material("conductor", metal=metal, finish="random"))
        img = OS.render_studio([obj], cam, depth=2, samples=8).reshape(-1, 3)
        return img[img.sum(1).argmax()]
    au, ag = one("au"), one("ag")
    assert au[0] > au[1] > au[2]
    assert float(np.ptp(ag / max(ag.max(), 1e-12))) < 0.12


def test_render_studio_and_render_optscene_are_different_by_construction():
    """同じシーンでも別物(片方は環境光、片方は実在の照明器具)。取り違えを検出する。"""
    cam = _cam(resolution=(32, 32), tilt_deg=30.0)
    scene = [OS.scene_plane(0.0, OS.scene_material("lambert", 0.4)),
             OS.scene_sphere((0.0, 0.0, 6.0), 6.0, OS.scene_material("lambert", 0.6))]
    light = illumdesign.light_source(kind="dome", radius_mm=80.0, height_mm=80.0, n=32)
    a = OS.render_optscene(scene, cam, [light])
    b = OS.render_studio(scene, cam, depth=2, samples=8)
    assert a.shape == b.shape
    assert not np.allclose(a / max(a.max(), 1e-12), b / max(b.max(), 1e-12), atol=1e-3)


# --------------------------------------------------------------------------- #
# fail-closed
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("call, match", [
    (lambda: OS.scene_material("plastic"), "kind must be one of"),
    (lambda: OS.scene_material("lambert", albedo=1.4), r"\[0, 1\]"),
    (lambda: OS.scene_material("conductor", metal="unobtainium"), "metal must be one of"),
    (lambda: OS.scene_material("conductor", finish="wobbly"), "finish must be one of"),
    (lambda: OS.scene_material("dielectric", sigma_per_mm=-1.0), "sigma_per_mm"),
    (lambda: OS.scene_sphere((0, 0, 1), -2.0), "radius_mm"),
    (lambda: OS.scene_cylinder((0, 0, 1), 2.0, 0.0), "half_height_mm"),
    (lambda: OS.optical_camera(tilt_deg=95.0), "tilt_deg"),
    (lambda: OS.optical_camera(focal_mm=0.0), "focal_mm"),
    (lambda: OS.trace_rays([], np.zeros((1, 3)), np.ones((1, 3))), "at least one primitive"),
])
def test_invalid_input_is_refused(call, match):
    with pytest.raises(ValueError, match=match):
        call()


def test_render_requires_a_real_light_source():
    with pytest.raises(ValueError, match="illumdesign.light_source"):
        OS.render_optscene([OS.scene_plane(0.0)], _cam(resolution=(8, 8)), [{"kind": "ring"}])


# --------------------------------------------------------------------------- #
# 加工目(欠陥ではない)
# --------------------------------------------------------------------------- #
def _disc(finish=None, **kw):
    d = OS.scene_cylinder((0.0, 0.0, 3.0), 9.0, 3.0, OS.scene_material("lambert", 0.55))
    return d if finish is None else OS.surface_finish(d, kind=finish, uv_size_mm=(18.0, 18.0), **kw)


def test_machining_marks_are_never_labelled_as_defects():
    """加工目は良品にも必ずある。ラベルに混ざったらデータが壊れる。"""
    cam = _cam(resolution=(96, 96))
    part = _disc("turned", pitch_um=320.0, depth_um=2.0)
    assert OS.optscene_defect_mask([part], cam).sum() == 0


def test_machining_marks_change_the_image_under_low_angle_light():
    cam = _cam(resolution=(96, 96))
    dark = illumdesign.light_source(kind="ring", radius_mm=95.0, height_mm=7.0, n=48)
    plain = OS.render_optscene([_disc()], cam, [dark])
    turned = OS.render_optscene([_disc("turned", pitch_um=320.0, depth_um=2.0)], cam, [dark])
    m = OS.optscene_mask([_disc()], cam, 0)
    assert turned[m].std() > 5.0 * max(plain[m].std(), 1e-12)


def test_marks_finer_than_a_pixel_are_flattened_not_aliased():
    """画素より細かい目は「構造」ではなく「平坦」になる(モアレの偽構造を作らない)。

    画素は面積を積分する箱フィルタなので、周期が画素幅に近づくと振幅は sinc で 0 に
    落ちる。これが無いと、生成画像に実在しない模様が入りモデルがそれを覚える
    (2026-09-05 の実測: 旋盤目 120 µm / 画素 82 µm で放射状の花が出た)。
    """
    cam = _cam(resolution=(96, 96))
    dark = illumdesign.light_source(kind="ring", radius_mm=95.0, height_mm=7.0, n=48)
    m = OS.optscene_mask([_disc()], cam, 0)
    coarse = OS.render_optscene([_disc("turned", pitch_um=600.0, depth_um=2.0)], cam, [dark])
    fine = OS.render_optscene([_disc("turned", pitch_um=8.0, depth_um=2.0)], cam, [dark])
    assert fine[m].std() < 0.05 * coarse[m].std()


def test_surface_finish_rejects_an_unknown_kind_and_keeps_the_original():
    with pytest.raises(ValueError, match="kind must be one of"):
        OS.surface_finish(_disc(), kind="sandblasted-ish")
    d = _disc()
    OS.surface_finish(d, kind="turned")
    assert "texture" not in d


# --------------------------------------------------------------------------- #
# ランダム欠陥
# --------------------------------------------------------------------------- #
def test_random_defects_is_deterministic_and_labels_everything_it_made():
    a = OS.random_defects(_disc(), count=4, seed=9, uv_size_mm=(18.0, 18.0))
    b = OS.random_defects(_disc(), count=4, seed=9, uv_size_mm=(18.0, 18.0))
    assert [x["kind"] for x in a["labels"]] == [x["kind"] for x in b["labels"]]
    assert len(a["labels"]) == 4
    # 異物は別の物体として置かれ、その物体もラベルに入る(取りこぼすと学習データが嘘になる)
    assert len(a["objects"]) == sum(1 for x in a["labels"] if x["kind"] == "foreign")


def test_foreign_objects_are_marked_as_defects_in_the_ground_truth():
    cam = _cam(resolution=(140, 140))
    made = OS.random_defects(_disc(), count=1, kinds=("foreign",), seed=4,
                             uv_size_mm=(18.0, 18.0))
    scene = [made["part"]] + made["objects"]
    assert made["objects"] and OS.optscene_defect_mask(scene, cam).sum() > 0


def test_count_zero_produces_a_good_part_with_no_labels():
    cam = _cam(resolution=(96, 96))
    made = OS.random_defects(_disc(), count=0, seed=0, uv_size_mm=(18.0, 18.0))
    assert made["labels"] == [] and made["objects"] == []
    assert OS.optscene_defect_mask([made["part"]], cam).sum() == 0


def test_topographic_only_defects_do_not_touch_the_albedo():
    """albedo_defects=False は**色を一切変えない**(凹凸だけ)。"""
    cam = _cam(resolution=(96, 96))
    flat = illumdesign.light_source(kind="dome", radius_mm=85.0, height_mm=70.0, n=48)
    made = OS.random_defects(_disc(), count=2, kinds=("scratch", "pits"), seed=6,
                             uv_size_mm=(18.0, 18.0), albedo_defects=False)
    img = OS.render_optscene([made["part"]], cam, [flat]).mean(-1)
    lab = OS.optscene_defect_mask([made["part"]], cam)
    good = OS.optscene_mask([made["part"]], cam, 0) & ~lab
    assert lab.any()
    rel = abs(float(img[lab].mean() - img[good].mean())) / max(float(img[good].mean()), 1e-30)
    assert rel < 0.02                                   # 拡散照明では見えない = 色は変えていない


def test_random_defects_rejects_an_unknown_kind():
    with pytest.raises(ValueError, match="kinds must be a subset"):
        OS.random_defects(_disc(), count=1, kinds=("rust-ish",))


# --------------------------------------------------------------------------- #
# スループット(大量生成が通常運用なので実測を残す)
# --------------------------------------------------------------------------- #
def test_dataset_throughput_reports_measured_timings():
    cam = _cam(resolution=(48, 48))
    light = illumdesign.light_source(kind="dome", radius_mm=80.0, height_mm=70.0, n=24)
    ds = OS.inspection_dataset([_disc()], cam, [light], n=3, seed=1)
    tp = OS.dataset_throughput(ds)
    assert tp["images"] == 3
    assert tp["seconds_per_image"] > 0.0 and tp["images_per_hour"] > 0.0
    assert 0.0 < tp["render_fraction"] <= 1.0
    assert tp["pixels_per_second"] == pytest.approx(48 * 48 * 3 / tp["seconds_total"], rel=1e-9)


def test_dataset_throughput_refuses_rows_without_measurements():
    """推定値を混ぜない(「速い」の根拠が消えるため)。"""
    with pytest.raises(ValueError, match="inspection_dataset"):
        OS.dataset_throughput([{"meta": {"light": "dome"}}])
    with pytest.raises(ValueError, match="empty"):
        OS.dataset_throughput([])


# --------------------------------------------------------------------------- #
# 加工目に学習可能な規則性が無いこと(2026-09-05 のユーザー基準)
# --------------------------------------------------------------------------- #
def _periodicity(sig):
    """周期性の 2 指標: (帯域内での尖り, 自己相関が一度落ちてから戻る度合い)。

    小ラグの自己相関は**滑らかなだけで 1 に近づく**ので、そこを見てはいけない。
    帯域制限した雑音でも 0.99 になる(2026-09-05 に実測して交絡が判明)。周期性は
    「相関が一度 0.2 を割ったあとに戻ってくるか」で見る。純正弦は 0.999、
    正弦 4 本の和は 0.873、帯域制限した白色雑音は 0.302。
    """
    a = np.asarray(sig, float)
    a = (a - a.mean()) * np.hanning(len(a))
    F = np.abs(np.fft.rfft(a)) ** 2
    F[0:3] = 0.0
    band = F[F > 0.01 * F.max()]
    spike = float(F.max() / max(band.mean(), 1e-30))
    ac = np.fft.irfft(F)
    ac = ac / max(ac[0], 1e-30)
    n = len(ac) // 2
    below = np.nonzero(ac[:n] < 0.2)[0]
    return spike, (1.0 if len(below) == 0 else float(np.abs(ac[below[0]:n]).max()))


def _slope_profile(kind, pitch_um, n=4000, span_mm=10.0):
    """加工目の傾きを直交方向に 1 次元で取り出す(照明も形状も混ぜない生の profile)。"""
    part = OS.surface_finish(OS.scene_box((0.0, 0.0, 2.5), (20.0, 20.0, 2.5)),
                             kind=kind, pitch_um=pitch_um, depth_um=0.9,
                             uv_size_mm=(42.0, 42.0), seed=3)
    v = np.linspace(-span_mm / 2, span_mm / 2, n)
    u = np.zeros_like(v)
    tu = np.tile([1.0, 0.0, 0.0], (n, 1))
    tv = np.tile([0.0, 1.0, 0.0], (n, 1))
    return OS._analytic_tilt(part["texture"], u, v, tu, tv, None)[:, 1]


def test_the_periodicity_metric_separates_a_sine_from_noise():
    """指標そのものの健全性(零点を先に固定する)。"""
    x = np.linspace(0.0, 40.0, 4000)
    assert _periodicity(np.sin(2 * np.pi * x / 0.9))[1] > 0.95        # 純正弦
    four = sum(np.sin(2 * np.pi * x / p + q) for p, q in
               ((0.9, 0.0), (0.41, 1.0), (0.19, 2.0), (2.1, 3.0)))
    assert _periodicity(four)[1] > 0.7                                # 正弦の和も周期的
    k = np.exp(-0.5 * (np.arange(-100, 101) / 12.0) ** 2)
    noise = np.convolve(np.random.default_rng(0).normal(size=4200), k, "valid")[:4000]
    assert _periodicity(noise)[1] < 0.5                               # 帯域制限した雑音


@pytest.mark.parametrize("pitch_um", [60.0, 120.0, 320.0])
def test_machining_marks_carry_no_learnable_periodicity(pitch_um):
    """加工目に**学習できる周期**が残っていないこと。

    ユーザー基準(2026-09-05)「AI にヘアラインの法則性を読まれるレベルだとまだダメ」。
    合成テクスチャに周期が残ると、モデルはそれを近道の手掛かりに使い、実機の
    加工面では働かない。正弦の和(0.873)では落ち、勾配ノイズ(0.188)なら通る。
    """
    assert _periodicity(_slope_profile("hairline", pitch_um))[1] < 0.5


def test_machining_marks_do_not_repeat_across_seeds():
    """seed を変えたら別の面になる(同じ模様を量産しない)。"""
    a = _slope_profile("hairline", 90.0)
    part = OS.surface_finish(OS.scene_box((0.0, 0.0, 2.5), (20.0, 20.0, 2.5)),
                             kind="hairline", pitch_um=90.0, depth_um=0.9,
                             uv_size_mm=(42.0, 42.0), seed=99)
    v = np.linspace(-5.0, 5.0, 4000)
    u = np.zeros_like(v)
    b = OS._analytic_tilt(part["texture"], u, v,
                          np.tile([1.0, 0.0, 0.0], (4000, 1)),
                          np.tile([0.0, 1.0, 0.0], (4000, 1)), None)[:, 1]
    corr = float(np.corrcoef(a, b)[0, 1])
    assert abs(corr) < 0.2, f"seed を変えても相関 {corr:.3f} = ほぼ同じ面"


def test_lightbox_environment_is_bright_but_not_flat():
    """加工面が加工面に見える 2 条件: 周囲が明るい / それでも勾配がある。"""
    # 明かりは天頂ではなく仰角 0.85 rad(既定)に置いてある ―― 天頂を測ると外れる
    key = np.array([[0.0, np.cos(0.85), np.sin(0.85)]])
    side = np.array([[0.0, 1.0, 0.0]])
    down = np.array([[0.0, 0.0, -1.0]])
    a, b, c = (float(OS.env_lightbox(x)[0]) for x in (key, side, down))
    assert b > 0.3 and c > 0.3          # 暗い環境ではアルミが黒く写ってしまう
    assert a > 2.0 * b                  # 一様だと異方性ローブの差が出ない
    # env_studio は劇的に見せる側(暗い周囲)。1 方向で比べると補助灯に当たって
    # 逆転するので、球面平均で比べる(周囲が明るいかどうかが違いの本体)
    rng = np.random.default_rng(0)
    dirs = rng.normal(size=(4000, 3))
    dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    # 平均は studio のソフトボックスの尖りに引っ張られるので中央値で比べる
    assert np.median(OS.env_lightbox(dirs)) > 3.0 * np.median(OS.env_studio(dirs))


def test_brushed_metal_needs_an_oblique_view_to_show_its_grain():
    """真上から見た平面は反射方向が天頂に集中し、加工目が出ない(斜めが要る)。"""
    plate = OS.surface_finish(
        OS.scene_box((0.0, 0.0, 2.5), (20.0, 20.0, 2.5),
                     OS.scene_material("conductor", metal="al", finish="linear")),
        kind="hairline", pitch_um=90.0, depth_um=1.0, uv_size_mm=(42.0, 42.0), seed=3)
    light = illumdesign.light_source(kind="ring", radius_mm=70.0, height_mm=90.0, n=24)
    grain = []
    for tilt in (2.0, 55.0):
        cam = _cam(resolution=(96, 96), focal_mm=12.0, working_distance_mm=260.0,
                   tilt_deg=tilt)
        im = OS.render_optscene([plate], cam, [light], depth=1,
                                environment=OS.env_lightbox).mean(-1)
        grain.append(float(np.abs(np.diff(im, axis=1)).mean() / max(im.mean(), 1e-30)))
    assert grain[1] > 3.0 * grain[0]


# --------------------------------------------------------------------------- #
# 明視野 / 暗視野のコントラスト反転
# --------------------------------------------------------------------------- #
def test_bright_and_dark_field_invert_the_defect_contrast():
    """傷は**明視野で暗く、暗視野で明るく**写る(教科書どおりの反転)。

    鏡面だけのモデルでは暗視野は原理的に成立しない ―― 低角 12 度の照明を真上の
    カメラへ返すには面法線が 39 度傾く必要があり、傷の傾斜(5-15 度)では届かない。
    実際の暗視野が光るのは、傷が材料を削り取った跡で**局所的に粗く、散乱で返す**
    から。だから欠陥は法線だけでなく粗さも上げる必要がある(2026-09-05)。
    """
    base = OS.surface_finish(
        OS.scene_box((0.0, 0.0, 2.5), (20.0, 20.0, 2.5),
                     OS.scene_material("conductor", metal="al", finish="linear",
                                       roughness_um=0.03)),
        kind="hairline", pitch_um=90.0, depth_um=0.6, uv_size_mm=(42.0, 42.0), seed=3)
    part = OS.random_defects(base, count=1, kinds=("scratch",), seed=21,
                             uv_size_mm=(42.0, 42.0), height_um=(20.0, 40.0),
                             albedo_defects=False, defect_roughness_um=0.4)["part"]
    cam = _cam(resolution=(140, 140), focal_mm=12.0, working_distance_mm=260.0)
    lab = OS.optscene_defect_mask([part], cam)
    good = OS.optscene_mask([part], cam, 0) & ~lab
    assert lab.any()

    bright = illumdesign.light_source(kind="coaxial", radius_mm=70.0, height_mm=140.0, n=128)
    bright["size_mm"] = 25.0                       # 器具の実体。点近似だと鏡像が細すぎる
    dark = illumdesign.light_source(kind="ring", radius_mm=95.0, height_mm=20.0, n=96)
    dark["size_mm"] = 25.0
    out = []
    for light in (bright, dark):
        im = OS.render_optscene([part], cam, [light], depth=1).mean(-1)
        out.append(float(im[lab].mean() - im[good].mean()) / max(float(im[good].mean()), 1e-30))
    assert out[0] < -0.1, f"明視野で傷が暗くならない: {out[0]:+.3f}"
    assert out[1] > +0.1, f"暗視野で傷が明るくならない: {out[1]:+.3f}"


def test_defect_roughness_is_what_creates_the_inversion():
    """粗さを 0 にすると反転がほぼ消える(法線の傾きだけでは足りない)。"""
    def contrast(rq, light):
        # 加工目のある面で比べる。完全鏡面だと暗視野では背景も欠陥も光らず、
        # 「粗さの効果」ではなく「どちらも真っ暗」を測ってしまう
        base = OS.surface_finish(
            OS.scene_box((0.0, 0.0, 2.5), (20.0, 20.0, 2.5),
                         OS.scene_material("conductor", metal="al", finish="linear",
                                           roughness_um=0.03)),
            kind="hairline", pitch_um=90.0, depth_um=0.6, uv_size_mm=(42.0, 42.0), seed=3)
        part = OS.random_defects(base, count=1, kinds=("scratch",), seed=21,
                                 uv_size_mm=(42.0, 42.0), height_um=(20.0, 40.0),
                                 albedo_defects=False, defect_roughness_um=rq)["part"]
        cam = _cam(resolution=(120, 120), focal_mm=12.0, working_distance_mm=260.0)
        lab = OS.optscene_defect_mask([part], cam)
        good = OS.optscene_mask([part], cam, 0) & ~lab
        im = OS.render_optscene([part], cam, [light], depth=1).mean(-1)
        return float(im[lab].mean() - im[good].mean()) / max(float(im[good].mean()), 1e-30)
    dark = illumdesign.light_source(kind="ring", radius_mm=95.0, height_mm=20.0, n=96)
    dark["size_mm"] = 25.0
    # 主張は「粗さを上げると暗視野のコントラストが上がる」という向きだけ。
    # 倍率まで固定すると、加工目の強さや照明の置き方で簡単に破れる
    weak, strong = contrast(0.0, dark), contrast(0.4, dark)
    assert strong > weak, f"粗さ 0 で {weak:+.3f} / 0.4 で {strong:+.3f}"


# --------------------------------------------------------------------------- #
# 型番でスペックを引く
# --------------------------------------------------------------------------- #
def test_specs_load_by_model_number():
    """メーカー・型番を指定すれば、カメラとレンズのオブジェクトが 1 行で組める。"""
    sen = OS.sensor_spec(model="IMX264")
    assert (sen["width"], sen["height"]) == (2448, 2048)
    assert sen["pixel_um"] == 3.45 and sen["noise_values_are"].startswith("EMVA1288")
    lens = OS.lens_spec(model="HF25XA-1", maker="Fujinon", working_distance_mm=250.0)
    assert lens["focal_mm"] == 25.0 and lens["f_number"] == 1.8      # 省略時は開放
    assert lens["image_circle_mm"] == 11.0                           # 2/3"
    lay = OS.vision_layout(sen, lens, [OS.light_spec(kind="coaxial")])
    assert lay["budget"]["magnification"] > 0.0


def test_image_circle_must_cover_the_sensor_diagonal():
    """覆えないと四隅が黒く落ちる。形式名でなく実寸で比べる。"""
    lens = OS.lens_spec(model="Fujinon HF25XA-1")                   # 2/3" = 11.0 mm
    assert OS.covers_sensor(lens, OS.sensor_spec(model="IMX264"))["covers"]      # 対角 11.0
    big = OS.covers_sensor(lens, OS.sensor_spec(model="IMX541"))     # 対角 17.5
    assert not big["covers"] and big["margin_mm"] < -5.0


def test_catalogs_filter_by_maker_and_unknown_models_are_refused():
    assert set(OS.lens_catalog(maker="Ricoh")) == {
        "Ricoh FL-CC0814A-2M", "Ricoh FL-CC1214A-2M",
        "Ricoh FL-CC1614-5M", "Ricoh FL-CC3516-2M"}
    assert all(v["maker"] == "Gpixel" for v in OS.sensor_catalog(maker="Gpixel").values())
    with pytest.raises(ValueError, match="unknown lens model"):
        OS.lens_spec(model="NOT-A-LENS")
    with pytest.raises(ValueError, match="unknown sensor model"):
        OS.sensor_spec(model="IMX9999")


def test_lighting_identity_needs_the_maker_because_of_oem_relabelling():
    """照明は OEM 供給が多く、同じ型番が別ブランドで出る。型番だけでは一意にならない。"""
    a = OS.register_light("TestBrandA", "XX-100", kind="ring", radius_mm=45.0,
                          height_mm=60.0, size_mm=20.0)
    b = OS.register_light("TestBrandB", "XX-100", kind="ring", radius_mm=45.0,
                          height_mm=60.0, size_mm=20.0, oem_of=a)
    assert OS.light_catalog()[b]["oem_of"] == a          # 来歴が辿れる
    with pytest.raises(ValueError, match="ambiguous across makers"):
        OS.light_spec(model="XX-100")
    assert OS.light_spec(model="XX-100", maker="TestBrandA")["model"] == a
    with pytest.raises(ValueError, match="both maker and model are required"):
        OS.register_light("", "XX-100")


def test_light_catalog_ships_no_invented_vendor_specs():
    """既定は一般形状のみ。配光・波長・実体寸法はデータシートにしかないので捏造しない。"""
    assert all(v["maker"] == "generic" for k, v in OS.light_catalog().items()
               if not k.startswith("TestBrand") and not k.startswith("CCS")
               and not k.startswith("OtherBrand"))
