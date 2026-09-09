# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""設計判断集(`docs/DESIGN_NOTES*.md`)の門(2026-09-09)。

ソースの日本語コメントは 100,786 行あり、6 言語で併記する形は取らない
(約 50 万行に膨らみ、編集のたびに 6 か所を直すことになる)。代わりに `★` の
付いた塊 606 件だけを生成物として訳す。

ここで見るのは 2 つ:

* **生成物が最新か**(ソースの ★ が変われば作り直しが要る)
* **訳の本数が減っていないか**(ratchet)。増やすのは歓迎、減らすのは事故。
  原文を書き換えると訳が外れて未訳に戻る —— それは**正しい**挙動だが、
  黙って減ると気づけないのでここで止める。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import gen_design_notes as G  # noqa: E402

#: 訳の下限。**増やしたらこの数も上げる**(下げるときは理由をコミットに書く)。
#: 2026-09-09 の第一陣は 5 件 —— 外から来た人が最初に当たる場所から埋めている。
MIN_TRANSLATED = 5


def _meta():
    with open(os.path.join(ROOT, "docs", "design_notes.json"), encoding="utf-8") as f:
        return json.load(f)


def test_the_digest_is_current():
    """作り直した内容が commit 済みと一致すること。"""
    blocks = G.collect()
    for lang in ("ja", "en"):
        name = "DESIGN_NOTES.md" if lang == "ja" else "DESIGN_NOTES.%s.md" % lang
        with open(os.path.join(ROOT, "docs", name), encoding="utf-8") as f:
            on_disk = f.read()
        assert on_disk == G.render(blocks, lang), (
            "%s が古い —— `py -3.11 tools/gen_design_notes.py` を回して commit すること"
            % name)


def test_translation_count_never_goes_down():
    tr = _meta()["translated"]
    low = sorted((c, n) for c, n in tr.items() if n < MIN_TRANSLATED)
    assert not low, (
        "訳の本数が下限 %d を割った: %s —— 原文を書き換えると訳が外れて未訳に戻る"
        "(それ自体は正しい)。訳を直してから commit すること"
        % (MIN_TRANSLATED, ", ".join("%s=%d" % (c, n) for c, n in low)))


def test_the_collection_is_not_empty():
    """集まらなくなったら門は無言で通る ——「一致の門は空を通す」を封じる。"""
    meta = _meta()
    assert meta["total"] >= 300, (
        "★ の塊が %d 件しか集まらない(2026-09-09 の実測は 606 件)—— 抽出が壊れていないか"
        % meta["total"])
    assert meta["files"] >= 100


def test_untranslated_entries_are_marked_not_hidden():
    """未訳を黙って原文に落とすと「訳したつもり」になる。印が出ていること。"""
    with open(os.path.join(ROOT, "docs", "DESIGN_NOTES.en.md"), encoding="utf-8") as f:
        en = f.read()
    meta = _meta()
    if meta["translated"]["en"] < meta["total"]:
        assert "not translated" in en, "未訳の印が英語版に出ていない"
