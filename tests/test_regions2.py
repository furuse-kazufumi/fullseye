"""Ground-truth + functional-gate tests for backends_regions2 (r2_ tier).

Runs WITHOUT importing ops.py: a tiny ``_Op`` stub stands in for the real dataclass
and we drive :func:`backends_regions2.build` directly.  Every operator gets (1) a
functional-gate check across three (a, b) knob settings and (2) a constructed-input
test that proves the CLAIMED semantics, not merely that the fn runs.
"""
from __future__ import annotations

import numpy as np
import pytest

import backends_regions2 as R2


class _Op:
    def __init__(self, *a):
        self.name = a[0]
        self.halcon = a[2]
        self.in_sort = a[3]
        self.out_sort = a[4]
        self.fn = a[5]


def _norm(x):
    m = float(np.max(np.abs(x)))
    return x / m if m > 1e-8 else x


def _binm(v):
    return np.asarray(v) > 0.5


OPS = R2.build(_Op, "image", "region", "feature", "contour", _norm, _binm)
OPS_BY_NAME = {o.name: o for o in OPS}


# --------------------------------------------------------------------------- #
# canonical inputs
# --------------------------------------------------------------------------- #
def _canonical_region():
    """A mask with a filled disk, a rectangle blob and a small blob (multi-component)."""
    m = np.zeros((60, 60), np.float64)
    yy, xx = np.ogrid[:60, :60]
    m[(yy - 15) ** 2 + (xx - 15) ** 2 <= 9 ** 2] = 1.0     # disk
    m[35:50, 30:55] = 1.0                                  # rectangle
    m[5:9, 45:49] = 1.0                                    # small blob
    return m


def _disk_mask(h, w, cy, cx, r):
    yy, xx = np.ogrid[:h, :w]
    return ((yy - cy) ** 2 + (xx - cx) ** 2 <= r * r).astype(np.float64)


AB = [(0.3, 0.4), (0.6, 0.7), (0.15, 0.85)]


# --------------------------------------------------------------------------- #
# registry sanity
# --------------------------------------------------------------------------- #
def test_registry_names_unique_and_prefixed():
    names = [o.name for o in OPS]
    assert len(names) == len(set(names)), "duplicate op names"
    # em_skeleton はアルゴリズム名(Eckhardt-Maderlechner)を冠する意図的な例外
    assert all(n.startswith("r2_") or n == "em_skeleton" for n in names)
    # halcon is always a str; it MAY be "" for a genuine op that does not claim a
    # HALCON name (e.g. r2_smallest_rectangle1 duplicates a core op's coverage, so
    # it carries no name to avoid a double coverage-claim; em_skeleton likewise —
    # `skeleton` coverage is already claimed by the core skeleton op).
    assert all(isinstance(o.halcon, str) for o in OPS)
    assert ({o.name for o in OPS if not o.halcon}
            == {"r2_smallest_rectangle1", "em_skeleton", "r2_endpoints_skeleton"})
    # contlength is honestly skipped, not silently faked
    assert "contlength" in R2.SKIPPED
    assert "contlength" not in {o.halcon for o in OPS}


# --------------------------------------------------------------------------- #
# functional gate: correct sort / ndim / dtype / finite / domain, never raises
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("op", OPS, ids=[o.name for o in OPS])
@pytest.mark.parametrize("a,b", AB)
def test_functional_gate(op, a, b):
    m = _canonical_region()
    out = op.fn(m.copy(), a, b)
    if op.out_sort == "region":
        assert isinstance(out, np.ndarray)
        assert out.ndim == 2
        assert out.dtype == np.float64
        assert out.shape == m.shape
        assert np.all(np.isfinite(out))
        assert out.min() >= 0.0 and out.max() <= 1.0
        assert np.all((out == 0.0) | (out == 1.0)), "region must be a 0/1 mask"
    elif op.out_sort == "feature":
        f = float(out)
        assert np.isfinite(f)
    else:
        raise AssertionError(f"unexpected out_sort {op.out_sort}")


@pytest.mark.parametrize("op", OPS, ids=[o.name for o in OPS])
def test_fail_soft_on_degenerate(op):
    for bad in (np.zeros((8, 8)), np.ones((8, 8)), np.zeros((1, 1)), np.zeros((3, 3))):
        out = op.fn(bad.astype(np.float64), 0.5, 0.5)     # must not raise
        if op.out_sort == "region":
            assert np.all(np.isfinite(out))
        else:
            assert np.isfinite(float(out))


# --------------------------------------------------------------------------- #
# ground truth
# --------------------------------------------------------------------------- #
def test_inner_circle_of_disk_recovers_disk():
    h = w = 61
    cy = cx = 30
    r = 18
    disk = _disk_mask(h, w, cy, cx, r)
    out = OPS_BY_NAME["r2_inner_circle"].fn(disk, 0.5, 0.5)   # a=0.5 -> exact inradius
    inter = np.logical_and(out > 0.5, disk > 0.5).sum()
    union = np.logical_or(out > 0.5, disk > 0.5).sum()
    iou = inter / union
    assert iou > 0.85, f"inner circle of a disk should ~equal the disk (IoU={iou:.3f})"
    # center of the drawn circle sits at the disk center
    ys, xs = np.where(out > 0.5)
    assert abs(ys.mean() - cy) <= 1.5 and abs(xs.mean() - cx) <= 1.5


def test_inner_circle_stays_inside_ring_free_region():
    # inscribed circle of a square must fit inside it (no spill of note)
    m = np.zeros((50, 50), np.float64)
    m[10:40, 10:40] = 1.0
    out = OPS_BY_NAME["r2_inner_circle"].fn(m, 0.5, 0.5)
    spill = np.logical_and(out > 0.5, m < 0.5).sum()
    assert spill <= out.sum() * 0.03, "inscribed circle should stay within the region"


def test_inner_rectangle1_of_solid_rectangle_is_that_rectangle():
    m = np.zeros((50, 60), np.float64)
    m[8:33, 12:52] = 1.0                                     # 25 x 40 solid block
    out = OPS_BY_NAME["r2_inner_rectangle1"].fn(m, 0.0, 0.0)  # a=0 -> exact
    assert np.array_equal(out > 0.5, m > 0.5), "max inscribed rect == the solid block"


def test_inner_rectangle1_all_foreground():
    # the returned rectangle must be entirely inside the region
    m = np.zeros((40, 40), np.float64)
    m[5:35, 5:35] = 1.0
    m[20:35, 20:35] = 0.0                                    # carve an L
    out = OPS_BY_NAME["r2_inner_rectangle1"].fn(m, 0.0, 0.0)
    assert out.sum() > 0
    assert np.all(m[out > 0.5] > 0.5), "inscribed rect must be all-foreground"


def test_smallest_rectangle1_is_axis_bbox():
    m = np.zeros((40, 40), np.float64)
    pts = [(6, 9), (30, 33), (6, 33), (30, 9), (18, 20)]
    for (y, x) in pts:
        m[y, x] = 1.0
    out = OPS_BY_NAME["r2_smallest_rectangle1"].fn(m, 0.5, 0.5)
    ys, xs = np.where(out > 0.5)
    assert ys.min() == 6 and ys.max() == 30
    assert xs.min() == 9 and xs.max() == 33
    # every point is covered
    for (y, x) in pts:
        assert out[y, x] > 0.5


def test_smallest_circle_encloses_all_and_radius_is_minimal():
    # exact geometry on the four corners of a square
    s = 40
    corners = np.array([[0, 0], [0, s], [s, 0], [s, s]], np.float64)
    cy, cx, r = R2._min_enclosing_circle(corners)
    assert abs(cy - s / 2) < 1e-6 and abs(cx - s / 2) < 1e-6
    # minimal enclosing radius of a square = half the diagonal
    assert abs(r - (s * np.sqrt(2) / 2)) < 1e-4
    # and no smaller than that: a radius = side/2 would NOT enclose the corners
    assert r > s / 2 + 1.0

    # op: every foreground pixel of a filled square lands inside the drawn circle
    m = np.zeros((60, 60), np.float64)
    m[10:50, 10:50] = 1.0
    out = OPS_BY_NAME["r2_smallest_circle"].fn(m, 0.0, 0.0)
    assert np.all(out[m > 0.5] > 0.5), "min enclosing circle must contain the region"


def test_smallest_circle_tight_not_whole_image():
    m = np.zeros((80, 80), np.float64)
    m[30:50, 30:50] = 1.0                                    # 20x20 square near center
    ys, xs = np.where(m > 0.5)
    _, _, r = R2._min_enclosing_circle(np.column_stack([ys, xs]))
    # radius ~ half diagonal of a 19-wide square (~13.4), certainly < 20
    assert 12.0 < r < 16.0


def test_smallest_rectangle2_aligns_to_rotated_bar():
    # build a bar of length ~40, width ~6, rotated by theta
    h = w = 100
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    cx = cy = 50.0
    theta = np.deg2rad(30.0)
    ux, uy = np.cos(theta), np.sin(theta)
    du = (xx - cx) * ux + (yy - cy) * uy
    dv = -(xx - cx) * uy + (yy - cy) * ux
    bar = ((np.abs(du) <= 20.0) & (np.abs(dv) <= 3.0)).astype(np.float64)

    ys, xs = np.where(bar > 0.5)
    _, _, long_len, short_len, ang = R2._min_area_rect(np.column_stack([ys, xs]))
    # long side ~ 40, short side ~ 6
    assert 36 < long_len < 46, long_len
    assert 3 < short_len < 10, short_len
    # orientation matches the bar (mod 180)
    err = abs(((np.rad2deg(ang) - 30.0 + 90) % 180) - 90)
    assert err < 6.0, f"oriented rect angle off by {err:.1f} deg"

    # rasterised oriented rect covers essentially the whole bar
    out = OPS_BY_NAME["r2_smallest_rectangle2"].fn(bar, 0.0, 0.0)
    covered = np.logical_and(out > 0.5, bar > 0.5).sum() / bar.sum()
    assert covered > 0.95, f"oriented rect should cover the bar (covered={covered:.3f})"


def test_smallest_rectangle2_beats_axis_bbox_on_diagonal():
    # a diagonal bar: oriented min-area rect is far smaller than the axis bbox
    h = w = 80
    m = np.zeros((h, w), np.float64)
    for t in range(10, 70):
        m[t, t] = 1.0
        m[t, t + 1] = 1.0
    ys, xs = np.where(m > 0.5)
    _, _, long_len, short_len, _ = R2._min_area_rect(np.column_stack([ys, xs]))
    axis_area = (ys.max() - ys.min() + 1) * (xs.max() - xs.min() + 1)
    oriented_area = long_len * short_len
    assert oriented_area < axis_area * 0.5, "oriented rect must be tighter than axis bbox"


def test_sort_region_picks_kth_largest():
    m = np.zeros((60, 60), np.float64)
    m[2:22, 2:22] = 1.0                                      # area 400 (largest)
    m[2:12, 40:50] = 1.0                                     # area 100 (middle)
    m[50:55, 50:54] = 1.0                                    # area 20  (smallest)
    op = OPS_BY_NAME["r2_sort_region"]
    largest = op.fn(m, 0.0, 0.0)                             # k=0
    middle = op.fn(m, 0.5, 0.0)                              # k=1 (n=3 -> round(0.5*2)=1)
    smallest = op.fn(m, 1.0, 0.0)                            # k=2
    assert abs(largest.sum() - 400) < 1e-6
    assert abs(middle.sum() - 100) < 1e-6
    assert abs(smallest.sum() - 20) < 1e-6
    # each result is a single connected component
    from scipy import ndimage
    for r in (largest, middle, smallest):
        _, n = ndimage.label(r > 0.5)
        assert n == 1


def test_union1_merges_all_components():
    m = np.zeros((40, 40), np.float64)
    m[2:10, 2:10] = 1.0
    m[20:30, 25:35] = 1.0
    out = OPS_BY_NAME["r2_union1"].fn(m, 0.5, 0.5)
    # union of components == the whole foreground
    assert np.array_equal(out > 0.5, m > 0.5)
    assert out.sum() == m.sum()


def test_partition_rectangle_drops_empty_cells():
    # L-shaped region: bbox is a full square, bottom-right quadrant is empty
    m = np.zeros((40, 40), np.float64)
    m[0:40, 0:20] = 1.0                                      # left half
    m[0:20, 0:40] = 1.0                                      # top half  -> L (br empty)
    m[20:40, 20:40] = 0.0
    out = OPS_BY_NAME["r2_partition_rectangle"].fn(m, 0.1, 0.0)   # a small -> 2x2 grid
    # bottom-right quadrant must be dropped
    assert out[20:40, 20:40].sum() == 0.0
    # the three occupied quadrants are fully filled
    assert out[0:20, 0:20].mean() == 1.0
    assert out[20:40, 0:20].mean() == 1.0
    assert out[0:20, 20:40].mean() == 1.0


def test_runlength_features_mean_equals_width():
    m = np.zeros((30, 40), np.float64)
    m[5:20, 8:28] = 1.0                                      # solid rows of width 20
    f = float(OPS_BY_NAME["r2_runlength_features"].fn(m, 0.5, 0.5))
    assert abs(f - 20.0) < 1e-9, f"mean run length of width-20 rows should be 20 (got {f})"


def test_runlength_features_two_runs_per_row():
    m = np.zeros((10, 30), np.float64)
    m[3:7, 2:7] = 1.0                                        # run length 5
    m[3:7, 20:29] = 1.0                                      # run length 9
    f = float(OPS_BY_NAME["r2_runlength_features"].fn(m, 0.5, 0.5))
    assert abs(f - 7.0) < 1e-9, f"mean of runs {{5,9}} should be 7 (got {f})"


def test_split_skeleton_lines_breaks_plus_into_arms():
    from scipy import ndimage
    m = np.zeros((41, 41), np.float64)
    m[19:22, 5:36] = 1.0                                     # thick horizontal bar
    m[5:36, 19:22] = 1.0                                     # thick vertical bar (a plus)
    _, n_before = ndimage.label(m > 0.5)
    assert n_before == 1
    out = OPS_BY_NAME["r2_split_skeleton_lines"].fn(m, 0.0, 0.0)
    _, n_after = ndimage.label(out > 0.5)                    # 4-connectivity
    assert n_after >= 4, f"splitting a plus at its junction should yield >=4 arms (got {n_after})"
    # the junction region is removed: center pixel is no longer set
    assert out[20, 20] == 0.0


def test_split_skeleton_lines_leaves_straight_line_intact_count():
    from scipy import ndimage
    m = np.zeros((20, 40), np.float64)
    m[9:11, 4:36] = 1.0                                      # a single straight bar
    out = OPS_BY_NAME["r2_split_skeleton_lines"].fn(m, 0.0, 0.0)
    _, n = ndimage.label(out > 0.5)
    assert n == 1, "a junction-free line stays a single segment"
    assert out.sum() > 0


# --------------------------------------------------------------------------- #
# em_skeleton (Eckhardt-Maderlechner 型不変細線化) の回帰テスト
# --------------------------------------------------------------------------- #
def _em(m):
    return OPS_BY_NAME["em_skeleton"].fn(m, 0.5, 0.5)


def _topo(m):
    """(前景8連結成分数, 穴数)。画像外=背景の海を明示してから数える。"""
    from scipy import ndimage
    p = np.pad(np.asarray(m) > 0.5, 1)
    st8 = ndimage.generate_binary_structure(2, 2)
    return ndimage.label(p, structure=st8)[1], ndimage.label(~p)[1] - 1


def _em_test_shapes():
    from scipy import ndimage
    rng = np.random.default_rng(0)
    blob = ndimage.gaussian_filter(rng.random((120, 120)), 5)
    yy, xx = np.mgrid[:100, :100]
    ring = (((yy - 50) ** 2 + (xx - 50) ** 2) < 38 ** 2) & \
           (((yy - 50) ** 2 + (xx - 50) ** 2) > 10 ** 2)
    L = np.zeros((80, 80))
    L[8:72, 8:28] = 1.0
    L[52:72, 8:72] = 1.0
    return {"blob": (blob > blob.mean()).astype(np.float64),
            "ring": ring.astype(np.float64), "L": L}


def test_em_skeleton_preserves_topology():
    for name, m in _em_test_shapes().items():
        sk = _em(m)
        assert _topo(m) == _topo(sk), f"{name}: 位相(成分数・穴数)が保存されない"


def test_em_skeleton_symmetric_and_idempotent():
    m = _em_test_shapes()["blob"]
    sk = _em(m)
    assert np.array_equal(_em(np.rot90(m).copy()), np.rot90(sk)), "90度回転と非可換"
    assert np.array_equal(_em(m[::-1].copy()), sk[::-1]), "上下反転と非可換"
    assert np.array_equal(_em(sk), sk), "冪等でない"


def test_em_skeleton_thin_no_interior():
    from scipy import ndimage
    cross = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], bool)
    for name, m in _em_test_shapes().items():
        sk = _em(m) > 0.5
        interior = ndimage.binary_erosion(sk, structure=cross, border_value=0)
        assert interior.sum() == 0, f"{name}: interior 画素が残っている(細くない)"


def test_em_skeleton_branchier_than_zhang_suen():
    # EM 系は対称・枝多(Couprie の比較表の性格)。Zhang-Suen より画素が多い
    skimage = pytest.importorskip("skimage")
    from skimage.morphology import skeletonize
    m = _em_test_shapes()["blob"]
    em_px = (_em(m) > 0.5).sum()
    zs_px = skeletonize(m > 0.5).sum()
    assert em_px > zs_px, f"EM({em_px}px) が Zhang-Suen({zs_px}px) より枝を残すはず"


def test_em_skeleton_empty_and_single_pixel():
    assert _em(np.zeros((10, 10))).sum() == 0
    one = np.zeros((10, 10))
    one[5, 5] = 1.0
    assert np.array_equal(_em(one), one), "孤立 1 画素は不変のはず"


def test_em_skeleton_matches_published_em93_reference():
    """公表された EM93 の参照出力との突き合わせ(HALCON 実機なしの検証)。

    fixture の来歴: M. Couprie, "Note on fifteen 2D parallel thinning
    algorithms"(公開 PDF)の Fig 16(g)/Fig 17 から抽出した 1:1 ラスタ。
    同ノートの表(Fig 18)の EM93 行 = N1 724 / N2 2434 / N3 3895。
    形状 1 は骨格の画素集合そのもの、形状 2/3 は画素数で照合する。
    """
    import pathlib
    data = np.load(pathlib.Path(__file__).parent / "data" / "em93_reference.npz")
    mine1 = OPS_BY_NAME["em_skeleton"].fn(
        data["shape1"].astype(np.float64), 0.5, 0.5) > 0.5
    ref1 = data["em_skeleton1"].astype(bool)
    assert (mine1 == ref1).all(), (
        f"形状1で参照 EM93 と不一致: mine={int(mine1.sum())} ref={int(ref1.sum())} "
        f"diff={int((mine1 ^ ref1).sum())}")
    for key, nkey in (("shape2", "n2"), ("shape3", "n3")):
        mine = OPS_BY_NAME["em_skeleton"].fn(
            data[key].astype(np.float64), 0.5, 0.5) > 0.5
        assert int(mine.sum()) == int(data[nkey]), (
            f"{key}: 画素数 {int(mine.sum())} != 公表値 {int(data[nkey])}")


def test_endpoints_skeleton_plus_and_line():
    from scipy import ndimage
    # 1 画素幅の十字 -> 端点はちょうど腕の先の 4 画素、中心(分岐点)は端点でない
    m = np.zeros((41, 41), np.float64)
    m[20, 5:36] = 1.0
    m[5:36, 20] = 1.0
    out = OPS_BY_NAME["r2_endpoints_skeleton"].fn(m, 0.5, 0.5)
    ys, xs = np.where(out > 0.5)
    assert sorted(zip(ys.tolist(), xs.tolist())) == \
        [(5, 20), (20, 5), (20, 35), (35, 20)]
    assert out[20, 20] == 0.0
    # 太い十字 -> 内部で em_skeleton が走る。EM は枝を多く残すので
    # 端点クラスタは 4 以上(厳密数はアルゴリズム特性に依存するため縛らない)
    thick = np.zeros((41, 41), np.float64)
    thick[19:22, 5:36] = 1.0
    thick[5:36, 19:22] = 1.0
    out = OPS_BY_NAME["r2_endpoints_skeleton"].fn(thick, 0.5, 0.5)
    _, n = ndimage.label(out > 0.5, structure=np.ones((3, 3)))
    assert n >= 4, f"太い十字でも端点クラスタは 4 以上のはず (got {n})"
    # 1 画素幅の直線 -> 端点はちょうど両端の 2 画素
    line = np.zeros((11, 30), np.float64)
    line[5, 4:26] = 1.0
    out = OPS_BY_NAME["r2_endpoints_skeleton"].fn(line, 0.5, 0.5)
    ys, xs = np.where(out > 0.5)
    assert sorted(zip(ys.tolist(), xs.tolist())) == [(5, 4), (5, 25)]
    # 孤立 1 画素は端点
    dot = np.zeros((9, 9), np.float64)
    dot[4, 4] = 1.0
    assert OPS_BY_NAME["r2_endpoints_skeleton"].fn(dot, 0.5, 0.5)[4, 4] == 1.0
