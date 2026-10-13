---
id: sam-bond-voids
title: ハイブリッド接合のボイドを、超音波のエコーの明るさでなく位相で見つける(走査型音響顕微鏡の C スキャン・周波数の取引・POD)
title_en: Find hybrid-bond voids by the phase of the ultrasonic echo, not its brightness (scanning acoustic microscope C-scans, the frequency trade-off, POD)
category: 見つける
ops: [acoustic_material_table, acoustic_layer_stack, acoustic_interface_coefficients, pulse_echo_ascan, sam_cscan, echo_phase_polarity, sam_frequency_tradeoff]
examples: [poc_sam_hybrid_bonding_voids]
version: 0.6.1
---

# ハイブリッド接合のボイドを、超音波のエコーの明るさでなく位相で見つける(走査型音響顕微鏡の C スキャン・周波数の取引・POD)

## できること

貼り合わせた積層(Si のダイ + SiO2 と Cu パッドの接合層)を、水の中の集束探触子で上から 1 点ずつ測る走査型音響顕微鏡(SAM)を、層の物理から組み立てます。接合面の**空洞(ボイド)**は空気なので、そこで音響インピーダンスが約 4 万分の 1 に落ち、エコーが**反転**します。符号はボイドがビームより小さくても薄まりません。

- ★**材料の表と積層**。密度・縦波音速・Z = ρc・減衰 α0 f^n を、値ごとに出典と「確かめたか」の印つきで持ちます。確かめていない代表値(ポリイミド・エポキシ)は `allow_unverified=True` を言わない限り使えません。界面の係数は `R = (Z2 − Z1)/(Z2 + Z1)`、エネルギー保存 `R² + (Z1/Z2)T² = 1` を 1e-14 で満たし、符号が負になるのは Z が下がる界面だけです。
- ★**A スキャン**。層の伝達行列(垂直入射・縦波)と水の往復の伝搬・減衰で、広帯域パルスの RF を作ります。下から積み上げる Airy の再帰、時間領域で経路を 1 本ずつ数えた和、光学の薄膜の式(`thin_film_reflectance`、n ↔ Z)と 1e-12 で一致します。
- ★★**C スキャンと位相**。接合面の地図(ラベル = 積層の種類)を、周波数ごとのガウスの横 PSF(半値全幅 1.02 λ_w F#)でぼかしてゲートを掛け、振幅・位相・同相成分・従来の「1 点の符号」の像を返します。位相は接合面の**期待時刻**で、表面エコーに対して読みます。薄い Cu と SiO2 の層は ±90°(直交)、ボイドは 180° 付近(反転)。直交の背景に反転のエコーが**直角に**足されるので、小さなボイドは振幅をほとんど変えず、位相を使う量だけが動きます(9〜16 µm のボイドで振幅 0.4〜3.5σ に対し 3.0〜8.9σ)。
- ★**周波数の取引**。横分解能 ∝ 1/f と水の往復減衰 ∝ exp(−β f²) から、ボイドの信号を最大にする周波数を閉形式 `f* = (k/a)·sqrt(log2(1 + a² ln2/(β k²)))` で出します(減衰が f² でなければ数値で)。表面エコーの裾がゲートに入る下限(パルスが長すぎる)と、Si の縦波の臨界角で決まる F# の下限も返します。
- ★**POD**。C スキャンの検出量を `pod_ahat_fit` / `pod_from_ahat`(MIL-HDBK-1823A)に流して a90/95 を出せます。例では位相を使う検出が 150 MHz で 12.4 µm、振幅だけが 16.6 µm でした(同じ基準・同じ閾値の規則、合成)。「SAM のボイド検出に POD を当てた先行研究」は、私たちの検索(OpenAlex で "probability of detection" × "acoustic microscopy")では見つかりませんでした —— 新規性の主張ではなく、検索の結果です。

## What it does

Pulse-echo ultrasound in layered stacks and scanning-acoustic-microscope C-scans, built from first principles: a material table that carries a source and a verified flag per value (unverified placeholders are refused unless asked for), interface coefficients with the energy check R² + (Z1/Z2)T² = 1 and the sign flip exactly where Z drops, a normal-incidence longitudinal transfer-matrix A-scan with water path and power-law attenuation (checked against a bottom-up Airy recursion, a time-domain ray sum and the optical thin-film formula to 1e-12), and a focused C-scan with a per-frequency Gaussian lateral PSF (FWHM 1.02 λ_water F#) that returns amplitude, phase, in-phase and single-sample-polarity images. Phase is read at the expected time of the bond plane relative to the front-surface echo: thin Cu and SiO2 layers give quadrature echoes, voids are inverted, so a small void adds at right angles to the background and barely changes the amplitude. A closed-form optimal frequency balances lateral resolution against water attenuation, with the front-echo time floor and the critical-angle F-number floor alongside; C-scan statistics feed the existing POD operators.

## 向くところ / 向かないところ

- **1-D の平面波・垂直入射・縦波だけ**の層モデル + 周波数ごとのガウスの横 PSF です。横波へのモード変換、表面波、斜入射の角度スペクトル(V(z) 曲線)、水/Si 界面の屈折による収差(焦点ずれ・球面収差)は入っていません。開口が最初の固体の縦波の臨界角を超える F#(Si で 2.80 未満)は拒みます。
- ボイドは薄い空気の層です。部分的に接した界面(kissing bond。Baik & Thompson 1984 のばねモデル)、表面粗さ、層の厚さむらは入っていません —— kissing bond はボイドより見つけにくく、ここでの数字は楽観側です。
- 位相は期待時刻で読むので、ダイの厚さの誤差 δd は位相を `4π f0 δd / c` 回します(Si・200 MHz で 1 µm あたり 17°)。厚さが場所で変わる部品は、画素ごとに時刻を直してから読んでください(op はしていません)。
- 材料定数は読んだ公開資料の値か、そこから計算した値です。**Si の減衰は確かめた値が無いので 0**、成膜した SiO2 は溶融石英の値で代用しています。値そのものではなく関係(符号・保存則・比例則)に門を掛けています。
- 単一素子の集束探触子だけです。アレイ(全行列取得・TFM)のビームフォーマは持っていません。

## 最初の 1 本

```python
import numpy as np
import fullseye as fs

die = [("silicon", 100e-6)]                                      # 厚さ 100 µm の Si のダイ
S = {0: fs.ledger.acoustic_layer_stack(die + [("sio2", 1e-6), ("sio2", 1e-6)]),              # 誘電体
     1: fs.ledger.acoustic_layer_stack(die + [("sio2", 1e-6), ("air", 0.1e-6), ("sio2", 1e-6)])}  # ボイド
a = fs.ledger.pulse_echo_ascan(S[1], f0=150e6, water_path=1e-3)
print(fs.ledger.echo_phase_polarity(a, interface=2)["label"])     # 接合面のエコーは inverted

m = np.zeros((64, 64), dtype=np.int64)
yy, xx = np.mgrid[:64, :64]
m[(yy - 32) ** 2 + (xx - 32) ** 2 <= 8 ** 2] = 1                   # 直径 34 µm のボイド(画素 2 µm)
c = fs.ledger.sam_cscan(m, S, pixel_size=2e-6, f0=150e6, water_path=1e-3, gate_interface=2)
print("位相 %.0f°(中心)/ %.0f°(地)" % (np.degrees(c["phase"][32, 32]), np.degrees(c["phase"][2, 2])))
t = fs.ledger.sam_frequency_tradeoff(S[0], 10e-6, water_path=1e-3, interface=2)
print("10 µm のボイドの最適周波数 %.0f MHz(下限 %.0f MHz)" % (t["f_opt"] / 1e6, t["f_min_time"] / 1e6))
```

## 裏づけ

- op: `acoustic_material_table` / `acoustic_layer_stack` / `acoustic_interface_coefficients` / `pulse_echo_ascan` / `sam_cscan` / `echo_phase_polarity` / `sam_frequency_tradeoff`
- 例: [`poc_sam_hybrid_bonding_voids`](../../examples/poc_sam_hybrid_bonding_voids.py) —— Si 100 µm の下の接合面(SiO2 と Cu パッド、直径 40 µm・ピッチ 80 µm)に直径 5〜24 µm のボイド: 振幅の像では 12 個中 8 個が良品の明るさの範囲に隠れ、位相の像では 16 µm 以上のボイドがすべて反転と読まれ、良品は 26,724 画素中 1 画素。従来の「1 点の符号」は無傷の Cu パッドで 140〜400 MHz の間に 5 回転ぶ。POD の a90/95 は位相を使う検出で 12.4 / 13.9 / 57.6 µm、振幅だけで 16.6 / 19.3 / 101.6 µm(150 / 200 / 300 MHz)。
- 既存 op と組む: `pod_ahat_fit` / `pod_from_ahat` / `pod_false_call`(検出確率)・`matappear.thin_film_reflectance`(光学の薄膜の式、同じ形の答え合わせ)・`acoustics`(可聴域の 1-D 信号の道具。A スキャンの `rf` をそのまま渡せる)
- 先行(すべて抄録で確認、閉形式は自分で導いた): W. T. Thomson, *J. Appl. Phys.* 21, 1950 と M. J. S. Lowe, *IEEE TUFFC* 42(4), 1995(層の行列法); R. A. Lemons & C. F. Quate, *Appl. Phys. Lett.* 24, 1974(走査型音響顕微鏡); S. C. Hwang, 2013(位相反転による剥離の判定が装置・探触子・操作者で変わる、15〜75 MHz); J.-M. Baik & R. B. Thompson, *J. Nondestr. Eval.* 4, 1984(不完全な界面のばねモデル、未実装)。
