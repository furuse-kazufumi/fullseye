# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""外部 AI のレビュー(PyPI 0.6.0 を導入して実測)を一次検証して、本物だった項目の回帰テスト。

判定(2026-10-18、0.6.0 の venv と origin/master 9ba3ba8450 の両方で再現):

* N217 ``fullseye ops list`` が rc=2 —— 本物(文書の書式は ``fullseye ops`` だが、``algo list`` と非対称)。
* N224 ``apply`` の引数の取り違えの文が、受け取った image 側を言わない —— 本物(文言)。
* N209 ``save(img, path)`` の TypeError が「逆順」と言わない —— 文書不足 + 文言。
* N228 ``fullseye index`` の書き先の判定が ``site-packages/docs`` の有無だけ —— 本物(潜在)。
  再現の途中で、OpenCV の無い素の導入では ``fullseye index`` が AssertionError で落ちることも見つけた。
* 「SGM が無い」—— 誤検出。``fullseye.disparity_sgm`` は在るが、op_find がファサード層を見ておらず 0 件だった
  (探す側の欠陥は本物)。
* N226 族名(optdraw / simcal / octscan)で 0 件 —— 0.6.0 には族そのものが無い。master では引ける。
"""
from __future__ import annotations

import os
import subprocess
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import fullseye as fs  # noqa: E402
import imgevolve  # noqa: E402
import opassist  # noqa: E402


# --------------------------------------------------------------------------- #
# N217: `fullseye ops list`
# --------------------------------------------------------------------------- #
def test_ops_list_is_accepted_like_algo_list(tmp_path):
    """``fullseye ops list`` は ``fullseye ops`` と同じ一覧を出す(以前は rc=2)。"""
    env = dict(os.environ, PYTHONPATH=ROOT, PYTHONIOENCODING="utf-8")
    run = [sys.executable, os.path.join(ROOT, "imgevolve.py")]
    a = subprocess.run(run + ["ops", "list"], capture_output=True, text=True, encoding="utf-8",
                       cwd=str(tmp_path), env=env, timeout=600)
    assert a.returncode == 0, a.stderr[-600:]
    b = subprocess.run(run + ["ops"], capture_output=True, text=True, encoding="utf-8",
                       cwd=str(tmp_path), env=env, timeout=600)
    assert b.returncode == 0
    assert a.stdout == b.stdout and a.stdout.count("\n") > 500
    # 探針: 知らない語は今までどおり拒む(何でも通す口にしない)
    c = subprocess.run(run + ["ops", "lst"], capture_output=True, text=True, encoding="utf-8",
                       cwd=str(tmp_path), env=env, timeout=600)
    assert c.returncode == 2


# --------------------------------------------------------------------------- #
# N224 / N209: 引数の取り違えを、受け取った物と直した呼び方で言う
# --------------------------------------------------------------------------- #
def test_apply_swapped_names_both_arguments_and_the_fix():
    img = np.zeros((4, 4, 3))
    with pytest.raises(TypeError) as e:
        fs.apply("access_channel", img, 0)
    msg = str(e.value)
    assert "image='access_channel'" in msg and "name=ndarray" in msg
    assert "fullseye.apply(<image>, 'access_channel'" in msg


def test_save_swapped_says_swapped(tmp_path):
    p = str(tmp_path / "x.png")
    with pytest.raises(TypeError, match="swapped"):
        fs.save(np.zeros((4, 4)), p)
    assert not os.path.exists(p)
    # 対照群: 正しい順は書ける / path が配列で arr が配列のときは従来の文
    fs.save(p, np.zeros((4, 4)))
    assert os.path.exists(p)
    with pytest.raises(TypeError, match="path must be"):
        fs.save(np.zeros((4, 4)), np.zeros((4, 4)))


# --------------------------------------------------------------------------- #
# N228: index の書き先と、OpenCV の無い導入
# --------------------------------------------------------------------------- #
def test_index_does_not_write_into_a_foreign_docs_dir(tmp_path, monkeypatch):
    """site-packages に別のパッケージの ``docs/`` が在っても、そこを checkout と見なさない。"""
    site = tmp_path / "site-packages"
    (site / "docs").mkdir(parents=True)
    monkeypatch.setattr(imgevolve, "HERE", str(site))
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    assert imgevolve._index_default_out() == os.path.join(str(work), "OP_INDEX.json")
    # 対照群: checkout(docs/OP_INDEX.json と tools/regen_all.py が在る)なら docs/ へ
    (site / "docs" / "OP_INDEX.json").write_text("{}", encoding="utf-8")
    (site / "tools").mkdir()
    (site / "tools" / "regen_all.py").write_text("", encoding="utf-8")
    assert imgevolve._index_default_out() == os.path.join(str(site), "docs", "OP_INDEX.json")


def test_index_builds_without_opencv(monkeypatch):
    """素の ``pip install fullseye``(OpenCV 無し)では color 層が空なのが正しい —— 落ちない。"""
    import backends_color as CL
    monkeypatch.setattr(CL, "coverage", lambda: {"n_ops": 0, "halcon_names": [], "has_cv2": False})
    out = imgevolve._build_op_index()
    assert "color" not in out["tiers"] and out["n_ops"] > 3000
    # 探針: OpenCV が在るのに空なら、今までどおり止める
    monkeypatch.setattr(CL, "coverage", lambda: {"n_ops": 0, "halcon_names": [], "has_cv2": True})
    with pytest.raises(AssertionError, match="color"):
        imgevolve._build_op_index()


# --------------------------------------------------------------------------- #
# 「SGM が無い」の誤検出の根: op_find がファサード層を見ていなかった
# --------------------------------------------------------------------------- #
def test_op_find_reaches_facade_only_functions():
    hits = fs.op_find("sgm")
    top = hits[0]
    assert top["op"] == "disparity_sgm" and top["ledger"] == "facade" and top["match"] == "name"
    assert top["call"] == "fullseye.disparity_sgm(...)"
    names = [h["op"] for h in fs.op_find("disparity", limit=50)]
    assert {"disparity_sgm", "disparity_census", "disparity_map"} <= set(names)


def test_the_found_sgm_actually_matches_a_known_shift():
    """見つかった物が本当に対応付けを計算するか —— 真値の分かる横ずれで採点する。"""
    rng = np.random.default_rng(20261018)
    left = rng.random((48, 72))
    right = np.roll(left, -6, axis=1)          # 右画像 = 左を 6 画素ずらしたもの(真の視差 6)
    d = np.asarray(fs.disparity_sgm(left, right, max_disp=16))
    inner = d[6:-6, 20:-8]
    assert float(np.median(inner)) == 6.0
    assert float(np.mean(inner == 6.0)) > 0.95
    # 探針: ずらさなければ視差は 0 に寄る(当て推量で 6 を返していない)
    d0 = np.asarray(fs.disparity_sgm(left, left, max_disp=16))
    assert float(np.median(d0[6:-6, 20:-8])) == 0.0


def test_facade_tier_does_not_shadow_op_table_rows():
    """同じ名前が op 表にも在れば、そちらの行が勝つ(ファサードは重複して出さない)。"""
    for q in ("gauss_filter", "msa_gauge_rr"):
        hits = fs.op_find(q)
        assert hits[0]["op"] == q and hits[0]["ledger"] != "facade"
        assert sum(1 for h in hits if h["op"] == q) == 1


@pytest.mark.parametrize("family, member", [("optdraw", "lens_section_drawing"),
                                            ("simcal", "simcal_validate"),
                                            ("octscan", "oct_design")])
def test_family_names_find_their_members(family, member):
    """N226: 族名(モジュール名)のクエリで族の op が引ける(0.6.0 は族そのものが未収録)。"""
    assert member in [h["op"] for h in fs.op_find(family, limit=40)]


def test_facade_callables_exclude_modules():
    import types
    rows = opassist._facade_callables()
    assert len(rows) > 1000
    assert not any(isinstance(o, types.ModuleType) for _, o in rows)
