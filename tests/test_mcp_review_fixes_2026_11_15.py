# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PR #318(MCP の使い勝手の直し)の独立レビュー(2026-11-15)の指摘の回帰試験。

1. 表(dict)の中の配列が、ハンドル置き場のバイトの上限を素通りした。``len(repr(...))`` で数えていて、repr は大きい
   配列を「...」で省くので、128 MB の配列の表が 271 バイトになった(6 つ入れて 768 MB を持ったまま)。
2. 配列の真ん中だけが違う 2 つの表に同じハンドルが付き、2 回目の読み出しで前の値が返った
   (``json.dumps(default=repr)`` の repr が 1000 要素を超える配列を省く)。
3. 日本語の検索の評価(23 問)が repo に無く、再現できなかった。「ピクセルをミリメートルに変換したい」で
   pixel_to_world / mm_per_px_from_reference が上位 5 件に出なかった。
4. 入力の無い台帳 op を fullseye_apply で呼ぶと「handle は必須」で断られた(docs/MCP.md は呼べると書いていた)。
5. 作業プロセスで読み込みを許す場所に、親の sys.path が全部入った(``python -m`` で起動すると cwd も入る)。
6. 作業プロセスの結果(.npy)を、親が全部読んでから画素の上限で断っていた。
"""
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (ROOT, os.path.dirname(os.path.abspath(__file__)), os.path.join(ROOT, "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fullseye.mcp import server as S                              # noqa: E402
from fullseye.mcp.catalog import Catalog                          # noqa: E402
from fullseye.mcp.handles import HandleError, HandleStore         # noqa: E402
from fullseye.mcp.opworker import OpWorker, OpWorkerError, close_worker, decode_tree  # noqa: E402

FIXTURE = {"ledger_module": "mcp_worker_fixture_ledger", "ledger_table": "TABLE", "data_names": []}


@pytest.fixture(scope="module")
def cat():
    return Catalog.load()


@pytest.fixture()
def store(tmp_path):
    return HandleStore(thumb_dir=str(tmp_path / "thumb"))


@pytest.fixture(scope="module")
def worker():
    w = OpWorker()
    yield w
    w.close()


@pytest.fixture(scope="module", autouse=True)
def _close_shared_worker():
    yield
    close_worker()


def _held_array_bytes(store) -> int:
    """置き場が実際に持っている配列のバイト数(同じ配列は 1 回だけ数える)。"""
    seen, total, todo = set(), 0, [store._arr[h] for h in store._meta]
    while todo:
        item = todo.pop()
        if isinstance(item, np.ndarray):
            if id(item) not in seen:
                seen.add(id(item))
                total += int(item.nbytes)
        elif isinstance(item, dict):
            todo.extend(item.values())
        elif isinstance(item, (list, tuple)):
            todo.extend(item)
    return total


# --------------------------------------------------------------------------- 1: 表の中の配列もバイトの上限に数える
def test_arrays_inside_tables_count_against_the_byte_limit(tmp_path):
    """直す前: 表の大きさは repr の長さ(数百バイト)で、400,000 バイトの配列の表を 6 つ入れても追い出しが起きなかった。"""
    store = HandleStore(roots=[], max_bytes=1 << 20, thumb_dir=str(tmp_path / "t"))
    for k in range(6):                                   # 1 表 = 400,000 バイトの配列。上限は 1 MiB
        meta = store.put({"field": np.full(50_000, float(k)), "rows": [{"a": np.full(10, k)}]},
                         sort="table", provenance=[])
        assert meta["bytes"] >= 400_000, meta
    assert _held_array_bytes(store) <= store.max_bytes
    stats = store.stats()
    assert stats["bytes"] <= store.max_bytes and stats["evicted"] >= 4, stats
    with pytest.raises(HandleError, match="byte limit"):
        store.put({"field": np.zeros(200_000)}, sort="table", provenance=[])          # 1.6 MB > 1 MiB
    with pytest.raises(HandleError, match="byte limit"):
        store.put([np.zeros(100_000), np.zeros(100_000)], sort="any", provenance=[])  # list の中の配列も


def test_a_table_and_the_handles_of_its_fields_count_the_shared_array_once(tmp_path):
    """pipeline は表を入れた後、表の中の 2-D の配列を image のハンドルにする(同じ配列)。2 回数えると、上限の
    半分を超える配列の表は、自分の欄のハンドルを入れた時に追い出される。直しで入った数え方の設計の試験
    (直す前も通る。直す前は表を数百バイトと数えていたので、二重に数える事が無かった)。"""
    store = HandleStore(roots=[], max_bytes=1 << 20, thumb_dir=str(tmp_path / "t"))
    image = np.zeros((300, 300))                         # 720,000 バイト: 2 回数えると 1 MiB を超える
    table = store.put({"image": image, "height_mm": 3.0}, sort="table", provenance=[])
    field = store.put(image, sort="image", provenance=[{"field": "image"}])
    for meta in (table, field):
        store.get(meta["handle"])                        # どちらも生きている(追い出されていない)
    assert store.stats()["bytes"] < 2 * image.nbytes and store.stats()["evicted"] == 0


# --------------------------------------------------------------------------- 2: 表のハンドルは配列の中身ごと
def test_tables_that_differ_only_in_the_middle_of_a_long_array_get_different_handles(tmp_path):
    """直す前: zeros(5000) と [2500] だけ 1 の配列の表が同じハンドルになり(dedup)、読むと前の値 0.0 が返った。"""
    store = HandleStore(roots=[], max_bytes=1 << 24, thumb_dir=str(tmp_path / "t"))
    a = np.zeros(5000)
    b = a.copy()
    b[2500] = 1.0
    first = store.put({"v": a}, sort="table", provenance=[])
    second = store.put({"v": b}, sort="table", provenance=[])
    assert first["handle"] != second["handle"] and not second.get("dedup")
    assert store.get(second["handle"])[1]["v"][2500] == 1.0
    nested = [store.put({"rows": [{"v": x}]}, sort="table", provenance=[])["handle"] for x in (a, b)]
    assert nested[0] != nested[1]
    assert store.put([a], sort="any", provenance=[])["handle"] != store.put([b], sort="any", provenance=[])["handle"]
    assert store.put({"v": a.astype(np.float32)}, sort="table", provenance=[])["handle"] != first["handle"]
    assert store.put({"v": a.reshape(50, 100)}, sort="table", provenance=[])["handle"] != first["handle"]
    again = store.put({"v": a.copy()}, sort="table", provenance=[])     # 同じ中身は同じハンドル(重複して持たない)
    assert again["handle"] == first["handle"] and again["dedup"] is True
    keys = store.put({"x": 1.0, "y": [1, "a", None]}, sort="table", provenance=[])["handle"]
    assert store.put({"y": [1, "a", None], "x": 1.0}, sort="table", provenance=[])["handle"] == keys  # 鍵の順は問わない


# --------------------------------------------------------------------------- 3: 日本語の検索の評価と px→mm
@pytest.mark.parametrize("query", ["ピクセルをミリメートルに変換したい", "ピクセル を mm に換算"])
def test_pixel_to_millimetre_requests_find_the_conversion_ops(cat, store, query):
    """直す前: 「ピクセル」「ミリメートル」に英語の語の橋が無く、要約に「各ピクセル」を含む局所しきい値の op などが
    上位に来た。"""
    ops = S.call_tool("fullseye_find_ops", {"query": query}, cat, store)["structuredContent"]["ops"]
    top5 = [o["name"] for o in ops[:5]]
    assert {"pixel_to_world", "mm_per_px_from_reference"} & set(top5), (query, top5)


#: tools/mcp_find_ops_eval.py の床(2026-11-15 に測った値。master 2a6cefab26 は verification 14 / 5、review 9 / 5)
_EVAL_FLOOR = {"verification_2026_11_13": {"hit": 19, "usable": 16},
               "review_2026_11_15": {"hit": 10, "usable": 9},
               "review_2026_11_15/untuned": {"hit": 9, "usable": 8}}


def test_japanese_search_evaluation_is_in_the_repo_and_does_not_fall(cat, store):
    """直す前: PR 本文の「23 回、14 → 19 / 5 → 16」の問いと採点が repo に無かった。問題集と道具を置き、
    合わせた問い(tuned)とそうでない問いを分けて数える。"""
    import mcp_find_ops_eval as E
    ev = E.load()
    sets = {q["set"] for q in ev["queries"]}
    assert sets == {"verification_2026_11_13", "review_2026_11_15"}
    assert sum(q["set"] == "verification_2026_11_13" for q in ev["queries"]) == 23
    assert sum(q["set"] == "review_2026_11_15" and not q["tuned"] for q in ev["queries"]) == 9
    res = E.evaluate(ev, cat=cat, store=store)
    low = {key: (res["sets"][key], floor) for key, floor in _EVAL_FLOOR.items()
           if any(res["sets"][key][m] < v for m, v in floor.items())}
    assert not low, "床を割った: %s\n外れ: %s" % (low, [(r["query"], r["top"]) for r in res["rows"] if not r["relevant"]])


# --------------------------------------------------------------------------- 4: 入力の無い台帳 op は handle を省ける
def test_apply_runs_a_ledger_op_that_takes_no_input_without_a_handle(cat, store):
    """直す前: fullseye_apply(op=abbe_number, params={material: N-SF11}) が「arguments.handle は必須」で断られた。"""
    schema = next(t for t in S.handle_tools_list({})["tools"] if t["name"] == "fullseye_apply")["inputSchema"]
    assert schema["required"] == ["op"]
    r = S.call_tool("fullseye_apply", {"op": "abbe_number", "params": {"material": "N-SF11"}}, cat, store)
    assert not r["isError"], r["content"][0]["text"]
    assert r["structuredContent"]["stages"][0]["status"] == "ok"
    with pytest.raises(S.ArgError, match="handle"):                       # registry の op は画像のハンドルを取る
        S.call_tool("fullseye_apply", {"op": "gaussian"}, cat, store)
    with pytest.raises(S.ArgError, match="handle"):                       # 入力のある台帳 op も
        S.call_tool("fullseye_apply", {"op": "pixel_to_world", "params": {"mm_per_px": 0.02}}, cat, store)


# --------------------------------------------------------------------------- 5: 作業プロセスが読める場所
def test_worker_sandbox_reads_only_the_python_and_fullseye_trees(tmp_path, monkeypatch):
    """直す前: 読める場所に sys.path が全部入った。``python -m`` は cwd を sys.path[0] に置くので、ドライブの直下や
    ホームで起動すると、読み込みの制限が実質なくなった。"""
    import json
    from fullseye.mcp.opworker import _Sandbox
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    secret = elsewhere / "secret.txt"
    secret.write_text("secret", encoding="utf-8")
    monkeypatch.chdir(elsewhere)
    monkeypatch.setattr(sys, "path", ["", str(elsewhere)] + sys.path)
    box = _Sandbox(str(tmp_path / "scratch"))
    assert os.path.realpath(str(elsewhere)) not in box.read_roots
    box.armed = True
    for readable in (S.__file__, np.__file__, os.__file__, json.__file__, str(tmp_path / "scratch" / "x.npy")):
        box.hook("open", (readable, "r", 0))                              # fullseye・numpy・stdlib・作業フォルダ
    for unreadable in (str(secret), "secret.txt"):
        with pytest.raises(PermissionError):
            box.hook("open", (unreadable, "r", 0))


def test_worker_started_from_a_folder_on_sys_path_cannot_read_that_folder(tmp_path, monkeypatch):
    """同じ事を本物の作業プロセスで: 親の sys.path にあるだけの場所(cwd)のファイルを、op が読めない。"""
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    secret = elsewhere / "secret.txt"
    secret.write_text("secret", encoding="utf-8")
    monkeypatch.chdir(elsewhere)
    monkeypatch.setattr(sys, "path", [str(elsewhere)] + sys.path)
    w = OpWorker()
    try:
        with pytest.raises(OpWorkerError) as err:
            w.run(dict(FIXTURE, key="read_outside"), [], {"target": str(secret)}, time_limit_s=60, max_rss=1 << 30)
        assert (err.value.reason, err.value.error_type) == ("op_error", "PermissionError")
        value, _info = w.run(dict(FIXTURE, key="table"), [], {}, time_limit_s=60, max_rss=1 << 30)
        assert value["height_mm"] == 6.0                                   # 台帳と numpy は読める
    finally:
        w.close()


# --------------------------------------------------------------------------- 6: 結果の大きさは作業プロセスの側で断る
def test_worker_refuses_a_result_with_too_many_elements_before_handing_it_back(worker):
    """直す前: 作業プロセスは結果を全部 .npy に書き、親が全部読んでから画素の上限で断っていた。"""
    with pytest.raises(OpWorkerError) as err:
        worker.run(dict(FIXTURE, key="zeros", max_elements=10_000), [], {"rows": 300, "cols": 300},
                   time_limit_s=60, max_rss=1 << 30)
    assert err.value.reason == "output_limit" and "90000" in str(err.value) and "10000" in str(err.value)
    with pytest.raises(OpWorkerError) as err:
        worker.run(dict(FIXTURE, key="zeros", max_result_bytes=100_000), [], {"rows": 300, "cols": 300},
                   time_limit_s=60, max_rss=1 << 30)
    assert err.value.reason == "output_limit" and "720000" in str(err.value)
    value, _info = worker.run(dict(FIXTURE, key="zeros", max_elements=10_000), [], {"rows": 50, "cols": 50},
                              time_limit_s=60, max_rss=1 << 30)
    assert value["image"].shape == (50, 50)                                # 上限の内なら今までどおり返る


def test_parent_checks_the_size_of_a_returned_array_file_before_reading_it(tmp_path):
    """親の側も、子の出力(信頼境界)の .npy を、見出しの形で数えてから読む。"""
    np.save(tmp_path / "a000001.npy", np.zeros((300, 300)))
    node = {"t": "d", "v": {"image": {"t": "n", "file": "a000001.npy"}}}
    with pytest.raises(ValueError, match="elements"):
        decode_tree(node, str(tmp_path), max_elements=10_000)
    assert decode_tree(node, str(tmp_path))["image"].shape == (300, 300)


def test_pipeline_reports_a_ledger_result_over_the_pixel_limit_without_reading_it(cat, store, monkeypatch):
    """MCP の道具から: 上限を超える結果は、作業プロセスの側で断られ、resource_limit(output_limit)の段になる。
    親は結果の配列を復号しない。"""
    import fullseye.mcp.opworker as W
    limits = S._isolated_limits()
    monkeypatch.setattr(S, "_isolated_limits", lambda: dict(limits, max_pixels=1000))
    decoded = []
    real_decode = W.decode_tree

    def spy(node, folder, *args, **kwargs):
        value = real_decode(node, folder, *args, **kwargs)
        decoded.append(value)
        return value

    monkeypatch.setattr(W, "decode_tree", spy)
    r = S.call_tool("fullseye_pipeline", {"stages": [{"op": "cplx_plane_grid"}]}, cat, store)
    assert r["isError"]
    stage = r["structuredContent"]["stages"][0]
    assert stage["reason"] == "resource_limit" and stage["error"]["limit"] == "output_limit", stage
    assert not [v for v in decoded if isinstance(v, np.ndarray) and v.size > 1000]
