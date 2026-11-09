# -*- coding: utf-8 -*-
"""``fullseye_make_task`` / ``fullseye_score_pipeline`` の門(2026-11-09、独立レビューの指摘で 11-10 に増補)。

1. 族ごとに、正しい処理が合格し、わざと間違えた(もっともらしい)処理が不合格になる。
2. 真値が返り値のどこにも出ない(返り値の JSON 全体と本文を走査する)。
3. fail-closed: 例外・型の不一致・NaN・空・定数・知らない / 期限切れ / 使い切りの task_id。
4. 決定性: 同じ (kind, seed, params) から同じ task_id・同じ入力のバイト列・同じ採点。
5. 課題の入力に縛る(F1): 他のハンドル・取り込んだ答え・生成源の段は foreign_input。
6. 採点の回数は (kind, seed) ごと(F2): つまみの微小な変更・追い出し・期限切れで戻らない。
7. feedback の段階(F3)と実験モードの秘密値(F4)。
8. 採点器の中身(F5): 適用する許容 = 公表する許容 = 事前登録の表、誤差の符号を返さない、
   指標ごとの不合格の例、位相のずれは 2πm だけ許す。
9. 保管庫の lock(F9)。

正しい処理と間違えた処理は作った後に手で組んだもの。正しい処理の窓幅は seed 0〜49 で選んだ
(調整用の seed)。許容範囲は ``fullseye/mcp/task_tolerances.py``(事前登録の表)。
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import threading
import time

import numpy as np
import pytest

from fullseye.mcp import Catalog, call_tool
from fullseye.mcp import server as S
from fullseye.mcp import task_tolerances as TT
from fullseye.mcp import tasks as T
from fullseye.mcp.handles import HandleStore

#: 族ごとの (正しい処理, もっともらしく間違えた処理)。
PIPELINES = {
    # 照明むらを大域の Otsu で拾うと、暗い側の背景と明るい側の粒が混ざる。
    # top-hat の窓は粒(直径 6〜12 px)を包む 9 px。既定の 5 px では seed 50 本中 18 本で 1〜4 個数え違えた。
    "blob_count": ([{"op": "gaussian"}, {"op": "tophat", "a": 0.9}, {"op": "otsu"}, {"op": "count_obj"}],
                   [{"op": "otsu"}, {"op": "count_obj"}]),
    # 二値化してから端を取ると、しきい値の高さぶん端がずれる(画素の量子化より大きい)。
    "edge_subpixel": ([{"op": "gaussian"}, {"op": "m1_measure_pos"}],
                      [{"op": "threshold_sub_pix"}]),
    # 加工目の周期(横 7 px)で平均すると縞が消える。大域の Otsu は照明むらの片側を拾う。
    "defect_inspect": ([{"op": "mean_box_wh", "a": 0.4, "b": 0.0}, {"op": "invert_image"},
                        {"op": "xsitk_maxentropy_thresh"}, {"op": "select_largest"}],
                       [{"op": "invert_image"}, {"op": "otsu"}, {"op": "select_largest"}]),
    # 巻き込み位相のまま返すと 2π の段差が残る(展開し忘れ)。
    "fringe_phase": ([{"op": "decode_fringe"}],
                     [{"op": "wrapped_phase"}]),
}
SEEDS = (0, 1, 2)


@pytest.fixture(scope="module")
def cat():
    return Catalog.load()


@pytest.fixture(autouse=True)
def _public_mode(monkeypatch):
    """手元の環境変数で実験モードに入らないようにする(入れたいテストは TaskStore を直接作る)。"""
    monkeypatch.delenv(T.SECRET_ENV, raising=False)
    monkeypatch.delenv(T.FEEDBACK_ENV, raising=False)


def _store():
    return HandleStore(roots=[])


def _make(cat, store, kind, seed=0, **params):
    args = {"kind": kind, "seed": seed}
    if params:
        args["params"] = params
    r = call_tool("fullseye_make_task", args, cat, store)
    assert r["isError"] is False, r["content"][0]["text"]
    return r


def _score(cat, store, task_id, stages, **extra):
    return call_tool("fullseye_score_pipeline", {"task_id": task_id, "stages": stages, **extra}, cat, store)


def _rec(store, task_id):
    return store._fullseye_tasks._items[task_id]


# --------------------------------------------------------------------------- #
# 0. 道具の登録と族の数                                                          #
# --------------------------------------------------------------------------- #
def test_tools_are_in_full_profile_only_and_families_span_four_fields():
    assert {"fullseye_make_task", "fullseye_score_pipeline"} <= set(S.TOOLS)
    assert not ({"fullseye_make_task", "fullseye_score_pipeline"} & S.MINIMAL_TOOLS)
    assert len(T.FAMILIES) >= 4
    assert len({f.field for f in T.FAMILIES.values()}) == len(T.FAMILIES), "族の分野が重なっている"
    assert set(PIPELINES) == set(T.FAMILIES), "族を足したら正しい処理と間違えた処理もここに足す"
    assert S.TOOLS["fullseye_make_task"]["inputSchema"]["properties"]["kind"]["enum"] == sorted(T.FAMILIES)
    # 採点の stages は fullseye_pipeline と同じ形(同じ schema の物)
    assert (S.TOOLS["fullseye_score_pipeline"]["inputSchema"]["properties"]["stages"]
            is S.TOOLS["fullseye_pipeline"]["inputSchema"]["properties"]["stages"])


def test_comparison_families_exclude_the_weakly_separating_defect_family(cat):
    """比較実験に使える族の一覧を固定する。defect_inspect は正誤の分け方が弱いので外す(v2 で作り直す)。"""
    assert T.COMPARISON_FAMILIES == {"blob_count", "edge_subpixel", "fringe_phase"}
    assert T.COMPARISON_FAMILIES <= set(T.FAMILIES)
    for kind, fam in T.FAMILIES.items():
        made = _make(cat, _store(), kind)["structuredContent"]
        assert made["comparison_ready"] is (kind in T.COMPARISON_FAMILIES)
        if kind in T.COMPARISON_FAMILIES:
            assert fam.known_weakness is None and made["known_weakness"] is None
        else:
            assert made["known_weakness"] == fam.known_weakness
            assert "正誤の分け方が弱い" in fam.known_weakness and "20/50" in fam.known_weakness


def test_tolerances_are_the_preregistered_table():
    """許容範囲を結果に合わせて動かしたら、ここが落ちる(動かすなら表だけの commit を先に)。"""
    assert set(TT.TOLERANCES) == set(T.FAMILIES) == set(TT.RATIONALE)
    d = {k: f.tolerance(T.resolve_params(k, None)) for k, f in T.FAMILIES.items()}
    assert d["blob_count"] == {"count_error": 0.0}
    assert d["edge_subpixel"] == {"top_edge_error": 0.15, "bottom_edge_error": 0.15}
    assert d["defect_inspect"] == {"centroid_error": 1.5, "area_rel_error": 0.30, "mask_iou_deficit": 0.40}
    assert d["fringe_phase"]["phase_rms_error"] == pytest.approx(max(0.05, 3 * 0.005 / (0.3 * math.sqrt(2))))
    assert T.SCORING_VERSION == TT.SCORING_VERSION == "2026-11-10.1"
    for kind, fam in T.FAMILIES.items():
        assert [n for n, _ in fam.metrics] == list(TT.TOLERANCES[kind]), kind
        assert fam.rationale == TT.RATIONALE[kind]


# --------------------------------------------------------------------------- #
# 1. 正しい処理は合格、間違えた処理は不合格                                         #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("kind", sorted(PIPELINES))
@pytest.mark.parametrize("seed", SEEDS)
def test_correct_pipeline_passes_and_plausible_wrong_pipeline_fails(cat, kind, seed):
    store = _store()
    task = _make(cat, store, kind, seed)["structuredContent"]
    good, bad = PIPELINES[kind]
    r = _score(cat, store, task["task_id"], good)
    sc = r["structuredContent"]
    if kind == "defect_inspect" and sc.get("reason") == "hidden_check_failed":
        # 比較実験から外した族(known_weakness)。正しい処理の合格は 1 枚あたり約 94 % なので、
        # 隠れた双子にも合格を求めると約 6 % が双子の側で落ちる(報告の誤拒否率を参照)。
        pass
    else:
        assert r["isError"] is False and sc["passed"] is True, (kind, seed, sc)
        assert all(m["passed"] for m in sc["metrics"])
        assert [m["name"] for m in sc["metrics"]] == [n for n, _ in T.FAMILIES[kind].metrics]
    r = _score(cat, store, task["task_id"], bad)
    sc = r["structuredContent"]
    # 採点は成り立った(isError=false)が、許容外で不合格
    assert r["isError"] is False and sc["passed"] is False and sc["reason"] == "out_of_tolerance", (kind, seed, sc)
    worst = max(sc["metrics"], key=lambda m: m["ratio"] if m["ratio"] is not None else math.inf)
    assert not worst["passed"]
    assert any(worst["name"] in line and "超えた" in line for line in sc["explanation"]), sc["explanation"]
    assert sc["attempts_used"] == 2


# --------------------------------------------------------------------------- #
# 2. 真値が返り値のどこにも出ない                                                  #
# --------------------------------------------------------------------------- #
def _numbers_and_strings(value, nums, strs):
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, (int, float)):
        nums.append(float(value))
    elif isinstance(value, str):
        strs.append(value)
    elif isinstance(value, dict):
        for k, v in value.items():
            strs.append(str(k))
            _numbers_and_strings(v, nums, strs)
    elif isinstance(value, (list, tuple)):
        for v in value:
            _numbers_and_strings(v, nums, strs)
    else:
        raise AssertionError("JSON でない値が返り値にある: %r" % type(value))


def _longest_numeric_list(value) -> int:
    if isinstance(value, dict):
        return max([0] + [_longest_numeric_list(v) for v in value.values()])
    if isinstance(value, list):
        own = len(value) if value and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in value) else 0
        return max([own] + [_longest_numeric_list(v) for v in value])
    return 0


def _assert_no_truth(result: dict, truth: dict):
    payload = json.loads(json.dumps(result, ensure_ascii=False))       # JSON に載る物だけを見る
    nums, strs = [], []
    _numbers_and_strings(payload, nums, strs)
    text = "\n".join(strs)
    # 配列(真値の画像・マスク・点列)を丸ごと載せていない
    assert _longest_numeric_list(payload) < 16, "返り値に長い数列がある(配列を載せている)"
    for key, t in truth.items():
        if isinstance(t, np.ndarray):
            if t.dtype == bool:              # 真偽のマスクは長い数列の検査で見る(0/1 は値で区別できない)
                continue
            flat = np.asarray(t, dtype=np.float64).ravel()
            for x in nums:
                if abs(x) > 1e-3:          # 0 付近の誤差・定数は位相の値と偶然近いことがある
                    assert np.min(np.abs(flat - x)) > 1e-6, (key, x)
            continue
        t = float(t)
        assert all(not math.isclose(x, t, rel_tol=1e-6, abs_tol=1e-9) for x in nums), (key, t, nums)
        if float(t).is_integer():
            assert not re.search(r"(?<![\w.])%d(?![\w.])" % int(t), text), (key, t)
        else:
            for digits in (3, 4, 6):
                assert ("%.*f" % (digits, t)) not in text, (key, t, digits)


@pytest.mark.parametrize("kind", sorted(PIPELINES))
def test_truth_never_appears_in_make_or_score_results(cat, kind):
    store = _store()
    made = _make(cat, store, kind, 1)
    rec = _rec(store, made["structuredContent"]["task_id"])
    _assert_no_truth(made, rec.truth)
    good, bad = PIPELINES[kind]
    for stages in (good, bad, [{"op": "gaussian"}, {"op": "count_obj"}]):
        for feedback in ("detailed", "coarse", "pass_fail"):
            r = _score(cat, store, rec.task_id, stages, feedback=feedback)
            _assert_no_truth(r, rec.truth)
    # 採点の返り値は段の値や統計を載せない(正しい処理の出力は真値そのものに近い)
    sc = _score(cat, store, rec.task_id, good)["structuredContent"]
    for row in sc["stages"]:
        assert set(row) <= {"stage", "op", "status", "out_sort", "reason"}, row


def test_the_truth_scan_itself_catches_a_leak():
    """走査の門を本物の漏れで落とす(空を通す門でないことの確認)。"""
    with pytest.raises(AssertionError):
        _assert_no_truth({"content": [{"type": "text", "text": "数は 17 個"}]}, {"count": 17})
    with pytest.raises(AssertionError):
        _assert_no_truth({"structuredContent": {"x": 31.234567}}, {"top": 31.234567})
    with pytest.raises(AssertionError):
        _assert_no_truth({"structuredContent": {"x": list(range(20))}}, {"phase": np.zeros(3)})


# --------------------------------------------------------------------------- #
# 3. fail-closed                                                                #
# --------------------------------------------------------------------------- #
def _refused(r, reason):
    sc = r["structuredContent"]
    assert r["isError"] is True, sc
    assert sc["passed"] is False and sc["reason"] == reason, sc
    assert sc["message"]
    return sc


def test_type_mismatch_is_refused_before_any_stage_runs(cat, monkeypatch):
    store = _store()
    tid = _make(cat, store, "blob_count")["structuredContent"]["task_id"]
    ran = []
    monkeypatch.setattr(S, "_pipeline_dag", lambda *a, **k: ran.append(1))
    sc = _refused(_score(cat, store, tid, [{"op": "gaussian"}, {"op": "count_obj"}]), "type_gate")
    assert sc["errors"][0]["reason"] == "sort_mismatch"
    _refused(_score(cat, store, tid, [{"op": "otsu"}]), "output_sort_mismatch")
    _refused(_score(cat, store, tid, [{"op": "img_to_counts"}]), "type_gate")     # MCP で未検証の op
    assert ran == [], "型の門で落ちた処理が走った"


def test_exception_in_a_stage_is_refused(cat):
    store = _store()
    tid = _make(cat, store, "fringe_phase")["structuredContent"]["task_id"]
    # 変調の床が高すぎると有効画素が 0 になり、op が ValueError を投げる
    sc = _refused(_score(cat, store, tid, [{"op": "decode_fringe", "params": {"min_modulation": 0.9}}]),
                  "execution_failed")
    assert "ValueError" in sc["message"]


def test_exception_in_the_executor_or_the_scorer_is_refused(cat, monkeypatch):
    store = _store()
    tid = _make(cat, store, "blob_count")["structuredContent"]["task_id"]
    good = PIPELINES["blob_count"][0]

    def boom(*a, **k):
        raise RuntimeError("injected")
    monkeypatch.setattr(S, "_pipeline_dag", boom)
    assert "injected" in _refused(_score(cat, store, tid, good), "exception")["message"]
    monkeypatch.undo()
    monkeypatch.delenv(T.SECRET_ENV, raising=False)
    monkeypatch.setattr(T, "score_output", boom)
    _refused(_score(cat, store, tid, good), "unscorable_output")


def test_nan_output_is_refused(cat, monkeypatch):
    store = _store()
    tid = _make(cat, store, "fringe_phase")["structuredContent"]["task_id"]
    # 変調の床が一部の画素だけを落とす高さ → その画素が NaN の高さ図
    _refused(_score(cat, store, tid, [{"op": "decode_fringe", "params": {"min_modulation": 0.6}}]),
             "invalid_output")
    # スカラーの NaN(配列でないので実行器の検査を通る)は採点器が断る
    tid = _make(cat, store, "blob_count")["structuredContent"]["task_id"]
    import fullseye
    real = fullseye.apply
    monkeypatch.setattr(fullseye, "apply",
                        lambda x, op, *a, **k: np.float64("nan") if op == "count_obj" else real(x, op, *a, **k))
    _refused(_score(cat, store, tid, PIPELINES["blob_count"][0]), "invalid_output")


def test_empty_and_constant_outputs_are_refused(cat):
    store = _store()
    tid = _make(cat, store, "defect_inspect")["structuredContent"]["task_id"]
    # 入力を読む op で空・全面になる場合(生成の op は入力に依存しない op として先に断られる)
    _refused(_score(cat, store, tid, [{"op": "threshold", "a": 1.0, "b": 1.0}]), "empty_output")
    _refused(_score(cat, store, tid, [{"op": "threshold", "a": 0.0, "b": 0.0}]), "constant_output")
    tid = _make(cat, store, "fringe_phase")["structuredContent"]["task_id"]
    _refused(_score(cat, store, tid, [{"op": "wrapped_phase"}, {"op": "scale_image", "a": 0.0, "b": 0.0}]),
             "constant_output")


def test_unknown_expired_and_evicted_task_ids_are_refused(cat):
    store = _store()
    _refused(_score(cat, store, "fullseye://task/0123456789abcdef", [{"op": "otsu"}]), "unknown_task")
    _refused(_score(cat, store, "not-a-task", [{"op": "otsu"}]), "unknown_task")
    now = [0.0]
    store._fullseye_tasks = T.TaskStore(ttl_s=10.0, max_items=2, clock=lambda: now[0])
    good = PIPELINES["blob_count"][0]
    tid2 = _make(cat, store, "blob_count", 5)["structuredContent"]["task_id"]
    now[0] = 11.0
    _refused(_score(cat, store, tid2, good), "task_expired")
    _refused(_score(cat, store, tid2, good), "unknown_task")          # 期限切れは捨てた
    first = _make(cat, store, "edge_subpixel", 1)["structuredContent"]["task_id"]
    _make(cat, store, "edge_subpixel", 2)
    _make(cat, store, "edge_subpixel", 3)                              # max_items=2 で first を追い出す
    _refused(_score(cat, store, first, [{"op": "m1_measure_pos"}]), "unknown_task")


@pytest.mark.parametrize("args, why", [
    ({"kind": "nope", "seed": 0}, "どれか"),
    ({"kind": "blob_count", "seed": -1}, "以上"),
    ({"kind": "blob_count", "seed": 1.5}, "整数"),
    ({"kind": "blob_count", "seed": 0, "params": {"count": 12}}, "unknown_param"),
    ({"kind": "blob_count", "seed": 0, "params": {"noise": 0.9}}, "bad_param"),
    ({"kind": "blob_count", "seed": 0, "params": {"noise": "x"}}, "bad_param"),
    ({"kind": "blob_count", "seed": 0, "params": {"noise": True}}, "bad_param"),
    ({"kind": "blob_count", "seed": 0, "truth": 1}, "知らない引数"),
])
def test_bad_make_task_arguments_are_argument_errors(cat, args, why):
    with pytest.raises(S.ArgError, match=why):
        call_tool("fullseye_make_task", args, cat, _store())


def test_score_schema_refuses_a_handle_argument(cat):
    """入力は課題の画像に固定。別の画像を採点に差し込む引数は無い。"""
    with pytest.raises(S.ArgError, match="知らない引数"):
        call_tool("fullseye_score_pipeline", {"task_id": "fullseye://task/0123456789abcdef",
                                              "handle": "fullseye://img/0123456789abcdef",
                                              "stages": [{"op": "otsu"}]}, cat, _store())


# --------------------------------------------------------------------------- #
# 4. 決定性                                                                      #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("kind", sorted(PIPELINES))
def test_same_kind_seed_params_give_the_same_task_and_the_same_score(cat, kind):
    runs = []
    for _ in range(2):
        store = _store()
        made = _make(cat, store, kind, 7)
        tid = made["structuredContent"]["task_id"]
        _, arr = store.get(made["structuredContent"]["input"]["handle"])
        good, bad = PIPELINES[kind]
        scores = [_score(cat, store, tid, s)["structuredContent"] for s in (good, bad)]
        runs.append((tid, hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest(),
                     json.dumps(made["structuredContent"], sort_keys=True), json.dumps(scores, sort_keys=True)))
    assert runs[0] == runs[1]
    other = T.generate(kind, 8)[0]
    assert not np.array_equal(other, T.generate(kind, 7)[0]), "seed が課題を変えていない"
    assert T.task_id_of(kind, 7, T.resolve_params(kind, None)) == runs[0][0]


@pytest.mark.parametrize("kind", sorted(PIPELINES))
def test_params_change_the_input_but_never_the_truth(kind):
    """真値の鍵が (kind, seed) であることの根拠: どの族でも、つまみを両端に振っても真値は同じ。"""
    fam = T.FAMILIES[kind]
    lo = {k: p.lo for k, p in fam.params.items()}
    hi = {k: p.hi for k, p in fam.params.items()}
    a, ta, _ = T.generate(kind, 4, lo)
    b, tb, _ = T.generate(kind, 4, hi)
    assert not np.array_equal(a, b)
    assert set(ta) == set(tb)
    for k in ta:
        assert np.array_equal(np.asarray(ta[k]), np.asarray(tb[k])), (kind, k)


# --------------------------------------------------------------------------- #
# 5. 課題の入力に縛る(F1)                                                       #
# --------------------------------------------------------------------------- #
def _import(cat, store, arr, sort):
    import fullseye
    r = call_tool("fullseye_import_json", {"envelope": fullseye.to_jsonable(np.asarray(arr), sort)}, cat, store)
    return r["structuredContent"]["handle"]


def test_an_imported_answer_cannot_be_scored(cat):
    store = _store()
    tid = _make(cat, store, "fringe_phase", 9)["structuredContent"]["task_id"]
    answer = _import(cat, store, _rec(store, tid).truth["phase"] + 2 * math.pi, "image")
    sc = _refused(_score(cat, store, tid, [{"op": "identity", "inputs": [answer]}]), "foreign_input")
    assert sc["refs"] == [{"stage": 1, "op": "identity", "where": "inputs", "ref": answer}]
    region = np.zeros((128, 128), bool)
    region[10:20, 10:20] = True
    tid = _make(cat, store, "blob_count", 3)["structuredContent"]["task_id"]
    h = _import(cat, store, region, "region")
    _refused(_score(cat, store, tid, [{"op": "count_obj", "inputs": [h]}]), "foreign_input")
    # 後段だけ差し替えても同じ(前段が課題の入力を読んでいても)
    _refused(_score(cat, store, tid, [{"op": "otsu"}, {"op": "count_obj", "inputs": [h]}]), "foreign_input")


def test_another_tasks_input_cannot_be_used(cat):
    store = _store()
    a = _make(cat, store, "blob_count", 1)["structuredContent"]
    b = _make(cat, store, "blob_count", 2)["structuredContent"]
    stages = [{"op": "gaussian", "inputs": [b["input"]["handle"]]}, {"op": "tophat", "a": 0.9},
              {"op": "otsu"}, {"op": "count_obj"}]
    _refused(_score(cat, store, a["task_id"], stages), "foreign_input")
    # 課題の入力を名前で読むのは通る
    stages[0]["inputs"] = ["have:image"]
    assert _score(cat, store, a["task_id"], stages)["structuredContent"]["passed"] is True


@pytest.mark.parametrize("ref", ["have:region", "stage:0", "stage:x", "fullseye://img/0123456789abcdef",
                                 "fullseye://task/0123456789abcdef"])
def test_only_have_input_and_stage_refs_are_allowed(cat, ref):
    store = _store()
    tid = _make(cat, store, "blob_count")["structuredContent"]["task_id"]
    _refused(_score(cat, store, tid, [{"op": "otsu", "inputs": [ref]}, {"op": "count_obj"}]), "foreign_input")


def test_a_non_string_ref_is_an_argument_error(cat):
    store = _store()
    tid = _make(cat, store, "blob_count")["structuredContent"]["task_id"]
    with pytest.raises(S.ArgError):
        _score(cat, store, tid, [{"op": "otsu", "inputs": [3]}, {"op": "count_obj"}])


def test_a_param_ref_to_a_foreign_handle_is_refused(cat):
    store = _store()
    tid = _make(cat, store, "fringe_phase")["structuredContent"]["task_id"]
    h = _import(cat, store, np.zeros((64, 96)), "image")
    sc = _refused(_score(cat, store, tid, [{"op": "decode_fringe", "params": {"ref_phase": {"ref": h}}}]),
                  "foreign_input")
    assert sc["refs"][0]["where"] == "params.ref_phase"


def test_dependency_walk_finds_stages_that_do_not_read_the_input():
    """入力の無い段(生成源)と、課題の入力に辿り着かない最終段を見つける。"""
    stages = [{"op": "a"}, {"op": "b"}, {"op": "c"}]
    checked = {"stages": [{"stage": 1, "inputs": []}, {"stage": 2, "inputs": ["stage:1"]},
                          {"stage": 3, "inputs": ["stage:2"]}]}
    assert S._depends_on_input(checked, stages, "image") == (False, [1])
    checked["stages"][0]["inputs"] = ["have:image"]
    assert S._depends_on_input(checked, stages, "image") == (True, [])
    checked = {"stages": [{"stage": 1, "inputs": ["have:image"]}, {"stage": 2, "inputs": []},
                          {"stage": 3, "inputs": ["stage:2"]}]}
    assert S._depends_on_input(checked, stages, "image") == (False, [2])


# --------------------------------------------------------------------------- #
# 6. 採点の回数は (kind, seed) ごと(F2)                                          #
# --------------------------------------------------------------------------- #
def _exhaust(cat, store, tid, n):
    good = PIPELINES["blob_count"][0]
    for _ in range(n):
        assert _score(cat, store, tid, [{"op": "otsu"}])["structuredContent"]["reason"] == "output_sort_mismatch"
    _refused(_score(cat, store, tid, good), "attempts_exhausted")


def test_attempt_cap_survives_param_twins_eviction_and_expiry(cat):
    now = [0.0]
    store = _store()
    store._fullseye_tasks = T.TaskStore(ttl_s=10.0, max_attempts=3, max_items=2, clock=lambda: now[0])
    tid = _make(cat, store, "blob_count", 0)["structuredContent"]["task_id"]
    _exhaust(cat, store, tid, 3)
    # 作り直し: 同じ task_id、回数は戻らない
    again = _make(cat, store, "blob_count", 0)["structuredContent"]
    assert again["task_id"] == tid and again["attempts_used"] == 3
    _refused(_score(cat, store, tid, PIPELINES["blob_count"][0]), "attempts_exhausted")
    # つまみを微小に変えた双子(別の task_id、同じ真値)も同じ回数を数える
    twin = _make(cat, store, "blob_count", 0, noise=0.0200000001)["structuredContent"]
    assert twin["task_id"] != tid and twin["attempts_used"] == 3
    _refused(_score(cat, store, twin["task_id"], PIPELINES["blob_count"][0]), "attempts_exhausted")
    easy = _make(cat, store, "blob_count", 0, noise=0.0, illumination=0.0)["structuredContent"]
    _refused(_score(cat, store, easy["task_id"], PIPELINES["blob_count"][0]), "attempts_exhausted")
    # 他の課題で追い出してから作り直しても戻らない
    for seed in (10, 11, 12):
        _make(cat, store, "blob_count", seed)
    assert tid not in store._fullseye_tasks._items
    assert _make(cat, store, "blob_count", 0)["structuredContent"]["attempts_used"] == 3
    _refused(_score(cat, store, tid, PIPELINES["blob_count"][0]), "attempts_exhausted")
    # 期限が切れてから作り直しても戻らない
    now[0] = 100.0
    _refused(_score(cat, store, tid, PIPELINES["blob_count"][0]), "task_expired")
    assert _make(cat, store, "blob_count", 0)["structuredContent"]["attempts_used"] == 3
    _refused(_score(cat, store, tid, PIPELINES["blob_count"][0]), "attempts_exhausted")
    # 別の seed は別の真値なので別の回数
    other = _make(cat, store, "blob_count", 1)["structuredContent"]
    assert other["attempts_used"] == 0
    assert _score(cat, store, other["task_id"], PIPELINES["blob_count"][0])["structuredContent"]["passed"] is True


def test_the_truth_key_table_is_bounded(cat):
    store = _store()
    store._fullseye_tasks = T.TaskStore(max_truth_keys=2)
    _make(cat, store, "blob_count", 0)
    _make(cat, store, "blob_count", 0, noise=0.01)                    # 同じ鍵は数えない
    _make(cat, store, "edge_subpixel", 0)
    with pytest.raises(S.ArgError, match="too_many_tasks"):
        call_tool("fullseye_make_task", {"kind": "blob_count", "seed": 1}, cat, store)


# --------------------------------------------------------------------------- #
# 7. feedback の段階(F3)と実験モード(F4)                                       #
# --------------------------------------------------------------------------- #
def test_coarse_and_pass_fail_feedback_return_no_error_numbers(cat, capsys, tmp_path):
    store = _store()
    audit_path = str(tmp_path / "audit.jsonl")
    store._fullseye_tasks = T.TaskStore(audit_path=audit_path)
    tid = _make(cat, store, "edge_subpixel", 5)["structuredContent"]["task_id"]
    bad = PIPELINES["edge_subpixel"][1]
    coarse = _score(cat, store, tid, bad, feedback="coarse")
    sc = coarse["structuredContent"]
    assert sc["feedback_level"] == "coarse" and sc["passed"] is False
    assert all(set(m) == {"name", "unit", "tolerance", "passed", "band"} for m in sc["metrics"])
    assert {m["band"] for m in sc["metrics"]} <= {"<=1x", "<=2x", "<=5x", ">5x"}
    assert all(m["band"] == "<=5x" for m in sc["metrics"]), sc["metrics"]       # 0.36〜0.41 px / 0.15 px
    pf = _score(cat, store, tid, bad, feedback="pass_fail")["structuredContent"]
    assert pf["metrics"] == [] and pf["explanation"] == [] and pf["passed"] is False
    good = _score(cat, store, tid, PIPELINES["edge_subpixel"][0], feedback="pass_fail")["structuredContent"]
    assert good["passed"] is True and good["metrics"] == []
    for r in (coarse["structuredContent"], pf, good):
        nums = []
        _numbers_and_strings({k: v for k, v in r.items() if k not in ("attempts_used", "max_attempts")}, nums, [])
        assert set(nums) <= {0.15, 1.0, 2.0, 3.0, 4.0, 5.0}, nums             # 許容・段番号だけ
    # 詳しい値は監査ファイルにだけ残る(stderr には合否と回数だけ)
    with open(audit_path, encoding="utf-8") as fh:
        audit = [row for row in map(json.loads, fh) if "metrics" in row]
    assert len(audit) == 3 and all(len(a["metrics"]) == 2 and a["metrics"][0]["error"] > 0 for a in audit)
    err = capsys.readouterr().err
    assert "error" not in err and "metrics" not in err
    for a in audit:
        for m in a["metrics"]:
            assert ("%g" % m["error"]) not in err


def test_feedback_cap_limits_what_can_be_requested(cat):
    store = _store()
    store._fullseye_tasks = T.TaskStore(feedback_cap="coarse")
    tid = _make(cat, store, "blob_count")["structuredContent"]["task_id"]
    sc = _score(cat, store, tid, PIPELINES["blob_count"][1], feedback="detailed")["structuredContent"]
    assert sc["feedback_level"] == "coarse" and sc["feedback_capped"] is True
    assert "error" not in sc["metrics"][0]
    with pytest.raises(ValueError):
        T.TaskStore(feedback_cap="everything")


def test_secret_mode_cannot_be_regenerated_from_the_public_generator(cat, monkeypatch, capsys, tmp_path):
    secret = "experiment-secret-0123456789abcdef-XYZ"
    monkeypatch.setenv(T.SECRET_ENV, secret)
    monkeypatch.setenv(T.AUDIT_ENV, str(tmp_path / "audit.jsonl"))
    store = _store()
    made = _make(cat, store, "edge_subpixel", 42)["structuredContent"]
    assert made["mode"] == "secret" and made["scoring_version"].endswith("+secret")
    assert made["feedback_cap"] == "pass_fail"                         # 実験モードの既定
    rec = _rec(store, made["task_id"])
    public_arr, public_truth, params = T.generate("edge_subpixel", 42, made["params"])
    assert public_truth != rec.truth and not np.array_equal(public_arr, rec.input)
    assert made["task_id"] != T.task_id_of("edge_subpixel", 42, params)
    same_secret = T.generate("edge_subpixel", 42, made["params"], secret=secret)
    assert same_secret[1] == rec.truth                                 # 秘密値を持つサーバでは再現できる
    sc = _score(cat, store, made["task_id"], PIPELINES["edge_subpixel"][0], feedback="detailed")["structuredContent"]
    assert sc["passed"] is True and sc["feedback_level"] == "pass_fail" and sc["feedback_capped"] is True
    everything = json.dumps([made, sc], ensure_ascii=False) + capsys.readouterr().err
    assert secret not in everything


# --------------------------------------------------------------------------- #
# 7b. 独立レビュー第 2 巡(N1〜N4、N6)の回帰                                        #
# --------------------------------------------------------------------------- #
#: probe4_count.py が見つけた、画像を見ずに数 13 / 18 / 25 を出す 3 本(計数の 9/50 課題で 3 回以内に合格した)
CHECKER_PIPELINES = [
    [{"op": "hx_gen_checker_region", "a": 0.0}, {"op": "erosion_circle", "a": 0.0},
     {"op": "hx_clip_region_rel", "a": 0.7, "b": 0.0}, {"op": "count_obj"}],
    [{"op": "hx_gen_checker_region", "a": 0.0}, {"op": "erosion_circle", "a": 0.0},
     {"op": "hx_clip_region_rel", "a": 0.8, "b": 0.0}, {"op": "count_obj"}],
    [{"op": "hx_gen_checker_region", "a": 0.025}, {"op": "erosion_circle", "a": 0.0},
     {"op": "hx_clip_region_rel", "a": 0.7, "b": 0.0}, {"op": "count_obj"}],
]


def test_n1_input_ignoring_generators_are_refused_by_the_deny_list(cat):
    store = _store()
    for seed in (4, 6, 9):                                        # probe で偽造が通った seed
        tid = _make(cat, store, "blob_count", seed)["structuredContent"]["task_id"]
        for stages in CHECKER_PIPELINES:
            sc = _refused(_score(cat, store, tid, stages), "input_independent")
            assert sc["ops"] == [{"stage": 1, "op": "hx_gen_checker_region"}]
    tid = _make(cat, store, "defect_inspect", 7)["structuredContent"]["task_id"]
    _refused(_score(cat, store, tid, [{"op": "hx_gen_circle"}, {"op": "hx_move_region"}]), "input_independent")


def test_n1_the_deny_list_is_mechanical_and_spares_the_reference_pipelines():
    ops = S._input_independent_ops()
    assert {"hx_gen_checker_region", "hx_gen_circle", "hx_gen_ellipse", "hx_gen_rectangle2",
            "hx_gen_image_proto", "hx_gen_empty_region", "hx_full_domain"} <= ops
    used = {st["op"] for pair in PIPELINES.values() for stages in pair for st in stages}
    assert not (used & ops), used & ops
    import tools.gen_mcp_input_independent as G                   # 一覧を作る道具が在り、同じ一覧を指す
    assert G.OUT.endswith(os.path.join("fullseye", "data", "MCP_INPUT_INDEPENDENT.json"))


def test_n1_the_runtime_check_refuses_an_output_that_ignores_the_input(cat, monkeypatch):
    """一覧から漏れた生成の op も、入力を変えた写しで出力が同じなら断る(一覧を空にして確かめる)。"""
    monkeypatch.setattr(S, "_INPUT_INDEPENDENT", frozenset())
    store = _store()
    tid = _make(cat, store, "blob_count", 4)["structuredContent"]["task_id"]
    for stages in CHECKER_PIPELINES:
        _refused(_score(cat, store, tid, stages), "input_independent")
    # 正しい処理は写しで出力が変わるので通る
    assert _score(cat, store, tid, PIPELINES["blob_count"][0])["structuredContent"]["passed"] is True
    rec = _rec(store, tid)
    alt = store._fullseye_tasks.alternate_input(rec)
    assert not np.array_equal(alt, rec.input)


def test_n1_the_alternate_input_never_shares_the_truth():
    ts = T.TaskStore()
    for kind in T.FAMILIES:
        for seed in range(6):
            rec = ts.make(kind, seed)
            alt = ts.alternate_input(rec)
            assert alt.shape == rec.input.shape and not np.array_equal(alt, rec.input)


def test_n2_stderr_carries_only_pass_fail_and_attempts_in_secret_mode(cat, monkeypatch, capsys, tmp_path):
    monkeypatch.setenv(T.SECRET_ENV, "experiment-secret-0123456789abcdef-XYZ")
    audit = tmp_path / "experimenter" / "audit.jsonl"
    monkeypatch.setenv(T.AUDIT_ENV, str(audit))
    store = _store()
    tid = _make(cat, store, "edge_subpixel", 4)["structuredContent"]["task_id"]
    sc = _score(cat, store, tid, PIPELINES["edge_subpixel"][1], feedback="pass_fail")["structuredContent"]
    assert sc["passed"] is False and sc["metrics"] == []
    err = capsys.readouterr().err
    score_lines = [line for line in err.splitlines() if " score " in line]
    assert score_lines and all(line.endswith(("passed", "failed")) or "refused" in line for line in score_lines)
    rows = [json.loads(line) for line in audit.read_text(encoding="utf-8").splitlines()]
    errors = [m["error"] for r in rows for m in r.get("metrics", [])]
    assert len(errors) == 2 and all(e > 0.1 for e in errors)
    for e in errors:
        assert ("%g" % e) not in err and ("%.3f" % e) not in err


def test_r2_a_fixed_answer_with_a_tiny_input_dependence_fails_the_hidden_twin(cat, monkeypatch):
    """バイト単位の一致だけを見る検査は、入力にわずかに依存する固定の答えを通した(第 3 巡 R2)。
    隠れた双子の真値にも合格を求めると、固定の答えは落ちる。双子の側の誤差は返さない。"""
    import fullseye
    store = _store()
    tid = _make(cat, store, "edge_subpixel", 5)["structuredContent"]["task_id"]
    truth = _rec(store, tid).truth
    real = fullseye.apply

    def fake(x, op, *a, **k):
        if op != "m1_measure_pos":
            return real(x, op, *a, **k)
        wiggle = 1e-6 * float(np.mean(x))                      # 入力にわずかに依存(バイト一致を避ける)
        return {"shape": (96, 64), "cs": [np.array([[truth["top"] + wiggle, 31.5]]),
                                          np.array([[truth["bottom"] + wiggle, 31.5]])]}
    monkeypatch.setattr(fullseye, "apply", fake)
    r = _score(cat, store, tid, PIPELINES["edge_subpixel"][0])
    sc = _refused(r, "hidden_check_failed")
    assert "metrics" not in sc and "explanation" not in sc
    nums = []
    _numbers_and_strings({k: v for k, v in sc.items() if k != "stages"}, nums, [])   # 段の番号は除く
    assert all(x in (sc["attempts_used"], sc["max_attempts"]) for x in nums), nums
    # 本物の処理は双子でも合格する
    monkeypatch.setattr(fullseye, "apply", real)
    assert _score(cat, store, tid, PIPELINES["edge_subpixel"][0])["structuredContent"]["passed"] is True


_CHILD = r"""
import os, sys, time
sys.path.insert(0, sys.argv[1])
from fullseye.mcp import tasks as T
ts = T.TaskStore(secret=sys.argv[2], audit_path=sys.argv[3])
mode = sys.argv[4]
if mode == "hold_and_die":                      # lock を持ったまま落ちる
    ts._file_lock()
    sys.stdout.write("locked\n"); sys.stdout.flush()
    os._exit(3)
rec = ts.make("blob_count", 0)
ok = 0
for _ in range(int(sys.argv[5])):
    try:
        ts.claim(rec.task_id); ok += 1
    except T.TaskError as exc:
        assert exc.reason == "attempts_exhausted", exc.reason
sys.stdout.write("%d\n" % ok)
"""


def _child(tmp_path, *args):
    import subprocess
    import sys
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return subprocess.run([sys.executable, "-c", _CHILD, root, "experiment-secret-0123456789abcdef-XYZ", str(tmp_path / "a.jsonl"), *args],
                          capture_output=True, text=True, timeout=120)


def test_r4_a_lock_left_by_a_crashed_process_is_released_and_a_held_lock_times_out(tmp_path, monkeypatch):
    """OS のファイル lock: 持ち主が落ちれば OS が外す。生きている持ち主の lock は待って fail-closed。"""
    r = _child(tmp_path, "hold_and_die")
    assert r.returncode == 3 and r.stdout.strip() == "locked", r.stderr
    ts = T.TaskStore(secret="experiment-secret-0123456789abcdef-XYZ", audit_path=str(tmp_path / "a.jsonl"))
    rec = ts.make("blob_count", 0)
    assert ts.claim(rec.task_id).attempts == 1                    # 落ちたプロセスの lock は残らない
    held = ts._file_lock()                                         # 別の持ち主(別のハンドル)が持っている
    monkeypatch.setattr(T, "ATTEMPT_LOCK_TIMEOUT_S", 0.2)
    try:
        with pytest.raises(T.TaskError) as exc:
            ts.claim(rec.task_id)
        assert exc.value.reason == "attempt_store_unavailable"
    finally:
        T.TaskStore._file_unlock(held)
    assert ts.claim(rec.task_id).attempts == 2                     # 外れれば進む(回数は失われない)


def test_r4_concurrent_processes_never_lose_or_exceed_the_count(tmp_path):
    """4 プロセスが同じ真値を 12 回ずつ採点しても、通るのはちょうど上限の 32 回(回数が減らない・超えない)。"""
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(4) as pool:
        runs = list(pool.map(lambda _: _child(tmp_path, "claim", "12"), range(4)))
    assert len(runs) == 4
    assert all(r.returncode == 0 for r in runs), [r.stderr[-400:] for r in runs]
    assert sum(int(r.stdout.strip()) for r in runs) == T.TASK_MAX_ATTEMPTS
    ts = T.TaskStore(secret="experiment-secret-0123456789abcdef-XYZ", audit_path=str(tmp_path / "a.jsonl"))
    assert ts.attempts_of("blob_count", 0) == T.TASK_MAX_ATTEMPTS


def test_r4_an_unwritable_attempts_file_is_fail_closed_without_the_path(cat, tmp_path, monkeypatch):
    """書けない回数ファイル: 書き込みの OSError(文にパスを含む)を attempt_store_unavailable に包む。

    ★2026-11-10(PR #295 の CI): 以前は回数ファイルを chmod で読み取り専用にしていた。Linux の CI は権限が
    効かない環境(root)で、書けてしまい断られなかった。OS の権限に頼らず、置き換えの段(os.replace)で
    パスを含む OSError を出させて、どの OS でも同じに試す。
    """
    monkeypatch.setenv(T.SECRET_ENV, "experiment-secret-0123456789abcdef-XYZ")
    monkeypatch.setenv(T.AUDIT_ENV, str(tmp_path / "audit.jsonl"))
    store = _store()
    tid = _make(cat, store, "blob_count", 0)["structuredContent"]["task_id"]
    path = store._fullseye_tasks.attempts_path
    calls = []

    def refuse_replace(src, dst):
        calls.append(dst)
        raise PermissionError(13, "Permission denied", dst)       # 本物と同じく文にパスが入る
    monkeypatch.setattr(T.os, "replace", refuse_replace)
    sc = _refused(_score(cat, store, tid, PIPELINES["blob_count"][0]), "attempt_store_unavailable")
    assert calls == [path], calls                                  # 書き込みの段まで来て、そこで断られた
    everything = json.dumps(sc, ensure_ascii=False)
    assert str(tmp_path) not in everything and "attempts.json" not in everything, everything
    with pytest.raises(T.TaskError) as exc:
        store._fullseye_tasks._write_file({"k": 1})
    assert exc.value.reason == "attempt_store_unavailable" and str(tmp_path) not in str(exc.value)
    assert not os.path.exists(path + ".tmp")                       # 書きかけの一時ファイルを残さない
    monkeypatch.undo()
    monkeypatch.delenv(T.SECRET_ENV, raising=False)
    assert store._fullseye_tasks.attempts_of("blob_count", 0) == 0   # 書けなかった回は数えていない


def test_r5_an_unreadable_attempts_file_is_fail_closed_without_the_path(cat, tmp_path, monkeypatch):
    """読めないとき(回数ファイルの場所がディレクトリ)の文にも、ファイルの場所が出ない。"""
    monkeypatch.setenv(T.SECRET_ENV, "experiment-secret-0123456789abcdef-XYZ")
    monkeypatch.setenv(T.AUDIT_ENV, str(tmp_path / "audit.jsonl"))
    os.makedirs(tmp_path / "audit.jsonl.attempts.json")                 # open() が OSError になる
    with pytest.raises(S.ArgError) as exc:
        call_tool("fullseye_make_task", {"kind": "blob_count", "seed": 0}, cat, _store())
    assert "attempt_store_unavailable" in str(exc.value)
    assert str(tmp_path) not in str(exc.value) and "attempts.json" not in str(exc.value), str(exc.value)
    ts = T.TaskStore()
    with pytest.raises(T.TaskError) as exc2:
        ts._read_file()
    assert exc2.value.reason == "attempt_store_unavailable" and str(tmp_path) not in str(exc2.value)


def test_r5_the_count_is_read_under_the_file_lock(tmp_path, monkeypatch):
    """_count(課題作り・attempts_of の読み)も lock の下で読む: 他の持ち主が持っている間は待って fail-closed。"""
    ts = T.TaskStore(secret="experiment-secret-0123456789abcdef-XYZ", audit_path=str(tmp_path / "a.jsonl"))
    ts.make("blob_count", 0)
    held = ts._file_lock()
    monkeypatch.setattr(T, "ATTEMPT_LOCK_TIMEOUT_S", 0.2)
    try:
        with pytest.raises(T.TaskError) as exc:
            ts.attempts_of("blob_count", 0)
        assert exc.value.reason == "attempt_store_unavailable"
    finally:
        T.TaskStore._file_unlock(held)
    assert ts.attempts_of("blob_count", 0) == 0


def test_r4b_pass_fail_and_coarse_do_not_tell_a_twin_failure_from_a_plain_failure(cat, monkeypatch, tmp_path):
    """本体だけ合う出力と、両方外れる出力が、pass_fail・coarse では同じ返り値になる(区別は監査記録だけ)。"""
    import fullseye
    real = fullseye.apply
    for level in ("pass_fail", "coarse"):
        store = _store()
        audit = tmp_path / ("audit_%s.jsonl" % level)
        store._fullseye_tasks = T.TaskStore(audit_path=str(audit))
        tid = _make(cat, store, "edge_subpixel", 5)["structuredContent"]["task_id"]
        truth = _rec(store, tid).truth
        box = {}

        def fake(x, op, *a, **k):
            if op != "m1_measure_pos":
                return real(x, op, *a, **k)
            d = box["offset"] + 1e-6 * float(np.mean(x))
            return {"shape": (96, 64), "cs": [np.array([[truth["top"] + d, 31.5]]),
                                              np.array([[truth["bottom"] + d, 31.5]])]}
        monkeypatch.setattr(fullseye, "apply", fake)
        out = []
        for offset in (0.0, 0.31):                     # 本体だけ合う / 本体も双子も外れる(0.31 px ≈ 2x)
            box["offset"] = offset
            r = _score(cat, store, tid, PIPELINES["edge_subpixel"][0], feedback=level)
            sc = dict(r["structuredContent"])
            sc.pop("attempts_used")
            text = re.sub(r"試行 \d+/", "試行 n/", r["content"][0]["text"])
            out.append((r["isError"], sc, text))
        monkeypatch.setattr(fullseye, "apply", real)
        if level == "pass_fail":
            assert out[0] == out[1], out
        else:                                          # 段階は落ちた側の指標から作るので、形と理由が同じ
            (e0, s0, _), (e1, s1, _) = out
            assert e0 == e1 is False and s0["reason"] == s1["reason"] == "out_of_tolerance"
            assert set(s0) == set(s1) and all(set(m) == {"name", "unit", "tolerance", "passed", "band"}
                                              for m in s0["metrics"] + s1["metrics"])
            assert not all(m["passed"] for m in s0["metrics"])
        assert out[0][1]["passed"] is False and out[0][1]["reason"] == "out_of_tolerance"
        rows = [json.loads(x) for x in audit.read_text(encoding="utf-8").splitlines()]
        assert [r_["hidden_seed_check"] for r_ in rows if "hidden_seed_check" in r_] == ["failed"]


def test_r4c_the_twin_never_shares_any_truth_with_the_task():
    """双子の真値は本体とどの鍵でも違う(計数がたまたま同じ双子は飛ばす)。公開モードの 4 族 x seed 0〜199。"""
    ts = T.TaskStore()
    for kind in T.FAMILIES:
        for seed in range(200 if kind == "blob_count" else 30):
            rec = ts.make(kind, seed)
            alt = ts.alternate(rec)
            assert len(rec.truth) >= 1
            for key in rec.truth:
                assert not np.array_equal(np.asarray(alt.truth[key]), np.asarray(rec.truth[key])), (kind, seed, key)


def test_r4c_the_secret_mode_twin_needs_the_secret_and_changes_per_attempt(tmp_path):
    """実験モードの双子の seed は秘密値なしでは作れず(公開の式と一致しない、秘密値で変わる)、試行ごとに替わる。"""
    pub = T.TaskStore()
    a = T.TaskStore(secret="experiment-secret-0123456789abcdef-XYZ", audit_path=str(tmp_path / "a.jsonl"))
    b = T.TaskStore(secret="experiment-secret-0123456789abcdef-XYZ-other", audit_path=str(tmp_path / "b.jsonl"))
    for seed in range(5):
        ra, rb, rp = a.make("edge_subpixel", seed), b.make("edge_subpixel", seed), pub.make("edge_subpixel", seed)
        public_formula = set()
        for k in range(1, 64):
            h = hashlib.sha256(("alt|edge_subpixel|%d|%d|" % (seed, k)).encode("utf-8")).digest()
            public_formula.add(int.from_bytes(h[:4], "little") % (T.MAX_SEED + 1))
        seeds_a = set()
        for attempt in range(4):
            ra.attempts = attempt
            seeds_a.add(a.alternate(ra).seed)
        assert not (seeds_a & public_formula)
        assert len(seeds_a) == 4, seeds_a                         # 試行ごとに替わる
        rb.attempts = 0
        assert b.alternate(rb).seed not in seeds_a
        rp.attempts = 3
        assert pub.alternate(rp).seed == pub.alternate(pub.make("edge_subpixel", seed)).seed   # 公開は替えない


@pytest.mark.parametrize("content", ['{"k": "abc"}', '{"k": -1}', '{"k": 1.5}', '{"k": true}', "[1, 2]", "not json"])
def test_r4_a_corrupt_attempts_file_is_fail_closed(cat, tmp_path, monkeypatch, content):
    monkeypatch.setenv(T.SECRET_ENV, "experiment-secret-0123456789abcdef-XYZ")
    monkeypatch.setenv(T.AUDIT_ENV, str(tmp_path / "audit.jsonl"))
    (tmp_path / "audit.jsonl.attempts.json").write_text(content, encoding="utf-8")
    with pytest.raises(S.ArgError, match="attempt_store_unavailable"):
        call_tool("fullseye_make_task", {"kind": "blob_count", "seed": 0}, cat, _store())
    ts = T.TaskStore()
    (tmp_path / "audit.jsonl.attempts.json").write_text("{}", encoding="utf-8")
    rec = ts.make("blob_count", 0)
    (tmp_path / "audit.jsonl.attempts.json").write_text(content, encoding="utf-8")
    with pytest.raises(T.TaskError) as exc:
        ts.claim(rec.task_id)
    assert exc.value.reason == "attempt_store_unavailable"


def test_n3_literal_arrays_and_nested_dicts_in_params_are_refused(cat):
    store = _store()
    tid = _make(cat, store, "fringe_phase", 3)["structuredContent"]["task_id"]
    literal = np.zeros((64, 96)).tolist()
    sc = _refused(_score(cat, store, tid, [{"op": "decode_fringe", "params": {"ref_phase": literal}}]),
                  "param_not_allowed")
    assert sc["params"] == [{"stage": 1, "op": "decode_fringe", "param": "ref_phase", "type": "list"}]
    _refused(_score(cat, store, tid, [{"op": "decode_fringe", "params": {"mask": {"profile": "x"}}}]),
             "param_not_allowed")
    # 数・文字列・真偽と {ref: have|stage} は通る
    sc = _score(cat, store, tid, [{"op": "decode_fringe", "params": {"min_modulation": 0.1, "k": 1.0}}])
    assert sc["structuredContent"]["passed"] is True


def test_n4_attempts_persist_across_sessions_in_secret_mode(cat, monkeypatch, tmp_path):
    monkeypatch.setenv(T.SECRET_ENV, "experiment-secret-0123456789abcdef-XYZ")
    monkeypatch.setenv(T.AUDIT_ENV, str(tmp_path / "audit.jsonl"))
    first = _store()
    first._fullseye_tasks = T.TaskStore(max_attempts=2)
    tid = _make(cat, first, "blob_count", 0)["structuredContent"]["task_id"]
    for _ in range(2):
        _score(cat, first, tid, [{"op": "otsu"}])
    _refused(_score(cat, first, tid, [{"op": "otsu"}]), "attempts_exhausted")
    second = _store()                                              # 別のセッション(新しい保管庫)
    second._fullseye_tasks = T.TaskStore(max_attempts=2)
    made = _make(cat, second, "blob_count", 0)["structuredContent"]
    assert made["task_id"] == tid and made["attempts_used"] == 2
    _refused(_score(cat, second, tid, PIPELINES["blob_count"][0]), "attempts_exhausted")
    assert (tmp_path / "audit.jsonl.attempts.json").exists()


def test_n6_experiment_mode_is_fail_closed_on_a_weak_secret_or_a_missing_audit_path(cat, monkeypatch, tmp_path):
    monkeypatch.setenv(T.SECRET_ENV, "short-secret")
    monkeypatch.setenv(T.AUDIT_ENV, str(tmp_path / "audit.jsonl"))
    with pytest.raises(S.ArgError, match="短すぎる") as exc:
        call_tool("fullseye_make_task", {"kind": "blob_count", "seed": 0}, cat, _store())
    assert "short-secret" not in str(exc.value)
    monkeypatch.setenv(T.SECRET_ENV, "experiment-secret-0123456789abcdef-XYZ")
    monkeypatch.delenv(T.AUDIT_ENV)
    with pytest.raises(S.ArgError, match=T.AUDIT_ENV):
        call_tool("fullseye_make_task", {"kind": "blob_count", "seed": 0}, cat, _store())
    # 監査記録を MCP の根の中に置くと load_image で読めてしまう
    monkeypatch.setenv(T.AUDIT_ENV, str(tmp_path / "audit.jsonl"))
    with pytest.raises(S.ArgError, match="根の中"):
        call_tool("fullseye_make_task", {"kind": "blob_count", "seed": 0}, cat, HandleStore(roots=[str(tmp_path)]))


# --------------------------------------------------------------------------- #
# 8. 採点器の中身(F5)                                                           #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("kind", sorted(PIPELINES))
def test_applied_tolerance_equals_the_advertised_and_preregistered_one(cat, kind):
    store = _store()
    made = _make(cat, store, kind, 2)["structuredContent"]
    advertised = {m["name"]: m["tolerance"] for m in made["metrics"]}
    for stages in PIPELINES[kind]:
        sc = _score(cat, store, made["task_id"], stages)["structuredContent"]
        assert {m["name"]: m["tolerance"] for m in sc["metrics"]} == advertised
    if kind != "fringe_phase":
        assert advertised == {k: T._round(float(v)) for k, v in TT.TOLERANCES[kind].items()}


def _edge_points(top, bottom):
    return {"shape": (96, 64), "cs": [np.array([[top, 31.5]]), np.array([[bottom, 31.5]])]}


def _shifted_mask(mask, dy, dx):
    return np.roll(np.roll(mask, dy, axis=0), dx, axis=1)


def _record(kind, seed=3):
    arr, truth, p = T.generate(kind, seed)
    return T.TaskRecord("x", kind, seed, p, arr, truth, 0.0)


def test_the_error_sign_is_never_returned():
    """真値 ± d の 2 つの出力は、誤差も説明も同じでなければならない(符号を返さない約束)。"""
    def same(rec, lo, hi):
        a, b = T.score_output(rec, lo), T.score_output(rec, hi)
        assert a == b and T.explain(a) == T.explain(b), (rec.kind, a, b)
        for level in T.FEEDBACK_LEVELS:
            assert T.render_feedback(a, level) == T.render_feedback(b, level)
    r = _record("blob_count")
    same(r, np.float64(r.truth["count"] - 2), np.float64(r.truth["count"] + 2))
    r = _record("edge_subpixel")
    t, b = r.truth["top"], r.truth["bottom"]
    same(r, _edge_points(t - 0.3, b + 0.2), _edge_points(t + 0.3, b - 0.2))
    r = _record("fringe_phase")
    same(r, r.truth["phase"] + 0.2, r.truth["phase"] - 0.2)
    r = _record("defect_inspect")
    m = r.truth["mask"]
    a, b = T.score_output(r, _shifted_mask(m, 0, 3)), T.score_output(r, _shifted_mask(m, 0, -3))
    # 違うのは、解析的な中心と画素のマスクの重心のずれ(0.02 px 程度)だけ
    assert a[0]["error"] == pytest.approx(b[0]["error"], abs=0.05)
    assert all(x["error"] >= 0 for x in a + b)


def test_every_metric_has_a_failing_example():
    r = _record("blob_count")
    assert not T.score_output(r, np.float64(r.truth["count"] + 1))[0]["passed"], "1 個違いが通った"
    assert T.score_output(r, np.float64(r.truth["count"]))[0]["passed"]
    r = _record("edge_subpixel")
    t, b = r.truth["top"], r.truth["bottom"]
    top_only = T.score_output(r, _edge_points(t + 0.3, b))
    assert [m["passed"] for m in top_only] == [False, True]
    bottom_only = T.score_output(r, _edge_points(t, b - 0.3))
    assert [m["passed"] for m in bottom_only] == [True, False]
    within = T.score_output(r, _edge_points(t + 0.1, b - 0.1))
    assert len(within) == 2
    assert all(m["passed"] for m in within)
    r = _record("defect_inspect")
    m = r.truth["mask"]
    exact = {x["name"]: x for x in T.score_output(r, m)}
    assert all(x["passed"] for x in exact.values())
    shifted = {x["name"]: x for x in T.score_output(r, _shifted_mask(m, 0, 3))}    # 面積は同じ、3 px ずれ
    assert not shifted["centroid_error"]["passed"] and shifted["area_rel_error"]["passed"]
    bloated = {x["name"]: x for x in T.score_output(r, _dilate(m, 2))}
    assert not bloated["area_rel_error"]["passed"]
    # 重心と面積は合うが形が違う(高さ 2 行の横棒)→ IoU だけが落とす
    cy, cx, area = r.truth["cy"], r.truth["cx"], r.truth["area"]
    bar = np.zeros_like(m)
    half = int(round(area / 4))
    bar[int(round(cy)) - 1:int(round(cy)) + 1, int(round(cx)) - half:int(round(cx)) + half] = True
    flat = {x["name"]: x for x in T.score_output(r, bar)}
    assert flat["centroid_error"]["passed"] and flat["area_rel_error"]["passed"], flat
    assert not flat["mask_iou_deficit"]["passed"], flat
    r = _record("fringe_phase")
    assert not T.score_output(r, r.truth["phase"] + 0.5 * r.truth["phase"].std())[0]["passed"]


def test_fringe_allows_only_a_global_two_pi_m_offset():
    r = _record("fringe_phase")
    phase = r.truth["phase"]
    for m in (-2, -1, 1, 3):
        assert T.score_output(r, phase + 2 * math.pi * m)[0]["passed"], m
    for offset in (0.3, 1.0, math.pi, 2 * math.pi + 0.5):
        assert not T.score_output(r, phase + offset)[0]["passed"], offset


def _dilate(mask, k):
    from scipy import ndimage
    return ndimage.binary_dilation(mask, iterations=k)


def _erode(mask, k):
    from scipy import ndimage
    return ndimage.binary_erosion(mask, iterations=k)


# --------------------------------------------------------------------------- #
# 9. 保管庫の lock(F9)                                                          #
# --------------------------------------------------------------------------- #
def test_concurrent_claims_grant_exactly_the_cap():
    ts = T.TaskStore(max_attempts=32)
    rec = ts.make("edge_subpixel", 1)
    granted, refused = [], []
    barrier = threading.Barrier(16)

    def worker():
        barrier.wait()
        for _ in range(4):
            try:
                ts.claim(rec.task_id)
                granted.append(1)
            except T.TaskError as exc:
                refused.append(exc.reason)
    threads = [threading.Thread(target=worker) for _ in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(granted) == 32 and set(refused) == {"attempts_exhausted"} and len(refused) == 32
    assert ts.attempts_of("edge_subpixel", 1) == 32


def test_the_stdio_server_lists_and_runs_both_tools():
    """実 stdio を通す(関数を直接呼ぶテストは配線の誤りを隠す)。"""
    import io
    from fullseye.mcp import run_stdio_server

    def frame(obj):
        body = json.dumps(obj).encode("utf-8")
        return b"Content-Length: %d\r\n\r\n" % len(body) + body

    def call(i, name, **args):
        return frame({"jsonrpc": "2.0", "id": i, "method": "tools/call",
                      "params": {"name": name, "arguments": args}})
    first = io.BytesIO(frame({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
                       + call(2, "fullseye_make_task", kind="edge_subpixel", seed=3))
    out = io.BytesIO()
    store = _store()
    run_stdio_server(first, out, store=store)
    msgs = _parse(out.getvalue())
    assert {"fullseye_make_task", "fullseye_score_pipeline"} <= {t["name"] for t in msgs[0]["result"]["tools"]}
    tid = msgs[1]["result"]["structuredContent"]["task_id"]
    second = io.BytesIO(call(3, "fullseye_score_pipeline", task_id=tid, stages=PIPELINES["edge_subpixel"][0]))
    out = io.BytesIO()
    run_stdio_server(second, out, store=store)
    (msg,) = _parse(out.getvalue())
    assert msg["result"]["structuredContent"]["passed"] is True


def _parse(raw: bytes) -> list:
    msgs = []
    while raw:
        head, _, rest = raw.partition(b"\r\n\r\n")
        n = int(head.split(b":")[1])
        msgs.append(json.loads(rest[:n]))
        raw = rest[n:]
    return msgs
