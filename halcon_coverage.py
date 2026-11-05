"""HALCON coverage tracker — measured against the *real* MVTec reference.

Earlier this file encoded a hand-curated ~63-operator guess from memory. It now
loads the operator catalog mined by `halcon_scrape.py`
(`data/halcon_operators.json`, ~2380 real operators across HALCON's top-level
chapters) and measures imgevolve's registry against it via `Op.halcon`.

Outputs:
  - docs/HALCON_COVERAGE.md          human-readable coverage, ranked by gap
  - data/halcon_coverage_report.txt  terse console/report form
  - data/halcon_stubs.json           per-operator stub index (real op -> metadata
                                     + covered flag + imgevolve analog names)

Honest by construction:
  - `covered` counts *distinct real operators* that at least one imgevolve op
    claims as its nearest HALCON analogue (one op claims one operator).
  - `dangling` = `Op.halcon` names that do NOT exist in the real reference
    (typos, version drift, or aspirational names) — surfaced, not hidden.

    py -3.11 halcon_scrape.py            # once, to build the catalog
    py -3.11 halcon_coverage.py          # measure + regenerate docs
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
JSON_DEFAULT = os.path.join(HERE, "data", "halcon_operators.json")
MD_DEFAULT = os.path.join(HERE, "docs", "HALCON_COVERAGE.md")
REPORT_DEFAULT = os.path.join(HERE, "data", "halcon_coverage_report.txt")
STUBS_DEFAULT = os.path.join(HERE, "data", "halcon_stubs.json")
VERSIONS_DEFAULT = os.path.join(HERE, "data", "halcon_versions.json")
PYAPI_DEFAULT = os.path.join(HERE, "data", "halcon_pyapi.json")


#: ★2026-11-03(完成度監査 B、ユーザー決定): **名前は HALCON に対応しているが中身が薄い**もの。
#: 「対応済み」(``covered``)からは外し、「部分対応」(``partial``)として別に数えて見せる。
#: 中身を足して HALCON の同名 operator の仕事をするようになったら、ここから消す(消すと covered に戻る)。
#: 根拠: リポジトリ外の完成度監査 B(機能の穴)の
#: 「名前は対応しているが中身が薄いもの」表(関数本体の行数と呼び出しを ast で数えた)。
#: 値 = (Fullseye の関数, 何をするか, 何をしないか)。英語にしてあるのは生成物(英語の HALCON_COVERAGE.md)にそのまま載せるため。
PARTIAL = {
    "find_deformable_surface_model": (
        "matching3d.find_deformable_surface_model",
        "rigid point-pair-feature (PPF) surface matching (calls ppf.surface_match)",
        "no deformation: the model is matched as a rigid body"),
    "find_planar_uncalib_deformable_model": (
        "shapematch.find_planar_uncalib_deformable_model",
        "calls find_local_deformable_model (rigid shape match, then optical flow)",
        "no planar perspective / deformation model is estimated"),
    "measure_profile_sheet_of_light": (
        "final_genuine.measure_profile_sheet_of_light",
        "per-column intensity-weighted centroid of the laser line, in pixel rows",
        "no Steger / Gaussian-fit line centre, no light-plane geometry, no 3-D points"),
    "calibrate_sheet_of_light": (
        "final_genuine.calibrate_sheet_of_light",
        "one linear pixel-to-height scale fitted to known step heights",
        "no geometric calibration of the light plane, camera and movement axis"),
    "create_ocv_proj": (
        "final_genuine.create_ocv_proj",
        "per-pixel mean and standard-deviation template of the training images",
        "no character segmentation or projection model (HALCON OCV)"),
    "create_bead_inspection_model": (
        "final_genuine.create_bead_inspection_model",
        "stores the reference centre path, the nominal width and a tolerance",
        "no bead appearance model"),
    "apply_bead_inspection_model": (
        "final_genuine.apply_bead_inspection_model",
        "flags reference-path points farther than width/2 + tol from the bead mask (distance transform)",
        "does not tell too narrow / too wide / left-right offset / overflow apart; reports only 'missing'"),
    "find_box_3d": (
        "objmodel3d.find_box_3d",
        "one PCA-oriented bounding box of the whole point cloud",
        "no box search in a scene: no segmentation, no side-length matching, no score"),
    "binocular_calibration": (
        "caltab.binocular_calibration",
        "Zhang calibration of the left and right camera, each on its own",
        "no joint estimation of the relative pose between the two cameras"),
    # ---- 第 2 便(2026-11-03、同じ規則の延長): 監査 B の表の残り ----
    "find_local_deformable_model": (
        "shapematch.find_local_deformable_model",
        "rigid shape match, then a dense optical-flow field on the matched patch",
        "no deformation model optimised jointly with the match (HALCON's local deformable matching)"),
    "find_shape_model_3d": (
        "matching3d.find_shape_model_3d",
        "projects the model for n_views rotations about one axis and keeps the best NCC position",
        "no search over a view sphere, no full 6-DoF pose, no edge-based 3-D shape matching"),
    "create_texture_inspection_model": (
        "final_genuine.create_texture_inspection_model",
        "mean and covariance of two local features (patch mean and variance) over good images",
        "no multi-scale texture features and no training stage (HALCON's texture inspection model)"),
    "apply_texture_inspection_model": (
        "final_genuine.apply_texture_inspection_model",
        "Mahalanobis distance of the two local features, thresholded into a defect mask",
        "no multi-scale texture features; defects outside mean/variance changes are not modelled"),
    "camera_calibration": (
        "calib.camera_calibration",
        "Zhang closed-form intrinsics K (fx, fy, cx, cy, skew) from >= 3 views of a planar target, fail-closed",
        "no lens distortion and no joint non-linear refinement of K, distortion and extrinsics"),
    # ---- 第 3 便(2026-11-03): 部分対応の探す側と対になる、モデルを作る側 ----
    "create_local_deformable_model": (
        "shapematch.create_local_deformable_model",
        "keeps the template and a rigid shape model of it (create_shape_model)",
        "no deformation model (control grid / deformation parameters) is built"),
    "create_shape_model_3d": (
        "matching3d.create_shape_model_3d",
        "stores the 3-D points, the camera parameters and the number of views",
        "no views are precomputed: no view sphere, no 2-D shape models per view"),
}


def load_operators(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_versions(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def classify_versions(analog_names, versions_data):
    """Split imgevolve `Op.halcon` names by presence across HALCON releases.

    Returns present_all / drift(name -> [versions present]) / never(list).
    HALCON's op set changes between versions; this tells 'version drift'
    (real op, just not in every release) apart from a genuine bad name.
    """
    vers = versions_data["versions"]
    sets = {v: set(s) for v, s in versions_data["opsets"].items()}
    union = set().union(*sets.values())
    present_all, drift, never = [], {}, []
    for h in sorted(analog_names):
        inv = [v for v in vers if h in sets[v]]
        if len(inv) == len(vers):
            present_all.append(h)
        elif inv:
            drift[h] = inv
        else:
            never.append(h)
    return {"present_all": present_all, "drift": drift, "never": never,
            "counts": versions_data["counts"], "n_union": len(union)}


def analyze(data, registry, versions_data=None):
    operators = data["operators"]
    real = {op["name"]: op for op in operators}
    real_ops = set(real)

    # chapter -> set of operator names (top-level labels from the scrape)
    chapter_ops = {}
    for op in operators:
        for ch in op["chapters"] or ["(unclassified)"]:
            chapter_ops.setdefault(ch, set()).add(op["name"])

    # imgevolve analogue names, and the reverse map real-op -> [imgevolve op names]
    analog = {}
    for o in registry:
        h = (o.halcon or "").strip()
        if h:
            analog.setdefault(h, []).append(o.name)
    # 知覚 facade(camera/stereo/pcseg/ppf/pointcloud)が genuine 実装する operator も計上。
    # 進化 registry の Op ではないため data/halcon_facade_map.json から別途マージ(全 smoke 検証済)。
    # ★2026-10-06: 正本は同梱の fullseye/data/(c5268029e で移した)。旧来の data/ だけを見ていたため、
    #   facade の 600 本が黙って数えから落ち、HALCON 対応が 982 → 388 と出ていた(例外も警告も無し)。
    facade_path = next((p for p in (os.path.join(HERE, "fullseye", "data", "halcon_facade_map.json"),
                                    os.path.join(HERE, "data", "halcon_facade_map.json"))
                        if os.path.exists(p)), None)
    if facade_path is None:
        raise SystemExit("[halcon_coverage] halcon_facade_map.json が見つからない —— facade を数えずに"
                         "被覆率を出すと桁違いに小さくなるので止める")
    if os.path.exists(facade_path):
        with open(facade_path, encoding="utf-8") as fh:
            for hname, ref in json.load(fh).items():
                if hname.startswith("_"):
                    continue
                analog.setdefault(hname, []).append("facade:" + ref)
    # 台帳 op の対応(2026-11-02)。Op.halcon を持たない台帳の側の正本。
    import opassist
    for op_name, hname in opassist.ledger_halcon_map().items():
        analog.setdefault(hname, []).append("ledger:" + op_name)
    ours = set(analog)

    # 部分対応(PARTIAL)は名前の対応があっても covered に入れない。表が古くなった(名乗りが消えた /
    # 実在しない名前)ら止める —— 黙って何も外さない表は門にならない(fail-closed)。
    stale = sorted(n for n in PARTIAL if n not in ours or n not in real_ops)
    if stale:
        raise SystemExit("[halcon_coverage] PARTIAL に、名乗る op が無い / 実在しない名前: %s" % ", ".join(stale))
    partial = set(PARTIAL)
    covered = (ours & real_ops) - partial
    dangling = sorted(ours - real_ops)
    by_source = _covered_by_source(analog, covered)

    per_chapter = {}
    uncovered = {}
    for ch, opset in chapter_ops.items():
        cov = (opset & ours) - partial
        per_chapter[ch] = (len(cov), len(opset))
        uncovered[ch] = sorted(opset - covered)

    versions = classify_versions(ours, versions_data) if versions_data else None

    return {
        "n_real": len(real_ops),
        "n_registry": len(registry),
        "covered": covered,
        "covered_by_source": by_source,
        "partial": sorted(partial),
        "dangling": dangling,
        "per_chapter": per_chapter,
        "uncovered": uncovered,
        "chapter_ops": chapter_ops,
        "analog": analog,
        "real": real,
        "versions": versions,
    }


#: 対応の出どころ。**この順で 1 回だけ**数える(同じ HALCON 名を registry と facade の両方が名乗るなら
#: registry 側)。見出しの数はこの 3 つの和で、内訳が和として成り立つ。
SOURCES = ("registry", "facade", "ledger")

#: 出どころの説明(生成物の文言はここから作る —— 文言を手で書くと数と食い違う)。
SOURCE_LABEL = {
    "registry": "`Op.halcon` on the evolvable registry ops",
    "facade": "perception facades (`fullseye/data/halcon_facade_map.json`, not registry ops)",
    "ledger": "typed-ledger ops (`opassist.ledger_halcon_map()`, not registry ops)",
}


def _source_of(ref: str) -> str:
    """``analog`` の値 1 つの出どころ(``facade:`` / ``ledger:`` の接頭辞、無ければ registry)。"""
    if ref.startswith("facade:"):
        return "facade"
    if ref.startswith("ledger:"):
        return "ledger"
    return "registry"


def _covered_by_source(analog, covered):
    """``covered`` を出どころ別の**互いに素な**集合に分ける(:data:`SOURCES` の順に先取り)。

    ★2026-11-05(敵対的検証 第 2 巡 D2): 見出しは「1017 ... via `Op.halcon`, from 947 registry ops」
    と書いていたが、registry の ``Op.halcon`` が名乗るのは 388 名で、残り 629 名は facade と
    台帳の対応だった。数は合っていても説明が嘘をつく形なので、内訳を生成器が数えて出す。
    """
    seen, out = set(), {}
    for src in SOURCES:
        names = {h for h in covered if any(_source_of(r) == src for r in analog.get(h, ()))} - seen
        out[src] = names
        seen |= names
    assert seen == set(covered), "出どころの分からない対応がある: %s" % sorted(set(covered) - seen)[:5]
    return out


def source_breakdown_text(by_source, names=None):
    """``N via A, M via B, K via C`` の文(``names`` を渡すとその部分集合で数える)。"""
    parts = []
    for src in SOURCES:
        s = by_source[src] if names is None else (by_source[src] & set(names))
        parts.append("%d through %s" % (len(s), SOURCE_LABEL[src]))
    return ", ".join(parts[:-1]) + " and " + parts[-1]


def gap_ranking(a):
    items = [(ch, cov, total) for ch, (cov, total) in a["per_chapter"].items()]
    items.sort(key=lambda x: (x[2] - x[1], x[2]), reverse=True)
    return items


def build_md(data, a):
    n_cov = len(a["covered"])
    pct = 100.0 * n_cov / a["n_real"] if a["n_real"] else 0.0
    out = [
        "# HALCON operator coverage (measured vs the real reference)",
        "",
        "Source: `%s` (version %s)." % (data["source"], data["version"]),
        "Ground truth: **%d operators across %d top-level chapters** "
        "(%d TOC pages), mined by `halcon_scrape.py`."
        % (a["n_real"], len(a["per_chapter"]), data["n_chapters"]),
        "",
        "**imgevolve maps to %d / %d HALCON operators (%.1f%%)**: %s "
        "(each name counted once, in that order; the registry has %d ops)."
        % (n_cov, a["n_real"], pct, source_breakdown_text(a["covered_by_source"]), a["n_registry"]),
        "",
        "One imgevolve op claims one nearest HALCON operator, so coverage counts",
        "distinct real operators with an analogue. This number is grounded in the",
        "scraped reference, not memory; it grows with each new `Op.halcon`, facade",
        "entry or ledger mapping that names a real operator.",
        "",
        "**%d more HALCON names are partial analogues and are not counted** (the function "
        "carries the name but does only part of the operator's job; listed below)." % len(a["partial"]),
        "",
        "## Partial analogues (named, not counted as covered)",
        "",
        "| HALCON operator | Fullseye function | what it does | what it does not do |",
        "|---|---|---|---|",
    ] + ["| %s | `%s` | %s | %s |" % ((n,) + PARTIAL[n]) for n in a["partial"]] + [
        "",
        "## Per-chapter coverage (ranked by gap)",
        "",
        "| chapter | covered | total | gap |",
        "|---|---|---|---|",
    ]
    for ch, cov, total in gap_ranking(a):
        out.append("| %s | %d | %d | %d |" % (ch, cov, total, total - cov))
    if a["dangling"]:
        out += ["", "## `Op.halcon` names NOT found in the reference (fix candidates)", "",
                "These %d names are claimed by the registry but do not exist as operators "
                "in HALCON %s (typo / version drift / aspirational). Honest disclosure — "
                "they do not count toward coverage." % (len(a["dangling"]), data["version"]),
                "", "```", ", ".join(a["dangling"]), "```"]
    out += ["", "## Build targets — biggest gaps first (sample uncovered operators)", ""]
    for ch, cov, total in gap_ranking(a)[:12]:
        sample = a["uncovered"].get(ch, [])[:12]
        out.append("- **%s** (%d/%d): %s" % (ch, cov, total, ", ".join(sample)))
    v = a.get("versions")
    if v:
        cnt = ", ".join("v%s=%d" % (k, n) for k, n in v["counts"].items())
        out += ["", "## Version awareness (HALCON's op set changes between releases)",
                "Operator counts per scraped release: %s (union %d). Coverage above is vs "
                "the primary scrape; the classification below is honest about which claimed "
                "`Op.halcon` names are stable vs release-specific." % (cnt, v["n_union"]),
                "",
                "- **%d** claimed names exist in **all** scraped releases (stable)." % len(v["present_all"])]
        if v["drift"]:
            out.append("- **%d version-drift** (real, but only some releases): %s" % (
                len(v["drift"]),
                "; ".join("`%s` (in %s)" % (k, "/".join(ver)) for k, ver in sorted(v["drift"].items()))))
        out.append("- **%d** claimed names exist in **no** scraped release — genuine bad "
                   "names / library-specific / voxel-3D, not version drift." % len(v["never"]))
    out += ["", "## Honest reading",
            "- HALCON's ~%d operators include large non-algorithmic chapters "
            "(Graphics / Tuple / System / File / Develop / Control) an algorithm-design "
            "engine does not target; real algorithmic headroom is smaller than the raw gap."
            % a["n_real"],
            "- Many operators are parametric variants of one family (collapse to fewer).",
            "- Coverage counts a *nearest analogue*, not signature-level parity; per-operator "
            "typed stubs (`data/halcon_stubs.json`, with real Python signatures from the "
            "`mvtec-halcon` binding when available) track what is named vs implemented.", ""]
    return "\n".join(out)


def build_report(data, a):
    n_cov = len(a["covered"])
    pct = 100.0 * n_cov / a["n_real"] if a["n_real"] else 0.0
    lines = [
        "HALCON coverage -- version %s" % data["version"],
        "real operators: %d  top-level chapters: %d  registry ops: %d"
        % (a["n_real"], len(a["per_chapter"]), a["n_registry"]),
        "covered (distinct real ops with analogue): %d/%d (%.1f%%)"
        % (n_cov, a["n_real"], pct),
        "dangling Op.halcon refs: %d -> %s" % (len(a["dangling"]), a["dangling"]),
        "partial analogues (named, not counted): %d -> %s" % (len(a["partial"]), a["partial"]),
    ]
    v = a.get("versions")
    if v:
        lines.append("versions: %s (union %d)"
                     % (", ".join("v%s=%d" % kv for kv in v["counts"].items()), v["n_union"]))
        lines.append("  stable(all)=%d  drift=%d %s  never=%d"
                     % (len(v["present_all"]), len(v["drift"]),
                        sorted(v["drift"]), len(v["never"])))
    lines += ["", "top gap chapters:"]
    for ch, cov, total in gap_ranking(a)[:15]:
        lines.append("  %-28s %4d/%-5d gap=%d" % (ch, cov, total, total - cov))
    return "\n".join(lines) + "\n"


def build_stubs(data, a, pyapi=None):
    """Per-operator stub index: real op -> metadata + covered + imgevolve analogs.

    When the `mvtec-halcon` binding signatures are available (`pyapi`), each stub
    carries the real typed Python signature — turning the index into typed stubs
    grounded in HALCON's official Python API, not memory.
    """
    pyapi = pyapi or {}
    n_sig = 0
    stubs = {}
    for name, op in a["real"].items():
        sig = pyapi.get(name)
        if sig:
            n_sig += 1
        stubs[name] = {
            "chapters": op["chapters"],
            "short_desc": op.get("short_desc", ""),
            "url": op["url"],
            "covered": name in a["covered"],
            "imgevolve_analogs": a["analog"].get(name, []),
            "py_signature": sig,
        }
        if name in PARTIAL:
            stubs[name]["partial"] = {"does": PARTIAL[name][1], "does_not": PARTIAL[name][2]}
    return {
        "version": data["version"],
        "n_operators": len(stubs),
        "n_covered": len(a["covered"]),
        "n_with_signature": n_sig,
        "signature_source": "mvtec-halcon binding" if pyapi else None,
        "operators": stubs,
    }


def main():
    ap = argparse.ArgumentParser(description="measure imgevolve coverage vs real HALCON reference")
    ap.add_argument("--json", default=JSON_DEFAULT)
    ap.add_argument("--md", default=MD_DEFAULT)
    ap.add_argument("--report", default=REPORT_DEFAULT)
    ap.add_argument("--stubs", default=STUBS_DEFAULT)
    ap.add_argument("--versions", default=VERSIONS_DEFAULT,
                    help="multi-version op-set snapshot (halcon_scrape.py --op-sets)")
    ap.add_argument("--pyapi", default=PYAPI_DEFAULT,
                    help="derived mvtec-halcon Python signatures (optional)")
    args = ap.parse_args()

    if not os.path.exists(args.json):
        sys.stderr.write(
            "[halcon_coverage] catalog not found: %s\n"
            "  run first:  py -3.11 halcon_scrape.py --out %s\n" % (args.json, args.json))
        return 2

    sys.path.insert(0, HERE)
    import ops as R

    data = load_operators(args.json)
    versions_data = load_versions(args.versions)
    pyapi = load_versions(args.pyapi)  # same optional-JSON loader
    a = analyze(data, R.REGISTRY, versions_data)

    os.makedirs(os.path.dirname(args.md), exist_ok=True)
    with open(args.md, "w", encoding="utf-8") as fh:
        fh.write(build_md(data, a))
    os.makedirs(os.path.dirname(args.report), exist_ok=True)
    report = build_report(data, a)
    with open(args.report, "w", encoding="utf-8") as fh:
        fh.write(report)
    with open(args.stubs, "w", encoding="utf-8") as fh:
        json.dump(build_stubs(data, a, pyapi), fh, ensure_ascii=False, indent=1)

    print(report)
    print("[ok] wrote %s , %s , %s" % (args.md, args.report, args.stubs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
