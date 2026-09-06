# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsshape2d —— 2-D の形を**記述して写す** op の統一レジストリ。

実体は 2 モジュール(13 op / 2 カテゴリ):

* ``fourierdesc.py`` —— 閉輪郭の楕円フーリエ記述子(EFD)。形を有限個の係数に
  畳んで、回転・平行移動・始点・(任意で)大きさに不変な形で比べる。
* ``imagemorph.py`` —— 対応点(ランドマーク)で駆動する 2-D ワープとモーフ。
  薄板スプラインと区分アフィン。

## なぜ台帳を足したか(2026-09-06)

この 2 モジュールは**実装も専用テストも揃っていた**(``tests/test_fourierdesc.py``
と ``tests/test_fix_op_name_and_range_2026_09_02.py`` で 7/7・6/6 が実際に
呼ばれていた)のに、``fullseye.<名前>`` にも ``fullseye.ledger.<名前>`` にも
``fullseye.op.<名前>`` にも**一つも出ていませんでした**。呼んでいたのは
``tools/gen_*_gallery.py`` と tests だけ。つまり利用者から見ると存在しない。

``docs/ops`` の drift 検査も op→example のカバレッジも、**すでに登録された op**
を数える門なので、登録されなかったものは母集団にすら入らず、全部緑のまま
気づけませんでした。同じ形の穴を数える門を
``tests/test_public_reachability.py`` に立ててあります。

**登録面は 6 つ**: この台帳 / ``tools/opdocs.LEDGER_DIMS`` / ``typed_catalog``
(RESULT_ADAPTERS と PARAM_HINTS)/ ``chain_fuzz.TYPE_CHECKS`` の述語 /
``opassist._LEDGERS`` / ``pyproject`` の py-modules。どれか 1 つ落とすと
静かな穴になる —— この族はまさにそれで消えていた。
"""
import fourierdesc
import imagemorph

_MOD = {"fourierdesc": fourierdesc, "imagemorph": imagemorph}

# --------------------------------------------------------------------------- #
# 型語彙: **新語は 1 つだけ**(``efdmodel``)。その判断の記録。
# --------------------------------------------------------------------------- #
# 基準はこの repo 共通の 1 つ ——「混ぜたときに例外ではなく、もっともらしく
# 間違った数値が出るか」。加えて**生産者と消費者が族の中に両方いるか**。
#
#   * ``efdmodel`` = ``elliptic_fourier`` の返す辞書
#     ``{"a0", "c0", "coeffs", "n_harmonics"}``。既存の ``table``(list か dict)
#     の述語には当たってしまうが、``table`` プールには Zernike 係数表などが
#     入る。それを ``reconstruct`` に渡すと KeyError で**うるさく落ちる**ので
#     「静かに間違う」条件は満たさない —— が、そうなると族の 4 op が例外で
#     終わり、ファザーの検査面としては死ぬ。**型を分ける理由は「嘘を防ぐ」
#     だけでなく「実際に走らせる」でもある**(``shapemodel`` と同じ理由)。
#     生産者 ``elliptic_fourier``、消費者 ``reconstruct`` / ``invariants`` /
#     ``normalize`` / ``descriptor_distance`` が族内に揃っている。
#
#   * 輪郭とランドマークは ``pairs``((N,2))で足りる。**わざと分けていない**:
#     この族では輪郭点とランドマーク点を混ぜて渡しても、それは「別の点の
#     並びでワープした」だけで嘘にはならない(``warp_tps_image`` は対応が
#     取れてさえいれば正しく動く)。分ける理由が無い型は作らない。
#
#   * 画像は ``image2d``、モーフ列は ``images``、距離は ``measurement``、
#     正準化した係数 (H,4) は ``matrix``。
#
# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    # 記述 —— 閉輪郭を係数へ畳み、形として比べる。
    "descriptor": [
        ("elliptic_fourier", "fourierdesc", ["pairs"], "efdmodel"),
        ("reconstruct", "fourierdesc", ["efdmodel"], "pairs"),
        ("invariants", "fourierdesc", ["efdmodel"], "pairs"),
        ("normalize", "fourierdesc", ["efdmodel"], "matrix"),
        ("descriptor_distance", "fourierdesc", ["efdmodel", "efdmodel"], "measurement"),
        ("fourier_smooth", "fourierdesc", ["pairs"], "pairs"),
        ("from_xld", "fourierdesc", ["table"], "pairs"),
    ],
    # 変形 —— 対応点で画像を写す。
    "morph": [
        ("add_frame_corners", "imagemorph", ["pairs"], "pairs"),
        ("warp_tps_image", "imagemorph", ["image2d", "pairs", "pairs"], "image2d"),
        ("warp_piecewise_affine", "imagemorph", ["image2d", "pairs", "pairs"], "image2d"),
        ("blend", "imagemorph", ["image2d", "image2d"], "image2d"),
        ("morph", "imagemorph", ["image2d", "image2d", "pairs", "pairs"], "image2d"),
        ("morph_sequence", "imagemorph", ["image2d", "image2d", "pairs", "pairs"], "images"),
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


OPSSHAPE2D = _build()

#: 宣言 out 型と素の返りの橋渡し。**意図的に空** —— 13 op すべてが宣言どおりの
#: 値を 1 つだけ返すことを実測で確認した(2026-09-06)。タプルを返す op も、
#: 旗で返り型が変わる op もこの族には無い。
RESULT_ADAPTERS = {}


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSSHAPE2D.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


def get(name):
    """op 名 → 実体(callable、素の返り型)。"""
    return OPSSHAPE2D[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、**台帳の宣言 out 型どおりの値**を返す(adapter 適用)。"""
    result = OPSSHAPE2D[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSSHAPE2D[name]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSSHAPE2D.items() if m["func"] is None]


if __name__ == "__main__":
    print("opsshape2d: %d ops / %d categories"
          % (len(OPSSHAPE2D), len(categories())))
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
    for cat in categories():
        print("  %-11s %s" % (cat, ", ".join(list_ops(cat))))
