<!-- generated -->

### 産業検査ウィング ―― 合格の数字と不合格の数字は両立する

検査ラインの数字は合否に直結するので、1 つの指標に畳みたくなります。この部屋の 10 点は、畳んだ瞬間に消えるものを並べたものです。まとめた ROC が種類別の盲点を隠す織物、MTF が合格のまま黒レベルが不合格になる迷光、読取率だけ見ると寛容なデコーダが良く見えるバーコード。

真値はどれも自分で仕込んであります。周期地の閉形式、レーザー断面の h(x)、1 次元熱伝導の解析解、閉形式の欠陥周波数。だから「検出できました」の先にある「どこで検出できなくなるか」を、しきい値を後から合わせずに測れます。

もう 1 つの共通点は、壊れ方が連続ではなく崖であること。傾き 15 度と 16 度、時間窓 25 秒と 4 秒、ΔT 1.6 K ―― その位置は幾何か物理で先に計算できる場合が多く、計算できたものは実測と突き合わせてあります。

## 1. 周期のある地に埋もれた欠陥 ―― まとめた ROC が隠すもの

[![周期のある地に埋もれた欠陥 ―― まとめた ROC が隠すもの](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fabric_defect/04_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fabric_defect/04_scene.png)

*↑ **周期のある地に埋もれた欠陥 ―― まとめた ROC が隠すもの** ―― 周期 8 px の織り地に線・斑点・ムラの 3 種の欠陥を埋め、検出器のスコア地図と種類別の ROC を並べた図。現場でいちばん普通の「格子除去 + 低周波除去」はまとめた AUC 0.8113 で合格に見えるのに、ムラだけは 0.4746 とでたらめ以下。低周波を落とす 1 行が照明ムラと一緒に欠陥のムラを消していた ―― 外すだけで 0.9998 に戻る。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fabric_defect/01_auc_by_type_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fabric_defect/01_auc_by_type.png)

*↑ 測定の図*

```
py -3.11 examples/poc_fabric_defect.py
```

ソース: [examples/poc_fabric_defect.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_fabric_defect.py)



## 2. レーザー三角測量の断面から溶接ビードを測る ―― 測れなかったところを 0 と書く罪

[![レーザー三角測量の断面から溶接ビードを測る ―― 測れなかったところを 0 と書く罪](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_profile/01_laser_images_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_profile/01_laser_images.png)

*↑ **レーザー三角測量の断面から溶接ビードを測る ―― 測れなかったところを 0 と書く罪** ―― 輝線 1 本の行位置から断面 h(x) を戻し、余盛高さ・幅・アンダーカットを読む図。ゼロ点(各列の最大値の行)に対し重心は 9.3 倍良く、雑音ゼロなら対数放物線は機械精度(素の放物線と 12 桁差)なのに、雑音 1 % では 0.00272 対 0.00260 mm で区別がつかない。スパッタ 5 点で 3 種の推定量がそろって 0.11 mm(40 倍)へ壊れる ―― 効くのは精緻化ではなく、どのピークを選ぶか。*

[![0 で埋めた線は影の区間で h=0 に張り付き、左のアンダーカットが消えて偽のつま先ができる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_profile/02_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_profile/02_profile.png)

*↑ 測定の図 ―― 0 で埋めた線は影の区間で h=0 に張り付き、左のアンダーカットが消えて偽のつま先ができる。*

```
py -3.11 examples/poc_weld_bead_profile.py
```

ソース: [examples/poc_weld_bead_profile.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_weld_bead_profile.py)

使用 op(ノートへ): [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`median`](https://furuse.work/ops/2d/rank/median.html)

## 3. コンクリートのひび割れ幅は 1 画素より細い ―― 数える幅と、積分する幅

[![コンクリートのひび割れ幅は 1 画素より細い ―― 数える幅と、積分する幅](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width/02_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width/02_scene.png)

*↑ **コンクリートのひび割れ幅は 1 画素より細い ―― 数える幅と、積分する幅** ―― 1 px = 0.20 mm の視野で幅 0.05〜2.0 mm のひび割れを振り、二値化して数える幅と輝度欠損を積分する幅を並べた図。二値化は 0.20 mm 以下で何も返さず、真値 0.25〜0.40 mm の 4 条件が全部 0.200 mm を返す。積分法は 0.05 mm(0.25 px)まで連続に追えるが、照明が曲がると 1 次のベースラインでは +0.1741 mm の下駄が乗る(2 次なら +0.0062 mm)。*

[![2 値化の 2 本は階段。0.20 mm(1 px)以下ではマスクが空になり 0(= 未検出)へ落ちる。積分法は 0.05 mm (0.25 px)まで直線 y=x に乗る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width/01_width_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width/01_width_sweep.png)

*↑ 測定の図 ―― 2 値化の 2 本は階段。0.20 mm(1 px)以下ではマスクが空になり 0(= 未検出)へ落ちる。積分法は 0.05 mm (0.25 px)まで直線 y=x に乗る。*

```
py -3.11 examples/poc_crack_width.py
```

ソース: [examples/poc_crack_width.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_crack_width.py)

使用 op(ノートへ): [`distance_transform`](https://furuse.work/ops/2d/region/distance_transform.html) · [`sk_medial`](https://furuse.work/ops/2d/region/sk_medial.html) · [`skeleton`](https://furuse.work/ops/2d/region/skeleton.html) · [`thinning`](https://furuse.work/ops/2d/region/thinning.html) · [`vol_distance_transform`](https://furuse.work/ops/3d/medial/vol_distance_transform.html)

## 4. 迷光がコントラスト計測を壊す ―― MTF 合格・黒レベル不合格は両立する

[![迷光がコントラスト計測を壊す ―― MTF 合格・黒レベル不合格は両立する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_veiling_glare/04_glare_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_veiling_glare/04_glare_scene.png)

*↑ **迷光がコントラスト計測を壊す ―― MTF 合格・黒レベル不合格は両立する** ―― PSF の裾だけを重くした像で、刃のエッジの MTF と黒四角の黒レベルを同時に測った図。裾の割合 0 → 0.20 で MTF50 は 0.2347 → 0.2249 cyc/px(-4.2 %、合格のまま)なのに、黒レベルは 0.0 → 15.7 %(不合格)。±16 px の測定窓には裾のエネルギーの 6 % しか入らない ―― 迷光は測る範囲を宣言しないと数字にならない。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_veiling_glare/01_verdict_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_veiling_glare/01_verdict.png)

*↑ 測定の図*

```
py -3.11 examples/poc_veiling_glare.py
```

ソース: [examples/poc_veiling_glare.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_veiling_glare.py)

使用 op(ノートへ): [`airy_pattern`](https://furuse.work/ops/optics/wave/airy_pattern.html) · [`mtf_diffraction`](https://furuse.work/ops/optics/imaging/mtf_diffraction.html) · [`psf_to_mtf`](https://furuse.work/ops/optics/imaging/psf_to_mtf.html)

## 5. ディスプレイ検査のモアレは「本物のムラ」と区別できるか

[![ディスプレイ検査のモアレは「本物のムラ」と区別できるか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_moire_screen/04_moire_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_moire_screen/04_moire_scene.png)

*↑ **ディスプレイ検査のモアレは「本物のムラ」と区別できるか** ―― 画素格子と表示の縞が干渉して作るモアレと、本物の輝度ムラを同じ像に重ねた図。ならしの σ = 8 px で合計誤差 +0.9 % ―― 内訳は漏れ +8.3 % と減衰 -7.4 % の打ち消し。基本波のうなりが安全に見える k = 0.67 でも 3 次高調波がムラの帯に落ち、漏れは真値の +202.6 %。*

[![σ≈8 px で漏れと減衰が釣り合う。合計だけ見ると「良い測り方」に見える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_moire_screen/01_failure_split_plot_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_moire_screen/01_failure_split_plot.png)

*↑ 測定の図 ―― σ≈8 px で漏れと減衰が釣り合う。合計だけ見ると「良い測り方」に見える。*

```
py -3.11 examples/poc_moire_screen.py
```

ソース: [examples/poc_moire_screen.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_moire_screen.py)

使用 op(ノートへ): [`background_flatten`](https://furuse.work/ops/3d/surface_fit/background_flatten.html) · [`fft_image`](https://furuse.work/ops/2d/frequency/fft_image.html) · [`gauss_image`](https://furuse.work/ops/2d/smoothing/gauss_image.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html)

## 6. 転がり軸受の異常診断 ―― どこまで雑音に埋もれても当てられるか

[![転がり軸受の異常診断 ―― どこまで雑音に埋もれても当てられるか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bearing_diagnosis/01_envelope_vs_raw_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bearing_diagnosis/01_envelope_vs_raw.png)

*↑ **転がり軸受の異常診断 ―― どこまで雑音に埋もれても当てられるか** ―― 閉形式の欠陥周波数(BPFO 104.556 Hz)で合成した衝撃列を雑音に沈め、生スペクトルと包絡線スペクトルの検出率を並べた図。10/10 を保てた最悪の SNR は生 -0.9 dB、包絡線 -18.4 dB で 17.5 dB の差。ただし欠陥の無い記録でも大域顕著さは 43 まで出る ―― しきい値を null から決めていなければ、この PoC 自体が偽陽性を出していた。*

[![どちらも最悪条件では 0 に落ちる。包絡線は万能ではなく、崖が悪い SNR 側へ動くだけ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bearing_diagnosis/02_detection_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bearing_diagnosis/02_detection_sweep.png)

*↑ 測定の図 ―― どちらも最悪条件では 0 に落ちる。包絡線は万能ではなく、崖が悪い SNR 側へ動くだけ。*

```
py -3.11 examples/poc_bearing_diagnosis.py
```

ソース: [examples/poc_bearing_diagnosis.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bearing_diagnosis.py)

使用 op(ノートへ): [`bearing_defect_frequencies`](https://furuse.work/ops/acoustics/bearing/bearing_defect_frequencies.html) · [`envelope_spectrum`](https://furuse.work/ops/acoustics/bearing/envelope_spectrum.html) · [`spectral_kurtosis`](https://furuse.work/ops/acoustics/bearing/spectral_kurtosis.html) · [`synthesize_bearing_signal`](https://furuse.work/ops/acoustics/synthesis/synthesize_bearing_signal.html)

## 7. パルスサーモグラフィで内部欠陥の深さを測る

[![パルスサーモグラフィで内部欠陥の深さを測る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/02_depth_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/02_depth_map.png)

*↑ **パルスサーモグラフィで内部欠陥の深さを測る** ―― フラッシュ加熱後の表面温度を 1 次元熱伝導の厳密解で作り、剥離の深さを画像から当てる図。直径が深さの 4 倍以上なら数 % で当たるが、深さ 0.5 mm・直径 2 mm では +627 %。原因は横拡散ではなく当てはめる時間窓で、窓を 25 s → 4 s に切り詰めると -9 % に戻る。*

[![右下三角(直径が深さの 4 倍以上)は数 %。左上は横拡散で壊れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/01_depth_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermography_ndt/01_depth_table.png)

*↑ 測定の図 ―― 右下三角(直径が深さの 4 倍以上)は数 %。左上は横拡散で壊れる。*

```
py -3.11 examples/poc_thermography_ndt.py
```

ソース: [examples/poc_thermography_ndt.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_thermography_ndt.py)



## 8. カメラの熱ドリフトが寸法計測に効く量

[![カメラの熱ドリフトが寸法計測に効く量](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_drift_metrology/04_error_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_drift_metrology/04_error_maps.png)

*↑ **カメラの熱ドリフトが寸法計測に効く量** ―― 温度 ΔT で焦点距離・架台・主点が漂うカメラで一辺 40 mm のワークを測り、誤差を半径の 1 次式 a + b·R に分けた図。ΔT = 15 K で定数項 a = +224.5 ppm(片方だけ動かした対照条件 +225.3 ppm)。雑音の床(25 枚平均で 23 ppm)を超えるのは ΔT = 1.6 K から ―― それ以下では「温度の影響は見えない」が正しい報告。*

[![焦点距離ドリフトは R に依らない。主点ドリフトは R に比例(歪みを外す中心がずれるため)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_drift_metrology/01_separate_drifts_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_drift_metrology/01_separate_drifts.png)

*↑ 測定の図 ―― 焦点距離ドリフトは R に依らない。主点ドリフトは R に比例(歪みを外す中心がずれるため)。*

```
py -3.11 examples/poc_thermal_drift_metrology.py
```

ソース: [examples/poc_thermal_drift_metrology.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_thermal_drift_metrology.py)



## 9. 1 次元バーコードが読めなくなる境界 ―― 誤読と読み取り不能を分けて数える

[![1 次元バーコードが読めなくなる境界 ―― 誤読と読み取り不能を分けて数える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_barcode_1d/01_misread_split_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_barcode_1d/01_misread_split.png)

*↑ **1 次元バーコードが読めなくなる境界 ―― 誤読と読み取り不能を分けて数える** ―― 自作の簡易符号(実在規格ではない)を 4 通りに壊し、成功 / 誤読 / 読み取り不能を分けて数えた図。壊れ始めてからの 384 枚で、構造を検査する厳格デコーダは誤読 7.3 %、必ず 9 桁返す寛容デコーダは誤読 46.1 % ―― 成功率は寛容のほうが高い(47.7 % 対 40.1 %)。傾きの崖は幾何だけで決まり(予測 15.95 度)、実測は 15 度と 16 度のあいだ。*

[![小さい汚れは行が「読めてしまう」ので誤った票を投じる。大きい汚れは棄権するので多数決が効く。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_barcode_1d/02_smudge_nonmonotone_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_barcode_1d/02_smudge_nonmonotone.png)

*↑ 測定の図 ―― 小さい汚れは行が「読めてしまう」ので誤った票を投じる。大きい汚れは棄権するので多数決が効く。*

```
py -3.11 examples/poc_barcode_1d.py
```

ソース: [examples/poc_barcode_1d.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_barcode_1d.py)

使用 op(ノートへ): [`decode_barcode`](https://furuse.work/ops/2d/barcode/decode_barcode.html) · [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`vol_edge_probe`](https://furuse.work/ops/3d/probe/vol_edge_probe.html)

## 10. 2 値マトリクスコードを読む ―― 先に死ぬのはいつも幾何

[![2 値マトリクスコードを読む ―― 先に死ぬのはいつも幾何](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_matrix_code_reading/01_symbol_and_errors_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_matrix_code_reading/01_symbol_and_errors.png)

*↑ **2 値マトリクスコードを読む ―― 先に死ぬのはいつも幾何** ―― QR と同型のレイアウトに乱数ビットを置いた符号(誤り訂正なし)を、ぼけ・傾き・遮蔽で壊してビット誤り率を数えた図。ゼロ点は当てずっぽうの 0.5 に張り付き(0.526 / 0.507)、読める側は 0.0000。崖は傾き 78 度、位置検出パターンの遮蔽 2 モジュール ―― 真のホモグラフィを渡した条件と並べると、先に落ちるのはいつも定位。*

[![自力検出の線は sigma/m 0.50 を最後に途切れる(0.60 では位置検出パターンが見つからない)。標本化はそこでまだ BER 0.07 で読めている。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_matrix_code_reading/02_blur_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_matrix_code_reading/02_blur_cliff.png)

*↑ 測定の図 ―― 自力検出の線は sigma/m 0.50 を最後に途切れる(0.60 では位置検出パターンが見つからない)。標本化はそこでまだ BER 0.07 で読めている。*

```
py -3.11 examples/poc_matrix_code_reading.py
```

ソース: [examples/poc_matrix_code_reading.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_matrix_code_reading.py)

使用 op(ノートへ): [`adaptive_gauss_thresh`](https://furuse.work/ops/2d/segmentation/adaptive_gauss_thresh.html) · [`corner_response`](https://furuse.work/ops/2d/edges/corner_response.html) · [`illuminate`](https://furuse.work/ops/2d/gray/illuminate.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`sk_sauvola`](https://furuse.work/ops/2d/segmentation/sk_sauvola.html)

## 11. 溶接 X 線透過像の気孔 ―― 等級を 1 段間違える画像の割合で締める

[![溶接 X 線透過像の気孔 ―― 等級を 1 段間違える画像の割合で締める](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/01_scene_radiograph_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/01_scene_radiograph.png)

*↑ **溶接 X 線透過像の気孔 ―― 等級を 1 段間違える画像の割合で締める** ―― 板厚 10 mm + 円弧の余盛 + 球形気孔を Beer–Lambert で閉形式に描き、散乱・不鋭度・粒状雑音を足した透過像。固定しきい値のゼロ点は余盛のつま先を気孔に数える(塊 124 個、合計面積 15.19 mm²、真値 7.93)。検出の崖は CNR = 16.12·d² から先に予測でき、50 % 検出径は Rose の CNR = 4 では 0.50 mm と外れ、平滑化と最小面積 3 px を入れた予測 0.58 mm に対し実測 0.57 mm。背景推定 op の窓上限(矩形オープニング 9 px)は 2.0 mm から検出率 50 % を割り 2.5 mm で 0 % の崖になる ―― op を選ぶことが測定範囲を選ぶ。散乱 SPR=1 は体積径を (1+SPR)^(-1/3) で -22.6 %(予測 -20.6 %)縮める。等級を 1 段間違える画像はゼロ点 90 % → 体積径 23 %。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/02_map_detections_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_radiograph_porosity/02_map_detections.png)

*↑ 測定の図*

```
py -3.11 examples/poc_weld_radiograph_porosity.py
```

ソース: [examples/poc_weld_radiograph_porosity.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_weld_radiograph_porosity.py)

使用 op(ノートへ): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`blob_select`](https://furuse.work/ops/blob/select/blob_select.html) · [`estimate_noise`](https://furuse.work/ops/2d/features/estimate_noise.html) · [`gauss_image`](https://furuse.work/ops/2d/smoothing/gauss_image.html) · [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`gray_opening_rect`](https://furuse.work/ops/2d/morphology/gray_opening_rect.html) · [`identity`](https://furuse.work/ops/2d/misc/identity.html) · [`log_image`](https://furuse.work/ops/2d/arithmetic/log_image.html) · [`measure_pairs`](https://furuse.work/ops/measure1d/caliper/measure_pairs.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`median_rect`](https://furuse.work/ops/2d/rank/median_rect.html) · [`sk_rolling_ball`](https://furuse.work/ops/2d/smoothing/sk_rolling_ball.html) · [`xsitk_grayscale_grindpeak`](https://furuse.work/ops/2d/extra/xsitk_grayscale_grindpeak.html)

## 12. 太陽電池セルの EL 画像から発電損失を推定する ―― 「暗い = 不活性」ではない

[![太陽電池セルの EL 画像から発電損失を推定する ―― 「暗い = 不活性」ではない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_el_inspection/01_zero_point_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_el_inspection/01_zero_point_map.png)

*↑ **太陽電池セルの EL 画像から発電損失を推定する ―― 「暗い = 不活性」ではない** ―― 結晶シリコンセル(フィンガー 100 本・バスバー 3 本・結晶粒 70 個)の EL 画像を閉形式で合成し、孤立領域(真値 4.77 %)・クラック 5 本・断線 8 本を植えて cos^4 ビネッティングと光子雑音で観測した。ゼロ点の大域しきい値は暗画素率 21.7 % を不活性面積率と呼ぶが、その 42 % はフィンガー/バスバー、33 % は結晶粒とビネッティングで、本物の不活性領域は 20 %。行・列プロファイルで格子を割り、種別ごとの門で取ると面積率 4.61 %(誤差 -0.15 ポイント)、クラック再現率 0.88〜1.00、断線 8/8。sk_frangi は画像ごとの最大値で正規化するので、校正線は画像中でいちばん強くないと尺度を固定できず(実クラックと同じ線は応答 0.69、幅 3 px の強い線は 1.00)、校正なしは欠陥ゼロの良品で偽クラック 147 px を出す。結晶粒コントラスト c=0.24 から偽クラックと帯の飲み込みが同時に始まり、クラック幅の崖 1.25 px は「幅 × 深さ」の線形則(予測 1.38 px)で読める。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_el_inspection/02_by_type_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_el_inspection/02_by_type.png)

*↑ 測定の図*

```
py -3.11 examples/poc_solar_el_inspection.py
```

ソース: [examples/poc_solar_el_inspection.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_solar_el_inspection.py)

使用 op(ノートへ): [`aug_vignette`](https://furuse.work/ops/2d/augmentation/aug_vignette.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_select`](https://furuse.work/ops/blob/select/blob_select.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`gray_closing`](https://furuse.work/ops/2d/morphology/gray_closing.html) · [`hysteresis_threshold`](https://furuse.work/ops/2d/segmentation/hysteresis_threshold.html) · [`lines_gauss`](https://furuse.work/ops/2d/contour/lines_gauss.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`sk_frangi`](https://furuse.work/ops/2d/texture/sk_frangi.html) · [`sk_skeleton`](https://furuse.work/ops/2d/region/sk_skeleton.html) · [`total_length`](https://furuse.work/ops/2d/features/total_length.html) · [`vignette`](https://furuse.work/ops/gfx2d/post/vignette.html)

## 13. はんだフィレットの AOI ―― 3 リング照明は傾きの 3 段量子化器で、高さの 7 割は暗部にある

[![はんだフィレットの AOI ―― 3 リング照明は傾きの 3 段量子化器で、高さの 7 割は暗部にある](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solder_fillet_aoi/02_scene_grid_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solder_fillet_aoi/02_scene_grid.png)

*↑ **はんだフィレットの AOI ―― 3 リング照明は傾きの 3 段量子化器で、高さの 7 割は暗部にある** ―― 1608 チップのパッド・電極と、接触角と断面積で決まる円弧のフィレットを仕込み、仰角の違う 3 リング(赤 30-40°、緑 15-30°、青 0-15°)の応答を GGX で積分して合成した AOI 画像で、良品 / 不足 / ブリッジ / 浮きを判定する。接触角 18° の凹円弧は壁で 72° まで立つので、いちばん低いリングでも見えるのは高さの 28.8 %(予測)―― 色帯の傾きを積分する素朴な推定は真値の 0.284 倍にしかならない。色が変わる位置から円弧を壁まで外挿すると自由円弧で +1.7 % ± 5.3 % に収まるが、はんだ量が増えて爪先がパッド端に固定されると -42.3 % まで外れる。部品の位置ずれ 0.16 mm で爪先の傾きが 30° を超えて緑帯が消え、真値の高さは上がっているのに良品が「不足」になる(予測 0.16 mm、真値が不足になるのは 0.28 mm)。表面粗さは予想と違い暗部の縁を動かさず、粗さ 0.5 で赤帯の消失と同時に壊れて 0.6 で全体が暗部に落ちる。パッド平均色 ΔE のゼロ点は基準条件で 100 % 当たるが、ずれ・粗さ・むらを混ぜると良品 56 % / ブリッジ 68 % を NG にして区別しておらず、円弧推定の判定は良品 98 % / 不足 98 % / ブリッジ 100 % / 浮き 88 %(取りこぼしは持ち上がり角 8.7〜11.0°)。*

[![鏡面なら窓の端が階段になる。傾き 40° を超えるとどのリングも届かない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solder_fillet_aoi/01_ring_lut_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solder_fillet_aoi/01_ring_lut.png)

*↑ 測定の図 ―― 鏡面なら窓の端が階段になる。傾き 40° を超えるとどのリングも届かない。*

```
py -3.11 examples/poc_solder_fillet_aoi.py
```

ソース: [examples/poc_solder_fillet_aoi.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_solder_fillet_aoi.py)

使用 op(ノートへ): [`access_channel`](https://furuse.work/ops/2d/color/access_channel.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_select_largest`](https://furuse.work/ops/blob/select/blob_select_largest.html) · [`brdf_microfacet`](https://furuse.work/ops/specular/reflectance/brdf_microfacet.html) · [`illumination_design`](https://furuse.work/ops/optics/illumination/illumination_design.html) · [`intensity`](https://furuse.work/ops/2d/features/intensity.html) · [`rgb_to_lab`](https://furuse.work/ops/imgmetrics/colorspace/rgb_to_lab.html) · [`trans_from_rgb`](https://furuse.work/ops/2d/color/trans_from_rgb.html)

### 寸法・形状計測ウィング ―― 偏りと散らばりは別々に持つ

「この部品の幅は 50.50 画素だ」と言い切るには、偏り(いつも同じ向きにずれる分)と散らばり(撮るたびに変わる分)を別々に出す必要があります。合否は偏りで決まり、繰り返し精度は散らばりで決まる。1 つの「誤差」にまとめた瞬間、どちらの対策を打つべきかが分からなくなります。

この部屋の 10 点は、符号つき距離関数の部品、インボリュート歯形、指定 PSD の粗さ面、白色干渉のスタック、解析スペックル、Frocht の応力場、対称な合成頭蓋と、いずれも閉形式か解析描画で真値を握った上で、キャリパーや相関や位相の読みを採点しています。

共通して出てきたのは「定義を書かない数字は比較できない」ということです。距離変換の 2 通りの規約で 0.20 mm 違うひび割れ幅、個数基準と面積基準で 1.66 倍違う D50、評価領域を広げると頭打ちにならない Sz、本数基準か長さ基準かで 5 % 動く配向度。測定器の誤差ではなく、比べる相手の問題として現れます。

## 14. 産業部品の寸法検査 ―― 偏りと散らばりを別々に出す

[![産業部品の寸法検査 ―― 偏りと散らばりを別々に出す](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dimensional_inspection/01_slot_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dimensional_inspection/01_slot_bias.png)

*↑ **産業部品の寸法検査 ―― 偏りと散らばりを別々に出す** ―― 符号つき距離関数で描いた部品(スロット幅 50.50 px、1 px = 12.5 µm)を既知の PSF と雑音で撮り、4 系のキャリパーで測った図。大津の整数幅(ゼロ点)は RMS 0.464 px = 5.8 µm、埋もれていた 1-D 計測実装の偏りは -0.0113 px = -0.14 µm で 41 倍。エッジ間距離が PSF 幅の 3.09 倍を切ると幅は系統的に大きく出るのに、API は成功を返し続ける。*

[![偏りはどちらも正(対が互いを押し広げる)。符号が一定なので繰り返し測っても消えない。下端 -4 は表示の打ち切り(|偏り| < 1e-4 px)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dimensional_inspection/02_blur_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dimensional_inspection/02_blur_cliff.png)

*↑ 測定の図 ―― 偏りはどちらも正(対が互いを押し広げる)。符号が一定なので繰り返し測っても消えない。下端 -4 は表示の打ち切り(|偏り| < 1e-4 px)。*

```
py -3.11 examples/poc_dimensional_inspection.py
```

ソース: [examples/poc_dimensional_inspection.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dimensional_inspection.py)

使用 op(ノートへ): [`add_metrology_object_circle_measure`](https://furuse.work/ops/measure1d/model/add_metrology_object_circle_measure.html) · [`add_metrology_object_ellipse_measure`](https://furuse.work/ops/measure1d/model/add_metrology_object_ellipse_measure.html) · [`add_metrology_object_generic`](https://furuse.work/ops/measure1d/model/add_metrology_object_generic.html) · [`add_metrology_object_line_measure`](https://furuse.work/ops/measure1d/model/add_metrology_object_line_measure.html) · [`add_metrology_object_rectangle2_measure`](https://furuse.work/ops/measure1d/model/add_metrology_object_rectangle2_measure.html) · [`align_metrology_model`](https://furuse.work/ops/measure1d/apply/align_metrology_model.html) · [`apply_metrology_model`](https://furuse.work/ops/measure1d/apply/apply_metrology_model.html) · [`create_metrology_model`](https://furuse.work/ops/measure1d/model/create_metrology_model.html) · [`edge_points`](https://furuse.work/ops/3d/edges/edge_points.html) · [`ellipse`](https://furuse.work/ops/annotate/shape/ellipse.html) · [`fuzzy_measure_pairing`](https://furuse.work/ops/measure1d/caliper/fuzzy_measure_pairing.html) · [`gen_measure_arc`](https://furuse.work/ops/measure1d/caliper/gen_measure_arc.html) · [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`m1_measure_pairs`](https://furuse.work/ops/2d/measure1d/m1_measure_pairs.html) · [`m1_measure_pos`](https://furuse.work/ops/2d/measure1d/m1_measure_pos.html) · [`measure_pairs`](https://furuse.work/ops/measure1d/caliper/measure_pairs.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`translate_measure`](https://furuse.work/ops/measure1d/caliper/translate_measure.html)

## 15. 歯車の歯形を測る ―― 偏心は 1 次、歯は z 次

[![歯車の歯形を測る ―― 偏心は 1 次、歯は z 次](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/01_scene.png)

*↑ **歯車の歯形を測る ―― 偏心は 1 次、歯は z 次** ―― インボリュートの閉形式で描いた歯車から偏心と歯形を読む図。ゼロ点の最小二乗円は直径 47.278 mm で、ピッチ円 48 / 歯先円 52 / 歯底円 43 のどれでもない。歯が 1 枚欠けると偏心 0.050 mm が 0.1285 mm(+157 %)に化けるが、歯ごとに 1 標本だけ読む伝統的な測り方なら 0.0501 mm(+0.2 %)。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/02_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/02_profile.png)

*↑ 測定の図*

```
py -3.11 examples/poc_gear_tooth_metrology.py
```

ソース: [examples/poc_gear_tooth_metrology.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_gear_tooth_metrology.py)

使用 op(ノートへ): [`blob_boundaries`](https://furuse.work/ops/blob/extract/blob_boundaries.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`blob_region`](https://furuse.work/ops/blob/extract/blob_region.html) · [`blob_select_largest`](https://furuse.work/ops/blob/select/blob_select_largest.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`polar_trans_image`](https://furuse.work/ops/2d/geometry/polar_trans_image.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html)

## 16. 表面粗さ Sa / Sq / Sz は標本化とカットオフにどこまで耐えるか

[![表面粗さ Sa / Sq / Sz は標本化とカットオフにどこまで耐えるか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_surface_roughness/01_surface_components_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_surface_roughness/01_surface_components.png)

*↑ **表面粗さ Sa / Sq / Sz は標本化とカットオフにどこまで耐えるか** ―― 指定 PSD から合成した表面(Sq の真値は Parseval で解析的)に傾き・うねり・加工目・傷を足し、粗さパラメータを測った図。生の rms を Sq と呼ぶと 20 倍の過大、平面だけ除いても 1.8 倍。標本間隔 8 µm で Sa は -3.5 %(合格)、Sz は -19.8 %(不合格) ―― Sz は評価領域を広げると頭打ちにならず、「真の Sz」は存在しない。*

[![dx=8 µm では Sa が ±5 % 合格で Sz が不合格。同じデータでも見るパラメータで結論が反転する。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_surface_roughness/02_sampling_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_surface_roughness/02_sampling_cliff.png)

*↑ 測定の図 ―― dx=8 µm では Sa が ±5 % 合格で Sz が不合格。同じデータでも見るパラメータで結論が反転する。*

```
py -3.11 examples/poc_surface_roughness.py
```

ソース: [examples/poc_surface_roughness.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_surface_roughness.py)

使用 op(ノートへ): [`profile_params`](https://furuse.work/ops/roughness/measure/profile_params.html) · [`surface_filter`](https://furuse.work/ops/roughness/prepare/surface_filter.html) · [`surface_form_remove`](https://furuse.work/ops/roughness/prepare/surface_form_remove.html) · [`surface_params`](https://furuse.work/ops/roughness/measure/surface_params.html) · [`surface_psd`](https://furuse.work/ops/roughness/measure/surface_psd.html) · [`surface_synth_psd`](https://furuse.work/ops/roughness/synth/surface_synth_psd.html)

## 17. 白色干渉計でナノメートルの段差をどこまで正確に測れるか

[![白色干渉計でナノメートルの段差をどこまで正確に測れるか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/01_interferogram_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/01_interferogram.png)

*↑ **白色干渉計でナノメートルの段差をどこまで正確に測れるか** ―― 白色干渉計の走査スタックを合成し、50〜500 nm の段差を測り返した図。雑音 1 % で偏り 2.4 nm 以内・標準偏差 14.1 nm 以内、しかも段差の大きさにほぼ依らない。ゼロ点(包絡線の最大サンプル)の誤差は走査ステップの半分に厳密一致し、Nyquist 上限 0.15 µm の手前 0.14 µm では雑音なしでも +14.1 nm。*

[![0.02〜0.12 µm は 0.05 nm 以内で平ら。Nyquist 上限 0.15 µm の手前 0.14 µm で崖。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/02_zstep_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/02_zstep_sweep.png)

*↑ 測定の図 ―― 0.02〜0.12 µm は 0.05 nm 以内で平ら。Nyquist 上限 0.15 µm の手前 0.14 µm で崖。*

```
py -3.11 examples/poc_interferometry_step.py
```

ソース: [examples/poc_interferometry_step.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_interferometry_step.py)

使用 op(ノートへ): [`csi_design`](https://furuse.work/ops/interferometry/design/csi_design.html) · [`csi_height_map`](https://furuse.work/ops/interferometry/surface/csi_height_map.html) · [`csi_stack_simulate`](https://furuse.work/ops/interferometry/simulate/csi_stack_simulate.html) · [`decode_fringe`](https://furuse.work/ops/3d/structured_light/decode_fringe.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`synthesize_fringes`](https://furuse.work/ops/3d/structured_light/synthesize_fringes.html)

## 18. スペックル画像からひずみを測る(DIC)

[![スペックル画像からひずみを測る(DIC)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dic_strain/04_strain_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dic_strain/04_strain_map.png)

*↑ **スペックル画像からひずみを測る(DIC)** ―― 3000 個のガウス斑点を変形写像で移してから描き直したスペックル対から変位とひずみを読む図。真の変位 0.37 px に対し窓相関(piv)の偏り 0.0002 px・散らばり 0.0022 px で、ゼロ点(動かないと答える)の 167 倍。剛体回転が微小ひずみの定義で数百 µε の嘘を作る ―― Green-Lagrange なら厳密に 0。*

[![変形は補間ではなく斑点の再描画。だから真値が厳密。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dic_strain/01_speckle_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dic_strain/01_speckle.png)

*↑ 測定の図 ―― 変形は補間ではなく斑点の再描画。だから真値が厳密。*

```
py -3.11 examples/poc_dic_strain.py
```

ソース: [examples/poc_dic_strain.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dic_strain.py)

使用 op(ノートへ): [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`strain_from_displacement`](https://furuse.work/ops/piv/solid/strain_from_displacement.html)

## 19. クリープ試験のひずみ履歴 ―― 累積か直接か

[![クリープ試験のひずみ履歴 ―― 累積か直接か](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/01_speckle_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/01_speckle.png)

*↑ **クリープ試験のひずみ履歴 ―― 累積か直接か** ―― 1 時間のクリープを 25 コマ撮り、隣接コマの累積と基準フレームとの直接比較でひずみ履歴を出した図。終端で累積 61 µε / 直接 1878 µε と累積が 31 倍良く、教科書の「時刻で入れ替わる」交点は無い(入れ替わるのは雑音の軸)。コマを 24 → 4 歩に間引くと累積は -60 → -606 µε と悪化 ―― 効くのは歩数でなく 1 歩あたりの変形量。*

[![直接の偏りだけが伸びる。累積は偏りも散らばりも頭打ちで、しかも散らばりより偏りのほうが大きい ——ランダムウォークではない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/02_errors_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/02_errors.png)

*↑ 測定の図 ―― 直接の偏りだけが伸びる。累積は偏りも散らばりも頭打ちで、しかも散らばりより偏りのほうが大きい ——ランダムウォークではない。*

```
py -3.11 examples/poc_strain_history.py
```

ソース: [examples/poc_strain_history.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_strain_history.py)

使用 op(ノートへ): [`moving_average_window`](https://furuse.work/ops/videostream/window/moving_average_window.html) · [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`piv_error_stats`](https://furuse.work/ops/piv/assess/piv_error_stats.html) · [`piv_multipass`](https://furuse.work/ops/piv/estimate/piv_multipass.html) · [`piv_sample_at_windows`](https://furuse.work/ops/piv/assess/piv_sample_at_windows.html) · [`piv_synth_pair`](https://furuse.work/ops/piv/synth/piv_synth_pair.html) · [`poly_fit`](https://furuse.work/ops/math/interp_poly/poly_fit.html)

## 20. 光弾性で応力を測る ―― 巻き戻しが最初に失敗するのは等方点

[![光弾性で応力を測る ―― 巻き戻しが最初に失敗するのは等方点](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_photoelasticity/01_polariscope_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_photoelasticity/01_polariscope.png)

*↑ **光弾性で応力を測る ―― 巻き戻しが最初に失敗するのは等方点** ―― 円板圧縮の閉形式応力場(中心 4.2441 MPa、縞次数 2.380)を Mueller 行列の op で偏光像にし、縞から応力へ戻す図。op の偏光系は教科書式と 125 通りで最大差 2.2e-16。縞次数が 0.5 を超える 84.2 % の画素で位相が巻き、巻き戻しが最初に壊れるのは応力の大きい所ではなく、変調が落ちる等方点。*

[![左下 2 枚が「壊れる予報」。どちらもマスクで外せる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_photoelasticity/02_unwrap_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_photoelasticity/02_unwrap.png)

*↑ 測定の図 ―― 左下 2 枚が「壊れる予報」。どちらもマスクで外せる。*

```
py -3.11 examples/poc_photoelasticity.py
```

ソース: [examples/poc_photoelasticity.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_photoelasticity.py)

使用 op(ノートへ): [`mueller_apply`](https://furuse.work/ops/optics/polarization/mueller_apply.html) · [`mueller_element`](https://furuse.work/ops/optics/polarization/mueller_element.html) · [`unwrap_phase_2d`](https://furuse.work/ops/3d/structured_light/unwrap_phase_2d.html)

## 21. 左右非対称性を測る ―― 対称面は変形に引きずられる

[![左右非対称性を測る ―― 対称面は変形に引きずられる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bilateral_asymmetry/03_deviation_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bilateral_asymmetry/03_deviation_map.png)

*↑ **左右非対称性を測る ―― 対称面は変形に引きずられる** ―― 厳密に左右対称な合成頭蓋の片側に既知の膨らみを入れ、鏡映して重ねた図。完全対称な標本でも床は 0 にならず、点対点 1.33 mm → 点対面 0.030 mm → 近傍平滑 0.012 mm。残差を最小にする面は 6.33 mm の膨らみで 2.92 mm / 1.72 度引きずられ、非対称量の 46 % が消える。*

[![完全対称な標本を測った残差。点対点は点間隔がそのまま床になる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bilateral_asymmetry/01_floor_vs_spacing_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bilateral_asymmetry/01_floor_vs_spacing.png)

*↑ 測定の図 ―― 完全対称な標本を測った残差。点対点は点間隔がそのまま床になる。*

```
py -3.11 examples/poc_bilateral_asymmetry.py
```

ソース: [examples/poc_bilateral_asymmetry.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bilateral_asymmetry.py)

使用 op(ノートへ): [`chamfer_distance`](https://furuse.work/ops/3d/metrics/chamfer_distance.html) · [`detect_reflection_symmetry`](https://furuse.work/ops/3d/symmetry/detect_reflection_symmetry.html) · [`detect_rotational_symmetry`](https://furuse.work/ops/3d/symmetry/detect_rotational_symmetry.html) · [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`hausdorff_distance`](https://furuse.work/ops/3d/metrics/hausdorff_distance.html) · [`reflect_points`](https://furuse.work/ops/3d/symmetry/reflect_points.html) · [`reflection_symmetry_score`](https://furuse.work/ops/3d/symmetry/reflection_symmetry_score.html) · [`sample_surface`](https://furuse.work/ops/3d/superquadric/sample_surface.html) · [`vertex_normals`](https://furuse.work/ops/3d/mesh_process/vertex_normals.html)

## 22. 粒度分布を画像から測る ―― 融合と縁切れが逆向きに効き、途中で打ち消し合う

[![粒度分布を画像から測る ―― 融合と縁切れが逆向きに効き、途中で打ち消し合う](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/01_scene.png)

*↑ **粒度分布を画像から測る ―― 融合と縁切れが逆向きに効き、途中で打ち消し合う** ―― 粒子を撒いた合成画像から D10 / D50 / D90 を出し、融合(大きい側へ)と縁切れ(小さい側へ)を別々に数えた図。面積率 13.8 % で D50 誤差 +0.55 % ―― 融合 28 件と縁切れ 19 件が釣り合っているだけ。個数基準と面積基準では同じ塊から D50 が 26.9 µm と 44.7 µm(1.66 倍)。*

[![薄いところで 0 なのは正確だから。濃いところで 0 をまたぐのは融合と縁切れが釣り合っただけ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/02_density_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/02_density_sweep.png)

*↑ 測定の図 ―― 薄いところで 0 なのは正確だから。濃いところで 0 をまたぐのは融合と縁切れが釣り合っただけ。*

```
py -3.11 examples/poc_particle_sizing.py
```

ソース: [examples/poc_particle_sizing.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_particle_sizing.py)

使用 op(ノートへ): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`blob_region`](https://furuse.work/ops/blob/extract/blob_region.html) · [`blob_select`](https://furuse.work/ops/blob/select/blob_select.html) · [`circularity`](https://furuse.work/ops/2d/features/circularity.html) · [`distance_transform`](https://furuse.work/ops/2d/region/distance_transform.html)

## 23. 繊維の配向分布を測る ―― 角度は 180 度周期、素朴に平均すると 90 度ずれる

[![繊維の配向分布を測る ―― 角度は 180 度周期、素朴に平均すると 90 度ずれる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/01_scene.png)

*↑ **繊維の配向分布を測る ―― 角度は 180 度周期、素朴に平均すると 90 度ずれる** ―― フォン・ミーゼス分布から撒いた繊維 140 本の配向を構造テンソルで読む図。真の平均 177.9 度を算術平均は 105.55 度と報告し(-72.33 度)、2 倍角の円形平均なら +0.17 度 ―― 画像も測定も 1 ビットも変えていない。全画素を等しく数えると配向度が -31.3 % 落ちる。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/02_wrap_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/02_wrap.png)

*↑ 測定の図*

```
py -3.11 examples/poc_fiber_orientation.py
```

ソース: [examples/poc_fiber_orientation.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_fiber_orientation.py)

使用 op(ノートへ): [`coherence`](https://furuse.work/ops/acoustics/dual/coherence.html) · [`dc_structure_texture`](https://furuse.work/ops/2d/decomposition/dc_structure_texture.html) · [`moment_axes`](https://furuse.work/ops/3d/match_pose/moment_axes.html) · [`principal_moments`](https://furuse.work/ops/3d/moment_invariant/principal_moments.html) · [`sobel_amp`](https://furuse.work/ops/2d/edges/sobel_amp.html) · [`sobel_dir`](https://furuse.work/ops/2d/edges/sobel_dir.html)

## 24. 金属組織の結晶粒度 ―― 面積法と切片法は別の崖で落ちる

[![金属組織の結晶粒度 ―― 面積法と切片法は別の崖で落ちる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/01_scene.png)

*↑ **金属組織の結晶粒度 ―― 面積法と切片法は別の崖で落ちる** ―― 2-D Voronoi で粒を仕込み、粒界を幅 2 px で描いてエッチングむら・雑音・途切れを乗せ、ASTM E112 の面積法(大津 + 連結成分)と直線切断法(局所しきい値 + 4 方向の試験線)で G を測った図。面積法は雑音だけ -0.02・むらだけ -0.40 が両方で +3.82 と相互作用で死に、粒界の途切れでは 7.2 % で 1 段落ちる。切片法は 40.7 % まで持つが、予想の 29.3 % は外れ(マスク上で消える粒界は f の 0.76 倍)。混粒の全体 G 7.82 は細粒 9.01 にも粗粒 6.15 にも無く、64 タイル中 4 つしか ±0.5 に入らない。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/02_controls_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/02_controls.png)

*↑ 測定の図*

```
py -3.11 examples/poc_metal_grain_size.py
```

ソース: [examples/poc_metal_grain_size.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_metal_grain_size.py)

使用 op(ノートへ): [`bin_threshold`](https://furuse.work/ops/2d/segmentation/bin_threshold.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`bothat`](https://furuse.work/ops/2d/morphology/bothat.html) · [`dyn_threshold`](https://furuse.work/ops/2d/segmentation/dyn_threshold.html) · [`gray_bothat`](https://furuse.work/ops/2d/morphology/gray_bothat.html) · [`hx_close_edges`](https://furuse.work/ops/2d/halcon_ext/hx_close_edges.html) · [`invert_image`](https://furuse.work/ops/2d/gray/invert_image.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html)

## 25. ねじの輪郭からピッチ・フランク角・有効径 ―― 傾きは左右のフランクに逆符号で出る

[![ねじの輪郭からピッチ・フランク角・有効径 ―― 傾きは左右のフランクに逆符号で出る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/07_sampling_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/07_sampling_frames.png)

*↑ **ねじの輪郭からピッチ・フランク角・有効径 ―― 傾きは左右のフランクに逆符号で出る** ―― ISO 68-1 の基本三角形を閉形式で描いた M6 相当の投影像(1 px = 25 µm)。二値化した列幅の FFT はピッチを真値の半分 20 px と答える(上下輪郭が P/2 ずれた三角波の和は定数)。軸を 3 度傾けると左右フランク角は 33.18 / 26.74 度に割れ、半和 29.81 度が真のフランク角、半差 3.19 度が傾きの推定になる。片側フランクで測るピッチは 1 次で狂う(+3.28 / -2.79 %)が頂点間隔は 2 次(-0.12 %)。傾きを戻せば P -0.009 %、d2 +0.033 %。*

[![幅の系列は上下輪郭(P/2 ずれ)の和なので基本波が消える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/01_zero_spectrum_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/01_zero_spectrum.png)

*↑ 測定の図 ―― 幅の系列は上下輪郭(P/2 ずれ)の和なので基本波が消える。*

```
py -3.11 examples/poc_screw_thread_metrology.py
```

ソース: [examples/poc_screw_thread_metrology.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_screw_thread_metrology.py)

使用 op(ノートへ): [`fit_line_contours`](https://furuse.work/ops/2d/contour/fit_line_contours.html) · [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`hx_split_contours`](https://furuse.work/ops/2d/halcon_ext/hx_split_contours.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html) · [`threshold_sub_pix`](https://furuse.work/ops/2d/contour/threshold_sub_pix.html) · [`xg_regress_contours`](https://furuse.work/ops/2d/xldgeom/xg_regress_contours.html)

### 医用・生物ウィング ―― 個数が合っていて中身が外れている

細胞を数える、核の DNA 量を読む、血管の分岐を測る、創傷の面積を追う。どれも「1 つの数字」で報告されがちで、しかもその数字が合ってしまう場面があります。過分割と過統合が釣り合って個数の偏りが +0.3 個になる細胞計数、背景を引き忘れても分類が生き残る倍数性、いちばん安定して、いちばん間違った治癒定数を返す較正。

この部屋の 4 点は、真値に「どれとどれが重なっているか」「面積と DNA 量が別々にばらつく」「分岐則を厳密に満たす木」といった、ラベル画像だけでは残らない情報を持たせています。実データに差し替えるときも、ラベル画像だけを真値と呼ぶと主題そのものが消える、と各 docstring に書いてあります。

見どころは、性能が上がったように見えて測っている量が入れ替わっている場面です。ぼかすほど面積分類器が良くなるのは、面積という名前で DNA 量を漏らしているから。1 つの指標が良くなった理由を毎回追わないと、こういう嘘を成果として持ち帰ることになります。

## 26. 重なった細胞をどう数えるか ―― 個数・過分割・過統合を別々に測る

[![重なった細胞をどう数えるか ―― 個数・過分割・過統合を別々に測る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cell_counting/01_scene_dense_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cell_counting/01_scene_dense.png)

*↑ **重なった細胞をどう数えるか ―― 個数・過分割・過統合を別々に測る** ―― 重なった細胞の合成画像で、個数・過分割・過統合を別々に数えた図。いちばん密な条件でゼロ点は 78 個中 25 個を取りこぼし、失点は全部過統合。種の間引きを振ると釣り合う点があり、個数の偏り +0.3 個なのに分割誤りは 13.3 件残る ―― 個数だけ報告すれば最良の設定として通る。*

[![誤り合計の谷と |偏り| の谷は同じ場所に来ない。どちらを最適と呼ぶかで答えが変わる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cell_counting/02_h_tradeoff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cell_counting/02_h_tradeoff.png)

*↑ 測定の図 ―― 誤り合計の谷と |偏り| の谷は同じ場所に来ない。どちらを最適と呼ぶかで答えが変わる。*

```
py -3.11 examples/poc_cell_counting.py
```

ソース: [examples/poc_cell_counting.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_cell_counting.py)

使用 op(ノートへ): [`circularity`](https://furuse.work/ops/2d/features/circularity.html) · [`distance_transform`](https://furuse.work/ops/2d/region/distance_transform.html) · [`fill_holes`](https://furuse.work/ops/2d/region/fill_holes.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`sk_otsu`](https://furuse.work/ops/2d/segmentation/sk_otsu.html) · [`vol_distance_transform`](https://furuse.work/ops/3d/medial/vol_distance_transform.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_local_maxima`](https://furuse.work/ops/3d/feature/vol_local_maxima.html) · [`vol_watershed`](https://furuse.work/ops/3d/segment/vol_watershed.html) · [`xsk2_h_maxima`](https://furuse.work/ops/2d/segmentation/xsk2_h_maxima.html)

## 27. 蛍光核の積分輝度から倍数性を出す ―― 面積では分かれない

[![蛍光核の積分輝度から倍数性を出す ―― 面積では分かれない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_nuclei_ploidy/04_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_nuclei_ploidy/04_scene.png)

*↑ **蛍光核の積分輝度から倍数性を出す ―― 面積では分かれない** ―― DNA 量 D と面積 A を別々のばらつきで撒いた蛍光核で、倍数性を面積と積分輝度から分けた図。真の面積でも誤分類 15.4 %、積分輝度は 0 %。背景を引き忘れると分類は生き残ったまま DNA 指数だけが 2.115 → 1.702(-20 %)壊れる ―― 分類だけを見ていたら気づけない。*

[![累積分布。積分輝度の 4n は 2.1 付近に固まり、面積の 2 本は大きく重なる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_nuclei_ploidy/01_histograms_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_nuclei_ploidy/01_histograms.png)

*↑ 測定の図 ―― 累積分布。積分輝度の 4n は 2.1 付近に固まり、面積の 2 本は大きく重なる。*

```
py -3.11 examples/poc_nuclei_ploidy.py
```

ソース: [examples/poc_nuclei_ploidy.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_nuclei_ploidy.py)

使用 op(ノートへ): [`aperture_photometry`](https://furuse.work/ops/astrostack/photometry/aperture_photometry.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`sg_gmm_segment`](https://furuse.work/ops/2d/segment/sg_gmm_segment.html) · [`sk_otsu`](https://furuse.work/ops/2d/segmentation/sk_otsu.html)

## 28. 血管網を抜いて分岐を測る ―― ヒゲ、分岐近傍の径の過大、そして指数の脆さ

[![血管網を抜いて分岐を測る ―― ヒゲ、分岐近傍の径の過大、そして指数の脆さ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vessel_network/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vessel_network/01_scene.png)

*↑ **血管網を抜いて分岐を測る ―― ヒゲ、分岐近傍の径の過大、そして指数の脆さ** ―― Murray の法則に厳密に従う合成血管木を細線化し、分岐点・径・指数を測った図。分岐画素をそのまま数えると 25 個の分岐に 47 画素、連結成分にまとめれば 25 個ちょうど。ヒゲを作るのは細線化ではなく境界のざらつきで(余分な分岐 0 → 72 個)、径は分岐から 3 px 未満で +26.2 % 過大。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vessel_network/02_prune_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vessel_network/02_prune.png)

*↑ 測定の図*

```
py -3.11 examples/poc_vessel_network.py
```

ソース: [examples/poc_vessel_network.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_vessel_network.py)

使用 op(ノートへ): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`distance_transform`](https://furuse.work/ops/2d/region/distance_transform.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`medial_axis_points`](https://furuse.work/ops/3d/medial/medial_axis_points.html) · [`r2_split_skeleton_lines`](https://furuse.work/ops/2d/region/r2_split_skeleton_lines.html) · [`sk_medial`](https://furuse.work/ops/2d/region/sk_medial.html) · [`skeleton`](https://furuse.work/ops/2d/region/skeleton.html) · [`skeleton_branches3d`](https://furuse.work/ops/3d/medial/skeleton_branches3d.html) · [`skeleton_endpoints3d`](https://furuse.work/ops/3d/medial/skeleton_endpoints3d.html) · [`skeleton_junctions3d`](https://furuse.work/ops/3d/medial/skeleton_junctions3d.html) · [`skeleton_prune3d`](https://furuse.work/ops/3d/medial/skeleton_prune3d.html) · [`skeletonize_vol`](https://furuse.work/ops/3d/medial/skeletonize_vol.html) · [`thinning`](https://furuse.work/ops/2d/region/thinning.html) · [`vol_distance_transform`](https://furuse.work/ops/3d/medial/vol_distance_transform.html)

## 29. 創傷面積の経時変化 ―― 較正の誤差は面積に 2 乗で効く

[![創傷面積の経時変化 ―― 較正の誤差は面積に 2 乗で効く](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_wound_area_tracking/02_scenes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_wound_area_tracking/02_scenes.png)

*↑ **創傷面積の経時変化 ―― 較正の誤差は面積に 2 乗で効く** ―― mm 平面に置いた星形の創面(面積は閉形式)をピンホールカメラで日ごとに撮り、治癒定数 k を推定した図。距離が 4 % 違うだけで面積が 7.7 % 動き、日ごとに 1.2 % 漂うと真の k = 0.1200 に対しゼロ点は 0.1424(+18.7 %)。しかもその標準偏差 0.0049 は毎回較正の 0.0059 より小さい ―― いちばん安定して、いちばん間違った答え。*

[![ゼロ点の面積誤差。実測は閉形式の 2 乗則に乗り、線形近似からは外れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_wound_area_tracking/01_dist_square_law_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_wound_area_tracking/01_dist_square_law.png)

*↑ 測定の図 ―― ゼロ点の面積誤差。実測は閉形式の 2 乗則に乗り、線形近似からは外れる。*

```
py -3.11 examples/poc_wound_area_tracking.py
```

ソース: [examples/poc_wound_area_tracking.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_wound_area_tracking.py)

使用 op(ノートへ): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_select_largest`](https://furuse.work/ops/blob/select/blob_select_largest.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`warp_by_plane`](https://furuse.work/ops/3d/plane_sweep_stereo/warp_by_plane.html)

## 30. 蛍光の共局在は漏れ込みで嘘をつく ―― Pearson と Manders は別の場所で壊れる

[![蛍光の共局在は漏れ込みで嘘をつく ―― Pearson と Manders は別の場所で壊れる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/01_scene_channels_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/01_scene_channels.png)

*↑ **蛍光の共局在は漏れ込みで嘘をつく ―― Pearson と Manders は別の場所で壊れる** ―― 細胞体に小胞状の点を 2 色ぶん撒き、B の点の 0 / 25 / 50 / 100 % を A と同位置に置いて真の共局在率を握る。漏れ込み行列 [[1, α], [β, 1]] と細胞質・PSF・光子雑音を掛けた観測に Pearson r と Otsu-Manders を当てると、無関係な 2 色が α=β=10 % で r=0.203、M1=0.133 になる。単染色対照から α を 0.0996(真値 0.10)と推定して線形分離すれば r は 0.007 に戻るが、Manders は 100 % でも 0.705(Otsu より下の裾が落ちる、閉形式の予想 0.756)。Pearson が 0.5 を超える崖は対称漏れ込み α=0.282(予想 2−√3=0.268)、ぼけの崖は Manders だけに来て σ=2.5 px で Otsu の前景が細胞体へ飛び移る。Costes のシャッフル検定は漏れ込みだけの r を p=0.000 で「有意」と言う。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/02_scene_unmixed_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/02_scene_unmixed.png)

*↑ 測定の図*

```
py -3.11 examples/poc_colocalization_crosstalk.py
```

ソース: [examples/poc_colocalization_crosstalk.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_colocalization_crosstalk.py)

使用 op(ノートへ): [`gauss_image`](https://furuse.work/ops/2d/smoothing/gauss_image.html) · [`mat_lstsq`](https://furuse.work/ops/math/linalg/mat_lstsq.html) · [`mat_solve`](https://furuse.work/ops/math/linalg/mat_solve.html) · [`noise_sigma`](https://furuse.work/ops/astrostack/quality/noise_sigma.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`photon_sample`](https://furuse.work/ops/photon/counting/photon_sample.html) · [`reg_erode`](https://furuse.work/ops/2d/region/reg_erode.html) · [`stat_correlation`](https://furuse.work/ops/math/stats/stat_correlation.html)

## 31. MRI のバイアス場と組織面積 ―― 灰白質と白質は逆向きに壊れ、足すと隠れる

[![MRI のバイアス場と組織面積 ―― 灰白質と白質は逆向きに壊れ、足すと隠れる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/02_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/02_scene.png)

*↑ **MRI のバイアス場と組織面積 ―― 灰白質と白質は逆向きに壊れ、足すと隠れる** ―― 楕円殻の脳スライス風ファントム(頭蓋/CSF/皺つき皮質/WM、面積は幾何で既知)に表面コイル型の乗算場と Rician 雑音を掛け、大域 3 クラス大津(xsk2_multiotsu)で 3 組織の面積を測った図。振幅 30 % で GM +20.2 % / WM -7.7 % なのに GM+WM は +0.0 % で誤差が隠れ、雑音を止めると符号が反転する(GM -11.8 %)。崖の幾何予測 30 % に対し実測は 17.5 %。log I をそのまま平滑する素朴な補正は場が無くても GM +81.8 % 壊し、分割の残差を平滑する Wells 型反復にすると 40 % でも +1.8 %。場を 4 px まで細かくすると全補正器が壊れ、SNR 15 では場なしでも GM +8.5 %(WM が GM の 2.6 倍あるので小さい組織に出る)。*

[![雑音だけでは壊れず、場だけで GM と WM が逆向きに動く。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/01_controls_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/01_controls.png)

*↑ 測定の図 ―― 雑音だけでは壊れず、場だけで GM と WM が逆向きに動く。*

```
py -3.11 examples/poc_mri_bias_field.py
```

ソース: [examples/poc_mri_bias_field.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_mri_bias_field.py)

使用 op(ノートへ): [`dc_homomorphic`](https://furuse.work/ops/2d/decomposition/dc_homomorphic.html) · [`eval_bspline_surface`](https://furuse.work/ops/3d/freeform/eval_bspline_surface.html) · [`eval_poly_surface`](https://furuse.work/ops/3d/surface_fit/eval_poly_surface.html) · [`fit_bspline_surface`](https://furuse.work/ops/3d/freeform/fit_bspline_surface.html) · [`fit_poly_surface`](https://furuse.work/ops/3d/surface_fit/fit_poly_surface.html) · [`overlay_labels`](https://furuse.work/ops/annotate/overlay/overlay_labels.html) · [`xsk2_multiotsu`](https://furuse.work/ops/2d/segmentation/xsk2_multiotsu.html)

## 32. 骨梁の厚さ・間隔・骨体積率 ―― 平板モデルと直接法は同じ画像で別の値になる

[![骨梁の厚さ・間隔・骨体積率 ―― 平板モデルと直接法は同じ画像で別の値になる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bone_trabecular_thickness/01_scene_truth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bone_trabecular_thickness/01_scene_truth.png)

*↑ **骨梁の厚さ・間隔・骨体積率 ―― 平板モデルと直接法は同じ画像で別の値になる** ―― 線分の集合として閉形式で描いた 2-D 骨梁網(幅の中央値 120 µm)を、部分体積ぼけ・CT 雑音・カップ状バイアスで観測した。真値そのものが複数あり、幅の長さ加重平均 104.8 µm に対し最大内接円の定義では 121.6 µm、平板モデルは 118.4 µm ―― どの真値と比べるかで 9〜16 % が先に動く。解像度の崖は平均でなく分布に来る(画素 60 µm で分布の重なり 0.83 → 0.09、平均は量子化 -29.5 % と大津の太り +27.1 % が打ち消す)。雑音は斑点(σ 0.10 から)と途切れ(σ 0.15 から)の 2 方向から壊し、面積オープニングは斑点だけを消す。*

[![Tb.Th の平均は 2 px/骨梁でも持つが、BV/TV と分布は壊れている。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bone_trabecular_thickness/02_resolution_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bone_trabecular_thickness/02_resolution_sweep.png)

*↑ 測定の図 ―― Tb.Th の平均は 2 px/骨梁でも持つが、BV/TV と分布は壊れている。*

```
py -3.11 examples/poc_bone_trabecular_thickness.py
```

ソース: [examples/poc_bone_trabecular_thickness.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bone_trabecular_thickness.py)

使用 op(ノートへ): [`blob_distance`](https://furuse.work/ops/blob/split/blob_distance.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`dc_retinex`](https://furuse.work/ops/2d/decomposition/dc_retinex.html) · [`dist_transform`](https://furuse.work/ops/2d/region/dist_transform.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`get_region_thickness`](https://furuse.work/ops/2d/features/get_region_thickness.html) · [`opening_circle`](https://furuse.work/ops/2d/region/opening_circle.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`sk_area_opening`](https://furuse.work/ops/2d/morphology/sk_area_opening.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html)

### 天文・環境ウィング ―― 位置で偏り、真値の定義で反転する

星の明るさと位置、太陽の縁、全天の雲量、海氷の密接度、畑の被覆率、地形、河川の水位。対象は遠く、真値は普通手に入りません。この部屋の 8 点はそれを逆手に取り、天球座標・球冠の立体角・Eddington の周辺減光・国土地理院の標高タイルといった閉形式や公開データから真値を置いています。

共通して出てきたのは「同じ物が、どこにあるかで違って読める」ことです。同じ雲が天頂と地平線で 1.45 倍、同じ厚さの雲が太陽からの角距離で検出されたりされなかったり、同じ反射が検出器によって「静かに低く読む」か「黙って止まる」か。

もう 1 つは、真値の定義が結論を決めること。薄氷を「氷」に入れるか入れないかで同じ推定が -4.4 と +2.7 ポイントに外れ、マスクの角度を書かない雲量は 0.18 から 0.23 まで名乗れます。測定器より先に、何を真値と呼ぶかを書く必要があります。

## 33. 何枚重ねると、星の明るさは何 % の精度で測れるか

[![何枚重ねると、星の明るさは何 % の精度で測れるか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_astro_photometry/01_stack_scaling_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_astro_photometry/01_stack_scaling.png)

*↑ **何枚重ねると、星の明るさは何 % の精度で測れるか** ―― 指定どおりに置いた星野を N 枚重ね、開口測光の誤差が 1/√N で落ちるかを見た図。N = 1 → 16 で中央誤差 0.6350 % → 0.1616 %、8 通りすべてで理論から 4.6 % 以内。宇宙線 1 発で単純平均は +5.89 %、κ-σ なら +0.30 % ―― 棄却率は動かないので「棄却率が上がったから効いた」とは言えない。*

[![単純平均だけが 5.9 % 残る。κ-σ は汚染なしと区別できないところまで戻すが、棄却率はほとんど動かない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_astro_photometry/02_cosmic_ray_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_astro_photometry/02_cosmic_ray.png)

*↑ 測定の図 ―― 単純平均だけが 5.9 % 残る。κ-σ は汚染なしと区別できないところまで戻すが、棄却率はほとんど動かない。*

```
py -3.11 examples/poc_astro_photometry.py
```

ソース: [examples/poc_astro_photometry.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_astro_photometry.py)

使用 op(ノートへ): [`aperture_photometry`](https://furuse.work/ops/astrostack/photometry/aperture_photometry.html) · [`drizzle_resample`](https://furuse.work/ops/astrostack/stack/drizzle_resample.html) · [`lucky_select`](https://furuse.work/ops/astrostack/quality/lucky_select.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`sigma_clip_stack`](https://furuse.work/ops/astrostack/stack/sigma_clip_stack.html) · [`synth_frame_series`](https://furuse.work/ops/astrostack/synth/synth_frame_series.html) · [`synth_starfield`](https://furuse.work/ops/astrostack/synth/synth_starfield.html)

## 34. 星の位置は何分の 1 画素まで測れて、どこで崖に落ちるか

[![星の位置は何分の 1 画素まで測れて、どこで崖に落ちるか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_star_astrometry/03_starfield_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_star_astrometry/03_starfield.png)

*↑ **星の位置は何分の 1 画素まで測れて、どこで崖に落ちるか** ―― 既知の天球座標から描いた星の位置を 4 手法で測り、Fisher 情報の理論限界と比べた図。S/N 298 で重心(ゼロ点)は理論の 5.56 倍、背景引き重心は 1.03 倍で、限界を上回った手法は無い。暗い端でゼロ点が限界を下回って見える(0.2790 px 対 0.3471 px)のは、感度 0.038 で初期値の四捨五入を返しているだけ。*

[![暗い端で素の重心が下限を割って見えるのは「動かない推定器」だから(感度 0.038)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_star_astrometry/01_snr_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_star_astrometry/01_snr_sweep.png)

*↑ 測定の図 ―― 暗い端で素の重心が下限を割って見えるのは「動かない推定器」だから(感度 0.038)。*

```
py -3.11 examples/poc_star_astrometry.py
```

ソース: [examples/poc_star_astrometry.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_star_astrometry.py)

使用 op(ノートへ): [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`noise_sigma`](https://furuse.work/ops/astrostack/quality/noise_sigma.html) · [`psf_fit`](https://furuse.work/ops/astrostack/photometry/psf_fit.html) · [`star_detect`](https://furuse.work/ops/astrostack/photometry/star_detect.html)

## 35. 縁が暗い天体の輪郭はどこか ―― 周辺減光があると「50 % 法」は半径を小さく見る

[![縁が暗い天体の輪郭はどこか ―― 周辺減光があると「50 % 法」は半径を小さく見る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_limb_darkening/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_limb_darkening/01_scene.png)

*↑ **縁が暗い天体の輪郭はどこか ―― 周辺減光があると「50 % 法」は半径を小さく見る** ―― 周辺減光つきの太陽面をシーイング越しに撮り、縁の半径を 50 % 法・勾配最大・モデル当てはめで測った図。「偏りは減光係数に比例」の予想は外れ、u = 0.8 で -12.76 px(幾何だけの予測 -13.14 px)。しきい値 0.26 付近でぼけの影響が消える打ち消し点は、u を変えると 0.38 へ動く。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_limb_darkening/02_bias_vs_u_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_limb_darkening/02_bias_vs_u.png)

*↑ 測定の図*

```
py -3.11 examples/poc_solar_limb_darkening.py
```

ソース: [examples/poc_solar_limb_darkening.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_solar_limb_darkening.py)

使用 op(ノートへ): [`edge_points`](https://furuse.work/ops/3d/edges/edge_points.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`mat_lstsq`](https://furuse.work/ops/math/linalg/mat_lstsq.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html)

## 36. 全天カメラの雲量 ―― 画素を数えると位置で偏る

[![全天カメラの雲量 ―― 画素を数えると位置で偏る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_allsky_cloud_cover/03_mask_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_allsky_cloud_cover/03_mask_sweep.png)

*↑ **全天カメラの雲量 ―― 画素を数えると位置で偏る** ―― 魚眼(等距離射影)の空に球冠の雲(立体角は閉形式)を置き、画素数比と立体角重みで雲量を数えた図。同じ雲が天頂角 0 → 82 度で 0.00789 → 0.01142(1.45 倍)に読める。幾何だけの誤差 -5.02 % と検出だけの誤差 +37.95 % が、素朴な数え方では +29.73 % に打ち消し合う。*

[![画素数比は天頂で 0.81、地平線側で 1.17。重みを掛けると 1 に張り付く。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_allsky_cloud_cover/01_jacobian_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_allsky_cloud_cover/01_jacobian.png)

*↑ 測定の図 ―― 画素数比は天頂で 0.81、地平線側で 1.17。重みを掛けると 1 に張り付く。*

```
py -3.11 examples/poc_allsky_cloud_cover.py
```

ソース: [examples/poc_allsky_cloud_cover.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_allsky_cloud_cover.py)

使用 op(ノートへ): [`polar_trans_image`](https://furuse.work/ops/2d/geometry/polar_trans_image.html)

## 37. 海氷密接度 ―― 混合画素をどう数えるかで答えが変わる

[![海氷密接度 ―― 混合画素をどう数えるかで答えが変わる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sea_ice_concentration/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sea_ice_concentration/01_scene.png)

*↑ **海氷密接度 ―― 混合画素をどう数えるかで答えが変わる** ―― PSF でぼかした海氷/水の 2 バンド像から密接度を硬い分類と線形混合分解で出した図。硬い分類は -4.2 ポイント、分解は +0.02 ポイント。偏りは周長率で説明がつき(R² = 0.984)、密接度 0.49 付近でゼロを横切る ―― そこだけで検証すると合格する。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sea_ice_concentration/02_bias_vs_threshold_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sea_ice_concentration/02_bias_vs_threshold.png)

*↑ 測定の図*

```
py -3.11 examples/poc_sea_ice_concentration.py
```

ソース: [examples/poc_sea_ice_concentration.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_sea_ice_concentration.py)

使用 op(ノートへ): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`mat_lstsq`](https://furuse.work/ops/math/linalg/mat_lstsq.html)

## 38. 畑の緑を数える ―― 被覆率の真値を画素ごとの葉の面積率で持つ

[![畑の緑を数える ―― 被覆率の真値を画素ごとの葉の面積率で持つ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vegetation_cover/01_mixed_pixel_response_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vegetation_cover/01_mixed_pixel_response.png)

*↑ **畑の緑を数える ―― 被覆率の真値を画素ごとの葉の面積率で持つ** ―― 4 バンドの圃場像から被覆率を出し、画素ごとの葉の面積率を真値にした図。ゼロ点(緑チャネルに大津)は中期で +16.3 pp 上振れし、散らばりはどの手法も 0.5 pp 以下なので、効いている差はほぼ全部が偏り。発芽期・湿った土では被覆率の偏り -0.2 pp なのに適合率も再現率も 0.000 ―― 数字だけ合っていて画素が 1 つも当たっていない。*

[![影ゼロならゼロ点も悪くない。影は『暗さ』を手掛かりにする手法に直接刺さる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vegetation_cover/02_shadow_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vegetation_cover/02_shadow_sweep.png)

*↑ 測定の図 ―― 影ゼロならゼロ点も悪くない。影は『暗さ』を手掛かりにする手法に直接刺さる。*

```
py -3.11 examples/poc_vegetation_cover.py
```

ソース: [examples/poc_vegetation_cover.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_vegetation_cover.py)

使用 op(ノートへ): [`cv_otsu`](https://furuse.work/ops/2d/segmentation/cv_otsu.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`sk_otsu`](https://furuse.work/ops/2d/segmentation/sk_otsu.html)

## 39. 地形を測る ―― 傾斜・水の流れ・日当たりを閉形式と突き合わせる

[![地形を測る ―― 傾斜・水の流れ・日当たりを閉形式と突き合わせる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dem_terrain/01_cone_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dem_terrain/01_cone.png)

*↑ **地形を測る ―― 傾斜・水の流れ・日当たりを閉形式と突き合わせる** ―― 平面・円錐・ガウス丘で傾斜・曲率・天空率を閉形式と突き合わせた図。ガウス丘の曲率誤差はセルを半分にすると約 4 分の 1 ―― 離散化の誤差であって式の誤りではない。天空率は 513×513・8 方位で 2.03 秒 ―― 書き直す前は 41.9 秒かかっていて、テストは「動く」ことしか確かめていなかった。*

[![参照線と平行 = 2 次収束 = 離散化の誤差。式が違えばセルを細かくしても誤差は下げ止まる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dem_terrain/02_curvature_convergence_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dem_terrain/02_curvature_convergence.png)

*↑ 測定の図 ―― 参照線と平行 = 2 次収束 = 離散化の誤差。式が違えばセルを細かくしても誤差は下げ止まる。*

```
py -3.11 examples/poc_dem_terrain.py
```

ソース: [examples/poc_dem_terrain.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dem_terrain.py)

使用 op(ノートへ): [`dem_aspect`](https://furuse.work/ops/dem/surface/dem_aspect.html) · [`dem_curvature`](https://furuse.work/ops/dem/surface/dem_curvature.html) · [`dem_fill_sinks`](https://furuse.work/ops/dem/hydrology/dem_fill_sinks.html) · [`dem_flow_accumulation`](https://furuse.work/ops/dem/hydrology/dem_flow_accumulation.html) · [`dem_hillshade`](https://furuse.work/ops/dem/shading/dem_hillshade.html) · [`dem_sky_view_factor`](https://furuse.work/ops/dem/visibility/dem_sky_view_factor.html) · [`dem_slope`](https://furuse.work/ops/dem/surface/dem_slope.html)

## 40. 河川の水位を斜め写真から測る ―― 透視を無視した「行番号」は弓なりに外れる

[![河川の水位を斜め写真から測る ―― 透視を無視した「行番号」は弓なりに外れる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_water_level/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_water_level/01_scene.png)

*↑ **河川の水位を斜め写真から測る ―― 透視を無視した「行番号」は弓なりに外れる** ―― 量水標を斜めから撮った像で水面線を検出し、水位に直した図。目盛り 2 点の線形換算は最大 -6.4 cm(水位 1.00 m)弓なりに外れ、符号は水位でなく内挿(-6.6 cm)か外挿(+16.3 cm)かで決まる。4 点ホモグラフィなら 0.2 cm 以下で、残るのは透視でなく水面線の検出誤差。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_water_level/02_bias_vs_level_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_water_level/02_bias_vs_level.png)

*↑ 測定の図*

```
py -3.11 examples/poc_water_level.py
```

ソース: [examples/poc_water_level.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_water_level.py)

使用 op(ノートへ): [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`mat_svd`](https://furuse.work/ops/math/linalg/mat_svd.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`projective_trans_image`](https://furuse.work/ops/2d/geometry/projective_trans_image.html) · [`ransac_line`](https://furuse.work/ops/3d/robust_fit/ransac_line.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html)

## 41. 系外惑星トランジットを開口測光で取り出す ―― 深さと継続時間は別々に壊れる

[![系外惑星トランジットを開口測光で取り出す ―― 深さと継続時間は別々に壊れる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/01_scene_starfield_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/01_scene_starfield.png)

*↑ **系外惑星トランジットを開口測光で取り出す ―― 深さと継続時間は別々に壊れる** ―― 合成星野 240 枚に目標星だけ 10 ppt の周辺減光つきトランジットを仕込み、透明度変動・副画素ドリフト・フラット不均一・光子雑音を別々の乱数で載せて、fullseye の star_detect → frame_align → aperture_photometry で光度曲線を取り出す。ゼロ点(目標星の開口積分)は雲で深さ +72 ppt に壊れ、比較星との比なら -0.13 ppt / T14 -0.9 fr。比較星の選び方で残差 rms は 1.91〜11.43 ppt(6.0 倍)、逆分散重みは生の分散で決めると雲に騙されて単純和より 1.52 倍悪い。開口 1σ の崖は予想した重心誤差ではなく op の開口マスクの階段(supersample=8、不動の星で理論比 1.69 → 32 で 0.93)。検出限界 SNR=5 は暦既知で実測 1.48 / 理論 1.45 ppt、暦未知は 2.0 ppt で深さより先に継続時間が壊れる。ドリフト 2 px とフラット 3 % は単独で 0.16 / 0.08 ppt だが掛け算で 0.94 ppt、4 px で 2.97 ppt(真値の 30 %)の偽の深さ。*

[![前/入/最深部/出/後の各段階で平均した画像からトランジット外の平均を引いた [e-)。4 倍拡大](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/02_frames_transit_phases_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/02_frames_transit_phases.png)

*↑ 測定の図 ―― 前/入/最深部/出/後の各段階で平均した画像からトランジット外の平均を引いた [e-]。4 倍拡大*

```
py -3.11 examples/poc_exoplanet_transit.py
```

ソース: [examples/poc_exoplanet_transit.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_exoplanet_transit.py)

使用 op(ノートへ): [`aperture_photometry`](https://furuse.work/ops/astrostack/photometry/aperture_photometry.html) · [`frame_align`](https://furuse.work/ops/astrostack/align/frame_align.html) · [`normalize`](https://furuse.work/ops/shape2d/descriptor/normalize.html) · [`sigma_clip_stack`](https://furuse.work/ops/astrostack/stack/sigma_clip_stack.html) · [`star_detect`](https://furuse.work/ops/astrostack/photometry/star_detect.html)

## 42. 河川表面流速を斜め動画から測る(LSPIV)―― 速度の誤差と流量の誤差は別に数える

[![河川表面流速を斜め動画から測る(LSPIV)―― 速度の誤差と流量の誤差は別に数える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/01_scene.png)

*↑ **河川表面流速を斜め動画から測る(LSPIV)―― 速度の誤差と流量の誤差は別に数える** ―― 幅 8 m・最大 1.5 m/s のべき乗則の流速分布を真値に、泡トレーサを毎コマ動かして描いた川面を岸の斜めカメラ(ホモグラフィ既知)で 60 コマ撮り、空の映り込み・波紋・雑音を別々に足して、fullseye の piv_cross_correlate → warp_by_plane(正射化)→ piv_to_velocity で u(y) と流量 Q = h∫u dy を出す。ゼロ点(斜めのまま 1 尺度で換算)は近岸 +0.31 / 遠岸 -0.28 m/s と符号が逆で、見かけの川幅が 3.3 m に化けて流量 -57 %。正射化で速度 RMS 0.074 m/s・流量 -7.8 % だが、対照群でも流量 -3.0 % のうち -2.5 % は岸の台形積分だけで生じ、速度とは無関係。密度の崖は nan ではなく外れ値で来る(0.05 % で旗 44 %、アンサンブル相関は外れ窓を救わない)。窓を広げても岸の速度は「窓幅×勾配」の予想より桁で小さく(-0.008 m/s)、代わりに流量が -1.1 → -7.0 % と崖になる。動かない映り込みは細かいときだけ効き、引かれてから(速度比 0.70)張り付く(0.03)、時間中央値引きで 0.998 に戻る。dt の崖は 1/4 則ではなく対の消失で、探索上限を外しても同じ k=4 に立つ。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/02_frames_oblique_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/02_frames_oblique.png)

*↑ 測定の図*

```
py -3.11 examples/poc_river_surface_velocity.py
```

ソース: [examples/poc_river_surface_velocity.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_river_surface_velocity.py)

使用 op(ノートへ): [`highpass_image`](https://furuse.work/ops/2d/frequency/highpass_image.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`piv_ensemble_correlate`](https://furuse.work/ops/piv/estimate/piv_ensemble_correlate.html) · [`piv_error_stats`](https://furuse.work/ops/piv/assess/piv_error_stats.html) · [`piv_outlier_mask`](https://furuse.work/ops/piv/validate/piv_outlier_mask.html) · [`piv_replace_outliers`](https://furuse.work/ops/piv/validate/piv_replace_outliers.html) · [`piv_sample_at_windows`](https://furuse.work/ops/piv/assess/piv_sample_at_windows.html) · [`piv_to_velocity`](https://furuse.work/ops/piv/field/piv_to_velocity.html) · [`sigma_clip_stack`](https://furuse.work/ops/astrostack/stack/sigma_clip_stack.html) · [`warp_by_plane`](https://furuse.work/ops/3d/plane_sweep_stereo/warp_by_plane.html)

## 43. 変化検出と位置合わせ誤差 ―― 偽陽性はエッジの帯、しかも崖つき

[![変化検出と位置合わせ誤差 ―― 偽陽性はエッジの帯、しかも崖つき](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/03_map_fp_shift_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/03_map_fp_shift.png)

*↑ **変化検出と位置合わせ誤差 ―― 偽陽性はエッジの帯、しかも崖つき** ―― 2 時期の合成地表(畑・道路・建物・森林・湖)に建物新設・伐採・水域拡大を仕込み、時期 2 をサブピクセル平行移動・微小回転・照明差で崩して差分の偽陽性を測った。偽陽性はずれ 0.3 px まで雑音の床、0.5 px から崖(PSF から予測した δ*=τσ√2π/C=0.351 px と一致)、3 px で 7175 px。エッジ総長×ずれの比例則は 3 px で 0.78 倍だが崖を説明せず、PSF と雑音を入れた台帳予測は 0.84〜1.07 倍。位置合わせ 3 経路(PIV/特徴点/LK)は残留 0.02〜0.13 px まで戻すが、唯一の位相相関は 3-D 用の整数精度で残留 0.72 px ―― その偽陽性 995 px は「ずれだけ」の掃引を同じ残留で読んだ 915 px に乗る。伐採は位置合わせが完璧でも検出率 0.33、照明差だけの偽陽性 17198 px は放射補正で 0 になるがずれの 3497 px は直らない。*

[![0.35 px までゼロ、そこから立ち上がる。比例則は崖を説明しない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/01_plot_fp_vs_shift_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/01_plot_fp_vs_shift.png)

*↑ 測定の図 ―― 0.35 px までゼロ、そこから立ち上がる。比例則は崖を説明しない。*

```
py -3.11 examples/poc_change_detection_misreg.py
```

ソース: [examples/poc_change_detection_misreg.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_change_detection_misreg.py)

使用 op(ノートへ): [`affine_trans_image`](https://furuse.work/ops/2d/geometry/affine_trans_image.html) · [`histogram_match`](https://furuse.work/ops/colortransport/matching/histogram_match.html) · [`match_phase_3d`](https://furuse.work/ops/3d/match_pose/match_phase_3d.html) · [`opening_circle`](https://furuse.work/ops/2d/region/opening_circle.html) · [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`piv_outlier_mask`](https://furuse.work/ops/piv/validate/piv_outlier_mask.html) · [`procrustes_fit`](https://furuse.work/ops/shapestat/procrustes/procrustes_fit.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html) · [`voxel_iou`](https://furuse.work/ops/3d/metrics/voxel_iou.html)

## 44. 葉の病斑面積率 ―― 色の軸は照明に勝つが、等級は葉マスクと縁の定義で決まる

[![葉の病斑面積率 ―― 色の軸は照明に勝つが、等級は葉マスクと縁の定義で決まる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/01_scene.png)

*↑ **葉の病斑面積率 ―― 色の軸は照明に勝つが、等級は葉マスクと縁の定義で決まる** ―― 閉形式の葉輪郭に既知面積の病斑を植え、土・片側照明・白飛び・影を重ねた合成葉で、病斑面積率(病斑画素/葉画素)を測る。緑チャネルの固定しきい値(ゼロ点)は土の背景だけで +65.2 pt 外れ、白色方向を射影で消した G で葉を切り Lab の a* で病斑を切ると標準場面で -0.8 pt に収まる。照明むらは 50 % まで a* を動かさないが、白飛びの鏡面反射は a* に偽陽性だけを出し(20 % で +12.6 pt、偽陰性 0.0)、白を足しても動かない色相なら +2.0 pt。病斑の縁のぼけ幅 4 px では「不透明度 25 %/75 % のどちらを境界にするか」だけで面積率が ±3.5 pt 動き(Steiner の式が 0.4 pt 以内で予測)、等級境界 ±3 pt に置いた 40 枚は土の上ではどの手法も 19〜35 枚が誤等級 ―― 黒布の上で明るさで葉を切ると色相の固定しきい値で 8 枚。*

[![FN(青)の大きな塊は影と鏡面反射が重なった病斑(葉マスクごと落ちる)。FP(赤)は鏡面反射の下と病斑の縁。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/02_error_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/02_error_map.png)

*↑ 測定の図 ―― FN(青)の大きな塊は影と鏡面反射が重なった病斑(葉マスクごと落ちる)。FP(赤)は鏡面反射の下と病斑の縁。*

```
py -3.11 examples/poc_leaf_disease_area.py
```

ソース: [examples/poc_leaf_disease_area.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_leaf_disease_area.py)

使用 op(ノートへ): [`access_channel`](https://furuse.work/ops/2d/color/access_channel.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`fill_holes`](https://furuse.work/ops/2d/region/fill_holes.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`linear_to_srgb`](https://furuse.work/ops/gfx2d/colorspace/linear_to_srgb.html) · [`reg_close`](https://furuse.work/ops/2d/region/reg_close.html) · [`reg_erode`](https://furuse.work/ops/2d/region/reg_erode.html) · [`rgb_to_lab`](https://furuse.work/ops/imgmetrics/colorspace/rgb_to_lab.html) · [`select_largest`](https://furuse.work/ops/2d/region/select_largest.html) · [`sk_otsu`](https://furuse.work/ops/2d/segmentation/sk_otsu.html) · [`specular_free_transform`](https://furuse.work/ops/specular/dichromatic/specular_free_transform.html) · [`srgb_to_linear`](https://furuse.work/ops/gfx2d/colorspace/srgb_to_linear.html) · [`trans_from_rgb`](https://furuse.work/ops/2d/color/trans_from_rgb.html)

## 45. 年輪を数えて幅の時系列を取り出す ―― 年数の誤差と幅の相関は別の量

[![年輪を数えて幅の時系列を取り出す ―― 年数の誤差と幅の相関は別の量](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/01_scene.png)

*↑ **年輪を数えて幅の時系列を取り出す ―― 年数の誤差と幅の相関は別の量** ―― 偏心した髄・偏心成長・周方向のうねり・うねる割れ目・腐朽斑・木目・ぼけを載せた 36 年の円板を閉形式で仕込み、髄から 1 本の放射線のピーク数(ゼロ点)と、極座標展開+外縁で半径を正規化+θ 方向メディアン+24 扇形の測定線の合意(中央値)を比べた。ゼロ点は 24 方向中 18 方向でしか年数が合わないが、間違えた 6 方向でも幅の相関は中央値 0.900。合意法は 36 年・欠落 0・幅の相関 0.996(平均誤差 0.13 px)。髄の推定誤差 20 px でも幅の相関は 0.994 ―― cos で変調されるのは半径(傾き -14.9 px)で幅(-0.02 px)ではなく、減るのは髄近くの年数(予測 2 / 実測 2)。細い年輪は合意法 2.5 px、ゼロ点 3.0 px から落ち、ぼけ σ 4 px でゼロ点は偽輪 13 本を数える。*

[![偏心成長で境界が θ とともに斜めに走るので、正規化しないとθ 窓の中で外側の年輪がにじむ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/02_polar_stages_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/02_polar_stages.png)

*↑ 測定の図 ―― 偏心成長で境界が θ とともに斜めに走るので、正規化しないとθ 窓の中で外側の年輪がにじむ。*

```
py -3.11 examples/poc_tree_ring_dendro.py
```

ソース: [examples/poc_tree_ring_dendro.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_tree_ring_dendro.py)

使用 op(ノートへ): [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`median_rect`](https://furuse.work/ops/2d/rank/median_rect.html) · [`polar_unwrap`](https://furuse.work/ops/3d/curvilinear/polar_unwrap.html)

### 撮像品質・復元ウィング ―― 絵が良くなることと真値に近づくことは別

手ブレを戻す、拡大する、霞を剥がす、深度合成する、投影から再構成する、光子を数えて距離を出す。復元の分野は「見た目が良くなった」と「真値に近づいた」が最も混ざりやすい場所です。この部屋の 7 点は、核・深度・大気光・PSD・投影・到達時刻をこちらが決めた合成で、その 2 つを分けて採点しています。

見た目の指標は真値を最大値としません。霞んだ入力の対比が真値より高い、アンシャープで勾配は真値に一致するのに PSNR は落ちる、雑音を足すと PSNR が上がる。逆に、ナイキストより細かい縞を戻したのに PSNR が -0.01 dB しか動かない場面もあります。

共通して置いたゼロ点は「何もしない」です。核の角度が 19.4 度ずれた復元、投影 12 本の FBP、視程 782 m 以上の除霞、無テクスチャ領域の深度。いずれもそのゼロ点に負けます。負ける条件を数字で置くことが、この部屋の展示の中身です。

## 46. 手ブレはどこまで戻せるか ―― 核を自分で作り、掛けて、戻して、元と比べる

[![手ブレはどこまで戻せるか ―― 核を自分で作り、掛けて、戻して、元と比べる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/01_noise_ceiling_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/01_noise_ceiling.png)

*↑ **手ブレはどこまで戻せるか ―― 核を自分で作り、掛けて、戻して、元と比べる** ―― 既知の直線ブレ核を掛けて戻し、雑音と核の推定誤差で上限を測った図。無雑音なら 22.38 → 56.41 dB、SNR 20 dB では取り分 1.82 dB。核の角度が 19.4 度ずれると「何もしない」に抜かれ、回転ブレを 1 枚の核で戻すと回転中心が -49.41 dB 悪化する。*

[![4 枚目は「復元した」形をしているが、ゼロ点(観測そのもの)より悪い。絵の見た目では区別できない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/02_deblur_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/02_deblur.png)

*↑ 測定の図 ―― 4 枚目は「復元した」形をしているが、ゼロ点(観測そのもの)より悪い。絵の見た目では区別できない。*

```
py -3.11 examples/poc_camera_shake_deblur.py
```

ソース: [examples/poc_camera_shake_deblur.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_camera_shake_deblur.py)

使用 op(ノートへ): [`psnr`](https://furuse.work/ops/imgmetrics/fidelity/psnr.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`ssim`](https://furuse.work/ops/imgmetrics/fidelity/ssim.html) · [`unsharp`](https://furuse.work/ops/2d/smoothing/unsharp.html) · [`vol_richardson_lucy`](https://furuse.work/ops/3d/restoration/vol_richardson_lucy.html)

## 47. 超解像は情報を増やすのか ―― 真値を持ったまま縮小して、戻して、数える

[![超解像は情報を増やすのか ―― 真値を持ったまま縮小して、戻して、数える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/03_multiframe_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/03_multiframe.png)

*↑ **超解像は情報を増やすのか ―― 真値を持ったまま縮小して、戻して、数える** ―― 真値を縮小して観測を作り、単一画像拡大・逆投影・drizzle を分解能の列で採点した図。単一画像の拡大は bicubic のゼロ点を最大 +0.036 dB しか上回れない。副画素ずれのある 16 枚の drizzle は標本化不足の条件で +13.96 dB、ナイキスト超えの周期 6 の変調度が 0.03 → 0.38 に立ち上がる。*

[![鮮鋭化だけがナイキスト(周期 8)より細かい列にも縞を作る。それは分解能ではなく**無い縞**。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/01_upscale_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/01_upscale.png)

*↑ 測定の図 ―― 鮮鋭化だけがナイキスト(周期 8)より細かい列にも縞を作る。それは分解能ではなく**無い縞**。*

```
py -3.11 examples/poc_superresolution_limits.py
```

ソース: [examples/poc_superresolution_limits.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_superresolution_limits.py)

使用 op(ノートへ): [`drizzle_resample`](https://furuse.work/ops/astrostack/stack/drizzle_resample.html) · [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`psnr`](https://furuse.work/ops/imgmetrics/fidelity/psnr.html) · [`ssim`](https://furuse.work/ops/imgmetrics/fidelity/ssim.html) · [`unsharp`](https://furuse.work/ops/2d/smoothing/unsharp.html) · [`vol_fft_lowpass`](https://furuse.work/ops/3d/frequency/vol_fft_lowpass.html) · [`vol_resize`](https://furuse.work/ops/3d/geom_transform/vol_resize.html) · [`volume_downsample`](https://furuse.work/ops/3d/preprocess/volume_downsample.html)

## 48. 霞を剥がす ―― 大気散乱モデルで真値を作り、透過率と大気光を別々に採点する

[![霞を剥がす ―― 大気散乱モデルで真値を作り、透過率と大気光を別々に採点する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/01_scene.png)

*↑ **霞を剥がす ―― 大気散乱モデルで真値を作り、透過率と大気光を別々に採点する** ―― 深度・大気光・消散係数から真の透過率とシーンを持った霞画像を作り、除霞を採点した図。全体 +4.04 dB の中身は近景 -1.49 dB の劣化を中景 +4.03 / 遠景 +11.28 dB が覆ったもの。視程 782 m 以上では除霞が害になり、雑音を足すと PSNR が上がる(偶然の打ち消し)。*

[![空では過大評価(明るい側)、近景では過小評価(暗い側)。全体の平均バイアスでは打ち消し合って見えない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/02_transmission_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/02_transmission.png)

*↑ 測定の図 ―― 空では過大評価(明るい側)、近景では過小評価(暗い側)。全体の平均バイアスでは打ち消し合って見えない。*

```
py -3.11 examples/poc_dehazing.py
```

ソース: [examples/poc_dehazing.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dehazing.py)

使用 op(ノートへ): [`clahe`](https://furuse.work/ops/2d/gray/clahe.html) · [`equalize`](https://furuse.work/ops/2d/gray/equalize.html) · [`image_entropy`](https://furuse.work/ops/imgmetrics/information/image_entropy.html) · [`joint_bilateral`](https://furuse.work/ops/3d/depth_denoise/joint_bilateral.html) · [`psnr`](https://furuse.work/ops/imgmetrics/fidelity/psnr.html) · [`rank_image`](https://furuse.work/ops/2d/rank/rank_image.html) · [`ssim`](https://furuse.work/ops/imgmetrics/fidelity/ssim.html)

## 49. 深度合成 ―― 全焦点画像と深度地図は別物

[![深度合成 ―― 全焦点画像と深度地図は別物](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/01_stack_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/01_stack.png)

*↑ **深度合成 ―― 全焦点画像と深度地図は別物** ―― 錯乱円の閉形式で深さに応じたぼけを掛けた 15 枚から、全焦点画像と深度地図を取り出した図。全焦点は 35.89 dB(ゼロ点 20.98 dB)なのに、同じ融合の深度は無テクスチャ領域でゼロ点に 8 倍負ける(0.13 倍)。相対量の信頼度は無テクスチャで 0.9923 と有テクスチャの 0.9630 より高く出る ―― 絶対値(23600 倍差)で棄却すると RMS 1.505 → 0.878 mm。*

[![左下の無テクスチャの四角だけ、誤差が掃引全域にばらけた乱数になっている(段差帯のハローも見える)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/02_depth_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/02_depth_map.png)

*↑ 測定の図 ―― 左下の無テクスチャの四角だけ、誤差が掃引全域にばらけた乱数になっている(段差帯のハローも見える)。*

```
py -3.11 examples/poc_focus_stacking.py
```

ソース: [examples/poc_focus_stacking.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_focus_stacking.py)

使用 op(ノートへ): [`csi_height_map`](https://furuse.work/ops/interferometry/surface/csi_height_map.html) · [`defocus_blur`](https://furuse.work/ops/optics/scene/defocus_blur.html) · [`dilation_circle`](https://furuse.work/ops/2d/region/dilation_circle.html) · [`fuse`](https://furuse.work/ops/3d/tsdf_fusion/fuse.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`laplace`](https://furuse.work/ops/2d/edges/laplace.html) · [`mean_image`](https://furuse.work/ops/2d/smoothing/mean_image.html) · [`optical_camera`](https://furuse.work/ops/optics/scene/optical_camera.html) · [`psnr`](https://furuse.work/ops/imgmetrics/fidelity/psnr.html) · [`sobel_amp`](https://furuse.work/ops/2d/edges/sobel_amp.html) · [`xcv2_lap_var`](https://furuse.work/ops/2d/features/xcv2_lap_var.html)

## 50. 投影数を減らすと CT 再構成はどこから壊れるか

[![投影数を減らすと CT 再構成はどこから壊れるか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_fidelity/01_recon_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_fidelity/01_recon_sweep.png)

*↑ **投影数を減らすと CT 再構成はどこから壊れるか** ―― Shepp-Logan を 180 → 12 本で撮り直し、FBP を空白画像と無フィルタ逆投影の 2 つの零点と並べた図。12 本の FBP(RMSE 0.2576)は空白画像(0.2420)より悪い。サイノグラムの行和という再構成を見ない検算が、RMSE では見えない質量欠損 -3.34 % を捕まえ、ランプフィルタの DC ビンを直して -0.0099 % に。*

[![RMSE で見ると 12 本は空白画像 0.2420 より悪い。相関とストリークは別のことを言う。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_fidelity/02_fidelity_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_fidelity/02_fidelity_table.png)

*↑ 測定の図 ―― RMSE で見ると 12 本は空白画像 0.2420 より悪い。相関とストリークは別のことを言う。*

```
py -3.11 examples/poc_ct_fidelity.py
```

ソース: [examples/poc_ct_fidelity.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_fidelity.py)

使用 op(ノートへ): [`backproject_sinogram`](https://furuse.work/ops/tomography/reconstruct/backproject_sinogram.html) · [`ellipse_phantom`](https://furuse.work/ops/tomography/forward/ellipse_phantom.html) · [`ellipse_sinogram`](https://furuse.work/ops/tomography/forward/ellipse_sinogram.html) · [`filtered_backprojection`](https://furuse.work/ops/tomography/reconstruct/filtered_backprojection.html) · [`projection_angles`](https://furuse.work/ops/tomography/layout/projection_angles.html) · [`radon_transform`](https://furuse.work/ops/tomography/forward/radon_transform.html) · [`rmse`](https://furuse.work/ops/imgmetrics/fidelity/rmse.html) · [`ssim`](https://furuse.work/ops/imgmetrics/fidelity/ssim.html) · [`stat_correlation`](https://furuse.work/ops/math/stats/stat_correlation.html)

## 51. ライトフィールドから深度を出す ―― 既知の深度で作った光場に、ゼロ点を並べて突きつける

[![ライトフィールドから深度を出す ―― 既知の深度で作った光場に、ゼロ点を並べて突きつける](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/01_scene_and_depth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/01_scene_and_depth.png)

*↑ **ライトフィールドから深度を出す ―― 既知の深度で作った光場に、ゼロ点を並べて突きつける** ―― 9×9 の光場を解析的な逆写像で描き、真値スロープ地図に対して焦点度・EPI・2 眼ブロックマッチングを採点した図。定数ゼロ点には 22 倍勝つが、視点 2 枚だけ使う 2 眼に対しては cubic でようやく 1.6 倍。既定の linear 補間は整数スロープに吸着し、真値 1.30 を 1.4750 と読む(深度で 11.9 %)。*

[![linear は 1.08/1.15 を 1.0 へ、1.85 を 2.0 側へ引く。cubic は恒等線に乗る。生成側の補間はゼロ(Fourier シフト)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/02_focus_snapping_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/02_focus_snapping.png)

*↑ 測定の図 ―― linear は 1.08/1.15 を 1.0 へ、1.85 を 2.0 側へ引く。cubic は恒等線に乗る。生成側の補間はゼロ(Fourier シフト)。*

```
py -3.11 examples/poc_lightfield_depth.py
```

ソース: [examples/poc_lightfield_depth.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_lightfield_depth.py)

使用 op(ノートへ): [`lf_depth_from_focus`](https://furuse.work/ops/lightfield/depth/lf_depth_from_focus.html) · [`lf_disparity_to_depth`](https://furuse.work/ops/lightfield/depth/lf_disparity_to_depth.html) · [`lf_epi`](https://furuse.work/ops/lightfield/views/lf_epi.html) · [`lf_epi_slope`](https://furuse.work/ops/lightfield/depth/lf_epi_slope.html) · [`lf_refocus`](https://furuse.work/ops/lightfield/refocus/lf_refocus.html)

## 52. 光子を数えて距離を測る ―― 何個数えれば何ミリまで出るのか

[![光子を数えて距離を測る ―― 何個数えれば何ミリまで出るのか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/01_histograms_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/01_histograms.png)

*↑ **光子を数えて距離を測る ―― 何個数えれば何ミリまで出るのか** ―― 往復時刻にガウシアンをビン積分で置き Poisson 標本を引いた到達時刻ヒストグラムから距離を読む図。N = 200 光子でピーク位置そのまま 11.02 mm、ゲート重心 2.29 mm、理論限界 31.83 mm/√N に 1.00〜1.07 倍で乗る。背景が入ると素の重心は 2 桁崩れ(SBR 0.031 で 564 mm)、族が推すガウス当てはめ 8.82 mm は利用者が 6 行で書くゲート重心に負ける。*

[![背景が無ければ素の重心で足りる。背景が入ると 2 桁崩れ、docstring が勧める背景減算でも戻らない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/02_methods_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/02_methods.png)

*↑ 測定の図 ―― 背景が無ければ素の重心で足りる。背景が入ると 2 桁崩れ、docstring が勧める背景減算でも戻らない。*

```
py -3.11 examples/poc_dtof_ranging.py
```

ソース: [examples/poc_dtof_ranging.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dtof_ranging.py)

使用 op(ノートへ): [`dtof_cube_depth`](https://furuse.work/ops/photon/dtof/dtof_cube_depth.html) · [`dtof_cube_simulate`](https://furuse.work/ops/photon/dtof/dtof_cube_simulate.html) · [`dtof_depth`](https://furuse.work/ops/photon/dtof/dtof_depth.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`tcspc_background_subtract`](https://furuse.work/ops/photon/tcspc/tcspc_background_subtract.html) · [`tcspc_coates_correct`](https://furuse.work/ops/photon/spad/tcspc_coates_correct.html) · [`tcspc_simulate`](https://furuse.work/ops/photon/tcspc/tcspc_simulate.html)

### 時系列を 3-D として測るウィング ―― 動画は 1 つの体積

2-D の動画を (t, y, x) の 1 つの体積とみなすと、3-D の op ―― 連結成分、等値面、領域特徴 ―― がそのまま時間方向に効きます。合体したコロニーは時空間で Y 字になり、通過する車は (t, x) 画像の帯になり、波面の到達時刻は等値面になります。この部屋の 6 点はその実演です。

同時に、時間方向ならではの罠も出ました。フレーム格子への丸めは必ず遅らせ、画素の面積は合体を早める。誤リンクには向きの逆な 2 種類があり、誤り率 1 本では拡散係数がどちらへ外れるか決まらない。テンプレート追跡は見失うより先に静かにずれ、ずれた 152 フレーム全部が「見つけた」と報告する。

モーション拡大の展示は、この部屋でいちばん正直な結論を持っています。拡大率 200 まで機械精度で厳密に動くのに、測定の役には立たない ―― 拡大は人間に見せるための道具です。

## 53. 成長のタイムラプスを時空間の連結成分として測る

[![成長のタイムラプスを時空間の連結成分として測る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/01_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/01_frames.png)

*↑ **成長のタイムラプスを時空間の連結成分として測る** ―― 広がって合体するコロニーの動画を (t, y, x) の体積として 3-D 連結成分で読んだ図。画素が面積を持つせいで合体は早く見え(組 0-1 で -1.16 フレーム)、フレーム格子への丸めは遅らせる(+0.94) ―― 逆向きなので合計は小さく見える。`vol_label` の既定 26 近傍は、隙間 0.92 のニアミスを合体させた。*

[![縦が時間(下向き、4 倍に拡大)、横が列。2 本の管が合わさる高さがそのまま合体時刻。色は 3-D ラベル。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/02_ystructure_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/02_ystructure.png)

*↑ 測定の図 ―― 縦が時間(下向き、4 倍に拡大)、横が列。2 本の管が合わさる高さがそのまま合体時刻。色は 3-D ラベル。*

```
py -3.11 examples/poc_timelapse_growth.py
```

ソース: [examples/poc_timelapse_growth.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_timelapse_growth.py)

使用 op(ノートへ): [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_region_props`](https://furuse.work/ops/3d/regionprops/vol_region_props.html)

## 54. (x, y, t) で数える ―― 通過台数とオクルージョン、そして L/V という 1 つの定数

[![(x, y, t) で数える ―― 通過台数とオクルージョン、そして L/V という 1 つの定数](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/01_per_frame_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/01_per_frame.png)

*↑ **(x, y, t) で数える ―― 通過台数とオクルージョン、そして L/V という 1 つの定数** ―― 車を流した合成動画で、フレームごとの計数・仮想ループ・(t, x) スリット画像の連結成分を並べた図。フレームごとの最大値は通過 10 台に対し 7 ―― 別の量を測っている。破綻の条件は 3 つとも車長 ÷ 速度 = L/V(9.0 フレーム)で書け、フレーム間隔 16 では帯が千切れて 10 → 49 台。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/02_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/02_scene.png)

*↑ 測定の図*

```
py -3.11 examples/poc_traffic_counting.py
```

ソース: [examples/poc_traffic_counting.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_traffic_counting.py)

使用 op(ノートへ): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html)

## 55. 到達時刻面を (x, y, t) の等値面として取り出す

[![到達時刻面を (x, y, t) の等値面として取り出す](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/01_dt_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/01_dt_sweep.png)

*↑ **到達時刻面を (x, y, t) の等値面として取り出す** ―― 点源から広がる波面の到達時刻面を (x, y, t) 体積の等値面として取り出した図。ゼロ点(初めて超えたフレーム番号)の偏りは Δt/2 で枚数では消えず、線形補間で 27 倍(0.0209 ms)。放物線補間は線形に負け、しきい値がガウス波形の変曲点 θ = 0.6065 にあるとき線形が最良(3.8 倍差)。*

[![変曲点 θ=0.6065 では線形が 3.8 倍勝ち、θ=0.2 では放物線が 3.6 倍勝つ。交点は θ≈0.35 と θ≈0.75。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/02_threshold_crossover_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/02_threshold_crossover.png)

*↑ 測定の図 ―― 変曲点 θ=0.6065 では線形が 3.8 倍勝ち、θ=0.2 では放物線が 3.6 倍勝つ。交点は θ≈0.35 と θ≈0.75。*

```
py -3.11 examples/poc_xyt_event_surface.py
```

ソース: [examples/poc_xyt_event_surface.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_xyt_event_surface.py)

使用 op(ノートへ): [`vertex_normals`](https://furuse.work/ops/3d/mesh_process/vertex_normals.html) · [`vol_edge_probe`](https://furuse.work/ops/3d/probe/vol_edge_probe.html)

## 56. 粒子追跡を (行, 列, 時刻) の体積として測る ―― 誤リンクの向きは 1 種類ではない

[![粒子追跡を (行, 列, 時刻) の体積として測る ―― 誤リンクの向きは 1 種類ではない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/01_spacetime_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/01_spacetime.png)

*↑ **粒子追跡を (行, 列, 時刻) の体積として測る ―― 誤リンクの向きは 1 種類ではない** ―― 400 個の粒子の動画を追跡し、軌跡から拡散係数 D を読んだ図。曖昧な誤リンクは D を 0.925 倍に下げ、欠測による誤リンクは同じ動画で 3.429 倍に上げる ―― 誤り率 1 本では向きが決まらない。効くのは 1 対 1 制約ではなく、上限距離のゲート 1 行(3.429 → 1.304)。*

[![縦軸は常用対数(0 が真値)。欠測は遠い他人を掴んで D を上げ、曖昧は近い相手を選んで D を下げる。上限距離のゲート 1 行で上向きの暴走が 1/2.6 に。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/02_density_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/02_density_bias.png)

*↑ 測定の図 ―― 縦軸は常用対数(0 が真値)。欠測は遠い他人を掴んで D を上げ、曖昧は近い相手を選んで D を下げる。上限距離のゲート 1 行で上向きの暴走が 1/2.6 に。*

```
py -3.11 examples/poc_particle_tracking.py
```

ソース: [examples/poc_particle_tracking.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_particle_tracking.py)

使用 op(ノートへ): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_local_maxima`](https://furuse.work/ops/3d/feature/vol_local_maxima.html)

## 57. テンプレート追跡は「見失う」より先に「静かにずれる」

[![テンプレート追跡は「見失う」より先に「静かにずれる」](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/01_ncc_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/01_ncc_maps.png)

*↑ **テンプレート追跡は「見失う」より先に「静かにずれる」** ―― 既知の相似変換でカメラを動かし、テンプレート追跡が「見失う」「静かにずれる」「自信満々で間違える」の 3 通りで壊れるのを見た図。ずれていた 152 フレームの 152 フレーム全部が、遮蔽なしで校正したピークのしきい値を通って「見つけた」と報告した。真値なしで測れる絶対量は往復追跡の不一致だけ。*

[![同じ遮蔽率でも、そっくりな別物体が視野に居るだけで崖がはるかに手前へ来る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/02_occlusion_vs_twin_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/02_occlusion_vs_twin.png)

*↑ 測定の図 ―― 同じ遮蔽率でも、そっくりな別物体が視野に居るだけで崖がはるかに手前へ来る。*

```
py -3.11 examples/poc_template_tracking.py
```

ソース: [examples/poc_template_tracking.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_template_tracking.py)

使用 op(ノートへ): [`ncc_locate`](https://furuse.work/ops/2d/matching/ncc_locate.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`shape_locate`](https://furuse.work/ops/2d/matching/shape_locate.html)

## 58. 構造物の微小振動を映像から測る ―― モーション拡大は「測る」役に立つのか

[![構造物の微小振動を映像から測る ―― モーション拡大は「測る」役に立つのか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/01_slit_scan_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/01_slit_scan.png)

*↑ **構造物の微小振動を映像から測る ―― モーション拡大は「測る」役に立つのか** ―― 既知振幅 0.02 px・3.7 Hz の振動を合成し、モーション拡大が測定に効くかを見た図。拡大率 α = 200 まで機械精度で厳密。だが拡大は測定精度を良くしない ―― 位相を α 倍すると雑音も α 倍。片持ち梁では位相相関が 0.30 と 0.00 px の面積平均 0.15 px という、どこにも存在しない数を返す。*

[![剛体を仮定する位相相関が返す 0.150 px は 0.30 と 0.00 の面積平均で、どの列の真値とも違う。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/02_beam_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/02_beam_profile.png)

*↑ 測定の図 ―― 剛体を仮定する位相相関が返す 0.150 px は 0.30 と 0.00 の面積平均で、どの列の真値とも違う。*

```
py -3.11 examples/poc_motion_magnification.py
```

ソース: [examples/poc_motion_magnification.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_motion_magnification.py)

使用 op(ノートへ): [`band_snr`](https://furuse.work/ops/motionmag/temporal/band_snr.html) · [`displacement_series`](https://furuse.work/ops/motionmag/measure/displacement_series.html) · [`motion_magnify`](https://furuse.work/ops/motionmag/magnify/motion_magnify.html) · [`phase_displacement`](https://furuse.work/ops/motionmag/measure/phase_displacement.html) · [`synthesize_translation`](https://furuse.work/ops/motionmag/synthesis/synthesize_translation.html) · [`temporal_band_power`](https://furuse.work/ops/motionmag/temporal/temporal_band_power.html) · [`temporal_bandpass`](https://furuse.work/ops/motionmag/temporal/temporal_bandpass.html)

## 59. 動画から固有振動数・減衰比・モード形状を同定する ―― f は最後まで生き残り、ζ が先に嘘をつく

[![動画から固有振動数・減衰比・モード形状を同定する ―― f は最後まで生き残り、ζ が先に嘘をつく](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/01_scene.png)

*↑ **動画から固有振動数・減衰比・モード形状を同定する ―― f は最後まで生き残り、ζ が先に嘘をつく** ―― 片持ち梁(Euler–Bernoulli 閉形式)の 3 モード自由減衰を、雑音・照明ちらつき 100 Hz・手ぶれ・ローリングシャッター入りの動画に合成し、位相法(phase_displacement)と PIV(piv_cross_correlate)で f_n / ζ_n / MAC を測る。f_n は 3 モードとも 0.06 Hz 以内で当たるが、同じ時系列から出した ζ_1 は半値幅 0.0778 / 包絡線 0.0188 / 当てはめ 0.0181(真値 0.02)と方法で 3 通り。振幅を 0.02→2 px で掃引すると壊れる順番は f → ζ → MAC_2 → MAC_3 で、位相法は 0.02 px で f_1 誤差 +0.030 Hz のまま ζ_1 が真値の 0.23 倍になる。fps 48.5 では照明の折り返しがちょうど 3.00 Hz = f_1 に乗り、輝度のゼロ点は ζ を出せず位相法は 0.0191 で生き残る。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/02_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/02_frames.png)

*↑ 測定の図*

```
py -3.11 examples/poc_beam_modal_video.py
```

ソース: [examples/poc_beam_modal_video.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_beam_modal_video.py)

使用 op(ノートへ): [`phase_displacement`](https://furuse.work/ops/motionmag/measure/phase_displacement.html) · [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`temporal_bandpass`](https://furuse.work/ops/motionmag/temporal/temporal_bandpass.html)

### 幾何・校正ウィング ―― 残差が小さいことは正しさの証明にならない

カメラ校正の再投影誤差、パノラマの継ぎ目、点群位置合わせの残差。どれも「小さいほど良い」と読まれる数字ですが、この部屋の 3 点はその読み方が成り立たない場面を、真値を握った上で並べています。

再投影誤差 0.0688〜0.0690 px で焦点距離の誤差が 0.026〜7.334 %。隣の継ぎ目が 0.12 px なのに閉じる 1 本だけ 1.5 px。球や円柱では残差が同じまま姿勢が任意。最小二乗は残差を雑音まで落とすのが仕事で、落ちた先が真値かどうかは別の話です。

測り方そのものの罠も残してあります。点群を 1 組固定して姿勢だけ振っても標本は 1 つしか無く、乱数の種だけで「象限誤り 0 %」と「100 %」の両方が出ました。真値なしで測れる絶対量は、一周する撮り方の閉ループ誤差くらいしかありません。

## 60. 再投影誤差 0.05 px は何も保証しない

[![再投影誤差 0.05 px は何も保証しない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/03_frame_fill_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/03_frame_fill.png)

*↑ **再投影誤差 0.05 px は何も保証しない** ―― 既知の内部パラメータと姿勢で格子点を投影し、校正し直して成分ごとに誤差を出した図。板の傾き 32 / 8 / 2 度で再投影 RMS は 0.0688〜0.0690 px(比 1.00)なのに、fx の誤差は 0.026〜7.334 %(281 倍)。歪みのあるカメラでは退化検出の門が発火せず、非線形最適化は正面配置でも答えを返す。*

[![RMS は 1.00 倍しか動かないのに fx 誤差は 281 倍動く。配置の良し悪しを映すのは sigma_fx のほう。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/01_reproj_vs_truth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/01_reproj_vs_truth.png)

*↑ 測定の図 ―― RMS は 1.00 倍しか動かないのに fx 誤差は 281 倍動く。配置の良し悪しを映すのは sigma_fx のほう。*

```
py -3.11 examples/poc_camera_calibration.py
```

ソース: [examples/poc_camera_calibration.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_camera_calibration.py)

使用 op(ノートへ): [`project_points`](https://furuse.work/ops/3d/render/project_points.html) · [`reprojection_error`](https://furuse.work/ops/3d/pose_estimation/reprojection_error.html)

## 61. 隣どうしを鎖でつなぐと、一周して元に戻れない

[![隣どうしを鎖でつなぐと、一周して元に戻れない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/01_seams_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/01_seams.png)

*↑ **隣どうしを鎖でつなぐと、一周して元に戻れない** ―― 既知の回転列で円筒パノラマから 36 枚を切り出し、隣接ペアの鎖で一周させた図。隣の継ぎ目は 0.12 px なのに閉じる 1 本だけ 1.5 px(13 倍)開く。埋もれていた `bundle_adjust_mosaic` は鎖を上回らず(30/36 枚が単位行列のまま)、姿勢の最悪誤差は鎖 1.65 → 大域最適化 0.56 px。*

[![系 2(等分)は閉ループ誤差を下げるのに姿勢はかえって悪化する。新しい観測を足さずに効くのは系 3。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/02_pose_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/02_pose_error.png)

*↑ 測定の図 ―― 系 2(等分)は閉ループ誤差を下げるのに姿勢はかえって悪化する。新しい観測を足さずに効くのは系 3。*

```
py -3.11 examples/poc_panorama_drift.py
```

ソース: [examples/poc_panorama_drift.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_panorama_drift.py)

使用 op(ノートへ): [`pose_error`](https://furuse.work/ops/3d/metrics/pose_error.html) · [`warp_by_plane`](https://furuse.work/ops/3d/plane_sweep_stereo/warp_by_plane.html)

## 62. 点群位置合わせの収束域 ―― 初期姿勢がどれだけずれたら壊れるか

[![点群位置合わせの収束域 ―― 初期姿勢がどれだけずれたら壊れるか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/01_basin_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/01_basin.png)

*↑ **点群位置合わせの収束域 ―― 初期姿勢がどれだけずれたら壊れるか** ―― 点群を毎試行取り直し、初期姿勢のずれに対する ICP の成功率を等高線にした図。並進ずれ 0 で成功率が 50 % を切るのは点対点 90 度、点対面 120 度。球や円柱は残差が同じまま姿勢が任意で、大域手法では 16/16 が見かけ上収束しつつ姿勢は誤り ―― 残差では検出できない。*

[![非対称性が消えると 4 候補が形として区別できず、選択が崩れる(選ばれた解が第 1 候補から離れる)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/02_pca_quadrant_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/02_pca_quadrant.png)

*↑ 測定の図 ―― 非対称性が消えると 4 候補が形として区別できず、選択が崩れる(選ばれた解が第 1 候補から離れる)。*

```
py -3.11 examples/poc_registration_basin.py
```

ソース: [examples/poc_registration_basin.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_registration_basin.py)

使用 op(ノートへ): [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`farthest_point_sampling`](https://furuse.work/ops/3d/geodesic/farthest_point_sampling.html) · [`rmse`](https://furuse.work/ops/imgmetrics/fidelity/rmse.html)

### 色・分離ウィング ―― 「効く手法」は無い、あるのは効く条件だけ

光源を推定して色を戻す、多波長で絵画の層を剥がす、偏光で鏡面反射を分離する。この部屋の 3 点は、既知の分光反射率・既知の光源・フレネルの式から線形の輻度を合成し、分離の結果を真値と突き合わせています。

結論は、どの展示でも「壊れる軸が直交している」ことでした。白パッチ法は白が在れば最良で、いちばん明るい 1 枚を外すだけで 8 倍悪くなる。灰色世界は飽和に強く、有彩色が 2 割を超えると負ける。基準光源では全手法がゼロ点に負ける。バンドを増やしても勝てず、近赤外を入れた瞬間に勝つ。

共通の注意は「リニアな輻度に戻してから渡す」こと。sRGB ガンマのまま渡しても例外は出ず、分離が静かに劣化するだけです。例外が出ない失敗は、この展示全体で最も多い型です。

## 63. 色恒常性(ホワイトバランス)―― 「効く手法」は無い、あるのは効く条件だけ

[![色恒常性(ホワイトバランス)―― 「効く手法」は無い、あるのは効く条件だけ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/01_casts_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/01_casts.png)

*↑ **色恒常性(ホワイトバランス)―― 「効く手法」は無い、あるのは効く条件だけ** ―― 24 枚の既知分光反射率と既知光源から線形 RGB を合成し、光源推定の回復角度誤差を測った図。白パッチ法は 11 光源の中央値 1.06 度で最良だが、いちばん明るい 1 枚を外すと 8.45 度、露出 3 倍で 43 % を飽和させると 13.61 度で「何もしない」と一致。真の光源で対角補正しても 2500 K では ΔE00 平均 5.07 が残る。*

[![灰色世界はゼロ点(何もしない)の線を 0.1〜0.2 の間で上抜けする = そこから先は回すだけ損。白パッチ法には崖が無い。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/02_bias_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/02_bias_cliff.png)

*↑ 測定の図 ―― 灰色世界はゼロ点(何もしない)の線を 0.1〜0.2 の間で上抜けする = そこから先は回すだけ損。白パッチ法には崖が無い。*

```
py -3.11 examples/poc_white_balance.py
```

ソース: [examples/poc_white_balance.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_white_balance.py)

使用 op(ノートへ): [`delta_e_map`](https://furuse.work/ops/imgmetrics/colordiff/delta_e_map.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`illuminant_from_dichromatic_planes`](https://furuse.work/ops/specular/dichromatic/illuminant_from_dichromatic_planes.html) · [`laplace`](https://furuse.work/ops/2d/edges/laplace.html) · [`linear_to_srgb`](https://furuse.work/ops/gfx2d/colorspace/linear_to_srgb.html) · [`mean_image`](https://furuse.work/ops/2d/smoothing/mean_image.html) · [`prewitt_amp`](https://furuse.work/ops/2d/edges/prewitt_amp.html) · [`roberts`](https://furuse.work/ops/2d/edges/roberts.html) · [`sobel_amp`](https://furuse.work/ops/2d/edges/sobel_amp.html) · [`spectrum_to_srgb`](https://furuse.work/ops/optics/appearance/spectrum_to_srgb.html)

## 64. 多波長で層を剥がす ―― 下絵・地塗り・上塗り・褪色を、真値を握ったまま分離する

[![多波長で層を剥がす ―― 下絵・地塗り・上塗り・褪色を、真値を握ったまま分離する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/01_per_field_auc_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/01_per_field_auc.png)

*↑ **多波長で層を剥がす ―― 下絵・地塗り・上塗り・褪色を、真値を握ったまま分離する** ―― 地塗り・下絵・上塗り・褪色を重ねた分光キューブを合成し、層を分離した図。可視だけを 16 バンドに割っても RGB と同じ(再現率 0.118 対 0.119)で、勝ったのは近赤外を入れたこと。同じ検出器が群青で AUC 1.000、アズライトで 0.630、剥落部で 0.013 ―― 平均すると全部消える。褪色前の色の復元は ΔE00 16.79 → 16.46 で、ゼロ点にほぼ勝てなかった。*

[![近赤外の差分は剥落部(楕円)で消え、近赤外 1 枚は面ごとに水準が違う。塗り分けは 1–99 分位でクリップした表示のみ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/02_detector_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/02_detector_maps.png)

*↑ 測定の図 ―― 近赤外の差分は剥落部(楕円)で消え、近赤外 1 枚は面ごとに水準が違う。塗り分けは 1–99 分位でクリップした表示のみ。*

```
py -3.11 examples/poc_pigment_unmixing.py
```

ソース: [examples/poc_pigment_unmixing.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pigment_unmixing.py)

使用 op(ノートへ): [`delta_e_map`](https://furuse.work/ops/imgmetrics/colordiff/delta_e_map.html) · [`linear_to_srgb`](https://furuse.work/ops/gfx2d/colorspace/linear_to_srgb.html) · [`spectrum_to_srgb`](https://furuse.work/ops/optics/appearance/spectrum_to_srgb.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html)

## 65. 偏光で鏡面反射を剥がす ―― フレネルの式で真値を作り、分離結果を突き合わせる

[![偏光で鏡面反射を剥がす ―― フレネルの式で真値を作り、分離結果を突き合わせる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/01_fresnel_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/01_fresnel.png)

*↑ **偏光で鏡面反射を剥がす ―― フレネルの式で真値を作り、分離結果を突き合わせる** ―― 拡散と鏡面を s/p 成分で合成し、フレネルの式から偏光度を出して分離結果を採点した図。偏光を使う手は入射角 20 度では 1.2 倍しか勝たない。拡散成分の誤差は閉形式 R_p·E に一致してブリュースター角 56.31 度で 0 ―― `polarization_separate` の拡散はその分だけ系統的に大きい。*

[![実測と閉形式が重なる。70 度の絶対誤差は 20 度より悪いのに、ゼロ点比では 70 度が最良 —— 最適角は評価軸で割れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/02_angle_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/02_angle_error.png)

*↑ 測定の図 ―― 実測と閉形式が重なる。70 度の絶対誤差は 20 度より悪いのに、ゼロ点比では 70 度が最良 —— 最適角は評価軸で割れる。*

```
py -3.11 examples/poc_polarization_specular.py
```

ソース: [examples/poc_polarization_specular.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_polarization_specular.py)

使用 op(ノートへ): [`fresnel_reflectance`](https://furuse.work/ops/3d/optics/fresnel_reflectance.html) · [`polarization_dolp_map`](https://furuse.work/ops/specular/polarization/polarization_dolp_map.html) · [`polarization_render`](https://furuse.work/ops/specular/polarization/polarization_render.html) · [`polarization_separate`](https://furuse.work/ops/specular/polarization/polarization_separate.html) · [`polarization_stokes`](https://furuse.work/ops/specular/polarization/polarization_stokes.html) · [`rmse`](https://furuse.work/ops/imgmetrics/fidelity/rmse.html)

### 法科学・文書ウィング ―― 1 枚の成功例は証拠にならない

改竄検出と書類の正対化。どちらも「見つかった 1 枚」「まっすぐになった 1 枚」で語られがちですが、この部屋の 2 点は、貼付の場所と品質、既知のホモグラフィと照明、を自分で決めた上で、画素ごとの ROC と画素単位の幾何誤差で採点しています。

改竄検出は検出側(防御)の PoC です。改竄を自分で作るのは検出器を測るのに真値が要るためだけで、作り方は最も稚拙なものに留めてあります。この展示がいちばん強く示すのは、保存ボタン 1 回でどの手掛かりも弱る、という検出側に不利な事実のほうです。

書類のほうは、名前が同じでモデルが違う関数を取り違えても例外が出ず、台形が残ったままもっともらしい絵が返る、という穴を数字にしています。影除去に良いところ取りは無く、平らにするほど薄い字が消えます。

## 66. 改竄検出を ROC で語る ―― 「見つかった 1 枚」ではなく、偽陽性を固定したときの検出率

[![改竄検出を ROC で語る ―― 「見つかった 1 枚」ではなく、偽陽性を固定したときの検出率](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/01_score_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/01_score_maps.png)

*↑ **改竄検出を ROC で語る ―― 「見つかった 1 枚」ではなく、偽陽性を固定したときの検出率** ―― JPEG q60 の素材を q92 の背景に貼って q95 で保存した改竄画像 10 枚を、画素ごとの ROC で採点した図。ELA の 1 つの数字は向きが教科書と逆(貼付部 / 背景 = 0.58 倍)で、改竄していない画像でも場所への偏りで AUC 0.797 が出る。ゴーストの谷の深さは AUC 0.997 だが、全体を q75 で再圧縮すると 0.975 へ落ちる。*

[![凡例の数字は AUC。乱数が対角線に乗ることで測り方に偏りが無いと言える。ゴーストA は乱数と重なる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/02_roc_tampered_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/02_roc_tampered.png)

*↑ 測定の図 ―― 凡例の数字は AUC。乱数が対角線に乗ることで測り方に偏りが無いと言える。ゴーストA は乱数と重なる。*

```
py -3.11 examples/poc_forensics_roc.py
```

ソース: [examples/poc_forensics_roc.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_forensics_roc.py)

使用 op(ノートへ): [`copy_move_regions`](https://furuse.work/ops/imgforensics/copy_move/copy_move_regions.html) · [`error_level_map`](https://furuse.work/ops/imgforensics/compression/error_level_map.html) · [`jpeg_ghost_map`](https://furuse.work/ops/imgforensics/compression/jpeg_ghost_map.html) · [`jpeg_ghost_quality`](https://furuse.work/ops/imgforensics/compression/jpeg_ghost_quality.html) · [`noise_inconsistency_map`](https://furuse.work/ops/imgforensics/noise/noise_inconsistency_map.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html)

## 67. 手持ちで撮った書類をまっすぐに戻す ―― 台形補正と影除去を、真値と突き合わせて測る

[![手持ちで撮った書類をまっすぐに戻す ―― 台形補正と影除去を、真値と突き合わせて測る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/01_rectify_zero_points_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/01_rectify_zero_points.png)

*↑ **手持ちで撮った書類をまっすぐに戻す ―― 台形補正と影除去を、真値と突き合わせて測る** ―― 既知のホモグラフィと照明で撮った書類を戻し、4 隅と格子の画素誤差で採点した図。推定は格子 RMS 1.070 px(何もしない 37.376 px)だが、名前が同じでモデルが違う関数(アフィン)を取り違えると 32 倍悪く、例外は出ない。影の強さ 0.45 で 4 隅 RMS 5.72 px、0.55 で 65.10 px と崖。*

[![平坦・薄字・誤検出なしを同時に満たす行は 1 つも無い。窓 9 が fs.op で届く上限、窓 61 は自前。図の階調は真値で 217 段。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/02_shadow_tradeoff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/02_shadow_tradeoff.png)

*↑ 測定の図 ―― 平坦・薄字・誤検出なしを同時に満たす行は 1 つも無い。窓 9 が fs.op で届く上限、窓 61 は自前。図の階調は真値で 217 段。*

```
py -3.11 examples/poc_document_scan.py
```

ソース: [examples/poc_document_scan.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_document_scan.py)

使用 op(ノートへ): [`corner_response`](https://furuse.work/ops/2d/edges/corner_response.html) · [`dc_homomorphic`](https://furuse.work/ops/2d/decomposition/dc_homomorphic.html) · [`fill_holes`](https://furuse.work/ops/2d/region/fill_holes.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`get_region_contour`](https://furuse.work/ops/2d/region/get_region_contour.html) · [`gray_tophat`](https://furuse.work/ops/2d/morphology/gray_tophat.html) · [`illuminate`](https://furuse.work/ops/2d/gray/illuminate.html) · [`mean_image`](https://furuse.work/ops/2d/smoothing/mean_image.html) · [`opening_circle`](https://furuse.work/ops/2d/region/opening_circle.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`project_points`](https://furuse.work/ops/3d/render/project_points.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`select_largest`](https://furuse.work/ops/2d/region/select_largest.html) · [`sobel_dir`](https://furuse.work/ops/2d/edges/sobel_dir.html) · [`var_threshold`](https://furuse.work/ops/2d/segmentation/var_threshold.html)

## 68. カメラ指紋(PRNU)で「どのカメラで撮ったか」を当てる ―― 指紋は枚数で育ち、保存ボタンで消える

[![カメラ指紋(PRNU)で「どのカメラで撮ったか」を当てる ―― 指紋は枚数で育ち、保存ボタンで消える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/01_estimators_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/01_estimators.png)

*↑ **カメラ指紋(PRNU)で「どのカメラで撮ったか」を当てる ―― 指紋は枚数で育ち、保存ボタンで消える** ―― 2 台の仮想カメラに固定の感度むら K を仕込み、30 枚の残差から指紋を推定して照合した。清浄条件では同一カメラの PCE 中央値 2192 に対し別カメラ 15.7(AUC 1.000)だが、JPEG 相当の量子化は品質 50 相当で PCE を 3.6 % に、0.5× 縮小は 1.5 % に落とす ―― 消したのは幾何ではなく残差抽出器だった。K=0 のカメラでも同じ背景を 30 枚写せば PCE 1706 の「指紋」ができる。被写体は指紋に化ける。*

[![別カメラのピークは毎回別の位置に立つ((0,0) は 0/30)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/02_match_pce_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/02_match_pce.png)

*↑ 測定の図 ―― 別カメラのピークは毎回別の位置に立つ((0,0) は 0/30)。*

```
py -3.11 examples/poc_prnu_camera_fingerprint.py
```

ソース: [examples/poc_prnu_camera_fingerprint.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_prnu_camera_fingerprint.py)

使用 op(ノートへ): [`aug_jpeg_blocks`](https://furuse.work/ops/2d/augmentation/aug_jpeg_blocks.html) · [`evidence_quantile`](https://furuse.work/ops/imgforensics/calibration/evidence_quantile.html) · [`fingerprint_correlate`](https://furuse.work/ops/imgforensics/sensor/fingerprint_correlate.html) · [`gauss_image`](https://furuse.work/ops/2d/smoothing/gauss_image.html) · [`median_image`](https://furuse.work/ops/2d/rank/median_image.html) · [`null_distribution`](https://furuse.work/ops/imgforensics/calibration/null_distribution.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`sensor_fingerprint`](https://furuse.work/ops/imgforensics/sensor/sensor_fingerprint.html) · [`sk_nlm`](https://furuse.work/ops/2d/smoothing/sk_nlm.html) · [`sk_tv`](https://furuse.work/ops/2d/smoothing/sk_tv.html) · [`sk_wavelet`](https://furuse.work/ops/2d/smoothing/sk_wavelet.html) · [`xsp_dct_denoise`](https://furuse.work/ops/2d/smoothing/xsp_dct_denoise.html) · [`xsp_wiener`](https://furuse.work/ops/2d/smoothing/xsp_wiener.html)

## 69. 絵画のひび割れ網 ―― 3 指標のうち撮影条件で壊れるのは分岐次数だけ

[![絵画のひび割れ網 ―― 3 指標のうち撮影条件で壊れるのは分岐次数だけ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/07_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/07_scene.png)

*↑ **絵画のひび割れ網 ―― 3 指標のうち撮影条件で壊れるのは分岐次数だけ** ―― ボロノイ網を閉形式で描き、乾燥ひび(セル小・蛇行)と経年ひび(セル大・格子的)の 2 種に色斑・光沢むら・斜光・ぼけ・雑音を足して、リッジ op → 骨格 → 分岐点の op 列で網を測った。真値でセル径 18.0 vs 45.2 px、直線度 0.960 vs 1.000、次数 4 割合 0.20 vs 0.83 と 3 指標とも 2 種を分けるが、経年型の次数 4 割合は質感で 0.87 → 0.64、斜光で 0.70 と乾燥側へ動き、セル径と直線度は動かない。予想した崖は 2 つとも来なかった: 幅 0.15 px でも再現率 0.696、質感 c = 0.64 でも偽陽性 0.382。斜光は幅を +0.37 px 片側に太らせ、中心線を光源側へ 0.75 px 寄せる。*

[![Frangi は分岐点で応答が落ち、斜光でセルが崩れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/01_ridge_ops_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fresco_craquelure/01_ridge_ops.png)

*↑ 測定の図 ―― Frangi は分岐点で応答が落ち、斜光でセルが崩れる。*

```
py -3.11 examples/poc_fresco_craquelure.py
```

ソース: [examples/poc_fresco_craquelure.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_fresco_craquelure.py)

使用 op(ノートへ): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`cv_blackhat`](https://furuse.work/ops/2d/morphology/cv_blackhat.html) · [`distance_transform`](https://furuse.work/ops/2d/region/distance_transform.html) · [`hx_split_skeleton_region`](https://furuse.work/ops/2d/halcon_ext/hx_split_skeleton_region.html) · [`hysteresis_threshold`](https://furuse.work/ops/2d/segmentation/hysteresis_threshold.html) · [`junctions_skeleton`](https://furuse.work/ops/2d/region/junctions_skeleton.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`pruning`](https://furuse.work/ops/2d/region/pruning.html) · [`r2_endpoints_skeleton`](https://furuse.work/ops/2d/region/r2_endpoints_skeleton.html) · [`sk_area_opening`](https://furuse.work/ops/2d/morphology/sk_area_opening.html) · [`sk_frangi`](https://furuse.work/ops/2d/texture/sk_frangi.html) · [`sk_otsu`](https://furuse.work/ops/2d/segmentation/sk_otsu.html) · [`skeleton`](https://furuse.work/ops/2d/region/skeleton.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html) · [`xsk_meijering`](https://furuse.work/ops/2d/texture/xsk_meijering.html) · [`xsk_sato`](https://furuse.work/ops/2d/texture/xsk_sato.html)

### 3-D 形状ウィング ―― 合わせてから測ると、合わせた分だけ欠陥が消える

点群とメッシュの仕事は、2-D の仕事と 1 つだけ決定的に違います。**測る前に姿勢を合わせる**という段が入ることです。合わせる段は、測りたいずれを最小にする向きに形を回します。だから欠陥が大きいほど、合わせの段が欠陥を吸い、残差は小さく、部品は良品に見えます。この部屋の展示は、その吸われた分を数える試みです。

真値はすべて式で置いてあります。立体は解析的な面のブール演算で作り、体積・表面積・肉厚・曲率が式で分かるものを選びます。変形は既知の場(局所のへこみ、反り、法線方向の一定の摩耗)、姿勢は既知の回転と並進、点群は面からの一様サンプルに既知の密度・雑音・欠測を掛けたものです。だから「合わせの誤差」と「形の誤差」を別々に持てます。

3-D 特有の落とし穴も、この部屋では別々に数えます。最近傍距離は雑音があると必ず正へ偏る(片側だけ数える量だから)、法線の符号は下請けの都合で決まる、密度を変えると距離の尺度そのものが動く、対称な形は姿勢が一意に決まらない。どれも 1 つの数字に畳んだ瞬間に見えなくなります。

## 70. 壊れたメッシュを直してから測る ―― 消えるのは欠陥の数で、戻るのは量ではない

[![壊れたメッシュを直してから測る ―― 消えるのは欠陥の数で、戻るのは量ではない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/01_scene.png)

*↑ **壊れたメッシュを直してから測る ―― 消えるのは欠陥の数で、戻るのは量ではない** ―― 球とトーラスと角柱のブール和から閉じた三角メッシュを作り、穴・裏返った面・非多様体辺・退化三角形・重複頂点・自己交差を種類ごとに既知個数だけ仕込んで、位相の数字と体積・表面積の両方で追いました。オイラー標数は 6 種のうち 5 種にまったく反応せず、穴 6 個と重複面 6 枚を同時に入れると頂点・辺・面・χ が健全な部品と 1 つも違わなくなります。直したあとも量は戻らず、半頂角 45° の穴を塞いだ球は表面積が予測 -2.145 % に対して実測 +6.868 %(縁が円ではなく階段だから)、頂点を 6 個だけ突き刺したメッシュは位相の検査を 3 つとも通り抜けたまま表面積 +4.414 % / 体積 -0.332 % と 13 倍食い違いました。*

[![健全な部品の χ は 0(種数 1)。χ=2 を合格条件にすると健全品が落ちる。最終行は打ち消し。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/02_euler_blindspots_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/02_euler_blindspots.png)

*↑ 測定の図 ―― 健全な部品の χ は 0(種数 1)。χ=2 を合格条件にすると健全品が落ちる。最終行は打ち消し。*

```
py -3.11 examples/poc_mesh_quality_repair.py
```

ソース: [examples/poc_mesh_quality_repair.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_mesh_quality_repair.py)

使用 op(ノートへ): [`decimate_qem`](https://furuse.work/ops/3d/mesh_process/decimate_qem.html) · [`face_normals`](https://furuse.work/ops/3d/mesh_process/face_normals.html) · [`fill_holes`](https://furuse.work/ops/2d/region/fill_holes.html) · [`inertia_tensor`](https://furuse.work/ops/3d/moment_invariant/inertia_tensor.html) · [`mesh_area`](https://furuse.work/ops/3d/mesh_process/mesh_area.html) · [`mesh_edge_lengths`](https://furuse.work/ops/3d/terrain/mesh_edge_lengths.html) · [`mesh_edge_stats`](https://furuse.work/ops/3d/resolution/mesh_edge_stats.html) · [`sdf_subtract`](https://furuse.work/ops/3d/sdf_csg/sdf_subtract.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`vertex_curvature`](https://furuse.work/ops/3d/mesh_process/vertex_curvature.html) · [`vertex_normals`](https://furuse.work/ops/3d/mesh_process/vertex_normals.html) · [`voxel_to_mesh`](https://furuse.work/ops/3d/transform/voxel_to_mesh.html)

## 71. 斜面の土量 ―― 合わせてから引くと、崩れが浅くなる

[![斜面の土量 ―― 合わせてから引くと、崩れが浅くなる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/09_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/09_scene.png)

*↑ **斜面の土量 ―― 合わせてから引くと、崩れが浅くなる** ―― 傾斜のある合成地形に既知体積の掘削と堆積を仕込み、2 時期の航空点群から鉛直差分と法線方向の差で土量を測った。予想した「斜面では cos だけ体積が縮む」は外れで、水平投影面積で積む限り cos は約分し、掘削体積の誤差は傾斜 0〜40 度でどれも -0.011 % のまま動かない。壊れたのは合わせ方のほうで、変化域が視野の 33 % もあると位置合わせが変化そのものを吸い、正味土量は真値 -30.4 m3 に対し -3.8 m3 まで潰れた ―― 変化なしの対照ですら偽の掘削が 83.8 m3 出る。*

[![傾斜を 0 から 40 度まで振っても体積の誤差に傾向が無い。cos は積分で約分する。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/01_geometry_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/01_geometry.png)

*↑ 測定の図 ―― 傾斜を 0 から 40 度まで振っても体積の誤差に傾向が無い。cos は積分で約分する。*

```
py -3.11 examples/poc_lidar_terrain_change.py
```

ソース: [examples/poc_lidar_terrain_change.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_lidar_terrain_change.py)

使用 op(ノートへ): [`chamfer_distance`](https://furuse.work/ops/3d/metrics/chamfer_distance.html) · [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`estimate_oriented_normals`](https://furuse.work/ops/3d/normals_orient/estimate_oriented_normals.html) · [`fit_plane_3d`](https://furuse.work/ops/3d/geometry/fit_plane_3d.html) · [`icp_point2point_3d`](https://furuse.work/ops/3d/refine/icp_point2point_3d.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`ransac_plane`](https://furuse.work/ops/3d/robust_fit/ransac_plane.html) · [`voxel_grid_downsample`](https://furuse.work/ops/3d/preprocess/voxel_grid_downsample.html)

## 72. CAD と実測点群の差分検査 ―― 合わせた分だけ欠陥が消え、無い所にへこみが出る

[![CAD と実測点群の差分検査 ―― 合わせた分だけ欠陥が消え、無い所にへこみが出る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/01_scene.png)

*↑ **CAD と実測点群の差分検査 ―― 合わせた分だけ欠陥が消え、無い所にへこみが出る** ―― 解析形状の機械部品に、局所へこみ・反り・摩耗を法線方向の既知量として仕込み、既知の姿勢・雑音・欠測つきの実測点群を合成した。合わせてから符号付き偏差と公差外面積を測ると、局所へこみの読みは 3.7 % しか薄まらないのに、真値が 1.2 µm しかない部品中央に深さ 121 µm の存在しないへこみが出る(閉形式の予測 -120 µm)。消えるか化けるかは剛体 6 自由度が吸える偏差場に似ているかどうかで決まり、稜線では最近傍が隣の面へ飛んで、欠陥ゼロの対照でも 66.5 mm^2 の偽の公差外領域が出た。*

[![真の姿勢を与えた最終行が推定器そのものの床。点-面 ICP との差は姿勢ではなく datum の取り方の差。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/02_methods_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/02_methods.png)

*↑ 測定の図 ―― 真の姿勢を与えた最終行が推定器そのものの床。点-面 ICP との差は姿勢ではなく datum の取り方の差。*

```
py -3.11 examples/poc_cad_scan_deviation.py
```

ソース: [examples/poc_cad_scan_deviation.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_cad_scan_deviation.py)

使用 op(ノートへ): [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`chamfer_distance`](https://furuse.work/ops/3d/metrics/chamfer_distance.html) · [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`estimate_oriented_normals`](https://furuse.work/ops/3d/normals_orient/estimate_oriented_normals.html) · [`gicp`](https://furuse.work/ops/3d/gicp/gicp.html) · [`hausdorff_distance`](https://furuse.work/ops/3d/metrics/hausdorff_distance.html) · [`icp_point2plane`](https://furuse.work/ops/3d/refine/icp_point2plane.html) · [`icp_point2point_3d`](https://furuse.work/ops/3d/refine/icp_point2point_3d.html) · [`query_distance`](https://furuse.work/ops/3d/occupancy/query_distance.html) · [`register_fpfh`](https://furuse.work/ops/3d/feature_register/register_fpfh.html) · [`sphere_sdf`](https://furuse.work/ops/3d/sdf_csg/sphere_sdf.html) · [`voxel_grid_downsample`](https://furuse.work/ops/3d/preprocess/voxel_grid_downsample.html)

## 73. 造形しやすさを形から測る —— しきい値に貼りついた面は、丸めた分だけ判定が飛ぶ

[![造形しやすさを形から測る —— しきい値に貼りついた面は、丸めた分だけ判定が飛ぶ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/01_scene.png)

*↑ **造形しやすさを形から測る —— しきい値に貼りついた面は、丸めた分だけ判定が飛ぶ** ―― 設計値の分かる合成部品(薄壁・スロット・45 度前後の補強・穴)をボクセル化し、肉厚・要サポート面積・工具の入る隙間を測りました。しきい値 45 度の両側で必要面積は 185.22 → 576.10 mm^2 と 0.2 度で 3.11 倍に跳ね、その段差は等値面を距離場から取ると 100 %、平滑化でも 12 % 消えます。肉厚は 2 voxel 刻みに潰れ(内接球にしても同じ)、隙間の誤判定は両方向に出て、粗さ 0.500 mm では隙間が 2.000 mm に太り入らない工具を通します。*

[![上: 左端の 2 本が薄壁(1.500 mm)とそのあいだのスロット(1.500 mm)、右の三角が補強。下: リブと薄壁の footprint。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/02_sections_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/02_sections.png)

*↑ 測定の図 ―― 上: 左端の 2 本が薄壁(1.500 mm)とそのあいだのスロット(1.500 mm)、右の三角が補強。下: リブと薄壁の footprint。*

```
py -3.11 examples/poc_dfm_thickness_overhang.py
```

ソース: [examples/poc_dfm_thickness_overhang.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dfm_thickness_overhang.py)

使用 op(ノートへ): [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`face_normals`](https://furuse.work/ops/3d/mesh_process/face_normals.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`morph_erode3d`](https://furuse.work/ops/3d/morphology/morph_erode3d.html) · [`render_shaded`](https://furuse.work/ops/3d/render/render_shaded.html) · [`sdf_intersect`](https://furuse.work/ops/3d/sdf_csg/sdf_intersect.html) · [`sdf_subtract`](https://furuse.work/ops/3d/sdf_csg/sdf_subtract.html) · [`sdf_to_occupancy`](https://furuse.work/ops/3d/transform/sdf_to_occupancy.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`vol_wall_thickness`](https://furuse.work/ops/3d/probe/vol_wall_thickness.html) · [`voxel_to_mesh`](https://furuse.work/ops/3d/transform/voxel_to_mesh.html)

