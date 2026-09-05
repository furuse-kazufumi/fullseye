"""Emit CommandWorker spec JSONs for the full S0/S1/S2 graph across 3 problems.

Writes specs/*.json (list-arg, shared absolute workdir so the raptor board picks
the artifacts up). It does NOT touch the work-graph DB — the caller runs
`raptor-worklog add` with these spec files (kept as a separate, auditable step).
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _default_workdir() -> str:
    """work-graph の作業 dir。**配布物にローカル絶対パスを焼き込まない**ため環境変数から。

    2026-09-05 の監査で、非公開の兄弟ツリーのパスが PyPI の wheel に載っていた。
    手元の使い勝手は `$RAPTOR_DIR` で保ち、未設定なら `--workdir` を要求する。
    """
    root = os.environ.get("RAPTOR_DIR", "")
    return os.path.join(root, "out", "worklog", "imgevolve") if root else ""
PROBLEMS = ("denoise", "edge", "binarize")


def spec(cmd_tail: list[str], workdir: str, timeout: int, out_ext: str) -> dict:
    return {
        "cmd": ["py", "-3.11", *cmd_tail, "--workdir", workdir, "--out", f"<OUT>{out_ext}"],
        "cwd": str(HERE),
        "env": {"PYTHONUTF8": "1"},
        "produces": f"<OUT>{out_ext}",
        "timeout": timeout,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workdir", default=_default_workdir(),
                    help="work-graph の作業 dir(既定は $RAPTOR_DIR/out/worklog/imgevolve)")
    a = ap.parse_args()
    sd = HERE / "specs"; sd.mkdir(exist_ok=True)
    w = a.workdir

    for p in PROBLEMS:
        (sd / f"s0_{p}.json").write_text(json.dumps(
            spec(["baseline.py", "--problem", p, "--seed", "0"], w, 600, ".json"), indent=2), "utf-8")
        (sd / f"s1_{p}.json").write_text(json.dumps(
            spec(["evolve.py", "--problem", p, "--gens", "40", "--pop", "24", "--seed", "0"], w, 3600, ".json"),
            indent=2), "utf-8")
        (sd / f"metrics_{p}.json").write_text(json.dumps(
            spec(["report.py", "--problem", p], w, 300, ".md"), indent=2), "utf-8")
    # S2 codegen+difftest on the C-demonstrable problem (edge)
    (sd / "codegen_edge.json").write_text(json.dumps(
        spec(["codegen.py", "--problem", "edge"], w, 300, ".json"), indent=2), "utf-8")
    (sd / "difftest_edge.json").write_text(json.dumps(
        spec(["difftest.py", "--problem", "edge"], w, 600, ".json"), indent=2), "utf-8")
    print(f"wrote specs for {PROBLEMS} + edge codegen/difftest -> {sd}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
