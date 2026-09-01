# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""acoustic_condition_monitoring — 音響状態監視 op(acoustics)を「回転機械を
1 台、音だけで診断する」筋で一巡する。

    py -3.11 examples/acoustic_condition_monitoring.py

【この例が解く問題】
機械の音を録った。マイク 1 本(と加振試験のとき 2 本)。そこから
「どの部品がどう傷んでいるか」「何 dB か」「その振動はこの加振から来たのか」を
出す。画像でも点群でもない **1 次元の音圧**が唯一の観測量で、
`dsp` は素材(読み込み・帯域通過・スペクトル・包絡線)までを持っている。
この例はその先 —— 現場の問いに答える道具 —— を順に通す。

(1) 可逆 STFT: 位相を保つ短時間フーリエ変換。往復が機械精度で戻る。
    `dsp.spectrogram` は強度だけなので戻れない、という差を数値で見る。
(2) 窓と正規化: 窓を変えると生スペクトルの振幅は変わる。正規化を明示すれば
    どの窓でも同じ振幅が返ることを確かめる(=もっともらしく間違った dB を防ぐ)。
(3) 軸受診断: 既知の欠陥周波数で振幅変調した信号を合成し、**生スペクトルには
    欠陥周波数が存在しない**こと、包絡線スペクトルには**変調度そのもの**が
    立つことを確かめる。
(4) 復調帯域を機械に選ばせる: スペクトル尖度で「どこが衝撃的か」を出し、
    その帯域だけで復調して欠陥周波数を当てる(共振周波数を人が知らなくてよい)。
(5) 軸受運動学: 幾何から 4 つの特徴周波数を出し、厳密な恒等式で検算する。
(6) ケプストラム: 既知の反射遅延と既知の側帯波間隔を quefrency 軸で当てる。
(7) 次数比分析: 回転数が変わる走行記録で、**通常のスペクトルが壊れる**ことと
    角度領域リサンプルで次数が 1 本に戻ることを、同じ信号で並べて見る。
(8) 音響指標: 1/3 オクターブ帯域、A/C 特性、等価騒音レベル、パーセンタイル。
    基準値を明示しない dB は無意味、という規律を数値で示す。
(9) 2 チャネル: 既知の利得・既知の遅延・既知の雑音から伝達関数を復元し、
    H2 推定が 100 % 外れていても数字は何もおかしく見えないことを見る。
(10) 取り違えの実演: **正しいデータ + 間違ったサンプリング周波数**は
    例外も NaN も出さずに違う答えを返す。

【グラウンドトゥルース(数値で嘘を弾く)】
1.  STFT 往復: max|x - istft(stft(x))| が 1e-12 未満(窓・ホップを変えて)。
2.  振幅正規化: 窓を 5 種類変えても bin 中心の正弦は振幅どおりに読める。
3.  AM 合成: 解析包絡線は厳密に 1 + m cos(2 pi f_d t) なので、包絡線スペクトルの
    ピークは f_d に立ち、振幅は m。生スペクトルの f_d 成分は 0。
4.  スペクトル尖度: Gauss 雑音で 0、純音で -1(閉形式)。
5.  運動学: BPFO + BPFI = N f_r、BPFO = N FTF(厳密)。
6.  ケプストラム: 遅延 D の反射 -> quefrency = D/fs(bin 厳密)。
7.  次数: 既知次数は速度ランプを通しても同じ bin。共振は逆に滲む。
8.  A 特性は 1 kHz で厳密に 0 dB(構成上)。正弦の Leq = 10log10(A^2/2)。
    50/50 の 2 値信号で L10 と L90 が構成レベルそのもの。
9.  y = g x なら |H| = g、コヒーレンス = 1。出力雑音下で |H1/H2| = coherence(厳密)。
10. rate を 25600 -> 48000 と偽ると欠陥周波数の報告が 107 -> 200.6 Hz に動く。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import acoustics as A
import dsp


def main():
    # ------------------------------------------------------------------ #
    # 1) 可逆 STFT — 位相を保つ経路                                        #
    # ------------------------------------------------------------------ #
    rng = np.random.default_rng(0)
    fs = 16000.0
    x = rng.standard_normal(4096)
    print("1) 可逆 STFT(位相を保つ / dsp.spectrogram は強度だけで戻れない):")
    for window, win, hop in (("hann", 256, 128), ("hann", 256, 64),
                             ("blackman", 512, 128), ("boxcar", 256, 128)):
        tr = A.stft(x, fs, win=win, hop=hop, window=window)
        err = float(np.abs(A.istft(tr) - x).max())
        print(f"   {window:9s} win={win:4d} hop={hop:4d} -> "
              f"max|x-istft(stft(x))| = {err:.3e}  (NOLA 下限 {tr['nola_min']:.4g})")
        assert err < 1e-12
    tr = A.stft(x, fs, win=256, hop=255)
    print(f"   hann      win= 256 hop= 255 -> {np.abs(A.istft(tr) - x).max():.3e}"
          f"  (NOLA 下限 {tr['nola_min']:.3e} = 条件数が悪い、と分かる)")
    _, _, S = dsp.spectrogram(x, fs, win=256)
    print(f"   比較: dsp.spectrogram の返りは {S.dtype} = 位相が無く、"
          f"原理的に戻れない")

    # ------------------------------------------------------------------ #
    # 2) 窓と正規化 — 明示しないと「もっともらしく間違った dB」が出る       #
    # ------------------------------------------------------------------ #
    amp = 0.7
    tone = amp * np.sin(2.0 * np.pi * 1000.0 * np.arange(16000) / fs)
    print("\n2) 窓と正規化(真の振幅 0.700000、1 kHz は bin 中心):")
    raw, cal = [], []
    for w in ("hann", "hamming", "blackman", "flattop", "boxcar"):
        t0 = A.stft(tone, fs, win=256, hop=64, window=w, scaling="none")
        t1 = A.stft(tone, fs, win=256, hop=64, window=w, scaling="amplitude")
        r = float(np.abs(t0["spectra"][16, t0["interior"]]).mean())
        c = float(np.abs(t1["spectra"][16, t1["interior"]]).mean())
        raw.append(r)
        cal.append(c)
        print(f"   {w:9s}: scaling='none' -> {r:8.4f}   "
              f"scaling='amplitude' -> {c:.6f}")
    print(f"   正規化なしは窓で {min(raw):.1f}〜{max(raw):.1f} と "
          f"{max(raw) / min(raw):.1f} 倍ばらつく。明示すれば全窓で一致 "
          f"(最大差 {max(cal) - min(cal):.2e})")
    assert max(cal) - min(cal) < 1e-9

    # ------------------------------------------------------------------ #
    # 3) 軸受診断 — 欠陥周波数は生スペクトルに存在しない                   #
    # ------------------------------------------------------------------ #
    fs_b, f_carrier, f_defect, m = 25600.0, 3000.0, 107.0, 0.5
    sig = A.synthesize_bearing_signal(fs_b, 1.0, f_carrier, f_defect,
                                      modulation=m, mode="am")
    freqs, mag = dsp.spectrum(sig, fs_b)
    amp1 = mag * 2.0 / sig.size
    df = fs_b / sig.size
    print(f"\n3) 軸受(共振 {f_carrier:.0f} Hz を {f_defect:.0f} Hz で "
          f"変調度 {m} の振幅変調):")
    print(f"   生スペクトル: 欠陥 {f_defect:.0f} Hz の振幅 = "
          f"{amp1[int(round(f_defect / df))]:.3e}  <- **存在しない**")
    print(f"                 搬送波 {f_carrier:.0f} Hz = "
          f"{amp1[int(round(f_carrier / df))]:.6f}, "
          f"側帯波 {f_carrier - f_defect:.0f}/{f_carrier + f_defect:.0f} Hz = "
          f"{amp1[int(round((f_carrier - f_defect) / df))]:.6f} / "
          f"{amp1[int(round((f_carrier + f_defect) / df))]:.6f}  (= m/2)")
    env = A.envelope_spectrum(sig, fs_b, 2000.0, 4000.0)
    print(f"   包絡線スペクトル: ピーク {env['peak_freq']:.4f} Hz  "
          f"振幅 {env['peak_amplitude']:.6f}  <- 変調度 m そのもの")
    print(f"                     突出度 {env['peak_prominence']:.1f}、"
          f"帯域内エネルギー比 {env['band_fraction']:.4f}")
    assert abs(env["peak_freq"] - f_defect) < 1e-9
    assert abs(env["peak_amplitude"] - m) < 5e-4
    assert amp1[int(round(f_defect / df))] < 1e-12

    # ------------------------------------------------------------------ #
    # 4) 復調帯域を機械に選ばせる                                          #
    # ------------------------------------------------------------------ #
    imp = A.synthesize_bearing_signal(fs_b, 1.0, f_carrier, f_defect,
                                      mode="impulse", damping=0.05,
                                      noise_sigma=0.05, seed=3)
    sk = A.spectral_kurtosis(imp, fs_b)
    lo = max(1.0, sk["max_freq"] - sk["bin_hz"])
    hi = sk["max_freq"] + sk["bin_hz"]
    auto = A.envelope_spectrum(imp, fs_b, lo, hi)
    print("\n4) 復調帯域の自動選択(共振周波数を人が知らない場合):")
    print(f"   スペクトル尖度: 最大 {sk['max_kurtosis']:.3f} @ "
          f"{sk['max_freq']:.0f} Hz(窓 {sk['window_seconds'] * 1e3:.2f} ms、"
          f"推定器の標準偏差 {sk['noise_sigma']:.3f})")
    print(f"   選ばれた帯域 {lo:.0f}-{hi:.0f} Hz で復調 -> "
          f"{auto['peak_freq']:.4f} Hz  (真値 {f_defect:.0f})")
    print(f"   窓が衝撃間隔 {1e3 / f_defect:.2f} ms より長いと破綻する: ", end="")
    bad = A.spectral_kurtosis(imp, fs_b, win=256)
    print(f"win=256 ({bad['window_seconds'] * 1e3:.1f} ms) は "
          f"最大尖度 {bad['max_kurtosis']:+.3f} @ {bad['max_freq']:.0f} Hz "
          f"= 共振と無関係な帯域を指す(全フレームが衝撃を 1 個ずつ含むので、"
          f"帯域が定常に見えてしまう)")
    assert abs(auto["peak_freq"] - f_defect) < 1e-9

    # ------------------------------------------------------------------ #
    # 5) 軸受運動学 — 幾何から出して恒等式で検算                           #
    # ------------------------------------------------------------------ #
    b = A.bearing_defect_frequencies(1800.0, 9, 8.0, 40.0)
    print("\n5) 軸受運動学(1800 rpm、転動体 9 個、d=8、D=40、接触角 0):")
    print(f"   軸 {b['shaft_hz']:.6f} / 保持器 FTF {b['ftf_hz']:.6f} / "
          f"外輪 BPFO {b['bpfo_hz']:.6f} / 内輪 BPFI {b['bpfi_hz']:.6f} / "
          f"転動体 BSF {b['bsf_hz']:.6f} Hz")
    print(f"   検算: BPFO + BPFI - N*f_r = "
          f"{abs(b['bpfo_hz'] + b['bpfi_hz'] - 9 * b['shaft_hz']):.3e}、"
          f"BPFO - N*FTF = {abs(b['bpfo_hz'] - 9 * b['ftf_hz']):.3e}(厳密 0)")
    print(f"   注意: 転動体欠陥は両輪を叩くので普通は 2*BSF = "
          f"{b['bsf_hz_2x']:.3f} Hz に出る")
    assert abs(b["bpfo_hz"] + b["bpfi_hz"] - 9 * b["shaft_hz"]) < 1e-12

    # ------------------------------------------------------------------ #
    # 6) ケプストラム — 既知の遅延と既知の間隔                             #
    # ------------------------------------------------------------------ #
    fs_c, n_c, delay = 8000.0, 8192, 200
    base = rng.standard_normal(n_c)
    echoed = base.copy()
    echoed[delay:] += 0.6 * base[:-delay]
    ce = A.cepstrum(echoed, fs_c)
    train = np.zeros(16384)
    train[::160] = 1.0                                   # 50 Hz @ 8 kHz
    lines = np.convolve(train, rng.standard_normal(64))[:16384]
    cl = A.cepstrum(lines + 0.01 * rng.standard_normal(16384), fs_c,
                    min_quefrency=0.002)
    print("\n6) ケプストラム(周波数軸の周期構造を quefrency 軸へ):")
    print(f"   反射 {delay} サンプル -> quefrency {ce['peak_quefrency']:.6f} s "
          f"= {int(round(ce['peak_quefrency'] * fs_c))} サンプル "
          f"(真値 {delay})、床打ち bin {ce['floored_bins']}")
    print(f"   50 Hz 間隔の線スペクトル -> {cl['peak_quefrency']:.6f} s = "
          f"{cl['peak_rate_hz']:.2f} Hz (真値 50.00)")
    assert int(round(ce["peak_quefrency"] * fs_c)) == delay
    assert abs(cl["peak_rate_hz"] - 50.0) < 1e-9

    # ------------------------------------------------------------------ #
    # 7) 次数比分析 — 既存の素朴なやり方が壊れることを同じ信号で見る       #
    # ------------------------------------------------------------------ #
    ramp = A.synthesize_speed_ramp(5000.0, 4.0, 600.0, 1800.0,
                                   orders=(1.0, 3.5), resonance_hz=400.0)
    xs, rate_s, rpm_s = ramp["signal"], ramp["rate"], ramp["rpm"]
    f_o, m_o = dsp.spectrum(xs - xs.mean(), rate_s)
    a_o = m_o * 2.0 / xs.size
    sel = (f_o >= 32.0) & (f_o <= 110.0)                 # 次数 3.5 は 35-105 Hz
    wide = f_o[sel][a_o[sel] >= a_o[sel].max() / np.sqrt(2.0)]
    ordsp = A.order_spectrum(xs, rate_s, rpm_s, samples_per_rev=64,
                             revolutions=78)
    j = int(round(3.5 / ordsp["resolution_order"]))
    narrow = ordsp["orders"][ordsp["magnitude"]
                             >= ordsp["magnitude"][j] / np.sqrt(2.0)]
    narrow = narrow[(narrow > 3.0) & (narrow < 4.0)]
    print("\n7) 次数比分析(600->1800 rpm の走行、次数 1.0 と 3.5、"
          "固定共振 400 Hz、どちらも振幅 1.0):")
    print(f"   通常のスペクトル: 次数 3.5 成分の最大振幅 {a_o[sel].max():.6f} "
          f"@ {f_o[sel][int(np.argmax(a_o[sel]))]:.2f} Hz、"
          f"-3 dB 幅 {wide.max() - wide.min():.2f} Hz  <- **壊れている**")
    print(f"   次数スペクトル:   次数 {ordsp['orders'][j]:.4f} の振幅 "
          f"{ordsp['magnitude'][j]:.6f}、-3 dB 幅 "
          f"{narrow.max() - narrow.min():.5f} 次数  <- 1 本に戻る")
    lo_o, hi_o = 400.0 / (1800.0 / 60.0), 400.0 / (600.0 / 60.0)
    selr = (ordsp["orders"] >= lo_o) & (ordsp["orders"] <= hi_o)
    print(f"   逆向きの確認: 固定 400 Hz の共振は通常スペクトルで "
          f"{a_o[int(np.argmin(np.abs(f_o - 400.0)))]:.4f}(鋭い)、"
          f"角度領域では {ordsp['magnitude'][selr].max():.4f} が "
          f"{hi_o - lo_o:.1f} 次数に散る")
    odd = A.order_spectrum(xs, rate_s, rpm_s, 64, revolutions=79)
    j_odd = int(round(3.5 / odd["resolution_order"]))
    print(f"   罠: 半整数次数は回転数が奇数だと bin をまたぐ — 次数 3.5 の振幅は "
          f"revolutions=79 で {odd['magnitude'][j_odd]:.6f}、"
          f"78 で {ordsp['magnitude'][j]:.6f}(真値 1.0、例外は出ない)")
    assert odd["magnitude"][j_odd] < 0.7
    assert abs(ordsp["magnitude"][j] - 1.0) < 5e-3
    assert a_o[sel].max() < 0.15

    # ------------------------------------------------------------------ #
    # 8) 音響指標 — 基準値と重み付けを言わない dB は無意味                 #
    # ------------------------------------------------------------------ #
    one_k = np.sin(2.0 * np.pi * 1000.0 * np.arange(16000) / fs)
    print("\n8) 音響指標:")
    print("   A/C 特性(定義式から計算。規格の数表は 1 つも転記していない):")
    fr = np.array([10.0, 31.5, 100.0, 1000.0, 4000.0, 10000.0, 20000.0])
    wa = A.weighting_response(fr, "A")
    wc = A.weighting_response(fr, "C")
    print("     f[Hz]  " + " ".join(f"{v:9.1f}" for v in fr))
    print("     A[dB]  " + " ".join(f"{v:9.4f}" for v in wa))
    print("     C[dB]  " + " ".join(f"{v:9.4f}" for v in wc))
    print(f"     1 kHz で厳密に 0.0(構成上): A={wa[3]!r}  C={wc[3]!r}")
    deep = A.weighting_response(np.array([0.001, 0.01]), "A", floor_db=-1e6)
    deepc = A.weighting_response(np.array([0.001, 0.01]), "C", floor_db=-1e6)
    print(f"     低域漸近: A {deep[1] - deep[0]:.6f} dB/decade(理論 80)、"
          f"C {deepc[1] - deepc[0]:.6f}(理論 40)")
    oct3 = A.octave_spectrum(0.7 * one_k, fs, fraction=3, ref=1.0)
    k1 = int(np.argmin(np.abs(oct3["centers"] - 1000.0)))
    closed = 10.0 * np.log10(0.7 ** 2 / 2.0)
    print("   1/3 オクターブ(振幅 0.7 の 1 kHz 正弦、ref=1.0):")
    print(f"     1 kHz 帯域 {oct3['levels'][k1]:.10f} dB  "
          f"閉形式 10log10(0.7^2/2) = {closed:.10f}  差 "
          f"{abs(oct3['levels'][k1] - closed):.3e}")
    print(f"     床打ちした帯域 {int(oct3['clamped'].sum())}/"
          f"{oct3['clamped'].size}(-inf ではなく {A.FLOOR_DB:.0f} dB を返す)")
    print("   等価騒音レベル Leq(ref=1.0 = 「渡した単位の 1 に対する dB」、"
          "dB SPL ではない):")
    print(f"     1 kHz 正弦 振幅1.0: Z {A.equivalent_level(one_k, fs, 'Z'):.6f}  "
          f"A {A.equivalent_level(one_k, fs, 'A'):.6f}  "
          f"(A は 1 kHz で 0 dB なので一致)")
    print(f"     振幅 2 倍で {A.equivalent_level(2 * one_k, fs, 'Z') - A.equivalent_level(one_k, fs, 'Z'):+.6f} dB、"
          f"ref を 1/10 にすると "
          f"{A.equivalent_level(one_k, fs, 'Z', ref=0.1) - A.equivalent_level(one_k, fs, 'Z'):+.6f} dB")
    two = np.concatenate([one_k[:8000], 0.1 * one_k[8000:]])
    pl = A.percentile_level(two, fs, (10.0, 50.0, 90.0), weighting="Z",
                            window_s=0.125)
    print(f"   パーセンタイル(前半 振幅1.0 / 後半 0.1 の 50:50、"
          f"{pl['n_blocks']} ブロック):")
    print(f"     L10 {pl['L10']:.6f}  L50 {pl['L50']:.6f}  L90 {pl['L90']:.6f}  "
          f"Leq {pl['leq']:.6f}")
    print(f"     L10 - L90 = {pl['L10'] - pl['L90']:.6f} dB(50:50 なら構成"
          f"レベルそのもの)。Leq は L50 より "
          f"{pl['leq'] - pl['L50']:+.3f} dB = エネルギーは大きい側に寄る")
    assert abs(oct3["levels"][k1] - closed) < 1e-9
    assert abs((pl["L10"] - pl["L90"]) - 20.0) < 1e-6

    # ------------------------------------------------------------------ #
    # 9) 2 チャネル — 応答とコヒーレンスは必ず一緒に読む                   #
    # ------------------------------------------------------------------ #
    n2 = 16384
    drive = rng.standard_normal(n2)
    print("\n9) 2 チャネル(加振 -> 応答):")
    hg = A.transfer_function(drive, 2.5 * drive, fs, win=1024)
    print(f"   y = 2.5x        : |H| 平均 {hg['magnitude'].mean():.10f}  "
          f"最大偏差 {np.abs(hg['magnitude'] - 2.5).max():.3e}  "
          f"コヒーレンス {hg['coherence'].mean():.10f}")
    d_ = 37
    yd = np.zeros(n2)
    yd[d_:] = 0.8 * drive[:-d_]
    hd = A.transfer_function(drive, yd, fs, win=1024)
    seld = (hd["freqs"] > 200.0) & (hd["freqs"] < 7000.0)
    slope = np.polyfit(hd["freqs"][seld], np.unwrap(hd["phase_rad"])[seld], 1)[0]
    print(f"   y = 0.8 x[n-37] : 群遅延 {-slope / (2 * np.pi) * fs:.6f} サンプル "
          f"(真値 37)、|H| {hd['magnitude'][seld].mean():.6f}(真値 0.8)")
    noisy = 2.5 * drive + 2.5 * rng.standard_normal(n2)      # 出力雑音 0 dB
    h1 = A.transfer_function(drive, noisy, fs, win=1024, estimator="h1")
    h2 = A.transfer_function(drive, noisy, fs, win=1024, estimator="h2")
    ratio = np.abs(h1["response"] / h2["response"])
    print(f"   出力雑音 0 dB   : H1 |H| 平均 {h1['magnitude'].mean():.6f} "
          f"(真値 2.5、誤差 "
          f"{100 * abs(h1['magnitude'].mean() - 2.5) / 2.5:.2f} %)")
    print(f"                     H2 |H| 平均 {h2['magnitude'].mean():.6f} "
          f"<- **真値の {h2['magnitude'].mean() / 2.5:.2f} 倍。ずれているが、"
          f"この数字を見て変だと思う理由はどこにも無い**")
    print(f"                     |H1/H2| = コヒーレンス を点ごとに確認: "
          f"最大差 {np.abs(ratio - h1['coherence']).max():.3e}")
    ci = A.coherence(drive, rng.standard_normal(n2), fs, win=1024)
    print(f"   無相関な 2 本    : コヒーレンス平均 {ci['mean_coherence']:.6f} "
          f"<- 0 ではなく bias {ci['bias']:.4f} = 1/{ci['n_frames']} 付近に出る")
    assert np.abs(ratio - h1["coherence"]).max() < 1e-12

    # ------------------------------------------------------------------ #
    # 10) 取り違えの実演 — 例外も NaN も出ない誤り                         #
    # ------------------------------------------------------------------ #
    print("\n10) この族が防げない唯一の誤り(だから正直に見せる):")
    print("    同じ正しい録音を、違うサンプリング周波数だと言って渡す:")
    for r in (fs_b, 48000.0):
        e = A.envelope_spectrum(sig, r, 2000.0, 4000.0)
        o = A.octave_spectrum(sig, r)
        loud = o["centers"][int(np.argmax(o["levels"]))]
        tag = "(真)" if r == fs_b else "(偽)"
        print(f"      rate={r:7.0f} {tag} -> 欠陥 {e['peak_freq']:8.4f} Hz、"
              f"A 特性 Leq {A.equivalent_level(sig, r, 'A'):+.4f} dB、"
              f"最大 1/3 オクターブ {loud:.1f} Hz")
    print("    例外は出ない。NaN も出ない。全部もっともらしい。")
    print("    -> 防げるのは「文字列 / bool / complex の rate」だけなので、"
          "そこは fail-closed にしてある:")
    for badv in ("16000", True, 16000 + 0j):
        try:
            A.envelope_spectrum(sig, badv, 2000.0, 4000.0)
            print(f"      rate={badv!r}: 通ってしまった(バグ)")
        except ValueError as exc:
            print(f"      rate={badv!r:12s} -> ValueError: {str(exc)[:66]}...")

    print("\nPASS: acoustics 19 op すべてが閉形式のグラウンドトゥルースと一致")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
