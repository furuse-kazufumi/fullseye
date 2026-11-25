# Ginza v2 stage 2 operator PoC

## Claim / 主張

Explicit camera/BEV calibration plus classical polynomial and colour/contour rules can
recover a gentle-lane centre and signed curvature and can separate three supported Japanese
sign appearances without treating a red octagon as a Japanese stop sign. The useful claim is
limited to the independently generated holdout family below: blur, residual perspective,
flare, missing paint, and sign weathering have measured breakdown curves and are not hidden
behind the aggregate.

カメラ・BEV較正を明示し、古典的な多項式当てはめと色・輪郭規則だけを使うことで、
緩いカーブの車線中央・符号つき曲率と、日本式標識3種の外観を読める。ただし主張は、
下記の独立holdout族で測った範囲に限る。ぼけ、透視残差、フレア、白線欠損、標識劣化は
一軸ずつ強めた破綻曲線を出し、集計値の陰へ隠さない。

## Independent scene families / 独立な場面族

seedだけを変えた分割ではない。次の生成設定は調整用とholdoutで重ならない。

| 分離軸 | tuning | holdout |
|---|---|---|
| 道の曲がり | 二次係数 `|q|=0.0007..0.0022`、三次項0 | `|q|=0.0028..0.0045`、逆向き三次項 `|c|=1e-6..4e-6` |
| 隠れの形・数・位置 | 前方7–12 mの長方形を0個または1個 | 前方18–28 mの楕円を1–3個 |
| 照明 | 水平影だけ | 斜め影、放射状逆光、色つき放射照明 |
| 標識の順 | `stop, speed, no-entry, octagon, upright, damaged, low-saturation, blank` | 別順列を8件ごとに3位置回転 |
| 合成劣化の通常範囲 | 車線0.005–0.025、標識0.01–0.04 | 車線0.03–0.065、標識0.05–0.10 |

holdoutの真値は画像を作る前の解析曲線・場面metadataにだけ置き、opへはRGB、BEV対応、
輪郭だけを渡す。学習済み重み、semantic画像、地図、真値ラベルは渡さない。

## Realism envelope and sources / 現実味の範囲と出典の型

公開データはカメラの光子数・読み出し雑音や個々のJPEG品質を公開していない。したがって
下の数値はセンサ較正値ではなく、公開画像に見えるclean側から破綻側を画像空間で囲んだ
`practitioner` envelopeである。カテゴリ件数・収集条件は一次論文で確認した。推測値を
`verified`と呼ばない。

- 車線の場面型は[CULaneの一次論文表](https://openaccess.thecvf.com/content_ICCV_2019/papers/Hou_Learning_Lightweight_Lane_Detection_CNNs_by_Self_Attention_Distillation_ICCV_2019_paper.pdf)による。133,235 frameで、test側にno-line 11.7%、shadow 2.7%、dazzle-light 1.4%、curve 1.2%がある。
- 天候・時間帯・場面の幅は[BDD100K一次論文](https://openaccess.thecvf.com/content_CVPR_2020/papers/Yu_BDD100K_A_Diverse_Driving_Dataset_for_Heterogeneous_Multitask_Learning_CVPR_2020_paper.pdf)のcrowd-sourced dashcam 100,000 videoを場面型の根拠にした。
- 標識の天候・照明・地域差は[Mapillary Traffic Sign Dataset一次論文](https://www.ecva.net/papers/eccv_2020/papers_ECCV/papers/123680069.pdf)のstreet-level 105,000 imageを場面型の根拠にした。

| 独立に掃引する軸 | severity 0→1の画像空間範囲 |
|---|---|
| 焦点ぼけ | Gaussian `sigma=0..2.8 px` |
| 動きぼけ | 対角kernel `1..15 px` |
| 透視残差 | 四隅変位 `0..14 px` |
| ショット＋読み出し雑音 | 白100%当たり `1600..40 photons`相当、読み出し `0..0.030` |
| JPEG | quality `96..30`、4:2:0 |
| 逆光フレア | veiling luminance `0..0.70` |
| 路面 | 汚れ被覆 `0..0.30`、白線contrast loss `0..0.85`、欠損長率 `0..0.65` |
| 標識 | 汚れ被覆 `0..0.35`、bbox隠れ率 `0..0.45`、彩度損失 `0..0.85` |

## Quality gates / 質の門

| 観点 | 門 | 実測・判定方法 |
|---|---|---|
| 何を見せるか | 車線・標識の入力→出力→解析真値を同じ画面に置く | `01_first`、`02_middle`、`03_last`を原寸確認 |
| 壊れる側 | 各劣化軸の曲線と失敗入力を出す | `05`–`08`。標識はtruth `no_entry`→`unknown`、車線は0.481 mを表示 |
| 形 | 330-Aは一辺0.80 m、323/303は直径0.60 mを基準に合成 | 点列からの復元誤差 `<1e-12 m`をassert |
| 物理 | `v^2 |kappa| <= 2.5 m/s²` | 全有効曲率標本でassert、full最大2.5000000000000004 |
| 数字 | 図・JSON・この表を同じ実行にする | `post_review_metrics_365_final/final_2.json`の集計が一致 |
| 尺度 | RGB 0..1、曲線図の軸範囲固定 | 車線誤差0–0.45 m、F1/有効率0–1.05 |
| 解像度 | 1280×960以上、データ面の最近傍拡大なし | 下記8 PNGの寸法を実測 |
| 文字 | ja/en、データ外の帯、1080p換算22 px以上 | grid最小30 px、contact 22.8 px、plot legend 22 px |
| 体裁 | `examplefig.save_grid/save_plot` | 実装と8 PNGを確認 |
| 決定性 | 同じseedで2回描画しSHA-256一致 | `inspection_review_365_final/final_2`の8/8一致 |
| 標本 | fullはlane 12+20、sign 32+40。全件JSON | 実測。breakdownはlane 6、sign 40×5段階/軸 |
| 受入値 | 中心p95 ≤0.30 m、macro F1 ≥0.90、横加速度 ≤2.5 m/s² | full holdoutは0.1067、0.9279、2.5000 |
| 再生成 | `tools/regen_all.py --check` | commit前に実行 |
| 検分用出力 | first/middle/last/contactと破綻図をrepo外へ書く | 絶対パスを下記に記録 |
| 時間の門 | PoC単体timeoutはfull最長の2倍以上 | full 92.39/92.48 s、CI 6.62 s。下限240 s |

## Measured result / 実測結果

2026-11-25、同一checkoutで測った。レビュー前の値も、この修正直前にfullを再実行して
`pre_review_metrics_365.json`へ保存した値であり、記憶から写していない。

| full holdout | lane有効/件数 | 中心p95 / 最大 [m] | 曲率p95 / 最大 [1/m] | 標識正解/件数 | macro F1 | 横加速度最大 [m/s²] |
|---|---:|---:|---:|---:|---:|---:|
| review前 | 20/20 | 0.003096 / 0.008670 | 0.00003749 / 0.00004471 | 40/40 | 1.000000 | 2.500000 |
| review後 | 20/20 | 0.106704 / 0.477989 | 0.00146094 / 0.00224603 | 38/40 | 0.927885 | 2.5000000000000004 |

| run | lane有効/件数 / 点 | 標識正解/件数 | 中心p95 [m] | 曲率p95 [1/m] | macro F1 |
|---|---:|---:|---:|---:|---:|
| full tuning | 12/12 / 972 | 32/32 | 0.003561 | 0.00009904 | 1.000000 |
| full holdout | 20/20 / 1620 | 38/40 | 0.106704 | 0.00146094 | 0.927885 |
| CI tuning | 3/3 / 243 | 8/8 | 0.002172 | 0.00001746 | 1.000000 |
| CI holdout | 4/4 / 324 | 15/16 | 0.035485 | 0.00027778 | 0.904762 |

標識の2誤りはいずれも劣化した`no_entry`を`unknown`へ棄却したもの。誤った規制種へ
分類してはいないが、macro F1では失敗として数えた。full holdoutの中心最大0.478 mは
0.30 m線を越える個別例であり、p95合格だけで隠さず最大値も残す。

## Breakdown / 段階的な破綻

severityは`0, 0.25, 0.50, 0.75, 1.00`。車線のgateは全件有効かつ中心p95 ≤0.30 m、
標識はmacro F1 ≥0.90。「範囲内なし」はseverity 1でもgateを割らなかった意味で、
現実世界全般に頑健という意味ではない。

| 車線軸 | 最初のgate失敗 | severity 1の中心p95 [m] / 有効率 |
|---|---:|---:|
| focus blur | 1.00 | 0.0318 / 0.50 |
| motion blur | 0.50 | 0.2416 / 0.17 |
| perspective | 1.00 | 0.3799 / 1.00 |
| shot + read noise | 0.50 | 0.0125 / 0.83 |
| JPEG | 範囲内なし | 0.0086 / 1.00 |
| flare | 範囲内なし | 0.2181 / 1.00 |
| road dirt | 範囲内なし | 0.0033 / 1.00 |
| line fade | 1.00 | 0.0110 / 0.17 |
| line missing | 範囲内なし | 0.0038 / 1.00 |

| 標識軸 | 最初のgate失敗 | severity 1のmacro F1 |
|---|---:|---:|
| focus blur | 0.50 | 0.344 |
| motion blur | 0.25 | 0.344 |
| perspective | 範囲内なし | 0.967 |
| shot + read noise | 範囲内なし | 0.967 |
| JPEG | 範囲内なし | 1.000 |
| flare | 範囲内なし | 1.000 |
| sign dirt | 範囲内なし | 0.935 |
| sign occlusion | 1.00 | 0.808 |
| sign fade | 1.00 | 0.192 |

## Figures and reproducibility / 図と再現性

検分用出力はrepo外の
`C:\dev\data\ginza_v2_stage2_ops_2026_11_24\inspection_review_365_final` と
`C:\dev\data\ginza_v2_stage2_ops_2026_11_24\inspection_review_365_final_2`。2回の
集計JSONと8 PNGは一致した。

| file | pixels | SHA-256（2回一致） |
|---|---:|---|
| `01_first.png` | 1840×974 | `37B403E406B7C3DBD68680AD53258810BC17FF4CA102185A3224B7F3CF0B4A6D` |
| `02_middle.png` | 1840×974 | `82B29D640FA9951787F743758A121531AE259B611E12F08F3287103D78F45F94` |
| `03_last.png` | 1840×974 | `BDE6E7CDD07E3D01A0FD7E7794BAD944A734E447B987C9D9BFDE1E2ABCDEBF6A` |
| `04_contact_sheet.png` | 1840×1420 | `D1E3F20452F50C26FF17873308410D873CD0772C15F0A4B00A8CDE0EC1AEC02B` |
| `05_breakdown_lane_error.png` | 2290×1080 | `2D30BA0FD1E1EF0198B227327A82B1D0A3461C3242C77E23FB611485378B7E09` |
| `06_breakdown_lane_valid.png` | 2000×1080 | `B9F895A2C35326A3E793846FC3311C83C4D6E0D3C6080F797B3B63E3D3BE73B0` |
| `07_breakdown_sign_f1.png` | 2000×1080 | `E548A2249825AD124FC7191AB283D369684B8CAF5651174E8279D2891D702466` |
| `08_breakdown_failure.png` | 1840×974 | `40C9CDE48DA5344782CD931294FDF7AC37A3C76AA635C4685FB3315C71C21B9D` |

## Run / 実行

```powershell
$env:PYTHONPATH = 'C:\dev\projects\imgevolve_wt_ginza-stage2'
$env:FULLSEYE_FIGURE_DIR = 'C:\dev\data\ginza_v2_stage2_ops_2026_11_24\inspection_review_365'
py -3.11 examples/poc_ginza_stage2_ops.py --metrics C:\dev\data\ginza_v2_stage2_ops_2026_11_24\metrics.json
$env:FULLSEYE_FIGURE_DIR = $null
$env:CI = '1'
py -3.11 examples/poc_ginza_stage2_ops.py
```

`FULLSEYE_FIGURE_DIR`を指定しない場合は図を書かない。調整用・holdoutの全件、分離した
場面族、出典の型、劣化範囲、全breakdown点は標準出力へ出し、`--metrics`では同じ内容を
UTF-8 JSONへ保存する。
