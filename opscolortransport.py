# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opscolortransport —— **分布を運ぶ** op の統一レジストリ。

実体は :mod:`colortransport`。:mod:`opsimgmetrics` と**対**になる台帳で、
あちらが「どれだけ違うか**を測る**」なら、こちらは「相手に**合わせる**」。

## 外部・解析的な基準で裏が取れているもの

=========================  ===============================================
op                         答え合わせの出所(実測値)
=========================  ===============================================
``wasserstein_1d``         総当たりの割当問題(``linear_sum_assignment``)
                           と **差 0.00e+00 / 1.78e-15 / 1.11e-15**
                           (n = 5 / 20 / 50)
``poisson_blend``          構成上の不変量 2 つ。内部のラプラシアンが元と
                           **1.78e-15**、マスク外は貼り先と**厳密一致**
``histogram_match``        出力の分布が参照と厳密一致(順位を保つ単調写像)
``transport_plan_1d``      行和 = 1/n・列和 = 1/m が構成上厳密
``sinkhorn``               ``reg`` を下げると厳密解へ単調に近づく
=========================  ===============================================

## 「厳密」と「近似」を型で分けなかった理由

分けたくなるが、分けていない。``wasserstein_1d`` と ``sinkhorn_distance`` は
どちらも ``scalar`` を返す ―― **型では防げない**種類の取り違えだからで、
代わりに **op 名そのもの**に書いた(``sinkhorn_`` で始まるものは正則化つき)。
判断の根拠は ``sinkhorn_distance`` の実測:自分自身との「距離」が
``reg=0.2`` で **0.05 を超える**(厳密なら 0)。この偏りは値を見ても
気づけないので、名前と docstring で言うしかない。

## この族が黙って間違う場所(台帳から引ける)

``SILENT_FAILURES`` を参照。いずれも**例外が出ない**もの:

* ``color_transfer(method="reinhard")`` —— 単峰の正規分布を仮定している。
  二峰の絵では**平均も標準偏差も参照にぴたり合うのに分布は遠い**
  (実測: 同じ 2 枚でヒストグラム整合なら 1e-6 未満まで詰まるのに、
  Reinhard は 20 倍以上離れたまま)。
* ``color_transfer(method="histogram")`` —— 各軸の周辺分布は完璧に一致する
  のに**チャネル間の相関は元のまま**(実測: 相関 0 の参照に合わせても
  出力の R-G 相関は 0.9 超)。相関ごと運ぶなら ``"gaussian"``。
* ``poisson_blend`` —— **貼った物の色が変わる**のが目的の処理。貼った物体の
  色を測る用途に流すと、測っているのは貼り先の色になる。

使い方::

    import opscolortransport
    opscolortransport.list_ops("transport")
    opscolortransport.call("histogram_match", src, ref)
    opscolortransport.silent_failures("color_transfer")
"""
import colortransport

_MOD = {"colortransport": colortransport}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
# 新語彙は **transport_plan** の 1 つだけ(理由は下の NEW_SORTS)。
_CATALOG = {
    # 分布どうしの距離と計画。1 次元は厳密
    "transport": [
        ("wasserstein_1d", "colortransport", ["signal", "signal"], "scalar"),
        ("transport_plan_1d", "colortransport", ["signal", "signal"], "transport_plan"),
        ("sinkhorn", "colortransport", ["signal", "signal", "matrix"], "transport_plan"),
        ("sinkhorn_distance", "colortransport", ["signal", "signal", "matrix"], "scalar"),
        # 正則化の偏りを自分自身との距離で打ち消した版(自己距離が 0 に戻る)
        ("sinkhorn_divergence", "colortransport", ["signal", "signal", "matrix"], "scalar"),
    ],
    # **輸送計画を消費する側**。2026-09-02 の点検まで transport_plan は
    # 産む op が 2 つ・食う op が 0 の袋小路だった(この repo が繰り返し
    # 踏んできた「入口はあるが消費 op が無い型」の形)。
    "plan_use": [
        ("transport_cost", "colortransport", ["transport_plan", "matrix"], "scalar"),
        ("apply_transport", "colortransport", ["transport_plan", "signal"], "signal"),
    ],
    # 分布を合わせる
    "matching": [
        ("histogram_match", "colortransport", ["image2d", "image2d"], "image2d"),
        ("color_transfer", "colortransport", ["rgbimage", "rgbimage"], "rgbimage"),
        ("gaussian_transport_map", "colortransport", ["points", "points"], "matrix"),
    ],
    # 勾配場を運ぶ
    "blend": [
        ("poisson_blend", "colortransport", ["image2d", "image2d", "mask"], "image2d"),
    ],
}


#: 素の返りと台帳の宣言型のズレを吸収する表(連鎖ファザーが使う)。
#:
#: ``gaussian_transport_map`` は ``(A, m1, m2)`` の 3 つ組を返すのに、台帳は
#: ``matrix`` を宣言していた —— **2026-09-02 に台帳をファザーへ登録した瞬間に
#: TYPEMISS で露見**した(それまでこの族はファザーが一度も実行していなかった)。
#: 写像を当てるには 3 つとも要るので返り自体は変えず、宣言型の ``matrix`` を
#: 取り出す adapter を置く。**全部が欲しいときはモジュールを直接呼ぶ**。
RESULT_ADAPTERS = {
    "gaussian_transport_map": lambda r: r[0] if isinstance(r, tuple) else r,
}


def _build():
    reg = {}
    for cat, entries in _CATALOG.items():
        for name, mod, ins, out in entries:
            reg[name] = {
                "category": cat,
                "module": mod,
                "in": list(ins),
                "out": out,
                "func": getattr(_MOD[mod], name, None),
            }
    return reg


OPSCOLORTRANSPORT = _build()


#: 新設した型と、既存語彙と混ぜたときに**例外でなく何が起きるか**。
NEW_SORTS = {
    "transport_plan": (
        "matrix と混ぜると、行和・列和が周辺分布に一致するという意味が落ちる。"
        "普通の行列として正規化や転置を掛けると、質量保存が壊れたものが"
        "『輸送計画』の顔で下流へ流れる(形も dtype も matrix と同じなので"
        "例外にはならない)"
    ),
}

#: 例外が出ないまま間違う場所。台帳から引けるようにしておく。
SILENT_FAILURES = {
    "color_transfer": [
        {
            "when": 'method="reinhard" を二峰の絵に掛けたとき',
            "what": "平均と標準偏差は参照にぴたり合うのに、分布そのものは遠い",
            "measured": "同じ 2 枚で histogram なら W1 < 1e-6、reinhard は 20 倍以上離れたまま",
            "instead": 'method="histogram"(分布を合わせる)か "gaussian"(相関ごと運ぶ)',
        },
        {
            "when": 'method="histogram" を相関のある絵に掛けたとき',
            "what": "各軸の周辺分布は完璧に一致するが、チャネル間の相関は元のまま",
            "measured": "相関 0 の参照に合わせても出力の R-G 相関は 0.9 超",
            "instead": 'method="gaussian"(共分散ごと運ぶ Monge 写像)',
        },
    ],
    "sinkhorn_distance": [
        {
            "when": "厳密な距離として読んだとき",
            "what": "正則化のぶん系統的に偏る。自分自身との距離も 0 にならない",
            "measured": "reg=0.2 で自分自身との距離が 0.05 超",
            "instead": "1 次元なら wasserstein_1d(厳密)",
        },
    ],
    "poisson_blend": [
        {
            "when": "貼った物体の色を測る用途に流したとき",
            "what": "貼った物の色は変わる(それが目的の処理)ので、測っているのは貼り先の色",
            "measured": "明るい物(0.9)を暗い場所(0.1)に貼ると内部の平均は 0.3 未満へ",
            "instead": "色を測るなら合成前の src を測る。動いた量は返り値の info に出る",
        },
    ],
    "histogram_match": [
        {
            "when": "bins を指定したとき",
            "what": "累積分布を段で近似するので厳密でなくなる",
            "measured": "bins=16 で参照分布との最大差が 1e-3 を超える",
            "instead": "bins=None(既定・厳密)",
        },
    ],
}


def list_ops(category=None):
    """op 名の一覧(カテゴリ指定可)。"""
    if category is None:
        return sorted(OPSCOLORTRANSPORT)
    return sorted(n for n, m in OPSCOLORTRANSPORT.items() if m["category"] == category)


def categories():
    """カテゴリ一覧。"""
    return sorted({m["category"] for m in OPSCOLORTRANSPORT.values()})


def get(name):
    """op 名 → 実体(callable)。"""
    return OPSCOLORTRANSPORT[name]["func"]


def call(name, *args, **kwargs):
    """op を実行する。"""
    return OPSCOLORTRANSPORT[name]["func"](*args, **kwargs)


def info(name):
    """op のメタ情報。"""
    return OPSCOLORTRANSPORT[name]


def missing():
    """台帳にあるが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSCOLORTRANSPORT.items() if m["func"] is None]


def silent_failures(name=None):
    """例外が出ないまま間違う場所(:data:`SILENT_FAILURES`)。"""
    return SILENT_FAILURES if name is None else SILENT_FAILURES.get(name, [])


if __name__ == "__main__":     # pragma: no cover - 手元確認用
    print(f"opscolortransport: {len(OPSCOLORTRANSPORT)} ops / {len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
    n = sum(len(v) for v in SILENT_FAILURES.values())
    print(f"例外が出ないまま間違う場所: {n} 件 / {len(SILENT_FAILURES)} op")
    for op, items in SILENT_FAILURES.items():
        for it in items:
            print(f"  {op:22s} {it['when']}")
            print(f"  {'':22s}   -> {it['measured']}")
