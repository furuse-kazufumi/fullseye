<div class="vlang" markdown="1">

**日本語** · [English](en/index.md) · [简体中文](zh/index.md) · [繁體中文](tw/index.md) · [한국어](ko/index.md) · [Deutsch](de/index.md) · [हिन्दी](hi/index.md) · [Français](fr/index.md)

</div>

# Fullseye — ViEW2026

物理シミュレーションと画像処理を AI と組み合わせて、真値で確かめる。

タイルを押すと動画・図が開きます(▶ = 動く)。

[Fullseye とは(読み物)](about.md)

<style>
.vlang { font-size: 14px; line-height: 2; }
.vg { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin: 12px 0 20px; }
.vg.vs { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; }
@media (min-width: 600px) { .vg { grid-template-columns: repeat(3, minmax(0, 1fr)); } .vg.vs { grid-template-columns: repeat(5, minmax(0, 1fr)); } }
@media (min-width: 900px) { .vg { grid-template-columns: repeat(4, minmax(0, 1fr)); } .vg.vs { grid-template-columns: repeat(7, minmax(0, 1fr)); } }
.vg a, .vser a { display: block; position: relative; text-decoration: none; color: inherit; }
.vg img { display: block; width: 100%; max-width: 100%; height: auto; aspect-ratio: 1 / 1; object-fit: cover; border-radius: 6px; background: #222; }
.vg b { position: absolute; top: 6px; right: 6px; background: rgba(0,0,0,.6); color: #fff; font-size: 12px; padding: 1px 6px; border-radius: 9px; }
.vg span { display: block; font-size: 13px; line-height: 1.3; margin-top: 3px; }
.vg.vs span { font-size: 11px; }
.vser { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin: 12px 0 20px; }
@media (min-width: 600px) { .vser { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
.vser img { display: block; width: 100%; max-width: 100%; height: auto; aspect-ratio: 16 / 9; object-fit: cover; border-radius: 8px; background: #222; }
.vser strong { display: block; font-size: 14px; margin-top: 3px; line-height: 1.3; }
.vser span { display: block; font-size: 12px; line-height: 1.3; }
details.vall { margin: 6px 0; }
details.vall > summary { font-size: 15px; padding: 6px 0; cursor: pointer; }
.vl li { margin-bottom: 8px; }
</style>

<script>
(function () {
  try {
    var k = "fullseye_view2026_lang";
    if (localStorage.getItem(k)) return;
    localStorage.setItem(k, "seen");
    if (document.referrer && document.referrer.indexOf(location.host) >= 0) return;
    var n = (navigator.language || "").toLowerCase(), t = "";
    if (n.indexOf("zh") === 0) t = /tw|hk|mo|hant/.test(n) ? "tw" : "zh";
    else if (/^(en|ko|de|hi|fr)/.test(n)) t = n.slice(0, 2);
    if (t) location.replace(t + "/");
  } catch (e) {}
})();
</script>

## 触って見る

論文の図を、手元で動かして確かめられます(スマートフォンでも動きます)。タブで方法を切り替え、3-D はドラッグで回せます。

- **[光弾性の応力場](anim3d/photoelastic_anim3d.html?lang=ja)**: 検光子を回し、円板の応力場を走る色付きの縞を 3-D で確かめる。
- **[工業用 OCT の層構造](viewers/industrial_oct_anim3d.html?lang=ja)**: 深さ方向を掃引し、塗膜の B スキャンと層厚の測定を動かして見る。
- **[デフレクトメトリの面形状](viewers/phase_measuring_deflectometry_anim3d.html?lang=ja)**: 縞の位相を掃引し、写真では見えない表面の凹みが現れる過程を見る。
- **[CAD と実測点群の差分検査](viewers/poc_cad_scan_deviation.html?lang=ja)**: 位置合わせが欠陥を吸い、真値 1.2 µm の部品に 121 µm の存在しないへこみが出る。
- **[LiDAR の地形変化](viewers/poc_lidar_terrain_change.html?lang=ja)**: 素朴に引くと、変化の無い区画全体が 0.183 m 沈んで見える。補正すると、本当の変化だけが残る。
- **[テンプレート追跡](viewers/poc_template_tracking.html?lang=ja)**: そっくりな別物体に乗り換えても、追跡は「見つけた」と報告し続ける。
- **[パルスサーモグラフィの深さ推定](viewers/poc_thermography_ndt.html?lang=ja)**: 当てはめる時間窓を 25 秒から 4 秒に切るだけで、小さい欠陥の深さの誤差が最大 +627% から ±14% に縮む。外れた原因は物理でなく窓の選び方だった。
- **[タルボ絨毯と格子の X 線像](viewers/poc_grating_interferometry.html?lang=ja)**: 吸収では割れのコントラスト雑音比が 1.34 しかないが、暗視野では 13.5 に上がり、格子を回すと繊維の向きまで読める。
- **[縞の鏡像で見る µm の凹み](viewers/poc_phase_measuring_deflectometry.html?lang=ja)**: 写真の信号は雑音の 0.17 倍で何も見えないが、縞の鏡像から作る曲率の地図では、深さ 1 µm の凹みが雑音の 57 倍に立つ。
- **[小惑星の表面の曲がり具合](viewers/poc_asteroid_curvature.html?lang=ja)**: 実在の小惑星の点群から曲率を出し、尾根や巨礫の縁を色で見る。答えの分かる球で、先に物差しを確かめてある。
- **[焦点合成](viewers/poc_focus_stacking.html?lang=ja)**: F値を上げるほど焦点合成像が真のテクスチャに近づく
- **[白色干渉の段差](viewers/poc_interferometry_step.html?lang=ja)**: 雑音が増えると白色干渉の段差誤差が広がる
- **[偏光で鏡面除去](viewers/poc_polarization_specular.html?lang=ja)**: 入射角で鏡面分離の誤差が変わり、ブリュースター角近傍で最小になる
- **[光弾性の応力](viewers/poc_photoelasticity.html?lang=ja)**: 検光子を回すと光弾性縞が動き、平均輝度が周期的に変わる
- **[ハエの複眼](viewers/poc_compound_eye.html?lang=ja)**: 視点ごとのSNRを上げるほど複眼像が無雑音像に近づく
- **[接合層のボイド](viewers/poc_ct_void_morphology.html?lang=ja)**: しきい値を上げるほどボイド判定が広がり、体積率が増える
- **[動的輪郭](viewers/poc_active_contours.html?lang=ja)**: 反復を重ねるほどGVF輪郭が最終形へ近づく

## 目玉

<div class="vg">
<a href="../articles/assets/poc/poc_photoelasticity/03_load_and_isoclinics.mp4"><img src="thumbs/poc_photoelasticity.jpg" alt="光弾性の応力" loading="lazy" width="320" height="320"><b>&#9654;</b><span>光弾性の応力</span></a>
<a href="../articles/assets/poc/poc_telecentric_metrology/08_real_alignment_plate.png"><img src="thumbs/poc_telecentric_metrology.jpg" alt="テレセントリックレンズと寸法計測" loading="lazy" width="320" height="320"><span>テレセントリックレンズと寸法計測</span></a>
<a href="../articles/assets/poc/poc_code_matching_breakdown/05_highlight_sweep.gif"><img src="thumbs/poc_code_matching_breakdown.jpg" alt="照明と遮蔽に強い符号の照合" loading="lazy" width="320" height="320"><b>&#9654;</b><span>照明と遮蔽に強い符号の照合</span></a>
<a href="../articles/assets/poc/poc_good_sample_variation_model/04_visa_explanation.png"><img src="thumbs/poc_good_sample_variation_model.jpg" alt="良品統計の変動モデル" loading="lazy" width="320" height="320"><span>良品統計の変動モデル</span></a>
<a href="../articles/assets/poc/poc_fourier_ptychography/01_usaf_4x_fp_20x.png"><img src="thumbs/poc_fourier_ptychography.jpg" alt="フーリエ・タイコグラフィ(4 倍の視野で 20 倍の分解能)" loading="lazy" width="320" height="320"><span>フーリエ・タイコグラフィ(4 倍の視野で 20 倍の分解能)</span></a>
<a href="../articles/assets/poc/poc_cad_scan_deviation/14_align_orbit.gif"><img src="thumbs/poc_cad_scan_deviation.jpg" alt="CAD と点群の差" loading="lazy" width="320" height="320"><b>&#9654;</b><span>CAD と点群の差</span></a>
<a href="../articles/assets/poc/poc_weld_radiograph_porosity/06_map_toe_backgrounds.png"><img src="thumbs/poc_weld_radiograph_porosity.jpg" alt="溶接の気孔" loading="lazy" width="320" height="320"><span>溶接の気孔</span></a>
<a href="../articles/assets/poc/poc_hyperspectral_foreign_matter/04_real_pork_belly.png"><img src="thumbs/poc_hyperspectral_foreign_matter.jpg" alt="見た目が同じ異物をハイパースペクトルで選別" loading="lazy" width="320" height="320"><span>見た目が同じ異物をハイパースペクトルで選別</span></a>
<a href="../articles/assets/poc/poc_industrial_oct/01_real_paint_bscans.png"><img src="thumbs/poc_industrial_oct.jpg" alt="工業用 OCT(塗装の層厚と内部欠陥)" loading="lazy" width="320" height="320"><span>工業用 OCT(塗装の層厚と内部欠陥)</span></a>
<a href="../articles/assets/poc/poc_phase_measuring_deflectometry/08_ambiguity_map.png"><img src="thumbs/poc_phase_measuring_deflectometry.jpg" alt="写真では見えない µm の凹みを縞の鏡像で(デフレクトメトリ)" loading="lazy" width="320" height="320"><span>写真では見えない µm の凹みを縞の鏡像で(デフレクトメトリ)</span></a>
<a href="../articles/assets/poc/poc_tem_ctf_thon_rings/12_real_empiar_10028.png"><img src="thumbs/poc_tem_ctf_thon_rings.jpg" alt="仮想の透過電子顕微鏡(Thon リングと焦点外れ)" loading="lazy" width="320" height="320"><span>仮想の透過電子顕微鏡(Thon リングと焦点外れ)</span></a>
<a href="../articles/assets/poc/poc_thin_film_reflectometry/01_real_micrograph_thickness.png"><img src="thumbs/poc_thin_film_reflectometry.jpg" alt="分光反射率で薄膜の膜厚(公開の実測データで採点、ウェハの干渉色)" loading="lazy" width="320" height="320"><span>分光反射率で薄膜の膜厚(公開の実測データで採点、ウェハの干渉色)</span></a>
<a href="../articles/assets/poc/poc_virtual_sem_kv_cd_bse/05_sem_same_part_3kv_3detectors.png"><img src="thumbs/poc_virtual_sem_kv_cd_bse.jpg" alt="仮想 SEM と加速電圧" loading="lazy" width="320" height="320"><span>仮想 SEM と加速電圧</span></a>
<a href="../articles/assets/poc/poc_dual_energy_xray/05_material_colour.png"><img src="thumbs/poc_dual_energy_xray.jpg" alt="肉の中の骨片とガラスを 2 つのエネルギーで分ける(デュアルエナジー X 線)" loading="lazy" width="320" height="320"><span>肉の中の骨片とガラスを 2 つのエネルギーで分ける(デュアルエナジー X 線)</span></a>
</div>

<div class="vl" markdown="1">

- [光弾性の応力](../articles/assets/poc/poc_photoelasticity/03_load_and_isoclinics.mp4) (動画): 透明な樹脂に力を加えて偏光を通すと、内部の応力が縞として見える。円板を押しつぶした応力場を偏光像にし、縞次数が 0.5 を超えて位相が巻いた画素から応力を戻した。戻しが最初に失敗するのは、応力の大きい所ではなく縞の変調が落ちる等方点だった。
  検光子を回すと光弾性縞が動き、平均輝度が周期的に変わる **中心の縞次数 2.38(閉形式どおり)。op の偏光系は教科書の式と最大差 2.2e-16。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_photoelasticity.py)
  使った Fullseye の op: `axes_frame` · `axes_transform` · `mueller_apply` · `mueller_element` · `plot_series` · `text_box` · `ticks` · `unwrap_phase_2d`
  用語: Mueller matrix — 偏光状態を表すストークスベクトルに作用し、光学素子や試料による偏光変化を記述する4×4実行列。
- [テレセントリックレンズと寸法計測](../articles/assets/poc/poc_telecentric_metrology/08_real_alignment_plate.png) (図): 段差のある部品を一枚の画像で測ると、普通のレンズでは近い面ほど大きく写り、寸法が違って読まれる。論文で公開されたテレセントリックレンズの実画像を測り、倍率が論文の値と 0.05 % の差で一致した。合成の章では、物体の高さが変わってもテレセントリックでは倍率がほとんど動かない。
  主役は実画像: 論文(Stark ほか, Sci. Rep. 15, 28690, 2025、CC BY 4.0)のテレセン生画像を Fullseye の計測 op で測り、論文の値と突き合わせる。29.5° 傾いたアライメント板(円の間隔 1 mm)の 8 本のリングを、放射状の測定線(measure_pos)で取った線の中心へ「中心と形を共有する楕円の族」で当てると、長軸の伸びは 252.13 ± 0.04 px/mm で論文の K1 = 252.0 px/mm と +0.05 %(論文自身の K1・K2 が ±0.25 % 散っているので、それより細かい一致とは読まない)。★テレセンの証拠: 傾いた板の同心円の中心は r² に比例してずれない(β = 0.0035 ± 0.0034 px/mm²。同じ板を通常 f=25 で写すと 1.40 で、外側のリングの中心が 101 px ずれる)—— 入射瞳は 10.5 m より遠い。★リングごとに自由な楕円を当てると、影で弧が 36〜180° しか見えない外側のリングの長半径が外挿で狂う(弧 36° のリングで 768 px、正しくは 2142 px)。★樹脂の 3D プリント球(公称半径 2.5 mm)は輪郭の閾値で半径が 8 % 動き、真値にならない(2.400 / 2.452 mm。論文の計量級の球の生画像は公開データに無い)。以下は合成の章で、失敗条件を掃引する補助。ダイのボンディングやコネクタのピンは、高さの違う面の寸法を 1 枚の画像で測る。通常のレンズは近い面ほど大きく写すので段差の上と下で同じ寸法が違って写り、テレセントリックレンズは絞りを焦点に置いて主光線を光軸に平行にしてこれを消す。新 op 7 本(`telecentric`、`opsoptics` の `telecentric`): `telecentric_lens`(同じ BK7 相当の単レンズ f = 100 mm の絞りの位置だけを変えた通常 / 物体側 / 両側テレセン)/ `chief_ray_angle`(光線を入射瞳でなく絞りへ Newton 法で狙うので、入射瞳が無限遠でも動く —— `raytrace.chief_ray` はここで止まる)/ `magnification_vs_depth` / `telecentricity_error` / `defocus_spot_vs_depth` / `vignetting_vs_field` / `lens_equivalent_pinhole`(入射瞳に置いた `render3d` のピンホール)。像面を固定して物体を +5 mm 近づけると、作動距離 75 mm の FA レンズ(f = 25 mm)は倍率 +6.9 %、通常 f = 100 mm は +1.7 %、テレセンは −0.013 % で、実光線は閉形式 L/(L − Δz) と 7e-5 で一致する。オートフォーカスで合わせ直しても m = −f/(s − f) で +2.6 % 動き、戻らない。ピン(高さ 5 mm)・電極つきのダイ・穴(深さ 5 mm)を 3 種のレンズで描くと、FA レンズは画像から測ったピン上面の径を 6.9 % 大きく読み(閉形式と 7e-4)、ワークが 6 mm 上下すると読みが 8.6 % 動き、穴の内壁が 2,053 画素見えて底が 0.948 しか見えない(円の重なりの閉形式 0.949)。両側テレセンでは底が全部見え、内壁は 0 画素。部品はアルミの治具プレート・金めっきのピン・黒い樹脂モールドと銀色のリードの質感で描き(metalfinish の削り目と金属の複素屈折率の色、surfacelib の上塗り、影と AO)、照明を同軸落射・ドーム・低角リングに変えても、描いた画像から円の計測モデル(metrology)で測ったピン上面の径は閉形式と 0.33 % 以内、6 mm の上下で通常 f=25 は +8.3〜8.4 %、両側テレセンは ±0.16 % 以内。★物体で 47 µm/画素に粗くすると低角リングでは 2 % 外れた(暗視野で上面の縁が弱い)。★テレセンでも残る: 単レンズは瞳の球面収差で物高 8 mm のテレセン度が 0.05°(h³ で育つ)、物体側テレセンの歪曲は 3 %(両側の対称な配置では 0.005 %)。絞りのずれ δ は Newton の式で入射瞳を −f²/δ に動かし、物高 0.5 mm では閉形式と 0.04 %、8 mm では 11.8 % 大きい。テレセン度 0.1° が残ると段差 5 mm で 9.2 µm ずれる(閉形式 8.7 µm)。視野は前玉で決まり、50 % 点 11.6 mm は近軸の閉形式 12.4 mm より 0.8 mm 手前(瞳収差で光束が外へずれて太る)。ぼけの RMS の傾きは |m|·NA/√2 と 0.5 % 以内で、22 µm を回折で潰さない NA 0.033 では被写界深度は 0.68 mm が上限。第二の実装として OSS の optiland(MIT)と主光線の像の高さが 9e-8 mm で一致(屈折率は同じ公開の硝材カタログの係数なので、見ているのは光線追跡と狙いの実装)。学習 0、較正 0、門 29 件。 [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_telecentric_metrology.py)
  使った Fullseye の op: `add_metrology_object_circle_measure` · `annotate_scale_bar` · `apply_metrology_model` · `blast_normals` · `cast_shadow` · `chief_ray` · `chief_ray_angle` · `clearcoat_shade` · `create_metrology_model` · `defocus_spot_vs_depth` · `finish_shade` · `gen_measure_rectangle2` · `glass_catalog` · `lens_equivalent_pinhole` · `lens_system` · `magnification_vs_depth` · `measure_pos` · `metal_mirror_rgb` · `micro_normals` · `paraxial_trace` · `telecentric_lens` · `telecentricity_error` · `text_box` · `tonemap_reinhard` · `trace_rays` · `vignetting_vs_field`
- [照明と遮蔽に強い符号の照合](../articles/assets/poc/poc_code_matching_breakdown/05_highlight_sweep.gif) (GIF): テンプレート照合でよく使う正規化相互相関は、対象の一部が隠れたり光沢で白く飛んだりすると外れやすい。明るさの変化の向きを符号にして比べる照合を加え、公開の実写から切ったテンプレート 40 枚で撹乱を強めていった。符号で比べる照合は隠れに強いが、回転にはどの方法も弱かった。
  テンプレート照合の正規化相互相関(NCC)は明るさの値を比べるので、テンプレートの一部が隠れる・光沢が飛ぶ・片側だけ暗いといった局所の崩れに弱い。明るさの変化の向きを符号にして比べる照合 4 種(方向符号照合 OCM、増分符号相関 ISC、選択的相関係数 SCC、背景比較の Radial Reach Filter。文献の式から再実装)を codematch 6 op として足し、公開の実写 5 枚(CC0)から切った 32 x 32 のテンプレート 40 枚に段階的な撹乱を掛けた。当たりが半分を割る所は、遮蔽で NCC 10 %・SCC 36 %・ISC 63 %・OCM 67 %、飽和ハイライトで NCC 6 %・SCC 10 %・OCM 44 %・ISC 53 %。回転には 4 種とも弱い(7〜9°)。SCC は符号の合った画素だけを選ぶので無関係な位置でも相関が上がり(選択の偏り)、文献の式のままでは NCC より先に壊れた。無相関の使用率の期待値 + 4σ を床にして直した。空を切った平坦なテンプレート 11 枚では、NCC は相関 0.82 前後で 10 枚を外し、符号系は拒否するか正解する(誤答 0)。門は総当たりの第 2 実装・既存の NCC・単調変換での不変性・rot90 の可換性(巡回差を絶対差にした探針で崩れる)・正解位置の値の閉形式(1,080 試行で |z| ≤ 3.6)。 [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_code_matching_breakdown.py)
  使った Fullseye の op: `isc_match` · `ncc_locate` · `ocm_match` · `radial_reach_filter` · `reflect` · `scc_match` · `text_box`
  用語: OCM — 各画素の輝度勾配方向を離散符号に変え、符号差でテンプレートと画像を照合する方法。
- [良品統計の変動モデル](../articles/assets/poc/poc_good_sample_variation_model/04_visa_explanation.png) (図): 良品を何枚も撮り、画素ごとのいつものばらつきから外れた所を欠陥とするのは、外観検査の古典的な方法である。誤検出率を先に宣言して帯の幅を決めるようにし、公開の実画像 200 枚で採点した。位置合わせの有無が良品の枚数より効く一方、宣言した誤検出率は実画像では守られなかった。
  外観検査の古典「良品を何枚も撮り、画素ごとにいつもの値とばらつきを覚え、外れた画素を欠陥とする」を、帯の幅を手で決めず、1 画素あたりの誤検出率を宣言して決める op 族にした(新 op 5 本 varmodel_* と、方法に依存しない評価の物差し anomeval 4 本)。正規の良品なら新しい 1 枚の偏差は t 分布の予測区間に従うので、帯の幅は閉形式で出る。合成の良品で数えた誤検出率は、画素ごとの標準偏差・全画素で 1 つの分散・経験ベイズの縮小(Smyth 2004)・中央値と MAD の 4 種とも宣言の二項 4σ の帯に入り、画素ごとに雑音が違うのに 1 つの分散を使うと外れる。良品 5 枚では標準偏差の帯の幅は 9.4 倍(t₄ の裾)になり、縮小すると 5.0 倍、5σ の傷の検出率は 0.13 → 0.52。1〜2 px ずれた良品群は拒否され、無理に通すと縁の上の帯が 22 倍に太って縁の上の傷を 1 つも見つけない。並進を 1/20 px で測って Fourier シフトで合わせると 1.07 倍に戻る。3 枚に同じ傷のある「良品」群では標準偏差は傷を見逃し(0.00)、中央値と MAD は見つける(0.98)。公開実データ VisA pcb1(CC BY 4.0、試験 200 枚)では、合わせた帯の画素 AUROC 0.808・AUPRO 0.678 に対し、合わせない帯は 0.705・0.460。ゴールデン比較は画素 AUROC 0.826 と上回るが、欠陥を 1 つずつ数える AUPRO は 0.519 で下回る。宣言 1e-3 の誤検出率は実画像では 3.8 % で守られず、学習に使わなかった良品で帯を測り直しても 2.4 % —— 並進で取れない撮影の違いが残る。確率的なテクスチャ(DAGM 2007、CC BY 4.0)は平均像に構造が無く、位置合わせは「測れない」と報告され、検出は偶然並み(画素 AUROC 0.465)。この方法が効く所と効かない所の両方を数で示した。 [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_good_sample_variation_model.py)
  使った Fullseye の op: `anomaly_image_auroc` · `anomaly_pixel_auroc` · `anomaly_pro` · `anomaly_region_overlap` · `dc_rpca_sparse` · `varmodel_alignment` · `varmodel_calibrate` · `varmodel_fit` · `varmodel_score`
- [フーリエ・タイコグラフィ(4 倍の視野で 20 倍の分解能)](../articles/assets/poc/poc_fourier_ptychography/01_usaf_4x_fp_20x.png) (図): 低倍率の対物レンズは視野が広い代わりに、細かいところが見えない。照明の角度を変えて撮った像を周波数空間でつなぎ直すと、低倍率の視野のまま 20 倍の像と同じ細かさまで分解した。照明の重なりが足りず収束しない条件では、答えを出さずに拒否する。
  低倍率の対物の広い視野のまま、LED アレイで照明の角度を変えて撮った像の組を周波数空間でつなぎ、20 倍相当の分解能と位相を反復の位相回復(収束型の演算)で得る。新 op 6 本(`fourierptycho`、`opsoptics` の `fpm`): `fp_design`(合成 NA・遮断周期・隣り合う瞳の重なり率・LED の数・画素の標本化・境の LED を撮る前に)/ `fp_usaf_target` / `fp_capture`(斜めの平面波 → 瞳 → 強度、雑音・収差・LED アレイのずれ・反射型の高さ)/ `fp_stack_from_images`(実データの入口)/ `fp_reconstruct`(逐次の位相回復 + 瞳の同時推定 + LED の位置の補正。収束の履歴・止めた理由・合成 NA を返し、収束しなければ拒否)/ `fp_element_contrast`(USAF の要素ごとの3 本の棒の変調)。4 倍 / NA 0.1・LED 13 × 13 で合成 NA 0.424、4 倍の 1 枚は G7 E4(5.53 µm、閉形式 λ/NA 5.32 µm)まで、FP は G9 E5(1.22 µm、閉形式 1.25 µm)まで分解し、20 倍 / NA 0.40 のコヒーレント像と同じ要素。位相だけの物体は帯域制限した真値と rms 0.13 rad、反射型の 20〜40 nm の段差は rms 4.0 nm。重なりを 64 → 7 % に下げると、43 % 以上は収束、32 % 以下は「2 本の初期値が別の答えに着いた」か回数切れで拒否 —— 境が公表の下限 35 % を挟む。★残差だけでは見抜けない(重なり 18 % の残差は 64 % より小さい)。瞳の同時推定は収差 rms 0.12 波を 0.005 波まで戻し、LED アレイのずれ (0.6, −0.4) mm・1°・1.5 mm を (0.62, −0.36) mm・0.93°・1.25 mm と読み戻す。★k の符号の反転は位相の符号が反転した像に着き、残差は同じ(強度では区別できない)。実データ(公開の USAF の FP データ、repo に入れずデータがあるときだけ)では、公表の装置の値からの遮断周期 1.60 µm に対し G9 E3(1.55 µm)まで分解(生の 1 枚は G7 E3)。学習 0、較正 0、門 33 件。 [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_fourier_ptychography.py)
  使った Fullseye の op: `coherent_image` · `fp_capture` · `fp_design` · `fp_element_contrast` · `fp_reconstruct` · `fp_stack_from_images` · `fp_usaf_target`
- [CAD と点群の差](../articles/assets/poc/poc_cad_scan_deviation/14_align_orbit.gif) (GIF): 点群を設計形状へ合わせてから検査すると、位置合わせが欠陥を吸収したり別の場所へ移したりする。へこみや反りを既知量で入れた部品を合わせ、欠陥のない対照にも66.5平方mmの公差外領域が出る条件を測った。図では、剛体運動に似た偏差は薄まり、稜線では対応先が隣面へ飛んで偽のへこみが現れる。
  解析形状の機械部品に、局所へこみ・反り・摩耗を法線方向の既知量として仕込み、既知の姿勢・雑音・欠測つきの実測点群を合成した。合わせてから符号付き偏差と公差外面積を測ると、局所へこみの読みは 3.7 % しか薄まらないのに、真値が 1.2 µm しかない部品中央に深さ 121 µm の存在しないへこみが出る(閉形式の予測 -120 µm)。消えるか化けるかは剛体 6 自由度が吸える偏差場に似ているかどうかで決まり、稜線では最近傍が隣の面へ飛んで、欠陥ゼロの対照でも 66.5 mm^2 の偽の公差外領域が出た。 [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_cad_scan_deviation.py)
  使った Fullseye の op: `box_sdf` · `chamfer_distance` · `color_bar` · `esdf` · `estimate_normals` · `estimate_oriented_normals` · `face_areas` · `gicp` · `hausdorff_distance` · `icp_point2plane` · `icp_point2point_3d` · `query_distance` · `register_fpfh` · `sphere_sdf` · `text_box` · `voxel_grid_downsample`
- [溶接の気孔](../articles/assets/poc/poc_weld_radiograph_porosity/06_map_toe_backgrounds.png) (図): 溶接の X 線透過像で気孔を数え損なうと、溶接の等級を間違える。固定しきい値は余盛の縁まで気孔と数え、塊を 124 個も出した。背景を推定してから検出すると本物の気孔に絞れ、等級を誤る画像が大きく減った。
  板厚 10 mm + 円弧の余盛 + 球形気孔を Beer–Lambert(吸収による指数減衰則) で閉形式に描き、散乱・不鋭度・粒状雑音を足した透過像。固定しきい値のゼロ点は余盛のつま先を気孔に数える(塊 124 個、合計面積 15.19 mm²、真値 7.93)。検出の崖は CNR = 16.12·d² から先に予測でき、50 % 検出径は Rose の CNR = 4 では 0.50 mm と外れ、平滑化と最小面積 3 px を入れた予測 0.58 mm に対し実測 0.57 mm。背景推定 op の窓上限(矩形オープニング 9 px)は 2.0 mm から検出率 50 % を割り 2.5 mm で 0 % の崖になる ―― op を選ぶことが測定範囲を選ぶ。散乱 SPR=1 は体積径を (1+SPR)^(-1/3) で -22.6 %(予測 -20.6 %)縮める。等級を 1 段間違える画像はゼロ点 90 % → 体積径 23 %。 [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_weld_radiograph_porosity.py)
  使った Fullseye の op: `blob_features` · `blob_label` · `blob_overlay` · `blob_select` · `estimate_noise` · `gauss_image` · `gen_measure_rectangle2` · `gray_opening_rect` · `identity` · `log_image` · `measure_pairs` · `measure_pos` · `median_rect` · `sk_rolling_ball` · `xsitk_grayscale_grindpeak`
  用語: Beer–Lambert — 均一な吸収媒体を通る光の透過率が、濃度と光路長に対して指数関数的に減るという法則。
- [見た目が同じ異物をハイパースペクトルで選別](../articles/assets/poc/poc_hyperspectral_foreign_matter/04_real_pork_belly.png) (図): 肉や仁と同じ色の異物は、カラーカメラでは見分けられない。公開の実画像を分光画像として分類すると、豚バラの上の異物を誤警報 1.1 % で検出できた。帯域を減らすと誤警報が増え、合成データでは足りた条件が実データでは足りなかった。
  公開の実画像 2 つ(どちらも CC BY 4.0、repo には入れず取得スクリプト + キャッシュ)を Fullseye の op(`read_envi`・`spec_continuum_removal`・`spec_angle_mapper`・`spec_band_selection_fisher`)で分類し、データの正解ラベルで採点した。樹脂の破片 6 種(RODARE 3390、400〜2500 nm の分光カメラ): 連続体除去 + SAM でクラス平均の再現率 0.816(生の反射率の SAM は 0.439 —— 暗い破片は足し算のベースラインに負ける)。別の撮影の基準試料をライブラリにすると PP / PET / PE を 0.878、この PoC の材料表の物理モデルだけをライブラリにすると 0.628(当て推量 0.333)。黒い樹脂は反射率 0.03 で C-H の谷が他の 1/6。試験ヘッダの fwhm が切り出す前の450 個のまま残っていたのを fail-closed の読み手が拒否した —— 波長の札は樹脂の谷の位置で確かめ、fwhm だけ直した写しを読む。豚バラの上の異物 10 種(Zenodo 17242553、InGaAs ラインスキャン分光カメラ): 撮影で分けて採点(65 万画素)、SAM は AUC 0.92・誤警報 10 %、全 184 帯の LDA で検出 0.92・誤警報 1.1 %、Fisher の 6 帯で誤警報 2.1 %、3 帯では 23 % —— 合成では 3 帯で足りたのに実データでは足りない。合成(材料表の吸収帯 → Kubelka–Munk → ハロゲン × 溶融石英のレンズ × InGaAs、新 op 8 本)は壊れ方の補助: 仁と同色の異物は RGB でAUC 0.48、仁の含水率 12 % で誤排出 98 %、白板の後にランプが 200 K 下がると 49 %、カーボンブラック 1 wt % で PP と PE が 1 画素の雑音に埋もれる。合成の 1.000 と実データの 0.82〜0.92 の差が逆犯罪の大きさ。パラメータは一次情報(USGS の実測、論文、データシート)で照合し、PE の帯の強さを 2〜3 倍下げ、PET の最も深い 2 帯を足し、材料表の水の k を Segelstein 1981 に直した。 [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_hyperspectral_foreign_matter.py)
  使った Fullseye の op: `carbon_black_absorption` · `hyperspectral_band_weights` · `hyperspectral_capture` · `ingaas_photodiode_qe` · `kubelka_munk_reflectance` · `material_nir_absorption` · `median` · `nir_model_info` · `spectral_reflectance_from_material` · `text_box`
  用語: SAM — 二つのスペクトルをベクトルとみなし、そのなす角で形の類似度を測る分類法で、全体の乗算には不変。
- [工業用 OCT(塗装の層厚と内部欠陥)](../articles/assets/poc/poc_industrial_oct/01_real_paint_bscans.png) (図): 塗装や多層フィルムの層の厚さを、切らずに奥行き方向から見たい。公開されている自動車塗装の生の干渉スペクトルから透明層の厚さを求め、論文の OCT の値と 1.5 µm 以内で一致した。分離できない薄い層には値を出さず、測れないと返す。
  塗装・コンフォーマルコート・接着層・多層フィルムの層の並びと、層の中の空洞・剥離を光干渉断層(OCT)で壊さずに見る。新 op 13 本(`octscan`、`opsoptics` の `oct`): `oct_design`(軸分解能 0.44 λ0²/Δλ・深さ範囲 λ0²/(4δλ)・roll-off・SNR・横分解能と焦点深度を撮る前に)/ `oct_interferogram`・`oct_bscan_simulate`(層の並び → 干渉スペクトル、屈折率と分散は材料表)/ `oct_k_linearize`・`oct_dispersion_compensate`・`oct_dispersion_estimate`・`oct_ascan`・`oct_bscan` / `oct_layer_thickness`(群屈折率で厚さ、分離できなければ拒否)・`oct_bscan_boundaries`・`oct_bscan_flatten` / `oct_from_spectra`(生のスペクトルの入口)。**実測**: 公開の自動車塗装の生スペクトル(CC BY 4.0)を Fullseye の op だけで処理し、透明層 44.5 / 86.4 / 99.7 / 70.8 µm が論文の OCT と 1.5 µm 以内・顕微鏡と 3.6 µm 以内、着色層は 4 枚中 3 枚が顕微鏡と 2.3 µm 以内(1 枚は 7.6 µm ずれて未解決)、白の見本の着色層の下は拒否、透明層の光学厚 155.6 µm の深さに水平に出る自己相関の幽霊。合成: 群屈折率で割った厚さが真値と 0.04 µm、位相屈折率なら 0.9〜1.9 % 厚い、SNR・roll-off・分散の広がりが閉形式と一致、点像の幅の 1.4 倍より薄い層は拒否、コートの厚さの地図と空洞・剥離の検出。 [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_industrial_oct.py)
  使った Fullseye の op: `glass` · `material_optical_constants` · `oct_ascan` · `oct_bscan` · `oct_bscan_boundaries` · `oct_bscan_flatten` · `oct_bscan_simulate` · `oct_design` · `oct_dispersion_broadening` · `oct_dispersion_compensate` · `oct_dispersion_estimate` · `oct_from_spectra` · `oct_interferogram` · `oct_k_linearize` · `oct_layer_thickness`
  用語: OCT — 低コヒーレンス光の干渉を使って深さ方向の反射分布を測り、試料内部の断層像を非接触で得る方法。
- [写真では見えない µm の凹みを縞の鏡像で(デフレクトメトリ)](../articles/assets/poc/poc_phase_measuring_deflectometry/08_ambiguity_map.png) (図): 光沢のある塗装面のごく浅い凹みは、照明を当てた写真ではまず見えない。面の前の画面に縞を映し、その鏡像のゆがみから曲率を求めると、深さ 3 µm の凹みがはっきり浮かんだ。写真ではほぼ一様な面に、縞の鏡像からだけ凹みが現れる。
  光沢面(車の塗装パネル、カバーガラス)の深さ数 µm の凹みは、照明を当てた写真ではまず見えない —— 鏡は照明しか写さない。面の前の画面に位相シフト縞を出し、その鏡像を撮ると、面が 1e-3 rad 傾くだけで 30 cm 先の画面では 0.6 mm ずれる。新 op 6 本(`deflectometry`、`opsspecular` の `deflectometry`): `deflectometry_rig` / `deflectometry_screen_pattern` / `deflectometry_render`(高さ場 → 縞の鏡像。拡散成分、散乱、ガラスの裏面反射、開口積分のピント、雑音)/ `deflectometry_phase_to_slope`(絶対位相 → 法線、`match3d.normal_from_reflection`)/ `slope_to_curvature`(積分せず 1 回微分)/ `deflectometry_sensitivity`(撮る前の閉形式)。深さ 3 µm と 1 µm の凹み・うねり 0.8 µm・研磨ムラ 0.12 µm を仕込んだ塗装パネルで、ソフトボックスの写真の欠陥の信号は最大 0.00066(8 bit の 1 段の 0.17 倍)なのに、曲率マップの SNR は 110 と 57。勾配を積分した凹みの深さは真値と 0.5 % 以内。位相の雑音は閉形式 √(2/N)·σ/b と 1.00 倍、面の傾きの雑音は σ_u/(2d) の 0.67 倍(双線形の読み直しの √(4/9) どおり)。壊れるところ: 部品を 0.3 mm 浮かせると見かけの傾き Δz·sin θ/d(0.1 % で一致)と半径 388 m の椀が出るが凹みの深さは 0.7 % しか変わらない / 画面の距離を 2 % 間違えると深さが 2.3 % 浅い / 拡散成分 0.85 までは 1 µm の凹みが見え、0.9 で粗い縞の次数が飛び始める / 無反射コートの無いカバーガラスでは裏面の光が凹みの斜面(くさび)で逆向きに曲がり、傾きの感度が閉形式 0.246 に縮んで凹みが 1/4 の深さに見える(実測 0.246)/ 開口 8 mm では面にピントで縞の振幅が 0.60 倍、画面にピントで凹みが 0.52 倍の深さ。学習 0、較正 0、門 22 件。 [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_phase_measuring_deflectometry.py)
  使った Fullseye の op: `absolute_phase` · `deflectometry_phase_to_slope` · `deflectometry_render` · `deflectometry_rig` · `deflectometry_screen_pattern` · `deflectometry_sensitivity` · `fresnel_dielectric` · `integrate` · `sfp_height` · `slope_to_curvature` · `text_box` · `wrapped_phase`
- [仮想の透過電子顕微鏡(Thon リングと焦点外れ)](../articles/assets/poc/poc_tem_ctf_thon_rings/12_real_empiar_10028.png) (図): 透過電子顕微鏡の像は、焦点の外し方によって細部の明暗が反転する。この結像を組み立て、公開の実写 3 枚から焦点外れを推定すると、著者の解析ソフトの値とほぼ一致した。焦点を振ると、パワースペクトルの同心円が動き、正焦点の近くで細部が反転する。
  透過電子顕微鏡は薄い試料を透けた電子の位相を、球面収差 Cs と焦点外れ Δf で強度に変える。その変え方 CTF = −sin(χ + arcsin w) は周波数ごとに符号が入れ替わり、パワースペクトルに零点の同心円(Thon リング)を描く。新 op 11 本(`temsim`、`opsoptics` の `tem`): `tem_wavelength` / `tem_scherzer` / `tem_ctf` / `tem_ctf_profile` / `tem_projected_potential` / `tem_amorphous_film` / `tem_image_weak_phase` / `tem_multislice` / `tem_power_spectrum` / `tem_ctf_estimate` / `tem_ctf_correct`。結像は `coherent_image` に瞳 e^{iχ} を渡し、電子の散乱因子は `pxrd` の X 線の因子から Mott–Bethe で作り、リングの周期の初期値は k² について不等間隔の標本に `lomb_scargle`、フレームの位置合わせは `phase_correlation_fft`(どれも既存の op)。波長は公表値と 5 桁(300 kV で 1.9687 pm、補正なしは 13.7 % 長い)、零点は閉形式と 1.7e-12 Å⁻¹、Scherzer 焦点の最初の零点は 0.6580 Cs^¼ λ^¾、正弦位相格子の回折は J_n(φ₀)² と 1.6e-13。Si の平均内部ポテンシャルは中性原子の値 13.71 V に対して 13.83 V(実測 12.48 V より高いのは結合の分)。★Cu の f_e(0) は 10.5 % 小さい(X 線の当てはめの限界)。像が投影ポテンシャルに最もよく似る焦点は 900 Å で Scherzer 842 Å の 7 % 以内、正焦点では細部が反転する(相関 −0.30)。合成の写真 4 枚で Δf を 13 Å 以内、非点収差を 50 Å・5.2° 以内で回収し、jackknife の σ が誤差を覆う。雑音だけ・線量不足・正焦点の近く・タイルが 9 枚しかなく別の谷に落ちた当てはめ、の 4 例はすべて拒否。画素寸法を 2 % 間違えると Δf は 1.039 倍(閉形式 1.0404)。ドリフトした 10 枚は和にするとリングが消え(当てはまりの分解能 15.6 Å)、合わせると戻る(5.3 Å)。位相反転で投影ポテンシャルとの相関は 0.09 → 0.84、ウィーナーで 0.87、Δf を 10 % 間違えると 0.10。★実写(EMPIAR-10028、CC0)3 枚で、著者の CTFFIND3 の値と −55 / +65 / −0.5 Å(0.2 % 以内)。学習 0、較正 0、門 36 件。 [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_tem_ctf_thon_rings.py)
  使った Fullseye の op: `tem_amorphous_film` · `tem_ctf` · `tem_ctf_correct` · `tem_ctf_estimate` · `tem_ctf_profile` · `tem_image_weak_phase` · `tem_multislice` · `tem_power_spectrum` · `tem_projected_potential` · `tem_scherzer` · `tem_wavelength`
  用語: Thon rings — TEM像のパワースペクトルに現れる同心円で、CTFの零点と符号反転を反映し、デフォーカスや非点収差の推定に使う。; CTF — 透過電子顕微鏡で、試料の空間周波数成分が収差とデフォーカスにより像へどの符号・強さで伝わるかを表す関数。
- [分光反射率で薄膜の膜厚(公開の実測データで採点、ウェハの干渉色)](../articles/assets/poc/poc_thin_film_reflectometry/01_real_micrograph_thickness.png) (図): シリコン上の酸化膜の厚さは、反射スペクトルに出る干渉の縞から読み取れる。他の研究者が公開した実測データで採点し、裸のシリコンの実測反射率は材料表と 0.4 % の差に収まった。薄すぎる膜では、縞を数える方法が自ら信頼できないと判定する。
  Si 上の SiO₂ の膜厚を反射スペクトルの干渉縞から測る op 5 本(`filmoptics`、`opsoptics` の `film`): `multilayer_reflectance`(転送行列)/ `film_color` / `film_thickness_fft` / `film_thickness_fit` / `film_thickness_map`。膜も基板も材料表(`materials`)の鍵で引く。★主役は他人が測った実物のデータ(どちらも CC BY 4.0): Schwarz ら 2024 の顕微分光では、裸の Si の実測反射率が材料表の Si と中央値 0.4 % 差、SiO₂ の膜厚は直入射のモデルで 92.9 nm(基準 98.5 nm と −5.7 %)、残差が最小の NA 0.5 を入れると 95.8 nm(−2.7 %)。測定点の被覆率は 11 点を平均 0.6 点の誤差で読み返す。同じ試料の実物のカラー顕微鏡写真からは、裸の Si で白を合わせるだけで画素ごとの膜厚が出て中央値 87.4 nm(−11 %、カメラの分光感度は不明)。Sánchez-Arriaga ら 2023 の安価な分光器では、標準 476.3 nm が 5 本すべて 2 % 以内、198.7 nm は中央値 +6.6 % で、1 本は最良の候補が 51 nm に外れて正しい値は 2 番目の候補に残る。FFT 法は 98 nm の膜を自分で「信頼できない」と言う(下限の閉形式 554 nm)。合成の章: 1 層は Airy の式(別実装)と 3e-15、縞の本数は d·Δx と ±1、FFT の下限の閉形式 538 nm と実測 525 nm、材料の取り違え・入射角・NA の偏りは閉形式どおり。公表の色表との色相の一致は 1〜3 次で 59 %(弱い門)。模型のウェハ(彗星は縁まで半径方向、縁の盛り上がり、芯ずれの輪 —— 量は文献表に結びつけ、無いものは模型と明記)では分光 31 帯域の膜厚マップが RMS 0.17 nm、RGB は候補が複数の画素が 14 %。学習 0、門 37 件。 [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_thin_film_reflectometry.py)
  使った Fullseye の op: `annotate_colorbar` · `blackbody_spectrum` · `film_color` · `film_thickness_fft` · `film_thickness_fit` · `film_thickness_map` · `multilayer_reflectance` · `spectrum` · `text_box` · `thinning`
- [仮想 SEM と加速電圧](../articles/assets/poc/poc_virtual_sem_kv_cd_bse/05_sem_same_part_3kv_3detectors.png) (図): SEM の像は表面の写真ではなく、固体の中で散乱した電子のうち外へ出てきたものの集計である。電子を一つずつ追う模型を組み、反射電子の量を 7 元素の実測データベースと照合した。同じ線でも加速電圧を変えると、側壁のどの高さを線幅として測っているかが変わる。
  走査電子顕微鏡(SEM)の像は表面の写真ではなく、固体の中で散乱する一次電子の**相互作用の体積**から何が出てきたかの集計である。新 op 8 本(`sem_electron_mc` / `sem_yield_curve` / `sem_se_universal_curve` / `sem_line_profile` / `sem_cd_measure` / `sem_image` / `sem_charging_series` / `sem_se_escape_fraction`)と材料表の `material_electron_properties` で、一次電子を 1 個ずつ追うモンテカルロ(Joy の単散乱、弾性散乱は Browning 1994 の Mott 近似、阻止能は Joy-Luo)を組み、各段を外の実測値で採点した。反射電子係数 η は 7 元素(C〜Au)× 5/10/20/30 keV の全部が Joy のデータベースの実測の幅 ± 0.04 に入り、遮蔽ラザフォードに戻すと W・Au で外れる。最大の到達深さは Kanaya-Okayama の 0.83〜1.04 倍、深さは E^1.75(Si)/ E^1.52(Au)で伸びる(KO は 1.67)。二次電子の収率の形は C〜Ag の 5 元素で Lin & Joy 2005 の普遍曲線に RMS ≤ 0.076、Emax は表の −4〜+7 %(合わせていない)。W・Au は裾が厚く合わない(SE2 が主、未解決)。★ユーザーの見立て「Si の上の W は SE では見えず、反射電子の Z コントラストで浮かぶ」は条件つきで当たった: 段差の無い W を 1 kV で見たときだけ(SE +5 %、反射電子 +96 %)。5 kV では SE も +80 % —— 反射電子が表面を抜けるときに作る SE2 が Z を運ぶ。深さ 150 nm に埋もれた W は 1 kV では反射電子でも +3 %、20 kV で +154 %(情報深さ)。CD-SEM では PMMA の線(底辺 40 nm)を側壁 88 度で測ると、しきい値法の線幅が 1 kV 39.1 nm / 20 kV 39.9 nm ―― 低加速は側壁の上寄り(0.33)、高加速は根元(0.03)を測る。ただし側壁 80 度では差が小さく向きも逆で、「低加速ほど上を測る」は一般則ではない。垂直の側壁はどの電圧でも太く測る(+0.3〜+1.0 nm)。帯電は、η + δ > 1 の 0.5 kV で正に溜まって暗くなり、η + δ·F(V*) = 1 を二分法で別に解いた電位に 2e-15 V で止まる。20 kV は負に溜まり続けて明るくなる(現象論)。途中で見つけた欠陥も残す: 自由行程を出発点の材料で引いたまま材料の境界を素通りしていて、0.01 nm の Si のキャップで W の η が 0.425 → 0.329 に跳んでいた(境界で歩を切って直し、回帰の門にした)。実画像の章は未実施(線幅の真値つきの CC BY の CD-SEM 像が見つからない)。 [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_virtual_sem_kv_cd_bse.py)
  使った Fullseye の op: `material_electron_properties` · `sem_cd_measure` · `sem_charging_series` · `sem_electron_mc` · `sem_image` · `sem_line_profile` · `sem_se_escape_fraction` · `sem_se_universal_curve` · `sem_yield_curve` · `threshold`
- [肉の中の骨片とガラスを 2 つのエネルギーで分ける(デュアルエナジー X 線)](../articles/assets/poc/poc_dual_energy_xray/05_material_colour.png) (図): 食品の X 線検査の透過像では、厚い肉と薄い硬い異物を区別できない。光子のエネルギーを 2 つの窓で数え分けて厚みと材質に分けると、肉の重なりが作った偽の異物が消えた。分けられなくなるアルミの厚さも、閉形式の予測どおりに現れた。
  食品の X 線検査の 1 枚の透過像は各画素で L = −ln(I/I₀) という 1 つの数しか測らない —— 厚い肉と薄い硬い異物は区別できない。光子のエネルギーを 2 つの窓で数え分ける検出器で撮ると、μ(E) の形が材質で違うので、各画素で厚みと材質が分かれる(Alvarez & Macovski 1976 の基底分解)。新 op 14 本(`opstomography` の `spectral_xray`): 材料表の X 線の列(`material_xray_attenuation` ほか 3 本、NIST SRD 126 の部分集合と混合則)と `dualxray` 10 本(X 線管のスペクトル・線質・検出器のチャネル・投影・基底分解・CRLB・R 値・実効 Z・弁別の誤り率)。μ/ρ は NIST の公表値と一致(Cu 8 keV 52.55、K 端 38.4 → 278.4)、管の模型の半価層は IEC 61267 の線質 8 つと 5.8 % 以内(模型は公開のスペクトル計算(MIT)の形に合わせ、IEC の値は合わせに使っていない)。厚さ 25〜60 mm の肉のトレイで、骨片とガラスの段差は肉のむらの 0.9 倍、しきい値 1 本では肉の 86 % を誤検出、高域を取っても肉の重なりの縁が偽の塊 2 個になるが、赤身 + Al に分けた Al の像は偽の塊 0。厚い PE と薄い Al の交絡の組は 1 つの窓では d′ = 0、2 つの窓の誤り率 Φ(−d′/2) はモンテカルロと 0.004 以内、分けられなくなる Al の厚さ(誤り率 5 %)は閉形式 0.125 mm・実測 0.126 mm、肉 40 mm の下で 0.364 mm。分解の雑音はクラメール・ラオの下限の 0.995 / 0.997 倍。壊れ方: 電荷共有 25 % を知らずに分解すると肉が Al に化け、単色の近似は肉 6 cm で Al −1.5 mm に偏る。埋まった異物の見かけの Z は密度でも動く(PVC は 13.9 が 18.7 に見える)。学習 0、較正 0、門 21 件。 [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dual_energy_xray.py)
  使った Fullseye の op: `basis_decomposition_crlb` · `basis_material_decompose` · `dual_energy_separability` · `dual_kvp_channels` · `ellipse` · `material_effective_z` · `material_from_sellmeier` · `material_xray_attenuation` · `material_xray_constants` · `photon_counting_channels` · `reflect` · `xray_beam_quality` · `xray_channel_projection` · `xray_tube_spectrum`

</div>

## 準目玉

<div class="vg">
<a href="../articles/assets/poc/poc_malecns_activity_wave/01_activity_wave_connectome_vs_shuffle.gif"><img src="thumbs/poc_malecns_activity_wave.jpg" alt="ハエの脳の波" loading="lazy" width="320" height="320"><b>&#9654;</b><span>ハエの脳の波</span></a>
<a href="../articles/assets/poc/poc_bump_coplanarity/06_absorbed_defect.png"><img src="thumbs/poc_bump_coplanarity.jpg" alt="バンプ共平面性" loading="lazy" width="320" height="320"><span>バンプ共平面性</span></a>
<a href="../articles/assets/poc/poc_laser_line_speckle_floor/01_line.png"><img src="thumbs/poc_laser_line_speckle_floor.jpg" alt="光切断のスペックルの床" loading="lazy" width="320" height="320"><span>光切断のスペックルの床</span></a>
<a href="../articles/assets/poc/poc_real_stereo_depth/01_scene.png"><img src="thumbs/poc_real_stereo_depth.jpg" alt="実写のステレオ" loading="lazy" width="320" height="320"><span>実写のステレオ</span></a>
<a href="../articles/assets/poc/poc_public_camera_heading_real/06_numbers.png"><img src="thumbs/poc_public_camera_heading_real.jpg" alt="カメラの向き(実写)" loading="lazy" width="320" height="320"><span>カメラの向き(実写)</span></a>
<a href="../articles/assets/poc/poc_iqa_tid2013/03_tid2013_srocc_by_distortion.png"><img src="thumbs/poc_iqa_tid2013.jpg" alt="画質指標と TID2013" loading="lazy" width="320" height="320"><span>画質指標と TID2013</span></a>
</div>

<div class="vl" markdown="1">

- [ハエの脳の波](../articles/assets/poc/poc_malecns_activity_wave/01_activity_wave_connectome_vs_shuffle.gif) (GIF): 前の展示は「読み出し精度ではコネクトームと乱数グラフの差が出ない」で終わった。この展示は同じ reservoir を**見る**ことに使う: MaleCNS(雄の全中枢神経系)で soma の座標を持つニューロンのうちシナプス総数の上位 3,000 体の部分グラフ(344,719 辺)に、右の視葉だけへ刺激を入れ、活動が伝わる様子を脳と VNC の立体(灰 = 141,781 個の soma、橙 = 右、青 = 左)を回しながら描く。隣は各ニューロンの入出次数を保って辺を繋ぎ替えたグラフに**同じ刺激・同じ入力行列**。実測: コネクトームでは刺激の重心からの活動の平均距離が 88 → 230 µm と 17 步かけて伸び、点く順は視葉(潜時 0)→ 中枢(2)→ 下行(2)で、36 步では VNC に届かない。shuffle は 3 步で 300 µm に散り、遠い 1/4 のニューロンの 93 % が最初の周期内に点く(コネクトームは 0 %)。精度では見えなかった配線の空間構造が、動きでは見える。輝度の尺度は全コマで 1 つ。回転する図のほかに、同じ瞬間を背側・側面・体軸方向の 3 方向から同時に見る図も置く(`views=`)。生データは repo に入れない(手元の feather から部分グラフを作ってキャッシュ、無ければ距離依存の合成の代替で同じ経路)。
  右の視葉への刺激が、実際の配線(左)と、次数を保って繋ぎ替えた配線(右)を伝わる。 **実配線では活動の平均距離が 88 → 230 µm と 17 步かけて伸びる。繋ぎ替えでは 3 步で 300 µm に散る。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_malecns_activity_wave.py)
  使った Fullseye の op: `reservoir_from_graph` · `reservoir_states` · `graph_activity_spread` · `graph_activation_latency` · `points_activity_video`
- [バンプ共平面性](../articles/assets/poc/poc_bump_coplanarity/06_absorbed_defect.png) (図): 基板のそりを高さ場から引くとき、補正面が本物の低いバンプまで吸収しないかが問題になる。短小ピラーを仕込んだ高さ場へ曲面を当て、二次補正後の読み取り誤差1.23 µmを測った。次数を増やしても精度は上がらず、広い低次不良はそりとして消えて見逃しが増える。
  Cu ピラー 256 本の高さ場に、そり PV 50 µm と個体差 1σ 4 µm、短小バンプ 6 本を仕込んで測り返す。そりを引かずに平面だけ引くゼロ点は読み取り RMS 誤差 8.84 µm(個体差の 2.2 倍)で、誤検出 58 本の裏で本物の短小を 1 本見逃す。2 次曲面を引くと 1.23 µm・誤検出 0 になるが、3 次にすると 1.37 µm と逆に悪くなる(仕込んだ高次成分が 4 次のロブなので 3 次では取れず、増えた項が個体差を吸う)。崖は幾何で予測でき、2 次が個体差 1σ に並ぶのは PV 169.9 µm の予測に対して実測 169.4 µm。★中央が 8 µm 沈む本物の低次不良を足すと、残差からは 88.2 % 消える一方で短小の検出数は 5→5 本のまま変わらず、見逃しだけが 0→2 本に増える ―― 消えた分は「そり 30.06→36.20 µm」に化けている。 [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bump_coplanarity.py)
  使った Fullseye の op: `background_flatten` · `auto_threshold` · `blob_label` · `blob_features` · `fit_poly_surface` · `eval_poly_surface` · `surface_form_error`
- [光切断のスペックルの床](../articles/assets/poc/poc_laser_line_speckle_floor/01_line.png) (図): 溶接ビード PoC の続編。同じ光条をなめらかな帯 + 加法雑音ではなくコヒーレント結像(粗面の位相 → 観察開口の瞳 → |E|²)で描き直した。真値は描画に入れた高さ。★★加法雑音で輝度最大の画素より 8.6 倍良かった 3 点の対数放物線は、スペックルでは輝度最大と同じ誤差(12.7 vs 13.1 µm)に落ちて重心(6.4 µm)の 2 倍悪い —— 山の 3 点はいちばん明るい粒を追う。列ごとの重心は Dorsch の床 C·λ/(2π sin u sin θ) = 6.9 µm の 0.93 倍。★★静止した部品は 100 枚平均しても 6.91 → 6.79 µm、部品を動かすと 1/√N(0.099 倍)。加法雑音のモデルは静止のまま下がると言ってしまう。★開口と三角測量角を振った誤差は式の線に傾き −0.94 / −0.99 で乗り、実測 / 式は 0.84〜0.90。★★画素を 4 倍にすると見た目のコントラストは 1.02 → 0.80 に鈍るが、重心は 1.6e-13 µm しか動かない。検査 17 件・図 5 枚。
  溶接ビード PoC の続編。同じ光条をなめらかな帯 + 加法雑音ではなくコヒーレント結像(粗面の位相 → 観察開口の瞳 → |E|²)で描き直した。真値は描画に入れた高さ。★★加法雑音で輝度最大の画素より 8.6 倍良かった 3 点の対数放物線は、スペックルでは輝度最大と同じ誤差(12.7 vs 13.1 µm)に落ちて重心(6.4 µm)の 2 倍悪い —— 山の 3 点はいちばん明るい粒を追う。列ごとの重心は Dorsch の床 C·λ/(2π sin u sin θ) = 6.9 µm の 0.93 倍。★★静止した部品は 100 枚平均しても 6.91 → 6.79 µm、部品を動かすと 1/√N(0.099 倍)。加法雑音のモデルは静止のまま下がると言ってしまう。★開口と三角測量角を振った誤差は式の線に傾き −0.94 / −0.99 で乗り、実測 / 式は 0.84〜0.90。★★画素を 4 倍にすると見た目のコントラストは 1.02 → 0.80 に鈍るが、重心は 1.6e-13 µm しか動かない。検査 17 件・図 5 枚。 [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_laser_line_speckle_floor.py)
  使った Fullseye の op: `laser_line_coherent` · `triangulation_speckle_limit` · `speckle_statistics` · `speckle_field` · `speckle_reduction` · `coherent_image`
- [実写のステレオ](../articles/assets/poc/poc_real_stereo_depth/01_scene.png) (図): この博物館で初めて**実写**を通した 1 本(Middlebury 2014 motorcycle、真値視差つき)。★配布元の注記は真値の穴を NaN と書いているが実際は +inf で、np.nanmedian は中央視差を 42.55 px でなく 44.97 px と答える(isfinite で判定している fill_disparity と apply_cmap は正しく穴として扱った)。★既定 max_disp=16 は bad2 95.06 % ―― 真の最大視差 59.91 px を下回る設定は前景を丸ごと失うので、崖は 48 と 64 の間に立つ(幾何から先に言える)。ゼロ点 94.04 % に対し SGM 15.81 %、信頼度で下位 4 割を捨てると 6.80 %。★★距離に落とすところで形が反り返る: depth_from_disparity に主点オフセット doffs が無く、実写の校正値 31.086 px を無視すると距離が 1.519〜5.243 倍にばらけ、最良の単一スケール 0.3733 を掛けてなお残差 958.3 mm RMS(奥行きレンジ 2889 mm の 33.2 %)、遠い面は +1676 mm 押し出され近い面は -926 mm 引き込まれる。この PoC で doffs を引数に足した(閉形式と最大差 0 mm)。★census は実装が弱いのではなく 64 bit パックで窓が 7 で頭打ち(3/5/7 で 75.27/48.62/35.44 % と伸びている途中)。
  この博物館で初めて**実写**を通した 1 本(Middlebury 2014 motorcycle、真値視差つき)。★配布元の注記は真値の穴を NaN と書いているが実際は +inf で、np.nanmedian は中央視差を 42.55 px でなく 44.97 px と答える(isfinite で判定している fill_disparity と apply_cmap は正しく穴として扱った)。★既定 max_disp=16 は bad2 95.06 % ―― 真の最大視差 59.91 px を下回る設定は前景を丸ごと失うので、崖は 48 と 64 の間に立つ(幾何から先に言える)。ゼロ点 94.04 % に対し SGM 15.81 %、信頼度で下位 4 割を捨てると 6.80 %。★★距離に落とすところで形が反り返る: depth_from_disparity に主点オフセット doffs が無く、実写の校正値 31.086 px を無視すると距離が 1.519〜5.243 倍にばらけ、最良の単一スケール 0.3733 を掛けてなお残差 958.3 mm RMS(奥行きレンジ 2889 mm の 33.2 %)、遠い面は +1676 mm 押し出され近い面は -926 mm 引き込まれる。この PoC で doffs を引数に足した(閉形式と最大差 0 mm)。★census は実装が弱いのではなく 64 bit パックで窓が 7 で頭打ち(3/5/7 で 75.27/48.62/35.44 % と伸びている途中)。 [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_stereo_depth.py)
  使った Fullseye の op: `disparity_map` · `disparity_sgm` · `disparity_census` · `disparity_subpixel` · `disparity_confidence` · `fill_disparity` · `depth_from_disparity` · `colorize_disparity` · `apply_cmap`
- [カメラの向き(実写)](../articles/assets/poc/poc_public_camera_heading_real/06_numbers.png) (図): 合成(poc_public_camera_heading)では「太陽 = 飽和した小さな円盤」で足りたが、実写の道路カメラは違った。フィンランド Fintraffic 天候カメラ(807 局、CC BY 4.0、鍵なし)の 9 月 20〜21 日 24 時間分から太陽高度 2〜12° のフレームだけ探針すると、見た目の門(sun_pixel_position)は局名の白い文字・標識・白い車・レンズの水滴を太陽と言い(最初の探針で 24/24 誤検出)、太陽は円盤でなく露出で大きさの変わるブルームで上端の局名帯で切れ、カメラは道路を見下ろして空は上 3 分の 1しか無い。そこで geocam に 2 op を足した: sun_bloom_fit(最大の飽和塊の切れていない縁に Kåsa の円を当てて中心を返す。重心は切れた側の反対へ平均 12 px 偏る)と camera_orientation_from_sun_candidates(フレームごとの候補から、固定カメラで太陽の速さで動く 1 本を RANSAC で選び、道路カメラの事前知識 |roll| ≤ 12°・pitch −40〜0°・水平画角 25〜120° で非物理な仮説を捨て、焦点距離も同時に探索する。地平線下の時刻は投票しない)。807 局 × 24 時間で追えた日没は 1 本(E18・Hamina、公式メタデータの向きは UNKNOWN): 5 枚(15:01〜16:01 UTC)から yaw 267.9°・pitch −4.6°・roll 0.9°・f 1439 px(水平画角 48°)、残差 0.34°。独立な検算 = 同じ姿勢で画像中の車線の消失点(昼のフレーム複数の medoid)を世界方位に変えると 272.7°、OpenStreetMap の E18 の路線方位は 275.3°、差 2.5°。弱い自由度は隠さない: 1 枚抜きで yaw は 1.3° しか動かないが roll は 10°、f は 2 % 動く(1 時間の低仰角の弧の限界)。同じ写真で見た目の門は 22 回「太陽」と言い、正確 3・太陽だが中心ずれ 2・別の物 17。生画像は commit せず、集計(時刻・円当て・消失点・路線方位)だけを置く。出典 Fintraffic / Digitraffic(CC BY 4.0)、OpenStreetMap(ODbL)。
  合成(poc_public_camera_heading)では「太陽 = 飽和した小さな円盤」で足りたが、実写の道路カメラは違った。フィンランド Fintraffic 天候カメラ(807 局、CC BY 4.0、鍵なし)の 9 月 20〜21 日 24 時間分から太陽高度 2〜12° のフレームだけ探針すると、見た目の門(sun_pixel_position)は局名の白い文字・標識・白い車・レンズの水滴を太陽と言い(最初の探針で 24/24 誤検出)、太陽は円盤でなく露出で大きさの変わるブルームで上端の局名帯で切れ、カメラは道路を見下ろして空は上 3 分の 1しか無い。そこで geocam に 2 op を足した: sun_bloom_fit(最大の飽和塊の切れていない縁に Kåsa の円を当てて中心を返す。重心は切れた側の反対へ平均 12 px 偏る)と camera_orientation_from_sun_candidates(フレームごとの候補から、固定カメラで太陽の速さで動く 1 本を RANSAC で選び、道路カメラの事前知識 |roll| ≤ 12°・pitch −40〜0°・水平画角 25〜120° で非物理な仮説を捨て、焦点距離も同時に探索する。地平線下の時刻は投票しない)。807 局 × 24 時間で追えた日没は 1 本(E18・Hamina、公式メタデータの向きは UNKNOWN): 5 枚(15:01〜16:01 UTC)から yaw 267.9°・pitch −4.6°・roll 0.9°・f 1439 px(水平画角 48°)、残差 0.34°。独立な検算 = 同じ姿勢で画像中の車線の消失点(昼のフレーム複数の medoid)を世界方位に変えると 272.7°、OpenStreetMap の E18 の路線方位は 275.3°、差 2.5°。弱い自由度は隠さない: 1 枚抜きで yaw は 1.3° しか動かないが roll は 10°、f は 2 % 動く(1 時間の低仰角の弧の限界)。同じ写真で見た目の門は 22 回「太陽」と言い、正確 3・太陽だが中心ずれ 2・別の物 17。生画像は commit せず、集計(時刻・円当て・消失点・路線方位)だけを置く。出典 Fintraffic / Digitraffic(CC BY 4.0)、OpenStreetMap(ODbL)。 [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_public_camera_heading_real.py)
  使った Fullseye の op: `camera_orientation_from_sun_candidates` · `sun_position`
- [画質指標と TID2013](../articles/assets/poc/poc_iqa_tid2013/03_tid2013_srocc_by_distortion.png) (図): 「自作の罠を自分で解くのは限界」を受けて、真値を外から持ち込む画像側の第 1 弾。真値 = TID2013(Ponomarenko ほか、25 参照 × 24 歪み × 5 水準 = 3,000 枚、971 人の MOS)、基準 = 作者が配布物に同梱した 14 指標の値(psnr.txt / ssim.txt …)と公表の順位相関表。新モジュール iqatid(11 op): 作者の輝度規約 = BT.601 limited-range の整数 Y′(ページに明記が無く、実測で特定。full-range だと 1.321 dB ずれる)、平均順位の Spearman と τ_b の Kendall(公表 14 本の表はこの 2 つで再現できる)、公表表、台帳の読みと検証(3,000 行・名前の集合がディスクと一致・大文字小文字無視)、評価・作者値との比較・歪み種 24 ごとの相関。図は MOS vs PSNR / SSIM の散布、歪み種ごとの SROCC(局所ブロック歪み 0.15 / 0.63、コントラスト 0.44 / 0.45、彩度 0.22 / 0.22 が弱い)、作者値との差のヒストグラム、14 指標の公表・再現・Fullseye 値の表、1 組の参照・歪み・SSIM マップ。門 21 本: 順位相関の閉形式(単調 1・反転 −1・同順位の手計算 ρ = 8.5/√95・τ_b = 7/√90、graphinv の第 2 実装と 1e-12)、Y′ の端点 16 / 235、PSNR の +1 LSB = 48.13 dB、SSIM 恒等 1、公表表 14 本。実データ 3,000 組(110 s): Fullseye の PSNR(RGB)は作者の PSNRc と 4 桁一致(max 0.00005 dB)、輝度 PSNR は参照 I12 以外の 2,774 組で max 0.00017 dB(I12 の 115 組は 28 画素の輝度が丁度 .5 で丸めの向きが食い違い 0.00058 dB —— 黙って除外せず 2 つの門に分けた)、SSIM(Y′)は max 0.000051、順位相関 PSNR 0.6395 / 0.4699(公表 0.640 / 0.470)・SSIM 0.6370 / 0.4635(0.637 / 0.464)、作者値 14 本の再現の最大差 0.00048。作者は輝度 PSNR の完全一致を 100000.0 と書く(111 行、全部 彩度変化)。正直に: 4 桁一致は作者と同じ原実装(旧 ssim_index.m 相当、11×11 ガウス σ1.5、縁を落とす、ダウンサンプル無し)の規約を踏んだからで、SSIM の性能(14 本中 10 位)の話ではない。FSIM / FSIMc / VIF / GMSD は未実装で公表値だけ表に出す。画像と MOS は repo に入れない(研究・教育目的のみの配布条件、FULLSEYE_TID2013_DATA)。CI では合成の門だけ走る。
  「自作の罠を自分で解くのは限界」を受けて、真値を外から持ち込む画像側の第 1 弾。真値 = TID2013(Ponomarenko ほか、25 参照 × 24 歪み × 5 水準 = 3,000 枚、971 人の MOS)、基準 = 作者が配布物に同梱した 14 指標の値(psnr.txt / ssim.txt …)と公表の順位相関表。新モジュール iqatid(11 op): 作者の輝度規約 = BT.601 limited-range の整数 Y′(ページに明記が無く、実測で特定。full-range だと 1.321 dB ずれる)、平均順位の Spearman と τ_b の Kendall(公表 14 本の表はこの 2 つで再現できる)、公表表、台帳の読みと検証(3,000 行・名前の集合がディスクと一致・大文字小文字無視)、評価・作者値との比較・歪み種 24 ごとの相関。図は MOS vs PSNR / SSIM の散布、歪み種ごとの SROCC(局所ブロック歪み 0.15 / 0.63、コントラスト 0.44 / 0.45、彩度 0.22 / 0.22 が弱い)、作者値との差のヒストグラム、14 指標の公表・再現・Fullseye 値の表、1 組の参照・歪み・SSIM マップ。門 21 本: 順位相関の閉形式(単調 1・反転 −1・同順位の手計算 ρ = 8.5/√95・τ_b = 7/√90、graphinv の第 2 実装と 1e-12)、Y′ の端点 16 / 235、PSNR の +1 LSB = 48.13 dB、SSIM 恒等 1、公表表 14 本。実データ 3,000 組(110 s): Fullseye の PSNR(RGB)は作者の PSNRc と 4 桁一致(max 0.00005 dB)、輝度 PSNR は参照 I12 以外の 2,774 組で max 0.00017 dB(I12 の 115 組は 28 画素の輝度が丁度 .5 で丸めの向きが食い違い 0.00058 dB —— 黙って除外せず 2 つの門に分けた)、SSIM(Y′)は max 0.000051、順位相関 PSNR 0.6395 / 0.4699(公表 0.640 / 0.470)・SSIM 0.6370 / 0.4635(0.637 / 0.464)、作者値 14 本の再現の最大差 0.00048。作者は輝度 PSNR の完全一致を 100000.0 と書く(111 行、全部 彩度変化)。正直に: 4 桁一致は作者と同じ原実装(旧 ssim_index.m 相当、11×11 ガウス σ1.5、縁を落とす、ダウンサンプル無し)の規約を踏んだからで、SSIM の性能(14 本中 10 位)の話ではない。FSIM / FSIMc / VIF / GMSD は未実装で公表値だけ表に出す。画像と MOS は repo に入れない(研究・教育目的のみの配布条件、FULLSEYE_TID2013_DATA)。CI では合成の門だけ走る。 [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_iqa_tid2013.py)
  使った Fullseye の op: `tid2013_evaluate` · `tid2013_compare` · `rank_spearman` · `rank_kendall_b` · `psnr` · `ssim`

</div>

## シリーズ記事

<div class="vser">
<a href="https://qiita.com/furuse-kazufumi/items/c1606bcfa2085d204ad6"><img src="thumbs/series_museum.gif" alt="紙面の計測館" loading="lazy" width="480" height="270"><strong>紙面の計測館</strong><span>真値を自分で仕込んだ PoC の展示館</span></a>
<a href="https://qiita.com/furuse-kazufumi/items/b6498dc822bf9eed100f"><img src="thumbs/series_table_tennis.gif" alt="卓球" loading="lazy" width="480" height="270"><strong>卓球</strong><span>跳ねと摩擦を映像から測る</span></a>
<a href="https://qiita.com/furuse-kazufumi/items/1f128b8a36df373c11c7"><img src="thumbs/series_driving.gif" alt="自動運転" loading="lazy" width="480" height="270"><strong>自動運転</strong><span>定理と第 2 実装で採点する</span></a>
<a href="https://qiita.com/furuse-kazufumi/items/331af639c2b9a1493576"><img src="thumbs/series_connectome.gif" alt="コネクトーム(脳の配線図)" loading="lazy" width="480" height="270"><strong>コネクトーム(脳の配線図)</strong><span>ハエの視覚モデルを体に載せて測る</span></a>
<a href="https://qiita.com/furuse-kazufumi/items/57e2f1e5a09165e58b65"><img src="thumbs/series_humanoid.gif" alt="ヒューマノイド運動会" loading="lazy" width="480" height="270"><strong>ヒューマノイド運動会</strong><span>画像処理が審判をする自宅の運動会</span></a>
</div>

## Fullseye とは

光学設計や三次元計測などのセンシングを含む物理シミュレーションと古典画像処理を、MCP と RAG で AI に渡し、課題ごとに組み合わせを考えさせ、型整合性と真値つき評価で確かめながら対話的に課題を解く基盤です。オープンソース(Apache-2.0)。

[Fullseye について、もう少し詳しく読む](about.md)

[おまけ:そのほかの PoC](more.md)も見る。

<details markdown="1">
<summary><b>試してみる</b> (Python 3.11)</summary>

```
pip install fullseye
git clone https://github.com/furuse-kazufumi/fullseye
cd fullseye
python examples/poc_focus_stacking.py
```

焦点合成の PoC が約 20 秒で走り、真値に対する数字と `PASS` を印字します。図は `out/figures/poc_focus_stacking/` に書かれます。

</details>

<details markdown="1">
<summary><b>リンク</b></summary>

- [GitHub(ソースコード)](https://github.com/furuse-kazufumi/fullseye)
- [ギャラリー(全部の図)](../GALLERY.md)
- [演算子を探す・AI(RAG)から使う](../AI_RAG_GUIDE.md) · [MCP から使う](../MCP.md)
- [ドキュメント索引](../README.md)

</details>

<details markdown="1">
<summary><b>論文情報</b></summary>

- **題目**: Fullseye：型付き演算子と物理シミュレーションに基づく画像検査・三次元計測基盤
- **著者**: 古瀬 和文(個人研究者)
- **発表**: ViEW2026 ビジョン技術の実利用ワークショップ
- **論文 PDF**: [English](paper/101_en.pdf) · [简体中文](paper/101_zh.pdf)(日本語: 2026-11-26 以降に掲載)

**概要**: 画像検査・三次元計測の処理を，入出力のデータ型を宣言した演算子の連鎖として組み立て，物理・撮像シミュレーションで作った真値に対して定量評価し，処理手順・評価・失敗条件を記録して再利用できるオープンソース基盤Fullseyeを提案する．約3,000の型付き演算子，型の不整合を実行前に退ける検査，多言語の演算子検索（RAG），真値つきの200本超の実証プログラムからなり，代表例の定量評価と，合成・実測・実機の検証段階の区別について報告する．

</details>
