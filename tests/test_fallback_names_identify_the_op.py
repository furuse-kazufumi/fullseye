# -*- coding: utf-8 -*-
"""劣化を記録したとき、**どの op か**が分かること。

`backend_safe.guard` は記録名を「明示の name → ファサードが実行中の op
(`current_op`) → 関数の ``__qualname__``」の順で決める。ギャラリーや進化ループの
ように**ファサードを通さず ``op.fn(...)`` を直に呼ぶ**経路では最初の 2 つが無いので、
`build.<locals>._hog` のような**工場関数のクロージャ名**が記録される。
同じ工場から作られた op は全部同じキーに潰れる。

2026-09-05 の実測(修正前):

======================================  ======
退化入力で全 881 op を直に呼んだとき     値
======================================  ======
劣化の記録                              167 件
相異なるキー                             46
``?`` に潰れた記録                      122 件
======================================  ======

この状態で実際に困った —— ギャラリーが全ゼロ出力のまま緑だったとき、
記録に出るのは `build.<locals>._hog` で、犯人の op 名が分からなかった。

直したのは 2 箇所:
  * `ops._label_guarded_functions_with_their_op_name()` が登録後に
    ``__wrapped__`` の鎖へ本名を書く(実行時コストなし)
  * `backends_typed._make_runner` が ``record(None, ...)`` をやめる
"""
from __future__ import annotations

import os
import sys
import warnings

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import backend_safe as bs                               # noqa: E402
import ops                                              # noqa: E402


def _degrade_everything():
    """退化入力で全 op を**直に**呼び、記録された名前を返す。"""
    bs.clear_fallbacks()
    tiny = np.zeros((4, 4))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for op in ops.REGISTRY:
            try:
                op.fn(tiny, 0.5, 0.5)
            except Exception:                            # noqa: BLE001, S110
                pass
    return [d["name"] for d in bs.fallbacks()]


@pytest.fixture(scope="module")
def names():
    return _degrade_everything()


def test_the_registry_was_actually_labelled():
    """ラベル付けが走っていること(母数を主張する)。"""
    assert ops.OP_NAME_LABELS > 500, (
        "本名を書き込んだ関数が少なすぎる(%d) —— ラベル付けが効いていない"
        % ops.OP_NAME_LABELS)


def test_no_degradation_is_recorded_under_a_factory_closure_name(names):
    """``<locals>`` を含むキーが 1 つも無いこと。"""
    bad = sorted({n for n in names if "<locals>" in n})
    assert not bad, (
        "工場関数のクロージャ名で記録されている(どの op か分からない): %s" % bad[:10])


def test_no_degradation_is_recorded_as_an_unknown_op(names):
    """``?`` が 1 つも無いこと(名前を渡し忘れた record の跡)。"""
    n = sum(1 for x in names if x == "?")
    assert n == 0, "名前なしで記録された劣化が %d 件ある" % n


def test_every_recorded_name_is_a_real_op(names):
    """記録名が**実在の op 名**であること。綴り違いや加工済みの名前を弾く。"""
    live = {op.name for op in ops.REGISTRY}
    unknown = sorted({n for n in names if n not in live})
    assert not unknown, "レジストリに無い名前で記録されている: %s" % unknown[:10]


def test_the_keys_do_not_collapse(names):
    """記録の件数とキーの数が同じ = 1 件も潰れていない。

    退化入力なので「何件劣化するか」は環境で変わる。だから件数そのものではなく
    **件数とキー数の一致**を見る(潰れが起きた瞬間にだけ差が出る)。
    """
    assert names, "劣化が 1 件も記録されていない —— 検査が空振りしている"
    assert len(set(names)) == len(names), (
        "記録 %d 件がキー %d 個に潰れている" % (len(names), len(set(names))))
