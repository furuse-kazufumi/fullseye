"""examples/ の PoC は、環境変数 FULLSEYE_FIGURE_DIR が無いときに公開の図(docs/articles/assets/poc)を書かない。

2026-10-31: 深い光学の PoC 3 本が実行のたびに fig.savefig で docs/ の PNG を上書きしていた。CI でテストが
PoC を走らせると Linux の matplotlib で PNG が変わり、それを見たサムネ(_720.jpg)が作り直されて
regen_all --check が落ちた(SFR・波面)。書き先を docs/ に向ける PoC は、規約の環境変数で守ること。
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DOCS_OUT = re.compile(r"docs/articles/assets/poc|[\"']articles[\"']\s*/\s*[\"']assets")


def test_pocs_that_target_published_assets_are_guarded():
    bad = []
    for f in sorted(os.listdir(os.path.join(ROOT, "examples"))):
        if not f.endswith(".py"):
            continue
        src = open(os.path.join(ROOT, "examples", f), encoding="utf-8").read()
        if _DOCS_OUT.search(src) and re.search(r"savefig\(|write_text\(|imwrite\(", src) \
                and "FULLSEYE_FIGURE_DIR" not in src:
            bad.append(f)
    assert not bad, "docs/ の公開図を環境変数なしで書く PoC: " + ", ".join(bad)


def test_running_a_guarded_poc_leaves_published_png_untouched(tmp_path, monkeypatch):
    import importlib.util
    import sys
    monkeypatch.delenv("FULLSEYE_FIGURE_DIR", raising=False)
    png = os.path.join(ROOT, "docs", "articles", "assets", "poc", "poc_mueller_dofp_observability", "01_observability.png")
    before = open(png, "rb").read() if os.path.exists(png) else None
    p = os.path.join(ROOT, "examples", "poc_mueller_dofp_observability.py")
    spec = importlib.util.spec_from_file_location("poc_mueller_guard", p)
    m = importlib.util.module_from_spec(spec)
    sys.modules["poc_mueller_guard"] = m
    spec.loader.exec_module(m)
    assert not str(m.OUT).replace("\\", "/").endswith("docs/articles/assets/poc/poc_mueller_dofp_observability")
    if before is not None:
        assert open(png, "rb").read() == before
