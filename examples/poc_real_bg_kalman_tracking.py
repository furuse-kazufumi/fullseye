# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""実写の固定カメラの動画で背景を推定して人を切り出し、カルマン追跡で柱の裏を通り抜ける。

Background estimation and Kalman tracking on real static-camera video (LASIESTA, per-pixel ground
truth): cut out the walking person, score the mask against the hand-labelled truth, compare with
OpenCV's MOG2, and follow the person through an occlusion behind a pillar.

主役の op(opsmv の新しい op): ``create_bg_esti`` / ``run_bg_esti`` / ``update_bg_esti`` /
``give_bg_esti``(画素ごとのカルマン背景、Ridder ほか 1995)、``filter_kalman``(線形カルマン 1 周期)、
``opening_seg``(くびれで切り離して塊にする)、``atan2_image``(進む向き)。

データ: LASIESTA(Universidad Politécnica de Madrid、CC BY-SA 4.0、Cuevas ほか 2016)の屋内 3 本
(``I_SI_01`` = 3 人が順に横切る、``I_OC_01`` = 柱の裏を通る、``I_OC_02`` = 画面の外で折り返す)。
352×288、各 250〜300 コマ、全コマに画素ごとの真値(物体ごとの色、輪郭の灰色 = 判定しない画素)。
原本は repo に入れず ``tools/fetch_lasiesta.py`` で repo 外へ取得する(書庫の SHA-256 を固定)。
この PoC は展開後のコマと真値のバイト列の SHA-256 も固定し、違えば止まる(:data:`FRAME_DIGESTS`)。

手順と照合:

1. **背景差分の F 値**(CDnet と同じ数え方: 全コマの TP/FP/FN を足し、輪郭の灰色は数えない)。
   パラメータは ``I_SI_01``(学習用)だけで選び、``I_OC_01`` / ``I_OC_02``(評価用)に持ち込む。
   比べる相手は OpenCV の MOG2(色、影の判定つき)で、同じく ``I_SI_01`` で ``varThreshold`` を選ぶ。
2. **動かない塊の吸収**: ``run_bg_esti`` は前景の画素の更新を弱めるので、照明や反射で一度
   前景になった塊は背景へ戻らず「幽霊」として残る。重心が 8 コマ動かない塊の領域だけ
   ``update_bg_esti`` で背景へ取り込む段を足し、足す前と後の F 値を比べる。
3. **推定した背景**(``give_bg_esti``)を、真値が背景と言う画素だけで取った時間の中央値と比べる。
4. **追跡**: 塊の重心を等速モデルの ``filter_kalman`` で追い、99 % の NIS 門で対応づける。
   塊の面積が直前の中央値の半分を切ったら「一部が隠れた」とみなして更新に使わない(重心が偏る)。
   比べる相手は予測をしない最近傍の対応づけ。過程の雑音 q は ``I_SI_01`` で選ぶ。
   照合は真値の重心との距離、遮蔽をまたいで同じ番号が続くか、出てきたコマでの位置の誤差。
5. 限界: 隠れている間に向きを変えると等速の予測は外れる。``I_OC_02`` は画面の右の外で
   折り返して戻ってくる。真値の重心から ``atan2_image`` で向きを出し、隠れる前と後の
   向きの差を測ってから、追跡の結果を読む。

結果(2026-11-08、この機械で実測。``RECORDED`` と同じ値):

* 背景差分(評価列の F): Fullseye は I_OC_01 0.890 / I_OC_02 0.878、MOG2 は 0.987 / 0.884。
  灰色 1 枚の画素ごとのカルマンは、色と影の判定を持つ MOG2 に I_OC_01 で 0.10 負け、I_OC_02 は
  ほぼ並ぶ。動かない塊の吸収(``update_bg_esti``)は I_OC_01 で F を 0.794 → 0.890(適合率
  0.681 → 0.830)に上げた。床の反射で一度前景になった塊が、吸収なしでは最後まで残る。
  I_OC_02 では差が出ない(0.881 → 0.878)。推定した背景は MOG2 の方が真値の背景に近い
  (RMS 0.4 対 2.3〜3.1、0〜255)。
* 追跡: I_OC_01 では柱の裏の 26 コマを等速の予測でつなぎ、同じ番号のまま拾い直した
  (拾い直した時の誤差 5.7 画素、見えているコマの誤差の中央値 7.7 画素)。予測しない最近傍は
  柱で見失う。I_OC_02 は隠れている間に向きが 165° 変わり、カルマンは新しい番号で拾い直す
  (この列では最近傍も番号を継げない)。

正直に書いておくこと: 数値で選んだのは学習列(I_SI_01)での閾値・利得・吸収の有無・MOG2 の
``varThreshold``・過程の雑音 q だけ。追跡の作り(手すりで割れた体を 6 画素でまとめる、2 コマ
続けて見えた塊から始める、左右の縁に触れる塊を「一部が隠れた」と扱う)は 3 本の列を見ながら
決めた。評価列の数字はその分だけ楽観側に寄っている。

データが無い環境(CI)では取得せず、下の ``RECORDED`` を印字し、op の契約の門(OpenCV の
``cv2.KalmanFilter`` との一致、背景の分散の定常値 = リッカチ方程式の閉形式)だけを回す。

実行例::

    py -3.11 tools/fetch_lasiesta.py
    py -3.11 examples/poc_real_bg_kalman_tracking.py

図(``FULLSEYE_FIGURE_DIR`` があるときだけ): 柱を通り抜ける軌跡(代表図)、追跡の動画、
真値・Fullseye・MOG2 の切り出しの比較、推定した背景、追跡の誤差の時系列、F 値の表。
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402
import realdata  # noqa: E402

L = fs.ledger

SOURCE = ("LASIESTA (C. Cuevas, E. M. Yáñez, N. García, Computer Vision and Image Understanding 152, "
          "103-117 (2016), doi:10.1016/j.cviu.2016.08.005; Universidad Politécnica de Madrid), "
          "CC BY-SA 4.0. Frames shown unmodified except for drawn overlays")

#: 学習(パラメータを選ぶ)と評価(持ち込むだけ)の列。
TRAIN = "I_SI_01"
HELD_OUT = ("I_OC_01", "I_OC_02")
#: 列 → (コマ数, 展開後のコマと真値を順に連結したバイト列の SHA-256)。2026-11-08 に測った値。
FRAME_DIGESTS = {
    "I_SI_01": (300, "520a7403cacf259c6f7e06d17da9e4dad05938ccc6657acc3fca85ff5812e6eb"),
    "I_OC_01": (250, "2e8957ed8b95be18c00e14acd0e5c6fbc281199212874cd2e353c42ffbd0c117"),
    "I_OC_02": (250, "7c34e911f9e677b26dc64ff6c2ed936d8ff11481c72708667f18eef234263825"),
}

#: 背景差分の候補(学習列で選ぶ)。閾値は [0, 1] の灰色の差。
FS_THRESHOLDS = (0.04, 0.05, 0.06, 0.08, 0.10)
FS_GAINS = (0.0, 0.02)
MOG2_VAR = (8.0, 16.0, 32.0, 64.0)
#: 動かない塊の判定: 重心がこのコマ数ずっと TOL_PX 以内に在る塊は背景へ取り込む。
STILL_FRAMES = 8
STILL_TOL_PX = 2.0
#: 切り出しの後処理: 3×3 の opening_seg で切り離し、この面積[画素]未満の塊は捨てる。
MIN_BLOB_PX = 60
#: 追跡の検出に使う塊の最小面積[画素]と、軌跡を始める塊の最小面積[画素]。
MIN_DET_PX = 150
MIN_INIT_PX = 800
#: この画素数まで離れた前景の片は 1 つの塊にまとめる(手すり・脚の間で割れた体)。
GROUP_PX = 6
#: 軌跡を始めるときの 2 コマ目の対応の半径[画素](速度をこの 2 点の差で初期化する)。
INIT_RADIUS = 40.0
#: 2 自由度の χ² の 99 % 点(NIS の門)。
CHI2_99_2DOF = 9.2103
#: 観測の雑音の分散[画素²]と、過程の雑音 q の候補(加速度の白色雑音、学習列で選ぶ)。
MEAS_VAR = 4.0
Q_CANDIDATES = (0.01, 0.05, 0.2)
#: 予測しない最近傍の対応づけの半径[画素]。
NN_RADIUS = 30.0
#: 塊の面積が直前 10 回の中央値のこの割合を切ったら「一部が隠れた」とみなす。
PARTIAL_AREA = 0.5
#: 続けて見失ってよいコマ数(超えたら軌跡を閉じる)。
MAX_MISS = 45
#: 進む向きを測る真値の重心の区間[コマ]と、出てきた直後に飛ばすコマ数(体が出きるまで重心が偏る)。
HEADING_SPAN = 12
HEADING_SKIP = 6
#: 真値の物体が「見えている」とみなす面積(その列の中央値に対する割合)。
VISIBLE_FRAC = 0.25

# 実データを走らせた後、stdout の ``RECORDED_JSON`` と同じ値へ固定する。
RECORDED: dict = {'absorbed_frames': {'I_OC_01': 46, 'I_OC_02': 72, 'I_SI_01': 113},
 'bg_rms_255': {'I_OC_01': {'fullseye': 3.136, 'mog2': 0.412, 'plain': 3.578},
                'I_OC_02': {'fullseye': 2.349, 'mog2': 0.401, 'plain': 2.139},
                'I_SI_01': {'fullseye': 3.079, 'mog2': 0.544, 'plain': 3.772}},
 'contract': {'bg_variance_closed_form': 0.000270156,
              'bg_variance_steady': 0.000270156,
              'kalman_vs_opencv_max': 1.81899e-12,
              'mean_nis': 1.98888},
 'crossing': {'I_OC_01': {'hidden_frames': 26,
                          'kalman_err_at_reacquire': 5.73,
                          'kalman_same_id': True,
                          'nn_same_id': False,
                          'turn_deg': 10.1},
              'I_OC_02': {'hidden_frames': 29,
                          'kalman_err_at_reacquire': None,
                          'kalman_same_id': False,
                          'nn_same_id': False,
                          'turn_deg': 164.6}},
 'date': '2026-11-08',
 'digests': {'I_OC_01': '2e8957ed8b95be18c00e14acd0e5c6fbc281199212874cd2e353c42ffbd0c117',
             'I_OC_02': '7c34e911f9e677b26dc64ff6c2ed936d8ff11481c72708667f18eef234263825',
             'I_SI_01': '520a7403cacf259c6f7e06d17da9e4dad05938ccc6657acc3fca85ff5812e6eb'},
 'f': {'I_OC_01': {'absorb': [0.8898, 0.8297, 0.9593],
                   'mog2': [0.9868, 0.9933, 0.9804],
                   'plain': [0.7944, 0.6813, 0.9525]},
       'I_OC_02': {'absorb': [0.8779, 0.8581, 0.8987],
                   'mog2': [0.8841, 0.8502, 0.9209],
                   'plain': [0.8813, 0.8813, 0.8814]},
       'I_SI_01': {'absorb': [0.8679, 0.8935, 0.8437],
                   'mog2': [0.947, 0.9887, 0.9087],
                   'plain': [0.8531, 0.893, 0.8166]}},
 'q': 0.2,
 'selected': {'gain': 0.0, 'mog2_var': 64.0, 'plain_gain': 0.0, 'plain_threshold': 0.06, 'threshold': 0.05},
 'tracks': {'I_OC_01': {'kalman': {'median_err': 7.74, 'n_tracks': 1, 'p90_err': 12.19},
                        'nn': {'median_err': 10.26, 'n_tracks': 1, 'p90_err': 145.98}},
            'I_OC_02': {'kalman': {'median_err': 15.38, 'n_tracks': 2, 'p90_err': 88.51},
                        'nn': {'median_err': 13.87, 'n_tracks': 2, 'p90_err': 162.09}},
            'I_SI_01': {'kalman': {'median_err': 8.83, 'n_tracks': 3, 'p90_err': 20.58},
                        'nn': {'median_err': 8.5, 'n_tracks': 2, 'p90_err': 238.32}}}}


class TrackGateError(AssertionError):
    """門を通らなかった。"""


class Gates:
    """門を 1 つずつ記録し、最後にまとめて判定する。"""

    def __init__(self) -> None:
        self.rows: list[tuple[str, bool, str]] = []

    def check(self, name: str, ok, detail: str = "") -> bool:
        ok = bool(ok)
        self.rows.append((name, ok, detail))
        print("  [%s] %s%s" % ("OK" if ok else "NG", name, (" — " + detail) if detail else ""))
        return ok

    def failed(self):
        return [r for r in self.rows if not r[1]]


# --------------------------------------------------------------------------- #
# データ
# --------------------------------------------------------------------------- #
def lasiesta_cache() -> Path:
    """LASIESTA の repo 外の置き場(``FULLSEYE_LASIESTA_DATA`` で上書き)。

    開発の作業木が ``<root>/projects/<checkout>`` にあれば ``<root>/data/fullseye_poc_real/lasiesta``、
    それ以外はユーザーのキャッシュ。手元の絶対パスをソースに焼き込まないための分岐
    (``realdata.sem_metal_layer_cache`` と同じ形)。
    """
    configured = os.environ.get("FULLSEYE_LASIESTA_DATA", "").strip()
    if configured:
        return Path(configured).expanduser()
    if ROOT.parent.name.lower() == "projects":
        return ROOT.parent.parent / "data" / "fullseye_poc_real" / "lasiesta"
    return Path.home() / ".cache" / "fullseye" / "lasiesta"


def _frame_paths(root: Path, seq: str, n: int) -> list[tuple[Path, Path]]:
    pairs = [(root / seq / seq / ("%s-%d.bmp" % (seq, k)), root / seq / ("%s-GT" % seq) / ("%s-GT_%d.png" % (seq, k)))
             for k in range(1, n + 1)]
    missing = [str(p) for pair in pairs for p in pair if not p.is_file()]
    if missing:
        raise realdata.RealDataError("%s のコマが欠けている(%d 個、最初 %s)" % (seq, len(missing), missing[0]))
    extra = root / seq / seq / ("%s-%d.bmp" % (seq, n + 1))
    if extra.exists():
        raise realdata.RealDataError("%s のコマが台帳の %d より多い" % (seq, n))
    return pairs


def load_sequence(root: Path, seq: str, check_digest: bool = True) -> dict:
    """1 列を読み、SHA-256 を照合して RGB のコマと真値の前景・判定しない画素・物体 1 を返す。"""
    n, digest = FRAME_DIGESTS[seq]
    pairs = _frame_paths(root, seq, n)
    h = hashlib.sha256()
    rgb, gt = [], []
    for fp, gp in pairs:
        fb, gb = fp.read_bytes(), gp.read_bytes()
        h.update(fb)
        h.update(gb)
        rgb.append(np.asarray(Image.open(fp).convert("RGB")))
        gt.append(np.asarray(Image.open(gp).convert("RGB")))
    got = h.hexdigest()
    if check_digest and got != digest:
        raise realdata.RealDataError("%s のコマと真値の SHA-256 %s が台帳と違う" % (seq, got))
    rgb = np.stack(rgb)
    gt = np.stack(gt)
    ignore = (gt == 128).all(-1)
    background = (gt == 0).all(-1)
    objects = {name: (gt == np.array(col)).all(-1) for name, col in
               (("red", (255, 0, 0)), ("green", (0, 255, 0)), ("yellow", (255, 255, 0)), ("white", (255, 255, 255)))}
    known = ignore | background
    for m in objects.values():
        known |= m
    if not known.all():
        raise realdata.RealDataError("%s の真値に台帳に無い色がある(%d 画素)" % (seq, int((~known).sum())))
    realdata.mark_read("lasiesta:" + seq)
    return {"seq": seq, "rgb": rgb, "gray": rgb.astype(np.float64).mean(-1) / 255.0,
            "fg": ~(ignore | background), "ignore": ignore, "objects": objects, "digest": got}


# --------------------------------------------------------------------------- #
# 背景差分
# --------------------------------------------------------------------------- #
SE3 = np.ones((3, 3), bool)


def clean_mask(mask: np.ndarray) -> np.ndarray:
    """``opening_seg`` で 3×3 の収縮に残らない細かい塊を落とし、小さい塊を捨てる。"""
    labels = L.opening_seg(mask, SE3)
    sizes = np.bincount(labels.ravel())
    keep = sizes >= MIN_BLOB_PX
    keep[0] = False
    return keep[labels]


def run_fullseye(gray: np.ndarray, threshold: float, gain: float, absorb: bool):
    """画素ごとのカルマン背景で全コマを切り出す。``absorb`` で動かない塊を背景へ取り込む。"""
    model = L.create_bg_esti(gray[0], threshold=threshold, foreground_gain=gain)
    masks = np.zeros(gray.shape, bool)
    history: list[list[tuple[float, float]]] = []
    n_absorbed = 0
    for k in range(1, len(gray)):
        res = L.run_bg_esti(model, gray[k])
        model = res["model"]
        m = clean_mask(res["foreground"])
        masks[k] = m
        if not absorb:
            continue
        lab, n = ndi.label(m)
        cents = list(ndi.center_of_mass(m, lab, range(1, n + 1))) if n else []
        history.append(cents)
        if len(history) <= STILL_FRAMES:
            continue
        still = np.zeros(m.shape, bool)
        for i, c in enumerate(cents):
            if all(any(math.hypot(c[0] - d[0], c[1] - d[1]) < STILL_TOL_PX for d in past)
                   for past in history[-STILL_FRAMES - 1:-1]):
                still |= lab == i + 1
        if still.any():
            n_absorbed += 1
            model = L.update_bg_esti(model, gray[k], ndi.binary_dilation(still, iterations=2))
    return masks, model, n_absorbed


def run_mog2(rgb: np.ndarray, var: float):
    import cv2
    sub = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=float(var), detectShadows=True)
    masks = np.zeros(rgb.shape[:3], bool)
    for k in range(len(rgb)):
        f = sub.apply(np.ascontiguousarray(rgb[k][..., ::-1]))
        masks[k] = clean_mask(f == 255)                 # 127 = 影と判定された画素は背景に数える
    return masks, sub


def f_measure(pred: np.ndarray, data: dict) -> dict:
    """CDnet の数え方: 全コマ(最初のコマは初期化に使うので除く)の TP/FP/FN を足し、灰色は数えない。"""
    p, fg, valid = pred[1:], data["fg"][1:], ~data["ignore"][1:]
    tp = int((p & fg & valid).sum())
    fp = int((p & ~fg & valid).sum())
    fn = int((~p & fg & valid).sum())
    prec = tp / max(1, tp + fp)
    rec = tp / max(1, tp + fn)
    return {"F": 2 * prec * rec / max(1e-12, prec + rec), "precision": prec, "recall": rec,
            "tp": tp, "fp": fp, "fn": fn}


def clean_plate(data: dict) -> np.ndarray:
    """真値が背景と言うコマだけで取った、画素ごとの灰色の時間の中央値(背景の外の参照)。"""
    g = np.where(data["fg"] | data["ignore"], np.nan, data["gray"])
    with np.errstate(all="ignore"):
        plate = np.nanmedian(g, axis=0)
    return plate


# --------------------------------------------------------------------------- #
# 追跡
# --------------------------------------------------------------------------- #
def detections(mask: np.ndarray) -> list[tuple[float, float, int, bool]]:
    """塊の (重心の行, 列, 面積, 左右の縁に触れるか)。

    手すりの裏で体が何片にも割れるので、``GROUP_PX`` 画素まで離れた片は 1 つの塊にまとめる
    (まとめるのは番号だけで、重心と面積は元の前景の画素で数える)。左右の縁に触れる塊は体の
    一部が画面の外にある(この 3 本では人は左右から出入りし、上下の縁は撮り方で常に切れている)。
    """
    groups, n = ndi.label(ndi.binary_dilation(mask, iterations=GROUP_PX))
    lab = np.where(mask, groups, 0)
    if n == 0:
        return []
    sizes = np.bincount(lab.ravel(), minlength=n + 1)[1:]
    idx = [i + 1 for i in range(n) if sizes[i] >= MIN_DET_PX]
    if not idx:
        return []
    cents = ndi.center_of_mass(mask, lab, idx)
    edge = set(np.unique(np.r_[lab[:, 0], lab[:, -1]]).tolist()) - {0}
    return [(float(c[0]), float(c[1]), int(sizes[i - 1]), i in edge) for i, c in zip(idx, cents)]


def _cv_model(q: float):
    F = np.eye(4)
    F[0, 2] = F[1, 3] = 1.0
    H = np.zeros((2, 4))
    H[0, 0] = H[1, 1] = 1.0
    G = np.array([[0.5, 0.0], [0.0, 0.5], [1.0, 0.0], [0.0, 1.0]])
    return F, H, q * G @ G.T


def track(masks: np.ndarray, q: float, predictive: bool = True) -> dict:
    """1 本の軌跡を追う(物体は 1 つずつ現れる列が前提)。

    ``predictive`` が真なら ``filter_kalman`` の予測と NIS の門で対応づけ、偽なら直前の位置から
    ``NN_RADIUS`` 以内の最も近い塊に対応づける(予測しない比較の相手)。
    返りの ``status`` は 0 = 観測なし、1 = 観測で更新、2 = 一部が隠れた(更新に使わない)。
    画像の左右の縁は遮蔽物と同じに扱う: 縁に触れる塊からは軌跡を始めず、対応した塊が縁に触れて
    いれば「一部が隠れた」として更新に使わない(入りかけ・出かけの体の重心は偏る)。
    軌跡は 2 コマ続けて ``INIT_RADIUS`` 以内に見えた塊から始め、速度はその 2 点の差で置く。
    """
    F, H, Q = _cv_model(q)
    shape = masks.shape[1:]
    n = len(masks)
    out = {"id": np.full(n, -1), "pos": np.full((n, 2), np.nan), "vel": np.full((n, 2), np.nan),
           "status": np.zeros(n, int), "nis": np.full(n, np.nan)}
    cur = None
    tentative = None
    n_tracks = 0
    for k in range(n):
        dets = detections(masks[k])
        if cur is None:
            whole = [d for d in dets if not d[3] and d[2] >= MIN_INIT_PX]
            if tentative is not None:
                near = [d for d in whole if math.hypot(d[0] - tentative[0], d[1] - tentative[1]) < INIT_RADIUS]
                if near:
                    d = min(near, key=lambda d: math.hypot(d[0] - tentative[0], d[1] - tentative[1]))
                    v = (d[0] - tentative[0], d[1] - tentative[1])
                    cur = {"id": n_tracks, "x": np.array([d[0], d[1], v[0], v[1]]),
                           "P": np.diag([MEAS_VAR, MEAS_VAR, 2 * MEAS_VAR, 2 * MEAS_VAR]), "miss": 0,
                           "areas": [tentative[2], d[2]]}
                    n_tracks += 1
                    tentative = None
                    out["id"][k], out["pos"][k], out["vel"][k], out["status"][k] = cur["id"], d[:2], v, 1
                    continue
            tentative = max(whole, key=lambda d: d[2]) if whole else None
            continue
        pred = L.filter_kalman(cur["x"], cur["P"], None, F, H, Q, MEAS_VAR)
        best = None
        if predictive:
            S_inv = np.linalg.inv(H @ pred["P"] @ H.T + MEAS_VAR * np.eye(2))
            for d in dets:
                nu = np.array(d[:2]) - H @ pred["x"]
                nis = float(nu @ S_inv @ nu)
                if nis < CHI2_99_2DOF and (best is None or nis < best[0]):
                    best = (nis, d)
        else:
            for d in dets:
                dist = math.hypot(d[0] - cur["x"][0], d[1] - cur["x"][1])
                if dist < NN_RADIUS and (best is None or dist < best[0]):
                    best = (dist, d)
        status = 0
        if best is not None:
            whole = not best[1][3] and best[1][2] >= PARTIAL_AREA * float(np.median(cur["areas"][-10:]))
            status = 1 if whole else 2
        if predictive:
            res = L.filter_kalman(cur["x"], cur["P"], best[1][:2] if status == 1 else None, F, H, Q, MEAS_VAR)
            cur["x"], cur["P"] = res["x"], res["P"]
            if status == 1:
                out["nis"][k] = res["nis"]
        elif status:
            cur["x"] = np.array([best[1][0], best[1][1], best[1][0] - cur["x"][0], best[1][1] - cur["x"][1]])
        if status == 1:
            cur["areas"].append(best[1][2])
        cur["miss"] = 0 if status else cur["miss"] + 1
        out["id"][k], out["pos"][k], out["vel"][k], out["status"][k] = cur["id"], cur["x"][:2], cur["x"][2:], status
        r, c = cur["x"][:2]
        outside = r < -20 or c < -20 or r > shape[0] + 20 or c > shape[1] + 20
        if cur["miss"] > MAX_MISS or outside:
            cur = None
    out["n_tracks"] = n_tracks
    return out


def truth_track(data: dict) -> dict:
    """真値の前景(1 コマに物体は 1 つ)の重心と、見えているコマ。"""
    fg = data["fg"]
    area = fg.sum((1, 2))
    vis = area > VISIBLE_FRAC * float(np.median(area[area > 0]))
    cent = np.full((len(fg), 2), np.nan)
    for k in np.nonzero(area)[0]:
        cent[k] = ndi.center_of_mass(fg[k])
    return {"area": area, "visible": vis, "centroid": cent}


def occlusion_gaps(visible: np.ndarray, min_gap: int = 4) -> list[tuple[int, int]]:
    """見えているコマの間の、``min_gap`` コマ以上の空き(最後に見えたコマ, 次に見えたコマ)。"""
    ks = np.nonzero(visible)[0]
    return [(int(a), int(b)) for a, b in zip(ks[:-1], ks[1:]) if b - a >= min_gap]


def heading_deg(cent: np.ndarray, k0: int, k1: int) -> float:
    """``k0``〜``k1`` の真値の重心の変位から、進む向き[度](``atan2_image`` で、行を下向き正)。"""
    d = cent[k1] - cent[k0]
    ang = L.atan2_image(np.array([[d[0]]]), np.array([[d[1]]]))
    return float(np.degrees(ang[0, 0]))


def score_track(tr: dict, truth: dict) -> dict:
    vis = truth["visible"]
    err = np.hypot(tr["pos"][:, 0] - truth["centroid"][:, 0], tr["pos"][:, 1] - truth["centroid"][:, 1])
    on = vis & np.isfinite(err)
    ids = sorted(set(int(i) for i in tr["id"][vis] if i >= 0))
    return {"err": err, "median_err": float(np.median(err[on])) if on.any() else float("nan"),
            "p90_err": float(np.percentile(err[on], 90)) if on.any() else float("nan"),
            "coverage": float(on.sum() / max(1, vis.sum())), "ids": ids, "n_tracks": int(tr["n_tracks"])}


def crossing(tr: dict, truth: dict, gap: tuple[int, int]) -> dict:
    """遮蔽の前後で同じ番号が続いたか、出てきてから 5 コマ以内に観測で更新できたか、その時の誤差。"""
    a, b = gap
    before = int(tr["id"][a])
    after_ids = [int(i) for i in tr["id"][b:b + 6]]
    reacquired = [k for k in range(b, min(b + 6, len(tr["id"]))) if tr["status"][k] == 1]
    k = reacquired[0] if reacquired else b
    err = float(np.hypot(*(tr["pos"][k] - truth["centroid"][k]))) if np.isfinite(tr["pos"][k]).all() else float("nan")
    pred_b = tr["pos"][b - 1] if np.isfinite(tr["pos"][b - 1]).all() else tr["pos"][a]
    return {"gap": [a, b], "hidden_frames": b - a - 1, "id_before": before,
            "same_id": before >= 0 and bool(reacquired) and all(i == before for i in after_ids[:k - b + 1]),
            "reacquired_frame": k if reacquired else None, "err_at_reacquire": err,
            "prediction_err_at_reappear": float(np.hypot(*(pred_b - truth["centroid"][b])))}


# --------------------------------------------------------------------------- #
# CI でも回す op の契約の門
# --------------------------------------------------------------------------- #
def contract_gates(g: Gates) -> dict:
    print("\n== op の契約(実データなしでも回る)")
    import cv2
    rng = np.random.default_rng(20261108)
    q = 0.05
    F, H, Q = _cv_model(q)
    kf = cv2.KalmanFilter(4, 2, 0, cv2.CV_64F)
    kf.transitionMatrix = F.copy()
    kf.measurementMatrix = H.copy()
    kf.processNoiseCov = Q.copy()
    kf.measurementNoiseCov = MEAS_VAR * np.eye(2)
    x0 = np.array([100.0, 50.0, 0.0, 0.0])
    P0 = np.diag([MEAS_VAR, MEAS_VAR, 25.0, 25.0])
    kf.statePost = x0.reshape(4, 1).copy()
    kf.errorCovPost = P0.copy()
    x, P = x0.copy(), P0.copy()
    state = np.array([100.0, 50.0, 0.8, -2.5])
    G = np.array([[0.5, 0.0], [0.0, 0.5], [1.0, 0.0], [0.0, 1.0]])
    worst_x = worst_p = 0.0
    nis = []
    for k in range(1000):
        state = F @ state + G @ rng.normal(0, math.sqrt(q), 2)      # 真の運動もフィルタと同じモデル
        z = state[:2] + rng.normal(0, math.sqrt(MEAS_VAR), 2)
        observed = (k % 17) not in (5, 6, 7)          # 観測の欠けたコマを混ぜる
        res = L.filter_kalman(x, P, z if observed else None, F, H, Q, MEAS_VAR)
        kf.predict()
        if observed:
            kf.correct(z.reshape(2, 1))
            ref_x, ref_p = kf.statePost.ravel(), kf.errorCovPost
            nis.append(res["nis"])
        else:
            ref_x, ref_p = kf.statePre.ravel(), kf.errorCovPre
            # OpenCV は観測の無いコマで statePost を進めないので、次の予測のために写す
            kf.statePost = kf.statePre.copy()
            kf.errorCovPost = kf.errorCovPre.copy()
        x, P = res["x"], res["P"]
        worst_x = max(worst_x, float(np.abs(x - ref_x).max()))
        worst_p = max(worst_p, float(np.abs(P - ref_p).max()))
    g.check("filter_kalman の状態が cv2.KalmanFilter と一致(1000 コマ、欠け 3/17)", worst_x < 1e-9, "最大差 %.1e" % worst_x)
    g.check("filter_kalman の共分散が cv2.KalmanFilter と一致", worst_p < 1e-9, "最大差 %.1e(Joseph 形 対 標準形)" % worst_p)
    mean_nis = float(np.mean(nis))
    g.check("真のモデルの下で NIS の平均 ≈ 観測の次元 2", 1.8 < mean_nis < 2.2, "%.3f(n=%d)" % (mean_nis, len(nis)))

    # 背景の分散の定常値: p = (p + qb) r / (p + qb + r) の正の根(画素ごとのカルマンのリッカチ方程式)。
    qb, rb = 1e-4, 1e-3
    model = L.create_bg_esti(np.zeros((4, 4)), process_noise=qb, measurement_noise=rb, threshold=0.5)
    for _ in range(400):
        model = L.run_bg_esti(model, np.zeros((4, 4)))["model"]
    p_inf = (-qb + math.sqrt(qb * qb + 4 * qb * rb)) / 2.0
    got = float(model["variance"].mean())
    g.check("背景の分散の定常値 = リッカチの閉形式", abs(got - p_inf) < 1e-12, "%.6e 対 %.6e" % (got, p_inf))
    step = np.zeros((6, 6))
    step[2:4, 2:4] = 1.0
    m0 = L.create_bg_esti(np.zeros((6, 6)), threshold=0.5)
    res = L.run_bg_esti(m0, step)
    region = np.zeros((6, 6), bool)
    region[:3] = True
    m1 = L.update_bg_esti(m0, step, region)
    g.check("run_bg_esti は閾値を超えた画素だけを前景にする", int(res["foreground"].sum()) == 4)
    g.check("update_bg_esti は領域の外の背景と分散を動かさない",
            np.array_equal(L.give_bg_esti(m1)[3:], np.zeros((3, 6))) and np.array_equal(m1["variance"][3:], m0["variance"][3:])
            and L.give_bg_esti(m1)[2, 2] > 0)
    return {"kalman_vs_opencv_max": max(worst_x, worst_p), "mean_nis": mean_nis, "bg_variance_steady": got,
            "bg_variance_closed_form": p_inf}


# --------------------------------------------------------------------------- #
# 図
# --------------------------------------------------------------------------- #
def _font(size: int):
    path = figs._japanese_font_path(fail_closed=False)
    return ImageFont.truetype(str(path), size) if path else ImageFont.load_default()


def _overlay(rgb: np.ndarray, mask: np.ndarray, color, alpha=0.45) -> np.ndarray:
    out = rgb.astype(np.float64).copy()
    out[mask] = out[mask] * (1 - alpha) + np.array(color) * alpha
    edge = mask & ~ndi.binary_erosion(mask)
    out[edge] = color
    return out.astype(np.uint8)


def _polyline(draw, pts, color, width, scale):
    seg = []
    for p in pts:
        if np.isfinite(p).all():
            seg.append((p[1] * scale, p[0] * scale))
        elif len(seg) > 1:
            draw.line(seg, fill=color, width=width)
            seg = []
        else:
            seg = []
    if len(seg) > 1:
        draw.line(seg, fill=color, width=width)


def render_track_frame(data: dict, k: int, kal: dict, nn: dict, truth: dict, scale: int = 2,
                       upto: int | None = None, label: str = "") -> np.ndarray:
    upto = k if upto is None else upto
    base = _overlay(data["rgb"][k], data["fg"][k], (255, 255, 255), alpha=0.0)   # 真値の前景は白い輪郭だけ
    im = Image.fromarray(base).resize((base.shape[1] * scale, base.shape[0] * scale), Image.NEAREST)
    draw = ImageDraw.Draw(im)
    cent = truth["centroid"][:upto + 1]
    for p in cent[truth["visible"][:upto + 1]]:
        draw.ellipse([p[1] * scale - 2, p[0] * scale - 2, p[1] * scale + 2, p[0] * scale + 2], fill=(255, 255, 255))
    # 最近傍(予測なし): 番号が変わるところで線を切る
    _polyline(draw, np.where((nn["id"][:upto + 1] == nn["id"][max(0, int(np.argmax(nn["id"] >= 0)))])[:, None],
                             nn["pos"][:upto + 1], np.nan), fs.role_rgb8("wrong"), 3, scale)
    meas = np.where((kal["status"][:upto + 1] == 1)[:, None], kal["pos"][:upto + 1], np.nan)
    pred = kal["pos"][:upto + 1].copy()
    _polyline(draw, pred, fs.role_rgb8("emphasis"), 2, scale)
    _polyline(draw, meas, fs.role_rgb8("right"), 4, scale)
    p = kal["pos"][upto]
    if np.isfinite(p).all():
        draw.ellipse([p[1] * scale - 7, p[0] * scale - 7, p[1] * scale + 7, p[0] * scale + 7],
                     outline=fs.role_rgb8("right"), width=3)
    if label:
        lines = label.split("\n")
        size = 18 if scale >= 2 else 13
        font = _font(size)
        draw.rectangle([0, 0, im.width, (size + 8) * len(lines) + 2], fill=(0, 0, 0))
        for i, line in enumerate(lines):
            draw.text((8, 4 + i * (size + 8)), line, fill=(255, 255, 255), font=font)
    return np.asarray(im)


def render_mask_compare(data: dict, k: int, fs_mask: np.ndarray, mog_mask: np.ndarray, scale: int = 1) -> np.ndarray:
    """左から 実写 / 真値 / Fullseye / MOG2。正しい前景 = 空色、誤検出 = 朱、見逃し = 白。"""
    fg, ign = data["fg"][k], data["ignore"][k]
    tiles = [data["rgb"][k]]
    gt = np.zeros(fg.shape + (3,), np.uint8)
    gt[fg] = 255
    gt[ign] = 128
    tiles.append(gt)
    for m in (fs_mask, mog_mask):
        t = (data["rgb"][k] * 0.35).astype(np.uint8)
        t[m & fg] = fs.role_rgb8("right")
        t[m & ~fg & ~ign] = fs.role_rgb8("wrong")
        t[~m & fg & ~ign] = (255, 255, 255)
        tiles.append(t)
    gap = np.full((fg.shape[0], 6, 3), 255, np.uint8)
    row = np.hstack([x for t in tiles for x in (t, gap)][:-1])
    return np.asarray(Image.fromarray(row).resize((row.shape[1] * scale, row.shape[0] * scale), Image.NEAREST))


def write_figures(res: dict) -> None:
    if not figs.enabled():
        return
    oc1 = res["data"]["I_OC_01"]
    tr = res["tracks"]["I_OC_01"]
    truth = res["truth"]["I_OC_01"]
    gap = res["crossing"]["I_OC_01"]["kalman"]["gap"]
    k_show = min(len(oc1["rgb"]) - 1, gap[1] + 12)
    figs.save("pillar_crossing",
              render_track_frame(oc1, k_show, tr["kalman"], tr["nn"], truth,
                                 label="柱の裏 %d コマを等速の予測でつなぐ\n空色=観測で更新 / 橙=予測だけ / 朱=予測なしの最近傍"
                                 % res["crossing"]["I_OC_01"]["kalman"]["hidden_frames"]),
              caption="LASIESTA I_OC_01 の第 %d コマ。空色の太線 = filter_kalman が観測で更新した位置、橙の細線 = 予測だけで"
                      "進めた区間(柱の裏 %d コマと一部が隠れたコマ)、朱 = 予測しない最近傍(柱で見失い、出てきた人を拾えない)、"
                      "白点 = 真値の重心、白い輪郭 = 真値の前景。柱に半分入りかけたコマを更新に使ったので予測は上へ傾き、"
                      "出てきたコマで %.0f 画素ずれたが、NIS の門の内側で同じ番号のまま拾い直した。"
                      % (k_show + 1, res["crossing"]["I_OC_01"]["kalman"]["hidden_frames"],
                         res["crossing"]["I_OC_01"]["kalman"]["prediction_err_at_reappear"]), source=SOURCE)
    frames = []
    lo = max(0, int(np.argmax(truth["visible"])) - 2)
    for k in range(lo, len(oc1["rgb"]), 4):
        frames.append(render_track_frame(oc1, k, tr["kalman"], tr["nn"], truth, scale=1,
                                         label="第 %d コマ" % (k + 1)))
    figs.save_gif("tracking_movie", frames, fps=10,
                  caption="I_OC_01 を 4 コマおきに再生。空色 = カルマンの観測更新、橙 = 予測だけ、朱 = 予測なしの最近傍。")
    sel = res["selected"]
    for seq, k in (("I_OC_01", 150), ("I_OC_02", 110)):
        figs.save("masks_%s" % seq.lower(),
                  render_mask_compare(res["data"][seq], k, res["masks"][seq]["fullseye"][k], res["masks"][seq]["mog2"][k]),
                  caption="%s の第 %d コマ。左から 実写 / 真値(白 = 前景、灰 = 判定しない輪郭)/ Fullseye(閾値 %.2f、"
                          "動かない塊の吸収あり)/ MOG2(varThreshold %g)。空色 = 正しい前景、朱 = 誤検出、白 = 見逃し。"
                          % (seq, k + 1, sel["threshold"], sel["mog2_var"]), source=SOURCE)
    plate = res["plates"]["I_OC_01"]
    bg_fs = res["bg_images"]["I_OC_01"]["fullseye"]
    bg_plain = res["bg_images"]["I_OC_01"]["plain"]
    diff = lambda a: np.clip(np.abs(a - plate) * 4.0, 0, 1)  # noqa: E731
    panels = [np.nan_to_num(plate), bg_plain, bg_fs, diff(np.nan_to_num(bg_plain)), diff(bg_fs)]
    white = np.ones((plate.shape[0], 6))
    row = np.hstack([x for p in panels for x in (p, white)][:-1])
    figs.save("background", row, gray=True,
              caption="I_OC_01 の背景。左から 真値の背景画素の時間の中央値 / give_bg_esti(吸収なし)/ give_bg_esti(吸収あり)/ "
                      "差の 4 倍(吸収なし)/ 差の 4 倍(吸収あり)。", source=SOURCE)
    kal_err = res["scores"]["I_OC_01"]["kalman"]["err"]
    nn_err = res["scores"]["I_OC_01"]["nn"]["err"]
    ks = np.arange(len(kal_err)) + 1                      # コマの番号は 1 始まり(配布物の名前と同じ)
    vis = truth["visible"]
    figs.save_plot("track_error",
                   [("カルマン(予測 + NIS の門)", list(ks[vis]), list(np.nan_to_num(kal_err[vis], nan=-5))),
                    ("最近傍(予測なし)", list(ks[vis]), list(np.nan_to_num(nn_err[vis], nan=-5)))],
                   kinds=["scatter", "scatter"], colors=["right", "wrong"],
                   xlabel="コマ", ylabel="真値の重心からの距離 [画素](軌跡が無いコマは −5)",
                   title="I_OC_01: 柱の裏(第 %d〜%d コマ)の後で差が開く" % (gap[0] + 2, gap[1]),
                   caption="真値の物体が見えているコマだけを打った。", source=SOURCE)
    header = ["列", "Fullseye F(吸収なし)", "Fullseye F(吸収あり)", "MOG2 F", "カルマン 番号の数", "最近傍 番号の数"]
    rows = []
    for seq in (TRAIN,) + HELD_OUT:
        f = res["f"][seq]
        rows.append([seq + ("(学習)" if seq == TRAIN else "(評価)"), "%.3f" % f["plain"]["F"], "%.3f" % f["absorb"]["F"],
                     "%.3f" % f["mog2"]["F"], str(res["scores"][seq]["kalman"]["n_tracks"]),
                     str(res["scores"][seq]["nn"]["n_tracks"])])
    figs.save_table("scores", header, rows, title="背景差分の F 値と追跡の番号の数(LASIESTA 屋内 3 本)",
                    caption="F 値は CDnet の数え方(輪郭の灰色を除く全コマの和)。パラメータは I_SI_01 だけで選んだ。")


# --------------------------------------------------------------------------- #
# 本体
# --------------------------------------------------------------------------- #
def real_chapter(g: Gates, root: Path) -> dict:
    print("\n== 実データ: %s" % SOURCE)
    print("置き場: %s" % root)
    data = {seq: load_sequence(root, seq) for seq in (TRAIN,) + HELD_OUT}
    for seq, d in data.items():
        print("  %s: %d コマ %s、前景の画素 %d、SHA-256 %s…" % (seq, len(d["rgb"]), d["rgb"].shape[1:3],
                                                         int(d["fg"].sum()), d["digest"][:16]))
    g.check("3 本ともコマと真値の SHA-256 が台帳と一致", True)

    # 1. 学習列で選ぶ
    print("\n-- 1. 背景差分のパラメータを %s だけで選ぶ" % TRAIN)
    tr = data[TRAIN]
    grid = []
    for thr in FS_THRESHOLDS:
        for gain in FS_GAINS:
            for absorb in (False, True):
                masks, _, _ = run_fullseye(tr["gray"], thr, gain, absorb)
                sc = f_measure(masks, tr)
                grid.append((sc["F"], thr, gain, absorb))
                print("   Fullseye 閾値 %.2f 利得 %.2f 吸収 %s: F %.3f" % (thr, gain, "あり" if absorb else "なし", sc["F"]))
    best_plain = max(r for r in grid if not r[3])
    best_abs = max(r for r in grid if r[3])
    mog = []
    for var in MOG2_VAR:
        masks, _ = run_mog2(tr["rgb"], var)
        mog.append((f_measure(masks, tr)["F"], var))
        print("   MOG2 varThreshold %g: F %.3f" % (var, mog[-1][0]))
    best_mog = max(mog)
    sel = {"threshold": best_abs[1], "gain": best_abs[2], "plain_threshold": best_plain[1], "plain_gain": best_plain[2],
           "mog2_var": best_mog[1]}
    print("   選んだ: 吸収あり 閾値 %.2f 利得 %.2f / 吸収なし 閾値 %.2f 利得 %.2f / MOG2 %g"
          % (sel["threshold"], sel["gain"], sel["plain_threshold"], sel["plain_gain"], sel["mog2_var"]))

    # 2. 評価列へ持ち込む
    print("\n-- 2. 評価列へそのまま持ち込む(F 値、CDnet の数え方)")
    f_scores, mask_store, bg_images, plates, bg_err = {}, {}, {}, {}, {}
    for seq, d in data.items():
        m_plain, mod_plain, _ = run_fullseye(d["gray"], sel["plain_threshold"], sel["plain_gain"], False)
        m_abs, mod_abs, n_abs = run_fullseye(d["gray"], sel["threshold"], sel["gain"], True)
        m_mog, sub = run_mog2(d["rgb"], sel["mog2_var"])
        f_scores[seq] = {"plain": f_measure(m_plain, d), "absorb": f_measure(m_abs, d), "mog2": f_measure(m_mog, d),
                         "absorbed_frames": n_abs}
        mask_store[seq] = {"fullseye": m_abs, "mog2": m_mog}
        plate = clean_plate(d)
        plates[seq] = plate
        mog_bg = sub.getBackgroundImage()
        mog_bg = mog_bg.astype(np.float64).mean(-1) / 255.0 if mog_bg is not None else np.full(plate.shape, np.nan)
        bg_images[seq] = {"plain": L.give_bg_esti(mod_plain), "fullseye": L.give_bg_esti(mod_abs), "mog2": mog_bg}
        ok = np.isfinite(plate)
        bg_err[seq] = {k: float(np.sqrt(np.mean((v[ok] - plate[ok]) ** 2))) * 255.0 for k, v in bg_images[seq].items()}
        f = f_scores[seq]
        print("   %s: Fullseye 吸収なし F %.3f(P %.3f R %.3f)/ 吸収あり F %.3f(P %.3f R %.3f、吸収 %d コマ)/ "
              "MOG2 F %.3f(P %.3f R %.3f)" % (seq, f["plain"]["F"], f["plain"]["precision"], f["plain"]["recall"],
                                              f["absorb"]["F"], f["absorb"]["precision"], f["absorb"]["recall"], n_abs,
                                              f["mog2"]["F"], f["mog2"]["precision"], f["mog2"]["recall"]))
        print("      最後の背景と真値の背景の中央値の差(RMS、0〜255): 吸収なし %.2f / 吸収あり %.2f / MOG2 %.2f"
              % (bg_err[seq]["plain"], bg_err[seq]["fullseye"], bg_err[seq]["mog2"]))
    for seq in HELD_OUT:
        f = f_scores[seq]
        g.check("%s: Fullseye(吸収あり)の F ≥ 0.85" % seq, f["absorb"]["F"] >= 0.85, "%.3f" % f["absorb"]["F"])
        g.check("%s: 切り出しが空でも全部でもない(全コマの前景の割合)" % seq,
                0.0 < mask_store[seq]["fullseye"].mean() < 0.2, "%.4f" % mask_store[seq]["fullseye"].mean())
    f1, f2 = f_scores["I_OC_01"], f_scores["I_OC_02"]
    # 所見(変わったら書き換える)。吸収は I_OC_01 の幽霊(床の反射で一度前景になり戻らない塊)を消すが、
    # I_OC_02 では差が出ない。灰色 1 枚の Fullseye は、色と影の判定を持つ MOG2 にどちらの列でも届かない。
    g.check("所見: I_OC_01 は吸収で F が 0.05 以上上がる(適合率が上がる)",
            f1["absorb"]["F"] - f1["plain"]["F"] > 0.05 and f1["absorb"]["precision"] > f1["plain"]["precision"],
            "%.3f → %.3f(適合率 %.3f → %.3f)" % (f1["plain"]["F"], f1["absorb"]["F"], f1["plain"]["precision"],
                                              f1["absorb"]["precision"]))
    g.check("所見: I_OC_02 は吸収の有無で F が ±0.01 以内", abs(f2["absorb"]["F"] - f2["plain"]["F"]) < 0.01,
            "%.3f → %.3f" % (f2["plain"]["F"], f2["absorb"]["F"]))
    g.check("所見: I_OC_01 は MOG2 が 0.05 以上上", f1["mog2"]["F"] - f1["absorb"]["F"] > 0.05,
            "%.3f 対 %.3f" % (f1["mog2"]["F"], f1["absorb"]["F"]))
    g.check("所見: I_OC_02 は MOG2 との差が 0.02 以内", abs(f2["mog2"]["F"] - f2["absorb"]["F"]) < 0.02,
            "%.3f 対 %.3f" % (f2["mog2"]["F"], f2["absorb"]["F"]))
    g.check("所見: 推定した背景は MOG2 の方が真値の背景に近い(3 本とも)",
            all(bg_err[s]["mog2"] < bg_err[s]["fullseye"] for s in data),
            " / ".join("%s %.2f 対 %.2f" % (s, bg_err[s]["mog2"], bg_err[s]["fullseye"]) for s in data))

    # 3. 追跡
    print("\n-- 3. 追跡: 過程の雑音 q を %s だけで選ぶ" % TRAIN)
    truths = {seq: truth_track(d) for seq, d in data.items()}
    q_rows = []
    for q in Q_CANDIDATES:
        sc = score_track(track(mask_store[TRAIN]["fullseye"], q), truths[TRAIN])
        q_rows.append((sc["median_err"] + 50.0 * abs(sc["n_tracks"] - 3), q, sc))
        print("   q %.2f: 誤差の中央値 %.1f 画素、番号 %d(人は 3 人)" % (q, sc["median_err"], sc["n_tracks"]))
    q_best = min(q_rows)[1]
    print("   選んだ q = %.2f" % q_best)
    tracks, scores, crossings = {}, {}, {}
    for seq in (TRAIN,) + HELD_OUT:
        kal = track(mask_store[seq]["fullseye"], q_best, predictive=True)
        nn = track(mask_store[seq]["fullseye"], q_best, predictive=False)
        tracks[seq] = {"kalman": kal, "nn": nn}
        scores[seq] = {"kalman": score_track(kal, truths[seq]), "nn": score_track(nn, truths[seq])}
        s = scores[seq]
        print("   %s: カルマン 番号 %d・誤差の中央値 %.1f・90 %% 点 %.1f / 最近傍 番号 %d・%.1f・%.1f"
              % (seq, s["kalman"]["n_tracks"], s["kalman"]["median_err"], s["kalman"]["p90_err"],
                 s["nn"]["n_tracks"], s["nn"]["median_err"], s["nn"]["p90_err"]))
        if seq in HELD_OUT:
            gaps = occlusion_gaps(truths[seq]["visible"])
            if len(gaps) != 1:
                raise TrackGateError("%s: 遮蔽の区間が 1 つでない: %s" % (seq, gaps))
            a, b = gaps[0]
            cent = truths[seq]["centroid"]
            h_before = heading_deg(cent, a - HEADING_SPAN, a)
            h_after = heading_deg(cent, b + HEADING_SKIP, b + HEADING_SKIP + HEADING_SPAN)
            turn = abs((h_after - h_before + 180.0) % 360.0 - 180.0)
            crossings[seq] = {"kalman": crossing(kal, truths[seq], gaps[0]), "nn": crossing(nn, truths[seq], gaps[0]),
                              "heading_before_deg": h_before, "heading_after_deg": h_after, "turn_deg": turn}
            c = crossings[seq]
            print("      隠れたコマ %d(第 %d〜%d)、向き 前 %.0f° 後 %.0f°(変化 %.0f°)" %
                  (c["kalman"]["hidden_frames"], a + 2, b, h_before, h_after, turn))
            for name in ("kalman", "nn"):
                x = c[name]
                print("      %s: 同じ番号 %s、拾い直し 第 %s コマ、その時の誤差 %.1f 画素、出てきたコマでの予測の誤差 %.1f 画素"
                      % (name, x["same_id"], None if x["reacquired_frame"] is None else x["reacquired_frame"] + 1,
                         x["err_at_reacquire"], x["prediction_err_at_reappear"]))
    c1, c2 = crossings["I_OC_01"], crossings["I_OC_02"]
    g.check("I_OC_01: 向きはほぼ変わらない(< 30°)", c1["turn_deg"] < 30.0, "%.0f°" % c1["turn_deg"])
    g.check("I_OC_01: カルマンは柱の裏を同じ番号で通り抜ける", c1["kalman"]["same_id"]
            and scores["I_OC_01"]["kalman"]["n_tracks"] == 1, "番号 %s" % scores["I_OC_01"]["kalman"]["ids"])
    g.check("I_OC_01: 拾い直した時の誤差 < 20 画素", c1["kalman"]["err_at_reacquire"] < 20.0,
            "%.1f" % c1["kalman"]["err_at_reacquire"])
    g.check("I_OC_01: 予測しない最近傍は柱で見失う", not c1["nn"]["same_id"],
            "番号 %s" % scores["I_OC_01"]["nn"]["ids"])
    g.check("I_OC_01: 見えているコマの誤差の中央値 < 10 画素(カルマン)", scores["I_OC_01"]["kalman"]["median_err"] < 10.0,
            "%.1f" % scores["I_OC_01"]["kalman"]["median_err"])
    # 限界(変わったら書き換える): 隠れている間に折り返すと、等速の予測は画面の外へ出ていく。
    g.check("限界: I_OC_02 は隠れている間に折り返す(向きの変化 > 120°)", c2["turn_deg"] > 120.0, "%.0f°" % c2["turn_deg"])
    g.check("限界: I_OC_02 でカルマンは番号を継げない", not c2["kalman"]["same_id"], "番号 %s" % scores["I_OC_02"]["kalman"]["ids"])
    finite = [v for s in scores.values() for t in s.values() for v in (t["median_err"], t["p90_err"])]
    g.check("追跡の数値が全部有限", all(math.isfinite(v) for v in finite))
    return {"data": data, "selected": sel, "f": f_scores, "masks": mask_store, "plates": plates, "bg_images": bg_images,
            "bg_err": bg_err, "q": q_best, "tracks": tracks, "scores": scores, "crossing": crossings, "truth": truths}


def _record(res: dict, contract: dict) -> dict:
    return {
        "date": "2026-11-08",
        "digests": {seq: d["digest"] for seq, d in res["data"].items()},
        "selected": res["selected"], "q": res["q"],
        "f": {seq: {k: (round(v["F"], 4), round(v["precision"], 4), round(v["recall"], 4)) for k, v in f.items()
                    if isinstance(v, dict)} for seq, f in res["f"].items()},
        "absorbed_frames": {seq: f["absorbed_frames"] for seq, f in res["f"].items()},
        "bg_rms_255": {seq: {k: round(v, 3) for k, v in e.items()} for seq, e in res["bg_err"].items()},
        "tracks": {seq: {k: {"n_tracks": v["n_tracks"], "median_err": round(v["median_err"], 2),
                             "p90_err": round(v["p90_err"], 2)} for k, v in s.items()} for seq, s in res["scores"].items()},
        "crossing": {seq: {"turn_deg": round(c["turn_deg"], 1), "hidden_frames": c["kalman"]["hidden_frames"],
                           "kalman_same_id": c["kalman"]["same_id"], "nn_same_id": c["nn"]["same_id"],
                           "kalman_err_at_reacquire": (round(c["kalman"]["err_at_reacquire"], 2)
                                                       if math.isfinite(c["kalman"]["err_at_reacquire"]) else None)}
                     for seq, c in res["crossing"].items()},
        "contract": {k: float("%.6g" % v) for k, v in contract.items()},
    }


def main() -> None:
    t0 = time.perf_counter()
    g = Gates()
    contract = contract_gates(g)
    root = lasiesta_cache()
    have = all((root / seq / seq).is_dir() for seq in (TRAIN,) + HELD_OUT)
    if (os.environ.get("CI") and not os.environ.get("FULLSEYE_LASIESTA_DATA")) or not have:
        print("\n実データ(LASIESTA)が無いので実データの章を飛ばす。取得は py -3.11 tools/fetch_lasiesta.py")
        print("記録値(RECORDED): " + json.dumps(RECORDED, ensure_ascii=False, sort_keys=True))
        g.check("記録値が空でない", bool(RECORDED) and RECORDED.get("crossing", {}).get("I_OC_01", {}).get("kalman_same_id"))
    else:
        res = real_chapter(g, root)
        print("\nRECORDED_JSON=" + json.dumps(_record(res, contract), ensure_ascii=False, sort_keys=True))
        write_figures(res)
    errors = figs.errors()
    if errors:
        raise SystemExit("図の書き出しで失敗: " + "; ".join(errors))
    bad = g.failed()
    if bad:
        raise TrackGateError("門が %d 本外れた: %s" % (len(bad), "; ".join(r[0] for r in bad)))
    print("門 %d 本すべて通過(%.1f s)\nPASS" % (len(g.rows), time.perf_counter() - t0))


if __name__ == "__main__":
    main()
