# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""探針(probe)の照合: 2 つの実行(CPython と Pyodide)の op 出力を **ULP** で比べる。

    py -3.11 compare_outputs.py <out dir> <tag A> <tag B> [--ops-json <path>]

``<tag>_verify.json`` と ``<tag>_outputs.npz`` を読み、両方で ok だった op ごとに:
  * 形と dtype が同じか
  * bit 一致か(bool / 整数は完全一致、浮動小数は view を整数にして一致)
  * 違う場合は最大 ULP 差(float32 は float32 の ULP、float64 は float64 の)と最大絶対差
を出す。集計: 両方 ok / bit 一致 / 1 ULP 以内 / それ以上 / 形違い / 片方だけ失敗。
``--ops-json`` を渡すと、**B(ブラウザ側)で走って A と 1 ULP 以内で一致した op の一覧**をそこへ書く
(Studio-lite v0 が「ブラウザで使える op」として読む台帳)。
"""
from __future__ import annotations

import argparse
import json
import os
import sys


def ulp_diff(a, b):
    import numpy as np
    a = np.asarray(a)
    b = np.asarray(b)
    if a.dtype.kind in "fc" and b.dtype.kind in "fc":
        dt = np.result_type(a.dtype, b.dtype)
        a = a.astype(dt)
        b = b.astype(dt)
        if dt == np.float32:
            ia, ib = a.view(np.int32).astype(np.int64), b.view(np.int32).astype(np.int64)
        elif dt == np.float64:
            ia, ib = a.view(np.int64), b.view(np.int64)
        else:
            return None, float(np.nanmax(np.abs(a - b))) if a.size else 0.0
        both_nan = np.isnan(a) & np.isnan(b)
        d = np.abs(ia - ib)
        d[both_nan] = 0
        absd = np.abs(a - b)
        absd[both_nan] = 0
        return int(d.max()) if d.size else 0, float(np.nanmax(absd)) if absd.size else 0.0
    eq = np.array_equal(a, b)
    return (0 if eq else None), (0.0 if eq else float(np.max(np.abs(a.astype(np.float64) - b.astype(np.float64)))))


def main(argv=None) -> int:
    import numpy as np
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out_dir")
    ap.add_argument("tag_a")
    ap.add_argument("tag_b")
    ap.add_argument("--ops-json")
    a = ap.parse_args(argv)
    A = json.load(open(os.path.join(a.out_dir, a.tag_a + "_verify.json"), encoding="utf-8"))
    B = json.load(open(os.path.join(a.out_dir, a.tag_b + "_verify.json"), encoding="utf-8"))
    za = np.load(os.path.join(a.out_dir, a.tag_a + "_outputs.npz"))
    zb = np.load(os.path.join(a.out_dir, a.tag_b + "_outputs.npz"))
    names = sorted(set(A["rows"]) | set(B["rows"]))
    res = {"both_ok": 0, "bit_identical": 0, "within_1ulp": 0, "beyond_1ulp": 0, "shape_or_dtype_differs": 0,
           "only_a_ok": 0, "only_b_ok": 0, "both_fail": 0, "nonarray_equal": 0, "nonarray_differs": 0}
    per = {}
    for n in names:
        ra, rb = A["rows"].get(n), B["rows"].get(n)
        if not ra or not rb:
            continue
        if ra["ok"] and not rb["ok"]:
            res["only_a_ok"] += 1
            per[n] = {"verdict": "only_a_ok", "err_b": rb.get("error")}
            continue
        if rb["ok"] and not ra["ok"]:
            res["only_b_ok"] += 1
            per[n] = {"verdict": "only_b_ok", "err_a": ra.get("error")}
            continue
        if not ra["ok"] and not rb["ok"]:
            res["both_fail"] += 1
            per[n] = {"verdict": "both_fail"}
            continue
        res["both_ok"] += 1
        if ra["kind"] != "ndarray" or rb["kind"] != "ndarray":
            same = ra.get("repr") == rb.get("repr")
            res["nonarray_equal" if same else "nonarray_differs"] += 1
            per[n] = {"verdict": "nonarray_equal" if same else "nonarray_differs", "a": ra.get("repr"), "b": rb.get("repr")}
            continue
        xa, xb = za[n], zb[n]
        if xa.shape != xb.shape or str(xa.dtype) != str(xb.dtype):
            res["shape_or_dtype_differs"] += 1
            per[n] = {"verdict": "shape_or_dtype_differs", "a": [list(xa.shape), str(xa.dtype)], "b": [list(xb.shape), str(xb.dtype)]}
            continue
        u, d = ulp_diff(xa, xb)
        if u == 0:
            res["bit_identical"] += 1
            v = "bit_identical"
        elif u is not None and u <= 1:
            res["within_1ulp"] += 1
            v = "within_1ulp"
        else:
            res["beyond_1ulp"] += 1
            v = "beyond_1ulp"
        per[n] = {"verdict": v, "max_ulp": u, "max_abs": d, "ms_a": ra["ms"], "ms_b": rb["ms"]}
    ratios = [per[n]["ms_b"] / per[n]["ms_a"] for n in per if "ms_a" in per[n] and per[n]["ms_a"] > 0.05]
    if ratios:
        ratios.sort()
        res["speed_ratio_b_over_a"] = {"median": round(ratios[len(ratios) // 2], 2),
                                       "p10": round(ratios[len(ratios) // 10], 2),
                                       "p90": round(ratios[(len(ratios) * 9) // 10], 2), "n": len(ratios)}
    out = {"a": a.tag_a, "b": a.tag_b, "summary": res, "per_op": per}
    with open(os.path.join(a.out_dir, "compare_%s_vs_%s.json" % (a.tag_a, a.tag_b)), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    beyond = [(n, per[n]["max_ulp"], per[n]["max_abs"]) for n in per if per[n]["verdict"] == "beyond_1ulp"]
    beyond.sort(key=lambda t: -(t[1] or 0))
    print("beyond_1ulp (worst 25):", beyond[:25])
    print("only_a_ok:", [(n, per[n].get("err_b")) for n in per if per[n]["verdict"] == "only_a_ok"][:40])
    if a.ops_json:
        good = sorted(n for n in per if per[n]["verdict"] in ("bit_identical", "within_1ulp", "nonarray_equal"))
        rows_b = B["rows"]
        with open(a.ops_json, "w", encoding="utf-8") as f:
            json.dump({"source": "tools/probe_studio_web/compare_outputs.py %s vs %s" % (a.tag_a, a.tag_b),
                       "criterion": "both ran; output bit-identical or within 1 ULP of CPython (non-array results: repr equal)",
                       "n": len(good),
                       "ops": [{"name": n, "in": rows_b[n]["in"], "out": rows_b[n]["out"], "ms_browser": rows_b[n]["ms"],
                                "ms_native": A["rows"][n]["ms"], "verdict": per[n]["verdict"]} for n in good]},
                      f, ensure_ascii=False, indent=1)
        print("wrote", a.ops_json, len(good))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
