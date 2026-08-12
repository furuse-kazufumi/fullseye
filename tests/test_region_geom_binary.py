"""Regression guard: region-typed geometry ops must return a BINARY region.

Bug (2026-08-13 hardening audit, findings #5 / #41): the specs
`affine_trans_region`, `zoom_region`, `projective_trans_region` and
`polar_trans_region_inv` declare `in_sort = out_sort = "region"`, but they are
all compiled through `backends_auto._sh_geom`, which resamples with cubic-spline
(`ndimage.affine_transform`, order=3), bilinear (`cv2.warpPolar`) or perspective
(`cv2.warpPerspective`) interpolation and then only clips to [0, 1].  The result
carried FRACTIONAL membership -- transforming a radius-12 binary disk gave
`affine_trans_region` 2009 distinct values / 906 strictly-fractional pixels --
which violates the region contract (`out_sort == "region"` means values in
{0, 1}) and silently deletes thin/small regions at the `> 0.5` cut every
downstream region consumer (`ops._bin`) applies: a 1-pixel region peaked at
0.4977 and was read as the empty set.

Ground truth: a geometric transform is a bijection of the plane, so the image of
a SET is a SET.  Membership is boolean; only the support may move.

RED before the fix, GREEN after it.  The last test pins the other half of the
contract -- image-typed geometry ops share the same `_sh_geom` and must stay
CONTINUOUS, so the fix must not leak into them.
"""
from __future__ import annotations

import numpy as np
import pytest

import ops

# every spec with shape="geom" and out_sort="region"
REGION_GEOM = ["affine_trans_region", "zoom_region", "projective_trans_region",
               "polar_trans_region_inv", "mirror_region", "transpose_region"]

# the subset that actually resamples (mirror/transpose are exact re-indexings)
INTERPOLATING = ["affine_trans_region", "zoom_region", "projective_trans_region"]

# image-typed siblings compiled through the SAME _sh_geom: must stay continuous
IMAGE_GEOM = ["affine_trans_image", "zoom_image_factor", "rotate_image",
              "projective_trans_image"]

PARAMS = [(0.0, 0.0), (0.3, 0.7), (0.5, 0.5), (1.0, 1.0)]


def _disk(n=64, r=12, cy=32, cx=32) -> np.ndarray:
    yy, xx = np.mgrid[0:n, 0:n]
    return (((yy - cy) ** 2 + (xx - cx) ** 2) <= r * r).astype(np.float64)


def _fn(name):
    fn = ops.RT.get(name)
    if fn is None:
        pytest.skip(f"{name} not registered (backend absent)")
    return fn


@pytest.mark.parametrize("name", REGION_GEOM)
@pytest.mark.parametrize("a,b", PARAMS)
def test_region_geom_output_is_binary(name, a, b):
    """out_sort == 'region' => every pixel is exactly 0.0 or 1.0."""
    out = np.asarray(_fn(name)(_disk(), a, b), np.float64)
    assert np.all(np.isfinite(out)), f"{name} produced non-finite values"
    vals = set(np.unique(out).tolist())
    frac = int(((out > 1e-9) & (out < 1.0 - 1e-9)).sum())
    assert vals <= {0.0, 1.0}, (
        f"{name}(a={a}, b={b}) violated the region contract: "
        f"{len(vals)} distinct values, {frac} fractional pixels "
        f"(min={out.min()}, max={out.max()})")


@pytest.mark.parametrize("name", INTERPOLATING)
@pytest.mark.parametrize("a,b", PARAMS)
def test_region_geom_does_not_annihilate_a_solid_region(name, a, b):
    """A non-degenerate region (radius-8 disk, 197 px) survives the transform.

    These transforms are near-identity in scale (zoom 0.7x..1.3x, rotation
    +/-20 deg, perspective <= 18%), so a solid blob must keep a substantial part
    of its area -- re-binarising must never threshold it out of existence.
    """
    src = _disk(64, 8)
    out = np.asarray(_fn(name)(src.copy(), a, b), np.float64)
    area = float((out > 0.5).sum())
    assert area > 0.0, (
        f"{name}(a={a}, b={b}) annihilated a solid {int(src.sum())} px region")
    assert area >= 0.3 * float(src.sum()), (
        f"{name}(a={a}, b={b}) kept only {area} of {src.sum()} px")


@pytest.mark.parametrize("name", IMAGE_GEOM)
def test_image_geom_ops_stay_continuous(name):
    """The region fix must NOT leak into the image-typed geometry ops."""
    yy, xx = np.mgrid[0:48, 0:48]
    img = np.clip(xx / 47.0, 0, 1)
    out = np.asarray(_fn(name)(img.copy(), 0.3, 0.7), np.float64)
    assert np.unique(out).size > 2, (
        f"{name} was binarised: out_sort='image' must stay continuous "
        f"({np.unique(out).size} distinct values)")
