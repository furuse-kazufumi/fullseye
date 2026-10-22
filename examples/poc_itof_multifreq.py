# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 間接 ToF(位相方式)—— 周波数を上げるほど細かく測れるが、折り返し・多重反射・縁の混合・高調波で壊れる。

    py -3.11 examples/poc_itof_multifreq.py

【問い】連続波の間接 ToF(光を f で強度変調し、戻り光との相関を 4 段の位相で測る)は、何ミリまで測れて、
どこで壊れるのか。新 op 8 本(``itof``、``opsoptics`` の ``itof``)を、閉形式・既存の op(``residue`` の CRT、
``lighttransport`` の多経路と部屋の隅の輸送、``photoncount`` の直接 ToF)で採点する。

  0. **閉形式を先に印字**: 距離 d = cφ/(4πf)、非曖昧距離 c/(2f)、4 段の位相の雑音 σ_φ = √(B/2)/A(B = オフセット、
     A = 振幅、電子数)→ σ_d = c σ_φ/(4πf)、三角波の相関の 4 段の推定 atan(u/(1−u))(u = 2φ/π)、
     多周波の非曖昧距離 c/(2·gcd f)、Wang–Xia の保証(剰余の誤差 < Γ/4)。
  1. **雑音**: 平らな壁で信号を 16 倍振り、σ_d が閉形式に乗るか(傾き −1/2)。背景光は B だけを増やす。
  2. **多周波アンラップ**: 倉庫の通路(2.1〜18.3 m)を 3 周波で撮る。1 周波は 1.25 m ごとに折り返し、3 周波の剰余を
     次数の仮説を全部試す最尤の復号で組むと 18.7 m まで一意になる。遠いほど信号が弱く、**次数を丸ごと誤って距離が
     周期の単位で飛ぶ**画素が出る。誤り率の実測を和集合の上界と突き合わせ、2 周波のうなり(古典的な方法)・
     ``residue.residue_crt``(Wang–Xia の錨の選び方)と比べる。周波数の組を変えると非曖昧距離 7.5 m の外の棚が手前に
     **折り返して映る**。
  3. **マルチパス**: (a) 半透明の板(包装フィルム)の奥の箱 —— 経路が 2 本。1 周波の距離は 2 つの間のどこかに出る
     (``lighttransport.tof_multipath_phase`` と一致)。等間隔 8 周波の行列ペンシルで 2 本に分け、分けられる
     間隔の下限を測る。(b) 部屋の隅(凹んだ部品の内角)—— 1 回反射の経路を輸送行列から並べて撮り、
     ``lighttransport.tof_transport_depth`` と一致させ、内角の面が全体に奥へ伸びることと周波数で偏りが変わることを見る。
  4. **フライングピクセル**: 卓上の箱を画素の 6 倍の細かさで描いて撮ると、縁の画素は前景と背景の間に浮く。
     ``itof_flying_pixel_mask`` で印をつけ、真値(画素内に段差がある画素)と照合する。
  5. **高調波の周期誤差**: 矩形波の変調で、壁をレールで 0〜7.4 m 動かす。誤差は閉形式の atan に一致し、
     模型の逆引きと、16 点の較正の当てはめで補正する。
  6. **背景光**: 太陽光を信号の 0〜50 倍まで足すと、σ_d は √(1 + 背景/信号) で悪くなり、遠い所から次数の誤りが噴き出す。
  7. **直接 ToF と同じ場面で比べる**: 同じ卓上の場面(包装フィルムと箱の縁)を ``photoncount`` の直接 ToF
     (光子の到達時刻のヒストグラム、ピーク)で撮る。壊れ方が違う: 直接 ToF は 2 つの山を別々に見るので、縁は
     前景か背景のどちらかに寄り(宙に浮かない)、フィルムの奥の箱の距離もずれない。
  8. **公開の実機の生データ**(3 周波 × 3 段、CC BY 4.0。データがあるときだけ走る): 生パケットを読み、
     ``itof_phase_amplitude`` と ``itof_unwrap_multifreq`` に通して、複数の姿勢から融合した真値と比べる。

【実測(seed 固定。full 約 37 s、reduced 約 6 s)】
  * 雑音: SNR ≥ 3 の 11 条件で σ_d は閉形式の 0.999〜1.029 倍。SNR 2.3 では近似が外れ 8 % 大きい。背景光 4×S で 2.10〜2.21 倍。
  * 多周波(16/80/120 MHz): 次数の誤りは σ_φ = 0.33 rad で 0.116(上界 0.132)、0.24 rad で 0.021(上界 0.020)。
    ★同じ生信号で ``residue_crt`` は 0.1161 / 0.0210 —— 最尤と同等。Wang–Xia の錨の選び方(雑音の分散が最小の帯、
    同分散なら円上の最小二乗に最も近い剰余)が効く(最も長い周期 = 16 MHz を錨にしていた修正前は 0.556 / 0.407)。
    保証 0.105 rad の外の標本には ResidueBoundWarning が出る。通路では 4 m 以内の飛び 0.1 %、8〜12 m で 31 %(上界の平均 47 %)。
  * マルチパス: フィルム(0.95 m)と箱(1.30 m)の 1 周波の距離は 1.2227 m(``tof_multipath_phase`` と一致)。8 周波の行列
    ペンシルは雑音なしで 1e-9 m まで戻し、雑音ありでは間隔 0.8 m で 100 %、0.5 m で 76 %、0.2 m 以下は 3 % 以下しか 2 cm
    に入らない。部屋の隅は全パッチで 8〜99 mm 奥へ伸び、輸送行列の 1 回反射と 1e-15 m で一致。
  * フライングピクセル: 視野内のどの面からも 4 cm 以上離れた画素 35 のうち 97 % に印、段差の無い画素を消すのは 0.03 %(閾値 4 cm・距離の 3 %・3σ。距離に比例した閾値なしでは 0.24 %)。
    直接 ToF は同じ場面で浮いた画素 0、フィルムの下の距離のずれも 0.1 mm(iToF は −70 mm)。
  * 周期誤差: 矩形波で ±84.8 mm(閉形式と 1.8e-15 rad)。模型の逆引きで 2.24 mm(雑音の床 2.14 mm)、16 点の較正で 5.20 mm。
  * 背景光: 信号の 50 倍で 4 m 以内の RMSE が 8.7 → 45.8 mm、12 m 以遠の次数の誤りが 12 % → 93 %。
  * 実データ(右半分 97,943 画素、30 cm 以上の飛び): 最尤 1 枚 0.376 / 10 枚平均 0.131、``residue_crt`` も 0.376 / 0.131
    (最尤と同等。錨を直す前は 0.559 / 0.293)。
    margin > 0.2 の画素だけ残すと 68 % が残り、飛びは 0.020。

【外部真値】閉形式(位相と距離、Lange の雑音、三角波の相関、CRT の非曖昧距離、和集合の上界)、合成シーンの既知の距離、
既存 op(``residue.residue_crt``、``lighttransport.tof_multipath_phase`` / ``tof_transport_depth``、
``photoncount.dtof_cube_simulate`` / ``dtof_cube_depth``)。【学習】0。【較正】5 章の 16 点だけ(周期誤差の当てはめ)。

★正直に書いておくこと:
  * 場面は合成(箱と床の光線追跡、反射率は手続き的な模様)。強さは Lambert(cos)と逆二乗だけで、鏡面反射・
    レンズの迷光・画素間のクロストークは入れていない。信号の電子数(1 m・反射率 1 で 4 万電子)は**模型**の値。
  * 3 次元の場面には相互反射を入れていない(フィルムの 2 経路だけ)。部屋の隅の相互反射は 2 次元(押し出し形状)の
    ``lighttransport`` の断面で別に測った。実物の凹みでは鏡面の相互反射が支配的なことが多い。
  * 周波数の組(16・80・120 MHz の 3 周波 × 3 段)は公開論文に書かれた家庭用の 3 次元センサの値に合わせた。
    ただしこの PoC は各周波数を 4 段で撮る(段の数は ``n_phases`` で変えられる)。
  * 直接 ToF との比較は**壊れ方**の比較で、雑音の比較ではない(光子の予算は方式ごとに意味が違う)。
  * 公開の生データの章(8 章)は、焦点距離・画像中心・周波数ごとの距離のオフセット(6 個)を**左半分の画素の真値で
    較正**し、右半分で採点する。真値は融合から作ったもので、論文の要求精度は 30 cm より良い程度 —— 数 cm の精度の
    評価には使えないので、30 cm 以上の飛び(次数の誤り)だけを数える。データが無ければこの章は飛ばす(CI も飛ばす)。

EXTEND: 実機の生信号を使うなら、``itof_capture`` を外し、センサの出力(周波数ごと K 段のバケット、
``(F, K, H, W)``)を ``itof_phase_amplitude`` に直接渡す。合成では「与えたから知っている」次の 3 つを、実機では
自分で決めること: (1) **段の位相の符号と原点**(θ_k = +2πk/K か −2πk/K か、0 段目がどこか)—— 間違えると距離が
c/(2f) − d に裏返る。既知の距離の平面を 2 か所に置いて確かめる。(2) **距離のオフセット**(電気配線と駆動回路の
遅延)—— ``itof_wiggling_correct`` の較正の定数項 c_0 で埋める。(3) **周波数の正確な値** —— 非曖昧距離と CRT の
次数は周波数の比で決まる。周期誤差は矩形に近い変調なら必ず出るので、レール上の平面で 16 点以上の較正を取る。
"""
from __future__ import annotations

import math
import os
import sys
import time
import warnings

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import itof as T  # noqa: E402
import lighttransport as LT  # noqa: E402
import photoncount as PC  # noqa: E402
import residue  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"

C = T.C_LIGHT
S_REF = 40000.0          # 1 m・反射率 1・正面の面からの信号電子(1 回の測定 = 4 段の合計)【模型】
CD = 0.5                 # 復調コントラスト【模型、Lange の計算例 0.4 と単純な模型の上限 0.67 の間】
READ_E = 10.0            # 読み出し雑音 [e⁻]【模型】
F_SET = (16e6, 80e6, 120e6)        # 3 周波(公開論文に書かれた家庭用センサの組と同じ値)
F_NEAR = (80e6, 100e6, 120e6)      # 非曖昧距離 7.5 m の組(比較用)
SS = 6                   # フライングピクセル用の細かさ(1 画素 = 6 × 6 標本)

FAILS: list[str] = []
GATES: list[str] = []


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


# ─────────────────────────────── 場面(箱と床の光線追跡) ───────────────────────────────
def camera_rays(w, h, fov_deg, eye, target, up=(0.0, 0.0, 1.0)):
    """ピンホールの視線 ``(h, w, 3)``(単位ベクトル)。"""
    eye = np.asarray(eye, float)
    fwd = np.asarray(target, float) - eye
    fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, up)
    right /= np.linalg.norm(right)
    upv = np.cross(right, fwd)
    fx = 0.5 * w / math.tan(math.radians(fov_deg) / 2)
    jj, ii = np.meshgrid(np.arange(w) + 0.5, np.arange(h) + 0.5)
    x = (jj - 0.5 * w) / fx
    y = -(ii - 0.5 * h) / fx
    d = fwd[None, None] + x[..., None] * right[None, None] + y[..., None] * upv[None, None]
    return d / np.linalg.norm(d, axis=-1, keepdims=True)


def cast(eye, dirs, boxes, floor_z=0.0):
    """光線と(床 + 軸に平行な箱)の最初の交点: 距離 t、法線、材料の番号、交点。"""
    eye = np.asarray(eye, float)
    t = np.full(dirs.shape[:2], np.inf)
    nrm = np.zeros(dirs.shape)
    mat = np.full(dirs.shape[:2], -1, dtype=int)
    dz = dirs[..., 2]
    with np.errstate(divide="ignore", invalid="ignore"):
        tf = (floor_z - eye[2]) / dz
    hit = (dz < 0) & (tf > 0)
    t = np.where(hit, tf, t)
    nrm[hit] = (0.0, 0.0, 1.0)
    mat[hit] = 0
    for bi, (lo, hi, m) in enumerate(boxes):
        lo, hi = np.asarray(lo, float), np.asarray(hi, float)
        with np.errstate(divide="ignore", invalid="ignore"):
            t1 = (lo[None, None] - eye[None, None]) / dirs
            t2 = (hi[None, None] - eye[None, None]) / dirs
        tmin3 = np.minimum(t1, t2)
        tmax3 = np.maximum(t1, t2)
        tmin = np.nanmax(tmin3, axis=-1)
        tmax = np.nanmin(tmax3, axis=-1)
        ok = (tmax >= tmin) & (tmin > 1e-6) & (tmin < t)
        ax = np.nanargmax(tmin3, axis=-1)
        t = np.where(ok, tmin, t)
        for a in range(3):
            sel = ok & (ax == a)
            n = np.zeros(3)
            nrm[sel] = 0.0
            nrm[sel, a] = -np.sign(dirs[sel, a])
        mat = np.where(ok, m, mat)
        del n
    pts = eye[None, None] + t[..., None] * dirs
    return t, nrm, mat, pts


def _ripple(u, v, seed, scale):
    """手続き的な模様(位相の乱れた正弦の和)—— 段ボールの繊維、木目、コンクリートのむら。"""
    rng = np.random.default_rng(seed)
    out = np.zeros_like(u)
    for _ in range(12):
        k = rng.uniform(0.5, 2.0) * scale
        th = rng.uniform(0, np.pi)
        out += np.sin(k * (u * math.cos(th) + v * math.sin(th)) + rng.uniform(0, 2 * np.pi)) / 12
    return out


def reflectivity(mat, pts, nrm, dirs):
    """近赤外の反射率 × cos(入射角)。材料: 0 床(コンクリート)/ 1 段ボール / 2 白いラベル / 3 棚の鋼材 / 4 奥の壁。"""
    u, v, z = pts[..., 0], pts[..., 1], pts[..., 2]
    base = np.select([mat == 0, mat == 1, mat == 2, mat == 3, mat == 4],
                     [0.28 + 0.05 * _ripple(u, v, 1, 9.0),
                      0.45 + 0.06 * _ripple(u + z, v - z, 2, 40.0),
                      0.82 + 0.0 * u,
                      0.20 + 0.02 * _ripple(u, z, 3, 6.0),
                      0.35 + 0.04 * _ripple(u, z, 4, 3.0)], 0.0)
    # 箱の上面のラベルにバーコード(暗い棒 = 振幅が小さい = 雑音が大きい)
    bars = (np.sin(260.0 * u) > 0.3) & (mat == 2)
    base = np.where(bars, 0.08, base)
    cosi = np.clip(-(nrm * dirs).sum(-1), 0.0, 1.0)
    return np.clip(base, 0.0, 1.0) * cosi


def tabletop(w, h, ss=1):
    """卓上(ピッキング)の場面: 床から 1.6 m の高さで斜め下を見る。段ボール箱 3 つ(上面に白いラベル)と、
    包装フィルム(床から 0.30 m の水平な半透明の板、右半分の上空)。"""
    eye = (0.0, -0.75, 1.6)
    dirs = camera_rays(w * ss, h * ss, 58.0, eye, (0.0, 0.55, 0.0))
    boxes = [((-0.55, 0.05, 0.0), (-0.15, 0.45, 0.28), 1), ((-0.45, 0.15, 0.28), (-0.25, 0.30, 0.281), 2),
             ((0.05, 0.25, 0.0), (0.40, 0.65, 0.18), 1), ((0.12, 0.35, 0.18), (0.30, 0.48, 0.181), 2),
             ((-0.05, -0.30, 0.0), (0.25, -0.05, 0.12), 1)]
    t, nrm, mat, pts = cast(eye, dirs, boxes)
    rho = reflectivity(mat, pts, nrm, dirs)
    # 包装フィルム: z = 0.30 の水平な板(x ∈ [0.0, 0.6]、y ∈ [0.1, 0.8])。表で 6 % を返し、往復で 0.85 を通す。
    ez = eye[2]
    tfilm = (0.30 - ez) / dirs[..., 2]
    pf = np.asarray(eye)[None, None] + tfilm[..., None] * dirs
    on = (pf[..., 0] > 0.0) & (pf[..., 0] < 0.6) & (pf[..., 1] > 0.1) & (pf[..., 1] < 0.8) & (tfilm < t)
    cosf = np.clip(-dirs[..., 2], 0, 1)
    film_amp = np.where(on, 0.06 * cosf / tfilm ** 2, 0.0)
    rho_eff = np.where(on, rho * 0.85, rho)
    return {"depth": t, "rho": rho_eff, "film_depth": np.where(on, tfilm, 1.0), "film_amp": film_amp,
            "film": on, "pts": pts, "dirs": dirs, "eye": np.asarray(eye), "mat": mat}


def warehouse(w, h):
    """倉庫の通路: 高さ 1.2 m から通路の奥へ。左右に棚(段ごとの箱)、17.5 m 先に壁。"""
    eye = (0.0, 0.0, 1.2)
    dirs = camera_rays(w, h, 62.0, eye, (0.0, 10.0, 0.9))
    boxes = [((-8.0, 16.6, 0.0), (8.0, 16.9, 30.0), 4)]
    rng = np.random.default_rng(5)
    for side in (-1, 1):
        x0 = 1.1 if side > 0 else -2.1
        for y in np.arange(1.0, 16.4, 2.0):                                  # 棚の柱
            boxes.append(((x0, y, 0.0), (x0 + 1.0, y + 0.08, 3.6), 3))
        for lv in (0.0, 1.2, 2.4):                                          # 棚板
            boxes.append(((x0, 1.0, lv + 0.02), (x0 + 1.0, 16.4, lv + 0.08), 3))
            for y in np.arange(1.15, 15.7, 0.65):                           # 箱
                if rng.random() < 0.8:
                    hh = rng.uniform(0.35, 0.95)
                    xin = x0 + (0.0 if side > 0 else rng.uniform(0.0, 0.3))
                    xo = x0 + 1.0 - (rng.uniform(0.0, 0.3) if side > 0 else 0.0)
                    boxes.append(((xin, y, lv + 0.08), (xo, y + rng.uniform(0.45, 0.6), lv + 0.08 + hh), 1))
    t, nrm, mat, pts = cast(eye, dirs, boxes)
    assert np.isfinite(t).all(), "warehouse: 何にも当たらない視線がある"
    return {"depth": t, "rho": reflectivity(mat, pts, nrm, dirs), "pts": pts}


# ─────────────────────────────── 0. 閉形式 ───────────────────────────────
def chapter_closed_form():
    print("\n0. 閉形式を先に印字")
    for f in (16e6, 20e6, 80e6, 100e6, 120e6):
        nb = T.itof_noise_budget(f, signal_electrons=6400.0, demod_contrast=CD, read_noise_e=READ_E)
        print("   f = %5.0f MHz: 非曖昧距離 c/(2f) = %6.3f m、S = 6400 e⁻ で σ_φ = %.4f rad → σ_d = %5.2f mm"
              % (f / 1e6, C / (2 * f), nb["phase_sigma"], nb["depth_sigma"] * 1e3))
    nb = T.itof_noise_budget(20e6, 6400.0, CD, 0.0, READ_E)
    A, B = CD * 6400 / 4, 6400 / 4
    want = C / (4 * math.pi * 20e6) * math.sqrt((B + READ_E ** 2) / 2) / A
    gate("雑音の閉形式 σ_d = c/(4πf)·√((B+σ_r²)/2)/A と op", abs(nb["depth_sigma"] - want) < 1e-15 * want + 1e-18,
         "%.6f mm" % (want * 1e3))
    # Lange の形: ΔL = (L/√8)·√B/(2A_L)。A_L は積分前の正弦の振幅 = π/2 × 標本の振幅(半周期の窓)。
    L = C / (2 * 20e6)
    lange = L / math.sqrt(8) * math.sqrt(B) / (2 * (math.pi / 2) * A)
    nb0 = T.itof_noise_budget(20e6, 6400.0, CD, 0.0, 0.0)
    gate("Lange の式(積分前の振幅 = 標本の π/2 倍)と一致", abs(lange - nb0["depth_sigma"]) < 1e-12 * lange,
         "%.6f mm と %.6f mm" % (lange * 1e3, nb0["depth_sigma"] * 1e3))
    u = np.linspace(0.02, 0.98, 49)
    est = np.arctan(u / (1 - u))
    print("   三角波の相関の 4 段: 推定 = atan(u/(1−u))、誤差の最大 %.4f rad(20 MHz で %.1f mm)"
          % (np.abs(est - u * np.pi / 2).max(), np.abs(est - u * np.pi / 2).max() * C / (4 * math.pi * 20e6) * 1e3))
    er = T.itof_unwrap_error_rate(F_SET, 0.05)
    er2 = T.itof_unwrap_error_rate(F_NEAR, 0.05)
    print("   3 周波 %s MHz: 共通の基本 %.0f MHz、非曖昧距離 %.3f m、n_i = %s、Γ = %.4f m、Wang–Xia の保証 = 位相の誤差 < %s rad"
          % ([int(f / 1e6) for f in F_SET], C / (2 * er["unambiguous_range"]) / 1e6, er["unambiguous_range"],
             er["integers"].tolist(), er["gamma"], np.round(er["guaranteed_phase_rad"], 4).tolist()))
    print("   3 周波 %s MHz: 非曖昧距離 %.3f m(この外は手前に折り返す)" % ([int(f / 1e6) for f in F_NEAR], er2["unambiguous_range"]))
    gate("非曖昧距離 c/(2·gcd f) = 18.737 m(16/80/120 MHz)", abs(er["unambiguous_range"] - C / (2 * 8e6)) < 1e-9)
    return {"tri_max": float(np.abs(est - u * np.pi / 2).max()), "U": er["unambiguous_range"],
            "U_near": er2["unambiguous_range"], "gamma": er["gamma"]}


# ─────────────────────────────── 1. 雑音 ───────────────────────────────
def chapter_noise():
    print("\n1. 雑音: 平らな壁(2.0 m、20 MHz)で信号と背景光を振る")
    n = 120 if REDUCED else 220
    wall = np.full((n, n), 2.0)
    rows = []
    for k, S in enumerate((500.0, 1000.0, 2000.0, 4000.0, 8000.0, 16000.0)):
        for amb_ratio in (0.0, 4.0):
            raw = T.itof_capture(wall, frequencies_hz=(20e6,), signal_electrons=S, demod_contrast=CD,
                                 ambient_electrons=amb_ratio * S, read_noise_e=READ_E, seed=10 + k)
            pa = T.itof_phase_amplitude(raw)
            meas = float(np.std(pa["wrapped_depth"]))
            pred = T.itof_noise_budget(20e6, S, CD, amb_ratio * S, READ_E)["depth_sigma"]
            rows.append((S, amb_ratio, meas, pred, float(np.median(pa["depth_sigma"]))))
            print("   S = %6.0f e⁻ 背景 %3.0f×S: σ_d 実測 %6.2f mm / 閉形式 %6.2f mm(比 %.3f)/ 画素ごとの見積もり %6.2f mm"
                  % (S, amb_ratio, meas * 1e3, pred * 1e3, meas / pred, rows[-1][4] * 1e3))
    r0 = [r for r in rows if r[1] == 0.0]
    snr = np.array([T.itof_noise_budget(20e6, r[0], CD, r[1] * r[0], READ_E)["snr"] for r in rows])
    ratio = np.array([r[2] / r[3] for r in rows])
    hi_snr = snr >= 3.0
    gate("σ_d の実測が閉形式の ±4 %% 以内(SNR = A/√(B+σ_r²) ≥ 3 の %d 条件)" % hi_snr.sum(),
         bool(np.all(np.abs(ratio[hi_snr] - 1) < 0.04)), "比 %.3f〜%.3f" % (ratio[hi_snr].min(), ratio[hi_snr].max()))
    print("   ★SNR < 3(%s)では小さい雑音の近似が外れ、実測が閉形式より %.0f〜%.0f %% 大きい"
          % (", ".join("%.1f" % s for s in snr[~hi_snr]), 100 * (ratio[~hi_snr].min() - 1), 100 * (ratio[~hi_snr].max() - 1)))
    sl = np.polyfit(np.log([r[0] for r in r0[2:]]), np.log([r[2] for r in r0[2:]]), 1)[0]
    gate("信号を増やすと σ_d ∝ S^(−1/2)(読み出し雑音が効かない範囲)", abs(sl + 0.5) < 0.04, "傾き %.3f" % sl)
    amb = [r for r in rows if r[1] == 4.0]
    worse = np.array([a[2] / b[2] for a, b in zip(amb, r0) if a[0] >= 2000])
    want = np.array([a[3] / b[3] for a, b in zip(amb, r0) if a[0] >= 2000])
    gate("背景光 4×S の悪化の倍率が閉形式 √((5S/4 + σ_r²)/(S/4 + σ_r²)) の ±4 % 以内(S ≥ 2000 e⁻、S が大きいと √5 = 2.24 倍)",
         bool(np.all(np.abs(worse / want - 1) < 0.04)),
         "実測 %.2f〜%.2f 倍 / 閉形式 %.2f〜%.2f 倍" % (worse.min(), worse.max(), want.min(), want.max()))
    return rows


# ─────────────────────────────── 2. 多周波アンラップ ───────────────────────────────
def mc_error_rate(freqs, S, n, seed, method="ml"):
    """平らな板(距離は一様乱数)で次数の誤り率を実測する。"""
    rng = np.random.default_rng(seed)
    U = T.itof_unwrap_error_rate(freqs, 0.1)["unambiguous_range"]
    d = rng.uniform(0.3, U - 0.3, (n, n))
    raw = T.itof_capture(d, frequencies_hz=freqs, signal_electrons=S, demod_contrast=CD, read_noise_e=READ_E,
                         seed=seed + 1)
    pa = T.itof_phase_amplitude(raw)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", residue.ResidueBoundWarning)
        un = T.itof_unwrap_multifreq(pa, method=method)
    n_warn = sum(1 for x in caught if issubclass(x.category, residue.ResidueBoundWarning))
    jump = np.abs(un["depth"] - d) > 0.25 * min(C / (2 * f) for f in freqs)
    sig = float(np.median(pa["phase_sigma"]))
    return float(jump.mean()), sig, n_warn


def chapter_unwrap():
    print("\n2. 多周波アンラップ")
    # 2a. 誤り率: 実測と和集合の上界
    n = 140 if REDUCED else 260
    rows = []
    for S in (60.0, 130.0, 200.0, 300.0, 450.0):
        rate, sig, _ = mc_error_rate(F_SET, S, n, 100 + int(S))
        rate_crt, _, warn_crt = mc_error_rate(F_SET, S, n, 100 + int(S), "crt")
        er = T.itof_unwrap_error_rate(F_SET, sig)
        rows.append((S, sig, rate, er["nearest_term"], er["union_bound"], rate_crt, warn_crt))
        print("   S = %4.0f e⁻: σ_φ = %.3f rad、次数の誤り 最尤 %.4f(和集合の上界 %.4f / 最近の 1 項 %.4f)、"
              "residue_crt %.4f" % (S, sig, rate, er["union_bound"], er["nearest_term"], rate_crt))
    ok = [r for r in rows if 3e-3 < r[2] < 0.3]
    gate("誤り率の実測が [最近の 1 項 × 0.5, 和集合の上界 × 1.3] に入る(誤り率 0.1〜30 % の条件)",
         len(ok) >= 2 and all(0.5 * r[3] <= r[2] <= 1.3 * r[4] for r in ok),
         "; ".join("%.4f ∈ [%.4f, %.4f]" % (r[2], 0.5 * r[3], 1.3 * r[4]) for r in ok))
    g_wx = T.itof_unwrap_error_rate(F_SET, 0.1)["guaranteed_phase_rad"][0]
    # ★2026-10-18: residue_crt の錨を Wang–Xia 2010(IV-A 節)どおりに直した後は、最尤の復号と同等になる。
    # 修正前(最も長い周期 = 16 MHz を常に錨にした)は 0.556 / 0.407 と大きく誤っていた。差の許容は
    # 最尤の 10 % + 標本 5 個(誤りの少ない条件で数個の入れ替わりを許す)。
    gate("residue_crt(Wang–Xia の錨の選び方: 雑音の分散が最小の帯、同分散なら円上の最小二乗に最も近い剰余)は"
         "同じ生信号で最尤の復号と同等(差が最尤の 10 % + 標本 5 個以内)",
         all(abs(r[5] - r[2]) <= 0.1 * r[2] + 5.0 / n ** 2 for r in rows),
         "; ".join("%.4f ≈ %.4f" % (r[5], r[2]) for r in rows))
    gate("residue_crt は Wang–Xia の保証(低い周波数で %.3f rad)の外の標本を黙って返さない(ResidueBoundWarning)" % g_wx,
         all(r[6] > 0 for r in rows if r[1] > g_wx),
         "; ".join("σ_φ %.3f rad: 警告 %d 回" % (r[1], r[6]) for r in rows))
    # 2b. うなり(2 周波)と CRT(最尤)
    two = (80e6, 100e6)
    cmp_rows = []
    for S in (150.0, 300.0):
        rb, _, _ = mc_error_rate(two, S, n, 300 + int(S), "beat")
        rc, sg, _ = mc_error_rate(two, S, n, 300 + int(S), "ml")
        cmp_rows.append((S, sg, rb, rc))
        print("   2 周波 80/100 MHz、S = %3.0f e⁻(σ_φ %.3f rad): うなり %.4f / 最尤 %.4f" % (S, sg, rb, rc))
    gate("同じ生信号で、最尤の復号はうなりより次数の誤りが少ない", all(r[3] < r[2] for r in cmp_rows),
         "; ".join("%.4f < %.4f" % (r[3], r[2]) for r in cmp_rows))
    # 2c. 倉庫の通路
    w, h = (160, 120) if REDUCED else (320, 240)
    sc = warehouse(w, h)
    d = sc["depth"]
    raw = T.itof_capture(d, sc["rho"], frequencies_hz=F_SET, signal_electrons=S_REF * 6, demod_contrast=CD,
                         read_noise_e=READ_E, falloff_m=1.0, seed=7)
    pa = T.itof_phase_amplitude(raw)
    un = T.itof_unwrap_multifreq(pa)
    err = un["depth"] - d
    jump = np.abs(err) > 0.3
    print("   通路 %d × %d 画素、距離 %.2f〜%.2f m: 120 MHz は %d 回折り返す。最尤の復号の後、周期単位で飛んだ画素 %.2f %%"
          % (w, h, d.min(), d.max(), int(d.max() // (C / 2 / 120e6)), 100 * jump.mean()))
    bins = [(0, 4), (4, 8), (8, 12), (12, 16), (16, 19)]
    # 画素ごとの上界: σ_φ が帯ごとにほぼ等しいので、σ = 1 の距離 D_m を求めておき、画素の σ で割る
    from scipy.special import erfc
    D1 = T.itof_unwrap_error_rate(F_SET, 1.0)["distances"]
    s_pix = np.sqrt(np.mean(pa["phase_sigma"] ** 2, axis=0))
    wh_rows = []
    for lo, hi in bins:
        sel = (d >= lo) & (d < hi)
        if sel.sum() < 50:
            continue
        sp = s_pix[sel]
        bnd = np.minimum(1.0, 0.5 * erfc(D1[None, :] / (2.0 * sp[:, None]) / math.sqrt(2.0)).sum(1))
        good = sel & ~jump
        wh_rows.append((lo, hi, int(sel.sum()), float(jump[sel].mean()), float(bnd.mean()),
                        float(np.sqrt(np.mean(err[good] ** 2))) if good.any() else float("nan"),
                        float(np.median(pa["depth_sigma"][2][sel]))))
        print("   %4.1f〜%4.1f m(%5d 画素): 飛び %.4f / 画素ごとの上界の平均 %.4f、飛ばなかった画素の RMSE %.1f mm"
              "(120 MHz 単独の見積もり %.1f mm)" % (lo, hi, sel.sum(), wh_rows[-1][3], wh_rows[-1][4], wh_rows[-1][5] * 1e3,
                                              wh_rows[-1][6] * 1e3))
    gate("遠いほど次数の誤りが増える(最も近い帯 < 最も遠い帯)", wh_rows[0][3] < wh_rows[-1][3],
         "%.4f → %.4f" % (wh_rows[0][3], wh_rows[-1][3]))
    gate("通路の距離帯ごとの飛びが、画素ごとの和集合の上界の平均 × 1.3 + 0.005 以下",
         all(r[3] <= 1.3 * r[4] + 0.005 for r in wh_rows), "; ".join("%.3f ≤ %.3f" % (r[3], 1.3 * r[4] + 0.005) for r in wh_rows))
    # 非曖昧距離 7.5 m の組では、7.5 m より奥が手前に折り返る
    raw2 = T.itof_capture(d, sc["rho"], frequencies_hz=F_NEAR, signal_electrons=S_REF * 6, demod_contrast=CD,
                          read_noise_e=READ_E, falloff_m=1.0, seed=8)
    un2 = T.itof_unwrap_multifreq(T.itof_phase_amplitude(raw2))
    far = d > un2["unambiguous_range"] + 0.2
    folded = np.abs(un2["depth"][far] - (d[far] - un2["unambiguous_range"] * np.floor(d[far] / un2["unambiguous_range"])))
    gate("80/100/120 MHz の組(非曖昧距離 7.49 m)では奥の棚が d − 7.49·k に折り返して映る",
         float(np.median(folded)) < 0.05, "奥 %d 画素、折り返しの式との差の中央値 %.1f mm" % (far.sum(), np.median(folded) * 1e3))
    return {"rows": rows, "cmp": cmp_rows, "wh": wh_rows, "scene": sc, "pa": pa, "un": un, "un_near": un2,
            "depth": d}


# ─────────────────────────────── 3. マルチパス ───────────────────────────────
def chapter_multipath():
    print("\n3. マルチパス")
    # 3a. 半透明の板(2 経路): 1 周波の距離は 2 つの間に出る
    d_film, d_box = 0.95, 1.30
    a_film, a_box = 0.10, 0.35
    seps = np.array([0.05, 0.10, 0.20, 0.35, 0.50, 0.80])
    one = np.ones((1, 1))
    raw = T.itof_capture(one * d_box, one * a_box, frequencies_hz=(20e6,), paths_depth=(one * d_film)[None],
                         paths_amplitude=(one * a_film)[None], noise=False)
    got = T.itof_phase_amplitude(raw)["wrapped_depth"][0, 0, 0]
    ref = LT.tof_multipath_phase(np.array([a_box, a_film]), np.array([2 * d_box, 2 * d_film]), 20e6)
    gate("2 経路の 1 周波の距離が lighttransport.tof_multipath_phase と一致", abs(got - ref["depth"]) < 1e-9,
         "%.6f m(箱 %.2f m、フィルム %.2f m)" % (got, d_box, d_film))
    fs8 = np.arange(1, 9) * 20e6
    raw8 = T.itof_capture(one * d_box, one * a_box, frequencies_hz=fs8, paths_depth=(one * d_film)[None],
                          paths_amplitude=(one * a_film)[None], noise=False)
    ms = T.itof_multipath_separate(T.itof_phase_amplitude(raw8))
    dd = ms["depth"][:, 0, 0]
    gate("雑音なしの 8 周波(20〜160 MHz)の行列ペンシルが 2 本の距離を復元", abs(dd[0] - d_film) < 1e-8 and abs(dd[1] - d_box) < 1e-8,
         "%.9f / %.9f m、強さの比 %.4f(真 %.4f)" % (dd[0], dd[1], ms["amplitude"][0, 0, 0] / ms["amplitude"][1, 0, 0], a_film / a_box))
    # 間隔を振る(雑音あり): 分けられる下限
    n = 60 if REDUCED else 120
    sep_rows = []
    for sp in seps:
        df = d_box - sp
        r8 = T.itof_capture(np.full((n, n), d_box), np.full((n, n), a_box), frequencies_hz=fs8,
                            signal_electrons=S_REF * 3, demod_contrast=CD, read_noise_e=READ_E,
                            paths_depth=np.full((1, n, n), df), paths_amplitude=np.full((1, n, n), a_film),
                            seed=int(sp * 1000))
        p8 = T.itof_phase_amplitude(r8)
        m8 = T.itof_multipath_separate(p8)
        e_box = np.abs(m8["depth"][1] - d_box)
        single = p8["wrapped_depth"][0]
        sep_rows.append((sp, float(np.median(e_box)), float(np.mean(e_box < 0.02)), float(np.mean(single) - d_box)))
        print("   フィルムと箱の間隔 %.2f m: 1 周波(20 MHz)の距離のずれ %+6.1f mm / 分離後の箱の誤差 中央値 %6.1f mm、2 cm 以内 %.0f %%"
              % (sp, sep_rows[-1][3] * 1e3, sep_rows[-1][1] * 1e3, 100 * sep_rows[-1][2]))
    gate("間隔 0.8 m(帯域 160 MHz の分解能 c/(2FΔf) = %.2f m の近く)なら分離後の箱が 2 cm 以内(9 割以上の画素)"
         % ms["resolution"], all(r[2] > 0.9 for r in sep_rows if r[0] >= 0.8),
         ", ".join("%.2f m: %.0f %%" % (r[0], 100 * r[2]) for r in sep_rows))
    gate("間隔 0.2 m 以下では分けられない(2 cm 以内が 1 割未満)", all(r[2] < 0.1 for r in sep_rows if r[0] <= 0.2),
         ", ".join("%.2f m: %.0f %%" % (r[0], 100 * r[2]) for r in sep_rows if r[0] <= 0.2))
    # 3b. 部屋の隅(V 溝 90°、幅 2 m、カメラは開口の 1.5 m 上)
    prof = LT.groove_profile("vgroove", n_patches=120 if REDUCED else 200, width=2.0)
    alb = 0.6
    Tm = LT.transport_matrix_radiosity(prof, albedo=alb)
    cam = np.array([0.0, 1.5])
    c = prof["centers"]
    to = cam[None] - c
    r = np.hypot(to[:, 0], to[:, 1])
    cosi = (prof["normals"] * to).sum(1) / r
    Fm = LT.form_factors_2d(prof)
    Rm = np.hypot(c[:, None, 0] - c[None, :, 0], c[:, None, 1] - c[None, :, 1])
    # 1 回反射の経路: パッチ j(直接に照らされ)→ パッチ i(画素)。強さ ρ_i F_ij ρ_j cos_j / r_j、経路長 r_j + R_ij + r_i
    a_dir = alb * cosi / r
    a_path = alb * Fm * (alb * cosi / r)[None, :]
    L_path = r[None, :] + Rm + r[:, None]
    P = c.shape[0]
    bias_rows = []
    for f in (20e6, 60e6, 120e6):
        rawc = T.itof_capture((r)[None, :], (a_dir)[None, :], frequencies_hz=(f,), paths_depth=(0.5 * L_path.T)[:, None, :],
                              paths_amplitude=a_path.T[:, None, :], noise=False)
        pc = T.itof_phase_amplitude(rawc)
        mine = pc["wrapped_depth"][0, 0]
        ref1 = LT.tof_transport_depth(Tm, camera_xz=(0.0, 1.5), modulation_hz=f, n_bounces=1)
        full = LT.tof_transport_depth(Tm, camera_xz=(0.0, 1.5), modulation_hz=f)
        bias = T._wrap((mine - r) / (C / (4 * np.pi * f))) * C / (4 * np.pi * f)
        bias_rows.append((f, bias, ref1["bias"], full["bias"]))
        print("   隅 f = %3.0f MHz: 1 回反射の偏り 最大 %+5.1f mm(輸送の 1 回反射 %+5.1f mm、全反射 %+5.1f mm)、差 %.1e m"
              % (f / 1e6, bias.max() * 1e3, ref1["bias"].max() * 1e3, full["bias"].max() * 1e3,
                 np.abs(bias - ref1["bias"]).max()))
    gate("部屋の隅: 経路を並べた itof_capture と tof_transport_depth(1 回反射)が全パッチで一致",
         all(np.abs(b[1] - b[2]).max() < 1e-9 for b in bias_rows),
         "最大の差 %.1e m(%d パッチ × 3 周波)" % (max(np.abs(b[1] - b[2]).max() for b in bias_rows), P))
    b20 = bias_rows[0][3]
    gate("部屋の隅: 全パッチで距離が伸びる(全反射、20 MHz の偏りが正)", bool((b20 > 0).all()),
         "%.1f〜%.1f mm(最大は横位置 %+.2f m、頂点付近 %.1f mm)"
         % (b20.min() * 1e3, b20.max() * 1e3, c[int(np.argmax(b20)), 0], b20[np.abs(c[:, 0]) < 0.1].mean() * 1e3))
    return {"sep": sep_rows, "single_ref": ref["depth"], "corner": bias_rows, "cx": c[:, 0], "ms": ms}


# ─────────────────────────────── 4. フライングピクセル ───────────────────────────────
def chapter_flying():
    print("\n4. フライングピクセル(卓上の箱、1 画素 = %d × %d 標本)" % (SS, SS))
    w, h = (96, 72) if REDUCED else (160, 120)
    sc = tabletop(w, h, SS)
    raw = T.itof_capture(sc["depth"], sc["rho"], frequencies_hz=F_SET, signal_electrons=S_REF, demod_contrast=CD,
                         read_noise_e=READ_E, paths_depth=sc["film_depth"][None], paths_amplitude=sc["film_amp"][None],
                         supersample=SS, falloff_m=1.0, seed=21)
    pa = T.itof_phase_amplitude(raw)
    un = T.itof_unwrap_multifreq(pa)
    d = un["depth"]
    fine = sc["depth"]
    blk = fine.reshape(h, SS, w, SS)
    dmin, dmax = blk.min(axis=(1, 3)), blk.max(axis=(1, 3))
    step = (dmax - dmin) > 0.08
    film = sc["film"].reshape(h, SS, w, SS).any(axis=(1, 3))
    # 真値: 画素の視野(細かい標本 6 × 6)に**実在する面のどれからも 4 cm 以上離れた**距離を返した画素 = 宙に浮いた点。
    # (画素内の距離の幅だけで決めると、浅い角度で見た箱の側面 —— 本当にそこにある面 —— まで数えてしまう)
    floating = step & (np.abs(blk - d[:, None, :, None]).min(axis=(1, 3)) > 0.04) & ~film
    sig = 1.0 / np.sqrt((1.0 / pa["depth_sigma"] ** 2).sum(0))          # 3 周波を合わせた距離の雑音(見積もり)
    # 閾値は 4 cm・距離の 3 %・3σ(奥の床は浅い角度で 1 画素あたり数 cm 変わるので、距離に比例した閾値が要る)
    mask = T.itof_flying_pixel_mask(d, threshold_m=0.04, rel_threshold=0.03, depth_sigma=sig) > 0
    tp = (mask & floating).sum()
    prec = tp / max(mask[~film].sum(), 1)
    rec = tp / max(floating.sum(), 1)
    flat = ~step & ~film
    fpr = (mask & flat).sum() / max(flat.sum(), 1)
    print("   段差をまたぐ画素 %d、そのうち視野内のどの面からも 4 cm 以上離れて浮いた画素 %d(%.0f %%)。印: 再現率 %.2f / 適合率 %.2f、"
          "段差の無い画素を誤って消す割合 %.2f %%" % (step.sum(), floating.sum(), 100 * floating.sum() / max(step.sum(), 1),
                                              rec, prec, 100 * fpr))
    gate("フライングピクセルの印: 浮いた画素の 8 割以上を拾い、段差の無い画素を消すのは 1 % 以下(閾値 4 cm・距離の 3 %・3σ)",
         rec >= 0.8 and fpr <= 0.01, "再現率 %.2f、誤って消す %.2f %%" % (rec, 100 * fpr))
    rows_pr = []
    for thr, rel, ns in ((0.02, 0.0, 2.0), (0.04, 0.0, 3.0), (0.04, 0.03, 3.0), (0.06, 0.03, 4.0)):
        mm = T.itof_flying_pixel_mask(d, threshold_m=thr, rel_threshold=rel, depth_sigma=sig, n_sigma=ns) > 0
        tp_ = (mm & floating).sum()
        rows_pr.append((thr, rel, ns, tp_ / max(floating.sum(), 1), tp_ / max(mm[~film].sum(), 1),
                        (mm & flat).sum() / max(flat.sum(), 1)))
        print("   閾値 %.2f m・距離の %.0f %%・%.0fσ: 再現率 %.2f / 適合率 %.2f / 誤って消す %.2f %%"
              % (thr, 100 * rel, ns, rows_pr[-1][3], rows_pr[-1][4], 100 * rows_pr[-1][5]))
    nf = ~step & ~film
    rm = float(np.sqrt(np.mean((d - raw["true_depth"])[nf] ** 2)))
    print("   段差もフィルムも無い画素の RMSE %.2f mm(3 周波の重みつき平均。奥の床は信号が弱い)" % (rm * 1e3))
    return {"scene": sc, "raw": raw, "pa": pa, "depth": d, "mask": mask, "floating": floating, "step": step,
            "film": film, "prec": prec, "rec": rec, "fpr": fpr, "pr": rows_pr, "w": w, "h": h}


# ─────────────────────────────── 5. 周期誤差 ───────────────────────────────
def chapter_wiggling():
    print("\n5. 高調波の周期誤差(矩形波の変調、20 MHz、壁をレールで 0.1〜7.4 m)")
    f = 20e6
    pos = np.linspace(0.1, 7.4, 400)
    raw = T.itof_capture(pos[None, :], frequencies_hz=(f,), waveform="square", signal_electrons=4e6,
                         demod_contrast=CD, read_noise_e=READ_E, seed=31)
    pa = T.itof_phase_amplitude(raw)
    true_phi = np.mod(4 * np.pi * f * pos / C, 2 * np.pi)
    err = T._wrap(pa["phase"][0, 0] - true_phi)
    # 閉形式: 象限ごとに atan(u/(1−u))
    q = np.floor(true_phi / (np.pi / 2))
    u = (true_phi - q * np.pi / 2) / (np.pi / 2)
    closed = T._wrap(q * np.pi / 2 + np.arctan2(u, 1 - u) - true_phi)
    rawn = T.itof_capture(pos[None, :], frequencies_hz=(f,), waveform="square", noise=False, demod_contrast=CD)
    errn = T._wrap(T.itof_phase_amplitude(rawn)["phase"][0, 0] - true_phi)
    gate("雑音なしの周期誤差が閉形式 atan(u/(1−u)) と一致", np.abs(errn - closed).max() < 1e-12,
         "最大の差 %.1e rad、誤差の振幅 %.4f rad = %.1f mm" % (np.abs(errn - closed).max(), np.abs(closed).max(),
                                                       np.abs(closed).max() * C / (4 * np.pi * f) * 1e3))
    lut = T.itof_wiggling_correct(pa)
    e_lut = T._wrap(lut["phase"][0, 0] - true_phi)
    cal_idx = np.linspace(0, pos.size - 1, 16).astype(int)
    # 較正は「レール上の 16 点」: 真の位相は既知、測定は雑音つき
    fit = T.itof_wiggling_correct(pa["phase"][:, :, :], frequencies_hz=(f,), calibration=(pa["phase"][0, 0, cal_idx], true_phi[cal_idx]),
                                  n_harmonics=2)
    e_fit = T._wrap(fit["phase"][0, 0] - true_phi)
    noise = float(np.median(pa["phase_sigma"]))
    sc = C / (4 * np.pi * f) * 1e3
    print("   誤差の RMS: 補正なし %.2f mm / 模型の逆引き %.2f mm / 16 点の較正 %.2f mm(雑音の床 %.2f mm)"
          % (np.sqrt(np.mean(err ** 2)) * sc, np.sqrt(np.mean(e_lut ** 2)) * sc, np.sqrt(np.mean(e_fit ** 2)) * sc, noise * sc))
    gate("模型の逆引きで周期誤差が雑音の床まで下がる(RMS が雑音の 1.2 倍以内)",
         np.sqrt(np.mean(e_lut ** 2)) < 1.2 * noise, "%.4f rad(雑音 %.4f)" % (np.sqrt(np.mean(e_lut ** 2)), noise))
    gate("16 点の較正(2π/4 周期の調和 2 本)で RMS が補正なしの 1/5 以下",
         np.sqrt(np.mean(e_fit ** 2)) < 0.2 * np.sqrt(np.mean(err ** 2)),
         "%.4f → %.4f rad" % (np.sqrt(np.mean(err ** 2)), np.sqrt(np.mean(e_fit ** 2))))
    return {"pos": pos, "err": err, "closed": closed, "e_lut": e_lut, "e_fit": e_fit, "cal_idx": cal_idx, "scale": sc}


# ─────────────────────────────── 6. 背景光 ───────────────────────────────
def chapter_ambient(wh):
    print("\n6. 背景光(太陽光を信号の 0〜50 倍): 通路の場面、3 周波")
    sc = wh["scene"]
    d = sc["depth"]
    rows = []
    sig_e = S_REF * 6 * sc["rho"] / d ** 2
    for k, ratio in enumerate((0.0, 2.0, 8.0, 20.0, 50.0)):
        raw = T.itof_capture(d, sc["rho"], frequencies_hz=F_SET, signal_electrons=S_REF * 6, demod_contrast=CD,
                             ambient_electrons=ratio * float(np.median(sig_e)), read_noise_e=READ_E, falloff_m=1.0,
                             seed=40 + k)
        pa = T.itof_phase_amplitude(raw)
        un = T.itof_unwrap_multifreq(pa)
        jump = np.abs(un["depth"] - d) > 0.3
        near = d < 4
        far = d > 12
        good = ~jump & near
        rows.append((ratio, float(jump[near].mean()), float(jump[far].mean()),
                     float(np.sqrt(np.mean((un["depth"] - d)[good] ** 2))) if good.any() else float("nan")))
        print("   背景 %4.0f × 信号の中央値: 次数の誤り 4 m 以内 %.4f / 12 m 以遠 %.4f、4 m 以内の RMSE %.1f mm"
              % (ratio, rows[-1][1], rows[-1][2], rows[-1][3] * 1e3))
    gate("背景光が増えるほど遠い所の次数の誤りが増える(単調)", all(rows[i][2] <= rows[i + 1][2] + 1e-9 for i in range(len(rows) - 1)),
         " → ".join("%.3f" % r[2] for r in rows))
    gate("背景光が増えるほど近い所の RMSE が増える(単調)", all(rows[i][3] < rows[i + 1][3] for i in range(len(rows) - 1)),
         " → ".join("%.1f" % (r[3] * 1e3) for r in rows))
    return rows


# ─────────────────────────────── 7. 直接 ToF と比べる ───────────────────────────────
def chapter_dtof(fl):
    print("\n7. 直接 ToF(光子の到達時刻のヒストグラム)と同じ卓上の場面で比べる")
    sc = fl["scene"]
    w, h = fl["w"], fl["h"]
    bins, bin_ps = 280, 100.0
    # 画素の開口を通る光は線形に足し合わさる → 細かい標本ごとの期待値の立方体を作り、画素に足してから Poisson
    fine = sc["depth"]
    cube = np.zeros((h, w, bins))
    sig_ph = 2000.0                                  # 1 m・反射率 1 の光子数(反射率 0.3・2 m で約 150 光子)
    for dy in range(SS):
        for dx in range(SS):
            dsub = fine[dy::SS, dx::SS]
            rsub = sc["rho"][dy::SS, dx::SS] / dsub ** 2
            cube += PC.dtof_cube_simulate(dsub, bins=bins, bin_ps=bin_ps, reflectivity=rsub, signal_photons=sig_ph,
                                          ambient_photons=0.0, irf_fwhm_ps=200.0, noise=False) / SS ** 2
            fd = sc["film_depth"][dy::SS, dx::SS]
            fa = sc["film_amp"][dy::SS, dx::SS]
            if (fa > 0).any():
                cube += PC.dtof_cube_simulate(fd, bins=bins, bin_ps=bin_ps, reflectivity=fa, signal_photons=sig_ph,
                                              ambient_photons=0.0, irf_fwhm_ps=200.0, noise=False) / SS ** 2
    cube += 5.0 / bins
    cube = np.random.default_rng(51).poisson(cube).astype(np.float64)
    dt = PC.dtof_cube_depth(cube, bin_ps=bin_ps, mode="gaussian")
    blk = fine.reshape(h, SS, w, SS)
    dmin, dmax = blk.min(axis=(1, 3)), blk.max(axis=(1, 3))
    step = fl["step"]
    film = fl["film"]
    float_d = step & (np.abs(blk - dt[:, None, :, None]).min(axis=(1, 3)) > 0.04) & ~film
    float_i = fl["floating"]
    print("   段差をまたぐ画素 %d: 間に浮いた画素 iToF %d(%.0f %%)/ 直接 ToF %d(%.0f %%)"
          % (step.sum(), float_i.sum(), 100 * float_i.sum() / step.sum(), float_d.sum(), 100 * float_d.sum() / step.sum()))
    gate("直接 ToF は縁で宙に浮かない(浮いた画素が iToF の 1/4 以下)", float_d.sum() <= 0.25 * float_i.sum(),
         "%d と %d" % (float_d.sum(), float_i.sum()))
    # フィルムの奥の箱の距離
    tr = fl["raw"]["true_depth"]
    sel = film & ~step & (np.abs(tr - np.median(tr[film & ~step])) < 0.5)
    e_i = np.median(fl["depth"][sel] - tr[sel])
    e_d = np.median(dt[sel] - tr[sel])
    print("   フィルムの下の画素 %d: 距離のずれの中央値 iToF %+.1f mm / 直接 ToF %+.1f mm"
          % (sel.sum(), e_i * 1e3, e_d * 1e3))
    gate("フィルムの下: iToF は手前に引かれ(−5 mm より大きいずれ)、直接 ToF はずれない(±5 mm)",
         e_i < -0.005 and abs(e_d) < 0.005, "%+.1f / %+.1f mm" % (e_i * 1e3, e_d * 1e3))
    return {"dt": dt, "float_d": float_d}


# ─────────────────────────────── 8. 公開の生データ(あれば) ───────────────────────────────
#: 公開データ: F. J. Lawin, P.-E. Forssén, H. Ovrén, "Efficient Multi-Frequency Phase Unwrapping using Kernel Density
#: Estimation", ECCV 2016 のデータ(Zenodo, DOI 10.5281/zenodo.19608956, CC BY 4.0)。家庭用の 3 次元センサの生パケット
#: (3 周波 × 3 段、画素 512 × 424)を 1 場面あたり数十枚と、複数の姿勢から融合した真値の距離(z、mm)。
#: repo には同梱しない。zip の logs/<場面>.h5 と data/<場面>_gt.bin を 1 つのディレクトリに置き、
#: 環境変数 FULLSEYE_ITOF_DATA でそのディレクトリを指す(既定の場面は library)。
REAL_FREQS = np.array([80e6, 16e6, 120e6])           # 生パケットの副画像 0–2 / 3–5 / 6–8 の周波数
REAL_STEPS = np.array([0.0, 2.094395, 4.18879])      # 段の参照位相(この形式では e^{−iθ} で合わせる → 渡すのは −θ)
REAL_SUB_BYTES = 298496                              # 副画像 1 枚のバイト数(11 bit × 512 × 424 を詰めたもの)


def _lut11to16():
    """11 bit の符号つき対数圧縮 → 16 bit(オープンソースのドライバ libfreenect2 の段 1 の移植、Apache-2.0)。"""
    lut = np.zeros(2048, np.int64)
    y = 0
    for x in range(1024):
        inc = 1 << (x // 128 - (1 if x >= 128 else 0))
        lut[x] = y
        lut[1024 + x] = -y
        y += inc
    lut[1024] = 32767                                 # 飽和の印
    return lut


def read_public_raw(directory, scene="library", n_frames=10):
    """公開の生パケットを読み、``(枚, F=3, K=3, 424, 510)`` のバケット、画素ごとの参照位相のずれ ``(3, 424, 510)``、
    飽和の印、真値の z [m] を返す。データは信頼しない入力として数値だけを読む(h5py)。"""
    import h5py
    lut = _lut11to16()
    xs, ys = np.arange(512), np.arange(424)
    r1zi = ((xs >> 2) + ((xs & 3) << 7)) * 11
    r1yi, sh = r1zi >> 4, r1zi & 15
    row = np.where(ys < 212, ys + 212, 423 - ys)
    idx = row[:, None] * 352 + r1yi[None, :]
    with h5py.File(os.path.join(directory, "%s.h5" % scene), "r") as f:
        raw = f["P0Tables"][()].tobytes()
        if len(raw) < 34 + 3 * (2 * 512 * 424 + 2):
            raise ValueError("P0Tables が短すぎる(%d バイト)" % len(raw))
        off, p0 = 34, []
        for _ in range(3):
            p0.append(np.frombuffer(raw, "<u2", 512 * 424, off).reshape(424, 512).astype(np.float64)[::-1])
            off += 2 * 512 * 424 + 2
        names = sorted([k for k in f.keys() if k.startswith("Frame_")], key=lambda s: int(s.split("_")[1]))[:n_frames]
        frames, sat = [], np.zeros((424, 512), bool)
        for nm in names:
            buf = f[nm]["Ir"][()].tobytes()
            if len(buf) < 9 * REAL_SUB_BYTES:
                raise ValueError("%s の生パケットが短すぎる(%d バイト)" % (nm, len(buf)))
            s = np.empty((3, 3, 424, 512))
            for k in range(3):
                for j in range(3):
                    w = np.frombuffer(buf, "<u2", REAL_SUB_BYTES // 2, REAL_SUB_BYTES * (3 * k + j)).astype(np.int64)
                    w = np.concatenate([w, [0]])
                    v = ((w[idx] >> sh[None, :]) | (w[idx + 1] << (16 - sh[None, :]))) & 2047
                    sat |= v == 1024
                    s[k, j] = lut[v]
            frames.append(s)
    # 生の並びは上下が逆(ドライバと同じく反転)。左右の端の 1 列ずつは真値に無い。
    smp = np.stack(frames)[..., ::-1, :][..., 1:511]
    base = (np.stack(p0) * 0.000031 * np.pi)[..., ::-1, :][..., 1:511]      # 画素ごとの参照位相のずれ [rad]
    gt = np.fromfile(os.path.join(directory, "%s_gt.bin" % scene), np.float32)
    if gt.size != 510 * 424:
        raise ValueError("真値の大きさが合わない(%d)" % gt.size)
    gt = gt.reshape(510, 424).T.astype(np.float64) / 1000.0
    return smp, base, sat[::-1][:, 1:511], gt


def chapter_real_data():
    print("\n8. 公開の生データ(実機の 3 周波 × 3 段)で、最尤の復号と residue_crt を真値と突き合わせる")
    directory = os.environ.get("FULLSEYE_ITOF_DATA")
    if not directory or not os.path.isfile(os.path.join(directory, "library.h5")):
        print("   データが無いので飛ばす(Zenodo 10.5281/zenodo.19608956、CC BY 4.0。置き場所は環境変数 FULLSEYE_ITOF_DATA)")
        return None
    from scipy.optimize import least_squares
    smp, base, sat, gt = read_public_raw(directory, n_frames=4 if REDUCED else 10)
    period = C / (2 * REAL_FREQS)
    # 位相: 段の参照位相を渡して op で解き、画素ごとのずれを足す
    Z, A1, B1, ph1 = 0.0, None, None, None
    for i in range(smp.shape[0]):
        pa = T.itof_phase_amplitude(smp[i], REAL_FREQS, phase_offsets_rad=-REAL_STEPS)
        ph = np.mod(pa["phase"] + base, 2 * np.pi)
        if i == 0:
            ph1, A1, B1 = ph, pa["amplitude"], pa["offset"]
        Z = Z + pa["amplitude"] * np.exp(1j * ph)
    phm, Am = np.mod(np.angle(Z), 2 * np.pi), np.abs(Z) / smp.shape[0]
    H, W = gt.shape
    u = np.arange(1, 511)[None, :] * np.ones((H, 1))
    v = np.arange(H)[:, None] * np.ones((1, W))
    valid = (gt > 0) & ~sat
    calib, evalm = valid & (u < 255), valid & (u >= 255)

    # 較正(左半分の画素だけ): 焦点距離・画像中心(z → 視線に沿った距離)と、周波数ごとの距離のオフセット(系の遅延)
    def resid(x, sel):
        fx, cx, cy = x[:3]
        r = gt[sel] * np.sqrt(1 + ((u[sel] - cx) / fx) ** 2 + ((v[sel] - cy) / fx) ** 2)
        return np.concatenate([(np.mod(phm[k][sel] / (2 * np.pi) * period[k] - r - x[3 + k] + period[k] / 2, period[k])
                                - period[k] / 2) / period[k] * 2 * np.pi for k in range(3)])

    rng = np.random.default_rng(0)
    sel = np.zeros_like(calib)
    sel.flat[rng.choice(np.flatnonzero(calib), 20000, replace=False)] = True
    best = None
    for fx0 in (300.0, 360.0, 420.0):
        for o0 in (-0.1, 0.0, 0.1):
            r = least_squares(resid, [fx0, W / 2, H / 2, o0, o0, o0], args=(sel,), loss="soft_l1", f_scale=0.1)
            if best is None or r.cost < best.cost:
                best = r
    fx, cx, cy = best.x[:3]
    offs = best.x[3:]
    print("   較正(左半分の 2 万画素): 焦点距離 %.1f px、中心 (%.1f, %.1f)、距離のオフセット %s mm"
          % (fx, cx, cy, ", ".join("%+.0f(%d MHz)" % (o * 1e3, f / 1e6) for o, f in zip(offs, REAL_FREQS))))
    rgt = gt * np.sqrt(1 + ((u - cx) / fx) ** 2 + ((v - cy) / fx) ** 2)
    res = {}
    for name, ph, wgt in (("1 枚", ph1, A1 ** 2 / np.maximum(B1, 1.0)), ("%d 枚の平均" % smp.shape[0], phm, Am ** 2)):
        phc = np.stack([np.mod(ph[k] - 2 * np.pi * offs[k] / period[k], 2 * np.pi) for k in range(3)])
        for meth in ("ml", "crt"):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", residue.ResidueBoundWarning)   # 保証の外の画素は飛びとして数える
                un = T.itof_unwrap_multifreq(phc, REAL_FREQS, weights=wgt, method=meth)
            e = un["depth"] - rgt
            jump = np.abs(e) > 0.3
            res[(name, meth)] = (float(jump[evalm].mean()), un, e)
            print("   %s・%s: 右半分の %d 画素で 30 cm 以上飛んだ割合 %.3f、飛ばなかった画素の誤差の中央値 %.1f mm"
                  % (name, "最尤" if meth == "ml" else "residue_crt", evalm.sum(), jump[evalm].mean(),
                     1e3 * np.median(np.abs(e[evalm & ~jump]))))
        for k in np.argsort(REAL_FREQS):
            d = phc[k] / (2 * np.pi) * period[k]
            ew = np.mod(d - rgt + period[k] / 2, period[k]) - period[k] / 2
            print("      %s %3.0f MHz 単独の折り返した距離の誤差(中央値)%.1f mm"
                  % (name, REAL_FREQS[k] / 1e6, 1e3 * np.median(np.abs(ew[evalm]))))
    avg = "%d 枚の平均" % smp.shape[0]
    gate("実データ: residue_crt(Wang–Xia の錨)は最尤の復号と同等(1 枚でも平均でも、飛びの差が最尤の 10 % 以内)",
         all(abs(res[(k, "crt")][0] - res[(k, "ml")][0]) <= 0.1 * res[(k, "ml")][0] for k in ("1 枚", avg)),
         "1 枚 %.4f ≈ %.4f、平均 %.4f ≈ %.4f" % (res[("1 枚", "crt")][0], res[("1 枚", "ml")][0], res[(avg, "crt")][0],
                                              res[(avg, "ml")][0]))
    gate("実データ: 枚数を平均すると飛びが減る(最尤)", res[(avg, "ml")][0] < res[("1 枚", "ml")][0],
         "%.3f → %.3f" % (res[("1 枚", "ml")][0], res[(avg, "ml")][0]))
    un, e = res[(avg, "ml")][1], res[(avg, "ml")][2]
    jump = np.abs(e) > 0.3
    rows = []
    for q in (0.0, 0.1, 0.2, 0.3):
        keep = evalm & (un["margin"] > q)
        rows.append((q, keep.sum() / evalm.sum(), float(jump[keep].mean())))
        print("   採点の差(margin)> %.1f の画素だけ残す: 残る割合 %.2f、その中で飛んだ割合 %.4f" % rows[-1])
    gate("実データ: margin > 0.2 で残した画素の飛びは全体の 1/3 以下(次数が際どい画素を捨てられる)",
         rows[2][2] <= rows[0][2] / 3, "%.4f / %.4f" % (rows[2][2], rows[0][2]))
    rr = []
    for lo, hi in ((0, 4), (4, 8), (8, 12), (12, 18)):
        s_ = evalm & (rgt >= lo) & (rgt < hi)
        if s_.sum() > 500:
            rr.append((lo, hi, int(s_.sum()), float(jump[s_].mean())))
            print("   %2d〜%2d m(%6d 画素): 飛び %.3f" % rr[-1])
    return {"rgt": rgt, "res": res, "evalm": evalm, "avg": avg, "margin_rows": rows, "Am": Am, "range_rows": rr}


# ─────────────────────────────── 図 ───────────────────────────────
def _depth_rgb(d, lo, hi, cmap="turbo"):
    import imgio
    return imgio.apply_cmap(np.clip((d - lo) / (hi - lo), 0, 1), name=cmap)


def _pointcloud(depth, dirs_center, eye, mask=None, color=None):
    pts = eye[None, None] + depth[..., None] * dirs_center
    return pts.reshape(-1, 3)


def make_figures(cf, noise, uw, mp, fl, wg, amb, dt, real):
    import studio
    import fullseye as fs

    # 1. 通路: 振幅・真値・1 周波の折り返し・3 周波の復号・誤差・非曖昧距離 7.49 m の組
    d = uw["depth"]
    wrapped = uw["pa"]["wrapped_depth"]
    amp = uw["pa"]["amplitude"][2]
    U = cf["U"]
    figs.save_grid("warehouse_unwrap",
                   [np.sqrt(amp / np.percentile(amp, 99.5)), _depth_rgb(d, 0, U), _depth_rgb(wrapped[2], 0, C / (2 * 120e6)),
                    _depth_rgb(uw["un"]["depth"], 0, U), np.clip(uw["un"]["depth"] - d, -0.1, 0.1),
                    _depth_rgb(uw["un_near"]["depth"], 0, U)],
                   captions=["振幅(120 MHz、明るさは平方根)", "真の距離 %.1f〜%.1f m" % (d.min(), d.max()),
                             "120 MHz 単独(1.25 m で折り返す)", "16/80/120 MHz の最尤の復号(%.1f m まで一意)" % U,
                             "誤差 ±10 cm(橙 = 手前・青 = 奥に飛んだ画素)", "80/100/120 MHz(非曖昧距離 7.49 m)"],
                   signed=[False, False, False, False, True, False], gray=[True, False, False, False, False, False],
                   ncols=3,
                   caption="倉庫の通路を 3 周波の間接 ToF で撮る。120 MHz の位相は 1.25 m ごとに折り返す。3 周波の剰余を全部の"
                           "次数の仮説で採点すると %.1f m まで一意になるが、遠い棚ほど信号が弱く、次数を丸ごと誤った画素が点状に出る"
                           "(誤差の図)。周波数の最大公約数が 20 MHz の組では 7.49 m より奥が何の警告も無く手前に折り返して映る(右下)。"
                           % U)
    # 2. 次数の誤り率: 実測と上界
    rows = uw["rows"]
    figs.save_plot("unwrap_error_rate",
                   [("実測(16/80/120 MHz、最尤の復号)", np.array([r[1] for r in rows]), np.log10(np.maximum([r[2] for r in rows], 1e-5))),
                    ("和集合の上界", np.array([r[1] for r in rows]), np.log10(np.maximum([r[4] for r in rows], 1e-5))),
                    ("最近の 1 項", np.array([r[1] for r in rows]), np.log10(np.maximum([r[3] for r in rows], 1e-5)))],
                   xlabel="位相の雑音 σ_φ [rad]", ylabel="log10(次数を誤る確率)", title="多周波アンラップの誤り率",
                   kinds=["scatter", "line", "line"], styles=[None, "dashed", "dotted"], colors=["emphasis", "reference", "neutral"],
                   caption="平らな板(距離は一様乱数)で信号を振り、次数を誤った画素の割合を数えた。破線は候補ごとのガウスの 2 仮説の"
                           "誤りの和(和集合の上界)、点線はその最大の 1 項。実測は 2 本の間に入る。")
    # 3. 通路の距離帯ごと
    wh = uw["wh"]
    xs = np.array([(r[0] + r[1]) / 2 for r in wh])
    figs.save_plot("warehouse_by_range",
                   [("次数の誤り(実測)", xs, np.log10(np.maximum([r[3] for r in wh], 1e-5))),
                    ("和集合の上界(画素ごとの σ_φ の中央値から)", xs, np.log10(np.maximum([r[4] for r in wh], 1e-5)))],
                   xlabel="距離 [m]", ylabel="log10(誤り率)", title="遠いほど次数を誤る",
                   kinds=["scatter", "line"], styles=[None, "dashed"], colors=["emphasis", "reference"],
                   caption="通路の画素を距離帯に分け、次数を誤った割合と、その帯の位相雑音から見積もった上界を並べた。信号は距離の 2 乗で弱まる。")
    # 5. マルチパス: 間隔
    sep = mp["sep"]
    figs.save_plot("film_separation",
                   [("1 周波 20 MHz の距離のずれ", np.array([r[0] for r in sep]), np.log10(np.array([abs(r[3]) for r in sep]) * 1e3)),
                    ("8 周波の分離後の箱の誤差(中央値)", np.array([r[0] for r in sep]), np.log10(np.array([r[1] for r in sep]) * 1e3))],
                   xlabel="フィルムと箱の間隔 [m]", ylabel="log10(誤差 [mm])", title="半透明のフィルムの奥の箱",
                   kinds=["line", "line"], styles=["dashed", None], colors=["wrong", "right"],
                   caption="フィルム(反射 10 %)の奥の箱(35 %)。1 周波の距離は 2 つの経路の間に引かれる。等間隔 8 周波(20〜160 MHz)の"
                           "行列ペンシルで 2 本に分けると、間隔が大きいほど箱の距離が戻り、近すぎると分けられない。")
    # 6. 隅の偏り
    cx = mp["cx"]
    ser = []
    for f, b1, _r1, bfull in mp["corner"]:
        ser.append(("%d MHz(全反射)" % int(f / 1e6), cx, bfull * 1e3))
    ser.append(("20 MHz(1 回反射、経路を並べて撮影)", cx, mp["corner"][0][1] * 1e3))
    figs.save_plot("corner_bias", ser, xlabel="隅の断面の横位置 [m](0 = 頂点)", ylabel="距離のずれ [mm]",
                   title="部屋の隅(90° の V、反射率 0.6)の距離の伸び",
                   styles=[None, None, None, "dashed"], colors=["emphasis", "neutral", "right", "reference"],
                   caption="向かいの壁で 1 回以上反射した光が遅れて混ざり、内角の面は全体に奥へ伸びる。頂点そのものでは向かいの面が"
                           "近く遅れが小さいので偏りは小さく、頂点から 0.3〜0.5 m 離れた所で最大になる。周波数で偏りの形が変わる(高い周波数"
                           "では遠回りの経路の位相が回って打ち消し合う)。破線は経路を並べて itof_capture で撮ったもので、輸送行列の 1 回反射と一致する。")
    # 7. フライングピクセル: 1 行の断面と、箱の点群を横から
    import imgio
    sc = fl["scene"]
    h, w = fl["h"], fl["w"]
    dirs_c = sc["dirs"][SS // 2::SS, SS // 2::SS]
    eye = sc["eye"]
    tgt = np.array([-0.35, 0.25, 0.28]) - eye                  # 左の箱の上面の中央を通る行
    tgt /= np.linalg.norm(tgt)
    r0 = int(np.unravel_index(np.argmax((dirs_c * tgt).sum(-1)), (h, w))[0])
    xf = (np.arange(w * SS) + 0.5) / SS
    xp = np.arange(w) + 0.5
    fine_row = sc["depth"][r0 * SS + SS // 2]
    flag = fl["mask"][r0] > 0
    figs.save_plot("flying_pixel_profile",
                   [("真の面(画素の 1/6 の細かさ)", xf, fine_row), ("iToF 3 周波", xp, fl["depth"][r0]),
                    ("直接 ToF(ピーク)", xp, dt["dt"][r0]), ("フライングピクセルの印", xp[flag], fl["depth"][r0][flag])],
                   xlabel="画像の列 [画素](%d 行目)" % r0, ylabel="距離 [m]", title="箱をまたぐ 1 行の距離",
                   kinds=["line", "scatter", "scatter", "scatter"], styles=["dashed", None, None, None],
                   colors=["reference", "emphasis", "right", "wrong"],
                   caption="左の箱の上面を通る 1 行。iToF は箱の縁の画素で前景と背景の間の距離を返す(宙に浮いた点)。直接 ToF は"
                           "2 つの山のどちらかを選ぶので、縁の画素も前景か背景のどちらかに乗る。右側(列 113〜135 付近)は包装フィルムの下で、"
                           "iToF だけが手前に引かれている。")
    Pt = (eye[None, None] + fl["depth"][..., None] * dirs_c).reshape(-1, 3)
    mflag = fl["mask"].reshape(-1) > 0
    box = (Pt[:, 0] > -0.75) & (Pt[:, 0] < 0.05) & (Pt[:, 1] > -0.1) & (Pt[:, 1] < 0.75) & (Pt[:, 2] > -0.06) & (Pt[:, 2] < 0.45)
    Q, mq = Pt[box], mflag[box]
    cz = imgio.apply_cmap(np.clip((Q[:, 2] + 0.05) / 0.4, 0, 1).reshape(1, -1), name="viridis")[0]
    cols = np.where(mq[:, None], np.array([0.95, 0.25, 0.2])[None], cz)
    center = np.array([-0.35, 0.3, 0.15])
    view = studio.render_points_frame(Q, cols, yaw=90.0, pitch=15.0, zoom=1.3, size=560, point_px=2, center=center, radius=0.6)
    view2 = studio.render_points_frame(Q[~mq], cz[~mq], yaw=90.0, pitch=15.0, zoom=1.3, size=560, point_px=2,
                                       center=center, radius=0.6)
    figs.save_grid("flying_pixels_side",
                   [view, view2], captions=["箱の点群を横から(赤 = フライングピクセルの印、色 = 高さ)", "印を除いた点群"], ncols=2,
                   caption="左の箱(高さ 28 cm)の点群を横から見た。箱の縁から背後の床へ、カメラの視線に沿って宙に浮いた点の列が伸びる"
                           "(画素の視野が段差をまたぎ、2 つの位相が混ざった)。印は浮いた点の %.0f %% を拾い、段差の無い画素を消すのは %.2f %%。"
                           % (100 * fl["rec"], 100 * fl["fpr"]))
    # 8. 直接 ToF と比べる
    tr = fl["raw"]["true_depth"]
    figs.save_grid("itof_vs_dtof",
                   [_depth_rgb(tr, 1.2, 2.6), np.clip(fl["depth"] - tr, -0.06, 0.06), np.clip(dt["dt"] - tr, -0.06, 0.06),
                    fl["pa"]["amplitude"][1] / np.percentile(fl["pa"]["amplitude"][1], 99)],
                   captions=["真の距離(画素内の平均)", "iToF 3 周波の誤差 ±6 cm", "直接 ToF(ピーク)の誤差 ±6 cm", "iToF の振幅(80 MHz)"],
                   signed=[False, True, True, False], ncols=2, gray=[False, False, False, True],
                   caption="同じ卓上の場面を 2 つの方式で撮る。iToF はフィルムの下が手前に引かれ、箱の縁に沿って誤差の線が出る(フライング"
                           "ピクセル)。直接 ToF は 2 つの山を別々に見るので、縁はどちらかの面に寄り、フィルムの下もずれない。")
    # 9. 周期誤差
    sc_ = wg["scale"]
    figs.save_plot("wiggling",
                   [("補正なし(実測)", wg["pos"], wg["err"] * sc_), ("閉形式 atan(u/(1−u))", wg["pos"], wg["closed"] * sc_),
                    ("模型の逆引き", wg["pos"], wg["e_lut"] * sc_), ("16 点の較正", wg["pos"], wg["e_fit"] * sc_)],
                   xlabel="レール上の壁の位置 [m]", ylabel="距離の誤差 [mm]", title="矩形波の変調の周期誤差(20 MHz、4 段)",
                   styles=[None, "dashed", None, None], colors=["wrong", "reference", "right", "emphasis"],
                   kinds=["scatter", "line", "line", "line"],
                   caption="矩形どうしの相関は三角波で、4 段の推定に 3 次と 5 次の高調波が折り返し、誤差が 1.87 m(位相 π/2)ごとに波打つ。"
                           "閉形式に一致し、模型の逆引きか 16 点の較正で雑音の床まで下がる。")
    # 10. 背景光
    figs.save_plot("ambient",
                   [("4 m 以内の RMSE [mm]", np.array([r[0] for r in amb]), np.array([r[3] for r in amb]) * 1e3),
                    ("12 m 以遠の次数の誤り [%]", np.array([r[0] for r in amb]), np.array([r[2] for r in amb]) * 100)],
                   xlabel="背景光 / 信号(中央値)", ylabel="mm / %", title="太陽光は B だけを増やす",
                   colors=["emphasis", "wrong"],
                   caption="背景光は振幅 A を増やさずオフセット B(とショット雑音 √B)だけを増やす。近い所は雑音が増え、遠い所では次数の誤りが噴き出す。")
    # 11. 雑音の閉形式
    r0 = [r for r in noise if r[1] == 0.0]
    r4 = [r for r in noise if r[1] == 4.0]
    figs.save_plot("noise_closed_form",
                   [("実測(背景なし)", np.log10([r[0] for r in r0]), np.log10([r[2] * 1e3 for r in r0])),
                    ("閉形式", np.log10([r[0] for r in r0]), np.log10([r[3] * 1e3 for r in r0])),
                    ("実測(背景 4×S)", np.log10([r[0] for r in r4]), np.log10([r[2] * 1e3 for r in r4])),
                    ("閉形式(背景 4×S)", np.log10([r[0] for r in r4]), np.log10([r[3] * 1e3 for r in r4]))],
                   xlabel="log10(信号電子 S)", ylabel="log10(σ_d [mm])", title="4 段の位相の雑音(20 MHz、壁 2 m)",
                   kinds=["scatter", "line", "scatter", "line"], styles=[None, "dashed", None, "dashed"],
                   colors=["emphasis", "reference", "wrong", "reference"],
                   caption="σ_d = c/(4πf)·√((B + σ_r²)/2)/A。信号を 4 倍にすると σ_d は半分。背景光は B を増やすだけ。")
    # 12. 公開の生データ(あるときだけ)
    if real is not None:
        un = real["res"][(real["avg"], "ml")][1]
        e_ml = real["res"][(real["avg"], "ml")][2]
        e_crt = real["res"][(real["avg"], "crt")][2]
        ok = real["evalm"] | (real["rgt"] > 0)
        figs.save_grid("public_raw_unwrap",
                       [_depth_rgb(np.where(real["rgt"] > 0, real["rgt"], 0), 0, 18.7), _depth_rgb(un["depth"], 0, 18.7),
                        np.where(ok, np.clip(e_ml, -0.5, 0.5), 0), np.where(ok, np.clip(e_crt, -0.5, 0.5), 0)],
                       captions=["真値(複数の姿勢から融合、視線に沿った距離)", "3 周波の最尤の復号(%s)" % real["avg"],
                                 "最尤の誤差 ±0.5 m", "residue_crt の誤差 ±0.5 m"],
                       signed=[False, False, True, True], ncols=2,
                       caption="実機の生データ(3 周波 × 3 段)を itof_phase_amplitude と itof_unwrap_multifreq に通し、真値と比べた。"
                               "左半分で焦点距離・中心・周波数ごとのオフセットを較正し、右半分で採点した。錨を Wang–Xia の"
                               "選び方にした residue_crt は最尤と同等。データ: Lawin, Forssén, Ovrén (ECCV 2016)、Zenodo 10.5281/zenodo.19608956、CC BY 4.0。")
        mr = real["margin_rows"]
        figs.save_plot("public_raw_margin",
                       [("残る画素の割合", np.array([r[0] for r in mr]), np.array([r[1] for r in mr]) * 100),
                        ("その中で飛んだ割合 ×10", np.array([r[0] for r in mr]), np.array([r[2] for r in mr]) * 1000)],
                       xlabel="採点の差(margin)の下限", ylabel="%", title="次数が際どい画素を捨てる(実データ)",
                       kinds=["line", "line"], colors=["neutral", "wrong"],
                       caption="最良と次点の仮説の採点の差(margin)が小さい画素を捨てると、残った画素の飛びが減る。"
                               "データ: Lawin, Forssén, Ovrén (ECCV 2016)、Zenodo 10.5281/zenodo.19608956、CC BY 4.0。")
    # GIF: 点群を回す
    frames = []
    nfr = 14
    for k in range(nfr):
        yaw = 30.0 + 90.0 * k / (nfr - 1)
        a = studio.render_points_frame(Q, cols, yaw=yaw, pitch=15.0, zoom=1.3, size=300, point_px=2, center=center,
                                       radius=0.6)
        b = studio.render_points_frame(Q[~mq], cz[~mq], yaw=yaw, pitch=15.0, zoom=1.3, size=300, point_px=2,
                                       center=center, radius=0.6)
        fig = fs.annotate_figure_grid([a, b], ncols=2, letters=False,
                                      captions=["iToF の点群(赤 = 宙に浮いた点)", "印を除いた点群"],
                                      title="フライングピクセル(卓上の箱、3 周波)")
        frames.append(np.asarray(fig))
    frames = frames + frames[::-1]
    figs.save_gif("flying_pixels_orbit", frames, fps=8.0,
                  caption="左の箱の点群を回して見る。横から見ると、縁から背後の床へ視線に沿って伸びる赤い点の列(フライングピクセル)が"
                          "現れる。右は印を除いたもの。")


def main():
    t0 = time.time()
    print("PoC 間接 ToF(予算 %s)" % ("reduced" if REDUCED else "full"))
    cf = chapter_closed_form()
    noise = chapter_noise()
    uw = chapter_unwrap()
    mp = chapter_multipath()
    fl = chapter_flying()
    wg = chapter_wiggling()
    amb = chapter_ambient(uw)
    dt = chapter_dtof(fl)
    real = chapter_real_data()
    if not REDUCED and figs.target_dir() is not None:
        make_figures(cf, noise, uw, mp, fl, wg, amb, dt, real)
    print("\n所要 %.1f s、門 %d 件中 NG %d 件" % (time.time() - t0, len(GATES), len(FAILS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
