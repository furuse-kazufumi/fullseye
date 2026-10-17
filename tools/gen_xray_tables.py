# -*- coding: utf-8 -*-
"""NIST の X 線質量減衰係数の表(Hubbell & Seltzer、SRD 126)から ``materials_xray_data.py`` を作る。

使い方::

    py -3.11 -I tools/gen_xray_tables.py --nist <dir> [--out materials_xray_data.py] [--check]

``<dir>`` は NIST の公開ページを手で保存したディレクトリ::

    <dir>/tab1.html            元素の Z/A・I・密度(Table 1)
    <dir>/tab2.html            化合物・混合物の組成(質量分率、Table 2。人体組織は ICRU 44)
    <dir>/elem/zNN.html        元素の μ/ρ・μ_en/ρ(Table 3、ElemTab/zNN.html)
    <dir>/comp/<page>.html     化合物の μ/ρ・μ_en/ρ(Table 4、ComTab/<page>.html)

取得元は https://physics.nist.gov/PhysRefData/XrayMassCoef/ (ログイン不要)。
``--check`` は生成結果を既存ファイルと比べ、違えば exit 1(手で書き換えた痕跡を見つける)。

**何を同梱するか(2026-10-15)**: NIST の標準参照データ(SRD)は Standard Reference Data Act
(15 U.S.C. 290e)により米国商務長官の著作権の表示がある。数値そのものは測定・計算の事実なので、
**X 線検査で使う元素 49 種と化合物 21 種、1 keV〜1 MeV の行だけ**を、出典の表示つきで同梱する
(全 92 元素・48 化合物・1 keV〜100 GeV の表は同梱しない)。全体が要る使い方は、ユーザーが
NIST のページを読むか、xraylib(BSD-3)を optional で入れる。

数値は HTML の文字列をそのまま float にする(手で写さない)。エネルギーは MeV → keV に直す
(×1000、表の有効数字 6 桁はそのまま残る)。吸収端の行は NIST と同じく同じエネルギーで 2 行
(端の下と上)あり、上の行に端の名前(K / L1 / …)をつける。
"""
from __future__ import annotations

import argparse
import html
import os
import re
import sys

# 同梱する化合物: (NIST のページ名, Table 2 の名前, fullseye のキー, 一言)
COMPOUNDS = [
    ("water", 'Water, Liquid', "WATER", "水(液体)"),
    ("air", 'Air, Dry (near sea level)', "AIR", "乾燥空気 —— 空気カーマ(線質の半価層)の重み"),
    ("muscle", 'Muscle, Skeletal (ICRU-44)', "MUSCLE_ICRU44", "骨格筋(ICRU 44)—— 食肉の赤身の代表"),
    ("adipose", 'Adipose Tissue (ICRU-44)', "ADIPOSE_ICRU44", "脂肪組織(ICRU 44)—— 食肉の脂身の代表"),
    ("tissue", 'Tissue, Soft (ICRU-44)', "SOFT_TISSUE_ICRU44", "軟部組織(ICRU 44)"),
    ("breast", 'Breast Tissue (ICRU-44)', "BREAST_ICRU44", "乳腺組織(ICRU 44)"),
    ("bone", 'Bone, Cortical (ICRU-44)', "BONE_CORTICAL_ICRU44", "皮質骨(ICRU 44)—— 骨片の代表"),
    ("b100", 'B-100 Bone-Equivalent Plastic', "B100_BONE_PLASTIC", "骨等価プラスチック B-100"),
    ("polyethylene", 'Polyethylene', "POLYETHYLENE", "ポリエチレン"),
    ("pmma", 'Polymethyl Methacrylate', "PMMA", "ポリメタクリル酸メチル"),
    ("polystyrene", 'Polystyrene', "POLYSTYRENE", "ポリスチレン"),
    ("polyvinyl", 'Polyvinyl Chloride', "PVC", "ポリ塩化ビニル"),
    ("teflon", 'Polytetrafluoroethylene, (Teflon)', "PTFE", "ポリテトラフルオロエチレン"),
    ("mylar", 'Polyethylene Terephthalate, (Mylar)', "PET", "ポリエチレンテレフタラート"),
    ("pyrex", 'Glass, Borosilicate (Pyrex)', "BOROSILICATE_GLASS", "ホウケイ酸ガラス"),
    ("glass", 'Glass, Lead', "LEAD_GLASS", "鉛ガラス"),
    ("concrete", 'Concrete, Ordinary', "CONCRETE", "普通コンクリート —— 石の代表"),
    ("cesium", 'Cesium Iodide', "CSI", "ヨウ化セシウム(シンチレータ)"),
    ("gadolinium", 'Gadolinium Oxysulfide', "GOS", "ガドリニウムオキシ硫化物(シンチレータ)"),
    ("telluride", 'Cadmium Telluride', "CDTE", "テルル化カドミウム(直接変換の検出器)"),
    ("gallium", 'Gallium Arsenide', "GAAS", "ヒ化ガリウム"),
]

E_MAX_KEV = 1000.0
SOURCE = ("J. H. Hubbell and S. M. Seltzer, Tables of X-Ray Mass Attenuation Coefficients and Mass "
          "Energy-Absorption Coefficients (version 1.4), NIST Standard Reference Database 126 (2004), "
          "https://physics.nist.gov/xaamdi, doi:10.18434/T4D01F. Human-tissue compositions: ICRU Report 44 (1989).")
NOTICE = ("NIST Standard Reference Data, (c) U.S. Secretary of Commerce on behalf of the United States "
          "(15 U.S.C. 290e). A small subset (49 elements, 21 materials, 1 keV - 1 MeV) is reproduced "
          "with attribution; the full tables are at the URL above.")

_NUM = re.compile(r"^[0-9]+\.[0-9]+E[+-][0-9]+$")
_EDGE = re.compile(r"^(K|L[123]|M[1-5]|N[1-7])$")


def _text(path):
    with open(path, encoding="latin-1") as fh:
        raw = fh.read()
    raw = re.sub(r"(?is)<script.*?</script>", " ", raw)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return html.unescape(raw).replace("\xa0", " ")


def parse_table(path):
    """μ/ρ のページから ((E_keV, mu_rho, muen_rho, edge), ...) を読む。"""
    txt = _text(path)
    # 表は最後の「(cm2/g)」見出しの後ろ(化合物のページは図の説明が前にある)
    idx = [m.end() for m in re.finditer(r"\(cm\s*2\s*/g\)", txt)]
    if len(idx) < 2:
        raise SystemExit("%s: table header not found" % path)
    toks = txt[idx[-1]:].split()
    rows, label, nums = [], "", []
    for t in toks:
        if _EDGE.match(t) and not nums:
            label = t
            continue
        if _NUM.match(t):
            nums.append(float(t))
            if len(nums) == 3:
                e_kev = round(nums[0] * 1000.0, 6)
                rows.append((e_kev, nums[1], nums[2], label))
                label, nums = "", []
            continue
        if rows and t.lower().startswith(("back", "table", "nist")):
            break
    if len(rows) < 30:
        raise SystemExit("%s: only %d rows parsed" % (path, len(rows)))
    es = [r[0] for r in rows]
    if any(b < a for a, b in zip(es, es[1:])):
        raise SystemExit("%s: energies not monotone" % path)
    return tuple(r for r in rows if r[0] <= E_MAX_KEV * (1 + 1e-9))


def parse_tab1(path):
    """Table 1 → {Z: (symbol, name, Z/A, I eV, density)}。"""
    toks = _text(path).split()
    out = {}
    i = 0
    while i < len(toks):
        t = toks[i]
        if t.isdigit() and 1 <= int(t) <= 92 and i + 1 < len(toks) and re.match(r"^[A-Z][a-z]?$", toks[i + 1]):
            z, sym = int(t), toks[i + 1]
            j = i + 2
            name = []
            while j < len(toks) and not re.match(r"^0\.[0-9]+$", toks[j]):
                name.append(toks[j])
                j += 1
            if j + 2 < len(toks) and z not in out:
                out[z] = (sym, " ".join(name), float(toks[j]), float(toks[j + 1]), float(toks[j + 2]))
                i = j + 3
                continue
        i += 1
    if len(out) != 92:
        raise SystemExit("tab1: parsed %d elements, expected 92" % len(out))
    return out


def parse_tab2(path):
    """Table 2 → {正規化した名前: (名前, Z/A, I, density, ((Z, w), ...))}。"""
    txt = _text(path)
    body = txt[txt.find("by weight"):]
    toks = body.split()[2:]
    out, i = {}, 0
    while i < len(toks):
        name = []
        while i < len(toks) and not re.match(r"^0\.[0-9]+$", toks[i]):
            name.append(toks[i])
            i += 1
        if i + 2 >= len(toks):
            break
        za, ie, rho = float(toks[i]), float(toks[i + 1]), float(toks[i + 2])
        i += 3
        comp = []
        while i + 1 < len(toks) and re.match(r"^[0-9]+:$", toks[i]):
            comp.append((int(toks[i][:-1]), float(toks[i + 1])))
            i += 2
        nm = " ".join(name).strip()
        out[_norm(nm)] = (nm, za, ie, rho, tuple(comp))
    return out


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _page_title(path):
    with open(path, encoding="latin-1") as fh:
        raw = fh.read()
    m = re.search(r"(?is)<title>[^<]*?\s-\s([^<]+)</title>", raw)
    if not m:
        raise SystemExit("%s: title not found" % path)
    return html.unescape(m.group(1)).strip()


def build(nist_dir):
    t1 = parse_tab1(os.path.join(nist_dir, "tab1.html"))
    t2 = parse_tab2(os.path.join(nist_dir, "tab2.html"))
    elems = []
    edir = os.path.join(nist_dir, "elem")
    for fn in sorted(os.listdir(edir)):
        m = re.match(r"^z(\d\d)\.html$", fn)
        if not m:
            continue
        z = int(m.group(1))
        sym, name, za, ie, rho = t1[z]
        elems.append({"Z": z, "symbol": sym, "name": name, "z_over_a": za, "i_ev": ie,
                      "density_g_cm3": rho, "page": "ElemTab/z%02d.html" % z,
                      "rows": parse_table(os.path.join(edir, fn))})
    have = {e["Z"] for e in elems}
    comps = []
    for page, tab2_name, key, note in COMPOUNDS:
        path = os.path.join(nist_dir, "comp", page + ".html")
        if _norm(tab2_name) not in t2:
            raise SystemExit("%s: %r is not in Table 2" % (page, tab2_name))
        title = _norm(_page_title(path))
        words = [w for w in re.split(r"[^a-z]+", tab2_name.lower()) if len(w) >= 3]
        if not any(w in title for w in words):
            raise SystemExit("%s: page title %r does not name %r" % (page, title, tab2_name))
        nm, za, ie, rho, comp = t2[_norm(tab2_name)]
        s = sum(w for _, w in comp)
        if abs(s - 1.0) > 2e-3:
            raise SystemExit("%s: composition sums to %.6f" % (page, s))
        missing = sorted(z for z, _ in comp if z not in have)
        if missing:
            raise SystemExit("%s: element tables missing for Z=%s" % (page, missing))
        comps.append({"key": key, "nist_name": nm, "note": note, "z_over_a": za, "i_ev": ie,
                      "density_g_cm3": rho, "composition": comp, "page": "ComTab/%s.html" % page,
                      "rows": parse_table(path)})
    return elems, comps


def render(elems, comps):
    out = io_lines = []
    w = io_lines.append
    w("# -*- coding: utf-8 -*-")
    w("# GENERATED by tools/gen_xray_tables.py from the NIST X-ray mass attenuation tables.")
    w("# Source: " + SOURCE)
    w("# Notice: " + NOTICE)
    w("# Do not edit by hand: re-run the generator with --nist <saved pages dir>.")
    w("#")
    w("# rows = (E [keV], mu/rho [cm^2/g], mu_en/rho [cm^2/g], edge) ; an absorption edge appears twice at the")
    w("# same energy (below, then above with the edge name). Consumer: materials.py (X-ray column).")
    w('"""X-ray mass attenuation subset (NIST SRD 126, Hubbell & Seltzer) for fullseye materials."""')
    w("")
    w("XRAY_SOURCE = %r" % SOURCE)
    w("XRAY_NOTICE = %r" % NOTICE)
    w("")
    w("XRAY_ELEMENTS = (")
    for e in elems:
        w("    {'Z': %d, 'symbol': %r, 'name': %r, 'z_over_a': %r, 'i_ev': %r, 'density_g_cm3': %r, 'page': %r,"
          % (e["Z"], e["symbol"], e["name"], e["z_over_a"], e["i_ev"], e["density_g_cm3"], e["page"]))
        w("     'rows': (")
        for r in e["rows"]:
            w("         (%r, %r, %r, %r)," % r)
        w("     )},")
    w(")")
    w("")
    w("XRAY_COMPOUNDS = (")
    for c in comps:
        w("    {'key': %r, 'nist_name': %r, 'note': %r, 'z_over_a': %r, 'i_ev': %r, 'density_g_cm3': %r, 'page': %r,"
          % (c["key"], c["nist_name"], c["note"], c["z_over_a"], c["i_ev"], c["density_g_cm3"], c["page"]))
        w("     'composition': %r," % (c["composition"],))
        w("     'rows': (")
        for r in c["rows"]:
            w("         (%r, %r, %r, %r)," % r)
        w("     )},")
    w(")")
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--nist", required=True, help="directory with the saved NIST pages")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                                  "materials_xray_data.py"))
    ap.add_argument("--check", action="store_true", help="compare with the existing file; exit 1 on drift")
    a = ap.parse_args(argv)
    text = render(*build(a.nist))
    if a.check:
        with open(a.out, encoding="utf-8") as fh:
            same = fh.read() == text
        print("materials_xray_data.py: %s" % ("up to date" if same else "DRIFT"))
        return 0 if same else 1
    with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print("wrote %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
