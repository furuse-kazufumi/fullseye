# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opscalib —— カメラ校正・平面写像・対応点からの変換推定 op の統一レジストリ。

実体は ``calib.py``(投影・Zhang 内部校正・Tsai-Lenz ハンドアイ)、
``caltab.py``(校正板の生成・シミュレート・検出・姿勢)、
``fit_transform.py``(対応点 → 剛体/相似/射影変換)。21 op / 5 カテゴリ。

呼び出し例::

    import numpy as np
    import fullseye as fs

    K = {"fx": 500.0, "fy": 500.0, "cx": 128.0, "cy": 128.0}
    board = fs.ledger.create_caltab(7, 7, 10.0)          # 7x7、10 mm ピッチ、板中心が原点
    c, s = np.cos(0.2), np.sin(0.2)                       # x 軸まわりに 0.2 rad 傾ける
    pose = np.eye(4)
    pose[:3, :3] = [[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]]
    pose[:3, 3] = [0.0, 0.0, 600.0]                       # 600 mm 先に置く
    sim = fs.ledger.sim_caltab(board, K, pose, 256)      # その見え方を合成
    found = fs.ledger.find_marks_and_pose(sim["image"], K, board)
    print("marks:", found["n_marks"], "reproj rms < 0.5 px:", found["reproj_rms"] < 0.5)
    print("distance [mm]: %.1f (true 600)" % found["pose"][2, 3])

出力は ``marks: 49 reproj rms < 0.5 px: True`` と ``distance [mm]: 600.5 (true 600)``
(マークを画素へ塗った量子化のぶん 0.5 mm ずれる。``tests/test_opscalib.py`` がこの例を
実行し、1 mm 以内であることを確かめる)。

## なぜ台帳に載せたか(実装 2026-08、台帳 2026-10-23)

**実装は 2026-08 からあり、試験も 30 本以上あった。それでも利用者からは
「無い」ものだった。** 21 op について公開面を引いた実測(2026-10-23、master):

==============================  =========================================
引いた層                          結果
==============================  =========================================
``fullseye.<名前>``               21 中 **1**(``camera_calibration`` だけ)
``fullseye.ledger.<名前>``        21 中 **0**
``docs/OP_INDEX.json``           21 中 **0**
``docs/ops/`` の op ノート         **0 枚**
``fullseye.op_find("caltab")``   **0 件**
==============================  =========================================

外部の AI 2 体が独立に「カメラ校正の op は確認できなかった」と報告したのは、
この状態を正確に写している。``examples/poc_camera_calibration.py`` も
「ファサードだけを見る利用者にとって **fullseye はカメラ校正ができない
ライブラリに見える**」と書いた。その宿題を台帳の側で閉じたのがこの族。

この穴が長く見えなかった理由も記録しておく: 公開面に届かないモジュールを数える門
(``tests/test_public_reachability.py`` の ``_shipped_modules``)が、2026-10-02 まで
``pyproject.toml`` の py-modules を途中までしか読めていなかった(配列内コメントの
``]`` で非貪欲の正規表現が止まった)。calib / caltab は数えられる機会が無かった。

## 型語彙: **新語をひとつも作らない**

判断の基準はこの repo 共通のもの ——「混ぜたときに例外ではなく、もっともらしく
間違った数値が出るか」。この族の入出力は既存の語彙にそのまま収まる:

* ``points``    —— 3-D 点 (N,3) だけ(述語が ``(N, 3)`` を要求する)。
* ``keypoints`` —— 2-D の点列 (N,2): 画素の ``(row, col)``、ワールド平面の点、校正板のマーク。
* ``matrix``    —— 3x3 の同次変換(アフィン/剛体/相似/射影)と、4x4 の同次変換
  (``hand_eye_calibration`` の X)。この repo の ``pose`` は ``(R(3,3), t(3,))`` のタプルを
  指す語なので、4x4 行列を ``pose`` と名乗ると述語に落ちる(2026-09-16 の初版はそうなっていた)。
* ``table``   —— 鍵つきの計測結果 dict(``fx``/``fy``/``cx``/``cy``/``reproj_rms``、
  校正板の記述、写像テーブル)。
* XLD 輪郭(``{"shape", "cs": [(N,2), ...]}``)も ``table`` として宣言する。``contour`` は
  索引に語としてあるが連鎖の述語が無く、宣言すると型検査が「述語なし」で落ちる。
* ``image2d`` —— 校正板の画像。

★**カメラ内部パラメータ(``cam_par``)に新しい sort を作らなかった。**
``{"fx","fy","cx","cy"}`` の dict は ``table`` の述語(鍵つき dict)に収まり、
かつ**この族の外に消費者がいない**(``camera.py`` の内部行列は 3x3 ``matrix`` で
受ける別系統)。1 族の中だけで閉じる型に新語を与えると、語彙が増えるだけで
連鎖は 1 本も増えない。

## 台帳に**載せなかった**もの(理由つき)

「実装が在る」と「公開してよい」は別なので、外したものは黙って落とさず並べる。

1. ``vector_to_hom_mat2d`` —— **同名の実装が 2 つあり、座標規約が違う**。
   ``calib.vector_to_hom_mat2d`` は (x, y) の DLT ホモグラフィ、
   ``fit_transform.vector_to_hom_mat2d`` は (row, col) のアフィン最小二乗。
   台帳は 1 名前 1 実装なので、どちらを載せても**もう片方を期待した呼び手が
   例外なしに間違った行列を受け取る**(2 座標が入れ替わるだけなので、
   再投影誤差も小さいまま出うる)。射影変換が要るなら
   ``hom_vector_to_proj_hom_mat2d``(Hartley 正規化つき DLT、``(row, col)`` 契約が
   試験で固定されている)を使う。
2. ``calibrate_cameras`` / ``calibrate_hand_eye`` / ``find_calib_object`` ——
   それぞれ ``camera_calibration`` / ``hand_eye_calibration`` / ``find_caltab``
   の**別名**。同じ実装を 2 つの名前で出すと利用者がどちらを呼ぶか決められない。
3. ``binocular_calibration`` —— **名乗りと中身が食い違う**。docstring は
   「ステレオ相対姿勢を推定」と読めるが、実体は左右を個別に Zhang 校正して
   相対姿勢の代わりに**説明の文字列**を返すだけ。
4. ``mosaic.py`` の歪み込みの対応推定 —— 返りの ``kappa`` が常に ``0.0``
   (歪みを推定していない)。球面モザイクも平面の射影をそのまま返す。名乗りと
   中身が食い違うので、この族にも他の族にも入れていない。
"""
import calib
import caltab
import fit_transform

_MOD = {"calib": calib, "caltab": caltab, "fit_transform": fit_transform}

# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    # 投影 —— 3-D 点を画素へ。族の最下層で、校正の検算にも使う。
    "project": [
        ("project_3d_point", "calib", ["points"], "keypoints"),
        ("project_point_hom_mat3d", "calib", ["points"], "keypoints"),
        ("project_hom_point_hom_mat3d", "calib", ["matrix"], "keypoints"),
    ],
    # 平面写像 —— 画素 ↔ ワールド平面(z=0)。寸法を mm で読むための層。
    "plane": [
        ("image_to_world_plane", "calib", ["keypoints"], "keypoints"),
        ("image_points_to_world_plane", "calib", ["table"], "keypoints"),
        ("contour_to_world_plane_xld", "calib", ["table"], "table"),
        ("gen_image_to_world_plane_map", "caltab", [], "table"),
        ("gen_radial_distortion_map", "calib", [], "table"),
    ],
    # 校正板 —— 作る/描く/シミュレートする/見つける。族の入口。
    "target": [
        ("caltab_points", "caltab", [], "keypoints"),
        ("create_caltab", "caltab", [], "table"),
        ("gen_caltab", "caltab", [], "table"),
        ("sim_caltab", "caltab", ["table"], "table"),
        ("disp_caltab", "caltab", ["table"], "image2d"),
        ("find_caltab", "caltab", ["image2d"], "keypoints"),
    ],
    # 校正 —— 内部パラメータ・板の姿勢・ハンドアイ。族の目的。
    "calibrate": [
        ("camera_calibration", "calib", ["keypoints"], "table"),
        ("find_marks_and_pose", "caltab", ["image2d"], "table"),
        ("hand_eye_calibration", "calib", [], "matrix"),
    ],
    # 対応点 → 変換 —— 校正の前後で使う 2-D 変換推定(Kabsch / Umeyama / DLT)。
    "fit": [
        ("vector_to_rigid", "fit_transform", ["keypoints"], "matrix"),
        ("vector_to_similarity", "fit_transform", ["keypoints"], "matrix"),
        ("vector_angle_to_rigid", "fit_transform", [], "matrix"),
        ("hom_vector_to_proj_hom_mat2d", "fit_transform", ["keypoints"], "matrix"),
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
