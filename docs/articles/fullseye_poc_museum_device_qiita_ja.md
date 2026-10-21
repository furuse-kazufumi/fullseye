> **言語 / Language**: **日本語** · [English](https://github.com/furuse-kazufumi/fullseye/blob/master/docs/articles/fullseye_poc_museum_device_qiita_en.md)

# 紙面の計測館 —— 装置の棟(センサーと計測器を物理から再現する)

> **[紙面の計測館 総合案内](https://qiita.com/furuse-kazufumi/items/c1606bcfa2085d204ad6)** の一棟です。ほかの棟・用語・テーゼは案内にあります。

この棟には **14 点**を掛けています。番号は**収蔵番号**で、棟を移しても分けても変わりません。

> 各展示の「使用 op」から、その op のノート(型契約・罠・図・Studio で走るプログラム)へ飛べます: [オペレータ目録](https://furuse.work/OP_CATALOG.html) / [op ノートの索引](https://furuse.work/ops/INDEX.html)。

### 装置の棟 ―― 生の出力から、装置固有の壊れ方まで再現する

計測装置を名前だけ借り、都合のよい画像を出すのは簡単です。この部屋の 14 点は逆に、光子・電子・干渉・熱拡散・走査・光線追跡から装置の生出力を作り、そこから普段の測定値までを一続きにしています。

同じ距離でも iToF と dToF では多重反射と pile-up の現れ方が違い、同じ粒子でも SEM と TEM では直径が違って読めます。TDI は段数を増やせば暗い欠陥が見える一方、同期ずれを段数ぶん積み重ねます。装置名が同じでも、物理を省いた模型では壊れる場所を再現できません。

各展示は閉形式、公開実測値、独立実装のいずれかを門にしています。狙いは実機の完全な代用品を名乗ることではなく、どの物理を入れ、何をまだ入れていないかを明示したうえで、測定値がいつ信用できなくなるかを実機に触れる前に確かめることです。

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



## No.2026.178 —— カメラを買わずにカメラを測る ―― EMVA 1288 の手順で、既知の値を仕込んだセンサから量子効率・ゲイン・暗雑音を取り戻す

[![カメラを買わずにカメラを測る ―― EMVA 1288 の手順で、既知の値を仕込んだセンサから量子効率・ゲイン・暗雑音を取り戻す](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/01_photon_transfer.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/01_photon_transfer.gif)

*↑ **カメラを買わずにカメラを測る ―― EMVA 1288 の手順で、既知の値を仕込んだセンサから量子効率・ゲイン・暗雑音を取り戻す** ―― カメラのデータシートにある量子効率 η・システムゲイン K・暗雑音 σ_d・飽和・SNR・ダイナミックレンジ・DSNU・PRNU は、EMVA 1288 Release 4.0 Linear の手順で出した数である。この展示は**物理モデルでセンサを合成**し(光子のポアソン → 電子 → 暗雑音・暗電流 → K 倍 → 量子化・飽和、列・行・画素の DSNU と PRNU の模様つき)、新しい op 族 sensorchar(10 op)の**規格の推定手順**で仕込んだ値を取り戻す。合成と推定は別の式。門: 復元 —— 同じ露光で 2 枚ずつ撮った平均と時間分散(式 16・18)の photon transfer(式 50)から K -0.66 %、暗画像から σ_d +0.13 %(式 53)、応答の傾きから η +0.67 %(式 52)、暗電流 +0.6 %、列・行・画素の空間分散(式 42)と DSNU +0.6 %・PRNU -0.1 % / 恒等式 —— SNR(μ_p.min) = 1(式 26 と 21 は独立)・理想センサ = √μ_p(式 23)を機械精度、傾き 1 → 1/2(式 22)/ 適用範囲 —— 暗画像の分散が 0.24 DN² 未満では σ_d を推定しない(式 53・54)が、平らなセンサでは本当に推定の壊れる境界 / 公表値 —— メーカーが公表した EMVA 1288 データ 38 型番で最大 SNR = √μ_e.sat(式 55)が全型番 0.49 dB 以内 / 直線性 —— 直線性の誤差(式 58〜63)の閉形式が独立の重みつき最小二乗と 3.9e-13 / 欠陥画素 —— 仕込んだ 9 個を数え直す。見つけたこと: σ_d を photon transfer の**切片**から出すと +53.5 %(規格は暗画像から直接)。DSNU の模様があると画素ごとの暗レベルのずれが量子化のディザになり、規格が「推定できない」とする K = 0.10 でも 0.7 %(平ら 29.8 %)—— 規格の境界は保守側。台帳の 8 番目は飽和 21.0 ke⁻・暗雑音 7 e⁻ からは DR 68.9 dB なのに台帳は 74 dB —— どちらかの欄が別条件の値と見られる(未確認、台帳は直さず門で名指し)。★★規格の残りの式(2026-10-13): 規格 5 節の模擬カメラ(640 × 480、DSNU に振幅 1.5 DN の正弦 2 本、照明が端へ 3 % 落ちる)で、8.1 節の高域フィルタをかけないと PRNU は 0.831 %(仕込み 0.5 %、+66 %)、かけると 0.497 %(白い利得 0.9885 の分だけ低い)。DSNU は波長 25 画素の正弦が 38 % に減るぶん 21.25 → 18.83 e⁻ で、伝達関数からの予測と一致。8.6 節のスペクトログラムの式 72 で正弦の振幅 1.46 / 1.50 DN を取り戻す。付録 C.5 の式 86 が書く 0.92 は実測 0.960(Parseval 1 − 1/25)と合わない。★式 51(photon transfer の直線性、局所の傾きの相対偏差の平均 < 3 %)は画素数が要る: 線形なセンサでも 128 × 160 では 6 回中 1 回落ち、512 × 640 では落ちない。正直に: 合成センサ、1〜7 節の照明は一様、公表値は整数に丸めた値で K が無いので DR の検算は量子化雑音を 0 とみなす。前処理が数をどう動かすかは続編 poc_emva1288_in_camera_processing。14 門、約 4 秒。*

[![SNR は暗い側で傾き 1(暗雑音が支配)、明るい側で傾き 1/2(光子雑音が支配)。SNR = 1 になる露光が絶対感度しきい値 μ_p.min = 6.8 光子。量子化雑音の分だけ μ_e.min = 4.20 e⁻ は暗雑音 3.4 ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/02_snr_curve_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/02_snr_curve.png)

*↑ 測定の図 ―― SNR は暗い側で傾き 1(暗雑音が支配)、明るい側で傾き 1/2(光子雑音が支配)。SNR = 1 になる露光が絶対感度しきい値 μ_p.min = 6.8 光子。量子化雑音の分だけ μ_e.min = 4.20 e⁻ は暗雑音 3.4 e⁻ より大きい。*

[![暗画像の分散が 0.24 DN² より小さいと、規格は σ_d を推定しない(式 53・54)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/03_validity_boundary_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/03_validity_boundary.png)

*↑ 暗画像の分散が 0.24 DN² より小さいと、規格は σ_d を推定しない(式 53・54)。*

[![メーカーが公表した EMVA 1288 データ 38 型番の飽和容量・暗雑音・量子効率から式 (28) で DR を出し直す。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/04_datasheet_dynamic_range_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/04_datasheet_dynamic_range.png)

*↑ メーカーが公表した EMVA 1288 データ 38 型番の飽和容量・暗雑音・量子効率から式 (28) で DR を出し直す。*

[![白い DSNU は平らな床(高さ = 標準偏差 1.5 DN)、正弦は鋭い山(横 0.04・縦 0.2 c/px)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/06_spectrogram_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/06_spectrogram.png)

*↑ 白い DSNU は平らな床(高さ = 標準偏差 1.5 DN)、正弦は鋭い山(横 0.04・縦 0.2 c/px)。*

[![Release 4.0 のフィルタは高域でほぼ 1(付録 E.3)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/07_highpass_transfer_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_emva1288_sensor/07_highpass_transfer.png)

*↑ Release 4.0 のフィルタは高域でほぼ 1(付録 E.3)。*

```
py -3.11 examples/poc_emva1288_sensor.py
```

ソース: [examples/poc_emva1288_sensor.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_emva1288_sensor.py)

この回が作った図は全部で **8 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_emva1288_sensor)

使用 op(ノートへ): [`emva_dark_current`](https://furuse.work/ops/optics/sensorchar/emva_dark_current.html) · [`emva_defect_pixels`](https://furuse.work/ops/optics/sensorchar/emva_defect_pixels.html) · [`emva_dynamic_range`](https://furuse.work/ops/optics/sensorchar/emva_dynamic_range.html) · [`emva_exposure_for_snr`](https://furuse.work/ops/optics/sensorchar/emva_exposure_for_snr.html) · [`emva_highpass`](https://furuse.work/ops/optics/sensorchar/emva_highpass.html) · [`emva_linearity_error`](https://furuse.work/ops/optics/sensorchar/emva_linearity_error.html) · [`emva_pair_statistics`](https://furuse.work/ops/optics/sensorchar/emva_pair_statistics.html) · [`emva_photon_exposure`](https://furuse.work/ops/optics/sensorchar/emva_photon_exposure.html) · [`emva_photon_transfer`](https://furuse.work/ops/optics/sensorchar/emva_photon_transfer.html) · [`emva_ptc_linearity_check`](https://furuse.work/ops/optics/sensorchar/emva_ptc_linearity_check.html) · [`emva_quantum_efficiency`](https://furuse.work/ops/optics/sensorchar/emva_quantum_efficiency.html) · [`emva_sensitivity_threshold`](https://furuse.work/ops/optics/sensorchar/emva_sensitivity_threshold.html) · [`emva_snr_curve`](https://furuse.work/ops/optics/sensorchar/emva_snr_curve.html) · [`emva_spatial_nonuniformity`](https://furuse.work/ops/optics/sensorchar/emva_spatial_nonuniformity.html) · [`emva_spectrogram`](https://furuse.work/ops/optics/sensorchar/emva_spectrogram.html) · [`emva_total_snr`](https://furuse.work/ops/optics/sensorchar/emva_total_snr.html) · [`spectrogram`](https://furuse.work/ops/oned/signal/spectrogram.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html)

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

## No.2026.234 —— 写真では見えない µm の凹みを、画面に映した縞の鏡像で見つける ―― 位相計測デフレクトメトリ

[![写真では見えない µm の凹みを、画面に映した縞の鏡像で見つける ―― 位相計測デフレクトメトリ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/03_photo_vs_pmd_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/03_photo_vs_pmd.png)

*↑ **写真では見えない µm の凹みを、画面に映した縞の鏡像で見つける ―― 位相計測デフレクトメトリ** ―― 光沢面(車の塗装パネル、カバーガラス)の深さ数 µm の凹みは、照明を当てた写真ではまず見えない —— 鏡は照明しか写さない。面の前の画面に位相シフト縞を出し、その鏡像を撮ると、面が 1e-3 rad 傾くだけで 30 cm 先の画面では 0.6 mm ずれる。新 op 6 本(`deflectometry`、`opsspecular` の `deflectometry`): `deflectometry_rig` / `deflectometry_screen_pattern` / `deflectometry_render`(高さ場 → 縞の鏡像。拡散成分、散乱、ガラスの裏面反射、開口積分のピント、雑音)/ `deflectometry_phase_to_slope`(絶対位相 → 法線、`match3d.normal_from_reflection`)/ `slope_to_curvature`(積分せず 1 回微分)/ `deflectometry_sensitivity`(撮る前の閉形式)。深さ 3 µm と 1 µm の凹み・うねり 0.8 µm・研磨ムラ 0.12 µm を仕込んだ塗装パネルで、ソフトボックスの写真の欠陥の信号は最大 0.00066(8 bit の 1 段の 0.17 倍)なのに、曲率マップの SNR は 110 と 57。勾配を積分した凹みの深さは真値と 0.5 % 以内。位相の雑音は閉形式 √(2/N)·σ/b と 1.00 倍、面の傾きの雑音は σ_u/(2d) の 0.67 倍(双線形の読み直しの √(4/9) どおり)。壊れるところ: 部品を 0.3 mm 浮かせると見かけの傾き Δz·sin θ/d(0.1 % で一致)と半径 388 m の椀が出るが凹みの深さは 0.7 % しか変わらない / 画面の距離を 2 % 間違えると深さが 2.3 % 浅い / 拡散成分 0.85 までは 1 µm の凹みが見え、0.9 で粗い縞の次数が飛び始める / 無反射コートの無いカバーガラスでは裏面の光が凹みの斜面(くさび)で逆向きに曲がり、傾きの感度が閉形式 0.246 に縮んで凹みが 1/4 の深さに見える(実測 0.246)/ 開口 8 mm では面にピントで縞の振幅が 0.60 倍、画面にピントで凹みが 0.52 倍の深さ。学習 0、較正 0、門 22 件。*

[![面の前の画面(520 × 320 mm)にこの 4 枚を順に出し、面に映った鏡像を撮る。縦縞は画面の u(入射面内)を、同じ 4 枚を横縞にしたものが v を符号化する。粗い縞(周期 160 mm)の 4 枚で次数を決める。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/01_screen_patterns_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/01_screen_patterns.png)

*↑ 測定の図 ―― 面の前の画面(520 × 320 mm)にこの 4 枚を順に出し、面に映った鏡像を撮る。縦縞は画面の u(入射面内)を、同じ 4 枚を横縞にしたものが v を符号化する。粗い縞(周期 160 mm)の 4 枚で次数を決める。*

[![左が真値の高さ(視野 40 mm、青 = 高い・橙 = 低い)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/02_sample_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/02_sample.png)

*↑ 左が真値の高さ(視野 40 mm、青 = 高い・橙 = 低い)。*

[![真値(破線)と復元(実線)はほぼ重なるので、差を 10 倍にして点線で重ねた。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/05_dimple_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/05_dimple_profile.png)

*↑ 真値(破線)と復元(実線)はほぼ重なるので、差を 10 倍にして点線で重ねた。*

[![平らな板を 0.3 mm 浮かせただけで、測った高さは 40 mm で約 14 µm 傾く(左、視野の中心で 3.4e-4 rad)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/08_ambiguity_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/08_ambiguity_map.png)

*↑ 平らな板を 0.3 mm 浮かせただけで、測った高さは 40 mm で約 14 µm 傾く(左、視野の中心で 3.4e-4 rad)。*

[![表と裏の反射率はほぼ同じ(R1 0.043、R2 0.039)なので、2 つの縞の和の位相は上限 1.16 rad までずれ得る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/12_glass_back_reflection_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/12_glass_back_reflection.png)

*↑ 表と裏の反射率はほぼ同じ(R1 0.043、R2 0.039)なので、2 つの縞の和の位相は上限 1.16 rad までずれ得る。*

[![拡散成分 k_d = 0, 0.5, 0.8, 0.85, 0.9, 0.95, 0.98, 0.99, 0.995 と上げていったときの平均曲率(±2.5e-3 /mm)。雑音が 1/(1 − k_d) で増え、浅い凹み B が先に沈み、](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/09_diffuse_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry/09_diffuse_sweep.gif)

*↑ 動く図 ―― 拡散成分 k_d = 0, 0.5, 0.8, 0.85, 0.9, 0.95, 0.98, 0.99, 0.995 と上げていったときの平均曲率(±2.5e-3 /mm)。雑音が 1/(1 − k_d) で増え、浅い凹み B が先に沈み、最後は粗い縞の次数が飛ぶ。*

```
py -3.11 examples/poc_phase_measuring_deflectometry.py
```

ソース: [examples/poc_phase_measuring_deflectometry.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_phase_measuring_deflectometry.py)

この回が作った図は全部で **14 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_phase_measuring_deflectometry)

使用 op(ノートへ): [`absolute_phase`](https://furuse.work/ops/3d/structured_light/absolute_phase.html) · [`deflectometry_phase_to_slope`](https://furuse.work/ops/specular/deflectometry/deflectometry_phase_to_slope.html) · [`deflectometry_render`](https://furuse.work/ops/specular/deflectometry/deflectometry_render.html) · [`deflectometry_rig`](https://furuse.work/ops/specular/deflectometry/deflectometry_rig.html) · [`deflectometry_screen_pattern`](https://furuse.work/ops/specular/deflectometry/deflectometry_screen_pattern.html) · [`deflectometry_sensitivity`](https://furuse.work/ops/specular/deflectometry/deflectometry_sensitivity.html) · [`fresnel_dielectric`](https://furuse.work/ops/optics/interface/fresnel_dielectric.html) · [`integrate`](https://furuse.work/ops/3d/tsdf_fusion/integrate.html) · [`sfp_height`](https://furuse.work/ops/optics/shape_from_polarization/sfp_height.html) · [`slope_to_curvature`](https://furuse.work/ops/specular/deflectometry/slope_to_curvature.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`wrapped_phase`](https://furuse.work/ops/3d/structured_light/wrapped_phase.html)

## No.2026.235 —— TDI ラインスキャンとラインスキャン用レンズ ―― 段数で欠陥が見え、同期がずれると流れ、C マウントでは長いセンサの端が消える

[![TDI ラインスキャンとラインスキャン用レンズ ―― 段数で欠陥が見え、同期がずれると流れ、C マウントでは長いセンサの端が消える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tdi_linescan/01_tdi_stages_defects_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tdi_linescan/01_tdi_stages_defects.png)

*↑ **TDI ラインスキャンとラインスキャン用レンズ ―― 段数で欠陥が見え、同期がずれると流れ、C マウントでは長いセンサの端が消える** ―― フィルム・鋼板・ウェハのように流れてくるものはラインセンサで撮り、暗いラインでは TDI で N 段ぶん露光を積む。新 op 6 本(`linescan`、`opsoptics` の `linescan`): `tdi_snr`(EMVA 1288 の式 21 を段数倍、電荷加算 / デジタル加算)/ `tdi_sync_mtf`(同期ずれ・ヨーの閉形式)/ `linescan_acquire`(反射率の地図を搬送して撮る: 速度誤差・ヨー・蛇行・エンコーダ同期・レンズ・雑音)/ `lens_field_profile`(像高ごとの照度と MTF を光線追跡で)/ `linescan_lens_columns` / `linescan_lens_example`。★1 段 40 光子の暗い冷延鋼板で、2 枚撮りの時間雑音から測った SNR は式 21 と全段数で 1.2 % 以内。デジタル加算は 64 段で ×8.09(√64 = 8)、電荷加算は読み出し雑音を 1 回しか払わないので ×26.9。薄い傷・ピンホール・異物の検出は 1 段 0 / 3 → 64 段 3 / 3(誤検出 0)。★同期ずれ ε で像が N·ε 画素流れ、流れ方向の MTF は |sinc(f N ε)| —— 閉形式を先に印字し、正弦波の板で 45 条件の最大差 0.0035。速度のうねり ±3 % は自走で局所 MTF 0.64 まで落ち、エンコーダ同期で 1.000 に戻る。ヨーの幅方向のぼけ |sinc(f N sin θ)| はエンコーダでは直らない(9 条件で最大差 0.0017)。★同じ形の三枚玉を 57 mm の像円用(f 90)と 2/3 型用(f 35、C マウントの流用)に作って光線追跡: 照度は cos⁴ × 瞳 × 歪曲に厳密に分かれ(最大差 2e-16)、ラインスキャン用は端で 0.976(cos⁴ は 0.855、樽型歪曲 −2.9 % が ×1.111)、C マウントは像高 19.7 mm から光が届かない。フラットフィールド補正で照度の幅は 0.961 → 1.000 に揃うが、正弦波の変調は補正の前後で差 0.0006(MTF は直らない)、像高 14 mm の異物の CNR は C マウントで 1.52 → 1.54 のまま(ラインスキャン用 2.49)。学習 0、較正 0、門 19 件。*

[![EMVA 1288 の 2 枚撮り(時間雑音)で測った SNR と、式 21 を段数倍した閉形式。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tdi_linescan/02_snr_vs_stages_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tdi_linescan/02_snr_vs_stages.png)

*↑ 測定の図 ―― EMVA 1288 の 2 枚撮り(時間雑音)で測った SNR と、式 21 を段数倍した閉形式。*

[![ε は搬送速度とラインレートの相対誤差。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tdi_linescan/03_sync_error_mtf_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tdi_linescan/03_sync_error_mtf.png)

*↑ ε は搬送速度とラインレートの相対誤差。*

[![web が走査軸から θ 傾くと、64 段の間に幅方向へ 64·sin θ 画素ずれる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tdi_linescan/05_yaw_cross_mtf_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tdi_linescan/05_yaw_cross_mtf.png)

*↑ web が走査軸から θ 傾くと、64 段の間に幅方向へ 64·sin θ 画素ずれる。*

[![光線追跡(射影立体角の一様格子)で数えた照度。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tdi_linescan/07_lens_relative_illumination_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tdi_linescan/07_lens_relative_illumination.png)

*↑ 光線追跡(射影立体角の一様格子)で数えた照度。*

[![同じ明るさの尺度で表示。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tdi_linescan/09_full_width_shading_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tdi_linescan/09_full_width_shading.png)

*↑ 同じ明るさの尺度で表示。*

```
py -3.11 examples/poc_tdi_linescan.py
```

ソース: [examples/poc_tdi_linescan.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_tdi_linescan.py)

この回が作った図は全部で **10 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_tdi_linescan)

使用 op(ノートへ): [`emva_pair_statistics`](https://furuse.work/ops/optics/sensorchar/emva_pair_statistics.html) · [`lens_field_profile`](https://furuse.work/ops/optics/linescan/lens_field_profile.html) · [`lens_shading_correct`](https://furuse.work/ops/gfx2d/isp/lens_shading_correct.html) · [`lens_shading_gain`](https://furuse.work/ops/gfx2d/isp/lens_shading_gain.html) · [`lens_system`](https://furuse.work/ops/optics/design/lens_system.html) · [`linescan_acquire`](https://furuse.work/ops/optics/linescan/linescan_acquire.html) · [`linescan_lens_columns`](https://furuse.work/ops/optics/linescan/linescan_lens_columns.html) · [`linescan_lens_example`](https://furuse.work/ops/optics/linescan/linescan_lens_example.html) · [`paraxial_trace`](https://furuse.work/ops/optics/design/paraxial_trace.html) · [`relative_illumination`](https://furuse.work/ops/optics/geometric/relative_illumination.html) · [`tdi_snr`](https://furuse.work/ops/optics/linescan/tdi_snr.html) · [`tdi_sync_mtf`](https://furuse.work/ops/optics/linescan/tdi_sync_mtf.html)

## No.2026.241 —— 工業用 OCT ―― 塗装・コート・多層フィルムの層厚と中の欠陥を、1 本の干渉スペクトルの FFT で深さ方向に見る

[![工業用 OCT ―― 塗装・コート・多層フィルムの層厚と中の欠陥を、1 本の干渉スペクトルの FFT で深さ方向に見る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/01_real_paint_bscans_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/01_real_paint_bscans.png)

*↑ **工業用 OCT ―― 塗装・コート・多層フィルムの層厚と中の欠陥を、1 本の干渉スペクトルの FFT で深さ方向に見る** ―― 塗装・コンフォーマルコート・接着層・多層フィルムの層の並びと、層の中の空洞・剥離を光干渉断層(OCT)で壊さずに見る。新 op 13 本(`octscan`、`opsoptics` の `oct`): `oct_design`(軸分解能 0.44 λ0²/Δλ・深さ範囲 λ0²/(4δλ)・roll-off・SNR・横分解能と焦点深度を撮る前に)/ `oct_interferogram`・`oct_bscan_simulate`(層の並び → 干渉スペクトル、屈折率と分散は材料表)/ `oct_k_linearize`・`oct_dispersion_compensate`・`oct_dispersion_estimate`・`oct_ascan`・`oct_bscan` / `oct_layer_thickness`(群屈折率で厚さ、分離できなければ拒否)・`oct_bscan_boundaries`・`oct_bscan_flatten` / `oct_from_spectra`(生のスペクトルの入口)。**実測**: 公開の自動車塗装の生スペクトル(CC BY 4.0)を Fullseye の op だけで処理し、透明層 44.5 / 86.4 / 99.7 / 70.8 µm が論文の OCT と 1.5 µm 以内・顕微鏡と 3.6 µm 以内、着色層は 4 枚中 3 枚が顕微鏡と 2.3 µm 以内(1 枚は 7.6 µm ずれて未解決)、白の見本の着色層の下は拒否、透明層の光学厚 155.6 µm の深さに水平に出る自己相関の幽霊。合成: 群屈折率で割った厚さが真値と 0.04 µm、位相屈折率なら 0.9〜1.9 % 厚い、SNR・roll-off・分散の広がりが閉形式と一致、点像の幅の 1.4 倍より薄い層は拒否、コートの厚さの地図と空洞・剥離の検出。*

[![屈折率は論文と同じ 1.56(透明層)・1.64(着色層)。表のどの行がどのファイルかは論文に無く、透明層の厚さで決めた(推定)。着色層はその対応と独立の突き合わせ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/02_real_thickness_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/02_real_thickness_table.png)

*↑ 測定の図 ―― 屈折率は論文と同じ 1.56(透明層)・1.64(着色層)。表のどの行がどのファイルかは論文に無く、透明層の厚さで決めた(推定)。着色層はその対応と独立の突き合わせ。*

[![黒・濃色は透明層の下の面と着色層の下の面の 2 つの山。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/03_real_flattened_profiles_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/03_real_flattened_profiles.png)

*↑ 黒・濃色は透明層の下の面と着色層の下の面の 2 つの山。*

[![SD 840/50 nm 2048 画素(深さ範囲 2.26 mm)、SS 1310/100 nm・瞬時線幅 0.1 nm。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/06_rolloff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/06_rolloff.png)

*↑ SD 840/50 nm 2048 画素(深さ範囲 2.26 mm)、SS 1310/100 nm・瞬時線幅 0.1 nm。*

[![試料腕が参照光と同じ桁に強いと、層の上下の面どうしの干渉が 0 の近くに立つ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/09_autocorrelation_ghost_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/09_autocorrelation_ghost.png)

*↑ 試料腕が参照光と同じ桁に強いと、層の上下の面どうしの干渉が 0 の近くに立つ。*

[![横 1.2 mm、縦は光路 25〜440 µm。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/12_coat_bscan_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/12_coat_bscan.png)

*↑ 横 1.2 mm、縦は光路 25〜440 µm。*

[![試料腕に溶融石英 12 mm の分散の不一致。補償の係数 a2 を 0 から 35.6 µm² まで動かすと、PMMA / PC / PS の 3 層の界面がにじみから線に締まる(横 0.6 mm、光路 130〜380 µm)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/15_dispersion_compensation.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_industrial_oct/15_dispersion_compensation.gif)

*↑ 動く図 ―― 試料腕に溶融石英 12 mm の分散の不一致。補償の係数 a2 を 0 から 35.6 µm² まで動かすと、PMMA / PC / PS の 3 層の界面がにじみから線に締まる(横 0.6 mm、光路 130〜380 µm)。*

```
py -3.11 examples/poc_industrial_oct.py
```

ソース: [examples/poc_industrial_oct.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_industrial_oct.py)

この回が作った図は全部で **15 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_industrial_oct)

使用 op(ノートへ): [`glass`](https://furuse.work/ops/optics/design/glass.html) · [`material_optical_constants`](https://furuse.work/ops/optics/matprop/material_optical_constants.html) · [`oct_ascan`](https://furuse.work/ops/optics/oct/oct_ascan.html) · [`oct_bscan`](https://furuse.work/ops/optics/oct/oct_bscan.html) · [`oct_bscan_boundaries`](https://furuse.work/ops/optics/oct/oct_bscan_boundaries.html) · [`oct_bscan_flatten`](https://furuse.work/ops/optics/oct/oct_bscan_flatten.html) · [`oct_bscan_simulate`](https://furuse.work/ops/optics/oct/oct_bscan_simulate.html) · [`oct_design`](https://furuse.work/ops/optics/oct/oct_design.html) · [`oct_dispersion_broadening`](https://furuse.work/ops/optics/oct/oct_dispersion_broadening.html) · [`oct_dispersion_compensate`](https://furuse.work/ops/optics/oct/oct_dispersion_compensate.html) · [`oct_dispersion_estimate`](https://furuse.work/ops/optics/oct/oct_dispersion_estimate.html) · [`oct_from_spectra`](https://furuse.work/ops/optics/oct/oct_from_spectra.html) · [`oct_interferogram`](https://furuse.work/ops/optics/oct/oct_interferogram.html) · [`oct_k_linearize`](https://furuse.work/ops/optics/oct/oct_k_linearize.html) · [`oct_layer_thickness`](https://furuse.work/ops/optics/oct/oct_layer_thickness.html)

## No.2026.255 —— 肉の中の骨片とガラスを、2 つのエネルギーで材質ごとに分ける(デュアルエナジー / フォトンカウンティング X 線)

[![肉の中の骨片とガラスを、2 つのエネルギーで材質ごとに分ける(デュアルエナジー / フォトンカウンティング X 線)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dual_energy_xray/04_tray_single_vs_basis_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dual_energy_xray/04_tray_single_vs_basis.png)

*↑ **肉の中の骨片とガラスを、2 つのエネルギーで材質ごとに分ける(デュアルエナジー / フォトンカウンティング X 線)** ―― 食品の X 線検査の 1 枚の透過像は各画素で L = −ln(I/I₀) という 1 つの数しか測らない —— 厚い肉と薄い硬い異物は区別できない。光子のエネルギーを 2 つの窓で数え分ける検出器で撮ると、μ(E) の形が材質で違うので、各画素で厚みと材質が分かれる(Alvarez & Macovski 1976 の基底分解)。新 op 14 本(`opstomography` の `spectral_xray`): 材料表の X 線の列(`material_xray_attenuation` ほか 3 本、NIST SRD 126 の部分集合と混合則)と `dualxray` 10 本(X 線管のスペクトル・線質・検出器のチャネル・投影・基底分解・CRLB・R 値・実効 Z・弁別の誤り率)。μ/ρ は NIST の公表値と一致(Cu 8 keV 52.55、K 端 38.4 → 278.4)、管の模型の半価層は IEC 61267 の線質 8 つと 5.8 % 以内(模型は公開のスペクトル計算(MIT)の形に合わせ、IEC の値は合わせに使っていない)。厚さ 25〜60 mm の肉のトレイで、骨片とガラスの段差は肉のむらの 0.9 倍、しきい値 1 本では肉の 86 % を誤検出、高域を取っても肉の重なりの縁が偽の塊 2 個になるが、赤身 + Al に分けた Al の像は偽の塊 0。厚い PE と薄い Al の交絡の組は 1 つの窓では d′ = 0、2 つの窓の誤り率 Φ(−d′/2) はモンテカルロと 0.004 以内、分けられなくなる Al の厚さ(誤り率 5 %)は閉形式 0.125 mm・実測 0.126 mm、肉 40 mm の下で 0.364 mm。分解の雑音はクラメール・ラオの下限の 0.995 / 0.997 倍。壊れ方: 電荷共有 25 % を知らずに分解すると肉が Al に化け、単色の近似は肉 6 cm で Al −1.5 mm に偏る。埋まった異物の見かけの Z は密度でも動く(PVC は 13.9 が 18.7 に見える)。学習 0、較正 0、門 21 件。*

[![W 陽極の管(Kramers の厚い陽極 + 自己吸収 + K 線 59 / 67 keV)を Al 2.5 mm で濾した光子スペクトル(半価層 2.74 mm Al、平均 42.6 keV)。CdTe 2 mm の吸収効率をかけ、堆積エ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dual_energy_xray/01_spectrum_and_windows_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dual_energy_xray/01_spectrum_and_windows.png)

*↑ 測定の図 ―― W 陽極の管(Kramers の厚い陽極 + 自己吸収 + K 線 59 / 67 keV)を Al 2.5 mm で濾した光子スペクトル(半価層 2.74 mm Al、平均 42.6 keV)。CdTe 2 mm の吸収効率をかけ、堆積エネルギーで 2 つの窓に分ける。*

[![低いエネルギーでは光電効果(≈ Z³/E³)で Z の大きい材料ほど急に増え、高いエネルギーではコンプトン散乱で電子密度に揃う。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dual_energy_xray/02_mass_attenuation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dual_energy_xray/02_mass_attenuation.png)

*↑ 低いエネルギーでは光電効果(≈ Z³/E³)で Z の大きい材料ほど急に増え、高いエネルギーではコンプトン散乱で電子密度に揃う。*

[![1 枚の透過像(灰色)の上に、Al の像で浮いた画素だけ、基底の向きから読んだ見かけの Z を色で重ねた(緑 ≈ 12〜14、黄〜橙 ≈ 15〜20、赤 ≈ 25 以上)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dual_energy_xray/05_material_colour_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dual_energy_xray/05_material_colour.png)

*↑ 1 枚の透過像(灰色)の上に、Al の像で浮いた画素だけ、基底の向きから読んだ見かけの Z を色で重ねた(緑 ≈ 12〜14、黄〜橙 ≈ 15〜20、赤 ≈ 25 以上)。*

[![高い窓だけでは同じ L(1 枚の像の d′ = 0)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dual_energy_xray/08_confound_boundary_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dual_energy_xray/08_confound_boundary.png)

*↑ 高い窓だけでは同じ L(1 枚の像の d′ = 0)。*

[![肉 4 cm の下の Al の厚さの雑音(下限)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dual_energy_xray/10_threshold_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dual_energy_xray/10_threshold_sweep.png)

*↑ 肉 4 cm の下の Al の厚さの雑音(下限)。*

```
py -3.11 examples/poc_dual_energy_xray.py
```

ソース: [examples/poc_dual_energy_xray.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dual_energy_xray.py)

この回が作った図は全部で **12 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_dual_energy_xray)

使用 op(ノートへ): [`basis_decomposition_crlb`](https://furuse.work/ops/tomography/spectral_xray/basis_decomposition_crlb.html) · [`basis_material_decompose`](https://furuse.work/ops/tomography/spectral_xray/basis_material_decompose.html) · [`dual_energy_separability`](https://furuse.work/ops/tomography/spectral_xray/dual_energy_separability.html) · [`dual_kvp_channels`](https://furuse.work/ops/tomography/spectral_xray/dual_kvp_channels.html) · [`ellipse`](https://furuse.work/ops/annotate/shape/ellipse.html) · [`material_effective_z`](https://furuse.work/ops/tomography/spectral_xray/material_effective_z.html) · [`material_from_sellmeier`](https://furuse.work/ops/optics/matprop/material_from_sellmeier.html) · [`material_xray_attenuation`](https://furuse.work/ops/tomography/spectral_xray/material_xray_attenuation.html) · [`material_xray_constants`](https://furuse.work/ops/tomography/spectral_xray/material_xray_constants.html) · [`photon_counting_channels`](https://furuse.work/ops/tomography/spectral_xray/photon_counting_channels.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`xray_beam_quality`](https://furuse.work/ops/tomography/spectral_xray/xray_beam_quality.html) · [`xray_channel_projection`](https://furuse.work/ops/tomography/spectral_xray/xray_channel_projection.html) · [`xray_tube_spectrum`](https://furuse.work/ops/tomography/spectral_xray/xray_tube_spectrum.html)

## No.2026.271 —— レンズの製造公差を、MTF・歩留まり・補償ストロークまで一枚の予算にする

[![レンズの製造公差を、MTF・歩留まり・補償ストロークまで一枚の予算にする](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/01_sensitivity_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/01_sensitivity.png)

*↑ **レンズの製造公差を、MTF・歩留まり・補償ストロークまで一枚の予算にする** ―― 公開処方の三枚玉に、曲率・厚み・屈折率・アッベ数・偏心・傾き・面の非点不整・くさび・群偏心を行ごとに割り当てる。新 op 8 本は分布、中央差分感度、Monte Carlo、Wilson 95 % 歩留まり区間、複数の補償変数と組立ストロークを一つの報告にする。薄いくさびの像移動は閉形式 f(n−1)α に 6e-8、1 fringe の非点不整の実光線 OPD RMS は閉形式に 1.3 %。CI の 16 試行では歩留まり 0.688、内部間隔と像面の補償を足すと 1.000。一様・正規・切断正規は同じ ±公差でも 0.750 / 1.000 / 1.000、首位の公差を締めて低感度を緩めた再配分は 0.833。学習 0、較正 0。*

[![同じ試行から得た MTF と RMS spot。赤線は合否限界。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/02_histograms_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/02_histograms.png)

*↑ 測定の図 ―― 同じ試行から得た MTF と RMS spot。赤線は合否限界。*

[![像面だけの場合と内部間隔を加えた場合を比較。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/03_compensation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/03_compensation.png)

*↑ 像面だけの場合と内部間隔を加えた場合を比較。*

[![一様・正規・±公差で切った正規分布の歩留まり。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/04_distributions_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/04_distributions.png)

*↑ 一様・正規・±公差で切った正規分布の歩留まり。*

[![線形予測と Monte-Carlo 実測を明示。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/05_rebudget_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/05_rebudget.png)

*↑ 線形予測と Monte-Carlo 実測を明示。*

[![同じ処方の基準像と、1 arcmin のくさびを入れた像。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/06_wedge_probe_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/06_wedge_probe.png)

*↑ 同じ処方の基準像と、1 arcmin のくさびを入れた像。*

[![感度首行を -tol から +tol へ掃引した点像。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/07_tolerance_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lens_tolerancing/07_tolerance_sweep.gif)

*↑ 動く図 ―― 感度首行を -tol から +tol へ掃引した点像。*

```
py -3.11 examples/poc_lens_tolerancing.py
```

ソース: [examples/poc_lens_tolerancing.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_lens_tolerancing.py)

この回が作った図は全部で **7 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_lens_tolerancing)

使用 op(ノートへ): [`chief_ray`](https://furuse.work/ops/optics/design/chief_ray.html) · [`lens_system`](https://furuse.work/ops/optics/design/lens_system.html) · [`opd_samples`](https://furuse.work/ops/optics/design/opd_samples.html) · [`ray_bundle`](https://furuse.work/ops/optics/design/ray_bundle.html) · [`tolerance_compensators`](https://furuse.work/ops/optics/tolerancing/tolerance_compensators.html) · [`tolerance_criteria`](https://furuse.work/ops/optics/tolerancing/tolerance_criteria.html) · [`tolerance_monte_carlo`](https://furuse.work/ops/optics/tolerancing/tolerance_monte_carlo.html) · [`tolerance_report`](https://furuse.work/ops/optics/tolerancing/tolerance_report.html) · [`tolerance_sensitivity`](https://furuse.work/ops/optics/tolerancing/tolerance_sensitivity.html) · [`tolerance_table`](https://furuse.work/ops/optics/tolerancing/tolerance_table.html) · [`tolerance_table_from_zmx`](https://furuse.work/ops/optics/tolerancing/tolerance_table_from_zmx.html) · [`tolerance_table_zmx`](https://furuse.work/ops/optics/tolerancing/tolerance_table_zmx.html)

## No.2026.273 —— 同じ粒子を走査像と透過像で測る ―― 52 nm と 48 nm のどちらが正しいか

[![同じ粒子を走査像と透過像で測る ―― 52 nm と 48 nm のどちらが正しいか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/02_same_specimen_sem_tem_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/02_same_specimen_sem_tem.png)

*↑ **同じ粒子を走査像と透過像で測る ―― 52 nm と 48 nm のどちらが正しいか** ―― 同じ球形・ファセット粒子14個の台帳から二つの像を作り、面積相当径、最大傾斜、接触対の分水嶺、傾斜像の高さ、限定角再構成を共通の真値で採点する。52 nm粒子では走査像のしきい値径は+4.16 nm、透過像は正焦点で-0.18 nm、焦点外れ12000 nmで+9.82 nm。走査像の偏りはガウス縁の閉形式2 sqrt(2 ln 2) sigmaに一致し、透過像の暗い縁はsqrt(lambda defocus)に10%以内。反射信号の材料比は公表された反射係数、立体計測は平行投影の閉形式と完全角再構成で検算する。新opなし、学習0、較正0。*

[![Truth height only: turbo-like pseudo-colour with a nanometre colour bar in the margin.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/01_truth_height_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/01_truth_height.png)

*↑ 測定の図 ―― Truth height only: turbo-like pseudo-colour with a nanometre colour bar in the margin.*

[![Bright-field in-focus and under-focus output | derived diameters | absolute residual.](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/03_tem_raw_overlay_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/03_tem_raw_overlay_error.png)

*↑ Bright-field in-focus and under-focus output | derived diameters | absolute residual.*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/04_diameter_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/04_diameter_bias.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/05_touching_watershed_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/05_touching_watershed.png)

*↑ この回の図*

[![図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/06_missing_wedge_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/06_missing_wedge.png)

*↑ この回の図*

[![24 greyscale bright-field frames with data bar; first and last defocus differ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/08_tem_focus_sweep.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sem_tem_same_particle/08_tem_focus_sweep.gif)

*↑ 動く図 ―― 24 greyscale bright-field frames with data bar; first and last defocus differ*

```
py -3.11 examples/poc_sem_tem_same_particle.py
```

ソース: [examples/poc_sem_tem_same_particle.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_sem_tem_same_particle.py)

この回が作った図は全部で **8 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_sem_tem_same_particle)

使用 op(ノートへ): [`color_bar`](https://furuse.work/ops/annotate/furniture/color_bar.html) · [`filtered_backprojection`](https://furuse.work/ops/tomography/reconstruct/filtered_backprojection.html) · [`radon_transform`](https://furuse.work/ops/tomography/forward/radon_transform.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`scale_bar`](https://furuse.work/ops/annotate/furniture/scale_bar.html) · [`sem_electron_mc`](https://furuse.work/ops/generative/sem/sem_electron_mc.html) · [`sem_image`](https://furuse.work/ops/generative/sem/sem_image.html) · [`sem_render`](https://furuse.work/ops/generative/sem/sem_render.html) · [`tem_image_weak_phase`](https://furuse.work/ops/optics/tem/tem_image_weak_phase.html) · [`tem_multislice`](https://furuse.work/ops/optics/tem/tem_multislice.html) · [`tem_projected_potential`](https://furuse.work/ops/optics/tem/tem_projected_potential.html) · [`tem_wavelength`](https://furuse.work/ops/optics/tem/tem_wavelength.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`watersheds_marker`](https://furuse.work/ops/segmentation/watershed/watersheds_marker.html)

## No.2026.274 —— 同じ3次元場面を間接ToFと直接ToFで測る――多経路・混合画素・pile-up・体積誤差

[![同じ3次元場面を間接ToFと直接ToFで測る――多経路・混合画素・pile-up・体積誤差](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/01_scene_viewer_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/01_scene_viewer.png)

*↑ **同じ3次元場面を間接ToFと直接ToFで測る――多経路・混合画素・pile-up・体積誤差** ―― 320×240画素の同じ場面を、IR振幅、1.5–6.0 mの色距離、点群で見比べる。合成と実測の振幅分布のW1距離は0.145（門0.594）。続く図は物理効果を順に加えた深度、振幅と距離雑音（対数傾きは実測 -0.878、合成 -1.027）、壁接合部の湾曲（実測 -551 mm、合成 +75 mm。プロファイルの向きを揃えると同符号）、透明板の1.35 m離れた二返り、細い柱の混合画素、直接方式の時間ヒストグラム、三つの箱の体積（誤差 +0.16 / +0.47 / +0.29 %）を示す。最後は48枚、576×432画素、8 fpsで1.4–6.2 mを進む光前線。実フレームは再配布せず、曲線と集計値だけを載せる。新しいop 0、学習0、較正0、門13件。*

[![全パネル同じ距離範囲。暗部の荒れと隅の湾曲が順に現れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/02_effects_added_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/02_effects_added.png)

*↑ 測定の図 ―― 全パネル同じ距離範囲。暗部の荒れと隅の湾曲が順に現れる。*

[![対数傾きは実測 -0.878、合成 -1.027。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/03_noise_vs_amplitude_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/03_noise_vs_amplitude.png)

*↑ 対数傾きは実測 -0.878、合成 -1.027。*

[![実測は曲線だけを掲載し、フレームを再配布しない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/04_corner_bow_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/04_corner_bow.png)

*↑ 実測は曲線だけを掲載し、フレームを再配布しない。*

[![手描きマスクではなく3×3サブ光線のフェーザ和。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/06_pole_flying_pixels_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/06_pole_flying_pixels.png)

*↑ 手描きマスクではなく3×3サブ光線のフェーザ和。*

[![強い画素では最初の光子が早い側へ偏る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/07_dtof_histograms_depth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/07_dtof_histograms_depth.png)

*↑ 強い画素では最初の光子が早い側へ偏る。*

[![48枚、576×432。各時刻を99パーセンタイル・γ=0.5で階調化。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/09_dtof_light_front.gif)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tof_camera/09_dtof_light_front.gif)

*↑ 動く図 ―― 48枚、576×432。各時刻を99パーセンタイル・γ=0.5で階調化。*

```
py -3.11 examples/poc_tof_camera.py
```

ソース: [examples/poc_tof_camera.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_tof_camera.py)

この回が作った図は全部で **9 枚**あります —— [全部見る](https://github.com/furuse-kazufumi/fullseye/tree/master/docs/articles/assets/poc/poc_tof_camera)

使用 op(ノートへ): [`bilateral_filter_depth`](https://furuse.work/ops/3d/depth_denoise/bilateral_filter_depth.html) · [`depth_to_points`](https://furuse.work/ops/3d/transform/depth_to_points.html) · [`dtof_cube_depth`](https://furuse.work/ops/photon/dtof/dtof_cube_depth.html) · [`dtof_cube_simulate`](https://furuse.work/ops/photon/dtof/dtof_cube_simulate.html) · [`points_render`](https://furuse.work/ops/3d/render/points_render.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html)




---

**この展示館は Claude Code と一緒に作りました。** 問いと方向決めは私、実装・掃引・対照群・敵対レビューは Claude Code、という分業です。53 本の PoC を 2 日で走らせて図まで揃えられたのは、この運用のおかげです。試してみたい方は、こちらの招待リンクから **1 週間の無料トライアル** が使えます: [claude.ai/referral/0sqPw8E_lw](https://claude.ai/referral/0sqPw8E_lw)

面白い展示が 1 つでもあったら、**いいね・ストック**をもらえると助かります。どのウィングを次に増やすかは反応を見て決めるつもりなので、「自分の分野のこれが欲しい」もコメントで教えてください。実データに差し替えて崖の位置が変わった話は、いちばん聞きたい話です。
