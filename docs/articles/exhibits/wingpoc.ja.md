<!-- generated -->

### 産業検査ウィング ―― 合格の数字と不合格の数字は両立する

検査ラインの数字は合否に直結するので、1 つの指標に畳みたくなります。この部屋の 31 点は、畳んだ瞬間に消えるものを並べたものです。まとめた ROC が種類別の盲点を隠す織物、MTF が合格のまま黒レベルが不合格になる迷光、読取率だけ見ると寛容なデコーダが良く見えるバーコード。

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

[![Basler の EMVA 1288 データ 38 型番の飽和容量・暗雑音・量子効率から式 (28) で DR を出し直す。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/04_datasheet_dynamic_range_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/04_datasheet_dynamic_range.png)

*↑ Basler の EMVA 1288 データ 38 型番の飽和容量・暗雑音・量子効率から式 (28) で DR を出し直す。*

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

使用 op(ノートへ): [`contours_to_gcode`](https://furuse.work/ops/printpath/slice/contours_to_gcode.html) · [`gcode_extrusion_volume`](https://furuse.work/ops/printpath/gcode/gcode_extrusion_volume.html) · [`gcode_layer_image`](https://furuse.work/ops/printpath/gcode/gcode_layer_image.html) · [`gcode_read`](https://furuse.work/ops/printpath/gcode/gcode_read.html) · [`gcode_time_estimate`](https://furuse.work/ops/printpath/gcode/gcode_time_estimate.html) · [`gcode_write`](https://furuse.work/ops/printpath/gcode/gcode_write.html) · [`mesh_slice_contours`](https://furuse.work/ops/printpath/slice/mesh_slice_contours.html) · [`mesh_slice_stack`](https://furuse.work/ops/printpath/slice/mesh_slice_stack.html) · [`print_layer_defect_map`](https://furuse.work/ops/printpath/inspect/print_layer_defect_map.html) · [`read_3mf`](https://furuse.work/ops/printpath/format/read_3mf.html) · [`vol_render_transfer`](https://furuse.work/ops/videocube/render/vol_render_transfer.html) · [`write_3mf`](https://furuse.work/ops/printpath/format/write_3mf.html)

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

この部屋の 23 点は、符号つき距離関数の部品、インボリュート歯形、指定 PSD の粗さ面、白色干渉のスタック、解析スペックル、Frocht の応力場、対称な合成頭蓋と、いずれも閉形式か解析描画で真値を握った上で、キャリパーや相関や位相の読みを採点しています。

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

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/04_stages_area_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/04_stages_area.png)

*↑ この回の図*

[![融合した塊の数は f = 5 % を頂点に減る(塊どうしがさらに融合して 1 つになる)が、飲まれた粒の数は増え続ける。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/06_failure_area_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/06_failure_area.png)

*↑ 融合した塊の数は f = 5 % を頂点に減る(塊どうしがさらに融合して 1 つになる)が、飲まれた粒の数は増え続ける。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/08_intercept_cdf_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/08_intercept_cdf.png)

*↑ この回の図*

```
py -3.11 examples/poc_metal_grain_size.py
```

ソース: [examples/poc_metal_grain_size.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_metal_grain_size.py)

この回が作った図は全部で **9 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_metal_grain_size)

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

## No.2026.142 —— その数字のうち、いくつが測り方のものか ―― ゲージ R&R と測定の不確かさ

[![その数字のうち、いくつが測り方のものか ―― ゲージ R&R と測定の不確かさ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/01_scene.png)

*↑ **その数字のうち、いくつが測り方のものか ―― ゲージ R&R と測定の不確かさ** ―― 管理図も工程能力も**測定のばらつきを含んだままの数字**を見ている —— それを分け、1 回の測定の不確かさを報告できる形にするまでを全部「絵の外」から採点した。★平方和の分解は**代数的な恒等式**なので分散成分の出し方と独立に閉じる(相対差 1e-16)。繰り返し性は升目ごとの標本分散の平均に等しく、**既存の numpy が真値**になる。★★規格の worked example(90 点)を再現: EV 0.199933 / AV 0.226838 / GRR 0.302372 / PV 1.042327 で公表値と最大差 1.5e-06、寄与率 3.4 / 4.4 / 7.8 / 92.2 % は完全一致。★★交互作用を残すか誤差へ畳むかで **EV が 7.3 % 動く** —— どちらのモデルで出したかを返り値に載せないと、同じ工程について別の数字を返して理由が残らない。★★負の分散成分は稀な端ではなく、真値 0 のとき 40 本中 24 本で出る(丸めを申告しない実装は「差は無い」と言い切る)。★カッパは一致率ではない: 独立でたらめでも合格率 0.95 なら一致率 0.920 に対し κ は 0.101。★★**相関を無視した誤りの向きは一定でない** —— u_c(R) は 0.0702 → 0.1945(2.8 倍の過大)、u_c(X) は過小。★有効自由度は **t 表を引く直前に切り捨てる**(16.64 → 16 で k = 2.1199)。★★**正しく失敗する**: 比較損失を停留点で評価すると伝播則は u=0・区間 [0,0] を返す —— 1 次近似が情報を失う手法の限界で、モンテカルロは [0, 150]e-6。黙って 0 を返さず構造で申告する。★★4 つの矩形分布の和には Irwin-Hall の**厳密解** −3.879407 があり、正規近似を使う伝播則は 0.040521 構造的に広く出る。検査 28 件・図 9 枚。*

[![測定の行為(GRR)が総変動に占めるのは 7.8 %、部品どうしの差が 92.2 %。どちらも公表値と一致する(最大差 1.5e-06)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/02_components_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/02_components.png)

*↑ 測定の図 ―― 測定の行為(GRR)が総変動に占めるのは 7.8 %、部品どうしの差が 92.2 %。どちらも公表値と一致する(最大差 1.5e-06)。*

[![交互作用が**無い**ところ(左端)では畳むほうが真値 0.30 に近く、あるところでは畳むと交互作用を誤差に混ぜてしまうので上へ外れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/03_pooling_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/03_pooling.png)

*↑ 交互作用が**無い**ところ(左端)では畳むほうが真値 0.30 に近く、あるところでは畳むと交互作用を誤差に混ぜてしまうので上へ外れる。*

[![偏り = 0.070 -0.013 x 基準値。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/05_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/05_bias.png)

*↑ 偏り = 0.070 -0.013 x 基準値。*

[![電圧と電流の相関だけを振った(他の 2 つは実測値で固定)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/08_correlation_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/08_correlation_sweep.png)

*↑ 電圧と電流の相関だけを振った(他の 2 つは実測値で固定)。*

[![感度 c₁ = 2x₁ なので x₁=0 では 1 次近似が情報を全部失い、伝播則は [0, 0) を返す。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/11_breakdown_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/11_breakdown.png)

*↑ 感度 c₁ = 2x₁ なので x₁=0 では 1 次近似が情報を全部失い、伝播則は [0, 0] を返す。*

[![評価点 x₁ を 0 から 0.026 へ動かしたもの。★左端では真の分布が**原点に肩を持つ指数**(u²χ²₂)で、伝播則は感度 c = 2x₁ が 0 になるため区間が**1 点に潰れる**。少し動かすと今度は区間が**負の損失**へ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/12_breakdown_movie.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_measurement_system_analysis/12_breakdown_movie.gif)

*↑ 動く図 ―― 評価点 x₁ を 0 から 0.026 へ動かしたもの。★左端では真の分布が**原点に肩を持つ指数**(u²χ²₂)で、伝播則は感度 c = 2x₁ が 0 になるため区間が**1 点に潰れる**。少し動かすと今度は区間が**負の損失**へ張り出す(物理的にありえない)。さらに離れると真の分布が正規に近づき、両者はようやく重なる —— **壊れ方は連続ではなく、3 つの段階がある**。*

```
py -3.11 examples/poc_measurement_system_analysis.py
```

ソース: [examples/poc_measurement_system_analysis.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_measurement_system_analysis.py)

この回が作った図は全部で **14 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_measurement_system_analysis)

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

*↑ **骨梁の厚さ・間隔・骨体積率 ―― 平板モデルと直接法は同じ画像で別の値になる** ―― 線分の集合として閉形式で描いた 2-D 骨梁網(幅の中央値 120 µm)を、部分体積ぼけ・CT 雑音・カップ状バイアスで観測した。真値そのものが複数あり、幅の長さ加重平均 104.8 µm に対し最大内接円の定義では 121.6 µm、平板モデルは 118.4 µm ―― どの真値と比べるかで 9〜16 % が先に動く。解像度の崖は平均でなく分布に来る(画素 60 µm で分布の重なり 0.83 → 0.09、平均は量子化 -29.5 % と大津の太り +27.1 % が打ち消す)。雑音は斑点(σ 0.10 から)と途切れ(σ 0.15 から)の 2 方向から壊し、面積オープニングは斑点だけを消す。*

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

*↑ **蛍光の共局在は漏れ込みで嘘をつく ―― Pearson と Manders は別の場所で壊れる** ―― 細胞体に小胞状の点を 2 色ぶん撒き、B の点の 0 / 25 / 50 / 100 % を A と同位置に置いて真の共局在率を握る。漏れ込み行列 [[1, α], [β, 1]] と細胞質・PSF・光子雑音を掛けた観測に Pearson r と Otsu-Manders を当てると、無関係な 2 色が α=β=10 % で r=0.203、M1=0.133 になる。単染色対照から α を 0.0996(真値 0.10)と推定して線形分離すれば r は 0.007 に戻るが、Manders は 100 % でも 0.705(Otsu より下の裾が落ちる、閉形式の予想 0.756)。Pearson が 0.5 を超える崖は対称漏れ込み α=0.282(予想 2−√3=0.268)、ぼけの崖は Manders だけに来て σ=2.5 px で Otsu の前景が細胞体へ飛び移る。Costes のシャッフル検定は漏れ込みだけの r を p=0.000 で「有意」と言う。*

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

*↑ **動きの量子化 ―― 脳から筋へ、命令の次元はどこで落ちるか(ハエの首と RL の関節を同じ物差しで)** ―― 人は手を上げるとき筋肉を 1 本ずつ意識しない。脳の何万もの状態は体を動かす段階で少数の命令に畳まれているはずで、ハエではその場所が配線に見える: MaleCNS v1.0(Janelia、CC BY 4.0)で中枢脳の介在 32,164 体 → 下行ニューロン(DN)1,314 体の細い首 → 腹髄の介在 13,161 体 → 運動ニューロン(MN)708 体。conngraph に足した 4 op(graph_layer_propagate / graph_block_shuffle / states_participation_ratio / states_layer_dimension)で、脳 → DN → 腹髄 → MN の部分グラフ(4,022 体)に乱数の疎な刺激 400 通りを前向きに通し、各層の状態の実効次元(participation ratio、Gao ら 2017)を読んだ。疎な発火(kWTA 10 %)で 282 > 61 > 8.7 > 2.4 と単調に落ち、脳の状態から MN と同じ 708 列を抜いても 249 なので層の大きさのせいではない。各受け手の入力重みを保って送り手だけ混ぜた対照では MN が 21.9 残る —— 腹髄 → 筋の圧縮は配線の特異性、首(DN)の段は対照と同じ(61 vs 62)で収束そのもの。正直な内訳: 生の PR は少数の刺激が MN を強く駆動する裾の重さ(応答ノルムの最大は中央値の 17 倍)にも引かれるので、各刺激を単位ノルムに揃えた向きだけの次元も測った —— それでも実配線 25 vs 対照 54(kWTA)、線形では 7 vs 42。同じ数式を Physical AI に当てると、G1 ヒューマノイドの RL 歩行・走行の関節軌道は 2.4〜4.1(中央値 3.2)、ダンス 9.3・格闘 11.9、evis の筋活動 73 本は 6〜9。桁の比較であって同一性の主張ではない。生データと部分グラフは commit しない。*

[![effective dimension of the states each layer takes under 400 random sparse stimuli of the brain layer: real wiring vs a ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_motor_bottleneck/01_funnel_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_motor_bottleneck/01_funnel.png)

*↑ 測定の図 ―― effective dimension of the states each layer takes under 400 random sparse stimuli of the brain layer: real wiring vs a control that keeps every receiver's input weights but shuffles who sends them; the neck (DN) compresses by convergence alone, the VNC -> MN stage compresses by the specific wiring*

[![the same funnel after every stimulus response is scaled to unit norm (magnitude removed, direction k](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_motor_bottleneck/02_funnel_direction_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_motor_bottleneck/02_funnel_direction.png)

*↑ the same funnel after every stimulus response is scaled to unit norm (magnitude removed, direction kept): the real wiring still leaves fewer MN direct…*

[![the 400 stimuli projected on the first two principal components of the MN states: real wiring folds ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_motor_bottleneck/04_command_space_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_motor_bottleneck/04_command_space.png)

*↑ the 400 stimuli projected on the first two principal components of the MN states: real wiring folds them onto a few directions, the shuffled control s…*

[![participation ratio of joint-angle trajectories (G1 humanoid, RL policies and mocap retargets) and o](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_motor_bottleneck/05_physical_ai_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_connectome_motor_bottleneck/05_physical_ai.png)

*↑ participation ratio of joint-angle trajectories (G1 humanoid, RL policies and mocap retargets) and of muscle activations (evis), next to the fly's MN…*

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

星の明るさと位置、太陽の縁、全天の雲量、海氷の密接度、畑の被覆率、地形、河川の水位。対象は遠く、真値は普通手に入りません。この部屋の 20 点はそれを逆手に取り、天球座標・球冠の立体角・Eddington の周辺減光・国土地理院の標高タイルといった閉形式や公開データから真値を置いています。

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

使用 op(ノートへ): [`dem_aspect`](https://furuse.work/ops/dem/surface/dem_aspect.html) · [`dem_datum_shift_3param`](https://furuse.work/ops/dem/geodesy/dem_datum_shift_3param.html) · [`dem_earth_curvature_drop`](https://furuse.work/ops/dem/geodesy/dem_earth_curvature_drop.html) · [`dem_ecef_to_geodetic`](https://furuse.work/ops/dem/geodesy/dem_ecef_to_geodetic.html) · [`dem_enu_from_geodetic`](https://furuse.work/ops/dem/geodesy/dem_enu_from_geodetic.html) · [`dem_flow_direction`](https://furuse.work/ops/dem/hydrology/dem_flow_direction.html) · [`dem_geodetic_from_enu`](https://furuse.work/ops/dem/geodesy/dem_geodetic_from_enu.html) · [`dem_geodetic_to_ecef`](https://furuse.work/ops/dem/geodesy/dem_geodetic_to_ecef.html) · [`dem_geoid_height`](https://furuse.work/ops/dem/geodesy/dem_geoid_height.html) · [`dem_slope`](https://furuse.work/ops/dem/surface/dem_slope.html) · [`median`](https://furuse.work/ops/2d/rank/median.html)

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

### 撮像品質・復元ウィング ―― 絵が良くなることと真値に近づくことは別

手ブレを戻す、拡大する、霞を剥がす、深度合成する、投影から再構成する、光子を数えて距離を出す。復元の分野は「見た目が良くなった」と「真値に近づいた」が最も混ざりやすい場所です。この部屋の 14 点は、核・深度・大気光・PSD・投影・到達時刻をこちらが決めた合成で、その 2 つを分けて採点しています。

見た目の指標は真値を最大値としません。霞んだ入力の対比が真値より高い、アンシャープで勾配は真値に一致するのに PSNR は落ちる、雑音を足すと PSNR が上がる。逆に、ナイキストより細かい縞を戻したのに PSNR が -0.01 dB しか動かない場面もあります。

共通して置いたゼロ点は「何もしない」です。核の角度が 19.4 度ずれた復元、投影 12 本の FBP、視程 782 m 以上の除霞、無テクスチャ領域の深度。いずれもそのゼロ点に負けます。負ける条件を数字で置くことが、この部屋の展示の中身です。

## No.2026.007 —— 手ブレはどこまで戻せるか ―― 核を自分で作り、掛けて、戻して、元と比べる

[![手ブレはどこまで戻せるか ―― 核を自分で作り、掛けて、戻して、元と比べる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/01_noise_ceiling_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/01_noise_ceiling.png)

*↑ **手ブレはどこまで戻せるか ―― 核を自分で作り、掛けて、戻して、元と比べる** ―― 既知の直線ブレ核を掛けて戻し、雑音と核の推定誤差で上限を測った図。無雑音なら 22.38 → 56.41 dB、SNR 20 dB では取り分 1.82 dB。核の角度が 19.4 度ずれると「何もしない」に抜かれ、回転ブレを 1 枚の核で戻すと回転中心が -49.41 dB 悪化する。*

[![4 枚目は「復元した」形をしているが、ゼロ点(観測そのもの)より悪い。絵の見た目では区別できない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/02_deblur_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/02_deblur.png)

*↑ 測定の図 ―― 4 枚目は「復元した」形をしているが、ゼロ点(観測そのもの)より悪い。絵の見た目では区別できない。*

[![交点が現場で効く数字。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/03_kernel_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/03_kernel_error.png)

*↑ 交点が現場で効く数字。*

[![核を作った右側だけが正。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/04_rotational_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/04_rotational.png)

*↑ 核を作った右側だけが正。*

[![15 px・20 度の直線ブレに SNR 40 dB の雑音を載せた観測を、角度を 0〜30 度ずらした核で Wiener 復元し直していく(正則化量は毎回神託で最良化)。ずれ 0 度で 28.87 dB、20 度で 22.31 dB。0.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/05_kernel_angle_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/05_kernel_angle_sweep.gif)

*↑ 動く図 ―― 15 px・20 度の直線ブレに SNR 40 dB の雑音を載せた観測を、角度を 0〜30 度ずらした核で Wiener 復元し直していく(正則化量は毎回神託で最良化)。ずれ 0 度で 28.87 dB、20 度で 22.31 dB。0.5 度刻みで追うと 19.2 度でアンシャープマスク(22.40 dB)に、19.4 度で「何もしない」(22.38 dB)に抜かれる(本文の表の補間では 19.2 / 19.4 度)。抜かれた後の復元も「復元した」形をしている —— 右の誤差地図でだけ、縞状のリンギングが真値からのずれとして見える。*

```
py -3.11 examples/poc_camera_shake_deblur.py
```

ソース: [examples/poc_camera_shake_deblur.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_camera_shake_deblur.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_camera_shake_deblur)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`psnr`](https://furuse.work/ops/imgmetrics/fidelity/psnr.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`ssim`](https://furuse.work/ops/imgmetrics/fidelity/ssim.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html) · [`unsharp`](https://furuse.work/ops/2d/smoothing/unsharp.html) · [`vol_richardson_lucy`](https://furuse.work/ops/3d/restoration/vol_richardson_lucy.html)

## No.2026.062 —— 疑似カラーは読み手の判断を変える —— 無い境目を数え、位置を先に当てる

[![疑似カラーは読み手の判断を変える —— 無い境目を数え、位置を先に当てる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colormap_readability/05_scene_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colormap_readability/05_scene_maps.png)

*↑ **疑似カラーは読み手の判断を変える —— 無い境目を数え、位置を先に当てる** ―― 段差がゼロと分かっているなめらかな場を塗り、CIE L* と CIEDE2000 で「無い境目」を数えた。jet は 3 本・hsv は 4 本立ち、viridis と gray は 0 本。★立つ位置は sRGB の伝達関数と CIE の Y 係数から解けて、jet の明度折返し予測 0.3750 / 0.4490 / 0.6250 に対し実測 0.3750 / 0.4492 / 0.6250(最大ずれ 0.0002)。本物の段差が偽の境目を追い越すのは jet で 0.296 %FS・viridis で 0.050 %FS(配色の LUT だけからの予測と一致)——jet を選ぶと段差に 5.9 倍の高さが要る。配色より効くのは写し方で、4.3 桁の 1/r² 場では区別できる階調の実効数が linear 1.4 → rank 76.0。★★外れ値を 1 個混ぜると log が 27.4 → 16.3(-41 %)落ち、percentile と rank だけが不変。*

[![平らなら偽の境目は立たない。jet と hsv の山がそのまま『見えてしまう帯』になる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colormap_readability/01_gain_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colormap_readability/01_gain_profile.png)

*↑ 測定の図 ―― 平らなら偽の境目は立たない。jet と hsv の山がそのまま『見えてしまう帯』になる。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colormap_readability/02_lightness_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colormap_readability/02_lightness_profile.png)

*↑ この回の図*

[![jet の**輪**が偽の境目。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colormap_readability/06_false_edge_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colormap_readability/06_false_edge_map.png)

*↑ jet の**輪**が偽の境目。*

[![左は範囲外と『ちょうど端』が同じ色。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colormap_readability/09_range_sentinel_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colormap_readability/09_range_sentinel.png)

*↑ 左は範囲外と『ちょうど端』が同じ色。*

[![番号の大小に意味は無いのに、連続マップは『近い番号 = 近い領域』と読ませる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colormap_readability/12_categorical_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colormap_readability/12_categorical.png)

*↑ 番号の大小に意味は無いのに、連続マップは『近い番号 = 近い領域』と読ませる。*

```
py -3.11 examples/poc_colormap_readability.py
```

ソース: [examples/poc_colormap_readability.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_colormap_readability.py)

この回が作った図は全部で **14 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_colormap_readability)

使用 op(ノートへ): [`delta_e_map`](https://furuse.work/ops/imgmetrics/colordiff/delta_e_map.html) · [`percentile`](https://furuse.work/ops/2d/rank/percentile.html) · [`rgb_to_lab`](https://furuse.work/ops/imgmetrics/colorspace/rgb_to_lab.html)

## No.2026.118 —— ハエの複眼は光場センサ ―― 神経重ね合わせの「重ねると頑健」は膝の手前まで

[![ハエの複眼は光場センサ ―― 神経重ね合わせの「重ねると頑健」は膝の手前まで](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_compound_eye/01_compound_eye_scaling_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_compound_eye/01_compound_eye_scaling.png)

*↑ **ハエの複眼は光場センサ ―― 神経重ね合わせの「重ねると頑健」は膝の手前まで** ―― 個眼アレイを 9×9 のプレノプティック系として合成し、同じ点を N 個眼で重ねたときの SNR 利得を測った図。小開口では √N がほぼ厳密(N=5 で 2.25 対 2.24)だが、大開口では補間誤差が平均で消えず飽和する(N=49 で 5.33 対 7.00)。ハエの R1–R6 の 6 重の重ね合わせは膝の手前にある。距離はアレイでこそ出て(手前 +1.998・奥 +0.499、真値 2.00 / 0.50)、少数派の遮蔽者は median 重ねなら貫ける(隠れ画素の RMS: 中心 1 枚 0.237 → mean 0.065 → median 0.025)。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_compound_eye/02_compound_eye_superposition_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_compound_eye/02_compound_eye_superposition.png)

*↑ 測定の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_compound_eye/03_compound_eye_depth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_compound_eye/03_compound_eye_depth.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_compound_eye/04_compound_eye_occlusion_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_compound_eye/04_compound_eye_occlusion.png)

*↑ この回の図*

```
py -3.11 examples/poc_compound_eye.py
```

ソース: [examples/poc_compound_eye.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_compound_eye.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_compound_eye)

使用 op(ノートへ): [`lf_all_in_focus`](https://furuse.work/ops/lightfield/depth/lf_all_in_focus.html) · [`lf_aperture_mask`](https://furuse.work/ops/lightfield/refocus/lf_aperture_mask.html) · [`lf_depth_from_focus`](https://furuse.work/ops/lightfield/depth/lf_depth_from_focus.html) · [`lf_plenoptic_design`](https://furuse.work/ops/lightfield/depth/lf_plenoptic_design.html) · [`lf_subaperture`](https://furuse.work/ops/lightfield/views/lf_subaperture.html) · [`lf_synthesize`](https://furuse.work/ops/lightfield/synthesis/lf_synthesize.html) · [`lf_synthetic_aperture`](https://furuse.work/ops/lightfield/refocus/lf_synthetic_aperture.html) · [`median`](https://furuse.work/ops/2d/rank/median.html)

## No.2026.010 —— 投影数を減らすと CT 再構成はどこから壊れるか

[![投影数を減らすと CT 再構成はどこから壊れるか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_fidelity/01_recon_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_fidelity/01_recon_sweep.png)

*↑ **投影数を減らすと CT 再構成はどこから壊れるか** ―― Shepp-Logan を 180 → 12 本で撮り直し、FBP を空白画像と無フィルタ逆投影の 2 つの零点と並べた図。12 本の FBP(RMSE 0.2576)は空白画像(0.2420)より悪い。サイノグラムの行和という再構成を見ない検算が、RMSE では見えない質量欠損 -3.34 % を捕まえ、ランプフィルタの DC ビンを直して -0.0099 % に。*

[![RMSE で見ると 12 本は空白画像 0.2420 より悪い。相関とストリークは別のことを言う。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_fidelity/02_fidelity_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_fidelity/02_fidelity_table.png)

*↑ 測定の図 ―― RMSE で見ると 12 本は空白画像 0.2420 より悪い。相関とストリークは別のことを言う。*

[![零点 A = 空白画像、零点 B = 無フィルタ逆投影(どちらも水平・ほぼ水平)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_fidelity/03_rmse_vs_views_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_fidelity/03_rmse_vs_views.png)

*↑ 零点 A = 空白画像、零点 B = 無フィルタ逆投影(どちらも水平・ほぼ水平)。*

```
py -3.11 examples/poc_ct_fidelity.py
```

ソース: [examples/poc_ct_fidelity.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_fidelity.py)

この回が作った図は全部で **3 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_ct_fidelity)

使用 op(ノートへ): [`backproject_sinogram`](https://furuse.work/ops/tomography/reconstruct/backproject_sinogram.html) · [`ellipse_phantom`](https://furuse.work/ops/tomography/forward/ellipse_phantom.html) · [`ellipse_sinogram`](https://furuse.work/ops/tomography/forward/ellipse_sinogram.html) · [`filtered_backprojection`](https://furuse.work/ops/tomography/reconstruct/filtered_backprojection.html) · [`projection_angles`](https://furuse.work/ops/tomography/layout/projection_angles.html) · [`radon_transform`](https://furuse.work/ops/tomography/forward/radon_transform.html) · [`rmse`](https://furuse.work/ops/imgmetrics/fidelity/rmse.html) · [`ssim`](https://furuse.work/ops/imgmetrics/fidelity/ssim.html) · [`stat_correlation`](https://furuse.work/ops/math/stats/stat_correlation.html)

## No.2026.011 —— 霞を剥がす ―― 大気散乱モデルで真値を作り、透過率と大気光を別々に採点する

[![霞を剥がす ―― 大気散乱モデルで真値を作り、透過率と大気光を別々に採点する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/01_scene.png)

*↑ **霞を剥がす ―― 大気散乱モデルで真値を作り、透過率と大気光を別々に採点する** ―― 深度・大気光・消散係数から真の透過率とシーンを持った霞画像を作り、除霞を採点した図。全体 +4.04 dB の中身は近景 -1.49 dB の劣化を中景 +4.03 / 遠景 +11.28 dB が覆ったもの。視程 782 m 以上では除霞が害になり、雑音を足すと PSNR が上がる(偶然の打ち消し)。*

[![空では過大評価(明るい側)、近景では過小評価(暗い側)。全体の平均バイアスでは打ち消し合って見えない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/02_transmission_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/02_transmission.png)

*↑ 測定の図 ―― 空では過大評価(明るい側)、近景では過小評価(暗い側)。全体の平均バイアスでは打ち消し合って見えない。*

[![全体 +4.04 dB の正体。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/03_bands_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/03_bands.png)

*↑ 全体 +4.04 dB の正体。*

[![左端(薄い霞 = 視程が長い側)で利得が 0 を割る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/04_haze_density_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/04_haze_density.png)

*↑ 左端(薄い霞 = 視程が長い側)で利得が 0 を割る。*

[![動画(110 コマ、120 × 160 px を 2 倍で表示): 消散係数 beta を 0.0025(視程 1565 m)から 0.08(視程 49 m)まで連続に振る。上段は霞んだ観測・暗チャネル除霞・真値、下段は推定した透過率・真の](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/05_haze_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/05_haze_sweep.gif)

*↑ 動く図 ―― 動画(110 コマ、120 × 160 px を 2 倍で表示): 消散係数 beta を 0.0025(視程 1565 m)から 0.08(視程 49 m)まで連続に振る。上段は霞んだ観測・暗チャネル除霞・真値、下段は推定した透過率・真の透過率と、暗チャネル除霞の PSNR 利得(対 何もしない)の曲線。利得は beta ≦ 0.0065(視程 606 m 以上)で負 = 薄い霞では除霞が害になる(5 節の 7 点の表では 0.0050 と 0.0075 の間)。濃霧の端では +2.98 dB。真の A と t を与えたオラクルの PSNR は中央上の板に併記。表示は 8 bit に丸めた観測をそのまま使っている。*

```
py -3.11 examples/poc_dehazing.py
```

ソース: [examples/poc_dehazing.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dehazing.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_dehazing)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`clahe`](https://furuse.work/ops/2d/gray/clahe.html) · [`equalize`](https://furuse.work/ops/2d/gray/equalize.html) · [`image_entropy`](https://furuse.work/ops/imgmetrics/information/image_entropy.html) · [`joint_bilateral`](https://furuse.work/ops/3d/depth_denoise/joint_bilateral.html) · [`nice_ticks`](https://furuse.work/ops/annotate/plot/nice_ticks.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`psnr`](https://furuse.work/ops/imgmetrics/fidelity/psnr.html) · [`rank_image`](https://furuse.work/ops/2d/rank/rank_image.html) · [`ssim`](https://furuse.work/ops/imgmetrics/fidelity/ssim.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html)

## No.2026.016 —— 光子を数えて距離を測る ―― 何個数えれば何ミリまで出るのか

[![光子を数えて距離を測る ―― 何個数えれば何ミリまで出るのか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/01_histograms_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/01_histograms.png)

*↑ **光子を数えて距離を測る ―― 何個数えれば何ミリまで出るのか** ―― 往復時刻にガウシアンをビン積分で置き Poisson 標本を引いた到達時刻ヒストグラムから距離を読む図。N = 200 光子でピーク位置そのまま 11.02 mm、ゲート重心 2.29 mm、理論限界 31.83 mm/√N に 1.00〜1.07 倍で乗る。背景が入ると素の重心は 2 桁崩れ(SBR 0.031 で 564 mm)、族が推すガウス当てはめ 8.82 mm は利用者が 6 行で書くゲート重心に負ける。*

[![背景が無ければ素の重心で足りる。背景が入ると 2 桁崩れ、docstring が勧める背景減算でも戻らない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/02_methods_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/02_methods.png)

*↑ 測定の図 ―― 背景が無ければ素の重心で足りる。背景が入ると 2 桁崩れ、docstring が勧める背景減算でも戻らない。*

[![ゲート重心は CRB に寄り添って落ちる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/03_crb_scaling_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/03_crb_scaling.png)

*↑ ゲート重心は CRB に寄り添って落ちる。*

[![素の推定は μ にほぼ比例して手前へずれる(5 光子/サイクルで -34.5 mm)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/04_pileup_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/04_pileup.png)

*↑ 素の推定は μ にほぼ比例して手前へずれる(5 光子/サイクルで -34.5 mm)。*

```
py -3.11 examples/poc_dtof_ranging.py
```

ソース: [examples/poc_dtof_ranging.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dtof_ranging.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_dtof_ranging)

使用 op(ノートへ): [`dtof_cube_depth`](https://furuse.work/ops/photon/dtof/dtof_cube_depth.html) · [`dtof_cube_simulate`](https://furuse.work/ops/photon/dtof/dtof_cube_simulate.html) · [`dtof_depth`](https://furuse.work/ops/photon/dtof/dtof_depth.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`tcspc_background_subtract`](https://furuse.work/ops/photon/tcspc/tcspc_background_subtract.html) · [`tcspc_coates_correct`](https://furuse.work/ops/photon/spad/tcspc_coates_correct.html) · [`tcspc_simulate`](https://furuse.work/ops/photon/tcspc/tcspc_simulate.html)

## No.2026.119 —— ハエの視覚前段を op の連鎖で ―― 合成の空を回る/前進すると、何が読めて何が読めないか

[![ハエの視覚前段を op の連鎖で ―― 合成の空を回る/前進すると、何が読めて何が読めないか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_vision/01_fly_vision_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_vision/01_fly_vision_scene.png)

*↑ **ハエの視覚前段を op の連鎖で ―― 合成の空を回る/前進すると、何が読めて何が読めないか** ―― 六角格子 721 個眼 → 受容野 → ラミナの DC 落とし → Hassenstein-Reichardt 相関器 → HS 対向和を繋いだ 1 匹の眼で、1/f の帯つき空を回る図。自己回転の向きと波形は読める(真の角速度との相関 +0.785、膜 LP つき +0.880、符号一致 0.92)が、ラミナ段の DC 落としを省くと相関器は DC × 高域通過の揺れを出して +0.504 に落ちる。回転せずに前進すると全視野の読み出しは −0.689 の「回転」に化け、上半視野に限っても受容野が地平線をまたぐぶん −0.221 が漏れる(el>2Δρ で 0.000)。対向比は速さを落とすので、20 m 先のドームの 1.4°/s の流れも −0.612 に読む。LGMD η のピークは衝突の α·l/|v| 前(−0.1570 s、予測 −0.1567 s)で θ=23.97°(予測 24.02°、球の厳密な見込み角なら 4 次式の根で 24.6°)、τ 球式は d/|v| に RMS 1e-5 s で乗り、円板式の誤用は θ=60° で cos²(θ/2)=0.75 倍。12 方位の縞で DSI 0.798、好む向き 0°。*

[![相関 +0.785(膜 LP つき +0.880、ラミナ段なし +0.504)。対向比は符号の一致度なので、尺度 k は最小二乗で合わせてある。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_vision/02_fly_vision_rotation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_vision/02_fly_vision_rotation.png)

*↑ 測定の図 ―― 相関 +0.785(膜 LP つき +0.880、ラミナ段なし +0.504)。対向比は符号の一致度なので、尺度 k は最小二乗で合わせてある。*

[![偏り: 全視野 -0.689 / 上半 el>0 -0.221 / el>2Δρ +0.000 / ドーム -0.612](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_vision/03_fly_vision_forward_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_vision/03_fly_vision_forward.png)

*↑ 偏り: 全視野 -0.689 / 上半 el>0 -0.221 / el>2Δρ +0.000 / ドーム -0.612*

[![ピーク -0.157 s(予測 -0.157 s)、θ_peak 24.0°(予測 24.0°)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_vision/04_fly_vision_looming_eta_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_vision/04_fly_vision_looming_eta.png)

*↑ ピーク -0.157 s(予測 -0.157 s)、θ_peak 24.0°(予測 24.0°)。*

[![球式は RMS 0.00001 s で真値に乗る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_vision/05_fly_vision_looming_tau_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_vision/05_fly_vision_looming_tau.png)

*↑ 球式は RMS 0.00001 s で真値に乗る。*

[![負の応答(逆向き)は fly_dsi が 0 に切る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_vision/06_fly_vision_dsi_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_vision/06_fly_vision_dsi.png)

*↑ 負の応答(逆向き)は fly_dsi が 0 に切る。*

```
py -3.11 examples/poc_fly_vision.py
```

ソース: [examples/poc_fly_vision.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_fly_vision.py)

この回が作った図は全部で **6 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_fly_vision)

使用 op(ノートへ): [`fly_dsi`](https://furuse.work/ops/flyvision/tuning/fly_dsi.html) · [`fly_emd_response`](https://furuse.work/ops/flyvision/motion/fly_emd_response.html) · [`fly_hex_lattice`](https://furuse.work/ops/flyvision/lattice/fly_hex_lattice.html) · [`fly_hex_resample`](https://furuse.work/ops/flyvision/sample/fly_hex_resample.html) · [`fly_hs_readout`](https://furuse.work/ops/flyvision/integrate/fly_hs_readout.html) · [`fly_lgmd_eta`](https://furuse.work/ops/flyvision/looming/fly_lgmd_eta.html) · [`fly_sky_1f`](https://furuse.work/ops/flyvision/stimulus/fly_sky_1f.html) · [`fly_tau_from_expansion`](https://furuse.work/ops/flyvision/looming/fly_tau_from_expansion.html)

## No.2026.019 —— 深度合成 ―― 全焦点画像と深度地図は別物

[![深度合成 ―― 全焦点画像と深度地図は別物](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/01_stack_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/01_stack.png)

*↑ **深度合成 ―― 全焦点画像と深度地図は別物** ―― 錯乱円の閉形式で深さに応じたぼけを掛けた 15 枚から、全焦点画像と深度地図を取り出した図。全焦点は 35.89 dB(ゼロ点 20.98 dB)なのに、同じ融合の深度は無テクスチャ領域でゼロ点に 8 倍負ける(0.13 倍)。相対量の信頼度は無テクスチャで 0.9923 と有テクスチャの 0.9630 より高く出る ―― 絶対値(23600 倍差)で棄却すると RMS 1.505 → 0.878 mm。*

[![合焦点法は全焦点画像と同時に距離画像も出す。ただし左下の無テクスチャの四角だけ、誤差が掃引全域にばらけた乱数になっている(段差帯のハローも見える)—— 絵ほど距離は当てにならない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/02_depth_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/02_depth_map.png)

*↑ 測定の図 ―― 合焦点法は全焦点画像と同時に距離画像も出す。ただし左下の無テクスチャの四角だけ、誤差が掃引全域にばらけた乱数になっている(段差帯のハローも見える)—— 絵ほど距離は当てにならない。*

[![左下の無テクスチャの四角が、相対量(0.90-1.00 に切って表示)では最も明るい = 自信ありに見え、絶対量(対数)でだけ「何も見えていない」と出る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/03_confidence_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/03_confidence.png)

*↑ 左下の無テクスチャの四角が、相対量(0.90-1.00 に切って表示)では最も明るい = 自信ありに見え、絶対量(対数)でだけ「何も見えていない」と出る。*

[![2 本が離れていく = 残りの誤差は標本化ではなく焦点評価が持っている。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/04_frames_floor_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/04_frames_floor.png)

*↑ 2 本が離れていく = 残りの誤差は標本化ではなく焦点評価が持っている。*

[![焦点を 196.23〜203.00 mm で 17 枚掃引し、1 枚進むたびに「ここまでで焦点評価が最大のフレーム」を画素ごとに選び直す。左 = いまの 1 枚(橙 = この 1 枚で最良が更新された画素)、中 = ここまでの全焦点画像、右](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/05_focus_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/05_focus_sweep.gif)

*↑ 動く図 ―― 焦点を 196.23〜203.00 mm で 17 枚掃引し、1 枚進むたびに「ここまでで焦点評価が最大のフレーム」を画素ごとに選び直す。左 = いまの 1 枚(橙 = この 1 枚で最良が更新された画素)、中 = ここまでの全焦点画像、右 = ここまでの距離画像。全焦点画像の PSNR は 22.17 dB から 33.69 dB へ育ち、中央の 1 枚(28.52 dB)を上回る。一方、左下の無地の四角は最後まで掃引のたびに塗り替わり(最後の 1 枚でも無地の 12 % が入れ替わる。テクスチャ有は 4 %)、距離誤差は 2.203 mm(テクスチャ有 0.467 mm)で終わる。*

```
py -3.11 examples/poc_focus_stacking.py
```

ソース: [examples/poc_focus_stacking.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_focus_stacking.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_focus_stacking)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`csi_height_map`](https://furuse.work/ops/interferometry/surface/csi_height_map.html) · [`defocus_blur`](https://furuse.work/ops/optics/scene/defocus_blur.html) · [`dilation_circle`](https://furuse.work/ops/2d/region/dilation_circle.html) · [`fuse`](https://furuse.work/ops/3d/tsdf_fusion/fuse.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`laplace`](https://furuse.work/ops/2d/edges/laplace.html) · [`mean_image`](https://furuse.work/ops/2d/smoothing/mean_image.html) · [`optical_camera`](https://furuse.work/ops/optics/scene/optical_camera.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`psnr`](https://furuse.work/ops/imgmetrics/fidelity/psnr.html) · [`sobel_amp`](https://furuse.work/ops/2d/edges/sobel_amp.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html) · [`xcv2_lap_var`](https://furuse.work/ops/2d/features/xcv2_lap_var.html)

## No.2026.023 —— ライトフィールドから深度を出す ―― 既知の深度で作った光場に、ゼロ点を並べて突きつける

[![ライトフィールドから深度を出す ―― 既知の深度で作った光場に、ゼロ点を並べて突きつける](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/01_scene_and_depth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/01_scene_and_depth.png)

*↑ **ライトフィールドから深度を出す ―― 既知の深度で作った光場に、ゼロ点を並べて突きつける** ―― 9×9 の光場を解析的な逆写像で描き、真値スロープ地図に対して焦点度・EPI・2 眼ブロックマッチングを採点した図。定数ゼロ点には 22 倍勝つが、視点 2 枚だけ使う 2 眼に対しては cubic でようやく 1.6 倍。既定の linear 補間は整数スロープに吸着し、真値 1.30 を 1.4750 と読む(深度で 11.9 %)。*

[![linear は 1.08/1.15 を 1.0 へ、1.85 を 2.0 側へ引く。cubic は恒等線に乗る。生成側の補間はゼロ(Fourier シフト)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/02_focus_snapping_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/02_focus_snapping.png)

*↑ 測定の図 ―― linear は 1.08/1.15 を 1.0 へ、1.85 を 2.0 側へ引く。cubic は恒等線に乗る。生成側の補間はゼロ(Fourier シフト)。*

[![EPI は SNR 20 で既に -35 %。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/03_texture_breakdown_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/03_texture_breakdown.png)

*↑ EPI は SNR 20 で既に -35 %。*

[![境界から 5 px 離れれば内側の水準に戻る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/04_occlusion_bands_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/04_occlusion_bands.png)

*↑ 境界から 5 px 離れれば内側の水準に戻る。*

```
py -3.11 examples/poc_lightfield_depth.py
```

ソース: [examples/poc_lightfield_depth.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_lightfield_depth.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_lightfield_depth)

使用 op(ノートへ): [`lf_depth_from_focus`](https://furuse.work/ops/lightfield/depth/lf_depth_from_focus.html) · [`lf_disparity_to_depth`](https://furuse.work/ops/lightfield/depth/lf_disparity_to_depth.html) · [`lf_epi`](https://furuse.work/ops/lightfield/views/lf_epi.html) · [`lf_epi_slope`](https://furuse.work/ops/lightfield/depth/lf_epi_slope.html) · [`lf_refocus`](https://furuse.work/ops/lightfield/refocus/lf_refocus.html)

## No.2026.105 —— 実写のブレを取る ―― 3 つの物差しに、3 人の勝者

[![実写のブレを取る ―― 3 つの物差しに、3 人の勝者](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_deblur_honesty/01_restore_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_deblur_honesty/01_restore.png)

*↑ **実写のブレを取る ―― 3 つの物差しに、3 人の勝者** ―― 真値を実写そのもの(scikit-image camera、CC0)にして、劣化だけ自分で作る(直線ブレ 11 px・20 度 + 雑音 σ=0.004)。★ゼロ点(何もしない)が 24.04 dB と強く、よく使われる nsr=0.005 の Wiener は 23.66 dB で**負ける**。★★ただしそこで止めると相手を弱く見せたことになる ―― nsr を振ると 0.0005 で 19.18 dB、0.02 で 25.40 dB。**ノブを固定した比較は比較ではない**。★★しかもノブで動く幅 6.22 dB は、脱畳み込みをするかしないかの差 1.36 dB の **4.6 倍** ―― 手法よりノブが効く。★★同じ 7 通りの結果に 3 つの物差しを当てると、**別々の手法が 1 位**になる: PSNR は正しい PSF の Wiener(25.40 dB)、勾配エネルギーは motion_deblur(0.2986 = 真値 0.1936 の 1.54 倍、**真値より鋭い絵が選ばれる**)、blur_effect は unsharp。参照なし指標が選ぶ手法は PSNR で **4.98 dB / 3.26 dB 損**をする(なお blur_effect は真値そのものは正しく最良と判定する ―― 「ぼけているか」は測れていて、それでも選ばせると損をする)。★長さを 11→21 px と間違えた PSF は 18.56 dB(ゼロ点より -5.48 dB)なのに勾配は真値の 1.37 倍で「よく効いた」ように見える。★崖: 雑音 σ=0.016 で利得は +0.05 dB(1.6 % の雑音で脱畳み込みは何も買わない)、ブレ長の利得は L=5 が山で両端で落ちる(小さいブレは取るものが無く、大きいブレは情報が消えている)。*

[![固定した nsr で比べると、正しい PSF でもゼロ点に負ける。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_deblur_honesty/02_nsr_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_deblur_honesty/02_nsr.png)

*↑ 測定の図 ―― 固定した nsr で比べると、正しい PSF でもゼロ点に負ける。*

[![σ=0 で +1.52 dB、σ=0.016 で +0.05 dB。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_deblur_honesty/03_cliffs_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_deblur_honesty/03_cliffs.png)

*↑ σ=0 で +1.52 dB、σ=0.016 で +0.05 dB。*

[![参照なし指標が選ぶ手法は PSNR で 3〜5 dB 劣る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_deblur_honesty/04_metrics_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_deblur_honesty/04_metrics.png)

*↑ 参照なし指標が選ぶ手法は PSNR で 3〜5 dB 劣る。*

```
py -3.11 examples/poc_real_deblur_honesty.py
```

ソース: [examples/poc_real_deblur_honesty.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_deblur_honesty.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_real_deblur_honesty)

使用 op(ノートへ): [`iv_motion_deblur`](https://furuse.work/ops/2d/restoration/iv_motion_deblur.html) · [`iv_richardson_lucy`](https://furuse.work/ops/2d/restoration/iv_richardson_lucy.html) · [`iv_unsharp_deblur`](https://furuse.work/ops/2d/restoration/iv_unsharp_deblur.html) · [`psnr`](https://furuse.work/ops/imgmetrics/fidelity/psnr.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`sk_blur_effect`](https://furuse.work/ops/2d/features/sk_blur_effect.html) · [`unsharp`](https://furuse.work/ops/2d/smoothing/unsharp.html)

## No.2026.039 —— 超解像は情報を増やすのか ―― 真値を持ったまま縮小して、戻して、数える

[![超解像は情報を増やすのか ―― 真値を持ったまま縮小して、戻して、数える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/03_multiframe_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/03_multiframe.png)

*↑ **超解像は情報を増やすのか ―― 真値を持ったまま縮小して、戻して、数える** ―― 真値を縮小して観測を作り、単一画像拡大・逆投影・drizzle を分解能の列で採点した図。単一画像の拡大は bicubic のゼロ点を最大 +0.036 dB しか上回れない。副画素ずれのある 16 枚の drizzle は標本化不足の条件で +13.96 dB、ナイキスト超えの周期 6 の変調度が 0.03 → 0.38 に立ち上がる。*

[![鮮鋭化だけがナイキスト(周期 8)より細かい列にも縞を作る。それは分解能ではなく**無い縞**。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/01_upscale_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/01_upscale.png)

*↑ 測定の図 ―― 鮮鋭化だけがナイキスト(周期 8)より細かい列にも縞を作る。それは分解能ではなく**無い縞**。*

[![IBP は周期 12 以上の落ちた変調を戻すが、8 より細かい列は1 本も戻らない(順モデルの零空間)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/02_modulation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/02_modulation.png)

*↑ IBP は周期 12 以上の落ちた変調を戻すが、8 より細かい列は1 本も戻らない(順モデルの零空間)。*

[![上限の線がレンズの許す限界。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/04_multiframe_modulation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/04_multiframe_modulation.png)

*↑ 上限の線がレンズの許す限界。*

[![動画(61 コマ、縞の群を 2 倍で表示): 前半は単一画像の IBP を 0 → 24 回。周期 12 の変調度は 0.78 → 0.96 と戻るが、ナイキスト(周期 8)より細かい列の最大は 0.03 → 0.04 にとどまる —— 順](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/05_growth.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/05_growth.gif)

*↑ 動く図 ―― 動画(61 コマ、縞の群を 2 倍で表示): 前半は単一画像の IBP を 0 → 24 回。周期 12 の変調度は 0.78 → 0.96 と戻るが、ナイキスト(周期 8)より細かい列の最大は 0.03 → 0.04 にとどまる —— 順モデルの零空間に落ちた縞は何回回しても立たない(PSNR も 21.10 → 21.09 dB で動かない)。後半は標本化不足(σ = 0.30)の 16 枚を 1 枚ずつ drizzle に足す(ずれは相互相関で推定、pixfrac は枚数に合わせて 1.0 → 0.4、被覆の穴は単一画像の bicubic で埋めて割合を表示)。周期 6 の変調度は単一画像の 0.03 から 16 枚で 0.38 まで立ち上がる(レンズの上限 0.46)。PSNR は 28.27 → 42.24 dB。*

```
py -3.11 examples/poc_superresolution_limits.py
```

ソース: [examples/poc_superresolution_limits.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_superresolution_limits.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_superresolution_limits)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`data_to_pixel`](https://furuse.work/ops/annotate/plot/data_to_pixel.html) · [`drizzle_resample`](https://furuse.work/ops/astrostack/stack/drizzle_resample.html) · [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`psnr`](https://furuse.work/ops/imgmetrics/fidelity/psnr.html) · [`ssim`](https://furuse.work/ops/imgmetrics/fidelity/ssim.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html) · [`unsharp`](https://furuse.work/ops/2d/smoothing/unsharp.html) · [`vol_fft_lowpass`](https://furuse.work/ops/3d/frequency/vol_fft_lowpass.html) · [`vol_resize`](https://furuse.work/ops/3d/geom_transform/vol_resize.html) · [`volume_downsample`](https://furuse.work/ops/3d/preprocess/volume_downsample.html)

## No.2026.135 —— ハエの視葉だけで進路を立て直す ―― ラミナから操舵まで、学習なしで

[![ハエの視葉だけで進路を立て直す ―― ラミナから操舵まで、学習なしで](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_optomotor_steering/06_follow.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_optomotor_steering/06_follow.gif)

*↑ **ハエの視葉だけで進路を立て直す ―― ラミナから操舵まで、学習なしで** ―― 外乱で向きが流れていく機体に、複眼と閉じた式の回路しか積まずに進路を立て直す —— ハエの optomotor 反応を fullseye の op だけで組み、真値のジャイロと並べて測った。経路は全段が学習なしの閉形式で、勾配で決めた数は 1 つも無い: 複眼で標本化(fly_hex_resample)→ ラミナの順応と帯域通過(fly_lamina_filter)→ ON / OFF に分ける(fly_onoff_split)→ 六角格子の 6 方向すべてで方向選択(fly_t4t5_field)→ 局所フロー(fly_flow_from_directions)→ 整合フィルタへの線形当てはめ(fly_matched_filter / fly_egomotion_from_flow)→ ヨー角速度 → 6 ニューロン 8 シナプスの操舵回路(graph_conductance_states)→ 舵。段ごとに厳密な恒等式がある: 景色を 1 万倍明るくしてもラミナの出力は変わらない(Weber、差 7e-16)、T4 の三腕モデル(Haag ら 2016 の逐語の定数 τ=250 ms・k=5/5/10)は論文の 2 柱刺激で 24.9636 / 0.8195 をそのまま返し、「増強と抑制は相補的」という主張は比の積の恒等式(4.161 × 7.321 = 30.461 = 三腕)として機械精度で成り立つ、整合フィルタの 1.7 rad/s は 9 桁一致で戻る。測った限界も隠さない: 古典の縞ドラムでは動き続ける回転との相関 0.976 だが自然な 1/f の景色では 0.897 に落ち、必要な較正利得は縞 2.64 に対し自然な景色 6.76 / 7.88 —— 種類が変われば 3.0 倍、同じ統計の別の景色どうしでも 1.16 倍ちがう(相関器は速度計ではなく対比つきの運動計)。視野 80° の 1 つの眼で同じ +0.5 rad/s を 12 枚の景色で測ると散らばり 1.05 で 12 枚中 4 枚は回転の符号すら間違えるが、fly_eye_merge で 3 つの眼を 250° に束ねると散らばり 0.44・符号の誤り 0 枚になる —— 複眼が広いことは飾りではない。閉ループ(較正は景色 A、飛ぶのは見たことのない景色 B)では、舵を切らなければ進路は 51 度流れ、視葉の反射は 33 度に、真値のジャイロは 23 度にする。反射は絶対の方位を知らないので流れをゼロにはできない —— そこから先は中枢複合体(コンパス)の仕事。操舵をコネクトームの側で書いても同じ 33 度で、膜電位は反転電位の凸結合なのでどんな入力でも発散しない。データは同梱しない(景色は fly_sky_1f が種から作る)。*

[![left to right, top to bottom: what the ommatidia see, the lamina's contrast (brightness thrown away), the ON and OFF cha](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_optomotor_steering/01_pathway_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_optomotor_steering/01_pathway.png)

*↑ 測定の図 ―― left to right, top to bottom: what the ommatidia see, the lamina's contrast (brightness thrown away), the ON and OFF channels, and the direction-selective field read as a local flow. The eye is turning at 0.5 rad/s in a 1/f panorama; nothing here was trained.*

[![each scene is fitted with its own single gain; the striped drum is nearly linear, and a natural 1/f ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_optomotor_steering/02_tuning_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_optomotor_steering/02_tuning.png)

*↑ each scene is fitted with its own single gain; the striped drum is nearly linear, and a natural 1/f scene needs a gain 3.0x larger — a correlation det…*

[![a narrow eye is at the mercy of whichever few large features are in front of it: over eight scenes o](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_optomotor_steering/03_wide_eye_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_optomotor_steering/03_wide_eye.png)

*↑ a narrow eye is at the mercy of whichever few large features are in front of it: over eight scenes of identical statistics it scatters and gets the si…*

[![the disturbance has a steady bias, so the open loop drifts away; the optomotor reflex cuts the drift](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_optomotor_steering/04_closed_loop_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_optomotor_steering/04_closed_loop.png)

*↑ the disturbance has a steady bias, so the open loop drifts away; the optomotor reflex cuts the drift but cannot null it — a reflex has no absolute hea…*

[![the wiring is written by hand as a synapse table and run as a conductance circuit; the state is a co](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_optomotor_steering/05_circuit_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fly_optomotor_steering/05_circuit.png)

*↑ the wiring is written by hand as a synapse table and run as a conductance circuit; the state is a convex combination of the reversal potentials, so it…*

```
py -3.11 examples/poc_fly_optomotor_steering.py
```

ソース: [examples/poc_fly_optomotor_steering.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_fly_optomotor_steering.py)

この回が作った図は全部で **7 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_fly_optomotor_steering)

使用 op(ノートへ): [`fly_egomotion_from_flow`](https://furuse.work/ops/flyvision/selfmotion/fly_egomotion_from_flow.html) · [`fly_eye_merge`](https://furuse.work/ops/flyvision/selfmotion/fly_eye_merge.html) · [`fly_flow_from_directions`](https://furuse.work/ops/flyvision/direction/fly_flow_from_directions.html) · [`fly_hex_lattice`](https://furuse.work/ops/flyvision/lattice/fly_hex_lattice.html) · [`fly_hex_resample`](https://furuse.work/ops/flyvision/sample/fly_hex_resample.html) · [`fly_lamina_filter`](https://furuse.work/ops/flyvision/lamina/fly_lamina_filter.html) · [`fly_matched_filter`](https://furuse.work/ops/flyvision/selfmotion/fly_matched_filter.html) · [`fly_onoff_split`](https://furuse.work/ops/flyvision/lamina/fly_onoff_split.html) · [`fly_sky_1f`](https://furuse.work/ops/flyvision/stimulus/fly_sky_1f.html) · [`fly_t4t5_field`](https://furuse.work/ops/flyvision/direction/fly_t4t5_field.html) · [`graph_conductance_states`](https://furuse.work/ops/conngraph/circuit/graph_conductance_states.html) · [`graph_from_synapses`](https://furuse.work/ops/conngraph/construct/graph_from_synapses.html)

## No.2026.148 —— 遠ざかると消える距離と、形が変わるときの面積

[![遠ざかると消える距離と、形が変わるときの面積](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/04_vanish_at_p_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/04_vanish_at_p.png)

*↑ **遠ざかると消える距離と、形が変わるときの面積** ―― **「高周波と低周波を混ぜた絵」にも「滑らかに形が変わる絵」にも、絵から直接測れる厳密な真値がある** —— そして **よく使われている作り方のほうが、その真値を外す**。★★芯 1: **分解の直交性。** 理想的な周波数マスクで低域と高域に分けると 2 枚は厳密に直交するので `E(低) + E(高) = E(元)` が成り立つ(4 通りの遮断で帳尻の相対値 **1.9e-16**)。ところが教科書どおりの作り方(ガウシアンでぼかし、残りを高域にする)では **0.53 %〜3.10 %** ずれる。**どちらも足せば元に戻る** —— **可逆であることと直交であることは別**。しかもずれは **単調でない**: いちばん悪いのはぼかしが最も弱い a = 0.1 で、いちばん小さいのは途中の a = 0.7。**強くしても弱くしても直らない。**★★芯 2: **遠ざかると消える距離は整数。** k 画素を束ねる操作の伝達関数は `sin(πfk)/(k sin(πf))` で、f·k が整数のとき厳密に 0。つまり **周期 p 画素の模様は p 画素に束ねるとちょうど消える**(5 通りの周期で **1.4e-14**)。さらに強く、**束ねたあとの絵は 1 画素ずつ閉形式で書ける** —— 振幅だけでなく **束ねた画素の中心が (k−1)/2 ずれること**まで式に入っていて、束ね幅 1〜48 の全画素で **2.8e-14**。★★芯 3: **形の面積は t の厳密な 2 次式。** 多角形の頂点を線形補間すると囲む面積は `a t² + b t + c` に乗るので、**3 コマ測れば全コマを予言できる**(3 通りの形で **2.4e-15**)。それが**絵からも出る**: 多角形を画素に塗って数えた面積でも、格子 128 で 1.10 % だったずれが格子 512・1 画素を 4×4 に分けて **0.053 %** まで縮む。しかも **「1 画素を 4×4 に分ける」のは「格子を 4 倍細かくする」と厳密に同じ数字**(0.00e+00 で一致)。★★芯 4: **絵から測ると符号が消える。そこで予言はちょうど 25 % 外れる。** 頂点順を逆にした多角形へモーフすると、符号つき面積は t の 1 次式になり (t = 0.5 で多角形が線に潰れる)2 次式の予言は 3.4e-15 で当たる。しかし**絵から測れるのは正の面積だけ**なので放物線は折り返し、3 コマから当てた予言は最大値の **ちょうど 1/4** 外れる —— 2 つの形で **25.0 %** と **25.0 %**。**外れ方まで閉形式で出る。** ★★芯 5: **スプラインの 2 つの厳密な性質。** Catmull-Rom は制御点を **距離 0.0e+00** で通り、ベジエは制御点を通らない代わりに **凸包から出ない**(4 通り × 401 点すべて)—— ちょうど裏返しの性質。★★**外した予言を 3 つ残してある。** (a)「切り替わる束ね幅は遮断周波数 fc から 1/(2 fc) で予言できる」は**外れ**で、fc を 3 倍振っても実測は 3.4〜3.9 画素から動かない —— 決めているのは遮断周波数ではなく **高域側の絵が実際に持つ周期**。(b) 上の「ぼかしのずれは単調」も外れ。(c)「絵の最大と最小で振幅を測れば閉形式と一致する」も**外れ**で、k = 6 では **20.7 % 小さく**出る —— **画素が山の頂上を踏まないから**。**式は踏まなくても正しい。****新しい op は 1 つも足していない。** 検査 20 件・図 13 枚(動く図 1 枚を含む)。*

[![低い周波数に粗い模様、高い周波数に細かい模様を入れた 1 枚を、束ねながら見たもの。**束ねるのは「遠ざかる」こと**で、細かいほうが先に消える。ただし ★**いつ消えるかは遮断周波数では決まらない** —— 下の数表の「外した予言」を参照](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/01_hybrid_near_far_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/01_hybrid_near_far.png)

*↑ 測定の図 ―― 低い周波数に粗い模様、高い周波数に細かい模様を入れた 1 枚を、束ねながら見たもの。**束ねるのは「遠ざかる」こと**で、細かいほうが先に消える。ただし ★**いつ消えるかは遮断周波数では決まらない** —— 下の数表の「外した予言」を参照。*

[![**どちらも足せば元に戻る**(再構成の誤差は両方 1e-13 未満)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/02_orthogonal_split_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/02_orthogonal_split.png)

*↑ **どちらも足せば元に戻る**(再構成の誤差は両方 1e-13 未満)。*

[![k = 24 と k = 48(f·k が整数)で **厳密に 0**、その間では戻る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/05_transfer_curve_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/05_transfer_curve.png)

*↑ k = 24 と k = 48(f·k が整数)で **厳密に 0**、その間では戻る。*

[![閉形式なら 2.4e-15。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/09_area_from_picture_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/09_area_from_picture.png)

*↑ 閉形式なら 2.4e-15。*

[![薄い折れ線が制御点をつないだもの、濃い線が Catmull-Rom。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/12_catmull_through_points_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/12_catmull_through_points.png)

*↑ 薄い折れ線が制御点をつないだもの、濃い線が Catmull-Rom。*

[![6 角形が別の 6 角形へ変わって戻るところ。★見た目は連続に変わるが、**囲む面積は t の 厳密な 2 次式**に乗っている(次の図)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/06_morph_loop.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area/06_morph_loop.gif)

*↑ 動く図 ―― 6 角形が別の 6 角形へ変わって戻るところ。★見た目は連続に変わるが、**囲む面積は t の 厳密な 2 次式**に乗っている(次の図)。*

```
py -3.11 examples/poc_vanishing_detail_and_morphing_area.py
```

ソース: [examples/poc_vanishing_detail_and_morphing_area.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_vanishing_detail_and_morphing_area.py)

この回が作った図は全部で **14 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_vanishing_detail_and_morphing_area)

使用 op(ノートへ): [`convex_hull`](https://furuse.work/ops/3d/bounds/convex_hull.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`morph`](https://furuse.work/ops/shape2d/morph/morph.html)

## No.2026.184 —— セグメンテーションの関門 ―― 真値つきの 6 つの世界に 10 手法を当て、どの物差しがどの壊れ方に盲目かを測る

[![セグメンテーションの関門 ―― 真値つきの 6 つの世界に 10 手法を当て、どの物差しがどの壊れ方に盲目かを測る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/01_worlds_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/01_worlds.png)

*↑ **セグメンテーションの関門 ―― 真値つきの 6 つの世界に 10 手法を当て、どの物差しがどの壊れ方に盲目かを測る** ―― セグメンテーションを増やす前に、採点の物差しと真値を先に置いた —— 新モジュール segeval(分割表・Dice/Jaccard・境界 F・Hausdorff/ASSD・過分割/未分割・個数の一致・採点表、各 op に恒等式か第 2 実装の門)と segworld(真値つきの合成世界 6 種: 等半径の触れ合う粒はレンズ面積の閉形式、ボロノイ結晶粒は粒界長が scipy の稜線と 1e-9 で一致、影のある部品、平均が同じで質感だけ違う領域、照明の勾配、幅 1〜3 px の細い構造)。既存 10 手法(Otsu・局所閾値・Niblack・Sauvola・Chan–Vese・random walker・分水嶺 2 種・Felzenszwalb・SLIC)を既定のノブで総当たり。門: 6 世界すべてで真 vs 真が全部の物差しで満点 / マスクの物差しは融合に盲目(Otsu は J=0.95 なのに 9/10 が未分割)/ 境界の物差しは過分割に盲目(勾配の分水嶺は BF=1.00 なのに過分割 339)/ Sauvola は結晶粒の個数を全部当てるが粒界の帯を落とし J=0.91 / 影のある部品はどの手法も J < 0.3、真値を見る閾値のオラクルでも J=0.29 / 質感はマスク手法 ARI < 0.3、局所 σ の k-means は ARI=0.92 / 照明の勾配は大域 Otsu J=0.21、フラットフィールド後 J=1.00 / 細い構造は Otsu の境界 F が 1.00 でも雑音の粒で過分割 29。正直に: 手法のノブは既定固定(合わせれば直るものがある)、境界 F は距離変換の BF(Martin 2004 の 2 部マッチングではない)、個数の一致の辺の条件は自前の定義。10 門、2.0 s。*

[![Jaccard は物体マスク(格子を返す手法は —)。VI = Meilă の情報の変分(0 が一致)、ARI = 補正 Rand、境界 F は τ = 2 px、HD95 = 境界の Hausdorff の 95 % 点。過分割/未分割は](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/02_scores_blobs_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/02_scores_blobs.png)

*↑ 測定の図 ―― Jaccard は物体マスク(格子を返す手法は —)。VI = Meilă の情報の変分(0 が一致)、ARI = 補正 Rand、境界 F は τ = 2 px、HD95 = 境界の Hausdorff の 95 % 点。過分割/未分割は分割表の多数決の多重度、一致/分裂/融合/欠落/偽は主に重なる辺の次数。最後の行はルールの直し方。*

[![Jaccard は物体マスク(格子を返す手法は —)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/03_scores_voronoi_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/03_scores_voronoi.png)

*↑ Jaccard は物体マスク(格子を返す手法は —)。*

[![Jaccard は物体マスク(格子を返す手法は —)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/04_scores_parts_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/04_scores_parts.png)

*↑ Jaccard は物体マスク(格子を返す手法は —)。*

[![Jaccard は物体マスク(格子を返す手法は —)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/05_scores_texture_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/05_scores_texture.png)

*↑ Jaccard は物体マスク(格子を返す手法は —)。*

[![Jaccard は物体マスク(格子を返す手法は —)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/06_scores_gradient_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/06_scores_gradient.png)

*↑ Jaccard は物体マスク(格子を返す手法は —)。*

[![触れ合う粒: 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_random_wa](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/08_gauntlet_blobs.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/08_gauntlet_blobs.gif)

*↑ 動く図 ―― 触れ合う粒: 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_random_walker, watersheds, sg_watershed_gradient, sk_felzenszwalb, sk_slic, edt_watershed)。*

[![結晶粒(ボロノイ): 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_rando](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/09_gauntlet_voronoi.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/09_gauntlet_voronoi.gif)

*↑ 動く図 ―― 結晶粒(ボロノイ): 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_random_walker, watersheds, sg_watershed_gradient, sk_felzenszwalb, sk_slic)。*

[![影のある部品: 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_random_w](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/10_gauntlet_parts.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/10_gauntlet_parts.gif)

*↑ 動く図 ―― 影のある部品: 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_random_walker, watersheds, sg_watershed_gradient, sk_felzenszwalb, sk_slic)。*

[![質感だけ違う領域: 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_random](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/11_gauntlet_texture.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/11_gauntlet_texture.gif)

*↑ 動く図 ―― 質感だけ違う領域: 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_random_walker, watersheds, sg_watershed_gradient, sk_felzenszwalb, sk_slic, texture_kmeans)。*

[![照明の勾配: 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_random_wa](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/12_gauntlet_gradient.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/12_gauntlet_gradient.gif)

*↑ 動く図 ―― 照明の勾配: 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_random_walker, watersheds, sg_watershed_gradient, sk_felzenszwalb, sk_slic, flat_field_otsu)。*

[![細い構造: 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_random_wal](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/13_gauntlet_thin.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_segmentation_gauntlet/13_gauntlet_thin.gif)

*↑ 動く図 ―― 細い構造: 緑 = 真値の境界、赤 = 手法の境界、黄 = 一致。1 コマ = 1 手法(otsu, local_threshold, sk_niblack, sk_sauvola, sk_chan_vese, xsk_random_walker, watersheds, sg_watershed_gradient, sk_felzenszwalb, sk_slic)。*

```
py -3.11 examples/poc_segmentation_gauntlet.py
```

ソース: [examples/poc_segmentation_gauntlet.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_segmentation_gauntlet.py)

この回が作った図は全部で **13 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_segmentation_gauntlet)

使用 op(ノートへ): [`blob_distance`](https://furuse.work/ops/blob/split/blob_distance.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`local_threshold`](https://furuse.work/ops/2d/segmentation/local_threshold.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`seg_dice_jaccard`](https://furuse.work/ops/segmentation/score/seg_dice_jaccard.html) · [`seg_score_card`](https://furuse.work/ops/segmentation/score/seg_score_card.html) · [`sg_watershed_gradient`](https://furuse.work/ops/2d/segment/sg_watershed_gradient.html) · [`sk_chan_vese`](https://furuse.work/ops/2d/segmentation/sk_chan_vese.html) · [`sk_felzenszwalb`](https://furuse.work/ops/2d/segmentation/sk_felzenszwalb.html) · [`sk_niblack`](https://furuse.work/ops/2d/segmentation/sk_niblack.html) · [`sk_sauvola`](https://furuse.work/ops/2d/segmentation/sk_sauvola.html) · [`sk_slic`](https://furuse.work/ops/2d/segmentation/sk_slic.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`watersheds`](https://furuse.work/ops/2d/segmentation/watersheds.html) · [`world_blobs_touching`](https://furuse.work/ops/segmentation/world/world_blobs_touching.html) · [`world_gradient_illumination`](https://furuse.work/ops/segmentation/world/world_gradient_illumination.html) · [`world_grains_voronoi`](https://furuse.work/ops/segmentation/world/world_grains_voronoi.html) · [`world_parts_with_shadow`](https://furuse.work/ops/segmentation/world/world_parts_with_shadow.html) · [`world_texture_regions`](https://furuse.work/ops/segmentation/world/world_texture_regions.html) · [`world_thin_structures`](https://furuse.work/ops/segmentation/world/world_thin_structures.html) · [`xsk_random_walker`](https://furuse.work/ops/2d/segmentation/xsk_random_walker.html)

### 時系列を 3-D として測るウィング ―― 動画は 1 つの体積

2-D の動画を (t, y, x) の 1 つの体積とみなすと、3-D の op ―― 連結成分、等値面、領域特徴 ―― がそのまま時間方向に効きます。合体したコロニーは時空間で Y 字になり、通過する車は (t, x) 画像の帯になり、波面の到達時刻は等値面になります。この部屋の 19 点はその実演です。

同時に、時間方向ならではの罠も出ました。フレーム格子への丸めは必ず遅らせ、画素の面積は合体を早める。誤リンクには向きの逆な 2 種類があり、誤り率 1 本では拡散係数がどちらへ外れるか決まらない。テンプレート追跡は見失うより先に静かにずれ、ずれた 152 フレーム全部が「見つけた」と報告する。

モーション拡大の展示は、この部屋でいちばん正直な結論を持っています。拡大率 200 まで機械精度で厳密に動くのに、測定の役には立たない ―― 拡大は人間に見せるための道具です。

## No.2026.055 —— 動画から固有振動数・減衰比・モード形状を同定する ―― f は最後まで生き残り、ζ が先に嘘をつく

[![動画から固有振動数・減衰比・モード形状を同定する ―― f は最後まで生き残り、ζ が先に嘘をつく](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/01_scene.png)

*↑ **動画から固有振動数・減衰比・モード形状を同定する ―― f は最後まで生き残り、ζ が先に嘘をつく** ―― 片持ち梁(Euler–Bernoulli 閉形式)の 3 モード自由減衰を、雑音・照明ちらつき 100 Hz・手ぶれ・ローリングシャッター入りの動画に合成し、位相法(phase_displacement)と PIV(piv_cross_correlate)で f_n / ζ_n / MAC を測る。f_n は 3 モードとも 0.06 Hz 以内で当たるが、同じ時系列から出した ζ_1 は半値幅 0.0778 / 包絡線 0.0188 / 当てはめ 0.0181(真値 0.02)と方法で 3 通り。振幅を 0.02→2 px で掃引すると壊れる順番は f → ζ → MAC_2 → MAC_3 で、位相法は 0.02 px で f_1 誤差 +0.030 Hz のまま ζ_1 が真値の 0.23 倍になる。fps 48.5 では照明の折り返しがちょうど 3.00 Hz = f_1 に乗り、輝度のゼロ点は ζ を出せず位相法は 0.0191 で生き残る。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/02_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/02_frames.png)

*↑ 測定の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/03_zero_point_spectrum_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/03_zero_point_spectrum.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/05_tip_waveform_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/05_tip_waveform.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/08_cliff_frequency_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/08_cliff_frequency.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/11_fps_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/11_fps_sweep.png)

*↑ この回の図*

[![動画(640 × 502、24 fps、292 コマ): 片持ち梁の自由減衰(A_1 = 0.2 px、雑音・照明ちらつき・手ぶれ・ローリングシャッター入り、撮影 128 fps を 5.3 倍のスローで再生)。画面のままでは梁は動いて見え](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/14_beam_video.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/14_beam_video.gif)

*↑ 動く図 ―― 動画(640 × 502、24 fps、292 コマ): 片持ち梁の自由減衰(A_1 = 0.2 px、雑音・照明ちらつき・手ぶれ・ローリングシャッター入り、撮影 128 fps を 5.3 倍のスローで再生)。画面のままでは梁は動いて見えないので、12 測点のたわみを 50 倍に誇張して重ねた(白 = 真値、青 = 位相法の測定)。下段は先端の変位が時刻とともに伸びる(白 = 真値、青 = 位相法、朱 = PIV)。最後のコマが同定結果: f_1 は 3.013 Hz(真 3.000)と当たるが、同じ時系列から出した ζ_1 は 半値幅 0.0778 / 包絡線 0.0188 / 当てはめ 0.0181(真 0.020)と方法で 3 通りに割れる。*

```
py -3.11 examples/poc_beam_modal_video.py
```

ソース: [examples/poc_beam_modal_video.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_beam_modal_video.py)

この回が作った図は全部で **14 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_beam_modal_video)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`data_to_pixel`](https://furuse.work/ops/annotate/plot/data_to_pixel.html) · [`envelope`](https://furuse.work/ops/oned/signal/envelope.html) · [`phase_displacement`](https://furuse.work/ops/motionmag/measure/phase_displacement.html) · [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`temporal_bandpass`](https://furuse.work/ops/motionmag/temporal/temporal_bandpass.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html)

## No.2026.060 —— 冷蔵輸送の温度記録 ―― ロガーを置いた場所が合否を決めている

[![冷蔵輸送の温度記録 ―― ロガーを置いた場所が合否を決めている](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cold_chain_excursion/01_scene_slices_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cold_chain_excursion/01_scene_slices.png)

*↑ **冷蔵輸送の温度記録 ―― ロガーを置いた場所が合否を決めている** ―― 12.0 m x 2.4 m のリーファー荷室の 12 時間を (t, y, x) の 1 つの体積(720 分 x 60 x 12 セル)として組み立て、吹き出し口からの距離・4 枚の壁からの侵入・扉開閉 5 回のパルス・荷の 1 次遅れ(空気 5 分 / 製品 64〜91 分)を既知の閉形式で仕込んだ図。真に不合格な製品セルは 108 / 490(22.0 %)なのに、製品にロガーを 1 個貼ると 82.4 % の置き方が「合格」と言う。要因を 1 つずつ止めると壊れ方が分かれる ―― 壁だけなら偽合格 95.5 %・偽不合格 0.0 %、壁を止めて扉だけ残すと偽不合格が 3.5 % 現れ、しかも製品に貼ったロガーは 100 % 合格と言う(短いパルスは製品に入らない)。崖は紙の上で予測できて、時定数の崖は「空気 + ロガー」の 2 段モデルで実測 19〜138 分に対し相対 18 % 以内、サンプリング間隔と 0.5 K 量子化の崖は予測と完全一致。同じ記録から出した 3 指標は「12 °C に許す時間」に直すと 60 / 276 / 197 分と 4.6 倍ずれ、720 セル中 82 セル(11.4 %)で合否が揃わない。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cold_chain_excursion/02_layout_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cold_chain_excursion/02_layout_maps.png)

*↑ 測定の図*

[![扉前の空気は跳ねるが製品には届かない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cold_chain_excursion/03_traces_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cold_chain_excursion/03_traces.png)

*↑ 扉前の空気は跳ねるが製品には届かない。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cold_chain_excursion/06_sweep_tau_positions_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cold_chain_excursion/06_sweep_tau_positions.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cold_chain_excursion/10_control_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cold_chain_excursion/10_control_maps.png)

*↑ この回の図*

[![1 枚目は render_volume_projection を幅方向から掛けた xray 投影(明るいほど幅方向に厚い)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cold_chain_excursion/13_excursion_body_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cold_chain_excursion/13_excursion_body.png)

*↑ 1 枚目は render_volume_projection を幅方向から掛けた xray 投影(明るいほど幅方向に厚い)。*

```
py -3.11 examples/poc_cold_chain_excursion.py
```

ソース: [examples/poc_cold_chain_excursion.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_cold_chain_excursion.py)

この回が作った図は全部で **16 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_cold_chain_excursion)

使用 op(ノートへ): [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`integrate_funct_1d`](https://furuse.work/ops/oned/function/integrate_funct_1d.html) · [`quantize`](https://furuse.work/ops/oned/signal/quantize.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`sample_funct_1d`](https://furuse.work/ops/oned/function/sample_funct_1d.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_label_shape_stats`](https://furuse.work/ops/volcolor/measure/vol_label_shape_stats.html) · [`vol_mip`](https://furuse.work/ops/2d/3d/vol_mip.html) · [`vol_profile_line`](https://furuse.work/ops/3d/probe/vol_profile_line.html) · [`vol_region_props`](https://furuse.work/ops/3d/regionprops/vol_region_props.html)

## No.2026.095 —— ひび割れの「幅」ではなく「伸び」を測る ―― 同じ壁を撮り返すと誤差の性質が変わる

[![ひび割れの「幅」ではなく「伸び」を測る ―― 同じ壁を撮り返すと誤差の性質が変わる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/01_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/01_frames.png)

*↑ **ひび割れの「幅」ではなく「伸び」を測る ―― 同じ壁を撮り返すと誤差の性質が変わる** ―― 1 px = 0.15 mm の壁を 3 年 12 期にわたり撮り返し、ひび割れの成長率 0.040 mm/年 を測る。2 値化して画素を数えるやり方は幅を 25.0 % 過小に言いながら成長率は +153.0 % 過大に言い、幅を凍結した対照群でも +0.0117 mm/年 の「成長」を出す(犯人はぼけ。要因を 1 つずつ止めて分けた)。輝度欠損を積分するやり方は成長率 +3.1 %、対照群では +0.0005 mm/年。★2 値化の成長率は初期の幅だけで 0.0241〜0.1038 mm/年 と動く ―― 1 画素の段差が観測窓に来たかどうかで決まる。*

[![2 値化は幅の偏りより**期ごとの跳ね**が問題。跳ねの正体はぼけと画素位相で、4 節と 3 節で分けて数える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/02_timeseries_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/02_timeseries.png)

*↑ 測定の図 ―― 2 値化は幅の偏りより**期ごとの跳ね**が問題。跳ねの正体はぼけと画素位相で、4 節と 3 節で分けて数える。*

[![ここに出る傾きはすべて『見かけの成長』。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/03_control_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/03_control.png)

*↑ ここに出る傾きはすべて『見かけの成長』。*

[![傾きが 0 に近いほど列方向の画素位相が揃い、2 値化は画面ごと 1 画素単位で跳ぶ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/05_phase_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/05_phase.png)

*↑ 傾きが 0 に近いほど列方向の画素位相が揃い、2 値化は画面ごと 1 画素単位で跳ぶ。*

[![横線を下回った時点で 0.040 mm/年 を 2σ で言える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/07_cliff_epochs_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/07_cliff_epochs.png)

*↑ 横線を下回った時点で 0.040 mm/年 を 2σ で言える。*

[![2 値化は臨界幅より細いと 0(未検出)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/09_cliff_width_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/09_cliff_width.png)

*↑ 2 値化は臨界幅より細いと 0(未検出)。*

[![動画(576 × 456、12 fps、378 コマ): 同じ壁を 3 年 12 期撮り返す。各期で中心線に直交する断面を 24 本、左から順に切り(橙 = いま切っている断面、右下が拡大)、下段左がその断面の輝度欠損 —— その面積が幅そ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/11_series_video.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/11_series_video.gif)

*↑ 動く図 ―― 動画(576 × 456、12 fps、378 コマ): 同じ壁を 3 年 12 期撮り返す。各期で中心線に直交する断面を 24 本、左から順に切り(橙 = いま切っている断面、右下が拡大)、下段左がその断面の輝度欠損 —— その面積が幅そのもの。24 本の平均が積分法の幅(青、測りかけの期は橙の輪で途中平均)、朱のマスクの画素を数えたのが 2 値化(朱)。真の幅は 1 期 0.010 mm ずつ伸びる(0.067 画素)。最後の当てはめで成長率は 真値 0.0400 / 積分法 0.0412 / 2 値化 0.1012 mm/年。2 値化は期ごとに跳ね(0.0185〜0.3386 mm)、跳ねの正体はぼけ(PSF σ 0.75〜1.24 px)と据え直しの画素位相。*

```
py -3.11 examples/poc_crack_width_timeseries.py
```

ソース: [examples/poc_crack_width_timeseries.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_crack_width_timeseries.py)

この回が作った図は全部で **11 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_crack_width_timeseries)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`data_to_pixel`](https://furuse.work/ops/annotate/plot/data_to_pixel.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html)

## No.2026.026 —— 構造物の微小振動を映像から測る ―― モーション拡大は「測る」役に立つのか

[![構造物の微小振動を映像から測る ―― モーション拡大は「測る」役に立つのか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/01_slit_scan_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/01_slit_scan.png)

*↑ **構造物の微小振動を映像から測る ―― モーション拡大は「測る」役に立つのか** ―― 既知振幅 0.02 px・3.7 Hz の振動を合成し、モーション拡大が測定に効くかを見た図。拡大率 α = 200 まで機械精度で厳密。だが拡大は測定精度を良くしない ―― 位相を α 倍すると雑音も α 倍。片持ち梁では位相相関が 0.30 と 0.00 px の面積平均 0.15 px という、どこにも存在しない数を返す。*

[![剛体を仮定する位相相関が返す 0.150 px は 0.30 と 0.00 の面積平均で、どの列の真値とも違う。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/02_beam_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/02_beam_profile.png)

*↑ 測定の図 ―― 剛体を仮定する位相相関が返す 0.150 px は 0.30 と 0.00 の面積平均で、どの列の真値とも違う。*

[![3.7 Hz を含む帯だけが 0 dB。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/03_band_selectivity_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/03_band_selectivity.png)

*↑ 3.7 Hz を含む帯だけが 0 dB。*

[![3.05 px までは機械精度、3.10 px で崩壊。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/04_amplitude_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/04_amplitude_cliff.png)

*↑ 3.05 px までは機械精度、3.10 px で崩壊。*

[![動画(480 × 480、12 fps、124 コマ): 3.7 Hz・0.1 px で揺れる表面(雑音 σ 0.01)。左が生の映像、右が 10 倍に拡大した映像で、朱の細い縦線は静止時の縞の山。生では揺れが表示 0.3 px で目に見え](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/05_magnify_video.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/05_magnify_video.gif)

*↑ 動く図 ―― 動画(480 × 480、12 fps、124 コマ): 3.7 Hz・0.1 px で揺れる表面(雑音 σ 0.01)。左が生の映像、右が 10 倍に拡大した映像で、朱の細い縦線は静止時の縞の山。生では揺れが表示 0.3 px で目に見えず、拡大後は 1 px 相当で見える。下段は変位の時系列: 白 = 真値、青 = 生の映像から測った値、橙 = 拡大後に測って 10 で割った値。振幅は 真 0.1000 / 生から 0.10012 / 拡大後 0.10013 px で、拡大しても測定は良くならない(見せるための道具)。*

```
py -3.11 examples/poc_motion_magnification.py
```

ソース: [examples/poc_motion_magnification.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_motion_magnification.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_motion_magnification)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`band_snr`](https://furuse.work/ops/motionmag/temporal/band_snr.html) · [`data_to_pixel`](https://furuse.work/ops/annotate/plot/data_to_pixel.html) · [`displacement_series`](https://furuse.work/ops/motionmag/measure/displacement_series.html) · [`motion_magnify`](https://furuse.work/ops/motionmag/magnify/motion_magnify.html) · [`phase_displacement`](https://furuse.work/ops/motionmag/measure/phase_displacement.html) · [`synthesize_translation`](https://furuse.work/ops/motionmag/synthesis/synthesize_translation.html) · [`temporal_band_power`](https://furuse.work/ops/motionmag/temporal/temporal_band_power.html) · [`temporal_bandpass`](https://furuse.work/ops/motionmag/temporal/temporal_bandpass.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html)

## No.2026.030 —— 粒子追跡を (行, 列, 時刻) の体積として測る ―― 誤リンクの向きは 1 種類ではない

[![粒子追跡を (行, 列, 時刻) の体積として測る ―― 誤リンクの向きは 1 種類ではない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/05_tracking_links.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/05_tracking_links.gif)

*↑ **粒子追跡を (行, 列, 時刻) の体積として測る ―― 誤リンクの向きは 1 種類ではない** ―― 400 個の粒子の動画を追跡し、軌跡から拡散係数 D を読んだ図。曖昧な誤リンクは D を 0.925 倍に下げ、欠測による誤リンクは同じ動画で 3.429 倍に上げる ―― 誤り率 1 本では向きが決まらない。効くのは 1 対 1 制約ではなく、上限距離のゲート 1 行(3.429 → 1.304)。*

[![時間最大投影では粒子が尾を引く(= 軌跡)。kymograph は行 90-101 の帯を縦(時間)へ積んだもので、筋の傾きがそのまま列方向の速度。縦は 5 倍に拡大。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/01_spacetime_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/01_spacetime.png)

*↑ 測定の図 ―― 時間最大投影では粒子が尾を引く(= 軌跡)。kymograph は行 90-101 の帯を縦(時間)へ積んだもので、筋の傾きがそのまま列方向の速度。縦は 5 倍に拡大。*

[![縦軸は常用対数(0 が真値)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/02_density_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/02_density_bias.png)

*↑ 縦軸は常用対数(0 が真値)。*

[![真値で割った比。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/03_msd_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/03_msd.png)

*↑ 真値で割った比。*

[![曖昧と欠測を分けて数えると、D の外れる向きが説明できる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/04_density_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/04_density_table.png)

*↑ 曖昧と欠測を分けて数えると、D の外れる向きが説明できる。*

```
py -3.11 examples/poc_particle_tracking.py
```

ソース: [examples/poc_particle_tracking.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_particle_tracking.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_particle_tracking)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_local_maxima`](https://furuse.work/ops/3d/feature/vol_local_maxima.html)

## No.2026.111 —— 沈下したのか、測り直しただけなのか ―― 検出限界で切ると景色が変わる

[![沈下したのか、測り直しただけなのか ―― 検出限界で切ると景色が変わる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_settlement_significance/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_settlement_significance/01_scene.png)

*↑ **沈下したのか、測り直しただけなのか ―― 検出限界で切ると景色が変わる** ―― トンネル掘進で沈んだ 24 x 16 m の路面を 2 時期の点群で測る。ゼロ点の最近傍距離(C2C)は変化ゼロでも中央値 47.74 mm を返し(正体は点間隔)、符号も持たない。M3C2 の平均は -2.43 mm で真値と一致するが、LoD を超えて有意なのは 275/551 core(49.9 %)でその平均は -4.34 mm ―― 1 行の平均はどちらとも一致しない。LoD は沈下ではなく面の地図で、ゾーンごとに 0.51〜3.58 mm。有意なものだけ足すと体積は 0.8569 → 0.7643 m3 に痩せ、その欠け量は core ごとの LoD から先に計算できる(予測 0.867 / 実測 0.892)。*

[![有意の地図は真値の地図をよく復元する(TPR 88.7 % / FPR 3.6 %)。ただし縁が痩せる —— そこが 7 節の体積の話。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_settlement_significance/02_map_change_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_settlement_significance/02_map_change.png)

*↑ 測定の図 ―― 有意の地図は真値の地図をよく復元する(TPR 88.7 % / FPR 3.6 %)。ただし縁が痩せる —— そこが 7 節の体積の話。*

[![上の帯(砂利の路肩)は粗さ 15 mm・密度半分なので LoD が跳ね上がる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_settlement_significance/03_map_lod_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_settlement_significance/03_map_lod.png)

*↑ 上の帯(砂利の路肩)は粗さ 15 mm・密度半分なので LoD が跳ね上がる。*

[![予測は 1.96·σ·sqrt(1/na+1/nb)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_settlement_significance/04_lod_by_zone_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_settlement_significance/04_lod_by_zone.png)

*↑ 予測は 1.96·σ·sqrt(1/na+1/nb)。*

[![LoD は雑音しか見ていないので、系統誤差はそのまま「有意な沈下」として通る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_settlement_significance/05_map_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_settlement_significance/05_map_bias.png)

*↑ LoD は雑音しか見ていないので、系統誤差はそのまま「有意な沈下」として通る。*

[![崖の位置はそのゾーンの LoD で決まる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_settlement_significance/06_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_settlement_significance/06_cliff.png)

*↑ 崖の位置はそのゾーンの LoD で決まる。*

```
py -3.11 examples/poc_settlement_significance.py
```

ソース: [examples/poc_settlement_significance.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_settlement_significance.py)

この回が作った図は全部で **7 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_settlement_significance)



## No.2026.041 —— テンプレート追跡は「見失う」より先に「静かにずれる」

[![テンプレート追跡は「見失う」より先に「静かにずれる」](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/01_ncc_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/01_ncc_maps.png)

*↑ **テンプレート追跡は「見失う」より先に「静かにずれる」** ―― 既知の相似変換でカメラを動かし、テンプレート追跡が「見失う」「静かにずれる」「自信満々で間違える」の 3 通りで壊れるのを見た図。ずれていた 152 フレームの 152 フレーム全部が、遮蔽なしで校正したピークのしきい値を通って「見つけた」と報告した。真値なしで測れる絶対量は往復追跡の不一致だけ。*

[![同じ遮蔽率でも、そっくりな別物体が視野に居るだけで崖がはるかに手前へ来る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/02_occlusion_vs_twin_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/02_occlusion_vs_twin.png)

*↑ 測定の図 ―― 同じ遮蔽率でも、そっくりな別物体が視野に居るだけで崖がはるかに手前へ来る。*

[![更新なしは平らなまま。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/03_drift_curves_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/03_drift_curves.png)

*↑ 更新なしは平らなまま。*

[![得意な崖が逆。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/04_confidence_auc_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/04_confidence_auc.png)

*↑ 得意な崖が逆。*

[![動画(30 フレーム + 最後で 2 秒止め、5 fps): 同じ 1 枚目のテンプレートを更新なし全域探索で追う(ゼロ点)。3 フレーム目から真の対象の 70 % を左から隠す。左 = 平坦な遮蔽物: ピークは平均 0.745 まで下がっ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/05_twin_vs_flat_occluder.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/05_twin_vs_flat_occluder.gif)

*↑ 動く図 ―― 動画(30 フレーム + 最後で 2 秒止め、5 fps): 同じ 1 枚目のテンプレートを更新なし全域探索で追う(ゼロ点)。3 フレーム目から真の対象の 70 % を左から隠す。左 = 平坦な遮蔽物: ピークは平均 0.745 まで下がってしきい値 0.843 を割る(「見失った?」と正直に言う)が、位置は平均 0.78 px で追えている(見失い 0 / 27)。右 = そっくりな別物体が 51 px 離れて一緒に流れる: 最初の遮蔽フレームで複製に乗り換え、平均誤差 46.13 px、見失い 27 / 27 —— それなのにピークは平均 0.856 でしきい値を超え、27 / 27 フレームで「見つけた」と報告する。下段の紫(突出度)は右で平均 0.111 としきい値 0.304 を割って取り違えを疑うが、追えている左でも平均 0.203 で同じく割る —— 突出度が測っているのは曖昧さで、正しさではない*

```
py -3.11 examples/poc_template_tracking.py
```

ソース: [examples/poc_template_tracking.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_template_tracking.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_template_tracking)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`ncc_locate`](https://furuse.work/ops/2d/matching/ncc_locate.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`shape_locate`](https://furuse.work/ops/2d/matching/shape_locate.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html)

## No.2026.044 —— 成長のタイムラプスを時空間の連結成分として測る

[![成長のタイムラプスを時空間の連結成分として測る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/01_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/01_frames.png)

*↑ **成長のタイムラプスを時空間の連結成分として測る** ―― 広がって合体するコロニーの動画を (t, y, x) の体積として 3-D 連結成分で読んだ図。画素が面積を持つせいで合体は早く見え(組 0-1 で -1.16 フレーム)、フレーム格子への丸めは遅らせる(+0.94) ―― 逆向きなので合計は小さく見える。`vol_label` の既定 26 近傍は、隙間 0.92 のニアミスを合体させた。*

[![縦が時間(下向き、4 倍に拡大)、横が列。2 本の管が合わさる高さがそのまま合体時刻。色は 3-D ラベル。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/02_ystructure_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/02_ystructure.png)

*↑ 測定の図 ―― 縦が時間(下向き、4 倍に拡大)、横が列。2 本の管が合わさる高さがそのまま合体時刻。色は 3-D ラベル。*

[![横軸はどちらも『何倍粗くしたか』。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/03_sampling_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/03_sampling.png)

*↑ 横軸はどちらも『何倍粗くしたか』。*

[![空間側は格子の位相でこれだけ動く(偏りより大きい)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/04_sampling_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/04_sampling_table.png)

*↑ 空間側は格子の位相でこれだけ動く(偏りより大きい)。*

[![動画(48 フレーム): 左は二値のフレームを 3-D の家族ラベルで塗ったもの(白の細線 = 真の連続円。色は体積全体で決まる家族なので、合体する 2 個は合体の前から同じ色)。右は合体する 2 組の中心を通る行の時空間断面が時刻とともに](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/05_growth_merge.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/05_growth_merge.gif)

*↑ 動く図 ―― 動画(48 フレーム): 左は二値のフレームを 3-D の家族ラベルで塗ったもの(白の細線 = 真の連続円。色は体積全体で決まる家族なので、合体する 2 個は合体の前から同じ色)。右は合体する 2 組の中心を通る行の時空間断面が時刻とともに現れ、Y 字の分かれ目が合体時刻になる(白の点線 = 閉形式の真値 7.99 / 30.09、橙 = 観測 7 / 31)。下はフレームを独立に数えた塊の数で、減ったのは t = 7, 31, 47。最後の t = 47 の減少はニアミス 4-5(最終フレームでも隙間 0.92)を 8 近傍が繋いだ偽の合体で、真の個数は 5 のまま。*

```
py -3.11 examples/poc_timelapse_growth.py
```

ソース: [examples/poc_timelapse_growth.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_timelapse_growth.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_timelapse_growth)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_region_props`](https://furuse.work/ops/3d/regionprops/vol_region_props.html)

## No.2026.045 —— (x, y, t) で数える ―― 通過台数とオクルージョン、そして L/V という 1 つの定数

[![(x, y, t) で数える ―― 通過台数とオクルージョン、そして L/V という 1 つの定数](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/01_per_frame_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/01_per_frame.png)

*↑ **(x, y, t) で数える ―― 通過台数とオクルージョン、そして L/V という 1 つの定数** ―― 車を流した合成動画で、フレームごとの計数・仮想ループ・(t, x) スリット画像の連結成分を並べた図。フレームごとの最大値は通過 10 台に対し 7 ―― 別の量を測っている。破綻の条件は 3 つとも車長 ÷ 速度 = L/V(9.0 フレーム)で書け、フレーム間隔 16 では帯が千切れて 10 → 49 台。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/02_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/02_scene.png)

*↑ 測定の図*

[![トラックは画像の 50 行から 99 行を占めるので、遠い車線の計数行 63 を横切る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/03_tall_vehicles_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/03_tall_vehicles.png)

*↑ トラックは画像の 50 行から 99 行を占めるので、遠い車線の計数行 63 を横切る。*

[![全部の帯を数えると千切れて過大に(実測は最大 67 だが、他の系列が潰れるので 20 で頭打ちにして描いている)、計数列と交わる帯だけなら見逃しだけ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/04_framerate_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/04_framerate.png)

*↑ 全部の帯を数えると千切れて過大に(実測は最大 67 だが、他の系列が潰れるので 20 で頭打ちにして描いている)、計数列と交わる帯だけなら見逃しだけ。*

[![動画(768 × 422、10 fps、210 コマ = 撮った速さ): 2 車線の道路を 18 秒。上段はカメラの画に前景マスク(橙)と計数列(黄の縦線)を重ねたもの、下段は 2 車線の計数行を時間方向に積んだスリット画像 (t, x) ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/05_counting_video.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/05_counting_video.gif)

*↑ 動く図 ―― 動画(768 × 422、10 fps、210 コマ = 撮った速さ): 2 車線の道路を 18 秒。上段はカメラの画に前景マスク(橙)と計数列(黄の縦線)を重ねたもの、下段は 2 車線の計数行を時間方向に積んだスリット画像 (t, x) が上から伸びていく —— 車 1 台が斜めの帯 1 本になり、傾きが速度。見出しの数字は時刻までの累積で、最後は 真値 10 / 仮想ループ 10 / スリット法 10 台と同点(途中で真値が遅れて見えるのは、真値を車体の中心で、ループとスリットを車体の先端で数えるため)。フレームごとに連結成分を数えるゼロ点は最大 7 で、「いま写っている数」を数えているだけ。*

```
py -3.11 examples/poc_traffic_counting.py
```

ソース: [examples/poc_traffic_counting.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_traffic_counting.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_traffic_counting)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`data_to_pixel`](https://furuse.work/ops/annotate/plot/data_to_pixel.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html)

## No.2026.089 —— 庫内の滞留はどこで生まれたか ―― 待ちの種類を分けずに数えると全部「混雑」になる

[![庫内の滞留はどこで生まれたか ―― 待ちの種類を分けずに数えると全部「混雑」になる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/09_scene_layout_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/09_scene_layout.png)

*↑ **庫内の滞留はどこで生まれたか ―― 待ちの種類を分けずに数えると全部「混雑」になる** ―― 物流センターの平面図と 26 台の軌跡を合成し、補充待ち・人待ち・通路の干渉・システム待ち・欠品を既知の時刻と長さで仕込んで、動画を (t, y, x) の 1 つの体積として読んだ図。ゼロ点の「総滞留時間」321.5 秒のうち真の待ちは 198.0 秒(61.6 %)で、残りは生産的な作業と徐行。人待ちを全部止めても通路の干渉を全部止めてもゼロ点は -39.0 / -38.0 秒しか違わず原因が決まらないが、種類別なら該当の型だけが 0 に落ちる。欠品は滞留を -17.0 秒しか動かさないのに余計な移動を 94.6 m 生み、崖は 3 軸で別々の型を殺す ―― 標本間隔は短い待ち、遮蔽は棚に張りつく型、ID の併合は 2 人の関係を読む型。*

[![ヒートマップは場所を当てるが、「1 人が長く待った」と「何人も短く止まった」を分けない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/01_heat_ambiguity_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/01_heat_ambiguity.png)

*↑ 測定の図 ―― ヒートマップは場所を当てるが、「1 人が長く待った」と「何人も短く止まった」を分けない。*

[![ゼロ点はこの表を 1 つの数字に畳む。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/02_types_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/02_types.png)

*↑ ゼロ点はこの表を 1 つの数字に畳む。*

[![短い待ち(通路の干渉・欠品)から先に消える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/04_sweep_interval_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/04_sweep_interval.png)

*↑ 短い待ち(通路の干渉・欠品)から先に消える。*

[![天井カメラ 2 台。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/07_sweep_occlusion_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/07_sweep_occlusion.png)

*↑ 天井カメラ 2 台。*

[![上段は通路が明るい(人が通っただけ)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/10_xyt_projection_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/10_xyt_projection.png)

*↑ 上段は通路が明るい(人が通っただけ)。*

```
py -3.11 examples/poc_warehouse_flow.py
```

ソース: [examples/poc_warehouse_flow.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_warehouse_flow.py)

この回が作った図は全部で **12 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_warehouse_flow)

使用 op(ノートへ): [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`face_areas`](https://furuse.work/ops/3d/mesh_process/face_areas.html) · [`mesh_volume`](https://furuse.work/ops/3d/mesh_process/mesh_volume.html) · [`occupancy_grid`](https://furuse.work/ops/3d/occupancy/occupancy_grid.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`vol_dilate`](https://furuse.work/ops/2d/3d/vol_dilate.html) · [`vol_erode`](https://furuse.work/ops/2d/3d/vol_erode.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_opening_ball`](https://furuse.work/ops/2d/3d/vol_opening_ball.html) · [`vol_region_props`](https://furuse.work/ops/3d/regionprops/vol_region_props.html)

## No.2026.053 —— 到達時刻面を (x, y, t) の等値面として取り出す

[![到達時刻面を (x, y, t) の等値面として取り出す](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/01_dt_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/01_dt_sweep.png)

*↑ **到達時刻面を (x, y, t) の等値面として取り出す** ―― 点源から広がる波面の到達時刻面を (x, y, t) 体積の等値面として取り出した図。ゼロ点(初めて超えたフレーム番号)の偏りは Δt/2 で枚数では消えず、線形補間で 27 倍(0.0209 ms)。放物線補間は線形に負け、しきい値がガウス波形の変曲点 θ = 0.6065 にあるとき線形が最良(3.8 倍差)。*

[![変曲点 θ=0.6065 では線形が 3.8 倍勝ち、θ=0.2 では放物線が 3.6 倍勝つ。交点は θ≈0.35 と θ≈0.75。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/02_threshold_crossover_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/02_threshold_crossover.png)

*↑ 測定の図 ―― 変曲点 θ=0.6065 では線形が 3.8 倍勝ち、θ=0.2 では放物線が 3.6 倍勝つ。交点は θ≈0.35 と θ≈0.75。*

[![各帯の中央値。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/03_merge_line_speed_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/03_merge_line_speed.png)

*↑ 各帯の中央値。*

[![差は上下 99 % 分位(±0.0327 ms)で切った。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/04_arrival_surface_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/04_arrival_surface.png)

*↑ 差は上下 99 % 分位(±0.0327 ms)で切った。*

[![動画(624 × 586、20 fps、171 コマ): 2 つの点源から波面が広がる(源 B は 4 ms 遅れて点火)。左が波面の強度、右は線形補間で出した到達時刻を、波面が通り過ぎた画素から順に塗ったもの —— 動画 (t, y, x](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/05_arrival_video.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/05_arrival_video.gif)

*↑ 動く図 ―― 動画(624 × 586、20 fps、171 コマ): 2 つの点源から波面が広がる(源 B は 4 ms 遅れて点火)。左が波面の強度、右は線形補間で出した到達時刻を、波面が通り過ぎた画素から順に塗ったもの —— 動画 (t, y, x) を1 つの体積とみなしたときの等値面が、こうして 1 枚の面になる。点線は撮る前に閉形式で予測した合流線。下段は行 72 の断面で、白 = 真値、橙 = ゼロ点(初めてしきい値を超えたコマの時刻、1 ms の階段)、青 = 線形補間。最後に全画素の誤差: ゼロ点 RMS 0.568 ms(偏り +0.489)、線形補間 RMS 0.0209 ms(27 倍)。*

```
py -3.11 examples/poc_xyt_event_surface.py
```

ソース: [examples/poc_xyt_event_surface.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_xyt_event_surface.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_xyt_event_surface)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`data_to_pixel`](https://furuse.work/ops/annotate/plot/data_to_pixel.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html) · [`vertex_normals`](https://furuse.work/ops/3d/mesh_process/vertex_normals.html) · [`vol_edge_probe`](https://furuse.work/ops/3d/probe/vol_edge_probe.html)

## No.2026.127 —— 動画を空間 × 時間の立方体として見る ―― 何が・どこを・いつ通ったかが 1 枚の立体に出る

[![動画を空間 × 時間の立方体として見る ―― 何が・どこを・いつ通ったかが 1 枚の立体に出る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/02_cube_orbit.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/02_cube_orbit.gif)

*↑ **動画を空間 × 時間の立方体として見る ―― 何が・どこを・いつ通ったかが 1 枚の立体に出る** ―― Video Summagator(Nguyen・Niu・Liu、ACM CHI 2012)は動画を (x, y, t) の立方体にし、動かない背景を薄く・動く物体を濃く描いて、切ったり回したりして場面へ飛ぶ道具。同じことを新族 videocube の 6 op(numpy + scipy のみ、新しい型なし)で再実装した: 時間差分の大きさを不透明度に(video_spacetime_cube)、任意視点の前から後ろへの α 合成で軌跡を時刻の色(青 = 始め → 赤 = 終わり)に塗る(vol_render_transfer)、断面(video_cube_cut: x–t のスリットスキャン)、回す(video_cube_orbit)、代表フレーム(video_summary_keyframes)、アニメーション GIF に書く(video_write_gif、使い回しの出口)。監視カメラ風の合成クリップ(通過の行・時刻・速度が既知の 3 物体)で、スリットスキャンの筋の最初の行と傾きから読んだ出現時刻と速度は真値と一致(±0 フレーム、速度 +2.00 / −1.50 / +1.00)、代表フレームは 3 物体すべての出現直後を捉える(乱数で 4 枚選ぶと平均 0.21 物体)。同じ op でハエの脳の EM 連続断面(CREMI sample A、32 断面、生データは commit しない)を立方体にすると、膜が奥行きの色で塗られた管になって神経突起が断面を貫いて走る。Studio では Tools ▸ Video cube が対話的に動く(ドラッグで回転、断面のスライダ、断面をクリックでそのフレームへ、.npy / GIF / 動画 / .hdf のスタックを開く、Save GIF)。*

[![the clip as a space-time cube (time = depth to the right): moving objects leave trails coloured by time (blue = start, r](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/01_cube_time_coloured_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/01_cube_time_coloured.png)

*↑ 測定の図 ―― the clip as a space-time cube (time = depth to the right): moving objects leave trails coloured by time (blue = start, red = end); the static background is a faint grey*

[![x-t slit scans of the three rows: a streak's first row is the onset, its slope is the speed (yellow ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/03_slit_scans_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/03_slit_scans.png)

*↑ x-t slit scans of the three rows: a streak's first row is the onset, its slope is the speed (yellow line = injected onset)*

[![video_summary_keyframes picks the frames right after each object appears; the head-on cube is the wh](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/04_keyframes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/04_keyframes.png)

*↑ video_summary_keyframes picks the frames right after each object appears; the head-on cube is the whole clip in one image*

[![a real clip from this repo (a turntable GIF, 40 frames of 160x160): a rotating object becomes a heli](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/05_turntable_cube_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/05_turntable_cube.png)

*↑ a real clip from this repo (a turntable GIF, 40 frames of 160x160): a rotating object becomes a helix in the space-time cube*

[![the same cube operators on a z-stack of EM sections (CREMI sample A, 32 sections of 256^2 (adult Dro](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/06_em_stack_cube_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/06_em_stack_cube.png)

*↑ the same cube operators on a z-stack of EM sections (CREMI sample A, 32 sections of 256^2 (adult Drosophila FAFB)): membranes become tubes running thr…*

[![the EM stack rotating: neurites are the tubes, coloured by depth; the same operator that rotated the surveillance clip](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/07_em_stack_orbit.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_video_cube/07_em_stack_orbit.gif)

*↑ 動く図 ―― the EM stack rotating: neurites are the tubes, coloured by depth; the same operator that rotated the surveillance clip*

```
py -3.11 examples/poc_video_cube.py
```

ソース: [examples/poc_video_cube.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_video_cube.py)

この回が作った図は全部で **7 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_video_cube)

使用 op(ノートへ): [`intensity`](https://furuse.work/ops/2d/features/intensity.html) · [`video_cube_cut`](https://furuse.work/ops/videocube/cube/video_cube_cut.html) · [`video_cube_orbit`](https://furuse.work/ops/videocube/render/video_cube_orbit.html) · [`video_spacetime_cube`](https://furuse.work/ops/videocube/cube/video_spacetime_cube.html) · [`video_summary_keyframes`](https://furuse.work/ops/videocube/summary/video_summary_keyframes.html) · [`video_write_gif`](https://furuse.work/ops/videocube/export/video_write_gif.html) · [`vol_render_transfer`](https://furuse.work/ops/videocube/render/vol_render_transfer.html)

## No.2026.128 —— 生きている組織の 3D+t を古典手法だけで短い 3D 動画像に ―― 増幅・流れ・補間・高さ場、全部に真値

[![生きている組織の 3D+t を古典手法だけで短い 3D 動画像に ―― 増幅・流れ・補間・高さ場、全部に真値](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/01_beating_orbit.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/01_beating_orbit.gif)

*↑ **生きている組織の 3D+t を古典手法だけで短い 3D 動画像に ―― 増幅・流れ・補間・高さ場、全部に真値** ―― 動画生成 AI は「もっともらしい動き」を発明する。新族 live4d(14 op、numpy + scipy のみ、新語は volseq = 体積の時系列 (T, Z, Y, X) の 1 つ)は内容を発明しない代わりに、実在する動きを見える形にする 4 つの道を用意し、どれも真値つきの合成系列で数字に固定した。(1) 増幅: 半径が 0.1 voxel(目に見えない)だけ拍動する殻を volseq_magnify_motion(Wu らの Eulerian 線形拡大の 3 次元版)で 8 倍にすると、読み取った半径の振幅は 7.89 倍、周期は不変。(2) 流れ: 既知の速さ ±0.75 voxel/frame で分かれる 2 つの塊の変位場(vol_flow_3d、3 次元 Lucas–Kanade)は勾配のある場所で +0.776 / −0.776、軌跡(volseq_pathline_render)は時刻の色で 1 枚の立体になる。(3) 補間: 2 倍のレートで作った系列を半分に間引いて volseq_interpolate_flow で埋めると、1 コマの動きが塊の大きさの 2 倍のとき抜いた真のフレームとの RMSE は 0.0016(線形ブレンドは 0.0207)—— ただし動きが約 0.8 σ より小さい領域ではブレンドで足り、warp の再標本化が少し損をする(正直に図にした)。(4) 高さ場: 焦点掃引の時系列(動く山)から focus_sweep_height_video が起こした高さは真値と RMSE 0.31 枚。Cell Tracking Challenge の生きた細胞の 3D+t(Fluo-N3DH-CHO、生データは commit しない)も同じ経路で回る。*

[![radius of the shell read from each volume: the measured beat (0.10 voxel) is below one voxel; after magnification it fol](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/02_radius_trace_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/02_radius_trace.png)

*↑ 測定の図 ―― radius of the shell read from each volume: the measured beat (0.10 voxel) is below one voxel; after magnification it follows alpha x truth*

[![pathlines of particles carried by the 3-D flow of the dividing blob, coloured by time (blue = start,](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/03_pathlines_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/03_pathlines.png)

*↑ pathlines of particles carried by the 3-D flow of the dividing blob, coloured by time (blue = start, red = end); the faint grey is the first volume*

[![a frame removed from a 2x-rate series (motion 5 voxel = 2 sigma per step) re-created two ways (max p](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/05_interpolation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/05_interpolation.png)

*↑ a frame removed from a 2x-rate series (motion 5 voxel = 2 sigma per step) re-created two ways (max projections): the linear blend shows two ghosts per…*

[![error of the re-created frames against the removed ones, as the motion per step grows: below about o](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/06_interpolation_regimes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/06_interpolation_regimes.png)

*↑ error of the re-created frames against the removed ones, as the motion per step grows: below about one blob width a linear blend is as good (the warp'…*

[![Fluo-N3DH-CHO/01 (12 volumes of (5, 111, 128), y/x 1/4): pathlines of the 3-D flow between consecuti](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/09_ctc_pathlines_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/09_ctc_pathlines.png)

*↑ Fluo-N3DH-CHO/01 (12 volumes of (5, 111, 128), y/x 1/4): pathlines of the 3-D flow between consecutive volumes, coloured by time*

[![the same pathlines orbited: two straight bundles leaving the split point at +/-0.75 voxel/frame](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/04_pathlines_orbit.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/04_pathlines_orbit.gif)

*↑ 動く図 ―― the same pathlines orbited: two straight bundles leaving the split point at +/-0.75 voxel/frame*

[![height field recovered from a focus sweep series (a moving bump, 11 planes), shaded and coloured by height (blue = low, ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/07_focus_surface.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/07_focus_surface.gif)

*↑ 動く図 ―― height field recovered from a focus sweep series (a moving bump, 11 planes), shaded and coloured by height (blue = low, red = high); RMSE 0.31 planes*

[![Fluo-N3DH-CHO/01 (12 volumes of (5, 111, 128), y/x 1/4): the live volumes orbited while time advances (intensity as opac](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/08_ctc_orbit.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_live4d/08_ctc_orbit.gif)

*↑ 動く図 ―― Fluo-N3DH-CHO/01 (12 volumes of (5, 111, 128), y/x 1/4): the live volumes orbited while time advances (intensity as opacity)*

```
py -3.11 examples/poc_live4d.py
```

ソース: [examples/poc_live4d.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_live4d.py)

この回が作った図は全部で **10 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_live4d)

使用 op(ノートへ): [`blend`](https://furuse.work/ops/shape2d/morph/blend.html) · [`focus_sweep_height_video`](https://furuse.work/ops/live4d/render/focus_sweep_height_video.html) · [`focus_sweep_surface_video`](https://furuse.work/ops/live4d/render/focus_sweep_surface_video.html) · [`vol_flow_3d`](https://furuse.work/ops/live4d/flow/vol_flow_3d.html) · [`volseq_interpolate_flow`](https://furuse.work/ops/live4d/time/volseq_interpolate_flow.html) · [`volseq_magnify_motion`](https://furuse.work/ops/live4d/time/volseq_magnify_motion.html) · [`volseq_pathline_orbit`](https://furuse.work/ops/live4d/flow/volseq_pathline_orbit.html) · [`volseq_pathline_render`](https://furuse.work/ops/live4d/flow/volseq_pathline_render.html) · [`volseq_render_orbit`](https://furuse.work/ops/live4d/render/volseq_render_orbit.html) · [`volseq_synth_beating`](https://furuse.work/ops/live4d/synth/volseq_synth_beating.html) · [`volseq_synth_dividing`](https://furuse.work/ops/live4d/synth/volseq_synth_dividing.html)

## No.2026.170 —— 卓球の球を先駆者の目で測る ―― 真値つきの台で、多カメラ追跡・三角測量・軌道予測・跳ね・スピンを定理で採点する

[![卓球の球を先駆者の目で測る ―― 真値つきの台で、多カメラ追跡・三角測量・軌道予測・跳ね・スピンを定理で採点する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/01_rig_view_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/01_rig_view.png)

*↑ **卓球の球を先駆者の目で測る ―― 真値つきの台で、多カメラ追跡・三角測量・軌道予測・跳ね・スピンを定理で採点する** ―― ロボット卓球の視覚は 1988 年から同じ構えでできている: 複数のカメラで球を見つけ、三角測量で 3-D の点にし、抗力とマグヌスの入った運動方程式で先を読み、跳ねを越えて予測し、できれば模様からスピンを測る。この展示はその一式を numpy の op で組み、世界の側が持つ真値(球の中心・姿勢・接触時刻・角速度は生成時に決めた式)で採点する。まず力学の定理: 抗力もマグヌスも 0 なら RK4 の飛翔は閉形式の放物線と 1e-12、放物線の最小二乗は g = 9.81 を 4.0e-15 で戻す。乱数 500 通りの衝突(e ∈ [0.3, 1]、μ ∈ [0, 0.6])で接触点まわりの角運動量の相対誤差は最大 4.9e-16、転がりに移るのが 136、滑ったままが 364。30.5 cm から落とすと(e = 0.90)頂点は 24.7、20.0、16.2、13.1 cm で閉形式 e^{2k}h₀ と 3.0e-07、最初の跳ね 24.7 cm は ITTF の規格 24〜26 cm の中、頂点列からも接触間隔からも e = 0.900000 が戻り、止まるまでの総時間 4.736 s は閉形式 4.738 s と並ぶ。次にITTF の台に 40 mm の球(模様 14 個)を置き、トップスピン(ω = 240 rad/s)の打球を 100 fps で 0.6 秒、カメラ 2 台 + 近接 1 台で撮る(61 コマ × 2 台の描画に 22.0 s)。真値の接触は t = 0.3094 s、点 (0.507, 0.052)、v [5.15, −0.28, −2.65] → [5.01, −0.17, 2.39]、ω [0, 240, 0] → [8.5, 250.6, 0](grip)。色度で検出した中心は 122 / 122 コマで見つかり真値の投影と中央値 0.152 px、90 % 点 0.299 px、最大 2.094 px(像の半径 ≈ 4.3 px)。DLT の三角測量は真値の投影から 3.8e-15 m、検出からは中央値 1.61 mm、90 % 点 4.25 mm、最大 23.56 mm(再投影 rms の中央値 0.094 px)。等加速度の Kalman は放物線に厳密なので真値を入れた新息は最大 8.2e-09 m(抗力 + マグヌスの真値だと 2.3e-03 m = モデルの外)、検出からの速度の誤差は中央値 0.074 m/s(|v| ≈ 5.9 m/s)。z の局所最小は t = 0.31 で真値と 0.6 ms。跳ねる前の 15 コマ(0.15 s)から 6 パラメータの Gauss–Newton で初期状態を当て(真値の軌跡なら 3.2e-13 で戻る)、跳ねを越えて予測すると、真のスピンを知っていれば着地点は 0.4 cm(時刻 0.5 ms)、スピンを無視すると 20.2 cm、放物線で当てると真のスピンでも 6.6 cm 外れる —— その差がマグヌスの分。跳ね際の近接カメラ(1000 fps、ストロボ)で模様が 2 つ以上対応づいたコマ組 19 / 19 を Kabsch で回した角速度の中央値は [1.7, 256.6, −2.1] rad/s(真値 [8.5, 250.6, 0]、|ω| 2394 rpm)で相対誤差 3.7 %。反発係数は前後 12 コマずつを運動方程式で当てて v_z −2.637 → 2.403、e = 0.9114(真値 0.90)。正直に: 放物線の当てはめだと 0.9398 で、抗力とマグヌスを g に吸って 4.4 % ずれる。球の検出は色が既知の合成映像で実写の照明・ぼけ・背景は無く、空力係数は文献の代表値で真値も同じ式(空力の門ではない)。10 門、42.0 s。最後に、自由に動くラケット 2 本(板 15 × 16 cm、速さ ≤ 6 m/s)で打ち合う: 前回に近い少しずらした位置へ返す送り合いは上限 12 本まで続き、遠い隅を速く狙う攻める側が入ると 9 本で終わる(打つ前に真の物理で先読みして外すなら巻き戻す仕組みつき、攻める側は 99 回巻き戻しても外した)。知覚の位置に雑音を足すと 5 cm までは本数が変わらず(板の余裕)、10 cm で 2 本 —— ラリーの本数が知覚・予測・制御の一式を採点する指標。*

[![カメラ 1 の像での球の軌跡: 真値の投影(線)と検出(点)。中心の誤差の中央値 0.15 px。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/02_tracks_2d_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/02_tracks_2d.png)

*↑ 測定の図 ―― カメラ 1 の像での球の軌跡: 真値の投影(線)と検出(点)。中心の誤差の中央値 0.15 px。*

[![x–z 面の軌跡。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/03_trajectory_xz_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/03_trajectory_xz.png)

*↑ x–z 面の軌跡。*

[![30.5 cm から落とした球(e = 0.90)の頂点: 閉形式 e^{2k}h₀ と 1e-6 で一致し、最初の跳ね 24.7 cm は ITTF の規格 24〜26 cm の中。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/04_drop_apexes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/04_drop_apexes.png)

*↑ 30.5 cm から落とした球(e = 0.90)の頂点: 閉形式 e^{2k}h₀ と 1e-6 で一致し、最初の跳ね 24.7 cm は ITTF の規格 24〜26 cm の中。*

[![跳ね際の近接カメラ(1000 fps、256 × 256、20°)の 4 コマ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/05_spin_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/05_spin_frames.png)

*↑ 跳ね際の近接カメラ(1000 fps、256 × 256、20°)の 4 コマ。*

[![知覚(球の位置)にガウス雑音を足したときのラリーの本数(送り合い、上限 8 本): 0 mm → 8 本、50 mm → 8 本、100 mm → 2 本。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/08_rally_vs_noise_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/08_rally_vs_noise.png)

*↑ 知覚(球の位置)にガウス雑音を足したときのラリーの本数(送り合い、上限 8 本): 0 mm → 8 本、50 mm → 8 本、100 mm → 2 本。*

[![追跡カメラ 1(2 × 2 平均で 512 × 400)、100 fps を 1/10 速で。橙の十字は検出、緑は Kalman の状態の投影、赤は跳ねる前の 15 コマから予測した着地点。球は 2291 rpm のトップスピンで、台で 1](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/06_rally_gif.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/06_rally_gif.gif)

*↑ 動く図 ―― 追跡カメラ 1(2 × 2 平均で 512 × 400)、100 fps を 1/10 速で。橙の十字は検出、緑は Kalman の状態の投影、赤は跳ねる前の 15 コマから予測した着地点。球は 2291 rpm のトップスピンで、台で 1 度跳ねる(e = 0.90)。*

[![自由に動く 2 本のラケット(板 15 × 16 cm、速さ ≤ 6 m/s、加速度 ≤ 60 m/s²)の送り合い(前回に近い少しずらした位置へ返す)、最初の 3 秒を 1/5 速で。相手コートに 1 度跳ねた球を面 x = ±1.55 ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/07_rally_two_rackets.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ball_bounce/07_rally_two_rackets.gif)

*↑ 動く図 ―― 自由に動く 2 本のラケット(板 15 × 16 cm、速さ ≤ 6 m/s、加速度 ≤ 60 m/s²)の送り合い(前回に近い少しずらした位置へ返す)、最初の 3 秒を 1/5 速で。相手コートに 1 度跳ねた球を面 x = ±1.55 m で迎え撃ち、狙った点へ運動方程式で返す。この設定では上限 12 本まで続く。攻める側(遠い隅を速く)が入ると 9 本で終わる(out)。*

```
py -3.11 examples/poc_ball_bounce.py
```

ソース: [examples/poc_ball_bounce.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ball_bounce.py)

この回が作った図は全部で **8 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_ball_bounce)

使用 op(ノートへ): [`add_ball`](https://furuse.work/ops/drive/ballworld/add_ball.html) · [`apex_sequence`](https://furuse.work/ops/drive/ball/apex_sequence.html) · [`ball_detect`](https://furuse.work/ops/drive/balltrack/ball_detect.html) · [`ball_mesh`](https://furuse.work/ops/drive/ballworld/ball_mesh.html) · [`ball_params`](https://furuse.work/ops/drive/ball/ball_params.html) · [`ball_set_pose`](https://furuse.work/ops/drive/ballworld/ball_set_pose.html) · [`ball_track`](https://furuse.work/ops/drive/balltrack/ball_track.html) · [`ball_truth`](https://furuse.work/ops/drive/ballworld/ball_truth.html) · [`bounce`](https://furuse.work/ops/drive/ball/bounce.html) · [`bounce_detect`](https://furuse.work/ops/drive/balltrack/bounce_detect.html) · [`bounce_total_time`](https://furuse.work/ops/drive/ball/bounce_total_time.html) · [`camera_rig`](https://furuse.work/ops/drive/ballworld/camera_rig.html) · [`contact_angular_momentum`](https://furuse.work/ops/drive/ball/contact_angular_momentum.html) · [`crosshair`](https://furuse.work/ops/annotate/pointer/crosshair.html) · [`fit_parabola`](https://furuse.work/ops/drive/ball/fit_parabola.html) · [`flight_fit`](https://furuse.work/ops/drive/ball/flight_fit.html) · [`flight_ode`](https://furuse.work/ops/drive/ball/flight_ode.html) · [`flight_simulate`](https://furuse.work/ops/drive/ball/flight_simulate.html) · [`flight_state_at`](https://furuse.work/ops/drive/ball/flight_state_at.html) · [`flight_vacuum`](https://furuse.work/ops/drive/ball/flight_vacuum.html) · [`impact_params`](https://furuse.work/ops/drive/ball/impact_params.html) · [`kalman_ca`](https://furuse.work/ops/drive/balltrack/kalman_ca.html) · [`marker_direction`](https://furuse.work/ops/drive/balltrack/marker_direction.html) · [`racket_params`](https://furuse.work/ops/drive/racket/racket_params.html) …(他 12)

## No.2026.171 —— けん玉を先駆者の目で ―― 本物の形のけん玉を 2 台のカメラで撮り、画像だけから玉の軌道を予測して大皿・小皿・中皿で受ける

[![けん玉を先駆者の目で ―― 本物の形のけん玉を 2 台のカメラで撮り、画像だけから玉の軌道を予測して大皿・小皿・中皿で受ける](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/01_rig_view_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/01_rig_view.png)

*↑ **けん玉を先駆者の目で ―― 本物の形のけん玉を 2 台のカメラで撮り、画像だけから玉の軌道を予測して大皿・小皿・中皿で受ける** ―― けん玉をロボットにやらせた研究は 30 年続いている(1996 年の人の手本からの via-point、2009 年の DMP + 強化学習の ball-in-a-cup、2020 年の「振り上げはオフライン・キャッチはオンライン」の 2 段割り)。この展示はその構えを numpy の op で組み直した。形: 日本けん玉協会の公表値(玉 60 mm、横幅 70 mm、全長 180 mm)とユーザー提供の JKA 16-2 型の説明(けんの高さ 160 mm、皿 大皿 42・中皿 38・小皿 35 mm、糸は皿胴の穴から。一次資料は未確認)で、けん(けん先 → 細い首 → 皿胴を貫く胴 → 段と輪のある握り → 中皿)と皿胴(両端がラッパのように開いて大皿・小皿)を回転体で、穴(直径 17 mm・深さ 40 mm のくぼみ)のある玉を作り、寸法を頂点から測ると全部 1e-9 で一致、けん先を穴の底まで挿した全長も 180 mm(穴の深さ 40 mm は 160 + 60 − 180 で導いた値)。力学の定理: K(0.5) = 1.685750354812596 を AGM が 1e-12、周期 4√(L/g)K(sin θ₀/2) をひも(有効長 0.42 m)が 3.0e-4・棒が 8.9e-11、張力の閉形式と最大 0.26 %、弛む角 125.04°(閉形式 125.26°)、射影法の散逸は dt に 1 次(比 9.7)、snap の落ちは ½mv_r² と 0.2 %。閉ループの根拠は画像だけ: 2 台のカメラ(480 × 360、100 fps)で世界を描き、色度で玉を検出して三角測量(誤差 中央値 0.51 mm)、玉と皿胴の糸穴の距離がひもより 5 mm 短いコマが 2 回続いたら弛んだとし(真値 0.077 s、画像 0.100 s)、その後のコマに重力つきの放物線(未知 6)を当てて玉の着地点を読む。真値 (p, v) は世界を描くためだけに使う。制御は段階を明示した: 膝で真上に引き上げる(4.9 g、けんは糸穴の側へ 10 cm 逃がす)→ 弛むまで待つ → 玉の下端がけん玉を越えるまで待つ → 皿を玉の真下へ水平に運ぶ → 着地で下げる。玉を動かすのは重力とひもの張力だけで、けんが玉に触れたら失敗(逃がさない振り上げは 0.260 s に皿胴に当たる)。同じ計画で技の姿勢だけを切り替え、20 試行の成功率は 大皿 真値 1.00・画像 1.00(横ずれ 2.40 mm)、小皿 1.00・1.00、中皿 0.95・0.95、ろうそく(真値)0.95。着地で下げると相対速さの平均は 0.91 → 0.61 m/s(大皿)。落下点の予測誤差は弛んだ後のコマ数とともに 10.51 mm(3 コマ)→ 0.98 mm(44 コマ)と減る。画素雑音 0 / 0.5 / 1 / 2 / 8 / 16 px の成功率は 1.00 / 1.00 / 1.00 / 1.00 / 0.90 / 0.40 —— 2 px まで平らなのは皿の縁の余裕(半径 21 mm)が吸う分で、横ずれは 2.40 → 4.12 → 12.05 mm と増える。推奨品(大皿 49 mm)も 1.00。玉の穴は静止した玉なら 2 台の三角測量で向きの誤差 中央値 1.8°・最大 4.7°。世界を 3D Gaussian Splatting にしてから認識もした(gsplatnp: 世界の面にガウシアンを貼り、EWA 投影・手前からの α 合成・Mip-Splatting の不透明度の補正で描く。ガウシアンは写真から学習したものでなく真の形から作り、再構成の不完全さは間隔と誤差のつまみで模す): 間隔 4 mm の 3DGS の画像だけで閉ループは 1 + 2 試行すべて捕り(三角測量の誤差 中央値 0.30 mm)、間隔を 2〜64 mm に振っても玉の検出率は 1.00(曲率の上限で玉の上には 146 個以上が残る)、崩すのは位置の誤差(20 mm で 0.25)と色の誤差(0.3 で 0.00)。玉の穴は 480 × 360 では 3DGS のぼけに塗りつぶされ(40 姿勢で 1、メッシュは 14)、解像度 × 2・間隔 2 mm で 16(誤差 中央値 2.3°)、間隔 4 mm では 0 —— 穴を読むには玉に画素が、穴の中にガウシアンが要る。穴は表面に貼った円盤でなく深さ 40 mm のくぼみとして作る(円盤だと 3DGS では手前の玉のガウシアンに覆われて消えた)。連続技も入れた(ユーザー「受けたら、受けた状態から続けて別の皿で受けて」「10 回成功すれば良し」): 受けた皿から放ち(皿を上へ加速して g より強く止めると玉が皿から離れる、頂点は v²/2g の閉形式と 2e-6 m)、飛んでいる間に持ち替えて(手首 ≤ 30 rad/s、仮定)次の皿を着地点の真下へ運び、位置と速度を目標にする手元の制御で速さを合わせて受ける(位置だけの制御は頂点 20 cm で 1 回も受けられない)。画像だけで もしかめ(大皿 ↔ 中皿)も 3 皿(大皿 → 小皿 → 中皿)も 10 回連続(協会のもしかめの級で 5 級相当)、着地の相対速さ 0.41〜0.48 m/s、飛び始めも毎回画像から。正直に: 雑音が無いと 100 回でも同じ 1 周期の繰り返しで、画素雑音 2 px では もしかめ 3 回・3 皿 6 回で崩れる。正直に: 実写でなく真値つきの合成映像、玉の回転は解かない(弛んだら最後の姿勢のまま)、捕球は「縁に触れた瞬間に横ずれ ≤ 縁の半径・相対速さ ≤ 1 m/s(仮定の閾値)・下降中」の判定で跳ねと転がりは扱わない、皿持ちの傾き 15°・皿の深さ・玉 75 g などは仮定。飛翔中の穴は下を向き、目の高さの 2 台からは 2 台同時にはほぼ見えない(54 コマ中 0)。ろうそくが中皿より難しい理由は剛体・並進だけの手元では表せない。16 門、171.0 s。*

[![近接カメラ(図のためだけ、けん玉から 0.36 m)で見た 4 技の持ち方の姿勢(けんと皿胴は 1 つの剛体、持つ所だけが違う)。けん(けん先 → 細い首 → 皿胴を貫く胴 → 段と輪のある握り → 中皿)、皿胴の両端がラッパのように開いた](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/02_kendama_closeup_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/02_kendama_closeup.png)

*↑ 測定の図 ―― 近接カメラ(図のためだけ、けん玉から 0.36 m)で見た 4 技の持ち方の姿勢(けんと皿胴は 1 つの剛体、持つ所だけが違う)。けん(けん先 → 細い首 → 皿胴を貫く胴 → 段と輪のある握り → 中皿)、皿胴の両端がラッパのように開いた大皿(赤)・小皿(紫)、中皿(青)、直径 17 mm・深さ 40 mm の穴(くぼみ)のある玉、皿胴の糸穴から出る糸。寸法は JKA 16-2 型(けん 160 mm、横幅 70 mm、皿 42 / 38 / 35 mm)。玉の位置と向きは見せるために置いたもの。*

[![真下から 150° 相当の速さ(3.92 m/s)で打ち出した玉のひも(有効長 0.42 m)の張力。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/03_tension_closed_form_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/03_tension_closed_form.png)

*↑ 真下から 150° 相当の速さ(3.92 m/s)で打ち出した玉のひも(有効長 0.42 m)の張力。*

[![y–z 面(手元を逃がす向き)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/04_catch_yz_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/04_catch_yz.png)

*↑ y–z 面(手元を逃がす向き)。*

[![画像だけの閉ループの成功率(大皿、各 20 試行): 0 px → 1.00、0.5 px → 1.00、1 px → 1.00、2 px → 1.00、8 px → 0.90、16 px → 0.4](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/07_success_vs_pixel_noise_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/07_success_vs_pixel_noise.png)

*↑ 画像だけの閉ループの成功率(大皿、各 20 試行): 0 px → 1.00、0.5 px → 1.00、1 px → 1.00、2 px → 1.00、8 px → 0.90、16 px → 0.40。*

[![3DGS の世界の捕球の試行(弛み → 捕球の 12 コマ)を、つまみを振った 3DGS で描き直して色度の検出(balltrack.ball_detect)にかけた。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/09_gs_noise_knobs_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/09_gs_noise_knobs.png)

*↑ 3DGS の世界の捕球の試行(弛み → 捕球の 12 コマ)を、つまみを振った 3DGS で描き直して色度の検出(balltrack.ball_detect)にかけた。*

[![カメラ 2、100 fps を 1/10 速で(最後のコマで 1 秒止める)。振り上げ → t = 0.077 s にひもが弛む(画像での検出 0.100 s)→ 玉がけんを越えるまで待つ → 皿を水平に運ぶ → 着地で下げる → t = ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/05_catch_gif.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/05_catch_gif.gif)

*↑ 動く図 ―― カメラ 2、100 fps を 1/10 速で(最後のコマで 1 秒止める)。振り上げ → t = 0.077 s にひもが弛む(画像での検出 0.100 s)→ 玉がけんを越えるまで待つ → 皿を水平に運ぶ → 着地で下げる → t = 0.540 s に大皿で受ける。十字は画像の予測(弛んだ後のコマに当てた重力つきの放物線)から読んだ着地点、枠の中は同じカメラでけん玉のまわりを 3 倍の解像度に描き直した窓。t ≈ 0.3 s に玉がけんに重なって見えるのはカメラから見た重なりで、けんは糸穴の側へ 10 cm 逃げて玉の奥にある(その間の隙間の最小 41 mm)。正直に: 捕球は「縁に触れた瞬間に横ずれ ≤ 21 mm・相対速さ ≤ 1 m/s・下降中」の判定で、縁での跳ねと転がりは描いていない。*

[![右 = 閉ループの知覚が実際に見た画像(世界を 3DGS にして描いたもの、カメラ 2、100 fps を 1/10 速)、左 = 同じ瞬間のメッシュ(真の形)。右上の窓 = 同じカメラでけん玉のまわりを 3 倍の解像度に描き直したもの(左](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/10_gs_catch_gif.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_kendama/10_gs_catch_gif.gif)

*↑ 動く図 ―― 右 = 閉ループの知覚が実際に見た画像(世界を 3DGS にして描いたもの、カメラ 2、100 fps を 1/10 速)、左 = 同じ瞬間のメッシュ(真の形)。右上の窓 = 同じカメラでけん玉のまわりを 3 倍の解像度に描き直したもの(左はメッシュ、右は同じ 3DGS)。青の輪 = 色度で検出した玉、十字 = 弛んだ後のコマに当てた重力つきの放物線から読んだ着地点。t = 0.541 s に大皿で受ける(横ずれ 4.34 mm、推定 391 回は全部 3DGS の画像から)。*

```
py -3.11 examples/poc_kendama.py
```

ソース: [examples/poc_kendama.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_kendama.py)

この回が作った図は全部で **11 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_kendama)

使用 op(ノートへ): [`ball_detect`](https://furuse.work/ops/drive/balltrack/ball_detect.html) · [`camera_perceiver`](https://furuse.work/ops/drive/kendamaworld/camera_perceiver.html) · [`catch_plan_staged`](https://furuse.work/ops/drive/kendama/catch_plan_staged.html) · [`catch_success_rate`](https://furuse.work/ops/drive/kendama/catch_success_rate.html) · [`crosshair`](https://furuse.work/ops/annotate/pointer/crosshair.html) · [`elliptic_k_agm`](https://furuse.work/ops/drive/kendama/elliptic_k_agm.html) · [`gs_from_world`](https://furuse.work/ops/drive/gsplat/gs_from_world.html) · [`gs_render`](https://furuse.work/ops/drive/gsplat/gs_render.html) · [`gs_render_fn`](https://furuse.work/ops/drive/gsplat/gs_render_fn.html) · [`gs_update`](https://furuse.work/ops/drive/gsplat/gs_update.html) · [`hole_detect`](https://furuse.work/ops/drive/kendama/hole_detect.html) · [`ken_mesh`](https://furuse.work/ops/drive/kendamaworld/ken_mesh.html) · [`kendama_clearance`](https://furuse.work/ops/drive/kendamaworld/kendama_clearance.html) · [`kendama_combo_simulate`](https://furuse.work/ops/drive/kendama/kendama_combo_simulate.html) · [`kendama_params`](https://furuse.work/ops/drive/kendama/kendama_params.html) · [`kendama_pose`](https://furuse.work/ops/drive/kendamaworld/kendama_pose.html) · [`kendama_rig`](https://furuse.work/ops/drive/kendamaworld/kendama_rig.html) · [`kendama_simulate`](https://furuse.work/ops/drive/kendama/kendama_simulate.html) · [`kendama_world`](https://furuse.work/ops/drive/kendamaworld/kendama_world.html) · [`leader_line`](https://furuse.work/ops/annotate/pointer/leader_line.html) · [`overlay_mask`](https://furuse.work/ops/annotate/overlay/overlay_mask.html) · [`pendulum_launch_speed`](https://furuse.work/ops/drive/kendama/pendulum_launch_speed.html) · [`pendulum_period_exact`](https://furuse.work/ops/drive/kendama/pendulum_period_exact.html) · [`pendulum_rod_simulate`](https://furuse.work/ops/drive/kendama/pendulum_rod_simulate.html) …(他 10)

## No.2026.174 —— 回転で曲がる卓球の球を撮って、回転を 2 通りで読む ―― 曲がり方から / 球の模様から

[![回転で曲がる卓球の球を撮って、回転を 2 通りで読む ―― 曲がり方から / 球の模様から](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/03_top_view_sidespin.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/03_top_view_sidespin.gif)

*↑ **回転で曲がる卓球の球を撮って、回転を 2 通りで読む ―― 曲がり方から / 球の模様から** ―― 同じ速さ・同じ向きで打ち出した卓球の球でも、トップスピン(前回転)は沈んで手前に、バックスピン(下回転)は浮いて奥に落ち、横回転は横に逸れる(マグヌス効果、力は ω × v の向き)。この展示は回転だけ違う 4 本(150 rad/s ≈ 1,430 rpm)を 2 台のカメラ(240 fps)で撮り、回転を **2 通りで読む**。曲がり方から: 三角測量した跳ねる前の軌跡に、抗力 + マグヌスの運動方程式を位置・速度・回転の 9 パラメータで当てる(新しい op fit_spin、減衰つきの当てはめ)。垂直成分の誤差はトップ 3.9 %・バック 0.9 %・横 1.7 %、読んだ回転で先読みした着地点は 4 本とも真値と 2 cm 以内(x = [0.488, 0.754, 1.124] m、順はトップ < 無回転 < バック)。模様から: 同じ打球を近接カメラ(1000 fps、20 コマ)で撮り、黒い模様(14 個)の動きを Kabsch で当てる —— 4.8 %・3.2 %・0.9 %。2 つの測り方は独立(片方は軌跡だけ、片方は模様だけを見る)で、互いに 10 % 以内に一致する(第 2 実装の門)。定理の門: マグヌスの力は ω × v なので、進行方向に平行な回転は力を生まない —— 瞬間の加速度の差は 1e-12 未満、0.25 s 飛んでも 7.1 mm(垂直な回転なら 5.4 cm)。だから fit_spin はこの成分を分けて返し、無回転の球で当てはめが出した 22 rad/s の回転はほとんどこの読めない向きにある。軌跡が短いと曲がりが検出の誤差に埋もれて読めない(400.3 % → 4.0 %)。見つけたこと: 打つ側のカメラから見ると、ネットの向こうで低く飛ぶ球の上半分がネットの白帯に隠れ、検出の中心がずれる(三角測量で最大 26 mm)—— 半径が前後の 0.8 倍未満の検出を捨てる。模様の向きを出す op(marker_direction)は球を光軸上とみなしていたので、画面を横切る球では視線の変化がそのまま見かけの回転になった(1 ms で 0.01 rad、1 コマの回転の 7 %)—— カメラの K を渡すと透視で厳密に解くようにした。正直に: 合成映像(色が既知、実写の照明・ぼけ無し)、空力係数(C_d = 0.4、スピン比の C_L)は真値と当てはめで同じ式、回転は飛行中一定。8 門、34.4 s。*

[![同じ速さ・同じ向き(v₀ = (6.0, 0, 1.3) m/s)で打ち出した 3 本を横から: トップスピン(橙)は沈んで x = 0.49 m、無回転(黄)は 0.75 m、バックスピン(青)は浮いて 1.12 m に落ちる(台の中心か](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/01_side_three_serves.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/01_side_three_serves.gif)

*↑ 測定の図 ―― 同じ速さ・同じ向き(v₀ = (6.0, 0, 1.3) m/s)で打ち出した 3 本を横から: トップスピン(橙)は沈んで x = 0.49 m、無回転(黄)は 0.75 m、バックスピン(青)は浮いて 1.12 m に落ちる(台の中心から)。球は見やすさのため 1.6 倍で描いた。MP4 = 240 fps の全コマ(1/8 スロー)。*

[![曲がり方(軌跡に運動方程式を当てる)と模様(近接カメラの Kabsch)は独立。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/04_two_readings_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/04_two_readings.png)

*↑ 曲がり方(軌跡に運動方程式を当てる)と模様(近接カメラの Kabsch)は独立。*

[![跳ねる前の先頭 n コマだけで回転を読む。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/05_error_vs_length_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/05_error_vs_length.png)

*↑ 跳ねる前の先頭 n コマだけで回転を読む。*

[![近接カメラ(1000 fps、20 コマ = 20 ms)のトップスピン。黒い模様(14 個、見えるのは 4〜6 個)を前のコマと向きで対応づけ、Kabsch で回転を当てる: ω = [-0.7, 150.1, -7.2) rad/s(真](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/02_spin_closeup.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_spin/02_spin_closeup.gif)

*↑ 動く図 ―― 近接カメラ(1000 fps、20 コマ = 20 ms)のトップスピン。黒い模様(14 個、見えるのは 4〜6 個)を前のコマと向きで対応づけ、Kabsch で回転を当てる: ω = [-0.7, 150.1, -7.2] rad/s(真値 (0, 150, 0))。1/100 スロー、3 回繰り返し。*

```
py -3.11 examples/poc_table_tennis_spin.py
```

ソース: [examples/poc_table_tennis_spin.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_table_tennis_spin.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_table_tennis_spin)

使用 op(ノートへ): [`add_ball`](https://furuse.work/ops/drive/ballworld/add_ball.html) · [`ball_detect`](https://furuse.work/ops/drive/balltrack/ball_detect.html) · [`ball_mesh`](https://furuse.work/ops/drive/ballworld/ball_mesh.html) · [`ball_params`](https://furuse.work/ops/drive/ball/ball_params.html) · [`ball_set_pose`](https://furuse.work/ops/drive/ballworld/ball_set_pose.html) · [`ball_track`](https://furuse.work/ops/drive/balltrack/ball_track.html) · [`bounce_detect`](https://furuse.work/ops/drive/balltrack/bounce_detect.html) · [`camera_rig`](https://furuse.work/ops/drive/ballworld/camera_rig.html) · [`fit_spin`](https://furuse.work/ops/drive/ball/fit_spin.html) · [`flight_ode`](https://furuse.work/ops/drive/ball/flight_ode.html) · [`flight_simulate`](https://furuse.work/ops/drive/ball/flight_simulate.html) · [`impact_params`](https://furuse.work/ops/drive/ball/impact_params.html) · [`marker_direction`](https://furuse.work/ops/drive/balltrack/marker_direction.html) · [`reproject`](https://furuse.work/ops/drive/balltrack/reproject.html) · [`rotation_from_omega`](https://furuse.work/ops/drive/ballworld/rotation_from_omega.html) · [`spin_from_marker_sequence`](https://furuse.work/ops/drive/balltrack/spin_from_marker_sequence.html) · [`table_params`](https://furuse.work/ops/drive/ballworld/table_params.html) · [`table_world`](https://furuse.work/ops/drive/ballworld/table_world.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`track_triangulate`](https://furuse.work/ops/drive/balltrack/track_triangulate.html) · [`world_camera`](https://furuse.work/ops/drive/world/world_camera.html)

## No.2026.175 —— 跳ねる卓球の球を高速カメラで撮って、反発係数と摩擦係数を読む ―― 公表値と照合する

[![跳ねる卓球の球を高速カメラで撮って、反発係数と摩擦係数を読む ―― 公表値と照合する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_bounce/05_regime_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_bounce/05_regime_map.png)

*↑ **跳ねる卓球の球を高速カメラで撮って、反発係数と摩擦係数を読む ―― 公表値と照合する** ―― 卓球の球が台で跳ねると、縦の速さは反発係数 e の分だけ残り、横の速さと回転は摩擦で入れ替わる。接地点の滑りが小さければ跳ねの途中で止まって**転がりに移り**、大きければ**滑ったまま**離れる。この展示は台の上の跳ね 22 本を横から 1 台の高速カメラ(1000 fps、ROI 読み出し)で撮り、**画像だけから** e・摩擦係数 μ・跳ねの種類を読んで公表値と照合する。運動面が分かっているので 1 台で位置が出る(中心の画素の視線と面の交点)。跳ねの前後に抗力 + マグヌスの運動方程式を当てて接触の瞬間の速度を出し、回転は球の模様から 2 段で読む(新しい op spin_from_marker_sequence)。門: Cross 2002 の閉形式(薄い殻の球: 転がりに移る跳ねは v_x' = 0.6 v_x + 0.4 rω、滑ったままは Δv_t = μ(1+e)|v_z|、境目は (2/5)|s| = μ(1+e)|v_z|)が力積で書いた実装と乱数 300 通りで一致 / ITTF の台の跳ね(Laws 2.1.3: 30 cm → 約 23 cm)を動画から 23.0 cm / e の速さへの依存の傾き -0.00572 /(km/h)がInaba ら 2017 の実測 −0.0058 と 1.4 % / 滑ったままの跳ねから μ = 0.2500(真値 0.25)/ 跳ねの種類が閉形式の境目と 15 / 15 / 転がりに移った跳ねはrω' と v_x' が 3 % 以内 / 摩擦の無い台では横の速さも回転も変わらない。見つけたこと: 30 → 23 cm を e = √(23/30) = 0.876 と読むと空気抵抗の分を落とす —— その台は 21.7 cm しか跳ねず、抗力込みで約 23 cm になる e は 0.9019。Inaba らの式そのもの(切片 1.0002)は 30 cm から 25.5 cm 跳ねる台になり、ITTF と公表値同士で食い違う(研究室の台と規格の差か、測り方の差かは未確認)。転がりに移った跳ねの「見かけの μ」は μ の下界にすぎない。正直に: 合成映像、台の e(v) は ITTF の切片と Inaba らの傾きを継いだ合成、μ は定数(Inaba らの実測は接地点の速さで増える)、球の変形(5.5 m/s からの座屈)は入れていない。7 門、21.6 s。*

[![ITTF の台の跳ねの試験(Laws 2.1.3: 30 cm から落として約 23 cm)。球の下端を 30 cm から落とし、動画から読んだ跳ねの高さは 23.0 cm(世界の真値 23.0 cm)。物差しは 1 cm 刻み。MP4 =](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_bounce/01_drop_test.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_bounce/01_drop_test.gif)

*↑ 測定の図 ―― ITTF の台の跳ねの試験(Laws 2.1.3: 30 cm から落として約 23 cm)。球の下端を 30 cm から落とし、動画から読んだ跳ねの高さは 23.0 cm(世界の真値 23.0 cm)。物差しは 1 cm 刻み。MP4 = 240 fps の全コマ(1/8 スロー)。*

[![動画から読んだ e(22 本)と公表値。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_bounce/04_restitution_vs_speed_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_bounce/04_restitution_vs_speed.png)

*↑ 動画から読んだ e(22 本)と公表値。*

[![バックスピン(ω = −150 rad/s)の跳ね(当たる瞬間 v = (4.9, −4.3) m/s)、1000 fps を 1/40 スローで。接地点が大きく滑ったまま離れる(滑り +7.89 → +2.89 m/s)。模様から読んだ回](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_bounce/02_backspin_bounce.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_bounce/02_backspin_bounce.gif)

*↑ 動く図 ―― バックスピン(ω = −150 rad/s)の跳ね(当たる瞬間 v = (4.9, −4.3) m/s)、1000 fps を 1/40 スローで。接地点が大きく滑ったまま離れる(滑り +7.89 → +2.89 m/s)。模様から読んだ回転 -150 → +0 rad/s、横の速さの減り 1.997 m/s → 見かけの μ 0.250。*

[![トップスピン(ω = +200 rad/s)の跳ね(当たる瞬間 v = (2.9, −3.1) m/s)。接地点の滑りが小さいので跳ねの途中で止まり、転がりに移って離れる(滑り -1.17 → -0.01 m/s、跳ねた後の rω' = 3](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_bounce/03_topspin_bounce.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_bounce/03_topspin_bounce.gif)

*↑ 動く図 ―― トップスピン(ω = +200 rad/s)の跳ね(当たる瞬間 v = (2.9, −3.1) m/s)。接地点の滑りが小さいので跳ねの途中で止まり、転がりに移って離れる(滑り -1.17 → -0.01 m/s、跳ねた後の rω' = 3.320 m/s と v_x' = 3.312 m/s)。*

```
py -3.11 examples/poc_table_tennis_bounce.py
```

ソース: [examples/poc_table_tennis_bounce.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_table_tennis_bounce.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_table_tennis_bounce)

使用 op(ノートへ): [`add_ball`](https://furuse.work/ops/drive/ballworld/add_ball.html) · [`ball_detect`](https://furuse.work/ops/drive/balltrack/ball_detect.html) · [`ball_mesh`](https://furuse.work/ops/drive/ballworld/ball_mesh.html) · [`ball_params`](https://furuse.work/ops/drive/ball/ball_params.html) · [`ball_set_pose`](https://furuse.work/ops/drive/ballworld/ball_set_pose.html) · [`bounce`](https://furuse.work/ops/drive/ball/bounce.html) · [`bounce_detect`](https://furuse.work/ops/drive/balltrack/bounce_detect.html) · [`crosshair`](https://furuse.work/ops/annotate/pointer/crosshair.html) · [`flight_fit`](https://furuse.work/ops/drive/ball/flight_fit.html) · [`flight_ode`](https://furuse.work/ops/drive/ball/flight_ode.html) · [`flight_simulate`](https://furuse.work/ops/drive/ball/flight_simulate.html) · [`flight_state_at`](https://furuse.work/ops/drive/ball/flight_state_at.html) · [`impact_params`](https://furuse.work/ops/drive/ball/impact_params.html) · [`marker_direction`](https://furuse.work/ops/drive/balltrack/marker_direction.html) · [`ray_plane_range`](https://furuse.work/ops/drive/lidar/ray_plane_range.html) · [`reproject`](https://furuse.work/ops/drive/balltrack/reproject.html) · [`rotation_from_omega`](https://furuse.work/ops/drive/ballworld/rotation_from_omega.html) · [`spin_from_marker_sequence`](https://furuse.work/ops/drive/balltrack/spin_from_marker_sequence.html) · [`table_params`](https://furuse.work/ops/drive/ballworld/table_params.html) · [`table_world`](https://furuse.work/ops/drive/ballworld/table_world.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`world_camera`](https://furuse.work/ops/drive/world/world_camera.html)

## No.2026.177 —— 読みの誤差が卓球のラリーを終わらせる ―― 雑音と遅れが着地点をどれだけ動かすかを、打つ前に閉形式で出す

[![読みの誤差が卓球のラリーを終わらせる ―― 雑音と遅れが着地点をどれだけ動かすかを、打つ前に閉形式で出す](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_rally_loop/01_landing_cloud.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_rally_loop/01_landing_cloud.gif)

*↑ **読みの誤差が卓球のラリーを終わらせる ―― 雑音と遅れが着地点をどれだけ動かすかを、打つ前に閉形式で出す** ―― 卓球ロボットは球の位置を読んでから、相手コートの狙った点に落ちる打球を計算して打つ。読みが δ ずれていれば、計算は**ずれた位置から**、球は**本当の位置から**飛び出すので着地点がずれ、台の縁までの余白を越えるとアウトでラリーが終わる。この展示は「読みの誤差 → 着地点の誤差」の伝わり方(ヤコビアン J、2 × 3)を打つ前に出し、雑音・遅れ・ラリーの途切れがそれで説明できるかを確かめる。門: 空気の無い世界で、狙い・ラケットの計画・衝突・飛翔を通した数値の J が閉形式 ΔL_xy = −δ_xy − (v_xy/|v_z(T)|)δ_z と差 2.5e-06(高さの読み違い 1 cm は前後に 2.1 cm)/ 抗力 + マグヌスありで σ = 2 cm の読みの 300 本のばらつき (前後 4.6, 左右 2.0) cm が J Σ Jᵀ と 1.0・0.8 % / 縁から 6 cm を σ = 3 cm で狙うアウトの確率が予測 0.043・打った 300 本で 0.060(二項の 1.5 σ)/ 遅れ τ = 5・10・20 ms の着地点のずれが J · (−vτ − ½gτ² ẑ) と 0.2〜0.6 % / 雑音 0 の送り合いは 4 回とも上限の 10 本、σ = 6 cm(余白から出した上限 σ* = 5.2 cm の 1.2 倍)では 9・8・2・7 本ですべてアウト / 誤差 0 なら狙いから 0.52 mm。見つけたこと: 「τ 前の読み」の高さを + ½gτ² と書いていた(正しくは −)。門は同じ読みのずれを両辺に入れて比べるので、誤りのまま通っていた —— 数値積分と突き合わせて直した。雑音が大きい側(縁 12 cm を σ = 5 cm)は予測 0.017、実際 0.003 —— 前の乱数では逆向きに 2.7 σ 外れていて、300 本では一次の近似の誤りの向きは決まらない。正直に: 誤差は球の位置の読みだけ(速度・回転は真値)で毎コマ独立のガウス、ラケットは計画どおりに打てる、アウトは縁の余白だけで判定。6 門、289 s。*

[![高さを 5 cm 高く読むと、狙いの計算(灰)は低い弾道を選び、本当の位置から打った球(赤)は狙いより 10.2 cm 手前に落ちる。J の前後の増幅 2.06 × 5 cm = 10.3 cm(一次の予測)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_rally_loop/02_height_misread.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_rally_loop/02_height_misread.gif)

*↑ 測定の図 ―― 高さを 5 cm 高く読むと、狙いの計算(灰)は低い弾道を選び、本当の位置から打った球(赤)は狙いより 10.2 cm 手前に落ちる。J の前後の増幅 2.06 × 5 cm = 10.3 cm(一次の予測)。*

[![読みの雑音は 3 方向に同じ大きさでも、着地点のずれは前後に 2.2 倍伸びる(高さの読み違いが落ちる角の分だけ増える)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_rally_loop/04_spread_vs_prediction_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_rally_loop/04_spread_vs_prediction.png)

*↑ 読みの雑音は 3 方向に同じ大きさでも、着地点のずれは前後に 2.2 倍伸びる(高さの読み違いが落ちる角の分だけ増える)。*

[![上から見た送り合い(1/2 速)。上 = 読みの雑音 0 で上限の 10 本、下 = 毎コマの読みに σ = 6 cm で 9 本(アウト)。ラケットは届いている —— 途切れる理由は空振りでなく、読み違いから狙った打球のアウト。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_rally_loop/03_rally_compare.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_table_tennis_rally_loop/03_rally_compare.gif)

*↑ 動く図 ―― 上から見た送り合い(1/2 速)。上 = 読みの雑音 0 で上限の 10 本、下 = 毎コマの読みに σ = 6 cm で 9 本(アウト)。ラケットは届いている —— 途切れる理由は空振りでなく、読み違いから狙った打球のアウト。*

```
py -3.11 examples/poc_table_tennis_rally_loop.py
```

ソース: [examples/poc_table_tennis_rally_loop.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_table_tennis_rally_loop.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_table_tennis_rally_loop)

使用 op(ノートへ): [`aim_velocity`](https://furuse.work/ops/drive/racket/aim_velocity.html) · [`ball_params`](https://furuse.work/ops/drive/ball/ball_params.html) · [`flight_simulate`](https://furuse.work/ops/drive/ball/flight_simulate.html) · [`impact_params`](https://furuse.work/ops/drive/ball/impact_params.html) · [`racket_impact`](https://furuse.work/ops/drive/racket/racket_impact.html) · [`racket_params`](https://furuse.work/ops/drive/racket/racket_params.html) · [`racket_plan`](https://furuse.work/ops/drive/racket/racket_plan.html) · [`rally_simulate`](https://furuse.work/ops/drive/racket/rally_simulate.html) · [`table_params`](https://furuse.work/ops/drive/ballworld/table_params.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html)

## No.2026.145 —— 継ぎ目の無い動画で、時間方向 op の周期境界を検査する

[![継ぎ目の無い動画で、時間方向 op の周期境界を検査する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/05_contamination_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/05_contamination_map.png)

*↑ **継ぎ目の無い動画で、時間方向 op の周期境界を検査する** ―― 周期的な素材には、時間方向 op が満たすべき**厳密な不変量**がある —— 周期 T の動画 v に対し、周期境界を正しく扱う op なら **op(roll(v,k)) == roll(op(v),k)**(巡回シフト等変性)が厳密に成り立つ。端を複製・固定・切り捨てで埋める実装はここで割れる。`perpetual_loop` は時間依存の量をすべて θ の関数にして作るので**継ぎ目は消したのでなく最初から存在せず**(継ぎ目の比 1.0509 —— 0 ではなく 1 が正解)、この等式の真値は厳密に 0 差になる。**新しい op は 1 つも足していない。**★★この回の芯は「**『厳密に一致』が空の出力から出た**」こと: `three_frame_difference` を既定のまま走らせると最大差 **0.0e+00**・汚れ **0 フレーム**という満点を返すが、**中身のあるフレームは 0/32** —— 既定のしきい値 0.1 に対し素材の隣接フレーム差が最大 **0.0841** しかなく、何も検出していない。空の出力はどうシフトしても空なので一致して当然で、**等変性だけを見る門はここに構造的に盲目**。しきい値を 0.03 にすると同じ op が中身 30/32・汚れ 4 フレーム・最大差 1.000 となり、**満点が嘘だったと分かる**。★台帳から拾った **video -> video の単入力 op 16 本を全数走査**すると 3 群に割れた: (1) **窓つき**(端だけ汚れる)= frame_difference_causal 2 / optical_flow_magnitude_stream 2 / moving_average_window 4 / background_subtraction_window 8 / temporal_bilateral 8 / temporal_median_window 8 —— **その枚数を捨てれば残りは厳密に一致**。(2) **全フレーム**(32/32)= deflicker / exponential_background / exponential_foreground / running_gaussian_background / running_gaussian_foreground —— 再帰や全域統計なので端を捨てても直らない。(3) **空に近い** = three_frame_difference / motion_history_image / motion_energy_image —— 汚れ 0 に見えるが合格ではない。★★★**汚れるフレームは個数でなく集合として閉形式で予言できる**: 窓幅 w のop が汚すのは集合 **roll(B,k) ∪ B**(B = 不完全なフレーム)で、w = 3/5/7/9/11/13 の**6 通りとも集合そのものが一致**(4/8/12/16/19/21)。素朴な「w-1 フレーム」は6 通り全部外れ、2(w-1) も w=11 で外れる —— T=32・シフト 9 で 2 つの帯が**重なる**からで、重なり 1 フレームまで閉形式が説明する。★はじめ「中心窓なので前後 (w-1)/2」と予言して外した。外れた集合を引き算すると**汚れているのは先頭側だけで末尾は無傷**だった —— つまり窓は中心でなく**後方(因果的)**で、不完全なのは先頭の w-1 フレーム。**窓の向きは、実装を読まなくても汚れた集合の形から読める。**検査 17 件・図 9 枚(動く図 1 枚を含む)。*

[![`perpetual_loop("plasma_orbit")` の 4 コマ。時間に依る量をすべて θ の関数にしてあるので、**t = T は t = 0 と同じ式**です ---- 継ぎ目は消したのではなく最初から作られていません(継](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/01_loop_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/01_loop_frames.png)

*↑ 測定の図 ―― `perpetual_loop("plasma_orbit")` の 4 コマ。時間に依る量をすべて θ の関数にしてあるので、**t = T は t = 0 と同じ式**です ---- 継ぎ目は消したのではなく最初から作られていません(継ぎ目の比 1.0509、**0 ではなく 1 が正解**)。★だから「巡回シフトしても同じ動画」という**厳密な真値**が素材の側に立ちます。*

[![`three_frame_difference` の同じコマです。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/03_empty_output_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/03_empty_output.png)

*↑ `three_frame_difference` の同じコマです。*

[![継ぎ目の無い動画 32 コマを巡回シフトして測った全数走査です。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/04_scan_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/04_scan.png)

*↑ 継ぎ目の無い動画 32 コマを巡回シフトして測った全数走査です。*

[![窓幅 7 のときに汚れたフレームの位置。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/07_bad_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/07_bad_frames.png)

*↑ 窓幅 7 のときに汚れたフレームの位置。*

[![端だけが汚れる 6 本について、汚れたフレーム数を少ない順に並べたもの。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/08_trim_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/08_trim.png)

*↑ 端だけが汚れる 6 本について、汚れたフレーム数を少ない順に並べたもの。*

[![同じ動画を実際に回したもの(32 コマ)。**最後のコマから最初のコマへ戻るところに継ぎ目が見えません** ---- 消したのではなく、時間に依る量をすべて θ の関数にしてあるので**最初から存在しない**からです。★この性質があるので「](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/02_loop.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_periodic_video_boundary/02_loop.gif)

*↑ 動く図 ―― 同じ動画を実際に回したもの(32 コマ)。**最後のコマから最初のコマへ戻るところに継ぎ目が見えません** ---- 消したのではなく、時間に依る量をすべて θ の関数にしてあるので**最初から存在しない**からです。★この性質があるので「巡回シフトしても同じ動画」が**厳密な真値**になり、時間方向 op の周期境界を数で採点できます。*

```
py -3.11 examples/poc_periodic_video_boundary.py
```

ソース: [examples/poc_periodic_video_boundary.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_periodic_video_boundary.py)

この回が作った図は全部で **9 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_periodic_video_boundary)

使用 op(ノートへ): [`moving_average_window`](https://furuse.work/ops/videostream/window/moving_average_window.html) · [`perpetual_loop`](https://furuse.work/ops/generative/loop/perpetual_loop.html) · [`perpetual_loop_seam`](https://furuse.work/ops/generative/loop/perpetual_loop_seam.html) · [`three_frame_difference`](https://furuse.work/ops/videostream/motion/three_frame_difference.html)

### 幾何・校正ウィング ―― 残差が小さいことは正しさの証明にならない

カメラ校正の再投影誤差、パノラマの継ぎ目、点群位置合わせの残差。どれも「小さいほど良い」と読まれる数字ですが、この部屋の 7 点はその読み方が成り立たない場面を、真値を握った上で並べています。

再投影誤差 0.0688〜0.0690 px で焦点距離の誤差が 0.026〜7.334 %。隣の継ぎ目が 0.12 px なのに閉じる 1 本だけ 1.5 px。球や円柱では残差が同じまま姿勢が任意。最小二乗は残差を雑音まで落とすのが仕事で、落ちた先が真値かどうかは別の話です。

測り方そのものの罠も残してあります。点群を 1 組固定して姿勢だけ振っても標本は 1 つしか無く、乱数の種だけで「象限誤り 0 %」と「100 %」の両方が出ました。真値なしで測れる絶対量は、一周する撮り方の閉ループ誤差くらいしかありません。

## No.2026.006 —— 再投影誤差 0.05 px は何も保証しない

[![再投影誤差 0.05 px は何も保証しない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/03_frame_fill_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/03_frame_fill.png)

*↑ **再投影誤差 0.05 px は何も保証しない** ―― 既知の内部パラメータと姿勢で格子点を投影し、校正し直して成分ごとに誤差を出した図。板の傾き 32 / 8 / 2 度で再投影 RMS は 0.0688〜0.0690 px(比 1.00)なのに、fx の誤差は 0.026〜7.334 %(281 倍)。歪みのあるカメラでは退化検出の門が発火せず、非線形最適化は正面配置でも答えを返す。*

[![RMS は 1.00 倍しか動かないのに fx 誤差は 281 倍動く。配置の良し悪しを映すのは sigma_fx のほう。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/01_reproj_vs_truth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/01_reproj_vs_truth.png)

*↑ 測定の図 ―― RMS は 1.00 倍しか動かないのに fx 誤差は 281 倍動く。配置の良し悪しを映すのは sigma_fx のほう。*

[![2 本は重なる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/02_fx_z_coupling_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/02_fx_z_coupling.png)

*↑ 2 本は重なる。*

[![どちらも雑音 0 では真値。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/04_noise_amplification_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/04_noise_amplification.png)

*↑ どちらも雑音 0 では真値。*

[![第 1 部: 同じ雑音 0.05 px の観測を、傾き 32 度(左)と 2 度(右)の配置で解く反復。再投影 RMS はどちらも 0.069 / 0.069 px まで下がるが、fx は左が 1199.7(誤差 0.026 %)、右が 1](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/05_calibration_convergence.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/05_calibration_convergence.gif)

*↑ 動く図 ―― 第 1 部: 同じ雑音 0.05 px の観測を、傾き 32 度(左)と 2 度(右)の配置で解く反復。再投影 RMS はどちらも 0.069 / 0.069 px まで下がるが、fx は左が 1199.7(誤差 0.026 %)、右が 1112.0(誤差 7.33 %)で止まる。第 2 部: fx を真値の 0.92〜1.08 倍に固定して残りを解き直すと、左は RMS が 0.54 / 0.45 px(両端)まで跳ね上がるのに、右は 0.069 / 0.069 px とほとんど動かない —— 板までの距離 Z が fx と同じ比で動いて(Z 比 0.920 / 1.080)、画素の位置を保つため。右の配置では再投影誤差が焦点距離について何も言っていない。*

```
py -3.11 examples/poc_camera_calibration.py
```

ソース: [examples/poc_camera_calibration.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_camera_calibration.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_camera_calibration)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`data_to_pixel`](https://furuse.work/ops/annotate/plot/data_to_pixel.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`project_points`](https://furuse.work/ops/3d/render/project_points.html) · [`reprojection_error`](https://furuse.work/ops/3d/pose_estimation/reprojection_error.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html)

## No.2026.028 —— 隣どうしを鎖でつなぐと、一周して元に戻れない

[![隣どうしを鎖でつなぐと、一周して元に戻れない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/01_seams_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/01_seams.png)

*↑ **隣どうしを鎖でつなぐと、一周して元に戻れない** ―― 既知の回転列で円筒パノラマから 36 枚を切り出し、隣接ペアの鎖で一周させた図。隣の継ぎ目は 0.12 px なのに閉じる 1 本だけ 1.5 px(13 倍)開く。埋もれていた `bundle_adjust_mosaic` は鎖を上回らず(30/36 枚が単位行列のまま)、姿勢の最悪誤差は鎖 1.65 → 大域最適化 0.56 px。*

[![系 2(等分)は閉ループ誤差を下げるのに姿勢はかえって悪化する。新しい観測を足さずに効くのは系 3。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/02_pose_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/02_pose_error.png)

*↑ 測定の図 ―― 系 2(等分)は閉ループ誤差を下げるのに姿勢はかえって悪化する。新しい観測を足さずに効くのは系 3。*

[![上 2 枚はどちらも継ぎ目が綺麗に見える(後勝ちの上書きで混合しないため)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/03_mosaic_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/03_mosaic.png)

*↑ 上 2 枚はどちらも継ぎ目が綺麗に見える(後勝ちの上書きで混合しないため)。*

[![実測 log-log 傾き 0.89。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/04_drift_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/04_drift.png)

*↑ 実測 log-log 傾き 0.89。*

[![鎖(隣どうしの相対回転を掛けるだけ)で 36 枚を円筒に 1 枚ずつ貼る過程。白い枠が真の位置、橙の枠が鎖の推定位置(ずれを 20 倍に誇張)。隣どうしの継ぎ目は平均 0.119 px で合っているのに、真の姿勢からのずれ(右下の曲線)は積](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/05_chain_drift_video.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/05_chain_drift_video.gif)

*↑ 動く図 ―― 鎖(隣どうしの相対回転を掛けるだけ)で 36 枚を円筒に 1 枚ずつ貼る過程。白い枠が真の位置、橙の枠が鎖の推定位置(ずれを 20 倍に誇張)。隣どうしの継ぎ目は平均 0.119 px で合っているのに、真の姿勢からのずれ(右下の曲線)は積み上がって最悪 1.65 px(フレーム 16)。一周して 0 枚目(赤紫)と35 枚目(緑)を重ねると閉じる継ぎ目が 1.50 px 開き、縁に色の縞(二重像)が出る(左下、4 倍拡大)。最後に同じ 36 本の辺を閉ループ拘束で解き直すと(水色)、姿勢のずれは最悪 1.18 px、閉じる継ぎ目は 0.11 px。*

```
py -3.11 examples/poc_panorama_drift.py
```

ソース: [examples/poc_panorama_drift.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_panorama_drift.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_panorama_drift)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`pose_error`](https://furuse.work/ops/3d/metrics/pose_error.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html) · [`warp_by_plane`](https://furuse.work/ops/3d/plane_sweep_stereo/warp_by_plane.html)

## No.2026.108 —— 実写のステレオ写真で測る ―― 合成では出ない 3 つの躓き

[![実写のステレオ写真で測る ―― 合成では出ない 3 つの躓き](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stereo_depth/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stereo_depth/01_scene.png)

*↑ **実写のステレオ写真で測る ―― 合成では出ない 3 つの躓き** ―― この博物館で初めて**実写**を通した 1 本(Middlebury 2014 motorcycle、真値視差つき)。★配布元の注記は真値の穴を NaN と書いているが実際は +inf で、np.nanmedian は中央視差を 42.55 px でなく 44.97 px と答える(isfinite で判定している fill_disparity と apply_cmap は正しく穴として扱った)。★既定 max_disp=16 は bad2 95.06 % ―― 真の最大視差 59.91 px を下回る設定は前景を丸ごと失うので、崖は 48 と 64 の間に立つ(幾何から先に言える)。ゼロ点 94.04 % に対し SGM 15.81 %、信頼度で下位 4 割を捨てると 6.80 %。★★距離に落とすところで形が反り返る: depth_from_disparity に主点オフセット doffs が無く、実写の校正値 31.086 px を無視すると距離が 1.519〜5.243 倍にばらけ、最良の単一スケール 0.3733 を掛けてなお残差 958.3 mm RMS(奥行きレンジ 2889 mm の 33.2 %)、遠い面は +1676 mm 押し出され近い面は -926 mm 引き込まれる。この PoC で doffs を引数に足した(閉形式と最大差 0 mm)。★census は実装が弱いのではなく 64 bit パックで窓が 7 で頭打ち(3/5/7 で 75.27/48.62/35.44 % と伸びている途中)。*

[![下位 4 割を捨てると bad2 は 26.75 % -> 6.80 %。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stereo_depth/02_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stereo_depth/02_error.png)

*↑ 測定の図 ―― 下位 4 割を捨てると bad2 は 26.75 % -> 6.80 %。*

[![真の最大視差を下回る設定は前景を丸ごと失う。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stereo_depth/03_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stereo_depth/03_cliff.png)

*↑ 真の最大視差を下回る設定は前景を丸ごと失う。*

[![単一のスケールでは直らない(最良でも残差 958 mm RMS)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stereo_depth/04_depth_bend_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stereo_depth/04_depth_bend.png)

*↑ 単一のスケールでは直らない(最良でも残差 958 mm RMS)。*

[![census が最下位なのは窓が 64 bit で頭打ちだから。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stereo_depth/05_methods_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stereo_depth/05_methods.png)

*↑ census が最下位なのは窓が 64 bit で頭打ちだから。*

```
py -3.11 examples/poc_real_stereo_depth.py
```

ソース: [examples/poc_real_stereo_depth.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_stereo_depth.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_real_stereo_depth)



## No.2026.034 —— 点群位置合わせの収束域 ―― 初期姿勢がどれだけずれたら壊れるか

[![点群位置合わせの収束域 ―― 初期姿勢がどれだけずれたら壊れるか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/01_basin_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/01_basin.png)

*↑ **点群位置合わせの収束域 ―― 初期姿勢がどれだけずれたら壊れるか** ―― 点群を毎試行取り直し、初期姿勢のずれに対する ICP の成功率を等高線にした図。並進ずれ 0 で成功率が 50 % を切るのは点対点 90 度、点対面 120 度。球や円柱は残差が同じまま姿勢が任意で、大域手法では 16/16 が見かけ上収束しつつ姿勢は誤り ―― 残差では検出できない。*

[![非対称性が消えると 4 候補が形として区別できず、選択が崩れる(選ばれた解が第 1 候補から離れる)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/02_pca_quadrant_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/02_pca_quadrant.png)

*↑ 測定の図 ―― 非対称性が消えると 4 候補が形として区別できず、選択が崩れる(選ばれた解が第 1 候補から離れる)。*

[![平らな線ほど「広い」。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/03_width_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/03_width.png)

*↑ 平らな線ほど「広い」。*

[![球・円柱は残差が小さいまま姿勢が任意。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/04_symmetry_lies_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/04_symmetry_lies.png)

*↑ 球・円柱は残差が小さいまま姿勢が任意。*

[![点対点 ICP を 1 反復ずつ動かす(fs.icp(max_iter=1) を前回の姿勢から連鎖)。灰 = 目標の点群、色 = 動かしている点群(斜めから見た正射影)。同じ回転軸で初期回転ずれだけを 30 / 90 / 150 度と変え、](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/05_icp_basin_iterations.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/05_icp_basin_iterations.gif)

*↑ 動く図 ―― 点対点 ICP を 1 反復ずつ動かす(fs.icp(max_iter=1) を前回の姿勢から連鎖)。灰 = 目標の点群、色 = 動かしている点群(斜めから見た正射影)。同じ回転軸で初期回転ずれだけを 30 / 90 / 150 度と変え、並進ずれは直径の 10 %。反復予算は本文の点対点 ICP と同じ 60 回で、その後の回転誤差: 30 度 → 0.6 度(成功)、90 度 → 0.6 度(成功)、150 度 → 179.5 度(失敗)。下の曲線は回転誤差の推移(対数、灰線 = 成功のしきい値 3 度)。動画専用に取り直した 1 組の点群での 1 試行の軌跡で、成功率は第 2 章の表。*

```
py -3.11 examples/poc_registration_basin.py
```

ソース: [examples/poc_registration_basin.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_registration_basin.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_registration_basin)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`farthest_point_sampling`](https://furuse.work/ops/3d/geodesic/farthest_point_sampling.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html)

## No.2026.117 —— 「回転しても同じ」と言える量はどれか —— 実写の硬貨を 72 角度で回して数える

[![「回転しても同じ」と言える量はどれか —— 実写の硬貨を 72 角度で回して数える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rotation_invariance_audit/01_rotation_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rotation_invariance_audit/01_rotation_frames.png)

*↑ **「回転しても同じ」と言える量はどれか —— 実写の硬貨を 72 角度で回して数える** ―― 形の特徴量は当たり前のように「回転不変」と呼ばれる。だが**画素の格子は回転で不変ではない**ので、その主張はたいてい下請け(境界の数え方・補間・しきい値)の任意性のところで壊れる。scikit-image 同梱の実写 `coins`(大英博物館、ポンペイ出土のギリシャ硬貨)を 5 度ずつ 1 周させ、揺れを**3 本の腕**に分けて犯人を特定する: **A** 灰を線形補間して回してから二値化(人が実際にやること)/ **B** 0 度の二値マスクを最近傍で回す(境界の再ラスタライズだけ)/ **C** 90 度の倍数だけを `np.rot90` で回す(補間も再ラスタライズも無い)。回す道具は fullseye ではなく scipy —— 自分の回転で自分の不変性を測ると、両方同じ向きに間違っても気づけない。★**腕 C は 7 量すべてきっかり 0.00 %**。測り方そのものに向き依存は無く、揺れは全部「格子に置き直す代償」。★★**予測が外れた**: 書いた時点では「灰を補間して二値化し直すほうが荒れる」と思っていたが、**逆**だった —— 周囲長は A **2.52 %** < B **9.47 %**(3.8 倍)、円形度は A **4.82 %** < B **20.45 %**(4.2 倍)。二値マスクを最近傍で回すと境界が**階段のまま置き直される**のに対し、灰を補間してから二値化すると境界が下の連続信号から引き直される。**回すなら灰でやってから二値化する。二値マスクを回してはいけない。**★閉形式の錨(合成の正方形 L=80)では、45 度の 4 連結階段周囲長 `4L → 4L√2` の **+41.4 %** が上限。実測は **7.91 %** で、`regionprops` の Crofton 補正が 5.2 倍下回らせている —— 予測は「上限」であって「実測の当て」ではない、と書いておく。★**分母を疑う**: Hu[1](`moments_region_central_invar`)は円に近い形では真値がほぼ 0(3.9e-04)なので、相対ばらつき 29.6 % は「30 % ずれた」ではなく**0 を分母にした**だけ。表にその判定を並べてある。★図は反転色 `mode="xor"`(最上位 bit だけ反転 —— 地の模様が残り、どの階調でも消えない)で輪郭を描き、72 コマの GIF で数字の揺れが見えるようにした。*

[![実写の硬貨を 5 度ずつ 1 周。地がモノクロなので輪郭は彩度のある色で描いている(灰色には彩度が無いので、どの階調とも色相で区別がつく)。右の表の数字がどれだけ揺れるかが見える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rotation_invariance_audit/02_rotating_coin.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rotation_invariance_audit/02_rotating_coin.gif)

*↑ 測定の図 ―― 実写の硬貨を 5 度ずつ 1 周。地がモノクロなので輪郭は彩度のある色で描いている(灰色には彩度が無いので、どの階調とも色相で区別がつく)。右の表の数字がどれだけ揺れるかが見える。*

```
py -3.11 examples/poc_rotation_invariance_audit.py
```

ソース: [examples/poc_rotation_invariance_audit.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_rotation_invariance_audit.py)

この回が作った図は全部で **2 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_rotation_invariance_audit)

使用 op(ノートへ): [`annotate_outline`](https://furuse.work/ops/annotate/paper/annotate_outline.html) · [`annotate_table`](https://furuse.work/ops/annotate/paper/annotate_table.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`circularity`](https://furuse.work/ops/2d/features/circularity.html) · [`eccentricity`](https://furuse.work/ops/2d/features/eccentricity.html) · [`moments_region_2nd_invar`](https://furuse.work/ops/2d/features/moments_region_2nd_invar.html) · [`moments_region_central_invar`](https://furuse.work/ops/2d/features/moments_region_central_invar.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html)

## No.2026.133 —— 公共カメラはどこを向いているか ―― 位置しか公開されない固定カメラの向きを、写真そのものから決める

[![公共カメラはどこを向いているか ―― 位置しか公開されない固定カメラの向きを、写真そのものから決める](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading/02_yaw_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading/02_yaw_sweep.gif)

*↑ **公共カメラはどこを向いているか ―― 位置しか公開されない固定カメラの向きを、写真そのものから決める** ―― 公共の固定カメラ(道路・気象・観光)は位置は公開されるが向きは無いか粗い(道路の増減方向、id のハッシュ、手校正)。向きが無いと写真を地図・DEM・3D 都市に置けない。新族 geocam(7 op、numpy + scipy)は位置既知のカメラの (yaw, pitch, roll) を写真そのものから学習なしで、2 つの独立な手掛かりで決めて互いに検算する。(1) スカイライン: カメラ位置から DEM で描いた 360° の稜線(dem_skyline、地球の丸みと屈折、DEM の外は地平線の沈みで下限)と、写真から動的計画法で抜いた空と地形の境界(skyline_extract、Lie ら 2005)を照合し、yaw を一周した残差曲線と 2 番目の谷との差(margin)を返す(camera_orientation_from_skyline)。(2) 太陽: 太陽の見かけの位置は時刻と場所の閉形式(sun_position、NOAA、春分・夏至の既知値で検証)。写真の飽和した円盤(sun_pixel_position、雲や空の帯は充填率で拒否)を 2 点以上拾えば回転は Wahba 問題の SVD 解で一意(camera_orientation_from_sun)。真値の姿勢が分かる合成カメラ(合成 DEM + 空 + 雲 + 前景の柱 + 雑音、内部行列既知)で、スカイライン経路の誤差 0.11 / 0.06 / 0.06°、太陽経路 0.02 / 0.04 / 0.05°(6 コマ、朝夕の 2 コマだけでも 0.004°)、2 経路の一致 0.09°。対照 = 公開メタデータに近い「道路方向の事前知識」は 7.5°、平地の DEM では稜線が全方位で同じなので op が ambiguous を返す(黙って 137° 間違えない)。先行 = Lalonde ら IJCV 2010(太陽と空、webcam 22 台で 3°)/ Baatz ら ECCV 2012(スカイライン、位置未知の大規模版)。正直な内訳: 合成のみ(実データはフィンランド Fintraffic + NLS 標高、ノルウェー Statens vegvesen + Kartverket DTM10 が次の段、生画像は commit しない)、内部行列 K は要る(誤りは pitch と roll に化ける)、スカイラインは山があってこそ、太陽は写っていてこそ。*

[![the DEM ridge drawn at the estimated yaw / pitch / roll lies on the extracted skyline; errors 0.06 / 0.03 / 0.01 deg](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading/01_skyline_lock_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading/01_skyline_lock.png)

*↑ 測定の図 ―― the DEM ridge drawn at the estimated yaw / pitch / roll lies on the extracted skyline; errors 0.06 / 0.03 / 0.01 deg*

[![the op returns the whole residual curve so that the ambiguity is visible: a runner-up valley at 15 d](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading/03_yaw_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading/03_yaw_profile.png)

*↑ the op returns the whole residual curve so that the ambiguity is visible: a runner-up valley at 15 deg is 1.28 deg worse; the flat DEM curve is level*

[![the sun's path over the day where it is above the ridge (yellow, projected with the pose estimated f](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading/04_sun_track_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading/04_sun_track.png)

*↑ the sun's path over the day where it is above the ridge (yellow, projected with the pose estimated from the sun) and the 5 sun discs picked by sun_pix…*

[![both routes recover the pose to well under a degree and agree with each other; the public-metadata p](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading/05_numbers_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading/05_numbers.png)

*↑ both routes recover the pose to well under a degree and agree with each other; the public-metadata prior is off by ten degrees and the flat-ground cas…*

```
py -3.11 examples/poc_public_camera_heading.py
```

ソース: [examples/poc_public_camera_heading.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_public_camera_heading.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_public_camera_heading)

使用 op(ノートへ): [`camera_orientation_from_skyline`](https://furuse.work/ops/geocam/orientation/camera_orientation_from_skyline.html) · [`camera_orientation_from_sun`](https://furuse.work/ops/geocam/sun/camera_orientation_from_sun.html) · [`dem_skyline`](https://furuse.work/ops/geocam/skyline/dem_skyline.html) · [`project`](https://furuse.work/ops/3d/bundle_adjust/project.html) · [`render_skyline_view`](https://furuse.work/ops/geocam/skyline/render_skyline_view.html) · [`skyline_extract`](https://furuse.work/ops/geocam/skyline/skyline_extract.html) · [`sun_pixel_position`](https://furuse.work/ops/geocam/sun/sun_pixel_position.html) · [`sun_position`](https://furuse.work/ops/geocam/sun/sun_position.html)

## No.2026.134 —— 公共カメラはどこを向いているか・実写編 ―― 807 局の道路カメラで太陽を探し、日没 1 本から向きを決めて道路で検算する

[![公共カメラはどこを向いているか・実写編 ―― 807 局の道路カメラで太陽を探し、日没 1 本から向きを決めて道路で検算する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading_real/02_sunset_follow.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading_real/02_sunset_follow.gif)

*↑ **公共カメラはどこを向いているか・実写編 ―― 807 局の道路カメラで太陽を探し、日没 1 本から向きを決めて道路で検算する** ―― 合成(poc_public_camera_heading)では「太陽 = 飽和した小さな円盤」で足りたが、実写の道路カメラは違った。フィンランド Fintraffic 天候カメラ(807 局、CC BY 4.0、鍵なし)の 9 月 20〜21 日 24 時間分から太陽高度 2〜12° のフレームだけ探針すると、見た目の門(sun_pixel_position)は局名の白い文字・標識・白い車・レンズの水滴を太陽と言い(最初の探針で 24/24 誤検出)、太陽は円盤でなく露出で大きさの変わるブルームで上端の局名帯で切れ、カメラは道路を見下ろして空は上 3 分の 1しか無い。そこで geocam に 2 op を足した: sun_bloom_fit(最大の飽和塊の切れていない縁に Kåsa の円を当てて中心を返す。重心は切れた側の反対へ平均 12 px 偏る)と camera_orientation_from_sun_candidates(フレームごとの候補から、固定カメラで太陽の速さで動く 1 本を RANSAC で選び、道路カメラの事前知識 |roll| ≤ 12°・pitch −40〜0°・水平画角 25〜120° で非物理な仮説を捨て、焦点距離も同時に探索する。地平線下の時刻は投票しない)。807 局 × 24 時間で追えた日没は 1 本(E18・Hamina、公式メタデータの向きは UNKNOWN): 5 枚(15:01〜16:01 UTC)から yaw 267.9°・pitch −4.6°・roll 0.9°・f 1439 px(水平画角 48°)、残差 0.34°。独立な検算 = 同じ姿勢で画像中の車線の消失点(昼のフレーム複数の medoid)を世界方位に変えると 272.7°、OpenStreetMap の E18 の路線方位は 275.3°、差 2.5°。弱い自由度は隠さない: 1 枚抜きで yaw は 1.3° しか動かないが roll は 10°、f は 2 % 動く(1 時間の低仰角の弧の限界)。同じ写真で見た目の門は 22 回「太陽」と言い、正確 3・太陽だが中心ずれ 2・別の物 17。生画像は commit せず、集計(時刻・円当て・消失点・路線方位)だけを置く。出典 Fintraffic / Digitraffic(CC BY 4.0)、OpenStreetMap(ODbL)。*

[![the sunset seen by C0362200 (E18, Hamina, Finland; metadata says direction UNKNOWN): the sun's path for the evening draw](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading_real/01_sunset_track_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading_real/01_sunset_track.png)

*↑ 測定の図 ―― the sunset seen by C0362200 (E18, Hamina, Finland; metadata says direction UNKNOWN): the sun's path for the evening drawn from the fitted pose (magenta) and the 5 blooms fitted with a circle (cyan); yaw 267.9, pitch -4.6, roll 0.9, HFOV 48*

[![what the look-alone detector (sun_pixel_position, built for synthetic discs) called the sun in the s](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading_real/03_naive_picks_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading_real/03_naive_picks.png)

*↑ what the look-alone detector (sun_pixel_position, built for synthetic discs) called the sun in the same camera: 22 picks, 3 exactly the sun, 2 on the…*

[![refit with each sun frame removed: yaw barely moves, roll and the focal length are the weak directio](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading_real/04_jackknife_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading_real/04_jackknife.png)

*↑ refit with each sun frame removed: yaw barely moves, roll and the focal length are the weak directions of a 1-hour low-elevation arc — this is why the…*

[![for blooms cut by the station-name band the centroid sits 12.4 px (mean) away from the circle fitted](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading_real/05_bloom_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading_real/05_bloom_bias.png)

*↑ for blooms cut by the station-name band the centroid sits 12.4 px (mean) away from the circle fitted to the unclipped rim; the fit uses the circle*

[![one camera out of 807 stations gave a sun track of 4 or more frames on 2026-09-20/21 (2 more had 3 f](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading_real/06_numbers_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_public_camera_heading_real/06_numbers.png)

*↑ one camera out of 807 stations gave a sun track of 4 or more frames on 2026-09-20/21 (2 more had 3 frames and were left out); the vanishing point of i…*

```
py -3.11 examples/poc_public_camera_heading_real.py
```

ソース: [examples/poc_public_camera_heading_real.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_public_camera_heading_real.py)

この回が作った図は全部で **6 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_public_camera_heading_real)

使用 op(ノートへ): [`bloom`](https://furuse.work/ops/gfx2d/post/bloom.html) · [`camera_orientation_from_sun_candidates`](https://furuse.work/ops/geocam/sun/camera_orientation_from_sun_candidates.html) · [`ellipse`](https://furuse.work/ops/annotate/shape/ellipse.html) · [`project`](https://furuse.work/ops/3d/bundle_adjust/project.html) · [`sun_position`](https://furuse.work/ops/geocam/sun/sun_position.html)

### 色・分離ウィング ―― 「効く手法」は無い、あるのは効く条件だけ

光源を推定して色を戻す、多波長で絵画の層を剥がす、偏光で鏡面反射を分離する。この部屋の 4 点は、既知の分光反射率・既知の光源・フレネルの式から線形の輻度を合成し、分離の結果を真値と突き合わせています。

結論は、どの展示でも「壊れる軸が直交している」ことでした。白パッチ法は白が在れば最良で、いちばん明るい 1 枚を外すだけで 8 倍悪くなる。灰色世界は飽和に強く、有彩色が 2 割を超えると負ける。基準光源では全手法がゼロ点に負ける。バンドを増やしても勝てず、近赤外を入れた瞬間に勝つ。

共通の注意は「リニアな輻度に戻してから渡す」こと。sRGB ガンマのまま渡しても例外は出ず、分離が静かに劣化するだけです。例外が出ない失敗は、この展示全体で最も多い型です。

## No.2026.032 —— 多波長で層を剥がす ―― 下絵・地塗り・上塗り・褪色を、真値を握ったまま分離する

[![多波長で層を剥がす ―― 下絵・地塗り・上塗り・褪色を、真値を握ったまま分離する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/01_per_field_auc_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/01_per_field_auc.png)

*↑ **多波長で層を剥がす ―― 下絵・地塗り・上塗り・褪色を、真値を握ったまま分離する** ―― 地塗り・下絵・上塗り・褪色を重ねた分光キューブを合成し、層を分離した図。可視だけを 16 バンドに割っても RGB と同じ(再現率 0.118 対 0.119)で、勝ったのは近赤外を入れたこと。同じ検出器が群青で AUC 1.000、アズライトで 0.630、剥落部で 0.013 ―― 平均すると全部消える。褪色前の色の復元は ΔE00 16.79 → 16.46 で、ゼロ点にほぼ勝てなかった。*

[![近赤外の差分は剥落部(楕円)で消え、近赤外 1 枚は面ごとに水準が違う。塗り分けは 1–99 分位でクリップした表示のみ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/02_detector_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/02_detector_maps.png)

*↑ 測定の図 ―― 近赤外の差分は剥落部(楕円)で消え、近赤外 1 枚は面ごとに水準が違う。塗り分けは 1–99 分位でクリップした表示のみ。*

[![半分を割るのは tau 0.30–0.60 のあいだ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/03_thickness_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/03_thickness_cliff.png)

*↑ 半分を割るのは tau 0.30–0.60 のあいだ。*

[![ゼロ点の線より下に来た復元が 1 本も無い。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/04_restoration_vs_null_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/04_restoration_vs_null.png)

*↑ ゼロ点の線より下に来た復元が 1 本も無い。*

```
py -3.11 examples/poc_pigment_unmixing.py
```

ソース: [examples/poc_pigment_unmixing.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pigment_unmixing.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_pigment_unmixing)

使用 op(ノートへ): [`delta_e_map`](https://furuse.work/ops/imgmetrics/colordiff/delta_e_map.html) · [`linear_to_srgb`](https://furuse.work/ops/gfx2d/colorspace/linear_to_srgb.html) · [`spectrum_to_srgb`](https://furuse.work/ops/optics/appearance/spectrum_to_srgb.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html)

## No.2026.033 —— 偏光で鏡面反射を剥がす ―― フレネルの式で真値を作り、分離結果を突き合わせる

[![偏光で鏡面反射を剥がす ―― フレネルの式で真値を作り、分離結果を突き合わせる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/01_fresnel_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/01_fresnel.png)

*↑ **偏光で鏡面反射を剥がす ―― フレネルの式で真値を作り、分離結果を突き合わせる** ―― 拡散と鏡面を s/p 成分で合成し、フレネルの式から偏光度を出して分離結果を採点した図。偏光を使う手は入射角 20 度では 1.2 倍しか勝たない。拡散成分の誤差は閉形式 R_p·E に一致してブリュースター角 56.31 度で 0 ―― `polarization_separate` の拡散はその分だけ系統的に大きい。*

[![実測と閉形式が重なる。70 度の絶対誤差は 20 度より悪いのに、ゼロ点比では 70 度が最良 —— 最適角は評価軸で割れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/02_angle_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/02_angle_error.png)

*↑ 測定の図 ―― 実測と閉形式が重なる。70 度の絶対誤差は 20 度より悪いのに、ゼロ点比では 70 度が最良 —— 最適角は評価軸で割れる。*

[![残差はローブと同じ形。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/03_separation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/03_separation.png)

*↑ 残差はローブと同じ形。*

[![画素率 1.8 倍で誤差 2.8 倍 —— 雑音(σ に比例)や較正誤差(δ に比例)と違い、飽和は超線形に効く。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/04_saturation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/04_saturation.png)

*↑ 画素率 1.8 倍で誤差 2.8 倍 —— 雑音(σ に比例)や較正誤差(δ に比例)と違い、飽和は超線形に効く。*

```
py -3.11 examples/poc_polarization_specular.py
```

ソース: [examples/poc_polarization_specular.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_polarization_specular.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_polarization_specular)

使用 op(ノートへ): [`fresnel_reflectance`](https://furuse.work/ops/3d/optics/fresnel_reflectance.html) · [`polarization_dolp_map`](https://furuse.work/ops/specular/polarization/polarization_dolp_map.html) · [`polarization_render`](https://furuse.work/ops/specular/polarization/polarization_render.html) · [`polarization_separate`](https://furuse.work/ops/specular/polarization/polarization_separate.html) · [`polarization_stokes`](https://furuse.work/ops/specular/polarization/polarization_stokes.html) · [`rmse`](https://furuse.work/ops/imgmetrics/fidelity/rmse.html)

## No.2026.107 —— 実写の免疫染色を色で分ける ―― 見張り役が、見張るべき誤りにだけ盲目だった

[![実写の免疫染色を色で分ける ―― 見張り役が、見張るべき誤りにだけ盲目だった](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stain_unmix/01_separation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stain_unmix/01_separation.png)

*↑ **実写の免疫染色を色で分ける ―― 見張り役が、見張るべき誤りにだけ盲目だった** ―― 実写の免疫染色像(ヘマトキシリン + DAB)を色分離する。★合成なら完璧に分かれる(片方だけ濃度 1.0 を合成して解き直すと回収 1.0000 / 漏れ 0.0000)ので、合成だけ見ていると「解けている」で終わる。★実写では H の濃度が -4.446 まで振れ、負になる画素が 11.51 % ―― 負の濃度は「色素が光を出した」の意味で存在しない。★★染色ベクトルを平面内で ±20 度回すと H の中央値は 0.0471 → 0.1348(2.86 倍)、DAB は 0.3590 → 0.1836 と大きく動くのに、**残差チャネルの絶対中央値は 0.0345 のまま幅 3.3e-16** ―― 2 本が張る平面は回しても変わらないので、平面に直交する残差は定義上動かない。**「あてはまりの良さ」を見張っているつもりの量が、いちばん起こりやすい誤りだけを見ていない**。★★回した染色自身の負率も 11.51 % で完全に不変(双対ベクトルの向きが変わらず長さだけ変わるので符号は 1 画素も動かない)。動くのは相方 DAB の負率だけで、-20 度 0.00 % → +20 度 30.38 %。**見張り役は、自分ではなく相方を見る**。ただし単調なので片側の上限しか出ない。★往復の再構成は最大誤差 1e-06 だが、それは 4 節の誤りを何も否定しない ―― 何を検算しているかを言わないと検算にならない。この回に stain_unmix / stain_recompose / stain_vectors_from_patches を新設した(spec_unmix は 3 チャネルを設計上拒否するので RGB の入口が無かった)。*

[![H の中央値は 0.0656 -> 0.1348。残差の絶対中央値は 0.0345 のまま。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stain_unmix/02_blind_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stain_unmix/02_blind.png)

*↑ 測定の図 ―― H の中央値は 0.0656 -> 0.1348。残差の絶対中央値は 0.0345 のまま。*

[![残差と自分の負率は平坦。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stain_unmix/03_diagnostics_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stain_unmix/03_diagnostics.png)

*↑ 残差と自分の負率は平坦。*

[![濃度は 2.9 倍動くのに残差は 4 桁目まで同じ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stain_unmix/04_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stain_unmix/04_sweep.png)

*↑ 濃度は 2.9 倍動くのに残差は 4 桁目まで同じ。*

```
py -3.11 examples/poc_real_stain_unmix.py
```

ソース: [examples/poc_real_stain_unmix.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_stain_unmix.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_real_stain_unmix)



## No.2026.051 —— 色恒常性(ホワイトバランス)―― 「効く手法」は無い、あるのは効く条件だけ

[![色恒常性(ホワイトバランス)―― 「効く手法」は無い、あるのは効く条件だけ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/01_casts_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/01_casts.png)

*↑ **色恒常性(ホワイトバランス)―― 「効く手法」は無い、あるのは効く条件だけ** ―― 24 枚の既知分光反射率と既知光源から線形 RGB を合成し、光源推定の回復角度誤差を測った図。白パッチ法は 11 光源の中央値 1.06 度で最良だが、いちばん明るい 1 枚を外すと 8.45 度、露出 3 倍で 43 % を飽和させると 13.61 度で「何もしない」と一致。真の光源で対角補正しても 2500 K では ΔE00 平均 5.07 が残る。*

[![灰色世界はゼロ点(何もしない)の線を 0.1〜0.2 の間で上抜けする = そこから先は回すだけ損。白パッチ法には崖が無い。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/02_bias_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/02_bias_cliff.png)

*↑ 測定の図 ―― 灰色世界はゼロ点(何もしない)の線を 0.1〜0.2 の間で上抜けする = そこから先は回すだけ損。白パッチ法には崖が無い。*

[![露出 3 以上で白パッチ法の線が「何もしない」に重なる(max が (1,1,1) に張り付く)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/03_saturation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/03_saturation.png)

*↑ 露出 3 以上で白パッチ法の線が「何もしない」に重なる(max が (1,1,1) に張り付く)。*

[![最右列が推定誤差の実費。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/04_angle_to_de_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/04_angle_to_de.png)

*↑ 最右列が推定誤差の実費。*

```
py -3.11 examples/poc_white_balance.py
```

ソース: [examples/poc_white_balance.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_white_balance.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_white_balance)

使用 op(ノートへ): [`delta_e_map`](https://furuse.work/ops/imgmetrics/colordiff/delta_e_map.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`illuminant_from_dichromatic_planes`](https://furuse.work/ops/specular/dichromatic/illuminant_from_dichromatic_planes.html) · [`laplace`](https://furuse.work/ops/2d/edges/laplace.html) · [`linear_to_srgb`](https://furuse.work/ops/gfx2d/colorspace/linear_to_srgb.html) · [`mean_image`](https://furuse.work/ops/2d/smoothing/mean_image.html) · [`prewitt_amp`](https://furuse.work/ops/2d/edges/prewitt_amp.html) · [`roberts`](https://furuse.work/ops/2d/edges/roberts.html) · [`sobel_amp`](https://furuse.work/ops/2d/edges/sobel_amp.html) · [`spectrum_to_srgb`](https://furuse.work/ops/optics/appearance/spectrum_to_srgb.html)

### 法科学・文書ウィング ―― 1 枚の成功例は証拠にならない

改竄検出と書類の正対化。どちらも「見つかった 1 枚」「まっすぐになった 1 枚」で語られがちですが、この部屋の 4 点は、貼付の場所と品質、既知のホモグラフィと照明、を自分で決めた上で、画素ごとの ROC と画素単位の幾何誤差で採点しています。

改竄検出は検出側(防御)の PoC です。改竄を自分で作るのは検出器を測るのに真値が要るためだけで、作り方は最も稚拙なものに留めてあります。この展示がいちばん強く示すのは、保存ボタン 1 回でどの手掛かりも弱る、という検出側に不利な事実のほうです。

書類のほうは、名前が同じでモデルが違う関数を取り違えても例外が出ず、台形が残ったままもっともらしい絵が返る、という穴を数字にしています。影除去に良いところ取りは無く、平らにするほど薄い字が消えます。

## No.2026.015 —— 手持ちで撮った書類をまっすぐに戻す ―― 台形補正と影除去を、真値と突き合わせて測る

[![手持ちで撮った書類をまっすぐに戻す ―― 台形補正と影除去を、真値と突き合わせて測る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/01_rectify_zero_points_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/01_rectify_zero_points.png)

*↑ **手持ちで撮った書類をまっすぐに戻す ―― 台形補正と影除去を、真値と突き合わせて測る** ―― 既知のホモグラフィと照明で撮った書類を戻し、4 隅と格子の画素誤差で採点した図。推定は格子 RMS 1.070 px(何もしない 37.376 px)だが、名前が同じでモデルが違う関数(アフィン)を取り違えると 32 倍悪く、例外は出ない。影の強さ 0.45 で 4 隅 RMS 5.72 px、0.55 で 65.10 px と崖。*

[![平坦・薄字・誤検出なしを同時に満たす行は 1 つも無い。窓 9 が fs.op で届く上限、窓 61 は自前。図の階調は真値で 217 段。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/02_shadow_tradeoff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/02_shadow_tradeoff.png)

*↑ 測定の図 ―― 平坦・薄字・誤検出なしを同時に満たす行は 1 つも無い。窓 9 が fs.op で届く上限、窓 61 は自前。図の階調は真値で 217 段。*

[![下寄りの横長の帯が図の階調。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/03_shadow_removal_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/03_shadow_removal.png)

*↑ 下寄りの横長の帯が図の階調。*

[![60 度でも 2 px 台。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/04_tilt_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/04_tilt_cliff.png)

*↑ 60 度でも 2 px 台。*

```
py -3.11 examples/poc_document_scan.py
```

ソース: [examples/poc_document_scan.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_document_scan.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_document_scan)

使用 op(ノートへ): [`corner_response`](https://furuse.work/ops/2d/edges/corner_response.html) · [`dc_homomorphic`](https://furuse.work/ops/2d/decomposition/dc_homomorphic.html) · [`fill_holes`](https://furuse.work/ops/2d/region/fill_holes.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`get_region_contour`](https://furuse.work/ops/2d/region/get_region_contour.html) · [`gray_tophat`](https://furuse.work/ops/2d/morphology/gray_tophat.html) · [`illuminate`](https://furuse.work/ops/2d/gray/illuminate.html) · [`mean_image`](https://furuse.work/ops/2d/smoothing/mean_image.html) · [`opening_circle`](https://furuse.work/ops/2d/region/opening_circle.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`project_points`](https://furuse.work/ops/3d/render/project_points.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`select_largest`](https://furuse.work/ops/2d/region/select_largest.html) · [`sobel_dir`](https://furuse.work/ops/2d/edges/sobel_dir.html) · [`var_threshold`](https://furuse.work/ops/2d/segmentation/var_threshold.html)

## No.2026.020 —— 改竄検出を ROC で語る ―― 「見つかった 1 枚」ではなく、偽陽性を固定したときの検出率

[![改竄検出を ROC で語る ―― 「見つかった 1 枚」ではなく、偽陽性を固定したときの検出率](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/01_score_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/01_score_maps.png)

*↑ **改竄検出を ROC で語る ―― 「見つかった 1 枚」ではなく、偽陽性を固定したときの検出率** ―― JPEG q60 の素材を q92 の背景に貼って q95 で保存した改竄画像 10 枚を、画素ごとの ROC で採点した図。ELA の 1 つの数字は向きが教科書と逆(貼付部 / 背景 = 0.58 倍)で、改竄していない画像でも場所への偏りで AUC 0.797 が出る。ゴーストの谷の深さは AUC 0.997 だが、全体を q75 で再圧縮すると 0.975 へ落ちる。*

[![凡例の数字は AUC。乱数が対角線に乗ることで測り方に偏りが無いと言える。ゴーストA は乱数と重なる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/02_roc_tampered_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/02_roc_tampered.png)

*↑ 測定の図 ―― 凡例の数字は AUC。乱数が対角線に乗ることで測り方に偏りが無いと言える。ゴーストA は乱数と重なる。*

[![凡例の数字は AUC。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/03_roc_postprocess_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/03_roc_postprocess.png)

*↑ 凡例の数字は AUC。*

[![保存ボタン 1 回(q60 再圧縮)で ゴーストV は乱数以下。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/04_breaking_conditions_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/04_breaking_conditions.png)

*↑ 保存ボタン 1 回(q60 再圧縮)で ゴーストV は乱数以下。*

```
py -3.11 examples/poc_forensics_roc.py
```

ソース: [examples/poc_forensics_roc.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_forensics_roc.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_forensics_roc)

使用 op(ノートへ): [`copy_move_regions`](https://furuse.work/ops/imgforensics/copy_move/copy_move_regions.html) · [`error_level_map`](https://furuse.work/ops/imgforensics/compression/error_level_map.html) · [`jpeg_ghost_map`](https://furuse.work/ops/imgforensics/compression/jpeg_ghost_map.html) · [`jpeg_ghost_quality`](https://furuse.work/ops/imgforensics/compression/jpeg_ghost_quality.html) · [`noise_inconsistency_map`](https://furuse.work/ops/imgforensics/noise/noise_inconsistency_map.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html)

## No.2026.067 —— 絵画のひび割れ網 ―― 3 指標のうち撮影条件で壊れるのは分岐次数だけ

[![絵画のひび割れ網 ―― 3 指標のうち撮影条件で壊れるのは分岐次数だけ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/07_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/07_scene.png)

*↑ **絵画のひび割れ網 ―― 3 指標のうち撮影条件で壊れるのは分岐次数だけ** ―― ボロノイ網を閉形式で描き、乾燥ひび(セル小・蛇行)と経年ひび(セル大・格子的)の 2 種に色斑・光沢むら・斜光・ぼけ・雑音を足して、リッジ op → 骨格 → 分岐点の op 列で網を測った。真値でセル径 18.0 vs 45.2 px、直線度 0.960 vs 1.000、次数 4 割合 0.20 vs 0.83 と 3 指標とも 2 種を分けるが、経年型の次数 4 割合は質感で 0.87 → 0.64、斜光で 0.70 と乾燥側へ動き、セル径と直線度は動かない。予想した崖は 2 つとも来なかった: 幅 0.15 px でも再現率 0.696、質感 c = 0.64 でも偽陽性 0.382。斜光は幅を +0.37 px 片側に太らせ、中心線を光源側へ 0.75 px 寄せる。*

[![Frangi は分岐点で応答が落ち、斜光でセルが崩れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/01_ridge_ops_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/01_ridge_ops.png)

*↑ 測定の図 ―― Frangi は分岐点で応答が落ち、斜光でセルが崩れる。*

[![真値は幾何(ボロノイの頂点・辺)から。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/02_indicators_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/02_indicators.png)

*↑ 真値は幾何(ボロノイの頂点・辺)から。*

[![ひびの深さ 0.55。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/04_texture_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/04_texture_cliff.png)

*↑ ひびの深さ 0.55。*

[![ぼけが大きいほど小さいセルから消える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/06_blur_cell_limit_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/06_blur_cell_limit.png)

*↑ ぼけが大きいほど小さいセルから消える。*

[![縁に触れるセルは統計から外す(真値も同じ規約)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/09_map_cells_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/09_map_cells.png)

*↑ 縁に触れるセルは統計から外す(真値も同じ規約)。*

```
py -3.11 examples/poc_fresco_craquelure.py
```

ソース: [examples/poc_fresco_craquelure.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_fresco_craquelure.py)

この回が作った図は全部で **11 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_fresco_craquelure)

使用 op(ノートへ): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`cv_blackhat`](https://furuse.work/ops/2d/morphology/cv_blackhat.html) · [`distance_transform`](https://furuse.work/ops/2d/region/distance_transform.html) · [`hx_split_skeleton_region`](https://furuse.work/ops/2d/halcon_ext/hx_split_skeleton_region.html) · [`hysteresis_threshold`](https://furuse.work/ops/2d/segmentation/hysteresis_threshold.html) · [`junctions_skeleton`](https://furuse.work/ops/2d/region/junctions_skeleton.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`pruning`](https://furuse.work/ops/2d/region/pruning.html) · [`r2_endpoints_skeleton`](https://furuse.work/ops/2d/region/r2_endpoints_skeleton.html) · [`sk_area_opening`](https://furuse.work/ops/2d/morphology/sk_area_opening.html) · [`sk_frangi`](https://furuse.work/ops/2d/texture/sk_frangi.html) · [`sk_otsu`](https://furuse.work/ops/2d/segmentation/sk_otsu.html) · [`skeleton`](https://furuse.work/ops/2d/region/skeleton.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html) · [`xsk_meijering`](https://furuse.work/ops/2d/texture/xsk_meijering.html) · [`xsk_sato`](https://furuse.work/ops/2d/texture/xsk_sato.html)

## No.2026.077 —— カメラ指紋(PRNU)で「どのカメラで撮ったか」を当てる ―― 指紋は枚数で育ち、保存ボタンで消える

[![カメラ指紋(PRNU)で「どのカメラで撮ったか」を当てる ―― 指紋は枚数で育ち、保存ボタンで消える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/01_estimators_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/01_estimators.png)

*↑ **カメラ指紋(PRNU)で「どのカメラで撮ったか」を当てる ―― 指紋は枚数で育ち、保存ボタンで消える** ―― 2 台の仮想カメラに固定の感度むら K を仕込み、30 枚の残差から指紋を推定して照合した。清浄条件では同一カメラの PCE 中央値 2192 に対し別カメラ 15.7(AUC 1.000)だが、JPEG 相当の量子化は品質 50 相当で PCE を 3.6 % に、0.5× 縮小は 1.5 % に落とす ―― 消したのは幾何ではなく残差抽出器だった。K=0 のカメラでも同じ背景を 30 枚写せば PCE 1706 の「指紋」ができる。被写体は指紋に化ける。*

[![別カメラのピークは毎回別の位置に立つ((0,0) は 0/30)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/02_match_pce_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/02_match_pce.png)

*↑ 測定の図 ―― 別カメラのピークは毎回別の位置に立つ((0,0) は 0/30)。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/03_n_sweep_corr_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/03_n_sweep_corr.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/05_jpeg_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/05_jpeg_sweep.png)

*↑ この回の図*

[![幾何の上限 = K 自身を同じ往復に通した相関²。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/07_resize_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/07_resize_sweep.png)

*↑ 幾何の上限 = K 自身を同じ往復に通した相関²。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/09_controls_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/09_controls.png)

*↑ この回の図*

```
py -3.11 examples/poc_prnu_camera_fingerprint.py
```

ソース: [examples/poc_prnu_camera_fingerprint.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_prnu_camera_fingerprint.py)

この回が作った図は全部で **10 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint)

使用 op(ノートへ): [`aug_jpeg_blocks`](https://furuse.work/ops/2d/augmentation/aug_jpeg_blocks.html) · [`evidence_quantile`](https://furuse.work/ops/imgforensics/calibration/evidence_quantile.html) · [`fingerprint_correlate`](https://furuse.work/ops/imgforensics/sensor/fingerprint_correlate.html) · [`gauss_image`](https://furuse.work/ops/2d/smoothing/gauss_image.html) · [`median_image`](https://furuse.work/ops/2d/rank/median_image.html) · [`null_distribution`](https://furuse.work/ops/imgforensics/calibration/null_distribution.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`sensor_fingerprint`](https://furuse.work/ops/imgforensics/sensor/sensor_fingerprint.html) · [`sk_nlm`](https://furuse.work/ops/2d/smoothing/sk_nlm.html) · [`sk_tv`](https://furuse.work/ops/2d/smoothing/sk_tv.html) · [`sk_wavelet`](https://furuse.work/ops/2d/smoothing/sk_wavelet.html) · [`xsp_dct_denoise`](https://furuse.work/ops/2d/smoothing/xsp_dct_denoise.html) · [`xsp_wiener`](https://furuse.work/ops/2d/smoothing/xsp_wiener.html)

### 自動運転 ―― 定理と第 2 実装が門になる回(別記事)

この展示先の回は、計測の展示館ではなく**自動運転のシリーズ**に掛かっています。分ける基準は「真値がどこから来るか」です —— 計測の展示は測る対象があり真値は対象の側に、ここの回は車の運動学の定理・閉形式の構造を仮定しない第 2 実装・データセットの公表値から真値が出ます。記事は手書きなので、生成器はここを描きません。

## No.2026.166 —— 車は最短でどう曲がるか ―― Dubins・Reeds–Shepp の閉形式と、占有格子の上の Hybrid A* で縦列駐車

[![車は最短でどう曲がるか ―― Dubins・Reeds–Shepp の閉形式と、占有格子の上の Hybrid A* で縦列駐車](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_car_parking/01_dubins_six_words_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_car_parking/01_dubins_six_words.png)

*↑ **車は最短でどう曲がるか ―― Dubins・Reeds–Shepp の閉形式と、占有格子の上の Hybrid A* で縦列駐車** ―― 前輪で舵を切る車(最小回転半径 ρ)が姿勢 (x, y, θ) から姿勢 (x', y', θ') へ移る最短の道には定理がある。前進だけなら Dubins(1957): 最短路は円弧・直線・円弧の 3 区間で語は 6 つ。後退を許せば Reeds–Shepp(1990): 高々 5 区間で語は 48(Sussmann–Tang 1991 で 46)。どちらも区間長は閉形式で、新しい op car_dubins_path / car_reeds_shepp_path がそれを返す。障害物があれば car_hybrid_astar ―― 占有格子の上で {左・直進・右} × {前進・後退} の運動基本形を離散セル (x, y, θ) で枝刈りしながら A* で繋ぎ、障害物を無視した Reeds–Shepp 長を許容ヒューリスティックに、節点から目標へ解析的な一撃を試す(Dolgov ら 2010)。正しさの担保: 閉形式の各候補は前進積分で終点を検証し、届かない候補は捨てて数を返す ―― 乱数 400 対で落ちた候補 0、対あたりの RS 候補 6.6 本、18 の語族が候補にも最短にも全部現れた。語ごとの区間長を未知数にした終点方程式を SLSQP で多数の初期値から解く第 2 実装(閉形式の構造を仮定しない)は 3 対 × RS / Dubins の 6 件で閉形式と 1e-6 で一致(RS 10.132129 / 6.682896 / 3.322408、Dubins 10.132129 / 8.756928 / 4.552667)。定理の不等式と対称 ―― ユークリッド距離 ≤ RS ≤ Dubins、可逆 L(s, g) = L(g, s)、鏡映、剛体変換で不変、ρ に比例、三角不等式 ―― は 400 対 + 200 組で全部成立し、Dubins − RS の最大は 10.647 m(後退が効く分)。整列した目標では RS = Dubins = 距離、語は S。障害物の無い 40 × 30 m の格子では Hybrid A* の費用 23.353319 m が RS 長 23.353319 m と厳密一致(展開 1、最初の一撃が通る)、前進のみでも Dubins 長と一致。縦列駐車(18 × 8 m、cell 0.25 m、θ 72 分割、車体 4.5 × 1.8 m、ρ 5.5 m、7.5 m の車室)は費用 16.018 m ≥ 下界 7.986 m(障害物を無視した RS の道は駐車車両にぶつかる)、展開 3,385・生成 4,203、区間 42(後退 12・切替 8)、0.8 秒で、返した姿勢列は車体の矩形で衝突せず |Δθ| ≤ Δs/ρ。壁で塞ぐと ValueError(部分的な道は返さない)。合計 16.3 秒。正直に: 6.5 m の車室(車長 + 2.0 m)はこの離散化では到達不能になった。RS の式を写すとき mod2pi の折り方((−π, π] か [0, 2π) か)を間違えると CCSC 系 8 語が一度も候補に出ない ―― 語族を数える門で見つけた。*

[![小文字 = 後退の区間。後退を許すと Dubins より必ず短いか等しい(400 対で確認、最大差 10.647)。ρ = 1 m。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_car_parking/02_reeds_shepp_gallery_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_car_parking/02_reeds_shepp_gallery.png)

*↑ 測定の図 ―― 小文字 = 後退の区間。後退を許すと Dubins より必ず短いか等しい(400 対で確認、最大差 10.647)。ρ = 1 m。*

[![縦列駐車の Hybrid A*: 灰 = 障害物(縁石・駐車車両 2 台・壁)、薄緑の点 = 展開した 4203 姿勢、赤 = 前進、青 = 後退。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_car_parking/03_parking_tree_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_car_parking/03_parking_tree.png)

*↑ 縦列駐車の Hybrid A*: 灰 = 障害物(縁石・駐車車両 2 台・壁)、薄緑の点 = 展開した 4203 姿勢、赤 = 前進、青 = 後退。*

[![RS 最適化器 1 10.1321; Dubins 最適化器 1 10.1321; RS 最適化器 2 6.6829; Dubins 最適化器 2 8.7569; RS 最適化器 3 3.3224; ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_car_parking/05_truths_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_car_parking/05_truths.png)

*↑ RS 最適化器 1 10.1321; Dubins 最適化器 1 10.1321; RS 最適化器 2 6.6829; Dubins 最適化器 2 8.7569; RS 最適化器 3 3.3224; Dubins 最適化器 3 4.5527; 整列 5 m (Dubins) 5.0000; 整列 5…*

[![車(橙)が Hybrid A* の道を辿って 2 台の間に入る。52 コマ、前進 30 区間・後退 12 区間、切替 8 回。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_car_parking/04_parking_gif.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_car_parking/04_parking_gif.gif)

*↑ 動く図 ―― 車(橙)が Hybrid A* の道を辿って 2 台の間に入る。52 コマ、前進 30 区間・後退 12 区間、切替 8 回。*

```
py -3.11 examples/poc_car_parking.py
```

ソース: [examples/poc_car_parking.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_car_parking.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_car_parking)

使用 op(ノートへ): [`arrow`](https://furuse.work/ops/annotate/pointer/arrow.html) · [`car_dubins_path`](https://furuse.work/ops/graph/path/car_dubins_path.html) · [`car_hybrid_astar`](https://furuse.work/ops/graph/path/car_hybrid_astar.html) · [`car_reeds_shepp_path`](https://furuse.work/ops/graph/path/car_reeds_shepp_path.html)

## No.2026.167 —— 教習所が開校する ―― 規格寸法の周回コースに車と信号を置き、LiDAR とカメラで見て、定理と恒等式で採点する

[![教習所が開校する ―― 規格寸法の周回コースに車と信号を置き、LiDAR とカメラで見て、定理と恒等式で採点する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_school/01_course_plan_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_school/01_course_plan.png)

*↑ **教習所が開校する ―― 規格寸法の周回コースに車と信号を置き、LiDAR とカメラで見て、定理と恒等式で採点する** ―― 自動運転のデモは動くので、誰も正しさを測らない。測るには真値を持った世界が要る。道路交通法施行規則 別表第三(普通免許)の寸法どおりに周回コース(長円形、直線 80 m・幅 8 m)を作り、その中に幹線の十字(幅 7 m・信号 4 基)と課題 —— クランク(幅 3.5・曲角間 12・すみ切り 1)、S 字(幅 3.5・外側半径 7.5・弧 3/8 周)、坂道(緩 8 %・急 11 %)、縦列駐車、方向変換、踏切(軌間 1.1 m)—— を置き、出口は連絡路で周回へ戻す(drivecourse、真値は多角形の閉形式の面積)。3-D の世界にして CC0 の車と、日本の規格の寸法で手続き生成した信号機(横型 3 灯、向こう側の柱からアームで車線上)・標識を置き(driveworld / roadjp、面ごとにラベルと色)、回転式 LiDAR をメッシュに撃ち(lidarsim、Möller–Trumbore を方位・仰角のビンで加速、平面と箱の閉形式が第 2 実装)、車載カメラで撮る。門 14: 弧のある要素の面積は点数を増やすと閉形式へ単調収束、平らな路面の range は h/(−sin e) と 1e-9 で一致、LiDAR の点をカメラに投影した画素の深度と点の深度が一致(2 センサ 1 世界の恒等式)、車の LiDAR 点は置いた車の箱の中(100 %)、縁石の点から作った占有格子は真の占有の部分集合、Hybrid A*(13 巡目)の道は全姿勢で隅の越え幅が半セル以内、カメラが信号の赤・緑を読む(消すと読めない)。正直に: 規格の幅 3.5 m は 4.5 × 1.8 m の車に最大舵角と直進だけの運動基本形では前進のみで到達不能で、切り返しを許すと通る。*

[![同じ世界を斜めから: CC0 の車・信号機・標識・コーン(Kenney)を実寸に合わせて置き、縁石(高さ 0.15 m)と白線を多角形の縁に沿って生成(継ぎ目には置かない)。面ごとにラベルと色を持つので、センサの真値は世界の側にある。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_school/02_world_oblique_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_school/02_world_oblique.png)

*↑ 測定の図 ―― 同じ世界を斜めから: CC0 の車・信号機・標識・コーン(Kenney)を実寸に合わせて置き、縁石(高さ 0.15 m)と白線を多角形の縁に沿って生成(継ぎ目には置かない)。面ごとにラベルと色を持つので、センサの真値は世界の側にある。*

[![停止線の 10 m 手前での LiDAR 一掃(32 ビーム・0.5°、13691 点)を面のラベルで塗る: 灰 = 路面、黄 = 縁石、赤 = 車、緑 = 信号機、青 = 標識、橙 = コーン、白 ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_school/03_lidar_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_school/03_lidar_sweep.png)

*↑ 停止線の 10 m 手前での LiDAR 一掃(32 ビーム・0.5°、13691 点)を面のラベルで塗る: 灰 = 路面、黄 = 縁石、赤 = 車、緑 = 信号機、青 = 標識、橙 = コーン、白 = 白線。*

[![同じ瞬間の車載カメラ(60°)に LiDAR の点を投影して重ねる: 点の深度と画素の深度の相対差は中央値 3.00e-03、ラベル一致 100.0 %(1 画素の許容; 門 3、2 センサ 1 世界](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_school/04_camera_with_lidar_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_school/04_camera_with_lidar.png)

*↑ 同じ瞬間の車載カメラ(60°)に LiDAR の点を投影して重ねる: 点の深度と画素の深度の相対差は中央値 3.00e-03、ラベル一致 100.0 %(1 画素の許容; 門 3、2 センサ 1 世界の恒等式)。*

[![真値の散布: 8 種の要素の面積(靴紐 vs 閉形式)と路面の range 200 点(実測 vs h/(−sin e))。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_school/06_truths_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_school/06_truths.png)

*↑ 真値の散布: 8 種の要素の面積(靴紐 vs 閉形式)と路面の range 200 点(実測 vs h/(−sin e))。*

[![幹線で信号を待ち、車載カメラの画像処理(右上の ROI: 地図の信号位置を投影し色度で点灯を検出)が 'green' を読んだ次のコマで発進して交差点を渡り、クランクを抜けて連絡路から周回コースへ合流する(69 コマ、赤で 6 コマ待ち)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_school/05_drive_gif.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_school/05_drive_gif.gif)

*↑ 動く図 ―― 幹線で信号を待ち、車載カメラの画像処理(右上の ROI: 地図の信号位置を投影し色度で点灯を検出)が 'green' を読んだ次のコマで発進して交差点を渡り、クランクを抜けて連絡路から周回コースへ合流する(69 コマ、赤で 6 コマ待ち)。追走カメラの画像に LiDAR(16 ビーム)の点を重ねる。クランクは前進のみでは到達不能で、切り返し 14 回(後退の区間数)。全姿勢で隅の越え幅は半セル以内。*

```
py -3.11 examples/poc_driving_school.py
```

ソース: [examples/poc_driving_school.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_driving_school.py)

この回が作った図は全部で **6 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_driving_school)

使用 op(ノートへ): [`add_sign`](https://furuse.work/ops/drive/roadjp/add_sign.html) · [`ball_detect`](https://furuse.work/ops/drive/balltrack/ball_detect.html) · [`car_dubins_path`](https://furuse.work/ops/graph/path/car_dubins_path.html) · [`car_hybrid_astar`](https://furuse.work/ops/graph/path/car_hybrid_astar.html) · [`course_contains`](https://furuse.work/ops/drive/course/course_contains.html) · [`course_crank`](https://furuse.work/ops/drive/course/course_crank.html) · [`course_crossing`](https://furuse.work/ops/drive/course/course_crossing.html) · [`course_intersection`](https://furuse.work/ops/drive/course/course_intersection.html) · [`course_layout`](https://furuse.work/ops/drive/course/course_layout.html) · [`course_loop`](https://furuse.work/ops/drive/course/course_loop.html) · [`course_loop_bend`](https://furuse.work/ops/drive/course/course_loop_bend.html) · [`course_occupancy`](https://furuse.work/ops/drive/course/course_occupancy.html) · [`course_parallel_parking`](https://furuse.work/ops/drive/course/course_parallel_parking.html) · [`course_road`](https://furuse.work/ops/drive/course/course_road.html) · [`course_s_curve`](https://furuse.work/ops/drive/course/course_s_curve.html) · [`course_slope`](https://furuse.work/ops/drive/course/course_slope.html) · [`course_turnaround`](https://furuse.work/ops/drive/course/course_turnaround.html) · [`intersection`](https://furuse.work/ops/2d/nary/intersection.html) · [`lidar_scan`](https://furuse.work/ops/drive/lidar/lidar_scan.html) · [`lidar_spec`](https://furuse.work/ops/drive/lidar/lidar_spec.html) · [`load_asset`](https://furuse.work/ops/drive/world/load_asset.html) · [`resample`](https://furuse.work/ops/oned/signal/resample.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`world_build`](https://furuse.work/ops/drive/world/world_build.html) …(他 1)

## No.2026.168 —— 衝突までの時間と安全距離 ―― τ 理論の光学流と RSS の閉形式を、教習所の世界の真値で採点する

[![衝突までの時間と安全距離 ―― τ 理論の光学流と RSS の閉形式を、教習所の世界の真値で採点する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ttc_rss/01_scene_plan_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ttc_rss/01_scene_plan.png)

*↑ **衝突までの時間と安全距離 ―― τ 理論の光学流と RSS の閉形式を、教習所の世界の真値で採点する** ―― 対向車が来る。あと何秒でぶつかるか(τ、Lee 1976)は像が広がる速さだけで分かり、何 m 空けるべきかは Mobileye の RSS(Shalev-Shwartz ら 2017)が応答時間と加減速の上限から閉形式で与える。教習所の周回コース(直線 80 m、左側通行)で自車(8 m/s)の対向車線を同じ速さで来る車を車載カメラ(60°、640 × 400、10 Hz)で撮り、τ を 3 経路で出す: 深度像と 2 コマの間の剛体運動から画素ごとの閉形式(真値)、光学流(Lucas–Kanade 5 段)→ time_to_contact(FoE からの半径 / 半径方向の流れ)、見かけの面積の平方根の変化。恒等式: 純並進では真の流れを入れた値は「1 コマ後の τ」で、1 コマ足すと真の τ₀ と 1e-9 で一致(全コマ・全画素)。真の τ は 5 s から 1 秒に 1 秒ずつ減る(傾き −1)。流れからの τ は車が像で 150 画素以上の区間で真値に乗り、遠い区間はサブピクセルの流れで外れる(正直な数字)。RSS は ad-rss-lib の公表パラメータ表(ρ 1/2 s、加速 3.5、制動 4/8/3、横 0.2/0.8、μ 0.1 m)で、横方向の試験値 5 点と ±0.01、50 km/h の同方向で ≈ 40 / ≈ 80 m の公表図と一致。Lemma 2 の閉形式は最悪ケース(先行が急制動、後続は応答時間だけ加速して減速)の時間積分と 1e-6 で一致し、d₀ = d_min でちょうど 0。教習所では、自車線の停車車両に RSS が「危険」を出した瞬間に制動すると停止時の間隔が gap(t_b) − (vρ + v²/2b) と 1e-9 で一致する。対向車線の車は τ が 0.3 s まで落ちても横の安全距離 0.73 m < 車線の間隔 2.2 m で RSS は一度も騒がず、横へ 0.6 m/s で寄ってくると横が危険になり、そのとき縦はもう対向の安全距離 83 m の中で最悪ケースは衝突する —— 責任は寄った側。*

[![t = 4 s の車載カメラ(60°, 640 × 400)。対向車の画素の光学流(Lucas–Kanade 5 段、×3 で描く)は真の FoE(十字)から外へ向かい、その半径方向の速さから τ = 0.84 s(真値 0.86 s)。路](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ttc_rss/02_incar_flow_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ttc_rss/02_incar_flow.png)

*↑ 測定の図 ―― t = 4 s の車載カメラ(60°, 640 × 400)。対向車の画素の光学流(Lucas–Kanade 5 段、×3 で描く)は真の FoE(十字)から外へ向かい、その半径方向の速さから τ = 0.84 s(真値 0.86 s)。路面には模様が無いので流れは車と街灯にしか無い。*

[![対向車の τ(衝突までの時間)の 4 本: 真値は 5 s から 1 秒に 1 秒ずつ減る(傾き −1)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ttc_rss/03_tau_curves_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ttc_rss/03_tau_curves.png)

*↑ 対向車の τ(衝突までの時間)の 4 本: 真値は 5 s から 1 秒に 1 秒ずつ減る(傾き −1)。*

[![場面 A: 停車車両への間隔(青)が RSS の安全距離(橙、v = 8 で 26.28 m)を割った t = 6.0 s に「危険」→ 応答時間 1 s は速度維持、その後 4 m/s² で制動。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ttc_rss/04_rss_same_direction_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ttc_rss/04_rss_same_direction.png)

*↑ 場面 A: 停車車両への間隔(青)が RSS の安全距離(橙、v = 8 で 26.28 m)を割った t = 6.0 s に「危険」→ 応答時間 1 s は速度維持、その後 4 m/s² で制動。*

[![場面 B: 対向車線なら横の間隔 2.2 m > 横の安全距離 0.72 m で、τ が 0.3 s まで落ちても RSS は危険を出さない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ttc_rss/05_rss_lateral_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ttc_rss/05_rss_lateral.png)

*↑ 場面 B: 対向車線なら横の間隔 2.2 m > 横の安全距離 0.72 m で、τ が 0.3 s まで落ちても RSS は危険を出さない。*

[![車載カメラで 0 → 10 s(51 コマ): 対向車が来る間はその画素の光学流(矢印 ×4、長さ 40 px まで)と真の FoE(十字)を描き、τ の真値と流れからの τ を並べる。通り過ぎたあと自車線の停車車両に RSS が「危険」を](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ttc_rss/06_approach_gif.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ttc_rss/06_approach_gif.gif)

*↑ 動く図 ―― 車載カメラで 0 → 10 s(51 コマ): 対向車が来る間はその画素の光学流(矢印 ×4、長さ 40 px まで)と真の FoE(十字)を描き、τ の真値と流れからの τ を並べる。通り過ぎたあと自車線の停車車両に RSS が「危険」を出した瞬間(t = 6.0 s)に制動して 10.25 m 手前で止まる。*

```
py -3.11 examples/poc_ttc_rss.py
```

ソース: [examples/poc_ttc_rss.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ttc_rss.py)

この回が作った図は全部で **6 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_ttc_rss)

使用 op(ノートへ): [`arrow`](https://furuse.work/ops/annotate/pointer/arrow.html) · [`course_layout`](https://furuse.work/ops/drive/course/course_layout.html) · [`course_loop`](https://furuse.work/ops/drive/course/course_loop.html) · [`crosshair`](https://furuse.work/ops/annotate/pointer/crosshair.html) · [`flow_from_depth_motion`](https://furuse.work/ops/drive/ttc/flow_from_depth_motion.html) · [`foe_from_motion`](https://furuse.work/ops/drive/ttc/foe_from_motion.html) · [`label_extent`](https://furuse.work/ops/drive/ttc/label_extent.html) · [`load_asset`](https://furuse.work/ops/drive/world/load_asset.html) · [`relative_motion`](https://furuse.work/ops/drive/ttc/relative_motion.html) · [`rss_lateral`](https://furuse.work/ops/drive/rss/rss_lateral.html) · [`rss_lateral_check`](https://furuse.work/ops/drive/rss/rss_lateral_check.html) · [`rss_longitudinal_check`](https://furuse.work/ops/drive/rss/rss_longitudinal_check.html) · [`rss_longitudinal_opposite`](https://furuse.work/ops/drive/rss/rss_longitudinal_opposite.html) · [`rss_longitudinal_same`](https://furuse.work/ops/drive/rss/rss_longitudinal_same.html) · [`rss_params`](https://furuse.work/ops/drive/rss/rss_params.html) · [`rss_worst_case_gap`](https://furuse.work/ops/drive/rss/rss_worst_case_gap.html) · [`rss_worst_case_gap_opposite`](https://furuse.work/ops/drive/rss/rss_worst_case_gap_opposite.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ttc_from_flow`](https://furuse.work/ops/drive/ttc/ttc_from_flow.html) · [`ttc_from_range`](https://furuse.work/ops/drive/ttc/ttc_from_range.html) · [`ttc_from_scale`](https://furuse.work/ops/drive/ttc/ttc_from_scale.html) · [`ttc_truth`](https://furuse.work/ops/drive/ttc/ttc_truth.html) · [`world_build`](https://furuse.work/ops/drive/world/world_build.html) · [`world_camera`](https://furuse.work/ops/drive/world/world_camera.html) …(他 1)

## No.2026.169 —— 世界を広げる ―― 閉形式の地形と世界座標の材質、手続きの木と歩行者で、拡大の中心を流れから取り戻す

[![世界を広げる ―― 閉形式の地形と世界座標の材質、手続きの木と歩行者で、拡大の中心を流れから取り戻す](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_world_terrain/01_scene_terrain_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_world_terrain/01_scene_terrain.png)

*↑ **世界を広げる ―― 閉形式の地形と世界座標の材質、手続きの木と歩行者で、拡大の中心を流れから取り戻す** ―― 15 巡目の教習所はコースの外 8 m で世界が終わり、路面に模様が無かったので、光学流の拡大の中心(FoE)は「既知」にするしかなかった。この展示は世界を、生成の時に真値を持たせたまま広げる。地形は乱数位相の正弦の和(fBm のスペクトル合成、Saupe 1988)で高さも勾配も閉形式、512 × 512 の周期図の傾きは β̂ = 3.59(定理 2H + 2 = 3.6、H = 0.8)。コースへの距離場は点-線分の閉形式で道の外では |∇d| = 1(eikonal)、道の周り 2 m は平ら、12 m で起伏に繋がり、路面には振幅 0.8 m のうねり。材質は描画した深度から画素の世界座標を戻し、Perlin(2002)の勾配雑音(格子点で 0、周期 256、解析的な導関数)を世界座標で評価する: アスファルトの粒、草、暗い染み、水溜り(写り込みの強さが真値)、摩耗した白線(摩耗率が真値)。車載カメラの路面の画素の高さは閉形式と中央値 0.4 mm、99 % 点 13.0 cm(2 m 升の弦)で一致し、水溜りの画素は全部道の内側、白線の色は摩耗率の混色 × 陰影と 0 で一致。木 70 本(角柱 + 円錐 / 回転楕円体、針葉樹の体積は発散定理のメッシュ体積と 1e-9、広葉樹の冠は内接で上界の 0.88 倍)は道から 4 m 以上・互いに 5 m 以上に散布、横断歩道 9 縞 = 16.2 m²、歩行者(箱 + 回転体)が横断歩道を渡る。自車が坂を上り下りする 10 秒(30 fps の 2 コマずつ)で、真の流れからの FoE は foe_from_motion と 6e-14 px(純並進の流れは FoE から放射状)。路面の画素の Lucas–Kanade の流れだけから最小二乗(流線と点の距離、角度の残差で重み)で出した FoE は模様ありで中央値 1.9 px(全画素 1.2 px)、同じ地形で路面だけ無地にすると 57 px。正直に: 摩耗した白線と水溜りは明るさのしきい値では向きを選んでも最良で 25 % を間違える —— それが「判りにくい物」の狙いで、真値は画素単位で厳密。木・歩行者は箱と回転体、水溜りの写り込みは空の色を混ぜただけ。*

[![fBm の面(H = 0.8)の動径周期図は log–log で直線: 傾き β̂ = 3.59、定理(Saupe 1988: β = 2H + E、E = 2)は 3.6。帯域 [1/100, 1/10) 周期/m の 12 帯で当てはめ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_world_terrain/02_terrain_spectrum_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_world_terrain/02_terrain_spectrum.png)

*↑ 測定の図 ―― fBm の面(H = 0.8)の動径周期図は log–log で直線: 傾き β̂ = 3.59、定理(Saupe 1988: β = 2H + E、E = 2)は 3.6。帯域 [1/100, 1/10] 周期/m の 12 帯で当てはめ。有限の帯域と Hann 窓で +0.1 ほど急に出る。*

[![車載カメラ(60°, 640 × 400)の 1 コマと、その画素ごとの真値。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_world_terrain/03_incar_materials_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_world_terrain/03_incar_materials.png)

*↑ 車載カメラ(60°, 640 × 400)の 1 コマと、その画素ごとの真値。*

[![t = 1.2 s(誤差が中央値に最も近い典型的なコマ)の車載カメラ(480 × 300、30 fps の 2 コマ)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_world_terrain/04_foe_from_flow_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_world_terrain/04_foe_from_flow.png)

*↑ t = 1.2 s(誤差が中央値に最も近い典型的なコマ)の車載カメラ(480 × 300、30 fps の 2 コマ)。*

[![拡大の中心の推定誤差(真値との距離)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_world_terrain/05_foe_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_world_terrain/05_foe_error.png)

*↑ 拡大の中心の推定誤差(真値との距離)。*

[![車載カメラで 0 → 10 s(51 コマ、6 m/s): 起伏の中の周回コースを坂を上り下りしながら走る。矢印は LK の流れ(×4)、橙の十字は流れから推定した拡大の中心、緑は真値。横断歩道を歩行者が渡り、路面には水溜りと摩耗した白線。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_world_terrain/06_drive_gif.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_world_terrain/06_drive_gif.gif)

*↑ 動く図 ―― 車載カメラで 0 → 10 s(51 コマ、6 m/s): 起伏の中の周回コースを坂を上り下りしながら走る。矢印は LK の流れ(×4)、橙の十字は流れから推定した拡大の中心、緑は真値。横断歩道を歩行者が渡り、路面には水溜りと摩耗した白線。*

```
py -3.11 examples/poc_world_terrain.py
```

ソース: [examples/poc_world_terrain.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_world_terrain.py)

この回が作った図は全部で **6 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_world_terrain)

使用 op(ノートへ): [`add_mesh_object`](https://furuse.work/ops/drive/terrain/add_mesh_object.html) · [`add_sign`](https://furuse.work/ops/drive/roadjp/add_sign.html) · [`course_contains`](https://furuse.work/ops/drive/course/course_contains.html) · [`course_distance`](https://furuse.work/ops/drive/terrain/course_distance.html) · [`course_layout`](https://furuse.work/ops/drive/course/course_layout.html) · [`course_loop`](https://furuse.work/ops/drive/course/course_loop.html) · [`crosshair`](https://furuse.work/ops/annotate/pointer/crosshair.html) · [`crosswalk_mesh`](https://furuse.work/ops/drive/terrain/crosswalk_mesh.html) · [`fbm_gradient`](https://furuse.work/ops/drive/terrain/fbm_gradient.html) · [`fbm_height`](https://furuse.work/ops/drive/terrain/fbm_height.html) · [`flow_from_depth_motion`](https://furuse.work/ops/drive/ttc/flow_from_depth_motion.html) · [`foe_from_flow`](https://furuse.work/ops/drive/ttc/foe_from_flow.html) · [`foe_from_motion`](https://furuse.work/ops/drive/ttc/foe_from_motion.html) · [`material_params`](https://furuse.work/ops/drive/terrain/material_params.html) · [`mesh_signed_volume`](https://furuse.work/ops/drive/terrain/mesh_signed_volume.html) · [`pedestrian_mesh`](https://furuse.work/ops/drive/terrain/pedestrian_mesh.html) · [`perlin2`](https://furuse.work/ops/drive/terrain/perlin2.html) · [`radial_periodogram`](https://furuse.work/ops/drive/terrain/radial_periodogram.html) · [`relative_motion`](https://furuse.work/ops/drive/ttc/relative_motion.html) · [`scatter_offroad`](https://furuse.work/ops/drive/terrain/scatter_offroad.html) · [`spectral_slope`](https://furuse.work/ops/drive/terrain/spectral_slope.html) · [`terrain_gradient`](https://furuse.work/ops/drive/terrain/terrain_gradient.html) · [`terrain_height`](https://furuse.work/ops/drive/terrain/terrain_height.html) · [`terrain_params`](https://furuse.work/ops/drive/terrain/terrain_params.html) …(他 7)

## No.2026.172 —— 車に慣性と坂を ―― 空走 + 制動で停止線の手前に止まり、坂道で止まって逆行せずに発進する

[![車に慣性と坂を ―― 空走 + 制動で停止線の手前に止まり、坂道で止まって逆行せずに発進する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_longitudinal/01_drive_with_time.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_longitudinal/01_drive_with_time.gif)

*↑ **車に慣性と坂を ―― 空走 + 制動で停止線の手前に止まり、坂道で止まって逆行せずに発進する** ―― これまでの教習所の車は、2.5 m おきの姿勢の列で動き、停止線でいきなり止まっていた —— 時間も速さも無かった(ユーザー「車に慣性の法則。速度に対する制動にかかる距離は反映されてる? 坂道はある?」)。この展示は車に縦の運動を入れる: m dv/dt = 駆動 − 制動 − m g sin θ − c_rr m g cos θ − ½ρC_dA v|v|、止まっている間はブレーキで保持できる範囲なら動かない。真値は 3 つ。停止距離の閉形式 vρ + (1/2k)ln(1 + k v²/A)(A = b ± g sin θ + c_rr g cos θ、空気抵抗が無ければ v²/2A)と積分器が平地・上り・下り × 20/40/60 km/h の 15 組で 8.5e-14、平地では別に書いた rsssafety の停止距離と 5.5e-13。坂道発進のずり下がり½a₁τ² + (a₁τ)²/(2a₂)(ブレーキを離してから駆動が立ち上がるまでの τ)と 1.8e-15。エネルギー収支(½v² + g z + 転がり・空気・制動の仕事 − 駆動の仕事)が全区間で 1.2e-9 J/kg。閉ループ: 車載カメラで信号の色を読み(読みを信じる 20 m の中で 117 / 117 一致)、黄を読んでから反応時間の空走 + 2 段の制動(通達の「ブレーキを数回に分けて踏まない場合」の減点に合わせた)で停止線の手前 0.500 m に止まり、赤の間は 1 mm も動かず、青を読んでから発進。坂道コース(8 % の上り)の一時停止と発進は逆行 0 m、11 % の下りは 15 km/h 以下。警察庁 丙運発第 12 号(令和 4 年)の減点細目で採点すると減点 0・100 点。つまみは閉形式のしきい値で読む: 反応時間 2.546 s を越えると線を越えて停止位置不適、路面の μ が 0.1134 を割ると止まれない(雨はこの μ に入る = 次の回)、踏み替えに 1 s かかる下手な発進は勾配 9 % で逆行小・10〜11 % で逆行中・12.5 % 以上で逆行大(試験中止)。灯火を消すと 'unknown' のまま止まって発進しない(fail-closed)。正直に: 逆行の距離(小 0.3・中 0.5・大 1 m)と「停止線の 2 m 以上手前は不適」は通達に数字が無く二次情報、質量 1300 kg・制動の上限・反応 0.75 s などは仮定、停止の計画は知覚した瞬間に決めて途中で測り直さない(世界とモデルが同じなのでぴったり止まる)、坂道の縁石が地面の高さに描かれる(driveworld の課題)。14 門、28.0 s。*

[![速さ・路面の高さ・ブレーキの時系列。交差点では反応(空走)の間は速さを保ち、2 段で止まる(制動の 2 つの段)。赤の間は 0、青を読んで発進。坂で一時停止して発進し、急な下りでは制動で速さを保つ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_longitudinal/02_speed_distance_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_longitudinal/02_speed_distance.png)

*↑ 測定の図 ―― 速さ・路面の高さ・ブレーキの時系列。交差点では反応(空走)の間は速さを保ち、2 段で止まる(制動の 2 つの段)。赤の間は 0、青を読んで発進。坂で一時停止して発進し、急な下りでは制動で速さを保つ。*

[![停止距離 = 空走 vρ + 制動距離(制動 4 m/s²、反応 0.75 s)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_longitudinal/03_stopping_distance_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_longitudinal/03_stopping_distance.png)

*↑ 停止距離 = 空走 vρ + 制動距離(制動 4 m/s²、反応 0.75 s)。*

[![つまみ = 反応時間: 同じ場所で黄を読んでも、反応が遅いと空走が延び、閉形式のしきい値 ρ* = 2.55 s を越えると上限のブレーキでも停止線を越える(停止位置不適 / 信号無視)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_longitudinal/04_knob_reaction_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_longitudinal/04_knob_reaction.png)

*↑ つまみ = 反応時間: 同じ場所で黄を読んでも、反応が遅いと空走が延び、閉形式のしきい値 ρ* = 2.55 s を越えると上限のブレーキでも停止線を越える(停止位置不適 / 信号無視)。*

[![つまみ = 勾配: ブレーキを離してからアクセルまで 1.0 s かかる下手な坂道発進のずり下がり。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_longitudinal/05_knob_grade_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_longitudinal/05_knob_grade.png)

*↑ つまみ = 勾配: ブレーキを離してからアクセルまで 1.0 s かかる下手な坂道発進のずり下がり。*

```
py -3.11 examples/poc_driving_longitudinal.py
```

ソース: [examples/poc_driving_longitudinal.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_driving_longitudinal.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_driving_longitudinal)

使用 op(ノートへ): [`ball_detect`](https://furuse.work/ops/drive/balltrack/ball_detect.html) · [`course_intersection`](https://furuse.work/ops/drive/course/course_intersection.html) · [`course_layout`](https://furuse.work/ops/drive/course/course_layout.html) · [`course_road`](https://furuse.work/ops/drive/course/course_road.html) · [`course_slope`](https://furuse.work/ops/drive/course/course_slope.html) · [`hill_hold_brake_min`](https://furuse.work/ops/drive/long/hill_hold_brake_min.html) · [`hill_start_command`](https://furuse.work/ops/drive/long/hill_start_command.html) · [`hill_start_rollback`](https://furuse.work/ops/drive/long/hill_start_rollback.html) · [`load_asset`](https://furuse.work/ops/drive/world/load_asset.html) · [`long_energy_residual`](https://furuse.work/ops/drive/long/long_energy_residual.html) · [`long_params`](https://furuse.work/ops/drive/long/long_params.html) · [`long_simulate`](https://furuse.work/ops/drive/long/long_simulate.html) · [`plan_command`](https://furuse.work/ops/drive/long/plan_command.html) · [`road_eval`](https://furuse.work/ops/drive/long/road_eval.html) · [`road_profile`](https://furuse.work/ops/drive/long/road_profile.html) · [`rss_stopping_distance`](https://furuse.work/ops/drive/rss/rss_stopping_distance.html) · [`skill_test_score`](https://furuse.work/ops/drive/long/skill_test_score.html) · [`stop_line_plan`](https://furuse.work/ops/drive/long/stop_line_plan.html) · [`stopping_distance_grade`](https://furuse.work/ops/drive/long/stopping_distance_grade.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`world_build`](https://furuse.work/ops/drive/world/world_build.html) · [`world_camera`](https://furuse.work/ops/drive/world/world_camera.html)

## No.2026.173 —— 太陽と天気 ―― 朝日の逆光で信号が読めない時間帯、霧の中で見えてから止まれる速さ、雨の路面、夜の前照灯

[![太陽と天気 ―― 朝日の逆光で信号が読めない時間帯、霧の中で見えてから止まれる速さ、雨の路面、夜の前照灯](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_weather/04_fog_views_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_weather/04_fog_views.png)

*↑ **太陽と天気 ―― 朝日の逆光で信号が読めない時間帯、霧の中で見えてから止まれる速さ、雨の路面、夜の前照灯** ―― 自動運転は太陽光や天候の中を走る(ユーザー「太陽光や天候も再現できるといいね」)。この展示は教習所の世界を物理の単位(輝度 cd/m²・照度 lx)で照らし直し、車載カメラの画像処理(色度で灯火を読む)が **どこで読めなくなるかを画素の式から先に閉形式で出し**、描いた画像の読みがその両側で変わることを確かめる。太陽: 日時と緯度経度から高度・方位(NOAA の式)。国立天文台 暦計算室の東京 2026 年(春分・夏至・秋分・冬至)の日の出・南中・日の入りの時刻・方位・高度 24 値が丸めの単位(1 分・0.1°)で一致。影の先端は h cot(高度) と 1 画素以内(4 つの高度)。逆光: 光幕 L_v = 10E/θ²(Stiles–Holladay)は白いので、灯火の色度を灰色へ寄せる。色度が検出の許容を割る白の量 W* から閾値 θ* = √(10E/W*) を出すと、3 色 × 太陽の角の掃引で「読めた / 読めない」が予測と食い違い 0。春分の朝、東へ向かう車から赤が読めないのは 05:53〜07:05(太陽の式で出し、描いて確認)。霧: Koschmieder の法則。路面の縦の輝度の曲線に当てはめて視程を画像から戻す(視程 30〜200 m で誤差 0.96 %、雑音 1 %)。灯火の色が読める距離は ln(1 + W*/L_h)/β(L_h = 画像の空から測った大気光)で、画像の読みと掃引の 1 刻み以内。視程 200 m では赤が読めるのは停止線の 6.6 m 手前から → 止まれる速さ 17.5 km/h(停止距離の閉形式を v について解く)。その 0.9 倍では停止線の手前に止まり、1.25 倍では越える(閉ループ)。雨: 道路構造令の解説の停止距離の式 D = 0.694V + 0.00394V²/f と前の回の閉形式が一致(第 2 実装)、湿潤の f で停止距離が延び、路面に映った赤は地図の ROI の外なので読みを乱さない。夜: 仮定した配光で、すれ違い灯は 60 m・走行灯は 120 m の歩行者を画像で見つけ(保安基準の 40 m・100 m の性能)、見つけてから止まれる速さの上下で止まる / 止まれない。灯火を消すとどの天気でも 'unknown'(fail-closed)。正直に: 空と薄明の明るさ・灯火の輝度・前照灯の配光・HDR カメラの階調は仮定、光幕は人の目の散乱の式でカメラのレンズを代用、霧は描画と同じ一様なKoschmieder の世界で測っている、雨筋と鏡像のぼけは見た目だけ。13 門、134.9 s。*

[![春分(2026-03-20)の東京、朝 5:15 から夜 20:15 まで 15 分おき。左 = 東へ向かう車の車載カメラ(停止線の 15 m 手前)と信号の読み、右 = 斜め上から(影が太陽と反対へ伸び、短くなってまた伸びる)。朝、太陽が](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_weather/01_sun_day.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_weather/01_sun_day.gif)

*↑ 測定の図 ―― 春分(2026-03-20)の東京、朝 5:15 から夜 20:15 まで 15 分おき。左 = 東へ向かう車の車載カメラ(停止線の 15 m 手前)と信号の読み、右 = 斜め上から(影が太陽と反対へ伸び、短くなってまた伸びる)。朝、太陽が信号の後ろの低い空にある間は光幕で赤の色度が灰色へ寄り、画像処理は「読めない」(05:53〜07:05)。日が沈むと前照灯を点ける。*

[![東京の太陽の高度(NOAA の式、大気差つき)と国立天文台 暦計算室の公表値(点: 日の出・日の入りは高度 0、南中は高度)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_weather/02_sun_elevation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_weather/02_sun_elevation.png)

*↑ 東京の太陽の高度(NOAA の式、大気差つき)と国立天文台 暦計算室の公表値(点: 日の出・日の入りは高度 0、南中は高度)。*

[![逆光: 横 = 太陽と灯火への視線の角 θ、縦 = 画素の式から先に出した閾値 θ* = √(10 E_dn / W*)(高度で変わる)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_weather/03_backlight_threshold_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_weather/03_backlight_threshold.png)

*↑ 逆光: 横 = 太陽と灯火への視線の角 θ、縦 = 画素の式から先に出した閾値 θ* = √(10 E_dn / W*)(高度で変わる)。*

[![霧の濃さを画像から測る: 車線の中の路面の輝度を行ごとに並べると(点、雑音 1 %)、遠い行ほど大気光へ近づく。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_weather/05_fog_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_weather/05_fog_profile.png)

*↑ 霧の濃さを画像から測る: 車線の中の路面の輝度を行ごとに並べると(点、雑音 1 %)、遠い行ほど大気光へ近づく。*

[![霧の中で灯火の色が読める距離: 閉形式 d* = ln(1 + W*/L_h)/β(線)と、描いた画像で読めた距離(点)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_weather/06_fog_reach_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_weather/06_fog_reach.png)

*↑ 霧の中で灯火の色が読める距離: 閉形式 d* = ln(1 + W*/L_h)/β(線)と、描いた画像で読めた距離(点)。*

```
py -3.11 examples/poc_driving_weather.py
```

ソース: [examples/poc_driving_weather.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_driving_weather.py)

この回が作った図は全部で **7 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_driving_weather)

使用 op(ノートへ): [`ball_detect`](https://furuse.work/ops/drive/balltrack/ball_detect.html) · [`beta_from_mor`](https://furuse.work/ops/drive/env/beta_from_mor.html) · [`course_intersection`](https://furuse.work/ops/drive/course/course_intersection.html) · [`course_layout`](https://furuse.work/ops/drive/course/course_layout.html) · [`course_road`](https://furuse.work/ops/drive/course/course_road.html) · [`env_params`](https://furuse.work/ops/drive/env/env_params.html) · [`env_render`](https://furuse.work/ops/drive/env/env_render.html) · [`fog_beta_from_profile`](https://furuse.work/ops/drive/env/fog_beta_from_profile.html) · [`load_asset`](https://furuse.work/ops/drive/world/load_asset.html) · [`long_params`](https://furuse.work/ops/drive/long/long_params.html) · [`long_simulate`](https://furuse.work/ops/drive/long/long_simulate.html) · [`pedestrian_mesh`](https://furuse.work/ops/drive/terrain/pedestrian_mesh.html) · [`plan_command`](https://furuse.work/ops/drive/long/plan_command.html) · [`road_row_distance`](https://furuse.work/ops/drive/env/road_row_distance.html) · [`sight_stop_speed`](https://furuse.work/ops/drive/env/sight_stop_speed.html) · [`skill_test_score`](https://furuse.work/ops/drive/long/skill_test_score.html) · [`stop_line_plan`](https://furuse.work/ops/drive/long/stop_line_plan.html) · [`stopping_distance_grade`](https://furuse.work/ops/drive/long/stopping_distance_grade.html) · [`sun_at`](https://furuse.work/ops/drive/env/sun_at.html) · [`sun_events`](https://furuse.work/ops/drive/env/sun_events.html) · [`sun_illuminance`](https://furuse.work/ops/drive/env/sun_illuminance.html) · [`sun_vector`](https://furuse.work/ops/drive/env/sun_vector.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`veil_chroma_limit`](https://furuse.work/ops/drive/env/veil_chroma_limit.html) …(他 1)

## No.2026.176 —— 終わらない地図 ―― 区画を車の周りに作り足し、離れた区画は捨てて、50 km を途切れずに走る

[![終わらない地図 ―― 区画を車の周りに作り足し、離れた区画は捨てて、50 km を途切れずに走る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_endless_map/01_minimap_stream.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_endless_map/01_minimap_stream.gif)

*↑ **終わらない地図 ―― 区画を車の周りに作り足し、離れた区画は捨てて、50 km を途切れずに走る** ―― 著者の発案 ——「マップが前後左右方向にエンドレスに作られていき、一定以上離れたマップは自動に消えていく形にすれば、もっと長距離の連続走行のテストもできるのではないか」。世界を一辺 200 m の区画 (i, j) に分け、**区画の中身を区画の番号と世界の種だけで決める**(SplitMix64 のハッシュ、乱数の状態を持ち越さない)。道は区画の辺ごとに「横切るか・どこで横切るか」を**辺の番号のハッシュ**で決めるので、両側の区画が同じ値を読み、継ぎ目で必ずつながる。起伏は全体で共通の整数格子(区画の番号 × 升目数 + 升目の番号)の Perlin を区画の中の小数だけで補間するので、継ぎ目で連続し遠くでも桁が落ちない。位置は (区画, 区画の中の座標) で持ち、描くときも車の区画を原点にする(浮動原点)。車の周り 5 × 5 区画だけを持ち、1,000 km 先の区画から東寄りに 50 km 走る。門: 継ぎ目(区画の組 300、番号 ±10⁶ まで)の高さの差 3.3e-15 m・道の横切り位置はビット一致 / 作る順に依らない / 捨ててから作り直した 214 区画の指紋(SHA-256)が最初と一致 / 持つ区画は最大 25 / 車は道の中心線から外れない / 区画の中の座標は 50 km 後も誤差 2e-11 m、全体の座標を float32 で持つと 33.42 m ずれる(1,000 km 先の float32 の刻みは 62.5 mm)。見つけたこと: 道の周りを平らにする範囲が狭いと、地面の格子の三角形が道より上に出て道が埋もれる(道幅の半分 + 格子の対角 ≈ 18 m にした)。描画器は頂点が 1 つでもカメラの後ろにある三角形を捨てるので、100 m 級の道の帯は丸ごと消えた(格子の刻みで切る)。正直に: 道は分岐点と辺を結ぶ直線の折れ線、建物・交通・標識は無い、起伏は Perlin だけ。6 門、26.2 s。*

[![追従カメラ(赤 = 車、25 m ごと、最初の 3 km)。持っている 25 区画だけを、車のいる区画の原点に合わせて描く(浮動原点)—— 1,000 km 先でも頂点の座標は ±600 m に収まる。区画の継ぎ目で道と地面は途切れない。描](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_endless_map/02_dashcam.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_endless_map/02_dashcam.gif)

*↑ 測定の図 ―― 追従カメラ(赤 = 車、25 m ごと、最初の 3 km)。持っている 25 区画だけを、車のいる区画の原点に合わせて描く(浮動原点)—— 1,000 km 先でも頂点の座標は ±600 m に収まる。区画の継ぎ目で道と地面は途切れない。描画器はカメラの後ろに頂点がある三角形を捨てるので、足元の穴は地面の色で埋めている(見た目だけ)。*

[![東寄りに道の網をたどった経路。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_endless_map/03_route_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_endless_map/03_route.png)

*↑ 東寄りに道の網をたどった経路。*

```
py -3.11 examples/poc_driving_endless_map.py
```

ソース: [examples/poc_driving_endless_map.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_driving_endless_map.py)

この回が作った図は全部で **3 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_driving_endless_map)

使用 op(ノートへ): [`pose_normalize`](https://furuse.work/ops/drive/inf/pose_normalize.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`tile_digest`](https://furuse.work/ops/drive/inf/tile_digest.html) · [`tile_edge_crossing`](https://furuse.work/ops/drive/inf/tile_edge_crossing.html) · [`tile_height`](https://furuse.work/ops/drive/inf/tile_height.html) · [`tile_mesh`](https://furuse.work/ops/drive/inf/tile_mesh.html) · [`tile_params`](https://furuse.work/ops/drive/inf/tile_params.html) · [`tile_road_distance`](https://furuse.work/ops/drive/inf/tile_road_distance.html) · [`tile_roads`](https://furuse.work/ops/drive/inf/tile_roads.html) · [`tile_stream`](https://furuse.work/ops/drive/inf/tile_stream.html) · [`world_camera`](https://furuse.work/ops/drive/world/world_camera.html)

## No.2026.179 —— 動く交通と死角 ―― 路肩駐車の陰の子ども、対向車とのすれ違い、バス停、下手な運転、横断歩道で待つ人

[![動く交通と死角 ―― 路肩駐車の陰の子ども、対向車とのすれ違い、バス停、下手な運転、横断歩道で待つ人](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_traffic/01_dashcam_occlusion.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_traffic/01_dashcam_occlusion.gif)

*↑ **動く交通と死角 ―― 路肩駐車の陰の子ども、対向車とのすれ違い、バス停、下手な運転、横断歩道で待つ人** ―― 著者の発案 ——「歩行者とか外乱要素がまだまだ足りない」「自転車とかも道路上では走ってるよ」「路肩駐車してる車もいる」「下手くそな運転してる奴もいる」「頻度は多くないけど、飛び出す奴や横切る奴もいる」「路肩駐車のある場合、対向車とのすれ違いのタイミングを考えないといけない」「バス停車中は人の乗り降りが多く、飛び出してくる人がいやすいので、追い越しは注意がいる。出来れば発車まで待つほうが良い」「歩道で待つ人がいれば一時停止」、そして「自動車の教本に書かれている内容を読み返し、その中にある要素を再現するべき」。国家公安委員会告示「交通の方法に関する教則」から運転者の場面を 159 拾い、再現の状態を付けた台帳(docs/drive/kyosoku_scenarios.json、再現 8・一部 11・再現不能 7 は理由つき・未着手 133)を作り、台帳と PoC が互いに名指しし合う門を置いた。新モジュール drivetraffic 18 op。門: 路肩駐車の陰の見え始めは箱の角をかすめる視線の閉形式 = 目を 2 mm ずつ進めた視線判定、止まれる最大速度 10.7 km/h なら 445 試行の全部で子どもの手前に止まり 1.3 倍では止まれない試行が出る / 歩道の子は「見え → 隠れ → 見える」/ すれ違いの境目は閉形式 = PET 1 s の二分法(相対 1.6e-9)、対向 600 台/時の平均の待ち 9.0 s = Adams の式 / バス停は発車まで待つ < 徐行 < そのまま(期待件数の閉形式 = 時空のポアソン過程の MC)/ IDM の車列は慎重・普通が平衡車間に収束し、反応が車間時間より長い荒い運転は t = 10.8 s に追突 / 横ふらつきを OU の最尤で読むと荒い運転 17 / 17・誤検出 0(位置のばらつきでは 13 / 17)/ 横断歩道で渡る人の見逃し 0 / 稀な飛び出しの件数の平均 = 分散 = ∫λ、重要度サンプリングは閉形式と素朴な MC に一致し分散 1/25.7 / 自転車の側方 1.5 m(PoC が決めた値)を全試行で保つ / 背景差分の検知は真値から 0.133 s 遅れ・それより前の誤検知 0 / 通し走行 335 m で接触なし。見つけたこと: 位置のばらつきでは荒い運転を 4 台に 1 台逃す、2D の視線は 3D の描画より 0.5 s 遅い(安全側)、IDM の止まった車列は s0 ちょうどにならない、徐行ではみ出すと待ちが 9.0 → 19.3 s に倍増。正直に: 癖・歩く速さ 1.2 m/s・側方間隔は仮定、死角は 2D。20 門、68 s。*

[![俯瞰(通し走行 86 s・335 m): 自車(青)は路肩駐車の死角の手前で 10.7 km/h に落とし、対向の車列(橙 = 荒い運転、横にふらつく)が過ぎて隙間 D* が空くまで待ってからはみ出す。陰から走り出た子ども(黄)に止まり、渡](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_traffic/02_overhead_street.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_traffic/02_overhead_street.gif)

*↑ 測定の図 ―― 俯瞰(通し走行 86 s・335 m): 自車(青)は路肩駐車の死角の手前で 10.7 km/h に落とし、対向の車列(橙 = 荒い運転、横にふらつく)が過ぎて隙間 D* が空くまで待ってからはみ出す。陰から走り出た子ども(黄)に止まり、渡り切ってから発進。脇道から出た自転車(紫)の後ろにつき、対向車が過ぎたら側方 1.5 m + 追い越しの間にふらつける幅 4.5 σ̂ √h を空けて追い越す。停車中のバス(緑)の前を乗客(赤)が渡るので追い越さずに発車まで待つ。紫の影は自車の目から見えない所。最小の距離: 子ども 3.07 m・自転車 2.87 m・対向車 0.78 m。*

[![時空図(縦 = 先頭車からの位置、横 = 時刻、線 = 6 台)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_traffic/03_platoon_spacetime_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_traffic/03_platoon_spacetime.png)

*↑ 時空図(縦 = 先頭車からの位置、横 = 時刻、線 = 6 台)。*

[![横断の意図の混同行列(480 人、判断の時刻は乱数、位置の雑音 5 cm・向き 10°)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_traffic/04_intent_confusion_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_traffic/04_intent_confusion.png)

*↑ 横断の意図の混同行列(480 人、判断の時刻は乱数、位置の雑音 5 cm・向き 10°)。*

[![対向車がポアソン流のとき、はみ出しに要る隙間 τ = D*/v_on を待つ平均時間(Adams の式)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_traffic/06_passing_wait_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_traffic/06_passing_wait.png)

*↑ 対向車がポアソン流のとき、はみ出しに要る隙間 τ = D*/v_on を待つ平均時間(Adams の式)。*

[![停車中のバスの前後で出現率が高い(bus_stop_rate)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_traffic/07_bus_stop_risk_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_traffic/07_bus_stop_risk.png)

*↑ 停車中のバスの前後で出現率が高い(bus_stop_rate)。*

```
py -3.11 examples/poc_driving_traffic.py
```

ソース: [examples/poc_driving_traffic.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_driving_traffic.py)

この回が作った図は全部で **8 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_driving_traffic)

使用 op(ノートへ): [`add_mesh_object`](https://furuse.work/ops/drive/terrain/add_mesh_object.html) · [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`bus_stop_rate`](https://furuse.work/ops/drive/traffic/bus_stop_rate.html) · [`driver_style`](https://furuse.work/ops/drive/traffic/driver_style.html) · [`grid_lines`](https://furuse.work/ops/annotate/plot/grid_lines.html) · [`idm_accel`](https://furuse.work/ops/drive/traffic/idm_accel.html) · [`idm_equilibrium_gap`](https://furuse.work/ops/drive/traffic/idm_equilibrium_gap.html) · [`idm_platoon_simulate`](https://furuse.work/ops/drive/traffic/idm_platoon_simulate.html) · [`importance_risk_estimate`](https://furuse.work/ops/drive/traffic/importance_risk_estimate.html) · [`lateral_wobble`](https://furuse.work/ops/drive/traffic/lateral_wobble.html) · [`long_params`](https://furuse.work/ops/drive/long/long_params.html) · [`long_simulate`](https://furuse.work/ops/drive/long/long_simulate.html) · [`nice_ticks`](https://furuse.work/ops/annotate/plot/nice_ticks.html) · [`occlusion_reveal_distance`](https://furuse.work/ops/drive/traffic/occlusion_reveal_distance.html) · [`occlusion_safe_speed`](https://furuse.work/ops/drive/traffic/occlusion_safe_speed.html) · [`occlusion_visible_intervals`](https://furuse.work/ops/drive/traffic/occlusion_visible_intervals.html) · [`ou_estimate`](https://furuse.work/ops/drive/traffic/ou_estimate.html) · [`passing_decision`](https://furuse.work/ops/drive/traffic/passing_decision.html) · [`passing_gap_required`](https://furuse.work/ops/drive/traffic/passing_gap_required.html) · [`passing_simulate`](https://furuse.work/ops/drive/traffic/passing_simulate.html) · [`pedestrian_crossing`](https://furuse.work/ops/drive/traffic/pedestrian_crossing.html) · [`pedestrian_mesh`](https://furuse.work/ops/drive/terrain/pedestrian_mesh.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) …(他 5)

## No.2026.180 —— 判断の場面 ―― ミラーで左後方を確かめる、歩行者信号から黄を予測する、救急車に道を譲る、バスの発車を待つ

[![判断の場面 ―― ミラーで左後方を確かめる、歩行者信号から黄を予測する、救急車に道を譲る、バスの発車を待つ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_decisions/01_decisions_mirrors_ambulance.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_decisions/01_decisions_mirrors_ambulance.gif)

*↑ **判断の場面 ―― ミラーで左後方を確かめる、歩行者信号から黄を予測する、救急車に道を譲る、バスの発車を待つ** ―― 著者の発案 ——「信号は歩行者信号の動きを見て予測も必要」「ミラーの確認もいる」「救急車が来た時もちゃんとしないといけない」「バス停車中は……出来れば発車まで待つほうが良い」。前の回の教則の再現台帳から、合図の時期・緊急自動車・黄信号・バスの発進の場面を拾った。新モジュール drivedecide 18 op。門: ミラーを鏡の向こうの仮想カメラで描いた目印の位置 = 鏡面上の Fermat の点の光線追跡(12 点で最大 0.50 px、左右反転を外すと中央値 228 px ずれる)/ 凸面ドアミラーの死角の多角形 = 柱 295 点の描画と不一致 0、凸面 R 1.4 m で同じ幅の平面鏡の 37.1 m² が 20.4 m² に / 左折の前にミラーで左後方の自転車を確かめると 400 試行の全部で巻き込まない(最小 1.08 m)、直接の視界だけだと 68 試行で巻き込む / 確認の順序(ミラー → 合図 約 3 秒前・30 m 手前 → 進路変更 → 合図をやめる)を丁運発第44号の点数で採点、自車は減点 0・崩した 6 版はそれぞれの点数 / 200 m 先の歩行者信号の点灯を画素から読んで全コマ一致、黄の予測区間は全部で真値を含む / 600 試行で予測ありは黄の瞬間にジレンマゾーンに 0 回、予測なしは GHM の読みで 48 回(停止線の読みで 10)/ サイレンの近づく・遠ざかるは距離の変化率の符号と 99.89 % 一致、到着時間差の方位は幾何と最大 0.11° / 赤色灯の点滅は 3.75 fps で 1.25 Hz に折り返す / 救急車に交差点の手前で左に寄って一時停止(40 条 1 項)、寄らない版と交差点の中で止まる版は違反 / バスは発車まで待つ(最小間隔 3.18 m)、40 m 手前で要る減速 2.2957 m/s² = 刻み 0.1 ms のブレーキ + 二分法。見つけたこと: ジレンマゾーンは GHM と停止線の読みで形が変わる(停止線では 43 km/h 以下に無い)、音だけでは前後が分からずミラーの赤色灯で後ろと決める。正直に: 判断の遅れ 1.0 s・附近 30 m・左に寄る 1.0 m・ミラーの寸法は仮定、サイレン 960 / 770 Hz と黄 3 s は一次未確認。教則の台帳は再現 15・一部 12・不能 7・未着手 125。19 門、56.7 s。*

[![信号の予測(車載 640 × 360・10 fps + 俯瞰の帯)。並行する歩行者信号(右上に灯火のまわりを同じ焦点距離で描いた拡大)の青が t = 20.50 s に初めて消えたコマで「青点滅」と分かり、青点滅の長さ F = 10 s と](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_decisions/02_signal_prediction.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_decisions/02_signal_prediction.gif)

*↑ 測定の図 ―― 信号の予測(車載 640 × 360・10 fps + 俯瞰の帯)。並行する歩行者信号(右上に灯火のまわりを同じ焦点距離で描いた拡大)の青が t = 20.50 s に初めて消えたコマで「青点滅」と分かり、青点滅の長さ F = 10 s と Δ = 2 s から車両の黄を 32.23 s(±0.27、真値 32 s)と予測。50 km/h の自車(青)はそのままだと黄の瞬間に GHM のジレンマゾーン(50 km/h で橙、17.2〜46.0 m)に入ると分かるので、早めに 2 m/s² で減速して停止線で止まる。予測しない自車(黒)は黄の瞬間に停止線の 33.3 m 手前 = ジレンマゾーンの中。下の帯は行ごとに「その車の今の速さとブレーキの状態」でのジレンマゾーン(門の in_dilemma と同じ式、減速中は反応 0。上 = GHM 橙、下 = 停止線の読み 赤、50 km/h では 41.7〜46.0 m)—— 減速している青の車の帯は縮み、車は帯の外にいる。*

[![黄が点いた瞬間の (速さ, 停止線までの距離) の平面。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_decisions/03_dilemma_zone_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_decisions/03_dilemma_zone.png)

*↑ 黄が点いた瞬間の (速さ, 停止線までの距離) の平面。*

[![合成したサイレン(960 / 770 Hz を 0.65 s ずつ、発音時刻の 2 次方程式だけで作る)を左のマイクで聞いたスペクトログラム。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_decisions/04_siren_spectrogram_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_decisions/04_siren_spectrogram.png)

*↑ 合成したサイレン(960 / 770 Hz を 0.65 s ずつ、発音時刻の 2 次方程式だけで作る)を左のマイクで聞いたスペクトログラム。*

[![左後方(車の中心から左 1.2〜4.6 m・目の後ろ 15 m まで)のうち、左ドアミラーにも直接の視界(方位 100° まで、青の線)にも入らない所(赤)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_decisions/05_mirror_blind_zone_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_decisions/05_mirror_blind_zone.png)

*↑ 左後方(車の中心から左 1.2〜4.6 m・目の後ろ 15 m まで)のうち、左ドアミラーにも直接の視界(方位 100° まで、青の線)にも入らない所(赤)。*

[![技能試験の採点基準(警察庁 丁運発第44号: 安全不確認 10 点・合図不履行等 5 点)を check_sequence_score で。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_decisions/06_check_sequence_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_decisions/06_check_sequence.png)

*↑ 技能試験の採点基準(警察庁 丁運発第44号: 安全不確認 10 点・合図不履行等 5 点)を check_sequence_score で。*

```
py -3.11 examples/poc_driving_decisions.py
```

ソース: [examples/poc_driving_decisions.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_driving_decisions.py)

この回が作った図は全部で **6 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_driving_decisions)

使用 op(ノートへ): [`add_mesh_object`](https://furuse.work/ops/drive/terrain/add_mesh_object.html) · [`aliased_frequency`](https://furuse.work/ops/drive/decide/aliased_frequency.html) · [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`bus_departure_yield_check`](https://furuse.work/ops/drive/decide/bus_departure_yield_check.html) · [`check_sequence_score`](https://furuse.work/ops/drive/decide/check_sequence_score.html) · [`convex_mirror_fov`](https://furuse.work/ops/drive/decide/convex_mirror_fov.html) · [`dilemma_zone`](https://furuse.work/ops/drive/decide/dilemma_zone.html) · [`doppler_shift`](https://furuse.work/ops/drive/decide/doppler_shift.html) · [`doppler_track`](https://furuse.work/ops/drive/decide/doppler_track.html) · [`filled_polygon`](https://furuse.work/ops/annotate/shape/filled_polygon.html) · [`flash_frequency`](https://furuse.work/ops/drive/decide/flash_frequency.html) · [`grid_lines`](https://furuse.work/ops/annotate/plot/grid_lines.html) · [`idm_accel`](https://furuse.work/ops/drive/traffic/idm_accel.html) · [`legend_box`](https://furuse.work/ops/annotate/furniture/legend_box.html) · [`mirror_aim_normal`](https://furuse.work/ops/drive/decide/mirror_aim_normal.html) · [`mirror_blind_zone`](https://furuse.work/ops/drive/decide/mirror_blind_zone.html) · [`mirror_virtual_camera`](https://furuse.work/ops/drive/decide/mirror_virtual_camera.html) · [`nice_ticks`](https://furuse.work/ops/annotate/plot/nice_ticks.html) · [`plot_series`](https://furuse.work/ops/annotate/plot/plot_series.html) · [`predict_amber_onset`](https://furuse.work/ops/drive/decide/predict_amber_onset.html) · [`signal_phase_plan`](https://furuse.work/ops/drive/decide/signal_phase_plan.html) · [`signal_state`](https://furuse.work/ops/drive/decide/signal_state.html) · [`siren_signal`](https://furuse.work/ops/drive/decide/siren_signal.html) …(他 6)

## No.2026.181 —— 横の運動 ―― カーブの手前で落とす、車線の中を保つ、左に寄って左折する、内輪差で巻き込まない

[![横の運動 ―― カーブの手前で落とす、車線の中を保つ、左に寄って左折する、内輪差で巻き込まない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_lateral/04_offtracking_geometry_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_lateral/04_offtracking_geometry.png)

*↑ **横の運動 ―― カーブの手前で落とす、車線の中を保つ、左に寄って左折する、内輪差で巻き込まない** ―― 著者の方針 ——「AI には部品の組み合わせを考えてもらう、部品はルールベースに限定して増やす」「ランダムなものを載せるなら、統計に基づいて極端に外れすぎたものは採用しない」。教則の台帳から、道路の左に寄って通行・車線をまたがない・路肩にはみ出さない・曲がり角では徐行・左折は左端に寄り側端に沿って・右折は中央に寄り中心のすぐ内側、を拾った。新モジュール drivelateral 20 op。門: 標本の門(参照分布の両側 0.1 % 点で 1 個ずつ落とし理由を記録、集団は KS)で自転車の速さ 24,000 個から 22 個を落とし KS p = 0.905、単位の誤りは 1 個ずつの門を 86 % が通るが KS が D = 0.986 で落とす / クロソイド R 100 m・L 40 m は道路構造令の表と解説の許容 0.5〜0.75 m/s³ の中 / 120 人の速度計画は摩擦円の使用率 最大 0.48・曲がり角の附近 10 km/h 以下、計画なしは全員が円を出る(使用率 1.65〜2.42)/ 全員が中央線をまたがず(最小 0.24 m)路肩へ出ない(最小 0.34 m)/ pure pursuit の定常の横ずれ = 2 自由度の式 ±0.0001 m / 内輪差の閉形式 = 後輪の軌跡の数値 ±0.2 mm、90° で 0.68 m / 左に寄った左折は違反なし・隅で待つ自転車から 0.66 m、前輪で隅をなぞると内輪差で触れる / 寄らない左折は後ろの自転車の巻き込みが残り、重要度サンプリング p = 0.00024 と素朴な MC 12 / 24000 件が Poisson で食い違わない / 右折は大回り・早回りを違反に。見つけたこと: 運動学の式は定常の横ずれを 41〜47 % に見積もる、90° の左折で内輪差は定常に届かない、1 個ずつの門は単位の誤りを通す、稀な出来事は落とさず重みで数える。正直に: 線形タイヤで飽和は描かない、寸法・判定の幅・μ などの参照分布は仮定(一次は自転車の平均速度と道路構造令の表だけ)。教則の台帳は再現 22・一部 12・不能 7・未着手 118。15 門、45.1 s。*

[![主図(車載カメラ 640 × 360、356 コマ)。場面 1(190 コマ): 半径 100 m のカーブと半径 15 m の曲がり角(道路構造令の設計速度 50・20 km/h の表の値、クロソイドでつなぐ)。curvature_spe](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_lateral/01_lateral_dashcam.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_lateral/01_lateral_dashcam.gif)

*↑ 測定の図 ―― 主図(車載カメラ 640 × 360、356 コマ)。場面 1(190 コマ): 半径 100 m のカーブと半径 15 m の曲がり角(道路構造令の設計速度 50・20 km/h の表の値、クロソイドでつなぐ)。curvature_speed_plan の計画どおりカーブの手前で減速し、曲がり角の附近は 10 km/h、pure pursuit(注視距離は 2 自由度の定常の横ずれ ≤ 0.25 m で上限)で車線の中を走る。右上 = 摩擦円(黒 = μg、青 = この人の横加速度の上限、赤 = 今の加速度)。場面 2: 外側線から 0.25 m に寄って左折、後ろから 23 km/h の自転車は左に入れない(巻き込み なし)。場面 3: 車線の中央のまま左折、同じ自転車(同じ距離・速さ)が左に入り込み、曲がる車体に触れる(巻き込み あり)。右上 = 上から見た図(青の線 = 後輪の内側の軌跡、橙 = 隅で人・自転車が待つ所)。*

[![摩擦円: 車の加速度を μg で割った点(横 = 横加速度(左旋回を左に描く)、縦 = 縦加速度、黒の円 = 使用率 1)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_lateral/03_friction_circle_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_lateral/03_friction_circle.png)

*↑ 摩擦円: 車の加速度を μg で割った点(横 = 横加速度(左旋回を左に描く)、縦 = 縦加速度、黒の円 = 使用率 1)。*

[![曲率から作る速度計画(前向き・後ろ向きの 2 パス、摩擦円つき)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_lateral/05_speed_plan_band_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_lateral/05_speed_plan_band.png)

*↑ 曲率から作る速度計画(前向き・後ろ向きの 2 パス、摩擦円つき)。*

[![稀な出来事: 車線の中央のまま左折すると、後ろの自転車が左に入り込んで巻き込まれるのは、速い自転車(22.1 km/h 以上、採った速さの 2.9 %)がちょうど曲がる頃に追いつく細い帯だけ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_lateral/06_rare_event_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_lateral/06_rare_event_map.png)

*↑ 稀な出来事: 車線の中央のまま左折すると、後ろの自転車が左に入り込んで巻き込まれるのは、速い自転車(22.1 km/h 以上、採った速さの 2.9 %)がちょうど曲がる頃に追いつく細い帯だけ。*

[![乱数の値の門: 自転車の速さは参照分布 N(14.5, 3.5) km/h(平均は国総研の車道の旅行速度、幅は仮定)の両側 0.1 % 点(3.0〜26.0 km/h)の外を 1 個ずつ落としてから採](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_lateral/07_sample_gate_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_lateral/07_sample_gate.png)

*↑ 乱数の値の門: 自転車の速さは参照分布 N(14.5, 3.5) km/h(平均は国総研の車道の旅行速度、幅は仮定)の両側 0.1 % 点(3.0〜26.0 km/h)の外を 1 個ずつ落としてから採り(24000 個、KS p = 0.91)、残りを切断正規との KS で照合する。*

[![上から見た動画(229 コマ)。同じ運転者(μ 0.72)を、curvature_speed_plan の計画どおり(上左、青)と 50 km/h のまま(上右、赤)で走らせ、同じ道のりの所を並べる(60 m 四方、車について動く。点 = ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_lateral/02_lateral_birdseye.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_lateral/02_lateral_birdseye.gif)

*↑ 動く図 ―― 上から見た動画(229 コマ)。同じ運転者(μ 0.72)を、curvature_speed_plan の計画どおり(上左、青)と 50 km/h のまま(上右、赤)で走らせ、同じ道のりの所を並べる(60 m 四方、車について動く。点 = 過去 12 s の通った跡、青 = 摩擦円の中、赤 = 外)。下左 = 速さ(青の帯 = 120 人の計画の最小〜最大、青の線 = この人、赤 = 計画なし、橙 = 曲がり角の附近の徐行の区間、黒の縦線 = 今)、下右 = 摩擦円(加速度 / μg、横 = 横加速度(左旋回で左)・縦 = 縦加速度)。計画なしの点は曲がり角で円の外へ出る(使用率 最大 2.15 = 線形モデルの外、実際には滑る)。*

```
py -3.11 examples/poc_driving_lateral.py
```

ソース: [examples/poc_driving_lateral.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_driving_lateral.py)

この回が作った図は全部で **8 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_driving_lateral)

使用 op(ノートへ): [`ackermann_steer_angles`](https://furuse.work/ops/drive/lateral/ackermann_steer_angles.html) · [`add_mesh_object`](https://furuse.work/ops/drive/terrain/add_mesh_object.html) · [`bicycle_model_step`](https://furuse.work/ops/drive/lateral/bicycle_model_step.html) · [`clothoid_design`](https://furuse.work/ops/drive/lateral/clothoid_design.html) · [`clothoid_points`](https://furuse.work/ops/drive/lateral/clothoid_points.html) · [`curvature_speed_plan`](https://furuse.work/ops/drive/lateral/curvature_speed_plan.html) · [`ellipse`](https://furuse.work/ops/annotate/shape/ellipse.html) · [`friction_circle_usage`](https://furuse.work/ops/drive/lateral/friction_circle_usage.html) · [`lateral_offset`](https://furuse.work/ops/drive/lateral/lateral_offset.html) · [`offtracking_circle`](https://furuse.work/ops/drive/lateral/offtracking_circle.html) · [`pure_pursuit_circle_offset`](https://furuse.work/ops/drive/lateral/pure_pursuit_circle_offset.html) · [`pure_pursuit_curvature`](https://furuse.work/ops/drive/lateral/pure_pursuit_curvature.html) · [`rear_axle_path`](https://furuse.work/ops/drive/lateral/rear_axle_path.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`time_to_line_crossing`](https://furuse.work/ops/drive/lateral/time_to_line_crossing.html) · [`turn_maneuver_check`](https://furuse.work/ops/drive/lateral/turn_maneuver_check.html) · [`understeer_gradient`](https://furuse.work/ops/drive/lateral/understeer_gradient.html) · [`world_camera`](https://furuse.work/ops/drive/world/world_camera.html) · [`world_move`](https://furuse.work/ops/drive/world/world_move.html)

## No.2026.182 —— 踏切と交差点の優先 ―― 直前で止まって左右を見る、警報の間は入らない、向こう側が詰まっていれば入らない、広い道へは譲る

[![踏切と交差点の優先 ―― 直前で止まって左右を見る、警報の間は入らない、向こう側が詰まっていれば入らない、広い道へは譲る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_crossing/01_crossing_dashcam.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_crossing/01_crossing_dashcam.gif)

*↑ **踏切と交差点の優先 ―― 直前で止まって左右を見る、警報の間は入らない、向こう側が詰まっていれば入らない、広い道へは譲る** ―― 教則の台帳の未着手から、ルールベースの部品で再現できる場面をまとめて拾った —— 踏切(直前で一時停止して左右・警報中は入らない・向こう側が詰まっていれば入らない・やや中央寄り)、交差点の優先(広い道へ徐行して譲る・左方優先)、横断歩道(停止車両の横の一時停止・30 m 以内の追越し禁止)、駐停車禁止の距離。新モジュール drivecrossing 17 op、乱数の値は標本の門(0.1 % 点と KS)。門: 鉄道の解釈基準の時刻(遮断機つき 警報→遮断 15 s・遮断→到達 20 s)を満たし、固定の始動点が最小を割る速さは閉形式で 152 km/h / ルールの 240 人は違反 0・全員が渡り切り・列車が着くとき線路の上 0 人(余裕 最小 31.5 s)、止まらない版 no_stop 79・警報中に入る版 157(状態機械の数と一致、うち 23 人が線路の上)/ 見通しの三角形の閉形式 19.03 m = 光線の総当たり、見えない列車の確率 建物 7.92e-03・確かめ直さない 2.11e-02 を閉形式・MC・重要度サンプリングが 1.1σ 以内で一致 / 広い道で交差道路の車に減速を一切させない、素朴は進行妨害 104 / 240、左方優先は右から来る車が譲る場面もある / 横断歩道の停止車両の横は一時停止、30 m 以内で車の前に出ない(自転車は除外)/ 44 条の禁止区間 = 1 mm 格子で直接塗った答え、止まりたい所に止まると違反 476 / 1000(6 種類すべて)/ 警報灯の交互点滅を画素から 0.833 Hz・位相差 π、間引くと折り返しの式どおり 0.500 Hz。見つけたこと: 警報→到達 30 s は遮断機の無い踏切の値、固定の始動点では遅い列車ほど警報が長い、発進直後に警報が始まるジレンマ、門を素通りした汚れ(灯を隠す列車の色)を目視で見つけた。正直に: 幅の比 1.5・「急に」2.0 m/s²・遮断かんの時刻・参照分布は仮定、警報灯の毎分 50 回は二次資料、音での確認は扱わない。教則の台帳は再現 33・一部 14・不能 7・未着手 105。22 門、18.7 s。*

[![車載カメラ(640 × 360、114 コマ)。片側 2 車線、左の車線の SUV が横断歩道の直前で止まっている(歩行者 1.78 m/s が陰から渡る)。場面 1(72 コマ): 横に並ぶ前に一時停止、徐行で横断歩道の直前へ出て、歩行者](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_crossing/02_crosswalk_dashcam.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_crossing/02_crosswalk_dashcam.gif)

*↑ 測定の図 ―― 車載カメラ(640 × 360、114 コマ)。片側 2 車線、左の車線の SUV が横断歩道の直前で止まっている(歩行者 1.78 m/s が陰から渡る)。場面 1(72 コマ): 横に並ぶ前に一時停止、徐行で横断歩道の直前へ出て、歩行者が見えて渡り終えるまで待つ —— crosswalk_stopped_vehicle_check = 違反なし、触れた = いいえ。場面 2(42 コマ): 40 km/h のまま横を抜け、見えてから 0.75 s 後に 6 m/s² で止まろうとする —— 判定 = 38 条 2 項の違反、触れた = はい。*

[![主図の場面 1 の時刻。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_crossing/05_crossing_timeline_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_crossing/05_crossing_timeline.png)

*↑ 主図の場面 1 の時刻。*

[![主図の車載カメラのコマ(4.0 fps、運転者が前を向いて止まっている間、列車が灯を隠す前まで)で、向こう側の柱の 2 灯の画素を読んだ時系列。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_crossing/06_lamp_pixels_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_crossing/06_lamp_pixels.png)

*↑ 主図の車載カメラのコマ(4.0 fps、運転者が前を向いて止まっている間、列車が灯を隠す前まで)で、向こう側の柱の 2 灯の画素を読んだ時系列。*

[![見える距離 19.0 m(sight_triangle_distance = 光線の総当たり)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_crossing/08_hidden_train_estimates_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_crossing/08_hidden_train_estimates.png)

*↑ 見える距離 19.0 m(sight_triangle_distance = 光線の総当たり)。*

[![同じ 240 人(列車の速さ・発進・見る時間は標本の門を通った値)を 5 通りの方針で。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_crossing/10_crossing_policies_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_crossing/10_crossing_policies.png)

*↑ 同じ 240 人(列車の速さ・発進・見る時間は標本の門を通った値)を 5 通りの方針で。*

[![上から見た動画(151 コマ、0.5 秒ごと)。乱数の場面 #116(列車 96 km/h、向こう側の列の後端 = 踏切の端から 3.6 m)を 3 人で。左 = ルール(違反なし)、中 = 向こう側が詰まっていても入る(no_exit_r](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_crossing/03_crossing_birdseye.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_crossing/03_crossing_birdseye.gif)

*↑ 動く図 ―― 上から見た動画(151 コマ、0.5 秒ごと)。乱数の場面 #116(列車 96 km/h、向こう側の列の後端 = 踏切の端から 3.6 m)を 3 人で。左 = ルール(違反なし)、中 = 向こう側が詰まっていても入る(no_exit_room, stopped_inside)、右 = 警報中でも入る(entered_while_forbidden、列車が着くとき線路の上 = いいえ)。赤い車 = 警報〜上昇中に車体が踏切の上。*

[![上から見た動画(85 コマ)。狭い道(4 m)から広い道(7.0 m)へ(S098、36 条 2・3 項)。場面 #0 の同じ交差道路の車で、左 = ルール(線で徐行 10 km/h、7.9 s 待ってから、交差道路の車に減速を一切させない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_crossing/04_priority_birdseye.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_crossing/04_priority_birdseye.gif)

*↑ 動く図 ―― 上から見た動画(85 コマ)。狭い道(4 m)から広い道(7.0 m)へ(S098、36 条 2・3 項)。場面 #0 の同じ交差道路の車で、左 = ルール(線で徐行 10 km/h、7.9 s 待ってから、交差道路の車に減速を一切させない時刻に発進)、右 = 30 km/h のまま入る(交差道路の車に要った減速度 最大 5.1 m/s² = 進行妨害)。*

```
py -3.11 examples/poc_driving_crossing.py
```

ソース: [examples/poc_driving_crossing.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_driving_crossing.py)

この回が作った図は全部で **11 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_driving_crossing)

使用 op(ノートへ): [`add_mesh_object`](https://furuse.work/ops/drive/terrain/add_mesh_object.html) · [`aliased_frequency`](https://furuse.work/ops/drive/decide/aliased_frequency.html) · [`conflict_zone_intervals`](https://furuse.work/ops/drive/crossing/conflict_zone_intervals.html) · [`crossing_clear_time`](https://furuse.work/ops/drive/crossing/crossing_clear_time.html) · [`crossing_gate_state`](https://furuse.work/ops/drive/crossing/crossing_gate_state.html) · [`crossing_lamp_signal`](https://furuse.work/ops/drive/crossing/crossing_lamp_signal.html) · [`crossing_stop_check`](https://furuse.work/ops/drive/crossing/crossing_stop_check.html) · [`crossing_timing_check`](https://furuse.work/ops/drive/crossing/crossing_timing_check.html) · [`crosswalk_mesh`](https://furuse.work/ops/drive/terrain/crosswalk_mesh.html) · [`crosswalk_overtake_check`](https://furuse.work/ops/drive/crossing/crosswalk_overtake_check.html) · [`crosswalk_stopped_vehicle_check`](https://furuse.work/ops/drive/crossing/crosswalk_stopped_vehicle_check.html) · [`ellipse`](https://furuse.work/ops/annotate/shape/ellipse.html) · [`exit_room_check`](https://furuse.work/ops/drive/crossing/exit_room_check.html) · [`flash_frequency`](https://furuse.work/ops/drive/decide/flash_frequency.html) · [`intersection`](https://furuse.work/ops/2d/nary/intersection.html) · [`lamp_pair_phase`](https://furuse.work/ops/drive/crossing/lamp_pair_phase.html) · [`legal_stop_intervals`](https://furuse.work/ops/drive/crossing/legal_stop_intervals.html) · [`no_stopping_zones`](https://furuse.work/ops/drive/crossing/no_stopping_zones.html) · [`obstruction_decel`](https://furuse.work/ops/drive/crossing/obstruction_decel.html) · [`parking_position_check`](https://furuse.work/ops/drive/crossing/parking_position_check.html) · [`pedestrian_mesh`](https://furuse.work/ops/drive/terrain/pedestrian_mesh.html) · [`priority_rule`](https://furuse.work/ops/drive/crossing/priority_rule.html) · [`sight_triangle_distance`](https://furuse.work/ops/drive/crossing/sight_triangle_distance.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) …(他 3)

## No.2026.183 —— 追越しと見えない所 ―― 見通しが足りなければ待つ、ルームミラーに映ってから戻る、環道の車を妨げない、カーブミラーは遠く見える

[![追越しと見えない所 ―― 見通しが足りなければ待つ、ルームミラーに映ってから戻る、環道の車を妨げない、カーブミラーは遠く見える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_pass/01_overtake_dashcam.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_pass/01_overtake_dashcam.gif)

*↑ **追越しと見えない所 ―― 見通しが足りなければ待つ、ルームミラーに映ってから戻る、環道の車を妨げない、カーブミラーは遠く見える** ―― 教則の台帳の未着手から、ルールベースの部品で再現できる追越しと見えない所の場面 —— 追越し(見通しが要る距離 D* に足りなければ待つ・30 条の禁止区間・ルームミラーに前の車の全体が映ってから戻る)、追い越される側は速さを増さない、進路変更で後続車に急ブレーキをさせない、環状交差点(徐行で入り、出口の 1 つ手前の出口を過ぎたら左の合図)、坂の頂上の視距、カーブミラー。新モジュール drivepass 17 op、乱数の値は標本の門(0.1 % 点と KS)。門: ルームミラーの車間 閉形式 19.75 m = Fermat の最短経路の走査 / 30 条の禁止区間 = 条文の総当たり / 規則の 240 人は 188 人が追い越し、禁止区間 0・対向車との PET 最小 5.62 s、素朴は禁止区間 18・PET < 2 s が 44・割り込み 240 / 240 / 後続車に要る減速度の閉形式 = 2 台の時間の行進 / 環道の車に要る減速度 = 円周の行進、左の合図の時刻 = 出口の通過の再生、素朴は進行妨害 38 / 240 / 道路構造令の視距の表 3 行を再現 / 凸面鏡の大きさから読む距離 k·a = 3 次元の光線追跡(30 m → 190.04 m)、45° の斜めでは Coddington の式どおり縦 k_s = 4.75・横 k_t = 8.58、手前の死角 8.16 m。見つけたこと: 凸面鏡は遠く見えるが、速さは読み方で速くも遅くも見える / 坂の頂上の「付近」30 m は見通しが足りない 522 m のうち 60 m しか覆わない / 素朴な割り込みは前の車に急ブレーキを要らせない(危なさは車間時間と PET に出る)。正直に: 「付近」30 m・「急な」10 %・「急に」2.0 m/s²・徐行 10 km/h・鏡の寸法・参照分布は仮定、施行令 21 条は未確認。教則の台帳は再現 38・一部 17・不能 7・未着手 97。24 門、3.5 s。*

[![上から見た動画(178 コマ、0.2 s ごと = 実時間)。環状交差点(環道の半径 14 m、右回り)に南から入り 出口 3(右折) へ出る場面 #0 を、同じ環道の車で。左 = 規則: 環道の車に 2.0 m/s² を超える減速を要らせ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_pass/02_roundabout_birdseye.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_pass/02_roundabout_birdseye.gif)

*↑ 測定の図 ―― 上から見た動画(178 コマ、0.2 s ごと = 実時間)。環状交差点(環道の半径 14 m、右回り)に南から入り 出口 3(右折) へ出る場面 #0 を、同じ環道の車で。左 = 規則: 環道の車に 2.0 m/s² を超える減速を要らせない時刻まで 0.8 s 待ち、徐行(10 km/h)で入り、出口の 1 つ手前の出口の側方で左の合図(roundabout_signal_point、黄の点)—— roundabout_signal_check = 違反なし。右 = 素朴: 20 km/h のまま入り(環道の車に要らせた減速度 最大 3.1 m/s² = 37 条の 2 第 1 項の進行妨害)、右の合図で入り、出口の直前で左に変える(right_signal, left_late)。*

[![参照 N(55, 6) km/h(仮定)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_pass/04_sample_gate_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_pass/04_sample_gate.png)

*↑ 参照 N(55, 6) km/h(仮定)。*

[![凸形縦断曲線(±4 %、L 160 m、R 2000 m)の道で、運転者の目(1.2 m)から対向車(1.2 m)が見える距離。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_pass/05_sight_vs_dstar_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_pass/05_sight_vs_dstar.png)

*↑ 凸形縦断曲線(±4 %、L 160 m、R 2000 m)の道で、運転者の目(1.2 m)から対向車(1.2 m)が見える距離。*

[![平面鏡のつもりで像の大きさから距離を読むと k 倍遠い。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_pass/07_mirror_readings_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_pass/07_mirror_readings.png)

*↑ 平面鏡のつもりで像の大きさから距離を読むと k 倍遠い。*

[![240 場面(後続車の速さ・反応は標本の門を通った値、自車 50 km/h、残す車間 2 m)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_pass/08_lane_change_decel_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_pass/08_lane_change_decel.png)

*↑ 240 場面(後続車の速さ・反応は標本の門を通った値、自車 50 km/h、残す車間 2 m)。*

[![目玉の動画(51 コマ、実時間)。見通しの悪い T 字路(右の角は高さ 2 m の塀)で停止線に止まった運転者が、向こう側のカーブミラー(凸面 R 3 m・直径 0.8 m、目から 8.0 m、入射角 45°)を見る。左 = 運転席から見た](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_pass/03_mirror_tjunction.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_driving_pass/03_mirror_tjunction.gif)

*↑ 動く図 ―― 目玉の動画(51 コマ、実時間)。見通しの悪い T 字路(右の角は高さ 2 m の塀)で停止線に止まった運転者が、向こう側のカーブミラー(凸面 R 3 m・直径 0.8 m、目から 8.0 m、入射角 45°)を見る。左 = 運転席から見た鏡の拡大: 鏡の中は球面での反射の光線を環境の画像から引いて描いた(視差を深度で 3 回補正、車のメッシュの頂点の厳密な光線追跡と画素で照合)。右から 30 km/h で来る赤い車は、鏡から 29 m のとき鏡の中で高さ 48 px(同じ所の平面鏡なら 189 px)—— 画素の比で読むと 139 m 先。閉形式の読みは縦 140 m・横 253 m(Coddington の式 k_s = 4.75、k_t = 8.58。正面から見る近軸なら k = 6.33 で 187 m)。右上 = 運転席からの広い眺め、右下 = 上から見た本当の位置(赤の線 = 鏡に映らない手前 8.2 m、橙 = 映る範囲、緑 = 塀の陰から直接見える所。下の目盛り = 本当の距離と鏡の読み)。*

```
py -3.11 examples/poc_driving_pass.py
```

ソース: [examples/poc_driving_pass.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_driving_pass.py)

この回が作った図は全部で **9 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_driving_pass)

使用 op(ノートへ): [`convex_mirror_image`](https://furuse.work/ops/drive/pass/convex_mirror_image.html) · [`convex_mirror_misjudge`](https://furuse.work/ops/drive/pass/convex_mirror_misjudge.html) · [`crest_safe_speed`](https://furuse.work/ops/drive/pass/crest_safe_speed.html) · [`crest_sight_distance`](https://furuse.work/ops/drive/pass/crest_sight_distance.html) · [`ellipse`](https://furuse.work/ops/annotate/shape/ellipse.html) · [`intersection`](https://furuse.work/ops/2d/nary/intersection.html) · [`lane_change_follower_decel`](https://furuse.work/ops/drive/pass/lane_change_follower_decel.html) · [`lane_change_permitted`](https://furuse.work/ops/drive/pass/lane_change_permitted.html) · [`load_asset`](https://furuse.work/ops/drive/world/load_asset.html) · [`mirror_aim_normal`](https://furuse.work/ops/drive/decide/mirror_aim_normal.html) · [`mirror_road_coverage`](https://furuse.work/ops/drive/pass/mirror_road_coverage.html) · [`no_overtaking_zones`](https://furuse.work/ops/drive/pass/no_overtaking_zones.html) · [`overtake_permitted`](https://furuse.work/ops/drive/pass/overtake_permitted.html) · [`overtake_requirement`](https://furuse.work/ops/drive/pass/overtake_requirement.html) · [`overtake_return_gap`](https://furuse.work/ops/drive/pass/overtake_return_gap.html) · [`overtaken_conduct_check`](https://furuse.work/ops/drive/pass/overtaken_conduct_check.html) · [`roundabout_entry_check`](https://furuse.work/ops/drive/pass/roundabout_entry_check.html) · [`roundabout_signal_check`](https://furuse.work/ops/drive/pass/roundabout_signal_check.html) · [`roundabout_signal_point`](https://furuse.work/ops/drive/pass/roundabout_signal_point.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`world_camera`](https://furuse.work/ops/drive/world/world_camera.html)

### 数学の絵 ―― 定理が門になる回(別記事)

この展示先の回は、計測の展示館ではなく**数学の絵のシリーズ**に掛かっています。分ける基準は「真値がどこから来るか」です —— 計測の展示は測る対象があり真値は対象の側に、ここの回は対象が無く、真値は描いた絵そのものの定理・恒等式・不変量から出ます。記事は手書きなので、生成器はここを描きません。

## No.2026.137 —— 写真を 1 本の線にして、回る振り子に描かせる ―― 濃淡 → 点描 → 巡回路 → フーリエ級数 → G-code

[![写真を 1 本の線にして、回る振り子に描かせる ―― 濃淡 → 点描 → 巡回路 → フーリエ級数 → G-code](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_one_stroke_epicycles/07_epicycles.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_one_stroke_epicycles/07_epicycles.gif)

*↑ **写真を 1 本の線にして、回る振り子に描かせる ―― 濃淡 → 点描 → 巡回路 → フーリエ級数 → G-code** ―― 葛飾北斎「神奈川沖浪裏」(メトロポリタン美術館 CC0)の濃淡を 1 本の閉じた線にし、それを回る円の連鎖として描き直す。様式化は必ず「それらしい絵」が出るので、各段を数で門にした: 点描は濃淡を追うか(ランプで相関 0.9946、対照の一様画像では等間隔 cv 0.13)、★★**相関だけでは指数が見えない** —— 重心ボロノイの最適密度は √重み なので(Gersho)、実測の指数は 0.61 で暗さに比例していない(重みを二乗して 0.77)。巡回路は**最小全域木より短くなれない**ので比で言う(1.146、素朴な座標順は 41.4)、濃淡の再現は相関 0.984(同数のランダム線の対照群は +0.013)。★ペン幅は閉形式で解け、インク率は目標の 0.890 倍 —— 不足の 11 % が**線の重なりの量**。★★**ナイキストを先に確かめる**: 等弧長の打ち直しは間隔が線分より粗いと角を切って線が縮み、フーリエに載せる前に情報が落ちる(16,384 点で長さ保持 0.935 → 65,536 点で 0.984、誤差は 1/N)。★★円の本数はパーセバルで**描く前に**決まる(K=16 で 95.9 %、K=64 で 99.0 %)。GIF は**本物の回る腕**で、1 → 4 → 16 → 90 → 600 → 4000 本と増えるにつれ絵が正体を現す。出口は既存の G-code op で「1 本の線で紙の上 15.57 m、プロッタ最短 8.6 分」。--image で自分の写真でも走る。*

[![weighted Lloyd puts points where the picture is dark. The claim is measured, not looked at: on a ramp the count per band](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_one_stroke_epicycles/01_stipple_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_one_stroke_epicycles/01_stipple.png)

*↑ 測定の図 ―― weighted Lloyd puts points where the picture is dark. The claim is measured, not looked at: on a ramp the count per band correlates 0.995 with darkness, and on a flat image the points spread evenly (nearest-neighbour cv 0.13 against 0.37 for the ramp)*

[![Lloyd's energy sum w|x-c(x)|^2 never goes up — that is a property of the algorithm that can be check](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_one_stroke_epicycles/02_lloyd_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_one_stroke_epicycles/02_lloyd.png)

*↑ Lloyd's energy sum w|x-c(x)|^2 never goes up — that is a property of the algorithm that can be checked exactly, which is why it is the gate rather tha…*

[![both pictures visit exactly the same 9000 points exactly once; only the order differs.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_one_stroke_epicycles/03_tour_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_one_stroke_epicycles/03_tour.png)

*↑ both pictures visit exactly the same 9000 points exactly once; only the order differs.*

[![while the strokes do not overlap the ink fraction is length x width / area, so the width that reprod](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_one_stroke_epicycles/05_pen_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_one_stroke_epicycles/05_pen.png)

*↑ while the strokes do not overlap the ink fraction is length x width / area, so the width that reproduces the mean tone is solved in closed form (0.90…*

[![every row is measured by an operator in this run; the harmonic rows are predicted in closed form bef](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_one_stroke_epicycles/08_numbers_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_one_stroke_epicycles/08_numbers.png)

*↑ every row is measured by an operator in this run; the harmonic rows are predicted in closed form before the drawing is made*

```
py -3.11 examples/poc_one_stroke_epicycles.py
```

ソース: [examples/poc_one_stroke_epicycles.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_one_stroke_epicycles.py)

この回が作った図は全部で **9 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_one_stroke_epicycles)

使用 op(ノートへ): [`contour_epicycle_chain`](https://furuse.work/ops/shape2d/descriptor/contour_epicycle_chain.html) · [`contour_fourier_complex`](https://furuse.work/ops/shape2d/descriptor/contour_fourier_complex.html) · [`contour_fourier_truncation_energy`](https://furuse.work/ops/shape2d/descriptor/contour_fourier_truncation_energy.html) · [`contours_to_gcode`](https://furuse.work/ops/printpath/slice/contours_to_gcode.html) · [`gcode_time_estimate`](https://furuse.work/ops/printpath/gcode/gcode_time_estimate.html) · [`mst_length`](https://furuse.work/ops/printpath/stroke/mst_length.html) · [`stipple_energy`](https://furuse.work/ops/printpath/stroke/stipple_energy.html) · [`stipple_points_from_image`](https://furuse.work/ops/printpath/stroke/stipple_points_from_image.html) · [`stroke_resample_closed`](https://furuse.work/ops/printpath/stroke/stroke_resample_closed.html) · [`stroke_tone_error`](https://furuse.work/ops/printpath/stroke/stroke_tone_error.html) · [`stroke_tour_closed`](https://furuse.work/ops/printpath/stroke/stroke_tour_closed.html)

## No.2026.138 —— 複素平面を「面」で見る ―― 絵が定理を証明する側に回る

[![複素平面を「面」で見る ―― 絵が定理を証明する側に回る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_complex_plane_fields/05_mandelbrot_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_complex_plane_fields/05_mandelbrot.png)

*↑ **複素平面を「面」で見る ―― 絵が定理を証明する側に回る** ―― 複素解析の図(位相彩色・ニュートンの吸引域・マンデルブロ集合・翼まわりの流れ)は、きれいなので**合っているかを誰も確かめない**種類の絵である。4 枚を描き、1 枚ごとに**絵とは独立の真値**を当てて採点した。零点と極は既存 op(cplx_winding_number)が数える(+3 / +1 / −2、窓の外は数えない対照群つき)。★位相彩色は**画素の RGB だけ**から色相の巻き数を読むと零点の位数になる(偏角の原理)。★★z²−1 のニュートン吸引域はCayley 1879 の厳密解 = 2 つの半平面で、512² = 262,144 画素が**1 画素も外れず**未収束 0。3 次は Cayley が解けなかった側で、同じ格子の境界画素が 1,026 → 13,348(13 倍)—— それでも共役対称は厳密。★主カージオイドと周期 2 球は**反復せずに**内側と言える閉形式で、85,624 画素が反例 0 件、ただし実際に残った 95,078 画素の 90.1 %(下界であることも数で出る)。c=0 のジュリア集合は単位円板(全数走査)。翼まわりの場は翼の外で正則なので cplx_cr_residual が 2.06e-04、循環は経路に依らず(外周 −3.0263 / 内周 −3.0263)、後縁が有限なのはクッタ条件のおかげで循環 0 なら 20 倍以上に発散する(対照群)。★揚力と薄翼理論の比は迎角にも速さにもよらず**厳密に a/b**(1.0940、ずれ < 1e-9)。*

[![有理関数 (z−z₁)(z−z₂)/(z−p) の位相彩色。色相 = 偏角、明度 = |z|。零点では黒く、極では明るく色相が逆に回る。既存 op の cplx_winding_number が同じ場から数えた巻き数は +1 (零点 2 −](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_complex_plane_fields/01_rational_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_complex_plane_fields/01_rational.png)

*↑ 測定の図 ―― 有理関数 (z−z₁)(z−z₂)/(z−p) の位相彩色。色相 = 偏角、明度 = |z|。零点では黒く、極では明るく色相が逆に回る。既存 op の cplx_winding_number が同じ場から数えた巻き数は +1 (零点 2 − 極 1)で、絵の色相の回り方と一致する。*

[![★絵が定理を証明する側に回る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_complex_plane_fields/02_orders_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_complex_plane_fields/02_orders.png)

*↑ ★絵が定理を証明する側に回る。*

[![2 次の境界は虚軸 1 本(513 画素の格子で 1026)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_complex_plane_fields/04_boundary_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_complex_plane_fields/04_boundary.png)

*↑ 2 次の境界は虚軸 1 本(513 画素の格子で 1026)。*

[![迎角 8 度のジューコフスキー翼まわりの非粘性流。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_complex_plane_fields/07_flow_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_complex_plane_fields/07_flow.png)

*↑ 迎角 8 度のジューコフスキー翼まわりの非粘性流。*

[![★CL = 2π(a/b)sin(α+β)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_complex_plane_fields/09_lift_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_complex_plane_fields/09_lift.png)

*↑ ★CL = 2π(a/b)sin(α+β)。*

```
py -3.11 examples/poc_complex_plane_fields.py
```

ソース: [examples/poc_complex_plane_fields.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_complex_plane_fields.py)

この回が作った図は全部で **10 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_complex_plane_fields)

使用 op(ノートへ): [`boundary`](https://furuse.work/ops/2d/region/boundary.html) · [`cplx_cr_residual`](https://furuse.work/ops/math/complex/cplx_cr_residual.html) · [`cplx_domain_colour`](https://furuse.work/ops/math/complex/cplx_domain_colour.html) · [`cplx_escape_time`](https://furuse.work/ops/math/complex/cplx_escape_time.html) · [`cplx_newton_basins`](https://furuse.work/ops/math/complex/cplx_newton_basins.html) · [`cplx_plane_grid`](https://furuse.work/ops/math/complex/cplx_plane_grid.html) · [`cplx_rational_field`](https://furuse.work/ops/math/complex/cplx_rational_field.html) · [`cplx_winding_number`](https://furuse.work/ops/math/complex/cplx_winding_number.html) · [`joukowski_circulation`](https://furuse.work/ops/math/complex/joukowski_circulation.html) · [`mandelbrot_interior`](https://furuse.work/ops/math/complex/mandelbrot_interior.html) · [`potential_flow_joukowski`](https://furuse.work/ops/math/complex/potential_flow_joukowski.html)

## No.2026.139 —— 定理が門になる図 ―― アポロニウス・フォード・測地ドーム・葉序・IFS・空間充填曲線

[![定理が門になる図 ―― アポロニウス・フォード・測地ドーム・葉序・IFS・空間充填曲線](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_theorems_as_pictures/01_apollonian_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_theorems_as_pictures/01_apollonian.png)

*↑ **定理が門になる図 ―― アポロニウス・フォード・測地ドーム・葉序・IFS・空間充填曲線** ―― 数学的に美しい図は、きれいなので**合っているかを誰も確かめない** —— 実装が少し間違っていても円は詰まるし螺旋は回る。そこで 6 つの図を描き、**絵とは独立の真値**だけで採点した。★デカルトの円定理: 生成は反射で行うので、**接触を距離から探し直して**定理に入れる(depth 4 の 164 円で、見つかった接触 4 円の組すべてが相対ずれ 1e-13 以下)。★整数充填: 種 (−1,2,2,3) の曲率はどこまで行っても整数のまま(Lagarias–Mallows–Wilks)—— 絵では絶対に見えない誤りを捕まえる。★フォード円が接するのは **|p·s − q·r| = 1** のときに限る: 分母 12 までの 47 円・1,081 組で不一致 0、個数もオイラーの関数の和と一致。★★測地ドームは**次数 5 の頂点がちょうど 12 個**(f = 1,2,3,4,6 すべて、V−E+F=2)—— 次数は**既存の別実装** graph_degree_table に数えさせた(自分で数え直して自分と一致しても確かめたことにならない)。★葉序は角度をどう選んでも螺旋に見えるので絵を見ずに近傍の**番号差**を数える: 黄金角では山の 7/7 がフィボナッチ、対照群 137.0° と 90° は 2/7。★モランの式は**描く前に**次元を解き(シェルピンスキー 1.5850 = log3/log2)、描いた点は既存 fractal_dimension が 1.6164 —— 導出も入力も違うので一致は偶然では起きない。相似でないアフィン写像(シダ)は拒否する。★空間充填曲線は 4^n 点をちょうど 1 回ずつ通り隣は距離 1(row_major は行末で跳ぶ = 対照群、閉じているのは moore だけ)。局所性は主張でなく**表**: ヒルベルトは k=32 で 6.38 ≈ √32、走査線は 16.07。*

[![合計は 2·3^depth + 2。種の四つ組だけ 4 方向に反射し、以降は 3 方向 —— ここを 4 のままにすると親を作り直してdepth 3 で 56 個のはずが 88 個になる(一意な円は 56 のままなので、絵は正しく見える)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_theorems_as_pictures/02_apollonian_counts_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_theorems_as_pictures/02_apollonian_counts.png)

*↑ 測定の図 ―― 合計は 2·3^depth + 2。種の四つ組だけ 4 方向に反射し、以降は 3 方向 —— ここを 4 のままにすると親を作り直してdepth 3 で 56 個のはずが 88 個になる(一意な円は 56 のままなので、絵は正しく見える)。*

[![フォードの円(分母 12 まで、47 円)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_theorems_as_pictures/03_ford_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_theorems_as_pictures/03_ford.png)

*↑ フォードの円(分母 12 まで、47 円)。*

[![オイラーの公式 V − E + F = 2 の帰結。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_theorems_as_pictures/05_dome_degrees_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_theorems_as_pictures/05_dome_degrees.png)

*↑ オイラーの公式 V − E + F = 2 の帰結。*

[![黄金角の山は [34, 55, 89, 21, 13, 8, 144) —— すべてフィボナッチ数。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_theorems_as_pictures/07_parastichy_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_theorems_as_pictures/07_parastichy.png)

*↑ 黄金角の山は [34, 55, 89, 21, 13, 8, 144] —— すべてフィボナッチ数。*

[![order 5 で 4^5 = 1,024 点をちょうど 1 回ずつ通り、隣り合う点は必ず距離 1。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_theorems_as_pictures/09_curves_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_theorems_as_pictures/09_curves.png)

*↑ order 5 で 4^5 = 1,024 点をちょうど 1 回ずつ通り、隣り合う点は必ず距離 1。*

```
py -3.11 examples/poc_theorems_as_pictures.py
```

ソース: [examples/poc_theorems_as_pictures.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_theorems_as_pictures.py)

この回が作った図は全部で **11 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_theorems_as_pictures)

使用 op(ノートへ): [`circle_packing_apollonian`](https://furuse.work/ops/math/construct/circle_packing_apollonian.html) · [`curve_locality`](https://furuse.work/ops/math/construct/curve_locality.html) · [`ford_circles`](https://furuse.work/ops/math/construct/ford_circles.html) · [`fractal_dimension`](https://furuse.work/ops/2d/features/fractal_dimension.html) · [`geodesic_dome`](https://furuse.work/ops/3d/polyhedron/geodesic_dome.html) · [`graph_degree_table`](https://furuse.work/ops/conngraph/stats/graph_degree_table.html) · [`ifs_fractal`](https://furuse.work/ops/math/construct/ifs_fractal.html) · [`ifs_similarity_dimension`](https://furuse.work/ops/math/construct/ifs_similarity_dimension.html) · [`neighbour_index_gaps`](https://furuse.work/ops/math/construct/neighbour_index_gaps.html) · [`phyllotaxis_pattern`](https://furuse.work/ops/math/construct/phyllotaxis_pattern.html) · [`space_filling_curve`](https://furuse.work/ops/math/construct/space_filling_curve.html)

## No.2026.140 —— うなりは一つ ―― 干渉縞と印刷のモアレは同じ数学である

[![うなりは一つ ―― 干渉縞と印刷のモアレは同じ数学である](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beats_fringes_and_screens/01_membrane_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beats_fringes_and_screens/01_membrane.png)

*↑ **うなりは一つ ―― 干渉縞と印刷のモアレは同じ数学である** ―― 二重スリットの縞と、2 版を重ねた網点のモアレは教科書では別の章に載っているが、どちらも「2 つの周期構造の周波数ベクトルの差」で式は 1 本しかない —— その 1 本を両側から確かめた。★矩形膜の固有値は π²(m²/a² + n²/b²) で、正方膜の 8 モードが**最大差 0.00e+00** で一致(よく書かれる mnπ は積の式で、縮退の重複 5・5・10・10 まで見ると完全に別物)。節線の本数 m−1 / n−1 は整数なので丸めの余地がない。★円膜の節円は **J₀ の零点 / k** にある(J′₀ の零点は**腹** —— 取り違えると op が誤っているように見え、一度読み違えた)。★縞間隔 λD/d は**作った op とは別の op** が測り返して 4 設定すべて比 0.998〜1.003。縞が 3 本入らない設定は拒む。★回折格子は既存 grating_wavelengths で逆算して **550.000000 nm** に戻り、伝播しない次数は角度を捏造しない。デューティ 50 % の矩形格子では**偶数次が消え**(矩形波のフーリエ係数が 0)、3 次 / 1 次の強度比は sinc(m/2)² の 1/9(実測 0.1140)。★★モアレの周期は**描く前に**閉形式で出し、重ねた絵の FFT で測り返して比 0.948〜0.986 —— ★探す範囲を切らないと**スクリーン自身の山**(どの角度でも 16.7 px = 1/f)を拾って「予言と全然合わない」と読める。同じスクリーン同士は inf を返さず拒む。★網点が捨てたのは階調で、**保ったのは局所の平均濃度**(4 周期の窓で平均すると元の濃淡に戻り、平均絶対差 0.0517)。★彫版線のインク率は w/d の閉形式と 4 段すべて**差 0.0000**。ハッチの向きは既存 structure_tensor_orientation が決め、向きが構成で分かっている縞で 0.0〜0.3° のずれ(★f_min を切らないと線ではなく**濃淡の包絡**を拾って 90° ずれて見える)。★Lloyd のエネルギーは**既存 stipple_energy** が測って単調減少、セル平均は L2 最適でセル 10 個を全数走査して反例 0。*

[![(m, n) モードの節線は縦 m−1 本・横 n−1 本。円膜の節円は J₀ の零点 / k にある —— J′₀ の零点は腹の位置であって節ではない(取り違えると op が誤っているように見える)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beats_fringes_and_screens/02_nodal_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beats_fringes_and_screens/02_nodal.png)

*↑ 測定の図 ―― (m, n) モードの節線は縦 m−1 本・横 n−1 本。円膜の節円は J₀ の零点 / k にある —— J′₀ の零点は腹の位置であって節ではない(取り違えると op が誤っているように見える)。*

[![縞間隔は λD/d。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beats_fringes_and_screens/03_fringes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beats_fringes_and_screens/03_fringes.png)

*↑ 縞間隔は λD/d。*

[![★デューティ 50 % の矩形格子は**偶数次が消える**(矩形波のフーリエ係数が偶数調波で 0)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beats_fringes_and_screens/05_grating_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beats_fringes_and_screens/05_grating.png)

*↑ ★デューティ 50 % の矩形格子は**偶数次が消える**(矩形波のフーリエ係数が偶数調波で 0)。*

[![平均絶対差 0.0517。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beats_fringes_and_screens/08_halftone_tone_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beats_fringes_and_screens/08_halftone_tone.png)

*↑ 平均絶対差 0.0517。*

[![Lloyd 反復でセルが等エネルギーに近づく。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beats_fringes_and_screens/11_mosaic_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beats_fringes_and_screens/11_mosaic.png)

*↑ Lloyd 反復でセルが等エネルギーに近づく。*

```
py -3.11 examples/poc_beats_fringes_and_screens.py
```

ソース: [examples/poc_beats_fringes_and_screens.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_beats_fringes_and_screens.py)

この回が作った図は全部で **13 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_beats_fringes_and_screens)

使用 op(ノートへ): [`engrave_lines`](https://furuse.work/ops/printpath/npr/engrave_lines.html) · [`fraunhofer_pattern`](https://furuse.work/ops/optics/wave/fraunhofer_pattern.html) · [`grating_wavelengths`](https://furuse.work/ops/optics/appearance/grating_wavelengths.html) · [`halftone_moire_period`](https://furuse.work/ops/printpath/npr/halftone_moire_period.html) · [`halftone_screen`](https://furuse.work/ops/printpath/npr/halftone_screen.html) · [`hatch_field`](https://furuse.work/ops/printpath/npr/hatch_field.html) · [`mosaic_tiles_render`](https://furuse.work/ops/printpath/npr/mosaic_tiles_render.html) · [`mosaic_tiles_sites`](https://furuse.work/ops/printpath/npr/mosaic_tiles_sites.html) · [`stipple_energy`](https://furuse.work/ops/printpath/stroke/stipple_energy.html) · [`wave_fringe_period`](https://furuse.work/ops/math/wave/wave_fringe_period.html) · [`wave_grating_orders`](https://furuse.work/ops/math/wave/wave_grating_orders.html) · [`wave_membrane_mode`](https://furuse.work/ops/math/wave/wave_membrane_mode.html) · [`wave_mode_frequencies`](https://furuse.work/ops/math/wave/wave_mode_frequencies.html) · [`wave_nodal_lines`](https://furuse.work/ops/math/wave/wave_nodal_lines.html) · [`wave_two_slit`](https://furuse.work/ops/math/wave/wave_two_slit.html)

## No.2026.141 —— 絵では確かめられないもの ―― 力学系と極小曲面を定義と恒等式で採点する

[![絵では確かめられないもの ―― 力学系と極小曲面を定義と恒等式で採点する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_what_a_picture_cannot_check/02_lorenz_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_what_a_picture_cannot_check/02_lorenz.png)

*↑ **絵では確かめられないもの ―― 力学系と極小曲面を定義と恒等式で採点する** ―― ローレンツ・アトラクタの図は積分器が 1 次でも 4 次でも蝶に見え、極小曲面の図は平均曲率が 0 でなくてもきれいに見える —— 「見て分かる」が一切効かない族なので採点を全部絵の外から取った。★線形系の厳密解は expm(At)x₀ で、刻み半分にすると RK4 の誤差は**比 16.0 / 16.0 / 16.0**(4 次)、対照群のオイラー法は 2.08 / 2.04 / 2.02(1 次)、同じ dt=0.01 で 2.02e-02 対 3.33e-10。★★リアプノフ指数の**和**はトレース恒等式で厳密に −(σ+1+β) = −13.666667、実測 −13.666664(差 2.57e-06)—— 指数を出す手続き(接流 + QR)とは独立。λ₁ = 0.9142(公表値 0.906)、保存系の対照群は和 4.87e-15。★周期倍分岐は r = 3 と 1+√6 が厳密で実測 2.999401 / 3.449260、δ = 4.7485(文献値 4.6692)。★**残差を隠さない**: 分岐点での収束は代数的なので有限の burn-in では必ず手前に見え、burn 2,000 → 20,000 で誤差が **10.9 倍縮む** —— 門は「誤差が小さい」ではなく「伸ばすと置いていった分だけ縮む」で置いた。★★相関次元は円 1.0061・カントール 0.6408 だが平面は 1.8789(真値 2)—— 偏りの正体を**探し当ててから書いた**: 点数を 400 → 3,000 にしても**動かず**、正体は**べき乗則を見る半径の窓**(既定は対距離の 1〜25 パーセンタイルで、上端が箱の端に当たり相関和が飽和する)。窓を狭めると 1.887 → 2.050。★★場の**発散は厳密に tr(A)・渦度は A₁₀−A₀₁** で、それを測るのは**PIV 族の既存 op** —— 4 通りすべて 1e-6 未満、ローレンツの xy 断面は −σ−1 = −11.000000。★円を中心線にした管はトーラスなので体積 2π²Rr²・表面積 4π²Rr が解析解で、既存 mesh_volume / mesh_area が比 0.997 / 0.999。まっすぐな区間を含む曲線でも半径が 0.150000000000 で崩れない(平行移動フレーム)。★★極小曲面は |H| 中央値 0.00002〜0.00014 で、対照群の単位球 1.00004・半径 1 の円柱 0.50000 —— 門が素通しでない証拠。カテノイドとヘリコイドはガウス曲率が一致するが(等長)それは**必要条件にすぎない**。★ジャイロイドは体積比 0.499928 / 0.499981 / 0.499991(体心反転の対称性)だが、**節面近似の残差は隠さず出す**(|H| / 主曲率スケール = 0.1250)。*

[![厳密解は expm(At)x₀ なので、誤差は積分器の次数をそのまま出す。★どちらの軌道も絵にすると同じ円に見える —— 絵では次数は確かめられない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_what_a_picture_cannot_check/01_rk4_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_what_a_picture_cannot_check/01_rk4.png)

*↑ 測定の図 ―― 厳密解は expm(At)x₀ なので、誤差は積分器の次数をそのまま出す。★どちらの軌道も絵にすると同じ円に見える —— 絵では次数は確かめられない。*

[![Σλ = -13.66666、閉形式 −(σ+1+β) = -13.66667(差 2.6e-06)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_what_a_picture_cannot_check/03_lyapunov_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_what_a_picture_cannot_check/03_lyapunov.png)

*↑ Σλ = -13.66666、閉形式 −(σ+1+β) = -13.66667(差 2.6e-06)。*

[![円 1・平面 2・カントール log2/log3 = 0.6309。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_what_a_picture_cannot_check/05_dimension_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_what_a_picture_cannot_check/05_dimension.png)

*↑ 円 1・平面 2・カントール log2/log3 = 0.6309。*

[![同じ op で両方を測っている。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_what_a_picture_cannot_check/07_poincare_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_what_a_picture_cannot_check/07_poincare.png)

*↑ 同じ op で両方を測っている。*

[![「これは極小曲面だ」という主張を、**作り方を知らない op が採点する**。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_what_a_picture_cannot_check/09_minimal_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_what_a_picture_cannot_check/09_minimal.png)

*↑ 「これは極小曲面だ」という主張を、**作り方を知らない op が採点する**。*

```
py -3.11 examples/poc_what_a_picture_cannot_check.py
```

ソース: [examples/poc_what_a_picture_cannot_check.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_what_a_picture_cannot_check.py)

この回が作った図は全部で **11 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_what_a_picture_cannot_check)

使用 op(ノートへ): [`curve3d_tube_mesh`](https://furuse.work/ops/3d/surface/curve3d_tube_mesh.html) · [`dynsys_bifurcation_map`](https://furuse.work/ops/math/dynsys/dynsys_bifurcation_map.html) · [`dynsys_correlation_dimension`](https://furuse.work/ops/math/dynsys/dynsys_correlation_dimension.html) · [`dynsys_lyapunov_spectrum`](https://furuse.work/ops/math/dynsys/dynsys_lyapunov_spectrum.html) · [`dynsys_poincare_section`](https://furuse.work/ops/math/dynsys/dynsys_poincare_section.html) · [`gyroid_isosurface`](https://furuse.work/ops/3d/surface/gyroid_isosurface.html) · [`gyroid_solid_mask`](https://furuse.work/ops/3d/surface/gyroid_solid_mask.html) · [`mean_curvature`](https://furuse.work/ops/3d/curvature/mean_curvature.html) · [`mesh_area`](https://furuse.work/ops/3d/mesh_process/mesh_area.html) · [`mesh_volume`](https://furuse.work/ops/3d/mesh_process/mesh_volume.html) · [`minimal_surface`](https://furuse.work/ops/3d/surface/minimal_surface.html) · [`minimal_surface_bend`](https://furuse.work/ops/3d/surface/minimal_surface_bend.html) · [`ode_flow_states`](https://furuse.work/ops/math/dynsys/ode_flow_states.html) · [`ode_vector_field_grid`](https://furuse.work/ops/math/dynsys/ode_vector_field_grid.html) · [`piv_divergence`](https://furuse.work/ops/piv/field/piv_divergence.html) · [`piv_flow_magnitude`](https://furuse.work/ops/piv/field/piv_flow_magnitude.html) · [`piv_vorticity`](https://furuse.work/ops/piv/field/piv_vorticity.html) · [`principal_curvatures`](https://furuse.work/ops/3d/curvature/principal_curvatures.html) · [`vertex_curvature`](https://furuse.work/ops/3d/mesh_process/vertex_curvature.html)

## No.2026.143 —— 無限に描き続ける絵を、恒等式で採点する

[![無限に描き続ける絵を、恒等式で採点する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_illusions_and_perpetual_drawing/07_apollonian_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_illusions_and_perpetual_drawing/07_apollonian.png)

*↑ **無限に描き続ける絵を、恒等式で採点する** ―― **絵では確かめられないものを、閉形式と整数不変量で採点する。** この回の素材は「止めなければ終わらない」生成器 —— 規則 90 の一次元セルオートマトン、ラングトンの蟻、アポロニウスの円詰め、カオスゲーム、バーンズリーのシダ、流れ場、反応拡散、プラズマ。どれも**絵を見ても正しさが分からない**(「もっとフラクタルらしく」見えるだけ)ので、**絵と独立に成り立つ式**を同じ op から出して採点する。★★芯 1: **規則 90 の第 n 行は二項係数の偶奇そのもの** —— 残差 **0.00e+00**(リュカの定理の帰結「C(n,k) が奇 ⟺ (n & k) == k」を使う。二項係数を直接積むと C(62,31)·31 が int64 を黙って溢れる)。★★芯 2: **ラングトンの蟻の高速道路は周期 104 で同じ斜めの変位を繰り返し、104 歩あたり正味ちょうど 12 マスを黒くする** ——どちらも残差 **0.00e+00** の整数不変量。★最初「104 歩で 52 マス」と書いて**外した**: 実測 0.114 マス/歩 と合わず、測り直すと 12/104 = 0.11538 だった(周期の中で塗っては消すので、正味はずっと少ない)。★★芯 3: **互いに接する 4 円の曲率はデカルトの円定理 (Σk)² = 2Σk² を厳密に満たす** (残差 **1.19e-16**)。★★さらに**描いた円が本当に接しているか**を別に測る(残差 **9.20e-07**)—— 平方根の枝を選び損ねると、絵としては「フラクタルっぽい」まま**外へ逃げる円の鎖**が出る(実際に出した)。見た目では欠陥と分からない。★★芯 4: **流れ場は ψ の回転として作るので発散が恒等的に 0**(残差 7.0e-17)、**餌も死も無い反応拡散は総量が保存**、**ダイヤモンド–スクエア法は 4 隅を書き換えない** —— どれも数値解法が壊れていれば真っ先に崩れる量。★★芯 5: **継ぎ目の無い循環動画は「最後に頭へ戻す」で作らない** —— 時間依存の量をすべて θ の関数にして θ を 0→2π 回すと、t = T は t = 0 と**同じ式**になる。継ぎ目は消したのではなく**最初から存在しない**。★**測る側の偏りも 1 件入れてある**: ミュラー・リヤーの 2 本は厳密に等長なのに、素朴な長さ計測は **223 画素と 225 画素**と答える。しかも矢羽根が無くても **223 画素**(真値 220 より 3 画素長い)—— 反エイリアスの裾を「黒い画素」として数えているから。★ここでも**外した**: 「矢羽根が長いほど偏る」と読んだが、20 px で 2 画素に達したあと 80 px まで**動かない**。偏りを作るのは長さではなく、**端に裾が乗るかどうか**だけ。★★**この回で錯視の描画を落とした**: カフェウォールやカニッツァの検査は「厳密に水平に引いた目地が水平だ」「平坦に塗ったマスが平坦だ」という**定数を置いて定数を読み返すだけ**で、間に変換が 1 つも無く、測定の能力を何も試していなかった(同義反復)。絵の側も直線と矩形を引いているだけで、この箱の力を示さない。**新しい op は 1 つも足していない。** 検査 18 件・図 16 枚(動く図 1 枚を含む)。*

[![ミュラー・リヤー。**2 本の軸は厳密に等長**(矢羽根を外すと画素単位で同一)。ところが矢羽根を付けた図で「行の黒い区間」を素朴に測ると、真値 220 に対し **223 画素と 225 画素**になります。★これは知覚の話ではなく**測](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_illusions_and_perpetual_drawing/01_muller_lyer_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_illusions_and_perpetual_drawing/01_muller_lyer_bias.png)

*↑ 測定の図 ―― ミュラー・リヤー。**2 本の軸は厳密に等長**(矢羽根を外すと画素単位で同一)。ところが矢羽根を付けた図で「行の黒い区間」を素朴に測ると、真値 220 に対し **223 画素と 225 画素**になります。★これは知覚の話ではなく**測る側の偏り**で、矢羽根の裾が軸の端に乗るのが原因です。次の図が、その偏りの量と向きです。*

[![真値はどの点でも **220 画素で等長**。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_illusions_and_perpetual_drawing/02_bias_vs_head_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_illusions_and_perpetual_drawing/02_bias_vs_head.png)

*↑ 真値はどの点でも **220 画素で等長**。*

[![ラングトンの蟻を 21000 歩。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_illusions_and_perpetual_drawing/05_langtons_ant_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_illusions_and_perpetual_drawing/05_langtons_ant.png)

*↑ ラングトンの蟻を 21000 歩。*

[![バーンズリーのシダ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_illusions_and_perpetual_drawing/09_fern_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_illusions_and_perpetual_drawing/09_fern.png)

*↑ バーンズリーのシダ。*

[![ダイヤモンド–スクエア法(1980 年代の「プラズマ」)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_illusions_and_perpetual_drawing/12_plasma_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_illusions_and_perpetual_drawing/12_plasma.png)

*↑ ダイヤモンド–スクエア法(1980 年代の「プラズマ」)。*

[![**継ぎ目の無い循環動画**。最後のコマから最初のコマへ戻るところに、切れ目がありません。作り方が要点で、「最後に頭へ戻す」のではなく、**時間依存の量をすべてθ の関数にして θ を 0→2π 回す**と、t=T は t=0 と同じ式にな](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_illusions_and_perpetual_drawing/14_loop.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_illusions_and_perpetual_drawing/14_loop.gif)

*↑ 動く図 ―― **継ぎ目の無い循環動画**。最後のコマから最初のコマへ戻るところに、切れ目がありません。作り方が要点で、「最後に頭へ戻す」のではなく、**時間依存の量をすべてθ の関数にして θ を 0→2π 回す**と、t=T は t=0 と同じ式になります —— 継ぎ目は最初から存在しません。*

```
py -3.11 examples/poc_illusions_and_perpetual_drawing.py
```

ソース: [examples/poc_illusions_and_perpetual_drawing.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_illusions_and_perpetual_drawing.py)

この回が作った図は全部で **16 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_illusions_and_perpetual_drawing)

使用 op(ノートへ): [`illusion_muller_lyer`](https://furuse.work/ops/generative/illusion/illusion_muller_lyer.html) · [`perpetual_apollonian`](https://furuse.work/ops/generative/perpetual/perpetual_apollonian.html) · [`perpetual_chaos_game`](https://furuse.work/ops/generative/perpetual/perpetual_chaos_game.html) · [`perpetual_elementary_ca`](https://furuse.work/ops/generative/perpetual/perpetual_elementary_ca.html) · [`perpetual_flow_field`](https://furuse.work/ops/generative/perpetual/perpetual_flow_field.html) · [`perpetual_identities`](https://furuse.work/ops/generative/perpetual/perpetual_identities.html) · [`perpetual_ifs_attractor`](https://furuse.work/ops/generative/perpetual/perpetual_ifs_attractor.html) · [`perpetual_loop`](https://furuse.work/ops/generative/loop/perpetual_loop.html) · [`perpetual_loop_seam`](https://furuse.work/ops/generative/loop/perpetual_loop_seam.html) · [`perpetual_plasma`](https://furuse.work/ops/generative/perpetual/perpetual_plasma.html) · [`perpetual_reaction_diffusion`](https://furuse.work/ops/generative/perpetual/perpetual_reaction_diffusion.html) · [`perpetual_render`](https://furuse.work/ops/generative/stream/perpetual_render.html) · [`perpetual_state`](https://furuse.work/ops/generative/stream/perpetual_state.html) · [`perpetual_step`](https://furuse.work/ops/generative/stream/perpetual_step.html) · [`perpetual_ten_print`](https://furuse.work/ops/generative/perpetual/perpetual_ten_print.html) · [`perpetual_truchet`](https://furuse.work/ops/generative/perpetual/perpetual_truchet.html)

## No.2026.144 —— 錯視で測定器を健診する ―― キャリパーが外すのはどこで、なぜか

[![錯視で測定器を健診する ―― キャリパーが外すのはどこで、なぜか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_calipers_under_illusion/01_caliper_on_cafe_wall_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_calipers_under_illusion/01_caliper_on_cafe_wall.png)

*↑ **錯視で測定器を健診する ―― キャリパーが外すのはどこで、なぜか** ―― 錯視は「答えの分かっている図」である。だから**測られる側**ではなく**測る側**を採点できる —— Fullseye は真値つきの絵を作る op と HALCON 流のサブピクセル測定器を同じ箱に持っているので、この採点が 1 本の走行で閉じる。**新しい op は 1 つも足していない。**★カフェウォールの目地に直線の計測オブジェクトを当てると、傾きは **厳密に 0.0 度**・残差 rms も **0.0**(真値 0)—— 目が「傾いている」と言い張る図で、測る側は 1 ulp も外さない。★★ところが**探針 1 枚では足りなかった**: ずらし量 0.25 だけで試して「測定器は決して動かない」と書いたが、ずらし量 5 通り × 探索半幅 4 通りの 20 通りを全部測ると、**探索半幅が目地の帯幅 8 px に届く 10/16 px のとき、ずらし量 0.125 と 0.375 でだけ 0.1429 度傾く**(目地の反対側の境界を掴む)。0.25 はたまたま外れない側だった。★★★そして**外したことは答えでなく残差に出る** —— 0.1429 度は数字だけ見れば「ほぼ 0」で通ってしまうが、rms は **0.00 → 1.70** と桁で動き、角度 0 ⇔ rms 0 が 20 通り全部で一致する。**門は答えでなく残差に置く。**★ミュラー・リヤーでは**測定器も外す。ただし目とは別の理由で** —— 矢羽根は「長く見せる」だけでなく測定線の上に余計なエッジを置くので(2 本 → 4 本)、測定器は軸ではなく**矢羽根のストロークを対にする**(幅 5.701 px)。★★想定幅 220 px を**宣言して** fuzzy_measure_pairing に測らせると、適合度は矢羽根なし 0.9988 に対し矢羽根あり **0.0225** —— 間違った値を返すのではなく「想定幅の構造は見つからない」と**数で申告する**。測り方を宣言した分だけ、失敗が静かな誤りから見える拒否に変わる。★矢羽根が無くても答えは 223.777 px で真値 220 と合わないが、長さを 140〜300 px に振るとずれは **+3.777 px 一定**(振れ幅 0.0000 px)—— 比例なら倍率の誤り、一定なら**端の定義**のずれで、「線分の長さ」と「外側エッジ間の距離」は線幅ぶん違う量である。引けば真値に戻る。★★エビングハウスでは円の計測オブジェクトが 2 円の半径を **29.996525 px と 29.996525 px**(差 **2.5e-12 px**、真値 0)と返す。どちらも指定の 30 px より 0.0035 px 小さく、中心も −0.5076 px ずれるが、**系統誤差は両方に同じだけ乗るので差を取ると消える**。★ツェルナーでは7 本すべてが最大 |傾き| **4.3e-04 度**(幅 520 px を渡って 0.0039 px)。動いたのは答えではなく**証拠の数**で、ハッチの向きが 1 本おきに反転するため採用点が 61 点中 **13 と 19** を交互に取る —— 「測れた」と「よく測れた」は別の量。★★ポッゲンドルフでは**測定器が外す**: 共線のはずの 2 区間で角度が **0.450 度**違う。原因は極性が塊で交互すること(41 点が 9 個の塊、+18 / −23)—— **細い線には 2 つのエッジがあり、「線の位置」はどちらか(あるいは中心か)を言うまで定義されない**。両エッジを対にして中心を取ると角度差 0.450 → **0.115 度**、rms 2.07 → 0.10/0.39 まで下がるが **0 にはならない**(帯の縁の細い縦線と画像の端が測定線に掛かる)—— そこまでは追い込んでいない、というのが正直な状態。検査 24 件・図 16 枚。*

[![`measure_length` は「参照線の法線方向に何 px 探すか」。3 px から 16 px まで振っても角度は **0.0 のまま**で、採用された点も **4 通りとも 41 点**(半幅 3 px, 半幅 6 px, 半幅 ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_calipers_under_illusion/02_cafe_wall_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_calipers_under_illusion/02_cafe_wall_sweep.png)

*↑ 測定の図 ―― `measure_length` は「参照線の法線方向に何 px 探すか」。3 px から 16 px まで振っても角度は **0.0 のまま**で、採用された点も **4 通りとも 41 点**(半幅 3 px, 半幅 6 px, 半幅 10 px, 半幅 16 px)。目地は一様なグレーなので、探索を広げても拾える点は増えません。★これは**何も起きなかった図**です ---- はじめこの図説に「半幅を変えると点の数が変わる」と書きましたが、**生成された本文を読み返すとデータと違っていました**。証拠の数が実際に動く例は第 5 章のツェルナー(61 点中 13 と 19)のほうです。*

[![ずらし量 5 通り × 探索半幅 4 通りの **20 通り全部**を測ったもの。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_calipers_under_illusion/03_cafe_wall_grid_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_calipers_under_illusion/03_cafe_wall_grid.png)

*↑ ずらし量 5 通り × 探索半幅 4 通りの **20 通り全部**を測ったもの。*

[![青い横罫が測定線(`gen_measure_rectangle2`)、橙の縦罫が `measure_pos` が見つけたサブピクセルエッジです。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_calipers_under_illusion/06_muller_caliper_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_calipers_under_illusion/06_muller_caliper.png)

*↑ 青い横罫が測定線(`gen_measure_rectangle2`)、橙の縦罫が `measure_pos` が見つけたサブピクセルエッジです。*

[![エビングハウス錯視に**円の計測オブジェクト**(`add_metrology_object_circle_measure`)を当てたもの。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_calipers_under_illusion/10_ebbinghaus_circle_caliper_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_calipers_under_illusion/10_ebbinghaus_circle_caliper.png)

*↑ エビングハウス錯視に**円の計測オブジェクト**(`add_metrology_object_circle_measure`)を当てたもの。*

[![7 本の長い線について、**測った傾き**(真値 0)と**採用されたエッジ点の数**を重ねたもの。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_calipers_under_illusion/13_zollner_angles_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_calipers_under_illusion/13_zollner_angles.png)

*↑ 7 本の長い線について、**測った傾き**(真値 0)と**採用されたエッジ点の数**を重ねたもの。*

```
py -3.11 examples/poc_calipers_under_illusion.py
```

ソース: [examples/poc_calipers_under_illusion.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_calipers_under_illusion.py)

この回が作った図は全部で **16 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_calipers_under_illusion)

使用 op(ノートへ): [`add_metrology_object_circle_measure`](https://furuse.work/ops/measure1d/model/add_metrology_object_circle_measure.html) · [`add_metrology_object_line_measure`](https://furuse.work/ops/measure1d/model/add_metrology_object_line_measure.html) · [`apply_metrology_model`](https://furuse.work/ops/measure1d/apply/apply_metrology_model.html) · [`create_metrology_model`](https://furuse.work/ops/measure1d/model/create_metrology_model.html) · [`edge_points`](https://furuse.work/ops/3d/edges/edge_points.html) · [`fuzzy_measure_pairing`](https://furuse.work/ops/measure1d/caliper/fuzzy_measure_pairing.html) · [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`illusion_cafe_wall`](https://furuse.work/ops/generative/illusion/illusion_cafe_wall.html) · [`illusion_ebbinghaus`](https://furuse.work/ops/generative/illusion/illusion_ebbinghaus.html) · [`illusion_ground_truth`](https://furuse.work/ops/generative/illusion/illusion_ground_truth.html) · [`illusion_muller_lyer`](https://furuse.work/ops/generative/illusion/illusion_muller_lyer.html) · [`illusion_poggendorff`](https://furuse.work/ops/generative/illusion/illusion_poggendorff.html) · [`illusion_zollner`](https://furuse.work/ops/generative/illusion/illusion_zollner.html) · [`measure_pairs`](https://furuse.work/ops/measure1d/caliper/measure_pairs.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html)

### 3-D 形状ウィング ―― 合わせてから測ると、合わせた分だけ欠陥が消える

点群とメッシュの仕事は、2-D の仕事と 1 つだけ決定的に違います。**測る前に姿勢を合わせる**という段が入ることです。合わせる段は、測りたいずれを最小にする向きに形を回します。だから欠陥が大きいほど、合わせの段が欠陥を吸い、残差は小さく、部品は良品に見えます。この部屋の展示は、その吸われた分を数える試みです。

真値はすべて式で置いてあります。立体は解析的な面のブール演算で作り、体積・表面積・肉厚・曲率が式で分かるものを選びます。変形は既知の場(局所のへこみ、反り、法線方向の一定の摩耗)、姿勢は既知の回転と並進、点群は面からの一様サンプルに既知の密度・雑音・欠測を掛けたものです。だから「合わせの誤差」と「形の誤差」を別々に持てます。

3-D 特有の落とし穴も、この部屋では別々に数えます。最近傍距離は雑音があると必ず正へ偏る(片側だけ数える量だから)、法線の符号は下請けの都合で決まる、密度を変えると距離の尺度そのものが動く、対称な形は姿勢が一意に決まらない。どれも 1 つの数字に畳んだ瞬間に見えなくなります。

## No.2026.054 —— 電池セルの内部劣化を CT で測る ―― 膨れは外から見え、原因は中にある

[![電池セルの内部劣化を CT で測る ―― 膨れは外から見え、原因は中にある](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/02_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/02_scene.png)

*↑ **電池セルの内部劣化を CT で測る ―― 膨れは外から見え、原因は中にある** ―― 角形リチウムイオンセルの積層電極とアルミ缶を真値つきで組み、劣化を既知の場(一様膨れ・局所膨れ・層間ガス空隙・電極ずれ)として与えて、順投影 → ビームハードニング → 光子雑音 → FBP 再構成という実際の撮像を通してから測った。電極が 10 % 膨れても外形に出るのは 29.4 % だけで、しかも中央のノギスは体積等価な平均の 3.6 倍(+0.235 対 +0.066 mm)を読む。外形のふくらみを揃えた 3 つのセルは缶の高さが 0.000 mm しか違わないのに、内部指標は空隙率 0.00 対 5.20 %、層の平面度 0.0156 対 0.0784 mm で分かれ、その内部指標が壊れる崖は電極厚 0.200 mm ではなく層間の隙間 0.120 mm が決めた(voxel/層厚 = 0.30、標本化定理からの予測 0.80 は外れ)。*

[![真正面(0 度)なら空隙の影までは見える。ただし奥行きに積算されているので厚みも深さも出ない。22 度傾けると層の縞そのものが重なって消える —— 投影では姿勢が結果を決めてしまう。だから断層に落とす。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/01_xray_projection_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/01_xray_projection.png)

*↑ 測定の図 ―― 真正面(0 度)なら空隙の影までは見える。ただし奥行きに積算されているので厚みも深さも出ない。22 度傾けると層の縞そのものが重なって消える —— 投影では姿勢が結果を決めてしまう。だから断層に落とす。*

[![端板は周辺で固定なので中央だけが出る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/03_outer_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/03_outer_profile.png)

*↑ 端板は周辺で固定なので中央だけが出る。*

[![一様膨れは平らなまま上がる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/06_flatness_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/06_flatness.png)

*↑ 一様膨れは平らなまま上がる。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/10_void_slices_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/10_void_slices.png)

*↑ この回の図*

[![空隙体積は崖の手前から単調に痩せる(部分体積効果)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/13_sweep_resolution_err_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/13_sweep_resolution_err.png)

*↑ 空隙体積は崖の手前から単調に痩せる(部分体積効果)。*

```
py -3.11 examples/poc_battery_ct_degradation.py
```

ソース: [examples/poc_battery_ct_degradation.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_battery_ct_degradation.py)

この回が作った図は全部で **16 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_battery_ct_degradation)

使用 op(ノートへ): [`beam_hardening_apply`](https://furuse.work/ops/tomography/artifact/beam_hardening_apply.html) · [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`fbp_volume`](https://furuse.work/ops/tomography/volume/fbp_volume.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`plane_sdf`](https://furuse.work/ops/3d/sdf_csg/plane_sdf.html) · [`projection_angles`](https://furuse.work/ops/tomography/layout/projection_angles.html) · [`radon_volume`](https://furuse.work/ops/tomography/volume/radon_volume.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`ring_artifact_apply`](https://furuse.work/ops/tomography/artifact/ring_artifact_apply.html) · [`sdf_intersect`](https://furuse.work/ops/3d/sdf_csg/sdf_intersect.html) · [`sdf_subtract`](https://furuse.work/ops/3d/sdf_csg/sdf_subtract.html) · [`sdf_to_occupancy`](https://furuse.work/ops/3d/transform/sdf_to_occupancy.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`vol_bounding_box`](https://furuse.work/ops/3d/domain/vol_bounding_box.html) · [`vol_edge_probe`](https://furuse.work/ops/3d/probe/vol_edge_probe.html) · [`vol_fft_lowpass`](https://furuse.work/ops/3d/frequency/vol_fft_lowpass.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_profile_line`](https://furuse.work/ops/3d/probe/vol_profile_line.html) · [`vol_region_props`](https://furuse.work/ops/3d/regionprops/vol_region_props.html) · [`vol_resize`](https://furuse.work/ops/3d/geom_transform/vol_resize.html) · [`vol_wall_thickness`](https://furuse.work/ops/3d/probe/vol_wall_thickness.html)

## No.2026.056 —— 鳥瞰図への多センサ融合 —— 画像では合格の校正が、遠くでは長さになる

[![鳥瞰図への多センサ融合 —— 画像では合格の校正が、遠くでは長さになる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/01_scene_bev_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/01_scene_bev.png)

*↑ **鳥瞰図への多センサ融合 —— 画像では合格の校正が、遠くでは長さになる** ―― 解析的な街路(先行トラック + 互いの影に 1 台ずつ隠れる遠方車)を作り、左ミラーの LiDAR と右ミラーの深度カメラを共通の鳥瞰格子へ融合して、外部パラメータの誤差を回転・並進・時刻ずれに分けて掃引した。融合の占有 IoU 0.7033 は単センサの最良 0.5417 を上回るが、その利得はすべて視界の相補性から来ている。再投影 1 px は 22 m 先で 0.083 m に化け、崖はセル 0.2 m ではなく車幅で決まり(半分の点がセルを跨いでも IoU は 5.8 % しか落ちない)、yaw 3 度で融合は単センサに負ける。*

[![横に 1.80 m 離した 2 センサの「自由と言い切れた領域」。青い帯が LiDAR にしか見えない所、橙の帯がカメラにしか見えない所、灰色は両方。白は真値の障害物。22 m の 2 台は**互いの影に 1 台ずつ入っている**。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/02_shadow_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/02_shadow_map.png)

*↑ 測定の図 ―― 横に 1.80 m 離した 2 センサの「自由と言い切れた領域」。青い帯が LiDAR にしか見えない所、橙の帯がカメラにしか見えない所、灰色は両方。白は真値の障害物。22 m の 2 台は**互いの影に 1 台ずつ入っている**。*

[![画像 320 x 240 px、焦点距離 265 px。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/03_reprojection_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/03_reprojection.png)

*↑ 画像 320 x 240 px、焦点距離 265 px。*

[![誤差はカメラ側の外部パラメータにだけ入れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/04_conditions_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/04_conditions.png)

*↑ 誤差はカメラ側の外部パラメータにだけ入れる。*

[![LiDAR は 22 m の車を 1 セルも返せない(先行車の陰)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/06_fusion_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/06_fusion_map.png)

*↑ LiDAR は 22 m の車を 1 セルも返せない(先行車の陰)。*

[![水平の 2 本は単センサのゼロ点。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/08_cliff_rotation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/08_cliff_rotation.png)

*↑ 水平の 2 本は単センサのゼロ点。*

```
py -3.11 examples/poc_bev_sensor_fusion.py
```

ソース: [examples/poc_bev_sensor_fusion.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bev_sensor_fusion.py)

この回が作った図は全部で **9 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_bev_sensor_fusion)

使用 op(ノートへ): [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`closing_circle`](https://furuse.work/ops/2d/region/closing_circle.html) · [`depth_to_points`](https://furuse.work/ops/3d/transform/depth_to_points.html) · [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`fill_up`](https://furuse.work/ops/2d/region/fill_up.html) · [`fuse`](https://furuse.work/ops/3d/tsdf_fusion/fuse.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`occupancy_grid`](https://furuse.work/ops/3d/occupancy/occupancy_grid.html) · [`project_points`](https://furuse.work/ops/3d/render/project_points.html) · [`sdf_to_occupancy`](https://furuse.work/ops/3d/transform/sdf_to_occupancy.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`voxel_grid_downsample`](https://furuse.work/ops/3d/preprocess/voxel_grid_downsample.html) · [`voxel_iou`](https://furuse.work/ops/3d/metrics/voxel_iou.html)

## No.2026.058 —— CAD と実測点群の差分検査 ―― 合わせた分だけ欠陥が消え、無い所にへこみが出る

[![CAD と実測点群の差分検査 ―― 合わせた分だけ欠陥が消え、無い所にへこみが出る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/01_scene.png)

*↑ **CAD と実測点群の差分検査 ―― 合わせた分だけ欠陥が消え、無い所にへこみが出る** ―― 解析形状の機械部品に、局所へこみ・反り・摩耗を法線方向の既知量として仕込み、既知の姿勢・雑音・欠測つきの実測点群を合成した。合わせてから符号付き偏差と公差外面積を測ると、局所へこみの読みは 3.7 % しか薄まらないのに、真値が 1.2 µm しかない部品中央に深さ 121 µm の存在しないへこみが出る(閉形式の予測 -120 µm)。消えるか化けるかは剛体 6 自由度が吸える偏差場に似ているかどうかで決まり、稜線では最近傍が隣の面へ飛んで、欠陥ゼロの対照でも 66.5 mm^2 の偽の公差外領域が出た。*

[![真の姿勢を与えた最終行が推定器そのものの床。点-面 ICP との差は姿勢ではなく datum の取り方の差。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/02_methods_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/02_methods.png)

*↑ 測定の図 ―― 真の姿勢を与えた最終行が推定器そのものの床。点-面 ICP との差は姿勢ではなく datum の取り方の差。*

[![3 枚目が一様に色づくのが第 6 章の主張 —— 位置合わせが反りの平均を吸って、部品全体が下へずれて読める。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/03_deviation_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/03_deviation_maps.png)

*↑ 3 枚目が一様に色づくのが第 6 章の主張 —— 位置合わせが反りの平均を吸って、部品全体が下へずれて読める。*

[![2 次元 Poisson 点過程の最近傍距離の平均 = 0.5/√ρ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/05_density_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/05_density_bias.png)

*↑ 2 次元 Poisson 点過程の最近傍距離の平均 = 0.5/√ρ。*

[![深さを 30 倍にしても割合は動かないが、広がりを変えると比例して増える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/08_dent_area_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/08_dent_area.png)

*↑ 深さを 30 倍にしても割合は動かないが、広がりを変えると比例して増える。*

[![上面だけを見ている。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/11_warp_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/11_warp_maps.png)

*↑ 上面だけを見ている。*

[![主図(動画、640 × 360・30 fps・12 秒): 前半は実測点群(だいだい)が CAD の参照点(灰)に重なるまで —— 位置合わせなし → FPFH 粗合わせ → 点-面 ICP の推定姿勢の間を補間して動かす(偏差 RMS 1](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/14_align_orbit.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/14_align_orbit.gif)

*↑ 動く図 ―― 主図(動画、640 × 360・30 fps・12 秒): 前半は実測点群(だいだい)が CAD の参照点(灰)に重なるまで —— 位置合わせなし → FPFH 粗合わせ → 点-面 ICP の推定姿勢の間を補間して動かす(偏差 RMS 18285.3 → 105.4 → 81.7 µm)。後半は重なった点群を一周し、符号付き偏差(±0.40 mm、だいだい = 足りない / 青 = 余る)で塗る(形が読めるよう陰影を薄く足した)。公差 ±0.10 mm を外れた面積は推定 2300.6 mm²、真値 2514.5 mm²。左手前の 3 本の線は CAD の x・y・z 軸。*

```
py -3.11 examples/poc_cad_scan_deviation.py
```

ソース: [examples/poc_cad_scan_deviation.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_cad_scan_deviation.py)

この回が作った図は全部で **14 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_cad_scan_deviation)

使用 op(ノートへ): [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`chamfer_distance`](https://furuse.work/ops/3d/metrics/chamfer_distance.html) · [`color_bar`](https://furuse.work/ops/annotate/furniture/color_bar.html) · [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`estimate_oriented_normals`](https://furuse.work/ops/3d/normals_orient/estimate_oriented_normals.html) · [`face_areas`](https://furuse.work/ops/3d/mesh_process/face_areas.html) · [`gicp`](https://furuse.work/ops/3d/gicp/gicp.html) · [`hausdorff_distance`](https://furuse.work/ops/3d/metrics/hausdorff_distance.html) · [`icp_point2plane`](https://furuse.work/ops/3d/refine/icp_point2plane.html) · [`icp_point2point_3d`](https://furuse.work/ops/3d/refine/icp_point2point_3d.html) · [`query_distance`](https://furuse.work/ops/3d/occupancy/query_distance.html) · [`register_fpfh`](https://furuse.work/ops/3d/feature_register/register_fpfh.html) · [`sphere_sdf`](https://furuse.work/ops/3d/sdf_csg/sphere_sdf.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`voxel_grid_downsample`](https://furuse.work/ops/3d/preprocess/voxel_grid_downsample.html)

## No.2026.063 —— 作物の葉面積を上から測る —— 隠れるより先に、投影が畳んでしまう

[![作物の葉面積を上から測る —— 隠れるより先に、投影が畳んでしまう](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crop_phenotyping/08_scene_nadir_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crop_phenotyping/08_scene_nadir.png)

*↑ **作物の葉面積を上から測る —— 隠れるより先に、投影が畳んでしまう** ―― 葉を解析曲面(片面面積 pi/4·L·W、葉角も投影係数も閉形式)で組んだトウモロコシ群落に、天頂からの厳密な z-buffer をかけて植被率・遮蔽・葉角を測った。植被率を Beer-Lambert で戻す素朴な葉面積指数は、消光係数を真値に直しても真の 4.85 に対し -52.2 %、しかも 2 段階クランピングから予測した天井 2.26 のすぐ上(実測 2.70)で止まる。遮蔽は天頂の植被率を 1 ビットも変えず、壊しているのは 1 セルを平均 3.49 枚の葉が覆うのに 1 枚と数える「投影が畳む分」のほうで、点密度を 4 倍にしても判別できる上限は +1.92 しか伸びなかった。*

[![閉形式 2 pi r h + 4 pi r^2 / pi r^2 h + 4/3 pi r^3 と比べる。2 値化を挟むと面積だけが一方向に膨らむ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crop_phenotyping/01_capsule_calibration_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crop_phenotyping/01_capsule_calibration.png)

*↑ 測定の図 ―― 閉形式 2 pi r h + 4 pi r^2 / pi r^2 h + 4/3 pi r^3 と比べる。2 値化を挟むと面積だけが一方向に膨らむ。*

[![稈カプセルの符号付き距離場(縦断面、中心が内側 = 負)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crop_phenotyping/02_capsule_sdf_slice_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crop_phenotyping/02_capsule_sdf_slice.png)

*↑ 稈カプセルの符号付き距離場(縦断面、中心が内側 = 負)*

[![重なりの枚数(遮蔽を無視して全部数えた場合)は真値に乗る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crop_phenotyping/05_cliff_estimators_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crop_phenotyping/05_cliff_estimators.png)

*↑ 重なりの枚数(遮蔽を無視して全部数えた場合)は真値に乗る。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crop_phenotyping/10_sweep_beta_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crop_phenotyping/10_sweep_beta.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crop_phenotyping/14_wind_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crop_phenotyping/14_wind.png)

*↑ この回の図*

```
py -3.11 examples/poc_crop_phenotyping.py
```

ソース: [examples/poc_crop_phenotyping.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_crop_phenotyping.py)

この回が作った図は全部で **17 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_crop_phenotyping)

使用 op(ノートへ): [`boundary_vertices`](https://furuse.work/ops/3d/mesh_process/boundary_vertices.html) · [`capsule_sdf`](https://furuse.work/ops/3d/sdf_csg/capsule_sdf.html) · [`dem_slope`](https://furuse.work/ops/dem/surface/dem_slope.html) · [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`face_areas`](https://furuse.work/ops/3d/mesh_process/face_areas.html) · [`face_normals`](https://furuse.work/ops/3d/mesh_process/face_normals.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`mesh_area`](https://furuse.work/ops/3d/mesh_process/mesh_area.html) · [`mesh_sample_points`](https://furuse.work/ops/3d/resolution/mesh_sample_points.html) · [`mesh_volume`](https://furuse.work/ops/3d/mesh_process/mesh_volume.html) · [`occupancy_grid`](https://furuse.work/ops/3d/occupancy/occupancy_grid.html) · [`plane_segmentation`](https://furuse.work/ops/3d/segment/plane_segmentation.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`sdf_to_occupancy`](https://furuse.work/ops/3d/transform/sdf_to_occupancy.html)

## No.2026.064 —— 接合層のボイドを 1 個の数字に畳む ―― 畳んだ分だけ、寿命に効く形が消える

[![接合層のボイドを 1 個の数字に畳む ―― 畳んだ分だけ、寿命に効く形が消える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/01_scene_sections_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/01_scene_sections.png)

*↑ **接合層のボイドを 1 個の数字に畳む ―― 畳んだ分だけ、寿命に効く形が消える** ―― 合成のダイアタッチ接合層に、体積率を 3.000 % に厳密にそろえたまま位置・形・近接だけを変えた 5 条件のボイドを仕込み、PSF・雑音・カッピングつきの X 線 CT として撮り直した。2 値化してボイド率だけを出すゼロ点は 5 条件を 2.46〜2.63 %(開きは 0.17 ポイント)としか分けないのに、界面に接する扁平ボイドが界面を塞ぐ面積は同体積の球の 2.09 倍(14.49 対 6.92 %)、連なりの跨ぎ率は散在の 13.1 倍(80.0 対 6.1 %)になる。崖の予想は外れ、ボクセルを 60 µm まで粗くしてもボイド率は 3.21 % と崩れず(格子の位相の運で ±1.36 ポイント振れるだけ)、代わりに扁平度が測れなくなり界面欠損率が 14.16 → 9.78 % と『安全』側へ落ちた ―― 壊れる向きが合格の側なのがいちばん悪い。*

[![疑似カラーはラベル番号を並べ替えたもの。側面図で界面(上端)に貼りついているのが見える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/02_void_label_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/02_void_label_map.png)

*↑ 測定の図 ―― 疑似カラーはラベル番号を並べ替えたもの。側面図で界面(上端)に貼りついているのが見える。*

[![ボイド率の列だけを見ると 5 条件は区別できない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/03_controls_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/03_controls_table.png)

*↑ ボイド率の列だけを見ると 5 条件は区別できない。*

[![界面欠損率は 球/中央/散 0.0 % / 球/界面/散 6.9 % / 扁平/界面/散 14.5 % / 球/中央/連 0.0 % / 扁平/界面/連 14.7 % —— 体積率が同じでも 0 から](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/05_controls_section_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/05_controls_section.png)

*↑ 界面欠損率は 球/中央/散 0.0 % / 球/界面/散 6.9 % / 扁平/界面/散 14.5 % / 球/中央/連 0.0 % / 扁平/界面/連 14.7 % —— 体積率が同じでも 0 から 14.7 % まで動く。*

[![60 µm では扁平度が測れない(nan なので描けない)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/08_voxel_cliff_shape_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/08_voxel_cliff_shape.png)

*↑ 60 µm では扁平度が測れない(nan なので描けない)。*

[![塊の数が 24 から落ちた瞬間、最近接間隔は『隣のボイドまで』から『隣の鎖まで』に黙って入れ替わる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/10_threshold_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/10_threshold_sweep.png)

*↑ 塊の数が 24 から落ちた瞬間、最近接間隔は『隣のボイドまで』から『隣の鎖まで』に黙って入れ替わる。*

[![主図(動画、640 × 360・30 fps・11 秒): 同じボイド率の 2 条件(球・散在・層中央 2.46 % / 扁平・連なり・界面接触 2.63 %)で、xz 断面(橙の枠)を y 方向に掃引しながら 3-D のボイド(2 値化の](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/13_section_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/13_section_sweep.gif)

*↑ 動く図 ―― 主図(動画、640 × 360・30 fps・11 秒): 同じボイド率の 2 条件(球・散在・層中央 2.46 % / 扁平・連なり・界面接触 2.63 %)で、xz 断面(橙の枠)を y 方向に掃引しながら 3-D のボイド(2 値化の結果を marching cubes で面に)を回す。色はダイ側界面までの距離 —— 前者は層の中ほど(界面離隔の中央値 60.0 µm)、後者は界面に貼りつく(10.0 µm)。下は同じ断面の観測 CT(上 = ダイ)。合否の 1 個の数字(ボイド率)は 2 つを分けない。z は画面上だけ 2 倍。*

```
py -3.11 examples/poc_ct_void_morphology.py
```

ソース: [examples/poc_ct_void_morphology.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_void_morphology.py)

この回が作った図は全部で **13 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_ct_void_morphology)

使用 op(ノートへ): [`boundary_vertices`](https://furuse.work/ops/3d/mesh_process/boundary_vertices.html) · [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`color_bar`](https://furuse.work/ops/annotate/furniture/color_bar.html) · [`cylinder_sdf`](https://furuse.work/ops/3d/sdf_csg/cylinder_sdf.html) · [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`face_areas`](https://furuse.work/ops/3d/mesh_process/face_areas.html) · [`mesh_volume`](https://furuse.work/ops/3d/mesh_process/mesh_volume.html) · [`morph_dilate3d`](https://furuse.work/ops/3d/morphology/morph_dilate3d.html) · [`plane_sdf`](https://furuse.work/ops/3d/sdf_csg/plane_sdf.html) · [`query_distance`](https://furuse.work/ops/3d/occupancy/query_distance.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`sphere_sdf`](https://furuse.work/ops/3d/sdf_csg/sphere_sdf.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`vol_boundary_points`](https://furuse.work/ops/3d/boundary/vol_boundary_points.html) · [`vol_gaussian_psf`](https://furuse.work/ops/3d/restoration/vol_gaussian_psf.html) · [`voxel_to_mips`](https://furuse.work/ops/3d/transform/voxel_to_mips.html)

## No.2026.065 —— 造形しやすさを形から測る —— しきい値に貼りついた面は、丸めた分だけ判定が飛ぶ

[![造形しやすさを形から測る —— しきい値に貼りついた面は、丸めた分だけ判定が飛ぶ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/01_scene.png)

*↑ **造形しやすさを形から測る —— しきい値に貼りついた面は、丸めた分だけ判定が飛ぶ** ―― 設計値の分かる合成部品(薄壁・スロット・45 度前後の補強・穴)をボクセル化し、肉厚・要サポート面積・工具の入る隙間を測りました。しきい値 45 度の両側で必要面積は 185.22 → 576.10 mm^2 と 0.2 度で 3.11 倍に跳ね、その段差は等値面を距離場から取ると 100 %、平滑化でも 12 % 消えます。肉厚は 2 voxel 刻みに潰れ(内接球にしても同じ)、隙間の誤判定は両方向に出て、粗さ 0.500 mm では隙間が 2.000 mm に太り入らない工具を通します。*

[![上: 左端の 2 本が薄壁(1.500 mm)とそのあいだのスロット(1.500 mm)、右の三角が補強。下: リブと薄壁の footprint。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/02_sections_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/02_sections.png)

*↑ 測定の図 ―― 上: 左端の 2 本が薄壁(1.500 mm)とそのあいだのスロット(1.500 mm)、右の三角が補強。下: リブと薄壁の footprint。*

[![右ほど粗い。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/03_thickness_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/03_thickness_cliff.png)

*↑ 右ほど粗い。*

[![解析は階段。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/04_threshold_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/04_threshold_cliff.png)

*↑ 解析は階段。*

[![左 = 水平からの傾き(暗い = 0 度 = 最悪、明るい = 90 度 = 垂直)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/06_overhang_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/06_overhang_map.png)

*↑ 左 = 水平からの傾き(暗い = 0 度 = 最悪、明るい = 90 度 = 垂直)。*

[![1.600 mm を超えると入らない工具を通し、1.200 mm を切ると入る工具を落とす。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/08_reach_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/08_reach_cliff.png)

*↑ 1.600 mm を超えると入らない工具を通し、1.200 mm を切ると入る工具を落とす。*

```
py -3.11 examples/poc_dfm_thickness_overhang.py
```

ソース: [examples/poc_dfm_thickness_overhang.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dfm_thickness_overhang.py)

この回が作った図は全部で **9 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_dfm_thickness_overhang)

使用 op(ノートへ): [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`face_areas`](https://furuse.work/ops/3d/mesh_process/face_areas.html) · [`face_normals`](https://furuse.work/ops/3d/mesh_process/face_normals.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`morph_erode3d`](https://furuse.work/ops/3d/morphology/morph_erode3d.html) · [`render_shaded`](https://furuse.work/ops/3d/render/render_shaded.html) · [`sdf_intersect`](https://furuse.work/ops/3d/sdf_csg/sdf_intersect.html) · [`sdf_subtract`](https://furuse.work/ops/3d/sdf_csg/sdf_subtract.html) · [`sdf_to_occupancy`](https://furuse.work/ops/3d/transform/sdf_to_occupancy.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`vol_wall_thickness`](https://furuse.work/ops/3d/probe/vol_wall_thickness.html) · [`voxel_to_mesh`](https://furuse.work/ops/3d/transform/voxel_to_mesh.html)

## No.2026.070 —— 斜面の土量 ―― 合わせてから引くと、崩れが浅くなる

[![斜面の土量 ―― 合わせてから引くと、崩れが浅くなる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/09_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/09_scene.png)

*↑ **斜面の土量 ―― 合わせてから引くと、崩れが浅くなる** ―― 傾斜のある合成地形に既知体積の掘削と堆積を仕込み、2 時期の航空点群から鉛直差分と法線方向の差で土量を測った。予想した「斜面では cos だけ体積が縮む」は外れで、水平投影面積で積む限り cos は約分し、掘削体積の誤差は傾斜 0〜40 度でどれも -0.011 % のまま動かない。壊れたのは合わせ方のほうで、変化域が視野の 33 % もあると位置合わせが変化そのものを吸い、正味土量は真値 -30.4 m3 に対し -3.8 m3 まで潰れた ―― 変化なしの対照ですら偽の掘削が 83.8 m3 出る。*

[![傾斜を 0 から 40 度まで振っても体積の誤差に傾向が無い。cos は積分で約分する。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/01_geometry_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/01_geometry.png)

*↑ 測定の図 ―― 傾斜を 0 から 40 度まで振っても体積の誤差に傾向が無い。cos は積分で約分する。*

[![真の掘削は 164.2 m3。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/02_controls_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/02_controls.png)

*↑ 真の掘削は 164.2 m3。*

[![予測式は先に立ててから測った。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/04_slope_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/04_slope_table.png)

*↑ 予測式は先に立ててから測った。*

[![誤差はそのしきい値以上の真値に対する値。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/07_occlusion_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/07_occlusion.png)

*↑ 誤差はそのしきい値以上の真値に対する値。*

[![M3C2 の L は法線方向なので cos 25 度 = 0.906 倍だけ浅く出る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/11_scar_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/11_scar_profile.png)

*↑ M3C2 の L は法線方向なので cos 25 度 = 0.906 倍だけ浅く出る。*

[![主図(動画、640 × 360・30 fps・12 秒): 前半は傾斜 25 度の斜面を北の上空から横切り、時期 1 の点群(8 pt/m²、樹冠に当たった点 = 緑)を見せる(動画専用の乱数で作った別の標本)。後半は時期 2 の地形の周り](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/12_flight.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/12_flight.gif)

*↑ 動く図 ―― 主図(動画、640 × 360・30 fps・12 秒): 前半は傾斜 25 度の斜面を北の上空から横切り、時期 1 の点群(8 pt/m²、樹冠に当たった点 = 緑)を見せる(動画専用の乱数で作った別の標本)。後半は時期 2 の地形の周りを回り、色を DoD の鉛直差から M3C2 の法線距離へ塗り替える(同じ尺度 ±1.2 m、青 = 下がった)。崩壊中心の深さは DoD 1.212 m / M3C2 1.096 m で比 1.105(sec 25 度 = 1.103)。有意な core の M3C2 土量は掘削 142.3 / 堆積 107.7 m³(真値 164.2 / 133.7)。黒っぽい所は測れなかった core。*

```
py -3.11 examples/poc_lidar_terrain_change.py
```

ソース: [examples/poc_lidar_terrain_change.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_lidar_terrain_change.py)

この回が作った図は全部で **14 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_lidar_terrain_change)

使用 op(ノートへ): [`chamfer_distance`](https://furuse.work/ops/3d/metrics/chamfer_distance.html) · [`color_bar`](https://furuse.work/ops/annotate/furniture/color_bar.html) · [`dem_hillshade`](https://furuse.work/ops/dem/shading/dem_hillshade.html) · [`dem_slope`](https://furuse.work/ops/dem/surface/dem_slope.html) · [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`estimate_oriented_normals`](https://furuse.work/ops/3d/normals_orient/estimate_oriented_normals.html) · [`fit_plane_3d`](https://furuse.work/ops/3d/geometry/fit_plane_3d.html) · [`icp_point2point_3d`](https://furuse.work/ops/3d/refine/icp_point2point_3d.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`ransac_plane`](https://furuse.work/ops/3d/robust_fit/ransac_plane.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`voxel_grid_downsample`](https://furuse.work/ops/3d/preprocess/voxel_grid_downsample.html)

## No.2026.099 —— シルエットから体重を測る ―― 台数で買える誤差と、いくら買っても消えない誤差

[![シルエットから体重を測る ―― 台数で買える誤差と、いくら買っても消えない誤差](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/10_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/10_scene.png)

*↑ **シルエットから体重を測る ―― 台数で買える誤差と、いくら買っても消えない誤差** ―― 多視点シルエットの交差(visual hull)から家畜の体積を出し、体重へ換算する。視体積交差は**必ず上界**なので、問うべきは「良いか」ではなく「**必ず上に出る**」ほうだ。★★**閉形式の崖が、現場の目安を訂正した**。「K 台なら K 角形」は正しくない —— 平行投影ではカメラ 1 台が視線に**直交する接線 2 本**を与え(法線は方位 ± 90 度)、しかも**向かい合う 2 台は同じ 2 本**しか与えない。したがって接線の本数は偶数 K なら K 本、**奇数 K なら 2K 本**。結果として **3 台と 6 台は幾何としてまったく同じ**(閉形式 1.16772 / 1.16772、接線の集合が一致。実測差 0.013 は離散化だけ)、**偶数台は半分が無駄**で、**13 台(実測 1.03056)が 16 台(1.04768)に勝つ**。「体重 2 % 以内」を要求すると奇数 **13 台** / 偶数 **24 台**。円の素朴な読み (K/π)tan(π/K) は 13 台と出るので、**偶数台で組む現場は 11 台足りない見積り**を持つことになる。支持関数から出した楕円(a/b = 2.76)の厳密値に対し、近似平行投影(60 m・4.0 mm/px)の実測は**全 K で閉形式のすぐ上**に乗った(K=4: 1.27324 / 1.27528、K=8: 1.11657 / 1.12231、K=24: 1.01790 / 1.02821)—— **下界として的中**し、差は被覆マージンで説明できる。★対照群でこの縮退が**平行投影の性質**だと確かめた: 距離 8 m まで近づけると 3 台 1.20699 / 6 台 1.11211 と差が 7.1 倍に開く。★★この展示の中心は、**カメラを増やして消える誤差と、いくら増やしても消えない誤差を分けて数える**こと。脚の間の幽霊は K=4 → 48 で **7.13 % → 1.37 %**(5.2 倍)と素直に減るのに、**背中のくぼみはカメラを 12 倍にしても 3.8 ポイントしか減らない**(56.4 % → 52.6 %)。分かれ目は「その凹みが**輪郭に出るか**」で、出ない凹みはシルエットにそもそも情報が無い。K=48 で残る +3.4 % の内訳はくぼみ +1.00 % / 幽霊 +1.76 %、真の voxel の**取りこぼしは全 K で 0**(上界であることの確認)。★**前景抽出の 1 画素**も台数では買えない: K=12・4.0 mm/px で **+3.21 %/px**(体重 +23.7 kg)。Steiner の ΔV/V = (S/V)δ の予測 +3.09 %/px と比 1.04 で当たるが、押し上げ要因と押し下げ要因が**偶然釣り合った**結果なので、そのまま一般化しないよう本文に書いた。±3 画素で -8.71 〜 +9.43 %。★**物差しで勝者が入れ替わる**: 体積由来の体重とアロメトリ体重は「K=24 + 2 画素収縮」が最良だが、**重心の高さでは収縮なしの K=24 が勝つ**(細い脚が先に消えて重心が上がる)。3 つの物差しに 2 通りの勝者。★★**予想を外した**: 「巻尺は体に巻くから凸包を測っている。だから胸囲では 3-D 凸包が強いはず」と踏んだが、実測 **+55.2 %** で最悪の部類だった。体全体の凸包は**腹の下を埋める**ので、縦断面が地面まで伸びる —— **『断面の凸包』と『凸包の断面』は別物**。★カメラ配置の対照(上半球ランダム 8 台 対 等間隔 8 台、120 試行)は平均では互角(等間隔以下 57.5 %)だが、**最悪値は +30.20 % で等間隔の 2.4 倍** —— **危ないのは平均ではなく裾**。★★道具の穴を見つけて**その場で埋めた**: 空間彫刻が要求する OpenCV 規約(+Z 前方)の姿勢ヘルパは`fs.` / `fs.op.` / `fs.ledger.` / `op_find('look')`(0 件)の**どこからも引けず**、公開層で `look_at` の名を持つのは render3d の gluLookAt 版(-Z 前方)だけだった。**同じ名前で規約が逆**なので、掴み間違えると全点がカメラ後方に落ち、**例外を出さずに空の hull** が返る(カメラ 0 台は ValueError で fail-closed なのに、規約違いは無言)。`carve_look_at` を台帳に載せて引けるようにし、点が 1 つ残らず後方なら警告を出すようにし、`render3d.look_at` の docstring にも「彫刻には渡すな」と書いた。*

[![真値 0.7238 m^3 / 738 kg。外接直方体と OBB は上界の中でもいちばん粗い。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/01_null_baseline_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/01_null_baseline.png)

*↑ 測定の図 ―― 真値 0.7238 m^3 / 738 kg。外接直方体と OBB は上界の中でもいちばん粗い。*

[![法線は方位 ± 90 度。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/02_closed_form_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/02_closed_form.png)

*↑ 法線は方位 ± 90 度。*

[![くぼみ(輪郭に出ない凹み)は台数に鈍感、脚の間(輪郭に出る凹み)は台数に敏感。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/04_persistent_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/04_persistent.png)

*↑ くぼみ(輪郭に出ない凹み)は台数に鈍感、脚の間(輪郭に出る凹み)は台数に敏感。*

[![K=12・4.0 mm/px。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/07_controls_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/07_controls.png)

*↑ K=12・4.0 mm/px。*

[![脚の間の空隙はどの 1 枚にも写っている(だから彫れる)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/11_silhouettes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/11_silhouettes.png)

*↑ 脚の間の空隙はどの 1 枚にも写っている(だから彫れる)。*

[![動画(270 コマ、560 × 420 px): 牛の周りを 1 周しながら、彫刻に使うカメラの台数を 4 → 48 台(軸周り等間隔、8 m 先)へ増やす。表示は §4 で数えた視体積交差の占有の表面で、真の体に接する面は灰、真に空の所に](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/14_hull_orbit.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/14_hull_orbit.gif)

*↑ 動く図 ―― 動画(270 コマ、560 × 420 px): 牛の周りを 1 周しながら、彫刻に使うカメラの台数を 4 → 48 台(軸周り等間隔、8 m 先)へ増やす。表示は §4 で数えた視体積交差の占有の表面で、真の体に接する面は灰、真に空の所に立つ面(余分)はだいだい。最初の段は真の占有。横腹の帯と脚の間の幽霊(7.13 % → 1.37 %)は台数とともに消えるが、背中のくぼみに被さる蓋は K = 48 でも 52.6 % 埋まったまま(K = 4 で 56.4 %)—— 輪郭に出ない凹みはシルエットに情報が無い。体積は真値の 1.2255 → 1.0339 倍。カメラの仰角は 20 → 46 度へ上げていき、台数の多い段ほど背中の蓋が見える。左下の 3 本は x(体長)・y(体幅)・z(上)、灰の細線は地面の x 軸・y 軸。*

```
py -3.11 examples/poc_livestock_body_volume.py
```

ソース: [examples/poc_livestock_body_volume.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_livestock_body_volume.py)

この回が作った図は全部で **14 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_livestock_body_volume)

使用 op(ノートへ): [`carve`](https://furuse.work/ops/3d/space_carving/carve.html) · [`carve_look_at`](https://furuse.work/ops/3d/space_carving/carve_look_at.html) · [`convex_hull`](https://furuse.work/ops/3d/bounds/convex_hull.html) · [`erosion_circle`](https://furuse.work/ops/2d/region/erosion_circle.html) · [`mesh_volume`](https://furuse.work/ops/3d/mesh_process/mesh_volume.html) · [`synthesize_silhouette`](https://furuse.work/ops/3d/space_carving/synthesize_silhouette.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`vol_rle_bbox`](https://furuse.work/ops/3d/rle_region/vol_rle_bbox.html) · [`vol_rle_centroid`](https://furuse.work/ops/3d/rle_region/vol_rle_centroid.html) · [`vol_rle_encode`](https://furuse.work/ops/3d/rle_region/vol_rle_encode.html) · [`vol_rle_volume`](https://furuse.work/ops/3d/rle_region/vol_rle_volume.html) · [`voxel_to_mesh`](https://furuse.work/ops/3d/transform/voxel_to_mesh.html)

## No.2026.072 —— 壊れたメッシュを直してから測る ―― 消えるのは欠陥の数で、戻るのは量ではない

[![壊れたメッシュを直してから測る ―― 消えるのは欠陥の数で、戻るのは量ではない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/01_scene.png)

*↑ **壊れたメッシュを直してから測る ―― 消えるのは欠陥の数で、戻るのは量ではない** ―― 球とトーラスと角柱のブール和から閉じた三角メッシュを作り、穴・裏返った面・非多様体辺・退化三角形・重複頂点・自己交差を種類ごとに既知個数だけ仕込んで、位相の数字と体積・表面積の両方で追いました。オイラー標数は 6 種のうち 5 種にまったく反応せず、穴 6 個と重複面 6 枚を同時に入れると頂点・辺・面・χ が健全な部品と 1 つも違わなくなります。直したあとも量は戻らず、半頂角 45° の穴を塞いだ球は表面積が予測 -2.145 % に対して実測 +6.868 %(縁が円ではなく階段だから)、頂点を 6 個だけ突き刺したメッシュは位相の検査を 3 つとも通り抜けたまま表面積 +4.414 % / 体積 -0.332 % と 13 倍食い違いました。*

[![健全な部品の χ は 0(種数 1)。χ=2 を合格条件にすると健全品が落ちる。最終行は打ち消し。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/02_euler_blindspots_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/02_euler_blindspots.png)

*↑ 測定の図 ―― 健全な部品の χ は 0(種数 1)。χ=2 を合格条件にすると健全品が落ちる。最終行は打ち消し。*

[![ただし順番が両向きに効く —— 溶接前は割れの境界を穴として数え、溶接後は退化三角形を数え損ねる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/03_defect_counts_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/03_defect_counts.png)

*↑ ただし順番が両向きに効く —— 溶接前は割れの境界を穴として数え、溶接後は退化三角形を数え損ねる。*

[![幅ゼロの割れ(重複頂点 18 個)を直した結果。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/05_repair_vs_restore_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/05_repair_vs_restore.png)

*↑ 幅ゼロの割れ(重複頂点 18 個)を直した結果。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/08_hole_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/08_hole_frames.png)

*↑ この回の図*

[![面積 0 の判定に引っかかるずっと手前で、潰れ面の法線は使いものにならなくなる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/11_sliver_threshold_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/11_sliver_threshold.png)

*↑ 面積 0 の判定に引っかかるずっと手前で、潰れ面の法線は使いものにならなくなる。*

[![動画(272 コマ、480 × 480 px): 健全な部品(面 11208 枚)の周りを 1.5 周しながら、QEM 簡略化の削減率を 0 → 98 % へ 8 段で上げる。面は平らに塗り、色は面の 3 頂点の平均曲率 |H|(尺度は削減](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/14_decimate_orbit.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/14_decimate_orbit.gif)

*↑ 動く図 ―― 動画(272 コマ、480 × 480 px): 健全な部品(面 11208 枚)の周りを 1.5 周しながら、QEM 簡略化の削減率を 0 → 98 % へ 8 段で上げる。面は平らに塗り、色は面の 3 頂点の平均曲率 |H|(尺度は削減前の 99 パーセンタイル 12.6 /mm で固定)。50 % 削減で体積の誤差は -0.019 % しかないのに曲率の 95 パーセンタイルは 5.89 → 7.72(+31 %)—— 明るい(尖った)面が先に増える。98 % 削減でようやく体積 -4.199 %。左下の 3 本は配列の軸(0 = 貫通穴の軸 = 画面の上、2 = 角柱ボスの側)。*

```
py -3.11 examples/poc_mesh_quality_repair.py
```

ソース: [examples/poc_mesh_quality_repair.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_mesh_quality_repair.py)

この回が作った図は全部で **14 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_mesh_quality_repair)

使用 op(ノートへ): [`decimate_qem`](https://furuse.work/ops/3d/mesh_process/decimate_qem.html) · [`face_normals`](https://furuse.work/ops/3d/mesh_process/face_normals.html) · [`fill_holes`](https://furuse.work/ops/2d/region/fill_holes.html) · [`inertia_tensor`](https://furuse.work/ops/3d/moment_invariant/inertia_tensor.html) · [`mesh_area`](https://furuse.work/ops/3d/mesh_process/mesh_area.html) · [`mesh_edge_lengths`](https://furuse.work/ops/3d/terrain/mesh_edge_lengths.html) · [`mesh_edge_stats`](https://furuse.work/ops/3d/resolution/mesh_edge_stats.html) · [`sdf_subtract`](https://furuse.work/ops/3d/sdf_csg/sdf_subtract.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`vertex_curvature`](https://furuse.work/ops/3d/mesh_process/vertex_curvature.html) · [`vertex_normals`](https://furuse.work/ops/3d/mesh_process/vertex_normals.html) · [`voxel_to_mesh`](https://furuse.work/ops/3d/transform/voxel_to_mesh.html)

## No.2026.101 —— パレットの積載率 —— 1 つの数字が「隙間」と「はみ出し」を同じ値にする

[![パレットの積載率 —— 1 つの数字が「隙間」と「はみ出し」を同じ値にする](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pallet_load_utilization/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pallet_load_utilization/01_scene.png)

*↑ **パレットの積載率 —— 1 つの数字が「隙間」と「はみ出し」を同じ値にする** ―― 1200 x 1000 mm のパレットに、中身が正反対の 2 つの荷を積んだ。荷 A は上から見えない 400 x 400 x 420 mm の空洞と幅 20 / 50 / 120 mm の隙間だらけ、荷 B は詰まっているが 90 mm はみ出して天端が制限 1800 mm を 100 mm 超える。中段の高さを閉形式で 995.0 mm に解くと、見かけの積載率は 62.65 % と 62.67 %(差 0.02 pt)で一致する——同じ数字なのに A は 3.11 pt が見えない空洞、B ははみ出し 2.10 pt + 高さ超過 0.58 pt で、処置は「積み直す」と「降ろす」で逆。荷を 1 個の外形とみなすゼロ点は荷 B で AABB 113.90 % / OBB 166.44 % と 100 % を超え、真の中身と押し出し形の IoU は 0.9493 と 1.0000 でどちらも「よく合っている」としか読めない。高さマップのセル寸法という 1 つのつまみが逆向きに 2 通り壊し、幅 w の隙間は max(0, 1 - g/w) で消え(g = 40 mm で 20 mm の隙間は完全に消失、g = w ちょうどは位相で全か無かに割れて 5 回に 1 回だけ全部見える)、一方で 1 mm も出ていない荷 A に周長 x g/2 x 天端 の偽はみ出しが立ち、g = 40 mm からは本当に出ている荷 B の 0.0450 m3 を上回る。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pallet_load_utilization/02_hidden_void_section_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pallet_load_utilization/02_hidden_void_section.png)

*↑ 測定の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pallet_load_utilization/03_zero_points_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pallet_load_utilization/03_zero_points.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pallet_load_utilization/04_breakdown_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pallet_load_utilization/04_breakdown.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pallet_load_utilization/06_heightmap_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pallet_load_utilization/06_heightmap_frames.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pallet_load_utilization/07_gsd_false_overhang_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pallet_load_utilization/07_gsd_false_overhang.png)

*↑ この回の図*

```
py -3.11 examples/poc_pallet_load_utilization.py
```

ソース: [examples/poc_pallet_load_utilization.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pallet_load_utilization.py)

この回が作った図は全部で **8 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_pallet_load_utilization)

使用 op(ノートへ): [`aabb`](https://furuse.work/ops/3d/bounds/aabb.html) · [`convex_hull`](https://furuse.work/ops/3d/bounds/convex_hull.html) · [`euclidean_cluster`](https://furuse.work/ops/3d/segment/euclidean_cluster.html) · [`inner_box3`](https://furuse.work/ops/3d/regionprops/inner_box3.html) · [`mesh_volume`](https://furuse.work/ops/3d/mesh_process/mesh_volume.html) · [`voxel_iou`](https://furuse.work/ops/3d/metrics/voxel_iou.html)

## No.2026.075 —— 配管内面の減肉を展開図で測る ―― 軸を決めた分だけ、管底の腐食が消える

[![配管内面の減肉を展開図で測る ―― 軸を決めた分だけ、管底の腐食が消える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/01_scene_pipe_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/01_scene_pipe.png)

*↑ **配管内面の減肉を展開図で測る ―― 軸を決めた分だけ、管底の腐食が消える** ―― 合成の管に孔食・全周減肉・管底腐食・溶接ビード・楕円化・曲がりを既知の深さで仕込み、管内を走る距離センサの軸を意図的にずらして展開図を作りました。軸が 4.0 mm ずれるだけで腐食ゼロの真円の管の 44.8 % が減肉と判定され(中心のずれは振幅 e の 1 周期の正弦波になる、という幾何の予測との差は 1.84 ポイント)、偽の減肉体積は本物の孔食の 149.9 倍になります。1 周期を消せば偽物は消えますが、下水管でいちばん多い管底の腐食もその 79 % が同じ 1 周期に居るので検出率が 100.0 → 34.4 % へ落ち、軸の動きを物理どおり(直線とたわみ)に縛って初めて両方が残ります。*

[![下の帯の細くなっている所が管底腐食。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/02_scene_polar_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/02_scene_polar.png)

*↑ 測定の図 ―― 下の帯の細くなっている所が管底腐食。*

[![真の減肉 [mm)(縦 = z 0..300 mm、横 = θ 0..360 度。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/03_map_truth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/03_map_truth.png)

*↑ 真の減肉 [mm](縦 = z 0..300 mm、横 = θ 0..360 度。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/07_map_false_flag_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/07_map_false_flag.png)

*↑ この回の図*

[![楕円化は k=2 に立つので分離できる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/11_spectrum_defects_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/11_spectrum_defects.png)

*↑ 楕円化は k=2 に立つので分離できる。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/15_defect_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/15_defect_table.png)

*↑ この回の図*

```
py -3.11 examples/poc_pipe_wall_loss.py
```

ソース: [examples/poc_pipe_wall_loss.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pipe_wall_loss.py)

この回が作った図は全部で **19 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_pipe_wall_loss)

使用 op(ノートへ): [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_select`](https://furuse.work/ops/blob/select/blob_select.html) · [`cylinder_sdf`](https://furuse.work/ops/3d/sdf_csg/cylinder_sdf.html) · [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`polar_unwrap`](https://furuse.work/ops/3d/curvilinear/polar_unwrap.html) · [`ransac_cylinder`](https://furuse.work/ops/3d/robust_fit/ransac_cylinder.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`sdf_subtract`](https://furuse.work/ops/3d/sdf_csg/sdf_subtract.html) · [`sdf_to_occupancy`](https://furuse.work/ops/3d/transform/sdf_to_occupancy.html) · [`spectrum`](https://furuse.work/ops/oned/signal/spectrum.html) · [`vol_wall_thickness`](https://furuse.work/ops/3d/probe/vol_wall_thickness.html)

## No.2026.076 —— 積層の反りは層の履歴が決める —— 均した面積は置き場所を捨てる

[![積層の反りは層の履歴が決める —— 均した面積は置き場所を捨てる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/01_scene.png)

*↑ **積層の反りは層の履歴が決める —— 均した面積は置き場所を捨てる** ―― 1 層あたり一定の収縮ひずみを仕込んだ合成形状 7 つを層に切り、断面積の履歴だけから梁の閉形式で反りを予測して、層を 1 枚ずつ生やす有限要素の実測と突き合わせた。最終形状だけを見る予測器は原理的にゼロ(2.712e-21)を返し、履歴の閉形式は 7 形状中 4 形状で 0.4 % 以内に当たるが、面積を長さ方向に均した瞬間に「どこに置いたか」が消える。層面積の履歴が 1 mm^2 も違わない三つ子でたわみは 0.4109 / 0.3809 / 0.3271 mm と 26 % 開き、基板を引き剥がす力に至っては 11.8 対 573.5 N の 48 倍違って合否まで割れた。*

[![この断面の面積の列だけが、閉形式の入力になる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/02_layer_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/02_layer_frames.png)

*↑ 測定の図 ―― この断面の面積の列だけが、閉形式の入力になる。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/03_shapes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/03_shapes.png)

*↑ この回の図*

[![断面 2 次モーメントが層数の 3 乗で増えるのに、腕は 1 乗でしか伸びないため。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/07_saturation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/07_saturation.png)

*↑ 断面 2 次モーメントが層数の 3 乗で増えるのに、腕は 1 乗でしか伸びないため。*

[![首の細さでは崩れない(別図)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/12_cliff_aspect_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/12_cliff_aspect.png)

*↑ 首の細さでは崩れない(別図)。*

[![正 = 接着剤が引っ張られる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/16_peel_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/16_peel_profile.png)

*↑ 正 = 接着剤が引っ張られる。*

```
py -3.11 examples/poc_print_warpage_risk.py
```

ソース: [examples/poc_print_warpage_risk.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_print_warpage_risk.py)

この回が作った図は全部で **20 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_print_warpage_risk)

使用 op(ノートへ): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`sdf_to_occupancy`](https://furuse.work/ops/3d/transform/sdf_to_occupancy.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html)

## No.2026.081 —— 人と機械の安全距離 —— 代表点に置き換えた分だけ、危険が消える

[![人と機械の安全距離 —— 代表点に置き換えた分だけ、危険が消える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_safety_clearance/02_frames_clearance_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_safety_clearance/02_frames_clearance.png)

*↑ **人と機械の安全距離 —— 代表点に置き換えた分だけ、危険が消える** ―― 多関節の骨格に太さを持たせた人体(カプセル 10 本)と可動アームを合成し、表面どうしの真の最小分離距離を時刻ごとに閉形式で持たせた場面で、速度分離監視の判定がどこで嘘になるかを数えた。人を重心 1 点 + 半径 0.30 m の球で代表すると危険時に +0.166 m 遠く言い、危険の 14.3 % を見落とす(足元 1 点なら 28.6 %)—— どちらも誤検知はほぼ 0 で、壊れ方は片側にしか出ない。背面カメラ 1 台では危険フレームの 48.6 % で「推定を決めた部位が真の最近傍と違う」ことが起き見落としは 18.1 %、2 台目で 0 % に戻るが、繰り返し性から名乗った不確かさ 0.036 m は遮蔽の偏り 0.178 m の 5 分の 1 しか無い。*

[![危険 = 真の距離 < 0.640 m、停止判定 = 推定 < 0.690 m。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_safety_clearance/01_conditions_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_safety_clearance/01_conditions.png)

*↑ 測定の図 ―― 危険 = 真の距離 < 0.640 m、停止判定 = 推定 < 0.690 m。*

[![疎にするほど推定は遠くなるので、誤検知が減って見落としが増える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_safety_clearance/03_sweep_density_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_safety_clearance/03_sweep_density.png)

*↑ 疎にするほど推定は遠くなるので、誤検知が減って見落としが増える。*

[![横 = x [-0.2, 2.2) m、縦 = y [-1.1, 1.1) m。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_safety_clearance/06_map_miss_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_safety_clearance/06_map_miss.png)

*↑ 横 = x [-0.2, 2.2] m、縦 = y [-1.1, 1.1] m。*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_safety_clearance/09_grid_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_safety_clearance/09_grid_bias.png)

*↑ この回の図*

[![人は 10 本のカプセル、機械は 2 本のリンク + 基台、手前は治具台。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_safety_clearance/12_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_safety_clearance/12_scene.png)

*↑ 人は 10 本のカプセル、機械は 2 本のリンク + 基台、手前は治具台。*

```
py -3.11 examples/poc_safety_clearance.py
```

ソース: [examples/poc_safety_clearance.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_safety_clearance.py)

この回が作った図は全部で **14 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_safety_clearance)

使用 op(ノートへ): [`annotate3d_label`](https://furuse.work/ops/3d/annotate3d/annotate3d_label.html) · [`annotate3d_measure`](https://furuse.work/ops/3d/annotate3d/annotate3d_measure.html) · [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`capsule_sdf`](https://furuse.work/ops/3d/sdf_csg/capsule_sdf.html) · [`chamfer_distance`](https://furuse.work/ops/3d/metrics/chamfer_distance.html) · [`distance_line_line`](https://furuse.work/ops/3d/geometry/distance_line_line.html) · [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`face_areas`](https://furuse.work/ops/3d/mesh_process/face_areas.html) · [`hausdorff_distance`](https://furuse.work/ops/3d/metrics/hausdorff_distance.html) · [`query_distance`](https://furuse.work/ops/3d/occupancy/query_distance.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`sdf_to_occupancy`](https://furuse.work/ops/3d/transform/sdf_to_occupancy.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html)

## No.2026.082 —— 設計と実物の食い違いを部屋から測る ―― 合わせの妥協角は、無傷の部材へ配られる

[![設計と実物の食い違いを部屋から測る ―― 合わせの妥協角は、無傷の部材へ配られる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/01_scene_plan_section_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/01_scene_plan_section.png)

*↑ **設計と実物の食い違いを部屋から測る ―― 合わせの妥協角は、無傷の部材へ配られる** ―― 部屋 1 つ分の合成建物に、壁の傾き・床の勾配と反り・柱の寸法違い・開口のずれを既知量で仕込み、3 か所からの走査(柱の影・入射角依存の雑音・混合画素・レジストレーション誤差つき)で測り返した。設計モデルへの平均距離という建物 1 個の数字は施工誤差の有無で 1.41 mm しか動かず、点群を一括で合わせると壁の傾きは真値の 69 % に痩せ、代わりに完全に水平な天井が 0.89 mrad 傾いて見える(合わせが吸う量を閉形式で先に予測し、実測との差は 0.05 mrad)。崖は欠測率でなく残った面の高さで決まり、同じ 90 % の欠測でも無作為に落とせば 0.098 mrad、下から順に残す形なら 1.234 mrad と 12.6 倍違った。*

[![いちばん暗い所は 1 か所も見ていない。柱の影はスキャン位置から放射状に伸びる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/02_station_coverage_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/02_station_coverage.png)

*↑ 測定の図 ―― いちばん暗い所は 1 か所も見ていない。柱の影はスキャン位置から放射状に伸びる。*

[![(a) と (c) の差は平均で 1.41 mm、Chamfer で 0.50 mm。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/03_one_number_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/03_one_number.png)

*↑ (a) と (c) の差は平均で 1.41 mm、Chamfer で 0.50 mm。*

[![左端の帯が色目盛り(上 +12 mm / 下 -12 mm)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/06_deviation_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/06_deviation_map.png)

*↑ 左端の帯が色目盛り(上 +12 mm / 下 -12 mm)。*

[![「偽の誤差」列は設計どおりに建った建物を同じ手順で測った値。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/09_element_verdicts_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/09_element_verdicts.png)

*↑ 「偽の誤差」列は設計どおりに建った建物を同じ手順で測った値。*

[![点を増やしても系統誤差は薄まらない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/12_cliff_registration_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/12_cliff_registration.png)

*↑ 点を増やしても系統誤差は薄まらない。*

```
py -3.11 examples/poc_scan_to_bim_asbuilt.py
```

ソース: [examples/poc_scan_to_bim_asbuilt.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_scan_to_bim_asbuilt.py)

この回が作った図は全部で **15 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt)

使用 op(ノートへ): [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`chamfer_distance`](https://furuse.work/ops/3d/metrics/chamfer_distance.html) · [`cylinder_sdf`](https://furuse.work/ops/3d/sdf_csg/cylinder_sdf.html) · [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`euclidean_cluster`](https://furuse.work/ops/3d/segment/euclidean_cluster.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`plane_sdf`](https://furuse.work/ops/3d/sdf_csg/plane_sdf.html) · [`plane_segmentation`](https://furuse.work/ops/3d/segment/plane_segmentation.html) · [`sdf_intersect`](https://furuse.work/ops/3d/sdf_csg/sdf_intersect.html) · [`sdf_subtract`](https://furuse.work/ops/3d/sdf_csg/sdf_subtract.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`voxel_grid_downsample`](https://furuse.work/ops/3d/preprocess/voxel_grid_downsample.html)

## No.2026.086 —— 構造物を年ごとに測り返す —— 測る場所がずれると、劣化は進んだように見える

[![構造物を年ごとに測り返す —— 測る場所がずれると、劣化は進んだように見える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/01_scene.png)

*↑ **構造物を年ごとに測り返す —— 測る場所がずれると、劣化は進んだように見える** ―― 橋桁(平面 7 枚 + 円柱 2 本)に既知のたわみ・断面欠損・支承沈下・ひび割れを 3 時点ぶん仕込み、走査位置も密度も姿勢も毎回変えて測り返した。劣化ゼロで測り直しただけで最近傍差分は中央値 21.07 mm・最大 42.64 mm の「変化」を返し、しきい値 1 mm で数えた偽の補修候補 5.098 L は本物 5.882 L の 87 % に達する。たわみを含めて全点で合わせると中央のたわみの 0.689(閉形式 2/3)が姿勢に吸われて支点に -1.737 mm の偽の隆起が出、決まらない橋軸方向は桁の平面ではなく支承の円柱にだけ「41.2 mm 水平に動いた」として現れる。*

[![下フランジの暗い窪みが断面欠損、面全体の淡い変化がたわみ。腹板(法線が水平)にはたわみが出ない ——同じ劣化でも面の向きで見え方が変わる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/02_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/02_frames.png)

*↑ 測定の図 ―― 下フランジの暗い窪みが断面欠損、面全体の淡い変化がたわみ。腹板(法線が水平)にはたわみが出ない ——同じ劣化でも面の向きで見え方が変わる。*

[![同じ構造物を 3 回測る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/03_conditions_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/03_conditions.png)

*↑ 同じ構造物を 3 回測る。*

[![真のたわみは中央 3.00 mm。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/05_scope_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/05_scope.png)

*↑ 真のたわみは中央 3.00 mm。*

[![予測は (ω×(p-c))·n を core 上で積んだだけ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/07_cliff_angle_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/07_cliff_angle.png)

*↑ 予測は (ω×(p-c))·n を core 上で積んだだけ。*

[![押し出し形状の平面は法線に x 成分を持たない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/09_prism_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/09_prism.png)

*↑ 押し出し形状の平面は法線に x 成分を持たない。*

[![動画(640 × 530、15 fps、135 コマ): 橋桁を 2 年で 3 回点検する。左は真の法線方向変化(展開図、真値は 3 時点だけ定義なので点検の間は直線で補間して描いた)、右は法線方向に測った変化で、点検(1 年・2 年)が来](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/12_years_video.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/12_years_video.gif)

*↑ 動く図 ―― 動画(640 × 530、15 fps、135 コマ): 橋桁を 2 年で 3 回点検する。左は真の法線方向変化(展開図、真値は 3 時点だけ定義なので点検の間は直線で補間して描いた)、右は法線方向に測った変化で、点検(1 年・2 年)が来たときだけ更新される。下段は代表 3 点の時系列(線 = 真値、点 = 測定)。灰の帯は t2 の差の誤差 RMS の ±2 倍(±3.45 mm)で、代表 3 点のうち欠損の谷(真 -21.4 mm)だけが帯を大きく越える。速度の誤差 RMS は 0.863 mm/年 で、1 mm/年 の進行は 2σ = 1.726 mm/年 の下に沈む。*

```
py -3.11 examples/poc_structure_4d_deterioration.py
```

ソース: [examples/poc_structure_4d_deterioration.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_structure_4d_deterioration.py)

この回が作った図は全部で **12 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_structure_4d_deterioration)

使用 op(ノートへ): [`axes_frame`](https://furuse.work/ops/annotate/plot/axes_frame.html) · [`axes_transform`](https://furuse.work/ops/annotate/plot/axes_transform.html) · [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`chamfer_distance`](https://furuse.work/ops/3d/metrics/chamfer_distance.html) · [`cylinder_sdf`](https://furuse.work/ops/3d/sdf_csg/cylinder_sdf.html) · [`data_to_pixel`](https://furuse.work/ops/annotate/plot/data_to_pixel.html) · [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`euclidean_cluster`](https://furuse.work/ops/3d/segment/euclidean_cluster.html) · [`fit_circle_3d`](https://furuse.work/ops/3d/geometry/fit_circle_3d.html) · [`fit_plane_3d`](https://furuse.work/ops/3d/geometry/fit_plane_3d.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`hausdorff_distance`](https://furuse.work/ops/3d/metrics/hausdorff_distance.html) · [`plane_sdf`](https://furuse.work/ops/3d/sdf_csg/plane_sdf.html) · [`rmse`](https://furuse.work/ops/imgmetrics/fidelity/rmse.html) · [`sdf_intersect`](https://furuse.work/ops/3d/sdf_csg/sdf_intersect.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`ticks`](https://furuse.work/ops/annotate/plot/ticks.html) · [`voxel_grid_downsample`](https://furuse.work/ops/3d/preprocess/voxel_grid_downsample.html)

## No.2026.087 —— 対称性で欠けを補う —— 仮定した面がずれた分だけ、復元は嘘をつく

[![対称性で欠けを補う —— 仮定した面がずれた分だけ、復元は嘘をつく](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/01_scene.png)

*↑ **対称性で欠けを補う —— 仮定した面がずれた分だけ、復元は嘘をつく** ―― 左右対称な仮面を合成して完全形と対称面を真値に持ち、片側を球で削って対称復元を測った。面が真値なら復元 RMS 0.81 mm で穴埋め補間(1.60 mm)に勝つが、面が 1.39 度(84 分角)または 1.41 mm ずれた時点で負ける —— 誤差は鏡像変位の法線成分で予測でき(相対誤差 4.6 %、素朴な 2d sin α は 50.6 % 外す)、崖の位置は幾何だけで決まる。★欠損は面をずらす前に軸ごと飛ばし(失った点 3.1 % で PCA 候補の順位が逆転)、しかも本当は対称でない形では面が真値でも装飾を 3436 mm³ 捏造するか 3495 mm³ 消す。*

[![失われた真値の点から復元点群までの距離(符号なし、6 mm で頭打ち)。対称復元だけが眼窩の形を取り戻す。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/02_restore_error_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/02_restore_error_maps.png)

*↑ 測定の図 ―― 失われた真値の点から復元点群までの距離(符号なし、6 mm で頭打ち)。対称復元だけが眼窩の形を取り戻す。*

[![崖は alpha = 1.39 deg(84 分角)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/03_angle_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/03_angle_cliff.png)

*↑ 崖は alpha = 1.39 deg(84 分角)。*

[![鏡像点は厳密に 2t 動くが、表面誤差になるのはその法線成分(|n.x| の RMS = 0.50)だけ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/05_offset_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/05_offset_cliff.png)

*↑ 鏡像点は厳密に 2t 動くが、表面誤差になるのはその法線成分(|n.x| の RMS = 0.50)だけ。*

[![欠損のまま推定した面で復元すると、欠損部の全体が一様にずれる(位置ずれの署名)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/07_controls_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/07_controls_maps.png)

*↑ 欠損のまま推定した面で復元すると、欠損部の全体が一様にずれる(位置ずれの署名)。*

[![色は「鏡像 - 真値」。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/09_false_symmetry_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/09_false_symmetry.png)

*↑ 色は「鏡像 - 真値」。*

```
py -3.11 examples/poc_symmetry_restoration.py
```

ソース: [examples/poc_symmetry_restoration.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_symmetry_restoration.py)

この回が作った図は全部で **10 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_symmetry_restoration)

使用 op(ノートへ): [`detect_reflection_symmetry`](https://furuse.work/ops/3d/symmetry/detect_reflection_symmetry.html) · [`fill_holes`](https://furuse.work/ops/2d/region/fill_holes.html) · [`fit_plane_3d`](https://furuse.work/ops/3d/geometry/fit_plane_3d.html) · [`icp_point2point_3d`](https://furuse.work/ops/3d/refine/icp_point2point_3d.html) · [`normalize`](https://furuse.work/ops/shape2d/descriptor/normalize.html) · [`reflect_points`](https://furuse.work/ops/3d/symmetry/reflect_points.html) · [`reflection_symmetry_score`](https://furuse.work/ops/3d/symmetry/reflection_symmetry_score.html)

## No.2026.146 —— 無限に寄り続ける絵と、回り続ける立体 ―― 「戻ってくること」を真値にする

[![無限に寄り続ける絵と、回り続ける立体 ―― 「戻ってくること」を真値にする](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/01_zoom_steps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/01_zoom_steps.png)

*↑ **無限に寄り続ける絵と、回り続ける立体 ―― 「戻ってくること」を真値にする** ―― 終わらない動きには、終わりを見なくても採点できる等式がある —— **無限ズーム**は自己相似比だけ寄ると絵が**画素単位で**元に戻り、**立体回転**は 2π で元に戻る。どちらも「最後に頭へ戻す」編集ではなく構成から従うので、真値は厳密に 0 差になる。素材は**パスカルの三角形 mod 2**(規則 90 の真値そのもの)で、空隙の階層は桁を数えるだけで閉形式に出る: `I = floor(u·2^D)`、`J = floor(v·2^D)`、`b` を `I & J` の最上位ビット位置として**深さ `d = D − b`**。`u → u/2` で `I → I>>1` だから `b` は 1 減り `d` は 1 増える —— **だからいくら寄っても解像度が落ちない**(拡大した画像を引き伸ばしているのではなく、画素ごとに整数のビット判定で決めている)。1 周 8 倍のズームで frame(T) と frame(0) の最大差は **0.0e+00**。★★芯 1: **測った次元がズームで 1 ミリも動かない。** 既存の `fractal_dimension` をズーム 6 段に掛けると標準偏差が**厳密に 0**、しかも近似の深さと画素の細かさが合ったときは **log2(3) = 1.584962500721 に差 8.9e-16 で一致**する —— 近似ではない。★★芯 2: **同じ op が 0.0 を返す場面がある。** 画素より細かい近似(深さ 9)を渡すと 0.0 になるが、これは「構造が無い」ではなく「**画素より細かい**」の意味で、実際その近似は 262,144 画素中**前景 0 画素**まで消えている。数字だけ見る門はここで嘘をつく。★★芯 3: **2π は浮動小数では閉じない。** 角度 `2πi/T` で作った回転は i=T で `sin(2π) = -2.45e-16` のぶんだけずれ、法線に **1.40e-12** が残る。周期を**整数の剰余**で閉じると **0.0e+00**(厳密) —— 周期境界 PoC と同じ型の教訓。★★芯 4: **外した予言を 1 つそのまま残してある。** 立方体のシルエット面積は正射影なら `a²(|cosθ|+|sinθ|)`。実測の残差 2% を見て「marching cubes の面取りのせい」と読んだが**外れ**で、距離を 6 → 96 に伸ばすと厳密な立方体も marching cubes も同じように 0.128 → 0.004 まで落ちた —— 床の正体は**透視投影**だった。面取りのぶんは距離では直らない別の量に出る: シルエット面積の最大/最小は厳密な立方体では √2 = 1.4142 に収束する(1.4167)のに、marching cubes では **1.3958 で止まる**。**1 つの残差を 2 つの原因に切り分けたのは、距離を振ったから。**ほかに、素材(深さの場)の 4 回対称は厳密 0 なのに**絵にすると 1.1e-16 崩れる**(数学ではなく 2×2 平均の足す順番)、ジャイロイドの 2 つの迷路の体積比は奇対称から 0.500000000000。**新しい op は 1 つも足していない。**検査 25 件・図 15 枚(動く図 2 枚を含む)。*

[![右は 2 枚の差をそのまま出したもので、**全画素が 0**(最大差 0.0e+00)。倍率を 8 倍にしたのに同じ絵になるのは、色の巡回(周期 3)が深さの巡回とちょうど噛み合うから。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/02_zoom_seam_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/02_zoom_seam.png)

*↑ 測定の図 ―― 右は 2 枚の差をそのまま出したもので、**全画素が 0**(最大差 0.0e+00)。倍率を 8 倍にしたのに同じ絵になるのは、色の巡回(周期 3)が深さの巡回とちょうど噛み合うから。*

[![**空隙の深さ(色 = 深さ、深いほど濃い)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/04_zoom_depth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/04_zoom_depth.png)

*↑ **空隙の深さ(色 = 深さ、深いほど濃い)。*

[![左から深さ 5..9。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/06_dimension_vs_level_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/06_dimension_vs_level.png)

*↑ 左から深さ 5..9。*

[![正射影ならシルエット面積は `a²(|cosθ| + |sinθ|)` で、45 度が最大(√2 倍)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/10_cube_steps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/10_cube_steps.png)

*↑ 正射影ならシルエット面積は `a²(|cosθ| + |sinθ|)` で、45 度が最大(√2 倍)。*

[![厳密な立方体は √2 = 1.4142 に収束する(1.4167)のに、marching cubes で取り出した面は **1.3958 で止まる**。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/13_mesh_is_not_a_cube_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/13_mesh_is_not_a_cube.png)

*↑ 厳密な立方体は √2 = 1.4142 に収束する(1.4167)のに、marching cubes で取り出した面は **1.3958 で止まる**。*

[![止めどきは呼んだ側が決める。24 コマで 1 周(8 倍)、そこから先は同じ絵が続く。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/03_zoom_loop.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/03_zoom_loop.gif)

*↑ 動く図 ―― 止めどきは呼んだ側が決める。24 コマで 1 周(8 倍)、そこから先は同じ絵が続く。*

[![1 周 18 コマ。添字の剰余で角度を作っているので、18 コマ目は 0 コマ目と画素単位で同じ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/08_solid_loop.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids/08_solid_loop.gif)

*↑ 動く図 ―― 1 周 18 コマ。添字の剰余で角度を作っているので、18 コマ目は 0 コマ目と画素単位で同じ。*

```
py -3.11 examples/poc_endless_zoom_and_turning_solids.py
```

ソース: [examples/poc_endless_zoom_and_turning_solids.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_endless_zoom_and_turning_solids.py)

この回が作った図は全部で **15 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_endless_zoom_and_turning_solids)

使用 op(ノートへ): [`fractal_dimension`](https://furuse.work/ops/2d/features/fractal_dimension.html) · [`gyroid_isosurface`](https://furuse.work/ops/3d/surface/gyroid_isosurface.html) · [`mesh_volume`](https://furuse.work/ops/3d/mesh_process/mesh_volume.html) · [`perpetual_loop_seam`](https://furuse.work/ops/generative/loop/perpetual_loop_seam.html) · [`phong_shade`](https://furuse.work/ops/3d/render/phong_shade.html)

## No.2026.149 —— 4 次元の主張を、3 次元の平凡な op で採点する

[![4 次元の主張を、3 次元の平凡な op で採点する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/02_nested_tori_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/02_nested_tori.png)

*↑ **4 次元の主張を、3 次元の平凡な op で採点する** ―― **4 次元の位相と代数は、この箱にある 3 次元の産業用 op で厳密に採点できる** —— `fit_circle_3d`(点群に円を当てる)、`mesh_volume`(閉メッシュの符号つき体積)、`curve3d_tube_mesh`、`render_mesh`。ホップ束は S³ を S² 上の円の束に分ける。S³ の点を (z₁, z₂) ∈ C² と見ると、S² の 1 点 (θ, φ) の上の**繊維**は `q(t) = (cos(θ/2) e^{it}, sin(θ/2) e^{i(t+φ)})` という円で、**立体射影しても厳密に円のまま**(ヴィラルソー円)。★★芯 1: **4 次元の円が 2 次元の点になる。** 1 本の繊維をホップ写像で落とすと S² 上の広がりが **8.9e-16** —— 256 点すべてが 1 点に潰れる。★★芯 2: **その円を「点群に円を当てる op」が認める。** 立体射影した繊維の半径は緯度によって 0.70 から 7.34 まで変わるのに、`fit_circle_3d` の残差はどれも **1e-14 台**、平面からの外れも同じ桁。近似ではなく定理。★★芯 3: **2 本の繊維は必ず 1 回だけ絡む —— その整数が積分から出て、寄る速さまで予言できる。** ガウスの絡み数を離散化すると 4 通りの組すべてで 1 に寄り、**分割数を 2 倍にすると誤差がちょうど 1/4**(実測の比 **4.01 / 4.00 / 4.00 / 4.00**)—— **収束の次数が 1/n² だという予言が当たっている**。★★芯 4: **4 次元の回転は 2 枚の面で同時に起きて、比が有理のときだけ閉じる。** 超立方体(頂点 16・辺 32・面 24・胞 8、V − E + F − C = **0**、一辺 2 の超体積 **16.000000000000000**)を xy 面と zw 面で同時に回すと、比 1:2 / 2:3 / 3:4 は 60 歩でちょうど戻る(差 **0.0e+00**、途中の最小の隔たりは 0.23 以上なので「動いていないから一致した」ではない)。ところが比 1:φ(黄金比)は刻みを 400 に細かくして 20,000 歩まで回しても最小の隔たり **0.0257** で 0 に落ちない。★周期は**角度でなく整数の剰余**で閉じている。★★芯 5: **管の体積の誤差は、2 つに厳密に分かれる。** 真値を 2 段に置く —— A =「円断面・円中心線」、B =「**正 m 角形**断面・円中心線」。すると **B との相対差が断面の角数にまったく依らない**(同じ中心線なら m = 24 / 48 / 96 で差 **7.8e-16** 以内)—— **断面の粗さと中心線の粗さは独立に効く**。断面の効果は閉形式どおり **1/m²** で消える(比 3.99 / 4.00)。★★**外した予言を残してある。** 中心線の効果は 1/n² だと読んだが**外れ**で、点数を 2 倍・4 倍にすると **2.09 倍・4.15 倍**、つまり **1/n** でしか消えない —— 折れ線の周長は 1/n² で真値に寄るので、**残った差の原因は周長ではない**(継ぎ目の肉厚)。だから**片方のノブだけでは届かない**: 断面 96 角だけなら −0.001588、中心線 1600 点だけなら −0.003064 で止まり、両方回して −0.000925。**新しい op は 1 つも足していない。** 検査 19 件・図 10 枚(動く図 3 枚を含む)。*

[![ホップ束の繊維 4 本を立体射影して管にしたもの。★**4 次元では 4 本とも同じ大きさの円**なのに、3 次元へ写すと大きさが変わる —— それでも `fit_circle_3d` は 4 本すべてを **残差 1.4e-14** で円](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/01_hopf_fibers_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/01_hopf_fibers.png)

*↑ 測定の図 ―― ホップ束の繊維 4 本を立体射影して管にしたもの。★**4 次元では 4 本とも同じ大きさの円**なのに、3 次元へ写すと大きさが変わる —— それでも `fit_circle_3d` は 4 本すべてを **残差 1.4e-14** で円と認める。どの 2 本も**必ず 1 回だけ絡む**。*

[![`fit_circle_3d` に 200 点を食わせた残差。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/04_circle_fit_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/04_circle_fit.png)

*↑ `fit_circle_3d` に 200 点を食わせた残差。*

[![ガウスの積分で求めた絡み数の、**整数 1** からの差。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/05_linking_vs_n_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/05_linking_vs_n.png)

*↑ ガウスの積分で求めた絡み数の、**整数 1** からの差。*

[![真値 B は「**正 m 角形**断面・円中心線」の体積。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/08_tube_error_split_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/08_tube_error_split.png)

*↑ 真値 B は「**正 m 角形**断面・円中心線」の体積。*

[![断面の効果は閉形式どおり **1/m²**(比 3.99 / 4.00)で消えるのに、中心線の効果は **1/n**(比 2.09 / 4.15)でしか消えない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/09_tube_two_knobs_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/09_tube_two_knobs.png)

*↑ 断面の効果は閉形式どおり **1/m²**(比 3.99 / 4.00)で消えるのに、中心線の効果は **1/n**(比 2.09 / 4.15)でしか消えない。*

[![同じ 4 本を視点だけ回して見たもの。★**視点の周期は角度でなく整数の剰余で閉じている**(24 コマ目が 0 コマ目と同じ式になる)ので、継ぎ目が出ない。絡み方は視点を変えても変わらない —— 絡み数は**位相の量**だから。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/03_hopf_turn.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/03_hopf_turn.gif)

*↑ 動く図 ―― 同じ 4 本を視点だけ回して見たもの。★**視点の周期は角度でなく整数の剰余で閉じている**(24 コマ目が 0 コマ目と同じ式になる)ので、継ぎ目が出ない。絡み方は視点を変えても変わらない —— 絡み数は**位相の量**だから。*

[![比 **1 : 2**(有理)。60 コマでちょうど元に戻る —— 戻ったときの差は **0.0e+00**。★角度は**整数の剰余**で作っているので、有理な比なら継ぎ目が出ない。描いているのは 4 次元の超立方体を**2 枚の面で同時に](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/06_tesseract_rational.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/06_tesseract_rational.gif)

*↑ 動く図 ―― 比 **1 : 2**(有理)。60 コマでちょうど元に戻る —— 戻ったときの差は **0.0e+00**。★角度は**整数の剰余**で作っているので、有理な比なら継ぎ目が出ない。描いているのは 4 次元の超立方体を**2 枚の面で同時に回して**から w を落とした影。辺は 32 本とも同じ長さなのに、影では伸び縮みする。*

[![比 **1 : φ**(無理、黄金比)。この 60 コマでは戻らない。別に**刻みを 400 に細かくして 20,000 歩**まで回しても、最小の隔たりは **0.0257** で 0 に落ちない。★角度は**整数の剰余**で作っているの](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/07_tesseract_irrational.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools/07_tesseract_irrational.gif)

*↑ 動く図 ―― 比 **1 : φ**(無理、黄金比)。この 60 コマでは戻らない。別に**刻みを 400 に細かくして 20,000 歩**まで回しても、最小の隔たりは **0.0257** で 0 に落ちない。★角度は**整数の剰余**で作っているので、有理な比なら継ぎ目が出ない。描いているのは 4 次元の超立方体を**2 枚の面で同時に回して**から w を落とした影。辺は 32 本とも同じ長さなのに、影では伸び縮みする。*

```
py -3.11 examples/poc_four_dimensions_by_three_d_tools.py
```

ソース: [examples/poc_four_dimensions_by_three_d_tools.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_four_dimensions_by_three_d_tools.py)

この回が作った図は全部で **10 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_four_dimensions_by_three_d_tools)

使用 op(ノートへ): [`curve3d_tube_mesh`](https://furuse.work/ops/3d/surface/curve3d_tube_mesh.html) · [`fit_circle_3d`](https://furuse.work/ops/3d/geometry/fit_circle_3d.html) · [`mesh_volume`](https://furuse.work/ops/3d/mesh_process/mesh_volume.html)

