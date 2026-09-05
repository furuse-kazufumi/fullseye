# -*- coding: utf-8 -*-
"""配布物(wheel)の側で不変条件を数える —— CI の `Wheel completeness` から呼ぶ。

**なぜ別スクリプトなのか**: これは editable な checkout ではなく、
`pip install` した wheel の中で走る必要がある。checkout では
`sys.path` に source dir が入るので**全 root モジュールが見えてしまい**、
py-modules の漏れが原理的に再現しない。

2026-09-05 実測: `backends_halcon_ext` / `backends_typed` が py-modules に無く、
`pip install fullseye` した環境で op が **857 → 633(-224、26%)**。
`ops.FAILED_BACKENDS` にはその 2 件が最初から記録されていたが、
**それを見る門は checkout の側にしか立っていなかった**。
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings

warnings.filterwarnings("ignore")


def _dump(path: str) -> int:
    import fullseye
    import ops
    payload = {
        "version": getattr(fullseye, "__version__", "?"),
        "ops": sorted(fullseye.op_names()),
        "failed_backends": [list(x) for x in getattr(ops, "FAILED_BACKENDS", [])],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    print("%s: %d op / failed_backends %d"
          % (path, len(payload["ops"]), len(payload["failed_backends"])))
    return 0


def _compare(a_path: str, b_path: str) -> int:
    a = json.load(open(a_path, encoding="utf-8"))          # editable
    b = json.load(open(b_path, encoding="utf-8"))          # wheel
    problems = []
    lost = sorted(set(a["ops"]) - set(b["ops"]))
    if lost:
        problems.append("wheel から消えた op %d 本(先頭 30): %s" % (len(lost), lost[:30]))
    if b["failed_backends"]:
        problems.append("wheel 側で読み込めなかった backend: %s" % (b["failed_backends"],))
    print("editable %d op / wheel %d op" % (len(a["ops"]), len(b["ops"])))
    if problems:
        for t in problems:
            print("NG:", t)
        return 1
    print("OK: 配布物に欠けている op は無い")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dump", metavar="OUT")
    ap.add_argument("--compare", nargs=2, metavar=("EDITABLE", "WHEEL"))
    ns = ap.parse_args(argv)
    if ns.dump:
        return _dump(ns.dump)
    if ns.compare:
        return _compare(*ns.compare)
    ap.error("--dump か --compare のどちらかが要る")


if __name__ == "__main__":
    sys.exit(main())
