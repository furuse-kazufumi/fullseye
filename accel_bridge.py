"""accel_bridge — 進化 champion の op 列を GPU 常駐パイプラインで実行する橋渡し。

E2E の本丸の仕上げ: evolution が出す champion(genome / pipeline 文字列)を、accel が
GPU 化した op は **常駐パイプライン**(``accel.run_pipeline``、host->device 転送1回)で、
未対応 op は CPU(core ``ops.run_stages`` = ``RT``)で実行する。連続する accel 対応 op を
1区間にまとめ、区間単位で転送を償却する(転送回数 = GPU 区間数)。

このブリッジは同時に **次に GPU 化すべき op を champion 頻度で決めるデータ根拠**を出す:
``report_champions`` が全 champion の accel カバレッジと未対応 op の頻度表を返す。ランダムに
op を足すのでなく、進化が実際に選ぶ op を優先して wave を組むための honest な計画装置。

honest な限界:
- accel op は core と interior<5e-3 の faithful だが、torch の reflect/pool 規約が scipy と
  端で違うため、bridge 出力は core champion と **bit 一致しない(近似)**。妥当性は
  (1) interior 画素差 (2) タスク指標(PSNR/精度)が holdout で保たれるか で検証する
  (``validate_champion``)。
- accel は 2D image op のみ。volume(vol_*)・region モルフォロジ・feature/matching・
  backend 固有 op(sk_tv/cv_sharpen/illuminate 等)は現状すべて CPU 区間になる。
"""
from __future__ import annotations

import json
import pathlib
import re
from collections import Counter

import numpy as np

import accel
import accel_match
import accel_vol
import ops


def core_to_accel() -> dict:
    """core registry の op 名 -> accel op 名。ACCEL の 2 要素目(再現する core 名)から逆引き。

    ``accel.ACCEL`` は ``accel名: (fn, core名, halcon名)``。同じ core 名を二つの accel op が
    主張することは無い(各 accel op は 1 つの core op を faithful に再現)ので単射。
    """
    return {core: name for name, (_fn, core, _hal) in accel.ACCEL.items()}


def core_to_vol_accel() -> dict:
    """core の volume op 名 -> accel_vol op 名(VOL_ACCEL の 2 要素目から逆引き)。"""
    return {core: name for name, (_fn, core) in accel_vol.VOL_ACCEL.items()}


_C2A = core_to_accel()
_C2VA = core_to_vol_accel()
_C2M = dict(accel_match.MATCH_ACCEL)        # core match op 名 -> match accel(現状 ncc_locate のみ)
_TORCH = getattr(accel, "_HAS_TORCH", False)

_STAGE_RE = re.compile(r"([A-Za-z0-9_]+)\(a=([-\d.]+),\s*b=([-\d.]+)\)")


def _seg_kind(stage) -> str:
    """この stage の実行区間種別: 'gpu'(2D image accel)/ 'vol'(3D volume accel)/ 'cpu'。"""
    if _TORCH and stage.sort == ops.IMAGE and stage.op in _C2A:
        return "gpu"
    if _TORCH and stage.sort == ops.VOLUME and stage.op in _C2VA:
        return "vol"
    if _TORCH and stage.op in _C2M:              # NCC マッチング(IMAGE->MATCH の終端)
        return "match"
    return "cpu"


def _gpu_ok(stage) -> bool:
    """この stage を GPU(image / volume / match)で実行できるか。"""
    return _seg_kind(stage) in ("gpu", "vol", "match")


def stages_from_pipeline_str(s: str) -> list:
    """champion の ``pipeline`` 文字列 -> Stage 列(sort は名前から解決)。

    a/b は 2 桁丸めなので **カバレッジ/レポート用**(実行の忠実再現には genome を使う)。
    """
    if not s or s == "identity":
        return []
    specs = [(m.group(1), float(m.group(2)), float(m.group(3)))
             for m in _STAGE_RE.finditer(s)]
    return ops.decode_by_names(specs)


def _as_stages(x, start=ops.IMAGE) -> list:
    """genome(float列)/ Stage 列 / (name,a,b)・dict 列 / pipeline 文字列 を Stage 列へ。"""
    if isinstance(x, str):
        return stages_from_pipeline_str(x)
    if isinstance(x, (list, tuple)) and x and isinstance(x[0], ops.Stage):
        return [s for s in x if s.op != "identity"]
    arr = np.asarray(x, dtype=object)
    # 全要素が数値なら genome とみなす
    if arr.ndim == 1 and all(isinstance(v, (int, float, np.floating)) for v in x):
        return [s for s in ops.decode(np.asarray(x, np.float64), start)
                if s.op != "identity"]
    return ops.decode_by_names(x)


def plan(stages) -> list:
    """Stage 列を GPU(image)/ VOL(volume)/ CPU 区間の連なりに分割。

    返り値 = ``[("gpu", [(accel名,a,b),...]) | ("vol", [(vol_accel名,a,b),...]) |
    ("cpu", [Stage,...]), ...]``。連続する同種 GPU op は 1 区間にまとまり、
    ``accel.run_pipeline`` / ``accel_vol.run_pipeline_vol`` で転送 1 回に償却される。
    sort が image/volume を外れた op は自然に CPU 区間へ落ちる。
    """
    segs: list = []
    for st in stages:
        kind = _seg_kind(st)
        if kind == "gpu":
            item = (_C2A[st.op], st.a, st.b)
        elif kind == "vol":
            item = (_C2VA[st.op], st.a, st.b)
        elif kind == "match":
            item = (_C2M[st.op], st.a, st.b)
        else:
            item = st
        if segs and segs[-1][0] == kind:
            segs[-1][1].append(item)
        else:
            segs.append((kind, [item]))
    return segs


def run(stages_or_genome, imgs, device="cpu", start=ops.IMAGE):
    """champion を GPU(image/volume)/CPU 混在で実行。

    image accel 区間は ``accel.run_pipeline``、volume accel 区間は
    ``accel_vol.run_pipeline_vol``(いずれも常駐=転送 1 回)、未対応区間は core ``RT``(CPU)。
    ``imgs`` = list[2D or 3D ndarray](0..1)。返り値は最終区間の出力。
    """
    stages = _as_stages(stages_or_genome, start)
    cur = [np.asarray(im, np.float64) for im in imgs]
    for kind, items in plan(stages):
        if kind == "gpu":
            cur = [np.asarray(im, np.float64)
                   for im in accel.run_pipeline(items, cur, device=device)]
        elif kind == "vol":
            cur = [np.asarray(v, np.float64)
                   for v in accel_vol.run_pipeline_vol(items, cur, device=device)]
        elif kind == "match":
            # NCC は終端(MATCH)。テンプレートは ops._MATCH_CTX(呼び出し側が set 済み)。
            T = ops._MATCH_CTX.get("template")
            for _name, _a, _b in items:                 # 実際は ncc_locate 1 個
                cur = accel_match.ncc_locate_batch(cur, T, device=device)
        else:
            cur = [ops.run_stages(items, im) for im in cur]
    return cur


def coverage(stages_or_genome, start=ops.IMAGE) -> dict:
    """accel カバレッジ + 区間構造(転送回数 = GPU 区間数)。"""
    stages = _as_stages(stages_or_genome, start)
    segs = plan(stages)
    summary = [(k, [it[0] for it in items]) if k in ("gpu", "vol", "match")
               else ("cpu", [s.op for s in items]) for k, items in segs]
    n_gpu = sum(len(v) for k, v in summary if k in ("gpu", "vol", "match"))
    uncovered = [s.op for s in stages if not _gpu_ok(s)]
    return {
        "n_total": len(stages),
        "n_gpu": n_gpu,
        "n_cpu": len(stages) - n_gpu,
        "gpu_frac": (n_gpu / len(stages)) if stages else 0.0,
        "n_gpu_segments": sum(1 for k, _ in summary if k in ("gpu", "vol", "match")),
        "uncovered_ops": uncovered,
        "segments": summary,
    }


def validate_champion(stages_or_genome, imgs, device="cpu", start=ops.IMAGE, m=3) -> dict:
    """bridge 出力 vs 純 core 出力の interior 画素差(端 m px 除外)。

    accel の reflect/pool 規約が scipy と端で違うので bit 一致はしない。faithful op だけを
    GPU に載せているので **interior は小さい**はず。これが「GPU 化が champion を壊していない」
    ことの実データ根拠(honest 検証)。画像出力の champion 用(feature 出力段は無視)。
    """
    stages = _as_stages(stages_or_genome, start)
    bridge_out = run(stages, imgs, device=device, start=start)
    core_out = [ops.run_stages(stages, np.asarray(im, np.float64)) for im in imgs]
    diffs = []
    for b, c in zip(bridge_out, core_out):
        b = np.asarray(b, np.float64)
        c = np.asarray(c, np.float64)
        if b.ndim != 2 or b.shape != c.shape:
            continue
        if b.shape[0] > 2 * m and b.shape[1] > 2 * m:
            diffs.append(float(np.max(np.abs(b[m:-m, m:-m] - c[m:-m, m:-m]))))
        else:
            diffs.append(float(np.max(np.abs(b - c))))
    return {"n": len(diffs),
            "max_interior_diff": max(diffs) if diffs else 0.0,
            "mean_interior_diff": float(np.mean(diffs)) if diffs else 0.0}


def load_champion(path) -> dict:
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def report_champions(champ_dir="out/accuracy_bench") -> dict:
    """全 champion_*.json の accel カバレッジと、未対応 op の頻度表(= wave 優先度)。

    未対応 op を「何 champion に登場するか」でランク付けする(延べ回数でなく登場 champion 数
    を主指標にすると、多段で同じ op を繰り返す champion に引きずられない)。
    """
    d = pathlib.Path(champ_dir)
    per_problem = {}
    op_in_champs = Counter()   # 未対応 op -> 登場した champion 数
    op_total = Counter()       # 未対応 op -> 延べ登場回数
    for f in sorted(d.glob("champion_*.json")):
        champ = load_champion(f)
        cov = coverage(champ.get("pipeline", ""))
        per_problem[champ["problem"]] = cov
        for op in set(cov["uncovered_ops"]):
            op_in_champs[op] += 1
        for op in cov["uncovered_ops"]:
            op_total[op] += 1
    priority = [{"op": op, "in_champions": op_in_champs[op], "total": op_total[op]}
                for op, _ in sorted(op_in_champs.items(),
                                    key=lambda kv: (-kv[1], -op_total[kv[0]], kv[0]))]
    return {"per_problem": per_problem, "priority": priority}


def _print_report(champ_dir="out/accuracy_bench") -> None:
    rep = report_champions(champ_dir)
    print("=== champion ごとの accel カバレッジ ===")
    for prob, cov in rep["per_problem"].items():
        segs = " | ".join(f"{k}:{'>'.join(v)}" for k, v in cov["segments"])
        print(f"{prob:14s} gpu {cov['n_gpu']}/{cov['n_total']} "
              f"(seg={cov['n_gpu_segments']})  {segs}")
    print("\n=== 未対応 op の優先度(登場 champion 数, 延べ) ===")
    for row in rep["priority"]:
        print(f"  {row['op']:26s} champions={row['in_champions']}  total={row['total']}")


if __name__ == "__main__":
    import sys
    _print_report(sys.argv[1] if len(sys.argv) > 1 else "out/accuracy_bench")
