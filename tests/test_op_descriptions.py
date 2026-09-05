"""すべての op が「何をする op か」を自分で言えること。

2026-09-05 の実測: 登録済み 1,722 op のうち **787 本(46%)に説明が一文も
無かった**。内訳は 2-D レジストリに全部寄っていて、原因は 3 つ ——

1. ``backend_safe.guard`` が ``__doc__`` を転記していなかった(82 本)。実装は
   ちゃんと書いてあるのに、ガードで包んだ瞬間に消えていた。
2. ``backends_typed`` の橋が、カタログ側の説明を捨てていた(143 本)。
3. 残り 562 本は本当に誰も書いていなかった。

1 と 2 は配管の穴で、直せば説明が**戻ってくる**。この 2 つには専用の回帰
テストを置く —— 同じ握り潰しが再発したら「説明が減った」ではなく
「ガードが説明を落とした」と名指しで落ちてほしいから。

3 は書くしかない。ここで数えるのは**填め物ではなく説明があるか**で、
``tools/opdocs.py`` が読むのと同じ経路(``fn.__doc__`` → ``Op.doc``)を見る。
"""
from __future__ import annotations

import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _desc(op) -> str:
    """opdocs が読むのと同じ順で op の説明を引く。"""
    return ((getattr(op.fn, "__doc__", None) or "") or (getattr(op, "doc", "") or "")).strip()


def test_every_2d_op_says_what_it_does():
    """2-D レジストリの全 op に説明がある。

    数字で締める: 説明が無い op が 1 本でもあれば、その名前を全部出して落ちる
    (「何本足りない」だけでは、どれを書けばいいのか分からない)。
    """
    import ops
    gaps = sorted(op.name for op in ops.REGISTRY if not _desc(op))
    assert not gaps, "説明の無い 2-D op が %d 本: %s" % (len(gaps), gaps[:40])


def test_a_description_is_a_sentence_not_a_placeholder():
    """説明が「填め物」でないこと —— 短すぎる/op 名の言い換えだけ、を弾く。

    「説明を書いた」を「文字列を入れた」で満たせてしまうと、カバレッジの数字
    だけが 100% になって読者には何も渡らない(memory: 数える対象を間違えると
    未実行が発見ゼロに化ける、と同じ失敗)。
    """
    import ops
    thin = []
    for op in ops.REGISTRY:
        d = _desc(op)
        head = d.split("\n")[0].strip()
        if len(head) < 20 or head.strip(" .。") == op.name:
            thin.append((op.name, head))
    assert not thin, "説明が短すぎる/op 名の言い換えだけ: %s" % thin[:20]


def test_the_guard_does_not_swallow_the_implementations_description():
    """``guard`` は振る舞いを包むのであって、説明を消してはいけない(82 本の再発防止)。"""
    import backend_safe

    def impl(v, a, b):
        """ここに書いた説明が、ガード越しでも読めること。"""
        return v

    w = backend_safe.guard(impl, "image")
    assert (w.__doc__ or "").strip().startswith("ここに書いた説明が")


def test_the_typed_bridge_carries_the_catalogs_description():
    """橋渡しした op は、渡した先の説明と ``a``/``b`` の割り当てを持つ(143 本の再発防止)。"""
    import ops
    tb = [op for op in ops.REGISTRY if op.name.startswith("tb_")]
    assert tb, "typed bridge の op が 1 つも登録されていない"
    missing = [op.name for op in tb if not _desc(op)]
    assert not missing, "橋の op に説明が無い: %s" % missing[:20]
    # 橋である事実(元の op 名)と、a/b が何を振るかが本文に出ていること
    sample = next(op for op in tb)
    body = _desc(sample)
    assert sample.name[3:] in body, "元の op 名が説明に出ていない: %s" % sample.name
    assert "``a``" in body or "調整点は無く" in body or "no tunable" in body


def test_every_auto_spec_carries_its_own_description():
    """spec 駆動の op は spec が説明の置き場 —— 空欄を残さない。

    ``backends_auto`` の op は generic な shape から組み立てるので、実装の
    そばに docstring を書く場所が無い。spec に書かなければ**どこにも無い**。
    """
    import backends_auto
    holes = [s.get("halcon", "?") for s in backends_auto.load_specs()
             if not (s.get("doc") or "").strip()]
    assert not holes, "doc の無い auto spec が %d 件: %s" % (len(holes), holes[:30])


def test_seed_rows_have_the_description_column():
    """SEED の行は 7 要素 (halcon, category, in, out, shape, params, doc)。"""
    import backends_auto
    bad = [s[0] for s in backends_auto.SEED if len(s) != 7]
    assert not bad, "6 要素のままの SEED 行: %s" % bad[:30]


def test_the_shipped_spec_mirror_matches_the_json():
    """wheel に載る ``auto_specs_data.py`` が JSON と一致していること。

    説明を JSON にだけ書いて mirror を再生成し忘れると、**editable では説明が
    あるのに pip install したら消える**。ここが気付く唯一の場所。
    """
    src = os.path.join(ROOT, "data", "auto_specs")
    if not os.path.isdir(src):
        pytest.skip("data/auto_specs/ が無い(wheel 実行)")
    want = []
    for fn in sorted(os.listdir(src)):
        if fn.endswith(".json"):
            with open(os.path.join(src, fn), encoding="utf-8") as f:
                want.extend(json.load(f))
    from auto_specs_data import AUTO_SPECS
    assert AUTO_SPECS == want, ("auto_specs_data.py が古い —— "
                                "`py -3.11 gen_auto_specs_data.py` を実行すること")


def test_backend_doc_tables_do_not_name_ops_that_do_not_exist():
    """backend の ``DOCS`` に、登録されていない op 名が残っていないこと。

    op の名前を変えたのに ``DOCS`` を直し忘れると、**説明が黙って外れる**
    (キーが一致しないだけなので誰も落ちない)。
    """
    import ops
    live = {op.name for op in ops.REGISTRY}
    stale = {}
    for mod in sorted({"backends", "backends_pil", "backends_color", "backends_kornia",
                       "backends_ski2", "backends_scipy", "backends_extra"}):
        try:
            m = __import__(mod)
        except Exception:
            continue
        docs = getattr(m, "DOCS", None) or {}
        gone = sorted(set(docs) - live)
        if gone:
            stale[mod] = gone
    assert not stale, "DOCS に居ない op が残っている: %s" % stale
