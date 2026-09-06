# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""偏光で鏡面反射を剥がす —— フレネルの式で真値を作り、分離結果を突き合わせる。

EXTEND: 実際の偏光カメラ(Sony IMX250MZR = 画素上に 0/45/90/135 度の
ワイヤグリッドを敷いた division-of-focal-plane センサ)の生データに差し替えるなら、
本 PoC の ``render_sweep`` だけを実データ読み込みに置き換える。留意点は 4 つ。
(1) **デモザイクの前に生 Bayer 相当の 2x2 偏光モザイクを分離する** —— 4 枚は
互いに半画素ずれた別々の視点なので、補間せずに 1/2 解像度で扱うのが最も正直。
補間すると縁で偏光度が跳ね、それが「鏡面」として分離結果に漏れる。
(2) **リニアな輻度に戻す** —— 本族の op は全部リニア RGB / リニア輻度が前提で、
sRGB ガンマのまま渡しても例外は出ず、分離が静かに劣化するだけ。
(3) **消光比と画素ごとの角度誤差を較正する** —— IMX250MZR の消光比は可視域で
おおむね 200:1〜400:1 程度、素子ごとの主軸ずれも 1 度前後ある。本 PoC の 7-(b)
節が示すとおり、**全画素共通の角度オフセットは分離を壊さない**(方位だけ狂う)が、
**1 枚だけずれると壊れる**。較正すべきなのは絶対角ではなく相対角。
(4) **暗電流・黒レベルを引く** —— オフセットが残ると ``I_min`` が持ち上がり、
拡散成分が一律に過大評価される(これは雑音と違って平均しても消えない)。

この PoC が示すこと:

1. **真値は自分で作る** —— 拡散(無偏光)と鏡面(部分偏光)を s/p 成分に分けて
   自分で合成し、フレネルの式から偏光度を出す。分離結果はその真値と突き合わせる。
2. **ゼロ点を置く** —— 「分離しない」「フレームの最小値を拡散とみなす」を並べ、
   偏光を使う手が何倍勝つのかを数字で出す。**20 度では 1.2 倍しか勝たない。**
3. **ブリュースター角が最良、は本当か** —— 20/40/56.31/70 度で測ると、拡散成分の
   誤差は閉形式 ``R_p * E`` に厳密一致し、ブリュースター角で 0 になる。
4. **壊れる条件を数字で** —— 雑音・偏光子角度の較正誤差・白飛びの 3 つ。

★ この PoC が出した道具の穴は末尾の「所見」節に 5 件まとめた。要点は
``polarization_separate`` の返す "diffuse" が **``R_p * E`` だけ系統的に大きい**
こと、そしてその補正に必要な入射角の口が op に無いこと。
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import match3d                                                   # noqa: E402
import specularity                                               # noqa: E402

ETA = 1.5                       # 誘電体(ガラス / 樹脂)の屈折率
THETA_B = math.degrees(math.atan(ETA))          # ブリュースター角 = 56.3099 度
ANGLES = (0.0, 45.0, 90.0, 135.0)               # DoFP センサの 4 方位
H, W = 96, 128
E0 = 3.0                        # 鏡面ローブに入る光源の照度(拡散の数倍が普通)
AZIMUTH = 22.5                  # 入射面の方位。4 方位の格子から最も遠い最悪値
THETAS = (20.0, 40.0, THETA_B, 70.0)


# --------------------------------------------------------------------------- #
# 1. 真値の生成 —— 拡散・鏡面・フレネル                                          #
# --------------------------------------------------------------------------- #
def scene(h=H, w=W):
    """拡散輻度 (H,W) と鏡面ローブ (H,W) を作る。乱数は使わない。

    拡散側は同心円の縞・斜めの傾き・暗いパッチを重ねた **構造を持つ** 場にする。
    一様な板だと「どの画素でも同じ答え」になり、画素ごとに壊れる不具合が
    平均に隠れる(乱数でも同じ理由で隠れる)。
    """
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    r = np.hypot(yy - cy, xx - cx) / max(h, w)
    diffuse = 0.30 + 0.16 * np.cos(14.0 * r) + 0.10 * (xx / (w - 1))
    diffuse[10:26, 12:34] = 0.02                    # 暗いパッチ(雑音が最初に壊す所)
    diffuse[60:80, 90:120] = 0.55                   # 明るいパッチ
    diffuse = np.clip(diffuse, 0.02, 0.60)
    # 鏡面ローブ = 光源の像。中心を外し、拡散の縞とも暗パッチとも重ねる。
    gy, gx = 0.42 * (h - 1), 0.58 * (w - 1)
    lobe = np.exp(-(((yy - gy) / (0.16 * h)) ** 2 + ((xx - gx) / (0.16 * w)) ** 2))
    return diffuse, lobe


def fresnel_sp(theta_deg, eta=ETA):
    """入射角(度)→ (R_s, R_p)。空気 → 屈折率 eta の誘電体、強度反射率。

    r_s = (n1 cos_i - n2 cos_t)/(n1 cos_i + n2 cos_t)
    r_p = (n1 cos_t - n2 cos_i)/(n1 cos_t + n2 cos_i)
    ブリュースター角 tan(theta_B) = n2/n1 で r_p = 0 —— **p 偏光が消える**ので
    反射光は s 偏光だけになる = 偏光度 1。これが「偏光で鏡面が剥がせる」の全て。
    """
    ci = math.cos(math.radians(theta_deg))
    st = math.sin(math.radians(theta_deg)) / eta
    ct = math.sqrt(max(0.0, 1.0 - st * st))
    rs = (ci - eta * ct) / (ci + eta * ct)
    rp = (ct - eta * ci) / (ct + eta * ci)
    return rs * rs, rp * rp


def specular_components(lobe, theta_deg, irradiance=E0):
    """鏡面反射の s 成分・p 成分の輻度 (H,W) を返す。

    無偏光の光源(照度 E)は s と p に E/2 ずつ配分される。反射すると各々
    ``R_s * E/2`` と ``R_p * E/2`` になる。合計 = 鏡面の全輻度、差 = 偏光した分。
    """
    rs, rp = fresnel_sp(theta_deg)
    return 0.5 * rs * irradiance * lobe, 0.5 * rp * irradiance * lobe


def render_sweep(diffuse, spec_s, spec_p, angles=ANGLES, azimuth=AZIMUTH):
    """偏光子掃引 (N,H,W) を合成する。検光子角 t は s 軸から測る。

    ``I(t) = 0.5*D + I_s cos^2(t - az) + I_p sin^2(t - az)``
    拡散は完全無偏光なのでどの角度でも半分通る。鏡面は s/p が独立にマリュスの
    法則に従う。``specularity.polarization_render`` は鏡面を **完全偏光** として
    しか描けないので(下の 2 節で示すとおり等価な組み替えは可能)、部分偏光の
    前方モデルはここで自分で書く。
    """
    t = np.radians(np.asarray(angles, float) - azimuth)[:, None, None]
    return 0.5 * diffuse[None] + spec_s[None] * np.cos(t) ** 2 \
        + spec_p[None] * np.sin(t) ** 2


def rmse(a, b):
    return float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2)))


def separate(frames, angles=ANGLES, mvf=0.0):
    return specularity.polarization_separate(frames, angles, max_violation_frac=mvf)


# --------------------------------------------------------------------------- #
# ゼロ点(null)                                                                #
# --------------------------------------------------------------------------- #
def null_no_separation(frames):
    """何もしない —— 撮れた輻度をそのまま拡散だとみなす。

    等間隔 4 方位の平均は当てはめの a0 に厳密一致するので、全輻度 = 2*平均。
    """
    return 2.0 * frames.mean(axis=0)


def null_frame_min(frames):
    """素朴 —— 4 枚の画素ごと最小値を拡散とみなす(残りが鏡面)。"""
    return frames.min(axis=0)


def null_frame_min2(frames):
    """素朴 + 尺度だけ直した版 —— 2 x (4 枚の最小値)。

    op と同じ ``2 * I_min`` の式だが、``I_min`` を **正弦波当てはめでなく
    離散の最小値**で取る。方位が 4 方位の格子に乗っていれば op と一致し、
    外れていると必ず過大評価になる。ゼロ点として一番手強い。
    """
    return 2.0 * frames.min(axis=0)


def main():
    t_all = time.perf_counter()
    diffuse, lobe = scene()

    # ---------------------------------------------------------------- #
    print("=== 1. フレネル —— 入射角と鏡面の偏光度 ===")
    print(f"  屈折率 {ETA} / ブリュースター角 tan^-1({ETA}) = {THETA_B:.4f} 度")
    print(f"  {'入射角':>8}{'R_s':>10}{'R_p':>12}{'(R_s+R_p)/2':>14}"
          f"{'鏡面の偏光度':>14}{'match3d 差':>12}")
    for th in (0.0, 20.0, 40.0, THETA_B, 70.0, 85.0):
        rs, rp = fresnel_sp(th)
        dop = (rs - rp) / (rs + rp) if (rs + rp) > 0 else 0.0
        ref = match3d.fresnel_reflectance(math.cos(math.radians(th)), 1.0, ETA)
        print(f"  {th:>8.2f}{rs:>10.5f}{rp:>12.3e}{0.5 * (rs + rp):>14.5f}"
              f"{dop:>14.6f}{abs(0.5 * (rs + rp) - ref):>12.2e}")
    print("  → ブリュースター角で R_p が 0(1e-33 は倍精度の丸め)= 偏光度 1。")
    print("     垂直入射(0 度)は偏光度 0 —— 偏光板を回しても鏡面は動かない。")
    print("     最右列は match3d.fresnel_reflectance との差。同じ式を見ている。")

    # ---------------------------------------------------------------- #
    print("\n=== 2. 前方モデル —— op の完全偏光モデルとの等価な組み替え ===")
    s_s, s_p = specular_components(lobe, THETA_B)
    frames = render_sweep(diffuse, s_s, s_p)
    # I(t) = 0.5*(D + 2*I_p) + (I_s - I_p) cos^2(t-az)  という恒等式。
    eff_d, eff_s = diffuse + 2.0 * s_p, s_s - s_p
    ref = specularity.polarization_render(eff_d, eff_s, ANGLES, azimuth_deg=AZIMUTH)
    print(f"  自作の部分偏光レンダ vs polarization_render(等価な split)"
          f"の最大差 {np.abs(frames - ref).max():.3e}")
    print("  → 部分偏光の鏡面は「無偏光 2*I_p + 完全偏光 (I_s - I_p)」に厳密に")
    print("     分解できる。**op が拡散として返すのは D ではなく D + 2*I_p** で、")
    print("     これが以下すべての誤差の正体(モデルの外挿ではなく恒等式)。")
    for th in (20.0, 70.0):
        a, b = specular_components(lobe, th)
        f2 = render_sweep(diffuse, a, b)
        r2 = specularity.polarization_render(diffuse + 2 * b, a - b, ANGLES,
                                             azimuth_deg=AZIMUTH)
        print(f"     入射角 {th:>5.1f} 度でも最大差 {np.abs(f2 - r2).max():.3e}")

    # ---------------------------------------------------------------- #
    print("\n=== 3. ブリュースター角での分離 —— ゼロ点と並べる ===")
    d_true = diffuse
    s_true = s_s + s_p
    d_op, s_op = separate(frames)
    rho = 1.0                                       # ブリュースター角の鏡面偏光度
    print(f"  真値: 拡散 平均 {d_true.mean():.4f} / 鏡面 最大 {s_true.max():.4f}"
          f"(ローブ中心)")
    print(f"  {'手法':<34}{'拡散 RMSE':>12}{'鏡面 RMSE':>12}{'op 比':>9}")
    base = rmse(d_op, d_true)
    rows = [
        ("ゼロ点 1: 分離しない(全輻度)", null_no_separation(frames), None),
        ("ゼロ点 2: 4 枚の最小値", null_frame_min(frames), None),
        ("ゼロ点 3: 2 x 4 枚の最小値", null_frame_min2(frames), None),
        ("polarization_separate", d_op, s_op),
    ]
    for name, d_est, s_est in rows:
        e = rmse(d_est, d_true)
        es = rmse(s_est, s_true) if s_est is not None else float("nan")
        rs_txt = f"{es:>12.3e}" if s_est is not None else f"{'—':>12}"
        print(f"  {name:<34}{e:>12.3e}{rs_txt}{e / base:>11.3g}")
    print("  → ブリュースター角では op の誤差が 1e-17 台 = 倍精度の床。R_p = 0 な")
    print("     ので「2*I_min = D」が恒等式として成り立ち、ゼロ点との比は 14〜15 桁。")
    print("     この「比が意味を失うほど勝つ」のはブリュースター角限定で、4 節で")
    print("     角度を振ると 1.2 倍まで落ちる。**一点で測って一般化してはいけない。**")

    # ---------------------------------------------------------------- #
    print("\n=== 4. 入射角を振る —— 誤差は R_p * E に一致するか ===")
    print(f"  {'入射角':>8}{'鏡面偏光度':>12}{'op 拡散RMSE':>14}{'閉形式 R_p*E':>14}"
          f"{'差':>10}{'ゼロ点1':>12}{'ゼロ点1/op':>12}")
    ang_rows = {}
    g_rms = float(np.sqrt(np.mean(lobe ** 2)))
    for th in THETAS:
        a, b = specular_components(lobe, th)
        f = render_sweep(diffuse, a, b)
        d_e, s_e = separate(f)
        rs, rp = fresnel_sp(th)
        dop = (rs - rp) / (rs + rp)
        e = rmse(d_e, diffuse)
        pred = rp * E0 * g_rms                      # 2*I_p = R_p * E * lobe
        e0n = rmse(null_no_separation(f), diffuse)
        ratio = e0n / e if e > 0 else float("inf")
        ang_rows[th] = (dop, e, pred, e0n, ratio)
        rt = f"{ratio:>12.2f}" if np.isfinite(ratio) else f"{'∞':>12}"
        print(f"  {th:>8.2f}{dop:>12.6f}{e:>14.3e}{pred:>14.3e}"
              f"{abs(e - pred):>10.1e}{e0n:>12.3e}{rt}")
    print("  → 誤差は閉形式 R_p * E に厳密一致(差は 1e-17 台)。理論どおり")
    print("     ブリュースター角で最良、そこから離れるほど悪い。ただし **20 度では")
    print("     ゼロ点の 1.2 倍しか勝たない** —— 偏光板を付ける価値が無い角度がある。")
    print("     70 度は 20 度より良いが、40 度と大差ない(R_p が谷から立ち上がる)。")

    # ---------------------------------------------------------------- #
    print("\n=== 5. 入射角が既知なら偏りは閉形式で消せる ===")
    print(f"  {'入射角':>8}{'op RMSE':>12}{'補正後 RMSE':>14}{'雑音増幅 1/ρ':>14}")
    corr_rows = {}
    for th in THETAS:
        a, b = specular_components(lobe, th)
        f = render_sweep(diffuse, a, b)
        d_e, s_e = separate(f)
        rs, rp = fresnel_sp(th)
        r = (rs - rp) / (rs + rp)
        s_c = s_e / r                               # 真の鏡面 = 偏光分 / 偏光度
        d_c = (d_e + s_e) - s_c                     # 全輻度は保存されている
        corr_rows[th] = (rmse(d_e, diffuse), rmse(d_c, diffuse), 1.0 / r)
        print(f"  {th:>8.2f}{corr_rows[th][0]:>12.3e}{corr_rows[th][1]:>14.3e}"
              f"{1.0 / r:>14.2f}")
    print("  → I_s + I_p = (I_s - I_p)/ρ、ρ = (R_s-R_p)/(R_s+R_p) = 鏡面の偏光度。")
    print("     入射角さえ分かれば偏りは完全に消える(1e-17 台)。代償は 1/ρ 倍の")
    print("     雑音増幅で、20 度では 5.9 倍。**op にはこの ρ を渡す口が無い**(所見 a)。")

    # ---------------------------------------------------------------- #
    print("\n=== 6. 方位が 4 方位の格子に乗るかどうか ===")
    print(f"  {'入射面方位':>10}{'op RMSE':>12}{'ゼロ点3 RMSE':>14}{'ゼロ点3/op':>12}")
    az_rows = {}
    for az in (0.0, 10.0, 22.5, 45.0):
        a, b = specular_components(lobe, 70.0)
        f = render_sweep(diffuse, a, b, azimuth=az)
        e = rmse(separate(f)[0], diffuse)
        e3 = rmse(null_frame_min2(f), diffuse)
        az_rows[az] = (e, e3)
        print(f"  {az:>10.1f}{e:>12.3e}{e3:>14.3e}{e3 / e:>12.2f}")
    print("  → 方位が 0 度 / 45 度(= 測った角度そのもの)では離散最小値が真の")
    print("     I_min に一致し、素朴なゼロ点 3 が op に **引き分ける**。22.5 度で")
    print("     4.6 倍差。正弦波当てはめが効くのは格子から外れたときだけで、")
    print("     「当てはめだから常に良い」ではない。実機の方位は未知なので")
    print("     最悪値で設計すべき、というのがこの表の使い道。")

    # ---------------------------------------------------------------- #
    print("\n=== 7. 偏光度と Stokes —— 別の op も同じ真値に合うか ===")
    a70, b70 = specular_components(lobe, 70.0)
    f70 = render_sweep(diffuse, a70, b70)
    dolp = specularity.polarization_dolp_map(f70, ANGLES)
    dolp_true = (a70 - b70) / (diffuse + a70 + b70)
    print(f"  polarization_dolp_map と閉形式 (I_s-I_p)/(D+I_s+I_p) の最大差 "
          f"{np.abs(dolp - dolp_true).max():.3e}")
    print(f"  画素ごとの偏光度: 最大 {dolp.max():.4f}(ローブ中心)/ "
          f"ローブ外 {dolp[0, 0]:.3e}")
    st = specularity.polarization_stokes(f70, ANGLES)
    s0_true = float((diffuse + a70 + b70).mean())
    print(f"  polarization_stokes S0 {st[0]:.6f} / 閉形式の全輻度平均 "
          f"{s0_true:.6f}(差 {abs(st[0] - s0_true):.2e})")
    print(f"  S3 = {st[3]:.1f} —— 直線検光子だけでは円偏光は見えない(仕様どおり)。")
    print("  → 場面全体の偏光度は "
          f"{math.hypot(st[1], st[2]) / st[0]:.4f} で、画素最大 "
          f"{dolp.max():.4f} よりずっと小さい。**空間平均は鏡面を薄める** ——")
    print("     ここを取り違えると「偏光が使えない場面」と誤判定する。")

    # ---------------------------------------------------------------- #
    print("\n=== 8-(a) 壊れる条件: 雑音 ===")
    print(f"  {'雑音σ':>10}{'既定(fail-closed)':>20}{'違反画素率':>12}"
          f"{'RMSE(強制)':>14}{'雑音なし比':>12}")
    base70 = rmse(separate(f70)[0], diffuse)
    noise_rows = {}
    rng = np.random.default_rng(20260906)
    for sigma in (0.0, 1e-4, 1e-3, 3e-3, 1e-2, 3e-2, 1e-1):
        fn = f70 + sigma * rng.standard_normal(f70.shape)
        fn = np.maximum(fn, 0.0)                    # センサは負を返さない
        try:
            separate(fn)
            verdict = "通る"
        except ValueError:
            verdict = "拒否"
        d_f, _ = separate(fn, mvf=1.0)              # 強制的に通した場合
        # 違反画素率 = 当てはめた最小輻度が負になった画素
        a0 = fn.mean(axis=0)
        c = np.cos(np.radians(2 * np.asarray(ANGLES)))
        s = np.sin(np.radians(2 * np.asarray(ANGLES)))
        a1 = 2 * (fn * c[:, None, None]).mean(axis=0)
        a2 = 2 * (fn * s[:, None, None]).mean(axis=0)
        frac = float((a0 - np.hypot(a1, a2) < 0).mean())
        e = rmse(d_f, diffuse)
        noise_rows[sigma] = (verdict, frac, e)
        print(f"  {sigma:>10.0e}{verdict:>18}{frac:>12.4f}{e:>14.3e}"
              f"{e / base70:>12.2f}")
    print("  → 既定は fail-closed。σ = 1e-3 で最初の画素が負の最小輻度を吐き、")
    print("     **拒否に転じる境界は σ ≈ 1e-3**(拡散 0.02 の暗パッチが最初に落ちる)。")
    print("     強制通過させると RMSE は σ に比例して増え、σ = 1e-2 で雑音なしの")
    print("     6 倍、σ = 3e-2 で 17 倍。拒否は「使えない」ではなく「その画素の")
    print("     偏光信号が雑音に埋もれた」という正しい報告。")

    # ---------------------------------------------------------------- #
    print("\n=== 8-(b) 壊れる条件: 偏光子角度の較正誤差 ===")
    print(f"  {'誤差δ[度]':>10}{'全体オフセット':>16}{'1 枚だけずれ':>16}"
          f"{'1 枚ずれ/雑音なし':>18}")
    cal_rows = {}
    for delta in (0.0, 0.1, 0.5, 1.0, 2.0, 5.0):
        f_all = render_sweep(diffuse, a70, b70,
                             angles=tuple(x + delta for x in ANGLES))
        e_all = rmse(separate(f_all)[0], diffuse)   # 公称角で解く
        f_one = render_sweep(diffuse, a70, b70,
                             angles=(0.0, 45.0 + delta, 90.0, 135.0))
        e_one = rmse(separate(f_one, mvf=1.0)[0], diffuse)
        cal_rows[delta] = (e_all, e_one)
        print(f"  {delta:>10.1f}{e_all:>16.3e}{e_one:>16.3e}"
              f"{e_one / base70:>18.2f}")
    print("  → **全画素共通のオフセットは分離を一切壊さない**(1e-16 台のまま)。")
    print("     基底が丸ごと回るだけで振幅と平均が変わらないから。狂うのは方位")
    print("     (AoLP)だけ。一方 **1 枚だけ 1 度ずれると誤差は 2 桁跳ねる**。")
    print("     較正すべきは絶対角ではなく相対角、というのがこの 2 列の差。")

    # ---------------------------------------------------------------- #
    print("\n=== 8-(c) 壊れる条件: 鏡面の白飛び ===")
    print(f"  {'露光倍率':>10}{'飽和画素率':>12}{'拡散RMSE(規格化)':>20}"
          f"{'飽和なし比':>12}")
    sat_rows = {}
    for gain in (1.0, 1.5, 2.0, 3.0, 5.0):
        fg = np.minimum(f70 * gain, 1.0)
        frac = float((f70 * gain > 1.0).mean())
        d_g, _ = separate(fg, mvf=1.0)
        e = rmse(d_g / gain, diffuse)               # 倍率で割って比較可能にする
        sat_rows[gain] = (frac, e)
        print(f"  {gain:>10.1f}{frac:>12.4f}{e:>20.3e}{e / base70:>12.2f}")
    print("  → 白飛びは **例外を出さない**。I_max が頭打ちになると振幅が縮み、")
    print("     I_min が持ち上がり、拡散が過大評価される方向へ静かに倒れる。")
    print("     飽和 0.6% で誤差 2.4 倍、4.4% で 8.7 倍。fail-closed 検査は")
    print("     「最小輻度が負」しか見ておらず、上端の飽和は素通りする(所見 c)。")

    # ---------------------------------------------------------------- #
    print("\n=== 9. 速度(この機械での実測)===")
    big_d, big_l = scene(1024, 1024)
    ba, bb = specular_components(big_l, 70.0)
    big = render_sweep(big_d, ba, bb)
    for label, fn in (("polarization_separate", lambda: separate(big)),
                      ("polarization_dolp_map",
                       lambda: specularity.polarization_dolp_map(big, ANGLES)),
                      ("polarization_stokes",
                       lambda: specularity.polarization_stokes(big, ANGLES)),
                      ("ゼロ点 3(最小値)", lambda: null_frame_min2(big))):
        t0 = time.perf_counter()
        fn()
        print(f"  {label:<26}{1e3 * (time.perf_counter() - t0):>9.1f} ms  "
              f"(4 x 1024 x 1024)")
    print("  → 分離は最小二乗 1 回だけなので素朴なゼロ点と同じ桁。偏光板を")
    print("     付けない理由に計算コストは使えない。")

    # ---------------------------------------------------------------- #
    print("\n所見(想定と違ったこと):")
    print("   (1) 「ブリュースター角付近が最良」は正しかったが、**理由が予想と")
    print("       違った**。最初は「鏡面が強く偏光するから分離しやすい」と書こうと")
    print("       したが、誤差の閉形式は R_p * E であって R_s には依らない。")
    print("       効いているのは「s が強い」ではなく「**p が消える**」の方。")
    print("   (2) 70 度(偏光度 0.75)は 40 度(0.69)とほぼ同じ質で、20 度だけが")
    print("       極端に悪い。偏光度は 20→40 度で 0.17→0.69 と跳ねる。")
    print("       **設計上の閾は「ブリュースター角」ではなく「30 度より浅くない」**。")
    print("   (3) 素朴な 2 x 最小値が方位 0/45 度では op に引き分けた(6 節)。")
    print("       ゼロ点を 3 種類置かなければ「当てはめが常に勝つ」と書いていた。")

    print("\n所見(fullseye の穴 —— この PoC が出した道具の穴):")
    print("   (a) `polarization_separate` の返す \"diffuse\" は真の拡散より")
    print("       **常に R_p * E だけ大きい**(2 節の恒等式、4 節の実測)。docstring は")
    print("       「垂直入射で false」とだけ書くが、**偏りが閉形式で書ける**ことも、")
    print("       ρ = (R_s-R_p)/(R_s+R_p) を渡せば完全に消せることも書いていない。")
    print("       `specular_dop=` のような引数が 1 つあれば 5 節の補正が op 内で済む。")
    print("   (b) **AoLP(偏光の方位角)を返す op が無い。** `_polar_fit` は a1,a2 を")
    print("       計算しているので 0.5*atan2(a2,a1) を返すだけだが、外へ出る口は")
    print("       `polarization_stokes` の **場面全体 1 本**しかない。方位は入射面の")
    print("       向き = 面法線の方位そのもので、形状復元の主役なのに画素ごとに")
    print("       取れない(`polar_cam.py` は自前で計算していて op を使っていない)。")
    print("   (c) fail-closed 検査は下端(最小輻度が負)だけを見ており、**上端の")
    print("       飽和は素通りする**(8-c)。飽和は例外なしで拡散を過大評価する側へ")
    print("       倒れるので、雑音より質が悪い。`I >= 1.0` の画素率を返すか、")
    print("       `max_saturated_frac` があると同じ規律で守れる。")
    print("   (d) **画素ごとの Stokes 地図が無い。** `polarization_stokes` は空間平均")
    print("       (4,) だけで、7 節のとおり場面平均の偏光度 "
          f"{math.hypot(st[1], st[2]) / st[0]:.3f} は画素最大 {dolp.max():.3f} の")
    print("       1/6 以下。平均値で「偏光は使えない」と判断すると取り逃す。")
    print("   (e) 部分偏光の鏡面を **前方合成する op が無い**。")
    print("       `polarization_render` は鏡面完全偏光だけで、フレネルから")
    print("       (R_s, R_p) を作って掃引にする経路は本 PoC が手で書いた。")
    print("       `match3d.fresnel_reflectance` は s/p 平均しか返さないので、")
    print("       s と p を別々に返す口(または `polarization_render_fresnel`)が")
    print("       あれば、この PoC 全体が op の合成で書ける。")

    # ---- 自己検査(速さは assert しない)---------------------------------- #
    # 1. フレネル: ブリュースター角で R_p = 0、match3d と同じ式
    rs_b, rp_b = fresnel_sp(THETA_B)
    assert rp_b < 1e-30, f"ブリュースター角で R_p が 0 でない: {rp_b}"
    for th in (0.0, 20.0, 40.0, 70.0, 85.0):
        rs, rp = fresnel_sp(th)
        assert abs(0.5 * (rs + rp)
                   - match3d.fresnel_reflectance(math.cos(math.radians(th)),
                                                 1.0, ETA)) < 1e-12
    assert abs(fresnel_sp(0.0)[0] - fresnel_sp(0.0)[1]) < 1e-15, \
        "垂直入射で s と p が違う"

    # 2. 前方モデル: 部分偏光レンダ == op の完全偏光レンダ(等価な split)
    assert np.abs(frames - ref).max() < 1e-15, "前方モデルの組み替えが一致しない"

    # 3. ブリュースター角では分離が厳密(倍精度の床)
    assert rmse(d_op, d_true) < 1e-14, \
        f"ブリュースター角で拡散が厳密に出ない: {rmse(d_op, d_true):.3e}"
    assert rmse(s_op, s_true) < 1e-14, "ブリュースター角で鏡面が厳密に出ない"
    # 全輻度は分離で保存される(何も失わず何も作らない)
    assert np.abs((d_op + s_op) - (d_true + s_true)).max() < 1e-14

    # 4. 誤差は閉形式 R_p * E に一致し、ゼロ点に勝つ
    for th, (dop, e, pred, e0n, ratio) in ang_rows.items():
        assert abs(e - pred) < 1e-12 + 1e-6 * pred, \
            f"入射角 {th}: 誤差 {e:.3e} が閉形式 {pred:.3e} と違う"
        assert ratio > 1.0, f"入射角 {th}: ゼロ点 1 に勝てていない (比 {ratio:.2f})"
    assert ang_rows[THETA_B][1] < ang_rows[20.0][1], "ブリュースター角が最良でない"
    assert ang_rows[THETA_B][1] < ang_rows[70.0][1], "ブリュースター角が最良でない"
    assert ang_rows[20.0][4] < 1.5, "20 度でゼロ点との差が小さいという所見が崩れた"

    # 5. 入射角が既知なら偏りは消える
    for th, (e_raw, e_corr, amp) in corr_rows.items():
        assert e_corr <= e_raw + 1e-15, f"入射角 {th}: 補正で悪化した"
        assert e_corr < 1e-14, f"入射角 {th}: 補正後も偏りが残る ({e_corr:.3e})"

    # 6. 方位が格子に乗ると素朴なゼロ点が並ぶ / 外れると当てはめが効く
    assert az_rows[0.0][1] / az_rows[0.0][0] < 10.0, \
        "方位 0 度で素朴法が引き分ける、という所見が崩れた"
    assert az_rows[22.5][1] / az_rows[22.5][0] > 2.0, \
        "方位 22.5 度で当てはめが効く、という所見が崩れた"

    # 7. 偏光度と Stokes が閉形式に一致
    assert np.abs(dolp - dolp_true).max() < 1e-12, "偏光度が閉形式と違う"
    assert abs(st[0] - s0_true) < 1e-12, "Stokes S0 が全輻度平均と違う"
    assert st[3] == 0.0, "直線検光子だけで S3 が出ている"

    # 8-(a) 雑音: 既定は fail-closed、σ が上がれば誤差も上がる(単調)
    assert noise_rows[0.0][0] == "通る", "雑音なしで拒否された"
    assert noise_rows[1e-1][0] == "拒否", "σ=0.1 でも拒否されない(fail-closed 破れ)"
    errs = [noise_rows[s][2] for s in (1e-3, 3e-3, 1e-2, 3e-2, 1e-1)]
    assert all(b > a for a, b in zip(errs, errs[1:])), "雑音で誤差が単調に増えない"

    # 8-(b) 全体オフセットは無害 / 1 枚ずれは有害
    assert cal_rows[5.0][0] < 1e-14, \
        f"全体オフセットで分離が壊れた: {cal_rows[5.0][0]:.3e}"
    assert cal_rows[1.0][1] > 30.0 * max(base70, 1e-16), \
        "1 枚だけの角度誤差が無害になっている(想定外)"

    # 8-(c) 飽和は例外なしで静かに悪化する
    assert sat_rows[1.0][0] == 0.0, "露光 1 倍で既に飽和している"
    assert sat_rows[5.0][0] > 0.01, "露光 5 倍でも飽和しない(シーンが暗すぎる)"
    assert sat_rows[5.0][1] > 5.0 * sat_rows[1.0][1], "飽和で悪化していない"

    # 9. ゼロ点の妥当性(そもそもゼロ点が真値そのものになっていないこと)
    assert rmse(null_no_separation(frames), d_true) > 1e-3
    assert rmse(null_frame_min(frames), d_true) > 1e-2

    print(f"\n総所要 {time.perf_counter() - t_all:.1f} 秒")
    print("PASS")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
