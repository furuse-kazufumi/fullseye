#!/usr/bin/env python3
"""ViEW2026 に載せる展示が Fullseye の計算を通るかを静的に数える。"""
from __future__ import annotations

import ast
import json
import tomllib
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
VIEW = ROOT / "docs" / "view2026"
OP_INDEX = ROOT / "fullseye" / "data" / "OP_INDEX.json"
PYPROJECT = ROOT / "pyproject.toml"

# ``fs.<name>(...)`` だけでは Fullseye の「計算」を通った証拠にならない入口。
# 値は除外理由で、一覧そのものをテストと報告から確認できるよう公開する。
NON_COMPUTE_FS_CALLS = {
    "apply": "文字列 op の汎用ディスパッチ。既知の op 名がリテラルで渡された場合だけ別規則で数える",
    "available_ops": "利用可能な op の一覧取得であり、画像・計測の計算をしない",
    "ledger": "op 台帳と raw 実装への入口であり、この経路だけでは公開 Fullseye の計算を通した証拠にしない",
    "list_ops": "op の一覧取得であり、画像・計測の計算をしない",
    "op_explain": "op の説明取得であり、画像・計測の計算をしない",
    "op_find": "op の検索であり、画像・計測の計算をしない",
    "op_help": "op のヘルプ取得であり、画像・計測の計算をしない",
    "op_info": "op のメタデータ取得であり、画像・計測の計算をしない",
    "op_recommend": "op の推薦・検索であり、画像・計測の計算をしない",
    "op_search": "op の検索であり、画像・計測の計算をしない",
    "write_viewer": "計算済み結果を HTML に記録する表示処理であり、画像・計測の計算をしない",
}

# pyproject の ``py-modules`` には展示用 I/O も入る。これらの呼び出しだけで
# 「Fullseye の計算を通った」とすると、図を保存しただけの PoC が門を通る。
NON_COMPUTE_MODULES = {
    "examplefig": "作図・保存の補助であり、展示が示す画像・計測の計算本体ではない",
    "pocviewer": "計算済み結果を HTML に記録する表示処理である",
    "realdata": "入力データの取得口であり、画像・計測の計算をしない",
}


@dataclass(frozen=True)
class GateResult:
    exhibit_id: str
    source: Path | None
    calls: tuple[str, ...]

    @property
    def count(self) -> int:
        return len(self.calls)


@cache
def op_names() -> set[str]:
    data = json.loads(OP_INDEX.read_text(encoding="utf-8"))
    return {row["name"] for row in data["ops"]}


@cache
def distributed_modules() -> set[str]:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    setuptools = data["tool"]["setuptools"]
    modules = set(setuptools["py-modules"])
    modules.update(name.split(".", 1)[0] for name in setuptools["packages"])
    return modules


def withdrawn_ids(base: Path = VIEW) -> set[str]:
    ids: set[str] = set()
    for path in sorted(base.glob("withdrawn_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        ids.update(item["id"] for item in data["exhibits"])
    return ids


def _repo_path_from_url(value: str) -> Path | None:
    """GitHub の blob URL から、この checkout 内のファイルを返す。"""
    if not value:
        return None
    parsed = urlparse(value)
    marker = "/blob/master/"
    if parsed.netloc != "github.com" or marker not in parsed.path:
        return None
    candidate = ROOT / parsed.path.split(marker, 1)[1]
    return candidate if candidate.is_file() else None


def source_for(item: dict) -> Path | None:
    """展示の例、無ければ登録された作り元を返す。"""
    example = ROOT / "examples" / (item["id"] + ".py")
    if example.is_file():
        return example
    source = _repo_path_from_url(str(item.get("source_url", "")))
    if source is not None and source.suffix == ".py":
        return source
    return None


def _attr_parts(node: ast.AST) -> list[str] | None:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    parts.append(node.id)
    return list(reversed(parts))


def count_calls(path: Path) -> tuple[str, ...]:
    """4 規則の和集合に当たる Call ノードを、行番号つきで返す。"""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    ops = op_names()
    shipped = distributed_modules()
    fs_aliases: set[str] = set()
    module_aliases: set[str] = set()
    direct_ops: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".", 1)[0]
                local = alias.asname or top
                if alias.name == "fullseye":
                    fs_aliases.add(local)
                if top in shipped and top != "fullseye" and top not in NON_COMPUTE_MODULES:
                    module_aliases.add(local)
        elif isinstance(node, ast.ImportFrom) and node.module == "fullseye":
            for alias in node.names:
                if alias.name in ops:
                    direct_ops.add(alias.asname or alias.name)
    ledger_aliases: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        parts = _attr_parts(value) if value is not None else None
        if not parts or len(parts) != 2 or parts[0] not in fs_aliases or parts[1] != "ledger":
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        ledger_aliases.update(target.id for target in targets if isinstance(target, ast.Name))

    found: dict[int, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        parts = _attr_parts(node.func)
        final = parts[-1] if parts else node.func.id if isinstance(node.func, ast.Name) else ""

        reasons: list[str] = []
        rooted_at_fs = bool(parts and parts[0] in fs_aliases and len(parts) >= 2)
        fs_first = parts[1] if rooted_at_fs else ""
        # (a) OP_INDEX の op 名の呼び出し。外部ライブラリの同名関数は数えない。
        if ((isinstance(node.func, ast.Name) and node.func.id in direct_ops) or
                (rooted_at_fs and final in ops) or
                (parts and parts[0] in ledger_aliases and final in ops)):
            reasons.append("op:%s" % final)

        if rooted_at_fs:
            first = fs_first
            # (b) fs.<name>(...)。ledger 以下は全体を記録・検索経路として除く。
            if first not in NON_COMPUTE_FS_CALLS:
                reasons.append("fs:%s" % ".".join(parts[1:]))
            # (c) fs.apply(..., "<op 名>")。第2位置引数と op/name キーワードを認める。
            if first == "apply":
                values: list[ast.AST] = list(node.args[1:2])
                values += [kw.value for kw in node.keywords if kw.arg in ("op", "name")]
                for value in values:
                    if isinstance(value, ast.Constant) and isinstance(value.value, str) and value.value in ops:
                        reasons.append("apply:%s" % value.value)

        # (d) pyproject の配布対象トップレベルモジュールを import した名前空間の関数呼び出し。
        if parts and parts[0] in module_aliases and len(parts) >= 2:
            reasons.append("module:%s" % ".".join(parts))

        if reasons:
            found[id(node)] = "%d:%s" % (node.lineno, "+".join(sorted(set(reasons))))
    return tuple(sorted(found.values(), key=lambda value: int(value.split(":", 1)[0])))


def inspect(item: dict) -> GateResult:
    source = source_for(item)
    calls = count_calls(source) if source is not None else ()
    return GateResult(item["id"], source, calls)


def inspect_catalog(data: dict) -> dict[str, GateResult]:
    """exhibits/all の和集合を検査する。重複 id は情報の多い exhibits 側を優先する。"""
    items = {item["id"]: item for item in data["all"]}
    items.update({item["id"]: item for item in data["exhibits"]})
    return {item_id: inspect(item) for item_id, item in sorted(items.items())}
