> **言語 / Language**: **日本語** · [English](https://qiita.com/furuse-kazufumi/items/8a8f23e53b19ee8cdc10)

# 紙面の計測館 ―― 真値を自分で仕込んで、画像計測の「壊れる場所」を先に知る

![PoC museum montage](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/_hero_montage.jpg)

*↑ 展示の場面図を 12 枚並べたもの。どれも PoC スクリプト自身の出力で、記事のために描いた絵は 1 枚もありません。*

> 図と op の使い方は docs サイト [furuse.work](https://furuse.work/) と共通です。各展示の「使用 op」から op ノート(型契約・罠・図・Studio で走るプログラム)へ飛べます。AI に読ませるなら [AI_RAG_GUIDE](https://furuse.work/AI_RAG_GUIDE.html)。

## TL;DR

- 画像で「測る」仕事(ひび割れ幅、歯車の偏心、細胞の個数、星の明るさ、河川の水位…)を、**答えを自分で仕込んだ合成データ**(と、2026-09-08 に加わった実写 6 本)で採点する実行可能なスクリプト群を、画像処理ライブラリ Fullseye の `examples/poc_*.py` として公開しました。1 本ずつ `py -3.11 examples/poc_<名前>.py` で走り、数字は全部その場で印字されます。
- どの 1 本にも同じ 3 つが入っています: **真値(自分で仕込んだ正解)**、**ゼロ点(いちばん素朴なやり方の成績)**、**どこで壊れるかの崖**。「できました」ではなく「ここまでは信じてよく、ここから先は嘘になる」を数字で置く形です。
- 通して見えた 1 つの型 ―― **向きの逆な 2 つの失敗は打ち消し合い、まとめた 1 つの数字はそのときいちばん良く見える**。粒度分布・モアレ・雲量・海氷・細胞計数・除霞・タイムラプスで、別々の物理から同じ形が出ました。
- 展示は 9 つのウィング(産業検査 / 寸法・形状 / 医用・生物 / 天文・環境 / 撮像品質・復元 / 時系列を 3-D として測る / 幾何・校正 / 色・分離 / 法科学・文書)。自分の分野だけ拾ってもらえば足ります。
- 各スクリプトには実写へ差し替える口(`EXTEND` の印)があり、合成器 1 関数を差し替えれば採点の枠組みはそのまま自分のデータで動きます。使っている op はすべて docs サイトのノートに図つきで載っています。
- PoC を書くことでライブラリ側の穴(公開経路に出ていない実装、既定値が寛容側の op、窓が固定の op)も多数見つかりました。直したもの・直していないものを分けて末尾に書きます。

> 各展示の「使用 op」から、その op のノート(型契約・罠・図・Studio で走るプログラム)へ飛べます: [オペレータ目録](https://furuse.work/OP_CATALOG.html) / [op ノートの索引](https://furuse.work/ops/INDEX.html)。

## 用語(先に読むと楽)

- **PoC(proof of concept、概念実証)** —— 「この考え方で本当に測れるのか」を最小の実装で確かめる短いプログラム。ここでは 1 本 = 1 つの計測課題。
- **真値(ground truth)** —— 採点に使う正解。この展示の PoC は**ほとんどが真値を自分で作る**(既知の形・既知の変形・既知の雑音から画像を合成する)ので、推定値との差を丸め誤差の桁まで言えます。実写を使う 6 本は、真値の出どころを 3 通りに分けています —— 配布元が真値を付けているもの(ステレオ)、独立な 3 経路の一致で決めるもの(コイン)、**背景だけ本物にして対象は自分で仕込む**もの(深宇宙・免疫染色)。
- **ゼロ点(null baseline)** —— 「いちばん素朴なやり方」の成績。二値化して数える、1 枚目で較正して使い回す、何もしない、など。**ゼロ点に勝てない手法は、勝てないと書く**のが約束です。
- **閉形式(closed form)** —— 数値計算ではなく式で書ける答え。球冠の立体角、インボリュート歯形、円板圧縮の応力場、1 次元熱伝導の解。真値を閉形式で持てると、合成器そのものを検算できます。
- **打ち消し(cancellation)** —— 逆向きの 2 つの誤差が足し合わさって小さく見える現象。この展示の通し主題。**「合っている」のではなく「釣り合っているだけ」**を見分けるのが目的です。
- **対照群(control)** —— 原因を分けるために「その要因だけ止めた条件」を並べること。検出を止めて幾何だけの誤差を測る、ぼけをゼロにして減光だけの偏りを測る、など。

## 展示館のテーゼ

PoC を 1 本ずつ書いていた段階では、分野ごとに別々の話をしているつもりでした。粉体の粒度分布と、ディスプレイ検査のモアレと、全天カメラの雲量に、共通点があるとは思っていません。ところが並べると、同じ形の罠が別々の物理から出てきます。

**粒度分布**では、触れ合った粒子が 1 個に融合する誤りは大きい側へ、視野の縁で切れる誤りは小さい側へ引きます。面積率を 1.9 % から 28.2 % まで振ると代表径 D50 の誤差は -4.9 % から +4.5 % へ単調に動き、途中の **13.8 % でほぼゼロ(+0.55 %)を通ります**。そこは正確なのではなく、塊 140 個のうち融合 28 件と縁切れ 19 件が釣り合っているだけでした。**モアレ**では、ならしを強くするほどモアレの漏れ込み(過大)が減り本物のムラの減衰(過小)が増え、σ = 8 px で**合計誤差 +0.9 %** ―― 内訳は漏れ +8.3 % / 減衰 -7.4 %。**雲量**では、魚眼の幾何だけの誤差 -5.02 % と太陽まわりの偽陽性だけの誤差 +37.95 % が、素朴な数え方では +29.73 % に見えます。

同じ形は、**海氷密接度**(密接度 0.15 → 0.85 で偏りが -5.9 → +6.0 ポイントと符号を変え、0.49 付近でゼロを横切る)、**太陽の縁**(しきい値 0.26 付近でぼけの影響が消えるが、減光係数を変えると 0.38 へ動く)、**細胞計数**(過分割と過統合が釣り合う点で個数の偏り +0.3 個なのに分割誤りが 13.3 件残る)、**除霞**(全体 +4.04 dB の中身は近景 -1.49 dB の劣化)、**タイムラプス**(画素の面積で合体が早く見える分と、フレーム格子への丸めで遅く見える分が逆向き)にも出ました。

ここから引き出せる、書き手が消えても残る規則は 3 つです。**失敗の種類ごとに数える**(誤読と読み取り不能、過分割と過統合、曖昧な誤リンクと欠測による誤リンク ―― 畳んだ瞬間に「どちらを直すか」が決まらなくなる)。**対照群を置く**(原因を 1 つだけ止めた条件が無いと、打ち消しは「合っている」と区別できない)。**打ち消し点を「最良の条件」と呼ばない**(その点は条件を少し変えるだけで動く)。

## 最近の追加(新しい順)

- 2026-09-09 — 「回転しても同じ」と言える量はどれか —— 実写の硬貨を 72 角度で回して数える(poc_rotation_invariance_audit)
- 2026-09-08 — 光切断で溶接ビードを走査する ―― 分解能と遮蔽は同じノブの表裏(poc_weld_bead_scan_angle)
- 2026-09-08 — 竣工した部屋の壁を測る —— 外接直方体は寸法でなく部屋の向きを測っている(poc_asbuilt_wall_deviation)
- 2026-09-08 — 電極の呼吸を µm で測る ―― サブピクセルなら何でもよいわけではない(poc_battery_electrode_breathing)
- 2026-09-08 — 電極の屈曲度を CT から測る ―― 経験則は空隙率しか見ない(poc_battery_electrode_tortuosity)
- 2026-09-08 — バンプの共平面性を基板そりから分ける ―― 引きすぎると本物の不良も消える(poc_bump_coplanarity)
- 2026-09-08 — ひび割れの「幅」ではなく「伸び」を測る ―― 同じ壁を撮り返すと誤差の性質が変わる(poc_crack_width_timeseries)
- 2026-09-08 — ダイの傾きと TSV の位置ずれを 1 つの CT から分ける ―― 傾きは回転まで偽装する(poc_die_tilt_tsv_overlay)

## 展示室(全 116 展示)

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

使用 op(ノートへ): [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`smooth_funct_1d_mean`](https://furuse.work/ops/oned/function/smooth_funct_1d_mean.html)

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

使用 op(ノートへ): [`airy_pattern`](https://furuse.work/ops/optics/wave/airy_pattern.html) · [`create_funct_1d_pairs`](https://furuse.work/ops/oned/function/create_funct_1d_pairs.html) · [`derivate_funct_1d`](https://furuse.work/ops/oned/function/derivate_funct_1d.html) · [`get_y_value_funct_1d`](https://furuse.work/ops/oned/function/get_y_value_funct_1d.html) · [`invert_funct_1d`](https://furuse.work/ops/oned/function/invert_funct_1d.html) · [`mtf_diffraction`](https://furuse.work/ops/optics/imaging/mtf_diffraction.html) · [`psf_to_mtf`](https://furuse.work/ops/optics/imaging/psf_to_mtf.html)

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

使用 op(ノートへ): [`bearing_defect_frequencies`](https://furuse.work/ops/acoustics/bearing/bearing_defect_frequencies.html) · [`envelope_spectrum`](https://furuse.work/ops/acoustics/bearing/envelope_spectrum.html) · [`spectral_kurtosis`](https://furuse.work/ops/acoustics/bearing/spectral_kurtosis.html) · [`spectrum`](https://furuse.work/ops/oned/signal/spectrum.html) · [`synthesize_bearing_signal`](https://furuse.work/ops/acoustics/synthesis/synthesize_bearing_signal.html)

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

## 14. 混合廃棄物の材質選別 —— 何が消えるかは前処理の代数で決まる

[![混合廃棄物の材質選別 —— 何が消えるかは前処理の代数で決まる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_recycling_sorting/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_recycling_sorting/01_scene.png)

*↑ **混合廃棄物の材質選別 —— 何が消えるかは前処理の代数で決まる** ―― ベルト上の破片に材質・汚れ・濡れ・傾き・重なりを既知の量で仕込み、SWIR 64 バンドで分けます。破片ごとの劣化は s(λ)=g·R(λ)·exp(-w·A_w(λ))+(a·u(λ)+c) という閉形式なので、どの前処理が何に不変かが先に分かります —— 分光角は乗算 g に不変(乗算汚れ 0→0.8 で 0.995→0.990、傾き 0→70° で 0.993)、2 階微分は 1 次式 a·u+c を消す(加算 0→0.6 で生 SAM 0.995→0.827 に対し 2 次微分は全水準 0.995)。予想は 2 つ外れました: 濡れは 2 次微分でほとんど消せて(生 SAM 0.282 に対し 0.818)、理由は 2 階微分がガウス帯を 1/σ² で重みづけるから((43/70)²=0.37 倍)。連続体除去は加算が弱いうちは勝つ(0.983 対 0.865)のに強いと逆転する(0.736 対 0.827)。特徴の無い金属は微分で消え(再現率 0.06)、平坦度の門で 0.98 に戻ります。*

[![PP と PE は骨格が同じ(-CH2-)なのでわざと似せてある。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_recycling_sorting/02_library_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_recycling_sorting/02_library.png)

*↑ 測定の図 ―― PP と PE は骨格が同じ(-CH2-)なのでわざと似せてある。*

```
py -3.11 examples/poc_recycling_sorting.py
```

ソース: [examples/poc_recycling_sorting.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_recycling_sorting.py)

使用 op(ノートへ): [`overlay_labels`](https://furuse.work/ops/annotate/overlay/overlay_labels.html) · [`spectrum`](https://furuse.work/ops/oned/signal/spectrum.html)

## 15. 熱・振動・形状を束ねる設備保全 —— 3 つ見ても、同じものを 3 回見ていることがある

[![熱・振動・形状を束ねる設備保全 —— 3 つ見ても、同じものを 3 回見ていることがある](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_machine_condition_fusion/01_scene_machine_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_machine_condition_fusion/01_scene_machine.png)

*↑ **熱・振動・形状を束ねる設備保全 —— 3 つ見ても、同じものを 3 回見ていることがある** ―― 回転機械の 6 状態(正常・芯ずれ・アンバランス・軸受外輪傷・潤滑不良・ゆるみ)を、欠陥周波数の閉形式・板の定常フィン方程式の厳密解・仕込んだ芯ずれ量から作り、3 センサで識別します。基準条件の融合は 100.0 % ですが振動のみでも 100.0 % —— 熱も形状も 1 ポイントも足しません。芯ずれは振動・熱・形状のどれ 1 個でも 100.0 %(真値の重症度との相関 0.843 / 0.841 / 0.978 で、3 つは同じ数字の別の顔)。逆に熱だけでは 正常・アンバランス・ゆるみ が互いの中で 48/48 回まわり、振動を抜くと 100.0 % → 50.0 % / 31.2 % に落ちます。融合が効くのは振動が壊れてからで、雑音 σ=1.6 で 45.8 % → 78.1 %。崖は特徴 1 個の上で予測しました: 0.5X の次数ビンは T>2/f_r=68.6 ms(実測 50→70 ms の段で d' 2.45→4.32)、熱の広がりは半値直径 66 mm(実測 64 mm から崩れ 96 mm で d' 0.00)。側帯波は 1/T<FTF=86.1 ms と予測して外し、読み取り窓 1.2/FTF=103 ms が正しい条件でした。*

[![軸受外輪傷は狭く熱く、潤滑不良は広く熱い。最高温度だけ見ると同じ顔になる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_machine_condition_fusion/02_thermal_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_machine_condition_fusion/02_thermal_maps.png)

*↑ 測定の図 ―― 軸受外輪傷は狭く熱く、潤滑不良は広く熱い。最高温度だけ見ると同じ顔になる。*

```
py -3.11 examples/poc_machine_condition_fusion.py
```

ソース: [examples/poc_machine_condition_fusion.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_machine_condition_fusion.py)

使用 op(ノートへ): [`angle_between_lines`](https://furuse.work/ops/3d/geometry/angle_between_lines.html) · [`arrow`](https://furuse.work/ops/annotate/pointer/arrow.html) · [`bearing_defect_frequencies`](https://furuse.work/ops/acoustics/bearing/bearing_defect_frequencies.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`distance_point_line`](https://furuse.work/ops/3d/geometry/distance_point_line.html) · [`ellipse`](https://furuse.work/ops/annotate/shape/ellipse.html) · [`fuse`](https://furuse.work/ops/3d/tsdf_fusion/fuse.html) · [`jitter`](https://furuse.work/ops/3d/augment/jitter.html) · [`mat_pinv`](https://furuse.work/ops/math/linalg/mat_pinv.html) · [`rounded_rect`](https://furuse.work/ops/annotate/shape/rounded_rect.html) · [`spectrum`](https://furuse.work/ops/oned/signal/spectrum.html) · [`stat_correlation`](https://furuse.work/ops/math/stats/stat_correlation.html) · [`synthesize_bearing_signal`](https://furuse.work/ops/acoustics/synthesis/synthesize_bearing_signal.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html)

## 16. 音で漏水を掘り当てる ―― 相関がきれいでも、伝わる速さを間違えれば場所は外れる

[![音で漏水を掘り当てる ―― 相関がきれいでも、伝わる速さを間違えれば場所は外れる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leak_localization/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leak_localization/01_scene.png)

*↑ **音で漏水を掘り当てる ―― 相関がきれいでも、伝わる速さを間違えれば場所は外れる** ―― 120 m の埋設管の 2 点で漏水音を録り、到達時間差から位置を出す仕事を、源・音速・減衰・反射をすべて仕込んで再現した。音速が真値なら SNR 0 dB で 0.0107 m まで当たり(Knapp-Carter の下界 0.0091 m の 1.2 倍)、崖は予測 -20.1 dB に対し実測 -12.5 dB、その下では誤差が 36.0 m と探索窓いっぱいに飛ぶ。ところが音速を 10 % 誤るだけで 1.798 m ずれ(予測 (Δc/c)(x-L/2) = 1.800 m と 0.002 m 差)、途中で管種が鋳鉄から樹脂に変わる管路では時間差がちょうど 0 になって、鋳鉄・樹脂・その平均のどれを仮定しても 18.001 m 外す ―― 掛ける相手が 0 なので、音速をいくら較正しても直らない。反射では予想が外れ、GCC-PHAT は生の相関に 1 割しか勝たなかった(誤差 0.121 m のほぼ全部が偏りで、白色化するのは振幅、遅延を運ぶのは位相だから)。*

[![同じ漏水源に既知の遅れ 28.80 ms・距離に応じた減衰・独立な広帯域雑音を乗せた。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leak_localization/02_waveforms_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leak_localization/02_waveforms.png)

*↑ 測定の図 ―― 同じ漏水源に既知の遅れ 28.80 ms・距離に応じた減衰・独立な広帯域雑音を乗せた。*

```
py -3.11 examples/poc_leak_localization.py
```

ソース: [examples/poc_leak_localization.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_leak_localization.py)

使用 op(ノートへ): [`arrow`](https://furuse.work/ops/annotate/pointer/arrow.html) · [`bandpass`](https://furuse.work/ops/oned/signal/bandpass.html) · [`coherence`](https://furuse.work/ops/acoustics/dual/coherence.html) · [`correlation_score`](https://furuse.work/ops/reprconv/score/correlation_score.html) · [`phase_rad`](https://furuse.work/ops/2d/frequency/phase_rad.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html) · [`transfer_function`](https://furuse.work/ops/acoustics/dual/transfer_function.html)

## 17. 光切断で溶接ビードを走査する ―― 分解能と遮蔽は同じノブの表裏

[![光切断で溶接ビードを走査する ―― 分解能と遮蔽は同じノブの表裏](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_scan_angle/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_scan_angle/01_scene.png)

*↑ **光切断で溶接ビードを走査する ―― 分解能と遮蔽は同じノブの表裏** ―― すみ肉溶接の断面を閉形式で作り、余盛・脚長・のど厚・アンダーカット深さを既知関数で溶接線に沿って変えたうえで、三角測量角 θ を 15〜70 度で掃引しました。高さ分解能は 1/sinθ で良くなる一方、傾き cotθ を超えて登る面は自分の陰に入るので、遠側の母材面は幾何どおり θ = 37.0 度で背を向け、左アンダーカットはそれより早い 20.8〜34.5 度から欠け始めます(深い溝ほど早い)。危ないのは θ = 28 度で「測れた率」が 100 % のまま溝の区間の 25 % が欠測して深さが 27 % 過小に出ることと、さらに角度を上げると深い断面から集計を抜けて真値の平均が 0.260 → 0.047 mm と流れる生存者バイアスで、最適角は測定量ごとに 20 / 24 / 36 / 64 度とばらけます。*

[![θ を大きくすると高さの伸び K が増えて分解能は上がる(輝線の起伏が大きくなる)が、左半分の輝線が消えていく。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_scan_angle/02_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_weld_bead_scan_angle/02_frames.png)

*↑ 測定の図 ―― θ を大きくすると高さの伸び K が増えて分解能は上がる(輝線の起伏が大きくなる)が、左半分の輝線が消えていく。*

```
py -3.11 examples/poc_weld_bead_scan_angle.py
```

ソース: [examples/poc_weld_bead_scan_angle.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_weld_bead_scan_angle.py)

使用 op(ノートへ): [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`fit_plane_3d`](https://furuse.work/ops/3d/geometry/fit_plane_3d.html) · [`intersect_planes`](https://furuse.work/ops/3d/geometry/intersect_planes.html) · [`lines_gauss`](https://furuse.work/ops/2d/contour/lines_gauss.html) · [`normals_from_depth`](https://furuse.work/ops/3d/range_image/normals_from_depth.html) · [`occupancy_grid`](https://furuse.work/ops/3d/occupancy/occupancy_grid.html) · [`query_distance`](https://furuse.work/ops/3d/occupancy/query_distance.html)

## 18. 電極の屈曲度を CT から測る ―― 経験則は空隙率しか見ない

[![電極の屈曲度を CT から測る ―― 経験則は空隙率しか見ない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_tortuosity/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_tortuosity/01_scene.png)

*↑ **電極の屈曲度を CT から測る ―― 経験則は空隙率しか見ない** ―― リチウムイオン電池の電極塗工層を合成マイクロ CT で作り、空隙率と屈曲度を出す。現場の既定値 Bruggeman τ = ε^(-0.5) をゼロ点に置き、同じボリュームで定常拡散方程式を解いた真値と比べると、ε = 0.4448 で 1.499 対 1.843(-18.6 %)、ε を 0.691 → 0.168 と振ると誤差は -8.2 % → -69.1 % と単調に開く(実測の指数は 1.78 と 2.70 で、1.5 乗則はどちらでもない)。画像解析がよく報告する測地屈曲度 1.182 はその 2 乗が Bruggeman に 1 %以内で寄り添うだけで、真値には寄らない。決定打は対照群 ―― 空隙率を 0.4448 対 0.4510 に揃えて粒子を 4:1 に潰すと厚み方向の τ は 1.843 → 6.794(異方比 0.97 → 4.20)なのに、経験則は両方に同じ 1.5 を返す(面内は -8 % で当たって見え、厚み方向は -78 %)。閉気孔は最大 1.92 % で犯人ではなく、効いているのは粒子半径の 0.40 倍しかない首。解像度の崖を予測して掃引したが崖は無く、voxel を 5.5 倍粗くすると ε は -0.4 % しか動かないのに τ は +72 % ずれる ―― 警告なしに。*

[![左: 上端 1 / 下端 0 の濃度場。等濃度線が固相を避けて曲がる分が遠回り。右: bond ごとの散逸(明るいほど流れが集中している = 首)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_tortuosity/02_map_transport_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_tortuosity/02_map_transport.png)

*↑ 測定の図 ―― 左: 上端 1 / 下端 0 の濃度場。等濃度線が固相を避けて曲がる分が遠回り。右: bond ごとの散逸(明るいほど流れが集中している = 首)。*

```
py -3.11 examples/poc_battery_electrode_tortuosity.py
```

ソース: [examples/poc_battery_electrode_tortuosity.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_battery_electrode_tortuosity.py)

使用 op(ノートへ): [`vol_distance_transform`](https://furuse.work/ops/3d/medial/vol_distance_transform.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html)

## 19. バンプの共平面性を基板そりから分ける ―― 引きすぎると本物の不良も消える

[![バンプの共平面性を基板そりから分ける ―― 引きすぎると本物の不良も消える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bump_coplanarity/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bump_coplanarity/01_scene.png)

*↑ **バンプの共平面性を基板そりから分ける ―― 引きすぎると本物の不良も消える** ―― Cu ピラー 256 本の高さ場に、そり PV 50 µm と個体差 1σ 4 µm、短小バンプ 6 本を仕込んで測り返す。そりを引かずに平面だけ引くゼロ点は読み取り RMS 誤差 8.84 µm(個体差の 2.2 倍)で、誤検出 58 本の裏で本物の短小を 1 本見逃す。2 次曲面を引くと 1.23 µm・誤検出 0 になるが、3 次にすると 1.37 µm と逆に悪くなる(仕込んだ高次成分が 4 次のロブなので 3 次では取れず、増えた項が個体差を吸う)。崖は幾何で予測でき、2 次が個体差 1σ に並ぶのは PV 169.9 µm の予測に対して実測 169.4 µm。★中央が 8 µm 沈む本物の低次不良を足すと、残差からは 88.2 % 消える一方で短小の検出数は 5→5 本のまま変わらず、見逃しだけが 0→2 本に増える ―― 消えた分は「そり 30.06→36.20 µm」に化けている。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bump_coplanarity/02_deviation_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bump_coplanarity/02_deviation_map.png)

*↑ 測定の図*

```
py -3.11 examples/poc_bump_coplanarity.py
```

ソース: [examples/poc_bump_coplanarity.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bump_coplanarity.py)

使用 op(ノートへ): [`auto_threshold`](https://furuse.work/ops/2d/segmentation/auto_threshold.html) · [`background_flatten`](https://furuse.work/ops/3d/surface_fit/background_flatten.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`eval_poly_surface`](https://furuse.work/ops/3d/surface_fit/eval_poly_surface.html) · [`fit_poly_surface`](https://furuse.work/ops/3d/surface_fit/fit_poly_surface.html) · [`surface_form_error`](https://furuse.work/ops/3d/surface_fit/surface_form_error.html)

## 20. 実写のテクスチャを回す ―― 「回転不変」は、それが要らない素材でだけ成り立つ

[![実写のテクスチャを回す ―― 「回転不変」は、それが要らない素材でだけ成り立つ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_texture_invariance/01_textures_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_texture_invariance/01_textures.png)

*↑ **実写のテクスチャを回す ―― 「回転不変」は、それが要らない素材でだけ成り立つ** ―― 実写のテクスチャ 3 枚(brick / grass / gravel、CC0)を既知の角度で回し、記述子が自分自身からどれだけ離れるかを測る。★測る前に基準を置く ―― 素材どうしの距離のうち最小(草と砂利の 0.01250)がこの課題の分解能で、回転で動く量がこれを超えたら**回した自分より別の素材のほうが近い**。★★異方な brick は 5 度で 0.0433、60 度で 0.1205 = 分解能の **9.6 倍**。等方な grass / gravel は 0.0005〜0.0024(0.17 / 0.19 倍)で実質不変。★対照群 2 つで犯人を絞る: 補間だけ(+7/-7 度の往復)は brick 0.03685、そして**補間ゼロの厳密 90 度(np.rot90)でも 0.08501 = 6.8 倍** ―― 補間のせいではない。★異方性は独立に測れて順位を説明する: 勾配方向の大域的な偏り R は brick 0.309 対 grass 0.027 / gravel 0.029 で、10 倍違うのは brick だけ。★★「回転不変」な符号化に替えると 9.64 → ror 5.49 → uniform **1.72** まで下がるが、**1 を割らない**(等方な 2 つは 0.17 → 0.02 と 10 倍良くなるのに)。LBP の回転不変性は局所パターンの巡回に対するもので、素材そのものの向きの分布は消せないため。nri_uniform が 4.24 なので「uniform だから良い」のではなく「回転不変だから良い」ことも確かめられる。★この PoC を書くまで sk_lbp の b は未使用で method は 'default' 固定だった(hough_circle_trans と同じ形)―― 選べなければ下げようがないので割り当てた(b=0.5 は従来と同一)。*

[![brick だけが 1 を大きく超える(最大 9.6 倍)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_texture_invariance/02_drift_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_texture_invariance/02_drift.png)

*↑ 測定の図 ―― brick だけが 1 を大きく超える(最大 9.6 倍)。*

```
py -3.11 examples/poc_real_texture_invariance.py
```

ソース: [examples/poc_real_texture_invariance.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_texture_invariance.py)

使用 op(ノートへ): [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`sk_lbp`](https://furuse.work/ops/2d/texture/sk_lbp.html)

## 21. 搬送ロールの傷を周期から名指しする ―― 崖に着く前に、何も言えなくなる

[![搬送ロールの傷を周期から名指しする ―― 崖に着く前に、何も言えなくなる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_web_roll_periodicity/01_scene_web_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_web_roll_periodicity/01_scene_web.png)

*↑ **搬送ロールの傷を周期から名指しする ―― 崖に着く前に、何も言えなくなる** ―― フィルム・電池電極・銅箔・紙のロール to ロールでは、搬送ロールの傷 1 か所がその周長ごとに web へ転写される。欠陥地図の流れ方向スペクトルから周長を測り、πD の台帳と突き合わせて犯人を名指しできるか。★★素朴に「スペクトルの最大値」を読むと、**実在する無実のロールを名指しする** —— インパルス列の櫛では高調波が基本波と同じ高さなので最大値は C/2 = 235.62 mm を掴み、それが台帳の冷却ロール(314.16 mm)に落ちる。無い周長を答えるなら気づけるが、台帳の中の別の 1 本を指すので報告がそのまま通る。★同じ誤差は見逃し率 0 → 50 % を通して 235.9 mm のまま動かない —— **誤差が一定なのは頑健さの証拠ではない**(同じ間違いを続けているだけ)。対策は k=1..3 の高調波が全部立つ最低周波数を採る fail-closed の櫛法。★ゼロ点(欠陥の MD 間隔)は検出が完璧なら当たる(中央値の誤差 -0.03 mm)。見逃し 40 % で中央値 472.1 mm・平均 813.5 mm に対し櫛法は 3.2 mm —— **見逃しは位相を飛ばさない**(抜けた山は振幅を減らすだけ)。平均は clutter に、中央値は見逃しに弱く、どちらの弱点も櫛法には無い。★対照群(蛇行 25 mm)を補正しないと1 本のロールの欠陥列が CD で 2 本に割れる(レーンに残る周期欠陥 100 → 44 %)が、MD スペクトルはビット単位で無傷 —— 蛇行が壊すのは「CD でレーンを切ってから数える」手法だけ。★健全ロールだけ 60 試行で偽陽性 1.7 %。床は 0 でなく、健全側でも帯域内の最大値/中央値が 3.99 倍まで来て**単独のしきい値 2.5 倍を超える** —— 止めているのは高調波の全数要求のほう。★★崖は 2 つある: 予測 L_crit = C²/ΔC = 14137 mm に対し実測の**分解の崖 14000 mm**(比 0.99)。ところが報告率 100 % を保つ**検出の崖は 17000 mm と長い** —— 記録を短くすると「隣と取り違える」より先に「何も言えなくなる」ので、Rayleigh が正しく当てたその崖には辿り着けない。★判定そのものを直した: 24 試行では「隣へ落ちる 0 %」が成立したが、120 試行では最長 20000 mm でも 2 % 残り、**0 % は床ではなく小標本の産物**だった(床の 3 倍で数え直して 14000 mm)。同じ理由で「特定成功率 100 %」も97 / 98 % に直した。★取り違え先は掃引 9 点中 7 点で冷却ロール、471.24 / 314.16 = 1.500 の 3:2 —— 台帳に整数比があると、櫛法にも固有の取り違えがある。★この PoC が炙り出した道具の穴 2 件を、その場で埋めた: 点列から直接スペクトルを取る `fs.point_spectrum`(ビン幅を選ばない点過程の周期図。分解能 1/記録長 を返り値に持つ)と、1-D の山をサブビンで読む `fs.peak_subbin`(頂点を丸めずに返す —— ±0.5 を超えたら「そこは極大でない」という情報)。PoC 本体もその op を通るようにしたが、櫛の高調波を掴むという中心の所見は変わらない(道具ではなく読み方の問題)。*

[![見逃しは位相を飛ばさないので、櫛の山は低くなるだけで動かない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_web_roll_periodicity/02_null_vs_spectrum_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_web_roll_periodicity/02_null_vs_spectrum.png)

*↑ 測定の図 ―― 見逃しは位相を飛ばさないので、櫛の山は低くなるだけで動かない。*

```
py -3.11 examples/poc_web_roll_periodicity.py
```

ソース: [examples/poc_web_roll_periodicity.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_web_roll_periodicity.py)

使用 op(ノートへ): [`cepstrum`](https://furuse.work/ops/acoustics/bearing/cepstrum.html) · [`find_peaks`](https://furuse.work/ops/oned/signal/find_peaks.html) · [`local_min_max_funct_1d`](https://furuse.work/ops/oned/function/local_min_max_funct_1d.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`peak_subbin`](https://furuse.work/ops/oned/signal/peak_subbin.html) · [`point_spectrum`](https://furuse.work/ops/oned/signal/point_spectrum.html) · [`smooth_funct_1d_gauss`](https://furuse.work/ops/oned/function/smooth_funct_1d_gauss.html) · [`spectrum`](https://furuse.work/ops/oned/signal/spectrum.html)

## 22. 印刷の版ずれを刷り上がりから測る ―― 網点は格子なので、答えは 1 つに決まらない

[![印刷の版ずれを刷り上がりから測る ―― 網点は格子なので、答えは 1 つに決まらない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_registration/04_sweep_wrap_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_registration/04_sweep_wrap.png)

*↑ **印刷の版ずれを刷り上がりから測る ―― 網点は格子なので、答えは 1 つに決まらない** ―― オフセット・ラベル印刷の**版ずれ**を刷り上がりから測る。CMYK 4 版に慣行のスクリーン角(C 15°/M 75°/Y 0°/K 45°、133 lpi、1200 dpi でピッチ 9.02 px)と既知のずれを仕込んだ図。★★**網点は格子なので、相関で出るのは版ずれ d ではなく d mod Λ_θ** —— 軸方向で |d| ≤ p/2 = 4.51 px、対角で p/√2 = 6.38 px を超えると折り返す。これは測る前に閉形式で書けて、4 版 × 37 点 = 148 点のうち**144 点で予測と実測の差が 0.1096 px 以内**。残り 4 点は基本セルの境界のタイ(セル余裕 ≤ 0.165 px)で、格子で簡約した残差なら全点が合う —— **推定器は間違えておらず、格子で等価な答えのどれかを返している**(独立な 2 つの推定器が同じ折り返しをする)。★★効き方が具体的に効く: 真値 9.64 px は公差 2.0 px の 4.8 倍なのに、スクリーン角の違いだけで版ごとに 1.09〜3.32 px に見え、**4 版中 2 版が「合格」に見える** —— 同じ紙が同じだけずれた結果。★ゼロ点(インク重心)は折り返さない代わりに**縮尺が狂う**。傾きは閉形式 k = 1-β(β = 下地だけのインク量 ÷ 実際のインク量)で予測 0.3983 に対し実測 0.3711(差 0.0272)。★予測していなかったものが出た: 直線からの外れ 0.9864 px は網点ピッチ周期のさざ波で、**窓の縁で網点の列が出入りする**ため —— テーパ窓の対照群で 0.0048 px に落ちて原因が確定した。★対照群 (a): FM(確率)スクリーンに替えるだけで誤差は全域で最大 0.0029 px、折り返しゼロ。**崖の原因は推定器ではなく AM 網点の周期性**(代償はコントラスト 0.91 倍)。★対照群 (b): レジストマークを含む窓は当たる(0.0823 px)が、紙の伸び 0.600 %・版の傾き 0.120° があると誤差は距離に比例し(0.006319 px/px)、公差を超えるのは**予測 316.5 px / 実測 322.5 px** から —— 紙の 44 % が公差外。★★物差しを 2 つ置くと勝者が入れ替わる: 精度 1 位は素の相関 0.0071 px なのに判定一致率は 67.6 % で最下位、低域通過は判定 89.2 % でも精度が 94 倍悪い。**鈍い方で代表元を選び、鋭い方で詰める二段**なら両方勝つ(0.0071 px / 94.6 %)。成立条件「粗の誤差 < 基本セルの半径 4.511 px」も実測で確かめ、**二段が壊れた 2 点はすべて粗の誤差がその半径を超えた点**だった。絵柄をベタに寄せると 6 点中 3 点で丸ごと 1 格子跳ぶ。★合成器そのものが罠だった: 1200 dpi / 150 lpi(ピッチがちょうど 8.00 px)だと**全網点の標本位相が揃う**ので0.5 px ずらすたびに重心が 1.4 px 跳ねる。133 lpi にして解消した —— **整数比を避けるのが本質**で、スーパーサンプリングでは直らない。★★用途外の op を当てたら自信満々で外した: `fs.frame_align` は `inlier_ratio` **1.00** / `rms_px` 0.645 を返しながら真値 (0.00, +1.30) に対して **80.85 px** 外す(しかもその答えは網点格子のベクトルですらない = 折り返しとは別種の失敗)。**この PoC の指摘で op 側を直した** —— docstring に「繰り返し構造には使えない」を測った数字つきで書き、投票の**2 番手の山 / 1 番手**を `vote_margin` として返すようにした。賛成率はどちらの場合も 1.00 だが、`vote_margin` は網点 **1.000** / 星野 **0.143** で区別できる。*

[![スクリーン角が違うので格子の向きが違う。ピッチはどれも 9.02 px。同じ物理的なずれでも、この格子の違いが「見かけのずれ」を版ごとに変える(5 節)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_registration/01_plates_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_registration/01_plates.png)

*↑ 測定の図 ―― スクリーン角が違うので格子の向きが違う。ピッチはどれも 9.02 px。同じ物理的なずれでも、この格子の違いが「見かけのずれ」を版ごとに変える(5 節)*

```
py -3.11 examples/poc_print_registration.py
```

ソース: [examples/poc_print_registration.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_print_registration.py)

使用 op(ノートへ): [`frame_align`](https://furuse.work/ops/astrostack/align/frame_align.html) · [`inlier_ratio`](https://furuse.work/ops/3d/registration_metrics/inlier_ratio.html) · [`peak_subbin`](https://furuse.work/ops/oned/signal/peak_subbin.html) · [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html)

## 23. 熱画像は温度画像ではない ―― 放射率・反射・透過を取り違えたまま「温度」と呼ぶ

[![熱画像は温度画像ではない ―― 放射率・反射・透過を取り違えたまま「温度」と呼ぶ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/15_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/15_scene.png)

*↑ **熱画像は温度画像ではない ―― 放射率・反射・透過を取り違えたまま「温度」と呼ぶ** ―― 熱カメラの DN を温度に戻す**全経路**を、真値を自分で植てて測る。前向きモデルは `L = τ[ε L_bb(T_obj) + (1-ε) L_bb(T_refl)] + (1-τ) L_bb(T_atm)`。★**床を先に測る**: 往復 1.75e-06 K、量子化 6.28e-03 K、+NETD 2.71e-02 K。**350.0 K では厳密に 0 が出たが、それは校正表の節点にたまたま乗っただけ**なので、節点を外して測り直した —— **0 を床と呼ぶのは嘘**になる。★★**閉形式の予測を印字して、外した**: 素朴な `n = c2/(λ_eff T)` は数値微分から最大 **16.6 %** ずれる。外れの正体は実効波長の選び方ではなく **`e^x/(e^x-1)` の欠け**(x = c2/λT)で、入れると誤差 **0.00 %**。MWIR 300 K は x=10.9 でほぼ Wien、LWIR 800 K は x=1.80 で Rayleigh–Jeans 寄り。★★**崖の向きも外した**: 「低温ほど急」と印字したが、**絶対誤差は高温ほど大きい**(Δε/ε=5 % で 305 K の 0.233 K → 800 K の **16.907 K**)。log-log の傾きは実測 **2.717**、内訳は T/n = 1.741 + 反射因子 0.977 = 2.718 —— **閉形式は最初からそう言っていて、自分の式を読み違えていた**。★★**「低温ほど急」は正しかったが、犯人が違った**: 周囲からの上昇 (T_obj - T_refl) で割ると、放射率の誤差は 4.7 % → 3.4 % と **1.40 倍しか動かず発散しない**(Δε/ε に収束する)。発散するのは **T_refl の取り違え**のほうで 13.2 % → 0.0 %(**972 倍**)。上昇 10 K を切ると、反射が放射率より重くなる。★★**不確かさは足し算にならない**。ε=0.60±0.05・T_refl=300±5 K・相関 ρ=+0.7 という現実的な組を 20000 試行で数えると、**「95 % 区間」が実際に真値を包む割合は 独立 RSS で 88.03 %、相関つき Monte Carlo で 94.44 %**(-6.4 点)。★**床を先に測ってある**: ρ=0 なら RSS 95.03 % / MC 94.52 % なので、この落差は実装ではなく**相関を無視したことそのもの**。真の u 5.6518 K に対し RSS は 4.5086 K = **区間が 20.2 % 狭い**。取りこぼしは片側に寄る(下 7.14 % / 上 4.83 %)。ρ=-0.7 なら逆に 99.64 % と**過剰**になる —— **独立と仮定することは、安全側でも危険側でもなく『分からない側』**。★★**guard band(合否判定)**: 40000 試行(真値 65〜95 ℃ 一様)で、**誤合格 8.03 %(不確かさ無視)→ 0.81 %(RSS)→ 0.14 %(相関つき MC)**。**RSS は MC の 5.6 倍 誤合格する**。誤不合格は 6.69 → 28.22 → 40.03 % で、MC の band が広いのは相関だけでなく**分布の歪み**の分もある(対称 1.96u なら 11.08 K、上側 97.5 百分位は 13.47 K)。★**単位の崖**は 8 通りで例外 3 / 静かに 5。★**同じ「T_refl を摂氏で書く」取り違えが、ε=0.95 では静かに通り(-22.1 K)、ε=0.10 では例外になる** —— **止まるかどうかは間違いの種類ではなく場面で決まる**。静かな側は DN 平均→温度(+1.543 K、Jensen)、見かけ温度(-2.121 K)、τ 二重掛け(+2.485 K)、ΔT/T をセ氏(感度を 1/4.46 に過小評価)。★**熱画像そのもの**: 同じ 375.0 K のボルト(ε=0.10)が、ε=1 の絵では周りの塗装面より **62.3 K 低く**写る(309.7 K 対 372.0 K)—— 発熱部の真上が**いちばん健全に見える**。ε 地図で 375.0 K に復帰(残差 rms 0.106 K)するが、★**補正は偏りを消す代わりに雑音を増やす**: 残差 rms は塗装面 0.0571 K に対しボルト **0.3673 K(6.4 倍)**。ε の比 9.5 より小さいのは、ボルトの DN が低くて光子雑音も小さいから —— **2 つの効き方が逆向き**。★★**道具の穴を見つけて、その場で直した**: `fs.noise_sigma(method='mad')` は整数値の画像で **σ=0.5 相当のとき 0.0000** を返し、返せる値は 1.4826 の倍数だけ(σ=1.0 も σ=1.983 も同じ 1.4826)。14 bit の生 DN はまさに整数。**下流はもっと悪く、200x200 の整数フレームに植えた点目標 2 個を `star_detect` が 0 個**と返していた。`star_detect` には `σ≤0` の門が**在った**のに、コメントが「完全に平坦 = 雑音が測れない」と書いていて**前提のほうが誤り**だった。しかも `clip` 法の存在はコード内コメントに書かれていた —— **知識は在ったが、読む側(docstring と既定値)に無かった**。いまは `noise_sigma` が警告、`star_detect` は**平坦なら空・平坦でなければ拒否**。`clip` に替えれば植えた 2 個がちゃんと出る。*

[![LWIR・350 K・ε=0.95。校正表と直接積分の相対差は最大 8.9e-16。以下の誤差はすべてこの床の上。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/01_floor_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_thermal_radiometry/01_floor.png)

*↑ 測定の図 ―― LWIR・350 K・ε=0.95。校正表と直接積分の相対差は最大 8.9e-16。以下の誤差はすべてこの床の上。*

```
py -3.11 examples/poc_thermal_radiometry.py
```

ソース: [examples/poc_thermal_radiometry.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_thermal_radiometry.py)

使用 op(ノートへ): [`beer_lambert_transmittance`](https://furuse.work/ops/optics/glassbody/beer_lambert_transmittance.html) · [`interp_linear`](https://furuse.work/ops/math/interp_poly/interp_linear.html) · [`mat_eigh`](https://furuse.work/ops/math/linalg/mat_eigh.html) · [`noise_sigma`](https://furuse.work/ops/astrostack/quality/noise_sigma.html) · [`photon_uncertainty`](https://furuse.work/ops/photon/counting/photon_uncertainty.html) · [`poly_fit`](https://furuse.work/ops/math/interp_poly/poly_fit.html) · [`stat_correlation`](https://furuse.work/ops/math/stats/stat_correlation.html) · [`stat_covariance`](https://furuse.work/ops/math/stats/stat_covariance.html) · [`stat_describe`](https://furuse.work/ops/math/stats/stat_describe.html) · [`stat_histogram`](https://furuse.work/ops/math/stats/stat_histogram.html)

### 寸法・形状計測ウィング ―― 偏りと散らばりは別々に持つ

「この部品の幅は 50.50 画素だ」と言い切るには、偏り(いつも同じ向きにずれる分)と散らばり(撮るたびに変わる分)を別々に出す必要があります。合否は偏りで決まり、繰り返し精度は散らばりで決まる。1 つの「誤差」にまとめた瞬間、どちらの対策を打つべきかが分からなくなります。

この部屋の 10 点は、符号つき距離関数の部品、インボリュート歯形、指定 PSD の粗さ面、白色干渉のスタック、解析スペックル、Frocht の応力場、対称な合成頭蓋と、いずれも閉形式か解析描画で真値を握った上で、キャリパーや相関や位相の読みを採点しています。

共通して出てきたのは「定義を書かない数字は比較できない」ということです。距離変換の 2 通りの規約で 0.20 mm 違うひび割れ幅、個数基準と面積基準で 1.66 倍違う D50、評価領域を広げると頭打ちにならない Sz、本数基準か長さ基準かで 5 % 動く配向度。測定器の誤差ではなく、比べる相手の問題として現れます。

## 24. 産業部品の寸法検査 ―― 偏りと散らばりを別々に出す

[![産業部品の寸法検査 ―― 偏りと散らばりを別々に出す](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dimensional_inspection/01_slot_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dimensional_inspection/01_slot_bias.png)

*↑ **産業部品の寸法検査 ―― 偏りと散らばりを別々に出す** ―― 符号つき距離関数で描いた部品(スロット幅 50.50 px、1 px = 12.5 µm)を既知の PSF と雑音で撮り、4 系のキャリパーで測った図。大津の整数幅(ゼロ点)は RMS 0.464 px = 5.8 µm、埋もれていた 1-D 計測実装の偏りは -0.0113 px = -0.14 µm で 41 倍。エッジ間距離が PSF 幅の 3.09 倍を切ると幅は系統的に大きく出るのに、API は成功を返し続ける。*

[![偏りはどちらも正(対が互いを押し広げる)。符号が一定なので繰り返し測っても消えない。下端 -4 は表示の打ち切り(|偏り| < 1e-4 px)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dimensional_inspection/02_blur_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dimensional_inspection/02_blur_cliff.png)

*↑ 測定の図 ―― 偏りはどちらも正(対が互いを押し広げる)。符号が一定なので繰り返し測っても消えない。下端 -4 は表示の打ち切り(|偏り| < 1e-4 px)。*

```
py -3.11 examples/poc_dimensional_inspection.py
```

ソース: [examples/poc_dimensional_inspection.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dimensional_inspection.py)

使用 op(ノートへ): [`add_metrology_object_circle_measure`](https://furuse.work/ops/measure1d/model/add_metrology_object_circle_measure.html) · [`add_metrology_object_ellipse_measure`](https://furuse.work/ops/measure1d/model/add_metrology_object_ellipse_measure.html) · [`add_metrology_object_generic`](https://furuse.work/ops/measure1d/model/add_metrology_object_generic.html) · [`add_metrology_object_line_measure`](https://furuse.work/ops/measure1d/model/add_metrology_object_line_measure.html) · [`add_metrology_object_rectangle2_measure`](https://furuse.work/ops/measure1d/model/add_metrology_object_rectangle2_measure.html) · [`align_metrology_model`](https://furuse.work/ops/measure1d/apply/align_metrology_model.html) · [`apply_metrology_model`](https://furuse.work/ops/measure1d/apply/apply_metrology_model.html) · [`create_metrology_model`](https://furuse.work/ops/measure1d/model/create_metrology_model.html) · [`edge_points`](https://furuse.work/ops/3d/edges/edge_points.html) · [`ellipse`](https://furuse.work/ops/annotate/shape/ellipse.html) · [`fuzzy_measure_pairing`](https://furuse.work/ops/measure1d/caliper/fuzzy_measure_pairing.html) · [`gen_measure_arc`](https://furuse.work/ops/measure1d/caliper/gen_measure_arc.html) · [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`m1_measure_pairs`](https://furuse.work/ops/2d/measure1d/m1_measure_pairs.html) · [`m1_measure_pos`](https://furuse.work/ops/2d/measure1d/m1_measure_pos.html) · [`measure_pairs`](https://furuse.work/ops/measure1d/caliper/measure_pairs.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`translate_measure`](https://furuse.work/ops/measure1d/caliper/translate_measure.html)

## 25. 歯車の歯形を測る ―― 偏心は 1 次、歯は z 次

[![歯車の歯形を測る ―― 偏心は 1 次、歯は z 次](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/01_scene.png)

*↑ **歯車の歯形を測る ―― 偏心は 1 次、歯は z 次** ―― インボリュートの閉形式で描いた歯車から偏心と歯形を読む図。ゼロ点の最小二乗円は直径 47.278 mm で、ピッチ円 48 / 歯先円 52 / 歯底円 43 のどれでもない。歯が 1 枚欠けると偏心 0.050 mm が 0.1285 mm(+157 %)に化けるが、歯ごとに 1 標本だけ読む伝統的な測り方なら 0.0501 mm(+0.2 %)。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/02_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_gear_tooth_metrology/02_profile.png)

*↑ 測定の図*

```
py -3.11 examples/poc_gear_tooth_metrology.py
```

ソース: [examples/poc_gear_tooth_metrology.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_gear_tooth_metrology.py)

使用 op(ノートへ): [`blob_boundaries`](https://furuse.work/ops/blob/extract/blob_boundaries.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`blob_region`](https://furuse.work/ops/blob/extract/blob_region.html) · [`blob_select_largest`](https://furuse.work/ops/blob/select/blob_select_largest.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`polar_trans_image`](https://furuse.work/ops/2d/geometry/polar_trans_image.html) · [`spectrum`](https://furuse.work/ops/oned/signal/spectrum.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html)

## 26. 表面粗さ Sa / Sq / Sz は標本化とカットオフにどこまで耐えるか

[![表面粗さ Sa / Sq / Sz は標本化とカットオフにどこまで耐えるか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_surface_roughness/01_surface_components_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_surface_roughness/01_surface_components.png)

*↑ **表面粗さ Sa / Sq / Sz は標本化とカットオフにどこまで耐えるか** ―― 指定 PSD から合成した表面(Sq の真値は Parseval で解析的)に傾き・うねり・加工目・傷を足し、粗さパラメータを測った図。生の rms を Sq と呼ぶと 20 倍の過大、平面だけ除いても 1.8 倍。標本間隔 8 µm で Sa は -3.5 %(合格)、Sz は -19.8 %(不合格) ―― Sz は評価領域を広げると頭打ちにならず、「真の Sz」は存在しない。*

[![dx=8 µm では Sa が ±5 % 合格で Sz が不合格。同じデータでも見るパラメータで結論が反転する。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_surface_roughness/02_sampling_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_surface_roughness/02_sampling_cliff.png)

*↑ 測定の図 ―― dx=8 µm では Sa が ±5 % 合格で Sz が不合格。同じデータでも見るパラメータで結論が反転する。*

```
py -3.11 examples/poc_surface_roughness.py
```

ソース: [examples/poc_surface_roughness.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_surface_roughness.py)

使用 op(ノートへ): [`profile_params`](https://furuse.work/ops/roughness/measure/profile_params.html) · [`surface_filter`](https://furuse.work/ops/roughness/prepare/surface_filter.html) · [`surface_form_remove`](https://furuse.work/ops/roughness/prepare/surface_form_remove.html) · [`surface_params`](https://furuse.work/ops/roughness/measure/surface_params.html) · [`surface_psd`](https://furuse.work/ops/roughness/measure/surface_psd.html) · [`surface_synth_psd`](https://furuse.work/ops/roughness/synth/surface_synth_psd.html)

## 27. 白色干渉計でナノメートルの段差をどこまで正確に測れるか

[![白色干渉計でナノメートルの段差をどこまで正確に測れるか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/01_interferogram_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/01_interferogram.png)

*↑ **白色干渉計でナノメートルの段差をどこまで正確に測れるか** ―― 白色干渉計の走査スタックを合成し、50〜500 nm の段差を測り返した図。雑音 1 % で偏り 2.4 nm 以内・標準偏差 14.1 nm 以内、しかも段差の大きさにほぼ依らない。ゼロ点(包絡線の最大サンプル)の誤差は走査ステップの半分に厳密一致し、Nyquist 上限 0.15 µm の手前 0.14 µm では雑音なしでも +14.1 nm。*

[![0.02〜0.12 µm は 0.05 nm 以内で平ら。Nyquist 上限 0.15 µm の手前 0.14 µm で崖。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/02_zstep_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_interferometry_step/02_zstep_sweep.png)

*↑ 測定の図 ―― 0.02〜0.12 µm は 0.05 nm 以内で平ら。Nyquist 上限 0.15 µm の手前 0.14 µm で崖。*

```
py -3.11 examples/poc_interferometry_step.py
```

ソース: [examples/poc_interferometry_step.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_interferometry_step.py)

使用 op(ノートへ): [`csi_design`](https://furuse.work/ops/interferometry/design/csi_design.html) · [`csi_height_map`](https://furuse.work/ops/interferometry/surface/csi_height_map.html) · [`csi_stack_simulate`](https://furuse.work/ops/interferometry/simulate/csi_stack_simulate.html) · [`decode_fringe`](https://furuse.work/ops/3d/structured_light/decode_fringe.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`synthesize_fringes`](https://furuse.work/ops/3d/structured_light/synthesize_fringes.html)

## 28. スペックル画像からひずみを測る(DIC)

[![スペックル画像からひずみを測る(DIC)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dic_strain/04_strain_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dic_strain/04_strain_map.png)

*↑ **スペックル画像からひずみを測る(DIC)** ―― 3000 個のガウス斑点を変形写像で移してから描き直したスペックル対から変位とひずみを読む図。真の変位 0.37 px に対し窓相関(piv)の偏り 0.0002 px・散らばり 0.0022 px で、ゼロ点(動かないと答える)の 167 倍。剛体回転が微小ひずみの定義で数百 µε の嘘を作る ―― Green-Lagrange なら厳密に 0。*

[![変形は補間ではなく斑点の再描画。だから真値が厳密。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dic_strain/01_speckle_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dic_strain/01_speckle.png)

*↑ 測定の図 ―― 変形は補間ではなく斑点の再描画。だから真値が厳密。*

```
py -3.11 examples/poc_dic_strain.py
```

ソース: [examples/poc_dic_strain.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dic_strain.py)

使用 op(ノートへ): [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`strain_from_displacement`](https://furuse.work/ops/piv/solid/strain_from_displacement.html)

## 29. クリープ試験のひずみ履歴 ―― 累積か直接か

[![クリープ試験のひずみ履歴 ―― 累積か直接か](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/01_speckle_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/01_speckle.png)

*↑ **クリープ試験のひずみ履歴 ―― 累積か直接か** ―― 1 時間のクリープを 25 コマ撮り、隣接コマの累積と基準フレームとの直接比較でひずみ履歴を出した図。終端で累積 61 µε / 直接 1878 µε と累積が 31 倍良く、教科書の「時刻で入れ替わる」交点は無い(入れ替わるのは雑音の軸)。コマを 24 → 4 歩に間引くと累積は -60 → -606 µε と悪化 ―― 効くのは歩数でなく 1 歩あたりの変形量。*

[![直接の偏りだけが伸びる。累積は偏りも散らばりも頭打ちで、しかも散らばりより偏りのほうが大きい ——ランダムウォークではない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/02_errors_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_strain_history/02_errors.png)

*↑ 測定の図 ―― 直接の偏りだけが伸びる。累積は偏りも散らばりも頭打ちで、しかも散らばりより偏りのほうが大きい ——ランダムウォークではない。*

```
py -3.11 examples/poc_strain_history.py
```

ソース: [examples/poc_strain_history.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_strain_history.py)

使用 op(ノートへ): [`moving_average_window`](https://furuse.work/ops/videostream/window/moving_average_window.html) · [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`piv_error_stats`](https://furuse.work/ops/piv/assess/piv_error_stats.html) · [`piv_multipass`](https://furuse.work/ops/piv/estimate/piv_multipass.html) · [`piv_sample_at_windows`](https://furuse.work/ops/piv/assess/piv_sample_at_windows.html) · [`piv_synth_pair`](https://furuse.work/ops/piv/synth/piv_synth_pair.html) · [`poly_fit`](https://furuse.work/ops/math/interp_poly/poly_fit.html)

## 30. 光弾性で応力を測る ―― 巻き戻しが最初に失敗するのは等方点

[![光弾性で応力を測る ―― 巻き戻しが最初に失敗するのは等方点](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_photoelasticity/01_polariscope_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_photoelasticity/01_polariscope.png)

*↑ **光弾性で応力を測る ―― 巻き戻しが最初に失敗するのは等方点** ―― 円板圧縮の閉形式応力場(中心 4.2441 MPa、縞次数 2.380)を Mueller 行列の op で偏光像にし、縞から応力へ戻す図。op の偏光系は教科書式と 125 通りで最大差 2.2e-16。縞次数が 0.5 を超える 84.2 % の画素で位相が巻き、巻き戻しが最初に壊れるのは応力の大きい所ではなく、変調が落ちる等方点。*

[![左下 2 枚が「壊れる予報」。どちらもマスクで外せる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_photoelasticity/02_unwrap_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_photoelasticity/02_unwrap.png)

*↑ 測定の図 ―― 左下 2 枚が「壊れる予報」。どちらもマスクで外せる。*

```
py -3.11 examples/poc_photoelasticity.py
```

ソース: [examples/poc_photoelasticity.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_photoelasticity.py)

使用 op(ノートへ): [`mueller_apply`](https://furuse.work/ops/optics/polarization/mueller_apply.html) · [`mueller_element`](https://furuse.work/ops/optics/polarization/mueller_element.html) · [`unwrap_phase_2d`](https://furuse.work/ops/3d/structured_light/unwrap_phase_2d.html)

## 31. 左右非対称性を測る ―― 対称面は変形に引きずられる

[![左右非対称性を測る ―― 対称面は変形に引きずられる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bilateral_asymmetry/03_deviation_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bilateral_asymmetry/03_deviation_map.png)

*↑ **左右非対称性を測る ―― 対称面は変形に引きずられる** ―― 厳密に左右対称な合成頭蓋の片側に既知の膨らみを入れ、鏡映して重ねた図。完全対称な標本でも床は 0 にならず、点対点 1.33 mm → 点対面 0.030 mm → 近傍平滑 0.012 mm。残差を最小にする面は 6.33 mm の膨らみで 2.92 mm / 1.72 度引きずられ、非対称量の 46 % が消える。*

[![完全対称な標本を測った残差。点対点は点間隔がそのまま床になる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bilateral_asymmetry/01_floor_vs_spacing_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bilateral_asymmetry/01_floor_vs_spacing.png)

*↑ 測定の図 ―― 完全対称な標本を測った残差。点対点は点間隔がそのまま床になる。*

```
py -3.11 examples/poc_bilateral_asymmetry.py
```

ソース: [examples/poc_bilateral_asymmetry.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bilateral_asymmetry.py)

使用 op(ノートへ): [`chamfer_distance`](https://furuse.work/ops/3d/metrics/chamfer_distance.html) · [`detect_reflection_symmetry`](https://furuse.work/ops/3d/symmetry/detect_reflection_symmetry.html) · [`detect_rotational_symmetry`](https://furuse.work/ops/3d/symmetry/detect_rotational_symmetry.html) · [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`hausdorff_distance`](https://furuse.work/ops/3d/metrics/hausdorff_distance.html) · [`reflect_points`](https://furuse.work/ops/3d/symmetry/reflect_points.html) · [`reflection_symmetry_score`](https://furuse.work/ops/3d/symmetry/reflection_symmetry_score.html) · [`sample_surface`](https://furuse.work/ops/3d/superquadric/sample_surface.html) · [`vertex_normals`](https://furuse.work/ops/3d/mesh_process/vertex_normals.html)

## 32. 粒度分布を画像から測る ―― 融合と縁切れが逆向きに効き、途中で打ち消し合う

[![粒度分布を画像から測る ―― 融合と縁切れが逆向きに効き、途中で打ち消し合う](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/01_scene.png)

*↑ **粒度分布を画像から測る ―― 融合と縁切れが逆向きに効き、途中で打ち消し合う** ―― 粒子を撒いた合成画像から D10 / D50 / D90 を出し、融合(大きい側へ)と縁切れ(小さい側へ)を別々に数えた図。面積率 13.8 % で D50 誤差 +0.55 % ―― 融合 28 件と縁切れ 19 件が釣り合っているだけ。個数基準と面積基準では同じ塊から D50 が 26.9 µm と 44.7 µm(1.66 倍)。*

[![薄いところで 0 なのは正確だから。濃いところで 0 をまたぐのは融合と縁切れが釣り合っただけ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/02_density_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_sizing/02_density_sweep.png)

*↑ 測定の図 ―― 薄いところで 0 なのは正確だから。濃いところで 0 をまたぐのは融合と縁切れが釣り合っただけ。*

```
py -3.11 examples/poc_particle_sizing.py
```

ソース: [examples/poc_particle_sizing.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_particle_sizing.py)

使用 op(ノートへ): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`blob_region`](https://furuse.work/ops/blob/extract/blob_region.html) · [`blob_select`](https://furuse.work/ops/blob/select/blob_select.html) · [`circularity`](https://furuse.work/ops/2d/features/circularity.html) · [`distance_transform`](https://furuse.work/ops/2d/region/distance_transform.html)

## 33. 繊維の配向分布を測る ―― 角度は 180 度周期、素朴に平均すると 90 度ずれる

[![繊維の配向分布を測る ―― 角度は 180 度周期、素朴に平均すると 90 度ずれる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/01_scene.png)

*↑ **繊維の配向分布を測る ―― 角度は 180 度周期、素朴に平均すると 90 度ずれる** ―― フォン・ミーゼス分布から撒いた繊維 140 本の配向を構造テンソルで読む図。真の平均 177.9 度を算術平均は 105.55 度と報告し(-72.33 度)、2 倍角の円形平均なら +0.17 度 ―― 画像も測定も 1 ビットも変えていない。全画素を等しく数えると配向度が -31.3 % 落ちる。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/02_wrap_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_fiber_orientation/02_wrap.png)

*↑ 測定の図*

```
py -3.11 examples/poc_fiber_orientation.py
```

ソース: [examples/poc_fiber_orientation.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_fiber_orientation.py)

使用 op(ノートへ): [`coherence`](https://furuse.work/ops/acoustics/dual/coherence.html) · [`dc_structure_texture`](https://furuse.work/ops/2d/decomposition/dc_structure_texture.html) · [`moment_axes`](https://furuse.work/ops/3d/match_pose/moment_axes.html) · [`principal_moments`](https://furuse.work/ops/3d/moment_invariant/principal_moments.html) · [`smooth_funct_1d_gauss`](https://furuse.work/ops/oned/function/smooth_funct_1d_gauss.html) · [`sobel_amp`](https://furuse.work/ops/2d/edges/sobel_amp.html) · [`sobel_dir`](https://furuse.work/ops/2d/edges/sobel_dir.html)

## 34. 金属組織の結晶粒度 ―― 面積法と切片法は別の崖で落ちる

[![金属組織の結晶粒度 ―― 面積法と切片法は別の崖で落ちる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/01_scene.png)

*↑ **金属組織の結晶粒度 ―― 面積法と切片法は別の崖で落ちる** ―― 2-D Voronoi で粒を仕込み、粒界を幅 2 px で描いてエッチングむら・雑音・途切れを乗せ、ASTM E112 の面積法(大津 + 連結成分)と直線切断法(局所しきい値 + 4 方向の試験線)で G を測った図。面積法は雑音だけ -0.02・むらだけ -0.40 が両方で +3.82 と相互作用で死に、粒界の途切れでは 7.2 % で 1 段落ちる。切片法は 40.7 % まで持つが、予想の 29.3 % は外れ(マスク上で消える粒界は f の 0.76 倍)。混粒の全体 G 7.82 は細粒 9.01 にも粗粒 6.15 にも無く、64 タイル中 4 つしか ±0.5 に入らない。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/02_controls_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_metal_grain_size/02_controls.png)

*↑ 測定の図*

```
py -3.11 examples/poc_metal_grain_size.py
```

ソース: [examples/poc_metal_grain_size.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_metal_grain_size.py)

使用 op(ノートへ): [`bin_threshold`](https://furuse.work/ops/2d/segmentation/bin_threshold.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`bothat`](https://furuse.work/ops/2d/morphology/bothat.html) · [`dyn_threshold`](https://furuse.work/ops/2d/segmentation/dyn_threshold.html) · [`gray_bothat`](https://furuse.work/ops/2d/morphology/gray_bothat.html) · [`hx_close_edges`](https://furuse.work/ops/2d/halcon_ext/hx_close_edges.html) · [`invert_image`](https://furuse.work/ops/2d/gray/invert_image.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html)

## 35. ねじの輪郭からピッチ・フランク角・有効径 ―― 傾きは左右のフランクに逆符号で出る

[![ねじの輪郭からピッチ・フランク角・有効径 ―― 傾きは左右のフランクに逆符号で出る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/07_sampling_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/07_sampling_frames.png)

*↑ **ねじの輪郭からピッチ・フランク角・有効径 ―― 傾きは左右のフランクに逆符号で出る** ―― ISO 68-1 の基本三角形を閉形式で描いた M6 相当の投影像(1 px = 25 µm)。二値化した列幅の FFT はピッチを真値の半分 20 px と答える(上下輪郭が P/2 ずれた三角波の和は定数)。軸を 3 度傾けると左右フランク角は 33.18 / 26.74 度に割れ、半和 29.81 度が真のフランク角、半差 3.19 度が傾きの推定になる。片側フランクで測るピッチは 1 次で狂う(+3.28 / -2.79 %)が頂点間隔は 2 次(-0.12 %)。傾きを戻せば P -0.009 %、d2 +0.033 %。*

[![幅の系列は上下輪郭(P/2 ずれ)の和なので基本波が消える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/01_zero_spectrum_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_screw_thread_metrology/01_zero_spectrum.png)

*↑ 測定の図 ―― 幅の系列は上下輪郭(P/2 ずれ)の和なので基本波が消える。*

```
py -3.11 examples/poc_screw_thread_metrology.py
```

ソース: [examples/poc_screw_thread_metrology.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_screw_thread_metrology.py)

使用 op(ノートへ): [`fit_line_contours`](https://furuse.work/ops/2d/contour/fit_line_contours.html) · [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`hx_split_contours`](https://furuse.work/ops/2d/halcon_ext/hx_split_contours.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html) · [`threshold_sub_pix`](https://furuse.work/ops/2d/contour/threshold_sub_pix.html) · [`xg_regress_contours`](https://furuse.work/ops/2d/xldgeom/xg_regress_contours.html)

## 36. 竣工した部屋の壁を測る —— 外接直方体は寸法でなく部屋の向きを測っている

[![竣工した部屋の壁を測る —— 外接直方体は寸法でなく部屋の向きを測っている](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_asbuilt_wall_deviation/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_asbuilt_wall_deviation/01_scene.png)

*↑ **竣工した部屋の壁を測る —— 外接直方体は寸法でなく部屋の向きを測っている** ―― 内法 6.0 x 4.0 x 2.7 m の室内点群に、壁の倒れ(1.20〜9.00 mrad)・平面図の振れ 5.00 mrad・面外のふくらみ 9 mm を仕込み、素朴な外接直方体(AABB)と平面当てはめを同じ点群で突き合わせた。AABB は東西 +19.1 mm 過大で、部屋を走査軸に対して 1 度回すだけで +80.1 mm、10 度で +611.1 mm——これは施工誤差ではなく W cosψ + D sinψ という部屋の向きの式で、平面 2 枚の距離は ψ を振っても +2.24 mm から動かない。さらに AABB は点を 256 倍にすると +14.9 → +19.7 mm と広がり(雑音の最大値統計 2σ√(2 ln N))、測点を増やすほど悪くなる。外れ点(出 450 mm の家具)への壊れ方は 2 種類で、最小二乗は 10 % 混入で真値の 11 倍(66.3 mrad、閉形式の予測 63.8 と 4 % 以内)、RANSAC は 45 % まで持ちこたえて 55 % で棚へ乗り換える——そのとき倒れの誤差は 0.13 mrad と小さいまま面だけが 449.9 mm ずれるので、1 つの数字では破綻が見えない。面のふくらみ 1 個が倒れ(-1.258 mrad)・直交度(+0.500 mrad)・内法(+2.2 mm)の 3 つの判定を同時に汚し、どれも閉形式で 0.06 mrad 以内に予測できた。*

[![許容 ±10 mm。AABB は ψ=0.5 度で既に外れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_asbuilt_wall_deviation/02_aabb_vs_yaw_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_asbuilt_wall_deviation/02_aabb_vs_yaw.png)

*↑ 測定の図 ―― 許容 ±10 mm。AABB は ψ=0.5 度で既に外れる。*

```
py -3.11 examples/poc_asbuilt_wall_deviation.py
```

ソース: [examples/poc_asbuilt_wall_deviation.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_asbuilt_wall_deviation.py)

使用 op(ノートへ): [`aabb`](https://furuse.work/ops/3d/bounds/aabb.html) · [`angle_between_planes`](https://furuse.work/ops/3d/geometry/angle_between_planes.html) · [`angle_line_plane`](https://furuse.work/ops/3d/geometry/angle_line_plane.html) · [`distance_point_plane`](https://furuse.work/ops/3d/geometry/distance_point_plane.html) · [`fit_plane3`](https://furuse.work/ops/3d/geometry/fit_plane3.html) · [`ransac_plane`](https://furuse.work/ops/3d/robust_fit/ransac_plane.html)

## 37. 電極の呼吸を µm で測る ―― サブピクセルなら何でもよいわけではない

[![電極の呼吸を µm で測る ―― サブピクセルなら何でもよいわけではない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_breathing/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_breathing/01_scene.png)

*↑ **電極の呼吸を µm で測る ―― サブピクセルなら何でもよいわけではない** ―― 充放電で膨らむ電極の伸びを、2 時期の断面画像の層境界をサブピクセルで追って出す。真値は負極 1.00 % / 正極 0.20 % / セパレータ 0 %、積層 480.0 → 482.136 µm(+2.136 µm = +0.4450 %)。二値化して画素数を数えるゼロ点は 12 層中 0 層しか読めない一方、固定しきい値の交差はサブピクセルなので雑音なしでは当たる(+0.004495)―― 殺すのは対照群のほうで、伸びゼロのままオフセットを +0.10 かけるだけで -1.07e-02、真値の 2.4 倍の偽の伸びを逆符号で返し、ゲイン x1.30 では交差が半分に落ちて測定不能になる。勾配ピーク(measure_pos)は同じ条件で 0.0 のまま。そして自分の「誤差 1.8e-14 px」を疑って積層を小数画素ずらすと、それは真値を画素の中心に置いた検査の産物で、実際は RMS 0.0088 / 最大 0.0122 px のピークロッキングだった(負極 1 層のひずみに 3.0 % 効く)。崖は 2 段あり、本数が壊れる崖は予測した 3σ の崖より 5.5 倍手前に来る。*

[![境界は erf の重ね合わせで解析的に置いてあるので、真値は浮動小数点の精度で既知。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_breathing/02_profiles_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_electrode_breathing/02_profiles.png)

*↑ 測定の図 ―― 境界は erf の重ね合わせで解析的に置いてあるので、真値は浮動小数点の精度で既知。*

```
py -3.11 examples/poc_battery_electrode_breathing.py
```

ソース: [examples/poc_battery_electrode_breathing.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_battery_electrode_breathing.py)

使用 op(ノートへ): [`auto_threshold`](https://furuse.work/ops/2d/segmentation/auto_threshold.html) · [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`piv_peak_locking`](https://furuse.work/ops/piv/assess/piv_peak_locking.html)

## 38. ダイの傾きと TSV の位置ずれを 1 つの CT から分ける ―― 傾きは回転まで偽装する

[![ダイの傾きと TSV の位置ずれを 1 つの CT から分ける ―― 傾きは回転まで偽装する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_die_tilt_tsv_overlay/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_die_tilt_tsv_overlay/01_scene.png)

*↑ **ダイの傾きと TSV の位置ずれを 1 つの CT から分ける ―― 傾きは回転まで偽装する** ―― 上下 2 枚のダイに 7×7 の TSV を仕込み、真の位置ずれ (+0.800, −0.450) µm・回転 +0.01500°・傾き (1.20°, 0.70°) を与えた CT ボリューム 1 個だけで測り返す。上面の開口をそのまま比べるゼロ点は 2.419 µm 外し(仕様 ±1.0 µm の 2.4 倍、真の位置ずれ 0.918 µm より大きい)、その偽装量は「ダイ厚 × 上面法線の横成分」の閉形式と比 0.996 / 0.999 で一致する。ビアの軸で下面へ引き直すと 0.0023 µm まで戻る。★予想は外れた ―― 傾きは並進だけでなく回転も偽装する(Rx Ry のせん断 sinα sinβ 由来、予測 +0.00733° に対し対照群との差で実測 +0.00696°)。これは軸補正では消えず、測った傾きで逆投影して初めて対照群と同じ値に戻る。崖は 0.491° の予測に対し実測 0.492°。*

[![雲ごと 2.42 µm ずれるのが傾きの偽装。散らばりの広がりは測定精度。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_die_tilt_tsv_overlay/02_overlay_scatter_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_die_tilt_tsv_overlay/02_overlay_scatter.png)

*↑ 測定の図 ―― 雲ごと 2.42 µm ずれるのが傾きの偽装。散らばりの広がりは測定精度。*

```
py -3.11 examples/poc_die_tilt_tsv_overlay.py
```

ソース: [examples/poc_die_tilt_tsv_overlay.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_die_tilt_tsv_overlay.py)

使用 op(ノートへ): [`fit_line3`](https://furuse.work/ops/3d/geometry/fit_line3.html) · [`procrustes_fit`](https://furuse.work/ops/shapestat/procrustes/procrustes_fit.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html)

## 39. 実写のコインを数えて測る ―― 当たっている答えに、余裕があるとは限らない

[![実写のコインを数えて測る ―― 当たっている答えに、余裕があるとは限らない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_coin_metrology/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_coin_metrology/01_scene.png)

*↑ **実写のコインを数えて測る ―― 当たっている答えに、余裕があるとは限らない** ―― 「照明が斜めに落ちているから大域しきい値では駄目」で有名な実写(scikit-image coins)。背景は行 0.427→0.161 / 列 0.331→0.059 と確かに傾いているのに、★素の大域 Otsu + 穴埋め + 面積 150 が真値 24 枚をちょうど当てる(真値は面積の平坦域 50〜800・半径を明示した Hough・Sobel+穴埋めの 3 経路一致で決め、さらに円 1 個が成分 1 個に収まる 1 対 1 の検算まで通した)。★★ところが余裕は 0.05 しかない ―― 同じ形の勾配をわずかに足すだけで 24→22 枚。答えが合っていることは、余裕があることの証明にならない。★★+0.30 では面積の中央値が -0.27 % しか動かないのに最悪のコインは -24.20 %(+0.40 で -46.02 %)、しかもずれは行位置と r=-0.90 で相関する ―― 真の面積は置き場所に依らないので、この相関はまるごと誤差。★gray_tophat で平坦化すると枚数は粘るが面積の中央値が 0.29 倍になる(枚数の頑健さと寸法の頑健さは別)。★生の連結成分は 4 近傍 126 / 8 近傍 96 で 3 割違い、円形度 0.7 で絞ると 24→21 枚に減る。*

[![見た目はほとんど変わらないのに 2 枚落ちる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_coin_metrology/02_margin_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_coin_metrology/02_margin.png)

*↑ 測定の図 ―― 見た目はほとんど変わらないのに 2 枚落ちる。*

```
py -3.11 examples/poc_real_coin_metrology.py
```

ソース: [examples/poc_real_coin_metrology.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_coin_metrology.py)

使用 op(ノートへ): [`blob_count`](https://furuse.work/ops/2d/features/blob_count.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`canny`](https://furuse.work/ops/2d/segmentation/canny.html) · [`circularity`](https://furuse.work/ops/2d/features/circularity.html) · [`fill_holes`](https://furuse.work/ops/2d/region/fill_holes.html) · [`gray_tophat`](https://furuse.work/ops/2d/morphology/gray_tophat.html) · [`hough_circle_trans`](https://furuse.work/ops/2d/features/hough_circle_trans.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`sobel_amp`](https://furuse.work/ops/2d/edges/sobel_amp.html)

## 40. 弦でレールを測る ―― 伝達関数が 0 になる波長は、何 mm あっても 0 mm と出る

[![弦でレールを測る ―― 伝達関数が 0 になる波長は、何 mm あっても 0 mm と出る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rail_corrugation/02_transfer_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rail_corrugation/02_transfer.png)

*↑ **弦でレールを測る ―― 伝達関数が 0 になる波長は、何 mm あっても 0 mm と出る** ―― 軌道の凹凸を弦(正矢)で読む —— 2 点を結んだ弦から中点までの距離を測る、軌道検測とレール削正の受入れでいまも使われる方法。★ゼロ点(正矢をそのまま高さと読む)は波長で 0.0 % 〜 200.0 % に化ける: 同じ 1 本の 10 m 弦が λ=10 m を +100 %、λ=1.5 m を +50 %、λ=30 m を -50 %、λ=5.0 / 2.5 / 1.0 m を -100 % に読む —— **過大評価と過小評価が同時に起きる**ので、全体を一律の係数で直すことはできない。★★死角は幾何で厳密に予測できる: |H(λ)| = |1 - cos(πL/λ)| は λ = L/(2n) でちょうど 0、λ = L/(2n+1) で 2 倍。10 波長 × 2 本の弦の 20 通りで**予測と実測の差は最大 0.00000**、λ=5.00 m の 0.600 mm は 200 m 全長の最大絶対値でも 0.00000 mm。★1/3 オクターブ帯に整理しても消えない(比 0.00041 〜 2.000 = 4924 倍)。この節では op の total_power が効いた —— 帯の和は全 FFT ビンの和の 0.519 しかなく、欠けた 48 % は λ=30 m の通り変位が f_min の外に居るためで、帯だけ見ていたら気づけない。★|H| で割り戻す逆フィルタは死角で 6.9e7 mm に発散し、正則化を入れると 3 波長が**静かに「凹凸なし」**になる。★★弦を 2 本(10 m と 6 m)にすると 10 中 8 波長が誤差 0.1 % 以内に戻るが、共通の死角は 1 点ではなく λ = 1.000/k の**櫛**。予測を 1 つ外した —— 仕込んだ λ=0.100 m も残り、調べたら k=10 の歯だった。隣り合う死角の相対間隔はそのまま λ なので短波長ほど詰まり、波状摩耗の帯(0.03–0.30 m)だけで 30 本ある。★0.25 m 標本では 30 mm の波状摩耗が 0.750 m のうねり 0.0528 mm に化ける(短波長を止めた対照群 0.00584 mm の 9 倍。床が 0 でないのは長波長成分の漏れ)。★非対称弦(前 3.7 m / 後ろ 6.3 m)は長波長の死角を消すが、|H|=0 の条件が「a/λ も b/λ も整数」なので λ = gcd(a,b)/k = 0.100 m に死角ができる —— **波状摩耗を測るための弦が、波状摩耗の帯域に死角を作った**。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rail_corrugation/01_planted_components_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rail_corrugation/01_planted_components.png)

*↑ 測定の図*

```
py -3.11 examples/poc_rail_corrugation.py
```

ソース: [examples/poc_rail_corrugation.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_rail_corrugation.py)

使用 op(ノートへ): [`octave_bands`](https://furuse.work/ops/acoustics/level/octave_bands.html) · [`octave_spectrum`](https://furuse.work/ops/acoustics/level/octave_spectrum.html)

## 41. 堆積物の在庫量 ―― 誰も測っていない「山の下の地面」が答えを決める

[![堆積物の在庫量 ―― 誰も測っていない「山の下の地面」が答えを決める](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_stockpile_volume/05_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_stockpile_volume/05_scene.png)

*↑ **堆積物の在庫量 ―― 誰も測っていない「山の下の地面」が答えを決める** ―― 鉱山・骨材・港湾の**堆積物の在庫量**を 3-D スキャンから出す。山と地面を別々の式で置き、安息角 37 度の円錐 3 個の**和**にしたので体積が解析的に閉じる(3572.6089 m^3、セル 0.025 m の数値積分と一致)。★★**在庫量という 1 個の数字は、誰も測っていない面 —— 山の下の地面 —— の仮定で決まる**。★崖 (a) 底面の仮定は閉形式 ΔV = -A・Δh で先に印字してから測り、7 通りで差 **0.0000 m^3**。驚きは一致ではなく大きさのほうで、**測量では誤差とも呼ばない 5 cm が在庫の 1.269 %、かさ 1.6 t/m^3 なら 72.5 t**(トラック 3 台分)。★崖 (b) 遮蔽は「円錐は線織面」から可視率 = arccos((H-h_s)/(D tanφ))/π。6 通りで差 ≤ 0.0201 で、その差はセルを 1.2 → 0.6 → 0.4 m にすると 0.0339 → 0.0171 → 0.0120 と **1 次で縮む** —— **模型の誤りではなく離散化**だと切り分けられる。★★予測を 1 つ外した: 遮蔽部を補間すると体積は**過小**に出ると思っていた(円錐面は凹なので弦は下を通る)が、実測は **+17.20 % の過大**。裏側が法尻まで丸ごと見えないため三角形の相手が「山の上」ではなく**山の外の地面**になり、稜線から 30 m 先へ張った弦の勾配 0.37 m/m が真の斜面 0.75 m/m の**上**を通る。「凹だから過小」は両端が山の上にあるときの話だった。★★相殺の罠が出た: 同じ 1 か所スキャンで、真の地面を底面にすると **+17.20 %**、現場の手(外周平均の水平底面)だと **+0.51 %**。良くなったのではなく、外周の高さも同じ補間で **+0.728 m** 持ち上がって引き算で消えているだけ —— 証拠に、外周のうち**実際に見えた点だけ**で底面を決めると **+12.05 %** に戻る。**汚染された物差しで汚染された対象を測ると、誤差は消えたように見える**。★同じ形が §7 にも: 法尻に残土の土手を混ぜると**外れ値に強い RANSAC のほうが数字は悪い**(+2.48 % 対 TLS +0.61 %)が、RANSAC は土手を正しく捨てて「土手なし」の答え +1.91 % へ戻っただけで、TLS が良く見えるのは土手の持ち上げがうねりの偏りをたまたま打ち消したから。★外周平均の水平底面は footprint が概ね対称なら地面の**傾きを勝手に打ち消す**(平らな対照群 +0.01 %)。残る +1.79 % は全部うねりで、**傾いた平面を当てはめると悪化する**(+1.91 %)—— 「自由度を増やせば良くなる」は成立しない。★物差しで勝者が入れ替わる: 体積は水平底面が僅かに良く、**重心は平面当てはめが 6 分の 1**(0.07 m 対 0.42 m)。積込計画に効くのは重心のほう。★★2 つの誤差は**足し算にならない**(-0.70 % のはずが +0.51 %)—— 遮蔽の補間が底面を決める外周まで動かすので、2 つは絡む。誤差収支を「底面 x % + 遮蔽 y %」と足す報告は、この時点で嘘になる。★★道具のバグを 1 つ見つけて、その場で直した: `dem_viewshed` が**観測者の目線より高いセルを軒並み「見えない」と返していた**(平地に置いた円錐の頂点が可視 0.0、目線より高い 1541 セルの可視 0 個、底面の遮蔽率 0.8863 対 閉形式 0.5710)。視線の標本が `np.rint` で**目標セル自身**に丸まる自己遮蔽で、標本が目標セルに乗った回を数えないよう修正した(いま 頂点 1.0 / 遮蔽率 0.5900)。★**それまでの門が通した理由**が収穫で、可視領域の試験は「平地」と「壁の**向こう側**」しか見ておらず、**壁そのものが見えるか**を一度も確かめていなかった。*

[![A = 906.5 m^2。閉形式は測る前に印字してある。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_stockpile_volume/01_base_offset_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_stockpile_volume/01_base_offset.png)

*↑ 測定の図 ―― A = 906.5 m^2。閉形式は測る前に印字してある。*

```
py -3.11 examples/poc_stockpile_volume.py
```

ソース: [examples/poc_stockpile_volume.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_stockpile_volume.py)

使用 op(ノートへ): [`dem_hillshade`](https://furuse.work/ops/dem/shading/dem_hillshade.html) · [`dem_slope`](https://furuse.work/ops/dem/surface/dem_slope.html) · [`dem_viewshed`](https://furuse.work/ops/dem/visibility/dem_viewshed.html) · [`interp_scattered`](https://furuse.work/ops/math/interp_poly/interp_scattered.html) · [`moment_axes`](https://furuse.work/ops/3d/match_pose/moment_axes.html)

## 42. 多ビーム測深で海底が笑う ―― 音速を取り違えると、壊れるのは外側ビームだけ

[![多ビーム測深で海底が笑う ―― 音速を取り違えると、壊れるのは外側ビームだけ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/12_across_track_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/12_across_track.png)

*↑ **多ビーム測深で海底が笑う ―― 音速を取り違えると、壊れるのは外側ビームだけ** ―― 多ビーム音響測深で、水柱の**音速プロファイルを取り違えると平らな海底が反り返る**(smile / frown)。壊れるのは**外側ビームだけ**で、直下はほぼ無傷 —— だから現場でいちばん検査される所だけが正しく見える。真値は自分で植える: 深さ 50.0 m の完全な水平面、音速 1520 → 1480 m/s(勾配 -0.800 /s)、±70 度 141 本、判定は実在規格 **IHO S-44 Order 1a**(TVU(50 m) = **0.8201 m**)。★崖は**測る前に 2 通り印字**した。ラフな展開式 Δz ≈ (gD^2/2c0)tan^2θ の予測 **48.15 度**、一定勾配層で光線が円弧になることから出る厳密な閉形式 **48.68 度**。実測(エコー検出を止めた経路)は **48.68 度** —— **厳密式は当たり**(差 2.0e-11 m)、**展開式は 0.53 度手前に外した**(45 度まで 3.0 % 以内、70 度で 19.4 % 過大。「tan^2 で効く」は外側で崩れる)。★★**予測を 1 つ外した**: 「エコー検出は無視できる床」と見込んでいたが、**全経路の崖は 47.95 度**で 0.73 度早い。70 度ではビームが照らす帯のエコーが **21396 µs**(直下の 171 倍)に伸びて非対称になり、振幅検出の頂点が手前へ寄る(**-0.725 m**)。実機が外側で位相検出に切り替える理由が数字で出た。★**対照群で犯人を切り分ける**: 屈折だけで **-2.6974 m**、角度推定の床 **0.000000 m**、エコー検出の床 **-0.2221 m**。スマイルは角度誤差でもエコー検出誤差でもなく**屈折そのもの**。ただしエコーの床は角度とともに増えるので「床は一定」とは書けない。★**教科書式が実測の 34 % しかない**: 70 度のフットプリントは cos^2 式 **8.21 m** に対し実測 **24.14 m**。電子的に振った配列は開口が cosθ に縮んで見えるためビーム幅が 1/cosθ で広がり、正しい指数は 3(cos^3 式は -0.6 % で当たる)。★**実装の刻みだけで規格を割る**: 層内を等音速とみなす古い処理は、キャストを 2 層に切っただけで 65 度に **+1.2994 m**(TVU の 1.6 倍)。32 層で +0.0785 m と 1 次収束するので、**キャストの切り方は精度の一部**。★**真値なしでできる唯一の検査**は隣接測線の重なり。端では **2.697 m**(TVU の 3.3 倍)食い違うのに、**帯の真ん中では 0.0000 m** —— 両測線とも同じ振れ角で誤差が同じだけ乗って消えるので、帯の端まで見ないと見つからない。地形図にすると、継ぎ目なしの見かけ勾配は最大 2.99 度(スマイルの曲がり)、継ぎ目ありは最大 **49.367 度**(海底に無い崖が 1 本立つ)。★**上向き屈折(frown)では、深さが誤るのではなく何も記録されない** —— 限界角の予測 73.90 度に対し、届いた最後のビーム 73.0 度 / 届かない最初 74.0 度。swath が黙って狭くなるだけなので記録は異常に見えない。★掃引 200 ケース(音速差 25 通り × 深さ 8 通りの格子)では、±65 度 swath の **78.0 %** が端で Order 1a を割る。崖の角度は深さとともに 10 m の 64.47 度 → 200 m の 45.53 度へ単調に寄るが、漸近値 44.83 度に**ぴったりは乗らない**(TVU の定数項 a = 0.5 m が 200 m でもまだ 2 割残る)。★サーモクラインには一定勾配の当てはめも効かない: 最大 5.357 m → 1.253 m と 77 % しか取れず、しかも**直下で +0.262 m** 悪くなる —— いちばん検査される所を犠牲に外側を良くしている。★道具の穴も 4 層(fs / fs.op / fs.ledger / op_find)を引いて記録した。sonar / swath / bathym / tvu は 0 件、sound_speed / footprint / crossline は件数だけ返るが中身は無関係(件数を見て「在る」と読むと外す)。検証中に**片道の穴**も 1 つ塞いだ: ベクトル版 `refract` の docstring が「1 本ずつ回せ」としか書かず、**光線ごとに全反射を判定する `refract_rays` が既にある**ことに触れていなかった(逆向きの参照は在った)。*

[![エコーは beamform_delay_sum の角度応答 × Lambert 後方散乱で海底の帯を足し上げて合成。find_peaks + peak_subbin で検出。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/01_floor_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_multibeam_bathymetry/01_floor.png)

*↑ 測定の図 ―― エコーは beamform_delay_sum の角度応答 × Lambert 後方散乱で海底の帯を足し上げて合成。find_peaks + peak_subbin で検出。*

```
py -3.11 examples/poc_multibeam_bathymetry.py
```

ソース: [examples/poc_multibeam_bathymetry.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_multibeam_bathymetry.py)

使用 op(ノートへ): [`beamform_delay_sum`](https://furuse.work/ops/rangedoppler/beamform/beamform_delay_sum.html) · [`beamform_doa`](https://furuse.work/ops/rangedoppler/beamform/beamform_doa.html) · [`dem_slope`](https://furuse.work/ops/dem/surface/dem_slope.html) · [`find_peaks`](https://furuse.work/ops/oned/signal/find_peaks.html) · [`interp_scattered`](https://furuse.work/ops/math/interp_poly/interp_scattered.html) · [`peak_subbin`](https://furuse.work/ops/oned/signal/peak_subbin.html) · [`snell_angle`](https://furuse.work/ops/3d/optics/snell_angle.html)

### 医用・生物ウィング ―― 個数が合っていて中身が外れている

細胞を数える、核の DNA 量を読む、血管の分岐を測る、創傷の面積を追う。どれも「1 つの数字」で報告されがちで、しかもその数字が合ってしまう場面があります。過分割と過統合が釣り合って個数の偏りが +0.3 個になる細胞計数、背景を引き忘れても分類が生き残る倍数性、いちばん安定して、いちばん間違った治癒定数を返す較正。

この部屋の 4 点は、真値に「どれとどれが重なっているか」「面積と DNA 量が別々にばらつく」「分岐則を厳密に満たす木」といった、ラベル画像だけでは残らない情報を持たせています。実データに差し替えるときも、ラベル画像だけを真値と呼ぶと主題そのものが消える、と各 docstring に書いてあります。

見どころは、性能が上がったように見えて測っている量が入れ替わっている場面です。ぼかすほど面積分類器が良くなるのは、面積という名前で DNA 量を漏らしているから。1 つの指標が良くなった理由を毎回追わないと、こういう嘘を成果として持ち帰ることになります。

## 43. 重なった細胞をどう数えるか ―― 個数・過分割・過統合を別々に測る

[![重なった細胞をどう数えるか ―― 個数・過分割・過統合を別々に測る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cell_counting/01_scene_dense_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cell_counting/01_scene_dense.png)

*↑ **重なった細胞をどう数えるか ―― 個数・過分割・過統合を別々に測る** ―― 重なった細胞の合成画像で、個数・過分割・過統合を別々に数えた図。いちばん密な条件でゼロ点は 78 個中 25 個を取りこぼし、失点は全部過統合。種の間引きを振ると釣り合う点があり、個数の偏り +0.3 個なのに分割誤りは 13.3 件残る ―― 個数だけ報告すれば最良の設定として通る。*

[![誤り合計の谷と |偏り| の谷は同じ場所に来ない。どちらを最適と呼ぶかで答えが変わる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cell_counting/02_h_tradeoff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cell_counting/02_h_tradeoff.png)

*↑ 測定の図 ―― 誤り合計の谷と |偏り| の谷は同じ場所に来ない。どちらを最適と呼ぶかで答えが変わる。*

```
py -3.11 examples/poc_cell_counting.py
```

ソース: [examples/poc_cell_counting.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_cell_counting.py)

使用 op(ノートへ): [`circularity`](https://furuse.work/ops/2d/features/circularity.html) · [`distance_transform`](https://furuse.work/ops/2d/region/distance_transform.html) · [`fill_holes`](https://furuse.work/ops/2d/region/fill_holes.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`sk_otsu`](https://furuse.work/ops/2d/segmentation/sk_otsu.html) · [`vol_distance_transform`](https://furuse.work/ops/3d/medial/vol_distance_transform.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_local_maxima`](https://furuse.work/ops/3d/feature/vol_local_maxima.html) · [`vol_watershed`](https://furuse.work/ops/3d/segment/vol_watershed.html) · [`xsk2_h_maxima`](https://furuse.work/ops/2d/segmentation/xsk2_h_maxima.html)

## 44. 蛍光核の積分輝度から倍数性を出す ―― 面積では分かれない

[![蛍光核の積分輝度から倍数性を出す ―― 面積では分かれない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_nuclei_ploidy/04_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_nuclei_ploidy/04_scene.png)

*↑ **蛍光核の積分輝度から倍数性を出す ―― 面積では分かれない** ―― DNA 量 D と面積 A を別々のばらつきで撒いた蛍光核で、倍数性を面積と積分輝度から分けた図。真の面積でも誤分類 15.4 %、積分輝度は 0 %。背景を引き忘れると分類は生き残ったまま DNA 指数だけが 2.115 → 1.702(-20 %)壊れる ―― 分類だけを見ていたら気づけない。*

[![累積分布。積分輝度の 4n は 2.1 付近に固まり、面積の 2 本は大きく重なる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_nuclei_ploidy/01_histograms_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_nuclei_ploidy/01_histograms.png)

*↑ 測定の図 ―― 累積分布。積分輝度の 4n は 2.1 付近に固まり、面積の 2 本は大きく重なる。*

```
py -3.11 examples/poc_nuclei_ploidy.py
```

ソース: [examples/poc_nuclei_ploidy.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_nuclei_ploidy.py)

使用 op(ノートへ): [`aperture_photometry`](https://furuse.work/ops/astrostack/photometry/aperture_photometry.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`sg_gmm_segment`](https://furuse.work/ops/2d/segment/sg_gmm_segment.html) · [`sk_otsu`](https://furuse.work/ops/2d/segmentation/sk_otsu.html)

## 45. 血管網を抜いて分岐を測る ―― ヒゲ、分岐近傍の径の過大、そして指数の脆さ

[![血管網を抜いて分岐を測る ―― ヒゲ、分岐近傍の径の過大、そして指数の脆さ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vessel_network/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vessel_network/01_scene.png)

*↑ **血管網を抜いて分岐を測る ―― ヒゲ、分岐近傍の径の過大、そして指数の脆さ** ―― Murray の法則に厳密に従う合成血管木を細線化し、分岐点・径・指数を測った図。分岐画素をそのまま数えると 25 個の分岐に 47 画素、連結成分にまとめれば 25 個ちょうど。ヒゲを作るのは細線化ではなく境界のざらつきで(余分な分岐 0 → 72 個)、径は分岐から 3 px 未満で +26.2 % 過大。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vessel_network/02_prune_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vessel_network/02_prune.png)

*↑ 測定の図*

```
py -3.11 examples/poc_vessel_network.py
```

ソース: [examples/poc_vessel_network.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_vessel_network.py)

使用 op(ノートへ): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`distance_transform`](https://furuse.work/ops/2d/region/distance_transform.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`medial_axis_points`](https://furuse.work/ops/3d/medial/medial_axis_points.html) · [`r2_split_skeleton_lines`](https://furuse.work/ops/2d/region/r2_split_skeleton_lines.html) · [`sk_medial`](https://furuse.work/ops/2d/region/sk_medial.html) · [`skeleton`](https://furuse.work/ops/2d/region/skeleton.html) · [`skeleton_branches3d`](https://furuse.work/ops/3d/medial/skeleton_branches3d.html) · [`skeleton_endpoints3d`](https://furuse.work/ops/3d/medial/skeleton_endpoints3d.html) · [`skeleton_junctions3d`](https://furuse.work/ops/3d/medial/skeleton_junctions3d.html) · [`skeleton_prune3d`](https://furuse.work/ops/3d/medial/skeleton_prune3d.html) · [`skeletonize_vol`](https://furuse.work/ops/3d/medial/skeletonize_vol.html) · [`thinning`](https://furuse.work/ops/2d/region/thinning.html) · [`vol_distance_transform`](https://furuse.work/ops/3d/medial/vol_distance_transform.html)

## 46. 創傷面積の経時変化 ―― 較正の誤差は面積に 2 乗で効く

[![創傷面積の経時変化 ―― 較正の誤差は面積に 2 乗で効く](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_wound_area_tracking/02_scenes_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_wound_area_tracking/02_scenes.png)

*↑ **創傷面積の経時変化 ―― 較正の誤差は面積に 2 乗で効く** ―― mm 平面に置いた星形の創面(面積は閉形式)をピンホールカメラで日ごとに撮り、治癒定数 k を推定した図。距離が 4 % 違うだけで面積が 7.7 % 動き、日ごとに 1.2 % 漂うと真の k = 0.1200 に対しゼロ点は 0.1424(+18.7 %)。しかもその標準偏差 0.0049 は毎回較正の 0.0059 より小さい ―― いちばん安定して、いちばん間違った答え。*

[![ゼロ点の面積誤差。実測は閉形式の 2 乗則に乗り、線形近似からは外れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_wound_area_tracking/01_dist_square_law_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_wound_area_tracking/01_dist_square_law.png)

*↑ 測定の図 ―― ゼロ点の面積誤差。実測は閉形式の 2 乗則に乗り、線形近似からは外れる。*

```
py -3.11 examples/poc_wound_area_tracking.py
```

ソース: [examples/poc_wound_area_tracking.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_wound_area_tracking.py)

使用 op(ノートへ): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_select_largest`](https://furuse.work/ops/blob/select/blob_select_largest.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`warp_by_plane`](https://furuse.work/ops/3d/plane_sweep_stereo/warp_by_plane.html)

## 47. 蛍光の共局在は漏れ込みで嘘をつく ―― Pearson と Manders は別の場所で壊れる

[![蛍光の共局在は漏れ込みで嘘をつく ―― Pearson と Manders は別の場所で壊れる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/01_scene_channels_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/01_scene_channels.png)

*↑ **蛍光の共局在は漏れ込みで嘘をつく ―― Pearson と Manders は別の場所で壊れる** ―― 細胞体に小胞状の点を 2 色ぶん撒き、B の点の 0 / 25 / 50 / 100 % を A と同位置に置いて真の共局在率を握る。漏れ込み行列 [[1, α], [β, 1]] と細胞質・PSF・光子雑音を掛けた観測に Pearson r と Otsu-Manders を当てると、無関係な 2 色が α=β=10 % で r=0.203、M1=0.133 になる。単染色対照から α を 0.0996(真値 0.10)と推定して線形分離すれば r は 0.007 に戻るが、Manders は 100 % でも 0.705(Otsu より下の裾が落ちる、閉形式の予想 0.756)。Pearson が 0.5 を超える崖は対称漏れ込み α=0.282(予想 2−√3=0.268)、ぼけの崖は Manders だけに来て σ=2.5 px で Otsu の前景が細胞体へ飛び移る。Costes のシャッフル検定は漏れ込みだけの r を p=0.000 で「有意」と言う。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/02_scene_unmixed_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colocalization_crosstalk/02_scene_unmixed.png)

*↑ 測定の図*

```
py -3.11 examples/poc_colocalization_crosstalk.py
```

ソース: [examples/poc_colocalization_crosstalk.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_colocalization_crosstalk.py)

使用 op(ノートへ): [`gauss_image`](https://furuse.work/ops/2d/smoothing/gauss_image.html) · [`mat_lstsq`](https://furuse.work/ops/math/linalg/mat_lstsq.html) · [`mat_solve`](https://furuse.work/ops/math/linalg/mat_solve.html) · [`noise_sigma`](https://furuse.work/ops/astrostack/quality/noise_sigma.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`photon_sample`](https://furuse.work/ops/photon/counting/photon_sample.html) · [`reg_erode`](https://furuse.work/ops/2d/region/reg_erode.html) · [`stat_correlation`](https://furuse.work/ops/math/stats/stat_correlation.html)

## 48. MRI のバイアス場と組織面積 ―― 灰白質と白質は逆向きに壊れ、足すと隠れる

[![MRI のバイアス場と組織面積 ―― 灰白質と白質は逆向きに壊れ、足すと隠れる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/02_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/02_scene.png)

*↑ **MRI のバイアス場と組織面積 ―― 灰白質と白質は逆向きに壊れ、足すと隠れる** ―― 楕円殻の脳スライス風ファントム(頭蓋/CSF/皺つき皮質/WM、面積は幾何で既知)に表面コイル型の乗算場と Rician 雑音を掛け、大域 3 クラス大津(xsk2_multiotsu)で 3 組織の面積を測った図。振幅 30 % で GM +20.2 % / WM -7.7 % なのに GM+WM は +0.0 % で誤差が隠れ、雑音を止めると符号が反転する(GM -11.8 %)。崖の幾何予測 30 % に対し実測は 17.5 %。log I をそのまま平滑する素朴な補正は場が無くても GM +81.8 % 壊し、分割の残差を平滑する Wells 型反復にすると 40 % でも +1.8 %。場を 4 px まで細かくすると全補正器が壊れ、SNR 15 では場なしでも GM +8.5 %(WM が GM の 2.6 倍あるので小さい組織に出る)。*

[![雑音だけでは壊れず、場だけで GM と WM が逆向きに動く。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/01_controls_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mri_bias_field/01_controls.png)

*↑ 測定の図 ―― 雑音だけでは壊れず、場だけで GM と WM が逆向きに動く。*

```
py -3.11 examples/poc_mri_bias_field.py
```

ソース: [examples/poc_mri_bias_field.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_mri_bias_field.py)

使用 op(ノートへ): [`dc_homomorphic`](https://furuse.work/ops/2d/decomposition/dc_homomorphic.html) · [`eval_bspline_surface`](https://furuse.work/ops/3d/freeform/eval_bspline_surface.html) · [`eval_poly_surface`](https://furuse.work/ops/3d/surface_fit/eval_poly_surface.html) · [`fit_bspline_surface`](https://furuse.work/ops/3d/freeform/fit_bspline_surface.html) · [`fit_poly_surface`](https://furuse.work/ops/3d/surface_fit/fit_poly_surface.html) · [`overlay_labels`](https://furuse.work/ops/annotate/overlay/overlay_labels.html) · [`xsk2_multiotsu`](https://furuse.work/ops/2d/segmentation/xsk2_multiotsu.html)

## 49. 骨梁の厚さ・間隔・骨体積率 ―― 平板モデルと直接法は同じ画像で別の値になる

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

## 50. 何枚重ねると、星の明るさは何 % の精度で測れるか

[![何枚重ねると、星の明るさは何 % の精度で測れるか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_astro_photometry/01_stack_scaling_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_astro_photometry/01_stack_scaling.png)

*↑ **何枚重ねると、星の明るさは何 % の精度で測れるか** ―― 指定どおりに置いた星野を N 枚重ね、開口測光の誤差が 1/√N で落ちるかを見た図。N = 1 → 16 で中央誤差 0.6350 % → 0.1616 %、8 通りすべてで理論から 4.6 % 以内。宇宙線 1 発で単純平均は +5.89 %、κ-σ なら +0.30 % ―― 棄却率は動かないので「棄却率が上がったから効いた」とは言えない。*

[![単純平均だけが 5.9 % 残る。κ-σ は汚染なしと区別できないところまで戻すが、棄却率はほとんど動かない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_astro_photometry/02_cosmic_ray_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_astro_photometry/02_cosmic_ray.png)

*↑ 測定の図 ―― 単純平均だけが 5.9 % 残る。κ-σ は汚染なしと区別できないところまで戻すが、棄却率はほとんど動かない。*

```
py -3.11 examples/poc_astro_photometry.py
```

ソース: [examples/poc_astro_photometry.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_astro_photometry.py)

使用 op(ノートへ): [`aperture_photometry`](https://furuse.work/ops/astrostack/photometry/aperture_photometry.html) · [`drizzle_resample`](https://furuse.work/ops/astrostack/stack/drizzle_resample.html) · [`lucky_select`](https://furuse.work/ops/astrostack/quality/lucky_select.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`sigma_clip_stack`](https://furuse.work/ops/astrostack/stack/sigma_clip_stack.html) · [`synth_frame_series`](https://furuse.work/ops/astrostack/synth/synth_frame_series.html) · [`synth_starfield`](https://furuse.work/ops/astrostack/synth/synth_starfield.html)

## 51. 星の位置は何分の 1 画素まで測れて、どこで崖に落ちるか

[![星の位置は何分の 1 画素まで測れて、どこで崖に落ちるか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_star_astrometry/03_starfield_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_star_astrometry/03_starfield.png)

*↑ **星の位置は何分の 1 画素まで測れて、どこで崖に落ちるか** ―― 既知の天球座標から描いた星の位置を 4 手法で測り、Fisher 情報の理論限界と比べた図。S/N 298 で重心(ゼロ点)は理論の 5.56 倍、背景引き重心は 1.03 倍で、限界を上回った手法は無い。暗い端でゼロ点が限界を下回って見える(0.2790 px 対 0.3471 px)のは、感度 0.038 で初期値の四捨五入を返しているだけ。*

[![暗い端で素の重心が下限を割って見えるのは「動かない推定器」だから(感度 0.038)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_star_astrometry/01_snr_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_star_astrometry/01_snr_sweep.png)

*↑ 測定の図 ―― 暗い端で素の重心が下限を割って見えるのは「動かない推定器」だから(感度 0.038)。*

```
py -3.11 examples/poc_star_astrometry.py
```

ソース: [examples/poc_star_astrometry.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_star_astrometry.py)

使用 op(ノートへ): [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`noise_sigma`](https://furuse.work/ops/astrostack/quality/noise_sigma.html) · [`psf_fit`](https://furuse.work/ops/astrostack/photometry/psf_fit.html) · [`star_detect`](https://furuse.work/ops/astrostack/photometry/star_detect.html)

## 52. 縁が暗い天体の輪郭はどこか ―― 周辺減光があると「50 % 法」は半径を小さく見る

[![縁が暗い天体の輪郭はどこか ―― 周辺減光があると「50 % 法」は半径を小さく見る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_limb_darkening/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_limb_darkening/01_scene.png)

*↑ **縁が暗い天体の輪郭はどこか ―― 周辺減光があると「50 % 法」は半径を小さく見る** ―― 周辺減光つきの太陽面をシーイング越しに撮り、縁の半径を 50 % 法・勾配最大・モデル当てはめで測った図。「偏りは減光係数に比例」の予想は外れ、u = 0.8 で -12.76 px(幾何だけの予測 -13.14 px)。しきい値 0.26 付近でぼけの影響が消える打ち消し点は、u を変えると 0.38 へ動く。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_limb_darkening/02_bias_vs_u_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_solar_limb_darkening/02_bias_vs_u.png)

*↑ 測定の図*

```
py -3.11 examples/poc_solar_limb_darkening.py
```

ソース: [examples/poc_solar_limb_darkening.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_solar_limb_darkening.py)

使用 op(ノートへ): [`edge_points`](https://furuse.work/ops/3d/edges/edge_points.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`mat_lstsq`](https://furuse.work/ops/math/linalg/mat_lstsq.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html)

## 53. 全天カメラの雲量 ―― 画素を数えると位置で偏る

[![全天カメラの雲量 ―― 画素を数えると位置で偏る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_allsky_cloud_cover/03_mask_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_allsky_cloud_cover/03_mask_sweep.png)

*↑ **全天カメラの雲量 ―― 画素を数えると位置で偏る** ―― 魚眼(等距離射影)の空に球冠の雲(立体角は閉形式)を置き、画素数比と立体角重みで雲量を数えた図。同じ雲が天頂角 0 → 82 度で 0.00789 → 0.01142(1.45 倍)に読める。幾何だけの誤差 -5.02 % と検出だけの誤差 +37.95 % が、素朴な数え方では +29.73 % に打ち消し合う。*

[![画素数比は天頂で 0.81、地平線側で 1.17。重みを掛けると 1 に張り付く。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_allsky_cloud_cover/01_jacobian_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_allsky_cloud_cover/01_jacobian.png)

*↑ 測定の図 ―― 画素数比は天頂で 0.81、地平線側で 1.17。重みを掛けると 1 に張り付く。*

```
py -3.11 examples/poc_allsky_cloud_cover.py
```

ソース: [examples/poc_allsky_cloud_cover.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_allsky_cloud_cover.py)

使用 op(ノートへ): [`polar_trans_image`](https://furuse.work/ops/2d/geometry/polar_trans_image.html)

## 54. 海氷密接度 ―― 混合画素をどう数えるかで答えが変わる

[![海氷密接度 ―― 混合画素をどう数えるかで答えが変わる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sea_ice_concentration/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sea_ice_concentration/01_scene.png)

*↑ **海氷密接度 ―― 混合画素をどう数えるかで答えが変わる** ―― PSF でぼかした海氷/水の 2 バンド像から密接度を硬い分類と線形混合分解で出した図。硬い分類は -4.2 ポイント、分解は +0.02 ポイント。偏りは周長率で説明がつき(R² = 0.984)、密接度 0.49 付近でゼロを横切る ―― そこだけで検証すると合格する。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sea_ice_concentration/02_bias_vs_threshold_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_sea_ice_concentration/02_bias_vs_threshold.png)

*↑ 測定の図*

```
py -3.11 examples/poc_sea_ice_concentration.py
```

ソース: [examples/poc_sea_ice_concentration.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_sea_ice_concentration.py)

使用 op(ノートへ): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`mat_lstsq`](https://furuse.work/ops/math/linalg/mat_lstsq.html)

## 55. 畑の緑を数える ―― 被覆率の真値を画素ごとの葉の面積率で持つ

[![畑の緑を数える ―― 被覆率の真値を画素ごとの葉の面積率で持つ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vegetation_cover/01_mixed_pixel_response_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vegetation_cover/01_mixed_pixel_response.png)

*↑ **畑の緑を数える ―― 被覆率の真値を画素ごとの葉の面積率で持つ** ―― 4 バンドの圃場像から被覆率を出し、画素ごとの葉の面積率を真値にした図。ゼロ点(緑チャネルに大津)は中期で +16.3 pp 上振れし、散らばりはどの手法も 0.5 pp 以下なので、効いている差はほぼ全部が偏り。発芽期・湿った土では被覆率の偏り -0.2 pp なのに適合率も再現率も 0.000 ―― 数字だけ合っていて画素が 1 つも当たっていない。*

[![影ゼロならゼロ点も悪くない。影は『暗さ』を手掛かりにする手法に直接刺さる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vegetation_cover/02_shadow_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_vegetation_cover/02_shadow_sweep.png)

*↑ 測定の図 ―― 影ゼロならゼロ点も悪くない。影は『暗さ』を手掛かりにする手法に直接刺さる。*

```
py -3.11 examples/poc_vegetation_cover.py
```

ソース: [examples/poc_vegetation_cover.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_vegetation_cover.py)

使用 op(ノートへ): [`cv_otsu`](https://furuse.work/ops/2d/segmentation/cv_otsu.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`sk_otsu`](https://furuse.work/ops/2d/segmentation/sk_otsu.html)

## 56. 地形を測る ―― 傾斜・水の流れ・日当たりを閉形式と突き合わせる

[![地形を測る ―― 傾斜・水の流れ・日当たりを閉形式と突き合わせる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dem_terrain/01_cone_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dem_terrain/01_cone.png)

*↑ **地形を測る ―― 傾斜・水の流れ・日当たりを閉形式と突き合わせる** ―― 平面・円錐・ガウス丘で傾斜・曲率・天空率を閉形式と突き合わせた図。ガウス丘の曲率誤差はセルを半分にすると約 4 分の 1 ―― 離散化の誤差であって式の誤りではない。天空率は 513×513・8 方位で 2.03 秒 ―― 書き直す前は 41.9 秒かかっていて、テストは「動く」ことしか確かめていなかった。*

[![参照線と平行 = 2 次収束 = 離散化の誤差。式が違えばセルを細かくしても誤差は下げ止まる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dem_terrain/02_curvature_convergence_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dem_terrain/02_curvature_convergence.png)

*↑ 測定の図 ―― 参照線と平行 = 2 次収束 = 離散化の誤差。式が違えばセルを細かくしても誤差は下げ止まる。*

```
py -3.11 examples/poc_dem_terrain.py
```

ソース: [examples/poc_dem_terrain.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dem_terrain.py)

使用 op(ノートへ): [`dem_aspect`](https://furuse.work/ops/dem/surface/dem_aspect.html) · [`dem_curvature`](https://furuse.work/ops/dem/surface/dem_curvature.html) · [`dem_fill_sinks`](https://furuse.work/ops/dem/hydrology/dem_fill_sinks.html) · [`dem_flow_accumulation`](https://furuse.work/ops/dem/hydrology/dem_flow_accumulation.html) · [`dem_hillshade`](https://furuse.work/ops/dem/shading/dem_hillshade.html) · [`dem_sky_view_factor`](https://furuse.work/ops/dem/visibility/dem_sky_view_factor.html) · [`dem_slope`](https://furuse.work/ops/dem/surface/dem_slope.html)

## 57. 河川の水位を斜め写真から測る ―― 透視を無視した「行番号」は弓なりに外れる

[![河川の水位を斜め写真から測る ―― 透視を無視した「行番号」は弓なりに外れる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_water_level/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_water_level/01_scene.png)

*↑ **河川の水位を斜め写真から測る ―― 透視を無視した「行番号」は弓なりに外れる** ―― 量水標を斜めから撮った像で水面線を検出し、水位に直した図。目盛り 2 点の線形換算は最大 -6.4 cm(水位 1.00 m)弓なりに外れ、符号は水位でなく内挿(-6.6 cm)か外挿(+16.3 cm)かで決まる。4 点ホモグラフィなら 0.2 cm 以下で、残るのは透視でなく水面線の検出誤差。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_water_level/02_bias_vs_level_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_water_level/02_bias_vs_level.png)

*↑ 測定の図*

```
py -3.11 examples/poc_water_level.py
```

ソース: [examples/poc_water_level.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_water_level.py)

使用 op(ノートへ): [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`mat_svd`](https://furuse.work/ops/math/linalg/mat_svd.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`projective_trans_image`](https://furuse.work/ops/2d/geometry/projective_trans_image.html) · [`ransac_line`](https://furuse.work/ops/3d/robust_fit/ransac_line.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html)

## 58. 系外惑星トランジットを開口測光で取り出す ―― 深さと継続時間は別々に壊れる

[![系外惑星トランジットを開口測光で取り出す ―― 深さと継続時間は別々に壊れる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/01_scene_starfield_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/01_scene_starfield.png)

*↑ **系外惑星トランジットを開口測光で取り出す ―― 深さと継続時間は別々に壊れる** ―― 合成星野 240 枚に目標星だけ 10 ppt の周辺減光つきトランジットを仕込み、透明度変動・副画素ドリフト・フラット不均一・光子雑音を別々の乱数で載せて、fullseye の star_detect → frame_align → aperture_photometry で光度曲線を取り出す。ゼロ点(目標星の開口積分)は雲で深さ +72 ppt に壊れ、比較星との比なら -0.13 ppt / T14 -0.9 fr。比較星の選び方で残差 rms は 1.91〜11.43 ppt(6.0 倍)、逆分散重みは生の分散で決めると雲に騙されて単純和より 1.52 倍悪い。開口 1σ の崖は予想した重心誤差ではなく op の開口マスクの階段(supersample=8、不動の星で理論比 1.69 → 32 で 0.93)。検出限界 SNR=5 は暦既知で実測 1.48 / 理論 1.45 ppt、暦未知は 2.0 ppt で深さより先に継続時間が壊れる。ドリフト 2 px とフラット 3 % は単独で 0.16 / 0.08 ppt だが掛け算で 0.94 ppt、4 px で 2.97 ppt(真値の 30 %)の偽の深さ。*

[![前/入/最深部/出/後の各段階で平均した画像からトランジット外の平均を引いた [e-)。4 倍拡大](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/02_frames_transit_phases_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_exoplanet_transit/02_frames_transit_phases.png)

*↑ 測定の図 ―― 前/入/最深部/出/後の各段階で平均した画像からトランジット外の平均を引いた [e-]。4 倍拡大*

```
py -3.11 examples/poc_exoplanet_transit.py
```

ソース: [examples/poc_exoplanet_transit.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_exoplanet_transit.py)

使用 op(ノートへ): [`aperture_photometry`](https://furuse.work/ops/astrostack/photometry/aperture_photometry.html) · [`frame_align`](https://furuse.work/ops/astrostack/align/frame_align.html) · [`normalize`](https://furuse.work/ops/shape2d/descriptor/normalize.html) · [`sigma_clip_stack`](https://furuse.work/ops/astrostack/stack/sigma_clip_stack.html) · [`star_detect`](https://furuse.work/ops/astrostack/photometry/star_detect.html)

## 59. 河川表面流速を斜め動画から測る(LSPIV)―― 速度の誤差と流量の誤差は別に数える

[![河川表面流速を斜め動画から測る(LSPIV)―― 速度の誤差と流量の誤差は別に数える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/01_scene.png)

*↑ **河川表面流速を斜め動画から測る(LSPIV)―― 速度の誤差と流量の誤差は別に数える** ―― 幅 8 m・最大 1.5 m/s のべき乗則の流速分布を真値に、泡トレーサを毎コマ動かして描いた川面を岸の斜めカメラ(ホモグラフィ既知)で 60 コマ撮り、空の映り込み・波紋・雑音を別々に足して、fullseye の piv_cross_correlate → warp_by_plane(正射化)→ piv_to_velocity で u(y) と流量 Q = h∫u dy を出す。ゼロ点(斜めのまま 1 尺度で換算)は近岸 +0.31 / 遠岸 -0.28 m/s と符号が逆で、見かけの川幅が 3.3 m に化けて流量 -57 %。正射化で速度 RMS 0.074 m/s・流量 -7.8 % だが、対照群でも流量 -3.0 % のうち -2.5 % は岸の台形積分だけで生じ、速度とは無関係。密度の崖は nan ではなく外れ値で来る(0.05 % で旗 44 %、アンサンブル相関は外れ窓を救わない)。窓を広げても岸の速度は「窓幅×勾配」の予想より桁で小さく(-0.008 m/s)、代わりに流量が -1.1 → -7.0 % と崖になる。動かない映り込みは細かいときだけ効き、引かれてから(速度比 0.70)張り付く(0.03)、時間中央値引きで 0.998 に戻る。dt の崖は 1/4 則ではなく対の消失で、探索上限を外しても同じ k=4 に立つ。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/02_frames_oblique_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_river_surface_velocity/02_frames_oblique.png)

*↑ 測定の図*

```
py -3.11 examples/poc_river_surface_velocity.py
```

ソース: [examples/poc_river_surface_velocity.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_river_surface_velocity.py)

使用 op(ノートへ): [`highpass_image`](https://furuse.work/ops/2d/frequency/highpass_image.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`piv_ensemble_correlate`](https://furuse.work/ops/piv/estimate/piv_ensemble_correlate.html) · [`piv_error_stats`](https://furuse.work/ops/piv/assess/piv_error_stats.html) · [`piv_outlier_mask`](https://furuse.work/ops/piv/validate/piv_outlier_mask.html) · [`piv_replace_outliers`](https://furuse.work/ops/piv/validate/piv_replace_outliers.html) · [`piv_sample_at_windows`](https://furuse.work/ops/piv/assess/piv_sample_at_windows.html) · [`piv_to_velocity`](https://furuse.work/ops/piv/field/piv_to_velocity.html) · [`sigma_clip_stack`](https://furuse.work/ops/astrostack/stack/sigma_clip_stack.html) · [`warp_by_plane`](https://furuse.work/ops/3d/plane_sweep_stereo/warp_by_plane.html)

## 60. 変化検出と位置合わせ誤差 ―― 偽陽性はエッジの帯、しかも崖つき

[![変化検出と位置合わせ誤差 ―― 偽陽性はエッジの帯、しかも崖つき](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/03_map_fp_shift_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/03_map_fp_shift.png)

*↑ **変化検出と位置合わせ誤差 ―― 偽陽性はエッジの帯、しかも崖つき** ―― 2 時期の合成地表(畑・道路・建物・森林・湖)に建物新設・伐採・水域拡大を仕込み、時期 2 をサブピクセル平行移動・微小回転・照明差で崩して差分の偽陽性を測った。偽陽性はずれ 0.3 px まで雑音の床、0.5 px から崖(PSF から予測した δ*=τσ√2π/C=0.351 px と一致)、3 px で 7175 px。エッジ総長×ずれの比例則は 3 px で 0.78 倍だが崖を説明せず、PSF と雑音を入れた台帳予測は 0.84〜1.07 倍。位置合わせ 3 経路(PIV/特徴点/LK)は残留 0.02〜0.13 px まで戻すが、唯一の位相相関は 3-D 用の整数精度で残留 0.72 px ―― その偽陽性 995 px は「ずれだけ」の掃引を同じ残留で読んだ 915 px に乗る。伐採は位置合わせが完璧でも検出率 0.33、照明差だけの偽陽性 17198 px は放射補正で 0 になるがずれの 3497 px は直らない。*

[![0.35 px までゼロ、そこから立ち上がる。比例則は崖を説明しない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/01_plot_fp_vs_shift_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_change_detection_misreg/01_plot_fp_vs_shift.png)

*↑ 測定の図 ―― 0.35 px までゼロ、そこから立ち上がる。比例則は崖を説明しない。*

```
py -3.11 examples/poc_change_detection_misreg.py
```

ソース: [examples/poc_change_detection_misreg.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_change_detection_misreg.py)

使用 op(ノートへ): [`affine_trans_image`](https://furuse.work/ops/2d/geometry/affine_trans_image.html) · [`histogram_match`](https://furuse.work/ops/colortransport/matching/histogram_match.html) · [`match_phase_3d`](https://furuse.work/ops/3d/match_pose/match_phase_3d.html) · [`opening_circle`](https://furuse.work/ops/2d/region/opening_circle.html) · [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`piv_outlier_mask`](https://furuse.work/ops/piv/validate/piv_outlier_mask.html) · [`procrustes_fit`](https://furuse.work/ops/shapestat/procrustes/procrustes_fit.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html) · [`voxel_iou`](https://furuse.work/ops/3d/metrics/voxel_iou.html)

## 61. 葉の病斑面積率 ―― 色の軸は照明に勝つが、等級は葉マスクと縁の定義で決まる

[![葉の病斑面積率 ―― 色の軸は照明に勝つが、等級は葉マスクと縁の定義で決まる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/01_scene.png)

*↑ **葉の病斑面積率 ―― 色の軸は照明に勝つが、等級は葉マスクと縁の定義で決まる** ―― 閉形式の葉輪郭に既知面積の病斑を植え、土・片側照明・白飛び・影を重ねた合成葉で、病斑面積率(病斑画素/葉画素)を測る。緑チャネルの固定しきい値(ゼロ点)は土の背景だけで +65.2 pt 外れ、白色方向を射影で消した G で葉を切り Lab の a* で病斑を切ると標準場面で -0.8 pt に収まる。照明むらは 50 % まで a* を動かさないが、白飛びの鏡面反射は a* に偽陽性だけを出し(20 % で +12.6 pt、偽陰性 0.0)、白を足しても動かない色相なら +2.0 pt。病斑の縁のぼけ幅 4 px では「不透明度 25 %/75 % のどちらを境界にするか」だけで面積率が ±3.5 pt 動き(Steiner の式が 0.4 pt 以内で予測)、等級境界 ±3 pt に置いた 40 枚は土の上ではどの手法も 19〜35 枚が誤等級 ―― 黒布の上で明るさで葉を切ると色相の固定しきい値で 8 枚。*

[![FN(青)の大きな塊は影と鏡面反射が重なった病斑(葉マスクごと落ちる)。FP(赤)は鏡面反射の下と病斑の縁。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/02_error_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_leaf_disease_area/02_error_map.png)

*↑ 測定の図 ―― FN(青)の大きな塊は影と鏡面反射が重なった病斑(葉マスクごと落ちる)。FP(赤)は鏡面反射の下と病斑の縁。*

```
py -3.11 examples/poc_leaf_disease_area.py
```

ソース: [examples/poc_leaf_disease_area.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_leaf_disease_area.py)

使用 op(ノートへ): [`access_channel`](https://furuse.work/ops/2d/color/access_channel.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_overlay`](https://furuse.work/ops/blob/extract/blob_overlay.html) · [`fill_holes`](https://furuse.work/ops/2d/region/fill_holes.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`linear_to_srgb`](https://furuse.work/ops/gfx2d/colorspace/linear_to_srgb.html) · [`reg_close`](https://furuse.work/ops/2d/region/reg_close.html) · [`reg_erode`](https://furuse.work/ops/2d/region/reg_erode.html) · [`rgb_to_lab`](https://furuse.work/ops/imgmetrics/colorspace/rgb_to_lab.html) · [`select_largest`](https://furuse.work/ops/2d/region/select_largest.html) · [`sk_otsu`](https://furuse.work/ops/2d/segmentation/sk_otsu.html) · [`specular_free_transform`](https://furuse.work/ops/specular/dichromatic/specular_free_transform.html) · [`srgb_to_linear`](https://furuse.work/ops/gfx2d/colorspace/srgb_to_linear.html) · [`trans_from_rgb`](https://furuse.work/ops/2d/color/trans_from_rgb.html)

## 62. 年輪を数えて幅の時系列を取り出す ―― 年数の誤差と幅の相関は別の量

[![年輪を数えて幅の時系列を取り出す ―― 年数の誤差と幅の相関は別の量](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/01_scene.png)

*↑ **年輪を数えて幅の時系列を取り出す ―― 年数の誤差と幅の相関は別の量** ―― 偏心した髄・偏心成長・周方向のうねり・うねる割れ目・腐朽斑・木目・ぼけを載せた 36 年の円板を閉形式で仕込み、髄から 1 本の放射線のピーク数(ゼロ点)と、極座標展開+外縁で半径を正規化+θ 方向メディアン+24 扇形の測定線の合意(中央値)を比べた。ゼロ点は 24 方向中 18 方向でしか年数が合わないが、間違えた 6 方向でも幅の相関は中央値 0.900。合意法は 36 年・欠落 0・幅の相関 0.996(平均誤差 0.13 px)。髄の推定誤差 20 px でも幅の相関は 0.994 ―― cos で変調されるのは半径(傾き -14.9 px)で幅(-0.02 px)ではなく、減るのは髄近くの年数(予測 2 / 実測 2)。細い年輪は合意法 2.5 px、ゼロ点 3.0 px から落ち、ぼけ σ 4 px でゼロ点は偽輪 13 本を数える。*

[![偏心成長で境界が θ とともに斜めに走るので、正規化しないとθ 窓の中で外側の年輪がにじむ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/02_polar_stages_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_tree_ring_dendro/02_polar_stages.png)

*↑ 測定の図 ―― 偏心成長で境界が θ とともに斜めに走るので、正規化しないとθ 窓の中で外側の年輪がにじむ。*

```
py -3.11 examples/poc_tree_ring_dendro.py
```

ソース: [examples/poc_tree_ring_dendro.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_tree_ring_dendro.py)

使用 op(ノートへ): [`derivate_funct_1d`](https://furuse.work/ops/oned/function/derivate_funct_1d.html) · [`find_peaks`](https://furuse.work/ops/oned/signal/find_peaks.html) · [`gen_measure_rectangle2`](https://furuse.work/ops/measure1d/caliper/gen_measure_rectangle2.html) · [`measure_pos`](https://furuse.work/ops/measure1d/caliper/measure_pos.html) · [`median_rect`](https://furuse.work/ops/2d/rank/median_rect.html) · [`polar_unwrap`](https://furuse.work/ops/3d/curvilinear/polar_unwrap.html) · [`smooth_funct_1d_gauss`](https://furuse.work/ops/oned/function/smooth_funct_1d_gauss.html)

## 63. 太陽光発電所のドローン熱画像 —— 温度差を測っているつもりで、風と角度を測っている

[![太陽光発電所のドローン熱画像 —— 温度差を測っているつもりで、風と角度を測っている](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/06_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/06_scene.png)

*↑ **太陽光発電所のドローン熱画像 —— 温度差を測っているつもりで、風と角度を測っている** ―― 定常熱収支の閉形式でメガソーラーのアレイを合成し、既知の故障(セル内ホットスポット・ストリング故障)と、故障ではない温度差(影・汚れ)を仕込んだ図。余剰発熱 320 W/m² のホットスポットは薄まる前 11.20 K なのにカメラには 4.23 K しか届かず、薄めているのは予想した熱伝導(×0.960)ではなくカメラ(×0.511)だった。電気的故障をひとつも置かない対照群でも、画像平均を基準にすると塊が 6 個上がる(健全 1・非故障の温度差 5)。崖はしきい値ではなく面積の門が決め、ホットスポットは風速 1.0 m/s で消える(面積基準の予測 1.1 m/s、ピーク基準の予測 3.0 m/s は外れ)。列間影は同じストリングの日向側を +4.68 K 熱くし、本物のストリング故障 +5.55 K との差は 0.87 K しかない。*

[![「偽」= 故障でも影でも汚れでもない場所に出た塊。しきい値 3.0 K、風速 1.0 m/s。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/01_norm_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pv_thermal_survey/01_norm_table.png)

*↑ 測定の図 ―― 「偽」= 故障でも影でも汚れでもない場所に出た塊。しきい値 3.0 K、風速 1.0 m/s。*

```
py -3.11 examples/poc_pv_thermal_survey.py
```

ソース: [examples/poc_pv_thermal_survey.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pv_thermal_survey.py)

使用 op(ノートへ): [`beer_lambert_transmittance`](https://furuse.work/ops/optics/glassbody/beer_lambert_transmittance.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_select`](https://furuse.work/ops/blob/select/blob_select.html) · [`fresnel_dielectric`](https://furuse.work/ops/optics/interface/fresnel_dielectric.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`overlay_mask`](https://furuse.work/ops/annotate/overlay/overlay_mask.html) · [`surface_form_remove`](https://furuse.work/ops/roughness/prepare/surface_form_remove.html) · [`volume_downsample`](https://furuse.work/ops/3d/preprocess/volume_downsample.html) · [`warp_by_plane`](https://furuse.work/ops/3d/plane_sweep_stereo/warp_by_plane.html) · [`zoom_image_factor`](https://furuse.work/ops/2d/geometry/zoom_image_factor.html)

## 64. 実写の深宇宙に既知の星を仕込む ―― 汚染は測定値と信頼度を同じ向きに嘘つかせる

[![実写の深宇宙に既知の星を仕込む ―― 汚染は測定値と信頼度を同じ向きに嘘つかせる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_sky_photometry/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_sky_photometry/01_scene.png)

*↑ **実写の深宇宙に既知の星を仕込む ―― 汚染は測定値と信頼度を同じ向きに嘘つかせる** ―― Hubble Deep Field(NASA/STScI、public domain)の**本物の背景**に、フラックスが分かっているガウシアン星を仕込んで回収する ―― 真値は自分で入れたので確実、背景だけが本物。★実写の空は正規分布ではない: 頑健なばらつき 1,474 e- に対し素の標準偏差は 6,698 e-(4.54 倍)で、std をノイズだと思うと検出限界を 4.5 倍甘く出す。★背景は 1 つの数字ではなく、64x64 タイル 195 枚で 3,176〜8,448 e- に散る(大域中央値で引くと最大 3.6σ の系統誤差)。★★空だと思った場所でも開口に**一定量**が混入する ―― 回収比は F=2,000 e- で 4.38 倍、100,000 で 1.058 倍。これは倍率ではなく足し算で、1 + C/(F·frac) に最大ずれ 0.9 % で乗る(C = 6,677 e-、背景×実効画素のわずか 3.0 %)。★「偏りが 10 % を切るのは 67,521 e- から」と**先に予測してから**測ると回収比 1.086(予測 1.100)。★★混雑した場所では桁が変わる(341 倍 → 7.80 倍)―― 中央値は「外れ値に強い」のであって、視野の半分が汚染されていたら中央値こそが汚染。★★信頼度も同じ向きに嘘をつく: op が返す SNR 19.2 に対し同じ背景からの閉形式は 4.2。S/N は測ったフラックスから作るので、**S/N を採否の門にすると汚染された測定ほど通る**。*

[![開口 1 つあたり C = 6677 e- の足し算として説明できる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_sky_photometry/02_recovery_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_sky_photometry/02_recovery.png)

*↑ 測定の図 ―― 開口 1 つあたり C = 6677 e- の足し算として説明できる。*

```
py -3.11 examples/poc_real_sky_photometry.py
```

ソース: [examples/poc_real_sky_photometry.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_sky_photometry.py)

使用 op(ノートへ): [`aperture_photometry`](https://furuse.work/ops/astrostack/photometry/aperture_photometry.html)

## 65. 疎な温度センサから 3-D 熱場を復元する ―― 格子の死角がラックを消す

[![疎な温度センサから 3-D 熱場を復元する ―― 格子の死角がラックを消す](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_datacenter_thermal_field/01_scene_truth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_datacenter_thermal_field/01_scene_truth.png)

*↑ **疎な温度センサから 3-D 熱場を復元する ―― 格子の死角がラックを消す** ―― サーバ室 12 x 8.4 x 3.0 m の温度場を式で置き、格子状の温度センサから復元してホットスポット 3 台を探す。★ゼロ点(全センサの平均 = 場は平らとみなす)は RMSE 2.192 °C でホットスポットを 1 台も見つけない。最良の RBF は 0.214 °C = 10.2 倍。★★崖は測る前に閉形式で言える: 間隔 d の 3-D 格子でピークからいちばん遠い点はセル中心の d√3/2 なので、見えるピークは **exp(-3d²/8σ²)** 倍に落ち、半減間隔は d* = 1.3596σ。幾何だけを取り出した実測との差は最大 **1.2e-15** —— 完全に一致する。★**外れたのは閉形式ではなく「現場で測れる量」のほう**。復元した場のピークには背景の復元誤差が同じ場所に載るので、素朴な実測は予測を最大 +0.2598 超過する —— つまり**崖は実際より浅く見える**。σ=0.22 m のラックは d=1.20 m で幾何の回復 0.000014(消滅)なのに、素朴に測ると 0.1609 残って見える。残っているのは背景の誤差。★閉形式は曲線ではなく**床**: 同じ d=0.60 m でもラックが格子のどこに落ちるかで回復は 0.0615(セル中心)から 1.0(センサ直上)まで跳ぶ。設計に使えるのは最悪位相の値だけで、「平均すればこれくらい見える」はそのラックには通じない。★対照群 a(格子 vs 乱数、同じ本数): 乱数は死角を**消さない。どのラックが死角に落ちるかを振るだけ**。格子の最悪距離を超える乱数点は実測 6.17 %(Poisson の予測 6.58 %、差 0.41 ポイント)。格子は幾何の下限を 1 度も割らないが、乱数は 3 台中 2 台で割った —— 同じ本数でも「最悪でもここまで見える」と設計時に言い切れるかが違う。★★対照群 b(補間法 3 種): **動かないのは指数、動くのは係数**。log 回復 vs d² の傾きは予測 -3.0612 /m² に対し 3 手法とも最大 3.05 % 差。しかし「崖の位置は手法で動かない」という予測は外した —— 薄板スプラインは内挿なのに節点の値を超えて一律 1.372 倍持ち上がり、半減間隔を 0.4777 → 0.6015 m(26 %)ずらす。最近傍と線形が小数点以下まで一致するのは、どちらも節点を超えないため。★「持ち上がる手法は偽の峰も同じだけ立てる」も外した: 床は最近傍 0.975 °C(雑音 0.15 °C の 6.5 倍 = 滑らかな背景を階段で近似した段差)に対し線形 0.132 / RBF 0.164 で、**持ち上がる側のほうが低い**。★物差し 3 つ(場の RMSE / ピーク温度の誤差 / 位置の誤差)を同時に勝つ手法は無い。線形補間は d=1.20 m で評価点の 71.2 % が凸包の外に出て最近傍に化ける —— センサを部屋の内側にしか置けない以上、外挿しない手法は端で必ず別の手法になる。★この PoC が炙り出した道具の穴を、その場で埋めた: 散らばった N-D 点から場を作る `fs.interp_scattered`(nearest / linear / rbf)。設計で効いたのは**凸包の外に出た割合を返り値に入れた**こと —— この PoC が測った 71.2 % は黙って NaN か別手法に化ける量なので、戻り値に居るべきだった。使ってみて `neighbors`(RBF を近傍だけで解く)も足した —— 全体解は O(n³) で1400 / 4000 / 8000 点が 0.55 / 1.76 / 7.53 秒。**op は使って初めて足りない引数が分かる**。*

[![幾何の実測は予測と最大 1.2e-15 しか違わない。素朴な実測が上に浮くぶんが背景の復元誤差。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_datacenter_thermal_field/02_cliff_prediction_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_datacenter_thermal_field/02_cliff_prediction.png)

*↑ 測定の図 ―― 幾何の実測は予測と最大 1.2e-15 しか違わない。素朴な実測が上に浮くぶんが背景の復元誤差。*

```
py -3.11 examples/poc_datacenter_thermal_field.py
```

ソース: [examples/poc_datacenter_thermal_field.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_datacenter_thermal_field.py)

使用 op(ノートへ): [`interp_scattered`](https://furuse.work/ops/math/interp_poly/interp_scattered.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`rmse`](https://furuse.work/ops/imgmetrics/fidelity/rmse.html) · [`vol_local_maxima`](https://furuse.work/ops/3d/feature/vol_local_maxima.html)

## 66. 走査幅 ―― 空撮画像から測った 1 本の数字が、捜索計画の成否を決める

[![走査幅 ―― 空撮画像から測った 1 本の数字が、捜索計画の成否を決める](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_search_sweep_width/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_search_sweep_width/01_scene.png)

*↑ **走査幅 ―― 空撮画像から測った 1 本の数字が、捜索計画の成否を決める** ―― 空撮画像から**横距離曲線** p(x)(機体直下からの横方向距離ごとの検出確率)を測り、その面積 **W = ∫p dx** を走査幅として捜索計画に渡す。画像処理と意思決定が 1 本の数字でつながる場所。★まず**走査幅の定義そのものを実証**した: 形の違う 4 本の曲線(実測 p / 幅 W の矩形 / 底辺 2W の三角形 / 二峰形)を同じ面積 **256.2 m** に揃えると、半幅 500 m に一様に撒いた目標の検出割合は 0.2559 / 0.2563 / 0.2556 / 0.2566 —— **4 つとも予測 0.2562 の 0.8σ 以内**。**曲線の形は消え、面積だけが残る**。これが 1 本の数字を計画に渡せる理由。★崖は被覆率 C = W·v·t/A = 1。閉形式を**先に印字**して min(1,C) = **1.0000**、1-exp(-C) = **0.6321**。矩形の対照群の実測は 1.0000 / 0.6348(+0.005 は航跡が有限本 n=64 だからで、厳密式 1-(1-W/Wd)^64 = 0.6350)。★★**予測を 4 つ外した**。(1) 実測の p を入れると平行捜索は **0.8464** で 1.000 に届かない —— min(1,C) は p が幅 W の**矩形**であること(定値域則)に依存していて、裾を引く実曲線では隣の航跡と裾が重なる。(2)「平らな曲線のほうが矩形に近く平行捜索に強い」は**逆**だった(0.7705 対 0.8464)。矩形に近いとは『平ら』ではなく『W の内側に立ち、外へ裾を引かない』こと(支持域/W が 2.40 対 2.25)。★同じ 2 本が**ランダム捜索では一致する**(0.6371 対 0.6357)—— ランダム捜索は面積しか見ない。(3)「端は解像度が落ちる」—— ナディア向きの中心投影では**地上分解能は端まで一定**(相対ばらつき 0.0e+00)。落ちるのは cos^4・大気・軸外ぼけのほうで、f-theta 光学なら端は 2.132 倍粗くなる。(4)「背景を引けば良くなる」—— 画像全体の中央値と σ で割るのは**アフィン変換なので順位が変わらない**(174.4 → 172.0 m)。効くのは**場所ごと**に引いたときだけ(239.6 m)。★**最適高度は内点に来た**(220 m で W = 258.1 ± 4.0 m)。ただし 220 m と 300 m は標準誤差内で**測り分けられていない**と正直に書いた。低高度側で落ちる理由は解像度ではなく**掃引幅そのもの**(高度 100 m では視野の端でも p = 0.707 のまま切れており W は下限値)。掃引速度 W·v で見ると、v ∝ min(1, h/600) の機体では最適が **420 m** へ動く —— **『高度を下げて W を上げる』は成り立たない**(下げると掃引幅が縮み、機体によっては速度まで落ちる)。★★**見張り役**: 検出率だけ見ていると誤検出が見えない。誤検出は端ではなく**直下に集中**する(0-32 m 帯 **113 件** / 最外 256-288 m 帯 **0 件**)—— 目標も白波も同じ cos^4・同じ大気で暗くなるので、**いちばんよく見える所がいちばん吠える**。同じ画像・同じ検出器で閾値だけ動かすと W は **406 m から 170 m** まで動く(誤検出 22.9 件/枚 → 0.37 件/枚)。**『走査幅 400 m』という報告は、誤検出率が書いていなければ何も言っていない**。★対照群は差 ± σ つきで並べた: 白波 +107.1±5.6、cos^4 +65.5±6.6、軸外ぼけ +48.6±6.2 に対し、**大気 +6.0±5.9 は 1.0σ で「効いている」と言えない**。足し算にもならない。★素材側の穴も 1 つ踏んだ: 点源を画素中心 1 点で標本すると**総フラックスの誤差は 4.6e-07 なのにピーク値が σ=0.9 px で 10.6 % 過大**になり、σ が横距離で変わるので横距離曲線そのものが傾く。**総和が合っていることは、山の高さが合っている証拠にならない** —— erf で画素を厳密積分するよう直した。★★道具の穴を 4 つ見つけ、**うち 1 つはその場で埋めた**: 点状目標の座標を返す 2-D op は `star_detect` だけなのに、「小さい目標 検出」「スポット 検出」「漂流 捜索」では op_find が **0 件**だった。掛けて見ると原因は名前ではなく **op_find 側** —— 語の切り出しが `[a-z0-9]+` の ASCII 限定で和文は語が 1 つも取れず、採点する doc も docstring の **1 行目だけ**(30 文字)。**和文の複数語クエリは構造的に必ず 0 件**になっていた。CJK の連なりを語として取り 2-gram で按分する段を「既存の点が 0 のときだけ」足し、採点対象を docstring 全文へ広げ、star_detect に「名前は天体だが中身は分野中立」と書いた。いまは同じ和文で 1〜2 位に出る(ただし「点 検出」は今も出ない —— 「点」1 文字は輪郭 op の説明にも必ず出るため。限界も隠さない)。*

[![半幅 500 m に一様に撒いた 400000 個。予測 W/2X = 0.2562、モンテカルロの標準偏差 0.0007。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_search_sweep_width/02_sweep_width_equivalence_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_search_sweep_width/02_sweep_width_equivalence.png)

*↑ 測定の図 ―― 半幅 500 m に一様に撒いた 400000 個。予測 W/2X = 0.2562、モンテカルロの標準偏差 0.0007。*

```
py -3.11 examples/poc_search_sweep_width.py
```

ソース: [examples/poc_search_sweep_width.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_search_sweep_width.py)

使用 op(ノートへ): [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`gray_tophat`](https://furuse.work/ops/2d/morphology/gray_tophat.html) · [`integrate_funct_1d`](https://furuse.work/ops/oned/function/integrate_funct_1d.html) · [`laplace`](https://furuse.work/ops/2d/edges/laplace.html) · [`ncc_locate`](https://furuse.work/ops/2d/matching/ncc_locate.html) · [`noise_sigma`](https://furuse.work/ops/astrostack/quality/noise_sigma.html) · [`photon_sample`](https://furuse.work/ops/photon/counting/photon_sample.html) · [`relative_illumination`](https://furuse.work/ops/optics/geometric/relative_illumination.html) · [`star_detect`](https://furuse.work/ops/astrostack/photometry/star_detect.html) · [`tophat`](https://furuse.work/ops/2d/morphology/tophat.html) · [`vignette`](https://furuse.work/ops/gfx2d/post/vignette.html) · [`xsk_blob_log`](https://furuse.work/ops/2d/features/xsk_blob_log.html)

## 67. 座標は「もっともらしい数字」のまま数十メートル間違う ―― 楕円体高・測地成果・平面近似

[![座標は「もっともらしい数字」のまま数十メートル間違う ―― 楕円体高・測地成果・平面近似](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_height_frames/01_geoid_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_height_frames/01_geoid_frames.png)

*↑ **座標は「もっともらしい数字」のまま数十メートル間違う ―― 楕円体高・測地成果・平面近似** ―― GNSS が返すのは**楕円体高 h**、地図と設計図が使うのは**標高 H**。関係は `H = h - N`(N = ジオイド高。日本付近で 30〜40 m)。この取り違えが**どの量に効き、どの量では消えるか**を、合成のジオイド場で真値を植てて測る。★**床を二重に取る**: 既存 op の往復は 3D で 1.07e-06 m。それに加えて**独立実装(反復法)との差**を緯度 7.2e-07 m / 高さ 8.6e-07 m で測った —— **往復だけでは「往きと復りが同じ向きに誤っている」を排除できない**から。★**閉形式の予測が当たったもの**: 傾斜への影響の上限 `atan|∇N|` は予測 0.008771 度 / 実測 0.008600 度(N 一定の対照群は **2.0e-14 度 = 厳密に 0**)、土量 `ΔV = A·N̄` は差 **1.5e-08 m³**、平地の流向が反転する割合は予測 76.1 % / 実測 76.2 %(42787/56169。D8 では 97.2 %)、測地成果の相対誤差 `(a_B-a_W)/a_W` は予測 -116.0 ppm / 実測 -106.1 ppm(1 km 基線で -0.1059 m)。★★**外した予測**: 視通への影響の上限を `|∇N|·d = 2.60 m` と置いたが、実測は **0.052 m(50 分の 1)**。理由は **N の線形部が視線にも地面にも同じだけ乗って消える**こと —— 絞り直した上限 `|N''|d²/8 = 0.144 m` の 36 % に収まった。判定が変わった組は 3/2120(0.14 %)で、**曲率落ち 14.2 m のほうが 276 倍効く**。★★**崖は閉形式で出るが、1 つの数字では出ない**: 局所平面近似の落ち `d²/2R` は 10 km で予測 -7.8481 m。実測は**南北 -7.8652 m / 東西 -7.8303 m** —— 子午線曲率半径 6357143 m と卯酉線 6385412 m の差で、平均半径の予測は**両者のあいだ**に来る(30 km で 0.316 m 開く)。大気屈折(k≈0.13)を入れると崖は `1/√(1-k) = 1.072` 倍だけ遠くへ動く(5 mm を割るのが 252 m → 271 m)。★**この展示の主題**: **同じ 36 m が、量によって全部効いたり全く効かなかったりする**。差を取る量(傾斜 0.0086 度・視通 0.052 m)ではほぼ消え、絶対量では全部効く(土量 **+3.97e+07 m³**、浸水面積 41.9 % → **0.0 %**、逆向きの誤りなら 100 %)。★0 %/100 % は分母 58081 の**構造的な全滅**で、小標本の産物ではないことも明記した。★対照群で「**設計面も同じ GNSS で作る**」と誤差が **0.0 m³** になる —— **汚染された物差しで汚染された対象を測ると、誤差は消えたように見える**。★測地成果(datum)の取り違えは平均 **446.6 m**(281.6〜592.7)ずれるのに、相対検査(基線長の比較)が見せるのは 1 km あたり 0.106 m = **4216 分の 1**。**大きさではなく『もっともらしさ』が問題**で、例外は出ず地図にも載る。★epoch(座標の時刻)も静かに効く: プレート運動 2.5 cm/年 なら Scan-to-BIM の 5 mm を **0.2 年**で、土木の出来形 25 mm を 1.0 年で割る。**成果に epoch を書かないと、古い成果ほど静かにずれ続ける**。★★**静かに間違う / うるさく壊れる を分けて数えた**(標本 3600、全球格子)。**例外が出たのは緯経の入れ替えだけ、それも 1800/3600 = 50.0 %**(`lat_deg must be within [-90,90]` に当たるのは |経度|>90 のときだけ)。ラジアンを度として渡す(8883 km)、経度の符号反転(4800 km)、ECEF の x と y の入れ替え(4849 km、**返った緯度経度が妥当な範囲に収まった点 3600/3600 = 100 %**)、高さがフィート(228 m)は**例外 0 件**。まとめ表 11 項目のうち **静かに間違うものが 10 件**。★★**道具の穴を見つけて、その場で直した**: `dem_ecef_to_geodetic` が地球の中心付近で **緯度 180 度**を返していた —— 緯度として存在せず、しかも**自分の逆関数が拒否する**値。原因は楕円体の**縮閉線の内側では測地緯度が一意でない**ことで、閉形式 `(a·r)^(2/3) + (b·|z|)^(2/3) < (a²-b²)^(2/3)` で判定して fail-closed にした(境界 42697.7 m は実測ともちょうど一致)。★docstring の往復誤差も**中央値を最大値として**書いていたので、標本の範囲つきで測り直した。*

[![分母 58081 セル。真値 24325(41.9 %)に対し、誤用は 0 と 58081。**どちらの絵も「もっともらしい」**(全面浸水は津波の図に見える)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_height_frames/02_flood_masks_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_geodetic_height_frames/02_flood_masks.png)

*↑ 測定の図 ―― 分母 58081 セル。真値 24325(41.9 %)に対し、誤用は 0 と 58081。**どちらの絵も「もっともらしい」**(全面浸水は津波の図に見える)。*

```
py -3.11 examples/poc_geodetic_height_frames.py
```

ソース: [examples/poc_geodetic_height_frames.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_geodetic_height_frames.py)

使用 op(ノートへ): [`dem_aspect`](https://furuse.work/ops/dem/surface/dem_aspect.html) · [`dem_earth_curvature_drop`](https://furuse.work/ops/dem/geodesy/dem_earth_curvature_drop.html) · [`dem_ecef_to_geodetic`](https://furuse.work/ops/dem/geodesy/dem_ecef_to_geodetic.html) · [`dem_flow_direction`](https://furuse.work/ops/dem/hydrology/dem_flow_direction.html) · [`dem_geodetic_to_ecef`](https://furuse.work/ops/dem/geodesy/dem_geodetic_to_ecef.html) · [`dem_slope`](https://furuse.work/ops/dem/surface/dem_slope.html) · [`median`](https://furuse.work/ops/2d/rank/median.html)

### 撮像品質・復元ウィング ―― 絵が良くなることと真値に近づくことは別

手ブレを戻す、拡大する、霞を剥がす、深度合成する、投影から再構成する、光子を数えて距離を出す。復元の分野は「見た目が良くなった」と「真値に近づいた」が最も混ざりやすい場所です。この部屋の 7 点は、核・深度・大気光・PSD・投影・到達時刻をこちらが決めた合成で、その 2 つを分けて採点しています。

見た目の指標は真値を最大値としません。霞んだ入力の対比が真値より高い、アンシャープで勾配は真値に一致するのに PSNR は落ちる、雑音を足すと PSNR が上がる。逆に、ナイキストより細かい縞を戻したのに PSNR が -0.01 dB しか動かない場面もあります。

共通して置いたゼロ点は「何もしない」です。核の角度が 19.4 度ずれた復元、投影 12 本の FBP、視程 782 m 以上の除霞、無テクスチャ領域の深度。いずれもそのゼロ点に負けます。負ける条件を数字で置くことが、この部屋の展示の中身です。

## 68. 手ブレはどこまで戻せるか ―― 核を自分で作り、掛けて、戻して、元と比べる

[![手ブレはどこまで戻せるか ―― 核を自分で作り、掛けて、戻して、元と比べる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/01_noise_ceiling_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/01_noise_ceiling.png)

*↑ **手ブレはどこまで戻せるか ―― 核を自分で作り、掛けて、戻して、元と比べる** ―― 既知の直線ブレ核を掛けて戻し、雑音と核の推定誤差で上限を測った図。無雑音なら 22.38 → 56.41 dB、SNR 20 dB では取り分 1.82 dB。核の角度が 19.4 度ずれると「何もしない」に抜かれ、回転ブレを 1 枚の核で戻すと回転中心が -49.41 dB 悪化する。*

[![4 枚目は「復元した」形をしているが、ゼロ点(観測そのもの)より悪い。絵の見た目では区別できない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/02_deblur_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_shake_deblur/02_deblur.png)

*↑ 測定の図 ―― 4 枚目は「復元した」形をしているが、ゼロ点(観測そのもの)より悪い。絵の見た目では区別できない。*

```
py -3.11 examples/poc_camera_shake_deblur.py
```

ソース: [examples/poc_camera_shake_deblur.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_camera_shake_deblur.py)

使用 op(ノートへ): [`psnr`](https://furuse.work/ops/imgmetrics/fidelity/psnr.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`ssim`](https://furuse.work/ops/imgmetrics/fidelity/ssim.html) · [`unsharp`](https://furuse.work/ops/2d/smoothing/unsharp.html) · [`vol_richardson_lucy`](https://furuse.work/ops/3d/restoration/vol_richardson_lucy.html)

## 69. 超解像は情報を増やすのか ―― 真値を持ったまま縮小して、戻して、数える

[![超解像は情報を増やすのか ―― 真値を持ったまま縮小して、戻して、数える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/03_multiframe_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/03_multiframe.png)

*↑ **超解像は情報を増やすのか ―― 真値を持ったまま縮小して、戻して、数える** ―― 真値を縮小して観測を作り、単一画像拡大・逆投影・drizzle を分解能の列で採点した図。単一画像の拡大は bicubic のゼロ点を最大 +0.036 dB しか上回れない。副画素ずれのある 16 枚の drizzle は標本化不足の条件で +13.96 dB、ナイキスト超えの周期 6 の変調度が 0.03 → 0.38 に立ち上がる。*

[![鮮鋭化だけがナイキスト(周期 8)より細かい列にも縞を作る。それは分解能ではなく**無い縞**。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/01_upscale_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_superresolution_limits/01_upscale.png)

*↑ 測定の図 ―― 鮮鋭化だけがナイキスト(周期 8)より細かい列にも縞を作る。それは分解能ではなく**無い縞**。*

```
py -3.11 examples/poc_superresolution_limits.py
```

ソース: [examples/poc_superresolution_limits.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_superresolution_limits.py)

使用 op(ノートへ): [`drizzle_resample`](https://furuse.work/ops/astrostack/stack/drizzle_resample.html) · [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`psnr`](https://furuse.work/ops/imgmetrics/fidelity/psnr.html) · [`ssim`](https://furuse.work/ops/imgmetrics/fidelity/ssim.html) · [`unsharp`](https://furuse.work/ops/2d/smoothing/unsharp.html) · [`vol_fft_lowpass`](https://furuse.work/ops/3d/frequency/vol_fft_lowpass.html) · [`vol_resize`](https://furuse.work/ops/3d/geom_transform/vol_resize.html) · [`volume_downsample`](https://furuse.work/ops/3d/preprocess/volume_downsample.html)

## 70. 霞を剥がす ―― 大気散乱モデルで真値を作り、透過率と大気光を別々に採点する

[![霞を剥がす ―― 大気散乱モデルで真値を作り、透過率と大気光を別々に採点する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/01_scene.png)

*↑ **霞を剥がす ―― 大気散乱モデルで真値を作り、透過率と大気光を別々に採点する** ―― 深度・大気光・消散係数から真の透過率とシーンを持った霞画像を作り、除霞を採点した図。全体 +4.04 dB の中身は近景 -1.49 dB の劣化を中景 +4.03 / 遠景 +11.28 dB が覆ったもの。視程 782 m 以上では除霞が害になり、雑音を足すと PSNR が上がる(偶然の打ち消し)。*

[![空では過大評価(明るい側)、近景では過小評価(暗い側)。全体の平均バイアスでは打ち消し合って見えない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/02_transmission_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dehazing/02_transmission.png)

*↑ 測定の図 ―― 空では過大評価(明るい側)、近景では過小評価(暗い側)。全体の平均バイアスでは打ち消し合って見えない。*

```
py -3.11 examples/poc_dehazing.py
```

ソース: [examples/poc_dehazing.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dehazing.py)

使用 op(ノートへ): [`clahe`](https://furuse.work/ops/2d/gray/clahe.html) · [`equalize`](https://furuse.work/ops/2d/gray/equalize.html) · [`image_entropy`](https://furuse.work/ops/imgmetrics/information/image_entropy.html) · [`joint_bilateral`](https://furuse.work/ops/3d/depth_denoise/joint_bilateral.html) · [`psnr`](https://furuse.work/ops/imgmetrics/fidelity/psnr.html) · [`rank_image`](https://furuse.work/ops/2d/rank/rank_image.html) · [`ssim`](https://furuse.work/ops/imgmetrics/fidelity/ssim.html)

## 71. 深度合成 ―― 全焦点画像と深度地図は別物

[![深度合成 ―― 全焦点画像と深度地図は別物](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/01_stack_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/01_stack.png)

*↑ **深度合成 ―― 全焦点画像と深度地図は別物** ―― 錯乱円の閉形式で深さに応じたぼけを掛けた 15 枚から、全焦点画像と深度地図を取り出した図。全焦点は 35.89 dB(ゼロ点 20.98 dB)なのに、同じ融合の深度は無テクスチャ領域でゼロ点に 8 倍負ける(0.13 倍)。相対量の信頼度は無テクスチャで 0.9923 と有テクスチャの 0.9630 より高く出る ―― 絶対値(23600 倍差)で棄却すると RMS 1.505 → 0.878 mm。*

[![左下の無テクスチャの四角だけ、誤差が掃引全域にばらけた乱数になっている(段差帯のハローも見える)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/02_depth_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_focus_stacking/02_depth_map.png)

*↑ 測定の図 ―― 左下の無テクスチャの四角だけ、誤差が掃引全域にばらけた乱数になっている(段差帯のハローも見える)。*

```
py -3.11 examples/poc_focus_stacking.py
```

ソース: [examples/poc_focus_stacking.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_focus_stacking.py)

使用 op(ノートへ): [`csi_height_map`](https://furuse.work/ops/interferometry/surface/csi_height_map.html) · [`defocus_blur`](https://furuse.work/ops/optics/scene/defocus_blur.html) · [`dilation_circle`](https://furuse.work/ops/2d/region/dilation_circle.html) · [`fuse`](https://furuse.work/ops/3d/tsdf_fusion/fuse.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`laplace`](https://furuse.work/ops/2d/edges/laplace.html) · [`mean_image`](https://furuse.work/ops/2d/smoothing/mean_image.html) · [`optical_camera`](https://furuse.work/ops/optics/scene/optical_camera.html) · [`psnr`](https://furuse.work/ops/imgmetrics/fidelity/psnr.html) · [`sobel_amp`](https://furuse.work/ops/2d/edges/sobel_amp.html) · [`xcv2_lap_var`](https://furuse.work/ops/2d/features/xcv2_lap_var.html)

## 72. 投影数を減らすと CT 再構成はどこから壊れるか

[![投影数を減らすと CT 再構成はどこから壊れるか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_fidelity/01_recon_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_fidelity/01_recon_sweep.png)

*↑ **投影数を減らすと CT 再構成はどこから壊れるか** ―― Shepp-Logan を 180 → 12 本で撮り直し、FBP を空白画像と無フィルタ逆投影の 2 つの零点と並べた図。12 本の FBP(RMSE 0.2576)は空白画像(0.2420)より悪い。サイノグラムの行和という再構成を見ない検算が、RMSE では見えない質量欠損 -3.34 % を捕まえ、ランプフィルタの DC ビンを直して -0.0099 % に。*

[![RMSE で見ると 12 本は空白画像 0.2420 より悪い。相関とストリークは別のことを言う。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_fidelity/02_fidelity_table_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_fidelity/02_fidelity_table.png)

*↑ 測定の図 ―― RMSE で見ると 12 本は空白画像 0.2420 より悪い。相関とストリークは別のことを言う。*

```
py -3.11 examples/poc_ct_fidelity.py
```

ソース: [examples/poc_ct_fidelity.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_fidelity.py)

使用 op(ノートへ): [`backproject_sinogram`](https://furuse.work/ops/tomography/reconstruct/backproject_sinogram.html) · [`ellipse_phantom`](https://furuse.work/ops/tomography/forward/ellipse_phantom.html) · [`ellipse_sinogram`](https://furuse.work/ops/tomography/forward/ellipse_sinogram.html) · [`filtered_backprojection`](https://furuse.work/ops/tomography/reconstruct/filtered_backprojection.html) · [`projection_angles`](https://furuse.work/ops/tomography/layout/projection_angles.html) · [`radon_transform`](https://furuse.work/ops/tomography/forward/radon_transform.html) · [`rmse`](https://furuse.work/ops/imgmetrics/fidelity/rmse.html) · [`ssim`](https://furuse.work/ops/imgmetrics/fidelity/ssim.html) · [`stat_correlation`](https://furuse.work/ops/math/stats/stat_correlation.html)

## 73. ライトフィールドから深度を出す ―― 既知の深度で作った光場に、ゼロ点を並べて突きつける

[![ライトフィールドから深度を出す ―― 既知の深度で作った光場に、ゼロ点を並べて突きつける](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/01_scene_and_depth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/01_scene_and_depth.png)

*↑ **ライトフィールドから深度を出す ―― 既知の深度で作った光場に、ゼロ点を並べて突きつける** ―― 9×9 の光場を解析的な逆写像で描き、真値スロープ地図に対して焦点度・EPI・2 眼ブロックマッチングを採点した図。定数ゼロ点には 22 倍勝つが、視点 2 枚だけ使う 2 眼に対しては cubic でようやく 1.6 倍。既定の linear 補間は整数スロープに吸着し、真値 1.30 を 1.4750 と読む(深度で 11.9 %)。*

[![linear は 1.08/1.15 を 1.0 へ、1.85 を 2.0 側へ引く。cubic は恒等線に乗る。生成側の補間はゼロ(Fourier シフト)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/02_focus_snapping_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lightfield_depth/02_focus_snapping.png)

*↑ 測定の図 ―― linear は 1.08/1.15 を 1.0 へ、1.85 を 2.0 側へ引く。cubic は恒等線に乗る。生成側の補間はゼロ(Fourier シフト)。*

```
py -3.11 examples/poc_lightfield_depth.py
```

ソース: [examples/poc_lightfield_depth.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_lightfield_depth.py)

使用 op(ノートへ): [`lf_depth_from_focus`](https://furuse.work/ops/lightfield/depth/lf_depth_from_focus.html) · [`lf_disparity_to_depth`](https://furuse.work/ops/lightfield/depth/lf_disparity_to_depth.html) · [`lf_epi`](https://furuse.work/ops/lightfield/views/lf_epi.html) · [`lf_epi_slope`](https://furuse.work/ops/lightfield/depth/lf_epi_slope.html) · [`lf_refocus`](https://furuse.work/ops/lightfield/refocus/lf_refocus.html)

## 74. 光子を数えて距離を測る ―― 何個数えれば何ミリまで出るのか

[![光子を数えて距離を測る ―― 何個数えれば何ミリまで出るのか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/01_histograms_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/01_histograms.png)

*↑ **光子を数えて距離を測る ―― 何個数えれば何ミリまで出るのか** ―― 往復時刻にガウシアンをビン積分で置き Poisson 標本を引いた到達時刻ヒストグラムから距離を読む図。N = 200 光子でピーク位置そのまま 11.02 mm、ゲート重心 2.29 mm、理論限界 31.83 mm/√N に 1.00〜1.07 倍で乗る。背景が入ると素の重心は 2 桁崩れ(SBR 0.031 で 564 mm)、族が推すガウス当てはめ 8.82 mm は利用者が 6 行で書くゲート重心に負ける。*

[![背景が無ければ素の重心で足りる。背景が入ると 2 桁崩れ、docstring が勧める背景減算でも戻らない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/02_methods_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dtof_ranging/02_methods.png)

*↑ 測定の図 ―― 背景が無ければ素の重心で足りる。背景が入ると 2 桁崩れ、docstring が勧める背景減算でも戻らない。*

```
py -3.11 examples/poc_dtof_ranging.py
```

ソース: [examples/poc_dtof_ranging.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dtof_ranging.py)

使用 op(ノートへ): [`dtof_cube_depth`](https://furuse.work/ops/photon/dtof/dtof_cube_depth.html) · [`dtof_cube_simulate`](https://furuse.work/ops/photon/dtof/dtof_cube_simulate.html) · [`dtof_depth`](https://furuse.work/ops/photon/dtof/dtof_depth.html) · [`gaussian`](https://furuse.work/ops/2d/smoothing/gaussian.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`tcspc_background_subtract`](https://furuse.work/ops/photon/tcspc/tcspc_background_subtract.html) · [`tcspc_coates_correct`](https://furuse.work/ops/photon/spad/tcspc_coates_correct.html) · [`tcspc_simulate`](https://furuse.work/ops/photon/tcspc/tcspc_simulate.html)

## 75. 疑似カラーは読み手の判断を変える —— 無い境目を数え、位置を先に当てる

[![疑似カラーは読み手の判断を変える —— 無い境目を数え、位置を先に当てる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colormap_readability/05_scene_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colormap_readability/05_scene_maps.png)

*↑ **疑似カラーは読み手の判断を変える —— 無い境目を数え、位置を先に当てる** ―― 段差がゼロと分かっているなめらかな場を塗り、CIE L* と CIEDE2000 で「無い境目」を数えた。jet は 3 本・hsv は 4 本立ち、viridis と gray は 0 本。★立つ位置は sRGB の伝達関数と CIE の Y 係数から解けて、jet の明度折返し予測 0.3750 / 0.4490 / 0.6250 に対し実測 0.3750 / 0.4492 / 0.6250(最大ずれ 0.0002)。本物の段差が偽の境目を追い越すのは jet で 0.296 %FS・viridis で 0.050 %FS(配色の LUT だけからの予測と一致)——jet を選ぶと段差に 5.9 倍の高さが要る。配色より効くのは写し方で、4.3 桁の 1/r² 場では区別できる階調の実効数が linear 1.4 → rank 76.0。★★外れ値を 1 個混ぜると log が 27.4 → 16.3(-41 %)落ち、percentile と rank だけが不変。*

[![平らなら偽の境目は立たない。jet と hsv の山がそのまま『見えてしまう帯』になる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colormap_readability/01_gain_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_colormap_readability/01_gain_profile.png)

*↑ 測定の図 ―― 平らなら偽の境目は立たない。jet と hsv の山がそのまま『見えてしまう帯』になる。*

```
py -3.11 examples/poc_colormap_readability.py
```

ソース: [examples/poc_colormap_readability.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_colormap_readability.py)

使用 op(ノートへ): [`delta_e_map`](https://furuse.work/ops/imgmetrics/colordiff/delta_e_map.html) · [`percentile`](https://furuse.work/ops/2d/rank/percentile.html) · [`rgb_to_lab`](https://furuse.work/ops/imgmetrics/colorspace/rgb_to_lab.html)

## 76. 実写のブレを取る ―― 3 つの物差しに、3 人の勝者

[![実写のブレを取る ―― 3 つの物差しに、3 人の勝者](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_deblur_honesty/01_restore_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_deblur_honesty/01_restore.png)

*↑ **実写のブレを取る ―― 3 つの物差しに、3 人の勝者** ―― 真値を実写そのもの(scikit-image camera、CC0)にして、劣化だけ自分で作る(直線ブレ 11 px・20 度 + 雑音 σ=0.004)。★ゼロ点(何もしない)が 24.04 dB と強く、よく使われる nsr=0.005 の Wiener は 23.66 dB で**負ける**。★★ただしそこで止めると相手を弱く見せたことになる ―― nsr を振ると 0.0005 で 19.18 dB、0.02 で 25.40 dB。**ノブを固定した比較は比較ではない**。★★しかもノブで動く幅 6.22 dB は、脱畳み込みをするかしないかの差 1.36 dB の **4.6 倍** ―― 手法よりノブが効く。★★同じ 7 通りの結果に 3 つの物差しを当てると、**別々の手法が 1 位**になる: PSNR は正しい PSF の Wiener(25.40 dB)、勾配エネルギーは motion_deblur(0.2986 = 真値 0.1936 の 1.54 倍、**真値より鋭い絵が選ばれる**)、blur_effect は unsharp。参照なし指標が選ぶ手法は PSNR で **4.98 dB / 3.26 dB 損**をする(なお blur_effect は真値そのものは正しく最良と判定する ―― 「ぼけているか」は測れていて、それでも選ばせると損をする)。★長さを 11→21 px と間違えた PSF は 18.56 dB(ゼロ点より -5.48 dB)なのに勾配は真値の 1.37 倍で「よく効いた」ように見える。★崖: 雑音 σ=0.016 で利得は +0.05 dB(1.6 % の雑音で脱畳み込みは何も買わない)、ブレ長の利得は L=5 が山で両端で落ちる(小さいブレは取るものが無く、大きいブレは情報が消えている)。*

[![固定した nsr で比べると、正しい PSF でもゼロ点に負ける。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_deblur_honesty/02_nsr_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_deblur_honesty/02_nsr.png)

*↑ 測定の図 ―― 固定した nsr で比べると、正しい PSF でもゼロ点に負ける。*

```
py -3.11 examples/poc_real_deblur_honesty.py
```

ソース: [examples/poc_real_deblur_honesty.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_deblur_honesty.py)

使用 op(ノートへ): [`iv_motion_deblur`](https://furuse.work/ops/2d/restoration/iv_motion_deblur.html) · [`iv_richardson_lucy`](https://furuse.work/ops/2d/restoration/iv_richardson_lucy.html) · [`iv_unsharp_deblur`](https://furuse.work/ops/2d/restoration/iv_unsharp_deblur.html) · [`psnr`](https://furuse.work/ops/imgmetrics/fidelity/psnr.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`sk_blur_effect`](https://furuse.work/ops/2d/features/sk_blur_effect.html) · [`unsharp`](https://furuse.work/ops/2d/smoothing/unsharp.html)

### 時系列を 3-D として測るウィング ―― 動画は 1 つの体積

2-D の動画を (t, y, x) の 1 つの体積とみなすと、3-D の op ―― 連結成分、等値面、領域特徴 ―― がそのまま時間方向に効きます。合体したコロニーは時空間で Y 字になり、通過する車は (t, x) 画像の帯になり、波面の到達時刻は等値面になります。この部屋の 6 点はその実演です。

同時に、時間方向ならではの罠も出ました。フレーム格子への丸めは必ず遅らせ、画素の面積は合体を早める。誤リンクには向きの逆な 2 種類があり、誤り率 1 本では拡散係数がどちらへ外れるか決まらない。テンプレート追跡は見失うより先に静かにずれ、ずれた 152 フレーム全部が「見つけた」と報告する。

モーション拡大の展示は、この部屋でいちばん正直な結論を持っています。拡大率 200 まで機械精度で厳密に動くのに、測定の役には立たない ―― 拡大は人間に見せるための道具です。

## 77. 成長のタイムラプスを時空間の連結成分として測る

[![成長のタイムラプスを時空間の連結成分として測る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/01_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/01_frames.png)

*↑ **成長のタイムラプスを時空間の連結成分として測る** ―― 広がって合体するコロニーの動画を (t, y, x) の体積として 3-D 連結成分で読んだ図。画素が面積を持つせいで合体は早く見え(組 0-1 で -1.16 フレーム)、フレーム格子への丸めは遅らせる(+0.94) ―― 逆向きなので合計は小さく見える。`vol_label` の既定 26 近傍は、隙間 0.92 のニアミスを合体させた。*

[![縦が時間(下向き、4 倍に拡大)、横が列。2 本の管が合わさる高さがそのまま合体時刻。色は 3-D ラベル。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/02_ystructure_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_timelapse_growth/02_ystructure.png)

*↑ 測定の図 ―― 縦が時間(下向き、4 倍に拡大)、横が列。2 本の管が合わさる高さがそのまま合体時刻。色は 3-D ラベル。*

```
py -3.11 examples/poc_timelapse_growth.py
```

ソース: [examples/poc_timelapse_growth.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_timelapse_growth.py)

使用 op(ノートへ): [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_region_props`](https://furuse.work/ops/3d/regionprops/vol_region_props.html)

## 78. (x, y, t) で数える ―― 通過台数とオクルージョン、そして L/V という 1 つの定数

[![(x, y, t) で数える ―― 通過台数とオクルージョン、そして L/V という 1 つの定数](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/01_per_frame_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/01_per_frame.png)

*↑ **(x, y, t) で数える ―― 通過台数とオクルージョン、そして L/V という 1 つの定数** ―― 車を流した合成動画で、フレームごとの計数・仮想ループ・(t, x) スリット画像の連結成分を並べた図。フレームごとの最大値は通過 10 台に対し 7 ―― 別の量を測っている。破綻の条件は 3 つとも車長 ÷ 速度 = L/V(9.0 フレーム)で書け、フレーム間隔 16 では帯が千切れて 10 → 49 台。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/02_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_traffic_counting/02_scene.png)

*↑ 測定の図*

```
py -3.11 examples/poc_traffic_counting.py
```

ソース: [examples/poc_traffic_counting.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_traffic_counting.py)

使用 op(ノートへ): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html)

## 79. 到達時刻面を (x, y, t) の等値面として取り出す

[![到達時刻面を (x, y, t) の等値面として取り出す](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/01_dt_sweep_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/01_dt_sweep.png)

*↑ **到達時刻面を (x, y, t) の等値面として取り出す** ―― 点源から広がる波面の到達時刻面を (x, y, t) 体積の等値面として取り出した図。ゼロ点(初めて超えたフレーム番号)の偏りは Δt/2 で枚数では消えず、線形補間で 27 倍(0.0209 ms)。放物線補間は線形に負け、しきい値がガウス波形の変曲点 θ = 0.6065 にあるとき線形が最良(3.8 倍差)。*

[![変曲点 θ=0.6065 では線形が 3.8 倍勝ち、θ=0.2 では放物線が 3.6 倍勝つ。交点は θ≈0.35 と θ≈0.75。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/02_threshold_crossover_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_xyt_event_surface/02_threshold_crossover.png)

*↑ 測定の図 ―― 変曲点 θ=0.6065 では線形が 3.8 倍勝ち、θ=0.2 では放物線が 3.6 倍勝つ。交点は θ≈0.35 と θ≈0.75。*

```
py -3.11 examples/poc_xyt_event_surface.py
```

ソース: [examples/poc_xyt_event_surface.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_xyt_event_surface.py)

使用 op(ノートへ): [`vertex_normals`](https://furuse.work/ops/3d/mesh_process/vertex_normals.html) · [`vol_edge_probe`](https://furuse.work/ops/3d/probe/vol_edge_probe.html)

## 80. 粒子追跡を (行, 列, 時刻) の体積として測る ―― 誤リンクの向きは 1 種類ではない

[![粒子追跡を (行, 列, 時刻) の体積として測る ―― 誤リンクの向きは 1 種類ではない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/01_spacetime_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/01_spacetime.png)

*↑ **粒子追跡を (行, 列, 時刻) の体積として測る ―― 誤リンクの向きは 1 種類ではない** ―― 400 個の粒子の動画を追跡し、軌跡から拡散係数 D を読んだ図。曖昧な誤リンクは D を 0.925 倍に下げ、欠測による誤リンクは同じ動画で 3.429 倍に上げる ―― 誤り率 1 本では向きが決まらない。効くのは 1 対 1 制約ではなく、上限距離のゲート 1 行(3.429 → 1.304)。*

[![縦軸は常用対数(0 が真値)。欠測は遠い他人を掴んで D を上げ、曖昧は近い相手を選んで D を下げる。上限距離のゲート 1 行で上向きの暴走が 1/2.6 に。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/02_density_bias_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_particle_tracking/02_density_bias.png)

*↑ 測定の図 ―― 縦軸は常用対数(0 が真値)。欠測は遠い他人を掴んで D を上げ、曖昧は近い相手を選んで D を下げる。上限距離のゲート 1 行で上向きの暴走が 1/2.6 に。*

```
py -3.11 examples/poc_particle_tracking.py
```

ソース: [examples/poc_particle_tracking.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_particle_tracking.py)

使用 op(ノートへ): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_local_maxima`](https://furuse.work/ops/3d/feature/vol_local_maxima.html)

## 81. テンプレート追跡は「見失う」より先に「静かにずれる」

[![テンプレート追跡は「見失う」より先に「静かにずれる」](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/01_ncc_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/01_ncc_maps.png)

*↑ **テンプレート追跡は「見失う」より先に「静かにずれる」** ―― 既知の相似変換でカメラを動かし、テンプレート追跡が「見失う」「静かにずれる」「自信満々で間違える」の 3 通りで壊れるのを見た図。ずれていた 152 フレームの 152 フレーム全部が、遮蔽なしで校正したピークのしきい値を通って「見つけた」と報告した。真値なしで測れる絶対量は往復追跡の不一致だけ。*

[![同じ遮蔽率でも、そっくりな別物体が視野に居るだけで崖がはるかに手前へ来る。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/02_occlusion_vs_twin_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_template_tracking/02_occlusion_vs_twin.png)

*↑ 測定の図 ―― 同じ遮蔽率でも、そっくりな別物体が視野に居るだけで崖がはるかに手前へ来る。*

```
py -3.11 examples/poc_template_tracking.py
```

ソース: [examples/poc_template_tracking.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_template_tracking.py)

使用 op(ノートへ): [`ncc_locate`](https://furuse.work/ops/2d/matching/ncc_locate.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`shape_locate`](https://furuse.work/ops/2d/matching/shape_locate.html)

## 82. 構造物の微小振動を映像から測る ―― モーション拡大は「測る」役に立つのか

[![構造物の微小振動を映像から測る ―― モーション拡大は「測る」役に立つのか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/01_slit_scan_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/01_slit_scan.png)

*↑ **構造物の微小振動を映像から測る ―― モーション拡大は「測る」役に立つのか** ―― 既知振幅 0.02 px・3.7 Hz の振動を合成し、モーション拡大が測定に効くかを見た図。拡大率 α = 200 まで機械精度で厳密。だが拡大は測定精度を良くしない ―― 位相を α 倍すると雑音も α 倍。片持ち梁では位相相関が 0.30 と 0.00 px の面積平均 0.15 px という、どこにも存在しない数を返す。*

[![剛体を仮定する位相相関が返す 0.150 px は 0.30 と 0.00 の面積平均で、どの列の真値とも違う。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/02_beam_profile_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_motion_magnification/02_beam_profile.png)

*↑ 測定の図 ―― 剛体を仮定する位相相関が返す 0.150 px は 0.30 と 0.00 の面積平均で、どの列の真値とも違う。*

```
py -3.11 examples/poc_motion_magnification.py
```

ソース: [examples/poc_motion_magnification.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_motion_magnification.py)

使用 op(ノートへ): [`band_snr`](https://furuse.work/ops/motionmag/temporal/band_snr.html) · [`displacement_series`](https://furuse.work/ops/motionmag/measure/displacement_series.html) · [`motion_magnify`](https://furuse.work/ops/motionmag/magnify/motion_magnify.html) · [`phase_displacement`](https://furuse.work/ops/motionmag/measure/phase_displacement.html) · [`synthesize_translation`](https://furuse.work/ops/motionmag/synthesis/synthesize_translation.html) · [`temporal_band_power`](https://furuse.work/ops/motionmag/temporal/temporal_band_power.html) · [`temporal_bandpass`](https://furuse.work/ops/motionmag/temporal/temporal_bandpass.html)

## 83. 動画から固有振動数・減衰比・モード形状を同定する ―― f は最後まで生き残り、ζ が先に嘘をつく

[![動画から固有振動数・減衰比・モード形状を同定する ―― f は最後まで生き残り、ζ が先に嘘をつく](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/01_scene.png)

*↑ **動画から固有振動数・減衰比・モード形状を同定する ―― f は最後まで生き残り、ζ が先に嘘をつく** ―― 片持ち梁(Euler–Bernoulli 閉形式)の 3 モード自由減衰を、雑音・照明ちらつき 100 Hz・手ぶれ・ローリングシャッター入りの動画に合成し、位相法(phase_displacement)と PIV(piv_cross_correlate)で f_n / ζ_n / MAC を測る。f_n は 3 モードとも 0.06 Hz 以内で当たるが、同じ時系列から出した ζ_1 は半値幅 0.0778 / 包絡線 0.0188 / 当てはめ 0.0181(真値 0.02)と方法で 3 通り。振幅を 0.02→2 px で掃引すると壊れる順番は f → ζ → MAC_2 → MAC_3 で、位相法は 0.02 px で f_1 誤差 +0.030 Hz のまま ζ_1 が真値の 0.23 倍になる。fps 48.5 では照明の折り返しがちょうど 3.00 Hz = f_1 に乗り、輝度のゼロ点は ζ を出せず位相法は 0.0191 で生き残る。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/02_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_beam_modal_video/02_frames.png)

*↑ 測定の図*

```
py -3.11 examples/poc_beam_modal_video.py
```

ソース: [examples/poc_beam_modal_video.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_beam_modal_video.py)

使用 op(ノートへ): [`envelope`](https://furuse.work/ops/oned/signal/envelope.html) · [`phase_displacement`](https://furuse.work/ops/motionmag/measure/phase_displacement.html) · [`piv_cross_correlate`](https://furuse.work/ops/piv/estimate/piv_cross_correlate.html) · [`temporal_bandpass`](https://furuse.work/ops/motionmag/temporal/temporal_bandpass.html)

## 84. 庫内の滞留はどこで生まれたか ―― 待ちの種類を分けずに数えると全部「混雑」になる

[![庫内の滞留はどこで生まれたか ―― 待ちの種類を分けずに数えると全部「混雑」になる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/09_scene_layout_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/09_scene_layout.png)

*↑ **庫内の滞留はどこで生まれたか ―― 待ちの種類を分けずに数えると全部「混雑」になる** ―― 物流センターの平面図と 26 台の軌跡を合成し、補充待ち・人待ち・通路の干渉・システム待ち・欠品を既知の時刻と長さで仕込んで、動画を (t, y, x) の 1 つの体積として読んだ図。ゼロ点の「総滞留時間」321.5 秒のうち真の待ちは 198.0 秒(61.6 %)で、残りは生産的な作業と徐行。人待ちを全部止めても通路の干渉を全部止めてもゼロ点は -39.0 / -38.0 秒しか違わず原因が決まらないが、種類別なら該当の型だけが 0 に落ちる。欠品は滞留を -17.0 秒しか動かさないのに余計な移動を 94.6 m 生み、崖は 3 軸で別々の型を殺す ―― 標本間隔は短い待ち、遮蔽は棚に張りつく型、ID の併合は 2 人の関係を読む型。*

[![ヒートマップは場所を当てるが、「1 人が長く待った」と「何人も短く止まった」を分けない。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/01_heat_ambiguity_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_warehouse_flow/01_heat_ambiguity.png)

*↑ 測定の図 ―― ヒートマップは場所を当てるが、「1 人が長く待った」と「何人も短く止まった」を分けない。*

```
py -3.11 examples/poc_warehouse_flow.py
```

ソース: [examples/poc_warehouse_flow.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_warehouse_flow.py)

使用 op(ノートへ): [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`face_areas`](https://furuse.work/ops/3d/mesh_process/face_areas.html) · [`mesh_volume`](https://furuse.work/ops/3d/mesh_process/mesh_volume.html) · [`occupancy_grid`](https://furuse.work/ops/3d/occupancy/occupancy_grid.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`vol_dilate`](https://furuse.work/ops/2d/3d/vol_dilate.html) · [`vol_erode`](https://furuse.work/ops/2d/3d/vol_erode.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_opening_ball`](https://furuse.work/ops/2d/3d/vol_opening_ball.html) · [`vol_region_props`](https://furuse.work/ops/3d/regionprops/vol_region_props.html)

## 85. 冷蔵輸送の温度記録 ―― ロガーを置いた場所が合否を決めている

[![冷蔵輸送の温度記録 ―― ロガーを置いた場所が合否を決めている](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cold_chain_excursion/01_scene_slices_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cold_chain_excursion/01_scene_slices.png)

*↑ **冷蔵輸送の温度記録 ―― ロガーを置いた場所が合否を決めている** ―― 12.0 m x 2.4 m のリーファー荷室の 12 時間を (t, y, x) の 1 つの体積(720 分 x 60 x 12 セル)として組み立て、吹き出し口からの距離・4 枚の壁からの侵入・扉開閉 5 回のパルス・荷の 1 次遅れ(空気 5 分 / 製品 64〜91 分)を既知の閉形式で仕込んだ図。真に不合格な製品セルは 108 / 490(22.0 %)なのに、製品にロガーを 1 個貼ると 82.4 % の置き方が「合格」と言う。要因を 1 つずつ止めると壊れ方が分かれる ―― 壁だけなら偽合格 95.5 %・偽不合格 0.0 %、壁を止めて扉だけ残すと偽不合格が 3.5 % 現れ、しかも製品に貼ったロガーは 100 % 合格と言う(短いパルスは製品に入らない)。崖は紙の上で予測できて、時定数の崖は「空気 + ロガー」の 2 段モデルで実測 19〜138 分に対し相対 18 % 以内、サンプリング間隔と 0.5 K 量子化の崖は予測と完全一致。同じ記録から出した 3 指標は「12 °C に許す時間」に直すと 60 / 276 / 197 分と 4.6 倍ずれ、720 セル中 82 セル(11.4 %)で合否が揃わない。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cold_chain_excursion/02_layout_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cold_chain_excursion/02_layout_maps.png)

*↑ 測定の図*

```
py -3.11 examples/poc_cold_chain_excursion.py
```

ソース: [examples/poc_cold_chain_excursion.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_cold_chain_excursion.py)

使用 op(ノートへ): [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`integrate_funct_1d`](https://furuse.work/ops/oned/function/integrate_funct_1d.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`sample_funct_1d`](https://furuse.work/ops/oned/function/sample_funct_1d.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_label_shape_stats`](https://furuse.work/ops/volcolor/measure/vol_label_shape_stats.html) · [`vol_mip`](https://furuse.work/ops/2d/3d/vol_mip.html) · [`vol_profile_line`](https://furuse.work/ops/3d/probe/vol_profile_line.html) · [`vol_region_props`](https://furuse.work/ops/3d/regionprops/vol_region_props.html)

## 86. ひび割れの「幅」ではなく「伸び」を測る ―― 同じ壁を撮り返すと誤差の性質が変わる

[![ひび割れの「幅」ではなく「伸び」を測る ―― 同じ壁を撮り返すと誤差の性質が変わる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/01_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/01_frames.png)

*↑ **ひび割れの「幅」ではなく「伸び」を測る ―― 同じ壁を撮り返すと誤差の性質が変わる** ―― 1 px = 0.15 mm の壁を 3 年 12 期にわたり撮り返し、ひび割れの成長率 0.040 mm/年 を測る。2 値化して画素を数えるやり方は幅を 25.0 % 過小に言いながら成長率は +153.0 % 過大に言い、幅を凍結した対照群でも +0.0117 mm/年 の「成長」を出す(犯人はぼけ。要因を 1 つずつ止めて分けた)。輝度欠損を積分するやり方は成長率 +3.1 %、対照群では +0.0005 mm/年。★2 値化の成長率は初期の幅だけで 0.0241〜0.1038 mm/年 と動く ―― 1 画素の段差が観測窓に来たかどうかで決まる。*

[![2 値化は幅の偏りより**期ごとの跳ね**が問題。跳ねの正体はぼけと画素位相で、4 節と 3 節で分けて数える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/02_timeseries_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crack_width_timeseries/02_timeseries.png)

*↑ 測定の図 ―― 2 値化は幅の偏りより**期ごとの跳ね**が問題。跳ねの正体はぼけと画素位相で、4 節と 3 節で分けて数える。*

```
py -3.11 examples/poc_crack_width_timeseries.py
```

ソース: [examples/poc_crack_width_timeseries.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_crack_width_timeseries.py)



## 87. 沈下したのか、測り直しただけなのか ―― 検出限界で切ると景色が変わる

[![沈下したのか、測り直しただけなのか ―― 検出限界で切ると景色が変わる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_settlement_significance/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_settlement_significance/01_scene.png)

*↑ **沈下したのか、測り直しただけなのか ―― 検出限界で切ると景色が変わる** ―― トンネル掘進で沈んだ 24 x 16 m の路面を 2 時期の点群で測る。ゼロ点の最近傍距離(C2C)は変化ゼロでも中央値 47.74 mm を返し(正体は点間隔)、符号も持たない。M3C2 の平均は -2.43 mm で真値と一致するが、LoD を超えて有意なのは 275/551 core(49.9 %)でその平均は -4.34 mm ―― 1 行の平均はどちらとも一致しない。LoD は沈下ではなく面の地図で、ゾーンごとに 0.51〜3.58 mm。有意なものだけ足すと体積は 0.8569 → 0.7643 m3 に痩せ、その欠け量は core ごとの LoD から先に計算できる(予測 0.867 / 実測 0.892)。*

[![有意の地図は真値の地図をよく復元する(TPR 88.7 % / FPR 3.6 %)。ただし縁が痩せる —— そこが 7 節の体積の話。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_settlement_significance/02_map_change_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_settlement_significance/02_map_change.png)

*↑ 測定の図 ―― 有意の地図は真値の地図をよく復元する(TPR 88.7 % / FPR 3.6 %)。ただし縁が痩せる —— そこが 7 節の体積の話。*

```
py -3.11 examples/poc_settlement_significance.py
```

ソース: [examples/poc_settlement_significance.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_settlement_significance.py)



### 幾何・校正ウィング ―― 残差が小さいことは正しさの証明にならない

カメラ校正の再投影誤差、パノラマの継ぎ目、点群位置合わせの残差。どれも「小さいほど良い」と読まれる数字ですが、この部屋の 3 点はその読み方が成り立たない場面を、真値を握った上で並べています。

再投影誤差 0.0688〜0.0690 px で焦点距離の誤差が 0.026〜7.334 %。隣の継ぎ目が 0.12 px なのに閉じる 1 本だけ 1.5 px。球や円柱では残差が同じまま姿勢が任意。最小二乗は残差を雑音まで落とすのが仕事で、落ちた先が真値かどうかは別の話です。

測り方そのものの罠も残してあります。点群を 1 組固定して姿勢だけ振っても標本は 1 つしか無く、乱数の種だけで「象限誤り 0 %」と「100 %」の両方が出ました。真値なしで測れる絶対量は、一周する撮り方の閉ループ誤差くらいしかありません。

## 88. 再投影誤差 0.05 px は何も保証しない

[![再投影誤差 0.05 px は何も保証しない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/03_frame_fill_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/03_frame_fill.png)

*↑ **再投影誤差 0.05 px は何も保証しない** ―― 既知の内部パラメータと姿勢で格子点を投影し、校正し直して成分ごとに誤差を出した図。板の傾き 32 / 8 / 2 度で再投影 RMS は 0.0688〜0.0690 px(比 1.00)なのに、fx の誤差は 0.026〜7.334 %(281 倍)。歪みのあるカメラでは退化検出の門が発火せず、非線形最適化は正面配置でも答えを返す。*

[![RMS は 1.00 倍しか動かないのに fx 誤差は 281 倍動く。配置の良し悪しを映すのは sigma_fx のほう。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/01_reproj_vs_truth_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_camera_calibration/01_reproj_vs_truth.png)

*↑ 測定の図 ―― RMS は 1.00 倍しか動かないのに fx 誤差は 281 倍動く。配置の良し悪しを映すのは sigma_fx のほう。*

```
py -3.11 examples/poc_camera_calibration.py
```

ソース: [examples/poc_camera_calibration.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_camera_calibration.py)

使用 op(ノートへ): [`project_points`](https://furuse.work/ops/3d/render/project_points.html) · [`reprojection_error`](https://furuse.work/ops/3d/pose_estimation/reprojection_error.html)

## 89. 隣どうしを鎖でつなぐと、一周して元に戻れない

[![隣どうしを鎖でつなぐと、一周して元に戻れない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/01_seams_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/01_seams.png)

*↑ **隣どうしを鎖でつなぐと、一周して元に戻れない** ―― 既知の回転列で円筒パノラマから 36 枚を切り出し、隣接ペアの鎖で一周させた図。隣の継ぎ目は 0.12 px なのに閉じる 1 本だけ 1.5 px(13 倍)開く。埋もれていた `bundle_adjust_mosaic` は鎖を上回らず(30/36 枚が単位行列のまま)、姿勢の最悪誤差は鎖 1.65 → 大域最適化 0.56 px。*

[![系 2(等分)は閉ループ誤差を下げるのに姿勢はかえって悪化する。新しい観測を足さずに効くのは系 3。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/02_pose_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_panorama_drift/02_pose_error.png)

*↑ 測定の図 ―― 系 2(等分)は閉ループ誤差を下げるのに姿勢はかえって悪化する。新しい観測を足さずに効くのは系 3。*

```
py -3.11 examples/poc_panorama_drift.py
```

ソース: [examples/poc_panorama_drift.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_panorama_drift.py)

使用 op(ノートへ): [`pose_error`](https://furuse.work/ops/3d/metrics/pose_error.html) · [`warp_by_plane`](https://furuse.work/ops/3d/plane_sweep_stereo/warp_by_plane.html)

## 90. 点群位置合わせの収束域 ―― 初期姿勢がどれだけずれたら壊れるか

[![点群位置合わせの収束域 ―― 初期姿勢がどれだけずれたら壊れるか](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/01_basin_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/01_basin.png)

*↑ **点群位置合わせの収束域 ―― 初期姿勢がどれだけずれたら壊れるか** ―― 点群を毎試行取り直し、初期姿勢のずれに対する ICP の成功率を等高線にした図。並進ずれ 0 で成功率が 50 % を切るのは点対点 90 度、点対面 120 度。球や円柱は残差が同じまま姿勢が任意で、大域手法では 16/16 が見かけ上収束しつつ姿勢は誤り ―― 残差では検出できない。*

[![非対称性が消えると 4 候補が形として区別できず、選択が崩れる(選ばれた解が第 1 候補から離れる)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/02_pca_quadrant_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_registration_basin/02_pca_quadrant.png)

*↑ 測定の図 ―― 非対称性が消えると 4 候補が形として区別できず、選択が崩れる(選ばれた解が第 1 候補から離れる)。*

```
py -3.11 examples/poc_registration_basin.py
```

ソース: [examples/poc_registration_basin.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_registration_basin.py)

使用 op(ノートへ): [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`farthest_point_sampling`](https://furuse.work/ops/3d/geodesic/farthest_point_sampling.html) · [`rmse`](https://furuse.work/ops/imgmetrics/fidelity/rmse.html)

## 91. 実写のステレオ写真で測る ―― 合成では出ない 3 つの躓き

[![実写のステレオ写真で測る ―― 合成では出ない 3 つの躓き](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stereo_depth/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stereo_depth/01_scene.png)

*↑ **実写のステレオ写真で測る ―― 合成では出ない 3 つの躓き** ―― この博物館で初めて**実写**を通した 1 本(Middlebury 2014 motorcycle、真値視差つき)。★配布元の注記は真値の穴を NaN と書いているが実際は +inf で、np.nanmedian は中央視差を 42.55 px でなく 44.97 px と答える(isfinite で判定している fill_disparity と apply_cmap は正しく穴として扱った)。★既定 max_disp=16 は bad2 95.06 % ―― 真の最大視差 59.91 px を下回る設定は前景を丸ごと失うので、崖は 48 と 64 の間に立つ(幾何から先に言える)。ゼロ点 94.04 % に対し SGM 15.81 %、信頼度で下位 4 割を捨てると 6.80 %。★★距離に落とすところで形が反り返る: depth_from_disparity に主点オフセット doffs が無く、実写の校正値 31.086 px を無視すると距離が 1.519〜5.243 倍にばらけ、最良の単一スケール 0.3733 を掛けてなお残差 958.3 mm RMS(奥行きレンジ 2889 mm の 33.2 %)、遠い面は +1676 mm 押し出され近い面は -926 mm 引き込まれる。この PoC で doffs を引数に足した(閉形式と最大差 0 mm)。★census は実装が弱いのではなく 64 bit パックで窓が 7 で頭打ち(3/5/7 で 75.27/48.62/35.44 % と伸びている途中)。*

[![下位 4 割を捨てると bad2 は 26.75 % -> 6.80 %。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stereo_depth/02_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stereo_depth/02_error.png)

*↑ 測定の図 ―― 下位 4 割を捨てると bad2 は 26.75 % -> 6.80 %。*

```
py -3.11 examples/poc_real_stereo_depth.py
```

ソース: [examples/poc_real_stereo_depth.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_stereo_depth.py)



## 92. 「回転しても同じ」と言える量はどれか —— 実写の硬貨を 72 角度で回して数える

[![「回転しても同じ」と言える量はどれか —— 実写の硬貨を 72 角度で回して数える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rotation_invariance_audit/01_rotation_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rotation_invariance_audit/01_rotation_frames.png)

*↑ **「回転しても同じ」と言える量はどれか —— 実写の硬貨を 72 角度で回して数える** ―― 形の特徴量は当たり前のように「回転不変」と呼ばれる。だが**画素の格子は回転で不変ではない**ので、その主張はたいてい下請け(境界の数え方・補間・しきい値)の任意性のところで壊れる。scikit-image 同梱の実写 `coins`(大英博物館、ポンペイ出土のギリシャ硬貨)を 5 度ずつ 1 周させ、揺れを**3 本の腕**に分けて犯人を特定する: **A** 灰を線形補間して回してから二値化(人が実際にやること)/ **B** 0 度の二値マスクを最近傍で回す(境界の再ラスタライズだけ)/ **C** 90 度の倍数だけを `np.rot90` で回す(補間も再ラスタライズも無い)。回す道具は fullseye ではなく scipy —— 自分の回転で自分の不変性を測ると、両方同じ向きに間違っても気づけない。★**腕 C は 7 量すべてきっかり 0.00 %**。測り方そのものに向き依存は無く、揺れは全部「格子に置き直す代償」。★★**予測が外れた**: 書いた時点では「灰を補間して二値化し直すほうが荒れる」と思っていたが、**逆**だった —— 周囲長は A **2.52 %** < B **9.47 %**(3.8 倍)、円形度は A **4.82 %** < B **20.45 %**(4.2 倍)。二値マスクを最近傍で回すと境界が**階段のまま置き直される**のに対し、灰を補間してから二値化すると境界が下の連続信号から引き直される。**回すなら灰でやってから二値化する。二値マスクを回してはいけない。**★閉形式の錨(合成の正方形 L=80)では、45 度の 4 連結階段周囲長 `4L → 4L√2` の **+41.4 %** が上限。実測は **7.91 %** で、`regionprops` の Crofton 補正が 5.2 倍下回らせている —— 予測は「上限」であって「実測の当て」ではない、と書いておく。★**分母を疑う**: Hu[1](`moments_region_central_invar`)は円に近い形では真値がほぼ 0(3.9e-04)なので、相対ばらつき 29.6 % は「30 % ずれた」ではなく**0 を分母にした**だけ。表にその判定を並べてある。★図は反転色 `mode="xor"`(最上位 bit だけ反転 —— 地の模様が残り、どの階調でも消えない)で輪郭を描き、72 コマの GIF で数字の揺れが見えるようにした。*

[![実写の硬貨を 5 度ずつ 1 周。地がモノクロなので輪郭は彩度のある色で描いている(灰色には彩度が無いので、どの階調とも色相で区別がつく)。右の表の数字がどれだけ揺れるかが見える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rotation_invariance_audit/02_rotating_coin_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_rotation_invariance_audit/02_rotating_coin.gif)

*↑ 測定の図 ―― 実写の硬貨を 5 度ずつ 1 周。地がモノクロなので輪郭は彩度のある色で描いている(灰色には彩度が無いので、どの階調とも色相で区別がつく)。右の表の数字がどれだけ揺れるかが見える。*

```
py -3.11 examples/poc_rotation_invariance_audit.py
```

ソース: [examples/poc_rotation_invariance_audit.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_rotation_invariance_audit.py)

使用 op(ノートへ): [`annotate_outline`](https://furuse.work/ops/annotate/paper/annotate_outline.html) · [`annotate_table`](https://furuse.work/ops/annotate/paper/annotate_table.html) · [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`circularity`](https://furuse.work/ops/2d/features/circularity.html) · [`eccentricity`](https://furuse.work/ops/2d/features/eccentricity.html) · [`moments_region_2nd_invar`](https://furuse.work/ops/2d/features/moments_region_2nd_invar.html) · [`moments_region_central_invar`](https://furuse.work/ops/2d/features/moments_region_central_invar.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html)

### 色・分離ウィング ―― 「効く手法」は無い、あるのは効く条件だけ

光源を推定して色を戻す、多波長で絵画の層を剥がす、偏光で鏡面反射を分離する。この部屋の 3 点は、既知の分光反射率・既知の光源・フレネルの式から線形の輻度を合成し、分離の結果を真値と突き合わせています。

結論は、どの展示でも「壊れる軸が直交している」ことでした。白パッチ法は白が在れば最良で、いちばん明るい 1 枚を外すだけで 8 倍悪くなる。灰色世界は飽和に強く、有彩色が 2 割を超えると負ける。基準光源では全手法がゼロ点に負ける。バンドを増やしても勝てず、近赤外を入れた瞬間に勝つ。

共通の注意は「リニアな輻度に戻してから渡す」こと。sRGB ガンマのまま渡しても例外は出ず、分離が静かに劣化するだけです。例外が出ない失敗は、この展示全体で最も多い型です。

## 93. 色恒常性(ホワイトバランス)―― 「効く手法」は無い、あるのは効く条件だけ

[![色恒常性(ホワイトバランス)―― 「効く手法」は無い、あるのは効く条件だけ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/01_casts_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/01_casts.png)

*↑ **色恒常性(ホワイトバランス)―― 「効く手法」は無い、あるのは効く条件だけ** ―― 24 枚の既知分光反射率と既知光源から線形 RGB を合成し、光源推定の回復角度誤差を測った図。白パッチ法は 11 光源の中央値 1.06 度で最良だが、いちばん明るい 1 枚を外すと 8.45 度、露出 3 倍で 43 % を飽和させると 13.61 度で「何もしない」と一致。真の光源で対角補正しても 2500 K では ΔE00 平均 5.07 が残る。*

[![灰色世界はゼロ点(何もしない)の線を 0.1〜0.2 の間で上抜けする = そこから先は回すだけ損。白パッチ法には崖が無い。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/02_bias_cliff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_white_balance/02_bias_cliff.png)

*↑ 測定の図 ―― 灰色世界はゼロ点(何もしない)の線を 0.1〜0.2 の間で上抜けする = そこから先は回すだけ損。白パッチ法には崖が無い。*

```
py -3.11 examples/poc_white_balance.py
```

ソース: [examples/poc_white_balance.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_white_balance.py)

使用 op(ノートへ): [`delta_e_map`](https://furuse.work/ops/imgmetrics/colordiff/delta_e_map.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`illuminant_from_dichromatic_planes`](https://furuse.work/ops/specular/dichromatic/illuminant_from_dichromatic_planes.html) · [`laplace`](https://furuse.work/ops/2d/edges/laplace.html) · [`linear_to_srgb`](https://furuse.work/ops/gfx2d/colorspace/linear_to_srgb.html) · [`mean_image`](https://furuse.work/ops/2d/smoothing/mean_image.html) · [`prewitt_amp`](https://furuse.work/ops/2d/edges/prewitt_amp.html) · [`roberts`](https://furuse.work/ops/2d/edges/roberts.html) · [`sobel_amp`](https://furuse.work/ops/2d/edges/sobel_amp.html) · [`spectrum_to_srgb`](https://furuse.work/ops/optics/appearance/spectrum_to_srgb.html)

## 94. 多波長で層を剥がす ―― 下絵・地塗り・上塗り・褪色を、真値を握ったまま分離する

[![多波長で層を剥がす ―― 下絵・地塗り・上塗り・褪色を、真値を握ったまま分離する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/01_per_field_auc_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/01_per_field_auc.png)

*↑ **多波長で層を剥がす ―― 下絵・地塗り・上塗り・褪色を、真値を握ったまま分離する** ―― 地塗り・下絵・上塗り・褪色を重ねた分光キューブを合成し、層を分離した図。可視だけを 16 バンドに割っても RGB と同じ(再現率 0.118 対 0.119)で、勝ったのは近赤外を入れたこと。同じ検出器が群青で AUC 1.000、アズライトで 0.630、剥落部で 0.013 ―― 平均すると全部消える。褪色前の色の復元は ΔE00 16.79 → 16.46 で、ゼロ点にほぼ勝てなかった。*

[![近赤外の差分は剥落部(楕円)で消え、近赤外 1 枚は面ごとに水準が違う。塗り分けは 1–99 分位でクリップした表示のみ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/02_detector_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pigment_unmixing/02_detector_maps.png)

*↑ 測定の図 ―― 近赤外の差分は剥落部(楕円)で消え、近赤外 1 枚は面ごとに水準が違う。塗り分けは 1–99 分位でクリップした表示のみ。*

```
py -3.11 examples/poc_pigment_unmixing.py
```

ソース: [examples/poc_pigment_unmixing.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pigment_unmixing.py)

使用 op(ノートへ): [`delta_e_map`](https://furuse.work/ops/imgmetrics/colordiff/delta_e_map.html) · [`linear_to_srgb`](https://furuse.work/ops/gfx2d/colorspace/linear_to_srgb.html) · [`spectrum_to_srgb`](https://furuse.work/ops/optics/appearance/spectrum_to_srgb.html) · [`threshold`](https://furuse.work/ops/2d/segmentation/threshold.html)

## 95. 偏光で鏡面反射を剥がす ―― フレネルの式で真値を作り、分離結果を突き合わせる

[![偏光で鏡面反射を剥がす ―― フレネルの式で真値を作り、分離結果を突き合わせる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/01_fresnel_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/01_fresnel.png)

*↑ **偏光で鏡面反射を剥がす ―― フレネルの式で真値を作り、分離結果を突き合わせる** ―― 拡散と鏡面を s/p 成分で合成し、フレネルの式から偏光度を出して分離結果を採点した図。偏光を使う手は入射角 20 度では 1.2 倍しか勝たない。拡散成分の誤差は閉形式 R_p·E に一致してブリュースター角 56.31 度で 0 ―― `polarization_separate` の拡散はその分だけ系統的に大きい。*

[![実測と閉形式が重なる。70 度の絶対誤差は 20 度より悪いのに、ゼロ点比では 70 度が最良 —— 最適角は評価軸で割れる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/02_angle_error_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_polarization_specular/02_angle_error.png)

*↑ 測定の図 ―― 実測と閉形式が重なる。70 度の絶対誤差は 20 度より悪いのに、ゼロ点比では 70 度が最良 —— 最適角は評価軸で割れる。*

```
py -3.11 examples/poc_polarization_specular.py
```

ソース: [examples/poc_polarization_specular.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_polarization_specular.py)

使用 op(ノートへ): [`fresnel_reflectance`](https://furuse.work/ops/3d/optics/fresnel_reflectance.html) · [`polarization_dolp_map`](https://furuse.work/ops/specular/polarization/polarization_dolp_map.html) · [`polarization_render`](https://furuse.work/ops/specular/polarization/polarization_render.html) · [`polarization_separate`](https://furuse.work/ops/specular/polarization/polarization_separate.html) · [`polarization_stokes`](https://furuse.work/ops/specular/polarization/polarization_stokes.html) · [`rmse`](https://furuse.work/ops/imgmetrics/fidelity/rmse.html)

## 96. 実写の免疫染色を色で分ける ―― 見張り役が、見張るべき誤りにだけ盲目だった

[![実写の免疫染色を色で分ける ―― 見張り役が、見張るべき誤りにだけ盲目だった](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stain_unmix/01_separation_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stain_unmix/01_separation.png)

*↑ **実写の免疫染色を色で分ける ―― 見張り役が、見張るべき誤りにだけ盲目だった** ―― 実写の免疫染色像(ヘマトキシリン + DAB)を色分離する。★合成なら完璧に分かれる(片方だけ濃度 1.0 を合成して解き直すと回収 1.0000 / 漏れ 0.0000)ので、合成だけ見ていると「解けている」で終わる。★実写では H の濃度が -4.446 まで振れ、負になる画素が 11.51 % ―― 負の濃度は「色素が光を出した」の意味で存在しない。★★染色ベクトルを平面内で ±20 度回すと H の中央値は 0.0471 → 0.1348(2.86 倍)、DAB は 0.3590 → 0.1836 と大きく動くのに、**残差チャネルの絶対中央値は 0.0345 のまま幅 3.3e-16** ―― 2 本が張る平面は回しても変わらないので、平面に直交する残差は定義上動かない。**「あてはまりの良さ」を見張っているつもりの量が、いちばん起こりやすい誤りだけを見ていない**。★★回した染色自身の負率も 11.51 % で完全に不変(双対ベクトルの向きが変わらず長さだけ変わるので符号は 1 画素も動かない)。動くのは相方 DAB の負率だけで、-20 度 0.00 % → +20 度 30.38 %。**見張り役は、自分ではなく相方を見る**。ただし単調なので片側の上限しか出ない。★往復の再構成は最大誤差 1e-06 だが、それは 4 節の誤りを何も否定しない ―― 何を検算しているかを言わないと検算にならない。この回に stain_unmix / stain_recompose / stain_vectors_from_patches を新設した(spec_unmix は 3 チャネルを設計上拒否するので RGB の入口が無かった)。*

[![H の中央値は 0.0656 -> 0.1348。残差の絶対中央値は 0.0345 のまま。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stain_unmix/02_blind_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_real_stain_unmix/02_blind.png)

*↑ 測定の図 ―― H の中央値は 0.0656 -> 0.1348。残差の絶対中央値は 0.0345 のまま。*

```
py -3.11 examples/poc_real_stain_unmix.py
```

ソース: [examples/poc_real_stain_unmix.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_real_stain_unmix.py)



### 法科学・文書ウィング ―― 1 枚の成功例は証拠にならない

改竄検出と書類の正対化。どちらも「見つかった 1 枚」「まっすぐになった 1 枚」で語られがちですが、この部屋の 2 点は、貼付の場所と品質、既知のホモグラフィと照明、を自分で決めた上で、画素ごとの ROC と画素単位の幾何誤差で採点しています。

改竄検出は検出側(防御)の PoC です。改竄を自分で作るのは検出器を測るのに真値が要るためだけで、作り方は最も稚拙なものに留めてあります。この展示がいちばん強く示すのは、保存ボタン 1 回でどの手掛かりも弱る、という検出側に不利な事実のほうです。

書類のほうは、名前が同じでモデルが違う関数を取り違えても例外が出ず、台形が残ったままもっともらしい絵が返る、という穴を数字にしています。影除去に良いところ取りは無く、平らにするほど薄い字が消えます。

## 97. 改竄検出を ROC で語る ―― 「見つかった 1 枚」ではなく、偽陽性を固定したときの検出率

[![改竄検出を ROC で語る ―― 「見つかった 1 枚」ではなく、偽陽性を固定したときの検出率](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/01_score_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/01_score_maps.png)

*↑ **改竄検出を ROC で語る ―― 「見つかった 1 枚」ではなく、偽陽性を固定したときの検出率** ―― JPEG q60 の素材を q92 の背景に貼って q95 で保存した改竄画像 10 枚を、画素ごとの ROC で採点した図。ELA の 1 つの数字は向きが教科書と逆(貼付部 / 背景 = 0.58 倍)で、改竄していない画像でも場所への偏りで AUC 0.797 が出る。ゴーストの谷の深さは AUC 0.997 だが、全体を q75 で再圧縮すると 0.975 へ落ちる。*

[![凡例の数字は AUC。乱数が対角線に乗ることで測り方に偏りが無いと言える。ゴーストA は乱数と重なる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/02_roc_tampered_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_forensics_roc/02_roc_tampered.png)

*↑ 測定の図 ―― 凡例の数字は AUC。乱数が対角線に乗ることで測り方に偏りが無いと言える。ゴーストA は乱数と重なる。*

```
py -3.11 examples/poc_forensics_roc.py
```

ソース: [examples/poc_forensics_roc.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_forensics_roc.py)

使用 op(ノートへ): [`copy_move_regions`](https://furuse.work/ops/imgforensics/copy_move/copy_move_regions.html) · [`error_level_map`](https://furuse.work/ops/imgforensics/compression/error_level_map.html) · [`jpeg_ghost_map`](https://furuse.work/ops/imgforensics/compression/jpeg_ghost_map.html) · [`jpeg_ghost_quality`](https://furuse.work/ops/imgforensics/compression/jpeg_ghost_quality.html) · [`noise_inconsistency_map`](https://furuse.work/ops/imgforensics/noise/noise_inconsistency_map.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html)

## 98. 手持ちで撮った書類をまっすぐに戻す ―― 台形補正と影除去を、真値と突き合わせて測る

[![手持ちで撮った書類をまっすぐに戻す ―― 台形補正と影除去を、真値と突き合わせて測る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/01_rectify_zero_points_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/01_rectify_zero_points.png)

*↑ **手持ちで撮った書類をまっすぐに戻す ―― 台形補正と影除去を、真値と突き合わせて測る** ―― 既知のホモグラフィと照明で撮った書類を戻し、4 隅と格子の画素誤差で採点した図。推定は格子 RMS 1.070 px(何もしない 37.376 px)だが、名前が同じでモデルが違う関数(アフィン)を取り違えると 32 倍悪く、例外は出ない。影の強さ 0.45 で 4 隅 RMS 5.72 px、0.55 で 65.10 px と崖。*

[![平坦・薄字・誤検出なしを同時に満たす行は 1 つも無い。窓 9 が fs.op で届く上限、窓 61 は自前。図の階調は真値で 217 段。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/02_shadow_tradeoff_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_document_scan/02_shadow_tradeoff.png)

*↑ 測定の図 ―― 平坦・薄字・誤検出なしを同時に満たす行は 1 つも無い。窓 9 が fs.op で届く上限、窓 61 は自前。図の階調は真値で 217 段。*

```
py -3.11 examples/poc_document_scan.py
```

ソース: [examples/poc_document_scan.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_document_scan.py)

使用 op(ノートへ): [`corner_response`](https://furuse.work/ops/2d/edges/corner_response.html) · [`dc_homomorphic`](https://furuse.work/ops/2d/decomposition/dc_homomorphic.html) · [`fill_holes`](https://furuse.work/ops/2d/region/fill_holes.html) · [`gauss_filter`](https://furuse.work/ops/2d/smoothing/gauss_filter.html) · [`get_region_contour`](https://furuse.work/ops/2d/region/get_region_contour.html) · [`gray_tophat`](https://furuse.work/ops/2d/morphology/gray_tophat.html) · [`illuminate`](https://furuse.work/ops/2d/gray/illuminate.html) · [`mean_image`](https://furuse.work/ops/2d/smoothing/mean_image.html) · [`opening_circle`](https://furuse.work/ops/2d/region/opening_circle.html) · [`otsu`](https://furuse.work/ops/2d/segmentation/otsu.html) · [`project_points`](https://furuse.work/ops/3d/render/project_points.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`select_largest`](https://furuse.work/ops/2d/region/select_largest.html) · [`sobel_dir`](https://furuse.work/ops/2d/edges/sobel_dir.html) · [`var_threshold`](https://furuse.work/ops/2d/segmentation/var_threshold.html)

## 99. カメラ指紋(PRNU)で「どのカメラで撮ったか」を当てる ―― 指紋は枚数で育ち、保存ボタンで消える

[![カメラ指紋(PRNU)で「どのカメラで撮ったか」を当てる ―― 指紋は枚数で育ち、保存ボタンで消える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/01_estimators_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/01_estimators.png)

*↑ **カメラ指紋(PRNU)で「どのカメラで撮ったか」を当てる ―― 指紋は枚数で育ち、保存ボタンで消える** ―― 2 台の仮想カメラに固定の感度むら K を仕込み、30 枚の残差から指紋を推定して照合した。清浄条件では同一カメラの PCE 中央値 2192 に対し別カメラ 15.7(AUC 1.000)だが、JPEG 相当の量子化は品質 50 相当で PCE を 3.6 % に、0.5× 縮小は 1.5 % に落とす ―― 消したのは幾何ではなく残差抽出器だった。K=0 のカメラでも同じ背景を 30 枚写せば PCE 1706 の「指紋」ができる。被写体は指紋に化ける。*

[![別カメラのピークは毎回別の位置に立つ((0,0) は 0/30)。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/02_match_pce_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_prnu_camera_fingerprint/02_match_pce.png)

*↑ 測定の図 ―― 別カメラのピークは毎回別の位置に立つ((0,0) は 0/30)。*

```
py -3.11 examples/poc_prnu_camera_fingerprint.py
```

ソース: [examples/poc_prnu_camera_fingerprint.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_prnu_camera_fingerprint.py)

使用 op(ノートへ): [`aug_jpeg_blocks`](https://furuse.work/ops/2d/augmentation/aug_jpeg_blocks.html) · [`evidence_quantile`](https://furuse.work/ops/imgforensics/calibration/evidence_quantile.html) · [`fingerprint_correlate`](https://furuse.work/ops/imgforensics/sensor/fingerprint_correlate.html) · [`gauss_image`](https://furuse.work/ops/2d/smoothing/gauss_image.html) · [`median_image`](https://furuse.work/ops/2d/rank/median_image.html) · [`null_distribution`](https://furuse.work/ops/imgforensics/calibration/null_distribution.html) · [`reflect`](https://furuse.work/ops/3d/optics/reflect.html) · [`sensor_fingerprint`](https://furuse.work/ops/imgforensics/sensor/sensor_fingerprint.html) · [`sk_nlm`](https://furuse.work/ops/2d/smoothing/sk_nlm.html) · [`sk_tv`](https://furuse.work/ops/2d/smoothing/sk_tv.html) · [`sk_wavelet`](https://furuse.work/ops/2d/smoothing/sk_wavelet.html) · [`xsp_dct_denoise`](https://furuse.work/ops/2d/smoothing/xsp_dct_denoise.html) · [`xsp_wiener`](https://furuse.work/ops/2d/smoothing/xsp_wiener.html)

## 100. 絵画のひび割れ網 ―― 3 指標のうち撮影条件で壊れるのは分岐次数だけ

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

## 101. 壊れたメッシュを直してから測る ―― 消えるのは欠陥の数で、戻るのは量ではない

[![壊れたメッシュを直してから測る ―― 消えるのは欠陥の数で、戻るのは量ではない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/01_scene.png)

*↑ **壊れたメッシュを直してから測る ―― 消えるのは欠陥の数で、戻るのは量ではない** ―― 球とトーラスと角柱のブール和から閉じた三角メッシュを作り、穴・裏返った面・非多様体辺・退化三角形・重複頂点・自己交差を種類ごとに既知個数だけ仕込んで、位相の数字と体積・表面積の両方で追いました。オイラー標数は 6 種のうち 5 種にまったく反応せず、穴 6 個と重複面 6 枚を同時に入れると頂点・辺・面・χ が健全な部品と 1 つも違わなくなります。直したあとも量は戻らず、半頂角 45° の穴を塞いだ球は表面積が予測 -2.145 % に対して実測 +6.868 %(縁が円ではなく階段だから)、頂点を 6 個だけ突き刺したメッシュは位相の検査を 3 つとも通り抜けたまま表面積 +4.414 % / 体積 -0.332 % と 13 倍食い違いました。*

[![健全な部品の χ は 0(種数 1)。χ=2 を合格条件にすると健全品が落ちる。最終行は打ち消し。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/02_euler_blindspots_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_mesh_quality_repair/02_euler_blindspots.png)

*↑ 測定の図 ―― 健全な部品の χ は 0(種数 1)。χ=2 を合格条件にすると健全品が落ちる。最終行は打ち消し。*

```
py -3.11 examples/poc_mesh_quality_repair.py
```

ソース: [examples/poc_mesh_quality_repair.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_mesh_quality_repair.py)

使用 op(ノートへ): [`decimate_qem`](https://furuse.work/ops/3d/mesh_process/decimate_qem.html) · [`face_normals`](https://furuse.work/ops/3d/mesh_process/face_normals.html) · [`fill_holes`](https://furuse.work/ops/2d/region/fill_holes.html) · [`inertia_tensor`](https://furuse.work/ops/3d/moment_invariant/inertia_tensor.html) · [`mesh_area`](https://furuse.work/ops/3d/mesh_process/mesh_area.html) · [`mesh_edge_lengths`](https://furuse.work/ops/3d/terrain/mesh_edge_lengths.html) · [`mesh_edge_stats`](https://furuse.work/ops/3d/resolution/mesh_edge_stats.html) · [`sdf_subtract`](https://furuse.work/ops/3d/sdf_csg/sdf_subtract.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`vertex_curvature`](https://furuse.work/ops/3d/mesh_process/vertex_curvature.html) · [`vertex_normals`](https://furuse.work/ops/3d/mesh_process/vertex_normals.html) · [`voxel_to_mesh`](https://furuse.work/ops/3d/transform/voxel_to_mesh.html)

## 102. 斜面の土量 ―― 合わせてから引くと、崩れが浅くなる

[![斜面の土量 ―― 合わせてから引くと、崩れが浅くなる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/09_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/09_scene.png)

*↑ **斜面の土量 ―― 合わせてから引くと、崩れが浅くなる** ―― 傾斜のある合成地形に既知体積の掘削と堆積を仕込み、2 時期の航空点群から鉛直差分と法線方向の差で土量を測った。予想した「斜面では cos だけ体積が縮む」は外れで、水平投影面積で積む限り cos は約分し、掘削体積の誤差は傾斜 0〜40 度でどれも -0.011 % のまま動かない。壊れたのは合わせ方のほうで、変化域が視野の 33 % もあると位置合わせが変化そのものを吸い、正味土量は真値 -30.4 m3 に対し -3.8 m3 まで潰れた ―― 変化なしの対照ですら偽の掘削が 83.8 m3 出る。*

[![傾斜を 0 から 40 度まで振っても体積の誤差に傾向が無い。cos は積分で約分する。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/01_geometry_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_lidar_terrain_change/01_geometry.png)

*↑ 測定の図 ―― 傾斜を 0 から 40 度まで振っても体積の誤差に傾向が無い。cos は積分で約分する。*

```
py -3.11 examples/poc_lidar_terrain_change.py
```

ソース: [examples/poc_lidar_terrain_change.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_lidar_terrain_change.py)

使用 op(ノートへ): [`chamfer_distance`](https://furuse.work/ops/3d/metrics/chamfer_distance.html) · [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`estimate_oriented_normals`](https://furuse.work/ops/3d/normals_orient/estimate_oriented_normals.html) · [`fit_plane_3d`](https://furuse.work/ops/3d/geometry/fit_plane_3d.html) · [`icp_point2point_3d`](https://furuse.work/ops/3d/refine/icp_point2point_3d.html) · [`median`](https://furuse.work/ops/2d/rank/median.html) · [`ransac_plane`](https://furuse.work/ops/3d/robust_fit/ransac_plane.html) · [`voxel_grid_downsample`](https://furuse.work/ops/3d/preprocess/voxel_grid_downsample.html)

## 103. CAD と実測点群の差分検査 ―― 合わせた分だけ欠陥が消え、無い所にへこみが出る

[![CAD と実測点群の差分検査 ―― 合わせた分だけ欠陥が消え、無い所にへこみが出る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/01_scene.png)

*↑ **CAD と実測点群の差分検査 ―― 合わせた分だけ欠陥が消え、無い所にへこみが出る** ―― 解析形状の機械部品に、局所へこみ・反り・摩耗を法線方向の既知量として仕込み、既知の姿勢・雑音・欠測つきの実測点群を合成した。合わせてから符号付き偏差と公差外面積を測ると、局所へこみの読みは 3.7 % しか薄まらないのに、真値が 1.2 µm しかない部品中央に深さ 121 µm の存在しないへこみが出る(閉形式の予測 -120 µm)。消えるか化けるかは剛体 6 自由度が吸える偏差場に似ているかどうかで決まり、稜線では最近傍が隣の面へ飛んで、欠陥ゼロの対照でも 66.5 mm^2 の偽の公差外領域が出た。*

[![真の姿勢を与えた最終行が推定器そのものの床。点-面 ICP との差は姿勢ではなく datum の取り方の差。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/02_methods_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_cad_scan_deviation/02_methods.png)

*↑ 測定の図 ―― 真の姿勢を与えた最終行が推定器そのものの床。点-面 ICP との差は姿勢ではなく datum の取り方の差。*

```
py -3.11 examples/poc_cad_scan_deviation.py
```

ソース: [examples/poc_cad_scan_deviation.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_cad_scan_deviation.py)

使用 op(ノートへ): [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`chamfer_distance`](https://furuse.work/ops/3d/metrics/chamfer_distance.html) · [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`estimate_oriented_normals`](https://furuse.work/ops/3d/normals_orient/estimate_oriented_normals.html) · [`face_areas`](https://furuse.work/ops/3d/mesh_process/face_areas.html) · [`gicp`](https://furuse.work/ops/3d/gicp/gicp.html) · [`hausdorff_distance`](https://furuse.work/ops/3d/metrics/hausdorff_distance.html) · [`icp_point2plane`](https://furuse.work/ops/3d/refine/icp_point2plane.html) · [`icp_point2point_3d`](https://furuse.work/ops/3d/refine/icp_point2point_3d.html) · [`query_distance`](https://furuse.work/ops/3d/occupancy/query_distance.html) · [`register_fpfh`](https://furuse.work/ops/3d/feature_register/register_fpfh.html) · [`sphere_sdf`](https://furuse.work/ops/3d/sdf_csg/sphere_sdf.html) · [`voxel_grid_downsample`](https://furuse.work/ops/3d/preprocess/voxel_grid_downsample.html)

## 104. 造形しやすさを形から測る —— しきい値に貼りついた面は、丸めた分だけ判定が飛ぶ

[![造形しやすさを形から測る —— しきい値に貼りついた面は、丸めた分だけ判定が飛ぶ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/01_scene.png)

*↑ **造形しやすさを形から測る —— しきい値に貼りついた面は、丸めた分だけ判定が飛ぶ** ―― 設計値の分かる合成部品(薄壁・スロット・45 度前後の補強・穴)をボクセル化し、肉厚・要サポート面積・工具の入る隙間を測りました。しきい値 45 度の両側で必要面積は 185.22 → 576.10 mm^2 と 0.2 度で 3.11 倍に跳ね、その段差は等値面を距離場から取ると 100 %、平滑化でも 12 % 消えます。肉厚は 2 voxel 刻みに潰れ(内接球にしても同じ)、隙間の誤判定は両方向に出て、粗さ 0.500 mm では隙間が 2.000 mm に太り入らない工具を通します。*

[![上: 左端の 2 本が薄壁(1.500 mm)とそのあいだのスロット(1.500 mm)、右の三角が補強。下: リブと薄壁の footprint。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/02_sections_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_dfm_thickness_overhang/02_sections.png)

*↑ 測定の図 ―― 上: 左端の 2 本が薄壁(1.500 mm)とそのあいだのスロット(1.500 mm)、右の三角が補強。下: リブと薄壁の footprint。*

```
py -3.11 examples/poc_dfm_thickness_overhang.py
```

ソース: [examples/poc_dfm_thickness_overhang.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_dfm_thickness_overhang.py)

使用 op(ノートへ): [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`face_areas`](https://furuse.work/ops/3d/mesh_process/face_areas.html) · [`face_normals`](https://furuse.work/ops/3d/mesh_process/face_normals.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`morph_erode3d`](https://furuse.work/ops/3d/morphology/morph_erode3d.html) · [`render_shaded`](https://furuse.work/ops/3d/render/render_shaded.html) · [`sdf_intersect`](https://furuse.work/ops/3d/sdf_csg/sdf_intersect.html) · [`sdf_subtract`](https://furuse.work/ops/3d/sdf_csg/sdf_subtract.html) · [`sdf_to_occupancy`](https://furuse.work/ops/3d/transform/sdf_to_occupancy.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`vol_wall_thickness`](https://furuse.work/ops/3d/probe/vol_wall_thickness.html) · [`voxel_to_mesh`](https://furuse.work/ops/3d/transform/voxel_to_mesh.html)

## 105. 対称性で欠けを補う —— 仮定した面がずれた分だけ、復元は嘘をつく

[![対称性で欠けを補う —— 仮定した面がずれた分だけ、復元は嘘をつく](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/01_scene.png)

*↑ **対称性で欠けを補う —— 仮定した面がずれた分だけ、復元は嘘をつく** ―― 左右対称な仮面を合成して完全形と対称面を真値に持ち、片側を球で削って対称復元を測った。面が真値なら復元 RMS 0.81 mm で穴埋め補間(1.60 mm)に勝つが、面が 1.39 度(84 分角)または 1.41 mm ずれた時点で負ける —— 誤差は鏡像変位の法線成分で予測でき(相対誤差 4.6 %、素朴な 2d sin α は 50.6 % 外す)、崖の位置は幾何だけで決まる。★欠損は面をずらす前に軸ごと飛ばし(失った点 3.1 % で PCA 候補の順位が逆転)、しかも本当は対称でない形では面が真値でも装飾を 3436 mm³ 捏造するか 3495 mm³ 消す。*

[![失われた真値の点から復元点群までの距離(符号なし、6 mm で頭打ち)。対称復元だけが眼窩の形を取り戻す。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/02_restore_error_maps_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_symmetry_restoration/02_restore_error_maps.png)

*↑ 測定の図 ―― 失われた真値の点から復元点群までの距離(符号なし、6 mm で頭打ち)。対称復元だけが眼窩の形を取り戻す。*

```
py -3.11 examples/poc_symmetry_restoration.py
```

ソース: [examples/poc_symmetry_restoration.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_symmetry_restoration.py)

使用 op(ノートへ): [`detect_reflection_symmetry`](https://furuse.work/ops/3d/symmetry/detect_reflection_symmetry.html) · [`fill_holes`](https://furuse.work/ops/2d/region/fill_holes.html) · [`fit_plane_3d`](https://furuse.work/ops/3d/geometry/fit_plane_3d.html) · [`icp_point2point_3d`](https://furuse.work/ops/3d/refine/icp_point2point_3d.html) · [`normalize`](https://furuse.work/ops/shape2d/descriptor/normalize.html) · [`reflect_points`](https://furuse.work/ops/3d/symmetry/reflect_points.html) · [`reflection_symmetry_score`](https://furuse.work/ops/3d/symmetry/reflection_symmetry_score.html)

## 106. 積層の反りは層の履歴が決める —— 均した面積は置き場所を捨てる

[![積層の反りは層の履歴が決める —— 均した面積は置き場所を捨てる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/01_scene.png)

*↑ **積層の反りは層の履歴が決める —— 均した面積は置き場所を捨てる** ―― 1 層あたり一定の収縮ひずみを仕込んだ合成形状 7 つを層に切り、断面積の履歴だけから梁の閉形式で反りを予測して、層を 1 枚ずつ生やす有限要素の実測と突き合わせた。最終形状だけを見る予測器は原理的にゼロ(2.712e-21)を返し、履歴の閉形式は 7 形状中 4 形状で 0.4 % 以内に当たるが、面積を長さ方向に均した瞬間に「どこに置いたか」が消える。層面積の履歴が 1 mm^2 も違わない三つ子でたわみは 0.4109 / 0.3809 / 0.3271 mm と 26 % 開き、基板を引き剥がす力に至っては 11.8 対 573.5 N の 48 倍違って合否まで割れた。*

[![この断面の面積の列だけが、閉形式の入力になる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/02_layer_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_print_warpage_risk/02_layer_frames.png)

*↑ 測定の図 ―― この断面の面積の列だけが、閉形式の入力になる。*

```
py -3.11 examples/poc_print_warpage_risk.py
```

ソース: [examples/poc_print_warpage_risk.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_print_warpage_risk.py)

使用 op(ノートへ): [`blob_features`](https://furuse.work/ops/blob/measure/blob_features.html) · [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`sdf_to_occupancy`](https://furuse.work/ops/3d/transform/sdf_to_occupancy.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`text_box`](https://furuse.work/ops/annotate/text/text_box.html)

## 107. 鳥瞰図への多センサ融合 —— 画像では合格の校正が、遠くでは長さになる

[![鳥瞰図への多センサ融合 —— 画像では合格の校正が、遠くでは長さになる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/01_scene_bev_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/01_scene_bev.png)

*↑ **鳥瞰図への多センサ融合 —— 画像では合格の校正が、遠くでは長さになる** ―― 解析的な街路(先行トラック + 互いの影に 1 台ずつ隠れる遠方車)を作り、左ミラーの LiDAR と右ミラーの深度カメラを共通の鳥瞰格子へ融合して、外部パラメータの誤差を回転・並進・時刻ずれに分けて掃引した。融合の占有 IoU 0.7033 は単センサの最良 0.5417 を上回るが、その利得はすべて視界の相補性から来ている。再投影 1 px は 22 m 先で 0.083 m に化け、崖はセル 0.2 m ではなく車幅で決まり(半分の点がセルを跨いでも IoU は 5.8 % しか落ちない)、yaw 3 度で融合は単センサに負ける。*

[![横に 1.80 m 離した 2 センサの「自由と言い切れた領域」。青い帯が LiDAR にしか見えない所、橙の帯がカメラにしか見えない所、灰色は両方。白は真値の障害物。22 m の 2 台は**互いの影に 1 台ずつ入っている**。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/02_shadow_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_bev_sensor_fusion/02_shadow_map.png)

*↑ 測定の図 ―― 横に 1.80 m 離した 2 センサの「自由と言い切れた領域」。青い帯が LiDAR にしか見えない所、橙の帯がカメラにしか見えない所、灰色は両方。白は真値の障害物。22 m の 2 台は**互いの影に 1 台ずつ入っている**。*

```
py -3.11 examples/poc_bev_sensor_fusion.py
```

ソース: [examples/poc_bev_sensor_fusion.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_bev_sensor_fusion.py)

使用 op(ノートへ): [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`closing_circle`](https://furuse.work/ops/2d/region/closing_circle.html) · [`depth_to_points`](https://furuse.work/ops/3d/transform/depth_to_points.html) · [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`fill_up`](https://furuse.work/ops/2d/region/fill_up.html) · [`fuse`](https://furuse.work/ops/3d/tsdf_fusion/fuse.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`occupancy_grid`](https://furuse.work/ops/3d/occupancy/occupancy_grid.html) · [`project_points`](https://furuse.work/ops/3d/render/project_points.html) · [`sdf_to_occupancy`](https://furuse.work/ops/3d/transform/sdf_to_occupancy.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`voxel_grid_downsample`](https://furuse.work/ops/3d/preprocess/voxel_grid_downsample.html) · [`voxel_iou`](https://furuse.work/ops/3d/metrics/voxel_iou.html)

## 108. 接合層のボイドを 1 個の数字に畳む ―― 畳んだ分だけ、寿命に効く形が消える

[![接合層のボイドを 1 個の数字に畳む ―― 畳んだ分だけ、寿命に効く形が消える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/01_scene_sections_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/01_scene_sections.png)

*↑ **接合層のボイドを 1 個の数字に畳む ―― 畳んだ分だけ、寿命に効く形が消える** ―― 合成のダイアタッチ接合層に、体積率を 3.000 % に厳密にそろえたまま位置・形・近接だけを変えた 5 条件のボイドを仕込み、PSF・雑音・カッピングつきの X 線 CT として撮り直した。2 値化してボイド率だけを出すゼロ点は 5 条件を 2.46〜2.63 %(開きは 0.17 ポイント)としか分けないのに、界面に接する扁平ボイドが界面を塞ぐ面積は同体積の球の 2.09 倍(14.49 対 6.92 %)、連なりの跨ぎ率は散在の 13.1 倍(80.0 対 6.1 %)になる。崖の予想は外れ、ボクセルを 60 µm まで粗くしてもボイド率は 3.21 % と崩れず(格子の位相の運で ±1.36 ポイント振れるだけ)、代わりに扁平度が測れなくなり界面欠損率が 14.16 → 9.78 % と『安全』側へ落ちた ―― 壊れる向きが合格の側なのがいちばん悪い。*

[![疑似カラーはラベル番号を並べ替えたもの。側面図で界面(上端)に貼りついているのが見える。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/02_void_label_map_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_ct_void_morphology/02_void_label_map.png)

*↑ 測定の図 ―― 疑似カラーはラベル番号を並べ替えたもの。側面図で界面(上端)に貼りついているのが見える。*

```
py -3.11 examples/poc_ct_void_morphology.py
```

ソース: [examples/poc_ct_void_morphology.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_ct_void_morphology.py)

使用 op(ノートへ): [`boundary_vertices`](https://furuse.work/ops/3d/mesh_process/boundary_vertices.html) · [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`cylinder_sdf`](https://furuse.work/ops/3d/sdf_csg/cylinder_sdf.html) · [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`face_areas`](https://furuse.work/ops/3d/mesh_process/face_areas.html) · [`mesh_volume`](https://furuse.work/ops/3d/mesh_process/mesh_volume.html) · [`morph_dilate3d`](https://furuse.work/ops/3d/morphology/morph_dilate3d.html) · [`plane_sdf`](https://furuse.work/ops/3d/sdf_csg/plane_sdf.html) · [`query_distance`](https://furuse.work/ops/3d/occupancy/query_distance.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`sphere_sdf`](https://furuse.work/ops/3d/sdf_csg/sphere_sdf.html) · [`vol_boundary_points`](https://furuse.work/ops/3d/boundary/vol_boundary_points.html) · [`vol_gaussian_psf`](https://furuse.work/ops/3d/restoration/vol_gaussian_psf.html) · [`voxel_to_mips`](https://furuse.work/ops/3d/transform/voxel_to_mips.html)

## 109. 電池セルの内部劣化を CT で測る ―― 膨れは外から見え、原因は中にある

[![電池セルの内部劣化を CT で測る ―― 膨れは外から見え、原因は中にある](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/02_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/02_scene.png)

*↑ **電池セルの内部劣化を CT で測る ―― 膨れは外から見え、原因は中にある** ―― 角形リチウムイオンセルの積層電極とアルミ缶を真値つきで組み、劣化を既知の場(一様膨れ・局所膨れ・層間ガス空隙・電極ずれ)として与えて、順投影 → ビームハードニング → 光子雑音 → FBP 再構成という実際の撮像を通してから測った。電極が 10 % 膨れても外形に出るのは 29.4 % だけで、しかも中央のノギスは体積等価な平均の 3.6 倍(+0.235 対 +0.066 mm)を読む。外形のふくらみを揃えた 3 つのセルは缶の高さが 0.000 mm しか違わないのに、内部指標は空隙率 0.00 対 5.20 %、層の平面度 0.0156 対 0.0784 mm で分かれ、その内部指標が壊れる崖は電極厚 0.200 mm ではなく層間の隙間 0.120 mm が決めた(voxel/層厚 = 0.30、標本化定理からの予測 0.80 は外れ)。*

[![真正面(0 度)なら空隙の影までは見える。ただし奥行きに積算されているので厚みも深さも出ない。22 度傾けると層の縞そのものが重なって消える —— 投影では姿勢が結果を決めてしまう。だから断層に落とす。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/01_xray_projection_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_battery_ct_degradation/01_xray_projection.png)

*↑ 測定の図 ―― 真正面(0 度)なら空隙の影までは見える。ただし奥行きに積算されているので厚みも深さも出ない。22 度傾けると層の縞そのものが重なって消える —— 投影では姿勢が結果を決めてしまう。だから断層に落とす。*

```
py -3.11 examples/poc_battery_ct_degradation.py
```

ソース: [examples/poc_battery_ct_degradation.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_battery_ct_degradation.py)

使用 op(ノートへ): [`beam_hardening_apply`](https://furuse.work/ops/tomography/artifact/beam_hardening_apply.html) · [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`fbp_volume`](https://furuse.work/ops/tomography/volume/fbp_volume.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`plane_sdf`](https://furuse.work/ops/3d/sdf_csg/plane_sdf.html) · [`projection_angles`](https://furuse.work/ops/tomography/layout/projection_angles.html) · [`radon_volume`](https://furuse.work/ops/tomography/volume/radon_volume.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`ring_artifact_apply`](https://furuse.work/ops/tomography/artifact/ring_artifact_apply.html) · [`sdf_intersect`](https://furuse.work/ops/3d/sdf_csg/sdf_intersect.html) · [`sdf_subtract`](https://furuse.work/ops/3d/sdf_csg/sdf_subtract.html) · [`sdf_to_occupancy`](https://furuse.work/ops/3d/transform/sdf_to_occupancy.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`vol_bounding_box`](https://furuse.work/ops/3d/domain/vol_bounding_box.html) · [`vol_edge_probe`](https://furuse.work/ops/3d/probe/vol_edge_probe.html) · [`vol_fft_lowpass`](https://furuse.work/ops/3d/frequency/vol_fft_lowpass.html) · [`vol_label`](https://furuse.work/ops/3d/regionprops/vol_label.html) · [`vol_profile_line`](https://furuse.work/ops/3d/probe/vol_profile_line.html) · [`vol_region_props`](https://furuse.work/ops/3d/regionprops/vol_region_props.html) · [`vol_resize`](https://furuse.work/ops/3d/geom_transform/vol_resize.html) · [`vol_wall_thickness`](https://furuse.work/ops/3d/probe/vol_wall_thickness.html)

## 110. 構造物を年ごとに測り返す —— 測る場所がずれると、劣化は進んだように見える

[![構造物を年ごとに測り返す —— 測る場所がずれると、劣化は進んだように見える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/01_scene.png)

*↑ **構造物を年ごとに測り返す —— 測る場所がずれると、劣化は進んだように見える** ―― 橋桁(平面 7 枚 + 円柱 2 本)に既知のたわみ・断面欠損・支承沈下・ひび割れを 3 時点ぶん仕込み、走査位置も密度も姿勢も毎回変えて測り返した。劣化ゼロで測り直しただけで最近傍差分は中央値 21.07 mm・最大 42.64 mm の「変化」を返し、しきい値 1 mm で数えた偽の補修候補 5.098 L は本物 5.882 L の 87 % に達する。たわみを含めて全点で合わせると中央のたわみの 0.689(閉形式 2/3)が姿勢に吸われて支点に -1.737 mm の偽の隆起が出、決まらない橋軸方向は桁の平面ではなく支承の円柱にだけ「41.2 mm 水平に動いた」として現れる。*

[![下フランジの暗い窪みが断面欠損、面全体の淡い変化がたわみ。腹板(法線が水平)にはたわみが出ない ——同じ劣化でも面の向きで見え方が変わる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/02_frames_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_structure_4d_deterioration/02_frames.png)

*↑ 測定の図 ―― 下フランジの暗い窪みが断面欠損、面全体の淡い変化がたわみ。腹板(法線が水平)にはたわみが出ない ——同じ劣化でも面の向きで見え方が変わる。*

```
py -3.11 examples/poc_structure_4d_deterioration.py
```

ソース: [examples/poc_structure_4d_deterioration.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_structure_4d_deterioration.py)

使用 op(ノートへ): [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`chamfer_distance`](https://furuse.work/ops/3d/metrics/chamfer_distance.html) · [`cylinder_sdf`](https://furuse.work/ops/3d/sdf_csg/cylinder_sdf.html) · [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`euclidean_cluster`](https://furuse.work/ops/3d/segment/euclidean_cluster.html) · [`fit_circle_3d`](https://furuse.work/ops/3d/geometry/fit_circle_3d.html) · [`fit_plane_3d`](https://furuse.work/ops/3d/geometry/fit_plane_3d.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`hausdorff_distance`](https://furuse.work/ops/3d/metrics/hausdorff_distance.html) · [`plane_sdf`](https://furuse.work/ops/3d/sdf_csg/plane_sdf.html) · [`rmse`](https://furuse.work/ops/imgmetrics/fidelity/rmse.html) · [`sdf_intersect`](https://furuse.work/ops/3d/sdf_csg/sdf_intersect.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`voxel_grid_downsample`](https://furuse.work/ops/3d/preprocess/voxel_grid_downsample.html)

## 111. 設計と実物の食い違いを部屋から測る ―― 合わせの妥協角は、無傷の部材へ配られる

[![設計と実物の食い違いを部屋から測る ―― 合わせの妥協角は、無傷の部材へ配られる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/01_scene_plan_section_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/01_scene_plan_section.png)

*↑ **設計と実物の食い違いを部屋から測る ―― 合わせの妥協角は、無傷の部材へ配られる** ―― 部屋 1 つ分の合成建物に、壁の傾き・床の勾配と反り・柱の寸法違い・開口のずれを既知量で仕込み、3 か所からの走査(柱の影・入射角依存の雑音・混合画素・レジストレーション誤差つき)で測り返した。設計モデルへの平均距離という建物 1 個の数字は施工誤差の有無で 1.41 mm しか動かず、点群を一括で合わせると壁の傾きは真値の 69 % に痩せ、代わりに完全に水平な天井が 0.89 mrad 傾いて見える(合わせが吸う量を閉形式で先に予測し、実測との差は 0.05 mrad)。崖は欠測率でなく残った面の高さで決まり、同じ 90 % の欠測でも無作為に落とせば 0.098 mrad、下から順に残す形なら 1.234 mrad と 12.6 倍違った。*

[![いちばん暗い所は 1 か所も見ていない。柱の影はスキャン位置から放射状に伸びる。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/02_station_coverage_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_scan_to_bim_asbuilt/02_station_coverage.png)

*↑ 測定の図 ―― いちばん暗い所は 1 か所も見ていない。柱の影はスキャン位置から放射状に伸びる。*

```
py -3.11 examples/poc_scan_to_bim_asbuilt.py
```

ソース: [examples/poc_scan_to_bim_asbuilt.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_scan_to_bim_asbuilt.py)

使用 op(ノートへ): [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`chamfer_distance`](https://furuse.work/ops/3d/metrics/chamfer_distance.html) · [`cylinder_sdf`](https://furuse.work/ops/3d/sdf_csg/cylinder_sdf.html) · [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`euclidean_cluster`](https://furuse.work/ops/3d/segment/euclidean_cluster.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`plane_sdf`](https://furuse.work/ops/3d/sdf_csg/plane_sdf.html) · [`plane_segmentation`](https://furuse.work/ops/3d/segment/plane_segmentation.html) · [`sdf_intersect`](https://furuse.work/ops/3d/sdf_csg/sdf_intersect.html) · [`sdf_subtract`](https://furuse.work/ops/3d/sdf_csg/sdf_subtract.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html) · [`voxel_grid_downsample`](https://furuse.work/ops/3d/preprocess/voxel_grid_downsample.html)

## 112. 配管内面の減肉を展開図で測る ―― 軸を決めた分だけ、管底の腐食が消える

[![配管内面の減肉を展開図で測る ―― 軸を決めた分だけ、管底の腐食が消える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/01_scene_pipe_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/01_scene_pipe.png)

*↑ **配管内面の減肉を展開図で測る ―― 軸を決めた分だけ、管底の腐食が消える** ―― 合成の管に孔食・全周減肉・管底腐食・溶接ビード・楕円化・曲がりを既知の深さで仕込み、管内を走る距離センサの軸を意図的にずらして展開図を作りました。軸が 4.0 mm ずれるだけで腐食ゼロの真円の管の 44.8 % が減肉と判定され(中心のずれは振幅 e の 1 周期の正弦波になる、という幾何の予測との差は 1.84 ポイント)、偽の減肉体積は本物の孔食の 149.9 倍になります。1 周期を消せば偽物は消えますが、下水管でいちばん多い管底の腐食もその 79 % が同じ 1 周期に居るので検出率が 100.0 → 34.4 % へ落ち、軸の動きを物理どおり(直線とたわみ)に縛って初めて両方が残ります。*

[![下の帯の細くなっている所が管底腐食。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/02_scene_polar_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pipe_wall_loss/02_scene_polar.png)

*↑ 測定の図 ―― 下の帯の細くなっている所が管底腐食。*

```
py -3.11 examples/poc_pipe_wall_loss.py
```

ソース: [examples/poc_pipe_wall_loss.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pipe_wall_loss.py)

使用 op(ノートへ): [`blob_label`](https://furuse.work/ops/blob/connect/blob_label.html) · [`blob_select`](https://furuse.work/ops/blob/select/blob_select.html) · [`cylinder_sdf`](https://furuse.work/ops/3d/sdf_csg/cylinder_sdf.html) · [`cylinder_unwrap`](https://furuse.work/ops/3d/curvilinear/cylinder_unwrap.html) · [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`polar_unwrap`](https://furuse.work/ops/3d/curvilinear/polar_unwrap.html) · [`ransac_cylinder`](https://furuse.work/ops/3d/robust_fit/ransac_cylinder.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`sdf_subtract`](https://furuse.work/ops/3d/sdf_csg/sdf_subtract.html) · [`sdf_to_occupancy`](https://furuse.work/ops/3d/transform/sdf_to_occupancy.html) · [`spectrum`](https://furuse.work/ops/oned/signal/spectrum.html) · [`vol_wall_thickness`](https://furuse.work/ops/3d/probe/vol_wall_thickness.html)

## 113. 作物の葉面積を上から測る —— 隠れるより先に、投影が畳んでしまう

[![作物の葉面積を上から測る —— 隠れるより先に、投影が畳んでしまう](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crop_phenotyping/08_scene_nadir_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crop_phenotyping/08_scene_nadir.png)

*↑ **作物の葉面積を上から測る —— 隠れるより先に、投影が畳んでしまう** ―― 葉を解析曲面(片面面積 pi/4·L·W、葉角も投影係数も閉形式)で組んだトウモロコシ群落に、天頂からの厳密な z-buffer をかけて植被率・遮蔽・葉角を測った。植被率を Beer-Lambert で戻す素朴な葉面積指数は、消光係数を真値に直しても真の 4.85 に対し -52.2 %、しかも 2 段階クランピングから予測した天井 2.26 のすぐ上(実測 2.70)で止まる。遮蔽は天頂の植被率を 1 ビットも変えず、壊しているのは 1 セルを平均 3.49 枚の葉が覆うのに 1 枚と数える「投影が畳む分」のほうで、点密度を 4 倍にしても判別できる上限は +1.92 しか伸びなかった。*

[![閉形式 2 pi r h + 4 pi r^2 / pi r^2 h + 4/3 pi r^3 と比べる。2 値化を挟むと面積だけが一方向に膨らむ。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crop_phenotyping/01_capsule_calibration_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_crop_phenotyping/01_capsule_calibration.png)

*↑ 測定の図 ―― 閉形式 2 pi r h + 4 pi r^2 / pi r^2 h + 4/3 pi r^3 と比べる。2 値化を挟むと面積だけが一方向に膨らむ。*

```
py -3.11 examples/poc_crop_phenotyping.py
```

ソース: [examples/poc_crop_phenotyping.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_crop_phenotyping.py)

使用 op(ノートへ): [`boundary_vertices`](https://furuse.work/ops/3d/mesh_process/boundary_vertices.html) · [`capsule_sdf`](https://furuse.work/ops/3d/sdf_csg/capsule_sdf.html) · [`dem_slope`](https://furuse.work/ops/dem/surface/dem_slope.html) · [`estimate_normals`](https://furuse.work/ops/3d/curvature/estimate_normals.html) · [`face_areas`](https://furuse.work/ops/3d/mesh_process/face_areas.html) · [`face_normals`](https://furuse.work/ops/3d/mesh_process/face_normals.html) · [`grid_coords`](https://furuse.work/ops/3d/sdf_csg/grid_coords.html) · [`mesh_area`](https://furuse.work/ops/3d/mesh_process/mesh_area.html) · [`mesh_sample_points`](https://furuse.work/ops/3d/resolution/mesh_sample_points.html) · [`mesh_volume`](https://furuse.work/ops/3d/mesh_process/mesh_volume.html) · [`occupancy_grid`](https://furuse.work/ops/3d/occupancy/occupancy_grid.html) · [`plane_segmentation`](https://furuse.work/ops/3d/segment/plane_segmentation.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`sdf_to_occupancy`](https://furuse.work/ops/3d/transform/sdf_to_occupancy.html)

## 114. 人と機械の安全距離 —— 代表点に置き換えた分だけ、危険が消える

[![人と機械の安全距離 —— 代表点に置き換えた分だけ、危険が消える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_safety_clearance/02_frames_clearance_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_safety_clearance/02_frames_clearance.png)

*↑ **人と機械の安全距離 —— 代表点に置き換えた分だけ、危険が消える** ―― 多関節の骨格に太さを持たせた人体(カプセル 10 本)と可動アームを合成し、表面どうしの真の最小分離距離を時刻ごとに閉形式で持たせた場面で、速度分離監視の判定がどこで嘘になるかを数えた。人を重心 1 点 + 半径 0.30 m の球で代表すると危険時に +0.166 m 遠く言い、危険の 14.3 % を見落とす(足元 1 点なら 28.6 %)—— どちらも誤検知はほぼ 0 で、壊れ方は片側にしか出ない。背面カメラ 1 台では危険フレームの 48.6 % で「推定を決めた部位が真の最近傍と違う」ことが起き見落としは 18.1 %、2 台目で 0 % に戻るが、繰り返し性から名乗った不確かさ 0.036 m は遮蔽の偏り 0.178 m の 5 分の 1 しか無い。*

[![危険 = 真の距離 < 0.640 m、停止判定 = 推定 < 0.690 m。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_safety_clearance/01_conditions_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_safety_clearance/01_conditions.png)

*↑ 測定の図 ―― 危険 = 真の距離 < 0.640 m、停止判定 = 推定 < 0.690 m。*

```
py -3.11 examples/poc_safety_clearance.py
```

ソース: [examples/poc_safety_clearance.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_safety_clearance.py)

使用 op(ノートへ): [`annotate3d_label`](https://furuse.work/ops/3d/annotate3d/annotate3d_label.html) · [`annotate3d_measure`](https://furuse.work/ops/3d/annotate3d/annotate3d_measure.html) · [`box_sdf`](https://furuse.work/ops/3d/sdf_csg/box_sdf.html) · [`capsule_sdf`](https://furuse.work/ops/3d/sdf_csg/capsule_sdf.html) · [`chamfer_distance`](https://furuse.work/ops/3d/metrics/chamfer_distance.html) · [`distance_line_line`](https://furuse.work/ops/3d/geometry/distance_line_line.html) · [`esdf`](https://furuse.work/ops/3d/occupancy/esdf.html) · [`face_areas`](https://furuse.work/ops/3d/mesh_process/face_areas.html) · [`hausdorff_distance`](https://furuse.work/ops/3d/metrics/hausdorff_distance.html) · [`query_distance`](https://furuse.work/ops/3d/occupancy/query_distance.html) · [`render_volume_projection`](https://furuse.work/ops/3d/render/render_volume_projection.html) · [`sdf_to_occupancy`](https://furuse.work/ops/3d/transform/sdf_to_occupancy.html) · [`sdf_union`](https://furuse.work/ops/3d/sdf_csg/sdf_union.html)

## 115. パレットの積載率 —— 1 つの数字が「隙間」と「はみ出し」を同じ値にする

[![パレットの積載率 —— 1 つの数字が「隙間」と「はみ出し」を同じ値にする](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pallet_load_utilization/01_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pallet_load_utilization/01_scene.png)

*↑ **パレットの積載率 —— 1 つの数字が「隙間」と「はみ出し」を同じ値にする** ―― 1200 x 1000 mm のパレットに、中身が正反対の 2 つの荷を積んだ。荷 A は上から見えない 400 x 400 x 420 mm の空洞と幅 20 / 50 / 120 mm の隙間だらけ、荷 B は詰まっているが 90 mm はみ出して天端が制限 1800 mm を 100 mm 超える。中段の高さを閉形式で 995.0 mm に解くと、見かけの積載率は 62.65 % と 62.67 %(差 0.02 pt)で一致する——同じ数字なのに A は 3.11 pt が見えない空洞、B ははみ出し 2.10 pt + 高さ超過 0.58 pt で、処置は「積み直す」と「降ろす」で逆。荷を 1 個の外形とみなすゼロ点は荷 B で AABB 113.90 % / OBB 166.44 % と 100 % を超え、真の中身と押し出し形の IoU は 0.9493 と 1.0000 でどちらも「よく合っている」としか読めない。高さマップのセル寸法という 1 つのつまみが逆向きに 2 通り壊し、幅 w の隙間は max(0, 1 - g/w) で消え(g = 40 mm で 20 mm の隙間は完全に消失、g = w ちょうどは位相で全か無かに割れて 5 回に 1 回だけ全部見える)、一方で 1 mm も出ていない荷 A に周長 x g/2 x 天端 の偽はみ出しが立ち、g = 40 mm からは本当に出ている荷 B の 0.0450 m3 を上回る。*

[![測定の図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pallet_load_utilization/02_hidden_void_section_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_pallet_load_utilization/02_hidden_void_section.png)

*↑ 測定の図*

```
py -3.11 examples/poc_pallet_load_utilization.py
```

ソース: [examples/poc_pallet_load_utilization.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_pallet_load_utilization.py)

使用 op(ノートへ): [`aabb`](https://furuse.work/ops/3d/bounds/aabb.html) · [`convex_hull`](https://furuse.work/ops/3d/bounds/convex_hull.html) · [`euclidean_cluster`](https://furuse.work/ops/3d/segment/euclidean_cluster.html) · [`inner_box3`](https://furuse.work/ops/3d/regionprops/inner_box3.html) · [`mesh_volume`](https://furuse.work/ops/3d/mesh_process/mesh_volume.html) · [`voxel_iou`](https://furuse.work/ops/3d/metrics/voxel_iou.html)

## 116. シルエットから体重を測る ―― 台数で買える誤差と、いくら買っても消えない誤差

[![シルエットから体重を測る ―― 台数で買える誤差と、いくら買っても消えない誤差](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/10_scene_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/10_scene.png)

*↑ **シルエットから体重を測る ―― 台数で買える誤差と、いくら買っても消えない誤差** ―― 多視点シルエットの交差(visual hull)から家畜の体積を出し、体重へ換算する。視体積交差は**必ず上界**なので、問うべきは「良いか」ではなく「**必ず上に出る**」ほうだ。★★**閉形式の崖が、現場の目安を訂正した**。「K 台なら K 角形」は正しくない —— 平行投影ではカメラ 1 台が視線に**直交する接線 2 本**を与え(法線は方位 ± 90 度)、しかも**向かい合う 2 台は同じ 2 本**しか与えない。したがって接線の本数は偶数 K なら K 本、**奇数 K なら 2K 本**。結果として **3 台と 6 台は幾何としてまったく同じ**(閉形式 1.16772 / 1.16772、接線の集合が一致。実測差 0.013 は離散化だけ)、**偶数台は半分が無駄**で、**13 台(実測 1.03056)が 16 台(1.04768)に勝つ**。「体重 2 % 以内」を要求すると奇数 **13 台** / 偶数 **24 台**。円の素朴な読み (K/π)tan(π/K) は 13 台と出るので、**偶数台で組む現場は 11 台足りない見積り**を持つことになる。支持関数から出した楕円(a/b = 2.76)の厳密値に対し、近似平行投影(60 m・4.0 mm/px)の実測は**全 K で閉形式のすぐ上**に乗った(K=4: 1.27324 / 1.27528、K=8: 1.11657 / 1.12231、K=24: 1.01790 / 1.02821)—— **下界として的中**し、差は被覆マージンで説明できる。★対照群でこの縮退が**平行投影の性質**だと確かめた: 距離 8 m まで近づけると 3 台 1.20699 / 6 台 1.11211 と差が 7.1 倍に開く。★★この展示の中心は、**カメラを増やして消える誤差と、いくら増やしても消えない誤差を分けて数える**こと。脚の間の幽霊は K=4 → 48 で **7.13 % → 1.37 %**(5.2 倍)と素直に減るのに、**背中のくぼみはカメラを 12 倍にしても 3.8 ポイントしか減らない**(56.4 % → 52.6 %)。分かれ目は「その凹みが**輪郭に出るか**」で、出ない凹みはシルエットにそもそも情報が無い。K=48 で残る +3.4 % の内訳はくぼみ +1.00 % / 幽霊 +1.76 %、真の voxel の**取りこぼしは全 K で 0**(上界であることの確認)。★**前景抽出の 1 画素**も台数では買えない: K=12・4.0 mm/px で **+3.21 %/px**(体重 +23.7 kg)。Steiner の ΔV/V = (S/V)δ の予測 +3.09 %/px と比 1.04 で当たるが、押し上げ要因と押し下げ要因が**偶然釣り合った**結果なので、そのまま一般化しないよう本文に書いた。±3 画素で -8.71 〜 +9.43 %。★**物差しで勝者が入れ替わる**: 体積由来の体重とアロメトリ体重は「K=24 + 2 画素収縮」が最良だが、**重心の高さでは収縮なしの K=24 が勝つ**(細い脚が先に消えて重心が上がる)。3 つの物差しに 2 通りの勝者。★★**予想を外した**: 「巻尺は体に巻くから凸包を測っている。だから胸囲では 3-D 凸包が強いはず」と踏んだが、実測 **+55.2 %** で最悪の部類だった。体全体の凸包は**腹の下を埋める**ので、縦断面が地面まで伸びる —— **『断面の凸包』と『凸包の断面』は別物**。★カメラ配置の対照(上半球ランダム 8 台 対 等間隔 8 台、120 試行)は平均では互角(等間隔以下 57.5 %)だが、**最悪値は +30.20 % で等間隔の 2.4 倍** —— **危ないのは平均ではなく裾**。★★道具の穴を見つけて**その場で埋めた**: 空間彫刻が要求する OpenCV 規約(+Z 前方)の姿勢ヘルパは`fs.` / `fs.op.` / `fs.ledger.` / `op_find('look')`(0 件)の**どこからも引けず**、公開層で `look_at` の名を持つのは render3d の gluLookAt 版(-Z 前方)だけだった。**同じ名前で規約が逆**なので、掴み間違えると全点がカメラ後方に落ち、**例外を出さずに空の hull** が返る(カメラ 0 台は ValueError で fail-closed なのに、規約違いは無言)。`carve_look_at` を台帳に載せて引けるようにし、点が 1 つ残らず後方なら警告を出すようにし、`render3d.look_at` の docstring にも「彫刻には渡すな」と書いた。*

[![真値 0.7238 m^3 / 738 kg。外接直方体と OBB は上界の中でもいちばん粗い。](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/01_null_baseline_720.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/poc/poc_livestock_body_volume/01_null_baseline.png)

*↑ 測定の図 ―― 真値 0.7238 m^3 / 738 kg。外接直方体と OBB は上界の中でもいちばん粗い。*

```
py -3.11 examples/poc_livestock_body_volume.py
```

ソース: [examples/poc_livestock_body_volume.py](https://github.com/furuse-kazufumi/fullseye/blob/master/examples/poc_livestock_body_volume.py)

使用 op(ノートへ): [`carve`](https://furuse.work/ops/3d/space_carving/carve.html) · [`carve_look_at`](https://furuse.work/ops/3d/space_carving/carve_look_at.html) · [`convex_hull`](https://furuse.work/ops/3d/bounds/convex_hull.html) · [`erosion_circle`](https://furuse.work/ops/2d/region/erosion_circle.html) · [`mesh_volume`](https://furuse.work/ops/3d/mesh_process/mesh_volume.html) · [`synthesize_silhouette`](https://furuse.work/ops/3d/space_carving/synthesize_silhouette.html) · [`vol_rle_bbox`](https://furuse.work/ops/3d/rle_region/vol_rle_bbox.html) · [`vol_rle_centroid`](https://furuse.work/ops/3d/rle_region/vol_rle_centroid.html) · [`vol_rle_encode`](https://furuse.work/ops/3d/rle_region/vol_rle_encode.html) · [`vol_rle_volume`](https://furuse.work/ops/3d/rle_region/vol_rle_volume.html)


## 自分の問題に当てはめるには

105 本のうち 99 本は合成データで閉じています。2026-09-08 に**初めて実写を 6 本**入れました(ステレオ対 / コイン / 深宇宙 / 免疫染色 / ブレ取り / テクスチャの回転)。合成の 99 本も、**実データへの差し替え口を最初から決めて書いてあります**。

**1. `EXTEND` の印を探す。** 各スクリプトの docstring に `EXTEND:` で始まる段落があり、「この関数の戻り値をこれに置き換える」と書いてあります。ほとんどの PoC は合成器 1 関数(`make_scene` / `render` / `build_case` など)だけを差し替えれば、ゼロ点・崖の掃引・表の印字はそのまま動きます。同時に「真値が消えるので測れなくなるもの」も書いてあります ―― 手ブレの PoC では実写真だと意味を保つのはリンギングと速度の章だけ、パノラマなら閉ループ誤差だけ、追跡なら往復不一致だけ。**真値なしで測れる絶対量は少ない**ので、そこを先に読んでから撮り方を決めるのが早道です。

**2. op は 2 段で呼べる。** 1 行で済ませたいときは `fs.apply(img, "op名", ...)`、引数の規約まで握りたいときは `fs.ledger.<op名>(...)`。PoC の中で裸のモジュールを直接 import している箇所には「公開経路に出ていない」と注記してあります(それ自体が末尾の「穴」の一覧です)。

**3. 図と使い方は docs サイトにある。** [https://furuse.work/](https://furuse.work/) に op ごとのノート(何をする op か、型契約、罠、関連 op、図)があります。各展示には、その PoC が呼んでいる op のノートへのリンクが付きます。Fullseye Studio を横に開いておくと、PoC が印字した中間結果(マスク、断面、スペクトル)を画像ウィンドウや 3-D 表示で確かめられます。

**4. AI に読ませる。** `pip install fullseye` のあと `fullseye-rag` を 1 回叩くと、op のノート群が Claude Code のスキルとして登録されます。この状態で「この PoC を自分の顕微鏡画像に差し替えて」と頼むと、AI は `EXTEND` 段落と op ノートを読んで差し替え案を書きます。**私が使っている運用はこれ**で、この展示の PoC 群も同じ経路で書き進めました。

---

## 正直な限界

**測っていないもの。** 105 本のうち 99 本は合成データです。実機の記録には、転がり滑り、複数の共振、紙の反り、焦点ブリージング、2 光源の混在といった、ここで仕込んでいない要因が乗ります。各 PoC が出す検出限界や崖の位置は**そのモデル・その条件での上界**であって現場の値ではなく、どの docstring にもそう書いてあります。バーコードとマトリクスコードは実在規格ではないので、読取率を規格準拠リーダの性能として引用してはいけません。改竄検出は防御側だけを扱い、うまく作る方法は含めていません。

**PoC が見つけて直したもの。** CT のランプフィルタが DC ビンで各投影の平均を丸ごと引いていた(質量欠損 -3.34 % → -0.0099 %)。当初「検出器を増やすと改善する」と読んでいたのは取り違えで、363 bin と 511 bin が同じ値を返していたのは両方 FFT のパッド長 1024 に詰まるからでした。地形の天空率が 41.9 秒かかっていたのを、結果 bit 一致のまま 2.03 秒に。DIC で既存の `piv_cross_correlate` を検索が返さず「無い」と書きかけた件は、検索の側を直しました。`mueller_apply` が画像に効かなかった件は broadcast を通しました。

**PoC が見つけたが、op 本体はまだ直していないもの。** カメラ校正・パノラマが公開経路(`fs.` / `fs.ledger` / op レジストリ)から届かない。`h_maxima` の h が正規化画像に対する比なので、大きい細胞が 1 つ入るだけで小さい細胞側の下限が 0.42 → 0.80 画素へ上がる。`vol_label` の既定 26 近傍が寛容側でニアミスを合体させる。`gauss_image` の σ が 0.3〜3.0 に固定、`min_filter` の窓が 3, 5, 7, 9 に固定、局所しきい値の窓が最大 4 px / 15 px でモジュール寸法に届かない。`ncc_locate` が相関マップを返さず突出度が計算できない。`reprojection_error` に歪み引数が無い。2-D 画像を任意倍率でリサイズする op、任意のホモグラフィで歪ませる op、大気散乱の族、統計ベースの光源推定 op、光弾性の族が無い。`polarization_separate` の拡散成分が R_p·E だけ系統的に大きい。**PoC は道具の穴を出すためにある**、というのがこの一覧の言い分です。

---

## 次回に続く

穴の一覧は、そのまま次の作業台帳です。公開経路に出ていない実装を出す、既定値が寛容側の op を締める、窓が固定の op を開ける ―― 1 つ直すたびに、この展示の PoC を走らせ直して数字がどう動くかを見られます。**ゼロ点は動かないはずで、動いたら何かを壊した合図です。**

もう 1 つ気になっていることがあります。通し主題の「逆向きの 2 つの失敗」は、7 つの PoC で別々の物理から出ました。では、実データに差し替えたとき ―― 合成には入っていなかった要因が乗ったとき ―― でも同じ形が出るのでしょうか。それとも合成だから綺麗に釣り合って見えただけなのでしょうか。2026-09-08 に最初の 2 歩を踏みました。出てきたのは**合成では作れない型**の躓きです —— 配布元が「欠測は NaN」と書いた真値の穴が実際は +inf で、nan 系の集計だけが 2.4 px ずれること。既定の探索範囲が実物の目盛りに届かず bad2 が 95 % になること。距離に落とす式に主点オフセットが無く、無視すると**単一の係数では直せない反り**(残差 958 mm RMS = レンジの 33 %)が出ること。そして、**答えが合っていても余裕が 0.05 しかない**こと。逆向きの 2 つの失敗が実データでも釣り合うのかは、まだ 2 本ぶんしか答えがありません。次もそこを歩きます。

---

### 作り手について

問いと方向は私が決め、実装・掃引・対照群の追加・予想の反証は Claude Code に回しました。docstring の「予想が外れた」は、その反証の記録です。

自分の分野の 1 本を走らせて、崖の位置が現場の感覚と違ったら、それがいちばん聞きたい話です。



---

**この展示館は Claude Code と一緒に作りました。** 問いと方向決めは私、実装・掃引・対照群・敵対レビューは Claude Code、という分業です。53 本の PoC を 2 日で走らせて図まで揃えられたのは、この運用のおかげです。試してみたい方は、こちらの招待リンクから **1 週間の無料トライアル** が使えます: [claude.ai/referral/0sqPw8E_lw](https://claude.ai/referral/0sqPw8E_lw)

面白い展示が 1 つでもあったら、**いいね・ストック**をもらえると助かります。どのウィングを次に増やすかは反応を見て決めるつもりなので、「自分の分野のこれが欲しい」もコメントで教えてください。実データに差し替えて崖の位置が変わった話は、いちばん聞きたい話です。
