"""Build the MCP recipe index from human-written recipes: recipes.py (Studio samples) + fullseye/recipebook.

Two sources, both hand-authored and both executed by the test suite:

* ``recipes.py RECIPES`` — the 25 Studio sample pipelines (2-D registry ops, ``(op, a, b)``).
* ``fullseye/recipebook`` — the coverage recipes (>= 1 per docs/ops family; tests/test_recipebook.py
  runs every one on two synthetic variants with truth gates).

Each row carries ``runner``: ``"mcp"`` when every stage is an MCP-verified registry op with only the a/b
knobs (MCP ``fullseye_pipeline`` runs it as is), else ``"python"`` (call the stage ops in order through
the facade / the op graph's executor; ``args`` / ``kw`` are the real arguments). MCP ``fullseye_find_ops``
only offers ``runner == "mcp"`` rows, because those are the ones an MCP client can execute.
"""
from __future__ import annotations
import ast, json, os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

LANGS = ("ja", "en", "zh", "tw", "ko", "de", "hi")

#: recipes.py の task 語 -> 典型の課題の分類(recipebook.TASK_CLASSES)。
LEGACY_TASK_CLASS = {"denoise": "preprocess", "edge": "preprocess", "segment": "preprocess",
                     "measure": "measurement", "ocr": "preprocess", "enhance": "preprocess",
                     "texture": "analysis", "features": "analysis", "morphology": "preprocess",
                     "shape": "analysis", "inspect": "inspection"}


def _line_numbers(path, var="RECIPES"):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    value = next(n.value for n in tree.body if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == var for t in n.targets))
    out = {}
    for n in value.elts:
        if not isinstance(n, ast.Dict):
            continue
        for k, v in zip(n.keys, n.values):
            if isinstance(k, ast.Constant) and k.value == "name" and isinstance(v, ast.Constant):
                out[v.value] = n.lineno
    return out


def _texts(names, by_name):
    terms = {lang: [] for lang in LANGS}
    for name in names:
        summaries = by_name.get(name, {}).get("s", {})
        for lang in LANGS:
            text = summaries.get(lang) or summaries.get("en") or summaries.get("ja")
            if text:
                terms[lang].append(text)
    return terms


def _public_stage(st):
    """索引に載せる段(既定の args は省く)。"""
    out = {"op": st["op"]}
    for k in ("a", "b", "args", "kw", "call"):
        if k in st:
            out[k] = st[k]
    return out


def build():
    sys.path.insert(0, str(ROOT))
    os.environ.setdefault("FULLSEYE_DEVICE", "cpu")
    import api, recipes  # noqa: E401
    import fullseye  # noqa: F401  (engine modules on sys.path)
    from fullseye import recipebook as rb
    rows = json.loads((ROOT / "fullseye/data/OP_SEARCH.json").read_text(encoding="utf-8"))["ops"]
    by_name = {r["n"]: r for r in rows}
    out = []
    # 日本語の名前と説明(手書き)。ja の検索文に足し、行にも when_ja として載せる。
    NOTES_JA = rb.notes_ja()
    lines = _line_numbers(ROOT / "recipes.py")
    for r in recipes.RECIPES:
        sort = "image"; stages = []
        for name, a, b in r["stages"]:
            op = api.find_op(name)
            if op is None or op.in_sort not in (sort, "any"):
                raise RuntimeError(f"invalid recipe {r['name']}: {name} after {sort}")
            sort = op.out_sort; stages.append({"op": name, "a": a, "b": b})
        terms = _texts([s["op"] for s in stages], by_name)
        tclass = LEGACY_TASK_CLASS.get(r["task"], "preprocess")
        out.append({"name": r["name"], "task": r["task"], "family": "2d", "task_class": tclass,
                    "halcon": None, "runner": "mcp", "input_sort": "image", "output_sort": sort,
                    "stages": stages, "when": r["note"], "image": r.get("image"),
                    "source": {"path": "recipes.py", "line": lines[r["name"]]},
                    "when_ja": NOTES_JA.get(r["name"]),
                    "index_text": {lang: " ".join([r["name"], r["task"], r["note"],
                                                   *([NOTES_JA[r["name"]]] if lang == "ja" and r["name"] in NOTES_JA else []),
                                                   *texts])
                                   for lang, texts in terms.items()}})
    book_lines = {}
    for book in rb.BOOKS:
        p = ROOT / "fullseye" / "recipebook" / (book + ".py")
        if p.exists():
            # 本は dict を直に書くものと、小さな関数で組むものがある。名前の文字列定数の最初の行を取る。
            first = {}
            for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    first[node.value] = min(first.get(node.value, node.lineno), node.lineno)
            book_lines[book] = first
    for r in rb.RECIPES:
        book = rb.BOOK_OF[r["name"]]
        if rb.type_cuts(r):
            raise RuntimeError("recipe %r has type cuts: %s" % (r["name"], [c for c in rb.connections(r) if not c[4]]))
        stages = [_public_stage(st) for st in r["stages"]]
        terms = _texts([s["op"] for s in stages], by_name)
        words = [r["name"], r["task"], r["task_class"], r["family"], r.get("halcon") or "", r["note"]]
        out.append({"name": r["name"], "task": r["task"], "family": r["family"], "task_class": r["task_class"],
                    "halcon": r.get("halcon"), "runner": "mcp" if rb.is_mcp_runnable(r) else "python",
                    "input_sort": rb.norm_sort(r.get("input_sort")), "output_sort": rb.output_sort(r),
                    "stages": stages, "when": r["note"], "image": None,
                    "source": {"path": "fullseye/recipebook/%s.py" % book, "line": book_lines[book][r["name"]]},
                    "when_ja": NOTES_JA.get(r["name"]),
                    "index_text": {lang: " ".join([*words,
                                                   *([NOTES_JA[r["name"]]] if lang == "ja" and r["name"] in NOTES_JA else []),
                                                   *texts]) for lang, texts in terms.items()}})
    names = [r["name"] for r in out]
    dup = sorted({n for n in names if names.count(n) > 1})
    if dup:
        raise RuntimeError("recipe names collide between recipes.py and recipebook: %s" % dup)
    poc = sorted((ROOT / "examples").glob("poc_*.py"))
    gate = json.loads((ROOT / "studio_lite/gates/recipes_gate.json").read_text(encoding="utf-8"))
    docs = list((ROOT / "docs").rglob("*.md"))
    return {"schema_version": 2, "recipes": out, "inventory": [
        {"source": "recipes.py RECIPES", "found": len(recipes.RECIPES), "included": len(recipes.RECIPES),
         "excluded": 0, "reason": None},
        {"source": "fullseye/recipebook RECIPES", "found": len(rb.RECIPES), "included": len(rb.RECIPES),
         "excluded": 0, "reason": None},
        {"source": "examples/poc_*.py", "found": len(poc), "included": 0, "excluded": len(poc),
         "reason": "PoC programs are arbitrary Python; a linear MCP pipeline cannot be extracted statically without guessing."},
        {"source": "studio_lite/gates/recipes_gate.json", "found": len(gate.get("recipes", [])), "included": 0,
         "excluded": len(gate.get("recipes", [])),
         "reason": "Execution gates duplicate selected built-in recipes and are not distinct examples."},
        {"source": "docs/**/*.md", "found": len(docs), "included": 0, "excluded": len(docs),
         "reason": "Documentation contains prose and snippets, not a statically unambiguous inventory of MCP stages."}]}


if __name__ == "__main__":
    target = ROOT / "fullseye/data/RECIPE_INDEX.json"
    target.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(target)
