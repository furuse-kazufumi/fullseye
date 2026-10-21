"""Performance slice 5: every optimized path is gated against its old algorithm."""
from __future__ import annotations

import math
import inspect

import numpy as np
import pytest

import acoustics
import bspline_surf
import filmoptics
import imgmetrics
import photoncount
import printpath
import spectralrad


def _old_compare(a, b, **kw):
    dr = imgmetrics.data_range_of(a, b, data_range=kw.get("data_range"))
    out = {"mse": imgmetrics.mse(a, b), "rmse": imgmetrics.rmse(a, b),
           "psnr": imgmetrics.psnr(a, b, data_range=dr),
           "ssim": imgmetrics.ssim(a, b, data_range=dr, channel_axis=kw.get("channel_axis")),
           "mutual_information": imgmetrics.mutual_information(a, b, bins=kw.get("bins", 64), data_range=dr),
           "ncd": imgmetrics.ncd(np.asarray(a), np.asarray(b),
              levels=256 if np.issubdtype(np.asarray(a).dtype, np.floating) else None,
              data_range=dr if np.issubdtype(np.asarray(a).dtype, np.floating) else None)}
    try:
        out["normalized_mutual_information"] = imgmetrics.normalized_mutual_information(
            a, b, bins=kw.get("bins", 64), data_range=dr)
    except ValueError:
        out["normalized_mutual_information"] = None
    if kw.get("ms"):
        out["ms_ssim"] = imgmetrics.ms_ssim(a, b, data_range=dr)
    return out


@pytest.mark.parametrize("case", ["gray", "uniform", "channel", "ms"])
def test_compare_images_matches_old_shared_primitives(case, monkeypatch):
    rng = np.random.default_rng(41)
    shape = (192, 192) if case == "ms" else ((32, 34, 3) if case == "channel" else (32, 34))
    a = np.full(shape, .25) if case == "uniform" else rng.random(shape)
    b = a.copy() if case == "uniform" else np.clip(a + rng.normal(0, .02, shape), 0, 1)
    kw = {"channel_axis": -1} if case == "channel" else ({"ms": True} if case == "ms" else {})
    old = _old_compare(a, b, **kw)
    counts = {"hist": 0}
    original = imgmetrics.np.histogram2d
    def counted(*args, **kwargs):
        counts["hist"] += 1
        return original(*args, **kwargs)
    monkeypatch.setattr(imgmetrics.np, "histogram2d", counted)
    got = imgmetrics.compare_images(a, b, **kw)
    assert counts["hist"] == 1
    for key, value in old.items():
        if value is None:
            assert got[key] is None
        else:
            assert got[key] == pytest.approx(value, abs=1e-12)
    source = inspect.getsource(imgmetrics.compare_images)
    assert source.count("(fa - fb) ** 2") == 1


def test_scattered_bspline_matches_old_loop_boundaries_knots_and_order():
    from scipy.interpolate import bisplrep, bisplev
    rng = np.random.default_rng(42)
    x = rng.random(300); y = rng.random(300); z = np.sin(3*x) + y*y
    tck = bisplrep(x, y, z, s=.2)
    qx = np.r_[rng.random(100_000), tck[0], [-1., 2.]]
    qy = np.r_[rng.random(100_000), np.resize(tck[1], len(tck[0])), [.3, .7]]
    order = rng.permutation(qx.size); qx, qy = qx[order], qy[order]
    old = np.array([float(bisplev(float(a), float(b), tck)) for a, b in zip(qx, qy)])
    assert np.allclose(bspline_surf.eval_bspline_surface(tck, qx, qy), old, rtol=0, atol=1e-10)


def _old_fill(ring, x, y, xmin, ymin, W, H, ppm):
    acc = np.zeros((H, W), np.int32)
    for rid in np.unique(ring):
        px=(x[ring==rid]-xmin)*ppm; py=(y[ring==rid]-ymin)*ppm
        if len(px)<3: continue
        sign=1 if .5*np.sum(px*np.roll(py,-1)-np.roll(px,-1)*py)>0 else -1
        for row in range(int(max(0,math.floor(py.min()))), int(min(H-1,math.ceil(py.max())))+1):
            yc=row+.5; xs=[]
            for i in range(len(px)):
                j=(i+1)%len(px); y0,y1=py[i],py[j]
                if (y0<=yc)!=(y1<=yc): xs.append(px[i]+(yc-y0)/(y1-y0)*(px[j]-px[i]))
            xs.sort()
            for a,b in zip(xs[0::2],xs[1::2]):
                lo,hi=int(math.ceil(a-.5)),int(math.floor(b-.5))
                if hi>=lo: acc[row,max(lo,0):min(hi,W-1)+1]+=sign
    return acc>0


@pytest.mark.parametrize("rings", [
    [np.array([[1,1],[9,1],[9,9],[1,9]]), np.array([[3,3],[3,7],[7,7],[7,3]])],
    [np.array([[1,.5],[8,.5],[8,3],[4,3],[4,8],[1,8]])],
    [np.array([[1,1],[5,5],[1,9]]), np.array([[5,5],[9,1],[9,9]])],
])
def test_active_edge_fill_is_bit_identical(rings):
    ring=np.concatenate([np.full(len(p),i) for i,p in enumerate(rings)])
    pts=np.concatenate(rings)
    got=printpath._fill_rings(ring,pts[:,0],pts[:,1],0,0,12,12,1)
    assert np.array_equal(got,_old_fill(ring,pts[:,0],pts[:,1],0,0,12,12,1))


def _box(z1=6.):
    v=np.array([[0,0,0],[5,0,0],[5,4,0],[0,4,0],[0,0,z1],[5,0,z1],[5,4,z1],[0,4,z1]],float)
    f=np.array([[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]])
    return v,f


def test_slice_stack_matches_old_all_triangle_layers_and_tests_fewer(monkeypatch):
    mesh=_box(); old=[]
    for k in range(6):
        c=printpath.mesh_slice_contours(mesh,k+.5)
        old.append(_old_fill(c["ring"],c["x"],c["y"],-2,-2,90,80,10))
    seen=[]; original=printpath._mesh_slice_contours_arrays
    def counted(V,F,*args,**kwargs):
        seen.append(len(F)); return original(V,F,*args,**kwargs)
    monkeypatch.setattr(printpath,"_mesh_slice_contours_arrays",counted)
    got=printpath.mesh_slice_stack(mesh,layer_mm=1,px_per_mm=10)
    assert np.array_equal(got,np.asarray(old))
    assert sum(seen) < 6*len(mesh[1])


def _old_film_core(px,lut,grid,tol):
    B=px.shape[1]; sse=np.maximum(np.sum(px*px,axis=1)[:,None]-2*px@lut.T+np.sum(lut*lut,axis=1),0)
    rm=np.sqrt(sse/B); j=np.argmin(rm,axis=1); jj=np.clip(j,1,len(grid)-2); rows=np.arange(len(j))
    a,b,c=rm[rows,jj-1],rm[rows,jj],rm[rows,jj+1]; den=a-2*b+c
    off=np.where((den>1e-300)&(j==jj),.5*(a-c)/np.where(den>1e-300,den,1),0)
    thick=np.where(j==jj,grid[jj]+np.clip(off,-.5,.5)*(grid[1]-grid[0]),grid[j])
    best=rm[rows,j]; left=np.c_[np.full(len(j),np.inf),rm[:,:-1]]; right=np.c_[rm[:,1:],np.full(len(j),np.inf)]
    return thick,best,np.sum((rm<=left)&(rm<right)&(rm<=best[:,None]+tol),axis=1)


def test_film_sse_search_matches_old_rmse_search_including_near_tie():
    lam=np.arange(420.,701.,40.); grid=np.arange(0.,801.,1.)
    lut=filmoptics._model_lut(lam,"SIO2","SI",(),grid,0,0,1,0,"t")
    px=np.vstack([lut[137],np.nextafter((lut[250]+lut[500])/2,np.inf)])
    old=_old_film_core(px,lut,grid,.01)
    cube=px.T.reshape(len(lam),1,2)
    got=filmoptics.film_thickness_map(cube,lam,"SIO2","SI",0,800,step_nm=1,ambiguity_rms=.01)
    assert np.allclose(got["thickness"].ravel(),old[0],rtol=0,atol=1e-12)
    assert np.allclose(got["rmse"].ravel(),old[1],rtol=0,atol=1e-12)
    assert np.array_equal(got["n_candidates"].ravel(),old[2])


def test_fractional_peak_reuses_argmax_and_centroid_skips_it(monkeypatch):
    cube=np.array([[[0.,2.,1.,0.],[1.,1.,1.,1.]]])
    original=photoncount.np.argmax; calls=0
    def counted(*a,**k):
        nonlocal calls; calls+=1; return original(*a,**k)
    monkeypatch.setattr(photoncount.np,"argmax",counted)
    photoncount.dtof_cube_depth(cube,mode="parabolic",min_counts=0)
    assert calls == 1
    calls=0; photoncount.dtof_cube_depth(cube,mode="centroid",min_counts=0)
    assert calls == 0


def _old_istft(t):
    spec=t["spectra"]; w=t["window_values"]; L=t["win"]; h=t["hop"]
    starts=np.arange(0,t["padded"]-L+1,h); frames=np.fft.irfft(spec.T/t["scale"],n=t["nfft"],axis=1)[:,:L]
    acc=np.zeros(t["padded"]); den=np.zeros(t["padded"])
    for i,s in enumerate(starts): acc[s:s+L]+=frames[i]*w; den[s:s+L]+=w*w
    sl=slice(t["pad_left"],t["pad_left"]+t["length"])
    return acc[sl]/den[sl]


@pytest.mark.parametrize("win,hop,n", [(64,32,1000),(63,17,1000),(64,21,20)])
def test_istft_periodic_normalization_matches_old(win,hop,n):
    x=np.random.default_rng(win+hop).normal(size=n); t=acoustics.stft(x,rate=48000,win=win,hop=hop)
    assert np.allclose(acoustics.istft(t),_old_istft(t),rtol=0,atol=1e-12)


def test_spectral_integral_table_matches_old_random_bands():
    rng=np.random.default_rng(43); x=np.sort(rng.uniform(400,900,500)); x[[0,-1]]=[400,900]
    curve=np.c_[x,np.sin(x/70)**2+.1]; table=spectralrad.spectral_integral_table(curve)
    endpoints=np.r_[x,rng.uniform(400,900,400)]
    for a,b in endpoints.reshape(-1,2):
        lo,hi=sorted((a,b))
        if hi>lo: assert table["integrate"](lo,hi)==pytest.approx(spectralrad.spectral_integral(curve,lo,hi),abs=1e-12)
    with pytest.raises(ValueError): table["integrate"](399,500)
