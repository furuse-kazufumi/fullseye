# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""粉末 X 線回折を測る —— 2-D 検出器の環から相を同定して分ける(規則だけ、学習なし、2026-10-05)。

2-D 検出器に写ったデバイ環(Debye–Scherrer 環)から、検出器の幾何を較正し、方位積分で 1-D の 2θ プロファイルに落とし、
山を拾って立方晶なら指数を付け、結晶構造(CIF)から作った参照パターンの辞書と非負の最小二乗で相の重量分率を出し、
説明しきれない山を残差から取り出す。混合物の相を 1 つずつ剥がす貪欲な前進選択(:func:`phase_peel`)もある。
背景: 多相の回折パターンを 1 回の観測から分解する研究(npj Comput. Mater. 2026、doi:10.1038/s41524-026-02087-w)は
生成モデルで分けている。ここは同じ問いを **学習なし** の物理模型(Bragg・構造因子・Lorentz 因子・Scherrer)で解く。

一次情報で確かめた定義と式(読んだものだけ):

- **Bragg**: ``λ = 2 d sin θ``。角は ``θ = atan2(s, sqrt((1 − s)(1 + s)))``、``s = λ / (2d)``(acos / asin は端で
  丸めの床がある)。``s > 1`` の反射は存在しない(:func:`powder_reflections` が落とす)。
- **面間隔**: 逆格子の計量 ``G* = G⁻¹``、``1/d² = hᵀ G* h``(三斜晶まで一般)。
- **構造因子**: ``F(hkl) = Σⱼ occⱼ fⱼ(s) exp(−Bⱼ s²) exp(2πi (h xⱼ + k yⱼ + l zⱼ))``、``s = sin θ / λ = 1/(2d)``、
  ``B = 8π² U_iso``。原子の散乱因子 ``f₀(s) = c + Σ₁⁵ aᵢ exp(−bᵢ s²)`` は Waasmaier & Kirfel, Acta Cryst. A51 (1995)
  416–431 の 5 ガウス近似(係数は DABAX の f0_WaasKirf.dat から機械的に写した。:data:`FORM_FACTORS`)。異常分散
  (f′, f″)は **入れていない**。
- **Lorentz 因子**: 粉末の環 1 本の全強度は ``m |F|² cos θ / sin 2θ`` に比例し(反射の位置にある結晶の割合 cos θ と、
  逆格子点が Ewald 球を横切る速さ 1/sin 2θ)、それが円周 ``2π sin 2θ`` に広がるので、環の上の単位立体角あたり
  ``∝ m |F|² / (sin θ · sin 2θ) = m |F|² / (2 sin² θ cos θ)``(``lorentz="powder"``)。これは走査型の回折計の
  ``1 / (sin² θ cos θ)`` と **定数倍しか違わない**(受光スリットが環の一部を切るのと、2-D 検出器が環の単位長さを
  見るのは同じ量)—— 2026-10-05 の試作で 2 つを別の選択肢にしたら相分率が小数 4 桁まで同じで、そこから気付いた。
- **偏光**: 直線偏光の度合い ``p``(0 = 無偏光の管球、1 = 水平偏光の放射光)で
  ``P(2θ, χ) = ½ (1 + cos² 2θ) − ½ p cos 2χ sin² 2θ``。
- **Scherrer**: ``L = K λ / (β cos θ)``、``β`` は試料による広がりの FWHM [rad]。装置の広がりはガウスとして 2 乗で引く
  (``β² = B_obs² − B_inst²``)。``K = 0.9`` が既定(球・FWHM の慣用値。形と定義で 0.89〜0.94 の幅がある)。
- **重量分率**: 混合物の吸収が全相で共通(透過配置、微視的吸収なし)と置くと、相 p の強度の倍率は体積分率 vₚ に比例し
  ``vₚ ∝ Wₚ / ρₚ``、``ρ = Σ occ·m / (N_A V)``。NNLS の倍率 sₚ から ``Wₚ ∝ sₚ ρₚ``(Hill & Howard 1987 の ZMV と同じ形)。
- **立方晶の指数付け**: ``1/d² = N / a²``、``N = h² + k² + l²``。消滅則は P(全部)、I(h+k+l 偶数)、F(全偶か全奇)、
  diamond(F かつ「全偶で h+k+l = 4n+2」を除く)。候補は de Wolff の M 型の性能指数(最後の観測線までの計算線の数で割る)で比べる。

検出器の幾何(Fit2D 型): ビームは +z、試料は原点。``(cx, cy)`` はビームが検出器に当たる画素(列, 行の順に x, y)、
``distance`` は試料からその点までのビームに沿った距離 [mm]、``pixel`` は画素の辺 [mm]、``tilt`` は検出器の法線と
ビームのなす角 [deg]、``tilt_dir`` は傾きの回転軸の向き(検出器面内、+列から測った角 [deg])。``wavelength`` は Å
(CIF の格子定数と同じ単位)。画素 (row, col) の 2θ = ``atan2(hypot(Pₓ, P_y), P_z)``、方位 χ = ``atan2(P_y, Pₓ)``。

失敗はすべて ``ValueError``(綴り違い・空・非有限・形の不一致・存在しない元素・環が見つからない較正)。
"""
from __future__ import annotations

import math
import re

import numpy as np

__all__ = [
    "FORM_FACTORS", "ATOMIC_MASS", "LATTICES", "PROTOTYPES",
    "cif_read", "cubic_prototype", "powder_reflections", "scherrer_size",
    "debye_ring_image", "detector_two_theta", "detector_calibrate", "azimuthal_integrate",
    "diffraction_peaks", "cubic_index",
    "phase_dictionary", "phase_fractions", "unexplained_peaks", "phase_peel",
]

#: 原子(イオン)の散乱因子の 5 ガウス近似: 名前 → (原子番号, (a1..a5, c, b1..b5))。``f₀(s) = c + Σ aᵢ exp(−bᵢ s²)``、
#: ``s = sin θ / λ`` [Å⁻¹]。Waasmaier & Kirfel 1995(DABAX の f0_WaasKirf.dat から機械的に写した、手で打っていない)。
FORM_FACTORS = {
    "C": (6, (2.657506, 1.078079, 1.490909, -4.241070, 0.713791, 4.297983, 14.780758, 0.776775, 42.086842, -0.000294, 0.239535)),
    "O": (8, (2.960427, 2.508818, 0.637853, 0.722838, 1.142756, 0.027014, 14.182259, 5.936858, 0.112726, 34.958481, 0.390240)),
    "O2-": (8, (3.990247, 2.300563, 0.607200, 1.907882, 1.167080, 0.025429, 16.639956, 5.636819, 0.108493, 47.299709, 0.379984)),
    "F": (9, (3.511943, 2.772244, 0.678385, 0.915159, 1.089261, 0.032557, 10.687859, 4.380466, 0.093982, 27.255203, 0.313066)),
    "F1-": (9, (0.457649, 3.841561, 1.432771, 0.801876, 3.395041, 0.069525, 0.917243, 5.507803, 0.164955, 51.076206, 15.821679)),
    "Na": (11, (4.910127, 3.081783, 1.262067, 1.098938, 0.560991, 0.079712, 3.281434, 9.119178, 0.102763, 132.013947, 0.405878)),
    "Na1+": (11, (3.148690, 4.073989, 0.767888, 0.995612, 0.968249, 0.045300, 2.594987, 6.046925, 0.070139, 14.122657, 0.217037)),
    "Mg": (12, (4.708971, 1.194814, 1.558157, 1.170413, 3.239403, 0.126842, 4.875207, 108.506081, 0.111516, 48.292408, 1.928171)),
    "Mg2+": (12, (3.062918, 4.135106, 0.853742, 1.036792, 0.852520, 0.058851, 2.015803, 4.417941, 0.065307, 9.669710, 0.187818)),
    "Al": (13, (4.730796, 2.313951, 1.541980, 1.117564, 3.154754, 0.139509, 3.628931, 43.051167, 0.095960, 108.932388, 1.555918)),
    "Al3+": (13, (4.132015, 0.912049, 1.102425, 0.614876, 3.219136, 0.019397, 3.528641, 7.378344, 0.133708, 0.039065, 1.644728)),
    "Si": (14, (5.275329, 3.191038, 1.511514, 1.356849, 2.519114, 0.145073, 2.631338, 33.730728, 0.081119, 86.288643, 1.170087)),
    "Cl": (17, (1.446071, 6.870609, 6.151801, 1.750347, 0.634168, 0.146773, 0.052357, 1.193165, 18.343416, 46.398396, 0.401005)),
    "Cl1-": (17, (1.061802, 7.139886, 6.524271, 2.355626, 35.829403, -34.916603, 0.144727, 1.171795, 19.467655, 60.320301, 0.000436)),
    "K": (19, (8.163991, 7.146945, 1.070140, 0.877316, 1.486434, 0.253614, 12.816323, 0.808945, 210.327011, 39.597652, 0.052821)),
    "K1+": (19, (-17.609339, 1.494873, 7.150305, 10.899569, 15.808228, 0.257164, 18.840979, 0.053453, 0.812940, 22.264105, 14.351593)),
    "Ca": (20, (8.593655, 1.477324, 1.436254, 1.182839, 7.113258, 0.196255, 10.460644, 0.041891, 81.390381, 169.847839, 0.688098)),
    "Ca2+": (20, (8.501441, 12.880483, 9.765095, 7.156669, 0.711160, -21.013187, 10.525848, -0.004033, 0.010692, 0.684443, 27.231771)),
    "Ti": (22, (9.818524, 1.522646, 1.703101, 1.768774, 7.082555, 0.102473, 8.001879, 0.029763, 39.885422, 120.157997, 0.532405)),
    "Fe": (26, (12.311098, 1.876623, 3.066177, 2.070451, 6.975185, -0.304931, 5.009415, 0.014461, 18.743040, 82.767876, 0.346506)),
    "Ni": (28, (13.521865, 6.947285, 3.866028, 2.135900, 4.284731, -2.762697, 4.077277, 0.286763, 14.622634, 71.966080, 0.004437)),
    "Cu": (29, (14.014192, 4.784577, 5.056806, 1.457971, 6.932996, -3.254477, 3.738280, 0.003744, 13.034982, 72.554794, 0.265666)),
    "Zn": (30, (14.741002, 6.907748, 4.642337, 2.191766, 38.424042, -36.915829, 3.388232, 0.243315, 11.903689, 63.312130, 0.000397)),
    "Ce": (58, (17.355122, 43.988499, 20.546650, 3.130670, 11.353665, -38.386017, 0.328369, 0.002047, 3.088196, 134.907654, 18.832960)),
    "Ce4+": (58, (17.457533, 25.659941, 11.691037, 19.695251, -16.994749, -3.515096, 0.311812, -0.003793, 16.568687, 2.886395, -0.008931)),
}

#: 標準原子量 [g/mol] (IUPAC の慣用値、4〜5 桁)。密度と重量分率の換算にだけ使う。
ATOMIC_MASS = {
    "C": 12.011, "O": 15.999, "F": 18.998, "Na": 22.990, "Mg": 24.305, "Al": 26.982, "Si": 28.085, "Cl": 35.45,
    "K": 39.098, "Ca": 40.078, "Ti": 47.867, "Fe": 55.845, "Ni": 58.693, "Cu": 63.546, "Zn": 65.38, "Ce": 140.116,
}

#: 立方晶の格子の名前(:func:`cubic_index`)。
LATTICES = ("P", "I", "F", "diamond")

#: 立方晶の原型の名前 → 単位格子内の分率座標(副格子ごと)。:func:`cubic_prototype` が使う。
PROTOTYPES = {
    "sc": ([(0, 0, 0)],),
    "bcc": ([(0, 0, 0), (0.5, 0.5, 0.5)],),
    "fcc": ([(0, 0, 0), (0, 0.5, 0.5), (0.5, 0, 0.5), (0.5, 0.5, 0)],),
    "diamond": ([(0, 0, 0), (0, 0.5, 0.5), (0.5, 0, 0.5), (0.5, 0.5, 0),
                 (0.25, 0.25, 0.25), (0.25, 0.75, 0.75), (0.75, 0.25, 0.75), (0.75, 0.75, 0.25)],),
    "rocksalt": ([(0, 0, 0), (0, 0.5, 0.5), (0.5, 0, 0.5), (0.5, 0.5, 0)],
                 [(0.5, 0.5, 0.5), (0.5, 0, 0), (0, 0.5, 0), (0, 0, 0.5)]),
    "cscl": ([(0, 0, 0)], [(0.5, 0.5, 0.5)]),
    "zincblende": ([(0, 0, 0), (0, 0.5, 0.5), (0.5, 0, 0.5), (0.5, 0.5, 0)],
                   [(0.25, 0.25, 0.25), (0.25, 0.75, 0.75), (0.75, 0.25, 0.75), (0.75, 0.75, 0.25)]),
    "fluorite": ([(0, 0, 0), (0, 0.5, 0.5), (0.5, 0, 0.5), (0.5, 0.5, 0)],
                 [(x, y, z) for x in (0.25, 0.75) for y in (0.25, 0.75) for z in (0.25, 0.75)]),
}

_AVOGADRO = 6.02214076e23
_FWHM_TO_SIGMA = 1.0 / (2.0 * math.sqrt(2.0 * math.log(2.0)))
_LORENTZ = ("powder", "none")


# ----------------------------------------------------------------------------------------------
# 引数の検査(fail-closed)
# ----------------------------------------------------------------------------------------------
def _num(v, name, positive=False, nonneg=False, allow_inf=False):
    if isinstance(v, bool):
        raise ValueError("%s must be a number, got %r" % (name, v))
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s must be a number, got %r" % (name, v)) from None
    if math.isnan(f) or (math.isinf(f) and not allow_inf):
        raise ValueError("%s must be finite, got %r" % (name, v))
    if positive and not f > 0:
        raise ValueError("%s must be > 0, got %r" % (name, v))
    if nonneg and f < 0:
        raise ValueError("%s must be >= 0, got %r" % (name, v))
    return f


def _choice(v, name, allowed):
    if not isinstance(v, str) or v not in allowed:
        raise ValueError("%s must be one of %r, got %r" % (name, tuple(allowed), v))
    return v


def _vec(a, name, min_len=1):
    try:
        x = np.asarray(a, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("%s must be a numeric 1-D array" % name) from None
    if x.ndim != 1 or x.size < min_len:
        raise ValueError("%s must be 1-D with at least %d values, got shape %r" % (name, min_len, np.shape(a)))
    if not np.all(np.isfinite(x)):
        raise ValueError("%s contains nan/inf" % name)
    return x


def _axis(two_theta, intensity, min_len=7):
    x = _vec(two_theta, "two_theta", min_len)
    y = _vec(intensity, "intensity", min_len)
    if x.size != y.size:
        raise ValueError("two_theta and intensity must have the same length (%d vs %d)" % (x.size, y.size))
    if np.any(np.diff(x) <= 0):
        raise ValueError("two_theta must be strictly increasing")
    if x[0] <= 0 or x[-1] >= 180:
        raise ValueError("two_theta must lie in (0, 180) degrees")
    return x, y


def _image(a, name="image"):
    try:
        im = np.asarray(a, dtype=np.float64)
    except (TypeError, ValueError):
        raise ValueError("%s must be a numeric 2-D array" % name) from None
    if im.ndim != 2 or min(im.shape) < 8:
        raise ValueError("%s must be 2-D and at least 8x8, got shape %r" % (name, np.shape(a)))
    return im


def _geometry(geom):
    if not isinstance(geom, dict):
        raise ValueError("geometry must be a dict with cx, cy, distance, pixel, wavelength (tilt, tilt_dir optional)")
    for k in ("cx", "cy", "distance", "pixel", "wavelength"):
        if k not in geom:
            raise ValueError("geometry is missing %r" % k)
    unknown = set(geom) - {"cx", "cy", "distance", "pixel", "wavelength", "tilt", "tilt_dir",
                           "rms_two_theta_deg", "n_points", "rings_deg", "ok", "n_rings"}
    if unknown:
        raise ValueError("geometry has unknown keys %r (spelling?)" % sorted(unknown))
    g = {"cx": _num(geom["cx"], "geometry['cx']"), "cy": _num(geom["cy"], "geometry['cy']"),
         "distance": _num(geom["distance"], "geometry['distance']", positive=True),
         "pixel": _num(geom["pixel"], "geometry['pixel']", positive=True),
         "wavelength": _num(geom["wavelength"], "geometry['wavelength']", positive=True),
         "tilt": _num(geom.get("tilt", 0.0), "geometry['tilt']"),
         "tilt_dir": _num(geom.get("tilt_dir", 0.0), "geometry['tilt_dir']")}
    if abs(g["tilt"]) >= 60:
        raise ValueError("geometry['tilt'] must be within (-60, 60) degrees, got %r" % g["tilt"])
    return g


def _two_theta_deg(d, wavelength):
    """Bragg の 2θ [deg] (``s > 1`` は nan)。角は atan2(acos / asin の端の丸めの床を避ける)。"""
    s = wavelength / (2.0 * np.asarray(d, dtype=np.float64))
    ok = s <= 1.0
    s = np.where(ok, s, np.nan)
    return np.degrees(2.0 * np.arctan2(s, np.sqrt(np.clip((1.0 - s) * (1.0 + s), 0.0, None))))


def _f0(symbol, s):
    if symbol not in FORM_FACTORS:
        raise ValueError("no scattering factor for %r (known: %s)" % (symbol, ", ".join(sorted(FORM_FACTORS))))
    c = FORM_FACTORS[symbol][1]
    s2 = np.asarray(s, dtype=np.float64) ** 2
    out = np.full(s2.shape, c[5])
    for i in range(5):
        out = out + c[i] * np.exp(-c[6 + i] * s2)
    return out


def _element(symbol):
    m = re.match(r"([A-Z][a-z]?)", symbol or "")
    if not m:
        raise ValueError("cannot read an element from %r" % symbol)
    return m.group(1)


def _scatterer(type_symbol, notes):
    """CIF の型記号(``Al3+``・``O2-``・``Na+``・``Si``)→ :data:`FORM_FACTORS` の名前。無いイオンは中性原子(notes に残す)。"""
    t = str(type_symbol).strip()
    el = _element(t)
    m = re.match(r"([A-Z][a-z]?)(\d*)([+-])$", t)
    if m:
        key = "%s%s%s" % (m.group(1), m.group(2) or "1", m.group(3))
        if key in FORM_FACTORS:
            return key
        notes.append("no ionic scattering factor for %s; used neutral %s" % (t, el))
    if el not in FORM_FACTORS:
        raise ValueError("no scattering factor for element %r (from %r)" % (el, type_symbol))
    return el


# ----------------------------------------------------------------------------------------------
# CIF の読み込み
# ----------------------------------------------------------------------------------------------
def _cif_tokens(text):
    toks = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith(";"):
            buf = [ln[1:]]
            i += 1
            while i < len(lines) and not lines[i].startswith(";"):
                buf.append(lines[i])
                i += 1
            toks.append(("str", "\n".join(buf).strip()))
            i += 1
            continue
        j = 0
        while j < len(ln):
            ch = ln[j]
            if ch.isspace():
                j += 1
            elif ch == "#":
                break
            elif ch in "'\"":
                k = j + 1
                while k < len(ln) and not (ln[k] == ch and (k + 1 == len(ln) or ln[k + 1].isspace())):
                    k += 1
                toks.append(("str", ln[j + 1:k]))
                j = k + 1
            else:
                k = j
                while k < len(ln) and not ln[k].isspace():
                    k += 1
                toks.append(("bare", ln[j:k]))
                j = k
        i += 1
    return toks


def _cif_parse(text):
    toks = _cif_tokens(text)
    items, loops = {}, []
    i, n = 0, len(toks)
    while i < n:
        kind, t = toks[i]
        tl = t.lower()
        if kind == "bare" and tl == "loop_":
            i += 1
            tags = []
            while i < n and toks[i][0] == "bare" and toks[i][1].startswith("_"):
                tags.append(toks[i][1].lower())
                i += 1
            vals = []
            while i < n and not (toks[i][0] == "bare" and (toks[i][1].startswith("_") or toks[i][1].lower() == "loop_"
                                                            or toks[i][1].lower().startswith("data_"))):
                vals.append(toks[i][1])
                i += 1
            if tags and len(vals) % len(tags) == 0:
                rows = [dict(zip(tags, vals[r:r + len(tags)])) for r in range(0, len(vals), len(tags))]
                loops.append((tags, rows))
            elif tags:
                raise ValueError("CIF loop with tags %r has %d values, not a multiple of %d" % (tags[:3], len(vals), len(tags)))
        elif kind == "bare" and t.startswith("_"):
            if i + 1 >= n:
                raise ValueError("CIF tag %r has no value" % t)
            items[tl] = toks[i + 1][1]
            i += 2
        else:
            i += 1
    return items, loops


def _cif_num(v, name, default=None):
    if v is None or v in (".", "?"):
        if default is None:
            raise ValueError("CIF value %s is missing" % name)
        return default
    m = re.match(r"^([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)(?:\(\d+\))?$", str(v).strip())
    if not m:
        raise ValueError("CIF value %s is not a number: %r" % (name, v))
    return float(m.group(1))


def _symop(s):
    """``'1/2+x,y-x,-z'`` → (3×3 の回転, 並進)。eval は使わない。"""
    parts = s.replace(" ", "").lower().split(",")
    if len(parts) != 3:
        raise ValueError("symmetry operation %r must have 3 components" % s)
    R = np.zeros((3, 3))
    t = np.zeros(3)
    for r, p in enumerate(parts):
        pos = 0
        if not p:
            raise ValueError("empty component in symmetry operation %r" % s)
        for m in re.finditer(r"([+-]?)(\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?)?\*?([xyz])?", p):
            if m.end() == m.start():
                continue
            if m.start() != pos:
                raise ValueError("cannot read symmetry operation %r" % s)
            pos = m.end()
            sign = -1.0 if m.group(1) == "-" else 1.0
            num = m.group(2)
            if num:
                a, _, b = num.partition("/")
                val = float(a) / (float(b) if b else 1.0)
            else:
                val = 1.0
            if m.group(3):
                R[r, "xyz".index(m.group(3))] += sign * val
            elif num:
                t[r] += sign * val
            else:
                raise ValueError("cannot read symmetry operation %r" % s)
        if pos != len(p):
            raise ValueError("cannot read symmetry operation %r" % s)
    return R, t


def _expand_sites(sites, ops, tol=1e-4):
    atoms = []
    for st in sites:
        found = []
        for R, t in ops:
            x = (R @ st["xyz"] + t) % 1.0
            x[np.isclose(x, 1.0, atol=tol)] = 0.0
            if any(np.all(np.abs(((x - y) + 0.5) % 1.0 - 0.5) < tol) for y in found):
                continue
            found.append(x)
        for x in found:
            atoms.append({"label": st["label"], "type": st["type"], "xyz": x, "occ": st["occ"], "B": st["B"]})
    return atoms


def _phase_density(cell_volume, atoms):
    mass = 0.0
    for a in atoms:
        el = _element(a["type"])
        if el not in ATOMIC_MASS:
            raise ValueError("no atomic mass for %r" % el)
        mass += a["occ"] * ATOMIC_MASS[el]
    return mass, mass / (_AVOGADRO * cell_volume * 1e-24)


def _cell_metric(cell):
    a, b, c, al, be, ga = cell
    ca, cb, cg = (math.cos(math.radians(v)) for v in (al, be, ga))
    G = np.array([[a * a, a * b * cg, a * c * cb], [a * b * cg, b * b, b * c * ca], [a * c * cb, b * c * ca, c * c]])
    vol2 = float(np.linalg.det(G))
    if not vol2 > 0:
        raise ValueError("cell %r has no positive volume" % (cell,))
    return G, math.sqrt(vol2)


def _make_phase(name, cell, atoms, notes, source):
    for k, v in zip(("a", "b", "c", "alpha", "beta", "gamma"), cell):
        _num(v, "cell %s" % k, positive=True)
    G, vol = _cell_metric(cell)
    mass, rho = _phase_density(vol, atoms)
    return {"name": name, "cell": tuple(float(v) for v in cell), "volume": vol, "atoms": atoms,
            "cell_mass": mass, "density": rho, "notes": list(notes), "source": source}


def cif_read(cif, name=None, default_b=0.5):
    """CIF(結晶構造の標準書式)を読んで、単位格子の中の全原子に展開した「相」を返す。

    ``cif`` はファイルのパスか CIF の本文(文字列。``data_`` か ``_cell_length_a`` を含むなら本文とみなす)。
    読むもの: ``_cell_length_a/b/c``・``_cell_angle_alpha/beta/gamma``、対称操作のループ
    (``_space_group_symop_operation_xyz`` か ``_symmetry_equiv_pos_as_xyz``、無ければ恒等だけ)、原子のループ
    (``_atom_site_fract_x/y/z``、``_atom_site_type_symbol``(無ければラベルの先頭の元素記号)、``_atom_site_occupancy``
    (既定 1)、``_atom_site_U_iso_or_equiv`` か ``_atom_site_B_iso_or_equiv``(無ければ ``default_b`` [Å²]))。
    数値の不確かさの括弧(``4.76050(5)``)は落とす。対称操作は自前の小さな構文解析で読み、``eval`` しない。

    返り値(dict、相): ``name``・``cell``(a, b, c [Å], α, β, γ [deg])・``volume`` [Å³]・``atoms``(展開後の原子の
    list: ``type``・``xyz``・``occ``・``B``)・``cell_mass`` [g/mol]・``density`` [g/cm³]・``notes``(中性原子で代用した
    イオンなど)・``source``(DOI と COD 番号があれば)。:func:`powder_reflections` と :func:`phase_dictionary` の入力。

    Raises ValueError: 格子定数が無い・数値でない、対称操作が読めない、原子が無い、散乱因子の無い元素。
    """
    if not isinstance(cif, str) or not cif:
        raise ValueError("cif must be a path or CIF text (str)")
    if "data_" in cif or "_cell_length_a" in cif:
        text = cif
    else:
        try:
            with open(cif, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError as exc:
            raise ValueError("cannot read CIF %r: %s" % (cif, exc)) from None
    _num(default_b, "default_b", nonneg=True)
    items, loops = _cif_parse(text)
    cell = tuple(_cif_num(items.get(k), k) for k in ("_cell_length_a", "_cell_length_b", "_cell_length_c",
                                                     "_cell_angle_alpha", "_cell_angle_beta", "_cell_angle_gamma"))
    ops = None
    sites = None
    notes = []
    for tags, rows in loops:
        for tg in ("_space_group_symop_operation_xyz", "_symmetry_equiv_pos_as_xyz"):
            if tg in tags and ops is None:
                ops = [_symop(r[tg]) for r in rows]
        if "_atom_site_fract_x" in tags and sites is None:
            sites = []
            for r in rows:
                label = r.get("_atom_site_label", "X")
                typ = r.get("_atom_site_type_symbol", label)
                occ = _cif_num(r.get("_atom_site_occupancy"), "occupancy", default=1.0)
                if r.get("_atom_site_u_iso_or_equiv") not in (None, ".", "?"):
                    B = 8 * math.pi ** 2 * _cif_num(r["_atom_site_u_iso_or_equiv"], "U_iso")
                elif r.get("_atom_site_b_iso_or_equiv") not in (None, ".", "?"):
                    B = _cif_num(r["_atom_site_b_iso_or_equiv"], "B_iso")
                else:
                    B = float(default_b)
                    notes.append("site %s has no displacement parameter; B = %g A^2 assumed" % (label, B))
                xyz = np.array([_cif_num(r.get("_atom_site_fract_" + c), "fract_" + c) for c in "xyz"])
                sites.append({"label": label, "type": _scatterer(typ, notes), "xyz": xyz, "occ": occ, "B": B})
    if not sites:
        raise ValueError("CIF has no _atom_site_fract_x loop (no atoms)")
    if ops is None:
        ops = [(np.eye(3), np.zeros(3))]
        notes.append("no symmetry operations in the CIF; the listed sites are taken as the whole cell (P1)")
    atoms = _expand_sites(sites, ops)
    src = {k: items[k] for k in ("_journal_paper_doi", "_cod_database_code") if k in items}
    nm = name or items.get("_chemical_name_mineral") or items.get("_chemical_formula_sum") or "phase"
    return _make_phase(str(nm), cell, atoms, notes, src)


def cubic_prototype(kind, a, species, b_iso=0.5, name=None):
    """立方晶の原型(``sc``・``bcc``・``fcc``・``diamond``・``rocksalt``・``cscl``・``zincblende``・``fluorite``)から相を作る。

    CIF が無いときの相の作り方(教科書の座標だけ)。``species`` は副格子ごとの散乱体の名前の list(rocksalt は
    ``["Na", "Cl"]``、fluorite は ``["Ca", "F"]`` の順 = 陽イオン、陰イオン)。``a`` [Å]、``b_iso`` [Å²] は全原子共通。
    返り値は :func:`cif_read` と同じ形の相。

    Raises ValueError: 原型の名前の綴り違い、副格子の数と ``species`` の数の不一致、未知の元素、``a <= 0``。
    """
    _choice(kind, "kind", tuple(PROTOTYPES))
    a = _num(a, "a", positive=True)
    b = _num(b_iso, "b_iso", nonneg=True)
    if isinstance(species, str):
        species = [species]
    subl = PROTOTYPES[kind]
    if not isinstance(species, (list, tuple)) or len(species) != len(subl):
        raise ValueError("prototype %r needs %d species, got %r" % (kind, len(subl), species))
    notes = []
    atoms = []
    for sp, pos in zip(species, subl):
        key = _scatterer(sp, notes)
        for p in pos:
            atoms.append({"label": key, "type": key, "xyz": np.array(p, dtype=float), "occ": 1.0, "B": b})
    return _make_phase(name or "%s %s" % ("-".join(species), kind), (a, a, a, 90.0, 90.0, 90.0), atoms, notes,
                       {"prototype": kind})


def _check_phase(phase, name="phase"):
    if not isinstance(phase, dict) or "cell" not in phase or "atoms" not in phase:
        raise ValueError("%s must be a phase dict from cif_read or cubic_prototype" % name)
    if not phase["atoms"]:
        raise ValueError("%s has no atoms" % name)
    return phase


# ----------------------------------------------------------------------------------------------
# 反射の一覧(Bragg・構造因子・Lorentz 因子)
# ----------------------------------------------------------------------------------------------
def _lorentz(two_theta_deg, kind):
    th = np.radians(np.asarray(two_theta_deg) / 2.0)
    if kind == "powder":
        return 1.0 / (np.sin(th) ** 2 * np.cos(th))
    return np.ones_like(th)


def powder_reflections(phase, wavelength, two_theta_max=90.0, lorentz="powder", lattice_scale=1.0,
                       include_extinct=False, rel_cutoff=1e-10):
    """相の粉末反射の一覧: 面間隔 d、Bragg の 2θ、多重度、|F|²、強度(Lorentz 因子つき、偏光なし)。

    全ての (h, k, l) を ``2θ <= two_theta_max`` まで列挙し、構造因子
    ``F = Σ occ f₀(s) exp(−B s²) exp(2πi h·x)`` を計算して、**同じ d・同じ |F|² の反射を 1 本にまとめる**(多重度 m)。
    粉末では同じ d の反射は区別できないので、d が同じで |F|² の違う族(立方晶の 333 と 511 など)は別の行のまま同じ 2θ に並ぶ。
    ``lattice_scale`` は格子定数を全部その倍率にする(熱膨張・固溶の模擬。:func:`phase_fractions` の格子の追い込みが使う)。
    ``include_extinct=True`` で |F|² が最大の ``rel_cutoff`` 倍未満の(消滅した)反射も残す(``extinct=True`` の印つき)。
    強度 = ``m |F|² L(2θ)``(``lorentz``: ``"powder"`` = ``1/(sin² θ cos θ)``、``"none"``)。偏光は
    :func:`azimuthal_integrate` が割り戻す前提で入れない。

    返り値(dict): ``hkl``(代表、(n, 3) int)・``d`` [Å]・``two_theta`` [deg]・``multiplicity``・``F2``・``intensity``・
    ``extinct``(bool)、2θ の昇順。``name``・``volume``・``density`` も写す。

    Raises ValueError: 相の形でない、波長が非正、``two_theta_max`` が (0, 180) の外、Lorentz の綴り違い。
    """
    ph = _check_phase(phase)
    lam = _num(wavelength, "wavelength", positive=True)
    tmax = _num(two_theta_max, "two_theta_max", positive=True)
    if tmax >= 180:
        raise ValueError("two_theta_max must be < 180 degrees, got %r" % two_theta_max)
    _choice(lorentz, "lorentz", _LORENTZ)
    sc = _num(lattice_scale, "lattice_scale", positive=True)
    _num(rel_cutoff, "rel_cutoff", nonneg=True)
    a, b, c, al, be, ga = ph["cell"]
    cell = (a * sc, b * sc, c * sc, al, be, ga)
    G, vol = _cell_metric(cell)
    Gs = np.linalg.inv(G)
    q_max = (2.0 * math.sin(math.radians(tmax / 2.0)) / lam) ** 2       # 1/d² の上限
    # 各軸の最大指数: h = d*·a なので |h| <= |d*| |a| = sqrt(q_max) sqrt(G[0,0])(k, l も同じ)
    hmax = [int(math.floor(math.sqrt(q_max * G[i, i]))) + 1 for i in range(3)]
    rng = [np.arange(-m, m + 1) for m in hmax]
    H = np.stack(np.meshgrid(*rng, indexing="ij"), -1).reshape(-1, 3)
    H = H[np.any(H != 0, axis=1)]
    q = np.einsum("ni,ij,nj->n", H, Gs, H)
    keep = q <= q_max * (1 + 1e-12)
    H, q = H[keep], q[keep]
    if H.size == 0:
        raise ValueError("no reflection below two_theta_max=%g at wavelength %g" % (tmax, lam))
    d = 1.0 / np.sqrt(q)
    s = 0.5 / d
    X = np.array([at["xyz"] for at in ph["atoms"]])
    occ = np.array([at["occ"] for at in ph["atoms"]])
    Bs = np.array([at["B"] for at in ph["atoms"]])
    types = [at["type"] for at in ph["atoms"]]
    fcache = {t: _f0(t, s) for t in set(types)}
    fj = np.stack([fcache[t] for t in types], 1) * occ[None, :] * np.exp(-np.outer(s ** 2, Bs))
    phase_arg = 2 * np.pi * (H @ X.T)
    F = np.sum(fj * np.exp(1j * phase_arg), axis=1)
    F2 = np.abs(F) ** 2
    # 同じ d・同じ |F|² をまとめる
    kd = np.round(d, 9)
    kf = np.round(F2 / max(F2.max(), 1e-300), 9)
    order = np.lexsort((kf, -kd))
    groups = {}
    for i in order:
        key = (kd[i], kf[i])
        groups.setdefault(key, []).append(i)
    rows = []
    fmax = F2.max()
    for key, idx in groups.items():
        hk = H[idx]
        # 代表は族の中の実在の指数から: 非負の成分が最も多く、その中で辞書順最大のもの(立方晶なら 220・311、
        # 六方晶の設定でも 012 のように族に実在する指数を返す —— 絶対値を並べ替えると六方晶では族に無い指数になる)
        rep = max((tuple(int(v) for v in r) for r in hk), key=lambda r: (sum(v >= 0 for v in r), r))
        f2 = float(F2[idx[0]])
        ext = f2 < rel_cutoff * fmax
        if ext and not include_extinct:
            continue
        rows.append((float(d[idx[0]]), rep, len(idx), f2, ext))
    rows.sort(key=lambda r: -r[0])
    dd = np.array([r[0] for r in rows])
    tt = _two_theta_deg(dd, lam)
    mult = np.array([r[2] for r in rows])
    f2a = np.array([r[3] for r in rows])
    return {"name": ph["name"], "hkl": np.array([r[1] for r in rows], dtype=int).reshape(-1, 3), "d": dd,
            "two_theta": tt, "multiplicity": mult, "F2": f2a, "intensity": mult * f2a * _lorentz(tt, lorentz),
            "extinct": np.array([r[4] for r in rows], dtype=bool), "volume": vol, "density": ph["density"],
            "wavelength": lam, "lorentz": lorentz}


def scherrer_size(fwhm, two_theta, wavelength, K=0.9, instrumental_fwhm=0.0, combine="gauss"):
    """Scherrer の式で結晶子径 [Å] (``L = K λ / (β cos θ)``)。

    ``fwhm``・``instrumental_fwhm`` は 2θ の半値全幅 [deg]、``two_theta`` [deg]、``wavelength`` [Å]。試料による広がり β は
    ``combine="gauss"`` で ``sqrt(fwhm² − inst²)``、``"lorentz"`` で ``fwhm − inst``。配列を渡せば配列で返す。
    Scherrer の式は **体積で重みを付けた柱の長さ** の目安で、ひずみの広がり(tan θ に比例)は区別しない —— ひずみが
    疑わしいときは複数の山で Williamson–Hall のように tan θ への依存を見ること。

    Raises ValueError: ``fwhm <= instrumental_fwhm``(装置より細い山 = 径が決まらない)、非正の値、綴り違い。
    """
    _choice(combine, "combine", ("gauss", "lorentz"))
    lam = _num(wavelength, "wavelength", positive=True)
    K = _num(K, "K", positive=True)
    w = np.atleast_1d(np.asarray(fwhm, dtype=np.float64))
    t = np.atleast_1d(np.asarray(two_theta, dtype=np.float64))
    inst = np.atleast_1d(np.asarray(instrumental_fwhm, dtype=np.float64))
    for arr, nm in ((w, "fwhm"), (t, "two_theta"), (inst, "instrumental_fwhm")):
        if not np.all(np.isfinite(arr)):
            raise ValueError("%s contains nan/inf" % nm)
    if np.any(w <= 0) or np.any(t <= 0) or np.any(t >= 180) or np.any(inst < 0):
        raise ValueError("fwhm must be > 0, two_theta in (0, 180), instrumental_fwhm >= 0")
    if np.any(w <= inst):
        raise ValueError("fwhm %r is not wider than the instrumental width %r — the size is not resolved" % (w, inst))
    beta = np.sqrt(w ** 2 - inst ** 2) if combine == "gauss" else w - inst
    L = K * lam / (np.radians(beta) * np.cos(np.radians(t / 2.0)))
    return float(L[0]) if np.ndim(fwhm) == 0 and np.ndim(two_theta) == 0 else L


# ----------------------------------------------------------------------------------------------
# 1-D の模型(山の形と参照パターン)
# ----------------------------------------------------------------------------------------------
def _inst_spec(inst, name="instrumental_fwhm"):
    """装置の FWHM の指定: 数 [deg] か ``(2θ の列, FWHM の列)`` の表(Si 標準で測った値など。間は線形補間、外は端の値)。"""
    if isinstance(inst, (tuple, list)) and len(inst) == 2 and np.ndim(inst[0]) == 1:
        tt = _vec(inst[0], name + "[0]", 2)
        ww = _vec(inst[1], name + "[1]", 2)
        if tt.size != ww.size or np.any(np.diff(tt) <= 0) or np.any(ww < 0):
            raise ValueError("%s table must be (increasing two_theta, fwhm >= 0) of equal length" % name)
        return (tt, ww)
    return _num(inst, name, nonneg=True)


def _inst_at(inst, t):
    if isinstance(inst, tuple):
        return np.interp(t, inst[0], inst[1])
    return np.full(np.shape(t), float(inst))


def _fwhm_deg(two_theta, wavelength, size, K, inst):
    """Scherrer の広がり(size = 径 [Å]、inf なら 0)と装置の広がりをガウスで足した FWHM [deg]。"""
    t = np.asarray(two_theta, dtype=np.float64)
    inst = _inst_at(inst, t)
    if math.isinf(size):
        b = np.zeros_like(t)
    else:
        b = np.degrees(K * wavelength / (size * np.cos(np.radians(t / 2.0))))
    return np.sqrt(b ** 2 + inst ** 2)


def _render(lines_tt, lines_I, grid, fwhm, eta=0.0):
    """線の列(位置・強度・幅)を格子に描く(面積 = 強度の pseudo-Voigt)。"""
    out = np.zeros_like(grid)
    if lines_tt.size == 0:
        return out
    fw = np.broadcast_to(np.asarray(fwhm, dtype=np.float64), lines_tt.shape)
    for t0, A, w in zip(lines_tt, lines_I, fw):
        if not (w > 0) or not np.isfinite(t0):
            continue
        half = 8.0 * w if eta == 0 else 40.0 * w
        lo, hi = np.searchsorted(grid, [t0 - half, t0 + half])
        if hi <= lo:
            continue
        x = grid[lo:hi] - t0
        sg = w * _FWHM_TO_SIGMA
        g = np.exp(-0.5 * (x / sg) ** 2) / (sg * math.sqrt(2 * math.pi))
        if eta:
            gam = w / 2.0
            lz = gam / (math.pi * (x * x + gam * gam))
            g = (1 - eta) * g + eta * lz
        out[lo:hi] += A * g
    return out


def _phase_profile(phase, grid, wavelength, size, K, inst, lorentz, lattice_scale=1.0, eta=0.0):
    """相の 1-D の強度(体積分率 1 あたり、単位立体角あたり): ``(1/V²) Σ m|F|² L × 形``。"""
    tmax = min(179.0, float(grid[-1]) + 2.0)
    ref = powder_reflections(phase, wavelength, two_theta_max=tmax, lorentz=lorentz, lattice_scale=lattice_scale)
    fw = _fwhm_deg(ref["two_theta"], wavelength, size, K, inst)
    return _render(ref["two_theta"], ref["intensity"] / ref["volume"] ** 2, grid, fw, eta), ref


# ----------------------------------------------------------------------------------------------
# 検出器の幾何
# ----------------------------------------------------------------------------------------------
def _rotation(tilt_deg, tilt_dir_deg):
    tau = math.radians(tilt_deg)
    phi = math.radians(tilt_dir_deg)
    k = np.array([math.cos(phi), math.sin(phi), 0.0])
    Kx = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(tau) * Kx + (1 - math.cos(tau)) * (Kx @ Kx)


def _pixel_vectors(rows, cols, g):
    R = _rotation(g["tilt"], g["tilt_dir"])
    eu, ev, n = R[:, 0], R[:, 1], R[:, 2]
    u = (np.asarray(cols, dtype=np.float64) - g["cx"]) * g["pixel"]
    v = (np.asarray(rows, dtype=np.float64) - g["cy"]) * g["pixel"]
    P = (u[..., None] * eu + v[..., None] * ev)
    P[..., 2] += g["distance"]
    return P, n


def _tth_chi(rows, cols, g):
    P, n = _pixel_vectors(rows, cols, g)
    tth = np.degrees(np.arctan2(np.hypot(P[..., 0], P[..., 1]), P[..., 2]))
    chi = np.degrees(np.arctan2(P[..., 1], P[..., 0]))
    r = np.linalg.norm(P, axis=-1)
    omega = (P @ n) / r ** 3 * g["distance"] ** 2          # 立体角(ビームの中心で傾き 0 なら 1)
    return tth, chi, omega


def _polarization(tth_deg, chi_deg, p):
    t2 = np.radians(tth_deg)
    return 0.5 * (1 + np.cos(t2) ** 2) - 0.5 * p * np.cos(2 * np.radians(chi_deg)) * np.sin(t2) ** 2


def detector_two_theta(shape, geometry):
    """検出器の各画素の 2θ・方位 χ・相対立体角(傾き・距離・中心つき)。

    ``shape = (H, W)``、``geometry`` は module の docstring の Fit2D 型。返り値(dict): ``two_theta`` [deg]・``chi`` [deg]
    (``atan2``、+列が 0、+行が +90)・``solid_angle``(ビームの中心で傾き 0 のとき 1 になる相対値、``cos³`` で落ちる)。
    2θ は ``atan2(hypot(Pₓ, P_y), P_z)`` で求める(acos を使うと 2θ → 0 の近くで丸めの床が出る)。

    Raises ValueError: 形が 2 要素の正の整数でない、幾何の鍵の欠け・綴り違い、``|tilt| >= 60``。
    """
    if not isinstance(shape, (tuple, list)) or len(shape) != 2:
        raise ValueError("shape must be (H, W), got %r" % (shape,))
    H, W = (int(_num(s, "shape", positive=True)) for s in shape)
    g = _geometry(geometry)
    rr, cc = np.mgrid[0:H, 0:W]
    tth, chi, om = _tth_chi(rr, cc, g)
    return {"two_theta": tth, "chi": chi, "solid_angle": om}


def debye_ring_image(phases, weight_fractions, geometry, shape=(512, 512), size=math.inf, K=0.9,
                     instrumental_fwhm=0.02, counts=2.0e4, background=0.03, polarization=0.0, lorentz="powder",
                     supersample=2, lattice_scales=None, seed=0, step=0.002, eta=0.0):
    """デバイ環の 2-D 検出器像を合成する(相ごとの寄与つき)。

    相 p の単位立体角あたりの強度 ``∝ vₚ (1/Vₚ²) Σ m|F|² L(2θ) × 形``(体積分率 ``vₚ ∝ Wₚ / ρₚ``)、山の幅は Scherrer
    (``size`` [Å]、相ごとの list も可、inf = 広がりなし)と装置の FWHM(``instrumental_fwhm`` [deg])をガウスで足す。
    画素の値 = 強度 × 偏光 ``P(2θ, χ)`` × 相対立体角 + 平らな背景(``background`` × 最大の強度、これも立体角つき)。
    画素は ``supersample``² 点の平均(画素の幅の広がりが自然に入る)。``counts`` が数なら最大を ``counts`` に揃えて
    Poisson の雑音(``seed``)、``None`` なら雑音なし。``lattice_scales`` は相ごとの格子の倍率(熱膨張・固溶の模擬)。
    ``eta`` は山の形の Lorentz の割合(pseudo-Voigt、0 = ガウス)—— 辞書と違う形で合成して、形の取り違えの効きを測るため。

    返り値(dict): ``image``((H, W) float、数え数)・``per_phase``((P, H, W)、雑音なしの相ごとの寄与)・``background``
    ((H, W))・``names``・``weight_fractions``・``volume_fractions``・``two_theta``(画素の中心の 2θ)・``geometry``。

    Raises ValueError: 相と分率の数の不一致、負の分率・総和 0、幾何の不備、像が小さすぎる。
    """
    if isinstance(phases, dict):
        phases = [phases]
    if not isinstance(phases, (list, tuple)) or not phases:
        raise ValueError("phases must be a non-empty list of phase dicts")
    for i, p in enumerate(phases):
        _check_phase(p, "phases[%d]" % i)
    w = _vec(weight_fractions, "weight_fractions")
    if w.size != len(phases):
        raise ValueError("weight_fractions has %d values for %d phases" % (w.size, len(phases)))
    if np.any(w < 0) or w.sum() <= 0:
        raise ValueError("weight_fractions must be >= 0 with a positive sum")
    w = w / w.sum()
    g = _geometry(geometry)
    if not isinstance(shape, (tuple, list)) or len(shape) != 2:
        raise ValueError("shape must be (H, W)")
    H, W = (int(_num(s, "shape", positive=True)) for s in shape)
    if min(H, W) < 8:
        raise ValueError("shape must be at least 8x8")
    ss = int(_num(supersample, "supersample", positive=True))
    _choice(lorentz, "lorentz", _LORENTZ)
    pol = _num(polarization, "polarization")
    if not 0 <= pol <= 1:
        raise ValueError("polarization must be in [0, 1]")
    inst = _inst_spec(instrumental_fwhm)
    sizes = list(size) if isinstance(size, (list, tuple, np.ndarray)) else [size] * len(phases)
    if len(sizes) != len(phases):
        raise ValueError("size has %d values for %d phases" % (len(sizes), len(phases)))
    sizes = [_num(s_, "size", positive=True, allow_inf=True) for s_ in sizes]
    scales = [1.0] * len(phases) if lattice_scales is None else [_num(s_, "lattice_scales", positive=True) for s_ in lattice_scales]
    if len(scales) != len(phases):
        raise ValueError("lattice_scales has %d values for %d phases" % (len(scales), len(phases)))
    rho = np.array([p["density"] for p in phases])
    v = (w / rho) / np.sum(w / rho)
    # 画素の中の副標本点の 2θ
    off = (np.arange(ss) + 0.5) / ss - 0.5
    rr, cc = np.mgrid[0:H, 0:W].astype(np.float64)
    sub = []
    for dy in off:
        for dx in off:
            sub.append(_tth_chi(rr + dy, cc + dx, g))
    tmin = min(float(s_[0].min()) for s_ in sub)
    tmax = max(float(s_[0].max()) for s_ in sub)
    grid = np.arange(max(tmin - 1.0, 0.01), min(tmax + 1.0, 179.0), _num(step, "step", positive=True))
    per = np.zeros((len(phases), H, W))
    bgim = np.zeros((H, W))
    profiles = []
    for i, p in enumerate(phases):
        prof, _ref = _phase_profile(p, grid, g["wavelength"], sizes[i], _num(K, "K", positive=True), inst,
                                    lorentz, scales[i], _num(eta, "eta", nonneg=True))
        profiles.append(v[i] * prof)
    for tth, chi, om in sub:
        P = _polarization(tth, chi, pol) * om
        for i in range(len(phases)):
            per[i] += np.interp(tth, grid, profiles[i]) * P / ss ** 2
        bgim += om / ss ** 2
    peak = float(per.sum(0).max())
    if not peak > 0:
        raise ValueError("no diffraction ring falls on the detector (check distance, pixel and wavelength)")
    bg_level = _num(background, "background", nonneg=True) * peak
    clean = per.sum(0) + bg_level * bgim
    if counts is None:
        img = clean.copy()
        scale = 1.0
    else:
        scale = _num(counts, "counts", positive=True) / float(clean.max())
        img = np.random.default_rng(int(seed)).poisson(clean * scale).astype(np.float64)
    tc, _chi, _om = _tth_chi(rr, cc, g)
    return {"image": img, "per_phase": per * scale, "background": bg_level * bgim * scale,
            "names": [p["name"] for p in phases], "weight_fractions": w, "volume_fractions": v,
            "two_theta": tc, "geometry": dict(g)}


# ----------------------------------------------------------------------------------------------
# 方位積分
# ----------------------------------------------------------------------------------------------
def azimuthal_integrate(image, geometry, n_bins=None, two_theta_range=None, mask=None, solid_angle=True,
                        polarization=None, chi_range=None, supersample=2):
    """2-D の検出器像を 2θ の 1-D プロファイルに落とす(方位積分、マスクと補正つき)。

    各画素を ``supersample``² 個の副画素に分け(値は等分)、副画素の中心の 2θ でビンに振り分けて、ビンごとに **平均**
    する(画素の分け方の粗さによる縞を減らす)。``solid_angle=True`` で相対立体角を、``polarization`` が数(0 = 無偏光、
    1 = 水平偏光)なら偏光因子を、平均の前に割り戻す。``mask`` は True の画素を **除く**(同じ形の bool)。``chi_range``
    = (χ₀, χ₁) [deg] で扇形だけを積分(χ は ``atan2`` の (−180, 180])。非有限の画素は mask に入っていなければ拒否する。

    ``n_bins`` の既定は画素 1 個の角の半分の幅になる数(``0.5·pixel/distance`` [rad])。
    返り値(dict): ``two_theta``(ビンの中心 [deg])・``intensity``(平均)・``count``(副画素の重みの和、0 のビンは
    ``intensity`` が nan —— 埋めない)・``sigma``(Poisson を仮定した平均の標準誤差)。

    Raises ValueError: 2-D でない、mask の形の不一致、非有限の画素、範囲が空、扇形が空、ビン数 < 8。
    """
    im = _image(image)
    g = _geometry(geometry)
    nb = None if n_bins is None else int(_num(n_bins, "n_bins", positive=True))
    if nb is not None and nb < 8:
        raise ValueError("n_bins must be >= 8")
    ss = int(_num(supersample, "supersample", positive=True))
    if mask is not None:
        m = np.asarray(mask)
        if m.shape != im.shape or m.dtype != bool:
            raise ValueError("mask must be a bool array of the image shape %r" % (im.shape,))
        valid = ~m
    else:
        valid = np.ones(im.shape, dtype=bool)
    if not np.all(np.isfinite(im[valid])):
        raise ValueError("image has nan/inf outside the mask (mask them or fix the image)")
    pol = None if polarization is None else _num(polarization, "polarization")
    H, W = im.shape
    rr, cc = np.mgrid[0:H, 0:W].astype(np.float64)
    off = (np.arange(ss) + 0.5) / ss - 0.5
    vals, tths, wts, cors = [], [], [], []
    for dy in off:
        for dx in off:
            tth, chi, om = _tth_chi(rr + dy, cc + dx, g)
            corr = np.ones_like(tth)
            if solid_angle:
                corr = corr * om
            if pol is not None:
                corr = corr * _polarization(tth, chi, pol)
            sel = valid.copy()
            if chi_range is not None:
                c0, c1 = (_num(c, "chi_range") for c in chi_range)
                sel &= (chi >= c0) & (chi < c1) if c0 < c1 else (chi >= c0) | (chi < c1)
            vals.append((im / corr)[sel])
            cors.append(corr[sel])
            tths.append(tth[sel])
            wts.append(np.full(int(sel.sum()), 1.0 / ss ** 2))
    val = np.concatenate(vals)
    tt = np.concatenate(tths)
    wt = np.concatenate(wts)
    cr = np.concatenate(cors)
    if tt.size == 0:
        raise ValueError("no pixel left to integrate (mask / chi_range removed everything)")
    if two_theta_range is None:
        lo, hi = float(tt.min()), float(tt.max())
    else:
        lo, hi = (_num(v_, "two_theta_range") for v_ in two_theta_range)
    if not hi > lo:
        raise ValueError("two_theta_range is empty: %r" % ((lo, hi),))
    if nb is None:
        # 既定: ビンの幅 = 画素 1 個がビームの中心で張る角の半分(細かすぎると隣のビンが同じ画素を分け合い相関する)
        nb = max(8, int(math.ceil((hi - lo) / (0.5 * math.degrees(g["pixel"] / g["distance"])))))
    edges = np.linspace(lo, hi, nb + 1)
    idx = np.searchsorted(edges, tt, side="right") - 1
    ok = (idx >= 0) & (idx < nb)
    s_w = np.bincount(idx[ok], weights=wt[ok], minlength=nb)
    s_v = np.bincount(idx[ok], weights=(val * wt)[ok], minlength=nb)
    # ★2026-10-07: 補正で割った値 v = I / c の分散は I / c² = |v| / c(補正を σ に通さないと 2θ=55° で σ を 2.3 倍小さく見積もった)
    s_va = np.bincount(idx[ok], weights=(np.abs(val) / cr * wt)[ok], minlength=nb)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = s_v / s_w
        # Poisson: 画素の分散 ≈ 値。1 画素の副画素の重みの和は 1 なので、平均の分散 ≈ Σ w |v| / (Σ w)²
        # (副画素は同じ画素の写しで独立ではない —— 副画素を独立に数えると σ を ss 倍小さく見積もる)
        sig = np.sqrt(s_va) / s_w
    mean[s_w == 0] = np.nan
    sig[s_w == 0] = np.nan
    return {"two_theta": 0.5 * (edges[1:] + edges[:-1]), "intensity": mean, "count": s_w, "sigma": sig}


# ----------------------------------------------------------------------------------------------
# 山の検出と立方晶の指数付け
# ----------------------------------------------------------------------------------------------
def _rolling(a, w, fn):
    from scipy.ndimage import minimum_filter1d, uniform_filter1d
    if fn == "min":
        return minimum_filter1d(a, w, mode="nearest")
    return uniform_filter1d(a, w, mode="nearest")


def _baseline(y, w):
    """転がり最小 → 転がり平均の背景を、雑音の真ん中まで持ち上げる。

    転がり最小は雑音の下の端をなぞるので、そのままだと背景が雑音の数 σ 下に沈み、背景を引いた値の雑音が全部正に
    寄って偽の山が門を越える(2026-10-05 に実測: 背景の雑音 0.8 に対し 4〜5 沈んでいた)。山はプロファイルの
    少数派なので、``y − b`` の中央値だけ持ち上げる。
    """
    b = _rolling(y, w, "min")
    b = _rolling(b, w, "mean")
    return b + float(np.median(y - b))


def diffraction_peaks(two_theta, intensity, min_snr=6.0, baseline_window=None, max_peaks=200, noise=None):
    """1-D の回折プロファイルから山を拾い、ガウス + 直線の局所の当てはめで位置・高さ・FWHM・面積を出す。

    手順: 窓 ``baseline_window`` [deg] (既定 = 範囲の 4 %)の転がり最小 → 転がり平均で背景を作り、背景を引いた値の
    局所の最大のうち ``min_snr`` × 雑音を超えるものを候補にする(雑音は間隔 1〜8 の差分の MAD の最大から。``noise`` に
    数か、:func:`azimuthal_integrate` の ``sigma`` のようなビンごとの配列を渡してもよい —— 中心の近くや隅のように画素の
    少ないビンの揺れを山と取り違えないためには配列が要る)。各候補の半値幅を目で測る代わりに半値の交点で見積もり、隣の候補との中点で切った窓でガウス + 直線を
    ``scipy.optimize.least_squares`` で当てる。重なった山は窓が切られるぶん偏る(分けたいなら :func:`phase_fractions`)。

    返り値(dict): ``two_theta``・``height``・``fwhm`` [deg]・``area``・``snr``・``fit_ok``(当てはめが収束し窓の中に
    収まったか)、``noise``、``baseline``(格子と同じ長さ)。山が無ければ長さ 0 の配列(空 = 失敗ではない)。

    Raises ValueError: 長さの不一致・非有限・2θ が増えない、``min_snr <= 0``。
    """
    x, y = _axis(two_theta, intensity)
    snr = _num(min_snr, "min_snr", positive=True)
    bw = 0.04 * (x[-1] - x[0]) if baseline_window is None else _num(baseline_window, "baseline_window", positive=True)
    if noise is not None:
        if np.ndim(noise) == 0:
            noise = _num(noise, "noise", positive=True)
        else:
            noise = _vec(noise, "noise", x.size)
            if noise.size != x.size or np.any(noise <= 0):
                raise ValueError("noise must be a positive scalar or an array of the profile's length")
    return _peaks_core(x, y, snr, bw, int(max_peaks), noise)


def _peaks_core(x, y, snr, bw, max_peaks, noise):
    """:func:`diffraction_peaks` の本体(検査済みの x, y。x は 2θ でなく半径 [px] でもよい)。``bw=None`` は背景 0。"""
    dx = float(np.median(np.diff(x)))
    if bw is None:
        base = np.zeros_like(y)
    else:
        wpts = max(3, int(round(bw / dx)) | 1)
        base = _baseline(y, wpts)
    z = y - base
    if noise is None:
        # 隣のビンは画素の分け方で相関する(1 画素が数ビンにまたがる)ので、差分の間隔 1〜8 の MAD の最大を雑音とする
        # (間隔 1 だけだと相関で雑音を数倍小さく見積もり、雑音の揺れを山として拾う)
        sigma = 0.0
        for lag in (1, 2, 4, 8):
            if z.size > lag + 4:
                dz = z[lag:] - z[:-lag]
                sigma = max(sigma, 1.4826 * float(np.median(np.abs(dz - np.median(dz)))) / math.sqrt(2.0))
    else:
        sigma = noise
    floor = 1e-12 * max(float(np.max(np.abs(y))), 1e-300)
    sig_arr = np.maximum(np.broadcast_to(np.asarray(sigma, dtype=np.float64), z.shape), floor)
    zs = np.convolve(z, [0.25, 0.5, 0.25], mode="same")
    cand = np.where((zs[1:-1] >= zs[:-2]) & (zs[1:-1] > zs[2:]) & (zs[1:-1] > snr * sig_arr[1:-1]))[0] + 1
    # 2 標本以内の候補は高い方だけ
    keep = []
    for i in cand[np.argsort(-z[cand])]:
        if all(abs(i - j) > 2 for j in keep):
            keep.append(i)
    keep = sorted(keep[:int(max_peaks)])
    from scipy.optimize import least_squares
    out = {k: [] for k in ("two_theta", "height", "fwhm", "area", "snr", "fit_ok")}
    for n, i in enumerate(keep):
        half = z[i] / 2.0
        lo = i
        while lo > 0 and z[lo] > half:
            lo -= 1
        hi = i
        while hi < z.size - 1 and z[hi] > half:
            hi += 1
        w0 = max((x[hi] - x[lo]), 2 * dx)
        a = max(0, i - int(round(1.5 * w0 / dx)) - 2)
        b = min(z.size, i + int(round(1.5 * w0 / dx)) + 3)
        if n > 0:
            a = max(a, (keep[n - 1] + i) // 2 + 1)
        if n + 1 < len(keep):
            b = min(b, (keep[n + 1] + i) // 2)
        if b - a < 5:
            a, b = max(0, i - 2), min(z.size, i + 3)
        xs, ys = x[a:b], z[a:b]

        def res(p, xs=xs, ys=ys):
            A, x0, wv, c0, c1 = p
            return A * np.exp(-4 * math.log(2) * (xs - x0) ** 2 / wv ** 2) + c0 + c1 * (xs - xs.mean()) - ys

        p0 = [z[i], x[i], w0, 0.0, 0.0]
        lb = [0.0, x[i] - w0, 0.25 * dx, -np.inf, -np.inf]
        ub = [np.inf, x[i] + w0, 20 * w0 + dx, np.inf, np.inf]
        try:
            r = least_squares(res, p0, bounds=(lb, ub))
            A, x0, wv = float(r.x[0]), float(r.x[1]), float(r.x[2])
            ok = bool(r.success) and xs[0] <= x0 <= xs[-1]
        except (ValueError, np.linalg.LinAlgError):
            A, x0, wv, ok = float(z[i]), float(x[i]), float(w0), False
        out["two_theta"].append(x0)
        out["height"].append(A)
        out["fwhm"].append(wv)
        out["area"].append(A * wv * math.sqrt(math.pi / (4 * math.log(2))))
        out["snr"].append(A / float(sig_arr[i]))
        out["fit_ok"].append(ok)
    res_d = {k: np.asarray(v, dtype=bool if k == "fit_ok" else np.float64) for k, v in out.items()}
    res_d["noise"] = sigma if np.ndim(sigma) == 0 else np.asarray(sigma)
    res_d["baseline"] = base
    return res_d


def _allowed_N(lattice, n_max=400):
    """格子の許される N = h²+k²+l² と代表の (h, k, l)(h >= k >= l >= 0)。"""
    out = {}
    m = int(math.isqrt(n_max)) + 1
    for h in range(m + 1):
        for k in range(h + 1):
            for l_ in range(k + 1):
                N = h * h + k * k + l_ * l_
                if N == 0 or N > n_max:
                    continue
                par = [h % 2, k % 2, l_ % 2]
                ok = {"P": True, "I": (h + k + l_) % 2 == 0,
                      "F": len(set(par)) == 1,
                      "diamond": len(set(par)) == 1 and not (par == [0, 0, 0] and (h + k + l_) % 4 == 2)}[lattice]
                if ok and N not in out:
                    out[N] = (h, k, l_)
    return dict(sorted(out.items()))


def cubic_index(two_theta, wavelength, lattices=LATTICES, tolerance=0.05, n_first=6, max_unindexed=0):
    """立方晶として山に指数を付け、格子(P / I / F / diamond)と格子定数 a [Å] を決める。

    ``1/d² = N / a²`` なので、1 本目の山に許される N の小さい方から ``n_first`` 個を当てて a を仮に決め、全部の山を
    最も近い許される N に割り当て、``a`` を最小二乗で追い込み(割り当て → 追い込みを 2 回)、計算と観測の 2θ の差が
    ``tolerance`` [deg] 以内の候補だけを残す(外れる山が ``max_unindexed`` 本までなら、それを除いて残す —— 不純物や
    偽の山が 1 本混じっただけで全部を捨てないため。除いた山は ``unindexed`` に返す)。候補どうしは de Wolff の M 型の性能指数
    ``M = Q_last / (2 ε̄ N_calc)``(``Q = 1/d²``、``ε̄`` = |ΔQ| の平均、``N_calc`` = 最後の観測線までに許される計算線の数)
    で比べる —— P は何にでも合うが計算線が多いぶん M が下がる。外した山がある候補は ``(指数の付いた割合)⁴`` で割り引く
    (経験的な重み。強い山を捨てて計算線の少ない格子に逃げるのを防ぐ)。

    返り値(dict): ``lattice``・``a``・``a_sigma``(残差からの標準誤差)・``two_theta``(指数の付いた山)・``hkl``((n, 3))・
    ``N``・``residual_deg``(観測 − 計算)・``fom``・``missing``(範囲内で許されるのに観測に無い N の list)・``unindexed``
    (外した山)・``candidates``(全候補の要約)。
    当てはまる候補が無ければ ``lattice = None``(立方晶でない・山の取り違え)。

    Raises ValueError: 山が 2 本未満・非有限・(0, 180) の外、波長が非正、格子の綴り違い。
    """
    t = np.sort(_vec(two_theta, "two_theta", 2))
    if np.any(t <= 0) or np.any(t >= 180):
        raise ValueError("two_theta must be in (0, 180) degrees")
    lam = _num(wavelength, "wavelength", positive=True)
    tol = _num(tolerance, "tolerance", positive=True)
    for L in lattices:
        _choice(L, "lattice", LATTICES)
    q = (2 * np.sin(np.radians(t / 2)) / lam) ** 2
    cands = []
    for L in lattices:
        allowed = _allowed_N(L)
        Ns = np.array(list(allowed))
        for N0 in Ns[:int(n_first)]:
            inv_a2 = q[0] / N0

            def _tth(qq):
                return np.degrees(2 * np.arctan2(lam * np.sqrt(qq) / 2, np.sqrt(np.clip(1 - lam ** 2 * qq / 4, 0, None))))

            use = np.ones(t.size, dtype=bool)
            for _ in range(4):
                Nassign = Ns[np.argmin(np.abs(q[:, None] / inv_a2 - Ns[None, :]), axis=1)]
                # 追い込みは 2θ の差が tolerance 以内の山だけで(偽の山 1 本が高い N の重みで a を引きずらないように)
                use = np.abs(t - _tth(Nassign * inv_a2)) <= tol
                if use.sum() < 2:
                    break
                inv_a2 = float(np.sum(Nassign[use] * q[use]) / np.sum(Nassign[use] ** 2))
            Nassign = Ns[np.argmin(np.abs(q[:, None] / inv_a2 - Ns[None, :]), axis=1)]
            qc = Nassign * inv_a2
            tc = np.degrees(2 * np.arctan2(lam * np.sqrt(qc) / 2, np.sqrt(np.clip(1 - lam ** 2 * qc / 4, 0, None))))
            resid = t - tc
            bad = np.abs(resid) > tol
            if bad.sum() > int(max_unindexed) or (~bad).sum() < min(3, t.size):
                continue
            if bad.any():
                # 外れた山を除いて a を追い込み直す
                inv_a2 = float(np.sum(Nassign[~bad] * q[~bad]) / np.sum(Nassign[~bad] ** 2))
                qc = Nassign * inv_a2
                tc = np.degrees(2 * np.arctan2(lam * np.sqrt(qc) / 2, np.sqrt(np.clip(1 - lam ** 2 * qc / 4, 0, None))))
                resid = t - tc
                bad = np.abs(resid) > tol
                if bad.sum() > int(max_unindexed) or (~bad).sum() < min(3, t.size):
                    continue
            unind = t[bad]
            t_i, q_i, qc_i, N_i = t[~bad], q[~bad], qc[~bad], Nassign[~bad]
            ncalc = int(np.sum(Ns * inv_a2 <= q_i[-1] * (1 + 1e-9)))
            eps = max(float(np.mean(np.abs(q_i - qc_i))), 1e-9 * float(q_i[-1]))
            # 外した山があれば (指数の付いた割合)⁴ で割り引く —— 割り引かないと、強い山を「外れ」に捨てて計算線の少ない
            # 格子に逃げる候補が勝つ(岩塩型 MgO の 200 と 220 を捨てて diamond を選んだ、2026-10-05 に実測)
            fom = float(q_i[-1] / (2 * eps * ncalc)) * (len(q_i) / len(q)) ** 4
            a = 1.0 / math.sqrt(inv_a2)
            # a の標準誤差: q = N/a² の当てはめの残差から
            if len(q_i) > 1:
                s2 = float(np.sum((q_i - qc_i) ** 2) / max(len(q_i) - 1, 1))
                var_inv = s2 / float(np.sum(N_i ** 2))
                a_sig = 0.5 * a ** 3 * math.sqrt(var_inv)
            else:
                a_sig = float("nan")
            obs = set(N_i.tolist())
            missing = [int(N) for N in Ns if N * inv_a2 <= q_i[-1] * (1 + 1e-9) and N not in obs]
            cands.append({"lattice": L, "a": a, "a_sigma": a_sig, "N": N_i.astype(int), "two_theta": t_i,
                          "hkl": np.array([allowed[int(N)] for N in N_i], dtype=int), "residual_deg": resid[~bad],
                          "fom": fom, "n_calc": ncalc, "missing": missing, "unindexed": unind})
    if not cands:
        return {"lattice": None, "a": float("nan"), "a_sigma": float("nan"), "hkl": np.zeros((0, 3), int),
                "N": np.zeros(0, int), "two_theta": np.zeros(0), "residual_deg": np.zeros(0), "fom": 0.0,
                "missing": [], "unindexed": t, "candidates": []}
    cands.sort(key=lambda c: (-c["fom"], c["n_calc"]))
    best = dict(cands[0])
    best["candidates"] = [{"lattice": c["lattice"], "a": c["a"], "fom": c["fom"], "n_calc": c["n_calc"]} for c in cands[:12]]
    return best


# ----------------------------------------------------------------------------------------------
# 検出器の較正
# ----------------------------------------------------------------------------------------------
def _circle_fit(px, py):
    A = np.column_stack([2 * px, 2 * py, np.ones_like(px)])
    sol, *_ = np.linalg.lstsq(A, px * px + py * py, rcond=None)
    cx, cy, c = sol
    return float(cx), float(cy), float(math.sqrt(max(c + cx * cx + cy * cy, 0.0)))


def _ray_samples(im, cx, cy, n_az, rmax, step=0.5):
    from scipy.ndimage import map_coordinates
    chi = np.arange(n_az) * 2 * np.pi / n_az
    r = np.arange(0, rmax, step)
    X = cx + r[None, :] * np.cos(chi[:, None])
    Y = cy + r[None, :] * np.sin(chi[:, None])
    v = map_coordinates(im, [Y, X], order=1, mode="constant", cval=np.nan)
    return chi, r, v


def _nanmean0(v):
    """列ごとの nan を除いた平均(全部 nan の列は nan、警告なし)。"""
    f = np.isfinite(v)
    n = f.sum(0)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(n > 0, np.where(f, v, 0.0).sum(0) / np.maximum(n, 1), np.nan)


def _ring_point(r, prof, r0, win):
    sel = (r >= r0 - win) & (r <= r0 + win) & np.isfinite(prof)
    if sel.sum() < 5:
        return None
    rs, vs = r[sel], prof[sel]
    base = np.min(vs)
    wv = vs - base
    if wv.max() <= 0:
        return None
    k = int(np.argmax(wv))
    if k == 0 or k == wv.size - 1:
        return None
    top = wv >= 0.5 * wv[k]
    # 最大を含む連続区間だけで重心
    lo = k
    while lo > 0 and top[lo - 1]:
        lo -= 1
    hi = k
    while hi < top.size - 1 and top[hi + 1]:
        hi += 1
    ww = wv[lo:hi + 1]
    return float(np.sum(rs[lo:hi + 1] * ww) / np.sum(ww)), float(wv[k])


def detector_calibrate(image, d_spacings, geometry_guess, n_azimuth=180, fit_tilt=True, min_rings=2):
    """既知の標準(Si など)の環から検出器の中心・距離・傾きを較正する。

    ``d_spacings`` は標準の面間隔 [Å] の list(強い順でなくてよい)、``geometry_guess`` には少なくとも ``pixel`` と
    ``wavelength``、分かっていれば ``cx``・``cy``・``distance``・``tilt``・``tilt_dir`` を入れる。手順:

    1. 中心が無ければ明るい画素の重心から始め、最も強い環を光線に沿って拾い、円の当てはめで中心を 3 回更新する。
    2. 距離が無ければ、半径方向のプロファイルの最初の山を d の候補(小さい 2θ から 4 本)に当て、他の環の予測と
       観測の山が最も多く一致する組を選ぶ。
    3. 現在の幾何で各環の位置を ``n_azimuth`` 本の光線上で予測し、窓の中の強度の重心で点を拾い、
       ``scipy.optimize.least_squares`` で ``(cx, cy, distance, tilt の 2 成分)`` を 2θ の残差 [deg] で当てる。窓を
       縮めながら 3 回。傾きは回転ベクトルの 2 成分 ``tilt·(cos φ, sin φ)`` で解く(傾き 0 で φ が不定になる特異点を避ける)。

    返り値(dict): 幾何(``cx``・``cy``・``distance``・``pixel``・``wavelength``・``tilt``・``tilt_dir``)に
    ``rms_two_theta_deg``・``n_points``・``n_rings``・``rings_deg``・``ok``(rms が画素 1/4 の角 ``0.25·pixel/distance`` 未満
かつ環 >= ``min_rings``)を足したもの。

    Raises ValueError: 像が 2-D でない、d が 1 本も無い、pixel / wavelength が無い、環が ``min_rings`` 本見つからない。
    """
    from scipy.optimize import least_squares
    im = _image(image)
    if not np.all(np.isfinite(im)):
        raise ValueError("image has nan/inf")
    ds = _vec(d_spacings, "d_spacings", 1)
    if np.any(ds <= 0):
        raise ValueError("d_spacings must be > 0")
    if not isinstance(geometry_guess, dict) or "pixel" not in geometry_guess or "wavelength" not in geometry_guess:
        raise ValueError("geometry_guess must be a dict with at least 'pixel' and 'wavelength'")
    pix = _num(geometry_guess["pixel"], "pixel", positive=True)
    lam = _num(geometry_guess["wavelength"], "wavelength", positive=True)
    nring = int(_num(min_rings, "min_rings", positive=True))
    tth_k = np.sort(_two_theta_deg(ds, lam))
    tth_k = tth_k[np.isfinite(tth_k)]
    if tth_k.size == 0:
        raise ValueError("no d-spacing is reachable at this wavelength (lambda > 2d)")
    H, W = im.shape
    rmax = float(math.hypot(H, W))
    # 1. 中心
    if "cx" in geometry_guess and "cy" in geometry_guess:
        cx, cy = _num(geometry_guess["cx"], "cx"), _num(geometry_guess["cy"], "cy")
    else:
        thr = np.quantile(im, 0.995)
        yy, xx = np.nonzero(im >= thr)
        cx, cy = float(xx.mean()), float(yy.mean())
        for _ in range(3):
            chi, r, v = _ray_samples(im, cx, cy, 72, rmax)
            prof = _nanmean0(v)
            prof = np.where(np.isfinite(prof), prof, 0.0)
            pb = prof - _baseline(prof, 41)
            rstar = r[int(np.argmax(pb[10:])) + 10]
            pts = [_ring_point(r, v[i], rstar, 12) for i in range(chi.size)]
            ok = [(chi[i], p[0]) for i, p in enumerate(pts) if p is not None]
            if len(ok) < 8:
                break
            px = np.array([cx + rr_ * math.cos(c_) for c_, rr_ in ok])
            py = np.array([cy + rr_ * math.sin(c_) for c_, rr_ in ok])
            cx, cy, _rad = _circle_fit(px, py)
    # 2. 距離
    if "distance" in geometry_guess:
        D = _num(geometry_guess["distance"], "distance", positive=True)
    else:
        yy, xx = np.mgrid[0:H, 0:W]
        ib = np.hypot(yy - cy, xx - cx).astype(int).ravel()
        cnt = np.bincount(ib)
        with np.errstate(invalid="ignore", divide="ignore"):
            prof = np.bincount(ib, weights=im.ravel()) / cnt
        r = np.arange(prof.size, dtype=np.float64)
        good = cnt >= 20
        pk = _peaks_core(r[good][2:], prof[good][2:], 8.0, 8.0, 60, None)
        robs, hobs = pk["two_theta"], pk["height"]
        if robs.size < 2:
            raise ValueError("fewer than 2 rings visible in the radial profile; give geometry_guess['distance']")
        rvis = float(r[good].max())
        best = None
        for o in robs[np.argsort(-hobs)[:3]]:
            for k in range(min(4, tth_k.size)):
                Dk = o * pix / math.tan(math.radians(tth_k[k]))
                rp = Dk * np.tan(np.radians(tth_k)) / pix
                rp = rp[(rp > 3) & (rp < rvis - 3)][:5]          # 内側の 5 本(傾きで外側ほど環が割れる)
                if rp.size < 2:
                    continue
                dist = np.array([np.min(np.abs(robs - x_)) for x_ in rp])
                frac = float(np.mean(dist < 2.0 + 0.03 * rp))
                key = (frac, -float(np.mean(np.minimum(dist, 5.0))))
                if best is None or key > best[0]:
                    best = (key, Dk)
        if best is None:
            raise ValueError("could not assign the visible rings to the d-spacings; give geometry_guess['distance']")
        D = best[1]
    t0 = _num(geometry_guess.get("tilt", 0.0), "tilt")
    p0 = _num(geometry_guess.get("tilt_dir", 0.0), "tilt_dir")
    params = np.array([cx, cy, D, t0 * math.cos(math.radians(p0)), t0 * math.sin(math.radians(p0))])

    def geom_of(p):
        tilt = math.hypot(p[3], p[4])
        return {"cx": p[0], "cy": p[1], "distance": p[2], "pixel": pix, "wavelength": lam, "tilt": tilt,
                "tilt_dir": math.degrees(math.atan2(p[4], p[3])) if tilt > 0 else 0.0}

    from scipy.ndimage import map_coordinates
    rms = float("inf")
    used = []
    pts_r = pts_c = pts_k = None
    for it, win in enumerate((10.0, 5.0, 3.0, 3.0)):
        g = geom_of(params)
        # 各環の各光線上で予測の半径を求める
        n_az = int(n_azimuth)
        chi = np.arange(n_az) * 2 * np.pi / n_az
        rs = np.arange(0, rmax, 0.25)
        X = g["cx"] + rs[None, :] * np.cos(chi[:, None])
        Y = g["cy"] + rs[None, :] * np.sin(chi[:, None])
        T, _c, _o = _tth_chi(Y, X, g)
        V = map_coordinates(im, [Y, X], order=1, mode="constant", cval=np.nan)
        prow, pcol, pk_ = [], [], []
        used = []
        for k, tk in enumerate(tth_k):
            n_ok = 0
            for i in range(n_az):
                Ti = T[i]
                j = np.searchsorted(Ti, tk)
                if j <= 0 or j >= Ti.size or not np.isfinite(V[i, j]):
                    continue
                r0 = rs[j]
                # 隣の環との間隔の半分より窓を広げない
                pr = _ring_point(rs, V[i], r0, win)
                if pr is None:
                    continue
                rr_, h = pr
                prow.append(g["cy"] + rr_ * math.sin(chi[i]))
                pcol.append(g["cx"] + rr_ * math.cos(chi[i]))
                pk_.append(tk)
                n_ok += 1
            if n_ok >= max(8, n_az // 6):
                used.append(float(tk))
            else:
                # 点の少ない環(画像の外・弱すぎる)は捨てる
                cut = len(pk_) - n_ok
                del prow[cut:], pcol[cut:], pk_[cut:]
        if len(used) < nring:
            raise ValueError("only %d calibration ring(s) found (need %d); check the guess and d_spacings" % (len(used), nring))
        pts_r, pts_c, pts_k = np.array(prow), np.array(pcol), np.array(pk_)

        def resid(p):
            gg = geom_of(p)
            tt, _cc, _oo = _tth_chi(pts_r, pts_c, gg)
            return tt - pts_k

        free = np.ones(5, dtype=bool) if fit_tilt else np.array([True, True, True, False, False])

        def resid_free(pf):
            p = params.copy()
            p[free] = pf
            return resid(p)

        r_ = least_squares(resid_free, params[free], x_scale="jac", loss="soft_l1", f_scale=0.02)
        params[free] = r_.x
        rr = resid(params)
        # 外れ点(重なり・雑音)を 4 σ で落として最後にもう一度
        keep = np.abs(rr) < max(4 * np.std(rr), 1e-4)
        pts_r, pts_c, pts_k = pts_r[keep], pts_c[keep], pts_k[keep]
        rms = float(np.sqrt(np.mean(resid(params) ** 2)))
    g = geom_of(params)
    g.update({"rms_two_theta_deg": rms, "n_points": int(pts_k.size), "n_rings": len(used), "rings_deg": used,
              "ok": bool(rms < 0.25 * math.degrees(pix / g["distance"]) and len(used) >= nring)})
    return g


# ----------------------------------------------------------------------------------------------
# 参照パターンの辞書と相分率
# ----------------------------------------------------------------------------------------------
def phase_dictionary(phases, two_theta, wavelength, size=math.inf, K=0.9, instrumental_fwhm=0.02, lorentz="powder",
                     eta=0.0):
    """相の参照パターンの辞書: 2θ の格子の上に、体積分率 1 あたりの 1-D 強度を相ごとに並べる。

    1 行 = ``(1/V²) Σ m|F|² L(2θ) × 形``(形は Scherrer の ``size`` [Å] と装置の FWHM をガウスで足した幅の pseudo-Voigt、
    ``eta`` は Lorentz の割合)。``instrumental_fwhm`` は数 [deg] か ``(2θ の列, FWHM の列)`` の表 —— 平らな検出器では画素の
    張る角が ``cos² 2θ`` で縮むので装置の幅は 2θ で変わる。広がりの無い標準(Si)の像を同じ幾何で積分し、
    :func:`diffraction_peaks` の FWHM を表にして渡すのが筋(PoC の手順)。:func:`azimuthal_integrate` を偏光・立体角の補正つきで回したプロファイルと同じ量に揃う。
    幅が合っていないと NNLS の倍率が偏る —— :func:`diffraction_peaks` の FWHM と :func:`scherrer_size` で ``size`` を
    先に見積もるのが筋。

    返り値(dict): ``names``・``two_theta``・``matrix``((P, n))・``density`` [g/cm³]・``phases``(元の相、格子の追い込みで
    描き直すため)・``params``(波長・幅・Lorentz)。

    Raises ValueError: 相が空・相の形でない、名前の重複、格子が増えない、幅の値が不正。
    """
    if isinstance(phases, dict):
        phases = [phases]
    if not isinstance(phases, (list, tuple)) or not phases:
        raise ValueError("phases must be a non-empty list of phase dicts")
    for i, p in enumerate(phases):
        _check_phase(p, "phases[%d]" % i)
    names = [p["name"] for p in phases]
    if len(set(names)) != len(names):
        raise ValueError("phase names must be unique, got %r" % names)
    x = _vec(two_theta, "two_theta", 7)
    if np.any(np.diff(x) <= 0) or x[0] <= 0 or x[-1] >= 180:
        raise ValueError("two_theta must be strictly increasing within (0, 180)")
    lam = _num(wavelength, "wavelength", positive=True)
    sz = _num(size, "size", positive=True, allow_inf=True)
    inst = _inst_spec(instrumental_fwhm)
    _choice(lorentz, "lorentz", _LORENTZ)
    K = _num(K, "K", positive=True)
    eta = _num(eta, "eta", nonneg=True)
    M = np.stack([_phase_profile(p, x, lam, sz, K, inst, lorentz, 1.0, eta)[0] for p in phases])
    return {"names": names, "two_theta": x, "matrix": M, "density": np.array([p["density"] for p in phases]),
            "phases": list(phases), "params": {"wavelength": lam, "size": sz, "K": K, "instrumental_fwhm": inst,
                                               "lorentz": lorentz, "eta": eta}}


def _check_dict(dic):
    if not isinstance(dic, dict) or "matrix" not in dic or "names" not in dic:
        raise ValueError("dictionary must come from phase_dictionary")
    return dic


def _cheb(x, order):
    """背景の Chebyshev の基底 T₀..T_order(2θ を [−1, 1] に写して漸化式で。cos(k·arccos t) は端で丸めの床がある)。"""
    t = 2 * (x - x[0]) / (x[-1] - x[0]) - 1
    return np.polynomial.chebyshev.chebvander(t, order).T


def _solve(y, M, B, wts):
    from scipy.optimize import lsq_linear
    A = np.vstack([M, B]).T
    nrm = np.maximum(np.abs(A).max(0), 1e-300)
    An = A / nrm
    lb = np.r_[np.zeros(M.shape[0]), -np.inf * np.ones(B.shape[0])]
    ub = np.inf * np.ones(A.shape[1])
    r = lsq_linear(An * wts[:, None], y * wts, bounds=(lb, ub), lsmr_tol="auto", method="bvls")
    coef = r.x / nrm
    return coef, A @ coef


def phase_fractions(two_theta, intensity, dictionary, background_order=4, sigma=None, lattice_tolerance=0.0,
                    phases=None):
    """非負の最小二乗(NNLS)で混合物の相分率を出す(背景は Chebyshev の多項式で同時に当てる)。

    ``y ≈ Σ sₚ Rₚ(2θ) + Σ cₖ Tₖ(2θ)``、``sₚ >= 0``、``cₖ`` は符号自由(``scipy.optimize.lsq_linear`` の BVLS)。
    体積分率 ``vₚ ∝ sₚ``、重量分率 ``Wₚ ∝ sₚ ρₚ``(module の docstring)。``sigma`` を渡せば 1/σ で重みを付ける。
    ``lattice_tolerance`` > 0 なら相ごとに格子の倍率を ``1 ± tolerance`` の中で黄金分割の座標降下で追い込む
    (参照の格子定数と試料の格子定数がずれていると、山が半分ずれた参照は倍率が下がり分率が偏る —— 罠の門を参照)。
    ``phases`` で辞書の一部の名前だけを使う。

    返り値(dict): ``names``・``scale``・``volume_fraction``・``weight_fraction``・``lattice_scale``・``fit``・
    ``background``・``residual``・``rwp``(重みつきの相対残差)・``two_theta``・``wavelength``。

    Raises ValueError: 長さの不一致、辞書の格子と 2θ の不一致、背景の次数が負、未知の相の名前。
    """
    x, y = _axis(two_theta, intensity)
    dic = _check_dict(dictionary)
    if dic["two_theta"].shape != x.shape or not np.allclose(dic["two_theta"], x, rtol=0, atol=1e-9):
        raise ValueError("intensity must be sampled on the dictionary's two_theta grid")
    order = int(_num(background_order, "background_order", nonneg=True))
    tol = _num(lattice_tolerance, "lattice_tolerance", nonneg=True)
    if tol >= 0.1:
        raise ValueError("lattice_tolerance must be < 0.1 (10 %)")
    names = list(dic["names"]) if phases is None else list(phases)
    for n_ in names:
        if n_ not in dic["names"]:
            raise ValueError("unknown phase %r (dictionary has %r)" % (n_, dic["names"]))
    idx = [dic["names"].index(n_) for n_ in names]
    M = dic["matrix"][idx].copy()
    if sigma is None:
        wts = np.ones_like(y)
    else:
        sg = _vec(sigma, "sigma", x.size)
        if sg.size != x.size or np.any(sg <= 0):
            raise ValueError("sigma must be > 0 with the length of intensity")
        wts = 1.0 / sg
    B = _cheb(x, order)
    pr = dic["params"]
    scales = np.ones(len(idx))

    def chi2(Mx):
        coef, fit = _solve(y, Mx, B, wts)
        return float(np.sum(((y - fit) * wts) ** 2)), coef, fit

    if tol > 0:
        gr = (math.sqrt(5) - 1) / 2
        for _sweep in range(2):
            for j, i in enumerate(idx):
                ph = dic["phases"][i]

                def f(sc, j=j, ph=ph):
                    Mx = M.copy()
                    Mx[j] = _phase_profile(ph, x, pr["wavelength"], pr["size"], pr["K"], pr["instrumental_fwhm"],
                                           pr["lorentz"], sc, pr["eta"])[0]
                    return chi2(Mx)[0], Mx[j]

                a_, b_ = 1 - tol, 1 + tol
                c_, d_ = b_ - gr * (b_ - a_), a_ + gr * (b_ - a_)
                fc, fd = f(c_)[0], f(d_)[0]
                for _ in range(22):
                    if fc < fd:
                        b_, d_, fd = d_, c_, fc
                        c_ = b_ - gr * (b_ - a_)
                        fc = f(c_)[0]
                    else:
                        a_, c_, fc = c_, d_, fd
                        d_ = a_ + gr * (b_ - a_)
                        fd = f(d_)[0]
                sc = 0.5 * (a_ + b_)
                scales[j] = sc
                M[j] = f(sc)[1]
    _c2, coef, fit = chi2(M)
    s = coef[:len(idx)]
    bg = coef[len(idx):] @ B
    rho = dic["density"][idx]
    vs = s / s.sum() if s.sum() > 0 else np.zeros_like(s)
    ws = s * rho / np.sum(s * rho) if s.sum() > 0 else np.zeros_like(s)
    rwp = float(np.sqrt(np.sum(((y - fit) * wts) ** 2) / max(np.sum((y * wts) ** 2), 1e-300)))
    return {"names": names, "scale": s, "volume_fraction": vs, "weight_fraction": ws, "lattice_scale": scales,
            "fit": fit, "background": bg, "residual": y - fit, "rwp": rwp, "two_theta": x,
            "wavelength": pr["wavelength"]}


def unexplained_peaks(fit_result, intensity=None, min_snr=6.0, index=True, noise=None, known_ratio=0.25,
                      model_error=0.1):
    """相分率の当てはめの残差から、辞書のどの相でも説明できない山を取り出す(未知相の手がかり)。

    残差(``fit_result`` の ``residual``、または ``intensity − fit``)に :func:`diffraction_peaks` をかけ、正の山だけを
    残す。既知相の強い線の上に乗った残差の山(高さが、その位置の既知相の模型の ``known_ratio`` 倍未満)は幅や形の
    合わなさの名残りである見込みが高いので ``near_known=True`` の印を付け、指数付けからは外す(消さずに返す)。残りが
    3 本以上あれば :func:`cubic_index` で立方晶として指数付けを試みる(``index=True``、外れ 1/3 まで許す)。既知相の格子が
    ずれていると残差に「正と負の対」が出て偽の山になる —— その場合は :func:`phase_fractions` の ``lattice_tolerance`` を先に使う。
    ``noise`` には :func:`azimuthal_integrate` の ``sigma`` を渡すのが筋(無ければ残差の MAD から見積もる)。山の判定に使う
    雑音は ``sqrt(noise² + (model_error × 既知相の模型)²)`` —— 計数が多いと Poisson の σ は小さく、強い既知線の形の
    わずかな合わなさ(画素の箱形の広がりをガウスで近似した名残り。合成像で rwp 2〜4 %)が何千 σ の「山」に見えるので、
    模型そのものの相対誤差を雑音の床に入れる。

    返り値(dict): ``two_theta``・``d`` [Å]・``height``・``fwhm``・``snr``・``near_known``(bool)・``index``
    (:func:`cubic_index` の結果か None)。

    Raises ValueError: ``fit_result`` が :func:`phase_fractions` の形でない、長さの不一致。
    """
    if not isinstance(fit_result, dict) or "residual" not in fit_result or "two_theta" not in fit_result:
        raise ValueError("fit_result must come from phase_fractions")
    x = _vec(fit_result["two_theta"], "two_theta", 7)
    if intensity is None:
        r = _vec(fit_result["residual"], "residual", 7)
    else:
        r = _vec(intensity, "intensity", 7) - _vec(fit_result["fit"], "fit", 7)
    if r.size != x.size:
        raise ValueError("residual and two_theta lengths differ")
    lam = _num(fit_result.get("wavelength", float("nan")), "wavelength", positive=True)
    # 残差は 0 の周りなので、背景の窓は狭く(負の側の対は背景が吸わない)
    kr = _num(known_ratio, "known_ratio", nonneg=True)
    me = _num(model_error, "model_error", nonneg=True)
    model = np.asarray(fit_result["fit"], dtype=np.float64) - np.asarray(fit_result.get("background", 0.0))
    if noise is None:
        dz = np.diff(r)
        base_noise = 1.4826 * float(np.median(np.abs(dz - np.median(dz)))) / math.sqrt(2.0)
    elif np.ndim(noise) == 0:
        base_noise = _num(noise, "noise", positive=True)
    else:
        base_noise = _vec(noise, "noise", x.size)
        if base_noise.size != x.size:
            raise ValueError("noise must be a scalar or an array of the profile's length")
    eff = np.sqrt(np.asarray(base_noise, dtype=np.float64) ** 2 + (me * np.maximum(model, 0.0)) ** 2)
    eff = np.maximum(np.broadcast_to(eff, x.shape), 1e-12 * max(float(np.max(np.abs(r))), 1e-300))
    # 残差は背景を引いた後の量なので背景は 0(転がり最小を使うと負の谷の間が「山」に見える —— 2026-10-05 に実測)
    pk = _peaks_core(x, r, _num(min_snr, "min_snr", positive=True), None, 200, eff)
    sel = pk["height"] > 0
    tt = pk["two_theta"][sel]
    h = pk["height"][sel]
    near = h < kr * np.interp(tt, x, model) if tt.size else np.zeros(0, dtype=bool)
    d = lam / (2 * np.sin(np.radians(tt / 2))) if tt.size else np.zeros(0)
    free = tt[~near]
    idx = cubic_index(free, lam, max_unindexed=free.size // 3) if (index and free.size >= 3) else None
    return {"two_theta": tt, "d": d, "height": h, "fwhm": pk["fwhm"][sel], "snr": pk["snr"][sel],
            "near_known": near, "index": idx}


def phase_peel(two_theta, intensity, dictionary, max_phases=None, min_gain=0.05, min_fraction=0.005,
               background_order=4, sigma=None):
    """混合物から相を 1 つずつ剥がす(貪欲な前進選択)。

    段 0 は背景だけ。各段で、まだ選んでいない相を 1 つずつ足して :func:`phase_fractions` を当て、``rwp`` が最も下がる
    相を選ぶ。``rwp`` の相対的な下がり幅が ``min_gain`` 未満、または選んだ相の重量分率が ``min_fraction`` 未満なら止める。
    全部の相を一度に当てる :func:`phase_fractions` と違い、「どの順で、どれだけ説明が進んだか」が残る(図の素材)。

    返り値(dict): ``order``(選んだ順の名前)・``stages``(各段の ``phases``・``weight_fraction``・``fit``・``residual``・
    ``rwp``)・``final``(最後の段の :func:`phase_fractions` の結果)。

    Raises ValueError: :func:`phase_fractions` と同じ。``min_gain`` が [0, 1) の外。
    """
    x, y = _axis(two_theta, intensity)
    dic = _check_dict(dictionary)
    mg = _num(min_gain, "min_gain", nonneg=True)
    if mg >= 1:
        raise ValueError("min_gain must be in [0, 1)")
    mf = _num(min_fraction, "min_fraction", nonneg=True)
    maxp = len(dic["names"]) if max_phases is None else int(_num(max_phases, "max_phases", positive=True))
    order = int(_num(background_order, "background_order", nonneg=True))
    wts = np.ones_like(y) if sigma is None else 1.0 / _vec(sigma, "sigma", x.size)
    B = _cheb(x, order)
    coef, fit0 = _solve(y, np.zeros((0, x.size)), B, wts)
    rwp0 = float(np.sqrt(np.sum(((y - fit0) * wts) ** 2) / np.sum((y * wts) ** 2)))
    stages = [{"phases": [], "weight_fraction": np.zeros(0), "fit": fit0, "residual": y - fit0, "rwp": rwp0}]
    chosen = []
    final = None
    while len(chosen) < maxp:
        best = None
        for n_ in dic["names"]:
            if n_ in chosen:
                continue
            r = phase_fractions(x, y, dic, background_order=order, sigma=sigma, phases=chosen + [n_])
            if best is None or r["rwp"] < best[1]["rwp"]:
                best = (n_, r)
        if best is None:
            break
        n_, r = best
        gain = 1 - r["rwp"] / stages[-1]["rwp"]
        if gain < mg or r["weight_fraction"][-1] < mf:
            break
        chosen.append(n_)
        final = r
        stages.append({"phases": list(chosen), "weight_fraction": r["weight_fraction"], "fit": r["fit"],
                       "residual": r["residual"], "rwp": r["rwp"]})
    return {"order": chosen, "stages": stages, "final": final}
