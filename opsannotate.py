# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsannotate — 図注(annotate)op の統一レジストリ(台帳)。

著者の要望(2026-09-02)「描画周りの op を充実させましょう」。それまで描画は
:mod:`imagedraw` の 5 op(線・折れ線・円・マーカー・輪郭)だけで、**図に意味を
載せる層が無かった** ―― その穴を、生成器 6 本が各自の私的ヘルパーで埋めていた。

台帳の役割は opsmath / opsquat と同じで、「何があるか」を一望させること。
op 本体は :mod:`annotate`。

    import opsannotate
    opsannotate.list_ops("plot")
    opsannotate.get("scale_bar")(img, 100.0, 0.5, "µm")

## 型の語彙

既存の台帳(ops3d / ops1d / opsmath)の語彙をそのまま使い、この層で新しく
必要になった 4 つだけを足した。**足した理由**(既存語で表現すると嘘になるもの
だけを足す、という opsmath の規律に従う):

* ``text``   — 文字列。``table`` でも ``signal`` でもない。図注の入力の半分は
  文字なので、型として見えないと台帳の意味がない。
* ``axes``   — :func:`annotate.axes_transform` が返す**データ↔画素の対応**。
  中身は dict なので ``table`` と同型だが、消費側 5 op
  (``axes_frame``/``grid_lines``/``ticks``/``plot_series``/``data_to_pixel``)が
  ``rect``/``xlim``/``ylim``/``invert_y``/``xscale``/``yscale`` の**全キー**を
  前提にする。一般の ``table`` を渡せる型にすると、KeyError ではなく
  **もっともらしく間違った位置に描く**(``rect`` を欠いた dict が来たら
  そこで気づけない)。
* ``entries`` — ``(color, text)`` の並び(凡例の行)。``pairs`` は数値の対で、
  ここは色と文字なので別物。
* ``lut``    — ``(n,3)`` の色対応表。``matrix`` と同型だが、値域 [0,1] と
  「行が色」という意味を持つ(:func:`palette.diverging_lut` の出力)。

``mask``(2 値の (H,W))と ``labels``(整数の (H,W))は既存語彙。
"""
import numpy as np

import annotate

_MOD = {"annotate": annotate}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    # 文字 —— 幅を測ってから描く(黙って切らない)
    "text": [
        ("measure_text", "annotate", ["text"], "table"),
        ("text_box", "annotate", ["image2d", "text"], "image2d"),
    ],
    # 指し示す
    "pointer": [
        ("arrow", "annotate", ["image2d"], "image2d"),
        ("leader_line", "annotate", ["image2d", "text"], "image2d"),
        ("label_points", "annotate", ["image2d", "pairs"], "image2d"),
        ("crosshair", "annotate", ["image2d"], "image2d"),
    ],
    # 図の備品(凡例・カラーバー・スケールバー)
    "furniture": [
        ("legend_box", "annotate", ["image2d", "entries"], "image2d"),
        ("color_bar", "annotate", ["image2d", "lut"], "image2d"),
        ("scale_bar", "annotate", ["image2d"], "image2d"),
    ],
    # グラフ(matplotlib を使わないので、軸を引くのもこの層の仕事)
    "plot": [
        ("axes_transform", "annotate", [], "axes"),
        ("data_to_pixel", "annotate", ["axes", "signal", "signal"], "pairs"),
        ("nice_ticks", "annotate", [], "signal"),
        ("axes_frame", "annotate", ["image2d", "axes"], "image2d"),
        ("grid_lines", "annotate", ["image2d", "axes"], "image2d"),
        ("ticks", "annotate", ["image2d", "axes"], "image2d"),
        ("plot_series", "annotate", ["image2d", "axes", "signal", "signal"], "image2d"),
    ],
    # 重ね(α 合成)
    "overlay": [
        ("overlay_mask", "annotate", ["image2d", "mask"], "image2d"),
        ("overlay_labels", "annotate", ["image2d", "labels"], "image2d"),
    ],
    # 組み立て
    "compose": [
        ("zoom_inset", "annotate", ["image2d"], "image2d"),
        ("compare_frame", "annotate", ["image2d", "image2d"], "image2d"),
        ("panel_grid", "annotate", ["image2d"], "image2d"),
    ],
    # 図形(下敷き・囲み・角度)
    "shape": [
        ("rounded_rect", "annotate", ["image2d"], "image2d"),
        ("filled_polygon", "annotate", ["image2d", "pairs"], "image2d"),
        ("arc", "annotate", ["image2d"], "image2d"),
        ("ellipse", "annotate", ["image2d"], "image2d"),
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


OPSANNOTATE = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSANNOTATE.items() if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し(opsmath / ops3d と同じ一級機構)。
#: :func:`annotate.data_to_pixel` は「px と py の 2 本」を返すのが素直な形
#: (``px, py = data_to_pixel(...)``)だが、台帳の ``pairs`` の正典は
#: **(N,2) か同じ長さの 1-D 2 本**なので、``call`` 経由では (N,2) に組み直す。
RESULT_ADAPTERS = {
    "data_to_pixel": lambda r: np.stack([np.atleast_1d(np.asarray(r[0], np.float64)),
                                         np.atleast_1d(np.asarray(r[1], np.float64))], axis=1)
    if isinstance(r, tuple) and len(r) == 2 else r,
}


def get(name):
    """op 名 → 実体(callable、素の返り型)。宣言型が欲しければ :func:`call`。"""
    return OPSANNOTATE[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、**台帳の宣言 out 型どおりの値**を返す(adapter 適用)。"""
    result = OPSANNOTATE[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSANNOTATE[name]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSANNOTATE.items() if m["func"] is None]


if __name__ == "__main__":
    print(f"opsannotate: {len(OPSANNOTATE)} ops / {len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
