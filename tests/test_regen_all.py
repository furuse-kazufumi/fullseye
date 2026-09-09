# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""`tools/regen_all.py` の表が現実から遅れないための門(2026-09-09)。

`regen_all` は「生成物の回し忘れ」を潰すために作った。ところがその CHAIN 自体を
**人が手で選んでいた**ので、同じ失敗が一段上で再発した —— `gen_examples3d_doc`
が漏れ、`docs/EXAMPLES_3D.md` は `ops3d = 347 op` と書いたまま古びていた
(実際は 357)。`tools/` の外にある `imgevolve.py index`(`docs/OP_INDEX.json`)と
`conversion_matrix.py`(`docs/CONVERSION_MATRIX.md`)も同じ理由で外れていた。

**手で書く表は、門を付けない限り必ず遅れる。** だからここでは
「ファイルを書くスクリプト」を**ディレクトリの側から**列挙し、その 1 本 1 本が
3 つの表のどれかに載っていることを要求する:

  * ``CHAIN``           —— 回すもの(``--check`` の対象)
  * ``EXCLUDED``        —— 生成器だが門にできないもの(**理由を書く**)
  * ``NOT_A_GENERATOR`` —— そもそも生成器でないもの(ベンチ・門・公開スクリプト)

新しい生成器を足した人は、どれかに分類することを迫られる。どれでもよいが、
**黙って増やすことだけができない。**
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import regen_all as RA  # noqa: E402


def test_every_generator_is_classified():
    """CHAIN / EXCLUDED / NOT_A_GENERATOR のどれにも無い生成器があれば落ちる。"""
    rest = RA.unclassified()
    assert not rest, (
        "分類されていない生成器が %d 本: %s —— "
        "回すなら CHAIN に、回せないなら EXCLUDED に**理由つきで**、"
        "生成器でないなら NOT_A_GENERATOR に入れてください "
        "(tools/regen_all.py)" % (len(rest), ", ".join(rest)))


def test_the_discovery_actually_finds_things():
    """列挙が空になったら門は無言で通る —— 「一致の門は空を通す」の型を封じる。

    印を緩めて 0 本にすれば `test_every_generator_is_classified` は永遠に緑。
    実測の下限を置いて、それが起きたら気づけるようにする。
    """
    found = RA.discover_generators()
    assert len(found) >= 30, (
        "生成器の列挙が %d 本しか返さない(2026-09-09 の実測は 44 本)—— "
        "_WRITES の印が壊れていないか" % len(found))
    assert "imgevolve.py" in found, "tools/ の外にある生成器が列挙から落ちている"


def test_excluded_entries_carry_a_reason():
    """除外は理由とセットでなければ、ただの黙殺と区別がつかない。"""
    thin = sorted(k for k, v in RA.EXCLUDED.items() if len(v.strip()) < 15)
    assert not thin, "除外の理由が短すぎる(なぜ門にできないかを書く): %s" % ", ".join(thin)


def test_chain_and_excluded_do_not_overlap():
    in_chain = {args[0] for args, _ in RA.CHAIN}
    both = sorted(in_chain & (set(RA.EXCLUDED) | set(RA.NOT_A_GENERATOR)))
    assert not both, "CHAIN と除外表の両方に載っている: %s" % ", ".join(both)


def test_classified_entries_still_exist():
    """消えたファイルの名前が表に残り続けると、表は嘘の台帳になる。"""
    missing = sorted(name for name in
                     (set(RA.EXCLUDED) | set(RA.NOT_A_GENERATOR)
                      | {args[0] for args, _ in RA.CHAIN})
                     if not os.path.isfile(os.path.join(ROOT, name)))
    assert not missing, "表に載っているのに実在しないファイル: %s" % ", ".join(missing)
