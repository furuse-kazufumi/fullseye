# -*- coding: utf-8 -*-
"""fullseye の MCP サーバ(PoC: 検索 / 引き当て / 被覆)の検証。

検証の設計(2026-09-15、今夜の教訓を全部載せる):

1. **実 stdio を通す** —— ``py -m fullseye.mcp`` を subprocess で起動し、Content-Length
   フレームで往復する。関数を直接呼ぶテストは配線バグを隠す
   ([[feedback_same_bug_class_recurs_check_siblings]] のテスト規律)。
2. **壊して確かめる** —— 未知 tool / 未知 method / 壊れた JSON / 型違い / 範囲外 /
   余計なキー / 未知 op 名 が、**狙った表明**で落ちることを本文で判定する。
   exit code や「落ちた」だけで満足しない([[feedback_falsify_a_gate_with_a_real_subject]])。
3. **返った ≠ 中身がある** —— ノート本文の長さと必須節、検索の層別内訳、上限劣化の
   明記を別に数える([[feedback_ran_is_not_meaningful_output]])。
4. **stdout の純度** —— プロトコル以外の 1 バイトも stdout に出ていないこと。
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from fullseye.mcp import TOOLS, Catalog, call_tool, dispatch, run_stdio_server  # noqa: E402
from fullseye.mcp.server import ArgError, MAX_SEARCH_LIMIT, read_message  # noqa: E402


# --------------------------------------------------------------------------- #
# 転送のヘルパ                                                                  #
# --------------------------------------------------------------------------- #
def _frame(msg: dict) -> bytes:
    body = json.dumps(msg, ensure_ascii=False).encode("utf-8")
    return b"Content-Length: " + str(len(body)).encode() + b"\r\n\r\n" + body


def _parse_all(buf: bytes) -> tuple[list[dict], bytes]:
    """フレームを全部読み、**余りのバイト**も返す(stdout の純度検査に使う)。"""
    stream = io.BytesIO(buf)
    out = []
    while True:
        pos = stream.tell()
        msg = read_message(stream)
        if msg is None:
            return out, buf[pos:]
        out.append(msg)


def _req(i, method, **params):
    return {"jsonrpc": "2.0", "id": i, "method": method, "params": params}


def _call(i, tool, **args):
    # ★引数名を `name` にしていて `_call(4, "fullseye_op_help", name="gaussian")` が
    #   TypeError になり、**subprocess の実 stdio 往復が 1 度も走らないまま**
    #   23 件が緑だった(2026-09-15)。走らなかった検査は無いのと同じ。
    return _req(i, "tools/call", name=tool, arguments=args)


@pytest.fixture(scope="module")
def cat():
    return Catalog.load()


def _run(cat, *msgs: bytes) -> list[dict]:
    """プロセス内で転送層ごと回す(フレーミングを通す)。"""
    stdin, stdout = io.BytesIO(b"".join(msgs)), io.BytesIO()
    run_stdio_server(stdin, stdout, catalog=cat)
    out, rest = _parse_all(stdout.getvalue())
    assert rest.strip() == b"", "stdout にフレーム以外のバイトがある: %r" % rest[:80]
    return out


# --------------------------------------------------------------------------- #
# 1. 実 stdio(subprocess)                                                      #
# --------------------------------------------------------------------------- #
def test_real_stdio_roundtrip_through_a_subprocess():
    """本物のプロセス境界を通す。initialize → tools/list → 検索 → 引き当て。"""
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    payload = b"".join([
        _frame(_req(1, "initialize", protocolVersion="2025-06-18", capabilities={},
                    clientInfo={"name": "pytest", "version": "0"})),
        _frame({"jsonrpc": "2.0", "method": "notifications/initialized"}),
        _frame(_req(2, "tools/list")),
        _frame(_call(3, "fullseye_search_ops", query="gauss", limit=5)),
        _frame(_call(4, "fullseye_op_help", name="gaussian")),
    ])
    p = subprocess.run([sys.executable, "-m", "fullseye.mcp"], input=payload,
                       capture_output=True, cwd=ROOT, env=env, timeout=120)
    assert p.returncode == 0, p.stderr.decode("utf-8", "replace")[-2000:]
    msgs, rest = _parse_all(p.stdout)
    assert rest.strip() == b"", (
        "stdout にプロトコル以外のバイトがある(print の混入?): %r" % rest[:120])
    assert [m["id"] for m in msgs] == [1, 2, 3, 4], "通知に返事をしている / 順序が崩れた"
    assert msgs[0]["result"]["protocolVersion"] == "2025-06-18"
    assert msgs[0]["result"]["serverInfo"]["name"] == "fullseye"
    names = {t["name"] for t in msgs[1]["result"]["tools"]}
    assert names == set(TOOLS)
    s = msgs[2]["result"]
    assert not s["isError"]
    top = [o["name"] for o in s["structuredContent"]["ops"]]
    # ★最初 `gaussian` が先頭と決めつけて落ちた。`gauss_filter` と `gaussian` は同じ
    #   HALCON 別名を共有する別 op で、`api.find_op` は `name == halcon` の正典を優先する。
    #   検索もその規約に揃えたので、正典が先頭・`gaussian` が上位に居ることを見る。
    assert top[0] == "gauss_filter", top
    assert "gaussian" in top[:3], top
    h = msgs[3]["result"]
    assert not h["isError"]
    assert h["structuredContent"]["found"] is True
    assert h["structuredContent"]["body_chars"] > 500
    links = [c for c in h["content"] if c["type"] == "resource_link"]
    assert links, "図が resource_link で 1 枚も付いていない"
    assert all(c["uri"].startswith("file:///") for c in links)
    assert b"[fullseye-mcp] ready" in p.stderr, "起動ログが stderr に出ていない"


# --------------------------------------------------------------------------- #
# 2. 壊して確かめる(狙った表明で落ちること)                                     #
# --------------------------------------------------------------------------- #
def test_unknown_tool_is_refused_by_name(cat):
    (r,) = _run(cat, _frame(_call(1, "fullseye_delete_everything")))
    assert r["error"]["code"] == -32602
    assert "知らない tool" in r["error"]["message"]
    assert "fullseye_delete_everything" in r["error"]["message"]


def test_unknown_method_is_refused(cat):
    (r,) = _run(cat, _frame(_req(1, "resources/read", uri="file:///x")))
    assert r["error"]["code"] == -32601
    assert "resources/read" in r["error"]["message"]


def test_broken_json_gets_parse_error_and_the_server_keeps_going(cat):
    bad = b"Content-Length: 5\r\n\r\n{bad}"
    r1, r2 = _run(cat, bad, _frame(_req(7, "ping")))
    assert r1["error"]["code"] == -32700 and r1["id"] is None
    assert r2["id"] == 7 and r2["result"] == {}, "壊れたフレームの後で止まった"


def test_notification_with_unknown_method_gets_no_reply(cat):
    out = _run(cat, _frame({"jsonrpc": "2.0", "method": "notifications/whatever"}),
               _frame(_req(1, "ping")))
    assert [m["id"] for m in out] == [1]


def test_extra_argument_is_refused_not_ignored(cat):
    (r,) = _run(cat, _frame(_call(1, "fullseye_search_ops", query="gauss", evil=1)))
    assert r["error"]["code"] == -32602
    assert "知らない引数" in r["error"]["message"] and "evil" in r["error"]["message"]


@pytest.mark.parametrize("bad, why", [
    ({"limit": MAX_SEARCH_LIMIT + 1}, "以下"),
    ({"limit": 0}, "以上"),
    ({"limit": "5"}, "整数"),
    ({"limit": True}, "整数"),          # bool は int のサブクラス。素通りさせない
    ({"query": 5}, "文字列"),
    ({"query": "x" * 201}, "文字以下"),
    ({"source": "wheel"}, "どれか"),
    ({"in_sort": "banana"}, "知らない種別"),
])
def test_bad_search_arguments_are_refused_with_the_right_reason(cat, bad, why):
    (r,) = _run(cat, _frame(_call(1, "fullseye_search_ops", **bad)))
    assert r["error"]["code"] == -32602, r
    assert why in r["error"]["message"], "落ちたが理由が違う: %s" % r["error"]["message"]


def test_missing_required_argument_is_refused(cat):
    (r,) = _run(cat, _frame(_call(1, "fullseye_op_help")))
    assert r["error"]["code"] == -32602 and "必須" in r["error"]["message"]


def test_unknown_op_name_is_a_tool_error_with_nearest_candidates(cat):
    (r,) = _run(cat, _frame(_call(1, "fullseye_op_help", name="gaussy")))
    res = r["result"]
    assert res["isError"] is True
    text = res["content"][0]["text"]
    assert "gaussy" in text and "近い名前" in text
    assert "gaussian" in text, "近い名前に gaussian が出ていない: %s" % text


def test_every_declared_tool_has_a_body(cat):
    """TOOLS に足して本体を忘れると『未実装の tool』で落ちる。それを先に潰す。

    画像系 3 tool は順に依存する(samples → load → apply → inspect)ので、
    1 つの store を通して**実際の返り値から次の引数を作る**。"""
    from fullseye.mcp.handles import HandleStore
    store = HandleStore()
    order = ["fullseye_search_ops", "fullseye_op_help", "fullseye_catalog_coverage",
             "fullseye_list_samples", "fullseye_load_image", "fullseye_apply", "fullseye_inspect",
             "fullseye_pipeline"]
    assert set(order) == set(TOOLS), "tool を足したらこの表にも足すこと: %s" % (set(TOOLS) ^ set(order))
    ctx: dict = {}
    for n in order:
        if n == "fullseye_search_ops":
            a = {"query": "gauss"}
        elif n == "fullseye_op_help":
            a = {"name": "gaussian"}
        elif n == "fullseye_load_image":
            a = {"path": ctx["sample_path"], "vision": "none"}
        elif n == "fullseye_apply":
            a = {"handle": ctx["handle"], "op": "gaussian", "vision": "none"}
        elif n == "fullseye_inspect":
            a = {"handle": ctx["handle_out"], "vision": "none"}
        elif n == "fullseye_pipeline":
            a = {"handle": ctx["handle"], "stages": [{"op": "gaussian"}, {"op": "otsu"}], "vision": "none"}
        else:
            a = {}
        res = call_tool(n, a, cat, store)
        assert res["isError"] is False, (n, res["content"][0]["text"][:300])
        sc = res.get("structuredContent", {})
        if n == "fullseye_list_samples":
            ctx["sample_path"] = sc["samples"][0]["path"]
        elif n == "fullseye_load_image":
            ctx["handle"] = sc["handle"]
        elif n == "fullseye_apply":
            ctx["handle_out"] = sc["handle"]


# --------------------------------------------------------------------------- #
# 3. 返った ≠ 中身がある                                                        #
# --------------------------------------------------------------------------- #
def test_search_hit_carries_its_provenance(cat):
    r = call_tool("fullseye_search_ops", {"query": "gaussian", "limit": 5}, cat)["structuredContent"]
    top = r["ops"][0]
    assert top["name"] == "gaussian"
    assert {"index", "registry", "note"} <= set(top["sources"]), top
    assert top["in_sort"] == "image" and top["out_sort"] == "image"
    assert r["by_sources"] and sum(r["by_sources"].values()) == r["total"]


def test_search_finds_a_facade_only_function_the_index_does_not_know(cat):
    """★索引だけ見る検索なら**構造的に出てこない** op。4 層にした理由そのもの。

    最初の被験者は `vol_boundary`(facade + note、索引に無い)だった。2026-09-15 に
    索引が台帳 33 族を数えるようになり、**ノートを持つ名前は全部索引に入った**
    (facade+note だけの名前は 0)。残る「索引に無い facade」は 448 で、ノートも無い
    純粋な facade 関数 —— `census_transform`(ステレオの前処理)をここの被験者にする。
    """
    r = call_tool("fullseye_search_ops", {"query": "census_transform", "limit": 10}, cat)["structuredContent"]
    names = {o["name"]: o for o in r["ops"]}
    assert "census_transform" in names, r["ops"]
    o = names["census_transform"]
    assert "facade" in o["sources"], o
    assert "index" not in o["sources"], "索引に入ったなら、この検査は別の facade-only op に移すこと"
    # ★以前の被験者は台帳経由で索引に入ったこと(= 索引が台帳を数えている)も見る
    r2 = call_tool("fullseye_search_ops", {"query": "vol_boundary", "limit": 5}, cat)["structuredContent"]
    v = {o["name"]: o for o in r2["ops"]}["vol_boundary"]
    assert {"index", "ledger", "note"} <= set(v["sources"]), v


def test_search_can_be_narrowed_to_one_layer(cat):
    r = call_tool("fullseye_search_ops", {"query": "", "source": "facade", "limit": 100}, cat)["structuredContent"]
    assert r["total"] > 100
    assert all("facade" in o["sources"] for o in r["ops"])


def test_search_finds_a_ledger_only_op_by_its_unprefixed_name(cat):
    """`bundle_adjust` は台帳名。レジストリでは `tb_bundle_adjust`。**台帳名で検索して
    出てくる**ことが 5 層目の存在証明。"""
    r = call_tool("fullseye_search_ops", {"query": "bundle_adjust", "limit": 10}, cat)["structuredContent"]
    names = {o["name"]: o for o in r["ops"]}
    assert "bundle_adjust" in names, [o["name"] for o in r["ops"]]
    assert "ledger" in names["bundle_adjust"]["sources"], names["bundle_adjust"]
    assert "note" in names["bundle_adjust"]["sources"]


def test_op_help_returns_a_real_note_with_figures(cat):
    res = call_tool("fullseye_op_help", {"name": "gaussian"}, cat)
    h = res["structuredContent"]
    text = res["content"][0]["text"]
    assert h["found"] and h["body_format"] == "markdown"
    assert h["body_source"].startswith("docs/ops/")
    assert h["frontmatter"]["op"] == "gaussian" and h["frontmatter"]["halcon"] == "gauss_filter"
    assert h["body_chars"] > 500
    assert "## 使い方" in text and "gauss_filter" in text
    # ★2026-09-17 に ``b`` は「未使用」から**端の扱いを選ぶつまみ**になった。
    #   ノートがその意味と**歴史側の帯**を両方書いていることを固定する ——
    #   どちらか片方だけだと、保存済みプログラムを読む人が挙動を誤解する。
    assert "端の扱い" in text, "b が何を選ぶのかがノートから消えた"
    assert "b <= 0.5" in text or "b`` <= 0.5" in text, (
        "歴史的な挙動がどの帯にあるかがノートから消えた")
    assert sum(m in text for m in ("reflect", "nearest", "constant", "wrap")) >= 3, (
        "選択肢の名前がノートに出ていない")
    kinds = {f["kind"] for f in h["figures"]}
    assert {".png", ".a.jpg"} <= kinds, kinds
    links = [c for c in res["content"] if c["type"] == "resource_link"]
    assert len(links) == len(h["figures"])
    assert {lk["mimeType"] for lk in links} <= {"image/png", "image/jpeg", "image/gif"}


def test_op_help_is_not_vacuous_across_a_sample_of_indexed_ops(cat):
    """25 op で本文が空・極端に短い・op 名を含まない、が 1 つも無いこと。"""
    import random
    names = sorted(e.name for e in cat.entries.values() if "index" in e.sources)
    rng = random.Random(20260915)
    thin = []
    for n in rng.sample(names, 25):
        h = cat.help(n)
        if not h["found"] or h["body_chars"] < 200 or n not in (h["body"] or ""):
            thin.append((n, h.get("body_chars"), h.get("body_source")))
    assert not thin, "中身の薄いノート: %s" % thin


def test_structured_content_over_the_cap_is_dropped_and_said_so(cat):
    res = call_tool("fullseye_search_ops", {"query": "", "limit": 100}, cat, max_structured_bytes=64)
    assert "structuredContent" not in res
    assert "上限" in res["content"][0]["text"] and "落とした" in res["content"][0]["text"]
    assert res["_meta"]["fullseye"]["structured_dropped"] is True
    assert res["_meta"]["fullseye"]["bytes"] > 64


def test_coverage_reports_all_five_layers_and_there_are_no_orphan_notes(cat):
    c = call_tool("fullseye_catalog_coverage", {}, cat)["structuredContent"]
    assert set(c["per_source"]) == {"index", "registry", "ledger", "note", "facade"}
    assert all(v > 0 for v in c["per_source"].values()), c["per_source"]
    # 2026-09-15 実測: 索引の全 op にノートがある。減ったら知識層の穴。
    assert c["index_without_note"] == [], c["index_without_note"][:20]
    # ★同日実測: 4 層で 480 枚が「どこにも無いノート」に見えたが、5 層目(ledger)で
    #   480 / 480 が解決した。ここが 0 でなくなったら、まず**引き忘れた層**を疑うこと
    #   ([[feedback_search_all_tiers_before_declaring_a_gap]])。ノートの残骸と決めつけない。
    assert c["note_only"] == 0, "呼べる層のどこにも無いノート: %s" % c["note_only_names"][:20]
    assert len(c["note_only_names"]) == c["note_only"]


def test_tools_list_declares_closed_schemas(cat):
    (r,) = _run(cat, _frame(_req(1, "tools/list")))
    for t in r["result"]["tools"]:
        assert t["inputSchema"]["additionalProperties"] is False, t["name"]
        assert t["description"].strip()


def test_missing_index_refuses_to_build_a_catalog_instead_of_returning_an_empty_one(monkeypatch):
    """索引が**どこにも**無ければ止まる。0.1.11 の wheel は docs/ を持たずこの例外で止まった
    (黙って空のカタログ = 検索が『該当なし』を正直に見せかける、にはならない)。
    0.2.0 で索引はパッケージ内にも入ったので、両方を消して同じ経路が残っていることを見る。"""
    import fullseye.mcp.catalog as C
    from fullseye.mcp import CatalogError
    monkeypatch.setattr(C, "_packaged", lambda name: None)
    monkeypatch.setattr(C, "OP_INDEX", os.path.join(ROOT, "docs", "__no_such_index__.json"))
    with pytest.raises(CatalogError) as ei:
        C.Catalog.load(with_facade=False)
    assert "OP_INDEX.json が無い" in str(ei.value)
    assert "空のカタログ" in str(ei.value), "拒否はしたが、なぜ拒否するのかを言っていない"


def test_missing_notes_refuse_to_build_a_catalog(monkeypatch):
    """索引があってもノート層がどこにも無ければ止まる —— 黙って note=0 で動くと、被覆 tool が
    「索引の全 op にノートが無い」という嘘を正直に見せかける。"""
    import fullseye.mcp.catalog as C
    from fullseye.mcp import CatalogError
    monkeypatch.setattr(C, "_packaged", lambda name: None)
    monkeypatch.setattr(C, "OPS_DOCS", os.path.join(ROOT, "docs", "__no_such_ops__"))
    with pytest.raises(CatalogError) as ei:
        C.Catalog.load(with_facade=False)
    assert "ノートが無い" in str(ei.value)


def test_the_catalog_says_where_it_read_the_index_and_the_notes_from(cat):
    """checkout では索引はパッケージ内の複製、ノートは docs/ops の正本(本文つき)。"""
    assert cat.index_source.startswith("package:") and cat.index_source.endswith("OP_INDEX.json")
    assert cat.notes_source.startswith("docs:")
    c = call_tool("fullseye_catalog_coverage", {}, cat)["structuredContent"]
    assert c["index_source"] == cat.index_source and c["notes_source"] == cat.notes_source


def test_the_packaged_catalog_data_equals_the_docs_it_was_copied_from():
    """★wheel が読む複製(fullseye/data/)が正本(docs/)と一致していること。

    2 か所に同じものを持つ以上、ずれは必ず起きる。`tools/regen_all.py --check` が CI で
    回すが、テストでも数える —— **中身の件数まで**(一致の門は空を通す)。"""
    import fullseye.mcp.catalog as C
    pkg_idx = json.load(open(os.path.join(ROOT, "fullseye", "data", C.PKG_INDEX), encoding="utf-8"))
    doc_idx = json.load(open(os.path.join(ROOT, "docs", "OP_INDEX.json"), encoding="utf-8"))
    assert pkg_idx == doc_idx, "fullseye/data/OP_INDEX.json が docs/OP_INDEX.json と違う —— `py -3.11 tools/gen_mcp_data.py`"
    assert pkg_idx["n_ops"] == len(pkg_idx["ops"]) > 1900
    pkg_notes = json.load(open(os.path.join(ROOT, "fullseye", "data", C.PKG_NOTES), encoding="utf-8"))
    fresh = C.scan_notes(C.OPS_DOCS)
    assert pkg_notes["notes"] == fresh, "fullseye/data/OP_NOTES.json が docs/ops と違う —— `py -3.11 tools/gen_mcp_data.py`"
    assert pkg_notes["n_ops"] == len(fresh) > 1900
    assert pkg_notes["n_notes"] == sum(len(v) for v in fresh.values()) >= pkg_notes["n_ops"]
    # MCP が読む項目だけが入っていること(本文・examples・author は入れない)
    for metas in list(fresh.values())[:200]:
        for m in metas:
            assert set(m) <= set(C.NOTE_KEYS) | {"path"}, m
            assert m["path"].startswith("docs/ops/") and not os.path.isabs(m["path"]), m
    # 索引の全 op が複製側のノートでも引けること(wheel でも index_without_note == [])
    missing = sorted(o["name"] for o in pkg_idx["ops"] if o["name"] not in pkg_notes["notes"])
    assert not missing, missing[:10]


def test_help_falls_back_to_the_shipped_html_when_the_note_body_is_absent(cat, monkeypatch):
    """wheel ではノート本文が無い。同梱 HTML に落ち、**落ちたことと本文の在り処**を書くこと
    (2-D op は op_help/ 直下、台帳族は op_help/<dim>/)。"""
    import fullseye.mcp.catalog as C
    for name, where in (("gaussian", "studio_assets/op_help/gaussian.html"),
                        ("abcd_matrix", "studio_assets/op_help/optics/abcd_matrix.html")):
        e = cat.entries[name]
        monkeypatch.setattr(e, "note_paths", [])
        h = cat.help(name)
        assert h["found"] and h["body_format"] == "html", h.get("body_source")
        assert h["body_source"] == where
        assert h["body_chars"] > 500
        assert h["has_note"] is True and h["note_refs"][0].startswith("docs/ops/")
        assert "note_body_unavailable" in h
    # 図: docs/ops/_fig が無い環境では同梱の Studio 図に落ちる
    monkeypatch.setattr(C, "FIG_DIR", os.path.join(ROOT, "docs", "__no_fig__"))
    h = cat.help("gaussian")
    assert h["figures"] and h["figures"][0]["source"] == "studio_assets/op_help/fig", h["figures"]


# --------------------------------------------------------------------------- #
# 4. 検証器そのものを壊して確かめる                                              #
# --------------------------------------------------------------------------- #
def test_the_validator_actually_checks_each_rule():
    from fullseye.mcp.server import _validate
    # 1 ケースにつき**破る規則は 1 つだけ**にする。最初 `"bbb"` で enum と maxLength を
    # 同時に破り、先に当たった enum の表明で落ちて「maxLength が効いた」と読めなかった。
    s = {"type": "object", "properties": {"n": {"type": "integer", "minimum": 1, "maximum": 3},
                                          "s": {"type": "string", "enum": ["a", "bb"]},
                                          "t": {"type": "string", "maxLength": 2}},
         "required": ["n"], "additionalProperties": False}
    assert _validate(s, {"n": 2, "s": "a", "t": "xy"}) == {"n": 2, "s": "a", "t": "xy"}
    for bad, why in [({}, "必須"), ({"n": 0}, "以上"), ({"n": 4}, "以下"), ({"n": "2"}, "整数"),
                     ({"n": True}, "整数"), ({"n": 2, "s": "c"}, "どれか"),
                     ({"n": 2, "t": "xyz"}, "文字以下"), ({"n": 2, "z": 1}, "知らない引数"),
                     ([], "オブジェクト")]:
        with pytest.raises(ArgError) as ei:
            _validate(s, bad)
        assert why in str(ei.value), (bad, str(ei.value))
