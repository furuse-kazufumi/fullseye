# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0.
"""Generate the single operator graph and its AI-facing facets.

The graph is the source of truth: sorts are nodes and operators are (possibly
n-ary) hyperedges.  Families, device advice, pipeline shapes, patterns and the
sort guide are attributes or queries over that graph, never independent op
inventories.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
DATA = ROOT / "fullseye" / "data"
DOCS = ROOT / "docs" / "ops"

FAMILY_RULES = {
    "denoise": r"denois|noise.*(?:filter|remove|reduce)|median|bilateral|nlm|wiener",
    "edge_detection": r"canny|sobel|prewitt|scharr|laplac|edge|deriche",
    "thresholding": r"threshold|binar|otsu|niblack|sauvola",
    "morphology": r"morph|erod|dilat|opening|closing|skeleton|thin(?:ning)?",
    "phase_unwrap": r"unwrap",
    "fringe_phase": r"fringe|phase.*(?:shift|extract|demod)|fourier.*phase",
    "sorting": r"(?:quick|heap|merge|intro|stable|radix|counting)_?sort|^sort_",
}

STRUCTURE_RULES = [
    ("global_transform", r"fft|fourier|dct|wavelet"),
    ("irregular_sequential", r"watershed|flood|unwrap|connected|component|(?:quick|heap|merge).*sort"),
    ("reduction_histogram", r"hist|reduce|mean|median|percentile|otsu"),
    ("neighborhood_stencil", r"filter|blur|gauss|median|sobel|canny|morph|erod|dilat|laplac"),
    ("sparse_graph", r"graph|mesh|path|route|sparse"),
]


def _dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def _source(name: str, family: str) -> dict:
    return {"kind": "registry", "value": "name/category", "detail": f"{name}/{family}"}


def _knobs() -> dict:
    # docs/op_knob.json is the measured source.  The package copy is written by
    # gen_mcp_data later in regen_all, so reading that copy would invert the chain.
    p = ROOT / "docs" / "op_knob.json"
    rows = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    return {r.get("op"): r for r in rows if isinstance(r, dict) and r.get("op")}


def _param_metadata(name: str, family: str, knob: dict | None) -> dict:
    out = {}
    for key in ("a", "b"):
        measured = (knob or {}).get(key) or {}
        used = measured.get("used")
        if used is None:
            # Older probe schema records an effect magnitude rather than a bool.
            effect = measured.get("effect", measured.get("range"))
            used = effect not in (None, 0, 0.0, [], {})
        rec = {"used": bool(used), "source": "docs/op_knob.json" if knob else "unmeasured"}
        if rec["used"]:
            rec.update({"kind": "normalized", "normalized": [0.0, 1.0],
                        "mapping": "measured normalized knob; physical mapping not documented"})
            if measured.get("breakpoints"):
                rec["discrete"] = measured["breakpoints"]
        out[key] = rec
    return out


def build() -> dict[str, object]:
    import conversion_matrix as cm
    a = cm.analyse()
    knobs = _knobs()
    family_rows: dict[str, list] = defaultdict(list)
    edges = []
    produced, consumed = Counter(), Counter()
    for name, category, ins, out, _fn in a["ops"]:
        produced[out] += 1
        consumed.update(ins)
        text = f"{name} {category}".lower()
        fam = next((f for f, rx in FAMILY_RULES.items() if re.search(rx, text)), None)
        structure = next((s for s, rx in STRUCTURE_RULES if re.search(rx, text)), "elementwise_or_unknown")
        src = _source(name, category)
        edge = {"op": name, "inputs": list(ins), "output": out, "category": category,
                "family": fam, "reversible": "unknown", "loss": "unknown",
                "compute": {"structure": structure,
                            "intensity": "memory_or_unknown", "source": src},
                "implementations": [{"backend": "python/registry", "status": "available", "source": src}],
                "parity": {"status": "unmeasured", "source": "accel.parity required"},
                "gpu_timing": "unmeasured", "parameters": _param_metadata(name, category, knobs.get(name)),
                "source": src}
        edges.append(edge)
        if fam:
            family_rows[fam].append({"op": name, "inputs": list(ins), "output": out,
                                     "properties": [], "property_sources": [src],
                                     "complexity_exponent": None, "quality": {"status": "unmeasured"}})

    nodes = []
    generators = set(a["generators"])
    checks = set(a["checks"])
    for sort in a["sorts"]:
        nodes.append({"sort": sort, "container": _container(sort), "size_hint": "input-dependent",
                      "produced_by": produced[sort], "consumed_by": consumed[sort],
                      "generator": sort in generators, "type_check": sort in checks,
                      "choose_when": "undocumented", "source": "chain_fuzz catalog"})
    graph = {"schema": 1, "generated_by": "tools/gen_op_facets.py", "model": "typed AND-OR hypergraph",
             "counts": {"nodes": len(nodes), "edges": len(edges),
                        "conversion_pairs": len(a["edges"]),
                        "conversion_edge_incidence": sum(map(len, a["edges"].values()))},
             "nodes": nodes, "edges": edges,
             "diagnostics": {k: a[k] for k in ("dead_ends", "orphans", "never_consumed", "unchecked_ops", "unreachable")}}
    families = {"schema": 1, "source_graph": "OP_GRAPH.json", "rule_source": "tools/gen_op_facets.py:FAMILY_RULES",
                "families": [{"name": f, "ops": sorted(family_rows.get(f, []), key=lambda x: x["op"]),
                              "probes": [], "timing_source": "docs/ops/families_timing.json"}
                             for f in FAMILY_RULES]}
    device = {"schema": 1, "source_graph": "OP_GRAPH.json", "gpu_policy": "unmeasured unless device_timing says otherwise",
              "ops": [{"op": e["op"], "compute": e["compute"], "implementations": e["implementations"],
                       "parity": e["parity"], "gpu_timing": e["gpu_timing"]} for e in edges]}
    sorts = {"schema": 1, "source_graph": "OP_GRAPH.json", "sorts": nodes}
    shapes = _shapes()
    patterns = _patterns()
    return {"OP_GRAPH.json": graph, "OP_FAMILIES.json": families, "OP_DEVICE.json": device,
            "OP_SORTS.json": sorts, "OP_SHAPES.json": shapes, "OP_PATTERNS.json": patterns,
            "docs/ops/patterns.json": patterns}


def _shapes():
    rows = [
      ("single", "dense_field", "serial", True, "RMSE/PSNR"),
      ("same_view_bundle", "dense_field", "bundle_reduction", True, "RMSE/PSNR"),
      ("different_views", "pose", "join", False, "pose error"),
      ("reference_target", "mask", "join", False, "IoU"),
      ("time_series", "sparse_features", "stateful_stream", False, "position error/F1"),
      ("volume", "mask", "serial", True, "IoU"),
      ("point_mesh", "scalar", "serial", True, "bias/repeatability"),
      ("huge_single", "dense_field", "tile", False, "RMSE/PSNR"),
      ("batch", "decision", "map", True, "false positive/false negative"),
    ]
    return {"schema":1,"source_graph":"OP_GRAPH.json","shapes":[
      {"input_form":i,"output_form":o,"shape":s,"currently_composable":ok,"metric":m,
       "patterns":["Pipe-and-Filter"] if s=="serial" else [s],
       "resource_hint":"GPU candidate only after measurement" if s=="map" else "device depends on edge attributes",
       "missing":[] if ok else ["typed DAG executor" if s=="join" else "executor support for "+s],
       "example":{"status":"none","source":"no mechanically verified example"}}
      for i,o,s,ok,m in rows]}


def _patterns():
    names = ["Pipe-and-Filter","Strategy","Adapter","Template Method","Coarse-to-fine",
             "Hypothesize-and-Verify","Voting","Chain of Responsibility","Decorator"]
    return {"schema":1,"source_graph":"OP_GRAPH.json","patterns":[
      {"name":n,"intent":n,"slots":[{"role":"typed operator","input":"$current","output":"$next",
                                       "family":None}],
       "example":{"status":"none","source":"no mechanically verified example"}}
      for n in names]}


def _container(sort: str) -> str:
    s = sort.lower()
    if any(x in s for x in ("graph", "network")): return "graph"
    if any(x in s for x in ("point", "keypoint", "contour", "region")): return "sparse_set"
    if any(x in s for x in ("table", "list", "series", "video", "images", "sweep")): return "sequence"
    if any(x in s for x in ("scalar", "score", "bool", "number")): return "scalar"
    if any(x in s for x in ("image", "depth", "phase", "flow", "voxel", "volume")): return "dense_array"
    if any(x in s for x in ("map", "dict")): return "mapping"
    return "structured_value"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ns = ap.parse_args(argv)
    built = build()
    bad = []
    for name, obj in built.items():
        p = (ROOT / name) if name.startswith("docs/") else (DATA / name)
        text = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
        if ns.check:
            if not p.exists() or p.read_text(encoding="utf-8") != text: bad.append(str(p))
        else: _dump(p, obj)
    if bad:
        print("stale generated facets: " + ", ".join(bad), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
