"""watershed3d の 3 op(台帳 opssegmentation の ``watershed3d``、2026-10-02)の門。

それまで ``fs.watershed3d.<fn>`` からしか届かず、関数名が tests/ にも examples/ にも出ていなかった。
門 = 鏡映対称な 2 球で体積が厳密に等しい / 前景をちょうど覆う / scipy と skimage の 2 実装が一致 /
separate_touching は watershed_vol(markers=None) を畳んだだけ / 離れた球は連結成分と同じ分割。
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import opssegmentation as O  # noqa: E402
import watershed3d as W  # noqa: E402

OPS = ("distance_peaks", "watershed_vol", "separate_touching")


def _balls(centres, radii, shape=(24, 24, 40)):
    z, y, x = np.mgrid[:shape[0], :shape[1], :shape[2]]
    v = np.zeros(shape, bool)
    for (cz, cy, cx), r in zip(centres, radii):
        v |= (z - cz) ** 2 + (y - cy) ** 2 + (x - cx) ** 2 <= r * r
    return v


def _touching(r1=7, r2=7):
    return _balls([(11.5, 11.5, 13), (11.5, 11.5, 26)], [r1, r2])


def _same_partition(a, b):
    fwd, bwd = {}, {}
    for p, q in zip(np.ravel(a).tolist(), np.ravel(b).tolist()):
        if fwd.setdefault(p, q) != q or bwd.setdefault(q, p) != p:
            return False
    return True


def test_the_ledger_lists_the_three_ops_with_voxel_in_and_labels_out():
    assert O.missing() == []
    assert set(O.list_ops("watershed3d")) == set(OPS)
    for n in OPS:
        meta = O.info(n)
        assert meta["in"] == ["voxel"] and meta["out"] == "labels"


def test_ops_are_reachable_from_fs_ledger():
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        import fullseye as fs
    for n in OPS:
        assert callable(getattr(fs.ledger, n))


def test_touching_balls_fuse_under_connected_components_but_seed_twice():
    v = _touching()
    assert ndimage.label(v)[1] == 1
    seeds = W.distance_peaks(v, min_distance=5.0)
    assert len(np.unique(seeds)) - 1 == 2


def test_mirror_symmetric_balls_get_exactly_equal_volumes():
    """x → 39 − x で 2 球が入れ替わり格子も自分に写る → 体積は厳密に等しい。"""
    v = _touching()
    assert np.array_equal(v, v[:, :, ::-1])
    lab = W.watershed_vol(v, min_distance=5.0)
    ids = [i for i in np.unique(lab) if i]
    assert len(ids) == 2
    a, b = ((lab == i).sum() for i in ids)
    assert a == b


@pytest.mark.parametrize("op", ["watershed_vol", "separate_touching"])
def test_labels_cover_exactly_the_foreground(op):
    v = _touching(7, 5)
    lab = O.call(op, v)
    assert np.array_equal(lab > 0, v)


def test_separate_touching_is_watershed_vol_without_markers():
    v = _touching(7, 5)
    for d in (3.0, 5.0):
        assert np.array_equal(W.separate_touching(v, min_distance=d),
                              W.watershed_vol(v, markers=None, min_distance=d))


@pytest.mark.skipif(importlib.util.find_spec("skimage") is None, reason="skimage が無い")
def test_scipy_fallback_agrees_with_skimage():
    """第 2 実装: 純 scipy のフォールバックと skimage の分水嶺が同じ分割(番号の付け替えに不変)。"""
    v = _touching()
    a = W.watershed_vol(v, min_distance=5.0, method="skimage")
    b = W.watershed_vol(v, min_distance=5.0, method="scipy")
    assert _same_partition(a, b)


def test_separate_balls_match_connected_components():
    """離れた 3 球は分水嶺でも連結成分と同じ分割(余計に割らない)。"""
    v = _balls([(11.5, 11.5, 7), (11.5, 11.5, 20), (11.5, 11.5, 33)], [4, 5, 4])
    cc = ndimage.label(v)[0]
    assert ndimage.label(v)[1] == 3
    assert _same_partition(W.separate_touching(v, min_distance=3.0), cc)


def test_the_larger_ball_gets_the_larger_label():
    v = _touching(7, 5)
    lab = W.separate_touching(v, min_distance=4.0)
    big, small = lab[11, 11, 13], lab[11, 11, 26]
    assert big != small and (lab == big).sum() > (lab == small).sum()


def test_empty_volume_returns_zeros():
    for n in OPS:
        out = O.call(n, np.zeros((6, 6, 6), bool))
        assert out.shape == (6, 6, 6) and not out.any()


def test_unknown_method_is_rejected():
    with pytest.raises(ValueError):
        W.watershed_vol(_touching(), method="nope")
