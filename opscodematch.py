# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opscodematch —— 符号系の頑健照合(方向符号・増分符号・選択的相関・放射リーチ)の台帳。

実体は :mod:`codematch`。明るさの値ではなく変化の向きを符号にして比べる照合の族で、
照明の変化・局所のハイライト・部分的な遮蔽で NCC(``find_ncc_model`` / ``ncc_locate``)が
壊れる所でどこまで残り、どこで壊れるかを測るために置く。

* ``orientation_code`` / ``increment_sign`` —— 符号化だけ(画像 → 符号の画像)。
* ``ocm_match`` / ``isc_match`` / ``scc_match`` —— テンプレート照合(画像 2 枚 → 表)。
  座標の規約は ``find_ncc_model`` と同じテンプレート中心。
* ``radial_reach_filter`` —— 背景と現在の画像の比較(画像 2 枚 → 表、前景のマスク)。

平坦なテンプレート・平坦な背景のように**符号が位置や変化を決めない入力では、値を
返さずに ValueError**(NCC はどこかに最大値を作って返してしまう)。

使い方::

    import opscodematch
    opscodematch.list_ops("match")
    opscodematch.call("isc_match", image, template)["row"]
"""
import codematch

_MOD = {"codematch": codematch}

# --------------------------------------------------------------------------
# 型の語彙: 新しい語は作らない(既存の語に収まる)。
# --------------------------------------------------------------------------
#   * image2d — 入力の灰色画像、テンプレート、背景。符号の画像(int16 / uint8 の 2 次元配列)も
#     image2d として返す(符号を明るさとして読む op に流しても、値の範囲が 0..N なので
#     例外にならないが、それは「符号の分布を見る」正しい使い方でもある)。
#   * table   — 照合と RRF は dict を返す(位置・点数・次点との余裕・採点した位置のマスク、
#     RRF は前景・判定した画素・方向ごとの reach)。既存の table 語。
#
# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    # 符号化。照合はこれを内側で使うが、符号そのものを見たい・別の照合に流したい時の口。
    "code": [
        ("orientation_code", "codematch", ["image2d"], "image2d"),
        ("increment_sign", "codematch", ["image2d"], "image2d"),
    ],
    # テンプレート照合。NCC と同じ中心規約・同じ返りの鍵(row / col / score)。
    "match": [
        ("ocm_match", "codematch", ["image2d", "image2d"], "table"),
        ("isc_match", "codematch", ["image2d", "image2d"], "table"),
        ("scc_match", "codematch", ["image2d", "image2d"], "table"),
    ],
    # 背景との比較(変化の検出)。
    "change": [
        ("radial_reach_filter", "codematch", ["image2d", "image2d"], "table"),
    ],
}


def _build():
    reg = {}
    for cat, entries in _CATALOG.items():
        for name, mod, ins, out in entries:
            fn = getattr(_MOD[mod], name, None)
            doc = ""
            if fn is not None and fn.__doc__:
                doc = fn.__doc__.strip().splitlines()[0]
            reg[name] = {"category": cat, "module": mod, "in": ins, "out": out,
                         "func": fn, "doc": doc}
    return reg


OPSCODEMATCH = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSCODEMATCH.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し。**空 —— 意図的に**。6 op はすべて宣言型どおり
#: (2 次元配列 = image2d、dict = table)を素で返す。
RESULT_ADAPTERS = {}


def get(name):
    """op 名 → 実体(callable)。"""
    return OPSCODEMATCH[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、台帳の宣言 out 型どおりの値を返す(adapter 適用)。"""
    result = OPSCODEMATCH[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSCODEMATCH[name]


def missing():
    """台帳にあるのに実体の無い op(空であるべき)。"""
    return [n for n, m in OPSCODEMATCH.items() if m["func"] is None]


if __name__ == "__main__":
    for c in categories():
        print(c, list_ops(c))
    print("missing:", missing())
