# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""CT projection kernels shared by every scan geometry, on numpy or on a GPU.

:mod:`tomography` is the fail-closed, numpy-only parallel-beam library and it stays
exactly that. This module holds the one thing the scan geometries of :mod:`ctscan`
have in common and the GPU routes of the parallel-beam operators:

    forward_project(volume, geometry)      ray-driven line integrals, A
    adjoint_project(projections, geometry)  the exact transpose of that A
    voxel_backproject(filtered, geometry)   voxel-driven back-projection for FBP/FDK

A *geometry* is the plain dict that :func:`ctscan.ct_scan_geometry` builds: per view,
a source (or a ray direction), a detector centre and two detector axes. Nothing here
knows what a helix or a laminography tilt is. A new scan is a new geometry and a new
weight, never a new kernel.

**Why three kernels and not two.** The pair ``forward_project`` and
``adjoint_project`` is matched to rounding: ``<Ax, y> = <x, A^T y>``. An iterative
solver needs that, otherwise it converges to something that is not a least-squares
solution. ``voxel_backproject`` is what filtered back-projection needs instead: it
evaluates the filtered projection at the point where a voxel lands on the detector,
which is the discretised inversion formula. It is not the transpose of ``A`` and is
not used as one.

**The interpolation is the definition in** :mod:`tomography`. Rays are sampled at a
uniform step inside the sphere around the volume, trilinearly, with each corner
outside the volume counting zero, and the sum is multiplied by the step. For a
parallel geometry with one slice this is exactly ``tomography._project`` and the
back-projection is exactly ``tomography._backproject``, which is what the parity
figures in ``docs/perf/gpu_ct_2026-11-02.md`` measure.

**GPU routes.** :func:`radon_transform`, :func:`backproject_sinogram`,
:func:`filtered_backprojection`, :func:`sart_reconstruct`, :func:`radon_volume` and
:func:`fbp_volume` take the same arguments as their namesakes in :mod:`tomography`
plus ``device``. The CPU case calls the namesake, so a host without CUDA gets the
existing result bit for bit. The GPU case runs in single precision and splits the
work to fit the free VRAM. Sizes above the host-memory caps of :mod:`tomography`
are accepted on the GPU route only, because those caps exist for the float64 route.
"""
from __future__ import annotations

import importlib.util
import os
from concurrent.futures import ThreadPoolExecutor

import numpy as np

import tomography as _tomo

__all__ = [
    "resolve_device", "forward_project", "adjoint_project", "voxel_backproject",
    "filter_rows", "gpu_memory_peak_bytes", "reset_gpu_memory_peak",
    "radon_transform", "backproject_sinogram", "filtered_backprojection",
    "sart_reconstruct", "radon_volume", "fbp_volume", "parallel_slice_geometry",
]

#: Bytes one trilinear ray sample costs at its peak (coordinates, fractions, indices).
BYTES_PER_RAY_SAMPLE = 64

#: Bytes one bilinear detector sample costs at its peak during back-projection.
BYTES_PER_VOXEL_SAMPLE = 110

#: Fraction of the free VRAM a kernel may plan to use.
VRAM_FRACTION = 0.6

#: Samples in one numpy batch. Keeps the CPU route below about 1.5 GB of temporaries.
CPU_BATCH_SAMPLES = 20_000_000

#: Worker threads of the numpy route. The kernels spend their time inside numpy, which
#: releases the GIL, so threads scale here.
CPU_THREADS = max(1, min(8, (os.cpu_count() or 1)))


def resolve_device(device="auto") -> str:
    """Resolve ``"auto"`` to ``"cuda"`` or ``"cpu"``; ``FULLSEYE_DEVICE`` overrides.

    The same contract as :func:`api.resolve_device`, kept here so that this module
    does not import the facade. An explicit ``"cuda"`` on a host without CUDA is
    refused with the reason instead of quietly running on the CPU.
    """
    requested = str(os.environ.get("FULLSEYE_DEVICE", device)).strip().lower()
    if requested not in ("auto", "cpu", "cuda"):
        raise ValueError("device must be 'auto', 'cpu' or 'cuda', got %r" % (requested,))
    if requested == "cpu":
        return "cpu"
    available = False
    why = "torch is not installed"
    if importlib.util.find_spec("torch") is not None:
        import torch
        available = bool(torch.cuda.is_available())
        why = "torch %s: torch.cuda.is_available() is False" % torch.__version__
    if requested == "cuda" and not available:
        raise RuntimeError("device='cuda' requested but CUDA is not available here (%s)"
                           % why)
    return "cuda" if available else "cpu"


class _Numpy:
    """The kernels' array vocabulary on numpy (float64)."""

    name = "cpu"

    def __init__(self):
        self.real = np.float64

    def asarray(self, a):
        return np.asarray(a, dtype=self.real)

    def host(self, a):
        return np.asarray(a)

    def zeros(self, shape):
        return np.zeros(shape, dtype=self.real)

    def arange(self, a, b):
        return np.arange(a, b, dtype=self.real)

    def to_int(self, a):
        return a.astype(np.int64)

    def add_at(self, dst, idx, val):
        np.add.at(dst, idx, val)

    def expand(self, a, like):
        return np.broadcast_to(a, like.shape)

    def ravel(self, a):
        return a.ravel()

    def sample_budget(self, per_sample):
        return CPU_BATCH_SAMPLES

    def fits(self, n_bytes):
        return True

    def rfft(self, a, n):
        return np.fft.rfft(a, n=n, axis=-1)

    def irfft(self, a, n):
        return np.fft.irfft(a, n=n, axis=-1)


class _Torch:
    """The same vocabulary on a CUDA tensor (float32 unless ``double``)."""

    name = "cuda"

    def __init__(self, double=False):
        import torch
        self.torch = torch
        self.real = torch.float64 if double else torch.float32
        self.device = torch.device("cuda")

    def asarray(self, a):
        if self.torch.is_tensor(a):
            return a.to(self.device, dtype=self.real)
        return self.torch.as_tensor(np.asarray(a), device=self.device, dtype=self.real)

    def host(self, a):
        self.torch.cuda.synchronize()
        return a.detach().cpu().numpy()

    def zeros(self, shape):
        return self.torch.zeros(shape, dtype=self.real, device=self.device)

    def arange(self, a, b):
        return self.torch.arange(a, b, dtype=self.real, device=self.device)

    def to_int(self, a):
        return a.long()

    def add_at(self, dst, idx, val):
        dst.index_add_(0, idx, val)

    def expand(self, a, like):
        return a.expand_as(like)

    def ravel(self, a):
        return a.reshape(-1)

    def free_bytes(self):
        """Free VRAM, counting what torch has reserved but is not using."""
        cuda = self.torch.cuda
        return int(cuda.mem_get_info()[0]) + int(cuda.memory_reserved() - cuda.memory_allocated())

    def sample_budget(self, per_sample):
        return max(1_000_000, int(self.free_bytes() * VRAM_FRACTION / per_sample))

    def fits(self, n_bytes):
        return n_bytes < self.free_bytes() * VRAM_FRACTION

    def rfft(self, a, n):
        return self.torch.fft.rfft(a, n=n, dim=-1)

    def irfft(self, a, n):
        return self.torch.fft.irfft(a, n=n, dim=-1)


def _backend(device, double=False):
    return _Numpy() if resolve_device(device) == "cpu" else _Torch(double)


def gpu_memory_peak_bytes() -> int:
    """Peak VRAM allocated by this process since the last reset (0 without CUDA)."""
    if importlib.util.find_spec("torch") is None:
        return 0
    import torch
    return int(torch.cuda.max_memory_allocated()) if torch.cuda.is_available() else 0


def reset_gpu_memory_peak() -> None:
    """Restart the peak-VRAM counter (no-op without CUDA)."""
    if importlib.util.find_spec("torch") is None:
        return
    import torch
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()


def _floor(b, a):
    return b.torch.floor(a) if b.name == "cuda" else np.floor(a)


def _trilinear(b, vol, shape, x, y, z, planar):
    """Trilinear sample of the flattened *vol*; a corner outside counts zero."""
    nz, ny, nx = shape
    out = None
    for ix, iy, iz, w in _corners(b, x, y, z, planar):
        ok = (ix >= 0) & (ix < nx) & (iy >= 0) & (iy < ny) & (iz >= 0) & (iz < nz)
        idx = (iz * ny + iy) * nx + ix
        idx = idx * ok
        s = vol[idx] * w * ok
        out = s if out is None else out + s
    return out


def _corners(b, x, y, z, planar):
    """Yield ``(ix, iy, iz, weight)`` for each interpolation corner."""
    x0 = _floor(b, x)
    y0 = _floor(b, y)
    z0 = _floor(b, z)
    fx = x - x0
    fy = y - y0
    fz = z - z0
    ix0 = b.to_int(x0)
    iy0 = b.to_int(y0)
    iz0 = b.to_int(z0)
    for dz in (0,) if planar else (0, 1):
        wz = (fz if dz else 1.0 - fz) if not planar else 1.0
        for dy in (0, 1):
            wy = fy if dy else 1.0 - fy
            for dx in (0, 1):
                wx = fx if dx else 1.0 - fx
                yield ix0 + dx, iy0 + dy, iz0 + dz, wx * wy * wz


def _ray_grid(geom):
    """The uniform ray parameters: half-length around the volume and the step."""
    nz, ny, nx = geom["vol_shape"]
    voxel = geom["voxel"]
    radius = geom.get("ray_radius")
    if radius is None:
        radius = (0.5 * float(np.sqrt(nz * nz + ny * ny + nx * nx)) + 1.0) * voxel
    step = voxel / float(geom.get("oversample", 1))
    n_t = int(np.ceil(2.0 * radius / step)) + 1
    return radius, n_t


def _rays(b, geom, i, r0, r1):
    """Ray origins and unit directions of rows ``r0:r1`` of view *i*, physical units."""
    nu, nv = geom["n_u"], geom["n_v"]
    uu = (b.arange(0, nu) - geom["cu"]) * geom["du"]
    vv = (b.arange(r0, r1) - geom["cv"]) * geom["dv"]
    uu = uu[None, :]
    vv = vv[:, None]
    c = geom["det_center"][i]
    u = geom["det_u"][i]
    v = geom["det_v"][i]
    if geom["beam"] == "parallel":
        d = geom["source"][i]
        ox = c[0] + uu * u[0] + vv * v[0]
        oy = c[1] + uu * u[1] + vv * v[1]
        oz = c[2] + uu * u[2] + vv * v[2]
        return ox, oy, oz, float(d[0]), float(d[1]), float(d[2])
    s = geom["source"][i]
    if geom["detector"] == "arc":
        dsd = geom["dsd"]
        n = (c - s) / np.linalg.norm(c - s)
        lib = b.torch if b.name == "cuda" else np
        gamma = uu / dsd
        cg = lib.cos(gamma) * dsd
        sg = lib.sin(gamma) * dsd
        dx = cg * n[0] + sg * u[0] + vv * v[0]
        dy = cg * n[1] + sg * u[1] + vv * v[1]
        dz = cg * n[2] + sg * u[2] + vv * v[2]
    else:
        dx = (c[0] - s[0]) + uu * u[0] + vv * v[0]
        dy = (c[1] - s[1]) + uu * u[1] + vv * v[1]
        dz = (c[2] - s[2]) + uu * u[2] + vv * v[2]
    norm = (dx * dx + dy * dy + dz * dz) ** 0.5
    return float(s[0]), float(s[1]), float(s[2]), dx / norm, dy / norm, dz / norm


def _sample_points(b, geom, i, r0, r1, t, radius):
    """Volume-index coordinates of the samples of rays that meet the sphere around it.

    A ray that misses the sphere of *radius* around the volume integrates to zero, so it
    is dropped here. On a detector wider than the object that is most of the work.
    Returns ``(x, y, z, keep)`` with ``x`` of shape ``(kept rays, samples)`` and ``keep``
    the ``(rows, columns)`` mask of those rays.
    """
    ox, oy, oz, dx, dy, dz = _rays(b, geom, i, r0, r1)
    t0 = -(ox * dx + oy * dy + oz * dz)
    keep = ox * ox + oy * oy + oz * oz - t0 * t0 <= radius * radius

    def pick(a):
        return a[keep][:, None] if hasattr(a, "shape") else a

    voxel = geom["voxel"]
    nz, ny, nx = geom["vol_shape"]
    tt = pick(t0) + t[None, :]

    def axis(o, d, n):
        return (pick(o) + tt * pick(d)) / voxel + (n - 1) / 2.0

    return axis(ox, dx, nx), axis(oy, dy, ny), axis(oz, dz, nz), keep


def _row_batches(geom, n_t, budget):
    rows = max(1, int(budget // max(1, n_t * geom["n_u"])))
    return [(r, min(r + rows, geom["n_v"])) for r in range(0, geom["n_v"], rows)]


def _views(geom, views):
    return np.arange(geom["n_views"]) if views is None else np.asarray(views, dtype=np.int64)


def forward_project(volume, geometry, views=None, device="auto", double=False):
    """Ray-driven projection: ``(Z, Y, X)`` volume to ``(views, V, U)`` line integrals.

    :param volume: real volume of the geometry's ``vol_shape``.
    :param geometry: dict from :func:`ctscan.ct_scan_geometry`.
    :param views: view indices to project; ``None`` means all of them.
    :param device: ``"auto"``, ``"cpu"`` or ``"cuda"``.
    :param double: use float64 on the GPU (the CPU route always is).
    :returns: float array of shape ``(len(views), n_v, n_u)``.
    """
    b = _backend(device, double)
    return b.host(_forward(b, volume, geometry, views))


def _forward(b, volume, geom, views=None):
    idx = _views(geom, views)
    vol = b.ravel(b.asarray(volume))
    shape = tuple(geom["vol_shape"])
    radius, n_t = _ray_grid(geom)
    dt = 2.0 * radius / (n_t - 1)
    t = b.arange(0, n_t) * dt - radius
    batches = _row_batches(geom, n_t, b.sample_budget(BYTES_PER_RAY_SAMPLE))
    out = b.zeros((idx.size, geom["n_v"], geom["n_u"]))
    planar = bool(geom.get("planar", False))

    use_grid = b.name == "cuda" and not planar and min(shape) > 1
    vol5 = vol.reshape((1, 1) + shape) if use_grid else None

    def one_view(k):
        for r0, r1 in batches:
            x, y, z, keep = _sample_points(b, geom, int(idx[k]), r0, r1, t, radius)
            if x.shape[0] == 0:
                continue
            if use_grid:
                val = _grid_trilinear(b, vol5, shape, x, y, z)
            else:
                val = _trilinear(b, vol, shape, x, y, z, planar)
            row = out[k, r0:r1]
            row[keep] = val.sum(-1) * dt

    _for_each(b, range(idx.size), one_view)
    return out


def _grid_trilinear(b, vol5, shape, x, y, z):
    """The same trilinear rule as :func:`_trilinear`, by the GPU's grid sampler."""
    nz, ny, nx = shape
    grid = b.torch.stack([x * (2.0 / (nx - 1)) - 1.0, y * (2.0 / (ny - 1)) - 1.0,
                          z * (2.0 / (nz - 1)) - 1.0], dim=-1)
    out = b.torch.nn.functional.grid_sample(vol5, grid[None, None], mode="bilinear",
                                            padding_mode="zeros", align_corners=True)
    return out[0, 0, 0]


def _for_each(b, items, fn):
    """Run ``fn(item)`` for each item: threaded on numpy, in order on a GPU."""
    items = list(items)
    if b.name == "cpu" and len(items) > 1 and CPU_THREADS > 1:
        with ThreadPoolExecutor(CPU_THREADS) as pool:
            list(pool.map(fn, items))
    else:
        for item in items:
            fn(item)


def adjoint_project(projections, geometry, views=None, device="auto", double=False):
    """The exact transpose of :func:`forward_project`.

    :param projections: array of shape ``(len(views), n_v, n_u)``.
    :param geometry: dict from :func:`ctscan.ct_scan_geometry`.
    :param views: view indices the rows of *projections* stand for.
    :param device: ``"auto"``, ``"cpu"`` or ``"cuda"``.
    :param double: use float64 on the GPU.
    :returns: float volume of the geometry's ``vol_shape``.
    """
    b = _backend(device, double)
    return b.host(_adjoint(b, projections, geometry, views))


def _adjoint(b, projections, geom, views=None):
    idx = _views(geom, views)
    proj = b.asarray(projections)
    shape = tuple(geom["vol_shape"])
    nz, ny, nx = shape
    radius, n_t = _ray_grid(geom)
    dt = 2.0 * radius / (n_t - 1)
    t = b.arange(0, n_t) * dt - radius
    batches = _row_batches(geom, n_t, b.sample_budget(BYTES_PER_RAY_SAMPLE))
    planar = bool(geom.get("planar", False))
    n_groups = CPU_THREADS if b.name == "cpu" else 1
    parts = [None] * n_groups     # slot g: the sum must not depend on thread finishing order

    def one_group(g):
        acc = b.zeros((nz * ny * nx,))
        for k in range(g, idx.size, n_groups):
            for r0, r1 in batches:
                x, y, z, keep = _sample_points(b, geom, int(idx[k]), r0, r1, t, radius)
                if x.shape[0] == 0:
                    continue
                inside = ((x > -1.0) & (x < nx) & (y > -1.0) & (y < ny)
                          & (z > -1.0) & (z < nz))
                val = b.expand(proj[k, r0:r1][keep][:, None] * dt, x)[inside]
                x, y, z = x[inside], y[inside], z[inside]
                for ix, iy, iz, w in _corners(b, x, y, z, planar):
                    ok = (ix >= 0) & (ix < nx) & (iy >= 0) & (iy < ny) & (iz >= 0) & (iz < nz)
                    sel = ((iz[ok] * ny + iy[ok]) * nx + ix[ok])
                    b.add_at(acc, sel, (val * w)[ok])
        parts[g] = acc

    _for_each(b, range(n_groups), one_group)
    out = parts[0]
    for acc in parts[1:]:
        out = out + acc
    return out.reshape(shape)


def _detector_plane(geom, idx):
    """Per view, the coefficients of the linear map from a point to the detector."""
    s = geom["source"][idx]
    c = geom["det_center"][idx]
    u = geom["det_u"][idx]
    v = geom["det_v"][idx]
    if geom["beam"] == "parallel":
        return {"u": u, "v": v, "u0": -np.sum(c * u, axis=1), "v0": -np.sum(c * v, axis=1)}
    n = np.cross(u, v)
    n /= np.linalg.norm(n, axis=1, keepdims=True)
    flip = np.sum(n * (c - s), axis=1) < 0.0
    n[flip] = -n[flip]
    return {"u": u, "v": v, "n": n, "s": s,
            "dsd": np.sum((c - s) * n, axis=1),
            "u0": np.sum((s - c) * u, axis=1), "v0": np.sum((s - c) * v, axis=1)}


def _bilinear_views(b, q, nv, nu, view, iu, iv, strict_u):
    """Bilinear sample of the stack *q* at ``(view, iv, iu)``; outside counts zero."""
    u0 = _floor(b, iu)
    v0 = _floor(b, iv)
    fu = iu - u0
    fv = iv - v0
    ju = b.to_int(u0)
    jv = b.to_int(v0)
    out = 0.0
    for dv in (0, 1):
        wv = fv if dv else 1.0 - fv
        for du in (0, 1):
            wu = fu if du else 1.0 - fu
            ku = ju + du
            kv = jv + dv
            ok = (ku >= 0) & (ku < nu) & (kv >= 0) & (kv < nv)
            if strict_u:
                ok = ok & (ju >= 0) & (ju + 1 < nu)
            ind = (view * nv + kv) * nu + ku
            out = out + q[ind * ok] * wu * wv * ok
    return out


def voxel_backproject(filtered, geometry, view_weight=None, device="auto",
                      normalize=None, strict_u=False, double=False):
    """Voxel-driven back-projection: each voxel reads the detector where it lands.

    :param filtered: ``(views, V, U)`` projections, already filtered and weighted.
    :param geometry: dict from :func:`ctscan.ct_scan_geometry`.
    :param view_weight: per-view ``d(beta)`` in radians; ``None`` means 1.
    :param device: ``"auto"``, ``"cpu"`` or ``"cuda"``.
    :param normalize: optional callable ``normalize(v_index_array)`` returning a
        per-sample weight. When given, the result is the weighted mean over views
        (the helical rule), scaled by ``pi``.
    :param strict_u: the detector-edge rule of :func:`tomography._backproject`
        (the voxel counts zero unless both neighbouring bins exist).
    :param double: use float64 on the GPU.
    :returns: float volume of the geometry's ``vol_shape``.
    """
    b = _backend(device, double)
    return b.host(_voxel_backproject(b, filtered, geometry, view_weight, normalize,
                                     strict_u))


def _voxel_backproject(b, filtered, geom, view_weight, normalize, strict_u):
    nz, ny, nx = geom["vol_shape"]
    nv, nu = geom["n_v"], geom["n_u"]
    n_views = geom["n_views"]
    voxel = geom["voxel"]
    du, dv, cu, cv = geom["du"], geom["dv"], geom["cu"], geom["cv"]
    arc = geom["detector"] == "arc"
    parallel = geom["beam"] == "parallel"
    dsd = geom.get("dsd")
    dso = geom.get("dso")
    weights = np.ones(n_views) if view_weight is None else np.asarray(view_weight, float)
    host = np.asarray(filtered) if not _is_tensor(filtered) else filtered
    n_bytes = n_views * nv * nu * 8
    resident = b.fits(n_bytes)
    q_all = b.asarray(host) if resident else None
    use_grid = b.name == "cuda" and not strict_u and nv > 1 and nu > 1

    budget = b.sample_budget(BYTES_PER_VOXEL_SAMPLE)
    per_view_slice = ny * nx
    slab = max(1, min(nz, int(budget // (per_view_slice * 8))))
    if b.name == "cpu":
        slab = min(slab, max(1, int(np.ceil(nz / CPU_THREADS))))
    batch = max(1, int(budget // (per_view_slice * slab)))
    xs = (b.arange(0, nx) - (nx - 1) / 2.0)[None, None, None, :] * voxel
    ys = (b.arange(0, ny) - (ny - 1) / 2.0)[None, None, :, None] * voxel
    out = b.zeros((nz, ny, nx))
    den = b.zeros((nz, ny, nx)) if normalize is not None else None

    def one_slab(z0):
        z1 = min(z0 + slab, nz)
        zs = (b.arange(z0, z1) - (nz - 1) / 2.0)[None, :, None, None] * voxel
        for v0 in range(0, n_views, batch):
            idx = np.arange(v0, min(v0 + batch, n_views))
            co = _detector_plane(geom, idx)
            shape1 = (idx.size, 1, 1, 1)

            def coef(a):
                return b.asarray(a).reshape(shape1)

            if parallel:
                pu = (coef(co["u"][:, 0]) * xs + coef(co["u"][:, 1]) * ys
                      + coef(co["u"][:, 2]) * zs + coef(co["u0"]))
                pv = (coef(co["v"][:, 0]) * xs + coef(co["v"][:, 1]) * ys
                      + coef(co["v"][:, 2]) * zs + coef(co["v0"]))
                wbp = 1.0
            else:
                wx = xs - coef(co["s"][:, 0])
                wy = ys - coef(co["s"][:, 1])
                wz = zs - coef(co["s"][:, 2])
                depth = (wx * coef(co["n"][:, 0]) + wy * coef(co["n"][:, 1])
                         + wz * coef(co["n"][:, 2]))
                scale = coef(co["dsd"]) / depth
                pu = (wx * coef(co["u"][:, 0]) + wy * coef(co["u"][:, 1])
                      + wz * coef(co["u"][:, 2])) * scale + coef(co["u0"])
                pv = (wx * coef(co["v"][:, 0]) + wy * coef(co["v"][:, 1])
                      + wz * coef(co["v"][:, 2])) * scale + coef(co["v0"])
                if arc:
                    lib = b.torch if b.name == "cuda" else np
                    gamma = lib.arctan(pu / dsd)
                    cg = lib.cos(gamma)
                    wbp = (dso / depth) ** 2 * cg * cg
                    pu = gamma * dsd
                    pv = pv * cg
                else:
                    wbp = (dso / depth) ** 2
            iu = pu / du + cu
            iv = pv / dv + cv
            del pu, pv
            lo, hi = int(idx[0]), int(idx[-1]) + 1
            q = q_all[lo:hi] if resident else b.asarray(host[lo:hi])
            if use_grid:
                s = _grid_bilinear(b, q, iu, iv, nu, nv)
            else:
                view = b.to_int(b.asarray(idx - lo).reshape(shape1))
                s = _bilinear_views(b, b.ravel(q), nv, nu, view, iu, iv, strict_u)
            dw = coef(weights[idx])
            if normalize is None:
                out[z0:z1] += (s * wbp * dw).sum(0)
            else:
                nw = normalize(iv)
                inside = (iu >= 0.0) & (iu <= nu - 1.0)
                nw = nw * inside
                out[z0:z1] += (s * wbp * nw * dw).sum(0)
                den[z0:z1] += (nw * dw).sum(0)

    _for_each(b, range(0, nz, slab), one_slab)
    if den is None:
        return out
    return out * np.pi / (den + 1e-6)


def _grid_bilinear(b, q, iu, iv, nu, nv):
    """Bilinear lookup of ``(B, V, U)`` at ``(B, Z, Y, X)``, by the GPU's grid sampler."""
    bb, zc, ny, nx = iu.shape
    grid = b.torch.stack([iu * (2.0 / (nu - 1)) - 1.0, iv * (2.0 / (nv - 1)) - 1.0], dim=-1)
    grid = grid.reshape(bb, zc * ny, nx, 2)
    out = b.torch.nn.functional.grid_sample(q[:, None], grid, mode="bilinear",
                                            padding_mode="zeros", align_corners=True)
    return out.reshape(bb, zc, ny, nx)


def _is_tensor(a):
    return type(a).__module__.startswith("torch")


def _filter_spectrum(n_pad, kind, cutoff, d_gamma):
    """The ramp spectrum, with the equiangular correction when *d_gamma* is given."""
    h = _tomo._ramp_filter(n_pad, kind, cutoff)
    if d_gamma is None:
        return h
    kernel = np.fft.irfft(h, n=n_pad)
    n = np.arange(n_pad, dtype=np.float64)
    n[n > n_pad // 2] -= n_pad
    gamma = n * d_gamma
    with np.errstate(divide="ignore", invalid="ignore"):
        corr = np.where(n == 0.0, 1.0, (gamma / np.sin(gamma)) ** 2)
    return np.real(np.fft.rfft(kernel * corr))


def filter_rows(stack, kind="ramp", cutoff=1.0, d_gamma=None, device="auto", double=False):
    """Ramp-filter ``(..., U)`` along ``U`` with unit pitch, zero-padded to twice ``U``.

    :param stack: real array whose last axis is the detector ``u`` axis.
    :param kind: one of :data:`tomography.FILTERS` except ``"none"``.
    :param cutoff: fraction of Nyquist to keep, in ``(0, 1]``.
    :param d_gamma: angular pitch of an equiangular detector, in radians; ``None``
        for a flat detector.
    :param device: ``"auto"``, ``"cpu"`` or ``"cuda"``.
    :param double: use float64 on the GPU.
    :returns: array of the same shape.
    """
    b = _backend(device, double)
    return b.host(_filter_rows(b, stack, kind, cutoff, d_gamma))


def _filter_rows(b, stack, kind, cutoff, d_gamma):
    nu = stack.shape[-1]
    n_pad = 1
    while n_pad < 2 * nu:
        n_pad <<= 1
    h = b.asarray(_filter_spectrum(n_pad, kind, cutoff, d_gamma))
    bytes_per_row = 3 * n_pad * 4
    n_rows = int(np.prod(stack.shape[:-1]))
    head = stack.reshape(-1, nu)
    if b.fits(n_rows * bytes_per_row):
        spec = b.rfft(b.asarray(head), n_pad) * h
        return b.irfft(spec, n_pad)[..., :nu].reshape(stack.shape)
    per = max(1, int(b.sample_budget(bytes_per_row)))
    out = np.empty((n_rows, nu), dtype=head.dtype)
    for r in range(0, n_rows, per):
        spec = b.rfft(b.asarray(head[r:r + per]), n_pad) * h
        out[r:r + per] = b.host(b.irfft(spec, n_pad)[..., :nu])
    return out.reshape(stack.shape)


# --------------------------------------------------------------------------- #
# the parallel-beam operators of tomography.py, on the same kernels            #
# --------------------------------------------------------------------------- #
def parallel_slice_geometry(angles_deg, n_detectors, size, n_slices=1):
    """A stack of independent parallel-beam slices, in :mod:`tomography` conventions.

    Unit detector pitch and unit voxel, the axis of rotation on bin
    ``(n_detectors-1)/2``, and the rays in the plane of each slice. The ray radius is
    the in-plane one of ``tomography._project``, so the samples coincide.
    """
    rad = np.deg2rad(np.asarray(angles_deg, dtype=np.float64))
    ca, sa = np.cos(rad), np.sin(rad)
    zero = np.zeros_like(ca)
    h, w = (size, size) if np.isscalar(size) else size
    return {
        "beam": "parallel", "detector": "flat", "vol_shape": (n_slices, h, w), "voxel": 1.0,
        "n_views": rad.size, "n_v": n_slices, "n_u": int(n_detectors),
        "du": 1.0, "dv": 1.0, "cu": (n_detectors - 1) / 2.0, "cv": (n_slices - 1) / 2.0,
        "source": np.stack([-sa, ca, zero], axis=1),
        "det_center": np.zeros((rad.size, 3)),
        "det_u": np.stack([ca, sa, zero], axis=1),
        "det_v": np.tile(np.array([0.0, 0.0, 1.0]), (rad.size, 1)),
        "planar": True, "ray_radius": 0.5 * float(np.hypot(h, w)) + 1.0,
    }


def _default_angles(angles_deg, op):
    if angles_deg is None:
        return np.linspace(0.0, 180.0, 180, endpoint=False)
    return _tomo._as_angles(angles_deg, None, op)


def _fp_gpu(b, vol, ang, n_d, oversample):
    z, h, w = vol.shape
    geom = parallel_slice_geometry(ang, n_d, (h, w), z)
    geom["oversample"] = oversample
    return _forward(b, vol, geom)


def radon_transform(image, angles_deg=None, n_detectors=None, oversample=1, device="auto"):
    """:func:`tomography.radon_transform`, with the GPU route.

    :param device: ``"auto"`` (CUDA when available), ``"cpu"`` or ``"cuda"``.
    :returns: ``(n_angles, n_detectors)`` float sinogram.
    """
    if resolve_device(device) == "cpu":
        return _tomo.radon_transform(image, angles_deg, n_detectors, oversample)
    op = "radon_transform"
    img = _tomo._as_float_array(image, "image", 1 << 28, op)
    if img.ndim != 2 or min(img.shape) < 2:
        raise ValueError("%s: image must be 2-D and at least 2x2, got %r" % (op, img.shape))
    ang = _default_angles(angles_deg, op)
    n_d = (_tomo._default_detectors(*img.shape) if n_detectors is None
           else _tomo._count(n_detectors, "n_detectors", 4, _tomo.MAX_DETECTORS))
    ov = _tomo._count(oversample, "oversample", 1, 8)
    if n_d < np.hypot(*img.shape) - 1.0:
        raise ValueError("%s: %d detector bins do not cover the image diagonal"
                         % (op, n_d))
    b = _Torch()
    return b.host(_fp_gpu(b, img[None], ang, n_d, ov)[:, 0])


def radon_volume(volume, angles_deg=None, n_detectors=None, oversample=1, device="auto"):
    """:func:`tomography.radon_volume`, with the GPU route.

    :param device: ``"auto"`` (CUDA when available), ``"cpu"`` or ``"cuda"``.
    :returns: ``(Z, n_angles, n_detectors)`` float stack.
    """
    if resolve_device(device) == "cpu":
        return _tomo.radon_volume(volume, angles_deg, n_detectors, oversample)
    op = "radon_volume"
    vol = _tomo._as_float_array(volume, "volume", 1 << 32, op)
    if vol.ndim != 3 or min(vol.shape[1:]) < 2:
        raise ValueError("%s: volume must be (Z, H, W), got %r" % (op, vol.shape))
    _, h, w = vol.shape
    ang = _default_angles(angles_deg, op)
    n_d = (_tomo._default_detectors(h, w) if n_detectors is None
           else _tomo._count(n_detectors, "n_detectors", 4, _tomo.MAX_DETECTORS))
    ov = _tomo._count(oversample, "oversample", 1, 8)
    if n_d < np.hypot(h, w) - 1.0:
        raise ValueError("%s: %d detector bins do not cover the in-plane diagonal"
                         % (op, n_d))
    b = _Torch()
    return b.host(_fp_gpu(b, vol, ang, n_d, ov).permute(1, 0, 2))


def _bp_gpu(b, stack_av, ang, n_d, sz, kind, cut, d_theta):
    """``stack_av`` is ``(angles, slices, detectors)``."""
    work = stack_av if kind == "none" else _filter_rows(b, stack_av, kind, cut, None)
    geom = parallel_slice_geometry(ang, n_d, sz, stack_av.shape[1])
    weights = np.full(ang.size, d_theta)
    return _voxel_backproject(b, work, geom, weights, None, True)


def filtered_backprojection(sinogram, angles_deg=None, size=None, filter_name="ramp",
                            cutoff=1.0, span_deg=None, device="auto"):
    """:func:`tomography.filtered_backprojection`, with the GPU route.

    :param device: ``"auto"`` (CUDA when available), ``"cpu"`` or ``"cuda"``.
    :returns: ``(size, size)`` float image.
    """
    if resolve_device(device) == "cpu":
        return _tomo.filtered_backprojection(sinogram, angles_deg, size, filter_name,
                                             cutoff, span_deg)
    op = "filtered_backprojection"
    sino = _tomo._as_float_array(sinogram, "sinogram", 1 << 30, op)
    if sino.ndim != 2 or sino.shape[0] < 1 or sino.shape[1] < 4:
        raise ValueError("%s: sinogram must be (angles, detectors), got %r" % (op, sino.shape))
    ang = _tomo._as_angles(angles_deg, sino.shape[0], op)
    kind = _tomo._choice(filter_name, _tomo.FILTERS, "filter_name", op)
    cut = _tomo._finite_scalar(cutoff, "cutoff")
    if not 0.0 < cut <= 1.0:
        raise ValueError("%s: cutoff must be in (0, 1], got %g" % (op, cut))
    sz = _recon_size(size, sino.shape[1], op)
    d_theta = _tomo._span_weight(ang, span_deg, op)
    b = _Torch()
    return b.host(_bp_gpu(b, sino[:, None, :], ang, sino.shape[1], sz, kind, cut, d_theta)[0])


def backproject_sinogram(sinogram, angles_deg=None, size=None, span_deg=None, device="auto"):
    """:func:`tomography.backproject_sinogram`, with the GPU route.

    :param device: ``"auto"`` (CUDA when available), ``"cpu"`` or ``"cuda"``.
    :returns: ``(size, size)`` float image.
    """
    if resolve_device(device) == "cpu":
        return _tomo.backproject_sinogram(sinogram, angles_deg, size, span_deg)
    return filtered_backprojection(sinogram, angles_deg, size, "none", 1.0, span_deg, device)


def _recon_size(size, n_det, op):
    if size is None:
        n = int(np.floor(n_det / np.sqrt(2.0)))
        return n if n % 2 == 1 else n - 1
    return _tomo._count(size, "size", 2, 1 << 15)


def fbp_volume(stack, angles_deg=None, size=None, filter_name="ramp", cutoff=1.0,
               span_deg=None, device="auto"):
    """:func:`tomography.fbp_volume`, with the GPU route.

    :param device: ``"auto"`` (CUDA when available), ``"cpu"`` or ``"cuda"``.
    :returns: ``(Z, size, size)`` float volume.
    """
    if resolve_device(device) == "cpu":
        return _tomo.fbp_volume(stack, angles_deg, size, filter_name, cutoff, span_deg)
    op = "fbp_volume"
    st = _tomo._as_float_array(stack, "stack", 1 << 32, op)
    if st.ndim != 3 or st.shape[1] < 2 or st.shape[2] < 4:
        raise ValueError("%s: stack must be (slice, angle, detector), got %r" % (op, st.shape))
    z, n_a, n_d = st.shape
    ang = _tomo._as_angles(angles_deg, n_a, op)
    kind = _tomo._choice(filter_name, _tomo.FILTERS, "filter_name", op)
    cut = _tomo._finite_scalar(cutoff, "cutoff")
    if not 0.0 < cut <= 1.0:
        raise ValueError("%s: cutoff must be in (0, 1], got %g" % (op, cut))
    sz = _recon_size(size, n_d, op)
    d_theta = _tomo._span_weight(ang, span_deg, op)
    b = _Torch()
    return b.host(_bp_gpu(b, np.ascontiguousarray(st.transpose(1, 0, 2)), ang, n_d, sz,
                          kind, cut, d_theta))


def sart_reconstruct(sinogram, angles_deg=None, size=None, n_iter=10, relaxation=0.3,
                     initial=None, nonnegative=True, device="auto"):
    """:func:`tomography.sart_reconstruct`, with the GPU route.

    The update is the same row-action rule, view by view, with the same interpolation
    on both sides (ray-driven forward, voxel-driven back) and the same normalisers.

    :param device: ``"auto"`` (CUDA when available), ``"cpu"`` or ``"cuda"``.
    :returns: ``(size, size)`` float image.
    """
    if resolve_device(device) == "cpu":
        return _tomo.sart_reconstruct(sinogram, angles_deg, size, n_iter, relaxation,
                                      initial, nonnegative)
    op = "sart_reconstruct"
    sino = _tomo._as_sinogram(sinogram, op)
    ang = _tomo._as_angles(angles_deg, sino.shape[0], op)
    sz = _tomo._recon_size(size, sino, op)
    n_it = _tomo._count(n_iter, "n_iter", 1, 500)
    lam = _tomo._finite_scalar(relaxation, "relaxation")
    if not 0.0 < lam < 2.0:
        raise ValueError("%s: relaxation must be in (0, 2), got %g" % (op, lam))
    if not isinstance(nonnegative, (bool, np.bool_)):
        raise ValueError("%s: nonnegative must be a bool, got %r"
                         % (op, type(nonnegative).__name__))
    b = _Torch()
    n_det = sino.shape[1]
    geom = parallel_slice_geometry(ang, n_det, sz, 1)
    if initial is None:
        x = b.zeros((1, sz, sz))
    else:
        init = _tomo._as_image(initial, op, "initial")
        if init.shape != (sz, sz):
            raise ValueError("%s: initial has shape %r but the reconstruction is %dx%d"
                             % (op, init.shape, sz, sz))
        x = b.asarray(init[None])
    data = b.asarray(sino)
    eps = 1e-9
    rows = _forward(b, b.zeros((1, sz, sz)) + 1.0, geom)[:, 0]
    one_view = dict(geom)
    for _ in range(n_it):
        for i in range(ang.size):
            view = np.array([i])
            fp = _forward(b, x, one_view, view)[0, 0]
            resid = (data[i] - fp) / rows[i].clamp_min(eps)
            single = _single_view(geom, i)
            back = _voxel_backproject(b, resid[None, None, :], single, None, None, True)
            cols = _voxel_backproject(b, (resid * 0.0 + 1.0)[None, None, :], single, None,
                                      None, True).clamp_min(eps)
            x = x + lam * back / cols
        if nonnegative:
            x = x.clamp_min(0.0)
    return b.host(x[0])


def _single_view(geom, i):
    one = dict(geom)
    one["n_views"] = 1
    for key in ("source", "det_center", "det_u", "det_v"):
        one[key] = geom[key][i:i + 1]
    return one
