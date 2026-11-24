# 顕微鏡粒径 PoC の質の門

主張は「端・未解決の重なり・校正期限を判断として記録すれば、画像の個数基準分布を、体積基準やレーザー回折と混同せず真値と比較できる」。区間は**分割後に受理した粒子に条件付けた9 Dx の名目95%同時区間**であり、未検出や曖昧成分を含む母集団の被覆を主張しない。主図の6粒子は判断経路の説明だけに使い、分位点を報告しない。別の324粒子試料で、受理推定粒子へ一意に対応する真値だけを用いて3基準のD10/D50/D90と条件付き同時区間を比べる。分位点は重み付き経験分布の中点規約である。

| 観点 | 門 | 2026-11-23 の実測値 | 根拠 |
|---|---|---:|---|
| 対象と入出力 | ステージミクロメータ、原画像、分割、真値、推定、分布、失敗側が同じ画面にある | 6 パネル（2列×3行） | `01_compendial_particle_microscopy_main.png` |
| 壊れる側 | 深い重なりで単一個数を断定しない | 曖昧 3 条件 | 主図パネル5、重なり率系列 |
| 形 | 箱や球で代用せず、解析的な円・楕円を画素化する | 円5、楕円1 | 合成真値表 `TRUTH` |
| 数字 | 孤立粒子の面積相当径を真値と比べる | 最大絶対誤差 0.165 px | 主図パネル6、evaluation manifest |
| 尺度 | ステージミクロメータ 200 px = 0.100 mm | 0.500000 ± 0.002500 µm/px | 主図パネル1・6 |
| 少標本 | 6粒子主図で母集団分位点を出さない | 有効粒子数4 < 最小30、全D値は `insufficient_sample` | 主図パネル6、evaluation manifest |
| 分位点規約 | 重複径を集約した重み付き経験分布の中点 | `lower_cumsum` を使わない | op出力 `policy.quantile_convention`、大標本図 |
| 大標本 | 低コントラスト、重なり、端を含む別試料で3基準ごとに、受理推定粒子と一意に対応する**条件付き真値**CDFを比べる | 324粒子を描画。条件付きの数基準D50 真値/推定は実行時に同じ対応表から再計算する。有効数は個数287.0、面積256.03、体積228.44 | `04_compendial_particle_microscopy_large_validation_number_cdf.png`、`05_compendial_particle_microscopy_large_validation_area_cdf.png`、`06_compendial_particle_microscopy_large_validation_volume_cdf.png` |
| 同時区間 | 9個のDxを同時に出す Bonferroni 条件付きbootstrap、尺度と端補正感度を合成 | 400独立試行で9本すべてを被覆した観測は376/400=94.0%、Wilsonの95%下限は91.23%。これは**事後の探索的な門**であり、名目95%を実証したとは書かない。尺度・分割・低コントラスト不検出・端判断を毎試行で変動。図表と試験は同じ再計算関数の値を使う | `tests/test_pharmaparticle.py`、図03の表 |
| 有効数の閾値 | Kish有効数を個数・面積・体積ごとに判定する**未検証の暫定**スクリーニング閾値30 | 数基準D50の80試行掃引: n=15/20は抑止、n=30/45/60は被覆80/80、平均区間幅0.003452/0.003071/0.002741 mm。29個×1 px + 1個×10^6 pxでは体積<1.01で抑止 | `tests/test_pharmaparticle.py` |
| 来歴 | 行の64桁文字列を形式検査せず、`blob_split` と `blob_count_interval` の構造化出力を入力しop内でdigestを再計算する | `component_id` と上流labelの一対一、両方向の行数、`upstream_split_label`の全行一意性と非ゼロlabel数、各行の面積・面積相当径を実際の`blob_split`画像から再計算して照合する。面積の許容は最近接画素の±0.5 px2と、それから導かれる径の範囲だけ。これは整合性検査であり改ざん検知ではない。署名・不変成果物・実行記録を持つ規制対応基盤で改ざん検知を扱う | `tests/test_pharmaparticle.py` |
| 端補正 | 包含確率、補正径、補正面積の不確かさを感度再標本化へ伝播する | 相関なしを入力来歴で明示し、相関入力はfail-closed。6σの物理範囲から外れる入力を拒否し、抽出時も物理範囲外ならclipせず再抽出する。実opを呼ぶ無作為場3窓で、Horvitz--Thompson補正後の中央値偏りが補正前より小さい | `tests/test_pharmaparticle.py` |
| 精度範囲 | 径、軸比、副画素位置、SNR、PSF、閾値、背景むらを掃引した範囲だけ主張する | 128条件: 受理条件付きの中央0.090 px、p90 1.605 px、最悪1.866 px、拒否23.4%（過分割23.4%）。mergeは各条件が真値1粒子のため**not assessed**。p90条件は d=20、比1.8、位相0.65、noise=.01、PSF=1.0、閾値=.68、勾配=.12 | `07_compendial_particle_microscopy_accuracy_sweep.png` と `07_compendial_particle_microscopy_accuracy_sweep_all_conditions.tsv` |
| 文字 | 文字をデータの上に置かず、帯・余白へ置く。CDFのD値札は軸外の専用帯 | CDF 2905×1400 px、最小32 px = 1080p換算24.69 px。大標本表 7162×1818 px、最小40 px = 同23.76 px。札の矩形が交差すれば描画時に拒否 | 原寸検分、PoCの`cdf-minimum-text-height-at-1080p`と`large-validation-minimum-text-height-at-1080p`門 |
| 体裁 | Fullseye / examplefig の描画器で作る | `annotate_figure_grid`、`render_plot`、`_render_table`、`save`、`save_grid` | PoC ソース |
| 決定性 | 同じ種と環境で配列・主図・manifest が一致 | SHA-256完全一致、manifest差分0 | 実行時の門 |
| 標本 | 1枚に全条件、重なり率系列5条件 | 粒子6、系列5 | 合成真値表・系列図 |
| 動画 | 今回は作らない | 0本 | 依頼どおり |
| 所要 | full と `CI=1` の両方を走らせる | full 5.36 s、CI 5.82 s（初回実測） | 標準出力 |

図は `FULLSEYE_FIGURE_DIR` に書く。受け取り検分では縮小一覧で済ませず、主図と重なり率系列を原寸で開く。
