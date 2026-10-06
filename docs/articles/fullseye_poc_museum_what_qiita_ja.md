> **言語 / Language**: **日本語** · [English](https://qiita.com/furuse-kazufumi/items/4f65e33d11099a1ebbca)

# 紙面の計測館 —— 何を測るかの棟(産業検査・寸法計測・医用生物・天文環境)

> **[紙面の計測館 総合案内](https://qiita.com/furuse-kazufumi/items/c1606bcfa2085d204ad6)** の一棟です。ほかの棟・用語・テーゼは案内にあります。

この棟には **114 点**を掛けています。番号は**収蔵番号**で、棟を移しても分けても変わりません。

> 各展示の「使用 op」から、その op のノート(型契約・罠・図・Studio で走るプログラム)へ飛べます: [オペレータ目録](https://furuse.work/OP_CATALOG.html) / [op ノートの索引](https://furuse.work/ops/INDEX.html)。

### 産業検査ウィング ―― 合格の数字と不合格の数字は両立する

検査ラインの数字は合否に直結するので、1 つの指標に畳みたくなります。この部屋の 32 点は、畳んだ瞬間に消えるものを並べたものです。まとめた ROC が種類別の盲点を隠す織物、MTF が合格のまま黒レベルが不合格になる迷光、読取率だけ見ると寛容なデコーダが良く見えるバーコード。

真値はどれも自分で仕込んであります。周期地の閉形式、レーザー断面の h(x)、1 次元熱伝導の解析解、閉形式の欠陥周波数。だから「検出できました」の先にある「どこで検出できなくなるか」を、しきい値を後から合わせずに測れます。

もう 1 つの共通点は、壊れ方が連続ではなく崖であること。傾き 15 度と 16 度、時間窓 25 秒と 4 秒、ΔT 1.6 K ―― その位置は幾何か物理で先に計算できる場合が多く、計算できたものは実測と突き合わせてあります。

## No.2026.003 —— 1 次元バーコードが読めなくなる境界 ―― 誤読と読み取り不能を分けて数える

[![1 次元バーコードが読めなくなる境界 ―― 誤読と読み取り不能を分けて数える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_barcode_1d/01_misread_split_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_barcode_1d/01_misread_split.png)

*↑ **1 次元バーコードが読めなくなる境界 ―― 誤読と読み取り不能を分けて数える** ―― 自作の簡易符号(実在規格ではない)を 4 通りに壊し、成功 / 誤読 / 読み取り不能を分けて数えた図。壊れ始めてからの 384 枚で、構造を検査する厳格デコーダは誤読 7.3 %、必ず 9 桁返す寛容デコーダは誤読 46.1 % ―― 成功率は寛容のほうが高い(47.7 % 対 40.1 %)。傾きの崖は幾何だけで決まり(予測 15.95 度)、実測は 15 度と 16 度のあいだ。*

[![小さい汚れは行が「読めてしまう」ので誤った票を投じる。大きい汚れは棄権するので多数決が効く。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_barcode_1d/02_smudge_nonmonotone_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_barcode_1d/02_smudge_nonmonotone.png)

*↑ 測定の図 ―― 小さい汚れは行が「読めてしまう」ので誤った票を投じる。大きい汚れは棄権するので多数決が効く。*

[![ぼけ 3 本(m=2,3,4 px)は 1 本に重なる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_barcode_1d/03_collapse_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_barcode_1d/03_collapse.png)

*↑ ぼけ 3 本(m=2,3,4 px)は 1 本に重なる。*

[![(d) は走査線が符号の上下からはみ出す角度。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_barcode_1d/04_barcode_damage_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_barcode_1d/04_barcode_damage.png)

*↑ (d) は走査線が符号の上下からはみ出す角度。*

```
py -3.11 examples/poc_barcode_1d.py
```

ソース: [examples/poc_barcode_1d.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_barcode_1d.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_barcode_1d)

使用 op(ノートへ): [`decode_barcode`](https://furuse.work/ops/2d/barcode/decode_barcode.html) · [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`vol_edge_probe`](https://furuse.work/ops/3d/probe/vol_edge_probe.html)

## No.2026.093 —— 電極の屈曲度を CT から測る ―― 経験則は空隙率しか見ない

[![電極の屈曲度を CT から測る ―― 経験則は空隙率しか見ない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_tortuosity/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_tortuosity/01_scene.png)

*↑ **電極の屈曲度を CT から測る ―― 経験則は空隙率しか見ない** ―― リチウムイオン電池の電極塗工層を合成マイクロ CT で作り、空隙率と屈曲度を出す。現場の既定値 Bruggeman τ = ε^(-0.5) をゼロ点に置き、同じボリュームで定常拡散方程式を解いた真値と比べると、ε = 0.4448 で 1.499 対 1.843(-18.6 %)、ε を 0.691 → 0.168 と振ると誤差は -8.2 % → -69.1 % と単調に開く(実測の指数は 1.78 と 2.70 で、1.5 乗則はどちらでもない)。画像解析がよく報告する測地屈曲度 1.182 はその 2 乗が Bruggeman に 1 %以内で寄り添うだけで、真値には寄らない。決定打は対照群 ―― 空隙率を 0.4448 対 0.4510 に揃えて粒子を 4:1 に潰すと厚み方向の τ は 1.843 → 6.794(異方比 0.97 → 4.20)なのに、経験則は両方に同じ 1.5 を返す(面内は -8 % で当たって見え、厚み方向は -78 %)。閉気孔は最大 1.92 % で犯人ではなく、効いているのは粒子半径の 0.40 倍しかない首。解像度の崖を予測して掃引したが崖は無く、voxel を 5.5 倍粗くすると ε は -0.4 % しか動かないのに τ は +72 % ずれる ―― 警告なしに。*

[![左: 上端 1 / 下端 0 の濃度場。等濃度線が固相を避けて曲がる分が遠回り。右: bond ごとの散逸(明るいほど流れが集中している = 首)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_tortuosity/02_map_transport_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_tortuosity/02_map_transport.png)

*↑ 測定の図 ―― 左: 上端 1 / 下端 0 の濃度場。等濃度線が固相を避けて曲がる分が遠回り。右: bond ごとの散逸(明るいほど流れが集中している = 首)。*

[![ε が下がるほど経験則と真値が開く。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_tortuosity/03_porosity_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_tortuosity/03_porosity_sweep.png)

*↑ ε が下がるほど経験則と真値が開く。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_tortuosity/04_bruggeman_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_tortuosity/04_bruggeman_error.png)

*↑ この回の図*

[![経験則は向きを持てない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_tortuosity/05_anisotropy_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_tortuosity/05_anisotropy.png)

*↑ 経験則は向きを持てない。*

[![同じ物理構造を粗い格子から細かい格子まで。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_tortuosity/06_resolution_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_tortuosity/06_resolution.png)

*↑ 同じ物理構造を粗い格子から細かい格子まで。*

```
py -3.11 examples/poc_battery_electrode_tortuosity.py
```

ソース: [examples/poc_battery_electrode_tortuosity.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_battery_electrode_tortuosity.py)

この回が作った図は全部で **6 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_battery_electrode_tortuosity)

使用 op(ノートへ): [`vol_distance_transform`](https://furuse.work/ops/3d/medial/vol_distance_transform.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html)

## No.2026.004 —— 転がり軸受の異常診断 ―― どこまで雑音に埋もれても当てられるか

[![転がり軸受の異常診断 ―― どこまで雑音に埋もれても当てられるか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bearing_diagnosis/01_envelope_vs_raw_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bearing_diagnosis/01_envelope_vs_raw.png)

*↑ **転がり軸受の異常診断 ―― どこまで雑音に埋もれても当てられるか** ―― 閉形式の欠陥周波数(BPFO 104.556 Hz)で合成した衝撃列を雑音に沈め、生スペクトルと包絡線スペクトルの検出率を並べた図。10/10 を保てた最悪の SNR は生 -0.9 dB、包絡線 -18.4 dB で 17.5 dB の差。ただし欠陥の無い記録でも大域顕著さは 43 まで出る ―― しきい値を null から決めていなければ、この PoC 自体が偽陽性を出していた。*

[![どちらも最悪条件では 0 に落ちる。包絡線は万能ではなく、崖が悪い SNR 側へ動くだけ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bearing_diagnosis/02_detection_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bearing_diagnosis/02_detection_sweep.png)

*↑ 測定の図 ―― どちらも最悪条件では 0 に落ちる。包絡線は万能ではなく、崖が悪い SNR 側へ動くだけ。*

[![win=32 は毎回共振を含み、win=256 は毎回外す。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bearing_diagnosis/03_sk_bands_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bearing_diagnosis/03_sk_bands.png)

*↑ win=32 は毎回共振を含み、win=256 は毎回外す。*

```
py -3.11 examples/poc_bearing_diagnosis.py
```

ソース: [examples/poc_bearing_diagnosis.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bearing_diagnosis.py)

この回が作った図は全部で **3 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_bearing_diagnosis)

使用 op(ノートへ): [`bearing_defect_frequencies`](https://furuse.work/ops/acoustics/bearing/bearing_defect_frequencies.html) · [`envelope_spectrum`](https://furuse.work/ops/acoustics/bearing/envelope_spectrum.html) · [`spectral_kurtosis`](https://furuse.work/ops/acoustics/bearing/spectral_kurtosis.html) · [`spectrum`](https://furuse.work/ops/oned/signal/spectrum.html) · [`synthesize_bearing_signal`](https://furuse.work/ops/acoustics/synthesis/synthesize_bearing_signal.html)

## No.2026.094 —— バンプの共平面性を基板そりから分ける ―― 引きすぎると本物の不良も消える

[![バンプの共平面性を基板そりから分ける ―― 引きすぎると本物の不良も消える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bump_coplanarity/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bump_coplanarity/01_scene.png)

*↑ **バンプの共平面性を基板そりから分ける ―― 引きすぎると本物の不良も消える** ―― Cu ピラー 256 本の高さ場に、そり PV 50 µm と個体差 1σ 4 µm、短小バンプ 6 本を仕込んで測り返す。そりを引かずに平面だけ引くゼロ点は読み取り RMS 誤差 8.84 µm(個体差の 2.2 倍)で、誤検出 58 本の裏で本物の短小を 1 本見逃す。2 次曲面を引くと 1.23 µm・誤検出 0 になるが、3 次にすると 1.37 µm と逆に悪くなる(仕込んだ高次成分が 4 次のロブなので 3 次では取れず、増えた項が個体差を吸う)。崖は幾何で予測でき、2 次が個体差 1σ に並ぶのは PV 169.9 µm の予測に対して実測 169.4 µm。★中央が 8 µm 沈む本物の低次不良を足すと、残差からは 88.2 % 消える一方で短小の検出数は 5→5 本のまま変わらず、見逃しだけが 0→2 本に増える ―― 消えた分は「そり 30.06→36.20 µm」に化けている。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bump_coplanarity/02_deviation_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bump_coplanarity/02_deviation_map.png)

*↑ 測定の図*

[![真値の共平面性は 38.44 µm、本当に仕様外なのは 5 本。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bump_coplanarity/03_order_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bump_coplanarity/03_order_table.png)

*↑ 真値の共平面性は 38.44 µm、本当に仕様外なのは 5 本。*

[![左端の 6 本が仕込んだ短小。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bump_coplanarity/04_sorted_deviation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bump_coplanarity/04_sorted_deviation.png)

*↑ 左端の 6 本が仕込んだ短小。*

[![そりの形を固定すれば、取り切れない残りは PV に比例する。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bump_coplanarity/05_warpage_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bump_coplanarity/05_warpage_cliff.png)

*↑ そりの形を固定すれば、取り切れない残りは PV に比例する。*

[![消えた分はそり側の数字に足されている(+6.14 µm)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bump_coplanarity/06_absorbed_defect_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bump_coplanarity/06_absorbed_defect.png)

*↑ 消えた分はそり側の数字に足されている(+6.14 µm)。*

```
py -3.11 examples/poc_bump_coplanarity.py
```

ソース: [examples/poc_bump_coplanarity.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bump_coplanarity.py)

この回が作った図は全部で **6 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_bump_coplanarity)

使用 op(ノートへ): [`auto_threshold`](https://furuse.work/ops/2d/segmentation/auto_threshold.html) · [`background_flatten`](https://furuse.work/ops/3d/surface_fit/background_flatten.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`eval_poly_surface`](https://furuse.work/ops/3d/surface_fit/eval_poly_surface.html) · [`fit_poly_surface`](https://furuse.work/ops/3d/surface_fit/fit_poly_surface.html) · [`surface_form_error`](https://furuse.work/ops/3d/surface_fit/surface_form_error.html)

## No.2026.009 —— コンクリートのひび割れ幅は 1 画素より細い ―― 数える幅と、積分する幅

[![コンクリートのひび割れ幅は 1 画素より細い ―― 数える幅と、積分する幅](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width/02_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width/02_scene.png)

*↑ **コンクリートのひび割れ幅は 1 画素より細い ―― 数える幅と、積分する幅** ―― 1 px = 0.20 mm の視野で幅 0.05〜2.0 mm のひび割れを振り、二値化して数える幅と輝度欠損を積分する幅を並べた図。二値化は 0.20 mm 以下で何も返さず、真値 0.25〜0.40 mm の 4 条件が全部 0.200 mm を返す。積分法は 0.05 mm(0.25 px)まで連続に追えるが、照明が曲がると 1 次のベースラインでは +0.1741 mm の下駄が乗る(2 次なら +0.0062 mm)。*

[![2 値化の 2 本は階段。0.20 mm(1 px)以下ではマスクが空になり 0(= 未検出)へ落ちる。積分法は 0.05 mm (0.25 px)まで直線 y=x に乗る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width/01_width_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width/01_width_sweep.png)

*↑ 測定の図 ―― 2 値化の 2 本は階段。0.20 mm(1 px)以下ではマスクが空になり 0(= 未検出)へ落ちる。積分法は 0.05 mm (0.25 px)まで直線 y=x に乗る。*

[![点ごとでは 2 値化が下に見えるが、経路平均に直すと積分法の散らばりは消え、2 値化の偏りは残る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width/03_crossover_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width/03_crossover.png)

*↑ 点ごとでは 2 値化が下に見えるが、経路平均に直すと積分法の散らばりは消え、2 値化の偏りは残る。*

[![真の幅は 0.60 mm 固定。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width/04_max_vs_mean_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width/04_max_vs_mean.png)

*↑ 真の幅は 0.60 mm 固定。*

```
py -3.11 examples/poc_crack_width.py
```

ソース: [examples/poc_crack_width.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_crack_width.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_crack_width)

使用 op(ノートへ): [`distance_transform`](https://furuse.work/ops/2d/region/distance_transform.html) · [`sk_medial`](https://furuse.work/ops/2d/region/sk_medial.html) · [`skeleton`](https://furuse.work/ops/2d/region/skeleton.html) · [`thinning`](https://furuse.work/ops/2d/region/thinning.html) · [`vol_distance_transform`](https://furuse.work/ops/3d/medial/vol_distance_transform.html)

## No.2026.017 —— 周期のある地に埋もれた欠陥 ―― まとめた ROC が隠すもの

[![周期のある地に埋もれた欠陥 ―― まとめた ROC が隠すもの](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fabric_defect/04_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fabric_defect/04_scene.png)

*↑ **周期のある地に埋もれた欠陥 ―― まとめた ROC が隠すもの** ―― 周期 8 px の織り地に線・斑点・ムラの 3 種の欠陥を埋め、検出器のスコア地図と種類別の ROC を並べた図。現場でいちばん普通の「格子除去 + 低周波除去」はまとめた AUC 0.8113 で合格に見えるのに、ムラだけは 0.4746 とでたらめ以下。低周波を落とす 1 行が照明ムラと一緒に欠陥のムラを消していた ―― 外すだけで 0.9998 に戻る。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fabric_defect/01_auc_by_type_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fabric_defect/01_auc_by_type.png)

*↑ 測定の図*

[![対角線に乗っている系列が盲点。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fabric_defect/02_roc_by_type_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fabric_defect/02_roc_by_type.png)

*↑ 対角線に乗っている系列が盲点。*

[![欠陥の無い地だけで測った残差。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fabric_defect/03_period_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fabric_defect/03_period_error.png)

*↑ 欠陥の無い地だけで測った残差。*

```
py -3.11 examples/poc_fabric_defect.py
```

ソース: [examples/poc_fabric_defect.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_fabric_defect.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_fabric_defect)



## No.2026.069 —— 音で漏水を掘り当てる ―― 相関がきれいでも、伝わる速さを間違えれば場所は外れる

[![音で漏水を掘り当てる ―― 相関がきれいでも、伝わる速さを間違えれば場所は外れる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leak_localization/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leak_localization/01_scene.png)

*↑ **音で漏水を掘り当てる ―― 相関がきれいでも、伝わる速さを間違えれば場所は外れる** ―― 120 m の埋設管の 2 点で漏水音を録り、到達時間差から位置を出す仕事を、源・音速・減衰・反射をすべて仕込んで再現した。音速が真値なら SNR 0 dB で 0.0107 m まで当たり(Knapp-Carter の下界 0.0091 m の 1.2 倍)、崖は予測 -20.1 dB に対し実測 -12.5 dB、その下では誤差が 36.0 m と探索窓いっぱいに飛ぶ。ところが音速を 10 % 誤るだけで 1.798 m ずれ(予測 (Δc/c)(x-L/2) = 1.800 m と 0.002 m 差)、途中で管種が鋳鉄から樹脂に変わる管路では時間差がちょうど 0 になって、鋳鉄・樹脂・その平均のどれを仮定しても 18.001 m 外す ―― 掛ける相手が 0 なので、音速をいくら較正しても直らない。反射では予想が外れ、GCC-PHAT は生の相関に 1 割しか勝たなかった(誤差 0.121 m のほぼ全部が偏りで、白色化するのは振幅、遅延を運ぶのは位相だから)。*

[![同じ漏水源に既知の遅れ 28.80 ms・距離に応じた減衰・独立な広帯域雑音を乗せた。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leak_localization/02_waveforms_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leak_localization/02_waveforms.png)

*↑ 測定の図 ―― 同じ漏水源に既知の遅れ 28.80 ms・距離に応じた減衰・独立な広帯域雑音を乗せた。*

[![探索窓は管路 0-120 m のぶんだけ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leak_localization/03_correlation_curves_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leak_localization/03_correlation_curves.png)

*↑ 探索窓は管路 0-120 m のぶんだけ。*

[![漏水位置を 41 点振った。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leak_localization/05_quantization_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leak_localization/05_quantization.png)

*↑ 漏水位置を 41 点振った。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leak_localization/08_gross_rate_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leak_localization/08_gross_rate.png)

*↑ この回の図*

[![相関の形も相関係数も一切変わらない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leak_localization/11_sound_speed_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leak_localization/11_sound_speed_error.png)

*↑ 相関の形も相関係数も一切変わらない。*

```
py -3.11 examples/poc_leak_localization.py
```

ソース: [examples/poc_leak_localization.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_leak_localization.py)

この回が作った図は全部で **13 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_leak_localization)

使用 op(ノートへ): [`arrow`](https://furuse.work/ops/annotate/pointer/arrow.html) · [`bandpass`](https://furuse.work/ops/oned/signal/bandpass.html) · [`correlation_score`](https://furuse.work/ops/reprconv/score/correlation_score.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`transfer_function`](https://furuse.work/ops/acoustics/dual/transfer_function.html)

## No.2026.071 —— 熱・振動・形状を束ねる設備保全 —— 3 つ見ても、同じものを 3 回見ていることがある

[![熱・振動・形状を束ねる設備保全 —— 3 つ見ても、同じものを 3 回見ていることがある](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_machine_condition_fusion/01_scene_machine_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_machine_condition_fusion/01_scene_machine.png)

*↑ **熱・振動・形状を束ねる設備保全 —— 3 つ見ても、同じものを 3 回見ていることがある** ―― 回転機械の 6 状態(正常・芯ずれ・アンバランス・軸受外輪傷・潤滑不良・ゆるみ)を、欠陥周波数の閉形式・板の定常フィン方程式の厳密解・仕込んだ芯ずれ量から作り、3 センサで識別します。基準条件の融合は 100.0 % ですが振動のみでも 100.0 % —— 熱も形状も 1 ポイントも足しません。芯ずれは振動・熱・形状のどれ 1 個でも 100.0 %(真値の重症度との相関 0.843 / 0.841 / 0.978 で、3 つは同じ数字の別の顔)。逆に熱だけでは 正常・アンバランス・ゆるみ が互いの中で 48/48 回まわり、振動を抜くと 100.0 % → 50.0 % / 31.2 % に落ちます。融合が効くのは振動が壊れてからで、雑音 σ=1.6 で 45.8 % → 78.1 %。崖は特徴 1 個の上で予測しました: 0.5X の次数ビンは T>2/f_r=68.6 ms(実測 50→70 ms の段で d' 2.45→4.32)、熱の広がりは半値直径 66 mm(実測 64 mm から崩れ 96 mm で d' 0.00)。側帯波は 1/T<FTF=86.1 ms と予測して外し、読み取り窓 1.2/FTF=103 ms が正しい条件でした。*

[![軸受外輪傷は狭く熱く、潤滑不良は広く熱い。最高温度だけ見ると同じ顔になる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_machine_condition_fusion/02_thermal_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_machine_condition_fusion/02_thermal_maps.png)

*↑ 測定の図 ―― 軸受外輪傷は狭く熱く、潤滑不良は広く熱い。最高温度だけ見ると同じ顔になる。*

[![芯ずれは 2X、アンバランスは 1X、ゆるみは 0.5X と櫛。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_machine_condition_fusion/03_order_spectra_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_machine_condition_fusion/03_order_spectra.png)

*↑ 芯ずれは 2X、アンバランスは 1X、ゆるみは 0.5X と櫛。*

[![平行ずれ(切片)と角度ずれ(傾き)を fit_line3 で分けて取る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_machine_condition_fusion/05_misalignment_geometry_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_machine_condition_fusion/05_misalignment_geometry.png)

*↑ 平行ずれ(切片)と角度ずれ(傾き)を fit_line3 で分けて取る。*

[![芯ずれと軸受外輪傷は無傷。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_machine_condition_fusion/08_confusion_without_vibration_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_machine_condition_fusion/08_confusion_without_vibration.png)

*↑ 芯ずれと軸受外輪傷は無傷。*

[![予測は 68.6 ms(0.5X の次数ビン)と 86.1 ms(FTF 側帯波)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_machine_condition_fusion/11_sweep_record_length_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_machine_condition_fusion/11_sweep_record_length.png)

*↑ 予測は 68.6 ms(0.5X の次数ビン)と 86.1 ms(FTF 側帯波)。*

```
py -3.11 examples/poc_machine_condition_fusion.py
```

ソース: [examples/poc_machine_condition_fusion.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_machine_condition_fusion.py)

この回が作った図は全部で **13 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_machine_condition_fusion)

使用 op(ノートへ): [`angle_between_lines`](https://furuse.work/ops/3d/geometry/angle_between_lines.html) · [`arrow`](https://furuse.work/ops/annotate/pointer/arrow.html) · [`bearing_defect_frequencies`](https://furuse.work/ops/acoustics/bearing/bearing_defect_frequencies.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`distance_point_line`](https://furuse.work/ops/3d/geometry/distance_point_line.html) · [`ellipse`](https://furuse.work/ops/annotate/shape/ellipse.html) · [`fuse`](https://furuse.work/ops/3d/tsdf_fusion/fuse.html) · [`jitter`](https://furuse.work/ops/3d/augment/jitter.html) · [`mat_pinv`](https://furuse.work/ops/math/linalg/mat_pinv.html) · [`rounded_rect`](https://furuse.work/ops/annotate/shape/rounded_rect.html) · [`spectrum`](https://furuse.work/ops/oned/signal/spectrum.html) · [`stat_correlation`](https://furuse.work/ops/math/stats/stat_correlation.html) · [`synthesize_bearing_signal`](https://furuse.work/ops/acoustics/synthesis/synthesize_bearing_signal.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html)

## No.2026.024 —— 2 値マトリクスコードを読む ―― 先に死ぬのはいつも幾何

[![2 値マトリクスコードを読む ―― 先に死ぬのはいつも幾何](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_matrix_code_reading/01_symbol_and_errors_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_matrix_code_reading/01_symbol_and_errors.png)

*↑ **2 値マトリクスコードを読む ―― 先に死ぬのはいつも幾何** ―― QR と同型のレイアウトに乱数ビットを置いた符号(誤り訂正なし)を、ぼけ・傾き・遮蔽で壊してビット誤り率を数えた図。ゼロ点は当てずっぽうの 0.5 に張り付き(0.526 / 0.507)、読める側は 0.0000。崖は傾き 78 度、位置検出パターンの遮蔽 2 モジュール ―― 真のホモグラフィを渡した条件と並べると、先に落ちるのはいつも定位。*

[![自力検出の線は sigma/m 0.50 を最後に途切れる(0.60 では位置検出パターンが見つからない)。標本化はそこでまだ BER 0.07 で読めている。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_matrix_code_reading/02_blur_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_matrix_code_reading/02_blur_cliff.png)

*↑ 測定の図 ―― 自力検出の線は sigma/m 0.50 を最後に途切れる(0.60 では位置検出パターンが見つからない)。標本化はそこでまだ BER 0.07 で読めている。*

[![照明ムラ 0.9 固定。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_matrix_code_reading/03_threshold_window_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_matrix_code_reading/03_threshold_window.png)

*↑ 照明ムラ 0.9 固定。*

[![位置検出パターンは一辺 2 モジュール(全体の 0.6 %)で致命的。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_matrix_code_reading/04_occlusion_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_matrix_code_reading/04_occlusion.png)

*↑ 位置検出パターンは一辺 2 モジュール(全体の 0.6 %)で致命的。*

```
py -3.11 examples/poc_matrix_code_reading.py
```

ソース: [examples/poc_matrix_code_reading.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_matrix_code_reading.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_matrix_code_reading)

使用 op(ノートへ): [`adaptive_gauss_thresh`](https://furuse.work/ops/2d/segmentation/adaptive_gauss_thresh.html) · [`corner_response`](https://furuse.work/ops/2d/edges/corner_response.html) · [`illuminate`](https://furuse.work/ops/2d/gray/illuminate.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`sk_sauvola`](https://furuse.work/ops/2d/segmentation/sk_sauvola.html)

## No.2026.025 —— ディスプレイ検査のモアレは「本物のムラ」と区別できるか

[![ディスプレイ検査のモアレは「本物のムラ」と区別できるか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_moire_screen/04_moire_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_moire_screen/04_moire_scene.png)

*↑ **ディスプレイ検査のモアレは「本物のムラ」と区別できるか** ―― 画素格子と表示の縞が干渉して作るモアレと、本物の輝度ムラを同じ像に重ねた図。ならしの σ = 8 px で合計誤差 +0.9 % ―― 内訳は漏れ +8.3 % と減衰 -7.4 % の打ち消し。基本波のうなりが安全に見える k = 0.67 でも 3 次高調波がムラの帯に落ち、漏れは真値の +202.6 %。*

[![σ≈8 px で漏れと減衰が釣り合う。合計だけ見ると「良い測り方」に見える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_moire_screen/01_failure_split_plot_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_moire_screen/01_failure_split_plot.png)

*↑ 測定の図 ―― σ≈8 px で漏れと減衰が釣り合う。合計だけ見ると「良い測り方」に見える。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_moire_screen/02_methods_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_moire_screen/02_methods.png)

*↑ この回の図*

[![縦線がムラの周波数。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_moire_screen/03_separability_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_moire_screen/03_separability.png)

*↑ 縦線がムラの周波数。*

```
py -3.11 examples/poc_moire_screen.py
```

ソース: [examples/poc_moire_screen.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_moire_screen.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_moire_screen)

使用 op(ノートへ): [`background_flatten`](https://furuse.work/ops/3d/surface_fit/background_flatten.html) · [`fft_image`](https://furuse.work/ops/2d/frequency/fft_image.html) · [`gauss_image`](https://furuse.work/ops/2d/smoothing/gauss_image.html) · [`halftone_moire_period`](https://furuse.work/ops/printpath/npr/halftone_moire_period.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html)

## No.2026.102 —— 印刷の版ずれを刷り上がりから測る ―― 網点は格子なので、答えは 1 つに決まらない

[![印刷の版ずれを刷り上がりから測る ―― 網点は格子なので、答えは 1 つに決まらない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_registration/04_sweep_wrap_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_registration/04_sweep_wrap.png)

*↑ **印刷の版ずれを刷り上がりから測る ―― 網点は格子なので、答えは 1 つに決まらない** ―― オフセット・ラベル印刷の**版ずれ**を刷り上がりから測る。CMYK 4 版に慣行のスクリーン角(C 15°/M 75°/Y 0°/K 45°、133 lpi、1200 dpi でピッチ 9.02 px)と既知のずれを仕込んだ図。★★**網点は格子なので、相関で出るのは版ずれ d ではなく d mod Λ_θ** —— 軸方向で |d| ≤ p/2 = 4.51 px、対角で p/√2 = 6.38 px を超えると折り返す。これは測る前に閉形式で書けて、4 版 × 37 点 = 148 点のうち**144 点で予測と実測の差が 0.1096 px 以内**。残り 4 点は基本セルの境界のタイ(セル余裕 ≤ 0.165 px)で、格子で簡約した残差なら全点が合う —— **推定器は間違えておらず、格子で等価な答えのどれかを返している**(独立な 2 つの推定器が同じ折り返しをする)。★★効き方が具体的に効く: 真値 9.64 px は公差 2.0 px の 4.8 倍なのに、スクリーン角の違いだけで版ごとに 1.09〜3.32 px に見え、**4 版中 2 版が「合格」に見える** —— 同じ紙が同じだけずれた結果。★ゼロ点(インク重心)は折り返さない代わりに**縮尺が狂う**。傾きは閉形式 k = 1-β(β = 下地だけのインク量 ÷ 実際のインク量)で予測 0.3983 に対し実測 0.3711(差 0.0272)。★予測していなかったものが出た: 直線からの外れ 0.9864 px は網点ピッチ周期のさざ波で、**窓の縁で網点の列が出入りする**ため —— テーパ窓の対照群で 0.0048 px に落ちて原因が確定した。★対照群 (a): FM(確率)スクリーンに替えるだけで誤差は全域で最大 0.0029 px、折り返しゼロ。**崖の原因は推定器ではなく AM 網点の周期性**(代償はコントラスト 0.91 倍)。★対照群 (b): レジストマークを含む窓は当たる(0.0823 px)が、紙の伸び 0.600 %・版の傾き 0.120° があると誤差は距離に比例し(0.006319 px/px)、公差を超えるのは**予測 316.5 px / 実測 322.5 px** から —— 紙の 44 % が公差外。★★物差しを 2 つ置くと勝者が入れ替わる: 精度 1 位は素の相関 0.0071 px なのに判定一致率は 67.6 % で最下位、低域通過は判定 89.2 % でも精度が 94 倍悪い。**鈍い方で代表元を選び、鋭い方で詰める二段**なら両方勝つ(0.0071 px / 94.6 %)。成立条件「粗の誤差 < 基本セルの半径 4.511 px」も実測で確かめ、**二段が壊れた 2 点はすべて粗の誤差がその半径を超えた点**だった。絵柄をベタに寄せると 6 点中 3 点で丸ごと 1 格子跳ぶ。★合成器そのものが罠だった: 1200 dpi / 150 lpi(ピッチがちょうど 8.00 px)だと**全網点の標本位相が揃う**ので0.5 px ずらすたびに重心が 1.4 px 跳ねる。133 lpi にして解消した —— **整数比を避けるのが本質**で、スーパーサンプリングでは直らない。★★用途外の op を当てたら自信満々で外した: `fs.frame_align` は `inlier_ratio` **1.00** / `rms_px` 0.645 を返しながら真値 (0.00, +1.30) に対して **80.85 px** 外す(しかもその答えは網点格子のベクトルですらない = 折り返しとは別種の失敗)。**この PoC の指摘で op 側を直した** —— docstring に「繰り返し構造には使えない」を測った数字つきで書き、投票の**2 番手の山 / 1 番手**を `vote_margin` として返すようにした。賛成率はどちらの場合も 1.00 だが、`vote_margin` は網点 **1.000** / 星野 **0.143** で区別できる。*

[![スクリーン角が違うので格子の向きが違う。ピッチはどれも 9.02 px。同じ物理的なずれでも、この格子の違いが「見かけのずれ」を版ごとに変える(5 節)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_registration/01_plates_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_registration/01_plates.png)

*↑ 測定の図 ―― スクリーン角が違うので格子の向きが違う。ピッチはどれも 9.02 px。同じ物理的なずれでも、この格子の違いが「見かけのずれ」を版ごとに変える(5 節)*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_registration/02_zero_point_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_registration/02_zero_point.png)

*↑ この回の図*

[![スクリーン角が違えば格子も違う。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_registration/05_sweep_all_plates_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_registration/05_sweep_all_plates.png)

*↑ スクリーン角が違えば格子も違う。*

[![絵柄も推定器も同じ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_registration/08_control_fm_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_registration/08_control_fm.png)

*↑ 絵柄も推定器も同じ。*

[![十字は非周期なので相関のピークが 1 つに決まる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_registration/11_mark_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_registration/11_mark_scene.png)

*↑ 十字は非周期なので相関のピークが 1 つに決まる。*

```
py -3.11 examples/poc_print_registration.py
```

ソース: [examples/poc_print_registration.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_print_registration.py)

この回が作った図は全部で **13 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_print_registration)

使用 op(ノートへ): [`fly_hex_lattice`](https://furuse.work/ops/flyvision/lattice/fly_hex_lattice.html) · [`frame_align`](https://furuse.work/ops/astrostack/align/frame_align.html) · [`halftone_moire_period`](https://furuse.work/ops/printpath/npr/halftone_moire_period.html) · [`halftone_screen`](https://furuse.work/ops/printpath/npr/halftone_screen.html) · [`peak_subbin`](https://furuse.work/ops/oned/signal/peak_subbin.html) · [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html)

## No.2026.116 —— 薄い欠陥はどこまで見えるか —— 実写の地に真値を仕込んで検出限界を測る

[![薄い欠陥はどこまで見えるか —— 実写の地に真値を仕込んで検出限界を測る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_defect_floor/01_defect_floor_panels_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_defect_floor/01_defect_floor_panels.png)

*↑ **薄い欠陥はどこまで見えるか —— 実写の地に真値を仕込んで検出限界を測る** ―― 「うちのラインでどこまで薄い傷が見えるか」を見積もるとき、いちばん普通のやり方は**平らな地に白色雑音を載せた合成画像**で限界を測ることだ。その見積もりがどれだけ甘いかを、真値を厳密に持ったまま実写で測る。地は CC0 の実写テクスチャ 3 種(brick / grass / gravel)、仕込むのは**位置・大きさ・振幅が既知のガウシアン欠陥**。比較相手は **検出器が実際に見る残差 σ を実写に揃えた**合成の地 —— 「雑音の量」を同じにしてから、構造の効果だけを取り出す。判定は「仕込んだ位置が応答の最大点になる最小の振幅」で、閾値を使わないので op 側の正規化に左右されない。★★**雑音を揃えても実写の限界は 2.03〜3.47 倍高い**。限界を決めているのは雑音ではなく**地の構造**だった。背景窓 3 通り × 欠陥 σ 2 通り × 地 3 種の **18 通り全部**で比は 1 を超え(1.72〜4.56)、整合フィルタと `laplace_of_gauss` という独立な 2 つの検出器でも残る。★**予測を外した**: 「欠陥が大きいほど差が開く」と書こうとしたが、それは**振幅の刻みが作った差**だった —— 34 段では σ=1.5 と σ=3.0 が別の格子点に丸まって差が見えるが、60 段にすると両方 3.30 倍で消える。刻みもノブである。★★**「実写だから場所で変わる」も誤り**。場所による限界の散らばりは brick が 16.8 倍と突出する一方、grass 2.4 倍・gravel 3.3 倍は**σ を揃えた合成の 3.3 倍と区別がつかない**。散らばりを生むのは「実写であること」ではなく**目地という構造**。★★そして**ゼロ点**(背景を引かず、生の画素の最大点を取るだけ)が、**「当てる」という 1 つの物差しでは整合フィルタに勝つ**(0.65〜0.90 倍で先に当てる。整合フィルタは地の構造も一緒に増幅するので損をする)。無欠陥面での空振りも brick では 0 対 0 の引き分けだった。分かれるのは**照明が 2 % ずれた瞬間**で、ゼロ点は 1 万画素あたり 10.3 回鳴り、整合フィルタは 0.0 回のまま —— 生の画素の閾値は明るさの絶対値だからだ。**当てる力・空振り・ずれへの強さを別々に数えないと、役に立たない検出器を勝たせられる。***

[![同じ欠陥を振幅 0.02 から 1.20 まで上げていく。左=実写の brick、右=**残差 σ を揃えた**合成の地。雑音の量は同じなのに、右のほうが先に見えてくる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_defect_floor/02_defect_floor_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_defect_floor/02_defect_floor_sweep.gif)

*↑ 測定の図 ―― 同じ欠陥を振幅 0.02 から 1.20 まで上げていく。左=実写の brick、右=**残差 σ を揃えた**合成の地。雑音の量は同じなのに、右のほうが先に見えてくる。*

```
py -3.11 examples/poc_real_defect_floor.py
```

ソース: [examples/poc_real_defect_floor.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_defect_floor.py)

この回が作った図は全部で **2 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_real_defect_floor)

使用 op(ノートへ): [`annotate_inset`](https://furuse.work/ops/annotate/paper/annotate_inset.html) · [`annotate_legend`](https://furuse.work/ops/annotate/paper/annotate_legend.html) · [`laplace_of_gauss`](https://furuse.work/ops/2d/edges/laplace_of_gauss.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html)

## No.2026.109 —— 実写のテクスチャを回す ―― 「回転不変」は、それが要らない素材でだけ成り立つ

[![実写のテクスチャを回す ―― 「回転不変」は、それが要らない素材でだけ成り立つ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_texture_invariance/01_textures_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_texture_invariance/01_textures.png)

*↑ **実写のテクスチャを回す ―― 「回転不変」は、それが要らない素材でだけ成り立つ** ―― 実写のテクスチャ 3 枚(brick / grass / gravel、CC0)を既知の角度で回し、記述子が自分自身からどれだけ離れるかを測る。★測る前に基準を置く ―― 素材どうしの距離のうち最小(草と砂利の 0.01250)がこの課題の分解能で、回転で動く量がこれを超えたら**回した自分より別の素材のほうが近い**。★★異方な brick は 5 度で 0.0433、60 度で 0.1205 = 分解能の **9.6 倍**。等方な grass / gravel は 0.0005〜0.0024(0.17 / 0.19 倍)で実質不変。★対照群 2 つで犯人を絞る: 補間だけ(+7/-7 度の往復)は brick 0.03685、そして**補間ゼロの厳密 90 度(np.rot90)でも 0.08501 = 6.8 倍** ―― 補間のせいではない。★異方性は独立に測れて順位を説明する: 勾配方向の大域的な偏り R は brick 0.309 対 grass 0.027 / gravel 0.029 で、10 倍違うのは brick だけ。★★「回転不変」な符号化に替えると 9.64 → ror 5.49 → uniform **1.72** まで下がるが、**1 を割らない**(等方な 2 つは 0.17 → 0.02 と 10 倍良くなるのに)。LBP の回転不変性は局所パターンの巡回に対するもので、素材そのものの向きの分布は消せないため。nri_uniform が 4.24 なので「uniform だから良い」のではなく「回転不変だから良い」ことも確かめられる。★この PoC を書くまで sk_lbp の b は未使用で method は 'default' 固定だった(hough_circle_trans と同じ形)―― 選べなければ下げようがないので割り当てた(b=0.5 は従来と同一)。*

[![brick だけが 1 を大きく超える(最大 9.6 倍)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_texture_invariance/02_drift_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_texture_invariance/02_drift.png)

*↑ 測定の図 ―― brick だけが 1 を大きく超える(最大 9.6 倍)。*

[![等方な 2 つは 10 倍良くなる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_texture_invariance/03_methods_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_texture_invariance/03_methods.png)

*↑ 等方な 2 つは 10 倍良くなる。*

[![単位はどれも「分解能に対する比」。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_texture_invariance/04_summary_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_texture_invariance/04_summary.png)

*↑ 単位はどれも「分解能に対する比」。*

```
py -3.11 examples/poc_real_texture_invariance.py
```

ソース: [examples/poc_real_texture_invariance.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_texture_invariance.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_real_texture_invariance)

使用 op(ノートへ): [`cooc_feature_matrix`](https://furuse.work/ops/2d/texture/cooc_feature_matrix.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`sk_lbp`](https://furuse.work/ops/2d/texture/sk_lbp.html)

## No.2026.079 —— 混合廃棄物の材質選別 —— 何が消えるかは前処理の代数で決まる

[![混合廃棄物の材質選別 —— 何が消えるかは前処理の代数で決まる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_recycling_sorting/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_recycling_sorting/01_scene.png)

*↑ **混合廃棄物の材質選別 —— 何が消えるかは前処理の代数で決まる** ―― ベルト上の破片に材質・汚れ・濡れ・傾き・重なりを既知の量で仕込み、SWIR 64 バンドで分けます。破片ごとの劣化は s(λ)=g·R(λ)·exp(-w·A_w(λ))+(a·u(λ)+c) という閉形式なので、どの前処理が何に不変かが先に分かります —— 分光角は乗算 g に不変(乗算汚れ 0→0.8 で 0.995→0.990、傾き 0→70° で 0.993)、2 階微分は 1 次式 a·u+c を消す(加算 0→0.6 で生 SAM 0.995→0.827 に対し 2 次微分は全水準 0.995)。予想は 2 つ外れました: 濡れは 2 次微分でほとんど消せて(生 SAM 0.282 に対し 0.818)、理由は 2 階微分がガウス帯を 1/σ² で重みづけるから((43/70)²=0.37 倍)。連続体除去は加算が弱いうちは勝つ(0.983 対 0.865)のに強いと逆転する(0.736 対 0.827)。特徴の無い金属は微分で消え(再現率 0.06)、平坦度の門で 0.98 に戻ります。*

[![PP と PE は骨格が同じ(-CH2-)なのでわざと似せてある。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_recycling_sorting/02_library_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_recycling_sorting/02_library.png)

*↑ 測定の図 ―― PP と PE は骨格が同じ(-CH2-)なのでわざと似せてある。*

[![乗算汚れ・傾き・重なりは平ら(SAM は明るさに不変)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_recycling_sorting/03_sweep_raw_sam_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_recycling_sorting/03_sweep_raw_sam.png)

*↑ 乗算汚れ・傾き・重なりは平ら(SAM は明るさに不変)。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_recycling_sorting/06_sweep_detection_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_recycling_sorting/06_sweep_detection.png)

*↑ この回の図*

[![1 個の正解率には出ない盲点がここに出る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_recycling_sorting/09_confusion_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_recycling_sorting/09_confusion.png)

*↑ 1 個の正解率には出ない盲点がここに出る。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_recycling_sorting/12_mixed_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_recycling_sorting/12_mixed_map.png)

*↑ この回の図*

```
py -3.11 examples/poc_recycling_sorting.py
```

ソース: [examples/poc_recycling_sorting.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_recycling_sorting.py)

この回が作った図は全部で **14 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_recycling_sorting)

使用 op(ノートへ): [`overlay_labels`](https://furuse.work/ops/annotate/overlay/overlay_labels.html) · [`spectrum`](https://furuse.work/ops/oned/signal/spectrum.html)

## No.2026.084 —— 太陽電池セルの EL 画像から発電損失を推定する ―― 「暗い = 不活性」ではない

[![太陽電池セルの EL 画像から発電損失を推定する ―― 「暗い = 不活性」ではない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_el_inspection/01_zero_point_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_el_inspection/01_zero_point_map.png)

*↑ **太陽電池セルの EL 画像から発電損失を推定する ―― 「暗い = 不活性」ではない** ―― 結晶シリコンセル(フィンガー 100 本・バスバー 3 本・結晶粒 70 個)の EL 画像を閉形式で合成し、孤立領域(真値 4.77 %)・クラック 5 本・断線 8 本を植えて cos^4 ビネッティングと光子雑音で観測した。ゼロ点の大域しきい値は暗画素率 21.7 % を不活性面積率と呼ぶが、その 42 % はフィンガー/バスバー、33 % は結晶粒とビネッティングで、本物の不活性領域は 20 %。行・列プロファイルで格子を割り、種別ごとの門で取ると面積率 4.61 %(誤差 -0.15 ポイント)、クラック再現率 0.88〜1.00、断線 8/8。sk_frangi は画像ごとの最大値で正規化するので、校正線は画像中でいちばん強くないと尺度を固定できず(実クラックと同じ線は応答 0.69、幅 3 px の強い線は 1.00)、校正なしは欠陥ゼロの良品で偽クラック 147 px を出す。結晶粒コントラスト c=0.24 から偽クラックと帯の飲み込みが同時に始まり、クラック幅の崖 1.25 px は「幅 × 深さ」の線形則(予測 1.38 px)で読める。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_el_inspection/02_by_type_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_el_inspection/02_by_type.png)

*↑ 測定の図*

[![孤立領域 2 つ・クラック 5 本・断線 8 本。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_el_inspection/03_scene_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_el_inspection/03_scene_map.png)

*↑ 孤立領域 2 つ・クラック 5 本・断線 8 本。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_el_inspection/04_frangi_norm_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_el_inspection/04_frangi_norm.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_el_inspection/06_crack_width_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_el_inspection/06_crack_width.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_el_inspection/07_vignette_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_el_inspection/07_vignette.png)

*↑ この回の図*

```
py -3.11 examples/poc_solar_el_inspection.py
```

ソース: [examples/poc_solar_el_inspection.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_solar_el_inspection.py)

この回が作った図は全部で **8 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_solar_el_inspection)

使用 op(ノートへ): [`aug_vignette`](https://furuse.work/ops/2d/augmentation/aug_vignette.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_select`](https://furuse.work/ops/blob/select/blob_select.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`gray_closing`](https://furuse.work/ops/2d/morphology/gray_closing.html) · [`hysteresis_threshold`](https://furuse.work/ops/2d/segmentation/hysteresis_threshold.html) · [`lines_gauss`](https://furuse.work/ops/2d/contour/lines_gauss.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`sk_frangi`](https://furuse.work/ops/2d/texture/sk_frangi.html) · [`sk_skeleton`](https://furuse.work/ops/2d/region/sk_skeleton.html) · [`total_length`](https://furuse.work/ops/2d/features/total_length.html) · [`vignette`](https://furuse.work/ops/gfx2d/post/vignette.html)

## No.2026.085 —— はんだフィレットの AOI ―― 3 リング照明は傾きの 3 段量子化器で、高さの 7 割は暗部にある

[![はんだフィレットの AOI ―― 3 リング照明は傾きの 3 段量子化器で、高さの 7 割は暗部にある](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solder_fillet_aoi/02_scene_grid_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solder_fillet_aoi/02_scene_grid.png)

*↑ **はんだフィレットの AOI ―― 3 リング照明は傾きの 3 段量子化器で、高さの 7 割は暗部にある** ―― 1608 チップのパッド・電極と、接触角と断面積で決まる円弧のフィレットを仕込み、仰角の違う 3 リング(赤 30-40°、緑 15-30°、青 0-15°)の応答を GGX で積分して合成した AOI 画像で、良品 / 不足 / ブリッジ / 浮きを判定する。接触角 18° の凹円弧は壁で 72° まで立つので、いちばん低いリングでも見えるのは高さの 28.8 %(予測)―― 色帯の傾きを積分する素朴な推定は真値の 0.284 倍にしかならない。色が変わる位置から円弧を壁まで外挿すると自由円弧で +1.7 % ± 5.3 % に収まるが、はんだ量が増えて爪先がパッド端に固定されると -42.3 % まで外れる。部品の位置ずれ 0.16 mm で爪先の傾きが 30° を超えて緑帯が消え、真値の高さは上がっているのに良品が「不足」になる(予測 0.16 mm、真値が不足になるのは 0.28 mm)。表面粗さは予想と違い暗部の縁を動かさず、粗さ 0.5 で赤帯の消失と同時に壊れて 0.6 で全体が暗部に落ちる。パッド平均色 ΔE のゼロ点は基準条件で 100 % 当たるが、ずれ・粗さ・むらを混ぜると良品 56 % / ブリッジ 68 % を NG にして区別しておらず、円弧推定の判定は良品 98 % / 不足 98 % / ブリッジ 100 % / 浮き 88 %(取りこぼしは持ち上がり角 8.7〜11.0°)。*

[![鏡面なら窓の端が階段になる。傾き 40° を超えるとどのリングも届かない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solder_fillet_aoi/01_ring_lut_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solder_fillet_aoi/01_ring_lut.png)

*↑ 測定の図 ―― 鏡面なら窓の端が階段になる。傾き 40° を超えるとどのリングも届かない。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solder_fillet_aoi/03_tilt_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solder_fillet_aoi/03_tilt_map.png)

*↑ この回の図*

[![E1 は 0.28 倍の直線に乗る(暗部を見ていない)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solder_fillet_aoi/05_volume_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solder_fillet_aoi/05_volume_sweep.png)

*↑ E1 は 0.28 倍の直線に乗る(暗部を見ていない)。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solder_fillet_aoi/08_shift_verdict_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solder_fillet_aoi/08_shift_verdict.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solder_fillet_aoi/10_ring_lut_rough_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solder_fillet_aoi/10_ring_lut_rough.png)

*↑ この回の図*

```
py -3.11 examples/poc_solder_fillet_aoi.py
```

ソース: [examples/poc_solder_fillet_aoi.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_solder_fillet_aoi.py)

この回が作った図は全部で **12 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_solder_fillet_aoi)

使用 op(ノートへ): [`access_channel`](https://furuse.work/ops/2d/color/access_channel.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_select_largest`](https://furuse.work/ops/blob/select/blob_select_largest.html) · [`brdf_microfacet`](https://furuse.work/ops/specular/reflectance/brdf_microfacet.html) · [`illumination_design`](https://furuse.work/ops/optics/illumination/illumination_design.html) · [`intensity`](https://furuse.work/ops/2d/features/intensity.html) · [`rgb_to_lab`](https://furuse.work/ops/imgmetrics/colorspace/rgb_to_lab.html) · [`trans_from_rgb`](https://furuse.work/ops/2d/color/trans_from_rgb.html)

## No.2026.121 —— 工程は管理下か、そして能力はあるか ―― 閉じた式だけで読む統計的工程管理

[![工程は管理下か、そして能力はあるか ―― 閉じた式だけで読む統計的工程管理](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_spc/01_spc_xbar_chart_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_spc/01_spc_xbar_chart.png)

*↑ **工程は管理下か、そして能力はあるか ―― 閉じた式だけで読む統計的工程管理** ―― マシンビジョンが測った寸法・欠陥数の系列を、学習を一切使わない 4 つの SPC op(すべて教科書の閉じた式で、突き合わせる厳密な恒等式を持つ)に繋いだ図。Xbar-R 管理図は末尾に入れた +4σ のずれを 4 群ぶん即座に捕らえ(n=5 の定数 A2/D3/D4 = 0.577/0.000/2.115、ISO 8258)、CUSUM は Shewhart 3σ が 1 件も鳴らさない +0.8σ の持続ドリフトを #45(ドリフト開始直後)で捕らえる。工程能力は中心が仕様中点なら Cpk = Cp = 1.307、中心を +1 ずらすと Cpk = 0.981 < Cp と「能力はあるが今の中心では出せていない」を分けて示す。多変量 T² は相関する 3 計測の同時ドリフトを 1 判定にまとめる(UCL は F 分布由来)。「絵が良くなること」と同じで、工程が回っていることと管理下にあることは別々に測る。*

[![Shewhart 3σ は 0 件、CUSUM は #46(ドリフト開始の直後)で h=5 を超えて警報。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_spc/02_spc_cusum_chart_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_spc/02_spc_cusum_chart.png)

*↑ 測定の図 ―― Shewhart 3σ は 0 件、CUSUM は #46(ドリフト開始の直後)で h=5 を超えて警報。*

```
py -3.11 examples/poc_spc.py
```

ソース: [examples/poc_spc.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_spc.py)

この回が作った図は全部で **2 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_spc)

使用 op(ノートへ): [`spc_capability`](https://furuse.work/ops/spc/capability/spc_capability.html) · [`spc_cusum`](https://furuse.work/ops/spc/change/spc_cusum.html) · [`spc_ewma`](https://furuse.work/ops/spc/change/spc_ewma.html) · [`spc_hotelling_t2`](https://furuse.work/ops/spc/multivariate/spc_hotelling_t2.html) · [`spc_mt_distance`](https://furuse.work/ops/spc/mt/spc_mt_distance.html) · [`spc_mt_sn_ratio`](https://furuse.work/ops/spc/mt/spc_mt_sn_ratio.html) · [`spc_mt_unit_space`](https://furuse.work/ops/spc/mt/spc_mt_unit_space.html) · [`spc_xbar_r`](https://furuse.work/ops/spc/chart/spc_xbar_r.html)

## No.2026.152 —— どのセンサーも正常値なのに、設備は異常 ―― MT 法が単変量 3σ の見逃しを拾う量

[![どのセンサーも正常値なのに、設備は異常 ―― MT 法が単変量 3σ の見逃しを拾う量](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mt_hidden_fault/01_mt_hidden_cloud_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mt_hidden_fault/01_mt_hidden_cloud.png)

*↑ **どのセンサーも正常値なのに、設備は異常 ―― MT 法が単変量 3σ の見逃しを拾う量** ―― 設備保全 PoC(振動・熱・形状の 3 センサ、20 特徴量)の健全 48 本を MT 法(マハラノビス・タグチ)の単位空間にし、健全の別標本 32 本で「単変量 max|z|」と「MD」の閾値を両方とも誤警報 0 に揃えて比べた図。健全な設備では特徴量どうしが強く相関する(継手温度と全体温度で ρ=0.999)ので、相関が壊れた標本は各特徴量が正常範囲のままでも距離では遠い。単変量が『全特徴量とも正常範囲』と言った 169 標本のうち MT 法は 79 本(47 %)を異常と言う。散布図の左上(単変量の閾値より左・MT の閾値より上)がその領域。恒等式は 2 つ: 単位空間の MD² 平均 = (N−1)/N(ddof=1 の定義から厳密)、2 特徴で点 (+z, −z) の MD² = z²/(1−ρ)(閉形式)。慣習の |z|>3 は 20 特徴では偶然に 12.5 % 鳴る。軽い故障は正常(0)と故障(1)の線形内挿 ―― 元 PoC の「重症度 × 故障値」は軽い側で正常より静かで冷たい別の異常になり、検出率が重症度に単調でなかった。素材は合成で、この割合はこの相関構造の上界。*

[![芯ずれ。差が最大なのは重症度 0.05 で、単変量 25.0 % に対し MT 法 100.0 %。重症度 0.50 以上は両方式とも 100 %。閾値は健全の別標本 32 本で両方式とも誤警報 0。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mt_hidden_fault/02_mt_vs_univariate_misalignment_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mt_hidden_fault/02_mt_vs_univariate_misalignment.png)

*↑ 測定の図 ―― 芯ずれ。差が最大なのは重症度 0.05 で、単変量 25.0 % に対し MT 法 100.0 %。重症度 0.50 以上は両方式とも 100 %。閾値は健全の別標本 32 本で両方式とも誤警報 0。*

[![アンバランス。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mt_hidden_fault/03_mt_vs_univariate_unbalance_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mt_hidden_fault/03_mt_vs_univariate_unbalance.png)

*↑ アンバランス。*

[![軸受外輪傷。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mt_hidden_fault/04_mt_vs_univariate_bearing_outer_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mt_hidden_fault/04_mt_vs_univariate_bearing_outer.png)

*↑ 軸受外輪傷。*

[![潤滑不良。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mt_hidden_fault/05_mt_vs_univariate_lubrication_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mt_hidden_fault/05_mt_vs_univariate_lubrication.png)

*↑ 潤滑不良。*

[![ゆるみ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mt_hidden_fault/06_mt_vs_univariate_looseness_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mt_hidden_fault/06_mt_vs_univariate_looseness.png)

*↑ ゆるみ。*

```
py -3.11 examples/poc_mt_hidden_fault.py
```

ソース: [examples/poc_mt_hidden_fault.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_mt_hidden_fault.py)

この回が作った図は全部で **6 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_mt_hidden_fault)

使用 op(ノートへ): [`spc_mt_distance`](https://furuse.work/ops/spc/mt/spc_mt_distance.html) · [`spc_mt_unit_space`](https://furuse.work/ops/spc/mt/spc_mt_unit_space.html)

## No.2026.155 —— 文字はどこにあるか、を学習なしで ―― 描いた文字を真値に、ストローク幅の検出器を採点する

[![文字はどこにあるか、を学習なしで ―― 描いた文字を真値に、ストローク幅の検出器を採点する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_text_region_truth/01_text_region_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_text_region_truth/01_text_region_scene.png)

*↑ **文字はどこにあるか、を学習なしで ―― 描いた文字を真値に、ストローク幅の検出器を採点する** ―― fullseye は OCR の前処理までで止まり「どこに文字があるか」を出す層が無かった。認識器(学習済みモデル)は載せない方針なので、文字の幾何 ―― ストロークの幅がほぼ一定 ―― だけで領域を出す古典(Stroke Width Transform、Epshtein 2010)を 3 op にし、自分でフォント描画した文字(インク画素が 1 px 単位で既知)で採点した図。真値は 3 つ: 幅 w の矩形ストロークで SWT = w が全画素で厳密(エッジを文字側の内側境界画素と定め、幅 = 向かい合う境界画素の中心間距離 + 1 という規約で整数になる)、2 倍拡大で中央値 5 → 10、描いたインクのうち候補矩形に入った割合(再現率)。Latin は size ≥ 32 でインク再現率 80〜90 %、CJK(漢字・かな)は 60〜79 %、矩形の精度は約 50 %(矩形は字の余白を含む)。文字の大きさ 6 段 × 雑音 4 段の表で、落ちるのは雑音でなく小さい字(size 16 の落ち込みは 12 より低く未解明として印字)。CJK フォントが無い環境ではラテン文字だけで回り、その旨を印字する。*

[![真値は描いたインク画素。再現率 = インクのうち候補矩形に入った割合。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_text_region_truth/02_text_region_coverage_latin_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_text_region_truth/02_text_region_coverage_latin.png)

*↑ 測定の図 ―― 真値は描いたインク画素。再現率 = インクのうち候補矩形に入った割合。*

[![真値は描いたインク画素。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_text_region_truth/03_text_region_coverage_cjk_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_text_region_truth/03_text_region_coverage_cjk.png)

*↑ 真値は描いたインク画素。*

```
py -3.11 examples/poc_text_region_truth.py
```

ソース: [examples/poc_text_region_truth.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_text_region_truth.py)

この回が作った図は全部で **3 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_text_region_truth)

使用 op(ノートへ): [`swt_map`](https://furuse.work/ops/text/stroke/swt_map.html) · [`text_candidates`](https://furuse.work/ops/text/detect/text_candidates.html) · [`text_lines`](https://furuse.work/ops/text/layout/text_lines.html)

## No.2026.042 —— カメラの熱ドリフトが寸法計測に効く量

[![カメラの熱ドリフトが寸法計測に効く量](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_drift_metrology/04_error_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_drift_metrology/04_error_maps.png)

*↑ **カメラの熱ドリフトが寸法計測に効く量** ―― 温度 ΔT で焦点距離・架台・主点が漂うカメラで一辺 40 mm のワークを測り、誤差を半径の 1 次式 a + b·R に分けた図。ΔT = 15 K で定数項 a = +224.5 ppm(片方だけ動かした対照条件 +225.3 ppm)。雑音の床(25 枚平均で 23 ppm)を超えるのは ΔT = 1.6 K から ―― それ以下では「温度の影響は見えない」が正しい報告。*

[![焦点距離ドリフトは R に依らない。主点ドリフトは R に比例(歪みを外す中心がずれるため)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_drift_metrology/01_separate_drifts_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_drift_metrology/01_separate_drifts.png)

*↑ 測定の図 ―― 焦点距離ドリフトは R に依らない。主点ドリフトは R に比例(歪みを外す中心がずれるため)。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_drift_metrology/02_countermeasures_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_drift_metrology/02_countermeasures.png)

*↑ この回の図*

[![周辺のワークのほうが感度が高い。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_drift_metrology/03_budget_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_drift_metrology/03_budget.png)

*↑ 周辺のワークのほうが感度が高い。*

```
py -3.11 examples/poc_thermal_drift_metrology.py
```

ソース: [examples/poc_thermal_drift_metrology.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_thermal_drift_metrology.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_thermal_drift_metrology)

使用 op(ノートへ): [`polygon_area`](https://furuse.work/ops/drive/japan/polygon_area.html)

## No.2026.113 —— 熱画像は温度画像ではない ―― 放射率・反射・透過を取り違えたまま「温度」と呼ぶ

[![熱画像は温度画像ではない ―― 放射率・反射・透過を取り違えたまま「温度」と呼ぶ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/15_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/15_scene.png)

*↑ **熱画像は温度画像ではない ―― 放射率・反射・透過を取り違えたまま「温度」と呼ぶ** ―― 熱カメラの DN を温度に戻す**全経路**を、真値を自分で植てて測る。前向きモデルは `L = τ[ε L_bb(T_obj) + (1-ε) L_bb(T_refl)] + (1-τ) L_bb(T_atm)`。★**床を先に測る**: 往復 1.75e-06 K、量子化 6.28e-03 K、+NETD 2.71e-02 K。**350.0 K では厳密に 0 が出たが、それは校正表の節点にたまたま乗っただけ**なので、節点を外して測り直した —— **0 を床と呼ぶのは嘘**になる。★★**閉形式の予測を印字して、外した**: 素朴な `n = c2/(λ_eff T)` は数値微分から最大 **16.6 %** ずれる。外れの正体は実効波長の選び方ではなく **`e^x/(e^x-1)` の欠け**(x = c2/λT)で、入れると誤差 **0.00 %**。MWIR 300 K は x=10.9 でほぼ Wien、LWIR 800 K は x=1.80 で Rayleigh–Jeans 寄り。★★**崖の向きも外した**: 「低温ほど急」と印字したが、**絶対誤差は高温ほど大きい**(Δε/ε=5 % で 305 K の 0.233 K → 800 K の **16.907 K**)。log-log の傾きは実測 **2.717**、内訳は T/n = 1.741 + 反射因子 0.977 = 2.718 —— **閉形式は最初からそう言っていて、自分の式を読み違えていた**。★★**「低温ほど急」は正しかったが、犯人が違った**: 周囲からの上昇 (T_obj - T_refl) で割ると、放射率の誤差は 4.7 % → 3.4 % と **1.40 倍しか動かず発散しない**(Δε/ε に収束する)。発散するのは **T_refl の取り違え**のほうで 13.2 % → 0.0 %(**972 倍**)。上昇 10 K を切ると、反射が放射率より重くなる。★★**不確かさは足し算にならない**。ε=0.60±0.05・T_refl=300±5 K・相関 ρ=+0.7 という現実的な組を 20000 試行で数えると、**「95 % 区間」が実際に真値を包む割合は 独立 RSS で 88.03 %、相関つき Monte Carlo で 94.44 %**(-6.4 点)。★**床を先に測ってある**: ρ=0 なら RSS 95.03 % / MC 94.52 % なので、この落差は実装ではなく**相関を無視したことそのもの**。真の u 5.6518 K に対し RSS は 4.5086 K = **区間が 20.2 % 狭い**。取りこぼしは片側に寄る(下 7.14 % / 上 4.83 %)。ρ=-0.7 なら逆に 99.64 % と**過剰**になる —— **独立と仮定することは、安全側でも危険側でもなく『分からない側』**。★★**guard band(合否判定)**: 40000 試行(真値 65〜95 ℃ 一様)で、**誤合格 8.03 %(不確かさ無視)→ 0.81 %(RSS)→ 0.14 %(相関つき MC)**。**RSS は MC の 5.6 倍 誤合格する**。誤不合格は 6.69 → 28.22 → 40.03 % で、MC の band が広いのは相関だけでなく**分布の歪み**の分もある(対称 1.96u なら 11.08 K、上側 97.5 百分位は 13.47 K)。★**単位の崖**は 8 通りで例外 3 / 静かに 5。★**同じ「T_refl を摂氏で書く」取り違えが、ε=0.95 では静かに通り(-22.1 K)、ε=0.10 では例外になる** —— **止まるかどうかは間違いの種類ではなく場面で決まる**。静かな側は DN 平均→温度(+1.543 K、Jensen)、見かけ温度(-2.121 K)、τ 二重掛け(+2.485 K)、ΔT/T をセ氏(感度を 1/4.46 に過小評価)。★**熱画像そのもの**: 同じ 375.0 K のボルト(ε=0.10)が、ε=1 の絵では周りの塗装面より **62.3 K 低く**写る(309.7 K 対 372.0 K)—— 発熱部の真上が**いちばん健全に見える**。ε 地図で 375.0 K に復帰(残差 rms 0.106 K)するが、★**補正は偏りを消す代わりに雑音を増やす**: 残差 rms は塗装面 0.0571 K に対しボルト **0.3673 K(6.4 倍)**。ε の比 9.5 より小さいのは、ボルトの DN が低くて光子雑音も小さいから —— **2 つの効き方が逆向き**。★★**道具の穴を見つけて、その場で直した**: `fs.noise_sigma(method='mad')` は整数値の画像で **σ=0.5 相当のとき 0.0000** を返し、返せる値は 1.4826 の倍数だけ(σ=1.0 も σ=1.983 も同じ 1.4826)。14 bit の生 DN はまさに整数。**下流はもっと悪く、200x200 の整数フレームに植えた点目標 2 個を `star_detect` が 0 個**と返していた。`star_detect` には `σ≤0` の門が**在った**のに、コメントが「完全に平坦 = 雑音が測れない」と書いていて**前提のほうが誤り**だった。しかも `clip` 法の存在はコード内コメントに書かれていた —— **知識は在ったが、読む側(docstring と既定値)に無かった**。いまは `noise_sigma` が警告、`star_detect` は**平坦なら空・平坦でなければ拒否**。`clip` に替えれば植えた 2 個がちゃんと出る。*

[![LWIR・350 K・ε=0.95。校正表と直接積分の相対差は最大 8.9e-16。以下の誤差はすべてこの床の上。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/01_floor_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/01_floor.png)

*↑ 測定の図 ―― LWIR・350 K・ε=0.95。校正表と直接積分の相対差は最大 8.9e-16。以下の誤差はすべてこの床の上。*

[![n = d ln L_bb/d ln T。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/02_planck_index_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/02_planck_index.png)

*↑ n = d ln L_bb/d ln T。*

[![LWIR・T_obj = 350 K・T_refl = 300 K。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/06_cliff_curves_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/06_cliff_curves.png)

*↑ LWIR・T_obj = 350 K・T_refl = 300 K。*

[![20000 試行 / 点。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/10_coverage_rho_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/10_coverage_rho.png)

*↑ 20000 試行 / 点。*

[![止まるのは校正表の範囲外に落ちたときだけ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/14_units_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/14_units.png)

*↑ 止まるのは校正表の範囲外に落ちたときだけ。*

```
py -3.11 examples/poc_thermal_radiometry.py
```

ソース: [examples/poc_thermal_radiometry.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_thermal_radiometry.py)

この回が作った図は全部で **18 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_thermal_radiometry)

使用 op(ノートへ): [`beer_lambert_transmittance`](https://furuse.work/ops/optics/glassbody/beer_lambert_transmittance.html) · [`interp_linear`](https://furuse.work/ops/math/interp_poly/interp_linear.html) · [`mat_eigh`](https://furuse.work/ops/math/linalg/mat_eigh.html) · [`noise_sigma`](https://furuse.work/ops/astrostack/quality/noise_sigma.html) · [`photon_uncertainty`](https://furuse.work/ops/photon/counting/photon_uncertainty.html) · [`poly_fit`](https://furuse.work/ops/math/interp_poly/poly_fit.html) · [`stat_correlation`](https://furuse.work/ops/math/stats/stat_correlation.html) · [`stat_covariance`](https://furuse.work/ops/math/stats/stat_covariance.html) · [`stat_describe`](https://furuse.work/ops/math/stats/stat_describe.html) · [`stat_histogram`](https://furuse.work/ops/math/stats/stat_histogram.html)

## No.2026.043 —— パルスサーモグラフィで内部欠陥の深さを測る

[![パルスサーモグラフィで内部欠陥の深さを測る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/02_depth_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/02_depth_map.png)

*↑ **パルスサーモグラフィで内部欠陥の深さを測る** ―― フラッシュ加熱後の表面温度を 1 次元熱伝導の厳密解で作り、剥離の深さを画像から当てる図。直径が深さの 4 倍以上なら数 % で当たるが、深さ 0.5 mm・直径 2 mm では +627 %。原因は横拡散ではなく当てはめる時間窓で、窓を 25 s → 4 s に切り詰めると -9 % に戻る。*

[![右下三角(直径が深さの 4 倍以上)は数 %。左上は横拡散で壊れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/01_depth_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/01_depth_table.png)

*↑ 測定の図 ―― 右下三角(直径が深さの 4 倍以上)は数 %。左上は横拡散で壊れる。*

[![早期の勾配は -1/2。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/03_tsr_curves_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/03_tsr_curves.png)

*↑ 早期の勾配は -1/2。*

```
py -3.11 examples/poc_thermography_ndt.py
```

ソース: [examples/poc_thermography_ndt.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_thermography_ndt.py)

この回が作った図は全部で **3 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_thermography_ndt)



## No.2026.047 —— 迷光がコントラスト計測を壊す ―― MTF 合格・黒レベル不合格は両立する

[![迷光がコントラスト計測を壊す ―― MTF 合格・黒レベル不合格は両立する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_veiling_glare/04_glare_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_veiling_glare/04_glare_scene.png)

*↑ **迷光がコントラスト計測を壊す ―― MTF 合格・黒レベル不合格は両立する** ―― PSF の裾だけを重くした像で、刃のエッジの MTF と黒四角の黒レベルを同時に測った図。裾の割合 0 → 0.20 で MTF50 は 0.2347 → 0.2249 cyc/px(-4.2 %、合格のまま)なのに、黒レベルは 0.0 → 15.7 %(不合格)。±16 px の測定窓には裾のエネルギーの 6 % しか入らない ―― 迷光は測る範囲を宣言しないと数字にならない。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_veiling_glare/01_verdict_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_veiling_glare/01_verdict.png)

*↑ 測定の図*

[![D を 16 倍にすると 19.6 % が 4.5 % になる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_veiling_glare/02_window_dependence_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_veiling_glare/02_window_dependence.png)

*↑ D を 16 倍にすると 19.6 % が 4.5 % になる。*

[![全 PSF の MTF と正弦チャートの絶対コントラストは 0.80 の台地を見る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_veiling_glare/03_mtf_curves_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_veiling_glare/03_mtf_curves.png)

*↑ 全 PSF の MTF と正弦チャートの絶対コントラストは 0.80 の台地を見る。*

```
py -3.11 examples/poc_veiling_glare.py
```

ソース: [examples/poc_veiling_glare.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_veiling_glare.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_veiling_glare)

使用 op(ノートへ): [`airy_pattern`](https://furuse.work/ops/optics/wave/airy_pattern.html) · [`create_funct_1d_pairs`](https://furuse.work/ops/oned/function/create_funct_1d_pairs.html) · [`derivate_funct_1d`](https://furuse.work/ops/oned/function/derivate_funct_1d.html) · [`edge_spread`](https://furuse.work/ops/optics/imaging/edge_spread.html) · [`get_y_value_funct_1d`](https://furuse.work/ops/oned/function/get_y_value_funct_1d.html) · [`invert_funct_1d`](https://furuse.work/ops/oned/function/invert_funct_1d.html) · [`mtf50`](https://furuse.work/ops/optics/imaging/mtf50.html) · [`mtf_diffraction`](https://furuse.work/ops/optics/imaging/mtf_diffraction.html) · [`psf_to_mtf`](https://furuse.work/ops/optics/imaging/psf_to_mtf.html) · [`sfr_from_edge`](https://furuse.work/ops/optics/imaging/sfr_from_edge.html) · [`veiling_glare_index`](https://furuse.work/ops/optics/imaging/veiling_glare_index.html)

## No.2026.178 —— カメラを買わずにカメラを測る ―― EMVA 1288 の手順で、既知の値を仕込んだセンサから量子効率・ゲイン・暗雑音を取り戻す

[![カメラを買わずにカメラを測る ―― EMVA 1288 の手順で、既知の値を仕込んだセンサから量子効率・ゲイン・暗雑音を取り戻す](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/01_photon_transfer.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/01_photon_transfer.gif)

*↑ **カメラを買わずにカメラを測る ―― EMVA 1288 の手順で、既知の値を仕込んだセンサから量子効率・ゲイン・暗雑音を取り戻す** ―― カメラのデータシートにある量子効率 η・システムゲイン K・暗雑音 σ_d・飽和・SNR・ダイナミックレンジ・DSNU・PRNU は、EMVA 1288 Release 4.0 Linear(= ISO 24942)の手順で出した数である。この展示は**物理モデルでセンサを合成**し(光子のポアソン → 電子 → 暗雑音・暗電流 → K 倍 → 量子化・飽和、列・行・画素の DSNU と PRNU の模様つき)、新しい op 族 sensorchar(10 op)の**規格の推定手順**で仕込んだ値を取り戻す。合成と推定は別の式。門: 復元 —— 同じ露光で 2 枚ずつ撮った平均と時間分散(式 16・18)の photon transfer(式 50)から K -0.66 %、暗画像から σ_d +0.13 %(式 53)、応答の傾きから η +0.67 %(式 52)、暗電流 +0.6 %、列・行・画素の空間分散(式 42)と DSNU +0.6 %・PRNU -0.1 % / 恒等式 —— SNR(μ_p.min) = 1(式 26 と 21 は独立)・理想センサ = √μ_p(式 23)を機械精度、傾き 1 → 1/2(式 22)/ 適用範囲 —— 暗画像の分散が 0.24 DN² 未満では σ_d を推定しない(式 53・54)が、平らなセンサでは本当に推定の壊れる境界 / 公表値 —— メーカーが公表した EMVA 1288 データ 38 型番で最大 SNR = √μ_e.sat(式 55)が全型番 0.49 dB 以内 / 直線性 —— 直線性の誤差(式 58〜63)の閉形式が独立の重みつき最小二乗と 3.9e-13 / 欠陥画素 —— 仕込んだ 9 個を数え直す。見つけたこと: σ_d を photon transfer の**切片**から出すと +53.5 %(規格は暗画像から直接)。DSNU の模様があると画素ごとの暗レベルのずれが量子化のディザになり、規格が「推定できない」とする K = 0.10 でも 0.7 %(平ら 29.8 %)—— 規格の境界は保守側。台帳の IMX287 は飽和 21.0 ke⁻・暗雑音 7 e⁻ からは DR 68.9 dB なのに台帳は 74 dB —— どちらかの欄が別条件の値と見られる(未確認、台帳は直さず門で名指し)。正直に: 合成センサ、高域フィルタ(8.1 節)と直線性の B-スプライン検査(式 51)は入れていない、公表値は整数に丸めた値で K が無いので DR の検算は量子化雑音を 0 とみなす。8 門、0.1 s。*

[![SNR は暗い側で傾き 1(暗雑音が支配)、明るい側で傾き 1/2(光子雑音が支配)。SNR = 1 になる露光が絶対感度しきい値 μ_p.min = 6.8 光子。量子化雑音の分だけ μ_e.min = 4.20 e⁻ は暗雑音 3.4 ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/02_snr_curve_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/02_snr_curve.png)

*↑ 測定の図 ―― SNR は暗い側で傾き 1(暗雑音が支配)、明るい側で傾き 1/2(光子雑音が支配)。SNR = 1 になる露光が絶対感度しきい値 μ_p.min = 6.8 光子。量子化雑音の分だけ μ_e.min = 4.20 e⁻ は暗雑音 3.4 e⁻ より大きい。*

[![暗画像の分散が 0.24 DN² より小さいと、規格は σ_d を推定しない(式 53・54)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/03_validity_boundary_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/03_validity_boundary.png)

*↑ 暗画像の分散が 0.24 DN² より小さいと、規格は σ_d を推定しない(式 53・54)。*

[![メーカーが公表した EMVA 1288 データ 38 型番の飽和容量・暗雑音・量子効率から式 (28) で DR を出し直す。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/04_datasheet_dynamic_range_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/04_datasheet_dynamic_range.png)

*↑ メーカーが公表した EMVA 1288 データ 38 型番の飽和容量・暗雑音・量子効率から式 (28) で DR を出し直す。*

```
py -3.11 examples/poc_emva1288_sensor.py
```

ソース: [examples/poc_emva1288_sensor.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_emva1288_sensor.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_emva1288_sensor)

使用 op(ノートへ): [`emva_dark_current`](https://furuse.work/ops/optics/sensorchar/emva_dark_current.html) · [`emva_defect_pixels`](https://furuse.work/ops/optics/sensorchar/emva_defect_pixels.html) · [`emva_dynamic_range`](https://furuse.work/ops/optics/sensorchar/emva_dynamic_range.html) · [`emva_linearity_error`](https://furuse.work/ops/optics/sensorchar/emva_linearity_error.html) · [`emva_pair_statistics`](https://furuse.work/ops/optics/sensorchar/emva_pair_statistics.html) · [`emva_photon_transfer`](https://furuse.work/ops/optics/sensorchar/emva_photon_transfer.html) · [`emva_quantum_efficiency`](https://furuse.work/ops/optics/sensorchar/emva_quantum_efficiency.html) · [`emva_sensitivity_threshold`](https://furuse.work/ops/optics/sensorchar/emva_sensitivity_threshold.html) · [`emva_snr_curve`](https://furuse.work/ops/optics/sensorchar/emva_snr_curve.html) · [`emva_spatial_nonuniformity`](https://furuse.work/ops/optics/sensorchar/emva_spatial_nonuniformity.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html)

## No.2026.114 —— 搬送ロールの傷を周期から名指しする ―― 崖に着く前に、何も言えなくなる

[![搬送ロールの傷を周期から名指しする ―― 崖に着く前に、何も言えなくなる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_web_roll_periodicity/01_scene_web_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_web_roll_periodicity/01_scene_web.png)

*↑ **搬送ロールの傷を周期から名指しする ―― 崖に着く前に、何も言えなくなる** ―― フィルム・電池電極・銅箔・紙のロール to ロールでは、搬送ロールの傷 1 か所がその周長ごとに web へ転写される。欠陥地図の流れ方向スペクトルから周長を測り、πD の台帳と突き合わせて犯人を名指しできるか。★★素朴に「スペクトルの最大値」を読むと、**実在する無実のロールを名指しする** —— インパルス列の櫛では高調波が基本波と同じ高さなので最大値は C/2 = 235.62 mm を掴み、それが台帳の冷却ロール(314.16 mm)に落ちる。無い周長を答えるなら気づけるが、台帳の中の別の 1 本を指すので報告がそのまま通る。★同じ誤差は見逃し率 0 → 50 % を通して 235.9 mm のまま動かない —— **誤差が一定なのは頑健さの証拠ではない**(同じ間違いを続けているだけ)。対策は k=1..3 の高調波が全部立つ最低周波数を採る fail-closed の櫛法。★ゼロ点(欠陥の MD 間隔)は検出が完璧なら当たる(中央値の誤差 -0.03 mm)。見逃し 40 % で中央値 472.1 mm・平均 813.5 mm に対し櫛法は 3.2 mm —— **見逃しは位相を飛ばさない**(抜けた山は振幅を減らすだけ)。平均は clutter に、中央値は見逃しに弱く、どちらの弱点も櫛法には無い。★対照群(蛇行 25 mm)を補正しないと1 本のロールの欠陥列が CD で 2 本に割れる(レーンに残る周期欠陥 100 → 44 %)が、MD スペクトルはビット単位で無傷 —— 蛇行が壊すのは「CD でレーンを切ってから数える」手法だけ。★健全ロールだけ 60 試行で偽陽性 1.7 %。床は 0 でなく、健全側でも帯域内の最大値/中央値が 3.99 倍まで来て**単独のしきい値 2.5 倍を超える** —— 止めているのは高調波の全数要求のほう。★★崖は 2 つある: 予測 L_crit = C²/ΔC = 14137 mm に対し実測の**分解の崖 14000 mm**(比 0.99)。ところが報告率 100 % を保つ**検出の崖は 17000 mm と長い** —— 記録を短くすると「隣と取り違える」より先に「何も言えなくなる」ので、Rayleigh が正しく当てたその崖には辿り着けない。★判定そのものを直した: 24 試行では「隣へ落ちる 0 %」が成立したが、120 試行では最長 20000 mm でも 2 % 残り、**0 % は床ではなく小標本の産物**だった(床の 3 倍で数え直して 14000 mm)。同じ理由で「特定成功率 100 %」も97 / 98 % に直した。★取り違え先は掃引 9 点中 7 点で冷却ロール、471.24 / 314.16 = 1.500 の 3:2 —— 台帳に整数比があると、櫛法にも固有の取り違えがある。★この PoC が炙り出した道具の穴 2 件を、その場で埋めた: 点列から直接スペクトルを取る `fs.point_spectrum`(ビン幅を選ばない点過程の周期図。分解能 1/記録長 を返り値に持つ)と、1-D の山をサブビンで読む `fs.peak_subbin`(頂点を丸めずに返す —— ±0.5 を超えたら「そこは極大でない」という情報)。PoC 本体もその op を通るようにしたが、櫛の高調波を掴むという中心の所見は変わらない(道具ではなく読み方の問題)。*

[![見逃しは位相を飛ばさないので、櫛の山は低くなるだけで動かない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_web_roll_periodicity/02_null_vs_spectrum_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_web_roll_periodicity/02_null_vs_spectrum.png)

*↑ 測定の図 ―― 見逃しは位相を飛ばさないので、櫛の山は低くなるだけで動かない。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_web_roll_periodicity/03_null_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_web_roll_periodicity/03_null_table.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_web_roll_periodicity/05_meander_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_web_roll_periodicity/05_meander_table.png)

*↑ この回の図*

[![縦線が閉形式の予測 C²/ΔC。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_web_roll_periodicity/07_cliff_length_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_web_roll_periodicity/07_cliff_length.png)

*↑ 縦線が閉形式の予測 C²/ΔC。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_web_roll_periodicity/09_cliff_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_web_roll_periodicity/09_cliff_table.png)

*↑ この回の図*

```
py -3.11 examples/poc_web_roll_periodicity.py
```

ソース: [examples/poc_web_roll_periodicity.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_web_roll_periodicity.py)

この回が作った図は全部で **10 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_web_roll_periodicity)

使用 op(ノートへ): [`cepstrum`](https://furuse.work/ops/acoustics/bearing/cepstrum.html) · [`find_peaks`](https://furuse.work/ops/oned/signal/find_peaks.html) · [`local_min_max_funct_1d`](https://furuse.work/ops/oned/function/local_min_max_funct_1d.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`peak_subbin`](https://furuse.work/ops/oned/signal/peak_subbin.html) · [`point_spectrum`](https://furuse.work/ops/oned/signal/point_spectrum.html) · [`smooth_funct_1d_gauss`](https://furuse.work/ops/oned/function/smooth_funct_1d_gauss.html) · [`spectrum`](https://furuse.work/ops/oned/signal/spectrum.html)

## No.2026.050 —— レーザー三角測量の断面から溶接ビードを測る ―― 測れなかったところを 0 と書く罪

[![レーザー三角測量の断面から溶接ビードを測る ―― 測れなかったところを 0 と書く罪](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_profile/01_laser_images_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_profile/01_laser_images.png)

*↑ **レーザー三角測量の断面から溶接ビードを測る ―― 測れなかったところを 0 と書く罪** ―― 輝線 1 本の行位置から断面 h(x) を戻し、余盛高さ・幅・アンダーカットを読む図。ゼロ点(各列の最大値の行)に対し重心は 9.3 倍良く、雑音ゼロなら対数放物線は機械精度(素の放物線と 12 桁差)なのに、雑音 1 % では 0.00272 対 0.00260 mm で区別がつかない。スパッタ 5 点で 3 種の推定量がそろって 0.11 mm(40 倍)へ壊れる ―― 効くのは精緻化ではなく、どのピークを選ぶか。*

[![0 で埋めた線は影の区間で h=0 に張り付き、左のアンダーカットが消えて偽のつま先ができる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_profile/02_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_profile/02_profile.png)

*↑ 測定の図 ―― 0 で埋めた線は影の区間で h=0 に張り付き、左のアンダーカットが消えて偽のつま先ができる。*

[![真値 0.45 mm。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_profile/03_undercut_vs_angle_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_profile/03_undercut_vs_angle.png)

*↑ 真値 0.45 mm。*

[![遮蔽が無ければ全部 1 % 以内。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_profile/04_quantities_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_profile/04_quantities.png)

*↑ 遮蔽が無ければ全部 1 % 以内。*

```
py -3.11 examples/poc_weld_bead_profile.py
```

ソース: [examples/poc_weld_bead_profile.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_weld_bead_profile.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_weld_bead_profile)

使用 op(ノートへ): [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`smooth_funct_1d_mean`](https://furuse.work/ops/oned/function/smooth_funct_1d_mean.html)

## No.2026.115 —— 光切断で溶接ビードを走査する ―― 分解能と遮蔽は同じノブの表裏

[![光切断で溶接ビードを走査する ―― 分解能と遮蔽は同じノブの表裏](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_scan_angle/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_scan_angle/01_scene.png)

*↑ **光切断で溶接ビードを走査する ―― 分解能と遮蔽は同じノブの表裏** ―― すみ肉溶接の断面を閉形式で作り、余盛・脚長・のど厚・アンダーカット深さを既知関数で溶接線に沿って変えたうえで、三角測量角 θ を 15〜70 度で掃引しました。高さ分解能は 1/sinθ で良くなる一方、傾き cotθ を超えて登る面は自分の陰に入るので、遠側の母材面は幾何どおり θ = 37.0 度で背を向け、左アンダーカットはそれより早い 20.8〜34.5 度から欠け始めます(深い溝ほど早い)。危ないのは θ = 28 度で「測れた率」が 100 % のまま溝の区間の 25 % が欠測して深さが 27 % 過小に出ることと、さらに角度を上げると深い断面から集計を抜けて真値の平均が 0.260 → 0.047 mm と流れる生存者バイアスで、最適角は測定量ごとに 20 / 24 / 36 / 64 度とばらけます。*

[![θ を大きくすると高さの伸び K が増えて分解能は上がる(輝線の起伏が大きくなる)が、左半分の輝線が消えていく。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_scan_angle/02_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_scan_angle/02_frames.png)

*↑ 測定の図 ―― θ を大きくすると高さの伸び K が増えて分解能は上がる(輝線の起伏が大きくなる)が、左半分の輝線が消えていく。*

[![θ = 28 度。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_scan_angle/03_profile_28_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_scan_angle/03_profile_28.png)

*↑ θ = 28 度。*

[![下に凸の谷がアンダーカット。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_scan_angle/05_undercut_zoom_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_scan_angle/05_undercut_zoom.png)

*↑ 下に凸の谷がアンダーカット。*

[![同じノブの表裏。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_scan_angle/07_resolution_vs_occlusion_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_scan_angle/07_resolution_vs_occlusion.png)

*↑ 同じノブの表裏。*

[![脚長は sin²(母材角)、溝深さは cos²(母材角) —— 同じ母材面で足すと 1。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_scan_angle/09_calibration_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_scan_angle/09_calibration.png)

*↑ 脚長は sin²(母材角)、溝深さは cos²(母材角) —— 同じ母材面で足すと 1。*

```
py -3.11 examples/poc_weld_bead_scan_angle.py
```

ソース: [examples/poc_weld_bead_scan_angle.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_weld_bead_scan_angle.py)

この回が作った図は全部で **11 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_weld_bead_scan_angle)

使用 op(ノートへ): [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`fit_plane_3d`](https://furuse.work/ops/3d/geometry/fit_plane_3d.html) · [`intersect_planes`](https://furuse.work/ops/3d/geometry/intersect_planes.html) · [`lines_gauss`](https://furuse.work/ops/2d/contour/lines_gauss.html) · [`normals_from_depth`](https://furuse.work/ops/3d/range_image/normals_from_depth.html) · [`occupancy_grid`](https://furuse.work/ops/3d/occupancy/occupancy_grid.html) · [`query_distance`](https://furuse.work/ops/3d/occupancy/query_distance.html)

## No.2026.090 —— 溶接 X 線透過像の気孔 ―― 等級を 1 段間違える画像の割合で締める

[![溶接 X 線透過像の気孔 ―― 等級を 1 段間違える画像の割合で締める](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/01_scene_radiograph_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/01_scene_radiograph.png)

*↑ **溶接 X 線透過像の気孔 ―― 等級を 1 段間違える画像の割合で締める** ―― 板厚 10 mm + 円弧の余盛 + 球形気孔を Beer–Lambert で閉形式に描き、散乱・不鋭度・粒状雑音を足した透過像。固定しきい値のゼロ点は余盛のつま先を気孔に数える(塊 124 個、合計面積 15.19 mm²、真値 7.93)。検出の崖は CNR = 16.12·d² から先に予測でき、50 % 検出径は Rose の CNR = 4 では 0.50 mm と外れ、平滑化と最小面積 3 px を入れた予測 0.58 mm に対し実測 0.57 mm。背景推定 op の窓上限(矩形オープニング 9 px)は 2.0 mm から検出率 50 % を割り 2.5 mm で 0 % の崖になる ―― op を選ぶことが測定範囲を選ぶ。散乱 SPR=1 は体積径を (1+SPR)^(-1/3) で -22.6 %(予測 -20.6 %)縮める。等級を 1 段間違える画像はゼロ点 90 % → 体積径 23 %。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/02_map_detections_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/02_map_detections.png)

*↑ 測定の図*

[![小さい側の崖は CNR で予測どおり。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/03_detect_vs_diameter_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/03_detect_vs_diameter.png)

*↑ 小さい側の崖は CNR で予測どおり。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/04_toe_detection_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/04_toe_detection.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/06_frames_scatter_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/06_frames_scatter.png)

*↑ この回の図*

[![視認基準 CNR ≥ 3(Rose)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/08_iqi_visibility_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/08_iqi_visibility.png)

*↑ 視認基準 CNR ≥ 3(Rose)。*

```
py -3.11 examples/poc_weld_radiograph_porosity.py
```

ソース: [examples/poc_weld_radiograph_porosity.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_weld_radiograph_porosity.py)

この回が作った図は全部で **9 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_weld_radiograph_porosity)

使用 op(ノートへ): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`blob_select`](https://furuse.work/ops/blob/select/blob_select.html) · [`estimate_noise`](https://furuse.work/ops/2d/features/estimate_noise.html) · [`gauss_image`](https://furuse.work/ops/2d/smoothing/gauss_image.html) · [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`gray_opening_rect`](https://furuse.work/ops/2d/morphology/gray_opening_rect.html) · [`identity`](https://furuse.work/ops/2d/misc/identity.html) · [`log_image`](https://furuse.work/ops/2d/arithmetic/log_image.html) · [`measure_pairs`](https://furuse.work/ops/measure1d/caliper/measure_pairs.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`median_rect`](https://furuse.work/ops/2d/rank/median_rect.html) · [`sk_rolling_ball`](https://furuse.work/ops/2d/smoothing/sk_rolling_ball.html) · [`xsitk_grayscale_grindpeak`](https://furuse.work/ops/2d/extra/xsitk_grayscale_grindpeak.html)

## No.2026.122 —— 画像の誤字を認識せずに見つけて直す ―― 閾値は書体の違いから導く

[![画像の誤字を認識せずに見つけて直す ―― 閾値は書体の違いから導く](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_glyph_typo_detection/01_sign_before_after_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_glyph_typo_detection/01_sign_before_after.png)

*↑ **画像の誤字を認識せずに見つけて直す ―― 閾値は書体の違いから導く** ―― 正しい文字列を入力で貰えるので、6000 通りの多クラス分類は要らず、各マスを指定の 1 字と比べるだけで済む。閾値は勘で置かず、同じ字を別の書体で描いたときの距離の 95 % 点(0.058)から導いた。距離は平均でなく 99 パーセンタイル ―― 取り違えは部首を共有したまま一部だけ入れ替わるので、平均では 検 と 横 の距離が 0.0171 と書体雑音の床より下に沈み、原理的に検出できない。合成した掲示では壊した 4 字を全部検出して誤検出ゼロ、置換後の距離は 0.0805 から 0.0258 に下がり 4 字とも床を下回った。*

[![床を超えたマスが誤字。壊した位置は 2, 3, 5, 7。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_glyph_typo_detection/02_cell_distance_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_glyph_typo_detection/02_cell_distance.png)

*↑ 測定の図 ―― 床を超えたマスが誤字。壊した位置は 2, 3, 5, 7。*

```
py -3.11 examples/poc_glyph_typo_detection.py
```

ソース: [examples/poc_glyph_typo_detection.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_glyph_typo_detection.py)

この回が作った図は全部で **2 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_glyph_typo_detection)



## No.2026.130 —— 3D プリンタの層検査 ―― 形 → 層 → 経路 → 画像 の往復を自分で閉じ、仕込んだ欠陥を数字で捕まえる

[![3D プリンタの層検査 ―― 形 → 層 → 経路 → 画像 の往復を自分で閉じ、仕込んだ欠陥を数字で捕まえる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_layer_inspection/02_layers_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_layer_inspection/02_layers.png)

*↑ **3D プリンタの層検査 ―― 形 → 層 → 経路 → 画像 の往復を自分で閉じ、仕込んだ欠陥を数字で捕まえる** ―― 3D プリンタのデータは「形(メッシュ)→ 層(スライス)→ 経路(G-code)→ 印刷中の層画像」と流れる。新族 printpath(11 op、numpy + 標準ライブラリ、新語なし)でこの往復が既存の語彙(mesh / voxel / table / image2d)だけで閉じるので、真値を自分で仕込める。角穴つきの箱と歯車状の柱(穴つき)を 0.2 mm で切った層マスクの面積は閉形式の真値と一致(184.00 mm² と 0.07 %)、穴だけが残る層は空(三角形の法線で輪郭に向きを付けて nonzero winding)、輪郭を周回する G-code の押し出し量は「周長 × 線幅 × 層厚 / フィラメント断面積」と厳密一致、G-code は読み書きで往復(相対座標・相対 E・リトラクト・G92・インチも読み、円弧と座標の欠けは拒む)、3MF も往復。層検査: 期待の層画像(gcode_layer_image)に欠け 6 か所・はみ出し 6 か所(1〜4 mm)を注入した観測を print_layer_defect_map が符号つきで捕まえ、許容 3 px(0.3 mm)で再現率 0.959・偽陽性 0。カメラを 0.2 mm ずらすと再現率 0.895・精度 0.946 に落ちる(ずれの分だけ欠陥の縁を許容に食われる)—— 許容を振った曲線をそのまま出した。*

[![gear-like boss with a round hole sliced at 0.2 mm into 30 layer masks (mesh_slice_stack) and rendered as a solid, grey =](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_layer_inspection/01_slice_stack_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_layer_inspection/01_slice_stack.png)

*↑ 測定の図 ―― gear-like boss with a round hole sliced at 0.2 mm into 30 layer masks (mesh_slice_stack) and rendered as a solid, grey = height*

[![precision and recall of the defect map against the injected truth as the tolerance grows, without an](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_layer_inspection/03_tolerance_curve_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_layer_inspection/03_tolerance_curve.png)

*↑ precision and recall of the defect map against the injected truth as the tolerance grows, without and with a 0.2 mm camera shift: a small tolerance ab…*

[![every number with the bar it had to clear](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_layer_inspection/04_numbers_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_layer_inspection/04_numbers.png)

*↑ every number with the bar it had to clear*

```
py -3.11 examples/poc_print_layer_inspection.py
```

ソース: [examples/poc_print_layer_inspection.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_print_layer_inspection.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_print_layer_inspection)

使用 op(ノートへ): [`contours_to_gcode`](https://furuse.work/ops/printpath/slice/contours_to_gcode.html) · [`gcode_extrusion_volume`](https://furuse.work/ops/printpath/gcode/gcode_extrusion_volume.html) · [`gcode_layer_image`](https://furuse.work/ops/printpath/gcode/gcode_layer_image.html) · [`gcode_read`](https://furuse.work/ops/printpath/gcode/gcode_read.html) · [`gcode_time_estimate`](https://furuse.work/ops/printpath/gcode/gcode_time_estimate.html) · [`gcode_write`](https://furuse.work/ops/printpath/gcode/gcode_write.html) · [`mesh_slice_contours`](https://furuse.work/ops/printpath/slice/mesh_slice_contours.html) · [`mesh_slice_stack`](https://furuse.work/ops/printpath/slice/mesh_slice_stack.html) · [`print_layer_defect_map`](https://furuse.work/ops/printpath/inspect/print_layer_defect_map.html) · [`prism_mesh`](https://furuse.work/ops/drive/japan/prism_mesh.html) · [`read_3mf`](https://furuse.work/ops/printpath/format/read_3mf.html) · [`vol_render_transfer`](https://furuse.work/ops/videocube/render/vol_render_transfer.html) · [`write_3mf`](https://furuse.work/ops/printpath/format/write_3mf.html)

## No.2026.189 —— 遅れても詰まらない倉庫 ―― AGV の群れは「計画が正しい」だけでは止まる

[![遅れても詰まらない倉庫 ―― AGV の群れは「計画が正しい」だけでは止まる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_agv_fleet/01_agv_naive_vs_adg.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_agv_fleet/01_agv_naive_vs_adg.gif)

*↑ **遅れても詰まらない倉庫 ―― AGV の群れは「計画が正しい」だけでは止まる** ―― 著者の発案「製造業でよく使われる AGV 系は全然やってないな」。床の格子を走る 12 台の搬送計画を焦点探索の CBS で作り(コスト 96 ≤ 1.1 × 下界 88)、同じ計画を各車両が 1 手ごとに確率 0.3 で遅れる条件で 1000 通り実行した図。「次のマスが空いていれば進む」素朴な実行は 641 / 1000 が詰まり、行動依存グラフ(ADG、Hönig ら 2019)に従う実行は衝突 0・デッドロック 0。詰まった 641 件のうち 640 件は着いて居座る車が通路を塞いだもので、待ちの閉路は 1 件だけだった。門: CBS の総コストが全台を 1 つの状態にした A*(第 2 実装)の最適値と 40 / 40 で一致、焦点探索 ≤ 1.3·最適 40 / 40、優先度付き計画がどの順でも解けない問題の実例(CBS と結合 A* は総コスト 9)、VDA 5050 の order は規則の違反 0。正直に: 1 手 = 一定時間の格子の離散モデルで、加減速・旋回・車体の大きさは入れていない。*

[![最後のコマ(左: デッドロック、右: 全台到着)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_agv_fleet/02_agv_naive_vs_adg_still_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_agv_fleet/02_agv_naive_vs_adg_still.png)

*↑ 測定の図 ―― 最後のコマ(左: デッドロック、右: 全台到着)*

[![同じ 12 台の計画を、遅れの確率ごとに 200 通り走らせたデッドロックの割合。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_agv_fleet/03_agv_deadlock_vs_delay_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_agv_fleet/03_agv_deadlock_vs_delay.png)

*↑ 同じ 12 台の計画を、遅れの確率ごとに 200 通り走らせたデッドロックの割合。*

[![優先度付き計画が、どちらを先にしても解けない問題(CBS の総コスト 9)。CBS は片方に道を譲らせて解く](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_agv_fleet/04_agv_prioritized_counterexample.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_agv_fleet/04_agv_prioritized_counterexample.gif)

*↑ 動く図 ―― 優先度付き計画が、どちらを先にしても解けない問題(CBS の総コスト 9)。CBS は片方に道を譲らせて解く*

```
py -3.11 examples/poc_agv_fleet.py
```

ソース: [examples/poc_agv_fleet.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_agv_fleet.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_agv_fleet)

使用 op(ノートへ): [`adg_build`](https://furuse.work/ops/drive/agv/adg_build.html) · [`adg_execute`](https://furuse.work/ops/drive/agv/adg_execute.html) · [`arrow`](https://furuse.work/ops/annotate/pointer/arrow.html) · [`mapf_cbs`](https://furuse.work/ops/drive/agv/mapf_cbs.html) · [`mapf_ecbs`](https://furuse.work/ops/drive/agv/mapf_ecbs.html) · [`mapf_joint_astar`](https://furuse.work/ops/drive/agv/mapf_joint_astar.html) · [`mapf_prioritized`](https://furuse.work/ops/drive/agv/mapf_prioritized.html) · [`naive_execute`](https://furuse.work/ops/drive/agv/naive_execute.html) · [`plan_conflicts`](https://furuse.work/ops/drive/agv/plan_conflicts.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`vda5050_check`](https://furuse.work/ops/drive/agv/vda5050_check.html) · [`vda5050_order`](https://furuse.work/ops/drive/agv/vda5050_order.html) · [`warehouse_grid`](https://furuse.work/ops/drive/agv/warehouse_grid.html)

## No.2026.185 —— 金属積層造形の熱画像から X 線 CT へ ―― 生信号を温度と呼ばない、時間軸と画素ピッチ、下向き面だけに付く粉

[![金属積層造形の熱画像から X 線 CT へ ―― 生信号を温度と呼ばない、時間軸と画素ピッチ、下向き面だけに付く粉](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_am_thermal_to_ct/01_melt_pool_frames.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_am_thermal_to_ct/01_melt_pool_frames.gif)

*↑ **金属積層造形の熱画像から X 線 CT へ ―― 生信号を温度と呼ばない、時間軸と画素ピッチ、下向き面だけに付く粉** ―― 金属積層造形(レーザ粉末床溶融、In718)の工程中の熱画像と、造形後の X 線 CT を Fullseye の既存 op でつなぐ。実データは米国国立標準技術研究所(NIST)の公開データ(熱画像 doi:10.18434/mds2-2716、X 線 CT doi:10.18434/mds2-2291 は Georgia Institute of Technology で測定)を 2026-10-02 に部分抽出し、しきい値処理・切り出し・疑似カラー化した(改変、NIST は AS IS で提供、https://www.nist.gov/open/license)。データは配布物に含めず、無ければ真値つきの合成で同じ門を走らせる。門: 生信号(DL)を温度と呼ばない —— 変換は放射率 ε を必須の引数にし、同じ飽和 4095 DL が ε=1 で 1401 ℃・ε=0.3 で 1641 ℃(差 239 K)、飽和は下限、0 は測定なし(式に通すと −204 ℃ に張り付く)/ 走査指令の laser-on 24 本 = 熱画像のバースト 24 本、周期は +2.3 % ずれる(原因は未解決として記録、合成では注入した 2.3 % を +2.31 % で読む) / 画素ピッチは走査速度から逆算して 21.31 µm(条件間で最大 0.20 %)/ 溶融池の長さは条件間のばらつきが反復内の 15 倍 / CT は設計 STL の断面と Dice 0.981、表面のはみ出しは下向き面(穴の天井)63 µm > 上向き 32 µm —— 付着粉が下向き面にだけ垂れる / 内部の空隙 0 個(検出下限 約 63 µm、閉じた空気 7 個はすべて表面から 0.02 mm 以内の付着粉)。正直に: 校正式は属性の文字列を推定して読んだ、液相線 1336 ℃ は仮定、CT のボクセル寸法は設計寸法からの逆算、時間軸の 2.3 % のずれは未解決。*

[![calibration T = 14388/(a ln(c eps/x + 1)) - b/a (reading of the file's model string is our assumption). 4095 DL = 1402 C](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_am_thermal_to_ct/02_dl_to_celsius_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_am_thermal_to_ct/02_dl_to_celsius.png)

*↑ 測定の図 ―― calibration T = 14388/(a ln(c eps/x + 1)) - b/a (reading of the file's model string is our assumption). 4095 DL = 1402 C at eps=1, 1641 C at eps=0.3. Pixels >= 2759 DL are above the liquidus for any eps <= 1. Source: National Institute of Standards and Technology (NIST), doi:10.18434/mds2-2716 (thermography) and doi:10.18434/mds2-2291 (XCT, measured at Georgia Tech); subsets extracted 2026-10-02, thresholded/cropped/false-coloured here (modified). Provided AS IS, https://www.nist.gov/open/license*

[![Line_0_1, row 300: 19 saturated frames are only a lower bound; the curve stops at frame 189 where th](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_am_thermal_to_ct/03_cooling_curve_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_am_thermal_to_ct/03_cooling_curve.png)

*↑ Line_0_1, row 300: 19 saturated frames are only a lower bound; the curve stops at frame 189 where the camera reports 0 (below 100 DL) instead of falli…*

[![Y pad: the command (XYPT, no time step stored) and the staring camera agree on the count and on the ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_am_thermal_to_ct/04_time_axis_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_am_thermal_to_ct/04_time_axis.png)

*↑ Y pad: the command (XYPT, no time step stored) and the staring camera agree on the count and on the long last interval, yet drift apart by 2.3 % per p…*

[![slice at z = 4.00 mm just below the crown of the 4 mm hole: particles hang into the hole from the do](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_am_thermal_to_ct/07_ct_hole_crown_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_am_thermal_to_ct/07_ct_hole_crown.png)

*↑ slice at z = 4.00 mm just below the crown of the 4 mm hole: particles hang into the hole from the down-facing surface; red = design.*

[![XCT vs STL: protrusion = p95 of the signed distance (outward positive) after subtracting the median ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_am_thermal_to_ct/08_protrusion_by_facing_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_am_thermal_to_ct/08_protrusion_by_facing.png)

*↑ XCT vs STL: protrusion = p95 of the signed distance (outward positive) after subtracting the median of each 0.25 mm surface cell (form error); line =…*

[![XCT slices 121..320 (z = 1.75..4.16 mm, build direction) with the STL cross-section in red. Note the powder/dross hangin](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_am_thermal_to_ct/06_ct_slices.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_am_thermal_to_ct/06_ct_slices.gif)

*↑ 動く図 ―― XCT slices 121..320 (z = 1.75..4.16 mm, build direction) with the STL cross-section in red. Note the powder/dross hanging under the hole crown and the 45 deg notch. Source: National Institute of Standards and Technology (NIST), doi:10.18434/mds2-2716 (thermography) and doi:10.18434/mds2-2291 (XCT, measured at Georgia Tech); subsets extracted 2026-10-02, thresholded/cropped/false-coloured here (modified). Provided AS IS, https://www.nist.gov/open/license*

```
py -3.11 examples/poc_am_thermal_to_ct.py
```

ソース: [examples/poc_am_thermal_to_ct.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_am_thermal_to_ct.py)

この回が作った図は全部で **9 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_am_thermal_to_ct)

使用 op(ノートへ): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_select_largest`](https://furuse.work/ops/blob/select/blob_select_largest.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`mesh_slice_stack`](https://furuse.work/ops/printpath/slice/mesh_slice_stack.html) · [`seg_boundary_f`](https://furuse.work/ops/segmentation/score/seg_boundary_f.html) · [`seg_dice_jaccard`](https://furuse.work/ops/segmentation/score/seg_dice_jaccard.html) · [`signed_surface_distance`](https://furuse.work/ops/shapestat/deviation/signed_surface_distance.html) · [`sk_otsu`](https://furuse.work/ops/2d/segmentation/sk_otsu.html) · [`vol_boundary_points`](https://furuse.work/ops/3d/boundary/vol_boundary_points.html) · [`vol_gaussian`](https://furuse.work/ops/2d/3d/vol_gaussian.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_region_props`](https://furuse.work/ops/3d/regionprops/vol_region_props.html)

### 寸法・形状計測ウィング ―― 偏りと散らばりは別々に持つ

「この部品の幅は 50.50 画素だ」と言い切るには、偏り(いつも同じ向きにずれる分)と散らばり(撮るたびに変わる分)を別々に出す必要があります。合否は偏りで決まり、繰り返し精度は散らばりで決まる。1 つの「誤差」にまとめた瞬間、どちらの対策を打つべきかが分からなくなります。

この部屋の 35 点は、符号つき距離関数の部品、インボリュート歯形、指定 PSD の粗さ面、白色干渉のスタック、解析スペックル、Frocht の応力場、対称な合成頭蓋と、いずれも閉形式か解析描画で真値を握った上で、キャリパーや相関や位相の読みを採点しています。

共通して出てきたのは「定義を書かない数字は比較できない」ということです。距離変換の 2 通りの規約で 0.20 mm 違うひび割れ幅、個数基準と面積基準で 1.66 倍違う D50、評価領域を広げると頭打ちにならない Sz、本数基準か長さ基準かで 5 % 動く配向度。測定器の誤差ではなく、比べる相手の問題として現れます。

## No.2026.120 —— 全数の 2-D 検査と抜き取りの 3-D 検査を対応づける ―― 格子は自分自身に重なる

[![全数の 2-D 検査と抜き取りの 3-D 検査を対応づける ―― 格子は自分自身に重なる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_aoi_ct_traceability/01_aoi_and_ct_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_aoi_ct_traceability/01_aoi_and_ct.png)

*↑ **全数の 2-D 検査と抜き取りの 3-D 検査を対応づける ―― 格子は自分自身に重なる** ―― 実装ラインは二段になっている。AOI(自動外観検査)は全数を上から撮り、X 線 CT は抜き取りで中身を撮る。現場が知りたいのは「AOI の数字から CT の数字をどこまで言えるか」で、これは 1 台の装置の精度ではなく、2 つの装置の出した番号が同じ接合部を指しているかという対応づけの問題。規則正しく並んだ接合部は点の配置だけでは装置間で一対一に対応づかない ―― 6x5 の格子は 30 点すべての距離署名が縮退し、署名は 9 種類しかない(格子が自分自身に重なるので向きが読めない)。3 辺がすべて異なる基準マーク(3600/5200/6325 um)を入れると回転も鏡映も一意に決まり、並進 + 回転 + 番号の振り直しを与えても対応が全復元する。そのうえで AOI の見かけのボイド率は CT の体積率と相関 0.973、悪い順 5 個も 5/5 一致する ―― にもかかわらず、寿命に効く「界面に接したボイド」を持つ27 個のうちその 5 個で拾えるのは 19 % だけ。合否の順位が合っていることは、危ない個体を拾えていることを意味しない。最初これを剛体変換(Kabsch)だけで解こうとして失敗した経緯も残してある。*

[![直線は「面積率に比例する」という素朴な仮定。点はそこから両側へ離れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_aoi_ct_traceability/02_area_vs_volume_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_aoi_ct_traceability/02_area_vs_volume.png)

*↑ 測定の図 ―― 直線は「面積率に比例する」という素朴な仮定。点はそこから両側へ離れる。*

[![AOI の面積率が大きい接合部が、界面に接するボイドを持つとは限らない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_aoi_ct_traceability/03_interface_voids_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_aoi_ct_traceability/03_interface_voids.png)

*↑ AOI の面積率が大きい接合部が、界面に接するボイドを持つとは限らない。*

[![同じロットを同じ「悪い順」で並べても、順位は一致しない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_aoi_ct_traceability/04_worst_first_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_aoi_ct_traceability/04_worst_first.png)

*↑ 同じロットを同じ「悪い順」で並べても、順位は一致しない。*

```
py -3.11 examples/poc_aoi_ct_traceability.py
```

ソース: [examples/poc_aoi_ct_traceability.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_aoi_ct_traceability.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_aoi_ct_traceability)

使用 op(ノートへ): [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html)

## No.2026.091 —— 竣工した部屋の壁を測る —— 外接直方体は寸法でなく部屋の向きを測っている

[![竣工した部屋の壁を測る —— 外接直方体は寸法でなく部屋の向きを測っている](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_asbuilt_wall_deviation/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_asbuilt_wall_deviation/01_scene.png)

*↑ **竣工した部屋の壁を測る —— 外接直方体は寸法でなく部屋の向きを測っている** ―― 内法 6.0 x 4.0 x 2.7 m の室内点群に、壁の倒れ(1.20〜9.00 mrad)・平面図の振れ 5.00 mrad・面外のふくらみ 9 mm を仕込み、素朴な外接直方体(AABB)と平面当てはめを同じ点群で突き合わせた。AABB は東西 +19.1 mm 過大で、部屋を走査軸に対して 1 度回すだけで +80.1 mm、10 度で +611.1 mm——これは施工誤差ではなく W cosψ + D sinψ という部屋の向きの式で、平面 2 枚の距離は ψ を振っても +2.24 mm から動かない。さらに AABB は点を 256 倍にすると +14.9 → +19.7 mm と広がり(雑音の最大値統計 2σ√(2 ln N))、測点を増やすほど悪くなる。外れ点(出 450 mm の家具)への壊れ方は 2 種類で、最小二乗は 10 % 混入で真値の 11 倍(66.3 mrad、閉形式の予測 63.8 と 4 % 以内)、RANSAC は 45 % まで持ちこたえて 55 % で棚へ乗り換える——そのとき倒れの誤差は 0.13 mrad と小さいまま面だけが 449.9 mm ずれるので、1 つの数字では破綻が見えない。面のふくらみ 1 個が倒れ(-1.258 mrad)・直交度(+0.500 mrad)・内法(+2.2 mm)の 3 つの判定を同時に汚し、どれも閉形式で 0.06 mrad 以内に予測できた。*

[![許容 ±10 mm。AABB は ψ=0.5 度で既に外れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_asbuilt_wall_deviation/02_aabb_vs_yaw_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_asbuilt_wall_deviation/02_aabb_vs_yaw.png)

*↑ 測定の図 ―― 許容 ±10 mm。AABB は ψ=0.5 度で既に外れる。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_asbuilt_wall_deviation/03_aabb_grows_with_points_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_asbuilt_wall_deviation/03_aabb_grows_with_points.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_asbuilt_wall_deviation/05_squareness_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_asbuilt_wall_deviation/05_squareness.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_asbuilt_wall_deviation/08_outlier_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_asbuilt_wall_deviation/08_outlier_maps.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_asbuilt_wall_deviation/10_bulge_fake_tilt_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_asbuilt_wall_deviation/10_bulge_fake_tilt.png)

*↑ この回の図*

```
py -3.11 examples/poc_asbuilt_wall_deviation.py
```

ソース: [examples/poc_asbuilt_wall_deviation.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_asbuilt_wall_deviation.py)

この回が作った図は全部で **12 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_asbuilt_wall_deviation)

使用 op(ノートへ): [`aabb`](https://furuse.work/ops/3d/bounds/aabb.html) · [`angle_between_planes`](https://furuse.work/ops/3d/geometry/angle_between_planes.html) · [`angle_line_plane`](https://furuse.work/ops/3d/geometry/angle_line_plane.html) · [`distance_point_plane`](https://furuse.work/ops/3d/geometry/distance_point_plane.html) · [`fit_plane3`](https://furuse.work/ops/3d/geometry/fit_plane3.html) · [`ransac_plane`](https://furuse.work/ops/3d/robust_fit/ransac_plane.html)

## No.2026.092 —— 電極の呼吸を µm で測る ―― サブピクセルなら何でもよいわけではない

[![電極の呼吸を µm で測る ―― サブピクセルなら何でもよいわけではない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_breathing/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_breathing/01_scene.png)

*↑ **電極の呼吸を µm で測る ―― サブピクセルなら何でもよいわけではない** ―― 充放電で膨らむ電極の伸びを、2 時期の断面画像の層境界をサブピクセルで追って出す。真値は負極 1.00 % / 正極 0.20 % / セパレータ 0 %、積層 480.0 → 482.136 µm(+2.136 µm = +0.4450 %)。二値化して画素数を数えるゼロ点は 12 層中 0 層しか読めない一方、固定しきい値の交差はサブピクセルなので雑音なしでは当たる(+0.004495)―― 殺すのは対照群のほうで、伸びゼロのままオフセットを +0.10 かけるだけで -1.07e-02、真値の 2.4 倍の偽の伸びを逆符号で返し、ゲイン x1.30 では交差が半分に落ちて測定不能になる。勾配ピーク(measure_pos)は同じ条件で 0.0 のまま。そして自分の「誤差 1.8e-14 px」を疑って積層を小数画素ずらすと、それは真値を画素の中心に置いた検査の産物で、実際は RMS 0.0088 / 最大 0.0122 px のピークロッキングだった(負極 1 層のひずみに 3.0 % 効く)。崖は 2 段あり、本数が壊れる崖は予測した 3σ の崖より 5.5 倍手前に来る。*

[![境界は erf の重ね合わせで解析的に置いてあるので、真値は浮動小数点の精度で既知。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_breathing/02_profiles_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_breathing/02_profiles.png)

*↑ 測定の図 ―― 境界は erf の重ね合わせで解析的に置いてあるので、真値は浮動小数点の精度で既知。*

[![階段状に増えるのは、伸びる層(負極 1.00 %)と伸びない層(セパレータ 0 %)が交互だから。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_breathing/03_displacement_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_breathing/03_displacement.png)

*↑ 階段状に増えるのは、伸びる層(負極 1.00 %)と伸びない層(セパレータ 0 %)が交互だから。*

[![真値を画素の中心に置いた検査は、推定器を実力以上に良く見せる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_breathing/04_peak_locking_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_breathing/04_peak_locking.png)

*↑ 真値を画素の中心に置いた検査は、推定器を実力以上に良く見せる。*

[![横線は真値。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_breathing/06_noise_scaling_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_breathing/06_noise_scaling.png)

*↑ 横線は真値。*

[![実測が予測から離れる左端は、雑音が増えたのではなく**境界を数え損ねている**。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_breathing/08_contrast_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_breathing/08_contrast_cliff.png)

*↑ 実測が予測から離れる左端は、雑音が増えたのではなく**境界を数え損ねている**。*

```
py -3.11 examples/poc_battery_electrode_breathing.py
```

ソース: [examples/poc_battery_electrode_breathing.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_battery_electrode_breathing.py)

この回が作った図は全部で **9 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_battery_electrode_breathing)

使用 op(ノートへ): [`auto_threshold`](https://furuse.work/ops/2d/segmentation/auto_threshold.html) · [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`piv_peak_locking`](https://furuse.work/ops/piv/assess/piv_peak_locking.html)

## No.2026.005 —— 左右非対称性を測る ―― 対称面は変形に引きずられる

[![左右非対称性を測る ―― 対称面は変形に引きずられる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bilateral_asymmetry/03_deviation_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bilateral_asymmetry/03_deviation_map.png)

*↑ **左右非対称性を測る ―― 対称面は変形に引きずられる** ―― 厳密に左右対称な合成頭蓋の片側に既知の膨らみを入れ、鏡映して重ねた図。完全対称な標本でも床は 0 にならず、点対点 1.33 mm → 点対面 0.030 mm → 近傍平滑 0.012 mm。残差を最小にする面は 6.33 mm の膨らみで 2.92 mm / 1.72 度引きずられ、非対称量の 46 % が消える。*

[![完全対称な標本を測った残差。点対点は点間隔がそのまま床になる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bilateral_asymmetry/01_floor_vs_spacing_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bilateral_asymmetry/01_floor_vs_spacing.png)

*↑ 測定の図 ―― 完全対称な標本を測った残差。点対点は点間隔がそのまま床になる。*

[![真値の線は利得 1.0。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bilateral_asymmetry/02_gain_vs_amplitude_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bilateral_asymmetry/02_gain_vs_amplitude.png)

*↑ 真値の線は利得 1.0。*

[![margin < 0.1 で採用を止めれば、66〜88 度の外しは弾ける。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bilateral_asymmetry/04_degenerate_margin_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bilateral_asymmetry/04_degenerate_margin.png)

*↑ margin < 0.1 で採用を止めれば、66〜88 度の外しは弾ける。*

```
py -3.11 examples/poc_bilateral_asymmetry.py
```

ソース: [examples/poc_bilateral_asymmetry.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bilateral_asymmetry.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_bilateral_asymmetry)

使用 op(ノートへ): [`chamfer_distance`](https://furuse.work/ops/3d/metrics/chamfer_distance.html) · [`detect_reflection_symmetry`](https://furuse.work/ops/3d/symmetry/detect_reflection_symmetry.html) · [`detect_rotational_symmetry`](https://furuse.work/ops/3d/symmetry/detect_rotational_symmetry.html) · [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`hausdorff_distance`](https://furuse.work/ops/3d/metrics/hausdorff_distance.html) · [`reflect_points`](https://furuse.work/ops/3d/symmetry/reflect_points.html) · [`reflection_symmetry_score`](https://furuse.work/ops/3d/symmetry/reflection_symmetry_score.html) · [`sample_surface`](https://furuse.work/ops/3d/superquadric/sample_surface.html) · [`vertex_normals`](https://furuse.work/ops/3d/mesh_process/vertex_normals.html)

## No.2026.013 —— スペックル画像からひずみを測る(DIC)

[![スペックル画像からひずみを測る(DIC)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dic_strain/04_strain_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dic_strain/04_strain_map.png)

*↑ **スペックル画像からひずみを測る(DIC)** ―― 3000 個のガウス斑点を変形写像で移してから描き直したスペックル対から変位とひずみを読む図。真の変位 0.37 px に対し窓相関(piv)の偏り 0.0002 px・散らばり 0.0022 px で、ゼロ点(動かないと答える)の 167 倍。剛体回転が微小ひずみの定義で数百 µε の嘘を作る ―― Green-Lagrange なら厳密に 0。*

[![変形は補間ではなく斑点の再描画。だから真値が厳密。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dic_strain/01_speckle_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dic_strain/01_speckle.png)

*↑ 測定の図 ―― 変形は補間ではなく斑点の再描画。だから真値が厳密。*

[![lk は 0.5 px 側へ寄る(教科書の peak locking と逆)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dic_strain/02_subpixel_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dic_strain/02_subpixel_bias.png)

*↑ lk は 0.5 px 側へ寄る(教科書の peak locking と逆)。*

[![窓を広げると尖頭が下がり幅が広がる(空間分解能の限界)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dic_strain/03_strain_concentration_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dic_strain/03_strain_concentration.png)

*↑ 窓を広げると尖頭が下がり幅が広がる(空間分解能の限界)。*

[![引張試験の荷重を 48 段で上げる過程(lk、窓 31)。真のひずみを 0 → 3000 µε、同時に試験機が 0 → 2.0 度回る。変形像は毎段、斑点を写して描き直す(補間なし)。最終段で微小ひずみ ∂u/∂x の領域平均は 2341 ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dic_strain/05_tensile_ramp.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dic_strain/05_tensile_ramp.gif)

*↑ 動く図 ―― 引張試験の荷重を 48 段で上げる過程(lk、窓 31)。真のひずみを 0 → 3000 µε、同時に試験機が 0 → 2.0 度回る。変形像は毎段、斑点を写して描き直す(補間なし)。最終段で微小ひずみ ∂u/∂x の領域平均は 2341 µε(理論 (1+e)cosθ-1 = 2389 µε)—— 材料は 3000 µε 伸びているのに、回転が約 611 µε 少なく見せる。Green-Lagrange は 2961 µε(理論 e+e²/2 = 3005 µε)。地図の色は全コマ共通の尺度。*

```
py -3.11 examples/poc_dic_strain.py
```

ソース: [examples/poc_dic_strain.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dic_strain.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_dic_strain)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`strain_from_displacement`](https://furuse.work/ops/piv/solid/strain_from_displacement.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html)

## No.2026.097 —— ダイの傾きと TSV の位置ずれを 1 つの CT から分ける ―― 傾きは回転まで偽装する

[![ダイの傾きと TSV の位置ずれを 1 つの CT から分ける ―― 傾きは回転まで偽装する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_die_tilt_tsv_overlay/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_die_tilt_tsv_overlay/01_scene.png)

*↑ **ダイの傾きと TSV の位置ずれを 1 つの CT から分ける ―― 傾きは回転まで偽装する** ―― 上下 2 枚のダイに 7×7 の TSV を仕込み、真の位置ずれ (+0.800, −0.450) µm・回転 +0.01500°・傾き (1.20°, 0.70°) を与えた CT ボリューム 1 個だけで測り返す。上面の開口をそのまま比べるゼロ点は 2.419 µm 外し(仕様 ±1.0 µm の 2.4 倍、真の位置ずれ 0.918 µm より大きい)、その偽装量は「ダイ厚 × 上面法線の横成分」の閉形式と比 0.996 / 0.999 で一致する。ビアの軸で下面へ引き直すと 0.0023 µm まで戻る。★予想は外れた ―― 傾きは並進だけでなく回転も偽装する(Rx Ry のせん断 sinα sinβ 由来、予測 +0.00733° に対し対照群との差で実測 +0.00696°)。これは軸補正では消えず、測った傾きで逆投影して初めて対照群と同じ値に戻る。崖は 0.491° の予測に対し実測 0.492°。*

[![雲ごと 2.42 µm ずれるのが傾きの偽装。散らばりの広がりは測定精度。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_die_tilt_tsv_overlay/02_overlay_scatter_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_die_tilt_tsv_overlay/02_overlay_scatter.png)

*↑ 測定の図 ―― 雲ごと 2.42 µm ずれるのが傾きの偽装。散らばりの広がりは測定精度。*

[![偽の回転の予測 +0.00733°、倍率の予測 -147.0 ppm(対照群との差で実測 +0.00696° / -144.5 ppm)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_die_tilt_tsv_overlay/03_estimator_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_die_tilt_tsv_overlay/03_estimator_table.png)

*↑ 偽の回転の予測 +0.00733°、倍率の予測 -147.0 ppm(対照群との差で実測 +0.00696° / -144.5 ppm)。*

[![ゼロ点(青)と予測(赤)は重なっている —— 誤差はダイ厚 x |法線の横成分| そのもの。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_die_tilt_tsv_overlay/04_tilt_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_die_tilt_tsv_overlay/04_tilt_cliff.png)

*↑ ゼロ点(青)と予測(赤)は重なっている —— 誤差はダイ厚 x |法線の横成分| そのもの。*

[![真の回転 0.01500° を超えるのは α ≈ 1.2°。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_die_tilt_tsv_overlay/05_rotation_vs_tilt_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_die_tilt_tsv_overlay/05_rotation_vs_tilt.png)

*↑ 真の回転 0.01500° を超えるのは α ≈ 1.2°。*

```
py -3.11 examples/poc_die_tilt_tsv_overlay.py
```

ソース: [examples/poc_die_tilt_tsv_overlay.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_die_tilt_tsv_overlay.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_die_tilt_tsv_overlay)

使用 op(ノートへ): [`fit_line3`](https://furuse.work/ops/3d/geometry/fit_line3.html) · [`procrustes_fit`](https://furuse.work/ops/shapestat/procrustes/procrustes_fit.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html)

## No.2026.014 —— 産業部品の寸法検査 ―― 偏りと散らばりを別々に出す

[![産業部品の寸法検査 ―― 偏りと散らばりを別々に出す](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dimensional_inspection/01_slot_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dimensional_inspection/01_slot_bias.png)

*↑ **産業部品の寸法検査 ―― 偏りと散らばりを別々に出す** ―― 符号つき距離関数で描いた部品(スロット幅 50.50 px、1 px = 12.5 µm)を既知の PSF と雑音で撮り、4 系のキャリパーで測った図。大津の整数幅(ゼロ点)は RMS 0.464 px = 5.8 µm、埋もれていた 1-D 計測実装の偏りは -0.0113 px = -0.14 µm で 41 倍。エッジ間距離が PSF 幅の 3.09 倍を切ると幅は系統的に大きく出るのに、API は成功を返し続ける。*

[![偏りはどちらも正(対が互いを押し広げる)。符号が一定なので繰り返し測っても消えない。下端 -4 は表示の打ち切り(|偏り| < 1e-4 px)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dimensional_inspection/02_blur_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dimensional_inspection/02_blur_cliff.png)

*↑ 測定の図 ―― 偏りはどちらも正(対が互いを押し広げる)。符号が一定なので繰り返し測っても消えない。下端 -4 は表示の打ち切り(|偏り| < 1e-4 px)。*

[![偏りは SNR 140 まで動かず、増えるのは散らばりだけ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dimensional_inspection/03_noise_bias_spread_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dimensional_inspection/03_noise_bias_spread.png)

*↑ 偏りは SNR 140 まで動かず、増えるのは散らばりだけ。*

[![3 本の縦線は 16.0 px = 200 um 離れている。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dimensional_inspection/04_edge_definition_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dimensional_inspection/04_edge_definition.png)

*↑ 3 本の縦線は 16.0 px = 200 um 離れている。*

```
py -3.11 examples/poc_dimensional_inspection.py
```

ソース: [examples/poc_dimensional_inspection.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dimensional_inspection.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_dimensional_inspection)

使用 op(ノートへ): [`add_metrology_object_circle_measure`](https://furuse.work/ops/measure1d/model/add_metrology_object_circle_measure.html) · [`add_metrology_object_ellipse_measure`](https://furuse.work/ops/measure1d/model/add_metrology_object_ellipse_measure.html) · [`add_metrology_object_generic`](https://furuse.work/ops/measure1d/model/add_metrology_object_generic.html) · [`add_metrology_object_line_measure`](https://furuse.work/ops/measure1d/model/add_metrology_object_line_measure.html) · [`add_metrology_object_rectangle2_measure`](https://furuse.work/ops/measure1d/model/add_metrology_object_rectangle2_measure.html) · [`align_metrology_model`](https://furuse.work/ops/measure1d/apply/align_metrology_model.html) · [`apply_metrology_model`](https://furuse.work/ops/measure1d/apply/apply_metrology_model.html) · [`create_metrology_model`](https://furuse.work/ops/measure1d/model/create_metrology_model.html) · [`edge_points`](https://furuse.work/ops/3d/edges/edge_points.html) · [`ellipse`](https://furuse.work/ops/annotate/shape/ellipse.html) · [`fuzzy_measure_pairing`](https://furuse.work/ops/measure1d/caliper/fuzzy_measure_pairing.html) · [`gen_measure_arc`](https://furuse.work/ops/measure1d/caliper/gen_measure_arc.html) · [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`m1_measure_pairs`](https://furuse.work/ops/2d/measure1d/m1_measure_pairs.html) · [`m1_measure_pos`](https://furuse.work/ops/2d/measure1d/m1_measure_pos.html) · [`measure_pairs`](https://furuse.work/ops/measure1d/caliper/measure_pairs.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`translate_measure`](https://furuse.work/ops/measure1d/caliper/translate_measure.html)

## No.2026.018 —— 繊維の配向分布を測る ―― 角度は 180 度周期、素朴に平均すると 90 度ずれる

[![繊維の配向分布を測る ―― 角度は 180 度周期、素朴に平均すると 90 度ずれる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/01_scene.png)

*↑ **繊維の配向分布を測る ―― 角度は 180 度周期、素朴に平均すると 90 度ずれる** ―― フォン・ミーゼス分布から撒いた繊維 140 本の配向を構造テンソルで読む図。真の平均 177.9 度を算術平均は 105.55 度と報告し(-72.33 度)、2 倍角の円形平均なら +0.17 度 ―― 画像も測定も 1 ビットも変えていない。全画素を等しく数えると配向度が -31.3 % 落ちる。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/02_wrap_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/02_wrap.png)

*↑ 測定の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/03_field_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/03_field.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/04_histogram_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/04_histogram.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/05_density_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/05_density.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/06_scales_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/06_scales.png)

*↑ この回の図*

```
py -3.11 examples/poc_fiber_orientation.py
```

ソース: [examples/poc_fiber_orientation.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_fiber_orientation.py)

この回が作った図は全部で **6 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_fiber_orientation)

使用 op(ノートへ): [`coherence`](https://furuse.work/ops/acoustics/dual/coherence.html) · [`dc_structure_texture`](https://furuse.work/ops/2d/decomposition/dc_structure_texture.html) · [`moment_axes`](https://furuse.work/ops/3d/match_pose/moment_axes.html) · [`principal_moments`](https://furuse.work/ops/3d/moment_invariant/principal_moments.html) · [`smooth_funct_1d_gauss`](https://furuse.work/ops/oned/function/smooth_funct_1d_gauss.html) · [`sobel_amp`](https://furuse.work/ops/2d/edges/sobel_amp.html) · [`sobel_dir`](https://furuse.work/ops/2d/edges/sobel_dir.html)

## No.2026.021 —— 歯車の歯形を測る ―― 偏心は 1 次、歯は z 次

[![歯車の歯形を測る ―― 偏心は 1 次、歯は z 次](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/01_scene.png)

*↑ **歯車の歯形を測る ―― 偏心は 1 次、歯は z 次** ―― インボリュートの閉形式で描いた歯車から偏心と歯形を読む図。ゼロ点の最小二乗円は直径 47.278 mm で、ピッチ円 48 / 歯先円 52 / 歯底円 43 のどれでもない。歯が 1 枚欠けると偏心 0.050 mm が 0.1285 mm(+157 %)に化けるが、歯ごとに 1 標本だけ読む伝統的な測り方なら 0.0501 mm(+0.2 %)。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/02_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/02_profile.png)

*↑ 測定の図*

[![歯の次数 24/48/72 は 2.6 mm あるので 0.35 mm で切った](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/03_spectrum_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/03_spectrum.png)

*↑ 歯の次数 24/48/72 は 2.6 mm あるので 0.35 mm で切った*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/04_missing_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/04_missing.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/05_illumination_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/05_illumination.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/06_summary_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/06_summary.png)

*↑ この回の図*

```
py -3.11 examples/poc_gear_tooth_metrology.py
```

ソース: [examples/poc_gear_tooth_metrology.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_gear_tooth_metrology.py)

この回が作った図は全部で **6 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_gear_tooth_metrology)

使用 op(ノートへ): [`blob_boundaries`](https://furuse.work/ops/blob/extract/blob_boundaries.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`blob_region`](https://furuse.work/ops/blob/extract/blob_region.html) · [`blob_select_largest`](https://furuse.work/ops/blob/select/blob_select_largest.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`polar_trans_image`](https://furuse.work/ops/2d/geometry/polar_trans_image.html) · [`spectrum`](https://furuse.work/ops/oned/signal/spectrum.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html)

## No.2026.022 —— 白色干渉計でナノメートルの段差をどこまで正確に測れるか

[![白色干渉計でナノメートルの段差をどこまで正確に測れるか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/01_interferogram_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/01_interferogram.png)

*↑ **白色干渉計でナノメートルの段差をどこまで正確に測れるか** ―― 白色干渉計の走査スタックを合成し、50〜500 nm の段差を測り返した図。雑音 1 % で偏り 2.4 nm 以内・標準偏差 14.1 nm 以内、しかも段差の大きさにほぼ依らない。ゼロ点(包絡線の最大サンプル)の誤差は走査ステップの半分に厳密一致し、Nyquist 上限 0.15 µm の手前 0.14 µm では雑音なしでも +14.1 nm。*

[![0.02〜0.12 µm は 0.05 nm 以内で平ら。Nyquist 上限 0.15 µm の手前 0.14 µm で崖。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/02_zstep_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/02_zstep_sweep.png)

*↑ 測定の図 ―― 0.02〜0.12 µm は 0.05 nm 以内で平ら。Nyquist 上限 0.15 µm の手前 0.14 µm で崖。*

[![centroid は散らばりが gaussian の 1/3〜1/5 なのに総合誤差では上に来る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/03_noise_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/03_noise_sweep.png)

*↑ centroid は散らばりが gaussian の 1/3〜1/5 なのに総合誤差では上に来る。*

[![4 種の段差でゲインが揃う = オフセットではなく倍率の誤差。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/04_centroid_gain_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/04_centroid_gain.png)

*↑ 4 種の段差でゲインが揃う = オフセットではなく倍率の誤差。*

[![動画(148 コマ): 仕込む段差を 0 → 0.90 µm へ連続に増やし、同じ表面を 2 つの方法で測る(雑音なし)。左は低い側・高い側 1 画素ずつのコヒーレンス走査の信号で、縦線は csi_height_map(gaussian)が](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/05_step_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/05_step_sweep.gif)

*↑ 動く図 ―― 動画(148 コマ): 仕込む段差を 0 → 0.90 µm へ連続に増やし、同じ表面を 2 つの方法で測る(雑音なし)。左は低い側・高い側 1 画素ずつのコヒーレンス走査の信号で、縦線は csi_height_map(gaussian)が包絡線から読んだ高さ。右は測った段差 vs 仕込んだ段差。包絡線(だいだい)は全域で対角線に乗り、誤差は最大 8.5e-11 nm —— 包絡線には周期が無いので巻き戻らない。位相シフト法(水色、4 段)は段差 0.153 µm(λ/4 = 0.150 µm の直後)で初めて λ/2 ぶん飛び、以後 λ/2 ごとに鋸の歯になる。*

```
py -3.11 examples/poc_interferometry_step.py
```

ソース: [examples/poc_interferometry_step.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_interferometry_step.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_interferometry_step)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`csi_design`](https://furuse.work/ops/interferometry/design/csi_design.html) · [`csi_height_map`](https://furuse.work/ops/interferometry/surface/csi_height_map.html) · [`csi_stack_simulate`](https://furuse.work/ops/interferometry/simulate/csi_stack_simulate.html) · [`decode_fringe`](https://furuse.work/ops/3d/structured_light/decode_fringe.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`synthesize_fringes`](https://furuse.work/ops/3d/structured_light/synthesize_fringes.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html)

## No.2026.073 —— 金属組織の結晶粒度 ―― 面積法と切片法は別の崖で落ちる

[![金属組織の結晶粒度 ―― 面積法と切片法は別の崖で落ちる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/01_scene.png)

*↑ **金属組織の結晶粒度 ―― 面積法と切片法は別の崖で落ちる** ―― 2-D Voronoi で粒を仕込み、粒界を幅 2 px で描いてエッチングむら・雑音・途切れを乗せ、ASTM E112 の面積法(大津 + 連結成分)と直線切断法(局所しきい値 + 4 方向の試験線)で G を測った図。面積法は雑音だけ -0.02・むらだけ -0.40 が両方で +3.82 と相互作用で死に、粒界の途切れでは 7.2 % で 1 段落ちる。切片法は 40.7 % まで持つが、予想の 29.3 % は外れ(マスク上で消える粒界は f の 0.76 倍)。混粒の全体 G 7.82 は細粒 9.01 にも粗粒 6.15 にも無く、64 タイル中 4 つしか ±0.5 に入らない。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/02_controls_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/02_controls.png)

*↑ 測定の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/03_stages_intercept_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/03_stages_intercept.png)

*↑ この回の図*

[![面積法は 1 本の途切れで 2 粒が融合するので、切片法の 6 分の 1 の途切れで 1 段落ちる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/05_cliff_break_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/05_cliff_break_sweep.png)

*↑ 面積法は 1 本の途切れで 2 粒が融合するので、切片法の 6 分の 1 の途切れで 1 段落ちる。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/07_failure_intercept_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/07_failure_intercept.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/09_duplex_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/09_duplex_map.png)

*↑ この回の図*

```
py -3.11 examples/poc_metal_grain_size.py
```

ソース: [examples/poc_metal_grain_size.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_metal_grain_size.py)

この回が作った図は全部で **11 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_metal_grain_size)

使用 op(ノートへ): [`bin_threshold`](https://furuse.work/ops/2d/segmentation/bin_threshold.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`bothat`](https://furuse.work/ops/2d/morphology/bothat.html) · [`dyn_threshold`](https://furuse.work/ops/2d/segmentation/dyn_threshold.html) · [`gray_bothat`](https://furuse.work/ops/2d/morphology/gray_bothat.html) · [`hx_close_edges`](https://furuse.work/ops/2d/halcon_ext/hx_close_edges.html) · [`invert_image`](https://furuse.work/ops/2d/gray/invert_image.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html)

## No.2026.100 —— 多ビーム測深で海底が笑う ―― 音速を取り違えると、壊れるのは外側ビームだけ

[![多ビーム測深で海底が笑う ―― 音速を取り違えると、壊れるのは外側ビームだけ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/12_across_track_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/12_across_track.png)

*↑ **多ビーム測深で海底が笑う ―― 音速を取り違えると、壊れるのは外側ビームだけ** ―― 多ビーム音響測深で、水柱の**音速プロファイルを取り違えると平らな海底が反り返る**(smile / frown)。壊れるのは**外側ビームだけ**で、直下はほぼ無傷 —— だから現場でいちばん検査される所だけが正しく見える。真値は自分で植える: 深さ 50.0 m の完全な水平面、音速 1520 → 1480 m/s(勾配 -0.800 /s)、±70 度 141 本、判定は実在規格 **IHO S-44 Order 1a**(TVU(50 m) = **0.8201 m**)。★崖は**測る前に 2 通り印字**した。ラフな展開式 Δz ≈ (gD^2/2c0)tan^2θ の予測 **48.15 度**、一定勾配層で光線が円弧になることから出る厳密な閉形式 **48.68 度**。実測(エコー検出を止めた経路)は **48.68 度** —— **厳密式は当たり**(差 2.0e-11 m)、**展開式は 0.53 度手前に外した**(45 度まで 3.0 % 以内、70 度で 19.4 % 過大。「tan^2 で効く」は外側で崩れる)。★★**予測を 1 つ外した**: 「エコー検出は無視できる床」と見込んでいたが、**全経路の崖は 47.95 度**で 0.73 度早い。70 度ではビームが照らす帯のエコーが **21396 µs**(直下の 171 倍)に伸びて非対称になり、振幅検出の頂点が手前へ寄る(**-0.725 m**)。実機が外側で位相検出に切り替える理由が数字で出た。★**対照群で犯人を切り分ける**: 屈折だけで **-2.6974 m**、角度推定の床 **0.000000 m**、エコー検出の床 **-0.2221 m**。スマイルは角度誤差でもエコー検出誤差でもなく**屈折そのもの**。ただしエコーの床は角度とともに増えるので「床は一定」とは書けない。★**教科書式が実測の 34 % しかない**: 70 度のフットプリントは cos^2 式 **8.21 m** に対し実測 **24.14 m**。電子的に振った配列は開口が cosθ に縮んで見えるためビーム幅が 1/cosθ で広がり、正しい指数は 3(cos^3 式は -0.6 % で当たる)。★**実装の刻みだけで規格を割る**: 層内を等音速とみなす古い処理は、キャストを 2 層に切っただけで 65 度に **+1.2994 m**(TVU の 1.6 倍)。32 層で +0.0785 m と 1 次収束するので、**キャストの切り方は精度の一部**。★**真値なしでできる唯一の検査**は隣接測線の重なり。端では **2.697 m**(TVU の 3.3 倍)食い違うのに、**帯の真ん中では 0.0000 m** —— 両測線とも同じ振れ角で誤差が同じだけ乗って消えるので、帯の端まで見ないと見つからない。地形図にすると、継ぎ目なしの見かけ勾配は最大 2.99 度(スマイルの曲がり)、継ぎ目ありは最大 **49.367 度**(海底に無い崖が 1 本立つ)。★**上向き屈折(frown)では、深さが誤るのではなく何も記録されない** —— 限界角の予測 73.90 度に対し、届いた最後のビーム 73.0 度 / 届かない最初 74.0 度。swath が黙って狭くなるだけなので記録は異常に見えない。★掃引 200 ケース(音速差 25 通り × 深さ 8 通りの格子)では、±65 度 swath の **78.0 %** が端で Order 1a を割る。崖の角度は深さとともに 10 m の 64.47 度 → 200 m の 45.53 度へ単調に寄るが、漸近値 44.83 度に**ぴったりは乗らない**(TVU の定数項 a = 0.5 m が 200 m でもまだ 2 割残る)。★サーモクラインには一定勾配の当てはめも効かない: 最大 5.357 m → 1.253 m と 77 % しか取れず、しかも**直下で +0.262 m** 悪くなる —— いちばん検査される所を犠牲に外側を良くしている。★道具の穴も 4 層(fs / fs.op / fs.ledger / op_find)を引いて記録した。sonar / swath / bathym / tvu は 0 件、sound_speed / footprint / crossline は件数だけ返るが中身は無関係(件数を見て「在る」と読むと外す)。検証中に**片道の穴**も 1 つ塞いだ: ベクトル版 `refract` の docstring が「1 本ずつ回せ」としか書かず、**光線ごとに全反射を判定する `refract_rays` が既にある**ことに触れていなかった(逆向きの参照は在った)。*

[![エコーは beamform_delay_sum の角度応答 × Lambert 後方散乱で海底の帯を足し上げて合成。find_peaks + peak_subbin で検出。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/01_floor_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/01_floor.png)

*↑ 測定の図 ―― エコーは beamform_delay_sum の角度応答 × Lambert 後方散乱で海底の帯を足し上げて合成。find_peaks + peak_subbin で検出。*

[![長さは 125 / 2271 / 21396 µs(170 倍の開き)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/02_echo_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/02_echo.png)

*↑ 長さは 125 / 2271 / 21396 µs(170 倍の開き)。*

[![Δc = -40 m/s の深水漸近値は 44.83 度。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/06_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/06_sweep.png)

*↑ Δc = -40 m/s の深水漸近値は 44.83 度。*

[![素子 96 本・λ/2 間隔。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/10_beam_pattern_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/10_beam_pattern.png)

*↑ 素子 96 本・λ/2 間隔。*

[![○ = 在る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/15_op_holes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/15_op_holes.png)

*↑ ○ = 在る。*

[![主図(動画、640 × 360・30 fps・12 秒): 深さ 50 m の平らな海底を、船が 2 本の測線(間隔 101.4 m)で測る。水色は真の音線(水柱の音速差 -40 m/s の線形プロファイルで円弧に曲がる)、白い点と面は直下](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/17_survey.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/17_survey.gif)

*↑ 動く図 ―― 主図(動画、640 × 360・30 fps・12 秒): 深さ 50 m の平らな海底を、船が 2 本の測線(間隔 101.4 m)で測る。水色は真の音線(水柱の音速差 -40 m/s の線形プロファイルで円弧に曲がる)、白い点と面は直下較正した等音速の処理が記録する海底で、色は「測った − 真の深さ」(高さの誤差だけ画面上 5 倍)。直下は +0.000 m、65 度は -2.697 m —— 平らな海底が外側だけ持ち上がる「スマイル」。最後に重なり帯を回り込むと、同じ海底を直下と最外ビームで測った 2.697 m の段差(TVU 0.820 m の 3.3 倍)が立っている。*

```
py -3.11 examples/poc_multibeam_bathymetry.py
```

ソース: [examples/poc_multibeam_bathymetry.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_multibeam_bathymetry.py)

この回が作った図は全部で **19 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_multibeam_bathymetry)

使用 op(ノートへ): [`beamform_delay_sum`](https://furuse.work/ops/rangedoppler/beamform/beamform_delay_sum.html) · [`beamform_doa`](https://furuse.work/ops/rangedoppler/beamform/beamform_doa.html) · [`color_bar`](https://furuse.work/ops/annotate/furniture/color_bar.html) · [`dem_slope`](https://furuse.work/ops/dem/surface/dem_slope.html) · [`find_peaks`](https://furuse.work/ops/oned/signal/find_peaks.html) · [`intensity`](https://furuse.work/ops/2d/features/intensity.html) · [`interp_scattered`](https://furuse.work/ops/math/interp_poly/interp_scattered.html) · [`peak_subbin`](https://furuse.work/ops/oned/signal/peak_subbin.html) · [`snell_angle`](https://furuse.work/ops/3d/optics/snell_angle.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html)

## No.2026.029 —— 粒度分布を画像から測る ―― 融合と縁切れが逆向きに効き、途中で打ち消し合う

[![粒度分布を画像から測る ―― 融合と縁切れが逆向きに効き、途中で打ち消し合う](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/01_scene.png)

*↑ **粒度分布を画像から測る ―― 融合と縁切れが逆向きに効き、途中で打ち消し合う** ―― 粒子を撒いた合成画像から D10 / D50 / D90 を出し、融合(大きい側へ)と縁切れ(小さい側へ)を別々に数えた図。面積率 13.8 % で D50 誤差 +0.55 % ―― 融合 28 件と縁切れ 19 件が釣り合っているだけ。個数基準と面積基準では同じ塊から D50 が 26.9 µm と 44.7 µm(1.66 倍)。*

[![薄いところで 0 なのは正確だから。濃いところで 0 をまたぐのは融合と縁切れが釣り合っただけ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/02_density_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/02_density_sweep.png)

*↑ 測定の図 ―― 薄いところで 0 なのは正確だから。濃いところで 0 をまたぐのは融合と縁切れが釣り合っただけ。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/03_failure_counts_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/03_failure_counts.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/04_merge_separability_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/04_merge_separability.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/05_merge_filter_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/05_merge_filter.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/06_edge_rules_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/06_edge_rules.png)

*↑ この回の図*

```
py -3.11 examples/poc_particle_sizing.py
```

ソース: [examples/poc_particle_sizing.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_particle_sizing.py)

この回が作った図は全部で **7 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_particle_sizing)

使用 op(ノートへ): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`blob_region`](https://furuse.work/ops/blob/extract/blob_region.html) · [`blob_select`](https://furuse.work/ops/blob/select/blob_select.html) · [`circularity`](https://furuse.work/ops/2d/features/circularity.html) · [`distance_transform`](https://furuse.work/ops/2d/region/distance_transform.html)

## No.2026.031 —— 光弾性で応力を測る ―― 巻き戻しが最初に失敗するのは等方点

[![光弾性で応力を測る ―― 巻き戻しが最初に失敗するのは等方点](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_photoelasticity/01_polariscope_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_photoelasticity/01_polariscope.png)

*↑ **光弾性で応力を測る ―― 巻き戻しが最初に失敗するのは等方点** ―― 円板圧縮の閉形式応力場(中心 4.2441 MPa、縞次数 2.380)を Mueller 行列の op で偏光像にし、縞から応力へ戻す図。op の偏光系は教科書式と 125 通りで最大差 2.2e-16。縞次数が 0.5 を超える 84.2 % の画素で位相が巻き、巻き戻しが最初に壊れるのは応力の大きい所ではなく、変調が落ちる等方点。*

[![左下 2 枚が「壊れる予報」。予報は当たるが、外せば直るとは限らない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_photoelasticity/02_unwrap_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_photoelasticity/02_unwrap.png)

*↑ 測定の図 ―― 左下 2 枚が「壊れる予報」。予報は当たるが、外せば直るとは限らない。*

[![動画(230 コマ、円板 φ50 mm を 361 画素で描画、半径 0.9R の外は描かない): 前半は荷重を 0 → 500 N へ上げる。暗視野(円偏光)の暗線は縞次数が整数の等値線で、荷重点から湧き出して中心へ寄る。中心の縞次数は荷](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_photoelasticity/03_load_and_isoclinics.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_photoelasticity/03_load_and_isoclinics.gif)

*↑ 動く図 ―― 動画(230 コマ、円板 φ50 mm を 361 画素で描画、半径 0.9R の外は描かない): 前半は荷重を 0 → 500 N へ上げる。暗視野(円偏光)の暗線は縞次数が整数の等値線で、荷重点から湧き出して中心へ寄る。中心の縞次数は荷重に比例して 2.38 まで増え(閉形式 h(σ1-σ2)/fσ)、右のグラフの中心の明るさ sin²(πN) が 0 に落ちるたびに暗線が中心を通過する(通過 2 回)。後半は荷重 500 N のまま、直交させた平面偏光子の対を 0 → 90 度回す。平面偏光の黒には 2 種類あり、回しても動かない縞は等色線(暗視野と同じ)、回すと動く黒い帯が等傾線 = 主応力の向きが偏光子と平行か直交する点で、中央の真値 θ の図で白く塗った点と重なる。偏光系は fullseye の mueller_element / mueller_apply(暗視野)と sin²(2(θ-β))·sin²(δ/2)(平面)。*

```
py -3.11 examples/poc_photoelasticity.py
```

ソース: [examples/poc_photoelasticity.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_photoelasticity.py)

この回が作った図は全部で **3 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_photoelasticity)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`mueller_apply`](https://furuse.work/ops/optics/polarization/mueller_apply.html) · [`mueller_element`](https://furuse.work/ops/optics/polarization/mueller_element.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html) · [`unwrap_phase_2d`](https://furuse.work/ops/3d/structured_light/unwrap_phase_2d.html)

## No.2026.103 —— 弦でレールを測る ―― 伝達関数が 0 になる波長は、何 mm あっても 0 mm と出る

[![弦でレールを測る ―― 伝達関数が 0 になる波長は、何 mm あっても 0 mm と出る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rail_corrugation/02_transfer_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rail_corrugation/02_transfer.png)

*↑ **弦でレールを測る ―― 伝達関数が 0 になる波長は、何 mm あっても 0 mm と出る** ―― 軌道の凹凸を弦(正矢)で読む —— 2 点を結んだ弦から中点までの距離を測る、軌道検測とレール削正の受入れでいまも使われる方法。★ゼロ点(正矢をそのまま高さと読む)は波長で 0.0 % 〜 200.0 % に化ける: 同じ 1 本の 10 m 弦が λ=10 m を +100 %、λ=1.5 m を +50 %、λ=30 m を -50 %、λ=5.0 / 2.5 / 1.0 m を -100 % に読む —— **過大評価と過小評価が同時に起きる**ので、全体を一律の係数で直すことはできない。★★死角は幾何で厳密に予測できる: |H(λ)| = |1 - cos(πL/λ)| は λ = L/(2n) でちょうど 0、λ = L/(2n+1) で 2 倍。10 波長 × 2 本の弦の 20 通りで**予測と実測の差は最大 0.00000**、λ=5.00 m の 0.600 mm は 200 m 全長の最大絶対値でも 0.00000 mm。★1/3 オクターブ帯に整理しても消えない(比 0.00041 〜 2.000 = 4924 倍)。この節では op の total_power が効いた —— 帯の和は全 FFT ビンの和の 0.519 しかなく、欠けた 48 % は λ=30 m の通り変位が f_min の外に居るためで、帯だけ見ていたら気づけない。★|H| で割り戻す逆フィルタは死角で 6.9e7 mm に発散し、正則化を入れると 3 波長が**静かに「凹凸なし」**になる。★★弦を 2 本(10 m と 6 m)にすると 10 中 8 波長が誤差 0.1 % 以内に戻るが、共通の死角は 1 点ではなく λ = 1.000/k の**櫛**。予測を 1 つ外した —— 仕込んだ λ=0.100 m も残り、調べたら k=10 の歯だった。隣り合う死角の相対間隔はそのまま λ なので短波長ほど詰まり、波状摩耗の帯(0.03–0.30 m)だけで 30 本ある。★0.25 m 標本では 30 mm の波状摩耗が 0.750 m のうねり 0.0528 mm に化ける(短波長を止めた対照群 0.00584 mm の 9 倍。床が 0 でないのは長波長成分の漏れ)。★非対称弦(前 3.7 m / 後ろ 6.3 m)は長波長の死角を消すが、|H|=0 の条件が「a/λ も b/λ も整数」なので λ = gcd(a,b)/k = 0.100 m に死角ができる —— **波状摩耗を測るための弦が、波状摩耗の帯域に死角を作った**。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rail_corrugation/01_planted_components_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rail_corrugation/01_planted_components.png)

*↑ 測定の図*

[![10 m 弦は λ=5.0 / 2.5 / 1.67 / 1.25 / 1.0 m で厳密に 0、λ=10 / 3.33 m で 2 倍。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rail_corrugation/03_transfer_zoom_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rail_corrugation/03_transfer_zoom.png)

*↑ 10 m 弦は λ=5.0 / 2.5 / 1.67 / 1.25 / 1.0 m で厳密に 0、λ=10 / 3.33 m で 2 倍。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rail_corrugation/05_octave_bands_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rail_corrugation/05_octave_bands.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rail_corrugation/07_dual_chord_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rail_corrugation/07_dual_chord.png)

*↑ この回の図*

[![0.750 m の周期がきれいに立つ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rail_corrugation/09_aliasing_seen_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rail_corrugation/09_aliasing_seen.png)

*↑ 0.750 m の周期がきれいに立つ。*

```
py -3.11 examples/poc_rail_corrugation.py
```

ソース: [examples/poc_rail_corrugation.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_rail_corrugation.py)

この回が作った図は全部で **11 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_rail_corrugation)

使用 op(ノートへ): [`octave_bands`](https://furuse.work/ops/acoustics/level/octave_bands.html) · [`octave_spectrum`](https://furuse.work/ops/acoustics/level/octave_spectrum.html)

## No.2026.104 —— 実写のコインを数えて測る ―― 当たっている答えに、余裕があるとは限らない

[![実写のコインを数えて測る ―― 当たっている答えに、余裕があるとは限らない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_coin_metrology/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_coin_metrology/01_scene.png)

*↑ **実写のコインを数えて測る ―― 当たっている答えに、余裕があるとは限らない** ―― 「照明が斜めに落ちているから大域しきい値では駄目」で有名な実写(scikit-image coins)。背景は行 0.427→0.161 / 列 0.331→0.059 と確かに傾いているのに、★素の大域 Otsu + 穴埋め + 面積 150 が真値 24 枚をちょうど当てる(真値は面積の平坦域 50〜800・半径を明示した Hough・Sobel+穴埋めの 3 経路一致で決め、さらに円 1 個が成分 1 個に収まる 1 対 1 の検算まで通した)。★★ところが余裕は 0.05 しかない ―― 同じ形の勾配をわずかに足すだけで 24→22 枚。答えが合っていることは、余裕があることの証明にならない。★★+0.30 では面積の中央値が -0.27 % しか動かないのに最悪のコインは -24.20 %(+0.40 で -46.02 %)、しかもずれは行位置と r=-0.90 で相関する ―― 真の面積は置き場所に依らないので、この相関はまるごと誤差。★gray_tophat で平坦化すると枚数は粘るが面積の中央値が 0.29 倍になる(枚数の頑健さと寸法の頑健さは別)。★生の連結成分は 4 近傍 126 / 8 近傍 96 で 3 割違い、円形度 0.7 で絞ると 24→21 枚に減る。*

[![見た目はほとんど変わらないのに 2 枚落ちる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_coin_metrology/02_margin_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_coin_metrology/02_margin.png)

*↑ 測定の図 ―― 見た目はほとんど変わらないのに 2 枚落ちる。*

[![代表値で報告すると、壊れているのに壊れていないように見える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_coin_metrology/03_drift_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_coin_metrology/03_drift.png)

*↑ 代表値で報告すると、壊れているのに壊れていないように見える。*

[![生の個数は近傍の規約で 3 割違う。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_coin_metrology/04_truth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_coin_metrology/04_truth.png)

*↑ 生の個数は近傍の規約で 3 割違う。*

```
py -3.11 examples/poc_real_coin_metrology.py
```

ソース: [examples/poc_real_coin_metrology.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_coin_metrology.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_real_coin_metrology)

使用 op(ノートへ): [`blob_count`](https://furuse.work/ops/2d/features/blob_count.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`canny`](https://furuse.work/ops/2d/segmentation/canny.html) · [`fill_holes`](https://furuse.work/ops/2d/region/fill_holes.html) · [`gray_tophat`](https://furuse.work/ops/2d/morphology/gray_tophat.html) · [`hough_circle_trans`](https://furuse.work/ops/2d/features/hough_circle_trans.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`sobel_amp`](https://furuse.work/ops/2d/edges/sobel_amp.html)

## No.2026.083 —— ねじの輪郭からピッチ・フランク角・有効径 ―― 傾きは左右のフランクに逆符号で出る

[![ねじの輪郭からピッチ・フランク角・有効径 ―― 傾きは左右のフランクに逆符号で出る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/07_sampling_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/07_sampling_frames.png)

*↑ **ねじの輪郭からピッチ・フランク角・有効径 ―― 傾きは左右のフランクに逆符号で出る** ―― ISO 68-1 の基本三角形を閉形式で描いた M6 相当の投影像(1 px = 25 µm)。二値化した列幅の FFT はピッチを真値の半分 20 px と答える(上下輪郭が P/2 ずれた三角波の和は定数)。軸を 3 度傾けると左右フランク角は 33.18 / 26.74 度に割れ、半和 29.81 度が真のフランク角、半差 3.19 度が傾きの推定になる。片側フランクで測るピッチは 1 次で狂う(+3.28 / -2.79 %)が頂点間隔は 2 次(-0.12 %)。傾きを戻せば P -0.009 %、d2 +0.033 %。*

[![幅の系列は上下輪郭(P/2 ずれ)の和なので基本波が消える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/01_zero_spectrum_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/01_zero_spectrum.png)

*↑ 測定の図 ―― 幅の系列は上下輪郭(P/2 ずれ)の和なので基本波が消える。*

[![片側のフランクだけで測ると 1 度あたり約 1 % 狂う。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/02_tilt_pitch_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/02_tilt_pitch.png)

*↑ 片側のフランクだけで測ると 1 度あたり約 1 % 狂う。*

[![半差が θ、半和が α。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/03_tilt_angles_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/03_tilt_angles.png)

*↑ 半差が θ、半和が α。*

[![生 = 水平 caliper 4 山、補正 = θ_est の向きの caliper 16 山(3 種の平均)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/05_tilt_correction_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/05_tilt_correction.png)

*↑ 生 = 水平 caliper 4 山、補正 = θ_est の向きの caliper 16 山(3 種の平均)。*

[![帯はフランクの中央 30 %(両端の丸みから 7.6 px)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/06_blur_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/06_blur_sweep.png)

*↑ 帯はフランクの中央 30 %(両端の丸みから 7.6 px)。*

```
py -3.11 examples/poc_screw_thread_metrology.py
```

ソース: [examples/poc_screw_thread_metrology.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_screw_thread_metrology.py)

この回が作った図は全部で **8 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_screw_thread_metrology)

使用 op(ノートへ): [`fit_line_contours`](https://furuse.work/ops/2d/contour/fit_line_contours.html) · [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`hx_split_contours`](https://furuse.work/ops/2d/halcon_ext/hx_split_contours.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html) · [`threshold_sub_pix`](https://furuse.work/ops/2d/contour/threshold_sub_pix.html) · [`xg_regress_contours`](https://furuse.work/ops/2d/xldgeom/xg_regress_contours.html)

## No.2026.112 —— 堆積物の在庫量 ―― 誰も測っていない「山の下の地面」が答えを決める

[![堆積物の在庫量 ―― 誰も測っていない「山の下の地面」が答えを決める](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_stockpile_volume/05_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_stockpile_volume/05_scene.png)

*↑ **堆積物の在庫量 ―― 誰も測っていない「山の下の地面」が答えを決める** ―― 鉱山・骨材・港湾の**堆積物の在庫量**を 3-D スキャンから出す。山と地面を別々の式で置き、安息角 37 度の円錐 3 個の**和**にしたので体積が解析的に閉じる(3572.6089 m^3、セル 0.025 m の数値積分と一致)。★★**在庫量という 1 個の数字は、誰も測っていない面 —— 山の下の地面 —— の仮定で決まる**。★崖 (a) 底面の仮定は閉形式 ΔV = -A・Δh で先に印字してから測り、7 通りで差 **0.0000 m^3**。驚きは一致ではなく大きさのほうで、**測量では誤差とも呼ばない 5 cm が在庫の 1.269 %、かさ 1.6 t/m^3 なら 72.5 t**(トラック 3 台分)。★崖 (b) 遮蔽は「円錐は線織面」から可視率 = arccos((H-h_s)/(D tanφ))/π。6 通りで差 ≤ 0.0201 で、その差はセルを 1.2 → 0.6 → 0.4 m にすると 0.0339 → 0.0171 → 0.0120 と **1 次で縮む** —— **模型の誤りではなく離散化**だと切り分けられる。★★予測を 1 つ外した: 遮蔽部を補間すると体積は**過小**に出ると思っていた(円錐面は凹なので弦は下を通る)が、実測は **+17.20 % の過大**。裏側が法尻まで丸ごと見えないため三角形の相手が「山の上」ではなく**山の外の地面**になり、稜線から 30 m 先へ張った弦の勾配 0.37 m/m が真の斜面 0.75 m/m の**上**を通る。「凹だから過小」は両端が山の上にあるときの話だった。★★相殺の罠が出た: 同じ 1 か所スキャンで、真の地面を底面にすると **+17.20 %**、現場の手(外周平均の水平底面)だと **+0.51 %**。良くなったのではなく、外周の高さも同じ補間で **+0.728 m** 持ち上がって引き算で消えているだけ —— 証拠に、外周のうち**実際に見えた点だけ**で底面を決めると **+12.05 %** に戻る。**汚染された物差しで汚染された対象を測ると、誤差は消えたように見える**。★同じ形が §7 にも: 法尻に残土の土手を混ぜると**外れ値に強い RANSAC のほうが数字は悪い**(+2.48 % 対 TLS +0.61 %)が、RANSAC は土手を正しく捨てて「土手なし」の答え +1.91 % へ戻っただけで、TLS が良く見えるのは土手の持ち上げがうねりの偏りをたまたま打ち消したから。★外周平均の水平底面は footprint が概ね対称なら地面の**傾きを勝手に打ち消す**(平らな対照群 +0.01 %)。残る +1.79 % は全部うねりで、**傾いた平面を当てはめると悪化する**(+1.91 %)—— 「自由度を増やせば良くなる」は成立しない。★物差しで勝者が入れ替わる: 体積は水平底面が僅かに良く、**重心は平面当てはめが 6 分の 1**(0.07 m 対 0.42 m)。積込計画に効くのは重心のほう。★★2 つの誤差は**足し算にならない**(-0.70 % のはずが +0.51 %)—— 遮蔽の補間が底面を決める外周まで動かすので、2 つは絡む。誤差収支を「底面 x % + 遮蔽 y %」と足す報告は、この時点で嘘になる。★★道具のバグを 1 つ見つけて、その場で直した: `dem_viewshed` が**観測者の目線より高いセルを軒並み「見えない」と返していた**(平地に置いた円錐の頂点が可視 0.0、目線より高い 1541 セルの可視 0 個、底面の遮蔽率 0.8863 対 閉形式 0.5710)。視線の標本が `np.rint` で**目標セル自身**に丸まる自己遮蔽で、標本が目標セルに乗った回を数えないよう修正した(いま 頂点 1.0 / 遮蔽率 0.5900)。★**それまでの門が通した理由**が収穫で、可視領域の試験は「平地」と「壁の**向こう側**」しか見ておらず、**壁そのものが見えるか**を一度も確かめていなかった。*

[![A = 906.5 m^2。閉形式は測る前に印字してある。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_stockpile_volume/01_base_offset_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_stockpile_volume/01_base_offset.png)

*↑ 測定の図 ―― A = 906.5 m^2。閉形式は測る前に印字してある。*

[![2 本は重なる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_stockpile_volume/02_base_offset_line_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_stockpile_volume/02_base_offset_line.png)

*↑ 2 本は重なる。*

[![可視率 = arccos((H-h_s)/(D tanφ))/π。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_stockpile_volume/03_occlusion_closed_form_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_stockpile_volume/03_occlusion_closed_form.png)

*↑ 可視率 = arccos((H-h_s)/(D tanφ))/π。*

[![3 か所で遮蔽は 1.4 % まで落ちるが、うねり由来の +1.8 % は何か所測っても消えない(底面は誰も測っていない)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_stockpile_volume/04_scan_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_stockpile_volume/04_scan_sweep.png)

*↑ 3 か所で遮蔽は 1.4 % まで落ちるが、うねり由来の +1.8 % は何か所測っても消えない(底面は誰も測っていない)。*

[![対照群(平ら/全周)で 2 つを切り分けてから、両方入れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_stockpile_volume/06_summary_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_stockpile_volume/06_summary.png)

*↑ 対照群(平ら/全周)で 2 つを切り分けてから、両方入れる。*

[![主図(動画、640 × 360・30 fps・12 秒): うねりのある地面に置いた山の周りを一周しながら、走査位置を 1 → 2 → 3 か所と増やす。描いているのは補間で埋めた DSM(在庫計算が信じている面)で、色は「補間 − 真の面](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_stockpile_volume/07_scan_orbit.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_stockpile_volume/07_scan_orbit.gif)

*↑ 動く図 ―― 主図(動画、640 × 360・30 fps・12 秒): うねりのある地面に置いた山の周りを一周しながら、走査位置を 1 → 2 → 3 か所と増やす。描いているのは補間で埋めた DSM(在庫計算が信じている面)で、色は「補間 − 真の面」(最大 5.23 m)。見えなかった割合は 0.660 → 0.315 → 0.014。在庫量の誤差は真の底面で +17.20 % → +3.05 % → +0.05 %、外周平均の水平底面で +0.51 % → +2.41 % → +1.83 % —— 3 か所で遮蔽は塞がるが、うねり由来の偏りは残る。高さは実寸。*

```
py -3.11 examples/poc_stockpile_volume.py
```

ソース: [examples/poc_stockpile_volume.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_stockpile_volume.py)

この回が作った図は全部で **7 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_stockpile_volume)

使用 op(ノートへ): [`color_bar`](https://furuse.work/ops/annotate/furniture/color_bar.html) · [`dem_hillshade`](https://furuse.work/ops/dem/shading/dem_hillshade.html) · [`dem_slope`](https://furuse.work/ops/dem/surface/dem_slope.html) · [`dem_viewshed`](https://furuse.work/ops/dem/visibility/dem_viewshed.html) · [`interp_scattered`](https://furuse.work/ops/math/interp_poly/interp_scattered.html) · [`moment_axes`](https://furuse.work/ops/3d/match_pose/moment_axes.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html)

## No.2026.038 —— クリープ試験のひずみ履歴 ―― 累積か直接か

[![クリープ試験のひずみ履歴 ―― 累積か直接か](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/01_speckle_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/01_speckle.png)

*↑ **クリープ試験のひずみ履歴 ―― 累積か直接か** ―― 1 時間のクリープを 25 コマ撮り、隣接コマの累積と基準フレームとの直接比較でひずみ履歴を出した図。終端で累積 61 µε / 直接 1878 µε と累積が 31 倍良く、教科書の「時刻で入れ替わる」交点は無い(入れ替わるのは雑音の軸)。コマを 24 → 4 歩に間引くと累積は -60 → -606 µε と悪化 ―― 効くのは歩数でなく 1 歩あたりの変形量。*

[![直接の偏りだけが伸びる。累積は偏りも散らばりも頭打ちで、しかも散らばりより偏りのほうが大きい ——ランダムウォークではない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/02_errors_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/02_errors.png)

*↑ 測定の図 ―― 直接の偏りだけが伸びる。累積は偏りも散らばりも頭打ちで、しかも散らばりより偏りのほうが大きい ——ランダムウォークではない。*

[![因果フィルタの偏りは遅れ (w-1)/2 の閉形式にほぼ乗る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/03_rate_tradeoff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/03_rate_tradeoff.png)

*↑ 因果フィルタの偏りは遅れ (w-1)/2 の閉形式にほぼ乗る。*

[![予測 = w=1 の偏り + 閉形式(中央はなまり、因果は遅れ)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/04_rate_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/04_rate_table.png)

*↑ 予測 = w=1 の偏り + 閉形式(中央はなまり、因果は遅れ)。*

[![動画(720 × 458、8 fps、127 コマ): クリープ試験を 25 コマ撮る。左はその時刻のスペックル像に、t=0 との直接 PIV の変位を 3 倍の矢印で重ねたもの(中心から外へ伸びる)。右上は真ひずみ(白、閉形式)と測った値](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/05_history_video.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/05_history_video.gif)

*↑ 動く図 ―― 動画(720 × 458、8 fps、127 コマ): クリープ試験を 25 コマ撮る。左はその時刻のスペックル像に、t=0 との直接 PIV の変位を 3 倍の矢印で重ねたもの(中心から外へ伸びる)。右上は真ひずみ(白、閉形式)と測った値(青 = 隣のコマどうしの増分を足す累積、朱 = いつも t=0 と比べる直接)、右下はその誤差。直接の誤差だけが変形とともに伸び、終端で 累積 -49 µε / 直接 -1888 µε(雑音の実現 1 通り、第 2 節と同じ種)。*

```
py -3.11 examples/poc_strain_history.py
```

ソース: [examples/poc_strain_history.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_strain_history.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_strain_history)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`data_to_pixel`](https://furuse.work/ops/annotate/plot/data_to_pixel.html) · [`moving_average_window`](https://furuse.work/ops/videostream/window/moving_average_window.html) · [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`piv_error_stats`](https://furuse.work/ops/piv/assess/piv_error_stats.html) · [`piv_multipass`](https://furuse.work/ops/piv/estimate/piv_multipass.html) · [`piv_sample_at_windows`](https://furuse.work/ops/piv/assess/piv_sample_at_windows.html) · [`piv_synth_pair`](https://furuse.work/ops/piv/synth/piv_synth_pair.html) · [`poly_fit`](https://furuse.work/ops/math/interp_poly/poly_fit.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html)

## No.2026.040 —— 表面粗さ Sa / Sq / Sz は標本化とカットオフにどこまで耐えるか

[![表面粗さ Sa / Sq / Sz は標本化とカットオフにどこまで耐えるか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_surface_roughness/01_surface_components_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_surface_roughness/01_surface_components.png)

*↑ **表面粗さ Sa / Sq / Sz は標本化とカットオフにどこまで耐えるか** ―― 指定 PSD から合成した表面(Sq の真値は Parseval で解析的)に傾き・うねり・加工目・傷を足し、粗さパラメータを測った図。生の rms を Sq と呼ぶと 20 倍の過大、平面だけ除いても 1.8 倍。標本間隔 8 µm で Sa は -3.5 %(合格)、Sz は -19.8 %(不合格) ―― Sz は評価領域を広げると頭打ちにならず、「真の Sz」は存在しない。*

[![dx=8 µm では Sa が ±5 % 合格で Sz が不合格。同じデータでも見るパラメータで結論が反転する。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_surface_roughness/02_sampling_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_surface_roughness/02_sampling_cliff.png)

*↑ 測定の図 ―― dx=8 µm では Sa が ±5 % 合格で Sz が不合格。同じデータでも見るパラメータで結論が反転する。*

[![頭打ちにならないので『真の Sz』は存在しない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_surface_roughness/03_sz_vs_window_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_surface_roughness/03_sz_vs_window.png)

*↑ 頭打ちにならないので『真の Sz』は存在しない。*

[![左は加工目(λ=32µm)を落として過小、右はうねり(λ=256µm)が漏れて過大。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_surface_roughness/04_lambda_c_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_surface_roughness/04_lambda_c_sweep.png)

*↑ 左は加工目(λ=32µm)を落として過小、右はうねり(λ=256µm)が漏れて過大。*

```
py -3.11 examples/poc_surface_roughness.py
```

ソース: [examples/poc_surface_roughness.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_surface_roughness.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_surface_roughness)

使用 op(ノートへ): [`profile_params`](https://furuse.work/ops/roughness/measure/profile_params.html) · [`surface_filter`](https://furuse.work/ops/roughness/prepare/surface_filter.html) · [`surface_form_remove`](https://furuse.work/ops/roughness/prepare/surface_form_remove.html) · [`surface_params`](https://furuse.work/ops/roughness/measure/surface_params.html) · [`surface_psd`](https://furuse.work/ops/roughness/measure/surface_psd.html) · [`surface_synth_psd`](https://furuse.work/ops/roughness/synth/surface_synth_psd.html)

## No.2026.196 —— 視触覚センサ(弾性膜 + カメラ)の合成と逆算 ―― Hertz 接触とフォトメトリックステレオの閉形式を門に、球の押し込みから力を読む

[![視触覚センサ(弾性膜 + カメラ)の合成と逆算 ―― Hertz 接触とフォトメトリックステレオの閉形式を門に、球の押し込みから力を読む](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacsim_elastic_membrane/01_tacsim_membrane_rgb_crop_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacsim_elastic_membrane/01_tacsim_membrane_rgb_crop.png)

*↑ **視触覚センサ(弾性膜 + カメラ)の合成と逆算 ―― Hertz 接触とフォトメトリックステレオの閉形式を門に、球の押し込みから力を読む** ―― 物理シミュ × Fullseye 系列の第 2 弾(「自作の罠は限界: 真値・門・被験者の 1 つを外から」)。外から来るものは閉形式 2 系統。弾性接触 = Hertz(Johnson, Contact Mechanics, CUP 1985: a³ = 3FR/(4E*)、δ = a²/R、p(r) = p0√(1 − r²/a²)、半空間の表面変位は内側 δ − r²/(2R)・外側 式 3.42a、r = a で値 δ/2 と傾き −a/R が連続)。光学 = Woodham 1980 のフォトメトリックステレオ N = L⁻¹I と Frankot-Chellappa 1988 の法線積分(弾性膜を 3 色の方向照明で撮って 1 枚で法線を読む原理は Johnson & Adelson, CVPR 2009)。自分で作ったのは 3 つ: 外側解の半径方向スロープの閉形式 dh/dr = (2/πR)[r arcsin(a/r) − a√(1 − a²/r²)](導出、数値微分と 5e-9 で一致)、それを法線場のスロープ分布に 1 パラメータ a で当てる逆算(高さの積分を通らないので FFT 積分の振幅減衰・有限窓・オフセットの影響を受けない)、δ の 1D 積分に Boussinesq の遠方場 ū_z ≈ F/(πE*r) の裾 r_max·s̄(r_max) を足す窓打ち切りの補正。被験者は Fullseye の既存 op(photometric_stereo / integrate_normals / surface_normals / render_lambertian、measure.fit_circle)。新モジュール tacsim 14 op。図は圧痕まわりの等倍切り出し(62.5 µm/px、a = 0.88 mm = 14 px)、球・円柱・直線エッジ・F 字スタンプの合成像と復元高さ、荷重を 0.005 → 0.12 N に上げる GIF(左 合成像、右 Hertz の a–F 曲線に点が増える)、復元高さと真値の断面、スロープ分布と Hertz 模型、a–F に 2 経路の測定点、壊れる場所(較正ずれ・雑音)。門 17 本: 複合弾性率の極限、Hertz の恒等式(1e-9)、圧力の面積分 = F・線積分 = F/L(0.1 %)、表面変位の内外連続とスロープの導出検算、Frankot-Chellappa の往復 0.11 µm(δ = 261 µm)、Woodham の厳密性(中央 0.0001°)、当てはめ経路 a 0.05〜0.26 %・F 0.14〜0.79 %(0.02〜0.12 N)、δ 経路 δ 0.28〜0.84 %・F 0.43〜1.26 %、模型なしのリングは −8.2〜−4.9 %(分解能の予測 −0.7 px/a = −7.8〜−4.3 % と 1 pt 以内)、a ∝ F^{1/3}(指数 0.3335)、窓打ち切りの不足 4.37 %(閉形式 ū_z(r_max)/δ = 4.7 %)、ambient 0.03 を引かないと δ が 3.17 % 低い(予測 ambient/sin 55° = 3.7 %)、仰角 15° の較正ずれは斜面 0.00° → 5.69°・平坦域 0.05°、雑音 σ = 0.03 で法線 2.7° でも F 0.5 %、4 形状の往復 RMS 0.4〜0.6 µm(スタンプは 60° の壁の付着影で 10.8 µm)、円柱の幾何接触半幅 √(2Rd − d²) = 1.308 mm(実測 1.312)、tac_contact_mask は recall 0.92 だが面積 1.78 倍。正直に: 小変形 Hertz(δ/R ≈ 0.09)、Lambertian・影なし・鏡面なし、半無限の膜、粘弾性・マーカーなし。模型なしのリングは a = 14 px では 5 % 内側(当てはめ経路が主、リングは第 2 実装)。踏んだ罠: |∇h| のしきい値の帯は非対称なカスプで 9 % 内側に寄る、FFT 積分は深い局所のへこみを 13 % 減衰、ambient 項が法線を 3.7 % 寝かせる(実機の参照フレーム較正に当たる引き算が要る)。門だけ 0.7 s、図込み 12 s。*

[![球・円柱・直線エッジ・F 字スタンプを 0.3 mm 押し込んだ膜(幾何学的な追従、弾性の裾なし、46.9 µm/px、中央 ±1.9 mm を 3 倍)。上 = 3 色照明の合成像、下 = フォトメトリックステレオ + Frankot-C](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacsim_elastic_membrane/02_tacsim_four_shapes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacsim_elastic_membrane/02_tacsim_four_shapes.png)

*↑ 測定の図 ―― 球・円柱・直線エッジ・F 字スタンプを 0.3 mm 押し込んだ膜(幾何学的な追従、弾性の裾なし、46.9 µm/px、中央 ±1.9 mm を 3 倍)。上 = 3 色照明の合成像、下 = フォトメトリックステレオ + Frankot-Chellappa で復元した高さ(接触域の RMS を併記)。*

[![中央行の断面。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacsim_elastic_membrane/04_tacsim_height_cross_section_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacsim_elastic_membrane/04_tacsim_height_cross_section.png)

*↑ 中央行の断面。*

[![法線場から取った半径方向スロープの方位平均(点)と、1 パラメータ a で当てた Hertz のスロープ模型(破線: 内側 r/R、外側 (2/πR)[r arcsin(a/r) − a√(1−a²/](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacsim_elastic_membrane/05_tacsim_slope_profile_fit_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacsim_elastic_membrane/05_tacsim_slope_profile_fit.png)

*↑ 法線場から取った半径方向スロープの方位平均(点)と、1 パラメータ a で当てた Hertz のスロープ模型(破線: 内側 r/R、外側 (2/πR)[r arcsin(a/r) − a√(1−a²/r²)])。*

[![破線 = Hertz の閉形式。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacsim_elastic_membrane/06_tacsim_hertz_a_vs_F_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacsim_elastic_membrane/06_tacsim_hertz_a_vs_F.png)

*↑ 破線 = Hertz の閉形式。*

[![壊れる場所: 法線の角誤差 [deg)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacsim_elastic_membrane/07_tacsim_failure_modes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacsim_elastic_membrane/07_tacsim_failure_modes.png)

*↑ 壊れる場所: 法線の角誤差 [deg]。*

[![荷重を 0.005 → 0.12 N に上げる(12 コマ)。左 = 圧痕まわり ±2.0 mm の合成像(62.5 µm/px を 4 倍)、右 = Hertz の a–F 曲線(破線 = 閉形式)に、各コマの像から当てはめ経路で読んだ ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacsim_elastic_membrane/03_tacsim_force_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacsim_elastic_membrane/03_tacsim_force_sweep.gif)

*↑ 動く図 ―― 荷重を 0.005 → 0.12 N に上げる(12 コマ)。左 = 圧痕まわり ±2.0 mm の合成像(62.5 µm/px を 4 倍)、右 = Hertz の a–F 曲線(破線 = 閉形式)に、各コマの像から当てはめ経路で読んだ a が点として増えていく。*

```
py -3.11 examples/poc_tacsim_elastic_membrane.py
```

ソース: [examples/poc_tacsim_elastic_membrane.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_tacsim_elastic_membrane.py)

この回が作った図は全部で **7 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_tacsim_elastic_membrane)

使用 op(ノートへ): [`combined_modulus`](https://furuse.work/ops/drive/tacsim/combined_modulus.html) · [`contact_radius_fit`](https://furuse.work/ops/drive/tacsim/contact_radius_fit.html) · [`contact_radius_ring`](https://furuse.work/ops/drive/tacsim/contact_radius_ring.html) · [`hertz_cylinder`](https://furuse.work/ops/drive/tacsim/hertz_cylinder.html) · [`hertz_force`](https://furuse.work/ops/drive/tacsim/hertz_force.html) · [`hertz_pressure`](https://furuse.work/ops/drive/tacsim/hertz_pressure.html) · [`hertz_sphere`](https://furuse.work/ops/drive/tacsim/hertz_sphere.html) · [`hertz_surface_uz`](https://furuse.work/ops/drive/tacsim/hertz_surface_uz.html) · [`integrate_normals`](https://furuse.work/ops/3d/photometric/integrate_normals.html) · [`membrane_delta_from_normals`](https://furuse.work/ops/drive/tacsim/membrane_delta_from_normals.html) · [`membrane_indent_shape`](https://furuse.work/ops/drive/tacsim/membrane_indent_shape.html) · [`membrane_indent_sphere`](https://furuse.work/ops/drive/tacsim/membrane_indent_sphere.html) · [`membrane_lights`](https://furuse.work/ops/drive/tacsim/membrane_lights.html) · [`membrane_recover`](https://furuse.work/ops/drive/tacsim/membrane_recover.html) · [`membrane_render_rgb`](https://furuse.work/ops/drive/tacsim/membrane_render_rgb.html) · [`photometric_stereo`](https://furuse.work/ops/3d/photometric/photometric_stereo.html) · [`tac_contact_mask`](https://furuse.work/ops/2d/tactile/tac_contact_mask.html)

## No.2026.198 —— 視触覚センサのマーカー配列からせん断場・固着/滑り・接線力を読む ―― Cattaneo–Mindlin の閉形式と有限要素の節点変位を門に

[![視触覚センサのマーカー配列からせん断場・固着/滑り・接線力を読む ―― Cattaneo–Mindlin の閉形式と有限要素の節点変位を門に](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacsim_marker_shear/01_tacslip_marker_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacsim_marker_shear/01_tacslip_marker_frames.png)

*↑ **視触覚センサのマーカー配列からせん断場・固着/滑り・接線力を読む ―― Cattaneo–Mindlin の閉形式と有限要素の節点変位を門に** ―― 物理シミュ × Fullseye 系列 第 2 弾の第 2 本(第 1 本 = 法線荷重の押し込みから力)。外から来るものは 2 系統。閉形式(Johnson, Contact Mechanics, CUP 1985): Cattaneo 1938 / Mindlin 1949 の部分滑り(§7.2)―― 球を法線 P で押したまま接線 Q < μP を掛けると固着円 c/a = (1 − Q/μP)^{1/3}、接線トラクション q = q′ − q″(Hertz 形 2 つの差、滑り環では Coulomb の限界 μp(r) に張り付く)、剛体球の接線変位 δx = 3μP(2−ν)/(16Ga)[1 − (1−Q/μP)^{2/3}]、初期接線剛性 kt = 8Ga/(2−ν)、固着円内の表面変位は一様。Hertz 形接線トラクションの円内解(式 3.91)、法線荷重の半径変位(式 3.41b)、接線点荷重の半空間解 = Cerruti(式 3.22)。有限要素の節点変位(有限厚のドーム状ゲル、Robo-Touch/Taxim リポジトリ同梱、MIT。環境変数 FULLSEYE_TAXIM_DATA があるときだけ、repo には入れない)。公表の定性値(Yuan, Dong, Adelson, Sensors 2017): 滑りは周縁から、変位ヒストグラムのエントロピーは部分滑りで増える。自分で作ったのは 3 つ: 接触円の外側と滑り環の接線変位には閉形式が無いので Cerruti 核を画素平均(中心画素は解析積分 4h ln(1+√2))で離散化して FFT で畳む(円内の 3.91 と ūx 0.017 %・ūy 0.03 %、固着円の一様性 std 0.006 %)、任意の固着半径の場を相似則 g(x) − (c/a)²g(x·a/c) で出す逆算模型(畳み込み 1 回、真の変位で c/a 0.001)、マーカー像は変位で中心を移してから描く(補間しない)。被験者は Fullseye の既存 op: blob2d.blob_label / blob_features(重心)、pivops.piv_cross_correlate(窓相関、第 2 実装)、backends_subpix の副画素極値、backends_tactile.tac_shear_field(別被験者)、measure.fit_circle、tacsim の Hertz と膜の合成。新モジュール tacslip 20 op。寸法は分解能の罠を先に潰して決めた: R = 6 mm・P = 0.5 N・E 0.2 MPa・ν 0.48 → a = 2.05 mm = 32.9 px(62.5 µm/px)、マーカー 0.5 mm = 8 px(半径 2.5 px)で接触円内 53 個、全滑り δx = 514 µm = 8.2 px、μ = 0.5 は仮定(計画書の錨 70.5 µm を再現する値)。図は基準像/荷重後/追跡ベクトルの 3 連(固着円の中は一様に動き、滑り環で遅れ、外側は 1/r)、接線力を 0 → μP に上げる GIF(閉形式の固着円 緑と画像から当てた c 赤が重なり、全滑りで核が消える)、q(r) の 2 項、δx–Q(閉形式線と固着核の中央値)、エントロピー vs Q/μP、有限要素 vs 半空間(r·u の減衰と dx(θ) の角度依存)、壊れる場所(格子エイリアス・密度・雑音)。門 20 本(有限要素の 2 本はデータがあるとき、門だけ 2.8 s、図込み 19 s): ∫q dA = Q(6e-7)、c/a の閉形式と全滑りの印、dδx/dQ(0) = 1/kt(1e-6)と錨 70.6 µm、ūr(a)/δ = 2(1−2ν)/(3π(1−ν)) = 1.6 %(導出)、Cerruti 畳み込み vs 3.91、固着円の一様性、遠方 1/r(3a で 1.016)、重心の往復(反復ガウス重み 0.003 px・二値 0.16 px、格子共通のバイアス 0.010 → 0.004 px)、法線荷重だけでは最大 0.187 px = |ūr| の最大(r = 0.93a、ūr(a) の 1.022 倍)、追跡 RMS 0.007〜0.010 px(Q/μP 0.25〜0.9、961/961 対応)、PIV は 8 px 格子を 5 px ずらすと −3.000 px(ジッタ格子で 4.999)・探索を ±3.8 px に絞れば固着円で 0.03 px、逆算 Q/μP 誤差 0.026 → 0.007・c/a 0.011・Q 0.4〜0.9 %・μ 10.2 → 1.2 %(μ と Q は G・ν・a 既知なら別々に決まるが、μ の誤差は c/a の 2c/(1−c²) 倍 = 10.4 → 1.2 倍に増幅)、模型なしの固着半径は 2.3〜4.7 px(= ピッチの分解能)、全滑りで c/a 0.000・核のばらつき 42 %、指数 0.341(閉形式 1/3)、エントロピー 0.078 → 0.677 で単調非減少、tac_shear_field は核 0.043・環 0.039 で分けない、マーカー間隔 16 px(円内 13 個)でも Q/μP 0.03 以内・画素雑音 σ 0.05 で追跡 RMS 0.031 px、有限要素は r·dz が 1/r から 2 倍外れる r½ = 2.27 mm(1 mm 0.88・2 mm 0.57・3 mm 0.32)、斜め荷重の dx(θ) は r = 1.5〜2 mm で Cerruti の A + B cos²θ(R² 0.78〜0.80)に乗り ν 0.49〜0.51、r = 3 mm では比 2.4 > 半空間の上限 2。正直に: 半空間・小変形・剛体球・Coulomb・準静的(incipient slip の時間発展・粘弾性なし、全滑り近くの縁はせん断ひずみ 0.25 で線形の外)、μ は低 Q で決まりにくい(Q/μP 0.25 で 10 %)、有限要素は点荷重状(接触 < 節点間隔 0.16 mm)で固着円は試せず荷重も不明(形の比較だけ、dz ケースにも dy/dz = 0.25 の非対称)、相関と最近傍は |u| ≥ ピッチ/2 を原理的に測れない(対応は「視野の縁は遠方場」という前提に依る)、53 個のマーカーではエントロピーに段がつく。踏んだ罠: 規則格子に相関を当てると格子周期でエイリアス(多段 64→32 は第 1 段が ±8/±16 に飛ぶ)、核の変位 6.4 px は隣の基準位置から 1.6 px なので最近傍の種も飛ぶ(縁から連続性で伸ばす)、半径 2 px の円盤の重心は ±0.03 px の pixel-locking が格子共通モードになり c/a を 0.02 ずらす(半径 2.5 px + 反復ガウス重みで 3 分の 1、剛体シフト項は 1/r の尾と縮退して逆効果)、ūr の最大は縁でなく 0.93a、滑り環で隣接間隔が 8 → 6 px に縮み低しきい値の縞が繋がる、c/a 格子の線形補間模型は 0.01 ずれる。δx_full ≈ マーカーピッチは最悪の組 ―― 実機設計はピッチ > 2·δx_full か非周期配置。*

[![接線力を 0 → μP に上げる(12 コマ)。左 = マーカー像 + 追跡ベクトル(4 倍)、緑 = 閉形式の固着円 c = a(1 − Q/μP)^{1/3}、赤 = 画像から当てた c、白 = 接触円 a。右 = c/a の閉形式(破](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacsim_marker_shear/02_tacslip_stick_circle_shrinks.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacsim_marker_shear/02_tacslip_stick_circle_shrinks.gif)

*↑ 測定の図 ―― 接線力を 0 → μP に上げる(12 コマ)。左 = マーカー像 + 追跡ベクトル(4 倍)、緑 = 閉形式の固着円 c = a(1 − Q/μP)^{1/3}、赤 = 画像から当てた c、白 = 接触円 a。右 = c/a の閉形式(破線)に各コマの推定点が増える。Q = μP で核が消え全滑り。*

[![接線トラクション q(r) = μp0[√(1−r²/a²) − (c/a)√(1−r²/c²))。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacsim_marker_shear/03_tacslip_traction_q_r_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacsim_marker_shear/03_tacslip_traction_q_r.png)

*↑ 接線トラクション q(r) = μp0[√(1−r²/a²) − (c/a)√(1−r²/c²)]。*

[![剛体球の接線変位 δx = 3μP(2−ν)/(16Ga)[1 − (1−Q/μP)^{2/3}) (破線)と初期剛性 kt = 8Ga/(2−ν) の直線(点線)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacsim_marker_shear/04_tacslip_delta_x_vs_Q_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacsim_marker_shear/04_tacslip_delta_x_vs_Q.png)

*↑ 剛体球の接線変位 δx = 3μP(2−ν)/(16Ga)[1 − (1−Q/μP)^{2/3}] (破線)と初期剛性 kt = 8Ga/(2−ν) の直線(点線)。*

[![接触円内のマーカー変位の大きさのヒストグラム(16 ビン)のエントロピー。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacsim_marker_shear/05_tacslip_entropy_vs_Q_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacsim_marker_shear/05_tacslip_entropy_vs_Q.png)

*↑ 接触円内のマーカー変位の大きさのヒストグラム(16 ビン)のエントロピー。*

[![第 2 真値: 有限要素の節点変位(ドーム状の有限厚ゲル、Robo-Touch/Taxim リポジトリ同梱、MIT)と半空間解。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacsim_marker_shear/06_tacslip_fem_vs_halfspace_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacsim_marker_shear/06_tacslip_fem_vs_halfspace.png)

*↑ 第 2 真値: 有限要素の節点変位(ドーム状の有限厚ゲル、Robo-Touch/Taxim リポジトリ同梱、MIT)と半空間解。*

```
py -3.11 examples/poc_tacsim_marker_shear.py
```

ソース: [examples/poc_tacsim_marker_shear.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_tacsim_marker_shear.py)

この回が作った図は全部で **7 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_tacsim_marker_shear)

使用 op(ノートへ): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`cerruti_kernel`](https://furuse.work/ops/drive/tacslip/cerruti_kernel.html) · [`cerruti_surface_displacement`](https://furuse.work/ops/drive/tacslip/cerruti_surface_displacement.html) · [`combined_modulus`](https://furuse.work/ops/drive/tacsim/combined_modulus.html) · [`displace_markers`](https://furuse.work/ops/drive/tacslip/displace_markers.html) · [`fem_nodes_load`](https://furuse.work/ops/drive/tacslip/fem_nodes_load.html) · [`fem_vs_halfspace`](https://furuse.work/ops/drive/tacslip/fem_vs_halfspace.html) · [`hertz_pressure`](https://furuse.work/ops/drive/tacsim/hertz_pressure.html) · [`hertz_sphere`](https://furuse.work/ops/drive/tacsim/hertz_sphere.html) · [`hertz_surface_ur`](https://furuse.work/ops/drive/tacslip/hertz_surface_ur.html) · [`hertzian_tangential_inner`](https://furuse.work/ops/drive/tacslip/hertzian_tangential_inner.html) · [`marker_detect`](https://furuse.work/ops/drive/tacslip/marker_detect.html) · [`marker_image`](https://furuse.work/ops/drive/tacslip/marker_image.html) · [`marker_track`](https://furuse.work/ops/drive/tacslip/marker_track.html) · [`membrane_indent_sphere`](https://furuse.work/ops/drive/tacsim/membrane_indent_sphere.html) · [`membrane_lights`](https://furuse.work/ops/drive/tacsim/membrane_lights.html) · [`membrane_markers`](https://furuse.work/ops/drive/tacslip/membrane_markers.html) · [`membrane_render_markers`](https://furuse.work/ops/drive/tacslip/membrane_render_markers.html) · [`membrane_render_rgb`](https://furuse.work/ops/drive/tacsim/membrane_render_rgb.html) · [`membrane_shear_field`](https://furuse.work/ops/drive/tacslip/membrane_shear_field.html) · [`mindlin_fit`](https://furuse.work/ops/drive/tacslip/mindlin_fit.html) · [`mindlin_model`](https://furuse.work/ops/drive/tacslip/mindlin_model.html) · [`mindlin_partial_slip`](https://furuse.work/ops/drive/tacslip/mindlin_partial_slip.html) · [`mindlin_traction`](https://furuse.work/ops/drive/tacslip/mindlin_traction.html) …(他 5)

## No.2026.199 —— 視触覚センサのマーカー場から「触覚双極子」で把持内の傾き・ねじりトルクを読む ―― Gauss の法則が半空間で恒等式になることを門に

[![視触覚センサのマーカー場から「触覚双極子」で把持内の傾き・ねじりトルクを読む ―― Gauss の法則が半空間で恒等式になることを門に](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tactile_dipole_torque/01_tactorque_marker_field_dipole_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tactile_dipole_torque/01_tactorque_marker_field_dipole.png)

*↑ **視触覚センサのマーカー場から「触覚双極子」で把持内の傾き・ねじりトルクを読む ―― Gauss の法則が半空間で恒等式になることを門に** ―― 物理シミュ × Fullseye 系列 第 2 弾の第 3 本(第 1 本 = 法線荷重の押し込みから力、第 2 本 = マーカー配列からせん断と固着/滑り)。再実装した方法は Fuchioka & Hamaya, ICRA 2024(arXiv 2404.15626): 学習なし・光学模型なしで、マーカー変位場 v の発散 ∇·v を「電荷」(法線力の分布、Gauss の法則の類推)と見て双極子 p = (1/N) Σ r_i (∇·v)_i を取り(原点は正負の電荷の重心の中点)、傾きトルクは双極子に直交 τ = [c_x p_y, −c_y p_x](係数 c は力覚センサで線形に較正)。手順の要は把持後に零点を取ること。著者のコードは無ライセンスなので読まず、本文の式だけから書いた。センサは retrographic sensing(Johnson & Adelson 2009)系。外から来るものは 2 系統。閉形式(Johnson, Contact Mechanics, CUP 1985): 平頭円形押し込み子の圧 p = P/(2πa√(a²−r²))(式 3.34)に傾きモーメントの反対称項 3Mx/(2πa³√(a²−r²))(∫ x p dA = M、離れない条件 M ≤ Pa/3、導出)、法線点荷重の半空間表面変位 = Boussinesq(§3.2: ū_r = −(1−2ν)P/(4πGr)、ū_z = (1−ν)P/(2πGr))、Hertz 圧の表面変位(式 3.41b・3.42a)、楕円 Hertz 圧(式 4.24)、無滑りねじり(Reissner–Sagoci)q_θ = 3M_z r/(4πa³√(a²−r²))・β = 3M_z/(16Ga³)、Cattaneo–Mindlin の部分滑り(前作)。有限要素の節点変位(有限厚のドーム状ゲル、Robo-Touch/Taxim リポジトリ同梱、MIT。環境変数 FULLSEYE_TAXIM_DATA があるときだけ、repo には入れない)。自分で導いたのは 3 つ(全部門に): Gauss の法則は半空間で厳密 —— 2 次元で ∇·(r̂/r) = 2πδ² なので ∇·ū = −(1−2ν)p/(2G)、だから面積重みの双極子は圧力の 1 次モーメント(= 傾きモーメント M)に比例し押し込み子の形に依らない(ただし係数 −(1−2ν)/(2G) は ν → 0.5 で消える: 実機の信号は有限厚ゲルの膨らみから来る); Cerruti 点荷重の場の発散 −(1−ν)Qx/(2πGr³) —— 純せん断は窓全体に (1−ν)/(1−2ν)·Q·R の偽の傾き(ν 0.48 で 13·Q·R)を作るので窓を固着円に限る(傾きは縁の特異点に電荷が集中するので窓 ≥ a + 1.5 ピッチが要り、両立しないから小さい窓では固定比 0.47 を較正で吸収する); 基線形式(|u| を電荷に)は零点後の対称な傾きで |u| が M の偶関数なので恒等的に 0。被験者 = 既存 op: tacslip.marker_track(重心と対応)、tacslip.cerruti_kernel の畳み込み(ねじりの独立実装)、sceneflow.flow_divergence / flow_curl(格子の第 2 実装)、pivops.piv_vorticity(符号規約 (dy, dx) で −curl)。新モジュール tactorque 17 op。寸法: 平頭 a = 3 mm、P = 2 N(離れの限界 M = 2 N·mm)、視野 16 mm、門の格子 128 px(125 µm/px)、像の格子 256 px(62.5 µm/px)、マーカー 0.5 mm。図: マーカー像 + 追跡ベクトル(40 倍)+ 双極子矢印(等倍切り出し)と追跡場の発散地図、M を 0 → 1.5 N·mm に上げる GIF(双極子が伸び、点が閉形式の線に乗る)、分解の地図(発散 → 傾き、curl → ねじり、平均 → 並進)、FEM の法線 vs 斜め(発散の散布 + 半径プロファイル)、壊れる場所(雑音 ∝ σ、窓半径で 6 桁動くせん断漏れ、窓中心 2 mm ずれで −57 %)、3 形状の係数。門 17 本(FEM 2 本はデータがあるとき、FEM なしの実測で門だけ 2.0 s、図込み 29 s): 平頭圧の格子積分 Σp h² = P 0.57 %・Σx p h² = M 0.86 %(縁 1/√ の格子誤差)と離れの fail-closed、Boussinesq 核 vs 3.41b 0.03 % / 3.42a 0.01 % / 平頭 u_z 0.35 %、Gauss 恒等式 0.21 %(ν 0.48 と 0.3 で同じ = (1−2ν) スケーリングの確認)、純法線で双極子 8e-16(3 形式)、D ∝ M は R² = 1.000000・係数は閉形式と 0.035 %・D_y/D_x 4e-4・原点不変 1e-4(格子の正味電荷 −8e-4)、基線形式 3e-4、3 形状(平頭・球・稜)で係数のばらつき 密 0.001 % / 0.5 mm 格子 0.25 %、ねじり ∫r q dA = M_z 0.99・β −0.47 %・一様性 0.14 %・剛体回転 −0.5 %・curl −0.5 %・piv_vorticity = −curl 1e-16(平頭押し込み子は q/(μp) の最大 0.238 で無滑りが厳密)、Hertz 接触のねじりの部分滑り(全滑りまでの比 0.5 / 0.8 の像)を既定の読みで ×0.999 / ×1.000、0.4.0 の無滑りの関係なら ×1.330 / ×1.851 過大(2026-10-06 の直し: 旧の門は合成も読みも無滑りだったので過大に気づかなかった)、重ね合わせの分解 傾き 2.35 %(ねじり → 傾きの漏れ、傾き単独 0.22 %)・ねじり 0.5 %・並進 0.038 px、純せん断の漏れ ≤ 0.0012 N·mm(固着円 − 当てはめ半径)/ 32.5 N·mm(全窓、導出 31.2)、雑音 0.03 px → σ_M = 0.114 N·mm(窓 1.5a、252 個)・全窓 0.72・0.01 px で 0.038(∝ σ)、綴り壊し 11/11 + nan ≠ 0、散在最小二乗 = 中心差分 1e-15(5 点; 9 点は縁で 11 % 違う)、像から M1 誤差 0.7 %・追跡 RMS 0.0054 px・961/961 対応、FEM は核の発散 +0.019 と環 −0.0036(膨らみ、半空間と符号が逆)、斜め荷重の双極子 ΔD_x = −6.4e-11 m³ で Δt_x = +19 µm(せん断漏れの符号)。正直に: 半空間の係数は実機(有限厚・ほぼ非圧縮)の大きさを与えない(ν 0.48 で 1 N·mm が 0.06 px、実機は較正という論文の立場と同じ)、Johnson の式番号のうち傾いた平頭・平頭の u_z・Reissner–Sagoci は本文で未確認(独立実装で数値検証)、Lubkin 1951 の部分滑りねじりの閉形式は未実装(部分滑りは cuttouch の数値解で直す)、論文の「係数は物体ごとに違う」は有限厚で起きること(半空間では形状不変)で本 PoC では実機を試していない、粘弾性・incipient slip の時間発展・optical flow は扱わない。踏んだ罠: 9 点(3×3)の平面当ては行平均の差分で縁で 11 % ずれる(5 点で中心差分と一致)、平均 curl/2 は縁で 11 % 低い(剛体回転の最小二乗で)、格子の副画素位相の非対称をねじりが拾って傾きに 2 % 漏れる、原点不変の門は格子の正味電荷 1e-3 で破れるので 1e-6 でなく 1e-3。*

[![傾きモーメントを 0 → 1.5 N·mm に 7 段で上げる。左 = マーカー 1 個ごとの発散(赤 +・青 −、押し込み子の縁に正負の対が立つ)と変位(60 倍)、赤矢印 = 双極子(長さ ∝ M)。右 = 格子マーカーの双極子 D_x](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tactile_dipole_torque/02_tactorque_dipole_grows_with_M.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tactile_dipole_torque/02_tactorque_dipole_grows_with_M.gif)

*↑ 測定の図 ―― 傾きモーメントを 0 → 1.5 N·mm に 7 段で上げる。左 = マーカー 1 個ごとの発散(赤 +・青 −、押し込み子の縁に正負の対が立つ)と変位(60 倍)、赤矢印 = 双極子(長さ ∝ M)。右 = 格子マーカーの双極子 D_x が閉形式の線 −(1−2ν)/2G·M1(破線)に乗る: R² = 1.000000、傾きの比 0.9997。*

[![重ね合わせた場(傾き 1 N·mm + ねじり 0.5 N·mm + 並進 1 px)を 3 つに分ける: 発散の双極子が傾き(M1 = 1.015 N·mm、真値 0.991、窓 a + 当てはめ半](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tactile_dipole_torque/03_tactorque_decomposition_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tactile_dipole_torque/03_tactorque_decomposition_maps.png)

*↑ 重ね合わせた場(傾き 1 N·mm + ねじり 0.5 N·mm + 並進 1 px)を 3 つに分ける: 発散の双極子が傾き(M1 = 1.015 N·mm、真値 0.991、窓 a + 当てはめ半径)、剛体回転の最小二乗がねじり(M_z = 0.497 N·mm、真値 0.500、窓 0.9a)…*

[![第 2 真値: 有限要素の節点変位(有限厚のドーム状ゲル、Robo-Touch/Taxim リポジトリ同梱、MIT、節点 15,230・間隔 0.155 mm)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tactile_dipole_torque/04_tactorque_fem_oblique_vs_normal_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tactile_dipole_torque/04_tactorque_fem_oblique_vs_normal.png)

*↑ 第 2 真値: 有限要素の節点変位(有限厚のドーム状ゲル、Robo-Touch/Taxim リポジトリ同梱、MIT、節点 15,230・間隔 0.155 mm)。*

[![壊れる場所。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tactile_dipole_torque/05_tactorque_where_it_breaks_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tactile_dipole_torque/05_tactorque_where_it_breaks.png)

*↑ 壊れる場所。*

[![圧力の 1 次モーメントが同じ 1 N·mm の 3 つの押し込み子: 平頭にモーメント、Hertz 球を M/P だけずらす、細長い楕円(稜)をずらす。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tactile_dipole_torque/06_tactorque_shape_coefficient_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tactile_dipole_torque/06_tactorque_shape_coefficient.png)

*↑ 圧力の 1 次モーメントが同じ 1 N·mm の 3 つの押し込み子: 平頭にモーメント、Hertz 球を M/P だけずらす、細長い楕円(稜)をずらす。*

```
py -3.11 examples/poc_tactile_dipole_torque.py
```

ソース: [examples/poc_tactile_dipole_torque.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_tactile_dipole_torque.py)

この回が作った図は全部で **6 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_tactile_dipole_torque)

使用 op(ノートへ): [`boussinesq_kernel`](https://furuse.work/ops/drive/tactorque/boussinesq_kernel.html) · [`boussinesq_surface_displacement`](https://furuse.work/ops/drive/tactorque/boussinesq_surface_displacement.html) · [`cerruti_kernel`](https://furuse.work/ops/drive/tacslip/cerruti_kernel.html) · [`combined_modulus`](https://furuse.work/ops/drive/tacsim/combined_modulus.html) · [`dipole_to_torque_fit`](https://furuse.work/ops/drive/tactorque/dipole_to_torque_fit.html) · [`dipole_torque_resolution`](https://furuse.work/ops/drive/tactorque/dipole_torque_resolution.html) · [`displace_markers`](https://furuse.work/ops/drive/tacslip/displace_markers.html) · [`ellipse_pressure_shifted`](https://furuse.work/ops/drive/tactorque/ellipse_pressure_shifted.html) · [`fem_nodes_load`](https://furuse.work/ops/drive/tacslip/fem_nodes_load.html) · [`grasp_torque_frame`](https://furuse.work/ops/drive/tactorque/grasp_torque_frame.html) · [`hertz_pressure`](https://furuse.work/ops/drive/tacsim/hertz_pressure.html) · [`hertz_pressure_shifted`](https://furuse.work/ops/drive/tactorque/hertz_pressure_shifted.html) · [`hertz_sphere`](https://furuse.work/ops/drive/tacsim/hertz_sphere.html) · [`hertz_surface_ur`](https://furuse.work/ops/drive/tacslip/hertz_surface_ur.html) · [`hertz_surface_uz`](https://furuse.work/ops/drive/tacsim/hertz_surface_uz.html) · [`marker_divergence`](https://furuse.work/ops/drive/tactorque/marker_divergence.html) · [`marker_image`](https://furuse.work/ops/drive/tacslip/marker_image.html) · [`membrane_lights`](https://furuse.work/ops/drive/tacsim/membrane_lights.html) · [`membrane_markers`](https://furuse.work/ops/drive/tacslip/membrane_markers.html) · [`membrane_render_markers`](https://furuse.work/ops/drive/tacslip/membrane_render_markers.html) · [`membrane_render_rgb`](https://furuse.work/ops/drive/tacsim/membrane_render_rgb.html) · [`membrane_shear_field`](https://furuse.work/ops/drive/tacslip/membrane_shear_field.html) · [`mindlin_partial_slip`](https://furuse.work/ops/drive/tacslip/mindlin_partial_slip.html) · [`pad_context`](https://furuse.work/ops/drive/pegtactile/pad_context.html) …(他 12)

## No.2026.202 —— 粉体の山を画像で測る ―― 安息角・体積・質量・流動性・排出率を規則だけで、真値は閉形式・公表値・MuJoCo

[![粉体の山を画像で測る ―― 安息角・体積・質量・流動性・排出率を規則だけで、真値は閉形式・公表値・MuJoCo](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_granular_heap_repose/01_granular_heap_side_view_two_lines_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_granular_heap_repose/01_granular_heap_side_view_two_lines.png)

*↑ **粉体の山を画像で測る ―― 安息角・体積・質量・流動性・排出率を規則だけで、真値は閉形式・公表値・MuJoCo** ―― 物理シミュ × Fullseye 系列(pegsim / tacsim / tacslip / tactorque / puck / pegfail に続く)。先行研究の粉体計量(Kadokawa, Hamaya, Tanaka, IROS 2023, doi 10.1109/iros55552.2023.10342463)は秤の質量だけを観測に使い、視覚は無い。ここは山の形(側面像・高さ図)から安息角・体積・質量・流動性・排出率を読む側を、新モジュール granular(23 op + mujoco の facade 2)で学習なしに組む。外から来る真値は 4 系統。(1) 閉形式: 円錐 V = (π/3)R²H、H = R tan φ、m = ρ_b V; Beverloo, Leniger, van de Velde 1961 の排出則 W = C ρ_b √g (D₀ − k d)^{5/2}(C ≈ 0.58、k ≈ 1.4、Nedderman 1992 の整理)。(2) 公表の表: USP 一般章 <1174> Powder Flow の Table 1(安息角 → 流動性区分、原典 Carr 1965)—— 表は整数の度なので四捨五入して引く(30.4 → excellent、30.5 → good、25 度未満は表の外)。(3) 公表値: 1 mm ガラス球の安息角 25.2 ± 0.8 度(Sunday, Murdoch, Tardivel, Schwartz, Michel, MNRAS 2020、arXiv 2009.10448 §5.4)。側面像の上縁に左右別々に直線を当て、裾と頂を除く測り方(§5.3)も同論文から取った。(4) 第 2 実装(--full): MuJoCo 3 の剛体球 1,200 個(r 4 mm、滑り摩擦 0.16、転がり 0.09·R)を平底ホッパの正方孔(48 mm)から流して山を作る。側面像の計測は縁の画素の被覆率をそのまま副画素の位置に読む(edge 法): 被覆率に一様雑音 ±0.1 を足しても 0.0064 度。★列和法(被覆率の列和 = 粉の高さ)は [0, 1] に切った雑音で粉の平均値が 0.975 になり、tan φ がその比で縮んで −0.63 度 —— 最初は「裾の丸みの偏り」と誤読しかけ、丸みを 0 にしても残ったので気づいた。高さ図は demops.dem_slope の勾配ヒストグラムの最頻(雑音は勾配を上にしか動かさない: σ 0.05 px で +0.12 度、0.1 px で +0.37 度)。★傾いた基準面 β = 5 度は安息角に足し算される: 左右の斜面は 33.62 / 26.10 度 = 閉形式 atan(tan φ ± tan β)、左右差 7.52 度で警報(datum_tilt_check)、tan の引き算で 30.0000 度に戻る。高さ図の最頻は 5.00 度 = 地面そのもの(地面のセルがヒストグラムを乗っ取る; datum を渡せば 29.9994)。せん断型(datum)とカメラのロール(回転型)は片側の斜面で 1 次で違う(33.62 対 35.00 度)ので補正の種類を取り違えない。図: 側面像に当てた 2 直線(等倍)、勾配ヒストグラム、分解能で壊れる場所(山の幅 25〜400 px)、裾の丸み・頂の鈍り・傾いた基準面・幅 50 px の山(10 倍で画素が見える)、Beverloo の W(D₀)、流動性の帯に公表値と MuJoCo の値、スプーンの傾け、基準面の傾きを −8〜+8 度で振る GIF; --full: 球が孔から流れて山になる GIF(壁と底板の線つき)、球の山の側面に当てた直線と公表値 25.2 度の斜面、高さ図、排出の質量の列と Beverloo の傾き、MuJoCo と外の真値の表。門 20 本(numpy、1.3 s)+ --full 5 本(MuJoCo、34 s): 円錐の往復 1.8e-16、高さ図の体積 3.5e-7、側面像の往復 0.0000 度、Beverloo の指数 n = 2.5074・C = 0.5894(合成排出の高さ図の列 6 本、σ 0.5 mm; 雑音なし n = 2.5000000)、W(30 mm, 1 mm, 1500) = 0.3769 kg/s、裾の丸み −0.248 → 裾 15 % 除外で −0.001 度、頂の鈍り −0.554 → −0.004 度、分解能(雑音 ±0.1、4 角度 × 6 seed: 山の幅 50 px で側面 0.197 度、25 px で 0.624 度、高さ図は 50 px で 1.097 度)、流動性区分の境界 16 点、綴り壊しと山が写っていない・切れている場合の ValueError、スプーンの規則 θ_c = φ − atan(2h₀/L)(自分の導出: L 50 mm・h₀ 5 mm で 18.69 度、h₀ → 0 で φ。2026-10-05 に楔の傾きを小角の近似 tan φ − tan θ(この時 20.67 度)から厳密な tan(φ − θ) に直し、口に壁の無い器は θ = 0⁺ からこぼれる扱いを足した)、容器の充填率 0.6300 / 粉面の傾き 3.000 度、動画からの質量(同じ円錐を両辺に入れるので配管の検査)、MJCF 文字列、入口の棚卸し; --full: 山ができた(逃げ 0、ビンに残る滞留層 114、高さ 38.4 mm = 4.8 粒径)、側面 4 方位(22.4 / 23.0 / 18.9 / 24.4 度)の平均 22.17 度 vs 公表値 25.2 ± 0.8 → −3.03 度(門 −7〜+1)、2 粒径で平滑した高さ図の中央値 25.74 度(平滑なしの最頻 65.5 度 = 球の縁)、排出率 0.906 kg/s vs Beverloo(正方孔を等価直径 54.2 mm に、ρ_b 1312 kg/m³ はビンの実測)0.911 kg/s。正直に: 合成の側面像は縁の模型が計測と同じなので雑音なしの往復は配管の検査で、独立な被験者は雑音と MuJoCo の球だけ。MuJoCo の山が公表値より 3 度低い理由(剛体の軟接触で付着なし、転がり摩擦の模型が DEM と違う、山が 5 粒径しか無い、正方孔の流れで方位ごとに 18.9〜24.4 度)は切り分けていない。Beverloo との比 0.99 は一致が良すぎるので信用せず桁の門に留める(前の構成では 1.02 / 1.14、D₀/d = 6.8 は詰まりの限界付近、帯のコマ 14)。Al-Hashemi & Al-Amoudi 2018(CC BY 4.0)の材料別の表は取得できず未収録、Zhou ほか 2002 の経験式は未読。mg 級の計量は画像の体積分解能では無理(g 級の砕石・ビーズで成立、mg 級は秤に譲る)。容器の充填率は内寸 = 画像の仮定(壁の検出は未実装)。踏んだ罠: 滑らかな台(μ 0.16)では 1,200 球が半径 0.15 m の単層に広がり山にならなかった —— 1 球の実測で転がり抵抗は滑り摩擦の限界 μ_s g で飽和する(転がり係数 0.01 でも 0.1 でも減速 1.6 m/s²)ので粗い台 μ 1.0 にした(実験で底に紙やすりを貼るのと同じ)。軟接触の時定数 < 2·timestep は発散(op が拒否)、Newton 解法は密な山で 280 s を超えて止まる → CG + 楕円錐。*

[![高さ図の勾配ヒストグラム(demops.dem_slope)。雑音なしは 1 ビンに立つ。σ = 0.1 px の雑音で最頻が +0.12 度ずれる(|∇| は雑音で増えるだけ)—— 同じ大きさの雑音で側面像は 0.01 度も動かない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_granular_heap_repose/02_granular_slope_histogram_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_granular_heap_repose/02_granular_slope_histogram.png)

*↑ 測定の図 ―― 高さ図の勾配ヒストグラム(demops.dem_slope)。雑音なしは 1 ビンに立つ。σ = 0.1 px の雑音で最頻が +0.12 度ずれる(|∇| は雑音で増えるだけ)—— 同じ大きさの雑音で側面像は 0.01 度も動かない。*

[![山の幅(画素)と φ の最大誤差(2 角度 × 8 seed)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_granular_heap_repose/03_granular_where_it_breaks_resolution_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_granular_heap_repose/03_granular_where_it_breaks_resolution.png)

*↑ 山の幅(画素)と φ の最大誤差(2 角度 × 8 seed)。*

[![基準面が 5 度傾くと左右が 33.62 / 26.10 度に割れる(atan(tan φ ± tan β))。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_granular_heap_repose/06_granular_breaks_tilted_datum_view_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_granular_heap_repose/06_granular_breaks_tilted_datum_view.png)

*↑ 基準面が 5 度傾くと左右が 33.62 / 26.10 度に割れる(atan(tan φ ± tan β))。*

[![安息角 → 流動性区分(USP <1174> 表 1、原典 Carr 1965)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_granular_heap_repose/09_granular_flowability_bands_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_granular_heap_repose/09_granular_flowability_bands.png)

*↑ 安息角 → 流動性区分(USP <1174> 表 1、原典 Carr 1965)。*

[![同じ山の高さ図(単位 mm、球面の最大高さ、1.5 mm/セルを 3 倍の最近傍で表示)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_granular_heap_repose/14_granular_mujoco_heightmap_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_granular_heap_repose/14_granular_mujoco_heightmap.png)

*↑ 同じ山の高さ図(単位 mm、球面の最大高さ、1.5 mm/セルを 3 倍の最近傍で表示)。*

[![基準面の傾き β を −8〜+8 度で振る(32 コマ)。左右の斜面が atan(tan φ ± tan β) で割れ、左右差 ≈ 2β が 1 度を超えると警報。tan の引き算で 30 度に戻る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_granular_heap_repose/11_granular_datum_tilt_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_granular_heap_repose/11_granular_datum_tilt_sweep.gif)

*↑ 動く図 ―― 基準面の傾き β を −8〜+8 度で振る(32 コマ)。左右の斜面が atan(tan φ ± tan β) で割れ、左右差 ≈ 2β が 1 度を超えると警報。tan の引き算で 30 度に戻る。*

[![剛体球 1200 個(r 4 mm、滑り摩擦 0.16、転がり 0.09·R、粗い台)が平底ホッパ(青灰の線 = 壁と底板)の正方孔(48 mm)から流れて山になる(0.5 mm/px、67 コマ)。φ = 22.17 度(4 方位の平均)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_granular_heap_repose/12_granular_mujoco_heap_render_settling.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_granular_heap_repose/12_granular_mujoco_heap_render_settling.gif)

*↑ 動く図 ―― 剛体球 1200 個(r 4 mm、滑り摩擦 0.16、転がり 0.09·R、粗い台)が平底ホッパ(青灰の線 = 壁と底板)の正方孔(48 mm)から流れて山になる(0.5 mm/px、67 コマ)。φ = 22.17 度(4 方位の平均)。*

```
py -3.11 examples/poc_granular_heap_repose.py
```

ソース: [examples/poc_granular_heap_repose.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_granular_heap_repose.py)

この回が作った図は全部で **16 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_granular_heap_repose)

使用 op(ノートへ): [`beverloo_fit`](https://furuse.work/ops/drive/granular/beverloo_fit.html) · [`beverloo_rate`](https://furuse.work/ops/drive/granular/beverloo_rate.html) · [`container_fill_level`](https://furuse.work/ops/drive/granular/container_fill_level.html) · [`container_synth`](https://furuse.work/ops/drive/granular/container_synth.html) · [`datum_tilt_check`](https://furuse.work/ops/drive/granular/datum_tilt_check.html) · [`difference`](https://furuse.work/ops/2d/nary/difference.html) · [`discharge_synth`](https://furuse.work/ops/drive/granular/discharge_synth.html) · [`dispense_mass_from_video`](https://furuse.work/ops/drive/granular/dispense_mass_from_video.html) · [`heap_mass`](https://furuse.work/ops/drive/granular/heap_mass.html) · [`heap_scene_mjcf`](https://furuse.work/ops/drive/granular/heap_scene_mjcf.html) · [`heap_spheres_select`](https://furuse.work/ops/drive/granular/heap_spheres_select.html) · [`heap_synth_cone`](https://furuse.work/ops/drive/granular/heap_synth_cone.html) · [`heap_volume_cone`](https://furuse.work/ops/drive/granular/heap_volume_cone.html) · [`heap_volume_heightmap`](https://furuse.work/ops/drive/granular/heap_volume_heightmap.html) · [`hopper_discharge_rate`](https://furuse.work/ops/drive/granular/hopper_discharge_rate.html) · [`powder_flowability_class`](https://furuse.work/ops/drive/granular/powder_flowability_class.html) · [`repose_angle_heightmap`](https://furuse.work/ops/drive/granular/repose_angle_heightmap.html) · [`repose_angle_silhouette`](https://furuse.work/ops/drive/granular/repose_angle_silhouette.html) · [`spheres_render_shaded`](https://furuse.work/ops/drive/granular/spheres_render_shaded.html) · [`spheres_to_heightmap`](https://furuse.work/ops/drive/granular/spheres_to_heightmap.html) · [`spheres_to_silhouette`](https://furuse.work/ops/drive/granular/spheres_to_silhouette.html) · [`spoon_tilt_critical`](https://furuse.work/ops/drive/granular/spoon_tilt_critical.html) · [`spoon_tilt_dispense`](https://furuse.work/ops/drive/granular/spoon_tilt_dispense.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html)

## No.2026.205 —— 食材の切断を画像で測る ―― 刃の追跡・切片の厚み・切断面の粗さ・手首のたわみからの切断力、真値は閉形式と MuJoCo

[![食材の切断を画像で測る ―― 刃の追跡・切片の厚み・切断面の粗さ・手首のたわみからの切断力、真値は閉形式と MuJoCo](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_food_cutting_measure/01_cutting_track_force.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_food_cutting_measure/01_cutting_track_force.gif)

*↑ **食材の切断を画像で測る ―― 刃の追跡・切片の厚み・切断面の粗さ・手首のたわみからの切断力、真値は閉形式と MuJoCo** ―― 物理シミュ × Fullseye 系列。題材はロボットの食材スライスの研究(arXiv:2404.02569、ICRA 2024)。学習はせず規則だけで「画像 → 刃の高さ → 柔らかい手首のたわみ → 力 → 靱性 R」の鎖を閉じる。新モジュール cutting 16 op + mujoco の facade 1。外から来る真値は 3 つ。(1) 閉形式の切断力学: Atkins, Interface Focus 6:20160019 (2016) の式 1.1〜1.4(摩擦なしの押し + 引き、V/(Rw) = 1/(1+ξ²)、H = ξV、F_res/(Rw) = 1/√(1+ξ²))と本文の数(H/Rw は ξ = 1 で最大 0.5、傾けた刃を縦に動かすと ξ = tan i)、Williams & Patel, Interface Focus 6:20150108 (2016) の式 2.6(くさび + Coulomb 摩擦、最小 1/(1 − sin β))と本文の例(μ = 0.2 で θo = 79°・最小 1.24)。摩擦と刃角を含む slice/push の式は未読なので実装せず、組み合わせは ValueError。(2) 物理エンジン = MuJoCo(--full): 正射影カメラで描いた刃を同じ追跡器で追い、食材の抵抗を関節の摩擦損失として毎歩 R·w_eff·g(ξ) に置き換えた手首の拘束力と比べる。柔体は剛性の桁が合うが破断しない(刃は潜り込む)ことも門で固定。(3) 有限要素の刃の力(--full、任意、非商用): arXiv:2105.12244 が公開した CSV(CC BY-NC 4.0)を環境変数から読み、形の比較だけ(データは repo に入れず、図にも載せない)。★厚みの縁は行の 3 色(背景・食材・刃)の線形分解で読む: 背景の割合は端面で 1 → 0、刃の割合は刃の面で 0 → 1 の純粋な段なので、窓の中の和が縁の位置になる。ぼけは割合の和を変えないので、窓を端面の段の 2 次モーメントから広げれば偏らない —— ぼけ 4 px の厚みの偏り −18 µm → +11 µm、8 px は刃の帯がぼけに比べて細すぎるので拒否(試作は −37 µm で黙って通った)。★薄い切片の食材の参照色は刃の向こうの本体から取るので照明の左右勾配で 13 % ずれる: 刃の帯の輝度から照明を推定して戻し 66 → 5 µm。図: 合成の切断の GIF(推定の刃先線・隠れた所は破線・真値・先端・力の曲線)、刃先方向の像と両縁、40 枚の厚みの分布と散布、切断面の断面、壊れる場所、slice/push の閉形式; --full: MuJoCo の GIF、柔体に刃を押した力。門 14 本(numpy、CPU 0.95 s)+ --full 7 本: 閉形式 1e-16、H/Rw の最大 0.5000 @ ξ 1.000、θo 78.69°・最小 1.2440、角度 0.017°、隠れた中央の刃先 8.2 µm、先端 0.24 mm、深さ 29 µm(0.12 px)、厚み 0.1〜5 mm の偏り 6.9 µm・行ごとの RMS 18.5 µm・傾き 0.021°、粗さの床 Rq 11 µm、R 393.6(真値 400、−1.6 %)・ξ 0.561(真値 0.570)、力 1.25 倍の世界で R 500.0(自己申告); --full(8 px/mm・20 px/mm): 角度 0.0014°・刃先 1.1 µm・深さ 2.2 µm・厚みの偏り 2.8 µm・RMS 10.4 µm、雑音 0.05 まで ≤ 5 µm で 0.1 は拒否、MuJoCo 柔体 F/(E·A·δ/H) 1.106 / 1.074 / 1.059、刃は 0.76 N で頭打ち、描画 → 追跡 0.9 µm・0.0007°、手首の力 0.083 N ≤ c·v 0.150 N、FEM 6 本の残差 / 定常値 ≤ 0.068。正直に: 力の真値は外から来ていない —— 合成の力も当てはめも同じ Atkins の模型で作るので、画像 → R の鎖は配管の検査(力 1.25 倍の世界でも R が 1.25 倍に出るだけで靱性と摩擦を分けられない)。食材は変形しない、刃先は直線、片刃を仮定。靱性の実測値は引用しない。画像つきの切断の公開データは見つからなかった。MuJoCo の柔体は保持中も ±5〜11 % 揺れ続ける。踏んだ罠: 画像の中心は ((H−1)/2, (W−1)/2)(H/2 だと 62.5 µm ずれる)、MuJoCo の摩擦損失は既定だと粘性のように柔らかい、入り始めの軌跡で ξ を出すと 0.63(真値 0.57)。*

[![刃先方向の像(20 px/mm、等倍): 片刃の平らな面と食材の端面の距離 = 切片の厚み。破線 = 推定の両縁。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_food_cutting_measure/02_edge_view_thickness_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_food_cutting_measure/02_edge_view_thickness.png)

*↑ 測定の図 ―― 刃先方向の像(20 px/mm、等倍): 片刃の平らな面と食材の端面の距離 = 切片の厚み。破線 = 推定の両縁。*

[![狙い 1.5 mm・ばらつき σ 0.08 mm・傾き σ 0.5° の 40 枚: 真値(破線)と画像(実線)の分布。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_food_cutting_measure/03_thickness_distribution_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_food_cutting_measure/03_thickness_distribution.png)

*↑ 狙い 1.5 mm・ばらつき σ 0.08 mm・傾き σ 0.5° の 40 枚: 真値(破線)と画像(実線)の分布。*

[![40 枚の測った厚み vs 真値(破線 = y = x)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_food_cutting_measure/04_thickness_scatter_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_food_cutting_measure/04_thickness_scatter.png)

*↑ 40 枚の測った厚み vs 真値(破線 = y = x)。*

[![雑音とぼけを強めたときの深さ・厚みの誤差(元の解像度)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_food_cutting_measure/06_where_it_breaks_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_food_cutting_measure/06_where_it_breaks.png)

*↑ 雑音とぼけを強めたときの深さ・厚みの誤差(元の解像度)。*

[![摩擦なしの slice/push の閉形式。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_food_cutting_measure/07_slice_push_closed_form_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_food_cutting_measure/07_slice_push_closed_form.png)

*↑ 摩擦なしの slice/push の閉形式。*

[![MuJoCo の正射影カメラで描いた刃(柔らかい手首 4 N/mm、抵抗 = 摩擦損失 = Atkins の切断力)を同じ追跡器で追う。破線 = 推定の刃先線。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_food_cutting_measure/08_mujoco_wrist_track.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_food_cutting_measure/08_mujoco_wrist_track.gif)

*↑ 動く図 ―― MuJoCo の正射影カメラで描いた刃(柔らかい手首 4 N/mm、抵抗 = 摩擦損失 = Atkins の切断力)を同じ追跡器で追う。破線 = 推定の刃先線。*

```
py -3.11 examples/poc_food_cutting_measure.py
```

ソース: [examples/poc_food_cutting_measure.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_food_cutting_measure.py)

この回が作った図は全部で **9 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_food_cutting_measure)

使用 op(ノートへ): [`cut_depth_from_side`](https://furuse.work/ops/drive/cutting/cut_depth_from_side.html) · [`cut_force_atkins`](https://furuse.work/ops/drive/cutting/cut_force_atkins.html) · [`cut_force_csv_load`](https://furuse.work/ops/drive/cutting/cut_force_csv_load.html) · [`cut_force_fit`](https://furuse.work/ops/drive/cutting/cut_force_fit.html) · [`cut_surface_roughness`](https://furuse.work/ops/drive/cutting/cut_surface_roughness.html) · [`cutting_edge_render`](https://furuse.work/ops/drive/cutting/cutting_edge_render.html) · [`cutting_episode_synth`](https://furuse.work/ops/drive/cutting/cutting_episode_synth.html) · [`cutting_face_render`](https://furuse.work/ops/drive/cutting/cutting_face_render.html) · [`cutting_scene`](https://furuse.work/ops/drive/cutting/cutting_scene.html) · [`cutting_wrist_mjcf`](https://furuse.work/ops/drive/cutting/cutting_wrist_mjcf.html) · [`food_cut_width`](https://furuse.work/ops/drive/cutting/food_cut_width.html) · [`force_from_wrist_displacement`](https://furuse.work/ops/drive/cutting/force_from_wrist_displacement.html) · [`identity`](https://furuse.work/ops/2d/misc/identity.html) · [`knife_edge_track`](https://furuse.work/ops/drive/cutting/knife_edge_track.html) · [`profile_params`](https://furuse.work/ops/roughness/measure/profile_params.html) · [`slice_push_from_track`](https://furuse.work/ops/drive/cutting/slice_push_from_track.html) · [`slice_push_ratio`](https://furuse.work/ops/drive/cutting/slice_push_ratio.html) · [`slice_thickness_profile`](https://furuse.work/ops/drive/cutting/slice_thickness_profile.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`zoom_inset`](https://furuse.work/ops/annotate/compose/zoom_inset.html)

## No.2026.207 —— ドーム状の柔らかい指先を平らな物に押す大変形接触を、スケーリング則と連続体の厳密解で門にする ―― 原文の式 (3) の 1 次の係数は活字どおりだと円柱で力が負、本文の模型から 2n/(1+n) を導いた

[![ドーム状の柔らかい指先を平らな物に押す大変形接触を、スケーリング則と連続体の厳密解で門にする ―― 原文の式 (3) の 1 次の係数は活字どおりだと円柱で力が負、本文の模型から 2n/(1+n) を導いた](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacdome_large_deformation/01_tacdome_press_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacdome_large_deformation/01_tacdome_press_sweep.gif)

*↑ **ドーム状の柔らかい指先を平らな物に押す大変形接触を、スケーリング則と連続体の厳密解で門にする ―― 原文の式 (3) の 1 次の係数は活字どおりだと円柱で力が負、本文の模型から 2n/(1+n) を導いた** ―― 物理シミュ × Fullseye 系列(視触覚)、tacsim(Hertz の膜、小変形)の先。一次情報は T. Mu ほか "A scaling law for large-deformation contact in soft materials"(arXiv:2509.18581、2025)の PDF。ドーム状の柔らかい指先センサ(半球、高さ L = 半径 R = 8 mm、μ = 0.1 MPa は設計の仮定)が平らな物に押される形で成り立たせた。枠組みは断面 f = c rᵖ の線形解 F_L = C δⁿ(n = 1 + 1/p)、大変形 F = κₙ(δ/L) F_L、接触半径の式 (4)(不完全ベータ)、普遍形 κ = (1 − 10/9·δ/L)⁻¹。新モジュール tacdome 12 op、全部 numpy。★式 (3) の 1 次の係数: 原文の頁を 400 dpi の画像にして読んだ活字 (4+2n)/(1+n) では円柱で κ₁(0.5) = −1.667(力が負)。本文の模型(1D 断面の各点に長さ L − g の neo-Hookean 円柱ばね)を積分すると c₁ = 2n/(1+n)・c₂ = n/(2+n)、接触半径は式 (4) と一字一句同じ —— 2 次と式 (4) は活字と一致し、1 次だけが違う。ばねの長さを全部 L にした別の模型は係数 (1.008, 0.258) でどちらの読みにも合わない。付録は arXiv に無く未読。外から来る真値は 3 系統: 非圧縮 neo-Hookean の円柱の一軸圧縮の厳密解(導出した κ₁ と 1.9e-15)、Hertz の小変形極限(被験者 tacsim と 1e-12)、論文の普遍形 k = 10/9(導出した κ₁⁻¹ の最小二乗 1.1060、0.5 % 差)。第 2 実装 = ばね列の中点則(閉形式と 8.5e-9)、式 (4) は 3 経路が 1e-15 で一致。導出した κ⁻¹(0.5) = 0.429 / 0.493 / 0.545(n = 1 / 1.5 / 2)は論文の図 4B の挿入図と同じ並び。被験者の結果 —— 観測量で外れ方が変わる: 半球の指先で押し込みから読む Hertz の力は δ/L = 0.05 / 0.3 / 0.5 で −4.10 / −27.79 / −50.70 %、半径は −1.71 / −11.70 / −22.20 %。ところが接触半径から Hertz で力を読む(視触覚センサの読み方)と κ と半径の伸びがほぼ打ち消して max +5.39 %(d = 0.4)。円錐は打ち消さず d = 0.5 で −18.95 %、平頭は半径が δ を決めないので読めない。内側カメラの接触像(192 px、0.117 mm/px)から面積法(被覆率を切らずに線形和)で半径 max 0.004 %、力の逆算 max 0.013 %、雑音 σ = 0.03 で 0.411 %。縁の画素に measure.fit_circle を当てると −0.61〜−2.51 %。--full: 512 px の 20 点で半径 0.0049 %・力 0.0146 %、MuJoCo の柔体(線形弾性の立方体を摩擦なしで圧縮)は小ひずみの剛性比 0.98〜0.99 で線形極限だけ合い、ε = 0.31 で 0.18 につぶれる = 大変形の真値には使えない(門は小ひずみだけ)。図: 押し込みの GIF(内側カメラの像・ばね列・力の曲線)、3 形状の力、κ⁻¹ の帯と 3 つの読み、a/a_L と円柱の厳密解、Hertz の誤差、接触像の縁の 24 倍; --full: 柔体の剛性比。門 13 本(既定 0.2 s)+ --full 2 本(図込み 41 s)。正直に: 図 5C(半径 vs 力)は再現できない(導出では同じ力の半径の差 0〜1.7 %、付録のセンサ寸法が未読)。「全形状が普遍形の狭い帯に入る」も導出では再現しない(普遍形が球より 10.9 %・円錐より 22.7 % 高い)。円柱の実験値は摩擦込みなので門にしていない。半球は放物線で近似、摩擦なし・準静的・非圧縮、照明は理想化。踏んだ罠: 図の説明文の画素ピッチを m の値のまま mm と書いていた(0.000 mm/px、組み込みの検分で直した)。*

[![球(p = 2、n = 1.5)・円錐(p = 1、n = 2、傾き 1)・平頭の円柱(p = ∞、n = 1、半径 = L)の力(無次元、縦軸は対数)。破線 = 線形解(球は Hertz)、実線 = 大変形 F = κₙ F_L。δ/L ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacdome_large_deformation/02_tacdome_force_three_shapes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacdome_large_deformation/02_tacdome_force_three_shapes.png)

*↑ 測定の図 ―― 球(p = 2、n = 1.5)・円錐(p = 1、n = 2、傾き 1)・平頭の円柱(p = ∞、n = 1、半径 = L)の力(無次元、縦軸は対数)。破線 = 線形解(球は Hertz)、実線 = 大変形 F = κₙ F_L。δ/L = 0.3 を超えると開き、平頭が最も大きく外れる(全ばねが最大ひずみ)。*

[![導出した κₙ⁻¹(実線、n = 1 / 1.5 / 2)は n = 2 が上 = 論文の図 4B の挿入図と同じ並び。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacdome_large_deformation/03_tacdome_kappa_band_readings_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacdome_large_deformation/03_tacdome_kappa_band_readings.png)

*↑ 導出した κₙ⁻¹(実線、n = 1 / 1.5 / 2)は n = 2 が上 = 論文の図 4B の挿入図と同じ並び。*

[![式 (4) の a/a_L(積分の形で計算、不完全ベータの形と 1e-12 で一致)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacdome_large_deformation/04_tacdome_radius_ratio_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacdome_large_deformation/04_tacdome_radius_ratio.png)

*↑ 式 (4) の a/a_L(積分の形で計算、不完全ベータの形と 1e-12 で一致)。*

[![小変形の Hertz を大変形に当てた誤差(寸法・弾性率に依らない)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacdome_large_deformation/05_tacdome_hertz_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacdome_large_deformation/05_tacdome_hertz_error.png)

*↑ 小変形の Hertz を大変形に当てた誤差(寸法・弾性率に依らない)。*

[![左 = d = 0.3 の内側カメラの接触像(192 px、0.117 mm/px、画素を 2 倍、赤 = 面積法で読んだ円、黄 = 右の範囲)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacdome_large_deformation/06_tacdome_contact_edge_crop_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tacdome_large_deformation/06_tacdome_contact_edge_crop.png)

*↑ 左 = d = 0.3 の内側カメラの接触像(192 px、0.117 mm/px、画素を 2 倍、赤 = 面積法で読んだ円、黄 = 右の範囲)。*

```
py -3.11 examples/poc_tacdome_large_deformation.py
```

ソース: [examples/poc_tacdome_large_deformation.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_tacdome_large_deformation.py)

この回が作った図は全部で **7 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_tacdome_large_deformation)

使用 op(ノートへ): [`contact_patch_radius`](https://furuse.work/ops/drive/tacdome/contact_patch_radius.html) · [`dome_contact_image`](https://furuse.work/ops/drive/tacdome/dome_contact_image.html) · [`hertz_force`](https://furuse.work/ops/drive/tacsim/hertz_force.html) · [`hertz_small_strain_error`](https://furuse.work/ops/drive/tacdome/hertz_small_strain_error.html) · [`hertz_sphere`](https://furuse.work/ops/drive/tacsim/hertz_sphere.html) · [`large_deformation_contact`](https://furuse.work/ops/drive/tacdome/large_deformation_contact.html) · [`large_deformation_inverse`](https://furuse.work/ops/drive/tacdome/large_deformation_inverse.html) · [`largedef_correction`](https://furuse.work/ops/drive/tacdome/largedef_correction.html) · [`largedef_radius_ratio`](https://furuse.work/ops/drive/tacdome/largedef_radius_ratio.html) · [`largedef_universal_correction`](https://furuse.work/ops/drive/tacdome/largedef_universal_correction.html) · [`mdr_spring_bed`](https://furuse.work/ops/drive/tacdome/mdr_spring_bed.html) · [`neohookean_cylinder_exact`](https://furuse.work/ops/drive/tacdome/neohookean_cylinder_exact.html) · [`powerlaw_linear_contact`](https://furuse.work/ops/drive/tacdome/powerlaw_linear_contact.html)

## No.2026.209 —— 研削・研磨・拭き取りを画像で測る ―― 削れた深さ・拭けた帯の幅・面積を Preston の式と接触圧の閉形式と MuJoCo で、柔らかい手首は板の高さの誤差 2 mm でも帯がそろい硬い手首は途中で浮いて拭けない

[![研削・研磨・拭き取りを画像で測る ―― 削れた深さ・拭けた帯の幅・面積を Preston の式と接触圧の閉形式と MuJoCo で、柔らかい手首は板の高さの誤差 2 mm でも帯がそろい硬い手首は途中で浮いて拭けない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polish_wipe_measure/02_polish_track_profiles_vs_closed_form_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polish_wipe_measure/02_polish_track_profiles_vs_closed_form.png)

*↑ **研削・研磨・拭き取りを画像で測る ―― 削れた深さ・拭けた帯の幅・面積を Preston の式と接触圧の閉形式と MuJoCo で、柔らかい手首は板の高さの誤差 2 mm でも帯がそろい硬い手首は途中で浮いて拭けない** ―― 物理シミュ × Fullseye 系列の続き。研削の模倣学習(DIPCOM、arXiv:2410.19235)と可変コンプライアンスの拭き(Comp-ACT、arXiv:2406.14990)は接触を保つ剛性を学習で決める。台帳では「視覚が薄い」と保留していたが、仕事の結果(削れた量・拭けた範囲)は画像で測れるので、学習なしで残る部品として成立させた。新モジュール polish 13 op + mujoco の facade 3。外から来るもの: Preston の式 dh/dt = k_p p v(原文 1927 は未読、式の形と k_p の桁 = セリアでガラス 2e-13〜2e-12 m²/N は Shen ほか 2018、J. Am. Ceram. Soc. の式 (1) と本文から)、接触圧(平板 = 一様、球 = Hertz、tacsim の hertz_sphere)、導出した閉形式(直線の一筆の断面、拭けた帯の幅と拭ける最小の力、平行な一筆の面積、弾性床のパッドで粗さが exp(−k_p k_w v t) で減ること)、MuJoCo。(1) 除去の地図の 2 実装(小区間ごとの直接の積分 / 軌跡の線密度と圧力の窓の FFT 畳み込み)が rms 差 0.37 % of peak、体積比 3.6e-4。(2) 一筆の断面 = 閉形式(平板 2k_p p √(a² − y²)、Hertz k_p (E*/R)(a² − y²) で曲率が力に依らない、回る平板の asinh の式)が 0.26 % 以内、体積 / 長さ = k_p F(0.99964 / 1.00002)。(3) 膜の画像(Beer–Lambert、雑音 1 %)から Otsu で読んだ帯の幅 = 閉形式が平板・Hertz 各 4 力で 0.28 % 以内。罠: Otsu のしきい値は残膜 h0 の約 1/3 を意味し、戻さないと最大 36 % 外れる。拭ける最小の力 1.90 N の下で「きれい」な画素 0、平行な 4 本の一筆の面積は 4 つの間隔で 0.30 % 以内(型を画素の中心に置くと縁が 1 列まるごと落ちて −1.7 %、0.3 画素ずらした)。(4) 前後の高さ図(粗さ 20 nm・雑音 1 nm・載せ直し)から削れた深さ 240 nm を rms 1.41 nm で読み、Preston 係数を 0.04 % で当てた(外周の枠を参照にすると 42 % 外れる)。(5) 弾性床: 全面が当たる間 rms は exp に 0.20 % 以内、roughness の Sq 比 0.1351 vs 0.1353。山だけが当たると 19 % 外れる。(6) MuJoCo(--full): 円柱の工具を手首のばね(300 N/m と 10 kN/m)で板に押して動かす。柔らかい手首の力 = ばねの閉形式(99 % 点 0.05 %)、摩擦 = μ、硬い手首は閉形式の 19.8 mm に対し 19.2 mm で浮く。MuJoCo の力で拭いた跡の帯の幅 = 力が変わる一筆の閉形式(中央値 0.55 % / 0.17 %)。帯の幅の変動係数 柔らかい 0.02 %・硬い 13 %、拭けない列 83 / 309 —— 可変コンプライアンスで拭く理由を学習なしで帯の幅の画像から。図: 平行に拭く動く図、一筆の断面と閉形式、帯の幅と力、高さ図と深さの読み、弾性床の粗さの減り、面積と間隔; --full: 一筆の間の力、MuJoCo の力で拭いた跡。門 10 本(既定 1.9 s)+ --full 5 本(図込み 15 s)。正直に: 拭き取りの膜の除去係数は仮の値(帯の幅の門は同じ係数で閉形式と画像が合うかを見るもの)。平板の一様な圧力は剛な平板の仮定(縁で立つ Boussinesq の圧力は入れていない)。弾性床は仮定、高さ図は横にずれない前提。MuJoCo の既定の接触は柔らかすぎて力が 6〜17 % 小さく出たので、接触を硬くし楕円の錐にした。研削の切りくずの模型は扱っていない。*

[![半径 5 mm の平らなパッドで、長さ 30 mm の一筆を間隔 1.2a で 4 本(持ち上げて戻る)。暗い所 = 残った膜(Beer–Lambert)、青い輪 = 工具。最後の画像で拭けた面積 961.8 mm²、閉形式 (2a + (](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polish_wipe_measure/01_polish_raster_wipe_coat.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polish_wipe_measure/01_polish_raster_wipe_coat.gif)

*↑ 測定の図 ―― 半径 5 mm の平らなパッドで、長さ 30 mm の一筆を間隔 1.2a で 4 本(持ち上げて戻る)。暗い所 = 残った膜(Beer–Lambert)、青い輪 = 工具。最後の画像で拭けた面積 961.8 mm²、閉形式 (2a + (N−1)min(s, 2a))L + Nπa² − (N−1)lens(s) = 1087.1 mm²。縁は膜が薄くなるだけで消えきらない所があり(パッドの縁は通過の弦が短い)、Otsu のしきい値がその途中に入る。*

[![膜 1 µm、除去係数は仮の値(平板で拭ける最小の力が 2 N になる値)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polish_wipe_measure/03_polish_band_width_vs_force_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polish_wipe_measure/03_polish_band_width_vs_force.png)

*↑ 膜 1 µm、除去係数は仮の値(平板で拭ける最小の力が 2 N になる値)。*

[![16 × 24 mm、画素 0.1 mm。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polish_wipe_measure/04_polish_height_maps_depth_read_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polish_wipe_measure/04_polish_height_maps_depth_read.png)

*↑ 16 × 24 mm、画素 0.1 mm。*

[![4 本の一筆(長さ 30 mm、パッド半径 5 mm)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polish_wipe_measure/06_polish_raster_area_vs_pitch_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polish_wipe_measure/06_polish_raster_area_vs_pitch.png)

*↑ 4 本の一筆(長さ 30 mm、パッド半径 5 mm)。*

[![板の高さの誤差 2 mm(80 mm で)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polish_wipe_measure/07_polish_mujoco_force_along_stroke_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polish_wipe_measure/07_polish_mujoco_force_along_stroke.png)

*↑ 板の高さの誤差 2 mm(80 mm で)。*

```
py -3.11 examples/poc_polish_wipe_measure.py
```

ソース: [examples/poc_polish_wipe_measure.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_polish_wipe_measure.py)

この回が作った図は全部で **8 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_polish_wipe_measure)

使用 op(ノートへ): [`band_width_profile`](https://furuse.work/ops/drive/polish/band_width_profile.html) · [`coat_image`](https://furuse.work/ops/drive/polish/coat_image.html) · [`coat_thickness_from_image`](https://furuse.work/ops/drive/polish/coat_thickness_from_image.html) · [`polish_scene_mjcf`](https://furuse.work/ops/drive/polish/polish_scene_mjcf.html) · [`preston_coefficient_fit`](https://furuse.work/ops/drive/polish/preston_coefficient_fit.html) · [`preston_pressure_kernel`](https://furuse.work/ops/drive/polish/preston_pressure_kernel.html) · [`preston_removal_map`](https://furuse.work/ops/drive/polish/preston_removal_map.html) · [`preston_track_profile`](https://furuse.work/ops/drive/polish/preston_track_profile.html) · [`raster_wipe_area`](https://furuse.work/ops/drive/polish/raster_wipe_area.html) · [`removal_depth_from_heights`](https://furuse.work/ops/drive/polish/removal_depth_from_heights.html) · [`surface_form_remove`](https://furuse.work/ops/roughness/prepare/surface_form_remove.html) · [`surface_params`](https://furuse.work/ops/roughness/measure/surface_params.html) · [`surface_synth_psd`](https://furuse.work/ops/roughness/synth/surface_synth_psd.html) · [`winkler_polish_run`](https://furuse.work/ops/drive/polish/winkler_polish_run.html) · [`wipe_band_width`](https://furuse.work/ops/drive/polish/wipe_band_width.html) · [`wipe_coverage`](https://furuse.work/ops/drive/polish/wipe_coverage.html)

## No.2026.210 —— 粉体のすくいと注ぎを画像で測る ―― すくった量を側面像の輪郭から、注ぎの流量を PIV の速さ × Boolean 模型の線密度から、MuJoCo の球の個数と横切り数で 5 % 以内

[![粉体のすくいと注ぎを画像で測る ―― すくった量を側面像の輪郭から、注ぎの流量を PIV の速さ × Boolean 模型の線密度から、MuJoCo の球の個数と横切り数で 5 % 以内](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_powder_scoop_pour/01_scoop_spoon_side_views_states_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_powder_scoop_pour/01_scoop_spoon_side_views_states.png)

*↑ **粉体のすくいと注ぎを画像で測る ―― すくった量を側面像の輪郭から、注ぎの流量を PIV の速さ × Boolean 模型の線密度から、MuJoCo の球の個数と横切り数で 5 % 以内** ―― 物理シミュ × Fullseye 系列、granular(山の安息角・体積・Beverloo 排出)の続き。先行研究の粉体計量(Kadokawa, Hamaya, Tanaka, IROS 2023)は秤の質量だけを観測に使う。こちらは横から見た像で、スプーンにすくった量と、傾けて注いだときの流量を読む。新モジュール scoop 15 op + mujoco の facade 2。(1) すくった量: 球冠の椀(縁の半径 a、深さ h)のすり切り V = πh(3a² + h²)/6(体素 300³ と 1.4e-5)、山盛りは縁の上の安息角の円錐(granular の heap_volume_cone と一致)。側面像の体積は Pappus の形 π Σ|x − x_axis| c で読む: 被覆率に線形なので、平らな粉面が行の途中を横切っても偏らない(罠: 行の幅を直径にした円板の和は f² で数え落として −1.5 %)。金属の椀は縁より下が見えないので、すり切りの閉形式 + 縁の上の回転体; 縁の上が空だと「すり切りか足りないかは横から分からない」で ValueError。縦長の盛り(楕円錐 1.6 : 1)は直交 2 方向の楕円の和で体素の真値に −0.01 %、片方だけの回転体は −37.5 % / +60.0 %。(2) 粒の数(MuJoCo、--full): 椀を薄板 118 枚で張り、剛体球(半径 2 mm)を椀の中から積んで放す(上から落とすと跳ねて 500 個中 172 個しか残らなかった)。2 方向の像の体積 × 充填率(1 回で較正、ν = 0.539 —— 輪郭は粒の外側の包絡なので充填そのものより小さい)で、他の 5 本の個数を +3.2 / +0.1 / −0.5 / −3.8 / −4.3 %。金属の椀として読むと山の裾が縁に届いた 600 個で +1.0 %、山になりかけの 330 個は +9.3 % → rim_full=False の旗。半径 3.5 mm(縁の半径 / 粒径 4.3)は同じ較正で −9.5 % → 規則 scoop_image_limit は a/d < 5 を秤に回す。(3) 注ぎの流量: 速さは PIV(pivops.piv_cross_correlate の全コマ対の中央値)、線密度は時間平均の被覆率を Boolean 模型 c = 1 − exp(−nπr²) で逆に解いて横に積分、流量 = λ v。合成の流れで速さ 0.82 %、流量は実現した横切り数の 0.98〜1.03 倍、素朴な c/(πr²) は 0.60〜0.73 倍。MuJoCo で口の開いた樋(665 球)を 15 度/s で傾けると、像の流量は線を横切った球の数の0.98〜1.04 倍(傾き 6〜26 度の 5 区間、160〜482 個/s; 素朴な数え方は 0.88〜0.95)、速さは自由落下 √(v₀² + 2gs) と 1.6 % 以内、時間積分した注いだ量は器から出た数の −5.8 %。流量は口の流れの層を等価直径にした Beverloo の 0.42 倍(桁だけ)。(4) 傾き角への依存(自分の導出): 口に壁の無い器は前面が初めから安息角の斜面なので、保持断面は A(θ) = ∫₀ᴸ min(h₀, x tan(φ − θ)) dx で θ = 0⁺ からこぼれ始める。MuJoCo の出た割合に φ と深さを当てはめると口の楔が RMS 0.023、口に縁のある器(granular の lip="wall"、初めは口まで平らに満ちる)0.050、2 % 出た角 1.3 度 < 縁のある器の θ_c 5.4 度。この導出を根拠に granular の楔の傾きを小角の近似 tan φ − tan θ(RMS 0.038)から厳密な tan(φ − θ) に直し、口の楔の式は granular の 1 か所にまとめた(縁のある器は厳密にすると合いが悪くなる —— 近似の誤差が口に縁が無いことの誤差を偶然打ち消していた)。器に残る量を像の断面積(− 粒半径 × 自由表面の長さ)で読むと数より最大 0.09 遅れる。図: すくいの側面像、楕円の盛りの 2 方向、合成の流れの GIF、速さと自由落下、Boolean 模型と素朴な数え方、傾けの 2 模型、像か秤か; --full: MuJoCo の椀、注ぎの GIF、出た割合、流量の像と数、参照との表。門 15 本(既定 0.7 s)+ --full 10 本(図込み 71 s)。正直に: 側面像の体積は軸対称か断面が楕円を仮定。体積 → 粒の数は充填率を 1 回較正(量が多いほど ν が上がる系統 ±4 %)。Boolean 模型は粒の位置が独立な流れの式で、口の近くの密な流れでは外れる。傾けて出る量の比較は φ と深さを当てはめたもの(独立でない)、奥の平らな層が実際には流れて薄くなる挙動はどちらの模型にも無い(一次情報は未読)。MuJoCo は剛体の軟接触・付着なし・単分散の球で、μm 級の粉には当てはまらない。*

[![縦長の盛り(楕円錐 1.6 : 1)を直交する 2 方向から見た像(等倍)。2 方向の楕円の和は体素の真値に -0.01 %、片方だけの回転体は -37 % / +60 % 外れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_powder_scoop_pour/02_scoop_elliptic_heap_two_views_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_powder_scoop_pour/02_scoop_elliptic_heap_two_views.png)

*↑ 測定の図 ―― 縦長の盛り(楕円錐 1.6 : 1)を直交する 2 方向から見た像(等倍)。2 方向の楕円の和は体素の真値に -0.01 %、片方だけの回転体は -37 % / +60 % 外れる。*

[![PIV(全コマ対の中央値)の速さと自由落下の閉形式。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_powder_scoop_pour/04_scoop_stream_speed_vs_freefall_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_powder_scoop_pour/04_scoop_stream_speed_vs_freefall.png)

*↑ PIV(全コマ対の中央値)の速さと自由落下の閉形式。*

[![口に壁の無い器(前面が初めから安息角の斜面)は θ = 0⁺ からこぼれ、口に縁のある器(granular の lip="wall"、初めは口まで平らに満ちている)は θ_c まで 1 粒も出ない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_powder_scoop_pour/06_scoop_tilt_models_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_powder_scoop_pour/06_scoop_tilt_models.png)

*↑ 口に壁の無い器(前面が初めから安息角の斜面)は θ = 0⁺ からこぼれ、口に縁のある器(granular の lip="wall"、初めは口まで平らに満ちている)は θ_c まで 1 粒も出ない。*

[![球冠の椀(青 = 内面の閉形式、縁 30 mm、深さ 12 mm、薄板 118 枚)にすくった剛体球(半径 2 mm)150 / 330 / 600 個(陰影つき正射影、0.25 mm/px、等倍)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_powder_scoop_pour/08_scoop_mujoco_fills_render_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_powder_scoop_pour/08_scoop_mujoco_fills_render.png)

*↑ 球冠の椀(青 = 内面の閉形式、縁 30 mm、深さ 12 mm、薄板 118 枚)にすくった剛体球(半径 2 mm)150 / 330 / 600 個(陰影つき正射影、0.25 mm/px、等倍)。*

[![流れの像から読んだ流量(3 高さの平均)と MuJoCo で線を横切った数。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_powder_scoop_pour/11_scoop_mujoco_flux_image_vs_count_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_powder_scoop_pour/11_scoop_mujoco_flux_image_vs_count.png)

*↑ 流れの像から読んだ流量(3 高さの平均)と MuJoCo で線を横切った数。*

[![合成の流れ(3000 個/s、半径 1 mm、幅 8 mm、0.5 mm/px を 2 倍の最近傍、1.5 ms/コマ)。破線 = 流量を読む 3 つの帯。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_powder_scoop_pour/03_scoop_stream_synthetic_frames.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_powder_scoop_pour/03_scoop_stream_synthetic_frames.gif)

*↑ 動く図 ―― 合成の流れ(3000 個/s、半径 1 mm、幅 8 mm、0.5 mm/px を 2 倍の最近傍、1.5 ms/コマ)。破線 = 流量を読む 3 つの帯。*

[![口の開いた樋(青 = 床と奥壁、床 80 mm、幅 24 mm、滑らかな側壁)を口の縁を軸に 15 度/s で傾ける(剛体球 665 個、0.5 mm/px、陰影つき正射影)。数は傾け始めに器にあった球のうち口を越えた数。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_powder_scoop_pour/09_scoop_mujoco_pour_render.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_powder_scoop_pour/09_scoop_mujoco_pour_render.gif)

*↑ 動く図 ―― 口の開いた樋(青 = 床と奥壁、床 80 mm、幅 24 mm、滑らかな側壁)を口の縁を軸に 15 度/s で傾ける(剛体球 665 個、0.5 mm/px、陰影つき正射影)。数は傾け始めに器にあった球のうち口を越えた数。*

```
py -3.11 examples/poc_powder_scoop_pour.py
```

ソース: [examples/poc_powder_scoop_pour.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_powder_scoop_pour.py)

この回が作った図は全部で **12 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_powder_scoop_pour)

使用 op(ノートへ): [`beverloo_rate`](https://furuse.work/ops/drive/granular/beverloo_rate.html) · [`difference`](https://furuse.work/ops/2d/nary/difference.html) · [`heap_volume_cone`](https://furuse.work/ops/drive/granular/heap_volume_cone.html) · [`pour_scene_mjcf`](https://furuse.work/ops/drive/scoop/pour_scene_mjcf.html) · [`revolution_volume_side`](https://furuse.work/ops/drive/scoop/revolution_volume_side.html) · [`scoop_count`](https://furuse.work/ops/drive/scoop/scoop_count.html) · [`scoop_image_limit`](https://furuse.work/ops/drive/scoop/scoop_image_limit.html) · [`scoop_scene_mjcf`](https://furuse.work/ops/drive/scoop/scoop_scene_mjcf.html) · [`scoop_synth_side`](https://furuse.work/ops/drive/scoop/scoop_synth_side.html) · [`scoop_volume_read`](https://furuse.work/ops/drive/scoop/scoop_volume_read.html) · [`spheres_render_shaded`](https://furuse.work/ops/drive/granular/spheres_render_shaded.html) · [`spheres_to_silhouette`](https://furuse.work/ops/drive/granular/spheres_to_silhouette.html) · [`spoon_bowl_volume`](https://furuse.work/ops/drive/scoop/spoon_bowl_volume.html) · [`stream_flux_read`](https://furuse.work/ops/drive/scoop/stream_flux_read.html) · [`stream_synth`](https://furuse.work/ops/drive/scoop/stream_synth.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`tilt_pour_rate`](https://furuse.work/ops/drive/scoop/tilt_pour_rate.html) · [`tilt_wedge_retained`](https://furuse.work/ops/drive/scoop/tilt_wedge_retained.html) · [`tilted_surface_read`](https://furuse.work/ops/drive/scoop/tilted_surface_read.html) · [`two_view_volume`](https://furuse.work/ops/drive/scoop/two_view_volume.html)

## No.2026.211 —— 乳鉢の粉砕を測る ―― 粒度分布の D50、粉砕則、独立 3 回のばらつき、AE の帯域電力。真値は公開されたレーザー回折の実測、D50 の定義の違いが 1 区間 = 12 % の偏り

[![乳鉢の粉砕を測る ―― 粒度分布の D50、粉砕則、独立 3 回のばらつき、AE の帯域電力。真値は公開されたレーザー回折の実測、D50 の定義の違いが 1 区間 = 12 % の偏り](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_powder_grinding_ae/01_synthetic_particles_labels_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_powder_grinding_ae/01_synthetic_particles_labels.png)

*↑ **乳鉢の粉砕を測る ―― 粒度分布の D50、粉砕則、独立 3 回のばらつき、AE の帯域電力。真値は公開されたレーザー回折の実測、D50 の定義の違いが 1 区間 = 12 % の偏り** ―― 物理シミュ × Fullseye 系列、粉体の 3 本目(granular / scoop の続き)。題材はロボットが乳鉢で粉を挽き、音響放射(AE)で挽き具合を見張る研究。その公開データ(Zenodo 概念 DOI 10.5281/zenodo.18064323、CC BY 4.0)のレーザー回折の粒度分布(NaCl / クエン酸 / グルタミン酸ナトリウム × 独立 3 回 × 粉砕 3〜25 min の 7 時点、+ 粉砕前・60 min・手作業)と AE の生波形 6 本を外の真値にした。データは repo に入れない(粒度分布 117 本と AE 6 本だけを抜き、環境変数 FULLSEYE_GRIND_DATA で渡す。無い CI では numpy の 12 門だけ走る)。新モジュール grind 13 op、facade なし。(1) D50 の定義: 装置の CSV の区間の端と体積の行の対応を読み、ヘッダの Dx(50) は「端の累積を log(径) で線形補間」と全 117 本で一致(最大差 3.2e-15)。公開の解析コードのある段は累積を区間の下の端に置くので 1 区間分(比 1.136)小さい: −11.80〜−11.98 %。(2) 粉砕則(Reddy の式 (1)・(5)〜(7)、dE = −C dx/xⁿ、Kick n = 1・Bond 1.5・Rittinger 2)を正味の粉砕時間に当てはめると(log D50 の rms、21 点)NaCl は Rittinger 0.050、クエン酸は Bond 0.100、MSG は Bond 0.156。Kick はどの材料でも最良にならない。ところが、その材料の時点・縮み・残差で 3 則を作り直したモンテカルロで正しい則が勝つ割合はクエン酸 92〜100 %(縮み 20 倍)、MSG 70〜92 %、NaCl 58〜78 %(縮み 2.7 倍)—— NaCl の「Rittinger が最良」は当てにならない。粉砕前への外挿(当てはめに使っていない測定)は最良の則で −6 / −18 / −11 %、n を自由にすると +34 / +57 % と悪化(当てはめ過ぎ)。(3) 独立 3 回のばらつき(D50 の cv、7 時点の二乗平均)は NaCl 5.2 %・クエン酸 6.5 %・MSG 13.2 %。同じ粉の繰り返し測定の cv は 0.8〜17.1 % で、独立試行より小さいとは限らない。25 min の D50 は全ての組で標準誤差の 12 倍以上離れる。(4) 篩上 R(200 µm) の見かけの一次の速度(Deniz 2004 の式、出典 Austin)は 0.17〜0.20 /min、前半より後半が遅い(一次から外れる)。(5) AE の帯域電力(0.1〜1 MHz)は公開の解析コードの定義を同じ 6 本で走らせた値と差 0.0、acoustics.stft の密度の帯域積分とは Parseval で 0.982〜1.052。3 min → 25 min で NaCl 185 → 31 mV²、クエン酸 806 → 7.1、MSG 2209 → 184、どれも D50 と同じ向き。(6) 60 min のクエン酸は 25 min の 11.4 µm より粗い 39.9 µm(凝集)で、単調に細かくなる則はどれも表せない。図: 合成の粒子と体積基準 vs 個数基準、則の見分け(合成)、3 材料の D50 の曲線と 3 則、粒度分布が細かくなる GIF、AE のスペクトログラム(挽き始めと挽き終わりを同じ色の尺度で)、AE の帯域電力 vs D50、コマごとの帯域電力、篩上の一次の速度、60 min で則が破れる表、実データの設計での見分けの表。門 12 本(numpy、0.6 s)+ データ 10 本、--full はモンテカルロ 10 倍(図込み 25 s)。正直に: エネルギー ∝ 正味の時間は仮定(則どうしの比較にしか使っていない)。AE は材料ごとに 2 点なので単調性も指数も 2 点の比で、相関の強さは言えない。論文本文は未読、Bond 1952 と Austin の原著も未読。60 min と粉砕前の測定は装置の設定が違う。画像からの D50 は合成の門だけ。*

[![同じ画像の同じ粒子でも、体積基準の D50 は個数基準の 1.39 倍。レーザー回折は体積基準。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_powder_grinding_ae/02_image_volume_vs_number_basis_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_powder_grinding_ae/02_image_volume_vs_number_basis.png)

*↑ 測定の図 ―― 同じ画像の同じ粒子でも、体積基準の D50 は個数基準の 1.39 倍。レーザー回折は体積基準。*

[![縮みが小さいと、雑音 5 % でも 3 則の区別がつかない(200 回ずつ)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_powder_grinding_ae/03_law_identifiability_synthetic_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_powder_grinding_ae/03_law_identifiability_synthetic.png)

*↑ 縮みが小さいと、雑音 5 % でも 3 則の区別がつかない(200 回ずつ)。*

[![citric acid の D50(独立 3 回)と 3 則の当てはめ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_powder_grinding_ae/05_d50_vs_time_Citricacid_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_powder_grinding_ae/05_d50_vs_time_Citricacid.png)

*↑ citric acid の D50(独立 3 回)と 3 則の当てはめ。*

[![各材料 2 点しか取っていない(データ量の上限)ので、傾き α は 2 点の比。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_powder_grinding_ae/09_ae_power_vs_d50_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_powder_grinding_ae/09_ae_power_vs_d50.png)

*↑ 各材料 2 点しか取っていない(データ量の上限)ので、傾き α は 2 点の比。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_powder_grinding_ae/11_first_order_oversize_200um_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_powder_grinding_ae/11_first_order_oversize_200um.png)

*↑ この回の図*

[![1st の試行の累積粒度分布が、粉砕前 → 3 → 25 min で左(細かい側)へ動く。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_powder_grinding_ae/07_psd_fining_during_grinding.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_powder_grinding_ae/07_psd_fining_during_grinding.gif)

*↑ 動く図 ―― 1st の試行の累積粒度分布が、粉砕前 → 3 → 25 min で左(細かい側)へ動く。*

```
py -3.11 examples/poc_powder_grinding_ae.py
```

ソース: [examples/poc_powder_grinding_ae.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_powder_grinding_ae.py)

この回が作った図は全部で **13 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_powder_grinding_ae)

使用 op(ノートへ): [`ae_band_power`](https://furuse.work/ops/drive/grind/ae_band_power.html) · [`ae_read_csv`](https://furuse.work/ops/drive/grind/ae_read_csv.html) · [`ae_size_correspondence`](https://furuse.work/ops/drive/grind/ae_size_correspondence.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`breakage_first_order_fit`](https://furuse.work/ops/drive/grind/breakage_first_order_fit.html) · [`comminution_energy`](https://furuse.work/ops/drive/grind/comminution_energy.html) · [`comminution_law_fit`](https://furuse.work/ops/drive/grind/comminution_law_fit.html) · [`particle_image_d50`](https://furuse.work/ops/drive/grind/particle_image_d50.html) · [`particle_image_synth`](https://furuse.work/ops/drive/grind/particle_image_synth.html) · [`particle_size_dx`](https://furuse.work/ops/drive/grind/particle_size_dx.html) · [`particle_size_oversize`](https://furuse.work/ops/drive/grind/particle_size_oversize.html) · [`particle_size_read`](https://furuse.work/ops/drive/grind/particle_size_read.html) · [`particle_size_synth`](https://furuse.work/ops/drive/grind/particle_size_synth.html) · [`replicate_compare`](https://furuse.work/ops/drive/grind/replicate_compare.html)

## No.2026.214 —— 粉末 X 線回折の 2-D 検出器像から相を 1 つずつ剥がす ―― 較正・方位積分・NNLS・残差の未知相。真値は NIST SRM 640g の証明書と COD の CIF、合成と解析が模型を共有する分は食い違わせて測る

[![粉末 X 線回折の 2-D 検出器像から相を 1 つずつ剥がす ―― 較正・方位積分・NNLS・残差の未知相。真値は NIST SRM 640g の証明書と COD の CIF、合成と解析が模型を共有する分は食い違わせて測る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pxrd_phase_peel/01_phase_peel.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pxrd_phase_peel/01_phase_peel.gif)

*↑ **粉末 X 線回折の 2-D 検出器像から相を 1 つずつ剥がす ―― 較正・方位積分・NNLS・残差の未知相。真値は NIST SRM 640g の証明書と COD の CIF、合成と解析が模型を共有する分は食い違わせて測る** ―― 混合物の粉末に X 線を当てると、検出器には相ごとのデバイ環が重なって写る。新モジュール pxrd(14 op)は学習なしに、標準 Si の環で検出器の中心・距離・傾きを較正し(傾き 3° で中心 0.011 px、距離 0.0009 %、傾き 3.004°・向き −40.01°、rms 0.019°)、方位積分で 2θ のプロファイルに落とし、山の幅から Scherrer で結晶子径を出し(354 Å、真 350 Å)、CIF から作った参照の辞書で相を 1 つずつ剥がし(NNLS の前進選択、NaCl > CaF₂ > コランダムの順、rwp 0.546 → 0.179)、残差に残った 8 本の山を立方晶 F・a = 4.2170 Å(真 4.2170)と指数付けして、候補 4 つ(MgO・NiO・CaO・KCl)から MgO を名指しする。4 相(35 / 30 / 20 / 15 wt%)の分率の誤差は 0.04 wt%。外の真値は NIST SRM 640g の証明書: a = 0.543 110 9 nm と Cu Kα1 から、表の線 11 本を Bragg + 消滅則で最大 0.00044° に再現し、140° までに他の線は 1 本も出ない。相は COD の CIF(CC0、repo の外)。罠: 傾き 5° を無視して積分すると環が楕円になり、山 10 本が 23 本に割れる。試料の格子が参照より 0.4 % 大きいだけで分率が崩れ、格子の追い込みで戻る。正直に: 合成と解析は同じ物理模型を共有するので、0.04 wt% は「幾何・画素・雑音・重なりを通り抜けても模型の量が戻る」確認にとどまる。模型をわざと食い違わせて漏れを測った: 山の形の取り違え 0.33 wt%、イオンと中性原子 0.06 wt%、結晶子径 −29 % で 0.97 wt%。微視的吸収・選択配向・異常分散は模型に無く、強度の外部真値(実測の相対強度)もまだ無い。*

[![the detector image coloured by phase (1:1 pixels, lossless PNG)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pxrd_phase_peel/02_detector_by_phase_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pxrd_phase_peel/02_detector_by_phase.png)

*↑ 測定の図 ―― the detector image coloured by phase (1:1 pixels, lossless PNG)*

[![the observed detector image (background removed, gamma 0.5)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pxrd_phase_peel/03_detector_observed_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pxrd_phase_peel/03_detector_observed.png)

*↑ the observed detector image (background removed, gamma 0.5)*

[![integrated profile, NNLS fit and each phase's contribution](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pxrd_phase_peel/04_profile_fit_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pxrd_phase_peel/04_profile_fit.png)

*↑ integrated profile, NNLS fit and each phase's contribution*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pxrd_phase_peel/06_trap_lattice_mismatch_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pxrd_phase_peel/06_trap_lattice_mismatch.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pxrd_phase_peel/08_calibration_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pxrd_phase_peel/08_calibration.png)

*↑ この回の図*

```
py -3.11 examples/poc_pxrd_phase_peel.py
```

ソース: [examples/poc_pxrd_phase_peel.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pxrd_phase_peel.py)

この回が作った図は全部で **9 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_pxrd_phase_peel)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`azimuthal_integrate`](https://furuse.work/ops/drive/pxrd/azimuthal_integrate.html) · [`cif_read`](https://furuse.work/ops/drive/pxrd/cif_read.html) · [`cubic_index`](https://furuse.work/ops/drive/pxrd/cubic_index.html) · [`cubic_prototype`](https://furuse.work/ops/drive/pxrd/cubic_prototype.html) · [`debye_ring_image`](https://furuse.work/ops/drive/pxrd/debye_ring_image.html) · [`detector_calibrate`](https://furuse.work/ops/drive/pxrd/detector_calibrate.html) · [`detector_two_theta`](https://furuse.work/ops/drive/pxrd/detector_two_theta.html) · [`difference`](https://furuse.work/ops/2d/nary/difference.html) · [`diffraction_peaks`](https://furuse.work/ops/drive/pxrd/diffraction_peaks.html) · [`grid_lines`](https://furuse.work/ops/annotate/plot/grid_lines.html) · [`intensity`](https://furuse.work/ops/2d/features/intensity.html) · [`legend_box`](https://furuse.work/ops/annotate/furniture/legend_box.html) · [`nice_ticks`](https://furuse.work/ops/annotate/plot/nice_ticks.html) · [`phase_dictionary`](https://furuse.work/ops/drive/pxrd/phase_dictionary.html) · [`phase_fractions`](https://furuse.work/ops/drive/pxrd/phase_fractions.html) · [`phase_peel`](https://furuse.work/ops/drive/pxrd/phase_peel.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`powder_reflections`](https://furuse.work/ops/drive/pxrd/powder_reflections.html) · [`scherrer_size`](https://furuse.work/ops/drive/pxrd/scherrer_size.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html) · [`unexplained_peaks`](https://furuse.work/ops/drive/pxrd/unexplained_peaks.html)

## No.2026.215 —— 何分すり潰せば 1 回分の薬の量が揃うか ―― 粒径から含量のばらつきを閉形式と Monte Carlo で、粉砕則で必要な時間を逆算。写真の CV が低く出た正体は同じ 12 枚の縮尺違い

[![何分すり潰せば 1 回分の薬の量が揃うか ―― 粒径から含量のばらつきを閉形式と Monte Carlo で、粉砕則で必要な時間を逆算。写真の CV が低く出た正体は同じ 12 枚の縮尺違い](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dose_uniformity_from_grinding/01_cv_bias_decomposition_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dose_uniformity_from_grinding/01_cv_bias_decomposition.png)

*↑ **何分すり潰せば 1 回分の薬の量が揃うか ―― 粒径から含量のばらつきを閉形式と Monte Carlo で、粉砕則で必要な時間を逆算。写真の CV が低く出た正体は同じ 12 枚の縮尺違い** ―― grind(乳鉢の粉砕を測る)の続き。よく混ざった粉から 1 回分を取ると、薬の粒の数が Poisson で揺らぐだけで含量がばらつく。複合 Poisson から CV² = (πρ/6)·D63³/D を導出し(D63 = 個数基準の 6 次 / 3 次モーメントの比の 3 乗根)、体積基準の粒度分布からは恒等式 D63³ = E_v[d³] で形を仮定せずに出す。粉砕則を D63 に当てて、CV が目標(受入値 15 相当の 6.25 %、または第 1 段の合格の確率)まで下がる時間を逆算する。閉形式 vs Monte Carlo(径を引いて足すだけ)は 8 条件で差 / 標準誤差 最大 1.72、恒等式は 1e-16。★試走の「写真から出した CV が 4 つの径で一貫して −6 %」は、4 つの径が画素の単位で同じ 12 枚の画像だったための見かけ(門 4)。独立な束に分けると主因は縁に触れる粒の取りこぼし(0.956)、Miles–Lantuéjoul の重み + 対数正規で 1.001・散らばりは ±0.102 → ±0.060。「AV ≤ 15 相当」の CV 6.25 % の粉は第 1 段を約半分しか通らない(χ² 0.563、平均のずれの項込みで 0.501)。実データ(公開のレーザー回折、repo の外・FULLSEYE_GRIND_DATA)では D16/D50/D84 の対数正規が CV を中央値 1,336 倍に見積もる(二峰)ので使えず、5 mg で CV 6.25 % に要る時間は NaCl 24 min・クエン酸 28 min・MSG 31 min(後 2 つは外挿)、0.1 mg は 96〜206 min。正直に: CV は粒の数の揺らぎだけの下限、受入値の数は二次資料、粉砕則を D63 に当てるのは仮定。門 13 本(データ無しの CI は 11 本、2.3 s)、既定は Monte Carlo 1,000 回・画像 30 束、--full は 8,000 回・200 束。*

[![レーザー回折の粒度分布から形を仮定せずに出した CV(粒の数の揺らぎだけ = 下限)。3 則の必要時間 24〜24 min。目標が測った範囲の近くなので則はほぼ同じ答えを返す。0.1 mg(100〜206 min)のような遠い外挿では則で大](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dose_uniformity_from_grinding/02_cv_vs_grinding_NaCl_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dose_uniformity_from_grinding/02_cv_vs_grinding_NaCl.png)

*↑ 測定の図 ―― レーザー回折の粒度分布から形を仮定せずに出した CV(粒の数の揺らぎだけ = 下限)。3 則の必要時間 24〜24 min。目標が測った範囲の近くなので則はほぼ同じ答えを返す。0.1 mg(100〜206 min)のような遠い外挿では則で大きく開く。*

[![レーザー回折の粒度分布から形を仮定せずに出した CV(粒の数の揺らぎだけ = 下限)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dose_uniformity_from_grinding/03_cv_vs_grinding_Citricacid_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dose_uniformity_from_grinding/03_cv_vs_grinding_Citricacid.png)

*↑ レーザー回折の粒度分布から形を仮定せずに出した CV(粒の数の揺らぎだけ = 下限)。*

[![レーザー回折の粒度分布から形を仮定せずに出した CV(粒の数の揺らぎだけ = 下限)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dose_uniformity_from_grinding/04_cv_vs_grinding_MSG_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dose_uniformity_from_grinding/04_cv_vs_grinding_MSG.png)

*↑ レーザー回折の粒度分布から形を仮定せずに出した CV(粒の数の揺らぎだけ = 下限)。*

[![同じ粉を挽く時間だけ変えて 5 mg を 10 個取った含量(粒の数の揺らぎだけ、正規近似の 1 回の模擬)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dose_uniformity_from_grinding/05_ten_units_NaCl_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dose_uniformity_from_grinding/05_ten_units_NaCl.png)

*↑ 同じ粉を挽く時間だけ変えて 5 mg を 10 個取った含量(粒の数の揺らぎだけ、正規近似の 1 回の模擬)。*

[![最良の則で、CV 6.25 % に要る粉砕時間 [min)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dose_uniformity_from_grinding/06_grinding_time_by_dose_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dose_uniformity_from_grinding/06_grinding_time_by_dose.png)

*↑ 最良の則で、CV 6.25 % に要る粉砕時間 [min]。*

```
py -3.11 examples/poc_dose_uniformity_from_grinding.py
```

ソース: [examples/poc_dose_uniformity_from_grinding.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dose_uniformity_from_grinding.py)

この回が作った図は全部で **7 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_dose_uniformity_from_grinding)

使用 op(ノートへ): [`comminution_energy`](https://furuse.work/ops/drive/grind/comminution_energy.html) · [`dose_cv_from_sizes`](https://furuse.work/ops/drive/doseunif/dose_cv_from_sizes.html) · [`dose_cv_lognormal`](https://furuse.work/ops/drive/doseunif/dose_cv_lognormal.html) · [`grind_time_for_dose_cv`](https://furuse.work/ops/drive/doseunif/grind_time_for_dose_cv.html) · [`particle_image_d50`](https://furuse.work/ops/drive/grind/particle_image_d50.html) · [`particle_image_synth`](https://furuse.work/ops/drive/grind/particle_image_synth.html) · [`particle_size_read`](https://furuse.work/ops/drive/grind/particle_size_read.html) · [`particle_size_synth`](https://furuse.work/ops/drive/grind/particle_size_synth.html)

## No.2026.216 —— 包丁を指先の視触覚だけで持って切る ―― 手首の力センサなしに靱性と刃の当たり位置、持てる柄の長さの限界。既存の読み手のねじりの過大(比 0.5 で +33 %)を部分滑りの数値解で直す

[![包丁を指先の視触覚だけで持って切る ―― 手首の力センサなしに靱性と刃の当たり位置、持てる柄の長さの限界。既存の読み手のねじりの過大(比 0.5 で +33 %)を部分滑りの数値解で直す](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_knife_tactile_toughness/04_pad_images_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_knife_tactile_toughness/04_pad_images.png)

*↑ **包丁を指先の視触覚だけで持って切る ―― 手首の力センサなしに靱性と刃の当たり位置、持てる柄の長さの限界。既存の読み手のねじりの過大(比 0.5 で +33 %)を部分滑りの数値解で直す** ―― cutting(食材の切断を画像で測る)× pegtactile(2 本指の膜で接触レンチ)の連鎖。包丁の背を 2 枚のパッドで挟み、膜の像だけから押し V・引き H・モーメント M_x を復元し、刃の当たり位置 Ly = (M_x + Lz·H)/V、slice/push 比 ξ̂ = H/V、靱性 R を読む。★見つけて直したこと: pegtactile.pad_tactile_read はパッドのねじりを無滑り(Reissner–Sagoci)で読むが、Hertz 接触のねじりは縁から必ず滑るので M を過大に読む —— 部分滑りの像で比 0.5 で ×1.328、0.85 で ×2.022(数値解の予測と 0.4 % 以内)。接触円を 64 環に分け Cerruti 核の影響行列で部分滑りを解き(両端は閉形式: c → a で β/β_RS 0.9986、c → 0 で全滑りのトルク +0.11 %)、補正後 0.2 % 以内。MuJoCo の切断(既定の門は 4 コマ、図は 14 コマ)→ パッドの像だけで R̂ 59.86 J/m²(設定 60)、ξ̂ 0.0701(tan θ 0.0699)、当たり位置の誤差 中央値 0.01 mm・最大 0.48 mm(無滑りの読みのままだと 6.09 mm)。持てる柄の長さの限界: 把持力 4 N では刃の当たりが把持点から 6.0 mm を超えると読めない(8 N で 13.2 mm、16 N で 31.3 mm)、範囲の外は readable = False の印。正直に: 膜の合成と補正は同じ数値解(本物のゲルが半空間の部分滑りどおりかは未確認)、せん断とねじりは重ね合わせ、V は MuJoCo の摩擦損失に書いた式そのもの、H は H = ξV で作った。門 13 本(3.0 s、mujoco が無ければ閉形式の切断で代える)、--full は全 79 コマ・96 環・17 点。*

[![押し 2 N の切断で、刃の当たり位置が指から離れるほどパッドのねじりが増え、固着円が縮む。把持力 4 N では -3.5〜6.0 mm の外で読めなくなり、-4.5〜7.0 mm の外で全滑り。把持力を 4 倍にすると範囲は約 6.3 倍](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_knife_tactile_toughness/01_handle_length_limit_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_knife_tactile_toughness/01_handle_length_limit.png)

*↑ 測定の図 ―― 押し 2 N の切断で、刃の当たり位置が指から離れるほどパッドのねじりが増え、固着円が縮む。把持力 4 N では -3.5〜6.0 mm の外で読めなくなり、-4.5〜7.0 mm の外で全滑り。把持力を 4 倍にすると範囲は約 6.3 倍(全滑りのトルク ∝ P a ∝ P^{4/3})。*

[![無滑りの関係でねじりを読むと、指から離れるほど当たり位置を遠くに読む(部分滑りでねじれ角が大きい)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_knife_tactile_toughness/02_contact_position_read_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_knife_tactile_toughness/02_contact_position_read.png)

*↑ 無滑りの関係でねじりを読むと、指から離れるほど当たり位置を遠くに読む(部分滑りでねじれ角が大きい)。*

[![刃が食材の左端から切れ始め、切っている幅の中点(当たり位置)が右へ動く。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_knife_tactile_toughness/03_mujoco_cut_timeline_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_knife_tactile_toughness/03_mujoco_cut_timeline.png)

*↑ 刃が食材の左端から切れ始め、切っている幅の中点(当たり位置)が右へ動く。*

[![パッドのねじれ(周方向の変位 ÷ 半径)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_knife_tactile_toughness/05_stick_zone_shrinks_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_knife_tactile_toughness/05_stick_zone_shrinks.png)

*↑ パッドのねじれ(周方向の変位 ÷ 半径)。*

[![MuJoCo の柔らかい手首で刃を押し下げる(上)。下は包丁の背を挟む 2 枚のパッドの膜の像 —— この像だけで力と当たり位置を読む。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_knife_tactile_toughness/06_cut_with_fingertip_pads.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_knife_tactile_toughness/06_cut_with_fingertip_pads.gif)

*↑ 動く図 ―― MuJoCo の柔らかい手首で刃を押し下げる(上)。下は包丁の背を挟む 2 枚のパッドの膜の像 —— この像だけで力と当たり位置を読む。*

```
py -3.11 examples/poc_knife_tactile_toughness.py
```

ソース: [examples/poc_knife_tactile_toughness.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_knife_tactile_toughness.py)

この回が作った図は全部で **6 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_knife_tactile_toughness)

使用 op(ノートへ): [`combined_modulus`](https://furuse.work/ops/drive/tacsim/combined_modulus.html) · [`cutting_episode_synth`](https://furuse.work/ops/drive/cutting/cutting_episode_synth.html) · [`cutting_scene`](https://furuse.work/ops/drive/cutting/cutting_scene.html) · [`food_cut_width`](https://furuse.work/ops/drive/cutting/food_cut_width.html) · [`hertz_sphere`](https://furuse.work/ops/drive/tacsim/hertz_sphere.html) · [`knife_load_from_pads`](https://furuse.work/ops/drive/cuttouch/knife_load_from_pads.html) · [`membrane_indent_sphere`](https://furuse.work/ops/drive/tacsim/membrane_indent_sphere.html) · [`membrane_render_markers`](https://furuse.work/ops/drive/tacslip/membrane_render_markers.html) · [`membrane_render_rgb`](https://furuse.work/ops/drive/tacsim/membrane_render_rgb.html) · [`pad_context`](https://furuse.work/ops/drive/pegtactile/pad_context.html) · [`pad_marker_displacement`](https://furuse.work/ops/drive/pegtactile/pad_marker_displacement.html) · [`pad_params`](https://furuse.work/ops/drive/pegtactile/pad_params.html) · [`pad_tactile_read`](https://furuse.work/ops/drive/pegtactile/pad_tactile_read.html) · [`peg_wrench_to_pad_loads`](https://furuse.work/ops/drive/pegtactile/peg_wrench_to_pad_loads.html) · [`rigid_rotation_fit`](https://furuse.work/ops/drive/tactorque/rigid_rotation_fit.html) · [`torsion_partial_slip`](https://furuse.work/ops/drive/cuttouch/torsion_partial_slip.html) · [`toughness_from_pads`](https://furuse.work/ops/drive/cuttouch/toughness_from_pads.html)

## No.2026.142 —— その数字のうち、いくつが測り方のものか ―― ゲージ R&R と測定の不確かさ

[![その数字のうち、いくつが測り方のものか ―― ゲージ R&R と測定の不確かさ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/01_scene.png)

*↑ **その数字のうち、いくつが測り方のものか ―― ゲージ R&R と測定の不確かさ** ―― 管理図も工程能力も**測定のばらつきを含んだままの数字**を見ている —— それを分け、1 回の測定の不確かさを報告できる形にするまでを全部「絵の外」から採点した。★平方和の分解は**代数的な恒等式**なので分散成分の出し方と独立に閉じる(相対差 1e-16)。繰り返し性は升目ごとの標本分散の平均に等しく、**既存の numpy が真値**になる。★★規格の worked example(90 点)を再現: EV 0.199933 / AV 0.226838 / GRR 0.302372 / PV 1.042327 で公表値と最大差 1.5e-06、寄与率 3.4 / 4.4 / 7.8 / 92.2 % は完全一致。★★交互作用を残すか誤差へ畳むかで **EV が 7.3 % 動く** —— どちらのモデルで出したかを返り値に載せないと、同じ工程について別の数字を返して理由が残らない。★★負の分散成分は稀な端ではなく、真値 0 のとき 40 本中 24 本で出る(丸めを申告しない実装は「差は無い」と言い切る)。★カッパは一致率ではない: 独立でたらめでも合格率 0.95 なら一致率 0.920 に対し κ は 0.101。★★**相関を無視した誤りの向きは一定でない** —— u_c(R) は 0.0702 → 0.1945(2.8 倍の過大)、u_c(X) は過小。★有効自由度は **t 表を引く直前に切り捨てる**(16.64 → 16 で k = 2.1199)。★★**正しく失敗する**: 比較損失を停留点で評価すると伝播則は u=0・区間 [0,0] を返す —— 1 次近似が情報を失う手法の限界で、モンテカルロは [0, 150]e-6。黙って 0 を返さず構造で申告する。★★4 つの矩形分布の和には Irwin-Hall の**厳密解** −3.879407 があり、正規近似を使う伝播則は 0.040521 構造的に広く出る。検査 28 件・図 9 枚。*

[![測定の行為(GRR)が総変動に占めるのは 7.8 %、部品どうしの差が 92.2 %。どちらも公表値と一致する(最大差 1.5e-06)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/02_components_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/02_components.png)

*↑ 測定の図 ―― 測定の行為(GRR)が総変動に占めるのは 7.8 %、部品どうしの差が 92.2 %。どちらも公表値と一致する(最大差 1.5e-06)。*

[![各升目(部品 × 測定者)で 3 回測った値の**幅**。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/03_r_chart_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/03_r_chart.png)

*↑ 各升目(部品 × 測定者)で 3 回測った値の**幅**。*

[![交互作用が**無い**ところ(左端)では畳むほうが真値 0.30 に近く、あるところでは畳むと交互作用を誤差に混ぜてしまうので上へ外れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/07_pooling_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/07_pooling.png)

*↑ 交互作用が**無い**ところ(左端)では畳むほうが真値 0.30 に近く、あるところでは畳むと交互作用を誤差に混ぜてしまうので上へ外れる。*

[![電圧と電流の相関だけを振った(他の 2 つは実測値で固定)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/12_correlation_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/12_correlation_sweep.png)

*↑ 電圧と電流の相関だけを振った(他の 2 つは実測値で固定)。*

[![校正証明書に「±a」とだけ書いてあるとき、それを標準不確かさへ直す除数は**形で決まります** —— 矩形なら a/√3、三角なら a/√6、両端に寄る U 字(温度の上下動など)なら a/√2、「9](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/18_divisors_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/18_divisors.png)

*↑ 校正証明書に「±a」とだけ書いてあるとき、それを標準不確かさへ直す除数は**形で決まります** —— 矩形なら a/√3、三角なら a/√6、両端に寄る U 字(温度の上下動など)なら a/√2、「95 % の幅」と書いてあるなら 1.959964 で割る。*

[![評価点 x₁ を 0 から 0.026 へ動かしたもの。★左端では真の分布が**原点に肩を持つ指数**(u²χ²₂)で、伝播則は感度 c = 2x₁ が 0 になるため区間が**1 点に潰れる**。少し動かすと今度は区間が**負の損失**へ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/16_breakdown_movie.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/16_breakdown_movie.gif)

*↑ 動く図 ―― 評価点 x₁ を 0 から 0.026 へ動かしたもの。★左端では真の分布が**原点に肩を持つ指数**(u²χ²₂)で、伝播則は感度 c = 2x₁ が 0 になるため区間が**1 点に潰れる**。少し動かすと今度は区間が**負の損失**へ張り出す(物理的にありえない)。さらに離れると真の分布が正規に近づき、両者はようやく重なる —— **壊れ方は連続ではなく、3 つの段階がある**。*

```
py -3.11 examples/poc_measurement_system_analysis.py
```

ソース: [examples/poc_measurement_system_analysis.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_measurement_system_analysis.py)

この回が作った図は全部で **22 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_measurement_system_analysis)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`grid_lines`](https://furuse.work/ops/annotate/plot/grid_lines.html) · [`gum_expanded`](https://furuse.work/ops/spc/uncertainty/gum_expanded.html) · [`gum_monte_carlo`](https://furuse.work/ops/spc/uncertainty/gum_monte_carlo.html) · [`gum_propagate`](https://furuse.work/ops/spc/uncertainty/gum_propagate.html) · [`gum_standard_uncertainty`](https://furuse.work/ops/spc/uncertainty/gum_standard_uncertainty.html) · [`gum_validate`](https://furuse.work/ops/spc/uncertainty/gum_validate.html) · [`legend_box`](https://furuse.work/ops/annotate/furniture/legend_box.html) · [`msa_anova_table`](https://furuse.work/ops/spc/msa/msa_anova_table.html) · [`msa_attribute_agreement`](https://furuse.work/ops/spc/msa/msa_attribute_agreement.html) · [`msa_bias_linearity`](https://furuse.work/ops/spc/msa/msa_bias_linearity.html) · [`msa_gauge_rr`](https://furuse.work/ops/spc/msa/msa_gauge_rr.html) · [`nice_ticks`](https://furuse.work/ops/annotate/plot/nice_ticks.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html)

## No.2026.150 —— 収差の絵は、絵のまま採点できる —— ゼルニケ多項式と点像

[![収差の絵は、絵のまま採点できる —— ゼルニケ多項式と点像](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_zernike_aberrations/01_zernike_pyramid_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_zernike_aberrations/01_zernike_pyramid.png)

*↑ **収差の絵は、絵のまま採点できる —— ゼルニケ多項式と点像** ―― **収差の絵は、描いたあとに絵から係数を読み返せて、その読み返しが閉形式と厳密に一致する** —— 使うのは箱にある `fit_zernike`(円板画像 → {(n,m): 係数})と `wavefront_stats`(RMS・PV・ストレール比)だけ。ゼルニケ多項式は単位円板の上の直交系で、収差の言葉そのものになっている ——(2,0) がデフォーカス、(2,±2) が非点収差、(3,±1) がコマ、(4,0) が球面収差。n ≤ 6 の **28 本**(閉形式 (n+1)(n+2)/2)はどれも縁で厳密に 1 になり(28 本すべて **0.0e+00**)、半径方向の零点の本数は **(n−|m|)/2** に 28 本すべてで一致する。直交性も閉形式 **π/(2(n+1))·(1+δ_m0)** と対角で相対差 **4.86e-06**、非対角は **5.50e-07**。★★芯 1: **既存 op が自分で開示している「~10 % のクロストーク」の原因は、解像度ではなかった。** `fit_zernike` の docstring は「既定のサンプリングではモード間に最大 ~10 % のクロストークが残る。定量が要るなら nr/nt を上げよ」と書いている。ところが漏れは **1/nr** でしか落ちず(2 倍ごとの比 **1.93 / 1.78 / 1.50** —— 1/nr² が言う 4 には遠く、しかも上げるほど鈍る)、**8 倍の解像度=計算 64 倍で 5.1 倍**しか買えない。真因は**極座標格子のいちばん外のリング 1 本**が瞳の縁に乗り、双一次補間が外側の 0 を吸い込むこと —— **解像度を一切変えず**にその 1 本を捨てるだけで、漏れは 4 モードの最悪でも 0.09801 → **0.000259**(**379 倍**)、回収のずれは **0.000010**。多項式を円板の 2 % 外まで延ばして段差を縁から追い出しても **0.000042** まで落ち、同じ結論になる。★★芯 2: **絵は回るのに、測った数は 1 ビットも動かない。** 回転は係数を exp(−imθ) 倍するだけなので対の振幅 √(c₊²+c₋²) は厳密に不変 —— 6 通りの角度で最大 **1.1e-16**、二乗和の差は **0.0e+00**。しかも**絵に描いてから読み返しても** 3 通りの回転で振幅の幅は **3.34e-10**(真値 0.664831)。★★芯 3: **点像の輪はベッセル関数の零点で決まり、絵から測り返せる。** 第 1 暗環は j₁ の第 1 零点 ÷ π = **1.219670 λ/D** で、絵の振幅が符号を変える点から **3.6e-04** 以内(瞳の半径を 3 倍に振っても同じ桁)。無収差のストレール比は厳密に **1.000000000000**。`wavefront_stats` が返すマレシャル近似は RMS 0.02 波で差 **8.8e-06** なのに 0.18 波で **2.0e-02** —— **2308 倍**に開く(op 自身が返す RMS は絵から測った RMS と相対差 3.69e-05)。★★芯 4: **干渉縞が消える半径も閉形式。** 球面収差 6ρ⁴−6ρ²+1 の勾配 12ρ(2ρ²−1) は **ρ = 1/√2** で 0 になり、そこだけ縞が広い帯になる —— 絵から **0.70462**(真値 0.70711)、ずれは縞の本数に反比例して消える(振幅 2 倍で 2.02 / 2.01 倍)。★★芯 5: **絵の対称性の回数から m が読めるが、偶数の m は 2 倍の回数で現れる。** 点像を方位方向にフーリエ変換すると、m = 0(デフォーカス・球面収差)は全ハーモニクスが床以下(最大 0.00110)で厳密な回転対称、**奇数の |m|** は k = |m| に立ち(コマ 0.1200 / 三つ葉 0.0946)、**偶数の |m| は k = |m| が厳密に消えて**(最大 0.00050)k = 2|m| から立つ ——非点収差が「2 回対称」でなく **4 回**に見える理由がこれで、偶数 m の波面は θ に対し π 周期なので瞳の場が点対称になり**1 次の交差項が恒等的に 0** になるから。収差を半分にすると奇数は **2.06 / 2.02 / 1.87 / 1.97**(1 次)、非点収差は **3.67 / 3.66**(2 次)。★★芯 6: **濃淡の付け方は飾りではない。** 無収差の点像の 3.5〜8.0 λ/D を 8 bit にすると、線形では階調 **1 段**(完全な黒。その帯の最大値は 1.6e-03 で 255 倍しても 1 に届かない)、asinh なら **66 段**。しかも asinh は狭義単調なので**画素の大小は 4,998 組すべてで入れ替わらない** —— 見やすくすることと嘘をつくことは別だと数で言える。★**外した予言を 3 つ残してある**: 瞳の縁をなめらかにしても第 1 暗環は改善しない / 誤差 ∝ 1/瞳径 も成立しない —— 真因は私の**線形補間**で、線形だと最悪 **1.1e-02** でしかも瞳を大きくすると悪化するのに、3 次なら **3.6e-04**(**30 倍**)で瞳を 3 倍に振っても平らだった / 停留環を放物線で精密化したら悪化した。★**自分の測り方の欠陥も 2 件**: 瞳を格子の中心から半画素ずらして置いていた(像面に位相が乗る。直すと虚部の残り 5.3e-17)/ 方位を最近傍で拾って、**瞳の半径にも縁の滑らかさにもまったく依らない** 偽信号 0.01489 を作っていた(双一次で 0.00058、**26 倍**)。当てはめは op と同じ手順を numpy で書いた**写し**で回している(op 本体は torch を要り、CI の一部に入っていないため)—— torch がある環境では本物と照合していて、最大差は **4.7e-07**(grid_sample が float32 なのでその桁)。**新しい op は 1 つも足していない。** 検査 28 件・図 14 枚(動く図 2 枚を含む)。*

[![**波面を立体に起こす**(箱の `render3d` で描画)。左上がデフォーカス(お椀)、右上が非点収差(鞍)、左下がコマ、右下が球面収差。収差の名前は、この形の名前です。立体にしても採点は変わりません —— 係数は絵ではなく多項式に属](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_zernike_aberrations/02_wavefront_3d_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_zernike_aberrations/02_wavefront_3d.png)

*↑ 測定の図 ―― **波面を立体に起こす**(箱の `render3d` で描画)。左上がデフォーカス(お椀)、右上が非点収差(鞍)、左下がコマ、右下が球面収差。収差の名前は、この形の名前です。立体にしても採点は変わりません —— 係数は絵ではなく多項式に属しているからで、後の図で**絵を回しても数が動かないこと**を見せます。*

[![**干渉縞** cos(2πW)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_zernike_aberrations/03_interferogram_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_zernike_aberrations/03_interferogram.png)

*↑ **干渉縞** cos(2πW)。*

[![**濃淡の付け方は飾りではありません。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_zernike_aberrations/05_tone_matters_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_zernike_aberrations/05_tone_matters.png)

*↑ **濃淡の付け方は飾りではありません。*

[![**28 × 28 のグラム行列** ∫Z_n^m Z_n'^m' ρdρdθ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_zernike_aberrations/10_gram_matrix_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_zernike_aberrations/10_gram_matrix.png)

*↑ **28 × 28 のグラム行列** ∫Z_n^m Z_n'^m' ρdρdθ。*

[![`wavefront_stats` が返すストレール比はマレシャル近似 exp(−(2πσ)²) です。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_zernike_aberrations/12_strehl_vs_marechal_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_zernike_aberrations/12_strehl_vs_marechal.png)

*↑ `wavefront_stats` が返すストレール比はマレシャル近似 exp(−(2πσ)²) です。*

[![**スルーフォーカス** —— デフォーカスを −0.55 波から +0.55 波まで振って戻します。輪が**同心のまま**伸縮するのがデフォーカスの特徴で、ピントの前後で絵が対称になります(だから往復させても継ぎ目が見えません)。中央の ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_zernike_aberrations/06_through_focus.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_zernike_aberrations/06_through_focus.gif)

*↑ 動く図 ―― **スルーフォーカス** —— デフォーカスを −0.55 波から +0.55 波まで振って戻します。輪が**同心のまま**伸縮するのがデフォーカスの特徴で、ピントの前後で絵が対称になります(だから往復させても継ぎ目が見えません)。中央の 1 コマだけが無収差のエアリーで、そこだけストレール比が厳密に **1.000000000000** です。*

[![**絵は回るのに、測った数は動きません。** 左が波面(コマ 0.62 ＋ 非点収差 0.35 ＋ 球面収差 0.18)、右がその点像。1 周ぶん回しています。回転は係数を exp(−imθ) 倍するだけなので、対の振幅 √(c₊²+c₋²](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_zernike_aberrations/07_rotating_coma.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_zernike_aberrations/07_rotating_coma.gif)

*↑ 動く図 ―― **絵は回るのに、測った数は動きません。** 左が波面(コマ 0.62 ＋ 非点収差 0.35 ＋ 球面収差 0.18)、右がその点像。1 周ぶん回しています。回転は係数を exp(−imθ) 倍するだけなので、対の振幅 √(c₊²+c₋²) は**厳密に**不変 —— 6 通りの角度で最大 **1.1e-16**。しかも**絵に描いてから `fit_zernike` で読み返しても**、3 通りの回転で振幅の幅は **3.3e-10** しかありません(真値 0.664831)。★球面収差(m = 0)だけは絵そのものが回りません —— m = 0 は回転で変わらないモードだからで、これも絵から読めます。*

```
py -3.11 examples/poc_zernike_aberrations.py
```

ソース: [examples/poc_zernike_aberrations.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_zernike_aberrations.py)

この回が作った図は全部で **14 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_zernike_aberrations)

使用 op(ノートへ): [`fit_zernike`](https://furuse.work/ops/3d/curvilinear/fit_zernike.html) · [`wavefront_stats`](https://furuse.work/ops/optics/imaging/wavefront_stats.html)

## No.2026.151 —— 速くする工夫は、全部おなじ数の別の括り方だった —— 注意機構を恒等式で採点する

[![速くする工夫は、全部おなじ数の別の括り方だった —— 注意機構を恒等式で採点する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_attention_identities/01_attention_masks_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_attention_identities/01_attention_masks.png)

*↑ **速くする工夫は、全部おなじ数の別の括り方だった —— 注意機構を恒等式で採点する** ―― **LLM に至る系譜に出てくる高速化・省メモリ化は、どれも近似ではなく恒等式の括り直しで、その等式は機械精度で検算できる** —— 使うのは新しい族 `llmcore`(10 op、**numpy だけ・torch を使わない**)。入力は**画像のパッチ列**にしてある(64×64 を 8×8 で切った 64 トークン)ので、注意がそのまま ViT の入口になり、絵の側でも主張が立つ。★★芯 1: **FlashAttention は近似ではない。** タイル + online softmax は一括と一致する —— タイルの大きさを 7 通り(1 行〜64 行)振って最悪 **1.33e-15**。速さの出どころは計算を変えたことではなく、**(T, T) の行列を作らない**こと。★外した予言: 「タイルを細かくするほど誤差が積もる」→ 積もりはするが **64 枚 1.33e-15 対 1 枚 1.22e-15 = 1.1 倍**にしかならない。★★芯 2: **線形 Attention は結合則そのもの。** (QKᵀ)V == Q(KᵀV) が **1.18e-15**、因果つきの累積状態でも **9.39e-16**。O(T²d) と O(Td²) は同じ数の別の括り方で、**演算回数の比は厳密に T/d**(T=2048 で 32 倍、整数)—— 交差点が **T == d** にあるのはその帰結。★予言は途中で外れる —— 実測の時間比は 32 倍に届かず **15〜16 倍で頭打ち**(二次の側が帯域律速)。★★時間は機械が決める(同じ commit で手元 11.6 倍・CI の走者 2.0 倍)ので、**この PoC は演算回数の恒等式だけを合否にし、時間は報告に落としている**。★★芯 3: **因果マスクの下では、未来を書き換えても前の出力が 1 ビットも動かない**(**0.0e+00**)。これは同義反復ではない —— 実際に 32 行目から先の key/value を**別の乱数に差し替えて**測っており、後半は **0.403** 動く。KV Cache が成り立つ根拠がこれで、逐次に 1 行ずつ進めた結果は一括と **5.92e-16**。★★芯 4: **注意の疎さは整数で数えられる。** 因果マスクの非ゼロは厳密に **T(T+1)/2 = 2080**、幅 9 の窓は **Σ min(i+1, W) = 540** —— どちらも**浮動小数の許容差が要らない**主張。★★芯 5: **位置符号が無ければ、注意はパッチの順番を見ていない。** パッチを並べ替えて出力を戻すと**元と一致する**(**4.4e-16**)。RoPE を入れると一致しない(**0.018**)—— **それが位置符号の仕事**で、絵で見ると「同じ絵」と「別の絵」になる。★★芯 6: **RoPE は回転なのでノルムを保ち、内積は相対位置だけで決まる。** ノルムの差は 64 本すべてで **4.44e-16**、位置の差を 7 に固定して絶対位置を 40 通り動かした内積の幅が **1.11e-15**。★★芯 7: **GQA の両端は厳密に既存の 2 つ。** `n_kv_heads == n_heads` で MHA、`== 1` で MQA と **0.0e+00** で一致し、中間(`n_kv_heads=2`)はどちらとも **0.942** 違う。「中間を取る」という主張が端で検算できる。ほかに: **RMS 正規化の出力は RMS が厳密に 1**(ずれ 2.22e-16、eps=1e-6 を入れると 1.53e-04 ずれる —— それが eps の値段)/ **注意は凸結合なので値域を出ない**が(出力 [0.474, 0.502] ⊂ 入力 [0.025, 1.000])**同時に幅が 35.4 倍に潰れる**(平均は対比を消す)/ **最大値を引くのは飾りではない**(スコアを大きくすると素の exp は 64 行のうち **15 行**が inf/NaN になり、引けば 0 行)。★**外した予言をもう 1 つ残してある**: online softmax の途中の状態が答えに単調に近づくと読んだが、**単調ではない**(0.10 / 0.17 / 0.19 / 0.15 / 0.11 / 0.07 / 0.02 / 0.00 と上がってから下がる)——走っている最大値が更新されるたびに分母が組み替わるので、途中の値は答えの近似ですらない。★**8 通りの誤りが全部 op 名を名乗って止まる**(どの op が何を拒んだかが読める)。検査 26 件・図 10 枚。*

[![縦軸は **1e-16 単位**。タイルを 64 枚に割っても相対差は **1.3e-15** —— 近似ではなく、同じ和を別の順で足しているだけ。★外した予言: 誤差はタイル数に比例して積もる → **64 倍のタイル数で 1.1 倍**](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_attention_identities/02_tiled_exactness_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_attention_identities/02_tiled_exactness.png)

*↑ 測定の図 ―― 縦軸は **1e-16 単位**。タイルを 64 枚に割っても相対差は **1.3e-15** —— 近似ではなく、同じ和を別の順で足しているだけ。★外した予言: 誤差はタイル数に比例して積もる → **64 倍のタイル数で 1.1 倍**にしかならない。*

[![**答えは同じ**(相対差 1.2e-15)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_attention_identities/03_linear_crossover_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_attention_identities/03_linear_crossover.png)

*↑ **答えは同じ**(相対差 1.2e-15)。*

[![2 枚目と 3 枚目は**差 4.4e-16** —— パッチを並べ替えてから戻すと元に戻る(置換同変)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_attention_identities/05_patch_shuffle_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_attention_identities/05_patch_shuffle.png)

*↑ 2 枚目と 3 枚目は**差 4.4e-16** —— パッチを並べ替えてから戻すと元に戻る(置換同変)。*

[![2 本の線は 64 本すべてで重なる(最大差 **4.4e-16**)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_attention_identities/07_rope_norm_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_attention_identities/07_rope_norm.png)

*↑ 2 本の線は 64 本すべてで重なる(最大差 **4.4e-16**)。*

[![行和が 1 なので出力は入力の凸結合で、値域 [0.025, 1.000) を出ない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_attention_identities/09_convex_mixing_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_attention_identities/09_convex_mixing.png)

*↑ 行和が 1 なので出力は入力の凸結合で、値域 [0.025, 1.000] を出ない。*

```
py -3.11 examples/poc_attention_identities.py
```

ソース: [examples/poc_attention_identities.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_attention_identities.py)

この回が作った図は全部で **10 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_attention_identities)

使用 op(ノートへ): [`attention_apply`](https://furuse.work/ops/llmcore/score/attention_apply.html) · [`attention_grouped`](https://furuse.work/ops/llmcore/attend/attention_grouped.html) · [`attention_linear`](https://furuse.work/ops/llmcore/attend/attention_linear.html) · [`attention_scores`](https://furuse.work/ops/llmcore/score/attention_scores.html) · [`attention_softmax`](https://furuse.work/ops/llmcore/attend/attention_softmax.html) · [`attention_tiled`](https://furuse.work/ops/llmcore/attend/attention_tiled.html) · [`attention_weights`](https://furuse.work/ops/llmcore/score/attention_weights.html) · [`kv_cache_decode`](https://furuse.work/ops/llmcore/decode/kv_cache_decode.html) · [`project`](https://furuse.work/ops/3d/bundle_adjust/project.html) · [`rms_norm`](https://furuse.work/ops/llmcore/prepare/rms_norm.html) · [`rope_rotate`](https://furuse.work/ops/llmcore/prepare/rope_rotate.html)

### 医用・生物ウィング ―― 個数が合っていて中身が外れている

細胞を数える、核の DNA 量を読む、血管の分岐を測る、創傷の面積を追う。どれも「1 つの数字」で報告されがちで、しかもその数字が合ってしまう場面があります。過分割と過統合が釣り合って個数の偏りが +0.3 個になる細胞計数、背景を引き忘れても分類が生き残る倍数性、いちばん安定して、いちばん間違った治癒定数を返す較正。

この部屋の 26 点は、真値に「どれとどれが重なっているか」「面積と DNA 量が別々にばらつく」「分岐則を厳密に満たす木」といった、ラベル画像だけでは残らない情報を持たせています。実データに差し替えるときも、ラベル画像だけを真値と呼ぶと主題そのものが消える、と各 docstring に書いてあります。

見どころは、性能が上がったように見えて測っている量が入れ替わっている場面です。ぼかすほど面積分類器が良くなるのは、面積という名前で DNA 量を漏らしているから。1 つの指標が良くなった理由を毎回追わないと、こういう嘘を成果として持ち帰ることになります。

## No.2026.057 —— 骨梁の厚さ・間隔・骨体積率 ―― 平板モデルと直接法は同じ画像で別の値になる

[![骨梁の厚さ・間隔・骨体積率 ―― 平板モデルと直接法は同じ画像で別の値になる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bone_trabecular_thickness/01_scene_truth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bone_trabecular_thickness/01_scene_truth.png)

*↑ **骨梁の厚さ・間隔・骨体積率 ―― 平板モデルと直接法は同じ画像で別の値になる** ―― 線分の集合として閉形式で描いた 2-D 骨梁網(幅の中央値 120 µm)を、部分体積ぼけ・CT 雑音・カップ状バイアスで観測した。真値そのものが複数あり、幅の長さ加重平均 104.8 µm に対し最大内接円の定義では 121.6 µm、平板モデルは 118.4 µm ―― どの真値と比べるかで 9〜16 % が先に動く。解像度の崖は平均でなく分布に来る(画素 60 µm で分布の重なり 0.83 → 0.09、平均は量子化 -29.5 % と大津の太り +26.6 % が打ち消す)。雑音は斑点(σ 0.10 から)と途切れ(σ 0.15 から)の 2 方向から壊し、面積オープニングは斑点だけを消す。*

[![Tb.Th の平均は 2 px/骨梁でも持つが、BV/TV と分布は壊れている。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bone_trabecular_thickness/02_resolution_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bone_trabecular_thickness/02_resolution_sweep.png)

*↑ 測定の図 ―― Tb.Th の平均は 2 px/骨梁でも持つが、BV/TV と分布は壊れている。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bone_trabecular_thickness/03_thickness_distribution_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bone_trabecular_thickness/03_thickness_distribution.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bone_trabecular_thickness/06_thickness_map_measured_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bone_trabecular_thickness/06_thickness_map_measured.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bone_trabecular_thickness/09_noise_remedies_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bone_trabecular_thickness/09_noise_remedies.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bone_trabecular_thickness/12_bias_masks_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bone_trabecular_thickness/12_bias_masks.png)

*↑ この回の図*

```
py -3.11 examples/poc_bone_trabecular_thickness.py
```

ソース: [examples/poc_bone_trabecular_thickness.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bone_trabecular_thickness.py)

この回が作った図は全部で **14 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_bone_trabecular_thickness)

使用 op(ノートへ): [`blob_distance`](https://furuse.work/ops/blob/split/blob_distance.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`dc_retinex`](https://furuse.work/ops/2d/decomposition/dc_retinex.html) · [`dist_transform`](https://furuse.work/ops/2d/region/dist_transform.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`get_region_thickness`](https://furuse.work/ops/2d/features/get_region_thickness.html) · [`local_thickness`](https://furuse.work/ops/2d/morphology/local_thickness.html) · [`opening_circle`](https://furuse.work/ops/2d/region/opening_circle.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`sk_area_opening`](https://furuse.work/ops/2d/morphology/sk_area_opening.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html)

## No.2026.008 —— 重なった細胞をどう数えるか ―― 個数・過分割・過統合を別々に測る

[![重なった細胞をどう数えるか ―― 個数・過分割・過統合を別々に測る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cell_counting/01_scene_dense_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cell_counting/01_scene_dense.png)

*↑ **重なった細胞をどう数えるか ―― 個数・過分割・過統合を別々に測る** ―― 重なった細胞の合成画像で、個数・過分割・過統合を別々に数えた図。いちばん密な条件でゼロ点は 78 個中 25 個を取りこぼし、失点は全部過統合。種の間引きを振ると釣り合う点があり、個数の偏り +0.3 個なのに分割誤りは 13.3 件残る ―― 個数だけ報告すれば最良の設定として通る。*

[![誤り合計の谷と |偏り| の谷は同じ場所に来ない。どちらを最適と呼ぶかで答えが変わる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cell_counting/02_h_tradeoff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cell_counting/02_h_tradeoff.png)

*↑ 測定の図 ―― 誤り合計の谷と |偏り| の谷は同じ場所に来ない。どちらを最適と呼ぶかで答えが変わる。*

[![偏りが 0 を横切る間隔 6 で分割誤りは 13.3 件残る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cell_counting/03_count_cancellation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cell_counting/03_count_cancellation.png)

*↑ 偏りが 0 を横切る間隔 6 で分割誤りは 13.3 件残る。*

[![真値の前景率 11.6 %。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cell_counting/04_noise_vs_shading_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cell_counting/04_noise_vs_shading.png)

*↑ 真値の前景率 11.6 %。*

```
py -3.11 examples/poc_cell_counting.py
```

ソース: [examples/poc_cell_counting.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_cell_counting.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_cell_counting)

使用 op(ノートへ): [`circularity`](https://furuse.work/ops/2d/features/circularity.html) · [`distance_transform`](https://furuse.work/ops/2d/region/distance_transform.html) · [`fill_holes`](https://furuse.work/ops/2d/region/fill_holes.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`sk_otsu`](https://furuse.work/ops/2d/segmentation/sk_otsu.html) · [`vol_distance_transform`](https://furuse.work/ops/3d/medial/vol_distance_transform.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_local_maxima`](https://furuse.work/ops/3d/feature/vol_local_maxima.html) · [`vol_watershed`](https://furuse.work/ops/3d/segment/vol_watershed.html) · [`xsk2_h_maxima`](https://furuse.work/ops/2d/segmentation/xsk2_h_maxima.html)

## No.2026.061 —— 蛍光の共局在は漏れ込みで嘘をつく ―― Pearson と Manders は別の場所で壊れる

[![蛍光の共局在は漏れ込みで嘘をつく ―― Pearson と Manders は別の場所で壊れる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/01_scene_channels_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/01_scene_channels.png)

*↑ **蛍光の共局在は漏れ込みで嘘をつく ―― Pearson と Manders は別の場所で壊れる** ―― 細胞体に小胞状の点を 2 色ぶん撒き、B の点の 0 / 25 / 50 / 100 % を A と同位置に置いて真の共局在率を握る。漏れ込み行列 [[1, α], [β, 1]] と細胞質・PSF・光子雑音を掛けた観測に Pearson r と Otsu-Manders を当てると、無関係な 2 色が α=β=10 % で r=0.203、M1=0.132 になる。単染色対照から α を 0.0996(真値 0.10)と推定して線形分離すれば r は 0.007 に戻るが、Manders は 100 % でも 0.699(Otsu より下の裾が落ちる、閉形式の予想 0.750)。Pearson が 0.5 を超える崖は対称漏れ込み α=0.282(予想 2−√3=0.268)、ぼけの崖は Manders だけに来て σ=2.5 px で Otsu の前景が細胞体へ飛び移る。Costes のシャッフル検定は漏れ込みだけの r を p=0.000 で「有意」と言う。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/02_scene_unmixed_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/02_scene_unmixed.png)

*↑ 測定の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/03_cytofluorogram_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/03_cytofluorogram.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/05_costes_significance_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/05_costes_significance.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/07_crosstalk_sweep_manders_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/07_crosstalk_sweep_manders.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/09_psf_masks_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/09_psf_masks.png)

*↑ この回の図*

```
py -3.11 examples/poc_colocalization_crosstalk.py
```

ソース: [examples/poc_colocalization_crosstalk.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_colocalization_crosstalk.py)

この回が作った図は全部で **11 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_colocalization_crosstalk)

使用 op(ノートへ): [`gauss_image`](https://furuse.work/ops/2d/smoothing/gauss_image.html) · [`mat_lstsq`](https://furuse.work/ops/math/linalg/mat_lstsq.html) · [`mat_solve`](https://furuse.work/ops/math/linalg/mat_solve.html) · [`noise_sigma`](https://furuse.work/ops/astrostack/quality/noise_sigma.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`photon_sample`](https://furuse.work/ops/photon/counting/photon_sample.html) · [`reg_erode`](https://furuse.work/ops/2d/region/reg_erode.html) · [`stat_correlation`](https://furuse.work/ops/math/stats/stat_correlation.html)

## No.2026.074 —— MRI のバイアス場と組織面積 ―― 灰白質と白質は逆向きに壊れ、足すと隠れる

[![MRI のバイアス場と組織面積 ―― 灰白質と白質は逆向きに壊れ、足すと隠れる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/02_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/02_scene.png)

*↑ **MRI のバイアス場と組織面積 ―― 灰白質と白質は逆向きに壊れ、足すと隠れる** ―― 楕円殻の脳スライス風ファントム(頭蓋/CSF/皺つき皮質/WM、面積は幾何で既知)に表面コイル型の乗算場と Rician 雑音を掛け、大域 3 クラス大津(xsk2_multiotsu)で 3 組織の面積を測った図。振幅 30 % で GM +20.2 % / WM -7.7 % なのに GM+WM は +0.0 % で誤差が隠れ、雑音を止めると符号が反転する(GM -11.8 %)。崖の幾何予測 30 % に対し実測は 17.5 %。log I をそのまま平滑する素朴な補正は場が無くても GM +81.8 % 壊し、分割の残差を平滑する Wells 型反復にすると 40 % でも +1.8 %。場を 4 px まで細かくすると全補正器が壊れ、SNR 15 では場なしでも GM +8.5 %(WM が GM の 2.6 倍あるので小さい組織に出る)。*

[![雑音だけでは壊れず、場だけで GM と WM が逆向きに動く。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/01_controls_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/01_controls.png)

*↑ 測定の図 ―― 雑音だけでは壊れず、場だけで GM と WM が逆向きに動く。*

[![幾何予測(しきい値固定・雑音なし)と大津の実測は同じ振幅で崖を越える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/03_amplitude_sweep_zero_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/03_amplitude_sweep_zero.png)

*↑ 幾何予測(しきい値固定・雑音なし)と大津の実測は同じ振幅で崖を越える。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/05_amplitude_residual_cv_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/05_amplitude_residual_cv.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/07_bias_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/07_bias_map.png)

*↑ この回の図*

[![σ_b 4 px は皮質リボンの太さ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/09_frequency_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/09_frequency_sweep.png)

*↑ σ_b 4 px は皮質リボンの太さ。*

```
py -3.11 examples/poc_mri_bias_field.py
```

ソース: [examples/poc_mri_bias_field.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_mri_bias_field.py)

この回が作った図は全部で **11 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_mri_bias_field)

使用 op(ノートへ): [`dc_homomorphic`](https://furuse.work/ops/2d/decomposition/dc_homomorphic.html) · [`eval_bspline_surface`](https://furuse.work/ops/3d/freeform/eval_bspline_surface.html) · [`eval_poly_surface`](https://furuse.work/ops/3d/surface_fit/eval_poly_surface.html) · [`fit_bspline_surface`](https://furuse.work/ops/3d/freeform/fit_bspline_surface.html) · [`fit_poly_surface`](https://furuse.work/ops/3d/surface_fit/fit_poly_surface.html) · [`overlay_labels`](https://furuse.work/ops/annotate/overlay/overlay_labels.html) · [`xsk2_multiotsu`](https://furuse.work/ops/2d/segmentation/xsk2_multiotsu.html)

## No.2026.027 —— 蛍光核の積分輝度から倍数性を出す ―― 面積では分かれない

[![蛍光核の積分輝度から倍数性を出す ―― 面積では分かれない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_nuclei_ploidy/04_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_nuclei_ploidy/04_scene.png)

*↑ **蛍光核の積分輝度から倍数性を出す ―― 面積では分かれない** ―― DNA 量 D と面積 A を別々のばらつきで撒いた蛍光核で、倍数性を面積と積分輝度から分けた図。真の面積でも誤分類 15.4 %、積分輝度は 0 %。背景を引き忘れると分類は生き残ったまま DNA 指数だけが 2.115 → 1.702(-20 %)壊れる ―― 分類だけを見ていたら気づけない。*

[![累積分布。積分輝度の 4n は 2.1 付近に固まり、面積の 2 本は大きく重なる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_nuclei_ploidy/01_histograms_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_nuclei_ploidy/01_histograms.png)

*↑ 測定の図 ―― 累積分布。積分輝度の 4n は 2.1 付近に固まり、面積の 2 本は大きく重なる。*

[![誤分類率はほぼ 0 のままだが、DNA 指数は背景とともに 2.00 から落ちる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_nuclei_ploidy/02_background_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_nuclei_ploidy/02_background.png)

*↑ 誤分類率はほぼ 0 のままだが、DNA 指数は背景とともに 2.00 から落ちる。*

[![特徴量が分かれてさえいれば割り方は選ばない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_nuclei_ploidy/03_mixture_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_nuclei_ploidy/03_mixture.png)

*↑ 特徴量が分かれてさえいれば割り方は選ばない。*

```
py -3.11 examples/poc_nuclei_ploidy.py
```

ソース: [examples/poc_nuclei_ploidy.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_nuclei_ploidy.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_nuclei_ploidy)

使用 op(ノートへ): [`aperture_photometry`](https://furuse.work/ops/astrostack/photometry/aperture_photometry.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`sg_gmm_segment`](https://furuse.work/ops/2d/segment/sg_gmm_segment.html) · [`sk_otsu`](https://furuse.work/ops/2d/segmentation/sk_otsu.html)

## No.2026.048 —— 血管網を抜いて分岐を測る ―― ヒゲ、分岐近傍の径の過大、そして指数の脆さ

[![血管網を抜いて分岐を測る ―― ヒゲ、分岐近傍の径の過大、そして指数の脆さ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vessel_network/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vessel_network/01_scene.png)

*↑ **血管網を抜いて分岐を測る ―― ヒゲ、分岐近傍の径の過大、そして指数の脆さ** ―― Murray の法則に厳密に従う合成血管木を細線化し、分岐点・径・指数を測った図。分岐画素をそのまま数えると 25 個の分岐に 47 画素、連結成分にまとめれば 25 個ちょうど。ヒゲを作るのは細線化ではなく境界のざらつきで(余分な分岐 0 → 72 個)、径は分岐から 3 px 未満で +26.2 % 過大。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vessel_network/02_prune_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vessel_network/02_prune.png)

*↑ 測定の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vessel_network/03_radius_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vessel_network/03_radius_bias.png)

*↑ この回の図*

[![分岐から 2 px の点は 1 つも解けなかったので図から外した](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vessel_network/04_murray_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vessel_network/04_murray.png)

*↑ 分岐から 2 px の点は 1 つも解けなかったので図から外した*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vessel_network/05_summary_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vessel_network/05_summary.png)

*↑ この回の図*

```
py -3.11 examples/poc_vessel_network.py
```

ソース: [examples/poc_vessel_network.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_vessel_network.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_vessel_network)

使用 op(ノートへ): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`distance_transform`](https://furuse.work/ops/2d/region/distance_transform.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`medial_axis_points`](https://furuse.work/ops/3d/medial/medial_axis_points.html) · [`r2_split_skeleton_lines`](https://furuse.work/ops/2d/region/r2_split_skeleton_lines.html) · [`sk_medial`](https://furuse.work/ops/2d/region/sk_medial.html) · [`skeleton`](https://furuse.work/ops/2d/region/skeleton.html) · [`skeleton_branches3d`](https://furuse.work/ops/3d/medial/skeleton_branches3d.html) · [`skeleton_endpoints3d`](https://furuse.work/ops/3d/medial/skeleton_endpoints3d.html) · [`skeleton_junctions3d`](https://furuse.work/ops/3d/medial/skeleton_junctions3d.html) · [`skeleton_prune3d`](https://furuse.work/ops/3d/medial/skeleton_prune3d.html) · [`skeletonize_vol`](https://furuse.work/ops/3d/medial/skeletonize_vol.html) · [`thinning`](https://furuse.work/ops/2d/region/thinning.html) · [`vol_distance_transform`](https://furuse.work/ops/3d/medial/vol_distance_transform.html)

## No.2026.052 —— 創傷面積の経時変化 ―― 較正の誤差は面積に 2 乗で効く

[![創傷面積の経時変化 ―― 較正の誤差は面積に 2 乗で効く](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_wound_area_tracking/02_scenes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_wound_area_tracking/02_scenes.png)

*↑ **創傷面積の経時変化 ―― 較正の誤差は面積に 2 乗で効く** ―― mm 平面に置いた星形の創面(面積は閉形式)をピンホールカメラで日ごとに撮り、治癒定数 k を推定した図。距離が 4 % 違うだけで面積が 7.7 % 動き、日ごとに 1.2 % 漂うと真の k = 0.1200 に対しゼロ点は 0.1424(+18.7 %)。しかもその標準偏差 0.0049 は毎回較正の 0.0059 より小さい ―― いちばん安定して、いちばん間違った答え。*

[![ゼロ点の面積誤差。実測は閉形式の 2 乗則に乗り、線形近似からは外れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_wound_area_tracking/01_dist_square_law_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_wound_area_tracking/01_dist_square_law.png)

*↑ 測定の図 ―― ゼロ点の面積誤差。実測は閉形式の 2 乗則に乗り、線形近似からは外れる。*

[![ゼロ点は毎回もっともらしい値を返しながら、傾きだけが系統的に急になる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_wound_area_tracking/03_healing_curve_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_wound_area_tracking/03_healing_curve.png)

*↑ ゼロ点は毎回もっともらしい値を返しながら、傾きだけが系統的に急になる。*

[![較正は d に対して (1+d)²-1、しきい値はほぼ線形。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_wound_area_tracking/04_sensitivity_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_wound_area_tracking/04_sensitivity.png)

*↑ 較正は d に対して (1+d)²-1、しきい値はほぼ線形。*

[![ゼロ点は散らばりがいちばん小さく、偏りがいちばん大きい。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_wound_area_tracking/05_summary_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_wound_area_tracking/05_summary.png)

*↑ ゼロ点は散らばりがいちばん小さく、偏りがいちばん大きい。*

[![動画(800 × 544、12 fps、143 コマ): 真の面積 A0·exp(-kt)(k = 0.12 /day)で縮む創面を 8 日撮る。撮影距離は 1 日 +1.2 % 漂い(この 1 本では 448 → 495 mm)、傾き・方](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_wound_area_tracking/06_healing_video.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_wound_area_tracking/06_healing_video.gif)

*↑ 動く図 ―― 動画(800 × 544、12 fps、143 コマ): 真の面積 A0·exp(-kt)(k = 0.12 /day)で縮む創面を 8 日撮る。撮影距離は 1 日 +1.2 % 漂い(この 1 本では 448 → 495 mm)、傾き・方位・回転も毎回変わる(日と日の間は条件を補間した仮想の撮影、整数日のコマが門と同じ 1 枚)。左 = カメラの像(水色 = 測った塊、紫の十字 = 較正標識)、右 = 正対化した像。M0(1 枚目だけで較正)は0 日目 +10.7 % から 7 日目 -9.9 % へ真値の下へ漂い、下の対数グラフで M0 の傾きだけが急になる。この 1 本の k は M0 0.1473 / M1 0.1253 / M2 0.1174(真値 0.1200)、8 seed の平均は M0 0.1424(+18.7 %)/ M1 0.1225(+2.1 %)/ M2 0.1200(+0.0 %)。*

```
py -3.11 examples/poc_wound_area_tracking.py
```

ソース: [examples/poc_wound_area_tracking.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_wound_area_tracking.py)

この回が作った図は全部で **6 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_wound_area_tracking)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_select_largest`](https://furuse.work/ops/blob/select/blob_select_largest.html) · [`data_to_pixel`](https://furuse.work/ops/annotate/plot/data_to_pixel.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html) · [`warp_by_plane`](https://furuse.work/ops/3d/plane_sweep_stereo/warp_by_plane.html)

## No.2026.123 —— 幼虫コネクトームを reservoir にして数字を読む ―― 配線は効いていない

[![幼虫コネクトームを reservoir にして数字を読む ―― 配線は効いていない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_larval_connectome_reservoir/01_adjacency_binned_connectome_vs_shuffle_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_larval_connectome_reservoir/01_adjacency_binned_connectome_vs_shuffle.png)

*↑ **幼虫コネクトームを reservoir にして数字を読む ―― 配線は効いていない** ―― ショウジョウバエ幼虫の完全コネクトーム(Winding 2023、2,952 ニューロン・110,677 辺)をそのまま固定の再帰網にし、読み出しだけ閉形式の ridge で学習すると、MNIST の部分集合(訓練 4,000・評価 1,000)で 91.9 % 読める(生画素の ridge は 77.6 %)。先行研究はここで止まるが、この展示は対照を置く: 各ニューロンの入出次数を保ったまま辺を繋ぎ替えたグラフで 91.6 %、同じ密度の乱数グラフで 91.9 %、ガウス乱数の reservoir で 91.5 %。差は 3 seed で +0.3 ポイント。読み出しが使っているのは reservoir という仕組みであって、進化が決めた配線ではない。設定(入力の尺度と正則化)はコネクトームの検証分割で 1 度だけ選び、全対照に同じ値を使う。*

[![|state| of the 300 highest-degree neurons over 6 steps for one test digit: connectome | shuffle](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_larval_connectome_reservoir/02_activity_raster_connectome_vs_shuffle_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_larval_connectome_reservoir/02_activity_raster_connectome_vs_shuffle.png)

*↑ 測定の図 ―― |state| of the 300 highest-degree neurons over 6 steps for one test digit: connectome | shuffle*

[![test accuracy per reservoir variant (rows: no reservoir, connectome, shuffle, ER, Gaussian)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_larval_connectome_reservoir/03_accuracy_bars_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_larval_connectome_reservoir/03_accuracy_bars.png)

*↑ test accuracy per reservoir variant (rows: no reservoir, connectome, shuffle, ER, Gaussian)*

```
py -3.11 examples/poc_larval_connectome_reservoir.py
```

ソース: [examples/poc_larval_connectome_reservoir.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_larval_connectome_reservoir.py)

この回が作った図は全部で **3 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_larval_connectome_reservoir)

使用 op(ノートへ): [`graph_degree_preserving_shuffle`](https://furuse.work/ops/conngraph/construct/graph_degree_preserving_shuffle.html) · [`graph_degree_table`](https://furuse.work/ops/conngraph/stats/graph_degree_table.html) · [`graph_spectral_radius`](https://furuse.work/ops/conngraph/stats/graph_spectral_radius.html) · [`reservoir_encode`](https://furuse.work/ops/conngraph/reservoir/reservoir_encode.html) · [`reservoir_from_graph`](https://furuse.work/ops/conngraph/reservoir/reservoir_from_graph.html) · [`ridge_predict`](https://furuse.work/ops/conngraph/reservoir/ridge_predict.html) · [`ridge_readout`](https://furuse.work/ops/conngraph/reservoir/ridge_readout.html)

## No.2026.124 —— ハエの脳の立体の上で、刺激の波が配線を伝わるのを見る ―― コネクトーム vs 次数保存 shuffle

[![ハエの脳の立体の上で、刺激の波が配線を伝わるのを見る ―― コネクトーム vs 次数保存 shuffle](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_malecns_activity_wave/02_activity_wave_three_views.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_malecns_activity_wave/02_activity_wave_three_views.gif)

*↑ **ハエの脳の立体の上で、刺激の波が配線を伝わるのを見る ―― コネクトーム vs 次数保存 shuffle** ―― 前の展示は「読み出し精度ではコネクトームと乱数グラフの差が出ない」で終わった。この展示は同じ reservoir を**見る**ことに使う: MaleCNS(雄の全中枢神経系)で soma の座標を持つニューロンのうちシナプス総数の上位 3,000 体の部分グラフ(344,719 辺)に、右の視葉だけへ刺激を入れ、活動が伝わる様子を脳と VNC の立体(灰 = 141,781 個の soma、橙 = 右、青 = 左)を回しながら描く。隣は各ニューロンの入出次数を保って辺を繋ぎ替えたグラフに**同じ刺激・同じ入力行列**。実測: コネクトームでは刺激の重心からの活動の平均距離が 88 → 230 µm と 17 步かけて伸び、点く順は視葉(潜時 0)→ 中枢(2)→ 下行(2)で、36 步では VNC に届かない。shuffle は 3 步で 300 µm に散り、遠い 1/4 のニューロンの 93 % が最初の周期内に点く(コネクトームは 0 %)。精度では見えなかった配線の空間構造が、動きでは見える。輝度の尺度は全コマで 1 つ。回転する図のほかに、同じ瞬間を背側・側面・体軸方向の 3 方向から同時に見る図も置く(`views=`)。生データは repo に入れない(手元の feather から部分グラフを作ってキャッシュ、無ければ距離依存の合成の代替で同じ経路)。*

[![a pulse into the right optic lobe (orange = right, blue = left somata; grey = all 141781 somata) propagates through the ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_malecns_activity_wave/01_activity_wave_connectome_vs_shuffle.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_malecns_activity_wave/01_activity_wave_connectome_vs_shuffle.gif)

*↑ 測定の図 ―― a pulse into the right optic lobe (orange = right, blue = left somata; grey = all 141781 somata) propagates through the real wiring (left) and through the same degrees rewired at random (right); 3000 neurons, 344719 edges, 36 steps, one brightness scale for every frame*

[![when each neuron first lights up (yellow = step 0, orange = step 3, blue = step 6 or later, grey = n](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_malecns_activity_wave/03_activation_latency_map_connectome_vs_shuffle_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_malecns_activity_wave/03_activation_latency_map_connectome_vs_shuffle.png)

*↑ when each neuron first lights up (yellow = step 0, orange = step 3, blue = step 6 or later, grey = never within 36 steps): connectome | shuffle*

[![graph_activity_spread: |x|-weighted mean distance from the stimulated somata](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_malecns_activity_wave/04_activity_spread_mean_distance_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_malecns_activity_wave/04_activity_spread_mean_distance.png)

*↑ graph_activity_spread: |x|-weighted mean distance from the stimulated somata*

```
py -3.11 examples/poc_malecns_activity_wave.py
```

ソース: [examples/poc_malecns_activity_wave.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_malecns_activity_wave.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_malecns_activity_wave)

使用 op(ノートへ): [`graph_activation_latency`](https://furuse.work/ops/conngraph/activity/graph_activation_latency.html) · [`graph_activity_spread`](https://furuse.work/ops/conngraph/activity/graph_activity_spread.html) · [`graph_degree_preserving_shuffle`](https://furuse.work/ops/conngraph/construct/graph_degree_preserving_shuffle.html) · [`points_activity_video`](https://furuse.work/ops/conngraph/activity/points_activity_video.html) · [`reservoir_from_graph`](https://furuse.work/ops/conngraph/reservoir/reservoir_from_graph.html) · [`reservoir_states`](https://furuse.work/ops/conngraph/reservoir/reservoir_states.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html)

## No.2026.125 —— 複眼が見る像と、脳のどこが反応するかを並べる ―― 個眼を指でなぞると応答が配線を伝わる

[![複眼が見る像と、脳のどこが反応するかを並べる ―― 個眼を指でなぞると応答が配線を伝わる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_eye_to_brain/02_image_through_the_eye.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_eye_to_brain/02_image_through_the_eye.gif)

*↑ **複眼が見る像と、脳のどこが反応するかを並べる ―― 個眼を指でなぞると応答が配線を伝わる** ―― MaleCNS の注釈には視葉ニューロンごとに六角柱(網膜の個眼に対応する柱)が付いている。右眼の 892 柱それぞれの視葉ニューロン(柱ごとに上位 3 体)と中枢・下行のハブ 1,400 体を部分グラフ(4,076 体・150,487 辺)にし、個眼 1 つ分の解像度で刺激を入れる。動く図 1: 刺激する柱を眼の一行に沿って動かすと、応答(黄 = 刺激ノード、橙 = 右、青 = 左、尺度 = 刺激を除いた応答の最大)が視葉の中を同じ向きに動く —— 刺激した柱の座標と応答重心の相関はコネクトームで −0.92、次数保存 shuffle(同じ入力行列)で +0.01。網膜部位対応(retinotopy)が配線にあり、乱数には無い。動く図 2: 縦縞が視野を横切る像を `fly_hex_resample` で個眼に落とし、個眼の明るさをそのまま柱の刺激にして脳に入れると、応答が縞を追う(背側と側面の 2 方向)。Studio では Tools ▸ Compound eye → brain が同じ部品で対話的に動く: マウスが指す個眼の柱を刺激し、ドラッグで視点を変え、Studio の画像を眼に通し、shuffle と切り替える。柱と個眼の対応は六角座標の正規化による近似。生データも部分グラフも commit しない(手元の feather からキャッシュ、無ければ六角柱つきの合成の代替で同じ経路)。*

[![a stimulus of one eye column (+ its 6 neighbours) moves along a row of the right eye; yellow = stimulated neurons, orang](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_eye_to_brain/01_eye_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_eye_to_brain/01_eye_sweep.gif)

*↑ 測定の図 ―― a stimulus of one eye column (+ its 6 neighbours) moves along a row of the right eye; yellow = stimulated neurons, orange/blue = response (scale = response peak); the connectome answers retinotopically, the shuffle does not*

[![|x|-weighted centroid of the responding optic-lobe neurons vs the stimulated column](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_eye_to_brain/03_retinotopy_scatter_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_eye_to_brain/03_retinotopy_scatter.png)

*↑ |x|-weighted centroid of the responding optic-lobe neurons vs the stimulated column*

[![fly_hex_quantize(mode=log): a low-contrast soft bar (0.5 + 0.3, sigma 6 px) crossing the visual fiel](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_eye_to_brain/04_retinotopy_vs_bits_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_eye_to_brain/04_retinotopy_vs_bits.png)

*↑ fly_hex_quantize(mode=log): a low-contrast soft bar (0.5 + 0.3, sigma 6 px) crossing the visual field is quantized to n bits per ommatidium before ent…*

```
py -3.11 examples/poc_eye_to_brain.py
```

ソース: [examples/poc_eye_to_brain.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_eye_to_brain.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_eye_to_brain)

使用 op(ノートへ): [`fly_hex_quantize`](https://furuse.work/ops/flyvision/sample/fly_hex_quantize.html) · [`points_activity_video`](https://furuse.work/ops/conngraph/activity/points_activity_video.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html)

## No.2026.126 —— EM 連結体校正のセカンドオピニオン ―― 膜はラベルの境界にしか無いはず

[![EM 連結体校正のセカンドオピニオン ―― 膜はラベルの境界にしか無いはず](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_second_opinion/01_second_opinion_slice_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_second_opinion/01_second_opinion_slice.png)

*↑ **EM 連結体校正のセカンドオピニオン ―― 膜はラベルの境界にしか無いはず** ―― 電子顕微鏡の連続断面からニューロンを切り出した自動分割には融合(2 細胞が 1 id)と分断(1 細胞が 2 id)が残り、先行研究はどれも深層学習で候補を出す。この PoC は学習なしで同じ 2 種類を数える: 「細胞膜(暗い稜線)はラベルの境界にしか無い」を 2 通りに ―― 内部を横切る膜の弦 = 融合の疑い(閉じた輪 = ミトコンドリアは穴で除く)、膜の無い境界 = 分断の疑い。CREMI sample A(512² 断面 12 枚、生データは commit しない)の正解ラベルに人工の融合・分断を仕込み、閾値を前半 6 枚で選んで後半 6 枚で測ると、分断は AUC 1.00(TPR 1.00 / FPR 0.11)、融合は面積で揃えた負例に対して AUC 0.83(TPR 0.12 / FPR 0.01、乱数 0.53、面積だけ 0.70)。融合は弱い: 内部に膜の多い細胞が弦と同じ形で高く出る。仕込んだ融合は「大きな 2 ラベルの和」なので、面積で揃えずに測ると「大きいラベル = 怪しい」だけで 0.87 が出てしまう ―― 閾値を選ぶ断面と測る断面を分ける holdout_threshold を op にした理由。動く図は断面を z に積んだ立方体の上で疑わしい箇所(マゼンタ = 融合、シアン = 分断、明るさ = スコア)を回す。新族 emproof(7 op、numpy + scipy のみ)。*

[![suspects on the stacked cube: magenta = merge suspects (membrane chords), cyan = split suspects (membrane-free boundarie](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_second_opinion/02_suspects_on_the_cube.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_second_opinion/02_suspects_on_the_cube.gif)

*↑ 測定の図 ―― suspects on the stacked cube: magenta = merge suspects (membrane chords), cyan = split suspects (membrane-free boundaries), brightness = score, grey = all label boundaries*

[![ROC on the held-out slices; thresholds were chosen on the other half](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_second_opinion/03_holdout_roc_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_second_opinion/03_holdout_roc.png)

*↑ ROC on the held-out slices; thresholds were chosen on the other half*

[![tau = smallest threshold with train FPR <= 5 %; every number in the test columns comes from slices t](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_second_opinion/04_holdout_numbers_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_second_opinion/04_holdout_numbers.png)

*↑ tau = smallest threshold with train FPR <= 5 %; every number in the test columns comes from slices the threshold never saw*

```
py -3.11 examples/poc_em_second_opinion.py
```

ソース: [examples/poc_em_second_opinion.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_em_second_opinion.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_em_second_opinion)

使用 op(ノートへ): [`holdout_threshold`](https://furuse.work/ops/emproof/evaluate/holdout_threshold.html) · [`points_activity_video`](https://furuse.work/ops/conngraph/activity/points_activity_video.html) · [`seg_boundary_membrane_gap`](https://furuse.work/ops/emproof/suspect/seg_boundary_membrane_gap.html) · [`seg_inject_merge`](https://furuse.work/ops/emproof/inject/seg_inject_merge.html) · [`seg_inject_split`](https://furuse.work/ops/emproof/inject/seg_inject_split.html) · [`seg_label_changes`](https://furuse.work/ops/emproof/inject/seg_label_changes.html) · [`seg_membrane_chord_score`](https://furuse.work/ops/emproof/suspect/seg_membrane_chord_score.html) · [`seg_membrane_response`](https://furuse.work/ops/emproof/response/seg_membrane_response.html)

## No.2026.129 —— 動きの量子化 ―― 脳から筋へ、命令の次元はどこで落ちるか(ハエの首と RL の関節を同じ物差しで)

[![動きの量子化 ―― 脳から筋へ、命令の次元はどこで落ちるか(ハエの首と RL の関節を同じ物差しで)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_motor_bottleneck/03_activity_flow.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_motor_bottleneck/03_activity_flow.gif)

*↑ **動きの量子化 ―― 脳から筋へ、命令の次元はどこで落ちるか(ハエの首と RL の関節を同じ物差しで)** ―― 人は手を上げるとき筋肉を 1 本ずつ意識しない。脳の何万もの状態は体を動かす段階で少数の命令に畳まれているはずで、ハエではその場所が配線に見える: MaleCNS v1.0(Janelia、CC BY 4.0)で中枢脳の介在 32,164 体 → 下行ニューロン(DN)1,314 体の細い首 → 腹髄の介在 13,161 体 → 運動ニューロン(MN)708 体。conngraph に足した 4 op(graph_layer_propagate / graph_block_shuffle / states_participation_ratio / states_layer_dimension)で、脳 → DN → 腹髄 → MN の部分グラフ(4,022 体)に乱数の疎な刺激 400 通りを前向きに通し、各層の状態の実効次元(participation ratio、Gao ら 2017)を読んだ。疎な発火(kWTA 10 %)で 282 > 61 > 8.7 > 2.4 と単調に落ち、脳の状態から MN と同じ 708 列を抜いても 249 なので層の大きさのせいではない。各受け手の入力重みを保って送り手だけ混ぜた対照では MN が 21.9 残る —— 腹髄 → 筋の圧縮は配線の特異性、首(DN)の段は対照と同じ(61 vs 62)で収束そのもの。正直な内訳: 生の PR は少数の刺激が MN を強く駆動する裾の重さ(応答ノルムの最大は中央値の 17 倍)にも引かれるので、各刺激を単位ノルムに揃えた向きだけの次元も測った —— それでも実配線 25 vs 対照 54(kWTA)、線形では 7 vs 42。同じ数式を Physical AI に当てると、G1 ヒューマノイドの RL 歩行・走行の関節軌道は 1.5〜4.1(中央値 3.2)、ダンス 9.3・格闘 11.9、evis の筋活動(最大 73 本)は 5.8〜9.6。桁の比較であって同一性の主張ではない。生データと部分グラフは commit しない。*

[![effective dimension of the states each layer takes under 400 random sparse stimuli of the brain layer: real wiring vs a ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_motor_bottleneck/01_funnel_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_motor_bottleneck/01_funnel.png)

*↑ 測定の図 ―― effective dimension of the states each layer takes under 400 random sparse stimuli of the brain layer: real wiring vs a control that keeps every receiver's input weights but shuffles who sends them; the neck (DN) compresses by convergence alone, the VNC -> MN stage compresses by the specific wiring*

[![the same funnel after every stimulus response is scaled to unit norm (magnitude removed, direction k](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_motor_bottleneck/02_funnel_direction_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_motor_bottleneck/02_funnel_direction.png)

*↑ the same funnel after every stimulus response is scaled to unit norm (magnitude removed, direction kept): the real wiring still leaves fewer MN direct…*

[![the 400 stimuli projected on the first two principal components of the MN states: real wiring folds ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_motor_bottleneck/04_command_space_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_motor_bottleneck/04_command_space.png)

*↑ the 400 stimuli projected on the first two principal components of the MN states: real wiring folds them onto a few directions, the shuffled control s…*

[![participation ratio of joint-angle trajectories (G1 humanoid, RL policies and mocap retargets), next](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_motor_bottleneck/05_physical_ai_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_motor_bottleneck/05_physical_ai.png)

*↑ participation ratio of joint-angle trajectories (G1 humanoid, RL policies and mocap retargets), next to the fly's MN command dimension (2.4) under ran…*

[![every number, with the bar it had to clear](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_motor_bottleneck/06_numbers_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_motor_bottleneck/06_numbers.png)

*↑ every number, with the bar it had to clear*

```
py -3.11 examples/poc_connectome_motor_bottleneck.py
```

ソース: [examples/poc_connectome_motor_bottleneck.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_connectome_motor_bottleneck.py)

この回が作った図は全部で **6 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_connectome_motor_bottleneck)

使用 op(ノートへ): [`graph_block_shuffle`](https://furuse.work/ops/conngraph/dimension/graph_block_shuffle.html) · [`graph_layer_propagate`](https://furuse.work/ops/conngraph/dimension/graph_layer_propagate.html) · [`points_activity_video`](https://furuse.work/ops/conngraph/activity/points_activity_video.html) · [`states_layer_dimension`](https://furuse.work/ops/conngraph/dimension/states_layer_dimension.html) · [`states_participation_ratio`](https://furuse.work/ops/conngraph/dimension/states_participation_ratio.html)

## No.2026.131 —— MICrONS の脳の波 ―― 1 mm³ の視覚野で、配線は実測の応答をどこまで説明するか

[![MICrONS の脳の波 ―― 1 mm³ の視覚野で、配線は実測の応答をどこまで説明するか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_microns_brain_wave/01_brain_wave.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_microns_brain_wave/01_brain_wave.gif)

*↑ **MICrONS の脳の波 ―― 1 mm³ の視覚野で、配線は実測の応答をどこまで説明するか** ―― MICrONS(マウス V1 + 高次視覚野の約 1 mm³)は、同じニューロンについて電子顕微鏡の配線と 2 光子の活動の両方を持つ唯一級のデータ。Ding ら 2025(Nature)の公開表 —— 12,894 体の soma 位置・視覚野・自然動画への試行平均応答 120 コマと、校正済みの軸索 148 本から出る 1.69 M 対(Connected 8,128 / ADP = 軸索と樹状突起が触れているのに結合していない 287 k / Same region 1.40 M)—— を、生データも部分グラフも commit せずに読む。実測の応答をそのまま 1 mm³ の脳の波として points_activity_video で回し(各細胞が自分の上位 1/4 にいる瞬間だけ点く)、配線がその波をどこまで説明するかを 3 つの物差しで測った。(1) like-to-like の再現: 信号相関は Connected 0.071 > ADP 0.045 > Same region 0.025 で、軸索ごとに札を混ぜる置換帰無(SD 0.0018)に対して差 0.027 は 15 SD。ADP と Connected の soma 間距離は同じ(289 vs 295 µm)なので ADP が距離を揃えた対照になる。(2) 配線は近接以上を足す: 各軸索の応答と「相手の応答の平均」の相関(同じ 120 コマ上の類似度で、holdout の予測ではない)は、結合相手 0.24 > 同数の触れている相手 0.18 > 同数の同領域 0.12、軸索ごとの対で 73 % が結合相手を勝たせる。(3) 配線の波: 148 本の実測応答を conngraph の reservoir(4,096 体の部分グラフ、軸索 → 軸索の辺 269 本は落とす)に流し、1 コマ遅れの post の状態と実測の相関は 0.085、次数保存シャッフル 20 本は平均 0.048 ± 0.002(最大 0.053)で全部下、利得を 0.3 / 3 倍にしても順序は同じ。正直な内訳: 絶対値は小さい —— 校正済みの軸索 148 本から post 1 体あたり 1.8 本しか入力のない一段のグラフで、波の広がり(軸索からの平均距離 316 µm)は対照と同じ。空間の局所性は候補の集合(ADP)に既に入っていて、誰を選ぶかには入っていない。データが無ければ合成の皮質(潜在 8 本 + 近接候補からの like-to-like 結合)で同じ手順を回し、合成では順序だけを検査する。*

[![signal correlation of the in vivo responses: pairs in the same region binned by soma distance (curve), against the means](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_microns_brain_wave/02_like_to_like_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_microns_brain_wave/02_like_to_like.png)

*↑ 測定の図 ―― signal correlation of the in vivo responses: pairs in the same region binned by soma distance (curve), against the means of the connected pairs and of the ADP pairs whose axon and dendrite touch without a synapse; the per-axon permutation null of Connected - ADP has sd 0.0018*

[![each axon's response predicted from the mean response of its connected partners (y) versus the same ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_microns_brain_wave/03_wiring_vs_proximity_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_microns_brain_wave/03_wiring_vs_proximity.png)

*↑ each axon's response predicted from the mean response of its connected partners (y) versus the same number of touching-but-unconnected partners (x): a…*

[![every number, with the bar it had to clear](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_microns_brain_wave/05_numbers_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_microns_brain_wave/05_numbers.png)

*↑ every number, with the bar it had to clear*

[![the measured responses of the 148 proofread axons (pale yellow) driven through the reservoir of the 4096-node connected ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_microns_brain_wave/04_wave_on_wiring.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_microns_brain_wave/04_wave_on_wiring.gif)

*↑ 動く図 ―― the measured responses of the 148 proofread axons (pale yellow) driven through the reservoir of the 4096-node connected subgraph over all somata (grey): a target lights when the drive it receives through its real synapses is in its own top quartile; correlation of the reservoir states with the measured responses 0.085 vs 0.048 for a degree-preserving shuffle*

```
py -3.11 examples/poc_microns_brain_wave.py
```

ソース: [examples/poc_microns_brain_wave.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_microns_brain_wave.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_microns_brain_wave)

使用 op(ノートへ): [`graph_activity_spread`](https://furuse.work/ops/conngraph/activity/graph_activity_spread.html) · [`graph_degree_preserving_shuffle`](https://furuse.work/ops/conngraph/construct/graph_degree_preserving_shuffle.html) · [`graph_from_synapses`](https://furuse.work/ops/conngraph/construct/graph_from_synapses.html) · [`points_activity_video`](https://furuse.work/ops/conngraph/activity/points_activity_video.html) · [`reservoir_states`](https://furuse.work/ops/conngraph/reservoir/reservoir_states.html)

## No.2026.132 —— 枝の縄張り ―― 骨格が「どこ」かだけでなく「どの枝が近いか」を体積に配ると、枝ごとの体積と半径が測れる

[![枝の縄張り ―― 骨格が「どこ」かだけでなく「どの枝が近いか」を体積に配ると、枝ごとの体積と半径が測れる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_branch_territory/02_territory_turning.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_branch_territory/02_territory_turning.gif)

*↑ **枝の縄張り ―― 骨格が「どこ」かだけでなく「どの枝が近いか」を体積に配ると、枝ごとの体積と半径が測れる** ―― EM 連続断面から切り出したニューロンは骨格化すれば枝のグラフになるが、形態計測が要る枝ごとの体積・半径(ケーブル理論の区画パラメータ)は、体積の各 voxel が「どの枝に属するか」を決めて初めて数えられる。距離変換は最近の骨格までの距離(値)を返すが、どの骨格 voxel が最近か(向き)を捨てるので、そのままでは枝の縄張りは引けない。半径の違う 5 本の枝 + 分断された 1 片 + ごみ 6 個の合成樹状突起(真値の枝ラベルつき)で、vol_rle_components で片ごとに持って体積で選び(8 成分 → 2 を残しごみ 6 を落とす)、skeletonize_vol → skeleton_branches3d の枝 id を骨格に載せ、vol_nearest_label で空間の全 voxel に最近の枝 id を配って(ボロノイ分割)片の中に切ると、縄張りの voxel 一致率は 0.978、枝ごとの体積誤差は 2.9 % 以内。半径は vol_nearest_seed_vector(表面 → 骨格の変位)の長さ + 0.5(表面 voxel の中心は境界の半 voxel 内側)で全枝 0.24 voxel 以内 —— 骨格上の距離変換という古典(0.23 voxel 以内)と同じ精度で、こちらは表面の全 voxel に半径が付く。値だけの古典(接合点の周りを球で削って連結成分に分ける)は、球を小さくすると枝が分かれず(r=0〜4 で一致率 0.63〜0.65)、大きくすると体積を捨てる(r=6 で 0.78、22 % が未割当)—— 向きが要る証拠。正直な内訳: 骨格の枝は接合点で切れるので幹は 3 本の枝 id に分かれ(9 本 → 真値 6 本、重なりの多数決で対応)、半径の +0.5 は離散化の既知の偏りを明示的に足したもの。*

[![z projection of the synthetic dendrite: every voxel gets the branch whose skeleton is nearest, so the branch volumes can](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_branch_territory/01_territories_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_branch_territory/01_territories.png)

*↑ 測定の図 ―― z projection of the synthetic dendrite: every voxel gets the branch whose skeleton is nearest, so the branch volumes can be counted; cutting balls around the junctions instead either fails to separate the branches or throws volume away*

[![both readings recover the radius of every branch to within half a voxel (the surface voxel centre si](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_branch_territory/03_radius_recovery_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_branch_territory/03_radius_recovery.png)

*↑ both readings recover the radius of every branch to within half a voxel (the surface voxel centre sits half a voxel inside the boundary, hence the +0.…*

[![volume per branch comes from the territory; the junction-cut rows show that no ball radius separates](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_branch_territory/04_branch_numbers_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_branch_territory/04_branch_numbers.png)

*↑ volume per branch comes from the territory; the junction-cut rows show that no ball radius separates the branches without throwing volume away*

```
py -3.11 examples/poc_em_branch_territory.py
```

ソース: [examples/poc_em_branch_territory.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_em_branch_territory.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_em_branch_territory)

使用 op(ノートへ): [`identity`](https://furuse.work/ops/2d/misc/identity.html) · [`points_activity_video`](https://furuse.work/ops/conngraph/activity/points_activity_video.html) · [`skeleton`](https://furuse.work/ops/2d/region/skeleton.html) · [`skeleton_branches3d`](https://furuse.work/ops/3d/medial/skeleton_branches3d.html) · [`skeleton_graph3d`](https://furuse.work/ops/3d/medial/skeleton_graph3d.html) · [`skeletonize_vol`](https://furuse.work/ops/3d/medial/skeletonize_vol.html) · [`vol_distance_transform`](https://furuse.work/ops/3d/medial/vol_distance_transform.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_nearest_label`](https://furuse.work/ops/3d/medial/vol_nearest_label.html) · [`vol_nearest_seed_vector`](https://furuse.work/ops/3d/medial/vol_nearest_seed_vector.html) · [`vol_rle_components`](https://furuse.work/ops/3d/rle_region/vol_rle_components.html) · [`vol_rle_decode`](https://furuse.work/ops/3d/rle_region/vol_rle_decode.html) · [`vol_rle_volume`](https://furuse.work/ops/3d/rle_region/vol_rle_volume.html)

## No.2026.153 —— 線虫の配線は左右対称か ―― L/R 入れ替えの Jaccard を閉形式と次数保存ヌルで挟む

[![線虫の配線は左右対称か ―― L/R 入れ替えの Jaccard を閉形式と次数保存ヌルで挟む](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_lr_symmetry/01_lr_jaccard_closed_form_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_lr_symmetry/01_lr_jaccard_closed_form.png)

*↑ **線虫の配線は左右対称か ―― L/R 入れ替えの Jaccard を閉形式と次数保存ヌルで挟む** ―― C. elegans 雌雄同体の化学シナプス配線(Cook 2019、n=300、|E|=3,669、左右対 98 組)で、左右の対をすべて入れ替えた配線と元の配線の辺集合の重なり(Jaccard)を測った図。実測 0.473 は、完全対称なら 1.000、同じ次数列で辺を入れ替えた次数保存ヌルなら 0.080 ± 0.002(z 159)で、そのどちらからも離れた中間にある。真値は集合の数え上げの閉形式 ―― 鏡映な合成配線(片側 m 辺)の右半分から k 辺を移すと Jaccard = (m−k)/(m+k) で、k=0..120 の 16 段で分子・分母の整数まで op と一致する。対ごとの非対称率は 0.7 から 0.15 へなだらかに下がり、予想した「少数の対への集中」は実測では一様の 2 倍程度(上位 10 組で 20 %、一様なら 10 %)。上位は HSN 60 % / PVN 57 % / RMG 53 % / URX 48 %。データは同梱せず、無ければ合成の鏡映配線(Jaccard 0.500 = (120−40)/(120+40))で回る。*

[![C. elegans 雌雄同体・化学シナプス(Cook 2019)。98 組のうち上位 10 組が非対称辺の 20 %(一様なら 10 %)。水平線は全体の Jaccard からの期待率 1 − J。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_lr_symmetry/02_lr_pair_asymmetry_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_lr_symmetry/02_lr_pair_asymmetry.png)

*↑ 測定の図 ―― C. elegans 雌雄同体・化学シナプス(Cook 2019)。98 組のうち上位 10 組が非対称辺の 20 %(一様なら 10 %)。水平線は全体の Jaccard からの期待率 1 − J。*

```
py -3.11 examples/poc_connectome_lr_symmetry.py
```

ソース: [examples/poc_connectome_lr_symmetry.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_connectome_lr_symmetry.py)

この回が作った図は全部で **2 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_connectome_lr_symmetry)

使用 op(ノートへ): [`graph_degree_summary`](https://furuse.work/ops/graph/degree/graph_degree_summary.html) · [`graph_swap_symmetry`](https://furuse.work/ops/graph/symmetry/graph_swap_symmetry.html)

## No.2026.156 —— 同じ線虫の配線は、個体が違うとどこまで同じか ―― 8 匹の発生系列で「全員に在る結合」を数える

[![同じ線虫の配線は、個体が違うとどこまで同じか ―― 8 匹の発生系列で「全員に在る結合」を数える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_across_worms/01_occupancy_matrix_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_across_worms/01_occupancy_matrix.png)

*↑ **同じ線虫の配線は、個体が違うとどこまで同じか ―― 8 匹の発生系列で「全員に在る結合」を数える** ―― 遺伝的に同一な C. elegans 8 匹(Witvliet 2021、生直後〜成虫)の化学シナプス配線を、8 匹全員に在る 183 細胞の上で重ね、各結合が何匹に在るかを graph_edge_consensus で数えた図。8 匹全員に在る結合は 442 本で、各個体の入次数・出次数を保ったまま独立に組み替えた次数保存ヌルでは 20 標本の最大でも 0 本。この核は和集合 2,977 本の 15 % の結合で、8 匹合計のシナプスの 57 % を担う。一方、2 匹どうしの Jaccard は推定齢の差とともに下がり(隣り合う段階の平均 0.51、生直後と成虫で 0.33〜0.34)、同齢の成虫 2 匹どうしでも 0.53 と隣り合う発生段階と同程度にとどまる。発生順に見ると、途中から現れて最後まで残る結合が 701 本、途中で消える結合は 55 本。真値は合成系列の閉形式 ―― 核 C 本を全員に、固有 u 本を個体ごとに重ならず置くと h[K]=C・h[1]=K·u・どの 2 匹の Jaccard も C/(C+2u)・stable/added/lost/flicker = C/u/u/(K−2)u で、整数まで op と一致する。公表値との照合: 論文は 7 匹以上に在る結合を stable とし成虫の結合の約 43 % とするが、細胞単位で素朴に数えると 34.5 %。著者の結合ごとの分類表と照合すると、論文は左右の対でまとめた結合が 7 匹以上に在れば対の細胞単位の結合すべてに stable の札を付けており(48.9 %)、それだけで論文の stable 792 本のうち 789 本(99.6 %)を再現する。variable・dynamic を先に除くと 45.4 %。データは同梱せず(nemanode.org のデータには明示のライセンスが無い)、無ければ合成の系列で回る。*

[![生まれた直後から成虫まで 8 匹の配線を順に。色は全体での出現回数なので、早い段階から在る結合ほど明るい。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_across_worms/02_wiring_across_development.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_across_worms/02_wiring_across_development.gif)

*↑ 測定の図 ―― 生まれた直後から成虫まで 8 匹の配線を順に。色は全体での出現回数なので、早い段階から在る結合ほど明るい。*

[![ヌルは各個体の入次数・出次数を保ったまま独立に組み替えた配線。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_across_worms/03_occupancy_vs_null_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_across_worms/03_occupancy_vs_null.png)

*↑ ヌルは各個体の入次数・出次数を保ったまま独立に組み替えた配線。*

[![横軸 0 の点が同齢の成虫 2 匹(Jaccard 0.53)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_across_worms/04_jaccard_vs_age_gap_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_across_worms/04_jaccard_vs_age_gap.png)

*↑ 横軸 0 の点が同齢の成虫 2 匹(Jaccard 0.53)。*

[![8 匹全員に在る結合は結合数の 15 %、シナプスの 57 %。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_across_worms/05_synapse_share_by_occupancy_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_across_worms/05_synapse_share_by_occupancy.png)

*↑ 8 匹全員に在る結合は結合数の 15 %、シナプスの 57 %。*

[![論文は左右の対でまとめた結合が 7 匹以上に在れば、その対の細胞単位の結合すべてに stable の札を付ける(②)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_across_worms/06_paper_comparison_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_across_worms/06_paper_comparison.png)

*↑ 論文は左右の対でまとめた結合が 7 匹以上に在れば、その対の細胞単位の結合すべてに stable の札を付ける(②)。*

```
py -3.11 examples/poc_connectome_across_worms.py
```

ソース: [examples/poc_connectome_across_worms.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_connectome_across_worms.py)

この回が作った図は全部で **6 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_connectome_across_worms)

使用 op(ノートへ): [`graph_edge_consensus`](https://furuse.work/ops/graph/population/graph_edge_consensus.html) · [`intersection`](https://furuse.work/ops/2d/nary/intersection.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html)

## No.2026.157 —— 40 年前の手作業の配線図と、今の成虫の配線はどれだけ重なるか ―― 時代の差を個体の差と並べる

[![40 年前の手作業の配線図と、今の成虫の配線はどれだけ重なるか ―― 時代の差を個体の差と並べる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_across_decades/01_jaccard_across_decades_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_across_decades/01_jaccard_across_decades.png)

*↑ **40 年前の手作業の配線図と、今の成虫の配線はどれだけ重なるか ―― 時代の差を個体の差と並べる** ―― C. elegans の配線図の原点 White 1986(電子顕微鏡写真の手作業トレース、成虫 N2U)を、Witvliet 2021 の成虫 2 匹と共通の 215 細胞の上でgraph_edge_consensus で重ねた図。重なり(Jaccard)は同じ手法の成虫 2 匹で 0.508、1986 の N2U と 2021 の 2 匹で 0.431・0.442 ―― 時代と手法の差は 0.07 で、個体差 1 − 0.508 = 0.49 に比べて小さい。3 匹すべてに在る結合は 1,015 本で、各個体を次数保存で組み替えたヌルの平均 28 本の 36 倍。2021 の 2 匹ともに在るのに 1986 に無い結合 451 本は平均 2.0 シナプスの細い結合で、3 匹とも在る結合(平均 5.7)と分布がはっきり分かれる。★検査が見つけたもの: 2 匹の平均シナプス数を丸めて階級に入れると numpy の偶数丸め(2.5 → 2)で奇数・偶数のギザギザが出た —— 合計(整数)のまま数えて消した。正直な内訳: nemanode 上の N2U は 2020 年に Zhen lab が筋肉を補った版で、時代の差には再注釈の差も含まれる。JSH は L4 幼虫なので成虫の比較に入れない。データは同梱せず、無ければ合成で回る。*

[![3 匹すべてに在る結合 1015 本、ヌルの平均 28.2 本。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_across_decades/02_occupancy_vs_null_decades_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_across_decades/02_occupancy_vs_null_decades.png)

*↑ 測定の図 ―― 3 匹すべてに在る結合 1015 本、ヌルの平均 28.2 本。*

[![2021 の 2 匹ともに在るのに 1986 に無い結合は平均 2.01 シナプス、3 匹とも在る結合は 5.73。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_across_decades/03_what_1986_missed_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_across_decades/03_what_1986_missed.png)

*↑ 2021 の 2 匹ともに在るのに 1986 に無い結合は平均 2.01 シナプス、3 匹とも在る結合は 5.73。*

```
py -3.11 examples/poc_connectome_across_decades.py
```

ソース: [examples/poc_connectome_across_decades.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_connectome_across_decades.py)

この回が作った図は全部で **3 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_connectome_across_decades)

使用 op(ノートへ): [`graph_edge_consensus`](https://furuse.work/ops/graph/population/graph_edge_consensus.html) · [`intersection`](https://furuse.work/ops/2d/nary/intersection.html)

## No.2026.158 —— 線虫の神経突起は、生まれてから何倍に伸びるか ―― 8 匹の骨格を op で測り、論文の値と並べる

[![線虫の神経突起は、生まれてから何倍に伸びるか ―― 8 匹の骨格を op で測り、論文の値と並べる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_worm_neurites_grow/01_neurite_length_growth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_worm_neurites_grow/01_neurite_length_growth.png)

*↑ **線虫の神経突起は、生まれてから何倍に伸びるか ―― 8 匹の骨格を op で測り、論文の値と並べる** ―― Witvliet 2021 の C. elegans 8 匹(生直後〜成虫)の神経突起の骨格を SWC の木に直し、tree_from_swc / tree_morphometry / tree_sholl で測った図。木は 1,727 本(途中で途切れて断片に分かれた骨格 61 個は断片ごとに測って合算)で、構造の約束(根 1 つ・親 id < 子 id・節点 = 辺 + 1)と Sholl の閉形式(曲線の下の面積 = Σ|d_子 − d_親|)をすべて通過。第 2 実装: 断片が 1 つの骨格 1,586 本で、op の最長経路が著者の節点ごとの dist_to_root の最大と相対 1.75e-9 で一致。★検査が見つけたもの: 著者の length は線分の長さの合計ではなく(中央値 0.89 倍、1,586 本中 1,360 本が不一致)門にならない。dist_to_root には座標の無い節点も混ざる(1 匹目で 196 本中 54 本)ので、座標のある節点だけで比べる。SWC に座標を小数 3 桁で書くと丸めで 1.9e-6 ずれた。総長は生直後 2,806 µm → 成虫 12,038 µm で 4.29 倍(8 匹に共通の 195 本だけなら 3.86 倍)、論文は約 5 倍。著者の length を足しても 3.95 倍で、5 倍そのものはこのファイルの単純な合計からは出ない(同じ桁までは合う)。L3 の個体の総長が L2 とほぼ同じなのは標本の縮みで、著者は 1.1 倍に補正している。データは同梱しない。*

[![同じ名前のニューロン AVAL を 4 つの発生段階で。3-D の Sholl なので回転に依らない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_worm_neurites_grow/02_sholl_through_development_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_worm_neurites_grow/02_sholl_through_development.png)

*↑ 測定の図 ―― 同じ名前のニューロン AVAL を 4 つの発生段階で。3-D の Sholl なので回転に依らない。*

```
py -3.11 examples/poc_worm_neurites_grow.py
```

ソース: [examples/poc_worm_neurites_grow.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_worm_neurites_grow.py)

この回が作った図は全部で **2 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_worm_neurites_grow)

使用 op(ノートへ): [`intersection`](https://furuse.work/ops/2d/nary/intersection.html) · [`tree_from_swc`](https://furuse.work/ops/graph/tree/tree_from_swc.html) · [`tree_morphometry`](https://furuse.work/ops/graph/tree/tree_morphometry.html) · [`tree_sholl`](https://furuse.work/ops/graph/tree/tree_sholl.html)

## No.2026.159 —— 電子顕微鏡の神経の切り出しを採点する ―― 分けすぎと、まとめすぎを別々の数字にする

[![電子顕微鏡の神経の切り出しを採点する ―― 分けすぎと、まとめすぎを別々の数字にする](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_split_merge_score/01_split_vs_merge_by_threshold_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_split_merge_score/01_split_vs_merge_by_threshold.png)

*↑ **電子顕微鏡の神経の切り出しを採点する ―― 分けすぎと、まとめすぎを別々の数字にする** ―― コネクトームを作る自動の切り出しの誤りは、1 本の神経を 2 つに切る分断と、別々の 2 本をくっつける融合の 2 種類。seg_variation_of_information は VOI を split(分けすぎ)と merge(まとめすぎ)に分けて返す。CREMI sample A(z=40、512²)の正解に、既存の seg_inject_split / seg_inject_merge で誤りを 1 つずつ仕込むと、分断 4 件は split だけ、融合 4 件は merge だけが閉形式 (m/N)·H2(m1/m) ビットどおり上がった(誤差 < 1e-12、実データのどの割り方でも厳密)。古典の切り出し(膜応答 → しきい値 → 連結成分 → 膜の画素を最寄りの細胞へ)は、しきい値 60 % で split 1.14 / merge 0.18(分けすぎ)、85 % で split 0.05 / merge 5.02(まとめすぎ)と入れ替わり、交点の手前の 65 % で VOI が最小(1.263)。★検査が見つけたもの: 膜の画素を背景(ラベル 0)のまま残すと背景全体が 1 つの巨大な領域として数えられ、70 % で merge 2.07(割り振ると 0.85)と 2.4 倍に水増しされて、どのしきい値でも「まとめすぎ」に見えた。第 2 実装の scikit-image では adapted Rand error が一致したが、その precision は正解側の対で割られていて、docstring の説明と名前が入れ替わっていた。生データは同梱しない。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_split_merge_score/02_truth_vs_classic_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_split_merge_score/02_truth_vs_classic.png)

*↑ 測定の図*

```
py -3.11 examples/poc_em_split_merge_score.py
```

ソース: [examples/poc_em_split_merge_score.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_em_split_merge_score.py)

この回が作った図は全部で **2 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_em_split_merge_score)

使用 op(ノートへ): [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`seg_inject_merge`](https://furuse.work/ops/emproof/inject/seg_inject_merge.html) · [`seg_inject_split`](https://furuse.work/ops/emproof/inject/seg_inject_split.html) · [`seg_label_changes`](https://furuse.work/ops/emproof/inject/seg_label_changes.html) · [`seg_membrane_response`](https://furuse.work/ops/emproof/response/seg_membrane_response.html) · [`seg_rand`](https://furuse.work/ops/emproof/score/seg_rand.html) · [`seg_variation_of_information`](https://furuse.work/ops/emproof/score/seg_variation_of_information.html)

## No.2026.160 —— 切り出しの誤りは、配線図のどこを壊すか ―― 画素の採点は分断を重く、融合を軽く数える

[![切り出しの誤りは、配線図のどこを壊すか ―― 画素の採点は分断を重く、融合を軽く数える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_wiring_errors/01_proofreading_order_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_wiring_errors/01_proofreading_order.png)

*↑ **切り出しの誤りは、配線図のどこを壊すか ―― 画素の採点は分断を重く、融合を軽く数える** ―― コネクトームは切り出した神経の上にシナプスの注釈(前の点・後の点)を落として読むので、切り出しの誤りは配線図の誤りに化ける ―― ただし全部ではない。seg_wiring_variation は画素の VOI をシナプスの端 2n 点だけで取り直す。この構成は Plaza ら 2014(Focused proofreading)の synapse VI と同じで、ここでのものは numpy だけの実装・接続ごとの水準・誤りを仕込む実験・校正の順番の比較。CREMI sample A(z 125 枚 × xy 625²、シナプス 115 個・接続 107 本)の正解に、シナプスのある神経 54 本それぞれ「x の中央で半分に切る」「いちばん広く接する隣と貼る」誤りを 1 件ずつ仕込むと、端の VOI は全 108 件で閉形式 (s/2n)·H2(s1/s) と一致した(最大誤差 1.4e-17)。分断の 23 / 54 件は配線を 1 ビットも変えない(切った面の片側に端が無い)。画素 1 ビットあたりの配線の損傷(中央値)は融合 1.30 / 分断 0.58、画素と端の順位相関は 0.60。画素の VOI の大きい順に上位 20 件を直すと配線の損傷は 41 % 消え、でたらめ(19 %)よりずっと効くが、配線の順(49 %)には届かない。★検査が見つけたもの: 条件つきエントロピーを H(a,b) − H(a) の差で出すと、名前の付け替えだけの比較に 8.9e-16 の屑が残り「同一なら 0」の門に落ちた —— 直接の和 −Σ p log2(n_ij / n_i) に変えて厳密に 0。接続ごとに束ねた VOI だけでは、シナプス 1 個の接続が切られても 0 のまま(107 本の大半がそれ)なので、端の水準を主にした。同じ誤りを NRI(Reilly 2018、端の対の F 値。新しい op seg_synapse_nri、端の上の 1 − adapted Rand error と厳密に一致)でも採点し、端の VOI が 0 の誤りは NRI の損失も 0 であることを門にした。NRI の損失と端の VOI の順位相関は 1.00、画素の VOI とは 0.59。比 1.30 / 0.58 の中身: 誤り 1 件の 配線 / 画素 は恒等的に 密度 × 偏り(全 108 件で門)。融合は偏り ≈ 1 で比は密度、分断の割引は端の個数の少なさ(中央値 3 個、一様に散っていても 2 項分布で H2 の期待 0.62、実測 0.53)が主因。新 op seg_wiring_exposure は端の個数だけからの予言(上限 s/2n、2 項分布の期待値)を神経ごとに返す(分断 54 件の合計: 実測 0.677 / 予言 0.788 / 上限 1.000 ビット)。生データは同梱しない。*

[![1 点 = 仕込んだ誤り 1 件。順位相関 0.60。分断の 23 / 54 件は配線を 1 ビットも変えない(横軸の上に並ぶ)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_wiring_errors/02_pixel_vs_wiring_cost_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_wiring_errors/02_pixel_vs_wiring_cost.png)

*↑ 測定の図 ―― 1 点 = 仕込んだ誤り 1 件。順位相関 0.60。分断の 23 / 54 件は配線を 1 ビットも変えない(横軸の上に並ぶ)。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_wiring_errors/03_two_cuts_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_wiring_errors/03_two_cuts.png)

*↑ この回の図*

[![CREMI sample A(z 125 枚 × xy 625² @ 0,625)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_wiring_errors/04_count_only_prediction_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_em_wiring_errors/04_count_only_prediction.png)

*↑ CREMI sample A(z 125 枚 × xy 625² @ 0,625)。*

```
py -3.11 examples/poc_em_wiring_errors.py
```

ソース: [examples/poc_em_wiring_errors.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_em_wiring_errors.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_em_wiring_errors)

使用 op(ノートへ): [`seg_synapse_nri`](https://furuse.work/ops/emproof/wiring/seg_synapse_nri.html) · [`seg_synapse_partners`](https://furuse.work/ops/emproof/wiring/seg_synapse_partners.html) · [`seg_variation_of_information`](https://furuse.work/ops/emproof/score/seg_variation_of_information.html) · [`seg_wiring_exposure`](https://furuse.work/ops/emproof/wiring/seg_wiring_exposure.html) · [`seg_wiring_variation`](https://furuse.work/ops/emproof/wiring/seg_wiring_variation.html)

## No.2026.161 —— シナプスは神経突起に比例して増えるか ―― 8 匹の線虫で、形の成長と配線の成長を細胞ごとに並べる

[![シナプスは神経突起に比例して増えるか ―― 8 匹の線虫で、形の成長と配線の成長を細胞ごとに並べる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_worm_synapses_vs_neurites/01_density_by_stage_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_worm_synapses_vs_neurites/01_density_by_stage.png)

*↑ **シナプスは神経突起に比例して増えるか ―― 8 匹の線虫で、形の成長と配線の成長を細胞ごとに並べる** ―― Witvliet 2021 の 8 匹は、同じ個体に骨格(形)と配線(シナプス)の両方がある。tree op で測った神経突起の総長と化学シナプスの総数から、密度は L1 生直後の 0.462 /µm から L1 16 時間の 0.611 へ ×1.32 上がり、L1 以後の揺れ(最大 / 最小)は 1.14 ――論文の「L1 を除けば密度は保たれる」と矛盾しない(門は「L1 の上がり > その後の揺れ」で、数字を当てはめない)。細胞ごとに並べると、1 匹目と 8 匹目の両方に骨格とシナプスがある 178 細胞で、突起の伸び(中央値 ×3.7)とシナプスの増え(中央値 ×6.0)の順位相関は 0.23(細胞をシャッフルした零分布の 97.5 % 点 0.17)。0 ではないが、形だけでは決まらない。密度が上がった細胞は 82 %。新しい op graph_strength_growth で 1 匹目と 8 匹目の行列を比べると、新しいシナプス 6,674 個のうち既存の接続を太らせたのが 3,232、新しい接続が 3,627、消えた −159、細った −26(4 つの和は厳密に 6,674)。生まれた時の相手の数と増分の順位相関は入力 0.58 / 出力 0.51、上位 1 割のハブの取り分は入力 34 % → 28 %、出力 24 % → 20 % と下がる ―― 「ハブは入力を不釣り合いに増やす」は、この定義では出ない(論文の量とは定義が違うので矛盾とは言わない)。生データは同梱しない。*

[![1 点 = 細胞 178 個。順位相関 0.23(零分布 97.5 % 点 0.17)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_worm_synapses_vs_neurites/02_cell_growth_scatter_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_worm_synapses_vs_neurites/02_cell_growth_scatter.png)

*↑ 測定の図 ―― 1 点 = 細胞 178 個。順位相関 0.23(零分布 97.5 % 点 0.17)。*

[![順位相関 入力 0.58 / 出力 0.51。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_worm_synapses_vs_neurites/03_gain_vs_degree_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_worm_synapses_vs_neurites/03_gain_vs_degree.png)

*↑ 順位相関 入力 0.58 / 出力 0.51。*

```
py -3.11 examples/poc_worm_synapses_vs_neurites.py
```

ソース: [examples/poc_worm_synapses_vs_neurites.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_worm_synapses_vs_neurites.py)

この回が作った図は全部で **3 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_worm_synapses_vs_neurites)

使用 op(ノートへ): [`graph_strength_growth`](https://furuse.work/ops/graph/population/graph_strength_growth.html) · [`tree_from_swc`](https://furuse.work/ops/graph/tree/tree_from_swc.html) · [`tree_morphometry`](https://furuse.work/ops/graph/tree/tree_morphometry.html)

## No.2026.162 —— 走行長は小さな融合を許さない ―― 同じ誤りを、ERL と VOI は違う重さで数える

[![走行長は小さな融合を許さない ―― 同じ誤りを、ERL と VOI は違う重さで数える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_skeleton_run_length_vs_voi/01_merge_size_erl_vs_voi_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_skeleton_run_length_vs_voi/01_merge_size_erl_vs_voi.png)

*↑ **走行長は小さな融合を許さない ―― 同じ誤りを、ERL と VOI は違う重さで数える** ―― 自動切り出しの採点には、分割表から出す VOI(split / merge)と、正解の骨格の上を「同じ物体のまま何 µm 走れるか」で測る ERL(expected run length、Januszewski 2018)がある。新しい op tree_run_length は、骨格の節点に候補のラベルを塗った走行を数え、融合した物体の走行を 0 とみなす。Witvliet 2021 の骨格 1,713 本(12 節点以上)を正解に、候補のラベル付けを 1 つずつ仕込んだ(候補は合成で、切り出し器の出力ではない)。分断 1 つの ERL は閉形式 (A² + (L − A − |e|)²)/L(A = 切った側の部分木のケーブル、第 2 の走査で数える)と全 1,713 本で一致(相対 4e-15)、VOI の split は (m/N)·H2 と一致(3.5e-16)。分岐の無い骨格 100 本では、真ん中で切ると ERL は 0.48 L、端(1 割)で切ると 0.80 L。骨格 a の遠い側 q を骨格 b の物体に貼る融合(856 組)では、VOI の merge は q = 5 % の 0.142 ビットから 50 % の 0.662 へ単調に増えるが、貼られた側 b の ERL は q に依らず 0(損失 1.000)、a の損失は分断と同じ 1 − (1 − q)²。分岐の無い骨格 65 本をケーブルの上で一様に 3 点で切ると、走行の割合は Dirichlet(1,…,1) に従い、平均 Σl²/L'² ÷ 2/(m+2) = 1.023。★検査が見つけたもの: 最初の版は「貼った側 a の損失が q に依らず一定」と主張していた —— 誤り。ERL が 0 にするのは融合した物体の走行で、a の残りは無傷のまま残る。一定の損失を受けるのはその物体に丸ごと覆われる b。また、切る位置を節点番号の上で一様に取ると期待値との比が 0.945 にずれた —— 辺の長さが揃っていないので、ケーブルの上で一様に取る。生データは同梱しない。*

[![1 点 = 骨格 1 本。真ん中で切ると ERL は L の約 1/2、端で切ると約 0.8 L。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_skeleton_run_length_vs_voi/02_cut_position_erl_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_skeleton_run_length_vs_voi/02_cut_position_erl.png)

*↑ 測定の図 ―― 1 点 = 骨格 1 本。真ん中で切ると ERL は L の約 1/2、端で切ると約 0.8 L。*

```
py -3.11 examples/poc_skeleton_run_length_vs_voi.py
```

ソース: [examples/poc_skeleton_run_length_vs_voi.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_skeleton_run_length_vs_voi.py)

この回が作った図は全部で **2 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_skeleton_run_length_vs_voi)

使用 op(ノートへ): [`seg_variation_of_information`](https://furuse.work/ops/emproof/score/seg_variation_of_information.html) · [`tree_from_swc`](https://furuse.work/ops/graph/tree/tree_from_swc.html) · [`tree_run_length`](https://furuse.work/ops/graph/tree/tree_run_length.html)

## No.2026.163 —— 粘菌の管は迷路を解く ―― 太る・細るだけの力学が最短路に収束することを、定理と Dijkstra で挟む

[![粘菌の管は迷路を解く ―― 太る・細るだけの力学が最短路に収束することを、定理と Dijkstra で挟む](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_physarum_maze/01_maze_tubes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_physarum_maze/01_maze_tubes.png)

*↑ **粘菌の管は迷路を解く ―― 太る・細るだけの力学が最短路に収束することを、定理と Dijkstra で挟む** ―― 粘菌 Physarum は、管を流れる流量で管を太らせ・細らせるだけで迷路の最短路を残す(Tero 2010)。その力学(キルヒホッフで圧力を解き、dD/dt = |Q| − D)は、最短路が一意なら導電度がその指示関数に収束することが証明されている(Bonifaci 2012)。新しい op 2 本 graph_physarum_path(重み付きグラフ)と physarum_route(コスト画像、隣の画素を長さ (c_u+c_v)/2 の管で結ぶ)で回し、真値は Dijkstra(scipy)と route_through_array(skimage)。15×15 の格子 5 通り・21×21 の完全迷路・32×32 の地形の全部で粘菌の道は最小コスト経路と一致(差 < 1e-9)。格子は 600 反復の時点で 5/5 が一致(afterman の PoC は 4/5)、3,000 反復で指示関数(最短路の管 > 0.99、他 < 0.01)に収束したのは 3/5 で、打ち切りの 2 つは「2 番目に短い道との差」(最短路の辺を1 本ずつ外した Dijkstra の最小 = 厳密)が 0.009・0.032 と小さく、拮抗する 2 本目が残る —— 収束の速さはこの差が決める。Lyapunov 関数 V = Σ L·D は迷路で 227,280 → 133.60(最短路 133.59)へ 23 区間で一度も増えず。単位流量の長さ Σ|Q|L ≥ 最短路の不等式は全件で厳密に成立。一様なコストのように同じ長さの道が何本もある(タイ)場合は 1 本に収束しないので op は拒否する。*

[![同じ迷路、24 コマ。行き止まりから順に細り、最後に最短路だけが残る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_physarum_maze/02_maze_tubes_gif.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_physarum_maze/02_maze_tubes_gif.gif)

*↑ 測定の図 ―― 同じ迷路、24 コマ。行き止まりから順に細り、最後に最短路だけが残る。*

[![32×32。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_physarum_maze/03_terrain_route_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_physarum_maze/03_terrain_route.png)

*↑ 32×32。*

[![15×15 の格子、辺長 U(0.5, 1.5)、左上 → 右下。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_physarum_maze/04_lattice_tubes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_physarum_maze/04_lattice_tubes.png)

*↑ 15×15 の格子、辺長 U(0.5, 1.5)、左上 → 右下。*

```
py -3.11 examples/poc_physarum_maze.py
```

ソース: [examples/poc_physarum_maze.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_physarum_maze.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_physarum_maze)

使用 op(ノートへ): [`graph_physarum_path`](https://furuse.work/ops/graph/flow/graph_physarum_path.html) · [`physarum_route`](https://furuse.work/ops/graph/flow/physarum_route.html)

## No.2026.165 —— 粘菌は最適輸送を解く ―― 源と吸込を質量の分布にすると、同じ管の力学が Earth Mover 距離へ収束する

[![粘菌は最適輸送を解く ―― 源と吸込を質量の分布にすると、同じ管の力学が Earth Mover 距離へ収束する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_physarum_transport/01_transport_tubes_gif.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_physarum_transport/01_transport_tubes_gif.gif)

*↑ **粘菌は最適輸送を解く ―― 源と吸込を質量の分布にすると、同じ管の力学が Earth Mover 距離へ収束する** ―― 迷路の PoC は源 1 つ・吸込 1 つだった。源と吸込を供給ベクトル(Σ = 0)にすると、同じ力学(キルヒホッフで圧力、Q = D (p_u − p_v)/L、dD/dt = |Q| − D)がグラフ上の L1 最適輸送(Beckmann 問題 = 1-Wasserstein 距離)の解へ収束する(Bonifaci 2017、Facca–Karrenbauer–Kolev–Mehlhorn 2020、連続体は Facca–Cardin–Putti 2018)。新しい op 2 本 graph_physarum_transport(重み付きグラフ + 供給)と physarum_transport_image(質量画像 2 枚、画素を長さ 1 の管で結ぶ = マンハッタン距離の EMD)は、費用 Σ L|Q|(上界)と一緒に Kantorovich–Rubinstein の下界 ―― 圧力を 1-Lipschitz にした McShane 包絡 φ の bᵀφ ―― を返す。真の距離は必ずその間に在るので、隙間が「最適から幾ら離れているか」の証明書になり、隙間が閉じたら止まる。真値 10 件と照合: 乱数の木 5 本では閉形式 Σ L_e|部分木の供給| と相対 1.7e-15 で一致(木では流れが一意で 37〜38 反復)、不等間隔の 1 次元格子では既存 op wasserstein_1d と 0.316477 で一致、12 点 ↔ 12 点の完全 2 部グラフでは Hungarian 法の最小割当 0.163242 に対し 0.163244(459 反復)で、生き残った管の集合が最適割当そのもの(割当の管 ≥ 1.00、それ以外 ≤ 0.001)、6×6 格子の乱数質量では LP(HiGHS)と 0.591849 で一致、円盤を (5, 8) 画素ずらした画像との EMD は定理どおり 13.000086 = |dr| + |dc|、源 1・吸込 1 では下界が Dijkstra の距離 9.367260049 と厳密に一致(圧力の包絡 = 最短路のポテンシャル)。距離の公理(対称・長さと質量に線形・三角不等式)も成立。円盤 → 2 円盤(24×24)では EMD 12.0001 に 183 反復で来て、管が張られていく 36 コマの動く図を撮った。合計 9.1 秒。正直に: 粘菌は Hungarian 法やネットワーク単体法より速くはない。売りは局所則だけで解に来ること、バッチで完全並列なこと、そして証明書を自前で返すこと。*

[![EMD 12.0001(画素単位)。粘菌の費用 12.0001、Kantorovich–Rubinstein の下界 12.0000。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_physarum_transport/02_transport_tubes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_physarum_transport/02_transport_tubes.png)

*↑ 測定の図 ―― EMD 12.0001(画素単位)。粘菌の費用 12.0001、Kantorovich–Rubinstein の下界 12.0000。*

[![完全 2 部グラフ 144 本、ユークリッド長。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_physarum_transport/03_assignment_tubes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_physarum_transport/03_assignment_tubes.png)

*↑ 完全 2 部グラフ 144 本、ユークリッド長。*

[![円盤 → 2 円盤。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_physarum_transport/04_sandwich_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_physarum_transport/04_sandwich.png)

*↑ 円盤 → 2 円盤。*

[![木 seed 0 16.34; 木 seed 1 13.71; 木 seed 2 14.19; 木 seed 3 15.71; 木 seed 4 14.44; 1 次元 0.3165; 割当 12×1](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_physarum_transport/05_five_truths_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_physarum_transport/05_five_truths.png)

*↑ 木 seed 0 16.34; 木 seed 1 13.71; 木 seed 2 14.19; 木 seed 3 15.71; 木 seed 4 14.44; 1 次元 0.3165; 割当 12×12 0.1632; 格子 6×6 LP 0.5918; 平行移動 (5, 8) 13; 単一対 7×…*

```
py -3.11 examples/poc_physarum_transport.py
```

ソース: [examples/poc_physarum_transport.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_physarum_transport.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_physarum_transport)

使用 op(ノートへ): [`graph_physarum_transport`](https://furuse.work/ops/graph/flow/graph_physarum_transport.html) · [`physarum_transport_image`](https://furuse.work/ops/graph/flow/physarum_transport_image.html) · [`wasserstein_1d`](https://furuse.work/ops/colortransport/transport/wasserstein_1d.html)

## No.2026.154 —— 本物の木で骨格計測を採点する ―― NeuroMorpho の SWC を真値に、投影が何を壊すかを測る

[![本物の木で骨格計測を採点する ―― NeuroMorpho の SWC を真値に、投影が何を壊すかを測る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_swc_tree_truth/03_junctions_vs_view_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_swc_tree_truth/03_junctions_vs_view.png)

*↑ **本物の木で骨格計測を採点する ―― NeuroMorpho の SWC を真値に、投影が何を壊すかを測る** ―― 血管網 PoC は合成の木を真値にしたが、ここでは実物の木 ―― NeuroMorpho.Org の SWC(節点ごとに座標・半径・親 id、マウス新皮質 3 本、CC BY 4.0)―― を真値にする。SWC は構造制約(根はちょうど 1 つ / 親 id < 子 id / 節点数 = 辺数 + 1)を持つのでそれ自体が門になり、壊れた木は採点しない。3 次元の Sholl 交点数(根を中心とする球と枝の交点)は原点からの距離が回転不変なので、12 回転で整数が 1 つも動かない。ところが画像計測は投影の上で走る ―― 投影して円で数えた Sholl は角度で最大 9〜16 交点動き、分岐点は真値 16 / 11 / 37 個に対して視線 12 角度で 22〜28 / 15〜24 / 41〜49 個(余分は枝の交差が細線化で分岐に化けたもの)、骨格長はケーブル総長の 0.72〜0.82 倍に縮む。「木の計測」の精度は木でなく視線が決めている。データは同梱せず、無ければ構造制約を満たす合成の木で回る(3 次元で絡む合成の木は投影の余分が実物より多い ―― 印字する)。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_swc_tree_truth/01_swc_projection_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_swc_tree_truth/01_swc_projection.png)

*↑ 測定の図*

[![3-D の交点数は 12 回転で整数が 1 つも動かない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_swc_tree_truth/02_sholl_3d_vs_projected_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_swc_tree_truth/02_sholl_3d_vs_projected.png)

*↑ 3-D の交点数は 12 回転で整数が 1 つも動かない。*

```
py -3.11 examples/poc_swc_tree_truth.py
```

ソース: [examples/poc_swc_tree_truth.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_swc_tree_truth.py)

この回が作った図は全部で **3 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_swc_tree_truth)

使用 op(ノートへ): [`skeleton`](https://furuse.work/ops/2d/region/skeleton.html) · [`tree_from_swc`](https://furuse.work/ops/graph/tree/tree_from_swc.html) · [`tree_morphometry`](https://furuse.work/ops/graph/tree/tree_morphometry.html) · [`tree_sholl`](https://furuse.work/ops/graph/tree/tree_sholl.html)

## No.2026.164 —— 線虫の脳の核は生まれた時から在る ―― 8 匹の発生系列で「最も深い殻」に居続ける細胞を数える

[![線虫の脳の核は生まれた時から在る ―― 8 匹の発生系列で「最も深い殻」に居続ける細胞を数える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_worm_core_persists/03_core_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_worm_core_persists/03_core_map.png)

*↑ **線虫の脳の核は生まれた時から在る ―― 8 匹の発生系列で「最も深い殻」に居続ける細胞を数える** ―― Witvliet 2021 の 8 匹(生後 0 時間 → 成虫)の化学シナプス配線を、新しい op graph_kcore(k-core / 重み付き s-core、入・出・総・無向)・graph_rich_club_curve(rich club 係数を全 k で、次数保存ヌルで割る)・graph_core_persistence(K 匹の最深殻に居続ける細胞)で剥く。門は定理: 完全グラフの殻の指数は n − 1、木は 1、閉路は 2、0/1 行列の s-core は k-core と厳密一致、重み c 倍で指数 c 倍、無向は networkx と全節点一致、φ(k) は 1 点ずつの graph_rich_club と全 k で一致。シナプス数で剥いた最深殻(入・s-core)は発生を通じて 6〜10 細胞と小さいまま指数が 7 → 55 と深くなり、介在神経 RIA の左右対は 8 匹全員の最深殻に居る(運動神経 10 種・介在神経 2 種、筋肉とグリアは入らない)。0/1 で剥く k-core は成虫でも指数 3〜5 で最深殻が 150 細胞に膨らみ核を見分けられない。入・出 × k・s の 4 種のどれかで持続する細胞は 51 個で Yadav & Singh 2026(bioRxiv)の公表値と一致、ただし論文の「頭部の神経では AIBR・RIBL・RIAR の 3 個」は 4 種すべてで持続する RIAL・RIAR とは定義が合わず、そのまま記す。rich club の帯は全段で在り、比の最大は 1.4〜3.3 倍、成虫で k = 1〜28 に広がる。図は 8 匹の配線を神経の位置(骨格の根、体軸方向から)に載せ、成虫の向きに Procrustes で揃えた 8 面と、段の間を補間して配線が生え核が入れ替わる動く図。所要 ≈ 17 s。*

[![同じ 8 匹。0/1 の k-core は成虫でも指数 5、最深殻が 179 細胞まで膨らむ。シナプス数で剥く s-core は最深殻が 6〜10 細胞のまま深くなる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_worm_core_persists/01_core_depth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_worm_core_persists/01_core_depth.png)

*↑ 測定の図 ―― 同じ 8 匹。0/1 の k-core は成虫でも指数 5、最深殻が 179 細胞まで膨らむ。シナプス数で剥く s-core は最深殻が 6〜10 細胞のまま深くなる。*

[![次数保存ヌル 20 標本。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_worm_core_persists/02_rich_club_curves_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_worm_core_persists/02_rich_club_curves.png)

*↑ 次数保存ヌル 20 標本。*

[![生後 0 時間から成虫まで。結合が生え、最深殻(橙)が入れ替わる中で、赤の細胞(RIAL RIAR)は一度も外れない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_worm_core_persists/04_core_map_gif.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_worm_core_persists/04_core_map_gif.gif)

*↑ 動く図 ―― 生後 0 時間から成虫まで。結合が生え、最深殻(橙)が入れ替わる中で、赤の細胞(RIAL RIAR)は一度も外れない。*

```
py -3.11 examples/poc_worm_core_persists.py
```

ソース: [examples/poc_worm_core_persists.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_worm_core_persists.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_worm_core_persists)

使用 op(ノートへ): [`graph_core_persistence`](https://furuse.work/ops/graph/population/graph_core_persistence.html) · [`graph_kcore`](https://furuse.work/ops/graph/core/graph_kcore.html) · [`graph_rich_club`](https://furuse.work/ops/conngraph/stats/graph_rich_club.html) · [`graph_rich_club_curve`](https://furuse.work/ops/graph/core/graph_rich_club_curve.html)

### 天文・環境ウィング ―― 位置で偏り、真値の定義で反転する

星の明るさと位置、太陽の縁、全天の雲量、海氷の密接度、畑の被覆率、地形、河川の水位。対象は遠く、真値は普通手に入りません。この部屋の 21 点はそれを逆手に取り、天球座標・球冠の立体角・Eddington の周辺減光・国土地理院の標高タイルといった閉形式や公開データから真値を置いています。

共通して出てきたのは「同じ物が、どこにあるかで違って読める」ことです。同じ雲が天頂と地平線で 1.45 倍、同じ厚さの雲が太陽からの角距離で検出されたりされなかったり、同じ反射が検出器によって「静かに低く読む」か「黙って止まる」か。

もう 1 つは、真値の定義が結論を決めること。薄氷を「氷」に入れるか入れないかで同じ推定が -4.4 と +2.7 ポイントに外れ、マスクの角度を書かない雲量は 0.18 から 0.23 まで名乗れます。測定器より先に、何を真値と呼ぶかを書く必要があります。

## No.2026.001 —— 全天カメラの雲量 ―― 画素を数えると位置で偏る

[![全天カメラの雲量 ―― 画素を数えると位置で偏る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_allsky_cloud_cover/03_mask_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_allsky_cloud_cover/03_mask_sweep.png)

*↑ **全天カメラの雲量 ―― 画素を数えると位置で偏る** ―― 魚眼(等距離射影)の空に球冠の雲(立体角は閉形式)を置き、画素数比と立体角重みで雲量を数えた図。同じ雲が天頂角 0 → 82 度で 0.00789 → 0.01142(1.45 倍)に読める。幾何だけの誤差 -5.02 % と検出だけの誤差 +37.95 % が、素朴な数え方では +29.73 % に打ち消し合う。*

[![画素数比は天頂で 0.81、地平線側で 1.17。重みを掛けると 1 に張り付く。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_allsky_cloud_cover/01_jacobian_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_allsky_cloud_cover/01_jacobian.png)

*↑ 測定の図 ―― 画素数比は天頂で 0.81、地平線側で 1.17。重みを掛けると 1 に張り付く。*

[![偽陽性は実測と閉形式が重なる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_allsky_cloud_cover/02_rbr_threshold_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_allsky_cloud_cover/02_rbr_threshold.png)

*↑ 偽陽性は実測と閉形式が重なる。*

[![4 枚目が sinθ/θ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_allsky_cloud_cover/04_allsky_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_allsky_cloud_cover/04_allsky.png)

*↑ 4 枚目が sinθ/θ。*

```
py -3.11 examples/poc_allsky_cloud_cover.py
```

ソース: [examples/poc_allsky_cloud_cover.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_allsky_cloud_cover.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_allsky_cloud_cover)

使用 op(ノートへ): [`polar_trans_image`](https://furuse.work/ops/2d/geometry/polar_trans_image.html)

## No.2026.002 —— 何枚重ねると、星の明るさは何 % の精度で測れるか

[![何枚重ねると、星の明るさは何 % の精度で測れるか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_astro_photometry/01_stack_scaling_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_astro_photometry/01_stack_scaling.png)

*↑ **何枚重ねると、星の明るさは何 % の精度で測れるか** ―― 指定どおりに置いた星野を N 枚重ね、開口測光の誤差が 1/√N で落ちるかを見た図。N = 1 → 16 で中央誤差 0.6350 % → 0.1616 %、8 通りすべてで理論から 4.6 % 以内。宇宙線 1 発で単純平均は +5.89 %、κ-σ なら +0.30 % ―― 棄却率は動かないので「棄却率が上がったから効いた」とは言えない。*

[![単純平均だけが 5.9 % 残る。κ-σ は汚染なしと区別できないところまで戻すが、棄却率はほとんど動かない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_astro_photometry/02_cosmic_ray_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_astro_photometry/02_cosmic_ray.png)

*↑ 測定の図 ―― 単純平均だけが 5.9 % 残る。κ-σ は汚染なしと区別できないところまで戻すが、棄却率はほとんど動かない。*

[![開口を広く取れるなら、ぼけたフレームも同じ明るさを持っている(r=12 では 3 本が重なる)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_astro_photometry/03_aperture_tradeoff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_astro_photometry/03_aperture_tradeoff.png)

*↑ 開口を広く取れるなら、ぼけたフレームも同じ明るさを持っている(r=12 では 3 本が重なる)。*

[![悪いほうは星が広がっている。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_astro_photometry/04_lucky_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_astro_photometry/04_lucky_frames.png)

*↑ 悪いほうは星が広がっている。*

```
py -3.11 examples/poc_astro_photometry.py
```

ソース: [examples/poc_astro_photometry.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_astro_photometry.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_astro_photometry)

使用 op(ノートへ): [`aperture_photometry`](https://furuse.work/ops/astrostack/photometry/aperture_photometry.html) · [`drizzle_resample`](https://furuse.work/ops/astrostack/stack/drizzle_resample.html) · [`lucky_select`](https://furuse.work/ops/astrostack/quality/lucky_select.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`sigma_clip_stack`](https://furuse.work/ops/astrostack/stack/sigma_clip_stack.html) · [`synth_frame_series`](https://furuse.work/ops/astrostack/synth/synth_frame_series.html) · [`synth_starfield`](https://furuse.work/ops/astrostack/synth/synth_starfield.html)

## No.2026.059 —— 変化検出と位置合わせ誤差 ―― 偽陽性はエッジの帯、しかも崖つき

[![変化検出と位置合わせ誤差 ―― 偽陽性はエッジの帯、しかも崖つき](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/03_map_fp_shift_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/03_map_fp_shift.png)

*↑ **変化検出と位置合わせ誤差 ―― 偽陽性はエッジの帯、しかも崖つき** ―― 2 時期の合成地表(畑・道路・建物・森林・湖)に建物新設・伐採・水域拡大を仕込み、時期 2 をサブピクセル平行移動・微小回転・照明差で崩して差分の偽陽性を測った。偽陽性はずれ 0.3 px まで雑音の床、0.5 px から崖(PSF から予測した δ*=τσ√2π/C=0.351 px と一致)、3 px で 7175 px。エッジ総長×ずれの比例則は 3 px で 0.78 倍だが崖を説明せず、PSF と雑音を入れた台帳予測は 0.84〜1.07 倍。位置合わせ 3 経路(PIV/特徴点/LK)は残留 0.02〜0.13 px まで戻すが、唯一の位相相関は 3-D 用の整数精度で残留 0.72 px ―― その偽陽性 995 px は「ずれだけ」の掃引を同じ残留で読んだ 915 px に乗る。伐採は位置合わせが完璧でも検出率 0.33、照明差だけの偽陽性 17198 px は放射補正で 0 になるがずれの 3497 px は直らない。*

[![0.35 px までゼロ、そこから立ち上がる。比例則は崖を説明しない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/01_plot_fp_vs_shift_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/01_plot_fp_vs_shift.png)

*↑ 測定の図 ―― 0.35 px までゼロ、そこから立ち上がる。比例則は崖を説明しない。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/02_table_fp_shift_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/02_table_fp_shift.png)

*↑ この回の図*

[![回転 1 度の偽陽性地図(橙)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/05_map_rotation_1deg_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/05_map_rotation_1deg.png)

*↑ 回転 1 度の偽陽性地図(橙)。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/07_table_size_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/07_table_size_cliff.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/09_table_registration_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/09_table_registration.png)

*↑ この回の図*

```
py -3.11 examples/poc_change_detection_misreg.py
```

ソース: [examples/poc_change_detection_misreg.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_change_detection_misreg.py)

この回が作った図は全部で **11 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_change_detection_misreg)

使用 op(ノートへ): [`affine_trans_image`](https://furuse.work/ops/2d/geometry/affine_trans_image.html) · [`histogram_match`](https://furuse.work/ops/colortransport/matching/histogram_match.html) · [`match_phase_3d`](https://furuse.work/ops/3d/match_pose/match_phase_3d.html) · [`opening_circle`](https://furuse.work/ops/2d/region/opening_circle.html) · [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`piv_outlier_mask`](https://furuse.work/ops/piv/validate/piv_outlier_mask.html) · [`procrustes_fit`](https://furuse.work/ops/shapestat/procrustes/procrustes_fit.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html) · [`voxel_iou`](https://furuse.work/ops/3d/metrics/voxel_iou.html)

## No.2026.096 —— 疎な温度センサから 3-D 熱場を復元する ―― 格子の死角がラックを消す

[![疎な温度センサから 3-D 熱場を復元する ―― 格子の死角がラックを消す](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_datacenter_thermal_field/01_scene_truth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_datacenter_thermal_field/01_scene_truth.png)

*↑ **疎な温度センサから 3-D 熱場を復元する ―― 格子の死角がラックを消す** ―― サーバ室 12 x 8.4 x 3.0 m の温度場を式で置き、格子状の温度センサから復元してホットスポット 3 台を探す。★ゼロ点(全センサの平均 = 場は平らとみなす)は RMSE 2.192 °C でホットスポットを 1 台も見つけない。最良の RBF は 0.214 °C = 10.2 倍。★★崖は測る前に閉形式で言える: 間隔 d の 3-D 格子でピークからいちばん遠い点はセル中心の d√3/2 なので、見えるピークは **exp(-3d²/8σ²)** 倍に落ち、半減間隔は d* = 1.3596σ。幾何だけを取り出した実測との差は最大 **1.2e-15** —— 完全に一致する。★**外れたのは閉形式ではなく「現場で測れる量」のほう**。復元した場のピークには背景の復元誤差が同じ場所に載るので、素朴な実測は予測を最大 +0.2598 超過する —— つまり**崖は実際より浅く見える**。σ=0.22 m のラックは d=1.20 m で幾何の回復 0.000014(消滅)なのに、素朴に測ると 0.1609 残って見える。残っているのは背景の誤差。★閉形式は曲線ではなく**床**: 同じ d=0.60 m でもラックが格子のどこに落ちるかで回復は 0.0615(セル中心)から 1.0(センサ直上)まで跳ぶ。設計に使えるのは最悪位相の値だけで、「平均すればこれくらい見える」はそのラックには通じない。★対照群 a(格子 vs 乱数、同じ本数): 乱数は死角を**消さない。どのラックが死角に落ちるかを振るだけ**。格子の最悪距離を超える乱数点は実測 6.17 %(Poisson の予測 6.58 %、差 0.41 ポイント)。格子は幾何の下限を 1 度も割らないが、乱数は 3 台中 2 台で割った —— 同じ本数でも「最悪でもここまで見える」と設計時に言い切れるかが違う。★★対照群 b(補間法 3 種): **動かないのは指数、動くのは係数**。log 回復 vs d² の傾きは予測 -3.0612 /m² に対し 3 手法とも最大 3.05 % 差。しかし「崖の位置は手法で動かない」という予測は外した —— 薄板スプラインは内挿なのに節点の値を超えて一律 1.372 倍持ち上がり、半減間隔を 0.4777 → 0.6015 m(26 %)ずらす。最近傍と線形が小数点以下まで一致するのは、どちらも節点を超えないため。★「持ち上がる手法は偽の峰も同じだけ立てる」も外した: 床は最近傍 0.975 °C(雑音 0.15 °C の 6.5 倍 = 滑らかな背景を階段で近似した段差)に対し線形 0.132 / RBF 0.164 で、**持ち上がる側のほうが低い**。★物差し 3 つ(場の RMSE / ピーク温度の誤差 / 位置の誤差)を同時に勝つ手法は無い。線形補間は d=1.20 m で評価点の 71.2 % が凸包の外に出て最近傍に化ける —— センサを部屋の内側にしか置けない以上、外挿しない手法は端で必ず別の手法になる。★この PoC が炙り出した道具の穴を、その場で埋めた: 散らばった N-D 点から場を作る `fs.interp_scattered`(nearest / linear / rbf)。設計で効いたのは**凸包の外に出た割合を返り値に入れた**こと —— この PoC が測った 71.2 % は黙って NaN か別手法に化ける量なので、戻り値に居るべきだった。使ってみて `neighbors`(RBF を近傍だけで解く)も足した —— 全体解は O(n³) で1400 / 4000 / 8000 点が 0.55 / 1.76 / 7.53 秒。**op は使って初めて足りない引数が分かる**。*

[![幾何の実測は予測と最大 1.2e-15 しか違わない。素朴な実測が上に浮くぶんが背景の復元誤差。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_datacenter_thermal_field/02_cliff_prediction_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_datacenter_thermal_field/02_cliff_prediction.png)

*↑ 測定の図 ―― 幾何の実測は予測と最大 1.2e-15 しか違わない。素朴な実測が上に浮くぶんが背景の復元誤差。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_datacenter_thermal_field/03_cliff_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_datacenter_thermal_field/03_cliff_table.png)

*↑ この回の図*

[![格子の最悪距離 0.520 m を乱数の 6.17 % が超えた(予測 6.58 %)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_datacenter_thermal_field/04_grid_vs_random_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_datacenter_thermal_field/04_grid_vs_random.png)

*↑ 格子の最悪距離 0.520 m を乱数の 6.17 % が超えた(予測 6.58 %)。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_datacenter_thermal_field/06_metric_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_datacenter_thermal_field/06_metric_table.png)

*↑ この回の図*

[![横=x 0..12 m、縦=y 0..8.4 m。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_datacenter_thermal_field/07_map_reconstruction_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_datacenter_thermal_field/07_map_reconstruction.png)

*↑ 横=x 0..12 m、縦=y 0..8.4 m。*

```
py -3.11 examples/poc_datacenter_thermal_field.py
```

ソース: [examples/poc_datacenter_thermal_field.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_datacenter_thermal_field.py)

この回が作った図は全部で **8 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_datacenter_thermal_field)

使用 op(ノートへ): [`interp_scattered`](https://furuse.work/ops/math/interp_poly/interp_scattered.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`rmse`](https://furuse.work/ops/imgmetrics/fidelity/rmse.html) · [`vol_local_maxima`](https://furuse.work/ops/3d/feature/vol_local_maxima.html)

## No.2026.012 —— 地形を測る ―― 傾斜・水の流れ・日当たりを閉形式と突き合わせる

[![地形を測る ―― 傾斜・水の流れ・日当たりを閉形式と突き合わせる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dem_terrain/01_cone_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dem_terrain/01_cone.png)

*↑ **地形を測る ―― 傾斜・水の流れ・日当たりを閉形式と突き合わせる** ―― 平面・円錐・ガウス丘で傾斜・曲率・天空率を閉形式と突き合わせた図。ガウス丘の曲率誤差はセルを半分にすると約 4 分の 1 ―― 離散化の誤差であって式の誤りではない。天空率は 513×513・8 方位で 2.03 秒 ―― 書き直す前は 41.9 秒かかっていて、テストは「動く」ことしか確かめていなかった。*

[![参照線と平行 = 2 次収束 = 離散化の誤差。式が違えばセルを細かくしても誤差は下げ止まる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dem_terrain/02_curvature_convergence_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dem_terrain/02_curvature_convergence.png)

*↑ 測定の図 ―― 参照線と平行 = 2 次収束 = 離散化の誤差。式が違えばセルを細かくしても誤差は下げ止まる。*

[![同じ地形・同じ op。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dem_terrain/03_nodata_policies_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dem_terrain/03_nodata_policies.png)

*↑ 同じ地形・同じ op。*

[![陰影の平均は 北向き 0.354 / 東向き 0.811 / 南向き 0.811 / 西向き 0.354。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dem_terrain/04_hillshade_aspect_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dem_terrain/04_hillshade_aspect.png)

*↑ 陰影の平均は 北向き 0.354 / 東向き 0.811 / 南向き 0.811 / 西向き 0.354。*

[![主図(動画、640 × 360・30 fps・11 秒): 800 m 四方の地形(セル 5 m)を南南西から北へ回り込み、止まって太陽を一周させる。陰影は描画の光でなく dem_hillshade(仰角 35 度)の出力で塗り、青は de](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dem_terrain/05_terrain_flight.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dem_terrain/05_terrain_flight.gif)

*↑ 動く図 ―― 主図(動画、640 × 360・30 fps・11 秒): 800 m 四方の地形(セル 5 m)を南南西から北へ回り込み、止まって太陽を一周させる。陰影は描画の光でなく dem_hillshade(仰角 35 度)の出力で塗り、青は dem_flow_accumulation の集水量 150 セル以上。南向き斜面の陰影の平均は太陽方位 187 度で最大 0.719、北向き斜面は 1 度で最大 0.709 —— 日当たりは斜面の向きで決まる(§6 の平面と同じ結論)。高さは画面上だけ 2.5 倍。*

```
py -3.11 examples/poc_dem_terrain.py
```

ソース: [examples/poc_dem_terrain.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dem_terrain.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_dem_terrain)

使用 op(ノートへ): [`color_bar`](https://furuse.work/ops/annotate/furniture/color_bar.html) · [`dem_aspect`](https://furuse.work/ops/dem/surface/dem_aspect.html) · [`dem_curvature`](https://furuse.work/ops/dem/surface/dem_curvature.html) · [`dem_fill_sinks`](https://furuse.work/ops/dem/hydrology/dem_fill_sinks.html) · [`dem_flow_accumulation`](https://furuse.work/ops/dem/hydrology/dem_flow_accumulation.html) · [`dem_hillshade`](https://furuse.work/ops/dem/shading/dem_hillshade.html) · [`dem_sky_view_factor`](https://furuse.work/ops/dem/visibility/dem_sky_view_factor.html) · [`dem_slope`](https://furuse.work/ops/dem/surface/dem_slope.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html)

## No.2026.066 —— 系外惑星トランジットを開口測光で取り出す ―― 深さと継続時間は別々に壊れる

[![系外惑星トランジットを開口測光で取り出す ―― 深さと継続時間は別々に壊れる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/01_scene_starfield_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/01_scene_starfield.png)

*↑ **系外惑星トランジットを開口測光で取り出す ―― 深さと継続時間は別々に壊れる** ―― 合成星野 240 枚に目標星だけ 10 ppt の周辺減光つきトランジットを仕込み、透明度変動・副画素ドリフト・フラット不均一・光子雑音を別々の乱数で載せて、fullseye の star_detect → frame_align → aperture_photometry で光度曲線を取り出す。ゼロ点(目標星の開口積分)は雲で深さ +72 ppt に壊れ、比較星との比なら -0.13 ppt / T14 -0.9 fr。比較星の選び方で残差 rms は 1.91〜11.43 ppt(6.0 倍)、逆分散重みは生の分散で決めると雲に騙されて単純和より 1.52 倍悪い。開口 1σ の崖は予想した重心誤差ではなく op の開口マスクの階段(supersample=8、不動の星で理論比 1.69 → 32 で 0.93)。検出限界 SNR=5 は暦既知で実測 1.48 / 理論 1.45 ppt、暦未知は 2.0 ppt で深さより先に継続時間が壊れる。ドリフト 2 px とフラット 3 % は単独で 0.16 / 0.08 ppt だが掛け算で 0.94 ppt、4 px で 2.97 ppt(真値の 30 %)の偽の深さ。*

[![前/入/最深部/出/後の各段階で平均した画像からトランジット外の平均を引いた [e-)。4 倍拡大](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/02_frames_transit_phases_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/02_frames_transit_phases.png)

*↑ 測定の図 ―― 前/入/最深部/出/後の各段階で平均した画像からトランジット外の平均を引いた [e-]。4 倍拡大*

[![ゼロ点と比較星の和は雲(全星共通)そのもの。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/03_lightcurve_zero_vs_relative_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/03_lightcurve_zero_vs_relative.png)

*↑ ゼロ点と比較星の和は雲(全星共通)そのもの。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/05_comparison_choice_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/05_comparison_choice.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/07_aperture_depth_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/07_aperture_depth_bias.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/09_depth_cliff_t14_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/09_depth_cliff_t14.png)

*↑ この回の図*

```
py -3.11 examples/poc_exoplanet_transit.py
```

ソース: [examples/poc_exoplanet_transit.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_exoplanet_transit.py)

この回が作った図は全部で **11 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_exoplanet_transit)

使用 op(ノートへ): [`aperture_photometry`](https://furuse.work/ops/astrostack/photometry/aperture_photometry.html) · [`frame_align`](https://furuse.work/ops/astrostack/align/frame_align.html) · [`normalize`](https://furuse.work/ops/shape2d/descriptor/normalize.html) · [`sigma_clip_stack`](https://furuse.work/ops/astrostack/stack/sigma_clip_stack.html) · [`star_detect`](https://furuse.work/ops/astrostack/photometry/star_detect.html)

## No.2026.098 —— 座標は「もっともらしい数字」のまま数十メートル間違う ―― 楕円体高・測地成果・平面近似

[![座標は「もっともらしい数字」のまま数十メートル間違う ―― 楕円体高・測地成果・平面近似](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_height_frames/01_geoid_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_height_frames/01_geoid_frames.png)

*↑ **座標は「もっともらしい数字」のまま数十メートル間違う ―― 楕円体高・測地成果・平面近似** ―― GNSS が返すのは**楕円体高 h**、地図と設計図が使うのは**標高 H**。関係は `H = h - N`(N = ジオイド高。日本付近で 30〜40 m)。この取り違えが**どの量に効き、どの量では消えるか**を、合成のジオイド場で真値を植てて測る。★**床を二重に取る**: 既存 op の往復は 3D で 1.07e-06 m。それに加えて**独立実装(反復法)との差**を緯度 7.2e-07 m / 高さ 8.6e-07 m で測った —— **往復だけでは「往きと復りが同じ向きに誤っている」を排除できない**から。★**閉形式の予測が当たったもの**: 傾斜への影響の上限 `atan|∇N|` は予測 0.008771 度 / 実測 0.008600 度(N 一定の対照群は **2.0e-14 度 = 厳密に 0**)、土量 `ΔV = A·N̄` は差 **1.5e-08 m³**、平地の流向が反転する割合は予測 76.1 % / 実測 76.2 %(42787/56169。D8 では 97.2 %)、測地成果の相対誤差 `(a_B-a_W)/a_W` は予測 -116.0 ppm / 実測 -106.1 ppm(1 km 基線で -0.1059 m)。★★**外した予測**: 視通への影響の上限を `|∇N|·d = 2.60 m` と置いたが、実測は **0.052 m(50 分の 1)**。理由は **N の線形部が視線にも地面にも同じだけ乗って消える**こと —— 絞り直した上限 `|N''|d²/8 = 0.144 m` の 36 % に収まった。判定が変わった組は 3/2120(0.14 %)で、**曲率落ち 14.2 m のほうが 276 倍効く**。★★**崖は閉形式で出るが、1 つの数字では出ない**: 局所平面近似の落ち `d²/2R` は 10 km で予測 -7.8481 m。実測は**南北 -7.8652 m / 東西 -7.8303 m** —— 子午線曲率半径 6357143 m と卯酉線 6385412 m の差で、平均半径の予測は**両者のあいだ**に来る(30 km で 0.316 m 開く)。大気屈折(k≈0.13)を入れると崖は `1/√(1-k) = 1.072` 倍だけ遠くへ動く(5 mm を割るのが 252 m → 271 m)。★**この展示の主題**: **同じ 36 m が、量によって全部効いたり全く効かなかったりする**。差を取る量(傾斜 0.0086 度・視通 0.052 m)ではほぼ消え、絶対量では全部効く(土量 **+3.97e+07 m³**、浸水面積 41.9 % → **0.0 %**、逆向きの誤りなら 100 %)。★0 %/100 % は分母 58081 の**構造的な全滅**で、小標本の産物ではないことも明記した。★対照群で「**設計面も同じ GNSS で作る**」と誤差が **0.0 m³** になる —— **汚染された物差しで汚染された対象を測ると、誤差は消えたように見える**。★測地成果(datum)の取り違えは平均 **446.6 m**(281.6〜592.7)ずれるのに、相対検査(基線長の比較)が見せるのは 1 km あたり 0.106 m = **4216 分の 1**。**大きさではなく『もっともらしさ』が問題**で、例外は出ず地図にも載る。★epoch(座標の時刻)も静かに効く: プレート運動 2.5 cm/年 なら Scan-to-BIM の 5 mm を **0.2 年**で、土木の出来形 25 mm を 1.0 年で割る。**成果に epoch を書かないと、古い成果ほど静かにずれ続ける**。★★**静かに間違う / うるさく壊れる を分けて数えた**(標本 3600、全球格子)。**例外が出たのは緯経の入れ替えだけ、それも 1800/3600 = 50.0 %**(`lat_deg must be within [-90,90]` に当たるのは |経度|>90 のときだけ)。ラジアンを度として渡す(8883 km)、経度の符号反転(4800 km)、ECEF の x と y の入れ替え(4849 km、**返った緯度経度が妥当な範囲に収まった点 3600/3600 = 100 %**)、高さがフィート(228 m)は**例外 0 件**。まとめ表 11 項目のうち **静かに間違うものが 10 件**。★★**道具の穴を見つけて、その場で直した**: `dem_ecef_to_geodetic` が地球の中心付近で **緯度 180 度**を返していた —— 緯度として存在せず、しかも**自分の逆関数が拒否する**値。原因は楕円体の**縮閉線の内側では測地緯度が一意でない**ことで、閉形式 `(a·r)^(2/3) + (b·|z|)^(2/3) < (a²-b²)^(2/3)` で判定して fail-closed にした(境界 42697.7 m は実測ともちょうど一致)。★docstring の往復誤差も**中央値を最大値として**書いていたので、標本の範囲つきで測り直した。*

[![分母 58081 セル。真値 24325(41.9 %)に対し、誤用は 0 と 58081。**どちらの絵も「もっともらしい」**(全面浸水は津波の図に見える)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_height_frames/02_flood_masks_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_height_frames/02_flood_masks.png)

*↑ 測定の図 ―― 分母 58081 セル。真値 24325(41.9 %)に対し、誤用は 0 と 58081。**どちらの絵も「もっともらしい」**(全面浸水は津波の図に見える)。*

[![真の勾配の中央値 9.15e-05 に対し |∇N| は 1.2e-04。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_height_frames/03_flow_flip_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_height_frames/03_flow_flip.png)

*↑ 真の勾配の中央値 9.15e-05 に対し |∇N| は 1.2e-04。*

[![2.5 cm/年(代表値)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_height_frames/05_epoch_drift_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_height_frames/05_epoch_drift.png)

*↑ 2.5 cm/年(代表値)。*

[![真の ECEF(dem_geodetic_to_ecef)を自前の ENU 回転に通して測った。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_height_frames/08_enu_drop_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_height_frames/08_enu_drop.png)

*↑ 真の ECEF(dem_geodetic_to_ecef)を自前の ENU 回転に通して測った。*

[![全球 3600 点。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_height_frames/11_axis_order_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_height_frames/11_axis_order.png)

*↑ 全球 3600 点。*

```
py -3.11 examples/poc_geodetic_height_frames.py
```

ソース: [examples/poc_geodetic_height_frames.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_geodetic_height_frames.py)

この回が作った図は全部で **13 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_geodetic_height_frames)

使用 op(ノートへ): [`datum_tilt_check`](https://furuse.work/ops/drive/granular/datum_tilt_check.html) · [`dem_aspect`](https://furuse.work/ops/dem/surface/dem_aspect.html) · [`dem_datum_shift_3param`](https://furuse.work/ops/dem/geodesy/dem_datum_shift_3param.html) · [`dem_earth_curvature_drop`](https://furuse.work/ops/dem/geodesy/dem_earth_curvature_drop.html) · [`dem_ecef_to_geodetic`](https://furuse.work/ops/dem/geodesy/dem_ecef_to_geodetic.html) · [`dem_enu_from_geodetic`](https://furuse.work/ops/dem/geodesy/dem_enu_from_geodetic.html) · [`dem_flow_direction`](https://furuse.work/ops/dem/hydrology/dem_flow_direction.html) · [`dem_geodetic_from_enu`](https://furuse.work/ops/dem/geodesy/dem_geodetic_from_enu.html) · [`dem_geodetic_to_ecef`](https://furuse.work/ops/dem/geodesy/dem_geodetic_to_ecef.html) · [`dem_geoid_height`](https://furuse.work/ops/dem/geodesy/dem_geoid_height.html) · [`dem_slope`](https://furuse.work/ops/dem/surface/dem_slope.html) · [`median`](https://furuse.work/ops/2d/rank/median.html)

## No.2026.068 —— 葉の病斑面積率 ―― 色の軸は照明に勝つが、等級は葉マスクと縁の定義で決まる

[![葉の病斑面積率 ―― 色の軸は照明に勝つが、等級は葉マスクと縁の定義で決まる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/01_scene.png)

*↑ **葉の病斑面積率 ―― 色の軸は照明に勝つが、等級は葉マスクと縁の定義で決まる** ―― 閉形式の葉輪郭に既知面積の病斑を植え、土・片側照明・白飛び・影を重ねた合成葉で、病斑面積率(病斑画素/葉画素)を測る。緑チャネルの固定しきい値(ゼロ点)は土の背景だけで +65.2 pt 外れ、白色方向を射影で消した G で葉を切り Lab の a* で病斑を切ると標準場面で -0.8 pt に収まる。照明むらは 50 % まで a* を動かさないが、白飛びの鏡面反射は a* に偽陽性だけを出し(20 % で +12.6 pt、偽陰性 0.0)、白を足しても動かない色相なら +2.0 pt。病斑の縁のぼけ幅 4 px では「不透明度 25 %/75 % のどちらを境界にするか」だけで面積率が ±3.5 pt 動き(Steiner の式が 0.4 pt 以内で予測)、等級境界 ±3 pt に置いた 40 枚は土の上ではどの手法も 19〜35 枚が誤等級 ―― 黒布の上で明るさで葉を切ると色相の固定しきい値で 8 枚。*

[![FN(青)の大きな塊は影と鏡面反射が重なった病斑(葉マスクごと落ちる)。FP(赤)は鏡面反射の下と病斑の縁。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/02_error_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/02_error_map.png)

*↑ 測定の図 ―― FN(青)の大きな塊は影と鏡面反射が重なった病斑(葉マスクごと落ちる)。FP(赤)は鏡面反射の下と病斑の縁。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/03_frames_conditions_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/03_frames_conditions.png)

*↑ この回の図*

[![ゼロ点は固定しきい値を葉が割る列から予測できる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/04_cliff_illumination_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/04_cliff_illumination.png)

*↑ ゼロ点は固定しきい値を葉が割る列から予測できる。*

[![色相は白を足しても動かない(定義)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/06_cliff_specular_amplitude_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/06_cliff_specular_amplitude.png)

*↑ 色相は白を足しても動かない(定義)。*

[![予測の崖 1.8 px。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/08_cliff_lesion_size_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/08_cliff_lesion_size.png)

*↑ 予測の崖 1.8 px。*

```
py -3.11 examples/poc_leaf_disease_area.py
```

ソース: [examples/poc_leaf_disease_area.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_leaf_disease_area.py)

この回が作った図は全部で **9 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_leaf_disease_area)

使用 op(ノートへ): [`access_channel`](https://furuse.work/ops/2d/color/access_channel.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`fill_holes`](https://furuse.work/ops/2d/region/fill_holes.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`linear_to_srgb`](https://furuse.work/ops/gfx2d/colorspace/linear_to_srgb.html) · [`reg_close`](https://furuse.work/ops/2d/region/reg_close.html) · [`reg_erode`](https://furuse.work/ops/2d/region/reg_erode.html) · [`rgb_to_lab`](https://furuse.work/ops/imgmetrics/colorspace/rgb_to_lab.html) · [`select_largest`](https://furuse.work/ops/2d/region/select_largest.html) · [`sk_otsu`](https://furuse.work/ops/2d/segmentation/sk_otsu.html) · [`specular_free_transform`](https://furuse.work/ops/specular/dichromatic/specular_free_transform.html) · [`srgb_to_linear`](https://furuse.work/ops/gfx2d/colorspace/srgb_to_linear.html) · [`trans_from_rgb`](https://furuse.work/ops/2d/color/trans_from_rgb.html)

## No.2026.078 —— 太陽光発電所のドローン熱画像 —— 温度差を測っているつもりで、風と角度を測っている

[![太陽光発電所のドローン熱画像 —— 温度差を測っているつもりで、風と角度を測っている](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/06_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/06_scene.png)

*↑ **太陽光発電所のドローン熱画像 —— 温度差を測っているつもりで、風と角度を測っている** ―― 定常熱収支の閉形式でメガソーラーのアレイを合成し、既知の故障(セル内ホットスポット・ストリング故障)と、故障ではない温度差(影・汚れ)を仕込んだ図。余剰発熱 320 W/m² のホットスポットは薄まる前 11.20 K なのにカメラには 4.23 K しか届かず、薄めているのは予想した熱伝導(×0.960)ではなくカメラ(×0.511)だった。電気的故障をひとつも置かない対照群でも、画像平均を基準にすると塊が 6 個上がる(健全 1・非故障の温度差 5)。崖はしきい値ではなく面積の門が決め、ホットスポットは風速 1.0 m/s で消える(面積基準の予測 1.1 m/s、ピーク基準の予測 3.0 m/s は外れ)。列間影は同じストリングの日向側を +4.68 K 熱くし、本物のストリング故障 +5.55 K との差は 0.87 K しかない。*

[![「偽」= 故障でも影でも汚れでもない場所に出た塊。しきい値 3.0 K、風速 1.0 m/s。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/01_norm_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/01_norm_table.png)

*↑ 測定の図 ―― 「偽」= 故障でも影でも汚れでもない場所に出た塊。しきい値 3.0 K、風速 1.0 m/s。*

[![U(v) = 1.75·(5.7 + 3.8v + h_rad)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/02_wind_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/02_wind_sweep.png)

*↑ U(v) = 1.75·(5.7 + 3.8v + h_rad)。*

[![半径 30 mm の熱源。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/03_gsd_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/03_gsd_sweep.png)

*↑ 半径 30 mm の熱源。*

[![ε(θ) は Fresnel(等価屈折率 1.8)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/04_angle_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/04_angle_sweep.png)

*↑ ε(θ) は Fresnel(等価屈折率 1.8)。*

[![風速 1.0 m/s、モジュールごとの中央値を基準。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/05_netd_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/05_netd_sweep.png)

*↑ 風速 1.0 m/s、モジュールごとの中央値を基準。*

```
py -3.11 examples/poc_pv_thermal_survey.py
```

ソース: [examples/poc_pv_thermal_survey.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pv_thermal_survey.py)

この回が作った図は全部で **7 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_pv_thermal_survey)

使用 op(ノートへ): [`beer_lambert_transmittance`](https://furuse.work/ops/optics/glassbody/beer_lambert_transmittance.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_select`](https://furuse.work/ops/blob/select/blob_select.html) · [`fresnel_dielectric`](https://furuse.work/ops/optics/interface/fresnel_dielectric.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`overlay_mask`](https://furuse.work/ops/annotate/overlay/overlay_mask.html) · [`surface_form_remove`](https://furuse.work/ops/roughness/prepare/surface_form_remove.html) · [`volume_downsample`](https://furuse.work/ops/3d/preprocess/volume_downsample.html) · [`warp_by_plane`](https://furuse.work/ops/3d/plane_sweep_stereo/warp_by_plane.html) · [`zoom_image_factor`](https://furuse.work/ops/2d/geometry/zoom_image_factor.html)

## No.2026.106 —— 実写の深宇宙に既知の星を仕込む ―― 汚染は測定値と信頼度を同じ向きに嘘つかせる

[![実写の深宇宙に既知の星を仕込む ―― 汚染は測定値と信頼度を同じ向きに嘘つかせる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_sky_photometry/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_sky_photometry/01_scene.png)

*↑ **実写の深宇宙に既知の星を仕込む ―― 汚染は測定値と信頼度を同じ向きに嘘つかせる** ―― Hubble Deep Field(NASA/STScI、public domain)の**本物の背景**に、フラックスが分かっているガウシアン星を仕込んで回収する ―― 真値は自分で入れたので確実、背景だけが本物。★実写の空は正規分布ではない: 頑健なばらつき 1,474 e- に対し素の標準偏差は 6,698 e-(4.54 倍)で、std をノイズだと思うと検出限界を 4.5 倍甘く出す。★背景は 1 つの数字ではなく、64x64 タイル 195 枚で 3,176〜8,448 e- に散る(大域中央値で引くと最大 3.6σ の系統誤差)。★★空だと思った場所でも開口に**一定量**が混入する ―― 回収比は F=2,000 e- で 4.38 倍、100,000 で 1.058 倍。これは倍率ではなく足し算で、1 + C/(F·frac) に最大ずれ 0.9 % で乗る(C = 6,677 e-、背景×実効画素のわずか 3.0 %)。★「偏りが 10 % を切るのは 67,521 e- から」と**先に予測してから**測ると回収比 1.086(予測 1.100)。★★混雑した場所では桁が変わる(341 倍 → 7.80 倍)―― 中央値は「外れ値に強い」のであって、視野の半分が汚染されていたら中央値こそが汚染。★★信頼度も同じ向きに嘘をつく: op が返す SNR 19.2 に対し同じ背景からの閉形式は 4.2。S/N は測ったフラックスから作るので、**S/N を採否の門にすると汚染された測定ほど通る**。*

[![開口 1 つあたり C = 6677 e- の足し算として説明できる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_sky_photometry/02_recovery_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_sky_photometry/02_recovery.png)

*↑ 測定の図 ―― 開口 1 つあたり C = 6677 e- の足し算として説明できる。*

[![SNR は測ったフラックスから作るので、混入で分子が膨らむと S/N も膨らむ(F=2000 で 19.2 対 4.2)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_sky_photometry/03_snr_lies_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_sky_photometry/03_snr_lies.png)

*↑ SNR は測ったフラックスから作るので、混入で分子が膨らむと S/N も膨らむ(F=2000 で 19.2 対 4.2)。*

[![混雑側は桁が変わる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_sky_photometry/04_recovery_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_sky_photometry/04_recovery_table.png)

*↑ 混雑側は桁が変わる。*

```
py -3.11 examples/poc_real_sky_photometry.py
```

ソース: [examples/poc_real_sky_photometry.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_sky_photometry.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_real_sky_photometry)

使用 op(ノートへ): [`aperture_photometry`](https://furuse.work/ops/astrostack/photometry/aperture_photometry.html)

## No.2026.080 —— 河川表面流速を斜め動画から測る(LSPIV)―― 速度の誤差と流量の誤差は別に数える

[![河川表面流速を斜め動画から測る(LSPIV)―― 速度の誤差と流量の誤差は別に数える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/01_scene.png)

*↑ **河川表面流速を斜め動画から測る(LSPIV)―― 速度の誤差と流量の誤差は別に数える** ―― 幅 8 m・最大 1.5 m/s のべき乗則の流速分布を真値に、泡トレーサを毎コマ動かして描いた川面を岸の斜めカメラ(ホモグラフィ既知)で 60 コマ撮り、空の映り込み・波紋・雑音を別々に足して、fullseye の piv_cross_correlate → warp_by_plane(正射化)→ piv_to_velocity で u(y) と流量 Q = h∫u dy を出す。ゼロ点(斜めのまま 1 尺度で換算)は近岸 +0.31 / 遠岸 -0.28 m/s と符号が逆で、見かけの川幅が 3.3 m に化けて流量 -57 %。正射化で速度 RMS 0.074 m/s・流量 -7.8 % だが、対照群でも流量 -3.0 % のうち -2.5 % は岸の台形積分だけで生じ、速度とは無関係。密度の崖は nan ではなく外れ値で来る(0.05 % で旗 44 %、アンサンブル相関は外れ窓を救わない)。窓を広げても岸の速度は「窓幅×勾配」の予想より桁で小さく(-0.008 m/s)、代わりに流量が -1.1 → -7.0 % と崖になる。動かない映り込みは細かいときだけ効き、引かれてから(速度比 0.70)張り付く(0.03)、時間中央値引きで 0.998 に戻る。dt の崖は 1/4 則ではなく対の消失で、探索上限を外しても同じ k=4 に立つ。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/02_frames_oblique_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/02_frames_oblique.png)

*↑ 測定の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/03_map_speed_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/03_map_speed.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/05_density_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/05_density_cliff.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/08_window_discharge_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/08_window_discharge.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/10_reflection_modes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/10_reflection_modes.png)

*↑ この回の図*

[![動画(60 コマ、30 fps で撮った 2 秒を 1/3 の速さで再生): 左上 = 斜めカメラ(泡が右へ流れ、空の映り込みは動かない)、右上 = 既知ホモグラフィで正射化したコマと、いま足した対の PIV 変位(矢印 × 8)。下段は対](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/13_accumulate_pairs.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/13_accumulate_pairs.gif)

*↑ 動く図 ―― 動画(60 コマ、30 fps で撮った 2 秒を 1/3 の速さで再生): 左上 = 斜めカメラ(泡が右へ流れ、空の映り込みは動かない)、右上 = 既知ホモグラフィで正射化したコマと、いま足した対の PIV 変位(矢印 × 8)。下段は対を 1 つずつ足した平均から出した表面流速 u(y)(橙)と流量 Q の推移。1 対だけで Q = 11.68 m³/s(-7.3 %)、本文と同じ 20 対で 11.62 m³/s(-7.8 %、閉形式 12.6)、59 対で 11.63 m³/s(-7.7 %)—— **対を足しても流量の誤差はほとんど動かない**。平均で減るのは偶然誤差だけで、u(y) が真値より低めに出る偏りと岸 0 の台形則(だけで約 -2.5 %)は残る。紫は斜め画像のまま 1 尺度で直したゼロ点(近岸で速く遠岸で遅い)*

```
py -3.11 examples/poc_river_surface_velocity.py
```

ソース: [examples/poc_river_surface_velocity.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_river_surface_velocity.py)

この回が作った図は全部で **13 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_river_surface_velocity)

使用 op(ノートへ): [`arrow`](https://furuse.work/ops/annotate/pointer/arrow.html) · [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`highpass_image`](https://furuse.work/ops/2d/frequency/highpass_image.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`piv_ensemble_correlate`](https://furuse.work/ops/piv/estimate/piv_ensemble_correlate.html) · [`piv_error_stats`](https://furuse.work/ops/piv/assess/piv_error_stats.html) · [`piv_outlier_mask`](https://furuse.work/ops/piv/validate/piv_outlier_mask.html) · [`piv_replace_outliers`](https://furuse.work/ops/piv/validate/piv_replace_outliers.html) · [`piv_sample_at_windows`](https://furuse.work/ops/piv/assess/piv_sample_at_windows.html) · [`piv_to_velocity`](https://furuse.work/ops/piv/field/piv_to_velocity.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`sigma_clip_stack`](https://furuse.work/ops/astrostack/stack/sigma_clip_stack.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html) · [`warp_by_plane`](https://furuse.work/ops/3d/plane_sweep_stereo/warp_by_plane.html)

## No.2026.035 —— 海氷密接度 ―― 混合画素をどう数えるかで答えが変わる

[![海氷密接度 ―― 混合画素をどう数えるかで答えが変わる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sea_ice_concentration/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sea_ice_concentration/01_scene.png)

*↑ **海氷密接度 ―― 混合画素をどう数えるかで答えが変わる** ―― PSF でぼかした海氷/水の 2 バンド像から密接度を硬い分類と線形混合分解で出した図。硬い分類は -4.2 ポイント、分解は +0.02 ポイント。偏りは周長率で説明がつき(R² = 0.984)、密接度 0.49 付近でゼロを横切る ―― そこだけで検証すると合格する。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sea_ice_concentration/02_bias_vs_threshold_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sea_ice_concentration/02_bias_vs_threshold.png)

*↑ 測定の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sea_ice_concentration/03_bias_vs_concentration_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sea_ice_concentration/03_bias_vs_concentration.png)

*↑ この回の図*

[![下 3 段は端成分 5 % 誤差と薄氷 20 %(2 端成分の分解)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sea_ice_concentration/04_summary_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sea_ice_concentration/04_summary.png)

*↑ 下 3 段は端成分 5 % 誤差と薄氷 20 %(2 端成分の分解)。*

```
py -3.11 examples/poc_sea_ice_concentration.py
```

ソース: [examples/poc_sea_ice_concentration.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_sea_ice_concentration.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_sea_ice_concentration)

使用 op(ノートへ): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`mat_lstsq`](https://furuse.work/ops/math/linalg/mat_lstsq.html)

## No.2026.110 —— 走査幅 ―― 空撮画像から測った 1 本の数字が、捜索計画の成否を決める

[![走査幅 ―― 空撮画像から測った 1 本の数字が、捜索計画の成否を決める](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_search_sweep_width/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_search_sweep_width/01_scene.png)

*↑ **走査幅 ―― 空撮画像から測った 1 本の数字が、捜索計画の成否を決める** ―― 空撮画像から**横距離曲線** p(x)(機体直下からの横方向距離ごとの検出確率)を測り、その面積 **W = ∫p dx** を走査幅として捜索計画に渡す。画像処理と意思決定が 1 本の数字でつながる場所。★まず**走査幅の定義そのものを実証**した: 形の違う 4 本の曲線(実測 p / 幅 W の矩形 / 底辺 2W の三角形 / 二峰形)を同じ面積 **256.2 m** に揃えると、半幅 500 m に一様に撒いた目標の検出割合は 0.2559 / 0.2563 / 0.2556 / 0.2566 —— **4 つとも予測 0.2562 の 0.8σ 以内**。**曲線の形は消え、面積だけが残る**。これが 1 本の数字を計画に渡せる理由。★崖は被覆率 C = W·v·t/A = 1。閉形式を**先に印字**して min(1,C) = **1.0000**、1-exp(-C) = **0.6321**。矩形の対照群の実測は 1.0000 / 0.6348(+0.005 は航跡が有限本 n=64 だからで、厳密式 1-(1-W/Wd)^64 = 0.6350)。★★**予測を 4 つ外した**。(1) 実測の p を入れると平行捜索は **0.8464** で 1.000 に届かない —— min(1,C) は p が幅 W の**矩形**であること(定値域則)に依存していて、裾を引く実曲線では隣の航跡と裾が重なる。(2)「平らな曲線のほうが矩形に近く平行捜索に強い」は**逆**だった(0.7705 対 0.8464)。矩形に近いとは『平ら』ではなく『W の内側に立ち、外へ裾を引かない』こと(支持域/W が 2.40 対 2.25)。★同じ 2 本が**ランダム捜索では一致する**(0.6371 対 0.6357)—— ランダム捜索は面積しか見ない。(3)「端は解像度が落ちる」—— ナディア向きの中心投影では**地上分解能は端まで一定**(相対ばらつき 0.0e+00)。落ちるのは cos^4・大気・軸外ぼけのほうで、f-theta 光学なら端は 2.132 倍粗くなる。(4)「背景を引けば良くなる」—— 画像全体の中央値と σ で割るのは**アフィン変換なので順位が変わらない**(174.4 → 172.0 m)。効くのは**場所ごと**に引いたときだけ(239.6 m)。★**最適高度は内点に来た**(220 m で W = 258.1 ± 4.0 m)。ただし 220 m と 300 m は標準誤差内で**測り分けられていない**と正直に書いた。低高度側で落ちる理由は解像度ではなく**掃引幅そのもの**(高度 100 m では視野の端でも p = 0.707 のまま切れており W は下限値)。掃引速度 W·v で見ると、v ∝ min(1, h/600) の機体では最適が **420 m** へ動く —— **『高度を下げて W を上げる』は成り立たない**(下げると掃引幅が縮み、機体によっては速度まで落ちる)。★★**見張り役**: 検出率だけ見ていると誤検出が見えない。誤検出は端ではなく**直下に集中**する(0-32 m 帯 **113 件** / 最外 256-288 m 帯 **0 件**)—— 目標も白波も同じ cos^4・同じ大気で暗くなるので、**いちばんよく見える所がいちばん吠える**。同じ画像・同じ検出器で閾値だけ動かすと W は **406 m から 170 m** まで動く(誤検出 22.9 件/枚 → 0.37 件/枚)。**『走査幅 400 m』という報告は、誤検出率が書いていなければ何も言っていない**。★対照群は差 ± σ つきで並べた: 白波 +107.1±5.6、cos^4 +65.5±6.6、軸外ぼけ +48.6±6.2 に対し、**大気 +6.0±5.9 は 1.0σ で「効いている」と言えない**。足し算にもならない。★素材側の穴も 1 つ踏んだ: 点源を画素中心 1 点で標本すると**総フラックスの誤差は 4.6e-07 なのにピーク値が σ=0.9 px で 10.6 % 過大**になり、σ が横距離で変わるので横距離曲線そのものが傾く。**総和が合っていることは、山の高さが合っている証拠にならない** —— erf で画素を厳密積分するよう直した。★★道具の穴を 4 つ見つけ、**うち 1 つはその場で埋めた**: 点状目標の座標を返す 2-D op は `star_detect` だけなのに、「小さい目標 検出」「スポット 検出」「漂流 捜索」では op_find が **0 件**だった。掛けて見ると原因は名前ではなく **op_find 側** —— 語の切り出しが `[a-z0-9]+` の ASCII 限定で和文は語が 1 つも取れず、採点する doc も docstring の **1 行目だけ**(30 文字)。**和文の複数語クエリは構造的に必ず 0 件**になっていた。CJK の連なりを語として取り 2-gram で按分する段を「既存の点が 0 のときだけ」足し、採点対象を docstring 全文へ広げ、star_detect に「名前は天体だが中身は分野中立」と書いた。いまは同じ和文で 1〜2 位に出る(ただし「点 検出」は今も出ない —— 「点」1 文字は輪郭 op の説明にも必ず出るため。限界も隠さない)。*

[![半幅 500 m に一様に撒いた 400000 個。予測 W/2X = 0.2562、モンテカルロの標準偏差 0.0007。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_search_sweep_width/02_sweep_width_equivalence_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_search_sweep_width/02_sweep_width_equivalence.png)

*↑ 測定の図 ―― 半幅 500 m に一様に撒いた 400000 個。予測 W/2X = 0.2562、モンテカルロの標準偏差 0.0007。*

[![4 本とも面積 = W = 256 m。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_search_sweep_width/03_curve_shapes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_search_sweep_width/03_curve_shapes.png)

*↑ 4 本とも面積 = W = 256 m。*

[![完全平行は C=1 でちょうど 0 に落ちるが、実測の横距離曲線では 0.154 残る(裾が隣の航跡と重なるため)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_search_sweep_width/05_coverage_curves_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_search_sweep_width/05_coverage_curves.png)

*↑ 完全平行は C=1 でちょうど 0 に落ちるが、実測の横距離曲線では 0.154 残る(裾が隣の航跡と重なるため)。*

[![だから走査幅は必ず誤検出率と対で報告する。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_search_sweep_width/08_threshold_tradeoff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_search_sweep_width/08_threshold_tradeoff.png)

*↑ だから走査幅は必ず誤検出率と対で報告する。*

[![3 本とも誤検出 1.0 件/枚。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_search_sweep_width/10_lateral_range_curves_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_search_sweep_width/10_lateral_range_curves.png)

*↑ 3 本とも誤検出 1.0 件/枚。*

```
py -3.11 examples/poc_search_sweep_width.py
```

ソース: [examples/poc_search_sweep_width.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_search_sweep_width.py)

この回が作った図は全部で **12 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_search_sweep_width)

使用 op(ノートへ): [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`gray_tophat`](https://furuse.work/ops/2d/morphology/gray_tophat.html) · [`integrate_funct_1d`](https://furuse.work/ops/oned/function/integrate_funct_1d.html) · [`laplace`](https://furuse.work/ops/2d/edges/laplace.html) · [`ncc_locate`](https://furuse.work/ops/2d/matching/ncc_locate.html) · [`noise_sigma`](https://furuse.work/ops/astrostack/quality/noise_sigma.html) · [`photon_sample`](https://furuse.work/ops/photon/counting/photon_sample.html) · [`relative_illumination`](https://furuse.work/ops/optics/geometric/relative_illumination.html) · [`star_detect`](https://furuse.work/ops/astrostack/photometry/star_detect.html) · [`tophat`](https://furuse.work/ops/2d/morphology/tophat.html) · [`vignette`](https://furuse.work/ops/gfx2d/post/vignette.html) · [`xsk_blob_log`](https://furuse.work/ops/2d/features/xsk_blob_log.html)

## No.2026.036 —— 縁が暗い天体の輪郭はどこか ―― 周辺減光があると「50 % 法」は半径を小さく見る

[![縁が暗い天体の輪郭はどこか ―― 周辺減光があると「50 % 法」は半径を小さく見る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_limb_darkening/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_limb_darkening/01_scene.png)

*↑ **縁が暗い天体の輪郭はどこか ―― 周辺減光があると「50 % 法」は半径を小さく見る** ―― 周辺減光つきの太陽面をシーイング越しに撮り、縁の半径を 50 % 法・勾配最大・モデル当てはめで測った図。「偏りは減光係数に比例」の予想は外れ、u = 0.8 で -12.76 px(幾何だけの予測 -13.14 px)。しきい値 0.26 付近でぼけの影響が消える打ち消し点は、u を変えると 0.38 へ動く。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_limb_darkening/02_bias_vs_u_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_limb_darkening/02_bias_vs_u.png)

*↑ 測定の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_limb_darkening/03_seeing_cancel_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_limb_darkening/03_seeing_cancel.png)

*↑ この回の図*

[![縁に載った黒点だけが効く(内側の黒点は縁の点列に入らない)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_limb_darkening/04_sunspot_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_limb_darkening/04_sunspot.png)

*↑ 縁に載った黒点だけが効く(内側の黒点は縁の点列に入らない)。*

```
py -3.11 examples/poc_solar_limb_darkening.py
```

ソース: [examples/poc_solar_limb_darkening.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_solar_limb_darkening.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_solar_limb_darkening)

使用 op(ノートへ): [`edge_points`](https://furuse.work/ops/3d/edges/edge_points.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`mat_lstsq`](https://furuse.work/ops/math/linalg/mat_lstsq.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html)

## No.2026.037 —— 星の位置は何分の 1 画素まで測れて、どこで崖に落ちるか

[![星の位置は何分の 1 画素まで測れて、どこで崖に落ちるか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_star_astrometry/03_starfield_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_star_astrometry/03_starfield.png)

*↑ **星の位置は何分の 1 画素まで測れて、どこで崖に落ちるか** ―― 既知の天球座標から描いた星の位置を 4 手法で測り、Fisher 情報の理論限界と比べた図。S/N 298 で重心(ゼロ点)は理論の 5.56 倍、背景引き重心は 1.03 倍で、限界を上回った手法は無い。暗い端でゼロ点が限界を下回って見える(0.2790 px 対 0.3471 px)のは、感度 0.038 で初期値の四捨五入を返しているだけ。*

[![暗い端で素の重心が下限を割って見えるのは「動かない推定器」だから(感度 0.038)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_star_astrometry/01_snr_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_star_astrometry/01_snr_sweep.png)

*↑ 測定の図 ―― 暗い端で素の重心が下限を割って見えるのは「動かない推定器」だから(感度 0.038)。*

[![素の重心だけ FWHM に依らない(空の希釈)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_star_astrometry/02_phase_systematic_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_star_astrometry/02_phase_systematic.png)

*↑ 素の重心だけ FWHM に依らない(空の希釈)。*

[![混ぜた中央値は孤立星とも二重星とも違う「どこでもない値」。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_star_astrometry/04_sky_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_star_astrometry/04_sky_error.png)

*↑ 混ぜた中央値は孤立星とも二重星とも違う「どこでもない値」。*

```
py -3.11 examples/poc_star_astrometry.py
```

ソース: [examples/poc_star_astrometry.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_star_astrometry.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_star_astrometry)

使用 op(ノートへ): [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`noise_sigma`](https://furuse.work/ops/astrostack/quality/noise_sigma.html) · [`psf_fit`](https://furuse.work/ops/astrostack/photometry/psf_fit.html) · [`star_detect`](https://furuse.work/ops/astrostack/photometry/star_detect.html)

## No.2026.088 —— 年輪を数えて幅の時系列を取り出す ―― 年数の誤差と幅の相関は別の量

[![年輪を数えて幅の時系列を取り出す ―― 年数の誤差と幅の相関は別の量](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/01_scene.png)

*↑ **年輪を数えて幅の時系列を取り出す ―― 年数の誤差と幅の相関は別の量** ―― 偏心した髄・偏心成長・周方向のうねり・うねる割れ目・腐朽斑・木目・ぼけを載せた 36 年の円板を閉形式で仕込み、髄から 1 本の放射線のピーク数(ゼロ点)と、極座標展開+外縁で半径を正規化+θ 方向メディアン+24 扇形の測定線の合意(中央値)を比べた。ゼロ点は 24 方向中 18 方向でしか年数が合わないが、間違えた 6 方向でも幅の相関は中央値 0.900。合意法は 36 年・欠落 0・幅の相関 0.996(平均誤差 0.13 px)。髄の推定誤差 20 px でも幅の相関は 0.994 ―― cos で変調されるのは半径(傾き -14.9 px)で幅(-0.02 px)ではなく、減るのは髄近くの年数(予測 2 / 実測 2)。細い年輪は合意法 2.5 px、ゼロ点 3.0 px から落ち、ぼけ σ 4 px でゼロ点は偽輪 13 本を数える。*

[![偏心成長で境界が θ とともに斜めに走るので、正規化しないとθ 窓の中で外側の年輪がにじむ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/02_polar_stages_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/02_polar_stages.png)

*↑ 測定の図 ―― 偏心成長で境界が θ とともに斜めに走るので、正規化しないとθ 窓の中で外側の年輪がにじむ。*

[![展開図(横 = 半径 px、縦 = 角度)に、扇形ごとの測定線が拾った境界(赤、下)と真値(青、上)を重ねた。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/03_polar_edges_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/03_polar_edges_map.png)

*↑ 展開図(横 = 半径 px、縦 = 角度)に、扇形ごとの測定線が拾った境界(赤、下)と真値(青、上)を重ねた。*

[![ゼロ点は θ=0 方向の局所幅なので偏心成長ぶん尺度がずれる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/04_ring_widths_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/04_ring_widths.png)

*↑ ゼロ点は θ=0 方向の局所幅なので偏心成長ぶん尺度がずれる。*

[![幅系列の相関はほぼ動かない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/06_cliff_pith_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/06_cliff_pith_error.png)

*↑ 幅系列の相関はほぼ動かない。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/08_cliff_blur_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/08_cliff_blur.png)

*↑ この回の図*

```
py -3.11 examples/poc_tree_ring_dendro.py
```

ソース: [examples/poc_tree_ring_dendro.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_tree_ring_dendro.py)

この回が作った図は全部で **9 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_tree_ring_dendro)

使用 op(ノートへ): [`derivate_funct_1d`](https://furuse.work/ops/oned/function/derivate_funct_1d.html) · [`find_peaks`](https://furuse.work/ops/oned/signal/find_peaks.html) · [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`median_rect`](https://furuse.work/ops/2d/rank/median_rect.html) · [`polar_unwrap`](https://furuse.work/ops/3d/curvilinear/polar_unwrap.html) · [`smooth_funct_1d_gauss`](https://furuse.work/ops/oned/function/smooth_funct_1d_gauss.html)

## No.2026.046 —— 畑の緑を数える ―― 被覆率の真値を画素ごとの葉の面積率で持つ

[![畑の緑を数える ―― 被覆率の真値を画素ごとの葉の面積率で持つ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vegetation_cover/01_mixed_pixel_response_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vegetation_cover/01_mixed_pixel_response.png)

*↑ **畑の緑を数える ―― 被覆率の真値を画素ごとの葉の面積率で持つ** ―― 4 バンドの圃場像から被覆率を出し、画素ごとの葉の面積率を真値にした図。ゼロ点(緑チャネルに大津)は中期で +16.3 pp 上振れし、散らばりはどの手法も 0.5 pp 以下なので、効いている差はほぼ全部が偏り。発芽期・湿った土では被覆率の偏り -0.2 pp なのに適合率も再現率も 0.000 ―― 数字だけ合っていて画素が 1 つも当たっていない。*

[![影ゼロならゼロ点も悪くない。影は『暗さ』を手掛かりにする手法に直接刺さる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vegetation_cover/02_shadow_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vegetation_cover/02_shadow_sweep.png)

*↑ 測定の図 ―― 影ゼロならゼロ点も悪くない。影は『暗さ』を手掛かりにする手法に直接刺さる。*

[![純粋な葉が 67 % ある場面。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vegetation_cover/03_ppi_noise_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vegetation_cover/03_ppi_noise.png)

*↑ 純粋な葉が 67 % ある場面。*

[![白い画素の数だけが釣り合っている。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vegetation_cover/04_wet_soil_zero_hits_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vegetation_cover/04_wet_soil_zero_hits.png)

*↑ 白い画素の数だけが釣り合っている。*

```
py -3.11 examples/poc_vegetation_cover.py
```

ソース: [examples/poc_vegetation_cover.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_vegetation_cover.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_vegetation_cover)

使用 op(ノートへ): [`cv_otsu`](https://furuse.work/ops/2d/segmentation/cv_otsu.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`sk_otsu`](https://furuse.work/ops/2d/segmentation/sk_otsu.html)

## No.2026.049 —— 河川の水位を斜め写真から測る ―― 透視を無視した「行番号」は弓なりに外れる

[![河川の水位を斜め写真から測る ―― 透視を無視した「行番号」は弓なりに外れる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_water_level/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_water_level/01_scene.png)

*↑ **河川の水位を斜め写真から測る ―― 透視を無視した「行番号」は弓なりに外れる** ―― 量水標を斜めから撮った像で水面線を検出し、水位に直した図。目盛り 2 点の線形換算は最大 -6.4 cm(水位 1.00 m)弓なりに外れ、符号は水位でなく内挿(-6.6 cm)か外挿(+16.3 cm)かで決まる。4 点ホモグラフィなら 0.2 cm 以下で、残るのは透視でなく水面線の検出誤差。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_water_level/02_bias_vs_level_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_water_level/02_bias_vs_level.png)

*↑ 測定の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_water_level/03_anchors_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_water_level/03_anchors.png)

*↑ この回の図*

[![負 = 低く読む。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_water_level/04_reflection_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_water_level/04_reflection.png)

*↑ 負 = 低く読む。*

```
py -3.11 examples/poc_water_level.py
```

ソース: [examples/poc_water_level.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_water_level.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_water_level)

使用 op(ノートへ): [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`mat_svd`](https://furuse.work/ops/math/linalg/mat_svd.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`projective_trans_image`](https://furuse.work/ops/2d/geometry/projective_trans_image.html) · [`ransac_line`](https://furuse.work/ops/3d/robust_fit/ransac_line.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html)

## No.2026.217 —— 火星の実地形で車輪の滑りを不確かさ付きで予測し、滑りのリスクを避ける経路を引く ―― Bekker / Wong–Reece と CVaR、地形は HiRISE の DTM、ガウス過程はデータの外で立ち往生を「滑り 0.29」と答える

[![火星の実地形で車輪の滑りを不確かさ付きで予測し、滑りのリスクを避ける経路を引く ―― Bekker / Wong–Reece と CVaR、地形は HiRISE の DTM、ガウス過程はデータの外で立ち往生を「滑り 0.29」と答える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rover_slip_risk_path/07_two_soils_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rover_slip_risk_path/07_two_soils_scene.png)

*↑ **火星の実地形で車輪の滑りを不確かさ付きで予測し、滑りのリスクを避ける経路を引く ―― Bekker / Wong–Reece と CVaR、地形は HiRISE の DTM、ガウス過程はデータの外で立ち往生を「滑り 0.29」と答える** ―― 柔らかい砂の上では車輪が回っても車体はその分だけ進まず(滑り率 s)、斜面が急になると立ち往生する。既存の terrain.traversability は幾何だけで、土が支えきれない効果を持っていなかった。学習なしの土の力学と軽い統計で、Bekker の圧力–沈下 → Wong–Reece の剛な車輪の応力の数値積分 → 斜面の角ごとの定常の滑り率 → 地面を見るカメラの並進と車輪の回転から実際の滑り率 → 滑りの不確かさ(分位点回帰 + 共形の補正、ガウス過程)→ CVaR で割り引いた辺の所要時間のコスト地図と 8 近傍の Dijkstra。閉形式: τ = 0 の牽引 = −Bekker の締め固め抵抗を 1.9e-7。乾いた砂(火星の重力、50 kg・4 輪)は 20° で滑り 0.219、登れる最大 25.2°、剛な地面の極限 26.35°(MuJoCo の剛体の車輪 25.83°、砂では一致しない)。視覚オドメトリの滑り率 最大 0.0034。名目 90 % の帯の被覆は分位点回帰 0.915、ガウス過程は 8° 以上で 0.780 しか覆わず緩斜面で 0.992 と広すぎ、データの外の 32° を「滑り 0.29」と答える(真は立ち往生)。HiRISE の DTM(Balvicar クレーターの中央丘、パブリックドメイン、repo の外・FULLSEYE_ROVERSLIP_DATA)の上で平均の最短 672 m / リスク最小 696 m、平均の時間 +1.1 %、真の滑りで立ち往生の確率 2.23 % → 0.05 %。罠: Bekker の教科書の沈下の式 (3 − n)/3 は n = 1.9 で 17 % 深い、0.4.0 の phase_correlation_fft(窓なし・全白色化)は周期的でない地面の切り出しで (1, 0) を返した(真は (−2, −5)、2026-10-06 に既定を直した)。正直に: 滑りの真値は合成、土の種類は分からない、1 種の土では 2 経路はほとんど重なる。門 18 本(データ無し・mujoco 無しの CI は 15 本、3.1 s、曲線 5° 刻み・学習データは観測のまま)、図の実行と --full は 1° 刻み・学習データを視覚オドメトリ経由。*

[![real Mars terrain at 1:1 pixels: the mean-slip shortest path and the minimum slip-risk path](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rover_slip_risk_path/01_dtm_two_paths_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rover_slip_risk_path/01_dtm_two_paths.png)

*↑ 測定の図 ―― real Mars terrain at 1:1 pixels: the mean-slip shortest path and the minimum slip-risk path*

[![the risk-aware path trims the peaks of the upper band at almost no extra length](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rover_slip_risk_path/02_slip_band_along_paths_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rover_slip_risk_path/02_slip_band_along_paths.png)

*↑ the risk-aware path trims the peaks of the upper band at almost no extra length*

[![GP's uniform noise is too wide on gentle slopes, too narrow on steep ones, and reverts to the mean p](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rover_slip_risk_path/04_slip_band_gp_vs_quantile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rover_slip_risk_path/04_slip_band_gp_vs_quantile.png)

*↑ GP's uniform noise is too wide on gentle slopes, too narrow on steep ones, and reverts to the mean past the data*

[![the slope a wheel can hold is where DP/W reaches sin(slope)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rover_slip_risk_path/05_traction_slip_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rover_slip_risk_path/05_traction_slip.png)

*↑ the slope a wheel can hold is where DP/W reaches sin(slope)*

[![no sinkage, no shear deformation: a rigid-contact simulator cannot show soft-soil slip](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rover_slip_risk_path/06_mujoco_vs_wong_reece_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rover_slip_risk_path/06_mujoco_vs_wong_reece.png)

*↑ no sinkage, no shear deformation: a rigid-contact simulator cannot show soft-soil slip*

[![as the rover drives, measured slips tighten the slip-vs-slope band (quantile regression, 90 %)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rover_slip_risk_path/03_rover_slip_update.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rover_slip_risk_path/03_rover_slip_update.gif)

*↑ 動く図 ―― as the rover drives, measured slips tighten the slip-vs-slope band (quantile regression, 90 %)*

```
py -3.11 examples/poc_rover_slip_risk_path.py
```

ソース: [examples/poc_rover_slip_risk_path.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_rover_slip_risk_path.py)

この回が作った図は全部で **7 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_rover_slip_risk_path)

使用 op(ノートへ): [`bekker_wheel_sinkage`](https://furuse.work/ops/drive/roverslip/bekker_wheel_sinkage.html) · [`cvar_cost_map`](https://furuse.work/ops/drive/roverslip/cvar_cost_map.html) · [`fbm_height`](https://furuse.work/ops/drive/terrain/fbm_height.html) · [`fbm_params`](https://furuse.work/ops/drive/terrain/fbm_params.html) · [`ground_shift_track`](https://furuse.work/ops/drive/roverslip/ground_shift_track.html) · [`odometry_slip`](https://furuse.work/ops/drive/roverslip/odometry_slip.html) · [`path_slip_risk`](https://furuse.work/ops/drive/roverslip/path_slip_risk.html) · [`risk_aware_path`](https://furuse.work/ops/drive/roverslip/risk_aware_path.html) · [`slip_gp_fit`](https://furuse.work/ops/drive/roverslip/slip_gp_fit.html) · [`slip_predict`](https://furuse.work/ops/drive/roverslip/slip_predict.html) · [`slip_quantile_fit`](https://furuse.work/ops/drive/roverslip/slip_quantile_fit.html) · [`slope_slip_curve`](https://furuse.work/ops/drive/roverslip/slope_slip_curve.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`wheel_forces`](https://furuse.work/ops/drive/roverslip/wheel_forces.html) · [`wheel_sinkage`](https://furuse.work/ops/drive/roverslip/wheel_sinkage.html) · [`wheel_traction_curve`](https://furuse.work/ops/drive/roverslip/wheel_traction_curve.html)

## No.2026.136 —— 高さは 2 つある・実データ編 ―― 公開された測量成果 523 点で、高さの取り違えを検出器にかける

[![高さは 2 つある・実データ編 ―― 公開された測量成果 523 点で、高さの取り違えを検出器にかける](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_benchmarks_real/03_misuse_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_benchmarks_real/03_misuse.png)

*↑ **高さは 2 つある・実データ編 ―― 公開された測量成果 523 点で、高さの取り違えを検出器にかける** ―― 合成(poc_geodetic_height_frames)では「楕円体高と標高を混ぜると 30〜40 m ずれる」を**自分で作った数字**で示した。ここは同じ主張を**他人が測って公開した値**で確かめる回。NOAA/NGS の datasheet は 1 つの基準点について楕円体高 h(NAD 83(2011))・正標高 H(NAVD 88)・ジオイド高 N(GEOID18)・地心直交座標 (x,y,z) を**全部公開している**ので、コロラド州フロントレンジ(ロッキーの縁 = ジオイドの勾配が大きく、補間の誤差が出るなら出る場所)から 523 点を取った。★**既存 op を外の値と突き合わせた**: dem_geodetic_to_ecef は公開されている (x,y,z) と rms 0.5 mm・最大 0.8 mm で一致。逆変換は最大 7.1e-09 度ずれるが、これは公開座標の mm 丸めが作る床 9.0e-09 度の内側 —— **データより細かい一致は観測できない**。この op はこれまで自分との往復しか測っておらず、往復は実装が一貫していることしか言わない。★**粗い格子を引く誤りのほうが、モデルを 1 世代取り違える誤りより大きい**: 0.25 度の GEOID18 格子をdem_geoid_height で双一次補間した値と同じ点の公開値の差は rms 11.1 cm・最大 44.5 cm、いっぽうGEOID18 と旧 GEOID12B のモデル差は平均 −1.0 cm(幅 −9.8〜+6.3 cm)。格子を細かくするほうが先に効く。★**格子の外は端で埋めず拒否する**: 523 点のうち 15 点が外に落ち、拒否が実際に働いた(外挿した undulation は測量値ではない)。★**取り違えは外れ値に見えない**: 楕円体高をそのまま標高の列に入れると、残差は**全点が例外なく直線 −N に乗り**中央値 16.75 m 持ち上がる —— 桁で間違うのではなく全部が同じだけずれるので、数字を眺めても気づけない。★★**残差は測量の等級を、言われないまま並べ替える**: dem_height_frame_residual は成果の由来を 1 文字も読まないのに、|h−H−N| の中央値は水準測量 1.6 cm < 網調整 1.9 cm < GPS 観測 3.8 cm < VERTCON3(モデルによる基準換算)8.3 cm・最大 1.02 m の順に並ぶ。**基準が噛み合っているかを数えるだけで、由来の弱い点が浮く。** なお公開値どうしでも残差はぴったり 0 ではない(rms 10.6 cm): NAVD 88 は水準、GEOID18 は重力から作られていて、その食い違いが出る。局所 ENU は基準点が厳密に原点、往復は緯度 1.4e-14 度、既存 ECEF op を経由した別経路と 1.5e-11 m で一致し、20 km より遠い 461 点は接平面から平均 372 m 沈む(誤差ではなく地球の丸み)。同梱するのは集計 1 枚(点ごとに 10 列 + ジオイド格子 2 枚、56 KB)で、生データは commit しない。*

[![523 NGS marks, each publishing ellipsoidal height h (NAD 83), orthometric height H (NAVD 88) and geoid height N (GEOID18](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_benchmarks_real/01_residual_sorted_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_benchmarks_real/01_residual_sorted.png)

*↑ 測定の図 ―― 523 NGS marks, each publishing ellipsoidal height h (NAD 83), orthometric height H (NAVD 88) and geoid height N (GEOID18). The residual h - H - N is not exactly zero: NAVD 88 and GEOID18 were built from different measurements, and the mismatch shows up here at the centimetre level (rms 0.106 m, median -0.004 m). 74 of 523 marks exceed 0.1 m*

[![dem_height_frame_residual reads only the three height columns — never the metadata saying how each m](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_benchmarks_real/02_by_provenance_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_benchmarks_real/02_by_provenance.png)

*↑ dem_height_frame_residual reads only the three height columns — never the metadata saying how each mark was measured.*

[![the published GEOID18 undulation on a 0.25-degree grid over the Colorado Front Range (-19.40 to -11.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_benchmarks_real/04_geoid_grid_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_benchmarks_real/04_geoid_grid.png)

*↑ the published GEOID18 undulation on a 0.25-degree grid over the Colorado Front Range (-19.40 to -11.15 m, 9x7 nodes).*

[![GEOID18 minus GEOID12B on the same nodes: mean -0.010 m, range -0.098 to +0.063 m.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_benchmarks_real/06_model_shift_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_benchmarks_real/06_model_shift.png)

*↑ GEOID18 minus GEOID12B on the same nodes: mean -0.010 m, range -0.098 to +0.063 m.*

[![523 marks placed in the east-north-up frame of one of them (AB3303).](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_benchmarks_real/08_enu_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_benchmarks_real/08_enu_map.png)

*↑ 523 marks placed in the east-north-up frame of one of them (AB3303).*

```
py -3.11 examples/poc_geodetic_benchmarks_real.py
```

ソース: [examples/poc_geodetic_benchmarks_real.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_geodetic_benchmarks_real.py)

この回が作った図は全部で **9 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_geodetic_benchmarks_real)

使用 op(ノートへ): [`dem_datum_shift_3param`](https://furuse.work/ops/dem/geodesy/dem_datum_shift_3param.html) · [`dem_ecef_to_geodetic`](https://furuse.work/ops/dem/geodesy/dem_ecef_to_geodetic.html) · [`dem_enu_from_geodetic`](https://furuse.work/ops/dem/geodesy/dem_enu_from_geodetic.html) · [`dem_geodetic_from_enu`](https://furuse.work/ops/dem/geodesy/dem_geodetic_from_enu.html) · [`dem_geodetic_to_ecef`](https://furuse.work/ops/dem/geodesy/dem_geodetic_to_ecef.html) · [`dem_geoid_height`](https://furuse.work/ops/dem/geodesy/dem_geoid_height.html) · [`dem_height_frame_convert`](https://furuse.work/ops/dem/geodesy/dem_height_frame_convert.html) · [`dem_height_frame_residual`](https://furuse.work/ops/dem/geodesy/dem_height_frame_residual.html)

## No.2026.147 —— 重力レンズの像を、産業用の測定 op で採点する

[![重力レンズの像を、産業用の測定 op で採点する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gravitational_lens_invariants/01_images_vs_u_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gravitational_lens_invariants/01_images_vs_u.png)

*↑ **重力レンズの像を、産業用の測定 op で採点する** ―― **重力レンズには、絵から直接測れる厳密な不変量がある** —— しかも測る道具はこの箱にある平凡な 2-D の op(連結成分・面積・重心)でよい。点質量レンズをアインシュタイン半径 1 の単位で書くと、光源位置 `u` に対し像は `θ± = (u ± √(u²+4))/2`、倍率は `μ± = (u²+2)/(2u√(u²+4)) ± 1/2` になり、**光源がどこにあっても** `θ₊·θ₋ = −1` と **`μ₊ − μ₋ = 1`(整数)** が成り立つ。9 通りの光源位置で前者は **8.9e-16**、後者は **2.2e-16** しか動かない。★★芯 1: **その整数が、絵から出る。** 像面の画素を光源面へ引き戻して描いた絵を `blob_label` で 2 つの像に分け、面積を測って引き算すると、`μ₊ − |μ₋|` の 1 からのずれが格子 801 → 1601 → 3201 で **0.0660 → 0.0216 → 0.0126** と縮む —— モデルの数字ではなく**描いた絵を測って**出している。★★芯 2: **面輝度は厳密に変わらない。** リウヴィルの定理どおり、像の内部の値は u を振っても **1.000000000000000** のままで、変わるのは面積だけ(2,322 → 480 画素)。同じ 1 枚から「変わらない量」と「変わる量」が同時に出る。★★芯 3: **環の太さは光源の半径に等しい。** アインシュタイン環の上では動径方向の倍率が厳密に 1/2 なので、半径 ρ の光源は太さ ρ の環になる(4 通りで最大のずれ **7.2e-05**)。★★芯 4: **特異点がちょうど 1 画素の偽の像を作る。** 光源が真後ろ(u = 0)のとき像は環 **1 本**のはずなのに、連結成分は **2 個**になる —— 増えた 1 個はレンズ中心の 1 画素で、そこは偏向角が発散する点。**個数を数える門は、ここで嘘をつく。** ★★芯 5: **外した予言を 2 つ残してある。** (a)「絵から測るのが苦しいのは暗い像が小さくなる u = 1.5 の側だろう」は**外れ**で、どの解像度でも **u = 0.3(焦線に近い側)が最悪**だった(u = 1.5 の暗い像は格子 3201 で 209 画素ある)—— 苦しいのは像が小さいほうではなく**引き伸ばされて細い弧になる**ほう。(b) 縁のアンチエイリアスを光源面の距離で作っていたのが系統誤差の元で、距離場を像面での変化率 `|∇d|` で割るだけで u = 0.3 のずれが **0.0214 → 0.0126** に下がった —— **写像の先で測った距離を、そのまま手前の画素に使ってはいけない。** ほかに、特異等温球では像の間隔が**光源位置に依らず 2θ_E**(4 通りで最大のずれ 9.3e-03)、光源が横切る動画では |u| ≥ 0.3 で測った倍率が閉形式と相対差 0.009 まで一致し、焦線に近い |u| < 0.3 では 0.161 まで開く(**測れる範囲を主張と一緒に出す**)。図は光源を**校正ターゲット**(同心円 4 本 + 放射スポーク 12 本)にして歪みを目で読めるようにした。**新しい op は 1 つも足していない。** 検査 20 件・図 12 枚(動く図 1 枚を含む)。*

[![面積を測るのに模様は要らない。明るいほうの像は外側(θ₊ > 1)、暗いほうは内側(|θ₋| < 1)に出て、離れるほど内側の像は小さく暗くなる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gravitational_lens_invariants/02_disc_images_vs_u_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gravitational_lens_invariants/02_disc_images_vs_u.png)

*↑ 測定の図 ―― 面積を測るのに模様は要らない。明るいほうの像は外側(θ₊ > 1)、暗いほうは内側(|θ₋| < 1)に出て、離れるほど内側の像は小さく暗くなる。*

[![9 通りの u で θ₊·θ₋ は −1 から **8.9e-16**、μ₊ − μ₋ は 1 から **2.2e-16** しか動かない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gravitational_lens_invariants/03_closed_form_invariants_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gravitational_lens_invariants/03_closed_form_invariants.png)

*↑ 9 通りの u で θ₊·θ₋ は −1 から **8.9e-16**、μ₊ − μ₋ は 1 から **2.2e-16** しか動かない。*

[![像の内部の値はどちらも厳密に **1.000000000000000**。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gravitational_lens_invariants/05_brightness_and_area_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gravitational_lens_invariants/05_brightness_and_area.png)

*↑ 像の内部の値はどちらも厳密に **1.000000000000000**。*

[![環の上では動径方向の倍率が**厳密に 1/2** なので、直径 2ρ の光源は太さ ρ の環になる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gravitational_lens_invariants/07_ring_width_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gravitational_lens_invariants/07_ring_width.png)

*↑ 環の上では動径方向の倍率が**厳密に 1/2** なので、直径 2ρ の光源は太さ ρ の環になる。*

[![重心は `blob_label` で分けた成分ごとに、被覆率で重みを付けて出している。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gravitational_lens_invariants/09_sis_separation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gravitational_lens_invariants/09_sis_separation.png)

*↑ 重心は `blob_label` で分けた成分ごとに、被覆率で重みを付けて出している。*

[![光源がレンズの裏を横切る(図は校正ターゲット)。最接近で 2 つの像が伸びて環に近づく。**倍率の数字は同じ光源位置を無地の円盤で描き直して測ったもの**で、最大 19.61 倍。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gravitational_lens_invariants/10_source_crossing.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gravitational_lens_invariants/10_source_crossing.gif)

*↑ 動く図 ―― 光源がレンズの裏を横切る(図は校正ターゲット)。最接近で 2 つの像が伸びて環に近づく。**倍率の数字は同じ光源位置を無地の円盤で描き直して測ったもの**で、最大 19.61 倍。*

```
py -3.11 examples/poc_gravitational_lens_invariants.py
```

ソース: [examples/poc_gravitational_lens_invariants.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_gravitational_lens_invariants.py)

この回が作った図は全部で **12 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_gravitational_lens_invariants)

使用 op(ノートへ): [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html)




---

**この展示館は Claude Code と一緒に作りました。** 問いと方向決めは私、実装・掃引・対照群・敵対レビューは Claude Code、という分業です。53 本の PoC を 2 日で走らせて図まで揃えられたのは、この運用のおかげです。試してみたい方は、こちらの招待リンクから **1 週間の無料トライアル** が使えます: [claude.ai/referral/0sqPw8E_lw](https://claude.ai/referral/0sqPw8E_lw)

面白い展示が 1 つでもあったら、**いいね・ストック**をもらえると助かります。どのウィングを次に増やすかは反応を見て決めるつもりなので、「自分の分野のこれが欲しい」もコメントで教えてください。実データに差し替えて崖の位置が変わった話は、いちばん聞きたい話です。
