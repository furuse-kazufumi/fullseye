"""find_shape_model のピラミッドサーチ(粗密探索)の回帰テスト。

設計の根拠 = docs/HIGHSPEED_VISION.md「ピラミッドの正体」。一次資料で確認した
HALCON の流儀に合わせて **画像をピラミッド化し、モデルは各階層で作り直す**
(モデル点を間引くのではない)。
"""
from __future__ import annotations

import numpy as np
import pytest

import shapematch as SM


def _scene(seed: int, size: int = 200):
    rng = np.random.default_rng(seed)
    img = rng.normal(0.5, 0.04, (size, size))
    pr = int(rng.integers(30, size - 60))
    pc = int(rng.integers(30, size - 60))
    img[pr:pr + 30, pc:pc + 8] += 0.5
    img[pr + 4:pr + 7, pc:pc + 30] += 0.5
    img[pr + 22:pr + 25, pc:pc + 22] += 0.4
    return np.clip(img, 0, 1), pr, pc


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_pyramid_matches_flat_search(seed):
    """ピラミッド探索は平坦な全走査と同じ答えを返す(位置 +-1 px、スコア +-0.02)。"""
    img, pr, pc = _scene(seed)
    m = SM.create_shape_model(img[pr:pr + 34, pc:pc + 34])
    flat = SM.find_shape_model(m, img, num_levels=0, step=1)
    pyr = SM.find_shape_model(m, img)
    assert abs(flat["row"] - pyr["row"]) <= 1
    assert abs(flat["col"] - pyr["col"]) <= 1
    assert abs(flat["score"] - pyr["score"]) < 0.02
    assert pyr["levels"] >= 2, "ピラミッドが 1 階層しか立っていない"


def test_pyramid_is_faster():
    """大きい画像では粗密探索が平坦走査より明確に速い。"""
    import time
    img, pr, pc = _scene(7, size=320)
    m = SM.create_shape_model(img[pr:pr + 40, pc:pc + 40])
    t0 = time.perf_counter()
    SM.find_shape_model(m, img, num_levels=0, step=1)
    flat = time.perf_counter() - t0
    t0 = time.perf_counter()
    SM.find_shape_model(m, img)
    pyr = time.perf_counter() - t0
    assert pyr * 5 < flat, f"速くない: 平坦 {flat:.3f}s ピラミッド {pyr:.3f}s"


def test_model_pyramid_rebuilds_per_level():
    """各階層のモデルは縮小テンプレートから **作り直され**、点数が減っていく。"""
    img, pr, pc = _scene(3)
    m = SM.create_shape_model(img[pr:pr + 40, pc:pc + 40])
    lv = SM.build_model_pyramid(m)
    assert len(lv) >= 2
    for a, b in zip(lv, lv[1:]):
        assert b["shape"][0] < a["shape"][0]
        assert len(b["pts"]) < len(a["pts"])


def test_stale_template_falls_back_to_flat():
    """shape と食い違う template を持つ模型(dict 複製で作られたもの)は
    ピラミッドを立てず平坦探索へ落ちる。find_scaled_shape_model 対策。"""
    img, pr, pc = _scene(5)
    m = SM.create_shape_model(img[pr:pr + 40, pc:pc + 40])
    m2 = dict(m)
    m2["shape"] = (20, 20)                      # template と食い違わせる
    assert len(SM.build_model_pyramid(m2)) == 1
    r = SM.find_shape_model(m2, img)
    assert r["levels"] == 1


def test_thin_structure_keeps_enough_points():
    """細い線でも、テンプレートが長ければ粗い階層まで点が残る(実測どおり)。

    効くのは「細さ」ではなく **粗い階層で残るモデル点の数**。
    """
    img = np.zeros((160, 160))
    img[80:81, 20:150] = 1.0                    # 1 px の細線
    m = SM.create_shape_model(img[74:88, 20:150])
    lv = SM.build_model_pyramid(m)
    assert len(lv) >= 2, "細線でも階層が立つはず(点数が十分残るため)"
