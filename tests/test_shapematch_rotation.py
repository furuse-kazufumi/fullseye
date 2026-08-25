"""回転探索の回帰テスト。

この回で直したこと: find_shape_model は角度 0 固定で、HALCON が返す Angle を
一切見ていなかった。回転物体は score が 0.997(0度)から 0.25(60度)へ落ちて
取り逃していた。修正 = **テンプレートを回してモデルを作り直す**(rotate_model)。
回転で点の座標だけでなく **エッジの法線(勾配)も回る** ので、点だけ回すのは誤り
(45度で 0.688 vs 作り直し 0.961)。各角度もピラミッドに乗る。
"""
import numpy as np
import pytest
from scipy import ndimage

import shapematch as S


def _L(n=48):
    """非対称な L 字(回転で向きが変わることが分かる形)。"""
    t = np.zeros((n, n))
    t[8:n - 8, 12:18] = 1.0
    t[n - 18:n - 12, 12:n - 8] = 1.0
    return ndimage.gaussian_filter(t, 1.0)


@pytest.fixture
def tpl():
    return _L()


def _scene(tpl, r, c, ang, seed=0, size=256):
    rng = np.random.default_rng(seed)
    img = rng.normal(0.5, 0.02, (size, size))
    t = ndimage.rotate(tpl, ang, reshape=False)
    h, w = t.shape
    img[r - h // 2:r - h // 2 + h, c - w // 2:c - w // 2 + w] += t
    return img


@pytest.mark.parametrize("true_ang", [0, 30, -45, 60, 90])
def test_rotation_search_recovers_the_angle(tpl, true_ang):
    m = S.create_shape_model(tpl)
    img = _scene(tpl, 130, 120, true_ang)
    r = S.find_shape_model(m, img, angles=range(-90, 91, 15))
    assert abs(r["row"] - 130) <= 3 and abs(r["col"] - 120) <= 3
    # 角度は 15 度刻みなので ±15 度以内で当てる
    diff = ((r["angle"] - true_ang + 180) % 360) - 180
    assert abs(diff) <= 15
    assert r["score"] > 0.9


def test_rotated_object_is_missed_without_angle_search(tpl):
    """角度探索を切ると回転物体を取り逃す = 穴が実在した証拠。"""
    m = S.create_shape_model(tpl)
    img = _scene(tpl, 130, 120, 60)
    r = S.find_shape_model(m, img)          # angles=None(従来)
    assert r["score"] < 0.5


def test_rebuild_beats_point_only_rotation(tpl):
    """テンプレを回して作り直す方が、点だけ回すより高いスコア(勾配も回るから)。"""
    m = S.create_shape_model(tpl)
    img = _scene(tpl, 128, 128, 45)
    # 点だけ回す(誤り): grad は据え置き
    th = np.deg2rad(45)
    R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    cen = np.array(m["shape"]) / 2
    pts = ((m["pts"] - cen) @ R.T + cen).round().astype(int)
    m_pts_only = {"shape": m["shape"], "pts": pts, "grad": m["grad"],
                  "min_contrast": m["min_contrast"], "metric": m["metric"]}
    s_pts = S.find_shape_model(m_pts_only, img, num_levels=0)["score"]
    # テンプレを回して作り直す(正しい)
    s_rebuild = S.find_shape_model(S.rotate_model(m, 45), img, num_levels=0)["score"]
    assert s_rebuild > s_pts + 0.15


def test_rotate_model_rebuilds_gradients(tpl):
    """rotate_model は template を持ち、角度を記録し、ピラミッドに乗れる。"""
    rm = S.rotate_model(S.create_shape_model(tpl), 30)
    assert rm["angle"] == 30
    assert rm["template"].shape == rm["shape"]
    assert len(S.build_model_pyramid(rm)) > 1


def test_angle_search_has_no_false_positive_on_noise(tpl):
    m = S.create_shape_model(tpl)
    rng = np.random.default_rng(9)
    noise = rng.normal(0.5, 0.15, (256, 256))
    r = S.find_shape_model(m, noise, angles=range(-90, 91, 15), min_score=0.5)
    assert not r["found"]
    assert r["score"] < 0.4


def test_transform_model_composes_rotation_and_scale(tpl):
    """transform_model は回転 + スケールをまとめてテンプレに施す。"""
    m = S.create_shape_model(tpl)
    img_big_rot = _scene(ndimage.zoom(tpl, 1.25, order=1), 128, 128, 30)
    tm = S.transform_model(m, angle=30, scale_row=1.25, scale_col=1.25)
    r = S.find_shape_model(tm, img_big_rot, num_levels=0)
    assert abs(r["row"] - 128) <= 3 and abs(r["col"] - 128) <= 3
    assert r["score"] > 0.85


def test_backward_compat_angle_key(tpl):
    """angles を渡さない従来呼び出しでも angle キーは 0.0 で入る。"""
    m = S.create_shape_model(tpl)
    r = S.find_shape_model(m, _scene(tpl, 130, 120, 0))
    assert r["angle"] == 0.0
    assert r["score"] > 0.9
