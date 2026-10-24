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
にして ``unverified`` に名前を並べる(推測で埋めない)。2026-10-24 から、光収率の幅(文献のばらつきの理由を
読んだ材料だけ)と、発光の形を成分の並び(中心・エネルギー軸の FWHM・重み・測定配置・励起の種類、
成分ごとの出典と「図から読み取り」の印)で持つ。屈折率の表が RII にある材料(CsI / NaI /
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
# シンチレータ・蛍光体の発光の列(2026-10-23、発光の形と光収率の幅は 2026-10-24)  #
# --------------------------------------------------------------------------- #
# 値は一次情報を読んで写した定数(RII の表ではない)。1 値 1 出典で ``sources`` に残す。
#   PDG  = Particle Data Group, S. Navas et al., Phys. Rev. D 110, 030001 (2024), review "Particle detectors at
#          accelerators", Table 35.4 "Properties of several inorganic crystals"(密度・減衰時間・発光の極大・
#          極大での屈折率。光収率は NaI(Tl) を 100 とする相対値なので絶対値には使わない)。
#   LBNL = Berkeley Lab "Inorganic Scintillator Library"(https://scintillator.lbl.gov/inorganic-scintillator-library/、
#          公開の csv を 2026-10-23 に読んだ。SHA-256 6085c865…940a)。行ごとに原著の略号(Sakai1987 など)がある。
#          光収率 [photons/MeV] はここから取り、どの行かを書く。
#
# ★光収率の幅(``light_yield_range_photons_per_mev``、2026-10-24): 文献の値のばらつきが「何の違い」から来るかを
#   読んだ材料だけに (下限, 上限) を入れる(CdWO4 と LYSO)。それ以外は ``None``(幅が無いのではなく、確かめていない)。
#   CdWO4 の 7,800〜15,800 という低い値の多くは、減衰 13 µs に対して整形時間が短い(1 µs では光の 2〜3 割しか
#   拾わない)ことと、光電子数 phe/MeV(光検出器の QE と光の集め方を掛けた後)を光子数 ph/MeV と混ぜたことによる。
#   こうした値は幅に入れない —— 幅は「絶対値として測った値」どうしの違いだけにする。
#
# ★発光の形(``emission_components``、2026-10-24): 室温・X 線/γ 線励起で FWHM を**数値で**書いた一次文献は
#   見つからなかった。幅は全部、一次文献の図から読み取った値で、成分ごとに ``digitized_from_figure`` の印を付ける。
#   1 成分 = 中心 [nm]・FWHM [eV](``None`` は線)・積分の重み・測定配置(``surface`` = 励起した面から出る光 /
#   ``thick_crystal_transmission`` = 厚い結晶の中を通って出てくる光)・励起の種類(``xray`` / ``gamma`` / ``uv``)・
#   出典。ガウスは**エネルギー軸**の形(Ce³⁺・自己束縛励起子の帯はエネルギーで対称)で、波長軸へは消費側
#   (``dualxray.scintillator_sensor_qe``)がヤコビアン hc/λ² を掛けて移す。同じ測定配置の成分の重みの和は 1。
#   ★``center_nm`` はエネルギー軸の中心(hc/E_c)。波長軸の山はヤコビアンで数 nm 短波長に出る(BGO 480 → 468 nm)。
#   図の「極大」は波長軸で読んだ値なので、厳密には中心をやや長波長に置くべきかもしれない —— 差は Q̄ で 1.4 % 以内
#   (2026-10-24 に計算)で、調査で承認された値(中心 = 公表の極大)をそのまま使う。
#   幅の分からない材料(CsI:Tl / NaI:Tl)は ``None`` のまま —— 消費側は発光の極大の 1 本の線として扱い、そう
#   返り値に書く(幅を推測で入れない)。実測の発光スペクトルがあれば ``emission_spectrum=`` で渡す
#   (CsI:Tl は 2.25 / 2.55 eV の 2 帯だと分かっているが、幅と強度比を確かめられなかった)。
_PDG_2024 = ("Particle Data Group, S. Navas et al., Phys. Rev. D 110, 030001 (2024), review 35 'Particle detectors "
             "at accelerators', Table 35.4")
_LBNL = ("Berkeley Lab Inorganic Scintillator Library, https://scintillator.lbl.gov/inorganic-scintillator-library/ "
         "(csv read 2026-10-23), row ")
_DEHAAS_2008 = ("J. T. M. de Haas and P. Dorenbos, IEEE Trans. Nucl. Sci. 55, 1086 (2008), doi:10.1109/TNS.2008.922819, "
                "Table II")
_MAO_2008 = ("R. Mao, L. Zhang and R.-Y. Zhu, IEEE Trans. Nucl. Sci. 55, 1759 (2008), Figs. 7-8")
_GOS_JIM_2023 = ("J. Inorg. Mater. 38 (2023), doi:10.15541/jim20220542, Fig. 5(a) (commercial Gd2O2S:Tb powder, "
                 "X-ray 75 kV); integrated shares read from the digitized figure")

SCINTILLATORS = [
    {"name": "CSI:TL", "class": "crystal", "aliases": ["CSI(TL)", "CSI_TL"],
     "pages": [("main/CsI/nk/Li.yml", "undoped CsI; the Tl activator (~0.1 %) is not resolved in n")],
     "activator": "Tl+", "form": "single crystal", "xray_material": "CSI",
     "density_g_cm3": 4.51, "light_yield_photons_per_mev": 56000.0, "light_yield_range_photons_per_mev": None,
     "decay_time_ns": 1220.0, "emission_peak_nm": 550.0, "emission_components": None,
     "refractive_index_at_peak": 1.79,
     "sources": {"density_g_cm3": _PDG_2024, "decay_time_ns": _PDG_2024, "emission_peak_nm": _PDG_2024,
                 "refractive_index_at_peak": _PDG_2024,
                 "light_yield_photons_per_mev": _LBNL + "Sakai1987 (56,000; deHaas2005 and dehaas2008 also 56,000)",
                 "xray_material": "NIST SRD 126 compound table 'Cesium Iodide' (Tl neglected)"}},
    {"name": "NAI:TL", "class": "crystal", "aliases": ["NAI(TL)", "NAI_TL"],
     "pages": [("main/NaI/nk/Li.yml", "undoped NaI; the Tl activator is not resolved in n")],
     "activator": "Tl+", "form": "single crystal", "xray_material": "NaI",
     "density_g_cm3": 3.67, "light_yield_photons_per_mev": 45000.0, "light_yield_range_photons_per_mev": None,
     "decay_time_ns": 245.0, "emission_peak_nm": 410.0, "emission_components": None,
     "refractive_index_at_peak": 1.85,
     "sources": {"density_g_cm3": _PDG_2024, "decay_time_ns": _PDG_2024, "emission_peak_nm": _PDG_2024,
                 "refractive_index_at_peak": _PDG_2024,
                 "light_yield_photons_per_mev": _LBNL + "Sakai1987 (45,000; dehaas2008 also 45,000)",
                 "xray_material": "chemical formula NaI, mixture rule over NIST SRD 126 (Tl neglected)"}},
    {"name": "BI4GE3O12", "class": "crystal", "aliases": ["BGO"],
     "pages": [("main/Bi4Ge3O12/nk/Williams.yml", "")],
     "activator": "Bi3+ (intrinsic)", "form": "single crystal", "xray_material": "Bi4Ge3O12",
     "density_g_cm3": 7.13, "light_yield_photons_per_mev": 8500.0, "light_yield_range_photons_per_mev": None,
     "decay_time_ns": 300.0, "emission_peak_nm": 480.0,
     "emission_components": (
         {"geometry": "surface", "excitation": "uv", "center_nm": 480.0, "fwhm_ev": 0.70, "weight": 1.0,
          "digitized_from_figure": True,
          "source": "M. Itoh and T. Katagiri, J. Phys. Soc. Jpn., 'Intrinsic luminescence from self-trapped excitons in "
                    "Bi4Ge3O12 and Bi12GeO20', Fig. 2 (300 K, 150 nm excitation, light from the sample surface): one "
                    "Gaussian in energy, FWHM 0.70 eV read from the figure; the 90 kVp X-ray spectrum of "
                    "H. V. Piltingsrud, J. Nucl. Med. 20, 1279 (1979), Table 2 peaks at the same place"},),
     "refractive_index_at_peak": 2.15,
     "sources": {"density_g_cm3": _PDG_2024, "decay_time_ns": _PDG_2024, "emission_peak_nm": _PDG_2024,
                 "refractive_index_at_peak": _PDG_2024,
                 "light_yield_photons_per_mev": _LBNL + "Moszynski1997a (8,500; the room-temperature rows span "
                                                "7,100-10,600)",
                 "emission_components": "one Gaussian, read from a figure (see the component)",
                 "xray_material": "chemical formula Bi4Ge3O12, mixture rule over NIST SRD 126"}},
    {"name": "LU2SIO5:CE", "class": "crystal", "aliases": ["LSO", "LSO:CE", "LU2SIO5(CE)"],
     "pages": [],
     "activator": "Ce3+", "form": "single crystal", "xray_material": "Lu2SiO5",
     "density_g_cm3": 7.40, "light_yield_photons_per_mev": 27000.0, "light_yield_range_photons_per_mev": None,
     "decay_time_ns": 40.0, "emission_peak_nm": 402.0,
     "emission_components": (
         {"geometry": "surface", "excitation": "uv", "center_nm": 402.0, "fwhm_ev": 0.50, "weight": 1.0,
          "digitized_from_figure": True,
          "source": _MAO_2008 + ": UV-excited emission taken from the excited surface, peak 402 nm, FWHM 0.50 eV "
                                "read from the figure"},
         {"geometry": "thick_crystal_transmission", "excitation": "gamma", "center_nm": 453.0, "fwhm_ev": 0.63,
          "weight": 1.0, "digitized_from_figure": True,
          "source": _MAO_2008 + ": gamma-excited emission after passing through a long crystal - the blue side is "
                                "re-absorbed by Ce3+ (self-absorption) and the peak moves to 430-453 nm depending on "
                                "the sample; 453 nm and FWHM 0.63 eV read from the figure"}),
     "refractive_index_at_peak": 1.82,
     "sources": {"density_g_cm3": _PDG_2024, "decay_time_ns": _PDG_2024, "emission_peak_nm": _PDG_2024,
                 "refractive_index_at_peak": _PDG_2024,
                 "light_yield_photons_per_mev": _LBNL + "Melcher1996 (27,000; the rows span 22,200-33,000 with "
                                                "Ce content; " + _DEHAAS_2008 + " agrees)",
                 "emission_components": "one Gaussian per geometry, read from figures (see the components)",
                 "xray_material": "chemical formula Lu2SiO5, mixture rule over NIST SRD 126 (Ce neglected)"}},
    {"name": "LU1.8Y0.2SIO5:CE", "class": "crystal", "aliases": ["LYSO", "LYSO:CE"],
     "pages": [],
     "activator": "Ce3+", "form": "single crystal", "xray_material": "Lu1.8Y0.2SiO5",
     "density_g_cm3": 7.1, "light_yield_photons_per_mev": 27000.0,
     "light_yield_range_photons_per_mev": (26000.0, 27000.0),
     "decay_time_ns": 41.0, "emission_peak_nm": 397.0,
     "emission_components": (
         {"geometry": "surface", "excitation": "xray", "center_nm": 397.0, "fwhm_ev": 0.43, "weight": 0.5,
          "digitized_from_figure": True, "weight_assumed": True,
          "source": "L. Pidol et al. 2007 (hal-02423145), Table 2 (emission 397/427 nm, the two Ce3+ 5d-4f bands) and "
                    "Fig. 2 (X-ray excitation, room temperature): FWHM 0.37-0.50 eV read from figures, 0.43 eV used; "
                    "the intensity ratio of the two bands is not verified - 1:1 is an assumption"},
         {"geometry": "surface", "excitation": "xray", "center_nm": 427.0, "fwhm_ev": 0.43, "weight": 0.5,
          "digitized_from_figure": True, "weight_assumed": True,
          "source": "L. Pidol et al. 2007 (hal-02423145), Table 2 / Fig. 2 (as the 397 nm band; ratio assumed 1:1)"}),
     "refractive_index_at_peak": None,
     "sources": {"density_g_cm3": _LBNL + "Pidol2004",
                 "light_yield_photons_per_mev": _DEHAAS_2008 + " (APD 26,000 / PD 27,000 ph/MeV, 10 us shaping; the "
                                                "Lu:Y ratio of the measured sample is not stated). The earlier "
                                                + _LBNL + "Pidol2004 value 34,000 is not used",
                 "light_yield_range_photons_per_mev": _DEHAAS_2008 + ": the APD and PD readings of the same crystal "
                                                      "(26,000 and 27,000)",
                 "decay_time_ns": _LBNL + "Pidol2004 ('41 + slow': the fast component; a slow tail is not given)",
                 "emission_peak_nm": _LBNL + "Pidol2004",
                 "emission_components": "two Gaussians, widths read from figures, ratio assumed (see the components)",
                 "xray_material": "chemical formula Lu1.8Y0.2SiO5, mixture rule over NIST SRD 126 (Ce neglected)"}},
    {"name": "CDWO4", "class": "crystal", "aliases": [],
     "pages": [],
     "activator": "self-activated", "form": "single crystal", "xray_material": "CdWO4",
     "density_g_cm3": 7.9, "light_yield_photons_per_mev": 27000.0,
     "light_yield_range_photons_per_mev": (20000.0, 28000.0),
     "decay_time_ns": 12000.0, "emission_peak_nm": 480.0,
     "emission_components": (
         {"geometry": "thick_crystal_transmission", "excitation": "gamma", "center_nm": 480.0, "fwhm_ev": 0.58,
          "weight": 1.0, "digitized_from_figure": True,
          "source": "L. Bardelli et al., Nucl. Instrum. Meth. A 569, 743 (2006), arXiv:nucl-ex/0608004, Table 1 "
                    "(emission maximum 480 nm) and Fig. 6a (60Co gamma, crystal 42 mm diameter x 25 mm): one "
                    "Gaussian in energy, FWHM 0.58 eV read from the figure; the weak long-wavelength tail is "
                    "neglected"},),
     "refractive_index_at_peak": None,
     "sources": {"density_g_cm3": _LBNL + "Moszynski2005",
                 "light_yield_photons_per_mev":
                     "M. Moszynski et al., IEEE Trans. Nucl. Sci. 52, 3124 (2005) (abstract: 6,500 +- 200 phe/MeV, "
                     "10x10x3 mm) -> 27,400 ph/MeV as tabulated in V. B. Mikhailik and H. Kraus, arXiv:1001.5461 "
                     "(2010), Table 2; P. Dorenbos et al., IEEE Trans. Nucl. Sci. 42, 2190 (1995), Table I ~28,000 "
                     "(estimate); R. Holl et al., IEEE Trans. Nucl. Sci. 35, 105 (1988), Si photodiode absolute "
                     "20,000. Lower published values (7,800-15,800) mostly come from shaping times short against "
                     "the 13 us decay and from quoting photoelectrons (phe/MeV) as photons",
                 "light_yield_range_photons_per_mev": "absolute measurements only: Holl 1988 (20,000) to Dorenbos 1995 "
                                                      "(~28,000); see light_yield_photons_per_mev",
                 "decay_time_ns": _LBNL + "Moszynski2005",
                 "emission_peak_nm": "L. Bardelli et al., Nucl. Instrum. Meth. A 569, 743 (2006), "
                                     "arXiv:nucl-ex/0608004, Table 1 (480 nm; the 495 nm of the Moszynski2005 row is "
                                     "the outlier)",
                 "emission_components": "one Gaussian, read from a figure (see the component)",
                 "xray_material": "chemical formula CdWO4, mixture rule over NIST SRD 126"}},
    {"name": "GD2O2S:TB", "class": "crystal", "aliases": ["GOS:TB", "GD2O2S(TB)"],
     "pages": [],
     "activator": "Tb3+", "form": "powder phosphor / ceramic", "xray_material": "GOS",
     "density_g_cm3": 7.44, "light_yield_photons_per_mev": None, "light_yield_range_photons_per_mev": None,
     "decay_time_ns": 638000.0, "emission_peak_nm": 545.0,
     # Tb³⁺ の 4f-4f の線の束(各線の幅 ≲ 10 nm は Si の QE の変化に比べて細いので線として持つ)。⁵D₃ 群の割合は
     # Tb の濃度で変わる(濃いと ⁵D₃ → ⁵D₄ の交差緩和で減る)—— 市販の粉末 1 つの値。
     "emission_components": tuple(
         {"geometry": "surface", "excitation": "xray", "center_nm": c, "fwhm_ev": None, "weight": w,
          "digitized_from_figure": True, "source": _GOS_JIM_2023 + " (" + lab + ")"}
         for c, w, lab in ((411.0, 0.10, "5D3 group 380-460 nm, centroid 411 nm, ~10 %; depends on the Tb content"),
                           (490.0, 0.12, "5D4 -> 7F6, ~12 %"), (545.0, 0.53, "5D4 -> 7F5, ~53 %"),
                           (587.0, 0.13, "5D4 -> 7F4, ~13 %"), (620.0, 0.08, "5D4 -> 7F3, ~8 %"),
                           (667.0, 0.04, "5D4 -> 7F2..0, centroid 667 nm, ~4 %"))),
     "refractive_index_at_peak": None,
     "sources": {"density_g_cm3": "NIST SRD 126 Table 2 'Gadolinium Oxysulfide' (bulk; a powder screen is less dense)",
                 "decay_time_ns": "B. Tang et al., Molecules 28, 1815 (2023), doi:10.3390/molecules28041815, Table 1 "
                                  "(x = 0: 638 us; photoluminescence lifetime of Tb3+ under 293-298 nm excitation, "
                                  "not X-ray)",
                 "emission_peak_nm": "B. Tang et al., Molecules 28, 1815 (2023): strongest line 545 nm (5D4 -> 7F5); "
                                     "further lines at 494 / 589 / 623 nm (a line spectrum, not one band)",
                 "emission_components": "a bundle of six lines (weights read from a figure, see the components)",
                 "xray_material": "NIST SRD 126 compound table 'Gadolinium Oxysulfide' (Tb neglected)"}},
]
_SCINT_FIELDS = ("activator", "form", "xray_material", "density_g_cm3", "light_yield_photons_per_mev",
                 "light_yield_range_photons_per_mev", "decay_time_ns", "emission_peak_nm", "emission_components",
                 "refractive_index_at_peak")
_SCINT_BY_NAME = {s["name"]: s for s in SCINTILLATORS}
#: 発光の成分の測定配置と励起の種類(これ以外の語は生成を止める)。表の既定の配置は ``surface``(あれば)。
EMISSION_GEOMETRIES = ("surface", "thick_crystal_transmission")
EMISSION_EXCITATIONS = ("xray", "gamma", "uv")
_COMPONENT_KEYS = {"geometry", "excitation", "center_nm", "fwhm_ev", "weight", "digitized_from_figure", "source",
                   "weight_assumed"}


def _check_components(name, comps):
    """発光の成分の並びを検める(配置・励起の語、中心と幅が正、配置ごとの重みの和が 1、出典が空でない)。"""
    if not isinstance(comps, tuple) or not comps:
        raise SystemExit("%s: emission_components must be a non-empty tuple or None" % name)
    sums = {}
    for c in comps:
        if set(c) - _COMPONENT_KEYS or not {"geometry", "excitation", "center_nm", "fwhm_ev", "weight",
                                             "digitized_from_figure", "source"} <= set(c):
            raise SystemExit("%s: bad emission component keys %s" % (name, sorted(c)))
        if c["geometry"] not in EMISSION_GEOMETRIES or c["excitation"] not in EMISSION_EXCITATIONS:
            raise SystemExit("%s: unknown geometry/excitation %r/%r" % (name, c["geometry"], c["excitation"]))
        if not (c["center_nm"] > 0.0 and c["weight"] > 0.0) or (c["fwhm_ev"] is not None and not c["fwhm_ev"] > 0.0):
            raise SystemExit("%s: emission component needs centre > 0, weight > 0, FWHM > 0 or None" % name)
        if not c["source"] or not isinstance(c["digitized_from_figure"], bool):
            raise SystemExit("%s: emission component needs a source and a digitized_from_figure flag" % name)
        sums[c["geometry"]] = sums.get(c["geometry"], 0.0) + c["weight"]
    for g, s in sums.items():
        if abs(s - 1.0) > 1e-9:
            raise SystemExit("%s: emission weights of geometry %s sum to %r (need 1)" % (name, g, s))
    return tuple(dict(c) for c in comps), ("surface" if "surface" in sums else comps[0]["geometry"])


def _scintillator_properties(s):
    """SCINTILLATORS の 1 行 → レコードの ``properties``(密度は kg/m³ にも、発光の列は ``scintillator`` に)。"""
    sc = {k: s[k] for k in _SCINT_FIELDS}
    sc["sources"] = dict(s["sources"])
    sc["unverified"] = tuple(k for k in _SCINT_FIELDS if s[k] is None)
    for k in _SCINT_FIELDS:
        if s[k] is not None and k not in ("activator", "form") and k not in s["sources"]:
            raise SystemExit("%s: %s has a value but no source" % (s["name"], k))
    rng = s["light_yield_range_photons_per_mev"]
    if rng is not None:
        lo, hi = rng
        y = s["light_yield_photons_per_mev"]
        if y is None or not (0.0 < lo <= y <= hi):
            raise SystemExit("%s: light-yield range %r must bracket the value %r" % (s["name"], rng, y))
        sc["light_yield_range_photons_per_mev"] = (float(lo), float(hi))
    sc["emission_default_geometry"] = None
    if s["emission_components"] is not None:
        sc["emission_components"], sc["emission_default_geometry"] = _check_components(s["name"],
                                                                                       s["emission_components"])
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
    if isinstance(v, tuple) and v and all(isinstance(x, dict) for x in v):
        # 辞書の並び(シンチレータの発光の成分): 1 成分 1 塊
        return "(\n" + ",\n".join(pad + "    " + _fmt(x, indent + 4) for x in v) + ",\n" + pad + ")"
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
