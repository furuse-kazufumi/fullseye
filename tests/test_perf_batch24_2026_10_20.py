"""Regression gates for performance review batch 24.

The ``_old_*`` functions intentionally preserve the implementation at c52e55d416.
"""
import numpy as np
import pytest
from scipy import special

import mathops
import mathtransforms
import sdf_ops


def _old_hankel(r, f, *, r_max, order, n):
    j = special.jn_zeros(order, n + 1); S = j[-1]; jk = j[:-1]
    rg = jk * r_max / S; nu = jk / (2 * np.pi * r_max); V = S / (2*np.pi*r_max)
    fr = np.interp(rg, r, f, right=0.0); jp = np.abs(special.jv(order + 1, jk))
    T = 2 * special.jv(order, np.outer(jk, jk) / S) / (np.outer(jp, jp) * S)
    return T @ (fr / jp * r_max) * jp / V, float(np.abs(T @ T - np.eye(n)).max())


@pytest.mark.parametrize("order", [0, 1, 2])
@pytest.mark.parametrize("n", [64, 256])
def test_238_hankel_plan_exact_and_reused(order, n):
    r = np.linspace(0, 5, 401); f = np.exp(-r*r)
    plan = mathtransforms.HankelPlan(order, n)
    built = mathtransforms.HankelPlan.constructions
    assert mathtransforms.HankelPlan(order, n) is plan
    assert mathtransforms.HankelPlan.constructions == built
    for R in (2.5, 4.5):
        old, err = _old_hankel(r, f, r_max=R, order=order, n=n)
        got = mathtransforms.hankel_transform(r, f, r_max=R, order=order, n=n, plan=plan)
        np.testing.assert_allclose(got["F"], old, rtol=0, atol=1e-12)
        assert got["T_involution_error"] == err == plan.T_involution_error


def _old_analysis(a, h, g, axis):
    a = np.moveaxis(a, axis, -1); n = a.shape[-1]
    idx = (2*np.arange(n//2)[:, None] + np.arange(h.size)[None, :]) % n
    seg = a[..., idx]
    return tuple(np.moveaxis(v, -1, axis) for v in (seg @ h, seg @ g))


@pytest.mark.parametrize("shape", [(32,), (3, 32), (2, 3, 32)])
def test_239_analysis_matches_reference(shape):
    a = np.random.default_rng(4).normal(size=shape)
    for order in (2, 10):
        q = mathtransforms.wavelet_filters(order); h, g = q["lowpass"], q["highpass"]
        for axis in range(len(shape)):
            if shape[axis] % 2: continue
            old = _old_analysis(a, h, g, axis); new = mathtransforms._analysis_axis(a, h, g, axis)
            np.testing.assert_allclose(new, old, rtol=0, atol=1e-12)


def _old_synthesis(lo, hi, h, g, axis):
    lo, hi = np.moveaxis(lo,axis,-1), np.moveaxis(hi,axis,-1); m=lo.shape[-1]; n=2*m
    out=np.zeros(lo.shape[:-1]+(n,)); idx=(2*np.arange(m)[:,None]+np.arange(h.size)[None,:])%n
    for j in range(h.size): out[...,idx[:,j]] += lo*h[j]+hi*g[j]
    return np.moveaxis(out,-1,axis)


def test_240_synthesis_reference_and_reconstruction():
    x=np.random.default_rng(8).normal(size=(4,8,32))
    for order in (2,10):
        q=mathtransforms.wavelet_filters(order); h,g=q["lowpass"],q["highpass"]
        for axis in range(3):
            lo,hi=_old_analysis(x,h,g,axis)
            np.testing.assert_allclose(mathtransforms._synthesis_axis(lo,hi,h,g,axis), _old_synthesis(lo,hi,h,g,axis), atol=1e-12)


def test_241_hankel_image_memory_mode_matches():
    y,x=np.indices((129,151)); im=np.exp(-((y-61.3)**2+(x-76.7)**2)/400)
    old=mathtransforms.hankel_image(im,center=(61.3,76.7),n=64)
    new=mathtransforms.hankel_image(im,center=(61.3,76.7),n=64,memory_budget=32768)
    for key in ("r","profile","F"): np.testing.assert_allclose(new[key],old[key],atol=1e-10,rtol=0)
    assert abs(new["asymmetry"]-old["asymmetry"]) < 1e-10


def test_242_chunked_neighbours_bit_identical_ties_and_duplicates():
    p=np.array([(x,y) for x in range(12) for y in range(12)],float); p=np.vstack([p,p[:3]])
    assert np.array_equal(mathops.neighbour_index_gaps(p,5,chunk=17), mathops.neighbour_index_gaps(p,5,chunk=10000))


def test_244_finite_bifurcation_returns_view_without_copy():
    out=mathops.dynsys_bifurcation_map(n_r=30,burn_in=20,keep=8)
    assert not out.flags.owndata and out.base is not None


@pytest.mark.parametrize("dtype",[np.uint8,np.uint16,np.float32])
def test_245_period_matches_old_float64_copy(dtype):
    x=np.arange(512); im=(100+40*np.cos(2*np.pi*x/23.7))[None,:].repeat(80,0).astype(dtype)
    assert abs(mathops.wave_fringe_period(im)-mathops.wave_fringe_period(im.astype(np.float64))) < 1e-12


def test_243_dict_validation_and_result():
    t = np.linspace(0, 20, 1000); d = {f"x{i}": np.sin(t+i) for i in range(12)}
    got = mathops.dynsys_poincare_section(d, axis=2, value=0)
    arr = np.stack([d[k] for k in sorted(d)], axis=1)
    np.testing.assert_allclose(got, mathops.dynsys_poincare_section(arr, axis=2, value=0), atol=1e-12)
    bad = dict(d); bad["x11"] = bad["x11"][:-1]
    with pytest.raises(ValueError): mathops.dynsys_poincare_section(bad)
    bad = dict(d); bad["x11"] = bad["x11"].copy(); bad["x11"][2] = np.nan
    with pytest.raises(ValueError): mathops.dynsys_poincare_section(bad)


def test_246_lu_preserves_p_and_residual():
    for a in (np.array([[1e-14, 1.], [1., 1.]]), np.random.default_rng(2).normal(size=(20,20))):
        for mode in ("partial", "none"):
            got = mathops.mat_lu(a, mode)
            scale = max(np.abs(a).max(), np.finfo(float).tiny)
            old = float(np.abs(got["P"] @ a - got["L"] @ got["U"]).max()) / scale
            assert abs(got["residual"] - old) <= 1e-14


def test_247_axes_match_dense_primitives_and_csg():
    axes, _ = sdf_ops.grid_axes([[-2,2],[-3,3],[-1,1]], [17,13,11])
    dense, _ = sdf_ops.grid_coords([[-2,2],[-3,3],[-1,1]], [17,13,11])
    s0 = sdf_ops.sphere_sdf(dense, [.2,.3,.1], 1.2)
    b0 = sdf_ops.box_sdf(dense, [-.2,0,0], [.8,.7,.6])
    p0 = sdf_ops.plane_sdf(dense, [0,0,.1], [1,2,3])
    for fn, args, old in ((sdf_ops.sphere_sdf,([.2,.3,.1],1.2),s0),
                          (sdf_ops.box_sdf,([-.2,0,0],[.8,.7,.6]),b0),
                          (sdf_ops.plane_sdf,([0,0,.1],[1,2,3]),p0)):
        np.testing.assert_allclose(fn(axes, *args), old, rtol=0, atol=1e-12)
    np.testing.assert_allclose(sdf_ops.sdf_union(sdf_ops.sphere_sdf(axes,[.2,.3,.1],1.2), sdf_ops.box_sdf(axes,[-.2,0,0],[.8,.7,.6])), sdf_ops.sdf_union(s0,b0), atol=1e-12)
    np.testing.assert_allclose(sdf_ops.sdf_subtract(sdf_ops.sphere_sdf(axes,[.2,.3,.1],1.2), sdf_ops.box_sdf(axes,[-.2,0,0],[.8,.7,.6])), sdf_ops.sdf_subtract(s0,b0), atol=1e-12)


def test_248_plane_fast_variant_accuracy():
    rng = np.random.default_rng(9); g = rng.uniform(-1e3, 1e3, (1000,3))
    np.testing.assert_allclose(sdf_ops.plane_sdf(g,[3,4,5],[1,2,3], method="fast"), sdf_ops.plane_sdf(g,[3,4,5],[1,2,3]), atol=1e-12, rtol=0)
