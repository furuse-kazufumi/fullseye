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
import types

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
        # ★2026-11-11: PoC の門(SPLIT_BY_TEST)だけはテスト単位で散らしてよい。各 PoC はちょうど 1 片
        pocs = [x for x in ids if "poc_scripts_run" in x]
        assert sorted(x for p in plan for x in p if x in pocs) == sorted(pocs)
        assert [sum(1 for p in plan if x in p) for x in pocs] == [1] * len(pocs)


def test_shard_plan_on_the_real_baseline_is_balanced():
    with open(os.path.join(ROOT, ".test_durations"), encoding="utf-8") as f:
        d = json.load(f)
    ids = sorted(d)
    assert len(ids) > 20000
    plan = CST.shard_plan(ids, 6, d)
    # ★2026-11-11: SPLIT_BY_TEST(PoC の門)の 1 件ごとの記録値は台本の重さではない(一括実行の時間が片の
    #   最初の 1 件に付く)ので、そのファイルはファイルの記録の平均で数える(配る側と同じ物差し)
    avg = CST._split_weights(d)
    loads = [sum(avg.get(x.split("::", 1)[0], d[x]) for x in p) for p in plan]
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


def test_ci_yml_does_not_cancel_full_runs_and_never_starts_on_a_label():
    """ラベルでは run を起こさない(全部飛ばした run の check が本物の失敗に重なるのを作りごと防ぐ)。

    `ci:full` は run の開始時に API で読み、読めなければ full。master への push は 1 つの group で、
    走っている run は打ち切らない。
    """
    yaml = pytest.importorskip("yaml")
    path = os.path.join(ROOT, ".github", "workflows", "ci.yml")
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    doc = yaml.safe_load(raw)
    on = doc[True] if True in doc else doc["on"]          # YAML 1.1 は `on` を真偽値に読む
    assert on["pull_request"]["types"] == ["opened", "synchronize", "reopened"]
    # 式は完全一致で見る(部分文字列だと、PR を 1 つの group にまとめる・push を run ごとへ戻す、が通る)。
    # PR = 枝ごと(打ち切る)/ master への push = 1 つの group(打ち切らない)/ schedule・手動 = run ごと
    assert doc["concurrency"] == {
        "group": ("${{ github.event_name == 'pull_request' && format('ci-{0}-{1}', github.workflow, github.ref)"
                  " || github.event_name == 'push' && format('ci-{0}-push-{1}', github.workflow, github.ref)"
                  " || format('ci-{0}-run-{1}', github.workflow, github.run_id) }}"),
        "cancel-in-progress": "${{ github.event_name == 'pull_request' }}",
    }
    for job in ("changes", "core-minimal", "lint"):
        assert "if" not in doc["jobs"][job], job         # ラベルで飛ばすジョブは無い
    # payload のラベルは run を作った時点の写し(再実行でも変わらない)なので、判定に使わない
    assert "github.event.pull_request.labels" not in raw
    assert "github.event.label" not in raw
    steps = doc["jobs"]["changes"]["steps"]
    ids = [s.get("id") for s in steps]
    assert ids.index("label") < ids.index("select")
    label = next(s for s in steps if s.get("id") == "label")["run"]
    assert label.count("full=true") == 2 and label.count("full=false") == 1   # 読めないときも full
    assert doc["jobs"]["changes"]["permissions"]["pull-requests"] == "read"
    sel = next(s for s in steps if s.get("id") == "select")["run"]
    assert '"$FULL_LABEL" != false' in sel                # 空(出力なし)も full に倒す
    assert "tools/ci_select_tests\\.py" in sel and "_ci_select_tests_base.py" in sel
    # 範囲の起点は run の結論では選ばない(docs だけの run は全部 skip で success になる)。挙動は下の
    # test_the_failure_record_range_starts_at_the_same_run_as_the_docs_only_check が実行して見る
    prev = next(s for s in doc["jobs"]["failure-record"]["steps"] if s.get("id") == "prev")["run"]
    assert "ci-result-$sha" in prev and "conclusion" not in prev


# --------------------------------------------------------------------------- #
# 先頭のジョブ(gates): 落ちやすくて軽いテストを、片と並行して先に回す(2026-11-10)   #
# --------------------------------------------------------------------------- #
# 確かめるのは 3 つ: (1) gates は片を待たない (2) 先に回す一覧は道具が実績から出す(YAML に写さない)
# (3) 片の側は 1 件も減っていない(先頭のジョブは「先にも回す」で、片から外すものではない)。
CFH = _load("ci_failure_history")


def _workflow_jobs():
    yaml = pytest.importorskip("yaml")
    with open(os.path.join(ROOT, ".github", "workflows", "ci.yml"), encoding="utf-8") as f:
        return yaml.safe_load(f)["jobs"]


def _runs(job):
    return [s.get("run", "") for s in job["steps"]]


def test_early_plan_ranks_by_failed_runs_and_skips_what_does_not_fit(tmp_path):
    (tmp_path / "tests").mkdir()
    for name in ("a", "b", "c", "gate", "one_branch"):
        (tmp_path / "tests" / ("test_%s.py" % name)).write_text("def test_x():\n    assert 1 + 1 == 2\n", encoding="utf-8")
    dur = tmp_path / "durations.json"
    dur.write_text(json.dumps({"tests/test_a.py::test_x": 100.0, "tests/test_b.py::test_x": 300.0,
                               "tests/test_c.py::test_x": 150.0, "tests/test_gate.py::test_x": 10.0,
                               "tests/test_one_branch.py::test_x": 1.0}), encoding="utf-8")
    history = {"runs_read": 9, "window": [], "files": {
        "tests/test_a.py": {"failed_runs": 5, "branches": 3},
        "tests/test_b.py": {"failed_runs": 4, "branches": 2},
        "tests/test_c.py": {"failed_runs": 3, "branches": 2},
        "tests/test_one_branch.py": {"failed_runs": 8, "branches": 1},   # 同じブランチの push し直し
        "tests/test_gone.py": {"failed_runs": 7, "branches": 4},         # この木に無い
    }}
    always = ["tests/test_gate.py", CST.FRESHNESS_GATE]
    plan = CST.early_plan(always, history, budget=300, durations_path=dur, root=tmp_path)
    # a(100) の次の b(300) は入らないので飛ばし、c(150)・gate(10) を入れる。回す順 = 落ちた run の数の順
    assert plan["tests"] == ["tests/test_a.py", "tests/test_c.py", "tests/test_gate.py"]
    assert plan["seconds"] == 260.0 and plan["budget"] == 300
    why = {r["file"]: r["why"] for r in plan["rows"]}
    assert len(why) == 6 and "tests/test_one_branch.py" not in why
    assert why["tests/test_b.py"].startswith("over the 300 s budget")
    assert why["tests/test_gone.py"] == "not in this tree"
    assert why[CST.FRESHNESS_GATE].startswith("session-dependent")
    # 門は実績が 0 でも候補に入る(門を候補から落とすのは上限だけ)
    assert [r["failed_runs"] for r in plan["rows"] if r["file"] == "tests/test_gate.py"] == [0]
    with pytest.raises(ValueError, match="early list is empty"):
        CST.early_plan(always, history, budget=0.5, durations_path=dur, root=tmp_path)


def test_the_early_list_comes_from_the_failure_history_within_the_budget(selector, tmp_path):
    history = CST.load_failure_history()
    assert history["runs_read"] >= 30 and len(history["files"]) >= 20      # 数えた run が少なすぎる実績で選ばない
    plan = CST.early_plan(selector.always, history)
    rows = {r["file"]: r for r in plan["rows"]}
    early = plan["tests"]
    assert len(rows) == len(plan["rows"]) and len(early) == len(set(early)) >= 10
    # 候補 = 門の全部 + 2 本以上のブランチで落ちたファイルの全部
    recurring = [f for f, row in history["files"].items() if row["branches"] >= CST.EARLY_MIN_BRANCHES]
    assert len(selector.always) >= 10 and len(recurring) >= 5
    assert len(set(selector.always) - set(rows)) == 0 and len(set(recurring) - set(rows)) == 0
    # 上限と順番
    assert CST.EARLY_BUDGET_SECONDS == 480
    assert 0 < plan["seconds"] <= CST.EARLY_BUDGET_SECONDS
    assert abs(sum(rows[f]["seconds"] for f in early) - plan["seconds"]) < 0.06 * len(early)
    counts = [rows[f]["failed_runs"] for f in early]
    assert counts == sorted(counts, reverse=True) and counts[0] >= 2
    # 外したものには理由があり、上限で外したものは、いま足しても入らない(入るのに外したものが無い)
    later = [r for r in plan["rows"] if not r["early"]]
    assert len(later) >= 3 and sum(1 for r in later if r["why"]) == len(later)
    over = [r for r in later if r["why"].startswith("over the")]
    assert sum(1 for r in over if plan["seconds"] + r["seconds"] > CST.EARLY_BUDGET_SECONDS) == len(over)
    # 鮮度の門と台本の門は pytest に渡さない。渡すファイルは全部この木にある
    assert CST.FRESHNESS_GATE in rows and CST.FRESHNESS_GATE not in early
    assert len(set(CST.SCRIPT_RUNNERS) & set(early)) == 0
    assert sum(os.path.isfile(os.path.join(ROOT, f)) for f in early) == len(early)
    # CLI が書く一覧は同じもの(workflow はこのファイルを読む)
    out = tmp_path / "early.txt"
    assert CST.main(["--early-list", str(out)]) == 0
    assert out.read_text(encoding="utf-8").split() == early


def test_failure_history_is_fail_closed_and_counts_only_blocking_jobs(tmp_path):
    bad = tmp_path / "h.json"
    for payload in ({}, {"files": {}}, {"runs_read": 3, "files": {"tests/test_a.py": {"failed_runs": 0, "branches": 0}}},
                    {"runs_read": 3, "files": {"tests/test_a.py": {"failed_runs": 2, "branches": 3}}},
                    {"runs_read": 1, "files": {"tests/test_a.py": {"failed_runs": 2, "branches": 1}}}):
        bad.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(ValueError):
            CST.load_failure_history(bad)
    with pytest.raises(OSError):
        CST.load_failure_history(tmp_path / "missing.json")
    log = "\n".join([
        "full suite (py3.11, shard 1/6)\tRun tests\t2026-11-09T00:00:00.0Z FAILED tests/test_a.py::test_x - AssertionError",
        "full suite (py3.11, shard 1/6)\tRun tests\t2026-11-09T00:00:00.0Z FAILED tests/test_a.py::test_y - AssertionError",
        "selected tests (py3.11, shard 1/2)\tRun tests\t2026-11-09T00:00:00.0Z ERROR tests/test_b.py - ImportError: x",
        "python 3.15 preview (allowed to fail)\tRun tests\t2026-11-09T00:00:00.0Z FAILED tests/test_c.py::test_z",
        "order shuffle\tRun tests\t2026-11-09T00:00:00.0Z FAILED tests/test_d.py::test_z",
        "full suite (py3.11, shard 1/6)\tRun tests\t2026-11-09T00:00:00.0Z   the word FAILED tests/test_e.py in a traceback",
        "full suite (py3.11, shard 1/6)\tregen\t2026-11-09T00:00:00.0Z " + CFH.REGEN_DRIFT_MARKS[0],
    ])
    files, drift = CFH.parse_log(log)
    assert files == {"tests/test_a.py", "tests/test_b.py"} and drift is True
    assert CFH.parse_log(log.rsplit("\n", 1)[0]) == ({"tests/test_a.py", "tests/test_b.py"}, False)
    runs = [{"databaseId": 1, "createdAt": "2026-11-01T00:00:00Z", "headBranch": "pr/x"},
            {"databaseId": 2, "createdAt": "2026-11-02T00:00:00Z", "headBranch": "pr/x"},
            {"databaseId": 3, "createdAt": "2026-11-03T00:00:00Z", "headBranch": "master"}]
    data = CFH.aggregate(runs, {1: log, 2: log, 3: "nothing failed here"})
    assert data["runs_read"] == 3 and data["runs_with_test_failures"] == 2 and data["runs_with_regen_drift"] == 2
    assert data["files"] == {"tests/test_a.py": {"failed_runs": 2, "branches": 1},
                             "tests/test_b.py": {"failed_runs": 2, "branches": 1}}
    assert data["window"] == ["2026-11-01T00:00:00Z", "2026-11-03T00:00:00Z"]
    # 書いたものは、選ぶ側がそのまま読める(ブランチ名は書かない)
    out = tmp_path / "ok.json"
    out.write_text(CFH.dumps(data), encoding="utf-8")
    assert CST.load_failure_history(out)["files"]["tests/test_a.py"] == {"failed_runs": 2, "branches": 1}
    assert "pr/x" not in out.read_text(encoding="utf-8")


def test_freshness_forecast_calls_the_real_gate_on_the_session_of_its_shard(tmp_path):
    with open(os.path.join(ROOT, ".test_durations"), encoding="utf-8") as f:
        durations = json.load(f)
    gate = [n for n in durations if n.split("::", 1)[0] == CST.FRESHNESS_GATE]
    assert len(gate) == 1
    recorded = [n for n in sorted(durations) if n.split("::", 1)[0] != CST.FRESHNESS_GATE][:200] + gate
    res = CST.freshness_forecast(recorded, nshards=1)
    assert res == {"ok": True, "shard": "1/1", "in_shard": 201, "message": ""}
    # 記録の無いテストが 30 件足されると 201/231 = 87.0 % で、門の本体が落とす(閾値は門のファイルにしか無い)
    new = ["tests/test_zz_not_recorded_2026_11_10.py::test_%d" % i for i in range(30)]
    res = CST.freshness_forecast(recorded + new, nshards=1)
    assert res["ok"] is False and res["in_shard"] == 231 and "201/231" in res["message"]
    # 片に分けたら、門が入った片の session だけで数える
    res = CST.freshness_forecast(recorded + new, nshards=2)
    assert res["shard"] in ("1/2", "2/2") and 0 < res["in_shard"] < 231
    with pytest.raises(ValueError, match="no shard holds"):
        CST.freshness_forecast(recorded[:-1], nshards=2)
    # `pytest --collect-only -q` の出力を読む: 警告の行は数えず、件数が要約と合わなければ止める
    listing = tmp_path / "collected.txt"
    body = recorded + new + ["", "tests/test_a.py:12: UserWarning: a::b", "  warnings.warn('x::y')"]
    listing.write_text("\n".join(body + ["231 tests collected in 1.23s"]) + "\n", encoding="utf-8")
    assert CST.read_collected(str(listing)) == recorded + new
    assert CST.main(["--freshness-forecast", str(listing), "--nshards", "1"]) == 1     # 落ちる予報は exit 1
    assert CST.main(["--freshness-forecast", str(listing)]) == 2                         # 片の数が無い
    listing.write_text("\n".join(recorded + ["201 tests collected in 1.23s"]) + "\n", encoding="utf-8")
    assert CST.main(["--freshness-forecast", str(listing), "--nshards", "1"]) == 0
    listing.write_text("\n".join(recorded + ["999 tests collected in 1.23s"]) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="summary says 999"):
        CST.read_collected(str(listing))
    assert CST.main(["--freshness-forecast", str(listing), "--nshards", "1"]) == 2     # 読めない入力は緑にしない


def test_the_gates_job_does_not_wait_for_the_shards_and_reads_its_list_from_the_tool():
    jobs = _workflow_jobs()
    gates, regen, test = jobs["gates"], jobs["regen"], jobs["test"]
    assert test["needs"] == "changes" and test["if"] == "needs.changes.outputs.docs-only != 'true'"
    # 片を待たない(needs は changes だけ)。docs だけの PR の扱いは test と同じ条件
    early_jobs = [j for j in (gates, regen) if j["needs"] == "changes" and j["if"] == test["if"]]
    assert len(early_jobs) == 2
    # 一覧は道具が書いたファイルから読む。YAML にテストのファイル名を 1 つも写していない
    runs = _runs(gates)
    lister = [r for r in runs if "tools/ci_select_tests.py --early-list" in r]
    assert len(lister) == 1
    target = re.search(r"--early-list (\S+)", lister[0]).group(1)
    runner = [r for r in runs if re.search(r"^pytest -ra ", r, re.M)]
    assert len(runner) == 1 and runner[0].count(target) == 1
    lines = [ln.strip() for ln in runner[0].splitlines()]
    assert sum(ln.startswith("mapfile -t files < <(") and ln.endswith(" %s)" % target) for ln in lines) == 1
    # pytest には一覧の全部を渡し、絞る引数(-k・--deselect など)は付けない
    assert [ln for ln in lines if ln.startswith("pytest ")] == ['pytest -ra -q --durations=15 "${files[@]}"']
    assert runs.index(lister[0]) < runs.index(runner[0])
    assert sum(r.count("tests/test_") for r in runs) == 0
    assert "empty early list" in runner[0]                    # 0 件で緑にしない
    # 鮮度の予報は、先に回したテストが落ちても出す
    forecast = [s for s in gates["steps"] if "--freshness-forecast" in s.get("run", "")]
    assert len(forecast) == 1 and "--nshards" in forecast[0]["run"] and "!cancelled()" in forecast[0]["if"]
    # 準備(apt・pip・optional backend)は test の py3.11 と同じ文面
    by_name = {s.get("name"): s.get("run") for s in test["steps"] if s.get("run")}
    for job in (gates, regen):
        same = [s for s in job["steps"] if s.get("run") and by_name.get(s.get("name")) == s["run"]]
        assert len(same) == 4, [s.get("name") for s in same]
        assert job["env"] == test["env"]
        py = [s["with"]["python-version"] for s in job["steps"] if "setup-python" in s.get("uses", "")]
        assert py == ["3.11"]


def test_the_shards_still_run_everything_the_gates_job_runs(selector):
    jobs = _workflow_jobs()
    # 片の pytest は何も外していない(先頭のジョブの一覧を片は読まない)
    shard_runs = "\n".join(_runs(jobs["test"]))
    assert shard_runs.count('pytest "${args[@]}"') == 1
    assert sum(shard_runs.count(w) for w in ("--ignore", "--deselect", "ci_early", "--early-list")) == 0
    step = [s for s in jobs["test"]["steps"] if "FULLSEYE_CI_SHARD" in s.get("env", {})]
    assert len(step) == 1 and step[0]["run"].count('pytest "${args[@]}"') == 1
    assert sum(step[0]["run"].count(w) for w in (" -k ", " -m ", "-p no:")) == 0
    assert sorted(k for k in step[0]["env"] if k.startswith("FULLSEYE_CI_")) == [
        "FULLSEYE_CI_SELECTION", "FULLSEYE_CI_SHARD"]
    # 全数の片分け: 先頭のジョブで回すファイルも門も、6 片のどれかにちょうど 1 回入る(件数は 1 件も減らない)
    with open(os.path.join(ROOT, ".test_durations"), encoding="utf-8") as f:
        durations = json.load(f)
    early = CST.early_plan(selector.always, CST.load_failure_history())["tests"]
    wanted = sorted(set(early) | set(selector.always))
    recorded_files = {n.split("::", 1)[0] for n in durations}
    nodeids = sorted(durations) + ["%s::test_not_recorded_yet" % f for f in wanted if f not in recorded_files]
    plan = CST.shard_plan(nodeids, CST.MAX_SHARDS, durations)
    assert len(plan) == 6 and sum(len(p) for p in plan) == len(nodeids) >= 20000
    assert len(set().union(*[set(p) for p in plan])) == len(nodeids)
    holders = {f: sum(1 for p in plan if any(n.split("::", 1)[0] == f for n in p)) for f in wanted}
    assert len(wanted) >= 30 and sum(1 for f in wanted if holders[f] == 1) == len(wanted)
    # 生成物の回し忘れは 1 か所で、PR・master・毎日のどれでも走る条件(イベントで絞らない)
    regen_steps = [(name, r) for name, job in jobs.items() for r in _runs(job) if "regen_all.py --check" in r]
    assert [name for name, _ in regen_steps] == ["regen"]
    assert "event_name" not in jobs["regen"]["if"] and "mode" not in jobs["regen"]["if"]


# --------------------------------------------------------------------------- #
# 独立レビュー 3 回目(2026-11-10): 文字列の個数ではなく挙動と完全一致で門にする           #
# --------------------------------------------------------------------------- #
# ci.yml を 1 か所ずつ壊す 18 通りのうち 15 が、それまでの構造テストを通っていた(赤が緑に見える壊し方)。
# (1) シェルの step は取り出して実行する (2) continue-on-error と step の if は一覧と一致
# (3) 門の run は行の完全一致、片の引数は許可リスト (4) concurrency は式の完全一致(上のテスト)。
import shutil


def _bash():
    """bash の実体。Linux(CI)に無ければ**失敗**(skip にしない)。Windows は Git の bash を探す
    (System32 の bash は WSL の起動口で、Windows のパスを読めない)。"""
    if sys.platform != "win32":
        found = shutil.which("bash")
        assert found, "bash is required to run the workflow's shell steps"
        return found
    cands = []
    git = shutil.which("git")
    if git:
        here = os.path.dirname(os.path.realpath(git))
        for up in (os.path.dirname(here), os.path.dirname(os.path.dirname(here))):
            cands += [os.path.join(up, "bin", "bash.exe"), os.path.join(up, "usr", "bin", "bash.exe")]
    which = shutil.which("bash")
    if which and "system32" not in which.lower():
        cands.append(which)
    for c in cands:
        if os.path.isfile(c):
            return c
    pytest.skip("no Git Bash on this Windows machine (the Linux runners always run this)")


# 偽の gh: 応答は $FAKE_GH_DIR のファイル(--jq を通した後の形を書いておく)。FAKE_GH_MODE=fail は全部失敗。
_FAKE_GH = """#!/bin/sh
if [ "$FAKE_GH_MODE" = fail ]; then exit 1; fi
case "$1 $2" in
  "run list") cat "$FAKE_GH_DIR/runs" ;;
  "api repos/o/r/pulls/7") cat "$FAKE_GH_DIR/labels" ;;
  "api repos/o/r/actions/runs/"*)
    id=${2#repos/o/r/actions/runs/}; id=${id%%/*}
    [ -f "$FAKE_GH_DIR/artifacts_$id" ] || exit 1
    cat "$FAKE_GH_DIR/artifacts_$id" ;;
  *) exit 1 ;;
esac
"""


def _posix(path):
    return str(path).replace("\\", "/")


def _run_step(tmp_path, script, env, *, cwd=None, mode="ok"):
    """workflow の step の ``run`` を、偽の gh を PATH の先頭に置いて ``bash -e`` で走らせ、GITHUB_OUTPUT の行を返す。"""
    bash = _bash()
    bindir = tmp_path / "fake_bin"
    bindir.mkdir(exist_ok=True)
    gh = bindir / "gh"
    gh.write_text(_FAKE_GH, encoding="utf-8", newline="\n")
    gh.chmod(0o755)
    step = tmp_path / "step.sh"
    step.write_text(script, encoding="utf-8", newline="\n")
    out = tmp_path / "github_output.txt"
    out.write_text("", encoding="utf-8")
    full = dict(os.environ)
    full.update(env)
    full.update(PATH=os.pathsep.join([str(bindir), os.path.dirname(bash), os.environ.get("PATH", "")]),
                FAKE_GH_MODE=mode, FAKE_GH_DIR=_posix(tmp_path), REPO="o/r", GH_TOKEN="not-a-token",
                GITHUB_OUTPUT=_posix(out), GITHUB_STEP_SUMMARY=_posix(tmp_path / "summary.md"))
    r = subprocess.run([bash, "-e", _posix(step)], cwd=str(cwd or tmp_path), env=full, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, r.stdout + r.stderr
    return out.read_text(encoding="utf-8").splitlines()


def _step(job, step_id):
    return next(s for s in _workflow_jobs()[job]["steps"] if s.get("id") == step_id)


def _write(path, *lines):
    path.write_text("".join("%s\n" % ln for ln in lines), encoding="utf-8", newline="\n")


def test_the_label_step_runs_everything_when_the_labels_cannot_be_read(tmp_path):
    """label の step を実際に走らせる。読めない → full(選んだテストだけ、には倒れない)。"""
    script = _step("changes", "label")["run"]
    env = {"PR": "7"}
    unreadable = _run_step(tmp_path, script, env, mode="fail")
    assert "full=true" in unreadable and "full=false" not in unreadable
    _write(tmp_path / "labels", "bug", "ci:full")
    labelled = _run_step(tmp_path, script, env)
    assert "full=true" in labelled and "full=false" not in labelled
    _write(tmp_path / "labels", "bug", "ci:fuller", "not ci:full", "CI:FULL")     # 完全一致・大文字小文字を区別
    assert _run_step(tmp_path, script, env) == ["full=false"]
    _write(tmp_path / "labels")
    assert _run_step(tmp_path, script, env) == ["full=false"]


def _git(cwd, *args):
    r = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false",
                        "-c", "core.hooksPath=.git/no-hooks", "-c", "core.autocrlf=false", *args],
                       cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def test_a_docs_push_that_replaced_a_waiting_code_push_still_runs_the_full_suite(tmp_path):
    """push の docs-only の範囲は「テストが実際に走った最後の run」から(直前の push からではない)。

    レビューの手順: c0 の run は全数を走った → c1(コード)の run は待ちのまま c2(docs だけ)に置き換えられた。
    c2 の run が c1..c2 だけを見ると docs だけと判定して全部飛ばし、c1 は全数を通らない。
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    shas = []
    for name in ("a.py", "b.py", "notes.md"):
        (repo / name).write_text("x\n", encoding="utf-8")
        _git(repo, "add", name)
        _git(repo, "commit", "-q", "--no-verify", "-m", name)
        shas.append(_git(repo, "rev-parse", "HEAD"))
    c0, c1, c2 = shas
    script = _step("changes", "classify")["run"]
    env = {"EVENT_NAME": "push", "BASE_REF": "", "RUN_ID": "99"}

    def classify(mode="ok"):
        return _run_step(tmp_path, script, env, cwd=repo, mode=mode)

    def runs(*rows):
        _write(tmp_path / "runs", *("%s %s" % r for r in rows))

    def artifacts(run, *names):
        _write(tmp_path / ("artifacts_%s" % run), *names)

    runs((99, c2), (20, c0))
    artifacts(99, "ci-result-" + c2)                 # 自分の run(再実行で artifact が残っていても)は数えない
    artifacts(20, "ci-result-" + c0)
    assert classify() == ["docs-only=false"]
    # c1 の run が「docs だけ」で全部 skip(success、artifact なし)だった場合も、c1 は範囲に残る
    runs((99, c2), (30, c1), (20, c0))
    artifacts(30)
    assert classify() == ["docs-only=false"]
    # c1 の run がテストを走らせていれば、c2 は docs だけ(docs-only の省略そのものは生きている)
    artifacts(30, "ci-result-" + c1)
    assert classify() == ["docs-only=true"]
    # 名前は run の sha と完全一致で見る(別の sha の記録・別の artifact では数えない)
    artifacts(30, "ci-result-" + c0, "junit-py3.11-shard1", "ci-result-" + c1 + "-x")
    assert classify() == ["docs-only=false"]
    # 取れないときは全部回す: gh の失敗 / artifact のある run が無い / この木に無い sha
    artifacts(30, "ci-result-" + c1)
    assert classify(mode="fail") == ["docs-only=false"]
    artifacts(30)
    artifacts(20)
    assert classify() == ["docs-only=false"]
    runs((30, "0" * 40))
    artifacts(30, "ci-result-" + "0" * 40)
    assert classify() == ["docs-only=false"]


def test_the_failure_record_range_starts_at_the_same_run_as_the_docs_only_check(tmp_path):
    """failure-record の prev も同じ条件で選ぶ(同じ行)。regen・gates の結果も記録の道具へ渡す。"""
    prev = _step("failure-record", "prev")["run"]
    core = [ln.strip() for ln in prev.splitlines()]
    block = core[core.index('base=""'): core.index('done <<<"$runs"') + 2]
    assert block[-1] == "fi" and len(block) == 12
    other = [ln.strip() for ln in _step("changes", "classify")["run"].splitlines()]
    at = other.index(block[0])
    assert other[at: at + len(block)] == block
    a, b, c = "a" * 40, "b" * 40, "c" * 40
    env = {"RUN_ID": "99"}
    _write(tmp_path / "runs", "99 " + c, "30 " + b, "20 " + a)
    _write(tmp_path / "artifacts_99", "ci-result-" + c)
    _write(tmp_path / "artifacts_30")                 # docs だけの run: 完了して success だが、テストは走っていない
    _write(tmp_path / "artifacts_20", "ci-result-" + a)
    assert _run_step(tmp_path, prev, env) == ["sha=" + a]
    assert _run_step(tmp_path, prev, env, mode="fail") == ["sha="]
    job = _workflow_jobs()["failure-record"]
    assert job["needs"] == ["changes", "test", "regen", "gates"]
    rec = next(s for s in job["steps"] if "ci_failure_record.py" in s.get("run", ""))
    assert rec["env"]["BEFORE"] == "${{ steps.prev.outputs.sha || github.event.before }}"
    for flag, var in (("--test-result", "TEST"), ("--regen-result", "REGEN"), ("--gates-result", "GATES")):
        assert '%s "$%s_RESULT"' % (flag, var) in rec["run"]
        assert rec["env"]["%s_RESULT" % var] == "${{ needs.%s.result }}" % var.lower()


def test_failure_record_keeps_the_results_of_the_regen_and_gates_jobs(tmp_path):
    junit = tmp_path / "junit"
    junit.mkdir()
    out, summary = tmp_path / "r.json", tmp_path / "s.md"
    assert CFR.main([str(junit), "--sha", "0" * 40, "--test-result", "success", "--regen-result", "failure",
                     "--gates-result", "success", "-o", str(out), "--summary", str(summary)]) == 0
    rec = json.loads(out.read_text(encoding="utf-8"))
    assert (rec["test_result"], rec["regen_result"], rec["gates_result"]) == ("success", "failure", "success")
    text = summary.read_text(encoding="utf-8")
    assert "`regen (regen_all --check)` job did not succeed: failure" in text
    assert "`gates` job did not succeed" not in text


# job と step の `if`: ここに無い条件が 1 つでも付けば赤(門を条件つきで飛ばす壊し方を作りごと防ぐ)。
_STEP_IFS = {
    "gates": {
        "The test selection (PR only)": "needs.changes.outputs.mode == 'selected'",
        "Freshness forecast (test_test_durations_is_fresh on the session its shard will see)":
            "${{ !cancelled() && (steps.early.conclusion == 'success' || steps.early.conclusion == 'failure') }}",
    },
    "regen": {},
    "test": {
        "Record the installed versions (main)":
            "github.event_name != 'pull_request' && matrix.python-version == '3.11' && matrix.shard == 1",
        "Optional backends (py3.11 only — 不変条件を実際に走らせる)": "matrix.python-version == '3.11'",
        "Record the installed versions (with the optional backends)":
            "github.event_name != 'pull_request' && matrix.python-version == '3.11' && matrix.shard == 1",
        "Upload the installed versions (baseline for PR dependency checks)":
            "github.event_name != 'pull_request' && matrix.python-version == '3.11' && matrix.shard == 1",
        "The test selection (PR only)": "needs.changes.outputs.mode == 'selected'",
        "Name this shard's duration data": "always()",
        "Upload test durations": "always()",
        "Upload JUnit (失敗の記録へ)": "always()",
        "Upload coverage data (py3.11, this shard)":
            "matrix.python-version == '3.11' && needs.changes.outputs.mode == 'full'",
    },
}
_NEVER_IN_A_GATE = ("|| true", "|| :", "set +e", "exit 0", "continue-on-error")


def _lines(run):
    return [ln.strip() for ln in run.strip().splitlines()]


def test_the_blocking_jobs_cannot_turn_green_without_running_their_gates():
    """gates・regen・test: 落ちても緑(continue-on-error・`|| true`・`set +e`)と、走らず緑(if・絞る引数)を拒む。"""
    jobs = _workflow_jobs()
    for name, expected in _STEP_IFS.items():
        job = jobs[name]
        assert job["needs"] == "changes" and job["if"] == "needs.changes.outputs.docs-only != 'true'", name
        assert "continue-on-error" not in job and "defaults" not in job, name
        assert [s.get("name") for s in job["steps"] if "continue-on-error" in s or "shell" in s] == [], name
        assert {s.get("name"): s["if"] for s in job["steps"] if "if" in s} == expected, name
    gates = {s.get("name"): s for s in jobs["gates"]["steps"]}
    # 門の run は行の完全一致(1 行足す・`|| true`・`head`・`exit 0` を許さない)
    assert _lines(gates["List the early tests (tools/ci_select_tests.py --early-list)"]["run"]) == [
        'python tools/ci_select_tests.py --early-list ci_early_tests.txt --summary "$GITHUB_STEP_SUMMARY"']
    assert _lines(gates["Run the early tests"]["run"]) == [
        "mapfile -t files < <(sed -e '/^$/d' ci_early_tests.txt)",
        '[[ ${#files[@]} -gt 0 ]] || { echo "empty early list"; exit 1; }',
        'pytest -ra -q --durations=15 "${files[@]}"',
    ]
    forecast = gates["Freshness forecast (test_test_durations_is_fresh on the session its shard will see)"]["run"]
    assert _lines(forecast) == [
        "files=()",
        "selection=()",
        'if [[ "$MODE" == selected ]]; then',
        "mapfile -t files < <(grep -v '^#' ci-selection/ci_selected_tests.txt | sed -e 's/::.*$//' -e '/^$/d' | sort -u)",
        '[[ ${#files[@]} -gt 0 ]] || { echo "empty selection"; exit 1; }',
        "selection=(--selection ci-selection/ci_selected_tests.txt)",
        "fi",
        'pytest --collect-only -q "${files[@]}" > ci_collected.txt || { tail -n 60 ci_collected.txt; exit 1; }',
        "tail -n 1 ci_collected.txt",
        'python tools/ci_select_tests.py --freshness-forecast ci_collected.txt --nshards "$NSHARDS" "${selection[@]}"',
    ]
    regen = [s for s in jobs["regen"]["steps"] if "regen_all" in s.get("run", "")]
    assert [_lines(s["run"]) for s in regen] == [["python tools/regen_all.py --check"]]
    assert jobs["regen"]["steps"][-1] is regen[0]
    # 片: pytest に渡す引数は許可リスト(--collect-only・-k・--deselect などは 1 つも足せない)。呼び出しは最後の 1 行
    shard = [s for s in jobs["test"]["steps"] if s.get("name", "").startswith("Run tests with coverage")]
    assert len(shard) == 1
    lines = _lines(shard[0]["run"])
    assert lines[-1] == 'pytest "${args[@]}"' and sum("pytest" in ln for ln in lines) == 1
    tokens = [tok for ln in lines for m in re.finditer(r"args\+?=\(([^)]*)\)", ln) for tok in m.group(1).split()]
    assert sorted(tokens) == sorted([
        "-ra", '"--junitxml=junit-py$PYV-shard$SHARD.xml"', "--durations-path", ".test_durations",
        "--store-durations", "-v", "--timeout-method=signal", "-q", "--cov", '"${files[@]}"'])
    assert sum(ln.count("args") for ln in lines) == 6            # 5 つの代入 + 呼び出し。ほかの形で args を触らない
    scripts = [(job, s.get("name"), s["run"]) for job in ("gates", "regen") for s in jobs[job]["steps"]
               if s.get("run")]
    assert len(scripts) >= 10                                  # 空の一覧を見て通るのを防ぐ(今は 7 + 5)
    assert [(job, name, bad) for job, name, run in scripts for bad in _NEVER_IN_A_GATE if bad in run] == []
    assert not [bad for bad in _NEVER_IN_A_GATE if bad in shard[0]["run"]]


def test_hand_edited_inputs_of_the_early_list_are_refused(tmp_path):
    """実績の表は tests/ の下のテストのファイルだけ。必ず回す一覧の打ち間違いは黙って落とさない(rc 2)。"""
    with open(os.path.join(ROOT, CST.FAILURE_HISTORY), encoding="utf-8") as f:
        good = json.load(f)
    path = tmp_path / "history.json"
    for bad in ("tools/ci_select_tests.py", "tests/conftest.py", "../tests/test_x.py", "tests/test_x.py::test_a",
                "--deselect=tests/test_x.py", "tests/test_x.py --collect-only", "examples/poc_x.py"):
        files = dict(good["files"])
        files[bad] = {"failed_runs": 1, "branches": 1}
        path.write_text(json.dumps(dict(good, files=files)), encoding="utf-8")
        with pytest.raises(ValueError, match="not a test file under tests/"):
            CST.load_failure_history(path)
    # 形の正しい名前でこの木に無いもの(消したテスト)は読める。先頭の一覧には入らず、理由つきで残る
    files = dict(good["files"])
    files["tests/test_removed_long_ago.py"] = {"failed_runs": 50, "branches": 9}
    path.write_text(json.dumps(dict(good, files=files)), encoding="utf-8")
    plan = CST.early_plan([], CST.load_failure_history(path))
    gone = [r for r in plan["rows"] if r["file"] == "tests/test_removed_long_ago.py"]
    assert len(gone) == 1 and gone[0]["early"] is False and gone[0]["why"] == "not in this tree"
    assert "tests/test_removed_long_ago.py" not in plan["tests"]
    # 必ず回す一覧の打ち間違い: 一覧を書かずに rc 2
    with open(os.path.join(ROOT, "tools", "ci_always_run.txt"), encoding="utf-8") as f:
        real = f.read()
    always = tmp_path / "always.txt"
    always.write_text(real + "\ntests/test_this_gate_was_mistyped.py\n", encoding="utf-8")
    target = tmp_path / "early.txt"
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "ci_select_tests.py"), "--early-list", str(target),
                        "--always-file", str(always)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 2 and "tests/test_this_gate_was_mistyped.py" in r.stderr
    assert not target.exists()


# --------------------------------------------------------------------------- #
# ★PoC の門はテスト単位で片に散らす(2026-11-11、SPLIT_BY_TEST)                  #
# --------------------------------------------------------------------------- #
# run 42982984881: py3.12 片 1 = 71 分。片 1 は tests/test_poc_scripts_run.py の 310 本だけで、このファイル
# 1 つ(3,738 秒)が 6 片の平均(約 3,507 秒)を超えるので、ファイル単位では持った片が必ず最長になっていた。
_POC = "tests/test_poc_scripts_run.py"
_POC_GATE = _POC + "::test_the_gate_actually_sees_all_of_them"


def _poc_ids(m):
    return [_POC + "::test_the_poc_runs_clean[poc_%03d.py]" % i for i in range(m)]


def test_poc_runner_is_split_by_test_once_each_with_the_file_average_weight():
    assert CST.SPLIT_BY_TEST == (_POC,)
    others = ["tests/test_x%d.py::t" % i for i in range(5)]
    ids = others + _poc_ids(40) + [_POC_GATE]
    flat_rec = {x: 10.0 for x in ids}                    # 記録の合計 410 秒 / 41 本 = 10 秒ずつ
    # 同じ合計を 1 件に寄せた記録(CI の実際の形: 一括実行の時間が最初の 1 件に付き、残りは 0 秒)
    skew_rec = dict({x: 10.0 for x in others}, **{x: 0.0 for x in ids if x.startswith(_POC)})
    skew_rec[_poc_ids(40)[0]] = 410.0
    for n in (1, 2, 3, 6, 8):
        plan = CST.shard_plan(ids, n, flat_rec)
        flat = [x for p in plan for x in p]
        assert len(flat) == len(set(flat)) == len(ids) and set(flat) == set(ids)   # 落とさない・重ねない
        where = {x: i for i, p in enumerate(plan) for x in p}
        assert sum(1 for p in plan if _POC_GATE in p) == 1                         # PoC 以外のテストも 1 片
        assert len({where[x] for x in _poc_ids(40)}) == n                          # 全部の片に散る
        # 1 件ごとの記録値は重さに使わない(ファイルの合計 ÷ 本数): 寄せた記録でも同じ答え
        assert CST.shard_plan(ids, n, skew_rec) == plan
        # 決定的で、PoC の並びに依らない(同じ重さの PoC は名前の順で配る)
        rev = CST.shard_plan(others + list(reversed(_poc_ids(40))) + [_POC_GATE], n, flat_rec)
        assert {x: i for i, p in enumerate(rev) for x in p} == where


def test_poc_runner_split_on_the_real_baseline_shortens_the_longest_shard():
    with open(os.path.join(ROOT, ".test_durations"), encoding="utf-8") as f:
        d = json.load(f)
    ids = sorted(d)
    poc_total = sum(v for k, v in d.items() if k.startswith(_POC + "::"))
    pocs = [x for x in ids if x.startswith(_POC + "::test_the_poc_runs_clean[")]
    assert poc_total > 3000 and len(pocs) > 250
    for n in (1, 2, 3, 6, 8):
        plan, loads = CST._shard_plan_with_loads(ids, n, d)
        assert sum(len(p) for p in plan) == len(ids) == len(set().union(*[set(p) for p in plan]))
        holders = [sum(1 for p in plan if x in set(p)) for x in pocs]
        assert holders == [1] * len(pocs)
        assert abs(sum(loads) - sum(d.values())) < 1e-6 * sum(d.values())         # 重さの総量は変えない
    plan, loads = CST._shard_plan_with_loads(ids, 6, d)
    assert max(loads) < poc_total, (loads, poc_total)                              # 1 ファイルが下限ではなくなった
    assert max(loads) <= 1.02 * (sum(loads) / 6), loads
    info = CST.plan_session(ids, selection=None, shard="1/6", durations_path=CST.ROOT / ".test_durations")
    assert info["est_seconds"] == round(loads[0]) and info["sizes"] == [len(p) for p in plan]


def test_poc_runner_split_holds_with_a_pr_selection(tmp_path):
    sel = tmp_path / "sel.txt"
    chosen = _poc_ids(30)[::3]
    sel.write_text(chr(10).join(["tests/test_x0.py"] + chosen) + chr(10), encoding="utf-8")
    ids = ["tests/test_x0.py::a", "tests/test_x0.py::b", "tests/test_x1.py::c"] + _poc_ids(30) + [_POC_GATE]
    dur = tmp_path / "d.json"
    dur.write_text(json.dumps({x: 5.0 for x in ids}), encoding="utf-8")
    for n in (1, 2, 3, 6):
        kept = [CST.plan_session(ids, selection=str(sel), shard="%d/%d" % (k, n), durations_path=dur)["keep"]
                for k in range(1, n + 1)]
        flat = [x for p in kept for x in p]
        assert sorted(flat) == sorted(["tests/test_x0.py::a", "tests/test_x0.py::b"] + chosen)
        assert len(flat) == len(set(flat))
    # PR の見積もり(片の数を決める側)も 1 件ごとの記録値ではなくファイルの平均で数える
    skew = {x: 0.0 for x in _poc_ids(30)}
    skew[_poc_ids(30)[0]] = 300.0
    skew_path = tmp_path / "skew.json"
    skew_path.write_text(json.dumps(skew), encoding="utf-8")
    assert CST.estimate_seconds(chosen, skew_path) == pytest.approx(10.0 * len(chosen))
    with pytest.raises(ValueError):
        CST.plan_session(ids, selection=None, shard="7/6", durations_path=dur)      # 壊れた指定は止める


def test_the_poc_fixture_runs_only_the_pocs_left_in_the_session(monkeypatch):
    spec = importlib.util.spec_from_file_location("_poc_runner_t20261111", os.path.join(ROOT, _POC))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ran = []
    monkeypatch.delenv("PYTEST_XDIST_WORKER", raising=False)
    monkeypatch.setattr(mod, "_run_one", lambda path: (ran.append(path.name), (path.name, 0, ""))[1])
    names = [x.name for x in mod._poc_paths()]
    assert len(names) > 50
    keep = names[3:6]

    def item(n):
        return types.SimpleNamespace(originalname="test_the_poc_runs_clean", callspec=types.SimpleNamespace(params={"name": n}))
    request = types.SimpleNamespace(session=types.SimpleNamespace(
        items=[item(n) for n in keep] + [types.SimpleNamespace(originalname="test_the_gate_actually_sees_all_of_them")]))
    out = mod.poc_results.__wrapped__(request)
    assert sorted(ran) == sorted(keep) and sorted(out) == sorted(keep)
