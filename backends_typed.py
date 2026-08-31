# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Typed bridge — 型付き op カタログ(ops3d / ops1d / opsmath / opsoptics)を
進化レジストリ(``ops.py``)の語彙に接続する。

**なぜ要るか(実測 2026-09-01)**: fullseye には op の宇宙が 2 つあった。

  * ``ops.py`` の ``REGISTRY`` — 742 op。進化(``evolve.py`` / ``robust.py``)が
    探索する空間。``fn(v, a, b)`` 規約、sort は image/region/feature/contour/…
  * 型付きカタログ — 382 op(3d 310 / 1d 34 / math 26 / 2d 12)。連鎖ファザーと
    facade が使う。宣言された入出力型を持つ多引数 API。

**この 2 つは名前が 3 個しか重なっていなかった**。つまり進化は点群 op も 1-D op も
数学 op も一度も組み合わせたことがなく、自己拡張レジストリ(``backends_macro``)も
狭い方の宇宙でしか育っていなかった。本モジュールはその橋を架ける。

**安全性の根拠**: ``ops._candidates(sort)`` は ``in_sort`` で絞るだけなので、
**既存 sort の候補リスト長を変えなければ**ゲノム→op の写像は不変
(``docs/WAVE0_STABLE_SLOTS.md``: 長さが変わると既存 champion を黙って書き換える)。
そこで既定では **入力 sort が新設のもの(points / signal / matrix / cimage)だけ**を
登録する。出力 sort は既存でも構わない — 候補リストの絞り込みは入力側でしか
行われないため。既存 sort を入力に取る op(voxel / image2d / …)は
``IMGEVOLVE_WIDE_VOCAB=1`` の **opt-in** でのみ加わる(黙って広げない)。

**引数の束縛**: カタログ op は多引数だが、進化は ``fn(v, a, b)`` しか渡せない。
必須の追加引数は連鎖ファザーが持つヒント表(``tools/chain_fuzz`` の
``PARAM_HINTS`` / ``OP_PARAM_HINTS``)で束縛する — ファザーが 2000 連鎖で実際に
通していた値なので、机上の既定値ではなく **実績のある束縛**である。束縛できない
必須引数が残る op は登録しない(推測の既定値を捏造しない)。

**a, b ノブ**: 橋渡し op は ``a`` を「ヒント表で束縛したスカラ引数のスケール」に
使わない — ファザーのヒントは固定値であり、そこに勝手な写像を足すと出所不明の
パラメータになる。``a, b`` は **凍結**(``backends_macro`` の DNA op と同じ規約)。
パラメータ探索が要る op は、専用の wrapper を書いて別途登録するのが筋。

**fail-soft**: どの backend も守る契約どおり、実行時例外は入力の sort 妥当な値へ
落とす(進化の適応度計算を 1 op の失敗で止めない)。optional 依存の欠如も同様。
"""
from __future__ import annotations

import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))

#: カタログ型語彙 → ops.py の sort。値が None の型は「進化側に対応する sort が
#: 無い」= 橋を架けない(mesh / primitive / pose / descriptor など構造化された型)。
TYPE_TO_SORT = {
    "voxel": "volume",
    "sdf": "volume",
    "labels": "volume",
    "image2d": "image",
    "depth": "image",
    "measurement": "feature",
    "points": "points",
    "normals": "points",
    "keypoints": "points",
    "signal": "signal",
    "indices": "signal",
    "matrix": "matrix",
    "cimage": "cimage",
}

#: 既定で登録する入力 sort(すべて新設 = 既存の候補リストに触れない)
_NEW_SORTS = frozenset({"points", "signal", "matrix", "cimage"})


def _coerce(value, sort):
    """カタログ op の返りを進化側が扱える形へ正規化する。

    torch backend を持つ op は Tensor を返す(実測: ``edt_jfa``)。進化の
    ``_apply`` は ndarray 前提なので numpy へ落とす。dict/tuple を返す op は
    宣言 out 型に応じてカタログ側の adapter が既に整えている前提で、ここでは
    残る入れ物だけをほどく。
    """
    if hasattr(value, "detach") and hasattr(value, "cpu"):     # torch.Tensor
        value = value.detach().cpu().numpy()
    if isinstance(value, tuple) and value:
        value = value[0]
    if sort == "feature":
        try:
            return float(np.asarray(value, np.float64).ravel()[0])
        except (TypeError, ValueError, IndexError):
            return 0.0
    return np.asarray(value)


def _fallback(v, sort):
    """fail-soft の戻り値: 入力を sort 妥当な形にしたもの(全 backend 共通契約)。"""
    if sort == "feature":
        try:
            return float(np.mean(np.asarray(v, np.float64)))
        except (TypeError, ValueError):
            return 0.0
    return np.asarray(v)


def _make_runner(fn, kwargs, out_sort):
    """``fn(v, a, b)`` 規約のランナー。a, b は凍結(モジュール docstring 参照)。"""
    def _run(v, a, b):                                    # noqa: ARG001 - 規約
        try:
            return _coerce(fn(v, **kwargs), out_sort)
        except Exception:                                 # noqa: BLE001 - fail-soft
            return _fallback(v, out_sort)
    return _run


def _catalog_entries():
    """(name, dim, in_types, out_type, fn) をカタログから集める。

    ``tools/chain_fuzz`` の ``catalog()`` を単一の真実源として使う — カタログの
    定義が増えた(optics 等)ときに、こちらを直さなくても橋が伸びる。
    """
    tools = os.path.join(_HERE, "tools")
    if tools not in sys.path:
        sys.path.insert(0, tools)
    import chain_fuzz                                     # noqa: PLC0415
    return chain_fuzz


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, _norm, _bin):
    """進化レジストリへ足す Op のリストを返す(見つからなければ空)。"""
    try:
        cf = _catalog_entries()
    except Exception:                                     # noqa: BLE001 - optional
        return []
    wide = os.environ.get("IMGEVOLVE_WIDE_VOCAB", "") == "1"
    hint_names = set(cf.PARAM_HINTS)
    out = []
    try:
        entries = cf.catalog()
    except Exception:                                     # noqa: BLE001
        return []
    import inspect                                        # noqa: PLC0415
    rng = np.random.default_rng(0)                        # ヒントは決定的に引く
    for name, dim, ins, out_type, fn in entries:
        if len(ins) != 1:
            continue                                      # 多入力は別の合成モデル
        in_sort = TYPE_TO_SORT.get(ins[0])
        out_sort = TYPE_TO_SORT.get(out_type)
        if in_sort is None or out_sort is None:
            continue
        if in_sort not in _NEW_SORTS and not wide:
            continue                                      # 既存 sort は opt-in のみ
        try:
            sig = inspect.signature(fn)
        except (TypeError, ValueError):
            continue
        params = [p for p in sig.parameters.values()
                  if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
        kwargs, ok = {}, True
        for p in params[1:]:
            if p.default is not inspect.Parameter.empty:
                continue
            hint = cf.OP_PARAM_HINTS.get((name, p.name))
            if hint is None and p.name in hint_names:
                hint = cf.PARAM_HINTS[p.name]
            if hint is None:
                ok = False
                break                                     # 既定値を捏造しない
            val = hint(rng)
            if val is None:
                ok = False
                break
            kwargs[p.name] = val
        if not ok:
            continue
        adapter = cf.ADAPTERS.get(name)
        base = fn if adapter is None else (
            lambda *a, _f=fn, _ad=adapter, **k: _ad(_f(*a, **k)))
        out.append(Op("tb_" + name, "typed", "", in_sort, out_sort,
                      _make_runner(base, kwargs, out_sort)))
    return out
