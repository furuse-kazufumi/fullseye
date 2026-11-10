# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PR で回すテストの選び方(``tools/ci_select_tests.py``)と片分けの門(2026-11-10)。

PR は変更に関係するテストだけを回す。ここが**選び損ねる**と、PR は緑のまま master と
毎日の全数で初めて落ちる。だから確かめるのは「少なく選ばない」側:

1. パスの字面の読み方(畳む・型にする・単語だけの字面は repo 直下だけ)
2. 中核・対応の分からないファイル・消したファイル・変更 0 件は full(fail-safe)
3. 過去の PR で CI が実際に落としたテストが、その PR の変更から選ばれること
   (#272 の例の台本・#294 の台帳データ・変えたテストそのもの・毎回回す門)
4. 片分けはファイル単位で、全部のテストがちょうど 1 片に入る(落とさない・重ねない)
5. conftest の選択は、一覧が空・何も当たらないとき止まる(黙って 0 件で緑にしない)

過去の PR を当時の木で再生した結果(選ばれた失敗 / 実際の失敗)は、PR の説明に載せた
(当時の木は CI の checkout に無いので、ここでは今の木で同じ形の変更を確かめる)。
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name):
    spec = importlib.util.spec_from_file_location(name + "_t20261110", os.path.join(ROOT, "tools", name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CST = _load("ci_select_tests")
CFR = _load("ci_failure_record")


@pytest.fixture(scope="module")
def selector():
    ix = CST.Index(CST.ROOT)
    return CST.Selector(ix, CST.load_always())


def _selected(res, nodeid_or_file):
    """選んだ一覧に、ファイルごと or そのノード id で入っているか。"""
    tests = set(res.get("tests", []))
    return nodeid_or_file in tests or nodeid_or_file.split("::", 1)[0] in tests


# --------------------------------------------------------------------------- 1
def test_path_literals_are_folded_and_typed():
    src = '''
import os
from pathlib import Path
ROOT = Path(__file__).parents[1]
A = ROOT / "docs" / "real_data_runs.json"
B = os.path.join(ROOT, "..", "docs", "COLLECTION_SIZES.json")
C = ROOT / "examples" / (name + ".py")
D = sorted((ROOT / "examples").glob("poc_*.py"))
E = f"{ROOT}/fullseye/data/{name}.json"
F = "examples"
G = os.path.join(HERE, "data", name)
'''
    _imports, refs = CST.analyse_source(src, "tests/test_x.py")
    assert "docs/real_data_runs.json" in refs
    assert "docs/COLLECTION_SIZES.json" in refs          # ".." は落とす
    assert "docs" not in refs, refs                       # 内側の部分式を別の参照にしない
    assert "examples/*.py" in refs
    assert "examples/poc_*.py" in refs
    assert "fullseye/data" in refs
    assert "~examples" in refs                            # 畳めない単語だけの字面
    assert "data/*" in refs


def test_reference_matching_rules():
    assert CST.ref_matches("docs/x.json", "docs/x.json")
    assert CST.ref_matches("x.json", "docs/sub/x.json")             # 成分の並びとして一致
    assert not CST.ref_matches("x.json", "docs/xx.json")
    assert CST.ref_matches("examples/*.py", "examples/poc_a.py")
    assert CST.ref_matches("data/*", "fullseye/data/OP_INDEX.json")  # どこの data/ でも
    assert CST.ref_matches("~examples", "examples/a.py")
    assert not CST.ref_matches("~examples", "rust/fullseye_core/examples/c/main.c")  # 単語は直下だけ


def test_imports_with_literal_names_are_edges():
    src = "import importlib\nm = importlib.import_module('calib')\n__import__('backends_auto')\nfrom fullseye.mcp import server\n"
    imports, _refs = CST.analyse_source(src, "tests/test_x.py")
    assert {"calib", "backends_auto", "fullseye.mcp", "fullseye.mcp.server"} <= imports


# --------------------------------------------------------------------------- 2
@pytest.mark.parametrize("changed", [
    ["ops.py"], ["backends.py"], ["tests/conftest.py"], ["pyproject.toml"],
    [".github/workflows/ci.yml"], ["tools/ci_select_tests.py"], ["tools/regen_all.py"],
    ["examples/poc_camera_calibration.py", "api.py"],
])
def test_core_files_force_the_full_suite(selector, changed):
    res = selector.select(changed)
    assert res["mode"] == "full", res
    assert "core file" in res["reasons"][0]


def test_an_unmapped_or_deleted_file_forces_the_full_suite(selector):
    # 名前は実行時に作る(字面で書くと、このテスト自身がその名前を「名指しする」ことになる)。
    res = selector.select(["zz_unmapped_%d/file_%d.bin" % (7, 7)])
    assert res["mode"] == "full", res
    assert "no test is known to depend on" in res["reasons"][0]


def test_no_changes_or_too_many_force_the_full_suite(selector):
    assert selector.select([])["mode"] == "full"
    many = ["examples/poc_camera_calibration.py"] * 2 + ["f%d.txt" % i for i in range(CST.MAX_CHANGED + 1)]
    assert selector.select(many)["mode"] == "full"


def test_the_cli_falls_back_to_full_when_git_fails(tmp_path):
    out = tmp_path / "gh_out"
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "ci_select_tests.py"),
                        "--base", "no-such-ref-zz", "--github-output", str(out), "--json",
                        "--tests-file", str(tmp_path / "sel.txt")],
                       capture_output=True, text=True, cwd=ROOT, timeout=600)
    assert r.returncode == 0, r.stderr[-2000:]
    res = json.loads(r.stdout)
    assert res["mode"] == "full" and "git diff failed" in res["reasons"][0], res
    text = out.read_text(encoding="utf-8")
    assert "mode=full" in text and "nshards=6" in text and "shards=[1, 2, 3, 4, 5, 6]" in text


def test_the_always_run_gates_exist_and_are_always_selected(selector):
    always = CST.load_always()
    assert {"tests/test_vacuous_assertions.py", "tests/test_type_alias_ledger.py",
            "tests/test_test_durations_is_fresh.py"} <= set(always), always
    missing = [a for a in always if not os.path.exists(os.path.join(ROOT, a))]
    assert missing == [], missing
    res = selector.select(["examples/hessian_numpy_chain.py"])
    assert res["mode"] == "selected", res
    assert set(always) <= set(res["tests"])


# --------------------------------------------------------------------------- 3
def test_pr272_the_failing_example_script_is_selected(selector):
    """#272: ``examples/hessian_numpy_chain.py`` を変え、例の門のその台本が落ちた。"""
    res = selector.select(["examples/hessian_numpy_chain.py"])
    assert res["mode"] == "selected", res
    assert _selected(res, "tests/test_example_scripts_run.py::"
                          "test_the_example_runs_from_a_bare_checkout[hessian_numpy_chain.py]"), res["tests"][:40]


def test_pr294_the_macro_ledger_data_selects_the_macro_gate(selector):
    """#294: ``data/macro_champions.json`` を変え、``test_macro_ops`` が落ちた。"""
    res = selector.select(["data/macro_champions.json"])
    assert res["mode"] == "selected", res
    assert _selected(res, "tests/test_macro_ops.py")


def test_a_changed_test_file_selects_itself_and_the_gates_that_read_tests(selector):
    """#276 / #294 / #295: 変えたテストそのものと、tests/ を読む負債の門。"""
    res = selector.select(["tests/test_macro_ops.py"])
    assert res["mode"] == "selected", res
    assert _selected(res, "tests/test_macro_ops.py")
    assert _selected(res, "tests/test_vacuous_assertions.py")


def test_a_library_change_selects_its_importers_and_the_scripts_that_run_it(selector):
    res = selector.select(["fullseye/opsearch.py"])
    assert res["mode"] == "selected", res
    assert _selected(res, "tests/test_opsearch.py")
    assert _selected(res, "tests/test_rag_recall_airag.py")


def test_runner_params_are_narrowed_to_the_changed_script(selector):
    res = selector.select(["examples/poc_camera_calibration.py"])
    assert res["mode"] == "selected", res
    node = "tests/test_poc_scripts_run.py::test_the_poc_runs_clean[poc_camera_calibration.py]"
    assert _selected(res, node)
    assert "tests/test_poc_scripts_run.py" not in res["tests"]          # 84 本全部ではない
    others = [t for t in res["tests"] if t.startswith("tests/test_poc_scripts_run.py::")]
    assert others == [node], others


# --------------------------------------------------------------------------- 4
def test_shards_partition_by_file_and_keep_every_test():
    ids = ["tests/test_a.py::t%d" % i for i in range(5)] + \
          ["tests/test_b.py::t%d" % i for i in range(3)] + \
          ["tests/test_poc_scripts_run.py::test_the_poc_runs_clean[p%d.py]" % i for i in range(4)] + \
          ["tests/test_c.py::only"]
    dur = {"tests/test_a.py::t0": 50.0, "tests/test_b.py::t0": 40.0, "tests/test_c.py::only": 1.0}
    dur.update({"tests/test_poc_scripts_run.py::test_the_poc_runs_clean[p%d.py]" % i: 30.0 for i in range(4)})
    for n in (1, 2, 3, 6):
        plan = CST.shard_plan(ids, n, dur)
        flat = [x for p in plan for x in p]
        assert sorted(flat) == sorted(ids) and len(flat) == len(ids)       # 落とさない・重ねない
        assert plan == CST.shard_plan(ids, n, dur)                          # 決定的
        where = {x: i for i, p in enumerate(plan) for x in p}
        assert len({where[x] for x in ids if x.startswith("tests/test_a.py")}) == 1
        assert len({where[x] for x in ids if x.startswith("tests/test_b.py")}) == 1
        assert len({where[x] for x in ids if "poc_scripts_run" in x}) == 1   # 台本の門もファイルごと


def test_shard_plan_on_the_real_baseline_is_balanced():
    with open(os.path.join(ROOT, ".test_durations"), encoding="utf-8") as f:
        d = json.load(f)
    ids = sorted(d)
    assert len(ids) > 20000
    plan = CST.shard_plan(ids, 6, d)
    loads = [sum(d[x] for x in p) for p in plan]
    assert sum(len(p) for p in plan) == len(ids)
    assert max(loads) <= 1.10 * (sum(loads) / 6), loads


def test_selection_file_rules(tmp_path):
    p = tmp_path / "sel.txt"
    p.write_text("# full suite\n", encoding="utf-8")
    with pytest.raises(ValueError):
        CST.read_selection(str(p))                                          # 空の一覧は止める
    p.write_text("tests/test_a.py\ntests/test_b.py::t1\ntests/test_gone.py\n", encoding="utf-8")
    ids = ["tests/test_a.py::t0", "tests/test_a.py::t1", "tests/test_b.py::t0", "tests/test_b.py::t1"]
    info = CST.plan_session(ids, selection=str(p), shard=None)
    assert info["keep"] == ["tests/test_a.py::t0", "tests/test_a.py::t1", "tests/test_b.py::t1"]
    assert info["unmatched"] == ["tests/test_gone.py"]
    p.write_text("tests/test_gone.py\n", encoding="utf-8")
    with pytest.raises(ValueError):
        CST.plan_session(ids, selection=str(p), shard=None)                 # 1 件も当たらない
    with pytest.raises(ValueError):
        CST.parse_shard("7/6")


def test_the_conftest_selection_runs_only_the_listed_tests(tmp_path):
    sel = tmp_path / "sel.txt"
    sel.write_text("tests/test_ci_select_tests_2026_11_10.py::test_reference_matching_rules\n", encoding="utf-8")
    env = dict(os.environ, FULLSEYE_CI_SELECTION=str(sel), FULLSEYE_CI_SHARD="1/1")
    r = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider",
                        "tests/test_ci_select_tests_2026_11_10.py"],
                       capture_output=True, text=True, cwd=ROOT, env=env, timeout=600)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    assert "1/" in r.stdout and "[fullseye-ci]" in r.stdout, r.stdout[-2000:]
    sel.write_text("tests/test_no_such_file_zz.py\n", encoding="utf-8")
    r = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider",
                        "tests/test_ci_select_tests_2026_11_10.py"],
                       capture_output=True, text=True, cwd=ROOT, env=env, timeout=600)
    assert r.returncode != 0, r.stdout[-2000:]                               # fail-closed


# --------------------------------------------------------------------------- 5
def test_failure_record_reads_junit(tmp_path):
    d = tmp_path / "junit"
    d.mkdir()
    (d / "junit-py3.11-shard1.xml").write_text(
        '<testsuites><testsuite name="pytest" tests="3">'
        '<testcase classname="tests.test_a" name="test_ok"/>'
        '<testcase classname="tests.test_a" name="test_bad[x]"><failure message="boom"/></testcase>'
        '<testcase classname="tests.test_b.TestK" name="test_err"><error message="oops"/></testcase>'
        '</testsuite></testsuites>', encoding="utf-8")
    failed, n, bad = CFR.failed_tests(d)
    assert n == 3 and bad == []
    assert [f["nodeid"] for f in failed] == ["tests/test_a.py::test_bad[x]",
                                             "tests/test_b.py::TestK::test_err"]
    assert [f["kind"] for f in failed] == ["failure", "error"]


# --------------------------------------------------------------------------- 6
CDD = _load("ci_deps_drift")


def test_dependency_drift_compares_every_resolved_name(tmp_path):
    base, res = tmp_path / "base", tmp_path / "res"
    base.mkdir()
    res.mkdir()
    (base / "freeze-main.txt").write_text("numpy==2.3.0\nthreadpoolctl==3.7.0\npip==26.2.2\n-e git+x#egg=fullseye\n",
                                          encoding="utf-8")
    (base / "freeze-full.txt").write_text("torch==2.15.0+cpu\nkornia==0.9.0\n", encoding="utf-8")
    (res / "main.txt").write_text("numpy==2.3.0\nthreadpoolctl==3.7.0\n", encoding="utf-8")
    (res / "optional.txt").write_text("torch==2.15.0+cpu\nkornia==0.9.0\n", encoding="utf-8")
    assert CDD.compare_dirs(base, res) == (0, [])
    # #271 の型: 依存の新しい版
    (res / "main.txt").write_text("numpy==2.3.0\nthreadpoolctl==3.8.0\n", encoding="utf-8")
    code, lines = CDD.compare_dirs(base, res)
    assert code == 1 and lines == ["threadpoolctl: 3.7.0 -> 3.8.0"]
    # 新しく入る依存も違いに数える
    (res / "main.txt").write_text("numpy==2.3.0\nthreadpoolctl==3.7.0\nnewdep==1.0\n", encoding="utf-8")
    assert CDD.compare_dirs(base, res) == (1, ["newdep: new (1.0)"])
    # 基準が無い・空は比べられない(= full)
    (base / "freeze-full.txt").unlink()
    assert CDD.compare_dirs(base, res)[0] == 2
    (base / "freeze-full.txt").write_text("", encoding="utf-8")
    assert CDD.compare_dirs(base, res)[0] == 2


def test_dependency_drift_turns_the_pr_into_a_full_run(tmp_path):
    code, text = tmp_path / "c", tmp_path / "t"
    text.write_text("threadpoolctl: 3.7.0 -> 3.8.0\n", encoding="utf-8")
    code.write_text("0\n", encoding="utf-8")
    assert CST.deps_drift_reason(str(code), str(text)) is None
    code.write_text("1\n", encoding="utf-8")
    assert "threadpoolctl: 3.7.0 -> 3.8.0" in CST.deps_drift_reason(str(code), str(text))
    code.write_text("2\n", encoding="utf-8")
    assert "no dependency baseline" in CST.deps_drift_reason(str(code), str(text))
    assert CST.deps_drift_reason(str(tmp_path / "missing"), str(text)) == "dependency check result unreadable"
    out = tmp_path / "gh_out"
    code.write_text("1\n", encoding="utf-8")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "ci_select_tests.py"),
                        "--files", "examples/hessian_numpy_chain.py", "--deps-drift", str(code), str(text),
                        "--github-output", str(out), "--json", "--tests-file", str(tmp_path / "sel.txt")],
                       capture_output=True, text=True, cwd=ROOT, timeout=600)
    assert r.returncode == 0, r.stderr[-2000:]
    res = json.loads(r.stdout)
    assert res["mode"] == "full" and "dependency versions differ" in res["reasons"][0], res


def test_the_resolved_requirements_are_the_ones_the_test_job_installs():
    """``ci_deps_drift`` の要求と ci.yml のテストのジョブの ``pip install`` が食い違うと、比較が嘘になる。"""
    with open(os.path.join(ROOT, ".github", "workflows", "ci.yml"), encoding="utf-8") as f:
        text = f.read()
    job = text[text.index("\n  test:\n"):text.index("\n  duration-baseline:\n")]
    main_line = " ".join(job[job.index('pip install -e ".[opencv'):].split("\n", 2)[:2]).split()
    assert main_line[:2] == ["pip", "install"], main_line[:4]
    assert tuple(a.strip('"') for a in main_line[2:]) == CDD.MAIN_REQUIREMENTS, main_line
    opt = job[job.index("Optional backends (py3.11 only"):]
    assert 'pip install --index-url %s "torch>=2.13"' % CDD.TORCH_INDEX in opt
    assert 'pip install "kornia>=0.9" "mahotas>=1.4"' in opt
    assert 'pip install "opencv-contrib-python>=4.8.1.78"' in opt
    assert CDD.OPTIONAL_REQUIREMENTS == ("torch>=2.13", "kornia>=0.9", "mahotas>=1.4",
                                         "opencv-contrib-python>=4.8.1.78")


# --------------------------------------------------------------------------- 7
# 独立レビュー(2026-11-10)の指摘への門
_REVIEW_WALKERS = ("tests/test_provenance_naming.py", "tests/test_no_invalid_escape_sequences.py",
                   "tests/test_svd_full_matrices.py", "tests/test_fssystem.py",
                   "tests/test_docs_liquid_safe.py", "tests/test_no_stray_root_images_2026_11_01.py",
                   "tests/test_review_fixes_lib2_2026_10_07.py")

#: 探針(``walks_repo`` とは別の読み方): repo の根から走査する書き方。
_WALK_PROBE = re.compile(
    r"os\.walk\(\s*_?(?:ROOT|REPO|REPO_ROOT)\b|\b_?(?:ROOT|REPO|REPO_ROOT)\.rglob\(|ls-files"
    r"|glob\(\s*os\.path\.join\(\s*_?(?:ROOT|REPO)\s*,\s*[\"']\*\*")


def test_the_review_gates_are_named_in_the_always_run_list():
    assert set(_REVIEW_WALKERS) <= set(CST.load_always())


def test_every_test_that_walks_the_repo_runs_on_every_pr(selector):
    """tests/ の中で repo の根から走査するテストは、どの PR でも必ず回る(機械で見つける)。"""
    probed = []
    for name in sorted(os.listdir(os.path.join(ROOT, "tests"))):
        if not (name.startswith("test_") and name.endswith(".py")):
            continue
        with open(os.path.join(ROOT, "tests", name), encoding="utf-8", errors="ignore") as f:
            src = f.read()
        if _WALK_PROBE.search(src):
            probed.append("tests/" + name)
    assert len(probed) >= 6, probed                       # 探針が壊れて 0 本で通るのを防ぐ
    missing = sorted(set(probed) - set(selector.always))
    assert missing == [], missing
    assert set(_REVIEW_WALKERS) <= set(selector.always)
    res = selector.select(["examples/hessian_numpy_chain.py"])
    assert res["mode"] == "selected" and set(selector.always) <= set(res["tests"])


def test_walks_repo_reads_the_root_but_not_a_subdirectory():
    assert CST.walks_repo("import os\nfor dp, dn, fn in os.walk(ROOT):\n    pass\n")
    assert CST.walks_repo("for p in ROOT.rglob('*.py'):\n    pass\n")
    assert CST.walks_repo("subprocess.run(['git', 'ls-files'])\n")
    assert CST.walks_repo("def f(base):\n    os.listdir(base)\n")                 # 起点が読めない
    assert not CST.walks_repo("import os\nos.walk(os.path.join(ROOT, 'docs', 'ops'))\n")
    assert not CST.walks_repo("DOCS = ROOT / 'docs'\nfor p in DOCS.rglob('*.md'):\n    pass\n")
    assert not CST.walks_repo("def t(tmp_path):\n    list(tmp_path.iterdir())\n")


def test_review_repro_opsfileio_selects_the_two_gates(selector):
    """レビューの再現: ``opsfileio.py`` にベンダ名と不正なエスケープを入れた改変で、2 本の門が選ばれる。"""
    res = selector.select(["opsfileio.py"])
    assert res["mode"] == "selected", res
    assert _selected(res, "tests/test_provenance_naming.py")
    assert _selected(res, "tests/test_no_invalid_escape_sequences.py")


def test_root_level_files_match_double_star_patterns():
    assert CST.ref_matches("**/*.py", "opsfileio.py")
    assert CST.ref_matches("docs/**/*.md", "docs/x.md")
    assert not CST.ref_matches("**/*.md", "opsfileio.py")


def test_string_registries_and_spec_directories_are_dependencies(selector):
    """``("opsfileio", "OPSFILEIO")`` のような文字列のレジストリと、``data/auto_specs`` の広い参照。"""
    assert "opsfileio.py" in selector.ix.deps.get("opassist.py", set())
    res = selector.select(["data/auto_specs/filters.json"])
    assert res["mode"] == "selected", res
    assert _selected(res, "tests/test_gpu_fill3.py")          # レビューで選ばれなかった検出器
    assert _selected(res, "tests/test_op_contracts.py")


def test_ci_yml_does_not_cancel_full_runs_and_ignores_other_labels():
    yaml = pytest.importorskip("yaml")
    with open(os.path.join(ROOT, ".github", "workflows", "ci.yml"), encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    conc = doc["concurrency"]
    assert conc["cancel-in-progress"] == "${{ github.event_name == 'pull_request' }}"
    assert "github.run_id" in conc["group"] and "ci:full" in conc["group"]
    for job in ("changes", "core-minimal", "lint"):
        assert "ci:full" in doc["jobs"][job]["if"], job
    sel = next(s for s in doc["jobs"]["changes"]["steps"] if s.get("id") == "select")["run"]
    assert "tools/ci_select_tests\\.py" in sel and "_ci_select_tests_base.py" in sel
    prev = next(s for s in doc["jobs"]["failure-record"]["steps"] if s.get("id") == "prev")["run"]
    assert '"success"' in prev.replace('\\"', '"') and "cancelled" not in prev
