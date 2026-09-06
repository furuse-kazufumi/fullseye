# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsblob —— 2-D の連結成分解析(blob analysis)op の統一レジストリ。

実体は ``blob2d.py``(10 op / 5 カテゴリ)。台帳の役目は 3 つ:
docs/ops へノートを出す・連鎖ファザーに食わせる・宣言型と素の返りを橋渡しする。

使い方::

    import opsblob
    opsblob.list_ops("measure")
    lab = opsblob.call("blob_label", mask, connectivity=8)

## なぜ族を分けたか(2026-09-06)

相乗りできる先を先に探した。``opsshape2d``(形を記述して写す)は輪郭の
フーリエ記述子とワープで、**扱う対象が「1 つの形」**。こちらは
**「画像に散らばった n 個の物体」**で、生む型も消す型も違う。
``opsregions`` に当たるものは無い(``regions_setops`` / ``regions_gen`` は
台帳を持たない)。混ぜると台帳のカテゴリが「形」と「個数」の二重帳簿に
なるので、独立した 1 族を立てた(2026-09-06 に 7 op で開始、同日 10 op)。

## 型語彙: **新語は 1 つだけ**(``labels2d``)。その判断の記録

基準はこの repo 共通の 1 つ ——「混ぜたときに例外ではなく、もっともらしく
間違った数値が出るか」。加えて**生産者と消費者が族の中に両方いるか**。

* ``labels2d`` = 背景 0・物体 1..n の ``int32`` 画像。既存の ``mask`` の述語
  (2-D で bool か整数)には**当たってしまう**。だが逆向きに見ると:
  ``mask`` を ``blob_features`` に渡すと「別々の 2 個の細胞」が 1 個の物体と
  して測られ、**2 つの中心のあいだに重心が出る** —— 例外にならず、
  もっともらしく間違う。まさに型を分ける条件そのもの。
  そこで ``blob2d._as_labels`` は bool を**直し方つきで拒否**する
  (``blob_label(mask)`` を先に呼べ)。
  生産者 5(``blob_label`` / ``blob_select`` / ``blob_select_largest`` /
  ``blob_seeds`` / ``blob_split``)、消費者 7(``blob_features`` /
  ``blob_select`` / ``blob_select_largest`` / ``blob_split`` /
  ``blob_region`` / ``blob_boundaries`` / ``blob_overlay``)で族の中に閉じる。
  **出口も持たせた**(``blob_overlay`` → ``rgb``)—— 作れるが見られない型は
  連鎖の行き止まりになる(``flow2d`` で学んだ形)。

* 物体ごとの特徴量は ``table``(dict)。鍵ごとに長さ n の配列が入る。
  ``metrics`` は ``contract`` を持つ辞書という別の述語なので名乗らない。

* 1 個を抜いた領域と輪郭は ``mask``(2-D bool)—— 述語どおりで、既存の
  領域 op(集合演算・モルフォロジー)がそのまま使える。**ここは分けない**:
  「1 個の物体の領域」を他の領域と混ぜても、それは領域として正しい。
"""
import blob2d

_MOD = {"blob2d": blob2d}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    # 切る —— 二値領域を物体に分ける。この族の入口。
    "connect": [
        ("blob_label", "blob2d", ["mask"], "labels2d"),
    ],
    # 測る —— 物体ごとの 19 項目
    "measure": [
        ("blob_features", "blob2d", ["labels2d"], "table"),
    ],
    # 選ぶ —— 条件で残す(番号は振り直す)
    "select": [
        ("blob_select", "blob2d", ["labels2d"], "labels2d"),
        ("blob_select_largest", "blob2d", ["labels2d"], "labels2d"),
    ],
    # 割る —— 触れ合って 1 個になった塊を戻す(距離 → 種 → 分水嶺)
    # `poc_cell_counting` と `poc_particle_sizing` が**揃って**挙げた穴。
    # 連結成分は「触れているか」しか見ないので、重なった細胞や粒子は割れない。
    "split": [
        ("blob_distance", "blob2d", ["mask"], "image2d"),
        ("blob_seeds", "blob2d", ["image2d"], "labels2d"),
        ("blob_split", "blob2d", ["labels2d", "labels2d", "image2d"], "labels2d"),
    ],
    # 取り出す/見る —— 1 個を領域として抜く、輪郭、重ね描き(出口)
    "extract": [
        ("blob_region", "blob2d", ["labels2d"], "mask"),
        ("blob_boundaries", "blob2d", ["labels2d"], "mask"),
        ("blob_overlay", "blob2d", ["image2d", "labels2d"], "rgb"),
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


OPSBLOB = _build()

#: 宣言 out 型と素の返りの橋渡し。**この族はどの op もタプルを返さない**ので空。
#: (空であること自体が「調べたうえで要らない」の記録 —— 他の族と同じ体裁)
RESULT_ADAPTERS: dict = {}


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSBLOB.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


def get(name):
    """op 名 → 実体(callable、素の返り型)。"""
    return OPSBLOB[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、**台帳の宣言 out 型どおりの値**を返す(adapter 適用)。"""
    result = OPSBLOB[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSBLOB[name]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSBLOB.items() if m["func"] is None]


if __name__ == "__main__":
    print("opsblob: %d ops / %d categories" % (len(OPSBLOB), len(categories())))
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
    for cat in categories():
        print("  %-9s %s" % (cat, ", ".join(list_ops(cat))))
