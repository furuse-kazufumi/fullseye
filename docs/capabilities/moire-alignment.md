---
id: moire-alignment
title: モアレで位置合わせ(ピッチの僅かに違う 2 枚の格子 → 縞の位相 → nm のずれ、差動と Talbot ギャップ)
title_en: Moiré alignment (two gratings of slightly different pitch, fringe phase, nanometre shift, differential pairs and the Talbot gap)
category: 測る
ops: [moire_magnification, moire_talbot_gap, moire_overlay_image, moire_phase, moire_phase_to_shift, moire_differential_shift, moire_mark_read, moire_phase_crlb]
examples: [poc_moire_alignment]
version: 0.6.1
inputs: [image2d]
pipeline: [moire_magnification, moire_mark_read, moire_phase_crlb]
alternatives: [moire_phase, moire_phase_to_shift, moire_differential_shift, moire_overlay_image, moire_talbot_gap, absolute_phase]
limits: 0.1 nm 級の数字は白色雑音だけの床(`moire_phase_crlb`、PoC で Monte-Carlo と比 1.00)。実機の精度(公表値 10〜30 nm)を決めるマークの非対称・ギャップと傾き・レジスト膜はモデルに無い。読みは格子 1 ピッチ(差動は p_m p_w / (p_m + p_w))で折り返す。
calibration: ずれの尺度は格子のピッチ(リソグラフィの寸法)で、カメラの倍率ではない —— 差動のマークならカメラの倍率 2 % の誤りは読みに入らない(PoC)。どちらの格子が動くかで拡大率が違う(ウェハ 50・マスク 51)ので取り違えると 2 % 狂う。
---

# モアレで位置合わせ(ピッチの僅かに違う 2 枚の格子 → 縞の位相 → nm のずれ、差動と Talbot ギャップ)

## できること

リソグラフィやナノインプリントでは、マスクとウェハを nm の精度で重ねます。マスク側にピッチ p_m、ウェハ側に僅かに違うピッチ p_w の格子を置くと、2 枚はカメラのぼけで見えなくても、重ねた像には周期 P = p_m p_w / |Δp| の縞(モアレ)が現れ、ウェハが δ 動くと縞は M = p_m / |Δp| 倍の距離を動きます(マスクが動くなら p_w / |Δp| 倍)。`moirealign` の 8 本はその設計・合成・読み取り・限界を受け持ちます。

設計は `moire_magnification`(周期・拡大率・捕捉範囲。周期は印刷の網点のモアレ `halftone_moire_period` と同じ式で照合)と `moire_talbot_gap`(近接ギャップでマスクの像がどれだけ・どちらの符号で残るか。伝搬は `angular_spectrum_propagate`)。合成は `moire_overlay_image`(単一の対・逆向きのピッチ差の 2 対・2 次元の 4 象限、ぼけと画素の積分は閉形式、照明の傾き・雑音・マーク全体の流れ)。読み取りは `moire_phase`(既知の周波数での最小二乗 = ロックイン、または Takeda の FFT 法で位相の地図を `phase_unwrap`)、`moire_phase_to_shift`(粗い値で次数を決めるのは `absolute_phase`)、`moire_differential_shift`(2 対の差で像の流れ・照明・カメラの倍率の誤りを消す)、`moire_mark_read`(測定像と基準像からマーク 1 枚を読む)。`moire_phase_crlb` は白色雑音の下での位相とずれの下限です。

PoC `poc_moire_alignment` は、拡大率(ウェハ 50・マスク 51)を像から測り返し、1 nm の階段を誤差 0.08 nm で読み、Monte-Carlo の標準偏差が下限と比 1.00 で一致し、差動が 300 nm の流れと照明の傾きを消すことを示します。比べ手(20 µm の線の相互相関 + 放物線補間)との差は内訳(偏りと偶然の誤差)に分けて出します。

## What it does

Eight ops in `moirealign` (category `moire_align` of `opsoptics`) for alignment by moiré: two gratings with slightly different pitches (mask p_m, wafer p_w) form fringes of period p_m p_w / |Δp| that move M = p_m / |Δp| times further than the wafer (p_w / |Δp| if the mask moves). Design (magnification, capture range, the Talbot effect of a proximity gap), a closed-form camera image of single, differential and four-quadrant marks, fringe phase by lock-in or Takeda's FFT method, phase to shift with order resolution, differential pairs that cancel drift, illumination and camera-scale errors, and the white-noise lower bound. The PoC measures both magnifications from images, reads 1 nm steps with 0.08 nm RMS, matches the lower bound with a ratio of 1.00, and breaks the gain over a cross-correlation baseline into its bias and random parts.

## 向くところ / 向かないところ

**向く**: 位置合わせのマークの設計(ピッチの差と拡大率・捕捉範囲・必要な画素数と雑音の見積り)、重ね合わせ(オーバーレイ)の読み取りの試作、差動の 2 対で何が消えて何が消えないかの確認、ギャップの Talbot 効果で縞が反転する距離の予測、カメラの分解能では見えない格子のずれを読む実験の下準備。

**向かない**: ★ここで出る 0.1 nm 級の数字は**白色雑音だけ**の床です。実際の位置合わせの精度(公表値 10〜30 nm)はマークの非対称(エッチ・CMP)、ギャップとウェハの傾き、レジストの膜、照明の斜入射などの系統誤差が決め、このモデルには入っていません。ギャップの影響はマスクの像の回折だけ(戻りの光路の回折・多重反射は無し)で、0/1 の格子に限ります。読みはずれが動いた格子のピッチ 1 つ分(差動は p_m p_w / (p_m + p_w))で折り返すので、粗い位置決めを別に持つ必要があります。

## 推奨パイプライン

`moire_magnification` → `moire_mark_read` → `moire_phase_crlb`

`moire_magnification` でピッチの差から縞の周期・拡大率・捕捉範囲を決め(どちらの格子が動くかを `moving=` で)→ 測定像と基準像(どちらも `image2d`、差動のマーク)を `moire_mark_read` に渡してずれ [nm] を読み → `moire_phase_crlb` でその条件(画素数・縞の振幅・雑音)の下限と比べる。単一の対の読みは `single_x_nm` にも出るが、マーク全体の流れ(PoC では 300 nm)を拡大率で割った分だけずれる。

## 代替

位相の地図そのものが要るなら `moire_phase`(ロックイン = 既知の周波数の最小二乗、または Takeda の FFT 法)→ `moire_phase_to_shift`(次数は粗い値と `absolute_phase` で決める)。2 対の位相を自分で持っているなら `moire_differential_shift`。撮る前の見積りとマークの合成は `moire_overlay_image`、近接ギャップで縞が反転する距離は `moire_talbot_gap`。

## 限界

- 白色雑音の床だけを扱う。1 nm の階段の誤差 RMS 0.08 nm(PoC)はこの床の数字で、実機の位置合わせの精度ではない。
- ギャップの影響はマスクの像の回折だけ(戻りの光路の回折・多重反射は無し)、格子は 0/1 に限る。Talbot の反転では読みが半周期跳ぶ(PoC の門)。
- 比べ手(相互相関 + 放物線補間)との差 91 倍の大半は放物線の偏りで、偶然の誤差だけなら 2.5 倍(PoC が内訳を門にしている)。
- 読みは 1 ピッチで折り返すので、粗い位置決めを別に持つ。

## 実寸校正

ずれは格子のピッチ p_m・p_w から決まる量で、画素の大きさ(`pixel_um`)は縞の周波数を探す手がかりにしか使わない。差動のマークでは、カメラの倍率を 2 % 誤っても読みに入らないことを PoC が確かめている。拡大率はウェハが動くとき p_m/|Δp|、マスクが動くとき p_w/|Δp|(PoC で 50.000 / 51.000 を像から測り返す)なので、どちらを動かすかを取り違えないこと。

## 最初の 1 本

```python
import moirealign as MA

# マスク 2.00 µm・ウェハ 2.04 µm: 縞の周期と拡大率
print(round(MA.moire_magnification(2.0, 2.04)["magnification"], 3))  # 50.0(ウェハが動く)

# 差動のマーク(上 = 対 A、下 = 対 B)を撮って、25 nm のずれを読む。マーク全体が 300 nm 流れても消える
ref = MA.moire_overlay_image(layout="differential", noise_sigma=0.01, seed=1)
img = MA.moire_overlay_image(layout="differential", shift_nm=25.0, drift_nm=300.0, noise_sigma=0.01, seed=2)
r = MA.moire_mark_read(img, ref, 0.5, 2.0, 2.04, "differential")
print(round(r["shift_x_nm"], 2), round(r["single_x_nm"], 2))        # 25.16 と 19.16(差動は雑音 0.1 nm 級、単一の対は 300/M = 6 nm ずれる)
```

走らせて見るなら `py -3.11 examples/poc_moire_alignment.py`(図は `FULLSEYE_FIGURE_DIR` を指定したとき)。
