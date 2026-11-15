#!/usr/bin/env python
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""台帳 op のうち、MCP の隔離した子プロセス(fullseye/mcp/opworker.py)で走らせてよい物を**実測で**決める。

出力 ``docs/mcp_isolated_ops.json`` は実測の台帳(``docs/op_knob.json`` と同じ扱い)で、``tools/gen_op_facets.py`` が
読んで OP_GRAPH の ``verified_executable`` に写す。regen_all の鎖には入れない(回し直すと実行できる op の集合 =
契約が変わるので、人が差分を読む)。

載せる条件(全部):
- 台帳に載っていて、OP_GRAPH の実行先が Python の関数(registry 層の op は従来の経路で走る)。
- 引数にファイル・URL・関数を取らない(名前で判定。数の既定値を持つ ``paths`` のような名前は数として扱う)。
- データ入力の本数が OP_GRAPH と台帳で一致する。
- 見本の入力(``opassist.sample_input``、足りない型は既に通った op の出力)で、**MCP と同じ子プロセス**の中で
  ``VERIFY_TIME_S`` 秒・``VERIFY_RSS`` バイト以内に走り、作業フォルダの外に触らず、宣言の型の値を返し、
  値が JSON の木 + 数値配列で運べ、配列が有限である。

    py -3.11 tools/mcp_isolated_probe.py            # 全部を測って書く(約 2〜5 分)
    py -3.11 tools/gen_op_facets.py                 # OP_GRAPH に写す
    py -3.11 tools/mcp_isolated_probe.py --verify-mcp   # 見本を道具(fullseye_pipeline)の経路で走らせ、落ちた物を外す
    py -3.11 tools/gen_op_facets.py                 # もう一度写す
    py -3.11 tools/mcp_isolated_probe.py --only illumination_design lighting_sweep   # 一部だけ測って表示(書かない)

子プロセスで直接呼んで通っても、道具の経路(handle の形・引数の JSON・応答の上限)で落ちる op がある
(2026-11-13 実測: 配列の引数が list で届く・画像の列が (T,H,W) で届く・中間の上限 128 MiB)。
``--verify-mcp`` は、OP_GRAPH に載った見本を MCP と同じ道具の呼び出しで走らせ、落ちた物を
``mcp_pipeline_failed`` として台帳から外す。
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

OUT = ROOT / "docs" / "mcp_isolated_ops.json"
VERIFY_TIME_S = 5.0
VERIFY_RSS = 1 << 30
MAX_PRODUCER_TRIES = 16
#: 見本の段の数の上限(入力を作る段を含む)。長い鎖は見本として読めず、道具の段数の上限にも当たる。
MAX_EXAMPLE_STAGES = 12
#: 名前がこの接尾辞で終わる引数は数(``path_mm`` は光路長で、ファイルの path ではない)。
_UNIT_SUFFIXES = ("_mm", "_um", "_nm", "_cm", "_m", "_deg", "_rad", "_px", "_s", "_ms", "_hz", "_k", "_ev", "_kev",
                  # 放射量(``source_radiance`` は光源の放射輝度で、ファイルの source ではない)
                  "_radiance", "_irradiance", "_intensity", "_power", "_flux")
#: MCP の隔離実行で受ける計算先。GPU のメモリは子の見張りで縛れないので CPU だけ。
CPU_ONLY = ["cpu"]

#: 見本の値を自動で作れない op の、手で書いた見本(物理として意味のある値)。
EXAMPLES: dict[str, dict] = {
    "bottle_image": {"kwargs": {"radius_mm": 30.0, "wall_mm": 2.0, "height_mm": 120.0, "fill_fraction": 0.6,
                                "n_glass": 1.52, "n_liquid": 1.333, "pixel_pitch_um": 200.0}},
    "pixel_to_world": {"args": [46.3], "kwargs": {"mm_per_px": 0.02}},
    "mm_per_px_from_reference": {"args": [250.0], "kwargs": {"known_mm": 5.0}},
    # ★2026-11-13: 見本の自動の値(数 1 個)では形が合わず落ちていた物(中心は 3 成分、絞りは f 値か NA の一方)
    "lens_spec": {"kwargs": {"focal_mm": 25.0, "f_number": 2.8}},
    "darkfield_scatter_relation": {"kwargs": {"darkfield": 0.6, "thickness_mm": 1.0, "wavelength_nm": 0.05}},
    "scene_box": {"kwargs": {"center_mm": [0.0, 0.0, 5.0], "half_size_mm": [10.0, 10.0, 5.0]}},
    "scene_sphere": {"kwargs": {"center_mm": [0.0, 0.0, 10.0], "radius_mm": 10.0}},
    "scene_cylinder": {"kwargs": {"center_mm": [0.0, 0.0, 10.0], "radius_mm": 10.0, "half_height_mm": 10.0}},
    # 入力の型(table)は同じでも、作る op を決めないと別の表が入って落ちる物: 入力ごとに作る op を名指しする
    "illumination_visibility": {"producers": ["scene_box", None, "light_source"]},
    "trace_rays": {"producers": ["scene_box", None, None]},
}
#: 数 1 個を受けるデータ入力(JSON の数をそのまま params に書ける)。
SCALAR_SORTS = frozenset({"measurement", "scalar"})
_UNSAFE_TYPES = ("PathLike", "IO", "Callable", "URL")


def _json_default(value):
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, np.ndarray) and value.dtype.kind in "biuf" and value.size <= 4096:
        value = value.tolist()
    if value is None or isinstance(value, (bool, int, float, str)):
        if isinstance(value, float) and not np.isfinite(value):
            return None, False
        return value, True
    if isinstance(value, (list, tuple)):
        items = [_json_default(v) for v in value]
        if all(ok for _v, ok in items):
            return [v for v, _ok in items], True
    return None, False


def _unit(name: str, unit):
    """``mm_per_px`` のような名前は接尾辞だけで単位を決めない(px ではなく mm/px)。"""
    if "_per_" in name:
        head, _, tail = name.rpartition("_per_")
        num = head.rsplit("_", 1)[-1]
        if num in ("mm", "um", "nm", "px", "deg", "cm", "m", "lp", "cycles", "counts", "e"):
            return "%s/%s" % (num, tail)
    return unit


def _param_rows(spec: list[dict]) -> list[dict]:
    rows = []
    for sp in spec:
        if sp["kind"] == "data":
            continue
        row = {"name": sp["name"], "kind": sp["kind"], "required": bool(sp.get("required")),
               "unit": _unit(sp["name"], sp.get("unit"))}
        if sp["name"] == "device":
            row.update(kind="choice", choices=list(CPU_ONLY))
            row["doc"] = "MCP runs this op on the CPU only (GPU memory is not bounded by the worker's limit)"
            if sp.get("default") in (None, "cpu"):
                row["default"] = sp.get("default")
            rows.append(row)
            continue
        default, ok = _json_default(sp.get("default"))
        if ok:
            row["default"] = default
        if sp.get("choices"):
            row["choices"] = [str(c) for c in sp["choices"]]
        if sp.get("doc"):
            row["doc"] = " ".join(str(sp["doc"]).split())[:160]
        rows.append(row)
    return rows


def _type_ok(sort: str, value) -> bool:
    import chain_fuzz
    check = chain_fuzz.TYPE_CHECKS.get(sort)
    if value is None:
        return False
    return True if check is None else bool(check(value))


def _finite(value, depth=0) -> bool:
    if isinstance(value, np.ndarray):
        return value.dtype.kind not in "fc" or bool(np.isfinite(value).all())
    if isinstance(value, dict) and depth < 6:
        return all(_finite(v, depth + 1) for v in value.values())
    if isinstance(value, (list, tuple)) and depth < 6:
        return all(_finite(v, depth + 1) for v in value)
    return True


def _candidates():
    """(op, edge, ledger module, table, entry) —— 台帳にあり、実行先が Python の関数で、まだ MCP で走らない物。"""
    import importlib
    import opassist
    from fullseye.opsearch import _graph
    tables = dict(opassist._LEDGERS)
    for edge in _graph()["edges"]:
        if (edge.get("executor") or {}).get("kind") != "python":
            continue
        if edge.get("verified_executable") and not (edge.get("executor") or {}).get("isolation"):
            continue                                  # 従来の検証済み(同じプロセスで走る 11 op)
        mod_name, entry = opassist._ledger_entry(edge["op"])
        if entry is None:
            yield edge["op"], edge, None, None, None
            continue
        importlib.import_module(mod_name)
        yield edge["op"], edge, mod_name, tables[mod_name], entry


def _unsafe_params(entry) -> list[str]:
    """ファイル・URL・関数を取る引数の名前(数の既定値を持つ物は数として扱う)。"""
    import inspect
    if str(ROOT / "tools") not in sys.path:
        sys.path.insert(0, str(ROOT / "tools"))
    import gen_op_facets
    bad = []
    try:
        params = inspect.signature(entry["func"]).parameters.values()
    except (TypeError, ValueError):
        return ["<signature>"]
    for p in params:
        annotation = "" if p.annotation is inspect.Parameter.empty else str(p.annotation)
        named = bool(gen_op_facets._IO_PARAM_RX.search(p.name))
        typed = any(t.lower() in annotation.lower().replace("ratio", "") for t in _UNSAFE_TYPES)
        numeric_default = (isinstance(p.default, (int, float)) and not isinstance(p.default, bool)) or (
            isinstance(p.default, (tuple, list)) and p.default and all(
                isinstance(v, (int, float)) and not isinstance(v, bool) for v in p.default))
        numeric_name = p.name.lower().endswith(_UNIT_SUFFIXES)
        if typed or (named and not numeric_default and not numeric_name):
            bad.append(p.name)
    return bad


def probe(only: set[str] | None = None, verbose: bool = False) -> dict:
    import opassist
    from fullseye.mcp.opworker import OpWorker, OpWorkerError

    worker = OpWorker()
    allowed: dict[str, dict] = {}
    refused: dict[str, str] = {}
    produced: dict[str, list[tuple[str, object]]] = collections.defaultdict(list)   # 台帳の型 -> [(op, 値)]
    func_module: dict[str, str] = {}
    pending = []

    def attempt(name, job, args, kwargs):
        value, _info = worker.run(job, args, kwargs, time_limit_s=VERIFY_TIME_S, max_rss=VERIFY_RSS)
        leftovers = [p for p in os.listdir(worker._tmp) if not p.startswith(("in-", "out-"))]
        if leftovers:
            raise OpWorkerError("filesystem_side_effect", "left files in the scratch folder: %s" % leftovers[:3])
        return value

    def consider(name, edge, mod_name, table, entry, final: bool) -> bool:
        if entry is None:
            refused[name] = "not_in_ledger"
            return True
        unsafe = _unsafe_params(entry)
        if unsafe:
            refused[name] = "io_parameter"
            return True
        try:
            spec = opassist.param_spec(name)
        except ValueError:
            refused[name] = "no_parameter_spec"
            return True
        data = [sp for sp in spec if sp["kind"] == "data"]
        if len(data) != len(edge.get("inputs") or []):
            refused[name] = "input_count_differs_from_graph"
            return True
        job = {"ledger_module": mod_name, "ledger_table": table, "key": opassist._ledger_key(name),
               "data_names": [sp["name"] for sp in data]}
        example = EXAMPLES.get(name)
        try:
            if example is not None and ("args" in example or "kwargs" in example):
                args, kwargs = list(example.get("args", [])), dict(example.get("kwargs", {}))
            else:
                args, kwargs = opassist.sample_input(name)
            if example is not None and example.get("producers"):
                # 名指しした入力は、見本の種ではなく、名指しの op の出力にする
                args = [None if i < len(example["producers"]) and example["producers"][i] else a
                        for i, a in enumerate(args)]
        except Exception as exc:  # noqa: BLE001
            refused[name] = "no_sample_input"
            if verbose:
                print("  sample:", name, type(exc).__name__, str(exc)[:120])
            return True
        if any(v is None for v in kwargs.values()):
            refused[name] = "no_sample_input"
            return True
        if any(not _json_default(v)[1] for v in kwargs.values()):
            refused[name] = "sample_argument_not_json"
            return True
        missing = [i for i, a in enumerate(args) if a is None]
        choices: list[list] = [[(None, a)] for a in args]
        named = list((example or {}).get("producers") or [])
        for i in missing:
            sort = data[i]["sort"]
            want = named[i] if i < len(named) else None
            if want is not None:
                # 作る op の名指し: その op が通っていれば、その出力だけを使う
                pool = [item for item in produced.get(sort, []) if item[0] == want][:1]
                if not pool:
                    if final:
                        refused[name] = "no_sample_input"
                    return final
                choices[i] = pool
                continue
            # 同じ実装モジュール(illumdesign の light_source → defect_contrast)を先に、次に同じ台帳の物
            home = getattr(entry["func"], "__module__", None)
            pool = sorted(produced.get(sort, []), key=lambda item: (
                func_module.get(item[0]) != home, opassist._ledger_entry(item[0])[0] != mod_name,
                item[0]))[:MAX_PRODUCER_TRIES]
            if not pool:
                if final:
                    refused[name] = "no_sample_input"
                return final
            choices[i] = pool
        import itertools
        last = "no_sample_input"
        for n_try, combo in enumerate(itertools.product(*choices)):
            if n_try >= MAX_PRODUCER_TRIES:
                break
            try:
                value = attempt(name, job, [v for _src, v in combo], kwargs)
            except OpWorkerError as exc:
                last = {"op_error": "sample_run_failed"}.get(exc.reason, exc.reason)
                if verbose:
                    print("  run:", name, exc.reason, exc.error_type, str(exc)[:160])
                if exc.reason in ("time_limit", "memory_limit", "worker_died"):
                    break
                continue
            ledger_out = entry.get("out")
            if not _type_ok(ledger_out, value):
                last = "output_type_differs_from_declared"
                continue
            if not _finite(value):
                last = "nonfinite_output"
                continue
            stages = []
            refs = []
            for (src, _v), sp, graph_sort in zip(combo, data, edge["inputs"]):
                if src is None:
                    refs.append("have:%s" % graph_sort)
                else:
                    # 入力を作る op の見本の段を丸ごと前に置く(段の番号をずらす)
                    offset = len(stages)
                    for st in allowed[src]["example"]["stages"]:
                        st = json.loads(json.dumps(st))
                        if "inputs" in st:
                            st["inputs"] = ["stage:%d" % (int(r[6:]) + offset) if r.startswith("stage:") else r
                                            for r in st["inputs"]]
                        for pv in (st.get("params") or {}).values():
                            if isinstance(pv, dict) and str(pv.get("ref", "")).startswith("stage:"):
                                pv["ref"] = "stage:%d" % (int(pv["ref"][6:]) + offset)
                        stages.append(st)
                    refs.append("stage:%d" % len(stages))
            if len(stages) + 1 > MAX_EXAMPLE_STAGES:
                last = "example_chain_too_long"
                continue
            literal = {}
            if example is not None and example.get("args"):
                literal = {sp["name"]: a for sp, a in zip(data, example["args"])
                           if sp["sort"] in SCALAR_SORTS and isinstance(a, (int, float))}
                refs = [r for r, sp in zip(refs, data) if sp["name"] not in literal]
            stage = {"op": name}
            if refs:
                stage["inputs"] = refs
            params = dict(literal, **{k: _json_default(v)[0] for k, v in kwargs.items()})
            if params:
                stage["params"] = params
            stages.append(stage)
            allowed[name] = {
                "ledger": [mod_name, table], "key": job["key"],
                "data": [{"name": sp["name"], "sort": sp["sort"],
                          "literal": sp["sort"] in SCALAR_SORTS} for sp in data],
                "params": _param_rows(spec), "example": {"stages": stages},
                # 見本で配列だった引数(K など)。道具の JSON では list で届くので、渡す前に配列にする
                "array_params": sorted(k for k, v in kwargs.items() if isinstance(v, np.ndarray)),
            }
            func_module[name] = getattr(entry["func"], "__module__", None)
            if len(produced[ledger_out]) < 600:
                produced[ledger_out].append((name, value))
            return True
        refused[name] = last
        return True

    try:
        for name, edge, mod_name, table, entry in _candidates():
            if only and name not in only:
                continue
            if not consider(name, edge, mod_name, table, entry, final=False):
                pending.append((name, edge, mod_name, table, entry))
        for round_no in range(3):                       # 既に通った op の出力を入力に使う(最大 3 巡)
            still = []
            for item in pending:
                if not consider(*item, final=(round_no == 2)):
                    still.append(item)
            if len(still) == len(pending):
                for item in still:
                    consider(*item, final=True)
                still = []
            pending = still
            if not pending:
                break
    finally:
        worker.close()
    return {"schema": 1, "generated_by": "tools/mcp_isolated_probe.py",
            "limits": {"verify_time_s": VERIFY_TIME_S, "verify_rss_bytes": VERIFY_RSS},
            "checks": ["ran_in_the_mcp_worker", "no_file_outside_scratch", "no_network", "declared_output_type",
                       "finite", "json_tree_and_numeric_arrays_only", "within_time_and_memory"],
            "counts": {"allowed": len(allowed), "refused": len(refused),
                       "refused_by_reason": dict(sorted(collections.Counter(refused.values()).items()))},
            "ops": {k: allowed[k] for k in sorted(allowed)},
            "refused": {k: refused[k] for k in sorted(refused)}}


def sample_stages(stages: list[dict], isolated: dict, store) -> list[dict]:
    """見本の段が読む ``have:<型>`` を、その段の op の見本の入力のハンドルに置き換える(MCP で来る形)。

    画像の列(seq<image>)は (T,H,W) の配列(fullseye_load_stack と同じ)、それ以外は前の段の op が
    返す値と同じく、見本の値をそのまま置く。"""
    import opassist
    out = []
    for stage in stages:
        stage = json.loads(json.dumps(stage))
        refs = stage.get("inputs", [])
        if any(ref.startswith("have:") for ref in refs):
            executor = isolated[stage["op"]]["executor"]
            values, _kwargs = opassist.sample_input(stage["op"])
            given = [v for n, v in zip(executor["data_names"], values) if n not in stage.get("params", {})]
            if len(given) != len(refs):
                raise ValueError("%s: %d sample inputs for %d refs" % (stage["op"], len(given), len(refs)))
            handles = []
            for n, (ref, value) in enumerate(zip(refs, given)):
                if ref.startswith("have:"):
                    sort = ref.split(":", 1)[1]
                    if sort in ("seq<image>", "images") and isinstance(value, (list, tuple)):
                        value = np.stack([np.asarray(v, dtype=np.float64) for v in value])
                    ref = store.put(value, sort=sort, provenance=[{"input": n}])["handle"]
                handles.append(ref)
            stage["inputs"] = handles
            stage["allow_reuse"] = True
        out.append(stage)
    return out


def verify_mcp() -> dict:
    """OP_GRAPH に載った隔離 op の見本を、道具(``fullseye_pipeline``)の経路で走らせ、落ちた物を台帳から外す。"""
    import tempfile
    from fullseye.mcp import server as S
    from fullseye.mcp.catalog import Catalog
    from fullseye.mcp.handles import HandleStore
    from fullseye.mcp.opworker import close_worker
    from fullseye.opsearch import _graph

    ledger = json.loads(OUT.read_text(encoding="utf-8"))
    isolated = {e["op"]: e for e in _graph()["edges"] if (e.get("executor") or {}).get("isolation") == "worker"}
    if set(isolated) != set(ledger["ops"]):
        raise SystemExit("OP_GRAPH does not match docs/mcp_isolated_ops.json; run tools/gen_op_facets.py first")
    cat = Catalog.load()
    dropped: dict[str, str] = {}
    try:
        for name in sorted(isolated):
            with tempfile.TemporaryDirectory(prefix="fullseye-probe-") as tmp:
                store = HandleStore(thumb_dir=tmp)
                try:
                    stages = sample_stages(isolated[name]["example"]["stages"], isolated, store)
                    r = S.call_tool("fullseye_pipeline", {"stages": stages, "vision": "none"}, cat, store)
                except Exception as exc:  # noqa: BLE001 - 道具が断った・落ちた物は全部外す
                    dropped[name] = "%s: %s" % (type(exc).__name__, str(exc)[:160])
                    continue
                if r["isError"]:
                    bad = next((s for s in r["structuredContent"].get("stages", []) if s.get("status") == "failed"), {})
                    dropped[name] = "%s: %s" % (bad.get("reason"), json.dumps(bad.get("error"), ensure_ascii=False)[:160])
    finally:
        close_worker()
    for name in dropped:
        ledger["ops"].pop(name)
        ledger["refused"][name] = "mcp_pipeline_failed"
    # 入力の中身に依存しない op(採点が断る一覧)を、gen_mcp_input_independent と同じ 7 枚・同じ判定で決める。
    #   鎖(regen_all)の中で 1,500 op を 7 回ずつ走らせない(20 分を超え、時間の上限で一覧が環境で揺れる)。
    import fssystem
    sys.path.insert(0, str(ROOT / "tools"))
    import gen_mcp_input_independent as gmi
    one_input = [e for name, e in sorted(isolated.items()) if name not in dropped and len(e.get("inputs") or []) == 1]
    with fssystem.system(mcp_op_time_limit_s=int(VERIFY_TIME_S)):
        jcat, jstore, jinputs = gmi._context()
        try:
            flagged, tested = gmi.judge(one_input, jcat, jstore, jinputs)
        finally:
            close_worker()
    ledger["input_independent"] = {k: flagged[k] for k in sorted(flagged)}
    ledger["input_independence_tested"] = sorted(tested)
    ledger["refused"] = {k: ledger["refused"][k] for k in sorted(ledger["refused"])}
    ledger["counts"] = {"allowed": len(ledger["ops"]), "refused": len(ledger["refused"]),
                        "refused_by_reason": dict(sorted(collections.Counter(ledger["refused"].values()).items()))}
    if "verified_through_mcp_pipeline" not in ledger["checks"]:
        ledger["checks"].append("verified_through_mcp_pipeline")
    OUT.write_text(json.dumps(ledger, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    return dropped


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--only", nargs="*", help="この op だけ測って表示する(書かない)")
    ap.add_argument("--verify-mcp", action="store_true",
                    help="OP_GRAPH の見本を道具の経路で走らせ、落ちた op を台帳から外す(gen_op_facets の後)")
    args = ap.parse_args(argv)
    if args.verify_mcp:
        dropped = verify_mcp()
        for name, why in sorted(dropped.items()):
            print("dropped %s: %s" % (name, why))
        print("verify-mcp: dropped %d; now %d allowed" % (len(dropped),
                                                          len(json.loads(OUT.read_text(encoding="utf-8"))["ops"])))
        return 0
    result = probe(set(args.only) if args.only else None, verbose=bool(args.only))
    if args.only:
        print(json.dumps({k: result[k] for k in ("counts", "ops", "refused")}, ensure_ascii=False, indent=1)[:6000])
        return 0
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("wrote %s: %d allowed, %d refused %s" % (OUT.relative_to(ROOT), result["counts"]["allowed"],
                                                    result["counts"]["refused"], result["counts"]["refused_by_reason"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
