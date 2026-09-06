# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsmeasure1d —— 測定線・測定モデルによるサブピクセル計測の統一レジストリ。

実体は 2 モジュール(14 op / 3 カテゴリ。numpy と scipy のみ):

* ``measuring1d.py`` —— 測定線(矩形・円弧)に沿ってエッジをサブピクセルで取り、
  対にして幅を出す。工業検査でいうキャリパー。
* ``metrology.py`` —— 直線・円・矩形・楕円の当てはめをモデルとして持ち、
  1 枚の画像へまとめて適用する。

## なぜ台帳に載せたか —— 見えていなかったから、ただし測ってから

2026-09-06、この 2 モジュールが**公開経路のどこからも呼べない**ことが分かった
(``fs.`` / ``fs.ledger.`` / ``fs.op.`` のいずれからも 0/14)。同じ日に、同じく
埋もれていた ``mosaic`` を実測したところ ``bundle_adjust_mosaic`` が 36 枚中
30 枚を単位行列で返す(束調整ではない)ことが分かったので、**出す前に実地で
測る**方針を取った(``examples/poc_dimensional_inspection.py``)。

結果は **14/14 が動作**。ゼロ点(大津の整数幅)比 **41 倍**、スロット幅 50.50 px の
偏りが −0.5000 → **−0.0113 px**。合成不確かさ u_c = 0.0196 px = 0.245 um。
``mosaic`` とは違い、これは出す価値がある。

## 出す前に知っておくこと(実測)

1. **斜めの測定線に cos 補正は入っていない**。測定値 / 真値が 1/cos に一致する
   (70 度で 2.9105 対 2.9238)。呼ぶ側が掛ける。
2. **エッジが近いと幅は必ず大きく出る**。壊れるのは「ぼけ」ではなく
   **エッジ間距離 / PSF 幅**で、3.09 を切ると偏り > 0.05 px。しかも
   w/sigma 1.58 まで「対が見つかった」と答え続ける = **失敗を返さない**。
3. **``measure_pairs`` は極性が交互なら順序を問わない**(docstring は
   「立ち上がり→立ち下がり」と読める)。明るい構造の幅を期待して呼ぶと
   暗い構造の幅が返ることがある。``transition`` 引数が無いので選べない。
4. **``metrology`` の矩形は往復しない**。``add`` は (phi, l1, l2) を受けるが
   ``apply`` は l1 >= l2 に正規化して返すので、l1 < l2 で入れると phi が
   90 度回る(実測: 入力 phi=0/l1=25.25/l2=55.00 → 出力 phi=−90.00/
   l1=55.020/l2=25.256)。
5. **矩形当てはめは最小面積外接矩形**(凸包の極値点のみ)。60 点中 1 点を
   1.5 px 外へ動かすと幅が +1.50 px 動く(最小二乗なら 0.050 px)。
   ただし rms が 0.022 → 0.734 に上がるので **rms を必ずゲートにすること**。

**登録面は 6 つ**: この台帳 / ``tools/opdocs.LEDGER_DIMS`` / ``typed_catalog`` /
``chain_fuzz.TYPE_CHECKS`` の述語 / ``opassist._LEDGERS`` / ``pyproject``。
"""
import measuring1d
import metrology

_MOD = {"measuring1d": measuring1d, "metrology": metrology}

# --------------------------------------------------------------------------- #
# 型語彙: **新語を 2 つ**。その判断の記録。
# --------------------------------------------------------------------------- #
# 基準はこの repo 共通の 1 つ ——「混ぜたときに例外ではなく、もっともらしく
# 間違った数値が出るか」。加えて**生産者と消費者が族の中に両方いるか**。
#
#   * ``measurehandle`` = 測定線の定義(``{"type","origin","dir","rows","cols",
#     "spacing","shape",...}``)。``table``(list か dict)の述語には当たるが、
#     ``table`` プールには測定結果の dict も粗さパラメータの dict も入る。
#     それを ``measure_pos`` に渡すと KeyError で落ちる —— つまり「静かに
#     間違う」ではなく「族の 4 op が例外で終わる」ほうの害になる。
#     生産者 ``gen_measure_rectangle2`` / ``gen_measure_arc``、消費者
#     ``measure_pos`` / ``measure_pairs`` / ``fuzzy_measure_pairing`` /
#     ``translate_measure`` が族内に揃っている。
#
#   * ``metrologymodel`` = ``{"objects": [...]}``。同上。生産者
#     ``create_metrology_model`` / ``align_metrology_model``、消費者は
#     ``add_metrology_object_*`` 5 本と ``apply_metrology_model``。
#
#   * 測定結果(list[dict])は既存の ``table`` で足りる。**分けない** ——
#     後段でこれを食う op がこの族に無いので、型を作るとプールが痩せるだけ。
#
# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    # 測定線 —— どこを、どの向きに、どれだけの幅で見るか。
    "caliper": [
        ("gen_measure_rectangle2", "measuring1d", [], "measurehandle"),
        ("gen_measure_arc", "measuring1d", [], "measurehandle"),
        ("translate_measure", "measuring1d", ["measurehandle"], "measurehandle"),
        ("measure_pos", "measuring1d", ["image2d", "measurehandle"], "table"),
        ("measure_pairs", "measuring1d", ["image2d", "measurehandle"], "table"),
        ("fuzzy_measure_pairing", "measuring1d", ["image2d", "measurehandle"], "table"),
    ],
    # 計測モデル —— 図形をまとめて登録する。
    "model": [
        ("create_metrology_model", "metrology", [], "metrologymodel"),
        ("add_metrology_object_line_measure", "metrology", ["metrologymodel"], "scalar"),
        ("add_metrology_object_circle_measure", "metrology", ["metrologymodel"], "scalar"),
        ("add_metrology_object_rectangle2_measure", "metrology", ["metrologymodel"], "scalar"),
        ("add_metrology_object_ellipse_measure", "metrology", ["metrologymodel"], "scalar"),
        ("add_metrology_object_generic", "metrology", ["metrologymodel"], "scalar"),
    ],
    # 適用 —— 画像へ当てて当てはめ結果を返す。
    "apply": [
        ("align_metrology_model", "metrology", ["metrologymodel"], "metrologymodel"),
        ("apply_metrology_model", "metrology", ["metrologymodel", "image2d"], "table"),
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


OPSMEASURE1D = _build()

#: 宣言 out 型と素の返りの橋渡し。**意図的に空** —— 14 op すべてが宣言どおりの
#: 値を 1 つだけ返すことを実測で確認した(2026-09-06)。``add_metrology_object_*``
#: は index(int)を返しつつ model を**その場で書き換える**ので、返り値だけを
#: 見ると副作用が見えない。台帳では返り値の型(scalar)を正直に宣言し、
#: 書き換えられた model は呼び手が持っているものを使う。
RESULT_ADAPTERS = {}


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSMEASURE1D.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


def get(name):
    """op 名 → 実体(callable、素の返り型)。"""
    return OPSMEASURE1D[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、**台帳の宣言 out 型どおりの値**を返す(adapter 適用)。"""
    result = OPSMEASURE1D[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSMEASURE1D[name]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSMEASURE1D.items() if m["func"] is None]


if __name__ == "__main__":
    print("opsmeasure1d: %d ops / %d categories"
          % (len(OPSMEASURE1D), len(categories())))
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
    for cat in categories():
        print("  %-8s %s" % (cat, ", ".join(list_ops(cat))))
