#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""トップページ(``README.md`` と ``docs/README*.md``)に「どう確かめているか」の節を差し込む。

    py -3.11 tools/gen_trust_block.py                  # 書く
    py -3.11 tools/gen_trust_block.py --check          # 生成物と食い違い・データの古びがあれば exit 1
    py -3.11 tools/gen_trust_block.py --release-check  # 上に加え、現行の行と索引の厳密一致(リリース直前)

## なぜ要るか(2026-10-11)

トップに書く「テスト N 件」「op N 本」は、書いた日から古びる。概観記事には
「テスト 10,982 件」が残り続け、実際は 18,000 件を超えていた。**数を手で書く限り、
いつか必ず嘘になる。**

だから数は全部、コミット済みの**測定データ**に置き、この生成器が描き、
``tests/test_trust_block.py`` が「描いたものと食い違う」「データが今の版のものでない」
のどちらでも落ちる。

入力(どれも repo の中):

* ``docs/test_count.json``      —— 回帰テストの件数(版・commit・日付・測り方つき)
* ``docs/gate_inventory.json``  —— op を 1 本足したときに掛かる門の実測(mutation probe)
* ``docs/maturity.json``        —— 能力ごとの検証の段(``tools/gen_maturity.py`` の生成物。読むだけ)
* ``docs/op_count_history.json`` —— 版ごとの op 数(過去の行は記録として固定)
* ``docs/OP_INDEX.json``        —— 現行の索引(現行の行の照合にだけ使う)

★テスト件数は**ここでは数えない**。収集は 40 秒かかり、optional backend の有無で
件数が変わる —— ``regen_all --check`` に入れると環境で赤になる。版ごとに測って
``docs/test_count.json`` に記録し、門は「記録の版 = pyproject の版」を見る
(版を上げたら測り直すまで落ちる)。

``<!-- trust-block:start -->`` と ``<!-- trust-block:end -->`` の外は手書きのまま残す。
加えて全版の表 ``docs/OP_COUNT_HISTORY.md`` を書く。
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

START, END = "<!-- trust-block:start -->", "<!-- trust-block:end -->"
HISTORY_PAGE = "docs/OP_COUNT_HISTORY.md"

#: (書き込み先, 言語, 差し込みの目印(マーカーが無い初回だけ使う), リンクの前置き)
#: repo の README.md は英語。docs/README*.md は索引(GitHub Pages のトップ)。
TARGETS = [
    ("README.md", "en", "## Three ways in", "docs/"),
    ("docs/README.md", "ja", "<!-- poc-index:start -->", ""),
    ("docs/README.en.md", "en", "<!-- poc-index:start -->", ""),
    ("docs/README.zh.md", "zh", "<!-- poc-index:start -->", ""),
    ("docs/README.tw.md", "tw", "<!-- poc-index:start -->", ""),
    ("docs/README.ko.md", "ko", "<!-- poc-index:start -->", ""),
    ("docs/README.de.md", "de", "<!-- poc-index:start -->", ""),
]

CHECKS = ("raises", "nan", "wrong_type", "nondeterministic", "ignores_params",
          "no_description", "english_only_description", "accepts_empty_input")
STAGES = ("research-prototype", "verified-synthetic", "validated-public-real-data",
          "validated-hardware")

#: 言語ごとの文言。**数はここに書かない**(全部データから差し込む)。
L10N = {
    "ja": dict(
        title="どう確かめているか",
        intro=("ここの数字は手で書いていません。`docs/` の測定データ({files})から "
               "`tools/gen_trust_block.py` が描き、食い違えば `tests/test_trust_block.py` が落ちます。"
               "どの数にも、測った版と日付を添えています。"),
        tests=("**回帰テスト {n} 件** — {rel}、commit `{commit}`、{date} に `pytest --collect-only` で"
               "数えた値(optional backend をすべて入れた環境。入れていない環境では、その backend を"
               "使う試験が収集されず件数は減ります)。"),
        after="{v} の後のツリー(未リリース分を含む)", inrel="{v} に含まれる",
        gates_h="### op を 1 本足すと、どんな門が確かめるか",
        gates_intro=("層ごとに、わざと壊した op を 1 本だけ足して全試験を走らせ、落ちた試験を"
                     "数えました(mutation probe)。✓ = その壊れ方で落ちる門がある、✗ = **まだ無い**。"),
        meas="測定 {mark}: commit `{commit}`、{date}、{rel}。",
        cols=("層", "測定", "手続きの門", "振る舞いの門", "例外", "NaN", "型違い", "非決定",
              "引数を無視", "説明なし", "説明が英語だけ", "空入力を受理"),
        gates_notes=("手続きの門 = 正しく書いた op でも、ノートや索引を作り直すまで落ちる門の数。"
                     "振る舞いの門 = それとは別に、壊れ方を見て落ちる門の種類数。"),
        not_covered=("測っていないこと: もっともらしい間違った値(真値との差)、速度、OS 固有の落ち方、"
                     "2 つ以上の壊れ方の組み合わせ。✓ は「少なくとも 1 本落ちた」の意味で、落ちた理由が"
                     "読めることまでは保証しません。"),
        tiers={"t1": "2-D 中核(`ops.REGISTRY`)", "t2": "n 入力", "t3": "色",
               "t4": "型付き台帳 + `tb_` 橋", "t5": "型付き台帳(橋なし)", "t5b": "3-D 台帳",
               "t6": "facade のみ"},
        mat_h="### 検証の段",
        mat_intro=("能力 {n} 件を、何で確かめたかで分けた数(`docs/maturity.json`。いまのツリー(pyproject の版 {v})から "
                   "`tools/gen_maturity.py` が作る。段の定義は [MATURITY.md]({link}))。"),
        mat_cols=("段", "意味", "能力"),
        stages=("実装はあるが、試験や走る例が揃っていない", "真値を持つ合成データで自動検証",
                "公開の実測データを使う例が門で走る", "実機で検証(外部の報告を受理したときだけ)"),
        examples="例 {total} 本のうち、門が実際に走らせるもの {run} 本。",
        hist_h="### 版ごとの op の数",
        hist_cols=("版", "日付", "索引の op 計", "うち型付き台帳", "HALCON 対応", "PoC", "回帰テスト"),
        hist_tail="— = その版では測っていない。全部の版と列の定義: [OP_COUNT_HISTORY.md]({link})。",
        halcon_recount=("{first}〜{prev} の HALCON 対応 {old} は当時の記録値。{ver} からは数え方を"
                        "改めた {new}(実装が {diff} 本増えたのではない)。"),
        ledger_into_index=("{ver} で型付き台帳を初めて索引に含めた。{old} → {new} は数え方の変更で、"
                           "新しい実装ではない(台帳は {lfirst} から在ったが索引の外だった)。"),
    ),
    "en": dict(
        title="How it is checked",
        intro=("None of these numbers is typed by hand: `tools/gen_trust_block.py` renders them from "
               "measurement files in `docs/` ({files}), and `tests/test_trust_block.py` fails if this "
               "section drifts from them. Every number carries the version and date it was measured at."),
        tests=("**{n} regression tests** — {rel}, commit `{commit}`, counted with "
               "`pytest --collect-only` on {date} with every optional backend installed (without them, "
               "tests for the missing backends are not collected and the count is lower)."),
        after="the tree after {v} (includes unreleased changes)", inrel="included in {v}",
        gates_h="### If you add one operator, what checks it",
        gates_intro=("For each tier, one deliberately broken operator was injected and the whole suite "
                     "run; failing tests were counted (mutation probe). ✓ = a gate catches that "
                     "breakage, ✗ = **nothing catches it yet**."),
        meas="Measurement {mark}: commit `{commit}`, {date}, {rel}.",
        cols=("tier", "measured", "bookkeeping gates", "behavioural gates", "raises", "NaN",
              "wrong type", "nondeterministic", "ignores parameters", "no description",
              "English-only description", "accepts empty input"),
        gates_notes=("Bookkeeping gates fire for any new operator, even a correct one, until its note "
                     "and index entries are regenerated. Behavioural gates = the further distinct tests "
                     "that fail because of how the operator is broken."),
        not_covered=("Not measured: plausible but wrong values (distance from ground truth), speed, "
                     "OS-specific failures, two breakages at once. ✓ means at least one test failed, "
                     "not that its message explains why."),
        tiers={"t1": "2-D core (`ops.REGISTRY`)", "t2": "n-ary", "t3": "colour",
               "t4": "typed ledger + `tb_` bridge", "t5": "typed ledger (no bridge)",
               "t5b": "3-D ledger", "t6": "facade only"},
        mat_h="### Verification stage",
        mat_intro=("The {n} capabilities, split by how they are verified (`docs/maturity.json`, rebuilt "
                   "by `tools/gen_maturity.py` from the current tree (pyproject version {v}); stage definitions in "
                   "[MATURITY.md]({link}))."),
        mat_cols=("stage", "meaning", "capabilities"),
        stages=("implemented; tests or a running example still missing",
                "verified automatically against synthetic ground truth",
                "an example on public measured data runs in a gate",
                "validated on hardware (only from accepted external reports)"),
        examples="Of {total} examples, {run} are actually run by a gate.",
        hist_h="### Operator counts by version",
        hist_cols=("version", "date", "index total", "of which typed ledger", "HALCON", "PoC",
                   "regression tests"),
        hist_tail=("— = not measured for that version. All versions and column definitions: "
                   "[OP_COUNT_HISTORY.md]({link})."),
        halcon_recount=("The HALCON figure {old} for {first}–{prev} is the value recorded at the time; "
                        "from {ver} it is {new} under a revised count (not {diff} new implementations)."),
        ledger_into_index=("{ver} is the first version whose index includes the typed ledger: "
                           "{old} → {new} is a change in what is counted, not new implementation "
                           "(the ledger existed from {lfirst} but sat outside the index)."),
    ),
    "zh": dict(
        title="如何验证",
        intro=("这里的数字都不是手写的: `tools/gen_trust_block.py` 根据 `docs/` 中的测量数据({files})"
               "生成本节,若本节与数据不一致,`tests/test_trust_block.py` 就会失败。每个数字都附有测量时的"
               "版本和日期。"),
        tests=("**回归测试 {n} 个** — {rel},commit `{commit}`,{date} 用 `pytest --collect-only` 统计"
               "(安装了全部可选后端的环境。未安装时,依赖该后端的测试不会被收集,数量会更少)。"),
        after="{v} 之后的代码树(含未发布的修改)", inrel="包含在 {v} 中",
        gates_h="### 新增一个算子时,有哪些检查会验证它",
        gates_intro=("对每一层,只注入一个故意弄坏的算子并运行全部测试,统计失败的测试(mutation probe)。"
                     "✓ = 有检查能发现这种损坏,✗ = **目前还没有**。"),
        meas="测量 {mark}: commit `{commit}`,{date},{rel}。",
        cols=("层", "测量", "手续检查", "行为检查", "抛出异常", "NaN", "类型错误", "不确定",
              "忽略参数", "无说明", "说明仅英文", "接受空输入"),
        gates_notes=("手续检查 = 即使算子写得正确,在重新生成说明和索引之前也会失败的检查数。"
                     "行为检查 = 除此之外,因算子的损坏方式而失败的检查种类数。"),
        not_covered=("未测量: 看似合理但错误的值(与真值的差)、速度、特定操作系统的故障、两种以上损坏的组合。"
                     "✓ 表示至少有一个测试失败,不保证其信息能说明原因。"),
        tiers={"t1": "2-D 核心(`ops.REGISTRY`)", "t2": "n 元", "t3": "颜色",
               "t4": "类型化台账 + `tb_` 桥", "t5": "类型化台账(无桥)", "t5b": "3-D 台账",
               "t6": "仅 facade"},
        mat_h="### 验证阶段",
        mat_intro=("{n} 项能力按验证方式分类的数量(`docs/maturity.json`,由 `tools/gen_maturity.py` "
                   "从当前代码树(pyproject 版本 {v})生成;阶段定义见 [MATURITY.md]({link}))。"),
        mat_cols=("阶段", "含义", "能力"),
        stages=("已实现,但测试或可运行的示例尚不齐全", "已用合成真值自动验证",
                "使用公开实测数据的示例在检查中实际运行", "已在实机上验证(仅在接受外部报告时)"),
        examples="{total} 个示例中,检查实际运行的有 {run} 个。",
        hist_h="### 各版本的算子数",
        hist_cols=("版本", "日期", "索引算子总数", "其中类型化台账", "HALCON 对应", "PoC", "回归测试"),
        hist_tail="— = 该版本未测量。全部版本及列定义: [OP_COUNT_HISTORY.md]({link})(日语/英语)。",
        halcon_recount=("{first}–{prev} 的 HALCON 对应数 {old} 是当时的记录值;自 {ver} 起按修订后的"
                        "计数方法为 {new}(并非新增了 {diff} 个实现)。"),
        ledger_into_index=("{ver} 首次将类型化台账纳入索引: {old} → {new} 是计数口径的变化,并非新的实现"
                           "(台账自 {lfirst} 起就存在,但在索引之外)。"),
    ),
    "tw": dict(
        title="如何驗證",
        intro=("這裡的數字都不是手寫的: `tools/gen_trust_block.py` 依據 `docs/` 中的量測資料({files})"
               "產生本節,若本節與資料不一致,`tests/test_trust_block.py` 就會失敗。每個數字都附有量測時的"
               "版本與日期。"),
        tests=("**回歸測試 {n} 個** — {rel},commit `{commit}`,{date} 以 `pytest --collect-only` 計數"
               "(安裝了全部選用後端的環境。未安裝時,依賴該後端的測試不會被收集,數量會較少)。"),
        after="{v} 之後的程式碼樹(含未發布的修改)", inrel="包含在 {v} 中",
        gates_h="### 新增一個運算子時,有哪些檢查會驗證它",
        gates_intro=("對每一層,只注入一個故意弄壞的運算子並執行全部測試,計算失敗的測試(mutation probe)。"
                     "✓ = 有檢查能發現這種損壞,✗ = **目前還沒有**。"),
        meas="量測 {mark}: commit `{commit}`,{date},{rel}。",
        cols=("層", "量測", "手續檢查", "行為檢查", "拋出例外", "NaN", "型別錯誤", "不確定",
              "忽略參數", "無說明", "說明僅英文", "接受空輸入"),
        gates_notes=("手續檢查 = 即使運算子寫得正確,在重新產生說明與索引之前也會失敗的檢查數。"
                     "行為檢查 = 除此之外,因運算子的損壞方式而失敗的檢查種類數。"),
        not_covered=("未量測: 看似合理但錯誤的值(與真值的差)、速度、特定作業系統的故障、兩種以上損壞的組合。"
                     "✓ 表示至少有一個測試失敗,不保證其訊息能說明原因。"),
        tiers={"t1": "2-D 核心(`ops.REGISTRY`)", "t2": "n 元", "t3": "色彩",
               "t4": "型別化台帳 + `tb_` 橋", "t5": "型別化台帳(無橋)", "t5b": "3-D 台帳",
               "t6": "僅 facade"},
        mat_h="### 驗證階段",
        mat_intro=("{n} 項能力依驗證方式分類的數量(`docs/maturity.json`,由 `tools/gen_maturity.py` "
                   "從目前的程式碼樹(pyproject 版本 {v})產生;階段定義見 [MATURITY.md]({link}))。"),
        mat_cols=("階段", "含義", "能力"),
        stages=("已實作,但測試或可執行的範例尚未齊全", "已用合成真值自動驗證",
                "使用公開實測資料的範例在檢查中實際執行", "已在實機上驗證(僅在接受外部報告時)"),
        examples="{total} 個範例中,檢查實際執行的有 {run} 個。",
        hist_h="### 各版本的運算子數",
        hist_cols=("版本", "日期", "索引運算子總數", "其中型別化台帳", "HALCON 對應", "PoC", "回歸測試"),
        hist_tail="— = 該版本未量測。全部版本與欄位定義: [OP_COUNT_HISTORY.md]({link})(日文/英文)。",
        halcon_recount=("{first}–{prev} 的 HALCON 對應數 {old} 是當時的記錄值;自 {ver} 起依修訂後的"
                        "計數方式為 {new}(並非新增了 {diff} 個實作)。"),
        ledger_into_index=("{ver} 首次將型別化台帳納入索引: {old} → {new} 是計數口徑的變更,並非新的實作"
                           "(台帳自 {lfirst} 起就存在,但在索引之外)。"),
    ),
    "ko": dict(
        title="어떻게 확인하는가",
        intro=("여기의 숫자는 손으로 쓰지 않습니다. `tools/gen_trust_block.py`가 `docs/`의 측정 데이터"
               "({files})로부터 이 절을 생성하며, 데이터와 어긋나면 `tests/test_trust_block.py`가 "
               "실패합니다. 모든 숫자에 측정한 버전과 날짜를 붙였습니다."),
        tests=("**회귀 테스트 {n}건** — {rel}, commit `{commit}`, {date}에 `pytest --collect-only`로 "
               "센 값(선택적 백엔드를 모두 설치한 환경. 설치하지 않으면 해당 백엔드를 쓰는 테스트가 "
               "수집되지 않아 건수가 줄어듭니다)."),
        after="{v} 이후의 트리(미배포 변경 포함)", inrel="{v}에 포함",
        gates_h="### 연산자를 하나 추가하면 무엇이 확인하는가",
        gates_intro=("층마다 일부러 망가뜨린 연산자를 하나만 넣고 전체 테스트를 돌려, 실패한 테스트를 "
                     "셌습니다(mutation probe). ✓ = 그 망가짐을 잡는 게이트가 있음, ✗ = **아직 없음**."),
        meas="측정 {mark}: commit `{commit}`, {date}, {rel}.",
        cols=("층", "측정", "절차 게이트", "동작 게이트", "예외", "NaN", "잘못된 형", "비결정적",
              "인자 무시", "설명 없음", "영어로만 된 설명", "빈 입력 수용"),
        gates_notes=("절차 게이트 = 올바르게 작성한 연산자라도 노트와 색인을 다시 생성할 때까지 실패하는 "
                     "게이트 수. 동작 게이트 = 그와 별도로, 망가진 방식 때문에 실패하는 게이트의 종류 수."),
        not_covered=("측정하지 않은 것: 그럴듯하지만 틀린 값(참값과의 차이), 속도, OS 고유의 실패, 두 가지 "
                     "이상의 망가짐의 조합. ✓는 적어도 하나의 테스트가 실패했다는 뜻이며, 그 메시지가 원인을 "
                     "설명한다는 보장은 아닙니다."),
        tiers={"t1": "2-D 핵심(`ops.REGISTRY`)", "t2": "n항", "t3": "색",
               "t4": "타입 대장 + `tb_` 브리지", "t5": "타입 대장(브리지 없음)", "t5b": "3-D 대장",
               "t6": "facade만"},
        mat_h="### 검증 단계",
        mat_intro=("능력 {n}건을 무엇으로 확인했는지에 따라 나눈 수(`docs/maturity.json`, 현재 트리(pyproject 버전 {v})에서 "
                   "`tools/gen_maturity.py`가 생성. 단계 정의는 [MATURITY.md]({link}))."),
        mat_cols=("단계", "의미", "능력"),
        stages=("구현은 있으나 테스트나 실행되는 예가 아직 갖춰지지 않음", "참값을 가진 합성 데이터로 자동 검증",
                "공개 실측 데이터를 쓰는 예가 게이트에서 실제로 실행됨", "실기로 검증(외부 보고를 수리한 경우에만)"),
        examples="예 {total}건 중 게이트가 실제로 실행하는 것은 {run}건.",
        hist_h="### 버전별 연산자 수",
        hist_cols=("버전", "날짜", "색인의 연산자 합계", "그중 타입 대장", "HALCON 대응", "PoC", "회귀 테스트"),
        hist_tail="— = 그 버전에서는 측정하지 않음. 모든 버전과 열 정의: [OP_COUNT_HISTORY.md]({link})(일본어/영어).",
        halcon_recount=("{first}–{prev}의 HALCON 대응 {old}은 당시의 기록값이며, {ver}부터는 개정된 계수 "
                        "방식으로 {new}입니다({diff}개의 구현이 새로 늘어난 것이 아님)."),
        ledger_into_index=("{ver}에서 처음으로 타입 대장을 색인에 포함했습니다. {old} → {new}는 세는 범위의 "
                           "변경이며 새 구현이 아닙니다(대장은 {lfirst}부터 있었으나 색인 밖에 있었음)."),
    ),
    "de": dict(
        title="Wie geprüft wird",
        intro=("Keine dieser Zahlen ist von Hand geschrieben: `tools/gen_trust_block.py` erzeugt diesen "
               "Abschnitt aus Messdateien in `docs/` ({files}), und `tests/test_trust_block.py` schlägt "
               "fehl, wenn er davon abweicht. Jede Zahl trägt Version und Datum ihrer Messung."),
        tests=("**{n} Regressionstests** — {rel}, Commit `{commit}`, am {date} mit "
               "`pytest --collect-only` gezählt, mit allen optionalen Backends installiert (ohne sie "
               "werden die Tests der fehlenden Backends nicht gesammelt und die Zahl ist kleiner)."),
        after="Stand nach {v} (mit unveröffentlichten Änderungen)", inrel="in {v} enthalten",
        gates_h="### Was einen neu hinzugefügten Operator prüft",
        gates_intro=("Pro Schicht wurde genau ein absichtlich defekter Operator eingefügt und die gesamte "
                     "Testsuite ausgeführt; gezählt wurden die fehlschlagenden Tests (Mutation Probe). "
                     "✓ = ein Gate erkennt diesen Defekt, ✗ = **noch keines**."),
        meas="Messung {mark}: Commit `{commit}`, {date}, {rel}.",
        cols=("Schicht", "Messung", "Verwaltungs-Gates", "Verhaltens-Gates", "wirft Ausnahme", "NaN",
              "falscher Typ", "nicht deterministisch", "ignoriert Parameter", "keine Beschreibung",
              "Beschreibung nur Englisch", "akzeptiert leere Eingabe"),
        gates_notes=("Verwaltungs-Gates schlagen bei jedem neuen Operator an, auch bei einem korrekten, bis "
                     "seine Notiz und sein Indexeintrag neu erzeugt sind. Verhaltens-Gates = die weiteren, "
                     "verschiedenen Tests, die wegen der Art des Defekts fehlschlagen."),
        not_covered=("Nicht gemessen: plausible, aber falsche Werte (Abstand zur Grundwahrheit), "
                     "Geschwindigkeit, betriebssystemspezifische Fehler, zwei Defekte zugleich. ✓ heißt, "
                     "dass mindestens ein Test fehlschlug, nicht dass seine Meldung den Grund erklärt."),
        tiers={"t1": "2-D-Kern (`ops.REGISTRY`)", "t2": "n-är", "t3": "Farbe",
               "t4": "typisiertes Register + `tb_`-Brücke", "t5": "typisiertes Register (ohne Brücke)",
               "t5b": "3-D-Register", "t6": "nur Fassade"},
        mat_h="### Verifikationsstufe",
        mat_intro=("Die {n} Fähigkeiten, aufgeteilt nach Art der Prüfung (`docs/maturity.json`, von "
                   "`tools/gen_maturity.py` aus dem aktuellen Stand (pyproject-Version {v}) erzeugt; Stufen erklärt in "
                   "[MATURITY.md]({link}))."),
        mat_cols=("Stufe", "Bedeutung", "Fähigkeiten"),
        stages=("implementiert; Tests oder ein laufendes Beispiel fehlen noch",
                "automatisch gegen synthetische Grundwahrheit geprüft",
                "ein Beispiel mit öffentlichen Messdaten läuft in einem Gate",
                "an Hardware validiert (nur über angenommene externe Berichte)"),
        examples="Von {total} Beispielen werden {run} tatsächlich von einem Gate ausgeführt.",
        hist_h="### Operatorzahlen pro Version",
        hist_cols=("Version", "Datum", "Index gesamt", "davon typisiertes Register", "HALCON", "PoC",
                   "Regressionstests"),
        hist_tail=("— = für diese Version nicht gemessen. Alle Versionen und Spaltendefinitionen: "
                   "[OP_COUNT_HISTORY.md]({link}) (Japanisch/Englisch)."),
        halcon_recount=("Der HALCON-Wert {old} für {first}–{prev} ist der damals festgehaltene Wert; ab "
                        "{ver} beträgt er nach geänderter Zählung {new} (keine {diff} neuen "
                        "Implementierungen)."),
        ledger_into_index=("{ver} ist die erste Version, deren Index das typisierte Register enthält: "
                           "{old} → {new} ist eine Änderung der Zählweise, keine neue Implementierung "
                           "(das Register gab es ab {lfirst}, aber außerhalb des Index)."),
    ),
}

_DATA_FILES = ("test_count.json", "gate_inventory.json", "maturity.json", "op_count_history.json")


# ---------------------------------------------------------------- 入力

def _load(rel: str) -> dict:
    with io.open(os.path.join(_ROOT, rel), encoding="utf-8") as f:
        return json.load(f)


def pyproject_version(root: str = _ROOT) -> str:
    """``pyproject.toml`` の ``[project] version``。読めなければ例外(黙って既定値にしない)。"""
    with io.open(os.path.join(root, "pyproject.toml"), encoding="utf-8") as f:
        m = re.search(r'^version\s*=\s*"([^"]+)"', f.read(), re.M)
    if not m:
        raise RuntimeError("pyproject.toml に version が無い")
    return m.group(1)


def vkey(v: str) -> tuple:
    return tuple(int(x) for x in v.split("."))


def load_all() -> dict:
    return {"tests": _load("docs/test_count.json"), "gates": _load("docs/gate_inventory.json"),
            "maturity": _load("docs/maturity.json"), "history": _load("docs/op_count_history.json"),
            "index": _load("docs/OP_INDEX.json"), "version": pyproject_version()}


# ---------------------------------------------------------------- 描画

def _n(x) -> str:
    return "—" if x is None else "{:,}".format(x)


def _row(history: dict, version: str) -> dict:
    for r in history["rows"]:
        if r["version"] == version:
            return r
    raise KeyError(version)


def _rel(t: dict, kind: str, release: str) -> str:
    return t["after" if kind == "after_release" else "inrel"].format(v=release)


def _note(t: dict, history: dict, ch: dict) -> str:
    """定義が変わった版の注記。**数は行から差し込む**(注記に数を手書きしない)。"""
    rows = history["rows"]
    cur, prev = _row(history, ch["version"]), _row(history, ch["compare_with"])
    if ch["kind"] == "halcon_recount":
        return t["halcon_recount"].format(first=rows[0]["version"], prev=prev["version"],
                                          old=_n(prev["halcon"]), ver=cur["version"],
                                          new=_n(cur["halcon"]),
                                          diff=_n(cur["halcon"] - prev["halcon"]))
    if ch["kind"] == "ledger_into_index":
        lfirst = next(r["version"] for r in rows if r["ledger"] is not None)
        return t["ledger_into_index"].format(ver=cur["version"], old=_n(prev["index"]),
                                             new=_n(cur["index"]), lfirst=lfirst)
    raise ValueError("未知の注記の種類: %r" % ch["kind"])


def summary_versions(history: dict) -> list:
    """トップに出す版: 各 x.y.0 と、定義の変わり目の前後(注記が指す版)。"""
    named = set()
    for ch in history["definition_changes"]:
        named.update((ch["version"], ch["compare_with"]))
    return [r["version"] for r in history["rows"]
            if r["version"].endswith(".0") or r["version"] in named]


def build_block(lang: str, data: dict, link_prefix: str = "") -> str:
    t = L10N[lang]
    tc, gi, mat, hist, ver = (data["tests"], data["gates"], data["maturity"], data["history"],
                              data["version"])
    files = ", ".join("`%s`" % f for f in _DATA_FILES)
    out = [START,
           "<!-- generated by tools/gen_trust_block.py from docs/{test_count,gate_inventory,maturity,"
           "op_count_history}.json; edit the data, not this block -->",
           "", "## " + t["title"], "", t["intro"].format(files=files), "",
           t["tests"].format(n=_n(tc["count"]), rel=_rel(t, tc["relation"], tc["version"]),
                             commit=tc["commit"], date=tc["date"]),
           "", t["gates_h"], "", t["gates_intro"], ""]
    marks = {}
    for i, m in enumerate(gi["measurements"]):
        marks[m["id"]] = "①②③④⑤⑥⑦⑧⑨"[i]
        out.append("- " + t["meas"].format(mark=marks[m["id"]], commit=m["commit"], date=m["date"],
                                           rel=_rel(t, m["relation"], m["release"])))
    out += ["", "| " + " | ".join(t["cols"]) + " |", "|" + "---|" * len(t["cols"])]
    for tier in gi["tiers"]:
        cells = [t["tiers"][tier["id"]], marks[tier["measurement"]],
                 str(tier["bookkeeping_gates"]), str(tier["behavioural_gates"])]
        cells += ["✓" if tier["caught"][c] else "✗" for c in CHECKS]
        out.append("| " + " | ".join(cells) + " |")
    out += ["", t["gates_notes"], "", t["not_covered"], ""]

    caps = mat["capabilities"]
    counts = {s: sum(1 for c in caps if c.get("status") == s) for s in STAGES}
    ex = mat["example_execution"]
    out += [t["mat_h"], "",
            t["mat_intro"].format(n=_n(len(caps)), v=ver, link=link_prefix + "MATURITY.md"), "",
            "| " + " | ".join(t["mat_cols"]) + " |", "|---|---|---|"]
    for s, meaning in zip(STAGES, t["stages"]):
        out.append("| `%s` | %s | %s |" % (s, meaning, _n(counts[s])))
    out += ["", t["examples"].format(total=_n(ex["examples2d_total"]),
                                     run=_n(ex["examples2d_total"] - ex["not_run_by_any_gate"])), ""]

    out += [t["hist_h"], "", "| " + " | ".join(t["hist_cols"]) + " |",
            "|" + "---|" * len(t["hist_cols"])]
    for v in summary_versions(hist):
        r = _row(hist, v)
        out.append("| %s | %s | %s | %s | %s | %s | %s |" % (
            r["version"], r["date"], _n(r["index"]),
            ("—" if r["index"] is None else
             _n(r["ledger"]) if "ledger" in r["index_tiers"] else "0"),
            _n(r["halcon"]), _n(r["poc"]), _n(r["tests"])))
    out.append("")
    for ch in hist["definition_changes"]:
        out.append("- " + _note(t, hist, ch))
    out += ["", t["hist_tail"].format(link=link_prefix + "OP_COUNT_HISTORY.md"), "", END]
    return "\n".join(out)


def build_history_page(data: dict) -> str:
    """全版の表(日英併記)。"""
    hist = data["history"]
    cols = hist["columns"]
    keys = ("registry", "nary", "color", "ledger", "index", "halcon", "poc", "tests")
    head_ja = ("2-D 単入力", "n 入力", "色", "型付き台帳(族)", "索引の計", "HALCON 対応", "PoC",
               "回帰テスト")
    head_en = ("2-D single-input", "n-ary", "colour", "typed ledger (families)", "index total",
               "HALCON", "PoC", "regression tests")
    out = ["# op の数の推移(版ごと) / Operator counts by version", "",
           "<!-- generated by tools/gen_trust_block.py from docs/op_count_history.json; "
           "edit the data, not this page -->", "",
           "**Language:** 日本語 / English (併記 / side by side).", "",
           hist["about"]["ja"], "", "*" + hist["about"]["en"] + "*", "",
           "| 版 version | 日付 date | " + " | ".join(
               "%s<br>%s" % (j, e) for j, e in zip(head_ja, head_en)) + " |",
           "|" + "---|" * (2 + len(keys))]
    for r in hist["rows"]:
        cells = []
        for k in keys:
            if k == "ledger":
                cells.append(_n(r["ledger"]) + ("" if r["ledger_families"] is None
                                                else " (%d)" % r["ledger_families"]))
            elif k == "index":
                c = _n(r["index"])
                if r["index"] is not None and r["ledger"] is not None \
                        and "ledger" not in r["index_tiers"]:
                    c += " †"
                cells.append(c)
            else:
                cells.append(_n(r[k]))
        out.append("| %s | %s | %s |" % (r["version"], r["date"], " | ".join(cells)))
    out += ["", "† 型付き台帳はあったが、索引の計に含めていない版。 / "
                "*The typed ledger existed but was not part of the index total.*", "",
            "— その版では測っていない / その版に無い。 / *Not measured, or absent in that version.*", "",
            "## 定義が変わった版 / Where the definition changed", ""]
    for ch in hist["definition_changes"]:
        out.append("- " + _note(L10N["ja"], hist, ch))
        out.append("  *" + _note(L10N["en"], hist, ch) + "*")
    out += ["", "## 列の定義 / Columns", "", "| 列 column | 意味 | meaning |", "|---|---|---|"]
    for k in ("registry", "nary", "color", "ledger", "index", "halcon", "poc", "tests"):
        out.append("| `%s` | %s | %s |" % (k, cols[k]["ja"], cols[k]["en"]))
    out += ["", "## 測り方 / How it was measured (%s)" % hist["method"]["measured_on"], "",
            hist["method"]["ja"], "", "*" + hist["method"]["en"] + "*", ""]
    return "\n".join(out)


# ---------------------------------------------------------------- 門(テストからも呼ぶ)

def splice(text: str, block: str, anchor: str) -> str:
    """マーカーの間を差し替える。無ければ ``anchor`` の直前に入れる(初回のみ)。"""
    if START in text and END in text:
        head, rest = text.split(START, 1)
        return head + block + rest.split(END, 1)[1]
    if anchor not in text:
        raise RuntimeError("差し込み位置の目印が無い: %r" % anchor)
    i = text.index(anchor)
    return text[:i] + block + "\n\n" + text[i:]


def extract(text: str) -> str | None:
    text = text.replace("\r\n", "\n")
    if START not in text or END not in text:
        return None
    return START + text.split(START, 1)[1].split(END, 1)[0] + END


def drift_problems(data: dict | None = None, root: str = _ROOT) -> list:
    """生成物(ブロックと全版の表)が、いまのデータから描いたものと食い違っていれば列挙する。"""
    data = data or load_all()
    probs = []
    for rel, lang, _anchor, prefix in TARGETS:
        with io.open(os.path.join(root, rel), encoding="utf-8") as f:
            got = extract(f.read())
        if got is None:
            probs.append("%s: trust-block のマーカーが無い" % rel)
        elif got != build_block(lang, data, prefix):
            probs.append("%s: ブロックが生成物と食い違う(手で直した? データを変えて回し忘れた?)" % rel)
    p = os.path.join(root, HISTORY_PAGE)
    have = io.open(p, encoding="utf-8").read().replace("\r\n", "\n") if os.path.isfile(p) else None
    if have != build_history_page(data):
        probs.append("%s: 全版の表が生成物と食い違う" % HISTORY_PAGE)
    return probs


def stale_problems(data: dict | None = None, release: bool = False) -> list:
    """データが今の版のものでなければ列挙する(= 版を上げたのに測り直していない)。

    * pyproject の版の行が ``op_count_history.json`` に無い
    * ``test_count.json`` / ``gate_inventory.json`` が別の版のもの
    * 現行の行が索引より**多い**(リリースした op が索引から消えた)
    * ``release=True``(リリース直前)なら、現行の行と索引が層ごとに**厳密に一致**すること
    """
    data = data or load_all()
    ver, hist, idx = data["version"], data["history"], data["index"]
    probs = []
    versions = [r["version"] for r in hist["rows"]]
    if versions != sorted(versions, key=vkey) or len(set(versions)) != len(versions):
        probs.append("op_count_history.json の行が版の順に並んでいない / 重複がある")
    try:
        row = _row(hist, ver)
    except KeyError:
        row = None
        probs.append("op_count_history.json に版 %s の行が無い —— リリースしたら 1 行足す"
                     "(CONTRIBUTING.md「Cutting a release」)" % ver)
    if data["tests"]["version"] != ver:
        probs.append("test_count.json は版 %s のもの(pyproject は %s)—— 件数を測り直す"
                     % (data["tests"]["version"], ver))
    if data["gates"]["valid_for_version"] != ver:
        probs.append("gate_inventory.json は版 %s のもの(pyproject は %s)—— 門の棚卸しを測り直すか、"
                     "変わっていないことを確かめて valid_for_version を上げる"
                     % (data["gates"]["valid_for_version"], ver))
    if row is not None:
        tiers = idx["tiers"]
        for k in ("registry", "nary", "color", "ledger"):
            have = tiers.get(k, 0)
            want = row[k] or 0
            if want > have or (release and want != have):
                probs.append("版 %s の行の %s = %d が、いまの索引(docs/OP_INDEX.json)の %d と合わない"
                             % (ver, k, want, have))
        if row["index"] is None or row["index"] > idx["n_ops"] or (
                release and row["index"] != idx["n_ops"]):
            probs.append("版 %s の行の索引の計 = %s が、いまの索引の %d と合わない"
                         % (ver, row["index"], idx["n_ops"]))
    return probs


# ---------------------------------------------------------------- 書き込み

def _write_keep_eol(path: str, text_lf: str) -> None:
    """既存ファイルの改行(CRLF / LF)を保って書く。"""
    eol = "\n"
    if os.path.isfile(path):
        with open(path, "rb") as f:
            if b"\r\n" in f.read():
                eol = "\r\n"
    with io.open(path, "w", encoding="utf-8", newline=eol) as f:
        f.write(text_lf)


def write_all(data: dict | None = None) -> None:
    data = data or load_all()
    for rel, lang, anchor, prefix in TARGETS:
        p = os.path.join(_ROOT, rel)
        with io.open(p, encoding="utf-8") as f:
            s = f.read().replace("\r\n", "\n")
        new = splice(s, build_block(lang, data, prefix), anchor)
        if new != s:
            _write_keep_eol(p, new)
            print("wrote trust-block ->", rel)
    p = os.path.join(_ROOT, HISTORY_PAGE)
    page = build_history_page(data)
    old = io.open(p, encoding="utf-8").read().replace("\r\n", "\n") if os.path.isfile(p) else None
    if old != page:
        _write_keep_eol(p, page)
        print("wrote", HISTORY_PAGE)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="食い違い・古びがあれば exit 1(書かない)")
    ap.add_argument("--release-check", action="store_true",
                    help="--check に加え、現行の行と索引の厳密一致を見る(リリース直前に)")
    a = ap.parse_args(argv)
    data = load_all()
    if a.check or a.release_check:
        probs = drift_problems(data) + stale_problems(data, release=a.release_check)
        for p in probs:
            print("★", p)
        print("OK" if not probs else "%d 件" % len(probs))
        return 1 if probs else 0
    stale = stale_problems(data)
    for p in stale:
        print("★(データが古い)", p)
    write_all(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
