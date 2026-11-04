# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsmv —— 工業用ビジョンの定番の演算の台帳(ステレオ・幾何の再標本化・古典形態学ほか)。

実体は ``mvimage`` / ``mvstereo`` / ``mvmorph`` / ``mvtrack`` / ``mvclass`` / ``mvtext`` と、
既存の ``filters_arith`` / ``image_gray`` / ``image_gen`` / ``reconstruction`` / ``shapematch`` /
``matching`` / ``final_genuine2``。47 op / 10 カテゴリ。どの op も公開の論文と教科書の数式から実装した。

呼び出し例::

    import numpy as np
    import fullseye as fs

    rng = np.random.default_rng(0)
    right = rng.random((48, 96))                         # 乱点ステレオ: 真の視差は 6 画素
    left = np.roll(right, 6, axis=1)
    res = fs.ledger.binocular_disparity_ms(left, right, max_disp=12)
    print("median disparity:", round(float(np.nanmedian(res["disparity"])), 2))
    region = np.zeros((40, 80), bool)
    region[10:30, 10:30] = region[12:28, 50:70] = True   # 2 つの物体
    print("zones meet at col:", int(np.nonzero(fs.ledger.morph_skiz(region)[20])[0][0]))

出力は ``median disparity: 6.0`` と ``zones meet at col: 39``(``tests/test_opsmv.py`` が
この例を実行し、値を確かめる)。

## 型語彙: **新語を作らない**

入出力は既存の ``image2d`` / ``mask`` / ``labels2d`` / ``keypoints`` / ``points`` / ``table`` /
``signal`` / ``matrix`` / ``scalar`` に収まる。背景モデルと分類器は ``table``(鍵つき dict)
で、族の外に消費者がいない。``mask`` は bool を返す(``region_morph`` の 0/1 の float と違う
ので、float の領域は ``> 0`` で受ける)。

## 台帳に**載せなかった**もの(理由つき)

1. ``filters_freq`` にあった LUT の ``map_image`` は、幾何の写像を適用する演算と名前が同じで
   中身が違ったので消した。LUT は ``lut_trans`` を使う。
2. ``calib.image_to_world_plane`` は点を写す op のまま残した。画像を平行化する演算は
   :func:`mvimage.rectify_to_world_plane` として別の名前で足した。同じ名前で点と画像の両方を
   受けると、型の検査を通って別の意味の値が返る。
3. Golay の文字は ``l`` / ``m`` / ``e`` / ``i`` / ``c`` の 5 つだけ。形を教科書で確かめた
   ものに限った。
"""
import filters_arith
import final_genuine2
import image_gen
import image_gray
import matching
import mvclass
import mvimage
import mvmorph
import mvstereo
import mvtext
import mvtrack
import reconstruction
import shapematch

_MOD = {"filters_arith": filters_arith, "final_genuine2": final_genuine2, "image_gen": image_gen,
        "image_gray": image_gray, "matching": matching,
        "mvclass": mvclass, "mvimage": mvimage, "mvmorph": mvmorph, "mvstereo": mvstereo,
        "mvtext": mvtext, "mvtrack": mvtrack, "reconstruction": reconstruction,
        "shapematch": shapematch}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    # ステレオ —— 平行化した 2 枚から視差・距離・点群へ。
    "stereo": [
        ("binocular_disparity_ms", "mvstereo", ["image2d", "image2d"], "table"),
        ("binocular_distance_ms", "mvstereo", ["image2d", "image2d"], "table"),
        ("reconstruct_surface_stereo", "reconstruction", ["image2d"], "points"),
    ],
    # 幾何の再標本化 —— 写像の適用・平面への平行化・歪みの変換・回転矩形の切り出し。
    "resample": [
        ("map_image", "mvimage", ["image2d", "table"], "image2d"),
        ("rectify_to_world_plane", "mvimage", ["image2d", "table", "matrix"], "image2d"),
        ("change_radial_distortion_image", "mvimage", ["image2d", "table", "table"], "image2d"),
        ("crop_rectangle2", "image_gen", ["image2d"], "image2d"),
    ],
    # 灰色値の計測 —— 重み付きの重心・ヒストグラム・射影・輪郭に沿った読み取り。
    "gray": [
        ("atan2_image", "filters_arith", ["image2d", "image2d"], "image2d"),
        ("area_center_gray", "image_gray", ["image2d"], "table"),
        ("gray_histo", "image_gray", ["image2d"], "table"),
        ("gray_projections", "image_gray", ["image2d"], "table"),
        ("get_grayval_contour_xld", "mvimage", ["image2d", "keypoints"], "signal"),
    ],
    # 検出 —— 注目点とテンプレート。
    "detect": [
        ("points_lepetit", "mvimage", ["image2d"], "keypoints"),
        ("create_ncc_model", "matching", ["image2d"], "table"),
        ("find_ncc_models", "shapematch", ["table", "image2d"], "table"),
    ],
    # 姿勢 —— 円の像から 3-D の円へ。
    "pose": [
        ("get_circle_pose", "mvstereo", ["keypoints"], "table"),
    ],
    # 二値形態学の古典。
    "morphology": [
        ("golay_elements", "mvmorph", [], "table"),
        ("hit_or_miss_golay", "mvmorph", ["mask"], "mask"),
        ("hit_or_miss_seq", "mvmorph", ["mask"], "mask"),
        ("thickening_hit_miss", "mvmorph", ["mask", "mask", "mask"], "mask"),
        ("thickening_golay", "mvmorph", ["mask"], "mask"),
        ("thickening_seq", "mvmorph", ["mask"], "mask"),
        ("morph_hat", "mvmorph", ["mask", "mask"], "mask"),
        ("morph_skiz", "mvmorph", ["mask"], "mask"),
        ("opening_seg", "mvmorph", ["mask", "mask"], "labels2d"),
    ],
    # 曲線 —— 点列を通る B スプライン。
    "curve": [
        ("gen_nurbs_interp", "mvtext", ["keypoints"], "table"),
    ],
    # 追跡 —— カルマンフィルタと画素ごとの背景推定。
    "tracking": [
        ("filter_kalman", "mvtrack", [], "table"),
        ("create_bg_esti", "mvtrack", ["image2d"], "table"),
        ("run_bg_esti", "mvtrack", ["table", "image2d"], "table"),
        ("give_bg_esti", "mvtrack", ["table"], "image2d"),
        ("update_bg_esti", "mvtrack", ["table", "image2d", "mask"], "table"),
    ],
    # 分類 —— 特徴ベクトルの分類器と語の照合。
    "classify": [
        ("train_class_gmm", "mvclass", ["matrix"], "table"),
        ("classify_class_gmm", "mvclass", ["table", "matrix"], "table"),
        ("evaluate_class_gmm", "mvclass", ["table", "matrix"], "table"),
        ("train_class_knn", "mvclass", ["matrix"], "table"),
        ("classify_class_knn", "mvclass", ["table", "matrix"], "table"),
        ("train_class_mlp", "final_genuine2", ["matrix"], "table"),
        ("classify_class_mlp", "mvclass", ["table", "matrix"], "table"),
        ("train_class_svm", "final_genuine2", ["matrix"], "table"),
        ("classify_class_svm", "mvclass", ["table", "matrix"], "table"),
        ("create_lexicon", "mvclass", [], "table"),
        ("lookup_lexicon", "mvclass", ["table"], "scalar"),
        ("suggest_lexicon", "mvclass", ["table"], "table"),
    ],
    # 文字 —— 行の傾き・斜体角・字の切り出し。
    "text": [
        ("text_line_orientation", "mvtext", ["image2d"], "scalar"),
        ("text_line_slant", "mvtext", ["image2d"], "scalar"),
        ("segment_characters", "mvtext", ["image2d"], "labels2d"),
        ("select_characters", "mvtext", ["labels2d"], "labels2d"),
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


OPSMV = _build()

#: 宣言 out 型と素の返りの橋渡し。この族はどの op もタプルを返さないので空。
RESULT_ADAPTERS: dict = {}


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSMV.items() if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


def get(name):
    """op 名 → 実体(callable、素の返り型)。"""
    return OPSMV[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、台帳の宣言 out 型どおりの値を返す(adapter 適用)。"""
    result = OPSMV[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSMV[name]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSMV.items() if m["func"] is None]


if __name__ == "__main__":
    print("opsmv: %d ops / %d categories" % (len(OPSMV), len(categories())))
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
    for cat in categories():
        print("  %-11s %s" % (cat, ", ".join(list_ops(cat))))
