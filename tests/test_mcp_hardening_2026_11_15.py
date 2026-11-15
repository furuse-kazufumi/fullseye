# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PR #318 の外部レビュー(Codex、2026-11-15)の安全の指摘の回帰試験。

Codex の環境では Python が走らず、指摘は全部が静的な読みだった。ここに置くのは、動く再現で本物と確かめた物だけ
(各試験の docstring の「直す前」が、その再現で見た事)。

1. Content-Length 枠: 本文の大きさとヘッダの上限が無かった。``Content-Length: 10000000000000`` の 1 通(35 バイト)で
   ``read(10**13)`` が先に確保しようとして MemoryError になり、サーバが落ちた。重複した Content-Length は後の方が勝った。
2. 作業プロセス: 親の ``sys.path`` を全部受け継いだ。``python -m fullseye.mcp`` は cwd を ``sys.path[0]`` に置くので、
   起動したフォルダ(信頼しない repo など)の ``scipy.py`` が、囲いを掛ける前に作業プロセスで import された。
   親も起動の時に cwd の ``opsoptics.py`` / ``scipy.py`` を import した(同じ根の兄弟)。
3. 作業プロセスの出力の上限: 配列しか数えず、文字列・数の list は素通りした。見張りは結果を JSON にする前に止まり、
   親は子の返事の 1 行を長さの上限なしに読んだ。
4. JSON の入口: NaN / Infinity と重複した鍵を受け、id が NaN の要求に JSON でない返事(``"id": NaN``)を書いた。
5. 追い出しの履歴・追い出したハンドルの小図・viewer の HTML が、上限なしに増えた。
6. (試験の穴)上の 1〜5 を見る試験が無かった。
疑い 1. ``.npy`` は画素数(``shape[:2]``)しか見ず、``(1, 1, N)`` の配列を全部復号してから断った。
疑い 2. ハンドルの名前(sha256 の先頭 64 bit)が同じなら、中身を比べずに前の値を返した。
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import queue
import re
import subprocess
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (ROOT, os.path.dirname(os.path.abspath(__file__))):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fullseye.mcp import handles as H                              # noqa: E402
from fullseye.mcp import opworker as W                             # noqa: E402
from fullseye.mcp import server as S                               # noqa: E402
from fullseye.mcp.catalog import Catalog                           # noqa: E402
from fullseye.mcp.handles import HandleError, HandleStore          # noqa: E402
from fullseye.mcp.opworker import OpWorker, OpWorkerError, close_worker  # noqa: E402

FIXTURE = {"ledger_module": "mcp_worker_fixture_ledger", "ledger_table": "TABLE", "data_names": []}
PING = {"jsonrpc": "2.0", "id": 99, "method": "ping"}
GIB = 1 << 30


@pytest.fixture(scope="module")
def cat():
    return Catalog.load()


@pytest.fixture()
def store(tmp_path):
    return HandleStore(roots=[], thumb_dir=str(tmp_path / "thumb"))


@pytest.fixture(scope="module")
def worker():
    w = OpWorker()
    yield w
    w.close()


@pytest.fixture(scope="module", autouse=True)
def _close_shared_worker():
    yield
    close_worker()


def _frame(obj) -> bytes:
    body = json.dumps(obj).encode("utf-8")
    return b"Content-Length: %d\r\n\r\n" % len(body) + body


def _stream(raw: bytes) -> io.BufferedReader:
    """標準入力と同じ型(BufferedReader)。``read(n)`` が n バイトを先に確保するのはこの型。"""
    return io.BufferedReader(io.BytesIO(raw))


def _strict(raw: bytes):
    """厳密な JSON として読む(NaN / Infinity のトークンは断る)。"""
    def bad(token):
        raise ValueError("not JSON: %s" % token)
    return json.loads(raw, parse_constant=bad)


def _bodies(out: bytes) -> list[bytes]:
    """サーバの出力を 1 通ずつの本文に分ける(読み手はサーバの read_framed を使わない —— 試す物で試さない)。"""
    bodies, pos = [], 0
    while pos < len(out):
        m = re.compile(rb"Content-Length: (\d+)\r\n\r\n").match(out, pos)
        if m:
            end = m.end() + int(m.group(1))
            bodies.append(out[m.end():end])
            pos = end
            continue
        nl = out.find(b"\n", pos)
        nl = len(out) if nl < 0 else nl
        if out[pos:nl].strip():
            bodies.append(out[pos:nl])
        pos = nl + 1
    return bodies


def _serve(raw: bytes, cat, store) -> list:
    out = io.BytesIO()
    assert S.run_stdio_server(_stream(raw), out, catalog=cat, store=store) == 0
    return [_strict(b) for b in _bodies(out.getvalue())]


# --------------------------------------------------------------------------- 1: Content-Length 枠の上限
def test_a_huge_content_length_is_refused_and_the_server_keeps_answering(cat, store):
    """直す前: 35 バイトの 1 通で MemoryError になり、サーバが落ちた(次の ping に返事が無い)。"""
    replies = _serve(b"Content-Length: 10000000000000\r\n\r\n" + _frame(PING), cat, store)
    assert replies[0]["id"] is None and replies[0]["error"]["code"] == -32700, replies
    assert "Content-Length" in replies[0]["error"]["message"]
    assert replies[-1] == {"jsonrpc": "2.0", "id": 99, "result": {}}


def test_a_content_length_body_above_the_frame_limit_is_refused_unread(monkeypatch):
    """直す前: 改行区切りの 1 行には上限(64 MiB)があったが、Content-Length の本文は正の数かしか見なかった。"""
    monkeypatch.setattr(S, "MAX_LINE_BYTES", 1000)
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping", "pad": "x" * 1000}).encode()
    stream = _stream(b"Content-Length: %d\r\n\r\n" % len(body) + body)
    with pytest.raises(S.FramingError, match="1000"):
        S.read_framed(stream)
    assert stream.read(1) == b"{"                                   # 本文は読まずに断った
    with pytest.raises(S.FramingError):                              # 改行区切りも同じ上限
        S.read_framed(_stream(body + b"\n"))
    small = json.dumps(PING).encode()                                # 上限の内は今まで通り
    assert S.read_framed(_stream(b"Content-Length: %d\r\n\r\n" % len(small) + small)) == (PING, S.FRAMING_HEADERS)


@pytest.mark.parametrize("head", [
    b"".join(b"X-Pad-%d: v\r\n" % i for i in range(100)),          # 行が多すぎる
    b"X-Pad: " + b"v" * 20_000 + b"\r\n",                            # 1 行が長すぎる(総量も超える)
], ids=["100-lines", "20-kB-line"])
def test_the_header_block_has_a_line_and_byte_limit(head):
    """直す前: ヘッダの行の数とバイトの総量に上限が無く、別々の名前を送り続けると表が増え続けた。"""
    body = json.dumps(PING).encode()
    with pytest.raises(S.FramingError, match="見出し"):
        S.read_framed(_stream(head + b"Content-Length: %d\r\n\r\n" % len(body) + body))


@pytest.mark.parametrize("head", [
    b"Content-Length: 2\r\nContent-Length: 2\r\n",                  # 重複(同じ値でも断る)
    b"Content-Length: 9\r\ncontent-length: 2\r\n",                  # 大文字小文字だけ違う重複(直す前は後の 2 が勝った)
    b"Content-Length: 0_2\r\n",                                       # int() は _ を受ける
    b"Content-Length: +2\r\n",                                        # int() は + を受ける
    b"Content-Length: 2\r\nnot a header\r\n",                        # 名前: 値 の形でない行(直す前は黙って飛ばした)
], ids=["dup", "dup-case", "underscore", "plus", "no-colon"])
def test_duplicated_or_malformed_headers_are_refused(head):
    with pytest.raises(S.FramingError):
        S.read_framed(_stream(head + b"\r\n{}"))


def test_after_a_refused_header_block_the_server_keeps_answering(cat, store):
    """壊れたヘッダの塊は空行まで読み捨ててから断る(1 通に 1 つの -32700)。後の要求には今まで通り返す。"""
    raw = b"Content-Length: 2\r\nContent-Length: 2\r\n\r\n" + _frame(PING)
    replies = _serve(raw, cat, store)
    assert [r.get("error", {}).get("code") for r in replies] == [-32700, None], replies
    assert replies[-1]["id"] == 99


def test_normal_frames_still_read_with_a_content_type_header():
    """後方互換の設計の試験(直す前も通る): Content-Type の付いた枠・空行を挟んだ改行区切りは今まで通り読む。"""
    body = json.dumps(PING).encode()
    raw = b"Content-Length: %d\r\nContent-Type: application/vscode-jsonrpc; charset=utf-8\r\n\r\n" % len(body) + body
    assert S.read_framed(_stream(raw)) == (PING, S.FRAMING_HEADERS)
    assert S.read_framed(_stream(b"\r\n\n" + body + b"\n")) == (PING, S.FRAMING_LINES)


# --------------------------------------------------------------------------- 4: JSON の入口は厳密に
@pytest.mark.parametrize("raw", [
    b'{"jsonrpc":"2.0","id":NaN,"method":"ping"}',
    b'{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"x","arguments":{"a":Infinity}}}',
    b'{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"x","arguments":{"a":[-Infinity]}}}',
    b'{"jsonrpc":"2.0","id":1,"method":"ping","method":"tools/list"}',
    b'{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"a","arguments":{},"name":"b"}}',
], ids=["nan-id", "infinity", "minus-infinity", "dup-key", "dup-nested-key"])
def test_non_json_numbers_and_duplicate_keys_are_parse_errors(raw):
    """直す前: json.loads の既定は NaN / Infinity を受け、重複した鍵は後の方を取った(中継と解釈が割れる)。"""
    for framed in (raw + b"\n", b"Content-Length: %d\r\n\r\n" % len(raw) + raw):
        with pytest.raises(S.FramingError):
            S.read_framed(_stream(framed))


def test_a_nan_id_never_produces_a_non_json_reply(cat, store):
    """直す前: id が NaN の要求に ``{"id": NaN, ...}`` を書いた(書き出しの最後の網が allow_nan の既定のまま)。"""
    out = io.BytesIO()
    S.run_stdio_server(_stream(b'{"jsonrpc":"2.0","id":NaN,"method":"ping"}\n' + json.dumps(PING).encode() + b"\n"),
                       out, catalog=cat, store=store)
    replies = [_strict(b) for b in _bodies(out.getvalue())]           # どの 1 通も厳密な JSON
    assert replies[0]["id"] is None and replies[0]["error"]["code"] == -32700
    assert replies[-1] == {"jsonrpc": "2.0", "id": 99, "result": {}}


def test_a_parse_error_is_answered_in_the_framing_the_client_used(cat, store):
    """直す前: 最初の 1 通が読めない時、-32700 を Content-Length 枠で返した(枠が決まるのは読めた 1 通から)。
    改行区切りの公式のクライアントはその返事を読めない。NaN・重複した鍵を断るようにしたので、起き得る場面が増えた。"""
    out = io.BytesIO()
    S.run_stdio_server(_stream(b'{"jsonrpc": "2.0", "id": 1, "method": \n' + json.dumps(PING).encode() + b"\n"),
                       out, catalog=cat, store=store)
    first, second = out.getvalue().split(b"\n")[:2]
    assert _strict(first)["error"]["code"] == -32700 and _strict(second)["id"] == 99
    body = b'{"jsonrpc": "2.0", "id": 1, "method": '
    out = io.BytesIO()
    S.run_stdio_server(_stream(b"Content-Length: %d\r\n\r\n" % len(body) + body), out, catalog=cat, store=store)
    assert out.getvalue().startswith(b"Content-Length: ")                # Content-Length 枠の相手には同じ枠で


def test_write_message_never_writes_nan_even_in_its_fallback():
    for framing in (S.FRAMING_LINES, S.FRAMING_HEADERS):
        out = io.BytesIO()
        S.write_message(out, {"jsonrpc": "2.0", "id": float("nan"), "result": {"v": float("inf")}}, framing=framing)
        (body,) = _bodies(out.getvalue())
        reply = _strict(body)
        assert reply["id"] is None and reply["error"]["code"] == -32603


@pytest.mark.parametrize("bad_id", [{"x": 1}, [1], True, False], ids=["object", "array", "true", "false"])
def test_a_request_id_must_be_a_string_a_number_or_null(bad_id):
    """直す前: 配列や辞書の id をそのまま返した(JSON-RPC 2.0 の id は文字列・数・null だけ)。"""
    reply = S.dispatch({"jsonrpc": "2.0", "id": bad_id, "method": "ping"}, None, None)
    assert reply["id"] is None and reply["error"]["code"] == -32600, reply
    for good in ("a", 1, 1.5, 0, None):
        assert S.dispatch({"jsonrpc": "2.0", "id": good, "method": "ping"}, None, None) == {
            "jsonrpc": "2.0", "id": good, "result": {}}


# --------------------------------------------------------------------------- 5: 生成物と履歴の上限
def test_the_eviction_history_is_bounded(tmp_path):
    """直す前: 追い出したハンドルの名前は集合に足し続けた(max_items=4 で 5,000 回入れると 4,996 件)。"""
    st = HandleStore(roots=[], max_items=4, thumb_dir=str(tmp_path / "t"))
    handles = [st.put(np.full((2, 2), float(k)), sort="image", provenance=[])["handle"] for k in range(5000)]
    assert st.stats()["evicted"] <= 1024, st.stats()
    with pytest.raises(HandleError, match="追い出された"):          # 近い過去に追い出した物は、今まで通り理由つき
        st.get(handles[-5])
    with pytest.raises(HandleError):                                  # 古い物も断る(知らないハンドルとして)
        st.get(handles[0])


def test_thumbnails_of_evicted_handles_are_removed(cat, tmp_path, monkeypatch):
    """直す前: 追い出したハンドルの小図(PNG)は残り続けた(20 枚作ると、生きている 4 つ分を超えて 20 枚)。
    見るのはファイルの後始末なので、PNG の符号化(Pillow / OpenCV)は要らない形に差し替える。"""
    import imgio

    def fake_save(path, rgb):
        with open(path, "wb") as fh:
            fh.write(b"thumb %s" % str(np.asarray(rgb).shape).encode())

    monkeypatch.setattr(imgio, "save", fake_save)
    st = HandleStore(roots=[], max_items=4, thumb_dir=str(tmp_path / "t"))
    for k in range(20):
        h = st.put(np.full((32, 32), float(k)), sort="image", provenance=[])["handle"]
        r = S.call_tool("fullseye_inspect", {"handle": h, "vision": "thumb"}, cat, st)
        assert not r["isError"]
    alive = {h[len(H.PREFIX):] for h in st._meta}
    pngs = [f for f in os.listdir(st.thumb_dir) if f.endswith(".png")]
    assert pngs and {f.split(".")[0] for f in pngs} <= alive, (sorted(pngs), sorted(alive))


def _viewer_spec() -> dict:
    import pocviewer as pv
    tx = {"ja": "t"}
    return json.loads(json.dumps(pv.viewer_spec(
        "q", tx, tx, tx, [pv.viewer_points_tab("a", tx, "passed", tx, [[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]],
                                               val=[0.0, 1.0], cbar={"lo": 0, "hi": 1})]),
        default=lambda o: o.tolist()))


def test_viewer_files_have_a_count_and_byte_quota(cat, tmp_path):
    """直す前: fullseye_write_viewer は名前を変えれば何枚でも書けた(200 枚・11.8 MB が残った)。"""
    st = HandleStore(roots=[], thumb_dir=str(tmp_path / "t"))
    spec = _viewer_spec()
    paths = [S.call_tool("fullseye_write_viewer", {"spec": spec, "name": "v%03d" % k}, cat, st)
             ["structuredContent"]["path"] for k in range(70)]
    htmls = [f for f in os.listdir(st.thumb_dir) if f.endswith(".html")]
    assert len(htmls) <= 64 and os.path.exists(paths[-1]) and not os.path.exists(paths[0]), len(htmls)
    total = sum(os.path.getsize(os.path.join(st.thumb_dir, f)) for f in htmls)
    assert total <= st.max_viewer_bytes
    again = S.call_tool("fullseye_write_viewer", {"spec": spec, "name": "v069"}, cat, st)  # 同じ名前は書き換え
    assert again["structuredContent"]["path"] == paths[-1] and len(os.listdir(st.thumb_dir)) == len(htmls)
    st.max_viewer_bytes = 1000                                         # 1 枚で枠を超える物は書かずに断る
    with pytest.raises(S.ArgError, match="1000"):
        S.call_tool("fullseye_write_viewer", {"spec": spec, "name": "too_big"}, cat, st)
    assert not os.path.exists(os.path.join(st.thumb_dir, "too_big.html"))


# --------------------------------------------------------------------------- 2: 作業プロセスの import
def test_worker_does_not_import_a_ledger_module_planted_on_sys_path(tmp_path, monkeypatch):
    """直す前: 作業プロセスは親の sys.path を全部受け継ぎ、確かめていない場所にある同じ名前のモジュールを、囲いを
    掛ける前に import した(そのモジュールの最上位のコードが作業フォルダの外へ書けた)。"""
    planted = tmp_path / "untrusted"
    planted.mkdir()
    marker = tmp_path / "marker.txt"
    (planted / "mcp_worker_fixture_ledger.py").write_text(
        "with open(%r, 'w') as fh:\n    fh.write('planted')\nTABLE = {}\n" % str(marker), encoding="utf-8")
    monkeypatch.setattr(sys, "path", [str(planted)] + sys.path)
    w = OpWorker()
    try:
        value, _info = w.run(dict(FIXTURE, key="table"), [], {}, time_limit_s=60, max_rss=GIB)
    finally:
        w.close()
    assert not marker.exists(), "the planted module ran in the worker"
    assert value["height_mm"] == 6.0                                  # 本物の台帳(tests/ の下)が走った


def test_worker_runs_in_isolated_mode_with_only_trusted_paths(tmp_path, monkeypatch):
    """直す前: 子は ``-I`` 無しで起動し(PYTHONPATH・ユーザの site を読む)、sys.path に親の cwd などが入った。"""
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.setattr(sys, "path", [str(elsewhere)] + sys.path)
    monkeypatch.setenv("PYTHONPATH", str(elsewhere))
    w = OpWorker()
    try:
        value, _info = w.run(dict(FIXTURE, key="interpreter"), [], {}, time_limit_s=60, max_rss=GIB)
    finally:
        w.close()
    assert value["isolated"] == 1
    scratch = os.path.realpath(value["cwd"])
    roots = [r for r in W._read_roots(scratch) if r != scratch]
    outside = [p for p in value["path"] if not any(
        os.path.realpath(p) == r or os.path.realpath(p).startswith(r + os.sep) for r in roots)]
    assert not outside, outside


@pytest.mark.parametrize("module", ["json", "fullseye.mcp.server", "../mcp_worker_fixture_ledger"])
def test_worker_refuses_a_ledger_module_that_is_not_from_the_fullseye_tree(worker, module):
    """直す前: 実行先の名前をそのまま import した(標準ライブラリの json でも、点の付いた名前でも)。出どころ
    (``spec.origin``)が fullseye の置き場所の中の、点の無い名前のモジュールだけを読む。"""
    with pytest.raises(OpWorkerError) as err:
        worker.run({"ledger_module": module, "ledger_table": "TABLE", "key": "table", "data_names": []}, [], {},
                   time_limit_s=60, max_rss=GIB)
    assert err.value.reason == "unsupported_value", (err.value.reason, str(err.value))
    assert "ledger module" in str(err.value) and os.sep + "json" not in str(err.value)   # ホストのパスは出さない


def test_the_server_started_with_python_m_imports_nothing_from_its_cwd(tmp_path):
    """直す前: ``python -m fullseye.mcp`` は cwd を sys.path[0] に置き、起動の時に cwd の ``opsoptics.py`` と
    ``scipy.py`` を親が import した(作業プロセスも scipy を)。MCP のクライアントはサーバをプロジェクトのフォルダで
    起動するので、そこに置かれた同じ名前のファイルが本物より先に走った。"""
    planted = tmp_path / "project"
    planted.mkdir()
    marker = tmp_path / "marker.txt"
    code = ("import sys\nwith open(%r, 'a', encoding='utf-8') as fh:\n"
            "    fh.write(__name__ + ' ' + repr(sys.argv[:1]) + chr(10))\n"
            "raise ImportError('planted')\n" % str(marker))
    for name in ("opsoptics", "scipy"):
        (planted / (name + ".py")).write_text(code, encoding="utf-8")
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8", PYTHONPATH=ROOT)
    msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                        "clientInfo": {"name": "cwd-test", "version": "0"}}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
             "params": {"name": "fullseye_apply", "arguments": {"op": "abbe_number", "params": {"material": "N-SF11"}}}}]
    r = subprocess.run([sys.executable, "-m", "fullseye.mcp"], cwd=str(planted), env=env, timeout=600,
                       input=b"".join(json.dumps(m).encode() + b"\n" for m in msgs), capture_output=True)
    imported = marker.read_text(encoding="utf-8") if marker.exists() else ""
    assert not imported, imported
    replies = {x["id"]: x for x in (_strict(b) for b in _bodies(r.stdout))}
    assert replies[2]["result"]["isError"] is False, r.stderr.decode("utf-8", "replace")[-800:]


# --------------------------------------------------------------------------- 3: 作業プロセスの出力の上限
def test_result_limit_counts_strings_numbers_and_containers():
    """直す前: 数えるのは配列の要素とバイトだけで、文字列・数・dict / list は 0 と数えた。"""
    assert W._result_limit_error({"s": "x" * 2000}, {"max_result_bytes": 1000})
    assert W._result_limit_error({"rows": [1.0] * 2000}, {"max_elements": 1000})
    assert W._result_limit_error({"rows": [1.0] * 2000}, {"max_result_bytes": 1000})
    shared = [{}] * 600                                                # 同じ物の 2 回目も、送る時は 2 回書く
    assert W._result_limit_error([shared, shared], {"max_elements": 1000})
    assert W._result_limit_error({"s": "x" * 10, "image": np.zeros((5, 5))},
                                 {"max_result_bytes": 1000, "max_elements": 1000}) is None


@pytest.mark.parametrize("key, kwargs", [("big_string", {"chars": 200_000}), ("float_list", {"count": 50_000})])
def test_worker_output_limit_stops_strings_and_number_lists(worker, key, kwargs):
    """直す前: 200,000 文字の文字列・50,000 個の数の list が、上限 10,000 要素 / 100,000 バイトを素通りした。"""
    limits = dict(FIXTURE, key=key, max_elements=10_000, max_result_bytes=100_000)
    with pytest.raises(OpWorkerError) as err:
        worker.run(limits, [], kwargs, time_limit_s=60, max_rss=GIB)
    assert err.value.reason == "output_limit", (err.value.reason, str(err.value))
    small = {k: 100 for k in kwargs}
    value, _info = worker.run(limits, [], small, time_limit_s=60, max_rss=GIB)   # 上限の内は今まで通り
    assert len(next(iter(value.values()))) == 100


def test_worker_refuses_a_reply_line_above_the_limit(worker):
    """直す前: 子は返事の 1 行の長さを見ずに送り、親も上限なしに読んだ。"""
    with pytest.raises(OpWorkerError) as err:
        worker.run(dict(FIXTURE, key="big_string", max_reply_bytes=10_000), [], {"chars": 50_000},
                   time_limit_s=60, max_rss=GIB)
    assert err.value.reason == "output_limit" and "reply" in str(err.value)


def test_parent_stops_reading_a_reply_line_above_the_limit():
    """親の読み手は 1 行を上限 + 1 バイトまでしか読まない。超えたら印を置いて読むのをやめる(子は捨てる)。"""
    q = queue.Queue()
    W._pump(io.BytesIO(b"x" * 100 + b"\n" + b"ok\n"), q, 50)
    assert q.get_nowait() is W._TOO_LONG and q.get_nowait() is None
    q = queue.Queue()
    W._pump(io.BytesIO(b"ok\n" + b"y" * 50 + b"\n"), q, 50)
    assert [q.get_nowait() for _ in range(3)] == [b"ok\n", b"y" * 50 + b"\n", None]


def test_memory_watchdog_stays_on_while_the_result_is_encoded():
    """直す前: 見張りは op が返った所で止まり、結果を JSON にする間(8 MB の NUL が 48 MB の \\u0000 になる)は上限の
    外だった。上限 24 MiB の増分で、op 自体(8 MB)は通り、JSON にする所で止まる。"""
    w = OpWorker()
    try:
        with pytest.raises(OpWorkerError) as err:
            w.run(dict(FIXTURE, key="nul_string"), [], {"chars": 8_000_000}, time_limit_s=60, max_rss=24 << 20)
    finally:
        w.close()
    assert err.value.reason == "memory_limit", (err.value.reason, str(err.value))


# --------------------------------------------------------------------------- 疑い 1: .npy は全体のバイトを先に見る
def test_npy_is_checked_by_its_total_bytes_and_dtype_before_decoding(tmp_path, monkeypatch):
    """直す前: (1, 1, 200000) の配列は「1 画素」と数え、1.6 MB を全部復号してから置き場の上限 1 MiB で断った。
    数でない dtype(V20000)も全部読んでから断った。"""
    np.save(tmp_path / "tall.npy", np.zeros((1, 1, 200_000)))
    np.save(tmp_path / "void.npy", np.zeros((4, 4), dtype=[("blob", "V20000")]))
    np.save(tmp_path / "ok.npy", np.arange(64.0).reshape(8, 8))
    st = HandleStore(roots=[str(tmp_path)], max_bytes=1 << 20, thumb_dir=str(tmp_path / "t"))
    full_loads = []
    real_load = np.load

    def spy(path, *args, **kwargs):
        if kwargs.get("mmap_mode") is None:
            full_loads.append(os.path.basename(str(path)))
        return real_load(path, *args, **kwargs)

    monkeypatch.setattr(np, "load", spy)
    with pytest.raises(HandleError, match="bytes|バイト"):
        st.load("tall.npy")
    with pytest.raises(HandleError, match="dtype"):
        st.load("void.npy")
    assert full_loads == []
    assert st.load("ok.npy")["shape"] == [8, 8] and full_loads == ["ok.npy"]


# --------------------------------------------------------------------------- 疑い 2: ハンドルの名前の衝突
class _PrefixCollidingSha256:
    """sha256 の先頭 16 桁(ハンドルの名前)だけを 0 にする。残りは本物 —— 名前は衝突し、中身の digest は違う。"""

    def __init__(self, *args):
        self._h = hashlib.sha256(*args)

    def update(self, data):
        self._h.update(data)

    def hexdigest(self):
        return "0" * 16 + self._h.hexdigest()[16:]


class _HashlibWithCollidingNames:
    def __getattr__(self, name):
        return getattr(hashlib, name)

    sha256 = _PrefixCollidingSha256


def test_a_handle_name_collision_is_refused_instead_of_answering_with_the_other_value(tmp_path, monkeypatch):
    """直す前: 名前が同じなら中身を比べずに dedup と答え、後から入れた値の代わりに前の値を返した。"""
    monkeypatch.setattr(H, "hashlib", _HashlibWithCollidingNames())
    st = HandleStore(roots=[], thumb_dir=str(tmp_path / "t"))
    first = st.put(np.zeros((4, 4)), sort="image", provenance=[])
    with pytest.raises(HandleError, match="衝突"):
        st.put(np.ones((4, 4)), sort="image", provenance=[])
    assert np.array_equal(st.get(first["handle"])[1], np.zeros((4, 4)))
    again = st.put(np.zeros((4, 4)), sort="image", provenance=[])     # 同じ中身は今まで通り dedup
    assert again["handle"] == first["handle"] and again["dedup"] is True
