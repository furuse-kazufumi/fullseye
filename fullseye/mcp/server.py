# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""fullseye の MCP(Model Context Protocol)サーバ —— stdio / JSON-RPC 2.0。

器は llmesh の ``llmesh/mcp/stdio_server.py`` から借りた(Content-Length フレーミング、
``initialize`` / ``tools/list`` / ``tools/call``、protocol ``2025-06-18``)。
中身は :mod:`fullseye.mcp.catalog`。

設計の柱(2026-09-15、RAD と TRIZ の結果):
- **918 op を 918 個の tool にしない。** op はデータで、tool は検索・引き当て・実行の
  数個だけ(TheMCPCompany: 18,000 tool は retrieval 無しでは使えない)。
- **fail-closed。** 未知の tool / method / op 名 / 型違い / 範囲外 / 余計なキーは
  すべて明示的に拒否する。近い名前に黙って倒さない(Function Hijacking への
  構造的な緩和でもある)。
- **黙って劣化しない。** ``structuredContent`` が上限を超えたら落とすが、落としたことを
  本文と ``_meta`` に書く(llmesh の 512 KB と同じ値)。
- **stdout はプロトコル専用。** ログ・監査は stderr。stdout に 1 バイトでも余計に
  書くとフレーミングが壊れる。

この PoC は「知識層が LLM に効くか」だけを測る 3 tool(検索 / 引き当て / 被覆)。
画像を扱う ``apply`` はこの次の段。
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
from typing import Any

from .catalog import Catalog, CatalogError, SOURCES

PROTOCOL_VERSION = "2025-06-18"
SERVER_NAME = "fullseye"
#: llmesh/mcp/validator.py の ``_MAX_RAW_BYTES`` と同じ。超えたら typed tree を落とす。
MAX_STRUCTURED_BYTES = 512_000
#: 検索 1 回で返す上限。文脈経済のため(MCP-Universe: 歩数とともに入力が急増)。
MAX_SEARCH_LIMIT = 100

# --------------------------------------------------------------------------- #
# tool の宣言(入力スキーマは additionalProperties: false で余計なキーを拒む)     #
# --------------------------------------------------------------------------- #
_SORT_DESC = ("op の入出力の種別(image / region / points / volume ...)。"
              "既知の種別以外は拒否する")

TOOLS: dict[str, dict] = {
    "fullseye_search_ops": {
        "description": (
            "fullseye の op を探す。名前・HALCON 名・カテゴリ・次元の部分一致。"
            "返り値の sources が出どころ: index=機械可読索引 / registry=fullseye.apply で"
            "実行できる / note=知識層ノートあり / facade=import fullseye で呼べる関数。"
            "by_sources に層別の内訳が出る。"),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "maxLength": 200,
                          "description": "空白区切りの語。全部含む op が該当"},
                "in_sort": {"type": "string", "description": _SORT_DESC},
                "out_sort": {"type": "string", "description": _SORT_DESC},
                "source": {"type": "string", "enum": list(SOURCES),
                           "description": "この層に居る op だけに絞る"},
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_SEARCH_LIMIT},
            },
            "additionalProperties": False,
        },
    },
    "fullseye_op_help": {
        "description": (
            "op の知識層ノート(使い方・つまみ a/b の実効・HALCON 相当・関連ガイド)と、"
            "既に生成済みで実行が検証された図(入出力対比 / つまみ掃引 / 別入力)を返す。"
            "図は resource_link で、本文には載せない。"),
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string", "maxLength": 120}},
            "required": ["name"],
            "additionalProperties": False,
        },
    },
    "fullseye_catalog_coverage": {
        "description": (
            "カタログ 4 層(index / registry / note / facade)の交差を数える。"
            "検索がどれだけの機能を見えているか、ノートの無い op はどれかを返す。"),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
}


class ArgError(ValueError):
    """入力スキーマ違反。JSON-RPC の -32602 に写す。"""


def _validate(schema: dict, args: Any) -> dict:
    """依存を増やさない最小の検証(type / required / additionalProperties / enum /
    minimum / maximum / maxLength)。jsonschema があればそちらの方が厳密だが、
    **ここで検査する項目は全部自分で書けている**ことをテストが確かめる。"""
    if not isinstance(args, dict):
        raise ArgError("arguments はオブジェクトでなければならない(%s)" % type(args).__name__)
    props = schema.get("properties", {})
    if schema.get("additionalProperties") is False:
        extra = sorted(set(args) - set(props))
        if extra:
            raise ArgError("知らない引数: %s(許すのは %s)" % (extra, sorted(props)))
    for k in schema.get("required", ()):
        if k not in args:
            raise ArgError("必須の引数が無い: %s" % k)
    for k, v in args.items():
        p = props[k]
        t = p.get("type")
        if t == "string" and not isinstance(v, str):
            raise ArgError("%s は文字列でなければならない(%r)" % (k, v))
        if t == "integer" and (not isinstance(v, int) or isinstance(v, bool)):
            raise ArgError("%s は整数でなければならない(%r)" % (k, v))
        if "enum" in p and v not in p["enum"]:
            raise ArgError("%s は %s のどれか(%r)" % (k, p["enum"], v))
        if "minimum" in p and v < p["minimum"]:
            raise ArgError("%s は %d 以上(%r)" % (k, p["minimum"], v))
        if "maximum" in p and v > p["maximum"]:
            raise ArgError("%s は %d 以下(%r)" % (k, p["maximum"], v))
        if "maxLength" in p and len(v) > p["maxLength"]:
            raise ArgError("%s は %d 文字以下" % (k, p["maxLength"]))
    return args


# --------------------------------------------------------------------------- #
# 転送(llmesh から移植)                                                        #
# --------------------------------------------------------------------------- #
class FramingError(ValueError):
    """フレームは来たが JSON として読めない(EOF とは区別する)。"""


def read_message(stdin) -> dict | None:
    """Content-Length フレームを 1 つ読む。EOF は None、壊れた本文は FramingError。

    ★llmesh 版は両方 None にしていた。それだと「相手が切った」と「相手が壊れた JSON を
    送った」が同じに見え、後者に -32700 を返せない。"""
    headers: dict[bytes, bytes] = {}
    while True:
        raw = stdin.readline()
        if not raw:
            return None
        line = raw.strip()
        if not line:
            break
        if b":" in line:
            k, _, v = line.partition(b":")
            headers[k.strip().lower()] = v.strip()
    try:
        length = int(headers.get(b"content-length", 0))
    except ValueError as exc:
        raise FramingError("Content-Length が整数でない") from exc
    if length <= 0:
        return None
    body = stdin.read(length)
    if len(body) < length:
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise FramingError("本文が JSON でない: %s" % exc) from exc


def write_message(stdout, msg: dict) -> None:
    body = json.dumps(msg, ensure_ascii=False).encode("utf-8")
    stdout.write(b"Content-Length: " + str(len(body)).encode() + b"\r\n\r\n")
    stdout.write(body)
    stdout.flush()


def _ok(req_id, result) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _err(req_id, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _log(*parts) -> None:
    """監査は stderr へ。stdout はプロトコル専用。"""
    print("[fullseye-mcp]", *parts, file=sys.stderr, flush=True)


# --------------------------------------------------------------------------- #
# tool の結果                                                                   #
# --------------------------------------------------------------------------- #
def tool_result(text: str, structured: dict | None, *, links: list | None = None,
                max_structured_bytes: int = MAX_STRUCTURED_BYTES) -> dict:
    """本文(text)は必ず付け、typed tree は上限内なら付ける。超えたら**落としたと書く**。"""
    content: list[dict] = [{"type": "text", "text": text}]
    for lk in links or ():
        content.append(lk)
    result: dict = {"content": content, "isError": False}
    if structured is not None:
        n = len(json.dumps(structured, ensure_ascii=False).encode("utf-8"))
        if n <= max_structured_bytes:
            result["structuredContent"] = structured
        else:
            note = ("\n\n(structuredContent は %d バイトで上限 %d を超えたため落とした。"
                    "本文と resource_link だけを返している —— 黙って切り詰めてはいない)"
                    % (n, max_structured_bytes))
            content[0]["text"] += note
            result["_meta"] = {"fullseye": {"structured_dropped": True, "bytes": n,
                                            "limit": max_structured_bytes}}
    return result


def _tool_error(text: str) -> dict:
    return {"content": [{"type": "text", "text": text}], "isError": True}


def _figure_link(fig: dict) -> dict:
    ext = fig["kind"]
    mime = {"png": "image/png", "jpg": "image/jpeg", "gif": "image/gif"}[ext.rsplit(".", 1)[-1]]
    return {"type": "resource_link",
            "uri": pathlib.Path(fig["path"]).as_uri(),
            "name": os.path.basename(fig["path"]),
            "mimeType": mime,
            "description": fig["description"]}


def _search_text(r: dict) -> str:
    lines = ["検索 %r: 該当 %d 件(%d 件返却%s)" % (
        r["query"], r["total"], r["returned"], "、切り詰め" if r["truncated"] else "")]
    lines.append("層別: " + ", ".join("%s=%d" % kv for kv in sorted(r["by_sources"].items())))
    for o in r["ops"]:
        io = ("%s → %s" % (o["in_sort"], o["out_sort"])) if o["in_sort"] or o["out_sort"] else "(型なし)"
        lines.append("- %s  [%s]  %s  %s%s" % (
            o["name"], "+".join(o["sources"]), io,
            ("halcon=%s " % o["halcon"]) if o["halcon"] else "",
            "ノートあり" if o["has_note"] else "ノートなし"))
    return "\n".join(lines)


def _help_text(h: dict) -> str:
    if not h["found"]:
        return "%s: %s。近い名前: %s" % (h["name"], h["reason"], h["nearest"])
    head = "# %s  [%s]  %s → %s\n(本文 %d 文字、%s、出典 %s。図 %d 枚は resource_link)\n\n" % (
        h["name"], "+".join(h["sources"]), h["in_sort"], h["out_sort"],
        h["body_chars"], h["body_format"] or "本文なし", h["body_source"] or "-", len(h["figures"]))
    return head + (h["body"] or "(この op にはノートも Studio ヘルプも無い)")


def _coverage_text(c: dict) -> str:
    return ("op 名 %d。層別: %s。索引にあってノート無し %d / レジストリにあって索引無し %d / "
            "索引にあってレジストリ無し %d / facade にあって索引無し %d / ノートだけ %d"
            % (c["total_names"], c["per_source"], len(c["index_without_note"]),
               len(c["registry_not_in_index"]), len(c["index_not_in_registry"]),
               c["facade_not_in_index"], c["note_only"]))


# --------------------------------------------------------------------------- #
# ディスパッチ                                                                  #
# --------------------------------------------------------------------------- #
def handle_initialize(_params: dict) -> dict:
    return {"protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": SERVER_NAME, "version": _version()}}


def _version() -> str:
    try:
        import fullseye
        return str(getattr(fullseye, "__version__", "0"))
    except Exception:                                           # noqa: BLE001
        return "0"


def handle_tools_list(_params: dict) -> dict:
    return {"tools": [{"name": n, "description": t["description"], "inputSchema": t["inputSchema"]}
                      for n, t in sorted(TOOLS.items())]}


def call_tool(name: str, args: Any, cat: Catalog, *,
              max_structured_bytes: int = MAX_STRUCTURED_BYTES) -> dict:
    """tool 本体。引数違反は ArgError(= -32602)、実行の失敗は isError の結果。"""
    if name not in TOOLS:
        raise ArgError("知らない tool: %r(あるのは %s)" % (name, sorted(TOOLS)))
    a = _validate(TOOLS[name]["inputSchema"], args if args is not None else {})
    if name == "fullseye_search_ops":
        for k in ("in_sort", "out_sort"):
            if a.get(k) and a[k] not in cat.sorts:
                raise ArgError("%s=%r は知らない種別(あるのは %s)" % (k, a[k], cat.sorts))
        r = cat.search(a.get("query", ""), in_sort=a.get("in_sort"), out_sort=a.get("out_sort"),
                       source=a.get("source"), limit=a.get("limit", 20))
        return tool_result(_search_text(r), r, max_structured_bytes=max_structured_bytes)
    if name == "fullseye_op_help":
        h = cat.help(a["name"])
        if not h["found"]:
            return _tool_error(_help_text(h))
        links = [_figure_link(f) for f in h["figures"]]
        structured = {k: v for k, v in h.items() if k != "body"}   # 本文は text 側に
        return tool_result(_help_text(h), structured, links=links,
                           max_structured_bytes=max_structured_bytes)
    if name == "fullseye_catalog_coverage":
        c = cat.coverage()
        return tool_result(_coverage_text(c), c, max_structured_bytes=max_structured_bytes)
    raise ArgError("未実装の tool: %r" % name)                 # TOOLS に足して本体を忘れた


def dispatch(msg: dict, cat: Catalog) -> dict | None:
    """1 メッセージを処理。通知(id 無し)には返さない。"""
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0":
        return _err(msg.get("id") if isinstance(msg, dict) else None, -32600, "JSON-RPC 2.0 でない")
    req_id = msg.get("id")
    method = msg.get("method")
    params = msg.get("params") or {}
    is_notification = "id" not in msg
    try:
        if method == "initialize":
            res = handle_initialize(params)
        elif method == "ping":
            res = {}
        elif method == "tools/list":
            res = handle_tools_list(params)
        elif method == "tools/call":
            name = params.get("name")
            res = call_tool(name, params.get("arguments"), cat)
            _log("tools/call", name, "ok" if not res.get("isError") else "isError")
        elif method in ("notifications/initialized", "notifications/cancelled"):
            return None
        else:
            if is_notification:
                return None
            return _err(req_id, -32601, "知らない method: %r" % method)
    except ArgError as exc:
        _log("tools/call", params.get("name"), "-32602", str(exc))
        return None if is_notification else _err(req_id, -32602, str(exc))
    except CatalogError as exc:
        return None if is_notification else _err(req_id, -32603, "カタログ: %s" % exc)
    return None if is_notification else _ok(req_id, res)


def run_stdio_server(stdin=None, stdout=None, *, catalog: Catalog | None = None) -> int:
    """EOF まで回す。壊れたフレームには -32700 を返して続ける。"""
    stdin = stdin if stdin is not None else sys.stdin.buffer
    stdout = stdout if stdout is not None else sys.stdout.buffer
    cat = catalog if catalog is not None else Catalog.load()
    _log("ready: %d names, %d sorts" % (len(cat.entries), len(cat.sorts)))
    while True:
        try:
            msg = read_message(stdin)
        except FramingError as exc:
            write_message(stdout, _err(None, -32700, str(exc)))
            continue
        if msg is None:
            return 0
        resp = dispatch(msg, cat)
        if resp is not None:
            write_message(stdout, resp)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--coverage" in argv:
        # 起動せずに被覆だけ標準出力へ(人が読む用。プロトコルではない)
        print(json.dumps(Catalog.load().coverage(), ensure_ascii=False, indent=1))
        return 0
    return run_stdio_server()
