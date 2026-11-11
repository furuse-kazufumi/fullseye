# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""AI が Fullseye の op を組んだ検査を、公開実データの真値で採点する(手組み・既存のレシピ・良品学習と並べる)。

Score inspection recipes that an AI assembled from Fullseye operators against the ground truth of
public real data, side by side with a hand-built recipe, Fullseye's existing recipes and a learned baseline.

## 何をするか / What it does

1. 課題を自然言語で渡す(:data:`TASKS`)。AI はローカル LLM(14B と 32B のコード向け、課題・模型ごとに 10 回)で、
   Fullseye の **MCP サーバ(minimal)だけ**を道具に、op を探し(``fullseye_find_ops`` = 索引の RAG)、型の鎖を確かめ、
   開発用の 6 枚で試すよう**指示されて**レシピ(op の列)を返す。実際に開発用画像を読んだかは記録から数える
   (:func:`used_dev_images`)。AI を呼ぶのは手元の ``tools/gen_ai_inspection_recipes.py`` だけで、出てきたレシピは
   :data:`RECIPES_JSON` に**全部**保存してある(レシピを返せなかった回・壊れたレシピも消さない)。
2. 取り直しの便(phase)を分けて並べる(:data:`PHASES`)。第 1 便は道具が文脈長を渡しておらず、サーバの既定
   4,096 トークンで古い発言(課題文)が捨てられていた疑いが強い(作者と独立の検証で発見、手元で再現)。第 2 便は
   文脈長 32,768 を渡して取り直した(MCP は直す前)。第 3 便は MCP の不備(作業場所のファイルを一覧に出さない、
   無い名前の拒否に読める名前を添えない、検証が a/b の範囲外を通す、a/b を params に入れた形に直し方を返さない、
   ひび割れ・汚れの問い合わせに bothat / hx_plane_deviation が出ない)を直した後。直す前と後の成功率を並べる。
3. 比べる列: **クラウドの LLM エージェント**にも組ませた(``tools/mcp_replay_session.py``、課題ごとに 3 回、MCP は直す前)。
   クラウドなのでローカル LLM と混ぜず、別の列にする。そろえた条件 = 同じ MCP(minimal)・同じ課題文と指示文・
   画素を見ない・道具の呼び出しは 24 回まで(ローカルの道具は発言の頭でしか数えて
   いなかったので最大 33 回まで走った回がある。採点は **24 回目までの呼び出しで切ったレシピ** で行う ——
   :func:`capped_recipe`)。そろっていない条件(:data:`CONDITION_GAPS`、表 06 の注にも出す): ローカルだけに
   催促(試走せずに答えた時と JSON で答えなかった時に 1 回ずつ)がある / クラウドの模型の製品名は書かない方針で、
   温度は土台が出さない。土台は汎用のコーディング エージェント(依頼文で repo とデータを読まないよう指示)/
   クラウドの 6 本は CLI の応答を自前のコマンド(先頭だけ切る・JSON を解析する・grep)で切り出して読んだ
   (依頼文違反。ローカルは同じ長さに切った応答を全文そのまま読む)。
4. この PoC は保存したレシピを MCP の ``fullseye_pipeline`` と同じ入口(``call_tool``)で**決定的に**
   走らせ、試験画像の真値で採点する。AI はここでは呼ばない。
5. 並べるもの: 上の AI の列 / 開発側の手組み(開発に使っているクラウド LLM が Fullseye の内部を知った上で、
   同じ開発用 6 枚だけを見て、試行の上限なしに組んだ。試験画像では調整していない。**人ではない**)/ Fullseye の
   既存レシピ(``recipes.py`` の外観検査 2 本をそのまま)/ 既存の良品学習(``patchbank_fit``、良品 20 枚で学習し
   別の良品 10 枚で閾値を較正。MCP からは呼べない Python の経路)。
6. 採点は 1 つの数字にしない: 検出率・誤報率・面積の AUROC・(欠陥マスクのある課題は)欠陥領域に触れた割合と
   画素の誤報率・壊れ方・1 枚あたりの処理時間・段数。「選り分ける」は平衡正解率の 95 % 区間の下限が 0.5 を
   超えること(偶然を有意に超える)。失敗は「道具 / MCP の不備 / 模型」に帰属させて数える(:func:`attribute`)。

## 課題と真値 / Tasks and ground truth

* ``crack`` —— コンクリート壁の写真(227 × 227、灰色化)からひび割れのある画像を選り分ける。真値は配布元の
  ラベル(ひび割れあり / なし)。試験 400 枚(各 200、ファイル名順に等間隔で選ぶ)。
  Özgenel, Ç. F. (2019). Concrete Crack Images for Classification. Mendeley Data, v2.
  doi:10.17632/5y9wdsg2zt.2。ライセンス: "CC BY 4.0"(配布元の記録の License 欄)。改変: 灰色化。
  環境変数 ``FULLSEYE_CRACK_DATA`` に ``Positive/`` と ``Negative/`` を展開した dir を渡す。
* ``candle`` —— 4 本のろうそくの写真(VisA candle、1/4 に縮小・灰色化)から汚れ・欠け・異物を見つける。
  真値は配布元の画素マスク。試験 197 枚(異常 97・良品 100。異常 3 枚は開発用に回した)。
  Zou, Y., Jeong, J., Pemula, L., Zhang, D., Dabeer, O. (2022). SPot-the-Difference Self-Supervised
  Pre-training for Anomaly Detection and Segmentation. ECCV 2022. https://github.com/amazon-science/spot-diff 、
  "The data is released under the CC BY 4.0 license."。改変: 灰色化と 4×4 平均の縮小。
  環境変数 ``FULLSEYE_VISA_DATA`` に VisA を展開した dir(``split_csv/1cls.csv`` と ``candle/`` がある所)。

使うファイルの一覧は :data:`DATA_PINS` の SHA-256(ファイル名と中身の SHA-256 を並べた一覧の SHA-256)で固定し、
食い違えば止まる(fail-closed)。ダウンロード物は信頼しない入力として画像と CSV を読むだけ。

## CI / 記録 / CI and the record

実データは repo に入れない。CI(データ無し)は次を走らせる: レシピの記録そのものの指紋
(:data:`RECIPES_SHA256`)/便・模型ごとの回数/第 2 便以降が今の課題文・指示文で作られ、文脈の切り詰めの印が
無いこと/保存したレシピ全部を MCP の検証器(``validate_pipeline``、データ不要)に通して「型の鎖が切れている」数を
数え直す/採点の記録 :data:`SCORES_JSON` の行がいまのレシピの SHA-256 と 1 対 1 に対応する/見出しの数字
(:data:`HEADLINE`)が記録と一致する/採点の関数を既知の答えの小さな入力で検算する。データがあるときは全部を採点し直し、記録と一致すること
(処理時間を除く)を門にする。``FULLSEYE_AISCORE_RECORD=1`` で記録を書き直す。

実行例::

    py -3.11 examples/poc_ai_built_inspection_scored.py
    # 実データあり(手元):
    $env:FULLSEYE_CRACK_DATA = "<Positive/Negative のある dir>"; $env:FULLSEYE_VISA_DATA = "<VisA の dir>"
    py -3.11 examples/poc_ai_built_inspection_scored.py

図(``FULLSEYE_FIGURE_DIR`` があり、実データもあるとき): 試験画像に各レシピの検出を重ねた図(代表)、
課題ごとの検出率と誤報率の散布、まとめの表、失敗の帰属と直す前後の表。
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import statistics
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402
import realdata  # noqa: E402
import recipes as fa_recipes  # noqa: E402
from fullseye.mcp.catalog import Catalog  # noqa: E402
from fullseye.mcp.handles import HandleStore  # noqa: E402
from fullseye.mcp.server import call_tool, validate_pipeline  # noqa: E402

RECIPES_JSON = ROOT / "examples" / "data" / "ai_inspection_recipes_2026_11_08.json"
SCORES_JSON = ROOT / "examples" / "data" / "ai_inspection_scores_2026_11_08.json"
CRACK = os.environ.get("FULLSEYE_CRACK_DATA", "").strip()
VISA = os.environ.get("FULLSEYE_VISA_DATA", "").strip()
RECORD = os.environ.get("FULLSEYE_AISCORE_RECORD", "").strip() == "1"
#: 良品学習の結果を置く repo 外の dir(任意)。学習に数分かかるので、図を作り直すときの待ちを省く。
#: 鍵はデータの指紋なので、データが変われば使われない。
CACHE = os.environ.get("FULLSEYE_AISCORE_CACHE", "").strip()

CRACK_SOURCE = ("Özgenel, Ç. F. (2019). Concrete Crack Images for Classification. Mendeley Data, v2. "
                "doi:10.17632/5y9wdsg2zt.2. CC BY 4.0; converted to gray")
VISA_SOURCE = ("VisA candle (Zou et al., ECCV 2022), github.com/amazon-science/spot-diff, CC BY 4.0; "
               "gray + 4x4 mean downsampling")

#: 課題(AI に渡す文の正本)。``request`` を変えたら AI のレシピを作り直す(JSON に文の SHA-256 が残る)。
TASKS = {
    "crack": {
        "title": "コンクリートのひび割れ",
        "request": (
            "コンクリート壁を撮った灰色の写真(227 × 227 画素、値は 0〜1)から、ひび割れを見つける検査を組んでください。"
            "検査の出力は、ひび割れの画素を前景とする領域(region)です。ひび割れの無い画像では領域が空になり、"
            "ひび割れのある画像では空でない領域が出るのが合格です。表面には小さな穴や粒の模様があり、明るさは画像ごとに違います。\n"
            "開発用の画像(fullseye_load_image で読めます。例: fullseye_load_image(path=\"crack_dev_defect_1.png\")):\n"
            "- crack_dev_defect_1.png, crack_dev_defect_2.png, crack_dev_defect_3.png(ひび割れあり)\n"
            "- crack_dev_good_1.png, crack_dev_good_2.png, crack_dev_good_3.png(ひび割れなし)\n"
            "fullseye_pipeline で試し、ひび割れありでは前景が出て、なしでは前景が 0 になる op の列と引数を選んでください。"),
    },
    "candle": {
        "title": "ろうそくの汚れ・欠け",
        "request": (
            "黒い布の上に並んだ 4 本の白いろうそくを上から撮った灰色の写真(321 × 292 画素、値は 0〜1)から、"
            "ろうそくの表面の汚れ・欠け・異物を見つける検査を組んでください。検査の出力は、欠陥の画素を前景とする領域(region)です。"
            "欠陥の無い画像では領域が空になり、欠陥のある画像では欠陥の所に空でない領域が出るのが合格です。"
            "どのろうそくにも中央に芯の小さな穴があり、これは欠陥ではありません。欠陥の大きさは数画素から千画素を超えるものまでまちまちで(開発用の 3 枚では 100〜220 画素)、薄いものもあります。\n"
            "開発用の画像(fullseye_load_image で読めます。例: fullseye_load_image(path=\"candle_dev_defect_1.png\")):\n"
            "- candle_dev_defect_1.png, candle_dev_defect_2.png, candle_dev_defect_3.png(欠陥あり)\n"
            "- candle_dev_good_1.png, candle_dev_good_2.png, candle_dev_good_3.png(欠陥なし)\n"
            "fullseye_pipeline で試し、欠陥ありでは前景が出て、なしでは前景が 0 になる op の列と引数を選んでください。"),
    },
}

#: 開発側の手組み。開発に使っているクラウド LLM が、Fullseye の op と内部を知った上で、AI と**同じ開発用 6 枚だけ**を
#: 走らせ、試行の上限なしに組んだ(人ではない。AI の列と条件はそろっていない —— 公平な比較はクラウド LLM の列)。
#: 試験画像では一度も調整していない(採点は組み終えた後に 1 回)。
#: Developer-built recipes: written by the cloud LLM that develops this PoC, knowing Fullseye's internals, with no
#: trial limit, tuned on the same six development images only, never on the test set. Not a human.
HAND = {
    # ひび割れは周りより暗い太い筋 → 反転して明るい筋にし、画像全体の傾き(照明のむら)を平面で引き、
    # 0.15 より上を残して 216 px 未満の粒(穴・汚れ)を捨てる。開発用 6 枚で 3/3 検出・誤報 0/3。
    "crack": [{"op": "gaussian", "a": 0.5}, {"op": "invert"}, {"op": "hx_plane_deviation", "a": 0.5},
              {"op": "threshold", "a": 0.15}, {"op": "select_shape", "a": 1.0}],
    # 汚れは周りより暗い小さな斑 → 黒トップハット(9 px)で小さな暗点を浮かせ、0.35 より上を残す。
    # 芯の穴も同じ大きさの暗点なので、単画像の鎖では外せない(開発用 6 枚で 3/3 検出・誤報 2/3)。閾値 0.40 は
    # 検出 1/3・誤報 2/3、0.45 は検出 1/3・誤報 1/3 で、どちらも検出を落とすので 0.35 にした(検出を優先)。
    "candle": [{"op": "gaussian", "a": 0.1}, {"op": "bothat", "a": 0.9}, {"op": "threshold", "a": 0.35},
               {"op": "select_shape", "a": 0.0}],
}

#: Fullseye の既存レシピ(``recipes.py`` の外観検査)を、ひび割れ・ろうそく用に直さず**そのまま**当てる。
EXISTING = ("FA — scratch on hairline metal", "FA — dent and foreign fibre on resin")

#: 良品学習(既存の op、MCP からは呼べない)の設定。``poc_patch_anomaly`` で VisA に最も強かった記憶バンク 10 %。
LEARNED_N_FIT = 20
LEARNED_N_CAL = 10

#: 使うファイル一覧の指紋(:func:`file_manifest_sha256`)。2026-11-08 に手元の取得物で計算した値。
DATA_PINS = {"crack": "00b7ead6255bbeb059723bf35048da05c215328ed1f41e5fb7fb4af7e16f4e50", "candle": "eeb59cc5a45f93a9b1987a34a12b9e8594966509a1d361065fb18acab0285519"}

#: 取り直しの便。``expected`` = 課題・模型ごとの回数(門)。順序は表と図の並び。
PHASES = {
    "v1_openai_ctx4096": {"label": "第 1 便(文脈 4,096 で切れていた疑い)", "expected": 10, "current_prompts": False},
    "v2_ctx32k": {"label": "第 2 便(文脈 32k、MCP は直す前)", "expected": 10, "current_prompts": True},
    "v3_mcpfix": {"label": "第 3 便(文脈 32k、MCP を直した後)", "expected": 10, "current_prompts": True},
    "cloud_v2": {"label": "クラウド LLM(条件の差は表 06 の注、MCP は直す前)", "expected": 3, "current_prompts": True},
}

#: レシピの記録(:data:`RECIPES_JSON`)の指紋 = 中身を ``sort_keys`` で並べ直した JSON の SHA-256(改行の流儀に依らない)。
#: 記録を書き換えたら(取り直したら)ここを直す —— レシピと発言記録を一緒に書き換えて記録を作り直しても門を通る、
#: という抜け道を塞ぐ(2026-11-08、作者と独立の検証)。
RECIPES_SHA256 = "b6094e8ea897125a2ff31169c1597ad32e4696e137802caff3b268d4c177f629"

#: ローカルとクラウドで、そろっていない条件(表 06 の注・キャプションに出す)。
CONDITION_GAPS = (
    "ローカルだけに催促がある(試走せずに答えた時・JSON で答えなかった時に 1 回ずつ)",
    "クラウドの模型の製品名は書かない方針で、温度は土台が出さない。土台は汎用のコーディング エージェント",
    "クラウドの 6 本は CLI の応答を自前のコマンド(先頭だけ切る・JSON の解析・grep、1 本は保存して自前のスクリプト)で"
    "切り出して読んだ(依頼文違反)。ローカルは同じ長さに切った応答を全文そのまま読む",
    "ローカルの道具は呼び出しを発言の頭でしか数えず、最大 33 回まで走った。採点は 24 回目までで切ったレシピ",
)

#: 道具の呼び出しの上限(ローカル・クラウド共通)。採点はこの回数までの呼び出しで切ったレシピで行う。
CALL_CAP = 24

#: 見出しの数字(キャプション・CHANGELOG が引く量)。CI は記録と一致することを門にする。
HEADLINE: dict = {
    "crack/第 1 便 ローカル LLM 32B(コード向け)": "0/10",
    "crack/第 1 便 ローカル LLM 14B": "1/10",
    "crack/第 2 便 ローカル LLM 32B(コード向け)": "2/10",
    "crack/第 2 便 ローカル LLM 14B": "1/10",
    "crack/第 3 便 ローカル LLM 32B(コード向け)": "1/10",
    "crack/第 3 便 ローカル LLM 14B": "0/10",
    "crack/クラウド LLM": "3/3",
    "crack/hand": "0.98/0.08",
    "crack/learned:patchbank": "0.98/0.18",
    "crack/existing:FA — scratch on hairline metal": "0.69/0.01",
    "crack/第 1 便 ローカル LLM 32B(コード向け)/偏りの規則が無ければ": "1/10",
    "crack/第 1 便 ローカル LLM 14B/偏りの規則が無ければ": "1/10",
    "crack/第 2 便 ローカル LLM 32B(コード向け)/偏りの規則が無ければ": "3/10",
    "crack/第 2 便 ローカル LLM 14B/偏りの規則が無ければ": "2/10",
    "crack/第 3 便 ローカル LLM 32B(コード向け)/偏りの規則が無ければ": "1/10",
    "crack/第 3 便 ローカル LLM 14B/偏りの規則が無ければ": "4/10",
    "crack/クラウド LLM/偏りの規則が無ければ": "3/3",
    "crack/第 1 便 MCP の規則だけなら": "12/19",
    "crack/24 回で切った": "5",
    "crack/クラウド LLM の誤報": "0.32-0.52",
    "candle/第 1 便 ローカル LLM 32B(コード向け)": "0/10",
    "candle/第 1 便 ローカル LLM 14B": "0/10",
    "candle/第 2 便 ローカル LLM 32B(コード向け)": "0/10",
    "candle/第 2 便 ローカル LLM 14B": "0/10",
    "candle/第 3 便 ローカル LLM 32B(コード向け)": "0/10",
    "candle/第 3 便 ローカル LLM 14B": "0/10",
    "candle/クラウド LLM": "1/3",
    "candle/hand": "0.63/0.73",
    "candle/learned:patchbank": "0.53/0.13",
    "candle/existing:FA — scratch on hairline metal": "1.00/1.00",
    "candle/第 1 便 ローカル LLM 32B(コード向け)/偏りの規則が無ければ": "0/10",
    "candle/第 1 便 ローカル LLM 14B/偏りの規則が無ければ": "0/10",
    "candle/第 2 便 ローカル LLM 32B(コード向け)/偏りの規則が無ければ": "0/10",
    "candle/第 2 便 ローカル LLM 14B/偏りの規則が無ければ": "0/10",
    "candle/第 3 便 ローカル LLM 32B(コード向け)/偏りの規則が無ければ": "0/10",
    "candle/第 3 便 ローカル LLM 14B/偏りの規則が無ければ": "0/10",
    "candle/クラウド LLM/偏りの規則が無ければ": "1/3",
    "candle/第 1 便 MCP の規則だけなら": "11/20",
    "candle/24 回で切った": "5",
    "candle/クラウド LLM の誤報": "0.12-0.65",
}

ok_all: list[bool] = []
CAT = Catalog.load()


def model_label(name: str | None) -> str:
    """模型の名前を一般名にする(図・表・印字に製品名を出さない)。``14b`` → 「ローカル LLM 14B」。

    Generic label for a local model: its parameter count, and whether it is a code-tuned variant.
    The cloud agent column is recorded under the generic id ``cloud``.
    """
    if not name:
        return "-"
    if name == "cloud":
        return "クラウド LLM"
    m = re.search(r"(?<![\d.])(\d+(?:\.\d+)?)b\b", name.lower())
    size = ("%sB" % m.group(1)) if m else "?B"
    return "ローカル LLM %s%s" % (size, "(コード向け)" if "coder" in name.lower() else "")


def check(name: str, cond, detail: str = "") -> bool:
    """門 1 本。結果を印字して ``ok_all`` に積む / one gate: print and record."""
    ok = bool(cond)
    ok_all.append(ok)
    print("   [%s] %s%s" % ("OK" if ok else "NG", name, ("  (" + detail + ")") if detail else ""))
    return ok


# --------------------------------------------------------------------------- #
# データ / data                                                                 #
# --------------------------------------------------------------------------- #
def _gray(path: str, down: int = 1) -> np.ndarray:
    """8 bit の灰色(PIL の L)を [0, 1] にし、``down`` × ``down`` 平均で縮めて 8 bit に丸める。

    開発用 PNG(8 bit)と試験の配列を同じ量子化にそろえる —— AI が開発用で決めた閾値が、
    試験で量子化の差だけずれないように。
    """
    im = np.asarray(Image.open(path).convert("L"), dtype=np.float64) / 255.0
    if down > 1:
        h, w = im.shape
        h -= h % down
        w -= w % down
        im = im[:h, :w].reshape(h // down, down, w // down, down).mean(axis=(1, 3))
    return np.round(np.clip(im, 0.0, 1.0) * 255.0) / 255.0


def _mask(path: str | None, shape, down: int) -> np.ndarray:
    if not path:
        return np.zeros(shape, bool)
    m = np.asarray(Image.open(path).convert("L"), dtype=np.float64) > 0
    h, w = m.shape
    h -= h % down
    w -= w % down
    return m[:h, :w].reshape(h // down, down, w // down, down).mean(axis=(1, 3)) >= 0.25


def crack_split(root: str, n_test: int = 200, n_dev: int = 3, n_fit: int = LEARNED_N_FIT,
                n_cal: int = LEARNED_N_CAL) -> dict:
    """ひび割れの分け方(ファイル名順に等間隔で試験、残りの先頭から開発・学習・較正)。重なりは無い。"""
    out = {"test": [], "dev": [], "fit": [], "cal": []}
    for lab, sub in ((1, "Positive"), (0, "Negative")):
        names = sorted(n for n in os.listdir(os.path.join(root, sub)) if n.lower().endswith(".jpg"))
        step = len(names) // n_test
        test = names[step // 2::step][:n_test]
        rest = [n for n in names if n not in set(test)]
        out["test"] += [(os.path.join(sub, n), lab, None) for n in test]
        out["dev"] += [(os.path.join(sub, n), lab, None) for n in rest[:n_dev]]
        if lab == 0:                                    # 良品学習は良品だけを見る
            out["fit"] += [(os.path.join(sub, n), 0, None) for n in rest[n_dev:n_dev + n_fit]]
            out["cal"] += [(os.path.join(sub, n), 0, None) for n in rest[n_dev + n_fit:n_dev + n_fit + n_cal]]
    return out


def candle_split(root: str, n_dev: int = 3, n_fit: int = LEARNED_N_FIT, n_cal: int = LEARNED_N_CAL) -> dict:
    """VisA candle の分け方。試験の異常の先頭 3 枚を開発用へ回し、学習・較正・開発の良品は train から取る。

    手元の取得物は train の良品が一部だけなので、``split_csv`` の train のうち実在するものを順に使う。
    """
    with open(os.path.join(root, "split_csv", "1cls.csv"), encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r["object"] == "candle"]
    test = [r for r in rows if r["split"] == "test"]
    anom = [r for r in test if r["label"] == "anomaly"]
    train = [r for r in rows if r["split"] == "train" and os.path.isfile(os.path.join(root, r["image"]))]
    dev_anom = anom[:n_dev]
    test = [r for r in test if r not in dev_anom]
    f = lambda r: (r["image"], int(r["label"] == "anomaly"), r["mask"] or None)  # noqa: E731
    return {"test": [f(r) for r in test], "dev": [f(r) for r in dev_anom + train[n_fit + n_cal:n_fit + n_cal + n_dev]],
            "fit": [f(r) for r in train[:n_fit]], "cal": [f(r) for r in train[n_fit:n_fit + n_cal]]}


DOWN = {"crack": 1, "candle": 4}


def task_root(task: str) -> str:
    return CRACK if task == "crack" else VISA


def task_split(task: str) -> dict:
    return crack_split(CRACK) if task == "crack" else candle_split(VISA)


def file_manifest_sha256(root: str, split: dict) -> str:
    """使う全ファイル(画像とマスク)の「相対名 SHA-256」の行を並べた文字列の SHA-256。"""
    rels = sorted({p for part in split.values() for (p, _, m) in part for p in (p, m) if p})
    lines = []
    for rel in rels:
        with open(os.path.join(root, rel), "rb") as fh:
            lines.append("%s %s" % (rel.replace(os.sep, "/"), hashlib.sha256(fh.read()).hexdigest()))
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def load_part(task: str, part: list) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    root, down = task_root(task), DOWN[task]
    xs = [_gray(os.path.join(root, p), down) for p, _, _ in part]
    ys = np.array([lab for _, lab, _ in part], int)
    ms = np.stack([_mask(os.path.join(root, m) if m else None, x.shape, down) for x, (_, _, m) in zip(xs, part)])
    return np.stack(xs), ys, ms


def dev_names(task: str, part: list) -> list[str]:
    """開発用画像のファイル名(:data:`TASKS` の文と同じ名前)。"""
    out, k = [], {0: 0, 1: 0}
    for _, lab, _ in part:
        k[lab] += 1
        out.append("%s_dev_%s_%d.png" % (task, "defect" if lab else "good", k[lab]))
    return out


def write_dev_sandbox(dest: Path) -> list[Path]:
    """AI と手のレシピ作りに使う開発用 6 枚 × 課題を ``dest`` に 8 bit PNG で書く(``gen_ai_inspection_recipes`` が使う)。"""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    written = []
    for task in TASKS:
        if not task_root(task):
            raise SystemExit("%s のデータが無い: FULLSEYE_%s_DATA を設定する" % (task, "CRACK" if task == "crack" else "VISA"))
        sp = task_split(task)
        x, _, _ = load_part(task, sp["dev"])
        for im, name in zip(x, dev_names(task, sp["dev"])):
            Image.fromarray(np.round(im * 255).astype(np.uint8)).save(dest / name)
            written.append(dest / name)
    return written


# --------------------------------------------------------------------------- #
# レシピを走らせる / run a recipe                                              #
# --------------------------------------------------------------------------- #
def recipe_sha(stages) -> str:
    return hashlib.sha256(json.dumps(stages, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def existing_stages(name: str) -> list[dict]:
    """``recipes.py`` の ``(op, a, b)`` を MCP の段の形へ(値は変えない)。"""
    return [{"op": op, "a": a, "b": b} for op, a, b in fa_recipes.stages(name)]


def validate(stages) -> tuple[str, str]:
    """データ不要の検証: ``("ok" | "no_recipe" | "invalid", 理由)``。最後の段が region でなければ契約外。"""
    if not stages:
        return "no_recipe", "AI がレシピを返さなかった"
    try:
        r = validate_pipeline(stages, "image", CAT)
    except Exception as exc:                                   # noqa: BLE001  入力は AI の出力 = 信頼しない
        return "invalid", "%s: %s" % (type(exc).__name__, str(exc)[:120])
    if not r.get("valid"):
        e = (r.get("errors") or [{}])[0]
        return "invalid", "%s(段 %s %s)" % (e.get("reason"), e.get("stage"), e.get("value", ""))
    if r.get("out_sort") != "region":
        return "invalid", "最後の出力が %s(region でない)" % r.get("out_sort")
    return "ok", ""


def run_recipe(stages, images: np.ndarray) -> dict:
    """保存したレシピを MCP の ``fullseye_pipeline`` と同じ入口で 1 枚ずつ走らせる。

    返り値: ``masks``(bool、落ちた画像は全 False)、``errors``(画像ごとの例外文 or None)、``ms``(1 枚の壁時計)。
    """
    store = HandleStore(roots=[])
    masks, errors, ms = [], [], []
    for im in images:
        h = store.put(im, sort="image", provenance=[])["handle"]
        t0 = time.perf_counter()
        err, mask = None, np.zeros(im.shape, bool)
        try:
            r = call_tool("fullseye_pipeline", {"handle": h, "stages": stages, "vision": "none"}, CAT, store)
            sc = r.get("structuredContent") or {}
            if r.get("isError") or not sc.get("handle"):
                err = json.dumps(sc.get("error") or sc.get("errors") or sc, ensure_ascii=False)[:200]
            else:
                _meta, v = store.get(sc["handle"])
                a = np.asarray(v)
                if a.shape != im.shape:
                    err = "出力の形 %s が入力 %s と違う" % (a.shape, im.shape)
                else:
                    mask = a > 0.5
        except Exception as exc:                               # noqa: BLE001
            err = "%s: %s" % (type(exc).__name__, str(exc)[:160])
        ms.append((time.perf_counter() - t0) * 1000.0)
        masks.append(mask)
        errors.append(err)
    return {"masks": np.stack(masks), "errors": errors, "ms": ms}


# --------------------------------------------------------------------------- #
# 採点 / scoring                                                                #
# --------------------------------------------------------------------------- #
def score(masks: np.ndarray, errors: list, labels: np.ndarray, gt: np.ndarray | None) -> dict:
    """1 つのレシピの成績。落ちた画像は「不合格と判定した」として数える(検査は fail-closed)。

    * ``tpr`` 検出率 = 欠陥のある画像のうち NG と判定した割合、``fpr`` 誤報率 = 良品のうち NG の割合
    * ``auroc`` = 前景の面積を得点にした画像の AUROC(落ちた画像は最大の得点)
    * ``hit`` = 真値の欠陥領域(8 連結)のうち 1 画素でも前景が触れた割合、``pix_fpr`` = 良い画素の誤報率
    * ``degenerate`` = ほぼ全部 NG(95 % 以上、``"all"``)/ ほぼ全部 OK(5 % 以下、``"none"``)/ ``""``
    """
    labels = np.asarray(labels, int)
    err = np.array([e is not None for e in errors], bool)
    area = masks.reshape(len(masks), -1).sum(axis=1).astype(float)
    ng = (area > 0) | err
    area_s = np.where(err, area.max() + 1.0, area)
    pos, neg = labels == 1, labels == 0
    out = {"tpr": float(ng[pos].mean()), "fpr": float(ng[neg].mean()),
           "auroc": float(fs.ledger.anomaly_image_auroc(area_s, labels)["auroc"]),
           "n_err": int(err.sum()), "n": int(len(labels))}
    out["bal"] = 0.5 * (out["tpr"] + 1.0 - out["fpr"])
    # 平衡正解率の 95 % 区間の下限(2 群の割合の正規近似。偶然 0.5 を有意に超えるかの判定に使う)
    n1, n0 = max(1, int(pos.sum())), max(1, int(neg.sum()))
    var = 0.25 * (out["tpr"] * (1 - out["tpr"]) / n1 + out["fpr"] * (1 - out["fpr"]) / n0)
    out["bal_lo95"] = float(out["bal"] - 1.96 * var ** 0.5)
    out["degenerate"] = "all" if ng.mean() >= 0.95 else "none" if ng.mean() <= 0.05 else ""
    if gt is not None and gt.any():
        ov = fs.ledger.anomaly_region_overlap(masks, gt, min_overlap=0.5)
        out["hit"] = float(ov["hit_any"])
        out["pix_fpr"] = float(ov["fpr"])
    return out


def status_of(valid: str, sc: dict | None) -> str:
    """壊れ方の分類 / how a recipe fails."""
    if valid != "ok":
        return valid
    if sc["n_err"] >= 0.5 * sc["n"]:
        return "runtime_error"
    if sc["degenerate"] == "all":
        return "flags_everything"
    if sc["degenerate"] == "none":
        return "flags_nothing"
    if sc["bal_lo95"] <= 0.5:
        return "chance"
    return "ok"


STATUS_JA = {"ok": "選り分ける", "chance": "偶然を超えない", "no_recipe": "レシピ無し",
             "invalid": "型の鎖が切れている・契約外", "runtime_error": "実行時に落ちる",
             "flags_everything": "全部に反応", "flags_nothing": "何にも反応しない"}
BROKEN = ("no_recipe", "invalid", "runtime_error")
SKEWED = ("flags_everything", "flags_nothing")


def summarize(rows: list[dict]) -> dict:
    """AI の N 回の分布: 中央値・最良・最悪(選り分けたレシピの中で)と壊れた数。"""
    bal = [r["score"]["bal"] for r in rows if r["status"] == "ok"]
    return {"n": len(rows), "n_ok": len(bal), "n_chance": sum(r["status"] == "chance" for r in rows),
            "n_broken": sum(r["status"] in BROKEN for r in rows),
            "n_degenerate": sum(r["status"] in SKEWED for r in rows),
            "bal_median": statistics.median(bal) if bal else None,
            "bal_best": max(bal) if bal else None, "bal_worst": min(bal) if bal else None}


def self_test_scoring() -> None:
    """採点の関数を、答えの分かっている小さな入力で検算する(データ不要、CI でも走る)。"""
    print("\n0) 採点の検算(答えの分かっている入力)")
    lab = np.array([1, 1, 0, 0])
    m = np.zeros((4, 8, 8), bool)
    m[0, 2:4, 2:4] = True                 # 欠陥画像 0 は検出
    m[2, 0, 0] = True                     # 良品 2 に誤報
    gt = np.zeros_like(m)
    gt[0, 2:5, 2:5] = True
    gt[1, 6:8, 6:8] = True
    s = score(m, [None, None, None, None], lab, gt)
    check("検出率 = 1/2、誤報率 = 1/2", s["tpr"] == 0.5 and s["fpr"] == 0.5, "%.2f / %.2f" % (s["tpr"], s["fpr"]))
    check("欠陥領域に触れた割合 = 1/2(2 領域のうち 1)", s["hit"] == 0.5, "%.2f" % s["hit"])
    check("面積の AUROC = 0.625(4 面積 4, 0, 1, 0 の順位)", abs(s["auroc"] - 0.625) < 1e-12, "%.3f" % s["auroc"])
    s2 = score(np.zeros_like(m), [None, "boom", None, None], lab, gt)
    check("落ちた画像は NG と数える(検出率 1/2、誤報 0)", s2["tpr"] == 0.5 and s2["fpr"] == 0.0 and s2["n_err"] == 1)
    s3 = score(np.ones_like(m), [None] * 4, lab, gt)
    check("全部に反応 → degenerate=all、状態 flags_everything",
          s3["degenerate"] == "all" and status_of("ok", s3) == "flags_everything")
    # 偶然より悪い(平衡正解率 0.449)レシピは「選り分ける」に数えない
    lab2 = np.array([1] * 97 + [0] * 100)
    m2 = np.zeros((197, 2, 2), bool)
    m2[:61, 0, 0] = True                   # 検出 61/97 = 0.63
    m2[97:170, 0, 0] = True                # 誤報 73/100 = 0.73
    s4 = score(m2, [None] * 197, lab2, None)
    check("偶然より悪い列(平衡正解率 %.3f)は状態 chance(選り分けたに数えない)" % s4["bal"],
          status_of("ok", s4) == "chance" and s4["bal"] < 0.5)
    m3 = np.zeros((197, 2, 2), bool)
    m3[:95, 0, 0] = True
    m3[97:113, 0, 0] = True                # 検出 0.98・誤報 0.16
    check("はっきり選り分ける列は状態 ok", status_of("ok", score(m3, [None] * 197, lab2, None)) == "ok")
    check("型の鎖の検証: region で終わらない列は契約外",
          validate([{"op": "gaussian", "a": 0.5}])[0] == "invalid" and validate(HAND["crack"])[0] == "ok")
    check("型の鎖の検証: 知らない op は invalid、空はレシピ無し",
          validate([{"op": "no_such_op_zz"}])[0] == "invalid" and validate(None)[0] == "no_recipe")


# --------------------------------------------------------------------------- #
# 方法の一覧 / the competitors                                                 #
# --------------------------------------------------------------------------- #
def load_recipe_runs() -> dict:
    with open(RECIPES_JSON, encoding="utf-8") as fh:
        return json.load(fh)


def used_dev_images(task: str, calls: list) -> bool:
    """AI が開発用画像を 1 枚でも読めたか(読めずに同梱の見本や架空のパスで調整した回を分ける)。"""
    dev = {"%s_dev_%s_%d.png" % (task, k, i) for k in ("defect", "good") for i in (1, 2, 3)}
    return any(c.get("tool") == "fullseye_load_image" and not c.get("is_error") and c.get("path") in dev
               for c in calls)


def capped_recipe(run: dict) -> tuple[list | None, bool]:
    """``CALL_CAP`` 回目までの呼び出しで切ったときのレシピと、切ったかどうか。

    上限を超えた回は、24 回目の時点で止められていたはず(最後の答えは出ていない)ので、24 回目までに成功した
    最後の試走の段の列にする(無ければレシピ無し)。上限内の回は記録のレシピのまま。
    """
    calls = run.get("calls") or []
    if len(calls) <= CALL_CAP:
        return run.get("recipe"), False
    ok = [c for c in calls[:CALL_CAP] if c.get("tool") == "fullseye_pipeline" and not c.get("is_error") and c.get("stages")]
    return (ok[-1]["stages"] if ok else None), True


def methods_for(task: str, runs_json: dict) -> list[dict]:
    """採点する方法の一覧。AI は保存した全回(レシピ無しの回も)、便ごと。"""
    out = []
    for r in sorted(runs_json["runs"], key=lambda r: (list(PHASES).index(r["phase"]), r["model"], r["run"])):
        if r["task"] != task:
            continue
        stages, capped = capped_recipe(r)
        out.append({"key": "ai:%s:%s:%d" % (r["phase"], r["model"], r["run"]), "kind": "ai", "model": r["model"],
                    "phase": r["phase"], "run": r["run"], "stages": stages, "capped": capped,
                    "source": r.get("recipe_source") if not capped else ("capped_pipeline" if stages else "none"),
                    "stop": r.get("stop"), "final_text": r.get("final_text") or "",
                    "load_errors": sum(c.get("tool") == "fullseye_load_image" and c.get("is_error")
                                       for c in (r.get("calls") or [])),
                    "calls": r.get("n_tool_calls"), "elapsed_s": r.get("elapsed_s"),
                    "used_dev": used_dev_images(task, r.get("calls") or []),
                    "tried": sum(c.get("tool") == "fullseye_pipeline" and not c.get("is_error")
                                 for c in (r.get("calls") or []))})
    out.append({"key": "hand", "kind": "hand", "stages": HAND[task]})
    for name in EXISTING:
        out.append({"key": "existing:" + name, "kind": "existing", "stages": existing_stages(name)})
    return out


# --------------------------------------------------------------------------- #
# 失敗の帰属 / attributing a failure                                            #
# --------------------------------------------------------------------------- #
CAUSE_JA = {"tool": "道具(LLM を呼ぶ側)", "mcp": "Fullseye の MCP の不備", "model": "模型の弱さ"}


def attribute(m: dict, status: str, why: str, errors_text: str = "") -> str | None:
    """失敗した回を 3 つに分ける(規則は上から順に当てる。選り分けた回は ``None``)。

    * ``tool`` —— 第 1 便(文脈長を渡していなかった)、または LLM の要求が時間切れ・接続の失敗で止まった回。
    * ``mcp`` —— Fullseye の MCP 側に直せる原因がある回: 開発用画像を 1 枚も読めず、load_image を 2 回以上外した
      (作業場所のファイルを一覧に出さず、拒否に読める名前を添えなかった)/ 検証が通したのに実行が a/b の範囲外で
      落ちた / a/b を params に入れて「知らない引数」で断られた(直し方を返さなかった)。
    * ``model`` —— 残り(無い op 名・無い引数名の作成、同じ失敗の繰り返し、偏った出力、繰り返しの制限で止まった等)。

    この規則は第 3 便(MCP を直した後)にも同じに当てる —— 直したはずの原因が残っていれば ``mcp`` に数え直される。
    """
    if status == "ok":
        return None
    if m.get("phase") == "v1_openai_ctx4096":
        return "tool"
    if m.get("stop") == "llm_error" and "repeat limit" not in m.get("final_text", ""):
        return "tool"
    if not m.get("used_dev") and m.get("load_errors", 0) >= 2:
        return "mcp"
    if status == "runtime_error" and ("最大値" in errors_text or "最小値" in errors_text):
        return "mcp"
    if status == "invalid" and why.startswith("unknown_parameter") and set(
            x.strip(" '[]") for x in why.split("[", 1)[-1].split("]")[0].split(",")) <= {"a", "b"}:
        return "mcp"
    return "model"


# --------------------------------------------------------------------------- #
# 良品学習(既存の op、MCP の外)/ learned-from-good baseline                    #
# --------------------------------------------------------------------------- #
def learned_baseline(task: str, split: dict, x_test: np.ndarray, pin: str = "") -> dict:
    """``patchbank_fit``(良品 20 枚)で地図を作り、較正用の良品 10 枚の最大得点を閾値にして二値化する。

    ``FULLSEYE_AISCORE_CACHE`` があれば、データの指紋 ``pin`` を鍵に結果を置き・読む(決定的な計算なので
    結果は同じ。学習と採点の時間は最初の実行の値を残す)。
    """
    cpath = Path(CACHE) / ("learned_%s_%s.npz" % (task, pin[:16])) if (CACHE and pin) else None
    if cpath is not None and cpath.is_file():
        z = np.load(cpath)
        return {"masks": z["masks"], "errors": [None] * len(x_test), "ms": list(z["ms"]),
                "threshold": float(z["threshold"]), "fit_s": float(z["fit_s"]), "image_scores": z["image_scores"]}
    fit, _, _ = load_part(task, split["fit"])
    cal, _, _ = load_part(task, split["cal"])
    t0 = time.perf_counter()
    model = fs.ledger.patchbank_fit(fit, coreset=0.1)
    fit_s = time.perf_counter() - t0
    def maps(xs):
        out, ms = [], []
        for x in xs:
            t = time.perf_counter()
            out.append(fs.ledger.patchbank_score(x, model, smooth=4.0)["map"])
            ms.append((time.perf_counter() - t) * 1000.0)
        return np.stack(out), ms
    cal_maps, _ = maps(cal)
    thr = float(cal_maps.reshape(len(cal_maps), -1).max(axis=1).max())
    test_maps, ms = maps(x_test)
    out = {"masks": test_maps > thr, "errors": [None] * len(x_test), "ms": ms, "threshold": thr,
           "fit_s": fit_s, "image_scores": test_maps.reshape(len(test_maps), -1).max(axis=1)}
    if cpath is not None:
        cpath.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(cpath, masks=out["masks"], ms=np.asarray(ms), threshold=thr, fit_s=fit_s,
                            image_scores=out["image_scores"])
    return out


# --------------------------------------------------------------------------- #
# 図 / figures                                                                  #
# --------------------------------------------------------------------------- #
def _overlay(gray: np.ndarray, pred: np.ndarray, gt: np.ndarray | None) -> np.ndarray:
    """灰色の実写に、検出(強調色の塗り)と真値の欠陥(参照色の輪郭)を重ねる。画素は拡大しない。

    検出は表示のときだけ 2 画素太らせて塗る(1 画素の点の検出が縮小したタイルでも見えるように。判定と採点は太らせない)。
    """
    from scipy import ndimage as ndi  # noqa: PLC0415
    rgb = np.repeat(gray[..., None], 3, axis=2).astype(np.float64)
    em = np.array(fs.role_rgb8("emphasis"), float) / 255.0
    pred = ndi.binary_dilation(pred, iterations=2) if pred.any() else pred
    rgb[pred] = 0.35 * rgb[pred] + 0.65 * em
    if gt is not None and gt.any():
        edge = gt & ~ndi.binary_erosion(gt, iterations=1)
        rgb[ndi.binary_dilation(edge, iterations=1)] = np.array(fs.role_rgb8("reference"), float) / 255.0
    return np.clip(rgb, 0.0, 1.0)


def _pick_ai(rows: list[dict], phases: tuple, which: str = "best") -> dict | None:
    """指定の便で最後まで走った AI のレシピ(偏ったものも含む)のうち、平衡正解率の最良 / 中央の 1 本。"""
    ok = sorted((r for r in rows if r["kind"] == "ai" and r["phase"] in phases and r["score"] is not None
                 and r["status"] not in BROKEN),
                key=lambda r: (r["score"]["bal"], r["key"]))
    if not ok:
        return None
    return ok[-1] if which == "best" else ok[len(ok) // 2]


def _pick_images(task: str, y: np.ndarray, gt: np.ndarray) -> list[int]:
    """図に出す試験画像 3 枚: 欠陥 2(ろうそくは欠陥の面積が大きい順)と、最初の良品 1(どの列にも寄せない)。"""
    pos = np.flatnonzero(y == 1)
    if task == "candle":
        pos = pos[np.argsort(-gt[pos].reshape(len(pos), -1).sum(axis=1), kind="stable")]
    return [int(pos[0]), int(pos[1]), int(np.flatnonzero(y == 0)[0])]


def _verdict(pred: np.ndarray, label: int, gt: np.ndarray | None) -> tuple[str, bool]:
    """1 枚の判定の札。欠陥の画素マスクがあれば、欠陥に触れたかで正否を決める(画像単位の NG だけでは ○ にしない)。"""
    ng = bool(pred.any())
    if not label:
        return ("NG" if ng else "OK"), (not ng)
    if gt is not None and gt.any():
        hit = bool((pred & gt).any())
        return ("欠陥に触れた" if hit else ("NG・欠陥の外" if ng else "OK")), hit
    return ("NG" if ng else "OK"), ng


def write_figures(result: dict) -> None:
    """図: 課題ごとの実写の重ね描き、検出率と誤報率の散布、まとめの表、失敗の帰属の表。"""
    if not figs.enabled():
        return
    mark = fs.ROLE_MARKERS
    for task in TASKS:
        t = result[task]
        x, y, gt, rows = t["_x"], t["_y"], t["_gt"], t["rows"]
        stages = {m["key"]: m["stages"] for m in t["_methods"]}
        idx = _pick_images(task, y, gt)
        cols = [("開発側の手組み", next(r for r in rows if r["key"] == "hand")),
                ("ローカル LLM 最良(直した後)", _pick_ai(rows, ("v3_mcpfix",))),
                ("クラウド LLM 最良", _pick_ai(rows, ("cloud_v2",))),
                ("良品学習(既存)", next(r for r in rows if r["kind"] == "learned"))]
        panels, caps = [], []
        for i in idx:
            g = gt[i] if task == "candle" else None
            panels.append(_overlay(x[i], np.zeros_like(x[i], bool), g))
            caps.append("入力(%s)" % ("欠陥あり" if y[i] else "良品"))
            for name, r in cols:
                if r is None:
                    panels.append(np.repeat(x[i][..., None], 3, axis=2))
                    caps.append("%s: 該当なし" % name)
                    continue
                if r["kind"] == "learned":
                    pred = t["_learned"]["masks"][i]
                else:
                    pred = run_recipe(stages[r["key"]], x[i:i + 1])["masks"][0]
                word, right = _verdict(pred, int(y[i]), g)
                panels.append(_overlay(x[i], pred, g))
                caps.append("%s: %s %s" % (name, word, mark["right" if right else "wrong"]))
        title = "%s(試験画像、塗り = 検出%s)" % (TASKS[task]["title"], "、輪郭 = 真値の欠陥" if task == "candle" else "")
        rule = ("欠陥の画像は欠陥の輪郭に触れたら ○" if task == "candle" else "欠陥の画像は NG なら ○")
        figs.save_grid("%s_real" % task, panels, captions=caps, ncols=1 + len(cols), title=title,
                       caption=("%s。%s、良品は OK なら ○。LLM の列は最後まで走ったレシピのうち平衡正解率が最良の 1 本。"
                                "良品の段は試験の最初の良品(どの列にも寄せていない)。検出は表示のため 2 画素太らせた。"
                                "出典表示: %s" % (title, rule, CRACK_SOURCE if task == "crack" else VISA_SOURCE)))
    for task in TASKS:
        rows = result[task]["rows"]
        series, kinds, colors = [("偶然の線", [0, 1], [0, 1])], ["line"], ["neutral"]
        ex = [r for r in rows if r["kind"] == "existing" and r["score"] is not None]
        series.append(("既存レシピ(外観 2 本)", [r["score"]["fpr"] for r in ex], [r["score"]["tpr"] for r in ex]))
        kinds.append("scatter")
        colors.append("neutral")
        for key, label, role in (("learned:patchbank", "良品学習(既存)", "reference"), ("hand", "開発側の手組み", "baseline")):
            r = next(r for r in rows if r["key"] == key)
            series.append((label, [r["score"]["fpr"]], [r["score"]["tpr"]]))
            kinds.append("scatter")
            colors.append(role)
        missing = []
        for ph, role in (("v2_ctx32k", "wrong"), ("v3_mcpfix", "emphasis"), ("cloud_v2", "right")):
            mine = [r for r in rows if r["kind"] == "ai" and r["phase"] == ph]
            pts = [r for r in mine if r["score"] is not None and r["status"] not in BROKEN]
            if pts:
                series.append(("%s(%d 回中 %d 本が走った)" % (PHASES[ph]["label"], len(mine), len(pts)),
                               [r["score"]["fpr"] for r in pts], [r["score"]["tpr"] for r in pts]))
                kinds.append("scatter")
                colors.append(role)
            elif mine:
                missing.append(PHASES[ph]["label"])
        figs.save_plot("%s_scores" % task, series, xlabel="誤報率(良品を NG にした割合)",
                       ylabel="検出率(欠陥を NG にした割合)",
                       title="%s: 試験 %d 枚%s" % (TASKS[task]["title"], result[task]["n_test"],
                                                  "(%s は走ったレシピが無い)" % "・".join(missing) if missing else ""),
                       kinds=kinds, colors=colors, styles=["dotted"] + [None] * (len(series) - 1),
                       xlim=(-0.02, 1.02), ylim=(-0.02, 1.02), size=(680, 440),
                       caption=("左上ほど良い。対角の点線は偶然。LLM の点は 1 回ごとのレシピで、後から描いた列が上に重なる。"
                                "実行時に落ちたレシピと型の鎖が切れたレシピは点にしない。第 1 便は道具の不備で比べられないので省いた。"))
    header = ["課題", "組み手", "回数", "選り分けた", "偶然以下", "壊れた", "偏った",
              "検出率(中央)", "誤報率(中央)", "面積の AUROC(中央)", "段数(中央)"]
    body = []
    for task in TASKS:
        rows = result[task]["rows"]
        for name, rs in _groups(rows):
            sc = [r["score"] for r in rs if r["score"] is not None and r["status"] == "ok"]

            def med(k, sc=sc):
                return "%.2f" % statistics.median(s[k] for s in sc) if sc else "-"
            st = [r["n_stages"] for r in rs if r["n_stages"]]
            sm = summarize(rs)
            body.append([TASKS[task]["title"], name, str(len(rs)), str(sm["n_ok"]), str(sm["n_chance"]),
                         str(sm["n_broken"]), str(sm["n_degenerate"]),
                         med("tpr"), med("fpr"), med("auroc"), str(statistics.median(st)) if st else "-"])
    figs.save_table("summary", header, body, title="AI が組んだ検査の成績(公開実データ、真値は配布元)",
                    caption=("選り分けた = 平衡正解率の 95 % 区間の下限が 0.5 を超える。偶然以下 = 偏ってはいないが偶然を超えない。"
                             "壊れた = レシピ無し・型の鎖が切れている・実行時に落ちる。偏った = 95 % 以上 NG か 95 % 以上 OK。"
                             "検出率などの中央値は選り分けたレシピだけから。ひび割れでは既存レシピ(金属のヘアラインの傷用を直さず)の"
                             "1 本が誤報 0.01 で、クラウド LLM の最良より平衡正解率が高い。"))
    header = ["課題", "便・組み手", "回数", "選り分けた", "偏りの規則が無ければ", "開発用画像を読んだ", "24 回で切った",
              "失敗: 道具", "失敗: MCP", "失敗: 模型", "MCP の規則だけなら"]
    body = []
    for task in TASKS:
        for name, rs in _groups(result[task]["rows"], ai_only=True):
            body.append([TASKS[task]["title"], name, str(len(rs)), str(sum(r["status"] == "ok" for r in rs)),
                         str(sum(r["status"] == "ok" or bool(r.get("sorts_without_skew_rule")) for r in rs)),
                         str(sum(bool(r.get("used_dev")) for r in rs)), str(sum(bool(r.get("capped")) for r in rs))]
                        + [str(sum(r.get("cause") == c for r in rs)) for c in ("tool", "mcp", "model")]
                        + [str(sum(bool(r.get("cause_mcp_rule_only")) for r in rs))])
    figs.save_table("attribution", header, body, title="失敗の帰属と、道具・MCP を直す前後",
                    caption=("第 1 便 = 道具が文脈長を渡していなかった(古い発言が捨てられた疑い)。第 2 便 = 文脈長を直した。"
                             "第 3 便 = MCP の不備も直した。帰属は attribute() の規則を上から順に当てる: 第 1 便は失敗を全部「道具」に"
                             "寄せたので「失敗: MCP」は全便 0 になる。MCP の規則だけを当てた数を右端に出した(第 1 便で多い)。"
                             "第 2 便以降は文脈が直り開発用画像を読めたので、MCP の不備が成否を分けなくなった。"
                             "「選り分けた」は偏り(95 % 以上を NG)を除く規則に依る —— 規則が無ければの数を隣に出した。"
                             "そろっていない条件: " + " / ".join(CONDITION_GAPS)))


def _groups(rows: list[dict], ai_only: bool = False) -> list[tuple[str, list[dict]]]:
    """表の行の並び: 便 × 模型、(ai_only でなければ)手組み・既存レシピ・良品学習。"""
    out = []
    for ph in PHASES:
        for m in sorted({r["model"] for r in rows if r["kind"] == "ai" and r["phase"] == ph}):
            out.append(("%s %s" % (PHASES[ph]["label"].split("(")[0] if ph != "cloud_v2" else "", model_label(m)),
                        [r for r in rows if r["kind"] == "ai" and r["phase"] == ph and r["model"] == m]))
    out = [(n.strip(), rs) for n, rs in out]
    if not ai_only:
        out += [("開発側の手組み", [r for r in rows if r["kind"] == "hand"]),
                ("既存レシピ 2 本", [r for r in rows if r["kind"] == "existing"]),
                ("良品学習(既存)", [r for r in rows if r["kind"] == "learned"])]
    return out


# --------------------------------------------------------------------------- #
# 本体 / main                                                                   #
# --------------------------------------------------------------------------- #
def recipes_fingerprint(runs_json: dict) -> str:
    """レシピの記録の指紋(``sort_keys`` で並べ直した JSON の SHA-256。改行の流儀に依らない)。"""
    return hashlib.sha256(json.dumps(runs_json, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def current_prompt_shas() -> dict:
    """今の課題文の SHA-256(指示文は記録の prompts 表にあるかで確かめる)。"""
    return {t: hashlib.sha256(TASKS[t]["request"].encode("utf-8")).hexdigest() for t in TASKS}


def ci_checks(runs_json: dict, recorded: dict) -> None:
    """データが無くても走る門: 記録の指紋・回数・取り直しの条件、レシピの検証、記録とレシピの対応、見出しの数字。"""
    print("\n1) 保存したレシピ(データ不要の検証)")
    fp = recipes_fingerprint(runs_json)
    check("レシピの記録の指紋が固定値と一致", fp == RECIPES_SHA256, fp[:16])
    runs = runs_json["runs"]
    check("記録の便は既知のものだけ", {r["phase"] for r in runs} <= set(PHASES), ", ".join(sorted({r["phase"] for r in runs})))
    req = current_prompt_shas()
    for task in TASKS:
        for ph, spec in PHASES.items():
            mine = [r for r in runs if r["task"] == task and r["phase"] == ph]
            models = sorted({r["model"] for r in mine})
            check("%s / %s: 模型ごとにちょうど %d 回(%s)" % (task, ph, spec["expected"], ", ".join(map(model_label, models))),
                  bool(mine) and all(sorted(r["run"] for r in mine if r["model"] == m) ==
                                     list(range(1, spec["expected"] + 1)) for m in models),
                  "%d 回" % len(mine))
            if spec["current_prompts"]:
                check("%s / %s: 今の課題文で作った(SHA-256)" % (task, ph),
                      all(r.get("request_sha256") == req[task] for r in mine))
                sys_shas = {r.get("system_prompt_sha256") for r in mine}
                check("%s / %s: 指示文は 1 種類で、記録の prompts 表にある" % (task, ph),
                      len(sys_shas) == 1 and next(iter(sys_shas)) in (runs_json.get("prompts") or {}))
            if ph != "v1_openai_ctx4096" and ph != "cloud_v2":
                check("%s / %s: 文脈長を記録し、切り詰めの印(prompt が num_ctx の 9 割)が 1 本も無い" % (task, ph),
                      all(r.get("num_ctx") and r.get("truncation_suspect") is False and r.get("model_digest")
                          for r in mine),
                      "最大 prompt %d" % max((max(r.get("prompt_tokens_per_turn") or [0]) for r in mine), default=0))
        cloud = [r for r in runs if r["task"] == task and r["phase"] == "cloud_v2"]
        check("%s / cloud_v2: 条件を記録し、発言記録から導ける項目(上限・催促なし・並列の開始・依頼文)が記録と一致" % task,
              bool(cloud) and all(cloud_conditions_match(r, cloud, runs_json) for r in cloud))
        over = [r for r in runs if r["task"] == task and len(r.get("calls") or []) > CALL_CAP]
        check("%s: 上限 %d 回を超えた %d 本は 24 回目までで切ったレシピで採点する" % (task, CALL_CAP, len(over)),
              all(capped_recipe(r)[1] for r in over))
        ms = methods_for(task, runs_json)
        rec = {r["key"]: r for r in recorded.get(task, {}).get("rows", [])}
        bad_link, bad_valid = [], []
        for m in ms:
            v, _why = validate(m["stages"])
            r = rec.get(m["key"])
            if r is None or r["recipe_sha256"] != (recipe_sha(m["stages"]) if m["stages"] else None):
                bad_link.append(m["key"])
            elif (v == "ok") != (r["status"] not in ("no_recipe", "invalid")):
                bad_valid.append(m["key"])
        check("%s: 記録の行がいまのレシピ(SHA-256)と 1 対 1" % task,
              not bad_link and len(rec) == len(ms) + 1, "外れ %s" % bad_link[:3])
        check("%s: データ不要の検証(型の鎖・契約)が記録の状態と一致" % task, not bad_valid, "外れ %s" % bad_valid[:3])
    got = headline(recorded)
    check("見出しの数字(HEADLINE)が記録と一致", got == HEADLINE,
          "記録 %s" % json.dumps(got, ensure_ascii=False)[:300] if got != HEADLINE else "%d 項目" % len(got))


def cloud_conditions_match(r: dict, group: list, runs_json: dict) -> bool:
    """クラウドの 1 回の ``conditions`` を、その回の発言記録から導ける事実と照合する(定数があるかだけを見ない)。"""
    c = r.get("conditions")
    if not isinstance(c, dict):
        return False
    import datetime as _dt
    starts = sorted(_dt.datetime.fromisoformat(x["started"]) for x in group if x.get("started"))
    parallel = len(starts) == len(group) and (starts[-1] - starts[0]).total_seconds() < 120
    cap = int(str(c.get("call_cap", "")).split(",")[0])
    return (cap == CALL_CAP and len(r.get("calls") or []) <= cap
            and str(c.get("nudges", "")).startswith("none") and not r.get("nudges")
            and bool(c.get("started_in_parallel")) == parallel
            and c.get("brief_sha256") in (runs_json.get("prompts") or {})
            and "product name" in str(c.get("model", "")))


def headline(rec: dict) -> dict:
    """キャプション・CHANGELOG が引く数字を記録から作る(:data:`HEADLINE` と比べる)。"""
    out = {}
    for task in TASKS:
        rows = (rec.get(task) or {}).get("rows") or []
        if not rows:
            continue
        for name, rs in _groups(rows, ai_only=True):
            out["%s/%s" % (task, name)] = "%d/%d" % (sum(r["status"] == "ok" for r in rs), len(rs))
        for key in ("hand", "learned:patchbank", "existing:FA — scratch on hairline metal"):
            s = next(r for r in rows if r["key"] == key)["score"]
            out["%s/%s" % (task, key)] = "%.2f/%.2f" % (s["tpr"], s["fpr"])
        ai = [r for r in rows if r["kind"] == "ai"]
        for name, rs in _groups(rows, ai_only=True):
            out["%s/%s/偏りの規則が無ければ" % (task, name)] = "%d/%d" % (
                sum(r["status"] == "ok" or bool(r.get("sorts_without_skew_rule")) for r in rs), len(rs))
        v1 = [r for r in ai if r["phase"] == "v1_openai_ctx4096"]
        out["%s/第 1 便 MCP の規則だけなら" % task] = "%d/%d" % (
            sum(bool(r.get("cause_mcp_rule_only")) for r in v1), sum(r["status"] != "ok" for r in v1))
        out["%s/24 回で切った" % task] = str(sum(bool(r.get("capped")) for r in ai))
        cl = [r["score"]["fpr"] for r in ai if r["phase"] == "cloud_v2" and r["score"] is not None]
        if cl:
            out["%s/クラウド LLM の誤報" % task] = "%.2f-%.2f" % (min(cl), max(cl))
    return out


def full_run(runs_json: dict, recorded: dict) -> dict:
    """実データで全部を採点する。記録と比べる(処理時間を除く)。"""
    result = {}
    for task in TASKS:
        print("\n2) %s(%s)" % (TASKS[task]["title"], task))
        sp = task_split(task)
        pin = file_manifest_sha256(task_root(task), sp)
        if not check("%s: 使うファイル %d 個の指紋が固定値と一致" % (task, sum(len(v) for v in sp.values())),
                     pin == DATA_PINS[task], pin[:16]):
            raise SystemExit("データが固定値と違う(%s)。取得物を確かめる。" % task)
        realdata.mark_read("visa" if task == "candle" else "ozgenel-concrete-crack")
        x, y, gt = load_part(task, sp["test"])
        gt_or_none = gt if task == "candle" else None
        print("   試験 %d 枚(欠陥 %d・良品 %d)%s" % (len(y), int(y.sum()), int((y == 0).sum()),
                                               "、画素マスクあり" if gt_or_none is not None else ""))
        rows = []
        for m in methods_for(task, runs_json):
            v, why = validate(m["stages"])
            sc, ms, errs = None, [], ""
            if v == "ok":
                rr = run_recipe(m["stages"], x)
                sc = score(rr["masks"], rr["errors"], y, gt_or_none)
                ms = rr["ms"]
                errs = " ".join(e for e in rr["errors"][:5] if e)
            st = status_of(v, sc)
            row = {"key": m["key"], "kind": m["kind"], "model": m.get("model"), "phase": m.get("phase"),
                   "run": m.get("run"), "recipe_sha256": recipe_sha(m["stages"]) if m["stages"] else None,
                   "n_stages": len(m["stages"]) if m["stages"] else 0,
                   "ops": [s.get("op") for s in (m["stages"] or [])], "status": st, "why": why,
                   "score": sc, "ms_median": round(statistics.median(ms), 2) if ms else None,
                   "recipe_source": m.get("source"), "n_tool_calls": m.get("calls"),
                   "used_dev": m.get("used_dev"), "tried": m.get("tried"), "capped": m.get("capped", False),
                   "cause": attribute(m, st, why, errs) if m["kind"] == "ai" else None,
                   "cause_mcp_rule_only": (attribute(dict(m, phase="", stop=""), st, why, errs) == "mcp")
                   if m["kind"] == "ai" and st != "ok" else False,
                   "sorts_without_skew_rule": bool(sc is not None and st in SKEWED and sc["bal_lo95"] > 0.5)}
            rows.append(row)
        lb = learned_baseline(task, sp, x, pin)
        lsc = score(lb["masks"], lb["errors"], y, gt_or_none)
        lsc["auroc_map"] = float(fs.ledger.anomaly_image_auroc(lb["image_scores"], y)["auroc"])
        rows.append({"key": "learned:patchbank", "kind": "learned", "model": None, "phase": None, "run": None,
                     "recipe_sha256": None, "n_stages": None, "ops": ["patchbank_fit", "patchbank_score"],
                     "status": status_of("ok", lsc), "why": "", "score": lsc,
                     "ms_median": round(statistics.median(lb["ms"]), 2),
                     "fit_s": round(lb["fit_s"], 1), "threshold": lb["threshold"], "cause": None})
        result[task] = {"rows": rows, "n_test": int(len(y)), "n_defect": int(y.sum()), "data_pin": pin,
                        "_x": x, "_y": y, "_gt": gt, "_methods": methods_for(task, runs_json), "_learned": lb}
        print_table(task, rows)
        rec = {r["key"]: r for r in recorded.get(task, {}).get("rows", [])}
        if not RECORD:
            diffs = [r["key"] for r in rows if r["key"] not in rec
                     or json.dumps(_stable(r), sort_keys=True) != json.dumps(_stable(rec[r["key"]]), sort_keys=True)]
            check("%s: 採点し直した結果が記録と一致(処理時間を除く、%d 行)" % (task, len(rows)), not diffs,
                  "外れ %s" % diffs[:3])
    return result


def _stable(row: dict) -> dict:
    """記録と比べる部分(処理時間・学習時間を除き、数値は 1e-9 に丸める)。"""
    def r9(v):
        if isinstance(v, float):
            return round(v, 9)
        if isinstance(v, dict):
            return {k: r9(w) for k, w in v.items()}
        return v
    return {k: r9(v) for k, v in row.items() if k not in ("ms_median", "fit_s")}


def display_name(r: dict) -> str:
    """印字・図に出す名前(模型は一般名)。"""
    if r["kind"] == "ai":
        ph = PHASES[r["phase"]]["label"].split("(")[0]
        return "%s %s 第 %d 回" % (ph if r["phase"] != "cloud_v2" else "", model_label(r["model"]), r["run"])
    if r["kind"] == "hand":
        return "開発側の手組み"
    if r["kind"] == "learned":
        return "良品学習(既存)"
    return "既存 " + r["key"].split(":", 1)[1].split("—")[-1].strip()


def fmt_row(r: dict) -> str:
    s = r["score"]
    if s is None or r["status"] in BROKEN:
        return "%-36s %-22s %s" % (display_name(r).strip()[:36], STATUS_JA[r["status"]], r["why"][:60])
    extra = ("  触れた %.2f 画素誤報 %.4f" % (s["hit"], s["pix_fpr"])) if "hit" in s else ""
    return "%-36s %-14s 検出 %.2f 誤報 %.2f 面積AUROC %.3f%s  %s段 %s ms" % (
        display_name(r).strip()[:36], STATUS_JA[r["status"]], s["tpr"], s["fpr"], s["auroc"], extra,
        r["n_stages"] if r["n_stages"] is not None else "-", r["ms_median"])


def print_table(task: str, rows: list[dict]) -> None:
    for r in rows:
        print("   " + fmt_row(r))
    for name, rs in _groups(rows, ai_only=True):
        sm = summarize(rs)
        print("   %s: %d 回、選り分けた %d、偶然以下 %d、壊れた %d、偏った %d、平衡正解率 中央 %s 最良 %s" % (
            name, sm["n"], sm["n_ok"], sm["n_chance"], sm["n_broken"], sm["n_degenerate"],
            *("%.3f" % v if v is not None else "-" for v in (sm["bal_median"], sm["bal_best"]))))


def print_recorded(recorded: dict) -> None:
    print("\n2) 記録した採点(%s、実データありの手元実行)" % recorded.get("generated", "?"))
    for task in TASKS:
        t = recorded.get(task)
        if not t:
            continue
        print("   ── %s: 試験 %d 枚(欠陥 %d)" % (TASKS[task]["title"], t["n_test"], t["n_defect"]))
        print_table(task, t["rows"])


def findings(result_or_recorded: dict) -> None:
    """失敗の帰属と、道具・MCP を直す前後 / failure attribution, before and after the fixes."""
    from collections import Counter
    print("\n3) 失敗の帰属(道具 / MCP の不備 / 模型)と、直す前後")
    for task in TASKS:
        t = result_or_recorded.get(task)
        if not t:
            continue
        rows = t["rows"]
        hand = next(r for r in rows if r["key"] == "hand")
        print("   ── %s(開発側の手組みの平衡正解率 %.3f)" % (TASKS[task]["title"], hand["score"]["bal"]))
        for name, rs in _groups(rows, ai_only=True):
            c = Counter(r.get("cause") for r in rs if r.get("cause"))
            print("     %-34s 選り分けた %d / %d、開発用画像を読んだ %d、失敗の帰属 %s" % (
                name, sum(r["status"] == "ok" for r in rs), len(rs), sum(bool(r.get("used_dev")) for r in rs),
                ", ".join("%s %d" % (CAUSE_JA[k], v) for k, v in sorted(c.items())) or "なし"))
        ai = [r for r in rows if r["kind"] == "ai" and r["phase"] in ("v2_ctx32k", "v3_mcpfix")]
        opc = Counter(op for r in ai for op in set(r["ops"]))
        print("     第 2・3 便で AI が使った op(回数): %s" % ", ".join("%s %d" % kv for kv in opc.most_common(8)))


def write_record(result: dict) -> None:
    payload = {"_note": ("Scores of every saved recipe on public real data (examples/poc_ai_built_inspection_scored.py). "
                         "Written with FULLSEYE_AISCORE_RECORD=1; CI checks that rows match the saved recipes."),
               "generated": time.strftime("%Y-%m-%d")}
    for task, t in result.items():
        payload[task] = {k: v for k, v in t.items() if not k.startswith("_")}
    SCORES_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("   記録を書いた: %s" % SCORES_JSON.name)
    print("   見出しの数字(HEADLINE に写す): %s" % json.dumps(headline(payload), ensure_ascii=False))


def main() -> int:
    print("AI が組んだ検査を公開実データの真値で採点する")
    self_test_scoring()
    runs_json = load_recipe_runs()
    recorded = json.loads(SCORES_JSON.read_text(encoding="utf-8")) if SCORES_JSON.exists() else {}
    have_data = bool(CRACK and VISA and os.path.isdir(os.path.join(CRACK, "Positive"))
                     and os.path.isfile(os.path.join(VISA, "split_csv", "1cls.csv")))
    if not RECORD:
        ci_checks(runs_json, recorded)
    if have_data:
        result = full_run(runs_json, recorded)
        if RECORD:
            write_record(result)
        findings(result)
        write_figures(result)
    else:
        print("\n   FULLSEYE_CRACK_DATA / FULLSEYE_VISA_DATA が無いので、実データの採点は走らせない(記録を印字する)。")
        print_recorded(recorded)
        findings(recorded)
    errors = figs.errors()
    check("図の書き出しに失敗が無い", not errors, "; ".join(errors[:2]))
    if all(ok_all):
        print("\nPASS(門 %d 本)" % len(ok_all))
        return 0
    print("\nFAIL(%d / %d 本が NG)" % (sum(not o for o in ok_all), len(ok_all)))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
