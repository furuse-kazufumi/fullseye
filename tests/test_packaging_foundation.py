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


def _read(relpath: str) -> str:
    with open(os.path.join(ROOT, relpath), encoding="utf-8", errors="ignore") as f:
        return f.read()


def _py_modules() -> set[str]:
    m = re.search(r"py-modules\s*=\s*\[(.*?)\]", _read("pyproject.toml"), re.DOTALL)
    assert m, "py-modules list not found in pyproject.toml"
    return set(re.findall(r'"([^"]+)"', m.group(1)))


def _all_of(relpath: str) -> set[str]:
    tree = ast.parse(_read(relpath))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets):
            return {el.value for el in node.value.elts if isinstance(el, ast.Constant)}
    return set()


def test_every_runtime_root_module_is_in_py_modules():
    """A root .py imported by a shipped module must ship too (py-modules)."""
    declared = _py_modules()
    # examples/ examples_3d/ もパッケージとして ship されるため走査対象に含める
    # (公開前監査 2026-08-30: ここを見ていなかったため、サンプルが import する
    # root モジュール 4 件の py-modules 漏れをこのガードが見逃していた)。
    shipped_sources = ["api.py", "imgevolve.py", "studio.py", "engine.py",
                       "graphengine.py", "comm.py", "device.py", "dsp.py", "acquire.py",
                       os.path.join("fullseye", "__init__.py")] + [n + ".py" for n in declared]
    for pkg in ("examples", "examples_3d"):
        shipped_sources += [os.path.relpath(p, ROOT)
                            for p in glob.glob(os.path.join(ROOT, pkg, "*.py"))]
    root_mods = {os.path.basename(p)[:-3] for p in glob.glob(os.path.join(ROOT, "*.py"))}
    missing = []
    for mod in sorted(root_mods - declared - _DEV_TOOLS):
        pat = re.compile(rf"\b(?:import\s+{re.escape(mod)}\b|from\s+{re.escape(mod)}\s+import)")
        for src in shipped_sources:
            if os.path.exists(os.path.join(ROOT, src)) and pat.search(_read(src)):
                missing.append(mod)
                break
    assert not missing, (
        f"root modules imported at runtime but missing from pyproject py-modules "
        f"(they would vanish from a non-editable wheel): {missing}")


def test_facade_all_covers_api_all():
    """Everything api.py exports must be re-exported by the fullseye facade,
    else `from fullseye import *` silently loses a public symbol."""
    missing = sorted(_all_of("api.py") - _all_of(os.path.join("fullseye", "__init__.py")))
    assert not missing, f"api.__all__ names missing from fullseye.__all__: {missing}"


#: 意図的に**同梱しない** studio_assets のサブディレクトリ。ここに足すときは
#: 「出荷コードが読まないこと」を test_article_source_images_do_not_ship で示すこと。
_DELIBERATELY_UNSHIPPED = ("sample_sources_ai/",)


def test_studio_assets_are_shipped_by_package_data():
    """studio_assets must be a declared package and every tracked asset must match a
    package-data glob (else the installed Studio loses i18n / help / sample images).

    例外は :data:`_DELIBERATELY_UNSHIPPED` だけ —— 「全部入れる」を素の不変条件に
    すると、読まない 42 MB を配り続ける理由になってしまう(実測 2026-09-05:
    記事生成用の AI 素材が wheel の 58% を占めていた)。
    """
    txt = _read("pyproject.toml")
    assert re.search(r'packages\s*=\s*\[[^\]]*"studio_assets"', txt), \
        "studio_assets is not a declared package in pyproject.toml"
    m = re.search(r'"studio_assets"\s*=\s*\[(.*?)\]', txt, re.DOTALL)
    assert m, "no package-data globs declared for studio_assets"
    globs = re.findall(r'"([^"]+)"', m.group(1))
    tracked = [
        os.path.relpath(p, os.path.join(ROOT, "studio_assets")).replace("\\", "/")
        for p in glob.glob(os.path.join(ROOT, "studio_assets", "**", "*"), recursive=True)
        if os.path.isfile(p) and not p.endswith("__init__.py")
    ]
    tracked = [f for f in tracked if not f.startswith(_DELIBERATELY_UNSHIPPED)]
    assert tracked, "no studio_assets files found"
    unshipped = [f for f in tracked if not any(fnmatch.fnmatch(f, g) for g in globs)]
    assert not unshipped, f"studio_assets files not covered by any package-data glob: {unshipped}"


def test_article_source_images_do_not_ship():
    """記事生成用の AI 素材(`sample_sources_ai/`)を wheel に入れないこと。

    2026-09-05 実測: 出荷コードからは 1 箇所も読まれない(参照は
    `tools/fops_article/` = 記事生成の開発ツールと docs/ の仕様書だけ)のに、
    **圧縮後 42.1 MB = wheel 全体 72.0 MB の 58%** を占めていた。
    読まないものを配らない。Studio が実際に使うサンプルは `sample_images/` と
    `sample_thumbs/` で、そちらは同梱を続ける。
    """
    toml = _read("pyproject.toml")
    pkg_data = toml.split("[tool.setuptools.package-data]", 1)[1]
    assert '"sample_sources_ai/' not in pkg_data.replace(" ", ""), (
        "sample_sources_ai が package-data に戻っている —— 出荷コードは読まないのに "
        "wheel を 42 MB 太らせる")
    # 読み手がいないことを実際に確かめる(コメントの主張と実装をずらさない)
    import glob as _glob
    shipped = ([os.path.join(ROOT, p) for p in ("studio.py", "api.py", "sample_images.py",
                                                "sample_data.py", "imgevolve.py")]
               + _glob.glob(os.path.join(ROOT, "fullseye", "*.py"))
               + _glob.glob(os.path.join(ROOT, "examples", "*.py"))
               + _glob.glob(os.path.join(ROOT, "examples_3d", "*.py")))
    users = [os.path.relpath(p, ROOT) for p in shipped
             if os.path.exists(p) and "sample_sources_ai" in open(p, encoding="utf-8").read()]
    assert not users, ("出荷コードが sample_sources_ai を読んでいる: %s "
                       "—— 読むなら同梱に戻すこと(この検査を消すのではなく)" % users)


def test_citation_metadata_matches_the_released_version():
    """``CITATION.cff`` の版が ``pyproject.toml`` と一致すること。

    2026-09-05 実測: `version: 0.1.2` のまま 5 版ぶん取り残されていた。リリース手順に
    出てこないファイルは黙って古びる —— 引用した人には**間違った版**が伝わり、
    しかも誰も気づかない(ビルドもテストも読まないので)。

    ``date-released`` は CHANGELOG の最新見出しの日付と揃える。
    """
    import datetime
    cff = _read("CITATION.cff")
    ver = re.search(r"^version:\s*([0-9][^\s#]*)", cff, re.M)
    assert ver, "CITATION.cff に version が無い"
    proj = re.search(r'^version\s*=\s*"([^"]+)"', _read("pyproject.toml"), re.M)
    assert proj, "pyproject.toml に version が無い"
    assert ver.group(1) == proj.group(1), (
        "CITATION.cff の version %s が pyproject の %s と違う "
        "(リリース時に両方あげること)" % (ver.group(1), proj.group(1)))

    rel = re.search(r'^date-released:\s*"?([0-9]{4}-[0-9]{2}-[0-9]{2})"?', cff, re.M)
    assert rel, "CITATION.cff に date-released が無い"
    datetime.date.fromisoformat(rel.group(1))          # 形式が壊れていないこと
    head = re.search(r"^##\s*([0-9][^\s]*)\s*—\s*([0-9]{4}-[0-9]{2}-[0-9]{2})",
                     _read("CHANGELOG.md"), re.M)
    if head and head.group(1) == proj.group(1):        # 未リリース見出しのときは日付を問わない
        assert rel.group(1) == head.group(2), (
            "CITATION.cff の date-released %s が CHANGELOG の %s と違う"
            % (rel.group(1), head.group(2)))
