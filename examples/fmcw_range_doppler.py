# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""fmcw_range_doppler — コヒーレント測距 op(rangedoppler)を「4D レーダを 1 台
仕立てる」筋で一巡する。

    py -3.11 examples/fmcw_range_doppler.py

【この例が解く問題】
既存の `lidar_scan` / `pseudo_lidar` は幾何(レイキャスト)だけなので、
**距離は出るが速度が出ない** — 不正確なのではなく、表現する型が無い。FMCW
(周波数変調連続波)は戻ってきた波の**位相**を保つので、同じ 1 回の取得から
距離・速度・角度の 3 つが**すべて閉形式で**出る。ここではそれを順に組み立てる。

(1) 設計: 波形パラメータだけから bin 幅・分解能・2 つのエイリアス限界を出す
    (`visiondesign` と同じ「画像でなく限界を返す」立場)。
(2) 前方モデル: 既知の (R, v) からビート立方体を合成し、2D FFT のピークが
    **その bin にビット完全に**立つことを確認する。
(3) 複数標的: 3 つの標的が互いに影響せず、それぞれの bin と振幅で立つ。
(4) 窓関数: 強い標的の漏れに埋もれた弱い標的が、窓を掛けると**見えるように
    なる**ことを dB で測る。サイドローブ表は実測値。
(5) 符号: 遠ざかる標的と近づく標的。**取り違えても絵は同じ**なので数値で示す。
(6) エイリアス: 一意測距範囲・最大非曖昧速度を超える要求は、折り返した答えを
    返さず **fail-closed** になる。折り返したら何が起きたかも計算して見せる。
(7) 角度: 8 素子の直線配列で到来角を復元し、ビーム幅より近い 2 標的は
    **1 つに融合する(でっち上げない)**ことを確認する。
(8) 4D 検出: 検出 (R, v) を beamform_doa にそのまま渡し、(距離, 速度, 角度)
    の完全な検出表を作る。
(9) 実サンプリング(I/Q でない)を渡すと何が起きるかを実測して示す。

【グラウンドトゥルース(数値で嘘を弾く)】
1. ビート周波数 f_b = 2SR/c → レンジ bin = f_b·N_s/f_s。
2. ドップラー位相 Δφ = 4π·v·T_c/λ → 速度 bin = 2v·T_c·N_c/λ。
3. bin 中心の標的のピーク振幅は厳密に a·N_s·N_c(実測 相対誤差 0.0)。
4. 遅延和のピーク電力は厳密に (N_a·N_c·N_s)²(実測 相対誤差 0.0)。
5. 窓の PSL は窓自身の零詰め DFT の実測(rect -13.25 / hann -31.47 /
   hamming -42.45 / blackman -58.11 dB)。
6. 半 bin ずれた標的の rect でのピーク損失は厳密に 2/π(= -3.92 dB)。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import rangedoppler as R  # noqa: E402

C = R.SPEED_OF_LIGHT_M_S


def main():
    # ------------------------------------------------------------------ #
    # 1) 設計: データが 1 バイトも無い段階で限界を出す                    #
    # ------------------------------------------------------------------ #
    wave = dict(n_samples=64, n_chirps=32, sample_rate_hz=1.0e7,
                slope_hz_per_s=2.0e13, chirp_period_s=5.0e-5,
                wavelength_m=3.8934e-3)
    d = R.fmcw_design(**wave)
    dr, dv = d["range_bin_m"], d["velocity_bin_ms"]
    print("1) 波形設計(掃引帯域 %.0f MHz、CPI %.2f ms):"
          % (d["sweep_bandwidth_hz"] / 1e6,
             d["coherent_processing_interval_s"] * 1e3))
    print("   レンジ  : bin %.4f m  = c/(2B)  一意測距範囲 %.2f m"
          % (dr, d["max_unambiguous_range_m"]))
    print("   速度    : bin %.4f m/s = λ/(2·N_c·T_c)  最大非曖昧速度 ±%.3f m/s"
          % (dv, d["max_unambiguous_velocity_ms"]))
    print("   ビート  : %.0f Hz/m   ドップラー位相 %.4f rad/chirp per (m/s)"
          % (d["beat_hz_per_metre"], d["doppler_rad_per_chirp_per_ms"]))
    assert abs(dr - C / (2.0 * d["sweep_bandwidth_hz"])) < 1e-12
    assert abs(d["max_unambiguous_range_m"] - dr * 64) < 1e-9
    assert d["angular_resolution_deg"] is None      # 1 素子 = 開口が無い

    # ------------------------------------------------------------------ #
    # 2) 前方モデルと 2D FFT: ピークは bin にビット完全に立つ             #
    # ------------------------------------------------------------------ #
    rbin, vbin = 3, 4
    cube = R.fmcw_beat_simulate([rbin * dr], [vbin * dv], **wave)
    m = R.range_doppler_map(cube, normalize=True)
    i, j = np.unravel_index(int(np.argmax(m)), m.shape)
    print("2) 単一標的 R=%.4f m / v=%+.4f m/s → 立方体 %s (complex):"
          % (rbin * dr, vbin * dv, cube.shape))
    print("   ピーク cell (doppler,range)=(%d,%d) 期待 (%d,%d)  正規化ピーク %.17g"
          % (i - 16, j, vbin, rbin, m[i, j]))
    off = m.copy()
    off[i, j] = 0.0
    print("   ピーク以外の最大は %.2e(= 丸め誤差。信号は 1 cell に全部入る)"
          % (off.max() / m[i, j]))
    assert (int(j), int(i) - 16) == (rbin, vbin)
    assert m[i, j] == 1.0                            # 厳密
    assert off.max() < 1e-15

    # ------------------------------------------------------------------ #
    # 3) 複数標的: 線形なので互いに影響しない                             #
    # ------------------------------------------------------------------ #
    truth = [(5, -6, 1.0), (12, 3, 0.6), (40, 11, 0.3)]
    multi = R.fmcw_beat_simulate([b * dr for b, _, _ in truth],
                                 [k * dv for _, k, _ in truth],
                                 amplitudes=[a for _, _, a in truth], **wave)
    det = R.range_doppler_peaks(R.range_doppler_map(multi, normalize=True),
                                dr, dv, n_peaks=3)
    print("3) 3 標的(振幅 1.0 / 0.6 / 0.3):")
    for p in sorted(det["peaks"], key=lambda p: p["range_bin"]):
        print("   R=%7.4f m  v=%+8.4f m/s  振幅 %.6f" % (
            p["range_m"], p["velocity_ms"], p["magnitude"]))
    got = {(p["range_bin"], p["doppler_bin"]): p["magnitude"] for p in det["peaks"]}
    for b, k, a in truth:
        assert abs(got[(b, k)] - a) < 1e-12
    print("   → 距離・速度は誤差 0.0、振幅は 1e-12 未満(重ね合わせは厳密)")

    # ------------------------------------------------------------------ #
    # 4) 窓関数: 漏れに埋もれた弱い標的を掘り出す                          #
    # ------------------------------------------------------------------ #
    weak_db = -45.0
    pair = R.fmcw_beat_simulate([10.5 * dr, 20.0 * dr], [0.0, 0.0],
                                amplitudes=[1.0, 10.0 ** (weak_db / 20.0)],
                                **wave)
    print("4) 強い標的(bin 10.5、半 bin ずれ)+ %.0f dB 弱い標的(bin 20):"
          % weak_db)
    print("   窓        ピーク損失   bin20 の高さ   局所最大か")
    for w in R.WINDOWS:
        prof = R.fmcw_range_profile(R.fmcw_window_apply(pair, w, "range"),
                                    normalize=True)
        lvl = 20.0 * np.log10(prof[20] / prof.max())
        is_pk = bool(prof[20] > prof[19] and prof[20] > prof[21])
        print("   %-9s %7.2f dB   %8.2f dB      %s"
              % (w, 20.0 * np.log10(prof.max()), lvl, "はい" if is_pk else "いいえ"))
        if w == "rect":
            assert not is_pk                 # 漏れに埋もれて検出できない
            assert lvl > -30.0               # 真値 -45 dB より 15 dB も上
            assert abs(prof.max() - 2.0 / np.pi) < 1e-4   # scalloping = 2/π
        else:
            assert is_pk                     # 窓を掛けると出てくる
    print("   → rect ではピークですらない(真値 -45 dB のところが -24.6 dB)。")
    print("     rect のピーク損失 -3.92 dB は半 bin ずれの scalloping 2/π ちょうど")

    # ------------------------------------------------------------------ #
    # 5) 符号: 遠ざかる = 正。取り違えても絵は同じなので数値で示す         #
    # ------------------------------------------------------------------ #
    away = R.range_doppler_map(R.fmcw_beat_simulate([10 * dr], [+4 * dv], **wave))
    toward = R.range_doppler_map(R.fmcw_beat_simulate([10 * dr], [-4 * dv], **wave))
    ia = int(np.unravel_index(int(np.argmax(away)), away.shape)[0]) - 16
    it = int(np.unravel_index(int(np.argmax(toward)), toward.shape)[0]) - 16
    print("5) 速度の符号(v = dR/dt、遠ざかる = 正):")
    print("   遠ざかる %+.4f m/s → 速度 bin %+d / 近づく %+.4f m/s → 速度 bin %+d"
          % (+4 * dv, ia, -4 * dv, it))
    print("   2 枚のマップは零速度を軸にちょうど鏡像 = %s"
          % np.allclose(away, np.roll(toward[::-1, :], 1, axis=0)))
    print("   → 規約を逆にしても絵は同じくらいもっともらしい。だから型でなく")
    print("     テストで固定してある(tests/test_rangedoppler.py の符号クラス)")
    assert ia == +4 and it == -4

    # ------------------------------------------------------------------ #
    # 6) エイリアス: 折り返した答えを返さない                              #
    # ------------------------------------------------------------------ #
    print("6) エイリアスは黙って通さない:")
    folded = d["max_unambiguous_range_m"] + dr
    f_b = 2.0 * wave["slope_hz_per_s"] * folded / C
    alias = (f_b * 64 / wave["sample_rate_hz"]) % 64
    try:
        R.fmcw_beat_simulate([folded], [0.0], **wave)
        raise AssertionError("エイリアスが通ってしまった")
    except ValueError as exc:
        print("   %.2f m を頼む → 拒否(もし通せば bin %.1f = %.2f m に見えた)"
              % (folded, alias, alias * dr))
        assert "unambiguous range" in str(exc)
    v_over = d["max_unambiguous_velocity_ms"] + 2 * dv
    f_d = 2.0 * v_over / wave["wavelength_m"]
    b = (f_d * wave["chirp_period_s"] * 32) % 32
    signed = b - 32 if b >= 16 else b
    try:
        R.fmcw_beat_simulate([10.0], [v_over], **wave)
        raise AssertionError("エイリアスが通ってしまった")
    except ValueError:
        print("   %+.2f m/s を頼む → 拒否(もし通せば速度 bin %+.1f = %+.2f m/s、"
              "**符号が反転**)" % (v_over, signed, signed * dv))
        assert signed < 0.0
    try:
        R.fmcw_beat_simulate([10.0], [72.0], **wave)      # 72 km/h のつもり
        raise AssertionError("km/h が通ってしまった")
    except ValueError as exc:
        print("   72(km/h のつもり)→ 拒否。ただしこれは**上限による偶然の防御**で、")
        print("     30 km/h(= 8.3 m/s)を m/s と取り違えたら窓の中なので気づけない")
        assert "km/h" in str(exc)

    # ------------------------------------------------------------------ #
    # 7) 角度: 8 素子の直線配列                                            #
    # ------------------------------------------------------------------ #
    arr = dict(wave, n_antennas=8)
    da = R.fmcw_design(**arr)
    one = R.fmcw_beat_simulate([6 * dr], [0.0], angles_deg=[20.0], **arr)
    sp = R.beamform_delay_sum(one)
    print("7) 8 素子 λ/2 配列(ビーム幅 %.2f 度、視野 ±%.0f 度):"
          % (da["angular_resolution_deg"], da["max_unambiguous_angle_deg"]))
    print("   到来角 20 度 → 推定 %.1f 度  ピーク電力 %.17g = (N_a·N_c·N_s)²"
          % (np.arange(-90, 90.5, 1.0)[int(np.argmax(sp))], sp.max()))
    assert sp.max() == float(8 * 32 * 64) ** 2
    far = R.fmcw_beat_simulate([6 * dr, 6 * dr], [0.0, 0.0],
                               angles_deg=[-30.0, 30.0], **arr)
    near = R.fmcw_beat_simulate([6 * dr, 6 * dr], [0.0, 0.0],
                                angles_deg=[-2.0, 2.0], **arr)
    print("   ±30 度の 2 標的(ビーム幅より遠い)→ %s"
          % R.beamform_doa(far, n_targets=2)["angles_deg"])
    print("   ±2 度の 2 標的(ビーム幅より近い)→ %s = 1 本に融合。"
          % R.beamform_doa(near, n_targets=2)["angles_deg"])
    print("     遅延和は分離できないので、2 本あるふりをしない(正直な限界)")
    assert sorted(R.beamform_doa(far, n_targets=2)["angles_deg"]) == [-30.0, 30.0]
    assert R.beamform_doa(near, n_targets=2)["n_found"] == 1
    try:
        R.beamform_doa(R.fmcw_beat_simulate([6 * dr], [0.0], **wave))
        raise AssertionError("1 素子で角度が出てしまった")
    except ValueError:
        print("   1 素子(開口なし)→ 拒否。スペクトルは平坦で、argmax は")
        print("     先頭の格子点 -90 度を「自信のある方向」として返してしまう")

    # ------------------------------------------------------------------ #
    # 8) 4D 検出: (距離, 速度, 角度)                                       #
    # ------------------------------------------------------------------ #
    scene = [(3, 4, 10.0, 1.0), (20, -2, -40.0, 0.4), (33, 7, 55.0, 0.7)]
    cube4 = R.fmcw_beat_simulate([b * dr for b, _, _, _ in scene],
                                 [k * dv for _, k, _, _ in scene],
                                 angles_deg=[t for _, _, t, _ in scene],
                                 amplitudes=[a for _, _, _, a in scene], **arr)
    print("8) 4D 検出(1 回の取得から 3 つの量を同時に):")
    print("   距離 [m]   速度 [m/s]   角度 [deg]   振幅")
    rows = []
    for p in sorted(R.range_doppler_peaks(
            R.range_doppler_map(cube4, normalize=True), dr, dv, n_peaks=3
            )["peaks"], key=lambda p: p["range_bin"]):
        doa = R.beamform_doa(cube4, range_bin=p["range_bin"],
                             doppler_bin=p["doppler_bin"], range_bin_m=dr,
                             velocity_bin_ms=dv)
        rows.append((p["range_m"], p["velocity_ms"], doa["angles_deg"][0],
                     p["magnitude"]))
        print("   %8.4f   %+9.4f   %+9.1f   %.4f" % rows[-1])
    for (rb, kb, th, a), row in zip(scene, rows):
        assert abs(row[0] - rb * dr) < 1e-12
        assert abs(row[1] - kb * dv) < 1e-12
        assert row[2] == th
    print("   → 検出の doppler_bin をそのまま beamform_doa に渡せる(符号規約が")
    print("     同じ)。距離・速度は誤差 0.0、角度は格子上で厳密一致")

    # ------------------------------------------------------------------ #
    # 9) I/Q でない(実サンプリング)を渡したら何が起きるか                 #
    # ------------------------------------------------------------------ #
    real = R.fmcw_beat_simulate([10 * dr], [4 * dv], **wave).real
    mr = np.fft.fftshift(np.abs(np.fft.fft(np.fft.fft(real[0], axis=1), axis=0)),
                         axes=0) / (32 * 64)
    hits = sorted((int(i) - 16, int(j), float(mr[i, j]))
                  for i, j in np.argwhere(mr > 0.2 * mr.max()))
    print("9) 実サンプリング(I/Q でない)を渡すと:")
    for k, jj, a in hits:
        print("   速度 bin %+d / レンジ bin %2d(%.2f m)  振幅 %.4f" % (k, jj, jj * dr, a))
    print("   → 本物(bin 10)と**同じ振幅**の幽霊が bin 54 = %.2f m に、速度の"
          % (54 * dr))
    print("     符号を反転して立つ。どちらが本物かマップからは分からない。")
    print("     だから _as_beat_cube は dtype 段階で拒否し、解析信号を作れと言う")
    try:
        R.range_doppler_map(real)
        raise AssertionError("実配列が通ってしまった")
    except ValueError as exc:
        assert "real-valued" in str(exc)
    assert len(hits) == 2 and all(abs(a - 0.5) < 1e-12 for _, _, a in hits)

    print("PASS: rangedoppler 8 op すべてが閉形式のグラウンドトゥルースと一致")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
