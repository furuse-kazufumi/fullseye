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
``tests/test_materials.py`` が 550 nm の反射率を別の測定の表の値と突き合わせる。
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
    ("GE", "semiconductor", [("main/Ge/nk/Amotchkina.yml", ""), ("main/Ge/nk/Burnett.yml", "")], ["GERMANIUM"]),
    ("GAAS", "semiconductor", [("main/GaAs/nk/Aspnes.yml", ""), ("main/GaAs/nk/Skauli.yml", "")], []),
    ("GAN", "semiconductor", [("main/GaN/nk/Barker-o.yml", "ordinary ray")], []),
    ("INP", "semiconductor", [("main/InP/nk/Aspnes.yml", "")], []),
    ("SIC", "semiconductor", [("main/SiC/nk/Singh-o.yml", "6H, ordinary ray"), ("main/SiC/nk/Larruquert.yml", "")], []),
    # 膜
    ("SI3N4", "film", [("main/Si3N4/nk/Luke.yml", "")], ["SILICON_NITRIDE"]),
    ("TIO2", "film", [("main/TiO2/nk/Devore-o.yml", "rutile, ordinary ray")], []),
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
    ("WATER", "liquid", [("main/H2O/nk/Daimon-20.0C.yml", "20 C, visible"), ("main/H2O/nk/Hale.yml", "25 C, 0.2-200 um")], ["H2O"]),
    # プラスチック
    ("PMMA", "polymer", [("organic/(C5H8O2)n - poly(methyl methacrylate)/nk/Sultanova.yml", "")], ["ACRYLIC"]),
    ("POLYCARBONATE", "polymer", [("organic/(C16H14O3)n - polycarbonate/nk/Sultanova.yml", "")], ["PC"]),
    ("POLYSTYRENE", "polymer", [("organic/(C8H8)n - polystyrene/nk/Sultanova.yml", "")], ["PS"]),
    ("ZEONEX_E48R", "polymer", [("other/commercial polymers/ZeonexE48R/nk/Sultanova.yml", "cyclo-olefin polymer")], ["COP"]),
]

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
    for name, cls, pages, aliases in SELECTION:
        datasets = []
        props = {}
        cites = []
        for rel, note in pages:
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
        recs.append({"name": name, "class": cls, "aliases": tuple(aliases), "datasets": datasets,
                     "properties": props})
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
