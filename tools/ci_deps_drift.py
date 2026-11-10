"""PR の依存の版が、最後の全数の run から変わっていないかを確かめる(2026-11-10)。

なぜ要るか
----------
PR は変更に関係するテストだけを回す(``tools/ci_select_tests.py``)。ところが失敗には
**diff と無関係なもの**がある。2026-11-05 の #271 は 1 ファイルのテストを足しただけの PR で、
別のテスト(``test_t8_blas_cap_is_restored_after_contexts_interleave_across_threads``)が落ちた。
原因は同じ日に出た threadpoolctl 3.8.0(``tests/test_fix_t8_flake_2026_11_05.py``)。
変更から依存を辿る判定は、この型を原理的に選べない。

そこで「PR が入れる依存の版」を、最後に緑だった全数の run(master への push か毎日の
schedule)が実際に入れた版と比べ、**1 つでも違えば full suite** にする。

* 全数の run の py3.11 片 1 が ``pip freeze`` を 2 回残す(artifact ``pip-freeze-py3.11``):
  本体を入れた直後(``freeze-main.txt``)と、torch 系を足した後(``freeze-full.txt``)。
* PR の changes ジョブは、本体の要求を ``pip install --dry-run --report`` で丸ごと解決し
  (何も入れない)、``freeze-main.txt`` と**全部の名前**で比べる。torch 系はテストのジョブと
  同じ索引で**その 4 つの版だけ**を解決し(``--no-deps``)、``freeze-full.txt`` と比べる
  (torch の索引の依存を dry-run で正確に再現できないため。下流の版の差は本体の側で大半が見える)。
* 基準が取れない・解決に失敗した、も full(fail-safe)。

要求の並び(``MAIN_REQUIREMENTS`` / ``OPTIONAL_REQUIREMENTS``)は ``.github/workflows/ci.yml`` の
テストのジョブの ``pip install`` と同じでなければならない(``tests/test_ci_select_tests_2026_11_10.py``
が突き合わせる)。標準ライブラリだけで動く。

使い方::

    python tools/ci_deps_drift.py --freeze freeze-main.txt          # 全数の run(本体の後)
    python tools/ci_deps_drift.py --freeze freeze-full.txt          # 全数の run(torch 系の後)
    python tools/ci_deps_drift.py --resolve resolved/                # PR(何も入れない)
    python tools/ci_deps_drift.py --compare baseline/ resolved/      # 0 = 同じ / 1 = 違う / 2 = 比べられない
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

#: テストのジョブの「Install with optional backends (no torch)」と同じ要求。
MAIN_REQUIREMENTS: tuple[str, ...] = (
    "-e", ".[opencv,skimage,pil,wavelets,gui,video,volume,gltf,lidar,pcd,xlsx,export-verify]",
    "pytest", "pytest-cov", "pytest-split", "matplotlib", "sympy", "ziglang", "hypothesis",
    "pytest-timeout",
)
#: 同じジョブの「Optional backends (py3.11 only)」と同じ要求(torch は CPU 版の索引)。
TORCH_INDEX = "https://download.pytorch.org/whl/cpu"
OPTIONAL_REQUIREMENTS: tuple[str, ...] = (
    "torch>=2.13", "kornia>=0.9", "mahotas>=1.4", "opencv-contrib-python>=4.8.1.78",
)
#: 比べない(runner と CI の道具・この repo 自身)。
IGNORED = {"pip", "setuptools", "wheel", "fullseye", "imgevolve", "pkg-resources"}

_NL = "\n"


def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_freeze(text: str) -> dict[str, str]:
    """``pip freeze`` / ``name==version`` の行 -> {名前: 版}(editable と URL の行は外す)。"""
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "-e ", "--")) or " @ " in line:
            continue
        name, sep, ver = line.partition("==")
        if sep and _norm(name) not in IGNORED:
            out[_norm(name)] = ver.strip()
    return out


def _dump(pins: dict[str, str]) -> str:
    return "".join("%s==%s%s" % (k, v, _NL) for k, v in sorted(pins.items()))


def _dry_run(args: list[str], index_url: str | None = None) -> dict[str, str]:
    with tempfile.TemporaryDirectory() as tmp:
        report = Path(tmp) / "report.json"
        cmd = [sys.executable, "-m", "pip", "install", "--dry-run", "--ignore-installed",
               "--disable-pip-version-check", "--report", str(report)]
        if index_url:
            cmd += ["--index-url", index_url]
        cmd += list(args)
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError("pip could not resolve:" + _NL + proc.stdout[-3000:] + proc.stderr[-3000:])
        items = json.loads(report.read_text(encoding="utf-8"))["install"]
    out = {}
    for it in items:
        name = _norm(it["metadata"]["name"])
        if name not in IGNORED:
            out[name] = it["metadata"]["version"]
    if not out:
        raise RuntimeError("the resolver returned nothing")
    return out


def resolve_main() -> dict[str, str]:
    """テストのジョブ(py3.11)の本体の ``pip install`` が今入れるはずの版(依存を全部)。"""
    return _dry_run(list(MAIN_REQUIREMENTS))


def resolve_optional() -> dict[str, str]:
    """torch 系 4 つの版だけ(テストのジョブと同じ索引: torch は CPU 版の索引、他は PyPI)。"""
    out = {}
    for req in OPTIONAL_REQUIREMENTS:
        idx = TORCH_INDEX if req.startswith("torch") else None
        name = _norm(re.split(r"[<>=!~ ]", req, maxsplit=1)[0])
        got = _dry_run(["--no-deps", req], index_url=idx)
        if name not in got:
            raise RuntimeError("could not resolve %s" % req)
        out[name] = got[name]
    return out


def compare(baseline: dict[str, str], resolved: dict[str, str]) -> list[str]:
    """違い(人が読む文)。*resolved* の全部の名前を基準と比べる。基準にしか無い名前は数えない
    (runner に元から在る道具など)。"""
    diffs = []
    for name in sorted(resolved):
        if name not in baseline:
            diffs.append("%s: new (%s)" % (name, resolved[name]))
        elif baseline[name] != resolved[name]:
            diffs.append("%s: %s -> %s" % (name, baseline[name], resolved[name]))
    return diffs


def compare_dirs(base_d: Path, res_d: Path) -> tuple[int, list[str]]:
    """(0 = 同じ / 1 = 違う / 2 = 比べられない, 文)。"""
    diffs: list[str] = []
    for res_fn, base_fn in (("main.txt", "freeze-main.txt"), ("optional.txt", "freeze-full.txt")):
        bp, rp = base_d / base_fn, res_d / res_fn
        if not bp.exists() or not rp.exists():
            return 2, ["missing %s or %s" % (bp, rp)]
        base = parse_freeze(bp.read_text(encoding="utf-8"))
        res = parse_freeze(rp.read_text(encoding="utf-8"))
        if not base or not res:
            return 2, ["empty baseline or resolution (%s / %s)" % (bp.name, rp.name)]
        diffs += compare(base, res)
    return (1 if diffs else 0), diffs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split(_NL)[0])
    ap.add_argument("--freeze", metavar="OUT", help="この環境の pip freeze を正規化して書く(全数の run)")
    ap.add_argument("--resolve", metavar="DIR",
                    help="テストのジョブと同じ要求を dry-run で解決し DIR/main.txt・DIR/optional.txt に書く(PR)")
    ap.add_argument("--compare", nargs=2, metavar=("BASELINE_DIR", "RESOLVED_DIR"),
                    help="main.txt と freeze-main.txt、optional.txt と freeze-full.txt を比べる。"
                         "違いがあれば exit 1、基準が無い・空なら exit 2")
    args = ap.parse_args(argv)
    if args.freeze:
        text = subprocess.run([sys.executable, "-m", "pip", "freeze"], check=True,
                              capture_output=True, text=True).stdout
        frozen = parse_freeze(text)
        Path(args.freeze).write_text(_dump(frozen), encoding="utf-8")
        print("froze %d packages" % len(frozen))
    if args.resolve:
        out = Path(args.resolve)
        out.mkdir(parents=True, exist_ok=True)
        for fn, res in (("main.txt", resolve_main()), ("optional.txt", resolve_optional())):
            (out / fn).write_text(_dump(res), encoding="utf-8")
            print("resolved %d packages -> %s" % (len(res), fn))
    if args.compare:
        code, lines = compare_dirs(Path(args.compare[0]), Path(args.compare[1]))
        for line in lines:
            print(line)
        return code
    return 0


if __name__ == "__main__":
    sys.exit(main())
