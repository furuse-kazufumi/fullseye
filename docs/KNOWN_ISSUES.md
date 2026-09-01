# Known Issues — 実データ横断テストで発見(2026-08-30)

学術分野横断サンプル生成(`tools/gen_academic_gallery.py`)で実データ・多様画像を
流した際に見つかった既知バグ/設計ギャップ。「実データは合成では出ないバグ発見器」
の実証でもある。**全 5 件は 2026-08-30 に修正済み**(各項の「修正」参照。回帰テストは
`tests/test_known_issues_fixes.py` + `tests/test_specops_fusion.py`)。発見の経緯は
記録として残す。

検証状態の凡例: ✅=メンテナが最小再現で確認済み / ⚠=発見エージェント報告
(再現手順あり、メンテナ未追試)。

## 1. ✅ `count_obj` が 4 連結(HALCON 非パリティ疑い)
対角接触 2 画素の mask で `count_obj`=2、`segment_objects`(既定 8 連結)=1。
HALCON の `connection` 既定は 8 連結なので `count_obj` 側が非パリティ疑い。
実データでは細胞計数 342 vs 327 等の乖離として現れた。
再現: `m=zeros((8,8)); m[2,2]=m[3,3]=1; fs.apply(m,"count_obj") -> 2.0`
**✅ 修正済み(2026-08-30)**: `count_obj`(backends_auto)と `blob_count`(ops)を
8 連結既定に変更(HALCON パリティ)。旧 4 連結は `_blob_count(..., connectivity=4)` /
spec params `{"connectivity": 4}` で残置。回帰テスト:
`test_known_issues_fixes.py::test_count_diagonal_pair_is_one_object` ほか #1 群。

## 2. ✅ `sk_frangi` が a,b ノブを完全無視
(0.5,0.5)/(0.3,0.8)/(0.8,0.8)/(0.5,0.2) の 4 設定で出力がビット一致。
ノブをスケール範囲等へ配線するか、ノブ無しの契約に直すべき。
**✅ 修正済み(2026-08-30)**: a→sigma スケール範囲(最大 σ 1..5)、b→Frangi 感度
beta(0.15+0.7b)に配線。(0.5,0.5) は旧実装 `frangi(v, sigmas=range(1,4))` と
**ビット一致**を保証(既公開の生成画像を無効化しない)。回帰テスト:
`test_sk_frangi_default_matches_historical_output_bitwise` /
`test_sk_frangi_knobs_change_the_output`。

## 3. ⚠ `gen_contour_region_xld` の境界点がラスタ順(トレース順でない)
隣接点間距離 mean 17px / max 50px。順序前提の
`fourierdesc.elliptic_fourier` に食わせると無警告で崩壊(EFD 再構成が 1 軸に潰れる)。
再現: 楕円 mask → `gen_contour_region_xld` → `fourierdesc.from_xld` → 再構成。
回避: skimage `find_contours`(トレース順)を経由。
**✅ 修正済み(2026-08-30)**: 専用 kind `region_boundary` を新設(skimage
`find_contours` サブピクセル・トレース順、skimage 不在時は自前 Moore 近傍トレース)。
回帰テスト: `test_gen_contour_region_xld_points_are_trace_ordered` /
`test_gen_contour_region_xld_feeds_elliptic_fourier_without_collapse`(EFD 両軸
±25% + IoU>0.8)/ Moore フォールバック 2 件。

## 4. ⚠ registry `clahe` にタイル継ぎ目
タイル間の双線形補間が無く、勾配+ノイズ 512² で col 169/340 に不連続
(近傍差分中央値の 6 倍超)。実画像(星雲)で肉眼でも格子が見える。
`cv_clahe` / `xkor_clahe` は継ぎ目なし — 補間実装を移植するか docs に注記を。
**✅ 修正済み(2026-08-30)**: 標準 CLAHE のタイル間双線形補間(Zuiderveld 1994)を
実装(タイル中心 4 近傍の CDF をブレンド)。回帰テスト:
`test_clahe_tile_seams_are_gone`(境界不連続比が補間前の 1/3 未満かつ <2.5)/
`test_clahe_correlates_better_with_cv_clahe_than_before` /
`test_clahe_still_equalises_locally`(既存 `test_fix_clahe_coverage.py` も維持)。

## 5. ⚠ `spec_decorrelation_stretch` が RGB(B=3)を契約で拒否
考古学定番「RGB 写真への DStretch」がスペクトル op 経路では不可(fail-closed 自体は
正しい)。登録 op `principal_comp` で代替可能なことは確認済み。RGB 受け入れの別名 op
か、エラーメッセージでの `principal_comp` 誘導を検討。
**✅ 修正済み(2026-08-30)**: 設計判断=**RGB を受理**(RGB 写真への DStretch は
Gillespie 1986 以来この手法自身の正典的用途のため、この op のみ `_as_cube(...,
allow_rgb=True)` で B=3 を許可)。B=1・非 3 次元・非有限の fail-closed と、他の
スペクトル op の B=3 拒否(モダリティ境界)は維持。回帰テスト:
`test_specops_fusion.py::test_dcs_accepts_rgb_photograph`(受理+脱相関+平均保存+
他 op は拒否のまま)。

---

# Known Issues — 第 2 波: 2D 古典 op 展示づくりで発見(2026-09-02)

展示(`tools/gen_wing2d_gallery.py`)の作成中に見つかった 10 件。第 1 波と同じく
**例外を出さずに間違った数字・絵を返す**型に絞ってある(この repo はそちらを重く見る)。
うち 4 件は **op の名前そのものが実装と食い違っていた**。全件 2026-09-02 に対処済み。
回帰テストは `tests/test_fix_op_name_and_range_2026_09_02.py`。

## A1. ✅ `highpass_image` / `bandpass_image` / `fft_image_inv` が符号つきを返す
`image` を名乗りながら値域 `[-1,1]` の配列。実測(camera.png, a=0.2,b=0.5):
`highpass_image` min=**-0.6067** / 負 **50.2%**、`bandpass_image` min=**-0.8812** / 負 **49.8%**、
`fft_image_inv` 負 **49.4%**。保存・表示すると **画素の約半分が無言で真っ黒に潰れる**。
真因は **兄弟の間で規約が割れていた**こと —— core の `ops._highpass` は `_signed01`
(零点 0.5)を通していたのに、`backends_auto._sh_freq` は符号を保つ `_norm` を使っていた。
**✅ 修正**: 符号つき応答は `signed01`、非負応答は `_norm` に統一。
`highpass_image` は `highpass` と完全一致(min=+0.1966 / 負 0.0%)になった。

## A1b. ✅ 兄弟一掃 —— `image` を出す op の値域契約が無かった
`region` には全 op 一斉の値域契約テストがあったのに `image` には無く、そこが A1 の抜け道。
全 417 の image-out op を掃いて **7 件**の逸脱を検出:
A1 の 3 件のほか、`xsp_chamfer_dist`(塗り潰し領域で `scipy` の -1 センチネルを距離として
返し **一様 -1 の距離マップ**になる)、`unsharp`(min=-0.1499 / max=+1.1499)、
`sk_adjust_log`(max=1.1380)、`xkor_motion_blur`(float32 の丸めで 1 をわずかに超える)。
**✅ 修正**: 7 件すべて [0,1] に。後半 4 件は `ops._apply` が段間で掛けている clip と
同じなので **パイプライン結果はビット不変**、単発 `fullseye.apply` の白飛び/黒潰れだけが
消える。恒久ガードとして
`test_fix_op_name_and_range_2026_09_02.py::test_every_image_op_stays_in_the_unit_range`
(全 image-out op を parametrize)を追加。

## A2. ✅ `clahe` に clip limit が無く `b` が完全に死んでいた(★名前が嘘)
実測: `max|clahe(x,0.5,0.0) - clahe(x,0.5,1.0)|` が **きっかり 0.0**(`a` は 0.5289 動く)。
CLAHE の "C" は contrast **limited** の C であり、clip limit こそが AHE と CLAHE を
分ける当のもの —— **実装は AHE であって CLAHE ではなかった**。
**✅ 修正**: 標準の切り取り + 全ビンへの再配分(Zuiderveld 1994)を実装し `b` に割当。
`b` はビン平均カウントに対する倍率 `256**b`(`b=0` → 1 倍 = 強調ゼロ、`b=1` → 256 倍 =
切り取り不能 = **旧実装とビット一致**、OpenCV 既定 `clipLimit=40` ≈ `b=0.665`)。
既存 clahe テストは `b=0.0`(死んだ引数)で呼んでいたので `b=1.0`(= 旧挙動)に更新。

## A3. ✅ `estimate_noise` が σ の単位でなく、σ≳0.08 で 1.0 に張り付く
実測(camera.png + `add_noise_white`、σ=0.02..0.22 を 11 点):
`[0.3523, 0.6063, 0.8492, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]` ——
**11 点中 8 点が厳密に 1.0**。`min(1, 1.4826*MAD*3)` の飽和で、しかも σ=0.02 の入力に
0.3523 を返しており単位ですらなかった。
**✅ 修正**: 返り値を **ノイズ σ そのもの**([0,1] 階調)と定義し、
`σ = 1.4826*MAD(∇²x)/√20` に。√20 は 5 点ラプラシアンのノイズ利得(実測で
`1.4826*MAD/σ = 4.4501..4.4816` vs `√20=4.4721`、0.5% 以内)。同じ 11 点は
`[0.0263 .. 0.1920]` で **厳密単調**。上限 1.0 の clip は入力が [0,1] である以上
σ≥1 が起こらないので **到達しない安全弁**であって動作域ではない(docstring に明記)。

## A4. ✅ `zoom_image_factor` / `zoom_image_size` / `rescale_img` が同一実装(★名前が嘘)
実測: `zoom_image_factor` と `zoom_image_size` の最大絶対差 **0.0**、`rescale_img` とは
**4.9e-14**。3 つとも geom `"zoom"` の `s = 0.7 + 0.6a` に相乗りで、3 つとも `b` が未使用。
**別名 op が別物のふりをしていた**。
**✅ 修正**: 役割を分けた —— `zoom_image_factor` は HALCON と同じ **2 つの倍率**
(a=縦、b=横)、`zoom_image_size` は **目標サイズ**指定(出力 shape が
`(round(H(0.5+a)), round(W(0.5+b)))` に変わる、この族で唯一)、`rescale_img` は等方倍率 +
**補間次数**(`b` → `(0,1,3,3)[min(3,int(4b))]`、`b=0.5` は旧既定の 3 次と **ビット一致**)。
`rescale_img` の HALCON 名も実態に合わせて `zoom_image_size` → `zoom_image_factor` に訂正。

## A5. ✅ `area_center` が中心を返さず、面積でなく面積比を返す(★名前が嘘)
中身は `np.mean(mask)`。実測: 420×420 の中の 60×60 ブロック(3600 px)に対し
**0.02040816 = 3600/176400**。名前にある "center" は返らず、面積も画素数でなく比率で
**解像度依存**だった。
**✅ 修正**: HALCON と同じ **(面積, 行, 列)** の 3 成分を返す(`region → match` の
1-D ベクトル、`ncc_locate` と同形)。3 成分とも解像度に依らないよう正規化
(`[0]=面積/画像画素数`、`[1]=重心行/(H-1)`、`[2]=重心列/(W-1)`、空領域は `(0, 0.5, 0.5)`)。
`feature` と `match` はどちらも終端 sort(候補は `identity` のみ)なので
**ゲノム→op の写像は動かない**。★API 破壊: `fullseye.apply(region,"area_center")` の
返り値が `float` から長さ 3 の配列になった(面積だけ要るなら `area_frac`、または `[0]`)。

## A6. ✅ `gabor` の正規化が応答の大小を潰す
実測(96×96 の横縞、周波数 0.25): 生の畳み込みの平均振幅は θ=0° が 0.0165、θ=90° が
0.9077 で **54.9 倍**差なのに、op 経由の平均は 0.3554 対 0.4790 = **1.35 倍**。
`_norm`(その画像の最大絶対値で割る)が向きごとに別の除数を使うため。兄弟の `hx_gabor`
は `_norm01`(min–max 引き伸ばし)でさらに悪く、**順序が逆転**していた(横縞画像で
a=0.5 が 0.34663、ほぼ反応しないはずの a=0 が 0.58434)。
**✅ 修正**: `gabor` / `gen_gabor` / `hx_gabor` を **カーネルの L1 ノルム**で割る固定
スケールに(`|v|<=1` なら `|v*g| <= sum|g|` なので値域 [0,1] は保たれる)。54.9 倍 /
21.0 倍がそのまま残る。向きの規約(**a=0 が縦縞、a=0.5 が横縞**)も docstring とガイドに明記。
**未対処**: `sk_gabor` は向きノブを持たない(skimage 既定 θ=0、`a` は周波数)ため今回の
対象外。いまも画像依存の `_norm` なので **画像を跨いだ絶対比較には使えない**。

## A7. 📝 `rotate_image` / `rotate_img` が reshape=False + mode="reflect"(文書化)
帳票を回すと **四隅に鏡文字が折り返して写り込む**。
**📝 対処 = 文書化(実装は不変)**: この op の正典は「連鎖しても常に同じ形・同じ値域の
画像が出ること」。進化パイプラインは image を段間で無条件に繋ぐので、shape が変わる/
枠外に定数が入ると後段の統計が回転量に依存して動く。鏡映は画像自身の統計を保つので
この用途ではこちらを採る。**deskew には向かない**ことと、背景色で埋めたいときの逃げ道
(`ndimage.rotate(..., reshape=True, mode="constant", cval=bg)`)を docstring に明記した。

## A8. 📝 (x,y) と (row,col) が隣り合っていて取り違えても例外が出ない(文書化)
`imagemorph.morph` / `warp_*` は **(x,y) = (列,行)**、`fourierdesc.from_xld` と XLD 輪郭は
**(row,col)**。どちらも (N,2) float なので取り違えても **例外は出ず**「それらしく間違った」
モーフになる(実測: 中間コマに二重像、affine–TPS 平均差 0.01018 → 正しい (x,y) で 0.00802)。
**📝 対処 = 文書化**: 両モジュールの冒頭に「座標順の落とし穴」節を追加し、橋渡しは
`pts[:, ::-1]` と書くことを明示。

## A9. 📝 `find_shape_model(angles=...)` の `angle` の符号の向きが未文書(文書化)
**📝 対処 = 文書化(実装は不変)**: 返り値は「**テンプレートをこれだけ回すと画像中の
出現に重なる**」角度 = `scipy.ndimage.rotate(template, angle)` に渡す角度そのもの
(実測: `scene = ndimage.rotate(T, x)` を x=-30/-15/0/+15/+30 で探索させると返り値は
x に一致、score 1.000)。画素座標では変位 (dr,dc) が正の角 θ で
`(dr cosθ - dc sinθ, dr sinθ + dc cosθ)` に写る(実測: 真上 (-40,0) が θ=+30° で
(-34.67,-20.06)、閉形式 (-34.641,-20.000))。row 下向き・col 右向きの画面座標では
**反時計回り**なので、「上が 0°・時計回り正」の作図規約でそのまま描くと **鏡像になる**。

## A10. 📝 `apply_cmap` は渡した配列の中で正規化する(文書化)
`vmin`/`vmax` を省くと **その呼び出しで渡された配列の min/max** が両端になる。要素が 1 つなら
min==max なので `normalize` が `hi=lo+1` に倒し、**値によらずカラーマップの下端**が返る
(実測: `apply_cmap([[0.0]])` / `[[0.3]]` / `[[0.9]]` がどれも viridis の
(0.267, 0.005, 0.329))。警告も例外も出ない。同じ理由で複数画像を別々に呼ぶと色スケールが揃わない。
**📝 対処 = 文書化**: `apply_cmap` / `normalize` の docstring に明記し、
`vmin`/`vmax` の明示を促した。

## A11. ✅ `edges_sub_pix` が整数画素座標を返す(★名前が嘘)
`np.where` のインデックスをそのまま返しており、`sub_pix` を名乗りながらサブピクセル精度が
無かった(`docs/FULLSEYE_OP_ARTICLE_SPEC.md` に「ピクセル精度実装」と明記されていた)。
同名 op が **core と backends_auto に二重登録**されていて、レジストリは後勝ちなので実際に
走るのは backends_auto 側 —— A1 と同じ「兄弟の割れ」。
**✅ 修正**: 勾配の法線方向に放物線を当てる古典的なサブピクセル位置決め(Devernay 1995 系)を
**共有ヘルパ**(`backend_safe.subpixel_refine_edges`)にして両方から呼ぶ。実測(真の位置が
列 20.37 の合成ステップエッジ、a=0.2): 旧実装の返す列は {20.0, 21.0} で平均絶対誤差
**0.500 px**、精密化後は {20.324, 20.370} で **0.0228 px**(約 22 倍)。点の個数・連結成分の
分け方は不変。非極大抑制はしていないので太いエッジでは帯の全画素が稜線に寄って重なる
(1 画素幅の連鎖は `canny`、より高精度な等値線は `threshold_sub_pix` = 実測 0.001 px)。
