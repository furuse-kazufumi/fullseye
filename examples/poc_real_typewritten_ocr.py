# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""1943 年のタイプ打ちの技術報告(実スキャン)を、古典的な OCR の op だけで読む。

題材は米国の航空諮問委員会(NACA)の技術報告 TN 898「Adaptor for Measuring Principal Strains
with Tuckerman Strain Gage」(A. E. McPherson、1943)の 300 dpi のスキャン(NASA 技術報告サーバ
NTRS の 19930084880、"Public Use Permitted")。1 字ごとの幅が同じタイプライターの印字は、
製造現場の刻印・銘板・ラベルの印字と同じく「書体が 1 つで、汚れ・かすれ・傾きが実物の側にある」。

正解の文字列は、3 頁(報告の 1・3・5 頁)の 100 行を**人(この PoC の作者側)が画像を見て
1 行ずつ書き起こした**もの(:data:`TRANSCRIPTION`)。配布元の書き起こしは無い(NTRS の OCR の
文字列は誤りが多く、正解には使わない)。字形に忠実に書いた: このタイプライターには数字の 1 の
キーが無く、小文字の l で代用しているので ``l`` と書く。式・ギリシャ文字・添字のある行は外した。

主役の op と、照合する外の真値:

1. ``text_line_orientation``(行の傾き): 頁を既知の角度で回し、その角度を当てる。真値は回した
   角度。頁そのものの傾きは、行の下端(x 高さの字の底)を最小二乗で結ぶ別の方法で検算する。
   範囲(既定 ±30°)の外へ回すと外れることも示す。
2. ``text_line_slant``(字の傾斜): 直立した印字を既知の角度でせん断し、その角度を当てる。
   ★小さい傾斜(±2° 以内)は 0 と答える —— 縦画の高さが約 20 画素なので、2° のせん断は
   1 画素未満にしかならず、整数の列の射影に現れない。
3. ``segment_characters`` / ``select_characters``(字の切り出し): 行ごとに切り出した字の数を、
   書き起こしの字数(空白を除く)と数え合わせる。``max_gap`` を振ったときの一致する行の数と、
   ``select_characters`` が句読点を落とす様子も数える。
4. 4 種の分類器 ``train_class_gmm`` / ``train_class_knn`` / ``train_class_mlp`` / ``train_class_svm``
   (と ``classify_class_*`` / ``evaluate_class_gmm``): 同じ特徴、同じ学習(1・3 頁)、同じ試験
   (5 頁)で正解率を比べる。特徴は字ごとの区画濃度 + ``gray_projections`` + ``area_center_gray``。
   漏れが無いことを 3 つの門で確かめる(頁が別、試験の字と同じ画素の字が学習に無い、標準化と
   主成分は学習だけで決める)。ラベルを混ぜた対照で、正解率が多数派の割合まで落ちることも見る。
   外の真値として scikit-learn の k-NN(同じ特徴で完全一致)と、scipy の正規分布の密度で書いた
   2 次判別(GMM の 1 成分と同じ式)を並べる。
5. ``create_lexicon`` / ``lookup_lexicon`` / ``suggest_lexicon``(辞書): 読んだ語が辞書に無ければ
   編集距離 1 の語に直す。辞書を学習頁の語だけで作る(開いた語彙)と、試験頁の語も入れる
   (閉じた語彙 = 許される文字列の一覧が先に分かっている製造現場の場合、上限)の 2 通りで、
   語の正解率の上がり方と、**正しく読めた語を壊した数**を数える。
6. 再現性: 同じ seed で 2 回学習し、モデルの配列と予測が完全に一致すること。

データは repo に入れない。``tools/fetch_naca_tn898.py`` が NTRS から PDF を取得して SHA-256 で
固定し、この PoC が PDF の中の 3 頁の JPEG をそのまま取り出す(頁ごとにも SHA-256 を照合)。
置き場は ``FULLSEYE_NACA_TN898_DATA``、無ければ開発の作業木の隣の ``data/fullseye_poc_real/naca_tn898``。
取得していない環境(CI)では、scikit-image に同梱の実スキャン ``page``(BSD-3-Clause)で 1 と 2 の
門だけを回し、NACA の章は下の ``RECORDED``(手元で実データを回した値)を印字する。

実行例::

    py -3.11 tools/fetch_naca_tn898.py
    py -3.11 examples/poc_real_typewritten_ocr.py

図(``FULLSEYE_FIGURE_DIR`` があるときだけ): 5 頁の切り出しと読み(代表図)、回転の復元、
傾斜の復元、切り出しの数え合わせ、4 種の分類器の正解率、辞書の効き目。
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402
import realdata  # noqa: E402

L = fs.ledger

# --------------------------------------------------------------------------- #
# データの台帳
# --------------------------------------------------------------------------- #
#: NTRS の記録番号(NACA TN 898)。
NTRS_ID = "19930084880"
#: 取得する PDF の名前・バイト数・SHA-256(2026-11-08 に NTRS から取得した値)。
PDF_NAME = "19930084880.pdf"
PDF_BYTES = 12_271_741
PDF_SHA256 = "57166092520582608a31459c50627334130d8250996f96d58a659a1849972f18"
#: 使う 3 頁: PDF の頁番号(0 始まり)→ (PDF のオブジェクト番号, JPEG のバイト数, SHA-256)。
#: 頁 2・4・6 は報告の 1・3・5 頁。JPEG は PDF の DCTDecode の流れをそのまま取り出したもの(再符号化しない)。
PAGES = {
    2: (7, 732253, "112632d64f052f9960b9e4b7ab4a2a6a864e58d592db367c59a3d4f845a83c80"),
    4: (15, 601483, "6c094faa9d2605e89ae187f3c7c8bf49de9aa32aae28367ab3072786ada4ead0"),
    6: (23, 656543, "f25f670af4903331bc9b96c249d98f78186b81d7699a520fc94c614e7753d8d5"),
}
TRAIN_PAGES = (2, 4)
TEST_PAGE = 6
SOURCE_NACA = ("A. E. McPherson, Adaptor for Measuring Principal Strains with Tuckerman Strain Gage, "
               "NACA Technical Note 898 (1943), NASA NTRS 19930084880 — Copyright: Public Use Permitted")
SOURCE_PAGE = "scikit-image data.page (scanned page), BSD-3-Clause (scikit-image LICENSE.txt, Files: *)"

#: 書き起こし(2026-11-08、画像を見て 1 行ずつ。字形に忠実: 数字の 1 は小文字の l、° は度、± は
#: 下線つきの +)。キーは頁 → 行の番号(:func:`find_lines` が上から振る番号)。式・ギリシャ文字・添字の
#: 行は載せない(採点の外)。
TRANSCRIPTION = {
    2: {
        0: "NATIONAL ADVISORY COMMITTEE FOR AERONAUTICS",
        1: "TECHNICAL NOTE NO. 898",
        2: "ADAPTOR FOR MEASURING PRINCIPAL STRAINS",
        3: "WITH TUCKERMAN STRAIN GAGE",
        4: "By A. E. McPherson",
        5: "SUMMARY",
        6: "An adaptor is described which uses three Tuckerman",
        7: "optical strain gages to measure the displacement of the",
        8: "three vertices of an equilateral triangle along lines l20°",
        9: "apart.  These displacements are substituted in well-known",
        10: "equations in order to compute the magnitude and direction",
        11: "of the principal strains.  Tests of the adaptor indicate",
        12: "that principal strains over a gage length of l.42 inch may",
        13: "be measured with a systematic error not exceeding 4 percent",
        14: "and a mean observational error of the order of ±0.000006.",
        15: "The maximum observed error in strain was of the order of",
        16: "0.00008.  The directions of principal strains for uni-",
        17: "directional stress were measured with the adaptor with an",
        18: "average error of the order of l°.",
        19: "INTRODUCTION",
        20: "The stress distribution in the plate elements of mono-",
        21: "coque structures under load differs from that in the beam",
        22: "and tube elements of built-up structures of earlier types",
        23: "in being two-dimensional in many cases, with principal",
        24: "stresses of unknown direction as well as unknown magnitude.",
        27: "range, they may be computed by the well-known equations .",
        28: "(reference l):",
    },
    4: {
        0: "NACA Technical Note No. 898 3",
        1: "Method l requires the drilling of gage holes in the",
        2: "structure and is, therefore, ruled out for thin sheet",
        3: "material such as used in aircraft.  It also involves loss",
        4: "in accuracy due to frequent resetting of the gage.  Method",
        5: "2 has the inconvenience of requiring at least three repe-",
        6: "titions of the loading cycle.  Method 3 has been adopted",
        7: "by at least two investigators, as follows:",
        8: "Klemperer, (reference 3), developed a \"tensor gage,\"",
        9: "which is, in principle, a device for measuring strain along",
        10: "three gage lines, intersecting at l20°, by the displacement",
        11: "of three gage points which form the vertices of an equilat-",
        12: "eral triangle having a base length of about l inch.  The",
        13: "three gage points are constrained to move in the direction",
        14: "of three radii forming a l20° star.",
        15: "Ruge and de Forest (reference 4) have connected four",
        16: "wire strain gages into a strain rosette with four gage lines",
        17: "of 3/4-inch gage length making angles of 45° with each other.",
        18: "Neither one of the above devices makes use of existing",
        19: "strain-gage equipment.  It seemed desirable, therefore, to",
        20: "develop a relatively rugged adaptor which would permit the",
        21: "use of existing strain gages of proven accuracy, on a l20°",
        22: "rosette such as that adopted by Klemperer.  The Bureau of",
        23: "Aeronautics, Navy Department, accordingly authorized this",
        24: "Bureau to conduct an investigation along these lines.  This",
        25: "report describes the adaptor for measuring principal strains",
        26: "with Tuckerman optical strain gages (reference 5) which",
        27: "resulted from this investigation.",
        28: "DESCRIPTION OF ADAPTOR",
        29: "Principle",
        30: "The adaptor provides a means of measuring displacements",
    },
    6: {
        0: "NACA Technical Note No. 898 5",
        1: "points, part 9, by screwing them into the number 4-48 holes",
        2: "in parts 7.  Slip center tube, part ll, through center hole",
        3: "in gage clamp, part l5, shown in figure 7, and press into",
        4: "center hole in part l.  Press in tube until it is flush",
        5: "with inner edge of conical hole.  Put hold-down screws,",
        6: "part l6, in place and mount l-inch Tuckerman optical strain",
        7: "gages as shown in the photograph, figure 3.  The knife edges",
        8: "used are the uniform strain type (min. rad = 2.25 in.).",
        9: "Very little force is required to hold the gages down since",
        10: "the force is applied near the knife edge and since the",
        11: "knife edges act on a duralumin surface.",
        12: "CALIBRATION",
        13: "The adaptor was calibrated as follows.",
        14: "A strip of l7S-T aluminum alloy sheet with a free",
        15: "length of l9 inches and a cross section of 2-l/2 by l/8",
        16: "inch was mounted in a tension-testing machine of 20,000",
        17: "pounds capacity.  The axial and transverse strains in the",
        18: "free length under loads from 900 to 7500 pounds were meas-",
        19: "ured with Tuckerman strain gages.  The variation of strain",
        20: "across and along the area used for the calibration was found",
        21: "to be of the order of the observational errors.",
        22: "The adaptor was mounted on the strip as shown in the",
        23: "photograph, figure 3, and the sketch, figure 9.  The weight",
        24: "of the adaptor was carried by the rubber bands A through the",
        25: "string B which was attached to the upper head of the machine.",
        26: "The adaptor was held against the strip with a vacuum cup and",
        27: "rubber bands passing through the center tube.  Holding the",
        28: "adaptor against the specimen in this manner permits the cen-",
        29: "ter of the platform O, figure 2, to move freely in its",
        30: "plane, parallel to the plane determined by the points.  The",
        31: "hold-down force was kept between 2 and 3 pounds in order to",
        32: "securely mount the adaptor without excessive edgewise load",
        33: "on the flexure plates.  During the mounting as well as during",
        34: "the calibrations the load was never allowed to drop below",
        35: "900 pounds; this prevented slipping of the specimen in the",
        36: "grips and assured that the strain corresponding to a given",
        37: "load remained the same throughout the tests.",
        38: "In the first run one leg (leg a) was placed vertical",
        39: "by making the line connecting gage points for the other",
        40: "legs perpendicular to the edge of the specimen; a card-",
        41: "board template was used to obtain accurate alinement.  The",
    },
}

# --------------------------------------------------------------------------- #
# 手続きの定数(どれも学習頁だけを見て決めた。試験頁を見て動かさない)
# --------------------------------------------------------------------------- #
#: 行の帯を見つけるしきい値(灰色 0..1)。書き起こしの行番号はこの値で振った番号に結び付いている。
LINE_THRESHOLD = 0.55
#: 1 行の中で文字の塊とみなす列の隙間の上限[画素]。これより広い隙間の外側は余白の汚れとして捨てる。
GAP_BLOCK = 150
#: ``segment_characters`` の引数。かすれて 2〜3 画素割れた字を 1 字に戻す(字間は 8 画素以上)。
MIN_AREA, MAX_GAP = 12, 3
#: 字の区画濃度の格子(縦 × 横)。
GRID_R, GRID_C = 8, 6
#: 主成分の数(学習の特徴だけで決める)。
N_PCA = 24
#: 4 種の分類器の設定。
GMM_REG = 0.05
MLP_HIDDEN, MLP_EPOCHS = 48, 600
SVM_C, SVM_EPOCHS, SVM_LR = 1.0, 600, 0.01
#: 確信度で絞る場合、辞書で直してよい語 = GMM の事後確率がこれ未満の字を含む語。
CONF_BELOW = 0.999
#: 回転の復元を試す角度[度](``scipy.ndimage.rotate`` の正 = 画面で反時計回り)。
ROT_ANGLES = (-20.0, -10.0, -5.0, -2.0, -1.0, -0.5, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 28.0)
#: 走査の範囲(既定の ±30°)の外。ここでは外れるのが正しい。
ROT_OUTSIDE = 35.0
#: 傾斜の復元を試すせん断の角度[度]。
SLANT_ANGLES = (-30.0, -20.0, -10.0, -5.0, -2.0, -1.0, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 40.0)

#: 実データを手元で回した値(``RECORDED_JSON`` と同じもの)。CI はこれを印字する。
RECORDED: dict = {'acc': {'gmm': 0.9686299615877081,
                           'knn': 0.9807938540332907,
                           'mlp': 0.9660691421254801,
                           'svm': 0.9724711907810499},
                   'acc_ref': {'gmm': 0.9686299615877081,
                               'knn': 0.9807938540332907,
                               'mlp': 0.9807938540332907,
                               'svm': 0.9814340588988476},
                   'acc_seen': {'gmm': 0.9748711340206185,
                                'knn': 0.9871134020618557,
                                'mlp': 0.9722938144329897,
                                'svm': 0.9787371134020618},
                   'agree': {'gmm': 1.0, 'knn': 1.0, 'mlp': 0.9737516005121639, 'svm': 0.9827144686299616},
                   'baseline_residual_deg': {'2': -0.001485529909300999, '4': 0.009970302803805632, '6': -0.005569105280269482},
                   'ceiling': 0.9935979513444302,
                   'control': 0.05057618437900128,
                   'counts': {'2': {'glyphs_seg': 1049, 'glyphs_true': 1052, 'lines': 27, 'matched': 21, 'over': 3, 'under': 3},
                              '4': {'glyphs_seg': 1349, 'glyphs_true': 1351, 'lines': 31, 'matched': 27, 'over': 2, 'under': 2},
                              '6': {'glyphs_seg': 1880,
                                    'glyphs_true': 1881,
                                    'lines': 42,
                                    'matched': 34,
                                    'over': 4,
                                    'under': 4}},
                   'date': '2026-11-08',
                   'failed': 0,
                   'gap_sweep': {'0': 55, '1': 70, '2': 79, '3': 82, '4': 57, '5': 27},
                   'gates': 30,
                   'gmm2_acc': [0.9622279129321383, 0.9622279129321383, 0.9635083226632523],
                   'gmm_posterior': {'flagged': 17,
                                     'flagged_wrong': 13,
                                     'right_median': 1.0,
                                     'wrong': 49,
                                     'wrong_median': 0.9999999463455533},
                   'lexicon': {'gmm': {'before': 297,
                                       'closed': {'after': 314, 'broken': 0, 'fixed': 17, 'lines_exact_after': 19},
                                       'gated': {'after': 299, 'broken': 0, 'fixed': 2, 'lines_exact_after': 14},
                                       'lines': 34,
                                       'lines_exact_before': 13,
                                       'open': {'after': 279, 'broken': 22, 'fixed': 4, 'lines_exact_after': 8},
                                       'split_ok_lines': 33,
                                       'words': 336},
                               'knn': {'before': 310,
                                       'closed': {'after': 324, 'broken': 0, 'fixed': 14, 'lines_exact_after': 22},
                                       'gated': {'after': 311, 'broken': 0, 'fixed': 1, 'lines_exact_after': 16},
                                       'lines': 34,
                                       'lines_exact_before': 15,
                                       'open': {'after': 291, 'broken': 22, 'fixed': 3, 'lines_exact_after': 10},
                                       'split_ok_lines': 33,
                                       'words': 336},
                               'mlp': {'before': 290,
                                       'closed': {'after': 315, 'broken': 0, 'fixed': 25, 'lines_exact_after': 18},
                                       'gated': {'after': 292, 'broken': 0, 'fixed': 2, 'lines_exact_after': 9},
                                       'lines': 34,
                                       'lines_exact_before': 9,
                                       'open': {'after': 274, 'broken': 23, 'fixed': 7, 'lines_exact_after': 6},
                                       'split_ok_lines': 33,
                                       'words': 336},
                               'svm': {'before': 298,
                                       'closed': {'after': 321, 'broken': 0, 'fixed': 23, 'lines_exact_after': 21},
                                       'gated': {'after': 299, 'broken': 0, 'fixed': 1, 'lines_exact_after': 12},
                                       'lines': 34,
                                       'lines_exact_before': 12,
                                       'open': {'after': 281, 'broken': 22, 'fixed': 5, 'lines_exact_after': 8},
                                       'split_ok_lines': 33,
                                       'words': 336}},
                   'n_test': 1562,
                   'n_train': 1997,
                   'n_unseen': 10,
                   'naca_page_angles_deg': {'2': 0.6491612139879992, '4': -0.14190635898101198, '6': 0.08739376494572614},
                   'page_rotation_max_err_deg': 0.28482218433333295,
                   'pdf_sha256': '57166092520582608a31459c50627334130d8250996f96d58a659a1849972f18',
                   'rotation_max_err_deg': 0.006923554774893481,
                   'rotation_outside_err_deg': 13.28761432169825,
                   'select_dropped': {'(': 1, ')': 1, '-': 10, '.': 11, '/': 2},
                   'slant_rows': [[-30.0, -30.114],
                                  [-20.0, -19.872],
                                  [-10.0, -9.813],
                                  [-5.0, -6.323],
                                  [-2.0, -0.044],
                                  [-1.0, -0.017],
                                  [1.0, 0.024],
                                  [2.0, 0.057],
                                  [5.0, 5.397],
                                  [10.0, 9.772],
                                  [20.0, 19.623],
                                  [30.0, 30.156],
                                  [40.0, 40.022]]}


class OcrGateError(AssertionError):
    """門を通らなかった(どの章の何が外れたかを名指しする)。"""


class Gates:
    """門を 1 つずつ記録し、最後にまとめて判定する。"""

    def __init__(self) -> None:
        self.rows: list[tuple[str, str, bool, str]] = []

    def check(self, chapter: str, name: str, ok, detail: str = "") -> bool:
        ok = bool(ok)
        self.rows.append((chapter, name, ok, detail))
        print("  [%s] %s %s%s" % ("OK" if ok else "NG", chapter, name, (" — " + detail) if detail else ""))
        return ok

    def failed(self):
        return [r for r in self.rows if not r[2]]


# --------------------------------------------------------------------------- #
# データの取り口
# --------------------------------------------------------------------------- #
def naca_cache() -> Path:
    """NACA TN 898 の PDF の置き場(``FULLSEYE_NACA_TN898_DATA`` で上書き)。

    開発の作業木が ``<root>/projects/<checkout>`` にあれば ``<root>/data/fullseye_poc_real/naca_tn898``、
    それ以外はユーザーのキャッシュ。手元の絶対パスをソースに書かないための分岐。
    """
    configured = os.environ.get("FULLSEYE_NACA_TN898_DATA", "").strip()
    if configured:
        return Path(configured).expanduser()
    if ROOT.parent.name.lower() == "projects":
        return ROOT.parent.parent / "data" / "fullseye_poc_real" / "naca_tn898"
    return Path.home() / ".cache" / "fullseye" / "naca_tn898"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_naca_pages(required: bool = False) -> dict | None:
    """PDF を照合してから 3 頁の JPEG を取り出し、灰色 0..1 の配列にして返す。無ければ None。

    取得物は untrusted として扱う: PDF のバイト数と SHA-256、頁ごとの JPEG の SHA-256 が台帳と
    一致しなければ :class:`realdata.RealDataError`。
    """
    path = naca_cache() / PDF_NAME
    if not path.is_file():
        if required:
            raise realdata.RealDataError("NACA TN 898 の PDF が無い: %s(tools/fetch_naca_tn898.py で取得)" % path)
        return None
    raw = path.read_bytes()
    if len(raw) != PDF_BYTES or _sha256(raw) != PDF_SHA256:
        raise realdata.RealDataError("%s のバイト数か SHA-256 が台帳と違う" % path)
    out = {}
    for page, (obj, size, digest) in PAGES.items():
        m = re.search(rb"(?<![0-9])%d 0 obj\s*<<(.*?)>>\s*stream\r?\n" % obj, raw, re.S)
        if m is None:
            raise realdata.RealDataError("PDF にオブジェクト %d の流れが無い" % obj)
        head = m.group(1)
        length = re.search(rb"/Length (\d+)", head)
        if b"/DCTDecode" not in head or length is None or int(length.group(1)) != size:
            raise realdata.RealDataError("オブジェクト %d が JPEG(DCTDecode)%d バイトでない" % (obj, size))
        jpeg = raw[m.end():m.end() + size]
        if _sha256(jpeg) != digest:
            raise realdata.RealDataError("頁 %d の JPEG の SHA-256 が台帳と違う" % page)
        gray = np.asarray(Image.open(io.BytesIO(jpeg)).convert("L"), np.float64) / 255.0
        out[page] = gray
    realdata.mark_read("naca-tn898:" + PDF_NAME)
    return out


def load_skimage_page() -> np.ndarray:
    """scikit-image に同梱の実スキャン ``page``(191 × 384)を灰色 0..1 で返す。照明むらは割り算で均す。"""
    try:
        import skimage.data as skd
    except ImportError as exc:                                   # pragma: no cover
        raise realdata.RealDataError("scikit-image が無い(pip install \"fullseye[skimage]\")") from exc
    g = np.asarray(skd.page(), np.float64) / 255.0
    realdata.mark_read("skimage.data:page")
    background = ndi.uniform_filter(ndi.grey_closing(g, size=(15, 15)), 15)
    return np.clip(g / np.maximum(background, 1e-3), 0.0, 1.0)


# --------------------------------------------------------------------------- #
# 頁 → 行 → 字
# --------------------------------------------------------------------------- #
def otsu_from_histogram(g: np.ndarray) -> float:
    """``gray_histo`` の相対度数から大津のしきい値を出す(字のインクの判定に使う)。"""
    h = L.gray_histo(g, bins=256)
    p = np.asarray(h["relative"], np.float64)
    mids = 0.5 * (h["edges"][:-1] + h["edges"][1:])
    w = np.cumsum(p)
    m = np.cumsum(p * mids)
    between = np.where((w > 0) & (w < 1), (m[-1] * w - m) ** 2 / np.maximum(w * (1 - w), 1e-12), 0.0)
    return float(mids[int(np.argmax(between))])


def level_page(g: np.ndarray) -> tuple[np.ndarray, float]:
    """``text_line_orientation`` で頁の傾きを測り、その分だけ回して戻す。"""
    angle = L.text_line_orientation(g, max_angle=5.0, step=0.05)
    return ndi.rotate(g, angle, reshape=False, order=1, mode="constant", cval=1.0), angle


def find_lines(g: np.ndarray) -> list[tuple[int, int]]:
    """水平にした頁から行の帯 (上, 下) を上から順に返す。上付きの ° でつながった帯は最も薄い行で割る。"""
    ink = ndi.binary_opening(g < LINE_THRESHOLD, np.ones((2, 2)))
    colp = ink.sum(0)
    dense = np.nonzero(colp > 0.01 * g.shape[0])[0]
    c0, c1 = int(dense.min()), int(dense.max())
    prof = ink[:, c0:c1 + 1].sum(1)
    lab, _ = ndi.label(prof > 3)
    bands = [(sl[0].start, sl[0].stop) for sl in ndi.find_objects(lab) if sl[0].stop - sl[0].start >= 12]
    med = float(np.median([b - a for a, b in bands]))
    out, stack = [], list(bands)
    while stack:
        a, b = stack.pop(0)
        if b - a > 1.6 * med:
            lo, hi = a + int(0.4 * med), b - int(0.4 * med)
            cut = lo + int(np.argmin(prof[lo:hi]))
            stack[:0] = [(a, cut), (cut, b)]
            continue
        out.append((a, b))
    return out


def text_span(band_ink: np.ndarray) -> tuple[int, int]:
    """帯の中で最も広い「隙間 GAP_BLOCK 未満で続くインクの列」の範囲(余白の汚れを外す)。"""
    cols = np.nonzero(ndi.binary_opening(band_ink, np.ones((2, 2))).any(0))[0]
    if cols.size == 0:
        return 0, band_ink.shape[1] - 1
    runs, start = [], int(cols[0])
    for u, v in zip(cols[:-1], cols[1:]):
        if v - u > GAP_BLOCK:
            runs.append((start, int(u)))
            start = int(v)
    runs.append((start, int(cols[-1])))
    return max(runs, key=lambda t: t[1] - t[0])


def glyph_features(strip: np.ndarray, mask: np.ndarray, line_h: float) -> np.ndarray:
    """1 字の特徴: 区画濃度 8×6 + 行・列の射影(``gray_projections``)+ 位置と大きさ(``area_center_gray``)。

    ``strip`` は行の帯をその字の列だけ切り出した灰色、``mask`` はその字の画素。
    """
    ink = np.where(mask, 1.0 - strip, 0.0)
    rows = np.nonzero(mask.any(1))[0]
    cols = np.nonzero(mask.any(0))[0]
    r0, r1, c0, c1 = int(rows.min()), int(rows.max()) + 1, int(cols.min()), int(cols.max()) + 1
    box = np.clip(ink[r0:r1, c0:c1], 0.0, 1.0)
    h, w = box.shape
    scaled = (box / max(float(box.max()), 1e-9) * 255).astype(np.uint8)
    zone = np.asarray(Image.fromarray(scaled).resize((GRID_C, GRID_R), Image.BOX), np.float64).ravel() / 255.0
    pr = L.gray_projections(box)
    hp = np.interp(np.linspace(0, h - 1, 8), np.arange(h), pr["horizontal"]) if h > 1 else np.repeat(pr["horizontal"], 8)
    vp = np.interp(np.linspace(0, w - 1, 6), np.arange(w), pr["vertical"]) if w > 1 else np.repeat(pr["vertical"], 6)
    cg = L.area_center_gray(np.clip(ink, 0.0, 1.0))
    geo = [h / line_h, w / line_h, r0 / line_h, r1 / line_h, cg["row"] / line_h, float(mask.sum()) / line_h ** 2]
    return np.concatenate([zone, hp, vp, geo])


_DESKEWED: dict = {}


def read_page(g: np.ndarray, page: int, max_gap: int = MAX_GAP) -> dict:
    """1 頁を傾き直し → 行 → 字に切り、書き起こしと字数が合った行だけ特徴とラベルを返す。"""
    if page not in _DESKEWED:                       # 傾き直しは頁ごとに 1 回(max_gap の掃引で使い回す)
        _DESKEWED[page] = level_page(g)
    flat, angle = _DESKEWED[page]
    thr = otsu_from_histogram(flat)
    bands = find_lines(flat)
    lines = []
    for k, (a, b) in enumerate(bands):
        text = TRANSCRIPTION[page].get(k)
        if text is None:
            continue
        band = flat[a:b]
        lo, hi = text_span(band < thr)
        x0 = max(0, lo - 4)
        crop = band[:, x0:min(flat.shape[1], hi + 5)]
        lab = L.segment_characters(crop < thr, min_area=MIN_AREA, max_gap=max_gap)
        n = int(lab.max())
        want = text.replace(" ", "")
        row = {"page": page, "line": k, "text": text, "n_seg": n, "n_true": len(want), "ok": n == len(want),
               "rows": (a, b), "x0": x0, "lab": lab, "crop": crop, "feats": [], "labels": [], "boxes": []}
        if row["ok"]:
            for i, sl in enumerate(ndi.find_objects(lab), 1):
                m = lab[:, sl[1]] == i
                row["feats"].append(glyph_features(crop[:, sl[1]], m, float(b - a)))
                row["boxes"].append((sl[0].start, sl[0].stop, sl[1].start, sl[1].stop))
            row["labels"] = list(want)
        lines.append(row)
    return {"page": page, "angle": angle, "ink_level": thr, "flat": flat, "bands": bands, "lines": lines}


# --------------------------------------------------------------------------- #
# 章 1・2: 傾きと傾斜(既知の角度で回す・せん断する)
# --------------------------------------------------------------------------- #
def rotation_recovery(img: np.ndarray, gate_range: float = 28.0) -> dict:
    """既知の角度で回した画像の傾きを測り、回す前との差を回した角度と比べる。"""
    base = L.text_line_orientation(img, max_angle=30.0, step=0.05)
    rows = []
    for th in ROT_ANGLES + (ROT_OUTSIDE,):
        r = ndi.rotate(img, th, reshape=True, order=1, mode="constant", cval=1.0)
        est = L.text_line_orientation(r, max_angle=30.0, step=0.05) - base
        rows.append((th, est, est - (-th)))           # ndimage の +θ(反時計回り)は op の −θ
    inside = [abs(e) for th, _, e in rows if abs(th) <= gate_range]
    outside = [abs(e) for th, _, e in rows if abs(th) > 30.0]
    return {"base": base, "rows": rows, "max_err_inside": max(inside), "err_outside": outside[0]}


def shear(img: np.ndarray, angle_deg: float) -> np.ndarray:
    """行の中央を軸にせん断する: 下の行ほど左へ(``text_line_slant`` の正の向き)。"""
    t = math.tan(math.radians(angle_deg))
    h = img.shape[0]
    pad = int(abs(t) * h) + 2
    padded = np.pad(img, ((0, 0), (pad, pad)), constant_values=1.0)
    r0 = (h - 1) / 2.0
    return ndi.affine_transform(padded, np.array([[1.0, 0.0], [t, 1.0]]), offset=(0.0, -r0 * t), order=1, cval=1.0)


def slant_recovery(lines: list[np.ndarray]) -> dict:
    """直立した行をせん断し、``text_line_slant`` が当てた角度(行ごとの中央値)を返す。"""
    base = [L.text_line_slant(x, max_angle=45.0, step=0.25) for x in lines]
    rows = []
    for th in SLANT_ANGLES:
        est = [L.text_line_slant(shear(x, th), max_angle=45.0, step=0.25) - b0 for x, b0 in zip(lines, base)]
        rows.append((th, float(np.median(est)), float(np.median(est)) - th))
    return {"base": base, "rows": rows}


def baseline_angle(page: dict) -> float:
    """独立の検算: 合った行の x 高さの字(acemnorsuvwxz)の底を最小二乗の直線で結んだ傾き[度]の中央値。"""
    flat_letters = set("acemnorsuvwxz")
    slopes = []
    for row in page["lines"]:
        if not row["ok"]:
            continue
        pts = [(0.5 * (c0 + c1), r1) for (r0, r1, c0, c1), ch in zip(row["boxes"], row["labels"]) if ch in flat_letters]
        if len(pts) >= 10:
            x, y = np.asarray(pts, np.float64).T
            slopes.append(math.degrees(math.atan(np.polyfit(x, y, 1)[0])))
    if not slopes:
        raise OcrGateError("下端で検算できる行が無い")
    return float(np.median(slopes))


def chapter_page_angles(g: Gates, page_img: np.ndarray, label: str, tol_inside: float, gate_range: float) -> dict:
    rot = rotation_recovery(page_img, gate_range)
    for th, est, err in rot["rows"]:
        print("    回転 %+6.1f° → 推定 %+8.3f°(誤差 %+.3f°)" % (th, est, err))
    g.check(label, "±%.0f° の回転を %.2f° 以内で当てる" % (gate_range, tol_inside), rot["max_err_inside"] < tol_inside,
            "最大誤差 %.3f°" % rot["max_err_inside"])
    g.check(label, "範囲(±30°)の外の %.0f° は当てられない(限界の表明)" % ROT_OUTSIDE, rot["err_outside"] > 3.0,
            "誤差 %.1f°" % rot["err_outside"])
    return rot


# --------------------------------------------------------------------------- #
# 章 4: 4 種の分類器
# --------------------------------------------------------------------------- #
def stack_glyphs(pages: dict, which) -> tuple[np.ndarray, np.ndarray, list]:
    X, y, where = [], [], []
    for p in which:
        for row in pages[p]["lines"]:
            if row["ok"]:
                X += row["feats"]
                y += row["labels"]
                where += [(p, row["line"], i) for i in range(len(row["labels"]))]
    return np.asarray(X, np.float64), np.asarray(y), where


def pca_fit(X: np.ndarray, k: int) -> dict:
    mu, sd = X.mean(0), X.std(0)
    sd = np.where(sd > 0, sd, 1.0)
    Z = (X - mu) / sd
    centre = Z.mean(0)
    _, _, vt = np.linalg.svd(Z - centre, full_matrices=False)
    return {"mu": mu, "sd": sd, "centre": centre, "P": vt[:k].T}


def pca_apply(model: dict, X: np.ndarray) -> np.ndarray:
    return ((X - model["mu"]) / model["sd"] - model["centre"]) @ model["P"]


def train_all(Ptr: np.ndarray, ytr: np.ndarray, seed: int = 0) -> dict:
    return {"gmm": L.train_class_gmm(Ptr, ytr, n_centers=1, regularize=GMM_REG, seed=seed),
            "knn": L.train_class_knn(Ptr, ytr),
            "mlp": L.train_class_mlp(Ptr, ytr, hidden=MLP_HIDDEN, epochs=MLP_EPOCHS),
            "svm": L.train_class_svm(Ptr, ytr, C=SVM_C, epochs=SVM_EPOCHS, lr=SVM_LR)}


def predict_all(models: dict, P: np.ndarray) -> dict:
    return {"gmm": np.asarray(L.classify_class_gmm(models["gmm"], P)["labels"]),
            "knn": np.asarray(L.classify_class_knn(models["knn"], P, k=1)["labels"]),
            "mlp": np.asarray(L.classify_class_mlp(models["mlp"], P)["labels"]),
            "svm": np.asarray(L.classify_class_svm(models["svm"], P)["labels"])}


def _arrays(obj):
    """モデルの dict の中の配列を順に取り出す(再現性の門で丸ごと比べる)。"""
    if isinstance(obj, dict):
        for k in sorted(obj):
            yield from _arrays(obj[k])
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _arrays(v)
    else:
        yield np.asarray(obj)


def references(Ptr, ytr, Pte) -> dict:
    """外の真値: scikit-learn の 1-NN・線形 SVM・MLP と、scipy で書いた 2 次判別(GMM 1 成分と同じ式)。"""
    from scipy.stats import multivariate_normal
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.neural_network import MLPClassifier
    from sklearn.svm import LinearSVC

    mu, sd = Ptr.mean(0), Ptr.std(0)
    Str, Ste = (Ptr - mu) / sd, (Pte - mu) / sd
    classes = np.unique(ytr)
    logp = []
    for c in classes:
        R = Ptr[ytr == c]
        cov = np.cov(R.T, bias=True).reshape(R.shape[1], R.shape[1]) + GMM_REG * np.eye(R.shape[1])
        logp.append(multivariate_normal(R.mean(0), cov).logpdf(Pte) + math.log(float((ytr == c).mean())))
    import warnings
    os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")   # joblib が物理コア数を調べに行く警告を出さない
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        mlp = MLPClassifier((MLP_HIDDEN,), activation="tanh", max_iter=2000, random_state=0).fit(Str, ytr)
        svc = LinearSVC(C=SVM_C, max_iter=20000).fit(Str, ytr)
    return {"gmm": classes[np.argmax(np.stack(logp), axis=0)],
            "knn": KNeighborsClassifier(1).fit(Str, ytr).predict(Ste),
            "mlp": mlp.predict(Ste),
            "svm": svc.predict(Ste)}


# --------------------------------------------------------------------------- #
# 章 5: 辞書
# --------------------------------------------------------------------------- #
_CORE = re.compile(r"^([^A-Za-z0-9]*)(.*?)([^A-Za-z0-9]*)$")


def _split_word(token: str) -> tuple[str, str, str]:
    m = _CORE.match(token)
    return m.group(1), m.group(2), m.group(3)


def lexicon_words(pages) -> list[str]:
    words = []
    for p in pages:
        for text in TRANSCRIPTION[p].values():
            for tok in text.split():
                core = _split_word(tok)[1]
                if len(core) >= 2:
                    words.append(core)
    return words


def words_of_line(row: dict, chars: list[str]) -> list[str]:
    """字の並びを、字の中心の間隔(字送り)の 1.5 倍を越える隙間で語に分ける(書き起こしの空白は使わない)。"""
    centres = np.array([0.5 * (c0 + c1) for (_, _, c0, c1) in row["boxes"]])
    pitch = float(np.median(np.diff(centres)))
    words, cur = [], [chars[0]]
    for i in range(1, len(chars)):
        if centres[i] - centres[i - 1] > 1.5 * pitch:
            words.append("".join(cur))
            cur = []
        cur.append(chars[i])
    words.append("".join(cur))
    return words


def correct(lexicon: dict, word: str) -> str:
    """辞書に無い語を編集距離 1 の語に直す(3 字未満は直さない)。前後の句読点は残す。"""
    pre, core, post = _split_word(word)
    if len(core) < 3 or L.lookup_lexicon(lexicon, core) == 1.0:
        return word
    s = L.suggest_lexicon(lexicon, core)
    return pre + s["suggestion"] + post if s["distance"] <= 1 else word


def lexicon_effect(test_rows: list, pred: np.ndarray, conf: np.ndarray, lexicons: dict) -> dict:
    """語の正解率(前後)・行の完全一致・壊した語の数を辞書ごとに返す。

    ``lexicons`` の値は ``(辞書, 確信度の上限)``。上限が 1 以下なら、字の確信度(GMM の事後確率)が
    それより低い字を含む語だけを直す(上限 2.0 = 確信度で絞らない)。
    """
    out = {}
    k = 0
    per_line = []
    for row in test_rows:
        n = len(row["labels"])
        chars = [str(c) for c in pred[k:k + n]]
        cf = conf[k:k + n]
        k += n
        words = words_of_line(row, chars)
        lows, i = [], 0
        for w in words:
            lows.append(float(cf[i:i + len(w)].min()))
            i += len(w)
        per_line.append((words, row["text"].split(), lows))
    split_ok = sum(len(w) == len(t) for w, t, _ in per_line)
    scored = [(w, t, c) for w, t, c in per_line if len(w) == len(t)]
    n_words = sum(len(t) for _, t, _ in scored)
    before = sum(a == b for w, t, _ in scored for a, b in zip(w, t))
    lines_before = sum(w == t for w, t, _ in scored)
    out["split_ok_lines"] = split_ok
    out["lines"] = len(per_line)
    out["words"] = n_words
    out["before"] = before
    out["lines_exact_before"] = lines_before
    for name, (lex, below) in lexicons.items():
        after = broken = fixed = 0
        lines_after = 0
        for w, t, lows in scored:
            fixed_line = [correct(lex, a) if low < below else a for a, low in zip(w, lows)]
            lines_after += fixed_line == t
            for a, c, b in zip(w, fixed_line, t):
                after += c == b
                broken += (a == b) and (c != b)
                fixed += (a != b) and (c == b)
        out[name] = {"after": after, "broken": broken, "fixed": fixed, "lines_exact_after": lines_after}
    return out


# --------------------------------------------------------------------------- #
# 章ごとの本体
# --------------------------------------------------------------------------- #
def chapter_skimage_page(g: Gates) -> dict:
    print("\n== 実スキャン %s(CI でも回る)" % SOURCE_PAGE)
    img = load_skimage_page()
    # 191 × 384 の小さな頁で行が曲がっている(綴じ目の反り)。±20° で 0.3° 前後、28° では 0.9° 外れる。
    rot = chapter_page_angles(g, img, "page", tol_inside=0.5, gate_range=20.0)
    return {"image": img, "rotation": rot}


def chapter_naca(g: Gates, raw_pages: dict) -> dict:
    print("\n== NACA TN 898(%s)" % SOURCE_NACA)
    pages = {p: read_page(raw_pages[p], p) for p in PAGES}
    res: dict = {"pages": pages}

    # ---- 1. 行の傾き(頁そのものと、既知の回転)
    res["page_angles"] = {p: pages[p]["angle"] for p in pages}
    resid = {p: baseline_angle(pages[p]) for p in pages}
    res["baseline_residual"] = resid
    print("  頁の傾き(text_line_orientation): %s" % ", ".join("頁 %d: %+.3f°" % (p, a) for p, a in res["page_angles"].items()))
    g.check("傾き", "傾き直した頁の行の下端の傾き(独立の検算)が ±0.05° 以内",
            max(abs(v) for v in resid.values()) < 0.05, ", ".join("%+.4f°" % v for v in resid.values()))
    block = pages[TEST_PAGE]["flat"][400:1000, 300:2200]
    res["rotation"] = chapter_page_angles(g, block, "傾き", tol_inside=0.05, gate_range=28.0)

    # ---- 2. 字の傾斜(既知のせん断)
    test = pages[TEST_PAGE]
    strips = []
    for row in test["lines"]:
        if row["ok"] and len(row["labels"]) >= 40:
            strips.append(row["crop"])
    strips = strips[:6]
    sl = slant_recovery(strips)
    res["slant"] = sl
    for th, est, err in sl["rows"]:
        print("    せん断 %+5.1f° → 推定 %+7.2f°(誤差 %+.2f°)" % (th, est, err))
    big = [abs(err) for th, _, err in sl["rows"] if abs(th) >= 5.0]
    small = [abs(est) for th, est, _ in sl["rows"] if abs(th) <= 2.0]
    g.check("傾斜", "直立した印字の傾斜は 0(行 %d 本の中央値)" % len(strips), abs(float(np.median(sl["base"]))) < 0.5,
            "%+.2f°" % float(np.median(sl["base"])))
    g.check("傾斜", "|せん断| ≥ 5° を 2° 以内で当てる", len(big) == 9 and max(big) < 2.0, "最大誤差 %.2f°" % max(big))
    g.check("傾斜", "|せん断| ≤ 2° は 0 と答える(1 画素未満、限界の表明)", len(small) == 4 and max(small) < 0.5,
            "最大 %.2f°" % max(small))

    # ---- 3. 切り出しの数え合わせ
    counts = {}
    for p in pages:
        rows = pages[p]["lines"]
        counts[p] = {"lines": len(rows), "matched": sum(r["ok"] for r in rows),
                     "over": sum(r["n_seg"] > r["n_true"] for r in rows),
                     "under": sum(r["n_seg"] < r["n_true"] for r in rows),
                     "glyphs_true": sum(r["n_true"] for r in rows), "glyphs_seg": sum(r["n_seg"] for r in rows)}
        print("  頁 %d: 書き起こした行 %d、字数が合った行 %d(多すぎ %d・少なすぎ %d)、字 %d / 切り出し %d"
              % (p, counts[p]["lines"], counts[p]["matched"], counts[p]["over"], counts[p]["under"],
                 counts[p]["glyphs_true"], counts[p]["glyphs_seg"]))
        for r in rows:
            if not r["ok"]:
                print("      行 %2d: 切り出し %d / 正解 %d  %s" % (r["line"], r["n_seg"], r["n_true"], r["text"]))
    res["counts"] = counts
    n_lines = sum(c["lines"] for c in counts.values())
    n_match = sum(c["matched"] for c in counts.values())
    g.check("切り出し", "書き起こした 100 行", n_lines == 100, "%d 行" % n_lines)
    g.check("切り出し", "字数が書き起こしと合う行 ≥ 75 %", n_match >= 75, "%d / %d 行" % (n_match, n_lines))
    sweep = {}
    for mg in range(0, 6):
        sweep[mg] = sum(sum(r["ok"] for r in read_page(raw_pages[p], p, max_gap=mg)["lines"]) for p in pages)
    res["gap_sweep"] = sweep
    print("  max_gap と字数が合う行: %s" % ", ".join("%d→%d" % kv for kv in sweep.items()))
    g.check("切り出し", "max_gap = %d が掃引の最良" % MAX_GAP, sweep[MAX_GAP] == max(sweep.values()), str(sweep))
    # select_characters は高さで選ぶ: 句読点(. , - など)は字の高さの中央値の半分に届かず落ちる。
    test_ok = [r for r in test["lines"] if r["ok"]]
    dropped = Counter()
    kept_total = 0
    for r in test_ok:
        sel = L.select_characters(r["lab"])
        kept_total += int(sel.max())
        keep_boxes = {(s[1].start, s[1].stop) for s in ndi.find_objects(sel) if s is not None}
        for (r0, r1, c0, c1), ch in zip(r["boxes"], r["labels"]):
            if (c0, c1) not in keep_boxes:
                dropped[ch] += 1
    res["select_dropped"] = dict(dropped)
    n_test_glyphs = sum(len(r["labels"]) for r in test_ok)
    punct = sum(v for k, v in dropped.items() if not k.isalnum())
    print("  select_characters(既定)が落とした字 %d / %d: %s" % (n_test_glyphs - kept_total, n_test_glyphs,
                                                            ", ".join("%r×%d" % kv for kv in dropped.most_common(12))))
    g.check("切り出し", "select_characters は句読点を落とす(高さで選ぶ限界)", punct > 0 and punct >= 0.8 * sum(dropped.values()),
            "落ちた字のうち句読点 %d / %d" % (punct, sum(dropped.values())))

    # ---- 4. 分類器
    Xtr, ytr, wtr = stack_glyphs(pages, TRAIN_PAGES)
    Xte, yte, wte = stack_glyphs(pages, (TEST_PAGE,))
    model = pca_fit(Xtr, N_PCA)
    Ptr, Pte = pca_apply(model, Xtr), pca_apply(model, Xte)
    unseen = sorted(set(yte.tolist()) - set(ytr.tolist()))
    n_unseen = int(np.isin(yte, unseen).sum())
    print("  学習 %d 字(%d 種、頁 %s)/ 試験 %d 字(%d 種、頁 %d)。学習に無い字種 %s が試験に %d 字"
          % (len(ytr), len(set(ytr.tolist())), TRAIN_PAGES, len(yte), len(set(yte.tolist())), TEST_PAGE, unseen, n_unseen))
    # 漏れの門
    g.check("分類", "学習と試験は頁が別", not ({w[0] for w in wtr} & {w[0] for w in wte}),
            "学習 %s / 試験 %s" % (sorted({w[0] for w in wtr}), sorted({w[0] for w in wte})))
    from scipy.spatial import cKDTree
    dmin = float(cKDTree(Xtr).query(Xte)[0].min())
    g.check("分類", "試験の字と特徴が同一の字が学習に無い", dmin > 1e-6, "最小距離 %.3g" % dmin)
    model2 = pca_fit(np.vstack([Xtr, Xte]), N_PCA)
    g.check("分類", "標準化と主成分は学習だけで決めた(試験を混ぜると変わる)",
            not np.allclose(model["mu"], model2["mu"]), "平均の差 %.3g" % float(np.abs(model["mu"] - model2["mu"]).max()))
    t0 = time.perf_counter()
    models = train_all(Ptr, ytr, seed=0)
    pred = predict_all(models, Pte)
    t_train = time.perf_counter() - t0
    acc = {k: float((v == yte).mean()) for k, v in pred.items()}
    seen = ~np.isin(yte, unseen)
    acc_seen = {k: float((v[seen] == yte[seen]).mean()) for k, v in pred.items()}
    refs = references(Ptr, ytr, Pte)
    acc_ref = {k: float((v == yte).mean()) for k, v in refs.items()}
    agree = {k: float((pred[k] == refs[k]).mean()) for k in pred}
    majority = Counter(ytr.tolist()).most_common(1)[0]
    ceiling = 1.0 - n_unseen / len(yte)
    print("  正解率(全 %d 字、上限 %.4f = 学習に無い字種を除いた割合)" % (len(yte), ceiling))
    for k in ("gmm", "knn", "mlp", "svm"):
        print("    %-3s  Fullseye %.4f(既知の字種だけ %.4f)/ 外の実装 %.4f / 予測の一致 %.4f"
              % (k, acc[k], acc_seen[k], acc_ref[k], agree[k]))
    for k in pred:
        g.check("分類", "%s の正解率 ≥ 0.93" % k.upper(), acc[k] >= 0.93, "%.4f" % acc[k])
    g.check("分類", "k-NN(k=1)は scikit-learn と予測が完全一致", agree["knn"] == 1.0, "%.4f" % agree["knn"])
    g.check("分類", "GMM(1 成分)は scipy の 2 次判別と予測が 99.9 % 以上一致", agree["gmm"] >= 0.999, "%.4f" % agree["gmm"])
    g.check("分類", "MLP・SVM は外の実装と正解率の差 < 0.03(別の最適化なので予測の完全一致は求めない)",
            abs(acc["mlp"] - acc_ref["mlp"]) < 0.03 and abs(acc["svm"] - acc_ref["svm"]) < 0.03,
            "MLP %+.4f / SVM %+.4f" % (acc["mlp"] - acc_ref["mlp"], acc["svm"] - acc_ref["svm"]))
    # 対照: 学習のラベルを混ぜると、正解率は多数派の字の割合の近くまで落ちる(特徴が漏れていない)。
    rng = np.random.default_rng(12345)
    shuffled = rng.permutation(ytr)
    ctrl = float((np.asarray(L.classify_class_knn(L.train_class_knn(Ptr, shuffled), Pte, k=1)["labels"]) == yte).mean())
    prior = float(np.mean(yte == majority[0]))
    g.check("分類", "対照: ラベルを混ぜた k-NN は 0.2 未満に落ちる", ctrl < 0.2,
            "%.4f(多数派 %r の割合 %.4f)" % (ctrl, majority[0], prior))
    confusions = Counter((str(a), str(b)) for k in pred for a, b in zip(yte, pred[k]) if a != b)
    print("  取り違えの多い組(4 種の合計、正解 → 読み): %s"
          % ", ".join("%s→%s×%d" % (a, b, n) for (a, b), n in confusions.most_common(10)))
    res.update({"n_train": int(len(ytr)), "n_test": int(len(yte)), "n_classes_train": len(set(ytr.tolist())),
                "unseen": unseen, "n_unseen": n_unseen, "acc": acc, "acc_seen": acc_seen, "acc_ref": acc_ref,
                "agree": agree, "control": ctrl, "prior": prior, "ceiling": ceiling, "dmin": dmin,
                "confusions": confusions.most_common(10), "pred": pred, "yte": yte, "wte": wte,
                "t_train_s": t_train})

    # ---- 6. 再現性
    models_b = train_all(Ptr, ytr, seed=0)
    pred_b = predict_all(models_b, Pte)
    same_pred = all(np.array_equal(pred[k], pred_b[k]) for k in pred)
    same_model = all(len(list(_arrays(models[k]))) == len(list(_arrays(models_b[k])))
                     and all(np.array_equal(a, b) for a, b in zip(_arrays(models[k]), _arrays(models_b[k])))
                     for k in models)
    g.check("再現性", "同じ seed で 2 回学習: 4 種ともモデルの配列が完全一致", same_model)
    g.check("再現性", "同じ seed で 2 回学習: 4 種とも予測が完全一致", same_pred)
    gmm2 = [L.train_class_gmm(Ptr, ytr, n_centers=2, regularize=GMM_REG, seed=s) for s in (0, 0, 1)]
    p2 = [np.asarray(L.classify_class_gmm(m, Pte)["labels"]) for m in gmm2]
    same_seed = all(np.array_equal(a, b) for a, b in zip(_arrays(gmm2[0]), _arrays(gmm2[1])))
    diff_seed = not all(np.array_equal(a, b) for a, b in zip(_arrays(gmm2[0]), _arrays(gmm2[2])))
    g.check("再現性", "GMM 2 成分: seed 0 を 2 回 = 同じ、seed 1 = 初期値が変わって別のモデル", same_seed and diff_seed,
            "正解率 seed 0 %.4f / seed 1 %.4f" % (float((p2[0] == yte).mean()), float((p2[2] == yte).mean())))
    res["gmm2_acc"] = [float((p == yte).mean()) for p in p2]

    # ---- 5. 辞書
    open_lex = L.create_lexicon(lexicon_words(TRAIN_PAGES))
    closed_lex = L.create_lexicon(lexicon_words(TRAIN_PAGES + (TEST_PAGE,)))
    test_rows = [r for r in test["lines"] if r["ok"]]
    post = np.asarray(L.evaluate_class_gmm(models["gmm"], Pte)["posterior"]).max(axis=1)
    wrong_g = pred["gmm"] != yte
    res["gmm_posterior"] = {"wrong_median": float(np.median(post[wrong_g])), "right_median": float(np.median(post[~wrong_g])),
                            "flagged": int((post < CONF_BELOW).sum()),
                            "flagged_wrong": int((wrong_g & (post < CONF_BELOW)).sum()), "wrong": int(wrong_g.sum())}
    gp = res["gmm_posterior"]
    print("  GMM の事後確率: 誤った字の中央値 %.5f / 正しい字の中央値 %.5f(誤りでも確信が高い)。%.3f 未満の字 %d 字に、"
          "GMM の誤り %d 字のうち %d 字" % (gp["wrong_median"], gp["right_median"], CONF_BELOW, gp["flagged"], gp["wrong"],
                                         gp["flagged_wrong"]))
    lex = {}
    for k in pred:
        lex[k] = lexicon_effect(test_rows, pred[k], post, {"open": (open_lex, 2.0), "closed": (closed_lex, 2.0),
                                                           "gated": (open_lex, CONF_BELOW)})
        e = lex[k]
        print("  辞書(%s): 語 %d、そのまま %d → 開いた語彙 %d(直した %d・壊した %d)/ 開いた語彙 + 確信度 %d(直した %d・壊した %d)"
              "/ 閉じた語彙 %d(直した %d・壊した %d)。行の完全一致 %d → 開 %d・閉 %d(%d 行)"
              % (k, e["words"], e["before"], e["open"]["after"], e["open"]["fixed"], e["open"]["broken"],
                 e["gated"]["after"], e["gated"]["fixed"], e["gated"]["broken"],
                 e["closed"]["after"], e["closed"]["fixed"], e["closed"]["broken"],
                 e["lines_exact_before"], e["open"]["lines_exact_after"], e["closed"]["lines_exact_after"], e["lines"]))
    res["lexicon"] = lex
    res["lexicon_sizes"] = {"open": len(open_lex["words"]), "closed": len(closed_lex["words"])}
    e0 = lex["gmm"]
    g.check("辞書", "字送りで分けた語の数が書き起こしと合う行 ≥ 95 %", e0["split_ok_lines"] >= 0.95 * e0["lines"],
            "%d / %d 行" % (e0["split_ok_lines"], e0["lines"]))
    g.check("辞書", "閉じた語彙は 4 種とも語の正解を増やし、壊さない",
            all(lex[k]["closed"]["after"] > lex[k]["before"] and lex[k]["closed"]["broken"] == 0 for k in lex),
            ", ".join("%s %d→%d" % (k, lex[k]["before"], lex[k]["closed"]["after"]) for k in lex))
    g.check("辞書", "開いた語彙は正しく読めた語を壊し、4 種とも語の正解が減る(限界の表明)",
            all(lex[k]["open"]["after"] < lex[k]["before"] and lex[k]["open"]["broken"] > 0 for k in lex),
            ", ".join("%s %d→%d(壊した %d)" % (k, lex[k]["before"], lex[k]["open"]["after"], lex[k]["open"]["broken"])
                      for k in lex))
    g.check("辞書", "確信度で絞ると開いた語彙でも壊さず、減らさない",
            all(lex[k]["gated"]["broken"] == 0 and lex[k]["gated"]["after"] >= lex[k]["before"] for k in lex),
            ", ".join("%s %d→%d" % (k, lex[k]["before"], lex[k]["gated"]["after"]) for k in lex))
    return res


# --------------------------------------------------------------------------- #
# 図
# --------------------------------------------------------------------------- #
def render_reading(res: dict, first: int = 1, n_lines: int = 8) -> np.ndarray:
    """試験頁の行を並べ、字ごとの箱を k-NN の読みの正誤で塗る。○ = 正、× = 誤、灰 = 字数が合わず採点の外。"""
    page = res["pages"][TEST_PAGE]
    pred = res["pred"]["knn"]
    index = {w: i for i, w in enumerate(res["wte"])}
    rows = [r for r in page["lines"] if r["line"] >= first][:n_lines]
    width = max(r["crop"].shape[1] for r in rows)
    tiles = []
    right, wrong, neutral = fs.role_rgb8("right"), fs.role_rgb8("wrong"), fs.role_rgb8("neutral")
    from PIL import ImageFont
    font = ImageFont.truetype(str(figs._japanese_font_path()), 22)
    for r in rows:
        crop = (np.clip(r["crop"], 0, 1) * 255).astype(np.uint8)
        im = Image.fromarray(np.repeat(crop[:, :, None], 3, axis=2))
        band = Image.new("RGB", (width, crop.shape[0] + 34), (255, 255, 255))
        band.paste(im, (0, 0))
        draw = ImageDraw.Draw(band)
        if r["ok"]:
            for i, (r0, r1, c0, c1) in enumerate(r["boxes"]):
                ch = pred[index[(TEST_PAGE, r["line"], i)]]
                ok = ch == r["labels"][i]
                col = right if ok else wrong
                draw.rectangle([c0, r0, c1 - 1, r1 - 1], outline=col, width=2)
                draw.text((c0 + 2, crop.shape[0] + 4), str(ch), fill=col, font=font)
        else:
            for sl in ndi.find_objects(r["lab"]):
                draw.rectangle([sl[1].start, sl[0].start, sl[1].stop - 1, sl[0].stop - 1], outline=neutral, width=1)
            draw.text((4, crop.shape[0] + 4), "切り出し %d 字 / 正解 %d 字(採点の外)" % (r["n_seg"], r["n_true"]),
                      fill=neutral, font=font)
        tiles.append(np.asarray(band))
    gap = np.full((6, width, 3), 255, np.uint8)
    out = []
    for t in tiles:
        out += [t, gap]
    return np.vstack(out[:-1])


def write_figures(page_res: dict, res: dict | None, g: Gates) -> None:
    if not figs.enabled() or res is None:
        return
    figs.save("reading", render_reading(res),
              caption="NACA TN 898 の 5 頁(試験頁)。箱 = segment_characters の字、下の字 = k-NN の読み。"
                      "%s = 正、%s = 誤、灰 = 字数が書き起こしと合わず採点の外。"
                      % (fs.ROLE_MARKERS["right"] + "青", fs.ROLE_MARKERS["wrong"] + "橙"), source=SOURCE_NACA)
    rot, prot = res["rotation"], page_res["rotation"]
    th = [r[0] for r in rot["rows"] if abs(r[0]) <= 30]
    figs.save_plot("rotation", [("NACA 5 頁", th, [r[2] for r in rot["rows"] if abs(r[0]) <= 30]),
                                ("scikit-image page", th, [r[2] for r in prot["rows"] if abs(r[0]) <= 30])],
                   kinds=["line", "line"], colors=["emphasis", "neutral"],
                   xlabel="回した角度 [°]", ylabel="推定の誤差 [°]",
                   title="行の傾きの復元(text_line_orientation、範囲 ±30°)",
                   caption="頁を既知の角度で回して当てた。タイプ打ちの頁は ±0.01° 以内、曲がった小さな頁は 0.3° 前後。"
                           "範囲外の %.0f° は誤差 %.1f°(NACA)。" % (ROT_OUTSIDE, rot["err_outside"]),
                   source=SOURCE_NACA)
    sl = res["slant"]["rows"]
    xs = [r[0] for r in sl]
    figs.save_plot("slant", [("推定", xs, [r[1] for r in sl]), ("y = x", [-40, 40], [-40, 40])],
                   kinds=["scatter", "line"], styles=[None, "dashed"], colors=["emphasis", "reference"],
                   xlabel="せん断の角度 [°]", ylabel="text_line_slant [°]",
                   title="字の傾斜の復元(±2° 以内は 0 と答える)",
                   caption="直立した印字を既知の角度でせん断した。縦画は約 20 画素なので 2° は 1 画素未満で見えない。",
                   source=SOURCE_NACA)
    sw = res["gap_sweep"]
    figs.save_plot("gap_sweep", [("字数が合う行", list(sw), list(sw.values()))], kinds=["line"], colors=["emphasis"],
                   xlabel="segment_characters の max_gap [画素]", ylabel="行の数(100 行中)",
                   title="切り出しの数え合わせ(書き起こしの字数と一致する行)",
                   caption="小さいと、かすれて割れた字が 2 字に、大きいと詰まった大文字が 1 字になる。", source=SOURCE_NACA)
    header = ["分類器", "Fullseye", "既知の字種だけ", "外の実装", "予測の一致"]
    names = {"gmm": "GMM(1 成分)", "knn": "k-NN(k=1)", "mlp": "MLP(48)", "svm": "線形 SVM"}
    refs = {"gmm": "scipy 2 次判別", "knn": "sklearn 1-NN", "mlp": "sklearn MLP", "svm": "sklearn LinearSVC"}
    rows = [[names[k], "%.4f" % res["acc"][k], "%.4f" % res["acc_seen"][k],
             "%.4f(%s)" % (res["acc_ref"][k], refs[k]), "%.4f" % res["agree"][k]] for k in ("gmm", "knn", "mlp", "svm")]
    figs.save_table("classifiers", header, rows,
                    title="4 種の分類器(学習 %d 字 / 試験 %d 字、頁が別)" % (res["n_train"], res["n_test"]),
                    caption="同じ特徴(区画濃度・射影・重心、主成分 %d)。上限 %.4f は学習に無い字種 %d 字を除いた割合。"
                            "ラベルを混ぜた対照は %.4f。" % (N_PCA, res["ceiling"], res["n_unseen"], res["control"]))
    header = ["分類器", "語(そのまま)", "開いた語彙(壊した)", "+ 確信度(壊した)", "閉じた語彙(壊した)", "行の完全一致 前→閉"]
    rows = []
    for k in ("gmm", "knn", "mlp", "svm"):
        e = res["lexicon"][k]
        rows.append([names[k], "%d / %d" % (e["before"], e["words"]),
                     "%d(%d)" % (e["open"]["after"], e["open"]["broken"]),
                     "%d(%d)" % (e["gated"]["after"], e["gated"]["broken"]),
                     "%d(%d)" % (e["closed"]["after"], e["closed"]["broken"]),
                     "%d → %d / %d" % (e["lines_exact_before"], e["closed"]["lines_exact_after"], e["lines"])])
    figs.save_table("lexicon", header, rows, title="辞書で読み違いを直す(編集距離 1)",
                    caption="開いた語彙 = 学習頁の語 %d 語、閉じた語彙 = 試験頁の語も入れた %d 語(許される文字列が先に分かる場合の上限)。"
                            "確信度 = GMM の事後確率が %.3f 未満の字を含む語だけ直す。"
                            % (res["lexicon_sizes"]["open"], res["lexicon_sizes"]["closed"], CONF_BELOW))


# --------------------------------------------------------------------------- #
def _recordable(res: dict, page_res: dict, g: Gates) -> dict:
    return {
        "page_rotation_max_err_deg": page_res["rotation"]["max_err_inside"],
        "naca_page_angles_deg": {str(k): v for k, v in res["page_angles"].items()},
        "baseline_residual_deg": {str(k): v for k, v in res["baseline_residual"].items()},
        "rotation_max_err_deg": res["rotation"]["max_err_inside"], "rotation_outside_err_deg": res["rotation"]["err_outside"],
        "slant_rows": [[a, round(b, 3)] for a, b, _ in res["slant"]["rows"]],
        "counts": {str(k): v for k, v in res["counts"].items()}, "gap_sweep": res["gap_sweep"],
        "select_dropped": res["select_dropped"],
        "n_train": res["n_train"], "n_test": res["n_test"], "n_unseen": res["n_unseen"], "ceiling": res["ceiling"],
        "acc": res["acc"], "acc_seen": res["acc_seen"], "acc_ref": res["acc_ref"], "agree": res["agree"],
        "control": res["control"], "gmm2_acc": res["gmm2_acc"], "gmm_posterior": res["gmm_posterior"],
        "lexicon": {k: {kk: vv for kk, vv in v.items()} for k, v in res["lexicon"].items()},
        "gates": len(g.rows), "failed": len(g.failed()),
    }


def main() -> None:
    t0 = time.perf_counter()
    g = Gates()
    page_res = chapter_skimage_page(g)
    try:
        raw_pages = load_naca_pages(required=False)
    except realdata.RealDataError as exc:
        raise SystemExit("NACA TN 898 の取得物を拒否: %s" % exc) from exc
    res = None
    if raw_pages is None:
        print("\n== NACA TN 898 は未取得(%s)。py -3.11 tools/fetch_naca_tn898.py で取得すると全章が回る。" % naca_cache())
        if not RECORDED:
            raise SystemExit("記録値 RECORDED が空のまま —— 実データで回して RECORDED_JSON を写す")
        print("記録値(RECORDED、%s に実データで測った値): %s" % (RECORDED["date"], json.dumps(RECORDED, ensure_ascii=False, sort_keys=True)))
    else:
        res = chapter_naca(g, raw_pages)
        record = _recordable(res, page_res, g)
        print("\nRECORDED_JSON=" + json.dumps(record, ensure_ascii=False, sort_keys=True))
    write_figures(page_res, res, g)
    errors = figs.errors()
    if errors:
        raise SystemExit("図の書き出しで失敗: " + "; ".join(errors))
    bad = g.failed()
    if bad:
        raise OcrGateError("門が %d 本外れた: %s" % (len(bad), "; ".join("%s %s" % r[:2] for r in bad)))
    print("門 %d 本すべて通過(%.1f s)\nPASS" % (len(g.rows), time.perf_counter() - t0))


if __name__ == "__main__":
    main()
