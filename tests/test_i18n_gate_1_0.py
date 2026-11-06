# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""1.0.0 の文書の門 —— ``OP_CATALOG`` と知識ガイドの英語版・中国語版(``docs/I18N.md``)。

``CONTRIBUTING.md`` は 1.0.0 の条件に「``docs/I18N.md`` の文書の門(``OP_CATALOG`` と知識ガイドの
英語・中国語)」を挙げている。ここがその門。2 部に分かれる:

1. **門そのもの**(訳がそろうまで赤): 知識ガイド 17 本以上のそれぞれに ``.en.md`` / ``.zh.md`` があり、
   front matter(``lang`` / ``translation_of`` / ``source_sha256``)が正しく、``source_sha256`` が原文の
   **今の**中身と一致し(原文を直したら訳し直すまで赤)、code span・数値・URL・見出し・表・コードブロックが
   原文と一致すること。``OP_CATALOG.en.md`` / ``.zh.md`` が生成物として最新で、日本語の残りが 0 であること。
2. **照合の道具の検査**(常に緑): ``tools/i18n_guide_check.py`` が、合成した小さな原文・訳の組で
   一致を一致と、欠けを欠けと判定すること。道具が壊れて何でも通すなら、1. の緑には意味が無い。

訳のファイルの形式と照合の項目は ``tools/i18n_guide_check.py`` の docstring。
"""
from __future__ import annotations

import collections
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, ROOT)
import i18n_guide_check as IG  # noqa: E402
import opdocs as OD  # noqa: E402

from conftest import requires_full_registry  # noqa: E402

#: 知識ガイドの本数の床(2026-11-06 の実測 17)。訳のファイルを別のガイドと数えると 51 に見える。
_GUIDES_FLOOR = 17


def _guides():
    gs = OD.knowledge_guides()
    assert len(gs) >= _GUIDES_FLOOR, (
        "知識ガイドが %d 本(床 %d)—— 走査が壊れていないか" % (len(gs), _GUIDES_FLOOR))
    return gs


# =========================================================================== #
# 1. 門(訳がそろうまで赤)                                                    #
# =========================================================================== #
def test_knowledge_guides_are_not_inflated_by_their_translations():
    """訳(``<name>.<lang>.md``)は別のガイドではない —— 本数は原文の数のまま。"""
    gs = _guides()
    stems = [g["stem"] for g in gs]
    assert len(gs) == 17, "知識ガイドが %d 本(2026-11-06 は 17 本): %s" % (len(gs), stems)
    leaked = [s for s in stems if OD.translation_lang(s + ".md")]
    assert not leaked, "訳のファイルがガイドとして数えられている: %s" % leaked


def test_every_knowledge_guide_has_english_and_chinese():
    gs = _guides()
    missing = [IG.repo_rel(IG.translation_path(g["path"], lang))
               for g in gs for lang in IG.TARGET_LANGS
               if not os.path.exists(IG.translation_path(g["path"], lang))]
    assert not missing, "訳が無い %d / %d 組:\n  %s" % (
        len(missing), len(gs) * len(IG.TARGET_LANGS), "\n  ".join(missing))


def test_every_translation_matches_its_source():
    """front matter(lang / translation_of / source_sha256)と構造(code span・数値・URL・見出し・表・
    コードブロック)と地の文の日本語の残りを、全組について照合する。訳が無い組も落ちる側に数える。"""
    gs = _guides()
    pairs = [(g["path"], lang) for g in gs for lang in IG.TARGET_LANGS]
    assert len(pairs) >= 2 * _GUIDES_FLOOR
    bad = {}
    for src, lang in pairs:
        probs = IG.check_pair(src, lang)
        if probs:
            bad[IG.repo_rel(IG.translation_path(src, lang))] = probs
    assert not bad, "照合が合わない %d / %d 組(`py -3.11 tools/i18n_guide_check.py --all`):\n%s" % (
        len(bad), len(pairs),
        "\n".join("  %s\n    - %s" % (k, "\n    - ".join(v[:4])) for k, v in sorted(bad.items())))


def _catalog_paths():
    import gen_op_catalog as GC
    paths = GC.catalog_paths()
    assert set(paths) == {"ja", "en", "zh"}, paths
    return GC, paths


def test_op_catalog_translations_match_the_generator():
    """``OP_CATALOG.en.md`` / ``.zh.md``(docs と同梱の fullseye)が生成器の出力と一致する。"""
    requires_full_registry()
    GC, paths = _catalog_paths()
    stale = []
    for lang in ("en", "zh"):
        md = GC.build_catalog(lang)
        assert len(paths[lang]) == 2, paths[lang]
        for p in paths[lang]:
            if not os.path.exists(p):
                stale.append("%s が無い" % IG.repo_rel(p))
                continue
            with open(p, encoding="utf-8") as f:
                if f.read() != md:
                    stale.append("%s が古い" % IG.repo_rel(p))
    assert not stale, "`py -3.11 tools/gen_op_catalog.py` で作り直す: %s" % stale


def test_op_catalog_translations_have_no_japanese_left():
    """言語版の目録に日本語が残っていない(code span・URL・フェンスの中は除く)。

    ``en``: かな・漢字・全角記号。``zh``: ひらがな・カタカナ(和文の中点 ``・`` を含む)。
    """
    _GC, paths = _catalog_paths()
    found = {}
    for lang in ("en", "zh"):
        p = paths[lang][0]
        assert os.path.exists(p), "%s が無い" % IG.repo_rel(p)
        with open(p, encoding="utf-8") as f:
            text = f.read()
        assert text.count("\n- `") >= 3000, "%s の op 行が少なすぎる(空の目録を通さない)" % p
        res = IG.japanese_residue(text, lang)
        if res:
            found[lang] = res
    assert not found, "日本語が残る: %s" % {k: ["L%d %s" % x for x in v[:8]] + ["(計 %d 行)" % len(v)]
                                          for k, v in found.items()}


def test_op_catalog_translation_is_the_translation_not_a_copy():
    """英語版の op の要約は英語で、日本語版と同じ op を同じ数だけ載せる(訳したつもりで原文を写していない)。"""
    _GC, paths = _catalog_paths()
    texts = {}
    for lang in ("ja", "en", "zh"):
        with open(paths[lang][0], encoding="utf-8") as f:
            texts[lang] = f.read()
    ops = {lang: sorted(l.split("`")[1] for l in t.split("\n")
                        if l.startswith("- `") and "` `" in l and " GPU: " in l)
           for lang, t in texts.items()}
    assert len(ops["ja"]) >= 3000, len(ops["ja"])
    assert ops["en"] == ops["ja"] and ops["zh"] == ops["ja"], "言語版と日本語版で op の並びが違う"
    assert texts["en"] != texts["ja"] and texts["zh"] != texts["en"]


# =========================================================================== #
# 2. 照合の道具の検査(常に緑)                                                 #
# =========================================================================== #
_SRC = """---
guide: demo
dim: 2d
title: 測色の知識
title_en: Colorimetry
title_zh: 测色知识
applies_to: 2d/color
---
# 測色の知識

色は `spectrum_to_xyz` で求める。D65 の白色点は 6504 K、許容差は 1,000 分の 2。
詳しくは <https://cie.co.at/publications> を見る。

## 表

| 量 | 値 |
|---|---|
| ΔE | 2.3 |

```python
xyz = spectrum_to_xyz(s)   # 日本語のコメント
```
"""

_TR_EN_BODY = """# Colorimetry

Colour is computed with `spectrum_to_xyz`. The D65 white point is 6504 K and the tolerance is 2 in 1000.
See <https://cie.co.at/publications> for details.

## Table

| Quantity | Value |
|---|---|
| ΔE | 2.3 |

```python
xyz = spectrum_to_xyz(s)   # 日本語のコメント
```
"""


def _tr_en(src_text, body=_TR_EN_BODY, **over):
    front = {"guide": "demo", "dim": "2d", "title": "Colorimetry", "title_en": "Colorimetry",
             "title_zh": "测色知识", "applies_to": "2d/color", "lang": "en",
             "translation_of": "docs/ops/2d/guides/demo.md",
             "source_sha256": IG.hashlib.sha256(src_text.encode("utf-8")).hexdigest()}
    front.update(over)
    return "---\n" + "".join("%s: %s\n" % kv for kv in front.items() if kv[1] is not None) + "---\n" + body


def _check(tr, src=_SRC, lang="en"):
    return IG.check_texts(src, tr, lang, "docs/ops/2d/guides/demo.md",
                          IG.hashlib.sha256(src.encode("utf-8")).hexdigest())


def test_checker_accepts_a_matching_pair():
    assert _check(_tr_en(_SRC)) == []


def test_checker_catches_a_dropped_code_span():
    probs = _check(_tr_en(_SRC, _TR_EN_BODY.replace("`spectrum_to_xyz`", "spectrum_to_xyz", 1)))
    assert len(probs) == 1 and "code span" in probs[0] and "spectrum_to_xyz" in probs[0], probs


def test_checker_catches_a_changed_number_url_heading_table_and_fence():
    cases = {
        "数値": _TR_EN_BODY.replace("6504 K", "6500 K"),
        "URL": _TR_EN_BODY.replace("cie.co.at/publications", "cie.co.at/"),
        "見出し": _TR_EN_BODY.replace("## Table", "### Table"),
        "表の行数": _TR_EN_BODY.replace("| ΔE | 2.3 |\n", "| ΔE | 2.3 |\n| x | |\n"),
        "コードブロック": _TR_EN_BODY + "\n```\nmore\n```\n",
    }
    assert len(cases) == 5
    for label, body in cases.items():
        probs = _check(_tr_en(_SRC, body))
        assert len(probs) == 1 and label in probs[0], (label, probs)


def test_checker_front_matter_rules():
    stale = _check(_tr_en(_SRC, source_sha256="0" * 64))
    assert len(stale) == 1 and "source_sha256" in stale[0], stale
    wrong_lang = _check(_tr_en(_SRC, lang="zh"))
    assert len(wrong_lang) == 1 and "lang" in wrong_lang[0], wrong_lang
    wrong_of = _check(_tr_en(_SRC, translation_of="docs/ops/2d/guides/other.md"))
    assert len(wrong_of) == 1 and "translation_of" in wrong_of[0], wrong_of
    not_copied = _check(_tr_en(_SRC, applies_to="2d"))
    assert len(not_copied) == 1 and "applies_to" in not_copied[0], not_copied
    wrong_title = _check(_tr_en(_SRC, title="Colour"))
    assert len(wrong_title) == 1 and "title" in wrong_title[0], wrong_title
    extra = _check(_tr_en(_SRC, translator="x"))
    assert len(extra) == 1 and "translator" in extra[0], extra
    assert _check(_SRC) and any("front matter" in p or "lang" in p for p in _check(_SRC))


def test_checker_counts_japanese_left_in_prose_but_not_in_code_blocks():
    """地の文に日本語が残れば落とす。コードブロックの中(コメント・mermaid のラベル)は数えない。"""
    body = _TR_EN_BODY.replace("for details.", "for details. 詳しくは原文。")
    probs = _check(_tr_en(_SRC, body))
    assert len(probs) == 1 and "日本語" in probs[0], probs
    # 上の _TR_EN_BODY はコードブロックの中に日本語のコメントを持つが、一致の組として通る
    assert "日本語のコメント" in _TR_EN_BODY and _check(_tr_en(_SRC)) == []


def test_sha_is_computed_on_lf_normalised_bytes(tmp_path):
    lf, crlf = tmp_path / "a.md", tmp_path / "b.md"
    lf.write_bytes("# 題\n本文\n".encode("utf-8"))
    crlf.write_bytes("# 題\r\n本文\r\n".encode("utf-8"))
    assert IG.normalized_sha256(str(lf)) == IG.normalized_sha256(str(crlf))
    assert IG.normalized_sha256(str(lf)) == IG.hashlib.sha256("# 題\n本文\n".encode("utf-8")).hexdigest()


def test_numbers_are_normalised_for_separators_and_units():
    N = IG._numbers
    # 桁区切り(ASCII のカンマ)は外す。桁区切りでないカンマは 2 つの数
    assert N("1,234 と 1,2") == collections.Counter({"1234": 1, "1": 1, "2": 1})
    # 和文・中文の単位と英語の数詞を展開する(訳 A・B の報告: 「100 万」と「1,000,000」)
    assert N("約 100 万点") == N("about 1,000,000 points") == collections.Counter({"1000000": 1})
    assert N("2 万回") == N("20,000 times")
    assert N("1000 万回級") == N("10-million-cycle class") == N("1 千万") == collections.Counter({"10000000": 1})
    assert N("3 亿") == N("300,000,000") and N("1.5 億") == N("150,000,000")
    # ★全角の読点「，」は数を区切る(NFKC を先に掛けると 350,424 という 1 つの数に化けていた)
    assert N("350，424") == collections.Counter({"350": 1, "424": 1}) == N("350、424")
    # 全角数字は半角にそろえる
    assert N("１２") == N("12")


def test_japanese_residue_rules():
    en = "- `入力なし` ok\nplain 日本語\n```\n# 日本語\n```\nAlso a・b\n"
    assert [n for n, _s in IG.japanese_residue(en, "en")] == [2, 6]
    zh = "这是中文。\n仍有かな\n中点・不行\n`コード` 可以\n"
    assert [n for n, _s in IG.japanese_residue(zh, "zh")] == [2, 3]


def test_translation_files_are_tied_to_their_source(tmp_path, monkeypatch):
    """``<name>.en.md`` / ``.zh.md`` は別のガイドではなく原文の言語版(訳 B の作業木で 17 → 35 本に見えた)。"""
    for rel in ("optics/guides/a.md", "optics/guides/a.en.md", "optics/guides/a.zh.md",
                "math/guides/b.md", "math/guides/b.de.md"):
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("---\napplies_to: optics\n---\n# %s\n" % p.stem, encoding="utf-8")
    monkeypatch.setattr(OD, "DOCS", str(tmp_path))
    monkeypatch.setattr(OD, "_KNOWLEDGE_GUIDES", None)
    gs = OD.knowledge_guides()
    assert [g["stem"] for g in gs] == ["b", "a"] or [g["stem"] for g in gs] == ["a", "b"]
    assert len(gs) == 2
    a = str(tmp_path / "optics/guides/a.md")
    assert sorted(OD.guide_translations(a)) == ["en", "zh"]
    assert OD.translation_lang("a.zh.md") == "zh" and OD.translation_lang("a.md") is None
    # 指紋が合う訳だけが Studio のヘルプに出る
    tp = tmp_path / "optics/guides/a.en.md"
    tp.write_text("---\nlang: en\nsource_sha256: %s\n---\n# A\n" % IG.normalized_sha256(a), encoding="utf-8")
    assert OD.fresh_guide_translation(a, "en").endswith("# A\n")
    tp.write_text("---\nlang: en\nsource_sha256: %s\n---\n# A\n" % ("0" * 64), encoding="utf-8")
    assert OD.fresh_guide_translation(a, "en") is None
    assert OD.fresh_guide_translation(a, "ko") is None
