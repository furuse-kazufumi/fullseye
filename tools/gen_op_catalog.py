# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gen_op_catalog — Fullseye の全 op を LLM に渡せる markdown 台帳(OP_CATALOG.md)に出力。

    py -3.11 tools/gen_op_catalog.py [--out docs/OP_CATALOG.md]

目的: op が増えたので、用途を伝えれば **どの op をどう組み合わせるか AI が提案できる**
一枚の台帳を作る。人にも読めるが、第一の読者は LLM。内容:
    1. AI 向けの使い方(用途→パイプライン提案の手順)。
    2. worked examples(用途→使う op)= 実際の組合せの手本。
    3. スタンドアロン幾何/数学モジュールの関数 API(署名+一行説明)。
    4. 全 op を族(``docs/ops/<族>/``)→ カテゴリの順に(in→out・要約・HALCON 別名・例)。
       母集団は op ノートと同じ ``tools/opdocs._records``(48 族)。
    5. 参照(アルゴリズムの一次情報・further reading の URL)。

設計: 補助の節(例・単体モジュール・参照)は try/except で囲み、1 つの失敗が台帳全体を
壊さない(壊れた項目は "(introspection failed)" と明示し、握り潰さない)。**op の一覧の節だけは
fail-closed** —— そこが空なら台帳の意味が無い。

★言語版(2026-11-06、1.0.0 の文書の門): 日本語の ``OP_CATALOG.md`` に加えて英語版
``OP_CATALOG.en.md`` と简体中文版 ``OP_CATALOG.zh.md`` を書く(``docs/`` と同梱の ``fullseye/`` の両方)。

* op の要約は ``docs/i18n/op_summary.json``(``tools/opdocs.op_summary`` —— 原文の指紋が合う訳だけ)。
* 単体モジュールの docstring 先頭行は ``docs/i18n/op_catalog.json``(同じく指紋つき)。
* 枠の文(見出し・手順・族の一言・GPU の語など)はこのファイルの :data:`_TR`(**キーは日本語の原文**。
  原文を書き換えるとキーが外れて訳が無くなる = 古い訳が黙って残らない)。
* **訳が無い・指紋が古い行が 1 本でもあれば、en / zh を書かずに止まる**(:class:`CatalogTranslationError`)。
  黙って日本語に落とすと「英語版」に日本語が混ざり、読み手はそれを訳だと思って読む。
* worked examples の題と説明は日本語でしか書かれていない(474 + 124 例、約 25 万字)。訳した
  ふりをせず、言語版では **例の id・その例が呼ぶ op・起動コマンド**だけを並べ、その旨を節の冒頭に書く。
"""
from __future__ import annotations

import argparse
import inspect
import json
import os
import re
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

#: 書く言語。``ja`` が原文。
LANGS = ("ja", "en", "zh")

#: 単体モジュールの docstring 先頭行の対訳表(``tools/opdocs.fingerprint`` の指紋つき)。
CATALOG_I18N_PATH = os.path.join(_REPO, "docs", "i18n", "op_catalog.json")


class CatalogTranslationError(RuntimeError):
    """言語版に必要な訳が無い・古い。**補助の節の try/except でも握り潰さない**。"""


# op -> worked-example index (HDevelop-style "この op を使うサンプル"リンク)。壊れても台帳は出す。
_EX3D, _EX2D = None, None


def _ex_index():
    global _EX3D, _EX2D
    if _EX3D is None:
        try:
            from op_example_index import build_index
            _EX3D, _EX2D = build_index(split=True)
        except Exception:
            _EX3D, _EX2D = {}, {}
    return _EX3D, _EX2D


# --------------------------------------------------------------------------- #
# 枠の文言の対訳(キー = 日本語の原文)                                        #
# --------------------------------------------------------------------------- #
#: 日本語の原文 -> {"en": …, "zh": …}。``{n}`` などの差し込みは訳の側でも同じ名前で使う。
_TR: dict[str, dict[str, str]] = {
    # ---- 冒頭 ----
    ("Fullseye は説明可能な古典/幾何ビジョンの Physical-AI ツールキット。この台帳は "
     "**用途を伝えれば、どの op をどう組み合わせればよいかを AI が提案する**ための一覧です。"): {
        "en": ("Fullseye is a Physical-AI toolkit for explainable classical / geometric vision. This ledger "
               "is the list from which **an AI, once told the use case, proposes which ops to combine and how**."),
        "zh": ("Fullseye 是一个可解释的经典/几何视觉 Physical-AI 工具包。本台账是一份清单，"
               "**只要告知用途，AI 就能据此提出该组合哪些 op、如何组合**。")},
    "## この台帳の使い方(assistant 向け)": {
        "en": "## How to use this ledger (for assistants)",
        "zh": "## 本台账的使用方法(面向 assistant)"},
    "1. ユーザーの**用途(入力データ・欲しい出力)**を特定する。": {
        "en": "1. Identify the user's **use case (input data, desired output)**.",
        "zh": "1. 确定用户的**用途(输入数据、想要的输出)**。"},
    "2. まず **Worked examples**(用途→op の実例)から最も近いものを探し、その op 連鎖を土台にする。": {
        "en": ("2. First find the closest entry in **Worked examples** (use case → ops, real instances) "
               "and take its op chain as the base."),
        "zh": "2. 先在 **Worked examples**(用途→op 的实例)中找到最接近的一个，以其 op 链为基础。"},
    ("3. 連鎖は **in → out のデータ種**が繋がるように組む(例: `image → region → feature`、"
     "`points → voxel → mesh`)。2D パイプライン op は 1 画像+2 スカラつまみのモデル、"
     "点群/体積の 3D op と 2 画像を取る op(morph 等)は関数として呼ぶ。"): {
        "en": ("3. Build the chain so that the **in → out data kinds** connect (e.g. `image → region → feature`, "
               "`points → voxel → mesh`). 2-D pipeline ops follow the model of one image plus two scalar knobs; "
               "3-D point-cloud / volume ops and ops that take two images (morph etc.) are called as functions."),
        "zh": ("3. 组链时让 **in → out 的数据种类**首尾相接(例: `image → region → feature`、"
               "`points → voxel → mesh`)。2D 流水线 op 采用“1 幅图像 + 2 个标量旋钮”的模型；"
               "点云/体数据的 3D op 以及取 2 幅图像的 op(morph 等)作为函数调用。")},
    "4. 各 op の**前提と失敗条件**(退化入力・必要点数など)を必ず確認し、fail-closed に扱う。": {
        "en": ("4. Always check each op's **preconditions and failure conditions** (degenerate input, "
               "required number of points, etc.) and handle them fail-closed."),
        "zh": "4. 务必确认每个 op 的**前提与失败条件**(退化输入、所需点数等)，并按 fail-closed 处理。"},
    "5. 提案には**具体的な op 名**と、可能なら該当する worked example / References を添える。": {
        "en": ("5. Name **concrete ops** in the proposal and, where possible, attach the matching "
               "worked example / References."),
        "zh": "5. 提案中给出**具体的 op 名**，并尽可能附上对应的 worked example / References。"},
    "6. 実装が不確かなら、対応する `examples*/` を実行して ground-truth 出力で確かめる。": {
        "en": ("6. If you are unsure about the implementation, run the corresponding `examples*/` and check "
               "against its ground-truth output."),
        "zh": "6. 若对实现没有把握，运行对应的 `examples*/`，用 ground-truth 输出加以确认。"},
    # ---- worked examples ----
    "## Worked examples(用途 → 使う op の実例=推奨組合せの手本)": {
        "en": "## Worked examples (use case → the ops used; real instances = models for recommended combinations)",
        "zh": "## Worked examples(用途 → 所用 op 的实例 = 推荐组合的范例)"},
    "2-D 画像/信号/幾何": {"en": "2-D image / signal / geometry", "zh": "2-D 图像/信号/几何"},
    "3-D 点群/体積/曲面": {"en": "3-D point cloud / volume / surface", "zh": "3-D 点云/体数据/曲面"},
    "### {label}({n} 例)": {"en": "### {label} ({n} examples)", "zh": "### {label}({n} 例)"},
    "- (catalog: {mod} を読めませんでした: {e})": {
        "en": "- (catalog: could not read {mod}: {e})", "zh": "- (catalog: 无法读取 {mod}: {e})"},
    "_examples_note": {
        "en": ("_The titles and descriptions of the worked examples are written in Japanese only. Rather than "
               "pass them off as translated, this edition lists each example by its id, the ops it calls "
               "(from the example links of the op notes; at most {k}, the rest as a count) and the command "
               "that runs it. The descriptions are in the Japanese catalogue `OP_CATALOG.md`._"),
        "zh": ("_Worked examples 的标题与说明只有日文。本版不假装已翻译，只按 id 列出每个示例、"
               "它调用的 op(取自 op 笔记中的示例链接；最多 {k} 个，其余只给个数)以及运行它的命令。"
               "说明见日文版目录 `OP_CATALOG.md`。_")},
    "_examples_ops": {"en": "ops: {ops}", "zh": "op: {ops}"},
    "_examples_more": {"en": " (+{n} more)", "zh": "(另有 {n} 个)"},
    "_examples_noops": {"en": "ops: (not linked from any op note)", "zh": "op:(没有 op 笔记链接到此例)"},
    # ---- 単体モジュール ----
    "## スタンドアロン幾何/数学モジュール(関数 API)": {
        "en": "## Standalone geometry / math modules (function API)",
        "zh": "## 独立的几何/数学模块(函数 API)"},
    "1画像パイプラインに乗らない op(2画像・点列・可変引数)。関数として呼ぶ。": {
        "en": ("Ops that do not fit the one-image pipeline (two images, point sequences, variable arguments). "
               "Call them as functions."),
        "zh": "不适用于单图像流水线的 op(2 幅图像、点列、可变参数)。作为函数调用。"},
    "- (import 失敗: {e})": {"en": "- (import failed: {e})", "zh": "- (import 失败: {e})"},
    # ---- 族 → カテゴリ ----
    "## Operators by family(族 → カテゴリ、全 op)": {
        "en": "## Operators by family (family → category, all ops)",
        "zh": "## Operators by family(族 → 类别，全部 op)"},
    ("_計 {n} ops / {m} families。並びとノートの在り処は `docs/ops/INDEX.md` と同じ"
     "(ノート = `docs/ops/<族>/<カテゴリ>/<op>.md`)。台帳族の op は `fs.ledger.<op>` で呼ぶ。_"): {
        "en": ("_{n} ops / {m} families in total. The order and the location of the notes are the same as "
               "`docs/ops/INDEX.md` (note = `docs/ops/<family>/<category>/<op>.md`). "
               "Ops of the ledger families are called as `fs.ledger.<op>`._"),
        "zh": ("_共 {n} ops / {m} families。排列顺序与笔记位置同 `docs/ops/INDEX.md`"
               "(笔记 = `docs/ops/<族>/<类别>/<op>.md`)。台账族的 op 用 `fs.ledger.<op>` 调用。_")},
    "族の一覧: ": {"en": "Families: ", "zh": "族一览: "},
    "入力なし": {"en": "no input", "zh": "无输入"},
    " · 例: ": {"en": " · examples: ", "zh": " · 示例: "},
    " · 例: なし": {"en": " · examples: none", "zh": " · 示例: 无"},
    # GPU の語(tools/opdocs.gpu_status_text の出力。対訳の語はノートの GPU 行 = docs/i18n/opdocs.json に揃える)
    "なし": {"en": "none", "zh": "无"},
    "あり(許可リスト)": {"en": "yes (allow-list)", "zh": "有(许可列表)"},
    "鎖の中だけ(許可リスト)": {"en": "inside a chain only (allow-list)", "zh": "仅在链中(许可列表)"},
    "native(device 引数)": {"en": "native (device argument)", "zh": "native(device 参数)"},
    "native(device 引数、鎖の中だけ)": {"en": "native (device argument, inside a chain only)",
                                       "zh": "native(device 参数，仅在链中)"},
    "あり({a})": {"en": "yes ({a})", "zh": "有({a})"},
    "鎖の中だけ({a})": {"en": "inside a chain only ({a})", "zh": "仅在链中({a})"},
    # ---- 参照 ----
    "## References(アルゴリズムの一次情報・further reading)": {
        "en": "## References (primary sources for the algorithms, further reading)",
        "zh": "## References(算法的一手资料、further reading)"},
    "各 op の原理はモジュール docstring にも一次文献名を明記。以下は主要技術族の外部参照。": {
        "en": ("Each op's module docstring also names the primary literature for its principle. "
               "Below are external references for the main technique families."),
        "zh": "各 op 的原理也在模块 docstring 中注明了一手文献名。以下为主要技术族的外部参考。"},
    "Thin plate spline(TPS 変形)": {"en": "Thin plate spline (TPS deformation)",
                                     "zh": "Thin plate spline(TPS 变形)"},
    "Perspective-n-Point(PnP 姿勢)": {"en": "Perspective-n-Point (PnP pose)",
                                       "zh": "Perspective-n-Point(PnP 位姿)"},
    "RANSAC(ロバスト推定)": {"en": "RANSAC (robust estimation)", "zh": "RANSAC(鲁棒估计)"},
    "Geodesic(距離)": {"en": "Geodesic (distance)", "zh": "Geodesic(距离)"},
}


def _t(s: str, lang: str) -> str:
    """枠の文言 ``s``(日本語の原文)を ``lang`` へ。訳が無ければ :class:`CatalogTranslationError`。"""
    if lang == "ja":
        return s
    tr = (_TR.get(s) or {}).get(lang)
    if not tr:
        raise CatalogTranslationError(
            "gen_op_catalog: 枠の文言に %s の訳が無い(_TR に足す): %r" % (lang, s[:80]))
    return tr


def _has_ja(text: str) -> bool:
    """かな・漢字・全角記号を含むか(``tools/opdocs.has_japanese`` と同じ判定)。"""
    return bool(re.search(r"[぀-ヿ㐀-鿿＀-￯]", text or ""))


def _gpu_text(status: str, lang: str) -> str:
    """``gpu_status_text`` の日本語の語を ``lang`` へ。知らない形は止める(黙って日本語を出さない)。"""
    if lang == "ja":
        return status
    if status in _TR:
        return _t(status, lang)
    m = re.fullmatch(r"(あり|鎖の中だけ)\((.+)\)", status)
    if m and not _has_ja(m.group(2)):
        return _t(m.group(1) + "({a})", lang).format(a=m.group(2))
    raise CatalogTranslationError("gen_op_catalog: GPU の語 %r の %s 訳が無い(_TR に足す)" % (status, lang))


_CATALOG_I18N = None


def _catalog_i18n() -> dict:
    global _CATALOG_I18N
    if _CATALOG_I18N is None:
        try:
            with open(CATALOG_I18N_PATH, encoding="utf-8") as f:
                _CATALOG_I18N = json.load(f).get("lines", {}) or {}
        except FileNotFoundError:
            _CATALOG_I18N = {}
    return _CATALOG_I18N


def _doc_line_tr(key: str, src: str, lang: str, missing: list) -> str:
    """単体モジュールの docstring 先頭行 ``src`` を ``lang`` へ(``op_catalog.json``、指紋が合うときだけ)。"""
    if lang == "ja" or not src:
        return src
    if lang == "en" and not _has_ja(src):
        return src                                      # もともと英語
    sys.path.insert(0, os.path.join(_REPO, "tools"))
    import opdocs as OD
    ent = _catalog_i18n().get(key) or {}
    tr = (ent.get(lang) or "").strip()
    if ent.get("fp") != OD.fingerprint(src) or not tr:
        missing.append("op_catalog.json:%s(%s)" % (key, "stale" if tr else "no " + lang))
        return src
    return tr


def _ex_link(exs, lang: str = "ja") -> str:
    """例 id のリストを ' · 例: `a`, `b`'(無ければ ' · 例: なし')に整形。"""
    if exs:
        return _t(" · 例: ", lang) + ", ".join(f"`{e}`" for e in exs)
    return _t(" · 例: なし", lang)


def _doc1(obj) -> str:
    """オブジェクトの docstring 先頭行(無ければ空文字)。"""
    try:
        d = (inspect.getdoc(obj) or "").strip()
        return d.splitlines()[0].strip() if d else ""
    except Exception:
        return ""


def _sig(fn) -> str:
    try:
        return str(inspect.signature(fn))
    except (TypeError, ValueError):
        return "(...)"


# --------------------------------------------------------------------------- #
# セクション生成(各々エラー隔離)                                             #
# --------------------------------------------------------------------------- #
def _preamble(lang: str = "ja", missing: list | None = None) -> list[str]:
    T = (lambda s: _t(s, lang))
    return [
        "# Fullseye Operator Catalog — AI capability ledger",
        "",
        T("Fullseye は説明可能な古典/幾何ビジョンの Physical-AI ツールキット。この台帳は "
          "**用途を伝えれば、どの op をどう組み合わせればよいかを AI が提案する**ための一覧です。"),
        "",
        T("## この台帳の使い方(assistant 向け)"),
        "",
        T("1. ユーザーの**用途(入力データ・欲しい出力)**を特定する。"),
        T("2. まず **Worked examples**(用途→op の実例)から最も近いものを探し、その op 連鎖を土台にする。"),
        T("3. 連鎖は **in → out のデータ種**が繋がるように組む(例: `image → region → feature`、"
          "`points → voxel → mesh`)。2D パイプライン op は 1 画像+2 スカラつまみのモデル、"
          "点群/体積の 3D op と 2 画像を取る op(morph 等)は関数として呼ぶ。"),
        T("4. 各 op の**前提と失敗条件**(退化入力・必要点数など)を必ず確認し、fail-closed に扱う。"),
        T("5. 提案には**具体的な op 名**と、可能なら該当する worked example / References を添える。"),
        T("6. 実装が不確かなら、対応する `examples*/` を実行して ground-truth 出力で確かめる。"),
        "",
    ]


#: 言語版の worked examples で 1 例に並べる op の上限(残りは個数で書く)。
_EX_OPS_SHOWN = 12


def _ops_by_example() -> tuple[dict, dict]:
    """``(2-D の例 id -> {op}, 3-D の例 id -> {op})``。op ノートの例リンク(``rec["examples"]``)を逆に引く。"""
    sys.path.insert(0, os.path.join(_REPO, "tools"))
    import opdocs as OD
    two, three = {}, {}
    for r in OD._records()[0]:
        for e in r.get("examples") or ():
            (three if r["dim"] == "3d" else two).setdefault(e, set()).add(r["name"])
    return two, three


def _examples_section(lang: str = "ja", missing: list | None = None) -> list[str]:
    T = (lambda s: _t(s, lang))
    out = [T("## Worked examples(用途 → 使う op の実例=推奨組合せの手本)"), ""]
    if lang != "ja":
        out += [T("_examples_note").format(k=_EX_OPS_SHOWN), ""]
        two, three = _ops_by_example()
    for mod_name, label, run_dir in [("examples2d", "2-D 画像/信号/幾何", "examples"),
                                     ("examples3d", "3-D 点群/体積/曲面", "examples_3d")]:
        try:
            EX = __import__(mod_name)
            names = EX.names()
        except Exception as e:
            out += [f"### {T(label)}", T("- (catalog: {mod} を読めませんでした: {e})").format(mod=mod_name, e=e), ""]
            continue
        out += [T("### {label}({n} 例)").format(label=T(label), n=len(names)), ""]
        try:
            grouped = EX.by_task()
        except Exception:
            grouped = {"(all)": names}
        for task, ids in grouped.items():
            out.append(f"**{task}**")
            for i in ids:
                if lang != "ja":
                    ops = sorted((three if run_dir == "examples_3d" else two).get(i, ()))
                    if ops:
                        shown = ", ".join(f"`{o}`" for o in ops[:_EX_OPS_SHOWN])
                        more = (T("_examples_more").format(n=len(ops) - _EX_OPS_SHOWN)
                                if len(ops) > _EX_OPS_SHOWN else "")
                        what = T("_examples_ops").format(ops=shown) + more
                    else:
                        what = T("_examples_noops")
                    out.append(f"- `{i}` — {what} `py -3.11 {run_dir}/{i}.py`")
                    continue
                try:
                    e = EX.get(i)
                    out.append(f"- **{e.get('name', i)}** — {e.get('summary', '')} "
                               f"`py -3.11 {run_dir}/{i}.py`")
                except Exception as ex:
                    out.append(f"- {i} (introspection failed: {ex})")
            out.append("")
    return out


_STANDALONE = [
    ("imagemorph", "対応点駆動の2D画像ワープ・顔モーフ"),
    ("fourierdesc", "閉輪郭の楕円フーリエ記述子・平滑化"),
    ("imagedraw", "画像へのラスタ描画(マーカー/線/円/輪郭)"),
    ("signal1d", "点列の多項式/FFT/フィルタ/スプライン(開閉・2D/3D)"),
]


def _modules_section(lang: str = "ja", missing: list | None = None) -> list[str]:
    T = (lambda s: _t(s, lang))
    missing = [] if missing is None else missing
    out = [T("## スタンドアロン幾何/数学モジュール(関数 API)"), "",
           T("1画像パイプラインに乗らない op(2画像・点列・可変引数)。関数として呼ぶ。"), ""]
    for mod_name, hint in _STANDALONE:
        try:
            m = __import__(mod_name)
        except Exception as e:
            # 原文の一言(hint)は言語版では表を引かず、モジュール名だけを見出しにする(訳の無い日本語を出さない)
            head = f"### `{mod_name}` — {hint}" if lang == "ja" else f"### `{mod_name}`"
            out += [head, T("- (import 失敗: {e})").format(e=e), ""]
            continue
        d1 = _doc1(m)
        if d1:
            out += [f"### `{mod_name}` — {_doc_line_tr(mod_name, d1, lang, missing)}", ""]
        else:
            out += [f"### `{mod_name}` — {hint}" if lang == "ja" else f"### `{mod_name}`", ""]
        names = getattr(m, "__all__", None) or [n for n in dir(m) if not n.startswith("_")]
        for n in names:
            try:
                fn = getattr(m, n)
                if not callable(fn):
                    continue
                doc = _doc_line_tr(f"{mod_name}.{n}", _doc1(fn), lang, missing)
                out.append(f"- `{n}{_sig(fn)}` — {doc}")
            except CatalogTranslationError:
                raise
            except Exception as ex:
                out.append(f"- `{n}` (introspection failed: {ex})")
        out.append("")
    return out


#: 族の冒頭に置く手書きの一言(op の一覧そのものは生成)。無い族は一言なしで出す。
_FAMILY_INTRO = {
    "2d": ("1 画像を取り 1 画像/領域/輪郭/特徴を返すパイプライン op(`ops.REGISTRY`)と、複数画像を取る "
           "n-ary op(`imgops_nary`)。`in → out` のデータ種で連鎖を組む。HALCON 別名は用途の手掛かり。"),
    "3d": "点群・体積・メッシュ・深度の op(`ops3d.OPS3D`)。関数として呼ぶ。",
    "oned": ("プロファイル/信号の 1-D op。源流は 2-D の measure1d・3-D の probe・"
             "音声/センサー系列(dsp)— 取り出した (x, y) 列を funct1d/dsp で加工して測る。"),
    "math": ("視覚計測を支える数学 op(線形代数/統計/補間・多項式)+ 複素解析の"
             "計算可能な切り口(周回積分・Cauchy 積分公式・偏角の原理・Laurent 係数/"
             "留数・等角写像・Cauchy-Riemann 残差)。FFT/複素画像は complexops・"
             "volfreq、1-D 関数は funct1d を参照。"),
    "optics": ("レンズより上・画素より下の層。幾何光学(薄レンズ結像・ABCD 光線伝達・"
               "被写界深度・cos⁴ 口径食)/ 波動光学(Airy パターン・角スペクトル伝搬・"
               "Fraunhofer 回折・ガウシアンビーム)/ 結像品質(PSF→MTF・回折限界 MTF・"
               "Zernike 波面統計)/ 偏光(Jones・Stokes・Mueller)/ 材料の物性表(matprop)・"
               "光ファイバ(fiber)・センサーの特性(sensorchar)・大域光輸送ほか。"),
    "drive": ("名前は運転だが、中身は**物理シミュレーションとロボットの PoC の台帳**: 運転(コース・交通・判断・"
              "CARLA / CommonRoad)に加え、触覚(tac*)・peg-in-hole(peg*)・研磨(polish)・研削(grind)・切削(cutting)・"
              "粉体(granular / scoop)・粉末 X 線回折(pxrd)・球技(ball / puck)などがカテゴリとして同居している。"
              "カテゴリ名で引くこと。"),
}

_TR.update({
    _FAMILY_INTRO["2d"]: {
        "en": ("Pipeline ops that take one image and return one image / region / contour / feature "
               "(`ops.REGISTRY`), and n-ary ops that take several images (`imgops_nary`). Build chains by the "
               "`in → out` data kinds. The HALCON aliases are clues to the use case."),
        "zh": ("取 1 幅图像、返回 1 幅图像/区域/轮廓/特征的流水线 op(`ops.REGISTRY`)，以及取多幅图像的 "
               "n-ary op(`imgops_nary`)。按 `in → out` 的数据种类组链。HALCON 别名是用途的线索。")},
    _FAMILY_INTRO["3d"]: {
        "en": "Ops for point clouds, volumes, meshes and depth (`ops3d.OPS3D`). Call them as functions.",
        "zh": "点云、体数据、网格与深度的 op(`ops3d.OPS3D`)。作为函数调用。"},
    _FAMILY_INTRO["oned"]: {
        "en": ("1-D ops for profiles / signals. Their sources are 2-D measure1d, 3-D probe and audio / sensor "
               "series (dsp) — the extracted (x, y) sequence is processed with funct1d/dsp and measured."),
        "zh": ("剖面/信号的 1-D op。来源是 2-D 的 measure1d、3-D 的 probe 以及音频/传感器序列(dsp)"
               "—— 用 funct1d/dsp 加工取出的 (x, y) 序列并进行测量。")},
    _FAMILY_INTRO["math"]: {
        "en": ("Math ops that support visual measurement (linear algebra / statistics / interpolation, "
               "polynomials) + computable entry points into complex analysis (contour integrals, Cauchy's "
               "integral formula, the argument principle, Laurent coefficients / residues, conformal maps, "
               "Cauchy-Riemann residuals). For FFT / complex images see complexops and volfreq; for 1-D "
               "functions see funct1d."),
        "zh": ("支撑视觉测量的数学 op(线性代数/统计/插值、多项式)+ 复分析的可计算切入点(围道积分、"
               "Cauchy 积分公式、辐角原理、Laurent 系数/留数、共形映射、Cauchy-Riemann 残差)。"
               "FFT/复数图像见 complexops、volfreq，1-D 函数见 funct1d。")},
    _FAMILY_INTRO["optics"]: {
        "en": ("The layer above the lens and below the pixel. Geometric optics (thin-lens imaging, ABCD ray "
               "transfer, depth of field, cos⁴ vignetting) / wave optics (Airy pattern, angular-spectrum "
               "propagation, Fraunhofer diffraction, Gaussian beams) / imaging quality (PSF→MTF, "
               "diffraction-limited MTF, Zernike wavefront statistics) / polarisation (Jones, Stokes, Mueller) "
               "/ material property tables (matprop), optical fibres (fiber), sensor characteristics "
               "(sensorchar), global light transport and more."),
        "zh": ("位于镜头之上、像素之下的层。几何光学(薄透镜成像、ABCD 光线传递、景深、cos⁴ 渐晕)/ "
               "波动光学(Airy 图样、角谱传播、Fraunhofer 衍射、高斯光束)/ 成像质量(PSF→MTF、"
               "衍射极限 MTF、Zernike 波前统计)/ 偏振(Jones、Stokes、Mueller)/ 材料物性表(matprop)、"
               "光纤(fiber)、传感器特性(sensorchar)、全局光传输等。")},
    _FAMILY_INTRO["drive"]: {
        "en": ("The name says driving, but the content is a **ledger of physics-simulation and robot PoCs**: "
               "besides driving (courses, traffic, decisions, CARLA / CommonRoad), categories such as touch "
               "(tac*), peg-in-hole (peg*), polishing (polish), grinding (grind), cutting (cutting), granular "
               "media (granular / scoop), powder X-ray diffraction (pxrd) and ball games (ball / puck) live "
               "side by side. Look things up by category name."),
        "zh": ("名字是驾驶，内容却是**物理仿真与机器人 PoC 的台账**: 除驾驶(赛道、交通、决策、"
               "CARLA / CommonRoad)外，触觉(tac*)、peg-in-hole(peg*)、抛光(polish)、磨削(grind)、"
               "切削(cutting)、粉体(granular / scoop)、粉末 X 射线衍射(pxrd)、球类(ball / puck)等"
               "作为类别共存其中。请按类别名查找。")},
})


def _family_order(recs) -> list:
    """族の並び = ``docs/ops/INDEX.md`` と同じ(2d, 3d, 台帳の登録順)。台帳に無い族は最後に名前順。"""
    sys.path.insert(0, os.path.join(_REPO, "tools"))
    import opdocs as OD
    order = ["2d", "3d", *OD.LEDGER_DIMS]
    present = {r["dim"] for r in recs}
    return [d for d in order if d in present] + sorted(present - set(order))


def _families_section(lang: str = "ja", missing: list | None = None) -> list[str]:
    """全 op を**族(``docs/ops/<族>/``)→ カテゴリ**の順に並べる。

    ★2026-10-15 まで、このカタログは ops / ops3d / ops1d / opsmath / opsoptics の **5 つのレジストリだけ**を
    手で 1 節ずつ書いていて、残る 43 の台帳族(drive 694・segmentation 54・annotate 51 …)の **1,351 名が
    1 度も出てこなかった**。pip だけで入れた利用者の RAG(``fullseye-rag``)はこのファイルしか持たないので、
    その op は wheel の利用者からは探しようがなかった。op ノートと**同じ母集団**(``tools/opdocs._records``)
    から書くことで、族を足しても節を書き足す必要がなくなる(門 = ``tests/test_rag_by_ops.py``)。

    言語版の要約は ``opdocs.op_summary``(原文の指紋が合う訳だけ)。出せない op は ``missing`` に積む。
    """
    sys.path.insert(0, os.path.join(_REPO, "tools"))
    import opdocs as OD
    T = (lambda s: _t(s, lang))
    missing = [] if missing is None else missing
    recs = OD._records()[0]
    if not recs:
        raise RuntimeError("opdocs._records() が 0 件 —— 空のカタログを書かない(fail-closed)")
    by_dim: dict[str, dict[str, list]] = {}
    for r in recs:
        by_dim.setdefault(r["dim"], {}).setdefault(r["category"] or "(none)", []).append(r)
    order = _family_order(recs)
    out = [T("## Operators by family(族 → カテゴリ、全 op)"), "",
           T("_計 {n} ops / {m} families。並びとノートの在り処は `docs/ops/INDEX.md` と同じ"
             "(ノート = `docs/ops/<族>/<カテゴリ>/<op>.md`)。台帳族の op は `fs.ledger.<op>` で呼ぶ。_")
           .format(n=len(recs), m=len(order)), ""]
    out.append(T("族の一覧: ") + " · ".join(
        f"**{d}** {sum(len(v) for v in by_dim[d].values())}" for d in order))
    out.append("")
    sp = "" if lang == "ja" else " "                    # 日本語版は全角の括弧の流儀(空白なし)を保つ
    for dim in order:
        cats = by_dim[dim]
        n = sum(len(v) for v in cats.values())
        out.append(f"### {dim}{sp}({n} ops / {len(cats)} categories)")
        out.append("")
        if dim in _FAMILY_INTRO:
            out += [T(_FAMILY_INTRO[dim]), ""]
        for cat in sorted(cats):
            rows = sorted(cats[cat], key=lambda r: r["name"])
            out.append(f"#### {dim} / {cat}{sp}({len(rows)})")
            for r in rows:
                if lang == "ja":
                    summ = (OD.summary_and_rest(r.get("doc"))[0] or "").strip()
                else:
                    summ, ok = OD.op_summary(r, lang)
                    summ = (summ or "").strip()
                    if summ and not ok:
                        missing.append("op_summary.json:%s/%s" % (r["dim"], r["name"]))
                hal = f" (halcon: `{r['halcon']}`)" if r.get("halcon") else ""
                io_ = f"`{r.get('in') or T('入力なし')} → {r.get('out') or '?'}`"
                ex = _ex_link(r.get("examples"), lang) if dim in ("2d", "3d") else (
                    _ex_link(r.get("examples"), lang) if r.get("examples") else "")
                gpu = " GPU: " + _gpu_text(r.get("gpu_status", "なし"), lang)
                out.append(f"- `{r['name']}`{hal} {io_}{gpu}" + (f" — {summ}" if summ else "") + ex)
            out.append("")
    return out


# 参照(実在する一次情報/Wikipedia。捏造しない — 主要な技術族のみ curated)。
_REFERENCES = [
    ("Marching cubes(voxel→mesh)", "https://en.wikipedia.org/wiki/Marching_cubes"),
    ("Elliptic Fourier descriptors", "https://en.wikipedia.org/wiki/Elliptic_Fourier_descriptor"),
    ("Thin plate spline(TPS 変形)", "https://en.wikipedia.org/wiki/Thin_plate_spline"),
    ("Image morphing(feature-based)", "https://en.wikipedia.org/wiki/Morphing"),
    ("Perspective-n-Point(PnP 姿勢)", "https://en.wikipedia.org/wiki/Perspective-n-Point"),
    ("RANSAC(ロバスト推定)", "https://en.wikipedia.org/wiki/Random_sample_consensus"),
    ("Iterative closest point(ICP/GICP)", "https://en.wikipedia.org/wiki/Iterative_closest_point"),
    ("Superquadrics", "https://en.wikipedia.org/wiki/Superquadrics"),
    ("Signed distance function(ESDF)", "https://en.wikipedia.org/wiki/Signed_distance_function"),
    ("Photometric stereo", "https://en.wikipedia.org/wiki/Photometric_stereo"),
    ("Phase unwrapping(structured light)", "https://en.wikipedia.org/wiki/Phase_unwrapping"),
    ("Medial axis / skeleton", "https://en.wikipedia.org/wiki/Medial_axis"),
    ("Geodesic(距離)", "https://en.wikipedia.org/wiki/Geodesic"),
    ("Digital elevation model(DEM)", "https://en.wikipedia.org/wiki/Digital_elevation_model"),
    ("Spline interpolation", "https://en.wikipedia.org/wiki/Spline_interpolation"),
    ("Delaunay triangulation", "https://en.wikipedia.org/wiki/Delaunay_triangulation"),
    ("Fourier transform", "https://en.wikipedia.org/wiki/Fourier_transform"),
    ("Image moment(invariants)", "https://en.wikipedia.org/wiki/Image_moment"),
]


def _references_section(lang: str = "ja", missing: list | None = None) -> list[str]:
    T = (lambda s: _t(s, lang))
    out = [T("## References(アルゴリズムの一次情報・further reading)"), "",
           T("各 op の原理はモジュール docstring にも一次文献名を明記。以下は主要技術族の外部参照。"), ""]
    out += [f"- {T(name) if _has_ja(name) else name} — <{url}>" for name, url in _REFERENCES]
    out.append("")
    return out


def build_catalog(lang: str = "ja") -> str:
    """``lang`` の台帳を 1 枚の Markdown で返す。

    言語版(``en`` / ``zh``)で訳が無い・指紋が古い行があれば :class:`CatalogTranslationError`
    (件数と先頭のキーを言う)。日本語版は従来どおり。
    """
    if lang not in LANGS:
        raise ValueError("gen_op_catalog: lang は %s のどれか(got %r)" % (", ".join(LANGS), lang))
    lines: list[str] = []
    missing: list[str] = []
    for section in (_preamble, _examples_section, _modules_section,
                    _families_section, _references_section):
        if section is _families_section:
            # ★fail-closed: op の一覧は台帳の本体。ここを「(section failed)」の 1 行で済ませると
            #   カタログが黙って空になる(pip だけの利用者の RAG はこのファイルしか持たない)。
            lines += section(lang, missing)
            continue
        try:
            lines += section(lang, missing)
        except CatalogTranslationError:
            raise                                       # 訳の欠けは「節の失敗」に畳まない
        except Exception as e:                          # 補助の節は 1 つ壊れても全体を出す
            lines += [f"## (section {section.__name__} failed: {e})", ""]
    if missing:
        raise CatalogTranslationError(
            "gen_op_catalog: %s 版に出せない訳が %d 件(指紋が古い/訳が無い)—— 日本語を混ぜて書かずに止める: %s%s"
            % (lang, len(missing), ", ".join(missing[:20]), " …" if len(missing) > 20 else ""))
    return "\n".join(lines) + "\n"


def catalog_paths(ja_out: str | None = None) -> dict[str, list[str]]:
    """言語 -> 書き先(``docs/`` の人間向けと ``fullseye/`` の同梱)。``ja_out`` は日本語版の ``docs`` 側。"""
    ja_out = ja_out or os.path.join(_REPO, "docs", "OP_CATALOG.md")
    stem = ja_out[:-3] if ja_out.endswith(".md") else ja_out
    shipped_dir = os.path.join(_REPO, "fullseye")
    out = {}
    for lang in LANGS:
        suffix = ".md" if lang == "ja" else ".%s.md" % lang
        targets = [stem + suffix]
        shipped = os.path.join(shipped_dir, "OP_CATALOG" + suffix)
        if os.path.isdir(shipped_dir) and os.path.abspath(shipped) != os.path.abspath(targets[0]):
            targets.append(shipped)
        out[lang] = targets
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=os.path.join(_REPO, "docs", "OP_CATALOG.md"),
                    help="日本語版の書き先(言語版はその横に OP_CATALOG.<lang>.md)")
    args = ap.parse_args()
    # ★全言語を組み上げてから書く: 言語版の訳が欠けて止まるとき、日本語版だけ新しくなる半端を作らない。
    built = {lang: build_catalog(lang) for lang in LANGS}
    sys.path.insert(0, os.path.join(_REPO, "tools"))
    import i18n_guide_check as IG
    for lang, paths in catalog_paths(args.out).items():
        md = built[lang]
        for path in paths:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(md)
            print(f"wrote {path} ({len(md):,} bytes, {md.count(chr(10))} lines)")
        if lang != "ja":
            res = IG.japanese_residue(md, lang)
            print(f"  {lang}: 日本語の残り {len(res)} 行" + (
                "(先頭: " + "; ".join(f"L{n}: {s}" for n, s in res[:5]) + ")" if res else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
