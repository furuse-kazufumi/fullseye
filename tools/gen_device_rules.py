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
    """CPU に残しても GPU より遅くならない(揺れの範囲内を含む)。"""
    return cpu_s <= gpu_s * (1 + TOLERANCE) or cpu_s - gpu_s <= FLOOR_S


def last_cpu_side(points: list) -> int:
    """[(side, cpu_s, gpu_s), ...] から、そこまでの全寸法で CPU が負けなかった最後の side(無ければ 0)。"""
    last = 0
    for side, cpu_s, gpu_s in sorted(points):
        if cpu_s is None or gpu_s is None or not cpu_not_worse(cpu_s, gpu_s):
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
            if all(c and g and cpu_not_worse(c["wall_s"], g["wall_s"]) for c, g in pairs):
                last = side
            else:
                break
        if last == max(sides, default=0):
            c = next((r for r in grid_cpu if (r.get("op"), r.get("side"), r.get("n")) == (op, 4096, 1)), None)
            g = next((r for r in grid_gpu if (r.get("op"), r.get("side"), r.get("n")) == (op, 4096, 1)), None)
            if c and g and c["status"] == g["status"] == "ok" and cpu_not_worse(c["wall_s"], g["wall_s"]):
                last = 4096
        out[op] = (last + 1) ** 2 if last else 0        # 0 = 測った最小の寸法から GPU が勝つ
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


def pipeline_threshold(cpu_rows: list, gpu_rows: list) -> int:
    """パイプライン(2 段以上)の閾値: 測った全パイプライン・全変種で CPU が負けなかった最後の寸法の直後。"""
    cpu = {(r["pipeline"], r["variant"], r["side"]): r for r in cpu_rows if r.get("status") == "ok" and r["n"] == 1}
    gpu = {(r["pipeline"], r["variant"], r["side"]): r for r in gpu_rows if r.get("status") == "ok" and r["n"] == 1}
    lasts = []
    for name, variant in sorted({k[:2] for k in gpu}):
        points = [(k[2], cpu[k]["wall_s"] if k in cpu else None, g["wall_s"]) for k, g in gpu.items()
                  if k[:2] == (name, variant)]
        lasts.append(last_cpu_side(points))
    return (min(lasts) + 1) ** 2 if lasts and min(lasts) else 0


def families(accel_keys: dict) -> dict:
    """core op -> 族(``accel.ACCEL`` の kernel 名から)。"""
    return {core: FAMILY_OF_KERNEL.get(kernel, "other") for core, kernel in sorted(accel_keys.items())}


def build(logs: Path = LOGS, accel_kernels: dict | None = None) -> dict:
    if accel_kernels is None:
        sys.path.insert(0, str(ROOT))
        import accel
        accel_kernels = {core: fn.__name__ for _k, (fn, core, _h) in accel.ACCEL.items()}
    family_of = families(accel_kernels)
    bench_family = {r["op"]: r["family"] for r in read_logs("cpu_*.jsonl", logs) if "family" in r}
    grid_family = {op: bench_family[op] for op in bench_family}
    thresholds = op_thresholds(read_logs("sweep_cpu.jsonl", logs), read_logs("sweep_gpu.jsonl", logs),
                               read_logs("cpu_*.jsonl", logs), read_logs("gpu.jsonl", logs))
    return {
        "schema": 1,
        "basis": "docs/perf/gpu_crossover_2026-11-02.md",
        "tolerance": TOLERANCE,
        "floor_s": FLOOR_S,
        "ops": {op: {"family": family_of.get(op, "other"), "min_pixels": thresholds[op]} for op in sorted(thresholds)},
        "batch": batch_thresholds(read_logs("cpu_*.jsonl", logs), read_logs("gpu.jsonl", logs), grid_family),
        "pipeline": {"min_pixels": pipeline_threshold(read_logs("pipe_cpu.jsonl", logs), read_logs("gpipe.jsonl", logs))},
    }


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
