"""Audit failure-to-value fallbacks in the H16-owned modules.

Run ``py -3.11 tools/audit_fallbacks.py`` to refresh the ledger and add
``--check`` in CI to check that it is current.
"""
from __future__ import annotations

import argparse
import ast
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "fallback_audit.json"
COMMAND = "py -3.11 tools/audit_fallbacks.py"
MODULES = (
    "ops.py", "fslib.py", "image_gen.py", "geometry2d.py", "regions_gen.py",
    "regions_setops.py", "region_morph.py", "opsblob.py", "blob2d.py",
    "imagemorph.py", "morph_minkowski.py",
    # ★2026-11-09 独立レビュー(op 点検 geom): ops.RT / run_stages の op は backend_safe.guard が
    #   例外を握って fallback 値を返す。この経路(NaN 画像で ncc_locate → [0,0,0] 等)を勘定に入れる。
    "backend_safe.py",
)


def _name(node: ast.AST | None) -> str:
    if node is None:
        return "bare"
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_name(node.value)}.{node.attr}"
    if isinstance(node, ast.Tuple):
        return ", ".join(_name(item) for item in node.elts)
    return ast.unparse(node)


def _value(node: ast.AST | None) -> str:
    return "None" if node is None else ast.unparse(node)


def _empty_guard(node: ast.AST) -> bool:
    text = ast.unparse(node)
    return ("isinstance(" in text or ".size == 0" in text or
            "len(" in text and "== 0" in text)


def _classification(kind: str, qualname: str, fn_doc: str,
                    handler: ast.ExceptHandler | None,
                    returned: str) -> tuple[str, str]:
    if kind == "early_return":
        return "legitimate_empty", "空入力を明示的に検査して空の値を返す経路"
    # ★2026-11-09 独立レビュー: 本体が raise だけの節(素の ``raise`` で送り直す)は fail-closed。
    #   手書きの documented 表より先に見る(guard.w の MissingDependencyError 節が documented に
    #   数えられていた)。
    if handler is not None and handler.body and all(isinstance(n, ast.Raise) for n in handler.body):
        return "fail_closed", "捕捉した例外をそのまま(または別の例外として)送出する経路"
    documented = {
        "_have_cv2": "optional backendの既存選択機構が不在をFalseとして扱う",
        "_MatchCtx.__getitem__": "docstringにスレッドローカル値の共有fallbackが明記されている",
        "<module>": "optional backendの失敗をFAILED_BACKENDSと台帳へ記録する既存機構",
        "_label_guarded_functions_with_their_op_name": "変更不能なbuiltin/partialを飛ばす補助的なラベル処理",
        "guard.w": ("op の例外を record() で fs.fallbacks() に記録し(初回は警告)、sort の既定値"
                    "(match は [0,0,0])か op ごとの on_fail(ops._ON_FAIL_BY_OP: shape_locate は"
                    " 4 要素 [0,0,0,0])を返す。strict mode と MissingDependencyError は送出する"),
        "_fmt_exc": "例外の str() 自体が失敗したときに型名だけの表示へ落とす(記録の文字列化の補助)",
    }
    if qualname in documented:
        return "documented_fallback", documented[qualname]
    if qualname == "apply_genome":
        return ("undecided",
                "tests/test_known_bugs.py::test_apply_genome_handles_contour_ending_pipelineが例外を許さないため変更を保留")
    body = handler.body if handler else []
    if any(isinstance(n, ast.Raise) and n.exc is not None for n in ast.walk(ast.Module(body=body, type_ignores=[]))):
        return "fail_closed", "捕捉した例外をリポジトリ側の例外として送出する経路"
    doc = fn_doc.lower()
    if any(word in doc for word in ("fallback", "optional", "best-effort", "互換", "代替")):
        return "documented_fallback", "docstringに代替経路が明記されている"
    if returned != "-" or any(isinstance(n, ast.Pass) for n in body):
        return "silent_fallback", "例外を値またはpassへ変換して呼出側から失敗を隠す"
    return "undecided", "捕捉後の制御フローだけでは安全性を判定できない"


class _Scanner(ast.NodeVisitor):
    def __init__(self, module: str) -> None:
        self.module = module
        self.stack: list[tuple[str, str]] = []
        self.sites: list[dict[str, object]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.stack.append((node.name, ast.get_docstring(node) or ""))
        self.generic_visit(node)
        self.stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.stack.append((node.name, ""))
        self.generic_visit(node)
        self.stack.pop()

    def _qualname(self) -> str:
        return ".".join(name for name, _ in self.stack) or "<module>"

    def visit_Try(self, node: ast.Try) -> None:
        for handler in node.handlers:
            returns = [n for n in ast.walk(ast.Module(body=handler.body, type_ignores=[]))
                       if isinstance(n, ast.Return)]
            assigns = [n for n in ast.walk(ast.Module(body=handler.body, type_ignores=[]))
                       if isinstance(n, (ast.Assign, ast.AnnAssign, ast.AugAssign))]
            passes = [n for n in ast.walk(ast.Module(body=handler.body, type_ignores=[]))
                      if isinstance(n, ast.Pass)]
            raises = [n for n in ast.walk(ast.Module(body=handler.body, type_ignores=[]))
                      if isinstance(n, ast.Raise)]
            broad = handler.type is None or _name(handler.type) == "Exception"
            if not (returns or assigns or passes or raises or broad):
                continue
            values = [_value(n.value) for n in returns]
            values += [ast.unparse(n) for n in assigns]
            returned = "; ".join(values) if values else ("pass" if passes else "-")
            doc = self.stack[-1][1] if self.stack else ""
            classification, reason = _classification(
                "handler", self._qualname(), doc, handler, returned)
            self.sites.append({
                "module": self.module, "function": self._qualname(),
                "line": handler.lineno, "exception_types": [_name(handler.type)],
                "returned_or_assigned": returned, "classification": classification,
                "reason": reason,
            })
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        if _empty_guard(node.test):
            for stmt in node.body:
                if isinstance(stmt, ast.Return):
                    value = _value(stmt.value)
                    if "nan_to_num" in value:
                        # ★2026-11-09 独立レビュー: 代替値への置換は「空入力」ではない
                        self.sites.append({
                            "module": self.module, "function": self._qualname(),
                            "line": stmt.lineno, "exception_types": [],
                            "returned_or_assigned": value,
                            "classification": "documented_fallback",
                            "reason": "早期 return で np.nan_to_num の結果を返す経路(どの関数にも効く"
                                      "一般規則): 非有限値を代替値へ置き換えるのであって空入力ではない"
                                      "(置換値は呼び出しの引数どおり)",
                        })
                        continue
                    if value == "None" or any(token in value for token in ("zeros", "empty", "[:0", "[]", "{}", "0")):
                        self.sites.append({
                            "module": self.module, "function": self._qualname(),
                            "line": stmt.lineno, "exception_types": [],
                            "returned_or_assigned": value,
                            "classification": "legitimate_empty",
                            "reason": "空入力を明示的に検査して空の値を返す経路",
                        })
        self.generic_visit(node)


def scan() -> dict[str, object]:
    sites: list[dict[str, object]] = []
    for module in MODULES:
        scanner = _Scanner(module)
        scanner.visit(ast.parse((ROOT / module).read_text(encoding="utf-8"), filename=module))
        sites.extend(scanner.sites)
    sites.sort(key=lambda site: (site["module"], site["line"], site["function"]))
    counts = Counter(site["classification"] for site in sites)
    return {
        "header": {"scan_date": "2026-10-22", "command": COMMAND, "modules": list(MODULES)},
        "counts": {key: counts.get(key, 0) for key in (
            "fail_closed", "documented_fallback", "silent_fallback",
            "legitimate_empty", "undecided")},
        "sites": sites,
    }


def _render(data: dict[str, object]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = scan()
    fresh = _render(data)
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != fresh:
            print(f"{OUTPUT.relative_to(ROOT)} is stale; run: {COMMAND}")
            return 1
    else:
        OUTPUT.write_text(fresh, encoding="utf-8")
    print("classification          count")
    for name, count in data["counts"].items():
        print(f"{name:22} {count:5}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
