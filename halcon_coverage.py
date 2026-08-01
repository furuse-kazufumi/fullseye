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
    ours = set(analog)

    covered = ours & real_ops
    dangling = sorted(ours - real_ops)

    per_chapter = {}
    uncovered = {}
    for ch, opset in chapter_ops.items():
        cov = opset & ours
        per_chapter[ch] = (len(cov), len(opset))
        uncovered[ch] = sorted(opset - ours)

    versions = classify_versions(ours, versions_data) if versions_data else None

    return {
        "n_real": len(real_ops),
        "n_registry": len(registry),
        "covered": covered,
        "dangling": dangling,
        "per_chapter": per_chapter,
        "uncovered": uncovered,
        "chapter_ops": chapter_ops,
        "analog": analog,
        "real": real,
        "versions": versions,
    }


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
        "**imgevolve maps to %d / %d HALCON operators (%.1f%%)** via `Op.halcon`, "
        "from %d registry ops." % (n_cov, a["n_real"], pct, a["n_registry"]),
        "",
        "One imgevolve op claims one nearest HALCON operator, so coverage counts",
        "distinct real operators with an analogue. This number is grounded in the",
        "scraped reference, not memory; grow it by adding operator families to the",
        "registry (each new `Op.halcon` that names a real operator lifts coverage).",
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
