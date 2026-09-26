# Fullseye ドキュメント索引

**Language:** [日本語](README.md) · [English](README.en.md) · [简体中文](README.zh.md) · [繁體中文](README.tw.md) · [한국어](README.ko.md) · [Deutsch](README.de.md)

> **Fullseye is an open, explainable vision-and-measurement foundation for
> industrial inspection and Physical AI** — from image and signal acquisition to
> geometry, measurement, inspection evidence, and robot action.
> Apache-2.0 · `pip install fullseye` · **[English index →](README.en.md)**


![実際のオペレータ出力だけで作った 6 幕(エッジと方位 / 連結成分の選別 / サブピクセル計測 / SDF からのメッシュ化 / 点群クラスタリング / レンズのデフォーカス)。](articles/assets/fullseye_hero.gif)

*実際のオペレータ出力だけで作った 6 幕(エッジと方位 / 連結成分の選別 / サブピクセル計測 / SDF からのメッシュ化 / 点群クラスタリング / レンズのデフォーカス)。*

**Fullseye**（作業名 imgevolve）は、numpy-native な画像処理オペレータ・ライブラリと、HDevelop 風のビジュアル・パイプライン設計環境（Fullseye Studio）+ 実行ランタイム（FullseyeEngine）を備えた、HALCON/HDevelop 級の実用ツールです。オペレータは約 **932**（レジストリ）、実 HALCON オペレータ **980/2313** を genuine 実装、48 カテゴリをカバーします。

★ **画像処理ライブラリでは珍しく「仮想の光学設計」まで内蔵** —— 薄肉/厚肉レンズ・光線追跡・Seidel 収差・PSF/MTF に加え、damped-least-squares（Levenberg–Marquardt）でレンズ処方そのものを最適化（`optimize_lens`）。**撮像系を設計して、その像を上のオペレータで検査するまでを一気通貫**でできる（半導体・精密計測で効く差別化）。

> **まずはここから → [GETTING_STARTED.md](GETTING_STARTED.md)（5 分で動かす）**

> **できること一覧 → [CAPABILITIES.md](CAPABILITIES.md)**（何をしたいかで引く索引）／**PoC が上げた堅牢性 → [HARDENING.md](HARDENING.md)**（見つけて直した記録）／**どこまで検証できているか → [MATURITY.md](MATURITY.md)**（手で書かず数えて出す成熟度台帳）

---

<!-- poc-index:start -->

## PoC シリーズ — 真値つきで実問題を解いた 151 本

どれも**真値を閉形式か合成で厳密に持ち、ゼロ点(何もしない場合)を必ず併記**します。壊れ方は 1 つの指標に畳まず別々に数え、原因は対照群で分けます。全文と実行手順は [examples/README.md](../examples/README.md)。

| 分野 | PoC と、そこで分かったこと |
|---|---|
| 計測 (36) | [`poc_aoi_ct_traceability`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_aoi_ct_traceability.py) 全数の 2-D 検査と抜き取りの 3-D 検査を対応づける(格子は自分に重なる)<br>[`poc_asbuilt_wall_deviation`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_asbuilt_wall_deviation.py) 竣工した部屋の壁を測る(外接直方体は寸法でなく部屋の向きを測っている)<br>[`poc_battery_electrode_breathing`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_battery_electrode_breathing.py) 電極の呼吸を µm で測る(サブピクセルなら何でもよいわけではない)<br>[`poc_bone_trabecular_thickness`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bone_trabecular_thickness.py) 骨梁の厚さ Tb.Th・間隔 Tb.Sp・骨体積率(平板モデル vs 直接法)<br>[`poc_bump_coplanarity`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bump_coplanarity.py) バンプの共平面性と基板そりの分離(引きすぎると本物の不良も消える)<br>[`poc_cad_scan_deviation`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_cad_scan_deviation.py) CAD と実測点群の差分検査(合わせた分だけ欠陥が消え、無い所にへこみが出る)<br>[`poc_crack_width`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_crack_width.py) コンクリートのひび割れ幅は 1 画素より細い(数える幅と、積分する幅)<br>[`poc_crack_width_timeseries`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_crack_width_timeseries.py) ひび割れの伸びを 12 期で測る(幅が当たる測り方と、伸びが当たる測り方は別)<br>[`poc_datacenter_thermal_field`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_datacenter_thermal_field.py) 疎な温度センサから 3-D 熱場を復元する(格子の死角がラックを消す)<br>[`poc_dic_strain`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dic_strain.py) DIC ひずみ計測(2 度の回転が 600 µε の嘘のひずみを作る)<br>[`poc_dimensional_inspection`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dimensional_inspection.py) 部品の寸法検査(サブピクセル計測と、埋もれていた実装の実地評価)<br>[`poc_fiber_orientation`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_fiber_orientation.py) 繊維の配向分布(角度は 180 度周期。素朴に平均すると 90 度ずれる)<br>[`poc_gear_tooth_metrology`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_gear_tooth_metrology.py) 歯車の歯形(偏心は 1 次、歯は z 次。歯が 1 枚欠けると両方が混ざる)<br>[`poc_geodetic_height_frames`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_geodetic_height_frames.py) 測地の高さと座標系(数字はもっともらしいまま数十メートル間違う)<br>[`poc_interferometry_step`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_interferometry_step.py) 白色干渉によるナノメートルの段差計測(どこまで測れるか)<br>[`poc_livestock_body_volume`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_livestock_body_volume.py) 家畜の体積計測(視体積交差は上界。凹みはカメラを増やしても埋まらない)<br>[`poc_metal_grain_size`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_metal_grain_size.py) 結晶粒度 G(面積法と切片法は別の崖で落ちる)<br>[`poc_multibeam_bathymetry`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_multibeam_bathymetry.py) 多ビーム測深(音速を取り違えると外側ビームだけが壊れる)<br>[`poc_particle_sizing`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_particle_sizing.py) 粒度分布(D50 が合う点は「正確」ではなく打ち消し)<br>[`poc_photoelasticity`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_photoelasticity.py) 光弾性(縞から応力。壊れるのは応力が大きい所ではない)<br>[`poc_pipe_wall_loss`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pipe_wall_loss.py) 配管内面の減肉を展開図で測る(軸ずれと管底腐食は同じ 1 周期に居る)<br>[`poc_real_coin_metrology`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_coin_metrology.py) 実写のコインを数えて測る(答えは合っているが余裕は 0.05)<br>[`poc_scan_to_bim_asbuilt`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_scan_to_bim_asbuilt.py) 設計モデルと実物の差(部屋が合わせの自由度を吸い、余りを他の部材へ配る)<br>[`poc_screw_thread_metrology`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_screw_thread_metrology.py) ねじのピッチ・フランク角・有効径(傾きは左右フランクに逆符号)<br>[`poc_settlement_significance`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_settlement_significance.py) 沈下の有意性を検出限界で切る(平均は「全体が沈んだ」、LoD は「沈んだのは半分」)<br>[`poc_star_astrometry`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_star_astrometry.py) 星の位置を測る(理論下限を下回ったら、それは推定できていない印)<br>[`poc_stockpile_volume`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_stockpile_volume.py) 堆積物の在庫量(誰も測っていない山の下の地面が答えを決める)<br>[`poc_strain_history`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_strain_history.py) クリープ試験のひずみ履歴(累積か直接か。交点は時間軸には無かった)<br>[`poc_structure_4d_deterioration`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_structure_4d_deterioration.py) 構造物の 4D 差分(点検のたびに測る場所がずれる)<br>[`poc_surface_roughness`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_surface_roughness.py) 表面粗さ(同じデータで Sa は合格・Sz は不合格になる標本間隔がある)<br>[`poc_thermal_radiometry`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_thermal_radiometry.py) 熱画像は温度画像ではない(放射率と反射と、足し算にならない不確かさ)<br>[`poc_tree_ring_dendro`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_tree_ring_dendro.py) 年輪年代学(年数の誤差と幅の相関は別に数える)<br>[`poc_water_level`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_water_level.py) 河川の水位を斜め写真から測る(透視を無視した行番号は弓なりに外れる)<br>[`poc_weld_bead_profile`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_weld_bead_profile.py) レーザー三角測量の断面から溶接ビードを測る(測れなかったところを 0 と書く罪)<br>[`poc_weld_bead_scan_angle`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_weld_bead_scan_angle.py) 光切断で溶接ビードを走査する(分解能と遮蔽は同じノブの表裏)<br>[`poc_wound_area_tracking`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_wound_area_tracking.py) 創傷面積の経時変化(較正の誤差は面積に 2 乗で効く) |
| analysis (19) | [`poc_attention_identities`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_attention_identities.py) 速くする工夫は、全部おなじ数の別の括り方だった —— 注意機構を恒等式で採点する<br>[`poc_beats_fringes_and_screens`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_beats_fringes_and_screens.py) うなりは一つ(干渉縞と印刷のモアレは同じ数学)<br>[`poc_calipers_under_illusion`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_calipers_under_illusion.py) 錯視で測定器を健診する(キャリパーが外すのはどこで、なぜか)<br>[`poc_complex_plane_fields`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_complex_plane_fields.py) 複素平面を「面」で見る(位相彩色・吸引域・脱出時間・翼まわりの流れ)<br>[`poc_connectome_motor_bottleneck`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_connectome_motor_bottleneck.py) 動きの量子化 ―― 脳から筋へ、命令の次元はどこで落ちるか(MaleCNS の首と RL の関節を同じ物差しで)<br>[`poc_em_branch_territory`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_em_branch_territory.py) 枝の縄張り(骨格が「どこ」かだけでなく「どの枝が近いか」を体積に配ると、枝ごとの体積と半径が測れる)<br>[`poc_endless_zoom_and_turning_solids`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_endless_zoom_and_turning_solids.py) 無限に寄り続ける絵と、回り続ける立体<br>[`poc_four_dimensions_by_three_d_tools`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_four_dimensions_by_three_d_tools.py) 4 次元の主張を、3 次元の平凡な op で採点する<br>[`poc_geodetic_benchmarks_real`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_geodetic_benchmarks_real.py) 高さは 2 つある・実データ編(公開された測量成果 523 点で、高さの取り違えを検出器にかける)<br>[`poc_gravitational_lens_invariants`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_gravitational_lens_invariants.py) 重力レンズの像を、産業用の測定 op で採点する<br>[`poc_illusions_and_perpetual_drawing`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_illusions_and_perpetual_drawing.py) 無限に描き続ける絵を、恒等式で採点する<br>[`poc_measurement_system_analysis`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_measurement_system_analysis.py) その数字のうち、いくつが測り方のものか(ゲージ R&R と測定の不確かさ)<br>[`poc_microns_brain_wave`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_microns_brain_wave.py) MICrONS の脳の波 ―― 1 mm³ の視覚野で、配線は実測の応答をどこまで説明するか<br>[`poc_one_stroke_epicycles`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_one_stroke_epicycles.py) 写真を 1 本の線にして、回る振り子に描かせる(濃淡 → 点描 → 巡回路 → フーリエ → G-code)<br>[`poc_periodic_video_boundary`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_periodic_video_boundary.py) 継ぎ目の無い動画で、時間方向 op の周期境界を検査する<br>[`poc_theorems_as_pictures`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_theorems_as_pictures.py) 定理が門になる図(アポロニウス・フォード・測地ドーム・葉序・IFS・空間充填曲線)<br>[`poc_vanishing_detail_and_morphing_area`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_vanishing_detail_and_morphing_area.py) 遠ざかると消える距離と、形が変わるときの面積<br>[`poc_what_a_picture_cannot_check`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_what_a_picture_cannot_check.py) 絵では確かめられないもの(力学系と極小曲面を定義と恒等式で採点する)<br>[`poc_zernike_aberrations`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_zernike_aberrations.py) 収差の絵は、絵のまま採点できる —— ゼルニケ多項式と点像 |
| 診断 (10) | [`poc_bearing_diagnosis`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bearing_diagnosis.py) 転がり軸受の異常診断(どこまで雑音に埋もれた欠陥を拾えるか)<br>[`poc_cold_chain_excursion`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_cold_chain_excursion.py) 冷蔵輸送の逸脱判定(ロガーの置き場所が合否を決める)<br>[`poc_fabric_defect`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_fabric_defect.py) 周期のある地に埋もれた欠陥(まとめた ROC が隠すもの)<br>[`poc_machine_condition_fusion`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_machine_condition_fusion.py) 熱・振動・形状の総合診断(束ねても情報が増えない条件)<br>[`poc_prnu_camera_fingerprint`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_prnu_camera_fingerprint.py) カメラ指紋 PRNU(枚数で育ち、保存ボタンで消える)<br>[`poc_pv_thermal_survey`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pv_thermal_survey.py) 太陽光発電所のドローン熱画像(ΔT を測っているつもりで、風と角度を測っている)<br>[`poc_solar_el_inspection`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_solar_el_inspection.py) 太陽電池 EL 検査(暗い = 不活性ではない。種別ごとに測る)<br>[`poc_solder_fillet_aoi`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_solder_fillet_aoi.py) はんだフィレットの AOI(3 リング照明は傾きの 3 段量子化器)<br>[`poc_thermography_ndt`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_thermography_ndt.py) パルスサーモグラフィ(『測れない欠陥』の正体が時間窓だった)<br>[`poc_weld_radiograph_porosity`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_weld_radiograph_porosity.py) 溶接 X 線透過像の気孔検出と等級(等級を 1 段間違える割合) |
| 幾何 (7) | [`poc_dfm_thickness_overhang`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dfm_thickness_overhang.py) 造形しやすさを形から測る(しきい値に貼りついた面と、丸めで飛ぶ判定)<br>[`poc_mesh_quality_repair`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_mesh_quality_repair.py) メッシュの健全性診断と修復(直した分だけ欠陥は消え、量は戻らない)<br>[`poc_pallet_load_utilization`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pallet_load_utilization.py) パレットの積載率(1 つの数字が隙間とはみ出しを同じ値にする)<br>[`poc_panorama_drift`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_panorama_drift.py) パノラマの累積ドリフト(埋もれていた既存実装はゼロ点を上回らなかった)<br>[`poc_print_warpage_risk`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_print_warpage_risk.py) 積層造形の反りと剥離(面積の履歴で決まる分と、決まらない分)<br>[`poc_symmetry_restoration`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_symmetry_restoration.py) 対称性を使った欠損復元(文化財・化石。仮定した対称面が崖になる)<br>[`poc_xyt_event_surface`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_xyt_event_surface.py) 到達時刻面を (x, y, t) の等値面として取り出す(2-D の動画を 1 枚の 3-D の面として測る) |
| 測光 (6) | [`poc_allsky_cloud_cover`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_allsky_cloud_cover.py) 全天カメラの雲量(画素を数えると雲の位置で 1.45 倍動く)<br>[`poc_astro_photometry`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_astro_photometry.py) 天体スタックの測光精度(何枚重ねるとどこまで正確に測れるか)<br>[`poc_exoplanet_transit`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_exoplanet_transit.py) 系外惑星トランジットの相対測光(深さと継続時間は別々に壊れる)<br>[`poc_nuclei_ploidy`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_nuclei_ploidy.py) 蛍光核の積分輝度から倍数性を出す(面積では分かれない)<br>[`poc_real_sky_photometry`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_sky_photometry.py) 実写の深宇宙に既知の星を仕込んで測る(汚染は S/N も同じ向きに膨らませる)<br>[`poc_solar_limb_darkening`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_solar_limb_darkening.py) 縁が暗い天体の輪郭はどこか(周辺減光と「50 % 法」) |
| 分離 (6) | [`poc_colocalization_crosstalk`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_colocalization_crosstalk.py) 蛍光の共局在と漏れ込み(Pearson と Manders は別の場所で壊れる)<br>[`poc_pigment_unmixing`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pigment_unmixing.py) 多波長で彩色層を剥がす(勝ったのは「多波長」ではなく「近赤外」だった)<br>[`poc_polarization_specular`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_polarization_specular.py) 偏光による鏡面分離(分けた「拡散」は本当に拡散か)<br>[`poc_real_stain_unmix`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_stain_unmix.py) 実写の免疫染色を色で分ける(残差は平面内の誤りに構造的に盲目)<br>[`poc_recycling_sorting`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_recycling_sorting.py) 混合廃棄物の材質選別(消せる汚れと消せない汚れは代数で決まる)<br>[`poc_sea_ice_concentration`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_sea_ice_concentration.py) 海氷密接度(混合画素をどう数えるかで答えが変わる) |
| 校正 (5) | [`poc_camera_calibration`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_camera_calibration.py) カメラ校正の再投影誤差は何を保証しないか<br>[`poc_fly_optomotor_steering`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_fly_optomotor_steering.py) ハエの視葉だけで進路を立て直す(ラミナから操舵まで、学習なしで)<br>[`poc_public_camera_heading`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_public_camera_heading.py) 公共カメラはどこを向いているか(位置しか公開されない固定カメラの向きを、写真そのものから決める)<br>[`poc_public_camera_heading_real`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_public_camera_heading_real.py) 公共カメラはどこを向いているか・実写編(807 局の道路カメラで太陽を探し、日没 1 本から向きを決めて道路で検算する)<br>[`poc_thermal_drift_metrology`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_thermal_drift_metrology.py) カメラの熱ドリフトが寸法計測に効く量(分離できるのは歪みがあるから) |
| 領域分割 (5) | [`poc_cell_counting`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_cell_counting.py) 細胞の計数と分割(計数が合っていて分割が全部外れる点がある)<br>[`poc_leaf_disease_area`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_leaf_disease_area.py) 葉の病斑面積率(等級は色の軸より葉マスクと縁の定義で決まる)<br>[`poc_mri_bias_field`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_mri_bias_field.py) MRI バイアス場と組織面積(GM と WM は逆向きに壊れ、足すと隠れる)<br>[`poc_timelapse_growth`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_timelapse_growth.py) 成長のタイムラプスを時空間の連結成分として測る(合体はいつ起きたか)<br>[`poc_vegetation_cover`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_vegetation_cover.py) 植生被覆率(被覆率が当たっていて画素が全部外れる、が実際に起きる) |
| 動き (4) | [`poc_particle_tracking`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_particle_tracking.py) 粒子追跡を (行, 列, 時刻) の体積として測る(誤リンクの向きは 1 種類ではない)<br>[`poc_river_surface_velocity`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_river_surface_velocity.py) 河川表面流速を斜め動画から測る(速度の誤差と流量の誤差は別物)<br>[`poc_traffic_counting`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_traffic_counting.py) (x, y, t) で数える(通過台数とオクルージョン、そして L/V という 1 つの定数)<br>[`poc_warehouse_flow`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_warehouse_flow.py) 庫内の滞留を種類別に読む(1 つの「滞留時間」に畳むと全部が混雑になる) |
| 位置合わせ (4) | [`poc_change_detection_misreg`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_change_detection_misreg.py) 変化検出と位置合わせ誤差(偽陽性はエッジの帯、しかも崖つき)<br>[`poc_print_registration`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_print_registration.py) 印刷の版ずれを刷り上がりから測る(網点は格子なので答えが 1 つに決まらない)<br>[`poc_registration_basin`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_registration_basin.py) 点群位置合わせの収束域(どれだけずれていたら失敗するか)<br>[`poc_template_tracking`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_template_tracking.py) テンプレート追跡(見失うより先に、静かにずれる) |
| tomography_3d (4) | [`poc_battery_ct_degradation`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_battery_ct_degradation.py) 電池セルの内部劣化を CT で測る(膨れの何割が外から見えるか)<br>[`poc_battery_electrode_tortuosity`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_battery_electrode_tortuosity.py) 電極の屈曲度を CT から測る(Bruggeman は向きに盲目)<br>[`poc_ct_void_morphology`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_void_morphology.py) X 線 CT のボイド形態(合否 1 個の数字は、寿命に効く形に盲目)<br>[`poc_die_tilt_tsv_overlay`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_die_tilt_tsv_overlay.py) ダイの傾きと TSV の位置ずれ(同じ 1 つの CT から。傾きは回転まで偽装する) |
| visualization (4) | [`poc_eye_to_brain`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_eye_to_brain.py) 複眼が見る像と、脳のどこが反応するかを並べる(個眼をなぞると応答が配線を伝わる)<br>[`poc_live4d`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_live4d.py) 生きている組織の 3D+t を古典手法だけで短い 3D 動画像に(増幅・流れ・補間・高さ場、全部に真値)<br>[`poc_malecns_activity_wave`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_malecns_activity_wave.py) ハエの脳の立体の上で刺激の波が配線を伝わるのを見る(コネクトーム vs 次数保存 shuffle)<br>[`poc_video_cube`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_video_cube.py) 動画を空間 × 時間の立方体として見る(Video Summagator の再実装、ハエの脳の断面も同じ op で) |
| 深度 (3) | [`poc_focus_stacking`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_focus_stacking.py) 深度合成(絵は圧勝、深度はゼロ点に負ける場所がある)<br>[`poc_lightfield_depth`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_lightfield_depth.py) ライトフィールドの深度(81 視点は 2 眼に勝てるのか)<br>[`poc_real_stereo_depth`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_stereo_depth.py) 実写のステレオ対で視差と距離を測る(この博物館で初めての実データ) |
| 撮像品質 (3) | [`poc_colormap_readability`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_colormap_readability.py) 疑似カラーの選び方と値の写し方(無い境目を数える / 崖を先に当てる)<br>[`poc_moire_screen`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_moire_screen.py) パネル検査のモアレは「本物のムラ」と区別できるか(打ち消しと窓長)<br>[`poc_veiling_glare`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_veiling_glare.py) 迷光がコントラスト計測を壊す(MTF 合格・黒レベル不合格を同じレンズで作る) |
| 復元 (3) | [`poc_camera_shake_deblur`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_camera_shake_deblur.py) 手ブレ除去はどこまで戻せるか(核が既知でも雑音が上限を決める)<br>[`poc_dehazing`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dehazing.py) 霞除去(律速は大気光ではなく透過率。薄い霞では除霞が害になる)<br>[`poc_real_deblur_honesty`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_deblur_honesty.py) 実写のブレを取る(3 つの物差しに 3 人の勝者/ノブが手法より 4.6 倍効く) |
| 地形 (3) | [`poc_crop_phenotyping`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_crop_phenotyping.py) 作物の葉面積を上から測る(葉が重なると投影が畳む)<br>[`poc_dem_terrain`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dem_terrain.py) 地形を測る(傾斜・水の流れ・日当たりを閉形式と突き合わせる)<br>[`poc_lidar_terrain_change`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_lidar_terrain_change.py) 斜面の土量を測る(縦に引くか法線で測るか、そして合わせすぎの罠) |
| 読み取り (2) | [`poc_barcode_1d`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_barcode_1d.py) 1 次元バーコードが読めなくなる境界(誤読と読み取り不能を分けて数える)<br>[`poc_matrix_code_reading`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_matrix_code_reading.py) 2 値マトリクスコードの読取限界(何画素あれば読めるか) |
| detection (2) | [`poc_real_defect_floor`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_defect_floor.py) 薄い欠陥はどこまで見えるか(実写の地に真値を仕込んで検出限界を測る)<br>[`poc_search_sweep_width`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_search_sweep_width.py) 捜索救難の走査幅(画像から測った 1 本の数字が計画を決める) |
| 改ざん検出 (2) | [`poc_forensics_roc`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_forensics_roc.py) 画像改ざん検出の ROC(保存ボタン 1 回で何が消えるか)<br>[`poc_fresco_craquelure`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_fresco_craquelure.py) 絵画のひび割れ網(壊れるのは分岐次数だけ) |
| inspection (2) | [`poc_em_second_opinion`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_em_second_opinion.py) EM 連結体校正のセカンドオピニオン(膜はラベルの境界にしか無いはず)<br>[`poc_print_layer_inspection`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_print_layer_inspection.py) 3D プリンタの層検査(形 → 層 → 経路 → 画像 の往復を自分で閉じ、仕込んだ欠陥を数字で捕まえる) |
| 形態 (2) | [`poc_bilateral_asymmetry`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bilateral_asymmetry.py) 左右非対称性の定量(対称面そのものが変形に引きずられる)<br>[`poc_vessel_network`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_vessel_network.py) 血管網を抜いて分岐を測る(ヒゲ、分岐近傍の径の過大、指数の脆さ) |
| optics (2) | [`poc_compound_eye`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_compound_eye.py) ハエの複眼は光場センサ(神経重ね合わせで「重ねると頑健」を光学で測る)<br>[`poc_fly_vision`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_fly_vision.py) ハエの視覚前段を op の連鎖で(合成の空を回る/前進すると何が読めて何が読めないか) |
| perception_templates (2) | [`poc_bev_sensor_fusion`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bev_sensor_fusion.py) 鳥瞰図への多センサ融合(px で合格の校正が、遠くでは長さになる)<br>[`poc_safety_clearance`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_safety_clearance.py) 人と機械の安全距離(「近い」を測る点を置き換えると危険が消える) |
| 測距 (2) | [`poc_dtof_ranging`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dtof_ranging.py) 光子計数 dToF の距離精度(理論限界に乗るか、どこで崩れるか)<br>[`poc_leak_localization`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_leak_localization.py) 音で漏水を位置決めする(音速を誤ると掘る場所がずれる) |
| shape_descriptors (2) | [`poc_real_texture_invariance`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_texture_invariance.py) 実写テクスチャを回す(回転不変は等方な素材でだけ成り立つ)<br>[`poc_rotation_invariance_audit`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_rotation_invariance_audit.py) 「回転しても同じ」と言える量はどれか(実写の硬貨を 72 角度で監査) |
| signal_processing (2) | [`poc_rail_corrugation`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_rail_corrugation.py) レールの波状摩耗を弦で測る(伝達関数が 0 になる波長は 0 mm と出る)<br>[`poc_web_roll_periodicity`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_web_roll_periodicity.py) 搬送ロールの傷を周期から名指しする(崖に着く前に何も言えなくなる) |
| verification (2) | [`poc_glyph_typo_detection`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_glyph_typo_detection.py) 画像の誤字を認識せずに見つけて直す(正しい文字列を入力で貰う)<br>[`poc_larval_connectome_reservoir`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_larval_connectome_reservoir.py) 幼虫コネクトームを reservoir にして数字を読む(配線は効いていない) |
| 振動 (2) | [`poc_beam_modal_video`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_beam_modal_video.py) 動画からのモード同定(f は当たる、ζ が先に嘘をつく)<br>[`poc_motion_magnification`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_motion_magnification.py) モーション拡大の振幅精度(拡大は測るための道具か) |
| 色 (1) | [`poc_white_balance`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_white_balance.py) 色恒常性(どの手法にも「効く条件」があり、勝ち続ける手法は無い) |
| imgmetrics (1) | [`poc_spc`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_spc.py) 統計的工程管理を op の連鎖で(検査計測が管理下か・能力があるか) |
| 正対化 (1) | [`poc_document_scan`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_document_scan.py) 書類スキャンの台形補正と影除去(良いところ取りは無い) |
| 断層 (1) | [`poc_ct_fidelity`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_fidelity.py) CT 再構成の忠実度(投影数を減らすとどこで壊れるか) |
| 超解像 (1) | [`poc_superresolution_limits`](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_superresolution_limits.py) 超解像は情報を増やすか(単一画像では増えない) |

<!-- poc-index:end -->

<!-- ops-index:start -->

## オペレータを探す

**2,193 本の op ノート**(呼び出し方・型の契約・HALCON 対応・文献・来歴)と **58 本の族ガイド**があります。次元ごとの入口:

**網羅の実測**: 進化 op 932/932、型つき台帳 1240/1252、1 行ファサード `fullseye.<名前>` 596/1245。**ファサード側はまだ半分**(残りは補助関数・クラス・再輸出モジュール)。

**ノートの中身の実測**: 2198 本のうち、実行できる例が付いているのは **2132 本**(66 本は例ゼロ)、使い方の説明が 120 字以上あるのは **2147 本**(51 本は 1 行の要約だけ)。構造(呼び出し・型・次に繋がる op)は 2198 本すべてにある。

| 次元 | op 数 | 入口 |
|---|---:|---|
| `2d` — 進化する 2-D op(`fullseye.op.<名前>`) | 949 | [INDEX](ops/2d/INDEX.md) |
| `3d` — 点群 / メッシュ / 体積 / SDF / 6-DoF | 372 | [INDEX](ops/3d/INDEX.md) |
| `optics` — レンズ・収差・光線追跡・照明設計 | 131 | [INDEX](ops/optics/INDEX.md) · [ガイド](ops/optics/guides/optics_imaging.md) |
| `math` — 数値・線形代数 | 55 | [INDEX](ops/math/INDEX.md) · [ガイド](ops/math/guides/math_metrology.md) |
| `annotate` — 図注(軸・凡例・注記) | 51 | [INDEX](ops/annotate/INDEX.md) · [ガイド](ops/annotate/guides/figure_annotation.md) |
| `gfx2d` — 描画 | 44 | [INDEX](ops/gfx2d/INDEX.md) |
| `oned` | 42 | [INDEX](ops/oned/INDEX.md) |
| `reprconv` — 表現の橋渡し(型と型のあいだ) | 42 | [INDEX](ops/reprconv/INDEX.md) |
| `generative` | 30 | [INDEX](ops/generative/INDEX.md) · [ガイド](ops/generative/guides/generative_art.md) |
| `conngraph` | 28 | [INDEX](ops/conngraph/INDEX.md) · [ガイド](ops/conngraph/guides/conngraph.md) |
| `piv` — 粒子画像流速測定 + DIC | 26 | [INDEX](ops/piv/INDEX.md) · [ガイド](ops/piv/guides/piv_displacement.md) |
| `dem` — 地形 | 25 | [INDEX](ops/dem/INDEX.md) · [ガイド](ops/dem/guides/dem_terrain_analysis.md) |
| `imgmetrics` — 画質の指標 | 24 | [INDEX](ops/imgmetrics/INDEX.md) · [ガイド](ops/imgmetrics/guides/image_difference_metrics.md) |
| `printpath` | 23 | [INDEX](ops/printpath/INDEX.md) · [ガイド](ops/printpath/guides/printpath.md) |
| `acoustics` — 音響 | 20 | [INDEX](ops/acoustics/INDEX.md) · [ガイド](ops/acoustics/guides/acoustic_condition_monitoring.md) |
| `quat` — 四元数・単元信号 | 19 | [INDEX](ops/quat/INDEX.md) · [ガイド](ops/quat/guides/quaternion_monogenic.md) |
| `lightfield` — ライトフィールド | 17 | [INDEX](ops/lightfield/INDEX.md) · [ガイド](ops/lightfield/guides/lightfield_depth.md) |
| `photon` — 光子計数 / dToF | 17 | [INDEX](ops/photon/INDEX.md) · [ガイド](ops/photon/guides/photon_timeresolved.md) |
| `tomography` — 断層 | 17 | [INDEX](ops/tomography/INDEX.md) |
| `flyvision` | 16 | [INDEX](ops/flyvision/INDEX.md) · [ガイド](ops/flyvision/guides/fly_vision.md) |
| `imgforensics` — 改ざん検出 | 16 | [INDEX](ops/imgforensics/INDEX.md) |
| `shape2d` — 2-D の形の記述とワープ | 16 | [INDEX](ops/shape2d/INDEX.md) · [ガイド](ops/shape2d/guides/shape_description_2d.md) |
| `shapestat` — 形態統計 | 16 | [INDEX](ops/shapestat/INDEX.md) · [ガイド](ops/shapestat/guides/shape_statistics.md) |
| `videostream` — 動画ストリーム | 16 | [INDEX](ops/videostream/INDEX.md) · [ガイド](ops/videostream/guides/video_streaming.md) |
| `astrostack` — 天体スタック | 14 | [INDEX](ops/astrostack/INDEX.md) |
| `live4d` | 14 | [INDEX](ops/live4d/INDEX.md) · [ガイド](ops/live4d/guides/live4d.md) |
| `measure1d` — サブピクセル計測 | 14 | [INDEX](ops/measure1d/INDEX.md) · [ガイド](ops/measure1d/guides/subpixel_measuring.md) |
| `spc` | 14 | [INDEX](ops/spc/INDEX.md) |
| `specular` — 鏡面分離 | 13 | [INDEX](ops/specular/INDEX.md) · [ガイド](ops/specular/guides/specular_photometric.md) |
| `profile` — 断面形状 | 12 | [INDEX](ops/profile/INDEX.md) · [ガイド](ops/profile/guides/profile_metrology.md) |
| `colortransport` — 色の輸送 | 11 | [INDEX](ops/colortransport/INDEX.md) |
| `volcolor` — 体積の色 | 11 | [INDEX](ops/volcolor/INDEX.md) |
| `blob` — 2-D の連結成分解析 | 10 | [INDEX](ops/blob/INDEX.md) · [ガイド](ops/blob/guides/blob_analysis.md) |
| `llmcore` | 10 | [INDEX](ops/llmcore/INDEX.md) · [ガイド](ops/llmcore/guides/llmcore.md) |
| `geocam` | 9 | [INDEX](ops/geocam/INDEX.md) · [ガイド](ops/geocam/guides/geocam.md) |
| `interferometry` — 干渉計 | 9 | [INDEX](ops/interferometry/INDEX.md) · [ガイド](ops/interferometry/guides/coherence_scanning.md) |
| `motionmag` — モーション拡大 | 9 | [INDEX](ops/motionmag/INDEX.md) · [ガイド](ops/motionmag/guides/motion_magnification.md) |
| `rangedoppler` — FMCW レンジドップラー | 8 | [INDEX](ops/rangedoppler/INDEX.md) · [ガイド](ops/rangedoppler/guides/fmcw_range_doppler.md) |
| `emproof` | 7 | [INDEX](ops/emproof/INDEX.md) · [ガイド](ops/emproof/guides/emproof.md) |
| `roughness` — 表面粗さ | 6 | [INDEX](ops/roughness/INDEX.md) · [ガイド](ops/roughness/guides/surface_roughness.md) |
| `videocube` | 6 | [INDEX](ops/videocube/INDEX.md) · [ガイド](ops/videocube/guides/videocube.md) |
| `cadmap` — CAD 対応づけ | 4 | [INDEX](ops/cadmap/INDEX.md) |

名前で引くなら `py -3.11 imgevolve.py ops --search edge`、全 op の対応表は [OP_CATALOG.md](OP_CATALOG.md)、次元をまたぐ入口は [ops/INDEX.md](ops/INDEX.md)。

**AI から引くなら**: 機械可読の索引 [`OP_INDEX.json`](OP_INDEX.json)、使い方は [AI_RAG_GUIDE.md](AI_RAG_GUIDE.md)(`pip install fullseye[rag]` → `fullseye-rag search "エッジ"`、Claude Code なら `py -3.11 tools/setup_claude_rag.py`)。

<!-- ops-index:end -->

## 使い方（ユーザー向け・まずこの 4 つ）

| ドキュメント | 内容 |
|---|---|
| **[GETTING_STARTED.md](GETTING_STARTED.md)** | 5 分ではじめる: インストール → 最初のパイプライン → Studio/CLI/コードで実行 → 結果を見る |
| **[INSTALL.md](INSTALL.md)** | 環境構築の完全ガイド: 前提・`pip install -e .` と extras の使い分け・Windows/Linux インストーラ・最小構成/組み込み・トラブルシュート |
| **[STUDIO_GUIDE.md](STUDIO_GUIDE.md)** | Fullseye Studio 完全ガイド: 3 パネル・オペレータブラウザ・ステップ実行・つまみ・Inspector・知覚パネル・Command palette・ショートカット・Export |
| **[ENGINE.md](ENGINE.md)** | FullseyeEngine（設計 → 実行）: 全メソッド・Python からの利用・CLI `run`・他プロジェクトからの呼び出し |

---

## オペレータ / API リファレンス

| ドキュメント | 内容 |
|---|---|
| [OPERATORS.md](OPERATORS.md) | 全 897 オペレータのカタログ（48 カテゴリ、sort 別、HALCON/OpenCV/scikit-image/MATLAB の対応 API） |
| [EXAMPLES.md](EXAMPLES.md) | オペレータ別のサンプルコード（他ライブラリとの等価呼び出し付き） |
| [OP_INDEX.json](OP_INDEX.json) | 機械可読なオペレータ索引（`imgevolve.py index` で再生成） |
| [ADDING_OPS.md](ADDING_OPS.md) | 新しいオペレータの追加方法（進化・codegen・カタログ・索引が自動追従） |
| [../examples/README.md](../examples/README.md) | 実行可能なエンドツーエンドのサンプルスクリプト集 |

## 知覚スタック（ロボティクス/ビジョン）

| ドキュメント | 内容 |
|---|---|
| [PERCEPTION.md](PERCEPTION.md) | 知覚スタック 1 枚リファレンス（stereo / terrain / detect / registration / pose / flow / motion） |
| [PERCEPTION_REALDATA.md](PERCEPTION_REALDATA.md) | 実写クリップでの計測結果（ビデオ I/O + honest な実測値） |

## HALCON パリティ / 被覆（honest disclosure）

| ドキュメント | 内容 |
|---|---|
| [HALCON_PARITY.md](HALCON_PARITY.md) | 「名前だけ」でなく実際に同じ処理ができるかの genuine 実装状況（980/2313） |
| [HALCON_COVERAGE.md](HALCON_COVERAGE.md) | 公式リファレンス（v2605）を実スクレイプした被覆計測 |
| [LIB_COVERAGE.md](LIB_COVERAGE.md) | 多ライブラリ横断被覆（HALCON 以外の distinctive op 取り込み） |
| [PARITY_CROSSBACKEND.md](PARITY_CROSSBACKEND.md) | 独立実装（scipy/cv2/skimage）同士のクロスバックエンド一致による parity 実証 |

## 品質 / 来歴 / 再現

| ドキュメント | 内容 |
|---|---|
| [ACCURACY_BENCH.md](ACCURACY_BENCH.md) | 進化 champion vs null（holdout）の常設精度テーブル |
| [CHAIN_FUZZ.md](CHAIN_FUZZ.md) | 連鎖ファザー（op を鎖にして揺さぶる第三の品質保証層。拡散→収束→最小再現） |
| [EVOLUTION_ENVIRONMENT.md](EVOLUTION_ENVIRONMENT.md) | 進化型アルゴリズム開発環境（拡散→収縮→昇格。counterfactual utility ゲートと 2 つの op 宇宙の橋） |
| [PROVENANCE.md](PROVENANCE.md) | 公開アルゴリズムからの自作である旨の来歴 |
| [REFERENCES.md](REFERENCES.md) | 各オペレータの文献的裏付け |
| [REPRODUCE.md](REPRODUCE.md) | seed 駆動・決定論的な数値の再現手順 |
| [STATUS.md](STATUS.md) | プロジェクトの現在地・計画（plan_ref） |

## リリースノート / 設計

| ドキュメント | 内容 |
|---|---|
| [V13.md](V13.md) | v13 = 実用化 + クロスプロジェクト packaging + 知覚スタック |
| [V14.md](V14.md) | v14 = 知覚スタック完成（モーション + 堅牢化） |
| [STUDIO_UX.md](STUDIO_UX.md) | Fullseye Studio の UX/デザイン改善の意図と背景 |

---

## クイックコマンド

```powershell
py -3.11 -m pip install -e ".[opencv,gui]"     # 導入（画像 I/O + Studio）
py -3.11 studio.py                              # Fullseye Studio を起動（= fullseye-studio）
py -3.11 imgevolve.py ops --search edge         # オペレータ検索（= fullseye ops --search edge）
py -3.11 imgevolve.py apply gauss_filter in.png out.png --a 0.6
py -3.11 imgevolve.py run pipeline.json in.png --out result.png
py -3.11 imgevolve.py coverage                  # honest な被覆数
```

Python から:

```python
import fullseye, numpy as np
out = fullseye.run_pipeline(frame, ["gaussian", "sobel_amp", "otsu"])
eng = fullseye.FullseyeEngine.load("pipeline.json"); result = eng.run(frame)
```

---

![古典的な 2-D ビジョン op の実出力](articles/assets/vision_ops_montage.png)

*古典的な 2-D ビジョン op の実出力*

![Physical AI とセンサ模倣の実出力](articles/assets/physical_ai_montage.png)

*Physical AI とセンサ模倣の実出力*

<!-- docmap:start -->

## ドキュメント地図 — 全 212 本

**索引から 1 本も辿れない文書を作らない**ための全体地図です(`docs/ops/` の op ノート 2,193 本と族ガイド 58 本は上の「オペレータを探す」から、記事は [articles/](articles/README.md) から辿れます)。到達できない文書が 1 本でもあれば `tests/test_docs_index_reachable.py` が落ちます。**本文はほとんどが日本語**です。

**はじめに・使い方**(12)

| 文書 | 内容 |
|---|---|
| [`GETTING_STARTED.md`](GETTING_STARTED.md) | はじめかた（5分で動かす） |
| [`INSTALL.md`](INSTALL.md) | インストール / 環境構築 完全ガイド |
| [`STUDIO_GUIDE.md`](STUDIO_GUIDE.md) | Fullseye Studio 完全ガイド |
| [`STUDIO_UX.md`](STUDIO_UX.md) | Fullseye Studio — UX & design pass (v15) |
| [`EXAMPLES.md`](EXAMPLES.md) | imgevolve — sample code (cross-library recipes) |
| [`EXAMPLES_3D.md`](EXAMPLES_3D.md) | Fullseye 3-D ビジョン — 事例ギャラリー(EXAMPLES_3D) |
| [`GALLERY.md`](GALLERY.md) | Fullseye ギャラリー / Gallery |
| [`REPRODUCE.md`](REPRODUCE.md) | Reproducing the numbers |
| [`CONSUMER_APPLICATIONS.md`](CONSUMER_APPLICATIONS.md) | Fullseye — per-project applications (honest, 2026-08-15) |
| [`3DGS_USAGE.md`](3DGS_USAGE.md) | Fullseye 3DGS ― 使い方(1コマンド) |
| [`TERRAIN_WALK.md`](TERRAIN_WALK.md) | 地形の上を歩かせる(sim-native, GPU 不要) |
| [`GSPLAT_NATIVE_WINDOWS.md`](GSPLAT_NATIVE_WINDOWS.md) | gsplat native を Windows(RTX 5090 / torch cu128)でビルドする — 実証済み手順 |

**オペレータのリファレンス**(9)

| 文書 | 内容 |
|---|---|
| [`OPERATORS.md`](OPERATORS.md) | imgevolve — cross-library operator catalog |
| [`OP_CATALOG.md`](OP_CATALOG.md) | Fullseye Operator Catalog — AI capability ledger |
| [`OP_COMBINATION_MATRIX.md`](OP_COMBINATION_MATRIX.md) | fullseye 3D op × op 組み合わせマトリクス(実現性 × 差別化で優先度化) |
| [`CONVERSION_MATRIX.md`](CONVERSION_MATRIX.md) | 型変換の行列 ―― 穴と不具合の点検 |
| [`CONNECTIVITY.md`](CONNECTIVITY.md) | Fullseye connectivity — devices, cameras & industrial protocols |
| [`MATCH_3D_MATRIX.md`](MATCH_3D_MATRIX.md) | fullseye 3D ビジョン・ツールキット(Physical AI 向け、HALCON/OpenCV 差別化) |
| [`GENERAL_ALGORITHMS.md`](GENERAL_ALGORITHMS.md) | 汎用アルゴリズムを実装可能にする — algo-c 対応ロードマップ |
| [`ADDING_OPS.md`](ADDING_OPS.md) | Adding an operator |
| [`WAVE0_STABLE_SLOTS.md`](WAVE0_STABLE_SLOTS.md) | Wave-0: stable op slots + name-pinned champions |

**AI から引く(RAG)**(1)

| 文書 | 内容 |
|---|---|
| [`AI_RAG_GUIDE.md`](AI_RAG_GUIDE.md) | Fullseye を AI アシスタントの RAG にする手順(Claude Code 向け) |

**文献層(製造技術の知識 → 使う op)**(5)

| 文書 | 内容 |
|---|---|
| [`literature/INDEX.md`](literature/INDEX.md) | 文献層 —— RAD コーパスからの、op に繋がる来歴つき要約 |
| [`literature/mech_design.md`](literature/mech_design.md) | 文献層: メカ設計(機械設計) |
| [`literature/mechatronics_parts.md`](literature/mechatronics_parts.md) | 文献層: メカトロ部品(アクチュエータ・センサ・電気部品) |
| [`literature/manufacturing_processes.md`](literature/manufacturing_processes.md) | 文献層: 製造工程(あらゆる製造技術の開発に) |
| [`literature/OSS_LANDSCAPE.md`](literature/OSS_LANDSCAPE.md) | 既存 OSS の地図 —— すでにある道具と、Fullseye との繋ぎ方 |

**知覚・センサ**(7)

| 文書 | 内容 |
|---|---|
| [`PERCEPTION.md`](PERCEPTION.md) | Fullseye perception stack — one-page reference |
| [`PERCEPTION_PHYSICAL_AI.md`](PERCEPTION_PHYSICAL_AI.md) | Physical-AI perception pipeline (fullseye / imgevolve, v18.3, 2026-08-15) |
| [`PERCEPTION_REALDATA.md`](PERCEPTION_REALDATA.md) | v15 — perception stack on real footage (video I/O + honest field measurements) |
| [`SENSOR_PLAYBOOK.md`](SENSOR_PLAYBOOK.md) | Fullseye Sensor Playbook — センサー種別ごとの推奨 op パイプライン |
| [`HIGHSPEED_VISION.md`](HIGHSPEED_VISION.md) | 高速ビジョン(1ms 視覚フィードバック)を物理シミュ上でやる — 計画 |
| [`SAMPLE_IMAGE_REFERENCES.md`](SAMPLE_IMAGE_REFERENCES.md) | Sample images — provenance, source papers & public repositories |
| [`BBB_SENSING.md`](BBB_SENSING.md) | BBB sensing — 複眼光場 × コネクトーム(研究方向) |

**HALCON との対応**(6)

| 文書 | 内容 |
|---|---|
| [`HALCON_PARITY.md`](HALCON_PARITY.md) | HALCON parity — what imgevolve genuinely DOES (not just names) |
| [`HALCON_COVERAGE.md`](HALCON_COVERAGE.md) | HALCON operator coverage (measured vs the real reference) |
| [`HALCON_COVERAGE_HONEST.md`](HALCON_COVERAGE_HONEST.md) | HALCON カバレッジ — honest な分母(2026-08-18 更新) |
| [`HDEVELOP_FIDELITY.md`](HDEVELOP_FIDELITY.md) | Fullseye Studio — HDevelop 忠実化スペック(北極星) |
| [`HDEVELOP_DEV_OPS.md`](HDEVELOP_DEV_OPS.md) | HDevelop `dev_*` operator family — the UI/display control surface (Studio 北極星) |
| [`LIB_COVERAGE.md`](LIB_COVERAGE.md) | Multi-library coverage (imgevolve is not HALCON-only) |

**Fullseye Script**(3)

| 文書 | 内容 |
|---|---|
| [`FSCRIPT_DECISION.md`](FSCRIPT_DECISION.md) | Fullseye Script / Runtime — 要件定義と基本設計(確定案) |
| [`FSCRIPT_LANGUAGE.md`](FSCRIPT_LANGUAGE.md) | Fullseye Script — 言語 / ランタイム / ウォッチ IDE 設計仕様(北極星) |
| [`FSCRIPT_MEASUREMENTS.md`](FSCRIPT_MEASUREMENTS.md) | Fullseye Runtime — 実測記録 (2026-08-15) |

**品質・正直さ**(11)

| 文書 | 内容 |
|---|---|
| [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md) | Known Issues — 実データ横断テストで発見(2026-08-30) |
| [`STATUS.md`](STATUS.md) | imgevolve — status / plan (plan_ref) |
| [`ACCURACY_BENCH.md`](ACCURACY_BENCH.md) | Accuracy benchmark — champion vs null (holdout) |
| [`BENCH_VS_OPENCV.md`](BENCH_VS_OPENCV.md) | imgevolve GPU op vs OpenCV(CPU)処理速度ベンチ |
| [`PARITY_CROSSBACKEND.md`](PARITY_CROSSBACKEND.md) | Cross-backend parity — independent implementations agree at the tested points |
| [`CHAIN_FUZZ.md`](CHAIN_FUZZ.md) | 連鎖ファザー(chain fuzz)— op を鎖にして揺さぶる第三の品質保証層 |
| [`PROVENANCE.md`](PROVENANCE.md) | Provenance |
| [`REFERENCES.md`](REFERENCES.md) | imgevolve — operator research provenance |
| [`AUDIT_2026_08_12.md`](AUDIT_2026_08_12.md) | imgevolve implementation audit — 2026-08-12 |
| [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) | リリース手順書 — 同じ間違いを繰り返さないための門 |
| [`I18N.md`](I18N.md) | Fullseye の多言語対応 — 全体設計 / Internationalisation design |

**性能・GPU**(4)

| 文書 | 内容 |
|---|---|
| [`GPU_ACCEL_PLAN.md`](GPU_ACCEL_PLAN.md) | op の GPU 化ロードマップ(E2E の本丸) |
| [`GPU_OPTIMIZATION_PATTERNS.md`](GPU_OPTIMIZATION_PATTERNS.md) | GPU 最適化デザインパターン・カタログ(RTX 5090 / Blackwell sm_120 向け) |
| [`design/FAST_TWINS.md`](design/FAST_TWINS.md) | CPU 高速 twin(`fast.py`)— 実装記録と実測(2026-09-03) |
| [`design/PERF_MEMORY_VIDEO_SURVEY.md`](design/PERF_MEMORY_VIDEO_SURVEY.md) | op の高速化・省メモリ化・動画処理 — 実測にもとづく調査報告(2026-09-03) |

**設計・アーキテクチャ**(7)

| 文書 | 内容 |
|---|---|
| [`ENGINE.md`](ENGINE.md) | FullseyeEngine — 設計したパイプラインを実行するランタイム |
| [`EVOLUTION_ENVIRONMENT.md`](EVOLUTION_ENVIRONMENT.md) | 進化型アルゴリズム開発環境 — 拡散・収縮・昇格 |
| [`INTEGRATION.md`](INTEGRATION.md) | Depending on Fullseye from another project (stability contract) |
| [`UNIFIED_API_REQUIREMENTS.md`](UNIFIED_API_REQUIREMENTS.md) | Fullseye 統一インターフェース — 要件定義書 (v0.1, 2026-08-18) |
| [`design/TRIZ_DESIGN_PATTERN_MATRIX.md`](design/TRIZ_DESIGN_PATTERN_MATRIX.md) | TRIZ 40 発明原理 × ソフトウェア設計パターン × コンテナ型 — 構造選択マトリクス(fullseye) |
| [`EVIS_VISION_OSS_GAP.md`](EVIS_VISION_OSS_GAP.md) | evis の視覚部品 — OSS/ROS2 ギャップ分析 (2026-08-17) |
| [`INDUSTRY_SIGNALS.md`](INDUSTRY_SIGNALS.md) | 業界シグナル — 展示会・アワードを op 発想の恒常的な入力にする |

**作業記録・計画(履歴。**その日付時点の値**で、いまの値ではない)**(12)

| 文書 | 内容 |
|---|---|
| [`V13.md`](V13.md) | v13 — production hardening, cross-project packaging, perception stack |
| [`V14.md`](V14.md) | v14 — perception-stack completion: motion + robustness |
| [`SESSION_SUMMARY.md`](SESSION_SUMMARY.md) | Session Summary (auto-generated) |
| [`SESSION_2026_08_14.md`](SESSION_2026_08_14.md) | Session 2026-08-14 — Data-format expansion + Studio UI review |
| [`STUDIO_REVIEW_2026_08_14.md`](STUDIO_REVIEW_2026_08_14.md) | Fullseye Studio — verified UI review (2026-08-14) |
| [`NEXT_SESSION.md`](NEXT_SESSION.md) | 次セッション引き継ぎ — 高速化・省メモリ・動画 + 解像度管理 + 図注(2026-09-03 午前〜) |
| [`NEXT_OPS_PLAN_2026-08-31.md`](NEXT_OPS_PLAN_2026-08-31.md) | 次期 op 拡張計画(2026-08-31 調査、v0.1.4 リリース直後) |
| [`PLAN_0_1_9.md`](PLAN_0_1_9.md) | 0.1.9 → 0.1.10 の作業計画 |
| [`ARTICLE_INTEGRATION_TODO.md`](ARTICLE_INTEGRATION_TODO.md) | 記事への反映待ち(2026-09-02、可視化ウィング作業から) |
| [`ARTICLE_RESTRUCTURE_PLAN.md`](ARTICLE_RESTRUCTURE_PLAN.md) | Qiita 記事の章構成 組み替え計画(2026-09-02 起票 / **同日 実施済み** = commit 32e47171) |
| [`ARTICLE_GPU_SHAPEMATCH.md`](ARTICLE_GPU_SHAPEMATCH.md) | 記事材料: 形状マッチングを GPU に載せる —— 勾配方向スコアの conv2d 定式化 |
| [`FULLSEYE_OP_ARTICLE_SPEC.md`](FULLSEYE_OP_ARTICLE_SPEC.md) | Fullseye op カタログ画像・専用記事 仕様書(第 2 陣企画書) |

**そのほか**(135)

| 文書 | 内容 |
|---|---|
| [`3DGS_USAGE.de.md`](3DGS_USAGE.de.md) | Fullseye 3DGS – Anwendung (ein einziger Befehl) |
| [`3DGS_USAGE.en.md`](3DGS_USAGE.en.md) | Fullseye 3DGS — how to use it (one command) |
| [`3DGS_USAGE.ko.md`](3DGS_USAGE.ko.md) | Fullseye 3DGS — 사용법(명령어 한 줄) |
| [`3DGS_USAGE.tw.md`](3DGS_USAGE.tw.md) | Fullseye 3DGS —— 使用方法（一行指令） |
| [`3DGS_USAGE.zh.md`](3DGS_USAGE.zh.md) | Fullseye 3DGS —— 使用方法（单条命令） |
| [`AI_RAG_GUIDE.de.md`](AI_RAG_GUIDE.de.md) | Fullseye als RAG eines KI-Assistenten nutzen (für Claude Code) |
| [`AI_RAG_GUIDE.en.md`](AI_RAG_GUIDE.en.md) | Using Fullseye as an AI assistant's RAG (for Claude Code) |
| [`AI_RAG_GUIDE.ko.md`](AI_RAG_GUIDE.ko.md) | Fullseye를 AI 어시스턴트의 RAG로 사용하는 방법(Claude Code용) |
| [`AI_RAG_GUIDE.tw.md`](AI_RAG_GUIDE.tw.md) | 將 Fullseye 用作 AI 助理 RAG 的方法（針對 Claude Code） |
| [`AI_RAG_GUIDE.zh.md`](AI_RAG_GUIDE.zh.md) | 将 Fullseye 用作 AI 助手 RAG 的方法（面向 Claude Code） |
| [`BENCH_VS_OPENCV.en.md`](BENCH_VS_OPENCV.en.md) | imgevolve GPU op vs OpenCV (CPU) throughput benchmark |
| [`CAPABILITIES.en.md`](CAPABILITIES.en.md) | What Fullseye can do |
| [`CAPABILITIES.md`](CAPABILITIES.md) | Fullseye でできること |
| [`CHAIN_FUZZ.en.md`](CHAIN_FUZZ.en.md) | Chain Fuzzer (chain fuzz) — a third quality-assurance layer that shakes ops by wiring them into chains |
| [`DESIGN_NOTES.de.md`](DESIGN_NOTES.de.md) | Fullseye-Entwurfsnotizen (aus den ★-Kommentaren im Quellcode erzeugt) |
| [`DESIGN_NOTES.en.md`](DESIGN_NOTES.en.md) | Fullseye design notes (generated from the ★ comments in the source) |
| [`DESIGN_NOTES.ko.md`](DESIGN_NOTES.ko.md) | Fullseye 설계 판단 모음(소스의 ★ 주석에서 생성) |
| [`DESIGN_NOTES.md`](DESIGN_NOTES.md) | Fullseye 設計判断集(ソース中の ★ コメントから生成) |
| [`DESIGN_NOTES.tw.md`](DESIGN_NOTES.tw.md) | Fullseye 設計判斷集（由原始碼中的 ★ 註解產生） |
| [`DESIGN_NOTES.zh.md`](DESIGN_NOTES.zh.md) | Fullseye 设计判断集（由源码中的 ★ 注释生成） |
| [`ENGINE.de.md`](ENGINE.de.md) | FullseyeEngine — Laufzeitumgebung zur Ausführung entworfener Pipelines |
| [`ENGINE.en.md`](ENGINE.en.md) | FullseyeEngine — the runtime that executes a pipeline you designed |
| [`ENGINE.ko.md`](ENGINE.ko.md) | FullseyeEngine — 설계한 파이프라인을 실행하는 런타임 |
| [`ENGINE.tw.md`](ENGINE.tw.md) | FullseyeEngine — 執行已設計管線的執行環境 |
| [`ENGINE.zh.md`](ENGINE.zh.md) | FullseyeEngine — 运行已设计管道的运行时 |
| [`EVIS_VISION_OSS_GAP.en.md`](EVIS_VISION_OSS_GAP.en.md) | evis Vision Components — OSS/ROS2 Gap Analysis (2026-08-17) |
| [`EVOLUTION_ENVIRONMENT.en.md`](EVOLUTION_ENVIRONMENT.en.md) | Evolutionary Algorithm Development Environment — Expand, Contract, Promote |
| [`FSCRIPT_LANGUAGE.en.md`](FSCRIPT_LANGUAGE.en.md) | Fullseye Script — Language / Runtime / Watch IDE Design Specification (North Star) |
| [`GALLERY.en.md`](GALLERY.en.md) | Fullseye Gallery |
| [`GENERAL_ALGORITHMS.de.md`](GENERAL_ALGORITHMS.de.md) | Allgemeine Algorithmen implementierbar machen — algo-c Kompatibilitäts-Roadmap |
| [`GENERAL_ALGORITHMS.en.md`](GENERAL_ALGORITHMS.en.md) | Making general algorithms implementable — the algo-c support roadmap |
| [`GENERAL_ALGORITHMS.ko.md`](GENERAL_ALGORITHMS.ko.md) | 범용 알고리즘을 구현 가능하게 만들기 — algo-c 대응 로드맵 |
| [`GENERAL_ALGORITHMS.tw.md`](GENERAL_ALGORITHMS.tw.md) | 讓通用演算法也能實作 — algo-c 對應路線圖 |
| [`GENERAL_ALGORITHMS.zh.md`](GENERAL_ALGORITHMS.zh.md) | 让通用算法也能实现 — algo-c 对应路线图 |
| [`GETTING_STARTED.de.md`](GETTING_STARTED.de.md) | Erste Schritte (in 5 Minuten startklar) |
| [`GETTING_STARTED.en.md`](GETTING_STARTED.en.md) | Getting started (running in 5 minutes) |
| [`GETTING_STARTED.ko.md`](GETTING_STARTED.ko.md) | 시작하기 (5분 만에 실행하기) |
| [`GETTING_STARTED.tw.md`](GETTING_STARTED.tw.md) | 快速上手（5 分鐘跑起來） |
| [`GETTING_STARTED.zh.md`](GETTING_STARTED.zh.md) | 快速上手（5 分钟运行起来） |
| [`GPU_OPTIMIZATION_PATTERNS.en.md`](GPU_OPTIMIZATION_PATTERNS.en.md) | GPU Optimization Design-Pattern Catalog (for RTX 5090 / Blackwell sm_120) |
| [`GSPLAT_NATIVE_WINDOWS.en.md`](GSPLAT_NATIVE_WINDOWS.en.md) | Building native gsplat on Windows (RTX 5090 / torch cu128) — a proven procedure |
| [`HALCON_COVERAGE_HONEST.en.md`](HALCON_COVERAGE_HONEST.en.md) | HALCON Coverage — the honest denominator (updated 2026-08-18) |
| [`HARDENING.en.md`](HARDENING.en.md) | What the PoCs hardened — found, fixed, and gated |
| [`HARDENING.md`](HARDENING.md) | PoC が上げた堅牢性 —— 見つけて直した記録 |
| [`HDEVELOP_DEV_OPS.en.md`](HDEVELOP_DEV_OPS.en.md) | HDevelop `dev_*` operator family — the UI/display control surface (Studio north star) |
| [`HDEVELOP_FIDELITY.en.md`](HDEVELOP_FIDELITY.en.md) | Fullseye Studio — HDevelop Fidelity Spec (North Star) |
| [`I18N_PLAN.md`](I18N_PLAN.md) | 完全な多言語化 — 計画と現在地 |
| [`INSTALL.de.md`](INSTALL.de.md) | Installations- und Einrichtungshandbuch |
| [`INSTALL.en.md`](INSTALL.en.md) | Installation / Environment Setup — Complete Guide |
| [`INSTALL.ko.md`](INSTALL.ko.md) | 설치 / 환경 구축 완전 가이드 |
| [`INSTALL.tw.md`](INSTALL.tw.md) | 安裝 / 環境建置完整指南 |
| [`INSTALL.zh.md`](INSTALL.zh.md) | 安装 / 环境搭建完全指南 |
| [`MATCH_3D_MATRIX.en.md`](MATCH_3D_MATRIX.en.md) | fullseye 3D Vision Toolkit (for Physical AI, differentiating from HALCON/OpenCV) |
| [`MATURITY.md`](MATURITY.md) | 成熟度台帳(Maturity) |
| [`MCP.md`](MCP.md) | Fullseye を MCP(Model Context Protocol)から使う |
| [`OP_COMBINATION_MATRIX.en.md`](OP_COMBINATION_MATRIX.en.md) | fullseye 3D op × op Combination Matrix (prioritized by feasibility × differentiation) |
| [`SAMPLE_IMAGE_REFERENCES.en.md`](SAMPLE_IMAGE_REFERENCES.en.md) | Sample images — provenance, source papers & public repositories |
| [`STUDIO_GUIDE.de.md`](STUDIO_GUIDE.de.md) | Vollständiger Leitfaden zu Fullseye Studio |
| [`STUDIO_GUIDE.en.md`](STUDIO_GUIDE.en.md) | The complete guide to Fullseye Studio |
| [`STUDIO_GUIDE.ko.md`](STUDIO_GUIDE.ko.md) | Fullseye Studio 완전 가이드 |
| [`STUDIO_GUIDE.tw.md`](STUDIO_GUIDE.tw.md) | Fullseye Studio 完全指南 |
| [`STUDIO_GUIDE.zh.md`](STUDIO_GUIDE.zh.md) | Fullseye Studio 完全指南 |
| [`TERRAIN_WALK.en.md`](TERRAIN_WALK.en.md) | Walking a Character Over Terrain (sim-native, no GPU required) |
| [`UNIFIED_API_REQUIREMENTS.en.md`](UNIFIED_API_REQUIREMENTS.en.md) | Fullseye Unified Interface — Requirements Specification (v0.1, 2026-08-18) |
| [`capabilities/align-and-stack.md`](capabilities/align-and-stack.md) | id: align-and-stack |
| [`capabilities/beamforming-and-range-doppler.md`](capabilities/beamforming-and-range-doppler.md) | id: beamforming-and-range-doppler |
| [`capabilities/beats-fringes-and-screens.md`](capabilities/beats-fringes-and-screens.md) | id: beats-fringes-and-screens |
| [`capabilities/blob-and-region.md`](capabilities/blob-and-region.md) | id: blob-and-region |
| [`capabilities/camera-intrinsics-calibration.md`](capabilities/camera-intrinsics-calibration.md) | id: camera-intrinsics-calibration |
| [`capabilities/colour-and-delta-e.md`](capabilities/colour-and-delta-e.md) | id: colour-and-delta-e |
| [`capabilities/complex-plane-fields.md`](capabilities/complex-plane-fields.md) | id: complex-plane-fields |
| [`capabilities/estimate-lens-distortion.md`](capabilities/estimate-lens-distortion.md) | id: estimate-lens-distortion |
| [`capabilities/figures-and-annotation.md`](capabilities/figures-and-annotation.md) | id: figures-and-annotation |
| [`capabilities/fix-text-in-images.md`](capabilities/fix-text-in-images.md) | id: fix-text-in-images |
| [`capabilities/geodetic-frames.md`](capabilities/geodetic-frames.md) | id: geodetic-frames |
| [`capabilities/golden-compare.md`](capabilities/golden-compare.md) | id: golden-compare |
| [`capabilities/inspection-fixture.md`](capabilities/inspection-fixture.md) | id: inspection-fixture |
| [`capabilities/inspection-workflow.md`](capabilities/inspection-workflow.md) | id: inspection-workflow |
| [`capabilities/inverted-colour-overlays.md`](capabilities/inverted-colour-overlays.md) | id: inverted-colour-overlays |
| [`capabilities/lens-distortion-correction.md`](capabilities/lens-distortion-correction.md) | id: lens-distortion-correction |
| [`capabilities/measurement-system-and-uncertainty.md`](capabilities/measurement-system-and-uncertainty.md) | id: measurement-system-and-uncertainty |
| [`capabilities/one-stroke-drawing.md`](capabilities/one-stroke-drawing.md) | id: one-stroke-drawing |
| [`capabilities/optics-and-materials.md`](capabilities/optics-and-materials.md) | id: optics-and-materials |
| [`capabilities/pictures-that-carry-their-own-truth.md`](capabilities/pictures-that-carry-their-own-truth.md) | id: pictures-that-carry-their-own-truth |
| [`capabilities/point-target-detection.md`](capabilities/point-target-detection.md) | id: point-target-detection |
| [`capabilities/polarization-imaging.md`](capabilities/polarization-imaging.md) | id: polarization-imaging |
| [`capabilities/raw-to-display-isp.md`](capabilities/raw-to-display-isp.md) | id: raw-to-display-isp |
| [`capabilities/subpixel-2d-metrology.md`](capabilities/subpixel-2d-metrology.md) | id: subpixel-2d-metrology |
| [`capabilities/terrain-and-visibility.md`](capabilities/terrain-and-visibility.md) | id: terrain-and-visibility |
| [`capabilities/text-and-tables-on-images.md`](capabilities/text-and-tables-on-images.md) | id: text-and-tables-on-images |
| [`capabilities/theorems-as-pictures.md`](capabilities/theorems-as-pictures.md) | id: theorems-as-pictures |
| [`capabilities/tomography-reconstruction.md`](capabilities/tomography-reconstruction.md) | id: tomography-reconstruction |
| [`capabilities/typed-results-as-json.md`](capabilities/typed-results-as-json.md) | id: typed-results-as-json |
| [`capabilities/typed-results-as-markdown.md`](capabilities/typed-results-as-markdown.md) | id: typed-results-as-markdown |
| [`capabilities/vibration-and-acoustics.md`](capabilities/vibration-and-acoustics.md) | id: vibration-and-acoustics |
| [`capabilities/visual-hull-from-silhouettes.md`](capabilities/visual-hull-from-silhouettes.md) | id: visual-hull-from-silhouettes |
| [`capabilities/volume-from-3d-scan.md`](capabilities/volume-from-3d-scan.md) | id: volume-from-3d-scan |
| [`capabilities/what-a-picture-cannot-check.md`](capabilities/what-a-picture-cannot-check.md) | id: what-a-picture-cannot-check |
| [`capabilities/xlsx-report.md`](capabilities/xlsx-report.md) | id: xlsx-report |
| [`hardening/carve-look-at-unreachable-and-silent.md`](hardening/carve-look-at-unreachable-and-silent.md) | id: carve-look-at-unreachable-and-silent |
| [`hardening/cli-help-and-subcommands-broke-in-the-wheel.md`](hardening/cli-help-and-subcommands-broke-in-the-wheel.md) | id: cli-help-and-subcommands-broke-in-the-wheel |
| [`hardening/compactness-saturated-at-one.md`](hardening/compactness-saturated-at-one.md) | id: compactness-saturated-at-one |
| [`hardening/dem-viewshed-self-occlusion.md`](hardening/dem-viewshed-self-occlusion.md) | id: dem-viewshed-self-occlusion |
| [`hardening/dimensional-features-were-normalised.md`](hardening/dimensional-features-were-normalised.md) | id: dimensional-features-were-normalised |
| [`hardening/ecef-to-geodetic-returned-latitude-180.md`](hardening/ecef-to-geodetic-returned-latitude-180.md) | id: ecef-to-geodetic-returned-latitude-180 |
| [`hardening/empty-and-tiny-inputs-raised-raw-library-errors.md`](hardening/empty-and-tiny-inputs-raised-raw-library-errors.md) | id: empty-and-tiny-inputs-raised-raw-library-errors |
| [`hardening/empty-name-resolved-and-narrow-floats-not-upcast.md`](hardening/empty-name-resolved-and-narrow-floats-not-upcast.md) | id: empty-name-resolved-and-narrow-floats-not-upcast |
| [`hardening/engine-load-on-an-instance-was-silently-ignored.md`](hardening/engine-load-on-an-instance-was-silently-ignored.md) | id: engine-load-on-an-instance-was-silently-ignored |
| [`hardening/features-saturated-at-one.md`](hardening/features-saturated-at-one.md) | id: features-saturated-at-one |
| [`hardening/frame-align-inlier-ratio-is-not-confidence.md`](hardening/frame-align-inlier-ratio-is-not-confidence.md) | id: frame-align-inlier-ratio-is-not-confidence |
| [`hardening/functional-gate-did-not-know-the-match-sort.md`](hardening/functional-gate-did-not-know-the-match-sort.md) | id: functional-gate-did-not-know-the-match-sort |
| [`hardening/halcon-named-shape-factors.md`](hardening/halcon-named-shape-factors.md) | id: halcon-named-shape-factors |
| [`hardening/image-io-dropped-write-failures-and-crushed-16-bit.md`](hardening/image-io-dropped-write-failures-and-crushed-16-bit.md) | id: image-io-dropped-write-failures-and-crushed-16-bit |
| [`hardening/inputs-without-a-conversion-were-not-refused.md`](hardening/inputs-without-a-conversion-were-not-refused.md) | id: inputs-without-a-conversion-were-not-refused |
| [`hardening/itk-threshold-ops-returned-the-dark-side.md`](hardening/itk-threshold-ops-returned-the-dark-side.md) | id: itk-threshold-ops-returned-the-dark-side |
| [`hardening/ledger-evicted-silently-and-studio-help-aborted.md`](hardening/ledger-evicted-silently-and-studio-help-aborted.md) | id: ledger-evicted-silently-and-studio-help-aborted |
| [`hardening/ledger-lookups-returned-empty-for-unknown-names.md`](hardening/ledger-lookups-returned-empty-for-unknown-names.md) | id: ledger-lookups-returned-empty-for-unknown-names |
| [`hardening/mcp-facade-layer-listed-classes-as-ops.md`](hardening/mcp-facade-layer-listed-classes-as-ops.md) | id: mcp-facade-layer-listed-classes-as-ops |
| [`hardening/moment-invariants-two-families-same-name.md`](hardening/moment-invariants-two-families-same-name.md) | id: moment-invariants-two-families-same-name |
| [`hardening/nary-ops-unlisted-and-knobs-unstated.md`](hardening/nary-ops-unlisted-and-knobs-unstated.md) | id: nary-ops-unlisted-and-knobs-unstated |
| [`hardening/noise-sigma-mad-collapses-on-quantised-data.md`](hardening/noise-sigma-mad-collapses-on-quantised-data.md) | id: noise-sigma-mad-collapses-on-quantised-data |
| [`hardening/nonfinite-output-was-sanitized-silently.md`](hardening/nonfinite-output-was-sanitized-silently.md) | id: nonfinite-output-was-sanitized-silently |
| [`hardening/op-find-blind-to-japanese-queries.md`](hardening/op-find-blind-to-japanese-queries.md) | id: op-find-blind-to-japanese-queries |
| [`hardening/otsu-threshold-at-the-bin-midpoint.md`](hardening/otsu-threshold-at-the-bin-midpoint.md) | id: otsu-threshold-at-the-bin-midpoint |
| [`hardening/pfm-default-wrote-8-bit-values-into-a-float-format.md`](hardening/pfm-default-wrote-8-bit-values-into-a-float-format.md) | id: pfm-default-wrote-8-bit-values-into-a-float-format |
| [`hardening/pose-helpers-could-not-take-their-own-matrix.md`](hardening/pose-helpers-could-not-take-their-own-matrix.md) | id: pose-helpers-could-not-take-their-own-matrix |
| [`hardening/refract-one-way-reference.md`](hardening/refract-one-way-reference.md) | id: refract-one-way-reference |
| [`hardening/run-pipeline-stage-forms-fail-obscurely.md`](hardening/run-pipeline-stage-forms-fail-obscurely.md) | id: run-pipeline-stage-forms-fail-obscurely |
| [`hardening/stage-forms-read-differently-by-four-entry-points.md`](hardening/stage-forms-read-differently-by-four-entry-points.md) | id: stage-forms-read-differently-by-four-entry-points |
| [`hardening/strict-mode-only-covered-some-of-the-guards.md`](hardening/strict-mode-only-covered-some-of-the-guards.md) | id: strict-mode-only-covered-some-of-the-guards |
| [`hardening/studio-run-key-ignored-unapplied-edits.md`](hardening/studio-run-key-ignored-unapplied-edits.md) | id: studio-run-key-ignored-unapplied-edits |
| [`hardening/table-sort-mixes-rows-and-spec-dicts.md`](hardening/table-sort-mixes-rows-and-spec-dicts.md) | id: table-sort-mixes-rows-and-spec-dicts |
| [`hardening/unknown-operator-hides-missing-backend.md`](hardening/unknown-operator-hides-missing-backend.md) | id: unknown-operator-hides-missing-backend |
| [`hardening/wrappers-were-scalars-and-hints-were-raw-type-errors.md`](hardening/wrappers-were-scalars-and-hints-were-raw-type-errors.md) | id: wrappers-were-scalars-and-hints-were-raw-type-errors |
| [`literature/oss_landscape_notes.md`](literature/oss_landscape_notes.md) | OSS landscape notes (verified 2026-09-21) |

<!-- docmap:end -->
