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
    # keypoints は像面上の (N,2)。points((N,3))とは**別 sort**。
    # 2026-09-02 まで points へ写しており、_sort_ok が shape[1]==3 を要求する
    # ため (N,2) を返す/取る op が 4 件まるごと fail-soft に落ちていた。
    "keypoints": "keypoints",
    "signal": "signal",
    "indices": "signal",
    "matrix": "matrix",
    "cimage": "cimage",
    # 光子計数・ライトフィールド族(2026-09-01)。counts と countrate は
    # 進化側では 1 つの sort に畳む — voxel/sdf/labels を volume に、
    # points/normals を points に畳んでいるのと同じ粒度の判断で、
    # 「非負の 1-D」であることが進化にとって意味のある区別のすべてだから。
    # (keypoints も当初この列に入れていたが、**形が (N,2) で points の契約を
    #  満たさない**ため畳めなかった。畳めるかどうかは「意味が近いか」ではなく
    #  「同じ sort の形の契約を両方が満たすか」で決まる ―― 2026-09-02 の教訓。)
    # カタログ側で 2 語に分けてあるのは、型の嘘(ヒストグラムをレート op に
    # 渡す)をファザーに検出させるためで、そちらは別の目的。
    "lightfield": "lightfield",
    "counts": "counts",
    "countrate": "counts",
    "histcube": "histcube",
    # 2026-09-01 後半に足した族。いずれも**族の中に産出 op がある**ので、
    # 消費側だけの死んだ語彙にはならない(実測の消費/産出/自己ループ:
    # rgbimage 4/4/2 · video 9/2/1 · qimage 11/11/6 · beatcube 5/2/1)。
    # polsweep は消費 3・自己ループ 0 で「1 手で外へ出るだけ」に近く、
    # histcube と同じ理由で見送る(選択肢が 3 つある点だけ histcube より良い)。
    "rgbimage": "rgbimage",
    "video": "video",
    "qimage": "qimage",
    "beatcube": "beatcube",
}

#: 既定で登録する入力 sort(すべて新設 = 既存の候補リストに触れない)。
#:
#: **2026-09-01 に一度判断を誤り、実測で訂正した**ので経緯を残す。当初は
#: lightfield / counts / histcube を除外していた。理由は「その族の入口 op
#: (``lf_from_mla``: image2d → lightfield、``dtof_cube_simulate``: depth →
#: histcube)が既存の image sort を入力に取るので、既定に入れると image の
#: 候補リストが動いてゲノム → op の写像が変わる」というものだった。
#:
#: 前半は正しいが**結論が過剰だった**。``_candidates`` は **in_sort でしか
#: 絞らない**ので、除外すべきなのは入口 op(in_sort=image)だけであり、
#: それは in_sort=image が本集合に無いことで既に除外されている。消費側
#: (in_sort=lightfield/counts/histcube)を足しても**動くのは新設 sort の
#: 候補リストだけ**で、既存 sort は 1 件も変わらない。実測 2026-09-01:
#: image 523→523 / region 130→130 / points 33→33 /(全 sort 不変)、
#: レジストリ全体は 809 → 824。
#:
#: 「誰も産まないので死んだ語彙になる」という懸念も、**画像から始まる探索に
#: 限った話**だった。``Problem.in_sort`` がその sort なら入力は課題が供給する
#: ので、入口 op が無くても消費側は生きて動く。実際 counts / lightfield /
#: histcube の課題を足すために、この訂正が必要だった。
#:
#: 入口 op(既存 sort を入力に取るもの)は従来どおり ``IMGEVOLVE_WIDE_VOCAB=1``
#: の opt-in でのみ加わる。そこは変えていない。
#: **histcube は入れない**(2026-09-01 の実測判断)。この sort を消費する op は
#: ``dtof_cube_depth`` 1 つだけで、しかも出口が image なので、既定語彙に入れても
#: 「1 手で外へ出るだけ」= 進化する余地がゼロの死んだ枠になる。課題を足しても
#: 手の基準線と同じ 1 手しか組めない。**使える仕事が無い語彙は足さない**。
#: wide 語彙(IMGEVOLVE_WIDE_VOCAB=1)では従来どおり入る。
_NEW_SORTS = frozenset({"points", "signal", "matrix", "cimage",
                        "lightfield", "counts",
                        "rgbimage", "video", "qimage", "beatcube",
                        "keypoints"})


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


#: sort ごとの**形の契約**。分岐を積むより表に置く —— sort を 1 つ足すたびに
#: ``_sort_ok`` / ``_fallback`` / ``TYPE_TO_SORT`` の 3 箇所へ ``if`` を書き足す形
#: だったので、どこか 1 つ書き忘れても**例外にならず fail-soft に落ちるだけ**で
#: 気づけなかった(keypoints がまさにそれで、4 op が黙って死んでいた)。
#: 表にしておけば「この sort の行が無い」が一目で分かり、テストからも回せる。
_SHAPE_OK = {
    "volume": lambda v: v.ndim == 3,
    "image": lambda v: v.ndim == 2,
    "points": lambda v: v.ndim == 2 and v.shape[1] == 3,
    "keypoints": lambda v: v.ndim == 2 and v.shape[1] == 2,
    "signal": lambda v: v.ndim == 1,
    "matrix": lambda v: v.ndim == 2,
    "cimage": lambda v: v.ndim == 2 and v.dtype.kind == "c",
    # rgbimage = (H,W,3)、qimage = (H,W,4)。2026-09-02 までどちらも行が無く、
    # ``tb_quaternion_to_rgb``(qimage → rgbimage)が失敗すると ``_fallback`` が
    # 表に無い out_sort の既定 ``np.asarray(v)`` = **4 チャンネルの入力をそのまま
    # rgbimage として返していた**(乱数の (H,W,4) は非純四元数なので quatimage 側の
    # 番人が必ず拒否する → 毎回この経路)。同 sort の恒等検査には掛からず、
    # 形の検査にも行が無いので 4 チャンネルがそのまま通った。行を足すと
    # 4 チャンネルの返りは契約違反として弾かれ、失敗時は下の空値へ落ちる。
    "rgbimage": lambda v: v.ndim == 3 and v.shape[2] == 3,
    "qimage": lambda v: v.ndim == 3 and v.shape[2] == 4,
}


def _sort_ok(value, sort):
    """*value* が *sort* の形の契約を満たすか。

    進化の ``_apply`` は sort を信じて次の op を選ぶので、ここで形まで保証しないと
    嘘が下流へ漏れて**無関係な op** で落ちる。ファザーの ``TYPE_CHECKS`` と同じ
    考え方(宣言と実際の一致を機械検証する)を橋の出口にも置く。
    表に無い sort は「形の制約なし」= 配列であれば通す。
    """
    if sort == "feature":
        return isinstance(value, float)
    if not isinstance(value, np.ndarray) or value.dtype.kind not in "fciub":
        return False
    check = _SHAPE_OK.get(sort)
    return True if check is None else bool(check(value))


def _fallback(v, in_sort, out_sort):
    """fail-soft の戻り値。**宣言した out_sort に合う値**でなければならない。

    最初は「入力をそのまま返す」実装だったが、これは **out_sort が in_sort と
    違う op で型の嘘になる**。実測 2026-09-01: points→volume の橋渡し op が
    失敗したとき (N,3) の点群が返り、パイプラインはそれを volume と信じて次の
    ``vol_slice`` が ``IndexError: tuple index out of range`` で落ちた
    (fail-soft のはずが、失敗を 1 段先へ運んで別の場所で壊す形になっていた)。

    同型なら入力を通す(情報を保つ)。型が変わる op では **その sort の最小限
    妥当な値**を返す — 内容は無いが、下流の型契約は満たす。
    """
    if out_sort == "feature":
        try:
            return float(np.mean(np.asarray(v, np.float64)))
        except (TypeError, ValueError):
            return 0.0
    if in_sort == out_sort:
        return np.asarray(v)
    return _EMPTY_OF.get(out_sort, lambda: np.asarray(v))()


#: 型が変わる op の失敗時に返す「中身は無いが sort として妥当な値」。
#: :data:`_SHAPE_OK` と**対**になる表で、片方に行を足したらもう片方にも要る
#: (両方に無いと fail-soft が sort 契約を破り、下流の無関係な op で落ちる)。
_EMPTY_OF = {
    "volume": lambda: np.zeros((2, 2, 2), np.float64),
    "image": lambda: np.zeros((2, 2), np.float64),
    "points": lambda: np.zeros((1, 3), np.float64),
    "keypoints": lambda: np.zeros((1, 2), np.float64),
    "signal": lambda: np.zeros(2, np.float64),
    "matrix": lambda: np.zeros((2, 2), np.float64),
    "cimage": lambda: np.zeros((2, 2), np.complex128),
    "rgbimage": lambda: np.zeros((2, 2, 3), np.float64),
    "qimage": lambda: np.zeros((2, 2, 4), np.float64),
}


def _points_to_grid(v, res=16, margin=0.15):
    """点群 (N,3) → その境界箱を覆う座標格子 (res,res,res,3)。

    ``box_sdf`` / ``sphere_sdf`` は「``(..., 3)`` の座標を受け、その形から最後の軸を
    落として距離を返す」**要素ごと**の op なので、点群 (N,3) を渡すと (N,) が返る。
    宣言している out_sort は ``volume`` なので形の検査に落ち、``_fallback`` が
    ``zeros((2,2,2))`` を返す —— つまりこの 2 op は **候補枠を 2 つ占めたまま、
    どんな入力でも定数ゼロしか返していなかった**(2026-09-02 実測: 40 通りの
    点群すべてで返りが ``zeros((2,2,2))``、非ゼロ 0 件)。

    宣言 ``points → volume`` を素直に読めば「その点群が収まる領域に、この原始形状の
    距離場を焼く」であり、それには**座標格子**が要る。ここで作る。
    ``margin`` は境界箱の外側に取る余白(比率)で、これが無いと形状の外側が
    切れて距離場の符号が片側しか出ない。
    """
    P = np.asarray(v, np.float64)
    if P.ndim != 2 or P.shape[1] != 3 or P.shape[0] < 1 or not np.isfinite(P).all():
        raise ValueError("points must be a finite (N, 3) cloud")
    lo, hi = P.min(axis=0), P.max(axis=0)
    span = np.maximum(hi - lo, 1e-9)
    lo = lo - margin * span
    hi = hi + margin * span
    axes = [np.linspace(lo[k], hi[k], int(res)) for k in range(3)]
    return np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1)


#: 入口の値を op が実際に取れる形へ直す表(op 名 → 変換)。**ADAPTERS が返りを
#: 直すのに対し、こちらは入力を直す**。捏造ではなく、宣言した in_sort の値から
#: op の要求する表現へ写すだけのものに限る。
INPUT_ADAPTERS = {
    "box_sdf": _points_to_grid,
    "sphere_sdf": _points_to_grid,
}


def _point_labels_to_volume(points, labels, res=16):
    """点ごとのラベル ``(N,)`` を、その点群を覆う**ラベル体積** ``(res,res,res)`` にする。

    台帳が ``points → labels`` と宣言する点群セグメンテーション 3 op
    (``region_growing`` / ``euclidean_cluster`` / ``plane_segmentation``)は
    **点ごとの (N,) ラベル**を返す。ところが ``labels`` という型名は、この
    ライブラリでは 3-D のラベル体積も指しており(``TYPE_TO_SORT['labels'] =
    'volume'``)、進化側は 3 次元を要求する。結果、この 3 op は形の検査に落ちて
    ``_fallback`` の ``zeros((2,2,2))`` を返し続けていた —— 2026-09-02 実測で、
    40 通りの点群すべてで返りが定数ゼロ、非ゼロ 0 件。**候補枠を占めながら
    一度も仕事をしていなかった。**

    ファザー側の ``TYPE_CHECKS['labels']`` は 1/2/3 次元すべてを許す緩い述語なので、
    この食い違いは**ファザーからは見えない**。厳しい側(進化の sort 契約)だけが
    弾き、しかも fail-soft なので誰にも気づかれなかった。

    ここでは宣言を動かさずに真にする: 点を境界箱の格子へ落とし、各ボクセルに
    そこへ落ちた点の**最大ラベル**を入れる(空ボクセルは 0)。「点群を分割して
    その区分けを体積に焼く」は素直な読み方で、``points → labels(体積)`` が
    そのまま成り立つ。宣言を変えないので進化の decode(候補リストと out_sort)は
    1 ビットも動かない。
    """
    P = np.asarray(points, np.float64)
    lab = np.asarray(labels).reshape(-1)
    if P.ndim != 2 or P.shape[1] != 3 or lab.size != P.shape[0]:
        raise ValueError("expected (N,3) points and (N,) labels, got %r and %r"
                         % (P.shape, lab.shape))
    r = int(res)
    lo, hi = P.min(axis=0), P.max(axis=0)
    span = np.maximum(hi - lo, 1e-9)
    idx = np.clip(((P - lo) / span * (r - 1)).astype(np.int64), 0, r - 1)
    flat = (idx[:, 0] * r + idx[:, 1]) * r + idx[:, 2]
    # 未割当(負)は 0 に寄せる。ラベルは 1 起点に持ち上げて「空」と区別する。
    vals = np.where(lab < 0, 0, lab.astype(np.int64) + 1)
    vol = np.zeros(r ** 3, np.int64)
    np.maximum.at(vol, flat, vals)
    return vol.reshape(r, r, r).astype(np.float64)


#: 返りを**入力と一緒に**見て直す表(op 名 → ``fn(入力, 返り)``)。
#: ``ADAPTERS`` は返りだけを見るので、入力が要る変換はこちらに置く。
OUTPUT_ADAPTERS_WITH_INPUT = {
    "region_growing": _point_labels_to_volume,
    "euclidean_cluster": _point_labels_to_volume,
    "plane_segmentation": _point_labels_to_volume,
}


def _scaled(default, knob):
    """著者の既定値を中心にした相対スケール(既定の 1/4 〜 2 倍)。

    整数既定は整数へ丸め、最低 1 を保証する(近傍数 k=0 のような無意味な値を
    作らない)。範囲の根拠はモジュール docstring を参照。
    """
    val = float(default) * (0.25 + 1.75 * float(knob))
    if isinstance(default, int):
        return max(1, int(round(val)))
    return val


def _make_runner(fn, kwargs, tunable, in_sort, out_sort):
    """``fn(v, a, b)`` 規約のランナー。

    *tunable* は ``[(param 名, 既定値), ...]`` を最大 2 個(a に第 1、b に第 2)。
    空なら a, b は未使用(その op には調整点が無い)。
    """
    def _run(v, a, b):
        kw = dict(kwargs)
        for (pname, default), knob in zip(tunable, (a, b)):
            kw[pname] = _scaled(default, knob)
        try:
            got = _coerce(fn(v, **kw), out_sort)
        except Exception:                                 # noqa: BLE001 - fail-soft
            return _fallback(v, in_sort, out_sort)
        # 型の嘘も fail-soft と同じ扱い。**形まで検証する**のが要点で、
        # 「ndarray かどうか」では足りない: 宣言 volume の op が 2-D を返すと、
        # 下流の vol_* が「次元が合わない」と落ちて**無関係な場所で**失敗が
        # 顕在化する(実測 2026-09-01: scipy binary_dilation の
        # "structure and input must have same dimensionality")。
        if not _sort_ok(got, out_sort):
            return _fallback(v, in_sort, out_sort)
        return got
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
        pre = INPUT_ADAPTERS.get(name)
        if pre is not None:
            base = (lambda v, *a, _f=base, _pre=pre, **k: _f(_pre(v), *a, **k))
        post = OUTPUT_ADAPTERS_WITH_INPUT.get(name)
        if post is not None:
            base = (lambda v, *a, _f=base, _post=post, **k: _post(v, _f(v, *a, **k)))
        out.append(Op("tb_" + name, "typed", "", in_sort, out_sort,
                      _make_runner(base, kwargs, tunable, in_sort, out_sort)))
    return out
