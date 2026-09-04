---
guide: mv_image_sensors
dim: optics
title: イメージセンサの知識 — EMVA1288 と型番の読み方
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0
applies_to: optics/imaging_sim, optics/scene, 2d/noise
---

<!-- fullseye guide: 機械視覚の周辺知識。op ではなく、op に渡す値の
     出どころを示す教材。関連 op: sensor_spec / sensor_catalog / optical_budget -->

# 産業用イメージセンサ（現行品中心）

カメラは、ピクセルシフトや TDI を使わない限り**ほぼイメージセンサでスペックが決まる**。
接続インターフェース（USB3 Vision / GigE Vision / CoaXPress / 10GigE）が変えるのは
主にフレームレートと ROI の制約であって、画質そのものではない。したがって仮想化で
与えるべきパラメータは、カメラ型番ではなく**センサの諸元**である。

出典: Basler「CMOS sensor selection」（世代・画素・解像度・シャッタ・フレームレート）。
飽和容量・読み出し雑音・QE の実数は Basler 等の **EMVA1288 レポート**か Sony の
データシートにしか無く、一般公開ページには載らない（下表で「非公開」と明記する）。

## メーカー

イメージセンサを作るメーカーは多くない。産業用で実際に選択肢になるのは:

| メーカー | 産業用ライン | 位置づけ |
| --- | --- | --- |
| Sony Semiconductor | Pregius / Pregius S / STARVIS 2 | 事実上の標準。グローバルシャッタの主流 |
| onsemi | XGS / PYTHON | 大判・高速。XGS は 3.2 µm 世代 |
| Gpixel | GMAX / GSPRINT / GSENSE | 高解像度・高速。中判以上で強い |
| Teledyne e2v | Emerald / Sapphire | 低ノイズ・高感度。宇宙/科学寄りも |
| OmniVision | OG / OS 系 | 車載・組込寄り |

## 産業用センサ 38 型 — EMVA1288 実測つき（5 メーカー横並び）

出典は Basler のカメラ実測表なので、**ここに載っているのはカメラ側の値**である。

* **解像度**はそのカメラが出す画素数。メーカーは端を切って**センサ全有効画素より
  少し低く**することがあるので、センサ単体の仕様とは一致しないことがある。
* **フレームレート**は接続インターフェース（USB3 Vision / GigE / 5GigE / CXP-12）で
  変わる。センサの属性ではないので、この表には入れない。
* **QE / ダークノイズ / 飽和容量 / ダイナミックレンジ**は EMVA1288 実測（ace /
  ace 2 / boost）で、実装込みの値。別のカメラなら少し変わる。
* **画素ピッチ・シャッタ方式・世代**はセンサ由来なので、カメラが変わっても動かない。

### Sony

| 型番 | 系列 | 解像度 | 画素 [µm] | シャッタ | QE | 雑音 [e-] | 飽和 [ke-] | DR [dB] | 状態 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| IMX530 | Pregius S 4th | 24.6 MP / 5328×4608 | 2.74 | global | 66% | 2 | 9.6 | 71 | current |
| IMX540 | Pregius S 4th | 24.6 MP / 5328×4608 | 2.74 | global | 66% | 2 | 9.7 | 71 | current |
| IMX541 | Pregius S 4th | 20.3 MP / 4504×4504 | 2.74 | global | 66% | 2 | 9.7 | 71 | current |
| IMX183 | STARVIS | 20.0 MP / 5472×3648 | 2.40 | rolling | 75% | 3 | 13.8 | 71 | mature |
| IMX542 | Pregius S 4th | 16.1 MP / 5320×3032 | 2.74 | global | 66% | 2 | 9.7 | 71 | current |
| IMX304 | Pregius 2nd | 12.3 MP / 4096×3000 | 3.45 | global | 69% | 2 | 10.2 | 73 | mature |
| IMX545 | Pregius S 4th | 12.3 MP / 4096×3000 | 2.74 | global | 67% | 3 | 9.9 | 70 | current |
| IMX226 | STARVIS | 12.2 MP / 4024×3036 | 1.85 | rolling | 83% | 3 | 11.0 | 70 | mature |
| IMX267 | Pregius 2nd | 8.8 MP / 4096×2160 | 3.45 | global | 69% | 2 | 10.2 | 73 | mature |
| IMX546 | Pregius S 4th | 8.1 MP / 2840×2840 | 2.74 | global | 66% | 2 | 9.8 | 70 | current |
| IMX178 | STARVIS | 6.4 MP / 3088×2064 | 2.40 | rolling | 81% | 3 | 14.3 | 73 | mature |
| IMX264 | Pregius 2nd | 5.0 MP / 2448×2048 | 3.45 | global | 68% | 2 | 10.4 | 73 | mature |
| IMX252 | Pregius 2nd | 3.1 MP / 2048×1536 | 3.45 | global | 69% | 2 | 10.5 | 73 | mature |
| IMX265 | Pregius 2nd | 3.1 MP / 2048×1536 | 3.45 | global | 68% | 2 | 10.5 | 73 | mature |
| IMX174 | Pregius 1st | 2.3 MP / 1920×1200 | 5.86 | global | 70% | 7 | 31.8 | 74 | legacy |
| IMX249 | Pregius 1st | 2.3 MP / 1920×1200 | 5.86 | global | 70% | 7 | 31.9 | 74 | legacy |
| IMX392 | Pregius 2nd | 2.3 MP / 1920×1200 | 3.45 | global | 62% | 3 | 10.5 | 72 | mature |
| IMX273 | Pregius 2nd | 1.6 MP / 1440×1080 | 3.45 | global | 63% | 3 | 10.5 | 71 | mature |
| IMX287 | Pregius 2nd | 0.4 MP / 720×540 | 6.90 | global | 63% | 7 | 21.0 | 74 | mature |

### onsemi

| 型番 | 系列 | 解像度 | 画素 [µm] | シャッタ | QE | 雑音 [e-] | 飽和 [ke-] | DR [dB] | 状態 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| XGS 45000 | onsemi XGS | 44.7 MP / 8192×5460 | 3.20 | global | 55% | 5 | 9.0 | 65 | current |
| XGS 32000 | onsemi XGS | 32.5 MP / 6580×4935 | 3.20 | global | 56% | 4 | 9.3 | 66 | current |
| XGS 20000 | onsemi XGS | 20.2 MP / 4500×4500 | 3.20 | global | 55% | 4 | 9.2 | 66 | current |
| MT9J003 | onsemi | 10.6 MP / 3840×2748 | 1.67 | rolling | 46% | 6 | 2.8 | 54 | legacy |
| PYTHON 5000 | onsemi PYTHON | 5.3 MP / 2590×2048 | 4.80 | global | 55% | 12 | 8.2 | 57 | mature |
| PYTHON 2000 | onsemi PYTHON | 2.3 MP / 1920×1200 | 4.80 | global | 54% | 11 | 7.8 | 57 | mature |
| PYTHON 1300 | onsemi PYTHON | 1.3 MP / 1280×1024 | 4.80 | global | 53% | 11 | 6.9 | 56 | mature |
| PYTHON 500 | onsemi PYTHON | 0.5 MP / 800×600 | 4.80 | global | 54% | 11 | 7.8 | 57 | mature |
| PYTHON 300 | onsemi PYTHON | 0.3 MP / 640×480 | 4.80 | global | 52% | 11 | 7.1 | 57 | mature |

### Gpixel

| 型番 | 系列 | 解像度 | 画素 [µm] | シャッタ | QE | 雑音 [e-] | 飽和 [ke-] | DR [dB] | 状態 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GMAX3265 | Gpixel GMAX | 65.4 MP / 9344×7000 | 3.20 | global | 52% | 8 | 10.4 | 61 | current |
| GMAX0505 | Gpixel GMAX | 26.2 MP / 5120×5120 | 2.50 | global | 51% | 4 | 4.3 | 60 | current |
| GMAX2518 | Gpixel GMAX | 18.5 MP / 4508×4096 | 2.50 | global | 56% | 3 | 6.7 | 66 | current |
| GMAX2509 | Gpixel GMAX | 9.1 MP / 4200×2160 | 2.50 | global | 53% | 1 | 4.6 | 69 | current |
| GMAX2505 | Gpixel GMAX | 5.6 MP / 2600×2160 | 2.50 | global | 53% | 1 | 4.8 | 70 | current |

### ams

| 型番 | 系列 | 解像度 | 画素 [µm] | シャッタ | QE | 雑音 [e-] | 飽和 [ke-] | DR [dB] | 状態 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CMV12000 | ams CMV | 12.6 MP / 4096×3072 | 5.50 | global | 45% | 14 | 11.6 | 59 | mature |
| CMV4000 | ams CMV | 4.2 MP / 2048×2048 | 5.50 | global | 62% | 14 | 11.9 | 59 | mature |
| CMV2000 | ams CMV | 2.2 MP / 2048×1088 | 5.50 | global | 63% | 14 | 9.3 | 57 | mature |

### Teledyne

| 型番 | 系列 | 解像度 | 画素 [µm] | シャッタ | QE | 雑音 [e-] | 飽和 [ke-] | DR [dB] | 状態 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EV76C570 | Teledyne e2v | 1.9 MP / 1602×1202 | 4.50 | switchable | 47% | 22 | 6.8 | 50 | legacy |
| EV76C661 | Teledyne e2v NIR | 1.3 MP / 1280×1024 | 5.30 | switchable | 59% | 23 | 7.4 | 50 | legacy |

### メーカーごとの立ち位置（同じ測定法で比べた結果）

* **Sony Pregius / Pregius S** — バランスの基準。QE 62-70%、雑音 2-3 e-、飽和 9.6-10.5 ke-。
  1st（5.86 µm）だけ飽和 31.8 ke- と別格で、ダイナミックレンジ重視なら今も候補。
* **onsemi XGS**（3.2 µm）— **APS-C / 35 mm の大判**が本領。44.7 MP（8192×5460）まであり、
  この判は Sony に無い。QE 55-57%、雑音 4-5 e-。
* **onsemi PYTHON**（4.8 µm）— 小型・高速。ただし**雑音 11-12 e- は Pregius の 5 倍**で、
  暗い場面・暗視野では効いてくる。DR も 56-57 dB と低め。
* **Gpixel GMAX**（2.5 µm）— **雑音 1 e- 級**（GMAX2505 / 2509）が売り。飽和は 4-5 ke- と
  小さいので DR は 69-70 dB で Sony とほぼ同等になる。**65 MP（9344×7000）の
  GMAX3265** は超高解像度の選択肢がここしかない。
* **ams CMV**（5.5 µm、旧 CMOSIS）— 飽和 9-12 ke- だが**雑音 14 e-**。DR 57-59 dB。
* **Teledyne e2v EV76**（切替シャッタ）— 雑音 22-23 e-、DR 50 dB。NIR 強化版がある。

**選び方の含意**: 「画素が小さい＝不利」ではない。GMAX2505（2.5 µm・雑音 1 e-）は
DR 70 dB で Pregius S（2.74 µm・雑音 2 e-・71 dB）と並ぶ。効くのは**画素サイズ単体
ではなく飽和容量と雑音の比**で、暗視野のように信号が小さい用途では雑音が支配する。

## 自社でセンサを作っているカメラメーカー（型番から引けない）

上の表は「センサを買ってカメラを作る」メーカー（Basler / FLIR / IDS / Baumer /
Allied Vision / JAI …）の話である。**自社でセンサを設計・製造しているカメラメーカー**は
構造が違い、センサ型番から諸元を引くことができない。**カメラのデータシートが唯一の
出所**になるので、1 社ずつ個別に当たる必要がある。

| メーカー | センサ | 押さえ方 |
| --- | --- | --- |
| **Canon** | 2000 年から自社 CMOS を製造。**自社製品専用**で外販しない | 産業/医療/科学向けカメラのデータシート。画素レベルの独自構造が性能の根拠 |
| **Teledyne DALSA / e2v** | センサもカメラも自社（Teledyne Vision Solutions）。Emerald / Sapphire / Xineos、ラインスキャンの TDI | センサ単体も売っているので、両方のデータシートが引ける（例外的に楽） |
| **Photron** | FASTCAM SA-Z などに自社 CMOS。Mini 4K は自社 4096×2304 | 高速カメラのデータシート。フレームレートと画素数のトレードオフが主要諸元 |
| **Vision Research（Phantom）** | 自社設計のカスタム CMOS。v1211/v1611/v2011/v2511 系は **28 µm 画素**（感度重視）。TMX 系は裏面照射のカスタム | カメラのデータシート。画素が桁違いに大きいので、飽和容量と感度の前提が上表と全く違う |
| **Hamamatsu** | ORCA 系。**自社と外部の混在**（ORCA-Quest は Fairchild Imaging 開発のセンサを搭載）| 機種ごとに確認が要る。qCMOS など光子数分解の系統は別枠 |
| **Sony** | センサもカメラも作る（XCG 等）| センサ側の資料が引けるので上表と同じ扱いでよい |

**仮想化への含意**: 28 µm 画素（Phantom）と 2.74 µm 画素（Pregius S）では、飽和容量も
回折律速に入る F 値も一桁違う。`optical_budget` の「回折 1.22λN_w 対 標本化 2p」の
境目は画素ピッチで決まるので、**自社センサ機を想定するなら画素ピッチを実機の値で
与えないと、結論が逆になる**。

## Sony STARVIS 2（ローリング／一部グローバル、低照度）

IMX675 / IMX678 など。低照度でのダイナミックレンジが売り。外観検査では
グローバルシャッタが要る場面が多いので主役ではないが、暗視野や低照度の用途では候補。

## 一般公開されていない値（datasheet / EMVA1288 が要る）

以下は仮想化に**必須**だが、上の表の出典には無い:

* 飽和容量（full well capacity）[e⁻]
* 時間ダークノイズ / 読み出し雑音 [e⁻]
* 量子効率 QE(λ) [%]（分光感度曲線）
* 暗電流 [e⁻/s]、その温度依存
* 変換ゲイン [e⁻/DN]、ADC ビット深度
* PRNU / DSNU（画素間ばらつき）

上表の QE / ダークノイズ / 飽和容量 / DR は Basler の EMVA1288 実測で埋めた。
残る未取得は **暗電流の温度依存・変換ゲイン・PRNU / DSNU・分光感度曲線 QE(λ)** で、
これらは Sony のデータシート（NDA 相当）か、各社の EMVA1288 詳細レポートが要る。
`optscene.sensor_spec(model=...)` は埋まっている値を使い、戻り値の
`noise_values_are` に出所（EMVA1288 かユーザー指定か）を残す。

## 3.45 µm 画素が効いてくる場面（実装との接続）

`optical_budget` の分解限界は「回折 1.22λN_w と 標本化 2p の大きい方」。
画素 3.45 µm・550 nm なら、作動 F 値 N_w が **約 5.1 を超えたところで回折律速**に
変わる（1.22 × 0.55 × 5.1 ≈ 3.4 µm ≈ p）。つまり 3.45 µm 世代では F5.6 より絞ると
解像度は上がらず、被写界深度だけが伸びる。Pregius S の 2.74 µm ではこの境目が
F4 付近へ下がる。**画素ピッチを変えたら絞りの上限も変わる**、が設計上の帰結。
