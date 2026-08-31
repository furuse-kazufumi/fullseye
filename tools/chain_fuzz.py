# -*- coding: utf-8 -*-
"""chain_fuzz — 型で op を繋ぐ拡散・収束ファザー(ops3d + ops1d)。

進化レジストリの流儀を目録全体へ: 型互換な op をランダムに連鎖(拡散)し、
失敗を署名でまとめて最小再現に絞る(収束)。狙いは「単体テストは通るが
**op の出力を次の op が食うと壊れる**」клас の不具合 — 型契約の嘘、
タプル/リスト梱包の不一致、NaN の漏出、想定外の例外種。

判定の分類:
  CONTRACT  ValueError で明確な文言 = fail-closed が仕事をした(白)
  SUSPECT   それ以外の例外(TypeError/IndexError/KeyError/…)= 契約の穴
  NONFINITE 有限入力から NaN/Inf が無言で出た = 毒の漏出
  SLOW      1 op が閾値超(既定 10s)= 性能スメル

使い方:
    py -3.11 tools/chain_fuzz.py --chains 400 --length 6 --seed 0
    py -3.11 tools/chain_fuzz.py --minimize <chain.json>   # 収束(最小再現)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

SLOW_S = 10.0


# --------------------------------------------------------------------------- #
# 型 → 生成器(小さく・決定的に。voxel は 16^3 で全 op が秒未満)               #
# --------------------------------------------------------------------------- #
def _ball_vol(rng, n=16):
    z, y, x = np.mgrid[0:n, 0:n, 0:n].astype(np.float64)
    c = n / 2.0
    v = ((z - c) ** 2 + (y - c) ** 2 + (x - c) ** 2 <= (n * 0.3) ** 2).astype(np.float64)
    return np.clip(v + 0.05 * rng.standard_normal(v.shape), 0.0, 1.0)


def _points(rng, n=160):
    return rng.random((n, 3)) * 10.0


def _mesh(rng):
    import meshrepair
    return meshrepair.convex_hull(_points(rng, 60))


def make_generators():
    return {
        "voxel": _ball_vol,
        "points": _points,
        "image2d": lambda rng: rng.random((32, 32)),
        "depth": lambda rng: 1.0 + rng.random((32, 32)),
        "images": lambda rng: [rng.random((32, 32)) for _ in range(4)],
        "normals": lambda rng: (lambda v: v / np.linalg.norm(v, axis=1, keepdims=True))(
            rng.standard_normal((160, 3))),
        "signal": lambda rng: np.sin(np.linspace(0, 8 * np.pi, 256)) + 0.1 * rng.standard_normal(256),
        "vector": lambda rng: (lambda v: v / np.linalg.norm(v))(rng.standard_normal(3)),
        "pose": lambda rng: (np.eye(3), np.zeros(3)),
        "measurement": lambda rng: float(rng.random()),
        "angle": lambda rng: float(rng.uniform(0, 90)),
        "position": lambda rng: (8.0, 8.0, 8.0),
        "sdf": lambda rng: _ball_vol(rng) - 0.5,
        "gaussians": lambda rng: {"mu": _points(rng, 40), "sigma": np.full(40, 0.3),
                                  "w": np.full(40, 1.0 / 40)},
        # HALCON の complex 画像形式に対応(cx_fft の出力レイアウト = 中心 DC)
        "cimage": lambda rng: np.fft.fftshift(np.fft.fft2(rng.random((32, 32)))),
    }


#: 必須スカラ引数の名前 → 値サンプラ(署名 introspection で束縛)
PARAM_HINTS = {
    "center": lambda rng: 0.5, "width": lambda rng: 0.5,
    "gamma": lambda rng: float(rng.uniform(0.5, 2.0)),
    "cutoff": lambda rng: 0.1, "low": lambda rng: 0.05, "high": lambda rng: 0.2,
    "sigma": lambda rng: 1.0, "scale": lambda rng: 2.0,
    "angle_deg": lambda rng: float(rng.uniform(-90, 90)),
    "factor": lambda rng: 2, "matrix": lambda rng: np.eye(3),
    "p0": lambda rng: (2.0, 2.0, 2.0), "p1": lambda rng: (13.0, 13.0, 13.0),
    "iterations": lambda rng: 3, "psf": lambda rng: None,   # None -> skip op
    "markers": lambda rng: None,
    "rate": lambda rng: 100.0, "new_rate": lambda rng: 50.0,
    "x": lambda rng: 1.0, "step": lambda rng: 2,
}

#: 出力を pool 型へ合わせる梱包アダプタ(catalog の out 型と実際の返りの橋)
ADAPTERS = {
    "vol_label": lambda r: r[0],
    "vol_crop_domain": lambda r: r[0],
    "vol_rle_components": lambda r: r[0] if r else None,
    "label_components": lambda r: r[0] if isinstance(r, tuple) else r,
}


def catalog():
    """(name, module, in_types, out_type, fn) を ops3d + ops1d から集める。"""
    import ops1d
    import ops3d
    ops = []
    for n, m in ops3d.OPS3D.items():
        if m["func"] is not None:
            ops.append((n, "3d", list(m["in"]), m["out"], m["func"]))
    for n, m in ops1d.OPS1D.items():
        if m["func"] is not None and m["category"] != "io":   # ファイル I/O は除外
            ops.append((n, "1d", list(m["in"]), m["out"], m["func"]))
    return ops


def _bind_args(fn, data_args, rng):
    """先頭の必須位置引数へ data_args を割り当て、残る必須引数を名前ヒントで束縛。
    束縛できない必須引数が残れば None(この op はこの回スキップ)。"""
    import inspect
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return list(data_args), {}
    args = list(data_args)
    kwargs = {}
    params = [p for p in sig.parameters.values()
              if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
    for p in params[len(args):]:
        if p.default is not inspect.Parameter.empty:
            continue
        hint = PARAM_HINTS.get(p.name)
        if hint is None:
            return None
        val = hint(rng)
        if val is None:
            return None
        kwargs[p.name] = val
    return args, kwargs


def _classify(exc):
    if isinstance(exc, ValueError):
        return "CONTRACT"
    if isinstance(exc, (ImportError, ModuleNotFoundError, NotImplementedError)):
        return "OPTIONAL"      # optional 依存の明示エラーは白
    return "SUSPECT"


def _finite_ok(val):
    """ndarray(を含む入れ物)に NaN/Inf が無いか。数値以外は不問。"""
    if isinstance(val, np.ndarray):
        return val.dtype.kind not in "fc" or bool(np.isfinite(val).all())
    if isinstance(val, (list, tuple)):
        return all(_finite_ok(v) for v in val)
    if isinstance(val, dict):
        return all(_finite_ok(v) for v in val.values())
    if isinstance(val, float):
        return np.isfinite(val)
    return True


def run_chain(ops, gens, rng, length, log):
    """1 連鎖 = 型付き pool を育てながら length op を実行。発見は log に積む。"""
    pool = {}
    for t, g in gens.items():
        pool[t] = [g(rng)]
    trace = []
    for _ in range(length):
        # pool にある型を食える op を候補化
        cands = [o for o in ops
                 if all((t in pool and pool[t]) or t == "any" for t in o[2])]
        if not cands:
            break
        name, dim, ins, out, fn = cands[rng.integers(len(cands))]
        data_args = []
        for t in ins:
            src = pool[t] if t != "any" else pool[rng.choice(list(pool.keys()))]
            data_args.append(src[rng.integers(len(src))])
        bound = _bind_args(fn, data_args, rng)
        if bound is None:
            continue
        args, kwargs = bound
        t0 = time.perf_counter()
        try:
            result = fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 — ファザーの本懐
            kind = _classify(exc)
            if kind != "OPTIONAL":
                log.append({"kind": kind, "op": name, "dim": dim,
                            "exc": type(exc).__name__, "msg": str(exc)[:200],
                            "trace": trace + [name],
                            "tb": traceback.format_exc(limit=3)})
            continue
        dt = time.perf_counter() - t0
        if dt > SLOW_S:
            log.append({"kind": "SLOW", "op": name, "dim": dim, "sec": round(dt, 1),
                        "trace": trace + [name]})
        if name in ADAPTERS:
            result = ADAPTERS[name](result)
        if result is None:
            continue
        if not _finite_ok(result):
            log.append({"kind": "NONFINITE", "op": name, "dim": dim,
                        "trace": trace + [name]})
            continue                      # 毒は pool に入れない
        trace.append(name)
        pool.setdefault(out, []).append(result)
    return trace


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chains", type=int, default=200)
    ap.add_argument("--length", type=int, default=6)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "chain_fuzz.jsonl"))
    args = ap.parse_args()
    ops = catalog()
    gens = make_generators()
    rng = np.random.default_rng(args.seed)
    log = []
    used = set()
    t0 = time.perf_counter()
    for i in range(args.chains):
        trace = run_chain(ops, gens, rng, args.length, log)
        used.update(trace)
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{args.chains} chains, findings {len(log)}, "
                  f"ops covered {len(used)}", flush=True)
    wall = time.perf_counter() - t0

    # 収束: 署名(kind, op, exc)でまとめる
    sig = {}
    for f in log:
        key = (f["kind"], f["op"], f.get("exc", ""), f.get("msg", "")[:80])
        sig.setdefault(key, {"n": 0, "sample": f})
        sig[key]["n"] += 1
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        for key, v in sorted(sig.items()):
            rec = dict(v["sample"])
            rec["count"] = v["n"]
            rec.pop("tb", None)
            fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")

    kinds = {}
    for f in log:
        kinds[f["kind"]] = kinds.get(f["kind"], 0) + 1
    print(f"\n== 拡散 {args.chains} 連鎖 x len {args.length}(seed {args.seed}, "
          f"{wall:.0f}s)")
    print(f"== op カバレッジ: {len(used)}/{len(ops)}")
    print(f"== 発見(生): {kinds} / 署名数 {len(sig)}")
    print(f"== 署名一覧 -> {args.out}")
    order = {"SUSPECT": 0, "NONFINITE": 1, "SLOW": 2, "CONTRACT": 3}
    for key, v in sorted(sig.items(), key=lambda kv: (order.get(kv[0][0], 9), -kv[1]["n"])):
        kind, op, exc, msg = key
        if kind == "CONTRACT":
            continue                      # 白は件数のみ(ファイルには残す)
        print(f"  [{kind}] {op} x{v['n']} {exc}: {msg}")


if __name__ == "__main__":
    main()
