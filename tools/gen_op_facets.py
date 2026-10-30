# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0.
"""Generate the single operator graph and its AI-facing facets.

The graph is the source of truth: sorts are nodes and operators are (possibly
n-ary) hyperedges.  Families, device advice, pipeline shapes, patterns and the
sort guide are attributes or queries over that graph, never independent op
inventories.
"""
from __future__ import annotations

import argparse
import ast
import inspect
import json
import os
import random
import re
import shutil
import sys
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
DATA = ROOT / "fullseye" / "data"
DOCS = ROOT / "docs" / "ops"

# Public canonical vocabulary is the executor vocabulary.  Graph/ledger aliases
# are accepted at every API boundary and normalized exactly once here.
SORT_ALIASES = {"image2d": "image", "mask": "region", "contour2d": "contour",
                "features": "feature", "pointcloud": "points", "images":"seq<image>",
                "video":"seq<image>"}
TYPE_CONSTRUCTORS={"images":"seq<image>","video":"seq<image>","polsweep":"seq<polarized_image>",
                   "lightfield":"grid<image>","volume":"stack3<image>"}
ACQUIRABLE = {
    "image": "camera acquisition contract",
    "images": "multi-frame camera acquisition contract",
    "polsweep": "polarization camera/analyzer sweep",
    "points": "range sensor or point sampler",
    "lightfield": "light-field camera grid",
    "volume": "tomographic/volumetric acquisition",
    "video": "camera stream acquisition",
}
# These non-registry callables are exercised with meaningful synthetic arrays
# by the named gate.  Keeping this allowlist small and reviewable is deliberate.
VERIFIED_PYTHON = {
    "polarization_render", "polarization_dolp_map", "decode_fringe",
    "deflectometry_phase_to_slope", "fringe_ftp_phase", "depth_from_focus",
    "fit_circle_geometric", "fit_curve_principal_axis",
    "phase_correlation_shift", "fit_surface_principal_axes",
}
DATA_INPUT_OVERRIDES = {
    "triangulate": [("uv1", "image"), ("uv2", "image"), ("P1", "matrix"), ("P2", "matrix")],
    "recover_pose": [("test", "image"), ("reference", "image"), ("K1", "matrix")],
}
REF_PARAMETER_OVERRIDES = {
    "decode_fringe": {"ref_phase": "image", "mask": "region"},
    "deflectometry_phase_to_slope": {"rig": "table"},
    "recover_pose": {"K2": "matrix"},
}
DUPLICATE_EXEMPTIONS = {
    "gaussians_to_voxel": "chain_fuzz compatibility alias; first declaration is the public contract",
}
POLYMORPHIC_PASSTHROUGHS = {
    "identity": "ops.py:_identity returns its input value unchanged",
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
        output = "unknown"
    elif output == "untyped":
        output = "unknown"
    semantics = ("source" if not inputs and output != "unknown" else
                 "poly" if output == "poly" else
                 "unknown" if output == "unknown" or "unknown" in inputs else "typed")
    return inputs, output, semantics, bool(inputs)


def passthrough_semantics(name: str, inputs: list[str], output: str) -> tuple[list[str], str]:
    """Turn only source-backed identity contracts from historical ``any`` into poly."""
    if name in POLYMORPHIC_PASSTHROUGHS and inputs == ["any"] and output == "any":
        return ["poly"], "poly"
    return inputs, output

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

def _python_functions() -> dict[str, dict]:
    """Read top-level signatures without importing modules or running user code."""
    found = {}
    for path in sorted(ROOT.glob("*.py")):
        if path.name.startswith(("test_", "setup")):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name.startswith("_"):
                continue
            args = node.args.posonlyargs + node.args.args
            defaults = [None] * (len(args) - len(node.args.defaults)) + list(node.args.defaults)
            params = []
            for arg, default in zip(args, defaults):
                ann = ast.unparse(arg.annotation) if arg.annotation else None
                rec = {"name": arg.arg, "type": ann or "unannotated",
                       "required": default is None, "range": "undocumented", "unit": "undocumented"}
                if default is not None:
                    try:
                        value = ast.literal_eval(default)
                        json.dumps(value)
                        rec["default"] = value
                    except (ValueError, TypeError): rec["default"] = ast.unparse(default)
                params.append(rec)
            found.setdefault(node.name, {"module": path.stem, "callable": node.name, "parameters": params,
                                         "doc": ast.get_docstring(node) or ""})
    return found


_IO_PARAM_RX = re.compile(
    r"(?:^|_)(?:path|paths|file|files|filename|filepath|dir|directory|folder|url|uri|"
    r"source|destination|target|callback|callable|function|func|writer|reader|stream|socket)(?:$|_)", re.I)


def _runtime_function(fn) -> dict:
    """Describe the exact callable registered by chain_fuzz, never a namesake."""
    module = getattr(fn, "__module__", None)
    qualname = getattr(fn, "__qualname__", None)
    if not module or not qualname:
        raise RuntimeError("operator has no importable runtime target: %r" % (fn,))
    params = []
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError) as exc:
        return {"module": module, "callable": qualname, "parameters": [],
                "signature_error": type(exc).__name__}
    for p in sig.parameters.values():
        if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            continue
        annotation = "unannotated" if p.annotation is inspect.Parameter.empty else str(p.annotation)
        rec = {"name": p.name, "type": annotation,
               "required": p.default is inspect.Parameter.empty,
               "range": "undocumented", "unit": "undocumented"}
        if p.default is not inspect.Parameter.empty:
            try:
                json.dumps(p.default)
                rec["default"] = p.default
            except (TypeError, ValueError):
                rec["default"] = repr(p.default)
        params.append(rec)
    return {"module": module, "callable": qualname, "parameters": params,
            "doc": inspect.getdoc(fn) or ""}


def _mcp_unsafe_parameter(parameters: list[dict]) -> str | None:
    for p in parameters:
        name, annotation = p.get("name", ""), p.get("type", "")
        if _IO_PARAM_RX.search(name) or re.search(r"\b(?:PathLike|IO|Callable|URL)\b", annotation, re.I):
            return p.get("name") or "parameter"
    return None


def _verified_registry_ops() -> dict[str, dict]:
    """CPU-only execution allowlist; verification happens in this generation run."""
    import warnings
    import numpy as np
    import chain_fuzz
    import op_probe
    import ops
    results = {}
    for registry_op in ops.REGISTRY:
        name, out_sort = registry_op.name, registry_op.out_sort
        old_cwd=os.getcwd(); np_state=np.random.get_state(); py_state=random.getstate(); tmp=None
        try:
            with tempfile.TemporaryDirectory(prefix="fullseye-verify-",ignore_cleanup_errors=True) as tmp:
                os.chdir(tmp); before={p.relative_to(tmp).as_posix() for p in Path(tmp).rglob("*")}
                value = op_probe.sample_input(registry_op.in_sort,np.random.default_rng(20261028),structured=True)
                if value is None: raise ValueError("no_sample_input")
                started=time.monotonic()
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore"); result=registry_op.fn(value,0.5,0.5)
                elapsed=time.monotonic()-started
                after={p.relative_to(tmp).as_posix() for p in Path(tmp).rglob("*")}
                if elapsed>2.0: raise TimeoutError("execution exceeded 2 seconds")
                if before != after: raise RuntimeError("filesystem_side_effect: %s"%sorted(after-before))
                now=np.random.get_state()
                if np_state[0]!=now[0] or not np.array_equal(np_state[1],now[1]) or np_state[2:]!=now[2:]:
                    raise RuntimeError("numpy_random_state_changed")
                if py_state != random.getstate(): raise RuntimeError("python_random_state_changed")
                check=chain_fuzz.TYPE_CHECKS.get(out_sort)
                if result is None: raise ValueError("returned_none")
                if check is not None and not check(result): raise TypeError("output_type_mismatch")
                arrays=([result] if isinstance(result,np.ndarray) else
                        [v for v in result.values() if isinstance(v,np.ndarray)] if isinstance(result,dict) else [])
                if any(a.dtype.kind in "fc" and not np.isfinite(a).all() for a in arrays):
                    raise ValueError("nonfinite_output")
                results[name]={"status":"ok","under_2_seconds":True}
        except Exception as exc:
            results[name]={"status":"failed","reason":type(exc).__name__,"detail":str(exc)[:200]}
        finally:
            os.chdir(old_cwd); np.random.set_state(np_state); random.setstate(py_state)
            if tmp: shutil.rmtree(tmp,ignore_errors=True)
    return results


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
            if key == "a" and name in {"median","local_std"}:
                rec.update({"mapping":"docstring _k(a)","physical_values":[3,5,7,9],"unit":"pixels"})
            elif key == "b" and name == "local_std":
                rec.update({"mapping":"docstring _k(b)","physical_values":[3,5,7,9],"unit":"pixels"})
            elif key == "a" and name == "gaussian":
                rec.update({"mapping":"sigma = 0.3 + 2.7*a","physical_range":[0.3,3.0],"unit":"pixels"})
            elif key == "a" and name == "lowpass":
                rec.update({"mapping":"cutoff = 0.05 + 0.4*a","physical_range":[0.05,0.45],"unit":"normalized_frequency"})
            if key == "a" and knob.get("breakpoints"):
                rec["discrete"] = knob["breakpoints"]
        out[key] = rec
    return out

def _system_params():
    import fssystem
    return {"schema":2,"generated_from":"fssystem.SYSTEM_PARAMS","params":{
        name:{"default":spec["default"],"values":list(spec["values"]),"meaning":spec["doc"],
              "hide_from_ai":True,"applied_by":list(spec["applied_by"] or []),
              "affects_numbers":bool(spec["affects_numbers"]),
              "status":"applied" if spec["applied_by"] else "declared_not_applied"}
        for name,spec in sorted(fssystem.SYSTEM_PARAMS.items())}}


def build() -> dict[str, object]:
    import conversion_matrix as cm
    a = cm.analyse()
    knobs = _knobs()
    registry_verification = _verified_registry_ops()
    verified_registry = {name for name,result in registry_verification.items() if result["status"]=="ok"}
    import ops as runtime_ops
    registry_by_name = {op.name:op for op in runtime_ops.REGISTRY}
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
    runtime_functions = {}
    for name, category, ins, out, _fn in a["ops"]:
        if name not in index_names:
            excluded_chain_only.append({"op": name, "reason": "not present in public OP_INDEX"})
            continue
        if name in registry_by_name:
            registered=registry_by_name[name]
            ins,out,_fn=registered.in_sort,registered.out_sort,registered.fn
        ins, out = split_inputs(ins), canonical_sort(out)
        if name in nary:
            ins = [canonical_sort(x) for x in nary[name]["in_sorts"]]
        roles = None
        if name in DATA_INPUT_OVERRIDES:
            roles = [r for r, _s in DATA_INPUT_OVERRIDES[name]]
            ins = [canonical_sort(s) for _r, s in DATA_INPUT_OVERRIDES[name]]
        ins, out = passthrough_semantics(name, ins, out)
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
        target = _runtime_function(_fn)
        if roles is None and len(ins) > 1 and len(set(ins)) < len(ins):
            names=[p["name"] for p in target["parameters"][:len(ins)]]
            if len(names)==len(ins):
                roles = names
        previous = runtime_functions.get(name)
        if previous and (previous["module"], previous["callable"]) != (target["module"], target["callable"]):
            raise RuntimeError("operator %s resolves to multiple runtime targets" % name)
        runtime_functions[name] = target
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
        if name in POLYMORPHIC_PASSTHROUGHS:
            edge["type_evidence"] = POLYMORPHIC_PASSTHROUGHS[name]
        if roles:
            edge["input_roles"] = roles
        if name in REF_PARAMETER_OVERRIDES:
            edge["ref_parameters"] = REF_PARAMETER_OVERRIDES[name]
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
        ins, out = passthrough_semantics(name, ins, out)
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
        if name in POLYMORPHIC_PASSTHROUGHS:
            edge["type_evidence"] = POLYMORPHIC_PASSTHROUGHS[name]
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

    executable_reasons = Counter()
    for edge in edges:
        if edge.get("executable"):
            edge["executor"] = {"kind": "registry", "alias":edge["op"]}
            executable_reasons["registry"] += 1
        fn = runtime_functions.get(edge["op"])
        if fn is None and edge["op"] in registry_by_name:
            fn = _runtime_function(registry_by_name[edge["op"]].fn)
        if fn is not None:
            edge["runtime_target"] = {"module": fn["module"], "callable": fn["callable"]}
            if edge.get("executor",{}).get("kind")=="registry":
                edge["executor"].update(edge["runtime_target"])
        if not edge.get("executable") and edge.get("type_semantics") == "unknown":
            edge["executable_reason"] = "unknown_input_or_output_sort"
        elif not edge.get("executable") and fn is None:
            edge["executable_reason"] = "python_callable_not_found"
        elif not edge.get("executable") and len(fn["parameters"]) < len(edge["inputs"]):
            edge["executable_reason"] = "python_signature_has_fewer_inputs_than_graph"
        elif not edge.get("executable"):
            edge["executable"] = True
            edge["executor"] = {"kind": "python", "module": fn["module"], "callable": fn["callable"]}
            edge["parameter_schema"] = fn["parameters"][len(edge["inputs"]):]
            executable_reasons["python_signature"] += 1
        if edge.get("executor",{}).get("kind")=="python":
            edge.pop("parameters",None)

        unsafe = _mcp_unsafe_parameter((fn or {}).get("parameters", []))
        if unsafe:
            edge["verified_executable"] = False
            edge["not_executable_in_mcp"] = "io_side_effect"
            edge["mcp_rejection_detail"] = "unsafe parameter: %s" % unsafe
        elif edge.get("executor", {}).get("kind") == "registry" and edge["op"] in verified_registry:
            edge["verified_executable"] = True
            edge["verification"] = {"source": "tools/gen_op_facets.py::_verified_registry_ops", "status": "ok",
                                    "checks": ["executed", "typed", "shape", "finite", "temporary_cwd",
                                               "filesystem_unchanged", "random_state_unchanged", "under_2_seconds"]}
        elif edge.get("executor", {}).get("kind") == "python" and edge["op"] in VERIFIED_PYTHON:
            edge["verified_executable"] = True
            edge["verification"] = {
                "source": "tests/test_op_facets_2026_10_28.py::test_three_multi_input_business_dags_execute_through_mcp",
                "status": "ok", "checks": ["executed", "typed", "shape", "finite", "meaningful_synthetic_input"]}
        else:
            edge["verified_executable"] = False
            edge["not_executable_in_mcp"] = "not_verified"
            if edge.get("executor",{}).get("kind")=="registry" and edge["op"] in registry_verification:
                edge["verification"] = registry_verification[edge["op"]]

    stochastic_rx = re.compile(r"^(?:aug_|tb_random_)|random")
    global_rx = re.compile(r"equalize|autocontrast|autolevel")
    bundle_sorts = {"images","seq<image>","video","polsweep","lightfield","volume"}
    for edge in edges:
        if stochastic_rx.search(edge["op"]):
            edge["bundle_semantics"] = "stochastic"
        elif any(x in bundle_sorts for x in edge["inputs"]) or edge["output"] in bundle_sorts:
            edge["bundle_semantics"] = "temporal" if "video" in edge["inputs"] else "stack_global"
        elif (len(edge["inputs"]) == 1 and edge["inputs"][0] == edge["output"] and
              edge["compute"]["structure"] in {"elementwise","neighborhood_stencil"} and
              not global_rx.search(edge["op"])):
            edge["bundle_semantics"] = "elementwise"
        else:
            edge["bundle_semantics"] = "unknown"

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
              for e in edges if e.get("executable") and e.get("bundle_semantics")=="elementwise"
              and len(e["inputs"])==1 and e["inputs"][0]==e["output"]]
    for row in lifted:
        src={"kind":"derived_map","value":row["base_op"]}; sid=intern(src)
        edges.append({"op":row["op"],"inputs":[row["input"]],"output":row["output"],
                      "category":"map","family":None,"type_semantics":"typed","consumes_input":True,
                      "bundle_semantics":"elementwise","executable":False,"verified_executable":False,
                      "executable_reason":"map_executor_not_implemented","not_executable_in_mcp":"not_verified",
                      "compute":{"structure":"elementwise","intensity":"derived","source_ref":sid},
                      "implementations":[],"parameters":{},"source_ref":sid,
                      "population_extension_reason":"grounded elementwise lifting"})
        for sort in (row["input"],row["output"]):
            if sort not in {n["sort"] for n in nodes}:
                nodes.append({"sort":sort,"container":_container(sort),"size_hint":"input-dependent",
                              "produced_by":0,"consumed_by":0,"generator":False,"type_check":False,
                              "choose_when":"derived map container","source":"derived map"})
    parameter_summary={"measured_ops":sum(bool(knobs.get(e["op"])) for e in edges),
                       "a_unused":sum("a" in e.get("parameters",{}) and e["parameters"]["a"].get("source")!="unmeasured" and not e["parameters"]["a"].get("used") for e in edges),
                       "b_unused":sum("b" in e.get("parameters",{}) and e["parameters"]["b"].get("source")!="unmeasured" and not e["parameters"]["b"].get("used") for e in edges),
                       "reason":"docs/op_knob.json measured no output effect"}
    graph = {"schema": 2, "generated_by": "tools/gen_op_facets.py", "model": "typed AND-OR hypergraph",
             "sort_aliases": SORT_ALIASES, "population": "union of docs/OP_INDEX.json and chain_fuzz catalog",
             "acquirable_sorts": [{"sort": s, "source": " / ".join(srcs)} for s,srcs in sorted(
                 (lambda grouped: grouped.items())({s:[src for raw,src in ACQUIRABLE.items() if canonical_sort(raw)==s]
                                                    for s in {canonical_sort(raw) for raw in ACQUIRABLE}}))],
             "type_constructors":TYPE_CONSTRUCTORS,
             "lifted_map_edges":lifted,
             "parameter_summary":parameter_summary,
             "execution_summary":{"executable":sum(bool(e.get("executable")) for e in edges),
                                  "reasons":dict(sorted(executable_reasons.items())),
                                  "not_executable_reasons":dict(sorted(Counter(
                                      e.get("executable_reason", "unclassified") for e in edges
                                      if not e.get("executable")).items()))},
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
    def _validate_rows(families, measurements):
        if not families:
            raise RuntimeError("family ledger is empty")
        empty=[f["name"] for f in families if not f.get("members")]
        missing=[m["op"] for f in families for m in f.get("members",[]) if m["op"] not in measurements]
        if empty or missing:
            raise RuntimeError("invalid family measurements: empty=%r missing=%r" % (empty,missing))
    _validate_rows(ledger.get("families",[]),timing.get("measurements") or {})
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
    shapes = _shapes(edges)
    return {"OP_GRAPH.json": graph, "OP_FAMILIES.json": families,
            "OP_SHAPES.json": shapes, "SYSTEM_PARAMS.json": _system_params()}


def _shapes(edges):
    input_forms={"single":"image","same_view_bundle":"seq<image>","different_views":"seq<view<image>>",
                 "reference_target":"tuple<image,image>","time_series":"seq<image>","volume":"volume",
                 "point_mesh":"points","huge_single":"image","batch":"seq<image>"}
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
                     "currently_composable":bool(direct),
                     "metric":"IoU" if outf=="mask" else ("RMSE/PSNR" if outf=="dense_field" else "task-specific"),
                     "representative_chain":[direct[0]["op"]] if direct else [],
                     "example":{"status":"verified_graph_edge","op":direct[0]["op"]} if direct else {"status":"none"},
                     "missing":[] if direct else ["typed DAG executor or matching executable edge"]})
    return {"schema":2,"source_graph":"OP_GRAPH.json","input_forms":list(input_forms),
            "output_forms":list(output_forms),"type_constructors":TYPE_CONSTRUCTORS,"shapes":rows}


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
