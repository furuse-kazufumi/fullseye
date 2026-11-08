# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""実測のコーンビーム CT(クルミ 1 個)を Fullseye の撮影モードの op で再構成し、配布元の参照と照合する。

Reconstruct a measured cone-beam CT scan of a walnut with Fullseye's scan-mode operators and
score it against the reconstructions the data providers published.

データ / data: Der Sarkissian, Lucka, van Eijnatten, Colacicco, Coban & Batenburg, "A cone-beam
X-ray CT data collection designed for machine learning", Sci. Data 6, 215 (2019),
doi:10.1038/s41597-019-0235-y; Zenodo doi:10.5281/zenodo.2686726, CC BY 4.0。
原本(1 標本 6 GB)は repo に入れず、``tools/fetch_walnut_cbct.py`` が一部だけを取得する
(標本 1・中段の軌道 tubeV2・1200 枚から 4 枚に 1 枚の 300 枚・暗電流と白・幾何・参照再構成 2 種)。

間引きと縮小(どう減らしたか / how the data were reduced):

* 投影は 1200 枚 → 300 枚(4 枚に 1 枚、1.2° 刻み)。3-D の章はさらに 2 枚に 1 枚の 150 枚。
* 検出器 972 × 768 画素(0.1496 mm)を、中央面の章は 6 × 6、3-D の章は 8 × 8 に束ねる
  (透過率で平均してから −log)。回転中心で 0.30 mm / 0.40 mm。
* 中央面の章は、線源の高さの検出器 1 行ぶん(6 画素の帯)だけを fan として使う。
* 参照は配布元の 0.1 mm 格子(501³)を、こちらの格子へ箱で平均して比べる。

照合の相手(真値は外から / truth from outside):

1. ``full_AGD_50``: 配布元が **3 つの軌道すべて**(1200 × 3 枚、全解像度)から非負最小二乗で作った
   再構成。コーン角の影響が無い「正解に最も近い物」。
2. ``fdk_pos2``: 配布元が**同じ軌道 2** の全 1200 枚から ASTRA の FDK で作った再構成。
   Fullseye の FDK と同じ式の**別実装**。
3. 撮影装置の設定ファイル(SOD・SDD・画素)と、配布元の幾何ファイル(1201 行のベクトル)。

章:

* 幾何: 配布元のベクトルを ``ct_scan_geometry`` の円軌道に読み替え、表せない 2 つ
  (検出器の 0.5° の面内回転と 7.2 画素の縦のずれ)は投影を ``warp_parametric`` で引き直す。
* 中央面(fan): FDK・SIRT・OS-SART・TV を、全 300 枚 / 間引き(100・50・25 枚)/
  限られた角度(240°・150°・90°)で比べる。TV の重みは参照を見ずに、使わなかった投影への
  再投影誤差で選ぶ。
* 3-D(cone): FDK を ASTRA の FDK と比べ、高さごとの誤差が 3 軌道の参照に対して
  中央面から離れるほど増えること(Tuy の条件)を、Fullseye と ASTRA の両方で測る。
* 幾何の取り違え: 隣接の恒等式 <Ax,y> = <x,Aᵀy> は射影の対が整合しているかを測るだけで、
  データと幾何の食い違いは見えない。取り違え(面内回転・縦ずれ・回転の向き・横ずれ)は
  参照との一致と再投影の残差で見つける。
* 二重エネルギー: このデータは 40 kV の 1 エネルギーだけ。**第 2 エネルギーは合成**
  (実データの 1 エネルギーと、仮定した 2 物質の減弱係数の閉形式)で、実データではない。

実行例::

    py -3.11 tools/fetch_walnut_cbct.py
    FULLSEYE_FIGURE_DIR=out/walnut py -3.11 examples/poc_real_walnut_cbct.py

データが無い環境(CI)では取得せず、下の ``RECORDED`` を印字して、合成の幾何ベクトルで
幾何の読み替え(``fit_geometry`` / ``ideal_warp``)と隣接の恒等式の門だけを回す。
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import ctscan  # noqa: E402
import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402
import realdata  # noqa: E402

SOURCE = realdata.walnut_cbct_credit()

#: 配布元の検出器: 972 行 × 768 列、束ね 2 の後の画素 0.1496 mm(``scan settings.txt``)。
DET_ROWS, DET_COLS, DET_PIXEL_MM = 972, 768, 0.1496
#: 参照再構成の格子: 501³、0.1 mm、原点が中心(配布元の ``GroundTruthReconstruction.py``)。
REF_N, REF_VOXEL_MM = 501, 0.1
#: 中央面の章: 検出器を 6 × 6 に束ね、0.30 mm の 127 × 127 で再構成する(視野 38 mm を覆う)。
FAN_BIN, FAN_N, FAN_VOXEL = 6, 127, 0.3
#: 3-D の章: 8 × 8 に束ね、0.40 mm の 97³ で、投影は 150 枚。
CONE_BIN, CONE_N, CONE_VOXEL, CONE_VIEW_STEP = 8, 97, 0.4, 2
#: 内訳の切り分け: 中央面だけを 2 × 2(0.10 mm)で再構成し、0.30 mm へ箱で平均する。線源の高さの行を
#: 含む元の画素の帯(460〜499 行)だけを持つ。
FINE_BIN, FINE_N, FINE_VOXEL, FINE_ROW0, FINE_ROWS = 2, 381, 0.1, 460, 40
#: 評価する円の半径 [mm](検出器の視野の半径 19.05 mm の内側)。
EVAL_RADIUS_MM = 17.5
#: 間引き(全 300 枚から何枚に 1 枚)と、限られた角度(先頭から何度ぶん、その中は 2 枚に 1 枚 = 2.4° 刻み)。
#: 全 300 枚は FDK だけで回す(反復法の時間は投影の枚数に比例し、CPU で 1 本 1〜2 分かかる)。
SPARSE_STEPS = (2, 6, 12)
LIMITED_ARCS = (240.0, 150.0, 90.0)
LIMITED_STEP = 2
#: 反復の回数(全条件で共通。条件ごとに選び直さない)。
SIRT_ITERS, OSSART_ITERS, TV_ITERS = 60, 10, 100
#: TV の重みの候補。50 枚の条件で、使わなかった 250 枚への再投影誤差が最小のものを使う。
TV_WEIGHTS = (3e-6, 1e-5, 3e-5, 1e-4)
#: 二重エネルギーの仮定(合成の第 2 エネルギー用、物理の値ではない): 殻と、それ以外。
DE_MU_LOW, DE_MU_HIGH = (1.0, 0.6), (0.55, 0.45)

# 実データを走らせた後、stdout の ``RECORDED_JSON`` と同じ値へ固定する。
RECORDED = {'adjoint': {'cone': 5.960611570152381e-16, 'fan': 1.0751682582755414e-15, 'mismatch': 1.139560034095261},
 'cone': {'astra_vs_ref': 0.0023291119050506356,
          'corr': 0.9945788352596482,
          'diff_peak': 1.1253469459078713,
          'near_far': [0.002585838339649534,
                       0.010122513401233822,
                       0.0007789778301918565,
                       0.009900971877370794],
          'seconds': 6.088041600014549,
          'upper': [0.0025491359885181693, 0.0019380139043844074],
          'vs_astra': 0.002074113555348673},
 'dataset_manifest_sha256': 'af0d0d5cda5d55eb8e602c572bf1dd610eabeca9d892009e98975e0c3163c24d',
 'date': '2026-11-08',
 'dual': {'condition': 15.477054890909018,
          'flat_quieter': 3.51316838483778,
          'gain_flat': 0.47276399172188693,
          'gain_projection': 1.660899509207043,
          'noise_b0': 0.0018202665472629288,
          'noise_pred': 5.0,
          'noise_ratio': 5.05766592559637,
          'noise_single': 0.00035990248744005246,
          'repeat_noise_measured': 0.003215123359064165,
          'repeat_noise_model': 0.002574403009598878,
          'repeat_pixels': [4740, 12418],
          'threshold': 0.046058019094770246},
 'failed': 0,
 'fan': [{'cond': '300 枚',
          'method': 'FDK',
          'rmse': 0.002282681988180712,
          'scale': 1.0151853778714464,
          'seconds': 0.5653601000085473,
          'ssim': 0.9395462959780277},
         {'cond': '150 枚',
          'method': 'FDK',
          'rmse': 0.0027576647119979107,
          'scale': 1.0153486073815863,
          'seconds': 0.38711259997216985,
          'ssim': 0.8860217499162143},
         {'cond': '150 枚',
          'method': 'SIRT',
          'rmse': 0.004669765422011968,
          'scale': 1.0066766039846435,
          'seconds': 18.32520399999339,
          'ssim': 0.9037942134969006},
         {'cond': '150 枚',
          'method': 'OS-SART',
          'rmse': 0.0038112021364527693,
          'scale': 1.0069302868814474,
          'seconds': 4.38619099999778,
          'ssim': 0.9314253304218726},
         {'cond': '150 枚',
          'method': 'TV',
          'rmse': 0.0026436423061859454,
          'scale': 1.0079811078211414,
          'seconds': 32.13941339997109,
          'ssim': 0.9644506625782745},
         {'cond': '50 枚',
          'method': 'FDK',
          'rmse': 0.006867054174062506,
          'scale': 1.0146835211625622,
          'seconds': 0.09786549996351823,
          'ssim': 0.6610244365095885},
         {'cond': '50 枚',
          'method': 'SIRT',
          'rmse': 0.005514479014413534,
          'scale': 1.002659812555097,
          'seconds': 6.398228999983985,
          'ssim': 0.8423072501928909},
         {'cond': '50 枚',
          'method': 'OS-SART',
          'rmse': 0.004766115795551143,
          'scale': 1.0031662272463693,
          'seconds': 1.305520499998238,
          'ssim': 0.8701729859566275},
         {'cond': '50 枚',
          'method': 'TV',
          'rmse': 0.003060609470512624,
          'scale': 1.006964179134826,
          'seconds': 11.353741900005843,
          'ssim': 0.9484285288851169},
         {'cond': '25 枚',
          'method': 'FDK',
          'rmse': 0.012635505794267305,
          'scale': 1.0151988851915155,
          'seconds': 0.04711799998767674,
          'ssim': 0.49789358001584044},
         {'cond': '25 枚',
          'method': 'SIRT',
          'rmse': 0.007447085177753234,
          'scale': 0.9977669694951548,
          'seconds': 3.3982744999811985,
          'ssim': 0.7413055296143521},
         {'cond': '25 枚',
          'method': 'OS-SART',
          'rmse': 0.006743352792062496,
          'scale': 0.9986949924528424,
          'seconds': 0.6723294000257738,
          'ssim': 0.776857526677192},
         {'cond': '25 枚',
          'method': 'TV',
          'rmse': 0.004646030776906719,
          'scale': 1.0060782616527586,
          'seconds': 6.073194199998397,
          'ssim': 0.8825889508673398},
         {'cond': '240°',
          'method': 'FDK',
          'rmse': 0.0033966295114732418,
          'scale': 1.014914393219449,
          'seconds': 0.21475320000899956,
          'ssim': 0.8521209082527161},
         {'cond': '240°',
          'method': 'SIRT',
          'rmse': 0.005104695926825912,
          'scale': 1.005701518251249,
          'seconds': 12.11423599999398,
          'ssim': 0.8816124446061328},
         {'cond': '240°',
          'method': 'OS-SART',
          'rmse': 0.004195373513901503,
          'scale': 1.0065511955188922,
          'seconds': 2.7238622000440955,
          'ssim': 0.9144810254309488},
         {'cond': '240°',
          'method': 'TV',
          'rmse': 0.0027901983037930344,
          'scale': 1.0072457430011754,
          'seconds': 22.765794200007804,
          'ssim': 0.9579317570805356},
         {'cond': '150°',
          'method': 'FDK',
          'rmse': 0.009109808652350936,
          'scale': 0.849513626916559,
          'seconds': 0.12234040000475943,
          'ssim': 0.5950373077794755},
         {'cond': '150°',
          'method': 'SIRT',
          'rmse': 0.007552494858228185,
          'scale': 1.0001594529478348,
          'seconds': 8.394766100042034,
          'ssim': 0.7890833619362471},
         {'cond': '150°',
          'method': 'OS-SART',
          'rmse': 0.006991063390331167,
          'scale': 1.0030952532362274,
          'seconds': 1.8353970000171103,
          'ssim': 0.8127374790053695},
         {'cond': '150°',
          'method': 'TV',
          'rmse': 0.004297202751262529,
          'scale': 1.0097717842166725,
          'seconds': 14.523066299967468,
          'ssim': 0.9228532154131622},
         {'cond': '90°',
          'method': 'FDK',
          'rmse': 0.016647603172916647,
          'scale': 0.5128143109240855,
          'seconds': 0.06988550000824034,
          'ssim': 0.35521769536261},
         {'cond': '90°',
          'method': 'SIRT',
          'rmse': 0.012814213953581071,
          'scale': 0.9661589572946788,
          'seconds': 5.035178100049961,
          'ssim': 0.5880872582061885},
         {'cond': '90°',
          'method': 'OS-SART',
          'rmse': 0.012636026463707864,
          'scale': 0.9719577857762801,
          'seconds': 1.0047617999953218,
          'ssim': 0.6023735630473384},
         {'cond': '90°',
          'method': 'TV',
          'rmse': 0.011009455759068074,
          'scale': 0.9919567449073664,
          'seconds': 8.889871299965307,
          'ssim': 0.6803346816446988}],
 'fan_baseline_astra_vs_ref': {'rmse': 0.0009328917286845592,
                               'scale': 1.016422139863835,
                               'ssim': 0.9720249575050047},
 'fan_fine_0p1mm_boxed': {'rmse': 0.0012778285235524728,
                          'scale': 1.0162268238619891,
                          'ssim': 0.951449325592724},
 'fan_fullseye_vs_astra': {'rmse': 0.0020562849537197813,
                           'scale': 0.9987832201367101,
                           'ssim': 0.9615594857091206},
 'gates': 52,
 'geometry': {'da_mm': -0.0015075906119849016,
              'dh_mm': 1.0799000000000092,
              'dsd': 199.00618806264296,
              'dso': 66.00140202456363,
              'du': 0.14959999999999998,
              'src_z': 0.317124735999994,
              'step_deg': 1.2000000013349768,
              'theta_deg': 0.5000000000139884},
 'measured_angles_rule': 'full',
 'mistakes': [{'name': '正しい',
               'resid': 0.08701961268602337,
               'rmse': 0.002282681988180712,
               'ssim': 0.9395462959780277},
              {'name': '面内回転 0.5° を無視',
               'resid': 0.08722731680925885,
               'rmse': 0.0023110795005900605,
               'ssim': 0.9399717635835426},
              {'name': '縦ずれ 7.2 画素を無視',
               'resid': 0.08500475057504418,
               'rmse': 0.006031662808776003,
               'ssim': 0.8543956992701044},
              {'name': '横に 1 画素(0.3 mm)ずらす',
               'resid': 0.13987045245519808,
               'rmse': 0.00958536676463501,
               'ssim': 0.7027594532659002},
              {'name': '回転の向きを逆に',
               'resid': 0.1740126970808635,
               'rmse': 0.02089230422045125,
               'ssim': 0.26005924283023685}],
 'tv_holdout_rmse': {'0.0001': 0.016956553353902105,
                     '1e-05': 0.013912178598453695,
                     '3e-05': 0.014409524800484817,
                     '3e-06': 0.014561771379847316},
 'tv_weight': 1e-05}


class Gates:
    """門を 1 つずつ記録し、最後にまとめて判定する(どれが外れたかを全部出す)。"""

    def __init__(self) -> None:
        self.rows: list[tuple[str, str, bool, str]] = []

    def check(self, part: str, name: str, ok, detail: str = "") -> bool:
        ok = bool(ok)
        self.rows.append((part, name, ok, detail))
        print("  [%s] %s %s%s" % ("OK" if ok else "NG", part, name, (" — " + detail) if detail else ""))
        return ok

    def failed(self):
        return [r for r in self.rows if not r[2]]


# --------------------------------------------------------------------------- #
# 読み込みと幾何
# --------------------------------------------------------------------------- #
def _tif(path: Path) -> np.ndarray:
    with Image.open(path) as im:
        return np.asarray(im)


def _trafo(image: np.ndarray) -> np.ndarray:
    """装置の読み出し → 配布元の幾何の向き(``np.transpose(np.flipud(image))``、配布元のスクリプトと同じ)。"""
    return np.ascontiguousarray(np.transpose(np.flipud(image)))


def read_settings(root: Path) -> dict:
    """``scan settings.txt`` の SOD・SDD・画素(装置が書いた値、幾何ファイルとは独立)。"""
    text = (root / "scan settings.txt").read_text(encoding="latin-1")
    out = {}
    for key in ("SOD", "SDD", "Binned pixel size"):
        for line in text.splitlines():
            if line.split(":")[0].strip() == key:
                out[key] = float(line.split(":")[1].strip())
    if len(out) != 3:
        raise realdata.RealDataError("scan settings.txt に SOD / SDD / 画素が無い")
    return out


def fit_geometry(vecs: np.ndarray) -> dict:
    """ASTRA の ``cone_vec``(1 行 12 数)を、円軌道の数と、円軌道で表せない残りに分ける。

    円軌道(``ct_scan_geometry`` の ``"cone"``)は、線源が z 軸の周りを回り、検出器の u が水平、
    v が z 軸に平行で、主点(線源から検出器へ下ろした垂線の足)が検出器の中心に来る形。
    残りは、検出器の面内回転 ``theta``、主点からの検出器中心のずれ ``(da, dh)``、線源の高さ。
    """
    s, d, u, v = vecs[:, 0:3], vecs[:, 3:6], vecs[:, 6:9], vecs[:, 9:12]
    beta = np.unwrap(np.arctan2(s[:, 0], -s[:, 1]))
    uh = np.stack([np.cos(beta), np.sin(beta), 0.0 * beta], 1)          # 円軌道の u
    n = np.stack([-np.sin(beta), np.cos(beta), 0.0 * beta], 1)          # 線源 → 検出器
    du, dv = np.linalg.norm(u, axis=1), np.linalg.norm(v, axis=1)
    dso = np.hypot(s[:, 0], s[:, 1])
    dsd = ((d - s) * n).sum(1)
    p = s + dsd[:, None] * n                                            # 主点
    da = ((d - p) * uh).sum(1)
    dh = d[:, 2] - p[:, 2]
    theta = np.arctan2(-u[:, 2] / du, (u * uh).sum(1) / du)
    step = np.diff(np.rad2deg(beta))
    return {
        "beta_deg": np.rad2deg(beta), "step_deg": float(step.mean()), "step_sd_deg": float(step.std()),
        "dso": float(dso.mean()), "dsd": float(dsd.mean()), "du": float(du.mean()), "dv": float(dv.mean()),
        "da_mm": float(da.mean()), "dh_mm": float(dh.mean()), "theta_deg": float(np.rad2deg(theta).mean()),
        "src_z": float(s[:, 2].mean()),
        "spread": {"dso": float(np.ptp(dso)), "dsd": float(np.ptp(dsd)), "theta_deg": float(np.ptp(np.rad2deg(theta))),
                   "da_mm": float(np.ptp(da)), "dh_mm": float(np.ptp(dh)), "src_z": float(np.ptp(s[:, 2]))},
    }


def ideal_warp(fit: dict, b: int, n_rows: int, r0: int, nu: int, nv: int, *, roll: bool = True,
               voff: bool = True) -> np.ndarray:
    """束ねた実検出器の画素 (x, y) → 円軌道の理想検出器の画素 (x', y') の 3×3(``warp_parametric`` 用)。

    束ねた画素 (x, y) の中心は元の画素で ``(x b + (b−1)/2, r0 + y b + (b−1)/2)``。
    ``roll=False`` / ``voff=False`` は、取り違えの章で「面内回転を無視」「縦ずれを無視」を作る。
    """
    th = math.radians(fit["theta_deg"]) if roll else 0.0
    c, s = math.cos(th), math.sin(th)
    pix = fit["du"]
    big = b * pix
    # 束ねた実画素 → 元の画素の中心 → 検出器の中心からの距離 [mm](u_real, v_real の向き)
    to_raw = np.array([[b, 0.0, (b - 1) / 2.0], [0.0, b, r0 + (b - 1) / 2.0], [0, 0, 1.0]])
    centre = np.array([[pix, 0.0, -(DET_COLS - 1) / 2.0 * pix], [0.0, pix, -(DET_ROWS - 1) / 2.0 * pix], [0, 0, 1.0]])
    # 実検出器の軸 → 理想の軸(u_real = cos û − sin ẑ, v_real = sin û + cos ẑ)と、主点からのずれ
    rot = np.array([[c, s, fit["da_mm"]], [-s, c, fit["dh_mm"] if voff else 0.0], [0, 0, 1.0]])
    to_ideal = np.array([[1.0 / big, 0.0, (nu - 1) / 2.0], [0.0, 1.0 / big, (nv - 1) / 2.0], [0, 0, 1.0]])
    return to_ideal @ rot @ centre @ to_raw


def _bin(t: np.ndarray, b: int, r0: int, rows: int) -> np.ndarray:
    a = t[r0:r0 + rows]
    return a.reshape(rows // b, b, a.shape[1] // b, b).mean(axis=(1, 3))


def load_projections(root: Path, g: Gates) -> dict:
    """投影 300 枚を読み、透過率で束ねてから −log。束ね 6(全行)と 8(968 行)の 2 通りを返す。"""
    proj_dir = root / "Walnut1" / "Projections" / ("tubeV%d" % realdata.WALNUT_CBCT_ORBIT)
    dark = _trafo(_tif(proj_dir / "di000000.tif")).astype(np.float64)
    flat = 0.5 * (_trafo(_tif(proj_dir / "io000000.tif")).astype(np.float64)
                  + _trafo(_tif(proj_dir / "io000001.tif")).astype(np.float64))
    gain = flat - dark
    g.check("読込", "白 − 暗電流が全画素で正", float(gain.min()) > 0, "最小 %.0f カウント" % gain.min())
    idx = realdata.walnut_cbct_projection_indices()
    fan, cone, fine = [], [], []
    t_min, t_max = 1.0, 0.0
    for i in idx:
        t = (_trafo(_tif(proj_dir / ("scan_%06d.tif" % i))).astype(np.float64) - dark) / gain
        t_min, t_max = min(t_min, float(t.min())), max(t_max, float(t.max()))
        t = np.clip(t, 1e-4, None)
        fan.append(-np.log(_bin(t, FAN_BIN, 0, DET_ROWS)))
        cone.append(-np.log(_bin(t, CONE_BIN, 2, DET_ROWS - 4)))
        fine.append(-np.log(_bin(t, FINE_BIN, FINE_ROW0, FINE_ROWS)))
    g.check("読込", "投影 300 枚の透過率が (0, 1.3) の範囲", 0.0 < t_min and t_max < 1.3,
            "%.3f〜%.3f" % (t_min, t_max))

    # 同じ角度の 2 枚(0 番と 1200 番、約 5 分の間)。差は雑音と、線源の明るさの揺れだけ。
    def binned(i):
        t = (_trafo(_tif(proj_dir / ("scan_%06d.tif" % i))).astype(np.float64) - dark) / gain
        return _bin(np.clip(t, 1e-4, None), FAN_BIN, 0, DET_ROWS)

    t_a, t_b = binned(realdata.WALNUT_CBCT_REPEAT_INDEX), binned(idx[0])
    repeat = {"t": 0.5 * (t_a + t_b), "d": -np.log(t_a) + np.log(t_b), "gain_b": _bin(gain, FAN_BIN, 0, DET_ROWS)}
    realdata.mark_read("walnut-cbct:Walnut1/tubeV2")
    return {"fan": np.asarray(fan), "cone": np.asarray(cone), "fine": np.asarray(fine), "repeat": repeat,
            "dark_mean": float(dark.mean()),
            "flat_mean": float(flat.mean()), "t_min": t_min, "t_max": t_max}


def to_ideal(binned: np.ndarray, W: np.ndarray, nv: int, nu: int) -> np.ndarray:
    """束ねた投影の束 ``(view, rows, cols)`` を、理想検出器 ``(view, nv, nu)`` へ引き直す。"""
    return np.stack([fs.warp_parametric(p, W, out_shape=(nv, nu)) for p in binned])


# --------------------------------------------------------------------------- #
# 参照(配布元の 0.1 mm 格子)をこちらの格子へ
# --------------------------------------------------------------------------- #
def _box_weights(ratio: int) -> tuple[np.ndarray, np.ndarray]:
    """0.1 mm の格子で、幅 ``ratio`` × 0.1 mm の箱の重み(偶数は両端を半分)。"""
    if ratio % 2:
        off = np.arange(-(ratio // 2), ratio // 2 + 1)
        w = np.ones(ratio)
    else:
        off = np.arange(-(ratio // 2), ratio // 2 + 1)
        w = np.ones(ratio + 1)
        w[0] = w[-1] = 0.5
    return off, w / w.sum()


def _plane_down(slice2d: np.ndarray, n: int, ratio: int) -> np.ndarray:
    """1 枚の 501² を、中心を合わせた ``n``² の箱平均へ(中心の画素 250 がこちらの中心)。"""
    off, w = _box_weights(ratio)
    centres = 250 + ratio * (np.arange(n) - (n - 1) // 2)
    rows = sum(wk * slice2d[centres + ok, :] for ok, wk in zip(off, w))
    return sum(wk * rows[:, centres + ok] for ok, wk in zip(off, w))


def load_reference(root: Path, name: str, n: int, ratio: int, z_mm: np.ndarray) -> np.ndarray:
    """参照再構成 ``name`` を、面内は箱平均、z は線形補間 + 箱平均でこちらの格子へ。

    ``z_mm`` は**参照の座標系**での各スライスの中心の高さ(線源の高さを足した値)。
    """
    rec = root / "Walnut1" / "Reconstructions"
    off, w = _box_weights(ratio)
    need = set()
    for z in z_mm:
        for o in off:
            f = 250 + (z / REF_VOXEL_MM) + o
            need.update((int(math.floor(f)), int(math.floor(f)) + 1))
    need = sorted(k for k in need if 0 <= k < REF_N)
    planes = {}
    for k in need:
        a = _tif(rec / ("%s_%06d.tiff" % (name, k))).astype(np.float64)
        if a.shape != (REF_N, REF_N):
            raise realdata.RealDataError("%s の %d 枚目が %r" % (name, k, a.shape))
        planes[k] = _plane_down(a, n, ratio)
    out = np.zeros((len(z_mm), n, n))
    for i, z in enumerate(z_mm):
        acc = np.zeros((n, n))
        for o, wk in zip(off, w):
            f = 250 + (z / REF_VOXEL_MM) + o
            k0 = int(math.floor(f))
            t = f - k0
            lo = planes.get(k0, np.zeros((n, n)))
            hi = planes.get(k0 + 1, np.zeros((n, n)))
            acc += wk * ((1 - t) * lo + t * hi)
        out[i] = acc
    realdata.mark_read("walnut-cbct:Walnut1/%s" % name)
    return out


# --------------------------------------------------------------------------- #
# 採点
# --------------------------------------------------------------------------- #
def disk(n: int, voxel: float) -> np.ndarray:
    r = (np.arange(n) - (n - 1) / 2.0) * voxel
    return (r[None, :] ** 2 + r[:, None] ** 2) <= EVAL_RADIUS_MM ** 2


def score(img: np.ndarray, ref: np.ndarray, mask: np.ndarray) -> dict:
    """円の中の RMSE [1/mm]、円の外を 0 にした SSIM、参照の平均との比(絶対尺度)。"""
    a = np.where(mask, img, 0.0)
    b = np.where(mask, ref, 0.0)
    rng = float(np.percentile(b[mask], 99.9) - min(0.0, float(b[mask].min())))
    return {"rmse": float(fs.rmse(a[mask], b[mask])),
            "ssim": float(fs.ssim(a, b, data_range=rng)),
            "scale": float(a[mask].mean() / b[mask].mean())}


# --------------------------------------------------------------------------- #
# 章: 幾何
# --------------------------------------------------------------------------- #
def chapter_geometry(root: Path, g: Gates) -> dict:
    print("\n== 幾何: 配布元のベクトル → 円軌道")
    proj_dir = root / "Walnut1" / "Projections" / ("tubeV%d" % realdata.WALNUT_CBCT_ORBIT)
    allv = np.loadtxt(proj_dir / "scan_geom_corrected.geom")
    g.check("幾何", "幾何ファイルは 1201 行 × 12 数", allv.shape == (1201, 12), "%s" % (allv.shape,))
    vecs = allv[0:1200:realdata.WALNUT_CBCT_ANGULAR_STEP]
    fit = fit_geometry(vecs)
    st = read_settings(proj_dir)
    print("  SOD %.4f / SDD %.4f mm、画素 %.4f mm、面内回転 %.3f°、主点からの中心のずれ u %.4f / v %.4f mm、"
          "線源の高さ %.3f mm" % (fit["dso"], fit["dsd"], fit["du"], fit["theta_deg"], fit["da_mm"],
                                  fit["dh_mm"], fit["src_z"]))
    g.check("幾何", "SOD = 装置の設定ファイル(差 < 0.01 mm)", abs(fit["dso"] - st["SOD"]) < 0.01,
            "%.4f / %.4f mm" % (fit["dso"], st["SOD"]))
    g.check("幾何", "SDD = 装置の設定ファイル(差 < 0.01 mm)", abs(fit["dsd"] - st["SDD"]) < 0.01,
            "%.4f / %.4f mm" % (fit["dsd"], st["SDD"]))
    g.check("幾何", "画素 = 装置の設定ファイル", abs(fit["du"] - st["Binned pixel size"]) < 1e-6
            and abs(fit["dv"] - fit["du"]) < 1e-9, "%.4f mm" % fit["du"])
    sp = fit["spread"]
    g.check("幾何", "SOD・SDD・面内回転・ずれ・線源の高さが全 300 枚で一定(円軌道)",
            max(sp["dso"], sp["dsd"], sp["da_mm"], sp["dh_mm"], sp["src_z"]) < 1e-3 and sp["theta_deg"] < 1e-3,
            "最大の幅 %.1e mm / %.1e°" % (max(sp["dso"], sp["dsd"], sp["da_mm"], sp["dh_mm"], sp["src_z"]),
                                          sp["theta_deg"]))
    g.check("幾何", "角度は 1.2° 刻みの一様(標準偏差 < 1e-4°)、増える向き",
            abs(fit["step_deg"] - 1.2) < 1e-6 and fit["step_sd_deg"] < 1e-4, "%.7f ± %.1e°"
            % (fit["step_deg"], fit["step_sd_deg"]))
    # 円軌道で表せない 2 つ(門で「在る」ことを確かめ、投影の引き直しで消す)
    g.check("幾何", "表せない 1: 検出器の面内回転が 0 でない(0.1° 超)", abs(fit["theta_deg"]) > 0.1,
            "%.3f°、検出器の端で %.2f 画素の縦ずれ" % (fit["theta_deg"],
                                                    math.tan(math.radians(abs(fit["theta_deg"]))) * DET_COLS / 2))
    g.check("幾何", "表せない 2: 検出器の中心が主点から縦にずれる(1 画素超)", abs(fit["dh_mm"]) > fit["dv"],
            "%.2f 画素 = %.3f mm" % (fit["dh_mm"] / fit["dv"], fit["dh_mm"]))
    # ct_scan_geometry の円軌道を作り、ベクトルを配布元と比べる(引き直しの後は円軌道そのもの)
    geom = ctscan.ct_scan_geometry("cone", n_views=300, n_u=DET_COLS, n_v=DET_ROWS, vol_shape=(8, 8, 8),
                                   voxel=1.0, du=fit["du"], dv=fit["dv"], dso=fit["dso"], dsd=fit["dsd"],
                                   start_deg=float(fit["beta_deg"][0]))
    s = vecs[:, 0:3] - np.array([0.0, 0.0, fit["src_z"]])
    err_src = float(np.abs(geom["source"] - s).max())
    err_ang = float(np.abs(np.rad2deg(geom["angles_rad"]) - fit["beta_deg"]).max())
    g.check("幾何", "ct_scan_geometry の線源位置 = 配布元(< 0.01 mm、高さを除く)", err_src < 0.01, "%.2e mm" % err_src)
    g.check("幾何", "ct_scan_geometry の角度 = 配布元(< 1e-3°)", err_ang < 1e-3, "%.1e°" % err_ang)
    # 測った角度を angles_deg でそのまま渡しても、弧は 360° と数えられ、全周の重み(1/2)になること
    # (浮動小数の弧が 360 − 1e-6 を割ると短いスキャンの Parker に落ちる。その手前にいることを確かめる)。
    g_meas = ctscan.ct_scan_geometry("fan", angles_deg=fit["beta_deg"], n_u=8, n_v=1, vol_shape=(1, 8, 8),
                                     voxel=1.0, dso=fit["dso"], dsd=fit["dsd"])
    _, rule = ctscan._redundancy(g_meas, False, "probe")
    g.check("幾何", "測った 300 角を angles_deg で渡しても全周(重み 1/2)と判定される",
            rule == "full", "弧 %.6f°、規則 %s" % (g_meas["arc_deg"], rule))
    return {"fit": fit, "settings": st, "err_src_mm": err_src, "err_angle_deg": err_ang,
            "measured_angles_arc_deg": float(g_meas["arc_deg"]), "measured_angles_rule": rule}


# --------------------------------------------------------------------------- #
# 章: 中央面(fan)
# --------------------------------------------------------------------------- #
def fan_geometry(fit: dict, views: np.ndarray | None = None, arc_views: np.ndarray | None = None,
                 offset_u: float = 0.0) -> dict:
    """中央面の fan の幾何。``views`` は 300 枚のうち使う番号(0 から等間隔で全周)、``arc_views`` は
    限られた角度で使う番号(先頭から等間隔、弧は全周より短い)。"""
    big = FAN_BIN * fit["du"]
    kw = dict(n_u=DET_COLS // FAN_BIN, n_v=1, vol_shape=(1, FAN_N, FAN_N), voxel=FAN_VOXEL, du=big, dv=big,
              dso=fit["dso"], dsd=fit["dsd"], offset_u=offset_u)
    beta0 = float(fit["beta_deg"][0])
    if arc_views is not None:
        return ctscan.ct_scan_geometry("fan", angles_deg=beta0 + fit["step_deg"] * np.asarray(arc_views), **kw)
    views = np.asarray(views)
    if views[0] != 0 or (len(views) > 1 and np.ptp(np.diff(views)) != 0) or 300 % len(views):
        raise ValueError("fan_geometry: views は 0 から等間隔で 300 を割り切る数(%r)" % (views[:4],))
    return ctscan.ct_scan_geometry("fan", n_views=len(views), arc_deg=360.0, start_deg=beta0, **kw)


def fan_data(proj: dict, fit: dict, *, roll=True, voff=True) -> np.ndarray:
    W = ideal_warp(fit, FAN_BIN, DET_ROWS, 0, DET_COLS // FAN_BIN, 1, roll=roll, voff=voff)
    return to_ideal(proj["fan"], W, 1, DET_COLS // FAN_BIN)


def _reconstruct(method: str, p: np.ndarray, geom: dict, tv_weight: float, allow: bool):
    t0 = time.perf_counter()
    if method == "FDK":
        x = ctscan.fdk_reconstruct(p, geom, device="cpu", allow_incomplete=allow)
    elif method == "SIRT":
        x = ctscan.sirt_reconstruct(p, geom, n_iter=SIRT_ITERS, device="cpu")
    elif method == "OS-SART":
        x = ctscan.os_sart_reconstruct(p, geom, n_iter=OSSART_ITERS, n_subsets=min(10, geom["n_views"]),
                                       device="cpu")
    elif method == "TV":
        x = ctscan.tv_reconstruct(p, geom, tv_weight=tv_weight, n_iter=TV_ITERS, device="cpu")
    else:
        raise ValueError(method)
    return np.asarray(x)[0], time.perf_counter() - t0


METHODS = ("FDK", "SIRT", "OS-SART", "TV")


def choose_tv_weight(p_all: np.ndarray, fit: dict) -> tuple[float, dict]:
    """50 枚(6 枚に 1 枚)で TV を回し、使わなかった 250 枚への再投影誤差が最小の重みを選ぶ(参照は見ない)。"""
    use = np.arange(0, 300, 6)
    held = np.setdiff1d(np.arange(300), use)
    g_use = fan_geometry(fit, use)
    g_all = fan_geometry(fit, np.arange(300))
    errs = {}
    for w in TV_WEIGHTS:
        x, _ = _reconstruct("TV", p_all[use], g_use, w, False)
        re = ctscan.ct_forward_project(x[None], g_all, device="cpu")
        errs[w] = float(np.sqrt(np.mean((re[held] - p_all[held]) ** 2)))
    best = min(errs, key=errs.get)
    return best, errs


def chapter_fan(root: Path, proj: dict, geo: dict, g: Gates) -> dict:
    print("\n== 中央面(fan、束ね %d、%.2f mm)" % (FAN_BIN, FAN_VOXEL))
    fit = geo["fit"]
    p_all = fan_data(proj, fit)
    ref = load_reference(root, "full_AGD_50", FAN_N, 3, np.array([fit["src_z"]]))[0]
    ref_fdk = load_reference(root, "fdk_pos2", FAN_N, 3, np.array([fit["src_z"]]))[0]
    mask = disk(FAN_N, FAN_VOXEL)
    g.check("中央面", "参照(3 軌道)が円の中で空でも定数でもない",
            np.isfinite(ref).all() and float(np.ptp(ref[mask])) > 0.01, "範囲 %.4f〜%.4f /mm" % (ref.min(), ref.max()))
    base = score(ref_fdk, ref, mask)
    print("  配布元どうし(ASTRA の FDK 1200 枚 vs 3 軌道): RMSE %.4f /mm、SSIM %.3f" % (base["rmse"], base["ssim"]))

    tv_w, tv_errs = choose_tv_weight(p_all, fit)
    print("  TV の重み: 使わなかった 250 枚への再投影 RMSE %s → %.0e"
          % (", ".join("%.0e: %.4f" % kv for kv in tv_errs.items()), tv_w))
    g.check("中央面", "選んだ TV の重みは候補の端でない(候補の範囲が足りている)",
            TV_WEIGHTS[0] < tv_w < TV_WEIGHTS[-1], "%.0e(候補 %s)" % (tv_w, ", ".join("%.0e" % w for w in TV_WEIGHTS)))
    conds = [("300 枚", "full", 300, 360.0, p_all, fan_geometry(fit, np.arange(300)), ("FDK",))]
    for s in SPARSE_STEPS:
        views = np.arange(0, 300, s)
        conds.append(("%d 枚" % len(views), "sparse", len(views), 360.0, p_all[views], fan_geometry(fit, views),
                      METHODS))
    for arc in LIMITED_ARCS:
        views = np.arange(0, int(round(arc / fit["step_deg"])), LIMITED_STEP)
        conds.append(("%g°" % arc, "limited", len(views), arc, p_all[views], fan_geometry(fit, arc_views=views),
                      METHODS))
    rows, images = [], {}
    for label, kind, nview, arc, p, geom, methods in conds:
        allow = kind == "limited"
        for meth in methods:
            x, sec = _reconstruct(meth, p, geom, tv_w, allow)
            sc = score(x, ref, mask)
            rows.append({"cond": label, "kind": kind, "views": nview, "arc": arc, "method": meth,
                         "rmse": sc["rmse"], "ssim": sc["ssim"], "scale": sc["scale"], "seconds": sec})
            images[(label, meth)] = x
            print("  %-6s %-7s RMSE %.4f /mm  SSIM %.3f  平均の比 %.3f  %.1f s"
                  % (label, meth, sc["rmse"], sc["ssim"], sc["scale"], sec))
    allvals = np.asarray([v for v in images.values()])
    g.check("中央面", "全 %d 枚の再構成が有限で、定数でない" % len(images),
            np.isfinite(allvals).all() and all(float(np.ptp(v[mask])) > 1e-3 for v in images.values()))

    def r(cond, meth, key="rmse"):
        return next(x[key] for x in rows if x["cond"] == cond and x["method"] == meth)

    full = "300 枚"
    mine = images[(full, "FDK")]
    vs_astra = score(mine, ref_fdk, mask)
    flips = {"上下": ref_fdk[::-1], "左右": ref_fdk[:, ::-1], "転置": ref_fdk.T}
    flip_ssim = {k: score(mine, v, mask)["ssim"] for k, v in flips.items()}
    print("  Fullseye の FDK 300 枚 vs 配布元の FDK 1200 枚: RMSE %.4f /mm、SSIM %.3f、平均の比 %.4f"
          "(参照を反転させると SSIM %s)" % (vs_astra["rmse"], vs_astra["ssim"], vs_astra["scale"],
                                         " / ".join("%s %.2f" % kv for kv in flip_ssim.items())))
    g.check("中央面", "Fullseye の FDK = 配布元の FDK(別実装): SSIM > 0.9、平均の比 0.98〜1.02",
            vs_astra["ssim"] > 0.9 and 0.98 < vs_astra["scale"] < 1.02,
            "SSIM %.3f、比 %.4f" % (vs_astra["ssim"], vs_astra["scale"]))
    g.check("中央面", "向きは読み替えのまま(参照を上下・左右・転置すると SSIM < 0.5)",
            max(flip_ssim.values()) < 0.5, "最大 %.2f" % max(flip_ssim.values()))
    g.check("中央面", "全 300 枚の FDK は参照と SSIM > 0.85、平均の比 0.95〜1.05(絶対尺度)",
            r(full, "FDK", "ssim") > 0.85 and 0.95 < r(full, "FDK", "scale") < 1.05,
            "SSIM %.3f、比 %.3f" % (r(full, "FDK", "ssim"), r(full, "FDK", "scale")))
    g.check("中央面", "全 300 枚の FDK は配布元の FDK(1200 枚)より参照から遠い",
            r(full, "FDK") > base["rmse"], "%.4f > %.4f /mm" % (r(full, "FDK"), base["rmse"]))
    # 内訳: 差のどれだけが粗い格子(束ね 6・0.3 mm)の分か。0.1 mm で再構成して箱で平均し直す。
    big = FINE_BIN * fit["du"]
    gf = ctscan.ct_scan_geometry("fan", n_views=300, arc_deg=360.0, start_deg=float(fit["beta_deg"][0]),
                                 n_u=DET_COLS // FINE_BIN, n_v=1, vol_shape=(1, FINE_N, FINE_N), voxel=FINE_VOXEL,
                                 du=big, dv=big, dso=fit["dso"], dsd=fit["dsd"])
    W = ideal_warp(fit, FINE_BIN, FINE_ROWS, FINE_ROW0, DET_COLS // FINE_BIN, 1)
    pf = to_ideal(proj["fine"], W, 1, DET_COLS // FINE_BIN)
    xf = np.asarray(ctscan.fdk_reconstruct(pf, gf, device="cpu"))[0]
    ratio = int(round(FAN_VOXEL / FINE_VOXEL))
    xf3 = xf.reshape(FAN_N, ratio, FAN_N, ratio).mean(axis=(1, 3))
    fine = score(xf3, ref, mask)
    print("  内訳: 0.1 mm で再構成して 0.3 mm へ箱平均すると RMSE %.4f(0.3 mm で直接 %.4f、配布元 %.4f)"
          % (fine["rmse"], r(full, "FDK"), base["rmse"]))
    g.check("中央面", "内訳: 差の大半は粗い格子の分(0.1 mm で作り直すと RMSE が 0.7 倍未満)",
            fine["rmse"] < 0.7 * r(full, "FDK"), "%.4f / %.4f" % (fine["rmse"], r(full, "FDK")))
    worst = "%d 枚" % (300 // SPARSE_STEPS[-1])
    g.check("中央面", "25 枚では FDK が 4 手法で最も悪い(筋状の誤差)",
            r(worst, "FDK") == max(r(worst, m) for m in METHODS),
            " / ".join("%s %.4f" % (m, r(worst, m)) for m in METHODS))
    g.check("中央面", "25 枚では TV が 4 手法で最も良い", r(worst, "TV") == min(r(worst, m) for m in METHODS),
            "TV %.4f /mm" % r(worst, "TV"))
    half = "%d 枚" % (300 // SPARSE_STEPS[0])
    fdk_growth = r(worst, "FDK") / r(half, "FDK")
    tv_growth = r(worst, "TV") / r(half, "TV")
    g.check("中央面", "150 → 25 枚で誤差の伸びは TV が FDK より小さい", tv_growth < fdk_growth,
            "TV ×%.2f、FDK ×%.2f" % (tv_growth, fdk_growth))
    narrow = "%g°" % LIMITED_ARCS[-1]
    g.check("中央面", "90° ではどの手法も 300 枚の FDK の 1.5 倍より悪い(欠けた向きは戻らない)",
            min(r(narrow, m) for m in METHODS) > 1.5 * r(full, "FDK"),
            "最良 %.4f / 300 枚の FDK %.4f" % (min(r(narrow, m) for m in METHODS), r(full, "FDK")))
    short = "%g°" % LIMITED_ARCS[0]
    g.check("中央面", "240°(180° + 扇の全角 32° を超える)の FDK は Parker の重みで、同じ 2.4° 刻みの全周 150 枚の 1.5 倍以内",
            r(short, "FDK") < 1.5 * r(half, "FDK"), "%.4f / %.4f /mm" % (r(short, "FDK"), r(half, "FDK")))
    return {"rows": rows, "images": images, "ref": ref, "ref_fdk": ref_fdk, "mask": mask, "baseline": base,
            "vs_astra": vs_astra, "flip_ssim": flip_ssim, "fine": fine,
            "tv_weight": tv_w, "tv_errs": tv_errs, "p_all": p_all}


# --------------------------------------------------------------------------- #
# 章: 3-D(cone)
# --------------------------------------------------------------------------- #
def cone_geometry(fit: dict, *, reverse: bool = False, offset_u: float = 0.0) -> dict:
    big = CONE_BIN * fit["du"]
    n_views = 300 // CONE_VIEW_STEP
    angles = fit["beta_deg"][0] + fit["step_deg"] * CONE_VIEW_STEP * np.arange(n_views)
    start = float(angles[0])
    return ctscan.ct_scan_geometry("cone", n_views=n_views, arc_deg=360.0, start_deg=start,
                                   n_u=DET_COLS // CONE_BIN, n_v=(DET_ROWS - 4) // CONE_BIN,
                                   vol_shape=CONE_N, voxel=CONE_VOXEL, du=big, dv=big, dso=fit["dso"],
                                   dsd=fit["dsd"], offset_u=offset_u)


def cone_data(proj: dict, fit: dict, *, roll=True, voff=True, reverse=False) -> np.ndarray:
    nu, nv = DET_COLS // CONE_BIN, (DET_ROWS - 4) // CONE_BIN
    W = ideal_warp(fit, CONE_BIN, DET_ROWS - 4, 2, nu, nv, roll=roll, voff=voff)
    p = to_ideal(proj["cone"][::CONE_VIEW_STEP], W, nv, nu)
    return p[::-1].copy() if reverse else p


def chapter_cone(root: Path, proj: dict, geo: dict, g: Gates) -> dict:
    print("\n== 3-D(cone、束ね %d、%.2f mm、%d 枚)" % (CONE_BIN, CONE_VOXEL, 300 // CONE_VIEW_STEP))
    fit = geo["fit"]
    geom = cone_geometry(fit)
    p = cone_data(proj, fit)
    t0 = time.perf_counter()
    x = np.asarray(ctscan.fdk_reconstruct(p, geom, device="cpu"))
    sec = time.perf_counter() - t0
    z = fit["src_z"] + (np.arange(CONE_N) - (CONE_N - 1) / 2.0) * CONE_VOXEL
    ref = load_reference(root, "full_AGD_50", CONE_N, 4, z)
    astra = load_reference(root, "fdk_pos2", CONE_N, 4, z)
    mask = disk(CONE_N, CONE_VOXEL)
    obj = ref[:, mask].mean(1) > 0.1 * float(ref[:, mask].mean(1).max())   # クルミのある高さ
    per_z = []
    for k in range(CONE_N):
        if not obj[k]:
            continue
        a = fs.rmse(x[k][mask], ref[k][mask])
        b = fs.rmse(astra[k][mask], ref[k][mask])
        c = fs.rmse(x[k][mask], astra[k][mask])
        per_z.append((float(z[k] - fit["src_z"]), float(a), float(b), float(c)))
    per_z = np.asarray(per_z)
    near = np.abs(per_z[:, 0]) < 4.0
    low = per_z[:, 0] < -12.0
    high = per_z[:, 0] > 12.0
    fs_near, fs_far = float(np.median(per_z[near, 1])), float(per_z[low, 1].max())
    as_near, as_far = float(np.median(per_z[near, 2])), float(per_z[low, 2].max())
    fs_high, as_high = float(per_z[high, 1].max()), float(per_z[high, 2].max())
    diff_peak = float(per_z[:, 3].max() / np.median(per_z[:, 3]))
    vs = float(fs.rmse(x[:, mask][obj], astra[:, mask][obj]))
    vs_ref = float(fs.rmse(astra[:, mask][obj], ref[:, mask][obj]))
    corr = float(np.corrcoef(x[:, mask][obj].ravel(), astra[:, mask][obj].ravel())[0, 1])
    print("  FDK %.1f s。Fullseye と ASTRA の FDK: RMSE %.4f /mm、相関 %.4f(ASTRA と 3 軌道の参照: %.4f)"
          % (sec, vs, corr, vs_ref))
    print("  高さごとの RMSE(中央値 |z|<4 mm / 最大 z<−12 mm / 最大 z>12 mm): Fullseye %.4f / %.4f / %.4f、"
          "ASTRA %.4f / %.4f / %.4f /mm、Fullseye − ASTRA の最大は中央値の ×%.2f"
          % (fs_near, fs_far, fs_high, as_near, as_far, as_high, diff_peak))
    g.check("3-D", "再構成が有限で定数でない", np.isfinite(x).all() and float(np.ptp(x)) > 0.01)
    g.check("3-D", "クルミのある高さが %d 枚以上" % 40, int(obj.sum()) >= 40, "%d 枚" % int(obj.sum()))
    g.check("3-D", "Fullseye の FDK と ASTRA の FDK の相関 > 0.95(同じ軌道・別実装)", corr > 0.95, "%.4f" % corr)
    g.check("3-D", "Fullseye と ASTRA の差は、ASTRA と 3 軌道の参照の差より小さい", vs < vs_ref,
            "%.4f < %.4f /mm" % (vs, vs_ref))
    g.check("3-D", "コーン角: 下端(z < −12 mm)で Fullseye の誤差が中央面の 2 倍超", fs_far > 2 * fs_near,
            "%.4f / %.4f" % (fs_far, fs_near))
    g.check("3-D", "コーン角: ASTRA の FDK も下端で 2 倍超(同じ式の限界で、実装の違いではない)",
            as_far > 2 * as_near, "%.4f / %.4f" % (as_far, as_near))
    g.check("3-D", "2 つの FDK の差は高さに依らない(最大が中央値の 1.5 倍未満 = 同じ所で同じだけ崩れる)",
            diff_peak < 1.5, "×%.2f" % diff_peak)
    return {"x": x, "ref": ref, "astra": astra, "per_z": per_z, "seconds": sec, "vs_astra": vs,
            "astra_vs_ref": vs_ref, "corr": corr, "near_far": (fs_near, fs_far, as_near, as_far),
            "upper": (fs_high, as_high), "diff_peak": diff_peak,
            "geom": geom, "p": p, "mask": mask, "obj": obj}


# --------------------------------------------------------------------------- #
# 章: 幾何の取り違え
# --------------------------------------------------------------------------- #
def adjoint_gap(geom_a: dict, geom_t: dict, shape, seed: int = 7) -> float:
    """``|<A x, y> − <x, Aᵀ y>| / |<A x, y>|``(``A`` は ``geom_a``、``Aᵀ`` は ``geom_t`` で作る)。"""
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(shape)
    y = rng.standard_normal((geom_a["n_views"], geom_a["n_v"], geom_a["n_u"]))
    ax = ctscan.ct_forward_project(x, geom_a, device="cpu")
    aty = ctscan.ct_adjoint_project(y, geom_t, device="cpu")
    lhs, rhs = float((ax * y).sum()), float((x * aty).sum())
    return abs(lhs - rhs) / abs(lhs)


def chapter_mistakes(proj: dict, geo: dict, fan: dict, g: Gates) -> dict:
    print("\n== 幾何の取り違え(中央面の FDK、全 300 枚)")
    fit = geo["fit"]
    ref, mask = fan["ref"], fan["mask"]
    views = np.arange(300)
    g_ok = fan_geometry(fit, views)
    variants = [
        ("正しい", fan["p_all"], g_ok),
        ("面内回転 0.5° を無視", fan_data(proj, fit, roll=False), g_ok),
        ("縦ずれ 7.2 画素を無視", fan_data(proj, fit, voff=False), g_ok),
        ("横に 1 画素(0.3 mm)ずらす", fan["p_all"], fan_geometry(fit, views, offset_u=1.0)),
        ("回転の向きを逆に", fan["p_all"][::-1].copy(), g_ok),
    ]
    rows, images = [], {}
    for name, p, geom in variants:
        x = np.asarray(ctscan.fdk_reconstruct(p, geom, device="cpu"))
        re = ctscan.ct_forward_project(x, geom, device="cpu")
        resid = float(np.sqrt(np.mean((re - p) ** 2)) / np.sqrt(np.mean(p ** 2)))
        sc = score(x[0], ref, mask)
        rows.append({"name": name, "rmse": sc["rmse"], "ssim": sc["ssim"], "resid": resid})
        images[name] = x[0]
        print("  %-16s RMSE %.4f /mm  SSIM %.3f  再投影の相対残差 %.4f" % (name, sc["rmse"], sc["ssim"], resid))
    ok = rows[0]
    by = {row["name"]: row for row in rows}
    roll = by["面内回転 0.5° を無視"]
    g.check("取り違え", "面内回転 0.5° は中央面の 0.3 mm 格子では効かない(RMSE の差 < 5 %)",
            abs(roll["rmse"] / ok["rmse"] - 1) < 0.05, "%.5f / %.5f" % (roll["rmse"], ok["rmse"]))
    for row in rows[2:]:
        g.check("取り違え", "%s: 参照との RMSE が正しい幾何の 2 倍超" % row["name"], row["rmse"] > 2 * ok["rmse"],
                "%.4f / %.4f" % (row["rmse"], ok["rmse"]))
    voff = by["縦ずれ 7.2 画素を無視"]
    g.check("取り違え", "盲点: 縦ずれは再投影の残差では見つからない(正しい幾何の残差以下)",
            voff["resid"] <= ok["resid"], "%.4f ≤ %.4f(別の高さの行も、それ自体は矛盾の無いデータ)"
            % (voff["resid"], ok["resid"]))
    big = [r for r in rows[1:] if r["name"] in ("横に 1 画素(0.3 mm)ずらす", "回転の向きを逆に")]
    for row in big:
        g.check("取り違え", "%s: 再投影の残差も正しい幾何より大きい" % row["name"], row["resid"] > ok["resid"],
                "%.4f > %.4f" % (row["resid"], ok["resid"]))
    # 隣接の恒等式: 一致は射影の対の整合だけを言う
    gap_fan = adjoint_gap(g_ok, g_ok, (1, FAN_N, FAN_N))
    g_rev = fan_geometry(fit, views, offset_u=1.0)
    gap_mismatch = adjoint_gap(g_ok, g_rev, (1, FAN_N, FAN_N))
    small = ctscan.ct_scan_geometry("cone", n_views=60, n_u=DET_COLS // CONE_BIN, n_v=(DET_ROWS - 4) // CONE_BIN,
                                    vol_shape=(24, 48, 48), voxel=0.8, du=CONE_BIN * fit["du"],
                                    dv=CONE_BIN * fit["du"], dso=fit["dso"], dsd=fit["dsd"],
                                    start_deg=float(fit["beta_deg"][0]))
    gap_cone = adjoint_gap(small, small, (24, 48, 48))
    print("  <Ax,y> と <x,Aᵀy> の相対差: fan %.1e、cone %.1e、A と Aᵀ の幾何を変えると %.1e"
          % (gap_fan, gap_cone, gap_mismatch))
    g.check("取り違え", "隣接の恒等式(fan、この装置の幾何): 相対差 < 1e-10", gap_fan < 1e-10, "%.1e" % gap_fan)
    g.check("取り違え", "隣接の恒等式(cone、この装置の幾何): 相対差 < 1e-10", gap_cone < 1e-10, "%.1e" % gap_cone)
    g.check("取り違え", "A と Aᵀ の幾何を食い違わせると恒等式は崩れる(相対差 > 1e-3)", gap_mismatch > 1e-3,
            "%.1e" % gap_mismatch)
    return {"rows": rows, "images": images, "adjoint_fan": gap_fan, "adjoint_cone": gap_cone,
            "adjoint_mismatch": gap_mismatch}


# --------------------------------------------------------------------------- #
# 章: 二重エネルギー(第 2 エネルギーは合成)
# --------------------------------------------------------------------------- #
def flat_gain(root: Path, b: int = FAN_BIN) -> float:
    """2 枚の白の画像の差から ``g`` を測る。``b`` × ``b`` に束ねた画素で、分散 = g × 平均 / b² の ``g``。

    束ねる前の画素で測ると、隣どうしの雑音の相関が見えないので、束ねた投影の ``g`` と比べられない
    (束ねる前 0.019、6 × 6 で 0.47。2026-11-08 に測った)。
    """
    proj_dir = root / "Walnut1" / "Projections" / ("tubeV%d" % realdata.WALNUT_CBCT_ORBIT)
    dark = _trafo(_tif(proj_dir / "di000000.tif")).astype(np.float64)
    f1 = _trafo(_tif(proj_dir / "io000000.tif")).astype(np.float64) - dark
    f2 = _trafo(_tif(proj_dir / "io000001.tif")).astype(np.float64) - dark
    diff = _bin(f1, b, 0, DET_ROWS) - _bin(f2, b, 0, DET_ROWS)
    diff = diff - diff.mean()                    # 2 枚の間の全体の明るさの差は雑音から外す
    return float(diff.var() / 2.0 * b * b / _bin(0.5 * (f1 + f2), b, 0, DET_ROWS).mean())


def chapter_dual(root: Path, proj: dict, geo: dict, fan: dict, g: Gates) -> dict:
    """二重エネルギー。★低い側は実データ、高い側は閉形式の合成(実データではない)。

    低い側 ``p_L`` = 実測の線積分。殻(参照の上位 10 %)の道のり ``t_A`` を Fullseye の射影で作り、
    残り ``t_B = (p_L − μ_A,L t_A) / μ_B,L`` を「殻以外の物質」と見なして、高い側を
    ``p_H = μ_A,H t_A + μ_B,H t_B + n_H`` と作る。``n_H`` は白の画像 2 枚の差から測った
    ポアソンの雑音(固定の種)で、その大きさは同じ角度の実測 2 枚の差から測る(空気で測り、物の中で
    確かめる。白の画像 2 枚の差は投影 1 枚より静かで、使うと雑音を小さく見積もる)。分解は線形なので、
    基底 0 の雑音は ``M⁻¹`` の (0, 1) 成分だけ ``n_H`` を拡大したものになる。
    """
    print("\n== 二重エネルギー(★第 2 エネルギーは合成、実データではない)")
    fit = geo["fit"]
    ref, mask = fan["ref"], fan["mask"]
    geom = fan_geometry(fit, np.arange(300))
    p_low = fan["p_all"]
    thr = float(np.percentile(ref[mask], 90))
    shell = ((ref > thr) & mask).astype(np.float64)
    t_a = ctscan.ct_forward_project(shell[None], geom, device="cpu")
    mal, mbl = DE_MU_LOW
    mah, mbh = DE_MU_HIGH
    t_b = (p_low - mal * t_a) / mbl
    g_flat = flat_gain(root)
    # 雑音の模型(ポアソン: −log の分散 = g / (b² T F))を実データで作り、実データで確かめる。
    # 同じ角度の 2 枚の差(白は共通なので白の雑音は消える)の、空気(T > 0.97)で g を測り、
    # 物の中(0.3 < T < 0.9)で 1/T の伸びを予測と照合する。
    rep_ = proj["repeat"]
    t_rep, f_rep = rep_["t"], rep_["gain_b"]
    bb = FAN_BIN * FAN_BIN
    air = t_rep > 0.97
    obj = (t_rep > 0.3) & (t_rep < 0.9)
    d_air = rep_["d"][air] - np.median(rep_["d"][air])
    d_obj = rep_["d"][obj] - np.median(rep_["d"][obj])
    g_proj = float(d_air.var() / 2.0 / np.mean(1.0 / (bb * t_rep[air] * f_rep[air])))
    meas = float(d_obj.std() / math.sqrt(2.0))
    model = float(np.sqrt(np.mean(g_proj / (bb * t_rep[obj] * f_rep[obj]))))
    quiet = g_proj / g_flat
    # 合成の第 2 エネルギーの雑音: 同じ模型(投影 1 枚の雑音 + 白 2 枚の平均の雑音)、固定の種
    flat_b = float(f_rep.mean())
    trans = np.exp(-p_low)
    sigma = np.sqrt((g_proj / trans + 0.5 * g_flat) / (bb * flat_b))
    n_high = np.random.default_rng(20261107).standard_normal(p_low.shape) * sigma
    n_low = np.random.default_rng(20261108).standard_normal(p_low.shape) * sigma
    p_high = mah * t_a + mbh * t_b + n_high
    out = ctscan.ct_dual_energy_reconstruct(p_low, p_high, geom, mu_low=DE_MU_LOW, mu_high=DE_MU_HIGH,
                                            method="fdk", device="cpu")
    b0, b1 = np.asarray(out["basis_0"])[0], np.asarray(out["basis_1"])[0]
    m = np.array([DE_MU_LOW, DE_MU_HIGH], dtype=np.float64)
    inv = np.linalg.inv(m)
    fdk = lambda q, gg=geom: np.asarray(ctscan.fdk_reconstruct(q, gg, device="cpu"))[0]   # noqa: E731
    shell_rec = fdk(t_a)
    noise_single = float(fdk(n_low)[mask].std())               # 1 エネルギーの再構成の雑音(同じ模型)
    noise_b0 = float((b0 - shell_rec)[mask].std())             # 基底 0 から真の殻を引いた残り = 雑音だけ
    ratio = noise_b0 / noise_single
    pred = abs(inv[0, 1])
    lin = float(np.abs(b0 - (shell_rec + inv[0, 1] * fdk(n_high))).max())
    print("  条件数 %.2f(np.linalg.cond %.2f)、殻の閾値 %.4f /mm(参照の上位 10 %%)"
          % (out["condition"], np.linalg.cond(m), thr))
    print("  雑音の模型: 空気 %d 画素で g = %.4f(白 2 枚の差では %.4f、白は投影 1 枚の 1/%.1f の分散)。"
          "物の中 %d 画素で実測 %.2e、予測 %.2e(−log、束ね %d)"
          % (int(air.sum()), g_proj, g_flat, quiet, int(obj.sum()), meas, model, FAN_BIN))
    print("  再構成の雑音(円の中): 1 エネルギー %.2e、基底 0 %.2e /mm(×%.2f、|M⁻¹|₀₁ = %.2f)"
          % (noise_single, noise_b0, ratio, pred))
    g.check("二重", "条件数 = np.linalg.cond(M)", abs(out["condition"] - np.linalg.cond(m)) < 1e-9,
            "%.4f" % out["condition"])
    g.check("二重", "基底 0 = 殻の再構成 + (M⁻¹)₀₁ × n_H の再構成(線形、1e-9)", lin < 1e-9, "最大差 %.1e" % lin)
    g.check("二重", "同じ角度の 2 枚を比べた画素が空気・物の中とも 1000 以上",
            int(air.sum()) >= 1000 and int(obj.sum()) >= 1000, "%d / %d 画素" % (int(air.sum()), int(obj.sum())))
    g.check("二重", "雑音の模型(空気で測った g)は、物の中の実測と 0.7〜1.3 倍で合う(1/T の伸び)",
            0.7 < meas / model < 1.3, "実測 / 予測 = %.2f(模型は物の中の雑音を小さく見積もる)" % (meas / model))
    g.check("二重", "所見: 白の画像は投影 1 枚より静か(同じ束ね方で分散の比 > 2)。白の利得で雑音を作ると小さく見積もる",
            quiet > 2.0, "×%.1f" % quiet)
    g.check("二重", "基底 0 の雑音は 1 エネルギーの |M⁻¹|₀₁ 倍(±10 %)", abs(ratio / pred - 1) < 0.1,
            "×%.2f / ×%.2f" % (ratio, pred))
    return {"basis_0": b0, "basis_1": b1, "shell": shell, "condition": float(out["condition"]),
            "repeat_noise_measured": meas, "repeat_noise_model": model, "noise_single": noise_single,
            "noise_b0": noise_b0, "noise_ratio": ratio, "noise_pred": pred, "threshold": thr,
            "repeat_pixels": [int(air.sum()), int(obj.sum())], "gain_projection": g_proj, "gain_flat": g_flat,
            "flat_quieter": quiet}


# --------------------------------------------------------------------------- #
# CI の門(実データ無し): 合成の幾何ベクトルで、幾何の読み替えと恒等式
# --------------------------------------------------------------------------- #
def synthetic_gates(g: Gates) -> dict:
    """配布元と同じ形の幾何ベクトルを作り、``fit_geometry`` と ``ideal_warp`` が正しく読むかを確かめる。"""
    beta = np.deg2rad(1.2 * np.arange(300))
    th = math.radians(0.5)
    dso, dsd, src_z, dh = 66.0, 199.0, 0.3, 1.08
    n = np.stack([-np.sin(beta), np.cos(beta), 0 * beta], 1)
    uh = np.stack([np.cos(beta), np.sin(beta), 0 * beta], 1)
    z = np.array([0.0, 0.0, 1.0])
    s = -dso * n + np.array([0, 0, src_z])
    d = s + dsd * n + dh * z
    u = (np.cos(th) * uh - np.sin(th) * z) * DET_PIXEL_MM
    v = (np.sin(th) * uh + np.cos(th) * z) * DET_PIXEL_MM
    fit = fit_geometry(np.hstack([s, d, u, v]))
    g.check("合成", "fit_geometry が作った幾何を読み戻す(SOD・SDD・回転・縦ずれ・線源の高さ)",
            abs(fit["dso"] - dso) < 1e-9 and abs(fit["dsd"] - dsd) < 1e-9 and abs(fit["theta_deg"] - 0.5) < 1e-9
            and abs(fit["dh_mm"] - dh) < 1e-9 and abs(fit["src_z"] - src_z) < 1e-12,
            "%.4f %.4f %.4f° %.4f %.4f" % (fit["dso"], fit["dsd"], fit["theta_deg"], fit["dh_mm"], fit["src_z"]))
    # 主点に当たる実画素(元の画素の座標)が、理想検出器の中心へ写ること
    W = ideal_warp(fit, 1, DET_ROWS, 0, DET_COLS, DET_ROWS)
    c_raw = (DET_COLS - 1) / 2.0 - dh * math.sin(th) / DET_PIXEL_MM * (-1)
    r_raw = (DET_ROWS - 1) / 2.0 - dh * math.cos(th) / DET_PIXEL_MM
    # 主点 p = d − dh ẑ。実画素座標で d からの (−dh ẑ) を u_real, v_real へ分ける
    a_u = (-dh * z) @ (u[0] / DET_PIXEL_MM)
    a_v = (-dh * z) @ (v[0] / DET_PIXEL_MM)
    c_raw = (DET_COLS - 1) / 2.0 + a_u / DET_PIXEL_MM
    r_raw = (DET_ROWS - 1) / 2.0 + a_v / DET_PIXEL_MM
    q = W @ np.array([c_raw, r_raw, 1.0])
    err = float(np.hypot(q[0] - (DET_COLS - 1) / 2.0, q[1] - (DET_ROWS - 1) / 2.0))
    g.check("合成", "ideal_warp: 主点の実画素 → 理想検出器の中心(< 1e-9 画素)", err < 1e-9, "%.1e 画素" % err)
    geom = ctscan.ct_scan_geometry("fan", n_views=90, n_u=96, n_v=1, vol_shape=(1, 64, 64), voxel=0.5, dso=dso,
                                   dsd=dsd, du=1.2, dv=1.2)
    gap = adjoint_gap(geom, geom, (1, 64, 64))
    g.check("合成", "隣接の恒等式(fan、合成): 相対差 < 1e-10", gap < 1e-10, "%.1e" % gap)
    return {"adjoint_gap": gap, "warp_err_px": err}


# --------------------------------------------------------------------------- #
# 図
# --------------------------------------------------------------------------- #
def _crop(img: np.ndarray, mask: np.ndarray) -> np.ndarray:
    return np.where(mask, img, 0.0)


def write_figures(fan: dict, cone: dict, mis: dict, dual: dict, g: Gates) -> None:
    if not figs.enabled():
        return
    ref, mask = fan["ref"], fan["mask"]
    vr = (0.0, float(np.percentile(ref[mask], 99.8)))
    conds = ["150 枚", "25 枚", "150°", "90°"]
    panels, caps = [], []
    for cnd in conds:
        panels.append(_crop(ref, mask))
        caps.append("参照(3 軌道 3600 枚)")
        for meth in ("FDK", "SIRT", "TV"):
            panels.append(_crop(fan["images"][(cnd, meth)], mask))
            row = next(x for x in fan["rows"] if x["cond"] == cnd and x["method"] == meth)
            caps.append("%s %s RMSE %.4f" % (cnd, meth, row["rmse"]))
    figs.save_grid("methods_sparse_limited", panels, captions=caps, ncols=4, gray=True, vrange=vr,
                   title="実測クルミの中央面: 投影を減らすと手法の差が出る(参照との RMSE [1/mm])",
                   caption="行 = 全周 150 枚 / 全周 25 枚 / 150° / 90°、列 = 参照 / FDK / SIRT / TV。濃淡は全パネル共通の "
                           "0〜%.3f /mm。90° の TV は平らな塊を描き足すが、形は参照と違う。" % vr[1])
    figs.save_grid("reference_vs_fdk", [_crop(ref, mask), _crop(fan["ref_fdk"], mask),  # gray-ok: CT の減弱係数の断面。キャプションの「高さ」は線源の高さで、高さの場ではない
                                        _crop(fan["images"][("300 枚", "FDK")], mask)],
                   captions=["参照: 3 軌道 3600 枚", "配布元の FDK 1200 枚", "Fullseye FDK 300 枚"],
                   ncols=3, gray=True, vrange=vr, title="照合の相手(配布元の 2 つの再構成)",
                   caption="中央面(線源の高さ)。参照は 0.1 mm の格子を 0.3 mm へ箱で平均した。")
    sparse = [x for x in fan["rows"] if x["kind"] in ("sparse", "full")]
    series = []
    for meth in METHODS:
        pts = sorted((x["views"], x["rmse"]) for x in sparse if x["method"] == meth)
        series.append((meth, [p[0] for p in pts], [p[1] for p in pts]))
    series.append(("配布元の FDK 1200 枚", [25, 300], [fan["baseline"]["rmse"]] * 2))
    figs.save_plot("rmse_vs_views", series, kinds=["line"] * 5, styles=[None] * 4 + ["dashed"],
                   colors=["wrong", "neutral", "baseline", "right", "reference"],
                   xlabel="投影の枚数(360° を等間隔)", ylabel="参照との RMSE [1/mm]",
                   title="間引くと FDK が先に崩れる", source=SOURCE,
                   caption="TV の重みは 50 枚の条件で、使わなかった 250 枚への再投影誤差が最小の %.0e(参照は見ない)。"
                           % fan["tv_weight"])
    lim = [x for x in fan["rows"] if x["kind"] == "limited" or x["cond"] == "150 枚"]
    series = []
    for meth in METHODS:
        pts = sorted((x["arc"], x["rmse"]) for x in lim if x["method"] == meth)
        series.append((meth, [p[0] for p in pts], [p[1] for p in pts]))
    figs.save_plot("rmse_vs_arc", series, kinds=["line"] * 4, colors=["wrong", "neutral", "baseline", "right"],
                   xlabel="角度の範囲 [°](2.4° 刻み)", ylabel="参照との RMSE [1/mm]",
                   title="限られた角度では、どの手法も欠けた向きを戻せない", source=SOURCE,
                   caption="FDK は 212°(180° + 扇の全角)未満で allow_incomplete=True。")
    k = (CONE_N - 1) // 2
    cm = cone["mask"]
    vr3 = (0.0, float(np.percentile(cone["ref"][:, cm], 99.8)))
    figs.save_grid("cone_vertical", [cone["ref"][::-1, k, :], cone["astra"][::-1, k, :], cone["x"][::-1, k, :]],
                   captions=["参照: 3 軌道", "ASTRA FDK 軌道 2", "Fullseye FDK 軌道 2"], ncols=3, gray=True,
                   vrange=vr3, title="縦の断面(上 = 回転軸の上向き)。円軌道の FDK は中央面の外で近似",
                   caption="0.4 mm、150 枚。下端で 2 つの FDK が同じ形に崩れる(円軌道は中央面の外を測り切らない: Tuy の条件)。")
    pz = cone["per_z"]
    figs.save_plot("cone_error_by_height", [("Fullseye FDK", list(pz[:, 0]), list(pz[:, 1])),
                                            ("ASTRA FDK(配布元)", list(pz[:, 0]), list(pz[:, 2])),
                                            ("Fullseye − ASTRA", list(pz[:, 0]), list(pz[:, 3]))],
                   kinds=["line"] * 3, styles=[None, "dashed", "dotted"], colors=["emphasis", "reference", "neutral"],
                   xlabel="中央面からの高さ [mm]", ylabel="RMSE [1/mm]",
                   title="高さごとの誤差(3 軌道の参照に対して)", source=SOURCE,
                   caption="2 つの FDK は下端で同じだけ崩れ、差(点線)は高さに依らない。上端の伸びは小さい(理由は確かめていない)。"
                           "Fullseye の床が高いのは 0.4 mm に束ねた分(中央面の内訳を参照)。")
    names = [r["name"] for r in mis["rows"]]
    panels = [_crop(mis["images"][n], mask) for n in names] + [_crop(mis["images"][n] - ref, mask) for n in names]
    caps = (["%s %.4f" % (r["name"], r["rmse"]) for r in mis["rows"]]
            + ["差(再構成 − 参照)" for _ in names])
    figs.save_grid("geometry_mistakes", panels, captions=caps, ncols=5, gray=[True] * 5 + [False] * 5,
                   signed=[False] * 5 + [True] * 5, vrange=[vr] * 5 + [(-0.03, 0.03)] * 5,
                   title="幾何の取り違え(中央面の FDK、参照との RMSE [1/mm]、下段は差 ±0.03 /mm)",
                   caption="隣接の恒等式はどの取り違えでも 1e-10 以下で成り立つ。取り違えは参照と再投影の残差で見つける。")
    lim1 = float(np.percentile(np.abs(dual["basis_1"][mask]), 99.5))
    figs.save_grid("dual_energy_synthetic", [dual["shell"], dual["basis_0"], dual["basis_1"]],
                   captions=["殻(参照の上位 10 %)", "基底 0(殻)", "基底 1(殻以外、符号つき)"], ncols=3,
                   gray=[True, True, False], signed=[False, False, True],
                   vrange=[(0.0, 1.0), (0.0, 1.0), (-lim1, lim1)],
                   title="★第 2 エネルギーは合成(実データではない)",
                   caption="低い側は実データ、高い側は閉形式の合成 + 実測の 2 枚から作った雑音。条件数 %.2f。基底 0 の雑音は "
                           "1 エネルギーの ×%.2f(|M⁻¹|₀₁ = %.2f)。基底 1 は殻の中で負(仮定した μ が実物と違う分)。"
                           % (dual["condition"], dual["noise_ratio"], dual["noise_pred"]))
    header = ["条件", "FDK", "SIRT", "OS-SART", "TV"]
    rows = []
    for cnd in sorted({x["cond"] for x in fan["rows"]}, key=lambda c: [x["cond"] for x in fan["rows"]].index(c)):
        cells = []
        for m in METHODS:
            hit = [x for x in fan["rows"] if x["cond"] == cnd and x["method"] == m]
            cells.append("%.4f / %.2f / %.1fs" % (hit[0]["rmse"], hit[0]["ssim"], hit[0]["seconds"]) if hit else "—")
        rows.append([cnd] + cells)
    figs.save_table("scores", header, rows, title="中央面: 参照との RMSE [1/mm] / SSIM / 時間(CPU)",
                    caption="門 %d 本、外れ %d 本。" % (len(g.rows), len(g.failed())))


def _print_recorded():
    print("実データが無いため実データの章を飛ばす。CI は取得しない(tools/fetch_walnut_cbct.py)。")
    print("記録値(RECORDED): " + json.dumps(RECORDED, ensure_ascii=False, sort_keys=True))


def main() -> None:
    t0 = time.perf_counter()
    g = Gates()
    synthetic_gates(g)
    root = None
    if not (os.environ.get("CI") and not os.environ.get("FULLSEYE_WALNUT_CBCT_DATA")):
        try:
            root = realdata.walnut_cbct_root(required=False)
        except realdata.RealDataError as exc:
            print("実データ配置を拒否: %s" % exc)
            root = None
    if root is None:
        _print_recorded()
        if g.failed():
            raise SystemExit("門が外れた: %s" % "; ".join("%s %s" % r[:2] for r in g.failed()))
        print("門 %d 本すべて通過(%.1f s)\nPASS" % (len(g.rows), time.perf_counter() - t0))
        return
    print("実データ: %s" % SOURCE)
    print("置き場: 環境変数 FULLSEYE_WALNUT_CBCT_DATA か既定のキャッシュ(一覧の SHA-256 %s)"
          % realdata.WALNUT_CBCT_MANIFEST_SHA256)
    geo = chapter_geometry(root, g)
    proj = load_projections(root, g)
    fan = chapter_fan(root, proj, geo, g)
    cone = chapter_cone(root, proj, geo, g)
    mis = chapter_mistakes(proj, geo, fan, g)
    dual = chapter_dual(root, proj, geo, fan, g)
    record = {
        "dataset_manifest_sha256": realdata.WALNUT_CBCT_MANIFEST_SHA256,
        "geometry": {k: geo["fit"][k] for k in ("dso", "dsd", "du", "theta_deg", "da_mm", "dh_mm", "src_z",
                                                "step_deg")},
        "measured_angles_rule": geo["measured_angles_rule"],
        "fan": [{k: x[k] for k in ("cond", "method", "rmse", "ssim", "scale", "seconds")} for x in fan["rows"]],
        "fan_baseline_astra_vs_ref": fan["baseline"], "fan_fullseye_vs_astra": fan["vs_astra"],
        "fan_fine_0p1mm_boxed": fan["fine"],
        "tv_weight": fan["tv_weight"], "tv_holdout_rmse": {"%g" % k: v for k, v in fan["tv_errs"].items()},
        "cone": {"seconds": cone["seconds"], "vs_astra": cone["vs_astra"], "astra_vs_ref": cone["astra_vs_ref"],
                 "corr": cone["corr"], "near_far": cone["near_far"], "upper": cone["upper"],
                 "diff_peak": cone["diff_peak"]},
        "mistakes": mis["rows"], "adjoint": {"fan": mis["adjoint_fan"], "cone": mis["adjoint_cone"],
                                             "mismatch": mis["adjoint_mismatch"]},
        "dual": {k: dual[k] for k in ("condition", "repeat_noise_measured", "repeat_noise_model", "noise_single",
                                      "noise_b0", "noise_ratio", "noise_pred", "threshold", "repeat_pixels",
                                      "gain_projection", "gain_flat", "flat_quieter")},
        "gates": len(g.rows), "failed": len(g.failed()),
    }
    print("\nRECORDED_JSON=" + json.dumps(record, ensure_ascii=False, sort_keys=True))
    write_figures(fan, cone, mis, dual, g)
    errors = figs.errors()
    if errors:
        raise SystemExit("図の書き出しで失敗: " + "; ".join(errors))
    bad = g.failed()
    if bad:
        raise SystemExit("門が %d 本外れた: %s" % (len(bad), "; ".join("%s %s" % r[:2] for r in bad)))
    print("門 %d 本すべて通過(%.1f s)\nPASS" % (len(g.rows), time.perf_counter() - t0))


if __name__ == "__main__":
    main()
