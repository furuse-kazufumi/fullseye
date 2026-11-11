"""tools/pages_site.py(Pages の配備物から参照されない assets を外す道具)のテスト(2026-11-11)。

legacy 方式の配備物が 1.54 GB になり、上限 1 GB を超えて deploy が 10 分で落ちた。Actions 方式に変え、
組んだ ``_site`` から参照されない ``articles/assets/**`` を外してから配備する(.github/workflows/pages.yml)。
ここでは小さな偽のサイトで、緩い読み方(prune)と厳密な読み方(check)の両方を、内側の関数と CLI で通す。
"""
import importlib.util
import json
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tools", "pages_site.py")
_spec = importlib.util.spec_from_file_location("pages_site", TOOL)
ps = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ps)

A = "articles/assets/"

#: 参照のしかた → それで参照される assets(残るべきもの)。
REFERENCED = {
    "img_src": A + "img_src.png",
    "srcset_1x": A + "s1.png",
    "srcset_2x": A + "s2.png",
    "srcset_640w": A + "w640.png",
    "srcset_1280w": A + "w1280.png",
    "source_src": A + "clip.mp4",
    "poster": A + "poster.png",
    "data_src": A + "lazy.gif",
    "css_file_url": A + "bg_css.png",
    "style_attr_url": A + "bg_attr.png",
    "style_tag_url": A + "bg_tag.png",
    "abs_furuse": A + "abs1.gif",
    "abs_github_io": A + "abs2.gif",
    "root_relative": A + "rootrel.png",
    "nested_dotdot": A + "deep/nested.png",
    "pct_space": A + "with space.png",
    "pct_japanese": A + "日本語.png",
    "query": A + "q.png",
    "fragment": A + "frag.svg",
    "amp_entity": A + "a&b.png",
    "a_href": A + "download.zip",
    "link_href": A + "style.css",
    "script_src": A + "app.js",
}
UNREFERENCED = [A + "unused.png", A + "poc/big/unused.gif", A + "UPPER.png"]
OUTSIDE = ["ops/_fig/unreferenced.png", "articles/unreferenced.md.txt", "orphan.png"]

INDEX_HTML = """<!doctype html><html><head>
<link rel="stylesheet" href="articles/assets/style.css">
<script src="/articles/assets/app.js"></script>
<style>.x{background:url("articles/assets/bg_tag.png")}</style>
</head><body>
<img src="articles/assets/img_src.png">
<img srcset="articles/assets/s1.png 1x, articles/assets/s2.png 2x" src="articles/assets/img_src.png">
<img srcset="articles/assets/w640.png 640w,articles/assets/w1280.png 1280w">
<video poster="articles/assets/poster.png"><source src="articles/assets/clip.mp4" type="video/mp4"></video>
<img data-src="articles/assets/lazy.gif">
<div style="background-image:url('articles/assets/bg_attr.png')"></div>
<img src="https://furuse.work/articles/assets/abs1.gif">
<img src="https://furuse-kazufumi.github.io/fullseye/articles/assets/abs2.gif">
<img src="/articles/assets/rootrel.png">
<img src="articles/assets/with%20space.png">
<img src="articles/assets/%E6%97%A5%E6%9C%AC%E8%AA%9E.png">
<img src="articles/assets/q.png?v=3">
<img src="articles/assets/frag.svg#icon">
<img src="articles/assets/a&amp;b.png">
<img src="articles/assets/upper.png">
<a href="articles/assets/download.zip">zip</a>
<a href="view2026/">ViEW</a>
<a href="no/such/page.html">broken</a>
<a href="https://example.com/x.png">external</a>
<a href="#top">self</a>
</body></html>
"""
NESTED_HTML = '<html><body><img src="../../articles/assets/deep/nested.png"></body></html>'
CSS = ".bg{background:url(../assets/bg_css.png)}\n"


def make_site(root):
    """偽のサイト(``_site``)と、同じ中身の repo の docs を作る。(site, docs) を返す。"""
    site = root / "_site"
    docs = root / "docs"
    files = {
        "index.html": INDEX_HTML,
        "view2026/index.html": "<html><body>ok</body></html>",
        "view2026/ja/page.html": NESTED_HTML,
        "articles/css/site.css": CSS,
        "CNAME": "furuse.work\n",
    }
    blobs = list(REFERENCED.values()) + UNREFERENCED + OUTSIDE
    for base in (site, docs):
        for rel, text in files.items():
            p = base / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
        for i, rel in enumerate(blobs):
            p = base / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"x" * (100 + i))
    return site, docs


def site_files(site):
    return set(ps.walk_files(str(site)))


def run_cli(*args):
    return subprocess.run([sys.executable, TOOL, *args], capture_output=True, text=True,
                          encoding="utf-8", timeout=120)


def check_args(site, docs, max_bytes=10**9, min_pages=1, min_kept=1, extra=()):
    return ["check", "--site", str(site), "--source-docs", str(docs), "--max-bytes", str(max_bytes),
            "--min-pages", str(min_pages), "--min-kept-assets", str(min_kept), *extra]


# ---- prune(緩い読み方) ----

@pytest.mark.parametrize("kind", sorted(REFERENCED))
def test_each_reference_kind_keeps_its_asset(tmp_path, kind):
    site, _docs = make_site(tmp_path)
    plan = ps.plan_prune(str(site))
    assert REFERENCED[kind] not in plan["remove"], kind
    ps.apply_prune(str(site), plan["remove"])
    assert REFERENCED[kind] in site_files(site), kind


def test_unreferenced_assets_are_removed_and_outside_is_untouched(tmp_path):
    site, _docs = make_site(tmp_path)
    plan = ps.plan_prune(str(site))
    assert sorted(plan["remove"]) == sorted(UNREFERENCED)
    ps.apply_prune(str(site), plan["remove"])
    after = site_files(site)
    assert not (set(UNREFERENCED) & after)
    for rel in OUTSIDE + ["CNAME", "index.html"]:
        assert rel in after, rel
    # 空になったディレクトリは消える(assets の下だけ)
    assert not (site / "articles" / "assets" / "poc").exists()
    assert (site / "articles" / "assets").is_dir()


def test_case_only_difference_is_not_a_reference(tmp_path):
    # index.html は upper.png を参照し、実在するのは UPPER.png。Linux の配信では 404 なので残さない。
    site, _docs = make_site(tmp_path)
    plan = ps.plan_prune(str(site))
    assert A + "UPPER.png" in plan["remove"]
    files = ps.walk_files(str(site))
    assert A + "upper.png" not in files  # os.walk の集合は大文字小文字を区別する


def test_without_apply_nothing_is_removed_cli(tmp_path):
    site, _docs = make_site(tmp_path)
    before = site_files(site)
    rep_path = tmp_path / "prune.json"
    r = run_cli("prune", "--site", str(site), "--report-json", str(rep_path))
    assert r.returncode == 0, r.stderr
    assert site_files(site) == before
    rep = json.loads(rep_path.read_text(encoding="utf-8"))
    assert rep["applied"] is False
    assert rep["removed_assets"] == len(UNREFERENCED)


def test_prune_report_json_fields_cli(tmp_path):
    site, _docs = make_site(tmp_path)
    rep_path = tmp_path / "prune.json"
    md = tmp_path / "summary.md"
    r = run_cli("prune", "--site", str(site), "--apply", "--report-json", str(rep_path), "--summary-md", str(md))
    assert r.returncode == 0, r.stderr
    rep = json.loads(rep_path.read_text(encoding="utf-8"))
    for key in ("texts_read", "html_pages", "kept_assets", "kept_assets_bytes", "removed_assets",
                "removed_assets_bytes", "site_bytes_before", "site_bytes_after", "applied", "seconds", "remove",
                "kept_largest"):
        assert key in rep, key
    assert rep["applied"] is True
    assert rep["html_pages"] == 3
    # html 3 + site.css + unreferenced.md.txt + assets の中の style.css・app.js・frag.svg(assets も読む)。CNAME は読まない。
    assert rep["texts_read"] == 8
    assert rep["kept_assets"] == len(set(REFERENCED.values()))
    assert rep["removed_assets"] == len(UNREFERENCED)
    after = ps.walk_files(str(site))
    assert rep["site_bytes_after"] == sum(after.values())
    assert rep["site_bytes_before"] - rep["removed_assets_bytes"] == rep["site_bytes_after"]
    assert "残した assets" in md.read_text(encoding="utf-8")
    sizes = [b for _p, b in rep["kept_largest"]]
    assert sizes == sorted(sizes, reverse=True) and len(sizes) == rep["kept_assets"]


def test_apply_prune_refuses_paths_outside_assets(tmp_path):
    site, _docs = make_site(tmp_path)
    with pytest.raises(ps.SiteError):
        ps.apply_prune(str(site), ["orphan.png"])
    assert (site / "orphan.png").exists()


# ---- check(厳密な読み方) ----

def test_check_passes_after_prune(tmp_path):
    site, docs = make_site(tmp_path)
    ps.apply_prune(str(site), ps.plan_prune(str(site))["remove"])
    rep = ps.run_check(str(site), str(docs), 10**9, 1, 1)
    assert rep["ok"], rep["gates"]
    assert rep["missing_assets"] == []
    assert rep["html_pages"] == 3


@pytest.mark.parametrize("kind", sorted(REFERENCED))
def test_check_sees_each_reference_kind_when_its_asset_is_deleted(tmp_path, kind):
    """厳密な読み方が、どの参照のしかたでも欠けを見つける(属性を 1 つ抜くとここで落ちる)。"""
    site, docs = make_site(tmp_path)
    os.remove(os.path.join(site, *REFERENCED[kind].split("/")))
    rep = ps.run_check(str(site), str(docs), 10**9, 1, 1)
    assert not rep["gates"]["gate1_assets_present"], kind
    assert REFERENCED[kind] in {m["target"] for m in rep["missing_assets"]}


def test_check_cli_fails_and_names_the_referring_page(tmp_path):
    site, docs = make_site(tmp_path)
    os.remove(site / "articles" / "assets" / "deep" / "nested.png")
    r = run_cli(*check_args(site, docs))
    assert r.returncode == 1
    assert "view2026/ja/page.html" in r.stderr
    assert "articles/assets/deep/nested.png" in r.stderr


def test_check_ignores_assets_not_in_repo(tmp_path):
    # 門 1 の真値は repo。repo に無い assets への参照(元から切れている)は門 1 では数えない。
    site, docs = make_site(tmp_path)
    os.remove(docs / "articles" / "assets" / "img_src.png")
    os.remove(site / "articles" / "assets" / "img_src.png")
    rep = ps.run_check(str(site), str(docs), 10**9, 1, 1)
    assert rep["gates"]["gate1_assets_present"]


def test_broken_internal_links_are_reported_not_gated(tmp_path):
    site, docs = make_site(tmp_path)
    rep = ps.run_check(str(site), str(docs), 10**9, 1, 1)
    assert rep["ok"]
    targets = {b["target"] for b in rep["broken_internal_links"]}
    # upper.png(実在は UPPER.png)は repo でも解決できない assets への参照なので、黙って捨てず切れたリンクに数える
    assert targets == {"no/such/page.html", "articles/assets/upper.png"}
    assert rep["broken_internal_links_count"] == 2


def test_size_gate_boundary(tmp_path):
    site, docs = make_site(tmp_path)
    files = ps.walk_files(str(site))
    total = sum(files.values()) + len(files) * ps.TAR_HEADER_BYTES  # 門 2 は tar の見出しの見積もり込み
    assert ps.run_check(str(site), str(docs), total, 1, 1)["gates"]["gate2_size"]  # ちょうどは通る
    rep = ps.run_check(str(site), str(docs), total - 1, 1, 1)
    assert not rep["gates"]["gate2_size"] and not rep["ok"]
    assert rep["margin_bytes"] == -1
    assert run_cli(*check_args(site, docs, max_bytes=total)).returncode == 0
    assert run_cli(*check_args(site, docs, max_bytes=total - 1)).returncode == 1


def test_floor_gates(tmp_path):
    site, docs = make_site(tmp_path)
    assert ps.run_check(str(site), str(docs), 10**9, 3, 1)["gates"]["gate3_min_pages"]
    assert not ps.run_check(str(site), str(docs), 10**9, 4, 1)["gates"]["gate3_min_pages"]
    n_assets = sum(1 for p in ps.walk_files(str(site)) if p.startswith(A))
    assert ps.run_check(str(site), str(docs), 10**9, 1, n_assets)["gates"]["gate3_min_kept_assets"]
    (docs / "articles" / "assets" / "extra_in_repo.png").write_bytes(b"x")  # --source-docs の床を満たす
    assert not ps.run_check(str(site), str(docs), 10**9, 1, n_assets + 1)["gates"]["gate3_min_kept_assets"]


def test_floor_gates_red_on_empty_site_and_wrong_directory(tmp_path):
    site, docs = make_site(tmp_path)
    empty = tmp_path / "empty"
    empty.mkdir()
    r = run_cli(*check_args(empty, docs))
    assert r.returncode == 1  # ページ 0・assets 0
    rep_path = tmp_path / "c.json"
    run_cli(*check_args(empty, docs, extra=("--report-json", str(rep_path))))
    rep = json.loads(rep_path.read_text(encoding="utf-8"))
    assert not rep["gates"]["gate3_min_pages"] and not rep["gates"]["gate3_min_kept_assets"]
    # assets だけ消えたサイト(ページはある)
    for rel in ps.walk_files(str(site)):
        if rel.startswith(A):
            os.remove(os.path.join(site, *rel.split("/")))
    rep = ps.run_check(str(site), str(docs), 10**9, 1, 1)
    assert not rep["gates"]["gate3_min_kept_assets"]
    # 無いディレクトリ
    assert run_cli(*check_args(tmp_path / "nope", docs)).returncode == 2
    assert run_cli("prune", "--site", str(tmp_path / "nope")).returncode == 2


def test_floor_of_zero_is_refused(tmp_path):
    site, docs = make_site(tmp_path)
    assert run_cli(*check_args(site, docs, min_pages=0)).returncode == 2
    assert run_cli(*check_args(site, docs, min_kept=0)).returncode == 2


def test_check_report_json_fields_cli(tmp_path):
    site, docs = make_site(tmp_path)
    rep_path = tmp_path / "c.json"
    md = tmp_path / "s.md"
    r = run_cli(*check_args(site, docs, extra=("--report-json", str(rep_path), "--summary-md", str(md))))
    assert r.returncode == 0, r.stdout + r.stderr
    rep = json.loads(rep_path.read_text(encoding="utf-8"))
    for key in ("html_pages", "strict_references", "strict_asset_references", "kept_assets", "kept_assets_bytes",
                "site_bytes", "max_bytes", "margin_bytes", "missing_assets", "broken_internal_links_count",
                "broken_internal_links", "gates", "ok", "seconds"):
        assert key in rep, key
    assert set(rep["gates"]) == {"gate1_assets_present", "gate2_size", "gate3_min_pages", "gate3_min_kept_assets",
                                 "gate4_page_wiring"}
    assert rep["strict_asset_references"] >= len(set(REFERENCED.values()))
    assert "門 1" in md.read_text(encoding="utf-8")


# ---- 小道具 ----

def test_parse_srcset_and_css_urls():
    assert ps.parse_srcset("a.png 1x, b.png 2x") == ["a.png", "b.png"]
    assert ps.parse_srcset(" a.png  640w ,b.png 1280w") == ["a.png", "b.png"]
    assert ps.css_urls("url(a.png) url('b c.png') url(\"d.png\")") == ["a.png", "b c.png", "d.png"]


def test_strict_resolve():
    r = ps.strict_resolve
    assert r("view2026/ja/index.html", "../../articles/assets/x.png") == "articles/assets/x.png"
    assert r("a/b.html", "/articles/assets/x.png?v=1#f") == "articles/assets/x.png"
    assert r("a/b.html", "https://FURUSE.work/articles/assets/x.png") == "articles/assets/x.png"
    assert r("a/b.html", "https://example.com/x.png") is None
    assert r("a/b.html", "mailto:x@example.com") is None
    assert r("a/b.html", "#top") is None
    # 根を越える ../ はブラウザと同じく根で止める(サイトの根の外へは出ない。2026-11-11 の R1 a で
    # 「None」から直した。None にすると、ブラウザが読む assets を prune が消して check が通した)
    assert r("a/b.html", "../../../etc/passwd") == "etc/passwd"
    assert r("index.html", "../articles/assets/x.png") == "articles/assets/x.png"
    assert r("index.html", "../") == ""
    assert r("a/b.html", "c%20d.png") == "a/c d.png"


def test_loose_reads_json_js_text_and_quoted_names(tmp_path):
    """緩い読み方の拾い方を 1 つずつ要る形で通す(どれか 1 つを抜くと、ここで 1 本が消える)。"""
    site = tmp_path / "s"
    (site / "articles" / "assets").mkdir(parents=True)
    names = ("j1.png", "j2.png", "js.png", "j3.png", "日本.png", "j&k.png", "ent&x.png", "sp ace.png")
    for n in names:
        (site / "articles" / "assets" / n).write_bytes(b"x")
    (site / "articles" / "assets" / "unused.png").write_bytes(b"x")
    # json: \u で書いた日本語の名前(json として読まないと拾えない)と、HTML の実体参照のまま入った名前
    # (& も & で書く = 本文の実体参照を外しても拾えず、json の文字列の実体参照を外して初めて拾える)
    (site / "data.json").write_text(json.dumps({"a": ["articles/assets/j1.png", "articles/assets/日本.png"],
                                                "b": "articles/assets/j3.png", "c": "articles/assets/j&amp;k.png"},
                                               ensure_ascii=True).replace("&", "\\u0026"), encoding="utf-8")
    # js: \/ で書いた区切り(字句はバックスラッシュで切れる)と、テンプレート文字列
    (site / "app.js").write_text('const v = "articles\\/assets\\/j2.png"; load(`/articles/assets/js.png`)',
                                 encoding="utf-8")
    # 引用符の外の実体参照(字句は ; で切れる)
    (site / "notes.txt").write_text("see articles/assets/ent&amp;x.png\n", encoding="utf-8")
    # 引用符の中の空白入りの名前(字句は空白で切れる)
    (site / "page.html").write_text('<img src="articles/assets/sp ace.png">', encoding="utf-8")
    plan = ps.plan_prune(str(site))
    assert plan["remove"] == ["articles/assets/unused.png"]


def test_references_count_only_from_files_that_stay(tmp_path):
    """参照されない assets の中の json が隣の gif を並べていても、残す理由にしない(json ごと消える)。
    参照された assets の中の json(や svg)が並べるものは残す(到達できるものの閉包)。"""
    site = tmp_path / "s"
    for d in ("articles/assets/dead", "articles/assets/live"):
        (site / d).mkdir(parents=True)
    (site / "articles/assets/dead/manifest.json").write_text('{"f": "a.gif"}', encoding="utf-8")
    (site / "articles/assets/dead/a.gif").write_bytes(b"x")
    (site / "articles/assets/live/manifest.json").write_text('{"f": "b.gif"}', encoding="utf-8")
    (site / "articles/assets/live/b.gif").write_bytes(b"x")
    (site / "articles/assets/live/icon.svg").write_text('<svg><image href="c.png"/></svg>', encoding="utf-8")
    (site / "articles/assets/live/c.png").write_bytes(b"x")
    (site / "index.html").write_text('<a href="articles/assets/live/manifest.json">m</a>'
                                     '<img src="articles/assets/live/icon.svg">', encoding="utf-8")
    plan = ps.plan_prune(str(site))
    assert plan["remove"] == ["articles/assets/dead/a.gif", "articles/assets/dead/manifest.json"]


# ---- workflow(.github/workflows/pages.yml)----

WF_DIR = os.path.join(ROOT, ".github", "workflows")
PAGES_WF = os.path.join(WF_DIR, "pages.yml")
#: 門 3 の床(2026-11-11 に実物 = 8bc7ab22f7 を GitHub が組んだ _site で測った値のおよそ半分)。
#: workflow の値がこれより下がったら落とす。下げるなら実物で測り直し、理由と日付を workflow に書いてから。
FLOOR_PAGES = 2200
FLOOR_KEPT = 400


def _pages_wf():
    yaml = pytest.importorskip("yaml")
    with open(PAGES_WF, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _steps(job):
    return _pages_wf()["jobs"][job]["steps"]


def test_pages_workflow_triggers_and_top_permissions():
    wf = _pages_wf()
    on = wf.get("on", wf.get(True))  # YAML 1.1 は on を True と読む
    want = {"docs/**", ".github/workflows/pages.yml", "tools/pages_site.py"}
    assert on["push"]["branches"] == ["master"]
    assert set(on["push"]["paths"]) == want
    assert set(on["pull_request"]["paths"]) == want
    assert "workflow_dispatch" in on
    assert wf["permissions"] == {"contents": "read"}
    # 組むジョブは読むだけ(jekyll-build-pages の github-metadata が Pages の cname を読むのに pages: read が要る)。
    assert wf["jobs"]["build"]["permissions"] == {"contents": "read", "pages": "read"}, "組むジョブに書き込みの権限を足さない"


def test_deploy_job_runs_only_on_master_outside_pull_requests():
    job = _pages_wf()["jobs"]["deploy"]
    assert job["needs"] == "build"
    assert "github.event_name != 'pull_request'" in job["if"]
    assert "github.ref == 'refs/heads/master'" in job["if"]
    assert job["permissions"] == {"pages": "write", "id-token": "write"}
    assert job["environment"]["name"] == "github-pages"
    assert "steps.deployment.outputs.page_url" in job["environment"]["url"]
    dep = [s for s in job["steps"] if s.get("id") == "deployment"]
    assert len(dep) == 1 and dep[0]["uses"].startswith("actions/deploy-pages@")


def test_build_job_builds_prunes_checks_then_uploads_in_order():
    steps = _steps("build")
    def idx(pred):
        hits = [i for i, s in enumerate(steps) if pred(s)]
        assert len(hits) == 1, hits
        return hits[0]
    i_jek = idx(lambda s: s.get("uses", "").startswith("actions/jekyll-build-pages@"))
    i_own = idx(lambda s: "chown -R" in s.get("run", ""))
    i_snap = idx(lambda s: "pages_site.py snapshot" in s.get("run", ""))
    i_prune = idx(lambda s: "pages_site.py prune" in s.get("run", ""))
    i_check = idx(lambda s: "pages_site.py check" in s.get("run", ""))
    i_up = idx(lambda s: s.get("uses", "").startswith("actions/upload-pages-artifact@"))
    assert i_jek < i_own < i_snap < i_prune < i_check < i_up
    assert steps[i_jek]["with"] == {"source": "./docs", "destination": "./_site"}
    assert "--apply" in steps[i_prune]["run"]
    assert steps[i_up]["with"]["path"] == "_site"
    for i in (i_own, i_snap, i_prune, i_check):
        assert "if" not in steps[i] and not steps[i].get("continue-on-error"), steps[i]


def test_check_step_carries_the_size_limit_and_the_floors():
    run = next(s["run"] for s in _steps("build") if "pages_site.py check" in s.get("run", ""))
    def arg(name):
        m = re.search(r"--%s\s+(\d+)" % name, run)
        assert m, name
        return int(m.group(1))
    assert arg("max-bytes") == 1_000_000_000  # GitHub の上限 1 GB。結果を見て動かさない
    assert arg("min-pages") >= FLOOR_PAGES
    assert arg("min-kept-assets") >= FLOOR_KEPT
    assert "--source-docs docs" in run
    assert "--built-list pages-built.txt" in run


def test_pages_workflow_puts_no_expression_inside_run():
    for job, jd in _pages_wf()["jobs"].items():
        for s in jd.get("steps") or []:
            assert "${{" not in s.get("run", ""), (job, s.get("name"))


def test_every_action_in_every_workflow_is_pinned_to_a_commit_sha():
    n = 0
    for name in sorted(os.listdir(WF_DIR)):
        if not name.endswith((".yml", ".yaml")):
            continue
        with open(os.path.join(WF_DIR, name), encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                m = re.match(r"^\s*(?:-\s+)?uses:\s*(\S+)(.*)$", line)
                if not m:
                    continue
                n += 1
                assert re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", m.group(1)), (name, lineno, line)
                assert re.match(r"\s+#\s*v\d", m.group(2)), ("版の注記が無い", name, lineno, line)
    assert n >= 30, n  # 読み方が壊れて 0 本で通るのを防ぐ


def test_snapshot_and_built_list_separate_names_jekyll_never_served(tmp_path):
    """repo にあっても組んだ直後のサイトに無いもの(Jekyll が配信しない _ 始まり)は、--built-list を渡すと
    門 1 でなく報告に分かれる。prune が消したものは --built-list を渡しても門 1 で落ちる。"""
    site, docs = make_site(tmp_path)
    (docs / "articles" / "assets" / "_snippet.md").write_text("x", encoding="utf-8")
    page = site / "view2026" / "index.html"
    page.write_text('<a href="../articles/assets/_snippet.md">s</a>', encoding="utf-8")
    lst = tmp_path / "built.txt"
    r = run_cli("snapshot", "--site", str(site), "--out", str(lst))
    assert r.returncode == 0, r.stderr
    built = set(lst.read_text(encoding="utf-8").splitlines())
    assert built == site_files(site)
    # 渡さなければ repo だけが真値(厳しい側)
    assert run_cli(*check_args(site, docs)).returncode == 1
    rep_path = tmp_path / "c.json"
    r = run_cli(*check_args(site, docs, extra=("--built-list", str(lst), "--report-json", str(rep_path))))
    assert r.returncode == 0, r.stdout + r.stderr
    rep = json.loads(rep_path.read_text(encoding="utf-8"))
    assert rep["built_list_used"] is True
    assert [m["target"] for m in rep["not_built_assets"]] == ["articles/assets/_snippet.md"]
    assert rep["not_built_assets_count"] == 1
    # 組んだ後に消えたもの(一覧にはある)は門 1 で落ちる
    os.remove(site / "articles" / "assets" / "poster.png")
    r = run_cli(*check_args(site, docs, extra=("--built-list", str(lst))))
    assert r.returncode == 1 and "articles/assets/poster.png" in r.stderr


def test_built_list_and_snapshot_refuse_empty(tmp_path):
    site, docs = make_site(tmp_path)
    empty = tmp_path / "empty.txt"
    empty.write_text("", encoding="utf-8")
    assert run_cli(*check_args(site, docs, extra=("--built-list", str(empty)))).returncode == 2
    assert run_cli(*check_args(site, docs, extra=("--built-list", str(tmp_path / "nope.txt")))).returncode == 2
    (tmp_path / "e").mkdir()
    assert run_cli("snapshot", "--site", str(tmp_path / "e"), "--out", str(tmp_path / "o.txt")).returncode == 2


# ---- 門 4(ページの組み方: stylesheet・script・baseurl)----

THEME_HEAD = ('<html><head><title>T | fullseye</title><meta name="generator" content="Jekyll v3.10.0">'
              '<link rel="canonical" href="https://furuse.work/view2026/">'
              '<meta property="og:url" content="https://furuse.work/view2026/">'
              '<link rel="Stylesheet" href="/assets/css/style.css?v=abc#x">'  # rel は大文字小文字を区別しない
              '<script src="https://cdn.example.com/x.js"></script></head><body>ok</body></html>')


def make_themed_site(tmp_path):
    site, docs = make_site(tmp_path)
    for base in (site, docs):
        (base / "assets" / "css").mkdir(parents=True)
        (base / "assets" / "css" / "style.css").write_text("body{}", encoding="utf-8")
        (base / "view2026" / "index.html").write_text(THEME_HEAD, encoding="utf-8")
    return site, docs


def test_gate4_passes_on_a_well_wired_site_and_writes_the_build_sample(tmp_path):
    site, docs = make_themed_site(tmp_path)
    md = tmp_path / "s.md"
    r = run_cli(*check_args(site, docs, extra=("--summary-md", str(md))))
    assert r.returncode == 0, r.stdout + r.stderr
    rep = ps.run_check(str(site), str(docs), 10**9, 1, 1)
    assert rep["gates"]["gate4_page_wiring"]
    assert rep["wiring_internal_stylesheets"] == 2  # index.html と view2026/index.html
    smp = rep["build_samples"]["view2026/index.html"]
    assert smp == {"stylesheet": ["/assets/css/style.css?v=abc#x"], "canonical": "https://furuse.work/view2026/",
                   "og:url": "https://furuse.work/view2026/", "title": "T | fullseye", "generator": "Jekyll v3.10.0"}
    text = md.read_text(encoding="utf-8")
    assert "組み方の見本" in text and "`view2026/index.html` canonical: `https://furuse.work/view2026/`" in text


def test_gate4_fails_when_the_theme_css_is_missing(tmp_path):
    site, docs = make_themed_site(tmp_path)
    os.remove(site / "assets" / "css" / "style.css")
    r = run_cli(*check_args(site, docs))
    assert r.returncode == 1
    assert "WIRING view2026/index.html stylesheet" in r.stderr and "assets/css/style.css" in r.stderr
    rep = ps.run_check(str(site), str(docs), 10**9, 1, 1)
    assert not rep["gates"]["gate4_page_wiring"]
    assert rep["gates"]["gate1_assets_present"]  # assets の外なので門 1 では見えない(門 4 の役目)


def test_gate4_fails_when_an_internal_script_is_missing(tmp_path):
    site, docs = make_themed_site(tmp_path)
    os.remove(site / "articles" / "assets" / "app.js")
    rep = ps.run_check(str(site), str(docs), 10**9, 1, 1)
    assert not rep["gates"]["gate4_page_wiring"]
    assert {(m["kind"], m["target"]) for m in rep["wiring_missing"]} == {("script", "articles/assets/app.js")}


def test_gate4_fails_on_a_baseurl_fallen_to_the_repo_name(tmp_path):
    # url/baseurl が https://<owner>.github.io/fullseye に倒れると、全ページの CSS が /fullseye/... になる
    site, docs = make_themed_site(tmp_path)
    fallen = THEME_HEAD.replace('href="/assets/css/style.css', 'href="/fullseye/assets/css/style.css')
    (site / "view2026" / "index.html").write_text(fallen, encoding="utf-8")
    r = run_cli(*check_args(site, docs))
    assert r.returncode == 1
    assert "BASEURL view2026/index.html -> /fullseye/assets/css/style.css" in r.stderr
    rep = ps.run_check(str(site), str(docs), 10**9, 1, 1)
    assert rep["baseurl_prefixed_pages_count"] == 1


def test_gate4_counts_fullseye_prefix_even_when_the_file_exists(tmp_path):
    # 実在しても /fullseye/ 前置は furuse.work では 404 になる配置の印なので落とす(欠けの数とは別に数える)
    site, docs = make_themed_site(tmp_path)
    (site / "fullseye" / "x").mkdir(parents=True)
    (site / "fullseye" / "x" / "a.png").write_bytes(b"x")
    (site / "view2026" / "index.html").write_text(THEME_HEAD + '<img src="/fullseye/x/a.png">', encoding="utf-8")
    rep = ps.run_check(str(site), str(docs), 10**9, 1, 1)
    assert rep["wiring_missing"] == [] and rep["baseurl_prefixed_pages_count"] == 1
    assert not rep["gates"]["gate4_page_wiring"]


def test_gate4_fails_on_a_site_without_any_internal_stylesheet(tmp_path):
    # 空を通さない: サイト内の stylesheet が 0 本(テーマが付かなかった)なら落とす
    site, docs = make_site(tmp_path)
    idx = site / "index.html"
    idx.write_text(idx.read_text(encoding="utf-8").replace('rel="stylesheet" ', 'rel="preload" '), encoding="utf-8")
    rep = ps.run_check(str(site), str(docs), 10**9, 1, 1)
    assert rep["wiring_internal_stylesheets"] == 0
    assert rep["wiring_missing"] == [] and rep["baseurl_prefixed_pages_count"] == 0
    assert not rep["gates"]["gate4_page_wiring"]


# ---- 独立レビューの指摘(2026-11-11)----

def _write(base, rel, text="x"):
    p = base / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_f1_directory_and_extensionless_asset_pages_are_kept_and_checked(tmp_path):
    """href が assets の下のディレクトリ(index.html)・拡張子なし(.html)を指す形。prune が残し、消えたら門 1。"""
    site, docs = make_site(tmp_path)
    for base in (site, docs):
        _write(base, A + "demo/index.html", "<p>demo</p>")
        _write(base, A + "page.html", "<p>page</p>")
    _write(site, "links.html", '<a href="/articles/assets/demo/">d</a><a href="/articles/assets/page">p</a>')
    plan = ps.plan_prune(str(site))
    assert A + "demo/index.html" not in plan["remove"] and A + "page.html" not in plan["remove"]
    lst = tmp_path / "built.txt"
    assert run_cli("snapshot", "--site", str(site), "--out", str(lst)).returncode == 0
    for rel in (A + "demo/index.html", A + "page.html"):
        os.remove(os.path.join(site, *rel.split("/")))
        r = run_cli(*check_args(site, docs, extra=("--built-list", str(lst))))
        assert r.returncode == 1, rel
        assert "links.html" in r.stderr
        _write(site, rel, "<p>back</p>")


def test_f1_unresolvable_asset_reference_is_counted_as_broken(tmp_path):
    site, docs = make_site(tmp_path)
    _write(site, "links.html", '<img src="/articles/assets/nowhere.png">')
    rep = ps.run_check(str(site), str(docs), 10**9, 1, 1)
    assert rep["ok"]
    assert "articles/assets/nowhere.png" in {b["target"] for b in rep["broken_internal_links"]}
    built = set(ps.walk_files(str(site)))  # 一覧を渡しても、どこにも無いものは切れたリンクに数える
    rep = ps.run_check(str(site), str(docs), 10**9, 1, 1, built=built)
    assert rep["ok"] and "articles/assets/nowhere.png" in {b["target"] for b in rep["broken_internal_links"]}


def test_f2a_built_list_must_cover_the_site(tmp_path):
    site, docs = make_site(tmp_path)
    lst = tmp_path / "built.txt"
    lst.write_text("index.html\n", encoding="utf-8")  # 無関係な・prune の後に取った一覧
    r = run_cli(*check_args(site, docs, extra=("--built-list", str(lst))))
    assert r.returncode == 2 and "--built-list" in r.stderr


def test_f2b_only_underscore_or_dot_names_may_be_not_built(tmp_path):
    site, docs = make_site(tmp_path)
    _write(docs, A + "plain_missing.md")
    _write(docs, A + "_hidden.md")
    _write(docs, A + ".dot/x.md")
    _write(site, "links.html", '<a href="articles/assets/_hidden.md">h</a><a href="articles/assets/.dot/x.md">d</a>')
    lst = tmp_path / "built.txt"
    assert run_cli("snapshot", "--site", str(site), "--out", str(lst)).returncode == 0
    rep = ps.run_check(str(site), str(docs), 10**9, 1, 1, built=set(lst.read_text(encoding="utf-8").splitlines()))
    assert rep["ok"] and rep["not_built_assets_count"] == 2
    _write(site, "links2.html", '<a href="articles/assets/plain_missing.md">p</a>')
    built = set(lst.read_text(encoding="utf-8").splitlines()) | {"links2.html"}
    rep = ps.run_check(str(site), str(docs), 10**9, 1, 1, built=built)
    assert not rep["gates"]["gate1_assets_present"]
    assert [m["target"] for m in rep["missing_assets"]] == [A + "plain_missing.md"]


def test_f2c_source_docs_needs_the_assets_floor(tmp_path):
    site, _docs = make_site(tmp_path)
    wrong = tmp_path / "wrong_docs"
    wrong.mkdir()
    _write(wrong, "index.md")
    r = run_cli(*check_args(site, wrong))
    assert r.returncode == 2 and "--source-docs" in r.stderr


def test_f6_size_gate_counts_tar_headers_and_reports_percent(tmp_path):
    site, docs = make_site(tmp_path)
    files = ps.walk_files(str(site))
    total = sum(files.values())
    est = total + len(files) * ps.TAR_HEADER_BYTES
    rep = ps.run_check(str(site), str(docs), est, 1, 1)
    assert rep["gates"]["gate2_size"] and rep["site_bytes_with_tar_headers"] == est
    assert rep["tar_header_estimate_bytes"] == len(files) * 1024
    assert not ps.run_check(str(site), str(docs), est - 1, 1, 1)["gates"]["gate2_size"]
    assert not ps.run_check(str(site), str(docs), total, 1, 1)["gates"]["gate2_size"]  # 中身だけでは足りない
    md = tmp_path / "s.md"
    run_cli(*check_args(site, docs, extra=("--summary-md", str(md))))
    assert "1 GB まで残り" in md.read_text(encoding="utf-8") and " %)" in md.read_text(encoding="utf-8")


def test_f8_www_host_and_extensionless_html_resolution(tmp_path):
    assert ps.strict_resolve("a/b.html", "https://www.furuse.work/articles/assets/x.png") == "articles/assets/x.png"
    assert ps.loose_candidates("a/b.html", "https://www.furuse.work/articles/assets/x.png") >= {"articles/assets/x.png"}
    files = {"page.html": 1, "d/index.html": 1, "f.txt": 1}
    dirs = ps.dirs_of(files)
    assert ps._resolve_file("page", files, dirs) == "page.html"
    assert ps._resolve_file("d", files, dirs) == "d/index.html"
    assert ps._resolve_file("d/", files, dirs) == "d/index.html"
    assert ps._resolve_file("f.txt", files, dirs) == "f.txt"
    assert ps._resolve_file("f.txt/", files, dirs) is None
    assert ps._resolve_file("nope", files, dirs) is None
    assert ps._resolves_in("page", files, dirs)
    site, docs = make_site(tmp_path)
    _write(site, "about.html", "<p>a</p>")
    _write(site, "links.html", '<a href="about">a</a><img src="https://www.furuse.work/articles/assets/abs1.gif">')
    rep = ps.run_check(str(site), str(docs), 10**9, 1, 1)
    assert "about" not in {b["target"] for b in rep["broken_internal_links"]}
    os.remove(site / "articles" / "assets" / "abs1.gif")
    rep = ps.run_check(str(site), str(docs), 10**9, 1, 1)
    assert "links.html" in {m["page"] for m in rep["missing_assets"]}


def test_workflow_concurrency_is_per_job():
    jobs = _pages_wf()["jobs"]
    assert "concurrency" not in _pages_wf()
    assert jobs["deploy"]["concurrency"] == {"group": "pages", "cancel-in-progress": False}
    b = jobs["build"]["concurrency"]
    assert b["group"].startswith("pages-build-") and "github.ref" in b["group"]
    assert "pull_request" in b["cancel-in-progress"]


# ---- 独立レビュー 2 回目の指摘(2026-11-11、R1〜R4)----

def _prune_keeps_and_check_catches(tmp_path, page, body, target):
    """``page`` の ``body`` が ``target`` を読む形: prune が残し、消したら check(--built-list)が exit 1。"""
    site, docs = make_site(tmp_path)
    for base in (site, docs):
        _write(base, target, "<p>t</p>" if target.endswith(".html") else "T")
        # 門 4 が要るテーマの CSS を付ける(index.html を書き換えても門 4 で落ちないように)
        _write(base, page, '<html><head><link rel="stylesheet" href="/articles/css/site.css"></head><body>'
               + body + "</body></html>")
    plan = ps.plan_prune(str(site))
    assert target not in plan["remove"], (page, body)
    lst = tmp_path / "built.txt"
    assert run_cli("snapshot", "--site", str(site), "--out", str(lst)).returncode == 0
    assert run_cli(*check_args(site, docs, extra=("--built-list", str(lst)))).returncode == 0
    os.remove(os.path.join(site, *target.split("/")))
    r = run_cli(*check_args(site, docs, extra=("--built-list", str(lst))))
    assert r.returncode == 1, (page, body, r.stdout[-400:])
    assert "MISSING " + page in r.stderr


def test_r1a_dotdot_over_the_root_is_clamped_like_a_browser(tmp_path):
    _prune_keeps_and_check_catches(tmp_path, "index.html", '<img src="../articles/assets/over.png">',
                                   A + "over.png")


def test_r1a_dotdot_over_the_root_from_a_nested_page(tmp_path):
    _prune_keeps_and_check_catches(tmp_path, "view2026/index.html",
                                   '<img src="../../../articles/assets/over3.png">', A + "over3.png")


def test_r1b_backslash_is_read_as_slash(tmp_path):
    _prune_keeps_and_check_catches(tmp_path, "index.html", '<img src="/articles\\assets\\bs.png">',
                                   A + "bs.png")
    assert ps.strict_resolve("a/b.html", "..\\articles\\assets\\x.png") == "articles/assets/x.png"
    assert ps.strict_resolve("a/b.html", "\\\\example.com\\x.png") is None  # \\host = //host(外)


def test_r1b_backslash_relative_in_prune(tmp_path):
    _prune_keeps_and_check_catches(tmp_path, "articles/index.html", '<img src="assets\\rel\\bs2.png">',
                                   A + "rel/bs2.png")


def test_r1b_backslash_in_an_unquoted_attribute(tmp_path):
    """引用符の無い属性の \\(LOOSE_TOKEN は \\ で切るので、\\ を / と読んだ本文から拾う)。"""
    _prune_keeps_and_check_catches(tmp_path, "index.html", '<img src=/articles\\assets\\bs3.png>',
                                   A + "bs3.png")


def test_r1b_backslash_from_a_json_escape(tmp_path):
    """JSON の ``\\u005c``(本文には \\ が無く、json.loads の後の字句にだけ現れる)。"""
    site, _docs = make_site(tmp_path)
    _write(site, A + "j.png")
    _write(site, "data.json", '{"img": "articles\\u005cassets\\u005cj.png"}')
    assert A + "j.png" not in ps.plan_prune(str(site))["remove"]


def test_r1c_meta_refresh_url_is_a_reference(tmp_path):
    _prune_keeps_and_check_catches(tmp_path, "index.html",
                                   '<meta http-equiv="refresh" content="0;url=/articles/assets/r.html">',
                                   A + "r.html")
    m = ps.meta_refresh_url
    assert m("0;url=/a/b.html") == "/a/b.html"
    assert m("5; URL='x y.html'") == "x y.html"
    assert m(' 3 , url = "q.html" ') == "q.html"
    assert m("0") is None


def test_r1c_meta_refresh_upper_case_http_equiv(tmp_path):
    _prune_keeps_and_check_catches(tmp_path, "index.html",
                                   '<META HTTP-EQUIV="Refresh" CONTENT="1; URL=articles/assets/r2.html">',
                                   A + "r2.html")


def test_r1c_base_href_is_the_origin_of_relative_urls(tmp_path):
    _prune_keeps_and_check_catches(tmp_path, "index.html",
                                   '<base href="/articles/assets/demo2/"><img src="b.png">', A + "demo2/b.png")


def test_r1c_base_href_relative_and_file_shaped(tmp_path):
    # base が相対でファイルの形(dirname が起点)
    _prune_keeps_and_check_catches(tmp_path, "view2026/index.html",
                                   '<base href="../articles/assets/demo3/page.html"><img src="c.png">',
                                   A + "demo3/c.png")


def test_r1c_base_href_itself_is_not_a_reference_and_external_base_leaves_the_site(tmp_path):
    site, docs = make_site(tmp_path)
    _write(site, "b.html", '<base href="/articles/assets/nodir/"><img src="/articles/assets/img_src.png">')
    rep = ps.run_check(str(site), str(docs), 10**9, 1, 1)
    assert not [b for b in rep["broken_internal_links"] if b["target"].startswith(A + "nodir")]
    assert ps.strict_resolve_in_page("a/b.html", "x.png", "https://example.com/") is None
    assert ps.strict_resolve_in_page("a/b.html", "/articles/assets/x.png", "https://example.com/") == \
        "articles/assets/x.png"
    assert ps.strict_resolve_in_page("a/b.html", "x.png", None) == "a/x.png"
    assert ps.strict_resolve_in_page("a/b.html", "x.png", "/") == "x.png"


def test_r1c_unresolvable_asset_links_are_counted_separately(tmp_path):
    site, docs = make_site(tmp_path)
    before = ps.run_check(str(site), str(docs), 10**9, 1, 1)
    _write(site, "links.html", '<img src="/articles/assets/nowhere.png"><a href="/nope.html">n</a>')
    rep = ps.run_check(str(site), str(docs), 10**9, 1, 1)
    assert rep["ok"] and rep["broken_asset_links_count"] == before["broken_asset_links_count"] + 1
    assert rep["broken_internal_links_count"] == before["broken_internal_links_count"] + 2


def test_r2_quotes_close_with_the_same_quote_apostrophe_in_alt_paren(tmp_path):
    site, _docs = make_site(tmp_path)
    _write(site, A + "fig(1).png")
    _write(site, "p.html", '<img alt="Fullseye\'s demo" src="/articles/assets/fig(1).png">')
    assert A + "fig(1).png" not in ps.plan_prune(str(site))["remove"]


def test_r2_quotes_close_with_the_same_quote_apostrophe_in_alt_space(tmp_path):
    site, _docs = make_site(tmp_path)
    _write(site, A + "my shot.png")
    _write(site, "p.html", '<img alt="it\'s" src="/articles/assets/my shot.png">')
    assert A + "my shot.png" not in ps.plan_prune(str(site))["remove"]
    # 逆向き(一重の中に ")
    _write(site, A + "your shot.png")
    _write(site, "q.html", "<img title='a \"b\" c' src='/articles/assets/your shot.png'>")
    assert A + "your shot.png" not in ps.plan_prune(str(site))["remove"]


@pytest.mark.parametrize("shape", ["same", "docs_inside_site", "site_inside_docs"])
def test_r3_source_docs_must_not_be_the_site_or_nested(tmp_path, shape):
    site, docs = make_site(tmp_path)
    if shape == "same":
        d, s = site, site
    elif shape == "docs_inside_site":
        d, s = site / "articles", site
    else:
        d, s = docs, docs / "view2026"
    r = run_cli(*check_args(s, d))
    assert r.returncode == 2 and "--source-docs" in r.stderr, (shape, r.stderr[-300:])


def test_r3_siblings_are_fine(tmp_path):
    site, docs = make_site(tmp_path)
    assert run_cli(*check_args(site, docs)).returncode == 0


def test_r4_m11_source_docs_floor_is_the_assets_floor_not_one(tmp_path):
    """docs の assets が 1 本以上・床未満でも exit 2(床を 1 にする変異 M11 を殺す)。"""
    site, _docs = make_site(tmp_path)
    few = tmp_path / "few_docs"
    for i in range(3):
        _write(few, A + f"f{i}.png")
    r = run_cli(*check_args(site, few, min_kept=4))
    assert r.returncode == 2 and "--source-docs" in r.stderr
    ps.run_check(str(site), str(few), 10**9, 1, 3)  # ちょうど床なら docs の床では止めない


def test_r4_m14_relative_trailing_slash_stays_a_directory(tmp_path):
    assert ps.strict_resolve("articles/index.html", "assets/demo/") == "articles/assets/demo/"
    site, docs = make_site(tmp_path)
    _write(docs, A + "demo/index.html", "<p>d</p>")
    _write(site, A + "demo.html", "<p>other</p>")  # 末尾 / を落とすと、こちらに解けてしまう
    _write(docs, A + "demo.html", "<p>other</p>")
    _write(site, "articles/links.html", '<a href="assets/demo/">d</a>')
    rep = ps.run_check(str(site), str(docs), 10**9, 1, 1)
    assert not rep["ok"] and A + "demo/" in {m["target"] for m in rep["missing_assets"]}


def test_r4_m17_protocol_relative_www_host_is_this_site(tmp_path):
    u = "//www.furuse.work/articles/assets/x.png"
    assert ps.strict_resolve("a/b.html", u) == "articles/assets/x.png"
    assert "articles/assets/x.png" in ps.loose_candidates("a/b.html", u)


def test_r4_m18_read_list_refuses_an_empty_list_itself(tmp_path):
    p = tmp_path / "empty.txt"
    p.write_text("\n \n\n", encoding="utf-8")
    with pytest.raises(ps.SiteError, match="一覧が空"):
        ps.read_list(str(p))
