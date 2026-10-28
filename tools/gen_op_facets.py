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

# Public canonical vocabulary is the executor vocabulary.  Graph/ledger aliases
# are accepted at every API boundary and normalized exactly once here.
SORT_ALIASES = {"image2d": "image", "mask": "region", "contour2d": "contour",
                "features": "feature", "pointcloud": "points"}
ACQUIRABLE = {
    "image": "camera acquisition contract",
    "images": "multi-frame camera acquisition contract",
    "polsweep": "polarization camera/analyzer sweep",
    "points": "range sensor or point sampler",
    "lightfield": "light-field camera grid",
    "volume": "tomographic/volumetric acquisition",
    "video": "camera stream acquisition",
}
DUPLICATE_EXEMPTIONS = {
    "gaussians_to_voxel": "chain_fuzz compatibility alias; first declaration is the public contract",
}

def canonical_sort(value: str | None) -> str:
    value = (value or "untyped").strip()
    return SORT_ALIASES.get(value, value)

def split_inputs(value) -> list[str]:
    if isinstance(value, list):
        return [canonical_sort(x) for x in value]
    if not value:
        return ["untyped"]
    # Old indexes encoded n-ary inputs as a display string.  It is never a sort.
    return [canonical_sort(x) for x in re.split(r"\s*(?:×|\+|,)\s*", str(value)) if x]

def type_semantics(inputs: list[str], output: str) -> tuple[list[str], str, str, bool]:
    """Replace the overloaded historical ``any`` with explicit meanings."""
    inputs = ["unknown" if x in ("any", "untyped") else x for x in inputs]
    if output == "any":
        output = "poly" if inputs and inputs[0] != "unknown" else "unknown"
    elif output == "untyped":
        output = "unknown"
    semantics = ("source" if not inputs and output != "unknown" else
                 "poly" if output == "poly" else
                 "unknown" if output == "unknown" or "unknown" in inputs else "typed")
    return inputs, output, semantics, bool(inputs)

FAMILY_RULES = {
    "denoise": r"denois|noise.*(?:filter|remove|reduce)|median|bilateral|nlm|wiener",
    "edge_detection": r"canny|sobel|prewitt|scharr|laplac|edge|deriche",
    "thresholding": r"threshold|binar|otsu|niblack|sauvola",
    "morphology": r"morph|erod|dilat|opening|closing|skeleton|thin(?:ning)?",
    "phase_unwrap": r"unwrap",
    "fringe_phase": r"fringe|phase.*(?:shift|extract|demod)|fourier.*phase",
    "sorting": r"(?:quick|heap|merge|intro|stable|radix|counting)_?sort|^sort_",
}

def _dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def _source(name: str, family: str) -> dict:
    return {"kind": "registry", "value": "chain_fuzz catalog", "detail": family}


def _knobs() -> dict:
    # docs/op_knob.json is the measured source.  The package copy is written by
    # gen_mcp_data later in regen_all, so reading that copy would invert the chain.
    p = ROOT / "docs" / "op_knob.json"
    rows = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    return {r.get("op"): r for r in rows if isinstance(r, dict) and r.get("op")}


def _param_metadata(name: str, family: str, knob: dict | None) -> dict:
    out = {}
    knob = knob or {}
    for key in ("a", "b"):
        kind = knob.get(key + "_kind")
        effect = float(knob.get(key + "_effect") or 0.0)
        used = (kind not in (None, "unused") and effect > 0) if key == "a" else bool(knob.get("b_used"))
        rec = {"used": used, "source": "docs/op_knob.json" if knob else "unmeasured",
               "effect": effect, "kind": kind or ("continuous" if used else "unused")}
        if used:
            rec.update({"normalized": [0.0, 1.0], "mapping": "measured normalized knob; physical mapping not documented"})
            if key == "a" and knob.get("breakpoints"):
                rec["discrete"] = knob["breakpoints"]
        out[key] = rec
    return out

def _system_params():
    def p(default, meaning, hidden, source="system design 2026-10-28"):
        return {"default": default, "meaning": meaning, "hide_from_ai": hidden, "source": source}
    return {"schema": 1, "params": {
      "plan_k": p(5,"maximum returned plans",True), "plan_max_depth": p(4,"maximum graph depth",True),
      "budget_tokens": p(800,"default textual response budget",True), "limit": p(20,"default row limit",True),
      "max_structured_bytes": p(512000,"structured MCP response ceiling",True,"fullseye.mcp.server"),
      "max_stages": p(64,"pipeline stage safety ceiling",True), "device": p("cpu","execution device",True),
      "batch": p(1,"batch size",True), "lang": p("auto","response language",True),
      "vision": p("auto","diagnostic image policy",True), "seed": p(0,"deterministic random seed",True),
      "tile_size": p(512,"large-image tile edge",True), "border": p("reflect","neighborhood border policy",True),
      "numeric_floor": p(1e-12,"numerical denominator floor",True), "iteration_limit": p(100,"iterative solver cap",True),
      "gpu_idle_policy": p("no compute process and no loaded local model","GPU measurement admission",True)}}


def build() -> dict[str, object]:
    import conversion_matrix as cm
    a = cm.analyse()
    knobs = _knobs()
    index = json.loads((ROOT / "docs" / "OP_INDEX.json").read_text(encoding="utf-8"))
    index_rows = index.get("ops") or []
    if not index_rows:
        raise RuntimeError("docs/OP_INDEX.json has no ops")
    executable = {r["name"] for r in index_rows if r.get("tier") in {"registry", "color", "nary"}}
    index_names = {r["name"] for r in index_rows}
    nary = {r["name"]: r for r in index_rows if r.get("tier") == "nary"}
    for name, row in nary.items():
        if row.get("arity") != len(row.get("in_sorts") or []):
            raise RuntimeError("nary declaration arity mismatch for %s" % name)
    family_rows: dict[str, list] = defaultdict(list)
    try:
        import accel
        accel_names = {core for _public, (_fn, core, _halcon) in accel.ACCEL.items()}
    except Exception:
        accel_names = set()
    edges = []
    produced, consumed = Counter(), Counter()
    seen = set()
    signatures = {}
    duplicate_declarations = []
    excluded_chain_only = []
    for name, category, ins, out, _fn in a["ops"]:
        if name not in index_names:
            excluded_chain_only.append({"op": name, "reason": "not present in public OP_INDEX"})
            continue
        ins, out = split_inputs(ins), canonical_sort(out)
        if name in nary:
            ins = [canonical_sort(x) for x in nary[name]["in_sorts"]]
        ins, out, semantics, consumes = type_semantics(ins, out)
        signature = (tuple(ins), out, category)
        if name in seen:
            conflict = signatures[name] != signature
            if conflict and name not in DUPLICATE_EXEMPTIONS:
                raise RuntimeError("conflicting operator declarations for %s: %r != %r" %
                                   (name, signatures[name], signature))
            duplicate_declarations.append({"op": name, "conflicting": conflict,
                                           "kept": signatures[name], "ignored": signature,
                                           "exemption": DUPLICATE_EXEMPTIONS.get(name)})
            continue
        seen.add(name); signatures[name] = signature
        produced[out] += 1
        consumed.update(ins)
        text = f"{name} {category}".lower()
        fam = next((f for f, rx in FAMILY_RULES.items() if re.search(rx, text)), None)
        structure = "unknown"
        if name in accel_names:
            if name in {"lowpass", "highpass"}:
                structure = "global_transform"
            elif name == "fill_holes":
                structure = "irregular_sequential"
            elif re.search(r"gauss|sobel|median|morph|blur", name):
                structure = "neighborhood_stencil"
            else:
                structure = "elementwise"
        src = _source(name, category)
        edge = {"op": name, "inputs": list(ins), "output": out, "category": category,
                "family": None, "family_candidate": fam,
                "family_candidate_source": "heuristic_regex" if fam else None,
                "type_semantics": semantics, "consumes_input": consumes,
                "executable": name in executable,
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

    # OP_INDEX is the public population.  Add every op missing from the typed
    # ledger; missing type facts stay explicit instead of silently dropping it.
    for row in index_rows:
        name = row["name"]
        if name in seen:
            continue
        seen.add(name)
        ins = ([canonical_sort(x) for x in row.get("in_sorts", [])] if row.get("tier") == "nary"
               else split_inputs(row.get("in_sort")))
        out = canonical_sort(row.get("out_sort"))
        ins, out, semantics, consumes = type_semantics(ins, out)
        category = row.get("category") or "untyped"
        text = f"{name} {category}".lower()
        fam = next((f for f, rx in FAMILY_RULES.items() if re.search(rx, text)), None)
        src = {"kind": "index", "value": "docs/OP_INDEX.json"}
        edge = {"op": name, "inputs": ins, "output": out, "category": category, "family": None,
                "family_candidate": fam, "family_candidate_source": "heuristic_regex" if fam else None,
                "type_semantics": semantics, "consumes_input": consumes,
                "executable": name in executable,
                "compute": {"structure": "unknown", "intensity": "unknown", "source": src},
                "implementations": [{"backend": row.get("module") or "registry", "status": "available", "source": src}],
                "parity": {"status": "unmeasured", "source": "accel.parity required"},
                "gpu_timing": "unmeasured", "parameters": _param_metadata(name, category, knobs.get(name)), "source": src}
        edges.append(edge)
        produced[out] += 1; consumed.update(ins)
        if fam:
            family_rows[fam].append({"op": name, "inputs": ins, "output": out, "properties": [],
                                     "property_sources": [src], "complexity_exponent": None,
                                     "quality": {"status": "unmeasured"}})

    # The generic algorithm layer is intentionally outside OP_INDEX's image-op
    # registry.  Keep the three requested sorting alternatives as an explicit,
    # reasoned extension rather than hiding them behind a regex.
    for name in ("quicksort", "heapsort", "mergesort"):
        src = {"kind": "docstring", "value": "algo.py", "detail": name}
        edges.append({"op": name, "inputs": ["sequence"], "output": "sequence", "category": "sort",
                      "family": "sorting", "type_semantics": "typed", "consumes_input": True,
                      "executable": False,
                      "compute": {"structure": "irregular_sequential", "intensity": "comparison_bound", "source": src},
                      "implementations": [{"backend":"algo Python/C generator","status":"available","source":src}],
                      "parity":{"status":"unmeasured","source":"algo differential test"},
                      "gpu_timing":"not_applicable", "parameters":{}, "source":src,
                      "population_extension_reason":"generic algorithm layer requested by design"})
        produced["sequence"] += 1; consumed["sequence"] += 1

    # Intern provenance once and omit blanket unknown measurements.  This keeps
    # OP_GRAPH readable instead of repeating the same unmeasured/source record
    # thousands of times.
    sources={}; source_ids={}
    def intern(src):
        key=json.dumps(src,ensure_ascii=False,sort_keys=True)
        if key not in source_ids:
            sid="S%05d"%(len(source_ids)+1); source_ids[key]=sid; sources[sid]=src
        return source_ids[key]
    for e in edges:
        if e.get("source"): e["source_ref"]=intern(e.pop("source"))
        comp=e.get("compute",{})
        if comp.get("source"): comp["source_ref"]=intern(comp.pop("source"))
        for impl in e.get("implementations",[]):
            if impl.get("source"): impl["source_ref"]=intern(impl.pop("source"))
        if e.get("parity",{}).get("status")=="unmeasured": e.pop("parity",None)
        if e.get("gpu_timing")=="unmeasured": e.pop("gpu_timing",None)
        for p in e.get("parameters",{}).values():
            if p.get("source") and p["source"]!="unmeasured": p["source_ref"]=intern(p.pop("source"))

    nodes = []
    generators = {canonical_sort(x) for x in a["generators"]}
    checks = {canonical_sort(x) for x in a["checks"]}
    all_sorts = sorted({canonical_sort(s) for s in a["sorts"]} |
                       {x for e in edges for x in e["inputs"]} | {e["output"] for e in edges})
    all_sorts = [s for s in all_sorts if s != "any"]
    for sort in all_sorts:
        nodes.append({"sort": sort, "container": _container(sort), "size_hint": "input-dependent",
                      "produced_by": produced[sort], "consumed_by": consumed[sort],
                      "generator": sort in generators, "type_check": sort in checks,
                      "choose_when": "undocumented", "source": "chain_fuzz catalog"})
    lifted = [{"op":"map::"+e["op"],"base_op":e["op"],"input":"seq<%s>"%e["inputs"][0],
               "output":"seq<%s>"%e["output"],"kind":"map"}
              for e in edges if e.get("executable") and len(e["inputs"])==1 and e["inputs"][0]==e["output"]]
    parameter_summary={"measured_ops":sum(bool(knobs.get(e["op"])) for e in edges),
                       "a_unused":sum("a" in e.get("parameters",{}) and e["parameters"]["a"].get("source")!="unmeasured" and not e["parameters"]["a"].get("used") for e in edges),
                       "b_unused":sum("b" in e.get("parameters",{}) and e["parameters"]["b"].get("source")!="unmeasured" and not e["parameters"]["b"].get("used") for e in edges),
                       "reason":"docs/op_knob.json measured no output effect"}
    graph = {"schema": 2, "generated_by": "tools/gen_op_facets.py", "model": "typed AND-OR hypergraph",
             "sort_aliases": SORT_ALIASES, "population": "union of docs/OP_INDEX.json and chain_fuzz catalog",
             "acquirable_sorts": [{"sort": s, "source": src} for s, src in ACQUIRABLE.items()],
             "type_constructors":{"images":"seq<image>","video":"seq<image>","polsweep":"seq<polarized_image>",
                                  "lightfield":"grid<image>","volume":"stack3<image>"},
             "lifted_map_edges":lifted,
             "parameter_summary":parameter_summary,
             "sources":sources,
             "counts": {"nodes": len(nodes), "edges": len(edges),
                        "conversion_pairs": len(a["edges"]),
                        "conversion_edge_incidence": sum(map(len, a["edges"].values()))},
             "nodes": nodes, "edges": edges,
             "diagnostics": {**{k: a[k] for k in ("dead_ends", "orphans", "never_consumed", "unchecked_ops", "unreachable")},
                             "duplicate_declarations": duplicate_declarations}}
    graph["diagnostics"]["excluded_chain_only"] = excluded_chain_only
    ledger = json.loads((DOCS / "families.json").read_text(encoding="utf-8"))
    edge_map = {e["op"]: e for e in edges}
    timing_path = DOCS / "families_timing.json"
    timing = json.loads(timing_path.read_text(encoding="utf-8")) if timing_path.exists() else {"measurements":{}}
    fam_out=[]
    for f in ledger["families"]:
        rows=[]
        for member in f["members"]:
            e=edge_map.get(member["op"])
            if not e: raise RuntimeError("family ledger names missing op: "+member["op"])
            measured=(timing.get("measurements") or {}).get(member["op"],{})
            rows.append({"op":member["op"],"inputs":e["inputs"],"output":e["output"],
                         "membership_source":member["source"],"properties":measured.get("properties",[]),
                         "property_sources":[{"kind":"measurement","value":"docs/ops/families_timing.json"}] if measured else [],
                         "complexity_exponent":measured.get("complexity_exponent"),
                         "quality":measured.get("quality",{"status":"unmeasured"})})
            e["family"] = f["name"]
        fam_out.append({"name":f["name"],"ops":rows,"probes":["synthetic_probe_1","synthetic_probe_2"],
                        "timing_source":"docs/ops/families_timing.json"})
    families = {"schema": 2, "source_graph": "OP_GRAPH.json", "membership_source":"docs/ops/families.json",
                "regex_role":"candidate suggestions only", "families":fam_out}
    known_device = [e for e in edges if e["compute"]["structure"] != "unknown" or e["op"] in accel_names]
    device = {"schema": 2, "source_graph": "OP_GRAPH.json", "gpu_policy": "unmeasured unless device_timing says otherwise",
              "summary":{"total_ops":len(edges),"rows_with_implementation_evidence":len(known_device),
                         "omitted_unknown":len(edges)-len(known_device)},
              "ops": [{"op": e["op"], "compute": e["compute"], "implementations": e["implementations"],
                       "parity": e.get("parity",{"status":"unmeasured"}),
                       "gpu_timing": e.get("gpu_timing","unmeasured")} for e in known_device]}
    sorts = {"schema": 1, "source_graph": "OP_GRAPH.json", "sorts": nodes}
    shapes = _shapes(edges)
    patterns = _patterns()
    return {"OP_GRAPH.json": graph, "OP_FAMILIES.json": families, "OP_DEVICE.json": device,
            "OP_SORTS.json": sorts, "OP_SHAPES.json": shapes, "OP_PATTERNS.json": patterns,
            "SYSTEM_PARAMS.json": _system_params(), "docs/ops/patterns.json": patterns}


def _shapes(edges):
    input_forms={"single":"image","same_view_bundle":"images","different_views":"images",
                 "reference_target":"images","time_series":"video","volume":"volume",
                 "point_mesh":"points","huge_single":"image","batch":"images"}
    output_forms={"dense_field":{"image","depth","phase","flow"},"mask":{"region"},
                  "sparse_features":{"feature","features","contour","points"},"pose":{"pose","transform"},
                  "scalar":{"scalar","feature"},"decision":{"bool","decision"}}
    rows=[]
    for inf,insort in input_forms.items():
      for outf,outs in output_forms.items():
        direct=[e for e in edges if e.get("executable") and insort in e["inputs"] and e["output"] in outs]
        joins=[e for e in direct if len(e["inputs"])>1]
        reductions=[e for e in direct if insort in {"images","polsweep","lightfield","video","volume"}]
        shape="join" if joins else ("bundle_reduction" if reductions else ("map" if inf=="batch" else "serial"))
        rows.append({"input_form":inf,"output_form":outf,"input_sort":insort,"output_sorts":sorted(outs),
                     "shape":shape,"derived_from":{"direct_edges":len(direct),"join_edges":len(joins),"reduce_edges":len(reductions)},
                     "currently_composable":bool(direct) and shape in {"serial","bundle_reduction"},
                     "metric":"IoU" if outf=="mask" else ("RMSE/PSNR" if outf=="dense_field" else "task-specific"),
                     "representative_chain":[direct[0]["op"]] if direct else [],
                     "example":{"status":"verified_graph_edge","op":direct[0]["op"]} if direct else {"status":"none"},
                     "missing":[] if direct else ["typed DAG executor or matching executable edge"]})
    return {"schema":2,"source_graph":"OP_GRAPH.json","input_forms":list(input_forms),
            "output_forms":list(output_forms),"type_constructors":{"images":"seq<image>","video":"seq<image>",
            "polsweep":"seq<polarized_image>","lightfield":"grid<image>","volume":"stack3<image>"},"shapes":rows}


def _patterns():
    names = ["Pipe-and-Filter","Strategy","Adapter","Template Method","Coarse-to-fine",
             "Hypothesize-and-Verify","Voting","Chain of Responsibility","Decorator"]
    return {"schema":1,"source_graph":"OP_GRAPH.json","patterns":[
      {"name":n,"intent":n,"grounded":False,"slots":[{"role":"typed operator","input":"$current","output":"$next",
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
