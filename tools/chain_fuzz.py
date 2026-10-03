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
import contextlib
import json
import os
import tempfile
import re
import sys
import time
import traceback
import zlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

# ★カタログ・ヒント・アダプタは出荷モジュール ``typed_catalog`` が正本(2026-09-05)。
# 以前はここに住んでいて、backends_typed が tools/ を sys.path に足して読んでいた ——
# その結果 wheel では tb_* 143 op が黙って消えていた。向きを逆にした。
from typed_catalog import (ADAPTERS, OP_PARAM_HINTS, PARAM_HINTS,  # noqa: F401
                           _registry_adapters, catalog)

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


def _labels(rng):
    """整数ラベル。**2-D 画像と 3-D volume を必ず混ぜて出す**。

    2026-09-02 実測: 種が 2-D だけだと **3-D を要求する消費側が一度も走らない**。
    ``vol_region_props`` は 3-D を期待し 2-D を documented ValueError で拒否する
    ので、2-D しか無いプールでは毎回 fail-closed し、「同じ連鎖の中で先に
    vol_label が引かれた場合だけ」到達する = ``counts`` を ``signal`` に相乗り
    させていたときと同じ罠(実測でこの op は 1500 連鎖の未到達 75 件に入っていた)。
    逆に 3-D だけにすると 2-D を要求する ``cad_defect_to_cad`` /
    ``illuminant_from_dichromatic_planes`` が走らなくなるので、**両方**を出す。
    3-D は球ファントムの連結成分ラベルにする(真の成分数が分かっている)。
    """
    if rng.random() < 0.5:
        return _labels_2d(rng)
    import volops                                          # noqa: PLC0415
    return volops.vol_label(_ball_vol(rng) > 0.5, 26)[0]


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


def _conn_graph(rng):
    """conn_graph(2026-09-20、conngraph 族): 12 ノード 2 クリークの重みつき有向グラフ。

    ★一様乱数の行列にしない —— 成分数・モジュラリティ・rich club・モチーフは
    構造の無い入力では「どのノブでも同じ数」を返し、口が動いているかを測れない。
    内側は全結合(重み 1..5)、クリーク間は橋 2 本(重み 0.5)。橋の重みだけ乱数。
    """
    W = np.zeros((12, 12))
    for base in (0, 6):
        for i in range(6):
            for j in range(6):
                if i != j:
                    W[base + i, base + j] = 1.0 + (i * 7 + j * 3) % 5
    W[5, 6] = float(rng.uniform(0.2, 0.8))
    W[11, 0] = float(rng.uniform(0.2, 0.8))
    return W


def _synapse_table(rng):
    """synapse_table: `_conn_graph` の非零要素を (pre, post, count) の行にした表(count は整数)。"""
    W = _conn_graph(rng)
    pre, post = np.nonzero(W)
    return np.stack([pre, post, np.ceil(W[pre, post])], axis=1).astype(np.float64)


def _patch_tokens(rng, size=32, patch=8):
    """滑らかな画像を patch x patch で切った (T, patch²) の列。llmcore の種。"""
    y, x = np.mgrid[0:size, 0:size]
    img = 0.5 + 0.5 * np.sin(x / 5.0) * np.cos(y / 7.0) + 0.02 * rng.standard_normal((size, size))
    n = size // patch
    return img.reshape(n, patch, n, patch).transpose(0, 2, 1, 3).reshape(n * n, patch * patch)


def make_generators():
    return {
        "voxel": _ball_vol,
        # llmcore(2026-09-24): tokens は**画像パッチ**を種にする。★一様乱数だと
        # どの行も似た向きになり、注意の重みが全行ほぼ一様になって「走ったが
        # 意味のある出力でない」側に落ちる。滑らかな画像を 8x8 で切ると、
        # 近い場所のパッチが近い向きを向く = 注意が構造を持つ。
        "tokens": _patch_tokens,
        # attnmap: 上の tokens から実際に作った注意行列(行和 1 の本物)。
        "attnmap": lambda rng: __import__("llmcore").attention_weights(
            __import__("llmcore").attention_scores(_patch_tokens(rng), _patch_tokens(rng))),
        # conngraph(2026-09-20): 新語 2 つの種
        "conn_graph": _conn_graph,
        "synapse_table": _synapse_table,
        # table(列名 → 配列)の種。segcompare の配線 op が読む {pre, post} の座標表にしてある ——
        # 他の table を受ける op(graph_edge_consensus 等)は列名を見て断るので、嘘にはならない。
        "table": lambda rng: {"pre": rng.uniform(0, 32, (12, 2)), "post": rng.uniform(0, 32, (12, 2))},
        "points": _points,
        "image2d": lambda rng: rng.random((32, 32)),
        "depth": lambda rng: 1.0 + rng.random((32, 32)),
        "images": lambda rng: [rng.random((32, 32)) for _ in range(4)],
        "normals": lambda rng: (lambda v: v / np.linalg.norm(v, axis=1, keepdims=True))(
            rng.standard_normal((160, 3))),
        "signal": lambda rng: np.sin(np.linspace(0, 8 * np.pi, 256)) + 0.1 * rng.standard_normal(256),
        # 事象の位置(点過程)—— point_spectrum の入口。★**一様乱数だけにしない**:
        # 周期成分が無いと「周期を見つける op」の意味のある挙動を一度も踏まないので、
        # 周期 17.0 の列に 12 個の無関係な事象を混ぜた**構造データ**を種にする
        # (乱数だけの試験は構造の欠陥を隠す、というこの repo の規律)。
        "positions": lambda rng: np.sort(np.concatenate([
            np.arange(3.0, 200.0, 17.0)
            + rng.normal(0.0, 0.4, np.arange(3.0, 200.0, 17.0).size),
            rng.uniform(0.0, 200.0, 12)])),
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
        # coordgrid の種。産出 op(grid_coords)も台帳にあるが、種が無いと
        # sphere_sdf/box_sdf は「同じ連鎖で先に grid_coords が引かれた場合だけ」
        # 到達する状態になる。
        "coordgrid": lambda rng: __import__("sdf_ops").grid_coords(
            ((0.0, 10.0),) * 3, 16)[0],
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
        # volseq(2026-09-21): live4d の 8 op が受ける。既知の半径則で拍動する小さな殻(真値つきの前方モデル)。
        "volseq": lambda rng: __import__("live4d").volseq_synth_beating(
            (8, 12, 12), n_frames=8, period=8.0, amplitude=float(rng.uniform(0.2, 0.8)), radius=3.5),
        # rgbvideo(2026-09-21): これまで産む op(points_activity_video)だけで受ける op が無かった。
        # videocube.video_write_gif が受けるので種を置く(小さな色動画、[0, 1])。
        "rgbvideo": lambda rng: np.clip(rng.random((3, 12, 12, 3)), 0.0, 1.0),
        # volume(2026-10-01): 同じ露光で撮った画像の積み重ね (L, M, N)。sensorchar.emva_spatial_nonuniformity が 2 本受けるが、
        # カタログに volume を産む op が無く型の到達可能性で blocked になった。暗画像らしい小さな整数の積み重ねにする
        "volume": lambda rng: 40.0 + rng.poisson(float(rng.uniform(2.0, 30.0)), (4, 12, 12)).astype(np.float64),
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
        # labels は **2-D 画像と 3-D volume の 2 種を混ぜる**。既存 7 producers は
        # 3-D (D,H,W) か 1-D (N,) しか産まず**2-D のラベル画像を産む op が 1 つも
        # 無い**(実測)ので 2-D の種は必須。一方 3-D を種に置かないと
        # vol_region_props(3-D 要求)が「同じ連鎖で先に vol_label が引かれた場合
        # だけ」到達する — 詳細は _labels の docstring
        "labels": _labels,
        # --- 2026-09-02 に登録した 9 台帳の入口型の種 -----------------------
        # 種が無いと、その型を要求する op は**永久に走らない**。実測: 台帳を
        # 登録した直後は annotate 3/25・gfx2d 6/32・tomography 8/17 しか到達
        # しなかった。ここが「発見ゼロが未実行の偽装だった」の一番よくある入口。
        # 構造の要る型は**実体を通して作る**(手で組むと相関や不変量が実物と
        # 違う種になり、下流の検査が別の物を測ってしまう)。
        # mask は **産む op も種も無かった**(2026-09-02、`test_every_declared_
        # type_has_a_producer_or_a_seed` が検出)。そのため overlay_mask と
        # poisson_blend は永久に実行されない状態だった。中央に穴を開けない
        # 連結領域にする —— poisson_blend は「マスクが縁に接していたら拒否」
        # なので、縁から離すのが実際に走らせる条件。
        "mask": lambda rng: (lambda m: (m.__setitem__(
            (slice(6, 26), slice(8, 24)), True), m)[1])(np.zeros((32, 32), bool)),
        # labels2d(2026-09-06、blob 族)—— **実体 `blob_label` を通して作る**。
        # 手で番号を振ると「連番で歯抜けが無い」という族の約束を種のほうが
        # 破りかねず、下流の検査が別の物を測る。物体は**わざと 3 つとも形を
        # 変える**(四角・細長い棒・穴あきの輪)—— 同じ形を 3 つ並べた種だと
        # circularity も solidity も holes も全部同じ値になり、「どのノブでも
        # 同じ数が返る op」を見逃す。
        "labels2d": lambda rng: __import__("blob2d").blob_label(
            (lambda m: (m.__setitem__((slice(2, 10), slice(2, 10)), True),
                        m.__setitem__((slice(4, 8), slice(4, 8)), False),
                        m.__setitem__((slice(14, 17), slice(3, 20)), True),
                        m.__setitem__((slice(20, 30), slice(20, 30)), True),
                        m)[-1])(np.zeros((32, 32), bool))),
        "rgb": lambda rng: rng.random((24, 32, 3)),
        # ここに二度目の "rgbimage" があった —— 上の二色性レンダ(意図つき)を
        # 一様乱数で**黙って上書き**しており、鏡面分離系の op が
        # 「ランク 1 の条件を満たさない」で永久に拒否されていた。
        # 辞書は後勝ちなので、先に書いた意図が消える(ruff F601 が検出)。
        "rgba": lambda rng: rng.random((24, 32, 4)),
        "rgba_premul": lambda rng: (lambda a: np.concatenate(
            [rng.random((24, 32, 3)) * a, a], axis=-1))(rng.random((24, 32, 1))),
        "rgbvolume": lambda rng: rng.random((8, 16, 16, 3)),
        "sprites": lambda rng: [rng.random((8, 8, 4)) for _ in range(3)],
        "lut": lambda rng: rng.random((17, 17, 17, 3)),
        "text": lambda rng: "ラベル " + str(int(rng.integers(0, 100))),
        # axes は annotate の 5 op が要求する。実体を通して作る(rect と
        # xlim/ylim の整合が取れていないと、下流が「軸の外」で fail-closed する)
        "axes": lambda rng: __import__("annotate").axes_transform(
            (8, 8, 100, 80), (0.0, 10.0), (0.0, 5.0)),
        "entries": lambda rng: [("right", (0.3, 0.7, 0.9)), ("wrong", (0.8, 0.4, 0.1))],
        # 断層: sinogram = (角度, 検出器)。**アーチファクトを含む**もの
        # (まれに強い筋)を混ぜる ―― きれいな正弦波だけだと、実データで効く
        # はずの補正 op が「何もしなくても良い」入力しか見ない
        "sinogram": lambda rng: (lambda s: np.where(rng.random(s.shape) < 0.02, s * 6.0, s))(
            np.abs(np.sin(np.linspace(0, np.pi, 60))[:, None] * np.hanning(64)[None, :]) * 100.0
            + rng.random((60, 64))),
        "sinostack": lambda rng: np.stack(
            [np.abs(np.sin(np.linspace(0, np.pi, 40))[:, None] * np.hanning(48)[None, :]) * 100.0
             + rng.random((40, 48)) for _ in range(3)]),
        # lab / metrics / transport_plan / phash / fingerprint は実体から作る
        "lab": lambda rng: __import__("imgmetrics").rgb_to_lab(rng.random((24, 32, 3))),
        "metrics": lambda rng: (lambda M, a: M.compare_images(a, np.clip(a + 0.02, 0, 1)))(
            __import__("imgmetrics"), rng.random((32, 32))),
        "transport_plan": lambda rng: __import__("colortransport").transport_plan_1d(
            rng.random(12), rng.random(9)),
        "phash": lambda rng: __import__("imgforensics").perceptual_hash(rng.random((32, 32))),
        "fingerprint": lambda rng: __import__("imgforensics").sensor_fingerprint(
            [rng.random((32, 32)) * 0.4 + 0.3 for _ in range(4)]),
    }


#: 必須スカラ引数の名前 → 値サンプラ(署名 introspection で束縛)

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


def _b_render_lens(pool, rng):
    """lensimage.render_through_lens(image2d, table): 2 入力なので jones_apply と
    同じ理由(生成元 lens_system と消費側が同一連鎖に並ぶ確率 ~0.03%)で、
    半分は example_system の妥当な処方(実経路)、半分は pool の table(敵対
    入力 → ValueError)。list を返して残り(pixel_pitch_um 等)は既定値に任せる。"""
    imgs = pool.get("image2d") or []
    if not imgs:
        return None
    img = imgs[int(rng.integers(len(imgs)))]
    if rng.random() < 0.5:
        tables = pool.get("table") or []
        if tables:
            return [img, tables[int(rng.integers(len(tables)))]]
    import raytrace
    return [img, raytrace.example_system(str(rng.choice(["singlet", "doublet", "paraboloid"])))]


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


def _b_mesh_pair():
    """(V, F, V2, F2) を取る op(meshres.mesh_reduction_report)用 builder。

    2 つの ``mesh`` 種を 4 位置引数へ割る。プールに 1 つしか無ければ同じ
    メッシュを 2 度渡す(= 何も失っていない reduction の監査、誤差 0 の
    正当な入力)。
    """
    def build(pool, rng):
        meshes = [m for m in (pool.get("mesh") or [])
                  if isinstance(m, (tuple, list)) and len(m) >= 2]
        if not meshes:
            return None
        m1 = meshes[int(rng.integers(len(meshes)))]
        m2 = meshes[int(rng.integers(len(meshes)))]
        return [m1[0], m1[1], m2[0], m2[1]]
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


# --------------------------------------------------------------------------- #
# 2026-09-02: 狙い撃ちの網羅パス(--cover-all)で「必須引数が組めない」と挙がった  #
# 58 op のためのビルダー。ランダム歩行はこれらに一度も届いていなかったので、    #
# **束縛に失敗していること自体がこれまで観測されていなかった**。                #
#                                                                             #
# ここで分かったのは、そのうち何件かは台帳の ``in`` 宣言が実際のシグネチャと    #
# 合っていない、ということ ―― 例えば ``triangulate`` は台帳が                   #
# ``["image2d","image2d"]`` と言うのに実体は ``(pts1, pts2, P1, P2)`` で 2-D の  #
# 点集合を取る。**一度も実行されないので誰も気づけなかった**型の誤りである。    #
# 台帳を直すと進化エンジンの型グラフと docs の「次に繋がる op」まで動くため、    #
# ここではまずビルダーで**正しい呼び方**を固定し、走らせて挙動を見る。          #
# --------------------------------------------------------------------------- #
_K32 = np.array([[32.0, 0.0, 16.0], [0.0, 32.0, 16.0], [0.0, 0.0, 1.0]])


def _b_pose_error(pool, rng):
    """pose は ``(R, t)`` の組。台帳の ``["pose","pose"]`` を素直に割ると
    ``R_est`` に組がまるごと入り、4 引数を 2 個で埋めようとして必ず落ちる。"""
    ps = pool.get("pose")
    if not ps:
        return None
    r1, t1 = ps[rng.integers(len(ps))]
    r2, t2 = ps[rng.integers(len(ps))]
    return ([r1, t1, r2, t2], {})


def _b_normal_consistency(pool, rng):
    """``(points_a, normals_a, points_b, normals_b)`` の 4 データ引数。台帳は
    2 つしか宣言していない。**法線の行数は点数と一致していなければならない**
    (別点群の法線を混ぜると近傍 index が範囲外になる)ので同じ長さで揃える。"""
    pts, nrm = pool.get("points"), pool.get("normals")
    if not pts or not nrm:
        return None
    a, b = pts[rng.integers(len(pts))], pts[rng.integers(len(pts))]
    na, nb = nrm[rng.integers(len(nrm))], nrm[rng.integers(len(nrm))]
    n = min(len(a), len(na))
    m = min(len(b), len(nb))
    return ([a[:n], na[:n], b[:m], nb[:m]], {})


def _b_triangulate(pool, rng):
    """``(pts1, pts2, P1, P2)``。P は 3x4 の射影行列で、左右に 1 だけ離した
    ステレオ対にする(視差が出ない配置だと三角測量が退化する)。"""
    kp = pool.get("keypoints")
    if not kp:
        return None
    p1 = _K32 @ np.hstack([np.eye(3), np.zeros((3, 1))])
    p2 = _K32 @ np.hstack([np.eye(3), np.array([[-1.0], [0.0], [0.0]])])
    return ([kp[rng.integers(len(kp))], kp[rng.integers(len(kp))], p1, p2], {})


def _b_sampson(pool, rng):
    """``(F, pts1, pts2)``。F は上の左右ステレオと**同じ**外部標定から作る
    (``F = K^-T [t]_x R K^-1``、R=I, t=(-1,0,0))ので、幾何が整合する。"""
    kp = pool.get("keypoints")
    if not kp:
        return None
    ki = np.linalg.inv(_K32)
    tx = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, -1.0, 0.0]])
    f = ki.T @ tx @ ki
    return ([f, kp[rng.integers(len(kp))], kp[rng.integers(len(kp))]], {})


def _b_bundle(pool, rng):
    """``(cameras, points, obs_cam, obs_pt, obs_uv, K)``。観測は **この族自身の
    順投影 ``project`` で作る** —— 手で組むと (rvec|t) の並びや符号の約束を
    取り違えても分からず、「op が壊れている」のか「入力が違う」のかが
    切り分けられなくなる。カメラは点群 [0,10]^3 が必ず前方に来る位置へ置く。"""
    pts = pool.get("points")
    if not pts:
        return None
    import ops3d
    proj = ops3d.OPS3D["project"]["func"]
    p = np.asarray(pts[rng.integers(len(pts))])[:20]
    if len(p) < 4:
        return None
    cams = np.array([[0.0, 0.0, 0.0, -5.0, -5.0, 20.0],
                     [0.0, 0.0, 0.0, -3.0, -5.0, 20.0]])
    oc, op_, uv = [], [], []
    for ci, c in enumerate(cams):
        try:
            q = proj(p, c[:3], c[3:], _K32)
        except Exception:                      # noqa: BLE001 — 種作りの失敗は skip
            return None
        for pi in range(len(p)):
            oc.append(ci)
            op_.append(pi)
            uv.append(q[pi])
    return ([cams, p], {"obs_cam": np.asarray(oc), "obs_pt": np.asarray(op_),
                        "obs_uv": np.asarray(uv, dtype=float), "K": _K32})


def _b_pose_graph(pool, rng):
    """``(poses, edges)``。edges は ``(i, j, rvec_ij, t_ij, w_r, w_t)`` の列で、
    **相対姿勢はこの族自身の ``relative_pose`` から作る**(理由は _b_bundle と
    同じ)。輪にして最後を先頭へ戻すとループ閉じになる。"""
    import pose_graph as pg
    n = 5
    poses = np.zeros((n, 6))
    for i in range(n):
        poses[i, 2] = 0.15 * i                 # z 軸まわりに少しずつ回す
        poses[i, 3] = 2.0 * i                  # 並進もドリフトさせる
    edges = [(i, (i + 1) % n) + tuple(pg.relative_pose(poses[i], poses[(i + 1) % n]))
             + (1.0, 1.0) for i in range(n)]
    return ([poses, edges], {})


def _b_query_distance(pool, rng):
    """``(esdf_grid, bounds, res, query_points)``。台帳の ``["sdf","points"]`` を
    素直に割ると **bounds に点群が入る**(第 2 引数が bounds なので)。"""
    sdf, pts = pool.get("sdf"), pool.get("points")
    if not sdf or not pts:
        return None
    g = np.asarray(sdf[rng.integers(len(sdf))])
    if g.ndim != 3 or len(set(g.shape)) != 1:
        return None
    return ([g], {"bounds": ((0.0, 10.0), (0.0, 10.0), (0.0, 10.0)), "res": g.shape[0],
                  "query_points": np.asarray(pts[rng.integers(len(pts))])[:32]})


def _b_integrate(pool, rng):
    """``(tsdf, weight, depth, K, R, t, trunc)``。tsdf と weight は**同じ形**で
    なければならないので、weight は tsdf から作る(プールから拾うと形が合わない)。
    この op は in-place で書き換えて ``None`` を返す。"""
    sdf, dep = pool.get("sdf"), pool.get("depth")
    if not sdf or not dep:
        return None
    g = np.array(sdf[rng.integers(len(sdf))], dtype=float)
    if g.ndim != 3 or len(set(g.shape)) != 1:
        return None
    return ([g, np.zeros_like(g), np.asarray(dep[rng.integers(len(dep))], dtype=float)],
            {"K": _K32, "R": np.eye(3), "t": np.array([-5.0, -5.0, 20.0]),
             "trunc": 0.5, "bounds": ((0.0, 10.0), (0.0, 10.0), (0.0, 10.0))})


def _b_shot(pool, rng):
    """``(points, normals, kp_idx, tree, radius)``。tree は点群から作る KD 木で、
    **点群と同じものから作らないと近傍 index が別の点を指す**。"""
    pts, nrm = pool.get("points"), pool.get("normals")
    if not pts or not nrm:
        return None
    from scipy.spatial import cKDTree
    p = np.asarray(pts[rng.integers(len(pts))])
    n = np.asarray(nrm[rng.integers(len(nrm))])
    m = min(len(p), len(n))
    if m < 8:
        return None
    p, n = p[:m], n[:m]
    # ★ 非有限が混じった点群は **KD 木の構築そのものが生の ValueError で落ちる**
    #   (scipy: "data must be finite")。プールは NONFINITE を記録したうえで値を
    #   残す設計なので、汚れた点群がここへ来るのは想定内 —— 建てる側が防ぐ。
    #   2026-09-06 に実際に踏んだ: 新しい族が増えて連鎖の歩き方が変わり、
    #   seed 3_000_0xx でこの経路に当たってファザー自身が停止した(op の欠陥では
    #   なく**道具の欠陥**。束縛できない入力は例外ではなくスキップが約束)。
    if not (np.all(np.isfinite(p)) and np.all(np.isfinite(n))):
        return None
    return ([p, n, [0, 1, 2], cKDTree(p)], {"radius": 2.0})


def _b_leader_line(pool, rng):
    """``(img, anchor_xy, target_xy, text=...)``。台帳の ``["image2d","text"]`` を
    素直に割ると **anchor_xy に文字列が入る**(第 2 引数が座標なので)。"""
    img, txt = pool.get("image2d"), pool.get("text")
    if not img:
        return None
    return ([np.asarray(img[rng.integers(len(img))])],
            {"anchor_xy": (8.0, 8.0), "target_xy": (24.0, 22.0),
             "text": txt[rng.integers(len(txt))] if txt else None})


def _b_tilemap(pool, rng):
    """``(tiles, indices)``。indices は**タイル枚数の範囲に収まる**整数の 2-D 配列。
    範囲外だと描く前に落ちるので、プールの枚数から作る。"""
    sp = pool.get("sprites")
    if not sp:
        return None
    tiles = sp[rng.integers(len(sp))]
    k = len(tiles)
    if k < 1:
        return None
    return ([tiles], {"indices": np.arange(4).reshape(2, 2) % k})


def _b_parallax(pool, rng):
    """``(layers, camera_x, factors)``。factors は**層と同じ本数**でなければ
    ならない(手前ほど速く動く = 1.0 に近づける)。"""
    sp = pool.get("sprites")
    if not sp:
        return None
    layers = sp[rng.integers(len(sp))]
    k = len(layers)
    if k < 1:
        return None
    return ([layers], {"camera_x": 8.0,
                       "factors": tuple(np.linspace(0.25, 1.0, k))})


# --------------------------------------------------------------------------- #
# 2026-09-02(第 2 波): 「呼べたが毎回拒否された」68 op を減らす                 #
# --------------------------------------------------------------------------- #
# 網羅パスで **fn を呼べた 706 / 値を返せた 638** と分かれた。差の 68 は
# 「実行された」の数には入るが一度も成功していない = 実質は未実行に近い。
# 内訳を 1 件ずつ読むと大半が**入力の寸法**の話で、op 側は正しく門前払いして
# いた(例: 32x32 の絵に 100px の座標枠は入らない)。ここは種を op の要求に
# 合わせて直す。逆に**台帳の宣言が実際と違う**ものも混ざっていたので、
# それは builder で正しい呼び方を固定する(triangulate と同じ形)。
def _canvas(rng, pool, h=192, w=256):
    """プールの 32x32 を整数倍に引き伸ばした描画用キャンバス。

    annotate / gfx2d の描画 op は**文字や目盛りが物理的に収まる大きさ**を要求
    する。32x32 では text_box が 55px、legend_box が 111px はみ出して必ず
    fail-closed になり、13 op が「実行はされるが一度も描かない」状態だった。
    新しい絵を作らず既存プールを拡大するのは、下流に流れる値の素性を
    プール由来のまま保つため。
    """
    src = pool.get("image2d")
    if not src:
        return None
    a = np.asarray(src[rng.integers(len(src))], dtype=float)
    if a.ndim != 2 or a.shape[0] < 1 or a.shape[1] < 1:
        return None
    return np.kron(a, np.ones((max(1, h // a.shape[0]), max(1, w // a.shape[1]))))


def _b_draw(ins, **special):
    """描画 op 用: *ins* の各型を組み立て、``image2d`` はキャンバスに置き換える。"""
    def build(pool, rng):
        args = []
        for t in ins:
            if t in special:
                v = special[t](rng, pool)
                if v is None:
                    return None
                args.append(v)
                continue
            if t == "image2d":
                c = _canvas(rng, pool)
                if c is None:
                    return None
                args.append(c)
                continue
            src = pool.get(t)
            if not src:
                return None
            args.append(src[rng.integers(len(src))])
        return args
    return build


#: color_bar の ``lut`` は **(n>=2, 3) のカラーマップ**だが、プールの ``lut`` 型は
#: 3-D の色変換 LUT (17,17,17,3) —— 同じ名前で別物。型では防げないので op で狙う。
def _colormap(rng, pool):
    t = np.linspace(0.0, 1.0, 256)[:, None]
    return np.hstack([t, 1.0 - t, np.full_like(t, 0.5)])


def _labels_for_canvas(rng, pool):
    """キャンバスと**同じ形**のラベル画像。形が違うと overlay_labels は必ず拒否。"""
    lab = np.zeros((192, 256), dtype=np.int32)
    lab[40:100, 50:140] = 1
    lab[120:170, 160:230] = 2
    return lab


def _points_for_canvas(rng, pool):
    """キャンバスの内側に十分な余白を持つ点(ラベルの置き場所が残る配置)。"""
    return np.array([[60.0, 60.0], [180.0, 90.0], [110.0, 150.0]])


def _b_panels(pool, rng):
    """``panel_grid(panels, ...)`` は**画像の並び**を取る。台帳は ``['image2d']`` と
    宣言しており、1 枚の (H,W) を渡すと**行ごとに 1 枚**と解釈されて
    「img は (H,W) か (H,W,C)、実際は (32,)」で必ず落ちていた。"""
    src = pool.get("images") or pool.get("image2d")
    if not src:
        return None
    v = src[rng.integers(len(src))]
    return ([[np.asarray(x, float) for x in v]] if isinstance(v, list)
            else [[np.asarray(v, float)] * 3], {})


def _b_particles(pool, rng):
    """``particle_step`` / ``particle_render`` は ``particle_emit`` が返す**粒子 dict**
    を取る。台帳の ``table``(list|dict)プールには任意の dict が入るので、
    実際には毎回「キーが違う」で拒否されていた。族の入口 op から作る。"""
    import gfx2d
    st = gfx2d.particle_emit(64, 0, origin=(128.0, 96.0), spread=40.0)
    return [st]


def _b_sorted_xy(n_extra):
    """``interp_*`` / ``poly_fit`` は **x が狭義単調増加**であることを要求する。
    ``signal`` プールは雑音つき正弦波なので順序がなく、必ず拒否されていた。"""
    def build(pool, rng):
        src = pool.get("signal")
        if not src:
            return None
        y = np.asarray(src[rng.integers(len(src))], dtype=float).ravel()
        if y.size < 4:
            return None
        x = np.linspace(0.0, 1.0, y.size)
        args = [x, y]
        if n_extra:                       # xq: 定義域の内側に取る(外挿で拒否されない)
            args.append(np.linspace(0.05, 0.95, 16))
        return args
    return build


def _b_two_view_pts(with_k):
    """``essential_8point`` / ``fundamental_8point`` / ``recover_pose`` は
    **(N,2) の対応点** を取るのに、台帳は ``['image2d','image2d']`` と宣言している。
    triangulate と同じ形の宣言ミスで、絵を渡すと「pts1 は (N,2)」で必ず拒否される。
    対応は既知の左右ステレオから作る(視差が無いと本質行列が退化する)。

    ``fundamental_8point`` だけは **内部標定を取らない**(F は較正不要)。最初は
    3 つとも ``K1`` を渡してしまい、素の ``TypeError`` になった —— 幾何の意味を
    型でなく引数名で確かめるべき場所だった。
    """
    def build(pool, rng):
        kp = pool.get("keypoints")
        if not kp:
            return None
        p1 = np.asarray(kp[rng.integers(len(kp))], dtype=float)
        if len(p1) < 8:
            return None
        p2 = p1 + np.array([1.5, 0.0])    # 水平視差 = 左右カメラ
        return ([p1, p2], {"K1": _K32}) if with_k else ([p1, p2], {})
    return build


def _b_square_matrix(shape):
    """``matrix`` プールは 2..12 の任意形。正方 / 3x3 / 2x2 を要求する op 用。"""
    def build(pool, rng):
        n, m = shape
        a = rng.standard_normal((n, m))
        if n == m == 3:                   # 回転行列(matrix_to_angle が要求する)
            th = float(rng.uniform(-np.pi, np.pi))
            c, s = np.cos(th), np.sin(th)
            a = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
        elif n == m == 2:                 # 回転 x 等方スケール
            th = float(rng.uniform(-np.pi, np.pi))
            k = float(rng.uniform(0.5, 2.0))
            c, s = np.cos(th) * k, np.sin(th) * k
            a = np.array([[c, -s], [s, c]])
        elif n == m:
            a = a + a.T                   # 対称化(mat_eigh は実対称を要求)
        return [a]
    return build


def _b_linear_system(pool, rng):
    """``mat_solve(a, b)`` は正方 a と長さの合う b。プールの組合せでは滅多に揃わない。"""
    n = int(rng.integers(3, 8))
    a = rng.standard_normal((n, n)) + n * np.eye(n)      # 十分に非特異
    return [a, rng.standard_normal(n)]


def _b_lstsq(pool, rng):
    """``mat_lstsq`` は m >= n(優決定)。プールの (2,6) 等では必ず拒否される。"""
    m = int(rng.integers(6, 14))
    n = int(rng.integers(2, 5))
    return [rng.standard_normal((m, n)), rng.standard_normal(m)]


def _b_watermark(with_bits):
    """透かしの容量は絵の大きさで決まる。32x32 は LL が (16,16) = **4 ビット**しか
    入らないので、既定の 8 ビットや 64 ビット列は必ず容量超過で拒否されていた。
    絵を大きくして、実際に埋め込める本数を渡す。"""
    def build(pool, rng):
        c = _canvas(rng, pool)
        if c is None:
            return None
        c = np.clip(c, 0.0, 1.0)
        # LL は level=1 で 1/2、容量はその 2x2 ブロック数 = (H/4) * (W/4)
        cap = (c.shape[0] // 4) * (c.shape[1] // 4)
        bits = (rng.integers(0, 2, size=min(64, cap))).astype(np.int64)
        return [c, bits] if with_bits else ([c], {"n_bits": int(bits.size)})
    return build


# --------------------------------------------------------------------------- #
# flyvision(ハエ視葉)の消費 6 op。どれも「形の噛み合う入力」が要る:
#   * fly_hex_resample / fly_hs_readout — 格子(table)を引数から作らないと、
#     プールの table には csi_design / fly_dsi の dict も混ざっており、格子を
#     取り違えて fail-closed(CONTRACT)になる。列数が格子と合う入力を組む。
#   * fly_dsi / fly_hs_readout — 必須引数(angles_deg / n_pref)に名前ヒントが
#     無いので、builder が無いと **一度も実行されない**(_bind_args が None)。
#   * fly_emd_response — signal プールは長さがまちまち(256 の正弦、格子サイズの
#     resample 出力…)で、2 本を一様に引くと長さ不一致で CONTRACT。同長の
#     位相ずれ正弦を組んで実 HR 経路を通す。
#   * fly_lgmd_eta / fly_tau_from_expansion — 接近物体の**単調膨張角**を組む。
#     素の signal(正弦)は theta'<=0 の区間で fly_tau が NaN を返し NONFINITE に
#     数えられるので、膨張だけの角度にして意味のある経路を通す。
def _b_fly_resample(pool, rng):
    fv = __import__("flyvision")
    lat = fv.fly_hex_lattice(radius=4, dphi_deg=4.63)
    img = rng.random((64, 64))
    return (img, lat), {"fov_deg": 120.0, "drho_deg": 8.23}


def _b_fly_emd(pool, rng):
    dt, tau = 0.001, 0.05
    f = 1.0 / (2.0 * np.pi * tau)
    t = np.arange(256) * dt
    a = np.cos(2.0 * np.pi * f * t)
    b = np.cos(2.0 * np.pi * f * t - 0.6)
    return (a, b), {"tau_s": tau, "dt_s": dt}


def _b_fly_lgmd(pool, rng):
    dt = 0.002
    t = np.arange(0.0, 0.98, dt)
    ttc = 1.0 - t
    theta = 2.0 * np.arctan(0.05 / ttc)
    return (theta, dt), {}


def _b_fly_tau(pool, rng):
    dt = 0.002
    t = np.arange(0.0, 0.95, dt)
    d = 1.0 - t
    theta = 2.0 * np.arcsin(np.clip(0.05 / d, 0.0, 0.999))
    return (theta, dt), {"shape": "sphere"}


def _b_fly_hs(pool, rng):
    fv = __import__("flyvision")
    lat = fv.fly_hex_lattice(radius=3, dphi_deg=4.63)
    n = lat["dirs"].shape[0]
    resp = np.abs(rng.standard_normal((4, n)))
    return (resp, lat, 2), {"el_min_deg": 0.0}


def _b_fly_dsi(pool, rng):
    nd = 8
    ang = np.linspace(0.0, 360.0, nd, endpoint=False)
    resp = np.abs(rng.standard_normal(nd))
    return (resp, ang), {}


# --- SPC(統計的工程管理)。形の制約(部分群 2..10 列 / 観測 m>=p+1)を満たす --- #
def _b_spc_xbar_r(pool, rng):
    return (rng.normal(10.0, 1.0, size=(20, 5)),), {}


def _b_spc_cusum(pool, rng):
    return (rng.normal(0.0, 1.0, size=50),), {"target": 0.0, "k": 0.5, "h": 5.0}


def _b_spc_ewma(pool, rng):
    return (rng.normal(0.0, 1.0, size=50),), {"target": 0.0, "lam": 0.2, "L": 3.0, "sigma": 1.0}


def _b_spc_capability(pool, rng):
    return (rng.normal(10.0, 1.0, size=200),), {"lsl": 6.0, "usl": 14.0}


def _b_spc_hotelling_t2(pool, rng):
    return (rng.normal(0.0, 1.0, size=(50, 3)),), {}


# --- MT 法。単位空間は「観測 >= 2」だけが制約(p+1 は要らない) --- #
def _b_spc_mt_unit_space(pool, rng):
    return (rng.normal(0.0, 1.0, size=(60, 4)),), {}


def _b_spc_mt_distance(pool, rng):
    # ★単位空間は渡さない(渡すなら 3 つ全部)。渡さない形は「データ自身から
    #   作る」訓練時の呼び方で、ファザーが最も広く回せる。
    return (rng.normal(0.0, 1.0, size=(60, 4)),), {"threshold": 3.0}


# --- 配線行列の不変量。正方の 0/1 行列(自己結合なし)。 --- #
# --- 文字領域。暗い棒 2 本の画像 / その SWT / 候補の矩形。 --- #
def _b_text_img(pool, rng):
    img = np.ones((48, 96))
    img[18:23, 8:40] = 0.0
    img[18:23, 50:82] = 0.0
    return (img,), {}


def _b_text_swt(pool, rng):
    import textregion
    return (textregion.swt_map(_b_text_img(pool, rng)[0][0])["swt"],), {}


def _b_text_boxes(pool, rng):
    return (np.array([[18, 8, 23, 40], [18, 50, 23, 82]]),), {"stroke_width": [5.0, 5.0]}


# --- OpenVX の素の口。U8 の段差つき画像 / その Sobel の S16 / 恒等表。 --- #
def _b_vx_u8(pool, rng):
    img = rng.integers(0, 256, (24, 32)).astype(np.uint8)
    img[6:14, 8:20] = 200
    return (img,), {}


def _b_vx_sobel(pool, rng):
    return _b_vx_u8(pool, rng)[0], {"border": "replicate"}


def _b_vx_grad(pool, rng):
    import vxcore
    g = vxcore.vx_sobel3x3(_b_vx_u8(pool, rng)[0][0], border="replicate")
    return (g["gx"], g["gy"]), {}


def _b_vx_phase(pool, rng):
    return _b_vx_grad(pool, rng)[0], {"mapping": "floor"}


def _b_vx_lut(pool, rng):
    return (_b_vx_u8(pool, rng)[0][0], (255 - np.arange(256)).astype(np.uint8)), {}


def _b_vx_hist(pool, rng):
    return _b_vx_u8(pool, rng)[0], {"num_bins": 16, "offset": 0, "range_": 256}


def _b_vx_nms(pool, rng):
    return _b_vx_u8(pool, rng)[0], {"window": 3}


def _b_vx_affine(pool, rng):
    a = float(rng.uniform(-0.5, 0.5))
    M = np.array([[np.cos(a), -np.sin(a), rng.uniform(-3, 3)], [np.sin(a), np.cos(a), rng.uniform(-3, 3)]])
    return (_b_vx_u8(pool, rng)[0][0], M), {"interpolation": "bilinear", "border": "constant"}


def _b_vx_persp(pool, rng):
    H = np.eye(3) + np.array([[0.0, 0.03, 1.0], [0.02, 0.0, -1.0], [0.001, 0.001, 0.0]])
    return (_b_vx_u8(pool, rng)[0][0], H), {"interpolation": "nearest", "border": "constant"}


def _b_vx_remap(pool, rng):
    img = _b_vx_u8(pool, rng)[0][0]
    yy, xx = np.mgrid[0:img.shape[0], 0:img.shape[1]].astype(np.float64)
    return (img, xx + 0.5 * np.sin(yy / 3.0), yy), {"interpolation": "bilinear", "border": "constant"}


def _b_vx_nonlinear(pool, rng):
    return (_b_vx_u8(pool, rng)[0][0], np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], bool)), {"function": "median", "border": "replicate"}


def _b_graph_adj(pool, rng):
    B = (rng.random((40, 40)) < 0.12).astype(int)
    np.fill_diagonal(B, 0)
    return (B,), {}


def _b_graph_null(pool, rng):
    B = (rng.random((40, 40)) < 0.12).astype(int)
    np.fill_diagonal(B, 0)
    return (B,), {"n_samples": 3, "swaps_per_edge": 2, "seed": 0}


def _b_graph_swap(pool, rng):
    B = (rng.random((40, 40)) < 0.12).astype(int)
    np.fill_diagonal(B, 0)
    return (B,), {"pairs": [(0, 1), (2, 3), (4, 5)]}


def _b_graph_consensus(pool, rng):
    # 3 個体、同じ 30 節点。核 + 個体ごとの揺らぎ(全員に在る辺が必ずある)。
    core = (rng.random((30, 30)) < 0.08)
    mats = {}
    for k in "abc":
        B = (core | (rng.random((30, 30)) < 0.05)).astype(int)
        np.fill_diagonal(B, 0)
        mats[k] = B
    return (mats,), {"ordered": True, "n_null": 2, "swaps_per_edge": 1}


_SWC_Y = "1 1 0 0 0 5 -1\n2 3 10 0 0 1 1\n3 3 20 0 0 1 2\n4 3 30 10 0 1 3\n5 3 30 -10 0 1 3\n"


def _b_tree_swc(pool, rng):
    return (_SWC_Y,), {}


def _b_tree_table(pool, rng):
    import treemorph
    return (treemorph.tree_from_swc(_SWC_Y),), {}


def _b_tree_labels(pool, rng):
    import treemorph
    t = treemorph.tree_from_swc(_SWC_Y)
    return (t, rng.integers(1, 4, len(t["id"]))), {}


def _b_physarum_graph(pool, rng):
    n = 5
    A = np.zeros((n * n, n * n))
    for r in range(n):
        for c in range(n):
            u = r * n + c
            if c + 1 < n:
                A[u, u + 1] = A[u + 1, u] = rng.uniform(0.5, 1.5)
            if r + 1 < n:
                A[u, u + n] = A[u + n, u] = rng.uniform(0.5, 1.5)
    return (A,), {"dt": 0.3, "max_iters": 600}


def _b_physarum_route(pool, rng):
    return (rng.uniform(0.5, 1.5, (8, 8)),), {"dt": 0.3, "max_iters": 600}


def _b_physarum_transport(pool, rng):
    (A,), _ = _b_physarum_graph(pool, rng)
    s = rng.uniform(0, 1, len(A))
    s -= s.mean()
    return (A, s), {"dt": 0.3, "max_iters": 600}


def _b_physarum_transport_image(pool, rng):
    return (rng.uniform(0, 1, (6, 7)), rng.uniform(0, 1, (6, 7))), {"dt": 0.3, "max_iters": 600}


def _b_car_poses(pool, rng):
    poses = np.array([[rng.uniform(-3, 3), rng.uniform(-3, 3), rng.uniform(-3.1, 3.1)],
                      [rng.uniform(-3, 3), rng.uniform(-3, 3), rng.uniform(-3.1, 3.1)]])
    return (poses,), {"radius": float(rng.uniform(0.5, 2.0)), "step": 0.1}


def _b_car_hybrid_astar(pool, rng):
    occ = np.zeros((16, 24), bool)
    occ[4:12, 12] = True                     # 途中に短い壁
    poses = np.array([[2.0, 8.0, 0.0], [22.0, 8.0, 0.0]])
    return (occ, poses), {"radius": 3.0, "cell": 1.0, "n_theta": 24, "max_expansions": 20000}


def _b_course_none(pool, rng):
    return (), {}


def _b_course_layout(pool, rng):
    import drivecourse as DC
    return ([DC.course_crank(), DC.course_s_curve()], [(0.0, 0.0, 0.0), (40.0, 0.0, 0.0)]), {}


def _b_course_grid(pool, rng):
    import drivecourse as DC
    return (DC.course_crank(),), {"cell": 0.5}


def _b_course_contains(pool, rng):
    import drivecourse as DC
    return (DC.course_crank(), rng.uniform(-5, 25, (40, 2))), {}


def _b_world_build(pool, rng):
    import drivecourse as DC
    return (DC.course_turnaround(),), {"props": [("cone", 2.0, 1.0, 0.0)]}


def _b_world_camera(pool, rng):
    import drivecourse as DC
    import driveworld as DW
    w = DW.world_build(DC.course_turnaround())
    return (w, DW.camera_pose((-3.0, 1.75, 1.4), (8.0, 1.75, 0.8)), DW.camera_intrinsics(60, 64, 40)), \
        {"width": 64, "height": 40}


def _b_load_asset(pool, rng):
    return ("cone",), {}


def _b_lidar_scan(pool, rng):
    import lidarsim as LS
    V = np.array([[-30.0, -30.0, -1.7], [30.0, -30.0, -1.7], [30.0, 30.0, -1.7], [-30.0, 30.0, -1.7],
                  [4.0, -1.0, -1.7], [6.0, -1.0, -1.7], [6.0, 1.0, -1.7], [4.0, 1.0, -1.7],
                  [4.0, -1.0, 0.3], [6.0, -1.0, 0.3], [6.0, 1.0, 0.3], [4.0, 1.0, 0.3]])
    F = np.array([[0, 1, 2], [0, 2, 3], [4, 5, 9], [4, 9, 8], [5, 6, 10], [5, 10, 9], [6, 7, 11], [6, 11, 10],
                  [7, 4, 8], [7, 8, 11], [8, 9, 10], [8, 10, 11]])
    spec = LS.lidar_spec(n_beams=8, v_fov_deg=(-20.0, 5.0), azimuth_res_deg=2.0, range_max=40.0)
    return (V, F, spec, np.eye(4)), {}


def _b_ray_plane(pool, rng):
    d = rng.normal(size=(20, 3))
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    return (np.zeros(3), d, (0.0, 0.0, 1.0, 1.7)), {}


def _b_ray_box(pool, rng):
    d = rng.normal(size=(20, 3))
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    return (np.zeros(3), d, (2.0, -1.0, -1.0, 4.0, 1.0, 1.0)), {}


def _b_world_move(pool, rng):
    import drivecourse as DC
    import driveworld as DW
    w = DW.world_build(DC.course_turnaround(), props=[("cone", 2.0, 1.0, 0.0)])
    i = [k for k, o in enumerate(w["objects"]) if o["name"] == "cone"][0]
    return (w, i, 3.0, 1.5, 0.4), {}


def _b_two_poses(pool, rng):
    import driveworld as DW
    return (DW.camera_pose((-3.0, 1.75, 1.4), (8.0, 1.75, 0.8)), DW.camera_pose((-2.2, 1.75, 1.4), (8.8, 1.75, 0.8))), {}


def _b_K_T(pool, rng):
    import driveworld as DW
    T = np.eye(4)
    T[2, 3] = 0.8
    return (DW.camera_intrinsics(60, 64, 40), T), {}


def _b_depth_K_T(pool, rng):
    import driveworld as DW
    T = np.eye(4)
    T[2, 3] = 0.8
    return (rng.uniform(5, 30, (40, 64)), DW.camera_intrinsics(60, 64, 40), T), {}


def _b_ttc_truth(pool, rng):
    (d, K, T), _ = _b_depth_K_T(pool, rng)
    return (d, K, T, 0.1), {}


def _b_ttc_flow(pool, rng):
    import drivettc as TT
    (d, K, T), _ = _b_depth_K_T(pool, rng)
    f = TT.flow_from_depth_motion(d, K, T)
    return (f["u"], f["v"], 0.1), {"foe": TT.foe_from_motion(K, T)}


def _b_ttc_scale(pool, rng):
    return (20.0, 22.0, 0.1), {}


def _b_ttc_range(pool, rng):
    return (20.0, 16.0), {}


def _b_label_extent(pool, rng):
    L = np.zeros((20, 24), int)
    L[4:9, 6:15] = 2
    return (L, 2), {}


def _b_rss_p(pool, rng):
    import rsssafety as RS
    return (RS.rss_params(),), {}


def _b_rss_stop(pool, rng):
    return (8.0, 1.0, 3.5, 4.0), {}


def _b_rss_two_v(pool, rng):
    import rsssafety as RS
    return (8.0, 2.0, RS.rss_params()), {}


def _b_rss_lat(pool, rng):
    import rsssafety as RS
    return (0.3, -0.2, RS.rss_params()), {}


def _b_rss_check(pool, rng):
    import rsssafety as RS
    return (20.0, 8.0, 2.0, RS.rss_params()), {}


def _b_rss_lat_check(pool, rng):
    import rsssafety as RS
    return (2.0, 0.3, -0.2, RS.rss_params()), {}


def _b_rss_worst(pool, rng):
    import rsssafety as RS
    return (30.0, 8.0, 2.0, RS.rss_params()), {"dt": 0.01}


def _b_rss_worst_lat(pool, rng):
    import rsssafety as RS
    return (2.0, 0.3, -0.2, RS.rss_params()), {"dt": 0.01}


def _b_xy_grid(pool, rng):
    X, Y = np.meshgrid(np.linspace(-5.0, 5.0, 12), np.linspace(-4.0, 4.0, 10))
    return (X, Y), {"seed": 3, "freq": 0.7}


def _b_fbm_p(pool, rng):
    return (0,), {"n_waves": 32}


def _b_seed_only(pool, rng):
    return (0,), {}


def _b_fbm_field(pool, rng):
    import driveterrain as DTR
    X, Y = np.meshgrid(np.linspace(-20.0, 20.0, 12), np.linspace(-16.0, 16.0, 10))
    return (X, Y, DTR.fbm_params(0, n_waves=32)), {}


def _b_field_dx(pool, rng):
    import driveterrain as DTR
    xs = np.arange(48) * 1.0
    X, Y = np.meshgrid(xs, xs)
    return (DTR.fbm_height(X, Y, DTR.fbm_params(0, n_waves=64, f_min=1 / 40.0, f_max=1 / 4.0)), 1.0), {}


def _b_slope(pool, rng):
    (Z, dx), _ = _b_field_dx(pool, rng)
    return (Z, dx, 1 / 20.0, 1 / 5.0), {"n_bins": 16}


def _b_course_xy(pool, rng):
    import drivecourse as DC
    return (DC.course_road(30.0, 7.0), rng.uniform(-10, 40, (50, 2))), {}


def _b_terrain_p(pool, rng):
    return (0,), {"n_waves": 32, "road_amp": 0.5}


def _b_terrain_field(pool, rng):
    import drivecourse as DC
    import driveterrain as DTR
    X, Y = np.meshgrid(np.linspace(-10.0, 40.0, 12), np.linspace(-10.0, 17.0, 10))
    return (X, Y, DTR.terrain_params(0, n_waves=32)), {"course": DC.course_road(30.0, 7.0)}


def _b_terrain_mesh(pool, rng):
    import drivecourse as DC
    import driveterrain as DTR
    return (DTR.terrain_params(0, n_waves=32), DC.course_road(30.0, 7.0), (-8.0, 38.0, -8.0, 15.0)), {"step": 4.0}


def _b_world_terrain(pool, rng):
    import drivecourse as DC
    import driveterrain as DTR
    import driveworld as DW
    w = DW.world_build(DC.course_road(30.0, 7.0), props=[("cone", 4.0, 3.5, 0.0)], ground_step=4.0)
    return (w, DTR.terrain_params(0, n_waves=32)), {"step": 4.0}


def _b_world_view(pool, rng):
    import drivecourse as DC
    import driveterrain as DTR
    import driveworld as DW
    w = DW.world_build(DC.course_road(30.0, 7.0), ground_step=4.0)
    DTR.world_apply_terrain(w, DTR.terrain_params(0, n_waves=32), step=4.0)
    K = DW.camera_intrinsics(60.0, 96, 60)
    P = DW.camera_pose((1.0, 3.5, 1.35), (21.0, 3.5, 0.9))
    return (w, DW.world_camera(w, P, K, 96, 60), P, K, DTR.material_params(0)), {}


def _b_tree(pool, rng):
    return (5.0, 0.15, 1.5), {"kind": "conifer"}


def _b_ped(pool, rng):
    return (1.7,), {}


def _b_crosswalk(pool, rng):
    return ((10.0, 0.0), (10.0, 7.0), 3.0), {}


def _b_add_mesh(pool, rng):
    import drivecourse as DC
    import driveterrain as DTR
    import driveworld as DW
    w = DW.world_build(DC.course_road(30.0, 7.0), ground_step=4.0)
    return (w, DTR.tree_mesh(5.0), 2.0, -4.0, 0.3), {"name": "tree"}


def _b_scatter(pool, rng):
    import drivecourse as DC
    return (DC.course_road(30.0, 7.0), (-10.0, 40.0, -10.0, 17.0)), {"n": 8, "r_min": 3.0, "margin": 2.0, "seed": 1}


def _b_mesh_vol(pool, rng):
    import driveterrain as DTR
    m = DTR.tree_mesh(5.0, 0.15, 1.5, "conifer")
    return (m["V"], m["F"]), {}


def _b_foe_flow(pool, rng):
    import drivettc as TT
    (d, K, T), _ = _b_depth_K_T(pool, rng)
    f = TT.flow_from_depth_motion(d, K, T)
    return (f["u"], f["v"]), {}


def _b_ball_bp(pool, rng):
    import ballistics as BL
    return BL.ball_params()


def _b_ball_ip(pool, rng):
    import ballistics as BL
    return BL.impact_params(0.9, 0.25)


def _b_flight_vac(pool, rng):
    return ((0.0, 0.0, 0.5), (3.0, 0.2, 1.0), np.linspace(0.0, 0.05, 6)), {}


def _b_flight_ode(pool, rng):
    return ((0.0, 0.0, 0.5), (3.0, 0.2, 1.0), (0.0, 200.0, 0.0), _b_ball_bp(pool, rng), 0.05), {"dt": 1e-3}


def _b_flight_sim(pool, rng):
    return ((0.0, 0.0, 0.02), (3.0, 0.2, -1.0), (0.0, 200.0, 0.0), _b_ball_bp(pool, rng), _b_ball_ip(pool, rng), 0.05), {"dt": 1e-3}


def _b_flight_state(pool, rng):
    return ((0.0, 0.0, 0.5), (3.0, 0.2, 1.0), (0.0, 200.0, 0.0), _b_ball_bp(pool, rng), 0.02), {"n_steps": 10}


def _b_spin_ratio(pool, rng):
    return (np.linspace(0.0, 0.5, 8),), {}


def _b_reynolds(pool, rng):
    return (np.geomspace(1e2, 1e5, 8),), {}


def _b_bounce(pool, rng):
    return ((5.0, -0.3, -2.6), (0.0, 240.0, 0.0), (0.0, 0.0, 1.0), _b_ball_bp(pool, rng), _b_ball_ip(pool, rng)), {}


def _b_contact_L(pool, rng):
    return ((5.0, -0.3, -2.6), (0.0, 240.0, 0.0), (0.0, 0.0, 1.0), _b_ball_bp(pool, rng)), {}


def _b_apex_seq(pool, rng):
    return (0.305, 0.9, 4), {}


def _b_bounce_time(pool, rng):
    return (0.305, 0.9), {}


def _b_apexes(pool, rng):
    import ballistics as BL
    return (BL.apex_sequence(0.305, 0.9, 4),), {}


def _b_intervals(pool, rng):
    return (np.array([0.0, 0.5, 0.95, 1.355]),), {}


def _b_t_p(pool, rng):
    import ballistics as BL
    t = np.linspace(0.0, 0.05, 6)
    return (t, BL.flight_vacuum((0.0, 0.0, 0.5), (3.0, 0.2, 1.0), t)), {}


def _b_flight_fit(pool, rng):
    (t, p), _ = _b_t_p(pool, rng)
    return (t, p, (0.0, 200.0, 0.0), _b_ball_bp(pool, rng)), {"iters": 2, "dt": 1e-3}


def _b_fit_spin(pool, rng):
    import ballistics as BL
    # 9 パラメータ(p0・v0・ω)は ≥ 10 標本が要る。回転ありの軌跡を渡す(回転なしでも走るが ω の列が弱い)
    bp = _b_ball_bp(pool, rng)
    f = BL.flight_ode((0.0, 0.0, 0.5), (8.0, 0.5, 2.0), (0.0, 200.0, 0.0), bp, 0.121, 1e-3)
    idx = np.arange(0, 120, 10)
    return (f["t"][idx], f["p"][idx], bp), {"iters": 2, "dt": 1e-3}


def _b_fit_aero(pool, rng):
    import ballistics as BL
    # 8 パラメータの同定は ≥ 8 標本が要り、真空の軌跡だと C_d・C_L の列が消えて cond = inf → 抗力 + マグヌスの軌跡を渡す
    bp = _b_ball_bp(pool, rng)
    f = BL.flight_ode((0.0, 0.0, 0.5), (8.0, 0.5, 2.0), (0.0, 200.0, 0.0), bp, 0.101, 1e-3)
    idx = np.arange(0, 100, 10)
    return (f["t"][idx], f["p"][idx], (0.0, 200.0, 0.0), bp), {"iters": 2, "dt": 1e-3}


def _b_fit_bounce(pool, rng):
    import ballistics as BL
    (v, w, n, bp, ip), _ = _b_bounce(pool, rng)
    b = BL.bounce(v, w, n, bp, ip)
    return (v, w, b["v"], b["omega"], n, bp), {}


def _b_slide(pool, rng):
    return (2.0, 0.3), {}


def _b_mu(pool, rng):
    return (0.3,), {}


def _b_mu_from_stop(pool, rng):
    return (2.0, 0.68), {}


def _b_roll_slide(pool, rng):
    return ((1.0, 0.0, 0.0), (0.0, 50.0, 0.0), (0.0, 0.0, 1.0), _b_ball_bp(pool, rng)), {}


def _b_tether(pool, rng):
    return ((0.3, 0.0, -0.2), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 0.4, 0.2), {"dt": 1e-3}


def _b_pendulum(pool, rng):
    return (0.4,), {}


def _b_cup(pool, rng):
    return ((0.0, 0.0, 0.03), (0.0, 0.0, -0.3), (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), 0.03, 0.02), {}


def _b_ball_img(pool, rng):
    rr, cc = np.mgrid[0:60, 0:96]
    img = 0.05 * rng.random((60, 96))
    img[(rr - 30.0) ** 2 + (cc - 48.0) ** 2 <= 4.0 ** 2] = 1.0
    return (img,), {"mode": "bright"}


def _b_ball_dets(pool, rng):
    dets = [[{"col": 40.0 + 3.0 * k, "row": 30.0 - 1.0 * k, "radius": 4.0, "area": 50, "fill": 0.9, "score": 6.4}]
            for k in range(4)]
    return (dets,), {"max_jump": 40.0}


def _b_kalman(pool, rng):
    import ballistics as BL
    t = np.arange(8) * 0.01
    return (BL.flight_vacuum((0.0, 0.0, 0.5), (3.0, 0.2, 1.0), t), 0.01), {"q": 1.0, "r": 1e-3}


def _b_ball_cam(pool, rng):
    import ballworld as BW
    return BW.camera_rig(BW.table_params(), n=2, width=96, height_px=60)


def _b_reproject(pool, rng):
    import ballworld as BW
    cam = _b_ball_cam(pool, rng)[0]
    H = BW.table_params()["height"]
    return (np.array([[0.0, 0.0, H + 0.2], [0.3, 0.1, H + 0.3], [-0.3, -0.1, H + 0.25]]), cam["pose"], cam["K"]), {}


def _b_tri_dlt(pool, rng):
    import ballworld as BW
    import balltrack as BT
    rig = _b_ball_cam(pool, rng)
    X = np.array([[0.2, 0.1, BW.table_params()["height"] + 0.25]])
    uvs = np.array([BT.reproject(X, c["pose"], c["K"])[0] for c in rig])
    return (uvs, np.array([c["pose"] for c in rig]), np.array([c["K"] for c in rig])), {}


def _b_track_tri(pool, rng):
    import ballworld as BW
    import balltrack as BT
    rig = _b_ball_cam(pool, rng)
    H = BW.table_params()["height"]
    X = np.array([[0.0, 0.0, H + 0.2], [0.1, 0.02, H + 0.25], [0.2, 0.04, H + 0.28]])
    tracks = []
    for c in rig:
        uv = BT.reproject(X, c["pose"], c["K"])
        tracks.append({"frame": np.arange(3), "col": uv[:, 0], "row": uv[:, 1], "radius": np.full(3, 4.0),
                       "found": np.ones(3, bool)})
    return (tracks, np.array([c["pose"] for c in rig]), np.array([c["K"] for c in rig]), 3), {}


def _b_bounce_det(pool, rng):
    t = np.arange(12) * 0.01
    return (t, 0.1 + np.abs(t - 0.05) * 2.0), {"min_gap": 2}


def _b_marker_dir(pool, rng):
    return ((50.0, 31.0), (48.0, 30.0), 4.0), {}


def _b_spin_markers(pool, rng):
    import ballworld as BW
    d0 = np.array([[0.0, 0.0, 1.0], [0.6, 0.0, 0.8], [0.0, 0.6, 0.8]])
    R = BW.rotation_from_omega((0.0, 50.0, 0.0), 1e-3)
    return (d0, d0 @ R.T, 1e-3), {}


def _b_spin_marker_seq(pool, rng):
    import ballworld as BW
    d = np.array([[0.0, 0.0, 1.0], [0.6, 0.0, 0.8], [0.0, 0.6, 0.8], [-0.5, 0.3, 0.81]])
    seq, R = [], np.eye(3)
    for _ in range(8):
        seq.append(d @ R.T)
        R = BW.rotation_from_omega((0.0, 50.0, 10.0), 1e-3) @ R
    return (seq, 1e-3), {}


def _b_table_world(pool, rng):
    import ballworld as BW
    return (BW.table_params(),), {}


def _b_icosphere(pool, rng):
    return (0.02, 1), {}


def _b_ball_mesh(pool, rng):
    return (0.02, 1), {}


def _b_add_ball(pool, rng):
    import ballworld as BW
    tp = BW.table_params()
    return (BW.table_world(tp), BW.ball_mesh(0.02, 1), (0.0, 0.0, tp["height"] + 0.2)), {}


def _b_ball_pose(pool, rng):
    import ballworld as BW
    (w, m, p), _ = _b_add_ball(pool, rng)
    i = BW.add_ball(w, m, p)
    return (w, i, (0.1, 0.0, p[2]), np.eye(3)), {}


def _b_rot_omega(pool, rng):
    return ((0.0, 50.0, 0.0), 1e-3), {}


def _b_cam_rig(pool, rng):
    import ballworld as BW
    return (BW.table_params(),), {"n": 2, "width": 96, "height_px": 60}


def _b_ball_truth(pool, rng):
    import ballworld as BW
    (w, m, p), _ = _b_add_ball(pool, rng)
    i = BW.add_ball(w, m, p)
    return (w, i, _b_ball_cam(pool, rng)[0]), {}


def _b_rp(pool, rng):
    import racket as RK
    return RK.racket_params()


def _b_racket_impact(pool, rng):
    return ((5.0, 0.0, -1.0), (0.0, 200.0, 0.0), (-1.0, 0.0, 0.0), (-2.0, 0.0, 0.0), _b_ball_bp(pool, rng), _b_rp(pool, rng)), {}


def _b_hit_check(pool, rng):
    return ((1.55, 0.02, 1.0), (1.55, 0.0, 1.0), (-1.0, 0.0, 0.0), _b_rp(pool, rng), 0.02), {}


def _b_aim(pool, rng):
    return ((-1.3, 0.0, 1.0), (0.75, 0.1, 0.76), 0.3, _b_ball_bp(pool, rng)), {"refine": 2, "dt": 1e-3}


def _b_racket_plan(pool, rng):
    return ((5.0, 0.0, -1.0), (0.0, 200.0, 0.0), (-4.0, 0.3, 1.5), _b_ball_bp(pool, rng), _b_rp(pool, rng)), {"refine": 2}


def _b_racket_move(pool, rng):
    return ((1.55, 0.0, 1.0), (0.0, 0.0, 0.0), (1.55, 0.2, 1.1), 0.01, _b_rp(pool, rng)), {}


def _b_strategy(pool, rng):
    import ballworld as BW
    ctx = {"opp_pos": np.array([1.55, 0.1, 1.0]), "shot_index": 1, "tp": BW.table_params(), "prev_target": (0.75, 0.05)}
    return (0, ctx, np.random.default_rng(0)), {}


def _b_shot_legal(pool, rng):
    import ballworld as BW
    tp = BW.table_params()
    return ((-1.3, 0.0, tp["height"] + 0.25), (5.0, 0.0, 1.5), (0.0, 0.0, 0.0), _b_ball_bp(pool, rng), _b_ball_ip(pool, rng), tp,
            1.55, 0), {}


def _b_rally(pool, rng):
    import ballworld as BW
    return (_b_ball_bp(pool, rng), _b_rp(pool, rng), BW.table_params()), {"max_hits": 2, "retries": 0, "seed": 0}


def _b_sign_kind(pool, rng):
    # 文字の無い種類(no_entry = 赤地に白の横棒)にして、フォントの有無で結果が変わらないようにする
    return ("no_entry",), {}


def _b_sign_img(pool, rng):
    return ("no_entry",), {"size_px": 64}


def _b_plate_mesh(pool, rng):
    import roadjp as RJ
    return (RJ.sign_image("no_entry", size_px=64), 0.6, 0.6), {"cell": 4}


def _b_sign_mesh(pool, rng):
    return ("no_entry",), {"size_px": 64}


def _b_add_sign(pool, rng):
    import driveworld as DW
    return (DW._empty_world(), "no_entry", 5.0, -4.0, 0.0), {"size_px": 64}


def _b_signal_jp(pool, rng):
    return (), {"state": "red"}


def _b_add_signal_jp(pool, rng):
    import driveworld as DW
    return (DW._empty_world(), 10.0, 0.0, 0.0), {"state": "red", "arm": 2.0}


def _b_kp(pool, rng):
    import kendama as KD
    return KD.kendama_params()


def _b_kp_vac(pool, rng):
    import kendama as KD
    return KD.kendama_params(rho=0.0)


def _b_kp_only(pool, rng):
    return (_b_kp(pool, rng),), {}


def _b_ellk(pool, rng):
    return (0.5,), {}


def _b_period_exact(pool, rng):
    return (0.39, 1.0), {}


def _b_launch_speed(pool, rng):
    return (1.0, 0.39), {}


def _b_rod(pool, rng):
    return (0.39, 1.0, 0.2), {"dt": 1e-3}


def _b_tension(pool, rng):
    return (1.0, 0.3, 0.39, 0.075), {}


def _b_slack_angle(pool, rng):
    return (2.0, 0.39), {}


def _b_ken_catch(pool, rng):
    kp = _b_kp(pool, rng)
    c = np.array([0.1, 0.2, 0.3])
    return (kp, c + np.array([0.0, 0.0, kp["cup_rest_height"]]), (0.0, 0.0, -0.1), c), {}


def _b_ken_sim(pool, rng):
    # 手元固定・真空・計画なしの 0.2 s(200 step): 張ったままの振り子(ballistics.tether_simulate と同じ軌跡)
    kp = _b_kp_vac(pool, rng)
    L = kp["string"]
    return (kp, (0.0, 0.0, 0.0)), {"p0": (0.0, 0.0, -L), "v0": (1.0, 0.0, 0.0), "t_end": 0.2, "dt": 1e-3}


def _b_perceiver(pool, rng):
    return (np.random.default_rng(0), 0.01, 0.0), {}


def _b_success(pool, rng):
    return (_b_kp(pool, rng),), {"n": 1, "seed": 0, "t_end": 0.6}


def _b_ken_mesh(pool, rng):
    return (_b_kp(pool, rng),), {}


def _b_add_ken(pool, rng):
    import driveworld as DW
    import kendamaworld as KW
    return (DW._empty_world(), KW.ken_mesh(_b_kp(pool, rng)), (0.0, 0.0, 1.0)), {}


def _b_ken_pose(pool, rng):
    import kendamaworld as KW
    (w, m, p), _ = _b_add_ken(pool, rng)
    i = KW.add_ken(w, m, p)
    return (w, i, (0.05, 0.0, 1.1), np.eye(3)), {}


def _b_string_mesh(pool, rng):
    return ((0.0, 0.0, 0.6), (0.0, 0.0, 1.0)), {}


def _b_add_string(pool, rng):
    import driveworld as DW
    return (DW._empty_world(), (0.0, 0.0, 0.6), (0.0, 0.0, 1.0)), {}


def _b_string_set(pool, rng):
    import kendamaworld as KW
    (w, a, b), _ = _b_add_string(pool, rng)
    i = KW.add_string(w, a, b)
    return (w, i, (0.2, 0.1, 0.7), (0.0, 0.0, 1.0)), {}


def _b_ken_world(pool, rng):
    return (_b_kp(pool, rng),), {"subdiv": 1}


def _b_ken_rig(pool, rng):
    return (_b_kp(pool, rng),), {"n": 2, "width": 96, "height_px": 60}


def _b_ken_truth(pool, rng):
    import kendamaworld as KW
    kp = _b_kp(pool, rng)
    w = KW.kendama_world(kp, subdiv=1)
    return (w, w["kendama"]["ken"], KW.kendama_rig(kp, n=2, width=96, height_px=60)[0]), {}


def _b_staged(pool, rng):
    return (_b_kp(pool, rng),), {}


def _b_parabola_g(pool, rng):
    t = np.linspace(0.0, 0.07, 8)
    P = np.array([0.1, -0.2, 1.1]) + np.outer(t, [0.3, -0.1, 2.0]) - np.outer(4.905 * t * t, [0.0, 0.0, 1.0])
    return (t, P), {}


def _b_hole_img(pool, rng):
    rr, cc = np.mgrid[0:60, 0:60]
    img = np.full((60, 60, 3), 0.6)
    img[(rr - 30.0) ** 2 + (cc - 30.0) ** 2 <= 20.0 ** 2] = (1.0, 0.55, 0.05)
    img[(rr - 34.0) ** 2 + (cc - 36.0) ** 2 <= 5.0 ** 2] = (0.10, 0.06, 0.03)
    return (img, (30.0, 30.0), 20.0), {}


def _b_kendama_pose(pool, rng):
    import kendamaworld as KW
    kp = _b_kp(pool, rng)
    w = KW.kendama_world(kp, subdiv=1)
    return (w, (0.0, 0.0, 1.0), (0.05, -0.013, 0.7)), {}


def _b_ken_clear(pool, rng):
    return (_b_kp(pool, rng), (0.0, 0.0, 1.0), [(0.0, 0.0, 1.2), (0.0, 0.3, 1.0)]), {}


def _b_cam_perceiver(pool, rng):
    import kendamaworld as KW
    kp = _b_kp(pool, rng)
    w = KW.kendama_world(kp, subdiv=1)
    return (w, KW.kendama_rig(kp, n=2, width=96, height_px=72)), {"fps": 50.0, "window": 32}


def _b_kendama_combo(pool, rng):
    return (_b_kp(pool, rng),), {"n_catch": 1, "hand0": (0.0, 0.0, 1.1)}


def _long_road():
    import drivelong as DL
    return DL.road_profile([(0.0, 0.0), (20.0, 0.0), (40.0, 1.6), (44.0, 1.6)])


def _b_long_params(pool, rng):
    return (), {}


def _b_road_profile(pool, rng):
    return ([(0.0, 0.0), (20.0, 0.0), (40.0, 1.6), (44.0, 1.6)],), {}


def _b_road_eval(pool, rng):
    return (_long_road(), 25.0), {}


def _b_long_simulate(pool, rng):
    return (0.0, 5.0, lambda t, s, v: (0.0, 2.0)), {"t_end": 4.0, "dt": 0.05}


def _b_long_energy_residual(pool, rng):
    import drivelong as DL
    return (DL.long_simulate(0.0, 5.0, lambda t, s, v: (0.0, 2.0), t_end=4.0, dt=0.05),), {}


def _b_stopping_distance_grade(pool, rng):
    return (11.1, 0.75, 4.0), {"theta": 0.05}


def _b_stop_line_plan(pool, rng):
    return (5.5, 20.0), {}


def _b_plan_command(pool, rng):
    import drivelong as DL
    return (DL.stop_line_plan(5.5, 20.0),), {}


def _b_hill_hold_brake_min(pool, rng):
    return (0.08,), {}


def _b_hill_start_rollback(pool, rng):
    return (0.08, 1.0, 2.0), {}


def _b_hill_start_command(pool, rng):
    return (1.0, 1.0, 2.0, 1.0), {}


def _b_skill_test_thresholds(pool, rng):
    return (), {}


def _b_skill_test_score(pool, rng):
    return ([{"kind": "stop", "gap": 0.5}, {"kind": "start", "rollback": 0.1}],), {}


def _inf_tp():
    import driveinf as DI
    return DI.tile_params(tile=100.0, cells=4)


def _b_tile_hash(pool, rng):
    return (3, -4, 20261001), {"salt": 1}


def _b_pose_normalize(pool, rng):
    return (5, 2, 205.0, -3.0, 200.0), {}


def _b_tile_params(pool, rng):
    return (), {"tile": 100.0, "cells": 4}


def _b_tile_edge(pool, rng):
    return (0, 0, "E", _inf_tp()), {}


def _b_tile_ij(pool, rng):
    return (1, 2, _inf_tp()), {}


def _b_tile_xy(pool, rng):
    import numpy as np
    return (1, 2, np.array([10.0, 50.0, 99.0]), np.array([5.0, 50.0, 100.0]), _inf_tp()), {}


def _b_tile_mesh(pool, rng):
    return (1, 2, _inf_tp()), {"step": 20.0}


def _b_tile_digest(pool, rng):
    import driveinf as DI
    return (DI.tile_mesh(0, 0, _inf_tp(), step=20.0),), {}


def _b_tile_stream(pool, rng):
    return ({}, 0, 0, _inf_tp()), {"radius": 1, "step": 20.0}


def _b_global_to_tile(pool, rng):
    return (1234.5, -678.9, 200.0), {}


_TR_IDM = {"v0": 13.9, "T": 1.5, "a": 1.0, "b": 1.5, "s0": 2.0, "delta": 4.0}
_TR_BOX = (12.5, 2.5, 5.0, 2.0, 0.0)
_TR_PASS = (5.0, 3.0, 3.0, 8.0, 10.0)
_TR_BUS = {"bus_rear": 40.0, "bus_front": 52.0, "base": 0.002, "peak": 0.05, "spread": 4.0}


def _b_idm_accel(pool, rng):
    import numpy as np
    return (np.array([5.0, 10.0]), np.array([20.0, 30.0]), np.array([0.0, 1.0])), dict(_TR_IDM)


def _b_idm_gap(pool, rng):
    import numpy as np
    return (np.array([0.0, 5.0, 10.0]),), {k: _TR_IDM[k] for k in ("v0", "T", "s0", "delta")}


def _b_idm_platoon(pool, rng):
    import drivetraffic as TR
    p = {k: TR.driver_style("normal")[k] for k in ("v0", "T", "a", "b", "s0", "delta", "length")}
    return ((lambda t: 10.0 if t < 5 else 8.0), 3), {"params_per_vehicle": p, "dt": 0.1, "t_end": 20.0}


def _b_driver_style(pool, rng):
    return ("sloppy",), {"seed": 1}


def _b_lateral_wobble(pool, rng):
    return (200, 0.05), {"theta": 0.8, "sigma": 0.2, "seed": 3}


def _b_ou_estimate(pool, rng):
    import drivetraffic as TR
    return (TR.lateral_wobble(2000, 0.05, theta=0.8, sigma=0.2, seed=3), 0.05), {}


def _b_social_force(pool, rng):
    import numpy as np
    P = np.array([[0.0, 0.0], [10.0, 0.2]])
    V = np.array([[1.0, 0.0], [-1.0, 0.0]])
    G = np.array([[20.0, 0.0], [-10.0, 0.0]])
    return (P, V, G), {"dt": 0.05, "v0": 1.3, "tau": 0.5, "A": 25.0, "B": 0.08, "radius": 0.3}


def _b_ped_crossing(pool, rng):
    return ("wait_then_cross",), {}


def _b_occl_reveal(pool, rng):
    return ((0.0, 0.0), 0.0, _TR_BOX, (16.0, 3.0)), {}


def _b_occl_intervals(pool, rng):
    return ((0.0, 0.0), 0.0, _TR_BOX, (16.0, 3.0), 30.0), {}


def _b_occl_speed(pool, rng):
    import numpy as np
    return (np.array([5.0, 10.0, 20.0]),), {"reaction": 0.75, "brake": 6.0}


def _b_pass_gap(pool, rng):
    return _TR_PASS, {"lane_change_time": 1.5}


def _b_pass_decision(pool, rng):
    return (60.0,) + _TR_PASS, {"lane_change_time": 1.5}


def _b_bus_rate(pool, rng):
    import numpy as np
    return (np.linspace(0.0, 100.0, 11),), dict(_TR_BUS)


def _b_poisson_events(pool, rng):
    import drivetraffic as TR
    return ((lambda x: TR.bus_stop_rate(x, **_TR_BUS)), 100.0), {"rate_max": 0.06, "seed": 2}


def _b_poisson_events_xt(pool, rng):
    import numpy as np
    return ((lambda x, t: 0.01 + 0.0 * np.asarray(x) * np.asarray(t)), 50.0, 20.0), {"rate_max": 0.02, "seed": 2}


def _b_importance_risk(pool, rng):
    import numpy as np
    low = lambda x: 0.001 + 0.0 * np.asarray(x)            # noqa: E731
    high = lambda x: 0.01 + 0.0 * np.asarray(x)            # noqa: E731
    hit = lambda ev, r: float(np.any((ev >= 40.0) & (ev <= 50.0)))   # noqa: E731
    return (hit, low, high, 200, 4), {"x_max": 100.0, "boosted_rate_max": 0.02}


_DD_PLAN = dict(crossing_length=15.0, ped_green=12.0, walk_speed=1.0, ped_red_to_amber=2.0, amber=3.0, all_red=2.0,
                cross_green=20.0)


def _dd_traj():
    import numpy as np
    t = np.arange(0.0, 20.0, 0.1)
    v = np.maximum(0.0, 10.0 - 1.0 * t)
    x = 80.0 + np.concatenate([[0.0], np.cumsum(0.5 * (v[1:] + v[:-1]) * 0.1)])
    y = np.maximum(0.3, 1.5 - 0.1 * np.arange(len(t)))
    return {"t": t, "x": x, "y": y, "v": v}


def _b_mirror_matrix(pool, rng):
    return ([0.3, -1.0, 0.5, 2.0],), {}


def _b_mirror_vcam(pool, rng):
    import numpy as np
    P = np.eye(4)
    P[2, 3] = 5.0
    return (P, [0.0, 0.0, 1.0, 0.0]), {}


def _b_mirror_aim(pool, rng):
    return ((0.0, 0.4), (1.0, 1.0), (-1.0, 0.1)), {}


def _b_convex_fov(pool, rng):
    return (1.4, 0.18, 0.6), {}


def _b_mirror_blind(pool, rng):
    import drivedecide as DD
    n0 = DD.mirror_aim_normal((0.4, 0.4), (0.9, 1.05), (-1.0, 0.1))
    return ((0.4, 0.4), (0.9, 1.05), n0, 0.18), {"mirror_radius": 1.4}


def _b_check_seq(pool, rng):
    return ([{"t": 1.0, "kind": "signal_on"}, {"t": 0.0, "kind": "mirror"}, {"t": 4.0, "kind": "start"},
             {"t": 7.0, "kind": "end"}, {"t": 7.5, "kind": "signal_off"}],), {}


def _b_signal_plan(pool, rng):
    return (), dict(_DD_PLAN)


def _b_signal_state(pool, rng):
    import drivedecide as DD
    import numpy as np
    return (DD.signal_phase_plan(**_DD_PLAN), "ped_A", np.linspace(0.0, 60.0, 61)), {}


def _b_predict_amber(pool, rng):
    return ([(0.0, "green"), (11.5, "green"), (12.0, "flash"), (13.0, "flash")],), {"crossing_length": 15.0}


def _b_dilemma(pool, rng):
    return (13.9,), {"reaction": 1.0, "decel": 3.0, "amber": 3.0, "intersection_width": 20.0,
                     "car_length": 4.5}


def _b_flash_freq(pool, rng):
    import numpy as np
    t = np.arange(300) / 30.0
    return ((np.sin(2 * np.pi * 2.5 * t) > 0).astype(float), 30.0), {}


def _b_aliased(pool, rng):
    return (2.5, 3.75), {}


def _b_siren(pool, rng):
    return (0.5, 8000.0), {}


def _b_doppler_shift(pool, rng):
    return (960.0, 15.0), {}


def _b_doppler_track(pool, rng):
    import drivedecide as DD
    s = DD.siren_signal(2.0, 16000.0, source_start=(-30.0, 8.0), source_velocity=(15.0, 0.0))
    return (s["signals"][0], 16000.0), {}


def _b_tdoa(pool, rng):
    import drivedecide as DD
    s = DD.siren_signal(0.3, 48000.0, source_start=(60.0, 40.0), source_velocity=(0.0, 0.0),
                        mics=((0.0, 0.075), (0.0, -0.075)))
    return (s["signals"][0], s["signals"][1], 48000.0, 0.15), {}


def _b_yield_check(pool, rng):
    return (_dd_traj(),), {"t_approach": 0.0, "t_passed": 15.0, "intersections": [(140.0, 155.0)]}


def _b_bus_yield(pool, rng):
    return (_dd_traj(),), {"t_signal": 0.0, "bus_rear_x": 140.0}


_DL_CAR = {"mass": 1500.0, "l_f": 1.2, "l_r": 1.5, "c_f": 80000.0, "c_r": 90000.0, "inertia": 2500.0}


def _dl_arc_path():
    import numpy as np
    th = np.linspace(0.0, 1.2, 400)
    return np.stack([50.0 * np.sin(th), 50.0 * (1.0 - np.cos(th))], 1)


def _dl_turn():
    import math
    import drivelateral as DL
    import numpy as np
    ds, y_app, Rf, cx = 0.05, 2.2, 6.5, 26.0
    cy = y_app + Rf
    xs = np.arange(-40.0, cx, ds)
    pre = np.stack([xs, np.full_like(xs, y_app)], 1)
    n = int(round(Rf * math.pi / 2 / ds))
    ph = np.linspace(0, math.pi / 2, n + 1)[1:]
    arc = np.stack([cx + Rf * np.sin(ph), cy - Rf * np.cos(ph)], 1)
    ys = np.arange(ds, 15.0, ds)
    post = np.stack([np.full_like(ys, arc[-1, 0]), arc[-1, 1] + ys], 1)
    F = np.vstack([pre, arc, post])
    speed = np.where(F[:, 0] < cx - 25.0, 8.0, 2.5)
    return {"t": np.arange(len(F)), "front": F, "rear": DL.rear_axle_path(F, 2.7)["rear"], "speed": speed,
            "width": 1.8, "track": 1.55, "front_overhang": 0.9, "rear_overhang": 0.9}


def _b_friction_usage(pool, rng):
    import numpy as np
    return (np.array([0.0, 2.0, -4.0]), np.array([3.0, 0.0, 5.0])), {"mu": 0.8}


def _b_curve_speed(pool, rng):
    import numpy as np
    return (np.array([30.0, 100.0, 300.0]),), {"side_friction": 0.15, "superelevation": 0.06}


def _b_design_radius(pool, rng):
    import numpy as np
    return (np.array([40.0, 60.0, 80.0]),), {"side_friction": 0.13, "superelevation": 0.06}


def _b_understeer(pool, rng):
    return (dict(_DL_CAR),), {}


def _b_steady_corner(pool, rng):
    return (15.0, 100.0, dict(_DL_CAR)), {}


def _b_bicycle_step(pool, rng):
    import numpy as np
    return (np.zeros(5), 0.02, 15.0, dict(_DL_CAR), 0.01), {}


def _b_ackermann(pool, rng):
    import numpy as np
    return (np.array([6.0, 12.0]), 2.7, 1.55), {}


def _b_offtracking(pool, rng):
    import numpy as np
    return (6.0, 2.7, np.linspace(0.0, 9.4, 20)), {"track": 1.55}


def _b_rear_axle(pool, rng):
    return (_dl_arc_path(), 2.7), {}


def _b_fresnel(pool, rng):
    import numpy as np
    return (np.linspace(0.0, 3.0, 31),), {}


def _b_clothoid_pts(pool, rng):
    import numpy as np
    return (50.0, np.linspace(0.0, 50.0, 51)), {"kappa1": 1.0 / 100.0}


def _b_clothoid_design(pool, rng):
    return (100.0, 40.0), {"speed": 16.7}


def _b_pure_pursuit(pool, rng):
    return ((0.0, 0.5, 0.0), _dl_arc_path(), 8.0), {}


def _b_pp_offset(pool, rng):
    return (50.0, 8.0, 2.7), {}


def _b_stanley(pool, rng):
    return ((0.0, 0.5, 0.0), _dl_arc_path()), {"gain": 1.0, "speed": 10.0, "softening": 1.0}


def _b_stanley_decay(pool, rng):
    import numpy as np
    return (0.5, np.linspace(0.0, 5.0, 51)), {"gain": 1.0, "speed": 10.0}


def _b_speed_plan(pool, rng):
    import numpy as np
    s = np.linspace(0.0, 300.0, 301)
    k = np.where((s > 120) & (s < 180), 1.0 / 40.0, 0.0)
    return (s, k), {"v_max": 16.7, "a_lat_max": 2.0, "a_accel": 1.0, "a_decel": 2.0}


def _b_lateral_offset(pool, rng):
    import numpy as np
    return (np.array([[10.0, 1.5], [20.0, 4.5]]), _dl_arc_path()), {}


def _b_tlc(pool, rng):
    return (0.2, 0.01, 0.0, 15.0), {"line_offset": 1.75}


def _b_turn_check(pool, rng):
    return (_dl_turn(),), {"kind": "left", "x_entry": 24.0, "edge_y": 3.5, "center_y": 0.0, "corner_center": (24.0, 9.5),
                           "corner_radius": 6.0, "clearance": 0.5}


def _b_overtake_req(pool, rng):
    return (60 / 3.6, 40 / 3.6), {"lead_length": 4.5, "ego_length": 4.7, "gap_back": 12.0, "gap_front": 15.0,
                                  "accel": 1.0, "v_max": 80 / 3.6, "lane_change_time": 2.0,
                                  "v_oncoming": 60 / 3.6, "pet_min": 2.0}


def _b_overtake_return(pool, rng):
    return (), {"lane_offset": 3.5, "lead_width": 1.7}


def _b_no_pass_zones(pool, rng):
    return ([{"kind": "crosswalk", "start": 300.0, "end": 304.0}, {"kind": "tunnel", "start": 600.0, "end": 900.0}],), {}


def _b_overtake_permitted(pool, rng):
    import drivepass
    zr = drivepass.no_overtaking_zones([{"kind": "crosswalk", "start": 300.0, "end": 304.0}])
    return (), {"maneuver_start": 0.0, "maneuver_end": 150.0, "zones_result": zr, "dist_oncoming": 500.0}


def _b_overtaken_conduct(pool, rng):
    import numpy as np
    t = np.linspace(0.0, 12.0, 121)
    return ({"t": t, "v": np.full_like(t, 11.0)},), {"t_caught": 2.0, "t_passed": 9.0}


def _b_lc_follower(pool, rng):
    return (20.0, 25.0, 15.0), {"reaction": 1.0}


def _b_lc_permitted(pool, rng):
    return (), {"follower": {"gap": 60.0, "v_follow": 22.0, "v_ego": 20.0, "reaction": 1.0}, "boundary": "white"}


def _b_ra_entry(pool, rng):
    return (0.0, 15.0, [{"theta": 3.0, "speed": 4.0}, {"theta": 1.0, "speed": 5.0}]), {"t_clear": 4.0,
                                                                                        "entry_speed": 2.0}


def _b_ra_signal_point(pool, rng):
    import math
    return ([0.0, math.pi / 2, math.pi, 3 * math.pi / 2], 0, 3), {}


def _b_ra_signal_check(pool, rng):
    import math
    import numpy as np
    import drivepass
    arms = [0.0, math.pi / 2, math.pi, 3 * math.pi / 2]
    sp = drivepass.roundabout_signal_point(arms, 0, 3)
    prog = np.linspace(0.0, sp["exit_angle"] + 0.2, 601)
    on = (prog >= sp["signal_angle"]) & (prog <= sp["exit_angle"])
    return (prog, on), {"arm_angles": arms, "entry": 0, "exit": 3}


def _b_crest_sight(pool, rng):
    return (), {"grade_in": 0.04, "grade_out": -0.04, "length": 120.0}


def _b_crest_speed(pool, rng):
    return (80.0,), {"reaction": 0.75, "brake": 6.0}


def _b_hill_yield(pool, rng):
    return ("down",), {"ego_refuge_distance": 10.0, "other_refuge_distance": 80.0}


def _b_cm_image(pool, rng):
    import numpy as np
    return (np.array([10.0, 30.0, 60.0]), 3.0), {"eye_distance": 8.0, "object_size": 1.7}


def _b_cm_misjudge(pool, rng):
    import numpy as np
    return (np.array([10.0, 30.0, 60.0]), np.array([8.0, 10.0, 12.0]), 3.0), {"eye_distance": 8.0}


def _b_mirror_side(pool, rng):
    import numpy as np
    import drivedecide
    E, M = np.array([0.0, -4.0]), np.array([-1.0, 5.0])
    n = drivedecide.mirror_aim_normal(E, M, np.array([1.0, -0.2]))
    pts = np.array([[x, 2.0] for x in np.linspace(-20.0, 30.0, 11)])
    pts = pts[(pts - M) @ n > 0.5]
    return (E, M, n, pts), {"heading": (0.0, 1.0), "velocities": np.tile([[-8.0, 0.0]], (len(pts), 1))}


def _b_mirror_cover(pool, rng):
    return ((9.0, 0.0), (0.0, 0.0), (1.0, 0.0), 0.8), {"mirror_radius": 3.0, "road_point": (20.0, -30.0),
                                                        "road_direction": (0.0, 1.0)}


def _dc_lin(x0, v):
    import numpy as np
    t = np.linspace(0.0, 30.0, 301)
    return {"t": t, "x": x0 + v * t, "v": np.full_like(t, v)}


def _b_crossing_timing(pool, rng):
    return (0.0, 15.0, 35.0), {}


def _b_gate_state(pool, rng):
    import numpy as np
    return (np.linspace(0.0, 60.0, 601),), {"t_warning": 5.0, "t_lower_start": 12.0, "lower_duration": 8.0,
                                            "t_clear": 45.0, "raise_duration": 6.0}


def _b_lamp_signal(pool, rng):
    import numpy as np
    return (np.arange(0.0, 20.0, 0.1),), {"t_on": 0.0, "t_off": 15.0, "exposure": 0.05}


def _b_lamp_phase(pool, rng):
    import numpy as np
    t = np.arange(250) / 25.0
    return (np.sin(2 * np.pi * 0.9 * t), np.sin(2 * np.pi * 0.9 * t + np.pi), 25.0), {}


def _b_clear_time(pool, rng):
    return (3.5, 10.0, 4.5), {"accel": 1.5, "v_max": 5.56}


def _b_exit_room(pool, rng):
    import numpy as np
    return (np.array([14.0, 20.0]), 13.0, 4.5), {}


def _b_stop_check(pool, rng):
    return (_dc_lin(-40.0, 3.0),), {"stop_line": 0.0, "crossing_start": 2.0, "crossing_end": 12.0, "car_length": 4.5}


def _b_track_sight(pool, rng):
    return (22.2, 7.0), {}


def _b_sight_triangle(pool, rng):
    return (-1.13, 5.55, 4.5, 4.0), {}


def _b_priority(pool, rng):
    return ({"width": 4.0}, {"width": 7.0}), {}


def _b_conflict_zone(pool, rng):
    return (10.0, 6.0, 4.5), {"v0": 0.0, "accel": 1.5, "v_max": 8.3}


def _b_obstruction(pool, rng):
    return (40.0, 11.0, 5.0), {}


def _b_cw_overtake(pool, rng):
    o = dict(_dc_lin(80.0, 8.0), kind="car")
    return (_dc_lin(0.0, 14.0), [o]), {"crosswalk_start": 200.0, "crosswalk_end": 204.0}


def _b_cw_stopped(pool, rng):
    return (_dc_lin(-80.0, 5.0), [{"x": -1.0, "t0": 0.0, "t1": 100.0}]), {"crosswalk_start": 0.0, "crosswalk_end": 4.0}


def _b_no_stop_zones(pool, rng):
    return ([{"kind": "crosswalk", "start": 54.0, "end": 58.0}, {"kind": "bus_stop", "at": 110.0}],), {}


def _b_legal_stops(pool, rng):
    import numpy as np
    return (np.array([[45.0, 73.0]]), 0.0, 200.0, 4.5), {}


def _b_parking_check(pool, rng):
    import drivecrossing as DC
    z = DC.no_stopping_zones([{"kind": "crosswalk", "start": 54.0, "end": 58.0}, {"kind": "bus_stop", "at": 110.0}])
    return (40.0, 44.5, z), {}


def _env_world():
    import driveworld as DW
    import numpy as np
    w = DW._empty_world()
    Vg, Fg = DW._grid_plane(-10, 10, -10, 10, step=4.0)
    DW.world_add(w, Vg, Fg, 0, DW._ROAD_COLOR, name="ground")
    bx = np.array([[x, y, z] for z in (0.0, 2.0) for y in (-0.2, 0.2) for x in (-0.2, 0.2)]) + np.array([4.0, 0.0, 0.0])
    bf = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4],
                   [1, 5, 7], [1, 7, 3]])
    DW.world_add(w, bx, bf, 6, (0.8, 0.8, 0.8), name="pole")
    return w


def _env_cam():
    import driveworld as DW
    return DW.camera_pose((-4.0, 0.0, 1.35), (8.0, 0.0, 0.9)), DW.camera_intrinsics(60.0, 48, 32)


def _b_julian_day(pool, rng):
    return (2461120.25,), {}


def _b_sun_at(pool, rng):
    return (2461120.25, 35.6581, 139.7414), {}


def _b_sun_events(pool, rng):
    return (2026, 3, 20, 35.6581, 139.7414), {}


def _b_sun_vector(pool, rng):
    return (20.0, 135.0), {}


def _b_sun_illuminance(pool, rng):
    return (35.0,), {}


def _b_koschmieder(pool, rng):
    return (500.0, 4000.0, 0.02, [5.0, 50.0]), {}


def _b_mor_from_beta(pool, rng):
    return (0.02,), {}


def _b_beta_from_mor(pool, rng):
    return (150.0,), {}


def _b_road_row_distance(pool, rng):
    return ([210.0, 250.0, 300.0], 190.0, 554.0, 1.35), {}


def _b_fog_beta_from_profile(pool, rng):
    import numpy as np
    import driveenv as EV
    rows = np.arange(195, 400)
    d = EV.road_row_distance(rows, 190.0, 554.0, 1.35)
    return (rows, EV.koschmieder(1000.0, 5000.0, 0.03, d), 190.0, 554.0, 1.35), {"slant": False}


def _b_veiling_luminance(pool, rng):
    return (50000.0, [5.0, 20.0]), {}


def _b_veil_chroma_limit(pool, rng):
    return ((1.0, 0.12, 0.08), 10000.0), {}


def _b_sight_stop_speed(pool, rng):
    return (40.0, 0.75, 6.0), {}


def _b_env_params(pool, rng):
    return (), {"sun": (30.0, 180.0), "fog_mor": 200.0}


def _b_tone_map(pool, rng):
    import numpy as np
    return (np.full((8, 8, 3), 5000.0), 1e-4), {}


def _b_env_render(pool, rng):
    import driveenv as EV
    P, K = _env_cam()
    return (_env_world(), P, K, 48, 32, EV.env_params(sun=(30.0, 180.0))), {"shadow_res": 128}


def _gs_quad_world():
    import driveworld as DW
    w = DW._empty_world()
    V = np.array([[-0.1, -0.1, 0.0], [0.1, -0.1, 0.0], [0.1, 0.1, 0.0], [-0.1, 0.1, 0.0]])
    DW.world_add(w, V, np.array([[0, 1, 2], [0, 2, 3]]), 5, (0.8, 0.5, 0.2), name="quad")
    return w


def _gs_cam():
    import driveworld as DW
    return DW.camera_pose((0.0, -0.4, 0.3), (0.0, 0.0, 0.0)), DW.camera_intrinsics(40.0, 64, 48)


def _b_gs_from_world(pool, rng):
    return (_gs_quad_world(),), {"spacing": 0.01}


def _b_gs_update(pool, rng):
    import gsplatnp as GS
    w = _gs_quad_world()
    return (GS.gs_from_world(w, spacing=0.01), w), {}


def _b_gs_render(pool, rng):
    import gsplatnp as GS
    pose, K = _gs_cam()
    return (GS.gs_from_world(_gs_quad_world(), spacing=0.01), pose, K, 64, 48), {}


def _b_gs_render_fn(pool, rng):
    import gsplatnp as GS
    return (GS.gs_from_world(_gs_quad_world(), spacing=0.01),), {}


def _fuzz_file(name, data: bytes) -> str:
    """読み手の op 用の小さなファイルを一時ディレクトリに書く(builder は値でなくパスを渡す)。"""
    d = tempfile.mkdtemp(prefix="fuzz_io_")
    p = os.path.join(d, name)
    with open(p, "wb") as f:
        f.write(data)
    return p


def _b_gs_read_file(pool, rng):
    names = ["x", "y", "z", "f_dc_0", "f_dc_1", "f_dc_2", "opacity", "scale_0", "scale_1", "scale_2",
             "rot_0", "rot_1", "rot_2", "rot_3"]
    n = 16
    data = np.column_stack([rng.normal(size=(n, 3)), rng.normal(size=(n, 3)), rng.normal(size=n),
                            np.log(rng.random((n, 3)) * 0.1 + 0.01), rng.normal(size=(n, 4))]).astype("<f4")
    head = "ply\nformat binary_little_endian 1.0\nelement vertex %d\n%send_header\n" % (
        n, "".join("property float %s\n" % k for k in names))
    return (_fuzz_file("g.ply", head.encode("ascii") + data.tobytes()),), {}


_FUZZ_BVH = """HIERARCHY
ROOT hip
{
  OFFSET 0 0 0
  CHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation
  JOINT spine
  {
    OFFSET 0 1 0
    CHANNELS 3 Zrotation Xrotation Yrotation
    End Site
    {
      OFFSET 0 1 0
    }
  }
}
MOTION
Frames: 2
Frame Time: 0.033
0 0 0 0 0 0 0 0 0
1 0 0 30 10 5 20 0 0
"""


def _b_read_bvh(pool, rng):
    return (_fuzz_file("m.bvh", _FUZZ_BVH.encode("ascii")),), {}


def _fuzz_events(rng, n=200):
    return {"x": rng.integers(0, 16, n), "y": rng.integers(0, 12, n), "t": np.sort(rng.integers(0, 10000, n)),
            "p": rng.integers(0, 2, n)}


def _b_read_events(pool, rng):
    e = _fuzz_events(rng)
    rows = "".join("%d %d %d %d\n" % r for r in zip(e["x"], e["y"], e["t"], e["p"]))
    return (_fuzz_file("ev.txt", rows.encode("ascii")),), {}


def _b_events_to_frames(pool, rng):
    import motionio
    return (motionio.read_events(_b_read_events(pool, rng)[0][0]),), {"n_frames": 8}


def _b_graph_kcore(pool, rng):
    B = (rng.random((30, 30)) < 0.12).astype(int)
    np.fill_diagonal(B, 0)
    return (B,), {"mode": "total"}


def _b_graph_rich_club(pool, rng):
    B = (rng.random((30, 30)) < 0.12).astype(int)
    np.fill_diagonal(B, 0)
    return (B,), {"n_null": 2, "swaps_per_edge": 1}


def _b_graph_core_persistence(pool, rng):
    (mats,), _ = _b_graph_consensus(pool, rng)
    return (mats,), {"mode": "in"}


def _b_graph_growth(pool, rng):
    A = rng.poisson(0.3, (30, 30)).astype(float)
    B = A + rng.poisson(0.4, (30, 30))
    np.fill_diagonal(A, 0)
    np.fill_diagonal(B, 0)
    return (A, B), {}


def _b_seg_pair(pool, rng):
    a = np.repeat(np.repeat(rng.integers(1, 6, (4, 4)), 8, 0), 8, 1)
    b = a.copy()
    b[:16, :16] = 9                      # 融合と分断が両方ある候補
    return (a, b), {}


def _b_seg_wiring(pool, rng):
    a = np.repeat(np.repeat(rng.integers(1, 6, (4, 4)), 8, 0), 8, 1)
    syn = {"pre": rng.uniform(0, 32, (12, 2)), "post": rng.uniform(0, 32, (12, 2))}
    return (a, syn), {}


def _b_seg_wiring_pair(pool, rng):
    (a, b), _ = _b_seg_pair(pool, rng)
    syn = {"pre": rng.uniform(0, 32, (12, 2)), "post": rng.uniform(0, 32, (12, 2))}
    return (a, b, syn), {}


def _b_spc_mt_sn_ratio(pool, rng):
    # 距離は正でなければならない(0 は「単位空間の中心に居る異常標本」= 分離ゼロ)。
    return (rng.uniform(0.5, 20.0, size=12),), {}


def _b_msa_table(pool, rng):
    """部品 6 x 測定者 3 x 繰り返し 3 の**釣り合った**表(不釣り合いは op が拒む)。

    ★成分ごとに違う大きさを与える —— すべて同じ散らばりの表だと、分散成分を
    取り違えている実装でも数字が揃ってしまい、探針が何も言えなくなる。
    """
    p, o, r = 6, 3, 3
    a = rng.normal(0.0, 1.0, p)          # 部品差(大)
    b = rng.normal(0.0, 0.2, o)          # 測定者差(中)
    part, oper, val = [], [], []
    for i in range(p):
        for j in range(o):
            for _ in range(r):
                part.append("P%d" % i)
                oper.append("A%d" % j)
                val.append(10.0 + a[i] + b[j] + rng.normal(0.0, 0.3))
    return ({"part": np.array(part, dtype=object),
             "operator": np.array(oper, dtype=object),
             "value": np.array(val, dtype=np.float64)},), {}


def _b_msa_bias(pool, rng):
    """基準値を **5 水準 x 6 回**(1 水準だけだと傾きが推定できず op が拒む)。"""
    ref = np.repeat(np.array([1.0, 2.0, 3.0, 4.0, 5.0]), 6)
    return ({"reference": ref,
             "measured": ref + 0.05 - 0.01 * ref + rng.normal(0.0, 0.02, ref.size)},), {}


def _b_msa_attribute(pool, rng):
    """検査員 3 人 x 部品 20 個。**1 人 1 部品 1 回**(重複は op が拒む)。"""
    parts = ["q%02d" % i for i in range(20)]
    truth = rng.random(20) < 0.75
    app, prt, rat = [], [], []
    for a in "ABC":
        flip = rng.random(20) < 0.1                     # 検査員ごとに少しぶれる
        for k, p_ in enumerate(parts):
            app.append(a)
            prt.append(p_)
            rat.append("pass" if bool(truth[k] ^ flip[k]) else "fail")
    return ({"appraiser": np.array(app, dtype=object),
             "part": np.array(prt, dtype=object),
             "rating": np.array(rat, dtype=object)},), {}


def _b_gum_shape(pool, rng):
    names = ["rectangular", "triangular", "u_shaped", "normal_95"]
    return ({"halfwidth": rng.uniform(0.1, 2.0, 4),
             "distribution": np.array(names, dtype=object)},), {}


def _b_gum_budget(pool, rng):
    """不確かさ予算。感度は**符号を混ぜる**(相関項の符号を探針が動かせるように)。"""
    n = 4
    return ({"u": rng.uniform(0.05, 1.0, n),
             "sensitivity": rng.uniform(-2.0, 2.0, n),
             "dof": rng.uniform(3.0, 60.0, n)},), {}


def _b_gum_mc(pool, rng):
    """モンテカルロ。n は探針では小さく(規格の下限 1000)。"""
    n = 3
    return ({"u": rng.uniform(0.05, 1.0, n),
             "sensitivity": rng.uniform(-2.0, 2.0, n)},), {"n": 20_000, "seed": 0}


def _b_gum_validate(pool, rng):
    """**2 つの表**を突き合わせる op —— 伝播則の結果とモンテカルロの結果を自分で作る。

    プールの任意の表を 2 つ渡しても列が合わないので、ここで実体を通して組む
    (``gum_expanded`` は ``estimate`` を渡さないと区間を持たず、この op は拒む)。
    """
    import spc as _spc
    n = 3
    tab = {"u": rng.uniform(0.1, 1.0, n),
           "sensitivity": rng.uniform(-2.0, 2.0, n),
           "dof": np.full(n, np.inf)}
    guf = _spc.gum_expanded(tab, estimate=0.0)
    mcm = _spc.gum_monte_carlo(tab, n=20_000, seed=0)
    return (guf, mcm), {"ndig": 1}


def _b_perpetual_state(pool, rng):
    """``perpetual_step`` / ``perpetual_render`` に**本物の状態**を渡す。

    ★宣言 in は ``table`` だが、プールから拾った任意の表では ``system`` キーが
    無く必ず拒否される —— 走ったことにはなるが計算はしていない(MSA の 9 op で
    同じ穴を踏んだ)。種を builder で作って、実際に回るようにする。
    """
    import perpetual as _pp
    name = ("langtons_ant", "elementary_ca", "chaos_game")[int(rng.integers(0, 3))]
    return ([_pp.perpetual_state(name, size=41)], {})


def _b_perpetual_loop_seam(pool, rng):
    """``perpetual_loop_seam`` に**本物の循環動画**を渡す(小さいコマ数で)。"""
    import perpetual as _pp
    return ([_pp.perpetual_loop("plasma_orbit", frames=5, size=24)], {})


# --- HALCON Segmentation 章の 9 op(opssegmentation 台帳、2026-10-02)の種 ------------ #
# 汎用の種では走らない/走っても意味が無い理由(op ごと):
#   class_ndim_norm   : `table` の種は {pre, post} の座標表で model["mean"] が無く KeyError
#   classify_image_class_lut : `signal` の種は float なので返りが float 画像になり labels2d を名乗れない
#   class_2dim_sup    : 一様乱数の参照領域は特徴空間の箱が全域に膨らみ「全画素 True」しか返さない
#   class_2dim_unsup / regiongrowing_n / expand_gray / watersheds_marker :
#                       構造の無い乱数画像は「全画素が別領域」「全面 1 領域」のどちらかに潰れる
#   check_difference / learn_ndim_norm : 走るが、差の分布・共分散が意味を持つ種にする
# apply.py はこのブロックを tools/chain_fuzz.py の ``OP_ARG_BUILDERS = {`` の直前に挿入し、
# 辞書には ``_SEG9_ENTRIES`` の 9 行を足す。
def _seg9_fields(rng, shape=(24, 24)):
    """3 クラスの階段状 2 特徴画像(列で 3 分割)+ 小さな雑音。真のラベルも返す。"""
    H, W = shape
    gt = np.zeros((H, W), int)
    gt[:, W // 3:2 * W // 3] = 1
    gt[:, 2 * W // 3:] = 2
    centers = np.array([[0.1, 0.1], [0.5, 0.9], [0.9, 0.3]])
    f1 = centers[gt, 0] + rng.normal(0.0, 0.02, (H, W))
    f2 = centers[gt, 1] + rng.normal(0.0, 0.02, (H, W))
    return f1, f2, gt


def _b_seg_check_difference(pool, rng):
    a = rng.random((24, 24))
    b = a + rng.normal(0.0, 0.08, a.shape)          # 差の約 2 割が tol=0.1 を超える
    return (a, b), {"tol": 0.1}


def _b_seg_class_2dim_sup(pool, rng):
    f1, f2, gt = _seg9_fields(rng)
    ref = gt == 1                                     # 中央クラスの画素を参照領域に
    return (f1, f2, ref), {}


def _b_seg_learn_ndim_norm(pool, rng):
    X = rng.normal(size=(60, 3)) * np.array([2.0, 1.0, 0.5]) + np.array([1.0, -1.0, 0.0])
    return (X,), {}


def _b_seg_class_ndim_norm(pool, rng):
    imgs = [rng.random((24, 24)) for _ in range(3)]
    X = np.column_stack([im.ravel() for im in imgs])
    model = __import__("segmentation").learn_ndim_norm(X)     # D=3 が画像の枚数と噛み合う
    return (imgs, model), {"thresh": 2.0}


def _b_seg_class_2dim_unsup(pool, rng):
    f1, f2, _gt = _seg9_fields(rng)
    return (f1, f2), {"n_clusters": 3}


def _b_seg_classify_lut(pool, rng):
    im = rng.random((24, 24))
    lut = np.repeat(np.arange(4), 2)                  # 8 段の int LUT(クラス 0..3)
    return (im, lut), {}


def _b_seg_expand_gray(pool, rng):
    im = rng.random((24, 24))
    im[6:18, 6:18] = 0.5 + rng.normal(0.0, 0.01, (12, 12))   # 平坦な島
    seed = np.zeros((24, 24), bool)
    seed[11:13, 11:13] = True
    return (im, seed), {"tol": 0.05}


def _b_seg_regiongrowing_n(pool, rng):
    f1, f2, _gt = _seg9_fields(rng, shape=(16, 16))  # python の BFS なので小さく
    return ([f1, f2],), {"tol": 0.2}


def _b_seg_watersheds_marker(pool, rng):
    from scipy import ndimage as _ndi
    im = _ndi.gaussian_filter(rng.random((24, 24)), 2.0)
    mk = np.zeros((24, 24), int)
    mk[3, 3] = 1
    mk[20, 20] = 2
    mk[3, 20] = 3
    return (im, mk), {}


_SEG9_ENTRIES = {
    "check_difference": _b_seg_check_difference,
    "class_2dim_sup": _b_seg_class_2dim_sup,
    "learn_ndim_norm": _b_seg_learn_ndim_norm,
    "class_ndim_norm": _b_seg_class_ndim_norm,
    "class_2dim_unsup": _b_seg_class_2dim_unsup,
    "classify_image_class_lut": _b_seg_classify_lut,
    "expand_gray": _b_seg_expand_gray,
    "regiongrowing_n": _b_seg_regiongrowing_n,
    "watersheds_marker": _b_seg_watersheds_marker,
}
# --- /HALCON Segmentation 章の 9 op ---------------------------------------------------- #


# --- セグメンテーション 第 1 陣(opssegmentation の score / world、2026-10-02)の種 ------ #
# 汎用の種では走らない/走っても意味が無い理由(op ごと):
#   score 系(segeval の 8 本): 2 枚のラベル画像が要る。汎用の labels2d の種は 1 枚ずつ
#     別々に作られるので「形は合うが中身が無相関」になり、境界・個数の物差しが常に最悪値を
#     返す = 壊れ方の違いが出ない。構造(四角)を仕込んだ真値と、その 1 画素ずらし+偽の塊を
#     予測にして「ほぼ合うが少しずれる」入力にする(hausdorff/境界 F が有限で動く)。
#   world 系(segworld の 8 本): world_* はノブだけ(入力無し)。既定のままだと 160〜260 px で
#     遅いので、門と同じ構造を保ったまま小さく・個数を減らす。lens_area は 2 つのスカラ、
#     voronoi_cells は (n, 2) の種(汎用 points は (N, 3) なので shape[1]==2 で弾かれる)。
# apply.py はこのブロックを tools/chain_fuzz.py の ``OP_ARG_BUILDERS = {`` の直前に挿入し、
# 辞書には下の 16 行(``_SEGBATCH1_ENTRIES`` と同じ対応)を足す。
def _segbatch1_pair(rng):
    """背景 0 + 2x2 の四角(1..4)の真値ラベルと、1 画素ずらし + 偽の塊を 1 つ足した予測。"""
    t = np.zeros((40, 48), np.int64)
    k = 0
    for r in range(2):
        for c in range(2):
            k += 1
            y, x = 4 + r * 18, 4 + c * 22
            t[y:y + 12, x:x + 16] = k
    p = np.roll(t, 1, axis=0)
    p[6:10, 30:40] = 7                               # 偽の塊を 1 つ(個数の物差しが拾う)
    return p, t


def _b_segeval_seg_confusion_table(pool, rng):
    return _segbatch1_pair(rng), {}


def _b_segeval_seg_dice_jaccard(pool, rng):
    return _segbatch1_pair(rng), {"per_label": True}


def _b_segeval_seg_boundary_f(pool, rng):
    return _segbatch1_pair(rng), {"tau": 2.0}


def _b_segeval_seg_hausdorff(pool, rng):
    return _segbatch1_pair(rng), {"percentile": 95.0}


def _b_segeval_seg_mean_surface_distance(pool, rng):
    return _segbatch1_pair(rng), {}


def _b_segeval_seg_under_over_segmentation(pool, rng):
    return _segbatch1_pair(rng), {}


def _b_segeval_seg_object_counts_match(pool, rng):
    return _segbatch1_pair(rng), {"min_overlap": 0.5}


def _b_segeval_seg_score_card(pool, rng):
    return _segbatch1_pair(rng), {"tau": 2.0, "min_overlap": 0.5}


def _b_segworld_world_blobs_touching(pool, rng):
    return (), {"n": 5, "overlap": 0.2, "seed": int(rng.integers(0, 1_000_000)),
                "size": (72, 72), "radius": 10.0}


def _b_segworld_world_grains_voronoi(pool, rng):
    return (), {"n": 9, "seed": int(rng.integers(0, 1_000_000)), "size": (96, 96)}


def _b_segworld_world_parts_with_shadow(pool, rng):
    return (), {"seed": int(rng.integers(0, 1_000_000)), "n_parts": 2}


def _b_segworld_world_texture_regions(pool, rng):
    return (), {"seed": int(rng.integers(0, 1_000_000)), "n_regions": 2, "size": (96, 96)}


def _b_segworld_world_gradient_illumination(pool, rng):
    return (), {"seed": int(rng.integers(0, 1_000_000)), "n_objects": 4, "size": (96, 120)}


def _b_segworld_world_thin_structures(pool, rng):
    return (), {"seed": int(rng.integers(0, 1_000_000)), "n": 3, "size": (96, 96)}


def _b_segworld_lens_area(pool, rng):
    return (10.0, 12.0), {}                           # 等半径 r=10、中心間 d=12(重なる)


def _b_segworld_voronoi_cells(pool, rng):
    seeds = rng.uniform(4.0, 44.0, size=(6, 2))       # (n, 2) の [y, x](汎用 points は (N, 3))
    return (seeds, (48, 48)), {}


_SEGBATCH1_ENTRIES = {
    "seg_confusion_table": _b_segeval_seg_confusion_table,
    "seg_dice_jaccard": _b_segeval_seg_dice_jaccard,
    "seg_boundary_f": _b_segeval_seg_boundary_f,
    "seg_hausdorff": _b_segeval_seg_hausdorff,
    "seg_mean_surface_distance": _b_segeval_seg_mean_surface_distance,
    "seg_under_over_segmentation": _b_segeval_seg_under_over_segmentation,
    "seg_object_counts_match": _b_segeval_seg_object_counts_match,
    "seg_score_card": _b_segeval_seg_score_card,
    "world_blobs_touching": _b_segworld_world_blobs_touching,
    "world_grains_voronoi": _b_segworld_world_grains_voronoi,
    "world_parts_with_shadow": _b_segworld_world_parts_with_shadow,
    "world_texture_regions": _b_segworld_world_texture_regions,
    "world_gradient_illumination": _b_segworld_world_gradient_illumination,
    "world_thin_structures": _b_segworld_world_thin_structures,
    "lens_area": _b_segworld_lens_area,
    "voronoi_cells": _b_segworld_voronoi_cells,
}
# --- /セグメンテーション 第 1 陣の 16 op ------------------------------------------------- #


# --- セグメンテーション 第 2 陣(opssegmentation の contour、2026-10-02)の種 ---------- #
# 汎用の種では走らない/走っても意味が無い理由(op ごと):
#   全 10 本: 汎用の image2d は一様乱数で「縁」が無く、輪郭はどこにも止まらない(snake は縮み切る、
#     Chan–Vese は雑音を 2 値に割る、GAC は風船で全面に広がる)= 走るが壊れ方の違いが出ない。
#     真値の分かる明るい円盤(半径 11、少しぼかし + 小さな雑音)を共通の画像にする。
#   snake_evolve : 第 2 入力の (N, 2) [row, col] の閉曲線は汎用の種に無い(pairs の生成器が無い)。
#     円盤を囲む半径 18 の円(40 点)を初期輪郭にする。
#   chan_vese_* / morph_* / drle_evolve : 初期の内外(mask)は円盤と食い違う四角にする
#     (汎用の mask は乱数の画素で、内外が細切れ = 初期値として意味が無い)。
#   drle_evolve : 円盤を外から囲む四角から縮める(既定の k = 1/255 は 0..1 の画像で縁を強く止める。
#     255 倍して渡すと g が広い帯で潰れ、縁の 1 周外で止まって Dice 0.39 だった = 実測)。
#   level_set_reinit / curvature_flow : 入力は φ か mask。円盤の mask を渡す(内外の両方が要る)。
#   反復は既定か少なめ(48x48 で 1 本 0.1 秒未満)。snake と DRLSE は既定の 300 反復でないと
#     縁まで届かない(60 反復の snake は Dice 0.61、40 反復の DRLSE は 0.39 = 実測)。
# apply.py はこのブロックを tools/chain_fuzz.py の第 1 陣ブロックの直後(``OP_ARG_BUILDERS = {`` の前)に
# 挿入し、辞書には下の 10 行(``_SEGBATCH2_ENTRIES`` と同じ対応)を足す。
def _segbatch2_disk(rng, size=48, radius=11.0):
    """明るい円盤(中心 + 小さなずれ、半径 radius)の画像 0..1 と、その真のマスク。"""
    from scipy import ndimage as _ndi
    cy = size / 2.0 + rng.uniform(-1.0, 1.0)
    cx = size / 2.0 + rng.uniform(-1.0, 1.0)
    yy, xx = np.mgrid[0:size, 0:size]
    truth = (yy - cy) ** 2 + (xx - cx) ** 2 <= radius ** 2
    im = _ndi.gaussian_filter(truth.astype(np.float64), 1.0)
    im = np.clip(im + 0.02 * rng.standard_normal(im.shape), 0.0, 1.0)
    return im, truth


def _segbatch2_box(size=48, lo=8, hi=36):
    """円盤と食い違う四角の初期マスク(左上へずらす)。"""
    m = np.zeros((size, size), bool)
    m[lo:hi, lo:hi] = True
    return m


def _b_segcontour_snake_evolve(pool, rng):
    im, _ = _segbatch2_disk(rng)
    t = np.linspace(0.0, 2.0 * np.pi, 40, endpoint=False)
    init = np.c_[24.0 + 18.0 * np.sin(t), 24.0 + 18.0 * np.cos(t)]      # (N, 2) [row, col]
    return (im, init), {"alpha": 0.05, "beta": 0.05, "gamma": 1.0, "n_iter": 300}


def _b_segcontour_gvf_field(pool, rng):
    im, _ = _segbatch2_disk(rng)
    return (im,), {"mu": 0.2, "method": "direct"}


def _b_segcontour_chan_vese_energy(pool, rng):
    im, _ = _segbatch2_disk(rng)
    return (im, _segbatch2_box()), {}


def _b_segcontour_chan_vese_evolve(pool, rng):
    im, _ = _segbatch2_disk(rng)
    return (im, _segbatch2_box()), {"method": "convex", "n_iter": 30, "n_inner": 50}


def _b_segcontour_morph_chan_vese(pool, rng):
    im, _ = _segbatch2_disk(rng)
    return (im, _segbatch2_box()), {"n_iter": 20}


def _b_segcontour_morph_geodesic_ac(pool, rng):
    im, _ = _segbatch2_disk(rng)
    gy, gx = np.gradient(im)
    g = 1.0 / (1.0 + (gx * gx + gy * gy) / 0.02 ** 2)                    # 縁で小さい画像(edge_stop_g と同じ形)
    init = _segbatch2_box(lo=4, hi=44)                                    # 円盤を外から囲む → 風船で縮める
    return (g, init), {"n_iter": 40, "balloon": -1.0}


def _b_segcontour_edge_stop_g(pool, rng):
    im, _ = _segbatch2_disk(rng)
    return (im,), {"sigma": 1.0, "k": 0.1}


def _b_segcontour_level_set_reinit(pool, rng):
    _, truth = _segbatch2_disk(rng)
    return (truth,), {"n_iter": 30}


def _b_segcontour_drle_evolve(pool, rng):
    im, _ = _segbatch2_disk(rng)
    return (im, _segbatch2_box(lo=4, hi=44)), {"n_iter": 300}


def _b_segcontour_curvature_flow(pool, rng):
    _, truth = _segbatch2_disk(rng)
    return (truth,), {"t_end": 10.0}


_SEGBATCH2_ENTRIES = {
    "snake_evolve": _b_segcontour_snake_evolve,
    "gvf_field": _b_segcontour_gvf_field,
    "chan_vese_energy": _b_segcontour_chan_vese_energy,
    "chan_vese_evolve": _b_segcontour_chan_vese_evolve,
    "morph_chan_vese": _b_segcontour_morph_chan_vese,
    "morph_geodesic_ac": _b_segcontour_morph_geodesic_ac,
    "edge_stop_g": _b_segcontour_edge_stop_g,
    "level_set_reinit": _b_segcontour_level_set_reinit,
    "drle_evolve": _b_segcontour_drle_evolve,
    "curvature_flow": _b_segcontour_curvature_flow,
}
# --- /セグメンテーション 第 2 陣の 10 op ------------------------------------------------- #


# --- セグメンテーション 第 3 陣(opssegmentation の graph / threshold、2026-10-02)の種 ------ #
# 汎用の種では走らない/走っても意味が無い理由(op ごと):
#   全 16 本: 汎用の image2d は一様乱数(平らなヒストグラム・縁も盆地も無い)。
#     graph cut / α-expansion / SRM / 閾値 4 本 : 2 峰(3 峰)のヒストグラムが無いと「どこで割っても同じ」
#       = 走るが、閾値の定理(不動点・最小誤差・最大エントロピー)も平滑項の効き目も出ない。
#       → 真値の分かる段の画像(背景 0.2・円盤 0.75、3 ラベル版は帯を足す)+ 小さな雑音。
#       閾値 4 本は雑音を 0.1 に上げる: 雑音 0.03 だと 2 峰の間に空のビンが続き、Kittler の J・Kapur の H は
#       その区間で平ら(どこで割っても同じ分割)= 同点の取り方しか試せない(実測: Kittler 0.29、SimpleITK 0.47、
#       マスクは同一)。雑音 0.1 で谷が埋まり、基準の曲線そのものが閾値を決める。
#     graph_cut_binary / alpha_expansion : 雑音 0.12(段の差 0.25 の半分)。雑音 0.03 だと画素ごとの判定が
#       既に最小で、α-expansion の移動が 1 つも受け入れられない(実測 n_accepted = 0)= 平滑項を試していない。
#       0.12 では受け入れ 3〜4 回でエネルギーが単調に下がる。
#     quickshift : 特徴は (y, x, ratio·I)。ratio = 1 だと明るさの段 0.55 が空間の 1 画素より小さく、全面 1 領域
#       (実測 n_segments = 1)。ratio = 20 で段が 11 になり max_dist = 4 の枝が段で切れる。
#     max_tree / area_opening_attr : 一様乱数は画素ごとに極大で、成分木が画素数ぶんの葉になるだけ。
#       → 大きな明るい四角 + 小さな明るい点(面積 1〜4、開放で消えるべきもの)。
#     quasi_flat_zones / alpha_tree : 一様乱数は隣の差が大きく、どの α でも「全画素が別の領域」。
#       → 平らな台地 3 枚(差 0.3)+ 台地内の微小な揺れ(α = 0.05 で 1 枚にまとまる大きさ)。
#     hierarchical_watershed / ultrametric_contour_map : 地形の極小が画素ごとに散る。
#       → 深さの違う 3 つの谷(ガウスの窪み)= dynamics が段になる地形。
#     snic_superpixels / quickshift : 構造の無い画像では超画素が格子そのもの。→ 段の画像を使う。
#   superpixel_quality : 2 枚の labels2d。汎用の labels2d は blob の番号で、超画素と真値の関係が無い。
#     → 真値 = 円盤(0 = 背景、1 = 円盤)、超画素 = 4x4 の格子のブロック(円盤の縁を跨ぐ = CUSE > 0)。
#   画像は 24〜32 画素角(Python の Union-Find / 待ち行列なので 1 本 0.1 秒前後に抑える)。
# apply.py はこのブロックを tools/chain_fuzz.py の第 2 陣ブロックの直後(``OP_ARG_BUILDERS = {`` の前)に
# 挿入し、辞書には下の 16 行(``_SEGBATCH3_ENTRIES`` と同じ対応)を足す。
def _segbatch3_steps(rng, size=28, three=False, noise=0.03):
    """背景 0.2 に明るい円盤 0.75(three=True なら上端に 0.45 の帯も)+ 雑音 ``noise``。0..1 に切る。"""
    yy, xx = np.mgrid[0:size, 0:size]
    c = size / 2.0 + rng.uniform(-1.5, 1.5, 2)
    im = np.full((size, size), 0.2)
    im[(yy - c[0]) ** 2 + (xx - c[1]) ** 2 <= (size * 0.3) ** 2] = 0.75
    if three:
        im[: size // 5, :] = 0.45
    return np.clip(im + noise * rng.standard_normal(im.shape), 0.0, 1.0)


def _segbatch3_speckles(rng, size=28):
    """暗い背景に大きな明るい四角(面積 100)と小さな明るい点 6 個(面積 1〜4)。"""
    im = 0.1 + 0.02 * rng.random((size, size))
    im[4:14, 4:14] = 0.8
    for _ in range(6):
        r, c = rng.integers(16, size - 2, 2)
        h, w = rng.integers(1, 3, 2)
        im[r:r + h, c:c + w] = 0.6 + 0.3 * rng.random()
    return im


def _segbatch3_plateaus(rng, size=24):
    """台地 3 枚(0.1 / 0.4 / 0.7、縦の帯)+ 台地の中の揺れ ±0.01(α = 0.05 で 1 枚にまとまる)。"""
    im = np.empty((size, size))
    im[:, : size // 3] = 0.1
    im[:, size // 3: 2 * size // 3] = 0.4
    im[:, 2 * size // 3:] = 0.7
    return im + rng.uniform(-0.01, 0.01, im.shape)


def _segbatch3_valleys(rng, size=28):
    """深さ 1.0 / 0.6 / 0.3 の 3 つの谷(ガウスの窪み、σ = 4)+ ごく小さな揺れ。低い所が盆地。"""
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float64)
    f = np.ones((size, size))
    for (cy, cx), depth in zip(((7, 7), (7, 20), (20, 13)), (1.0, 0.6, 0.3)):
        f -= depth * np.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) / (2.0 * 4.0 ** 2))
    return f + 1e-3 * rng.random(f.shape)


def _b_seggraph_graph_cut_binary(pool, rng):
    return (_segbatch3_steps(rng, noise=0.12),), {"lam": 0.05}


def _b_seggraph_alpha_expansion(pool, rng):
    return (_segbatch3_steps(rng, three=True, noise=0.12), [0.2, 0.45, 0.75]), {"lam": 0.05, "max_cycles": 5}


def _b_seggraph_statistical_region_merging(pool, rng):
    return (_segbatch3_steps(rng),), {"q": 32.0}


def _b_seggraph_max_tree(pool, rng):
    return (_segbatch3_speckles(rng),), {}


def _b_seggraph_area_opening_attr(pool, rng):
    return (_segbatch3_speckles(rng), 8.0), {}                  # 面積 < 8 の点は消え、四角(100)は残る


def _b_seggraph_quasi_flat_zones(pool, rng):
    return (_segbatch3_plateaus(rng), 0.05), {}


def _b_seggraph_alpha_tree(pool, rng):
    return (_segbatch3_plateaus(rng), (0.0, 0.05, 0.35)), {}    # 画素ごと → 台地 3 枚 → 1 枚


def _b_seggraph_hierarchical_watershed(pool, rng):
    return (_segbatch3_valleys(rng),), {"n_regions": 2}


def _b_seggraph_ultrametric_contour_map(pool, rng):
    return (_segbatch3_valleys(rng),), {}


def _b_seggraph_snic_superpixels(pool, rng):
    return (_segbatch3_steps(rng),), {"n_segments": 16, "compactness": 0.1}


def _b_seggraph_quickshift(pool, rng):
    return (_segbatch3_steps(rng, size=20),), {"kernel_size": 2.0, "max_dist": 4.0, "ratio": 20.0, "search_radius": 6}


def _b_seggraph_superpixel_quality(pool, rng):
    size = 24
    yy, xx = np.mgrid[0:size, 0:size]
    c = size / 2.0 + rng.uniform(-1.0, 1.0, 2)
    truth = ((yy - c[0]) ** 2 + (xx - c[1]) ** 2 <= 49.0).astype(np.int64)        # 0 = 背景、1 = 円盤
    sp = (yy // 6) * 4 + (xx // 6) + 1                                           # 4x4 の格子(1..16)
    return (sp.astype(np.int64), truth), {"tau": 2.0}


def _b_seggraph_threshold_triangle(pool, rng):
    return (_segbatch3_steps(rng, size=32, noise=0.1),), {"nbins": 64}


def _b_seggraph_threshold_isodata(pool, rng):
    return (_segbatch3_steps(rng, size=32, noise=0.1),), {"nbins": 64}


def _b_seggraph_threshold_kittler(pool, rng):
    return (_segbatch3_steps(rng, size=32, noise=0.1),), {"nbins": 64}


def _b_seggraph_threshold_kapur(pool, rng):
    return (_segbatch3_steps(rng, size=32, noise=0.1),), {"nbins": 64}


_SEGBATCH3_ENTRIES = {
    "graph_cut_binary": _b_seggraph_graph_cut_binary,
    "alpha_expansion": _b_seggraph_alpha_expansion,
    "statistical_region_merging": _b_seggraph_statistical_region_merging,
    "max_tree": _b_seggraph_max_tree,
    "area_opening_attr": _b_seggraph_area_opening_attr,
    "quasi_flat_zones": _b_seggraph_quasi_flat_zones,
    "alpha_tree": _b_seggraph_alpha_tree,
    "hierarchical_watershed": _b_seggraph_hierarchical_watershed,
    "ultrametric_contour_map": _b_seggraph_ultrametric_contour_map,
    "snic_superpixels": _b_seggraph_snic_superpixels,
    "quickshift": _b_seggraph_quickshift,
    "superpixel_quality": _b_seggraph_superpixel_quality,
    "threshold_triangle": _b_seggraph_threshold_triangle,
    "threshold_isodata": _b_seggraph_threshold_isodata,
    "threshold_kittler": _b_seggraph_threshold_kittler,
    "threshold_kapur": _b_seggraph_threshold_kapur,
}
# --- /セグメンテーション 第 3 陣の 16 op ------------------------------------------------- #


OP_ARG_BUILDERS = {
    # --- 測定システム解析 / 測定の不確かさ(表の列が合わないと一度も計算しない) --- #
    "perpetual_step": _b_perpetual_state,
    "perpetual_render": _b_perpetual_state,
    "perpetual_loop_seam": _b_perpetual_loop_seam,
    "msa_anova_table": _b_msa_table,
    "msa_gauge_rr": _b_msa_table,
    "msa_bias_linearity": _b_msa_bias,
    "msa_attribute_agreement": _b_msa_attribute,
    "gum_standard_uncertainty": _b_gum_shape,
    "gum_propagate": _b_gum_budget,
    "gum_expanded": _b_gum_budget,
    "gum_monte_carlo": _b_gum_mc,
    "gum_validate": _b_gum_validate,
    # --- flyvision(ハエ視葉)の消費 6 op(形の噛み合う入力を組む) ------------ #
    "fly_hex_resample": _b_fly_resample,
    "fly_emd_response": _b_fly_emd,
    "fly_lgmd_eta": _b_fly_lgmd,
    "fly_tau_from_expansion": _b_fly_tau,
    "fly_hs_readout": _b_fly_hs,
    "fly_dsi": _b_fly_dsi,
    # --- SPC(統計的工程管理)の 4 op(形の噛み合う入力を組む) --------------- #
    "spc_xbar_r": _b_spc_xbar_r,
    "spc_cusum": _b_spc_cusum,
    "spc_ewma": _b_spc_ewma,
    "spc_capability": _b_spc_capability,
    "spc_hotelling_t2": _b_spc_hotelling_t2,
    "spc_mt_unit_space": _b_spc_mt_unit_space,
    "spc_mt_distance": _b_spc_mt_distance,
    "spc_mt_sn_ratio": _b_spc_mt_sn_ratio,
    "graph_degree_summary": _b_graph_adj,
    "graph_cycle3": _b_graph_adj,
    "graph_degree_preserving_null": _b_graph_null,
    "graph_swap_symmetry": _b_graph_swap,
    "graph_edge_consensus": _b_graph_consensus,
    # --- HALCON Segmentation 章の 9 op(opssegmentation、2026-10-02) ---------- #
    "check_difference": _b_seg_check_difference,
    "class_2dim_sup": _b_seg_class_2dim_sup,
    "learn_ndim_norm": _b_seg_learn_ndim_norm,
    "class_ndim_norm": _b_seg_class_ndim_norm,
    "class_2dim_unsup": _b_seg_class_2dim_unsup,
    "classify_image_class_lut": _b_seg_classify_lut,
    "expand_gray": _b_seg_expand_gray,
    "regiongrowing_n": _b_seg_regiongrowing_n,
    "watersheds_marker": _b_seg_watersheds_marker,
    # --- セグメンテーション 第 1 陣 score/world の 16 op(opssegmentation、2026-10-02) --- #
    "seg_confusion_table": _b_segeval_seg_confusion_table,
    "seg_dice_jaccard": _b_segeval_seg_dice_jaccard,
    "seg_boundary_f": _b_segeval_seg_boundary_f,
    "seg_hausdorff": _b_segeval_seg_hausdorff,
    "seg_mean_surface_distance": _b_segeval_seg_mean_surface_distance,
    "seg_under_over_segmentation": _b_segeval_seg_under_over_segmentation,
    "seg_object_counts_match": _b_segeval_seg_object_counts_match,
    "seg_score_card": _b_segeval_seg_score_card,
    "world_blobs_touching": _b_segworld_world_blobs_touching,
    "world_grains_voronoi": _b_segworld_world_grains_voronoi,
    "world_parts_with_shadow": _b_segworld_world_parts_with_shadow,
    "world_texture_regions": _b_segworld_world_texture_regions,
    "world_gradient_illumination": _b_segworld_world_gradient_illumination,
    "world_thin_structures": _b_segworld_world_thin_structures,
    "lens_area": _b_segworld_lens_area,
    "voronoi_cells": _b_segworld_voronoi_cells,
    # --- セグメンテーション 第 2 陣 contour の 10 op(opssegmentation、2026-10-02) --- #
    "snake_evolve": _b_segcontour_snake_evolve,
    "gvf_field": _b_segcontour_gvf_field,
    "chan_vese_energy": _b_segcontour_chan_vese_energy,
    "chan_vese_evolve": _b_segcontour_chan_vese_evolve,
    "morph_chan_vese": _b_segcontour_morph_chan_vese,
    "morph_geodesic_ac": _b_segcontour_morph_geodesic_ac,
    "edge_stop_g": _b_segcontour_edge_stop_g,
    "level_set_reinit": _b_segcontour_level_set_reinit,
    "drle_evolve": _b_segcontour_drle_evolve,
    "curvature_flow": _b_segcontour_curvature_flow,
    # --- セグメンテーション 第 3 陣 graph / threshold の 16 op(opssegmentation、2026-10-02) --- #
    "graph_cut_binary": _b_seggraph_graph_cut_binary,
    "alpha_expansion": _b_seggraph_alpha_expansion,
    "statistical_region_merging": _b_seggraph_statistical_region_merging,
    "max_tree": _b_seggraph_max_tree,
    "area_opening_attr": _b_seggraph_area_opening_attr,
    "quasi_flat_zones": _b_seggraph_quasi_flat_zones,
    "alpha_tree": _b_seggraph_alpha_tree,
    "hierarchical_watershed": _b_seggraph_hierarchical_watershed,
    "ultrametric_contour_map": _b_seggraph_ultrametric_contour_map,
    "snic_superpixels": _b_seggraph_snic_superpixels,
    "quickshift": _b_seggraph_quickshift,
    "superpixel_quality": _b_seggraph_superpixel_quality,
    "threshold_triangle": _b_seggraph_threshold_triangle,
    "threshold_isodata": _b_seggraph_threshold_isodata,
    "threshold_kittler": _b_seggraph_threshold_kittler,
    "threshold_kapur": _b_seggraph_threshold_kapur,
    "graph_strength_growth": _b_graph_growth,
    "graph_kcore": _b_graph_kcore,
    "graph_rich_club_curve": _b_graph_rich_club,
    "graph_core_persistence": _b_graph_core_persistence,
    "graph_physarum_path": _b_physarum_graph,
    "physarum_route": _b_physarum_route,
    "graph_physarum_transport": _b_physarum_transport,
    "physarum_transport_image": _b_physarum_transport_image,
    "car_dubins_path": _b_car_poses,
    "car_reeds_shepp_path": _b_car_poses,
    "car_hybrid_astar": _b_car_hybrid_astar,
    "course_crank": _b_course_none, "course_s_curve": _b_course_none, "course_turnaround": _b_course_none,
    "course_slope": _b_course_none, "course_intersection": _b_course_none,
    "course_parallel_parking": _b_course_none, "course_crossing": _b_course_none,
    "course_road": _b_course_none, "course_loop_bend": _b_course_none, "course_loop": _b_course_none,
    "course_layout": _b_course_layout, "course_occupancy": _b_course_grid, "course_contains": _b_course_contains,
    "world_build": _b_world_build, "world_camera": _b_world_camera, "load_asset": _b_load_asset,
    "lidar_spec": _b_course_none, "lidar_scan": _b_lidar_scan,
    "ray_plane_range": _b_ray_plane, "ray_box_ranges": _b_ray_box,
    "world_move": _b_world_move,
    "relative_motion": _b_two_poses, "foe_from_motion": _b_K_T, "flow_from_depth_motion": _b_depth_K_T,
    "ttc_truth": _b_ttc_truth, "ttc_from_flow": _b_ttc_flow, "ttc_from_scale": _b_ttc_scale, "ttc_from_range": _b_ttc_range,
    "label_extent": _b_label_extent,
    "rss_params": _b_course_none, "rss_stopping_distance": _b_rss_stop, "rss_longitudinal_same": _b_rss_two_v,
    "rss_longitudinal_opposite": _b_rss_two_v, "rss_lateral": _b_rss_lat, "rss_longitudinal_check": _b_rss_check,
    "rss_lateral_check": _b_rss_lat_check, "rss_worst_case_gap": _b_rss_worst, "rss_worst_case_gap_opposite": _b_rss_worst,
    "rss_worst_case_gap_lateral": _b_rss_worst_lat,
    "foe_from_flow": _b_foe_flow,
    "perlin2": _b_xy_grid, "fbm_params": _b_fbm_p, "fbm_height": _b_fbm_field, "fbm_gradient": _b_fbm_field,
    "radial_periodogram": _b_field_dx, "spectral_slope": _b_slope, "course_distance": _b_course_xy,
    "terrain_params": _b_terrain_p, "terrain_height": _b_terrain_field, "terrain_gradient": _b_terrain_field,
    "terrain_mesh": _b_terrain_mesh, "world_apply_terrain": _b_world_terrain, "material_params": _b_seed_only,
    "world_materials": _b_world_view, "tree_mesh": _b_tree, "pedestrian_mesh": _b_ped, "crosswalk_mesh": _b_crosswalk,
    "add_mesh_object": _b_add_mesh, "scatter_offroad": _b_scatter, "mesh_signed_volume": _b_mesh_vol,
    "ball_params": _b_course_none, "impact_params": _b_course_none, "flight_vacuum": _b_flight_vac,
    "flight_ode": _b_flight_ode, "flight_simulate": _b_flight_sim, "flight_state_at": _b_flight_state,
    "magnus_lift_coefficient": _b_spin_ratio, "drag_coefficient_sphere": _b_reynolds, "bounce": _b_bounce,
    "contact_angular_momentum": _b_contact_L, "apex_sequence": _b_apex_seq, "bounce_total_time": _b_bounce_time,
    "restitution_from_apexes": _b_apexes, "restitution_from_intervals": _b_intervals, "fit_parabola": _b_t_p,
    "flight_fit": _b_flight_fit, "fit_aero": _b_fit_aero, "fit_spin": _b_fit_spin, "fit_bounce": _b_fit_bounce,
    "slide_stop_distance": _b_slide, "incline_slip_angle": _b_mu, "mu_from_stop_distance": _b_mu_from_stop,
    "roll_slide_state": _b_roll_slide, "tether_simulate": _b_tether, "pendulum_period": _b_pendulum,
    "cup_catch_check": _b_cup,
    "ball_detect": _b_ball_img, "ball_track": _b_ball_dets, "kalman_ca": _b_kalman, "triangulate_dlt": _b_tri_dlt,
    "track_triangulate": _b_track_tri, "bounce_detect": _b_bounce_det, "marker_direction": _b_marker_dir,
    "spin_from_markers": _b_spin_markers, "spin_from_marker_sequence": _b_spin_marker_seq, "reproject": _b_reproject,
    "table_params": _b_course_none, "table_world": _b_table_world, "ball_mesh": _b_ball_mesh, "add_ball": _b_add_ball,
    "ball_set_pose": _b_ball_pose, "rotation_from_omega": _b_rot_omega, "camera_rig": _b_cam_rig,
    "ball_truth": _b_ball_truth, "icosphere": _b_icosphere,
    "racket_params": _b_course_none, "racket_impact": _b_racket_impact, "racket_hit_check": _b_hit_check,
    "aim_velocity": _b_aim, "racket_plan": _b_racket_plan, "racket_move": _b_racket_move,
    "strategy_attacker": _b_strategy, "strategy_feeder": _b_strategy, "shot_is_legal": _b_shot_legal,
    "rally_simulate": _b_rally,
    "kendama_params": _b_course_none, "elliptic_k_agm": _b_ellk, "pendulum_period_exact": _b_period_exact,
    "pendulum_launch_speed": _b_launch_speed, "pendulum_rod_simulate": _b_rod, "tether_tension_fixed": _b_tension,
    "tether_slack_angle": _b_slack_angle, "swing_up_plan": _b_kp_only, "swing_up_apex": _b_kp_only,
    "kendama_catch_check": _b_ken_catch, "kendama_simulate": _b_ken_sim, "catch_plan_ballistic": _b_kp_only,
    "noisy_perceiver": _b_perceiver, "catch_success_rate": _b_success,
    "ken_mesh": _b_ken_mesh, "add_ken": _b_add_ken, "ken_set_pose": _b_ken_pose, "string_mesh": _b_string_mesh,
    "add_string": _b_add_string, "string_set": _b_string_set, "kendama_world": _b_ken_world,
    "kendama_rig": _b_ken_rig, "ken_truth": _b_ken_truth,
    "catch_plan_staged": _b_staged, "swing_up_lift": _b_staged, "parabola_fit_g": _b_parabola_g, "hole_detect": _b_hole_img,
    "kendama_pose": _b_kendama_pose, "kendama_clearance": _b_ken_clear, "camera_perceiver": _b_cam_perceiver,
    "kendama_combo_simulate": _b_kendama_combo,
    "long_params": _b_long_params, "road_profile": _b_road_profile, "road_eval": _b_road_eval,
    "long_simulate": _b_long_simulate, "long_energy_residual": _b_long_energy_residual,
    "stopping_distance_grade": _b_stopping_distance_grade, "stop_line_plan": _b_stop_line_plan, "plan_command": _b_plan_command,
    "hill_hold_brake_min": _b_hill_hold_brake_min, "hill_start_rollback": _b_hill_start_rollback,
    "hill_start_command": _b_hill_start_command, "skill_test_thresholds": _b_skill_test_thresholds,
    "skill_test_score": _b_skill_test_score,
    "crossing_timing_check": _b_crossing_timing,
    "crossing_gate_state": _b_gate_state,
    "crossing_lamp_signal": _b_lamp_signal,
    "lamp_pair_phase": _b_lamp_phase,
    "crossing_clear_time": _b_clear_time,
    "exit_room_check": _b_exit_room,
    "crossing_stop_check": _b_stop_check,
    "track_sight_distance": _b_track_sight,
    "sight_triangle_distance": _b_sight_triangle,
    "priority_rule": _b_priority,
    "conflict_zone_intervals": _b_conflict_zone,
    "obstruction_decel": _b_obstruction,
    "crosswalk_overtake_check": _b_cw_overtake,
    "crosswalk_stopped_vehicle_check": _b_cw_stopped,
    "no_stopping_zones": _b_no_stop_zones,
    "legal_stop_intervals": _b_legal_stops,
    "parking_position_check": _b_parking_check,
    "overtake_requirement": _b_overtake_req,
    "overtake_return_gap": _b_overtake_return,
    "no_overtaking_zones": _b_no_pass_zones,
    "overtake_permitted": _b_overtake_permitted,
    "overtaken_conduct_check": _b_overtaken_conduct,
    "lane_change_follower_decel": _b_lc_follower,
    "lane_change_permitted": _b_lc_permitted,
    "roundabout_entry_check": _b_ra_entry,
    "roundabout_signal_point": _b_ra_signal_point,
    "roundabout_signal_check": _b_ra_signal_check,
    "crest_sight_distance": _b_crest_sight,
    "crest_safe_speed": _b_crest_speed,
    "hill_meeting_yield": _b_hill_yield,
    "convex_mirror_image": _b_cm_image,
    "convex_mirror_misjudge": _b_cm_misjudge,
    "mirror_image_side": _b_mirror_side,
    "mirror_road_coverage": _b_mirror_cover,
    "friction_circle_usage": _b_friction_usage,
    "curve_speed_limit": _b_curve_speed,
    "design_min_radius": _b_design_radius,
    "understeer_gradient": _b_understeer,
    "steady_cornering": _b_steady_corner,
    "bicycle_model_step": _b_bicycle_step,
    "ackermann_steer_angles": _b_ackermann,
    "offtracking_circle": _b_offtracking,
    "rear_axle_path": _b_rear_axle,
    "fresnel_integrals": _b_fresnel,
    "clothoid_points": _b_clothoid_pts,
    "clothoid_design": _b_clothoid_design,
    "pure_pursuit_curvature": _b_pure_pursuit,
    "pure_pursuit_circle_offset": _b_pp_offset,
    "stanley_steer": _b_stanley,
    "stanley_straight_decay": _b_stanley_decay,
    "curvature_speed_plan": _b_speed_plan,
    "lateral_offset": _b_lateral_offset,
    "time_to_line_crossing": _b_tlc,
    "turn_maneuver_check": _b_turn_check,
    "mirror_reflection_matrix": _b_mirror_matrix,
    "mirror_virtual_camera": _b_mirror_vcam,
    "mirror_aim_normal": _b_mirror_aim,
    "convex_mirror_fov": _b_convex_fov,
    "mirror_blind_zone": _b_mirror_blind,
    "check_sequence_score": _b_check_seq,
    "signal_phase_plan": _b_signal_plan,
    "signal_state": _b_signal_state,
    "predict_amber_onset": _b_predict_amber,
    "dilemma_zone": _b_dilemma,
    "flash_frequency": _b_flash_freq,
    "aliased_frequency": _b_aliased,
    "siren_signal": _b_siren,
    "doppler_shift": _b_doppler_shift,
    "doppler_track": _b_doppler_track,
    "tdoa_bearing": _b_tdoa,
    "yield_maneuver_check": _b_yield_check,
    "bus_departure_yield_check": _b_bus_yield,
    "idm_accel": _b_idm_accel, "idm_equilibrium_gap": _b_idm_gap, "idm_platoon_simulate": _b_idm_platoon,
    "driver_style": _b_driver_style, "lateral_wobble": _b_lateral_wobble, "ou_estimate": _b_ou_estimate,
    "social_force_step": _b_social_force, "pedestrian_crossing": _b_ped_crossing,
    "occlusion_reveal_distance": _b_occl_reveal, "occlusion_visible_intervals": _b_occl_intervals,
    "occlusion_safe_speed": _b_occl_speed, "passing_gap_required": _b_pass_gap, "passing_decision": _b_pass_decision,
    "passing_simulate": _b_pass_decision, "bus_stop_rate": _b_bus_rate, "poisson_events": _b_poisson_events,
    "poisson_events_xt": _b_poisson_events_xt, "importance_risk_estimate": _b_importance_risk,
    "tile_hash": _b_tile_hash, "tile_uniform": _b_tile_hash, "pose_normalize": _b_pose_normalize, "tile_params": _b_tile_params,
    "tile_edge_crossing": _b_tile_edge, "tile_roads": _b_tile_ij, "tile_road_distance": _b_tile_xy, "tile_height": _b_tile_xy,
    "tile_mesh": _b_tile_mesh, "tile_digest": _b_tile_digest, "tile_stream": _b_tile_stream, "global_to_tile": _b_global_to_tile,
    "julian_day": _b_julian_day, "sun_at": _b_sun_at, "sun_events": _b_sun_events, "sun_vector": _b_sun_vector,
    "sun_illuminance": _b_sun_illuminance, "koschmieder": _b_koschmieder, "mor_from_beta": _b_mor_from_beta,
    "beta_from_mor": _b_beta_from_mor, "road_row_distance": _b_road_row_distance, "fog_beta_from_profile": _b_fog_beta_from_profile,
    "veiling_luminance": _b_veiling_luminance, "veil_chroma_limit": _b_veil_chroma_limit, "sight_stop_speed": _b_sight_stop_speed,
    "env_params": _b_env_params, "tone_map": _b_tone_map, "env_render": _b_env_render,
    "gs_from_world": _b_gs_from_world, "gs_update": _b_gs_update, "gs_render": _b_gs_render, "gs_render_fn": _b_gs_render_fn,
    "gs_read_file": _b_gs_read_file, "read_bvh": _b_read_bvh, "read_events": _b_read_events,
    "events_to_frames": _b_events_to_frames,
    "sign_params": _b_sign_kind, "sign_image": _b_sign_img, "plate_mesh_from_image": _b_plate_mesh,
    "sign_mesh": _b_sign_mesh, "add_sign": _b_add_sign, "signal_jp_mesh": _b_signal_jp,
    "add_signal_jp": _b_add_signal_jp,
    "tree_from_swc": _b_tree_swc,
    "tree_morphometry": _b_tree_table,
    "tree_sholl": _b_tree_table,
    "tree_run_length": _b_tree_labels,
    "seg_contingency": _b_seg_pair,
    "seg_variation_of_information": _b_seg_pair,
    "seg_rand": _b_seg_pair,
    "seg_synapse_partners": _b_seg_wiring,
    "seg_wiring_variation": _b_seg_wiring_pair,
    "seg_synapse_nri": _b_seg_wiring_pair,
    "seg_wiring_exposure": _b_seg_wiring,
    "swt_map": _b_text_img,
    "vx_sobel3x3": _b_vx_sobel,
    "vx_magnitude": _b_vx_grad,
    "vx_phase": _b_vx_phase,
    "vx_table_lookup": _b_vx_lut,
    "vx_histogram": _b_vx_hist,
    "vx_nonmax_suppression": _b_vx_nms,
    "vx_warp_affine": _b_vx_affine,
    "vx_warp_perspective": _b_vx_persp,
    "vx_remap": _b_vx_remap,
    "vx_nonlinear_filter": _b_vx_nonlinear,
    "text_candidates": _b_text_swt,
    "text_lines": _b_text_boxes,
    # --- 描画: 32x32 では物理的に収まらない 13 op ---------------------------- #
    "text_box": _b_draw(["image2d", "text"]),
    "leader_line": _b_leader_line,
    "legend_box": _b_draw(["image2d", "entries"]),
    "scale_bar": _b_draw(["image2d"]),
    "axes_frame": _b_draw(["image2d", "axes"]),
    "grid_lines": _b_draw(["image2d", "axes"]),
    "ticks": _b_draw(["image2d", "axes"]),
    "plot_series": _b_draw(["image2d", "axes", "signal", "signal"]),
    "rounded_rect": _b_draw(["image2d"]),
    "zoom_inset": _b_draw(["image2d"]),
    "compare_frame": _b_draw(["image2d", "image2d"]),
    "color_bar": _b_draw(["image2d", "lut"], lut=_colormap),
    "overlay_labels": _b_draw(["image2d", "labels"], labels=_labels_for_canvas),
    "label_points": _b_draw(["image2d", "pairs"], pairs=_points_for_canvas),
    "panel_grid": _b_panels,
    # --- 族の入口 op から作らないと形が合わないもの -------------------------- #
    "particle_step": _b_particles,
    "particle_render": _b_particles,
    "watermark_embed": _b_watermark(True),
    "watermark_capacity": _b_watermark(True),
    "watermark_extract": _b_watermark(False),
    # --- 単調な x / 正方行列 / 優決定系 -------------------------------------- #
    "interp_linear": _b_sorted_xy(1),
    "interp_cubic": _b_sorted_xy(1),
    "poly_fit": _b_sorted_xy(0),
    "mat_eigh": _b_square_matrix((5, 5)),
    "mat_solve": _b_linear_system,
    "mat_lstsq": _b_lstsq,
    "matrix_to_angle": _b_square_matrix((3, 3)),
    "matrix_to_rot_scale": _b_square_matrix((2, 2)),
    # --- 台帳が image2d と宣言しているが実体は (N,2) 対応点 ------------------ #
    "essential_8point": _b_two_view_pts(True),
    "fundamental_8point": _b_two_view_pts(False),   # F は較正不要
    "recover_pose": _b_two_view_pts(True),

    "pose_error": _b_pose_error,
    "normal_consistency": _b_normal_consistency,
    "triangulate": _b_triangulate,
    "sampson_distance": _b_sampson,
    "bundle_adjust": _b_bundle,
    "mean_reprojection_error": _b_bundle,
    "optimize_pose_graph": _b_pose_graph,
    "mean_edge_error": _b_pose_graph,
    "query_distance": _b_query_distance,
    "integrate": _b_integrate,
    "shot_descriptor": _b_shot,
    "tilemap_render": _b_tilemap,
    "parallax_layers": _b_parallax,
    "abcd_matrix": _b_abcd,
    "wavefront_stats": _b_wavefront,
    "abcd_trace": _b_shaped("matrix", (2, 2), _mk_abcd),
    "jones_apply": _b_shaped("cimage", (2, 2), _mk_jones, "jones"),
    "render_through_lens": _b_render_lens,
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
    # meshres(2026-09-03): (V, F) を 2 位置引数へ割る解像度管理 op
    "mesh_edge_stats": _b_mesh_split(),
    "mesh_detail_map": _b_mesh_split(),
    "mesh_split_long_edges": _b_mesh_split(),
    "mesh_isotropic_remesh": _b_mesh_split(),
    "mesh_sample_points": _b_mesh_split(),
    "mesh_lod_chain": _b_mesh_split(),
    "mesh_decimate_preserving": _b_mesh_split(),
    "mesh_reduction_report": _b_mesh_pair(),     # (V, F, V2, F2)
    "cast_shadow": _b_mesh_split("vector"),      # (V, F, light)
    # terrain / 惑星測光(2026-09-03): (V, F) を割る 9 op。--cover-all で
    # 「必須引数が組めない」と出ていた(= 一度も実行されていなかった)
    "mesh_displace_fbm": _b_mesh_split(),
    "terrain_region_mask": _b_mesh_split(),
    "mesh_scatter_boulders": _b_mesh_split(),
    "mesh_edge_lengths": _b_mesh_split(),
    "mesh_subdivide": _b_mesh_split(),
    "displacement_band_weights": _b_mesh_split(),
    "mesh_displace_spectrum": _b_mesh_split(),
    "render_regolith": _b_mesh_split(),
    "shadow_raycast": _b_mesh_split("vector"),   # (V, F, light)
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

#: 文書化済みの非有限を返す op(鏡面/測光)。docstring の
#: 「**Unsolvable pixels are ``NaN``.**」節が契約として明記している: 信じられた光源が
#: *min_inliers*(既定・最小 3)未満、または信じられた方向が同一平面上で 3x3 正規方程式が
#: 特異な画素は、normals と albedo の両方が NaN になる。以前は勝った 3 光源部分集合の解を
#: 残していて「劣決定の画素が自信ありげな 1.3 度の答え」で返ってきたのを、**わざと**
#: NaN にした経緯まで書かれている(cadmap の「当たらなかった = NaN」と同じ思想)。
#: 一様乱数の 4 枚組は Lambertian 面ではないので、多くの画素で信じられる光源が 3 本未満に
#: なる ― これは op が仕事をしている。
#: 非ロバストな ``photometric_stereo``(全光源を使う baseline)は同じ入力で有限を返す
#: (実測)ので**入れない** — 入れると本物の非有限が黙って見逃される。
NONFINITE_BY_CONTRACT_SPECULAR = {"photometric_stereo_robust"}

#: 文書化済みの非有限を返す op(imgmetrics)。**完全一致の PSNR は inf** で、
#: そこに小さな値を足して有限に丸めると「非常に良い一致」が有限値に化け、
#: 平均を取ったときに嘘になる ―― 丸めない判断そのものが契約
#: (:func:`imgmetrics.psnr` の docstring と ``tests/test_imgmetrics.py``)。
#: ``compare_images`` は psnr を内に含むので同じ理由で載る。``measure_with`` は
#: その報告を**同じ条件で測り直す** op なので、同じ 2 枚を渡せば当然 psnr が inf
#: になる ―― 網羅パス(``--cover-all``)で初めて実行されて挙がった(metrics 型と
#: image2d 2 枚が同時に要るため、ランダム歩行では一度も踏まれていなかった)。
NONFINITE_BY_CONTRACT_METRICS = {"psnr", "compare_images", "measure_with"}

#: 文書化済みの非有限を返す op(astrostack / imgforensics)。**「答えられない」を
#: NaN で言うのが契約**で、0 で埋めると「測れた」に化ける。2026-09-02 に台帳を
#: ファザーへ登録した直後の実走で 4 op が挙がり、1 件ずつ実測して確認した:
#:
#:   * frame_quality — 星が 0 個の絵で fwhm_px / roundness / peak_snr が NaN
#:     (n_stars=0, score=0.0 が併せて返るので判別できる)。FWHM を 0 と答えると
#:     「非常に鋭い絵」に化ける。
#:   * psf_fit — 当てはめ箱が画像からはみ出すと converged=False, rms/fwhm_px が
#:     NaN、``reason="box falls outside the image"`` を添えて返す。
#:   * aperture_photometry — 検出でない位置ではフラックスが負になり、
#:     **負のフラックスの等級は存在しない**ので mag_instrumental が NaN
#:     (flux / snr は有限のまま負値で返るので、何が起きたか読める)。
#:   * jpeg_quality_estimate — 櫛が立たない(無圧縮の)絵で quality=None,
#:     fit_error=NaN。「品質 17」のような当てずっぽうを返さないための設計。
NONFINITE_BY_CONTRACT_ASTRO_FORENSICS = {
    "frame_quality", "psf_fit", "aperture_photometry", "jpeg_quality_estimate",
}

#: 出力を pool 型へ合わせる梱包アダプタ。基本はレジストリの RESULT_ADAPTERS
#: (型忠実の一級メタデータ)に委譲し、ファザー固有の追加だけここに置く






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
    # KEYWORD_ONLY も束縛する(2026-09-03): ``mesh_scatter_boulders(V, F, *, density,
    # d_min)`` のような必須キーワード引数は positional だけを見ていると **束縛されず、
    # 生の TypeError で「必須引数が組めない」**になっていた(ledger の raw-exception 検査
    # と --cover-all の SUSPECT で顕在化)。署名順では keyword-only は positional の
    # 後ろに並ぶので、data 引数で positional を埋めたあとのスライスはそのまま使える。
    params = [p for p in sig.parameters.values()
              if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)]
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


def _is_lab(v):
    """CIE L*a*b* か。**rgbimage と形も dtype も同じ**なので値域で見るしかない。

    L* は 0-100、sRGB は 0-1。sRGB を ΔE に渡しても例外は出ず、2 桁小さい
    色差が静かに出る ―― その取り違えをここで捕まえる。無彩色に近い暗い絵は
    L* も小さいので、`a*`/`b*` が負値を取りうることも併せて見る。

    **原理的な限界(実測 2026-09-02)**: 真っ黒な絵は Lab でも sRGB でも
    ``(0, 0, 0)`` なので**区別できない**。この述語は False を返す = TYPEMISS の
    偽陽性になる。**見逃しではなく誤報**の側なので安全な向きだが、
    「黒い lab を返す op」を足したらここが鳴ることは知っておくこと。
    """
    if not (isinstance(v, np.ndarray) and v.ndim >= 2 and v.shape[-1] == 3 and v.size):
        return False
    if not np.issubdtype(v.dtype, np.floating):
        return False
    L = v[..., 0]
    ab = v[..., 1:]
    # L* が 1 を超える(sRGB では起きない)か、a*/b* が負(sRGB では起きない)
    return bool(np.nanmax(L) > 1.5 or np.nanmin(ab) < -1e-9)


TYPE_CHECKS = {
    # --- 2026-09-02 に登録した 9 台帳が持ち込んだ型の述語 ------------------
    # 述語が無いと「宣言 out=X の op が何を返しても TYPEMISS にならない」ので、
    # 検査面を増やしたつもりで増えていない状態になる。台帳が提案を持つもの
    # (opsreprconv / opsimgforensics)はその定義をそのまま採る。
    #
    # `scalar` と `any` だけは意図的に緩い: 前者は「数 1 個」、後者は既存の
    # ワイルドカードで、run_chain が常に満たされたものとして扱う。
    "scalar": lambda v: isinstance(v, (int, float, np.integer, np.floating))
                        and not isinstance(v, bool),
    "any": lambda v: True,
    # 色: lab は rgbimage と**形も dtype も同じ**なので、L* が 0-100 かどうかで見る
    # (sRGB を ΔE に渡しても例外は出ず、2 桁小さい色差が静かに出る)
    "lab": _is_lab,
    "rgb": lambda v: isinstance(v, np.ndarray) and v.ndim == 3 and v.shape[-1] == 3,
    "rgba": lambda v: isinstance(v, np.ndarray) and v.ndim == 3 and v.shape[-1] == 4,
    "rgba_premul": lambda v: isinstance(v, np.ndarray) and v.ndim == 3 and v.shape[-1] == 4,
    "rgbvolume": lambda v: isinstance(v, np.ndarray) and v.ndim == 4 and v.shape[-1] == 3,
    "lut": lambda v: isinstance(v, np.ndarray) and v.ndim in (2, 4),
    "sprites": lambda v: isinstance(v, (list, tuple)) and len(v) > 0
                         and all(isinstance(s, np.ndarray) and s.ndim == 3 for s in v),
    # 断層: sinogram = (角度, 検出器)、sinostack = その積み重ね
    "sinogram": lambda v: isinstance(v, np.ndarray) and v.ndim == 2,
    "sinostack": lambda v: isinstance(v, np.ndarray) and v.ndim == 3,
    # 図注: text は文字列、entries は (ラベル, 色) の並び、axes は変換の辞書
    "text": lambda v: isinstance(v, str),
    "entries": lambda v: isinstance(v, (list, tuple)) and len(v) > 0,
    # 測る/運ぶ: metrics は contract を必ず持つ(数値だけの辞書と区別する)
    "metrics": lambda v: isinstance(v, dict) and "contract" in v,
    "transport_plan": lambda v: isinstance(v, np.ndarray) and v.ndim == 2
                                and v.size > 0 and float(np.nanmin(v)) >= -1e-12,
    # フォレンジック: 台帳の提案どおり
    "phash": lambda v: isinstance(v, np.ndarray) and v.ndim == 1 and v.dtype == bool,
    "fingerprint": lambda v: isinstance(v, np.ndarray) and v.ndim == 2
                             and np.issubdtype(v.dtype, np.floating),
    "mask": lambda v: isinstance(v, np.ndarray) and v.ndim == 2
                      and (v.dtype == bool or np.issubdtype(v.dtype, np.integer)),
    # labels2d(2026-09-06、blob 族): 背景 0・物体 1..n の 2-D 整数画像。
    # **bool を通さない**のが肝 —— mask の述語には当たってしまう型なので、
    # ここまで緩めると「二値を返す op が labels2d を名乗る」を検出できない。
    "labels2d": lambda v: isinstance(v, np.ndarray) and v.ndim == 2
                          and v.dtype != bool
                          and np.issubdtype(v.dtype, np.integer)
                          and v.size > 0 and int(v.min()) >= 0,
    # tokens(2026-09-24、llmcore 族): (T, d) の実数列。**軸の順が意味を持つ** ——
    # matrix の述語には当たるが、転置した (d, T) も「行列」としては正しいので、
    # 型を分けないと「長さ d の列を幅 T で」計算した数が例外なしに返る。
    "tokens": lambda v: isinstance(v, np.ndarray) and v.ndim == 2 and v.size > 0
                        and np.issubdtype(v.dtype, np.floating)
                        and bool(np.isfinite(v).all()),
    # attnmap(2026-09-24、llmcore 族): (T, S) の注意行列。生スコアと softmax 後の
    # 両方が座る(行和 1 は attention_apply が入口で検査する)。image2d と形は同じだが、
    # 画像として平滑化やしきい値をかけると行和 1 が黙って壊れる側。
    "attnmap": lambda v: isinstance(v, np.ndarray) and v.ndim == 2 and v.size > 0
                         and np.issubdtype(v.dtype, np.floating)
                         and bool(np.isfinite(v).all()),
    # conn_graph(2026-09-20、conngraph 族): 正方・実数・有限の n×n 隣接行列。
    # matrix の述語には当たるが、こちらは**正方と有限**を要求する —— 非正方や
    # NaN 入りを「グラフ」と名乗る op を TYPEMISS にするための型。
    "conn_graph": lambda v: isinstance(v, np.ndarray) and v.ndim == 2
                            and v.shape[0] == v.shape[1] and v.size > 0
                            and np.issubdtype(v.dtype, np.floating)
                            and bool(np.isfinite(v).all()),
    # synapse_table: (m, 3) の (pre_id, post_id, count)。points と同形なので、
    # id 列が**整数値かつ非負**であることまで見る(座標を id と読ませない)。
    "synapse_table": lambda v: isinstance(v, np.ndarray) and v.ndim == 2
                               and v.shape[1] == 3 and v.size > 0
                               and np.issubdtype(v.dtype, np.floating)
                               and bool(np.isfinite(v).all())
                               and bool(np.all(v[:, :2] == np.round(v[:, :2])))
                               and float(v[:, :2].min()) >= 0.0,
    # 実測でキーは mu / sigma / w(最初 "mean" と推測して書いたら
    # points_to_gaussians が TYPEMISS になった —— op ではなく述語が誤り)
    "gaussians": lambda v: isinstance(v, dict) and {"mu", "sigma", "w"} <= set(v),
    # 形態統計(2026-09-06): shapeset は形の群 (K, N, 3)、shapemodel は shape_pca の
    # 返す辞書。voxel(3 次元配列)や table(list/dict)にも当たってしまうので、
    # 述語をここで厳しくしないと、群の平均に濃度場を渡す連鎖が例外なしに通る。
    "shapeset": lambda v: isinstance(v, np.ndarray) and v.ndim == 3                           and v.shape[2] == 3 and v.shape[0] >= 2,
    "shapemodel": lambda v: isinstance(v, dict)                             and {"mean", "components", "variance", "n_points"} <= set(v),
    # efdmodel は elliptic_fourier の返す辞書。table(list/dict)にも当たるので
    # 鍵で見る —— 述語を緩くすると Zernike の係数表を reconstruct に渡す連鎖が
    # 「通ってしまう」のではなく KeyError で毎回落ち、族の 4 op が永久に
    # 未実行になる(嘘を防ぐためでなく、実際に走らせるための型)。
    "efdmodel": lambda v: isinstance(v, dict)
                          and {"a0", "c0", "coeffs", "n_harmonics"} <= set(v),
    # 測定線と計測モデル。どちらも dict なので table にも当たる。鍵で見ないと
    # 族の 8 op が KeyError で終わり、検査面としては死ぬ(嘘を防ぐためでなく
    # 実際に走らせるための型 —— efdmodel / shapemodel と同じ理由)。
    "measurehandle": lambda v: isinstance(v, dict)
                               and {"type", "rows", "cols", "spacing"} <= set(v),
    "metrologymodel": lambda v: isinstance(v, dict) and isinstance(v.get("objects"), list),
    "points": _is_pts,
    "normals": _is_pts,
    "keypoints": lambda v: _is_pts(v) or (isinstance(v, np.ndarray) and v.ndim == 2),
    "voxel": lambda v: isinstance(v, np.ndarray) and v.ndim == 3,
    "sdf": lambda v: isinstance(v, np.ndarray) and v.ndim == 3,
    # labels = **整数のラベル配列**。1-D(点ごと)/ 2-D(画像)/ 3-D(volume)が
    # 同じ型名に同居している(実測: 産む 7 op のうち label_components / vol_label /
    # vol_watershed が (D,H,W)、region_growing / euclidean_cluster /
    # plane_segmentation / segment_rigid_motions が (N,))。食う側も
    # vol_region_props が 3-D、cad_defect_to_cad と
    # illuminant_from_dichromatic_planes が 2-D を要求する。
    # **分けなかった理由**: 取り違えは全て documented ValueError で fail-closed し
    # (3 消費側とも実測)、「例外でなくもっともらしく間違う」条件を満たさない。
    # 代わりに生成器へ 2-D と 3-D の両方を置いて、どちらの消費側も実際に走るように
    # した(片方しか種が無いと相手側が永久に fail-closed = 「発見ゼロ」の偽装)。
    # 述語は ``ndim >= 1`` の素通しをやめ、**整数であること**と 1〜3 次元だけに絞る
    # (float の「ラベル」を渡されると下流は黙って丸める)。
    "labels": lambda v: len(_shape(v)) in (1, 2, 3)
    and getattr(getattr(v, "dtype", None), "kind", "") in "iub",
    "image2d": lambda v: isinstance(v, np.ndarray) and v.ndim == 2,
    "depth": lambda v: isinstance(v, np.ndarray) and v.ndim == 2,
    "cimage": lambda v: isinstance(v, np.ndarray) and v.ndim == 2 and v.dtype.kind == "c",
    "signal": lambda v: isinstance(v, np.ndarray) and v.ndim == 1,
    # measurement = スカラのみ(tuple/dict がここに紛れると下流 op が生 TypeError
    # で落ちる — 第 3 波でプール汚染として実測)
    "measurement": lambda v: isinstance(v, (int, float, np.floating, np.integer)),
    "indices": lambda v: isinstance(v, np.ndarray) and v.ndim == 1,
    # coordgrid = ボクセル中心の座標場 (nx,ny,nz,3)。points((N,3))とは**別 sort**:
    # 点群を sphere_sdf に渡すと (N,) が返り、宣言の 3-D 場にならない(型の嘘)。
    "coordgrid": lambda v: isinstance(v, np.ndarray) and v.ndim == 4 and v.shape[3] == 3,
    "table": lambda v: isinstance(v, (list, dict)),
    "rle_region": lambda v: type(v).__name__ == "VolRLE",
    "pointmap": lambda v: isinstance(v, np.ndarray) and v.ndim == 3 and v.shape[2] == 3,
    "normalmap": lambda v: isinstance(v, np.ndarray) and v.ndim == 3 and v.shape[2] == 3,
    "images": lambda v: isinstance(v, (list, tuple)) and all(
        isinstance(x, np.ndarray) and x.ndim == 2 for x in v),
    "vector": lambda v: isinstance(v, np.ndarray) and v.shape == (3,),
    # pairs = **(N,2) の (x, y) 列、または同じ長さの 1-D 配列 2 本のタプル**。
    #
    # ★ 2026-09-02 まで ``lambda v: True`` だった = **述語が「有る」と数えられている
    # ぶん、無いより悪い**(点検スクリプトも「述語あり」に数えてしまう)。実測で
    # None / 42 / 文字列 / dict まで通していた。
    #
    # 正典は消費側 6 op(reprconv の pairs_to_signal / pairs_to_image2d /
    # pairs_to_table / angles_to_normals / shape_index_to_curvature /
    # polar_to_cscalar)を**全部実行して**決めた: 6 op とも上の 2 形だけを受け、
    # それ以外は "pairs: must be (N, 2) or a 2-tuple of equal-length 1-D arrays"
    # で名指しの fail-closed になる(実測)。**(2,N) は受けない**ので、
    # 2-tuple を np.stack で (2,N) に潰していた adapter 3 件は axis=1 へ直した。
    # 長さの違う 2 本(histogram の counts/edges)も「対」ではないので弾く。
    "pairs": lambda v: (len(_shape(v)) == 2 and _shape(v)[1] == 2)
    or (_is_seq(v, 2) and len(_shape(v[0])) == 1
        and _shape(v[0]) == _shape(v[1])),
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
    # volseq(2026-09-21、live4d)= 体積の時系列 (T, Z, Y, X)、T >= 2。rgbvideo (T, H, W, 3) と ndim が同じだが
    # 述語は名前ごとに独立(宣言 out との突き合わせにしか使わない)。
    "volseq": lambda v: isinstance(v, np.ndarray) and v.ndim == 4 and v.shape[0] >= 2,
    "video": lambda v: isinstance(v, np.ndarray) and v.ndim == 3
    and v.dtype.kind == "f" and v.shape[0] >= 2
    and v.shape[1] >= 4 and v.shape[2] >= 4,
    # rgbimage = (H,W,3) の色画像。pointmap / normalmap と**構造は同じ**なので
    # 型を分けないと、法線マップを鏡面分離に渡しても例外なく「分離結果」が
    # 返る(実測確認済み)。型は入れ物の形でなく意味の約束
    "rgbimage": lambda v: isinstance(v, np.ndarray) and v.ndim == 3
    and v.shape[2] == 3,
    # rgbvideo = (F,H,W,3) の色動画(2026-09-20、conngraph の points_activity_video が産む)。
    # video (T,H,W) は灰色 1 チャネルで videops が ndim == 3 を要求するので混ぜない —— 載せると
    # 時間フィルタが最後の軸を幅と読んで例外なしに「処理した動画」を返す
    "rgbvideo": lambda v: isinstance(v, np.ndarray) and v.ndim == 4
    and v.shape[3] == 3 and v.dtype.kind == "f" and v.shape[0] >= 1,
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
    # axes は **2 つの別物**が同じ名前で同居している(2026-09-02 に annotate を
    # 登録して判明)。3-D の主軸 = 長さ 3 のベクトル列(``moment_axes``)、
    # 作図の軸変換 = ``rect``/``xlim``/``ylim`` を持つ辞書(``axes_transform``)。
    #
    # **分けなかった**。この repo の基準は「混ぜると例外でなく、もっともらしく
    # 間違った結果が出るか」で、実測はそうならない —— 3-D の主軸を
    # ``axes_frame`` / ``grid_lines`` / ``ticks`` に渡すと 3 つとも即座に
    # ``TypeError: tuple indices must be integers or slices, not str`` で落ちる
    # (絵は 1 画素も変わらない)。よって型ではなく述語で両方を受ける。
    "axes": lambda v: (isinstance(v, dict) and {"rect", "xlim", "ylim"} <= set(v))
                      or (_is_seq(v, 3) and _shape(v[0]) == (3,))
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

    # flow は **1 つの型名の下に別物が 2 つ**同居していたので分けた。
    #   flow_scattered (N,3)     — estimate_flow / nearest_neighbor_flow / smooth_flow
    #   flow_dense     (3,D,H,W) — scene_flow_lk
    # 分けた根拠は実測: 消費側 4 op(reprconv)の要求が**互いに排他**で、
    # flow_magnitude / flow_to_rgbimage は "this op takes DENSE scene flow
    # (3, D, H, W) …; got (160, 3)" と言い、flow_speed / flow_apply は
    # "this op takes SCATTERED flow (N, 3) …; got (3, 12, 12, 12)" と言う。
    # **どの 1 つの値も両方を満たせない**ので 1 型 1 述語では書けず、共有したままだと
    # 片側 2 op が毎回 fail-closed して「頑健だから発見ゼロ」に化ける
    # (counts / countrate、jones / stokes を分けたのと同じ判断)。
    # points と pointmap の「散布 / 組織化」の対比もそのまま当てはまる。
    "flow_scattered": lambda v: not _is_seq(v) and len(_shape(v)) == 2 \
    and _shape(v)[1] == 3,
    "flow_dense": lambda v: not _is_seq(v) and len(_shape(v)) == 4 \
    and _shape(v)[0] == 3,

    # flow2d = **平面**の密な変位場 (2, h, w)、成分 (dy, dx) [px/frame]。
    # flow_dense((3,D,H,W) の 3-D シーンフロー)とは別の型 —— あちらの述語は
    # ndim==4 を要求するので 2-D は該当せず、名前を借りると台帳が
    # 「3 成分を返す」と宣言しながら 2 成分を返すことになる(2026-09-06、
    # pivops 新設時)。述語を書き忘れていたことは
    # test_every_catalog_out_type_has_a_predicate が捕まえた —— 述語が無いと
    # 「宣言 out=flow2d の op が何を返しても TYPEMISS にならない」ので、
    # 検査面を増やしたつもりで増えていない状態になる。
    "flow2d": lambda v: not _is_seq(v) and len(_shape(v)) == 3 \
    and _shape(v)[0] == 2,

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
#: 2026-09-02、狙い撃ちの網羅パスで初めて到達して足した 2 つ:
#:
#:   * warp_by_plane — ``cval`` の既定が **nan**。射影で元画像の外に出た画素を
#:     「値が無い」と言うのが契約で、0 で埋めると黒い縁が本物の絵に化ける。
#:   * triangulate — 視線が平行な対応は有限の 3-D 点を決めない。同日まで
#:     ``±inf`` を返しており、下流の ``depth > 0`` が **inf を「カメラ前方」として
#:     数えて** recover_pose の候補選択を歪めていた(``inf > 0`` は True)。
#:     NaN に直したので比較が False になり数えられない ―― NaN であること自体が
#:     契約なのでここに載せる。
#: 文書化済みの非有限を返す op(レンズ処方)。``lens_system`` の docstring が
#: 「*object_mm*: … ``inf`` for an object at infinity」と契約している通り、処方 dict の
#: ``object_mm`` は**無限遠が既定値**(平行光で近軸量を定義する)。有限に丸めると
#: 主点・焦点距離の意味が変わるので丸めない。``example_system`` は lens_system の
#: 処方をそのまま、``bend_singlet`` は ``system`` キーに同じ処方を返す(fuzz 2026-09-20 の
#: 3 件はすべてこの 1 つの inf、replay で確認)。
NONFINITE_BY_CONTRACT_PRESCRIPTION = {"lens_system", "example_system", "bend_singlet"}

#: 文書化済みの非有限を返す op(計測の「測れなかった」)。
#:   * triangulate_column — 「NaN = 未確定画素(出力も NaN)」「交点が後方(Z<=0)や視線が
#:     平面と平行な画素は NaN」(docstring)。0 にすると「距離 0 の面」と混ざる。
#:   * m3c2_distance — 「片側に min_points だけ点が無い core は nan」(docstring)。
#:     「0 を返して変化なし」にしないのが設計。
#:   * piv_cross_correlate — 「相関の峰が立たない窓(テクスチャが無い・全面一様)は nan」で、
#:     何割が nan かを ``info["valid_fraction"]`` で併せて返す(fuzz では shadow_raycast の
#:     全画素 1 の影マップが b 側に入り全窓 nan)。
#: いずれも「非有限が契約」なので載せるが、**これ以外の非有限は見逃さない**(集合を
#: 広げすぎると本物の NaN バグが黙って通る — cadmap の注記と同じ)。
NONFINITE_BY_CONTRACT_MEASURE = {"triangulate_column", "m3c2_distance", "piv_cross_correlate"}

#: 分散分析表は「検定できない行」を **nan で返す**のが契約(残差と全体の行には
#: F も p も無く、``ms`` も全体行には無い。測定者が 1 人なら交互作用も検定できない)。
#: そこを 0 で埋めると「F=0 = 完全に有意でない」と読めてしまう —— 無いものは無いと
#: 書くほうが正しいので、非有限を契約として台帳に載せる(連鎖ファザーが実検出した)。
NONFINITE_BY_CONTRACT_MSA = {"msa_anova_table"}

NONFINITE_BY_CONTRACT = {"esdf", "register_spin", "register_fpfh",
                         "sdf_union", "sdf_intersect", "sdf_subtract",
                         "sdf_smooth_union", "sdf_offset", "mat_cond",
                         "warp_by_plane", "triangulate",
                         "world_materials",     # "xyz" は空の画素が NaN(深度が無い所は世界座標も無い、docstring どおり)
                         "ball_truth",          # "markers_uv" は球の裏側の模様が NaN(docstring どおり)
                         "reproject",           # カメラの後ろ(深度 ≤ 0)の点は NaN(docstring どおり)
                         "kalman_ca",           # "innovation" は観測の無いコマ(z が NaN)で NaN
                         "ken_truth",           # "radius_px" はカメラの後ろ(深度 ≤ 0)で NaN(docstring どおり)
                         "catch_success_rate",  # "mean_lateral" は 1 回も捕れなければ nan(docstring どおり)
                         } | NONFINITE_BY_CONTRACT_METRICS \
                         | NONFINITE_BY_CONTRACT_ASTRO_FORENSICS \
                         | NONFINITE_BY_CONTRACT_OPTICS \
    | NONFINITE_BY_CONTRACT_CADMAP | NONFINITE_BY_CONTRACT_SPECULAR \
    | NONFINITE_BY_CONTRACT_PRESCRIPTION | NONFINITE_BY_CONTRACT_MEASURE \
    | NONFINITE_BY_CONTRACT_MSA

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


#: 連鎖の実行中だけ cwd を移す先。``tempfile.gettempdir()`` の下に 1 つ作る。
_SCRATCH = "fullseye_chain_fuzz_scratch"


@contextlib.contextmanager
def _scratch_cwd():
    """連鎖の実行中だけ cwd を**捨て場**へ移す。

    ★探針が作る ``text`` は ``"ラベル 31"`` のように**相対パスとして成立する**。
    パス引数を台帳で ``text`` と宣言している書き込み op(``write_3mf`` など)に
    それが渡ると、op は素直に cwd へ書く —— cwd は repo 直下なので、スイートを
    回すたびに得体の知れないファイルが生まれる。2026-09-23 の実測で 9 本あり、
    **6 本は commit にも入っていた**(`git ls-files` は octal 引用するので
    ``grep`` が当たらず、`git status` にも出ないので長く気づかなかった)。

    op 名で除外しないのは、除外台帳が「パスを text で宣言する op」が増えるたびに
    伸びるため。守るべきは個々の op ではなく「**相対パスに書く行為**」なので、
    実行の側に 1 箇所だけ置く。生成器も内側に入れてある(生成器がファイルを
    作る型に変わっても同じ捨て場に落ちる)。
    """
    d = os.path.join(tempfile.gettempdir(), _SCRATCH)
    os.makedirs(d, exist_ok=True)
    prev = os.getcwd()
    os.chdir(d)
    try:
        yield d
    finally:
        os.chdir(prev)


def run_chain(ops, gens, rng, length, log, chain_seed=None, script=None,
              explore=0.0, census=None):
    """1 連鎖 = 型付き pool を育てながら op を実行。発見は log に積む。

    *script* に op 名の列を渡すと**その順で強制実行**する(--minimize の再走)。
    型が揃わない step は黙って飛ばす = その短縮では再現しない、と判定される。
    *chain_seed* は findings に載せて再現に使う。

    *census* に ``{"ran": set(), "bind_fail": set(), "no_input": set()}`` を渡すと、
    **返り値の trace(成功した op だけ)とは別に**、op ごとの到達状況を記録する。
    返す trace で覆われた op を数えると、以下の 3 つが区別できずに全部
    「未実行」へ落ちる —— これは repo の
    「発見ゼロは未実行の偽装かもしれない」をカバレッジ側でやり直す話:

    * ``ran`` —— ``fn`` を実際に呼んだ(拒否・例外でも呼んだことに変わりない)
    * ``bind_fail`` —— 必須引数が組めず **一度も呼んでいない**
    * ``no_input`` —— 入力型が pool に無く **一度も呼んでいない**
    """
    with _scratch_cwd():
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
                    if census is not None:
                        census["no_input"].add(name)
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
                # **必須引数を組めなかった** = fn は一度も呼ばれていない。成功列
                # (trace)からも findings からも消えるので、これを数えないと
                # 「頑健で発見ゼロ」と「引数が作れず未実行」が同じ顔になる。
                if census is not None:
                    census["bind_fail"].add(name)
                continue
            args, kwargs = bound
            # ここから先は fn を必ず呼ぶ。**呼んだこと自体**を成否と別に記録する
            # (拒否された op も「実行済み」— 実行されていない op とは意味が違う)。
            if census is not None:
                census["ran"].add(name)
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
# 網羅フェーズ: 全 op を「狙い撃ち」で 1 度は走らせる                          #
# --------------------------------------------------------------------------- #
# ランダム歩行は、型が繋がっていても**踏まない** op を必ず残す。実測(2026-09-02)
# では 707 op 中 196 が 500 連鎖 x 長さ 4 で一度も走らなかった一方、型到達性の
# 不動点計算では**構造的に到達不能な op は 0 件**だった(pool は最初から全生成器
# 型で埋まるので、入力が全部種型の op は長さ 1 で届く)。つまり残り 196 は
# 「頑健だから発見が無い」でも「到達不能」でもなく、**運が悪かっただけ**。
# 運に任せる理由は無いので、op ごとに最短のレシピを組んで直接叩く。
def type_recipes(ops, gens):
    """型 → その型を 1 つ作るための op 列(種のある型は空列)。

    ラウンドごとに「今作れる型」を広げる不動点計算なので、返る列は
    **ラウンド数の意味で最短**(同ラウンド内では台帳の並び順で先勝ち)。
    """
    recipe = {t: [] for t in gens}
    changed = True
    while changed:
        changed = False
        for name, _dim, ins, out, _fn in ops:
            if out in recipe:
                continue
            if not all(t in recipe or t == "any" for t in ins):
                continue
            steps = []
            for t in ins:
                for s in recipe.get(t, ()):
                    if s not in steps:
                        steps.append(s)
            recipe[out] = steps + [name]
            changed = True
    return recipe


def cover_script(op, recipe):
    """1 op を走らせるのに必要な最短の op 列(末尾がその op)。作れなければ None。"""
    name, _dim, ins, _out, _fn = op
    steps = []
    for t in ins:
        if t == "any":
            continue              # pool は必ず埋まっているので any は無条件で充足
        r = recipe.get(t)
        if r is None:
            return None
        for s in r:
            if s not in steps:
                steps.append(s)
    return steps + [name]


def cover_all(ops, gens, log, tries=8, base_seed=90_000, verbose=True):
    """全 op を 1 度は ``fn`` まで到達させる。返り = census(ran/bind_fail/no_input)。

    op ごとに最大 *tries* 種の seed を試す。1 回で足りないのは、レシピ途中の
    producer が入力値によっては拒否して型が pool に入らないことがあるため
    (乱数由来なので seed を変えれば通る)。**到達した時点で打ち切る**ので、
    素直に通る op は 1 回で終わる。
    """
    recipe = type_recipes(ops, gens)
    census = {"ran": set(), "bind_fail": set(), "no_input": set(),
              "unbuildable": set(), "ok": set()}
    for idx, op in enumerate(ops):
        name = op[0]
        if name in census["ok"]:
            continue              # レシピの途中で既に**成功**した op は再試行しない
        script = cover_script(op, recipe)
        if script is None:
            census["unbuildable"].add(name)
            continue
        for k in range(tries):
            seed = base_seed + idx * 101 + k
            trace = run_chain(ops, gens, np.random.default_rng(seed), 0, log,
                              chain_seed=seed, script=script, census=census)
            # trace = **値を返せた** op。呼べた(ran)との差が「毎回門前払い」
            # ―― これは「実行された」と「意味のある入力で試された」の違いで、
            # 数を 1 つしか出さないと後者の欠落が前者に隠れる。
            census["ok"].update(trace)
            if name in census["ok"]:
                break
        if verbose and (idx + 1) % 100 == 0:
            print(f"  cover {idx + 1}/{len(ops)}, 実行済み {len(census['ran'])}",
                  flush=True)
    # 到達した op は「組めなかった/型が無かった」の記録から外す(最終状態を残す)
    for key in ("bind_fail", "no_input"):
        census[key] -= census["ran"]
    return census


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
    ap.add_argument("--cover-all", action="store_true",
                    help="ランダム歩行の前に、全 op を狙い撃ちで 1 度ずつ走らせる。"
                         "型が繋がっていても踏まれない op を運任せにしない")
    ap.add_argument("--cover-tries", type=int, default=8,
                    help="--cover-all で 1 op あたり試す seed 数")
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
    census = {"ran": set(), "bind_fail": set(), "no_input": set(), "unbuildable": set()}
    t0 = time.perf_counter()
    if args.cover_all:
        print(f"== 網羅フェーズ: {len(ops)} op を狙い撃ち(1 op あたり最大 "
              f"{args.cover_tries} seed)", flush=True)
        census = cover_all(ops, gens, log, tries=args.cover_tries)
        print(f"== 網羅後: fn を呼べた {len(census['ran'])}/{len(ops)} / "
              f"うち値を返せた {len(census['ok'])}")
        # 「呼べたが毎回拒否された」は**成功ゼロ**。呼べた数だけを出すと、
        # 「入力が絵に収まっていないので毎回 fail-closed」が「実行済み」に
        # 化ける ―― 未実行が発見ゼロに化けるのと同じ形の見落としである。
        refused = sorted(census["ran"] - census["ok"])
        if refused:
            print(f"   呼べたが毎回拒否 {len(refused)}: {refused[:14]}")
        for key, label in (("bind_fail", "必須引数が組めない"),
                           ("no_input", "入力型が pool に入らない"),
                           ("unbuildable", "レシピが組めない")):
            if census[key]:
                print(f"   {label} {len(census[key])}: "
                      f"{sorted(census[key])[:12]}")
        used |= census["ran"]
    for i in range(args.chains):
        # 連鎖固有 seed: 後から i 番目だけを正確に再走できる(--minimize の前提)
        chain_seed = args.seed * 1_000_003 + i
        trace = run_chain(ops, gens, np.random.default_rng(chain_seed),
                          args.length, log, chain_seed=chain_seed,
                          explore=args.explore, census=census)
        used.update(trace)
        # trace は**成功した op だけ**。実行して拒否された op を未実行に混ぜない
        used.update(census["ran"])
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
