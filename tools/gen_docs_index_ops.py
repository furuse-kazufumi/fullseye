#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""索引(`docs/README*.md`)に「オペレータを探す」節を差し込む。

    py -3.11 tools/gen_docs_index_ops.py

## なぜ要るか(2026-09-06)

索引は設計文書へのリンク表だけで、**`docs/ops/` へのリンクが 1 本も無かった**
(`grep -c "ops/" docs/README.md` → 0)。そこには op ノートが 1,839 本と
族ガイドが 48 本あり、**この repo でいちばん大きい中身**で、公開サイト
<https://furuse.work/> を訪ねる人がまず見たいものである。入口が無ければ
在るものは無いのと同じ。

数(op 数・族の数)は動くので、**台帳から生成**してマーカーの間に差し込む。
`<!-- ops-index:start -->` と `<!-- ops-index:end -->` の外は手書きのまま残す。
"""
from __future__ import annotations

import io
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "tools"))

import opdocs as OD  # noqa: E402

START, END = "<!-- ops-index:start -->", "<!-- ops-index:end -->"
PSTART, PEND = "<!-- poc-index:start -->", "<!-- poc-index:end -->"
GH = "https://github.com/furuse-kazufumi/fullseye/blob/master/examples/%s.py"

#: 言語 -> (節題, 導入文, 表の見出し 2 つ)
POC_L10N = {
    "": ("PoC シリーズ — 真値つきで実問題を解いた {n} 本",
         "どれも**真値を閉形式か合成で厳密に持ち、ゼロ点(何もしない場合)を必ず併記**"
         "します。壊れ方は 1 つの指標に畳まず別々に数え、原因は対照群で分けます。"
         "全文と実行手順は [examples/README.md](../examples/README.md)。",
         ("分野", "PoC と、そこで分かったこと")),
    "en": ("PoC series — {n} real problems solved against a ground truth",
           "Every one carries a closed-form or synthetic ground truth and a null "
           "model. Failure modes are counted separately, never folded into one "
           "number, and causes are separated with a control group. Full list: "
           "[examples/README.md](../examples/README.md).",
           ("field", "PoC and what it showed")),
    "zh": ("PoC 系列 — 带真值求解的 {n} 个实际问题",
           "每一个都具有闭式或合成的真值，并必定附带零点(什么都不做)。失败模式分开计数，"
           "原因用对照组区分。完整列表: [examples/README.md](../examples/README.md)。",
           ("领域", "PoC 与其结论")),
    "tw": ("PoC 系列 — 帶真值求解的 {n} 個實際問題",
           "每一個都具有閉式或合成的真值，並必定附上零點(什麼都不做)。失敗方式分開計數，"
           "原因以對照組區分。完整列表: [examples/README.md](../examples/README.md)。",
           ("領域", "PoC 與其結論")),
    "ko": ("PoC 시리즈 — 참값을 두고 푼 실제 문제 {n}건",
           "모두 닫힌 형태 또는 합성으로 엄밀한 참값을 가지며, 제로 포인트(아무것도 하지 "
           "않는 경우)를 반드시 함께 적습니다. 전체 목록: "
           "[examples/README.md](../examples/README.md).",
           ("분야", "PoC와 알아낸 것")),
    "de": ("PoC-Serie — {n} reale Aufgaben mit Grundwahrheit",
           "Jede hat eine geschlossene oder synthetische Grundwahrheit und ein "
           "Nullmodell. Fehlerarten werden getrennt gezählt. Vollständige Liste: "
           "[examples/README.md](../examples/README.md).",
           ("Feld", "PoC und Befund"))}

TASK_L = {"metrology": ("計測", "metrology"), "diagnostics": ("診断", "diagnostics"),
          "photometry": ("測光", "photometry"), "imaging_quality": ("撮像品質", "imaging quality"),
          "flow": ("動き", "motion"), "segmentation": ("領域分割", "segmentation"),
          "morphology": ("形態", "morphology"), "geometry": ("幾何", "geometry"),
          "separation": ("分離", "separation"), "calibration": ("校正", "calibration"),
          "decoding": ("読み取り", "decoding"), "depth": ("深度", "depth"),
          "registration": ("位置合わせ", "registration"), "restoration": ("復元", "restoration"),
          "upscaling": ("超解像", "super-resolution"), "forensics": ("改ざん検出", "forensics"),
          "terrain": ("地形", "terrain"), "tomography": ("断層", "tomography"),
          "color": ("色", "colour"), "rectification": ("正対化", "rectification"),
          "vibration": ("振動", "vibration"), "ranging": ("測距", "ranging"),
          "appearance": ("見え方", "appearance")}


def build_poc(lang: str = "") -> str:
    import examples2d as EX

    title, intro, cols = POC_L10N[lang]
    pocs = [r for r in EX.EXAMPLES if r["id"].startswith("poc_")]
    by = {}
    for r in pocs:
        by.setdefault(r["task"], []).append(r)
    out = [PSTART, "", "## " + title.format(n=len(pocs)), "", intro, "",
           "| %s | %s |" % cols, "|---|---|"]
    for t in sorted(by, key=lambda k: (-len(by[k]), k)):
        ja, en = TASK_L.get(t, (t, t))
        label = ja if lang == "" else en
        items = []
        for r in sorted(by[t], key=lambda x: x["id"]):
            items.append("[**%s**](%s) — %s" % (r["name"], GH % r["id"], r["name"]))
        cell = "<br>".join("[`%s`](%s) %s" % (r["id"], GH % r["id"], r["name"])
                           for r in sorted(by[t], key=lambda x: x["id"]))
        out.append("| %s (%d) | %s |" % (label, len(by[t]), cell))
    out += ["", PEND]
    return chr(10).join(out)

#: 言語 → (節題, 導入文, 表の見出し 3 つ, 検索の案内)
L10N = {
    "": ("オペレータを探す",
         "**{total:,} 本の op ノート**(呼び出し方・型の契約・HALCON 対応・文献・"
         "来歴)と **{nguide} 本の族ガイド**があります。次元ごとの入口:",
         ("次元", "op 数", "入口"),
         "名前で引くなら `py -3.11 imgevolve.py ops --search edge`、"
         "全 op の対応表は [OP_CATALOG.md](OP_CATALOG.md)、次元をまたぐ入口は [ops/INDEX.md](ops/INDEX.md)。"),
    "en": ("Find an operator",
           "**{total:,} per-operator notes** (call form, type contract, HALCON "
           "counterpart, references, provenance) and **{nguide} family guides**. "
           "Entry points by dimension:",
           ("dimension", "ops", "entry"),
           "Search by name with `py -3.11 imgevolve.py ops --search edge`; the "
           "full cross-library table is [OP_CATALOG.md](OP_CATALOG.md) and the cross-dimension entry point is [ops/INDEX.md](ops/INDEX.md)."),
    "zh": ("查找算子",
           "共有 **{total:,} 篇算子说明**(调用形式、类型契约、HALCON 对应、参考文献、"
           "来源)与 **{nguide} 篇族指南**。按维度的入口:",
           ("维度", "算子数", "入口"),
           "按名称检索用 `py -3.11 imgevolve.py ops --search edge`;"
           "全部算子的对照表见 [OP_CATALOG.md](OP_CATALOG.md)，跨维度入口见 [ops/INDEX.md](ops/INDEX.md)。"),
    "tw": ("尋找運算子",
           "共有 **{total:,} 篇運算子說明**(呼叫方式、型別契約、HALCON 對應、參考文獻、"
           "來源)與 **{nguide} 篇族群指南**。依維度的入口:",
           ("維度", "運算子數", "入口"),
           "依名稱搜尋請用 `py -3.11 imgevolve.py ops --search edge`;"
           "全部運算子的對照表見 [OP_CATALOG.md](OP_CATALOG.md)，跨維度入口見 [ops/INDEX.md](ops/INDEX.md)。"),
    "ko": ("연산자 찾기",
           "**{total:,}개의 연산자 노트**(호출 형식, 타입 계약, HALCON 대응, 참고문헌, "
           "출처)와 **{nguide}개의 패밀리 가이드**가 있습니다. 차원별 입구:",
           ("차원", "연산자 수", "입구"),
           "이름으로 찾으려면 `py -3.11 imgevolve.py ops --search edge`, "
           "전체 대응표는 [OP_CATALOG.md](OP_CATALOG.md), 차원을 가로지르는 입구는 [ops/INDEX.md](ops/INDEX.md)."),
    "de": ("Einen Operator finden",
           "**{total:,} Operator-Notizen** (Aufrufform, Typvertrag, HALCON-Pendant, "
           "Literatur, Provenienz) und **{nguide} Familien-Leitfäden**. "
           "Einstiegspunkte nach Dimension:",
           ("Dimension", "Ops", "Einstieg"),
           "Nach Namen suchen mit `py -3.11 imgevolve.py ops --search edge`; "
           "die vollständige Tabelle ist [OP_CATALOG.md](OP_CATALOG.md), der dimensionsübergreifende Einstieg [ops/INDEX.md](ops/INDEX.md)."),
}

#: 次元 → 短い説明(日本語のみ。他言語では次元名だけ出す)。
DIM_JA = {
    "2d": "進化する 2-D op(`fullseye.op.<名前>`)",
    "3d": "点群 / メッシュ / 体積 / SDF / 6-DoF",
    "optics": "レンズ・収差・光線追跡・照明設計",
    "annotate": "図注(軸・凡例・注記)",
    "reprconv": "表現の橋渡し(型と型のあいだ)",
    "gfx2d": "描画", "math": "数値・線形代数", "imgmetrics": "画質の指標",
    "piv": "粒子画像流速測定 + DIC", "blob": "2-D の連結成分解析",
    "dem": "地形", "acoustics": "音響", "quat": "四元数・単元信号",
    "photon": "光子計数 / dToF", "lightfield": "ライトフィールド",
    "tomography": "断層", "imgforensics": "改ざん検出",
    "shapestat": "形態統計", "videostream": "動画ストリーム",
    "astrostack": "天体スタック", "measure1d": "サブピクセル計測",
    "shape2d": "2-D の形の記述とワープ", "specular": "鏡面分離",
    "profile": "断面形状", "volcolor": "体積の色",
    "colortransport": "色の輸送", "interferometry": "干渉計",
    "motionmag": "モーション拡大", "rangedoppler": "FMCW レンジドップラー",
    "roughness": "表面粗さ", "cadmap": "CAD 対応づけ",
}


def _records():
    """★`opdocs` の一次情報。**見つからなければ落とす**。

    最初の版は ``OD.records() if hasattr(OD, "records") else None`` と書いて
    いた。実体の名前は ``_records`` なので ``hasattr`` はいつも False になり、
    **表が空・「0 本の op ノート」と書かれた索引が 6 言語ぶん公開された**。
    在るものを無いことにする fail-soft は、この repo が繰り返し踏んでいる形
    (`feedback_failsoft_hides_permanently_dead_ops`)。名前が変わったら
    AttributeError で落ちるほうが良い。
    """
    recs, _idx2d, _op_fam, _fam_ops = OD._records()
    assert recs, "opdocs._records() が空 —— 台帳が読めていない"
    return recs


def _rows():
    """[(dim, n_ops, guide_stem or None)] を大きい順で返す。"""
    out = []
    counts = {}
    for r in _records():
        counts[r["dim"]] = counts.get(r["dim"], 0) + 1
    for dim in sorted(counts, key=lambda d: (-counts[d], d)):
        fam = None
        meta = OD.LEDGER_DIMS.get(dim)
        if meta:
            g = os.path.join(_ROOT, "docs", "ops", dim, "guides",
                             meta["family"] + ".md")
            if os.path.exists(g):
                fam = meta["family"]
        out.append((dim, counts[dim], fam))
    return out


def _note_substance():
    """★ノートが**実際に中身か**を数える(2026-09-06、ユーザーの指摘
    「生成物が正しいのか確かめて、中身が空とかなってたら意味ない」)。

    それまでの検査は「生成物と commit 済みが一致するか」しか見ておらず、
    **生成器が空を吐いても両方が空で一致して緑**になった。構造(見出しや
    frontmatter)が揃っていることと、読んで役に立つことは別なので、
    分けて数える。

    返り値 (総数, 実行できる例が 1 本以上, 使い方が 120 字以上)。
    """
    import glob
    total = ex = use = 0
    base = os.path.join(_ROOT, "docs", "ops")
    for q in glob.glob(os.path.join(base, "**", "*.md"), recursive=True):
        qq = q.replace("\\", "/")
        if "/guides/" in qq or os.path.basename(q) in ("INDEX.md", "SAMPLES.md"):
            continue
        total += 1
        txt = io.open(q, encoding="utf-8").read()
        if "## 実行できる例" in txt:
            body = txt.split("## 実行できる例", 1)[1].split(chr(10) + "## ")[0]
            if "](../" in body:
                ex += 1
        if "## 使い方" in txt:
            body = txt.split("## 使い方", 1)[1].split(chr(10) + "## ")[0]
            if len(body.strip()) >= 120:
                use += 1
    return total, ex, use


def _honest(lang: str) -> str:
    """**網羅していないことを索引そのものに書く。** 数は毎回数え直す。

    2026-09-06 にユーザーから「全 op を網羅してない。」と指摘された。実測で
    ノートは進化 registry と型つき台帳をほぼ覆うが、**1 行ファサード
    ``fullseye.<名前>`` から見ると半分**しか無い(残りは補助関数・クラス・
    再輸出モジュールを含む)。数字を出さずに「全 op」と書かないこと。
    """
    import fullseye as fs
    import ops as _ops
    import typed_catalog as _tc

    # ★ノートの集合は**台帳から**取る(ファイルを数え上げない)。
    # 2026-09-06 の敵対的レビュー(Codex)で、ファイルを glob して stem を
    # 数える版が `docs/ops/SAMPLES.md`(op ノートではない)を 1 本混ぜており、
    # 索引は 1,842、RAG ガイドは 1,843 と**食い違う数を同時に公開**していた。
    # ノートは records から 1:1 で生成されるので、records の名前が「ノートの
    # ある名前」の定義そのもの。ファイルとの一致は
    # `tests/test_docs_index_reachable.py` が別に見る(消えた/余った を検出)。
    noted = {r["name"] for r in _records()}
    reg = {getattr(o, "name", str(o)) for o in _ops.REGISTRY}
    led = {r[0] for r in _tc.catalog()}
    fac = {n for n in dir(fs) if not n.startswith("_")}
    t = {"": "**網羅の実測**: 進化 op {r[1]}/{r[0]}、型つき台帳 {l[1]}/{l[0]}、"
             "1 行ファサード `fullseye.<名前>` {f[1]}/{f[0]}。"
             "**ファサード側はまだ半分**(残りは補助関数・クラス・再輸出モジュール)。",
         "en": "**Measured coverage**: evolvable ops {r[1]}/{r[0]}, typed ledger "
               "{l[1]}/{l[0]}, one-line facade `fullseye.<name>` {f[1]}/{f[0]} — "
               "**the facade is only half covered** (the rest are helpers, classes "
               "and re-exported modules).",
         "zh": "**实测覆盖**: 演化算子 {r[1]}/{r[0]}、类型化台账 {l[1]}/{l[0]}、"
               "单行门面 `fullseye.<名称>` {f[1]}/{f[0]} —— **门面侧仅覆盖一半**。",
         "tw": "**實測涵蓋**: 演化運算子 {r[1]}/{r[0]}、型別台帳 {l[1]}/{l[0]}、"
               "單行門面 `fullseye.<名稱>` {f[1]}/{f[0]} —— **門面側僅涵蓋一半**。",
         "ko": "**실측 커버리지**: 진화 연산자 {r[1]}/{r[0]}, 타입 台帳 {l[1]}/{l[0]}, "
               "한 줄 파사드 `fullseye.<이름>` {f[1]}/{f[0]} — **파사드는 아직 절반**.",
         "de": "**Gemessene Abdeckung**: evolvierbare Ops {r[1]}/{r[0]}, typisiertes "
               "Ledger {l[1]}/{l[0]}, Fassade `fullseye.<name>` {f[1]}/{f[0]} — "
               "**die Fassade ist erst zur Hälfte abgedeckt**."}
    n, ex, use = _note_substance()
    sub = {"": "**ノートの中身の実測**: %d 本のうち、実行できる例が付いているのは "
               "**%d 本**(%d 本は例ゼロ)、使い方の説明が 120 字以上あるのは "
               "**%d 本**(%d 本は 1 行の要約だけ)。構造(呼び出し・型・"
               "次に繋がる op)は %d 本すべてにある。",
           "en": "**Measured substance**: of %d notes, **%d** link at least one "
                 "runnable example (%d have none) and **%d** have a usage section "
                 "of 120+ characters (%d are a one-line summary). The structure "
                 "(call form, types, ops that chain next) is present in all %d.",
           "zh": "**内容实测**: %d 篇中，附有可运行示例的 **%d** 篇(%d 篇没有)，"
                 "用法说明 120 字以上的 **%d** 篇(%d 篇仅一行)。"
                 "结构(调用形式、类型、可衔接算子)%d 篇全有。",
           "tw": "**內容實測**: %d 篇中，附有可執行範例的 **%d** 篇(%d 篇沒有)，"
                 "用法說明 120 字以上的 **%d** 篇(%d 篇僅一行)。"
                 "結構(呼叫形式、型別、可銜接運算子)%d 篇全有。",
           "ko": "**내용 실측**: %d건 중 실행 가능한 예제가 붙은 것은 **%d**건"
                 "(%d건은 없음), 사용법이 120자 이상인 것은 **%d**건"
                 "(%d건은 한 줄 요약). 구조(호출 형식·타입·다음 연산자)는 %d건 모두.",
           "de": "**Gemessener Inhalt**: von %d Notizen verweisen **%d** auf "
                 "mindestens ein lauffähiges Beispiel (%d ohne), **%d** haben einen "
                 "Nutzungsabschnitt ab 120 Zeichen (%d nur eine Zeile). Die Struktur "
                 "(Aufrufform, Typen, anschließbare Ops) haben alle %d."}
    line = t[lang].format(r=(len(reg), len(reg & noted)),
                          l=(len(led), len(led & noted)),
                          f=(len(fac), len(fac & noted)))
    return line + chr(10) + chr(10) + (sub[lang] % (n, ex, n - ex, use, n - use, n))


#: ★索引は人だけでなく **AI の検索面**でもある(2026-09-06 のユーザーの指摘
#: 「索引って RAG としても使われる部分だよね?」)。op ノートは AI コーディング
#: 支援の検索コーパスを兼ねるので、**機械が読む入口**を索引に明示する。
#: 半分しか無いものを「全 op」と書くと、RAG は残り半分について自信満々に
#: 間違える —— だから `_honest()` の実測行はこの節から外さない。
RAG_L10N = {
    "": "**AI から引くなら**: 機械可読の索引 [`OP_INDEX.json`](OP_INDEX.json)、"
        "使い方は [AI_RAG_GUIDE.md](AI_RAG_GUIDE.md)"
        "(`pip install fullseye[rag]` → `fullseye-rag search \"エッジ\"`、"
        "Claude Code なら `py -3.11 tools/setup_claude_rag.py`)。",
    "en": "**Retrieving from an AI assistant**: the machine-readable index is "
          "[`OP_INDEX.json`](OP_INDEX.json); how to use it is in "
          "[AI_RAG_GUIDE.md](AI_RAG_GUIDE.md) "
          "(`pip install fullseye[rag]`, then `fullseye-rag search \"edge\"`).",
    "zh": "**供 AI 检索**: 机器可读索引 [`OP_INDEX.json`](OP_INDEX.json)，"
          "用法见 [AI_RAG_GUIDE.md](AI_RAG_GUIDE.md)。",
    "tw": "**供 AI 檢索**: 機器可讀索引 [`OP_INDEX.json`](OP_INDEX.json)，"
          "用法見 [AI_RAG_GUIDE.md](AI_RAG_GUIDE.md)。",
    "ko": "**AI 검색용**: 기계가 읽는 색인 [`OP_INDEX.json`](OP_INDEX.json), "
          "사용법은 [AI_RAG_GUIDE.md](AI_RAG_GUIDE.md).",
    "de": "**Abruf durch KI-Assistenten**: der maschinenlesbare Index ist "
          "[`OP_INDEX.json`](OP_INDEX.json), die Anleitung steht in "
          "[AI_RAG_GUIDE.md](AI_RAG_GUIDE.md).",
}


def build(lang: str = "") -> str:
    title, intro, cols, tail = L10N[lang]
    rows = _rows()
    total = sum(n for _, n, _ in rows)
    nguide = _nguide()
    out = [START, "", "## " + title, "",
           intro.format(total=total, nguide=nguide), "",
           _honest(lang), "",
           "| %s | %s | %s |" % cols, "|---|---:|---|"]
    for dim, n, fam in rows:
        entry = "[INDEX](ops/%s/INDEX.md)" % dim
        if fam:
            entry += " · [%s](ops/%s/guides/%s.md)" % (
                "ガイド" if lang == "" else "guide", dim, fam)
        note = (" — " + DIM_JA[dim]) if (lang == "" and dim in DIM_JA) else ""
        out.append("| `%s`%s | %d | %s |" % (dim, note, n, entry))
    out += ["", tail, "", RAG_L10N[lang], "", END]
    return chr(10).join(out)



# --------------------------------------------------------------------------- #
# ドキュメント地図 —— 索引から 1 本も辿れない文書を作らない                       #
# --------------------------------------------------------------------------- #
DSTART, DEND = "<!-- docmap:start -->", "<!-- docmap:end -->"

#: 主題 -> (キー, 日本語見出し, 英語見出し, そこに置く文書)。**順序が表示順**。
#: 新しい文書はここに足す。足し忘れても「そのほか」に必ず出るので消えない。
DOC_GROUPS = [
    ("start", "はじめに・使い方", "Getting started", [
        "GETTING_STARTED.md", "INSTALL.md", "STUDIO_GUIDE.md", "STUDIO_UX.md",
        "EXAMPLES.md", "EXAMPLES_3D.md", "GALLERY.md", "REPRODUCE.md",
        "CONSUMER_APPLICATIONS.md", "3DGS_USAGE.md", "TERRAIN_WALK.md",
        "GSPLAT_NATIVE_WINDOWS.md"]),
    ("ref", "オペレータのリファレンス", "Operator reference", [
        "OPERATORS.md", "OP_CATALOG.md", "OP_COMBINATION_MATRIX.md",
        "CONVERSION_MATRIX.md", "CONNECTIVITY.md", "MATCH_3D_MATRIX.md",
        "GENERAL_ALGORITHMS.md", "ADDING_OPS.md", "WAVE0_STABLE_SLOTS.md"]),
    ("rag", "AI から引く(RAG)", "Retrieval for AI assistants", [
        "AI_RAG_GUIDE.md"]),
    ("perception", "知覚・センサ", "Perception and sensors", [
        "PERCEPTION.md", "PERCEPTION_PHYSICAL_AI.md", "PERCEPTION_REALDATA.md",
        "SENSOR_PLAYBOOK.md", "HIGHSPEED_VISION.md",
        "SAMPLE_IMAGE_REFERENCES.md"]),
    ("halcon", "HALCON との対応", "HALCON correspondence", [
        "HALCON_PARITY.md", "HALCON_COVERAGE.md", "HALCON_COVERAGE_HONEST.md",
        "HDEVELOP_FIDELITY.md", "HDEVELOP_DEV_OPS.md", "LIB_COVERAGE.md"]),
    ("fscript", "Fullseye Script", "Fullseye Script", [
        "FSCRIPT_DECISION.md", "FSCRIPT_LANGUAGE.md", "FSCRIPT_MEASUREMENTS.md"]),
    ("quality", "品質・正直さ", "Quality and honesty", [
        "KNOWN_ISSUES.md", "STATUS.md", "ACCURACY_BENCH.md", "BENCH_VS_OPENCV.md",
        "PARITY_CROSSBACKEND.md", "CHAIN_FUZZ.md", "PROVENANCE.md",
        "REFERENCES.md", "AUDIT_2026_08_12.md", "RELEASE_CHECKLIST.md",
        "I18N.md"]),
    ("perf", "性能・GPU", "Performance and GPU", [
        "GPU_ACCEL_PLAN.md", "GPU_OPTIMIZATION_PATTERNS.md",
        "design/FAST_TWINS.md", "design/PERF_MEMORY_VIDEO_SURVEY.md"]),
    ("design", "設計・アーキテクチャ", "Design and architecture", [
        "ENGINE.md", "EVOLUTION_ENVIRONMENT.md", "INTEGRATION.md",
        "UNIFIED_API_REQUIREMENTS.md", "design/TRIZ_DESIGN_PATTERN_MATRIX.md",
        "EVIS_VISION_OSS_GAP.md", "INDUSTRY_SIGNALS.md"]),
    ("history", "作業記録・計画(履歴。**その日付時点の値**で、いまの値ではない)",
     "Working notes and plans (historical; numbers are as of their date)", [
        "V13.md", "V14.md", "SESSION_SUMMARY.md", "SESSION_2026_08_14.md",
        "STUDIO_REVIEW_2026_08_14.md", "NEXT_SESSION.md",
        "NEXT_OPS_PLAN_2026-08-31.md", "PLAN_0_1_9.md",
        "ARTICLE_INTEGRATION_TODO.md", "ARTICLE_RESTRUCTURE_PLAN.md",
        "ARTICLE_GPU_SHAPEMATCH.md", "FULLSEYE_OP_ARTICLE_SPEC.md"]),
]

DOC_L10N = {
    "": ("ドキュメント地図 — 全 {n} 本",
         "**索引から 1 本も辿れない文書を作らない**ための全体地図です"
         "(`docs/ops/` の op ノート {nops:,} 本と族ガイド {nguide} 本は上の"
         "「オペレータを探す」から、記事は [articles/](articles/README.md) から"
         "辿れます)。到達できない文書が 1 本でもあれば "
         "`tests/test_docs_index_reachable.py` が落ちます。"
         "**本文はほとんどが日本語**です。", ("文書", "内容")),
    "en": ("Document map — all {n}",
           "The complete map, so that **no document is unreachable from this "
           "index** (the {nops:,} per-op notes and {nguide} family guides under "
           "`docs/ops/` are reached from the operator section above; articles "
           "from [articles/](articles/README.md)). One unreachable file fails "
           "`tests/test_docs_index_reachable.py`. **Most bodies are in "
           "Japanese.**", ("document", "what it covers")),
    "zh": ("文档地图 — 共 {n} 篇",
           "完整地图，确保**没有任何文档无法从索引到达**(`docs/ops/` 下的 {nops:,} 篇"
           "算子说明与 {nguide} 篇族群指南从上面的「查找算子」进入; 文章见 "
           "[articles/](articles/README.md))。**正文多为日语。**",
           ("文档", "内容")),
    "tw": ("文件地圖 — 共 {n} 篇",
           "完整地圖，確保**沒有任何文件無法從索引到達**(`docs/ops/` 下的 {nops:,} 篇"
           "運算子說明與 {nguide} 篇族群指南從上面的「尋找運算子」進入; 文章見 "
           "[articles/](articles/README.md))。**內文多為日文。**",
           ("文件", "內容")),
    "ko": ("문서 지도 — 전 {n}건",
           "**색인에서 닿지 않는 문서를 만들지 않기** 위한 전체 지도입니다"
           "(`docs/ops/`의 연산자 노트 {nops:,}건과 패밀리 가이드 {nguide}건은 위의 "
           "「연산자 찾기」에서, 기사는 [articles/](articles/README.md)에서). "
           "**본문은 대부분 일본어입니다.**", ("문서", "내용")),
    "de": ("Dokumentkarte — alle {n}",
           "Die vollständige Karte, damit **kein Dokument vom Index aus "
           "unerreichbar ist** (die {nops:,} Operator-Notizen und {nguide} "
           "Familien-Leitfäden unter `docs/ops/` über den Operator-Abschnitt "
           "oben; Artikel über [articles/](articles/README.md)). **Die Texte "
           "sind überwiegend japanisch.**", ("Dokument", "Inhalt")),
}


def _doc_title(rel: str) -> str:
    """先頭の `# 見出し` を 1 行の説明として使う。無ければ最初の本文行。"""
    path = os.path.join(_ROOT, "docs", rel)
    with io.open(path, encoding="utf-8") as f:
        for line in f:
            t = line.strip()
            if t.startswith("# "):
                t = t[2:].strip()
            elif (not t) or t.startswith(("<!--", "---", "!", "[", "#")):
                continue
            t = t.replace("|", "/")
            return t if len(t) <= 150 else t[:147] + "..."
    return ""


#: 地図から外す部分木。**それぞれ専用の節が面倒を見る**もの以外は外さない。
_DOCMAP_SKIP = ("ops", "articles")


def _all_docs() -> list:
    """`docs/` 以下の md を**再帰で**すべて(README* と ops/ articles/ を除く)。

    最初の版は「直下」と `design/` の 2 階層だけを見ていた(Codex の敵対的
    レビュー、2026-09-06)。新しく `docs/howto/` を切ったら地図から丸ごと
    落ちるうえ、地図の検査もこの同じ関数を見ていたので**検査は緑のまま**に
    なる。深さを決め打ちせず、外す部分木のほうを明示する。
    """
    base = os.path.join(_ROOT, "docs")
    out = []
    for root, dirs, files in os.walk(base):
        rel_root = os.path.relpath(root, base).replace(os.sep, "/")
        if rel_root == ".":
            dirs[:] = [d for d in dirs if d not in _DOCMAP_SKIP]
        dirs.sort()
        for f in sorted(files):
            if not f.endswith(".md") or f.startswith("README"):
                continue
            rel = f if rel_root == "." else rel_root + "/" + f
            out.append(rel)
    return sorted(out)


def _nguide() -> int:
    """族ガイドの本数。**`*.md` だけ数える**。

    最初の版は `len(os.listdir(guides))` で、隠しファイルや画像や一時ファイルが
    あればそのぶん「ガイドが N 本あります」と水増しされた(Codex の敵対的
    レビュー、2026-09-06)。いまは 0 本だが、数える対象は明示しておく。
    """
    base = os.path.join(_ROOT, "docs", "ops")
    n = 0
    for d in sorted(os.listdir(base)):
        g = os.path.join(base, d, "guides")
        if os.path.isdir(g):
            n += len([f for f in os.listdir(g) if f.endswith(".md")])
    return n


def build_docmap(lang: str = "") -> str:
    title, intro, cols = DOC_L10N[lang]
    have = _all_docs()
    assigned, groups = set(), []
    for _key, ja, en, names in DOC_GROUPS:
        gone = [n for n in names if n not in have]
        assert not gone, (
            "DOC_GROUPS に書いてある文書が見つからない(消えた? 改名した?): %s "
            "—— tools/gen_docs_index_ops.py の DOC_GROUPS を直すこと" % gone)
        assigned.update(names)
        groups.append((ja if lang == "" else en, list(names)))
    rest = [n for n in have if n not in assigned]
    if rest:
        groups.append(("そのほか" if lang == "" else "Other", rest))

    out = [DSTART, "", "## " + title.format(n=len(have)), "",
           intro.format(nops=len(_records()), nguide=_nguide()), ""]
    for head, rows in groups:
        if not rows:
            continue
        out.append("**%s**(%d)" % (head, len(rows)))
        out.append("")
        out.append("| %s | %s |" % cols)
        out.append("|---|---|")
        for n in rows:
            out.append("| [`%s`](%s) | %s |" % (n, n, _doc_title(n)))
        out.append("")
    out.append(DEND)
    return chr(10).join(out)


# --------------------------------------------------------------------------- #
# 記事の棚 —— docs/articles/ 以下を 1 本残らず並べる                             #
# --------------------------------------------------------------------------- #
ASTART, AEND = "<!-- articles:start -->", "<!-- articles:end -->"


def _article_rows():
    """docs/articles 以下の md を (グループ, 相対パス) で返す。README 自身は除く。"""
    base = os.path.join(_ROOT, "docs", "articles")
    rows = []
    for root, dirs, files in os.walk(base):
        dirs.sort()   # ★os.walk の並びは OS 依存(Linux CI だけドリフト門が落ちる)
        for f in sorted(files):
            if not f.endswith(".md"):
                continue
            rel = os.path.relpath(os.path.join(root, f), base).replace("\\", "/")
            if rel == "README.md":   # 書き込み先だけ除く(exhibits/README は載せる)
                continue
            if rel.startswith("exhibits/"):
                grp = "exhibits"
            elif rel.startswith("assets/"):
                grp = "assets"
            else:
                grp = "articles"
            rows.append((grp, rel))
    rows.sort()       # 念のため最終順序も固定する
    return rows


ART_HEAD = {
    "articles": ("記事", "記事本文。長文の原稿はここが正本で、Qiita などへは"
                 "ここから出す。"),
    "exhibits": ("展示(exhibits)", "記事の「紙面の科学館」章の単一真実源。"
                 "`<id>.ja.md` / `<id>.en.md` の 2 枚組で、本文は "
                 "`tools/build_exhibits.py` が組み立てる。"),
    "assets": ("図版まわりの資料", "図版の出典表記と、記事へ差し込む断片"
               "(`_*_snippet.md`)。断片は生成物で、手で編集しない。"),
}


def build_articles() -> str:
    rows = _article_rows()
    out = [ASTART, "",
           "## この下にあるもの(全 %d 本 —— 生成)" % len(rows), "",
           "`py -3.11 tools/gen_docs_index_ops.py` が "
           "`docs/articles/` を歩いて作ります。**ここから辿れない文書を作らない**"
           "ための一覧なので、手で足し引きしないでください。", ""]
    for key in ("articles", "exhibits", "assets"):
        got = [r for g, r in rows if g == key]
        if not got:
            continue
        head, note = ART_HEAD[key]
        out += ["**%s**(%d) —— %s" % (head, len(got), note), "",
                "| ファイル | 見出し |", "|---|---|"]
        for rel in got:
            out.append("| [`%s`](%s) | %s |" % (rel, rel, _articles_title(rel)))
        out.append("")
    out.append(AEND)
    return chr(10).join(out)


def _articles_title(rel: str) -> str:
    path = os.path.join(_ROOT, "docs", "articles", rel)
    with io.open(path, encoding="utf-8") as f:
        for line in f:
            t = line.strip()
            if t.startswith("#"):
                t = t.lstrip("#").strip()
            elif (not t) or t.startswith(("<!--", "---", "!", "[")):
                continue
            t = t.replace("|", "/")
            return t if len(t) <= 120 else t[:117] + "..."
    return ""


def write_articles() -> None:
    p = os.path.join(_ROOT, "docs", "articles", "README.md")
    s = io.open(p, encoding="utf-8").read()
    block = build_articles()
    if ASTART in s and AEND in s:
        head, rest = s.split(ASTART, 1)
        s = head + block + rest.split(AEND, 1)[1]
    else:
        s = s.rstrip() + chr(10) * 2 + block + chr(10)
    io.open(p, "w", encoding="utf-8", newline=chr(10)).write(s)
    print("wrote articles listing -> docs/articles/README.md")

def main() -> int:
    for lang in L10N:
        name = "README.md" if not lang else "README.%s.md" % lang
        p = os.path.join(_ROOT, "docs", name)
        s = io.open(p, encoding="utf-8").read()
        block = build(lang)
        pblock = build_poc(lang)
        if PSTART in s and PEND in s:
            h2, r2 = s.split(PSTART, 1)
            s = h2 + pblock + r2.split(PEND, 1)[1]
        else:
            sep = chr(10) + "---" + chr(10)
            i2 = s.index(sep) + len(sep)
            s = s[:i2] + chr(10) + pblock + chr(10) + s[i2:]
        if START in s and END in s:
            head, rest = s.split(START, 1)
            s = head + block + rest.split(END, 1)[1]
        else:
            # 「使い方」表の直前(最初の `---` の後)へ入れる
            i = s.index("\n---\n") + len("\n---\n")
            s = s[:i] + "\n" + block + "\n" + s[i:]
        dblock = build_docmap(lang)
        if DSTART in s and DEND in s:
            h3, r3 = s.split(DSTART, 1)
            s = h3 + dblock + r3.split(DEND, 1)[1]
        else:
            s = s.rstrip() + chr(10) * 2 + dblock + chr(10)
        io.open(p, "w", encoding="utf-8", newline=chr(10)).write(s)
        print("wrote ops+poc+docmap ->", name)
    write_articles()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
