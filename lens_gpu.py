# -*- coding: utf-8 -*-
"""lens_gpu — 設計案 M × 波長 W × 光線 R を 1 つのテンソルで追う逐次光線追跡(torch)。

``raytrace`` は光線束 1 つ・波長 1 つ・処方 1 つずつ Python のループで回す。ここでは同じ式を
``(M, W, R)`` の形に畳む。CPU でも GPU でも動き、**定義は ``raytrace`` のものをそのまま使う**
(新しい物理は足さない)。対応は次のとおり。

=============================  =======================================================
``paraxial_batch``             ``raytrace.paraxial_trace`` の全スカラー量
``trace_batch``                ``raytrace.trace_rays``(``valid`` の意味は同じ)
``bundle_batch``               ``raytrace.ray_bundle``(``aim="paraxial"`` の経路)
``spot_stats_batch``           ``raytrace.spot_stats``
``chromatic_batch``            ``raytrace.chromatic_shift``
``opd_batch``                  ``raytrace.opd_samples``
``mtf_batch``                  ``lensimage.through_focus_mtf`` の焦点 1 位置
``tolerance_monte_carlo``      ``raytrace.tolerance_analysis`` の MC 部(乱数列まで同じ)
``spectral_transmission``      ``lensrender`` の無偏光 Fresnel + ``materials`` の内部透過率
=============================  =======================================================

理想レンズ面 ``f``、``zernike_sag``、``afocal``、ケラレ係数、``aim="stop"`` も同じ定義で扱う。
**扱わないもの**: 物体側テレセン(入射瞳が無限遠)。バッチの中で一部の案に起きうるので、例外でなく
``failed`` の印で返す。``aim="stop"`` が収束しない案も同じ印になる(CPU は ``ValueError``)。

精度: 既定は float64。float32 は ``dtype="float32"`` で選べるが誤差は桁で悪化する
(実測は ``docs/perf/gpu_optics_2026-11-02.md``)。

★GPU が勝つのは一括のときだけ。1 回だけ小さく呼ぶなら転送と起動で負けるので、``device="auto"`` は
仕事量が :data:`AUTO_GPU_MIN_RAYS` 未満なら CPU を選ぶ。
"""
from __future__ import annotations

import dataclasses
import math

import numpy as np

import raytrace as RT
from torch_lazy import HAS_TORCH, torch

__all__ = ["compile_lens", "compile_many", "run_split", "marginal_focus", "chromatic_sweep", "paraxial_batch", "paraxial_color", "launch_batch", "trace_batch", "bundle_batch",
           "spot_stats_batch", "chromatic_batch", "opd_batch", "mtf_batch", "tolerance_draws",
           "tolerance_monte_carlo", "spectral_transmission", "index_array", "index_table",
           "absorption_array", "gpu_available"]

INF = float("inf")
#: ``device="auto"`` が GPU を選ぶ仕事量の下限(M × W × R × 面数)。実測で 23 万は CPU が勝ち、760 万は GPU が
#: 12 倍勝つので、その間に置く(docs/perf/gpu_optics_2026-11-02.md)。
AUTO_GPU_MIN_RAYS = 1_000_000
#: CPU で 1 回に積むメモリの目安(キャッシュから溢れて遅くならない大きさ)。
CPU_CHUNK_BYTES = 1 << 30
_NEWTON_ITERS = 40


def gpu_available() -> bool:
    """CUDA の GPU が使えるか(torch が無ければ False)。"""
    return bool(HAS_TORCH) and bool(torch.cuda.is_available())


def _device(device, work=None):
    if not HAS_TORCH:
        raise ImportError("lens_gpu needs the optional 'torch' backend: pip install \"fullseye[gpu]\"")
    d = "auto" if device is None else str(device)
    if d == "auto":
        if gpu_available() and (work is None or work >= AUTO_GPU_MIN_RAYS):
            return "cuda"
        return "cpu"
    if d not in ("cpu", "cuda") and not d.startswith("cuda:"):
        raise ValueError("device must be 'auto', 'cpu' or 'cuda', got %r" % (device,))
    if d != "cpu" and not gpu_available():
        raise ValueError("device=%r was asked for but no CUDA GPU is available" % (device,))
    return d


def _dtype(dtype):
    if dtype in ("float64", "double"):
        return torch.float64
    if dtype in ("float32", "float", "single"):
        return torch.float32
    raise ValueError("dtype must be 'float64' or 'float32', got %r" % (dtype,))


# --------------------------------------------------------------------------- #
# 屈折率: 波長配列で一括に
# --------------------------------------------------------------------------- #
def _wl_array(wl_um):
    wl = np.atleast_1d(np.asarray(wl_um, dtype=np.float64)).ravel()
    if wl.size == 0 or not np.all(np.isfinite(wl)) or np.any(wl <= 0.0):
        raise ValueError("wavelengths must be finite and > 0, got %r" % (wl_um,))
    return wl


def index_array(medium, wl_um):
    """``raytrace.refractive_index`` の波長配列版(同じ範囲で同じ拒否、ループなし)。"""
    wl = _wl_array(wl_um)
    if isinstance(medium, str):
        medium = RT.glass_catalog(medium)
    if isinstance(medium, dict) and "material" in medium:
        import materials as _mat
        rec = _mat._record(medium["material"], "refractive_index")
        n = np.asarray(_mat._nk(rec, wl, "refractive_index")[0], float) + RT._finite(medium.get("offset", 0.0), "index offset")
        if not (np.all(np.isfinite(n)) and np.all(n >= 1.0)):
            raise ValueError("%s index is below 1 or non-finite in this band" % rec["name"])
        return n
    if isinstance(medium, dict) and "sellmeier" in medium:
        lo, hi = RT._SELLMEIER_RANGE
        if np.any(wl < lo) or np.any(wl > hi):
            raise ValueError("wavelengths %.4g-%.4g um leave the Sellmeier fit range %s" % (wl.min(), wl.max(), (lo, hi)))
        coef = medium["sellmeier"]
        if not isinstance(coef, (tuple, list)) or len(coef) != 6:
            raise ValueError("sellmeier must hold six coefficients (B1, B2, B3, C1, C2, C3)")
        B1, B2, B3, C1, C2, C3 = (RT._finite(v, "sellmeier coefficient") for v in coef)
        l2 = wl * wl
        if min(np.abs(l2 - C1).min(), np.abs(l2 - C2).min(), np.abs(l2 - C3).min()) < 1e-12:
            raise ValueError("Sellmeier curve has a pole in this band")
        n2 = 1.0 + B1 * l2 / (l2 - C1) + B2 * l2 / (l2 - C2) + B3 * l2 / (l2 - C3)
        if not (np.all(n2 > 0) and np.all(np.isfinite(n2))):
            raise ValueError("Sellmeier curve is singular in this band")
        n = np.sqrt(n2) + RT._finite(medium.get("offset", 0.0), "index offset")
        if not np.all(n >= 1.0):
            raise ValueError("Sellmeier index below 1 in this band")
        return n
    if (isinstance(medium, dict) and "A" in medium) or (isinstance(medium, (tuple, list)) and len(medium) == 2):
        if np.any(wl < 0.40) or np.any(wl > 0.80):
            raise ValueError("wavelengths %.4g-%.4g um leave the (nd, vd) / Cauchy range (0.4, 0.8) um; name the "
                             "glass or give a Sellmeier / material dict" % (wl.min(), wl.max()))
        g = medium if isinstance(medium, dict) else RT.glass(*medium)
        return g["A"] + g["B"] / (wl * wl)
    n = RT._finite(medium, "index", positive=True)
    if n < 1.0:
        raise ValueError("a refractive index must be >= 1, got %r" % n)
    return np.full(wl.shape, n)


def absorption_array(medium, wl_um):
    """吸収係数 α [1/µm](``4πk/λ``、``materials`` と同じ定義)。k のデータが無い媒質は 0。"""
    wl = _wl_array(wl_um)
    if isinstance(medium, str):
        medium = RT.glass_catalog(medium)
    if isinstance(medium, dict) and "material" in medium:
        import materials as _mat
        rec = _mat._record(medium["material"], "absorption_array")
        k = np.asarray(_mat._nk(rec, wl, "absorption_array")[1], float)
        return 4.0 * np.pi * k / wl
    return np.zeros(wl.shape)


def index_table(media, wl_um, device="cpu", dtype="float64"):
    """媒質の列 × 波長の屈折率表 ``(G, W)`` を torch テンソルで返す(媒質ごとに 1 回だけ評価)。"""
    wl = _wl_array(wl_um)
    a = np.stack([index_array(m, wl) for m in media]) if len(media) else np.zeros((0, wl.size))
    return torch.as_tensor(a, dtype=_dtype(dtype), device=_device(device))


def _offset_gain(medium, wl):
    """``raytrace._index_offset(medium, δ)`` の n(λ) の δ に対する傾き(δ に厳密に線形)。

    Sellmeier・材料・Cauchy の dict・素の数は全波長で 1。``(nd, vd)`` の組だけは ``glass(nd + δ, vd)`` に
    作り直されるので分散も動く: ``1 + (1/λ² − 1/λ_d²) / (V_d (1/λ_F² − 1/λ_C²))``。
    """
    if isinstance(medium, (tuple, list)):
        K = 1.0 / RT.WL_F ** 2 - 1.0 / RT.WL_C ** 2
        return 1.0 + (1.0 / (wl * wl) - 1.0 / RT.WL_D ** 2) / (float(medium[1]) * K)
    return np.ones(wl.shape)


# --------------------------------------------------------------------------- #
# 処方 → テンソル
# --------------------------------------------------------------------------- #
@dataclasses.dataclass
class LensBatch:
    """``compile_lens`` の結果。``M`` 案 × ``W`` 波長 × ``S`` 面。"""
    system: dict
    wl: object            # (W,)
    c: object             # (M, S) 1/R(実光線)
    c_par: object         # (M, S) 近軸の曲率(a2 / odd の r² 項を含む)
    k: object             # (S,)
    t: object             # (M, S) 面の後の厚さ(None は 0)
    t_none: tuple
    ap: object            # (S,) inf = 無制限
    dec: object           # (M, S, 2) または None
    tilt: object          # (M, S, 2) または None(度)
    asph: object          # (S, A)
    a2: object            # (S,)
    odd: object           # (S, B)
    newton: tuple         # 面ごとに Newton が要るか
    mirror: tuple
    n_u: object           # (M, W, S + 1) 符号なしの屈折率(鏡は前の媒質のまま)
    sign: object          # (S + 1,) 進行方向の符号
    alpha: object         # (W, S + 1) 吸収係数 1/µm
    offsets: object       # (M, S) または None
    f: object             # (S,) 理想レンズの焦点距離(無ければ NaN)
    ideal: tuple          # 面ごとに理想レンズか
    astig: object         # (S, 2) zernike_sag の 2 係数
    has_astig: tuple

    @property
    def M(self):
        return self.n_u.shape[0]

    @property
    def W(self):
        return self.n_u.shape[1]

    @property
    def S(self):
        return self.c.shape[1]

    @property
    def device(self):
        return self.c.device

    @property
    def dtype(self):
        return self.c.dtype

    def tensor(self, a):
        return torch.as_tensor(a, dtype=self.dtype, device=self.device)

    def k_at(self, i):
        """面 i の円錐定数(全案で共通ならスカラー、案ごとなら (M, 1, 1))。"""
        return self.k[i] if self.k.ndim == 1 else self.k[:, i][:, None, None]

    def asph_at(self, i):
        """面 i の非球面係数の列(各要素はスカラーか (M, 1, 1))。"""
        a = self.asph
        return [a[i, j] for j in range(a.shape[1])] if a.ndim == 2 else [a[:, i, j][:, None, None] for j in range(a.shape[2])]


def _check_supported(system):
    RT._check_system(system)
    return RT._solved(system)


def _keeps_medium(s):
    """鏡と理想レンズは媒質を変えない(raytrace は n_after = n_before)。"""
    return bool(s["mirror"]) or s.get("f") is not None


def _index_rows(system, wl, offsets, tens):
    """(M, W, S + 1) の屈折率。δ の扱いは :func:`_offset_gain`。"""
    surf = system["surfaces"]
    S = len(surf)
    table = np.zeros((wl.size, S + 1))
    gain = np.zeros((wl.size, S + 1))
    table[:, 0] = system["index_object"]
    for i, s in enumerate(surf):
        if _keeps_medium(s):
            table[:, i + 1] = table[:, i]
            gain[:, i + 1] = gain[:, i]
        else:
            table[:, i + 1] = index_array(s["n"], wl)
            gain[:, i + 1] = _offset_gain(s["n"], wl)
    n = tens(table)[None]
    if offsets is None:
        return n
    # 鏡の後の媒質は前の媒質の δ を引き継ぐ(raytrace は n_after = n_before)
    d = np.array(offsets, dtype=np.float64)
    full = np.zeros((d.shape[0], S + 1))
    for i, s in enumerate(surf):
        full[:, i + 1] = full[:, i] if _keeps_medium(s) else d[:, i]
    return n + tens(full)[:, None, :] * tens(gain)[None]


def _alpha_rows(system, wl):
    surf = system["surfaces"]
    alpha = np.zeros((wl.size, len(surf) + 1))
    for i, s in enumerate(surf):
        alpha[:, i + 1] = alpha[:, i] if _keeps_medium(s) else absorption_array(s["n"], wl)
    return alpha


def compile_lens(system, wavelengths=None, device="auto", dtype="float64", overrides=None):
    """処方を :class:`LensBatch` にする。

    *wavelengths*: µm の列(既定は系の波長)。*overrides*: ``{"R", "t", "offset", "decenter", "tilt"}`` の
    ``(M, S[, 2])`` 配列(:func:`tolerance_draws`)。無ければ 1 案。
    """
    system = _check_supported(system)
    wl = _wl_array(system["wavelength_um"] if wavelengths is None else wavelengths)
    dt = _dtype(dtype)
    surf = system["surfaces"]
    S = len(surf)
    ov = overrides or {}
    n_designs = max((len(v) for v in ov.values()), default=1)
    dev = _device(device, n_designs * wl.size * S * 127)        # 光線数は未定なので hexapolar 6 輪を見積もりに使う

    def tens(a):
        return torch.as_tensor(np.asarray(a, dtype=np.float64), dtype=dt, device=dev)

    R = np.array([[s["R"] for s in surf]], float) if "R" not in ov else np.asarray(ov["R"], float)
    with np.errstate(divide="ignore"):
        c = np.where(np.isinf(R), 0.0, 1.0 / R)
    extra = np.array([RT._c_extra(s) if ("a2" in s or "odd" in s) else 0.0 for s in surf])
    t = np.array([[0.0 if s["t"] is None else s["t"] for s in surf]], float) if "t" not in ov else np.asarray(ov["t"], float)
    A = max((len(s["asph"]) for s in surf), default=0)
    B = max((len(s.get("odd", ())) for s in surf), default=0)
    asph = np.zeros((S, max(A, 1)))
    odd = np.zeros((S, max(B, 1)))
    for i, s in enumerate(surf):
        asph[i, :len(s["asph"])] = s["asph"]
        o = s.get("odd", ())
        odd[i, :len(o)] = o
    sign = [1.0]
    for s in surf:
        sign.append(-sign[-1] if s["mirror"] else sign[-1])
    n_u = _index_rows(system, wl, ov.get("offset"), tens)
    dec = ov.get("decenter")
    tilt = ov.get("tilt")
    if dec is None and any(s["decenter"] != (0.0, 0.0) for s in surf):
        dec = np.array([[s["decenter"] for s in surf]], float)
    if tilt is None and any(s["tilt"] != (0.0, 0.0) for s in surf):
        tilt = np.array([[s["tilt"] for s in surf]], float)
    M = max(c.shape[0], t.shape[0], n_u.shape[0], 1 if dec is None else dec.shape[0], 1 if tilt is None else tilt.shape[0])
    return LensBatch(system=system, wl=tens(wl), c=tens(c).expand(M, S), c_par=tens(c + extra).expand(M, S),
                     k=tens([s["k"] for s in surf]), t=tens(t).expand(M, S),
                     t_none=tuple(s["t"] is None for s in surf),
                     ap=tens([INF if s["ap"] is None else s["ap"] for s in surf]),
                     dec=None if dec is None else tens(dec).expand(M, S, 2),
                     tilt=None if tilt is None else tens(tilt).expand(M, S, 2),
                     asph=tens(asph), a2=tens([s.get("a2", 0.0) for s in surf]), odd=tens(odd),
                     newton=tuple(bool(s["asph"]) or RT._xtra(s) is not None or "zernike_sag" in s for s in surf),
                     mirror=tuple(bool(s["mirror"]) for s in surf),
                     n_u=n_u.expand(M, wl.size, S + 1), sign=tens(sign), alpha=tens(_alpha_rows(system, wl)),
                     offsets=ov.get("offset"),
                     f=tens([float("nan") if s.get("f") is None else s["f"] for s in surf]),
                     ideal=tuple(s.get("f") is not None for s in surf),
                     astig=tens([s.get("zernike_sag", (0.0, 0.0)) for s in surf]),
                     has_astig=tuple("zernike_sag" in s for s in surf))


def compile_many(systems, wavelengths=None, device="auto", dtype="float64"):
    """構造が同じ処方の列(面数・絞り・鏡・半開口・媒質が同じ)を 1 つの :class:`LensBatch` にする。

    ``R`` ``t`` ``k`` ``asph`` は案ごとに違ってよい(``lensopt`` の変数)。Jacobian の列を一括で評価する口。
    """
    solved = [_check_supported(s) for s in systems]
    if not solved:
        raise ValueError("compile_many: no systems")
    s0 = solved[0]
    surf0 = s0["surfaces"]
    S = len(surf0)
    for q in solved[1:]:
        surf = q["surfaces"]
        same = (len(surf) == S and q["stop"] == s0["stop"] and q["object_mm"] == s0["object_mm"]
                and all(a["mirror"] == b["mirror"] and a["ap"] == b["ap"] and a.get("f") == b.get("f")
                        and repr(a["n"]) == repr(b["n"]) and (a["t"] is None) == (b["t"] is None) for a, b in zip(surf0, surf)))
        if not same:
            raise ValueError("compile_many: the systems differ in structure (surfaces, stop, mirrors, apertures or media)")
    M = len(solved)
    R = np.array([[s["R"] for s in q["surfaces"]] for q in solved], float)
    t = np.array([[0.0 if s["t"] is None else s["t"] for s in q["surfaces"]] for q in solved], float)
    k = np.array([[s["k"] for s in q["surfaces"]] for q in solved], float)
    A = max(1, max(len(s["asph"]) for q in solved for s in q["surfaces"]))
    asph = np.zeros((M, S, A))
    for m, q in enumerate(solved):
        for i, s in enumerate(q["surfaces"]):
            asph[m, i, :len(s["asph"])] = s["asph"]
    lens = compile_lens(s0, wavelengths, device=device, dtype=dtype, overrides={"R": R, "t": t})
    return dataclasses.replace(lens, k=lens.tensor(k), asph=lens.tensor(asph), newton=tuple(
        any(bool(q["surfaces"][i]["asph"]) for q in solved) or lens.newton[i] for i in range(S)))


def _at_wavelengths(lens, wavelengths):
    """同じ設計案群を別の波長で(幾何は共有)。"""
    wl = _wl_array(wavelengths)

    def tens(a):
        return torch.as_tensor(np.asarray(a, dtype=np.float64), dtype=lens.dtype, device=lens.device)

    n_u = _index_rows(lens.system, wl, lens.offsets, tens).expand(lens.M, wl.size, lens.S + 1)
    return dataclasses.replace(lens, wl=tens(wl), n_u=n_u, alpha=tens(_alpha_rows(lens.system, wl)))


# --------------------------------------------------------------------------- #
# 近軸
# --------------------------------------------------------------------------- #
def _ptrace(c, t, n, y0, u0, pw=None):
    """(y, u) の式を (M, W) で。c (M, 1, S)、t (M, W, S)、n (M, W, S + 1)、pw (S,) 理想レンズの屈折力。"""
    ys, us = [], []
    y, u = y0, u0
    for i in range(c.shape[-1]):
        ys.append(y)
        n0, n1 = n[..., i], n[..., i + 1]
        u = n0 * u - y * c[..., i] * (n1 - n0)
        if pw is not None and pw[i] != 0:
            u = u - y * pw[i] * n0.abs()
        u = u / n1
        us.append(u)
        y = y + t[..., i] * u
    return torch.stack(ys, -1), torch.stack(us, -1)


def paraxial_batch(lens):
    """``raytrace.paraxial_trace`` の量を ``(M, W)`` で返す。

    CPU が ``ValueError`` にする「絞りを物体空間へ結像できない」案は ``failed`` の印にする
    (1 案ずつ例外にするとバッチが止まるため)。``marginal_y`` などは ``(M, W, S)``。
    """
    sysd = lens.system
    M, W, S = lens.M, lens.W, lens.S
    n = lens.n_u * lens.sign
    c = lens.c_par[:, None, :]
    t = (lens.t[:, None, :] * lens.sign[1:]).expand(M, W, S)
    zero = torch.zeros((M, W), dtype=lens.dtype, device=lens.device)
    one = zero + 1.0
    pw = torch.nan_to_num(1.0 / lens.f, nan=0.0) if any(lens.ideal) else None
    y, u = _ptrace(c, t, n, one, zero, pw)
    ul, yl = u[..., -1], y[..., -1]
    afocal = bool(sysd.get("afocal"))
    flat = (ul.abs() < 1e-15) | afocal
    # CPU が ValueError にする「afocal なのに焦点を結ぶ」案は failed の印にする
    not_collimated = afocal & (ul.abs() > 1e-9 * u.abs().amax(-1).clamp(min=1e-300))
    efl = torch.where(flat, zero + INF, -y[..., 0] / ul)
    bfl = torch.where(flat, zero + INF, -yl / ul)
    # 前側: 系を裏返して逆向きに
    c_r = -torch.flip(c, (-1,))
    n_r = torch.flip(n, (-1,))
    t_r = torch.cat([torch.flip(t, (-1,))[..., 1:], torch.zeros_like(t[..., :1])], -1)
    y_r, u_r = _ptrace(c_r, t_r, n_r, one, zero, None if pw is None else torch.flip(pw, (0,)))
    ffl = torch.where((u_r[..., -1].abs() > 1e-15) & (not afocal), y_r[..., -1] / u_r[..., -1], zero - INF)
    pp_front = torch.where(torch.isfinite(efl), ffl + efl, zero - INF)
    stop = sysd["stop"]
    stop_r = lens.ap[stop]
    obj = sysd["object_mm"]
    n0 = n[..., 0]

    def y_at_stop(y0, u0):
        return _ptrace(c, t, n, y0, u0, pw)[0][..., stop]

    if obj == INF:
        a = y_at_stop(one, zero)
        b = y_at_stop(zero, one)
        failed = a.abs() < 1e-15
        ep_pos = b / a
        ep_radius = stop_r / a.abs()
        mag = zero
        h = -b / a
        yc, uc = _ptrace(c, t, n, h, one, pw)
        ym, um = _ptrace(c, t, n, ep_radius, zero, pw)
        img = bfl
        lagrange = n0 * ep_radius
    else:
        a = y_at_stop(obj * one, one)
        b = y_at_stop(one, zero)
        failed = a.abs() < 1e-15
        s_per_H = -b / a
        ep_pos = torch.where(s_per_H.abs() > 1e-15, -obj - 1.0 / s_per_H, zero - INF)
        s_m = stop_r / a.abs()
        ep_radius = torch.where(torch.isfinite(ep_pos), (s_m * (obj + ep_pos)).abs(), zero + INF)
        yc, uc = _ptrace(c, t, n, 1.0 + s_per_H * obj, s_per_H, pw)
        ym, um = _ptrace(c, t, n, s_m * obj, s_m, pw)
        uml = um[..., -1]
        img = torch.where(uml.abs() > 1e-15, -ym[..., -1] / uml, zero + INF)
        mag = torch.where(torch.isfinite(img), yc[..., -1] + uc[..., -1] * img, zero + INF)
        lagrange = n0 * (s_per_H * (s_m * obj) - s_m * (1.0 + s_per_H * obj))
    ucl = uc[..., -1]
    xp_pos = torch.where(ucl.abs() > 1e-15, -yc[..., -1] / ucl, zero + INF)
    xp_radius = torch.where(torch.isfinite(xp_pos), (ym[..., -1] + um[..., -1] * xp_pos).abs(), zero + INF)
    sgn = lens.sign[-1]
    efl, bfl, img, xp_pos = efl * sgn, bfl * sgn, img * sgn, xp_pos * sgn
    pp_rear = torch.where(torch.isfinite(efl), bfl - efl, zero + INF)
    fno = torch.where((ep_radius == 0) | ~torch.isfinite(efl), zero + INF, efl.abs() / (2.0 * ep_radius))
    na = n[..., -1].abs() * um[..., -1].abs()
    out = {"efl": efl, "bfl": bfl, "ffl": ffl, "pp_front": pp_front, "pp_rear": pp_rear, "image_mm": img,
           "magnification": mag, "ep_position": ep_pos, "ep_radius": ep_radius, "xp_position": xp_pos,
           "xp_radius": xp_radius, "fno": fno, "na_image": na, "lagrange": lagrange,
           "marginal_y": ym, "marginal_u": um, "chief_y": yc, "chief_u": uc, "failed": failed | not_collimated}
    if afocal:
        out["angular_magnification"] = uc[..., -1] * sgn
    return out


def _reference_image(lens):
    """``raytrace.trace_rays`` が既定で使う像面: ``image_mm`` → 最後の ``t`` → 設計波長の近軸像。(M, 1)。"""
    sysd = lens.system
    if sysd["image_mm"] is not None:
        return lens.tensor([[sysd["image_mm"]]]).expand(lens.M, 1)
    if not lens.t_none[-1]:
        return lens.t[:, -1:]
    if sysd.get("afocal"):
        return torch.zeros((lens.M, 1), dtype=lens.dtype, device=lens.device)   # 射出は平行光: 読むのは角度
    return paraxial_batch(_at_wavelengths(lens, [sysd["wavelength_um"]]))["image_mm"]


def _chromatic_image(lens):
    """``raytrace.chromatic_shift`` の基準像面(最後の候補が近軸像でなく BFL)。(M, 1)。"""
    sysd = lens.system
    if sysd["image_mm"] is not None or not lens.t_none[-1]:
        return _reference_image(lens)
    return paraxial_batch(_at_wavelengths(lens, [sysd["wavelength_um"]]))["bfl"]


def paraxial_color(lens, field=None, image_mm=None):
    """近軸の色収差: ``efl`` ``bfl``(M, W)、``axial_color`` = BFL(最初) − BFL(最後)(M,)、
    ``chief_height``(基準像面の近軸主光線の高さ、M, W)、``lateral_color`` = 高さ(最初) − 高さ(最後)(M,)。

    基準像面は ``chromatic_shift`` と同じ(*image_mm* > ``t`` > 設計波長の BFL)。主光線の傾きは
    無限物体で ``tan(field)``、有限物体で物体高 *field*。
    """
    sysd = lens.system
    field = sysd["field"] if field is None else RT._finite(field, "field")
    p = paraxial_batch(lens)
    img = _chromatic_image(lens) if image_mm is None else lens.tensor([[float(image_mm)]]).expand(lens.M, 1)
    # raytrace の主光線は物体側の単位傾き / 単位物体高に正規化されている
    scale = math.tan(math.radians(field)) if sysd["object_mm"] == INF else field
    h = scale * (p["chief_y"][..., -1] + p["chief_u"][..., -1] * img * lens.sign[-1])
    return {"efl": p["efl"], "bfl": p["bfl"], "axial_color": p["bfl"][:, 0] - p["bfl"][:, -1], "chief_height": h,
            "lateral_color": h[:, 0] - h[:, -1], "failed": p["failed"]}


# --------------------------------------------------------------------------- #
# 実光線
# --------------------------------------------------------------------------- #
def _sag(r2, c, k, asph, a2, odd):
    root = torch.sqrt(1.0 - (1.0 + k) * c * c * r2)
    z = c * r2 / (1.0 + root)
    p = r2 * r2
    for a in asph:
        if torch.any(a != 0):
            z = z + a * p
        p = p * r2
    z = z + a2 * r2
    if torch.any(odd != 0):
        r = torch.sqrt(r2)
        p = r
        for j in range(odd.shape[0]):
            z = z + odd[j] * p
            p = p * r
    return z


def _dsag(r2, c, k, asph, a2, odd):
    root = torch.sqrt(1.0 - (1.0 + k) * c * c * r2)
    s = c / (2.0 * root)
    s = torch.where(c == 0, torch.zeros_like(s), s)
    p = r2
    m = 2.0
    for a in asph:
        if torch.any(a != 0):
            s = s + a * m * p
        p = p * r2
        m += 1.0
    s = s + a2
    if torch.any(odd != 0):
        r = torch.sqrt(r2)
        for i in range(1, odd.shape[0] + 1):
            b = odd[i - 1]
            if b == 0:
                continue
            if i == 1:
                s = s + torch.where(r > 0.0, b / (2.0 * r), torch.zeros_like(r))
            elif i == 2:
                s = s + b
            else:
                s = s + 0.5 * i * b * r ** (i - 2)
    return s


def _hit_conic(x, y, z, L, Mm, N, c, k):
    """``raytrace._intersect_conic`` と同じ根の選び方(頂点を含む葉、|t| の小さい方)。c は (M, 1, 1)。"""
    nan = torch.tensor(float("nan"), dtype=x.dtype, device=x.device)
    flat = -z / N
    flat = torch.where(N.abs() < 1e-15, nan, flat)
    if not torch.any(c != 0):
        return flat
    kk = 1.0 + k
    A = c * (L * L + Mm * Mm + kk * N * N)
    B = 2.0 * (c * (x * L + y * Mm + kk * z * N) - N)
    C = c * (x * x + y * y + kk * z * z) - 2.0 * z
    disc = B * B - 4.0 * A * C
    ok = disc >= 0
    sq = torch.sqrt(torch.where(ok, disc, torch.zeros_like(disc)))
    lin = A.abs() < 1e-14
    t_lin = -C / B
    # raytrace._intersect_conic と同じ安定な形(小さい根を C/q で解く)
    q = -0.5 * (B + torch.where(B >= 0, sq, -sq))
    big = q / A
    small = torch.where(q != 0, C / q, torch.zeros_like(q))
    t1 = torch.where(B >= 0, big, small)
    t2 = torch.where(B >= 0, small, big)
    on1 = kk * c * (z + t1 * N) <= 1.0 + 1e-9
    on2 = kk * c * (z + t2 * N) <= 1.0 + 1e-9
    near = torch.where(t1.abs() <= t2.abs(), t1, t2)
    pick = torch.where(on1 & on2, near, torch.where(on1, t1, torch.where(on2, t2, nan)))
    t = torch.where(lin, t_lin, pick)
    t = torch.where(ok, t, nan)
    return torch.where(c == 0, flat, t)


def _hit_asphere(x, y, z, L, Mm, N, c, k, asph, a2, odd, t0, astig=None):
    nan = torch.tensor(float("nan"), dtype=x.dtype, device=x.device)
    step_tol, f_tol = (1e-12, 1e-8) if x.dtype == torch.float64 else (1e-5, 1e-3)
    t = torch.where(torch.isfinite(t0), t0, torch.zeros_like(t0))

    def extra(xx, yy):
        if astig is None:
            return 0.0, 0.0, 0.0
        a0, a45, ap = astig
        return ((a0 * (xx * xx - yy * yy) + 2.0 * a45 * xx * yy) / (ap * ap),
                (2.0 * a0 * xx + 2.0 * a45 * yy) / (ap * ap), (-2.0 * a0 * yy + 2.0 * a45 * xx) / (ap * ap))

    for _ in range(_NEWTON_ITERS):
        xx, yy, zz = x + t * L, y + t * Mm, z + t * N
        r2 = xx * xx + yy * yy
        sa, dax, day = extra(xx, yy)
        F = zz - _sag(r2, c, k, asph, a2, odd) - sa
        s = _dsag(r2, c, k, asph, a2, odd)
        dF = N - 2.0 * s * (xx * L + yy * Mm) - dax * L - day * Mm
        step = F / dF
        step = torch.where(torch.isfinite(step), step, nan)
        t = t - step
        fin = torch.isfinite(step)
        if not torch.any(fin) or bool((step[fin].abs() < step_tol).all()):
            break
    xx, yy, zz = x + t * L, y + t * Mm, z + t * N
    F = zz - _sag(xx * xx + yy * yy, c, k, asph, a2, odd) - extra(xx, yy)[0]
    ok = torch.isfinite(t) & torch.isfinite(F) & (F.abs() < f_tol)
    return torch.where(ok, t, nan)


def _rot(lens, i):
    """面 i の回転 Rx @ Ry を (M, 1, 1) の 9 成分で。"""
    a = torch.deg2rad(lens.tilt[:, i, 0])[:, None, None]
    b = torch.deg2rad(lens.tilt[:, i, 1])[:, None, None]
    cx, sx, cy, sy = torch.cos(a), torch.sin(a), torch.cos(b), torch.sin(b)
    zero = torch.zeros_like(cx)
    return (cy, zero, sy, sx * sy, cx, -sx * cy, -cx * sy, sx, cx * cy)


def _norm3(x, y, z):
    return torch.sqrt(x * x + y * y + z * z)


def _ideal_phase(P0, D0, Q, f, n, obj_z=None):
    """``raytrace._ideal_phase``(理想レンズが足す光路長、局所座標)の (M, W, R) 版。"""
    x0, y0, z0 = P0
    L, Mm, N = D0
    qx_, qy_, qz_ = Q
    sdir = torch.where(N >= 0.0, 1.0, -1.0).to(N.dtype)
    ax, ay = L / N.abs(), Mm / N.abs()
    dn = _norm3(ax, ay, sdir)
    Fx, Fy, Fz = ax * f, ay * f, sdir * f
    sg = 1.0 if f > 0 else -1.0
    plane = n * (sg * _norm3(Fx, Fy, Fz) - (ax * qx_ + ay * qy_ + sdir * qz_) / dn
                 - sg * _norm3(Fx - qx_, Fy - qy_, Fz - qz_))
    if obj_z is None:
        return plane
    on_obj = (z0 - obj_z).abs() <= 1e-9 * max(1.0, abs(obj_z))
    s_o = -obj_z
    dd = s_o - f
    sph = _norm3(x0, y0, z0) - _norm3(x0 - qx_, y0 - qy_, z0 - qz_)
    if abs(dd) < 1e-12 * max(1.0, abs(f)):
        ox, oy = -x0 / s_o, -y0 / s_o
        dd_n = _norm3(ox, oy, torch.ones_like(ox))
        sph = sph + (ox * qx_ + oy * qy_ + qz_) / dd_n
    else:
        sp = f * s_o / dd
        m = -sp / s_o
        Ix, Iy = x0 * m, y0 * m
        sps = 1.0 if sp > 0 else -1.0
        sph = sph + sps * (_norm3(Ix, Iy, torch.full_like(Ix, sp)) - _norm3(Ix - qx_, Iy - qy_, sp - qz_))
    return n * torch.where(on_obj, sph, plane / n)


def trace_batch(lens, P, D, image_mm=None, opl=True, points=False, upto=None, visitor=None):
    """実光線の追跡。*P*, *D*: ``(x, y, z)`` の組で各 ``(M, W, R)`` に放送できるテンソル、D は単位ベクトル。

    返り値の ``x y z`` は像面の点、``L M N`` は最後の方向、``valid`` は ``raytrace.trace_rays`` と同じ意味
    (外れ・ケラレ・全反射・像面に届かない)で無効な点は NaN、``opl`` は像面までの光路長、
    ``opl_last`` は最終面までの光路長、``xl yl zl`` は最終面の点、``z_image`` は像面の z(M, W, 1)。
    *points*: 各面の点 ``(M, W, R, S + 2, 3)`` と方向 ``(…, S + 1, 3)`` も返す。
    *upto*: その面の直後で止める(``x y z`` はその面の点。絞りの狙いに使う)。
    *visitor*: 各面で ``visitor(i, info)`` を呼ぶ(``info`` は面の dict。:func:`spectral_transmission` と
    偏光の追跡が使う)。``i == S`` は像面の区間。
    """
    x, y, z = P
    L, Mm, N = D
    shape = (lens.M, lens.W, max(a.shape[-1] for a in (x, y, z, L, Mm, N)))
    x, y, z = x.expand(shape), y.expand(shape), z.expand(shape)
    L, Mm, N = L.expand(shape), Mm.expand(shape), N.expand(shape)
    nan = float("nan")
    path = torch.zeros(shape, dtype=lens.dtype, device=lens.device) if opl else None
    valid = torch.ones(shape, dtype=torch.bool, device=lens.device)
    zv = torch.zeros((lens.M, 1, 1), dtype=lens.dtype, device=lens.device)
    dirn = 1.0
    pts = [torch.stack((x, y, z), -1)] if points else None
    dirs = [torch.stack((L, Mm, N), -1)] if points else None
    for i in range(lens.S):
        nb = lens.n_u[..., i:i + 1]
        na = lens.n_u[..., i + 1:i + 2]
        c = lens.c[:, None, i:i + 1]
        k = lens.k_at(i)
        asph_i = lens.asph_at(i)
        dx = None if lens.dec is None else lens.dec[:, i, 0][:, None, None]
        dy = None if lens.dec is None else lens.dec[:, i, 1][:, None, None]
        moved = dx is not None and bool(torch.any(dx != 0) or torch.any(dy != 0))
        tilted = lens.tilt is not None and bool(torch.any(lens.tilt[:, i] != 0))
        xl = x - dx if moved else x
        yl = y - dy if moved else y
        zl = z - zv
        Ll, Ml, Nl = L, Mm, N
        if tilted:
            r = _rot(lens, i)
            xl, yl, zl = (xl * r[0] + yl * r[3] + zl * r[6], xl * r[1] + yl * r[4] + zl * r[7],
                          xl * r[2] + yl * r[5] + zl * r[8])
            Ll, Ml, Nl = (L * r[0] + Mm * r[3] + N * r[6], L * r[1] + Mm * r[4] + N * r[7],
                          L * r[2] + Mm * r[5] + N * r[8])
        ideal = lens.ideal[i]
        astig = (lens.astig[i, 0], lens.astig[i, 1], lens.ap[i]) if lens.has_astig[i] else None
        if ideal:                                         # 理想レンズ: 頂点面(z = 0)と交わる
            t = -zl / Nl
        else:
            t = _hit_conic(xl, yl, zl, Ll, Ml, Nl, c, k)
        if lens.newton[i]:
            t = _hit_asphere(xl, yl, zl, Ll, Ml, Nl, c, k, asph_i, lens.a2[i], lens.odd[i], t, astig)
        bad = ~torch.isfinite(t) | (t < -1e-9)
        t = t.masked_fill(bad, nan)
        qx, qy, qz = xl + t * Ll, yl + t * Ml, zl + t * Nl
        if math.isfinite(float(lens.ap[i])):
            bad = bad | (torch.sqrt(qx * qx + qy * qy) > lens.ap[i] * (1.0 + 1e-12))
        if lens.newton[i]:
            s = _dsag(qx * qx + qy * qy, c, k, asph_i, lens.a2[i], lens.odd[i])
            gx, gy, gz = -2.0 * s * qx, -2.0 * s * qy, torch.ones_like(qx)
            if astig is not None:
                a0, a45, ap_ = astig
                gx = gx - (2.0 * a0 * qx + 2.0 * a45 * qy) / (ap_ * ap_)
                gy = gy - (-2.0 * a0 * qy + 2.0 * a45 * qx) / (ap_ * ap_)
        else:
            gx, gy, gz = 2.0 * c * qx, 2.0 * c * qy, 2.0 * c * (1.0 + k) * qz - 2.0
        gn = torch.sqrt(gx * gx + gy * gy + gz * gz)
        gx, gy, gz = gx / gn, gy / gn, gz / gn
        dot = gx * Ll + gy * Ml + gz * Nl
        fl = torch.where(dot > 0, -1.0, 1.0).to(lens.dtype)
        gx, gy, gz, dot = gx * fl, gy * fl, gz * fl, dot * fl
        cos_i = -dot
        cos_t = None
        if lens.mirror[i]:
            Lo, Mo, No = Ll - 2.0 * dot * gx, Ml - 2.0 * dot * gy, Nl - 2.0 * dot * gz
            dirn = -dirn
        elif ideal:
            # 薄肉レンズの法則: 進行方向の傾き q = (Dx, Dy)/|Dz| が q' = q - h/f になる(厳密)
            f_i = float(lens.f[i])
            sd = torch.where(Nl >= 0.0, 1.0, -1.0).to(lens.dtype)
            Lo, Mo, No = Ll / Nl.abs() - qx / f_i, Ml / Nl.abs() - qy / f_i, sd
        else:
            eta = nb / na
            sin2_t = eta * eta * (1.0 - cos_i * cos_i)
            bad = bad | (sin2_t > 1.0)
            cos_t = torch.sqrt(torch.clamp(1.0 - sin2_t, min=0.0))
            b = eta * cos_i - cos_t
            Lo, Mo, No = eta * Ll + b * gx, eta * Ml + b * gy, eta * Nl + b * gz
        dn = torch.sqrt(Lo * Lo + Mo * Mo + No * No)
        Lo, Mo, No = Lo / dn, Mo / dn, No / dn
        if opl:
            path = path + nb * t.abs()
            if ideal:
                oz = -lens.system["object_mm"] if (i == 0 and lens.system["object_mm"] != INF) else None
                path = path + _ideal_phase((xl, yl, zl), (Ll, Ml, Nl), (qx, qy, qz), float(lens.f[i]), nb, oz)
        qxl, qyl = qx, qy
        if tilted:
            qx, qy, qz = (qx * r[0] + qy * r[1] + qz * r[2], qx * r[3] + qy * r[4] + qz * r[5],
                          qx * r[6] + qy * r[7] + qz * r[8])
            Lg, Mg, Ng = (Lo * r[0] + Mo * r[1] + No * r[2], Lo * r[3] + Mo * r[4] + No * r[5],
                          Lo * r[6] + Mo * r[7] + No * r[8])
        else:
            Lg, Mg, Ng = Lo, Mo, No
        valid = valid & ~bad
        x_new = (qx + dx if moved else qx).masked_fill(~valid, nan)
        y_new = (qy + dy if moved else qy).masked_fill(~valid, nan)
        z_new = (qz + zv).masked_fill(~valid, nan)
        Lg, Mg, Ng = Lg.masked_fill(~valid, nan), Mg.masked_fill(~valid, nan), Ng.masked_fill(~valid, nan)
        if visitor is not None:
            # 法線と入射方向は全体座標で渡す(偏光の基底が要る)
            if tilted:
                ng = (gx * r[0] + gy * r[1] + gz * r[2], gx * r[3] + gy * r[4] + gz * r[5],
                      gx * r[6] + gy * r[7] + gz * r[8])
            else:
                ng = (gx, gy, gz)
            visitor(i, {"t": t, "n1": nb, "n2": na, "cos_i": cos_i, "cos_t": cos_t, "mirror": lens.mirror[i], "ideal": ideal,
                        "normal": ng, "d_in": (L, Mm, N), "d_out": (Lg, Mg, Ng), "valid": valid})
        x, y, z, L, Mm, N = x_new, y_new, z_new, Lg, Mg, Ng
        if points:
            pts.append(torch.stack((x, y, z), -1))
            dirs.append(torch.stack((L, Mm, N), -1))
        if upto is not None and i == upto:
            # sx, sy は面の局所座標(raytrace._stop_xy)
            return {"x": x, "y": y, "z": z, "valid": valid, "sx": qxl.masked_fill(~valid, nan),
                    "sy": qyl.masked_fill(~valid, nan)}
        if not lens.t_none[i]:
            zv = zv + dirn * lens.t[:, i][:, None, None]
    z_last = zv if lens.t_none[-1] else zv - dirn * lens.t[:, -1][:, None, None]
    if image_mm is None:
        image_mm = _reference_image(lens)
    img = image_mm if torch.is_tensor(image_mm) else lens.tensor(image_mm)
    img = img[..., None] if img.ndim == 2 else img
    z_img = z_last + dirn * img
    sysd = lens.system
    nb = lens.n_u[..., -1:]
    if sysd.get("image_R", INF) == INF:
        tt = (z_img - z) / N
    else:
        c_im = lens.tensor([[[1.0 / sysd["image_R"]]]])
        tt = _hit_conic(x, y, dirn * (z - z_img), L, Mm, dirn * N, c_im, lens.tensor(sysd.get("image_k", 0.0)))
    qx, qy, qz = x + tt * L, y + tt * Mm, z + tt * N
    opl_last = path
    if opl:
        path = path + nb * tt.abs()
    valid = valid & torch.isfinite(tt) & (dirn * N > RT._MIN_DZ)
    if visitor is not None:
        visitor(lens.S, {"t": tt, "n1": nb, "valid": valid, "d_in": (L, Mm, N)})
    out = {"x": qx.masked_fill(~valid, nan), "y": qy.masked_fill(~valid, nan), "z": qz.masked_fill(~valid, nan),
           "L": L, "M": Mm, "N": N, "xl": x, "yl": y, "zl": z, "valid": valid, "opl": path, "opl_last": opl_last,
           "z_image": z_img, "n_image": nb, "dirn": dirn}
    if points:
        pts.append(torch.stack((out["x"], out["y"], out["z"]), -1))
        out["points"] = torch.stack(pts, -2)
        out["dirs"] = torch.stack(dirs, -2)
    return out


def launch_batch(lens, px, py, field, para, pupil_fill=1.0):
    """``raytrace._launch`` の (M, W, R) 版。*px*, *py* は (R,) か (M, W, R)。返り値 ``P, D, opl0``。"""
    sysd = lens.system
    obj = sysd["object_mm"]
    ep_z = para["ep_position"][..., None]
    ep_r = para["ep_radius"][..., None]
    X = px * ep_r * pupil_fill
    Y = py * ep_r * pupil_fill
    n0 = float(sysd["index_object"])
    if obj == INF:
        th = math.radians(field)
        Dy, Dz = math.sin(th), math.cos(th)
        Dyt = lens.tensor(Dy).expand_as(X)
        Dzt = lens.tensor(Dz).expand_as(X)
        z0 = torch.minimum(ep_z, torch.zeros_like(ep_z)) - torch.maximum(lens.tensor(10.0).expand_as(ep_z), ep_z.abs() + 1.0)
        s = (z0 - ep_z) / Dz
        Px, Py, Pz = X, Y + s * Dy, ep_z + s * Dz
        opl0 = n0 * (Py * Dy + Pz * Dz)
        return (Px, Py, Pz.expand_as(X)), (torch.zeros_like(X), Dyt, Dzt), opl0
    P0y = lens.tensor(float(field))
    P0z = lens.tensor(-float(obj))
    dx, dy, dz = X, Y - P0y, ep_z - P0z
    nn = torch.sqrt(dx * dx + dy * dy + dz * dz)
    return ((torch.zeros_like(X), P0y.expand_as(X), P0z.expand_as(X)), (dx / nn, dy / nn, dz / nn),
            torch.zeros_like(X))


def _chief_offset(lens, field, para):
    """``raytrace._chief_offset`` の (M, W) 版。分岐(打ち切り・据え置き)も 1 案ずつ同じに進める。"""
    shape = (lens.M, lens.W)
    zero = torch.zeros(shape, dtype=lens.dtype, device=lens.device)
    stop = lens.system["stop"]
    finite = torch.isfinite(para["ep_radius"])
    if field == 0.0:
        return zero, zero
    if stop == 0:
        s0_clean = torch.ones(shape, dtype=torch.bool, device=lens.device)
        if lens.dec is not None:
            s0_clean = s0_clean & (lens.dec[:, 0] == 0).all(-1)[:, None]
        if lens.tilt is not None:
            s0_clean = s0_clean & (lens.tilt[:, 0] == 0).all(-1)[:, None]
        if bool(s0_clean.all()):
            return zero, zero
    else:
        s0_clean = torch.zeros(shape, dtype=torch.bool, device=lens.device)
    active = finite & ~s0_clean
    px, py = zero.clone(), zero.clone()
    h = 1e-3
    o = torch.as_tensor([0.0, h, 0.0], dtype=lens.dtype, device=lens.device)
    p = torch.as_tensor([0.0, 0.0, h], dtype=lens.dtype, device=lens.device)
    for _ in range(20):
        if not bool(active.any()):
            break
        P, D, _ = launch_batch(lens, px[..., None] + o, py[..., None] + p, field, para)
        tr = trace_batch(lens, P, D, opl=False, upto=stop)
        qx, qy = tr["x"], tr["y"]
        q0x, q0y = qx[..., 0], qy[..., 0]
        lost = ~(torch.isfinite(q0x) & torch.isfinite(q0y))
        # ★float32 では 1e-10 mm に届かない(丸めが 1e-5 mm)。届かない判定だと毎回 20 反復して float64 より遅かった
        conv = torch.hypot(q0x, q0y) < (1e-10 if lens.dtype == torch.float64 else 1e-5)
        lost_fd = ~torch.isfinite(qx[..., 1:]).all(-1) | ~torch.isfinite(qy[..., 1:]).all(-1)
        a = (qx[..., 1] - q0x) / h
        b = (qx[..., 2] - q0x) / h
        c = (qy[..., 1] - q0y) / h
        d = (qy[..., 2] - q0y) / h
        det = a * d - b * c
        sing = det == 0
        px = torch.where(active & lost, zero, px)
        py = torch.where(active & lost, zero, py)
        go = active & ~lost & ~conv & ~lost_fd & ~sing
        dpx = (-d * q0x + b * q0y) / det
        dpy = (c * q0x - a * q0y) / det
        px = torch.where(go, px + dpx, px)
        py = torch.where(go, py + dpy, py)
        far = go & ((px.abs() > 5.0) | (py.abs() > 5.0))
        px = torch.where(far, zero, px)
        py = torch.where(far, zero, py)
        active = go & ~far
    return px, py


def _aim_at_stop(lens, tx, ty, field, para, gx, gy, cx, cy):
    """``raytrace._aim_at_stop`` の (M, W, R) 版。返り値 ``ux uy failed``(failed は (M, W))。

    光線ごとの減衰 Newton(前進差分の 2x2 ヤコビ行列)。狙いの追跡は半開口を外す。CPU が ValueError にする
    「許容を超えた光線が 1 本でもある」案は failed の印にする。
    """
    stop = lens.system["stop"]
    ap = lens.ap[stop]
    free = dataclasses.replace(lens, ap=torch.full_like(lens.ap, INF))

    def stop_xy(ux, uy):
        P, D, _ = launch_batch(lens, ux, uy, field, para)
        tr = trace_batch(free, P, D, opl=False, upto=stop)
        return tr["sx"], tr["sy"]

    def rel_err(ux, uy):
        sx, sy = stop_xy(ux, uy)
        return torch.hypot(sx - tx, sy - ty) / ap

    ux, uy = gx.clone(), gy.clone()
    err = rel_err(ux, uy)
    bad = ~torch.isfinite(err)
    if bool(bad.any()):                                   # 追えない出発点は中心へ引き寄せる
        s = 1.0
        for _ in range(60):
            s *= 0.9
            ux = torch.where(bad, cx + s * (gx - cx), ux)
            uy = torch.where(bad, cy + s * (gy - cy), uy)
            e = rel_err(ux, uy)
            if bool(torch.isfinite(e[bad]).all()):
                break
        err = rel_err(ux, uy)
    h = 1e-6
    ox = lens.tensor([0.0, h, 0.0])
    oy = lens.tensor([0.0, 0.0, h])
    for _ in range(RT._AIM_MAX_ITER):
        act = ~(err <= RT._AIM_GOAL)
        if not bool(act.any()):
            break
        R = ux.shape[-1]
        big_x = (ux[..., None] + ox).reshape(ux.shape[:-1] + (3 * R,))
        big_y = (uy[..., None] + oy).reshape(uy.shape[:-1] + (3 * R,))
        sx, sy = stop_xy(big_x, big_y)
        sx = sx.reshape(ux.shape + (3,)) - tx[..., None]
        sy = sy.reshape(uy.shape + (3,)) - ty[..., None]
        r0x, r0y = sx[..., 0], sy[..., 0]
        a, b = (sx[..., 1] - r0x) / h, (sx[..., 2] - r0x) / h
        c_, d = (sy[..., 1] - r0y) / h, (sy[..., 2] - r0y) / h
        det = a * d - b * c_
        stx = -(d * r0x - b * r0y) / det
        sty = -(-c_ * r0x + a * r0y) / det
        finite = torch.isfinite(stx) & torch.isfinite(sty)
        stx = torch.where(finite, stx, torch.zeros_like(stx))
        sty = torch.where(finite, sty, torch.zeros_like(sty))
        alpha = torch.ones_like(ux)
        pend = act.clone()
        improved = False
        for _bt in range(14):
            if not bool(pend.any()):
                break
            nx, ny = ux + alpha * stx, uy + alpha * sty
            en = rel_err(nx, ny)
            good = pend & torch.isfinite(en) & (en < err)
            ux = torch.where(good, nx, ux)
            uy = torch.where(good, ny, uy)
            err = torch.where(good, en, err)
            pend = pend & ~good
            improved = improved or bool(good.any())
            alpha = torch.where(pend, 0.5 * alpha, alpha)
        if not improved:
            break
    return ux, uy, (~(err <= RT._AIM_TOL)).any(-1)


def _launch_aimed(lens, qx, qy, field, para, pupil_fill):
    """``raytrace._launch_aimed``: 瞳の点 *q* (R,) を絞りの点へ。返り値 ``P D opl0 failed``。"""
    ap = lens.ap[lens.system["stop"]]
    shape = (lens.M, lens.W, 1)
    z1 = torch.zeros(shape, dtype=lens.dtype, device=lens.device)
    cx, cy, f0 = _aim_at_stop(lens, z1, z1, field, para, z1, z1, z1, z1)
    Q = (lens.M, lens.W, qx.shape[-1])
    qx, qy = qx.expand(Q), qy.expand(Q)
    ux, uy, f1 = _aim_at_stop(lens, qx * ap * pupil_fill, qy * ap * pupil_fill, field, para,
                              qx * pupil_fill + cx, qy * pupil_fill + cy, cx, cy)
    P, D, opl0 = launch_batch(lens, ux, uy, field, para)
    return P, D, opl0, f0 | f1


def _exit_angles(tr):
    az = tr["N"].abs()
    return (torch.rad2deg(torch.atan2(tr["L"], az)) * 60.0, torch.rad2deg(torch.atan2(tr["M"], az)) * 60.0)


_RAY_KEYS = ("x", "y", "z", "L", "M", "N", "xl", "yl", "zl", "valid", "opl", "opl_last", "opl0")


def bundle_batch(lens, field=None, rings=8, kind="hexapolar", pupil_fill=1.0, image_mm=None, para=None, px=None,
                 py=None, opl=False, points=False, visitor=None, vignette=True):
    """``raytrace.ray_bundle`` を (M, W, R) で(``aim`` とケラレ係数は系のもの)。

    返り値: :func:`trace_batch` の鍵 + ``chief_x`` ``chief_y`` (M, W)、``para``、``failed`` (M, W)
    (入射瞳が無限遠 / 絞りを結像できない / 狙いが収束しない案。その案の光線は全部無効)、``opl0``。
    ``afocal`` の系では ``x`` ``y`` は像面の位置でなく射出角(分)。*vignette*: False でケラレの圧縮をしない
    (:func:`opd_batch` はマスクとして扱う)。
    """
    sysd = lens.system
    field = sysd["field"] if field is None else RT._finite(field, "field")
    para = paraxial_batch(lens) if para is None else para
    if px is None:
        px, py = RT._pupil_grid(rings, kind)
    px, py = np.asarray(px, float), np.asarray(py, float)
    ic = int(np.argmin(px * px + py * py))
    v = RT._vig_at(sysd, field) if vignette else None
    if v is None:
        qx, qy = px, py
    else:
        qx, qy = RT._vig_forward(px, py, v)
        qx, qy = np.append(qx, 0.0), np.append(qy, 0.0)    # ケラレのない主光線は最後
    gx, gy = lens.tensor(qx), lens.tensor(qy)
    failed = para["failed"] | ~torch.isfinite(para["ep_radius"]) | ~torch.isfinite(para["ep_position"])
    if sysd.get("aim", "paraxial") == "stop":
        P, D, opl0, fa = _launch_aimed(lens, gx, gy, field, para, pupil_fill)
        failed = failed | fa
    else:
        dpx, dpy = _chief_offset(lens, field, para)
        P, D, opl0 = launch_batch(lens, gx + dpx[..., None], gy + dpy[..., None], field, para, pupil_fill)
    tr = trace_batch(lens, P, D, image_mm=image_mm, opl=opl, points=points, visitor=visitor)
    tr["opl0"] = opl0
    if bool(failed.any()):
        tr["valid"] = tr["valid"] & ~failed[..., None]
    if sysd.get("afocal"):
        tr["x"], tr["y"] = _exit_angles(tr)
    if v is None:
        cx, cy = tr["x"][..., ic], tr["y"][..., ic]
    else:
        cx, cy = tr["x"][..., -1], tr["y"][..., -1]
        tr["chief_rays"] = {k: tr[k][..., -1:] for k in _RAY_KEYS if tr.get(k) is not None}
        for k in _RAY_KEYS:
            if tr.get(k) is not None:
                tr[k] = tr[k][..., :len(px)]
    tr.update({"chief_x": cx, "chief_y": cy, "chief_index": ic, "para": para, "failed": failed, "field": field,
               "px": lens.tensor(px), "py": lens.tensor(py)})
    return tr


def spot_stats_batch(b):
    """:func:`bundle_batch` の結果から ``raytrace.spot_stats`` の量を (M, W) で。光線が 0 本の案は NaN。"""
    v = b["valid"]
    x, y = torch.nan_to_num(b["x"]), torch.nan_to_num(b["y"])
    m = v.to(x.dtype)
    cnt = m.sum(-1)
    safe = cnt.clamp(min=1.0)
    cx = (x * m).sum(-1) / safe
    cy = (y * m).sum(-1) / safe
    dx, dy = (x - cx[..., None]) * m, (y - cy[..., None]) * m
    r2 = dx * dx + dy * dy
    rms = torch.sqrt(r2.sum(-1) / safe)
    geo = torch.sqrt(r2.amax(-1))
    empty = cnt == 0
    nan = float("nan")
    return {"rms_radius": rms.masked_fill(empty, nan), "geo_radius": geo.masked_fill(empty, nan),
            "centroid_x": cx.masked_fill(empty, nan), "centroid_y": cy.masked_fill(empty, nan),
            "n_rays": cnt.to(torch.int64), "n_vignetted": (~v).sum(-1)}


def chromatic_batch(lens, field=None, rings=6, image_mm=None):
    """``raytrace.chromatic_shift`` の量を波長軸に一括で。各値は (M, W)、要約は (M,)。

    基準像面は設計波長の値に固定する(``chromatic_shift`` と同じ)。``rms_polychromatic`` は全波長の
    全光線を共通の重心のまわりで測る。
    """
    sysd = lens.system
    field = sysd["field"] if field is None else RT._finite(field, "field")
    img = _chromatic_image(lens) if image_mm is None else lens.tensor([[float(image_mm)]]).expand(lens.M, 1)
    b = bundle_batch(lens, field=field, rings=rings, image_mm=img)
    st = spot_stats_batch(b)
    p = b["para"]
    v = b["valid"]
    x, y = torch.nan_to_num(b["x"]), torch.nan_to_num(b["y"])
    m = v.to(x.dtype)
    cnt = m.sum((-1, -2)).clamp(min=1.0)
    cx = (x * m).sum((-1, -2)) / cnt
    cy = (y * m).sum((-1, -2)) / cnt
    dx, dy = (x - cx[..., None, None]) * m, (y - cy[..., None, None]) * m
    poly = torch.sqrt((dx * dx + dy * dy).sum((-1, -2)) / cnt)
    return {"wavelength_um": lens.wl, "efl": p["efl"], "bfl": p["bfl"], "chief_height": b["chief_y"],
            "rms_spot": st["rms_radius"], "n_rays": st["n_rays"], "axial_color": p["bfl"][:, 0] - p["bfl"][:, -1],
            "lateral_color": b["chief_y"][:, 0] - b["chief_y"][:, -1], "efl_range": p["efl"].amax(1) - p["efl"].amin(1),
            "rms_polychromatic": poly, "reference_image_mm": img, "field": field}


# --------------------------------------------------------------------------- #
# 波面と MTF
# --------------------------------------------------------------------------- #
def opd_batch(lens, field=None, size=64, image_mm=None):
    """``raytrace.opd_samples`` の量を (M, W, size²) で: ``px py opd valid`` と ``para``。"""
    sysd = lens.system
    field = sysd["field"] if field is None else RT._finite(field, "field")
    g = np.linspace(-1.0, 1.0, int(size))
    gx, gy = np.meshgrid(g, g)
    px, py = gx.ravel(), gy.ravel()
    ins = px * px + py * py <= 1.0 + 1e-12
    v = RT._vig_at(sysd, field)
    if v is not None:                                              # ケラレはここではマスク(格子は物理の瞳のまま)
        x0, y0 = RT._vig_inverse(px, py, v)
        ins &= x0 * x0 + y0 * y0 <= 1.0 + 1e-12
    inside = lens.tensor(ins.astype(float)) > 0.5
    if sysd.get("aim", "paraxial") == "stop":                      # 瞳の外の角は狙えないので中心へ
        pxa, pya = np.append(np.where(ins, px, 0.0), 0.0), np.append(np.where(ins, py, 0.0), 0.0)
    else:
        pxa, pya = np.append(px, 0.0), np.append(py, 0.0)          # 主光線は最後
    para = paraxial_batch(lens)
    img = _reference_image(lens) if image_mm is None else lens.tensor(image_mm)
    tr = bundle_batch(lens, field=field, px=pxa, py=pya, image_mm=img, para=para, opl=True, vignette=False)
    wl = lens.wl[None, :, None]
    if sysd.get("afocal"):                                         # 射出は平行光: 基準は平面波
        pxl, pyl, pzl = tr["xl"], tr["yl"], tr["zl"]
        dx, dy, dz = tr["L"], tr["M"], tr["N"]
        cx_, cy_, cz_ = dx[..., -1:], dy[..., -1:], dz[..., -1:]
        s = (((pxl[..., -1:] - pxl) * cx_ + (pyl[..., -1:] - pyl) * cy_ + (pzl[..., -1:] - pzl) * cz_)
             / (dx * cx_ + dy * cy_ + dz * cz_))
        opl_ref = tr["opl_last"] + tr["opl0"] + tr["n_image"] * s
        valid = tr["valid"] & torch.isfinite(opl_ref)
        w = ((opl_ref[..., -1:] - opl_ref) / (wl * 1e-3)).masked_fill(~valid, float("nan"))
        return {"px": px, "py": py, "opd": w[..., :-1], "valid": valid[..., :-1] & inside, "para": para,
                "degenerate": tr["failed"]}
    Cx, Cy, Cz = tr["x"][..., -1:], tr["y"][..., -1:], tr["z"][..., -1:]
    dirn = torch.where(tr["N"][..., -1:] >= 0, 1.0, -1.0).to(lens.dtype)
    img3 = img[..., None] if img.ndim == 2 else img
    z_last = tr["z_image"] - dirn * img3
    z_xp = z_last + dirn * para["xp_position"][..., None]
    Rref = (Cz - z_xp).abs()
    Pz, Dz = tr["zl"], tr["N"]
    ox, oy, oz = tr["xl"] - Cx, tr["yl"] - Cy, Pz - Cz
    b = ox * tr["L"] + oy * tr["M"] + oz * Dz
    cc = ox * ox + oy * oy + oz * oz - Rref * Rref
    disc = b * b - cc
    ok = disc >= 0
    sq = torch.sqrt(torch.where(ok, disc, torch.zeros_like(disc)))
    s1, s2 = -b - sq, -b + sq
    z1, z2 = Pz + s1 * Dz, Pz + s2 * Dz
    s = torch.where((z1 - z_xp).abs() <= (z2 - z_xp).abs(), s1, s2)
    opl_ref = tr["opl_last"] + tr["opl0"] + tr["n_image"] * s
    valid = tr["valid"] & ok
    w = (opl_ref[..., -1:] - opl_ref) / (wl * 1e-3)
    w = w.masked_fill(~valid, float("nan"))
    return {"px": px, "py": py, "opd": w[..., :-1], "valid": valid[..., :-1] & inside, "para": para,
            "degenerate": ~torch.isfinite(Rref[..., 0]) | (Rref[..., 0] < 1e-9) | tr["failed"]}


def _working_fno(para):
    na = para["na_image"]
    use_na = (na > 0) & torch.isfinite(na)
    return torch.where(use_na, 1.0 / (2.0 * na), para["fno"])


def mtf_batch(lens, field=None, size=64, frequency_cpmm=(10.0, 30.0, 50.0), image_mm=None, oversample=2, chunk=64):
    """``lensimage.through_focus_mtf`` の焦点 1 位置を (M, W) で: ``tangential`` ``sagittal`` (M, W, F)。

    瞳の位相から PSF を FFT し、その OTF の軸上の断面を読む。周波数は (M, W) ごとに格子が違うので
    線形補間も案ごと。``aliased`` (M, W): 隣の標本で位相が 0.5 波を超える(CPU は ValueError)、
    または有効な瞳の標本が 16 未満。その案は NaN。
    """
    f = np.atleast_1d(np.asarray(frequency_cpmm, dtype=float)).ravel()
    if f.size < 1 or not np.all(np.isfinite(f)) or np.any(f < 0.0):
        raise ValueError("frequency_cpmm must be finite and >= 0, got %r" % (frequency_cpmm,))
    size = int(size)
    o = opd_batch(lens, field=field, size=size, image_mm=image_mm)
    n = size
    mask = o["valid"].reshape(lens.M, lens.W, n, n)
    W = torch.nan_to_num(o["opd"]).reshape(lens.M, lens.W, n, n)
    W = torch.where(mask, W, torch.zeros_like(W))
    dxm = (W[..., :, 1:] - W[..., :, :-1]).abs() * (mask[..., :, 1:] & mask[..., :, :-1])
    dym = (W[..., 1:, :] - W[..., :-1, :]).abs() * (mask[..., 1:, :] & mask[..., :-1, :])
    step = torch.maximum(dxm.amax((-1, -2)), dym.amax((-1, -2)))
    aliased = (step > 0.5) | (mask.sum((-1, -2)) < 16) | o["degenerate"]
    Mg = (size - 1) * int(oversample)
    if Mg % 2:
        Mg += 1
    if Mg > 8192:
        raise ValueError("FFT grid %d too large; reduce size or oversample" % Mg)
    fno = _working_fno(o["para"])
    dx = lens.wl[None, :] * fno * (size - 1) / Mg
    nyq = 0.5e3 / dx
    if bool((lens.tensor(f.max()) > nyq[~aliased] * (1.0 + 1e-9)).any()):
        raise ValueError("a frequency is above the Nyquist limit of the PSF grid for this batch")
    ctype = torch.complex128 if lens.dtype == torch.float64 else torch.complex64
    B = lens.M * lens.W
    W1 = W.reshape(B, n, n)
    m1 = mask.reshape(B, n, n)
    rows, cols = [], []
    for i in range(0, B, int(chunk)):
        ph = 2.0 * math.pi * W1[i:i + chunk]
        P = torch.polar(m1[i:i + chunk].to(lens.dtype), ph).to(ctype)
        pad = torch.zeros((P.shape[0], Mg, Mg), dtype=ctype, device=lens.device)
        pad[:, :n, :n] = P
        psf = torch.fft.fft2(pad).abs() ** 2
        psf = psf / psf.sum((-1, -2), keepdim=True)
        otf = torch.fft.fft2(psf.to(ctype))
        dc = otf[:, 0, 0].abs()[:, None]
        rows.append(otf[:, : Mg // 2 + 1, 0].abs() / dc)
        cols.append(otf[:, 0, : Mg // 2 + 1].abs() / dc)
    rows = torch.cat(rows).reshape(lens.M, lens.W, -1)
    cols = torch.cat(cols).reshape(lens.M, lens.W, -1)
    ff = lens.tensor(f)
    idx = ff[None, None, :] * (Mg * dx[..., None]) / 1e3            # 格子の番号(小数)
    i0 = idx.floor().clamp(0, Mg // 2 - 1).to(torch.int64)
    a = idx - i0

    def interp(tab):
        v0 = torch.gather(tab, -1, i0)
        v1 = torch.gather(tab, -1, i0 + 1)
        return (v0 * (1.0 - a) + v1 * a).masked_fill(aliased[..., None], float("nan"))

    return {"frequency_cpmm": f, "tangential": interp(rows), "sagittal": interp(cols), "fno": fno, "aliased": aliased}


# --------------------------------------------------------------------------- #
# 分光透過
# --------------------------------------------------------------------------- #
def spectral_transmission(lens, field=None, rings=6, pupil_fill=1.0, image_mm=None, fresnel=True, absorption=True):
    """瞳で平均した分光透過率 ``T`` (M, W)。``valid_fraction`` はケラレの分だけ落ちる(失った光線は 0)。

    定義は既存のものに合わせた: 面ごとの Fresnel 損失は ``lensrender`` の無偏光の式(コートなし)
    ``1 − (R_s + R_p)/2``、内部透過は ``materials`` の ``exp(−αd)``(``α = 4πk/λ``)を媒質内の光線長 d で。
    カタログの Sellmeier 硝子と ``(nd, vd)`` には k のデータが無いので吸収は 0 になる
    (``materials`` の透過材を名指しすると k が入る)。多重反射は足さない(逐次追跡の 1 回通過)。
    返り値: ``T`` ``T_fresnel`` ``T_internal`` (M, W)、``T_ray`` (M, W, R)、``valid`` (M, W, R)。
    """
    state = {"logF": None, "logA": None}
    alpha = lens.alpha[None, :, :]

    def visit(i, info):
        if state["logF"] is None:
            state["logF"] = torch.zeros_like(info["t"])
            state["logA"] = torch.zeros_like(info["t"])
        if i > 0 or lens.alpha[:, 0].any():
            a = alpha[..., i:i + 1]
            if absorption:
                state["logA"] = state["logA"] - a * torch.nan_to_num(info["t"]).abs() * 1e3
        if fresnel and i < lens.S and info["cos_t"] is not None:
            n1, n2, ci, ct = info["n1"], info["n2"], info["cos_i"], info["cos_t"]
            rs = ((n1 * ci - n2 * ct) / (n1 * ci + n2 * ct)) ** 2
            rp = ((n1 * ct - n2 * ci) / (n1 * ct + n2 * ci)) ** 2
            state["logF"] = state["logF"] + torch.log(torch.nan_to_num(1.0 - 0.5 * (rs + rp), nan=1.0).clamp(min=1e-300))

    b = bundle_batch(lens, field=field, rings=rings, pupil_fill=pupil_fill, image_mm=image_mm, visitor=visit)
    v = b["valid"]
    m = v.to(lens.dtype)
    Tf = torch.exp(state["logF"]) * m
    Ta = torch.exp(state["logA"]) * m
    Tr = Tf * torch.exp(state["logA"])
    R = v.shape[-1]
    return {"wavelength_um": lens.wl, "T": Tr.sum(-1) / R, "T_fresnel": Tf.sum(-1) / R, "T_internal": Ta.sum(-1) / R,
            "T_ray": Tr, "valid": v, "valid_fraction": m.sum(-1) / R}


# --------------------------------------------------------------------------- #
# 公差モンテカルロ
# --------------------------------------------------------------------------- #
def tolerance_draws(system, tolerances=None, trials=1000, seed=0):
    """``raytrace._perturbed`` と**同じ乱数列**で (M, S) の摂動を作る。

    ``_perturbed`` は面の順に ``rng.uniform(-1, 1)`` を 1 つずつ引くので、同じ本数を 1 度に引けば同じ値になる。
    返り値: ``R t offset decenter tilt`` と、``lens_system`` が拒否する案の印 ``rejected`` (M,)。
    """
    tol = {"radius_pct": 0.5, "thickness_mm": 0.05, "index": 0.001, "decenter_mm": 0.02, "tilt_deg": 0.05}
    if tolerances:
        for k, v in tolerances.items():
            if k not in tol:
                raise ValueError("unknown tolerance %r (choose from %s)" % (k, sorted(tol)))
            tol[k] = RT._finite(v, k, nonneg=True)
    trials = int(trials)
    if trials < 1:
        raise ValueError("trials must be >= 1")
    surf = system["surfaces"]
    S = len(surf)
    plan = []
    for i, s in enumerate(surf):
        if tol["radius_pct"] and s["R"] != INF:
            plan.append(("R", i))
        if tol["thickness_mm"] and s["t"] is not None:
            plan.append(("t", i))
        if tol["index"] and not s["mirror"] and s["n_value"] > 1.0 and s.get("f") is None:
            plan.append(("n", i))
        if tol["decenter_mm"]:
            plan.extend((("dx", i), ("dy", i)))
        if tol["tilt_deg"]:
            plan.extend((("ax", i), ("ay", i)))
    rng = np.random.default_rng(int(seed))
    u = rng.uniform(-1, 1, size=(trials, len(plan)))
    R = np.tile([s["R"] for s in surf], (trials, 1)).astype(float)
    t = np.tile([0.0 if s["t"] is None else s["t"] for s in surf], (trials, 1)).astype(float)
    off = np.zeros((trials, S))
    dec = np.tile(np.array([s["decenter"] for s in surf], float), (trials, 1, 1))
    tilt = np.tile(np.array([s["tilt"] for s in surf], float), (trials, 1, 1))
    for j, (what, i) in enumerate(plan):
        v = u[:, j]
        if what == "R":
            R[:, i] = R[:, i] * (1.0 + v * tol["radius_pct"] / 100.0)
        elif what == "t":
            t[:, i] = np.maximum(0.0, t[:, i] + v * tol["thickness_mm"])
        elif what == "n":
            off[:, i] = v * tol["index"]
        elif what == "dx":
            dec[:, i, 0] += v * tol["decenter_mm"]
        elif what == "dy":
            dec[:, i, 1] += v * tol["decenter_mm"]
        elif what == "ax":
            tilt[:, i, 0] += v * tol["tilt_deg"]
        else:
            tilt[:, i, 1] += v * tol["tilt_deg"]
    rejected = np.zeros(trials, bool)
    for i, s in enumerate(surf):                     # lens_system の「半開口が円錐の範囲を超える」
        if s["ap"] is not None and s["k"] > -1.0 and s["R"] != INF:
            rejected |= (1.0 + s["k"]) * (s["ap"] / R[:, i]) ** 2 > 1.0
    return {"R": R, "t": t, "offset": off, "decenter": dec, "tilt": tilt, "rejected": rejected, "tolerances": tol}


def bytes_per_ray(n_surfaces, aimed=False):
    """1 光線が追跡中に占めるメモリの見積もり [byte]。

    ★実測で較正した(2026-11-02): triplet(6 面)の実演 1 のピークは 1 光線 1357 byte で、最初の見積もり
    384 byte は 3.5 倍過小だった。余裕を 1.4 倍取り ``8 (60 + 30 S)``。``aim="stop"`` は 3 倍の光線を積むので 4 倍。
    """
    return 8.0 * (60.0 + 30.0 * int(n_surfaces)) * (4.0 if aimed else 1.0)


def _is_oom(e):
    return isinstance(e, torch.cuda.OutOfMemoryError) or (isinstance(e, RuntimeError) and "out of memory" in str(e).lower())


def _free_items(device, bytes_per_item, reserve):
    if str(device).startswith("cuda"):
        free = torch.cuda.mem_get_info(torch.device(device))[0]
        return max(1, int(reserve * free / bytes_per_item))
    return max(1, int(CPU_CHUNK_BYTES / bytes_per_item))


def run_split(device, n, bytes_per_item, fn, chunk=None, reserve=0.5):
    """*n* 個の仕事を空きメモリに合わせて分けて ``fn(a, b, device)`` に渡す。返り値は統計の dict。

    GPU の空きは**分割のたびに読み直す**(CARLA など別のプロセスが途中で増やすため)。空きの *reserve* までしか
    使わない。それでも OOM なら分割を半分にして同じ区間をやり直し、1 個でも入らなければ残りを CPU で続ける
    (落とさない。遅くなったことは ``fell_back_to_cpu`` に残す)。*fn* は区間の結果を自分で書き込むこと。
    """
    n = int(n)
    a = 0
    cap = n if chunk is None else max(1, int(chunk))
    stats = {"chunks": 0, "oom_retries": 0, "fell_back_to_cpu": False, "smallest_chunk": n}
    dev = device
    while a < n:
        k = max(1, min(cap, n - a, _free_items(dev, bytes_per_item, reserve)))
        try:
            fn(a, a + k, dev)
        except (RuntimeError, MemoryError) as e:
            if isinstance(e, RuntimeError) and not _is_oom(e):
                raise
            if not str(dev).startswith("cuda"):
                raise
            torch.cuda.empty_cache()
            stats["oom_retries"] += 1
            if k == 1:
                dev = "cpu"
                stats["fell_back_to_cpu"] = True
                cap = n
            else:
                cap = max(1, k // 2)
            continue
        a += k
        stats["chunks"] += 1
        stats["smallest_chunk"] = min(stats["smallest_chunk"], k)
    return stats


def tolerance_monte_carlo(system, tolerances=None, trials=1000, seed=0, field=None, rings=6, compensator="auto",
                          wavelengths=None, device="auto", dtype="float64", chunk=None, pupil_fill=0.99):
    """``raytrace.tolerance_analysis`` の MC 部を一括で(感度表は作らない)。

    同じ *seed* なら案ごとに同じ摂動を引き、``efl`` と ``rms_spot`` の分布が CPU と一致する。*wavelengths* を
    与えると ``rms_spot_w`` (M, W) も返す(像面は設計波長で決める)。CPU が例外で数えない案は ``failed``。
    系の ``aim`` / ケラレ係数 / ``image_R`` は摂動した案にも効く(CPU の ``_perturbed`` も 2026-11-02 に揃えた)。
    """
    system = RT._freeze_solves(_check_supported(system))
    if compensator not in ("auto", "back_focus", "none"):
        raise ValueError("compensator must be 'auto', 'back_focus' or 'none', got %r" % (compensator,))
    field = system["field"] if field is None else RT._finite(field, "field")
    design_wl = float(system["wavelength_um"])
    wls = [design_wl] + ([] if wavelengths is None else [float(w) for w in _wl_array(wavelengths)])
    R = len(RT._pupil_grid(rings)[0])
    dev = _device(device, int(trials) * len(wls) * R * len(system["surfaces"]))
    d = tolerance_draws(system, tolerances, trials, seed)
    if system["image_mm"] is not None:
        img_nom = system["image_mm"]
    elif system["surfaces"][-1]["t"] is not None:
        img_nom = system["surfaces"][-1]["t"]
    else:
        img_nom = RT.paraxial_trace(system)["image_mm"]
    if compensator == "auto":
        used = "back_focus" if (system["image_mm"] is None and system["surfaces"][-1]["t"] is None) else "none"
    else:
        used = compensator
    trials = int(trials)
    efl = np.full(trials, np.nan)
    rms = np.full((trials, len(wls)), np.nan)
    failed = d["rejected"].copy()

    def one(a, b_, device_now):
        ov = {k: d[k][a:b_] for k in ("R", "t", "offset", "decenter", "tilt")}
        lens = compile_lens(system, wls, device=device_now, dtype=dtype, overrides=ov)
        p = paraxial_batch(lens)
        img = p["image_mm"][:, :1] if used == "back_focus" else lens.tensor([[img_nom]]).expand(lens.M, 1)
        b = bundle_batch(lens, field=field, rings=rings, pupil_fill=pupil_fill, image_mm=img, para=p)
        st = spot_stats_batch(b)
        efl[a:b_] = p["efl"][:, 0].detach().cpu().numpy()
        rms[a:b_] = st["rms_radius"].detach().cpu().numpy()
        failed[a:b_] |= (b["failed"].any(1) | (st["n_rays"][:, 0] == 0)).detach().cpu().numpy()

    aimed = system.get("aim", "paraxial") == "stop"
    per_design = R * len(wls) * bytes_per_ray(len(system["surfaces"]), aimed)
    split = run_split(dev, trials, per_design, one, chunk=chunk)
    ok = ~failed

    def dist(v):
        if len(v) == 0:
            return {"mean": INF, "std": INF, "p5": INF, "p95": INF, "worst": INF}
        return {"mean": float(v.mean()), "std": float(v.std()), "p5": float(np.percentile(v, 5)),
                "p95": float(np.percentile(v, 95)), "worst": float(v.max())}

    return {"efl": dist(efl[ok]), "rms_spot": dist(rms[ok, 0]), "efl_trial": efl, "rms_trial": rms[:, 0],
            "rms_spot_w": rms[:, 1:] if len(wls) > 1 else None, "failed_trial": failed, "failed": int(failed.sum()),
            "trials": trials, "seed": int(seed), "compensator": used, "tolerances": d["tolerances"], "device": dev,
            "chunk": split["smallest_chunk"], "split": split, "rays_per_design": R, "wavelengths_um": wls}


def marginal_focus(lens, h):
    """``chromconf._marginal_focus`` の (M, W) 版: 高さ *h* の平行光線が光軸と交わる位置。無効な案は NaN。"""
    z0 = torch.zeros((lens.M, lens.W, 1), dtype=lens.dtype, device=lens.device)
    tr = trace_batch(lens, (z0, z0 + float(h), z0 - 1.0), (z0, z0, z0 + 1.0), image_mm=[[50.0]], opl=False)
    zl = lens.t[:, :-1].sum(-1)[:, None, None]
    f = tr["zl"] + (-tr["yl"] / tr["M"]) * tr["N"] - zl
    bad = ~tr["valid"] | (tr["M"].abs() < 1e-15)
    return f.masked_fill(bad, float("nan"))[..., 0]


def chromatic_sweep(system, wavelengths, field=None, rings=6, device="auto", dtype="float64", chunk=None):
    """:func:`chromatic_batch` を波長軸で分割して回す(波長が多くても VRAM に収める)。返り値は numpy (W,)。"""
    system = _check_supported(system)
    wl = _wl_array(wavelengths)
    R = len(RT._pupil_grid(rings)[0])
    S = len(system["surfaces"])
    dev = _device(device, wl.size * R * S)
    keys = ("efl", "bfl", "chief_height", "rms_spot", "n_rays")
    out = {k: np.zeros(wl.size) for k in keys}
    ref = compile_lens(system, device="cpu")
    img = float(_chromatic_image(ref)[0, 0])

    def one(a, b_, device_now):
        c = chromatic_batch(compile_lens(system, wl[a:b_], device=device_now, dtype=dtype), field=field, rings=rings, image_mm=img)
        for k in keys:
            out[k][a:b_] = c[k][0].detach().cpu().numpy()

    split = run_split(dev, wl.size, R * bytes_per_ray(S, system.get("aim", "paraxial") == "stop"), one, chunk=chunk)
    out.update({"wavelength_um": wl, "axial_color": out["bfl"][0] - out["bfl"][-1],
                "lateral_color": out["chief_height"][0] - out["chief_height"][-1], "split": split, "device": dev})
    return out
