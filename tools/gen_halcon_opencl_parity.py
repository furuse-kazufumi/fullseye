#!/usr/bin/env python3
"""HALCON 26.05 "Supports OpenCL compute devices" 84 演算子 vs Fullseye 対応行列.

正本 = ``docs/perf/halcon_2605_opencl_ops.json``(HALCON 26.05 の古典演算子のうち
OpenCL 対応と明記された 84 件を vendor したもの; 元は HALCON 演算子コーパスの棚卸し
notes/halcon_2605_opencl_ops.json)。各 HALCON 名を Fullseye の
機械可読索引 (``docs/OP_INDEX.json`` の ``halcon`` 欄) と実装台帳 (``accel.ACCEL``)
から Fullseye op / GPU 経路の有無へ対応づける。

出力:
* ``docs/perf/HALCON_OPENCL_PARITY.md`` — 84 件の表(HALCON 名 / 章 / Fullseye op /
  GPU 経路 / 備考)+ 見出しの 3 数字。
* ``docs/perf/halcon_opencl_parity.json`` — 同じ内容の機械可読版。

見出しの数字は 3 つだけ: 対応あり N1 / そのうち GPU 経路あり N2 / 未対応 N3。
門: **N1 + N3 = 84**。測っていない比較(「HALCON より速い」等)は書かない。

    py -3.11 tools/gen_halcon_opencl_parity.py
    py -3.11 tools/gen_halcon_opencl_parity.py --check
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "docs" / "perf" / "halcon_2605_opencl_ops.json"
INDEX = ROOT / "docs" / "OP_INDEX.json"
OUT_MD = ROOT / "docs" / "perf" / "HALCON_OPENCL_PARITY.md"
OUT_JSON = ROOT / "docs" / "perf" / "halcon_opencl_parity.json"


def _accel_maps():
    sys.path.insert(0, str(ROOT))
    import accel
    import accel_match
    import accel_vol
    halcon_gpu = {h for _n, (_f, _c, h) in accel.ACCEL.items() if h}
    core_gpu = {c for _n, (_f, c, _h) in accel.ACCEL.items()}
    core_gpu |= {c for _n, (_f, c) in accel_vol.VOL_ACCEL.items()}
    core_gpu |= set(accel_match.MATCH_ACCEL)
    return halcon_gpu, core_gpu


def build() -> dict:
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    idx = json.loads(INDEX.read_text(encoding="utf-8"))["ops"]
    halcon_gpu, core_gpu = _accel_maps()
    h2f = defaultdict(list)
    for o in idx:
        if o.get("halcon"):
            h2f[o["halcon"]].append(o["name"])
    rows = []
    for e in sorted(corpus, key=lambda x: (x["chapter"], x["name"])):
        hn = e["name"]
        fs = sorted(h2f.get(hn, []))
        gpu = (hn in halcon_gpu) or any(f in core_gpu for f in fs)
        if fs:
            note = "Fullseye 対応あり" + ("(GPU 経路あり)" if gpu else "(CPU のみ)")
        else:
            note = "Fullseye 未対応"
        rows.append({"halcon": hn, "chapter": e["chapter"], "page": e.get("page"),
                     "fullseye_ops": fs, "gpu_path": bool(gpu), "note": note})
    n1 = sum(1 for r in rows if r["fullseye_ops"])
    n2 = sum(1 for r in rows if r["fullseye_ops"] and r["gpu_path"])
    n3 = sum(1 for r in rows if not r["fullseye_ops"])
    assert n1 + n3 == len(rows) == 84, "N1+N3 != 84 (%d + %d, rows=%d)" % (n1, n3, len(rows))
    return {"generated_by": "tools/gen_halcon_opencl_parity.py",
            "source": "docs/perf/halcon_2605_opencl_ops.json",
            "total": len(rows), "n1_fullseye": n1, "n2_gpu": n2, "n3_missing": n3,
            "rows": rows}


def render_md(data: dict) -> str:
    L = ["# HALCON 26.05 OpenCL 84 演算子 — Fullseye 対応行列", "",
         "HALCON 26.05 で「Supports OpenCL compute devices」が付く古典演算子 %d 件"
         "(正本 `docs/perf/halcon_2605_opencl_ops.json`)を、Fullseye の機械可読索引"
         "(`docs/OP_INDEX.json` の `halcon` 欄)と実装台帳(`accel.ACCEL` ほか)に対応づけた。"
         % data["total"], "",
         "- **Fullseye 対応あり N1 = %d**" % data["n1_fullseye"],
         "- **そのうち GPU 経路あり N2 = %d**" % data["n2_gpu"],
         "- **未対応 N3 = %d**" % data["n3_missing"],
         "", "門: N1 + N3 = %d + %d = **%d**。" % (data["n1_fullseye"], data["n3_missing"],
                                                  data["n1_fullseye"] + data["n3_missing"]),
         "", "「HALCON より速い」等、測っていない比較は書かない。", "",
         "| HALCON 名 | 章 | Fullseye 対応 op | GPU 経路 | 備考 |",
         "|---|---|---|:---:|---|"]
    for r in data["rows"]:
        fs = ", ".join("`%s`" % x for x in r["fullseye_ops"]) if r["fullseye_ops"] else "—"
        gpu = "あり" if r["gpu_path"] else ("なし" if r["fullseye_ops"] else "—")
        L.append("| `%s` | %s | %s | %s | %s |" % (r["halcon"], r["chapter"], fs, gpu, r["note"]))
    L.append("")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    data = build()
    md = render_md(data)
    js = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
    if a.check:
        drift = []
        if not OUT_MD.exists() or OUT_MD.read_text(encoding="utf-8") != md:
            drift.append(str(OUT_MD))
        if not OUT_JSON.exists() or OUT_JSON.read_text(encoding="utf-8") != js:
            drift.append(str(OUT_JSON))
        if drift:
            print("[halcon_opencl_parity] DRIFT: %s" % ", ".join(drift))
            return 1
        print("[halcon_opencl_parity] up to date")
        return 0
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(md, encoding="utf-8")
    OUT_JSON.write_text(js, encoding="utf-8")
    print("[halcon_opencl_parity] N1=%d N2=%d N3=%d (N1+N3=%d) -> %s"
          % (data["n1_fullseye"], data["n2_gpu"], data["n3_missing"],
             data["n1_fullseye"] + data["n3_missing"], OUT_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
