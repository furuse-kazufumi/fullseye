"""watersheds_marker の入力の門(2026-11-09 点検 g4_2d_stats の high / med)。

1. skimage の例外を ``except Exception`` で飲み、画像を見ない Voronoi へ黙って落ちていた。
   markers の形が違う((60,60) 対 image (80,80))と、例外なしで (60,60) を返した。
2. float の markers を切り捨てていた(0.9,1.8,2.7,3.6 → 0,1,2,3)。マーカー 1 個が消え、番号がずれた。
"""
import builtins

import numpy as np
import pytest
from scipy import ndimage

import segmentation as S


def _img():
    rng = np.random.default_rng(5)
    im = ndimage.gaussian_filter(rng.random((80, 80)), 3)
    return (im - im.min()) / np.ptp(im)


def _markers():
    mk = np.zeros((80, 80), int)
    mk[10, 10] = 1
    mk[70, 70] = 2
    mk[10, 70] = 3
    mk[40, 40] = 4
    return mk


def test_shape_mismatch_is_refused():
    with pytest.raises(ValueError, match="shape"):
        S.watersheds_marker(_img(), _markers()[:60, :60])


def test_zero_image_and_smaller_markers_refused():
    with pytest.raises(ValueError):
        S.watersheds_marker(np.zeros((80, 80)), np.zeros((60, 60), int))


def test_non_integer_float_markers_are_refused():
    with pytest.raises(ValueError, match="integer"):
        S.watersheds_marker(_img(), _markers().astype(float) * 0.9)


def test_integer_valued_float_markers_match_skimage():
    sks = pytest.importorskip("skimage.segmentation")
    im, mk = _img(), _markers()
    lab = S.watersheds_marker(im, mk.astype(float))
    assert int((lab != sks.watershed(im, mk)).sum()) == 0
    assert set(np.unique(lab).tolist()) == {1, 2, 3, 4}


def test_bool_and_uint_markers_accepted():
    pytest.importorskip("skimage")
    im = _img()
    mk = np.zeros((80, 80), bool)
    mk[5, 5] = True
    assert set(np.unique(S.watersheds_marker(im, mk)).tolist()) == {1}
    assert set(np.unique(S.watersheds_marker(im, _markers().astype(np.uint8))).tolist()) == {1, 2, 3, 4}


def test_negative_or_nan_markers_refused():
    mk = _markers().astype(float)
    mk[0, 0] = np.nan
    with pytest.raises(ValueError):
        S.watersheds_marker(_img(), mk)
    mk2 = _markers()
    mk2[0, 0] = -1
    with pytest.raises(ValueError):
        S.watersheds_marker(_img(), mk2)


def test_correct_input_still_matches_skimage_exactly():
    sks = pytest.importorskip("skimage.segmentation")
    im, mk = _img(), _markers()
    assert int((S.watersheds_marker(im, mk) != sks.watershed(im, mk)).sum()) == 0
    flat = np.zeros((40, 40))
    assert int((S.watersheds_marker(flat, mk[:40, :40]) != sks.watershed(flat, mk[:40, :40])).sum()) == 0


def test_missing_skimage_is_fail_closed_not_voronoi(monkeypatch):
    """skimage を import 不能にすると、Voronoi に落ちず MissingDependencyError(ImportError)。"""
    from backend_safe import MissingDependencyError
    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name == "skimage" or name.startswith("skimage."):
            raise ImportError("no skimage (test)")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(MissingDependencyError, match="skimage"):
        S.watersheds_marker(_img(), _markers())


def test_skimage_errors_are_not_swallowed(monkeypatch):
    """skimage の中で起きた例外(ImportError 以外)は、そのまま外に出る。"""
    sks = pytest.importorskip("skimage.segmentation")

    def boom(*a, **k):
        raise RuntimeError("inner failure (test)")

    monkeypatch.setattr(sks, "watershed", boom)
    with pytest.raises(RuntimeError, match="inner failure"):
        S.watersheds_marker(_img(), _markers())
