"""変異探針を層ごとに実行し、門が検出した試験を記録する。

外部計算環境では層ごとに次の形で実行する。層名だけを t1, t2, t3,
t4, t5, t5b, t6 のいずれかに替える。

``python tools/mutation_probe.py run --tier t1 --kinds a,b,c,d,e,f,g,g2,h --baseline --out out/probe --pytest-args "-n 4" --max-hours 11``

``list`` は注入先を表示する。``inject`` は探針モジュールと登録ブロックを
追加し、``restore`` は自分が追加したバイトだけを検証して取り除く。``run`` は
基準実行と各変異を順番に実行し、JUnit XML、個別 JSON、集計 JSON を残す。
既存の個別 JSON は再利用するため、中断後も同じコマンドで再開できる。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

BEGIN = "# MUTATION-PROBE BEGIN"
END = "# MUTATION-PROBE END"
STATE = ".mutation_probe_state.json"
KINDS = {
    "a": "well-formed",
    "b": "raises",
    "c": "nan",
    "d": "wrong_type",
    "e": "nondeterministic",
    "f": "ignores_params",
    "g": "no_description",
    "g2": "english_only_description",
    "h": "accepts_empty_input",
}
CAUGHT_KEYS = tuple(KINDS[k] for k in ("b", "c", "d", "e", "f", "g", "g2", "h"))

TIERS = {
    "t1": ("ops.py", "ops.REGISTRY", "Op を REGISTRY と索引用の派生表へ追加"),
    "t2": ("imgops_nary.py", "imgops_nary._DEFS", "NaryOp 定義を build_nary が発見"),
    "t3": ("backends_color.py", "backends_color._DEFS", "色 sort 定義を build と索引が発見"),
    "t4": ("opsmath.py", "OPSMATH typed ledger + tb_ bridge", "image2d 単入力台帳を typed_catalog と橋が発見"),
    "t5": ("opsmath.py", "OPSMATH typed ledger (no bridge)", "table 出力台帳を ledger が発見し橋は対象外"),
    "t5b": ("ops3d.py", "OPS3D", "3-D 台帳を typed_catalog と ledger が発見"),
    "t6": ("fullseye/__init__.py", "public facade", "facade 属性としてのみ公開"),
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_inventory(root: Path) -> dict:
    return json.loads((root / "docs" / "gate_inventory.json").read_text(encoding="utf-8"))


def list_probe(root: Path) -> None:
    inv = load_inventory(root)
    for tier in inv["tiers"]:
        tid = tier["id"]
        spec = TIERS.get(tid)
        status = "supported" if spec and (root / spec[0]).is_file() else "unsupported"
        detail = f"{spec[0]} / {spec[1]} / {spec[2]}" if spec else "注入先なし"
        print(f"{tid}: {tier['ja']} / {tier['en']} / {status} / {detail}")
    for key, description in KINDS.items():
        print(f"{key}: {description}")


def _module_text(kind: str, tier: str) -> str:
    doc = "" if kind == "g" else (
        "Return a probe value for the supplied input." if kind == "g2" else
        """入力値と二つの調整値から、契約に従う探針結果を返す。

    Return a probe result from the input and two controls.
    """
    )
    bodies = {
        "a": "return np.clip(x * (0.5 + a) + b * 0.1, 0.0, 1.0)",
        "b": "raise RuntimeError('mutation probe')",
        "c": "return np.full_like(x, np.nan, dtype=np.float64)",
        "d": "return np.asarray(x).tolist()",
        "e": "\n    global _counter\n    _counter += 1\n    return np.asarray(x, dtype=np.float64) + _counter * 1e-3",
        "f": "return np.asarray(x, dtype=np.float64).copy()",
        "g": "return np.clip(x * (0.5 + a) + b * 0.1, 0.0, 1.0)",
        "g2": "return np.clip(x * (0.5 + a) + b * 0.1, 0.0, 1.0)",
        "h": "return np.asarray(x, dtype=np.float64).copy()",
    }
    if tier == "t5":
        bodies.update({
            "a": "return {'value': float(x.mean() * (0.5 + a) + b * 0.1)}",
            "c": "return {'value': float('nan')}",
            "e": "\n    global _counter\n    _counter += 1\n    return {'value': float(x.mean()) + _counter * 1e-3}",
            "f": "return {'value': float(x.mean())}",
            "g": "return {'value': float(x.mean() * (0.5 + a) + b * 0.1)}",
            "g2": "return {'value': float(x.mean() * (0.5 + a) + b * 0.1)}",
            "h": "return {'value': float(x.mean()) if x.size else 0.0}",
        })
    body = bodies[kind]
    empty_guard = "" if kind == "h" else "\n    if x.size == 0:\n        raise ValueError('empty input')"
    return (
        '"""一時的な変異探針。mutation_probe.py が生成し、restore が削除する。"""\n'
        "import numpy as np\n\n_counter = 0\n\n"
        f"def probe(value, a=0.25, b=0.75):\n    {doc!r}\n"
        "    x = np.asarray(value, dtype=np.float64)"
        f"{empty_guard}\n    {body}\n"
    )


def _block(tier: str, name: str) -> str:
    if tier == "t1":
        code = f'''from probe_injected import probe as _mutation_probe_fn
_mutation_probe_op = Op({name!r}, "probe", "", IMAGE, IMAGE, _mutation_probe_fn, _c({name!r}))
REGISTRY.append(_mutation_probe_op)
RT[{name!r}] = _mutation_probe_fn
_BY_NAME[{name!r}] = _mutation_probe_op
OPS = tuple((op.name, op.fn) for op in REGISTRY)
N_OPS = len(REGISTRY)
OP_MODULE[{name!r}] = "probe_injected"
SLOTS = {{op.name: i for i, op in enumerate(REGISTRY)}}'''
    elif tier == "t2":
        code = f'''from probe_injected import probe as _mutation_probe_fn
_DEFS.append(({name!r}, "add_image", 2, (IMG, IMG), IMG,
              lambda io, a, b: _mutation_probe_fn(
                  (np.asarray(io[0]) + np.asarray(io[1])) * 0.5, a, b),
              _mutation_probe_fn.__doc__ or ""))'''
    elif tier == "t3":
        code = f'''from probe_injected import probe as _mutation_probe_fn
_DEFS.append(({name!r}, "probe", IMG, IMG, _mutation_probe_fn))
_mutation_probe_real_ops = _real_ops
def _real_ops():
    return _mutation_probe_real_ops() | {{{name!r}}}'''
    elif tier in ("t4", "t5"):
        out = "image2d" if tier == "t4" else "table"
        code = f'''from probe_injected import probe as _mutation_probe_fn
OPSMATH[{name!r}] = {{"category": "probe", "module": "probe_injected",
    "in": ["image2d"], "out": {out!r}, "func": _mutation_probe_fn,
    "doc": _mutation_probe_fn.__doc__ or ""}}'''
    elif tier == "t5b":
        code = f'''from probe_injected import probe as _mutation_probe_fn
OPS3D[{name!r}] = {{"category": "probe", "module": "probe_injected",
    "in": ["voxel"], "out": "voxel", "gpu": False,
    "func": _mutation_probe_fn, "doc": _mutation_probe_fn.__doc__ or ""}}'''
    elif tier == "t6":
        code = f'''from probe_injected import probe as {name}'''
    else:
        raise ValueError(f"unsupported tier: {tier}")
    return f"\n{BEGIN} {tier} {name}\n{code}\n{END}\n"


def inject(root: Path, tier: str, kind: str, name: str) -> None:
    if tier not in TIERS or not (root / TIERS[tier][0]).is_file():
        raise RuntimeError(f"unsupported tier: {tier}")
    if kind not in KINDS:
        raise ValueError(f"unknown kind: {kind}")
    if not re.fullmatch(r"probe_[A-Za-z0-9_]+", name):
        raise ValueError("name must be a probe_ prefixed Python identifier")
    state_path = root / STATE
    module = root / "probe_injected.py"
    if state_path.exists() or module.exists():
        raise RuntimeError("an injection already exists; run restore first")
    target = root / TIERS[tier][0]
    original = target.read_bytes()
    if BEGIN.encode() in original:
        raise RuntimeError(f"marker already present in {target}")
    block = _block(tier, name).encode("utf-8")
    module.write_text(_module_text(kind, tier), encoding="utf-8", newline="\n")
    target.write_bytes(original + block)
    state = {"tier": tier, "kind": kind, "name": name,
             "target": target.relative_to(root).as_posix(), "original_size": len(original),
             "original_sha256": _sha(original), "block_sha256": _sha(block)}
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def restore(root: Path) -> None:
    state_path = root / STATE
    if not state_path.exists():
        raise RuntimeError("no mutation probe state found")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    target = root / state["target"]
    data = target.read_bytes()
    size = int(state["original_size"])
    original, block = data[:size], data[size:]
    if _sha(original) != state["original_sha256"] or _sha(block) != state["block_sha256"]:
        raise RuntimeError("registration file changed after injection; refusing imprecise restore")
    target.write_bytes(original)
    module = root / "probe_injected.py"
    if not module.exists():
        raise RuntimeError("injected module is missing")
    module.unlink()
    state_path.unlink()
    if BEGIN.encode() in target.read_bytes() or module.exists() or state_path.exists():
        raise RuntimeError("restore verification failed")
    if (root / ".git").exists() or (root / ".git").is_file():
        check = subprocess.run(["git", "status", "--porcelain", "--", state["target"],
                                "probe_injected.py", STATE], cwd=root, text=True,
                               capture_output=True, check=False)
        if check.returncode or check.stdout.strip():
            raise RuntimeError("restore left injected paths dirty: " + check.stdout.strip())


def parse_junit(path: Path) -> dict:
    root = ET.parse(path).getroot()
    failed, errors, durations = [], [], {}
    for case in root.iter("testcase"):
        test_id = "::".join(x for x in (case.get("classname"), case.get("name")) if x)
        durations[test_id] = float(case.get("time", "0") or 0)
        if case.find("failure") is not None:
            failed.append(test_id)
        if case.find("error") is not None:
            errors.append(test_id)
    total = float(root.get("time", "0") or 0)
    if not total:
        total = sum(durations.values())
    return {"failed": sorted(failed), "errors": sorted(errors),
            "durations": durations, "duration": total}


def summarize(results: dict[str, dict], baseline: set[str] | None = None,
              partial: bool = False) -> dict:
    contaminated = set(baseline or ())
    failures = {k: (set(v.get("failed", ())) | set(v.get("errors", ()))) - contaminated
                for k, v in results.items()}
    bookkeeping = failures.get("a", set())
    caught = {}
    behavioural = {}
    for kind, key in zip(("b", "c", "d", "e", "f", "g", "g2", "h"), CAUGHT_KEYS):
        extra = sorted(failures.get(kind, set()) - bookkeeping)
        behavioural[key] = extra
        caught[key] = bool(extra)
    return {"partial": partial, "baseline_failures": sorted(contaminated),
            "bookkeeping": sorted(bookkeeping), "bookkeeping_gates": len(bookkeeping),
            "behavioural": behavioural,
            "behavioural_gates": len(set().union(*(set(v) for v in behavioural.values()))),
            "caught": caught}


def _run_pytest(root: Path, xml: Path, extra: str) -> tuple[int, float]:
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
           "--junitxml", str(xml)] + shlex.split(extra, posix=os.name != "nt") + ["tests"]
    started = time.monotonic()
    proc = subprocess.run(cmd, cwd=root, check=False)
    return proc.returncode, time.monotonic() - started


def run_probe(args: argparse.Namespace) -> None:
    root, out = args.root.resolve(), Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    tier = args.tier
    kinds = [x.strip() for x in args.kinds.split(",") if x.strip()]
    unknown = [k for k in kinds if k not in KINDS]
    if unknown:
        raise ValueError(f"unknown kinds: {', '.join(unknown)}")
    baseline_path = out / f"{tier}_baseline.json"
    if args.baseline and not baseline_path.exists():
        xml = out / f"{tier}_baseline.xml"
        rc, elapsed = _run_pytest(root, xml, args.pytest_args)
        data = parse_junit(xml)
        data.update(returncode=rc, wall_duration=elapsed)
        baseline_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    baseline = json.loads(baseline_path.read_text(encoding="utf-8")) if baseline_path.exists() else {}
    estimate = float(baseline.get("wall_duration") or baseline.get("duration") or 0)
    started = time.monotonic()
    partial = False
    results: dict[str, dict] = {}
    for kind in kinds:
        result_path = out / f"{tier}_{kind}.json"
        if result_path.exists():
            results[kind] = json.loads(result_path.read_text(encoding="utf-8"))
            continue
        if args.max_hours is not None and (time.monotonic() - started + estimate) > args.max_hours * 3600:
            partial = True
            break
        inject(root, tier, kind, f"probe_{tier}_{kind}")
        try:
            xml = out / f"{tier}_{kind}.xml"
            rc, elapsed = _run_pytest(root, xml, args.pytest_args)
            data = parse_junit(xml)
            data.update(returncode=rc, wall_duration=elapsed)
            result_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            results[kind] = data
        finally:
            restore(root)
    summary = summarize(results, set(baseline.get("failed", ())) | set(baseline.get("errors", ())), partial)
    summary.update(tier=tier, completed_kinds=sorted(results), requested_kinds=kinds)
    (out / f"{tier}_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    inj = sub.add_parser("inject")
    inj.add_argument("--tier", required=True)
    inj.add_argument("--kind", required=True)
    inj.add_argument("--name", required=True)
    sub.add_parser("restore")
    run = sub.add_parser("run")
    run.add_argument("--tier", required=True)
    run.add_argument("--kinds", required=True)
    run.add_argument("--out", required=True)
    run.add_argument("--pytest-args", default="-n 3")
    run.add_argument("--baseline", action="store_true")
    run.add_argument("--max-hours", type=float)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "list":
        list_probe(args.root.resolve())
    elif args.command == "inject":
        inject(args.root.resolve(), args.tier, args.kind, args.name)
    elif args.command == "restore":
        restore(args.root.resolve())
    else:
        run_probe(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
