<div class="vlang" markdown="1">

**日本語** · [English](en/index.md) · [简体中文](zh/index.md) · [繁體中文](tw/index.md) · [한국어](ko/index.md) · [Deutsch](de/index.md) · [हिन्दी](hi/index.md)

</div>

# Fullseye — ViEW2026

物理シミュレーションと画像処理を AI と組み合わせて、真値で確かめる。

タイルを押すと動画・図が開きます(▶ = 動く)。

<style>
.vlang { font-size: 14px; line-height: 2; }
.vg { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin: 12px 0 20px; }
@media (min-width: 600px) { .vg { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
@media (min-width: 900px) { .vg { grid-template-columns: repeat(4, minmax(0, 1fr)); } }
.vg a { display: block; position: relative; text-decoration: none; color: inherit; }
.vg img { display: block; width: 100%; max-width: 100%; height: auto; aspect-ratio: 1 / 1; object-fit: cover; border-radius: 6px; background: #222; }
.vg b { position: absolute; top: 6px; right: 6px; background: rgba(0,0,0,.6); color: #fff; font-size: 12px; padding: 1px 6px; border-radius: 9px; }
.vg span { display: block; font-size: 13px; line-height: 1.3; margin-top: 3px; }
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
    else if (/^(en|ko|de|hi)/.test(n)) t = n.slice(0, 2);
    if (t) location.replace(t + "/");
  } catch (e) {}
})();
</script>

<div class="vg">
<a href="../articles/assets/poc/poc_real_defect_floor/02_defect_floor_sweep.gif"><img src="thumbs/poc_real_defect_floor.jpg" alt="薄い傷の検出限界" loading="lazy" width="320" height="320"><b>&#9654;</b><span>薄い傷の検出限界</span></a>
<a href="../articles/assets/poc/poc_active_contours/06_u_shape_snakes.mp4"><img src="thumbs/poc_active_contours.jpg" alt="動的輪郭" loading="lazy" width="320" height="320"><b>&#9654;</b><span>動的輪郭</span></a>
<a href="../articles/assets/poc/poc_dic_strain/05_tensile_ramp.mp4"><img src="thumbs/poc_dic_strain.jpg" alt="DIC ひずみ" loading="lazy" width="320" height="320"><b>&#9654;</b><span>DIC ひずみ</span></a>
<a href="../articles/assets/poc/poc_focus_stacking/05_focus_sweep.mp4"><img src="thumbs/poc_focus_stacking.jpg" alt="焦点合成" loading="lazy" width="320" height="320"><b>&#9654;</b><span>焦点合成</span></a>
<a href="../articles/assets/poc/poc_registration_basin/05_icp_basin_iterations.mp4"><img src="thumbs/poc_registration_basin.jpg" alt="点群の位置合わせ" loading="lazy" width="320" height="320"><b>&#9654;</b><span>点群の位置合わせ</span></a>
<a href="../articles/assets/poc/poc_stockpile_volume/07_scan_orbit.mp4"><img src="thumbs/poc_stockpile_volume.jpg" alt="堆積物の体積" loading="lazy" width="320" height="320"><b>&#9654;</b><span>堆積物の体積</span></a>
<a href="../articles/assets/poc/poc_ct_fidelity/01_recon_sweep.png"><img src="thumbs/poc_ct_fidelity.jpg" alt="CT 再構成" loading="lazy" width="320" height="320"><span>CT 再構成</span></a>
<a href="../articles/assets/poc/poc_ct_void_morphology/13_section_sweep.mp4"><img src="thumbs/poc_ct_void_morphology.jpg" alt="CT のボイド" loading="lazy" width="320" height="320"><b>&#9654;</b><span>CT のボイド</span></a>
<a href="../articles/assets/poc/poc_interferometry_step/05_step_sweep.mp4"><img src="thumbs/poc_interferometry_step.jpg" alt="白色干渉の段差" loading="lazy" width="320" height="320"><b>&#9654;</b><span>白色干渉の段差</span></a>
<a href="../articles/assets/poc/poc_polarization_specular/03_separation.png"><img src="thumbs/poc_polarization_specular.jpg" alt="偏光で鏡面除去" loading="lazy" width="320" height="320"><span>偏光で鏡面除去</span></a>
<a href="../articles/assets/poc/poc_photoelasticity/03_load_and_isoclinics.mp4"><img src="thumbs/poc_photoelasticity.jpg" alt="光弾性の応力" loading="lazy" width="320" height="320"><b>&#9654;</b><span>光弾性の応力</span></a>
<a href="../articles/assets/poc/poc_thermography_ndt/02_depth_map.png"><img src="thumbs/poc_thermography_ndt.jpg" alt="熱画像の欠陥深さ" loading="lazy" width="320" height="320"><span>熱画像の欠陥深さ</span></a>
<a href="../articles/assets/poc/poc_motion_magnification/05_magnify_video.mp4"><img src="thumbs/poc_motion_magnification.jpg" alt="微小振動の拡大" loading="lazy" width="320" height="320"><b>&#9654;</b><span>微小振動の拡大</span></a>
<a href="../articles/assets/poc/poc_table_tennis_bounce/01_drop_test.mp4"><img src="thumbs/poc_table_tennis_bounce.jpg" alt="卓球の跳ね" loading="lazy" width="320" height="320"><b>&#9654;</b><span>卓球の跳ね</span></a>
<a href="../articles/assets/poc/poc_compound_eye/02_compound_eye_superposition.png"><img src="thumbs/poc_compound_eye.jpg" alt="複眼の光場" loading="lazy" width="320" height="320"><span>複眼の光場</span></a>
<a href="../articles/assets/poc/poc_pegsim_insertion/04_pegsim_insert_corrected.gif"><img src="thumbs/poc_pegsim_insertion.jpg" alt="ペグ挿入" loading="lazy" width="320" height="320"><b>&#9654;</b><span>ペグ挿入</span></a>
<a href="../articles/assets/poc/poc_air_hockey_intercept/02_airhockey_prediction_cone_narrows.gif"><img src="thumbs/poc_air_hockey_intercept.jpg" alt="エアホッケー" loading="lazy" width="320" height="320"><b>&#9654;</b><span>エアホッケー</span></a>
<a href="../articles/assets/poc/poc_tacsim_elastic_membrane/03_tacsim_force_sweep.gif"><img src="thumbs/poc_tacsim_elastic_membrane.jpg" alt="視触覚センサ" loading="lazy" width="320" height="320"><b>&#9654;</b><span>視触覚センサ</span></a>
</div>

## 何が見えるか・測った数字

数字はどれも、各 PoC が仕込んだ真値(閉形式・解析解・公表値)に対する実測で、PoC を実行すると同じ値が印字されます。

<div class="vl" markdown="1">

**画像検査・外観計測**

- [薄い傷の検出限界](../articles/assets/poc/poc_real_defect_floor/02_defect_floor_sweep.gif) (GIF): 実写の地(レンガ)と、雑音の量をそろえた合成の地に、同じ欠陥を濃くしながら仕込む。 **雑音の量をそろえても、実写の地の検出限界は合成の 2.03〜3.47 倍(位置・振幅が既知の欠陥に対して)。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_defect_floor.py)
- [動的輪郭](../articles/assets/poc/poc_active_contours/06_u_shape_snakes.mp4) (動画): U 字の凹部に、古典の snake(赤)は入れず、GVF(青)は奥まで入る。緑が真の縁。 **外力だけを GVF に替えると Dice 0.993(真の縁に対して)。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_active_contours.py)
- [DIC ひずみ](../articles/assets/poc/poc_dic_strain/05_tensile_ramp.mp4) (動画): 引張試験の荷重を上げながら、スペックル画像からひずみ地図を読む(試験機は同時に 2 度回る)。 **真のひずみ 3000 µε。微小ひずみは回転で 2341 µε と過小、Green-Lagrange は 2961 µε(理論 3005 µε)。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dic_strain.py)

**三次元計測・幾何処理**

- [焦点合成](../articles/assets/poc/poc_focus_stacking/05_focus_sweep.mp4) (動画): 焦点を 17 枚掃引しながら、全焦点画像と距離画像が育っていく。 **全焦点 PSNR 33.69 dB(中央の 1 枚は 28.52 dB)、深度誤差 0.467 mm(テクスチャあり)。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_focus_stacking.py)
- [点群の位置合わせ](../articles/assets/poc/poc_registration_basin/05_icp_basin_iterations.mp4) (動画): 初期の回転ずれ 30 / 90 / 150 度から、ICP を 1 反復ずつ動かす。 **60 反復後の回転誤差: 30 度と 90 度は 0.6 度(成功)、150 度は 179.5 度(失敗)。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_registration_basin.py)
- [堆積物の体積](../articles/assets/poc/poc_stockpile_volume/07_scan_orbit.mp4) (動画): 山の周りを回りながら、3-D スキャンの位置を 1 → 3 か所に増やす。色は補間面と真の面の差。 **在庫量の誤差は +17.20 % → +0.05 %(真の底面、体積の真値は閉形式 3572.6089 m³)。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_stockpile_volume.py)

**X線CT・ボリューム処理**

- [CT 再構成](../articles/assets/poc/poc_ct_fidelity/01_recon_sweep.png) (図): Shepp-Logan ファントムを投影 180 本 → 12 本で撮り直して再構成する。 **12 本の FBP は RMSE 0.2576 で空白画像 0.2420 にも負ける。質量の検算で −3.34 % の欠損を見つけ、−0.0099 % に直した。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_fidelity.py)
- [CT のボイド](../articles/assets/poc/poc_ct_void_morphology/13_section_sweep.mp4) (動画): ボイド率がほぼ同じ 2 条件の接合層を、断面を掃引しながら 3-D で回す(動画 4.3 MB)。 **ボイド率は 2.46 % 対 2.63 % なのに、界面からの距離の中央値は 60.0 µm 対 10.0 µm。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_void_morphology.py)

**光学・干渉・偏光**

- [白色干渉の段差](../articles/assets/poc/poc_interferometry_step/05_step_sweep.mp4) (動画): 仕込む段差を 0 → 0.90 µm に増やし、包絡線法と位相シフト法で測る。 **雑音 1 % で偏り 2.4 nm 以内(段差 50〜500 nm)。位相シフト法は 0.153 µm で λ/2 跳ぶ。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_interferometry_step.py)
- [偏光で鏡面除去](../articles/assets/poc/poc_polarization_specular/03_separation.png) (図): 偏光で鏡面反射を剥がした結果と、残った誤差の形。 **拡散成分の誤差は閉形式 R_p·E と一致し、ブリュースター角 56.31 度で 0。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_polarization_specular.py)
- [光弾性の応力](../articles/assets/poc/poc_photoelasticity/03_load_and_isoclinics.mp4) (動画): 円板に荷重をかけると縞が湧き出し、偏光子を回すと等傾線が動く。 **中心の縞次数 2.38(閉形式どおり)。op の偏光系は教科書の式と最大差 2.2e-16。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_photoelasticity.py)

**熱・音響・時系列**

- [熱画像の欠陥深さ](../articles/assets/poc/poc_thermography_ndt/02_depth_map.png) (図): フラッシュ加熱後の表面温度から、16 個の剥離の深さを読んだ地図。 **深さ 0.5 mm・直径 2 mm の欠陥は、当てはめの時間窓 25 秒で +612 %、4 秒に切ると −9 %。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_thermography_ndt.py)
- [微小振動の拡大](../articles/assets/poc/poc_motion_magnification/05_magnify_video.mp4) (動画): 0.1 px で揺れる表面。左が生の映像、右が 10 倍に拡大した映像。 **真の振幅 0.1000 px に対し、生から 0.10012、拡大後から 0.10013 px。拡大は見せる道具で、測定は良くならない。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_motion_magnification.py)
- [卓球の跳ね](../articles/assets/poc/poc_table_tennis_bounce/01_drop_test.mp4) (動画): ITTF の台の試験: 30 cm から球を落とし、跳ねた高さを動画から読む。 **動画から読んだ跳ねの高さ 23.0 cm(世界の真値 23.0 cm)。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_table_tennis_bounce.py)

**ロボット・空間知覚**

- [複眼の光場](../articles/assets/poc/poc_compound_eye/02_compound_eye_superposition.png) (図): 個眼アレイを光場センサとして合成し、同じ点を N 個眼で重ねる。 **SNR 利得は N=5 で 2.25(√5 = 2.24)、N=49 で 5.33(√49 = 7.00)。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_compound_eye.py)
- [ペグ挿入](../articles/assets/poc/poc_pegsim_insertion/04_pegsim_insert_corrected.gif) (GIF): 手首カメラで穴の位置を測って寄せ、柔らかい手首でペグを入れる(MuJoCo)。 **サーボ 7 回で真のずれ 2.24 → 0.03 mm。補正ありの挿入は 12 / 12 成功。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pegsim_insertion.py)
- [エアホッケー](../articles/assets/poc/poc_air_hockey_intercept/02_airhockey_prediction_cone_narrows.gif) (GIF): 粗いカメラでパックを追い、守備線との交点を予測する。コマが増えるほど予測の帯が細る。 **交点の 95 % 帯は N = 3 コマで 145 mm → N = 16 コマで 7 mm。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_air_hockey_intercept.py)
- [視触覚センサ](../articles/assets/poc/poc_tacsim_elastic_membrane/03_tacsim_force_sweep.gif) (GIF): 弾性膜を球で押す荷重を上げ、膜の画像から接触半径を読む。 **Hertz の閉形式に対し、接触半径の誤差 0.05〜0.26 %、荷重の誤差 0.14〜0.79 %(0.02〜0.12 N)。** [ソース](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_tacsim_elastic_membrane.py)

</div>

## Fullseye とは

光学設計や三次元計測などのセンシングを含む物理シミュレーションと古典画像処理を、MCP と RAG で AI に渡し、課題ごとに組み合わせを考えさせ、型整合性と真値つき評価で確かめながら対話的に課題を解く基盤です。オープンソース(Apache-2.0)。

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
- **論文 PDF**: 2026-11-26 以降に掲載

**概要**: 画像検査・三次元計測の処理を，入出力のデータ型を宣言した演算子の連鎖として組み立て，物理・撮像シミュレーションで作った真値に対して定量評価し，処理手順・評価・失敗条件を記録して再利用できるオープンソース基盤Fullseyeを提案する．約3,000の型付き演算子，型の不整合を実行前に退ける検査，多言語の演算子検索（RAG），真値つきの200本超の実証プログラムからなり，代表例の定量評価と，合成・実測・実機の検証段階の区別について報告する．

</details>
