#!/usr/bin/env python3
"""partial / none の掃引(``out/gpu_auto_sweep_rest``)の採用分を許可リストへ足す。

先に ``tools/gpu_auto_sweep.py report``(required / suitable の掃引から許可リストを作り直す)を
走らせてから、これを走らせる。何度走らせても同じ結果になる(足した行には ``tier_swept`` を付け、
再実行時はその行だけを消して作り直す)。

    <GPU の venv の python> tools/gpu_auto_merge_rest.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ["GPU_SWEEP_OUT"] = "gpu_auto_sweep_rest"
os.environ["GPU_SWEEP_TIERS"] = "partial,none"
sys.path.insert(0, str(Path(__file__).resolve().parent))

import gpu_auto_report as R  # noqa: E402
import gpu_auto_sweep as S  # noqa: E402

ALLOW = S.ROOT / "fullseye" / "data" / "gpu_auto_allow.json"
MARK = "partial,none"


def main() -> int:
    rows = R.classes(S.OUT, S.load_targets(), S.is_python_loop, S.MIN_RATIO)
    allow = json.loads(ALLOW.read_text(encoding="utf-8"))
    for key in ("ops", "resident_ops", "pipeline_ops"):
        allow.setdefault(key, {})
        allow[key] = {k: v for k, v in allow[key].items() if v.get("tier_swept") != MARK}
    for r in rows:
        cl, name = r["class"], r["name"]
        if cl == "adopted":
            allow["ops"][name] = {"ratio": round(r["s"]["ratio"], 2), "family": r["family"],
                                  "hand_written_gpu": False, "tier_swept": MARK}
        elif cl in ("adopted_resident", "pipeline"):
            key = "resident_ops" if cl == "adopted_resident" else "pipeline_ops"
            allow[key][name] = {"ratio_resident": round(r["r"]["ratio"], 3),
                                "ratio_single": round(r["s"].get("ratio") or 0, 3),
                                "chain": r["r"].get("chain"), "family": r["family"],
                                "tier_swept": MARK}
    ALLOW.write_text(json.dumps(allow, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                     encoding="utf-8")
    print({k: len(allow[k]) for k in ("ops", "resident_ops", "pipeline_ops")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
