"""PR の CI で回すテストを、変更されたファイルから**機械で**選ぶ(2026-11-10)。

なぜ要るか
----------
テストは 26,627 件・合計約 4.7 時間(``.test_durations``)。6 片に分けても PR 1 本で
1〜2 時間かかり、無料の runner の同時枠を PR と master で奪い合っていた。

方式(import の依存グラフ + 文字列のパス参照、状態を持たない)
--------------------------------------------------------------
1. repo の ``*.py`` を AST で読み、``import`` / ``from .. import`` /
   ``importlib.import_module("x")`` / ``__import__("x")`` の**字面の名前**で依存の辺を張る。
   ``ops.py`` が backend を名前の並び(``"backends_auto", ...``)で ``__import__`` する
   ので、``ops.py`` の中の ``"backends*"`` の字面も辺にする。
2. 各ファイルの**パスらしい文字列**を集め、「そのファイルが読む物」とみなす
   (``ROOT / "docs" / "X.md"`` / ``os.path.join(ROOT, "docs", "X.md")`` は ``docs/X.md`` に畳む。
   途中に字面でない引数が来たら型にする: ``ROOT / "examples" / (name + ".py")`` -> ``examples/*.py``。
   ``glob`` の型は ``fnmatch`` で照合。畳めない単語だけの字面は repo 直下の同名だけに当てる)。
3. ``subprocess`` などで**走らせる**ファイルが ``*.py`` を名指していれば、その台本の import の
   閉包も依存に入れる(実行の辺)。PoC / 例の門(``SCRIPT_RUNNERS``)は、変更が台本の側にしか
   効かないとき**その台本のパラメータだけ**を選ぶ。
4. テストファイル T の依存 = T から辺で届く全ファイル ∪ それらが参照する全パス。
   変更されたファイル F が T の依存に入っていれば T を選ぶ。

**迷ったら全部回す(fail-safe)**。次のどれかなら full suite:

* 共有の中核(``CORE_PATTERNS``: ops.py・backends.py・backend_safe.py・api.py・
  fullseye/__init__.py・conftest・CI の設定・依存の定義・生成物の仕組み・この道具)を触った
* どのテストも名指しで依存しないファイルを触った(対応が分からない。repo 全体を舐める型
  ``**/*`` でだけ当たるのは「対応あり」に数えない)/ 消したファイルを誰も参照していない
* 変更が多すぎる(``MAX_CHANGED``)/ ``.py`` が構文エラーで読めない / git の差分が取れない
* 依存の版が最後の全数の run と違う / 比べられない(``tools/ci_deps_drift.py``。diff と
  無関係な失敗 = #271 の threadpoolctl 3.8.0 は、変更から辿る判定では原理的に選べない)
* 判定そのものが例外で落ちた

repo 全体を見る門(``tools/ci_always_run.txt``: 台帳・生成物・負債の門)は、判定にかかわらず**必ず**回す。

ライブラリ(repo 直下・fullseye/・examples/)の**広い**参照(``"docs"`` だけ・``ROOT / "examples"``)は
数えない(``ops.py`` が全 backend を import するので、数えると docs のどの変更でも 93 % が選ばれる)。
門の側(``tests/`` と ``tools/``)の参照は広くても全部数える。

選ばなかったテストは master への push と毎日の schedule で全部回る
(CONTRIBUTING.md の「CI: which tests run where」)。PR の段で回す範囲を変えるだけで、
門・閾値・台帳は 1 つも緩めない。

片分け(``shard_plan``)と、pytest の側で一覧を読む入口(``plan_session``、``tests/conftest.py``
が呼ぶ)もここに置く。片は**ファイル単位**(module / session fixture を片ごとに作り直さない)。

使い方
------
    python tools/ci_select_tests.py --base origin/master            # 変更を git から
    python tools/ci_select_tests.py --files a.py docs/x.md          # 変更を直接
    python tools/ci_select_tests.py --base origin/master --github-output "$GITHUB_OUTPUT"
    python tools/ci_select_tests.py --early-list ci_early_tests.txt # 先頭のジョブで先に回すファイル
    python tools/ci_select_tests.py --freshness-forecast collected.txt --nshards 6

出力(``--json``)は ``{"mode": "full"|"selected", "reasons": [...], "tests": [...],
"seconds": 推定秒, "shards": 片の数}``。

先頭のジョブ(``gates``、片と並行)で先に回す一覧もここから出す(``early_plan``): 門の全部と、失敗の
実績(``tools/ci_failure_history.json``)で 2 本以上のブランチで落ちたファイルを、落ちた run の数の順に、
記録時間の合計 ``EARLY_BUDGET_SECONDS`` まで。**片からは何も外さない**(先頭のジョブは「先にも回す」)。
鮮度の門は session で答えが変わるので pytest に渡さず、片と同じ session を作って門の本体を呼ぶ
(``freshness_forecast``)。
"""
from __future__ import annotations

import argparse
import ast
import fnmatch
import importlib.util
import json
import math
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]

#: 触ったら full suite にするファイル(``fnmatch``、repo 相対・``/`` 区切り)。
#: ★足すのは自由、外すときは「全テストに効かない」根拠を書くこと。
CORE_PATTERNS: tuple[str, ...] = (
    # op の登録と実行の中核(全 op・全テストが通る)
    "ops.py", "backends.py", "backend_safe.py", "api.py", "fslib.py",
    "normalized_threshold.py", "fullseye/__init__.py", "fullseye/__main__.py",
    # テストの土台・pytest の設定
    "conftest.py", "tests/conftest.py", "tests/__init__.py", "pytest.ini", "setup.cfg", "tox.ini",
    # 依存の定義・配布物
    "pyproject.toml", "setup.py", "requirements*.txt", "MANIFEST.in", "constraints*.txt",
    # CI の設定と、この判定の道具そのもの
    ".github/*", "tools/ci_select_tests.py", "tools/ci_always_run.txt",
    # 生成物の仕組み(regen_all が全部を作り直す)
    "tools/regen_all.py",
)

#: 触っても**テストの対象にならない**ファイル(``.test_durations`` は片分けの入力で、
#: 鮮度の門 ``test_test_durations_is_fresh`` は ALWAYS_RUN で必ず回る)。
INERT_PATTERNS: tuple[str, ...] = (
    ".test_durations",
)

#: 変更ファイルがこれより多ければ、依存を辿らずに full suite(大きな統合 PR)。
MAX_CHANGED = 1500

#: 1 片の目安(秒)。選んだテストの推定合計をこれで割って片の数を決める(上限 6)。
TARGET_SHARD_SECONDS = 15 * 60
MAX_SHARDS = 6

#: 解析から外すディレクトリ(.py を含まない/テストから import されない)。
_SKIP_DIRS = {".git", "__pycache__", "node_modules", "rust", "target", ".venv", "venv",
              ".wheelenv", "dist", "build", "dist_check"}
#: 1 段だけで import できる場所(テストが sys.path に足す: repo 直下・tools・examples …)。
_FLAT_DIRS = ("", "tools", "examples", "examples_3d", "tests", "spikes", "studio_lite")


def _rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def _matches_any(path: str, patterns) -> bool:
    return any(fnmatch.fnmatchcase(path, pat) for pat in patterns)


# --------------------------------------------------------------------------- #
# 1 ファイルの解析                                                            #
# --------------------------------------------------------------------------- #
def _const_str(node) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _tail_pattern(node) -> str:
    """字面でない尾の型: ``name + ".py"`` / ``f"{x}.json"`` なら ``*.py`` / ``*.json``、他は ``*``。"""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        s = _const_str(node.right)
        if s and re.fullmatch(r"\.[A-Za-z0-9_]{1,8}", s):
            return "*" + s
    if isinstance(node, ast.JoinedStr) and node.values:
        s = _const_str(node.values[-1])
        if s and re.fullmatch(r"[\w\-.]*\.[A-Za-z0-9_]{1,8}", s):
            return "*" + s
    return "*"


def _fold_path(node, consumed: set) -> str | None:
    """``ROOT / "a" / "b"`` / ``os.path.join(X, "a", "b")`` の字面の尾を ``a/b`` に畳む。

    途中に字面でない引数が来たら、そこから先は型(``*`` / ``*.py``)にする
    (``ROOT / "examples" / (name + ".py")`` -> ``examples/*.py``)。
    """
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        consumed.add(id(node))                    # 内側の部分式を、あとで別の参照として数えない
        left = _fold_path(node.left, consumed)
        if left is None and _const_str(node.left) is not None:
            consumed.add(id(node.left))
            left = _const_str(node.left)
        right = _const_str(node.right)
        if right is not None:
            consumed.add(id(node.right))
        elif left:
            right = _tail_pattern(node.right)
        else:
            return None
        return (left.rstrip("/") + "/" + right.lstrip("/")) if left else right
    if isinstance(node, ast.Call):
        fn = node.func
        name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
        if name in ("join", "joinpath", "Path", "PurePath", "PosixPath", "WindowsPath"):
            consumed.add(id(node))
            parts: list[str] = []
            if isinstance(fn, ast.Attribute) and name == "joinpath":
                base = _fold_path(fn.value, consumed)
                if base:
                    parts.append(base)
            for a in node.args:
                s = _const_str(a)
                if s is not None:
                    consumed.add(id(a))
                    parts.append(s)
                    continue
                sub = _fold_path(a, consumed)
                if sub:
                    parts.append(sub)
                elif parts:
                    parts.append(_tail_pattern(a))      # 字面でない途中の引数: 型にして止める
                    break
            return "/".join(p.strip("/") for p in parts if p.strip("/")) or None
    return None


def _path_like(s: str) -> bool:
    if not s or len(s) > 240 or "\n" in s or " " in s.strip():
        return False
    if any(c in s for c in "*?["):
        return "/" in s or "." in s
    return "/" in s or "\\" in s or bool(re.search(r"\.[A-Za-z0-9]{1,6}$", s)) or bool(
        re.fullmatch(r"[A-Za-z0-9_\-]+", s))


def analyse_source(src: str, rel: str) -> tuple[set[str], set[str]]:
    """(import した名前, パスらしい参照) を返す。

    参照の書き方は 3 種類(``ref_matches`` が読む):

    * ``a/b.json`` のようなパス -> 変更パスの中の**連続する成分**として一致すれば当たり
    * ``examples/*.py`` のような型 -> ``fnmatch``(``*`` は ``/`` もまたぐ)
    * ``~examples`` -> 畳めなかった**単語だけ**の字面。repo 直下のその名前のディレクトリ/ファイルだけに当てる
      (``"name"`` や ``"ops"`` のような普通の単語が、深いところの同名ディレクトリを全部引くのを避ける)
    """
    tree = ast.parse(src)
    imports: set[str] = set()
    refs: set[str] = set()
    consumed: set[int] = set()
    pkg = rel.rsplit("/", 1)[0].replace("/", ".") if "/" in rel else ""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                imports.add(node.module)
                imports.update(node.module + "." + a.name for a in node.names)
            elif node.level > 0:
                base = pkg
                for _ in range(node.level - 1):
                    base = base.rpartition(".")[0]
                mod = ".".join(x for x in (base, node.module or "") if x)
                if mod:
                    imports.add(mod)
                    imports.update(mod + "." + a.name for a in node.names)
                else:
                    imports.update(a.name for a in node.names)
        elif isinstance(node, ast.Call):
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
            if name in ("import_module", "__import__") and node.args:
                s = _const_str(node.args[0])
                if s:
                    imports.add(s)
            if name in ("glob", "rglob", "iglob") and isinstance(fn, ast.Attribute) and node.args:
                pat = _const_str(node.args[0])
                base = _fold_path(fn.value, consumed)
                if base and base.endswith("/*"):
                    base = base[:-2]
                if pat is not None:
                    consumed.add(id(node.args[0]))
                    refs.add(((base + "/") if base else "") + ("**/" if name == "rglob" else "") + pat)
                elif base:
                    refs.add(base + "/*")
            if id(node) not in consumed:
                folded = _fold_path(node, consumed)
                if folded:
                    refs.add(folded)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div) and id(node) not in consumed:
            folded = _fold_path(node, consumed)
            if folded:
                refs.add(folded)
        elif isinstance(node, ast.JoinedStr):
            for v in node.values:
                s = _const_str(v)
                if s is not None:
                    consumed.add(id(v))
                    for piece in re.split(r"[\s{}]+", s):
                        piece = piece.strip("/\\")
                        if piece and _path_like(piece) and not re.fullmatch(r"[A-Za-z0-9_\-]+", piece):
                            refs.add(piece)
    for node in ast.walk(tree):
        s = _const_str(node)
        if s is not None and id(node) not in consumed and _path_like(s):
            s = s.replace("\\", "/").strip().strip("/")
            refs.add(("~" + s) if re.fullmatch(r"[A-Za-z0-9_\-]+", s) else s)
    norm = set()
    for r in refs:
        tilde = r.startswith("~")
        parts = [p for p in r.lstrip("~").replace("\\", "/").strip().split("/") if p not in ("", ".", "..")]
        r = ("~" if tilde else "") + "/".join(parts)
        if parts and r not in ("*", "**", "**/*"):
            norm.add(r)
    return imports, norm


# --------------------------------------------------------------------------- #
# repo 全体の索引                                                             #
# --------------------------------------------------------------------------- #
#: ソースにこれがあれば「参照した .py を**実行する**」とみなす(PoC を subprocess で走らせる門など)。
#: 実行するなら、参照先の import の閉包まで依存に入る(読むだけなら参照先のファイルだけ)。
_EXEC_MARKERS = ("subprocess", "runpy", "spec_from_file_location", "exec(", "os.system",
                 "Popen", "import_module(", "run_path(")

#: 「1 本ずつ別の PoC / 例を走らせる」門。変更が台本(とその依存)にしか効かないなら、
#: ファイル全体ではなく**その台本のパラメータだけ**を選ぶ(どちらの門も、session fixture が
#: このセッションに残ったパラメータの台本だけを走らせる作り)。
#: テストファイル -> (テスト関数名, 台本のディレクトリ, 台本の名前の型)
SCRIPT_RUNNERS: dict[str, tuple[str, str, str]] = {
    "tests/test_poc_scripts_run.py": ("test_the_poc_runs_clean", "examples", "poc_*.py"),
    "tests/test_example_scripts_run.py": ("test_the_example_runs_from_a_bare_checkout", "examples", "*.py"),
}


def _component_runs(path: str) -> list[str]:
    """``a/b/c`` -> 連続する成分の並び全部(``a``, ``a/b``, ``b/c``, ``c`` …)。"""
    parts = path.split("/")
    return ["/".join(parts[i:j]) for i in range(len(parts)) for j in range(i + 1, len(parts) + 1)]


#: 門の側(ディレクトリごと読む・走らせるのが仕事)。ここのファイルの参照は、広くても全部数える。
_GATE_DIRS = ("tests/", "tools/")


def _literal_parts(ref: str) -> list[str]:
    """参照の成分のうち、型(``*`` など)でない字面のもの。"""
    return [c for c in ref.lstrip("~").split("/") if c and not _is_glob(c)]


def _is_broad(ref: str) -> bool:
    """ディレクトリ丸ごとを指す参照か(単語だけ・ファイル名の無いパス・``dir/*`` / ``*.py`` の型)。"""
    if ref.startswith("~"):
        return True
    last = ref.rsplit("/", 1)[-1]
    if _is_glob(ref):
        return re.fullmatch(r"\*+(\.[A-Za-z0-9_]+)?", last) is not None
    return "." not in last


def _is_universal(ref: str) -> bool:
    """repo 全体を舐める型(``**/*`` / ``*.py`` / ``*/*.md``)か。名前の手がかりが何も無い型。"""
    return _is_glob(ref) and re.fullmatch(r"(\*\*?/)*\*+(\.[A-Za-z0-9_]+)?", ref) is not None


def _is_glob(ref: str) -> bool:
    return any(c in ref for c in "*?[")


def ref_matches(ref: str, path: str) -> bool:
    """参照 *ref* が変更パス *path* を指しうるか(迷ったら True)。書き方は ``analyse_source``。"""
    if ref.startswith("~"):
        word = ref[1:]
        return path == word or path.startswith(word + "/")
    if _is_glob(ref):
        base = path.rsplit("/", 1)[-1]
        # ``**/`` は 0 段のディレクトリにも当てる(``ROOT.rglob("*.py")`` は repo 直下の .py も読む。
        # 2026-11-10 の独立レビュー: ``**/*.py`` が直下の ``opsfileio.py`` に当たっていなかった)。
        pats = {ref, ref.replace("/**/", "/")}
        while True:
            more = {x[3:] for x in pats if x.startswith("**/")} - pats
            if not more:
                break
            pats |= more
        return any(fnmatch.fnmatchcase(path, x) or fnmatch.fnmatchcase(base, x)
                   or fnmatch.fnmatchcase(path, "*/" + x) for x in pats)
    return ("/" + ref + "/") in ("/" + path + "/")


_WALK_FUNCS = {"walk", "listdir", "scandir"}          # os.walk / os.listdir / os.scandir(target)
_WALK_METHODS = {"rglob", "iterdir"}                    # target.rglob(...) / target.iterdir()


def walks_repo(src: str) -> bool:
    """テストが **repo 全体**(特定の下位ディレクトリでなく)を走査するか。

    ★2026-11-10(独立レビュー): ``os.walk(ROOT)`` / ``ROOT.rglob("*.py")`` / ``git ls-files`` で repo の
    全ファイルを読む門は、どのファイルの変更でも落ちうる(ベンダ名・不正なエスケープ・迷子の画像)。
    依存の判定では拾い切れなかった(``opsfileio.py`` の改変で 7 本中 6 本が選ばれなかった)ので、
    機械で見つけて毎回回す。走査の起点が**字面の下位ディレクトリ**(``ROOT / "docs"`` など、
    モジュールの先頭で代入した名前も辿る)なら repo 全体ではない。起点が読めなければ repo 全体とみなす。
    """
    if "ls-files" in src:
        return True
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return True
    named: dict[str, str | None] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            named[node.targets[0].id] = _fold_path(node.value, set())

    def subdir(expr) -> bool:
        if isinstance(expr, ast.Name) and expr.id.startswith(("tmp", "tempdir")):
            return True                                   # pytest の tmp_path / tmpdir(repo の外)
        if isinstance(expr, ast.Name):
            folded = named.get(expr.id)
        else:
            folded = _fold_path(expr, set())
        return bool(folded) and len(_literal_parts(folded)) >= 1

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
        if name in _WALK_FUNCS and isinstance(fn, ast.Attribute) and getattr(fn.value, "id", "") == "os":
            if node.args and not subdir(node.args[0]):
                return True
        elif name in _WALK_METHODS and isinstance(fn, ast.Attribute):
            if not subdir(fn.value):
                return True
        elif name == "glob" and isinstance(fn, ast.Attribute) and node.args:
            pat = _const_str(node.args[0])
            if getattr(fn.value, "id", "") == "glob":           # glob.glob(join(X, "**", ...))
                folded = _fold_path(node.args[0], set()) or pat or ""
                if "**" in folded and not _literal_parts(folded.split("**", 1)[0]):
                    return True
            elif pat and "**" in pat and not subdir(fn.value):  # X.glob("**/...")
                return True
        elif name == "iglob" and node.args:
            folded = _fold_path(node.args[0], set()) or _const_str(node.args[0]) or ""
            if "**" in folded and not _literal_parts(folded.split("**", 1)[0]):
                return True
    return False


class Index:
    """repo の .py の import の辺・実行の辺と、パスらしい参照の索引。"""

    def __init__(self, root: Path = ROOT):
        self.root = root
        self.files: list[str] = []
        for dp, dn, fn in os.walk(root):
            dn[:] = sorted(d for d in dn if d not in _SKIP_DIRS and not d.startswith("."))
            for f in sorted(fn):
                if f.endswith(".py"):
                    self.files.append(Path(dp, f).relative_to(root).as_posix())
        self.file_set = set(self.files)
        self.mod2file: dict[str, str] = {}
        self.flat: dict[str, list[str]] = defaultdict(list)
        for f in self.files:
            parts = f[:-3].split("/")
            if parts[-1] == "__init__":
                parts = parts[:-1]
            if parts:
                self.mod2file.setdefault(".".join(parts), f)
            d = "/".join(f.split("/")[:-1])
            if d in _FLAT_DIRS:
                self.flat[f.split("/")[-1][:-3]].append(f)
        # .py の「連続する成分の並び」-> ファイル(参照から .py を引く逆引き)
        self._py_by_run: dict[str, set[str]] = defaultdict(set)
        for f in self.files:
            for run in _component_runs(f):
                self._py_by_run[run].add(f)
        self.imports: dict[str, set[str]] = {}
        self.refs: dict[str, set[str]] = {}
        self.executes: set[str] = set()
        self.unparsable: list[str] = []
        #: repo 全体を走査するテスト(``walks_repo``)。判定にかかわらず毎回回す。
        self.repo_walkers: set[str] = set()
        for f in self.files:
            try:
                src = (root / f).read_text(encoding="utf-8", errors="replace")
                imports, refs = analyse_source(src, f)
            except SyntaxError:
                self.unparsable.append(f)
                src, imports, refs = "", set(), set()
            words = {r[1:] for r in refs if r.startswith("~")}
            if re.fullmatch(r"tests/test_[^/]*\.py", f) and src and walks_repo(src):
                self.repo_walkers.add(f)
            if not f.startswith(_GATE_DIRS):
                # ★ライブラリ(repo 直下・fullseye/・examples/ …)の**広い**参照は数えない。
                #   ops.py が全 backend を import するので、ライブラリの閉包はほぼ全部のテストに入る。
                #   そこで ``"docs"`` や ``ROOT / "examples"`` のような 1 か所の広い参照を数えると、
                #   docs・examples のどの変更でもほぼ全部が選ばれて、判定が意味を失う(実測 93 %)。
                #   ファイルを名指しする参照(``data/macro_champions.json`` など)は数える。
                #   ここで落ちた依存は master と毎日の full suite が拾う。どのテストも名指ししない
                #   ファイルを触った PR は「対応が分からない」で full になる。
                #   ★2026-11-10(独立レビュー): ``data/auto_specs`` / ``docs/ops`` のように**字面が 2 段以上**
                #   あるディレクトリの参照は数える(backends_auto が data/auto_specs/*.json を読み込んで
                #   op を登録するのに、捨てていたので auto_specs の変更が 93 本しか選ばなかった)。
                #   捨てるのは字面が 1 段以下(``"docs"`` / ``ROOT / "examples"`` / ``*.md``)だけ。
                refs = {r for r in refs if not (_is_broad(r) and len(_literal_parts(r)) <= 1)}
            self.refs[f] = refs
            deps = {r for n in imports for r in self._resolve(n, f) if r != f}
            # ★文字列で引くレジストリ(``opassist.py`` の ``("opsfileio", "OPSFILEIO")`` など)。
            #   repo 直下のモジュール名と同じ字面の単語は、そのモジュールへの辺にする(多めに選ぶ側)。
            for w in words:
                tgt = self.mod2file.get(w)
                if tgt and "/" not in tgt and tgt != f:
                    deps.add(tgt)
            if f == "ops.py":                       # 名前の並びで __import__ する backend
                for m in re.findall(r'"(backends(?:_\w+)?)"', src):
                    if m + ".py" in self.file_set:
                        deps.add(m + ".py")
            self.imports[f] = deps
            if any(m in src for m in _EXEC_MARKERS):
                self.executes.add(f)
        # 実行の辺: 実行する印のあるファイル -> 参照が指す .py
        self.exec_edges: dict[str, set[str]] = {f: self.py_matching(self.refs[f]) - {f}
                                                for f in self.executes}
        self.deps: dict[str, set[str]] = {f: self.imports[f] | self.exec_edges.get(f, set())
                                          for f in self.files}

    def py_matching(self, refs) -> set[str]:
        """参照が指す .py(型か ``.py`` で終わるパスだけ。単語やディレクトリだけの参照は辺にしない)。"""
        out: set[str] = set()
        for r in refs:
            if r.startswith("~"):
                continue
            if _is_glob(r):
                # 走らせる対象として名指しできる型だけ(``examples/*.py``・``poc_*.py``)。
                # ``*.py`` / ``**/*`` のような repo 全体の型は「読む」側(参照の一致で数える)。
                if r.endswith(".py") and re.search(r"[A-Za-z0-9_]", r[:-3]):
                    out.update(f for f in self.files if ref_matches(r, f))
            elif r.endswith(".py"):
                out.update(self._py_by_run.get(r, ()))
        return out

    def _resolve(self, name: str, here: str) -> list[str]:
        out = []
        n = name
        while n:
            if n in self.mod2file:
                out.append(self.mod2file[n])
                head = n.split(".")[0]                   # パッケージの __init__ も通る
                if head in self.mod2file and self.mod2file[head] not in out:
                    out.append(self.mod2file[head])
                return out
            n = n.rpartition(".")[0]
        head = name.split(".")[0]
        hd = here.rsplit("/", 1)[0] if "/" in here else ""
        same = (hd + "/" if hd else "") + head + ".py"
        if same in self.file_set:
            return [same]
        return list(self.flat.get(head, ()))

    def closure(self, start, *, skip_edges: dict | None = None) -> frozenset:
        """*start*(ファイル名か、その集合)から依存の辺で届く全ファイル。"""
        seen = set([start] if isinstance(start, str) else start)
        stack = list(seen)
        while stack:
            x = stack.pop()
            nxt = self.deps.get(x, ())
            if skip_edges and x in skip_edges:
                nxt = set(nxt) - skip_edges[x]
            for y in nxt:
                if y not in seen:
                    seen.add(y)
                    stack.append(y)
        return frozenset(seen)

    def test_files(self) -> list[str]:
        return [f for f in self.files if re.fullmatch(r"tests/test_[^/]*\.py", f)]


class _Deps:
    """ファイルの集合と、それらの参照から「変更パス -> 当たるか」を速く引く形。"""

    def __init__(self, index: Index, files: frozenset, drop_refs=None):
        self.files = files
        refs: set[str] = set()
        for f in files:
            refs |= index.refs.get(f, set())
        if drop_refs:
            refs = {r for r in refs if not drop_refs(r)}
        self.top = {r[1:] for r in refs if r.startswith("~")}
        self.plain = {r for r in refs if not _is_glob(r) and not r.startswith("~")}
        self.globs = [r for r in refs if _is_glob(r) and not r.startswith("~") and not _is_universal(r)]
        self.universal = [r for r in refs if _is_universal(r) and not r.startswith("~")]

    def hits(self, path: str) -> int:
        """2 = 名指しで当たる / 1 = repo 全体を舐める型でだけ当たる / 0 = 当たらない。

        1 は「選ぶ」には数えるが、「このファイルに対応するテストがある」には数えない
        (``**/*`` を舐める門が 1 本あるだけで、どのファイルも「対応あり」になって
        対応の分からないファイルの fail-safe が働かなくなるのを防ぐ)。
        """
        if path in self.files:
            return 2
        if any(run in self.plain for run in _component_runs(path)):
            return 2
        parts = path.split("/")
        if any("/".join(parts[:i]) in self.top for i in range(1, len(parts) + 1)):
            return 2
        if any(ref_matches(g, path) for g in self.globs):
            return 2
        return 1 if any(ref_matches(g, path) for g in self.universal) else 0


class Selector:
    def __init__(self, index: Index, always: list[str]):
        self.ix = index
        self.explicit_always = list(always)
        self.always = sorted(set(always) | index.repo_walkers)
        self.tests = index.test_files()
        self.deps: dict[str, _Deps] = {}
        self.runner_own: dict[str, _Deps] = {}
        self.runner_scripts: dict[str, dict[str, _Deps]] = {}
        for t in self.tests:
            self.deps[t] = _Deps(index, index.closure(t))
            if t in SCRIPT_RUNNERS:
                _func, sdir, pat = SCRIPT_RUNNERS[t]
                scripts = sorted(f for f in index.files
                                 if f.startswith(sdir + "/") and f.count("/") == sdir.count("/") + 1
                                 and fnmatch.fnmatchcase(f.rsplit("/", 1)[-1], pat))
                # 門そのものの依存(台本へ向かう実行の辺と、台本のディレクトリを指す参照は除く)
                own = index.closure(t, skip_edges={t: set(scripts)})
                in_dir = (lambda r, d=sdir: r.lstrip("~") == d or r.startswith(d + "/")
                          or (_is_glob(r) and fnmatch.fnmatchcase(d + "/x.py", r)))
                self.runner_own[t] = _Deps(index, own, drop_refs=in_dir)
                self.runner_scripts[t] = {s: _Deps(index, index.closure(s)) for s in scripts}

    def tests_for(self, path: str) -> set[str]:
        return {t for t in self.tests if self.deps[t].hits(path)}

    def is_mapped(self, path: str) -> bool:
        """名指しで依存するテストが 1 本でもあるか(repo 全体を舐める型だけなら False)。"""
        return any(self.deps[t].hits(path) == 2 for t in self.tests)

    def nodes_for(self, path: str) -> tuple[set[str], set[str]]:
        """(ファイルごと選ぶテスト, パラメータだけ選ぶノード id)。"""
        whole, nodes = set(), set()
        for t in self.tests_for(path):
            if t in SCRIPT_RUNNERS and not self.runner_own[t].hits(path):
                func = SCRIPT_RUNNERS[t][0]
                picked = [s for s, d in self.runner_scripts[t].items() if d.hits(path)]
                if picked:
                    nodes.update("%s::%s[%s]" % (t, func, s.rsplit("/", 1)[-1]) for s in picked)
                    continue
            whole.add(t)
        return whole, nodes

    def select(self, changed: list[str]) -> dict:
        reasons: list[str] = []
        changed = sorted({c.replace("\\", "/") for c in changed if c})
        if not changed:
            return {"mode": "full", "reasons": ["no changed files (cannot tell what changed)"]}
        if len(changed) > MAX_CHANGED:
            return {"mode": "full", "reasons": ["%d changed files > %d" % (len(changed), MAX_CHANGED)]}
        core = [c for c in changed if _matches_any(c, CORE_PATTERNS)]
        if core:
            return {"mode": "full", "reasons": ["core file changed: " + ", ".join(core[:10])]}
        bad = [c for c in changed if c in self.ix.unparsable]
        if bad:
            return {"mode": "full", "reasons": ["unparsable python: " + ", ".join(bad[:10])]}
        whole: set[str] = set()
        nodes: set[str] = set()
        per_file: dict[str, list[str]] = {}
        unknown: list[str] = []
        for c in changed:
            if _matches_any(c, INERT_PATTERNS):
                per_file[c] = []
                continue
            exists = (self.ix.root / c).exists()
            w, n = self.nodes_for(c)
            if re.fullmatch(r"tests/test_[^/]*\.py", c) and exists:
                w.add(c)                                  # 変えたテストそのもの
            is_test = re.fullmatch(r"tests/test_[^/]*\.py", c) and exists
            if not is_test and not self.is_mapped(c):
                # 対応の分からないファイル(名指しするテストが無い)。消したファイルは、
                # 参照していたテストが今の木に残っていないかもしれない。
                unknown.append(c + ("" if exists else " (deleted)"))
            per_file[c] = sorted(w) + sorted(n)
            whole |= w
            nodes |= n
        if unknown:
            return {"mode": "full",
                    "reasons": ["no test is known to depend on: " + ", ".join(unknown[:10])
                                + (" (+%d more)" % (len(unknown) - 10) if len(unknown) > 10 else "")],
                    "per_file": per_file}
        missing = [a for a in self.always if not (self.ix.root / a).exists()]
        if missing:
            return {"mode": "full", "reasons": ["always-run gate missing: " + ", ".join(missing)]}
        whole |= set(self.always)
        nodes = {n for n in nodes if n.split("::", 1)[0] not in whole}
        tests = sorted(whole) + sorted(nodes)
        reasons.append("%d changed files -> %d test files + %d single parametrised runs "
                       "(incl. %d always-run gates)"
                       % (len(changed), len(whole), len(nodes), len(self.always)))
        return {"mode": "selected", "reasons": reasons, "tests": tests, "per_file": per_file}

# --------------------------------------------------------------------------- #
# pytest の側: 選んだテストだけ残す・片に分ける(tests/conftest.py が呼ぶ)        #
# --------------------------------------------------------------------------- #
SELECTION_ENV = "FULLSEYE_CI_SELECTION"     # 選んだテストの一覧のファイル(このツールの --tests-file)
SHARD_ENV = "FULLSEYE_CI_SHARD"             # "k/N"(1 始まり)


def read_selection(path: str) -> tuple[set[str], set[str]]:
    """一覧のファイル -> (ファイルごと選ぶテスト, ノード id で選ぶテスト)。読めなければ例外(fail-closed)。"""
    files, nodes = set(), set()
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        (nodes if "::" in line else files).add(line)
    if not files and not nodes:
        raise ValueError("the selection file %s is empty" % path)
    return files, nodes


def select_nodeids(nodeids: list[str], files: set[str], nodes: set[str]) -> tuple[list[str], list[str]]:
    """(残すノード id, 一覧にあるのに 1 件も当たらなかった項目)。"""
    keep = [n for n in nodeids if n in nodes or n.split("::", 1)[0] in files]
    present_files = {n.split("::", 1)[0] for n in nodeids}
    present = set(nodeids)
    unmatched = sorted([f for f in files if f not in present_files] + [n for n in nodes if n not in present])
    return keep, unmatched


def _group_key(nodeid: str) -> str:
    """片分けの単位。**ファイルごと**まとめる(module / session の fixture を片ごとに作り直さない)。

    ★2026-11-10 まで pytest-split の least_duration で**テストごと**に散らしていたので、
    module fixture の重い準備が片の数だけ作り直されていた(例: ``test_ledger_contracts.py`` の
    探針 1 回 約 300〜450 秒が 4 片で計 1,326 秒、``test_anim3d_i18n_itokawa`` の生成 1 回 約 300 秒が
    3 片で計 871 秒)。
    台本を走らせる門(``SCRIPT_RUNNERS``)も**ファイルごと**にする。session fixture が片に残った台本を
    まとめて並列に走らせ、その時間を**最初の 1 件**に計上するので、``.test_durations`` の
    パラメータごとの値は台本の重さではない(実測: 549 秒の 1 件と 0 秒の残り)。散らすと
    「0 秒」と記録された重い台本が 1 つの片に寄り、片 4 だけ 75 分になっていた(run 42594122086)。
    ファイルの合計(各片の一括実行の合計)なら重さとして意味がある。
    """
    return nodeid.split("::", 1)[0]


def shard_plan(nodeids: list[str], n: int, durations: dict) -> list[list[str]]:
    """*nodeids* を *n* 片に分ける(ファイル単位の LPT。決定的: 同じ入力なら全片で同じ答え)。

    重さは ``.test_durations`` の実測の和。記録の無いテストは記録のあるテストの平均で仮置き
    (pytest-split と同じ)。返り値の各片は元の並び順を保つ。全部のノード id がちょうど 1 片に入る。
    """
    if n < 1:
        raise ValueError("n must be >= 1")
    known = [durations[x] for x in nodeids if x in durations]
    mean = (sum(known) / len(known)) if known else 1.0
    weight: dict[str, float] = defaultdict(float)
    order: dict[str, int] = {}
    for i, x in enumerate(nodeids):
        k = _group_key(x)
        weight[k] += durations.get(x, mean)
        order.setdefault(k, i)
    loads = [0.0] * n
    where: dict[str, int] = {}
    for k in sorted(weight, key=lambda k: (-weight[k], order[k])):
        j = min(range(n), key=lambda j: (loads[j], j))
        where[k] = j
        loads[j] += weight[k]
    out: list[list[str]] = [[] for _ in range(n)]
    for x in nodeids:
        out[where[_group_key(x)]].append(x)
    return out


def parse_shard(spec: str) -> tuple[int, int]:
    k, _, n = spec.partition("/")
    k, n = int(k), int(n)
    if not (1 <= k <= n):
        raise ValueError("bad shard spec %r (want k/N with 1 <= k <= N)" % spec)
    return k, n


def plan_session(nodeids: list[str], *, selection: str | None, shard: str | None,
                 durations_path: Path | None = None) -> dict:
    """conftest から呼ぶ入口。残すノード id と、ログに出す数を返す。"""
    info: dict = {"collected": len(nodeids)}
    keep = list(nodeids)
    if selection:
        files, nodes = read_selection(selection)
        keep, unmatched = select_nodeids(keep, files, nodes)
        info.update(selected=len(keep), unmatched=unmatched)
        if not keep:
            raise ValueError("the selection %s matched no collected test" % selection)
    if shard:
        k, n = parse_shard(shard)
        try:
            durations = json.loads((durations_path or ROOT / ".test_durations").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            durations = {}
        plan = shard_plan(keep, n, durations)
        keep = plan[k - 1]
        known = [durations[x] for x in plan[k - 1] if x in durations]
        info.update(shard="%d/%d" % (k, n), in_shard=len(keep),
                    est_seconds=round(sum(known)), sizes=[len(p) for p in plan])
    info["keep"] = keep
    return info


# --------------------------------------------------------------------------- #
# 入出力                                                                      #
# --------------------------------------------------------------------------- #
def load_always(path: Path | None = None) -> list[str]:
    path = path or (ROOT / "tools" / "ci_always_run.txt")
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.append(line)
    return out


def estimate_seconds(tests: list[str] | None, durations_path: Path | None = None) -> float:
    durations_path = durations_path or (ROOT / ".test_durations")
    try:
        d = json.loads(durations_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return float("nan")
    if tests is None:
        return float(sum(d.values()))
    per: dict[str, float] = defaultdict(float)
    for k, v in d.items():
        per[k.split("::", 1)[0]] += v
    mean = (sum(per.values()) / len(per)) if per else 0.0
    total = 0.0
    for t in set(tests):
        if "::" in t:
            total += d.get(t, mean / 10.0)       # 1 パラメータ(未記録なら平均の 1/10 で仮置き)
        else:
            total += per.get(t, mean)
    return float(total)


def shards_for(seconds: float) -> int:
    if not math.isfinite(seconds):
        return MAX_SHARDS
    return max(1, min(MAX_SHARDS, math.ceil(seconds / TARGET_SHARD_SECONDS)))


# --------------------------------------------------------------------------- #
# 先頭のジョブ(gates): 落ちやすくて軽いテストを、片と並行して先に回す(2026-11-10)   #
# --------------------------------------------------------------------------- #
# 門も普通のテストも同じ片に混ぜて回すと、門が落ちても片が終わる 30〜45 分後まで赤にならない。
# 先頭のジョブは、**実績で落ちやすくて軽い**ファイルだけを先に回す。**片の側は何も減らさない**
# (ここで選ぶのは「先にも回すもの」で、片から外すものではない)。
#: 先頭のジョブで回すテストの ``.test_durations`` の合計の上限(秒)。入らないものは実績の順で外す。
EARLY_BUDGET_SECONDS = 8 * 60
#: 門でないテストを先頭のジョブへ入れる下限: 実績で**別々のブランチ**で落ちた数。
#: 同じブランチの push し直しで 2 回落ちただけのものは、繰り返す失敗の証拠にならない。
EARLY_MIN_BRANCHES = 2
#: 失敗の実績(``tools/ci_failure_history.py`` が GitHub のログから数えて書く。手で書かない)。
FAILURE_HISTORY = "tools/ci_failure_history.json"
#: 鮮度の門。判定が「その session に何が集まったか」で決まるので、数本だけ集めて回すと別の問いになる
#: (片では 4,000 件に対する 95 %、先頭のジョブでは数百件に対する 95 %)。先頭のジョブでは pytest に渡さず、
#: 片と同じ session を作って門の本体を呼ぶ(``freshness_forecast``)。
FRESHNESS_GATE = "tests/test_test_durations_is_fresh.py"


def load_failure_history(path: Path | None = None) -> dict:
    """失敗の実績の表。読めない・形が違うときは例外(fail-closed: 黙って「実績なし」にしない)。"""
    path = path or (ROOT / FAILURE_HISTORY)
    data = json.loads(path.read_text(encoding="utf-8"))
    files = data.get("files") if isinstance(data, dict) else None
    if not isinstance(files, dict) or not files:
        raise ValueError("%s has no 'files' table" % path)
    table: dict[str, dict] = {}
    for name, row in files.items():
        runs = row.get("failed_runs") if isinstance(row, dict) else None
        branches = row.get("branches") if isinstance(row, dict) else None
        if not (isinstance(runs, int) and isinstance(branches, int) and 1 <= branches <= runs):
            raise ValueError("%s: bad row for %r: %r" % (path, name, row))
        table[name] = {"failed_runs": runs, "branches": branches}
    runs_read = data.get("runs_read")
    if not isinstance(runs_read, int) or runs_read < max(r["failed_runs"] for r in table.values()):
        raise ValueError("%s: runs_read=%r is smaller than a file's failed_runs" % (path, runs_read))
    return {"runs_read": runs_read, "window": data.get("window") or [], "files": table}


def early_plan(always: list[str], history: dict, *, budget: float = EARLY_BUDGET_SECONDS,
               min_branches: int = EARLY_MIN_BRANCHES, durations_path: Path | None = None,
               root: Path = ROOT) -> dict:
    """先頭のジョブで回すテストのファイルを、失敗の実績の順に、時間の上限まで選ぶ。

    * 候補 = 門(*always* = 明示の一覧 + repo を走査するテスト)全部と、実績で *min_branches* 本以上の
      ブランチで落ちたファイル。
    * 外すもの = 鮮度の門(``FRESHNESS_GATE``)と台本を走らせる門(``SCRIPT_RUNNERS``)。どちらも判定や
      所要時間が session で決まる。この木に無いファイル(実績は別のブランチのもの)も外す。
    * 並べ方 = 落ちた run の数が多い順 → 記録時間が短い順 → 名前。上から見て、合計が *budget* を
      超えないものを入れる(入らないものは飛ばして次を見る)。記録の無いファイルはファイルの平均で仮置き。
    * 返り値の ``tests`` は**回す順**(落ちやすいものが先)。``rows`` は候補全部と、入れた / 外した理由。

    1 件も選べなければ例外(先頭のジョブが黙って 0 件で緑にならないように)。
    """
    durations_path = durations_path or (ROOT / ".test_durations")
    per: dict[str, float] = defaultdict(float)
    for k, v in json.loads(durations_path.read_text(encoding="utf-8")).items():
        per[k.split("::", 1)[0]] += v
    mean = (sum(per.values()) / len(per)) if per else 0.0
    table = history["files"]
    gates = set(always)
    pool = gates | {f for f, row in table.items() if row["branches"] >= min_branches}
    rows = []
    for f in pool:
        row = table.get(f, {"failed_runs": 0, "branches": 0})
        rows.append({"file": f, "failed_runs": row["failed_runs"], "branches": row["branches"],
                     "seconds": round(per.get(f, mean), 1), "recorded": f in per, "gate": f in gates})
    rows.sort(key=lambda r: (-r["failed_runs"], r["seconds"], r["file"]))
    total = 0.0
    for r in rows:
        if r["file"] == FRESHNESS_GATE:
            r.update(early=False, why="session-dependent (checked by the freshness forecast instead)")
        elif r["file"] in SCRIPT_RUNNERS:
            r.update(early=False, why="script runner (its time and verdict depend on the session)")
        elif not (root / r["file"]).is_file():
            r.update(early=False, why="not in this tree")
        elif total + r["seconds"] > budget:
            r.update(early=False, why="over the %d s budget" % budget)
        else:
            total += r["seconds"]
            r.update(early=True, why="")
    tests = [r["file"] for r in rows if r["early"]]
    if not tests:
        raise ValueError("the early list is empty (budget %s s, %d candidates)" % (budget, len(rows)))
    return {"tests": tests, "seconds": round(total, 1), "budget": budget, "rows": rows,
            "runs_read": history["runs_read"], "window": history["window"]}


def read_collected(path: str) -> list[str]:
    """``pytest --collect-only -q`` の出力 -> ノード id(集めた順)。

    末尾の「N tests collected」と件数が合わなければ例外(警告の行を拾った・行が欠けた、を黙って通さない)。
    """
    ids, total = [], None
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        head = line.split("::", 1)[0]
        if "::" in line and head.startswith("tests/") and head.endswith(".py") and " " not in head:
            ids.append(line)
            continue
        m = re.match(r"^(\d+) tests? collected in ", line)
        if m:
            total = int(m.group(1))
    if total is None or total != len(ids) or not ids:
        raise ValueError("%s: read %d node ids but the summary says %r collected" % (path, len(ids), total))
    return ids


def freshness_forecast(nodeids: list[str], *, nshards: int, selection: str | None = None,
                       durations_path: Path | None = None, gate_path: Path | None = None) -> dict:
    """鮮度の門が片で出す答えを、片が終わる前に出す。

    片と同じ手順(``plan_session``)で、鮮度の門が入る片の session を作り、**門の本体をそのまま呼ぶ**
    (閾値も文言もここへ写さない)。門のファイルにテスト関数がちょうど 1 つ、が前提(違えば例外)。
    """
    gate_path = gate_path or (ROOT / FRESHNESS_GATE)
    keep, shard = None, None
    for k in range(1, nshards + 1):
        info = plan_session(nodeids, selection=selection, shard="%d/%d" % (k, nshards),
                            durations_path=durations_path)
        if any(n.split("::", 1)[0] == FRESHNESS_GATE for n in info["keep"]):
            keep, shard = info["keep"], info["shard"]
            break
    if keep is None:
        raise ValueError("no shard holds %s (%d node ids, %d shards)" % (FRESHNESS_GATE, len(nodeids), nshards))
    spec = importlib.util.spec_from_file_location("_fullseye_freshness_gate", gate_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    funcs = [v for name, v in sorted(vars(mod).items()) if name.startswith("test_") and callable(v)]
    if len(funcs) != 1:
        raise ValueError("%s: expected exactly 1 test function, found %d" % (gate_path, len(funcs)))
    request = SimpleNamespace(session=SimpleNamespace(items=[SimpleNamespace(nodeid=n) for n in keep]))
    try:
        funcs[0](request)
    except AssertionError as e:
        return {"ok": False, "shard": shard, "in_shard": len(keep), "message": str(e)}
    return {"ok": True, "shard": shard, "in_shard": len(keep), "message": ""}


def _main_early(args) -> int:
    """``--early-list`` / ``--freshness-forecast``。入力が使えないときは 2(黙って緑にしない)。"""
    try:
        if args.early_list:
            always = Selector(Index(ROOT), load_always(args.always_file)).always
            plan = early_plan(always, load_failure_history())
            Path(args.early_list).write_text("\n".join(plan["tests"]) + "\n", encoding="utf-8")
            head = ("early tests: %d files, %.0f s recorded (budget %d s); ranked by %d failed runs (%s)"
                    % (len(plan["tests"]), plan["seconds"], plan["budget"], plan["runs_read"],
                       " .. ".join(plan["window"])))
            print(head)
            for r in plan["rows"]:
                print("  %-5s %2d runs %7.1f s%s  %s%s" % ("run" if r["early"] else "later", r["failed_runs"],
                                                         r["seconds"], " " if r["recorded"] else "*",
                                                         r["file"], ("   <- " + r["why"]) if r["why"] else ""))
            if args.summary:
                with open(args.summary, "a", encoding="utf-8") as fh:
                    fh.write("## %s\n\n| | failed runs | seconds | file |\n|---|---:|---:|---|\n" % head)
                    for r in plan["rows"]:
                        fh.write("| %s | %d | %.1f | `%s` %s |\n" % ("first" if r["early"] else "shards only",
                                                                    r["failed_runs"], r["seconds"], r["file"], r["why"]))
                    fh.write("\nEvery file above also runs in the shards. `*` in the log = no recorded time.\n")
        if args.freshness_forecast:
            if not args.nshards:
                raise ValueError("--freshness-forecast needs --nshards")
            res = freshness_forecast(read_collected(args.freshness_forecast), nshards=args.nshards,
                                     selection=args.selection or None)
            print("freshness forecast for shard %s (%d tests): %s"
                  % (res["shard"], res["in_shard"], "ok" if res["ok"] else "FAIL"))
            if not res["ok"]:
                print(res["message"])
                return 1
    except (OSError, ValueError, KeyError) as e:
        print("ci_select_tests: %s: %s" % (type(e).__name__, e), file=sys.stderr)
        return 2
    return 0


def changed_from_git(base: str, head: str = "HEAD") -> list[str]:
    out = subprocess.run(["git", "diff", "--name-only", "--no-renames", base + "..." + head],
                         cwd=ROOT, check=True, capture_output=True, text=True).stdout
    return [line.strip() for line in out.splitlines() if line.strip()]


def decide(changed: list[str] | None, *, full_reason: str | None = None,
           always_file: Path | None = None) -> dict:
    if full_reason:
        res = {"mode": "full", "reasons": [full_reason]}
    elif changed is None:
        res = {"mode": "full", "reasons": ["changed files unavailable"]}
    else:
        res = Selector(Index(ROOT), load_always(always_file)).select(changed)
    res["seconds"] = round(estimate_seconds(res.get("tests") if res["mode"] == "selected" else None))
    res["shards"] = shards_for(res["seconds"]) if res["mode"] == "selected" else MAX_SHARDS
    return res


def deps_drift_reason(code_file: str, text_file: str) -> str | None:
    """依存の版の比較(``tools/ci_deps_drift.py --compare``)が「同じ」でなければ full の理由を返す。

    diff と無関係な失敗(依存の新しい版、#271 の threadpoolctl 3.8.0)は変更から辿れないので、
    版が最後の全数の run と 1 つでも違えば全部回す。結果が読めないのも full(fail-safe)。
    """
    try:
        code = int(Path(code_file).read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return "dependency check result unreadable"
    try:
        lines = [ln for ln in Path(text_file).read_text(encoding="utf-8").splitlines() if ln.strip()]
    except OSError:
        lines = []
    if code == 0:
        return None
    what = "dependency versions differ from the last full run" if code == 1 else \
        "no dependency baseline from a full run (cannot compare)"
    return what + (": " + "; ".join(lines[:12]) if lines else "")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", help="git の比較元(PR の base、例: origin/master)")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--files", nargs="*", help="変更ファイルを直接渡す")
    ap.add_argument("--full", metavar="REASON", help="判定せず full にする(master・schedule・ci:full)")
    ap.add_argument("--json", action="store_true", help="結果を JSON で標準出力へ")
    ap.add_argument("--github-output", help="GITHUB_OUTPUT のパス(mode / shards / tests-file を書く)")
    ap.add_argument("--tests-file", default="ci_selected_tests.txt",
                    help="選んだテストの一覧を書くファイル(selected のときだけ)")
    ap.add_argument("--summary", help="GITHUB_STEP_SUMMARY のパス")
    ap.add_argument("--always-file", type=Path,
                    help="毎回回す門の一覧(既定 tools/ci_always_run.txt。CI は base の版を渡す)")
    ap.add_argument("--deps-drift", nargs=2, metavar=("CODE_FILE", "TEXT_FILE"),
                    help="tools/ci_deps_drift.py --compare の終了コードと出力。0 以外なら full "
                         "(依存の版が最後の全数の run と違う / 比べられない)")
    ap.add_argument("--early-list", metavar="FILE",
                    help="先頭のジョブ(gates)で先に回すテストのファイルを、回す順に FILE へ書く"
                         "(失敗の実績 tools/ci_failure_history.json の順、合計 %d 秒まで)" % EARLY_BUDGET_SECONDS)
    ap.add_argument("--freshness-forecast", metavar="COLLECTED",
                    help="`pytest --collect-only -q` の出力から、鮮度の門が片で出す答えを先に出す(落ちるなら exit 1)")
    ap.add_argument("--nshards", type=int, help="--freshness-forecast: 片の数")
    ap.add_argument("--selection", help="--freshness-forecast: PR で選んだテストの一覧(selected のとき)")
    args = ap.parse_args(argv)
    if args.early_list or args.freshness_forecast:
        return _main_early(args)
    changed = None
    full_reason = args.full
    if not full_reason and args.deps_drift:
        full_reason = deps_drift_reason(*args.deps_drift)
    if not full_reason:
        if args.files is not None:
            changed = args.files
        elif args.base:
            try:
                changed = changed_from_git(args.base, args.head)
            except (subprocess.CalledProcessError, OSError) as e:   # fail-safe: 全部
                full_reason = "git diff failed: %s" % e
        else:
            full_reason = "no --base / --files given"
    try:
        res = decide(changed, full_reason=full_reason, always_file=args.always_file)
    except Exception as e:  # noqa: BLE001 - 判定の故障は全部回す側へ倒す(黙って少なく回さない)
        res = {"mode": "full", "reasons": ["selector crashed: %s: %s" % (type(e).__name__, e)],
               "seconds": round(estimate_seconds(None)), "shards": MAX_SHARDS}
    if res["mode"] == "selected":
        Path(args.tests_file).write_text("\n".join(res["tests"]) + "\n", encoding="utf-8")
    if args.github_output:
        with open(args.github_output, "a", encoding="utf-8") as fh:
            fh.write("mode=%s\n" % res["mode"])
            fh.write("shards=%s\n" % json.dumps(list(range(1, res["shards"] + 1))))
            fh.write("nshards=%d\n" % res["shards"])
    if args.summary:
        with open(args.summary, "a", encoding="utf-8") as fh:
            fh.write("## CI test selection: **%s** (%d shard(s), est. %s s)\n\n"
                     % (res["mode"], res["shards"], res.get("seconds")))
            for r in res["reasons"]:
                fh.write("- %s\n" % r)
            if res["mode"] == "selected":
                fh.write("\n<details><summary>%d test files</summary>\n\n" % len(res["tests"]))
                for t in res["tests"]:
                    fh.write("- `%s`\n" % t)
                fh.write("\n</details>\n")
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        print("mode=%s shards=%d est=%ss" % (res["mode"], res["shards"], res.get("seconds")))
        for r in res["reasons"]:
            print("  " + r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
