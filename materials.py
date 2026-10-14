# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""materials — 材料の物性ライブラリ(観察用の光学系と観察対象が同じ材料表を引く)。

**1 材料 = 1 レコード**で、硝材(4 社 46 種)・結晶と IR 材(12)・半導体(Si / Ge / GaAs /
GaN / InP / SiC)・膜(Si₃N₄ / TiO₂ / Ta₂O₅ / HfO₂)・金属(Ag / Au / Cu / Al / Cr / Ni / Rh /
W / Ti / Pt)・液体(水)・プラスチック(PMMA / PC / PS / COP)の 83 種を同梱する。数値はすべて
refractiveindex.info database(CC0 1.0、Polyanskiy, Sci. Data 11, 94 (2024))の一次文献の
係数と数表で、``materials_data.py`` に生成物として置く(``tools/gen_material_tables.py``)。
メーカーの硝材カタログ本体(.agf)は同梱しない —— :func:`read_glass_catalog_agf` が
ユーザーのファイルを読む。

レコードの形(``material_record`` が返す)::

    {"name": "N-BK7", "class": "glass", "aliases": ("BK7",),
     "datasets": [{"type": "formula", "formula": 2, "range_um": (0.3, 2.5), "coefficients": (...),
                   "reference": "SCHOTT Zemax catalog 2017-01-20b ...", "page": "specs/schott/optical/N-BK7.yml"},
                  {"type": "k", "range_um": (0.3, 2.5), "rows": 25, ...}],
     "properties": {"nd": 1.5168, "Vd": 64.17, "density_kg_m3": 2510.0,
                    "thermal_expansion_per_k": 7.1e-06, "dn_dt_formula_a": (D0, D1, D2, E0, E1, λ_tk)}}

``datasets`` は波長区間ごとの一次文献で、n は最初に区間が当たる formula / nk / n の表から、
k は最初に当たる nk / k の表から取る(どちらも線形補間、refractiveindex.info と同じ)。
k の表が無い区間は k = 0 とし、返り値の ``k_source`` を ``None`` にして隠さない。

**波長の単位**: op の引数は nm(可視〜SWIR の検査で使う単位)、レコード内部は µm(一次文献の
単位)。波長の曲線はすべて ``pairs``(K, 2) = (λ [nm], 値)で返す —— 光源・センサ QE・
ライトガイドの曲線と同じ形にして、像 = 光源 × 光学系 × 対象 × QE の波長積分に直接渡せる
ようにするため。

分散式(refractiveindex.info の formula 1〜9、λ は µm)::

    1: n² − 1 = C₀ + Σ Cᵢ λ² / (λ² − Cᵢ₊₁²)        2: n² − 1 = C₀ + Σ Cᵢ λ² / (λ² − Cᵢ₊₁)
    3: n² = C₀ + Σ Cᵢ λ^Cᵢ₊₁                        4: n² = C₀ + C₁ λ^C₂/(λ² − C₃^C₄) + C₅ λ^C₆/(λ² − C₇^C₈) + Σ Cᵢ λ^Cᵢ₊₁
    5: n = C₀ + Σ Cᵢ λ^Cᵢ₊₁                         6: n − 1 = C₀ + Σ Cᵢ / (Cᵢ₊₁ − λ⁻²)
    7: n = C₀ + C₁ L + C₂ L² + C₃ λ² + C₄ λ⁴ + C₅ λ⁶ (L = 1/(λ² − 0.028))
    8: (n² − 1)/(n² + 2) = C₀ + C₁ λ²/(λ² − C₂) + C₃ λ²   9: n² = C₀ + C₁/(λ² − C₂) + C₃ (λ − C₄)/((λ − C₄)² + C₅)

真値の門(tests/test_materials.py): カタログ公表値の n_d / V_d(RII の PROPERTIES)、Si の
k(1.0 µm) = 5.09e-4 と k(1.2 µm) = 2.1e-7(Green 2008)、Ag の 500 nm で n = 0.05 / k = 3.13
(Johnson & Christy 1972)、水の n(589 nm, 20 ℃) = 1.3330(Daimon & Masumura 2007)。
"""
from __future__ import annotations

import io
import os
import re

import numpy as np

import materials_data as _md

__all__ = [
    "MATERIALS", "CLASSES", "AGF_EXAMPLE",
    "material_table", "material_record", "material_optical_constants",
    "material_dispersion", "material_extinction", "material_absorption",
    "material_transmittance", "material_reflectance", "abbe_number", "glass_map",
    "thermo_optic_coefficient", "plate_focus_shift", "silicon_free_carrier_absorption",
    "material_from_sellmeier", "material_from_curves", "read_glass_catalog_agf",
]

#: フラウンホーファー線 [µm](硝材カタログの定義どおり)。
WL_F, WL_D, WL_C = 0.48613, 0.58756, 0.65627
WL_E, WL_FP, WL_CP, WL_G = 0.54607, 0.47999, 0.64385, 0.43583

CLASSES = ("glass", "crystal", "semiconductor", "film", "metal", "liquid", "polymer", "custom")

_RECORDS = {r["name"]: r for r in _md.MATERIAL_RECORDS}
_ALIASES = {a: r["name"] for r in _md.MATERIAL_RECORDS for a in r["aliases"]}
MATERIALS = tuple(sorted(_RECORDS))


# --------------------------------------------------------------------------- #
# レコードの解決と分散式                                                        #
# --------------------------------------------------------------------------- #
def _key(name: str) -> str:
    return "_".join(str(name).strip().upper().split())


def _record(material, op: str) -> dict:
    """名前(別名可)かレコード dict を 1 レコードに解決する。無ければ ValueError。"""
    if isinstance(material, dict):
        if "datasets" not in material or "name" not in material:
            raise ValueError("%s: a material record needs 'name' and 'datasets' "
                             "(use material_from_sellmeier / material_from_curves / read_glass_catalog_agf)" % op)
        return material
    if not isinstance(material, str):
        raise ValueError("%s: material must be a name or a record dict, got %r" % (op, type(material).__name__))
    key = _key(material)
    key = _ALIASES.get(key, key)
    if key not in _RECORDS:
        raise ValueError("%s: unknown material %r (%d built in; list them with material_table(), "
                         "classes: %s)" % (op, material, len(_RECORDS), ", ".join(CLASSES[:-1])))
    return _RECORDS[key]


def _formula(k: int, c, lam: np.ndarray) -> np.ndarray:
    """refractiveindex.info の分散式 *k* を λ [µm] で評価して n を返す。"""
    c = [float(v) for v in c]
    lam = np.asarray(lam, dtype=np.float64)
    l2 = lam * lam
    if k == 1:
        n2 = 1.0 + c[0] + sum(c[i] * l2 / (l2 - c[i + 1] ** 2) for i in range(1, len(c) - 1, 2))
        return np.sqrt(n2)
    if k == 2:
        n2 = 1.0 + c[0] + sum(c[i] * l2 / (l2 - c[i + 1]) for i in range(1, len(c) - 1, 2))
        return np.sqrt(n2)
    if k == 3:
        n2 = c[0] + sum(c[i] * lam ** c[i + 1] for i in range(1, len(c) - 1, 2))
        return np.sqrt(n2)
    if k == 4:
        c = c + [0.0] * (17 - len(c))
        n2 = (c[0] + c[1] * lam ** c[2] / (l2 - c[3] ** c[4]) + c[5] * lam ** c[6] / (l2 - c[7] ** c[8])
              + sum(c[i] * lam ** c[i + 1] for i in range(9, 16, 2)))
        return np.sqrt(n2)
    if k == 5:
        return c[0] + sum(c[i] * lam ** c[i + 1] for i in range(1, len(c) - 1, 2))
    if k == 6:
        return 1.0 + c[0] + sum(c[i] / (c[i + 1] - lam ** -2.0) for i in range(1, len(c) - 1, 2))
    if k == 7:
        c = c + [0.0] * (6 - len(c))
        L = 1.0 / (l2 - 0.028)
        return c[0] + c[1] * L + c[2] * L * L + c[3] * l2 + c[4] * l2 ** 2 + c[5] * l2 ** 3
    if k == 8:
        c = c + [0.0] * (4 - len(c))
        a = c[0] + c[1] * l2 / (l2 - c[2]) + c[3] * l2
        return np.sqrt((1.0 + 2.0 * a) / (1.0 - a))
    if k == 9:
        c = c + [0.0] * (6 - len(c))
        n2 = c[0] + c[1] / (l2 - c[2]) + c[3] * (lam - c[4]) / ((lam - c[4]) ** 2 + c[5])
        return np.sqrt(n2)
    raise ValueError("unsupported dispersion formula %r (refractiveindex.info formulas 1-9)" % k)


def _rows(ds):
    return np.asarray(ds["rows"], dtype=np.float64).reshape(len(ds["rows"]), -1)


def _covers(ds, lam):
    lo, hi = ds["range_um"]
    return (lam >= lo - 1e-12) & (lam <= hi + 1e-12)


#: 2 つの n の出典の継ぎ目で混ぜる幅(前の出典の終わりの波長に対する割合)。
SEAM_BLEND_FRACTION = 0.03


def _n_of(ds, lam):
    if ds["type"] == "formula":
        return _formula(ds["formula"], ds["coefficients"], lam)
    tab = _rows(ds)
    order = np.argsort(tab[:, 0])
    return np.interp(lam, tab[order, 0], tab[order, 1])


def _blend_seams(rec, lam, n):
    """前の n の出典が終わる所で、次の出典が重なっていれば、終わりの手前 3 % を線形に混ぜる(in place)。

    ★2026-10-14: 混ぜずに切り替えていたので、Si の n は 1450 nm で +0.0018 跳んでいた(Green 2008 の表 →
    Salzberg の式、隣の 1 nm 刻みの 18 倍で向きも逆)。屈折率の微分(群屈折率・分散)を取る op がこの段差を拾う。
    混ぜるのは前の出典の範囲の**最後の 3 %** だけ —— 重なりが長い記録(水: 可視の全域で 2 本が重なる)でも、
    区間の内側は各一次文献の値のまま残る。
    """
    srcs = [d for d in rec["datasets"] if d["type"] in ("formula", "nk", "n")]
    for a, b in zip(srcs, srcs[1:]):
        end = a["range_um"][1]
        if not (b["range_um"][0] < end <= b["range_um"][1]):
            continue
        start = max(end * (1.0 - SEAM_BLEND_FRACTION), b["range_um"][0], a["range_um"][0])
        m = (lam >= start) & (lam <= end) & ~np.isnan(n)
        if not np.any(m) or end <= start:
            continue
        t = (lam[m] - start) / (end - start)
        n[m] = (1.0 - t) * _n_of(a, lam[m]) + t * _n_of(b, lam[m])


def _nk(rec: dict, lam_um, op: str):
    """λ [µm](配列)の n, k と出典ラベルの列。区間外は ValueError(表の外挿はしない)。"""
    lam = np.atleast_1d(np.asarray(lam_um, dtype=np.float64))
    if lam.size == 0:
        raise ValueError("%s: no wavelengths" % op)
    if not np.all(np.isfinite(lam)) or np.any(lam <= 0.0):
        raise ValueError("%s: wavelengths must be finite and > 0" % op)
    n = np.full(lam.shape, np.nan)
    k = np.zeros(lam.shape)
    n_src = [None] * lam.size
    k_src = [None] * lam.size
    k_set = np.zeros(lam.shape, dtype=bool)
    for ds in rec["datasets"]:
        m = _covers(ds, lam)
        t = ds["type"]
        if t in ("formula", "nk", "n"):
            need = m & np.isnan(n)
            if np.any(need):
                if t == "formula":
                    n[need] = _formula(ds["formula"], ds["coefficients"], lam[need])
                else:
                    tab = _rows(ds)
                    order = np.argsort(tab[:, 0])
                    n[need] = np.interp(lam[need], tab[order, 0], tab[order, 1])
                for i in np.flatnonzero(need):
                    n_src[i] = ds.get("page") or ds.get("reference") or t
        if t in ("nk", "k"):
            need = m & ~k_set
            if np.any(need):
                tab = _rows(ds)
                order = np.argsort(tab[:, 0])
                col = 2 if t == "nk" else 1
                k[need] = np.interp(lam[need], tab[order, 0], tab[order, col])
                k_set |= need
                for i in np.flatnonzero(need):
                    k_src[i] = ds.get("page") or ds.get("reference") or t
    _blend_seams(rec, lam, n)
    if np.any(np.isnan(n)):
        lo = min(ds["range_um"][0] for ds in rec["datasets"] if ds["type"] in ("formula", "nk", "n"))
        hi = max(ds["range_um"][1] for ds in rec["datasets"] if ds["type"] in ("formula", "nk", "n"))
        bad = lam[np.isnan(n)]
        raise ValueError("%s: %s has no refractive-index data at %.4g um (data cover %.4g-%.4g um; "
                         "the table is not extrapolated)" % (op, rec["name"], float(bad[0]), lo, hi))
    if np.any(~np.isfinite(n)) or np.any(n <= 0.0) or np.any(k < 0.0):
        raise ValueError("%s: %s gives a non-physical index (n <= 0 or k < 0) in the requested range"
                         % (op, rec["name"]))
    return n, k, n_src, k_src


def _grid_nm(wl_min_nm, wl_max_nm, n_points, op):
    lo, hi, n = float(wl_min_nm), float(wl_max_nm), int(n_points)
    if not (np.isfinite(lo) and np.isfinite(hi)) or lo <= 0.0 or hi <= lo:
        raise ValueError("%s: need 0 < wl_min_nm < wl_max_nm, got %r, %r" % (op, wl_min_nm, wl_max_nm))
    if n < 2:
        raise ValueError("%s: n_points must be >= 2, got %r" % (op, n_points))
    return np.linspace(lo, hi, n)


def _pairs(x, y):
    return np.stack([np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)], axis=1)


def _fresnel(m, cos_i, polarization: str):
    """複素屈折率 m = n + ik の面(入射側は真空)の反射率(Born & Wolf §13.2)。"""
    if polarization not in ("unpolarized", "s", "p"):
        raise ValueError("polarization must be unpolarized / s / p, got %r" % (polarization,))
    s2 = 1.0 - cos_i ** 2
    eta = np.sqrt(m * m - s2)
    rs = (cos_i - eta) / (cos_i + eta)
    rp = (m * m * cos_i - eta) / (m * m * cos_i + eta)
    Rs, Rp = np.abs(rs) ** 2, np.abs(rp) ** 2
    return Rs if polarization == "s" else Rp if polarization == "p" else 0.5 * (Rs + Rp)


def _intervals(datasets) -> tuple:
    """n のデータが覆う波長区間 [µm] を併合した列(穴があれば 2 つ以上になる)。"""
    spans = sorted((float(ds["range_um"][0]), float(ds["range_um"][1])) for ds in datasets)
    out = []
    for lo, hi in spans:
        if out and lo <= out[-1][1] * (1 + 1e-9):
            out[-1] = (out[-1][0], max(out[-1][1], hi))
        else:
            out.append((lo, hi))
    return tuple(out)


def _summary(rec: dict) -> dict:
    """数表の行を件数に畳んだレコードのコピー(表そのものは大きいので op の返り値には載せない)。"""
    out = {"name": rec["name"], "class": rec["class"], "aliases": tuple(rec.get("aliases", ())),
           "properties": dict(rec.get("properties", {})), "datasets": []}
    for ds in rec["datasets"]:
        d = {k: v for k, v in ds.items() if k != "rows"}
        d["range_um"] = tuple(float(v) for v in ds["range_um"])
        if "rows" in ds:
            d["rows"] = len(ds["rows"])
        out["datasets"].append(d)
    return out


# --------------------------------------------------------------------------- #
# 台帳 op                                                                       #
# --------------------------------------------------------------------------- #
def material_table(material_class: str = None) -> list:
    """同梱の材料表の一覧(名前・分類・波長範囲・n_d・V_d・出典)を返す。

    ``material_class`` で分類(glass / crystal / semiconductor / film / metal / liquid /
    polymer)に絞る。``None`` は全部。知らない分類は ValueError。

    返り値: 1 材料 1 行の dict の列。``range_um`` は n のデータが覆う波長 [µm] の両端、
    ``intervals_um`` は覆う区間の列(一次文献のあいだに穴があればここに出る —— GaAs は
    0.83〜0.97 µm に穴がある)、
    ``nd`` / ``vd`` はカタログの公表値(無い材料は ``None``)、``k_data`` は消衰係数の表が
    あるか、``reference`` は最初の一次文献。
    """
    if material_class is not None and material_class not in CLASSES[:-1]:
        raise ValueError("material_class must be one of %s, got %r" % (CLASSES[:-1], material_class))
    rows = []
    for name in MATERIALS:
        r = _RECORDS[name]
        if material_class is not None and r["class"] != material_class:
            continue
        nds = [ds for ds in r["datasets"] if ds["type"] in ("formula", "nk", "n")]
        iv = _intervals(nds)
        rows.append({"name": name, "class": r["class"], "aliases": tuple(r["aliases"]),
                     "range_um": (iv[0][0], iv[-1][1]), "intervals_um": iv,
                     "nd": r["properties"].get("nd"), "vd": r["properties"].get("Vd"),
                     "density_kg_m3": r["properties"].get("density_kg_m3"),
                     "k_data": any(ds["type"] in ("nk", "k") for ds in r["datasets"]),
                     "reference": nds[0].get("reference", "")})
    return rows


def material_record(material="N-BK7") -> dict:
    """材料 1 つのレコード(分類・別名・データ区間ごとの一次文献・カタログ公表値)を返す。

    ``material`` は名前(別名可: BK7 / SILICON / FUSED_SILICA …)か、
    :func:`material_from_sellmeier` 等が返すレコード dict。数表は行数に畳んである
    (``rows`` が整数)。知らない名前は ValueError。
    """
    return _summary(_record(material, "material_record"))


def material_optical_constants(material="SI", wavelength_nm: float = 1000.0) -> dict:
    """1 波長の光学定数 n, k と、そこから決まる吸収係数・複素誘電率・垂直入射反射率を返す。

    ``alpha_per_cm`` = 4πk/λ(Beer–Lambert の吸収係数 [1/cm])、``epsilon`` = (n + ik)²、
    ``reflectance_normal`` = |(m − 1)/(m + 1)|²。``n_source`` / ``k_source`` はどの一次文献の
    区間から取ったか(k の表が無ければ ``k_source`` は ``None`` で k = 0)。
    波長がデータ区間の外なら ValueError(外挿しない)。
    """
    op = "material_optical_constants"
    rec = _record(material, op)
    wl = float(wavelength_nm)
    if not np.isfinite(wl) or wl <= 0.0:
        raise ValueError("%s: wavelength_nm must be finite and > 0, got %r" % (op, wavelength_nm))
    n, k, ns, ks = _nk(rec, wl * 1e-3, op)
    m = complex(float(n[0]), float(k[0]))
    eps = m * m
    return {"material": rec["name"], "wavelength_nm": wl, "n": float(n[0]), "k": float(k[0]),
            "alpha_per_cm": float(4.0 * np.pi * k[0] / (wl * 1e-7)),
            "epsilon_re": float(eps.real), "epsilon_im": float(eps.imag),
            "reflectance_normal": float(abs((m - 1.0) / (m + 1.0)) ** 2),
            "n_source": ns[0], "k_source": ks[0]}


def material_dispersion(material="N-BK7", wl_min_nm: float = 400.0, wl_max_nm: float = 1000.0,
                        n_points: int = 121) -> np.ndarray:
    """屈折率の分散曲線 n(λ) を ``pairs``(λ [nm], n)で返す(等間隔 ``n_points`` 点)。

    区間がデータの外に出れば ValueError(表の外挿はしない)。
    """
    op = "material_dispersion"
    rec = _record(material, op)
    wl = _grid_nm(wl_min_nm, wl_max_nm, n_points, op)
    n, _, _, _ = _nk(rec, wl * 1e-3, op)
    return _pairs(wl, n)


def material_extinction(material="SI", wl_min_nm: float = 400.0, wl_max_nm: float = 1400.0,
                        n_points: int = 101) -> np.ndarray:
    """消衰係数の曲線 k(λ) を ``pairs``(λ [nm], k)で返す。k の表が無い区間は 0。"""
    op = "material_extinction"
    rec = _record(material, op)
    wl = _grid_nm(wl_min_nm, wl_max_nm, n_points, op)
    _, k, _, _ = _nk(rec, wl * 1e-3, op)
    return _pairs(wl, k)


def material_absorption(material="SI", wl_min_nm: float = 400.0, wl_max_nm: float = 1400.0,
                        n_points: int = 101) -> np.ndarray:
    """吸収係数の曲線 α(λ) = 4πk/λ [1/cm] を ``pairs``(λ [nm], α)で返す。

    Si では 1.0 µm で ≈ 64 /cm、1.2 µm で ≈ 0.02 /cm(Green 2008)—— 吸収端(≈ 1.1 µm)を
    跨ぐと 3 桁落ちる。これが NIR 透過検査の波長を決める数字。
    """
    op = "material_absorption"
    rec = _record(material, op)
    wl = _grid_nm(wl_min_nm, wl_max_nm, n_points, op)
    _, k, _, _ = _nk(rec, wl * 1e-3, op)
    return _pairs(wl, 4.0 * np.pi * k / (wl * 1e-7))


def material_transmittance(material="SI", thickness_mm: float = 0.7, wl_min_nm: float = 900.0,
                           wl_max_nm: float = 1400.0, n_points: int = 101,
                           include_fresnel: bool = True, extra_absorption=None) -> np.ndarray:
    """平行平板(厚さ ``thickness_mm``)の透過率 T(λ) を ``pairs``(λ [nm], T)で返す。

    T = (1 − R)² e^{−αt} / (1 − R² e^{−2αt})(両面の多重反射を足した非コヒーレントの式、
    R は垂直入射の |(m − 1)/(m + 1)|²、α = 4πk/λ)。``include_fresnel=False`` で内部透過率
    e^{−αt} だけにする(硝材カタログの「内部透過率」と同じ量)。
    厚さ 0 は T = 1 になるが、負や非有限は ValueError。

    ``extra_absorption``: 材料の表に無い吸収を足す ``pairs``(λ [nm], α [1/cm])。例: ドープした Si の自由キャリア吸収
    ``silicon_free_carrier_absorption(1e19, "n", ...)`` をそのまま渡す。格子の全波長を覆わなければ ValueError
    (外挿しない)、負の α も ValueError。表面の反射 R は材料の n,k のまま(自由キャリアの n の変化は小さいので無視)。
    """
    op = "material_transmittance"
    rec = _record(material, op)
    t = float(thickness_mm)
    if not np.isfinite(t) or t < 0.0:
        raise ValueError("%s: thickness_mm must be finite and >= 0, got %r" % (op, thickness_mm))
    wl = _grid_nm(wl_min_nm, wl_max_nm, n_points, op)
    n, k, _, _ = _nk(rec, wl * 1e-3, op)
    alpha_per_um = 4.0 * np.pi * k / (wl * 1e-3)
    if extra_absorption is not None:
        ea = np.asarray(extra_absorption, dtype=np.float64)
        if ea.ndim != 2 or ea.shape[1] != 2 or ea.shape[0] < 2 or not np.all(np.isfinite(ea)):
            raise ValueError("%s: extra_absorption must be finite pairs (wavelength nm, alpha 1/cm), shape (n, 2)" % op)
        order = np.argsort(ea[:, 0])
        ea = ea[order]
        if wl[0] < ea[0, 0] - 1e-9 or wl[-1] > ea[-1, 0] + 1e-9:
            raise ValueError("%s: extra_absorption covers %.6g-%.6g nm but the grid spans %.6g-%.6g nm "
                             "(not extrapolated)" % (op, ea[0, 0], ea[-1, 0], wl[0], wl[-1]))
        if np.any(ea[:, 1] < 0.0):
            raise ValueError("%s: extra_absorption must be >= 0 (negative alpha = gain)" % op)
        alpha_per_um = alpha_per_um + np.interp(wl, ea[:, 0], ea[:, 1]) * 1e-4      # 1/cm -> 1/µm
    inner = np.exp(-alpha_per_um * t * 1e3)
    if not include_fresnel:
        return _pairs(wl, inner)
    m = n + 1j * k
    R = np.abs((m - 1.0) / (m + 1.0)) ** 2
    T = (1.0 - R) ** 2 * inner / (1.0 - R * R * inner * inner)
    return _pairs(wl, T)


def material_reflectance(material="AG", wl_min_nm: float = 300.0, wl_max_nm: float = 1900.0,
                         n_points: int = 161, angle_deg: float = 0.0,
                         polarization: str = "unpolarized") -> np.ndarray:
    """空気から材料の面への反射率 R(λ) を ``pairs``(λ [nm], R)で返す(Fresnel、複素屈折率)。

    金属(k > 0)も誘電体(k = 0)も同じ式(Born & Wolf §13.2)。``angle_deg`` は入射角
    [0, 90)、``polarization`` は unpolarized / s / p。既定の区間 300〜1900 nm は Johnson & Christy の
    表(0.188〜1.937 µm)に収まる値(表の外は ValueError で、外挿しない)。
    銀は 500 nm で ≈ 0.98、金は 500 nm で ≈ 0.5 から 700 nm で ≈ 0.97 へ立ち上がり、
    アルミは 800 nm 付近に谷(≈ 0.87)がある —— 鏡の材料を選ぶ理由がそのまま出る。
    """
    op = "material_reflectance"
    rec = _record(material, op)
    th = float(angle_deg)
    if not np.isfinite(th) or not (0.0 <= th < 90.0):
        raise ValueError("%s: angle_deg must lie in [0, 90), got %r" % (op, angle_deg))
    wl = _grid_nm(wl_min_nm, wl_max_nm, n_points, op)
    n, k, _, _ = _nk(rec, wl * 1e-3, op)
    R = _fresnel(n + 1j * k, np.cos(np.radians(th)), polarization)
    return _pairs(wl, R)


def abbe_number(material="N-BK7") -> dict:
    """フラウンホーファー線の屈折率と Abbe 数(d 線系・e 線系)、部分分散 P_g,F を返す。

    V_d = (n_d − 1)/(n_F − n_C)、V_e = (n_e − 1)/(n_F' − n_C')、P_g,F = (n_g − n_F)/(n_F − n_C)
    (g 線 435.8 nm が分散式の区間の外なら ``ng`` / ``PgF`` は ``None`` —— プラスチックの式は 436.8 nm から)。
    ``nd_catalog`` / ``vd_catalog`` はカタログの公表値(無ければ ``None``)で、分散式から
    計算した ``nd`` / ``vd`` との差がテストの門(硝材 46 種で n_d 1e-4・V_d 0.3 以内)。
    金属のように d 線で k が大きい材料は Abbe 数に意味が無いので ValueError。
    """
    op = "abbe_number"
    rec = _record(material, op)
    lam = np.array([WL_FP, WL_F, WL_E, WL_D, WL_CP, WL_C])
    n, k, _, _ = _nk(rec, lam, op)
    if np.any(k > 1e-2):
        raise ValueError("%s: %s absorbs in the visible (k > 0.01); an Abbe number is meaningless"
                         % (op, rec["name"]))
    nfp, nf, ne, nd, ncp, nc = (float(v) for v in n)
    try:                                   # g 線(435.8 nm)は分散式の下端の外のことがある(プラスチック) → P_g,F だけ None
        ng = float(_nk(rec, np.array([WL_G]), op)[0][0])
        pgf = (ng - nf) / (nf - nc)
    except ValueError:
        ng, pgf = None, None
    p = rec.get("properties", {})
    return {"material": rec["name"], "nd": nd, "nF": nf, "nC": nc, "vd": (nd - 1.0) / (nf - nc),
            "ne": ne, "nFp": nfp, "nCp": ncp, "ve": (ne - 1.0) / (nfp - ncp),
            "ng": ng, "PgF": pgf,
            "nd_catalog": p.get("nd"), "vd_catalog": p.get("Vd"), "PgF_catalog_delta": p.get("dPgF")}


def glass_map(material_class: str = None) -> list:
    """Abbe 図(V_d 対 n_d)の点の列: 可視で透明な材料ごとに name / class / nd / vd / PgF。

    金属など d 線で吸収する材料、F〜C 線をデータが覆わない材料は載せない。
    ``material_class`` で分類に絞る(None は全部)。返り値は dict の列(``table``)。
    """
    if material_class is not None and material_class not in CLASSES[:-1]:
        raise ValueError("material_class must be one of %s, got %r" % (CLASSES[:-1], material_class))
    rows = []
    for name in MATERIALS:
        r = _RECORDS[name]
        if material_class is not None and r["class"] != material_class:
            continue
        try:
            a = abbe_number(name)
        except ValueError:
            continue
        rows.append({"name": name, "class": r["class"], "nd": a["nd"], "vd": a["vd"], "PgF": a["PgF"]})
    return rows


def thermo_optic_coefficient(material="N-BK7", wavelength_nm: float = 546.07,
                             temperature_c: float = 30.0) -> dict:
    """硝材の dn/dT(絶対、真空中)と基準温度からの屈折率変化 Δn をカタログの式 A で返す。

    dn/dT = (n² − 1)/(2n) · [D₀ + 2D₁ΔT + 3D₂ΔT² + (E₀ + 2E₁ΔT)/(λ² − λ_tk²)]、
    Δn = (n² − 1)/(2n) · [D₀ΔT + D₁ΔT² + D₂ΔT³ + (E₀ΔT + E₁ΔT²)/(λ² − λ_tk²)]
    (ΔT = T − T_ref、λ は µm、係数 D₀…λ_tk はカタログの thermal_dispersion、T_ref は
    カタログの基準温度 20 ℃ / 25 ℃)。係数の無い材料は ValueError(硝材 46 種にはある)。
    ``delta_n`` は温度で焦点がどれだけ動くか(dn/dT × ΔT × 厚さ)の入口。
    """
    op = "thermo_optic_coefficient"
    rec = _record(material, op)
    coef = rec.get("properties", {}).get("dn_dt_formula_a")
    if not coef:
        raise ValueError("%s: %s has no thermal-dispersion coefficients in its catalogue data" % (op, rec["name"]))
    wl = float(wavelength_nm)
    T = float(temperature_c)
    if not np.isfinite(wl) or wl <= 0.0 or not np.isfinite(T):
        raise ValueError("%s: wavelength_nm must be > 0 and temperature_c finite" % op)
    d0, d1, d2, e0, e1, ltk = (float(v) for v in coef)
    tref = rec.get("properties", {}).get("reference_temperature_c")
    if tref is None:
        # refractiveindex.info はカタログの基準温度(20 ℃ / 25 ℃)を整数 K(293 / 298)で持つので、
        # ℃ に戻して整数に丸める(19.85 ℃ のまま使うと基準温度で Δn が 0 にならない)。
        tref_k = next((ds.get("temperature_k") for ds in rec["datasets"] if ds.get("temperature_k")), 293.0)
        tref = float(round(tref_k - 273.15))
    dt = T - tref
    n, _, _, _ = _nk(rec, wl * 1e-3, op)
    n = float(n[0])
    lam = wl * 1e-3
    g = (n * n - 1.0) / (2.0 * n)
    dndt = g * (d0 + 2.0 * d1 * dt + 3.0 * d2 * dt * dt + (e0 + 2.0 * e1 * dt) / (lam * lam - ltk * ltk))
    dn = g * (d0 * dt + d1 * dt * dt + d2 * dt ** 3 + (e0 * dt + e1 * dt * dt) / (lam * lam - ltk * ltk))
    return {"material": rec["name"], "wavelength_nm": wl, "temperature_c": T,
            "reference_temperature_c": tref, "delta_t_k": dt, "n_reference": n,
            "dn_dt_per_k": dndt, "delta_n": dn, "n_at_temperature": n + dn}


def plate_focus_shift(material="SI", thickness_mm: float = 0.775, wavelength_nm: float = 1100.0,
                      numerical_aperture: float = 0.1) -> dict:
    """平行平板(ウェハ・窓・カバーガラス)を通して見たときの焦点ずれと球面収差を閉じた式で返す。

    近軸の焦点ずれ Δ₀ = t(1 − 1/n)、開口の縁の光線(sinθ = NA)の焦点ずれ
    Δ(θ) = t(1 − cosθ/√(n² − sin²θ))、縦球面収差 = Δ(θ) − Δ₀ ≈ t sin²θ (1 − 1/n²)/(2n)(平板が
    足す収差、NA の 2 乗。n = 3.5 の Si ウェハ 775 µm は近軸で ≈ 0.56 mm ずれ、NA 0.1 で ≈ 1.0 µm、
    NA 0.3 で ≈ 9 µm の縦収差)。
    ``optical_thickness_mm`` = n t。NA は (0, 1) でなければ ValueError。
    """
    op = "plate_focus_shift"
    rec = _record(material, op)
    t = float(thickness_mm)
    na = float(numerical_aperture)
    wl = float(wavelength_nm)
    if not np.isfinite(t) or t < 0.0:
        raise ValueError("%s: thickness_mm must be finite and >= 0" % op)
    if not np.isfinite(na) or not (0.0 < na < 1.0):
        raise ValueError("%s: numerical_aperture must lie in (0, 1), got %r" % (op, numerical_aperture))
    if not np.isfinite(wl) or wl <= 0.0:
        raise ValueError("%s: wavelength_nm must be > 0" % op)
    n, k, _, _ = _nk(rec, wl * 1e-3, op)
    n, k = float(n[0]), float(k[0])
    par = t * (1.0 - 1.0 / n)
    mar = t * (1.0 - np.sqrt(1.0 - na * na) / np.sqrt(n * n - na * na))
    return {"material": rec["name"], "wavelength_nm": wl, "n": n, "k": k, "thickness_mm": t,
            "numerical_aperture": na, "paraxial_shift_mm": par, "marginal_shift_mm": float(mar),
            "spherical_aberration_mm": float(mar - par), "optical_thickness_mm": n * t}


def silicon_free_carrier_absorption(doping_cm3: float = 1e17, carrier: str = "n",
                                    wl_min_nm: float = 1000.0, wl_max_nm: float = 2000.0,
                                    n_points: int = 101) -> np.ndarray:
    """ドープした Si の自由キャリア吸収 α_fc(λ) [1/cm] を ``pairs``(λ [nm], α)で返す。

    α_fc = c·N·λ²(λ は µm、N はキャリア密度 [cm⁻³]、c = 1.0e-18 (n 型) / 2.7e-18 (p 型)、
    Schroder, Thomas & Swartz, IEEE Trans. Electron Devices 25, 254 (1978))。
    吸収端の下(λ > 1.1 µm)で基板を透過させるとき、高濃度基板(10¹⁹ cm⁻³)は 1.3 µm で
    ≈ 17 /cm —— 775 µm のウェハで e^{−1.3} まで暗くなる。
    ``carrier`` は "n" / "p"、N < 0 は ValueError。
    """
    op = "silicon_free_carrier_absorption"
    N = float(doping_cm3)
    if not np.isfinite(N) or N < 0.0:
        raise ValueError("%s: doping_cm3 must be finite and >= 0, got %r" % (op, doping_cm3))
    if carrier not in ("n", "p"):
        raise ValueError("%s: carrier must be 'n' or 'p', got %r" % (op, carrier))
    c = 1.0e-18 if carrier == "n" else 2.7e-18
    wl = _grid_nm(wl_min_nm, wl_max_nm, n_points, op)
    lam = wl * 1e-3
    return _pairs(wl, c * N * lam * lam)


def material_from_sellmeier(name: str = "custom", b=(1.03961212, 0.231792344, 1.01046945),
                            c=(0.00600069867, 0.0200179144, 103.560653), range_um=(0.3, 2.5),
                            material_class: str = "glass", reference: str = "") -> dict:
    """Sellmeier 係数(n² − 1 = Σ Bᵢ λ²/(λ² − Cᵢ)、λ は µm、Cᵢ は µm²)から材料レコードを作る。

    既定値は BK7 相当(別名 ``"BK7"``)の公表係数(自分の硝材を足すときの雛形)。返り値は他の materials op に
    ``material`` としてそのまま渡せる。B と C の長さが違う・範囲が逆・係数が非有限なら ValueError。
    ``reference`` に出典を書いておくと ``material_record`` に残る。
    """
    op = "material_from_sellmeier"
    B = np.asarray(b, dtype=np.float64).ravel()
    C = np.asarray(c, dtype=np.float64).ravel()
    if B.size == 0 or B.size != C.size or not np.all(np.isfinite(B)) or not np.all(np.isfinite(C)):
        raise ValueError("%s: b and c must be equal-length finite sequences, got %d and %d" % (op, B.size, C.size))
    lo, hi = (float(v) for v in range_um)
    if not (0.0 < lo < hi):
        raise ValueError("%s: range_um must satisfy 0 < lo < hi, got %r" % (op, range_um))
    if material_class not in CLASSES:
        raise ValueError("%s: material_class must be one of %s" % (op, CLASSES))
    coef = [0.0]
    for bi, ci in zip(B, C):
        coef += [float(bi), float(ci)]
    rec = {"name": _key(name) if name else "CUSTOM", "class": material_class, "aliases": (),
           "datasets": [{"type": "formula", "formula": 2, "range_um": (lo, hi), "coefficients": tuple(coef),
                         "reference": str(reference), "page": "user"}],
           "properties": {}}
    _nk(rec, np.array([lo, 0.5 * (lo + hi), hi]), op)      # 区間の端と中央で物理的な n か確かめる
    return rec


#: :func:`material_from_curves` の既定の曲線(N-BK7 の分散式を 4 点で写した雛形)。
N_CURVE_EXAMPLE = ((400.0, 1.530849), (550.0, 1.518522), (700.0, 1.513064), (1000.0, 1.507502))


def material_from_curves(n_curve=N_CURVE_EXAMPLE, k_curve=None, name: str = "custom",
                         material_class: str = "custom", reference: str = "") -> dict:
    """測った n(λ)(と k(λ))の ``pairs``(λ [nm], 値)から材料レコードを作る。

    ``n_curve`` は (K, 2) で K ≥ 2、λ > 0、n > 0(既定は BK7 相当を 4 点で写した雛形
    :data:`N_CURVE_EXAMPLE`)。``k_curve`` は省略可(省略は k = 0)で
    k ≥ 0。空の入力(``n_curve`` が 0 要素)は ValueError。同じ λ の重複や非有限も ValueError。
    返り値は他の materials op に ``material`` として渡せる(区間は曲線の端まで、外挿しない)。
    """
    op = "material_from_curves"
    nc = np.asarray(n_curve, dtype=np.float64)
    if nc.size == 0:
        raise ValueError("%s: n_curve is empty — pass at least two (wavelength_nm, n) rows" % op)
    if nc.ndim != 2 or nc.shape[1] != 2 or nc.shape[0] < 2:
        raise ValueError("%s: n_curve must be (K, 2) with K >= 2, got shape %s" % (op, nc.shape))
    if not np.all(np.isfinite(nc)) or np.any(nc[:, 0] <= 0.0) or np.any(nc[:, 1] <= 0.0):
        raise ValueError("%s: n_curve needs finite rows with wavelength_nm > 0 and n > 0" % op)
    if np.unique(nc[:, 0]).size != nc.shape[0]:
        raise ValueError("%s: n_curve has duplicate wavelengths" % op)
    if material_class not in CLASSES:
        raise ValueError("%s: material_class must be one of %s" % (op, CLASSES))
    order = np.argsort(nc[:, 0])
    n_rows = [(float(w) * 1e-3, float(v)) for w, v in nc[order]]
    datasets = [{"type": "n", "range_um": (n_rows[0][0], n_rows[-1][0]), "rows": n_rows,
                 "reference": str(reference), "page": "user"}]
    if k_curve is not None:
        kc = np.asarray(k_curve, dtype=np.float64)
        if kc.ndim != 2 or kc.shape[1] != 2 or kc.shape[0] < 2:
            raise ValueError("%s: k_curve must be (K, 2) with K >= 2, got shape %s" % (op, kc.shape))
        if not np.all(np.isfinite(kc)) or np.any(kc[:, 0] <= 0.0) or np.any(kc[:, 1] < 0.0):
            raise ValueError("%s: k_curve needs finite rows with wavelength_nm > 0 and k >= 0" % op)
        order = np.argsort(kc[:, 0])
        k_rows = [(float(w) * 1e-3, float(v)) for w, v in kc[order]]
        datasets.append({"type": "k", "range_um": (k_rows[0][0], k_rows[-1][0]), "rows": k_rows,
                         "reference": str(reference), "page": "user"})
    return {"name": _key(name) if name else "CUSTOM", "class": material_class, "aliases": (),
            "datasets": datasets, "properties": {}}


# --------------------------------------------------------------------------- #
# 硝材カタログ(.agf)の取り込み                                                  #
# --------------------------------------------------------------------------- #
#: .agf の雛形(2 種)。係数は refractiveindex.info(CC0)に載る公表値 —— N-BK7 は Sellmeier 1
#: (式 2)、BSC7 は Schott 多項式(式 1)。テストは読んだ結果が同梱レコードと一致することを門にする。
AGF_EXAMPLE = """CC Example glass catalogue in Zemax .agf form (coefficients from the refractiveindex.info database, CC0)
NM N-BK7 2 517642 1.5168 64.17 0 1 0
ED 7.1 8.3 2.51 -0.0009 0
CD 1.03961212 0.00600069867 0.231792344 0.0200179144 1.01046945 103.560653 0 0 0 0
TD 1.86E-06 1.31E-08 -1.37E-11 4.34E-07 6.27E-10 0.17 20
LD 0.3 2.5
IT 0.4 0.997 10
IT 1.06 0.999 10
NM BSC7 1 517642 1.5168 64.2 0 1 0
ED 7.6 8.6 2.52 0.0016 0
CD 2.2702566 -0.0091988101 0.011609706 -7.6123911E-05 2.8558727E-05 -1.2566486E-06 0 0 0 0
TD 3.25479E-06 0 0 0 0 0 20
LD 0.36501 1.01398
"""

_AGF_POLY = {1: (2, -2, -4, -6, -8), 10: (2, -2, -4, -6, -8, -10, -12),
             12: (2, -2, -4, -6, -8, 4, 6), 13: (2, 4, -2, -4, -6, -8, -10, -12)}


def _agf_formula(code: int, cd, name: str):
    """Zemax の分散式番号と CD 係数を refractiveindex.info の式に写す。"""
    c = [float(v) for v in cd]
    if code in _AGF_POLY:
        exps = _AGF_POLY[code]
        coef = [c[0]]
        for a, e in zip(c[1:1 + len(exps)], exps):
            coef += [a, float(e)]
        return 3, tuple(coef)
    if code in (2, 6, 11):
        pairs = {2: 3, 6: 4, 11: 5}[code]
        return 2, tuple([0.0] + c[:2 * pairs])
    if code == 3:
        return 7, tuple(c[:6])
    if code == 4:
        a, b1, l1, b2, l2 = c[:5]
        return 4, (1.0 + a, b1, 2.0, l1, 2.0, b2, 0.0, l2, 2.0)
    if code == 5:
        return 5, (c[0], c[1], -1.0, c[2], -3.5)
    if code == 7:
        a, b, cc, d = c[:4]
        return 4, (a, b, 0.0, cc, 1.0, 0.0, 0.0, 0.0, 1.0, -d, 2.0)
    if code == 8:
        a, b, cc, d = c[:4]
        return 4, (a, b, 2.0, cc, 1.0, 0.0, 0.0, 0.0, 1.0, -d, 2.0)
    if code == 9:
        a, b, cc, d, e = c[:5]
        return 4, (a, b, 2.0, cc, 1.0, d, 2.0, e, 1.0)
    raise ValueError("read_glass_catalog_agf: glass %s uses dispersion formula %d, which is not one of the "
                     "Zemax formulas 1-13 this reader knows" % (name, code))


def _agf_text(source) -> str:
    raw = io.open(source, "rb").read()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def read_glass_catalog_agf(source=None) -> list:
    """硝材カタログ(光学設計ソフトの .agf 形式)を読んで材料レコードの列(``table``)にする。

    ``source`` は .agf ファイルのパス、.agf を並べたディレクトリ(全部読む)、または
    ``None``(同梱の雛形 :data:`AGF_EXAMPLE` を読む —— 自分のカタログを置く場所は
    ``os.environ["FULLSEYE_GLASS_DIR"]`` を渡す)。メーカーのカタログ本体は同梱しない。

    読むのは NM(名前・式番号・n_d・V_d)、CD(係数)、TD(dn/dT の式 A の係数と基準温度)、
    ED(熱膨張 ×1e-6 /K、密度 g/cm³、ΔP_g,F)、LD(波長範囲 µm)、IT(内部透過率 →
    k = −ln T · λ/(4π t))。知らない式番号・係数が足りない・範囲が無い硝材は ValueError
    (黙って別の式にしない)。返ったレコードは他の materials op に ``material`` として渡せる。
    """
    op = "read_glass_catalog_agf"
    if source is None:
        texts = [("AGF_EXAMPLE", AGF_EXAMPLE)]
    elif isinstance(source, str) and os.path.isdir(source):
        files = sorted(f for f in os.listdir(source) if f.lower().endswith(".agf"))
        if not files:
            raise ValueError("%s: no .agf file in %s" % (op, source))
        texts = [(f, _agf_text(os.path.join(source, f))) for f in files]
    elif isinstance(source, str) and os.path.isfile(source):
        texts = [(os.path.basename(source), _agf_text(source))]
    else:
        raise ValueError("%s: source must be None, an .agf file or a directory, got %r" % (op, source))
    out = []
    for label, text in texts:
        cur = None
        for line in text.splitlines():
            parts = line.split()
            if not parts:
                continue
            tag = parts[0].upper()
            if tag == "NM":
                if cur is not None:
                    out.append(_agf_finish(cur, label, op))
                if len(parts) < 3:
                    raise ValueError("%s: %s: NM line needs a name and a formula number: %r" % (op, label, line))
                cur = {"name": parts[1], "code": int(float(parts[2])), "cd": None, "td": None, "ed": None,
                       "ld": None, "it": [], "nd": None, "vd": None}
                if len(parts) >= 6:
                    cur["nd"], cur["vd"] = float(parts[4]), float(parts[5])
            elif cur is None:
                continue
            elif tag == "CD":
                cur["cd"] = [float(v) for v in parts[1:]]
            elif tag == "TD":
                cur["td"] = [float(v) for v in parts[1:]]
            elif tag == "ED":
                cur["ed"] = [float(v) for v in parts[1:]]
            elif tag == "LD":
                cur["ld"] = [float(v) for v in parts[1:3]]
            elif tag == "IT" and len(parts) >= 4:
                cur["it"].append((float(parts[1]), float(parts[2]), float(parts[3])))
        if cur is not None:
            out.append(_agf_finish(cur, label, op))
    if not out:
        raise ValueError("%s: no NM line (no glass) found" % op)
    return out


def _agf_finish(g: dict, label: str, op: str) -> dict:
    if g["cd"] is None:
        raise ValueError("%s: %s: glass %s has no CD (coefficient) line" % (op, label, g["name"]))
    if g["ld"] is None or not (0.0 < g["ld"][0] < g["ld"][1]):
        raise ValueError("%s: %s: glass %s has no usable LD (wavelength range) line" % (op, label, g["name"]))
    k, coef = _agf_formula(g["code"], g["cd"], g["name"])
    ds = {"type": "formula", "formula": k, "range_um": (g["ld"][0], g["ld"][1]), "coefficients": coef,
          "reference": "user catalogue %s" % label, "page": "agf:%s" % label}
    props = {}
    if g["nd"] is not None:
        props["nd"], props["Vd"] = g["nd"], g["vd"]
    if g["td"] and len(g["td"]) >= 6:
        props["dn_dt_formula_a"] = tuple(g["td"][:6])
        if len(g["td"]) >= 7:
            props["reference_temperature_c"] = g["td"][6]
            ds["temperature_k"] = g["td"][6] + 273.15
    if g["ed"]:
        if len(g["ed"]) >= 1:
            props["thermal_expansion_per_k"] = g["ed"][0] * 1e-6
        if len(g["ed"]) >= 3 and g["ed"][2] > 0:
            props["density_kg_m3"] = g["ed"][2] * 1e3
        if len(g["ed"]) >= 4:
            props["dPgF"] = g["ed"][3]
    datasets = [ds]
    rows = []
    for lam, T, t_mm in g["it"]:
        if T <= 0.0 or t_mm <= 0.0:
            continue
        rows.append((lam, max(0.0, -np.log(T)) * lam / (4.0 * np.pi * t_mm * 1e3)))
    if len(rows) >= 2:
        rows.sort()
        datasets.append({"type": "k", "range_um": (rows[0][0], rows[-1][0]), "rows": rows,
                         "reference": "internal transmittance (IT lines) of %s" % label, "page": "agf:%s" % label})
    rec = {"name": _key(g["name"]), "class": "glass", "aliases": (), "datasets": datasets, "properties": props}
    _nk(rec, np.array([g["ld"][0], g["ld"][1]]), op)
    return rec
