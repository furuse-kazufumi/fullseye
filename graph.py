"""Operator knowledge graph — the substrate for scaling HALCON coverage.

STATUS.md's plan step 1: build a graph whose nodes are the ~2313 real HALCON
operators (chapter, in/out sort, typed signature, backend-analog candidate) so
that (a) evolution has a typed search space and (b) backend-wrapped registry
entries can be generated from the analog edges.

This module is the single source of truth that both `backends_auto.py` (code
generation) and the per-chapter mining agents consume. It fuses three grounded
sources — never memory:

  data/halcon_operators.json  real op list + chapters + short_desc   (halcon_scrape)
  data/halcon_stubs.json      per-op typed Python signature           (mvtec-halcon binding)
  ops.REGISTRY                what imgevolve already covers (`Op.halcon`)

For each real operator it emits a node with:
  arity        number of HObject inputs in the signature (1 = unary = fits the
               single-image evolution thread; >=2 = n-ary capability op)
  ret_objs     number of HObject outputs
  is_infra     chapter is HDevelop-language / system plumbing (not an algorithm)
  is_algorithm 1-image (or region/xld) algorithmic op we can genuinely wrap
  sort_hint    inferred image/region/contour/... in->out from chapter + desc
  covered      already claimed by a registry `Op.halcon`

Run:  py -3.11 graph.py         # writes data/halcon_graph.json (+ summary)
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OPS_JSON = os.path.join(HERE, "data", "halcon_operators.json")
STUBS_JSON = os.path.join(HERE, "data", "halcon_stubs.json")
OUT_JSON = os.path.join(HERE, "data", "halcon_graph.json")

# Chapters that are HDevelop language / IDE / system plumbing, not image
# algorithms. An algorithm-design engine does not target these (honest scoping).
INFRA_CHAPTERS = {
    "Graphics", "Tuple", "System", "File", "Develop", "Control",
    "Matrix", "Image Source", "Serial", "Socket", "I/O-Devices",
}
# Chapters that need trained models / proprietary algorithms — parity is only
# partial (generic approximations possible, exact HALCON parity not).
MODEL_CHAPTERS = {
    "Classification", "OCR", "Deep Learning", "Deep Learning Model",
    "3D Reconstruction", "3D Matching", "3D Object Model", "Calibration",
    "Identification",
}


def _arity(sig) -> int:
    return sig["params"].count("HObject") if sig else 0


def _ret_objs(sig) -> int:
    return sig["ret"].count("HObject") if sig else 0


def _sort_hint(top: str, desc: str, ret_feature: bool) -> tuple[str, str]:
    """Cheap in->out sort inference from chapter + description keywords.

    HALCON's signatures type everything as HObject, so image-vs-region cannot be
    read off the params; the chapter + verbs disambiguate. Agents refine this per
    op — this is only a prior.
    """
    d = desc.lower()
    # measurement verbs -> feature output
    feat_words = ("area", "count", "number", "moments", "diameter", "orientation",
                  "eccentricity", "coordinates", "histogram", "entropy", "energy",
                  "gray-value features", "intensity")
    out_feature = ret_feature or any(w in d for w in feat_words)
    if top in ("Regions", "Morphology") or "region" in d[:40]:
        s_in = "region"
    elif top == "XLD" or "contour" in d[:40] or "xld" in d:
        s_in = "contour"
    else:
        s_in = "image"
    if out_feature and s_in in ("region", "contour"):
        s_out = "feature"
    elif top == "Segmentation" or ("threshold" in d) or ("segment" in d):
        s_out = "region" if s_in == "image" else s_in
    elif s_in == "contour":
        s_out = "contour"
    elif s_in == "region":
        s_out = "region"
    else:
        s_out = "image"
    return s_in, s_out


def build_nodes(operators, stubs, covered_names):
    nodes = {}
    for op in operators:
        name = op["name"]
        chs = op.get("chapters") or []
        top = chs[0] if chs else "(none)"
        stub = stubs.get(name, {})
        sig = stub.get("py_signature")
        arity = _arity(sig)
        rets = _ret_objs(sig)
        desc = op.get("short_desc", "")
        is_infra = bool(set(chs) & INFRA_CHAPTERS) and not (set(chs) - INFRA_CHAPTERS - {"Legacy"})
        is_model = bool(set(chs) & MODEL_CHAPTERS)
        ret_feature = bool(sig) and ("HObject" not in sig["ret"]) and (
            "float" in sig["ret"] or "int" in sig["ret"] or "Sequence" in sig["ret"])
        s_in, s_out = _sort_hint(top, desc, ret_feature and arity >= 1)
        # An algorithm node = has >=1 image/region input, not infra, sig known.
        is_algorithm = (arity >= 1) and (not is_infra)
        nodes[name] = {
            "name": name,
            "chapters": chs,
            "top_chapter": top,
            "short_desc": desc,
            "url": op.get("url", ""),
            "signature": sig,
            "arity": arity,
            "ret_objs": rets,
            "is_infra": is_infra,
            "is_model": is_model,
            "is_algorithm": is_algorithm,
            "unary": arity == 1,
            "sort_in_hint": s_in,
            "sort_out_hint": s_out,
            "covered": name in covered_names,
        }
    return nodes


def summarize(nodes):
    from collections import Counter
    unary_alg = Counter()
    unary_alg_uncov = Counter()
    nary = Counter()
    for n in nodes.values():
        if n["is_algorithm"] and n["unary"]:
            unary_alg[n["top_chapter"]] += 1
            if not n["covered"]:
                unary_alg_uncov[n["top_chapter"]] += 1
        elif n["is_algorithm"] and n["arity"] >= 2:
            nary[n["top_chapter"]] += 1
    return {
        "n_nodes": len(nodes),
        "n_covered": sum(1 for n in nodes.values() if n["covered"]),
        "n_unary_algorithm": sum(unary_alg.values()),
        "n_unary_algorithm_uncovered": sum(unary_alg_uncov.values()),
        "n_nary_algorithm": sum(nary.values()),
        "unary_algorithm_by_chapter": dict(unary_alg.most_common()),
        "unary_uncovered_by_chapter": dict(unary_alg_uncov.most_common()),
        "nary_by_chapter": dict(nary.most_common()),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ops", default=OPS_JSON)
    ap.add_argument("--stubs", default=STUBS_JSON)
    ap.add_argument("--out", default=OUT_JSON)
    a = ap.parse_args()

    if not os.path.exists(a.ops):
        sys.stderr.write("[graph] run halcon_scrape.py first: %s missing\n" % a.ops)
        return 2
    operators = json.load(open(a.ops, encoding="utf-8"))["operators"]
    stubs = json.load(open(a.stubs, encoding="utf-8"))["operators"] if os.path.exists(a.stubs) else {}

    sys.path.insert(0, HERE)
    import ops as R
    covered = {(o.halcon or "").strip() for o in R.REGISTRY if (o.halcon or "").strip()}

    nodes = build_nodes(operators, stubs, covered)
    summary = summarize(nodes)
    out = {"version": "graph-v1", "summary": summary, "nodes": nodes}
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("[graph] %d nodes -> %s" % (len(nodes), a.out))
    print("  unary algorithm ops: %d (uncovered %d) | n-ary: %d | covered: %d"
          % (summary["n_unary_algorithm"], summary["n_unary_algorithm_uncovered"],
             summary["n_nary_algorithm"], summary["n_covered"]))
    print("  top unary-uncovered chapters:")
    for ch, n in list(summary["unary_uncovered_by_chapter"].items())[:12]:
        print("    %-18s %d" % (ch, n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
