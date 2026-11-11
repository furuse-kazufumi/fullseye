"""op_find の説明文が言語混在にならない / op_find descriptions never mix in another language.

再現(wheel 相当 = docs/ops の無い環境): ``op_find`` は registry に doc の無い op の説明を help HTML から取る。
以前は ``glob`` で最初に当たった ``<op>.de.html`` が勝ち、既定でドイツ語(「Datenarten」「Aufruf」)が混ざった。
"""
import re

import opassist

GERMAN = re.compile(r"Datenarten|Aufruf|Dieser Operator")


def _page(root, name, kinds):
    (root / name).write_text(
        "<html><body><h1>x — 2D op</h1><ul><li>%s : image → image</li></ul></body></html>" % kinds,
        encoding="utf-8")


def test_html_fallback_is_english_whatever_the_listing_order(tmp_path):
    for n, k in (("x.de.html", "Datenarten"), ("x.en.html", "Data kinds"), ("x.html", "データ種"),
                 ("x.ko.html", "데이터 종류"), ("x.zh.html", "数据种类")):
        _page(tmp_path, n, k)
    out = opassist._help_html_lines(str(tmp_path))
    assert "Data kinds" in out["x"] and not GERMAN.search(out["x"])


def test_untranslated_original_is_the_fallback_not_another_language(tmp_path):
    _page(tmp_path, "y.de.html", "Datenarten")
    _page(tmp_path, "y.html", "データ種")
    _page(tmp_path, "z.de.html", "Datenarten")          # 英語も原文も無い: 他言語は採らない
    out = opassist._help_html_lines(str(tmp_path))
    assert "データ種" in out["y"] and "z" not in out


def test_shipped_help_pages_yield_no_german(monkeypatch):
    """同梱の help HTML 全体: 1000 件超を英語で引け、ドイツ語は 1 件も混ざらない(空走査でないこと)。"""
    import os
    root = opassist._help_html_root(os.path.dirname(os.path.abspath(opassist.__file__)))
    out = opassist._help_html_lines(root)
    assert len(out) > 900
    assert not [k for k, v in out.items() if GERMAN.search(v)]
    assert sum("Data kinds" in v for v in out.values()) > 900
