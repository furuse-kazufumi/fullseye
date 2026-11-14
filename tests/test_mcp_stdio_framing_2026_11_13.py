"""MCP の stdio の枠: 改行区切りの JSON(MCP の決まり)と Content-Length 枠の両方に応える(2026-11-13)。

1.1.0 までのサーバは Content-Length 枠しか読まず、公式のクライアント(mcp の Python SDK、Claude Code、
Claude Desktop)の initialize に応えなかった。既存の試験は自前のクライアント(同じ枠)との往復だったので、
この食い違いを見つけられなかった —— ここでは枠を 2 種とも外から与え、公式のクライアントがあればそれでも繋ぐ。
"""
from __future__ import annotations

import io
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from fullseye.mcp import server as S  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

INIT = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                   "clientInfo": {"name": "framing-test", "version": "0"}}}
INITIALIZED = {"jsonrpc": "2.0", "method": "notifications/initialized"}
LIST = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}


def _line(msg) -> bytes:
    return json.dumps(msg).encode("utf-8") + b"\n"


def _framed(msg) -> bytes:
    body = json.dumps(msg).encode("utf-8")
    return b"Content-Length: " + str(len(body)).encode() + b"\r\n\r\n" + body


@pytest.fixture(scope="module")
def catalog():
    return S.Catalog.load()


def _serve(raw: bytes, catalog) -> bytes:
    out = io.BytesIO()
    assert S.run_stdio_server(io.BytesIO(raw), out, catalog=catalog, store=S.HandleStore()) == 0
    return out.getvalue()


def _read_all(raw: bytes) -> list[tuple[object, str]]:
    stream, got = io.BytesIO(raw), []
    while True:
        one = S.read_framed(stream)
        if one is None:
            return got
        got.append(one)


def test_newline_delimited_requests_get_newline_delimited_replies(catalog):
    out = _serve(_line(INIT) + _line(INITIALIZED) + _line(LIST), catalog)
    assert b"Content-Length" not in out
    lines = out.split(b"\n")
    assert lines[-1] == b"" and len(lines) == 3, len(lines)       # 2 通の返事(通知には返さない)+ 末尾の空
    replies = [json.loads(x) for x in lines[:-1]]
    assert [r["id"] for r in replies] == [1, 2]
    assert replies[0]["result"]["serverInfo"]["name"] == "fullseye"
    assert len(replies[1]["result"]["tools"]) >= 10
    assert b"\r" not in out                                       # 1 行 1 通(本文に生の改行が入らない)


def test_content_length_requests_still_get_content_length_replies(catalog):
    out = _serve(_framed(INIT) + _framed(LIST), catalog)
    replies = _read_all(out)
    assert [f for _m, f in replies] == [S.FRAMING_HEADERS, S.FRAMING_HEADERS]
    assert [m["id"] for m, _f in replies] == [1, 2]
    assert out.startswith(b"Content-Length: ")


def test_the_reply_follows_the_framing_of_each_request(catalog):
    out = _serve(_line(INIT) + _framed(LIST) + _line(dict(LIST, id=3)), catalog)
    replies = _read_all(out)
    assert [(m["id"], f) for m, f in replies] == [
        (1, S.FRAMING_LINES), (2, S.FRAMING_HEADERS), (3, S.FRAMING_LINES)]


def test_blank_lines_between_newline_delimited_messages_are_skipped(catalog):
    out = _serve(b"\n" + _line(INIT) + b"\r\n\n" + _line(LIST) + b"\n", catalog)
    replies = _read_all(out)
    assert [m["id"] for m, _f in replies] == [1, 2]


@pytest.mark.parametrize("wrap", [_line, _framed], ids=["lines", "content-length"])
@pytest.mark.parametrize("body", [None, [1, 2], 7, "x"], ids=["null", "array", "number", "string"])
def test_a_body_that_is_not_an_object_is_refused_and_the_server_keeps_running(catalog, wrap, body):
    """本文が null の 1 通で、サーバが EOF と取り違えて黙って終了していた。"""
    if wrap is _line and not isinstance(body, list):
        pytest.skip("改行区切りでは、{ か [ で始まらない行はヘッダとして読まれる(別の試験)")
    replies = _read_all(_serve(wrap(body) + wrap(LIST), catalog))
    assert len(replies) == 2, replies
    assert replies[0][0]["error"]["code"] == -32600
    assert replies[1][0]["id"] == 2 and "tools" in replies[1][0]["result"]


@pytest.mark.parametrize("wrap", [_line, _framed], ids=["lines", "content-length"])
def test_a_deeply_nested_body_is_a_parse_error_not_a_crash(catalog, wrap):
    """3,000 段の入れ子 1 通で RecursionError のままサーバが落ちていた。

    ★2026-11-15: Python 3.14 の json.loads は 10 万段でも RecursionError を出さない(この試験が py3.14 でだけ
    -32602 になった)。サーバは読む前に深さを数えて断るので、どの版でも -32700。"""
    deep = b'{"jsonrpc":"2.0","id":9,"method":"tools/call","params":' + b"[" * 100000 + b"]" * 100000 + b"}"
    raw = (deep + b"\n") if wrap is _line else (b"Content-Length: %d\r\n\r\n" % len(deep) + deep)
    replies = _read_all(_serve(raw + wrap(LIST), catalog))
    assert len(replies) == 2, replies
    assert replies[0][0]["error"]["code"] == -32700
    assert replies[1][0]["id"] == 2


def _nested(depth: int) -> bytes:
    """params が depth 段の配列の 1 通(全体の深さは depth + 1: 外側の辞書の分)。"""
    return b'{"jsonrpc":"2.0","id":9,"method":"tools/list","params":' + b"[" * depth + b"]" * depth + b"}"


def test_the_depth_limit_is_exact_and_does_not_depend_on_the_interpreter(catalog):
    """上限ちょうどの深さは読み、1 段深いと -32700。json.loads の再帰の限界(版で違う)には頼らない。"""
    ok = _nested(S.MAX_JSON_DEPTH - 1)                    # 外側の辞書と合わせて、ちょうど上限
    deep = _nested(S.MAX_JSON_DEPTH)                      # 1 段深い
    assert S.json_depth(ok) == S.MAX_JSON_DEPTH and S.json_depth(deep) == S.MAX_JSON_DEPTH + 1
    assert isinstance(S._loads_body(ok), dict)
    with pytest.raises(S.FramingError):
        S._loads_body(deep)
    replies = _read_all(_serve(deep + b"\n" + ok + b"\n" + _line(LIST), catalog))
    assert len(replies) == 3, replies
    assert replies[0][0]["error"]["code"] == -32700
    assert replies[1][0].get("error", {}).get("code") != -32700       # 上限ちょうどは JSON として読まれる
    assert replies[2][0]["id"] == 2 and "tools" in replies[2][0]["result"]


def test_brackets_inside_strings_do_not_count_as_depth(catalog):
    """文字列の中の括弧(と、逃がした引用符の後ろの括弧)は深さに数えない。"""
    text = "[" * 500 + '\\" {{{{ \\\\' + "{" * 500
    msg = dict(LIST, id=5, params={"note": text, "list": [[1, 2], {"a": [3]}]})
    body = json.dumps(msg).encode("utf-8")
    assert body.count(b"[") + body.count(b"{") > S.MAX_JSON_DEPTH       # 早い道(総数が上限以下)を通らない
    assert S.json_depth(body) == 5                                      # 外の辞書・params・list・その中の辞書・[3]
    assert S._loads_body(body) == msg
    replies = _read_all(_serve(body + b"\n", catalog))
    assert len(replies) == 1 and replies[0][0]["id"] == 5
    assert replies[0][0].get("error", {}).get("code") != -32700         # JSON として読まれた(深すぎるとは言わない)


def test_broken_json_on_a_line_is_a_parse_error_and_the_next_line_is_served(catalog):
    replies = _read_all(_serve(b'{"jsonrpc": "2.0", "id": 1, "method": \n' + _line(LIST), catalog))
    assert [m.get("id") for m, _f in replies] == [None, 2]
    assert replies[0][0]["error"]["code"] == -32700


def test_read_message_keeps_its_contract():
    """従来の入口: EOF は None、null の本文と壊れた本文は FramingError、枠 2 種とも dict を返す。"""
    assert S.read_message(io.BytesIO(b"")) is None
    assert S.read_message(io.BytesIO(_line(LIST))) == LIST
    assert S.read_message(io.BytesIO(_framed(LIST))) == LIST
    with pytest.raises(S.FramingError):
        S.read_message(io.BytesIO(_framed(None)))
    with pytest.raises(S.FramingError):
        S.read_message(io.BytesIO(b"Content-Length: 3\r\n\r\n{]}"))


def test_write_message_never_puts_a_raw_newline_inside_a_line():
    buf = io.BytesIO()
    S.write_message(buf, {"jsonrpc": "2.0", "id": 1, "result": {"text": "a\nb\r\nc d"}}, framing=S.FRAMING_LINES)
    raw = buf.getvalue()
    assert raw.endswith(b"\n") and raw.count(b"\n") == 1 and b"\r" not in raw
    assert json.loads(raw)["result"]["text"] == "a\nb\r\nc d"
    # NaN は改行区切りでも書かない(同じ id の -32603 に置き換わる)
    buf = io.BytesIO()
    S.write_message(buf, {"jsonrpc": "2.0", "id": 5, "result": {"x": float("nan")}}, framing=S.FRAMING_LINES)
    got = json.loads(buf.getvalue())
    assert got["id"] == 5 and got["error"]["code"] == -32603


def test_the_official_mcp_client_can_connect_and_call_a_tool(tmp_path):
    """公式の Python クライアント(改行区切り)で initialize → tools/list → tools/call が通る。"""
    pytest.importorskip("mcp")
    import asyncio

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    env = dict(os.environ, PYTHONUTF8="1", PYTHONPATH=ROOT)
    params = StdioServerParameters(command=sys.executable, args=["-m", "fullseye.mcp"], env=env, cwd=str(tmp_path))

    async def main():
        with open(tmp_path / "stderr.log", "w", encoding="utf-8") as errlog:
            async with stdio_client(params, errlog=errlog) as (r, w):
                async with ClientSession(r, w) as session:
                    ini = await asyncio.wait_for(session.initialize(), 60)
                    tools = await asyncio.wait_for(session.list_tools(), 60)
                    names = [t.name for t in tools.tools]
                    res = await asyncio.wait_for(session.call_tool("fullseye_list_samples", {}), 60)
                    return ini.serverInfo.name, names, res

    name, names, res = asyncio.run(main())
    assert name == "fullseye"
    assert len(names) >= 10 and "fullseye_list_samples" in names
    assert not res.isError and len(res.content) >= 1
