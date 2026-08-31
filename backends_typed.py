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

**a, b ノブ(実測に基づく設計変更 2026-09-01)**: 最初は ``backends_macro`` の DNA op
に倣って凍結したが、実際に 58 op を走らせると **ノブを凍結した op は進化にとって
調整余地ゼロ**で、既定値が恒等な op(``scale_y_funct_1d`` の ``mult=1.0``)は
文字どおり何もしない枠になっていた。かといって絶対範囲を勝手に決めるのは
「出所不明のパラメータ」の捏造である。

そこで **著者自身が書いた既定値を基準にした相対スケール**だけを許す:

    p = default * (0.25 + 1.75 * knob)      # knob ∈ [0,1] → 既定の 1/4 〜 2 倍

正の数値既定を持つ第 1 引数に ``a``、第 2 引数に ``b`` を割り当てる(整数既定は
整数へ丸め、1 未満にならないよう下限 1)。**根拠は「その op の作者が妥当と考えた
値の近傍」**であって、こちらが発明した範囲ではない。既定を持たない必須引数は
従来どおりファザーのヒント表で束縛し、ノブは繋がない。

*正直な限界*: この相対スケールは「既定値が意味のある中心である」ことを仮定する。
比率でなく加法的な意味を持つ引数(オフセット、しきい値の絶対値)には不適切で、
その場合は探索が無駄になるだけ(誤った結果は出さない — 各 op の入口検証が
不正な値を fail-closed で弾く)。専用の範囲が要る op は個別 wrapper を書くのが筋。

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


def _scaled(default, knob):
    """著者の既定値を中心にした相対スケール(既定の 1/4 〜 2 倍)。

    整数既定は整数へ丸め、最低 1 を保証する(近傍数 k=0 のような無意味な値を
    作らない)。範囲の根拠はモジュール docstring を参照。
    """
    val = float(default) * (0.25 + 1.75 * float(knob))
    if isinstance(default, int):
        return max(1, int(round(val)))
    return val


def _make_runner(fn, kwargs, tunable, out_sort):
    """``fn(v, a, b)`` 規約のランナー。

    *tunable* は ``[(param 名, 既定値), ...]`` を最大 2 個(a に第 1、b に第 2)。
    空なら a, b は未使用(その op には調整点が無い)。
    """
    def _run(v, a, b):
        kw = dict(kwargs)
        for (pname, default), knob in zip(tunable, (a, b)):
            kw[pname] = _scaled(default, knob)
        try:
            return _coerce(fn(v, **kw), out_sort)
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
        kwargs, ok, tunable = {}, True, []
        for p in params[1:]:
            if p.default is not inspect.Parameter.empty:
                # 正の数値既定 = 進化が触れる調整点(最大 2 個を a, b に割り当て)
                if (isinstance(p.default, (int, float))
                        and not isinstance(p.default, bool)
                        and p.default > 0 and len(tunable) < 2):
                    tunable.append((p.name, p.default))
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
                      _make_runner(base, kwargs, tunable, out_sort)))
    return out
