# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""手書き経路の場面の台帳 ``fullseye/data/GPU_ACCEL_USE.json`` を実測ログから作る / Build the accel-use ledger.

入力は ``docs/perf/logs/label/label_ops.jsonl``(領域の解析の族の GPU 実測、``tools/bench_label_ops.py measure``
で手で測って commit)だけ。採否と場面(``single`` / ``pipeline``)は ``tools/bench_label_ops.build`` が決める。
``gpu_route`` がこの台帳を読み、op ノート(``tools/opdocs.py``)の GPU 欄も gpu_route から書くので、
regen_all の鎖では op ノートより前に回す(他の段の生成物を読まない)。

    py -3.11 tools/gen_accel_use.py           # 書く
    py -3.11 tools/gen_accel_use.py --check   # 差があれば exit 1
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "fullseye" / "data" / "GPU_ACCEL_USE.json"


def text() -> str:
    sys.path.insert(0, str(ROOT))
    from tools.bench_label_ops import build
    return json.dumps(build(), ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    ns = ap.parse_args(argv)
    new = text()
    if ns.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != new:
            print("stale: fullseye/data/GPU_ACCEL_USE.json")
            return 1
        return 0
    OUT.write_text(new, encoding="utf-8", newline="\n")
    print("wrote fullseye/data/GPU_ACCEL_USE.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
