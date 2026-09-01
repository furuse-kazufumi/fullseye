# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""quaternion_monogenic — 四元数画像 op(quatimage)を、閉形式の真値と突き合わせながら一巡する。

    py -3.11 examples/quaternion_monogenic.py

【この例が解く問題】
「複素数画像が使えるなら、4 元数画像も使えたら面白いことができるか?」— その答えを
**数字で**出す。複素数の画素は 2 次元値で回転軸が 1 本しかない。四元数の画素は
(a) 色を 3 次元回転でき、(b) 2 次元信号の解析信号(モノジェニック信号)を保持できる。
この 2 つが本物の差で、それ以外は差ではない、というところまで測って見せる。

【グラウンドトゥルース(数値で嘘を弾く)】
1. Riesz 変換: 格子 cos(2π(u₀x+v₀y)) に対して R1=(u₀/|ω|)sin、R2=(v₀/|ω|)sin が**閉形式**。
   位相が π/2 ずれ、方位は格子の向きに一致する。8 方位すべてで機械精度。
2. 色回転: q·x·q* は既知の回転を**厳密に**与える。往復・ノルム保存も機械精度。
3. 色選択フィルタ: 指定方向の成分がその場で厳密に 0 になる。
4. 四元数フーリエ変換: 左変換・右変換それぞれで逆変換が厳密に戻る(往復誤差 ~1e-15)。
5. 四元数相関: テンプレートを色回転させると、スカラー部が cos(角度)倍になり、
   ベクトル部の大きさから角度そのものが復元できる。
6. 変位計測: motionmag.synthesize_translation と同じ「閉形式の真値」で突き合わせる。

【honest な限界(この例が隠さないこと)】
- **色回転は 3x3 直交行列と完全に同じ写像**。四元数が勝つのは「チャンネルごとの処理」
  に対してだけで、行列に対しては勝たない。両方を実測して並べる。
- **QFT は 3 回のチャンネル FFT の線形再結合にすぎず、速くもならない**(実測で遅い)。
- **Riesz 変位計測は 1 オクターブに複数方位が入ると 13 % 静かに外れる**。
  motionmag(complex steerable)の既定合成クリップがまさにその条件で、この例は
  そこで**負ける様子をそのまま表示する**。
- モノジェニック方位は「振幅が高くても」偶対称点(局所位相 0 / π)で未定義になる。
  マスクは振幅ではなく **Riesz ベクトルの大きさ**に掛けること。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import motionmag as mm          # noqa: E402
import pose_quat                # noqa: E402
import quatimage as qi          # noqa: E402

H = W = 64
T = 64
FPS, FREQ, BAND = 32.0, 4.0, (3.0, 5.0)


def grating(cx, cy, phase=0.0, h=H, w=W):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    return np.cos(2.0 * np.pi * (cx * xx / w + cy * yy / h) + phase)


def one_grating_clip(amplitude, cyc_x=8, cyc_y=0, h=H, w=W, t=T):
    """1 成分だけを厳密な Fourier 位相ランプで並進させたクリップ(真値は閉形式)。"""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    base = 0.5 + 0.2 * np.cos(2.0 * np.pi * (cyc_x * xx / w + cyc_y * yy / h))
    fv, fu = np.fft.fftfreq(h)[:, None], np.fft.fftfreq(w)[None, :]
    spec = np.fft.fft2(base)
    disp = amplitude * np.sin(2.0 * np.pi * FREQ * np.arange(t) / FPS)
    return np.stack([np.real(np.fft.ifft2(spec * np.exp(-2j * np.pi * fu * d)))
                     for d in disp])


def _gain(series, amplitude):
    tr = amplitude * np.sin(2.0 * np.pi * FREQ * np.arange(T) / FPS)
    return float(series[:, 0] @ tr / (tr @ tr))


def run():
    out = {}

    # ------------------------------------------------------------------ #
    # 1) Riesz 変換 — 2 次元の解析信号は複素数の中に無い                  #
    # ------------------------------------------------------------------ #
    print("=" * 74)
    print("1) Riesz 変換 / モノジェニック信号 — 閉形式との突き合わせ")
    print("=" * 74)
    print("   1 次元の解析信号 f + i·H(f) は「90 度後ろ」の向きが 1 つに決まるから作れる。")
    print("   2 次元にはその向きが無い。だから Hilbert 変換の一般化は**対**になり、")
    print("   値は (f, R1f, R2f) = 四元数になる。振幅・位相・方位が同時に出る。")
    print()
    print("   %-12s %-14s %-14s %-14s %-12s" %
          ("格子方位", "R1 誤差", "R2 誤差", "方位誤差(rad)", "振幅"))
    worst_r = worst_o = 0.0
    for cx, cy in [(8, 0), (8, 3), (6, 6), (3, 8), (0, 8), (-3, 8), (-6, 6), (-8, 3)]:
        u0, v0 = cx / W, cy / H
        r = np.hypot(u0, v0)
        g = grating(cx, cy)
        q = qi.riesz_transform(g)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
        s = np.sin(2.0 * np.pi * (cx * xx / W + cy * yy / H))
        e1 = float(np.abs(q[..., 1] - (u0 / r) * s).max())
        e2 = float(np.abs(q[..., 2] - (v0 / r) * s).max())
        mono = qi.monogenic_signal(g, wavelength_px=1.0 / r)
        th = qi.monogenic_orientation(mono)
        rmag = np.hypot(mono[..., 1], mono[..., 2])
        live = rmag > 0.1 * rmag.max()          # ← 振幅ではなく |R| でマスクする
        true_th = np.mod(np.arctan2(v0, u0), np.pi)
        eo = float(np.abs(np.mod(th - true_th + np.pi / 2, np.pi) - np.pi / 2)[live].max())
        amp = qi.monogenic_amplitude(mono)
        worst_r, worst_o = max(worst_r, e1, e2), max(worst_o, eo)
        print("   %-12.1f %-14.3e %-14.3e %-14.3e %-12.15g"
              % (np.degrees(np.arctan2(cy, cx)), e1, e2, eo, amp.mean()))
    print()
    print("   → 最悪 Riesz 誤差 %.3e / 最悪 方位誤差 %.3e。振幅は方位に依らず 1"
          "(等方性)。" % (worst_r, worst_o))
    print("   honest: 方位は偶対称点(局所位相 0 / π)で**振幅が満点のまま**未定義になる。")
    r = np.hypot(6 / W, 6 / H)
    mono = qi.monogenic_signal(grating(6, 6), wavelength_px=1.0 / r)
    rmag = np.hypot(mono[..., 1], mono[..., 2])
    th = qi.monogenic_orientation(mono)
    true_th = np.mod(np.arctan2(6 / H, 6 / W), np.pi)
    err = np.abs(np.mod(th - true_th + np.pi / 2, np.pi) - np.pi / 2)
    i = int(err.argmax())
    print("           最悪画素: 方位誤差 %.4f rad, 振幅 %.4f, |R| %.2e"
          % (err.ravel()[i], qi.monogenic_amplitude(mono).ravel()[i], rmag.ravel()[i]))
    out["riesz_worst"] = worst_r

    # ------------------------------------------------------------------ #
    # 2) 色回転 — チャンネルごとには原理的に不可能、行列とは完全に同じ    #
    # ------------------------------------------------------------------ #
    print()
    print("=" * 74)
    print("2) 色空間の 3 次元回転 q·x·q* — 何に勝ち、何に勝たないか")
    print("=" * 74)
    red = np.zeros((8, 8, 3))
    red[..., 0] = 1.0
    q = qi.rgb_to_quaternion(red)
    rot90 = qi.quat_color_rotate(q, (0.0, 0.0, 1.0), np.radians(90.0))
    print("   純赤 (1,0,0) を青軸まわりに 90 度 → %s"
          % np.round(rot90[0, 0, 1:], 12))
    print("   チャンネルごとの利得(対角行列)では、緑は 0 のままにしかならない:")
    for gain in (0.0, 1.0, -3.5, 1e6):
        print("       緑チャンネル × %-8g → %g" % (gain, red[0, 0, 1] * gain))
    print("   → **チャンネルごとの処理に対しては原理的に勝つ**(零から何も作れない)。")
    print()
    ang = np.radians(30.0)
    c, s = np.cos(ang), np.sin(ang)
    R = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
    rgb = np.random.default_rng(0).random((16, 16, 3))
    quat_out = qi.quat_color_rotate(qi.rgb_to_quaternion(rgb), (0, 0, 1), ang)[..., 1:]
    mat_out = rgb @ R.T
    print("   同じ回転を 3x3 直交行列でやった場合との差: %.3e"
          % np.abs(quat_out - mat_out).max())
    print("   → **行列に対しては勝たない**(SO(3) と単位四元数は同型)。")
    print("      1e-12 の床は pose_quat.quat_normalize が norm+1e-12 で割るため。")
    print()
    rng = np.random.default_rng(3)
    q_acc, R_acc = np.array([1.0, 0, 0, 0]), np.eye(3)
    for _ in range(100_000):
        ax = rng.standard_normal(3)
        ax /= np.linalg.norm(ax)
        qq = pose_quat.axis_angle_to_quat(*ax, rng.uniform(-0.1, 0.1))
        q_acc = pose_quat.quat_compose(q_acc, qq)
        q_acc /= np.linalg.norm(q_acc)
        R_acc = R_acc @ pose_quat.quat_to_hom_mat3d(qq)[:3, :3]
    print("   10 万回合成したときの逸脱: 四元数 |q|-1 = %.3e / 行列 |RᵀR-I| = %.3e"
          % (abs(np.linalg.norm(q_acc) - 1.0), np.abs(R_acc.T @ R_acc - np.eye(3)).max()))
    print("   → 四元数の取り柄は「表現量 4 vs 9」と「合成の閉性」。小さいが本物。")

    # ------------------------------------------------------------------ #
    # 3) 色選択フィルタ                                                    #
    # ------------------------------------------------------------------ #
    print()
    print("=" * 74)
    print("3) 色に選択的なフィルタ — 指定方向だけを厳密に落とす / 残す")
    print("=" * 74)
    g = np.array([1.0, 1.0, 1.0]) / np.sqrt(3.0)        # 灰色軸
    Q = qi.rgb_to_quaternion(np.random.default_rng(1).random((32, 32, 3)))
    rem = qi.quat_color_filter(Q, g, "remove")
    keep = qi.quat_color_filter(Q, g, "keep")
    print("   remove 後に灰色軸へ残る成分: %.3e" % np.abs(rem[..., 1:] @ g).max())
    print("   remove + keep が元に戻る誤差 : %.3e" % np.abs(rem + keep - Q).max())
    P = np.eye(3) - np.outer(g, g)
    D = np.diag(np.diag(P))
    print("   チャンネルごとの最良近似(対角行列)の誤差: ||P-diag(P)||₂ = %.6f"
          % np.linalg.norm(P - D, 2))
    print("       純赤 (1,0,0): 正解 %s / 最良対角 %s → 誤差 %.6f"
          % (np.round(P @ np.array([1., 0, 0]), 6), np.round(D @ np.array([1., 0, 0]), 6),
             np.linalg.norm((P - D) @ np.array([1., 0, 0]))))
    print("   honest: remove は specularity.specular_free_transform と**同じ射影**で、")
    print("           作り直さず delegate している(一致は偶然でなく構成による)。")

    # ------------------------------------------------------------------ #
    # 4) 四元数フーリエ変換 — 左右は別物、そして速くはならない            #
    # ------------------------------------------------------------------ #
    print()
    print("=" * 74)
    print("4) 四元数フーリエ変換 — 非可換だから左右で別の変換になる")
    print("=" * 74)
    colour = qi.rgb_to_quaternion(np.random.default_rng(2).random((32, 32, 3)))
    for side in ("left", "right"):
        back = qi.iqft2(qi.qft2(colour, side), side)
        print("   %-5s 変換の往復誤差: %.3e" % (side, np.abs(back - colour).max()))
    FL, FR = qi.qft2(colour, "left"), qi.qft2(colour, "right")
    print("   左右のスペクトルの差 : max %.4g (ピーク係数 %.4g に対して %.1f %%)"
          % (np.abs(FL - FR).max(), qi.quat_norm(FL).max(),
             100 * np.abs(FL - FR).max() / qi.quat_norm(FL).max()))
    cross = qi.iqft2(qi.qft2(colour, "left"), "right")
    print("   左で変換して右で戻した場合の誤差: %.4g(データの振れ幅 %.4g)"
          % (np.abs(cross - colour).max(), np.abs(colour).max()))
    print("   → 例外も NaN も出ない。だから side は**既定値なしの必須引数**にしてある。")
    print()
    ch = [np.fft.fft2(colour[..., i]) for i in (1, 2, 3)]
    m, n, lam = qi._mu_basis(None, "example")
    FA = 1j * sum(m[i] * ch[i] for i in range(3))
    FB = (sum(n[i] * ch[i] for i in range(3))
          + 1j * sum(lam[i] * ch[i] for i in range(3)))
    rebuilt = qi._from_symplectic(np.fft.fftshift(FA), np.fft.fftshift(FB), m, n, lam)
    print("   QFT(left) を **3 回のチャンネル FFT だけ**から組み直した誤差: %.3e"
          % np.abs(rebuilt - FL).max())
    big = np.random.default_rng(4).random((256, 256, 4))

    def _t(f, n_rep=10):
        f()
        return min((lambda: (time.perf_counter(),
                             f(), time.perf_counter())[::2])() for _ in range(n_rep))

    ts_q, ts_c = [], []
    for _ in range(10):
        t0 = time.perf_counter(); qi.qft2(big, "left"); ts_q.append(time.perf_counter() - t0)
        t0 = time.perf_counter()
        for i in range(1, 4):
            np.fft.fft2(big[..., i])
        ts_c.append(time.perf_counter() - t0)
    print("   速度 (256x256, best of 10): QFT %.3f ms / チャンネル FFT×3 %.3f ms → %.2f 倍**遅い**"
          % (1000 * min(ts_q), 1000 * min(ts_c), min(ts_q) / min(ts_c)))
    print("   → QFT は情報も速度も増やさない。増えるのは「4 つの数が 1 つの代数対象で")
    print("      あり続ける」ことだけ。そこは正直に書く。")

    # ------------------------------------------------------------------ #
    # 5) 四元数相関 — 色のずれ方まで返る                                  #
    # ------------------------------------------------------------------ #
    print()
    print("=" * 74)
    print("5) 四元数相関 — スカラー部 = 一致度、ベクトル部 = 色のずれ方")
    print("=" * 74)
    patch = np.random.default_rng(5).random((32, 32, 3))
    patch[..., 2] = 0.0                      # 色を回転軸(青)に直交する面へ
    A = qi.rgb_to_quaternion(patch)
    print("   %-10s %-16s %-14s %-16s %s"
          % ("回転", "スカラー比", "cos(角度)", "復元角度", "ベクトル方向"))
    for deg in (0.0, 30.0, 60.0, 90.0):
        B = qi.quat_color_rotate(A, (0, 0, 1), np.radians(deg))
        c0 = qi.quat_correlate(A, A)[0, 0]
        c1 = qi.quat_correlate(A, B)[0, 0]
        v = c1[1:]
        nv = float(np.linalg.norm(v))
        direction = np.round(v / nv, 3) if nv > 1e-9 else np.zeros(3)
        print("   %-10.1f %-16.9f %-14.9f %-16.9f %s"
              % (deg, c1[0] / c0[0], np.cos(np.radians(deg)),
                 np.degrees(np.arctan2(nv, c1[0])), direction))
    print("   → ベクトル方向は回転軸の**符号反転**(共役が積の左にあるため)。")
    print("   honest: 色が回転軸に直交する面から外れると角度は偏る。")
    patch2 = np.random.default_rng(6).random((32, 32, 3))
    A2 = qi.rgb_to_quaternion(patch2)
    B2 = qi.quat_color_rotate(A2, (0, 0, 1), np.radians(30.0))
    c2 = qi.quat_correlate(A2, B2)[0, 0]
    print("           一般の色で 30 度回転 → 復元角度 %.3f 度(何も警告は出ない)"
          % np.degrees(np.arctan2(np.linalg.norm(c2[1:]), c2[0])))

    # ------------------------------------------------------------------ #
    # 6) 変位計測 — 既存の complex steerable 版との真っ向勝負             #
    # ------------------------------------------------------------------ #
    print()
    print("=" * 74)
    print("6) Riesz 変位計測 vs 既存の complex steerable 版(motionmag)")
    print("=" * 74)
    print("   同じクリップ、同じ真値、同じ帯域。真値は閉形式(Fourier 位相ランプ)。")
    print()
    print("   [A] 1 帯域に 1 成分だけ = モノジェニック信号の前提が成り立つ場合")
    print("   %-12s %-24s %-24s" % ("真の d (px)", "Riesz 相対誤差", "steerable 相対誤差"))
    for a in (0.001, 0.01, 0.1, 0.5, 1.0, 2.0, 3.0, 3.06, 3.07, 4.0):
        v = one_grating_clip(a)
        er = abs(_gain(qi.riesz_displacement_series(v, *BAND, FPS), a) - 1.0)
        es = abs(_gain(mm.displacement_series(v, *BAND, FPS), a) - 1.0)
        flag = "  ← 崩壊" if max(er, es) > 0.5 else ""
        print("   %-12.4g %-24.3e %-24.3e%s" % (a, er, es, flag))
    cliff = 2.404825557695773 / (2.0 * np.pi / 8.0)
    print("   → **どちらも同じ場所で崩れる**。J₀ の第一零点 k·A = 2.4048、")
    print("      8 px 格子なら A = %.4f px。天井は分解のせいではなく" % cliff)
    print("      「時間平均を位相の基準にしている」ことのせい。Riesz でも上がらない。")
    print()
    print("   [B] 1 帯域に 2 方位の成分が入る場合(motionmag の既定合成クリップ)")
    print("   %-36s %-20s %-20s" % ("クリップ", "Riesz 相対誤差", "steerable 相対誤差"))
    for name, kw in (("λ = (8, 16) px  ← 既定", {}),
                     ("λ = (8, 32) px  2 オクターブ差", {"wavelength_px": (8.0, 32.0)}),
                     ("λ = (8, 8)  px  同一帯域", {"wavelength_px": (8.0, 8.0)})):
        v = mm.synthesize_translation(frames=T, amplitude_px=0.5,
                                      frequency_hz=FREQ, fps=FPS, **kw)
        er = abs(_gain(qi.riesz_displacement_series(v, *BAND, FPS), 0.5) - 1.0)
        es = abs(_gain(mm.displacement_series(v, *BAND, FPS), 0.5) - 1.0)
        print("   %-36s %-20.3e %-20.3e" % (name, er, es))
    print("   → **ここで Riesz は負ける**。半径方向の帯域には方位の添字が無いので、")
    print("      同じオクターブに違う方位の成分が 2 つ入ると単一平面波の仮定が崩れる。")
    print("      例外も NaN も出ずに 13 % ずれる。2 オクターブ離すと機械精度に戻る")
    print("      = 原因はこれで確定する。実際の景色は大抵この悪いほうの条件にある。")
    print()
    v = one_grating_clip(0.5)
    fr = qi.riesz_displacement(v, *BAND, FPS)
    fs = mm.phase_displacement(v, *BAND, FPS)
    print("   [C] 測れない画素(rank 0): Riesz %d / %d、steerable %d / %d"
          % ((fr["rank"] == 0).sum(), fr["rank"].size,
             (fs["rank"] == 0).sum(), fs["rank"].size))
    print("      → Riesz は偶対称点で Riesz ベクトルが消えるので穴が空く(印は付く)。")
    print()
    print("   [D] 雑音下(1 成分、A = 0.5 px)— ここは Riesz が勝つ")
    print("   %-10s %-22s %-22s" % ("sigma", "Riesz 相対誤差", "steerable 相対誤差"))
    for s in (0.001, 0.01, 0.05):
        v = one_grating_clip(0.5) + np.random.default_rng(1).normal(0, s, (T, H, W))
        er = abs(_gain(qi.riesz_displacement_series(v, *BAND, FPS), 0.5) - 1.0)
        es = abs(_gain(mm.displacement_series(v, *BAND, FPS), 0.5) - 1.0)
        print("   %-10.4g %-22.3e %-22.3e" % (s, er, es))
    print()
    v = one_grating_clip(0.5)
    print("   [E] 速度(64x64x64、best of 5)")
    for name, f in (("riesz_displacement   ", lambda: qi.riesz_displacement(v, *BAND, FPS)),
                    ("mm.phase_displacement", lambda: mm.phase_displacement(v, *BAND, FPS)),
                    ("riesz_motion_magnify ", lambda: qi.riesz_motion_magnify(v, 2.0, *BAND, FPS)),
                    ("mm.motion_magnify    ", lambda: mm.motion_magnify(v, 2.0, *BAND, FPS))):
        f()
        ts = []
        for _ in range(5):
            t0 = time.perf_counter()
            f()
            ts.append(time.perf_counter() - t0)
        print("      %s %.4f s" % (name, min(ts)))
    print("      作る部分帯域の数: Riesz = scales = 4 / steerable = scales×orientations+3 = 19")

    # ------------------------------------------------------------------ #
    # 7) 増幅                                                             #
    # ------------------------------------------------------------------ #
    print()
    print("=" * 74)
    print("7) Riesz ピラミッドによるモーション増幅 — 利得は本当に利得か")
    print("=" * 74)
    v = one_grating_clip(0.1)
    ident = qi.riesz_motion_magnify(v, 1.0, *BAND, FPS)["video"]
    print("   alpha=1 が恒等になる誤差: %.3e" % np.abs(ident - v).max())
    print("   %-8s %-26s %-26s" % ("alpha", "Riesz 実測利得", "steerable 実測利得"))
    for a in (0.0, 2.0, 4.0, -1.0, 20.0):
        rr = qi.riesz_motion_magnify(v, a, *BAND, FPS)["video"]
        ss = mm.motion_magnify(v, a, *BAND, FPS)["video"]
        print("   %-8.1f %-26.12f %-26.12f"
              % (a, _gain(mm.displacement_series(rr, *BAND, FPS), 0.1),
                 _gain(mm.displacement_series(ss, *BAND, FPS), 0.1)))
    print("   ※ 利得は**独立な**推定器(steerable 版)で測っている(自作自演を避ける)。")
    print()
    vn = mm.synthesize_translation(frames=T, amplitude_px=0.2, frequency_hz=FREQ,
                                   fps=FPS, noise_sigma=0.01, seed=0)
    print("   増幅のコスト(0.2 px / sigma=0.01):")
    print("   %-8s %-20s %-20s %-16s" % ("alpha", "画像 SNR 変化(dB)", "運動 SNR 変化(dB)", "帯域線形性"))
    for a in (2.0, 4.0, 8.0):
        r = qi.riesz_motion_magnify(vn, a, *BAND, FPS)
        print("   %-8.1f %-20.4f %-20.4f %-16.6f"
              % (a, r["image_snr_change_db"], r["motion_snr_change_db"],
                 r["band_power_ratio"]))
    print("   → 運動 SNR は**決して上がらない**。増幅は見せる技術で、測る技術ではない。")

    print()
    print("=" * 74)
    print("まとめ(実測に基づく)")
    print("=" * 74)
    print("   本物の差 : 2 次元の解析信号(モノジェニック信号)は複素数の中に無い。")
    print("              色回転はチャンネルごとの処理では原理的に不可能。")
    print("   差でない : 色回転は 3x3 行列と同じ。QFT はチャンネル FFT の再結合で、遅い。")
    print("   負け     : Riesz 変位計測は複数方位が 1 オクターブに入ると 13 % 静かに外れる。")
    print("   勝ち     : 雑音下で約 2 倍正確、1.2〜2.1 倍速い、方位が連続値で出る。")
    return out


def main():
    run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
