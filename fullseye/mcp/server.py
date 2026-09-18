# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""fullseye の MCP(Model Context Protocol)サーバ —— stdio / JSON-RPC 2.0。

器は llmesh の ``llmesh/mcp/stdio_server.py`` から借りた(Content-Length フレーミング、
``initialize`` / ``tools/list`` / ``tools/call``、protocol ``2025-06-18``)。
中身は :mod:`fullseye.mcp.catalog`(op と知識層)、:mod:`fullseye.mcp.handles`
(画像のハンドルとサンドボックス)、:mod:`fullseye.mcp.diagnose`(自己診断と対比図)。

設計の柱(2026-09-15、RAD と TRIZ の結果):
- **918 op を 918 個の tool にしない。** op はデータで、tool は検索・引き当て・読み込み・
  実行・観察の 7 つだけ(TheMCPCompany: 18,000 tool は retrieval 無しでは使えない)。
- **fail-closed。** 未知の tool / method / op 名 / ハンドル / 根の外のパス / 型違い /
  範囲外 / 余計なキー / **in_sort の不一致**はすべて理由つきで拒否する。近い名前に
  黙って倒さない(Function Hijacking への構造的な緩和でもある)。
- **黙って劣化しない。** 既定は strict(``on_error="raise"``)。``allow_degraded`` を
  明示したときだけ fail-soft を許し、**劣化台帳を必ず結果に載せる**(空でも ``[]``)。
  ``structuredContent`` が上限を超えたら落とすが、落としたことを本文と ``_meta`` に書く。
- **画像は在らず、必要なときだけ在る。** 返り値は数値 + 判定(必ず併記)。判定が ok で
  ないときだけ入出力対比の小図を ``resource_link`` で**自動昇格**する(TRIZ 時間分離 /
  #22 災い転じて福)。``vision`` で強制も抑止もできる。
- **stdout はプロトコル専用。** ログ・監査は stderr。
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
from typing import Any

import numpy as np

from .catalog import Catalog, CatalogError, SOURCES
from .diagnose import side_by_side, stats_of, verdict_of
from .handles import HandleError, HandleStore

PROTOCOL_VERSION = "2025-06-18"
SERVER_NAME = "fullseye"
#: llmesh/mcp/validator.py の ``_MAX_RAW_BYTES`` と同じ。超えたら typed tree を落とす。
MAX_STRUCTURED_BYTES = 512_000
#: 検索 1 回で返す上限。文脈経済のため(MCP-Universe: 歩数とともに入力が急増)。
MAX_SEARCH_LIMIT = 100
VISION = ("auto", "none", "thumb")

# --------------------------------------------------------------------------- #
# tool の宣言(入力スキーマは additionalProperties: false で余計なキーを拒む)     #
# --------------------------------------------------------------------------- #
_SORT_DESC = ("op の入出力の種別(image / region / points / volume ...)。"
              "既知の種別以外は拒否する")
_HANDLE = {"type": "string", "maxLength": 64,
           "description": "fullseye://img/<16 hex>。load_image / apply が返す"}
_VISION = {"type": "string", "enum": list(VISION),
           "description": "auto=判定が ok でないときだけ対比の小図を出す / none=出さない / thumb=必ず出す"}

TOOLS: dict[str, dict] = {
    "fullseye_search_ops": {
        "description": (
            "fullseye の op を探す。名前・HALCON 名・カテゴリ・次元の部分一致。"
            "返り値の sources が出どころ: index=機械可読索引 / registry=fullseye_apply で"
            "実行できる / ledger=型付き台帳 / note=知識層ノートあり / facade=import fullseye で"
            "呼べる関数。by_sources に層別の内訳が出る。"),
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
            "カタログ 5 層(index / registry / ledger / note / facade)の交差を数える。"
            "検索がどれだけの機能を見えているか、ノートの無い op はどれかを返す。"),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    "fullseye_list_samples": {
        "description": "同梱のサンプル画像(来歴・ライセンスつき)。load_image に渡せるパスを返す。",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    "fullseye_load_image": {
        "description": (
            "画像を読み込んでハンドルを返す。読めるのはサンドボックス根の下だけ"
            "(既定は同梱サンプル、FULLSEYE_MCP_ROOT で追加)。画素は返さず、数値統計と判定を返す。"),
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "maxLength": 1024},
                "color": {"type": "boolean", "description": "true なら (H,W,3) の color として読む"},
                "vision": _VISION,
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    "fullseye_apply": {
        "description": (
            "ハンドルの画像に op を 1 つ適用し、出力ハンドル + 数値統計 + 判定 + 劣化台帳を返す。"
            "既定は strict(op が劣化したら拒否)。allow_degraded=true で fail-soft を許し、"
            "degraded に何が起きたかを載せる。判定が ok でなければ入出力対比の小図を自動で付ける。"
            "op の in_sort とハンドルの sort が違えば拒否する。"),
        "inputSchema": {
            "type": "object",
            "properties": {
                "handle": _HANDLE,
                "op": {"type": "string", "maxLength": 120},
                "a": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "b": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "allow_degraded": {"type": "boolean"},
                "vision": _VISION,
            },
            "required": ["handle", "op"],
            "additionalProperties": False,
        },
    },
    "fullseye_inspect": {
        "description": "ハンドルの数値統計と判定。vision=thumb で小図(1 枚)を resource_link で返す。",
        "inputSchema": {
            "type": "object",
            "properties": {"handle": _HANDLE, "vision": _VISION},
            "required": ["handle"],
            "additionalProperties": False,
        },
    },
    "fullseye_pipeline": {
        "description": (
            "op を順に適用する。段ごとに数値統計・判定・劣化台帳を記録し、最終ハンドル(と最後が"
            "計測なら値)を返す。走らせる前に段間の型連鎖(前段の out_sort = 次段の in_sort)を検査し、"
            "破れていれば 1 段も走らせず拒否。strict(既定)では劣化した段で止まり、どこまで走ったかを"
            "返す。判定が最初に割れた段の入出力対比の小図を自動で付ける。"),
        "inputSchema": {
            "type": "object",
            "properties": {
                "handle": _HANDLE,
                "stages": {
                    "type": "array", "minItems": 1, "maxItems": 64,
                    "items": {
                        "type": "object",
                        "properties": {
                            "op": {"type": "string", "maxLength": 120},
                            "a": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                            "b": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                        },
                        "required": ["op"],
                        "additionalProperties": False,
                    },
                    "description": "[{op, a?, b?}, …]。a/b の既定は 0.5",
                },
                "allow_degraded": {"type": "boolean"},
                "vision": _VISION,
            },
            "required": ["handle", "stages"],
            "additionalProperties": False,
        },
    },
    "fullseye_fix_text": {
        "description": (
            "画像の中の文字を「本当はこう書いてあるべき文字列」に合わせて直す(生成 AI が出した"
            "レポート用画像・看板の誤字を再生成せずに直す用途)。ハンドルは color(HxWx3)。"
            "items は行ごとに {text, bbox:[x,y,w,h]}(bbox は省略可: 行を自動検出)。mode=repair_flagged(既定)は床を超えた字だけ"
            "置き換え正しい字に触らない / mode=rewrite_line は bbox の行を同じ書体で丸ごと描き直す"
            "(見逃し・字数違いも直るが書体は変わる)。返り値: 直した画像のハンドル + 全解像度 PNG の"
            " resource_link + 行ごとの status(ok/replaced/failed_verification/skipped/rewritten)、"
            "skipped の reason_code、mismatch(typo=誤字 / unrelated=元の字が指示と無関係な疑い)。"
            "直せなかった行はそのまま残し、検証を通らない置換は元に戻す —— 黙って壊した絵は返さない。"),
        "inputSchema": {
            "type": "object",
            "properties": {
                "handle": _HANDLE,
                "items": {
                    "type": "array", "minItems": 1, "maxItems": 64,
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string", "maxLength": 200,
                                     "description": "その行に本当に書いてあるべき文字列"},
                            "bbox": {"type": "array", "minItems": 4, "maxItems": 4,
                                     "items": {"type": "number"},
                                     "description": "[x, y, w, h] 画素。行に密着した箱。省くと暗い字の"
                                                    "行を上から検出して items の順に当てる(全行そろえて"
                                                    "付けるか省く)。版面が取れなければ isError で断る"},
                        },
                        "required": ["text"],
                        "additionalProperties": False,
                    },
                },
                "mode": {"type": "string", "enum": ["repair_flagged", "rewrite_line"]},
                "threshold": {"type": "number", "minimum": 0.0, "maximum": 10.0,
                              "description": "省略すれば環境の書体の散らばりから床を測る(推奨)"},
                "vision": _VISION,
            },
            "required": ["handle", "items"],
            "additionalProperties": False,
        },
    },
    "fullseye_import_json": {
        "description": (
            "型付きの値を JSON 封筒で受け取り、以後の op が使えるハンドルにする(引数で JSON を"
            "渡す入口)。fullseye.to_json / to_jsonable が作る自己記述の封筒 "
            "{fullseye_sort, version, payload} を、文字列なら json= に、オブジェクトなら envelope= に"
            "渡す(どちらか一方)。image / color / region / points / matrix / signal … の配列 sort は"
            "ハンドルにして返す(handle + sort + shape)。feature / contour / table は配列でないので"
            "ハンドルにせず値を structuredContent に返す。壊れた封筒・未知 sort・形の不一致は"
            "-32602 で断る(fail-closed、推測しない)。"),
        "inputSchema": {
            "type": "object",
            "properties": {
                "json": {"type": "string", "maxLength": MAX_STRUCTURED_BYTES,
                         "description": "fullseye.to_json が作る JSON 文字列(封筒)"},
                "envelope": {"type": "object",
                             "description": "fullseye.to_jsonable が作る封筒(オブジェクト)。json とは排他"},
            },
            "additionalProperties": False,
        },
    },
    "fullseye_export_json": {
        "description": (
            "ハンドルの中身(型付きの値)を JSON 封筒として取り出す(MCP の外へ値を持ち出す出口)。"
            "structuredContent に fullseye.to_jsonable の封筒(fullseye.from_jsonable で bit そのまま"
            "戻せる)、本文に fullseye.to_markdown の読める描画(表または 1 行要約)を返す。"
            "readable=true なら封筒の数を base64 でなくリストにする(人が読める・往復は厳密)。"
            "封筒が上限(%d バイト)を超える大きな画像は isError で断る —— 画像はハンドルか小図で"
            "扱うこと。sort が JSON にできないハンドルも断る。" % MAX_STRUCTURED_BYTES),
        "inputSchema": {
            "type": "object",
            "properties": {
                "handle": _HANDLE,
                "readable": {"type": "boolean",
                             "description": "数を base64 でなくリストで出す(小さい値向け・往復は厳密)"},
            },
            "required": ["handle"],
            "additionalProperties": False,
        },
    },
    "fullseye_estimate_distortion": {
        "description": (
            "本来まっすぐな線群の点列から Brown–Conrady 歪み係数 dist=[k1,k2,p1,p2,k3] を推定する"
            "(plumb-line 法、チェッカーボード不要)。lines は各線の点列 [[x,y],…](x=col,y=row)を"
            "並べた配列(2 本以上・各線 3 点以上、向きの違う線を混ぜる)、K は 3x3 内部行列"
            "(主点=歪み中心で固定)。radial=1/2/3 で放射次数、tangential で p1,p2 の有無。返す dist は"
            "undistort_image / undistort_points にそのまま渡せる。lines/K は信頼境界で再検証し、"
            "形が違えば -32602、推定不能は isError で断る(fail-closed、推測しない)。"),
        "inputSchema": {
            "type": "object",
            "properties": {
                "lines": {"type": "array", "minItems": 2,
                          "description": "各線の点列 [[x,y],…](x=col,y=row)。2 本以上、各線 3 点以上"},
                "K": {"type": "array", "minItems": 3, "maxItems": 3,
                      "description": "3x3 内部行列(行の配列)。主点が歪み中心"},
                "radial": {"type": "integer", "minimum": 1, "maximum": 3,
                           "description": "放射次数(1=k1 / 2=k1,k2 / 3=k1,k2,k3)。既定 2"},
                "tangential": {"type": "boolean", "description": "p1,p2 も推定するか。既定 true"},
            },
            "required": ["lines", "K"],
            "additionalProperties": False,
        },
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
        if t == "boolean" and not isinstance(v, bool):
            raise ArgError("%s は真偽値でなければならない(%r)" % (k, v))
        if t == "integer" and (not isinstance(v, int) or isinstance(v, bool)):
            raise ArgError("%s は整数でなければならない(%r)" % (k, v))
        if t == "number" and (not isinstance(v, (int, float)) or isinstance(v, bool)):
            raise ArgError("%s は数でなければならない(%r)" % (k, v))
        if t == "number" and isinstance(v, float) and v != v:
            raise ArgError("%s が NaN" % k)
        if t == "array":
            if not isinstance(v, list):
                raise ArgError("%s は配列でなければならない(%s)" % (k, type(v).__name__))
            # 唯一の配列はパイプラインの段なので「段」と数える
            if "minItems" in p and len(v) < p["minItems"]:
                raise ArgError("%s は %d 段以上(いま %d)" % (k, p["minItems"], len(v)))
            if "maxItems" in p and len(v) > p["maxItems"]:
                raise ArgError("%s は %d 段以下(いま %d)" % (k, p["maxItems"], len(v)))
            items = p.get("items")
            if items and items.get("type") == "object":
                for i, it in enumerate(v):
                    try:
                        _validate(items, it)
                    except ArgError as exc:
                        raise ArgError("%s[%d]: %s" % (k, i, exc)) from exc
            elif items and items.get("type") == "number":
                for i, it in enumerate(v):
                    if not isinstance(it, (int, float)) or isinstance(it, bool) or it != it:
                        raise ArgError("%s[%d] は数でなければならない(%r)" % (k, i, it))
            continue
        if "enum" in p and v not in p["enum"]:
            raise ArgError("%s は %s のどれか(%r)" % (k, p["enum"], v))
        if "minimum" in p and v < p["minimum"]:
            raise ArgError("%s は %g 以上(%r)" % (k, p["minimum"], v))
        if "maximum" in p and v > p["maximum"]:
            raise ArgError("%s は %g 以下(%r)" % (k, p["maximum"], v))
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


def _tool_error(text: str, structured: dict | None = None) -> dict:
    r: dict = {"content": [{"type": "text", "text": text}], "isError": True}
    if structured is not None:
        r["structuredContent"] = structured
    return r


def _file_link(path: str, name: str, mime: str, description: str) -> dict:
    return {"type": "resource_link", "uri": pathlib.Path(path).as_uri(),
            "name": name, "mimeType": mime, "description": description}


def _figure_link(fig: dict) -> dict:
    ext = fig["kind"]
    mime = {"png": "image/png", "jpg": "image/jpeg", "gif": "image/gif"}[ext.rsplit(".", 1)[-1]]
    return _file_link(fig["path"], os.path.basename(fig["path"]), mime, fig["description"])


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


def _stats_line(st: dict, vd: dict) -> str:
    if st.get("kind") == "array" and "min" in st:
        nums = "shape=%s min=%.4g max=%.4g mean=%.4g std=%.4g nonfinite=%d" % (
            st["shape"], st["min"], st["max"], st["mean"], st["std"], st["nonfinite"])
    elif st.get("kind") == "scalar":
        nums = "value=%g" % st["value"]
    else:
        nums = json.dumps({k: v for k, v in st.items() if k != "kind"}, ensure_ascii=False)[:160]
    return "判定=%s(%s)  %s" % (vd["verdict"], "; ".join(vd["reasons"]), nums)


# --------------------------------------------------------------------------- #
# 画像を扱う tool の本体                                                         #
# --------------------------------------------------------------------------- #
def _describe(meta: dict, arr, *, op_name=None, out_sort=None) -> tuple[dict, dict]:
    st = stats_of(arr)
    vd = verdict_of(st, op_name=op_name, out_sort=out_sort or meta.get("sort"))
    return st, vd


def _maybe_thumb(store: HandleStore, meta: dict, inp, out, *, vision: str, escalate: bool,
                 quantity: bool, tag: str) -> list[dict]:
    """自動昇格: auto は判定が ok でないときだけ、thumb は必ず、none は出さない。"""
    if vision == "none" or (vision == "auto" and not escalate):
        return []
    rgb = side_by_side(inp, out, out_is_quantity=quantity) if inp is not None else side_by_side(out, None, out_is_quantity=quantity)
    if rgb is None:
        return []
    path = store.write_thumb(meta["handle"], rgb, tag)
    why = "判定が ok でないので自動で付けた" if vision == "auto" else "要求により付けた"
    desc = ("入出力の対比(左が入力・右が出力、高さ %d px、%s)。%s"
            % (rgb.shape[0], "出力は viridis の疑似カラー" if quantity else "グレーのまま", why))
    return [_file_link(path, os.path.basename(path), "image/png", desc)]


def _load_image(a: dict, store: HandleStore) -> dict:
    meta = store.load(a["path"], color=bool(a.get("color", False)))
    _, arr = store.get(meta["handle"])
    st, vd = _describe(meta, arr)
    links = _maybe_thumb(store, meta, None, arr, vision=a.get("vision", "auto"),
                         escalate=vd["escalate"], quantity=False, tag="load")
    structured = {"handle": meta["handle"], "sort": meta["sort"], "shape": meta["shape"],
                  "dtype": meta["dtype"], "provenance": meta["provenance"],
                  "stats": st, **vd, "dedup": bool(meta.get("dedup", False))}
    text = "%s  sort=%s\n%s" % (meta["handle"], meta["sort"], _stats_line(st, vd))
    return tool_result(text, structured, links=links)


def _resolve_op(name: str, cat: Catalog, *, stage: int | None = None):
    """registry 層の op に解決する。無ければ近い名前を添えて拒否(黙って倒さない)。"""
    import ops
    op = ops._BY_NAME.get(name)
    if op is None:
        where = "段 %d: " % stage if stage else ""
        raise ArgError("%sfullseye_apply で実行できる op ではない: %r(registry 層に無い)。近い名前: %s"
                       % (where, name, cat.nearest(name)))
    return op


def _check_sort(op, cur_sort: str, *, stage: int | None = None, prev: str = "ハンドル") -> None:
    """型契約を境界で守る。in_sort が合わなければ走らせない。"""
    if op.in_sort in ("any", cur_sort):
        return
    where = "(段 %d)" % stage if stage else ""
    raise ArgError("型の不一致%s: %s は %s を受けるが、%s は %s(変換 op を先に挟むこと)"
                   % (where, op.name, op.in_sort, prev, cur_sort))


def _run_op(arr, op, ka: float, kb: float, allow: bool):
    """1 op を走らせる。strict で失敗したら (None, degraded, err)。"""
    import backend_safe
    import fullseye
    backend_safe.clear_fallbacks()
    try:
        out = fullseye.apply(arr, op.name, ka, kb, on_error=("fallback" if allow else "raise"))
    except Exception as exc:                                    # noqa: BLE001
        return None, backend_safe.fallbacks(), {"type": type(exc).__name__, "message": str(exc)[:400]}
    return out, backend_safe.fallbacks(), None


def _stage(store: HandleStore, meta: dict, arr, op, ka: float, kb: float, allow: bool, *,
           vision: str, thumb_allowed: bool, tag: str):
    """apply 1 段ぶん: 記録(数値 + 判定 + 劣化台帳)と、必要なら小図。
    返り値 = (record, links, out_meta | None, out_value)。out_meta は配列のときだけ。"""
    import numpy as np
    import ops
    out, degraded, err = _run_op(arr, op, ka, kb, allow)
    rec: dict = {"op": op.name, "a": ka, "b": kb, "handle_in": meta.get("handle"),
                 "in_sort": op.in_sort, "out_sort": op.out_sort,
                 "degraded": degraded, "strict": not allow}
    if err is not None:
        rec["error"] = err
        return rec, [], None, None
    st = stats_of(out)
    vd = verdict_of(st, op_name=op.name, out_sort=op.out_sort)
    if degraded:
        vd = dict(vd, escalate=True,
                  reasons=vd["reasons"] + ["劣化 %d 件(degraded を見ること)" % len(degraded)])
    rec.update({"stats": st, **vd})
    prov = list(meta.get("provenance", [])) + [{"apply": op.name, "a": ka, "b": kb}]
    links: list[dict] = []
    m2 = None
    if isinstance(out, np.ndarray):
        m2 = store.put(out, sort=op.out_sort, provenance=prov)
        rec["handle"] = m2["handle"]
        if thumb_allowed:
            links = _maybe_thumb(store, m2, arr, out, vision=vision, escalate=vd["escalate"],
                                 quantity=op.name in ops.UNIT_RANGE_IS_NOT_THE_CONTRACT, tag=tag)
    elif isinstance(out, dict) and "cs" in out:
        rec["handle"] = None
        rec["contour"] = {"n": st.get("n_contours"), "points": st.get("n_points")}
        m2 = {"handle": None, "sort": op.out_sort, "provenance": prov}   # 連鎖用の疑似メタ
    else:
        rec["handle"] = None
        rec["value"] = st.get("value")
    return rec, links, m2, out


def _stage_text(rec: dict) -> str:
    if "error" in rec:
        return "%s(a=%.2f, b=%.2f) → strict で拒否: %s: %s" % (
            rec["op"], rec["a"], rec["b"], rec["error"]["type"], rec["error"]["message"][:200])
    head = "%s(a=%.2f, b=%.2f) → %s" % (
        rec["op"], rec["a"], rec["b"],
        rec.get("handle") or ("value=%s" % rec.get("value") if "value" in rec else "contour"))
    text = head + "\n" + _stats_line(rec["stats"], rec)
    if rec["degraded"]:
        text += "\n劣化 %d 件: " % len(rec["degraded"]) + "; ".join(
            "%s@%s: %s" % (d["name"], d["source"], d["error"][:80]) for d in rec["degraded"][:5])
    return text


def _apply(a: dict, cat: Catalog, store: HandleStore) -> dict:
    op = _resolve_op(a["op"], cat)
    meta, arr = store.get(a["handle"])
    _check_sort(op, meta["sort"], prev="ハンドル %s" % meta["handle"])
    ka, kb = float(a.get("a", 0.5)), float(a.get("b", 0.5))
    allow = bool(a.get("allow_degraded", False))
    rec, links, _, _ = _stage(store, meta, arr, op, ka, kb, allow, vision=a.get("vision", "auto"),
                              thumb_allowed=True, tag=op.name)
    if "error" in rec:
        text = _stage_text(rec) + "\n(allow_degraded=true で fail-soft を許せるが、劣化は degraded に載る)"
        return _tool_error(text, rec)
    return tool_result(_stage_text(rec), rec, links=links)


def _pipeline(a: dict, cat: Catalog, store: HandleStore) -> dict:
    """段を順に。**走らせる前に**型連鎖を検査し、strict は失敗した段で止まる。"""
    stages = a["stages"]
    ops_ = [_resolve_op(s["op"], cat, stage=i) for i, s in enumerate(stages, 1)]
    meta, arr = store.get(a["handle"])
    cur, prev = meta["sort"], "ハンドル %s" % meta["handle"]
    for i, op in enumerate(ops_, 1):
        _check_sort(op, cur, stage=i, prev=prev)
        cur, prev = op.out_sort, "前段 %s の出力" % op.name
    allow = bool(a.get("allow_degraded", False))
    vision = a.get("vision", "auto")
    recs: list[dict] = []
    links: list[dict] = []
    escalated = False
    cur_meta, cur_val = meta, arr
    final_handle, final_value = None, None
    for i, (s, op) in enumerate(zip(stages, ops_), 1):
        ka, kb = float(s.get("a", 0.5)), float(s.get("b", 0.5))
        thumb_ok = vision == "thumb" or (vision == "auto" and not escalated)
        rec, lk, m2, out = _stage(store, cur_meta, cur_val, op, ka, kb, allow, vision=vision,
                                  thumb_allowed=thumb_ok, tag="stage%d_%s" % (i, op.name))
        rec["stage"] = i
        recs.append(rec)
        if "error" in rec:
            text = ("段 %d の %s が strict で拒否された(%d/%d 段まで完了)。\n%s\n"
                    "(allow_degraded=true で fail-soft を許せるが、劣化は degraded に載る)"
                    % (i, op.name, i - 1, len(stages), _stage_text(rec)))
            return _tool_error(text, {"handle_in": meta["handle"], "stages": recs,
                                      "completed": i - 1, "stopped_at": i, "strict": not allow})
        if lk:
            for l in lk:
                l["description"] = "段 %d(%s): " % (i, op.name) + l["description"]
            links += lk
            escalated = True
        if m2 is not None:
            cur_meta, cur_val = m2, out
            if m2.get("handle"):
                final_handle = m2["handle"]
        else:
            final_value = rec.get("value")
            cur_meta, cur_val = {"handle": None, "sort": op.out_sort,
                                 "provenance": cur_meta.get("provenance", [])}, out
    structured = {"handle_in": meta["handle"], "stages": recs, "completed": len(recs),
                  "stopped_at": None, "handle": final_handle, "value": final_value,
                  "strict": not allow}
    lines = ["パイプライン %d 段 完走 → %s" % (
        len(recs), final_handle or ("value=%s" % final_value))]
    for r in recs:
        lines.append("[段 %d] " % r["stage"] + _stage_text(r).replace("\n", "\n        "))
    return tool_result("\n".join(lines), structured, links=links)


def _fix_text(a: dict, store: HandleStore) -> dict:
    """:func:`glyphops.correct_spec` を MCP から。**color ハンドル以外は拒否**し、
    直した画像はハンドルと全解像度 PNG(resource_link)の両方で返す —— 呼ぶ側(LLM)は
    画素を見られないので、ファイルとして受け取れる形が要る。"""
    import glyphops
    meta, arr = store.get(a["handle"])
    if meta["sort"] != "color":
        raise ArgError("fix_text は color(HxWx3)のハンドルを取る(いま %s)。"
                       "load_image を color=true で読み直す" % meta["sort"])
    policy: dict = {"mode": a.get("mode", "repair_flagged")}
    if "threshold" in a:
        policy["threshold"] = float(a["threshold"])
    rgb = np.asarray(arr, np.float64)
    if rgb.max() > 1.0:
        rgb = rgb / 255.0
    has = [("bbox" in it) for it in a["items"]]
    if any(has) and not all(has):
        raise ArgError("bbox は全部の行に付けるか、全部省く(混在は不可: 検出した行と与えた箱の"
                       "対応が決まらない)")
    layout = None
    if not any(has):
        # ★bbox が無いときは glyphops.make_spec に任せる。版面が取れなければ items に bbox が
        #   入らない = 黙って外れた箱で直すことは起きない。ここでは理由を付けて断る。
        spec = glyphops.make_spec(rgb, [it["text"] for it in a["items"]], policy)
        layout = spec["layout"]
        if layout["status"] != "ok":
            return _tool_error("fix_text: 行の位置が取れない —— %s。bbox を与えて呼び直す"
                               % layout["reason"], {"layout": layout})
    else:
        spec = {"items": [{"text": it["text"], "bbox": [float(v) for v in it["bbox"]]}
                          for it in a["items"]], "policy": policy}
    try:
        out, rep = glyphops.correct_spec(rgb, spec)
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        return _tool_error("fix_text: %s" % exc, {"error": str(exc)})
    prov = list(meta["provenance"]) + [{"fix_text": {
        "mode": rep["mode"], "items": len(spec["items"]),
        "threshold": rep["threshold"], "floor_source": rep["floor_source"]}}]
    om = store.put(out, sort="color", provenance=prov)
    full = store.write_thumb(om["handle"], out, "fixed")
    links = [_file_link(full, os.path.basename(full), "image/png",
                        "直した画像そのもの(全解像度、縮小していない)")]
    fine = ("ok", "replaced", "rewritten")
    bad = [it for it in rep["items"] if it["status"] not in fine]
    suspicious = any(it.get("mismatch") == "unrelated" for it in rep["items"])
    vision = a.get("vision", "auto")
    if vision == "thumb" or (vision == "auto" and (bad or suspicious)):
        sbs = side_by_side(rgb, out, out_is_quantity=False)
        if sbs is not None:
            pth = store.write_thumb(om["handle"], sbs, "before_after")
            links.append(_file_link(pth, os.path.basename(pth), "image/png",
                                    "前後の対比(左が入力・右が出力)"))
    marks = {"ok": "・", "replaced": "◆", "rewritten": "◆", "failed_verification": "×",
             "skipped": "?"}
    lines = ["fix_text(mode=%s, 床=%.4f from %s, 書体 %d 本) → %s" % (
        rep["mode"], rep["threshold"], rep["floor_source"], rep["fonts"], om["handle"])]
    for it in rep["items"]:
        cells = "".join(marks.get(c.get("status", ""), "?") for c in it.get("cells", ()))
        extra = ""
        if it.get("reason"):
            extra += "  %s[%s]" % (it["reason"], it.get("reason_code", ""))
        if it.get("mismatch") in ("typo", "unrelated"):
            extra += "  mismatch=%s(壊れ %.0f %%, 距離 %.3f)" % (
                it["mismatch"], 100 * it.get("mismatch_fraction", 0.0), it.get("mismatch_distance", 0.0))
        lines.append("- %-19s %-16s %s%s" % (it["status"], it["text"], cells, extra))
    lines.append("記号: ・無事 ◆直した ×検証不通過(元に戻した) ?直せない。"
                 "unrelated は「元の字が指示と無関係」の疑い —— 指示か画像のどちらかを確かめる")
    structured = {"handle": om["handle"], "sort": "color", "shape": om["shape"],
                  "provenance": prov, "report": rep, "fixed_png": full,
                  "items": spec["items"]}                      # 使った bbox(自動検出なら検出値)
    if layout is not None:
        structured["layout"] = layout
        lines.insert(1, "bbox は自動検出(%d 行): %s" % (
            layout["n_lines"], ", ".join(str(it["bbox"]) for it in spec["items"])))
    return tool_result("\n".join(lines), structured, links=links)


def _inspect(a: dict, store: HandleStore) -> dict:
    meta, arr = store.get(a["handle"])
    last_op = next((p["apply"] for p in reversed(meta["provenance"]) if "apply" in p), None)
    st, vd = _describe(meta, arr, op_name=last_op)
    import ops
    quantity = last_op in ops.UNIT_RANGE_IS_NOT_THE_CONTRACT
    links = _maybe_thumb(store, meta, None, arr, vision=a.get("vision", "auto"),
                         escalate=vd["escalate"], quantity=quantity, tag="inspect")
    structured = {**meta, "stats": st, **vd}
    text = "%s  sort=%s  来歴=%s\n%s" % (meta["handle"], meta["sort"],
                                          json.dumps(meta["provenance"], ensure_ascii=False)[:200],
                                          _stats_line(st, vd))
    return tool_result(text, structured, links=links)


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


def _import_json(a: dict, store: HandleStore) -> dict:
    """JSON 封筒(引数)→ 配列 sort はハンドル、非配列は値。壊れた封筒は -32602。"""
    import numpy as np
    import fullseye

    has_json = a.get("json") is not None
    has_env = a.get("envelope") is not None
    if has_json == has_env:
        raise ArgError("json(文字列)か envelope(オブジェクト)のどちらか一方を渡すこと")
    try:
        value, sort = (fullseye.from_json(a["json"]) if has_json
                       else fullseye.from_jsonable(a["envelope"]))
    except ValueError as exc:                                    # 信頼境界: 封筒を再検証
        raise ArgError("JSON 封筒が読めない: %s" % exc) from None
    if isinstance(value, np.ndarray):
        meta = store.put(value, sort=sort, provenance=[{"import_json": sort}])
        text = "取り込んだ: %s  sort=%s  shape=%s%s" % (
            meta["handle"], sort, meta["shape"], "  (既出=同じ内容)" if meta.get("dedup") else "")
        return tool_result(text, {"handle": meta["handle"], "sort": sort,
                                  "shape": meta["shape"], "dedup": bool(meta.get("dedup"))})
    # feature / contour / table は配列でないのでハンドルにしない。値を返す。
    env = fullseye.to_jsonable(value, sort)
    text = (fullseye.to_markdown(value, sort)
            + "\n\n(%s は配列でないのでハンドルにしない。値を structuredContent に返す)" % sort)
    return tool_result(text, {"sort": sort, "handle": None, "value": env})


def _export_json(a: dict, store: HandleStore, *, max_structured_bytes: int) -> dict:
    """ハンドルの中身 → JSON 封筒(structuredContent)+ Markdown(本文)。上限超過は isError。"""
    import json as _json
    import fullseye

    meta, arr = store.get(a["handle"])                           # 未知ハンドルは HandleError→ArgError
    sort = meta["sort"]
    if sort not in fullseye.JSON_SORTS:
        return _tool_error(
            "handle の sort=%r は JSON 橋が無い(JSON にできるのは %s)。"
            % (sort, ", ".join(fullseye.JSON_SORTS)))
    try:
        env = fullseye.to_jsonable(arr, sort, readable=bool(a.get("readable", False)))
    except ValueError as exc:
        return _tool_error("JSON 化できない(%s): %s" % (sort, exc))
    n = len(_json.dumps(env, ensure_ascii=False).encode("utf-8"))
    if n > max_structured_bytes:
        return _tool_error(
            "この値の JSON は %d バイトで上限 %d を超える(sort=%s, shape=%s)。"
            "大きな画像はハンドルのまま扱うか小図で見ること —— JSON では持ち出さない。"
            % (n, max_structured_bytes, sort, meta["shape"]))
    text = (fullseye.to_markdown(arr, sort, title="%s  sort=%s" % (meta["handle"], sort))
            + "\n\n(structuredContent が JSON 封筒。fullseye.from_jsonable で bit そのまま戻せる)")
    return tool_result(text, env, max_structured_bytes=max_structured_bytes)


def _estimate_distortion(a: dict) -> dict:
    """直線群の点列(JSON)+ K → 歪み係数 dist。lines/K は信頼境界で再検証する。"""
    import numpy as np
    import fullseye

    try:                                                         # 信頼境界: 生配列を再検証
        K = np.asarray(a["K"], dtype=float)
        if K.shape != (3, 3) or not np.all(np.isfinite(K)):
            raise ValueError("K は有限値の 3x3 でなければならない")
        lines = []
        for i, ln in enumerate(a["lines"]):
            arr = np.asarray(ln, dtype=float)
            if arr.ndim != 2 or arr.shape[1] != 2:
                raise ValueError("lines[%d] は (N, 2) の点列 [[x,y],…] でない" % i)
            if not np.all(np.isfinite(arr)):
                raise ValueError("lines[%d] に非有限値がある" % i)
            lines.append(arr)
    except (ValueError, TypeError) as exc:
        raise ArgError("lines / K が読めない: %s" % exc) from None

    radial = int(a.get("radial", 2))
    tangential = bool(a.get("tangential", True))
    try:
        dist = fullseye.estimate_distortion(lines, K, radial=radial, tangential=tangential)
    except ValueError as exc:                                    # 線 2 本未満・各線 3 点未満など
        return _tool_error("歪み係数を推定できない: %s" % exc)
    d = [float(x) for x in dist]
    text = ("推定した歪み係数 dist = [k1, k2, p1, p2, k3]\n"
            "  k1=%.6g  k2=%.6g  p1=%.6g  p2=%.6g  k3=%.6g\n"
            "(undistort_image / undistort_points にそのまま渡せる。主点=歪み中心は K 固定、"
            "線 %d 本から推定)" % (d[0], d[1], d[2], d[3], d[4], len(lines)))
    return tool_result(text, {"dist": d, "radial": radial, "tangential": tangential,
                              "n_lines": len(lines)})


def call_tool(name: str, args: Any, cat: Catalog, store: HandleStore | None = None, *,
              max_structured_bytes: int = MAX_STRUCTURED_BYTES) -> dict:
    """tool 本体。引数違反は ArgError(= -32602)、実行の失敗は isError の結果。"""
    if name not in TOOLS:
        raise ArgError("知らない tool: %r(あるのは %s)" % (name, sorted(TOOLS)))
    a = _validate(TOOLS[name]["inputSchema"], args if args is not None else {})
    store = store if store is not None else HandleStore()
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
    if name == "fullseye_list_samples":
        rows = store.samples()
        text = "同梱サンプル %d 枚(根: %s)\n" % (len(rows), store.roots) + "\n".join(
            "- %s  %s  [%s / %s]" % (r["name"], r["path"], r["source"], r["licence"]) for r in rows)
        return tool_result(text, {"samples": rows, "roots": store.roots},
                           max_structured_bytes=max_structured_bytes)
    try:
        if name == "fullseye_load_image":
            return _load_image(a, store)
        if name == "fullseye_apply":
            return _apply(a, cat, store)
        if name == "fullseye_inspect":
            return _inspect(a, store)
        if name == "fullseye_pipeline":
            return _pipeline(a, cat, store)
        if name == "fullseye_fix_text":
            return _fix_text(a, store)
        if name == "fullseye_import_json":
            return _import_json(a, store)
        if name == "fullseye_export_json":
            return _export_json(a, store, max_structured_bytes=max_structured_bytes)
        if name == "fullseye_estimate_distortion":
            return _estimate_distortion(a)
    except HandleError as exc:
        raise ArgError(str(exc)) from exc
    raise ArgError("未実装の tool: %r" % name)                 # TOOLS に足して本体を忘れた


def dispatch(msg: dict, cat: Catalog, store: HandleStore | None = None) -> dict | None:
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
            res = call_tool(name, params.get("arguments"), cat, store)
            _log("tools/call", name, "ok" if not res.get("isError") else "isError")
        elif method in ("notifications/initialized", "notifications/cancelled"):
            return None
        else:
            if is_notification:
                return None
            return _err(req_id, -32601, "知らない method: %r" % method)
    except ArgError as exc:
        _log("tools/call", params.get("name"), "-32602", str(exc)[:200])
        return None if is_notification else _err(req_id, -32602, str(exc))
    except CatalogError as exc:
        return None if is_notification else _err(req_id, -32603, "カタログ: %s" % exc)
    return None if is_notification else _ok(req_id, res)


def run_stdio_server(stdin=None, stdout=None, *, catalog: Catalog | None = None,
                     store: HandleStore | None = None) -> int:
    """EOF まで回す。壊れたフレームには -32700 を返して続ける。"""
    stdin = stdin if stdin is not None else sys.stdin.buffer
    stdout = stdout if stdout is not None else sys.stdout.buffer
    cat = catalog if catalog is not None else Catalog.load()
    store = store if store is not None else HandleStore()
    _log("ready: %d names, %d sorts, roots=%s" % (len(cat.entries), len(cat.sorts), store.roots))
    while True:
        try:
            msg = read_message(stdin)
        except FramingError as exc:
            write_message(stdout, _err(None, -32700, str(exc)))
            continue
        if msg is None:
            return 0
        resp = dispatch(msg, cat, store)
        if resp is not None:
            write_message(stdout, resp)


def demo() -> int:
    """自分を subprocess で起動し、samples → load → pipeline → inspect を叩いて表示する。

    docs/MCP.md の Quickstart はこれ。「貼る前に実行」(CONTRIBUTING)を機械化したもので、
    テストからも呼ぶ。stdout はこの関数の**外**(人向け)にしか書かない。
    """
    import subprocess
    from .catalog import ROOT
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    p = subprocess.Popen([sys.executable, "-m", "fullseye.mcp"], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, cwd=ROOT, env=env)
    seq = 0

    def call(method, **params):
        nonlocal seq
        seq += 1
        write_message(p.stdin, {"jsonrpc": "2.0", "id": seq, "method": method, "params": params})
        r = read_message(p.stdout)
        if r is None or "error" in r:
            raise RuntimeError("MCP の返事が無いか error: %r" % (r,))
        return r["result"]

    def tool(name, **a):
        r = call("tools/call", name=name, arguments=a)
        text = r["content"][0]["text"]
        links = [c["name"] for c in r["content"] if c["type"] == "resource_link"]
        print("--- %s%s" % (name, "  [isError]" if r.get("isError") else ""))
        print(text if len(text) < 1200 else text[:1200] + " …")
        if links:
            print("resource_link:", ", ".join(links))
        return r

    try:
        ini = call("initialize", protocolVersion=PROTOCOL_VERSION, capabilities={},
                   clientInfo={"name": "fullseye-demo", "version": "0"})
        print("server:", ini["serverInfo"], "protocol:", ini["protocolVersion"])
        tools = call("tools/list")["tools"]
        print("tools:", ", ".join(t["name"] for t in tools))
        s = tool("fullseye_list_samples")
        coins = next(x for x in s["structuredContent"]["samples"] if x["name"] == "coins")
        tool("fullseye_search_ops", query="threshold", limit=5)
        h = tool("fullseye_load_image", path=coins["path"])["structuredContent"]["handle"]
        pipe = tool("fullseye_pipeline", handle=h,
                    stages=[{"op": "gaussian", "a": 0.3}, {"op": "otsu"}, {"op": "count_obj"}])
        seg = pipe["structuredContent"]["handle"]
        tool("fullseye_inspect", handle=seg, vision="thumb")
        # JSON で値を注入 → ハンドル → JSON で取り出す(引数で JSON / MCP でも使う)。
        env = {"fullseye_sort": "points", "version": 1,
               "payload": {"encoding": "list", "dtype": "float64",
                           "shape": [2, 2], "data": [[1.5, 2.0], [3.25, 4.0]]}}
        jh = tool("fullseye_import_json", envelope=env)["structuredContent"]["handle"]
        tool("fullseye_export_json", handle=jh, readable=True)     # 封筒 + Markdown で返る
        # 直線群から歪み係数を推定(lines/K を JSON で渡す)。既知の樽型を回収してみせる。
        import numpy as _np
        import fullseye as _fs
        _K = _fs.intrinsic_matrix(0.95 * 200, 0.95 * 200, 99.5, 99.5)
        _true = [-0.24, 0.06, 0.0, 0.0, 0.0]
        _span = _np.linspace(12, 188, 30)
        _lines = ([_fs.distort_points(_np.column_stack([_span, _np.full(30, y)]), _K, _true).tolist()
                   for y in (40, 100, 160)]
                  + [_fs.distort_points(_np.column_stack([_np.full(30, x), _span]), _K, _true).tolist()
                     for x in (40, 100, 160)])
        tool("fullseye_estimate_distortion", lines=_lines, K=_K.tolist(), radial=2, tangential=False)
        tool("fullseye_apply", handle=h, op="count_obj")          # 型不一致 → 拒否される見本
    except RuntimeError as exc:
        print("(拒否の見本)", str(exc)[:300])
    finally:
        p.stdin.close()
        rc = p.wait(timeout=120)
    print("server exit:", rc)
    return 0 if rc == 0 else 1


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--coverage" in argv:
        # 起動せずに被覆だけ標準出力へ(人が読む用。プロトコルではない)
        print(json.dumps(Catalog.load().coverage(), ensure_ascii=False, indent=1))
        return 0
    if "--demo" in argv:
        return demo()
    return run_stdio_server()
