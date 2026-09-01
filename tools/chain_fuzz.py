# -*- coding: utf-8 -*-
"""chain_fuzz — 型で op を繋ぐ拡散・収束ファザー(ops3d + ops1d)。

進化レジストリの流儀を目録全体へ: 型互換な op をランダムに連鎖(拡散)し、
失敗を署名でまとめて最小再現に絞る(収束)。狙いは「単体テストは通るが
**op の出力を次の op が食うと壊れる**」クラスの不具合 — 型契約の嘘、
タプル/リスト梱包の不一致、NaN の漏出、想定外の例外種。

判定の分類:
  CONTRACT  ValueError で明確な文言 = fail-closed が仕事をした(白)
  SUSPECT   それ以外の例外(TypeError/IndexError/KeyError/…)= 契約の穴
  NONFINITE 有限入力から NaN/Inf が無言で出た = 毒の漏出
  TYPEMISS  目録の宣言 out 型と実際の返りが違う = 型の嘘
  GROWTH    産物が pool 上限超(拡大系の指数増殖)= 記録して捨てる
  SLOW      1 op が閾値超(既定 10s)= 性能スメル

再現性: 連鎖 i は master seed から導いた **連鎖固有 seed** で回る(共有 rng
だと i 番目だけを後から再現できないため)。各 findings はその ``seed`` を
持つので、``--minimize`` が正確に再走できる。

使い方:
    py -3.11 tools/chain_fuzz.py --chains 400 --length 6 --seed 0
    py -3.11 tools/chain_fuzz.py --minimize out/chain_fuzz.jsonl   # 全署名を短縮
    py -3.11 tools/chain_fuzz.py --minimize out/chain_fuzz.jsonl --only vol_frangi
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import traceback
import zlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

SLOW_S = 10.0


# --------------------------------------------------------------------------- #
# 型 → 生成器(小さく・決定的に。voxel は 16^3 で全 op が秒未満)               #
# --------------------------------------------------------------------------- #
def _ball_vol(rng, n=16):
    z, y, x = np.mgrid[0:n, 0:n, 0:n].astype(np.float64)
    c = n / 2.0
    v = ((z - c) ** 2 + (y - c) ** 2 + (x - c) ** 2 <= (n * 0.3) ** 2).astype(np.float64)
    return np.clip(v + 0.05 * rng.standard_normal(v.shape), 0.0, 1.0)


def _points(rng, n=160):
    return rng.random((n, 3)) * 10.0


def _mesh(rng):
    """三角形メッシュ ``(V (nv,3) float, F (nf,3) int)``。**3 種を必ず混ぜる**。

    2026-09-02 まで、この関数は定義だけあって ``make_generators()`` から
    **一度も参照されていなかった**(実測)。mesh は convex_hull / poisson_lite /
    alpha_shape_mesh / voxel_to_mesh が産むので型到達可能性としては到達側に
    入るが、種が無いと「同じ連鎖の中で先に生成 op が引かれた場合だけ」到達する
    = keypoints で実測した未到達パターンそのものになる。

    3 種を混ぜるのは分岐を全部踏ませるため:
      * 凸包 — 頂点数の多い一般の閉曲面(いちばん現実の走査に近い)。
      * 直方体 — 巻きが厳密に外向きの閉多面体。``cull_backfaces=True`` で
        「裏面だから当たらない」経路が確実に立つ。
      * 平面パッチ(2 三角形の開いた面)— 大半の視線が **miss** する。miss の
        NaN 経路と「当たり 0 の欠陥領域」を踏むのはこれだけ。
    片方だけだと cadmap の backface / miss 分岐が一度も走らない。
    """
    r = rng.random()
    if r < 0.5:
        import meshrepair                                # noqa: PLC0415
        return meshrepair.convex_hull(_points(rng, 60))
    if r < 0.8:
        h = 1.0 + rng.random(3) * 3.0
        V = np.array([[-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
                      [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]], float) * h
        F = np.array([[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7],
                      [0, 1, 5], [0, 5, 4], [3, 7, 6], [3, 6, 2],
                      [0, 4, 7], [0, 7, 3], [1, 2, 6], [1, 6, 5]], np.int64)
        return V, F
    a, b = 1.0 + 3.0 * rng.random(2)
    V = np.array([[-a, -b, 0.0], [a, -b, 0.0], [a, b, 0.0], [-a, b, 0.0]])
    return V, np.array([[0, 2, 1], [0, 3, 2]], np.int64)


def _labels_2d(rng):
    """2-D の整数ラベル画像 (H,W)(背景 0 + 矩形領域 2-3 個)。

    **これが無いと 2-D ラベルを食う op は永久に実行されない**(実測):
    ``labels`` を出す既存 op は 7 つあるが、``label_components`` / ``vol_label``
    / ``vol_watershed`` は **(D,H,W) の 3-D**、``region_growing`` /
    ``euclidean_cluster`` / ``plane_segmentation`` / ``segment_rigid_motions``
    は **(N,) の 1-D** で、**2-D のラベル画像を産む op が 1 つも無い**。
    実測 (2026-09-02, 1500 連鎖): 種を置かないと ``cad_defect_to_cad`` は
    引かれても毎回 ``labels must be a 2-D (H, W) label image, got (160,)`` で
    fail-closed し、**一度も実行されないまま「発見ゼロ」に見えた**。
    (同じ穴を ``illuminant_from_dichromatic_planes`` は専用 arg builder で
    自前のラベルを作って回避している。)
    """
    h = int(rng.integers(24, 49))
    w = int(rng.integers(24, 49))
    lab = np.zeros((h, w), np.int32)
    for k in range(1, int(rng.integers(2, 4))):
        r0 = int(rng.integers(0, h - 6))
        c0 = int(rng.integers(0, w - 6))
        lab[r0:r0 + int(rng.integers(3, 7)), c0:c0 + int(rng.integers(3, 7))] = k
    return lab


def _score_volume(rng):
    """ピークを 1 つ持つ異方性ガウスの相関 volume(サブボクセル精緻化の入力)。

    軸ごとに幅を変えてあるので、軸別の放物線当てはめと全 Hessian 法の差が
    実際に現れる。中心は格子からわざと外して置く(整数ピークにすると
    サブボクセル精緻化が「何もしない」経路しか通らない)。
    """
    n = 16
    z, y, x = np.mgrid[0:n, 0:n, 0:n].astype(np.float64)
    c = 7.5 + rng.uniform(-1.5, 1.5, size=3)
    s = rng.uniform(1.5, 3.0, size=3)
    return np.exp(-(((z - c[0]) / s[0]) ** 2 + ((y - c[1]) / s[1]) ** 2
                    + ((x - c[2]) / s[2]) ** 2) / 2.0)


def _motion_clip(rng):
    """既知の振幅・周波数でサブピクセル並進させた格子のクリップ。

    乱数フレームを積んでも「振動している」ことにはならず、帯域通過も位相増幅も
    意味を持たない。合成の前方モデルを種にすると、増幅後の変位が alpha*d に
    なるという**閉形式の真値**がプールの中に入る。
    """
    import motionmag                                     # noqa: PLC0415
    return motionmag.synthesize_translation(
        (32, 32), 32, amplitude_px=float(rng.uniform(0.05, 0.5)),
        frequency_hz=4.0, fps=32.0,
        direction_deg=float(rng.uniform(0.0, 180.0)),
        noise_sigma=float(rng.uniform(0.0, 0.02)),
        seed=int(rng.integers(0, 1 << 31)))


def _quat_image(rng):
    """四元数画像。**2 種類を必ず混ぜて出す**。

    色の四元数 (0,R,G,B) とモノジェニック信号は形が同じ (H,W,4) だが意味が
    違い、取り違えても例外は出ない(色画像の方位を測ると滑らかで
    もっともらしい atan2(G,R) 地図が返る)。片方しか種に置かないと、
    相手側の op が永久に fail-closed のまま「発見ゼロ」に見える。
    """
    import quatimage                                    # noqa: PLC0415
    if rng.random() < 0.5:
        return quatimage.monogenic_signal(rng.random((32, 32)), wavelength_px=8.0)
    import photometric                                  # noqa: PLC0415
    import specularity                                  # noqa: PLC0415
    return quatimage.rgb_to_quaternion(specularity.dichromatic_render(
        photometric.surface_normals(
            6.0 * np.exp(-((np.arange(32)[:, None] - 16.0) ** 2
                           + (np.arange(32)[None, :] - 16.0) ** 2) / 200.0)),
        (0.80, 0.55, 0.35), (0.30, 0.20, 1.0), specular=0.5, shininess=48.0))


def _beat_cube(rng):
    """FMCW ビート立方体(アンテナ, チャープ, サンプル)の複素。

    **4 素子で出すのが要点**: 既定の 1 素子だと開口が無く、ビームフォーミング
    2 op が毎回「開口が無い」で fail-closed になって一度も実行されない
    (= 「頑健だから発見ゼロ」と「未実行」が区別できなくなる)。
    """
    import rangedoppler                                  # noqa: PLC0415
    d = rangedoppler.fmcw_design(n_samples=32, n_chirps=16, n_antennas=4)
    dr, dv = d["range_bin_m"], d["velocity_bin_ms"]
    n = int(rng.integers(1, 4))
    return rangedoppler.fmcw_beat_simulate(
        ranges_m=[float(rng.integers(1, 30)) * dr for _ in range(n)],
        velocities_ms=[float(rng.integers(-7, 8)) * dv for _ in range(n)],
        angles_deg=[float(rng.uniform(-60.0, 60.0)) for _ in range(n)],
        amplitudes=[float(rng.uniform(0.3, 1.0)) for _ in range(n)],
        n_samples=32, n_chirps=16, n_antennas=4,
        noise_sigma=float(rng.uniform(0.0, 0.05)),
        seed=int(rng.integers(0, 1 << 31)))


def _photon_counts(rng):
    """光子カウントヒストグラム(非負・時間 bin 添字)。

    合成ではなく **実データと同じ作り方**にしてある: 既知距離の dToF 復路と
    背景光を足して Poisson 標本化する。適当な非負乱数を渡すと「山が 1 つある」
    という前提の op(ピーク探索・寿命フィット)が現実に無い形を食うことになる。
    """
    import photoncount                                   # noqa: PLC0415
    return photoncount.tcspc_simulate(
        distance_m=float(rng.uniform(0.5, 3.5)), bins=256, bin_ps=100.0,
        signal_photons=float(rng.uniform(100.0, 2000.0)),
        ambient_photons=float(rng.uniform(0.0, 500.0)),
        irf_fwhm_ps=500.0, seed=int(rng.integers(0, 1 << 31)))


def _jones_vec(rng):
    """Jones ベクトル (Ex, Ey): 長さ 2 の complex。単位強度に正規化。"""
    v = rng.standard_normal(2) + 1j * rng.standard_normal(2)
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else np.array([1.0 + 0j, 0.0 + 0j])


def _stokes_vec(rng):
    """Stokes ベクトル (S0..S3): 長さ 4 の実で、偏光度 <= 1 を必ず満たす。

    ここを満たさない値を入れると mueller_apply/stokes_analyze の fail-closed が
    正しく発火するだけで、偏光ファミリの実経路は一度も通らない。"""
    d = rng.standard_normal(3)
    d /= max(float(np.linalg.norm(d)), 1e-12)
    return np.concatenate([[1.0], d * float(rng.uniform(0.0, 1.0))])


def make_generators():
    return {
        "voxel": _ball_vol,
        "points": _points,
        "image2d": lambda rng: rng.random((32, 32)),
        "depth": lambda rng: 1.0 + rng.random((32, 32)),
        "images": lambda rng: [rng.random((32, 32)) for _ in range(4)],
        "normals": lambda rng: (lambda v: v / np.linalg.norm(v, axis=1, keepdims=True))(
            rng.standard_normal((160, 3))),
        "signal": lambda rng: np.sin(np.linspace(0, 8 * np.pi, 256)) + 0.1 * rng.standard_normal(256),
        "vector": lambda rng: (lambda v: v / np.linalg.norm(v))(rng.standard_normal(3)),
        "pose": lambda rng: (np.eye(3), np.zeros(3)),
        "measurement": lambda rng: float(rng.random()),
        "angle": lambda rng: float(rng.uniform(0, 90)),
        "position": lambda rng: (8.0, 8.0, 8.0),
        "sdf": lambda rng: _ball_vol(rng) - 0.5,
        "gaussians": lambda rng: {"mu": _points(rng, 40), "sigma": np.full(40, 0.3),
                                  "w": np.full(40, 1.0 / 40)},
        # HALCON の complex 画像形式に対応(cx_fft の出力レイアウト = 中心 DC)
        "cimage": lambda rng: np.fft.fftshift(np.fft.fft2(rng.random((32, 32)))),
        # organized 系(H,W,3)— (N,3) の points/normals とは別型
        "pointmap": lambda rng: rng.random((16, 16, 3)) * 8.0,
        "normalmap": lambda rng: np.dstack([np.zeros((16, 16)), np.zeros((16, 16)),
                                            np.ones((16, 16))]),
        # 数学ファミリ(opsmath): matrix は image2d(32²固定)より小さい一般行列
        "matrix": lambda rng: rng.standard_normal(
            (int(rng.integers(2, 12)), int(rng.integers(2, 12)))),
        "roots": lambda rng: rng.standard_normal(6) + 1j * rng.standard_normal(6),
        # cpoints = 複素平面の順序つき点列(閉曲線)。tier2 複素解析の入口は
        # 「一様サンプルの単位円」— これなら Laurent 係数(円限定)も通り、
        # 写像 op の像(退化した輪郭)が下流へ回って敵対入力にもなる
        "cpoints": lambda rng: np.exp(
            2j * np.pi * np.arange(64, dtype=np.float64) / 64.0),
        # 光学ファミリ(opsoptics)の偏光 2 語。長さ固定 + 物理制約つきなので
        # signal/cpoints へ相乗りさせると常に CONTRACT にしかならない(=偏光
        # 連鎖を一度も通らない)ため専用プールにする
        "jones": _jones_vec,
        "stokes": _stokes_vec,
        # ライトフィールド = 4-D (V,U,H,W)。空間サイズを image2d と揃えた 32x32
        # にしてあるので、2 入力の lf_all_in_focus(lightfield + image2d)が
        # ファザーの中で実際に噛み合う
        "lightfield": lambda rng: __import__("lightfield").lf_synthesize(
            (0.0, 1.0), angular=(3, 3), shape=(32, 32),
            seed=int(rng.integers(0, 1000)))[0],
        # 四元数画像 (H,W,4)、順序 (w,x,y,z)
        "qimage": _quat_image,
        # z 走査スタック (Z,H,W)。既知の高さ地図から合成するので真値が厳密
        "zscan": lambda rng: __import__("interferometry").csi_stack_simulate(
            5.0 + 2.0 * rng.random((16, 16)), 0.0, 0.05, 241, 0.6,
            envelope_fwhm_um=2.8258,
            reflectivity=0.4 + 0.6 * rng.random((16, 16)),
            noise=float(rng.uniform(0.0, 0.01)),
            seed=int(rng.integers(0, 1 << 31))),
        # 掃引 1-D。**2 種を必ず混ぜる**(干渉信号とスペクトル)。片方だけだと
        # 相手側の op が永久に fail-closed のまま「発見ゼロ」に見える
        "sweep": lambda rng: (
            __import__("interferometry").csi_signal_simulate(
                4.0 + 4.0 * rng.random(), 0.0, 0.05, 241, 0.6,
                envelope_fwhm_um=2.8258, reflectivity=0.5 + rng.random(),
                noise=float(rng.uniform(0.0, 0.01)),
                seed=int(rng.integers(0, 1 << 31)))
            if rng.random() < 0.5 else
            __import__("interferometry").chromatic_confocal_simulate(
                -15.0 + 30.0 * rng.random(), 500.0, 0.5, 401, 0.20, 600.0,
                peak_fwhm_nm=float(rng.uniform(2.0, 8.0)),
                noise=float(rng.uniform(0.0, 10.0)),
                seed=int(rng.integers(0, 1 << 31)))),
        # FMCW ビート立方体。既知の (距離, 速度, 到来角, 振幅) から合成するので
        # 2D FFT のピークがどこに立つべきかが閉形式で分かっている
        "beatcube": _beat_cube,
        # 偏光子掃引。既定の 0/45/90/135 度は面偏光センサの実配置で、
        # polarization_render の逆が polarization_separate なので鎖が閉じる
        "polsweep": lambda rng: __import__("specularity").polarization_render(
            0.40 + 0.30 * rng.random((32, 32)), 0.50 * rng.random((32, 32)),
            angles_deg=(0.0, 45.0, 90.0, 135.0),
            azimuth_deg=float(rng.uniform(0.0, 180.0))),
        # keypoints = 画像平面上の (N,2) 点。3-D 台帳の PnP 系はこれを食う。
        # 種が無いと「project_points が同じ連鎖の中で先に引かれた場合だけ」
        # 到達する状態になり、実測で pnp_ransac / dlt_pose / reprojection_error
        # が一度も実行されていなかった
        "keypoints": lambda rng: rng.random((160, 2)) * 32.0,
        # rgbimage = (H,W,3) の色画像。二色性反射モデルは**色の方向**で拡散と
        # 鏡面を分けるので、輝度画像 (image2d) では原理的に成立しない。
        # 種は順方向モデル(既知の法線・アルベド・光源から描く)= 分離の真値が
        # 分かっている画像にする
        "rgbimage": lambda rng: __import__("specularity").dichromatic_render(
            __import__("photometric").surface_normals(
                6.0 * np.exp(-((np.arange(32)[:, None] - 16.0) ** 2
                               + (np.arange(32)[None, :] - 16.0) ** 2) / 200.0)),
            (0.80, 0.55, 0.35), (0.30, 0.20, 1.0),
            specular=0.5, shininess=48.0),
        # video = (T,H,W) のフレーム列。**先頭が時間軸**という約束が voxel との
        # 違いで、種は「既知の振幅・周波数でサブピクセル並進させた格子」=
        # 増幅と変位推定の真値が閉形式で分かるクリップにする
        "video": _motion_clip,
        # score = ピークを持つ 3-D 相関/スコア volume。**カタログのどの op も
        # score を出力しない**ので、種を置かないと `refine_peak_newton` が
        # 構造的に到達不能なまま「発見ゼロ」に数えられる(型到達可能性の
        # 不動点計算で実測: 434 op 中これ 1 件だけが blocked だった)。
        # 一様乱数ではピーク精緻化が意味を持たないので、異方性ガウス山にする
        "score": _score_volume,
        # 光子カウント列。既知距離の dToF 復路 + 背景光を Poisson 標本化した
        # もの = 実データと同じ形と統計(実測 shape (256,)、値域 [0, 303])
        "counts": _photon_counts,
        # SPAD の計数レート列 [Hz]。既定デッドタイム 50 ns の飽和 2e7 Hz の
        # 半分までしか置かないので逆変換が必ず定義域に入る
        "countrate": lambda rng: np.sort(10.0 ** rng.uniform(3.0, 7.0, size=32)),
        # histcube = (H, W, T) の到達時刻ヒストグラム立方体。時間軸が最後で、
        # 128 bin x 200 ps = 一意測距範囲 3.84 m(深度 1-2 m は必ず窓に収まる)
        "histcube": lambda rng: __import__("photoncount").dtof_cube_simulate(
            1.0 + rng.random((16, 16)), bins=128, bin_ps=200.0,
            signal_photons=60.0, ambient_photons=10.0,
            seed=int(rng.integers(0, 1 << 31))),
        # mesh = (V (nv,3) float, F (nf,3) int)。**種が無いと cadmap の 4 op は
        # 「同じ連鎖の中で先に convex_hull / voxel_to_mesh が引かれた場合だけ」
        # 到達する** = keypoints で実測した未到達パターンそのもの。_mesh は
        # 閉凸包 / 直方体 / 開いた平面パッチの 3 種を混ぜる(理由は _mesh の
        # docstring)
        "mesh": _mesh,
        # labels の 2-D 画像。既存 7 producers は 3-D (D,H,W) か 1-D (N,) しか
        # 産まず、**2-D のラベル画像を産む op が 1 つも無い**(実測)ので、
        # 種を置かないと画像ラベルを食う op が永久に fail-closed になる
        "labels": _labels_2d,
    }


#: 必須スカラ引数の名前 → 値サンプラ(署名 introspection で束縛)
PARAM_HINTS = {
    "center": lambda rng: 0.5, "width": lambda rng: 0.5,
    "gamma": lambda rng: float(rng.uniform(0.5, 2.0)),
    "cutoff": lambda rng: 0.1, "low": lambda rng: 0.05, "high": lambda rng: 0.2,
    "sigma": lambda rng: 1.0, "scale": lambda rng: 2.0,
    "angle_deg": lambda rng: float(rng.uniform(-90, 90)),
    "factor": lambda rng: 2, "matrix": lambda rng: np.eye(3),
    "p0": lambda rng: (2.0, 2.0, 2.0), "p1": lambda rng: (13.0, 13.0, 13.0),
    "iterations": lambda rng: 3, "psf": lambda rng: None,   # None -> skip op
    "markers": lambda rng: None,
    "rate": lambda rng: 100.0, "new_rate": lambda rng: 50.0,
    "x": lambda rng: 1.0, "step": lambda rng: 2,
    "radius": lambda rng: 1.5, "ratio": lambda rng: 0.2,
    # 励起サイクル数(パイルアップ補正の分母)。tcspc_simulate 既定の総カウント
    # ~87 に対して十分大きくないと Coates 逆変換が定義域を外れる
    "cycles": lambda rng: 1_000_000,
    # 角度分解能。既定の (5,5) はファザーの 32x32 image2d を割り切れず
    # lf_from_mla が必ず ValueError になるので、割り切れる (4,4) を渡す
    "angular": lambda rng: (4, 4),
    "extent": lambda rng: 1.0, "lo": lambda rng: 0.8, "hi": lambda rng: 1.2,
    "strength": lambda rng: 0.5, "voxel": lambda rng: 0.5,
    "lights": lambda rng: (lambda L: L / np.linalg.norm(L, axis=1, keepdims=True))(
        np.array([[0.3, 0.3, 1.0], [-0.3, 0.3, 1.0], [0.3, -0.3, 1.0],
                  [-0.2, -0.2, 1.0]])),
    "k": lambda rng: 8, "n": lambda rng: 64, "size": lambda rng: 8,

    # --- 幾何・カメラ系(2026-09-01 追加)----------------------------------- #
    # 未到達 op の内訳を実測したところ、100 件中 **70 件が「必須引数を束縛でき
    # ず黙ってスキップ」**だった。記録も残らないので、外からは「頑健だから
    # 発見が無い」のと区別できない ―― カバレッジが数だけだった件と同じ形の
    # 見落としである。頻度順に不足していた引数へ、**プールの寸法と辻褄の合う**
    # 値を与える(points は [0,10]^3、image2d は 32x32、voxel は 16^3)。
    #
    # これは既に到達している op の挙動を変えない: 名前ヒントは**必須引数**に
    # しか効かず、これまで該当 op は丸ごとスキップされていたので、変わるのは
    # 「一度も実行されない」から「実行される」への一方向だけである。
    "K": lambda rng: np.array([[32.0, 0.0, 16.0],
                               [0.0, 32.0, 16.0],
                               [0.0, 0.0, 1.0]]),          # 32x32 画像の内部行列
    "K1": lambda rng: np.array([[32.0, 0.0, 16.0], [0.0, 32.0, 16.0], [0.0, 0.0, 1.0]]),
    "K2": lambda rng: np.array([[32.0, 0.0, 16.0], [0.0, 32.0, 16.0], [0.0, 0.0, 1.0]]),
    "fx": lambda rng: 32.0, "fy": lambda rng: 32.0,
    "cx": lambda rng: 16.0, "cy": lambda rng: 16.0,
    "R": lambda rng: np.eye(3), "t": lambda rng: np.array([0.0, 0.0, 12.0]),
    # 多視点(carve / visual_hull / fuse)。3 視点を Z 軸まわりに配置する
    "Ks": lambda rng: [np.array([[32.0, 0.0, 16.0], [0.0, 32.0, 16.0],
                                 [0.0, 0.0, 1.0]])] * 3,
    "Rs": lambda rng: [np.eye(3)] * 3,
    "ts": lambda rng: [np.array([0.0, 0.0, 12.0 + 2.0 * i]) for i in range(3)],
    # RANSAC の内れ値許容。points プールは [0,10]^3 なのでその 2% 相当
    "thresh": lambda rng: 0.2,
    # voxel 化の対象領域と解像度。points プールを丸ごと含む箱にする
    "bounds": lambda rng: (0.0, 0.0, 0.0, 10.0, 10.0, 10.0),
    "res": lambda rng: 16,
    "alpha": lambda rng: 1.0,
    # 3 点から線・面を作る系の 2 番目・3 番目の点(1 番目は型プールから来る)
    "b": lambda rng: np.array([1.0, 0.0, 0.0]),
    "c": lambda rng: np.array([0.0, 1.0, 0.0]),
    # 曲面フィットの座標軸(x は型プールから来る)
    "y": lambda rng: np.linspace(0.0, 1.0, 64),
    "z": lambda rng: np.linspace(0.0, 1.0, 64),
    "a": lambda rng: 1.0,
    # 時間軸の単位。T=32 / fps=32 なので 4 Hz はちょうど bin に乗り、
    # 3-5 Hz の通過帯域が空にならない
    "fps": lambda rng: 32.0, "f_lo": lambda rng: 3.0, "f_hi": lambda rng: 5.0,
    # 回転数。既定 rate=100 Hz・samples_per_rev=64 では 60 rpm が 32 Hz で
    # Nyquist 50 Hz に収まる。1800 rpm だとエイリアス検査で毎回弾かれ、
    # 次数比分析 2 op が一度も実行されない
    "rpm": lambda rng: 60.0,
    # 四元数の積は**非可換**なので、左右は既定に頼らせず必ず引く
    "side": lambda rng: "left" if rng.random() < 0.5 else "right",
    "axis_rgb": lambda rng: (lambda v: v / np.linalg.norm(v))(
        rng.standard_normal(3)),
    "direction_rgb": lambda rng: (lambda v: v / np.linalg.norm(v))(
        rng.standard_normal(3)),
    "angle_rad": lambda rng: float(rng.uniform(-np.pi, np.pi)),
}

#: シグネチャが「型リスト=先頭位置引数」の素直な形でない op の専用ビルダー。
#: pool と rng から (args, kwargs) を組み立てる(None を返すとこの回スキップ)
def _b_fuse(pool, rng):
    pts = pool.get("points")
    if not pts:
        return None
    return ([(pts[int(rng.integers(len(pts)))], "points", {})],), {"size": 8}


def _b_register_cross(pool, rng):
    cands = [p for p in pool.get("points", []) if _is_pts(p)]
    if not cands:
        return None
    a = cands[int(rng.integers(len(cands)))]
    b = a + rng.standard_normal(a.shape) * 0.1
    return (a, "points", b, "points"), {"method": "icp"}


def _b_abcd(pool, rng):
    """ABCD 素子リスト。半分は妥当な系(実経路を通す)、半分は pool の table
    (dict や他 op の返り)= 敵対入力で fail-closed を叩く。"""
    if rng.random() < 0.5:
        tables = pool.get("table") or []
        if tables:
            return (tables[int(rng.integers(len(tables)))],), {}
    kinds = [("free", float(rng.uniform(0.0, 200.0))),
             ("lens", float(rng.uniform(10.0, 200.0)) * rng.choice([-1.0, 1.0])),
             ("mirror", float(rng.uniform(10.0, 500.0))),
             ("interface", 1.0, float(rng.uniform(1.1, 2.0))),
             ("curved", 1.0, float(rng.uniform(1.1, 2.0)),
              float(rng.uniform(10.0, 500.0)))]
    k = int(rng.integers(1, 4))
    return ([kinds[int(rng.integers(len(kinds)))] for _ in range(k)],), {}


def _b_wavefront(pool, rng):
    """Zernike 係数 dict。半分は妥当な波面(match3d.fit_zernike と同形式)、
    半分は pool の table = 敵対入力。"""
    if rng.random() < 0.5:
        tables = pool.get("table") or []
        if tables:
            return (tables[int(rng.integers(len(tables)))],), {}
    idx = [(0, 0), (2, 0), (2, 2), (2, -2), (3, 1), (4, 0)]
    k = int(rng.integers(1, len(idx) + 1))
    return ({idx[i]: float(rng.normal(0.0, 0.05)) for i in range(k)},), {}


def _b_shaped(kind, shape, make, *extra):
    """先頭引数が **形の決まった行列**の op 用 builder を作る。

    光学の abcd_trace(2x2)/ jones_apply(2x2)/ mueller_apply(4x4)は、
    pool の一様抽選では実経路をまず通らない: 目録 400 op × 連鎖長 8 では
    「生成元の op(abcd_matrix / jones_element / mueller_element)と消費側が
    同一連鎖に、しかもこの順で入る」確率が ~0.03% しかなく、800 連鎖でも
    happy path 0 回・CONTRACT だけ、と実測した。そこで半分は *make* が作る
    妥当な行列(実経路)、半分は pool の一様抽選(敵対入力 → fail-closed)。
    ``_b_abcd`` / ``_b_wavefront`` と同じ「半分は妥当・半分は敵対」方針。"""
    def build(pool, rng):
        m = None
        if rng.random() < 0.5:
            fit = [c for c in (pool.get(kind) or [])
                   if isinstance(c, np.ndarray) and c.shape == shape]
            m = fit[int(rng.integers(len(fit)))] if fit else make(rng)
        else:
            cands = pool.get(kind) or []
            if cands:
                m = cands[int(rng.integers(len(cands)))]
        if m is None:
            return None
        args = [m]
        for t in extra:
            vals = pool.get(t) or []
            if not vals:
                return None
            args.append(vals[int(rng.integers(len(vals)))])
        return tuple(args), {}
    return build


def _mk_abcd(rng):
    import optics
    return optics.abcd_matrix([("free", float(rng.uniform(0.0, 200.0))),
                               ("lens", float(rng.uniform(10.0, 200.0)))])


def _mk_jones(rng):
    import optics
    return optics.jones_element(str(rng.choice(list(optics.JONES_KINDS))),
                                float(rng.uniform(-90.0, 90.0)),
                                float(rng.uniform(0.0, 360.0)))


def _mk_mueller(rng):
    import optics
    return optics.mueller_element(str(rng.choice(list(optics.MUELLER_KINDS))),
                                  float(rng.uniform(-90.0, 90.0)),
                                  float(rng.uniform(0.0, 360.0)))


def _b_dichromatic_planes(pool, rng):
    """(rgbimage, labels) for illuminant_from_dichromatic_planes。

    半分は本物の多材質シーンを組んで実経路を通し、半分は pool の生の labels を
    渡して fail-closed を叩く(_b_shaped と同じ「半分は妥当・半分は敵対」方針)。
    単一材質の rgbimage 生成器をそのまま渡すと二色性平面が 1 枚しか立たず、
    この op は毎回 CONTRACT になって一度も実行されない。
    """
    imgs = pool.get("rgbimage") or []
    if not imgs:
        return None
    img = imgs[int(rng.integers(len(imgs)))]
    h, w = img.shape[:2]
    if h < 6 or w < 6 or rng.random() < 0.5:
        labs = pool.get("labels") or []
        if not labs:
            return None
        return (img, labs[int(rng.integers(len(labs)))]), {}
    gamma = np.ones(3) / np.sqrt(3.0)
    m_s = img @ gamma
    m_s = np.clip(m_s - np.percentile(m_s, 70.0), 0.0, None)
    shade = np.linalg.norm(img - m_s[..., None] * gamma, axis=-1)
    labels = np.zeros((h, w), dtype=np.int32)
    labels[:, w // 3:2 * w // 3] = 1
    labels[:, 2 * w // 3:] = 2
    multi = np.zeros((h, w, 3))
    for k, c in enumerate(((0.80, 0.55, 0.35), (0.25, 0.60, 0.75),
                           (0.55, 0.30, 0.70))):
        im = np.asarray(c) * shade[..., None] + m_s[..., None] * gamma
        multi[labels == k] = im[labels == k]
    return (multi, labels), {}


def _b_steerable(pool, rng):
    """complex_steerable_reconstruct の入力を pool の table 一様抽選に任せると、
    他族の dict/list が来て毎回 CONTRACT になり実経路を一度も通らない。
    半分は image2d プールから作った**本物の分解**、半分は pool の table を素で
    渡す(敵対入力 → fail-closed)。
    """
    import motionmag                                     # noqa: PLC0415
    if rng.random() < 0.5:
        imgs = pool.get("image2d") or []
        if not imgs:
            return None
        img = imgs[int(rng.integers(len(imgs)))]
        return (motionmag.complex_steerable_decompose(
            img, scales=int(rng.integers(1, 5)),
            orientations=int(rng.integers(1, 5))),), {}
    tabs = pool.get("table") or []
    if not tabs:
        return None
    return (tabs[int(rng.integers(len(tabs)))],), {}


#: op 固有の引数(名前が汎用ヒントと衝突する/型が op ごとに違うもの)。
#: **既定値つきの引数もここに書けば上書きできる**(名前レベルの PARAM_HINTS は
#: 必須引数にしか効かない — 詳細は `_bind_args`)。


def _b_mesh_split(*extra):
    """``mesh`` を **(V, F) の 2 位置引数**へ割る op 用 builder を作る。

    ファザーは 1 入力種別につき 1 位置引数しか割り当てないので、
    ``mesh_to_voxel(vertices, faces, size, ...)`` のように (V, F) を 2 つに割る
    op は **2 番目の ``faces`` が「束縛できない必須引数」として残り、丸ごと
    スキップされる**。記録も残らないので、外からは「頑健だから発見が無い」の
    と区別できない ―― 引数を束縛できず 70 op が黙って飛ばされていた 2026-09-01
    の件と同じ形である。実測(2026-09-02、mesh の種を入れた直後の 1500 連鎖):
    mesh を食う 19 op のうち **この形の 8 op が全部未到達**だった
    (mesh_to_voxel / mesh_to_points / ambient_occlusion / cast_shadow /
    supersample_mesh / render_beauty / geodesic_mesh / decimate_qem)。

    *extra* は V, F の後に続く**型プール由来**の引数(cast_shadow の光源
    ``vector`` など)。残るスカラ必須引数(``size`` / ``target_faces`` …)は
    **list を返して通常経路の :func:`_bind_args` に任せる** — ここで自前に
    値を作ると PARAM_HINTS と二重管理になる。
    """
    def build(pool, rng):
        meshes = [m for m in (pool.get("mesh") or [])
                  if isinstance(m, (tuple, list)) and len(m) >= 2]
        if not meshes:
            return None
        m = meshes[int(rng.integers(len(meshes)))]
        args = [m[0], m[1]]
        for t in extra:
            vals = pool.get(t) or []
            if not vals:
                return None
            args.append(vals[int(rng.integers(len(vals)))])
        return args                      # list = 「data 引数だけ」の合図
    return build


def _b_vectors(n):
    """先頭 *n* 個の位置引数を **長さ 3 のベクトル**で埋める builder を作る。

    解析幾何の 11 op(``line_from_2points`` / ``intersect_planes`` /
    ``angle_between_lines`` / ``distance_point_line`` …)は引数が全部
    「点 or 方向 or 法線」の 3-ベクトルなのに、台帳の ``in`` は
    ``points`` / ``primitive`` と宣言されている。ファザーは 1 入力種別につき
    1 位置引数しか割り当てないので、**2 つ目以降が「束縛できない必須引数」として
    残り丸ごとスキップ**され、実測(2026-09-02, 1500 連鎖)で 11 op すべてが
    未到達だった ― ``mesh`` を (V,F) の 2 引数へ割る 8 op と同じ形の穴である。
    しかも 1 つ目には ``points`` プールの (160,3) や ``primitive`` プールの dict が
    渡るので、仮に束縛できても毎回 fail-closed するだけで実経路は通らない。

    台帳の ``in`` 宣言そのものを直すのが本筋だが、sort の候補リスト長が変わると
    既存 champion を黙って書き換えてしまう(docs/WAVE0_STABLE_SLOTS.md、
    tests/test_ops3d_ledger.py の KNOWN_LEDGER_GAPS["sphere_sdf"] が同じ理由で
    見送っている)。よってここでは **ファザー側だけ**で正しい形を組む。

    ``_b_shaped`` と同じ「半分は妥当・半分は敵対」方針: 半分は独立な単位ベクトル
    (退化しない実経路 = 交線も二面角も定義される)、半分は ``vector`` プールの
    一様抽選(同じベクトルが 2 度引かれれば平行・退化の分岐を踏む)。
    """
    def build(pool, rng):
        if rng.random() < 0.5:
            out = []
            for _ in range(n):
                v = rng.standard_normal(3)
                nv = float(np.linalg.norm(v))
                out.append(v / nv if nv > 0 else np.array([0.0, 0.0, 1.0]))
            return out
        vs = [v for v in (pool.get("vector") or [])
              if tuple(getattr(v, "shape", ())) == (3,)]
        if not vs:
            return None
        idx = (list(rng.permutation(len(vs))[:n]) if len(vs) >= n
               else [int(i) for i in rng.integers(len(vs), size=n)])
        return [vs[int(i)] for i in idx]
    return build


OP_ARG_BUILDERS = {
    "abcd_matrix": _b_abcd,
    "wavefront_stats": _b_wavefront,
    "abcd_trace": _b_shaped("matrix", (2, 2), _mk_abcd),
    "jones_apply": _b_shaped("cimage", (2, 2), _mk_jones, "jones"),
    "mueller_apply": _b_shaped("matrix", (4, 4), _mk_mueller, "stokes"),
    "fuse_to_voxel": _b_fuse,
    "register_cross": _b_register_cross,
    "to_points": lambda pool, rng: ((pool["points"][0], "points"), {})
    if pool.get("points") else None,
    "illuminant_from_dichromatic_planes": _b_dichromatic_planes,
    "complex_steerable_reconstruct": _b_steerable,
    # (V, F) を 2 位置引数へ割る 8 op(理由と実測は _b_mesh_split の docstring)
    "mesh_to_voxel": _b_mesh_split(),
    "mesh_to_points": _b_mesh_split(),
    "ambient_occlusion": _b_mesh_split(),
    "supersample_mesh": _b_mesh_split(),
    "render_beauty": _b_mesh_split(),
    "geodesic_mesh": _b_mesh_split(),
    "decimate_qem": _b_mesh_split(),
    "cast_shadow": _b_mesh_split("vector"),      # (V, F, light)
    # 3-ベクトルだけを取る解析幾何 11 op(理由と実測は _b_vectors の docstring)。
    # これを入れるまで 11 op すべてが未到達で、`primitive` / `position` の
    # 述語がこの一族に一度も当たっていなかった
    "line_from_2points": _b_vectors(2),          # (a, b)
    "plane_from_3points": _b_vectors(3),         # (a, b, c)
    "angle_3points": _b_vectors(3),              # (a, b, c)
    "intersect_planes": _b_vectors(4),           # (p1, n1, p2, n2)
    "intersect_line_plane": _b_vectors(4),       # (line_pt, d, plane_pt, n)
    "angle_between_lines": _b_vectors(2),        # (d1, d2)
    "angle_between_planes": _b_vectors(2),       # (n1, n2)
    "angle_line_plane": _b_vectors(2),           # (d, n)
    "distance_point_plane": _b_vectors(3),       # (p, plane_pt, n)
    "distance_point_line": _b_vectors(3),        # (p, line_pt, d)
    "distance_line_line": _b_vectors(4),         # (p1, d1, p2, d2)
}

OP_PARAM_HINTS = {
    # 既定 (5,5) はプールの 32x32 を割り切れず毎回 ValueError になり、この op が
    # 一度も実行されないまま「発見ゼロ」に見えていた。32 を割り切る (4,4) にする
    ("lf_from_mla", "angular"): lambda rng: (4, 4),
    # 描画系の size は (H, W)。名前ヒントの "size"(=8、近傍サイズ等のスカラ)を
    # そのまま渡すと生の TypeError になり、**op の契約の穴なのか入力が悪いのか**
    # 区別がつかなくなる。まず正しい形を渡してから判定する
    ("render_point_depth", "size"): lambda rng: (32, 32),
    ("synthesize_silhouette", "size"): lambda rng: (32, 32),
    # PARAM_HINTS["alpha"] は 1.0(= 恒等利得)なので、そのままだと
    # motion_magnify は毎回実行されるのに**一度も増幅しない**。狙いは
    # 増幅経路を通すことなので op 名で上書きする
    ("motion_magnify", "alpha"): lambda rng: 2.0,
    # bounds という 1 つの名前に 3 通りの形が要求されている(平坦 6-tuple /
    # ((min,max)x3) / (lo(3,), hi(3,)))。名前ヒントは平坦形のままにして、
    # 別形を要求する op だけ狙い撃つ ― さもないと毎回 ValueError で
    # **一度も実行されない**まま「発見ゼロ」に数えられる
    ("occupancy_grid", "bounds"): lambda rng: ((0.0, 10.0), (0.0, 10.0), (0.0, 10.0)),
    # sphere_sdf の R は**回転行列ではなく半径**。名前ヒントの np.eye(3) が
    # そのまま渡ると生の TypeError になる(名前の衝突であって op の罪ではない)
    ("sphere_sdf", "R"): lambda rng: 2.0,
    ("quat_color_filter", "mode"): lambda rng: "remove" if rng.random() < 0.5 else "keep",
    # PARAM_HINTS["alpha"] は 1.0(恒等利得)。motion_magnify と同じ理由で上書き
    ("riesz_motion_magnify", "alpha"): lambda rng: 2.0,
    # 既定 n_antennas=1 だとプールに 1 素子の立方体が入り、ビームフォーミング
    # 2 op が毎回「開口が無い」で弾かれて一度も実行されない
    ("fmcw_beat_simulate", "n_antennas"): lambda rng: 4,
    # 生成器の走査範囲と辻褄を合わせる(既定 2.8 でも動くが端切れが増える)
    ("csi_stack_simulate", "envelope_fwhm_um"): lambda rng: 2.8258,
    ("vol_richardson_lucy", "psf"): lambda rng: __import__("volrestore").vol_gaussian_psf(1.0),
    ("cx_wiener_deconvolve", "psf"): lambda rng: (lambda k: k / k.sum())(
        np.outer(*(np.exp(-np.linspace(-2, 2, 5) ** 2),) * 2)),
    ("cx_apply_transfer_function", "H"): lambda rng: rng.random((32, 32)),
    # tier2 複素解析: w = 輪郭の内側にありそうな点(外・線上なら fail-closed
    # の CONTRACT が出るのが正しい)。Möbius の 4 係数は ad-bc≠0 の実例
    ("cplx_cauchy_value", "w"): lambda rng: 0.1 + 0.1j,
    ("cplx_mobius", "a"): lambda rng: 1.0,
    ("cplx_mobius", "b"): lambda rng: -1j,
    ("cplx_mobius", "c"): lambda rng: 1.0,
    ("cplx_mobius", "d"): lambda rng: 1j,
    # mesh を (V, F) に割る 8 op のうち、残る必須引数がこの 2 つ。名前
    # ("target_faces" / "source")は他の op と衝突しないが**汎用の意味も無い**
    # ので、名前ヒントに置かず op 名で狙い撃つ。8 は種の最小メッシュ(平面
    # パッチ 2 面)より大きいが、実測でこの op は目標超過を例外にせず現状を
    # 返す(nf=2 / target=8 で (4,3),(2,3) が返る)ので毎回 CONTRACT にはならない
    ("decimate_qem", "target_faces"): lambda rng: 8,
    # 測地距離の起点は頂点添字。種の最小メッシュでも 0 は必ず存在する
    ("geodesic_mesh", "source"): lambda rng: 0,
}

#: 文書化済みの非有限を返す op(光学)。docstring が契約として明記している:
#: depth_of_field は過焦点距離以遠で far/depth = inf(それが過焦点距離の定義)、
#: gaussian_beam はウエストで wavefront_radius = inf(平面波面の曲率半径)。
#: どちらも有限の逆数(curvature_per_mm)や bool を併せて返す。
NONFINITE_BY_CONTRACT_OPTICS = {"depth_of_field", "gaussian_beam"}

#: 文書化済みの非有限を返す op(cadmap)。**「当たらなかった」を NaN で表すのが
#: 契約**で、最寄りの面へ丸めないための設計そのもの(丸めると「背景に載っていた
#: 欠陥」が「面 17 の欠陥」に化ける)。docstring で明記されているもの:
#:   * cad_pixel_to_surface — miss の bary / point / depth / normal が NaN
#:     (face_id = -1、hit = False が併せて返るので判別できる)。
#:   * cad_defect_to_cad — 当たり 0 の領域の centroid / depth_mean が NaN
#:     (area = 0.0, hit_fraction = 0.0 で**消さずに**残す)。
#: cad_surface_to_pixel / cad_visible_faces は非有限を返さない(実測)ので入れない
#: — 入れると本物の非有限が黙って見逃される。
NONFINITE_BY_CONTRACT_CADMAP = {"cad_pixel_to_surface", "cad_defect_to_cad"}

#: 出力を pool 型へ合わせる梱包アダプタ。基本はレジストリの RESULT_ADAPTERS
#: (型忠実の一級メタデータ)に委譲し、ファザー固有の追加だけここに置く
def _registry_adapters():
    import ops1d
    import ops3d
    import opsmath
    d = dict(ops3d.RESULT_ADAPTERS)
    d.update(ops1d.RESULT_ADAPTERS)
    d.update(opsmath.RESULT_ADAPTERS)
    import opsoptics
    d.update(opsoptics.RESULT_ADAPTERS)
    import opslightfield
    d.update(opslightfield.RESULT_ADAPTERS)
    import opsphoton
    d.update(opsphoton.RESULT_ADAPTERS)     # 現状は空(全 op が宣言型を素で返す)
    import opsspecular
    d.update(opsspecular.RESULT_ADAPTERS)
    import opsmotionmag
    d.update(opsmotionmag.RESULT_ADAPTERS)  # 意図的に空(下の理由を参照)
    import opsquat
    d.update(opsquat.RESULT_ADAPTERS)       # 空: 19 op とも宣言型を素で返す
    import opsrangedoppler
    d.update(opsrangedoppler.RESULT_ADAPTERS)   # 空(意図的)
    import opsacoustics
    d.update(opsacoustics.RESULT_ADAPTERS)      # 空(意図的)
    import opsinterferometry
    d.update(opsinterferometry.RESULT_ADAPTERS)  # 空(意図的)
    import opscadmap
    d.update(opscadmap.RESULT_ADAPTERS)          # 空(意図的): 素の返りが宣言型
    d["vol_rle_components"] = lambda r: r[0] if r else None
    d["label_components"] = lambda r: r[0] if isinstance(r, tuple) else r
    return d


ADAPTERS = _registry_adapters()


def catalog():
    """(name, module, in_types, out_type, fn) を ops3d + ops1d から集める。"""
    import ops1d
    import ops3d
    ops = []
    for n, m in ops3d.OPS3D.items():
        if m["func"] is not None:
            ops.append((n, "3d", list(m["in"]), m["out"], m["func"]))
    for n, m in ops1d.OPS1D.items():
        if m["func"] is not None and m["category"] != "io":   # ファイル I/O は除外
            ops.append((n, "1d", list(m["in"]), m["out"], m["func"]))
    # complexops = HALCON の complex 画像形式(2-D)。image2d <-> cimage の橋
    import complexops as cx
    for name, ins, out in [
        ("cx_fft", ["image2d"], "cimage"),
        ("cx_ifft", ["cimage"], "image2d"),
        ("cx_magnitude", ["cimage"], "image2d"),
        ("cx_phase", ["cimage"], "image2d"),
        ("cx_real", ["cimage"], "image2d"),
        ("cx_imag", ["cimage"], "image2d"),
        ("cx_log_magnitude", ["cimage"], "image2d"),
        ("cx_from_mag_phase", ["image2d", "image2d"], "cimage"),
        ("phase_unwrap", ["image2d"], "image2d"),
        ("cx_apply_transfer_function", ["cimage"], "cimage"),
        ("cx_bandpass", ["image2d"], "image2d"),
        ("cx_wiener_deconvolve", ["image2d"], "image2d"),
    ]:
        ops.append((name, "2d", ins, out, getattr(cx, name)))
    # 数学ファミリ(opsmath 台帳)。adapter 層を持たない=素の返りが宣言型で
    # あることを TYPEMISS 検査がそのまま機械検証する
    import opsmath
    for n, m in opsmath.OPSMATH.items():
        if m["func"] is not None:
            ops.append((n, "math", list(m["in"]), m["out"], m["func"]))
    # 光学ファミリ(opsoptics 台帳)。opsmath と同じく adapter 層を持たない=
    # 素の返りが宣言型であることを TYPEMISS 検査がそのまま機械検証する
    import opsoptics
    for n, m in opsoptics.OPSOPTICS.items():
        if m["func"] is not None:
            ops.append((n, "optics", list(m["in"]), m["out"], m["func"]))
    # ライトフィールドファミリ(opslightfield 台帳)。4-D (V,U,H,W) の新語彙
    # `lightfield` を持ち込む唯一の族で、`images` へ潰すと「どの視点か」が
    # 消えて refocus も EPI も定義できなくなるため型を分けている
    import opslightfield
    for n, m in opslightfield.OPSLIGHTFIELD.items():
        if m["func"] is not None:
            ops.append((n, "lightfield", list(m["in"]), m["out"], m["func"]))
    # 光子計数・時間分解(opsphoton 台帳)。新語彙 `histcube` は (H,W,T) で
    # **時間軸が最後**。voxel と ndim==3 の構造は同じだが軸の意味が違い、
    # (D,H,W) を渡すと例外ではなく「もっともらしく間違った深度」が出るため
    # 型を分ける(pointmap / normalmap を分けたのと同じ判断)
    import opsphoton
    for n, m in opsphoton.OPSPHOTON.items():
        if m["func"] is not None:
            ops.append((n, "photon", list(m["in"]), m["out"], m["func"]))
    # 鏡面反射の分離 / 反射モデル(opsspecular 台帳)。新語彙 `rgbimage` は
    # (H,W,3) で pointmap / normalmap と**構造は同じだが意味が違う**。実測で
    # normalmap を分離 op に渡すと例外なく「分離結果」が返ることを確認済み
    import opsspecular
    for n, m in opsspecular.OPSSPECULAR.items():
        if m["func"] is not None:
            ops.append((n, "specular", list(m["in"]), m["out"], m["func"]))
    # 位相ベースのモーション増幅(opsmotionmag 台帳)。新語彙 `video` は (T,H,W)。
    # voxel と ndim は同じだが**先頭が時間軸**で、voxel を渡しても例外も NaN も
    # 出ないまま z を時間として読む(実測確認済み)= histcube を voxel から
    # 分けたのと同じ判断
    import opsmotionmag
    for n, m in opsmotionmag.OPSMOTIONMAG.items():
        if m["func"] is not None:
            ops.append((n, "motionmag", list(m["in"]), m["out"], m["func"]))
    # 四元数画像(opsquat 台帳)。新語彙 `qimage` は (H,W,4)。色の四元数と
    # モノジェニック信号という**意味の違う 2 種類が同じ形**なので、生成器は
    # 必ず両方を出す(片方だけだと相手側の op が永久に fail-closed になる)
    import opsquat
    for n, m in opsquat.OPSQUAT.items():
        if m["func"] is not None:
            ops.append((n, "quat", list(m["in"]), m["out"], m["func"]))
    # FMCW レンジ-ドップラー(opsrangedoppler 台帳)。新語彙 `beatcube` は
    # (アンテナ, チャープ, サンプル) の**複素** 3-D。histcube (非負の光子カウント)
    # と形は一致するが dtype だけが違い、**キャスト 1 回で相互に通ってしまう**
    # (実測: np.abs(beatcube) を dtof_cube_depth に渡すと例外なく深度が返り、
    # histcube.astype(complex) を range_doppler_map に渡すとマップが返る)ので
    # 宣言型のレベルで分ける
    import opsrangedoppler
    for n, m in opsrangedoppler.OPSRANGEDOPPLER.items():
        if m["func"] is not None:
            ops.append((n, "rangedoppler", list(m["in"]), m["out"], m["func"]))
    # 音響・振動診断(opsacoustics 台帳)。**新しい型語彙を作らない**判断:
    # 任意の実 1-D 配列は本当に妥当な音響信号なので、専用型を宣言しても嘘に
    # ならない代わりに守るものが無い(counts と違って破る制約が無い)。危険は
    # 配列でなく **rate スカラ**の側にある — 同じ録音を 25600 でなく 48000 Hz
    # として読むと欠陥周波数が 107 Hz でなく 200.625 Hz と報告され、例外は
    # 出ない。よって防御はスカラ検証に置き、既存 dsp / funct1d との接続を保つ
    import opsacoustics
    for n, m in opsacoustics.OPSACOUSTICS.items():
        if m["func"] is not None:
            ops.append((n, "acoustics", list(m["in"]), m["out"], m["func"]))
    # コヒーレンス走査干渉(opsinterferometry 台帳)。型語彙 2 つ:
    # `zscan` = (Z,H,W) の走査スタック(**走査軸が先頭**)、`sweep` = 1-D の
    # 非負掃引。zscan を分けたのは実測で**片側だけが黙って通る**から —
    # zscan を video / histcube へ渡すと 4 op すべてが例外も NaN も出さずに
    # 「増幅結果」「深度」を返すが、逆向きは fail-closed する。実行時検査に
    # 頼れないので宣言型で分ける
    import opsinterferometry
    for n, m in opsinterferometry.OPSINTERFEROMETRY.items():
        if m["func"] is not None:
            ops.append((n, "interferometry", list(m["in"]), m["out"], m["func"]))
    # 欠陥 → CAD 面の逆写像(opscadmap 台帳)。**新しい型語彙を 1 つも作らない**
    # 判断: 4 op の入出力は既存の mesh / keypoints / points / labels / table /
    # indices にそのまま収まる。代わりにこの族が持ち込んだのは
    # **`mesh` 型の述語と種**で、2026-09-02 まで mesh は TYPE_CHECKS に述語が
    # 無く(宣言 out=mesh の op が何を返しても TYPEMISS にならない穴)、
    # make_generators にも種が無かった(実測。dead な _mesh ヘルパだけがあった)。
    # mesh を 1 引数で受ける形にしてあるので、`mesh_to_voxel(vertices, faces)`
    # のように (V,F) を 2 位置引数へ割る既存 op が「2 つ目が束縛できず永久に
    # スキップ」になる罠は踏まない。
    import opscadmap
    for n, m in opscadmap.OPSCADMAP.items():
        if m["func"] is not None:
            ops.append((n, "cadmap", list(m["in"]), m["out"], m["func"]))
    return ops


def _bind_args(op_name, fn, data_args, rng):
    """先頭の必須位置引数へ data_args を割り当て、残る必須引数を op 固有 →
    名前ヒントの順で束縛。束縛できない必須引数が残れば None(スキップ)。"""
    import inspect
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return list(data_args), {}
    args = list(data_args)
    kwargs = {}
    params = [p for p in sig.parameters.values()
              if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
    for p in params[len(args):]:
        if p.default is not inspect.Parameter.empty:
            # 既定値つきの引数は原則そのまま使う。ただし **op 固有ヒントがあれば
            # 上書きする**。既定値がプールの固定サイズと噛み合わない op は、
            # 上書きできないと毎回 ValueError になって「一度も実行されない」まま
            # 発見ゼロに見える(実測: lf_from_mla の既定 angular=(5,5) は 32x32 を
            # 割り切れず、1200 連鎖で覆われた 16/17 の残り 1 がこれだった)。
            # 名前レベルの PARAM_HINTS は既存 op の挙動を一斉に変えてしまうので
            # ここでは効かせない — 上書きは op 名で狙い撃ちしたものに限る。
            hint = OP_PARAM_HINTS.get((op_name, p.name))
            if hint is not None:
                val = hint(rng)
                if val is not None:
                    kwargs[p.name] = val
            continue
        hint = OP_PARAM_HINTS.get((op_name, p.name)) or PARAM_HINTS.get(p.name)
        if hint is None:
            return None
        val = hint(rng)
        if val is None:
            return None
        kwargs[p.name] = val
    return args, kwargs


#: pool 投入前の型検証(catalog の out 申告と実際の返りの乖離 = TYPEMISS を検出)
def _is_pts(v):
    return isinstance(v, np.ndarray) and v.ndim == 2 and v.shape[1] == 3


def _shape(v):
    """*v* の形。**型ではなく形で判定する**ための共通入口。

    GPU backend を持つ登録 op は ``torch.Tensor`` を返すのがこの repo の約束
    なので、``isinstance(np.ndarray)`` で書くと**述語の側が間違う**
    (`pose` の述語で実際に 6 件中 4 件を誤検出した — TYPE_CHECKS["pose"] の
    コメント参照)。配列でないものは ``()`` を返すので、
    ``_shape(v) == (3,)`` のように長さと寸法だけを見れば backend を跨げる。
    """
    s = getattr(v, "shape", ())
    try:
        return tuple(s)
    except TypeError:                       # shape が呼べない別物(念のため)
        return ()


def _is_scalar(v):
    """実スカラ(bool を除く)。`measurement` の述語と同じ判定を共有する。"""
    return isinstance(v, (int, float, np.floating, np.integer)) \
        and not isinstance(v, bool)


def _is_seq(v, *lengths):
    """タプル/リストで、長さが *lengths* のどれか(空指定なら長さを問わない)。"""
    return isinstance(v, (tuple, list)) and (not lengths or len(v) in lengths)


TYPE_CHECKS = {
    "points": _is_pts,
    "normals": _is_pts,
    "keypoints": lambda v: _is_pts(v) or (isinstance(v, np.ndarray) and v.ndim == 2),
    "voxel": lambda v: isinstance(v, np.ndarray) and v.ndim == 3,
    "sdf": lambda v: isinstance(v, np.ndarray) and v.ndim == 3,
    "labels": lambda v: isinstance(v, np.ndarray) and v.ndim >= 1,
    "image2d": lambda v: isinstance(v, np.ndarray) and v.ndim == 2,
    "depth": lambda v: isinstance(v, np.ndarray) and v.ndim == 2,
    "cimage": lambda v: isinstance(v, np.ndarray) and v.ndim == 2 and v.dtype.kind == "c",
    "signal": lambda v: isinstance(v, np.ndarray) and v.ndim == 1,
    # measurement = スカラのみ(tuple/dict がここに紛れると下流 op が生 TypeError
    # で落ちる — 第 3 波でプール汚染として実測)
    "measurement": lambda v: isinstance(v, (int, float, np.floating, np.integer)),
    "indices": lambda v: isinstance(v, np.ndarray) and v.ndim == 1,
    "table": lambda v: isinstance(v, (list, dict)),
    "rle_region": lambda v: type(v).__name__ == "VolRLE",
    "pointmap": lambda v: isinstance(v, np.ndarray) and v.ndim == 3 and v.shape[2] == 3,
    "normalmap": lambda v: isinstance(v, np.ndarray) and v.ndim == 3 and v.shape[2] == 3,
    "images": lambda v: isinstance(v, (list, tuple)) and all(
        isinstance(x, np.ndarray) and x.ndim == 2 for x in v),
    "vector": lambda v: isinstance(v, np.ndarray) and v.shape == (3,),
    "pairs": lambda v: True,
    "matrix": lambda v: isinstance(v, np.ndarray) and v.ndim == 2,
    "roots": lambda v: isinstance(v, np.ndarray) and v.ndim == 1
    and v.dtype.kind == "c",
    # cpoints = 複素 1-D の**順序つき**点列(閉曲線)。roots と同じ形だが別プール:
    # roots は順序に意味の無い解集合で、周回積分・巻き数は順序と閉性が答えそのもの
    "cpoints": lambda v: isinstance(v, np.ndarray) and v.ndim == 1
    and v.dtype.kind == "c",
    # cscalar = 複素スカラ(∮f dz / f(w) / 留数)。measurement(実スカラのみ)へ
    # 混ぜると下流の実数 op が生 TypeError で落ちるため型を分ける
    "cscalar": lambda v: isinstance(v, complex) and not isinstance(v, np.ndarray),
    # lightfield = 4-D (V, U, H, W)。角度 2 軸 × 空間 2 軸
    "lightfield": lambda v: isinstance(v, np.ndarray) and v.ndim == 4,
    # pose = 剛体変換。**述語が無いあいだ 3 通りの意味が同居していた**
    # (実測 2026-09-01: (R,t,…) タプル 10 op / dict 3 op / 4x4 同次行列を
    # 要求する消費側)。多数派かつ生成器が出す形である「先頭 2 要素が
    # R(3,3) と t(3,)」を正典とし、それ以外は TYPEMISS として顕在化させる。
    # dict を返すのが正直な op は RESULT_ADAPTERS で (R,t) を取り出すか、
    # 中身が姿勢でないなら table を名乗るのが筋(refine_lm の返りは
    # {cost,gain,iters,pos} で R も t も持っていなかった)
    # 判定は **型ではなく形**で行う: GPU backend を持つ登録 op は torch.Tensor を
    # 返すのがこの repo の約束で(`backends_typed._coerce` が numpy へ落とす)、
    # `isinstance(..., np.ndarray)` で書くと**述語の側が間違う**。実際 1 度
    # 間違えて register_spin / icp_point2point_3d / register_fpfh を誤って
    # TYPEMISS に挙げた ― 中身は正しい (R(3,3), t(3,), info) だった
    "pose": lambda v: isinstance(v, (tuple, list)) and len(v) >= 2
    and tuple(getattr(v[0], "shape", ())) == (3, 3)
    and tuple(getattr(v[1], "shape", ())) == (3,),
    # zscan = (Z,H,W) の走査スタック。video (T,H,W) / histcube (H,W,T) /
    # voxel と述語を相互に満たすので、型を分けないと軸の意味だけが黙って
    # すり替わる(実測: zscan を motion_magnify に渡すと有限の「増幅結果」が返る)
    "zscan": lambda v: isinstance(v, np.ndarray) and v.ndim == 3
    and v.dtype.kind == "f" and v.shape[0] >= 3
    and v.shape[1] >= 2 and v.shape[2] >= 2,
    # sweep = 非負の 1-D 掃引(干渉信号 or 戻りスペクトル)
    "sweep": lambda v: isinstance(v, np.ndarray) and v.ndim == 1
    and v.dtype.kind == "f" and v.size >= 16 and (v >= 0.0).all(),
    # beatcube = (アンテナ, チャープ, サンプル) の**複素**立方体。3-D complex の
    # 既存語彙は無い(cimage は 2-D)。real を弾くのがこの型の契約の本体で、
    # 実の histcube と形は同じだが dtype だけが違う
    "beatcube": lambda v: isinstance(v, np.ndarray) and v.ndim == 3
    and v.dtype.kind == "c" and v.shape[1] >= 2 and v.shape[2] >= 2,
    # qimage = (H,W,4) の四元数画像。**voxel / sdf / labels / video / score /
    # histcube の述語も同時に満たす**(どれも ndim==3)ので、宣言型が qimage の
    # op だけがこのプールを食う設計に頼っている。逆向き(既存の種が qimage を
    # 名乗る)は起きない — 既存生成器で shape[2]==4 のものは無い
    "qimage": lambda v: isinstance(v, np.ndarray) and v.ndim == 3
    and v.shape[2] == 4 and v.dtype.kind == "f",
    # polsweep = 検光子を既知角度で回して撮った (N,H,W)。images と構造は同じだが
    # 意味が違い、**両方向とも黙って間違う**: 本物のライトスタックを
    # polarization_separate へ渡すと例外を出さず偏光度 5.4% を捏造し、逆に
    # 本物の掃引を photometric_stereo_robust へ渡すと真の法線が (0,0,1) の
    # 平面に対して平均 34 度ずれた法線を返す(親の独立検算で 35.15 度 vs
    # 本物の測光データ 0.000000 度)。N>=3 はモデルの未知数が 3 つだから、
    # 非負は検光子を通った放射輝度だから。**フレーム順と角度列の対応は
    # 型では守れない** — 並べ替えた掃引は「別のシーンの正当な掃引」になる
    "polsweep": lambda v: isinstance(v, np.ndarray) and v.ndim == 3
    and v.shape[0] >= 3 and v.dtype.kind == "f"
    and np.isfinite(v).all() and (v >= 0.0).all(),
    # video = (T,H,W)。voxel と ndim は同じだが先頭が時間軸。共有すると例外も
    # NaN も無しに z を時間として読むので型を分ける(実測確認済み)
    "video": lambda v: isinstance(v, np.ndarray) and v.ndim == 3
    and v.dtype.kind == "f" and v.shape[0] >= 2
    and v.shape[1] >= 4 and v.shape[2] >= 4,
    # rgbimage = (H,W,3) の色画像。pointmap / normalmap と**構造は同じ**なので
    # 型を分けないと、法線マップを鏡面分離に渡しても例外なく「分離結果」が
    # 返る(実測確認済み)。型は入れ物の形でなく意味の約束
    "rgbimage": lambda v: isinstance(v, np.ndarray) and v.ndim == 3
    and v.shape[2] == 3,
    # score = ピークを持つ相関 volume。voxel と同じ 3-D だが、意味は「マッチの
    # 良さ」でありサブボクセル精緻化の入力になる
    "score": lambda v: isinstance(v, np.ndarray) and v.ndim == 3,
    # counts = 時間 bin で添字づけられた**非負**の光子カウント列。既存 signal と
    # 構造は同じだが、signal プール(正弦波 = 負値あり)を渡すと必ず CONTRACT に
    # なり photon 族が一度も実行されない(実測 7/17 未到達)。jones/stokes と同じ判断
    "counts": lambda v: isinstance(v, np.ndarray) and v.ndim == 1
    and v.dtype.kind == "f" and v.size >= 2 and (v >= 0.0).all(),
    # countrate = SPAD の計数レート列 [Hz]。counts と形は同じだが値域が 7 桁違い、
    # counts を渡すとデッドタイム則が恒等写像に潰れて物理が一度も踏まれない
    # (実測: ヒストグラムを渡すと相対変化 1.1e-4、本物のレートなら 33%)
    "countrate": lambda v: isinstance(v, np.ndarray) and v.ndim == 1
    and v.dtype.kind == "f" and v.size >= 1 and (v >= 0.0).all(),
    # histcube = (H, W, T) の到達時刻ヒストグラム。voxel と ndim は同じだが
    # 時間軸が最後という約束が違う(voxel を渡すと黙って間違った深度が出る)
    "histcube": lambda v: isinstance(v, np.ndarray) and v.ndim == 3
    and v.shape[2] >= 2 and v.dtype.kind == "f" and (v >= 0.0).all(),
    # jones = Jones ベクトル(長さ 2 固定の complex)。cpoints(輪郭)と形は
    # 同じでも意味が違い、長さが違えば必ず ValueError なので別プール
    "jones": lambda v: isinstance(v, np.ndarray) and v.shape == (2,)
    and v.dtype.kind == "c",
    # stokes = Stokes ベクトル(長さ 4 固定の実、偏光度 <= 1 が物理制約)
    "stokes": lambda v: isinstance(v, np.ndarray) and v.shape == (4,)
    and v.dtype.kind == "f",
    # mesh = ``(V (nv,3), F (nf,3))`` の **2 要素**タプル。pose と同じく
    # **型ではなく形**で判定する(GPU backend を持つ op は torch.Tensor を返す
    # のがこの repo の約束で、isinstance(np.ndarray) と書くと述語の側が間違う)。
    #
    # ★ 「2 要素ちょうど」は pose(`len >= 2` で info を許す)と**わざと違う**。
    # 実測 2026-09-02: mesh を 1 引数で受ける既存 consumer 4 件
    # (face_normals / vertex_normals / mesh_area / vertex_curvature)は
    # 3-tuple に対して "mesh must be a 2-element tuple (vertices, faces)" を
    # 送出し、cadmap の `_mesh` と render3d._mesh_arrays も 2 要素しか受けない。
    # つまり **この repo の mesh sort の正典は 2-tuple** で、余分な要素は
    # 「情報が多い」のではなく下流が全滅する型の嘘になる。唯一の例外だった
    # `voxel_to_mesh`((v, f, n) を返す)は ops3d.RESULT_ADAPTERS で正典の
    # 並びを取り出すようにした(gicp / vol_label と同じ扱い)。
    "mesh": lambda v: isinstance(v, (tuple, list)) and len(v) == 2
    and len(getattr(v[0], "shape", ())) == 2 and tuple(v[0].shape)[1:] == (3,)
    and len(getattr(v[1], "shape", ())) == 2 and tuple(v[1].shape)[1:] == (3,),

    # ======================================================================= #
    # wave-7(2026-09-02): **述語が 1 つも無かった 17 型**                      #
    #                                                                         #
    # tools/conversion_matrix.py で型変換を行列として点検したところ、変換を行う
    # 443 op ののべのうち **76 op が「出力型に述語の無い型」を宣言していた** =
    # 何を返しても TYPEMISS にならない穴だった。voxel_to_mesh の 3-tuple、
    # render_beauty の RGB、project_points のタプル、alpha_shape_boundary の
    # 添字はどれも「述語を足した瞬間に出てきた」ので、ここは未採掘の鉱脈である。
    #
    # 各型の「正典」は**多数決ではなく消費側を実行して**決めた。消費側が無い
    # 出力専用の型(axes/curvature/flow/frame/gradient/graph/hessian/rot_scale/
    # shift)は、産む op を全部実行して**全員が満たす一番強い不変条件**を書く
    # (= 弱くしすぎて何も守らない述語も、強くしすぎて正しい op を責める述語も
    # 避ける)。判定は全て **型ではなく形**(_shape)で行う。
    # ======================================================================= #

    # angle = **スカラ角(度)**。正典は消費側が決めた: 唯一の消費側
    # refine_rotation_z(scene, template, init_angle_deg) にタプルを渡すと
    # "init_angle_deg must be a scalar angle in degrees (got tuple) — this op
    # returns (angle_deg, n_iters); pass result[0] when chaining" で fail-closed
    # する(実測)。生成器も float。唯一の producer が (角, 反復数) を返すのは
    # ops3d.RESULT_ADAPTERS で剥がした
    "angle": _is_scalar,

    # axes = moment_axes の **(centroid(3,), axes(3,3), eigvals(3,))**。
    # 消費側が無い出力専用の型で producer も 1 つなので、その 1 つの契約
    # (docstring「返り値 (centroid(3,), axes(3,3) 列=主軸, eigvals(3,))」)を
    # そのまま固定する。3x3 が真ん中に来ることが姿勢正準化の本体
    "axes": lambda v: _is_seq(v, 3) and _shape(v[0]) == (3,)
    and _shape(v[1]) == (3, 3) and _shape(v[2]) == (3,),

    # bspline_curve = FITPACK の **tck = (t, c, k)**。消費側 eval_bspline_curve の
    # docstring が「fit_bspline_curve が返した (t, c, k)」と明記し、渡し間違いを
    # "curve tck" 名指しで弾く(tests/test_ops3d_ledger.py が固定済み)。
    # c は次元ごとの係数列(parametric splprep なので list of 1-D)
    "bspline_curve": lambda v: _is_seq(v, 3) and len(_shape(v[0])) == 1
    and isinstance(v[1], (tuple, list, np.ndarray))
    and isinstance(v[2], (int, np.integer)),

    # bspline_surface = FITPACK の **[tx, ty, c, kx, ky]**(bisplrep)。
    # 消費側 eval_bspline_surface / surface_residual がこの 5 要素を要求し、
    # 曲線 tck(3 要素)や多項式 model(dict)は名指しで fail-closed する
    "bspline_surface": lambda v: _is_seq(v, 5) and len(_shape(v[0])) == 1
    and len(_shape(v[1])) == 1 and len(_shape(v[2])) == 1
    and isinstance(v[3], (int, np.integer)) and isinstance(v[4], (int, np.integer)),

    # curvature = **曲率の場**。消費側は無いので producer 3 つを全部実行して
    # 一番強い共通条件を採った(実測 2026-09-02):
    #   vertex_curvature       -> (nv,) の 1 本(平均曲率の大きさ)
    #   principal_curvatures   -> ((N,), (N,)) の 2 本(k1, k2)
    #   curvature_maps         -> (S, curvedness, mask, |g|) の 4 本 (D,H,W)
    # つまり「1 本の場」または「**同じ形**の場を 2〜4 本」。形が揃っていることが
    # 効く条件で、揃っていない詰め合わせ(補助情報つきタプル)は弾く
    "curvature": lambda v: (len(_shape(v)) >= 1 and not _is_seq(v))
    or (_is_seq(v, 2, 3, 4) and all(len(_shape(x)) >= 1 for x in v)
        and len({_shape(x) for x in v}) == 1),

    # deformation = tps_fit の TPS モデル dict。消費側 tps_warp が
    # f(x) = [1,x,y,z]·a + Σ w_i·U(‖x−p_i‖) を評価するのに ctrl / w / a を引く
    "deformation": lambda v: isinstance(v, dict) and {"ctrl", "w", "a"} <= set(v),

    # descriptor = **数値配列**。正典は消費側が決めた: 唯一の消費側
    # shape_distance に dict を渡すと "descriptors must be numeric vectors
    # (got dict / dict)" で fail-closed し、ndarray なら (64,) の分布でも
    # (160,33) の per-point FPFH でも (160,3,3) の共分散でも通る(実測)。
    # よって次元数ではなく「配列であること」が契約。dict を返していた 3 op
    # (fit_zernike / central_moments / topology_signature)は out を 'table' へ
    # 直した(ops3d の該当行にコメント)
    "descriptor": lambda v: not isinstance(v, (tuple, list, dict))
    and len(_shape(v)) >= 1,

    # flow = **3 次元変位の場**。消費側は無いので producer 4 つを実行(実測):
    #   estimate_flow / nearest_neighbor_flow / smooth_flow -> (N,3) 散布
    #   scene_flow_lk                                       -> (3,D,H,W) 組織化
    # points と pointmap を分けているのと同じ「散布 / 組織化」の 2 形で、どちらも
    # 3 成分が要。成分軸の位置が違う(末尾 / 先頭)ので両方を明示的に許す
    "flow": lambda v: not _is_seq(v) and (
        (len(_shape(v)) == 2 and _shape(v)[1] == 3)
        or (len(_shape(v)) == 4 and _shape(v)[0] == 3)),

    # frame = frenet_frame の **(T, N, B) 各 (Npts,3) 単位ベクトル**。
    # 3 本が同じ点数で揃っていることが標構の意味そのもの(1 本でも欠けたら
    # 曲線上の直交系にならない)
    "frame": lambda v: _is_seq(v, 3) and all(
        len(_shape(x)) == 2 and _shape(x)[1] == 3 for x in v) \
    and len({_shape(x)[0] for x in v}) == 1,

    # gradient = **先頭に batch/channel 軸を持たない勾配場の組**。producer 2 つ:
    #   gradient3d -> (gmag (D,H,W), gvec (D,H,W,3))
    #   sobel3d    -> (gz, gy, gx) 各 (D,H,W)
    # 兄弟の hessian3d が (D,H,W) を 6 本返すことも合わせて、sort の正典は
    # 「空間 3 軸が先頭に来る場」。sobel3d は conv3d の出力を squeeze せず
    # (1,1,D,H,W) を返していた(この述語で顕在化)ので ops3d.RESULT_ADAPTERS で
    # 落とした。空間 3 軸が全要素で一致することを見る
    "gradient": lambda v: _is_seq(v, 2, 3) and all(
        len(_shape(x)) in (3, 4) for x in v) \
    and len({_shape(x)[:3] for x in v}) == 1,

    # graph = knn_graph の **(idx (N,k) int, dist (N,k) float)**。同じ形の 2 枚で、
    # 片方が添字(整数)であることが「グラフ」たる所以。float の添字を渡されると
    # 下流は黙って丸めるので dtype の種別まで見る
    "graph": lambda v: _is_seq(v, 2) and len(_shape(v[0])) == 2
    and _shape(v[0]) == _shape(v[1])
    and getattr(getattr(v[0], "dtype", None), "kind", "i") in "iu",

    # hessian = hessian3d の **6 独立成分 (fzz,fyy,fxx,fzy,fzx,fyx)**。対称行列の
    # 上三角なので 6 本ちょうどで、全部が同じ (D,H,W) であることが対称性の表現
    "hessian": lambda v: _is_seq(v, 6) and all(len(_shape(x)) == 3 for x in v) \
    and len({_shape(x) for x in v}) == 1,

    # poly_surface = fit_poly_surface の model dict。消費側 eval_poly_surface が
    # model["degree"] / coef / powers を引き、B スプラインの tck(list)を渡すと
    # "fit_poly_surface" 名指しで fail-closed する(tests/test_ops3d_ledger.py の
    # test_surface_models_are_separate_types が固定済み)
    "poly_surface": lambda v: isinstance(v, dict)
    and {"coef", "powers", "degree"} <= set(v),

    # position = **[z, y, x] の 3 成分**。正典は消費側を実行して決めた(実測):
    # refine_translation_lk / refine_lm に 4 成分を渡すと "init_pos must have
    # exactly 3 components [z, y, x] (got 4)" で fail-closed する。生成器も
    # (8.0, 8.0, 8.0)。match_* 系が返す [score, d, h, w] の 4 成分と
    # match_hough_3d の (topk,4) 投票表は ops3d.RESULT_ADAPTERS で座標だけに剥がした
    "position": lambda v: (_is_seq(v, 3) and all(_is_scalar(x) for x in v)) \
    or _shape(v) == (3,),

    # primitive = **幾何原始形状の記述**。33 の producer を全部実行したところ、
    # 名前つき dict(fit_plane3 / obb / ransac_* …)と位置つきタプル
    # (aabb=(min,max) / fit_plane_3d=(点,法線,rms) / vol_bounding_box=6 整数 …)の
    # 2 系統が同居していた。**単一の正典は無い** — 台帳の消費側 8 op
    # (angle_between_lines(d1,d2) など)は primitive オブジェクトではなく
    # 生のベクトルを 2 本取る宣言で、primitive を制約していない(実測)。
    # そこで「弱いが本当に全員が満たす」条件だけを書く: 部品に名前がついた dict
    # か、2 つ以上の部品を並べたタプル/リスト。裸の配列やスカラは
    # 「どの原始形状なのか」を運べないので嘘として弾く
    "primitive": lambda v: isinstance(v, dict) or _is_seq(v) and len(v) >= 2,

    # rot_scale = match_logpolar_z の **(angle_deg, scale)**。docstring が
    # 「返り値 (angle_deg, scale)」と明記。2 つのスカラで、片方だけ返すと
    # Fourier-Mellin の意味(回転とスケールの同時推定)が失われる
    "rot_scale": lambda v: _is_seq(v, 2) and all(_is_scalar(x) for x in v),

    # shift = match_phase_3d の **整数シフト (dz,dy,dx)**。位相相関の答えは
    # 格子上の平行移動なので 3 成分ちょうど(サブボクセルは refine_* の仕事)
    "shift": lambda v: (_is_seq(v, 3) and all(_is_scalar(x) for x in v)) \
    or _shape(v) == (3,),
}


#: docstring が非有限を明示契約している op(例: esdf は「全自由なら +inf」、
#: register_spin/register_fpfh は「対応なしなら rmse=inf」の文書化済み番兵値、
#: sdf_* は esdf の契約 inf を min/max 代数で厳密伝播 — sdf_ops モジュール docstring)
#: mat_cond は「厳密特異なら inf を返す(raise しない)」を docstring 契約
NONFINITE_BY_CONTRACT = {"esdf", "register_spin", "register_fpfh",
                         "sdf_union", "sdf_intersect", "sdf_subtract",
                         "sdf_smooth_union", "sdf_offset", "mat_cond"
                         } | NONFINITE_BY_CONTRACT_OPTICS \
    | NONFINITE_BY_CONTRACT_CADMAP

#: pool へ入れる 1 産物の上限バイト数。拡大系 op(upsample/uncrop/resize)の連鎖で
#: 体積が指数増殖し、後段の全 op が実質ハングする(wave-4 実測: ~34GB の voxel に
#: r=1 の morph_blackhat3d が 20 分+スラッシング)。上限超過は黙って捨てず
#: GROWTH として記録する(silent cap 禁止)。128MB ≈ float32 で 320³ 相当。
MAX_POOL_BYTES = 128 * 2 ** 20


def _nbytes(val):
    """産物の概算バイト数(ndarray は厳密、入れ物は再帰和、その他 0)。"""
    if isinstance(val, np.ndarray):
        return val.nbytes
    if isinstance(val, (list, tuple)):
        return sum(_nbytes(v) for v in val)
    if isinstance(val, dict):
        return sum(_nbytes(v) for v in val.values())
    return 0


def _classify(exc):
    if isinstance(exc, ValueError):
        return "CONTRACT"
    if isinstance(exc, (ImportError, ModuleNotFoundError, NotImplementedError)):
        return "OPTIONAL"      # optional 依存の明示エラーは白
    return "SUSPECT"


def _finite_ok(val):
    """ndarray(を含む入れ物)に NaN/Inf が無いか。数値以外は不問。"""
    if isinstance(val, np.ndarray):
        return val.dtype.kind not in "fc" or bool(np.isfinite(val).all())
    if isinstance(val, (list, tuple)):
        return all(_finite_ok(v) for v in val)
    if isinstance(val, dict):
        return all(_finite_ok(v) for v in val.values())
    if isinstance(val, float):
        return np.isfinite(val)
    return True


def _step_rng(chain_seed, name, occurrence, fallback):
    """引数束縛用の**位置に依存しない**乱数源。

    候補抽選(連鎖 rng)と引数抽選を分けるのが肝: 連鎖 rng は「次にどの op を
    引くか」で消費量が変わるため、op を 1 つ外すと以降の抽選が全部ずれ、
    最小化の再走が原理的に再現しなくなる(実測: 再現 48/65)。鍵を
    (連鎖 seed, op 名, その op の出現回数)にすると、**無関係な前段を落としても
    当該 op の引数抽選は不変**になり、pool の中身の違いだけが再現可否を決める
    = 削り込みが本来見たい依存関係そのものになる。
    """
    if chain_seed is None:
        return fallback                    # 旧来の呼び方(再現性を要求しない)
    key = zlib.crc32(name.encode("utf-8"))
    return np.random.default_rng((int(chain_seed) & 0xFFFFFFFF, key, occurrence))


def run_chain(ops, gens, rng, length, log, chain_seed=None, script=None,
              explore=0.0):
    """1 連鎖 = 型付き pool を育てながら op を実行。発見は log に積む。

    *script* に op 名の列を渡すと**その順で強制実行**する(--minimize の再走)。
    型が揃わない step は黙って飛ばす = その短縮では再現しない、と判定される。
    *chain_seed* は findings に載せて再現に使う。
    """
    pool = {}
    for t, g in gens.items():
        pool[t] = [g(rng)]
    trace = []
    occ = {}
    by_name = {o[0]: o for o in ops} if script is not None else None
    # この連鎖が狙う op(決定的: 連鎖固有 seed から引く)。script 再走のときは
    # 狙いを持たない — 再現は与えられた op 列がすべてだから。
    target = None
    if script is None and explore > 0.0 and ops:
        target = ops[int(np.random.default_rng(
            zlib.crc32(b"target|%d" % (chain_seed or 0))).integers(len(ops)))]
    for i in range(len(script) if script is not None else length):
        if script is not None:
            op = by_name.get(script[i])
            if op is None:
                continue
            name, dim, ins, out, fn = op
            if not all((t in pool and pool[t]) or t == "any" for t in ins):
                continue          # 入力型が揃わない = この短縮では到達不能
        else:
            # pool にある型を食える op を候補化
            cands = [o for o in ops
                     if all((t in pool and pool[t]) or t == "any" for t in o[2])]
            if not cands:
                break
            # **狙いを持った拡散**。一様に引くと、候補が数百ある中から特定の op
            # が長さ 6 の枠内で選ばれる確率は低く、実測では 1500 連鎖でも 112 op
            # が「構造的には到達可能なのに一度も引かれない」ままだった。
            #
            # 最初は「まだプールに無い型を産む op を優先する」型空間バイアスを
            # 試したが、**効かなかった**(321 → 322 op、1500 連鎖で +1)。プールは
            # 最初から全生成器型で埋まっているので、優先対象がすぐ尽きるため。
            #
            # そこで **連鎖ごとに目標 op を 1 つ決め、そこへ寄せる**方式にした。
            # 目標は連鎖固有 seed から決めるので chain_seed だけで再現でき、
            # --minimize / --replay の前提を壊さない。1500 連鎖 / 434 op なら
            # 1 op あたり平均 3.5 連鎖が狙ってくれる勘定になる。
            if target is not None and rng.random() < explore:
                hit = [o for o in cands if o[0] == target[0]]
                if hit:
                    cands = hit
                else:
                    # 目標が食う型を**産む** op を優先 = 1 手ぶん近づく
                    want = set(target[2])
                    step = [o for o in cands if o[3] in want]
                    if step:
                        cands = step
            name, dim, ins, out, fn = cands[rng.integers(len(cands))]
        occ[name] = occ.get(name, 0) + 1
        arng = _step_rng(chain_seed, name, occ[name], rng)
        if name in OP_ARG_BUILDERS:
            bound = OP_ARG_BUILDERS[name](pool, arng)
            # builder が **list** を返したら「data 引数だけを組んだ」の意で、
            # 残る必須引数の束縛は通常経路(op 固有 → 名前ヒント)に任せる。
            # tuple を返す builder(従来のもの)は (args, kwargs) 完成形。
            if isinstance(bound, list):
                bound = _bind_args(name, fn, bound, arng)
        else:
            data_args = []
            for t in ins:
                src = pool[t] if t != "any" else pool[arng.choice(sorted(pool))]
                data_args.append(src[arng.integers(len(src))])
            bound = _bind_args(name, fn, data_args, arng)
        if bound is None:
            continue
        args, kwargs = bound
        big = sum(_nbytes(a) for a in args)
        if big > 32 * 2 ** 20:
            # 重い入力は実行前に予告(万一のストールでもログだけで犯人が判る)
            print(f"  big-input: {name} ({big / 2**20:.0f} MB)", flush=True)
        t0 = time.perf_counter()
        try:
            result = fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 — ファザーの本懐
            kind = _classify(exc)
            if kind != "OPTIONAL":
                log.append({"kind": kind, "op": name, "dim": dim,
                            "exc": type(exc).__name__, "msg": str(exc)[:200],
                            "trace": trace + [name], "seed": chain_seed,
                            "tb": traceback.format_exc(limit=3)})
            continue
        dt = time.perf_counter() - t0
        if dt > SLOW_S:
            log.append({"kind": "SLOW", "op": name, "dim": dim, "sec": round(dt, 1),
                        "trace": trace + [name], "seed": chain_seed})
        if name in ADAPTERS:
            result = ADAPTERS[name](result)
        if result is None:
            continue
        if not _finite_ok(result) and name not in NONFINITE_BY_CONTRACT:
            log.append({"kind": "NONFINITE", "op": name, "dim": dim,
                        "trace": trace + [name], "seed": chain_seed})
            continue                      # 毒は pool に入れない
        nb = _nbytes(result)
        if nb > MAX_POOL_BYTES:
            log.append({"kind": "GROWTH", "op": name, "dim": dim,
                        "mb": round(nb / 2 ** 20, 1),
                        "trace": trace + [name], "seed": chain_seed})
            continue                      # 巨大産物は pool に入れない(指数増殖防止)
        check = TYPE_CHECKS.get(out)
        if check is not None and not check(result):
            log.append({"kind": "TYPEMISS", "op": name, "dim": dim,
                        "exc": out, "msg": "declared %r but returned %s%s" % (
                            out, type(result).__name__,
                            getattr(result, "shape", "")),
                        "trace": trace + [name], "seed": chain_seed})
            continue                      # 型の嘘も pool に入れない
        trace.append(name)
        pool.setdefault(out, []).append(result)
    return trace


# --------------------------------------------------------------------------- #
# 収束フェーズ: 発見を「最小再現の連鎖」へ削る(delta debugging)               #
# --------------------------------------------------------------------------- #
#: 署名を作るときにメッセージから消す可変部分。良いエラーメッセージほど
#: 「負の bin が 127 個、最小 -1.176」のように**その実行固有の数**を含むので、
#: 素のメッセージで同一視すると同じ 1 件の問題が実行のたびに別署名になる
#: (実測: photon 族を足した波で署名が 99 → 238 に膨れ、増分のほぼ全部が
#: 「dtof_depth: hist has N negative bin(s) (min -X)」の N と X 違いだった)。
_NUM_RE = re.compile(r"[-+]?\d[\d,]*\.?\d*(?:[eE][-+]?\d+)?")


def signature(finding):
    """findings を同一視する鍵(main の集約と --minimize で同じ定義を使う)。

    メッセージ中の**数値を伏せて**から比べる。伏せないと、実行ごとに違う数を
    含むメッセージが別々の署名になり、収束(拡散 → 署名でまとめる)が機能しない。
    """
    msg = _NUM_RE.sub("#", finding.get("msg", ""))
    return (finding["kind"], finding["op"], finding.get("exc", ""), msg[:80])


def reproduces(ops, gens, script, seed, target):
    """*script* を強制実行して *target* 署名が再現するか。"""
    log = []
    run_chain(ops, gens, np.random.default_rng(seed), 0, log,
              chain_seed=seed, script=script)
    return any(signature(f) == target for f in log)


def minimize_finding(ops, gens, finding, verbose=True):
    """1 件の発見を最小の op 列へ削る。→ (script or None, 再現したか)。

    貪欲な delta debugging: 末尾(当該 op)は残したまま、前段を 1 つずつ外して
    署名が再現し続けるかを試す。**再現しなかった場合は正直に None を返す**
    (この段階で「短縮できた」と嘘をつくと、その後の推測パッチを誘発する)。
    """
    target = signature(finding)
    seed = finding.get("seed")
    script = list(finding.get("trace") or [])
    if seed is None or not script:
        return None, False
    if not reproduces(ops, gens, script, seed, target):
        return None, False              # trace 単独では再現しない(honest)
    i = 0
    while i < len(script) - 1:          # 末尾 = 当該 op は落とさない
        trial = script[:i] + script[i + 1:]
        if reproduces(ops, gens, trial, seed, target):
            script = trial              # 外しても再現 = その op は無関係
            if verbose:
                print(f"    - drop {len(script) + 1}->{len(script)} ops", flush=True)
        else:
            i += 1
    return script, True


def minimize_file(path, ops, gens, only=None):
    """署名 jsonl の各行を最小化し、再現スクリプトを書き出す。"""
    findings = [json.loads(ln) for ln in open(path, encoding="utf-8") if ln.strip()]
    if only:
        findings = [f for f in findings if f.get("op") == only]
    print(f"== 最小化 {len(findings)} 署名 <- {path}")
    out_lines, n_ok = [], 0
    for f in findings:
        head = f"[{f['kind']}] {f['op']}"
        script, ok = minimize_finding(ops, gens, f, verbose=False)
        if not ok:
            print(f"  {head}: 再現せず(seed/trace 不足 or 非決定的)— 短縮なし")
            out_lines.append(dict(f, minimal=None, reproduced=False))
            continue
        n_ok += 1
        print(f"  {head}: {len(f.get('trace') or [])} -> {len(script)} ops  {script}")
        out_lines.append(dict(f, minimal=script, reproduced=True))
    dst = os.path.splitext(path)[0] + "_minimal.jsonl"
    with open(dst, "w", encoding="utf-8") as fh:
        for rec in out_lines:
            rec.pop("tb", None)
            fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    print(f"== 再現できた {n_ok}/{len(findings)} 件 -> {dst}")
    if n_ok:
        print("== 再走コマンド例:")
        for rec in out_lines[:3]:
            if rec.get("minimal"):
                print(f"   py -3.11 tools/chain_fuzz.py --replay {rec['seed']} "
                      f"--script {','.join(rec['minimal'])}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chains", type=int, default=200)
    ap.add_argument("--length", type=int, default=6)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "chain_fuzz.jsonl"))
    ap.add_argument("--minimize", metavar="JSONL",
                    help="署名 jsonl を読み、各発見を最小の op 列へ削る")
    ap.add_argument("--only", metavar="OP", help="--minimize をこの op に絞る")
    ap.add_argument("--replay", type=int, metavar="SEED",
                    help="--script を指定 seed で強制実行(最小再現の確認)")
    ap.add_argument("--script", help="--replay で実行する op 名のカンマ区切り")
    ap.add_argument("--explore", type=float, default=0.5,
                    help="型空間の探索バイアス [0,1]。まだプールに無い型を"
                         "産む op を優先する確率。0 で一様(旧挙動)")
    ap.add_argument("--coverage-out", metavar="JSON",
                    help="どの op が走り、どの op が一度も走らなかったかを書き出す。"
                         "「304/417」という数だけでは、残る 113 が頑健なのか"
                         "そもそも到達不能なのかが区別できない")
    args = ap.parse_args()
    if args.minimize:
        minimize_file(args.minimize, catalog(), make_generators(), only=args.only)
        return 0
    if args.replay is not None:
        if not args.script:
            print("--replay には --script が要る", file=sys.stderr)
            return 2
        script = [s for s in args.script.split(",") if s]
        log = []
        run_chain(catalog(), make_generators(), np.random.default_rng(args.replay),
                  0, log, chain_seed=args.replay, script=script)
        print(f"== replay seed={args.replay} script={script}")
        for f in log:
            print(f"  [{f['kind']}] {f['op']}: {f.get('exc', '')} {f.get('msg', '')[:120]}")
        if not log:
            print("  発見なし(この seed/script では再現しない)")
        return 0
    ops = catalog()
    gens = make_generators()
    log = []
    used = set()
    t0 = time.perf_counter()
    for i in range(args.chains):
        # 連鎖固有 seed: 後から i 番目だけを正確に再走できる(--minimize の前提)
        chain_seed = args.seed * 1_000_003 + i
        trace = run_chain(ops, gens, np.random.default_rng(chain_seed),
                          args.length, log, chain_seed=chain_seed,
                          explore=args.explore)
        used.update(trace)
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{args.chains} chains, findings {len(log)}, "
                  f"ops covered {len(used)}", flush=True)
    wall = time.perf_counter() - t0

    # 収束: 署名(kind, op, exc)でまとめる
    sig = {}
    for f in log:
        key = signature(f)
        sig.setdefault(key, {"n": 0, "sample": f})
        sig[key]["n"] += 1
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        for key, v in sorted(sig.items()):
            rec = dict(v["sample"])
            rec["count"] = v["n"]
            rec.pop("tb", None)
            fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")

    kinds = {}
    for f in log:
        kinds[f["kind"]] = kinds.get(f["kind"], 0) + 1
    print(f"\n== 拡散 {args.chains} 連鎖 x len {args.length}(seed {args.seed}, "
          f"{wall:.0f}s)")
    print(f"== op カバレッジ: {len(used)}/{len(ops)}")
    # 未到達を族ごとに出す。到達 0 の族は「頑健だから発見が無い」のではなく
    # 「そもそも連鎖が入ってこない」= 狭い sort の症状で、意味がまるで違う
    by_family = {}
    for name, fam, _ins, _out, _fn in ops:
        hit, miss = by_family.setdefault(fam, ([], []))
        (hit if name in used else miss).append(name)
    print("== 族ごとの到達: " + "  ".join(
        f"{fam} {len(h)}/{len(h) + len(m)}"
        for fam, (h, m) in sorted(by_family.items())))
    if args.coverage_out:
        os.makedirs(os.path.dirname(os.path.abspath(args.coverage_out)), exist_ok=True)
        with open(args.coverage_out, "w", encoding="utf-8") as fh:
            json.dump({"total": len(ops), "covered": sorted(used),
                       "uncovered": sorted(n for n, *_ in ops if n not in used),
                       "by_family": {f: {"covered": sorted(h), "uncovered": sorted(m)}
                                     for f, (h, m) in sorted(by_family.items())}},
                      fh, ensure_ascii=False, indent=1)
        print(f"== カバレッジ内訳 -> {args.coverage_out}")
    print(f"== 発見(生): {kinds} / 署名数 {len(sig)}")
    print(f"== 署名一覧 -> {args.out}")
    order = {"SUSPECT": 0, "NONFINITE": 1, "SLOW": 2, "CONTRACT": 3}
    for key, v in sorted(sig.items(), key=lambda kv: (order.get(kv[0][0], 9), -kv[1]["n"])):
        kind, op, exc, msg = key
        if kind == "CONTRACT":
            continue                      # 白は件数のみ(ファイルには残す)
        print(f"  [{kind}] {op} x{v['n']} {exc}: {msg}")
    if len(sig) > sum(1 for k in sig if k[0] == "CONTRACT"):
        print("\n== 収束(最小再現): py -3.11 tools/chain_fuzz.py "
              f"--minimize {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
