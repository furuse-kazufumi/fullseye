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

``--package-data WHEEL``(2026-11-13): git で追跡している ``fullseye/`` の実行時データ(.py 以外)と
wheel(zip)の中身を、**ファイルの側から**突き合わせる。列挙した物だけを数える門(目録・アイコン)は、
列挙から漏れた物に原理的に盲目 —— ``fullseye/data/TUNING_CARDS.json`` が 1.1.0 / 1.1.1 の wheel に無く、
MCP の ``fullseye_find_ops`` / ``fullseye_plan`` が毎回 -32603 で落ちていた(配布物の検証 S2)。
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
import tempfile
import warnings
import zipfile
from pathlib import Path

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
    # 「同梱しない」と決めた資産が wheel 側に在るか(package-data に書かなくても
    # VCS 探索で乗る —— 2026-09-07 に 42 MB が 2 日間乗っていた)
    unshipped_present = []
    try:
        import studio_assets                             # noqa: F401
        base = os.path.dirname(studio_assets.__file__)
        for d in ("sample_sources_ai",):
            if os.path.isdir(os.path.join(base, d)):
                unshipped_present.append("studio_assets/" + d)
    except Exception:                                  # noqa: BLE001
        pass
    # 2026-11-06: 同梱の目録(日本語・英語・中国語)が wheel に在るか。package-data の書き漏れは
    # checkout 側では見えない(fullseye/ に生成物が在るので)ので、配布物の側で数える。
    pkg_dir = os.path.dirname(fullseye.__file__)
    catalogs_missing = [n for n in ("OP_CATALOG.md", "OP_CATALOG.en.md", "OP_CATALOG.zh.md")
                        if not os.path.isfile(os.path.join(pkg_dir, n))]
    # 2026-11-12: Start メニューのアイコン(fullseye.ico / fullseye_256.png)が wheel に在るか。pyproject の文字列を
    # grep するだけの門は、package-data の書き方が効いているかを見ない。配布物の側で実在を数える。
    icons_missing = []
    try:
        import studio_assets                             # noqa: F401  (上の unshipped_present と同じ)
        sa_base = os.path.dirname(studio_assets.__file__)
        icons_missing = ["studio_assets/" + n for n in ("fullseye.ico", "fullseye_256.png")
                         if not os.path.isfile(os.path.join(sa_base, n))]
    except Exception:                                  # noqa: BLE001
        icons_missing = ["studio_assets/fullseye.ico", "studio_assets/fullseye_256.png"]
    payload = {
        "version": getattr(fullseye, "__version__", "?"),
        "catalogs_missing": catalogs_missing,
        "icons_missing": icons_missing,
        "unshipped_present": unshipped_present,
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
    a_path, b_path = _at_orig(a_path), _at_orig(b_path)
    for p in (a_path, b_path):
        if not os.path.exists(p):
            print("NG: 集計ファイルが無い: %s —— --dump が書けていない"
                  "(相対パスは %s 基準で解決している)" % (p, _ORIG_CWD))
            return 1
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
    # ★2026-09-08: editable 側も見る。それまで ``a["failed_backends"]`` は
    # **集めるだけで誰も読んでいなかった** —— 同じ回に examplefig の図の失敗と
    # 同じ型の穴として摘発した。editable の venv は optional 依存が**多い**ので、
    # 版の食い違いで backend が import に失敗しうる。そのとき wheel 側は
    # 「依存が無いから最初から居ない」だけで失敗を記録せず、この比較は緑のまま
    # 通ってしまう。落ちた backend の op はレジストリから黙って消える。
    if a.get("failed_backends"):
        problems.append("editable 側で backend が失敗(その族の op がレジストリから"
                        "黙って消えている): %s" % (a["failed_backends"],))
    if b.get("catalogs_missing"):
        problems.append("wheel に同梱の目録が無い: %s(pyproject の package-data を見る)"
                        % b["catalogs_missing"])
    if b.get("icons_missing"):
        problems.append("wheel に同梱のアイコンが無い: %s(Start メニューの .lnk が指す物。pyproject の package-data を見る)"
                        % b["icons_missing"])
    if b.get("unshipped_present"):
        problems.append("同梱しないはずの資産が wheel に乗っている: %s "
                        "(pyproject の exclude-package-data を見る)" % b["unshipped_present"])
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


# --------------------------------------------------------------------------- #
# 2026-11-13: git で追跡している fullseye/ の実行時データ と wheel の中身の突き合わせ
# --------------------------------------------------------------------------- #
#: 突き合わせる範囲: ``fullseye`` パッケージの下で git が追跡する **.py 以外**の全部
#: (data/*.json・OP_CATALOG*.md・SENSOR_PLAYBOOK.md・i18n/*.json・skill_template/ ……)。
#: .py は py-modules / packages の門(上の --dump / --compare と tests/test_packaging_subpackages.py)が見る。
PACKAGE_DATA_ROOT = "fullseye/"

#: git で追跡しているが**意図して**同梱しない ``fullseye/`` の下のファイルと、その理由。
#: 足すときは「wheel に入る .py が読まない」ことを確かめてから。同梱に変えたら、ここから消して
#: pyproject の package-data に足す。ここに在るのに git が追跡しなくなった物は NG(古い除外を残さない)。
NOT_SHIPPED = {
    "fullseye/data/gpu_required.json":
        "GPU 必須 op の正本名簿。読むのは tools/gpu_tier_rules.py と tools/gen_gpu_fill3_report.py(checkout の"
        "道具。imgevolve の索引づくりも tools/ を探して呼ぶ)だけで、wheel の実行時には読まない",
}

#: ソースから見つけた examples の実行時データのうち wheel に同梱する物。
EXAMPLE_SHIPPED = (
    "examples/data/ai_inspection_recipes_2026_11_08.json",
    "examples/data/ai_inspection_scores_2026_11_08.json",
    "examples/data/fintraffic_sun_2026_09_20.json",
    "examples/data/fp64_emulation_measured_2026_10_05.json",
    "examples/data/hokusai_great_wave_met_dp130155.png",
    "examples/data/ngs_geodetic_benchmarks_2026_09_22.json",
    "examples_3d/_gallery/showcase_turntable_pod.gif",
)

#: ソースから見つけたが同梱しない repo 直下データと理由。最上位 ``data`` パッケージは作らない。
EXAMPLE_NOT_SHIPPED = {
    "data/fileio_real":
        "1.5 MB の公開科学データ一式。最上位 data パッケージとの衝突を避け、checkout 専用にする",
    "data/itokawa_shape/gaskell_q64.npz":
        "checkout の重力 PoC 用形状。examples 配下への移動を伴うため同梱しない",
    "data/oct_real/paint_sdoct_cc_by.npz":
        "checkout の実測 OCT PoC 用。examples 配下への移動を伴うため同梱しない",
    "data/plateau_yokohama/venue_lod2.npz":
        "checkout の PLATEAU PoC 用。examples 配下への移動を伴うため同梱しない",
    "data/pmd_real/hammer_grid_cc0.npz":
        "checkout の PMD PoC 用。examples 配下への移動を伴うため同梱しない",
    "data/thin_film_real":
        "checkout の薄膜 PoC 2 本が共有する実測一式。examples 配下への移動を伴うため同梱しない",
    "data/thin_film_real/schwarz2024_micrograph_sio2_edge_640.jpg":
        "checkout の薄膜 PoC が直接読む実測画像。examples 配下への移動を伴うため同梱しない",
    "data/thin_film_real/schwarz2024_sio2_si_reflectance.csv":
        "checkout の薄膜 PoC が直接読む実測表。examples 配下への移動を伴うため同梱しない",
    "data/tum_rgbd_fr1_xyz":
        "3.9 MB の TUM RGB-D 一式。最上位 data パッケージとの衝突を避け、checkout 専用にする",
}


def _eval_example_path(node, names, source):
    """例の定数式を副作用なしで Path に畳む。/ Fold an example's constant path expression safely."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, int)):
        return node.value
    if isinstance(node, ast.Name):
        return source if node.id == "__file__" else names.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left = _eval_example_path(node.left, names, source)
        right = _eval_example_path(node.right, names, source)
        if isinstance(left, Path) and isinstance(right, (str, int)):
            return left / str(right)
    if isinstance(node, ast.Attribute):
        value = _eval_example_path(node.value, names, source)
        if node.attr == "parent" and isinstance(value, Path):
            return value.parent
    if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute)
            and node.value.attr == "parents"):
        value = _eval_example_path(node.value.value, names, source)
        index = _eval_example_path(node.slice, names, source)
        if isinstance(value, Path) and isinstance(index, int):
            return value.parents[index]
    if not isinstance(node, ast.Call):
        return None
    args = [_eval_example_path(arg, names, source) for arg in node.args]
    call = ast.unparse(node.func)
    if call in ("Path", "pathlib.Path") and args and isinstance(args[0], (str, Path)):
        return Path(args[0])
    if call.endswith(".resolve"):
        value = _eval_example_path(node.func.value, names, source)
        return value.resolve() if isinstance(value, Path) else None
    if call == "os.path.abspath" and args and isinstance(args[0], (str, Path)):
        return Path(args[0]).resolve()
    if call == "os.path.dirname" and args and isinstance(args[0], (str, Path)):
        return Path(args[0]).parent
    if (call == "os.path.join" and args and isinstance(args[0], (str, Path))
            and all(isinstance(arg, (str, int)) for arg in args[1:])):
        return Path(args[0]).joinpath(*(str(arg) for arg in args[1:]))
    return None


def _gallery_name_is_read(tree, name):
    """gallery の生成先ではなく、読取り呼出しへ渡す名前だけを選ぶ。/ Select gallery read inputs."""
    readers = {"open", "load", "imread", "read_bytes", "read_text"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or ast.unparse(node.func).rsplit(".", 1)[-1] not in readers:
            continue
        if any(isinstance(part, ast.Name) and part.id == name for arg in node.args for part in ast.walk(arg)):
            return True
    return False


def _example_runtime_paths(repo: str) -> dict:
    """examples のソースが指す実在データを ``path -> readers`` で返す。

    AST に見える定数式だけを辿るため、関数の引数を通じて渡されるパスは追跡しない。
    Discover existing runtime data referenced by constant expressions in examples. Paths passed
    through function parameters are intentionally not tracked because their runtime values are unknown.
    """
    root = Path(repo).resolve()
    data_roots = (root / "examples" / "data", root / "examples_3d" / "_gallery", root / "data")
    found = {}

    def record(value, source, tree, name=None):
        if not isinstance(value, Path):
            return
        path = value.resolve()
        inside = any(path == base or base in path.parents for base in data_roots)
        if not inside or not path.exists():
            return
        if name is not None and data_roots[1] in path.parents and not _gallery_name_is_read(tree, name):
            return
        rel = path.relative_to(root).as_posix()
        found.setdefault(rel, set()).add(source.relative_to(root).as_posix())

    def visit(node, names, source, tree):
        value = None
        targets = []
        if isinstance(node, ast.Assign):
            value, targets = _eval_example_path(node.value, names, source), node.targets
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            value, targets = _eval_example_path(node.value, names, source), [node.target]
        for target in targets:
            if not isinstance(target, ast.Name) or value is None:
                continue
            names[target.id] = value
            record(value, source, tree, target.id)

        if isinstance(node, ast.Call):
            reader = ast.unparse(node.func).rsplit(".", 1)[-1]
            if reader in {"open", "load", "imread", "read_bytes", "read_text"}:
                for arg in node.args:
                    record(_eval_example_path(arg, names, source), source, tree)
                if isinstance(node.func, ast.Attribute):
                    record(_eval_example_path(node.func.value, names, source), source, tree)

        for child in ast.iter_child_nodes(node):
            child_names = dict(names) if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) else names
            visit(child, child_names, source, tree)

    sources = sorted((root / "examples").rglob("*.py")) + sorted((root / "examples_3d").rglob("*.py"))
    for source in sources:
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        visit(tree, {}, source, tree)
    return {path: tuple(sorted(readers)) for path, readers in sorted(found.items())}


def _tracked_package_files(repo: str) -> list:
    """``git ls-files`` が追跡する ``fullseye/`` の下の .py 以外のファイル(repo 相対・``/`` 区切り)。

    git が使えなければ ``OSError`` / ``subprocess.SubprocessError`` をそのまま上げる(呼ぶ側が NG にする)。
    """
    out = subprocess.run(["git", "-C", repo, "ls-files", "-z", "--", PACKAGE_DATA_ROOT.rstrip("/")],
                         capture_output=True, check=True, timeout=300).stdout
    names = [p for p in out.decode("utf-8", "surrogateescape").split("\0") if p]
    return sorted(p for p in names if not p.endswith((".py", ".pyc")) and "/__pycache__/" not in p)


def _package_data(wheel: str, repo: str = "") -> int:
    """wheel(zip)に、git で追跡している ``fullseye/`` の実行時データが**中身ごと**入っているか。

    NG にするもの: 追跡しているのに wheel に無い / wheel の中で 0 バイト / 追跡が 0 件(門が空を通す)/
    :data:`NOT_SHIPPED` に挙げたのに追跡されていない(古い除外)/ wheel を開けない / git が使えない。
    判定は全部 NG の 1 行(traceback で死ぬ門は「門が壊れた」のか「落ちた」のかを区別できない)。
    """
    repo = repo or os.path.dirname(_HERE)
    wheel = _at_orig(wheel)
    try:
        tracked = _tracked_package_files(repo)
    except (OSError, subprocess.SubprocessError) as e:
        print("NG: git ls-files で %s の追跡ファイルを数えられない(%s: %s)—— checkout の tools/ から走らせる"
              % (PACKAGE_DATA_ROOT, type(e).__name__, e))
        return 1
    try:
        example_runtime = _example_runtime_paths(repo)
    except (OSError, SyntaxError, ValueError) as e:
        print("NG: examples のソースから実行時データを数えられない(%s: %s)" % (type(e).__name__, e))
        return 1
    classified = set(EXAMPLE_SHIPPED) | set(EXAMPLE_NOT_SHIPPED)
    unclassified = sorted(set(example_runtime) - classified)
    stale_examples = sorted(classified - set(example_runtime))
    if not tracked:
        print("NG: git が追跡する %s の .py 以外のファイルが 0 件 —— 門が空を通している(repo=%s)"
              % (PACKAGE_DATA_ROOT, repo))
        return 1
    try:
        with zipfile.ZipFile(wheel) as zf:
            sizes = {i.filename: i.file_size for i in zf.infolist()}
    except (OSError, zipfile.BadZipFile) as e:
        print("NG: wheel を開けない: %s(%s: %s)" % (wheel, type(e).__name__, e))
        return 1
    want = [p for p in tracked if p not in NOT_SHIPPED]
    missing = [p for p in want if p not in sizes]
    empty = [p for p in want if sizes.get(p) == 0]
    stale = sorted(p for p in NOT_SHIPPED if p not in tracked)
    problems = []
    if missing:
        problems.append("git で追跡している実行時データが wheel に無い(pyproject の [tool.setuptools.package-data] の "
                        "\"fullseye\" に足す。同梱しないなら理由を NOT_SHIPPED に書く): %s" % missing)
    if empty:
        problems.append("wheel の中で 0 バイト: %s" % empty)
    if stale:
        problems.append("NOT_SHIPPED に挙げたのに git が追跡していない(除外を消す): %s" % stale)
    example_missing = [p for p in EXAMPLE_SHIPPED if p not in sizes]
    example_empty = [p for p in EXAMPLE_SHIPPED if sizes.get(p) == 0]
    if unclassified:
        problems.append("examples のソースが読むが同梱/非同梱の表に無いデータ: %s" % unclassified)
    if stale_examples:
        problems.append("examples のソースから見つからない古い同梱/非同梱の表: %s" % stale_examples)
    if example_missing:
        problems.append("wheel の examples が実行時に読むデータが無い: %s" % example_missing)
    if example_empty:
        problems.append("wheel の examples 実行時データが 0 バイト: %s" % example_empty)
    print("%s: git が追跡する %s の .py 以外 %d 件(意図して同梱しない %d 件)/ そのうち wheel に在る %d 件"
          % (os.path.basename(wheel), PACKAGE_DATA_ROOT, len(tracked), len(tracked) - len(want),
             len(want) - len(missing)))
    print("examples のソースから見つけた実行時データ: %d 件(同梱 %d / 非同梱 %d)、wheel 内 %d / %d 件" %
          (len(example_runtime), len(EXAMPLE_SHIPPED), len(EXAMPLE_NOT_SHIPPED),
           len(EXAMPLE_SHIPPED) - len(example_missing), len(EXAMPLE_SHIPPED)))
    if problems:
        for t in problems:
            print("NG:", t)
        return 1
    print("OK: 追跡している実行時データは全部 wheel に中身ごと入っている")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dump", metavar="OUT")
    ap.add_argument("--compare", nargs=2, metavar=("EDITABLE", "WHEEL"))
    ap.add_argument("--package-data", metavar="WHEEL",
                    help="wheel (.whl) に git で追跡している fullseye/ の実行時データが入っているか")
    ns = ap.parse_args(argv)
    if ns.dump:
        return _dump(ns.dump)
    if ns.compare:
        return _compare(*ns.compare)
    if ns.package_data:
        return _package_data(ns.package_data)
    ap.error("--dump / --compare / --package-data のどれかが要る")


if __name__ == "__main__":
    sys.exit(main())
