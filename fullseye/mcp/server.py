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
import math
import os
import pathlib
import sys
import time
from typing import Any

import numpy as np
from fssystem import get_system

from .catalog import Catalog, CatalogError, SOURCES
from .diagnose import side_by_side, stats_of, verdict_of
from .handles import HandleError, HandleStore

PROTOCOL_VERSION = "2025-06-18"
SERVER_NAME = "fullseye"
#: llmesh/mcp/validator.py の ``_MAX_RAW_BYTES`` と同じ。超えたら typed tree を落とす。
MAX_STRUCTURED_BYTES = int(get_system("mcp_response_budget"))   # import 時の既定(schema の説明用)


def _response_budget(value=None) -> int:
    """structuredContent の上限(byte)。*value* が None なら**呼ぶたびに** fssystem の
    ``mcp_response_budget`` を読む。

    ★2026-11-05(敵対的検証 第 2 巡 T4): 以前は import 時に 1 回だけ定数にして既定引数へ焼いていたので、
    ``with fssystem.system(mcp_response_budget=16000)`` が MCP の応答に効かなかった(40 kB を返した)。"""
    return int(get_system("mcp_response_budget")) if value is None else int(value)

def _execution_policy() -> dict:
    return {"status":"declared_not_applied"}
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
    "fullseye_plan": {
        "description": "型付き経路を計画する。入力と欲しい型が分かったら使い、次に fullseye_op_cards を呼ぶ。",
        "inputSchema": {"type":"object","properties":{"have":{"oneOf":[{"type":"string"},{"type":"array","items":{"type":"string"}}]},
            "want":{"type":"string"},"goal":{"type":"string","maxLength":400},
            "direction":{"type":"string","enum":["forward","backward"]},
            "pattern":{"type":"string"}},"required":["have","want"],"additionalProperties":False}},
    "fullseye_describe": {
        "description": "型・op・族を1件説明する。候補の詳細が必要なときに使い、次に fullseye_choose を呼ぶ。",
        "inputSchema":{"type":"object","properties":{"kind":{"type":"string","enum":["sort","op","family"]},"name":{"type":"string"}},
                       "required":["kind","name"],"additionalProperties":False}},
    "fullseye_choose": {
        "description": "候補を測定済み制約だけで絞る。候補名が揃った後に使い、次に fullseye_op_cards を呼ぶ。",
        "inputSchema":{"type":"object","properties":{"candidates":{"type":"array","items":{"type":"string"},"minItems":1},
                       "constraints":{"type":"object"}},"required":["candidates"],"additionalProperties":False}},
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
    "fullseye_find_ops": {
        "description": (
            "やりたいことの言葉(日本語・英語・中文(簡/繁)・한국어・Deutsch・हिन्दी)で op を探す。"
            "op の要約 6 言語・名前・HALCON 名・型と、文献層のテーマ表で人が書いた文脈(現場の言い方、日本語と英訳)を BM25 で照合し、"
            "順位つきで要約とノートの場所(文脈のある op は contexts も)を返す。"
            "各候補は loader と pipeline stage の次呼び出し骨格つき。直接 0 件なら業務表現の"
            "英語候補と型同義語で決定的に再検索し、retry_ops を同じ応答で返す。"),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 1, "maxLength": 200,
                          "description": "やりたいこと(例: ノイズ除去 / remove noise / 边缘检测)"},
                "in_sort": {"type": "string", "description": _SORT_DESC},
                "out_sort": {"type": "string", "description": _SORT_DESC},
                "limit": {"type":"integer","minimum":1,"maximum":MAX_SEARCH_LIMIT,"default":7},
                "detail": {"type":"boolean","default":False,
                           "description":"true なら候補の要約・出典を本文にも展開する"},
                # ★2026-11-05(敵対的検証 第 2 巡 D10): ハンドラは a.get("lang") を読むのに schema に無く、
                #   additionalProperties: false で渡せなかった。要約の言語(既定は問い合わせから判定)。
                "lang": {"type": "string", "enum": ["ja", "en", "zh", "tw", "ko", "de", "hi"],
                         "description": "要約の言語(省略時は問い合わせの文字から判定)"},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    "fullseye_plan_chain": {
        "description": "Plan a type-compatible op chain without execution. Use before op_cards, validate_pipeline, then pipeline.",
        "inputSchema": {"type": "object", "properties": {
            "query": {"type": "string", "minLength": 1, "maxLength": 200},
            "start_sort": {"type": "string"}, "goal_sort": {"type": "string"},
            "k": {"type": "integer", "minimum": 1, "maximum": 100},
            "max_depth": {"type": "integer", "minimum": 1, "maximum": 16}},
            "required": ["query", "start_sort", "goal_sort"], "additionalProperties": False},
    },
    "fullseye_choose_op": {
        "description": "族の候補を実測済みの事実だけで絞る。族を選んだ後に使い、次に fullseye_op_cards を呼ぶ。",
        "inputSchema": {"type": "object", "properties": {
            "family": {"type": "string"}, "constraints": {"type": "object"}},
            "required": ["family"], "additionalProperties": False},
    },
    "fullseye_required_inputs": {
        "description": "Search the transposed AND-OR op graph from a desired output to required input sort sets.",
        "inputSchema": {"type": "object", "properties": {
            "goal_sort": {"type": "string"}, "max_depth": {"type": "integer", "minimum": 0, "maximum": 16},
            "k": {"type": "integer", "minimum": 1, "maximum": 100}},
            "required": ["goal_sort"], "additionalProperties": False},
    },
    "fullseye_param_space": {
        "description": "入力文脈と実測からopのつまみ範囲を返す。op決定後に使い、次に validate_pipeline を呼ぶ。",
        "inputSchema": {"type": "object", "properties": {
            "op": {"type": "string"}, "input_context": {"type": "object"}},
            "required": ["op"], "additionalProperties": False},
    },
    "fullseye_pipeline_shape": {
        "description": "グラフから入出力形に合う構造を調べる。形が分かるときに使い、次に fullseye_plan を呼ぶ。",
        "inputSchema": {"type":"object","properties":{"input_form":{"type":"string"},"output_form":{"type":"string"}},
                       "required":["input_form","output_form"],"additionalProperties":False},
    },
    "fullseye_patterns": {
        "description": "Return a typed design-pattern skeleton whose candidates come from plan_chain.",
        "inputSchema": {"type":"object","properties":{"name":{"type":"string"},"start_sort":{"type":"string"},"goal_sort":{"type":"string"}},
                       "required":["name","start_sort","goal_sort"],"additionalProperties":False},
    },
    "fullseye_sort_guide": {
        "description": "Explain a sort as a computer-science container with graph-derived counts.",
        "inputSchema": {"type":"object","properties":{"sort":{"type":"string"}},"additionalProperties":False},
    },
    "fullseye_op_cards": {
        "description": "Return short complete op cards within a token budget; cards are never cut mid-card.",
        "inputSchema": {"type": "object", "properties": {
            "names": {"type": "array", "minItems": 1, "maxItems": 100, "items": {"type": "string"}}},
            "required": ["names"], "additionalProperties": False},
    },
    "fullseye_suggest_pipeline": {
        "description": (
            "検索候補が一意なときだけ、その op のカードと fail-closed 検証済み一段 pipeline 案を"
            "1 回で返す。曖昧なら候補を返すだけで勝手に選ばない。次に fullseye_pipeline を呼ぶ。"),
        "inputSchema": {"type":"object","properties":{
            "query":{"type":"string","minLength":1,"maxLength":200},
            "start_sort":{"type":"string"},"goal_sort":{"type":"string"}},
            "required":["query","start_sort","goal_sort"],"additionalProperties":False},
    },
    "fullseye_validate_pipeline": {
        "description": "Validate op existence, knob ranges, stage count, and type chaining without execution (fail-closed).",
        "inputSchema": {"type": "object", "properties": {
            "start_sort": {"type": "string"},
            "bindings": {"type":"object","additionalProperties":_HANDLE},
            "stages": {"type": "array", "minItems": 1, "maxItems": 64, "items": {"type": "object",
                "properties": {"op": {"type": "string", "maxLength": 120},
                               "inputs": {"type":"array","items":{"type":"string"}},
                               "params": {"type":"object"},
                               "allow_reuse":{"type":"boolean"},
                               "a": {"type": "number"}, "b": {"type": "number"}},
                "required": ["op"], "additionalProperties": False}}},
            "required": ["stages"], "additionalProperties": False},
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
        "description": "読める画像名(files=作業場所、samples=同梱)。load_image の path に渡す。",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    "fullseye_load_image": {
        "description": (
            "画像を読みハンドルを返す。path は課題のファイル名か list_samples の名前。"
            "無ければ近い名前を添えて断る。返すのは数値統計。"),
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "maxLength": 1024},
                "vision": _VISION,
                "color": {"type": "boolean", "description": "true なら (H,W,3) の color として読む"},
                "force_color": {"type": "boolean", "description": "灰色ファイルも明示的に3チャンネル color として読む"},
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    "fullseye_load_template": {
        "description": (
            "位置決め用の登録見本を画像ハンドルとして読む。返った handle は fullseye_pipeline の"
            "template_handle に必ず渡す。パス制約・画素上限・型検査は load_image と同じ。"),
        "inputSchema": {
            "type":"object","properties":{"path":{"type":"string","maxLength":1024},
            "vision":_VISION},"required":["path"],"additionalProperties":False},
    },
    "fullseye_load_stack": {
        "description": "Load several sandboxed images into one typed sequence handle for multi-frame operators.",
        "inputSchema": {"type":"object","properties":{
            "paths":{"type":"array","minItems":1,"maxItems":256,"items":{"type":"string"}},
            "sort":{"type":"string","enum":["seq<image>","images","polsweep"]},
            "color":{"type":"boolean"},"force_color":{"type":"boolean"}},
            "required":["paths","sort"],"additionalProperties":False},
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
                "params": {"type":"object", "description":
                           "op台帳で公開された名前つき物理量(例: sigma_px/window_px/radius_px)"},
                "allow_degraded": {"type": "boolean"},
                "device": {"type":"string","enum":["auto","cpu","cuda"]},
                "parity_check": {"type":"boolean"},
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
                "template_handle": _HANDLE,
                "bindings": {"type":"object","additionalProperties":_HANDLE},
                "outputs": {"type":"array","items":{"type":"string"}},
                "vision": _VISION,
                "device": {"type":"string","enum":["auto","cpu","cuda"]},
                "parity_check": {"type":"boolean"},
                "dry_run": {"type":"boolean", "description": (
                    "true なら 1 段も走らせず、経路の検査だけを返す(段ごとの path/reason、型の切れ目、"
                    "区間、切り替わり、n_transfers)。入力の形は handle の配列から取る")},
                "assume_cuda": {"type":"boolean", "description": (
                    "dry_run のとき、GPU の無い機械でも CUDA・CuPy のある機械として経路表だけで決める")},
                "stages": {
                    "type": "array", "minItems": 1, "maxItems": 64,
                    "items": {
                        "type": "object",
                            "properties": {
                                "op": {"type": "string", "maxLength": 120},
                                "inputs": {"type":"array","items":{"type":"string"}},
                                "params": {"type":"object"},
                                "allow_reuse":{"type":"boolean"},
                            "a": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                            "b": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                        },
                        "required": ["op"],
                        "additionalProperties": False,
                    },
                    "description": "[{op, params?}, …]。物理量は名前つきparamsを使う。a/bは互換用。入力の無いopだけならhandle不要",
                },
            },
            "required": ["stages"],
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
    "fullseye_write_viewer": {
        "description": (
            "PoC の結果を、自己完結した 1 枚の HTML ビューア(タブ・正直なバッジ・3-D の点群/メッシュ・"
            "2-D 動画・前後の分割・動く 3-D(kind anim3d: 物体ごとの剛体姿勢の再生 + 同じ時間軸の 2-D)・"
            "言語切り替え)にして書く。spec は fullseye.viewer_spec が作る辞書と同じ形の"
            "JSON(配列は入れ子の数値リスト)、lang は言語の配列(ja/en/zh/tw/ko/de/hi/fr、先頭が既定)。"
            "文字列は要求した全言語ぶんが要る(足りなければ欠けた鍵を並べて -32602、他言語で補わない)。"
            "バッジは passed / limit / null の 3 種。HTML は MCP のサンドボックスの作業ディレクトリに"
            "書き、resource_link で返す(任意のパスへは書かない)。"),
        "inputSchema": {
            "type": "object",
            "properties": {
                "spec": {"type": "object",
                         "description": "{id, title, subtitle, hint, tabs:[{id,label,badge,text,numbers,kind,...}], credit?}。"
                                        "kind は mesh / points / frames / split。各文字列は {言語: 文}"},
                "lang": {"type": "array", "minItems": 1, "maxItems": 8,
                         "description": "言語の配列。既定 [\"ja\"]。先頭が既定の表示言語"},
                "name": {"type": "string", "maxLength": 64,
                         "description": "ファイル名の素(英数字と _ - だけ)。既定は spec.id"},
            },
            "required": ["spec"],
            "additionalProperties": False,
        },
    },
}


# ★2026-11-09: 真値付きの課題を作る道具と、組んだ処理を真値で採点する道具(full プロファイルだけ)。
#   「LLM が組む → 型の門 → 実行」の後ろに「真値で採点 → 合否 → 直させる」を足して輪を閉じる。
#   真値はサーバ側(fullseye/mcp/tasks.py の TaskStore)に task_id で持ち、返り値には載せない。
from .tasks import FAMILIES as _TASK_FAMILIES, MAX_SEED as _TASK_MAX_SEED  # noqa: E402

TOOLS["fullseye_make_task"] = {
    "description": (
        "真値付きの課題を作る(真値はサーバが持ち、返さない)。kind=族、seed=乱数の種(同じ kind・seed・"
        "params からは同じ課題)、params=族ごとの難度つまみ(省略は既定値)。入力画像のハンドル・課題文・"
        "出力の型と単位・指標と許容範囲・task_id を返す。採点の回数は (kind, seed) ごとに数える。"
        "族: %s。次に fullseye_score_pipeline を呼ぶ。"
        % ", ".join("%s(%s)" % (k, f.field) for k, f in sorted(_TASK_FAMILIES.items()))),
    "inputSchema": {
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": sorted(_TASK_FAMILIES)},
            "seed": {"type": "integer", "minimum": 0, "maximum": _TASK_MAX_SEED},
            "params": {"type": "object",
                       "description": "族ごとの難度つまみ(真値を決めない量だけ)。知らない名前・範囲外は -32602"},
        },
        "required": ["kind", "seed"],
        "additionalProperties": False,
    },
}
TOOLS["fullseye_score_pipeline"] = {
    "description": (
        "fullseye_make_task の課題を、組んだ処理(fullseye_pipeline と同じ形の stages)で解かせて真値で採点する。"
        "入力は課題の画像に固定(handle は渡さない)。実行の前に型の門を通し、最終段の出力を族ごとの指標で"
        "真値と比べ、指標ごとの誤差の大きさ・許容範囲・合否と外れ方の説明を返す(真値と誤差の符号は返さない)。"
        "段が読めるのは have:<課題の入力の型> と stage:N だけ(他のハンドルは foreign_input で断る)。"
        "例外・型の不一致・NaN/空/定数の出力・知らない/期限切れの task_id は合格を返さず reason を書く。"
        "feedback=detailed/coarse/pass_fail で返す細かさを選ぶ(サーバの上限まで)。"),
    "inputSchema": {
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "maxLength": 64,
                        "description": "fullseye://task/<16 hex>。fullseye_make_task が返す"},
            "stages": TOOLS["fullseye_pipeline"]["inputSchema"]["properties"]["stages"],
            "feedback": {"type": "string", "enum": ["detailed", "coarse", "pass_fail"],
                         "description": "detailed=誤差の大きさ / coarse=許容の何倍かの段階 / pass_fail=合否だけ"},
        },
        "required": ["task_id", "stages"],
        "additionalProperties": False,
    },
}


class ArgError(ValueError):
    """入力スキーマ違反。JSON-RPC の -32602 に写す。"""

    def __init__(self, message: str, *, data: dict | None = None):
        super().__init__(message)
        self.data = data


MAX_SCHEMA_DEPTH = 64


def _validate(schema: dict, args: Any) -> dict:
    """Recursively validate the JSON-schema subset used by MCP tools."""
    def check(spec, value, path, depth=0):
        if depth > MAX_SCHEMA_DEPTH:
            raise ArgError("%s exceeds maximum nesting depth %d" % (path, MAX_SCHEMA_DEPTH))
        if "oneOf" in spec:
            matches = 0
            for choice in spec["oneOf"]:
                try:
                    check(choice, value, path, depth); matches += 1
                except ArgError:
                    pass
            if matches != 1:
                raise ArgError("%s は oneOf のどれか一つに一致する必要がある" % path)
            return
        kind = spec.get("type")
        predicates = {
            "object": lambda x: isinstance(x, dict), "array": lambda x: isinstance(x, list),
            "string": lambda x: isinstance(x, str), "boolean": lambda x: isinstance(x, bool),
            "integer": lambda x: isinstance(x, int) and not isinstance(x, bool),
            "number": lambda x: isinstance(x, (int, float)) and not isinstance(x, bool),
        }
        if kind in predicates and not predicates[kind](value):
            labels={"object":"オブジェクト","array":"配列","string":"文字列","boolean":"真偽値",
                    "integer":"整数","number":"数"}
            raise ArgError("%s は%sでなければならない: %s" % (path,labels[kind],type(value).__name__))
        if isinstance(value, float) and not math.isfinite(value):
            raise ArgError("%s は有限値でなければならない (must be finite)" % path)
        if kind == "object":
            props = spec.get("properties", {}); additional = spec.get("additionalProperties", True)
            extra = set(value) - set(props)
            if additional is False and extra:
                raise ArgError("%s に知らない引数がある: %s" % (path, sorted(extra)))
            for name in spec.get("required", ()):
                if name not in value:
                    raise ArgError("%s.%s は必須" % (path, name))
            for name, item in value.items():
                child = props.get(name, additional if isinstance(additional, dict) else {})
                check(child, item, "%s.%s" % (path, name), depth + 1)
        elif kind == "array":
            if len(value) < spec.get("minItems", 0):
                raise ArgError("%s は%d 段以上" % (path,spec["minItems"]))
            if len(value) > spec.get("maxItems", 10**9):
                raise ArgError("%s は%d以下" % (path,spec["maxItems"]))
            for i, item in enumerate(value):
                check(spec.get("items", {}), item, "%s[%d]" % (path, i), depth + 1)
        elif not kind:
            if isinstance(value, dict):
                for name, item in value.items(): check({}, item, "%s.%s" % (path, name), depth + 1)
            elif isinstance(value, list):
                for i, item in enumerate(value): check({}, item, "%s[%d]" % (path, i), depth + 1)
        if "enum" in spec and value not in spec["enum"]: raise ArgError("%s は列挙値のどれか" % path)
        if "minimum" in spec and value < spec["minimum"]: raise ArgError("%s は最小値以上" % path)
        if "maximum" in spec and value > spec["maximum"]: raise ArgError("%s は最大値以下" % path)
        if "minLength" in spec and len(value) < spec["minLength"]: raise ArgError("%s is too short" % path)
        if "maxLength" in spec and len(value) > spec["maxLength"]: raise ArgError("%s は指定文字以下" % path)
    check(schema, args, "arguments")
    return args


# --------------------------------------------------------------------------- #
# 転送(llmesh から移植)                                                        #
# --------------------------------------------------------------------------- #
class FramingError(ValueError):
    """フレームは来たが JSON として読めない(EOF とは区別する)。"""


#: 枠の種類。``FRAMING_LINES`` = MCP の stdio の決まり(1 行 1 通、改行区切りの JSON)、
#: ``FRAMING_HEADERS`` = Content-Length 枠(LSP 風。1.1.0 までの唯一の形で、自前のクライアントが使う)。
FRAMING_LINES = "lines"
FRAMING_HEADERS = "content-length"

#: 改行区切りの 1 通の上限(バイト)。これを超える行は読み捨てずに断る(メモリを相手に握らせない)。
MAX_LINE_BYTES = 64 * 1024 * 1024


def _loads_body(body: bytes):
    """本文を JSON として読む。読めない・深すぎる入れ子は FramingError(→ -32700)。"""
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise FramingError("本文が JSON でない: %s" % exc) from exc
    except RecursionError as exc:
        # ★2026-11-13: 3,000 段の入れ子 1 通でサーバが落ちていた(json.loads の RecursionError を受けていなかった)。
        raise FramingError("本文の入れ子が深すぎる") from exc
    except UnicodeDecodeError as exc:
        raise FramingError("本文が UTF-8 でない: %s" % exc) from exc


def read_framed(stdin) -> tuple[object, str] | None:
    """1 通を読み、``(本文, 枠の種類)`` を返す。EOF は None、壊れた 1 通は FramingError。

    ★2026-11-13: MCP の stdio の決まりは「1 行 1 通の JSON(改行区切り)」で、公式のクライアント
    (Claude Code / Claude Desktop / mcp の Python SDK)はこの形で話す。1.1.0 までは Content-Length 枠
    しか読まず、公式のクライアントの initialize に応えなかった。先頭の行が ``{`` か ``[`` で始まれば
    改行区切り、そうでなければ Content-Length 枠として読む(両方に応える)。

    本文は dict とは限らない(``null`` や配列も JSON として正しい)。型の検査は呼び出し側が行う ——
    ここで None を返すのは EOF だけ(``null`` の本文を EOF と取り違えて黙って終了していた)。"""
    headers: dict[bytes, bytes] = {}
    while True:
        raw = stdin.readline(MAX_LINE_BYTES + 1)
        if not raw:
            return None
        line = raw.strip()
        if not headers and line[:1] in (b"{", b"["):
            if len(raw) > MAX_LINE_BYTES and not raw.endswith(b"\n"):
                raise FramingError("1 通が長すぎる(上限 %d バイト)" % MAX_LINE_BYTES)
            return _loads_body(line), FRAMING_LINES
        if not line:
            if not headers:
                continue                      # 通と通の間の空行は読み飛ばす(改行区切りの相手が余分に送る事がある)
            break
        if b":" in line:
            k, _, v = line.partition(b":")
            headers[k.strip().lower()] = v.strip()
    # ★2026-10-11: Content-Length が無い / 0 のフレームで None(= EOF)を返し、サーバが
    # 黙って終了していた。EOF は「ヘッダを 1 行も読めない」ときだけで、壊れたフレームは
    # FramingError(→ -32700)にしてループを続ける。
    if b"content-length" not in headers:
        raise FramingError("Content-Length ヘッダが無い")
    try:
        length = int(headers[b"content-length"])
    except ValueError as exc:
        raise FramingError("Content-Length が整数でない") from exc
    if length <= 0:
        raise FramingError("Content-Length が正でない(%d)" % length)
    body = stdin.read(length)
    if len(body) < length:
        return None
    return _loads_body(body), FRAMING_HEADERS


def read_message(stdin) -> dict | None:
    """1 通を読む(枠の種類は返さない、従来の入口)。EOF は None、壊れた 1 通は FramingError。

    ★llmesh 版は両方 None にしていた。それだと「相手が切った」と「相手が壊れた JSON を
    送った」が同じに見え、後者に -32700 を返せない。"""
    got = read_framed(stdin)
    if got is None:
        return None
    msg, _framing = got
    if msg is None:
        raise FramingError("本文が JSON の null(要求でも通知でもない)")
    return msg


def write_message(stdout, msg: dict, *, framing: str = FRAMING_HEADERS) -> None:
    """1 通を書く。``framing`` が ``FRAMING_LINES`` なら 1 行の JSON + 改行(MCP の stdio の決まり)、
    既定は Content-Length 枠。**JSON に無い NaN / ±inf のトークンは決して書かない**(fail-closed)。

    ★2026-11-05(敵対的検証): ``json.dumps`` の既定 ``allow_nan=True`` は ``NaN`` / ``Infinity`` を
    そのまま出し、厳密な JSON の相手には壊れた本文になる。非有限の値が混ざった応答は、同じ id の
    -32603(内部エラー)に置き換えて書く(値を黙って null にもしない)。"""
    try:
        body = json.dumps(msg, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except ValueError as exc:
        _log("write_message", "non-finite value in response refused: %s" % exc)
        body = json.dumps(_err(msg.get("id") if isinstance(msg, dict) else None, -32603,
                               "内部エラー: 応答に JSON で表せない非有限の値(NaN / inf)が含まれていた"),
                          ensure_ascii=False).encode("utf-8")
    if framing == FRAMING_LINES:
        # json.dumps は改行をエスケープするので、本文に生の改行は入らない(1 行 1 通が保たれる)。
        stdout.write(body + b"\n")
    else:
        stdout.write(b"Content-Length: " + str(len(body)).encode() + b"\r\n\r\n")
        stdout.write(body)
    stdout.flush()


def _ok(req_id, result) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _err(req_id, code: int, message: str, *, data: dict | None = None) -> dict:
    error = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": req_id, "error": error}


def _log(*parts) -> None:
    """監査は stderr へ。stdout はプロトコル専用。"""
    print("[fullseye-mcp]", *parts, file=sys.stderr, flush=True)


# --------------------------------------------------------------------------- #
# tool の結果                                                                   #
# --------------------------------------------------------------------------- #
def _structured_summary(value: dict) -> str:
    """Make structured results useful to text-only MCP clients in at most 3 lines."""
    ok = value.get("ok", value.get("valid", value.get("verdict", "ok") not in ("failed", "error")))
    reason = value.get("reason") or value.get("verdict")
    first = ("ok" if ok else "error") + ((": " + str(reason)) if reason else "")
    lines = [first]
    count_parts = []
    for key in ("total", "returned", "count"):
        if key in value:
            count_parts.append("%s=%s" % (key, value[key]))
    for key in ("ops", "plans", "stages", "samples"):
        rows = value.get(key)
        if isinstance(rows, list):
            count_parts.append("%s=%d" % (key, len(rows)))
            names = [row.get("name") if isinstance(row, dict) else row for row in rows[:3]]
            names = [str(name) for name in names if name]
            if names:
                count_parts.append("top=" + ",".join(names))
            break
    if count_parts:
        lines.append(" ".join(count_parts))
    handle = value.get("handle")
    sort = value.get("sort") or value.get("out_sort")
    if handle or sort:
        lines.append(" ".join(x for x in (("handle=" + str(handle)) if handle else "",
                                           ("sort=" + str(sort)) if sort else "") if x))
    return "\n".join(lines[:3])


def tool_result(text: str, structured: dict | None, *, links: list | None = None,
                max_structured_bytes: int | None = None) -> dict:
    """本文(text)は必ず付け、typed tree は上限内なら付ける。超えたら**落としたと書く**。"""
    max_structured_bytes = _response_budget(max_structured_bytes)
    if structured is not None and get_system("mcp_body_mode") == "compact" and text.lstrip().startswith(("{","[")):
        text = _structured_summary(structured)
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
    if structured is not None and get_system("mcp_body_mode") == "compact" and text.lstrip().startswith(("{", "[")):
        text = _structured_summary(structured)
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
    meta = store.load(a["path"], color=bool(a.get("color", False)),
                      force_color=bool(a.get("force_color", False)))
    _, arr = store.get(meta["handle"])
    _enforce_pixel_limit(arr, "load_image")
    st, vd = _describe(meta, arr)
    links = _maybe_thumb(store, meta, None, arr, vision=a.get("vision", "auto"),
                         escalate=vd["escalate"], quantity=False, tag="load")
    structured = {"handle": meta["handle"], "sort": meta["sort"], "shape": meta["shape"],
                  "dtype": meta["dtype"], "provenance": meta["provenance"],
                  "stats": st, **vd, "dedup": bool(meta.get("dedup", False))}
    if meta.get("note"):
        structured["note"] = meta["note"]
    text = "%s  sort=%s\n%s" % (meta["handle"], meta["sort"], _stats_line(st, vd))
    return tool_result(text, structured, links=links)


def _load_template(a: dict, store: HandleStore) -> dict:
    """Load a 2-D registration template without hidden global registration."""
    loaded = _load_image({"path": a["path"], "vision": a.get("vision", "auto")}, store)
    structured = loaded["structuredContent"]
    if structured["sort"] != "image" or len(structured["shape"]) != 2:
        raise ArgError("template must be a 2-D grayscale image; got sort=%s shape=%s" %
                       (structured["sort"], structured["shape"]))
    structured["role"] = "template"
    structured["next_call"] = ("fullseye_pipeline(handle=<scene_handle>, "
                               "template_handle=%s, stages=[{op:ncc_locate}])" %
                               structured["handle"])
    loaded["content"][0]["text"] += "\nrole=template; pass this handle as pipeline.template_handle"
    return loaded

def _load_stack(a: dict, store: HandleStore) -> dict:
    arrays, provenance, notes = [], [], []
    pixels = 0; limit = int(get_system("mcp_stack_max_pixels"))
    for path in a["paths"]:
        meta = store.load(path, color=bool(a.get("color", False)),
                          force_color=bool(a.get("force_color", False)))
        _, arr = store.get(meta["handle"])
        arrays.append(arr); provenance.extend(meta["provenance"])
        if meta.get("note"):
            notes.append(meta["note"])
        pixels += int(np.asarray(arr).size)
        if pixels > limit:
            raise ArgError("load_stack total pixels %d exceeds limit %d" % (pixels,limit))
    try:
        stack = np.stack(arrays)
    except ValueError as exc:
        raise ArgError("stack images must have one shape: %s" % exc) from None
    from fullseye.opsearch import normalize_sort
    sort = normalize_sort(a["sort"])
    meta = store.put(stack, sort=sort, provenance=provenance + [{"load_stack":len(arrays)}])
    if notes:
        meta["note"] = notes[0] if len(notes) == len(arrays) else "%d/%d files were gray and read as image" % (len(notes), len(arrays))
    return tool_result("%s sort=%s shape=%s" % (meta["handle"],sort,meta["shape"]), meta)


def _array_pixels(value) -> int:
    """Count ndarray elements in a possibly nested operation result once each."""
    seen: set[int] = set()

    def count(item) -> int:
        oid = id(item)
        if oid in seen:
            return 0
        if isinstance(item, np.ndarray):
            seen.add(oid)
            return int(item.size)
        if isinstance(item, dict):
            seen.add(oid)
            return sum(count(v) for v in item.values())
        if isinstance(item, (list, tuple)):
            seen.add(oid)
            return sum(count(v) for v in item)
        return 0

    return count(value)


def _value_nbytes(value) -> int:
    """Bounded-accounting size for a pipeline intermediate, including nested arrays."""
    seen: set[int] = set()

    def size(item) -> int:
        oid = id(item)
        if oid in seen:
            return 0
        if isinstance(item, np.ndarray):
            seen.add(oid)
            return int(item.nbytes)
        if isinstance(item, dict):
            seen.add(oid)
            return sum(len(str(k).encode("utf-8")) + size(v) for k, v in item.items())
        if isinstance(item, (list, tuple)):
            seen.add(oid)
            return sum(size(v) for v in item)
        if isinstance(item, str):
            return len(item.encode("utf-8"))
        if isinstance(item, (bytes, bytearray)):
            return len(item)
        return 8

    return size(value)


def _enforce_pixel_limit(value, where: str) -> None:
    pixels = _array_pixels(value)
    limit = int(get_system("mcp_stack_max_pixels"))
    if pixels > limit:
        raise ArgError("%s output pixels %d exceeds limit %d" % (where, pixels, limit))


def _resolve_op(name: str, cat: Catalog, *, stage: int | None = None):
    """registry 層の op に解決する。無ければ近い名前を添えて拒否(黙って倒さない)。"""
    import ops
    from fullseye.opsearch import mcp_unavailable_text
    op = ops._BY_NAME.get(name)
    if op is None:
        where = "段 %d: " % stage if stage else ""
        # ★2026-11-13: 台帳にある op にも「registry 層に無い」とだけ返し、「近い名前」に同じ名前を出していた。
        why = mcp_unavailable_text(name)
        near = [x for x in cat.nearest(name) if x != name]
        raise ArgError("%sfullseye_apply で実行できる op ではない: %r(registry 層に無い)。%s%s"
                       % (where, name, (why + "。") if why else "", ("近い名前: %s" % near) if near else ""))
    from fullseye.opsearch import _graph
    edge = next((e for e in _graph()["edges"] if e["op"] == name), None)
    if edge is None or not edge.get("verified_executable"):
        where = "stage %d: " % stage if stage else ""
        reason = (edge or {}).get("not_executable_in_mcp", "not verified")
        raise ArgError("%sop is not verified for MCP execution: %r (%s)" % (where, name, reason))
    return op


def _check_sort(op, cur_sort: str, *, stage: int | None = None, prev: str = "ハンドル") -> None:
    """型契約を境界で守る。in_sort が合わなければ走らせない。"""
    if op.in_sort in ("any", cur_sort):
        return
    where = "(段 %d)" % stage if stage else ""
    raise ArgError("型の不一致%s: %s は %s を受けるが、%s は %s(変換 op を先に挟むこと)"
                   % (where, op.name, op.in_sort, prev, cur_sort))


def _out_sort(op, in_sort: str | None) -> str:
    """op が出す型。``out_sort == "any"``(素通し)は受けた型を保つ(engine._thread_sort と同じ)。"""
    if op.out_sort == "any" and in_sort:
        return in_sort
    return op.out_sort


def _resolve_pipeline_ref(ref: str, values: dict, store: HandleStore | None):
    """Resolve one pipeline reference for both validation and execution."""
    if not isinstance(ref, str):
        raise ArgError("pipeline reference must be a string: %r" % (ref,))
    if ref in values:
        return values[ref]
    if ref.startswith("fullseye://") and store is not None:
        return store.get(ref)
    raise ArgError("unknown pipeline reference: %s" % ref)


def physical_parameter_catalog() -> dict[str, dict[str, dict]]:
    """Named physical controls, mechanically enumerated from param_specs' op ledger."""
    from param_specs import _mcp_physical_param_specs
    return _mcp_physical_param_specs()


def _physical_value_to_knob(op: str, name: str, value: Any, spec: dict) -> float:
    """Validate a displayed physical value before converting it to an a/b knob."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ArgError("%s.%s must be a finite number in %s %s" %
                       (op, name, spec.get("choices") or [spec.get("min"), spec.get("max")],
                        spec.get("unit") or ""))
    shown = float(value)
    choices = spec.get("choices")
    if choices:
        allowed = [float(x) for x in choices]
        if shown not in allowed:
            raise ArgError("%s.%s=%s is outside the documented choices %s %s; values are not rounded" %
                           (op, name, value, allowed, spec.get("unit") or ""))
        # 等幅でない choice(param_specs の half_then_thirds など)でも狂わないよう、param_specs の逆写像を通す(display = choice の添字)
        from param_specs import display_to_knob
        return display_to_knob(spec, allowed.index(shown))
    lo, hi = float(spec["min"]), float(spec["max"])
    if shown < lo or shown > hi:
        raise ArgError("%s.%s=%s is outside the documented range [%s, %s] %s; values are not clipped" %
                       (op, name, value, lo, hi, spec.get("unit") or ""))
    if spec.get("kind") == "int" and shown != round(shown):
        raise ArgError("%s.%s=%s must be an integer in [%s, %s] %s" %
                       (op, name, value, int(lo), int(hi), spec.get("unit") or ""))
    from param_specs import display_to_knob
    return display_to_knob(spec, shown)


def _named_knobs(op: str, params: dict | None, a: float = 0.5,
                 b: float = 0.5) -> tuple[float, float, dict]:
    """Resolve named physical params to knobs; unknown/conflicting values fail closed."""
    params = dict(params or {})
    catalog = physical_parameter_catalog()
    declared = catalog.get(op, {})
    named = {key: value for key, value in params.items() if key in declared}
    unknown = sorted(set(params) - set(declared))
    if unknown:
        raise ArgError("%s has unknown named parameters %s; physical parameters are %s" %
                       (op, unknown, sorted(declared)))
    if not named:
        return float(a), float(b), {}
    knobs = {"a": float(a), "b": float(b)}
    used = {}
    for name, value in named.items():
        spec = declared[name]
        knob = spec["knob"]
        knobs[knob] = _physical_value_to_knob(op, name, value, spec)
        used[name] = {"value": value, "unit": spec.get("unit"), "knob": knob,
                      "range": spec.get("choices") or [spec.get("min"), spec.get("max")]}
    return knobs["a"], knobs["b"], used


#: 数 1 個を受ける入力(``measurement``)に繋げる型。registry の計測 op は ``feature`` で数を返す。
_SCALAR_INPUT_SORTS = frozenset({"measurement", "scalar"})
_SCALAR_COMPATIBLE_SORTS = frozenset({"measurement", "scalar", "feature"})
#: 台帳 op の文字列の引数に書ける文字(パスの区切り・ドライブ名・親フォルダを書けない)。
_ISOLATED_TEXT_RX = __import__("re").compile(r"[\w .+\-()%,=µ°]{1,80}")
_ISOLATED_MAX_ELEMENTS = 4096
_ISOLATED_MAX_DEPTH = 4
#: 画像の列の型。MCP の handle では (T,H,W) の配列、台帳 op の引数と返り値では 2-D 配列の list。
_SEQUENCE_SORTS = frozenset({"seq<image>", "images"})
#: ラベルの型。台帳 op は整数の配列だけを受ける(実数のラベルは閾値の前の画像の取り違えとして断る)。
_LABEL_SORTS = frozenset({"labels", "labels2d"})


def _integral_labels(value):
    """MCP の handle に実数で入ったラベル(``fullseye_import_json`` などは実数で持つ)を整数にする。

    全部が有限の整数値のときだけ写す。小数を含む配列はそのまま渡し、op 自身の検査に断らせる(丸めない)。"""
    if isinstance(value, np.ndarray) and value.dtype.kind == "f" and value.size and np.isfinite(value).all():
        rounded = np.rint(value)
        if np.array_equal(rounded, value) and np.abs(rounded).max() < 2 ** 31:
            return rounded.astype(np.int32)
    return value


def _stack_sequence(value, op: str):
    """台帳 op が返した画像の列(2-D 配列の list)を、MCP の handle の形 (T,H,W) にまとめる。

    形の揃わない列・2-D でない要素は、まとめずにそのまま返す(後の出力の検査が invalid_output で断る)。"""
    if isinstance(value, (list, tuple)) and value and all(
            isinstance(frame, np.ndarray) and frame.ndim == 2 and frame.dtype.kind in "biuf"
            and frame.shape == value[0].shape for frame in value):
        return np.stack([np.asarray(frame, dtype=np.float64) for frame in value])
    return value


def _is_isolated(edge: dict | None) -> bool:
    """隔離した子プロセス(:mod:`fullseye.mcp.opworker`)で走らせる台帳 op か。"""
    return bool(edge) and (edge.get("executor") or {}).get("isolation") == "worker"


def _isolated_limits() -> dict:
    """隔離実行 1 回の上限(呼ぶたびに fssystem を読む)。"""
    return {"time_limit_s": float(get_system("mcp_op_time_limit_s")),
            "memory_limit_bytes": int(get_system("mcp_op_memory_limit_bytes")),
            "max_pixels": int(get_system("mcp_stack_max_pixels"))}


def _check_isolated_param(op: str, row: dict, value) -> str | None:
    """台帳 op の引数 1 個を、台帳の仕様(``opassist.param_spec`` 由来の kind / choices / 単位)で検査する。

    問題が無ければ None、あれば理由の文。信頼境界: 数は有限、列は 4096 要素・4 段まで、文字列は短い名前だけ
    (パスを書けない)。値は丸めず・切り詰めず、合わなければ断る。"""
    kind = row.get("kind") or "number"
    unit = (" [%s]" % row["unit"]) if row.get("unit") else ""
    name = "%s.%s" % (op, row["name"])
    if value is None:
        if row.get("required") or row.get("default", None) is not None:
            return "%s must not be null (omit it to use the default %r)" % (name, row.get("default"))
        return None
    if row.get("name") == "device" and value != "cpu":
        # GPU のメモリは子の見張り(作業プロセスのメモリの増分)では縛れないので、MCP からは CPU だけ
        return "%s=%r: the MCP op worker runs on the CPU only (omit it or pass \"cpu\")" % (name, value)
    if kind == "choice":
        choices = list(row.get("choices") or [])
        return None if value in choices else "%s=%r is not one of %s" % (name, value, choices)
    if kind == "bool":
        return None if isinstance(value, bool) else "%s must be true or false" % name
    if kind == "text":
        if isinstance(value, str) and _ISOLATED_TEXT_RX.fullmatch(value) and ".." not in value:
            return None
        return ("%s must be a short name (letters, digits, space, _ . + - ( ) %% , =; at most 80 characters); "
                "default %r" % (name, row.get("default")))
    count = [0]

    def numeric(item, depth) -> bool:
        if isinstance(item, bool):
            return False
        if isinstance(item, (int, float)):
            count[0] += 1
            if kind == "int" and not (isinstance(item, int) or float(item).is_integer()):
                return False
            return math.isfinite(float(item)) and abs(float(item)) <= 1e15 and count[0] <= _ISOLATED_MAX_ELEMENTS
        if isinstance(item, list) and depth < _ISOLATED_MAX_DEPTH:
            return all(numeric(x, depth + 1) for x in item)
        return False

    if numeric(value, 0):
        return None
    return ("%s must be a finite %s%s, or a list of them (at most %d elements, %d levels); default %r"
            % (name, "integer" if kind == "int" else "number", unit, _ISOLATED_MAX_ELEMENTS, _ISOLATED_MAX_DEPTH,
               row.get("default")))


def _scalar_of(value, where: str) -> float:
    """数 1 個を受ける入力へ渡す値を、有限の数 1 個として取り出す(合わなければ ArgError)。"""
    if isinstance(value, dict) and set(value) >= {"value"} and len(value) <= 3:
        value = value["value"]
    arr = np.asarray(value)
    if arr.dtype.kind not in "biuf" or arr.size != 1:
        raise ArgError("%s must be one number; got %s with %d element(s)" % (where, arr.dtype, arr.size))
    number = float(arr.reshape(-1)[0])
    if not math.isfinite(number):
        raise ArgError("%s must be finite" % where)
    return number


_UNIT_SUFFIXES = (("_per_mm", "1/mm"), ("_um", "µm"), ("_nm", "nm"), ("_mm", "mm"), ("_cm", "cm"), ("_deg", "°"),
                  ("_px", "px"), ("_hz", "Hz"), ("_ms", "ms"), ("_s", "s"), ("_rad", "rad"))


def _unit_of_key(key: str) -> str | None:
    """結果の表の鍵の名前から単位を読む(``height_mm`` → mm、``mm_per_px`` → mm/px)。名前に無ければ None。"""
    if "_per_" in key:
        head, _, tail = key.rpartition("_per_")
        num = head.rsplit("_", 1)[-1]
        if num in ("mm", "um", "nm", "px", "deg", "cm", "m", "lp", "cycles") and tail.isalpha():
            return "%s/%s" % (num, tail)
    for suffix, unit in sorted(_UNIT_SUFFIXES, key=lambda kv: -len(kv[0])):
        if key.endswith(suffix):
            return unit
    return None


def _array_field_sort(arr: np.ndarray) -> str:
    """表の中の配列に付ける型(次の pipeline の handle に渡せるように)。決められない形は ``any``。"""
    if arr.dtype.kind == "f" and arr.ndim == 2:
        return "image"
    if arr.dtype.kind == "f" and arr.ndim == 3 and arr.shape[-1] == 3:
        return "color"
    if arr.dtype.kind == "f" and arr.ndim == 1:
        return "signal"
    return "any"


def _summarize_value(value, store: HandleStore, *, provenance: list, max_bytes: int = 6000) -> dict:
    """台帳 op の結果(表・数・配列の木)を、上限つきの JSON の要約にする。

    返り値 ``{"value": 木, "units": {鍵: 単位}, "handles": [{key, handle, sort, shape}], "truncated": bool}``。
    数は有限だけを書く(非有限は ``null`` にして ``non_finite`` に鍵を残す)。17 要素以上の配列は値を載せず、
    形・最小・最大とハンドル(2-D の実数配列は ``image`` なので、次の pipeline の handle に渡せる)を返す。"""
    units: dict[str, str] = {}
    handles: list[dict] = []
    non_finite: list[str] = []
    state = {"rows": 10, "keys": 48, "truncated": False}

    def conv(item, key: str, depth: int):
        if isinstance(item, np.generic):
            item = item.item()
        if item is None or isinstance(item, (bool, str)):
            return item if not isinstance(item, str) or len(item) <= 200 else item[:200] + "…"
        if isinstance(item, int):
            return item
        if isinstance(item, float):
            if not math.isfinite(item):
                non_finite.append(key)
                return None
            return item
        if isinstance(item, complex):
            return {"re": conv(item.real, key, depth), "im": conv(item.imag, key, depth)}
        if isinstance(item, np.ndarray):
            if item.size <= 16 and item.dtype.kind in "biuf":
                return conv(item.tolist(), key, depth)
            desc: dict = {"array": list(item.shape), "dtype": str(item.dtype)}
            if item.size and item.dtype.kind in "biuf":
                finite = item[np.isfinite(item)] if item.dtype.kind == "f" else item
                if finite.size:
                    desc["min"], desc["max"] = float(finite.min()), float(finite.max())
            sort = _array_field_sort(item)
            try:
                meta = store.put(item, sort=sort, provenance=provenance + [{"field": key}])
                desc["handle"], desc["sort"] = meta["handle"], sort
                handles.append({"key": key, "handle": meta["handle"], "sort": sort, "shape": list(item.shape)})
            except HandleError:
                desc["handle"] = None
            return desc
        if isinstance(item, dict):
            if depth >= 6:
                state["truncated"] = True
                return {"_omitted": "nested table"}
            out = {}
            for n, (k, v) in enumerate(item.items()):
                k = str(k)
                if n >= state["keys"]:
                    out["_omitted_keys"] = len(item) - n
                    state["truncated"] = True
                    break
                unit = _unit_of_key(k)
                if unit:
                    units[k] = unit
                out[k] = conv(v, k, depth + 1)
            return out
        if isinstance(item, (list, tuple)):
            if depth >= 6:
                state["truncated"] = True
                return ["…"]
            rows = [conv(v, key, depth + 1) for v in item[:state["rows"]]]
            if len(item) > state["rows"]:
                rows.append({"_omitted_rows": len(item) - state["rows"]})
                state["truncated"] = True
            return rows
        state["truncated"] = True
        return "<%s>" % type(item).__name__

    for rows, keys in ((10, 48), (4, 24), (2, 12)):
        state.update(rows=rows, keys=keys, truncated=False)
        units.clear(); del handles[:]; del non_finite[:]
        tree = conv(value, "value", 0)
        if len(json.dumps(tree, ensure_ascii=False).encode("utf-8")) <= max_bytes:
            break
    else:
        tree = {"_omitted": "result is larger than %d bytes; read it with fullseye_inspect / fullseye_export_json "
                            "on value_handle" % max_bytes}
        state["truncated"] = True
    out = {"value": tree, "units": dict(units), "handles": list(handles), "truncated": bool(state["truncated"])}
    if non_finite:
        out["non_finite"] = sorted(set(non_finite))
    return out


def _summary_lines(summary: dict, limit: int = 40) -> list[str]:
    """:func:`_summarize_value` の要約を、人と文字だけのクライアントが読める行にする(単位つき)。"""
    units = summary.get("units", {})
    lines: list[str] = []

    def cell(v) -> str:
        if isinstance(v, float):
            return "%.6g" % v
        if isinstance(v, dict) and "array" in v:
            rng = (" min=%.4g max=%.4g" % (v["min"], v["max"])) if "min" in v else ""
            return "array shape=%s%s%s" % (v["array"], rng,
                                           (" handle=%s sort=%s" % (v["handle"], v.get("sort"))) if v.get("handle") else "")
        if isinstance(v, (dict, list)):
            return json.dumps(v, ensure_ascii=False)[:160]
        return str(v)

    tree = summary.get("value")
    if isinstance(tree, dict):
        for key, v in tree.items():
            unit = (" " + units[key]) if key in units and not isinstance(v, (dict, list)) else ""
            if isinstance(v, list) and v and all(isinstance(r, dict) for r in v):
                lines.append("%s (%d rows shown):" % (key, sum("_omitted_rows" not in r for r in v)))
                for n, row in enumerate(v[:5], 1):
                    if "_omitted_rows" in row:
                        lines.append("  … +%d rows" % row["_omitted_rows"])
                    else:
                        lines.append("  %d. %s" % (n, ", ".join(
                            "%s=%s%s" % (k, cell(x), (" " + units[k]) if k in units else "")
                            for k, x in list(row.items())[:8])))
            else:
                lines.append("%s = %s%s" % (key, cell(v), unit))
    else:
        lines.append("value = %s" % cell(tree))
    if summary.get("truncated"):
        lines.append("(要約は一部を省いた。全体は value_handle を fullseye_inspect / fullseye_export_json で読む)")
    return lines[:limit]


def _op_summary(name: str) -> str | None:
    """op の 1 行の説明(OP_CARDS の summary)。結果に「何を計算したか」を添えるのに使う。"""
    try:
        from fullseye.opsearch import PKG_CARDS, _load_data
        key = "cards_by_name"
        cache = _op_summary.__dict__
        if key not in cache:
            cache[key] = {c["name"]: c.get("summary") for c in _load_data(PKG_CARDS)["ops"]}
        return cache[key].get(name)
    except (FileNotFoundError, ValueError, KeyError):
        return None


def _run_isolated_stage(edge: dict, args: list, params: dict):
    """隔離した子プロセスで台帳 op を 1 つ走らせる。``(値, 情報)`` を返す。上限と失敗は例外で返す。"""
    from .opworker import run_isolated
    executor = edge["executor"]
    limits = _isolated_limits()
    for arg in args:
        _enforce_pixel_limit(arg, "input of %s" % edge["op"])
    job = {"ledger_module": executor["ledger_module"], "ledger_table": executor["ledger_table"],
           "key": executor["key"], "data_names": list(executor.get("data_names") or [])}
    _log("isolated", edge["op"], "start", "time<=%.0fs" % limits["time_limit_s"],
         "memory<=%dMiB" % (limits["memory_limit_bytes"] >> 20))
    value, info = run_isolated(job, args, params, time_limit_s=limits["time_limit_s"],
                               max_rss=limits["memory_limit_bytes"])
    _log("isolated", edge["op"], "done", "%.2fs" % info.get("elapsed_s", 0.0))
    return value, dict(info, **limits)


def _sort_mismatch_fixes(actual: str, expected: str) -> list[dict]:
    """Concrete, bounded repair candidates for a structured type mismatch."""
    fixes = []
    if expected in ("image", "color"):
        fixes.append({"kind":"loader", "tool":"fullseye_load_image",
                      "call":"fullseye_load_image(path=..., color=%s)" % (expected == "color")})
    elif expected in ("seq<image>", "polsweep"):
        fixes.append({"kind":"loader", "tool":"fullseye_load_stack",
                      "call":"fullseye_load_stack(paths=[...], sort=%r)" % expected})
    try:
        from fullseye.opsearch import plan
        route = plan(actual, expected, constraints={"k":1, "max_depth":3,
                     "max_expansions":1000, "timeout_ms":200})
        if route.get("ok") and route.get("plans"):
            ops = route["plans"][0]["ops"]
            fixes.append({"kind":"conversion", "ops":ops,
                          "stage":" -> ".join(ops)})
    except (TypeError, ValueError, FileNotFoundError):
        pass
    return fixes


def validate_pipeline(stages: list[dict], start_sort: str | None, cat: Catalog, *,
                      max_stages: int | None = None, bindings: dict | None = None,
                      store: HandleStore | None = None, outputs: list[str] | None = None) -> dict:
    """Shared non-executing pipeline validator used by both MCP entry points."""
    max_stages = int(max_stages or get_system("pipeline_max_stages"))
    errors, normalized = [], []
    from fullseye.opsearch import _graph, known_sorts, normalize_sort
    def normalize_ref(ref):
        if isinstance(ref, str) and ref.startswith("have:"):
            return "have:%s" % normalize_sort(ref.split(":", 1)[1])
        return ref
    start_sort = normalize_sort(start_sort)
    bindings = {
        ("have:%s" % normalize_sort(ref.split(":", 1)[1]) if isinstance(ref, str) and ref.startswith("have:") else ref): handle
        for ref, handle in dict(bindings or {}).items()
    }
    if start_sort is not None and start_sort not in known_sorts():
        errors.append({"layer": "pipeline", "stage": 0, "reason": "unknown_sort", "value": start_sort,
                       "candidates": []})
    if not stages:
        errors.append({"layer": "pipeline", "stage": 0, "reason": "empty_pipeline", "candidates": []})
    if len(stages) > max_stages:
        errors.append({"layer": "pipeline", "stage": 0, "reason": "too_many_stages",
                       "value": len(stages), "limit": max_stages, "candidates": []})
    graph_edges = {
        e["op"]: {**e, "inputs": [normalize_sort(x) for x in e.get("inputs", ())],
                  "output": normalize_sort(e.get("output"))}
        for e in _graph()["edges"]
    }
    physical_catalog = physical_parameter_catalog()
    binding_sorts = {}; binding_values = {}
    for ref, handle in bindings.items():
        if not ref.startswith("have:"):
            errors.append({"layer":"binding","stage":0,"reason":"invalid_binding_name","value":ref,"candidates":[]})
        elif store is None:
            binding_sorts[ref] = ref.split(":",1)[1]
            binding_values[ref] = ({"sort":binding_sorts[ref],"handle":handle},None)
        else:
            try:
                binding_values[ref] = store.get(handle)
                binding_sorts[ref] = normalize_sort(binding_values[ref][0]["sort"])
                declared=normalize_sort(ref.split(":",1)[1])
                if declared != binding_sorts[ref]:
                    errors.append({"layer":"binding","stage":0,"reason":"binding_sort_mismatch",
                                   "value":binding_sorts[ref],"expected":declared,"candidates":[]})
            except HandleError as exc:
                errors.append({"layer":"binding","stage":0,"reason":"invalid_handle","value":handle,
                               "detail":str(exc),"candidates":[]})
    if start_sort is not None:
        binding_sorts.setdefault("have:%s" % start_sort, start_sort)
        binding_values.setdefault("have:%s" % start_sort,({"sort":start_sort,"handle":None},None))
    indexed = {"stage:%d" % i: (i, spec) for i, spec in enumerate(stages[:max_stages], 1)}
    deps = {ref: ({x for x in spec.get("inputs", []) if isinstance(x,str) and x.startswith("stage:")} |
                  {v["ref"] for v in spec.get("params",{}).values()
                   if isinstance(v,dict) and isinstance(v.get("ref"),str) and v["ref"].startswith("stage:")})
            for ref,(_i,spec) in indexed.items()}
    ordered=[]; pending=dict(indexed)
    while pending:
        ready=sorted((ref for ref in pending if deps[ref].isdisjoint(pending)), key=lambda x:int(x.split(":")[1]))
        if not ready:
            errors.append({"layer":"pipeline","stage":0,"reason":"dependency_cycle","value":sorted(pending),"candidates":[]})
            break
        for ref in ready: ordered.append(pending.pop(ref));
    cur = start_sort
    stage_sorts = {}
    for i, spec in ordered:
        name = spec.get("op")
        edge = graph_edges.get(name)
        refs = spec.get("inputs")
        if refs is not None:
            refs = [normalize_ref(ref) for ref in refs]
        isolated = _is_isolated(edge)
        literal_names = []
        expected_inputs = list(edge["inputs"]) if edge else []
        if isolated:
            # 数 1 個を受けるデータ入力(measurement)は、名前で params に書ける(数、または {"ref": …})。
            executor = edge["executor"]
            literal_names = [n for n in executor.get("literal_inputs", []) if n in spec.get("params", {})]
            expected_inputs = [s for n, s in zip(executor.get("data_names", []), edge["inputs"])
                               if n not in literal_names]
        if refs is None:
            refs = [] if not edge or not expected_inputs else (["stage:%d"%(i-1)] if i>1 else
                    (["have:%s"%start_sort] if start_sort else []))
        if refs is not None:
            if edge is None:
                errors.append({"layer":"stage","stage":i,"reason":"unknown_op","value":name,
                               "candidates":[x for x in cat.nearest(name) if x != name]})
                continue
            if not edge.get("verified_executable"):
                from fullseye.opsearch import mcp_unavailable
                info = mcp_unavailable(name) or {}
                errors.append({"layer":"stage","stage":i,"reason":"not_executable_in_mcp","value":name,
                               "detail":edge.get("not_executable_in_mcp", edge.get("executable_reason","no verified executor")),
                               "why":info.get("why"),"probe_reason":info.get("reason"),
                               "instead":info.get("instead", []),
                               "candidates":info.get("executable_alternatives", [])})
                continue
            if len(refs) != len(expected_inputs):
                err = {"layer":"stage","stage":i,"reason":"input_arity_mismatch","value":len(refs),
                       "expected":len(expected_inputs),"expected_sorts":list(expected_inputs),"candidates":[]}
                if isolated and edge.get("example"):
                    err["example"] = edge["example"]
                errors.append(err)
            actual=[]; resolved=[]
            for ref in refs:
                known={**binding_values,**{r:({"sort":s,"handle":r},None) for r,s in stage_sorts.items()}}
                try:
                    meta,_value=_resolve_pipeline_ref(ref,known,store)
                    actual.append(normalize_sort(meta["sort"])); resolved.append(meta.get("handle") or ref)
                except (ArgError,HandleError) as exc:
                    actual.append("unknown"); resolved.append(ref)
                    errors.append({"layer":"stage","stage":i,"reason":"unknown_input_ref",
                                   "value":ref,"detail":str(exc),"candidates":[]})
            mismatches=[{"input":j,"actual":a,"expected":b} for j,(a,b) in enumerate(zip(actual,expected_inputs))
                        if b not in ("poly",a)
                        and not (isolated and b in _SCALAR_INPUT_SORTS and a in _SCALAR_COMPATIBLE_SORTS)]
            if mismatches:
                for mismatch in mismatches:
                    mismatch["fixes"] = _sort_mismatch_fixes(mismatch["actual"], mismatch["expected"])
                errors.append({"layer":"stage","stage":i,"reason":"sort_mismatch",
                               "actual":[m["actual"] for m in mismatches],
                               "expected":[m["expected"] for m in mismatches],
                               "value":mismatches,
                               "fixes":[fix for m in mismatches for fix in m["fixes"]],
                               "candidates":[]})
            roles=edge.get("input_roles",[])
            if len(set(resolved)) != len(resolved) and len(set(roles)) > 1 and not spec.get("allow_reuse",False):
                errors.append({"layer":"stage","stage":i,"reason":"distinct_role_reuses_reference",
                               "value":list(zip(roles,refs)),"candidates":[]})
            schema={p["name"]:p for p in edge.get("parameter_schema",[])}
            physical = physical_catalog.get(name, {})
            schema_names = set(schema) | set(physical)
            if isolated:
                schema_names |= set(edge["executor"].get("literal_inputs", []))
            unknown_params=sorted(set(spec.get("params",{}))-schema_names)
            if unknown_params:
                err = {"layer":"stage","stage":i,"reason":"unknown_parameter","value":unknown_params,
                       "candidates":sorted(schema_names)}
                if {"a", "b"} & set(unknown_params):
                    # ★2026-11-08: a/b を params の中に入れた形は、知らない引数として断るだけでは直し方が分からない
                    err["detail"] = "a と b は params の中ではなく段の直下に書く: {\"op\": ..., \"a\": 0.5}"
                errors.append(err)
            missing=[n for n,p in schema.items() if p.get("required") and n not in spec.get("params",{})]
            if missing:
                errors.append({"layer":"stage","stage":i,"reason":"missing_parameter","value":missing,"candidates":[]})
            for pname,pvalue in spec.get("params",{}).items():
                if pname in physical:
                    continue
                if isolated and pname in literal_names:
                    # 数 1 個の入力: 有限の数か、数を返した段への参照
                    if isinstance(pvalue, dict) and set(pvalue) == {"ref"}:
                        known={**binding_values,**{r:({"sort":s,"handle":r},None) for r,s in stage_sorts.items()}}
                        try:
                            ref_sort=normalize_sort(_resolve_pipeline_ref(normalize_ref(pvalue["ref"]),known,store)[0]["sort"])
                        except (ArgError,HandleError) as exc:
                            errors.append({"layer":"stage","stage":i,"reason":"unknown_parameter_ref",
                                           "value":pvalue["ref"],"detail":str(exc),"candidates":[]})
                            continue
                        if ref_sort not in _SCALAR_COMPATIBLE_SORTS:
                            errors.append({"layer":"stage","stage":i,"reason":"parameter_ref_sort_mismatch",
                                           "value":ref_sort,"expected":sorted(_SCALAR_COMPATIBLE_SORTS),"candidates":[]})
                    elif (isinstance(pvalue, bool) or not isinstance(pvalue, (int, float))
                          or not math.isfinite(float(pvalue))):
                        errors.append({"layer":"stage","stage":i,"reason":"parameter_type_mismatch","value":pname,
                                       "detail":"%s.%s must be one finite number or {\"ref\": \"stage:N\"}" % (name, pname),
                                       "candidates":[]})
                    continue
                if isolated and pname in schema and not (isinstance(pvalue, dict) and ("ref" in pvalue or "profile" in pvalue)):
                    problem = _check_isolated_param(name, schema[pname], pvalue)
                    if problem:
                        errors.append({"layer":"stage","stage":i,"reason":"parameter_type_mismatch","value":pname,
                                       "detail":problem,"expected":{k: schema[pname].get(k) for k in
                                                                    ("kind","unit","choices","default") if schema[pname].get(k) is not None},
                                       "candidates":[]})
                    continue
                if isinstance(pvalue,dict) and "ref" in pvalue:
                    expected=edge.get("ref_parameters",{}).get(pname)
                    known={**binding_values,**{r:({"sort":s,"handle":r},None) for r,s in stage_sorts.items()}}
                    param_ref = normalize_ref(pvalue["ref"])
                    try: actual_sort=normalize_sort(_resolve_pipeline_ref(param_ref,known,store)[0]["sort"])
                    except (ArgError,HandleError) as exc:
                        actual_sort=None
                        errors.append({"layer":"stage","stage":i,"reason":"unknown_parameter_ref",
                                       "value":pvalue["ref"],"detail":str(exc),"candidates":[]})
                    if expected is None:
                        errors.append({"layer":"stage","stage":i,"reason":"parameter_ref_not_declared",
                                       "value":pname,"candidates":sorted(edge.get("ref_parameters",{}))})
                    elif actual_sort not in (expected,None):
                        errors.append({"layer":"stage","stage":i,"reason":"parameter_ref_sort_mismatch",
                                       "value":actual_sort,"expected":expected,"candidates":[]})
                elif isinstance(pvalue,dict) and "profile" in pvalue:
                    from fssystem import resolve_profile
                    try: resolve_profile(pvalue["profile"])
                    except (TypeError,ValueError) as exc:
                        errors.append({"layer":"stage","stage":i,"reason":"unknown_profile",
                                       "value":pvalue.get("profile"),"detail":str(exc),"candidates":[]})
            # ★2026-11-08(AI が組んだ検査の PoC、作者と独立の検証): 検証は a/b の範囲を見ておらず、
            #   pipeline の入力スキーマ(0〜1)が断る値(threshold の a=128)を「正しい」と返していた。同じ規則で断る。
            knob_bad = {}
            for knob in ("a", "b"):
                if knob in spec:
                    v = spec[knob]
                    if isinstance(v, bool) or not isinstance(v, (int, float)) or not (0.0 <= float(v) <= 1.0):
                        knob_bad[knob] = v
            if knob_bad:
                errors.append({"layer":"stage","stage":i,"reason":"knob_out_of_range","value":knob_bad,
                               "detail":"a と b は 0〜1 の数(つまみの位置)。物理量で渡すなら op カードの名前つき params",
                               "candidates":[]})
            ka = 0.5 if "a" in knob_bad else float(spec.get("a", 0.5))
            kb = 0.5 if "b" in knob_bad else float(spec.get("b", 0.5))
            named_used = {}
            if physical:
                conflicts = sorted(name0 for name0, ps in physical.items()
                                   if name0 in spec.get("params", {}) and ps["knob"] in spec)
                if conflicts:
                    errors.append({"layer":"stage","stage":i,"reason":"conflicting_parameter_forms",
                                   "value":conflicts,"detail":"use named params or a/b, not both",
                                   "candidates":sorted(physical)})
                try:
                    ka, kb, named_used = _named_knobs(name, spec.get("params"), ka, kb)
                except ArgError as exc:
                    errors.append({"layer":"stage","stage":i,"reason":"physical_parameter_out_of_range",
                                   "value":dict(spec.get("params",{})),"detail":str(exc),
                                   "candidates":physical})
            out = actual[0] if edge["output"] == "poly" and actual else edge["output"]
            ref="stage:%d"%i; stage_sorts[ref]=out; cur=out
            normalized.append({"stage":i,"op":name,"inputs":list(refs),"params":dict(spec.get("params",{})),
                               "a":ka,"b":kb,"named_params":named_used,
                               "in_sorts":edge["inputs"],"out_sort":out})
            if isolated:
                normalized[-1].update({"isolated":True,"literal_inputs":list(literal_names)})
            continue
    known_outputs={**binding_values,**{r:({"sort":s,"handle":r},None) for r,s in stage_sorts.items()}}
    for ref in outputs or []:
        ref = normalize_ref(ref)
        try: _resolve_pipeline_ref(ref,known_outputs,store)
        except (ArgError,HandleError) as exc:
            errors.append({"layer":"pipeline","stage":0,"reason":"unknown_output_ref",
                           "value":ref,"detail":str(exc),"candidates":[]})
    return {"valid": not errors, "start_sort": start_sort, "bindings":bindings, "out_sort": cur,
            "stages": normalized, "execution_order":[x[0] for x in ordered], "errors": errors}


def _python_stage_inputs(args, in_sorts, name):
    """``python`` 実行器の段(型つきの関数を直に呼ぶ段)へ渡す入力に、``fullseye.apply`` の入口の契約を当てる。

    ★2026-11-05(外部監査 F2 の兄弟、nary-guard): ``registry`` の段は ``fullseye.apply(on_error="raise")``
    を通る(敵対的検証 C2)のに、``python`` の段(``phase_correlation_shift`` / ``polarization_render`` /
    ``deflectometry_phase_to_slope`` の 2 入力と ``fringe_ftp_phase`` など)は値をそのまま関数に渡していた ——
    ``.npy`` から読んだ uint8 のハンドルが、同じパイプラインの ``gauss_filter`` では拒否されるのに、
    こちらでは 0..255 の値のまま黙って計算された。入力ごとに、宣言 sort が dtype 契約の対象
    (``image`` / ``color`` / ``volume``)なら :func:`api._contract_dtype` を strict で当て(整数・bool は拒否、
    float16/32 は float64 へ無損失に昇格)、非有限値は ``fullseye.apply`` と同じ文で拒否する。
    それ以外の sort(``points`` / ``seq<image>`` / ``polsweep`` ...)は型つきの値の表現が別なので触らない。
    """
    import api
    sorts = list(in_sorts or ())
    out = []
    for k, x in enumerate(args):
        srt = sorts[k] if k < len(sorts) else None
        if srt in api._DTYPE_CONTRACT_SORTS and isinstance(x, np.ndarray):
            x = api._contract_dtype(x, api._NaryInput(name, srt, srt), "raise")
            api._refuse_nonfinite(x, name)
        out.append(x)
    return out


def _run_op(arr, op, ka: float, kb: float, allow: bool, device: str = "cpu"):
    """1 op を走らせる。strict で失敗したら (None, degraded, err)。"""
    import backend_safe
    import fullseye
    # ★2026-11-05(敵対的検証、契約の疑い「台帳の並行消去」を探針で確認): 以前は clear_fallbacks() で
    #   **プロセス全体の台帳を消して**から fallbacks() を読んでいた —— MCP を同じプロセスで呼ぶ利用者の
    #   台帳が 1 回の fullseye_apply で空になり、別スレッドの記録がこの呼び出しの degraded に混ざった。
    #   印(mark)からこのスレッドの記録だけを読む(台帳は消さない)。
    mark = backend_safe.mark()
    try:
        out = fullseye.apply(arr, op.name, ka, kb, device=device,
                            on_error=("fallback" if allow else "raise"))
    except Exception as exc:                                    # noqa: BLE001
        return None, backend_safe.events_since(mark), {"type": type(exc).__name__, "message": str(exc)[:400]}
    return out, backend_safe.events_since(mark), None


def _stage(store: HandleStore, meta: dict, arr, op, ka: float, kb: float, allow: bool, *,
           vision: str, thumb_allowed: bool, tag: str, device: str = "cpu"):
    """apply 1 段ぶん: 記録(数値 + 判定 + 劣化台帳)と、必要なら小図。
    返り値 = (record, links, out_meta | None, out_value)。out_meta は配列のときだけ。"""
    import numpy as np
    import ops
    out, degraded, err = _run_op(arr, op, ka, kb, allow, device=device)
    out_sort = _out_sort(op, meta.get("sort"))
    rec: dict = {"op": op.name, "a": ka, "b": kb, "handle_in": meta.get("handle"),
                 "in_sort": op.in_sort, "out_sort": out_sort,
                 "degraded": degraded, "strict": not allow}
    if err is not None:
        rec["error"] = err
        return rec, [], None, None
    _enforce_pixel_limit(out, "op %s" % op.name)
    st = stats_of(out)
    vd = verdict_of(st, op_name=op.name, out_sort=out_sort)
    if degraded:
        vd = dict(vd, escalate=True,
                  reasons=vd["reasons"] + ["劣化 %d 件(degraded を見ること)" % len(degraded)])
    rec.update({"stats": st, **vd})
    prov = list(meta.get("provenance", [])) + [{"apply": op.name, "a": ka, "b": kb}]
    links: list[dict] = []
    m2 = None
    if isinstance(out, np.ndarray):
        m2 = store.put(out, sort=out_sort, provenance=prov)
        rec["handle"] = m2["handle"]
        if thumb_allowed:
            links = _maybe_thumb(store, m2, arr, out, vision=vision, escalate=vd["escalate"],
                                 quantity=op.name in ops.UNIT_RANGE_IS_NOT_THE_CONTRACT, tag=tag)
    elif isinstance(out, dict) and "cs" in out:
        rec["handle"] = None
        rec["contour"] = {"n": st.get("n_contours"), "points": st.get("n_points")}
        m2 = {"handle": None, "sort": out_sort, "provenance": prov}   # 連鎖用の疑似メタ
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


#: JSON 添付を**しない** sort。画素・場・ボリューム系は大きく、ハンドル/小図で扱う
#: (export_json と同じ判断)。ここに無い小さい型(scalar/feature/table/points/matrix/
#: signal/vector/keypoints/counts/contour)だけ、結果に封筒 + Markdown を添える。
_BULKY_SORTS = frozenset({"image", "image2d", "rgb", "rgbimage", "color", "mask",
                          "region", "volume", "rgbvolume", "stokes", "polsweep"})


def _typed_json_addon(arr, sort, max_bytes):
    """小さい型付き結果なら ``(envelope, markdown)`` を返す。大きい画素/場や JSON 化
    できないものは ``None``(添付しない)。純粋に追加情報 —— 既存の結果は変えない。"""
    import json as _json

    import fullseye
    if sort not in fullseye.JSON_SORTS or sort in _BULKY_SORTS:
        return None
    try:
        env = fullseye.to_jsonable(arr, sort, readable=True)
    except Exception:                                           # noqa: BLE001 (添付は best-effort)
        return None
    if len(_json.dumps(env, ensure_ascii=False).encode("utf-8")) > max_bytes:
        return None                                            # 上限超過は添付しない(export_json 同様)
    try:
        md = fullseye.to_markdown(arr, sort)
    except Exception:                                           # noqa: BLE001
        md = None
    return env, md


def _pipeline_json_value(value, store: HandleStore, *, sort: str, provenance: list,
                         max_bytes: int = 2048):
    """Return a bounded, genuinely JSON-serializable pipeline value.

    Registry value outputs sometimes contain ndarrays inside dictionaries.  ``repr``
    is useful for diagnostics but must never be used as proof that the original tree
    can be put in ``structuredContent``.  Small arrays are described inline; larger
    arrays get their own handle.  Unsupported/cyclic/oversized trees are omitted and
    remain available through the value handle created by the caller.
    """
    active: set[int] = set()

    def convert(item):
        if item is None or isinstance(item, (str, bool, int)):
            return item
        if isinstance(item, float):
            # ★2026-11-05(敵対的検証): 非有限を黙って null にしない(fail-closed)。木ごと省き、
            #   値はハンドル(value_handle)から読む —— 他の経路(write_message)と同じく NaN を JSON に書かない。
            if not math.isfinite(item):
                raise ValueError("value holds a non-finite number")
            return item
        if isinstance(item, np.generic):
            return convert(item.item())
        if isinstance(item, np.ndarray):
            desc = {"shape": list(item.shape), "dtype": str(item.dtype)}
            try:
                listed = item.tolist()
                candidate = dict(desc, value=listed)
                if len(json.dumps(candidate, ensure_ascii=False).encode("utf-8")) <= max_bytes:
                    return candidate
            except (TypeError, ValueError, OverflowError):
                pass
            meta = store.put(item, sort=sort, provenance=provenance)
            return dict(desc, handle=meta["handle"])
        if isinstance(item, dict):
            oid = id(item)
            if oid in active or not all(isinstance(k, str) for k in item):
                raise ValueError("value is not a JSON tree")
            active.add(oid)
            try:
                return {k: convert(v) for k, v in item.items()}
            finally:
                active.remove(oid)
        if isinstance(item, (list, tuple)):
            oid = id(item)
            if oid in active:
                raise ValueError("value is cyclic")
            active.add(oid)
            try:
                return [convert(v) for v in item]
            finally:
                active.remove(oid)
        raise ValueError("unsupported value type %s" % type(item).__name__)

    try:
        normalized = convert(value)
        encoded = json.dumps(normalized, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, OverflowError, HandleError):
        return None
    return normalized if len(encoded) <= max_bytes else None


def _apply_isolated(a: dict, edge: dict, cat: Catalog, store: HandleStore, *,
                    max_structured_bytes: int | None = None) -> dict:
    """台帳 op(隔離して走る物)の fullseye_apply: 1 段の fullseye_pipeline と同じ経路・同じ検査で走らせる。"""
    if a.get("device") not in (None, "cpu", "auto"):
        raise ArgError("%s runs in the MCP op worker on the CPU only; omit device or pass \"cpu\"" % edge["op"])
    for key in ("a", "b", "allow_degraded", "parity_check"):
        if key in a:
            raise ArgError("%s is a ledger op: use named params (%s), not %s" % (
                edge["op"], ", ".join(r["name"] for r in edge.get("parameter_schema", [])) or "none", key))
    executor = edge["executor"]
    params = dict(a.get("params") or {})
    data_inputs = [n for n in executor.get("data_names", []) if n not in params]
    if len(data_inputs) > 1:
        raise ArgError("%s takes %d inputs (%s); fullseye_apply carries one handle. Use fullseye_pipeline with "
                       "stages=[{\"op\":%r,\"inputs\":[<handle>, ...]}]" % (
                           edge["op"], len(data_inputs), ", ".join(edge["inputs"]), edge["op"]))
    stage = {"op": edge["op"]}
    if params:
        stage["params"] = params
    args = {"stages": [stage], "vision": a.get("vision", "auto")}
    if data_inputs:
        args["handle"] = a["handle"]
    return _pipeline(args, cat, store, max_structured_bytes=max_structured_bytes)


def _apply(a: dict, cat: Catalog, store: HandleStore, *,
           max_structured_bytes: int | None = None) -> dict:
    max_structured_bytes = _response_budget(max_structured_bytes)
    import ops
    if a["op"] not in ops._BY_NAME:
        from fullseye.opsearch import _graph
        edge = next((e for e in _graph()["edges"] if e["op"] == a["op"]), None)
        if _is_isolated(edge) and edge.get("verified_executable"):
            # ★2026-11-13: 台帳 op(光学・照明・合成の入口 …)も fullseye_apply から呼べる(pipeline と同じ経路)
            return _apply_isolated(a, edge, cat, store, max_structured_bytes=max_structured_bytes)
    op = _resolve_op(a["op"], cat)
    meta, arr = store.get(a["handle"])
    _check_sort(op, meta["sort"], prev="ハンドル %s" % meta["handle"])
    physical = physical_parameter_catalog().get(op.name, {})
    conflicts = sorted(name for name, spec in physical.items()
                       if name in a.get("params", {}) and spec["knob"] in a)
    if conflicts:
        raise ArgError("%s: use named params or a/b, not both (%s)" % (op.name, conflicts))
    ka, kb, named = _named_knobs(op.name, a.get("params"),
                                  float(a.get("a", 0.5)), float(a.get("b", 0.5)))
    allow = bool(a.get("allow_degraded", False))
    rec, links, _, out = _stage(store, meta, arr, op, ka, kb, allow, vision=a.get("vision", "auto"),
                                thumb_allowed=True, tag=op.name, device=a.get("device", "cpu"))
    if "error" in rec:
        text = _stage_text(rec) + "\n(allow_degraded=true で fail-soft を許せるが、劣化は degraded に載る)"
        return _tool_error(text, rec)
    if named:
        rec["named_params"] = named
    import fullseye
    rec["acceleration"] = _acceleration_record(a.get("device", "cpu"), op.name, np.shape(arr),
                                               rec.get("degraded"))
    effective = rec["acceleration"]["device"]
    # CPU 参照との照合は求められた時だけ(既定で毎回 2 回走らせると GPU の意味が無い)
    if effective == "cuda" and bool(a.get("parity_check", False)) and isinstance(out, np.ndarray):
        cpu = fullseye.apply(arr, op.name, ka, kb, device="cpu", on_error="raise")
        if isinstance(cpu, np.ndarray) and cpu.shape == out.shape:
            rec["acceleration"]["max_abs_diff_vs_cpu"] = float(
                np.max(np.abs(np.asarray(out, np.float64) - np.asarray(cpu, np.float64))))
    text = _stage_text(rec)
    addon = _typed_json_addon(out, _out_sort(op, meta["sort"]), max_structured_bytes)
    if addon is not None:
        env, md = addon
        rec["json"] = env                                       # 追加: bit そのまま戻せる封筒
        if md:
            text += "\n\n" + md                                # 追加: 人が読める Markdown
    return tool_result(text, rec, links=links, max_structured_bytes=max_structured_bytes)


def _acceleration_record(requested, op_name: str, shape, degraded=None) -> dict:
    """``acceleration`` の中身(MCP の結果)。従来の ``requested`` / ``device`` / ``approximate`` に、
    ``path``(``accel`` / ``allow_single`` / ``cpu`` …)・``reason``(CPU を選んだ理由)・``resolved`` /
    ``source`` と、見たときは ``vram_free_mb`` / ``vram_min_free_mb`` を足す(追加のみ)。

    直前の ``fullseye.apply`` が使った選択(:func:`api.last_device_decision`)を優先し、無ければ同じ入力で
    :func:`api.explain_device` を引く。GPU で走らせて失敗し CPU で続いた記録が台帳にあれば
    ``device="cpu"`` / ``reason="gpu_failed"`` に直す(選んだ装置でなく、走った装置を返す)。
    """
    import api
    dec = api.last_device_decision()
    if dec is None or dec.get("requested") != str(requested):
        dec = api.explain_device(requested, stages=(op_name,), shape=shape)
    out = {"requested": requested, "device": dec["device"], "approximate": dec["device"] == "cuda",
           "path": dec.get("path"), "reason": dec.get("reason"), "resolved": dec.get("resolved"),
           "source": dec.get("source")}
    for key in ("vram_free_mb", "vram_min_free_mb"):
        if key in dec:
            out[key] = dec[key]
    if out["device"] == "cuda" and any(isinstance(d, dict) and d.get("source") == "gpu" for d in degraded or ()):
        out.update(device="cpu", approximate=False, path="cpu", reason="gpu_failed")
    return out


def _pipeline(a: dict, cat: Catalog, store: HandleStore, *,
              max_structured_bytes: int | None = None) -> dict:
    max_structured_bytes = _response_budget(max_structured_bytes)
    return _pipeline_dag(a,cat,store,max_structured_bytes=max_structured_bytes)


def _pipeline_dry_run(a: dict, store: HandleStore, max_structured_bytes: int) -> dict:
    """``dry_run``: 走らせずに経路を検査する(:func:`fullseye.explain_pipeline`)。"""
    import fullseye
    shape = None
    if a.get("handle"):
        _meta, value = store.get(a["handle"])
        shape = getattr(np.asarray(value), "shape", None)
    plan = fullseye.explain_pipeline([s.get("op") for s in a["stages"]], shape, device=a.get("device", "cpu"),
                                     assume_cuda=bool(a.get("assume_cuda", False)))
    lines = ["dry_run: %d 段 / GPU %d 段 / 切り替わり %d / 往復の見込み %d" % (
        len(plan["stages"]), plan["n_gpu_stages"], plan["n_switches"], plan["n_transfers"])]
    for sw in plan["switches"]:
        lines.append("  段 %d %s: %s -> %s (%s)" % (sw["at"] + 1, sw["op"], sw["from"], sw["to"], sw["reason"]))
    for br in plan["type_breaks"]:
        lines.append("  型の切れ目 段 %d %s: %s" % (br["index"] + 1, br["op"], br["reason"]))
    return tool_result("\n".join(lines), {"dry_run": True, "plan": plan},
                       max_structured_bytes=max_structured_bytes)


def _pipeline_dag(a: dict, cat: Catalog, store: HandleStore, *, max_structured_bytes: int) -> dict:
    """Execute the same reference vocabulary emitted by the planner."""
    import importlib
    import fullseye
    if a.get("dry_run"):
        return _pipeline_dry_run(a, store, max_structured_bytes)
    from fullseye.opsearch import _graph
    edges={e["op"]:e for e in _graph()["edges"]}
    policy=_execution_policy()
    pipeline_decision=fullseye.explain_device(a.get("device", "cpu"))
    device=pipeline_decision["resolved"]
    gpu_effective=pipeline_decision["device"] == "cuda"     # resolved cuda かつ CUDA が在る
    stage_devices=[]                      # 段ごとの装置・経路・理由(acceleration.stages)
    parity_check=bool(a.get("parity_check", False))
    explicit=bool(a.get("bindings") or a.get("outputs") or any("inputs" in s or "params" in s for s in a["stages"]))
    start_sort=store.get(a["handle"])[0]["sort"] if a.get("handle") else None
    bindings=dict(a.get("bindings",{}))
    if a.get("handle") and start_sort:
        bindings.setdefault("have:%s"%start_sort,a["handle"])
    matching = {stage.get("op") for stage in a["stages"]} & {"ncc_locate", "shape_locate"}
    template_value = None
    if matching:
        if not a.get("template_handle"):
            detail = {"valid":False, "reason":"missing_template_handle",
                      "actual":None, "expected":"2-D image template handle",
                      "fixes":[{"tool":"fullseye_load_template",
                                "call":"fullseye_load_template(path=<template path>)"}]}
            return _tool_error(json.dumps(detail, ensure_ascii=False), detail)
        tmeta, template_value = store.get(a["template_handle"])
        if tmeta.get("sort") != "image" or np.asarray(template_value).ndim != 2:
            detail = {"valid":False, "reason":"template_sort_mismatch",
                      "actual":tmeta.get("sort"), "expected":"image",
                      "fixes":[{"tool":"fullseye_load_template"}]}
            return _tool_error(json.dumps(detail, ensure_ascii=False), detail)
    checked=validate_pipeline(a["stages"],start_sort,cat,bindings=bindings,store=store,
                              outputs=a.get("outputs"))
    if not checked["valid"]:
        argument_reasons={"unknown_input_ref","unknown_parameter_ref","unknown_profile",
                          "unknown_output_ref","invalid_handle","invalid_binding_name","binding_sort_mismatch"}
        if any(e.get("reason") in argument_reasons for e in checked["errors"]):
            raise ArgError("pipeline validation failed: %s"%json.dumps(checked["errors"],ensure_ascii=False))
        if not explicit:
            first=checked["errors"][0]
            op=a["stages"][first.get("stage",1)-1].get("op") if first.get("stage") else "pipeline"
            label="型の不一致: " if first.get("reason")=="sort_mismatch" else ""
            raise ArgError("%s段 %s %s: %s"%(label,first.get("stage",0),op,
                json.dumps(first,ensure_ascii=False)), data=checked)
        return _tool_error(json.dumps(checked,ensure_ascii=False),checked)
    bindings = checked["bindings"]
    outputs=a.get("outputs") or (["stage:%d"%len(a["stages"])] if a["stages"] else [])
    from collections import Counter
    remaining=Counter(outputs)
    for normalized_stage in checked["stages"]:
        remaining.update(normalized_stage["inputs"])
        stage=a["stages"][normalized_stage["stage"]-1]
        remaining.update(v["ref"] for v in stage.get("params",{}).values()
                         if isinstance(v,dict) and "ref" in v)
    values={ref:store.get(handle) for ref,handle in bindings.items()}; records=[]; failed=set(); links=[]
    intermediate_bytes=0
    intermediate_limit=int(get_system("mcp_pipeline_max_intermediate_bytes"))

    def release(refs):
        for used_ref in refs:
            remaining[used_ref]-=1
            if remaining[used_ref] <= 0 and used_ref.startswith("stage:"):
                values.pop(used_ref,None)

    original={i:s for i,s in enumerate(a["stages"],1)}
    normalized_by_stage={s["stage"]:s for s in checked["stages"]}
    for i in checked["execution_order"]:
        spec=original[i]
        normalized_spec=normalized_by_stage[i]
        edge=edges[spec["op"]]; args=[]; metas=[]
        refs=next(x["inputs"] for x in checked["stages"] if x["stage"]==i)
        param_refs=[v["ref"] for v in spec.get("params",{}).values()
                    if isinstance(v,dict) and "ref" in v]
        blocked=[ref for ref in refs + param_refs if ref in failed]
        if blocked:
            failed.add("stage:%d"%i)
            records.append({"stage":i,"ref":"stage:%d"%i,"op":edge["op"],"status":"skipped",
                            "reason":"dependency_failed","blocked_by":blocked})
            release(refs + param_refs)
            continue
        for ref in refs:
            meta,value=_resolve_pipeline_ref(ref,values,store)
            values.setdefault(ref,(meta,value))
            metas.append(meta); args.append(value)
        params=dict(spec.get("params",{}))
        for pname,pvalue in list(params.items()):
            if isinstance(pvalue,dict) and "ref" in pvalue:
                params[pname]=_resolve_pipeline_ref(pvalue["ref"],values,store)[1]
            elif isinstance(pvalue,dict) and "profile" in pvalue:
                from fssystem import resolve_profile
                try: params[pname]=resolve_profile(pvalue["profile"])
                except ValueError as exc: raise ArgError(str(exc)) from exc
        parity_meta = None
        isolated_info = None
        try:
            executor=edge["executor"]
            if _is_isolated(edge):
                # 台帳 op(光学・照明・合成の入口): 隔離した子プロセスで、時間とメモリの上限つきで走らせる。
                #   引数は validate_pipeline が台帳の仕様で検査済み。ここでは境界を越える直前にもう一度見る。
                call_params = {}
                literal = {}
                for pname, pvalue in params.items():
                    if pname in normalized_spec.get("literal_inputs", ()):
                        literal[pname] = _scalar_of(pvalue, "%s.%s" % (edge["op"], pname))
                        continue
                    row = next((r for r in edge.get("parameter_schema", []) if r["name"] == pname), None)
                    raw = spec.get("params", {}).get(pname)
                    if row is None or (not (isinstance(raw, dict) and ("ref" in raw or "profile" in raw))
                                       and _check_isolated_param(edge["op"], row, pvalue)):
                        raise ArgError("stage %d (%s): parameter %r failed re-validation" % (i, edge["op"], pname))
                    if pname in executor.get("array_params", ()) and isinstance(pvalue, list):
                        # 見本で配列だった引数(K など)は、JSON の list のままでは op が添字で読めない
                        pvalue = np.asarray(pvalue, dtype=np.float64)
                    call_params[pname] = pvalue
                data_args = []
                supplied = iter(args)
                for dname, dsort in zip(executor.get("data_names", []), edge["inputs"]):
                    if dname in literal:
                        data_args.append(literal[dname])
                    else:
                        item = next(supplied)
                        if dsort in _SCALAR_INPUT_SORTS:
                            item = _scalar_of(item, "%s.%s" % (edge["op"], dname))
                        elif dsort in _SEQUENCE_SORTS and isinstance(item, np.ndarray) and item.ndim == 3:
                            # MCP の handle は (T,H,W) の配列。台帳 op は 2-D の list を受ける(3-D は意味が曖昧なので断る)
                            item = [np.ascontiguousarray(frame) for frame in item]
                        elif dsort in _LABEL_SORTS:
                            item = _integral_labels(item)
                        data_args.append(item)
                out, isolated_info = _run_isolated_stage(edge, data_args, call_params)
                if edge["output"] in _SEQUENCE_SORTS:
                    out = _stack_sequence(out, edge["op"])
            elif executor["kind"]=="identity":
                out=args[0]
            elif executor["kind"]=="registry":
                import ops as runtime_ops
                import backend_safe
                incoming=args if len(args)>1 else args[0]
                registered=runtime_ops._BY_NAME[executor["alias"]]
                actual=(registered.fn.__module__,registered.fn.__qualname__)
                expected=(executor["module"],executor["callable"])
                if actual != expected:
                    raise RuntimeError("registry target mismatch: %r != %r"%(actual,expected))
                with backend_safe.strict_mode(True), backend_safe.current_op(edge["op"]):
                    # ★2026-11-05(敵対的検証 C2): 以前は CPU の段が registered.fn を直接呼び、fullseye_apply
                    #   (fullseye.apply(on_error="raise"))が持つ入口の契約(dtype、非有限、ノブ、空・次元、
                    #   extra_checks)を全部飛ばしていた —— uint8 200 のハンドルに gaussian が uint8 200 を返した。
                    #   全段を同じ入口に通す。テンプレートも apply(template=...) で同じ検査を受ける。
                    stage_template = template_value if edge["op"] in {"ncc_locate", "shape_locate"} else None
                    # 段ごとに転送するので、規則も段ごとに通す(auto のときだけ CPU に残ることがある)
                    if device == "cuda" and len(args) == 1:
                        stage_decision=fullseye.explain_device(a.get("device", "cpu"), stages=(edge["op"],),
                                                               shape=np.shape(incoming))
                        stage_device=stage_decision["resolved"]
                    else:
                        stage_decision={"device":"cpu","path":"cpu",
                                        "reason":(pipeline_decision.get("reason") if device != "cuda"
                                                  else "multi_input")}
                        stage_device=device if len(args) == 1 else "cpu"
                    stage_devices.append({"stage":i,"op":edge["op"],
                                          "device":stage_decision["device"] if stage_device == "cuda" else "cpu",
                                          "path":stage_decision.get("path") if stage_device == "cuda" else "cpu",
                                          "reason":stage_decision.get("reason")})
                    out=fullseye.apply(incoming, executor["alias"], float(normalized_spec["a"]),
                                       float(normalized_spec["b"]),
                                       device=(stage_device if len(args) == 1 else "cpu"),
                                       on_error="raise", template=stage_template)
                    if gpu_effective and stage_device == "cuda" and parity_check and len(args) == 1 \
                            and isinstance(out, np.ndarray):
                        cpu=fullseye.apply(incoming,executor["alias"],float(normalized_spec["a"]),
                                           float(normalized_spec["b"]),device="cpu",on_error="raise",
                                           template=stage_template)
                        if isinstance(cpu,np.ndarray) and cpu.shape == out.shape:
                            parity_meta={"approximate":True,"max_abs_diff_vs_cpu":float(
                                np.max(np.abs(np.asarray(out,np.float64)-np.asarray(cpu,np.float64))))}
            else:
                fn=getattr(importlib.import_module(executor["module"]),executor["callable"])
                args=_python_stage_inputs(args, normalized_spec.get("in_sorts") or edge["inputs"], edge["op"])
                out=fn(*args,**params)
        except Exception as exc:  # noqa: BLE001
            failed.add("stage:%d"%i)
            reason = "execution_failed"
            error = {"type":type(exc).__name__,"message":str(exc)[:300]}
            if getattr(exc, "reason", None) in ("time_limit", "memory_limit"):
                # 隔離実行の上限: どの上限に当たったかと、その値を返す(黙って長く走らせない)
                reason = "resource_limit"
                error.update({"limit": exc.reason, **_isolated_limits()})
            elif getattr(exc, "reason", None) == "op_error" and getattr(exc, "error_type", None):
                error["type"] = exc.error_type
            if getattr(exc, "reason", None):
                _log("isolated", edge["op"], "failed", exc.reason)
            failed_rec = {"stage":i,"ref":"stage:%d"%i,"op":edge["op"],"status":"failed",
                          "reason":reason,"error":error}
            if _is_isolated(edge) and edge.get("example"):
                failed_rec["example"] = edge["example"]
            records.append(failed_rec)
            release(refs + param_refs)
            continue
        out_sort=metas[0]["sort"] if edge["output"]=="poly" and metas else edge["output"]
        ref="stage:%d"%i
        produced_bytes=_value_nbytes(out)
        intermediate_bytes+=produced_bytes
        try:
            _enforce_pixel_limit(out,"stage %d (%s)"%(i,edge["op"]))
            if intermediate_bytes > intermediate_limit:
                raise ArgError("pipeline intermediate bytes %d exceeds limit %d at stage %d (%s)" %
                               (intermediate_bytes,intermediate_limit,i,edge["op"]))
        except ArgError as exc:
            failed.add(ref)
            records.append({"stage":i,"ref":ref,"op":edge["op"],"status":"failed",
                            "reason":"resource_limit","bytes":produced_bytes,
                            "cumulative_bytes":intermediate_bytes,"error":{
                                "type":type(exc).__name__,"message":str(exc)}})
            release(refs + param_refs)
            del out
            continue
        array_sorts={"image","color","region","images","seq<image>","points","volume","depth","normalmap"}
        invalid=(out_sort in array_sorts and not isinstance(out,np.ndarray))
        invalid=invalid or (isinstance(out,np.ndarray) and out.dtype.kind in "fc" and not np.isfinite(out).all())
        if invalid:
            failed.add(ref); records.append({"stage":i,"ref":ref,"op":edge["op"],"status":"failed",
                    "reason":"invalid_output","out_sort":out_sort})
            release(refs + param_refs)
            continue
        meta=store.put(out,sort=out_sort,provenance=[{"pipeline":edge["op"],"inputs":refs}])
        values[ref]=(meta,out); handle=meta["handle"]
        st=stats_of(out) if isinstance(out,np.ndarray) else {"kind":type(out).__name__}
        vd=verdict_of(st,op_name=edge["op"],out_sort=out_sort) if isinstance(out,np.ndarray) else {
            "verdict":"value","escalate":False,"reasons":[]}
        rec={"stage":i,"ref":ref,"op":edge["op"],"inputs":refs,"status":"ok",
             "params":spec.get("params",{}),"out_sort":out_sort,"handle":handle,"stats":st,**vd,"degraded":[]}
        if parity_meta is not None:
            rec["parity"] = parity_meta
        if isinstance(out, np.ndarray) and out_sort not in _BULKY_SORTS and out.size <= 256:
            # ★2026-11-13: 複素数の配列(Jones ベクトルなど)をそのまま tolist すると JSON にできず、道具ごと落ちた
            rec["value"] = ({"re": out.real.tolist(), "im": out.imag.tolist()} if out.dtype.kind == "c"
                            else out.tolist())
        if normalized_spec.get("named_params"):
            rec["named_params"] = normalized_spec["named_params"]
        if isinstance(out,np.ndarray) and vd.get("escalate") and not links and a.get("vision","auto")!="none":
            links=_maybe_thumb(store,meta,args[0] if args else None,out,vision=a.get("vision","auto"),
                               escalate=True,quantity=False,tag="stage%d_%s"%(i,edge["op"]))
            for link in links: link["description"]="段 %d(%s): "% (i,edge["op"])+link["description"]
        if isolated_info is not None:
            rec["isolated"] = {"elapsed_s": round(isolated_info.get("elapsed_s", 0.0), 3),
                               "time_limit_s": isolated_info["time_limit_s"],
                               "memory_limit_bytes": isolated_info["memory_limit_bytes"]}
            meaning = _op_summary(edge["op"])
            if meaning:
                rec["meaning"] = meaning
            used = {}
            for row in edge.get("parameter_schema", []):
                if row["name"] in spec.get("params", {}) and row.get("unit") not in (None, "", "undocumented"):
                    used[row["name"]] = row["unit"]
            if used:
                rec["param_units"] = used
        if not isinstance(out,np.ndarray):
            rec["value_handle"],rec["handle"]=handle,None
            if isolated_info is not None:
                summary=_summarize_value(out,store,provenance=[{"pipeline_value":edge["op"],"stage":i}])
                rec["value"]=summary["value"]; rec["units"]=summary["units"]
                rec["field_handles"]=summary["handles"]; rec["value_truncated"]=summary["truncated"]
                if summary.get("non_finite"):
                    rec["non_finite"]=summary["non_finite"]
                rec["_lines"]=_summary_lines(summary)
            else:
                normalized=_pipeline_json_value(
                    out,store,sort=out_sort,
                    provenance=[{"pipeline_value":edge["op"],"stage":i}],max_bytes=2048)
                if normalized is not None:
                    rec["value"]=normalized
        records.append(rec)
        release(refs + param_refs)
        if remaining[ref] <= 0:
            values.pop(ref,None)
    output_rows=[{"ref":ref,"handle":values[ref][0]["handle"],"sort":values[ref][0]["sort"]}
                 for ref in outputs if ref in values]
    first_failed=next((r["stage"] for r in records if r.get("status")=="failed"),None)
    visible_records=records if explicit else [r for r in records if r.get("status")!="skipped"]
    linear_specs=[(s["op"], s["a"], s["b"]) for s in checked["stages"]]
    try:
        import accel_bridge
        acceleration=accel_bridge.coverage(linear_specs)
    except Exception:  # noqa: BLE001 - metadata must not change execution outcome
        acceleration={"n_gpu_segments":0,"segments":[],"n_transfers":0}
    acceleration["requested"] = a.get("device", "cpu")
    on_gpu=[s for s in stage_devices if s["device"] == "cuda"]
    # MCP の pipeline は段ごとに fullseye.apply を呼ぶ(段の間は host に戻る)。だから転送は GPU で走った
    # 段ごとに往復 1 回。coverage の n_gpu_segments は常駐で繋いだ場合の値で、ここでは参考。
    acceleration["device"] = "cuda" if gpu_effective and on_gpu else "cpu"
    acceleration["n_transfers"] = 2 * len(on_gpu) if gpu_effective else 0
    paths=sorted({s["path"] for s in stage_devices}) or ["cpu"]
    acceleration["path"] = paths[0] if len(paths) == 1 else "mixed"
    acceleration["reason"] = (None if acceleration["device"] == "cuda"
                              else next((s["reason"] for s in stage_devices if s["reason"]),
                                        pipeline_decision.get("reason")))
    acceleration["stages"] = stage_devices
    for key in ("vram_free_mb", "vram_min_free_mb"):
        if key in pipeline_decision:
            acceleration[key] = pipeline_decision[key]
    result={"completed":sum(r.get("status")=="ok" for r in records),"failed":sum(r.get("status")=="failed" for r in records),
            "stopped_at":first_failed,"strict":True,"stages":visible_records,"outputs":output_rows,
            "intermediate_bytes":intermediate_bytes,"intermediate_byte_limit":intermediate_limit,
            "system_policy":policy,"acceleration":acceleration}
    if len(output_rows)==1:
        result.update({"handle":output_rows[0]["handle"],"out_sort":output_rows[0]["sort"],
                       "output_ref":output_rows[0]["ref"]})
    if not explicit and records:
        last_value_record=next((r for r in reversed(records)
                                if r.get("status")=="ok" and r.get("value_handle")),None)
        last_value=None
        if last_value_record is not None:
            try: last_value=store.get(last_value_record["value_handle"])[1]
            except HandleError: pass
        last_array=next((r["handle"] for r in reversed(records)
                         if r.get("status")=="ok" and r.get("handle")),None)
        result["handle"]=last_array
        if last_value_record is not None and "value" in last_value_record:
            result["value"]=last_value_record["value"]
        addon=_typed_json_addon(last_value,records[-1].get("out_sort"),max_structured_bytes) if last_value is not None else None
        if addon is not None: result["json"]=addon[0]
    if failed:
        for r in records:
            r.pop("_lines", None)
        bad=next(r for r in records if r.get("status")=="failed")
        return _tool_error("段 %d %s failed in strict mode: "% (bad["stage"],bad["op"])+
                           json.dumps(result,ensure_ascii=False,separators=(",",":")),result)
    text=(("パイプライン %d 段 完走: "%sum(r.get("status")=="ok" for r in records)) +
          " -> ".join(r["op"] for r in records if r.get("status")=="ok"))
    table_lines = []
    for r in records:
        lines = r.pop("_lines", None)
        if lines and r.get("status") == "ok":
            table_lines.append("段 %d %s%s" % (r["stage"], r["op"], (": " + r["meaning"]) if r.get("meaning") else ""))
            table_lines.extend("  " + ln for ln in lines)
    if table_lines:
        text += "\n" + "\n".join(table_lines)
    else:
        text += "\n判定=ok value=%s" % result.get("value")
    return tool_result(text,result,links=links,max_structured_bytes=max_structured_bytes)


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


def _inspect(a: dict, store: HandleStore, *,
             max_structured_bytes: int | None = None) -> dict:
    max_structured_bytes = _response_budget(max_structured_bytes)
    meta, arr = store.get(a["handle"])
    if not isinstance(arr, np.ndarray):
        structured={**meta,"value":arr}
        return tool_result("%s sort=%s value=%s"%(meta["handle"],meta["sort"],
                           json.dumps(arr,ensure_ascii=False,default=repr)[:2000]),structured,
                           max_structured_bytes=max_structured_bytes)
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
    addon = _typed_json_addon(arr, meta["sort"], max_structured_bytes)   # 小さい型付きなら封筒 + Markdown
    if addon is not None:
        env, md = addon
        structured["json"] = env
        if md:
            text += "\n\n" + md
    return tool_result(text, structured, links=links, max_structured_bytes=max_structured_bytes)


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


MINIMAL_TOOLS = {"fullseye_find_ops", "fullseye_plan", "fullseye_describe", "fullseye_op_cards",
                 "fullseye_validate_pipeline", "fullseye_pipeline", "fullseye_load_image",
                 "fullseye_load_stack", "fullseye_list_samples", "fullseye_inspect"}
for _internal_tool in ("fullseye_patterns", "fullseye_plan_chain", "fullseye_required_inputs",
                       "fullseye_pipeline_shape", "fullseye_sort_guide", "fullseye_param_space",
                       "fullseye_choose_op"):
    TOOLS.pop(_internal_tool, None)

OP_EXECUTION_TOOLS = frozenset({"fullseye_apply", "fullseye_pipeline"})

def _profile_tool_names(profile: str) -> set[str]:
    if profile == "minimal":
        return set(MINIMAL_TOOLS)
    if profile == "full":
        return set(TOOLS)
    raise ArgError("unknown MCP tool profile: %r" % profile)

# minimal プロファイルの広告スキーマから隠す上級引数(受け付けは常に可。full では見せる)。
# 2026-11-02: device / parity_check を足した分で minimal が 1,500 トークンの予算を超えたため。
# 2026-11-04(統合 GPU): 第 5 便の dry_run / assume_cuda で再び 1,500 を超えた(1,588)ので同じ扱いにする。
# 2026-11-05(敵対的検証 D10): find_ops の lang を schema に足した分で 1,531 になったので lang も隠す。
#   plan の want の空・空白はハンドラが ArgError(-32602)で断る(minLength は空白だけを止められず、予算も食う)。
MINIMAL_HIDDEN_ARGS: dict[str, tuple[str, ...]] = {"fullseye_pipeline": ("device", "parity_check", "dry_run", "assume_cuda"),
                                                   "fullseye_find_ops": ("lang",)}


def _advertised_schema(name: str, profile: str) -> dict:
    schema = TOOLS[name]["inputSchema"]
    hidden = MINIMAL_HIDDEN_ARGS.get(name, ()) if profile == "minimal" else ()
    if not hidden:
        return schema
    import copy
    schema = copy.deepcopy(schema)
    for k in hidden:
        schema.get("properties", {}).pop(k, None)
    return schema


def handle_tools_list(params: dict) -> dict:
    profile = params.get("profile") or os.environ.get("FULLSEYE_MCP_PROFILE", "full")
    names = _profile_tool_names(profile)
    rows = [{"name": n, "description": TOOLS[n]["description"], "inputSchema": _advertised_schema(n, profile)}
            for n in sorted(names)]
    return {"tools": rows, "profile": profile,
            "estimated_tokens": math.ceil(len(json.dumps(rows, ensure_ascii=False)) / 4)}


def _import_json(a: dict, store: HandleStore) -> dict:
    """JSON 封筒(引数)→ 配列 sort はハンドル、非配列は値。壊れた封筒は -32602。"""
    import numpy as np
    import fullseye

    has_json = a.get("json") is not None
    has_env = a.get("envelope") is not None
    if has_json == has_env:
        raise ArgError("json(文字列)か envelope(オブジェクト)のどちらか一方を渡すこと")
    # T4 の兄弟: schema の maxLength は import 時の既定。いまの mcp_response_budget で呼ぶたびに測る。
    if has_json and isinstance(a["json"], str) and len(a["json"]) > _response_budget():
        raise ArgError("json は %d 文字で、上限 mcp_response_budget=%d を超える" % (len(a["json"]), _response_budget()))
    # ★2026-11-05(敵対的検証 C10): 宣言された形を、確保する**前**にサーバの上限で検査する
    #   (116 バイトの RLE 封筒で 576 MB を確保してから HandleStore.put が断っていた)。
    limits = {"max_bytes": int(store.max_bytes), "max_pixels": int(get_system("mcp_stack_max_pixels"))}
    try:
        value, sort = (fullseye.from_json(a["json"], **limits) if has_json
                       else fullseye.from_jsonable(a["envelope"], **limits))
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


_TASK_STORE_LOCK = __import__("threading").Lock()


def _task_store(store: HandleStore):
    """``store`` に付いた課題の保管庫(1 つの MCP セッション = 1 つの store = 1 つの保管庫)。"""
    tasks = getattr(store, "_fullseye_tasks", None)
    if tasks is None:
        with _TASK_STORE_LOCK:                                  # 遅延生成の取り合いで 2 つ作らない
            tasks = getattr(store, "_fullseye_tasks", None)
            if tasks is None:
                from .tasks import TaskStore
                try:
                    tasks = TaskStore()
                except ValueError as exc:                       # 実験モードの設定の不備は fail-closed
                    raise ArgError("課題の保管庫を作れない(設定の不備): %s" % exc) from None
                if tasks.audit_path and any(
                        os.path.realpath(tasks.audit_path) == r or
                        os.path.realpath(tasks.audit_path).startswith(r + os.sep) for r in store.roots):
                    raise ArgError("FULLSEYE_TASK_AUDIT_PATH が MCP の根の中にある(load_image で読めてしまう)")
                store._fullseye_tasks = tasks
    return tasks


_INPUT_INDEPENDENT: frozenset | None = None


def _input_independent_ops() -> frozenset:
    """出力が入力の中身に依存しない op の一覧(tools/gen_mcp_input_independent.py が機械的に作る)。"""
    global _INPUT_INDEPENDENT
    if _INPUT_INDEPENDENT is None:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "data", "MCP_INPUT_INDEPENDENT.json")
        try:
            with open(path, encoding="utf-8") as fh:
                _INPUT_INDEPENDENT = frozenset(json.load(fh)["ops"])
        except (OSError, ValueError, KeyError) as exc:          # 一覧が無ければ採点しない(fail-closed)
            raise ArgError("入力に依存しない op の一覧が読めない: %s" % exc) from None
    return _INPUT_INDEPENDENT


def _bad_params(stages: list) -> list[dict]:
    """採点で許す params の値は 数・文字列・真偽・null と ``{"ref": …}`` だけ。配列・入れ子の辞書は断る。

    ★2026-11-10(独立レビュー第 2 巡 N3): ``decode_fringe`` の ``ref_phase`` に 64x96 の配列をそのまま
    書くと受け付けられ、出力 = 復号 − 書いた配列 になって、答えを注入して合格できた。
    """
    bad = []
    for i, stage in enumerate(stages, 1):
        for name, value in (stage.get("params") or {}).items():
            if value is None or isinstance(value, (bool, int, float, str)):
                continue
            if isinstance(value, dict) and set(value) == {"ref"}:
                continue
            bad.append({"stage": i, "op": stage.get("op"), "param": name, "type": type(value).__name__})
    return bad


def _same_output(a, b) -> bool:
    """2 つの出力がバイト単位で同じか(配列・辞書・点列・スカラー)。"""
    if isinstance(a, np.ndarray) or isinstance(b, np.ndarray) or isinstance(a, np.generic) or isinstance(b, np.generic):
        a, b = np.asarray(a), np.asarray(b)
        return a.shape == b.shape and a.dtype == b.dtype and np.array_equal(a, b)
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_same_output(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(_same_output(x, y) for x, y in zip(a, b))
    return type(a) is type(b) and a == b


def _make_task(a: dict, store: HandleStore) -> dict:
    """真値付きの課題を作る。真値は保管庫に残し、返り値には入力のハンドルと課題文だけを載せる。"""
    from .tasks import FAMILIES, TaskError, public_task
    tasks = _task_store(store)
    try:
        rec = tasks.make(a["kind"], a["seed"], a.get("params"))
    except TaskError as exc:                                 # 知らない族・つまみ・範囲外は引数違反
        raise ArgError("%s: %s" % (exc.reason, exc)) from None
    fam = FAMILIES[rec.kind]
    meta = store.put(rec.input, sort=fam.input_sort, provenance=[{"task": rec.task_id}])
    body = public_task(rec, tasks.ttl_s, tasks.max_attempts)
    body["input"]["handle"] = meta["handle"]
    body["attempts_used"] = rec.attempts
    body["mode"] = tasks.mode
    body["feedback_cap"] = tasks.feedback_cap
    body["scoring_version"] = tasks.scoring_version
    body["next_call"] = {"tool": "fullseye_score_pipeline",
                         "arguments": {"task_id": rec.task_id, "stages": [{"op": "<op>"}]}}
    metrics = ", ".join("%s<=%g %s" % (m["name"], m["tolerance"], m["unit"]) for m in body["metrics"])
    text = ("課題 %s(%s, seed=%d): %s\n入力: %s %s handle=%s(段の inputs は have:%s か stage:N だけ)\n"
            "出力: %s(%s)\n許容: %s\n次: fullseye_score_pipeline(task_id=%s, stages=[...])"
            % (rec.kind, fam.field, rec.seed, fam.statement, fam.input_sort, list(fam.shape),
               meta["handle"], fam.input_sort, fam.output_form, "/".join(fam.output_sorts), metrics, rec.task_id))
    _log("task", rec.task_id, rec.kind, "seed=%d" % rec.seed, "mode=%s" % tasks.mode)
    return tool_result(text, body)


def _foreign_refs(stages: list, input_sort: str) -> list[dict]:
    """課題の入力(``have:<input_sort>``)と前段(``stage:N``)以外を読む参照を全部挙げる。

    ★2026-11-10(独立レビュー F1): 以前は段の ``inputs`` に任意の ``fullseye://`` ハンドルを
    書けた。``fullseye_import_json`` で取り込んだ答えや他の課題の入力を ``identity`` /
    ``count_obj`` に通すだけで、画像処理をせずに合格できた(2 回の問い合わせで偽造)。
    """
    import re
    have = "have:%s" % input_sort
    bad = []
    for i, stage in enumerate(stages, 1):
        refs = [("inputs", r) for r in stage.get("inputs", []) or []]
        refs += [("params.%s" % k, v["ref"]) for k, v in (stage.get("params") or {}).items()
                 if isinstance(v, dict) and "ref" in v]
        for where, ref in refs:
            if not (isinstance(ref, str) and (ref == have or re.fullmatch(r"stage:[1-9][0-9]*", ref))):
                bad.append({"stage": i, "op": stage.get("op"), "where": where, "ref": ref})
    return bad


def _depends_on_input(checked: dict, stages: list, input_sort: str) -> tuple[bool, list[int]]:
    """最終段が課題の入力に(依存の経路をたどって)依存しているか。入力の無い段(生成源)も返す。"""
    have = "have:%s" % input_sort
    rows = {s["stage"]: s for s in checked["stages"]}
    sources = [n for n, s in rows.items() if not s.get("inputs")]
    memo: dict[int, bool] = {}

    def dep(n: int) -> bool:
        if n in memo:
            return memo[n]
        memo[n] = False                                         # 循環は validate が先に断る。保険
        refs = list(rows[n].get("inputs") or [])
        refs += [v["ref"] for v in (stages[n - 1].get("params") or {}).values()
                 if isinstance(v, dict) and "ref" in v]
        ok = False
        for ref in refs:
            if ref == have:
                ok = True
            elif isinstance(ref, str) and ref.startswith("stage:") and int(ref[6:]) in rows:
                ok = ok or dep(int(ref[6:]))
        memo[n] = ok
        return ok
    return dep(len(stages)), sources


def _score_pipeline(a: dict, cat: Catalog, store: HandleStore) -> dict:
    """組んだ処理を課題の入力で走らせ、最終段の出力を真値で採点する(fail-closed)。

    合格は「段が課題の入力と前段だけを読み、型の門を通り、例外なく走り、出力が有限・非空・非定数で、
    全指標が許容内」のときだけ。それ以外は ``passed: false`` と ``reason``(機械が読む符号)を返す。
    採点が成り立った不合格(``out_of_tolerance``)は ``isError: false``、採点が成り立たなかった不合格は
    ``isError: true``。返り値に載せるのは段ごとの op・状態・型だけで、段の出力の値や統計は載せない
    (正しい処理の出力は真値そのものに近いので、載せると採点の返り値から真値が読める)。
    指標の詳しい値は ``feedback`` の段階に関わらず監査ログ(stderr)に残す。
    """
    from .tasks import (FAMILIES, TaskError, effective_feedback, render_feedback, score_output)
    tasks = _task_store(store)
    task_id = a["task_id"]
    try:
        level, capped = effective_feedback(a.get("feedback"), tasks.feedback_cap)
    except TaskError as exc:
        raise ArgError("%s: %s" % (exc.reason, exc)) from None

    def refuse(reason: str, message: str, **extra) -> dict:
        body = {"task_id": task_id, "passed": False, "reason": reason, "message": message,
                "feedback_level": level, **extra}
        _log("score", task_id, "refused", reason)
        try:
            tasks.audit({"task_id": task_id, "passed": False, "reason": reason, "attempt": extra.get("attempts_used"),
                         "mode": tasks.mode, "stages": a.get("stages"), "time": time.time()})
        except OSError:
            pass
        return _tool_error("不合格(%s): %s" % (reason, message), body)

    try:
        rec = tasks.claim(task_id)
    except TaskError as exc:
        return refuse(exc.reason, str(exc))
    fam = FAMILIES[rec.kind]
    base = {"kind": rec.kind, "attempts_used": rec.attempts, "max_attempts": tasks.max_attempts,
            "mode": tasks.mode, "scoring_version": tasks.scoring_version}
    if capped:
        base["feedback_capped"] = True
    stages = a["stages"]
    # 0. 課題の入力に縛る(F1): 段が読めるのは have:<入力の型> と stage:N だけ
    foreign = _foreign_refs(stages, fam.input_sort)
    if foreign:
        return refuse("foreign_input", "段が課題の入力と前段以外を読もうとした(読めるのは have:%s と stage:N だけ)"
                      % fam.input_sort, refs=foreign, **base)
    literal = _bad_params(stages)
    if literal:
        return refuse("param_not_allowed", "params に書けるのは 数・文字列・真偽・{\"ref\": …} だけ"
                      "(配列や入れ子の辞書でデータを持ち込めない)", params=literal, **base)
    # 0b. 入力の中身に依存しない op(生成の op など)を断る(N1、機械的に作った一覧)
    independent = [{"stage": i, "op": st.get("op")} for i, st in enumerate(stages, 1)
                   if st.get("op") in _input_independent_ops()]
    if independent:
        return refuse("input_independent", "入力の中身を読まない op がある(生成の op など): %s"
                      % ", ".join("段 %d %s" % (r["stage"], r["op"]) for r in independent),
                      ops=independent, **base)
    handle = store.put(rec.input, sort=fam.input_sort, provenance=[{"task": rec.task_id}])["handle"]
    # 1. 型の門(1 段も走らせない)。fullseye_pipeline と同じ検査器・同じ束縛名を使う。
    checked = validate_pipeline(stages, fam.input_sort, cat,
                                bindings={"have:%s" % fam.input_sort: handle}, store=store)
    if not checked["valid"]:
        return refuse("type_gate", "型の門で不合格(1 段も走らせていない)", errors=checked["errors"], **base)
    if checked.get("out_sort") not in fam.output_sorts:
        return refuse("output_sort_mismatch", "最終段の型 %s は採点できない(要るのは %s)"
                      % (checked.get("out_sort"), "/".join(fam.output_sorts)), **base)
    depends, sources = _depends_on_input(checked, stages, fam.input_sort)
    if sources:
        return refuse("foreign_input", "入力を読まない段(生成源)がある: 段 %s" % sources, **base)
    if not depends:
        return refuse("foreign_input", "最終段が課題の入力に依存していない", **base)
    # 2. 実行(fullseye_pipeline と同じ実行器。返り値は内部でだけ使うので上限で落とさない)
    try:
        res = _pipeline_dag({"handle": handle, "stages": stages, "vision": "none"}, cat, store,
                            max_structured_bytes=1 << 30)
    except ArgError as exc:
        return refuse("pipeline_refused", str(exc)[:400], **base)
    except Exception as exc:                                    # noqa: BLE001 - 例外は不合格の理由
        return refuse("exception", "%s: %s" % (type(exc).__name__, str(exc)[:300]), **base)
    sc = res.get("structuredContent") or {}
    summary = [{k: r[k] for k in ("stage", "op", "status", "out_sort", "reason") if r.get(k) is not None}
               for r in sc.get("stages", [])]
    if res.get("isError"):
        bad = next((r for r in sc.get("stages", []) if r.get("status") == "failed"), {})
        err = bad.get("error") or {}
        reason = "invalid_output" if bad.get("reason") == "invalid_output" else "execution_failed"
        return refuse(reason, "段 %s %s が失敗(%s%s)" % (
            bad.get("stage"), bad.get("op"), bad.get("reason"),
            (": %s: %s" % (err.get("type"), str(err.get("message"))[:200])) if err else ""),
            stages=summary, **base)
    rows = sc.get("outputs") or []
    if not rows:
        return refuse("empty_output", "最終段の出力が無い", stages=summary, **base)
    try:
        value = store.get(rows[-1]["handle"])[1]
    except HandleError as exc:
        return refuse("empty_output", str(exc), stages=summary, **base)
    # 3. 真値と比べる
    try:
        metrics = score_output(rec, value)
    except TaskError as exc:
        return refuse(exc.reason, str(exc), stages=summary, **base)
    except Exception as exc:                                    # noqa: BLE001 - 採点できない形は不合格
        return refuse("unscorable_output", "%s: %s" % (type(exc).__name__, str(exc)[:200]),
                      stages=summary, **base)
    # 3b. (採点できる形の出力だけ)隠れた双子の課題で同じ処理を走らせる(N1・R2、実行時の検査)
    #   - 出力がバイト単位で同じ → 入力を読んでいない(input_independent)
    #   - 本体が合格したなら、双子でもその真値に合格しなければならない(hidden_check_failed)。
    #     固定の答えは真値の違う 2 つの課題の両方には合格できない。双子の誤差は返さない。
    try:
        alt_rec = tasks.alternate(rec)
        alt = alt_rec.input
        alt_handle = store.put(alt, sort=fam.input_sort, provenance=[{"task_alt": rec.task_id}])["handle"]
        alt_res = _pipeline_dag({"handle": alt_handle, "stages": stages, "vision": "none"}, cat, store,
                                max_structured_bytes=1 << 30)
        alt_rows = (alt_res.get("structuredContent") or {}).get("outputs") or []
        alt_value = store.get(alt_rows[-1]["handle"])[1] if (alt_rows and not alt_res.get("isError")) else None
    except Exception as exc:                                    # noqa: BLE001 - 検査できなければ採点しない
        return refuse("input_check_failed", "入力を変えた写しで走らせられなかった(%s)" % type(exc).__name__,
                      stages=summary, **base)
    if alt_value is None:
        return refuse("input_check_failed", "入力を変えた写しでは処理が走り切らなかった", stages=summary, **base)
    if _same_output(value, alt_value):
        return refuse("input_independent", "入力を変えても最終段の出力が同じ(入力の中身を読んでいない)",
                      stages=summary, **base)
    hidden_passed = None
    twin_metrics = None
    if all(m["passed"] for m in metrics):
        try:
            twin_metrics = score_output(alt_rec, alt_value)
            hidden_passed = all(m["passed"] for m in twin_metrics)
        except Exception:                                       # noqa: BLE001 - 双子で採点できない形も不合格
            hidden_passed = False
        tasks.audit({"task_id": task_id, "hidden_seed_check": "passed" if hidden_passed else "failed",
                     "attempt": rec.attempts, "time": time.time()})
        if not hidden_passed and level == "detailed":
            return refuse("hidden_check_failed", "隠れた双子の課題(真値の違う同じ族)では合格しなかった"
                          "(固定の答え・課題の 1 枚にだけ合う処理は合格にしない)", stages=summary, **base)
    passed = all(m["passed"] for m in metrics) and hidden_passed is not False
    # ★2026-11-10(独立レビュー第 4 巡): pass_fail / coarse では、双子で落ちたことを返り値で区別しない
    #   (reason は out_of_tolerance、形も許容外の不合格と同じ)。区別すると「本体には合っていた」ことが分かり、
    #   本体と双子の探索を 2 回に分けられた(計数の 13/20 が 20 回以内に合格)。区別は監査記録にだけ残す。
    #   coarse で見せる段階は、落ちた側(双子)の指標から作る。
    shown_source = metrics if hidden_passed is not False else (twin_metrics or [
        dict(m, passed=False, ratio=None) for m in metrics])
    # 監査: 詳しい値は FULLSEYE_TASK_AUDIT_PATH の記録にだけ書く。stderr には合否と回数だけ
    # ★2026-11-10(独立レビュー第 2 巡 N2): 以前は stderr の score-audit 行に誤差を書いていた。MCP の
    #   クライアントは stdio サーバの stderr をファイルに残すので、ファイルを読める agent が pass_fail の
    #   上限を迂回して誤差を読めた。
    tasks.audit({"task_id": task_id, "kind": rec.kind, "seed": rec.seed, "mode": tasks.mode,
                 "attempt": rec.attempts, "passed": passed, "feedback_level": level,
                 "metrics": [{k: m[k] for k in ("name", "error", "tolerance", "passed")} for m in metrics],
                 "stages": stages, "time": time.time()})
    _log("score", task_id, "attempt=%d" % rec.attempts, "passed" if passed else "failed")
    shown, explanation = render_feedback(shown_source, level)
    body = {"task_id": task_id, "passed": passed, "feedback_level": level, "metrics": shown,
            "explanation": explanation, "stages": summary, **base}
    if not passed:
        body["reason"] = "out_of_tolerance"
    text = ("合格" if passed else "不合格(許容外)") + "(%s、試行 %d/%d、feedback=%s)" % (
        rec.kind, rec.attempts, tasks.max_attempts, level)
    if explanation:
        text += "\n" + "\n".join(explanation)
    return tool_result(text, body)


def _write_viewer(a: dict, store: HandleStore) -> dict:
    """spec(JSON)→ 自己完結 HTML。書く先はサンドボックスの作業ディレクトリだけ(名前は検査する)。"""
    import re
    import pocviewer

    spec = a["spec"]
    if not isinstance(spec, dict):
        raise ArgError("spec はオブジェクトでなければならない(%s)" % type(spec).__name__)
    langs = a.get("lang", ["ja"])
    if not all(isinstance(x, str) for x in langs):
        raise ArgError("lang は文字列の配列でなければならない")
    name = a.get("name") or str(spec.get("id", "viewer"))
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", name):
        raise ArgError("name は英数字と _ - だけ(64 文字まで): %r" % name)
    try:                                                   # 信頼境界: spec は untrusted、形違いは -32602
        text = pocviewer._build_html(spec, langs)
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise ArgError("spec が不正: %s" % exc) from None
    path = os.path.join(store.thumb_dir, name + ".html")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    size = len(text.encode("utf-8"))
    tabs = [t["id"] for t in spec["tabs"]]
    body = ("ビューアを書いた: %s(%.2f MB、タブ %d 本: %s、言語 %s)。ブラウザで開くだけで動く"
            "(外部の読み込み無し)。URL の ?lang=xx で開く言語、?tab=<id> で開くタブを選べる。"
            % (os.path.basename(path), size / 1e6, len(tabs), ", ".join(tabs), "/".join(langs)))
    return tool_result(body, {"path": path, "bytes": size, "tabs": tabs, "lang": list(langs)},
                       links=[_file_link(path, os.path.basename(path), "text/html", "自己完結の HTML ビューア")])


def call_tool(name: str, args: Any, cat: Catalog, store: HandleStore | None = None, *,
              max_structured_bytes: int | None = None) -> dict:
    """tool 本体。引数違反は ArgError(= -32602)、実行の失敗は isError の結果。"""
    max_structured_bytes = _response_budget(max_structured_bytes)
    if name not in TOOLS:
        raise ArgError("知らない tool: %r(あるのは %s)" % (name, sorted(TOOLS)))
    profile = os.environ.get("FULLSEYE_MCP_PROFILE", "full")
    if name not in _profile_tool_names(profile):
        raise ArgError("tool %r is not available in MCP profile %r" % (name, profile))
    a = _validate(TOOLS[name]["inputSchema"], args if args is not None else {})
    store = store if store is not None else HandleStore()
    if name in ("fullseye_plan", "fullseye_describe", "fullseye_choose"):
        from fullseye.opsearch import plan, describe, choose
        if name == "fullseye_plan":
            # ★2026-11-05(敵対的検証 第 2 巡 D10): schema を通る want="" / goal="   " が search_ops の
            #   ValueError のまま抜けて -32603(内部エラー)になっていた。空白だけの語は引数違反(-32602)。
            for key in ("want", "goal"):
                if isinstance(a.get(key), str) and not a[key].strip():
                    raise ArgError("%s が空(空白だけ)の文字列" % key)
            r = plan(a["have"], a["want"], a.get("direction", "forward"), a.get("pattern"), goal=a.get("goal"))
        elif name == "fullseye_describe":
            r = describe(a["kind"], a["name"])
        else:
            r = choose(a["candidates"], a.get("constraints"))
        if name == "fullseye_plan" and r.get("ok"):
            lines = []
            for number, proposal in enumerate(r.get("plans", ()), 1):
                stages = " -> ".join(proposal.get("ops", ()))
                types = "%s -> %s" % (",".join(r.get("have", ())), r.get("want"))
                evidence = ", ".join("%s→%s +%g" %
                                     (ev["term"], ev["op"], ev["points"])
                                     for ev in proposal.get("evidence", ()))
                lines.append("%d | %s | %s%s" %
                             (number, stages, types, " | evidence: " + evidence if evidence else ""))
            text = "\n".join(lines)
        else:
            text = json.dumps(r, ensure_ascii=False, indent=2)
        return tool_result(text, r, max_structured_bytes=max_structured_bytes) if r["ok"] else _tool_error(text, r)
    if name in ("fullseye_search_ops", "fullseye_find_ops"):
        # ★2026-10-11: find_ops は「既知の種別以外は拒否する」と書きながら typo を受け、
        # 0 件を返していた。search_ops と同じ門を通す。
        from fullseye.opsearch import known_sorts, normalize_sort
        for k in ("in_sort", "out_sort"):
            if a.get(k):
                a[k] = normalize_sort(a[k])
            if a.get(k) and a[k] not in known_sorts():
                raise ArgError("%s=%r は知らない種別(あるのは %s)" % (k, a[k], cat.sorts))
    if name == "fullseye_search_ops":
        r = cat.search(a.get("query", ""), in_sort=a.get("in_sort"), out_sort=a.get("out_sort"),
                       source=a.get("source"), limit=a.get("limit", 20))
        return tool_result(_search_text(r), r, max_structured_bytes=max_structured_bytes)
    if name == "fullseye_find_ops":
        from fullseye.opsearch import _format, search_ops, tuning_cards
        try:
            from fssystem import get_system
            total_limit = int(a.get("limit", get_system("find_ops_k")))
            # limit = the total number of proposals (ops + recipes) for every value,
            # not only the default.  Recipes take at most find_ops_recipe_max slots
            # and always leave one for an operator; the rest are operator rows.  The
            # split depends on limit alone, so a larger limit never returns fewer
            # ops (red-team 2026-11-05: limit 5/6/7/8 gave 5/6/5/8 ops, because only
            # a limit equal to the default reserved the recipe slots).
            recipe_limit = max(0, min(get_system("find_ops_recipe_max"), total_limit - 1))
            op_limit = total_limit - recipe_limit
            r = search_ops(a["query"], op_limit, lang=a.get("lang"),
                           in_sort=a.get("in_sort"), out_sort=a.get("out_sort"))
        except ValueError as exc:                          # 空の問い合わせ等は引数違反(-32602)
            raise ArgError(str(exc)) from exc
        from fullseye.recipesearch import find_recipes
        # ★2026-11-03: 索引に Python で呼ぶレシピ(台帳 op、kw 引数つき)が入った。MCP の pipeline で
        #   走らないレシピを出すと、組めない手順を勧めることになるので runner="mcp" だけを返す。
        r["recipes"] = find_recipes(a["query"], limit=recipe_limit, lang=a.get("lang"),
                                      in_sort=a.get("in_sort"), out_sort=a.get("out_sort"), runner="mcp")
        r["tuning_cards"] = tuning_cards(a["query"], [row["name"] for row in r["ops"]], limit=3)
        if a.get("detail"):
            text = _format(r)
            for recipe in r["recipes"]:
                text += "\nrecipe: %s [%s -> %s] %s" % (recipe["name"], recipe["input_sort"], recipe["output_sort"], recipe["when"])
        else:
            lines = []
            for op in r["ops"]:
                purpose = " ".join(op.get("summary", "").replace("\n", " ").split()[:12]) or "目的説明なし"
                aliases = op.get("same_as") or []
                alias_text = (" = " + " = ".join(aliases)) if aliases else ""
                lines.append("%s%s | %s → %s | %s | next: %s" %
                             (op["name"], alias_text, op.get("in_sort") or "?",
                              op.get("out_sort") or "?", purpose, op.get("next_call", "?")))
            for op in r.get("retry_ops", []):
                lines.append("retry[%s]: %s | %s → %s | next: %s" %
                             (op["retry_query"], op["name"], op.get("in_sort") or "?",
                              op.get("out_sort") or "?", op.get("next_call", "?")))
            for recipe in r["recipes"]:
                ops = [stage[0] if isinstance(stage, list) else stage.get("op", "?")
                       for stage in recipe.get("stages", [])]
                lines.append("recipe: %s | %d stages | %s" %
                             (recipe["name"], len(ops), " → ".join(ops)))
            text = "\n".join(lines) or _format(r)
        r["proposals"] = ([{"kind": "op", **row} for row in r["ops"]] +
                          [{"kind": "retry_op", **row} for row in r.get("retry_ops", [])] +
                          [{"kind": "recipe", **row} for row in r["recipes"]])[:total_limit]
        return tool_result(text, r, max_structured_bytes=max_structured_bytes)
    if name == "fullseye_suggest_pipeline":
        from fullseye.opsearch import normalize_sort, search_ops, op_cards
        start, goal = normalize_sort(a["start_sort"]), normalize_sort(a["goal_sort"])
        if not a["query"].strip():                       # D10: blank query = -32602, not an internal error
            raise ArgError("query が空白だけの文字列")
        found = search_ops(a["query"], 5, in_sort=start, out_sort=goal)
        candidates = found["ops"] or found.get("retry_ops", [])
        qkey = a["query"].strip().lower().replace(" ", "_")
        exact = [row for row in candidates if qkey in
                 {str(row.get("name", "")).lower(), str(row.get("halcon", "")).lower()}]
        unique = len(candidates) == 1 or len(exact) == 1
        chosen = exact[0] if len(exact) == 1 else (candidates[0] if len(candidates) == 1 else None)
        result = {"ok": bool(chosen), "unique": bool(chosen), "query": a["query"],
                  "start_sort": start, "goal_sort": goal,
                  "candidates": [{k: row.get(k) for k in ("name","in_sort","out_sort","score")}
                                 for row in candidates[:5]]}
        if chosen is not None:
            stages = [{"op": chosen["name"]}]
            checked = validate_pipeline(stages, start, cat)
            result.update({"op": chosen["name"], "pipeline": {"start_sort":start,"stages":stages},
                           "validation": checked, "card": op_cards([chosen["name"]])["cards"][0],
                           "next_call": chosen.get("next_call")})
            if not checked["valid"]:
                result["ok"] = result["unique"] = False
        else:
            result["reason"] = "candidate_not_unique"
        text = json.dumps(result, ensure_ascii=False, indent=2)
        return tool_result(text, result, max_structured_bytes=max_structured_bytes)
    if name == "fullseye_plan_chain":
        from fullseye.opsearch import plan_chain
        try:
            r = plan_chain(a["query"], a["start_sort"], a["goal_sort"], a.get("k", 5), a.get("max_depth", 4))
        except ValueError as exc:
            raise ArgError(str(exc)) from exc
        return tool_result(json.dumps(r, ensure_ascii=False, indent=2), r, max_structured_bytes=max_structured_bytes)
    if name in ("fullseye_choose_op", "fullseye_required_inputs", "fullseye_param_space"):
        from fullseye.opsearch import choose_op, required_inputs, param_space
        try:
            if name == "fullseye_choose_op":
                r = choose_op(a["family"], a.get("constraints"))
            elif name == "fullseye_required_inputs":
                r = required_inputs(a["goal_sort"], a.get("max_depth", 4), a.get("k", 10))
            else:
                r = param_space(a["op"], a.get("input_context"))
        except ValueError as exc:
            raise ArgError(str(exc)) from exc
        text = json.dumps(r, ensure_ascii=False, separators=(",", ":"))
        failed = r.get("fail_closed") or (name == "fullseye_required_inputs" and not r.get("solutions"))
        return _tool_error(text, r) if failed else tool_result(text, r, max_structured_bytes=max_structured_bytes)
    if name in ("fullseye_pipeline_shape", "fullseye_patterns", "fullseye_sort_guide"):
        from fullseye.opsearch import pipeline_shape, pattern_skeleton, sort_guide
        if name == "fullseye_pipeline_shape":
            r = pipeline_shape(a["input_form"], a["output_form"])
        elif name == "fullseye_patterns":
            r = pattern_skeleton(a["name"], a["start_sort"], a["goal_sort"])
        else:
            r = sort_guide(a.get("sort"))
        text = json.dumps(r, ensure_ascii=False, indent=2)
        return (_tool_error(text, r) if r.get("found") is False else
                tool_result(text, r, max_structured_bytes=max_structured_bytes))
    if name == "fullseye_op_cards":
        from fullseye.opsearch import op_cards
        try:
            r = op_cards(a["names"], a.get("budget_tokens", 500))
        except ValueError as exc:
            raise ArgError(str(exc)) from exc
        return tool_result(json.dumps(r, ensure_ascii=False, indent=2), r, max_structured_bytes=max_structured_bytes)
    if name == "fullseye_validate_pipeline":
        # ★2026-11-05(敵対的検証 第 2 巡 T3): 上限 64 を固定で渡しており(schema に max_stages は無い)、
        #   pipeline_max_stages=16 の下で validate tool は 40 段を valid、pipeline tool は拒否と割れた。
        #   None = validate_pipeline が fssystem の pipeline_max_stages を読む(pipeline と同じ上限)。
        r = validate_pipeline(a["stages"], a.get("start_sort"), cat, max_stages=None,
                              bindings=a.get("bindings"),store=store)
        text = json.dumps(r, ensure_ascii=False, indent=2)
        return (tool_result(text, r, max_structured_bytes=max_structured_bytes) if r["valid"]
                else _tool_error(text, r))
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
        names=[r["name"] for r in rows]
        files = store.root_files()
        text = ("files: " + (", ".join(files) if files else "(なし)") + "\nsamples: " + ", ".join(names))
        return tool_result(text, {"files": files, "samples": names},
                           max_structured_bytes=max_structured_bytes)
    try:
        if name == "fullseye_load_image":
            return _load_image(a, store)
        if name == "fullseye_load_template":
            return _load_template(a, store)
        if name == "fullseye_load_stack":
            return _load_stack(a, store)
        if name == "fullseye_apply":
            return _apply(a, cat, store, max_structured_bytes=max_structured_bytes)
        if name == "fullseye_inspect":
            return _inspect(a, store, max_structured_bytes=max_structured_bytes)
        if name == "fullseye_pipeline":
            return _pipeline(a, cat, store, max_structured_bytes=max_structured_bytes)
        if name == "fullseye_fix_text":
            return _fix_text(a, store)
        if name == "fullseye_import_json":
            return _import_json(a, store)
        if name == "fullseye_export_json":
            return _export_json(a, store, max_structured_bytes=max_structured_bytes)
        if name == "fullseye_estimate_distortion":
            return _estimate_distortion(a)
        if name == "fullseye_write_viewer":
            return _write_viewer(a, store)
        if name == "fullseye_make_task":
            return _make_task(a, store)
        if name == "fullseye_score_pipeline":
            return _score_pipeline(a, cat, store)
    except HandleError as exc:
        raise ArgError(str(exc)) from exc
    raise ArgError("未実装の tool: %r" % name)                 # TOOLS に足して本体を忘れた


def dispatch(msg: dict, cat: Catalog, store: HandleStore | None = None) -> dict | None:
    """1 メッセージを処理。通知(id 無し)には返さない。"""
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0":
        return _err(msg.get("id") if isinstance(msg, dict) else None, -32600, "JSON-RPC 2.0 でない")
    req_id = msg.get("id")
    method = msg.get("method")
    params = msg.get("params")
    is_notification = "id" not in msg
    # ★2026-10-11: params が配列 / 文字列、name が配列 / dict のとき、.get や辞書引きの
    # AttributeError / TypeError が run_stdio_server のループまで抜け、サーバが死んでいた
    # (後続の正しい要求にも返事が無い)。型は境界で検査して -32602、残りは最後の網で -32603。
    if params is None:
        params = {}
    if not isinstance(params, dict):
        return None if is_notification else _err(
            req_id, -32602, "params はオブジェクトでなければならない(%s)" % type(params).__name__)
    try:
        if method == "initialize":
            res = handle_initialize(params)
        elif method == "ping":
            res = {}
        elif method == "tools/list":
            res = handle_tools_list(params)
        elif method == "tools/call":
            name = params.get("name")
            if not isinstance(name, str):
                raise ArgError("params.name は tool 名の文字列でなければならない(%s)"
                               % type(name).__name__)
            res = call_tool(name, params.get("arguments"), cat, store)
            _log("tools/call", name, "ok" if not res.get("isError") else "isError")
        elif method in ("notifications/initialized", "notifications/cancelled"):
            return None
        else:
            if is_notification:
                return None
            return _err(req_id, -32601, "知らない method: %r" % method)
    except ArgError as exc:
        _log("tools/call", repr(params.get("name"))[:80], "-32602", str(exc)[:200])
        return None if is_notification else _err(req_id, -32602, str(exc), data=exc.data)
    except CatalogError as exc:
        return None if is_notification else _err(req_id, -32603, "カタログ: %s" % exc)
    except Exception as exc:                                    # noqa: BLE001 - 最後の網: ループを殺さない
        _log(str(method)[:40], "-32603", "%s: %s" % (type(exc).__name__, str(exc)[:200]))
        return None if is_notification else _err(
            req_id, -32603, "内部エラー(%s): %s" % (type(exc).__name__, str(exc)[:400]))
    return None if is_notification else _ok(req_id, res)


def run_stdio_server(stdin=None, stdout=None, *, catalog: Catalog | None = None,
                     store: HandleStore | None = None) -> int:
    """EOF まで回す。壊れたフレームには -32700 を返して続ける。"""
    stdin = stdin if stdin is not None else sys.stdin.buffer
    stdout = stdout if stdout is not None else sys.stdout.buffer
    cat = catalog if catalog is not None else Catalog.load()
    store = store if store is not None else HandleStore()
    # ★2026-09-20(GenSpark 第 38 報 N135): 「2390 names」が op 数と読まれた —— 数えているのは op 名 + HALCON 別名。
    _log("ready: %d catalog names (op names + HALCON aliases; ops = fullseye_catalog_coverage), %d sorts, roots=%s"
         % (len(cat.entries), len(cat.sorts), store.roots))
    framing = FRAMING_HEADERS            # 相手が最後に使った枠で返す(最初の 1 通が来るまでは従来の形)
    while True:
        try:
            got = read_framed(stdin)
        except FramingError as exc:
            write_message(stdout, _err(None, -32700, str(exc)), framing=framing)
            continue
        if got is None:
            return 0
        msg, framing = got
        if not isinstance(msg, dict):
            # ★2026-11-13: 本文が null の 1 通で黙って終了していた。要求の形でない本文は -32600 を返して続ける
            # (配列 = JSON-RPC のバッチは受け付けない)。
            write_message(stdout, _err(None, -32600, "要求は JSON のオブジェクトで送る(受け取った型: %s)"
                                       % type(msg).__name__), framing=framing)
            continue
        resp = dispatch(msg, cat, store)
        if resp is not None:
            write_message(stdout, resp, framing=framing)


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
        coins = "coins"
        tool("fullseye_search_ops", query="threshold", limit=5)
        h = tool("fullseye_load_image", path=coins)["structuredContent"]["handle"]
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
