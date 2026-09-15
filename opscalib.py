# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opscalib —— カメラ校正・平面写像・対応点からの変換推定 op の統一レジストリ。

実体は ``calib.py``(投影・Zhang 内部校正・Tsai-Lenz ハンドアイ)、
``caltab.py``(校正板の生成・シミュレート・検出・姿勢)、
``fit_transform.py``(対応点 → 剛体/相似/射影変換)。21 op / 5 カテゴリ。

使い方::

    import opscalib
    opscalib.list_ops("calibrate")
    K = opscalib.call("camera_calibration", object_points, image_points_list)

## なぜ台帳に載せたか(2026-09-16)

**実装は 2026-08 からあり、テストも 30 本以上あった。それでも利用者からは
「無い」ものだった。** 実測(2026-09-16):

==========================  =========================================
引いた層                      結果
==========================  =========================================
``fullseye.<名前>``           42 関数すべて **無し**
``fullseye.ledger.<名前>``    42 関数すべて **無し**
``ops.REGISTRY``(2-D op)    42 関数すべて **無し**
``docs/OP_INDEX.json``       42 関数すべて **無し**
``docs/ops/`` の op ノート     **1 枚も無い**
``fullseye.op_find("caltab")``  **0 件**
``fullseye.op_find("mosaic")``  **0 件**
``fullseye.vision_ops``       在る(HALCON facade 1,801 op の中)
==========================  =========================================

つまり **HALCON facade からは呼べるが、検索層と機械可読の索引からは
構造的に見えない**。外部の AI 2 体が独立に「カメラ校正の op は確認できなかった」
と報告したのは、この状態を正確に写している —— 引ける層が 1 つしか無く、
しかもそれは名前を先に知っている人しか辿れない層だった。

``examples/poc_camera_calibration.py`` も同じことを書いている:
「``calib.camera_calibration`` がリポジトリ唯一の内部行列推定だが、
``import fullseye as fs`` の公開名にも op レジストリにも入っていない。
ファサードだけを見る利用者にとって **fullseye はカメラ校正ができない
ライブラリに見える**」。PoC が挙げた宿題を、台帳の側で閉じたのがこの族。

## 型語彙: **新語をひとつも作らない**

判断の基準はこの repo 共通のもの ——「混ぜたときに例外ではなく、もっともらしく
間違った数値が出るか」。この族の入出力は既存の語彙にそのまま収まる:

* ``points``  —— 3-D 点 (N,3)、画素 (N,2) の ``(row, col)``、ワールド平面 (N,2)。
  どれも「点の並び」で、既存の ``points`` の述語どおり。
* ``pose``    —— 4x4 剛体変換。``pnp_ransac`` / ``fit_rigid`` が既に produce する型。
* ``matrix``  —— 3x3 の同次変換(アフィン/剛体/相似/射影)。``essential_8point`` と同じ。
* ``table``   —— 鍵つきの計測結果 dict(``fx``/``fy``/``cx``/``cy``/``reproj_rms``、
  校正板の記述、写像テーブル)。``blob_features`` と同じ扱い。
* ``contour`` —— XLD 輪郭。``contour_to_world_plane_xld`` の入出力。
* ``image2d`` —— 校正板の画像。

★**カメラ内部パラメータ(``cam_par``)に新しい sort を作らなかった。**
``{"fx","fy","cx","cy"}`` の dict は ``table`` の述語(鍵つき dict)に収まり、
かつ**この族の外に消費者がいない**(``camera.py`` の内部行列は 3x3 ``matrix`` で
受ける別系統)。1 族の中だけで閉じる型に新語を与えると、語彙が増えるだけで
連鎖は 1 本も増えない。0.2.1 を patch/minor の範囲に留める判断でもある。

## 台帳に**載せなかった**もの(理由つき)

「実装が在る」と「公開してよい」は別なので、外したものは黙って落とさず並べる。

1. ``vector_to_hom_mat2d`` —— **同名の実装が 2 つあり、座標規約が違う**。
   ``calib.vector_to_hom_mat2d`` は (x, y) の DLT ホモグラフィ、
   ``fit_transform.vector_to_hom_mat2d`` は (row, col) のアフィン最小二乗。
   台帳は 1 名前 1 実装なので、どちらを載せても**もう片方を期待した呼び手が
   例外なしに間違った行列を受け取る**(2 座標が入れ替わるだけなので、
   再投影誤差も小さいまま出うる)—— まさに型を分ける/載せない条件そのもの。
   射影変換が要るなら ``hom_vector_to_proj_hom_mat2d``(Hartley 正規化つき DLT、
   ``(row, col)`` 契約が試験で固定されている)を使う。
2. ``calibrate_cameras`` / ``calibrate_hand_eye`` / ``find_calib_object`` ——
   それぞれ ``camera_calibration`` / ``hand_eye_calibration`` / ``find_caltab``
   の**別名**。同じ実装を 2 つの名前で出すと利用者がどちらを呼ぶか決められない
   (``tests/test_op_discovery`` が 2-D 側で同じ規律を敷いている)。
3. ``binocular_calibration`` —— **契約が未確定**。docstring は「ステレオ相対姿勢を
   推定」と読めるが、実体は左右を個別に Zhang 校正して
   ``{"note": "相対姿勢は…(簡易)"}`` という**文字列**を返すだけで、
   相対姿勢そのものを返していない。名乗りと中身が食い違うものは出さない。

``mosaic.py`` と ``filters_freq.phase_correlation_fft`` の扱いは
``docs/MATURITY_INTERNAL.md`` に記録した(この族には入れていない)。
"""
import calib
import caltab
import fit_transform

_MOD = {"calib": calib, "caltab": caltab, "fit_transform": fit_transform}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    # 投影 —— 3-D 点を画素へ。族の最下層で、校正の検算にも使う。
    "project": [
        ("project_3d_point", "calib", ["points"], "points"),
        ("project_point_hom_mat3d", "calib", ["points"], "points"),
        ("project_hom_point_hom_mat3d", "calib", ["points"], "points"),
    ],
    # 平面写像 —— 画素 ↔ ワールド平面(z=0)。寸法を mm で読むための層。
    "plane": [
        ("image_to_world_plane", "calib", ["points"], "points"),
        ("image_points_to_world_plane", "calib", ["points"], "points"),
        ("contour_to_world_plane_xld", "calib", ["contour"], "contour"),
        ("gen_image_to_world_plane_map", "caltab", [], "table"),
        ("gen_radial_distortion_map", "calib", [], "table"),
    ],
    # 校正板 —— 作る/描く/シミュレートする/見つける。族の入口。
    "target": [
        ("caltab_points", "caltab", [], "points"),
        ("create_caltab", "caltab", [], "table"),
        ("gen_caltab", "caltab", [], "table"),
        ("sim_caltab", "caltab", ["table"], "table"),
        ("disp_caltab", "caltab", ["table"], "image2d"),
        ("find_caltab", "caltab", ["image2d"], "points"),
    ],
    # 校正 —— 内部パラメータ・板の姿勢・ハンドアイ。族の目的。
    "calibrate": [
        ("camera_calibration", "calib", ["points"], "table"),
        ("find_marks_and_pose", "caltab", ["image2d"], "table"),
        ("hand_eye_calibration", "calib", ["pose"], "pose"),
    ],
    # 対応点 → 変換 —— 校正の前後で使う 2-D 変換推定(Kabsch / Umeyama / DLT)。
    "fit": [
        ("vector_to_rigid", "fit_transform", ["points"], "matrix"),
        ("vector_to_similarity", "fit_transform", ["points"], "matrix"),
        ("vector_angle_to_rigid", "fit_transform", [], "matrix"),
        ("hom_vector_to_proj_hom_mat2d", "fit_transform", ["points"], "matrix"),
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


OPSCALIB = _build()

#: 宣言 out 型と素の返りの橋渡し。**この族はどの op もタプルを返さない**ので空
#: (空であること自体が「調べたうえで要らない」の記録 —— 他の族と同じ体裁)。
RESULT_ADAPTERS: dict = {}


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSCALIB.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


def get(name):
    """op 名 → 実体(callable、素の返り型)。"""
    return OPSCALIB[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、**台帳の宣言 out 型どおりの値**を返す(adapter 適用)。"""
    result = OPSCALIB[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSCALIB[name]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPSCALIB.items() if m["func"] is None]


if __name__ == "__main__":
    print("opscalib: %d ops / %d categories" % (len(OPSCALIB), len(categories())))
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
    for cat in categories():
        print("  %-10s %s" % (cat, ", ".join(list_ops(cat))))
