"""accel の常駐パイプライン(run_pipeline)テスト。

E2E の本丸 = **転送1回で op を連鎖する GPU 常駐パイプライン**。per-op の run_batch は
毎回バッチを転送し直すので、安い op ほど PCIe 転送に食われる(実測: batch
スループットが op によらず一定 = 転送律速、threshold/invert は CPU に負ける)。
run_pipeline は転送を1回に償却する —— そこで GPU が E2E で勝つ。

ここで固定する不変条件:
- **run_pipeline は run_batch を逐次適用したのと厳密一致**(同じ op・同じ device なので
  ビット一致)。torch が CPU ビルドでも成立するので GPU 無しの CI でも回る。

注意(honest、docs/HIGHSPEED_VISION.md「E2E GPU パイプラインの parity」):
accel の各 op は core registry と **内部が <5e-3 で一致**するが、**複数 op のチェーンは
ドリフトする** —— sobel/laplace の per-image-max 正規化(_norm_b)が端の reflect 規約差
(scipy reflect ≠ torch reflect)を全体スケールに広げ、末尾のハード threshold がそれを
二値反転に増幅する。だから CPU チェーンとの厳密一致は主張しない。GPU 常駐 vs GPU per-op
(どちらも accel = 同一演算)の転送償却が、parity 懸念なしに測れる正味の E2E 利得。
"""
import numpy as np
import pytest

import accel


HAS_TORCH = accel._HAS_TORCH


def _steps():
    return [("gauss_filter", 0.4, 0.4), ("sobel_amp", 0.5, 0.4),
            ("gray_dilation_rect", 0.5, 0.4), ("gray_erosion_rect", 0.5, 0.4),
            ("threshold", 0.3, 0.4)]


@pytest.mark.skipif(not HAS_TORCH, reason="torch 不在")
def test_resident_pipeline_equals_perop_chain():
    """常駐パイプラインは run_batch の逐次適用とビット一致(同一 op・同一 device)。"""
    rng = np.random.default_rng(0)
    imgs = [np.clip(rng.random((128, 128)), 0, 1) for _ in range(8)]
    steps = _steps()
    resident = accel.run_pipeline(steps, imgs, device="cpu")
    seq = imgs
    for name, a, b in steps:
        seq = accel.run_batch(name, seq, a, b, "cpu")
    for r, s in zip(resident, seq):
        assert np.array_equal(r, s)


@pytest.mark.skipif(not HAS_TORCH, reason="torch 不在")
def test_pipeline_shapes_and_range():
    rng = np.random.default_rng(1)
    imgs = [np.clip(rng.random((96, 96)), 0, 1) for _ in range(4)]
    out = accel.run_pipeline(_steps(), imgs, device="cpu")
    assert len(out) == 4
    for o in out:
        assert o.shape == (96, 96)
        assert o.min() >= 0.0 and o.max() <= 1.0


@pytest.mark.skipif(not HAS_TORCH, reason="torch 不在")
def test_empty_pipeline_is_identity():
    """空のステップ列は入力をそのまま返す(転送往復のみ)。"""
    rng = np.random.default_rng(2)
    imgs = [np.clip(rng.random((64, 64)), 0, 1) for _ in range(3)]
    out = accel.run_pipeline([], imgs, device="cpu")
    for i, o in zip(imgs, out):
        assert np.allclose(i, o, atol=1e-6)


@pytest.mark.skipif(not HAS_TORCH, reason="torch 不在")
def test_single_op_pipeline_matches_run_batch():
    rng = np.random.default_rng(3)
    imgs = [np.clip(rng.random((80, 80)), 0, 1) for _ in range(5)]
    a = accel.run_pipeline([("gauss_filter", 0.5, 0.4)], imgs, device="cpu")
    b = accel.run_batch("gauss_filter", imgs, 0.5, 0.4, "cpu")
    for x, y in zip(a, b):
        assert np.array_equal(x, y)
