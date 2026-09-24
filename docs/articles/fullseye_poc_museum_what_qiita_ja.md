> **言語 / Language**: **日本語** · [English](https://github.com/furuse-kazufumi/fullseye/blob/master/docs/articles/fullseye_poc_museum_what_qiita_en.md)

# 紙面の計測館 —— 何を測るかの棟(産業検査・寸法計測・医用生物・天文環境)

> **[紙面の計測館 総合案内](https://qiita.com/furuse-kazufumi/items/c1606bcfa2085d204ad6)** の一棟です。ほかの棟・用語・テーゼは案内にあります。

この棟には **84 点**を掛けています。番号は**収蔵番号**で、棟を移しても分けても変わりません。

> 各展示の「使用 op」から、その op のノート(型契約・罠・図・Studio で走るプログラム)へ飛べます: [オペレータ目録](https://furuse.work/OP_CATALOG.html) / [op ノートの索引](https://furuse.work/ops/INDEX.html)。

### 産業検査ウィング ―― 合格の数字と不合格の数字は両立する

検査ラインの数字は合否に直結するので、1 つの指標に畳みたくなります。この部屋の 10 点は、畳んだ瞬間に消えるものを並べたものです。まとめた ROC が種類別の盲点を隠す織物、MTF が合格のまま黒レベルが不合格になる迷光、読取率だけ見ると寛容なデコーダが良く見えるバーコード。

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

使用 op(ノートへ): [`spc_capability`](https://furuse.work/ops/spc/capability/spc_capability.html) · [`spc_cusum`](https://furuse.work/ops/spc/change/spc_cusum.html) · [`spc_ewma`](https://furuse.work/ops/spc/change/spc_ewma.html) · [`spc_hotelling_t2`](https://furuse.work/ops/spc/multivariate/spc_hotelling_t2.html) · [`spc_xbar_r`](https://furuse.work/ops/spc/chart/spc_xbar_r.html)

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

使用 op(ノートへ): [`airy_pattern`](https://furuse.work/ops/optics/wave/airy_pattern.html) · [`create_funct_1d_pairs`](https://furuse.work/ops/oned/function/create_funct_1d_pairs.html) · [`derivate_funct_1d`](https://furuse.work/ops/oned/function/derivate_funct_1d.html) · [`get_y_value_funct_1d`](https://furuse.work/ops/oned/function/get_y_value_funct_1d.html) · [`invert_funct_1d`](https://furuse.work/ops/oned/function/invert_funct_1d.html) · [`mtf_diffraction`](https://furuse.work/ops/optics/imaging/mtf_diffraction.html) · [`psf_to_mtf`](https://furuse.work/ops/optics/imaging/psf_to_mtf.html)

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

### 寸法・形状計測ウィング ―― 偏りと散らばりは別々に持つ

「この部品の幅は 50.50 画素だ」と言い切るには、偏り(いつも同じ向きにずれる分)と散らばり(撮るたびに変わる分)を別々に出す必要があります。合否は偏りで決まり、繰り返し精度は散らばりで決まる。1 つの「誤差」にまとめた瞬間、どちらの対策を打つべきかが分からなくなります。

この部屋の 10 点は、符号つき距離関数の部品、インボリュート歯形、指定 PSD の粗さ面、白色干渉のスタック、解析スペックル、Frocht の応力場、対称な合成頭蓋と、いずれも閉形式か解析描画で真値を握った上で、キャリパーや相関や位相の読みを採点しています。

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

```
py -3.11 examples/poc_dic_strain.py
```

ソース: [examples/poc_dic_strain.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dic_strain.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_dic_strain)

使用 op(ノートへ): [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`strain_from_displacement`](https://furuse.work/ops/piv/solid/strain_from_displacement.html)

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

```
py -3.11 examples/poc_interferometry_step.py
```

ソース: [examples/poc_interferometry_step.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_interferometry_step.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_interferometry_step)

使用 op(ノートへ): [`csi_design`](https://furuse.work/ops/interferometry/design/csi_design.html) · [`csi_height_map`](https://furuse.work/ops/interferometry/surface/csi_height_map.html) · [`csi_stack_simulate`](https://furuse.work/ops/interferometry/simulate/csi_stack_simulate.html) · [`decode_fringe`](https://furuse.work/ops/3d/structured_light/decode_fringe.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`synthesize_fringes`](https://furuse.work/ops/3d/structured_light/synthesize_fringes.html)

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

[![勾配ゼロ + 真の平均音速がゼロ点。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/05_controls_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/05_controls.png)

*↑ 勾配ゼロ + 真の平均音速がゼロ点。*

[![beamform_delay_sum の角度スペクトルの -3 dB 幅。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/09_beamwidth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/09_beamwidth.png)

*↑ beamform_delay_sum の角度スペクトルの -3 dB 幅。*

[![2 点キャスト(表層と海底だけ)の一定勾配当てはめ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/13_thermocline_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/13_thermocline.png)

*↑ 2 点キャスト(表層と海底だけ)の一定勾配当てはめ。*

```
py -3.11 examples/poc_multibeam_bathymetry.py
```

ソース: [examples/poc_multibeam_bathymetry.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_multibeam_bathymetry.py)

この回が作った図は全部で **16 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_multibeam_bathymetry)

使用 op(ノートへ): [`beamform_delay_sum`](https://furuse.work/ops/rangedoppler/beamform/beamform_delay_sum.html) · [`beamform_doa`](https://furuse.work/ops/rangedoppler/beamform/beamform_doa.html) · [`dem_slope`](https://furuse.work/ops/dem/surface/dem_slope.html) · [`find_peaks`](https://furuse.work/ops/oned/signal/find_peaks.html) · [`interp_scattered`](https://furuse.work/ops/math/interp_poly/interp_scattered.html) · [`peak_subbin`](https://furuse.work/ops/oned/signal/peak_subbin.html) · [`snell_angle`](https://furuse.work/ops/3d/optics/snell_angle.html)

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

[![左下 2 枚が「壊れる予報」。どちらもマスクで外せる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_photoelasticity/02_unwrap_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_photoelasticity/02_unwrap.png)

*↑ 測定の図 ―― 左下 2 枚が「壊れる予報」。どちらもマスクで外せる。*

```
py -3.11 examples/poc_photoelasticity.py
```

ソース: [examples/poc_photoelasticity.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_photoelasticity.py)

この回が作った図は全部で **2 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_photoelasticity)

使用 op(ノートへ): [`mueller_apply`](https://furuse.work/ops/optics/polarization/mueller_apply.html) · [`mueller_element`](https://furuse.work/ops/optics/polarization/mueller_element.html) · [`unwrap_phase_2d`](https://furuse.work/ops/3d/structured_light/unwrap_phase_2d.html)

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

```
py -3.11 examples/poc_stockpile_volume.py
```

ソース: [examples/poc_stockpile_volume.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_stockpile_volume.py)

この回が作った図は全部で **6 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_stockpile_volume)

使用 op(ノートへ): [`dem_hillshade`](https://furuse.work/ops/dem/shading/dem_hillshade.html) · [`dem_slope`](https://furuse.work/ops/dem/surface/dem_slope.html) · [`dem_viewshed`](https://furuse.work/ops/dem/visibility/dem_viewshed.html) · [`interp_scattered`](https://furuse.work/ops/math/interp_poly/interp_scattered.html) · [`moment_axes`](https://furuse.work/ops/3d/match_pose/moment_axes.html)

## No.2026.038 —— クリープ試験のひずみ履歴 ―― 累積か直接か

[![クリープ試験のひずみ履歴 ―― 累積か直接か](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/01_speckle_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/01_speckle.png)

*↑ **クリープ試験のひずみ履歴 ―― 累積か直接か** ―― 1 時間のクリープを 25 コマ撮り、隣接コマの累積と基準フレームとの直接比較でひずみ履歴を出した図。終端で累積 61 µε / 直接 1878 µε と累積が 31 倍良く、教科書の「時刻で入れ替わる」交点は無い(入れ替わるのは雑音の軸)。コマを 24 → 4 歩に間引くと累積は -60 → -606 µε と悪化 ―― 効くのは歩数でなく 1 歩あたりの変形量。*

[![直接の偏りだけが伸びる。累積は偏りも散らばりも頭打ちで、しかも散らばりより偏りのほうが大きい ——ランダムウォークではない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/02_errors_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/02_errors.png)

*↑ 測定の図 ―― 直接の偏りだけが伸びる。累積は偏りも散らばりも頭打ちで、しかも散らばりより偏りのほうが大きい ——ランダムウォークではない。*

[![因果フィルタの偏りは遅れ (w-1)/2 の閉形式にほぼ乗る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/03_rate_tradeoff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/03_rate_tradeoff.png)

*↑ 因果フィルタの偏りは遅れ (w-1)/2 の閉形式にほぼ乗る。*

[![予測 = w=1 の偏り + 閉形式(中央はなまり、因果は遅れ)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/04_rate_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/04_rate_table.png)

*↑ 予測 = w=1 の偏り + 閉形式(中央はなまり、因果は遅れ)。*

```
py -3.11 examples/poc_strain_history.py
```

ソース: [examples/poc_strain_history.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_strain_history.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_strain_history)

使用 op(ノートへ): [`moving_average_window`](https://furuse.work/ops/videostream/window/moving_average_window.html) · [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`piv_error_stats`](https://furuse.work/ops/piv/assess/piv_error_stats.html) · [`piv_multipass`](https://furuse.work/ops/piv/estimate/piv_multipass.html) · [`piv_sample_at_windows`](https://furuse.work/ops/piv/assess/piv_sample_at_windows.html) · [`piv_synth_pair`](https://furuse.work/ops/piv/synth/piv_synth_pair.html) · [`poly_fit`](https://furuse.work/ops/math/interp_poly/poly_fit.html)

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

この部屋の 4 点は、真値に「どれとどれが重なっているか」「面積と DNA 量が別々にばらつく」「分岐則を厳密に満たす木」といった、ラベル画像だけでは残らない情報を持たせています。実データに差し替えるときも、ラベル画像だけを真値と呼ぶと主題そのものが消える、と各 docstring に書いてあります。

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

```
py -3.11 examples/poc_wound_area_tracking.py
```

ソース: [examples/poc_wound_area_tracking.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_wound_area_tracking.py)

この回が作った図は全部で **5 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_wound_area_tracking)

使用 op(ノートへ): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_select_largest`](https://furuse.work/ops/blob/select/blob_select_largest.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`warp_by_plane`](https://furuse.work/ops/3d/plane_sweep_stereo/warp_by_plane.html)

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

### 天文・環境ウィング ―― 位置で偏り、真値の定義で反転する

星の明るさと位置、太陽の縁、全天の雲量、海氷の密接度、畑の被覆率、地形、河川の水位。対象は遠く、真値は普通手に入りません。この部屋の 8 点はそれを逆手に取り、天球座標・球冠の立体角・Eddington の周辺減光・国土地理院の標高タイルといった閉形式や公開データから真値を置いています。

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

```
py -3.11 examples/poc_dem_terrain.py
```

ソース: [examples/poc_dem_terrain.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dem_terrain.py)

この回が作った図は全部で **4 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_dem_terrain)

使用 op(ノートへ): [`dem_aspect`](https://furuse.work/ops/dem/surface/dem_aspect.html) · [`dem_curvature`](https://furuse.work/ops/dem/surface/dem_curvature.html) · [`dem_fill_sinks`](https://furuse.work/ops/dem/hydrology/dem_fill_sinks.html) · [`dem_flow_accumulation`](https://furuse.work/ops/dem/hydrology/dem_flow_accumulation.html) · [`dem_hillshade`](https://furuse.work/ops/dem/shading/dem_hillshade.html) · [`dem_sky_view_factor`](https://furuse.work/ops/dem/visibility/dem_sky_view_factor.html) · [`dem_slope`](https://furuse.work/ops/dem/surface/dem_slope.html)

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

```
py -3.11 examples/poc_river_surface_velocity.py
```

ソース: [examples/poc_river_surface_velocity.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_river_surface_velocity.py)

この回が作った図は全部で **12 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_river_surface_velocity)

使用 op(ノートへ): [`highpass_image`](https://furuse.work/ops/2d/frequency/highpass_image.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`piv_ensemble_correlate`](https://furuse.work/ops/piv/estimate/piv_ensemble_correlate.html) · [`piv_error_stats`](https://furuse.work/ops/piv/assess/piv_error_stats.html) · [`piv_outlier_mask`](https://furuse.work/ops/piv/validate/piv_outlier_mask.html) · [`piv_replace_outliers`](https://furuse.work/ops/piv/validate/piv_replace_outliers.html) · [`piv_sample_at_windows`](https://furuse.work/ops/piv/assess/piv_sample_at_windows.html) · [`piv_to_velocity`](https://furuse.work/ops/piv/field/piv_to_velocity.html) · [`sigma_clip_stack`](https://furuse.work/ops/astrostack/stack/sigma_clip_stack.html) · [`warp_by_plane`](https://furuse.work/ops/3d/plane_sweep_stereo/warp_by_plane.html)

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




---

**この展示館は Claude Code と一緒に作りました。** 問いと方向決めは私、実装・掃引・対照群・敵対レビューは Claude Code、という分業です。53 本の PoC を 2 日で走らせて図まで揃えられたのは、この運用のおかげです。試してみたい方は、こちらの招待リンクから **1 週間の無料トライアル** が使えます: [claude.ai/referral/0sqPw8E_lw](https://claude.ai/referral/0sqPw8E_lw)

面白い展示が 1 つでもあったら、**いいね・ストック**をもらえると助かります。どのウィングを次に増やすかは反応を見て決めるつもりなので、「自分の分野のこれが欲しい」もコメントで教えてください。実データに差し替えて崖の位置が変わった話は、いちばん聞きたい話です。
