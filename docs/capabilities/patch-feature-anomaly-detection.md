---
id: patch-feature-anomaly-detection
title: 良品だけから学んで外れたパッチを指す(古典特徴の「位置ごとの正規分布」と「記憶バンク」、再現率を保証する運用点)
title_en: Flag patches that leave what good samples look like (classical features, a normal distribution per position or a memory bank, and a recall-guaranteeing operating point)
category: 見つける
ops: [patch_features, patchdist_fit, patchdist_score, patchbank_fit, patchbank_score, anomaly_pixel_auroc, anomaly_pro, anomaly_image_auroc, anomaly_pixel_f1_max, anomaly_image_f1_max, anomaly_operating_point, anomaly_region_overlap]
examples: [poc_patch_anomaly, anomaly_eval_metrics]
version: 0.7.0
inputs: [video, image2d]
pipeline: [patchbank_fit, patchbank_score]
alternatives: [varmodel_fit, compare_to_golden, dc_rpca_sparse]
limits: 特徴は古典の手作り(勾配・Gabor・LBP・周波数帯・色)で、深層特徴ではない。細かい欠陥や意味の絡む欠陥(論理的な異常)は、位置の重みを足した記憶でも位置の違いまでしか言えない。良品群に欠陥が混ざると分布も記憶も鈍る。実データ(テクスチャ)では画像ごとの AUROC は 0.5〜0.6 止まりで、深層特徴の方法の数字の代わりにはならない。
calibration: 異常地図は特徴空間の距離(位置ごとの分布はマハラノビス距離)で、画素値の単位ではない。大きさを実寸で言うなら、既知寸法の的を同じ光学系で測り `mm_per_px_from_reference` → `pixel_to_world`(格子の刻み stride px が地図の分解能)。
---

# 良品だけから学んで外れたパッチを指す(古典特徴の「位置ごとの正規分布」と「記憶バンク」、再現率を保証する運用点)

## できること

良品の画像だけを何枚か渡すと、パッチ(格子の小窓)ごとの古典特徴を覚え、新しい 1 枚のどのパッチが良品から外れているかを異常地図で返します。覚え方は 2 つあります。

- **位置ごとの正規分布**(`patchdist_fit` / `patchdist_score`): 格子の位置ごとにパッチ特徴の多変量正規分布を当てはめ、マハラノビス距離で採点します。良品が n 枚で特徴が D 次元なら共分散は n ≦ D で特異になるので、★**縮小推定を宣言します**(`shrinkage="auto"` は Ledoit–Wolf の解析的な強さ、数を渡せば固定)。縮小を宣言せずに特異なら `ValueError` で拒否します(良品 5 枚・51 次元では階数 4)。`pool="global"` は全位置・全画像のパッチから分布を 1 つ当てはめ、位置が決まらない確率的なテクスチャに向きます。
- **記憶バンク**(`patchbank_fit` / `patchbank_score`): 良品のパッチ特徴を記憶し、k 近傍の距離で採点します。記憶は貪欲な k 中心の被覆で間引き(`coreset`)、★**被覆半径**(どの良品パッチも記憶のこの距離以内)を返します。`position_weight` を足すと格子の位置を特徴に加え、「正しい模様が違う場所にある」論理的な異常を指します。

特徴 `patch_features` は多重解像度の勾配(構造テンソル)・Gabor 応答・回転不変の一様 LBP のヒストグラム・パッチの周波数帯・色(反対色)で、深層特徴は使いません(決定的で、チャネルの意味を読めます)。採点は方法に依存しない `anomeval` の族で: 画素 AUROC・AUPRO・画像 AUROC・F1 最大(`anomaly_pixel_f1_max` / `anomaly_image_f1_max`)。そして ★**再現率を保証する運用点** `anomaly_operating_point`: 持ち出した欠陥 k 枚のうち何枚を拾うかを Clopper–Pearson の下限(信頼水準つき)で決め、保証できないほど欠陥が少ないときは閾値を返さず拒否します。

- ★確率場(1 枚ごとに模様が違う滑らかなテクスチャ、点と細い傷)では、位置ごとの正規分布(AUPRO 0.375、良品 20 枚)は、全位置まとめた分布(0.559)と記憶バンク 10 %(0.603)に負けます。良品 5・20・80 枚のどれでも順位は変わりません(0.155 / 0.272 / 0.313 に対し記憶バンク 0.617 / 0.653 / 0.715)。位置ごとの標本が n 個しかないのに 51 次元を推定するからで、勾配だけ 3 次元にすると 0.531 まで戻ります。
- ★既存の変動モデル(`varmodel_*`)は同じ確率場で画素 AUROC 0.785、記憶バンクは 0.881。織り(位相が毎回ランダム)では位置合わせが成り立たず変動モデルは拒否し、パッチ特徴は 0.97 の AUPRO で当てます。
- ★論理的な異常: 縦の棒が 24 px 動いた画像で、位置を見ない記憶の異常度は良品の 0.9 倍(見逃し)、位置の重み 4 を足すと 3.9 倍(指す)。
- ★記憶を 10 % に間引いても AUPRO は 0.638 対 0.684(全部)で、採点の CPU 時間は 0.84 秒対 12.55 秒。被覆半径は 8.42 → 7.38 → 6.61 → 5.66 → 0 と縮みます。
- ★運用点: 較正に欠陥 30 枚(再現率 0.8、信頼 0.9)で閾値を決める手順を 300 回繰り返すと、残りの欠陥での真の再現率が 0.8 以上になった割合は保証つきで 0.957、較正の欠陥の 80 % 点を取るだけの方法は 0.503。保証の代償は誤検出(平均 0.369 対 0.211)。欠陥 10 枚で 0.95 / 0.95 を求めると拒否(要 59 枚)。
- 公開実データ(テクスチャ・基板・ろうそく): DAGM 2007 Class1(確率的なテクスチャ、欠陥は細かい模様が消えた滑らかな斑、2×2 縮小・良品 40 枚・試験 100 枚)では、変動モデル(画素ごとの帯)が画素 AUROC 0.436 で偶然以下、位置ごとの正規分布は 0.532〜0.665、★勾配だけの記憶バンクは画素 AUROC 0.768・AUPRO 0.474(51 次元の記憶バンクは 0.623・0.188 で、特徴を増やすと悪くなる)。ただし画像ごとの AUROC は 0.50〜0.61 で、画像の合否には使えない。VisA pcb1(1/6 縮小・良品 20 枚・試験 200 枚)では、★記憶バンク 10 % が画素 AUROC 0.990・AUPRO 0.875・画像 AUROC 0.935・F1 最大 0.720(変動モデルの 0.808・0.678 を上回る)、位置の重みを足すと 0.969・0.790 に下がる。candle は記憶バンク 0.895・0.734、位置つき 0.901・0.716。

## What it does

Anomaly detection from good samples only, with classical, deterministic patch features instead of a pretrained network. `patchdist_*` fits a multivariate normal per grid position and scores by Mahalanobis distance; since n good images give a singular covariance when n <= D, the shrinkage is declared (Ledoit–Wolf analytic intensity, or a number) and `shrinkage="none"` is refused for a singular covariance. `pool="global"` fits one distribution to all patches for stationary textures. `patchbank_*` keeps a memory bank thinned by greedy k-centre covering, reports the covering radius, and optionally appends the grid position to find a correct pattern in the wrong place. Evaluation uses the method-independent `anomeval` family (pixel / image AUROC, AUPRO, F1 max) and `anomaly_operating_point`, which picks the highest threshold whose defect recall is guaranteed at a stated confidence with an exact Clopper–Pearson limit and refuses when there are too few defective images. On a stochastic texture the per-position normal distribution loses to the pooled distribution and the memory bank at 5, 20 and 80 good images; a memory bank at 10 % keeps its accuracy at about a tenth of the scoring time; the guaranteed operating point keeps its declared confidence in 95.7 % of 300 repetitions against 50.3 % for the unguaranteed quantile.

## 向くところ / 向かないところ

- 向く: 良品が少ししか無く欠陥の見本が無い外観検査(テクスチャ・布・基板・成形品)。位置が決まった品物は位置ごとの分布か位置つきの記憶、模様が毎回違う面は全位置まとめた分布か記憶バンク。
- **向かない: 欠陥の見本が十分あるなら**教師ありのほうが強い。細かい模様が消えるだけの欠陥(実データの滑らかな斑)は、縮小しすぎると見えなくなる(2×2 の縮小までは見える)。
- 位置ごとの正規分布を高次元の特徴で使うと、良品が数十枚でも標本が足りず外れる(上の数字)。特徴を絞るか `pool="global"` か記憶バンクに替える。
- 再現率の保証は「較正に使った欠陥と同じ分布の欠陥」について標本から言える主張で、未来の全ての欠陥の保証ではない。

## 推奨パイプライン

`patchbank_fit` → `patchbank_score`(必要なら `anomaly_pro` で採点、`anomaly_operating_point` で閾値)

良品を学び → 試験の 1 枚ごとに異常地図 → 画像ごとの最大値を持ち出した良品・欠陥で `anomaly_operating_point` にかけて運用の閾値を決める。位置が決まった品物は `position_weight`、模様が毎回違う面は `patchdist_fit(pool="global")` も試す。

## 代替

位置を合わせた良品なら `varmodel_fit`(画素ごとの帯、誤検出率を宣言)。基準 1 枚との差なら `compare_to_golden`。1 枚だけで周期的な背景の上の孤立した欠陥なら `dc_rpca_sparse`。

## 限界

古典の手作り特徴で、深層特徴の方法とは同じ数字にならない(実データのテクスチャで画素 AUROC は最良でも 0.77、画像ごとの AUROC は 0.5〜0.6)。良品に欠陥が混ざると両方式とも鈍る(記憶バンクのほうが緩やか)。位置の重みは位置の違いを言うだけで、意味(2 つの部品の組合せの正しさ)は言えない。

## 実寸校正

異常地図は特徴空間の距離で、画素値の単位ではありません。欠陥の大きさを実寸で言うなら、既知寸法の的を同じ光学系で測り `mm_per_px_from_reference` → `pixel_to_world`(地図の分解能は格子の刻み stride px)。

## 最初の 1 本

```python
import numpy as np
from scipy import ndimage as ndi
import fullseye as fs

rng = np.random.default_rng(0)
tex = lambda: ndi.gaussian_filter(rng.standard_normal((64, 64)), 2.0) * 4.0   # 1 枚ごとに模様が違う確率場
goods = np.stack([tex() for _ in range(20)])                                    # 良品 20 枚
model = fs.ledger.patchbank_fit(goods, coreset=0.1)                             # 記憶 10 %
print("記憶 %d / %d 個、被覆半径 %.2f" % (model["n_memory"], model["n_total"], model["covering_radius"]))

test = tex()
test[30:36, 20:40] += 3.0                                                       # 硬い縁の傷
r = fs.ledger.patchbank_score(test, model)
print("画像の異常度 %.2f、最大の場所 %s" % (r["image_score"], tuple(int(i) for i in np.unravel_index(r["map"].argmax(), r["map"].shape))))
```

## 裏づけ

- op: `patch_features` / `patchdist_fit` / `patchdist_score` / `patchbank_fit` / `patchbank_score`、評価 `anomaly_pixel_auroc` / `anomaly_pro` / `anomaly_image_auroc` / `anomaly_region_overlap` / `anomaly_pixel_f1_max` / `anomaly_image_f1_max` / `anomaly_operating_point`
- 例: [`poc_patch_anomaly`](../../examples/poc_patch_anomaly.py) —— 合成の 3 つの世界で 8 変種 + 変動モデル + 無作為、良品 5・20・80 枚、論理的な異常、記憶の間引き、縮小の宣言、運用点の保証の 300 回、公開実データ。[`anomaly_eval_metrics`](../../examples/anomaly_eval_metrics.py) —— 画素 AUROC と PRO が違うものを数えること。
- 再現する構成(ViEW の題目のみ): ViEW2022『Fourier-Convolutional PaDiMによる異常検知』/ ViEW2023『Scale-Invariantな欠陥検出のための多重解像度PaDiMの提案』/ ViEW2024『事前学習済みDNN中間特徴量の位置を考慮した近傍法による異常検知』/ ViEW2025『異常検知モデルにおけるプリミティブ特徴量の検討』/ ViEW2025『高速検査のための統計的近傍予測に基づく改良型PatchCoreの提案』/ ViEW2021『高解像度画像からの特徴量抽出による鍛造部品の異常検知と計算量抑制』。
- 先行: T. Defard ほか, *ICPR Workshops* 2020(位置ごとの正規分布); K. Roth ほか, *CVPR* 2022(記憶バンク・貪欲な被覆); O. Sener & S. Savarese, *ICLR* 2018(k 中心); O. Ledoit & M. Wolf, *J. Multivar. Anal.* 88:365, 2004; T. Ojala ほか, *IEEE TPAMI* 24:971, 2002; C. J. Clopper & E. S. Pearson, *Biometrika* 26:404, 1934。
- データ(実データの章、リポジトリに同梱しない): DAGM 2007 Class1(Zenodo 12750201、CC BY 4.0、2×2 の平均で縮小)と VisA(CC BY 4.0、灰色化と縮小)。
