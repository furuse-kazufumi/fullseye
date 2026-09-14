# -*- coding: utf-8 -*-
"""MCP の画像系 tool(load_image / apply / inspect / list_samples)の検証。

段取り 2 + 3(2026-09-15): 返り値は**数値 + 判定 + 劣化台帳**、画像は在らず、判定が
ok でないときだけ入出力対比の小図を**自動昇格**する(TRIZ 時間分離 / #25 セルフサービス)。

検証の設計は test_mcp_server.py と同じ 4 本柱:
1. 実 stdio でハンドルを**連鎖**させる(Popen で 1 往復ずつ。返り値から次の引数を作る)
2. 壊して確かめる: 根の外 / `..` 脱出 / 拡張子 / 無いファイル / 未知ハンドル / 型不一致 /
   つまみ範囲外 / strict の劣化拒否 —— それぞれ**狙った文言**で
3. 返った ≠ 中身: 判定は必ず数値と併記、小図は実際に開いて高さと非黒を見る
4. 昇格の 4 条件(auto で ok → 無し / auto で異常 → 有り / none → 無し / thumb → 有り)
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from fullseye.mcp import Catalog, call_tool  # noqa: E402
from fullseye.mcp.handles import PREFIX, SAMPLE_DIR, HandleError, HandleStore  # noqa: E402
from fullseye.mcp.server import ArgError, read_message, write_message  # noqa: E402


@pytest.fixture(scope="module")
def cat():
    return Catalog.load()


@pytest.fixture
def root(tmp_path):
    """テスト専用の根。定数画像・小さい画像をここに置く。"""
    import imgio
    imgio.save(str(tmp_path / "const.png"), np.zeros((32, 32)))
    imgio.save(str(tmp_path / "tiny.png"), np.random.default_rng(0).random((4, 4)))
    (tmp_path / "outside").mkdir()
    imgio.save(str(tmp_path / "outside" / "x.png"), np.zeros((8, 8)))
    return tmp_path


@pytest.fixture
def store(root):
    return HandleStore(roots=[SAMPLE_DIR, str(root)], thumb_dir=str(root / "thumbs"))


def _sample(name="coins"):
    p = os.path.join(SAMPLE_DIR, name + ".png")
    assert os.path.exists(p), p
    return p


def _links(res):
    return [c for c in res["content"] if c["type"] == "resource_link"]


def _png(uri: str) -> np.ndarray:
    import imgio
    from urllib.request import url2pathname
    from urllib.parse import urlparse
    path = url2pathname(urlparse(uri).path)
    return imgio.load(path, color=True)


# --------------------------------------------------------------------------- #
# 1. 実 stdio でハンドルを連鎖                                                   #
# --------------------------------------------------------------------------- #
def test_real_stdio_chains_handles_across_calls():
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    env.pop("FULLSEYE_MCP_ROOT", None)                         # 既定の根 = 同梱サンプルだけ
    p = subprocess.Popen([sys.executable, "-m", "fullseye.mcp"], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=ROOT, env=env)
    seq = [0]

    def talk(method, **params):
        seq[0] += 1
        write_message(p.stdin, {"jsonrpc": "2.0", "id": seq[0], "method": method, "params": params})
        r = read_message(p.stdout)
        assert r is not None and r["id"] == seq[0], r
        return r

    def call(tool, **a):
        r = talk("tools/call", name=tool, arguments=a)
        assert "result" in r, r
        return r["result"]

    try:
        talk("initialize", protocolVersion="2025-06-18", capabilities={}, clientInfo={"name": "t", "version": "0"})
        s = call("fullseye_list_samples")
        assert not s["isError"]
        coins = next(x for x in s["structuredContent"]["samples"] if x["name"] == "coins")
        h0 = call("fullseye_load_image", path=coins["path"])
        assert not h0["isError"], h0["content"][0]["text"]
        sc0 = h0["structuredContent"]
        assert sc0["handle"].startswith(PREFIX) and sc0["sort"] == "image"
        assert sc0["verdict"] == "ok" and "std" in sc0["stats"], sc0
        assert not _links(h0), "健全な画像に小図が付いている(auto は異常時だけ)"

        seg = call("fullseye_apply", handle=sc0["handle"], op="otsu")
        assert not seg["isError"], seg["content"][0]["text"]
        sc1 = seg["structuredContent"]
        assert sc1["in_sort"] == "image" and sc1["out_sort"] == "region"
        assert sc1["handle"].startswith(PREFIX) and sc1["degraded"] == [] and sc1["strict"] is True

        n = call("fullseye_apply", handle=sc1["handle"], op="count_obj")
        assert not n["isError"], n["content"][0]["text"]
        sc2 = n["structuredContent"]
        assert sc2["handle"] is None and isinstance(sc2["value"], float) and sc2["value"] > 0, sc2

        ins = call("fullseye_inspect", handle=sc1["handle"], vision="thumb")
        assert not ins["isError"]
        assert [x for x in ins["structuredContent"]["provenance"] if "apply" in x][-1]["apply"] == "otsu"
        assert len(_links(ins)) == 1
    finally:
        p.stdin.close()
        rc = p.wait(timeout=60)
    rest = p.stdout.read()
    assert rest.strip() == b"", "stdout にフレーム以外のバイト: %r" % rest[:80]
    assert rc == 0, p.stderr.read().decode("utf-8", "replace")[-1500:]


# --------------------------------------------------------------------------- #
# 2. 壊して確かめる                                                              #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("path, why", [
    (os.path.join(ROOT, "pyproject.toml"), "根の外"),
    (os.path.join(SAMPLE_DIR, "..", "sample_thumbs", "coins.png"), "根の外"),   # .. 脱出
    (os.path.join(SAMPLE_DIR, "manifest.json"), "拡張子"),
    (os.path.join(SAMPLE_DIR, "__no_such__.png"), "ファイルが無い"),
    ("", "空"),
])
def test_paths_outside_the_sandbox_are_refused_with_the_reason(cat, store, path, why):
    with pytest.raises(ArgError) as ei:
        call_tool("fullseye_load_image", {"path": path}, cat, store)
    assert why in str(ei.value), str(ei.value)


def test_an_extra_root_from_the_fixture_is_readable_but_its_sibling_is_not(cat, store, root):
    ok = call_tool("fullseye_load_image", {"path": str(root / "const.png")}, cat, store)
    assert not ok["isError"]
    # 根は tmp_path 全体なので outside/ も中。根を狭めた store で確かめる
    narrow = HandleStore(roots=[str(root / "outside")], thumb_dir=str(root / "t2"))
    with pytest.raises(ArgError) as ei:
        call_tool("fullseye_load_image", {"path": str(root / "const.png")}, cat, narrow)
    assert "根の外" in str(ei.value)


@pytest.mark.parametrize("handle, why", [
    ("fullseye://img/0000000000000000", "知らないハンドル"),
    ("not-a-handle", "ハンドルは"),
    ("fullseye://img/", "知らないハンドル"),
])
def test_bad_handles_are_refused(cat, store, handle, why):
    with pytest.raises(ArgError) as ei:
        call_tool("fullseye_inspect", {"handle": handle}, cat, store)
    assert why in str(ei.value), str(ei.value)


def test_sort_mismatch_is_refused_at_the_boundary(cat, store):
    """image のハンドルに region 用の op。黙って走らせない(型契約を境界で守る)。"""
    h = call_tool("fullseye_load_image", {"path": _sample()}, cat, store)["structuredContent"]["handle"]
    with pytest.raises(ArgError) as ei:
        call_tool("fullseye_apply", {"handle": h, "op": "count_obj"}, cat, store)
    m = str(ei.value)
    assert "型の不一致" in m and "region" in m and "image" in m, m


def test_unknown_op_in_apply_names_nearest_registry_ops(cat, store):
    h = call_tool("fullseye_load_image", {"path": _sample()}, cat, store)["structuredContent"]["handle"]
    with pytest.raises(ArgError) as ei:
        call_tool("fullseye_apply", {"handle": h, "op": "gaussy"}, cat, store)
    assert "registry 層に無い" in str(ei.value) and "gaussian" in str(ei.value)


@pytest.mark.parametrize("bad, why", [
    ({"a": 1.5}, "以下"), ({"b": -0.1}, "以上"), ({"a": "x"}, "数"),
    ({"a": True}, "数"), ({"vision": "always"}, "どれか"), ({"allow_degraded": "yes"}, "真偽値"),
])
def test_bad_apply_arguments_are_refused(cat, store, bad, why):
    h = call_tool("fullseye_load_image", {"path": _sample()}, cat, store)["structuredContent"]["handle"]
    with pytest.raises(ArgError) as ei:
        call_tool("fullseye_apply", {"handle": h, "op": "gaussian", **bad}, cat, store)
    assert why in str(ei.value), str(ei.value)


def _degrading_op(cat, store, root):
    """strict で**実際に例外を出す** (op, 入力ハンドル) を実測で選ぶ。

    ★最初は「xsk_inpaint は 4x4 で劣化するはず」と記憶で書いて外した(4x4 乱数では
    普通に走った)。劣化する組は環境(optional backend)と入力の両方で決まるので、
    候補 op × 候補入力を `on_error="raise"` で走らせ、最初に例外を出した組を使う。
    1 つも無ければ **理由を挙げて skip**(黙って緑にしない)。
    """
    import fullseye
    import imgio
    import ops
    inputs = {"tiny": np.random.default_rng(0).random((4, 4)),
              "zeros4": np.zeros((4, 4)), "two": np.random.default_rng(1).random((2, 2))}
    cands = ["xsk_inpaint", "xsk2_wiener", "xsk2_hog", "xkor_laplacian", "xkor_clahe",
             "dl_guided_filter", "xwt_mra_component", "xsp_savgol", "xsk2_multiotsu"]
    tried = []
    for n in cands:
        op = ops._BY_NAME.get(n)
        if op is None or op.in_sort != "image" or op.out_sort not in ("image", "region"):
            continue
        for iname, iv in inputs.items():
            try:
                fullseye.apply(iv.copy(), n, 0.5, 0.5, on_error="raise")
                tried.append((n, iname, "ok"))
            except Exception as exc:                            # noqa: BLE001
                p = root / ("degrade_%s.png" % iname)
                if not p.exists():
                    imgio.save(str(p), iv)
                h = call_tool("fullseye_load_image", {"path": str(p), "vision": "none"}, cat, store)["structuredContent"]["handle"]
                return n, h
    pytest.skip("strict で例外を出す (op, 入力) の組が見つからない: %s" % tried[:12])


def test_strict_refuses_a_degrading_op_and_says_why(cat, store, root):
    op, h = _degrading_op(cat, store, root)
    res = call_tool("fullseye_apply", {"handle": h, "op": op}, cat, store)
    assert res["isError"] is True, "strict なのに通った: %s" % res["content"][0]["text"][:200]
    text = res["content"][0]["text"]
    assert "strict で拒否" in text and op in text and "allow_degraded" in text
    sc = res["structuredContent"]
    assert sc["strict"] is True and "error" in sc and sc["error"]["message"]


def test_allow_degraded_returns_a_value_but_puts_the_degradation_on_the_record(cat, store, root):
    op, h = _degrading_op(cat, store, root)
    res = call_tool("fullseye_apply", {"handle": h, "op": op, "allow_degraded": True}, cat, store)
    assert res["isError"] is False, res["content"][0]["text"][:300]
    sc = res["structuredContent"]
    assert sc["strict"] is False
    assert sc["degraded"], "fail-soft で走ったのに劣化台帳が空 —— 沈黙のスキップ"
    d = sc["degraded"][0]
    assert d["name"] == op and d["source"] and d["error"]
    assert sc["escalate"] is True and any("劣化" in r for r in sc["reasons"])
    assert "劣化" in res["content"][0]["text"]


# --------------------------------------------------------------------------- #
# 3. 判定は数値と併記 / 4. 昇格の 4 条件                                          #
# --------------------------------------------------------------------------- #
def test_a_constant_image_is_called_constant_with_numbers_and_gets_a_thumbnail(cat, store, root):
    res = call_tool("fullseye_load_image", {"path": str(root / "const.png")}, cat, store)
    sc = res["structuredContent"]
    assert sc["verdict"] == "constant" and sc["escalate"] is True
    assert sc["stats"]["std"] == 0.0 and sc["stats"]["min"] == 0.0 and sc["stats"]["max"] == 0.0
    assert any("std=0" in r for r in sc["reasons"])
    links = _links(res)
    assert len(links) == 1 and "自動で付けた" in links[0]["description"]
    img = _png(links[0]["uri"])
    assert img.shape[0] == 96, img.shape


def test_vision_none_suppresses_the_thumbnail_even_when_the_verdict_is_bad(cat, store, root):
    res = call_tool("fullseye_load_image", {"path": str(root / "const.png"), "vision": "none"}, cat, store)
    assert res["structuredContent"]["verdict"] == "constant"
    assert not _links(res)


def test_a_healthy_output_gets_no_thumbnail_in_auto_but_one_when_forced(cat, store):
    h = call_tool("fullseye_load_image", {"path": _sample()}, cat, store)["structuredContent"]["handle"]
    auto = call_tool("fullseye_apply", {"handle": h, "op": "gaussian", "a": 0.3}, cat, store)
    sc = auto["structuredContent"]
    assert sc["verdict"] == "ok" and not _links(auto)
    for k in ("min", "max", "mean", "std", "nonfinite"):
        assert k in sc["stats"], "判定だけで数値が無い: %s" % k
    forced = call_tool("fullseye_apply", {"handle": h, "op": "gaussian", "a": 0.3, "vision": "thumb"}, cat, store)
    links = _links(forced)
    assert len(links) == 1 and "要求により" in links[0]["description"]
    img = _png(links[0]["uri"])
    assert img.shape[0] == 96 and img.shape[1] > 96 * 2, img.shape       # 左右に 2 枚
    assert float(img.std()) > 0.05, "対比図が真っ黒 / 一様"
    left, right = img[:, : img.shape[1] // 2], img[:, img.shape[1] // 2 + 1:]
    assert float(np.abs(left.mean() - right.mean())) < 0.2, "入力と出力が別物に見える(gaussian a=0.3)"


def test_out_of_range_image_output_is_flagged_unless_the_ledger_exempts_it():
    """診断器が今夜の台帳を引いていること: 同じ数値でも op 名で判定が変わる。"""
    from fullseye.mcp.diagnose import stats_of, verdict_of
    st = stats_of(np.linspace(0.0, 715.0, 64 * 64).reshape(64, 64))
    exempt = verdict_of(st, op_name="tb_project_cylindrical", out_sort="image")
    plain = verdict_of(st, op_name="gaussian", out_sort="image")
    assert exempt["verdict"] == "ok" and any("物理量" in r for r in exempt["reasons"]), exempt
    assert plain["verdict"] == "out_of_range" and plain["escalate"] is True, plain


def test_nonfinite_is_flagged_unless_the_ledger_says_inf_is_the_answer():
    from fullseye.mcp.diagnose import stats_of, verdict_of
    a = np.ones((16, 16)); a[0, 0] = np.inf
    st = stats_of(a)
    assert st["nonfinite"] == 1
    plain = verdict_of(st, op_name="gaussian", out_sort="image")
    assert plain["verdict"] == "nonfinite" and plain["escalate"] is True
    ok = verdict_of(st, op_name="tb_geodesic_distances", out_sort="signal")
    assert ok["verdict"] == "ok" and any("答え" in r for r in ok["reasons"]), ok


def test_same_file_loaded_twice_is_the_same_handle(cat, store):
    a = call_tool("fullseye_load_image", {"path": _sample()}, cat, store)["structuredContent"]
    b = call_tool("fullseye_load_image", {"path": _sample()}, cat, store)["structuredContent"]
    assert a["handle"] == b["handle"] and b["dedup"] is True and a["dedup"] is False


def test_evicted_handles_are_refused_not_silently_recreated(root):
    st = HandleStore(roots=[str(root)], max_items=2, thumb_dir=str(root / "t3"))
    h1 = st.put(np.zeros((2, 2)), sort="image", provenance=[])["handle"]
    st.put(np.ones((2, 2)), sort="image", provenance=[])
    st.put(np.full((2, 2), 0.5), sort="image", provenance=[])
    with pytest.raises(HandleError) as ei:
        st.get(h1)
    assert "追い出された" in str(ei.value)
    assert st.stats()["evicted"] == 1


def test_tools_list_declares_the_image_tools_with_closed_schemas(cat):
    from fullseye.mcp.server import handle_tools_list
    tl = {t["name"]: t for t in handle_tools_list({})["tools"]}
    for n in ("fullseye_list_samples", "fullseye_load_image", "fullseye_apply",
              "fullseye_inspect", "fullseye_pipeline"):
        assert n in tl and tl[n]["inputSchema"]["additionalProperties"] is False
    assert tl["fullseye_apply"]["inputSchema"]["required"] == ["handle", "op"]
    assert tl["fullseye_pipeline"]["inputSchema"]["required"] == ["handle", "stages"]


# --------------------------------------------------------------------------- #
# 5. パイプライン(段ごとの記録、失敗した段で止まる、型連鎖)                        #
# --------------------------------------------------------------------------- #
def test_pipeline_records_every_stage_and_returns_the_final_handle(cat, store):
    h = call_tool("fullseye_load_image", {"path": _sample()}, cat, store)["structuredContent"]["handle"]
    res = call_tool("fullseye_pipeline", {
        "handle": h,
        "stages": [{"op": "gaussian", "a": 0.3}, {"op": "otsu"}, {"op": "count_obj"}],
    }, cat, store)
    assert res["isError"] is False, res["content"][0]["text"][:300]
    sc = res["structuredContent"]
    assert [s["op"] for s in sc["stages"]] == ["gaussian", "otsu", "count_obj"]
    assert sc["completed"] == 3 and sc["stopped_at"] is None
    for s in sc["stages"]:
        assert "verdict" in s and "stats" in s and s["degraded"] == []
    assert sc["stages"][0]["out_sort"] == "image" and sc["stages"][1]["out_sort"] == "region"
    assert sc["stages"][2]["handle"] is None and sc["stages"][2]["value"] > 0
    assert sc["handle"] == sc["stages"][1]["handle"], "最後の配列ハンドルが最終ハンドル"
    assert sc["value"] == sc["stages"][2]["value"]
    text = res["content"][0]["text"]
    assert "gaussian" in text and "otsu" in text and "count_obj" in text


def test_pipeline_refuses_a_broken_sort_chain_before_running_anything(cat, store):
    """2 段目が前段の型を受けられない: 1 段目すら走らせずに拒否(先に検査)。"""
    h = call_tool("fullseye_load_image", {"path": _sample()}, cat, store)["structuredContent"]["handle"]
    before = store.stats()["alive"]
    with pytest.raises(ArgError) as ei:
        call_tool("fullseye_pipeline", {"handle": h, "stages": [{"op": "otsu"}, {"op": "gaussian"}, {"op": "count_obj"}]}, cat, store)
    m = str(ei.value)
    assert "段 2" in m and "gaussian" in m and "region" in m and "image" in m, m
    assert store.stats()["alive"] == before, "拒否したのに中間ハンドルが増えた = 走っている"


def test_pipeline_in_strict_mode_stops_at_the_failing_stage_and_says_where(cat, store, root):
    op, h = _degrading_op(cat, store, root)
    # 1 段目の gaussian は画素値を変えるので、2 段目に届く入力は探した組と少し違う。
    # それでも失敗する組か(形と値域は変わらない)を、走らせる前に直接確かめる。
    import fullseye
    import ops
    _, arr = store.get(h)
    pre = fullseye.apply(arr.copy(), "gaussian", 0.5, 0.5, on_error="raise")
    try:
        fullseye.apply(pre, op, 0.5, 0.5, on_error="raise")
        pytest.skip("%s は gaussian 後の入力では失敗しない(組の選び直しが要る)" % op)
    except Exception:                                           # noqa: BLE001
        pass
    assert ops._BY_NAME[op].out_sort == "image", "3 段目 otsu に image を渡す前提"
    res = call_tool("fullseye_pipeline", {"handle": h, "stages": [{"op": "gaussian"}, {"op": op}, {"op": "otsu"}]}, cat, store)
    assert res["isError"] is True
    sc = res["structuredContent"]
    assert sc["completed"] == 1 and sc["stopped_at"] == 2, sc
    assert sc["stages"][0]["verdict"] and sc["stages"][1]["error"]["message"]
    assert len(sc["stages"]) == 2, "止まった段より後が記録されている"
    text = res["content"][0]["text"]
    assert "段 2" in text and op in text and "strict" in text


def test_pipeline_escalates_the_first_bad_stage_not_the_last(cat, store, root):
    """定数画像を通す: 1 段目から判定が割れる。小図は**最初に割れた段**の 1 枚だけ。"""
    h = call_tool("fullseye_load_image", {"path": str(root / "const.png"), "vision": "none"}, cat, store)["structuredContent"]["handle"]
    res = call_tool("fullseye_pipeline", {"handle": h, "stages": [{"op": "gaussian"}, {"op": "invert"}]}, cat, store)
    assert res["isError"] is False
    sc = res["structuredContent"]
    assert sc["stages"][0]["verdict"] == "constant" and sc["stages"][1]["verdict"] == "constant"
    links = _links(res)
    assert len(links) == 1 and "段 1" in links[0]["description"], [lk["description"] for lk in links]


@pytest.mark.parametrize("bad, why", [
    ({"stages": []}, "1 段以上"),
    ({"stages": [{"op": "gaussian", "c": 1}]}, "知らない引数"),
    ({"stages": [{"a": 0.5}]}, "必須"),
    ({"stages": [{"op": "gaussian", "a": 2}]}, "以下"),
    ({"stages": "gaussian,otsu"}, "配列"),
    ({"stages": [{"op": "gaussian"}] * 65}, "以下"),
])
def test_bad_pipeline_arguments_are_refused(cat, store, bad, why):
    h = call_tool("fullseye_load_image", {"path": _sample()}, cat, store)["structuredContent"]["handle"]
    with pytest.raises(ArgError) as ei:
        call_tool("fullseye_pipeline", {"handle": h, **bad}, cat, store)
    assert why in str(ei.value), str(ei.value)
