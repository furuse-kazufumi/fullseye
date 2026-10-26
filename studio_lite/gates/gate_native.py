# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Studio-lite v0 の門(CPython 側): ブラウザが書いたレシピ JSON を **desktop Studio と同じ経路** で読んで走らせ、
ブラウザの出力と ULP で照合する。

    py -3.11 studio_lite/gates/gate_native.py <gate_browser.mjs の out dir>

見るもの(全部通って exit 0):
  1. ``engine.FullseyeEngine.load(<i>.json)`` が読める(engine の形 ``fullseye_pipeline`` / ``name`` / ``stages``)
  2. ``studio.validate_pipeline_dict`` が同じ JSON を受ける(Studio の Open pipeline と同じ検査)
  3. engine で走らせた最終結果が、ブラウザの最終結果と **bit 一致 or 1 ULP 以内**(非配列は repr 一致)
  4. ブラウザが Studio 形式(bypass 印つきの 4 要素段)を読めている(browser_gate.json の studio_format_loaded)
  5. 逆向き: Studio 形式の JSON を engine 経由で走らせたものと、ブラウザが読み直した段列を走らせたものが一致
結果は ``<out>/gate_native.json`` に残す。
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools", "probe_studio_web"))
sys.path.insert(0, os.path.join(ROOT, "studio_lite"))


def main(argv=None) -> int:
    import numpy as np
    import api
    import engine
    import studio
    import core
    import verify_ops_body
    from compare_outputs import ulp_diff
    out = (argv or sys.argv[1:])[0]
    B = json.load(open(os.path.join(out, "browser_gate.json"), encoding="utf-8"))
    zb = np.load(os.path.join(out, "browser_outputs.npz"))
    img = verify_ops_body.load_input(ROOT)
    core.set_subset(open(os.path.join(ROOT, "studio_lite", "ops_subset.json"), encoding="utf-8").read())
    G = json.load(open(os.path.join(ROOT, "studio_lite", "gates", "recipes_gate.json"), encoding="utf-8"))
    rows, fails = [], []
    for r in B["rows"]:
        i = r["i"]
        path = os.path.join(out, "recipes", "%02d.json" % i)
        d = json.load(open(path, encoding="utf-8"))
        row = {"i": i, "name": r["name"], "engine_load": False, "studio_validate": False, "verdict": None}
        try:
            eng = engine.FullseyeEngine.load(path)
            row["engine_load"] = True
            row["engine_stages"] = [list(s) for s in eng.stages]
        except Exception as e:  # noqa: BLE001
            row["engine_error"] = "%s: %s" % (type(e).__name__, e)
            fails.append(row)
            rows.append(row)
            continue
        try:
            studio.validate_pipeline_dict(d)
            row["studio_validate"] = True
        except Exception as e:  # noqa: BLE001
            row["studio_error"] = "%s: %s" % (type(e).__name__, e)
        native = eng.run(img)
        key = "r%02d" % i
        if r["kind"] == "ndarray":
            xb = zb[key]
            xa = np.asarray(native)
            if xa.shape != xb.shape or str(xa.dtype) != str(xb.dtype):
                row["verdict"] = "shape_or_dtype_differs"
                row["native"] = [list(xa.shape), str(xa.dtype)]
                row["browser"] = [list(xb.shape), str(xb.dtype)]
            else:
                u, dmax = ulp_diff(xa, xb)
                row["max_ulp"], row["max_abs"] = u, dmax
                row["verdict"] = "bit_identical" if u == 0 else ("within_1ulp" if (u is not None and u <= 1) else "beyond_1ulp")
        else:
            # engine.run は np.float64、api.apply は float を返す(repr が "np.float64(19.0)" と "19.0" で違う)。
            # 数値なら値で比べ、数値でなければ repr で比べる。
            same = repr(native) == r["repr"]
            if not same:
                try:
                    same = float(np.asarray(native).item()) == float(r["repr"].replace("np.float64(", "").rstrip(")"))
                except (TypeError, ValueError):
                    same = False
            row["verdict"] = "nonarray_equal" if same else "nonarray_differs"
            row["native"], row["browser"] = repr(native), r["repr"]
        row["ms_browser"], row["ms_native_engine"] = r["ms"], None
        import time
        t = time.perf_counter()
        eng.run(img)
        row["ms_native_engine"] = round((time.perf_counter() - t) * 1e3, 2)
        if row["verdict"] not in ("bit_identical", "within_1ulp", "nonarray_equal") or not row["studio_validate"]:
            fails.append(row)
        rows.append(row)
    # 4 + 5: Studio 形式(bypass つき)の往復
    sf = B.get("studio_format_loaded") or {}
    sample = G["studio_format_sample"]
    rev = {"browser_read_studio_format": bool(sf.get("stages")), "stages_seen_by_browser": sf.get("stages")}
    try:
        st_native = studio.validate_pipeline_dict(sample)
        # Studio は bypass 印(4 要素目 true)の段を走らせない —— ブラウザ側も同じに読んでいるかを見る
        a = api.run_pipeline(img, [tuple(s[:3]) for s in st_native if not (len(s) == 4 and s[3] is True)])
        rev["bypassed_in_studio"] = [s[0] for s in st_native if len(s) == 4 and s[3] is True]
        rev["bypassed_in_browser"] = sf.get("bypassed")
        b = api.run_pipeline(img, [tuple(s) for s in sf["stages"]])
        u, dmax = ulp_diff(np.asarray(a), np.asarray(b))
        rev["same_result"] = (u == 0)
        rev["max_ulp"] = u
    except Exception as e:  # noqa: BLE001
        rev["error"] = "%s: %s" % (type(e).__name__, e)
        rev["same_result"] = False
    if not rev.get("same_result"):
        fails.append({"name": "studio_format_roundtrip", **rev})
    summary = {"n": len(rows), "pass": len(rows) - sum(1 for r in rows if r in fails),
               "verdicts": {v: sum(1 for r in rows if r["verdict"] == v) for v in sorted({r["verdict"] for r in rows} - {None})},
               "studio_format_roundtrip": rev, "fails": [f.get("name") for f in fails],
               "speed_ratio_browser_over_native": sorted(round(r["ms_browser"] / r["ms_native_engine"], 2) for r in rows if r.get("ms_native_engine"))}
    with open(os.path.join(out, "gate_native.json"), "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "rows": rows, "browser_python": B.get("python")}, f, ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    for r in rows:
        print("%2d %-40s %-18s ulp=%s abs=%s  browser %s ms / native %s ms" % (r["i"], r["name"], r["verdict"], r.get("max_ulp"), r.get("max_abs"), r.get("ms_browser"), r.get("ms_native_engine")))
    return 0 if not fails else 1


if __name__ == "__main__":
    raise SystemExit(main())
