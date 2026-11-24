# Ginza v2 stage 2 operator PoC

## Claim / 主張

Explicit camera/BEV calibration plus classical polynomial and colour/contour rules can recover a gentle-lane centre and curvature, and can separate the three supported Japanese sign appearances without treating a red octagon as a Japanese stop sign.

カメラ・BEV較正を明示的に与え、古典的な多項式当てはめと色・輪郭規則だけを使うことで、緩いカーブの車線中央と曲率を復元し、赤い八角形を日本の一時停止と誤認せずに、対象とする日本式標識3種の外観を分類する。

## Quality gates / 質の門

| 観点 | 門 | 判定方法 |
|---|---|---|
| 何を見せるか | 合成RGB入力、白・黄のBEV点、推定中心線・真値、標識入力・分類・真値を同じ図に置く | full run の図を原寸確認 |
| 壊れる側 | 赤い八角形、欠けた輪郭、低彩度・白飛びを含め、`unknown` または非日本式として棄却する | holdout の全件表と図 |
| 形 | 一時停止は別表第二の一辺80 cmの逆三角形、最高速度候補と車両進入禁止は直径60 cmの円を基準に合成する | 合成器の座標とe-Gov図示寸法をassert |
| 物理 | 曲率からの速度上限で `v^2 |kappa| <= a_lat_max` | 全曲率標本でassert |
| 数字 | 図の中心誤差p95・曲率誤差・macro F1は同じ実行のJSONと一致する | 描画直前にassert |
| 尺度 | RGBは0..1、誤差図の範囲は全シナリオで固定 | 描画引数を検査 |
| 解像度 | 1280×960以上。データ面を最近傍拡大しない | 出力PNGを実測 |
| 文字 | 日本語・英語、データ外のcaption帯、1080p換算22 px以上 | 原寸確認 |
| 体裁 | `examplefig.save_grid` を使う | 実装を検査 |
| 決定性 | 同じseedで2回描画しSHA-256一致 | full run後に実測 |
| 標本 | 調整用とholdoutをシナリオ単位で分離し、全件をJSONへ出す | 件数とseedを記録 |
| 受入値 | 中心誤差p95 ≤ 0.30 m、holdout標識macro F1 ≥ 0.90 | design.mdの段階2ゲートと比較 |
| 再生成 | `tools/regen_all.py` と `--check` が成功 | commit前に実行 |
| 検分用出力 | first / middle / last / contact sheetをrepo外へ書く | 絶対パスを報告 |
| 時間の門 | full/CIの実測時間からテストtimeoutを決める | 実測値を報告 |

## Measured result / 実測結果

2026-11-25に同一checkoutから実行した。full runは調整用seed `20261124`とholdout
seed `20261217`を分離し、CI runも同じ2 seedの別標本を使う。規範上の寸法・色は
[e-Govの現行改正（2026-09-01施行）](https://laws.e-gov.go.jp/law/335M50004002003/20260901_508M60000802003)
別表第二に照合した。

| run | 車線シナリオ / 標本点 | 標識 | 中心誤差 p95 | 曲率誤差 p95 | 標識 macro F1 |
|---|---:|---:|---:|---:|---:|
| full tuning | 12 / 972 | 32 | 0.0034720553 m | 0.0000805050 1/m | 1.000 |
| full holdout | 20 / 1620 | 40 | 0.0030961833 m | 0.0000374853 1/m | 1.000 |
| CI tuning | 3 / 243 | 8 | 0.0031356323 m | 0.0000225050 1/m | 1.000 |
| CI holdout | 4 / 324 | 8 | 0.0050927912 m | 0.0000332250 1/m | 1.000 |

full holdoutは中心誤差最大0.0086702654 m、曲率誤差最大0.0000447058 1/mだった。
全曲率標本で最大横加速度は浮動小数点丸めを含め2.5000000000000004 m/s²で、
assert許容差 `1e-12` 内に収まった。全72標識を正しく分類し、赤八角形、正立した
赤三角形、欠損輪郭、低彩度、白帯のない赤円はすべて `unknown` へ棄却した。

一時停止は一辺0.80 m、円形標識は直径0.60 mを基準にし、合成scale 0.72–1.28は
法令の一般的な0.5–2倍範囲内である。座標から復元した寸法誤差は `1e-12` m未満。
画像はRGB 0..1の固定尺度で、データ面に最近傍拡大や疑似カラーを使っていない。

2回のfull描画で集計値・全行と4 PNGのSHA-256が一致した。first / middle / lastは
1840×974、contact sheetは1840×1420。captionは最小30 pxで、contact sheetの
1080p換算でも22.8 pxだった。SHA-256は順に
`6C08D46C77B75822C2E5DA70701A7FDC240B29F295EBC559D4AA7DAFDF929D6A`、
`3F4F20FE4BBD8E35241F77ACE689A62028E57E8A51FFF4408E3150385413B3A3`、
`875E2801ABF29DA72E09CD557A334AECCA24F0DE4D34BF9C74C9B44B2F61252F`、
`E49BC8EDF6594ACCF1B1CE7425FE9CED19E3B1797101827878CF285AA6CB25A2`。

検分用出力はrepo外の
`C:\dev\data\ginza_v2_stage2_ops_2026_11_24\inspection_full_g` と
`C:\dev\data\ginza_v2_stage2_ops_2026_11_24\inspection_full_h` に保存した。
fullのスクリプト内実測は19.13秒 / 21.22秒（壁時計22.5秒 / 24.6秒）、CIの反復は
0.67–0.98秒（壁時計3.4–4.4秒）だった。したがってPoC単体をテスト化する場合のtimeoutは、観測した
最悪値の2倍を上回る60秒を下限とする。

## Run / 実行

```powershell
$env:PYTHONPATH = 'C:\dev\projects\imgevolve_wt_ginza-stage2'
$env:FULLSEYE_FIGURE_DIR = 'C:\dev\data\ginza_v2_stage2_ops_2026_11_24\inspection_full'
py -3.11 examples/poc_ginza_stage2_ops.py
$env:FULLSEYE_FIGURE_DIR = $null
$env:CI = '1'
py -3.11 examples/poc_ginza_stage2_ops.py
```

The script writes no figure unless `FULLSEYE_FIGURE_DIR` is set. Metrics and every tuning/holdout row are always written to stdout; `--metrics` writes the same data as JSON.

`FULLSEYE_FIGURE_DIR` を指定しない実行では図を書かない。調整用・holdoutの全件と集計値は常に標準出力へ出し、`--metrics` では同じ値をJSONにも保存する。
