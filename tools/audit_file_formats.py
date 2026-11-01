# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0.
"""Statically inventory file-format readers and writers shipped by Fullseye.

The report is deliberately generated from Python source, the public operator
index and tests.  It is not a hand-maintained list: adding an extension to a
runtime module or exposing a reader/writer changes ``docs/FILE_FORMATS.md`` on
the next ``tools/regen_all.py`` run.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "FILE_FORMATS.md"

# Human labels do not determine membership or counts; discovery always comes
# from source literals.  Unknown extensions remain visible under an upper-case
# fallback label, which is important when a new format is introduced.
FORMAT_NAMES = {
    ".3fr": "Hasselblad RAW", ".agf": "Zemax glass catalog", ".asc": "XYZ text",
    ".avi": "AVI video", ".bmp": "BMP", ".csv": "CSV", ".dcm": "DICOM",
    ".dxf": "DXF", ".e57": "ASTM E57", ".exr": "OpenEXR", ".fits": "FITS",
    ".flac": "FLAC", ".gif": "GIF", ".glb": "glTF binary", ".gltf": "glTF",
    ".hdr": "Radiance HDR", ".jpeg": "JPEG", ".jpg": "JPEG", ".json": "JSON",
    ".las": "LAS", ".laz": "LAZ", ".mha": "MetaImage", ".mhd": "MetaImage",
    ".mjcf": "MuJoCo XML", ".mkv": "Matroska video", ".mrc": "MRC",
    ".nii": "NIfTI", ".nii.gz": "NIfTI", ".npy": "NumPy array", ".npz": "NumPy archive",
    ".nrrd": "NRRD", ".obj": "Wavefront OBJ", ".off": "Geomview OFF",
    ".ogg": "Ogg audio", ".ome.tif": "OME-TIFF", ".ome.tiff": "OME-TIFF",
    ".pcd": "PCL PCD", ".pfm": "PFM", ".ply": "Stanford PLY", ".png": "PNG",
    ".pts": "XYZ text", ".raw": "RAW raster", ".seq": "CODE V sequence",
    ".splat": "3D Gaussian splat", ".stl": "STL", ".svg": "SVG",
    ".tif": "TIFF", ".tiff": "TIFF", ".txt": "Text/XYZ", ".urdf": "URDF",
    ".wav": "WAV", ".webm": "WebM video", ".xlsx": "Excel workbook",
    ".xml": "XML", ".xyz": "XYZ point cloud", ".zmx": "Zemax lens file",
}
_EXT_RE = re.compile(r"^\.[a-z][a-z0-9]*(?:\.[a-z0-9]+)?$")
_IGNORED = {
    ".com", ".copy", ".dtype", ".format", ".get", ".html", ".index", ".kind",
    ".md", ".name", ".offset", ".path", ".shape", ".size", ".value",
}
_READ_NAME = re.compile(r"(?:^|_)(?:read|load|open|parse|decode|import)(?:_|$)")
_WRITE_NAME = re.compile(r"(?:^|_)(?:write|save|dump|export|encode)(?:_|$)")
_STDLIB = set(getattr(sys, "stdlib_module_names", ()))
_VERIFY_READERS = {
    ".csv": ("csv", "pandas"), ".ply": ("plyfile", "trimesh"),
    ".stl": ("stl", "trimesh"), ".obj": ("trimesh",), ".off": ("trimesh",),
    ".e57": ("pye57",), ".xlsx": ("openpyxl",), ".dxf": ("ezdxf",),
    ".fits": ("astropy",),
    ".mrc": ("mrcfile",),
    ".nrrd": ("nrrd",),
    ".nii": ("nibabel",), ".nii.gz": ("nibabel",),
}
_NAME_EXTS = {ext[1:]: ext for ext in FORMAT_NAMES if "." not in ext[1:]}


def _runtime_files() -> list[Path]:
    """Return importable project modules, excluding tests, examples and tools."""
    files = list(ROOT.glob("*.py")) + list((ROOT / "fullseye").rglob("*.py"))
    return sorted(p for p in files if "__pycache__" not in p.parts)


def _strings(node: ast.AST) -> set[str]:
    out = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            s = sub.value.lower()
            if _EXT_RE.fullmatch(s) and s not in _IGNORED:
                out.add(s)
    return out


def _module_name(path: Path) -> str:
    rel = path.relative_to(ROOT).with_suffix("")
    return ".".join(rel.parts)


def _imports(tree: ast.Module, local: set[str]) -> tuple[set[str], set[str]]:
    """Return module-level required/optional imports (not lazy function imports)."""
    required, optional = set(), set()

    def add(name: str, is_optional: bool) -> None:
        top = name.split(".")[0]
        if top in _STDLIB or top in local or top in {"numpy", "scipy", "fullseye"}:
            return
        (optional if is_optional else required).add(top)

    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            for name in names:
                add(name, False)
        elif isinstance(node, ast.Try):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Import):
                    for alias in sub.names:
                        add(alias.name, True)
                elif isinstance(sub, ast.ImportFrom):
                    add(sub.module or "", True)
    return required, optional


def _lazy_imports_and_calls(tree: ast.Module, local: set[str]):
    """Map each function to its lazy imports and same-module call targets."""
    imports, calls = {}, {}
    functions = {node.name: node for node in tree.body
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for name, node in functions.items():
        deps = set()
        for sub in ast.walk(node):
            if isinstance(sub, ast.Import):
                names = [alias.name for alias in sub.names]
            elif isinstance(sub, ast.ImportFrom):
                names = [sub.module or ""]
            else:
                continue
            for imported in names:
                top = imported.split(".", 1)[0]
                if top and top not in local and top not in _STDLIB:
                    deps.add(top)
        imports[name] = deps
        calls[name] = {sub.func.id for sub in ast.walk(node)
                       if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name)
                       and sub.func.id in functions}
    return imports, calls


def _reachable_lazy_imports(name: str, imports, calls) -> set[str]:
    result, seen, stack = set(), set(), [name]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        result.update(imports.get(current, ()))
        stack.extend(calls.get(current, ()))
    return result


def _source_inventory():
    files = _runtime_files()
    local = {p.stem for p in files}
    rows = defaultdict(lambda: {"read": set(), "write": set(), "modules": set(),
                               "required": set(), "optional": set()})
    for path in files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        module = _module_name(path)
        required, optional = _imports(tree, local)
        lazy_imports, calls = _lazy_imports_and_calls(tree, local)
        globals_by_name = {}
        for node in tree.body:
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                value = node.value
                names = ([t.id for t in node.targets if isinstance(t, ast.Name)]
                         if isinstance(node, ast.Assign) else
                         ([node.target.id] if isinstance(node.target, ast.Name) else []))
                exts = _strings(value)
                for name in names:
                    if exts:
                        globals_by_name[name] = exts
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name.startswith("_"):
                continue
            exts = _strings(node)
            for token in node.name.lower().split("_"):
                if token in _NAME_EXTS:
                    exts.add(_NAME_EXTS[token])
            used_names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
            for name in used_names:
                exts.update(globals_by_name.get(name, ()))
            lname = node.name.lower()
            reads = bool(_READ_NAME.search(lname))
            writes = bool(_WRITE_NAME.search(lname))
            if not (reads or writes):
                continue
            for ext in exts:
                rec = rows[ext]
                rec["modules"].add(module)
                rec["required"].update(required)
                rec["optional"].update(optional)
                rec["optional"].update(_reachable_lazy_imports(node.name, lazy_imports, calls))
                if reads:
                    rec["read"].add(f"{module}.{node.name}")
                if writes:
                    rec["write"].add(f"{module}.{node.name}")
    return rows


def _op_index() -> tuple[set[str], dict[str, set[str]]]:
    path = ROOT / "docs" / "OP_INDEX.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    names, by_module = set(), defaultdict(set)
    for row in data.get("ops", []):
        names.add(row["name"])
        by_module[row.get("module", "")].add(row["name"])
    return names, by_module


def _test_sources() -> dict[str, str]:
    return {str(p.relative_to(ROOT)).replace("\\", "/"): p.read_text(encoding="utf-8", errors="replace")
            for p in sorted((ROOT / "tests").glob("test_*.py"))}


def _imports_name(source: str, name: str) -> bool:
    """True only for a real import, not a coincidental function/file name."""
    return bool(re.search(r"(?m)^\s*(?:import\s+[^#\n]*\b%s\b|from\s+%s(?:\.|\s))"
                          % (re.escape(name), re.escape(name)), source))


def _short(items: set[str], limit: int = 4) -> str:
    vals = sorted(items)
    if not vals:
        return "—"
    shown = vals[:limit]
    return "<br>".join(f"`{v}`" for v in shown) + (f"<br>+{len(vals)-limit}" if len(vals) > limit else "")


def build_report() -> str:
    rows = _source_inventory()
    op_names, _ = _op_index()
    tests = _test_sources()
    lines = [
        "# Fullseye のファイル形式棚卸し",
        "",
        "この表は `tools/audit_file_formats.py` が実装モジュール、`docs/OP_INDEX.json`、テストを静的走査して生成する。",
        "拡張子や関数を手で数えた表ではない。`—` は、ソース上で対応する公開関数または検証を確認できなかったことを示す。",
        "",
        "| 形式 | 拡張子 | 読む関数 | 書く関数 | 公開 op | 依存 | テスト | 独立の読み手で検証 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    stats = {"read": 0, "write": 0, "pair": 0, "op": 0, "test": 0, "independent": 0}
    for ext in sorted(rows):
        rec = rows[ext]
        public = {f.rsplit(".", 1)[-1] for f in rec["read"] | rec["write"] if f.rsplit(".", 1)[-1] in op_names}
        needles = {ext} | {f.rsplit(".", 1)[-1] for f in rec["read"] | rec["write"]}
        hit_tests = {name for name, src in tests.items() if any(n in src for n in needles)}
        readers = _VERIFY_READERS.get(ext, ())
        independent = {reader for reader in readers
                       if any(_imports_name(src, reader) and any(n in src for n in needles)
                              for src in tests.values())}
        dep = []
        if rec["required"]:
            dep.append("必須: " + ", ".join(sorted(rec["required"])))
        if rec["optional"]:
            dep.append("optional: " + ", ".join(sorted(rec["optional"])))
        if not dep:
            dep.append("stdlib / core")
        stats["read"] += bool(rec["read"])
        stats["write"] += bool(rec["write"])
        stats["pair"] += bool(rec["read"] and rec["write"])
        stats["op"] += bool(public)
        stats["test"] += bool(hit_tests)
        stats["independent"] += bool(independent)
        lines.append("| %s | `%s` | %s | %s | %s | %s | %s | %s |" % (
            FORMAT_NAMES.get(ext, ext[1:].upper()), ext, _short(rec["read"]), _short(rec["write"]),
            _short(public), "<br>".join(dep), _short(hit_tests, 2), _short(independent)))
    lines += [
        "", "## 集計", "",
        (f"形式（拡張子） **{len(rows)}**、読みあり **{stats['read']}**、書きあり **{stats['write']}**、"
         f"読み書き対 **{stats['pair']}**、公開 op あり **{stats['op']}**、テストあり **{stats['test']}**、"
         f"独立の読み手による検証あり **{stats['independent']}**。"),
        "", "集計値も上表から生成しており、文書内に別の手書き件数は持たない。", "",
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="fail if docs/FILE_FORMATS.md differs")
    args = ap.parse_args(argv)
    text = build_report()
    old = OUT.read_text(encoding="utf-8") if OUT.exists() else None
    if args.check:
        if old != text:
            print(f"out of date: {OUT.relative_to(ROOT)}")
            return 1
        return 0
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
