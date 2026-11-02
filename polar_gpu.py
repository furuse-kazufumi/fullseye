# -*- coding: utf-8 -*-
"""polar_gpu — 偏光の一括計算(torch): 光線 × 波長の Jones / Mueller と、実寸画像のバッチ。

二つの経路がある。

1. **実光線の偏光追跡** :func:`polarized_bundle`。``lens_gpu`` の追跡の各面で Fresnel 振幅を掛け、
   光線ごとの Jones 行列(入射の横基底 → 射出の横基底、(M, W, R, 2, 2))を作る。Chipman の偏光光線追跡と同じく
   3 次元の電場ベクトルで面を渡すので、光線が折れても基底の取り違えが起きない。振幅は
   ``|τ|² = T``(面の電力透過率)に規格化してあり、``|E|²`` がそのまま光線の電力になる。

   コートなしの誘電体界面で全反射の光線は無効なので、係数はすべて実数(リターダンスは生じない。
   二色性と基底の回転だけが残る)。鏡は完全導体(``E_t → −E_t``)で、``raytrace`` の鏡と同じく無損失。

2. **行列と画像のバッチ**: ``optics`` / ``photoelastic`` / ``sfpolar`` の画素ごとの計算を ``(B, H, W)`` で。

=================================  ==================================================
``jones_element_batch``            ``optics.jones_element``(配列引数)
``mueller_element_batch``          ``optics.mueller_element``(配列引数、部分偏光子を除く)
``chain``                          ``J_last @ ... @ J_first``
``stokes_from_jones_batch``        ``optics.stokes_from_jones``
``mueller_apply_batch``            ``optics.mueller_apply`` の場版(物理の検査も同じ)
``stokes_analyze_batch``           ``optics.stokes_analyze`` の画素版(None は NaN)
``polarization_demosaic_batch``    ``optics.polarization_demosaic``
``photoelastic_images_batch``      ``photoelastic.photoelastic_polarization_images``
``sfp_render_batch``               ``sfpolar.sfp_render``
``dolp_to_zenith_batch``           ``sfpolar.dolp_to_zenith`` の二分法
=================================  ==================================================

定義を足していない。効果の測定と不採用の判断は ``docs/perf/gpu_optics_2026-11-02.md``。
"""
from __future__ import annotations

import math

import numpy as np

import lens_gpu as LG
from torch_lazy import F, torch

__all__ = ["polarized_bundle", "jones_to_mueller", "jones_element_batch", "mueller_element_batch", "chain",
           "stokes_from_jones_batch", "mueller_apply_batch", "stokes_analyze_batch", "polarization_demosaic_batch",
           "photoelastic_images_batch", "sfp_render_batch", "dolp_to_zenith_batch"]

_JONES_KINDS = ("polarizer", "retarder", "quarter_wave", "half_wave", "rotator")
_MUELLER_KINDS = ("polarizer", "retarder", "quarter_wave", "half_wave", "rotator", "depolarizer")
_BISECT_ITERS = 64
_DUST = 1e-12


def _tens(a, device, dtype):
    return torch.as_tensor(a, dtype=LG._dtype(dtype) if isinstance(dtype, str) else dtype, device=LG._device(device))


# --------------------------------------------------------------------------- #
# 素子
# --------------------------------------------------------------------------- #
def jones_element_batch(kind, angle_deg=0.0, retardance_deg=90.0, device="cpu", dtype="float64"):
    """``(*shape, 2, 2)`` の複素 Jones 行列。式と規約は ``optics._jones_field``。"""
    if kind not in _JONES_KINDS:
        raise ValueError("jones_element_batch: unknown kind %r (choose from %s)" % (kind, "/".join(_JONES_KINDS)))
    a = torch.deg2rad(_tens(angle_deg, device, dtype))
    c, s = torch.cos(a), torch.sin(a)
    r = torch.stack((torch.stack((c, -s), -1), torch.stack((s, c), -1)), -2).to(torch.complex128 if a.dtype == torch.float64 else torch.complex64)
    if kind == "rotator":
        return r
    j0 = torch.zeros_like(r)
    if kind == "polarizer":
        j0[..., 0, 0] = 1.0
    else:
        d = torch.deg2rad(_tens(retardance_deg, device, dtype)) if kind == "retarder" else \
            torch.deg2rad(torch.full_like(a, {"quarter_wave": 90.0, "half_wave": 180.0}[kind]))
        d = d.expand_as(a) if d.ndim <= a.ndim else d
        r = r.expand(d.shape + (2, 2))
        j0 = torch.zeros_like(r)
        j0[..., 0, 0] = torch.polar(torch.ones_like(d), -0.5 * d)
        j0[..., 1, 1] = torch.polar(torch.ones_like(d), 0.5 * d)
    return r @ j0 @ r.transpose(-1, -2)


def mueller_element_batch(kind, angle_deg=0.0, retardance_deg=90.0, device="cpu", dtype="float64"):
    """``(*shape, 4, 4)`` の Mueller 行列。式は ``optics._mueller_field``。"""
    if kind not in _MUELLER_KINDS:
        raise ValueError("mueller_element_batch: unknown kind %r (choose from %s)" % (kind, "/".join(_MUELLER_KINDS)))
    a = torch.deg2rad(_tens(angle_deg, device, dtype))
    d = None
    if kind == "retarder":
        d = torch.deg2rad(_tens(retardance_deg, device, dtype))
        a, d = torch.broadcast_tensors(a, d)
    c, s = torch.cos(2.0 * a), torch.sin(2.0 * a)
    m = torch.zeros(a.shape + (4, 4), dtype=a.dtype, device=a.device)
    if kind == "depolarizer":
        m[..., 0, 0] = 1.0
    elif kind == "polarizer":
        m[..., 0, 0] = 0.5
        m[..., 0, 1] = m[..., 1, 0] = 0.5 * c
        m[..., 0, 2] = m[..., 2, 0] = 0.5 * s
        m[..., 1, 1] = 0.5 * c * c
        m[..., 1, 2] = m[..., 2, 1] = 0.5 * c * s
        m[..., 2, 2] = 0.5 * s * s
    elif kind == "rotator":
        m[..., 0, 0] = 1.0
        m[..., 1, 1] = c
        m[..., 1, 2] = -s
        m[..., 2, 1] = s
        m[..., 2, 2] = c
        m[..., 3, 3] = 1.0
    else:
        if d is None:
            d = torch.deg2rad(torch.full_like(a, {"quarter_wave": 90.0, "half_wave": 180.0}[kind]))
        cd, sd = torch.cos(d), torch.sin(d)
        m[..., 0, 0] = 1.0
        m[..., 1, 1] = c * c + s * s * cd
        m[..., 1, 2] = m[..., 2, 1] = c * s * (1.0 - cd)
        m[..., 1, 3] = -s * sd
        m[..., 2, 2] = s * s + c * c * cd
        m[..., 2, 3] = c * sd
        m[..., 3, 1] = s * sd
        m[..., 3, 2] = -c * sd
        m[..., 3, 3] = cd
    return m


def chain(matrices):
    """素子を光の順に受け取り ``M_last @ ... @ M_first`` を返す(形は放送する)。"""
    matrices = list(matrices)
    if not matrices:
        raise ValueError("chain: no matrices")
    out = matrices[0]
    for m in matrices[1:]:
        out = m @ out
    return out


def stokes_from_jones_batch(state):
    """``(..., 2)`` の Jones ベクトル → ``(..., 4)`` の Stokes。``optics.stokes_from_jones`` の式。"""
    ex, ey = state[..., 0], state[..., 1]
    a, b = ex.abs() ** 2, ey.abs() ** 2
    cross = ex * torch.conj(ey)
    return torch.stack((a + b, a - b, 2.0 * cross.real, 2.0 * cross.imag), -1)


def mueller_apply_batch(mueller, stokes):
    """``(..., 4, 4) × (..., 4)``。入力の物理の検査は ``optics.mueller_apply`` と同じで、1 点でも破れば全体を拒否。"""
    s0 = stokes[..., 0]
    pol = torch.sqrt(stokes[..., 1] ** 2 + stokes[..., 2] ** 2 + stokes[..., 3] ** 2)
    bad = (s0 < 0) | (pol > s0 * (1.0 + 1e-9) + 1e-12)
    n_bad = int(bad.sum())
    if n_bad:
        raise ValueError("mueller_apply_batch: %d of %d Stokes vectors are unphysical (S0 < 0 or DoP > 1)"
                         % (n_bad, s0.numel()))
    out = torch.einsum("...ij,...j->...i", mueller, stokes)
    if not bool(torch.isfinite(out).all()):
        raise ValueError("mueller_apply_batch: the result overflowed")
    return out


def stokes_analyze_batch(stokes):
    """``optics.stokes_analyze`` の画素版。未定義の角は NaN、``handedness`` は +1 / -1 / 0(right / left / linear)。

    S0 == 0 の画素は全部 NaN(スカラー版は例外、場では暗い画素が普通に在るので印で返す)。
    """
    s0, s1, s2, s3 = stokes[..., 0], stokes[..., 1], stokes[..., 2], stokes[..., 3]
    pol = torch.sqrt(s1 * s1 + s2 * s2 + s3 * s3)
    if bool(((s0 < 0) | (pol > s0 * (1.0 + 1e-9) + 1e-12)).any()):
        raise ValueError("stokes_analyze_batch: unphysical Stokes vectors in the field")
    nan = float("nan")
    dark = s0 == 0
    lin = torch.hypot(s1, s2)
    dust = _DUST * s0
    az = torch.rad2deg(0.5 * torch.atan2(s2, s1)) % 180.0
    az = torch.where(az >= 180.0, torch.zeros_like(az), az).masked_fill(~(lin > dust), nan)
    ell = torch.rad2deg(0.5 * torch.asin(torch.clamp(s3 / pol, -1.0, 1.0))).masked_fill(~(pol > dust), nan)
    hand = torch.where(s3.abs() <= dust, torch.zeros_like(s3), torch.sign(s3))
    return {"intensity": s0, "dop": torch.clamp(pol / s0, max=1.0).masked_fill(dark, nan),
            "dolp": torch.clamp(lin / s0, max=1.0).masked_fill(dark, nan),
            "docp": torch.clamp(s3.abs() / s0, max=1.0).masked_fill(dark, nan),
            "azimuth_deg": az, "ellipticity_deg": ell, "handedness": hand.masked_fill(dark, nan)}


# --------------------------------------------------------------------------- #
# 光線ごとの偏光
# --------------------------------------------------------------------------- #
def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _unit(a):
    n = torch.sqrt(_dot(a, a))
    return (a[0] / n, a[1] / n, a[2] / n)


def _transverse_basis(d):
    """伝搬方向 *d* に直交する基底 (e1, e2)。+z 付近で (x, y) に連続につながる(e2 = d × e1)。"""
    zero = torch.zeros_like(d[0])
    one = zero + 1.0
    y = (zero, one, zero)
    e1 = _unit(_cross(y, d))
    return e1, _cross(d, e1)


def polarized_bundle(lens, field=None, rings=6, pupil_fill=1.0, image_mm=None, absorption=False):
    """光線束を偏光つきで追う。返り値は ``lens_gpu.bundle_batch`` の鍵に加えて:

    ``jones`` (M, W, R, 2, 2)(実数): 入射の横基底 → 射出の横基底。``e_out`` は射出の基底の 3 次元ベクトル。
    ``T_s_product`` ``T_p_product``: 面ごとの s / p の電力透過率の積(診断用、基底は面ごとに変わる)。

    *absorption*: ``exp(-αd/2)`` を振幅に掛ける。カタログの Sellmeier 硝子は k のデータが無いので効かない。
    """
    state = {"E": None, "Ts": None, "Tp": None}
    alpha = lens.alpha[None, :, :]

    def visit(i, info):
        if i == lens.S:
            if absorption and bool(lens.alpha[:, i].any()):
                amp = torch.exp(-0.5 * alpha[..., i:i + 1] * torch.nan_to_num(info["t"]).abs() * 1e3)
                state["E"] = [tuple(c * amp for c in e) for e in state["E"]]
            return
        d_in = info["d_in"]
        if state["E"] is None:
            e1, e2 = _transverse_basis(d_in)
            state["E"] = [e1, e2]
            state["basis_in"] = (e1, e2)
            state["Ts"] = torch.ones_like(d_in[0])
            state["Tp"] = torch.ones_like(d_in[0])
        if absorption and bool(lens.alpha[:, i].any()):
            amp = torch.exp(-0.5 * alpha[..., i:i + 1] * torch.nan_to_num(info["t"]).abs() * 1e3)
            state["E"] = [tuple(c * amp for c in e) for e in state["E"]]
        nu = info["normal"]
        d_out = info["d_out"]
        # 理想レンズは法線で曲がらない(高さで曲がる)ので、基底は入射と射出の張る面から取る
        s = _cross(d_in, d_out) if info.get("ideal") else _cross(d_in, nu)
        sn = torch.sqrt(_dot(s, s))
        # 垂直入射は s / p の区別が無い(t_s = t_p)ので、任意の直交方向でよい
        fb = _transverse_basis(d_in)[0]
        near = sn < 1e-14
        s = tuple(torch.where(near, f, a / sn.clamp(min=1e-300)) for a, f in zip(s, fb))
        pi = _cross(d_in, s)
        if info["mirror"]:
            ts, tp = -torch.ones_like(sn), torch.ones_like(sn)
        elif info.get("ideal"):
            ts, tp = torch.ones_like(sn), torch.ones_like(sn)     # 損失なしの理想レンズ
        else:
            n1, n2, ci, ct = info["n1"], info["n2"], info["cos_i"], info["cos_t"]
            g = torch.sqrt((n2 * ct) / (n1 * ci))                 # 振幅に掛けて |τ|² = T にする
            ts = g * 2.0 * n1 * ci / (n1 * ci + n2 * ct)
            tp = g * 2.0 * n1 * ci / (n2 * ci + n1 * ct)
        po = _cross(d_out, s)
        state["Ts"] = state["Ts"] * ts * ts
        state["Tp"] = state["Tp"] * tp * tp
        new = []
        for E in state["E"]:
            es = _dot(E, s) * ts
            ep = _dot(E, pi) * tp
            new.append((es * s[0] + ep * po[0], es * s[1] + ep * po[1], es * s[2] + ep * po[2]))
        state["E"] = new

    b = LG.bundle_batch(lens, field=field, rings=rings, pupil_fill=pupil_fill, image_mm=image_mm, visitor=visit)
    d = (b["L"], b["M"], b["N"])
    o1, o2 = _transverse_basis(d)
    E1, E2 = state["E"]
    J = torch.stack((torch.stack((_dot(E1, o1), _dot(E2, o1)), -1), torch.stack((_dot(E1, o2), _dot(E2, o2)), -1)), -2)
    b.update({"jones": J, "e_out": (o1, o2), "E_out": (E1, E2), "T_s_product": state["Ts"], "T_p_product": state["Tp"]})
    return b


def jones_to_mueller(J):
    """Jones → Mueller ``M = A (J ⊗ J*) A⁻¹``(``optics.stokes_from_jones`` の規約)。``(..., 2, 2)`` → ``(..., 4, 4)``。"""
    Jc = J.to(torch.complex128 if J.dtype in (torch.float64, torch.complex128) else torch.complex64)
    A = torch.as_tensor([[1, 0, 0, 1], [1, 0, 0, -1], [0, 1, 1, 0], [0, -1j, 1j, 0]], dtype=Jc.dtype, device=Jc.device)
    kr = torch.einsum("...ij,...kl->...ikjl", Jc, torch.conj(Jc)).reshape(Jc.shape[:-2] + (4, 4))
    return (A @ kr @ torch.linalg.inv(A)).real


# --------------------------------------------------------------------------- #
# 画像
# --------------------------------------------------------------------------- #
def polarization_demosaic_batch(raw, layout=((90.0, 45.0), (135.0, 0.0)), device="cpu", dtype="float64"):
    """``(B, H, W)`` のモザイク → ``(B, 4, H, W)``。``optics.polarization_demosaic`` と同じ鏡映と核。"""
    a = _tens(raw, device, dtype)
    squeeze = a.ndim == 2
    if squeeze:
        a = a[None]
    if a.ndim != 3:
        raise ValueError("polarization_demosaic_batch: raw must be (B, H, W) or (H, W), got shape %r" % (tuple(a.shape),))
    if a.shape[-1] % 2 or a.shape[-2] % 2:
        raise ValueError("polarization_demosaic_batch: height and width must be even, got %r" % (tuple(a.shape[-2:]),))
    if not bool(torch.isfinite(a).all()):
        raise ValueError("polarization_demosaic_batch: raw contains non-finite values")
    lay = [[float(layout[r][c]) % 180.0 for c in range(2)] for r in range(2)]
    if sorted(v for row in lay for v in row) != [0.0, 45.0, 90.0, 135.0]:
        raise ValueError("polarization_demosaic_batch: layout must hold each of 0, 45, 90, 135 once, got %r" % (layout,))
    pad = F.pad(a[:, None], (2, 2, 2, 2), mode="reflect")
    H, W = pad.shape[-2:]
    planes = torch.zeros((a.shape[0], 4, H, W), dtype=a.dtype, device=a.device)
    for k, ang in enumerate((0.0, 45.0, 90.0, 135.0)):
        r, c = next((r, c) for r in range(2) for c in range(2) if lay[r][c] == ang)
        planes[:, k, r::2, c::2] = pad[:, 0, r::2, c::2]
    ker = torch.as_tensor([[1.0, 2.0, 1.0], [2.0, 4.0, 2.0], [1.0, 2.0, 1.0]], dtype=a.dtype, device=a.device) / 4.0
    out = F.conv2d(planes, ker[None, None].repeat(4, 1, 1, 1), groups=4)[..., 1:-1, 1:-1]
    return out[0] if squeeze else out


def photoelastic_images_batch(delta_rad, axis_deg=0.0, analyzers="camera4", intensity=1.0, device="cpu", dtype="float64"):
    """``photoelastic.photoelastic_polarization_images`` の ``(B, K, H, W)`` 版。

    行列を組まず閉形式の Stokes ``S' = I(1, −sin2θ sinδ, cos2θ sinδ, cosδ)`` で直接計算する(同じ式の結果)。
    """
    d = _tens(delta_rad, device, dtype)
    th = torch.deg2rad(_tens(axis_deg, device, d.dtype))
    d, th = torch.broadcast_tensors(d, th)
    if analyzers not in ("camera4", "stokes6"):
        raise ValueError("photoelastic_images_batch: analyzers must be camera4 or stokes6, got %r" % (analyzers,))
    sd, cd = torch.sin(d), torch.cos(d)
    c2, s2 = torch.cos(2.0 * th), torch.sin(2.0 * th)
    i0 = float(intensity)
    # S' = (S0 + S3 成分の位相子の作用)。_retarder_field の 3 列目 + 0 列目と同じ
    S0 = i0 * torch.ones_like(d)
    S1 = i0 * (-s2 * sd)
    S2 = i0 * (c2 * sd)
    S3 = i0 * cd
    fr = [0.5 * (S0 + S1), 0.5 * (S0 + S2), 0.5 * (S0 - S1), 0.5 * (S0 - S2)]
    if analyzers == "stokes6":
        fr += [0.5 * (S0 + S3), 0.5 * (S0 - S3)]
    return torch.clamp(torch.stack(fr, -3), min=0.0)


def _rho_specular(theta, n):
    s2 = torch.sin(theta) ** 2
    c = torch.cos(theta)
    root = torch.sqrt(torch.clamp(n * n - s2, min=0.0))
    return 2.0 * s2 * c * root / (n * n - s2 - n * n * s2 + 2.0 * s2 * s2)


def _rho_diffuse(theta, n):
    s2 = torch.sin(theta) ** 2
    c = torch.cos(theta)
    root = torch.sqrt(torch.clamp(n * n - s2, min=0.0))
    return (n - 1.0 / n) ** 2 * s2 / (2.0 + 2.0 * n * n - (n + 1.0 / n) ** 2 * s2 + 4.0 * c * root)


def _stokes_from_normals(nrm, n, model, radiance):
    theta = torch.acos(torch.clamp(nrm[..., 2], -1.0, 1.0))
    phi = torch.atan2(nrm[..., 1], nrm[..., 0])
    rho = _rho_specular(theta, n) if model == "specular" else _rho_diffuse(theta, n)
    psi = phi + (0.5 * math.pi if model == "specular" else 0.0)
    return radiance, radiance * rho * torch.cos(2.0 * psi), radiance * rho * torch.sin(2.0 * psi)


def sfp_render_batch(normals, refractive_index=1.5, specular_radiance=1.0, diffuse_radiance=0.0,
                     angles_deg=(0.0, 45.0, 90.0, 135.0), device="cpu", dtype="float64"):
    """``sfpolar.sfp_render`` の ``(B, N, H, W)`` 版(``normals`` は ``(B, H, W, 3)`` か ``(H, W, 3)``)。"""
    nrm = _tens(normals, device, dtype)
    squeeze = nrm.ndim == 3
    if squeeze:
        nrm = nrm[None]
    if nrm.ndim != 4 or nrm.shape[-1] != 3:
        raise ValueError("sfp_render_batch: normals must be (B, H, W, 3), got %r" % (tuple(nrm.shape),))
    rs = torch.as_tensor(float(specular_radiance), dtype=nrm.dtype, device=nrm.device).expand(nrm.shape[:-1])
    rd = torch.as_tensor(float(diffuse_radiance), dtype=nrm.dtype, device=nrm.device).expand(nrm.shape[:-1])
    a = _stokes_from_normals(nrm, float(refractive_index), "specular", rs)
    b = _stokes_from_normals(nrm, float(refractive_index), "diffuse", rd)
    s0, s1, s2 = a[0] + b[0], a[1] + b[1], a[2] + b[2]
    t = torch.deg2rad(torch.as_tensor(np.asarray(angles_deg, float), dtype=nrm.dtype, device=nrm.device))[None, :, None, None]
    img = 0.5 * (s0[:, None] + s1[:, None] * torch.cos(2.0 * t) + s2[:, None] * torch.sin(2.0 * t))
    img = torch.clamp(img, min=0.0)
    return img[0] if squeeze else img


def _bisect(f, target, lo, hi, increasing):
    lo = torch.as_tensor(lo, dtype=target.dtype, device=target.device).expand_as(target).clone()
    hi = torch.as_tensor(hi, dtype=target.dtype, device=target.device).expand_as(target).clone()
    for _ in range(_BISECT_ITERS):
        mid = 0.5 * (lo + hi)
        below = f(mid) < target
        if not increasing:
            below = ~below
        lo = torch.where(below, mid, lo)
        hi = torch.where(below, hi, mid)
    return 0.5 * (lo + hi)


def dolp_to_zenith_batch(dolp, refractive_index=1.5, model="diffuse", device="cpu", dtype="float64"):
    """``sfpolar.dolp_to_zenith`` の二分法(``out_of_range="clamp"`` の場合)を場で: ``zenith_deg`` と ``n_solutions``。"""
    rho = _tens(dolp, device, dtype)
    n = float(refractive_index)
    if bool(((rho < 0.0) | (rho > 1.0)).any()):
        raise ValueError("dolp_to_zenith_batch: dolp must be in [0, 1]")
    half = 0.5 * math.pi
    if model == "diffuse":
        rmax = (n * n - 1.0) / (n * n + 1.0)
        th = _bisect(lambda t: _rho_diffuse(t, n), torch.clamp(rho, max=rmax), 0.0, half, True)
        return {"zenith_deg": torch.rad2deg(th)[None], "n_solutions": (rho <= rmax).to(torch.int64)}
    if model != "specular":
        raise ValueError("dolp_to_zenith_batch: model must be 'diffuse' or 'specular', got %r" % (model,))
    import sfpolar as _sf
    tb = math.atan(n)
    top = rho >= 1.0 - _sf._BREWSTER_EPS
    tgt = rho.masked_fill(top, 0.5)
    low = _bisect(lambda t: _rho_specular(t, n), tgt, 0.0, tb, True)
    high = _bisect(lambda t: _rho_specular(t, n), tgt, tb, half, False)
    low = low.masked_fill(top, tb)
    high = high.masked_fill(top, tb)
    return {"zenith_deg": torch.rad2deg(torch.stack((low, high))),
            "n_solutions": torch.where(top, 1, 2).to(torch.int64)}
