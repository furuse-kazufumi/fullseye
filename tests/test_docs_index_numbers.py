# -*- coding: utf-8 -*-
"""★ドキュメント索引に書いた数字が、いまの実装と合っていることを機械で確かめる。

## なぜ要るか(2026-09-06)

`docs/README.md` は GitHub Pages のトップ(<https://furuse.work/>)として配信
されている**入口**で、この日 6 言語に増やした。その直後にユーザーから
「索引の内容は現状を表現するのに適切かな?」と聞かれて数え直したところ、
**3 つとも古かった**:

| 索引の記述 | 実測(2026-09-06) |
|---|---|
| オペレータ約 **521**(レジストリ) | **885** |
| 実 HALCON オペレータ **269/2313** | **979/2313**(42.3 %) |
| **31** カテゴリ | **47** |

しかもその古い数字は、**6 言語ぶんに複製されたあと**だった。訳す前に数え直す
機会は何度もあったのに、誰も数えていなかった —— この repo が繰り返し踏んで
いる「**登録済みを数える門は未登録に盲目**」と同じ形で、**書いた数字を数え直す
門が無かった**。

## 何を守るか

索引に**書いてある数**が、いま走らせて出る数と**厳密に一致**すること。
6 言語すべてで同じ数が書かれていること(片方だけ直す事故を防ぐ)。

数はいずれ動くので、**この門が落ちたら索引を直す**のであって、門の側を
緩めるのではない。直し方はエラーメッセージに書いてある。
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INDEX = sorted((ROOT / "docs").glob("README*.md"))

#: 索引に書いてある数 → いまの値を返す呼び出し。ここが「一次情報」。
def _registry_ops() -> int:
    import ops

    return len(ops.REGISTRY)


def _registry_categories() -> int:
    import ops

    return len({getattr(o, "category", None) for o in ops.REGISTRY})


def _halcon_genuine() -> int:
    """`docs/HALCON_PARITY.md` の見出しの数(`imgevolve.py coverage` が書く)。"""
    md = (ROOT / "docs" / "HALCON_PARITY.md").read_text(encoding="utf-8")
    m = re.search(r"\*\*(\d+)\s*/\s*2313 distinct real HALCON operators", md)
    assert m, "HALCON_PARITY.md の見出しが読めない(生成器が変わった?)"
    return int(m.group(1))


def test_the_index_exists_in_six_languages():
    got = {p.name for p in INDEX}
    want = {"README.md", "README.en.md", "README.zh.md", "README.tw.md",
            "README.ko.md", "README.de.md"}
    assert got == want, sorted(got ^ want)


@pytest.mark.parametrize("path", INDEX, ids=lambda p: p.name)
def test_the_index_operator_count_is_current(path):
    """「オペレータ約 N(レジストリ)」の N が実際の登録数と一致すること。"""
    n = _registry_ops()
    md = path.read_text(encoding="utf-8")
    head = md.split("\n---\n", 1)[0]
    assert "**%d**" % n in head, (
        "%s の op 数が古い(いまは %d)。索引の冒頭を直すこと —— "
        "6 言語すべて同じ数字にする。" % (path.name, n))


@pytest.mark.parametrize("path", INDEX, ids=lambda p: p.name)
def test_the_index_category_count_is_current(path):
    n = _registry_categories()
    md = path.read_text(encoding="utf-8")
    assert re.search(r"(?<![0-9])%d(?![0-9])" % n, md.split("\n---\n", 1)[0]), (
        "%s のカテゴリ数が古い(いまは %d)" % (path.name, n))


@pytest.mark.parametrize("path", INDEX, ids=lambda p: p.name)
def test_the_index_halcon_number_is_current(path):
    """★ここがいちばん腐りやすい。269/2313 のまま 979/2313 まで放置されていた。"""
    n = _halcon_genuine()
    md = path.read_text(encoding="utf-8")
    stale = re.findall(r"(?<![0-9])(\d+)/2313", md)
    assert stale, "%s に HALCON の割合が書かれていない" % path.name
    assert set(stale) == {str(n)}, (
        "%s の HALCON 実装数が古い(いまは %d/2313)。書いてあるのは %s —— "
        "`py -3.11 imgevolve.py coverage` で数え直してから直すこと。"
        % (path.name, n, sorted(set(stale))))


def test_every_language_carries_the_same_numbers():
    """片方の言語だけ直す事故を止める(前回は 6 言語まとめて古かった)。"""
    seen = {}
    for p in INDEX:
        head = p.read_text(encoding="utf-8").split("\n---\n", 1)[0]
        seen[p.name] = sorted(set(re.findall(r"\*\*([\d,./]+)\*\*", head)))
    ref = seen["README.md"]
    bad = {k: v for k, v in seen.items() if v != ref}
    assert not bad, "言語ごとに数字が食い違っている: 基準(ja)=%s / %s" % (ref, bad)
