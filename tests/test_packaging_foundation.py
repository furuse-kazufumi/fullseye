"""Foundation guards: the install / packaging + public-API layers must stay correct.

The most foundational layer is "does an installed package actually work". These
guards catch the recurring ship-bug classes cheaply (no wheel build per run):

  * a new root-level RUNTIME module silently dropped from pyproject ``py-modules``
    — has bitten v14 / v18 / v18.3 / v18.5, where a non-editable ``pip install``
    then failed to import the module;
  * a Studio asset type not carried by ``package-data`` (installed Studio then
    degrades to English-only / no help / no sample images);
  * ``fullseye.__all__`` drifting behind ``api.__all__`` (a public symbol vanishes
    under ``from fullseye import *``).

An actual wheel build + isolated-venv install is the gold standard and is done by
hand at release; these static checks keep the base honest between builds.
"""
from __future__ import annotations

import ast
import fnmatch
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Root-level modules that are DEVELOPMENT tools (data-as-code generators / one-shot
# maintenance), legitimately not shipped in the wheel. Everything else at the root
# that a shipped module imports at runtime MUST be in py-modules.
_DEV_TOOLS = {
    "champion_to_macro", "gen_auto_specs_data", "gen_halcon_names_data",
    "recapture_wave0_pins",
}


def _pyproject_text() -> str:
    with open(os.path.join(ROOT, "pyproject.toml"), encoding="utf-8") as f:
        return f.read()


def _py_modules() -> set[str]:
    m = re.search(r"py-modules\s*=\s*\[(.*?)\]", _pyproject_text(), re.S)
    assert m, "py-modules list not found in pyproject.toml"
    return set(re.findall(r'"([^"]+)"', m.group(1)))


def _all_of(relpath: str) -> set[str]:
    with open(os.path.join(ROOT, relpath), encoding="utf-8") as f:
        tree = ast.parse(f.read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets):
            return {el.value for el in node.value.elts if isinstance(el, ast.Constant)}
    return set()


def test_every_runtime_root_module_is_in_py_modules():
    """A root .py imported by a shipped module must ship too (py-modules)."""
    declared = _py_modules()
    shipped_sources = ["api.py", "imgevolve.py", "studio.py", "engine.py",
                       "graphengine.py", "comm.py", "device.py", "dsp.py", "acquire.py",
                       os.path.join("fullseye", "__init__.py")] + [n + ".py" for n in declared]
    root_mods = {os.path.basename(p)[:-3] for p in glob.glob(os.path.join(ROOT, "*.py"))}
    missing = []
    for mod in sorted(root_mods - declared - _DEV_TOOLS):
        pat = re.compile(r"\b(?:import\s+%s\b|from\s+%s\s+import)" % (re.escape(mod), re.escape(mod)))
        for src in shipped_sources:
            p = os.path.join(ROOT, src)
            if os.path.exists(p) and pat.search(open(p, encoding="utf-8", errors="ignore").read()):
                missing.append(mod)
                break
    assert not missing, (
        "root modules imported at runtime but missing from pyproject py-modules "
        "(they would vanish from a non-editable wheel): %s" % missing)


def test_facade_all_covers_api_all():
    """Everything api.py exports must be re-exported by the fullseye facade,
    else `from fullseye import *` silently loses a public symbol."""
    api_all = _all_of("api.py")
    fs_all = _all_of(os.path.join("fullseye", "__init__.py"))
    missing = sorted(api_all - fs_all)
    assert not missing, "api.__all__ names missing from fullseye.__all__: %s" % missing


def test_studio_assets_are_shipped_by_package_data():
    """studio_assets must be a declared package and every tracked asset must match a
    package-data glob (else the installed Studio loses i18n / help / sample images)."""
    txt = _pyproject_text()
    assert re.search(r'packages\s*=\s*\[[^\]]*"studio_assets"', txt), \
        "studio_assets is not a declared package in pyproject.toml"
    m = re.search(r'"studio_assets"\s*=\s*\[(.*?)\]', txt, re.S)
    assert m, "no package-data globs declared for studio_assets"
    globs = re.findall(r'"([^"]+)"', m.group(1))
    tracked = [
        os.path.relpath(p, os.path.join(ROOT, "studio_assets")).replace("\\", "/")
        for p in glob.glob(os.path.join(ROOT, "studio_assets", "**", "*"), recursive=True)
        if os.path.isfile(p) and not p.endswith("__init__.py")
    ]
    assert tracked, "no studio_assets files found"
    unshipped = [f for f in tracked if not any(fnmatch.fnmatch(f, g) for g in globs)]
    assert not unshipped, "studio_assets files not covered by any package-data glob: %s" % unshipped
