# -*- coding: utf-8 -*-
"""refractiveindex.info database(CC0 1.0)から fullseye の材料表 ``materials_data.py`` を生成する。

使い方::

    py -3.11 -I tools/gen_material_tables.py --rii <database dir> [--out materials_data.py] [--check]

``<database dir>`` は RII の ``database/`` (``catalog-nk.yml`` と ``data/`` がある階層)。
``--check`` は生成結果を既存ファイルと比較して違えば exit 1(手で書き換えた痕跡を見つける)。

**何を同梱するか**: 一次文献の係数と表(CC0)だけ。各レコードに出典(REFERENCES を素の文に
したもの)と RII のページパスを残す。メーカーの硝材カタログ本体(.agf)は同梱しない
(``materials.read_glass_catalog_agf`` がユーザーのファイルを読む)。

**選定の方針**: 硝材は 4 社の代表(既存 ``raytrace._SELLMEIER`` の 17 種を含む)、結晶・IR 材・
半導体・金属・液体・プラスチック・膜は「検査光学で実際に使う材料」。1 材料に複数の
データ区間(例 Si: Green 2008 の n,k 0.25–1.45 µm と Salzberg の Sellmeier 1.36–11 µm)を
持てる。生成物は Python の literal だけ(実行時に YAML も I/O も要らない)。

**金属は測定値(または測定値に合わせた模型)から選ぶ**(2026-10-14): 初版は W と Pt に
Werner 2009 の REELS(電子エネルギー損失)逆算の表を選んでいて、可視の垂直反射率が
Pt 0.93 / W 0.84(550 nm)と、別の測定(Pt 0.64〜0.73 / W 0.50)から大きく外れていた。
いまは W = Weaver(測定)、Pt = Tselin 2024(分光エリプソメトリ、Phys. Rev. B 110, 195130)。

**半導体も結晶の表から選ぶ**(2026-10-14): 初版の Ge は Amotchkina(e-beam 蒸着の膜に近い値、n(0.6 µm) = 3.07、
n(10 µm) = 3.96)と Burnett(結晶)を継ぎ、SiC は 6H の Singh と Larruquert(スパッタ膜、n が 0.7 高い)を継いでいた
—— 継ぎ目で n が 0.044 / 0.66 跳び、別の物質を 1 本につないでいた。いまは Ge = Nunley(結晶、0.19〜2.48 µm)+ Burnett
(2〜14 µm)、SiC = Wang の 4H 常光線(0.40〜5 µm、ウェハの主流)。``tests/test_materials.py`` が継ぎ目の差(≤ 0.01)と
独立の表(Ge: Li 293 K、SiC: Singh の 6H、Si: Li 293 K)との差を数える。
``tests/test_materials.py`` が 550 nm の反射率を別の測定の表の値と突き合わせる。

**シンチレータ・蛍光体の発光の列**(2026-10-23、``SCINTILLATORS``): X 線・γ 線を光に変える無機の
シンチレータ 7 種(化学式で名前を付ける。商品名は使わない)。RII の表ではないので、値は一次情報を
読んで写した**キュレート済みの定数**で、値ごとに出典を ``sources`` に残す(PDG 2024 の表 35.4・
Berkeley Lab の Inorganic Scintillator Library の csv の行・論文)。確かめられなかった値は ``None``
にして ``unverified`` に名前を並べる(推測で埋めない)。屈折率の表が RII にある材料(CsI / NaI /
Bi4Ge3O12)は ``datasets`` にその一次文献も載せる。X 線の列は ``xray_material``(NIST の化合物の表の
名前か化学式)で ``materials`` の X 線の列が引く。
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sys

try:
    import yaml  # PyYAML(生成時だけ)
except ImportError:  # pragma: no cover
    sys.exit("PyYAML is required to run the generator: py -3.11 -m pip install pyyaml")

# (name, class, [(rii page, note)], aliases)
# class: glass / crystal / semiconductor / metal / liquid / polymer / film
_SCHOTT = ["N-BK7", "N-K5", "N-BAK4", "N-SK16", "N-SSK5", "N-BAF10", "N-LAK22", "N-LAK9",
           "N-LASF9", "N-FK51A", "N-F2", "N-SF2", "N-SF5", "N-SF10", "N-SF11", "N-SF6", "N-SF57",
           "N-PK52A", "N-KZFS4", "N-LAF34", "N-FK58", "N-LASF31A", "N-SF66", "N-LAK14",
           "N-PSK53A", "P-SF68"]
_OHARA = ["S-BSL7", "S-FPL51", "S-LAH58", "S-TIH6", "S-NPH1", "S-LAH79", "S-BAH11", "S-FSL5"]
_HOYA = ["FD60", "TAF3", "E-FD10", "BSC7", "FCD1", "TAC8", "M-TAC60"]
_CDGM = ["H-K9L", "H-ZF52A", "H-LAF50B", "D-ZK3", "H-ZLAF55D"]

SELECTION = []
_SCHOTT_ALIASES = {"N-BK7": ["BK7"], "N-SF11": ["SF11"], "N-SF2": ["SF2"], "N-F2": ["F2"], "N-SK16": ["SK16"]}
for _g in _SCHOTT:
    SELECTION.append((_g, "glass", [("specs/schott/optical/%s.yml" % _g, "")], _SCHOTT_ALIASES.get(_g, [])))
for _g in _OHARA:
    SELECTION.append((_g, "glass", [("specs/ohara/optical/%s.yml" % _g, "")], []))
for _g in _HOYA:
    SELECTION.append((_g, "glass", [("specs/hoya/optical/%s.yml" % _g, "")], []))
for _g in _CDGM:
    SELECTION.append((_g, "glass", [("specs/cdgm/optical/%s.yml" % _g, "")], []))

SELECTION += [
    # 結晶・IR 材(main/ の一次文献)
    ("SILICA", "crystal", [("main/SiO2/nk/Malitson.yml", "fused silica")], ["FUSED_SILICA", "SIO2"]),
    ("QUARTZ", "crystal", [("main/SiO2/nk/Ghosh-o.yml", "crystalline quartz, ordinary ray")], []),
    ("CAF2", "crystal", [("main/CaF2/nk/Malitson.yml", "")], ["FLUORITE"]),
    ("BAF2", "crystal", [("main/BaF2/nk/Li.yml", "")], []),
    ("MGF2", "crystal", [("main/MgF2/nk/Dodge-o.yml", "ordinary ray")], []),
    ("LIF", "crystal", [("main/LiF/nk/Li.yml", "")], []),
    ("KBR", "crystal", [("main/KBr/nk/Li.yml", "")], []),
    ("CSI", "crystal", [("main/CsI/nk/Li.yml", "")], []),
    ("SAPPHIRE", "crystal", [("main/Al2O3/nk/Malitson-o.yml", "ordinary ray")], ["AL2O3"]),
    ("YAG", "crystal", [("main/Y3Al5O12/nk/Zelmon.yml", "")], []),
    ("ZNSE", "crystal", [("main/ZnSe/nk/Connolly.yml", "")], []),
    ("ZNS", "crystal", [("main/ZnS/nk/Debenham.yml", "")], []),
    # 半導体
    ("SI", "semiconductor", [("main/Si/nk/Green-2008.yml", "300 K, band-to-band k"),
                             ("main/Si/nk/Salzberg.yml", "IR Sellmeier, k not given (0)")], ["SILICON"]),
    ("GE", "semiconductor", [("main/Ge/nk/Nunley.yml", "300 K, bulk crystal"), ("main/Ge/nk/Burnett.yml", "")], ["GERMANIUM"]),
    ("GAAS", "semiconductor", [("main/GaAs/nk/Aspnes.yml", ""), ("main/GaAs/nk/Skauli.yml", "")], []),
    ("GAN", "semiconductor", [("main/GaN/nk/Barker-o.yml", "ordinary ray")], []),
    ("INP", "semiconductor", [("main/InP/nk/Aspnes.yml", "")], []),
    ("SIC", "semiconductor", [("main/SiC/nk/Wang-4H-o.yml", "4H, ordinary ray")], ["4H-SIC"]),
    # 膜
    ("SI3N4", "film", [("main/Si3N4/nk/Luke.yml", "")], ["SILICON_NITRIDE"]),
    ("TIO2", "film", [("main/TiO2/nk/Devore-o.yml", "rutile, ordinary ray")], ["TIO2_RUTILE_O"]),
    # ★2026-10-15: 上の TIO2 はルチル単結晶の常光線だけ(430 nm から・k なし)。成膜した TiO2 は非晶質か
    # アナターゼが多く n が低い —— 膜の計算はこちらを名指しする(非公開の膜の PoC で、ルチルの n で膜を
    # 解くと傾いた面の膜厚の偏りが小さく出ることを確認)。
    ("TIO2_RUTILE_E", "film", [("main/TiO2/nk/Devore-e.yml", "rutile, extraordinary ray")], []),
    ("TIO2_AMORPHOUS", "film", [("main/TiO2/nk/Franta.yml",
                                 "e-beam film 99.6 nm on c-Si, amorphous (very fine polycrystalline); "
                                 "n and k from ellipsometry + spectrophotometry")], ["TIO2_FILM"]),
    ("TIO2_ANATASE", "film", [("main/TiO2/nk/Jolivet-anatase.yml", "ALD film grown at 300 C, anatase")], []),
    ("TA2O5", "film", [("main/Ta2O5/nk/Gao.yml", "")], []),
    ("HFO2", "film", [("main/HfO2/nk/Al-Kuhaili.yml", "")], []),
    # 金属
    ("AG", "metal", [("main/Ag/nk/Johnson.yml", "")], ["SILVER"]),
    ("AU", "metal", [("main/Au/nk/Johnson.yml", "")], ["GOLD"]),
    ("CU", "metal", [("main/Cu/nk/Johnson.yml", "")], ["COPPER"]),
    ("AL", "metal", [("main/Al/nk/Rakic.yml", "")], ["ALUMINIUM", "ALUMINUM"]),
    ("CR", "metal", [("main/Cr/nk/Johnson.yml", "")], ["CHROMIUM"]),
    ("NI", "metal", [("main/Ni/nk/Johnson.yml", "")], ["NICKEL"]),
    ("RH", "metal", [("main/Rh/nk/Weaver.yml", "")], ["RHODIUM"]),
    ("W", "metal", [("main/W/nk/Weaver.yml", "")], ["TUNGSTEN"]),
    ("TI", "metal", [("main/Ti/nk/Johnson.yml", "")], ["TITANIUM"]),
    ("PT", "metal", [("main/Pt/nk/Tselin.yml", "")], ["PLATINUM"]),
    # 液体
    ("WATER", "liquid", [("main/H2O/nk/Daimon-20.0C.yml", "20 C, visible"),
      ("main/H2O/nk/Segelstein.yml", "25 C, k only (Segelstein 1981 resolves the 1.45 / 1.94 um bands)", "k"),
      ("main/H2O/nk/Hale.yml", "25 C, 0.2-200 um")], ["H2O"]),
    # プラスチック
    ("PMMA", "polymer", [("organic/(C5H8O2)n - poly(methyl methacrylate)/nk/Sultanova.yml", "")], ["ACRYLIC"]),
    ("POLYCARBONATE", "polymer", [("organic/(C16H14O3)n - polycarbonate/nk/Sultanova.yml", "")], ["PC"]),
    ("POLYSTYRENE", "polymer", [("organic/(C8H8)n - polystyrene/nk/Sultanova.yml", "")], ["PS"]),
    ("ZEONEX_E48R", "polymer", [("other/commercial polymers/ZeonexE48R/nk/Sultanova.yml", "cyclo-olefin polymer")], ["COP"]),
]


# --------------------------------------------------------------------------- #
# シンチレータ・蛍光体の発光の列(2026-10-23)                                   #
# --------------------------------------------------------------------------- #
# 値は一次情報を読んで写した定数(RII の表ではない)。1 値 1 出典で ``sources`` に残す。
#   PDG  = Particle Data Group, S. Navas et al., Phys. Rev. D 110, 030001 (2024), review "Particle detectors at
#          accelerators", Table 35.4 "Properties of several inorganic crystals"(密度・減衰時間・発光の極大・
#          極大での屈折率。光収率は NaI(Tl) を 100 とする相対値なので絶対値には使わない)。
#   LBNL = Berkeley Lab "Inorganic Scintillator Library"(https://scintillator.lbl.gov/inorganic-scintillator-library/、
#          公開の csv を 2026-10-23 に読んだ。SHA-256 6085c865…940a)。行ごとに原著の略号(Sakai1987 など)がある。
#          光収率 [photons/MeV] はここから取り、どの行かを書く。
# 発光スペクトルの**幅**(FWHM)は、確かめられる一次情報を見つけられなかったので全材料 ``None``。
# 消費側(``dualxray.scintillator_sensor_qe``)は幅が無いとき発光を極大の 1 本の線として扱い、そう返り値に書く
# (幅を推測で入れない)。実測の発光スペクトルがあれば ``emission_spectrum=`` で渡す。
_PDG_2024 = ("Particle Data Group, S. Navas et al., Phys. Rev. D 110, 030001 (2024), review 35 'Particle detectors "
             "at accelerators', Table 35.4")
_LBNL = ("Berkeley Lab Inorganic Scintillator Library, https://scintillator.lbl.gov/inorganic-scintillator-library/ "
         "(csv read 2026-10-23), row ")

SCINTILLATORS = [
    {"name": "CSI:TL", "class": "crystal", "aliases": ["CSI(TL)", "CSI_TL"],
     "pages": [("main/CsI/nk/Li.yml", "undoped CsI; the Tl activator (~0.1 %) is not resolved in n")],
     "activator": "Tl+", "form": "single crystal", "xray_material": "CSI",
     "density_g_cm3": 4.51, "light_yield_photons_per_mev": 56000.0, "decay_time_ns": 1220.0,
     "emission_peak_nm": 550.0, "emission_fwhm_nm": None, "refractive_index_at_peak": 1.79,
     "sources": {"density_g_cm3": _PDG_2024, "decay_time_ns": _PDG_2024, "emission_peak_nm": _PDG_2024,
                 "refractive_index_at_peak": _PDG_2024,
                 "light_yield_photons_per_mev": _LBNL + "Sakai1987 (56,000; deHaas2005 and dehaas2008 also 56,000)",
                 "xray_material": "NIST SRD 126 compound table 'Cesium Iodide' (Tl neglected)"}},
    {"name": "NAI:TL", "class": "crystal", "aliases": ["NAI(TL)", "NAI_TL"],
     "pages": [("main/NaI/nk/Li.yml", "undoped NaI; the Tl activator is not resolved in n")],
     "activator": "Tl+", "form": "single crystal", "xray_material": "NaI",
     "density_g_cm3": 3.67, "light_yield_photons_per_mev": 45000.0, "decay_time_ns": 245.0,
     "emission_peak_nm": 410.0, "emission_fwhm_nm": None, "refractive_index_at_peak": 1.85,
     "sources": {"density_g_cm3": _PDG_2024, "decay_time_ns": _PDG_2024, "emission_peak_nm": _PDG_2024,
                 "refractive_index_at_peak": _PDG_2024,
                 "light_yield_photons_per_mev": _LBNL + "Sakai1987 (45,000; dehaas2008 also 45,000)",
                 "xray_material": "chemical formula NaI, mixture rule over NIST SRD 126 (Tl neglected)"}},
    {"name": "BI4GE3O12", "class": "crystal", "aliases": ["BGO"],
     "pages": [("main/Bi4Ge3O12/nk/Williams.yml", "")],
     "activator": "Bi3+ (intrinsic)", "form": "single crystal", "xray_material": "Bi4Ge3O12",
     "density_g_cm3": 7.13, "light_yield_photons_per_mev": 8500.0, "decay_time_ns": 300.0,
     "emission_peak_nm": 480.0, "emission_fwhm_nm": None, "refractive_index_at_peak": 2.15,
     "sources": {"density_g_cm3": _PDG_2024, "decay_time_ns": _PDG_2024, "emission_peak_nm": _PDG_2024,
                 "refractive_index_at_peak": _PDG_2024,
                 "light_yield_photons_per_mev": _LBNL + "Moszynski1997a (8,500; the room-temperature rows span "
                                                "7,100-10,600)",
                 "xray_material": "chemical formula Bi4Ge3O12, mixture rule over NIST SRD 126"}},
    {"name": "LU2SIO5:CE", "class": "crystal", "aliases": ["LSO", "LSO:CE", "LU2SIO5(CE)"],
     "pages": [],
     "activator": "Ce3+", "form": "single crystal", "xray_material": "Lu2SiO5",
     "density_g_cm3": 7.40, "light_yield_photons_per_mev": 27000.0, "decay_time_ns": 40.0,
     "emission_peak_nm": 402.0, "emission_fwhm_nm": None, "refractive_index_at_peak": 1.82,
     "sources": {"density_g_cm3": _PDG_2024, "decay_time_ns": _PDG_2024, "emission_peak_nm": _PDG_2024,
                 "refractive_index_at_peak": _PDG_2024,
                 "light_yield_photons_per_mev": _LBNL + "Melcher1996 (27,000; the rows span 22,200-33,000 with "
                                                "Ce content)",
                 "xray_material": "chemical formula Lu2SiO5, mixture rule over NIST SRD 126 (Ce neglected)"}},
    {"name": "LU1.8Y0.2SIO5:CE", "class": "crystal", "aliases": ["LYSO", "LYSO:CE"],
     "pages": [],
     "activator": "Ce3+", "form": "single crystal", "xray_material": "Lu1.8Y0.2SiO5",
     "density_g_cm3": 7.1, "light_yield_photons_per_mev": 34000.0, "decay_time_ns": 41.0,
     "emission_peak_nm": 397.0, "emission_fwhm_nm": None, "refractive_index_at_peak": None,
     "sources": {"density_g_cm3": _LBNL + "Pidol2004", "light_yield_photons_per_mev": _LBNL + "Pidol2004",
                 "decay_time_ns": _LBNL + "Pidol2004 ('41 + slow': the fast component; a slow tail is not given)",
                 "emission_peak_nm": _LBNL + "Pidol2004",
                 "xray_material": "chemical formula Lu1.8Y0.2SiO5, mixture rule over NIST SRD 126 (Ce neglected)"}},
    {"name": "CDWO4", "class": "crystal", "aliases": [],
     "pages": [],
     "activator": "self-activated", "form": "single crystal", "xray_material": "CdWO4",
     "density_g_cm3": 7.9, "light_yield_photons_per_mev": 27000.0, "decay_time_ns": 12000.0,
     "emission_peak_nm": 495.0, "emission_fwhm_nm": None, "refractive_index_at_peak": None,
     "sources": {"density_g_cm3": _LBNL + "Moszynski2005", "light_yield_photons_per_mev":
                 _LBNL + "Moszynski2005 (27,000; the other rows give 7,800-15,800 - the spread is large)",
                 "decay_time_ns": _LBNL + "Moszynski2005", "emission_peak_nm": _LBNL + "Moszynski2005",
                 "xray_material": "chemical formula CdWO4, mixture rule over NIST SRD 126"}},
    {"name": "GD2O2S:TB", "class": "crystal", "aliases": ["GOS:TB", "GD2O2S(TB)"],
     "pages": [],
     "activator": "Tb3+", "form": "powder phosphor / ceramic", "xray_material": "GOS",
     "density_g_cm3": 7.44, "light_yield_photons_per_mev": None, "decay_time_ns": 638000.0,
     "emission_peak_nm": 545.0, "emission_fwhm_nm": None, "refractive_index_at_peak": None,
     "sources": {"density_g_cm3": "NIST SRD 126 Table 2 'Gadolinium Oxysulfide' (bulk; a powder screen is less dense)",
                 "decay_time_ns": "B. Tang et al., Molecules 28, 1815 (2023), doi:10.3390/molecules28041815, Table 1 "
                                  "(x = 0: 638 us; photoluminescence lifetime of Tb3+ under 293-298 nm excitation, "
                                  "not X-ray)",
                 "emission_peak_nm": "B. Tang et al., Molecules 28, 1815 (2023): strongest line 545 nm (5D4 -> 7F5); "
                                     "further lines at 494 / 589 / 623 nm (a line spectrum, not one band)",
                 "xray_material": "NIST SRD 126 compound table 'Gadolinium Oxysulfide' (Tb neglected)"}},
]
_SCINT_FIELDS = ("activator", "form", "xray_material", "density_g_cm3", "light_yield_photons_per_mev",
                 "decay_time_ns", "emission_peak_nm", "emission_fwhm_nm", "refractive_index_at_peak")
_SCINT_BY_NAME = {s["name"]: s for s in SCINTILLATORS}


def _scintillator_properties(s):
    """SCINTILLATORS の 1 行 → レコードの ``properties``(密度は kg/m³ にも、発光の列は ``scintillator`` に)。"""
    sc = {k: s[k] for k in _SCINT_FIELDS}
    sc["sources"] = dict(s["sources"])
    sc["unverified"] = tuple(k for k in _SCINT_FIELDS if s[k] is None)
    for k in _SCINT_FIELDS:
        if s[k] is not None and k not in ("activator", "form") and k not in s["sources"]:
            raise SystemExit("%s: %s has a value but no source" % (s["name"], k))
    return {"density_kg_m3": float(s["density_g_cm3"]) * 1000.0, "scintillator": sc}


def _acoustic_properties(rho, c, alpha0, alpha_n, verified, source, uncertainty):
    """既存の超音波表を材料レコードへ移すためのキュレート済み物性。"""
    return {
        "density_kg_m3": float(rho),
        "sound_speed_longitudinal_m_s": float(c),
        "acoustic_attenuation_coefficient_np_per_m_hz_power": float(alpha0),
        "acoustic_attenuation_frequency_exponent": float(alpha_n),
        "acoustic_impedance_mrayl": float(rho * c / 1.0e6),
        "acoustic_verified": bool(verified),
        "acoustic_source": source,
        "acoustic_uncertainty": uncertainty,
    }


_WATER_ALPHA0 = 2.17e-3 / (20.0 / 2.302585092994046) * 100.0 / 1.0e12
CURATED_ACOUSTIC_PROPERTIES = {
    "WATER": _acoustic_properties(
        998.0, 1481.0, _WATER_ALPHA0, 2.0, True,
        "c = 1481 m/s at 20 C (Wikipedia 'Speed of sound', fresh water); rho = 998 kg/m3 "
        "lies between the tabulated 999.84 (0 C) and 997.05 (25 C) of Wikipedia "
        "'Properties of water' (interpolated, +-0.2 %%); attenuation 2.17e-3 dB/(cm MHz^2) "
        "(Szabo 2004 power law, as quoted beside Pinkerton 1949 in the open-source k-Wave "
        "attenuationWater help) = %.4g Np/(m Hz^2)" % _WATER_ALPHA0,
        "c and rho ~0.2 % (temperature: c moves ~3 m/s per K near 20 C); alpha ~10 %"),
    "SI": _acoustic_properties(
        2329.0, 8430.0, 0.0, 2.0, True,
        "[100] longitudinal V_L = sqrt(C11/rho) = 8.43e5 cm/s with C11 = 16.60e11 dyn/cm2 "
        "(McSkimin 1953) and rho = 2.329 g/cm3, Ioffe Institute NSM database 'Si - "
        "mechanical properties'. Attenuation NOT verified: set to 0 (assumption)",
        "c, rho < 1 % for [100]; [110]/[111] are 9.13e5 / 9.36e5 cm/s (anisotropy); "
        "attenuation unverified"),
    "SILICA": _acoustic_properties(
        2203.0, (71.7e9 * (1.0 - 0.17) / (2203.0 * (1.0 + 0.17) * (1.0 - 2.0 * 0.17))) ** 0.5,
        0.0, 2.0, True,
        "fused silica: rho = 2.203 g/cm3, E = 71.7 GPa, nu = 0.17 (Wikipedia 'Fused quartz'); "
        "c = sqrt(E(1-nu)/(rho(1+nu)(1-2nu))) computed here. Attenuation set to 0 (thin layers)",
        "bulk fused silica; deposited bonding oxides (PECVD, thermal) differ by an "
        "unverified amount - treat as representative"),
    "CU": _acoustic_properties(
        8935.0, ((140e9 + 4.0 * 48e9 / 3.0) / 8935.0) ** 0.5, 0.0, 1.0, True,
        "rho = 8.935 g/cm3 at 20 C, bulk modulus 140 GPa, shear modulus 48 GPa "
        "(Wikipedia 'Copper' infobox); c = sqrt((K + 4G/3)/rho) computed here. "
        "Attenuation set to 0 (micrometre layers)",
        "polycrystalline average; the same infobox gives E = 110-128 GPa, nu = 0.34, "
        "which spans c = 4.4-4.8 km/s - about +-5 %"),
    "AIR": _acoustic_properties(
        1.2041, 343.0, 0.0, 2.0, True,
        "c = 343 m/s and rho = 1.2041 kg/m3 at 20 C (Wikipedia 'Speed of sound'). "
        "Attenuation irrelevant for sub-micrometre gaps (set to 0)",
        "continuum value; a 0.1 um gap is comparable to the mean free path, but the "
        "echo is ~-1 for any gap above a few nm"),
    "POLYIMIDE": _acoustic_properties(
        1420.0, 2300.0, 1.0e-6, 1.0, False,
        "UNVERIFIED representative placeholder (no freely readable primary source was "
        "read). Pass allow_unverified=True and replace with your own measured values", "unknown"),
    "EPOXY_UNDERFILL": _acoustic_properties(
        1800.0, 2800.0, 2.0e-6, 1.0, False,
        "UNVERIFIED representative placeholder for a filled epoxy (no source read). Pass "
        "allow_unverified=True and replace with your own measured values", "unknown"),
}

_TAG = re.compile(r"<[^>]+>")


def _plain(s):
    if not s:
        return ""
    s = _TAG.sub("", str(s))
    return " ".join(s.split())


def _floats(s):
    return [float(v) for v in str(s).split()]


def _table(block):
    rows = []
    for line in str(block).strip().splitlines():
        vals = _floats(line)
        if vals:
            rows.append(tuple(vals))
    return rows


def _dataset(d):
    """RII の DATA 要素 1 つを ``{"type", "range_um", ...}`` にする。"""
    t = d["type"]
    if t.startswith("formula "):
        k = int(t.split()[1])
        if k not in (1, 2, 3, 4, 5, 6, 7, 8, 9):
            raise SystemExit("unsupported dispersion formula %r" % t)
        return {"type": "formula", "formula": k, "range_um": tuple(_floats(d["wavelength_range"])),
                "coefficients": tuple(_floats(d["coefficients"]))}
    if t == "tabulated nk":
        rows = _table(d["data"])
        return {"type": "nk", "range_um": (rows[0][0], rows[-1][0]), "rows": rows}
    if t == "tabulated n":
        rows = _table(d["data"])
        return {"type": "n", "range_um": (rows[0][0], rows[-1][0]), "rows": rows}
    if t == "tabulated k":
        rows = _table(d["data"])
        return {"type": "k", "range_um": (rows[0][0], rows[-1][0]), "rows": rows}
    raise SystemExit("unsupported DATA type %r" % t)


def _props(p):
    out = {}
    if not p:
        return out
    for key in ("nd", "Vd", "dPgF", "glass_code", "glass_status"):
        if key in p:
            out[key] = p[key]
    if "density" in p:
        v = p["density"]
        if isinstance(v, list):
            v = v[0].get("value")
        out["density_kg_m3"] = float(v)
    if "thermal_expansion" in p:
        te = p["thermal_expansion"]
        if isinstance(te, list):
            te = te[0]
        out["thermal_expansion_per_k"] = float(te["value"])
        if "temperature_range" in te:
            out["thermal_expansion_range_k"] = tuple(_floats(te["temperature_range"]))
    if "thermal_dispersion" in p:
        td = p["thermal_dispersion"]
        if isinstance(td, list):
            td = td[0]
        if td.get("type") == "formula A":
            out["dn_dt_formula_a"] = tuple(_floats(td["coefficients"]))
    return out


def build(rii_dir):
    data_dir = os.path.join(rii_dir, "data")
    recs = []
    for name, cls, pages, aliases in SELECTION + [(s["name"], s["class"], s["pages"], s["aliases"])
                                                 for s in SCINTILLATORS]:
        datasets = []
        props = {}
        cites = []
        for entry in pages:
            rel, note = entry[0], entry[1]
            only = entry[2] if len(entry) > 2 else None
            path = os.path.join(data_dir, rel)
            with io.open(path, encoding="utf-8") as f:
                head = f.read()
            if "CC0 1.0" not in head[:400]:
                raise SystemExit("%s: no CC0 waiver in the header" % rel)
            y = yaml.safe_load(head)
            for d in y["DATA"]:
                try:
                    ds = _dataset(d)
                except SystemExit as exc:
                    raise SystemExit("%s: %s" % (rel, exc))
                if only == "k":
                    # ★k だけを取る区間(n は次の出典のまま)。2026-10-15: RII の Hale & Querry の水は NIR を
                    # 0.2 µm おきにしか持たず、1.45 / 1.94 µm の吸収帯を線形補間で 1/3 に潰していた。n は滑らか
                    # なので Hale のまま、k だけ Segelstein 1981(同じ研究室の続き、細かい刻み)から取る。
                    if ds["type"] != "nk":
                        raise SystemExit("%s: k-only entry needs tabulated nk data" % rel)
                    ds = {"type": "k", "range_um": ds["range_um"], "rows": tuple((r[0], r[2]) for r in ds["rows"])}
                ds["page"] = rel
                ds["reference"] = _plain(y.get("REFERENCES"))
                if note:
                    ds["note"] = note
                cond = y.get("CONDITIONS") or {}
                if "temperature" in cond:
                    ds["temperature_k"] = float(cond["temperature"])
                datasets.append(ds)
            props.update(_props(y.get("PROPERTIES")))
            cites.append(_plain(y.get("REFERENCES")))
        props.update(CURATED_ACOUSTIC_PROPERTIES.get(name, {}))
        if name in _SCINT_BY_NAME:
            props.update(_scintillator_properties(_SCINT_BY_NAME[name]))
        recs.append({"name": name, "class": cls, "aliases": tuple(aliases), "datasets": datasets,
                     "properties": props})
    recs.extend([
        {"name": "AIR", "class": "gas", "aliases": (), "datasets": [],
         "properties": CURATED_ACOUSTIC_PROPERTIES["AIR"]},
        {"name": "POLYIMIDE", "class": "polymer", "aliases": (), "datasets": [],
         "properties": CURATED_ACOUSTIC_PROPERTIES["POLYIMIDE"]},
        {"name": "EPOXY_UNDERFILL", "class": "composite", "aliases": ("UNDERFILL",), "datasets": [],
         "properties": CURATED_ACOUSTIC_PROPERTIES["EPOXY_UNDERFILL"]},
    ])
    return recs


def _fmt(v, indent=0):
    pad = " " * indent
    if isinstance(v, dict):
        items = []
        for k, x in v.items():
            items.append("%s    %r: %s" % (pad, k, _fmt(x, indent + 4)))
        return "{\n" + ",\n".join(items) + "\n" + pad + "}"
    if isinstance(v, (list, tuple)) and v and isinstance(v[0], (list, tuple)):
        # 数表: 1 行 1 点
        lines = [pad + "    " + repr(tuple(r)) for r in v]
        return "(\n" + ",\n".join(lines) + ",\n" + pad + ")"
    if isinstance(v, list):
        return "[" + ", ".join(_fmt(x, indent + 4) for x in v) + "]" if not any(isinstance(x, dict) for x in v) \
            else "[\n" + ",\n".join(pad + "    " + _fmt(x, indent + 4) for x in v) + ",\n" + pad + "]"
    return repr(v)


HEADER = '''# -*- coding: utf-8 -*-
# GENERATED by tools/gen_material_tables.py from the refractiveindex.info database
# (CC0 1.0 — "copyright and related rights waived", each source page carries the waiver
# in its header). Cite: M. N. Polyanskiy, "Refractiveindex.info database of optical
# constants", Sci. Data 11, 94 (2024), https://doi.org/10.1038/s41597-023-02898-2.
# Do not edit by hand: re-run the generator with --rii <database dir>.
#
# 1 record = 1 material. ``datasets`` は波長区間ごとの一次文献(formula = 分散式、
# nk / n / k = 数表、λ は µm)。``properties`` は硝材カタログの公表値(nd / Vd / 密度 /
# 熱膨張 / dn/dT の式 A の係数)。消費側は ``materials.py``。
"""Material optical-constant records generated from the refractiveindex.info database (CC0)."""

MATERIAL_RECORDS = '''


def render(recs):
    return HEADER + _fmt(recs) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--rii", default=os.environ.get("FULLSEYE_RII_DIR"), help="RII database/ directory")
    ap.add_argument("--out", default="materials_data.py")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    if not a.rii or not os.path.isfile(os.path.join(a.rii, "catalog-nk.yml")):
        sys.exit("--rii must point at the RII database/ directory (catalog-nk.yml not found)")
    text = render(build(a.rii))
    if a.check:
        with io.open(a.out, encoding="utf-8", newline="") as f:
            cur = f.read().replace("\r\n", "\n")
        if cur != text:
            sys.exit("%s differs from the generator output" % a.out)
        print("ok %s matches the RII database" % a.out)
        return 0
    with io.open(a.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("wrote %s (%d records, %d bytes)" % (a.out, text.count("'name':"), len(text.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
