"""形状マッチングの GPU(conv2d 定式化)テスト。

この回で入れたこと: Steger 流の勾配方向スコアは「モデルを勾配カーネルに描いた
cross-correlation」= conv2d そのもの。変換(角度×スケール)をカーネルのバッチ軸に
積めば全変換を 2 回の conv2d で同時評価できる。実測 34-88x(docs/ARTICLE_GPU_SHAPEMATCH.md)。
※「HALCON が matching を GPU 化していない」は未検証の推測なので断定しない(§2 参照)。

CUDA GPU が無い環境では skip(CPU CI を壊さない)。
"""
import numpy as np
import pytest
from scipy import ndimage

import shapematch as S

try:
    import shapematch_gpu as G
    _GPU = G.gpu_available()
except Exception:
    _GPU = False

skip_gpu = pytest.mark.skipif(not _GPU, reason="CUDA GPU 不在")


def _L(n=48):
    t = np.zeros((n, n))
    t[8:n - 8, 12:18] = 1.0
    t[n - 18:n - 12, 12:n - 8] = 1.0
    return ndimage.gaussian_filter(t, 1.0)


def _scene(tpl, r, c, ang, scale=1.0, seed=0, size=256):
    rng = np.random.default_rng(seed)
    img = rng.normal(0.5, 0.02, (size, size))
    t = ndimage.rotate(tpl, ang, reshape=False)
    if scale != 1.0:
        t = ndimage.zoom(t, scale, order=1)
    h, w = t.shape
    img[r - h // 2:r - h // 2 + h, c - w // 2:c - w // 2 + w] += t
    return img


@skip_gpu
def test_score_map_matches_score_at_exactly():
    """mc=0・float64 なら conv 定式化は _score_at をビット一致で再現する。"""
    tpl = _L()
    m = S.create_shape_model(tpl)
    m["min_contrast"] = 0.0
    img = _scene(tpl, 130, 120, 0)
    sm = G.score_maps([m], img, metric="use_polarity", mc=0.0, dtype="float64")[0]
    gx = ndimage.sobel(img, axis=1)
    gy = ndimage.sobel(img, axis=0)
    mag = np.hypot(gx, gy)
    for (r, c) in [(130, 120), (100, 100), (130, 121), (90, 150)]:
        cpu = S._score_at(m, gy, gx, mag, r, c)
        assert abs(cpu - sm[r, c]) < 1e-9


@skip_gpu
@pytest.mark.parametrize("true_ang", [0, 30, -45, 60])
def test_gpu_rotation_matches_cpu_position(true_ang):
    tpl = _L()
    m = S.create_shape_model(tpl)
    img = _scene(tpl, 130, 120, true_ang)
    angles = range(-90, 91, 15)
    cpu = S.find_shape_model(m, img, angles=angles, device="cpu")
    gpu = S.find_shape_model(m, img, angles=angles, device="cuda")
    assert abs(gpu["row"] - cpu["row"]) <= 2
    assert abs(gpu["col"] - cpu["col"]) <= 2
    assert gpu["angle"] == cpu["angle"]
    assert gpu["score"] > 0.9


@skip_gpu
@pytest.mark.parametrize("true_s", [0.8, 1.0, 1.25])
def test_gpu_scale_matches_cpu(true_s):
    tpl = _L()
    m = S.create_shape_model(tpl)
    img = _scene(tpl, 128, 128, 0, scale=true_s)
    scales = (0.8, 1.0, 1.25, 1.5)
    cpu = S.find_scaled_shape_model(m, img, scales=scales, device="cpu")
    gpu = S.find_scaled_shape_model(m, img, scales=scales, device="cuda")
    assert abs(gpu["row"] - cpu["row"]) <= 2
    assert abs(gpu["col"] - cpu["col"]) <= 2
    assert gpu["scale"] == cpu["scale"]


@skip_gpu
def test_gpu_no_false_positive_on_noise():
    tpl = _L()
    m = S.create_shape_model(tpl)
    rng = np.random.default_rng(9)
    noise = rng.normal(0.5, 0.15, (256, 256))
    gpu = S.find_shape_model(m, noise, angles=range(-90, 91, 15),
                             min_score=0.5, device="cuda")
    assert not gpu["found"]
    assert gpu["score"] < 0.5


@skip_gpu
def test_ignore_local_metric_falls_back_to_cpu():
    """ignore_local_polarity は conv で表現できないので device=cuda でも CPU で回る。"""
    tpl = _L()
    m = S.create_shape_model(tpl, metric="ignore_local_polarity")
    img = _scene(tpl, 130, 120, 30)
    # 落ちずに結果が返れば OK(GPU 経路は None を返して CPU にフォールバック)
    r = S.find_shape_model(m, img, angles=range(-90, 91, 15), device="cuda")
    assert r["row"] > 0


@skip_gpu
def test_no_template_falls_back_to_cpu():
    tpl = _L()
    m = S.create_shape_model(tpl)
    m.pop("template", None)
    img = _scene(tpl, 130, 120, 0)
    r = S.find_shape_model(m, img, angles=range(-30, 31, 15), device="cuda")
    assert r["row"] > 0


def test_gpu_dispatch_is_silent_without_cuda():
    """CUDA が無い環境で device='cuda' を渡しても静かに CPU で動く(落ちない)。"""
    tpl = _L()
    m = S.create_shape_model(tpl)
    img = _scene(tpl, 130, 120, 0)
    r = S.find_shape_model(m, img, angles=range(-30, 31, 15), device="cuda")
    assert r["row"] > 0            # CUDA 有無どちらでも位置が返る


def _multi_scene(tpl, centers, size=384, seed=0):
    rng = np.random.default_rng(seed)
    img = rng.normal(0.5, 0.02, (size, size))
    h, w = tpl.shape
    for (r, c) in centers:
        img[r - h // 2:r - h // 2 + h, c - w // 2:c - w // 2 + w] += tpl
    return img


@skip_gpu
def test_gpu_multi_instance_matches_cpu():
    """複数インスタンス検出が CPU と同じ位置・個数を返す(スコアマップ GPU / NMS CPU)。"""
    tpl = _L(40)
    m = S.create_shape_model(tpl)
    centers = [(80, 90), (80, 220), (200, 150), (300, 300), (150, 320)]
    img = _multi_scene(tpl, centers)
    cpu = S.find_shape_models(m, img, min_score=0.5, max_matches=8,
                              min_distance=20, device="cpu")
    gpu = S.find_shape_models(m, img, min_score=0.5, max_matches=8,
                              min_distance=20, device="cuda")
    assert gpu["num"] == cpu["num"] == 5
    cs = sorted((x["row"], x["col"]) for x in cpu["matches"])
    gs = sorted((x["row"], x["col"]) for x in gpu["matches"])
    for (r, c), (r2, c2) in zip(cs, gs):
        assert abs(r - r2) <= 2 and abs(c - c2) <= 2


@skip_gpu
def test_gpu_multi_instance_no_false_positive_on_noise():
    tpl = _L(40)
    m = S.create_shape_model(tpl)
    rng = np.random.default_rng(3)
    noise = rng.normal(0.5, 0.15, (384, 384))
    gpu = S.find_shape_models(m, noise, min_score=0.5, max_matches=8,
                              min_distance=20, device="cuda")
    assert gpu["num"] == 0


def test_gpu_multi_instance_silent_fallback():
    """CUDA 無しでも device='cuda' で落ちず CPU で複数検出する。"""
    tpl = _L(40)
    m = S.create_shape_model(tpl)
    img = _multi_scene(tpl, [(80, 90), (200, 200)], size=320)
    r = S.find_shape_models(m, img, min_score=0.5, max_matches=4,
                            min_distance=20, device="cuda")
    assert r["num"] == 2
