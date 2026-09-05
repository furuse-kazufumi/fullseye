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
import os
import sys
import tempfile
import warnings

warnings.filterwarnings("ignore")

# ★**このスクリプト自身の置き場所を sys.path から外す。** Python はスクリプトの
# ディレクトリを sys.path[0] に載せるので、checkout の `tools/` から起動すると
# wheel 側の venv でも `tools/` 配下(非同梱の chain_fuzz 等)が import できてしまい、
# 「wheel に無いものが見える」状態で数えることになる。2026-09-05 のレビューで、
# この門が **tb_* 143 op の欠落を見逃していた**のはまさにこれ。
# 併せて cwd も空の一時ディレクトリへ移す(cwd が checkout だと同じことが起きる)。
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:] = [p for p in sys.path
               if os.path.abspath(p or os.getcwd()) not in (_HERE, os.path.dirname(_HERE))]
# ★cwd を移す**前に**元の cwd を覚え、以後すべての引数パスをここへ解決する。
# 2026-09-05 実測: preflight は絶対パスで渡すので手元では通り、ci.yml は相対パスで
# 渡すので dump が一時 dir に書き捨てられ、compare が FileNotFoundError で落ちた
# —— **門が本番の呼び出し経路では一度も比較を実行していなかった**。
# 「門は事故の起きる場所に立てる」の 3 度目。呼ぶ側を直すのではなく、
# 相対パスで呼ばれても正しく動くようにして、この型ごと閉じる。
_ORIG_CWD = os.getcwd()
os.chdir(tempfile.mkdtemp(prefix="fs_wheelcheck_"))


def _at_orig(path: str) -> str:
    """引数で渡されたパスを、chdir する前の作業ディレクトリ基準で解決する。"""
    return path if os.path.isabs(path) else os.path.join(_ORIG_CWD, path)


def _loaded_root_modules() -> list:
    """レジストリを組み上げたあとに読み込まれている**root モジュール**名。

    第三者ライブラリ(cv2 / skimage …)も混ざるが、比較側で py-modules の宣言と
    突き合わせるので問題ない。ここで見たいのは「同梱のはずのモジュールが wheel 側で
    読まれていない」こと ―― それが 224 op / 143 op を失った形。
    """
    out = set()
    for name, m in list(sys.modules.items()):
        f = getattr(m, "__file__", None)
        if not f or "." in name or not f.endswith(".py"):
            continue
        out.add(name)
    return sorted(out)


def _dump(path: str) -> int:
    path = _at_orig(path)
    import fullseye
    import ops
    try:
        import ops3d                                   # noqa: F401  3-D 側も組み上げる
    except Exception:                                  # noqa: BLE001
        pass
    names = sorted(fullseye.op_names())
    declared = []
    pp = os.path.join(_HERE and os.path.dirname(_HERE), "pyproject.toml")
    if os.path.exists(pp):
        try:
            import tomllib
            declared = tomllib.load(open(pp, "rb"))["tool"]["setuptools"]["py-modules"]
        except Exception:                              # noqa: BLE001
            declared = []
    payload = {
        "version": getattr(fullseye, "__version__", "?"),
        "ops": names,
        "failed_backends": [list(x) for x in getattr(ops, "FAILED_BACKENDS", [])],
        "root_modules": _loaded_root_modules(),
        "py_modules_declared": sorted(declared),       # editable 側でのみ埋まる
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    print("%s: %d op / root modules %d / failed_backends %d"
          % (path, len(names), len(payload["root_modules"]), len(payload["failed_backends"])))
    return 0


def _compare(a_path: str, b_path: str) -> int:
    """editable(a)と wheel(b)を突き合わせる。

    ★op の**数**は比べない。wheel 側の venv に optional 依存(cv2 等)が無ければ
    その op は正当に居ないので、数の差は同梱漏れの証拠にならない
    (2026-09-05: 最初の版は 208 op の「消失」を報告したが、全部 cv2 不在だった)。
    見るのは、**環境に依らず成り立つ**次の 3 つ:

    1. editable が読み込んだ root モジュールのうち **py-modules に宣言されたもの**は、
       wheel でも読み込まれている(= 同梱され、import できた)
    2. wheel 側の ``FAILED_BACKENDS`` が空(backend が import/build で失敗していない)
    3. numpy/scipy だけで成立する族(``tb_*`` / ``hx_*``)が wheel に**床の数**だけ在る
       (``backends_typed`` が黙って [] を返す型の再発をここで止める)
    """
    a = json.load(open(a_path, encoding="utf-8"))
    b = json.load(open(b_path, encoding="utf-8"))
    problems = []
    declared = set(a.get("py_modules_declared") or [])
    ea, wb = set(a["root_modules"]), set(b["root_modules"])
    missing = sorted((ea & declared) - wb)
    if missing:
        problems.append("同梱のはずの root モジュールが wheel 側で読まれていない"
                        "(同梱漏れ、または上流 backend の失敗で読まれなかった): %s" % missing)
    if b["failed_backends"]:
        problems.append("wheel 側で backend が失敗: %s" % (b["failed_backends"],))
    wo = set(b["ops"])
    for prefix, floor in (("tb_", 100), ("hx_", 50)):
        n = len([x for x in wo if x.startswith(prefix)])
        if n < floor:
            problems.append("wheel の %s* が %d 本(床 %d) —— backend が黙って空を返している疑い"
                            % (prefix, n, floor))
    print("editable %d op / wheel %d op(数の差は optional 依存の有無で正当に生じる)"
          % (len(a["ops"]), len(wo)))
    if problems:
        for t in problems:
            print("NG:", t)
        return 1
    print("OK: 同梱漏れ・backend 失敗・族の空振りは無い")
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
