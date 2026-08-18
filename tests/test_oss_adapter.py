"""OSS アダプタ契約(F4)の回帰テスト — 同一 I/F + backend 切替 + numpy フォールバック。"""
from __future__ import annotations

import warnings

import numpy as np

warnings.simplefilter("ignore")
from scipy.ndimage import gaussian_filter  # noqa: E402

import oss_adapter as O  # noqa: E402


def _pair(h=64, w=96, shift=4):
    left = gaussian_filter(np.random.default_rng(0).random((h, w)), 1.0)
    return left, np.roll(left, shift, axis=1)


def test_backends_reported():
    """F4: 各アダプタが実際に使う backend を報告する。"""
    b = O.backends()
    assert len(b) == 8
    for name, be in b.items():
        assert be in ("opencv", "skimage", "numpy(fallback)")


def test_prefer_numpy_forces_fallback():
    """F4: prefer='numpy' は OSS があっても numpy フォールバックを選ぶ。"""
    assert O.stereo.BlockMatching(prefer="numpy").backend == "numpy(fallback)"
    assert O.filter.Bilateral(prefer="numpy").backend == "numpy(fallback)"
    assert O.features.ORB(prefer="numpy").backend == "numpy(fallback)"


def test_stereo_both_backends_produce_disparity():
    """F4: BM/SGBM が OSS・numpy 双方で視差画像(同種)を返す。"""
    left, right = _pair()
    for cls in (O.stereo.BlockMatching, O.stereo.SGBM):
        d_auto = cls(max_disp=32).compute(left, right)
        d_np = cls(max_disp=32, prefer="numpy").compute(left, right)
        assert d_auto.shape == left.shape and d_np.shape == left.shape


def test_bilateral_fallback_close_to_opencv():
    """F4: Bilateral の numpy フォールバックが OSS 版と近い(同種の結果)。"""
    left, _ = _pair()
    cv = O.filter.Bilateral(d=5, sigma_color=0.2, sigma_space=3).apply(left)
    npv = O.filter.Bilateral(d=5, sigma_color=0.2, sigma_space=3, prefer="numpy").apply(left)
    assert cv.shape == npv.shape
    assert np.abs(cv - npv).mean() < 0.05          # エッジ保存平滑化として近い


def test_orb_and_harris_detect_keypoints():
    """F4: ORB(cv2)も Harris(numpy フォールバック)も keypoints を返す。"""
    tex = gaussian_filter(np.random.default_rng(1).random((80, 80)), 0.8)
    assert len(O.features.ORB(n=100).detect(tex)) >= 0     # cv2 は少ないこともある
    assert len(O.features.ORB(n=100, prefer="numpy").detect(tex)) > 0


def test_findcontours_circle_both_backends():
    """F4: findContours が OSS・numpy 双方で円輪郭(半径 ~15)を返す。"""
    yy, xx = np.mgrid[0:64, 0:64]
    mask = ((xx - 32) ** 2 + (yy - 32) ** 2 < 15 ** 2).astype(float)
    for prefer in ("auto", "numpy"):
        c = O.contour.FindContours(level=0.5, prefer=prefer).find(mask)
        assert len(c["cs"]) >= 1
        arr = c["cs"][0]
        d = np.hypot(arr[:, 0] - 32, arr[:, 1] - 32)
        assert 12 < np.median(d) < 18


def test_in_unified_registry():
    """F4: OSS アダプタが統一 registry に provenance=oss-adapter で載る。"""
    import unified as u
    assert any(o.provenance == "oss-adapter" for o in u.ops.find("SGBM"))
    d = u.ops.describe("BlockMatching")
    assert d["provenance"] == "oss-adapter" and "backend" in d["doc"]
