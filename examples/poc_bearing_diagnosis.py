# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_bearing_diagnosis — 転がり軸受の異常診断を「どこまで雑音に埋もれても
当てられるか」で測る PoC。

    py -3.11 examples/poc_bearing_diagnosis.py

【この PoC が答える問い】
`acoustic_condition_monitoring.py` は acoustics 19 op が閉形式のグラウンド
トゥルースと一致することを示す。こちらはその一歩先 —— **「検出できました」の
先にある「どこで検出できなくなるか」** を数字で出す。具体的には:

  * 欠陥周波数の真値は**幾何から式で決まる**(転動体数・ピッチ円径・素子径・
    接触角・回転数)。`bearing_defect_frequencies` の閉形式を真値とし、
    その周波数で衝撃列を合成して、包絡線スペクトルが**元の式に戻れるか**を測る。
  * 雑音 sigma を 7 段振り、**検出率(10 seed 中)**と**ピークの顕著さ**を出す。
  * ゼロ点を 2 つ置く。**(a) 生 FFT スペクトル** —— 包絡線解析が本当に何 dB
    分そこを上回るのか。**(b) 欠陥の無い記録(null)** —— 検出の閾値は
    「欠陥が無いときに何が出るか」から決める。閾値を先に決めて後から
    当てはめない。
  * 帯域選択(`spectral_kurtosis`)が選んだ帯域が**本当に共振帯に乗って
    いるか**を、真の共振周波数を知っている立場から採点する。

【この PoC が言えないこと(先に書く)】
合成信号である。実機の記録には転がり滑り(実測 1 % 程度)・複数の共振・
回転数変動・他部品の音が全部乗る。ここで出る検出限界 SNR は
**この合成モデル・この帯域・この記録長での上界**であって、現場の値ではない。
本 PoC の主張は「検出限界という量が測れる形になっている」ことまで。

【グラウンドトゥルース(閉形式)】
1. BPFO + BPFI = N f_r、BPFO = N FTF —— float64 で厳密に 0(丸め誤差ですらない)。
2. 衝撃列の繰り返し率は仕込んだ欠陥周波数そのもの。記録長 4 s なので
   スペクトル分解能は 0.25 Hz、真値との差はこの 1 bin 以内に入るはず。
3. 欠陥の無い記録では、どの周波数にも「欠陥」は無い —— null の顕著さの分布が
   検出閾値になる。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import acoustics as A
import dsp
import examplefig as figs

# 記録の条件。すべてここに集める(あとで「どの条件での数字か」を言えるように)。
RATE = 25600.0          # サンプリング周波数 [Hz]
DURATION = 4.0          # 記録長 [s] -> スペクトル分解能 1/4 = 0.25 Hz
RESONANCE = 3000.0      # 構造共振(搬送波)[Hz]。診断側は「知らない」ことにする場面がある
DAMPING = 0.05          # 共振の減衰比
BAND = (2000.0, 4000.0)  # 復調帯域。共振を知っている場合の「正解の帯域」
LOW, HIGH = 20.0, 500.0  # 欠陥周波数を探す範囲 [Hz]。軸受の特徴周波数はここに入る
HARMONICS = (1, 2, 3, 4)  # 衝撃列は基本波だけでなく高調波にも立つ(どれに当たっても正解)
TOL_FRAC = 0.01         # 一致とみなす相対許容(実機の滑り 1 % 相当)

# 軸受の幾何。9 個の転動体、素子径 7.94 mm、ピッチ円径 39.04 mm、接触角 0 度。
BEARING = dict(rpm=1750.0, n_elements=9, element_diameter=7.94,
               pitch_diameter=39.04, contact_angle_deg=0.0)


def _raw_amplitude_spectrum(x, rate):
    """生スペクトル(ゼロ点)を**片側振幅**に直して返す。

    `dsp.spectrum` が返すのは正規化前の ``|rfft|`` で、記録長に比例して伸びる。
    包絡線スペクトル側は内部で 2/N を掛けた振幅を返すので、そろえないと
    比較が「長さの違い」を見ているだけになる(この 2/N は 2 度掛けやすい)。
    """
    freqs, mag = dsp.spectrum(x, rate)
    return freqs, mag * (2.0 / len(x))


def _peak_and_prominence(freqs, magnitude, half_width=40.0):
    """探索範囲 LOW..HIGH の最大ピークと、その**局所**顕著さを返す。

    顕著さ = ピーク値 / (ピーク近傍 ±``half_width`` Hz の中央値)。
    ピーク自身の裾を巻き込まないよう、±2 Hz は中央値から除く。

    **なぜ局所か —— ここは一度間違えた**。最初は「ピーク / 探索範囲全体の
    中央値」(大域顕著さ)で書いた。狭い帯域で復調すると包絡線スペクトルは
    低周波に向かって単調に持ち上がる形になり、範囲全体の中央値が下がって
    **欠陥が 1 つも無い純雑音でも大域顕著さが 30 を超える**(§3 で実測)。
    局所中央値なら同じ null が 4 未満に収まる。両方printして残す。
    """
    sel = (freqs >= LOW) & (freqs <= HIGH)
    f = freqs[sel]
    m = magnitude[sel]
    i = int(np.argmax(m))
    fp = float(f[i])
    peak = float(m[i])
    glob = peak / float(np.median(m))
    near = (np.abs(f - fp) <= half_width) & (np.abs(f - fp) > 2.0)
    loc = peak / float(np.median(m[near])) if near.any() else float("nan")
    return fp, glob, loc


def _matches(found_hz, true_hz):
    """見つけたピークが真の欠陥周波数(またはその高調波)と一致するか。"""
    return any(abs(found_hz - h * true_hz) <= TOL_FRAC * h * true_hz for h in HARMONICS)


def _record(defect_hz, sigma, seed):
    """欠陥ありの記録を 1 本作る(衝撃列 + 白色雑音)。

    ``mode="impulse"`` は物理に近い側 —— 欠陥通過ごとに共振が叩かれて減衰する。
    ``mode="am"`` の厳密解析ケースと違い、**生スペクトルにも欠陥周波数の
    成分が少し出る**。ゼロ点を不当に弱くしないためにこちらを使う。
    """
    clean = A.synthesize_bearing_signal(RATE, DURATION, RESONANCE, defect_hz,
                                        mode="impulse", damping=DAMPING,
                                        noise_sigma=0.0)
    if sigma <= 0.0:
        return clean
    noise = np.random.default_rng(seed).standard_normal(clean.size)
    return clean + sigma * noise


def main():
    t_start = time.perf_counter()

    # ------------------------------------------------------------------ #
    # 1) 真値は幾何から —— 数表ではなく式                                  #
    # ------------------------------------------------------------------ #
    kin = A.bearing_defect_frequencies(**BEARING)
    n_el = BEARING["n_elements"]
    print("1) 欠陥周波数の真値(閉形式、%d rpm / 転動体 %d / d %.2f / D %.2f):"
          % (BEARING["rpm"], n_el, BEARING["element_diameter"],
             BEARING["pitch_diameter"]))
    print("   軸回転 f_r = %.6f Hz、比 d/D cos(a) = %.6f" % (kin["shaft_hz"], kin["ratio"]))
    for tag, key in (("FTF (保持器)", "ftf_hz"), ("BPFO(外輪)", "bpfo_hz"),
                     ("BPFI(内輪)", "bpfi_hz"), ("BSF (転動体)", "bsf_hz"),
                     ("2xBSF        ", "bsf_hz_2x")):
        print("     %s = %10.6f Hz" % (tag, kin[key]))
    id1 = kin["bpfo_hz"] + kin["bpfi_hz"] - n_el * kin["shaft_hz"]
    id2 = kin["bpfo_hz"] - n_el * kin["ftf_hz"]
    print("   恒等式の検算: BPFO+BPFI-N f_r = %.3e、BPFO-N FTF = %.3e"
          "(d と D の取り違えを即座に殺す)" % (id1, id2))
    assert id1 == 0.0 and id2 == 0.0

    # ------------------------------------------------------------------ #
    # 2) 仕込んだ周波数を包絡線が当て直せるか(3 欠陥タイプ)              #
    # ------------------------------------------------------------------ #
    resolution = 1.0 / DURATION
    print("\n2) 仕込んだ欠陥周波数 vs 包絡線スペクトルが読んだ周波数"
          "(sigma=0.5、帯域 %.0f-%.0f Hz、分解能 %.2f Hz):" % (BAND + (resolution,)))
    print("   %-7s %11s %11s %10s %8s   %s"
          % ("欠陥", "真値[Hz]", "読み[Hz]", "誤差[Hz]", "誤差[%]", "生スペクトルの最大ピーク"))
    for tag, true_hz in (("BPFO", kin["bpfo_hz"]), ("BPFI", kin["bpfi_hz"]),
                         ("2xBSF", kin["bsf_hz_2x"])):
        x = _record(true_hz, 0.5, seed=11)
        env = A.envelope_spectrum(x, RATE, BAND[0], BAND[1])
        fe, _, _ = _peak_and_prominence(env["freqs"], env["magnitude"])
        fr, amp = _raw_amplitude_spectrum(x, RATE)
        fr_peak, _, _ = _peak_and_prominence(fr, amp)
        err = fe - true_hz
        print("   %-7s %11.4f %11.4f %+10.4f %8.3f   %8.2f Hz (= %.2f 次高調波)"
              % (tag, true_hz, fe, err, 100.0 * abs(err) / true_hz,
                 fr_peak, fr_peak / true_hz))
        # 正しさの assert: 読み取りは分解能 1 bin 以内(高調波に落ちてもいない)
        assert abs(err) <= resolution, (tag, true_hz, fe)
        if tag == "BPFO" and figs.enabled():
            # 生と包絡線は**同じ振幅の単位**(どちらも 2/N 済み)なので重ねてよい。
            # 床は同じ高さで、峰の立ち方だけが違う —— それがこの節の主張。
            sel_r = (fr >= LOW) & (fr <= HIGH)
            ef = np.asarray(env["freqs"])
            em = np.asarray(env["magnitude"])
            sel_e = (ef >= LOW) & (ef <= HIGH)
            figs.save_plot("envelope_vs_raw",
                           [("生スペクトル(ゼロ点)", fr[sel_r], amp[sel_r]),
                            ("包絡線スペクトル", ef[sel_e], em[sel_e])],
                           xlabel="周波数 [Hz]", ylabel="片側振幅",
                           title="BPFO %.1f Hz を仕込んだ記録(sigma=0.5)" % true_hz,
                           caption="雑音の床は同じ高さ。包絡線だけが BPFO と"
                                   "その高調波に峰を立てる。")
    print("   -> 3 タイプとも 1 bin(%.2f Hz)以内。**生スペクトル側の最大ピークは"
          " 4 次高調波に立つことがある**" % resolution)
    print("      (衝撃列の基本波は 4 次より弱い。cepstrum が 4/f_d を返すのと同じ現象で、")
    print("       生スペクトルの最大値だけを読むと「欠陥周波数の 4 倍」を報告してしまう)")

    # ------------------------------------------------------------------ #
    # 3) ゼロ点 (b): 欠陥が無い記録は何を返すか -> 検出閾値               #
    # ------------------------------------------------------------------ #
    print("\n3) null(欠陥なし = 白色雑音のみ)で閾値を決める。"
          "20 本、帯域は 2 通り:")
    null_wide_g, null_wide_l, null_narrow_g, null_narrow_l = [], [], [], []
    for s in range(20):
        n = np.random.default_rng(200 + s).standard_normal(int(DURATION * RATE))
        env = A.envelope_spectrum(n, RATE, BAND[0], BAND[1])
        _, g, loc = _peak_and_prominence(env["freqs"], env["magnitude"])
        null_wide_g.append(g)
        null_wide_l.append(loc)
        sk = A.spectral_kurtosis(n, RATE, win=256)          # 狭い帯域を選ばせる
        env2 = A.envelope_spectrum(n, RATE, sk["band_lo"], sk["band_hi"])
        _, g2, l2 = _peak_and_prominence(env2["freqs"], env2["magnitude"])
        null_narrow_g.append(g2)
        null_narrow_l.append(l2)
    print("   帯域 2000-4000 Hz(幅 2000 Hz): 大域顕著さ 最大 %6.2f / 局所顕著さ 最大 %5.2f"
          % (max(null_wide_g), max(null_wide_l)))
    print("   SK が選んだ幅 200 Hz の帯域    : 大域顕著さ 最大 %6.2f / 局所顕著さ 最大 %5.2f"
          % (max(null_narrow_g), max(null_narrow_l)))
    print("   -> **欠陥が 1 つも無いのに大域顕著さは %.0f 倍**。狭帯域で復調した包絡線"
          % max(null_narrow_g))
    print("      スペクトルは低周波側が持ち上がる形なので、範囲全体の中央値が沈む。")
    print("      これは最初に自分が踏んだ罠で、閾値 5 なら null が全部「検出」になる。")
    print("      局所中央値に直すと null は %.2f までしか出ない。以後こちらを使う。"
          % max(max(null_wide_l), max(null_narrow_l)))
    assert max(null_narrow_g) > 10.0        # 罠が実在すること(この記録・この seed で)
    assert max(null_wide_l) < 5.0 and max(null_narrow_l) < 5.0
    threshold = 5.0
    print("   検出の判定条件 = 局所顕著さ >= %.1f かつ ピークが真値の高調波 1..4 と"
          " %.0f %% 以内で一致" % (threshold, 100 * TOL_FRAC))

    # ------------------------------------------------------------------ #
    # 4) SNR を振る —— 生スペクトル(ゼロ点 a)との差が本題                #
    # ------------------------------------------------------------------ #
    defect_hz = kin["bpfo_hz"]
    clean = _record(defect_hz, 0.0, seed=0)
    rms_clean = float(np.sqrt(np.mean(clean * clean)))
    n_trial = 10
    print("\n4) 雑音を上げていく(BPFO %.4f Hz、欠陥信号 RMS %.6f、各段 %d seed):"
          % (defect_hz, rms_clean, n_trial))
    print("   %6s %8s | %9s %9s | %9s %9s | %s"
          % ("sigma", "SNR[dB]", "生:検出", "生:顕著さ", "包絡:検出", "包絡:顕著さ", "包絡が読んだ周波数"))
    sweep = []
    for sigma in (0.05, 0.2, 0.5, 1.0, 1.5, 2.0, 3.0):
        snr_db = 20.0 * np.log10(rms_clean / sigma)
        raw_hit = env_hit = 0
        raw_p, env_p, env_f = [], [], []
        for s in range(n_trial):
            x = _record(defect_hz, sigma, seed=100 + s)
            fr, amp = _raw_amplitude_spectrum(x, RATE)
            f1, _, p1 = _peak_and_prominence(fr, amp)
            env = A.envelope_spectrum(x, RATE, BAND[0], BAND[1])
            f2, _, p2 = _peak_and_prominence(env["freqs"], env["magnitude"])
            raw_p.append(p1)
            env_p.append(p2)
            env_f.append(f2)
            raw_hit += int(_matches(f1, defect_hz) and p1 >= threshold)
            env_hit += int(_matches(f2, defect_hz) and p2 >= threshold)
        med_f = float(np.median(env_f))
        print("   %6.2f %+8.1f | %6d/%2d %9.1f | %6d/%2d %9.1f | %8.2f Hz%s"
              % (sigma, snr_db, raw_hit, n_trial, np.median(raw_p),
                 env_hit, n_trial, np.median(env_p), med_f,
                 "" if _matches(med_f, defect_hz) else "  <- 欠陥と無関係"))
        sweep.append((sigma, snr_db, raw_hit, env_hit))
        # 正しさの assert: 包絡線解析が生スペクトルを下回る段は 1 つも無いこと
        assert env_hit >= raw_hit, (sigma, raw_hit, env_hit)

    raw_last = [s for s in sweep if s[2] == n_trial]
    env_last = [s for s in sweep if s[3] == n_trial]
    raw_limit = raw_last[-1][1] if raw_last else float("nan")
    env_limit = env_last[-1][1] if env_last else float("nan")
    print("   検出限界(10/10 を保てた最も悪い SNR): 生 %+.1f dB / 包絡線 %+.1f dB"
          "  -> **%.1f dB 分の改善**" % (raw_limit, env_limit, raw_limit - env_limit))
    print("   どちらも落ちるのは sigma=%.1f(SNR %+.1f dB)。そこでは包絡線も"
          % (sweep[-2][0], sweep[-2][1]))
    print("   欠陥と無関係な周波数を返す —— 「常にピークを返す op」なので、"
          "顕著さを見ないと嘘を読む。")
    # 検出限界は「率が 10/10 から崩れる場所」なので、率そのものを横軸 SNR で描く。
    snr_axis = np.array([s[1] for s in sweep])
    figs.save_plot("detection_sweep",
                   [("生スペクトル(ゼロ点)", snr_axis, np.array([s[2] for s in sweep])),
                    ("包絡線スペクトル", snr_axis, np.array([s[3] for s in sweep]))],
                   xlabel="SNR [dB]", ylabel="検出数 / %d 試行" % n_trial,
                   title="検出限界 —— 崖の位置が %.1f dB ずれる" % (raw_limit - env_limit),
                   caption="どちらも最悪条件では 0 に落ちる。包絡線は万能ではなく、"
                           "崖が悪い SNR 側へ動くだけ。")
    assert env_limit < raw_limit                 # 包絡線が確かに下(悪い SNR)まで持つ
    assert sweep[0][2] == n_trial                # 生スペクトルも良条件では 10/10(ゼロ点は死んでいない)
    assert sweep[-1][3] == 0                     # 最悪条件では包絡線も落ちる(万能ではない)

    # ------------------------------------------------------------------ #
    # 5) 帯域を機械に選ばせる —— 選んだ帯域は共振に乗っているか            #
    # ------------------------------------------------------------------ #
    print("\n5) spectral_kurtosis による帯域選択(真の共振 %.0f Hz を診断側は知らない前提):"
          % RESONANCE)
    print("   %6s %5s %8s %9s %17s %7s %7s %11s %s"
          % ("sigma", "win", "枠[ms]", "最大SK", "選ばれた帯域[Hz]", "共振を", "帯域内", "包絡ピーク", "顕著さ"))
    print("   %6s %5s %8s %9s %17s %7s %7s %11s %s"
          % ("", "", "", "", "", "含むか", "の割合", "[Hz]", ""))
    sk_rows = []
    sk_table = []                       # 図用。print している表をそのまま持ち出す
    for sigma in (0.2, 1.0, 2.0):
        for win in (32, 64, 128, 256):
            x = _record(defect_hz, sigma, seed=3)
            sk = A.spectral_kurtosis(x, RATE, win=win)
            env = A.envelope_spectrum(x, RATE, sk["band_lo"], sk["band_hi"])
            fp, _, loc = _peak_and_prominence(env["freqs"], env["magnitude"])
            covers = sk["band_lo"] <= RESONANCE <= sk["band_hi"]
            ok = _matches(fp, defect_hz) and loc >= threshold
            print("   %6.2f %5d %8.2f %9.3f %7.0f-%-9.0f %7s %7.3f %11.2f %7.1f %s"
                  % (sigma, win, 1000.0 * sk["window_seconds"], sk["max_kurtosis"],
                     sk["band_lo"], sk["band_hi"], "はい" if covers else "いいえ",
                     env["band_fraction"], fp, loc, "OK" if ok else "NG"))
            sk_rows.append((sigma, win, covers, ok, env["band_fraction"], loc, fp))
            sk_table.append(["%.1f" % sigma, "%d" % win,
                             "%.2f" % (1000.0 * sk["window_seconds"]),
                             "%.0f-%.0f" % (sk["band_lo"], sk["band_hi"]),
                             "はい" if covers else "いいえ",
                             "%.3f" % env["band_fraction"],
                             "%.1f" % loc, "OK" if ok else "NG"])
    print("   衝撃の間隔 = 1/%.2f = %.2f ms。**枠がこれより長いと全部の枠に衝撃が 1 個ずつ"
          % (defect_hz, 1000.0 / defect_hz))
    print("   入り、その帯域は「定常」に見える** —— win=256(10 ms)がその失敗で、")
    print("   sigma によらず毎回 共振と無関係な狭い帯域を選ぶ(帯域内の割合が 0.1 前後 =")
    print("   記録の 1 割しかそこに無い、と返り値自身が言っている)。")
    win32 = [r for r in sk_rows if r[1] == 32]
    print("   逆に win=32(1.25 ms)は sigma %.1f まで共振を含む帯域を選び、"
          % max(r[0] for r in win32 if r[2]))
    print("   %d/%d で欠陥を当てた。**帯域選択は「当てる」より先に「枠長を衝撃間隔より"
          % (sum(r[3] for r in win32), len(win32)))
    print("   短く取る」で決まる**。win を振らずに 1 つの値で回すのは測定ではない。")
    assert all(r[2] for r in win32), "win=32 は 3 つの sigma すべてで共振帯を含むはず"
    assert not any(r[2] for r in sk_rows if r[1] == 256), "win=256 は共振を外し続けるはず"
    # 帯域内の割合は、共振を外した狭帯域を「顕著さだけ」で採らないための第 2 の指標
    bad_narrow = [r for r in sk_rows if r[1] == 256]
    print("   win=256 の帯域内割合 %.3f-%.3f に対し、win=32 は %.3f-%.3f。"
          % (min(r[4] for r in bad_narrow), max(r[4] for r in bad_narrow),
             min(r[4] for r in win32), max(r[4] for r in win32)))
    print("   顕著さと band_fraction を**両方**読めば、外した帯域は外したと分かる。")
    assert max(r[4] for r in bad_narrow) < min(r[4] for r in win32)

    # ------------------------------------------------------------------ #
    # 6) 正直な内訳                                                        #
    # ------------------------------------------------------------------ #
    print("\n6) 包絡線解析が生スペクトルを**上回らない**条件(探して、あった):")
    x = _record(defect_hz, 0.05, seed=100)
    fr, amp = _raw_amplitude_spectrum(x, RATE)
    f1, _, p1 = _peak_and_prominence(fr, amp)
    env = A.envelope_spectrum(x, RATE, BAND[0], BAND[1])
    f2, _, p2 = _peak_and_prominence(env["freqs"], env["magnitude"])
    print("   (a) SNR %+.1f dB(ほぼ無雑音)では生スペクトルも 10/10 で当てる。"
          % (20.0 * np.log10(rms_clean / 0.05)))
    print("       ただし読める周波数が違う: 生 %.2f Hz(%.0f 次高調波)/ 包絡線 %.2f Hz。"
          % (f1, f1 / defect_hz, f2))
    print("       「検出できた」だけを見ると同点、「何 Hz か」まで見ると差がつく。")
    bad_band = (200.0, 800.0)          # 共振の無い帯域(ここには何も無い)
    print("   (b) 帯域を外すと包絡線は生スペクトルに**負ける**。同じ記録を "
          "%.0f-%.0f Hz(共振の無い帯域)で復調した検出率:" % bad_band)
    print("       %6s %8s | %s" % ("sigma", "SNR[dB]", "正しい帯域 / 外した帯域 / 生スペクトル"))
    loser = None
    for sigma in (0.05, 0.2, 0.5, 1.0):
        good = bad = raw = 0
        frac = 0.0
        for s in range(n_trial):
            xs = _record(defect_hz, sigma, seed=100 + s)
            eg = A.envelope_spectrum(xs, RATE, BAND[0], BAND[1])
            fg, _, pg = _peak_and_prominence(eg["freqs"], eg["magnitude"])
            eb = A.envelope_spectrum(xs, RATE, bad_band[0], bad_band[1])
            fb, _, pb = _peak_and_prominence(eb["freqs"], eb["magnitude"])
            frr, ampr = _raw_amplitude_spectrum(xs, RATE)
            f1r, _, p1r = _peak_and_prominence(frr, ampr)
            good += int(_matches(fg, defect_hz) and pg >= threshold)
            bad += int(_matches(fb, defect_hz) and pb >= threshold)
            raw += int(_matches(f1r, defect_hz) and p1r >= threshold)
            frac = eb["band_fraction"]
        mark = ""
        if bad < raw:
            mark = "  <- 外した包絡線 < 生スペクトル(band_fraction %.3f)" % frac
            loser = (sigma, bad, raw)
        print("       %6.2f %+8.1f | %2d/%2d   %2d/%2d   %2d/%2d%s"
              % (sigma, 20.0 * np.log10(rms_clean / sigma), good, n_trial,
                 bad, n_trial, raw, n_trial, mark))
    print("       包絡線解析の性能は**帯域選択の性能そのもの**。帯域を外した包絡線は")
    print("       ゼロ点(生スペクトル)より悪い —— 「包絡線だから強い」ではない。")
    assert loser is not None, "外した帯域が生スペクトルに負ける段が 1 つも無い"
    print("   (c) この PoC の検出限界は合成モデル上の値。実機は滑り・複数共振・"
          "回転数変動があり、")
    print("       同じ SNR でもここまで持たない。ここで測ったのは"
          "「限界を測る手続きが動くこと」。")

    # ------------------------------------------------------------------ #
    # 想定と違ったこと(消さずに残す)                                      #
    # ------------------------------------------------------------------ #
    print("\n7) 想定と違ったこと:")
    print("   * 生スペクトルは思ったより強かった。衝撃列(mode='impulse')は AM と違い")
    print("     欠陥周波数の**族**を生スペクトルにも出す。ゼロ点を AM 信号で取っていたら")
    print("     生スペクトル振幅 4e-16 という「勝って当たり前」の比較になっていた。")
    print("   * その生スペクトルの最大ピークが基本波でなく 4 次高調波だったこと。")
    print("     周波数を当てる話と検出する話は別で、前者では包絡線が明確に上。")
    print("   * 純雑音が大域顕著さ 30 超を出したこと(§3)。閾値は null から決める、を")
    print("     手続きにしていなければ、この PoC 自体が偽陽性を出していた。")
    print("   * 「帯域を外せば必ず負ける」でもなかった(§6b の上 2 段)。衝撃は広帯域なので")
    print("     良 SNR では**どの帯域で復調しても**欠陥周波数が出る。負けるのは雑音が")
    print("     乗ってから —— 帯域選択の効きは SNR に依存し、単独では順位が決まらない。")

    elapsed = time.perf_counter() - t_start
    print("\n所要 %.2f s(assert していない = 環境依存の数字)。"
          "1 記録 %.0f サンプル / %.1f s。" % (elapsed, DURATION * RATE, DURATION))
    print("PASS: 欠陥周波数の閉形式に 1 bin 以内で戻り、検出限界は"
          " 生 %+.1f dB -> 包絡線 %+.1f dB" % (raw_limit, env_limit))
    return True


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
