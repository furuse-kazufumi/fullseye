# -*- coding: utf-8 -*-
"""チェックポイント unpickler の信頼境界。

2026-09-05 のセキュリティ監査で見つかった実物の穴の回帰テスト。
`_CkptUnpickler.find_class` が `super().find_class` を**先に**呼んでいたため、
import できるモジュールの属性がすべて実物として解決され、
`pickle.load()` の最中に任意コードが走った(実測で確認)。

このモジュールは出荷対象(`pyproject.toml` の py-modules)で、
`fullseye3d.g1_walk_policy()` と op 名 `g1_walk_policy` の両方から到達する。
RL のチェックポイントは**他人から貰う**前提の成果物なので、
「自分のファイルしか開かない」では守れない。

ここで固定するのは 3 つ:
  1. 危険なモジュールは**実物を返さない**
  2. 拒否は**黙ってスタブ**ではなく例外(黙って成功する検査は無い検査より悪い)
  3. 許可モジュールが未インストールのときのスタブ化は**壊さない**(元の設計意図)
"""
from __future__ import annotations

import io
import os
import pickle
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

G = pytest.importorskip("g1_policy_bridge")


@pytest.mark.parametrize(("module", "name"), [
    ("os", "system"),
    ("subprocess", "Popen"),
    ("builtins", "eval"),
    ("builtins", "exec"),
    ("shutil", "rmtree"),
    ("io", "open"),
    ("posix", "system"),
    ("nt", "system"),
])
def test_a_dangerous_callable_is_never_resolved(module, name):
    """危険な callable は実物として返らない。**例外で拒否**する。"""
    u = G._CkptUnpickler(io.BytesIO(b"."))
    with pytest.raises(pickle.UnpicklingError) as ei:
        u.find_class(module, name)
    assert module in str(ei.value), "拒否理由にモジュール名が出ていない"


def test_loading_a_hostile_checkpoint_does_not_execute_code(tmp_path):
    """悪意ある pickle を読んでも副作用が起きない(end-to-end)。

    ペイロードは `builtins.open` を呼んでファイルを作るだけの無害なもの。
    修正前はこのファイルが**実際に出来た**。
    """
    marker = tmp_path / "SHOULD_NOT_EXIST.txt"

    class Evil:
        def __reduce__(self):
            return (open, (str(marker), "w"))

    blob = pickle.dumps(Evil())
    with pytest.raises(pickle.UnpicklingError):
        G._CkptUnpickler(io.BytesIO(blob)).load()
    assert not marker.exists(), "拒否したはずなのに副作用が起きている"


def test_a_missing_training_class_still_falls_back_to_a_stub():
    """許可モジュールが入っていないときのスタブ化は元の設計意図。壊さない。"""
    u = G._CkptUnpickler(io.BytesIO(b"."))
    cls = u.find_class("brax.training.definitely_not_installed", "SomeState")
    assert issubclass(cls, G._Stub), "brax 不在時のスタブ経路が壊れている"


def test_the_allow_list_actually_covers_the_arrays_a_checkpoint_holds():
    """numpy の再構築経路は通らないと、正規のチェックポイントが読めない。"""
    u = G._CkptUnpickler(io.BytesIO(b"."))
    got = u.find_class("numpy", "dtype")
    assert got is not None and not (isinstance(got, type) and issubclass(got, G._Stub))


def test_dunder_attributes_are_refused_even_inside_the_allow_list():
    """許可モジュールでも dunder 属性はペイロードのクラスではない。"""
    u = G._CkptUnpickler(io.BytesIO(b"."))
    with pytest.raises(pickle.UnpicklingError):
        u.find_class("numpy", "__loader__")
