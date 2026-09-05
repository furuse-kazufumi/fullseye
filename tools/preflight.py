# -*- coding: utf-8 -*-
"""リリース前の点検を**機械に実行させる**。手順書 `docs/RELEASE_CHECKLIST.md` の実行部。

    py -3.11 tools/preflight.py           # 既定(全数テスト以外)
    py -3.11 tools/preflight.py --full    # 全数テストも含む(+20 分)
    py -3.11 tools/preflight.py --only wheel,linux

**なぜ道具にするのか**: 2026-09-05 に出した 0.1.8 で、次が全部「知っていたのに
やらなかった」形で起きた ——

* Linux CI が 0.1.6 から赤のまま 3 回リリースしていた(release は CI に依存していなかった)
* `pip install` した wheel から **224 op(26%)が消えていた**。
  `FAILED_BACKENDS` に理由つきで記録され、それを見るテストも**存在した**が、
  **その門は checkout の側にしか立っていなかった**(editable install は
  source dir を path に足すので、開発機では原理的に再現しない)
* 開発機(Windows)だけで確かめていた。Linux に入れて回したら、その場で
  **プロセス死 3 件・非有限漏れ 1 件・安全確認の空振り 1 件**が出た

チェックリストを「読んで思い出す」ものにすると、忙しい日に飛ばされる。
**判定を出す道具**にすれば飛ばせない。各項目は PASS / FAIL / SKIP と
**測った数**を出す。1 つでも FAIL なら終了コードは非ゼロ。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable


class Result:
    __slots__ = ("name", "state", "detail")

    def __init__(self, name, state, detail=""):
        self.name, self.state, self.detail = name, state, detail


def _run(cmd, cwd=ROOT, timeout=1800, env=None):
    e = dict(os.environ)
    e.setdefault("PYTHONUTF8", "1")
    if env:
        e.update(env)
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                          timeout=timeout, env=e, errors="replace")


# --------------------------------------------------------------------------- #
# 個々の点検
# --------------------------------------------------------------------------- #

def check_version() -> Result:
    """pyproject / CITATION.cff / CHANGELOG の版が揃っているか。

    揃っていないまま タグを打つと release ワークフローの版照合で落ちる —— が、
    そこで落ちると**タグを打ち直す**羽目になるので、手前で見る。
    """
    import tomllib
    v = tomllib.load(open(os.path.join(ROOT, "pyproject.toml"), "rb"))["project"]["version"]
    cff = open(os.path.join(ROOT, "CITATION.cff"), encoding="utf-8").read()
    chg = open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8").read()
    bad = []
    if ("version: %s" % v) not in cff:
        bad.append("CITATION.cff が %s になっていない" % v)
    if ("## %s " % v) not in chg:
        bad.append("CHANGELOG に '## %s' の節が無い" % v)
    r = _run(["git", "tag", "-l", "v" + v])
    if r.stdout.strip():
        bad.append("タグ v%s が既にある" % v)
    return Result("version", "FAIL" if bad else "PASS",
                  "; ".join(bad) if bad else "%s で揃っている" % v)


def check_ruff() -> Result:
    if shutil.which("ruff") is None:
        return Result("ruff", "SKIP", "ruff が無い")
    r = _run(["ruff", "check", ".", "--quiet"])
    n = len([x for x in r.stdout.splitlines() if x.strip()])
    return Result("ruff", "PASS" if r.returncode == 0 else "FAIL",
                  "指摘なし" if r.returncode == 0 else "%d 行の指摘" % n)


def check_ledger_gates() -> Result:
    """台帳(既知の不良を許すリスト)を守るテストが通るか。

    ★台帳そのものではなく**門**を見ている。台帳に古い項目が残ると、
    直った不具合が「既知」のまま居座り、次に壊れたときに気づけない。
    """
    files = ["tests/test_degenerate_inputs.py", "tests/test_op_knob_liveness.py",
             "tests/test_backends_typed_liveness.py", "tests/test_op_descriptions.py",
             "tests/test_fallback_policy.py", "tests/test_packaging_foundation.py",
             "tests/test_op_name_uniqueness.py", "tests/test_ops3d_ledger.py"]
    have = [f for f in files if os.path.exists(os.path.join(ROOT, f))]
    r = _run([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider"] + have)
    last = [x for x in r.stdout.strip().splitlines() if x.strip()][-1:] or [""]
    return Result("ledger-gates", "PASS" if r.returncode == 0 else "FAIL", last[0][:110])


def check_wheel() -> Result:
    """**配布物の側で数える。** editable と wheel で op 集合が一致するか。

    ここが 0.1.8 で 224 op を失った経路。editable install は source dir を
    `sys.path` に足すので、**開発機では絶対に再現しない**。
    """
    tmp = tempfile.mkdtemp(prefix="fs_preflight_")
    try:
        chk = os.path.join(ROOT, "tools", "ci_wheel_check.py")
        if not os.path.exists(chk):
            return Result("wheel", "SKIP", "tools/ci_wheel_check.py が無い")
        a = os.path.join(tmp, "ops_editable.json")
        if _run([PY, chk, "--dump", a]).returncode != 0:
            return Result("wheel", "FAIL", "editable 側の集計に失敗")
        # ★`build/lib` に前回の staging コピーが残っていると、setuptools はそれを
        # **そのまま wheel に詰める**(2026-09-05 実測: py-modules から外したモジュールが
        # wheel に入ったままで、門の変異テストが通ってしまった)。release.yml が
        # clean checkout から建てる理由と同じ。ここでも建てる前に必ず捨てる。
        shutil.rmtree(os.path.join(ROOT, "build", "lib"), ignore_errors=True)
        b = _run([PY, "-m", "build", "--wheel", "-o", os.path.join(tmp, "dist")], timeout=1800)
        if b.returncode != 0:
            return Result("wheel", "FAIL", "wheel のビルドに失敗: " + b.stderr[-160:])
        whl = [f for f in os.listdir(os.path.join(tmp, "dist")) if f.endswith(".whl")]
        if not whl:
            return Result("wheel", "FAIL", "wheel が出来ていない")
        venv = os.path.join(tmp, "venv")
        if _run([PY, "-m", "venv", venv]).returncode != 0:
            return Result("wheel", "FAIL", "venv を作れない")
        vpy = os.path.join(venv, "Scripts" if os.name == "nt" else "bin",
                           "python.exe" if os.name == "nt" else "python")
        _run([vpy, "-m", "pip", "-q", "install", "numpy", "scipy",
              os.path.join(tmp, "dist", whl[0])], timeout=1800)
        c = os.path.join(tmp, "ops_wheel.json")
        if _run([vpy, chk, "--dump", c]).returncode != 0:
            return Result("wheel", "FAIL", "wheel 側の集計に失敗")
        r = _run([PY, chk, "--compare", a, c])
        line = [x for x in r.stdout.splitlines() if x.strip()][-1:] or [""]
        return Result("wheel", "PASS" if r.returncode == 0 else "FAIL", line[0][:110])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


_SWEEP = r'''
import json, os, sys, warnings
warnings.filterwarnings("ignore")
import numpy as np, fullseye as F
log = sys.argv[1]
done = set()
if os.path.exists(log):
    for line in open(log, encoding="utf-8"):
        try: r = json.loads(line)
        except Exception: continue
        done.add((r["op"], r["kind"]))          # start だけの行 = そこで死んだ
out = open(log, "a", encoding="utf-8", buffering=1)
K = [("normal", lambda: np.linspace(0,1,64*64).reshape(64,64)),
     ("empty",  lambda: np.zeros((0,0))),
     ("nan",    lambda: np.full((16,16), np.nan)),
     ("inf",    lambda: np.full((16,16), np.inf)),
     ("ninf",   lambda: np.full((16,16), -np.inf)),
     ("one",    lambda: np.zeros((1,1))),
     ("halfnan",lambda: np.where(np.arange(256).reshape(16,16) % 2 == 0, np.nan, 0.5))]
for n in F.op_names():
    for kind, mk in K:
        if (n, kind) in done: continue
        out.write(json.dumps({"op": n, "kind": kind, "start": 1}) + "\n")
        try:
            o = F.apply(mk(), n, 0.5, 0.5)
            a = np.asarray(o if not isinstance(o, dict) else 0.0, float)
            st = "ok" if (a.size == 0 or np.all(np.isfinite(a))) else "nonfinite"
        except Exception as e:
            st = "raise:" + type(e).__name__
        out.write(json.dumps({"op": n, "kind": kind, "s": st}) + "\n")
out.write(json.dumps({"op": "-", "kind": "-", "all_done": 1}) + "\n")
'''


def _sweep_report(log_path, exempt):
    rows = []
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    res = [r for r in rows if "s" in r]
    started = [(r["op"], r["kind"]) for r in rows if r.get("start")]
    fin = {(r["op"], r["kind"]) for r in res}
    crashed = [s for s in started if s not in fin]
    nonfinite = sorted({r["op"] for r in res if r["s"] == "nonfinite"} - set(exempt))
    return len(res), crashed, nonfinite


def _degenerate(label, runner, workdir) -> Result:
    """退化入力(空 / 1 画素 / 全 NaN / ±Inf / 一部 NaN)を全 op に流す。

    ★**クラッシュで測定を失わない形**にしてある(1 行ずつ追記して再開する)。
    まとめて最後に書くと、プロセスが死んだ瞬間にそれまでの結果が全部消える。
    """
    import ops
    exempt = set(getattr(ops, "NONFINITE_IS_MEANINGFUL", {}))
    script = os.path.join(workdir, "sweep.py")
    log = os.path.join(workdir, "sweep.jsonl")
    open(script, "w", encoding="utf-8").write(_SWEEP)
    if os.path.exists(log):
        os.remove(log)
    for _ in range(40):
        runner(script, log)
        try:
            if any("all_done" in ln for ln in open(log, encoding="utf-8")):
                break
        except FileNotFoundError:
            return Result("degenerate:" + label, "FAIL", "スイープが起動しなかった")
    n, crashed, nonfinite = _sweep_report(log, exempt)
    if crashed or nonfinite:
        d = []
        if crashed:
            d.append("プロセス死 %d 件: %s" % (len(crashed), crashed[:4]))
        if nonfinite:
            d.append("非有限 %d 本: %s" % (len(nonfinite), nonfinite[:4]))
        return Result("degenerate:" + label, "FAIL", " / ".join(d))
    return Result("degenerate:" + label, "PASS", "%d 通り、クラッシュ 0・非有限 0" % n)


def check_degenerate_local() -> Result:
    tmp = tempfile.mkdtemp(prefix="fs_deg_")
    try:
        def run(script, log):
            _run([PY, script, log], timeout=1800)
        return _degenerate("local", run, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def check_degenerate_linux() -> Result:
    """★**開発機が Windows なら、ここが今日いちばん効いた点検**。

    2026-09-05: Windows では 1 件も落ちない入力で、Linux は 3 op が SIGSEGV。
    ネイティブのビルドが違えば境界の壊れ方も違う。
    """
    if os.name != "nt" or shutil.which("wsl") is None:
        return Result("degenerate:linux", "SKIP", "WSL が無い(Linux 上ならこの項目は local と同じ)")
    probe = _run(["wsl", "-e", "bash", "-lc",
                  "test -x /tmp/fs018/bin/python && /tmp/fs018/bin/python -c 'import fullseye'"])
    if probe.returncode != 0:
        return Result("degenerate:linux", "SKIP",
                      "WSL 側に検証用 venv が無い(docs/RELEASE_CHECKLIST.md の作り方を参照)")
    share = os.path.join(os.environ.get("TEMP", "/tmp"), "fs_preflight_linux")
    os.makedirs(share, exist_ok=True)
    wsl_share = "/mnt/" + share[0].lower() + share[2:].replace("\\", "/")

    def run(script, log):
        _run(["wsl", "-e", "bash", "-lc",
              "PYTHONPATH=/mnt/c/dev/projects/imgevolve /tmp/fs018/bin/python %s/%s %s/%s"
              % (wsl_share, os.path.basename(script), wsl_share, os.path.basename(log))],
             timeout=1800)
    return _degenerate("linux", run, share)


def check_ci() -> Result:
    """HEAD のコミットで CI が緑か。**0.1.6〜0.1.8 はここが赤のまま出ている。**"""
    if shutil.which("gh") is None:
        return Result("ci", "SKIP", "gh が無い")
    sha = _run(["git", "rev-parse", "HEAD"]).stdout.strip()
    r = _run(["gh", "api", "repos/{owner}/{repo}/actions/runs?head_sha=%s&per_page=50" % sha,
              "--jq", '[.workflow_runs[] | select(.name=="CI")] | sort_by(.created_at) | last | .conclusion'])
    conc = (r.stdout or "").strip()
    if not conc or conc in ("null",):
        return Result("ci", "FAIL", "このコミットで CI がまだ走っていない(push してから待つ)")
    return Result("ci", "PASS" if conc == "success" else "FAIL", "CI = %s" % conc)


def check_full_suite() -> Result:
    t = time.time()
    r = _run([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider"], timeout=5400)
    last = [x for x in r.stdout.strip().splitlines() if x.strip()][-1:] or [""]
    return Result("full-suite", "PASS" if r.returncode == 0 else "FAIL",
                  "%s (%.0f 分)" % (last[0][:90], (time.time() - t) / 60))


CHECKS = [
    ("version", check_version),
    ("ruff", check_ruff),
    ("ledgers", check_ledger_gates),
    ("wheel", check_wheel),
    ("degenerate", check_degenerate_local),
    ("linux", check_degenerate_linux),
    ("ci", check_ci),
]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--full", action="store_true", help="全数テストも走らせる(+20 分)")
    ap.add_argument("--only", help="実行する項目をカンマ区切りで指定")
    ns = ap.parse_args(argv)
    sys.path.insert(0, ROOT)

    todo = list(CHECKS)
    if ns.full:
        todo.append(("suite", check_full_suite))
    if ns.only:
        want = {x.strip() for x in ns.only.split(",")}
        todo = [(k, f) for k, f in todo if k in want]
        unknown = want - {k for k, _ in CHECKS} - {"suite"}
        if unknown:
            ap.error("知らない項目: %s" % sorted(unknown))
        if not todo:
            # ★`--only suite` を `--full` 無しで呼ぶと 0 項目になり、以前は
            # 「すべて PASS」と言って rc=0 で帰っていた(2026-09-05 レビューで実測)。
            # **何も検査していないのに通す門**は、無い門より悪い。
            ap.error("実行する項目が 0 件(suite は --full と併用)。")

    results = []
    for key, fn in todo:
        print("… %s" % key, flush=True)
        t = time.time()
        try:
            res = fn()
        except Exception as e:                              # noqa: BLE001
            res = Result(key, "FAIL", "点検自体が落ちた: %s: %s" % (type(e).__name__, e))
        res.detail = "%s  [%.0fs]" % (res.detail, time.time() - t)
        results.append(res)

    print("\n" + "=" * 78)
    for r in results:
        print("%-6s %-20s %s" % (r.state, r.name, r.detail))
    print("=" * 78)
    fails = [r for r in results if r.state == "FAIL"]
    skips = [r for r in results if r.state == "SKIP"]
    if skips:
        print("SKIP が %d 件ある —— **飛ばした項目は「通った」ではない**。"
              " 理由を読んで、出す前に埋められるか判断すること。" % len(skips))
    if fails:
        print("FAIL %d 件。リリースしない。" % len(fails))
        return 1
    if skips:
        print("FAIL は無いが SKIP がある —— 終了コード 2(「通った」とは言わない)。")
        return 2
    print("すべて PASS。`docs/RELEASE_CHECKLIST.md` の**手でやる項目**を確認してから出す。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
