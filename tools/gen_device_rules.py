"""実測ログから ``device="auto"`` の規則表を作る / Derive DEVICE_RULES.json from the crossover logs.

入力は ``docs/perf/logs/crossover/*.jsonl``(``tools/bench_gpu_crossover.py`` の生ログ)。表は決定的に作るので、
``tests/test_device_rules.py`` は GPU の無い CI でも「ログと表の一致」と「遅くなる点が無いこと」を検査できる。

閾値の向き: 規則が既定の挙動(常に GPU)を変えるのは「閾値未満を CPU に残す」ところだけ。だから遅くならない
条件は「閾値未満の全寸法・全つまみで CPU が GPU に負けない」こと。閾値は op ごとに「CPU が負けなかった最後の
寸法の直後」に置く。寸法の隙間は GPU のまま(= 既定の挙動)に残るので、隙間で遅くなることもない。

    py -3.11 tools/gen_device_rules.py          # 書く
    py -3.11 tools/gen_device_rules.py --check  # 差があれば exit 1
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "docs" / "perf" / "logs" / "crossover"
OUT = ROOT / "fullseye" / "data" / "DEVICE_RULES.json"

# 測定の揺れ(同じ点を測り直した差)より小さい負けは負けと数えない。CPU が GPU の 1+TOLERANCE 倍以内なら CPU 可。
TOLERANCE = 0.10
# これ未満の差は判断に使わない(タイマーと OS の揺れの大きさ)。
FLOOR_S = 50e-6

# accel の kernel 関数 -> 族。単 op の閾値には使わず(op ごとに測ってある)、枚数方向の閾値の束ね方にだけ使う。
FAMILY_OF_KERNEL = {
    "_gamma": "point", "_invert": "point", "_scale": "point", "_threshold": "point", "_sigmoid": "point",
    "_reg_copy": "point", "_reg_invert": "point", "_gaussian": "separable", "_mean": "separable",
    "_sobel": "separable", "_prewitt": "separable", "_roberts": "separable", "_dog": "separable",
    "_unsharp": "separable", "_grad_dir": "separable", "_adaptive_gauss": "separable", "_cv_sharpen": "separable",
    "_dyn_threshold": "separable", "_illuminate": "separable", "_median": "nonseparable",
    "_percentile": "nonseparable", "_bilateral": "nonseparable", "_std_filter": "nonseparable",
    "_laplace": "nonseparable", "_local_max": "nonseparable", "_erode_rect": "morphology",
    "_dilate_rect": "morphology", "_range_rect": "morphology", "_open_rect": "morphology",
    "_close_rect": "morphology", "_tophat": "morphology", "_bothat": "morphology", "_reg_dilate": "morphology",
    "_reg_erode": "morphology", "_erosion_golay": "morphology", "_erosion_circle": "morphology",
    "_dilation_circle": "morphology", "_opening_circle": "morphology", "g": "morphology",
    "_lowpass": "frequency", "_highpass": "frequency", "_sk_tv": "iterative", "_fill_holes_bin": "iterative",
    "_canny": "iterative", "_equalize": "iterative", "_otsu": "iterative", "_projective_warp": "geometry",
    "_projective_region": "geometry",
}


def read_logs(pattern: str, logs: Path = LOGS) -> list:
    rows = []
    for path in sorted(logs.glob(pattern)):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def cpu_not_worse(cpu_s: float, gpu_s: float) -> bool:
    """CPU に残しても GPU より遅くならない(揺れの範囲内を含む)。**検査**(遅くなった点を数える)に使う。"""
    return cpu_s <= gpu_s * (1 + TOLERANCE) or cpu_s - gpu_s <= FLOOR_S


def cpu_better(cpu_s: float, gpu_s: float) -> bool:
    """CPU が揺れの幅を超えて速い(``cpu * (1 + TOLERANCE) <= gpu``)。**閾値を決める**のはこちら。

    2026-11-03: 当初は閾値も :func:`cpu_not_worse`(揺れの範囲の引き分けも CPU)で決めていた。
    before/after の実測 1 回目(``before_after.jsonl``、568 点)で、引き分けで CPU に寄せた境目の寸法
    (掃引の間の 362 や、掃引で 10 % 以内だった 512)の 14 点が 10〜47 % 遅くなった。引き分けは GPU
    (= 規則の前の挙動)に残す。
    """
    return cpu_s * (1 + TOLERANCE) <= gpu_s


def last_cpu_side(points: list) -> int:
    """[(side, cpu_s, gpu_s), ...] から、そこまでの全寸法で CPU が負けなかった最後の side(無ければ 0)。"""
    last = 0
    for side, cpu_s, gpu_s in sorted(points):
        if cpu_s is None or gpu_s is None or not cpu_better(cpu_s, gpu_s):
            break
        last = side
    return last


def op_thresholds(sweep_cpu: list, sweep_gpu: list, grid_cpu: list = (), grid_gpu: list = ()) -> dict:
    """全 accel op の閾値(画素数)。全つまみで CPU が負けなかった最後の寸法の直後。

    掃引は一辺 2048 まで。そこまで CPU が負けなかった op は、格子の一辺 4096(既定つまみ、1 枚)でも
    CPU が負けなければ閾値を 4096 の直後へ動かす。
    """
    cpu = {(r["op"], r["side"], r["a"]): r for r in sweep_cpu if r.get("status") == "ok"}
    gpu = {(r["op"], r["side"], r["a"]): r for r in sweep_gpu if r.get("status") == "ok"}
    out = {}
    for op in sorted({k[0] for k in gpu} | {k[0] for k in cpu}):
        sides = sorted({k[1] for k in gpu if k[0] == op} | {k[1] for k in cpu if k[0] == op})
        knobs = sorted({k[2] for k in gpu if k[0] == op} | {k[2] for k in cpu if k[0] == op})
        last = 0
        for side in sides:
            pairs = [(cpu.get((op, side, a)), gpu.get((op, side, a))) for a in knobs]
            if all(c and g and cpu_better(c["wall_s"], g["wall_s"]) for c, g in pairs):
                last = side
            else:
                break
        if last == max(sides, default=0):
            c = next((r for r in grid_cpu if (r.get("op"), r.get("side"), r.get("n")) == (op, 4096, 1)), None)
            g = next((r for r in grid_gpu if (r.get("op"), r.get("side"), r.get("n")) == (op, 4096, 1)), None)
            if c and g and c["status"] == g["status"] == "ok" and cpu_better(c["wall_s"], g["wall_s"]):
                last = 4096
        out[op] = (last + 1) ** 2 if last else 0        # 0 = 測った最小の寸法から GPU が勝つ
    return out


#: 閾値の材料に使う before/after(1 回目)。2 回目以降(``before_after_2.jsonl``)は材料に入れず、
#: 新しい表の検証にだけ使う(材料と検証を同じ測定にしない)。
BA_TRAIN = "before_after.jsonl"


def cap_by_before_after(thresholds: dict, ba_rows: list) -> dict:
    """before/after で CPU(after)が GPU(before)より遅かった寸法は、閾値をその寸法以下へ下げる(GPU に戻す)。"""
    out = dict(thresholds)
    for r in ba_rows:
        if r.get("kind") != "op" or r["name"] not in out:
            continue
        if not cpu_not_worse(r["after_s"], r["before_s"]):
            out[r["name"]] = min(out[r["name"]], r["side"] * r["side"])
    return out


def batch_thresholds(cpu_rows: list, gpu_rows: list, family_of: dict) -> dict:
    """枚数ごとの閾値を族で束ねる。族の中で一番小さい値(= どの op でも CPU に残して遅くならない側)。"""
    cpu = {(r["op"], r["side"], r["n"]): r for r in cpu_rows if "side" in r and r.get("status") == "ok"}
    gpu = {(r["op"], r["side"], r["n"]): r for r in gpu_rows if "side" in r and r.get("status") == "ok"}
    grouped: dict = {}
    for op, n in sorted({(k[0], k[2]) for k in gpu}):
        family = family_of.get(op)
        if family is None:
            continue
        points = [(side, cpu[(op, side, n)]["wall_s"] if (op, side, n) in cpu else None, g["wall_s"])
                  for (o, side, m), g in gpu.items() if o == op and m == n]
        last = last_cpu_side(points)
        grouped.setdefault(family, {}).setdefault(str(n), []).append((last + 1) ** 2 if last else 0)
    return {family: {n: min(v) for n, v in sorted(by_n.items(), key=lambda kv: int(kv[0]))}
            for family, by_n in sorted(grouped.items())}


def pipeline_points(logs: Path = LOGS) -> dict:
    """``{(pipeline, variant, side, n): (cpu_s, gpu_s)}`` of every measured chain point.

    ``pipe_recheck.jsonl``(同じプロセスで CPU と GPU を交互に、回数を増やして測り直した点)が在る点は、
    その値で ``pipe_cpu`` / ``gpipe`` の値を置き換える。測り直しは一部の点だけを選ばず、全パイプラインの
    同じ寸法を測る(``tools/bench_gpu_crossover.py pipe-recheck``)。元の値はログに残る。
    """
    cpu = {(r["pipeline"], r["variant"], r["side"], r["n"]): r["wall_s"]
           for r in read_logs("pipe_cpu.jsonl", logs) if r.get("status") == "ok"}
    gpu = {(r["pipeline"], r["variant"], r["side"], r["n"]): r["wall_s"]
           for r in read_logs("gpipe.jsonl", logs) if r.get("status") == "ok"}
    out = {k: (cpu[k], gpu[k]) for k in sorted(set(cpu) & set(gpu))}
    for r in read_logs("pipe_recheck.jsonl", logs):
        if r.get("status") == "ok":
            out[(r["pipeline"], r["variant"], r["side"], r["n"])] = (r["cpu_s"], r["gpu_s"])
    return out


def pipeline_rule(table: dict, points: dict, chains: dict, accelerated) -> dict:
    """段ごとの規則(「全 GPU 段が単独で CPU に残る大きさなら鎖も CPU」)を、測った鎖の全点で試す。

    採用の条件(★after < before): 規則が CPU に回す測定点で CPU が GPU に負けた点が 1 つも無く、
    かつ CPU に回す点が 1 つ以上ある(空の規則は採用と呼ばない)。負けた点があれば採用せず、その点を
    ``violations`` に残す(規則が無いときの挙動 = 鎖は GPU のまま)。
    """
    import device_policy
    trial = dict(table, pipeline={"rule": "min_stage", "adopted": True})
    violations, on_cpu = [], 0
    for (name, variant, side, n), (cpu_s, gpu_s) in sorted(points.items()):
        stages = chains.get(name, {}).get(variant)
        if stages is None:
            continue
        if device_policy.route(stages, (side, side), n, rules=trial, accelerated=accelerated) != "cpu":
            continue
        on_cpu += 1
        if not cpu_not_worse(cpu_s, gpu_s):
            violations.append([name, variant, side, n, round(cpu_s, 6), round(gpu_s, 6)])
    return {"rule": "min_stage", "adopted": not violations and on_cpu > 0, "measured_points": len(points),
            "points_on_cpu": on_cpu, "violations": violations}


ALLOW = ROOT / "fullseye" / "data" / "gpu_auto_allow.json"
SWEEP_MD = ROOT / "docs" / "perf" / "gpu_auto_sweep_2026-11-02.md"
# 許可リストの倍率を測った大きさ(tools/gpu_auto_sweep.py の REAL と同じ規則)。表に入力の形が書かれて
# いない op は、入口の型からこの大きさを引く。型が判らない op は ``None`` = auto では選ばない。
_SORT_MEASURED = {
    "image": "2048×2048", "region": "2048×2048", "mask": "2048×2048", "depth": "2048×2048",
    "image2d": "2048×2048", "cimage": "2048×2048", "qimage": "2048×2048", "gradient": "2048×2048",
    "color": "2048×2048×3", "rgbimage": "2048×2048×3", "rgb": "2048×2048×3", "lab": "2048×2048×3",
    "rgba": "2048×2048×4", "volume": "256×256×256", "voxel": "256×256×256", "sdf": "256×256×256",
    "signal": "1048576", "video": "8×512×512", "matrix": "1024×1024",
}


def _measured_shapes(md: Path = SWEEP_MD) -> dict:
    """掃引の報告(表の 3 列目が入力の形)から ``{op: "2048×2048"}``。最初に出た行を使う。"""
    import re
    out: dict = {}
    if not md.exists():
        return out
    for line in md.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| `"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        m = re.match(r"`([^`]+)`", cells[0])
        if m and len(cells) > 2 and re.fullmatch(r"\d+(×\d+)*", cells[2]):
            out.setdefault(m.group(1), cells[2])
    return out


def _elements(shape_text):
    if not shape_text:
        return None
    n = 1
    for part in shape_text.split("×"):
        n *= int(part)
    return n


def shadow_section(allow_path: Path = ALLOW, md: Path = SWEEP_MD, in_sort: dict | None = None) -> dict:
    """許可リスト(``gpu_auto_allow.json``)を ``device="auto"`` が引く形にする。

    ``min_elements`` = 倍率を測った入力の要素数。auto はこれ以上の入力でだけ許可リストの道を選ぶ
    (それ未満は測っていない。小さいほど転送と起動の固定費が効き、倍率は下がる向き)。
    """
    if not allow_path.exists():
        return {"source": None, "ops": {}}
    allow = json.loads(allow_path.read_text(encoding="utf-8"))
    if in_sort is None:
        import api
        in_sort = {r["name"]: r["in_sort"] for r in api._rows()}
    shapes = _measured_shapes(md)
    rows: dict = {}
    for list_name in ("ops", "resident_ops", "pipeline_ops"):
        for op, row in sorted(allow.get(list_name, {}).items()):
            if op in rows:
                continue                      # 単独の採用を優先(枠は重ならないはずだが、重なれば強い方)
            shape = shapes.get(op) or _SORT_MEASURED.get(in_sort.get(op))
            ratio = row.get("ratio") if list_name == "ops" else row.get("ratio_resident")
            entry = {"list": list_name, "ratio": round(float(ratio), 3) if ratio is not None else None,
                     "measured_shape": shape, "min_elements": _elements(shape)}
            if list_name != "ops" and row.get("ratio_single") is not None:
                entry["ratio_single"] = round(float(row["ratio_single"]), 3)
            rows[op] = entry
    return {"source": "fullseye/data/gpu_auto_allow.json", "min_ratio": allow.get("min_ratio"), "ops": rows}


def _chains() -> dict:
    """bench の検査パイプライン(段名の列)。"""
    sys.path.insert(0, str(ROOT))
    from tools.bench_gpu_crossover import PIPELINES
    return {name: {v: [s[0] for s in chain] for v, chain in vs.items()} for name, vs in PIPELINES.items()}


def families(accel_keys: dict) -> dict:
    """core op -> 族(``accel.ACCEL`` の kernel 名から)。"""
    return {core: FAMILY_OF_KERNEL.get(kernel, "other") for core, kernel in sorted(accel_keys.items())}


def build(logs: Path = LOGS, accel_kernels: dict | None = None, accelerated=None) -> dict:
    sys.path.insert(0, str(ROOT))
    if accel_kernels is None:
        import accel
        accel_kernels = {core: fn.__name__ for _k, (fn, core, _h) in accel.ACCEL.items()}
    if accelerated is None:
        import api
        accelerated = api._gpu_op_names()
    family_of = families(accel_kernels)
    bench_family = {r["op"]: r["family"] for r in read_logs("cpu_*.jsonl", logs) if "family" in r}
    grid_family = {op: bench_family[op] for op in bench_family}
    thresholds = op_thresholds(read_logs("sweep_cpu.jsonl", logs), read_logs("sweep_gpu.jsonl", logs),
                               read_logs("cpu_*.jsonl", logs), read_logs("gpu.jsonl", logs))
    thresholds = cap_by_before_after(thresholds, read_logs(BA_TRAIN, logs))
    table = {
        "schema": 1,
        "basis": "docs/perf/gpu_crossover_2026-11-02.md",
        "tolerance": TOLERANCE,
        "floor_s": FLOOR_S,
        "ops": {op: {"family": family_of.get(op, "other"), "min_pixels": thresholds[op]} for op in sorted(thresholds)},
        "batch": batch_thresholds(read_logs("cpu_*.jsonl", logs), read_logs("gpu.jsonl", logs), grid_family),
    }
    table["pipeline"] = pipeline_rule(table, pipeline_points(logs), _chains(), accelerated)
    table["shadow"] = shadow_section()
    return table


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    ns = ap.parse_args(argv)
    text = json.dumps(build(), indent=1, ensure_ascii=False, sort_keys=True) + chr(10)
    if ns.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print("DEVICE_RULES.json is out of date: run tools/gen_device_rules.py")
            return 1
        return 0
    OUT.write_text(text, encoding="utf-8", newline=chr(10))
    print("wrote %s" % OUT.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
