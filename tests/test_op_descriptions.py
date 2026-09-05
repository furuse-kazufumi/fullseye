"""すべての op が「何をする op か」を自分で言えること。

2026-09-05 の実測: 登録済み 1,722 op のうち **787 本(46%)に説明が一文も
無かった**。内訳は 2-D レジストリに全部寄っていて、原因は 3 つ ——

1. ``backend_safe.guard`` が ``__doc__`` を転記していなかった(82 本)。実装は
   ちゃんと書いてあるのに、ガードで包んだ瞬間に消えていた。
2. ``backends_typed`` の橋が、カタログ側の説明を捨てていた(143 本)。
3. ``backends_regions3`` / ``backends_segment2`` / ``backends_subpix`` /
   ``backends_measure1d`` が ``build()`` 内に**自前のラッパ**を持っていて、
   そこでも同じ握り潰しが起きていた(28 本)。
4. 残りは本当に誰も書いていなかった(562 本)。

1〜3 は配管の穴で、直せば説明が**戻ってくる**。ここが本題:
**「仕組みがある」は「全経路が通る」ではない**。guard を直した時点では
直ったつもりだったが、同型のラッパ族はほかに 5 つあり、そのうち 4 つが
同じ穴を持っていた。だから個別の回帰テストに加えて、
:func:`test_no_wrapper_family_swallows_the_description` で**族を数える**。

4 は書くしかない。ここで数えるのは**填め物ではなく説明があるか**で、
``tools/opdocs.py`` が読むのと同じ経路(``Op.doc`` → ``fn.__doc__``)を見る。
順番が ``Op.doc`` 優先なのは、汎用ファクトリが返す**共有の関数オブジェクト**
の docstring を 56 op で使い回してしまうのを避けるため(``backends_r3``)。
"""
from __future__ import annotations

import json
import os
import sys

import pytest

from conftest import requires_backend

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _desc(op) -> str:
    """opdocs が読むのと同じ順で op の説明を引く。"""
    return ((getattr(op, "doc", "") or "") or (getattr(op.fn, "__doc__", None) or "")).strip()


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
    requires_backend('torch', 'kornia', 'mahotas', 'cv2.xfeatures2d')
    import ops
    live = {op.name for op in ops.REGISTRY}
    stale = {}
    for mod in _DOC_TABLE_MODULES:
        try:
            m = __import__(mod)
        except Exception:
            continue
        docs = getattr(m, "DOCS", None) or {}
        gone = sorted(set(docs) - live)
        if gone:
            stale[mod] = gone
    assert not stale, "DOCS に居ない op が残っている: %s" % stale


#: ``DOCS`` 表を持ちうる backend。増えたらここに足す(足し忘れは
#: :func:`test_every_doc_table_module_is_listed` が拾う)。
_DOC_TABLE_MODULES = (
    "backends", "backends_pil", "backends_color", "backends_kornia",
    "backends_ski2", "backends_scipy", "backends_extra", "backends_r3",
    "backends_regions3", "backends_segment2", "backends_subpix",
    "backends_measure1d", "backends_macro",
)


def test_every_doc_table_module_is_listed():
    """``DOCS`` を持つ backend が上の一覧から漏れていないこと。"""
    import glob
    import re
    missing = []
    for path in sorted(glob.glob(os.path.join(ROOT, "backends*.py"))):
        mod = os.path.splitext(os.path.basename(path))[0]
        if mod in _DOC_TABLE_MODULES:
            continue
        with open(path, encoding="utf-8") as f:
            if re.search(r"^DOCS\s*[:=]", f.read(), re.M):
                missing.append(mod)
    assert not missing, "DOCS を持つのに一覧に無い backend: %s" % missing


def test_no_wrapper_family_swallows_the_description():
    """op を包むラッパ族が、どれも ``__doc__`` を落とさないこと。

    2026-09-05 の教訓: ``guard`` を直しても足りなかった —— 同型のラッパは
    ``backend_safe.guard`` / ``backends_typed._make_runner`` / ``backends_r3._make``
    / regions3・segment2・subpix・measure1d の自前ラッパ、と**族が 6 つ**あり、
    4 つが同じ穴を持っていた。**仕組みの有無ではなく族を数える**
    (memory: 同型ラッパの家族数を数える。24 中 1 だった、の再来を防ぐ)。

    検査のしかた: 説明を持つ実装関数を各族のラッパに通して、ラッパ越しに
    説明が読めるかを見る。族の実体はレジストリから機械的に集めるので、
    新しい族が増えたら**登録した瞬間にここへ現れる**。
    """
    import collections
    import inspect
    import ops

    def impl(v, a, b):
        """ラッパ越しでも読めるべき説明。"""
        return v

    fams = collections.defaultdict(list)
    for op in ops.REGISTRY:
        q = getattr(op.fn, "__qualname__", "")
        if "<locals>" in q:
            src = os.path.basename(inspect.getsourcefile(op.fn) or "?")
            fams[(src, q.split(".<locals>")[0])].append(op)
    # ラッパで包まれた op は全体の大半。族が数えられなくなったら検出が壊れている
    assert len(fams) >= 6, "ラッパ族の検出が壊れている(%d 族しか見えない)" % len(fams)
    assert sum(len(v) for v in fams.values()) > 500, "包まれた op が急に減った"

    # **族の全員**を見る。代表 1 本だけだと、DOCS のキー打ち間違いで 2 本目以降が
    # 空になっても素通りする(Codex の敵対レビューで指摘された穴、2026-09-05)。
    blind = {}
    for (src, key), members in sorted(fams.items()):
        gone = [op.name for op in members if not _desc(op)]
        if gone:
            blind["%s:%s" % (src, key)] = "%d/%d 本が無説明 %s" % (
                len(gone), len(members), gone[:6])
    assert not blind, "説明を落としているラッパ族: %s" % blind

    # guard は直接も検査する(族の代表が偶然 DOCS を持っていても見逃さない)
    import backend_safe
    assert (backend_safe.guard(impl, "image").__doc__ or "").strip().startswith("ラッパ越し")


def test_the_two_nonfinite_ledgers_agree():
    """「非有限が正しい」op の一覧が、本体とテストで一致していること。

    2026-09-05: 全 op を ``guard`` で包んだとき、``sanitize`` が
    **非有限を有限に潰す**ので、「inf が正解」の op を除外する必要が出た。
    ところが除外表を 2 箇所(``ops.NONFINITE_IS_MEANINGFUL`` と
    ``tests/test_backends_typed_liveness.KNOWN_NONFINITE_BY_CONTRACT``)に
    分けて持つと、**片方だけ更新して静かにずれる**。
    実際に `tb_mat_cond` を取りこぼし、既存のテストに拾われた。
    """
    import importlib.util
    import ops
    path = os.path.join(HERE, "test_backends_typed_liveness.py")
    spec = importlib.util.spec_from_file_location("_liveness", path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:                              # noqa: BLE001
        pytest.skip("liveness テストが読めない: %s" % exc)
    a = set(ops.NONFINITE_IS_MEANINGFUL)
    b = set(mod.KNOWN_NONFINITE_BY_CONTRACT)
    assert a == b, ("非有限の除外表がずれている —— ops 側だけ: %s / テスト側だけ: %s"
                    % (sorted(a - b), sorted(b - a)))
