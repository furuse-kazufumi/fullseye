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
    "NIR_BAND_MODELS", "material_nir_absorption", "carbon_black_absorption", "nir_model_info",
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


# --------------------------------------------------------------------------- #
# X 線の列(2026-10-15): 質量減衰係数 μ/ρ(E)                                    #
# --------------------------------------------------------------------------- #
# 光学の列(n, k)と同じ名前で X 線の μ/ρ を引く。数値は NIST の表(Hubbell & Seltzer、SRD 126)の
# 部分集合 ``materials_xray_data.py``(``tools/gen_xray_tables.py`` の生成物)。
#
# 引き方は 3 通りで、上から先に当たったものを使う:
#   1. NIST が化合物として表にした材料(WATER / PMMA / BONE_CORTICAL_ICRU44 / PVC / CSI …)は表そのもの。
#   2. 元素(CU / AL / W / PB …、記号でも名前でも)は元素の表。
#   3. 組成(化学式か質量分率)が分かる材料は混合則 μ/ρ = Σ wᵢ (μ/ρ)ᵢ。光学の表の結晶・膜・半導体
#      (SAPPHIRE = Al2O3、SI3N4 …)と、食品の異物の代表(ソーダ石灰ガラス・天然ゴム・ステンレス・石 …)。
# 組成の分からない材料(硝材の N-BK7 など、メーカーが組成を公表しない)は ValueError で拒否する。
# 混合則は光電効果・コンプトン・干渉性散乱の断面積が原子ごとに足し合わさるという近似で、NIST の化合物の
# 表もこの規則で計算されている(化学結合・結晶の効果は吸収端の近くの数 % を除き無視できる)。
import materials_xray_data as _mx  # noqa: E402

# ★X 線の列の op 4 本の台帳は ``opstomography`` の ``spectral_xray``(dualxray と同じ族)。``materials.__all__`` は
#   ``opsoptics`` の ``matprop`` 台帳と 1 対 1(tests/test_materials.py)なので、ここには足さない —— 足すと
#   matprop の登録と食い違い、統合で他の作業(電子線の列)と同じ行を取り合う。

_XE = {e["Z"]: e for e in _mx.XRAY_ELEMENTS}
_XE_SYMBOL = {e["symbol"].upper(): e["Z"] for e in _mx.XRAY_ELEMENTS}
_XE_NAME = {e["name"].split(",")[0].strip().upper(): e["Z"] for e in _mx.XRAY_ELEMENTS}
_XE_NAME["ALUMINIUM"] = 13
_XC = {c["key"]: c for c in _mx.XRAY_COMPOUNDS}

#: X 線の列を組成から作る材料。**レコードの形は電子線の表(``ELECTRON_SOLID``、仮想 SEM)と同じ**
#: ``{"formula": {元素: 原子数}, "density_g_cm3": …}``(混合物は ``"mass_fractions": {化学式: 質量分率}``)。
#: 統合で 1 つの表に寄せられるようにしてある —— 同じ名前が ``ELECTRON_SOLID`` にあればそちらの組成と
#: 密度を使い(:func:`_xray_record`)、ここの値と食い違えば ``tests/test_dualxray.py`` が赤になる。
#: 密度は公称値(結晶の理論密度・ハンドブックの代表値)で、実物の気孔・充填材で変わる ——
#: 正確な値が要るときは ``density_g_cm3=`` で上書きする。
XRAY_SOLID = {
    # 光学の表にある材料(結晶・膜・半導体・樹脂)
    "SILICA": {"formula": {"Si": 1, "O": 2}, "density_g_cm3": 2.20},
    "QUARTZ": {"formula": {"Si": 1, "O": 2}, "density_g_cm3": 2.65},
    "SAPPHIRE": {"formula": {"Al": 2, "O": 3}, "density_g_cm3": 3.98},
    "CAF2": {"formula": {"Ca": 1, "F": 2}, "density_g_cm3": 3.18},
    "BAF2": {"formula": {"Ba": 1, "F": 2}, "density_g_cm3": 4.89},
    "LIF": {"formula": {"Li": 1, "F": 1}, "density_g_cm3": 2.635},
    "KBR": {"formula": {"K": 1, "Br": 1}, "density_g_cm3": 2.75},
    "MGF2": {"formula": {"Mg": 1, "F": 2}, "density_g_cm3": 3.15},
    "ZNS": {"formula": {"Zn": 1, "S": 1}, "density_g_cm3": 4.09},
    "ZNSE": {"formula": {"Zn": 1, "Se": 1}, "density_g_cm3": 5.27},
    "YAG": {"formula": {"Y": 3, "Al": 5, "O": 12}, "density_g_cm3": 4.56},
    "GAN": {"formula": {"Ga": 1, "N": 1}, "density_g_cm3": 6.15},
    "INP": {"formula": {"In": 1, "P": 1}, "density_g_cm3": 4.81},
    "SIC": {"formula": {"Si": 1, "C": 1}, "density_g_cm3": 3.21},
    "SI3N4": {"formula": {"Si": 3, "N": 4}, "density_g_cm3": 3.17},
    "TIO2": {"formula": {"Ti": 1, "O": 2}, "density_g_cm3": 4.23},
    "TA2O5": {"formula": {"Ta": 2, "O": 5}, "density_g_cm3": 8.2},
    "HFO2": {"formula": {"Hf": 1, "O": 2}, "density_g_cm3": 9.68},
    "POLYCARBONATE": {"formula": {"C": 16, "H": 14, "O": 3}, "density_g_cm3": 1.20},
    # 食品・電池・リサイクルの検査で出てくる材料(NIST の化合物の表に無いもの)
    "SODA_LIME_GLASS": {"mass_fractions": {"SiO2": 0.726, "Na2O": 0.139, "CaO": 0.084, "MgO": 0.039,
                                           "Al2O3": 0.012}, "density_g_cm3": 2.52},
    "NATURAL_RUBBER": {"formula": {"C": 5, "H": 8}, "density_g_cm3": 0.92},
    "POLYPROPYLENE": {"formula": {"C": 3, "H": 6}, "density_g_cm3": 0.90},
    "NYLON6": {"formula": {"C": 6, "H": 11, "N": 1, "O": 1}, "density_g_cm3": 1.14},
    "CALCITE": {"formula": {"Ca": 1, "C": 1, "O": 3}, "density_g_cm3": 2.71},
    "HYDROXYAPATITE": {"formula": {"Ca": 10, "P": 6, "O": 26, "H": 2}, "density_g_cm3": 3.16},
    "STAINLESS_STEEL_304": {"mass_fractions": {"Fe": 0.70, "Cr": 0.19, "Ni": 0.09, "Mn": 0.02}, "density_g_cm3": 8.0},
    "SOLDER_SAC305": {"mass_fractions": {"Sn": 0.965, "Ag": 0.03, "Cu": 0.005}, "density_g_cm3": 7.4},
}
#: 旧名(2026-10-15 の初版の名前)。中身は XRAY_SOLID と同じものを指す。
XRAY_FORMULAS = XRAY_SOLID


def _xray_record(key: str):
    """名前 → 組成のレコード。電子線の表(``ELECTRON_SOLID``、別の作業で入る)にあればそちらを優先する。"""
    es = globals().get("ELECTRON_SOLID")
    if isinstance(es, dict) and key in es and "formula" in es[key]:
        return es[key]
    return XRAY_SOLID.get(key)


def _record_composition(rec: dict, op: str) -> tuple:
    if "mass_fractions" in rec:
        return _composition(dict(rec["mass_fractions"]), op)
    formula = "".join("%s%s" % (el, ("%g" % n) if n != 1 else "") for el, n in rec["formula"].items())
    return _composition(formula, op)


_XRAY_ALIASES = {"H2O": "WATER", "PE": "POLYETHYLENE", "PS": "POLYSTYRENE", "PC": "POLYCARBONATE",
                 "TEFLON": "PTFE", "MYLAR": "PET", "BONE": "BONE_CORTICAL_ICRU44", "MUSCLE": "MUSCLE_ICRU44",
                 "MEAT": "MUSCLE_ICRU44", "FAT": "ADIPOSE_ICRU44", "ADIPOSE": "ADIPOSE_ICRU44",
                 "SOFT_TISSUE": "SOFT_TISSUE_ICRU44", "PYREX": "BOROSILICATE_GLASS", "GLASS": "SODA_LIME_GLASS",
                 "RUBBER": "NATURAL_RUBBER", "PP": "POLYPROPYLENE", "STONE": "CALCITE", "STEEL": "STAINLESS_STEEL_304",
                 "SOLDER": "SOLDER_SAC305", "GOS": "GOS", "CSI": "CSI"}
XRAY_E_MIN_KEV = min(r[0] for r in _mx.XRAY_ELEMENTS[0]["rows"])
XRAY_E_MAX_KEV = max(r[0] for r in _mx.XRAY_ELEMENTS[0]["rows"])
_FORMULA_TOKEN = re.compile(r"([A-Z][a-z]?)(\d*\.?\d*)")


def _atomic_mass(z: int) -> float:
    """A = Z / (Z/A)。NIST の表 1 の Z/A から(別の原子量表を持たない)。"""
    return z / _XE[z]["z_over_a"]


def _formula_fractions(formula: str, op: str) -> dict:
    """化学式 → {Z: 質量分率}。表に無い元素・読めない式は ValueError。"""
    s = str(formula).strip()
    if not s or _FORMULA_TOKEN.sub("", s) != "":
        raise ValueError("%s: cannot read chemical formula %r (use element symbols and counts, e.g. 'Al2O3')" % (op, formula))
    mass = {}
    for sym, cnt in _FORMULA_TOKEN.findall(s):
        z = _XE_SYMBOL.get(sym.upper())
        if z is None:
            raise ValueError("%s: element %r of %r has no X-ray table (bundled: %s)"
                             % (op, sym, formula, " ".join(sorted(e["symbol"] for e in _mx.XRAY_ELEMENTS))))
        n = float(cnt) if cnt else 1.0
        mass[z] = mass.get(z, 0.0) + n * _atomic_mass(z)
    tot = sum(mass.values())
    return {z: m / tot for z, m in mass.items()}


def _composition(spec, op: str) -> tuple:
    """化学式 / {化学式または記号: 質量分率} / ((Z, w), …) → ((Z, w), …)(w の和 = 1)。"""
    if isinstance(spec, str):
        fr = _formula_fractions(spec, op)
    elif isinstance(spec, dict):
        tot = 0.0
        fr = {}
        for part, w in spec.items():
            w = float(w)
            if not np.isfinite(w) or w < 0.0:
                raise ValueError("%s: mass fraction of %r must be finite and >= 0, got %r" % (op, part, w))
            tot += w
            for z, f in _formula_fractions(part, op).items():
                fr[z] = fr.get(z, 0.0) + w * f
        if not (0.98 <= tot <= 1.02):
            raise ValueError("%s: mass fractions sum to %.4f (must be 1 within 2 %%)" % (op, tot))
        fr = {z: f / tot for z, f in fr.items()}
    else:
        try:
            pairs = [(int(z), float(w)) for z, w in spec]
        except (TypeError, ValueError):
            raise ValueError("%s: composition must be a formula, a {formula: fraction} dict or (Z, fraction) pairs" % op)
        tot = sum(w for _, w in pairs)
        if not (0.98 <= tot <= 1.02) or any(w < 0 for _, w in pairs):
            raise ValueError("%s: (Z, fraction) pairs must be >= 0 and sum to 1, got %.4f" % (op, tot))
        fr = {}
        for z, w in pairs:
            if z not in _XE:
                raise ValueError("%s: Z=%d has no bundled X-ray table" % (op, z))
            fr[z] = fr.get(z, 0.0) + w / tot
    return tuple(sorted(fr.items()))


def _xray_source(material, op: str, density_g_cm3=None) -> dict:
    """名前 / 化学式 / {"composition": …, "density_g_cm3": …} → X 線の列(表か組成)と密度。"""
    if isinstance(material, dict):
        if "composition" not in material:
            raise ValueError("%s: a custom X-ray material needs 'composition' (formula, {part: fraction} or "
                             "(Z, fraction) pairs) and 'density_g_cm3'" % op)
        rho = material.get("density_g_cm3", density_g_cm3)
        src = {"name": str(material.get("name", "custom")), "kind": "mixture",
               "composition": _composition(material["composition"], op), "density_g_cm3": rho,
               "reference": "custom composition; elemental tables NIST SRD 126"}
    else:
        if not isinstance(material, str):
            raise ValueError("%s: material must be a name, a chemical formula or a dict, got %r" % (op, type(material).__name__))
        key = _key(material)
        key = _XRAY_ALIASES.get(key, key)
        key = _ALIASES.get(key, key) if key not in _XC and _xray_record(key) is None else key
        if key in _XC:
            c = _XC[key]
            src = {"name": key, "kind": "table", "rows": c["rows"], "composition": c["composition"],
                   "density_g_cm3": c["density_g_cm3"],
                   "reference": "NIST SRD 126 %s (%s)" % (c["page"], c["nist_name"])}
        elif key in _XE_SYMBOL or key in _XE_NAME:
            z = _XE_SYMBOL.get(key, _XE_NAME.get(key))
            e = _XE[z]
            src = {"name": e["symbol"].upper(), "kind": "table", "rows": e["rows"], "composition": ((z, 1.0),),
                   "density_g_cm3": e["density_g_cm3"], "reference": "NIST SRD 126 %s (%s)" % (e["page"], e["name"])}
        elif _xray_record(key) is not None:
            rec = _xray_record(key)
            src = {"name": key, "kind": "mixture", "composition": _record_composition(rec, op),
                   "density_g_cm3": rec["density_g_cm3"],
                   "reference": "mixture rule over NIST SRD 126 elemental tables; nominal density"}
        elif _FORMULA_TOKEN.sub("", str(material).strip()) == "" and re.search(r"[A-Z]", str(material)):
            src = {"name": str(material).strip(), "kind": "mixture", "composition": _composition(material, op),
                   "density_g_cm3": density_g_cm3, "reference": "chemical formula; mixture rule over NIST SRD 126"}
        elif key in _RECORDS:
            raise ValueError("%s: %r is in the optical table but its elemental composition is not public (a "
                             "manufacturer glass) - pass {'composition': ..., 'density_g_cm3': ...}" % (op, material))
        else:
            raise ValueError("%s: unknown X-ray material %r (see material_xray_table(); or pass a chemical "
                             "formula / {'composition': ..., 'density_g_cm3': ...})" % (op, material))
    if density_g_cm3 is not None:
        src["density_g_cm3"] = density_g_cm3
    if src["density_g_cm3"] is not None:
        rho = float(src["density_g_cm3"])
        if not np.isfinite(rho) or rho <= 0.0:
            raise ValueError("%s: density_g_cm3 must be finite and > 0, got %r" % (op, src["density_g_cm3"]))
        src["density_g_cm3"] = rho
    return src


def _xray_interp(rows, energy_kev: np.ndarray, col: int) -> np.ndarray:
    """表の log–log 補間(吸収端は区間の境目、端ちょうどは端の上の値)。"""
    e = np.array([r[0] for r in rows], dtype=np.float64)
    v = np.array([r[col] for r in rows], dtype=np.float64)
    E = np.asarray(energy_kev, dtype=np.float64)
    i = np.searchsorted(e, E, side="right") - 1
    i = np.clip(i, 0, len(e) - 2)
    lo, hi = e[i], e[i + 1]
    same = hi <= lo                                     # 端の下と上の 2 行の間には入らない(念のため)
    t = np.where(same, 0.0, np.log(np.maximum(E, 1e-300) / lo) / np.log(np.where(same, 2.0, hi / lo)))
    out = np.exp(np.log(v[i]) + t * (np.log(v[i + 1]) - np.log(v[i])))
    out = np.where(E == lo, v[i], out)                  # 表の点ちょうどは表の値そのもの(丸めの屑を足さない)
    at_end = E >= e[-1]
    return np.where(at_end, v[-1], out)


def _xray_mu_rho(src: dict, energy_kev, col: int = 1, op: str = "material_xray_attenuation") -> np.ndarray:
    E = np.asarray(energy_kev, dtype=np.float64)
    if not np.all(np.isfinite(E)) or np.any(E < XRAY_E_MIN_KEV * (1 - 1e-12)) or np.any(E > XRAY_E_MAX_KEV * (1 + 1e-12)):
        raise ValueError("%s: energy must lie in [%g, %g] keV (the bundled table; not extrapolated)"
                         % (op, XRAY_E_MIN_KEV, XRAY_E_MAX_KEV))
    if src["kind"] == "table":
        return _xray_interp(src["rows"], E, col)
    return sum(w * _xray_interp(_XE[z]["rows"], E, col) for z, w in src["composition"])


def _xray_edges(src: dict, lo: float, hi: float) -> list:
    out = []
    for z, w in src["composition"]:
        for r in _XE[z]["rows"]:
            if r[3] and lo <= r[0] <= hi:
                out.append((_XE[z]["symbol"], r[3], float(r[0])))
    return sorted(set(out), key=lambda t: t[2])


def material_xray_table() -> list:
    """X 線の列(質量減衰係数 μ/ρ)を引ける材料の一覧を返す。

    返り値: 1 材料 1 行の dict(name, kind = table / mixture / element, density_g_cm3, composition
    ((記号, 質量分率), …), optical(光学の表にも同じ名前のレコードがあるか), reference)。
    元素 49 種と NIST の化合物 20 種は NIST SRD 126(Hubbell & Seltzer)の表そのもの、それ以外は
    :data:`XRAY_SOLID`(と電子線の表)の組成から混合則で作る。範囲は 1 keV〜1 MeV(表の外は外挿しない)。
    """
    rows = []
    for z in sorted(_XE):
        e = _XE[z]
        rows.append({"name": e["symbol"].upper(), "kind": "element", "Z": z, "density_g_cm3": e["density_g_cm3"],
                     "composition": ((e["symbol"], 1.0),), "optical": e["symbol"].upper() in _RECORDS,
                     "reference": "NIST SRD 126 " + e["page"]})
    es = globals().get("ELECTRON_SOLID") or {}
    for key in list(_XC) + sorted(set(XRAY_SOLID) | {k for k in es if k not in _XC and k not in _XE_SYMBOL}):
        src = _xray_source(key, "material_xray_table")
        rows.append({"name": key, "kind": src["kind"], "density_g_cm3": src["density_g_cm3"],
                     "composition": tuple((_XE[z]["symbol"], round(w, 6)) for z, w in src["composition"]),
                     "optical": key in _RECORDS, "reference": src["reference"]})
    return rows


def material_xray_attenuation(material="CU", e_min_kev: float = 10.0, e_max_kev: float = 150.0,
                              n_points: int = 141, quantity: str = "mu_rho",
                              density_g_cm3=None) -> np.ndarray:
    """材料の X 線の減衰を ``pairs``(E [keV], 値)で返す(質量減衰係数 μ/ρ [cm²/g] が既定)。

    ``material``: 名前(``WATER`` / ``MUSCLE`` / ``BONE`` / ``PVC`` / ``CU`` / ``SAPPHIRE`` …、
    :func:`material_xray_table` の一覧)、化学式(``"Al2O3"``)、または
    ``{"composition": "C2H4" か {"SiO2": 0.7, …} か ((Z, w), …), "density_g_cm3": 0.93}``。
    ``quantity``: ``mu_rho``(全減衰、干渉性散乱を含む)/ ``mu_en_rho``(エネルギー吸収)/
    ``mu``(線減衰係数 μ = ρ·μ/ρ [1/cm]、密度が要る)。

    格子は ``e_min_kev``〜``e_max_kev`` の対数等間隔 ``n_points`` 点。吸収端(Cu の K 端 8.979 keV など)
    の上下は表の 2 行のあいだで飛ぶ —— 格子に端ちょうどの点があれば端の上の値になる。
    表は 1 keV〜1 MeV(NIST の行の log–log 補間、NIST が推奨する補間)。範囲の外は ValueError。

    公表値(NIST SRD 126): Cu の 8 keV で 52.55 cm²/g、K 端 8.979 keV で 38.29 → 278.4 cm²/g、
    水の 60 keV で 0.2059 cm²/g。
    """
    op = "material_xray_attenuation"
    if quantity not in ("mu_rho", "mu_en_rho", "mu"):
        raise ValueError("%s: quantity must be 'mu_rho', 'mu_en_rho' or 'mu', got %r" % (op, quantity))
    lo, hi, n = float(e_min_kev), float(e_max_kev), int(n_points)
    if not (np.isfinite(lo) and np.isfinite(hi) and 0.0 < lo < hi) or n < 2 or n > 100000:
        raise ValueError("%s: need 0 < e_min_kev < e_max_kev and 2 <= n_points <= 100000" % op)
    src = _xray_source(material, op, density_g_cm3)
    E = np.geomspace(lo, hi, n)
    v = _xray_mu_rho(src, E, 2 if quantity == "mu_en_rho" else 1, op)
    if quantity == "mu":
        if src["density_g_cm3"] is None:
            raise ValueError("%s: quantity='mu' needs a density (pass density_g_cm3=)" % op)
        v = v * src["density_g_cm3"]
    return _pairs(E, v)


def material_xray_constants(material="CU", energy_kev: float = 8.0, density_g_cm3=None) -> dict:
    """1 エネルギーの X 線の定数(μ/ρ・μ_en/ρ・μ・半価層・平均自由行程)と出典を返す。

    返り値: dict(name, energy_kev, mu_rho_cm2_g, mu_en_rho_cm2_g, density_g_cm3, mu_per_cm,
    hvl_mm = 10·ln 2/μ, mfp_mm = 10/μ, edges(±20 % の範囲にある吸収端の (元素, 端, keV)), kind, reference)。
    単色 X 線の半価層は ln 2/μ そのもの(多色の線質の半価層は ``dualxray.xray_beam_quality``)。
    """
    op = "material_xray_constants"
    E = float(energy_kev)
    src = _xray_source(material, op, density_g_cm3)
    mr = float(_xray_mu_rho(src, np.array([E]), 1, op)[0])
    me = float(_xray_mu_rho(src, np.array([E]), 2, op)[0])
    rho = src["density_g_cm3"]
    mu = None if rho is None else mr * rho
    return {"name": src["name"], "energy_kev": E, "mu_rho_cm2_g": mr, "mu_en_rho_cm2_g": me,
            "density_g_cm3": rho, "mu_per_cm": mu,
            "hvl_mm": None if mu is None else float(10.0 * np.log(2.0) / mu),
            "mfp_mm": None if mu is None else 10.0 / mu,
            "edges": _xray_edges(src, E / 1.2, E * 1.2), "kind": src["kind"], "reference": src["reference"]}


def material_effective_z(material="WATER", exponent: float = 2.94, density_g_cm3=None) -> dict:
    """組成から実効原子番号(Mayneord / Spiers の冪の式)と電子密度を返す。

    Z_eff = (Σ aᵢ Zᵢ^p)^(1/p)、aᵢ = wᵢ (Z/A)ᵢ / Σ wⱼ (Z/A)ⱼ は**電子の割合**、p = 2.94 は光電効果の
    断面積の Z 依存(≈ Z^3.94/原子 → Z^2.94/電子)から来る慣用の指数。水は 7.42(公表値)。
    電子密度 ρₑ = ρ N_A Σ wᵢ Zᵢ/Aᵢ [電子/cm³] と、水に対する比も返す。
    デュアルエナジーの像から推定する実効 Z(``dualxray.effective_z_map``)は、この「組成の Z_eff」と
    同じものではない(光電効果の比で定義した Z は、スペクトルの位置で値が数 % 動く)—— その差を
    PoC で数える。
    """
    op = "material_effective_z"
    p = float(exponent)
    if not np.isfinite(p) or not (1.0 <= p <= 5.0):
        raise ValueError("%s: exponent must lie in [1, 5], got %r" % (op, exponent))
    src = _xray_source(material, op, density_g_cm3)
    comp = src["composition"]
    ne = np.array([w * _XE[z]["z_over_a"] for z, w in comp])
    zs = np.array([float(z) for z, _ in comp])
    a = ne / ne.sum()
    zeff = float(np.sum(a * zs ** p) ** (1.0 / p))
    z_over_a = float(ne.sum())
    rho = src["density_g_cm3"]
    n_a = 6.02214076e23
    rho_e = None if rho is None else rho * n_a * z_over_a
    rho_e_w = 1.0 * n_a * sum(w * _XE[z]["z_over_a"] for z, w in _XC["WATER"]["composition"])
    return {"name": src["name"], "z_eff": zeff, "exponent": p, "z_over_a": z_over_a,
            "electron_density_per_cm3": rho_e,
            "electron_density_rel_water": None if rho_e is None else rho_e / rho_e_w,
            "electron_fractions": tuple((_XE[z]["symbol"], float(x)) for (z, _), x in zip(comp, a)),
            "density_g_cm3": rho}


# --------------------------------------------------------------------------- #
# 近赤外(NIR/SWIR)の吸収帯モデル —— 食品の異物・樹脂の選別で観察対象の側が引く表        #
# --------------------------------------------------------------------------- #
#: 吸収帯の重ね合わせで近赤外の吸収係数 α(λ) [1/mm] (自然対数の底)を作る材料。
#:
#: 2026-10-15(PoC ``poc_hyperspectral_foreign_matter``): 樹脂のレコード(PMMA / PC / PS / COP)は
#: Sultanova 2009 の分散式だけで、範囲は 0.437〜1.052 µm、k は無い。食品の異物や樹脂の選別が見る
#: 1.2〜2.4 µm の C-H・O-H の倍音・結合音はどこにも無かった。ここはその穴を埋める**簡易モデル**で、
#: 各帯は ``(中心 nm, 半値全幅 nm, ピークの α 1/mm)`` の Gauss。
#:
#: 印(``"grade"``): **U** = USGS の実測スペクトル(splib05a / splib07、public domain)の連続体除去した
#: 吸収の谷で中心を確かめた帯(PE: HDPE / LDPE 4 試料 GDS351/391/393/402、PET: GDS379/380/383)、
#: **L** = 論文の実測(Vázquez-Guardado ら 2015、Rani ら 2019)、**H** = 教科書で知られた帰属(Workman &
#: Weyer 2007、Schwanninger ら 2011)で中心は概数、**E** = 推定。**幅と強さはすべて模型**: PE の強さは
#: USGS の薄膜(LDPE 0.2 mm・HDPE 0.1 mm)の谷の深さから逆算した桁(1215 nm 0.1〜0.3、1730 nm 0.4〜1、
#: 2310 nm 1.5〜1.7 /mm。測定時の背景が記録に無いので桁の目安)に合わせ、PP・PS・脂質はそれに倣って
#: CH の密度で比例させた。2026-10-15 の一次情報の照合で初版の PE 1730 / 2310 nm(2 / 5 /mm)が 2〜3 倍
#: 過大と分かって下げ、PE の 2387 nm と PET の最も深い 2 帯(2258 / 2334 nm)と 1715 nm の肩を足した。
#: **実測スペクトルに合わせた値ではない** —— 分光器の実測で置き換えること
#: (``material_nir_absorption(..., bands=...)`` で上書きできる)。
#:
#: 水だけは表の一次文献を使う: ``WATER`` の k(Hale & Querry 1973)から α = 4πk/λ。食品・木材の
#: ``"water"`` は水の質量分率で、その水の α を分率で足す(混合は体積分率の線形和で近似)。
#: ``"components"`` を持つ材料は成分(脂質・タンパク質・炭水化物・リグニン)の分率で帯を足す。
#:
#: 出典: R. N. Clark ら, USGS Digital Spectral Library splib05a, USGS Open-File Report 03-395 (2003) と
#: R. F. Kokaly ら, splib07, USGS Data Series 1035 (2017)(public domain、樹脂の実測反射)/
#: M. Rani ら, Materials 12, 2740 (2019)(PP 1190 / 1400、PS 1140 / 1205 / 1675 nm)/
#: A. Vázquez-Guardado, M. Money, N. McKinney, D. Chanda, Appl. Opt. 54, 7396 (2015)
#: (PET 1664 / 1910、HDPE 1733 / 1767、PP 1709 / 1727、PS 1682 nm、黒い試料は NIR に反応しない)/
#: G. M. Hale, M. R. Querry, Appl. Opt. 12, 555 (1973)(水)/ M. Schwanninger, J. C. Rodrigues,
#: K. Fackler, J. Near Infrared Spectrosc. 19, 287 (2011)(木材・リグノセルロースの帯)/
#: J. Workman, L. Weyer, Practical Guide to Interpretive Near-Infrared Spectroscopy, CRC (2007)。
NIR_BAND_MODELS = {
    # ---- 成分(食品・木材の材料が分率で足す) ----
    "LIPID": {"class": "component", "aliases": ("FAT", "TRIGLYCERIDE"), "n_nir": 1.47,
              "bands": ((1210.0, 40.0, 0.08, "H"), (1728.0, 35.0, 0.6, "H"), (1765.0, 35.0, 0.5, "H"),
                        (2140.0, 40.0, 0.3, "H"), (2310.0, 40.0, 1.3, "H"), (2350.0, 40.0, 1.1, "H")),
              "baseline_per_mm": 0.002, "note": "triglyceride CH2 overtones and combinations; cis C=CH at 2140 nm"},
    "PROTEIN": {"class": "component", "aliases": (), "n_nir": 1.53,
                "bands": ((1510.0, 60.0, 0.15, "H"), (2050.0, 60.0, 0.4, "H"), (2180.0, 50.0, 0.4, "H")),
                "baseline_per_mm": 0.003, "note": "N-H overtone 1510 nm, N-H combinations 2050 / 2180 nm"},
    "CARBOHYDRATE": {"class": "component", "aliases": ("CELLULOSE", "STARCH"), "n_nir": 1.53,
                     "bands": ((1490.0, 80.0, 0.4, "H"), (1590.0, 60.0, 0.2, "H"), (2100.0, 60.0, 0.8, "H"),
                               (2270.0, 40.0, 0.4, "H"), (2330.0, 50.0, 0.5, "H")),
                     "baseline_per_mm": 0.003, "note": "O-H first overtone 1490 nm, O-H + C-O combination 2100 nm"},
    "LIGNIN": {"class": "component", "aliases": (), "n_nir": 1.6,
               "bands": ((1420.0, 50.0, 0.2, "H"), (1680.0, 40.0, 0.3, "H"), (2270.0, 40.0, 0.4, "H"),
                         (2330.0, 50.0, 0.4, "H")),
               "baseline_per_mm": 0.02, "note": "aromatic C-H 1680 nm, phenolic O-H 1420 nm"},
    # ---- 樹脂(リサイクルの選別、食品ラインの異物) ----
    "POLYETHYLENE": {"class": "polymer", "aliases": ("PE", "HDPE", "LDPE"), "n_nir": 1.51,
                     "bands": ((1215.0, 40.0, 0.15, "U"), (1395.0, 40.0, 0.10, "U"), (1731.0, 25.0, 0.8, "U"),
                               (1765.0, 25.0, 0.65, "U"), (2310.0, 35.0, 1.6, "U"), (2350.0, 28.0, 1.3, "U"),
                               (2387.0, 20.0, 0.6, "U")),
                     "baseline_per_mm": 0.002, "scattering_per_mm": 8.0, "reference_um": 500.0,
                     "note": "CH2 troughs of four USGS splib05a HDPE / LDPE samples (1215, 1395, 1731, 1765, 2310, 2350, 2387 nm)"},
    "POLYPROPYLENE": {"class": "polymer", "aliases": ("PP",), "n_nir": 1.49,
                      "bands": ((1195.0, 40.0, 0.12, "L"), (1395.0, 40.0, 0.10, "L"), (1709.0, 14.0, 0.6, "L"),
                                (1727.0, 14.0, 0.75, "L"), (2310.0, 45.0, 1.5, "H")),
                      "baseline_per_mm": 0.002, "scattering_per_mm": 8.0, "reference_um": 500.0,
                      "note": "CH3 + CH2: 1190 / 1400 nm (Rani 2019), 1709 / 1727 nm (Vazquez-Guardado 2015, not re-verified)"},
    "PET": {"class": "polymer", "aliases": ("POLYETHYLENE_TEREPHTHALATE",), "n_nir": 1.57,
            "bands": ((1130.0, 40.0, 0.05, "U"), (1662.0, 20.0, 0.6, "U"), (1715.0, 25.0, 0.2, "U"),
                      (1907.0, 30.0, 0.3, "U"), (2131.0, 40.0, 0.5, "U"), (2258.0, 35.0, 1.2, "U"),
                      (2334.0, 35.0, 0.9, "U")),
            "baseline_per_mm": 0.002, "scattering_per_mm": 8.0, "reference_um": 500.0,
            "note": "USGS splib05a PET troughs; the deepest are 2258 and 2334 nm (GDS379/380/383)"},
    "POLYSTYRENE": {"class": "polymer", "aliases": ("PS",), "n_nir": 1.57,
                    "bands": ((1145.0, 30.0, 0.06, "L"), (1682.0, 20.0, 0.6, "L"), (2170.0, 35.0, 0.8, "E"),
                              (2310.0, 40.0, 0.8, "E")),
                    "baseline_per_mm": 0.002, "scattering_per_mm": 8.0, "reference_um": 500.0,
                    "note": "aromatic C-H 1682 nm measured trough (Vazquez-Guardado 2015); n record: Sultanova 2009"},
    # ---- 食品と、食品ラインに混じる植物の破片 ----
    "NUT_KERNEL": {"class": "food", "aliases": ("ALMOND_KERNEL", "KERNEL"), "n_nir": 1.5,
                   "components": (("LIPID", 0.50), ("PROTEIN", 0.21), ("CARBOHYDRATE", 0.22)), "water": 0.045,
                   "baseline_per_mm": 0.003, "scattering_per_mm": 1.5, "reference_um": 1000.0,
                   "note": "almond-like composition (USDA order of magnitude): lipid 50 %, protein 21 %, "
                           "carbohydrate 22 %, water 4.5 %"},
    "NUT_SHELL": {"class": "food", "aliases": ("SHELL", "HULL"), "n_nir": 1.55,
                  "components": (("CARBOHYDRATE", 0.60), ("LIGNIN", 0.30)), "water": 0.08,
                  "baseline_per_mm": 0.01, "scattering_per_mm": 6.0, "reference_um": 500.0,
                  "note": "lignocellulose: cellulose + hemicellulose 60 %, lignin 30 %, water 8 % (estimate)"},
    "WOOD": {"class": "food", "aliases": ("WOOD_CHIP",), "n_nir": 1.55,
             "components": (("CARBOHYDRATE", 0.70), ("LIGNIN", 0.25)), "water": 0.12,
             "baseline_per_mm": 0.008, "scattering_per_mm": 4.0, "reference_um": 500.0,
             "note": "cellulose + hemicellulose 70 %, lignin 25 %, water 12 % (estimate)"},
}
_NIR_ALIASES = {a: k for k, v in NIR_BAND_MODELS.items() for a in v["aliases"]}

#: カーボンブラックの質量吸収断面積 [m²/g] at 550 nm と、その波長依存の指数(Bond & Bergstrom,
#: Aerosol Sci. Technol. 40, 27 (2006): MAC 7.5 ± 1.2 m²/g、吸収 Ångström 指数 ≈ 1)。
CARBON_BLACK_MAC_550 = 7.5
CARBON_BLACK_AAE = 1.0


def _nir_key(material, op):
    if not isinstance(material, str):
        raise ValueError("%s: material must be a name, got %r" % (op, type(material).__name__))
    key = _key(material)
    if key in NIR_BAND_MODELS:
        return key
    if key in _NIR_ALIASES:
        return _NIR_ALIASES[key]
    if key == "WATER" or _ALIASES.get(key) == "WATER":
        return "WATER"
    raise ValueError("%s: no near-infrared absorption model for %r (models: %s, and WATER from the n,k table)"
                     % (op, material, ", ".join(sorted(NIR_BAND_MODELS))))


def _band_sum(bands, wl):
    a = np.zeros_like(wl)
    for b in bands:
        c, fwhm, peak = float(b[0]), float(b[1]), float(b[2])
        if not (c > 0.0 and fwhm > 0.0 and peak >= 0.0 and all(map(np.isfinite, (c, fwhm, peak)))):
            raise ValueError("material_nir_absorption: a band needs centre > 0, FWHM > 0, peak >= 0, got %r" % (b,))
        sig = fwhm / (2.0 * np.sqrt(2.0 * np.log(2.0)))
        a += peak * np.exp(-0.5 * ((wl - c) / sig) ** 2)
    return a


def _water_alpha_per_mm(wl, op):
    n, k, _, k_src = _nk(_RECORDS["WATER"], wl / 1000.0, op)
    if any(s is None for s in k_src):
        raise ValueError("%s: the WATER table has no extinction coefficient over the requested range" % op)
    return 4.0 * np.pi * k / (wl * 1e-6)                     # λ in mm → α in 1/mm


def material_nir_absorption(material="POLYETHYLENE", wl_min_nm: float = 900.0, wl_max_nm: float = 2500.0,
                            n_points: int = 321, water_fraction=None, bands=None):
    """近赤外(0.9〜2.5 µm)の吸収係数 α(λ) [1/mm] (自然対数の底)を、吸収帯の重ね合わせで。

    *material* は :data:`NIR_BAND_MODELS` の名前か別名(``PE`` / ``PP`` / ``PET`` / ``PS`` /
    ``NUT_KERNEL`` / ``NUT_SHELL`` / ``WOOD`` / 成分 ``LIPID`` …)、または ``WATER``(この時だけ帯の
    モデルでなく表の k(Hale & Querry 1973)から α = 4πk/λ)。成分を持つ食品・木材は
    α = Σ fᵢ αᵢ + w α_水 + 基線。*water_fraction* を与えると表の水分率 w を上書きする(湿り・含水率の
    掃引)。*bands* に ``((中心 nm, 半値全幅 nm, α /mm), ...)`` を与えると帯の表を丸ごと差し替える
    (実測で合わせた帯を持ち込む口)。

    ★帯の幅と強さは**推定**(:data:`NIR_BAND_MODELS` の注)。中心は一次文献の実測(L 印)か
    教科書の帰属(H 印)。区間外の外挿はしない(水の表の範囲外は ValueError)。

    返り値: pairs(λ nm, α 1/mm)。光源・QE と同じ形なので :func:`spectralrad.kubelka_munk_reflectance`
    にそのまま渡せる。
    """
    op = "material_nir_absorption"
    wl = _grid_nm(wl_min_nm, wl_max_nm, n_points, op)
    key = _nir_key(material, op)
    if key == "WATER":
        if bands is not None or water_fraction is not None:
            raise ValueError("%s: WATER comes from the n,k table; bands / water_fraction do not apply" % op)
        return _pairs(wl, _water_alpha_per_mm(wl, op))
    m = NIR_BAND_MODELS[key]
    if bands is not None:
        alpha = _band_sum(bands, wl)
    elif "components" in m:
        alpha = np.zeros_like(wl)
        for comp, frac in m["components"]:
            alpha += float(frac) * _band_sum(NIR_BAND_MODELS[comp]["bands"], wl)
    else:
        alpha = _band_sum(m["bands"], wl)
    alpha = alpha + float(m.get("baseline_per_mm", 0.0))
    w = m.get("water", 0.0) if water_fraction is None else water_fraction
    w = float(w)
    if not (np.isfinite(w) and 0.0 <= w <= 1.0):
        raise ValueError("%s: water_fraction must lie in [0, 1], got %r" % (op, water_fraction))
    if w > 0.0:
        alpha = (1.0 - w) * alpha + w * _water_alpha_per_mm(wl, op)
    return _pairs(wl, alpha)


def carbon_black_absorption(fraction_by_mass: float = 0.005, wl_min_nm: float = 900.0,
                            wl_max_nm: float = 2500.0, n_points: int = 321, density_g_cm3: float = 1.0):
    """カーボンブラック(黒い樹脂の顔料)が足す吸収係数 α [1/mm]。

    α = MAC(λ)·ρ·w、MAC(λ) = 7.5 m²/g × (550/λ)^1(Bond & Bergstrom 2006 の黒色炭素の質量吸収断面積と
    吸収 Ångström 指数)。0.5 wt % の樹脂(ρ ≈ 1 g/cm³)で 1.6 µm に約 13 /mm —— どの樹脂の C-H の帯
    (1〜5 /mm)より強く、しかも平坦なので、帯の形が見えなくなる(黒い樹脂が NIR で選別できない理由)。

    返り値: pairs(λ nm, α 1/mm)。
    """
    op = "carbon_black_absorption"
    wl = _grid_nm(wl_min_nm, wl_max_nm, n_points, op)
    w, rho = float(fraction_by_mass), float(density_g_cm3)
    if not (np.isfinite(w) and 0.0 <= w <= 1.0):
        raise ValueError("%s: fraction_by_mass must lie in [0, 1], got %r" % (op, fraction_by_mass))
    if not (np.isfinite(rho) and rho > 0.0):
        raise ValueError("%s: density_g_cm3 must be finite and > 0, got %r" % (op, density_g_cm3))
    mac_m2_g = CARBON_BLACK_MAC_550 * (550.0 / wl) ** CARBON_BLACK_AAE
    alpha_per_m = mac_m2_g * (rho * 1e6) * w                     # g/cm³ → g/m³
    return _pairs(wl, alpha_per_m * 1e-3)


def nir_model_info(material="POLYETHYLENE") -> dict:
    """:data:`NIR_BAND_MODELS` の 1 材料を、出典の印つきで表にして返す(帯・成分・水・散乱・屈折率)。

    返り値: dict(name, class, bands [(中心, 幅, α, 印)] — 成分を持つ材料は成分ごとに分率を掛けた帯,
    components, water, scattering_per_mm, reference_um, n_nir, note)。
    """
    op = "nir_model_info"
    key = _nir_key(material, op)
    if key == "WATER":
        return {"name": "WATER", "class": "liquid", "bands": [], "components": (), "water": 1.0,
                "note": "alpha = 4 pi k / lambda from Hale & Querry 1973 (the n,k table)"}
    m = NIR_BAND_MODELS[key]
    if "components" in m:
        bands = [(c, f, a * frac, g) for comp, frac in m["components"] for (c, f, a, g) in NIR_BAND_MODELS[comp]["bands"]]
    else:
        bands = list(m["bands"])
    return {"name": key, "class": m["class"], "bands": bands, "components": tuple(m.get("components", ())),
            "water": float(m.get("water", 0.0)), "scattering_per_mm": m.get("scattering_per_mm"),
            "reference_um": m.get("reference_um"), "n_nir": m["n_nir"], "note": m.get("note", "")}
