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

展示(`tools/gen_wing2d_gallery.py`)の作成中に見つかった 12 件(報告された 10 件 + 兄弟一掃で出た A1b + 名前の嘘に加えた A11)。第 1 波と同じく
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

**兄弟一掃(未対処・報告のみ)**: 同じ「飽和する [0,1] 指標」を返す仲間を同じ条件で掃いた(平坦画像 + ガウス雑音 192×192、σ=0.01..0.30 を 11 点)。
`estimate_noise` は修正後 **0/11** が飽和(0.0099 .. 0.2922 で σ を 1:1 に追う)。
いっぽう `xsk3_estimate_sigma`(×5 正規化)は **4/11**、`xcv2_lap_var`(min(1, ·×20))は **9/11** が厳密に 1.0 になる。
この 2 つは σ ではなく「正規化された指標」を返す契約で、倍率も family guide に明記されている(= 黙ってはいない)ため今回は触っていない。ただし現実的な雑音域の大半で飽和するので、指標として使う場合は上端に張り付いていないか確認すること。

## A4. ✅ `zoom_image_factor` / `zoom_image_size` / `rescale_img` が同一実装(★名前が嘘)
実測: `zoom_image_factor` と `zoom_image_size` の最大絶対差 **0.0**、`rescale_img` とは
**4.9e-14**。3 つとも geom `"zoom"` の `s = 0.7 + 0.6a` に相乗りで、3 つとも `b` が未使用。
**別名 op が別物のふりをしていた**。
**✅ 修正**: 役割を分けた —— `zoom_image_factor` は HALCON と同じ **2 つの倍率**
(a=縦、b=横、中心固定)、`zoom_image_size` は **目標サイズ**指定(画像全体を
`(round(H(0.5+a)), round(W(0.5+b)))` 画素へリサンプルしてキャンバス左上に配置)、`rescale_img` は等方倍率 +
**補間次数**(`b` → `(0,1,3,3)[min(3,int(4b))]`、`b=0.5` は旧既定の 3 次と **ビット一致**)。
`rescale_img` の HALCON 名も実態に合わせて `zoom_image_size` → `zoom_image_factor` に訂正。

**副産物の発見**: 最初は目標サイズそのものを返す実装にしたところ、`test_evolution_honesty.py::test_evolve_is_reproducible_given_seed` が
`operands could not be broadcast together with shapes (70,50) (64,64)` で落ちた。「image/region op は **キャンバス shape を変えない**」というこの registry の
不変量が、どこにも書かれておらずテストも無いまま効いていたことが分かった(非正方入力で全 op を掃いた例外は `transpose_region` と `it_change_format` の 2 つだけ)。恒久ガードとして `test_image_and_region_ops_keep_the_canvas_shape` を追加した。

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
モーフになる。実測(96x96、円盤 A(30,30) -> B(62,66)、12 点の対応点、alpha=0.5): 同じ対応点で affine と TPS を掛けたときの平均差が、(row,col) を渡すと **0.00488**、正しく (x,y) に直すと **0.00260** —— 座標順を間違えると 2 つの補間法が別々の場所へワープするので食い違いが約 1.9 倍に開く。
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

---

# 構造的な既知課題と対策 — fail-soft の 3 層沈黙(2026-09-02 監査 → 09-03 対策)

2026-09-02 の堅牢性監査(8 本の並列監査 + 4417 テストの偽安心監査)で分かったこと:
**個々のテストの質は高い(真正 assertion-only 0.14%)のにバグが残る**のは、fail-soft が
3 層に重なって失敗を沈黙させる構造だった。確定バグ 7 件中 6 件が「例外を出さず黙って
間違う」型。

| 層 | 以前 | 問題 |
|---|---|---|
| facade `fullseye.apply` | ほぼ例外を出さない | 1-D 配列を画像 op に渡しても何か返る |
| GPU 分岐(`device="cuda"`) | `except Exception: pass` | 壊れたカーネルも CPU 結果に化ける(CI は CUDA 不在=GPU 実効カバレッジ 0%) |
| backend ラッパ `_safe` | 24 家族中 **1 家族だけ**が記録・strict 対応 | 永久に壊れた op と「働く恒等」が区別不能 |

## 対策(TRIZ: 信頼性 #27 vs 検出性 #37 の矛盾を「分離」で解く)

「落ちない」と「壊れが見える」をどちらかに倒すのではなく分離した(設計の対応表は
`docs/design/TRIZ_DESIGN_PATTERN_MATRIX.md`):

- **空間分離 / #24 仲介**: 記録・strict・sanitize を `backend_safe.guard()` に一元化。
  23 本の backend の `_safe` は全部これに委譲(`__fullseye_guarded__` マーカー付き)。
  backend モジュール自体の import 失敗も `ops.FAILED_BACKENDS` と台帳に残る。
- **条件分離 / #35**: `apply(..., on_error="fallback"|"warn"|"raise")`(既定は互換の
  `fallback`、`FULLSEYE_ON_ERROR` で一括変更)。`raise` は fail-closed。
- **時間分離 / #11 緩衝 + #32 可視化**: 既定経路でも op ごとに **1 回だけ**
  `FullseyeFallbackWarning` を出す(長いバッチを警告で埋めない)。
- **#23 フィードバック / #22 災い転じて福**: `fullseye.fallbacks()` /
  `fallback_counts()` の台帳が「死んだ op の監査」そのもの(8 本の Agent でやった仕事が
  常設化)。台帳の出所は `op` / `gpu` / `input` / `import` の 4 種で区別。
- **#1 分割**: GPU 分岐は「torch/accel 不在(ImportError)= 静かに CPU」と「カーネル失敗
  = 記録・strict なら送出」を分けた。
- 併せて facade の穴 2 つを塞いだ: 多入力 op(`tier == "nary"` 17 件)は
  `apply([x1, x2], name)` で呼べる(以前は一覧に載るのに `KeyError`)/ テンプレート
  マッチは `apply(img, "ncc_locate", template=T)` で設定できる(以前は内部 API のみで
  常に `[0,0,0]`)。HALCON 別名が複数 op に共有され正規 op が無い 2 件(`emphasize` /
  `points_harris`)は登録順でなくテーブル `api._ALIAS_CANONICAL` で解決(新しい曖昧
  別名はテストで fail)。

Codex(読取専用)の敵対レビューで追加した 2 巡目: strict は **thread-local**(別スレッドの方針を
汚さない)/ `record()` は `__str__` が壊れた例外でも落ちない / `warn` は呼び出し 1 回につき
1 警告(初回の二重発火なし)/ ブレーカー open でも `on_error="raise"` は GPU を再試行して送出 /
入れ子リストは従来どおり画像(n-ary 分岐は **op 名**で選ぶ)/ n-ary 本体も guard 経由 /
core op(ops.py)の例外も facade 境界で記録→型に合う fallback(`raise` では送出)/
最初の家族数調査が取りこぼした **`backends_macro` と `backends_typed` の 2 家族**も記録化
(typed の「型の嘘」分岐も記録)/ optional import の破損は `source="import"` で台帳へ。

回帰テスト: `tests/test_fallback_policy.py`(28 件)。`tests/test_backends.py` の
旧 API(`swallowed_errors` / `last_error` / `strict_mode`)は別名として維持。

---

# 2026-09-05 — 全 op に説明を書く作業で見つかった「名前と実装のずれ」

説明が無い 787 op に説明を書く過程で、**実装を読んだら名前や HALCON 対応が
約束していることをしていない** op が出てきた。説明の側は実装に合わせて正直に
書いた(近似は近似と書く)ので、ヘルプは嘘をつかない。**コードの側はまだ直して
いない** —— 挙動が変わる修正で、既に公開した生成画像の再現性に触れるため、
`sk_frangi` のときと同じく「既定値でビット一致」を保証した上で 0.1.8 で入れる。

検証状態の凡例は上と同じ。**15 件すべてを最小再現つきで追試した**(2026-09-05、別エージェントによる敵対的検証)——
13 件がそのまま確認、2 件(#19 / #23)は列挙の一部が誤りで上のとおり訂正、完全な誤りは 0 件。
ノブが効かない系は **0.0 と 1.0 を含めて端から端まで**振って確かめている(中間 2 点だけだと丸めで一致することがある)。

## 12. ✅ `_trans_to_rgb`(color)は HSV からの逆変換に固定
名前と HALCON 対応(`trans_from_rgb` の逆)は「任意の色空間 → RGB」を示唆するが、
実装は `cv2.COLOR_HSV2RGB` 固定で、Lab / YUV / XYZ からの逆変換が無い。
**対処案**: 色空間を `a` で選ぶ(既定 = HSV でビット一致)か、op 名を
`hsv_to_rgb` に寄せる。

## 13. ✅ `_edges_color`(color)は Di Zenzo 1 種類、`a`/`b` が未使用
HALCON の `edges_color` は Canny / Deriche / Shen を選べるが、実装は Di Zenzo
法のみ。ノブが 2 つとも効かない(`sk_frangi` #2 と同じ型の不具合)。

## 14. ✅ `_edges_color_sub_pix`(color)にサブピクセル補間が無い
名前は「サブピクセル精度」だが、実装は整数格子上のラベリングまで。
**対処案**: 勾配のパラボラ当てはめを入れるか、名前から `_sub_pix` を外す。

## 15. ✅ `_lines_color`(color)は線幅を返さない
HALCON の `lines_color` は線の幅を出すが、実装は輪郭点だけ。

## 16. ✅ kornia 系のノブが一部死んでいる
`xkor_gftt` / `xkor_hessian` / `xkor_dog`(共通ヘルパー `_resp`)と `xkor_unsharp`
で `a`/`b` の一部または全部が実質未使用。`xkor_motion` は `a` が
**カーネル長と角度の両方**を同時に振っており、独立に指定できない。
**対処案**: #2 と同じ手当て(既定でビット一致を保った配線)。

これらは「ヘルプが実装より立派なことを言う」状態を作る種でもある。
説明を書く作業が検出器として働いた、という記録として残す。

## 17. ✅ 別名で登録されているが実装が同一の op が 4 件
`power_ln` と `fft_generic`、`thinning_golay` と `thinning_seq` は spec 上は別の
HALCON 名だが、`backends_auto.py` 内では**同じ shape / 同じ kind** に落ちる
= 実装が完全に同一。抽選の二重取り(`ops.DROPPED_DUPLICATES` で潰した同名衝突と
違い、名前が違うので de-dup に掛からない)になっている。説明には同一である旨を
明記した。**対処案**: 一方を本来の演算に寄せるか、別名であることを台帳に出す。

## 18. ✅ `robinson_dir` だけ返り値の意味が違う
`sobel_dir` / `frei_dir` は `arctan2` の連続角度を返すが、`robinson_dir` は
8 方向カーネルの argmax インデックス(離散)を返す。名前が揃っているぶん
見落としやすい非対称。説明に明記した。

## 19. ✅ 多値を返す HALCON 演算を 1 スカラーに潰している
`connect_and_holes` / `elliptic_axis` は HALCON 側が複数値(ベクトル)を返すが、
この backend の `feature` sort は 1 スカラーしか運べないため情報が落ちている。
**訂正**: 最初の報告は `fill_up_shape` も同列に挙げていたが、これは誤り ——
`fill_up_shape` の `out_sort` は `region` でスカラーではない。この op の限界は
別種で、「面積の上限だけで穴を選別し、円形度など他の形状特徴が使えない」。**対処案**: `reprconv` の型を使うか、成分ごとに op を分ける
(memory: 混ぜると例外でなくもっともらしく間違う型は分ける)。

## 20. ✅ `vol_erode` / `vol_dilate` の `a` が実質 2 値スイッチ
サイズ式が `1 + 2*(1 + int(a))` で、`decode()` が `a` を [0,1] にクリップするため
**`a == 1.0` のときだけ 1 段階変わる**。連続パラメータとして機能していない
(`vol_dilation_ball` 系は `int(a*3)` を使っていて正しく効く)。#2 と同じ型。

## 21. ✅ `vol_median` は `a`/`b` を完全に無視(窓サイズ 3 固定)
2-D 版 `median` が `_k(a)` で窓を振るのに対し、3-D 側は固定。

## 22. ✅ `identity` は複製しない
HALCON の `copy_image` はメモリを複製するが、実装は入力配列をそのまま返す。
下流が破壊的に書き換えると呼び出し元の配列まで変わる。

## 23. ✅ 同一実装に落ちる HALCON 別名がもっとあった(#17 の続き)
SEED 表の実装読解で追加判明: `pow_image`/`gamma_image`、`median_separate`/`median_image`、
`rank_rect`/`rank_image`、`watersheds_threshold`/`watersheds`、
`regiongrowing_mean`/`regiongrowing`、`anisotropic_diffusion`/`coherence_enhancing_diff`、
`bilateral_filter`/`guided_filter`、`power_byte`/`fft_image` が、この backend では
**同じ shape/kind に落ちて区別されない**(実測でビット一致)。HALCON 上は別演算子。
**訂正**: 最初の報告は相方を `isotropic_diffusion` と書いていたが誤りで、正しくは
`anisotropic_diffusion`。`isotropic_diffusion` との差は実測 max|Δ| = 0.614 で別実装。
(この書き間違いは報告を書き写した側 —— 出荷される op の説明の方は正しかった。)

## 24. ✅ `min_max_gray` は最大値しか返さない
名前に反して最小値を計算していない。`feature` sort が 1 スカラーしか運べない
制約(#19)の現れでもある。

## 25. ✅ `height_width_ratio` が `min(1, height/width)` で飽和する
高さ > 幅 の領域では常に 1.0。縦長を区別できない非対称な実装。

## 26. ✅ `a`/`b` が完全に未使用の op(固定変換)
`polar_trans_image` / `polar_trans_image_inv` / `transpose_region` /
`polar_trans_contour_xld` ほか。#2・#13・#16・#20・#21 と同じ型で、
**ノブがあるのに効かない**。0.1.8 でまとめて棚卸しする。

---

# 2026-09-05(後半) — 読んで作った一覧と、測って作った台帳の関係

上の #12〜#26 は**実装を読んで**見つけたもの。0.1.8 で**測る仕掛け**
(`tests/test_op_knob_liveness.py` / `op_probe.py`)を入れたので、
両者の関係を明記しておく —— **数字の意味が違う**。

## ノブ(`a` / `b`)の全体像(実測、2026-09-05)

| | 個数 | 割合 |
|---|---:|---:|
| ノブの総数(881 op × a,b のうち測れたもの) | 1,762 | 100% |
| **実際に効く** | 719 | 41% |
| 効かない & 説明も「未使用」と書いてある | 1,017 | 58% |
| **効かない & 説明は「振る」と書いてある(= 嘘)** | **26** | 1.5% |

最後の 26 が `tests/test_op_knob_liveness.py` の固定対象。内訳は
**19 が純粋な「死んだノブ」**、7 は「入力を変えても出力が変わらない op」
(ノブ以前に動いていない。別カテゴリ)。

## 2 つの一覧が重ならない理由

KNOWN_ISSUES #12〜#26 が名指しする 47 op と、測定台帳の 19 件は
**1 件も重ならない**。矛盾ではなく、見ているものが違う:

* **測定台帳** = 「説明の主張」と「実測の挙動」の**食い違い**。
  効かないノブでも、説明に「未使用」と正直に書いてあれば通る。
* **KNOWN_ISSUES** = 「名前や HALCON 対応が約束していること」と
  「実装がしていること」のずれ。ノブが死んでいる件(#13/#16/#20/#21/#26)は、
  0.1.7 で**説明を実装に合わせて正直に書き直した**ので、測定台帳には出ない。

つまり **1,017 件の「正直に未使用」の中に、本来は効くべきノブが埋まっている**。
測定台帳はそれを見つけてくれない —— 見つけるのは「この op は本来何を
調整できるべきか」という設計の問いで、機械には出せない。
KNOWN_ISSUES 側が引き続きその一覧になる。

## 0.1.8 で直したもの(#12〜#26 とは別口)

- 0 サイズ入力での**プロセス死**(`xpil_offset`、Pillow のネイティブ側)
- **未ガードの 395 op** —— fail-soft の契約が掛かっていなかった。
  空入力での NaN 流出 14 件はこれが原因で、登録時に一律で包んで 0 件になった
- **非有限が意味を持つ op を潰していた**(`tb_geodesic_distances` の
  不達 inf → 1.0。到達可能な最大距離より小さい値に化けていた)
- **ファザーの種の二重定義**(`"rgbimage"` ほか 3 組)—— 意図のある生成器が
  黙って死に、鏡面分離 op 2 本が「永久に失敗」と誤認されていた
- 到達不能な**未定義名 5 件**(1 件は走れば `NameError`)
- ★**全 NaN でのプロセス死(2 本目)** —— `xsk2_reconstruction` /
  `xsk2_h_maxima`(`skimage.morphology` のネイティブ側で SIGSEGV)。
  **単独では落ちず、交互に呼んだときだけ落ちる**(ヒープ破壊)。
  `backend_safe.require_finite()` で入口に関門を置いた
- ★**退避値そのものが非有限だった** —— `fallback()` の image/color 系は
  `np.clip(入力, 0, 1)` で、`np.clip` は NaN を通す。**入力が非有限のときだけ**
  「返り値は有限」の約束が破れていた(`_clip01_finite()` に集約)
- ★**全 NaN の位相でハング** —— `xsk_unwrap_phase`(実測 5 分以上)。
  非有限をマスクして解決。有限入力に対する出力はビット単位で不変
- **順序依存 1 件** —— `tests/test_accel_match.py` がテンプレートを大域に残していた。
  直列では 100% 緑、`-n auto` で落ちる。週次 `order-shuffle` ジョブを追加

## まだ直していない(0.1.9 以降)

#12〜#26 のコード修正(ノブの配線・サブピクセル補間・多値型)。
いずれも既定出力が変わるので、`sk_frangi`(0.1.3)と同じく
「既定値でビット一致」を保証できるものから順に入れる。
`vol_median` / `xkor_motion` / `identity` は wave0 の pin に載っているので、
pin の更新を 1 件ずつ判断すること。


## 27. ⚠ `hx_test_self_intersect` が O(n²) の総当たり(実測 276 万回呼び出し)

プロファイラ 3 種(pyinstrument / cProfile / py-spy)が**独立に同じ場所**を
最上位ホットスポットとして指した —— `backends_halcon_ext.py` の
`_test_self_intersection_xld` が全セグメント対に `ccw()` を掛けている。
`tests/test_op_knob_liveness.py`(約 31 秒)の中で **`ccw` が 2,760,000 回**
呼ばれていた。呼び出し回数を出せたのは cProfile だけ(サンプリング型の
2 つは「そこにいる時間」しか出さない) —— **道具ごとに見えるものが違う**。

正しさの問題ではなく速さの問題。直し方は 2 通り:

* **numpy で総当たりをベクトル化**(数式は同じなので**出力はビット一致**にできる)。
  安全だが、点数の 2 乗のメモリを使うので上限が要る
* 掃引線 / 空間索引に替えて O(n log n) にする。速いが実装が重く、
  数値の縁で結果が変わりうる

0.1.9 でベクトル化から入る(ビット一致を確認できる方から)。

## 28. ⚠ memray / scalene が Windows で入らない(道具側の制約)

どちらも PyPI に Windows 向けの prebuilt wheel が無く、sdist からのビルドに
失敗する(memray は `pkg-config` 不在、scalene は VS Build Tools はあるのに
`distutils` の検出ロジックで別の失敗)。メモリのプロファイルが要るときは
WSL 側で測るか、`tracemalloc`(標準ライブラリ)で代替する。
詳細 = `<ローカルの作業パス>`。


## 29. ⚠ 「配線できるのに固定している」箇所が 18(0.1.9 の作業表)

測定台帳は「主張と実測の食い違い」しか見ないので、**「未使用」と正直に書いた
ノブ 1,017 個**の中に埋まっている「本来は効くべきノブ」を出せない。
そこで別の機械化をした —— **op の実装を AST で読み、呼んでいるライブラリ関数に
``a``/``b`` に依存しない数値を渡している箇所**を挙げる
(`scratchpad/knob_candidates.py`。境界処理・軸・dtype など「規約」の引数は除外)。

結果: **18 箇所**。多分岐の shape 関数は内部で分かれるので、
「その関数から作られる op 数」は上限であって実際に通る数ではない。

| 箇所 | 固定値 | 判断 |
|---|---|---|
| `backends_auto._sh_xld` (lines_gauss 分岐) | `frangi(sigmas=range(1,4))` | ★**配線する**。下記 |
| `backends_auto._sh_segment` | `chan_vese(max_num_iter=60)` | 反復回数。配線候補 |
| `backends_auto._sh_geom` | `swirl(radius=30)` | 幾何半径。配線候補 |
| `backends_auto._sh_cooc` | `graycomatrix(angles=[0.0])` | **1 方向しか見ていない**。テクスチャ特徴としては弱い |
| `backends_auto._sh_diffusion` | `denoise_nl_means(patch_size=5)` | 配線候補 |
| `backends_extra._watershed_markers` | `dilate(iterations=3)` | 配線候補 |
| `backends_filters2.f2_shock` | `grey_dilation/erosion(size=3)` | 配線候補 |
| `backends_ski2._hog` | `orientations=8` / `cells_per_block=(2,2)` | 配線候補 |
| `ops._vol_median` | `median_filter(size=3)` | #21 と同じ |
| `ops._convex_fill` / `_reg_close` | `binary_closing(border_value=1)` | **規約**。ノブではない |
| `backends_regions2` 2 件 | `binary_erosion(border_value=0)` | **規約**。ノブではない |
| `backends_halcon_ext._histo_to_thresh` | `histogram(range=(0.0,1.0))` | **画像の契約**。ノブではない |
| 同上 | `histogram(bins=64)` | 配線候補(量子化の粗さ) |
| `backends_xldgeom.xg_elliptic_axis` | `_fin(default=1.0)` | fallback の既定値。ノブではない |

★**兄弟コードの取りこぼし**: `sk_frangi` は 0.1.3 で
「`a` を σ のスケール範囲へ配線し、`(0.5,0.5)` は旧実装とビット一致」と直した。
**同じ `sigmas=range(1,4)` が `backends_auto` の xld shape に残っていた** ——
バグを 1 件直したら同クラスを兄弟コードで一掃する、を怠った跡。
`lines_gauss` は `a` がしきい値(`0.1+0.4a`)で埋まっているが **`b` が空いている**
ので、`sigmas=range(1, 2+int(round(b*4)))` にすれば **`b=0.5` で現行とビット一致**、
かつ `b` が生きる。

## 30. 配線の隠れコスト —— 説明を直すと訳が 5 言語ぶん無効になる

ノブを配線すると、その op の説明の「``b`` は未使用」が嘘になるので書き直す。
ところが `docs/i18n/op_summary.json` の訳は**原文の指紋**で紐づいているので、
原文を 1 文字でも変えるとその op の訳 5 言語が自動的に「未訳」へ落ちる
(古い訳を黙って出さないための設計で、これは正しい挙動)。

つまり **1 op の配線 = コード + 説明 + 訳 5 本**。
だから配線は**まとめてやる** —— 全部直してから、触れた op だけを 1 度に訳し直す。
1 件ずつ直して都度訳すと、6 言語 100% の状態が何度も崩れる。


## 31. 持ち越し —— 「0.1.8 で直す」と書いた #12〜#27 は 0.1.9 でも未修正

配線(#12〜#26)と O(n²)(#27)は **0.1.10** に送る。理由は #30(配線 1 op = コード +
説明 + 訳 5 本、まとめてやる)。ここに書いておかないと「直す」と書いたまま消える。

## 32. ⚠ 全域レビュー(2026-09-05、Fable)で確認したが 0.1.9 では直していないもの

各行は**再現済み**(自分で走らせて数字を確認)。直し方の方向だけ書く。

| # | 何が起きるか | 場所 | 方向 |
|---|---|---|---|
| 32-1 | 3-D 347 op の RAG ノートが docstring **1 行目のみ**(283 op が複数行、25 op は文の途中で切れる) | `ops3d.py` 786 付近 `splitlines()[0]` | 生成器を全文へ。指紋は 1 行目のままにするか要判断 |
| 32-2 | wheel 同梱 `OP_CATALOG.md` に台帳 19 族 343 op + n-ary 16 op が無い | 生成器が 5 レジストリしか読まない | `typed_catalog.catalog()` を読ませる |
| 32-3 | `docs/OP_INDEX.json` が 2026-08-12 で停止(538 vs 881)なのに「自動追従」と案内 | README / AI_RAG_GUIDE | 生成に組み込むか、案内を消す |
| 32-4 | `_NDIM_OK` が image/region に 3-D を許し、RGB (H,W,3) を 2-D op に渡すと体積として処理して無警告で返す | `api.py` 1226 | `image` は ndim==2 を要求(色は rgbimage/color sort へ) |
| 32-5 | `calib.camera_calibration` の縮退ゲートが近縮退+雑音を通し、fx が +16% でも RMS 0.13 px | `calib.py` 167-172 | RMS は K の誤りを反映しない(#caltab と同型)。条件数で見る |
| 32-6 | 角度の符号が HALCON と鏡像(1-D measuring / XLD / geometry 系)、同 repo の `hom_mat2d_rotate` とも逆 | `backends_measure1d` / `backends_xldgeom` | 既定出力が変わる → 0.2.0 の候補。まず文書化 |
| 32-7 | `fit_sphere3`(Kåsa)が浅いキャップで半径 −7%、rms は雑音レベルで無警告 | `measure3d` | 幾何フィット(Pratt/Taubin)へ、または docstring に限界を |
| 32-8 | `measure3d` の縮退ゲート(相対 1e-9)が近平面で r=38096・rms=0 を通す | `measure3d` | 条件数ゲート |
| 32-9 | `measure_pos(sigma=0)` が硬い段差を 0 本 | `measuring1d` | sigma=0 を最小 0.5 に |
| 32-10 | `fit_cylinder_ransac` が最良仮説をリフィットしない | `pcseg` | inlier で再最小二乗 |
| 32-11 | Studio の `for N` に上限が無く、Apply が O(N²) で GUI を凍らせる(停止手段なし) | `studio.py` 1537 / 269 | 上限 + 増分再計算 |
| 32-12 | OpenCV の「楕円」構造要素が 5×5 以上で横長(cv_ morphology 7 op が説明と違い異方) | `backends.py` `_se` | 説明に書くか、自前 SE に |
| 32-13 | 8bit 経路で 256 階調に落ちる 34 op のうち 19 本が説明に未記載 | xpil 11 / xcv 4 / 他 4 | 説明に「8bit を経由」を追加 |
| 32-14 | 一部 NaN で `_norm` が正規化を諦め image sort が [0,1] を超える(16 op) | `_norm` | NaN を除いた最大で正規化 |
| 32-15 | `wavefront_from_opd` の Zernike RMS が直接 RMS より 10% 低い(瞳半径 31.5 vs 32) | `raytrace` | 瞳半径の定義を揃える |
| 32-16 | ~~Linux CI の A 群 / B 群~~ **2026-09-05 に両方解消**。A = `requires_backend` 宣言 + py3.11 に実 backend 投入 + `FULLSEYE_REQUIRE_OPTIONAL` / B = 原因は「機械をまたぐフォント差」ではなく **CI に CJK フォントが 1 つも無かった**こと。`fonts-noto-cjk` を入れて Linux 124/124 緑 | — | 解消済み |
| 32-17 | **多コア機で SVD 系 op が遅い**(BLAS のスレッド過剰割り当て)。実測(WSL / 24 論理 CPU、`np.linalg.svd(full_matrices=False)`、**他の負荷を止めた状態**): 48x48 = 1 スレッド 0.0002s / 4 スレッド 0.0002s / **24 スレッド 0.0054s(27 倍)**、96x96 = 24 倍、192x192 = 13 倍、384x384 = 3.5 倍、768x768 = 0.135s / 0.093s / 0.398s(2.9 倍)。**4 スレッドまでは無害**(768 では 1.5 倍速い)。`dc_rpca_lowrank` は 1 回で 39 SVD を回すので、Linux で進化系テストが**タイムアウトした**。GitHub runner は 4 コアなので顕在化せず、**開発機とワークステーションだけが遅い**。★正直な注記: 最初の測定は自分が放置した探針プロセス 3 本が 3 コアを占有した状態で取ったもので、比率を 2〜3 倍過大に出していた(48x48 で 83 倍 → 実際は 27 倍)。負荷を止めて測り直した値が上記 | `fsthreads.py`(新設) / `backends_decomp.py` | **2026-09-06 修正**。(b) を採用し、分解の周りだけ短辺に応じて絞る(`fsthreads`、既定で有効・`FULLSEYE_BLAS_THREADS=off` で停止)。(a) は**採れなかった** —— `fssystem` の表に載せられるのは「厳しくする方向のみ」か「数値に一切影響しない」パラメータだけで、`tests/test_fssystem.py` が機械で強制している。スレッド数は下位ビットを動かすので条件を満たさない。選び方は 92 升の格子で採点した: 何もしないと 3975ms 損(最悪 19.91 倍)、短辺 `<512:1 <1024:4 else:8` で 303ms(最悪 1.41 倍)。要素数と長辺は合計では勝つが最悪が 2.50 / 3.89 倍で、平均より最悪を採った。実効: `dc_rpca_lowrank` 128² が 49.8ms → 12.3ms(**4.04 倍**)、結果の差は 5.9e-15(下位ビットのみ)。絞り忘れは `tests/test_blas_thread_discipline.py` が実際に流して数える(壊すと `backends_decomp.py:_rpca` を名指しで落ちることを確認済み)。★副産物: スレッド数は論理 CPU 数から決まるので、**何もしない状態のほうが機械ごとに違う下位ビットを出していた**。上限を固定したことで再現性は上がった |

**確かめて問題なかったこと**(レビューが数字つきで確認): 半画素の原点規約、Seidel 閉形式比
1.00000、Sellmeier、Welzl、箱の軸規約、訳 1,722×6 で stale/欠落 0・繁簡混入 0・
Umlaut 潰し 0、相対リンク 29,153 中不備 1、HTML href 149,664 全実在、入力の in-place
改変 0、転置等変性で (x,y) 取り違え 0。

## 33. ⚠ `observe_surface` の既定引数が 117 秒(2026-09-06、未解決)

「一行で使える入口」と銘打った `optscene.observe_surface` は、既定
`resolution=(256, 256)` / `supersample=2` で **116.93 秒**かかる。実測:

| resolution | supersample 1 | supersample 2 |
|---|---|---|
| 32 x 32 | 0.25 s | — |
| 64 x 64 | 0.69 s | — |
| 128 x 128 | 2.40 s | 19.10 s |
| 256 x 256 | 19.12 s | 116.93 s |

画素あたりの費用が一定でない(32 → 256 で画素は 64 倍、時間は 76 倍)。
プロファイルの内訳は `_light_background` が 16.2 秒中の 11.0 秒で、面光源
196 点 × 鏡面候補 25 回の二重ループ。

**試したが効かなかった案**: 発光点をチャンクでまとめて `einsum` にする書き換え
(相対差 4.3e-15 で一致)は **1.3 倍**にしかならなかった。律速は Python の
ループ回数ではなく**メモリ帯域**で、M=65536 の (k, M, 3) 一時配列を作る費用が
そのまま乗る。速くするなら発光点の間引き(`_thin_emitters` は既にある)を
鏡面候補側にも効かせるか、鏡面候補 25 回そのものを減らす必要があり、
どちらも見え方を変えるので測ってからでないと入れられない。

**当面の扱い**: docstring に費用表を書き、「試すときは `(64, 64)` /
`supersample=1`(0.69 秒)で呼べ」と明記した。連鎖ファザーは
`typed_catalog.OP_PARAM_HINTS` で 32 x 32 / 1 に固定(型と契約の検査に
2 分は要らない)。**既定値そのものは変えていない** —— 変えると同じ引数で
撮った過去の絵と比べられなくなるため、画質の既定を動かすのは別の判断。

## 34. カラー画像を「3 本目の空間軸」として扱う op が 89 本ある(契約が未決)

**症状**: `(H, W, 3)` を 2-D 画像用の op に渡すと、近傍演算が**色を跨ぐ**。
`_NDIM_OK["image"] = (2, 3)` が 3-D をわざと通しているが、中の実装は
`ndimage.*` を素通しするので「高さ 3 の体積」として畳み込まれる。

**どう数えたか(探針を 1 度作り直している)**: 最初は「R にだけエッジを置き、
出力の G が 0 でなければ漏れ」と数えたが、これは誤り —— `invert` は 0 を 1 に
写すので、漏れが無くても G は 1.0 になる。作り直した探針は因果の形で、
**R と G を両方の入力で 0 と 1 を含むよう固定**(正規化が配列全体の最大で割る
ため、min/max が動くと漏れ無しでも R が動く)し、**B の中身だけ**を `(0,1)` の
内側で 2 通りに変えて R の出力が動くかを見る。

2026-09-06 の全数計測(882 op のうち RGB の形のまま返る 472 op):

| | 本数 |
|---|---|
| 色を跨がない | 372 |
| **色を跨いだ** | **100** |
| 形が変わる(特徴量・輪郭など) | 370 |
| 例外 | 43 |

跨いだ 100 本の宣言入力型は image 78 / region 11 / volume 4 / color 3 /
rgbimage 2 / video 2。**volume・color・rgbimage・video は 3-D を受けるのが
仕様なので正しい**。不具合は **image 78 + region 11 = 89 本**。

カテゴリ別では smoothing 17 / rank 15 / edges 13 / frequency 11 / region 10 /
texture 8 —— つまり**近傍を見る族がまるごと**入っている。

**なぜ「1 件の修正」で済まないか**: いまのところ**カラー画像に対して正しい
呼び方が存在しない**。

| 呼び方 | 何が起きるか | 実測 |
|---|---|---|
| まとめて渡す | 近傍演算が色を跨ぐ | 89 本 |
| チャネルごとに 3 回呼ぶ | 自己正規化する op が各チャネルを自分の最大で割り、**チャネル間の比が消える** | 灰色エッジ法の角度誤差 自前 Sobel 1.03 度 → 画像ごと 4.17 度 → ch ごと **27.86 度**(ゼロ点 29.14 度) |

**いまの扱い**: 既定の数値は 1 つも変えていない。`on_error="raise"` のときだけ
拒否し、既定では台帳に記録して見えるようにした
(`api._CHANNEL_UNSAFE_OPS`、門は `tests/test_channel_axis.py`)。

**決めるべきこと(3 択)**:

1. **fail-closed** —— image/region 用の op に `(H,W,3|4)` を渡したら常に拒否する。
   利用者に `fs.split_channels` 相当を書かせる。いちばん正直だが、いま動いて
   いる呼び出しが全部落ちる。
2. **チャネルごとに自動で回す** —— `apply` が分解して 3 回呼び、**正規化を
   最後に 1 回だけ**掛けて比を保つ。期待どおりの意味になるが、
   `ops._norm` の位置を変えることになり、**2-D 単体の結果は変わらないが
   カラーの結果は今と変わる**。
3. **現状維持 + 記録**(いまここ)—— 数値は動かないが、正しい答えは返らない。

2 が本筋だが、`_norm` を op の外へ出す変更は 882 op すべての出力に触るので、
**parity 門を先に用意してから**にする。

## 35. py3.12 の CI が 1 度だけ segfault した(再現せず・原因未特定)

**事実**: 2026-09-06 の run `34018149265`(第 6 波の push)で、**py3.12 の
ジョブだけ**が exit 139 で落ちた。py3.10 / py3.11 / lint / core は同じ commit で
通過している。

進行 18 %(2160 テスト完了)で 5 分半止まり、`faulthandler_timeout=180` の
ダンプが出たあと segfault。ダンプは**途中で切れている**:

```
Timeout (0:03:00)!
Thread 0x...  (threading.Timer — pytest-timeout の見張り)
Thread 0x...:
  File "<string>", line 1 in <lambda>
  File "<shim>", line ??? in <interpreter trampoline>
Segmentation fault (core dumped) pytest -q -ra --cov ...
```

Python のフレームが 2 段しか出ていない(pytest 自身のスタックが無い)ので、
**ダンプの途中で落ちた**と読める。

**再現の試み(すべて陰性)**:

| やったこと | 結果 |
|---|---|
| 次の commit の CI(run `34022627278`) | py3.12 **41 分で緑**。同じ範囲を通過 |
| Windows に py3.12 を建てて全数実行 | 11252 passed。segfault 無し |
| 18 % 付近のテストを特定(`test_d*`〜`test_e*`) | 特に重い C 拡張は見当たらず |

**分かっていること**: `skimage.morphology.reconstruction` と `h_maxima` を
NaN 画像で交互に呼ぶと SIGSEGV する(2026-09-05 実測)。これは
`backend_safe.require_finite` で入口を塞いである。今回のダンプにその 2 op は
出ていないので**同じものとは言えない**。

**扱い**: 再現していないので原因を断定しない。**直したとは書かない**。
再発したらこの節に run 番号を足すこと。2 度目が出たら決定的なので、
`b5f8a86b9..4bb2e56ac` の範囲を二分探索する。

## 36. 例の図はギャラリーから走らせたときだけ出る(設計。ただし片手落ちが残る)

**いまの形**: `examplefig` は環境変数 `FULLSEYE_FIGURE_DIR` があるときだけ
PNG を書く。既定(CLI 実行)では**完全に無処理**なので、31 本の PoC の数値も
速度も変わらない。Studio のギャラリーが Run のときにその変数を渡す。

**片づいたもの(2026-09-06)**:

1. ~~配線済みは 3 本だけ~~ → **全 PoC を配線した**。`tests/test_example_figures.py`
   の `test_every_poc_is_wired_to_emit_figures` が `examples/poc_*.py` を 1 本ずつ
   AST で見て、`examplefig` を import し `figs.save*` を呼び `figs.errors()` を
   見ていることを要求する。**新しい PoC を足したときも自動で効く**ので、
   「絵の出ない画像処理の例」はもう作れない。
2. ~~`save_table` の列幅が固定(110 px)~~ → **`measure_text` で測って決める**
   ようにした(`examplefig._column_widths`、下限 56 / 上限 320 px)。
   自分の道具に「描く前に測る」関数があるのに使っていなかったのが直った。

**残っている片手落ち**:

1. **CLI から図を出す口が無い**。`FULLSEYE_FIGURE_DIR=... py -3.11
   examples/poc_x.py` で出せるが、`--figures <dir>` のような引数は無い。
   引数解析を全 PoC に足すより環境変数 1 本のほうが安いと判断した。
2. **パネル題がパネル幅に入らないと図が 1 枚まるごと落ちる**。
   `annotate_figure_grid` が fail-closed で拒否するのは正しいが、パネル幅は
   **入力画像の幅**で決まるので、呼び手には「何文字なら入るか」の手掛かりが
   無い(実測で 4 人の書き手が全員踏んだ)。題を自動で縮めるか、パネルを
   題が入る幅まで広げるかを決めていない。
3. **`_to_rgb8` はパネルごとに値域を伸ばす**ので、値が狭い帯に密集する量
   (突出度 0.96〜0.99)や外れ値の大きい差分は、呼び手が事前に分位点で
   切らないと潰れる。`clip=(lo, hi)` か `robust=True` の口が無く、いまは
   「切ったこと」を caption に書いて回避している。
4. **`save_plot` に水平・垂直の基準線を引く口が無い**。「ゼロ点」「上限」を
   示すのに定数の系列を渡していて、色役(5 つ)を 1 つ消費する。
   6 系列以上のグラフは色が巡って区別できない。
5. **`save_plot` の凡例は右上固定・不透明**なので、右上へ伸びるデータ
   (ROC、単調増加)を隠す。

門は `tests/test_example_figures.py`。`test_a_real_poc_emits_figures_only_when_asked`
は実際の PoC を**別プロセスで 2 回**走らせ、環境変数の有無で出力が変わり
**どちらも exit 0** であることを見る。加えて
`tests/test_poc_scripts_run.py` が **全 PoC を実際に走らせる**(§37)。


## 37. PoC を実行する門が無かった(2026-09-06 に追加。当時 4 本が赤だった)

**症状(当時)**: `examples/poc_*.py` を**実行するテストが 1 本も無かった**。
`test_examples2d` は登録と実体の一致を、`test_example_figures` は図の配線を
静的に見るだけで、**看板作品が誰にも走らされないまま置かれていた**。

見つかった 4 本は、いずれもこの repo が自分で仕掛けた
**「記録した穴が塞がったら鳴る」assert** が鳴っていたもの。仕掛けは正しく
機能していたのに、鳴らす人がいなかった:

| PoC | 鳴った理由 |
|---|---|
| `poc_registration_basin` | `fpfh` が既定の法線で回転不変になった(自前の `estimate_point_normals` が重心から外向きに符号を揃えるようになった)。`ppf_model` の既定 `dist_step` も凸包の直径に替わり回転不変になった |
| `poc_lightfield_depth` | `stereo.disparity_subpixel` が `np.divide(..., out=, where=)` に替わり、平坦領域の divide 警告が出なくなった |
| `poc_dimensional_inspection` | `opsmeasure1d` 台帳の登録で、届かなかった 14 関数が `fs.ledger` から届くようになった |
| `poc_ct_fidelity` | ランプフィルタの DC ビンを直した副産物で、検出器数と質量欠損の関係が消えた(**そもそも `n_detectors` は検出器の幅であって標本化の細かさではない**ので、動かないのが正しい) |

4 本とも**所見と assert を「塞がった状態を固定する」向きへ書き換えた**。
assert を消して通すのは、直すことでも記録することでもない。

**費用**: 直列 425 秒 / 6 並列 **85 秒**。`tests/test_poc_scripts_run.py` は
セッション用フィクスチャで一度に並列実行し、各 PoC はその結果を見るだけ ——
「どの PoC が落ちたか」が個別に出るのに、時間は 1 回ぶんで済む。

**まだやっていない**: 図を出す経路(`FULLSEYE_FIGURE_DIR` あり)での全 PoC 実行は
していない。1 本(`poc_dic_strain`)だけ `test_example_figures` が端から端まで
見ている。全本でやると時間が倍になるので、**figures 経路の壊れは 1 本ぶんしか
見張っていない**ことを承知の上で置いている。

## 38. 「op → example 100 %」の門は**母集団が 3 層のうち 2 層しかない**

**症状**: `tests/test_op_example_coverage.py` は `test_no_3d_op_lacks_an_example`
と `test_no_2d_op_lacks_an_example` の 2 本で「100 %」を主張しているが、
**数えている母集団が実際の公開 op より小さい**。2026-09-06 の実測:

| 層 | op 数 | 例索引に入っている |
|---|---|---|
| 3-D op | 347 | **347(100 %)** |
| 2-D 進化 op(`fullseye.op.*`) | **885** | **737** — 148 本が母集団の外 |
| 型つき台帳(`fullseye.ledger.*`) | 1,002 | **349** — **653 本が母集団の外** |

台帳側の内訳(例索引に 1 本も入っていない族): optics 124 / annotate 46 /
reprconv 41 / gfx2d 32 / 1d 32 / piv 26 / math 26 / imgmetrics 24 / quat 19 /
dem 19 / acoustics 19 / photon 17 / lightfield 17 / tomography 17 /
imgforensics 16 / shapestat 16 / videostream 16 / measure1d 14 / astrostack 14 /
shape2d 13 / specular 13 / profile 12 / 2d 12 / volcolor 11 /
colortransport 11 / **blob 10** / interferometry 9 / motionmag 9 /
rangedoppler 8 / roughness 6 / cadmap 4。

**なぜ緑のままだったか**: これは
[[feedback_registered_only_gates_miss_unregistered]] と同じ形 ——
**門は「索引に載っている op」を数えており、載っていない op は分母に入らない**。
だから族を足すたびに「100 %」の主張だけが自動で維持され、実際の被覆は下がる。
ユーザーの「本当にサンプルコードを各 op 分用意してるのかな?」で数え直した。

**いま言えること(正直に)**: 台帳 op には**族ガイド**(`docs/ops/<dim>/guides/`)
と**per-op ノート**(`docs/ops/**`、1,839 本)があり、ガイドの python スニペットは
テストで実行される。だが**「op 1 本ずつに動く例がある」わけではない**。

**やっていないこと**: 653 本ぶんの例は作っていない。0.1.10 では
**現状を数えて記録し、後戻りだけ止める**(`tests/test_op_example_coverage.py`
の ratchet)。埋めるのは次の波。

## §39 索引は「一致」しか見ておらず、中身が空でも緑だった(2026-09-06)

`docs/README.md` は GitHub Pages のトップ(<https://furuse.work/>)であり、
AI コーディング支援が引く検索面でもある。この日に到達性を数えたら、
**op ノート 1,842 本・族ガイド 48 本・記事 40 本が、入口から 1 本も辿れなかった**。

| | 直す前 | 直した後 |
|---|---|---|
| `docs/*.md` | 31 / 74 | **74 / 74** |
| `docs/ops/**/INDEX.md` | 0 / 32 | **32 / 32** |
| 族ガイド | 0 / 48 | **48 / 48** |
| op ノート | 0 / 1,842 | **1,842 / 1,842** |
| `docs/articles/**` | 0 / 40 | **40 / 40** |

原因は 2 つ、どちらも「在るものを無いことにする」形:

1. 索引に `docs/ops/` へのリンクが 1 本も無かった。
2. 直そうとして足した生成器が `OD.records()`(実体は `_records`)を `hasattr` で
   探し、**見つからないと黙って空を返した**。「0 本の op ノート」と書かれた
   空の表が 6 言語ぶん公開された。

### 敵対的レビュー(Codex)と、そこから直したもの

`codex exec -s read-only` に「どこでまた黙って壊れるか」を探させ、18 件の
うち実コードで裏が取れたものを直した:

| 指摘 | 実際にどうだったか | 直し方 |
|---|---|---|
| `_all_ops()` が nary 層を握り潰す | 事実。`except Exception: pass` で 17 op が消えうる。しかも**生成器と検査が同じ関数**なので CI は緑のまま | 握り潰しを外し、空なら落とす |
| `OP_INDEX.json` の検査が件数と名前だけ | 事実。型(`in_sort`/`out_sort`)が古くても通る。RAG は型で鎖を組むので**繋がらない鎖を提案する** | `build_op_index()` を切り出し、**生成物そのもの**と全一致で比較 |
| 索引 1,842 と RAG ガイド 1,843 が食い違う | 事実。差の 1 本は `docs/ops/SAMPLES.md`(op ノートではない)。ファイルを数えた私の側が誤り | ノート数は**台帳から**取る。ファイルとの一致は別の門で双方向に見る |
| 族ガイド数が `len(os.listdir())` | 事実(いまは 0 だが、画像や一時ファイルがあれば水増しされる) | `*.md` だけ数える |
| 到達性が ja からしか測られていない | 事実 | 6 言語すべてを出発点に測る |
| マーカーの重複を許している | 事実。生成器は最初の 1 組しか書き換えないので、2 つ目は永久に古い | ちょうど 1 回・正しい順であることを検査 |
| 表の検査が「20 行あればよい」 | 事実。数百 op 落ちても通る | **次元ごとの実数**と全一致で比較 |
| 地図が 2 階層しか見ていない | 事実。`docs/howto/` を切ったら丸ごと落ちる | 再帰。外す部分木のほうを明示 |
| HTML の `<img src>` を見ていない | 事実。`docs/GALLERY.md` に 14 か所 | 生 HTML も走査。画像のリンク切れも見る |
| 大文字小文字の検査が無い | 事実(違反は 0 件だが門が無い) | 公開側(Linux)の規則で厳密比較 |

### ★残っている本当の穴 —— ノートの「中身」

「生成物と commit 済みが一致するか」しか見ない門は、**両方が空でも緑**になる。
そこで中身の量を数えた(索引にもそのまま出している):

| | 実測(2026-09-06) |
|---|---|
| op ノート | 1,842 本 |
| 構造(frontmatter・呼び出し・データ種・次に繋がる op) | **1,842 / 1,842** |
| 実行できる例が 1 本以上 | **1,637**(205 本は例ゼロ) |
| 使い方の本文が 120 字以上 | **1,348**(494 本は 1 行の要約だけ) |
| ノート内の doctest | 4 本のみ |

205 本と 494 本は**まだ埋めていない**。`tests/test_docs_index_reachable.py` の
`_WITH_EXAMPLE_FLOOR` / `_WITH_USAGE_FLOOR` で後戻りだけ止めてある。
例ゼロの大半は `2d/typed/tb_*`(型つき薄ラッパ)で、`identity` のように
例を作る意味が薄いものも混ざる —— 埋めるときは**どれを埋めないか**も
理由つきで決めること。

### `OP_INDEX.json` の `halcon` 空欄について

902 op のうち **393 が空**だが、これは欠損ではなく「HALCON に対応する
オペレータが無い自前の op」。tier 別では registry 873 中 393 で、color 12 と
nary 17 は全数が HALCON 由来。RAG がこの欄で絞り込むときは「空 = 独自」と
読むこと。

### Studio ヘルプは「使い物になる形」か(2026-09-06 に実物を読んで確認)

生成できたことと、開いて読めることは別。11,854 ページを実際に読んだ結果:

| 見たこと | 結果 |
|---|---|
| ページ数 | 11,854(op 1,842 × 6 言語 + ガイド 48 × 6 + 手書き 3) |
| 空・スタブ | **0 本**(最小 2,004 B、中央 4,260 B) |
| ★Markdown が生のまま出ていた | **60 ページ → 0**(下記のバグを修正) |
| 内部リンク | `op:` / `guide2d:` / `example2d:` / `sample:` の Studio 内スキーム。`studio.py` が解決する(ファイルパスではない) |
| 言語版の欠け | `gaussian` / `otsu` / `sobel_mag` の 3 本のみ。**意図的** —— 手書きの英語ページで実行できる `sample:` を持ち、言語を切り替えても薄い自動生成に置き換わらないようにしてある |
| 本文の翻訳が届いているページ | en **906 / 1,887**、zh・tw・ko・de 各 **535 / 1,887**。届いていないページは**読み手の言語で**「まだ翻訳がありません。原文をそのまま載せます」と断ってから原文を出す |

**★直したバグ**: `tools/opdocs.py` の `_inline()` がコードスパンをリンクより
**先に**切っていた。リンクの表示文字列がコードスパンのとき(サンプル一覧へのリンクがこの形)、
「開き括弧」「コード」「閉じ括弧と行き先」の 3 つに割れ、リンクの正規表現が
どの断片にも当たらない。
生成は成功し、ドリフト検査も緑で、**人が開いたときだけ壊れて見える**。
リンクを先に切り、その表示文字列の中でコードスパンと太字を処理するよう入れ替えた。
門 = `tests/test_opdocs.py::test_the_help_html_contains_no_raw_markdown`(全ページ走査)
と `::test_inline_renders_a_link_whose_text_is_code`(回帰)、翻訳の後戻りは
`::test_the_help_translation_coverage_does_not_regress`(床つき)。

## §40 op ごとの「入力 → 出力」の図と Studio で走るプログラム(2026-09-06)

### 何を足したか

手書きヘルプ 3 本(`gaussian` / `otsu` / `sobel_mag`)と機械生成 902 本を並べて
数えたら、勝っている軸がきれいに分かれた:

| | 手書き 3 本 | 機械生成 |
|---|---|---|
| 実行できる `sample:` パイプライン | 3/3 | **0** |
| 使い方の本文(中央) | 409 字 | 288 字 |
| 呼び出し形(コピーして動く 1 行) | **0/3** | 100 % |
| 型が繋がる次の op / 兄弟 / 出典 / 5 言語 | 一部 | ほぼ全数 |

機械生成に足りない「その場で動く」は機械にも作れる。`tools/gen_op_figures.py` が
各 2-D op を**実際に走らせ**(`on_error="raise"`。fail-soft で恒等に落ちたものは
「動いた」と数えない)、通ったものだけ図と `sample:` プログラムを出す。ノート
(`docs/ops/**`、RAG が読む側)には図と ```` ```program ```` ブロック、Studio の
ヘルプ HTML にはその図と「Load this pipeline / Load & run」のボタンが載る。

| | 実測 |
|---|---|
| 図と `sample:` のある op | **724 / 885** |
| 型が届かない(理由をノートに明記) | **161**(`points` 53 / `signal` 26 / `video` 16 / `volume` 14 / `qimage` 11 / `cimage` 9 / `counts` 8 / `lightfield` 8 / `rgbimage` 6 / `beatcube` 4 / `matrix` 4 / `keypoints` 2) |
| 走らせて落ちた | **0** |
| 図 1 枚 | 中央 5 KB、724 枚で 5.3 MB(docs 側と wheel 側の 2 か所) |

161 本は「画像から始めて登録 op だけで作れる sort が 5 つしか無い」という
型グラフの計算結果で、`tests/test_op_figures.py` が登録簿から再計算して一致を
確かめる。image → points のような橋渡し op が登録されれば、門が落ちて
`PREFIX` を伸ばす番になる。

図の入力は**決定的な合成シーン**(円・矩形・細線・市松・階調 + 右下の区画だけ
ノイズ)。外部データセットは版で中身が変わりうるので、図を commit する以上
再生成で同じバイト列になることを優先した。ノイズを全面に撒くと PNG が縮まず
1 枚 16 KB になる(σ=0.02)ので区画に限った。図の中の文字は**短い英語だけ**
(ヘルプは 6 言語、図は 1 枚)。言語ごとの説明は `docs/i18n/opdocs.json` の対訳表。

### ★図が見つけた op のバグ: `smooth_contours` の端がゼロへ引かれる

図を初めて作ったとき、`smooth_contours` だけ輪郭 140 本ぶんの赤い筋が**左上へ
収束**していた。原因は `np.convolve(x, k, "same")` —— 端をゼロで埋めるので、
各輪郭の始点・終点の w 点が原点 (0,0) と平均され、最大 50 px 以上ずれる。
**平均ずれは 0.34 px** で、平均を見る数値テストには一度も引っかからなかった
(端だけが壊れる欠陥は平均に埋もれる)。端を端の値で埋めるよう直し、
`tests/test_smooth_contours_endpoints.py` が「出力は入力の範囲内」「最大ずれ」を
見る。`np.convolve(…, "same")` を輪郭に使う箇所は他に無かった。

### 描画側で「落ちた」と数えていた 112 本

最初の走行は 612 / 161 / 112 だった。112 本は**全部描画側**の問題で、op は走って
いた: contour 入力の左パネルが描けない(65)/ スカラ結果の札が 128 px に
収まらない(47)/ 長い op 名がキャプション幅に収まらない(36、次の走行)。
「走ったのに描けなかった」を「落ちた」に混ぜると、op の失敗率を 4 倍に
見せる。理由を分けて数えたから気づけた。

### ★公開サイトでは図が 404 だった(2026-09-07、push 後に実測)

push して Pages が反映されたあと `https://furuse.work/ops/_fig/gaussian.png` を
叩いたら **404**。索引の新節も op ノートも 200 なのに、図だけ配信されていない。
Jekyll は `_` で始まるディレクトリを配信しない(内部ディレクトリの規約)。
手元では 724 枚すべてリンクが通り、門も緑 —— **配信側の規則は配信側でしか
見えない**(「門は事故の起きる場所に立てる」の再演)。

直し方は `docs/_config.yml` の `include: [_fig]`。再発防止に
`tests/test_docs_index_reachable.py::test_underscore_directories_are_served_by_pages`
が、リンクされている `_` ディレクトリが include に載っていることを見る。
`docs/articles/assets/_sources` も `_` だが、md からリンクされていないので
配信されなくてよい(生成の元データ)。

### ★Linux CI で 22 件が落ちた —— 手元の文書と「その環境のレジストリ」を比べていた(2026-09-07)

push 後の CI(py3.10/3.11/3.12、`pip install -e .` のみ)で新しい門 22 件が落ちた。
手元 Windows では全体スイート 12,310 passed。原因は 1 つで、**op 集合が環境で
変わる**: Linux CI には torch / kornia / mahotas / `cv2.xfeatures2d` が無く、
`dl_*` / `xkor_*` / `xmh_*` / `xcv3_agast|brisk_count` の 26 op が消えて
**859 op / 40 カテゴリ**(手元は 885 / 47)。手元の満杯環境で生成した索引・
OP_INDEX.json・図の manifest を、その環境の生きたレジストリと厳密比較すれば落ちる。

これは Codex の敵対的レビュー #15(「環境依存の import 時に生成物が変わる」)で
**先送りにした指摘そのもの**。既存の `test_opdocs` は同じ理由で 2026-09-05 に
`requires_full_registry()`(conftest)を置いていた —— 満杯でなければ skip、
skip 理由に欠けている backend 名を出す。新しい門も同じ規約に揃えた。
環境に依らない検査(ファイルの実在・中身の量・図の実在・落ちた 0 本・床)は
skip せずそのまま走る。

同じ CI で分かった他の 2 つ:

* **図のバイト一致は OS をまたがない**。`identity.png` ですら Linux では別バイト
  (文字のアンチエイリアスと PNG 量子化が PIL/フォントで数バイト違う)。
  決定性の門は「同じ環境で 2 回作って同一」に変えた。守るのは乱数と実行順が
  混じっていないことで、環境をまたぐ見た目は生成した環境で目で見る。
* `poc_template_tracking.py` の自己制限 90 秒が、共有ランナーでは **134 秒**で
  落ちた。守りたいのは「桁で遅くなっていない」ことなので 300 秒に。

手元で CI を再現する方法(stub で optional backend を消す):

```powershell
$S = "$env:TEMP\nobackend"; New-Item -ItemType Directory -Force $S | Out-Null
foreach ($m in "torch","kornia","mahotas") { 'raise ImportError("stub")' | Set-Content -Encoding ascii "$S\$m.py" }
$env:PYTHONPATH = $S; py -3.11 -m pytest tests/test_op_figures.py tests/test_docs_index_reachable.py -q -rs
```

2 回目の CI(540f74907)は py3.11 が緑、py3.10 と py3.12 が別々の理由で赤だった:

* **py3.12: `faulthandler_timeout = 180` のスタックダンプが segfault を起こした**。
  `test_param_coevolution…`(手元 87 秒)が共有ランナーで 180 秒を超え、
  faulthandler が numpy/BLAS のスレッドが走っている最中にダンプを吐いて
  プロセスごと落ちた(exit 139)。しきい値を 600 秒に(本物のハングは pytest の
  timeout 900 秒が別に拾う)。
* **py3.10: `poc_ct_fidelity.py` が exit 1、しかし理由が読めなかった** —— PoC の門は
  失敗時に stderr の末尾しか出さず、PoC は所見を stdout に印字して `SystemExit(1)`
  する。門を直して stdout の末尾も出すようにした。PoC 側で丸めに敏感なのは
  「検出器の数で質量が動かない: |Δ| < 1e-9」だけで、同じ環境の前回は通っている
  (スレッド BLAS の加算順で 1e-9 は揺れる)ので 1e-6 に。次に落ちれば理由が出る。

3 回目の CI(1fcdf05b9)で py3.11/3.12 は緑になり、py3.10 の理由が門の stdout に出た:
「真値の一様領域は厳密に一定: `truth[flat].std() == 0.0`」が **5.6e-17** で NG。
旧 numpy(py3.10 に入る版)の `std` は加算順が違い、同じ値の配列でも厳密ゼロに
ならない。主張は「一定」なので `np.ptp(...) == 0.0`(max − min。総和を経ないので
厳密)に替えた。**float の `== 0.0` は総和を経た量には使わない。**

## §41 残っていた穴を埋めた回(2026-09-07): 入口 op・使い方 494 本・例ゼロ 205 本・空の図

§39/§40 の末尾に「残っている本当の穴」として書いた 4 件をすべて処理した。数字は
すべて `py -3.11 tools/gen_docs_index_ops.py` と `tests/` の門が数え直したもの。

### 1. 161 op に図と Studio プログラムが付いた(入口 op `img_to_*`、category `bridge`)

**原因**: 2-D レジストリには points / signal / video / volume / lightfield / cimage /
counts / beatcube / matrix / keypoints / qimage / rgbimage を**受ける** op が 161 本
あるのに、画像からそれらを**作る**登録 op が 1 本も無かった。typed bridge
(`backends_typed`)が入口 op を既定から外していたのは正しい理由による ——
`in_sort=image` の op を足すと image の候補リストが伸び、既存のゲノムが別の op に
写る(`docs/WAVE0_STABLE_SLOTS.md` §1)。

**解**: `backends_bridge.py` の 12 op を category `bridge` で `REGISTRY` に載せ、
`ops._candidates` が **その category を候補から除く**(`ops._NOT_A_CANDIDATE`)。
進化には見えず、名前で引く経路(`fullseye.apply` / Studio / 図 / 索引)には見える。
候補リストの不変は `tests/test_wave0.py`、橋の契約は `tests/test_backends_bridge.py`、
例は `examples/gallery2d_bridge.py`(閉形式で検算)、ガイドは
`docs/ops/2d/guides/gallery2d_bridge.md`。

**入口の尺度で 1 度やり直した**: 最初は点群を画素座標(0〜127)で作ったところ、
`tb_alpha_shape_boundary` / `tb_iss_keypoints` / `tb_radius_outlier_removal` が
**空**を返し、`tb_occupancy_grid` / `tb_euclidean_cluster` が**全 0** を返した。
typed bridge が点群 op に束縛した半径 2.0・境界箱 0〜10・格子解像度は連鎖ファザーの
種 `[0,10)^3` を前提にしている。入口をその尺度(`backends_bridge.POINTS_BOX = 10`)に
揃えて解消。**尺度の規約は台帳のどこにも書かれていなかった**(束縛値から逆算した)。

| 図の判定(897 op) | 本数 |
|---|---|
| 図あり(実際に走らせて描いた) | **892** |
| 型が届かない | **0**(§40 の 161 → 0) |
| 定義域が合わない(`gen_op_figures.DOMAIN_MISMATCH`、理由つき) | 4 |
| 走ったが返り値が空(`empty`) | 1(`tb_zero_crossings_funct_1d`: 非負のプロファイルに零交差は無い) |
| 落ちた | 0 |

定義域が合わない 4 本: `tb_angle_3points`(ちょうど 3 点が要る)/ `tb_indices_to_labels`
(整数の添字が要る)/ `tb_keypoints_to_image2d`(束縛した raster が 64×64 固定)/
`tb_cx_apply_transfer_function`(束縛した H が 32×32 固定)。後ろ 2 本は typed bridge の
束縛が入力の大きさに追随しないためで、ヒント表を入力依存にできれば通る。
`tests/test_op_figures.py::test_domain_mismatch_ledger_is_still_true` が「本当にまだ
拒否される」ことを走らせて確かめる(免除台帳が腐らないように)。

### 2. ★「out が真っ黒」—— 走ったことと意味のある出力が出たことを分けていなかった

ユーザー指摘(2026-09-07)。生成器は `fs.apply` が例外を投げなければ「図あり」に数え、
**空配列を黒い板として描いていた**。判定 `empty` を足し、空は図にせずノートに理由を
書く。`tests/test_op_figures.py::test_empty_verdicts_are_really_empty_and_ok_verdicts_are_not`
が「empty は本当に空、ok は空でない」を実行で確かめる。
ユーザーの次の問い「同じ状態は他にないか」に答えるため、892 枚の **out パネルを
数値で走査**した(一様 = 標準偏差 0、低コントラスト = 値域 0.1 未満):

| | 本数 | 処置 |
|---|---|---|
| out が一様 | 8 | 6 本は op の答えとして正しい定数(`hx_full_domain` / `hx_get_domain` = 全域、`hx_gen_empty_region` = 空、`hx_gen_image_proto` = 一定値、`r2_smallest_circle` = 領域が画像全体、`r3_select_region_point` = 点を含む領域が無い)。**2 本は入力側の欠陥**: `tb_geodesic_distances` は距離に inf が混じり折れ線が描けなかった → 非有限を除いて描く。`tb_specular_coefficient_map` は `img_to_rgb` が白いハイライトを作らず鏡面が全 0 → 入口を二色性反射(明部 0.75 超を白へ)に変更 |
| out の値域が 0.1 未満 | 1(周波数系) | min–max で伸ばし、キャプションを `out (stretched)` にして伸ばした事実を明示(`gen_op_figures.STRETCH_BELOW`) |
| out が値の札(スカラ特徴量) | 127 | 図にならないのが正しい |

`ncc_locate` / `shape_locate` はテンプレ未設定で 0 の match を返す(札)。

図の見せ方も sort ごとに変えた(`gen_op_figures._panel_for`): 点群は上から見た散布
(明るさ = z)、1-D 列は折れ線、体積は z 方向の MIP、動画は中央フレーム、
ライトフィールドは中央視点、複素画像は振幅、四元数画像はベクトル部を RGB に、
キーポイントは元画像への重ね描き。`array(4096, 3)` と書いた札では op が何をしたか
伝わらなかった。

### 2b. 図の第 2 波 —— 1 枚に纏めない(ユーザー指示 5 件を同日に反映)

| 指示 | 実装 |
|---|---|
| 「1 枚に纏める必要はない。段階的なもの・条件が複数あるものは分けて出す」 | `<op>.a.jpg` / `<op>.b.jpg`(つまみを 0.1 / 0.5 / 0.9 に振った 3 枚。**出力が変わる op だけ**。変わらなければ「つまみ a は出力を変えない(実測)」とノートに書く —— これは効かないつまみの台帳でもある)、`<op>.chain.jpg`(前置き op → この op の段階図) |
| 「物によっては疑似カラーのほうが分かりやすい」 | 距離・位相・向き・深度・曲率・スペクトル … **量の場**の出力に viridis 風の疑似カラー(`gen_op_figures.PSEUDOCOLOR` の名前規則、キャプション `out (viridis)`)。フィルタ系はグレーのまま |
| 「複雑なものはアニメーション GIF でも」 | 出力が動画 / ライトフィールド / 体積の op に `<op>.gif`(フレーム / 視点 / スライス)。静止画が完成形、GIF は補助(Studio の QTextBrowser は 1 コマ目) |
| 「高品質を求められるものは、いくつかの画像を試した結果が有っても良い」 | `<op>.inputs.jpg`: 合成シーン / 写真(skimage `camera`)/ 硬貨(`coins`)/ 生成画像 4 枚(部品・基板・ラベル・豆)の上段 = 入力、下段 = 出力 |
| 「モノクロとカラーの両方に対応している op もある」 | `inputs` 図の最終列にカラー写真(`astronaut`)。**色を跨がない op(§34 の 89 本以外)だけ**に掛け、跨ぐ op にはその旨をノートに書く(`color_ok`) |
| 「外部の画像生成 AI にテスト用の入力画像を作ってもらっても良い」 | `tools/gen_ai_inputs.py`。OpenAI は残高切れ(429)だったので Gemini `gemini-2.5-flash-image` で 4 枚生成。来歴(モデル・日時・プロンプト・SHA-256)は `docs/ops/_fig/inputs/PROVENANCE.json`。生成は人が走らせたときだけ(CI からは呼ばない) |

配り方: 主図 PNG と GIF は wheel(Studio ヘルプ)に同梱、JPEG(段階図・複数入力、128 px 等倍・品質 92)は docs サイトだけに置き、Studio ヘルプからはリンク(全 op ぶんを同梱すると PyPI の 100 MB 上限を超える。ユーザー指示「縮小し過ぎ。容量なら JPEG で」)。スカラを返す op には複数入力の図を作らない。主図も 32 色パレットをやめて可逆 PNG に(「極力は高品質な部分を見せたい」)。

門: `tests/test_op_figures.py::test_extra_figures_exist_and_are_counted`(床: 段階図 600 組・GIF 30 本・複数入力 600 本)、`::test_dead_knobs_are_really_dead`(「効かない」と記録したつまみが本当に効かないか抜き取り)。

### 2c. 再生成の順番(この回で 3 度やり直した —— 手順として固定)

```
py -3.11 tools/gen_op_figures.py        # 図(主図 PNG・段階図/複数入力 JPEG・GIF)+ figures.json
py -3.11 tools/opdocs.py md             # op ノート(図・sample: を埋め込む)
py -3.11 tools/opdocs.py toc            # ★op 目次(INDEX.md、レジストリ指紋)—— md では作られない
py -3.11 tools/opdocs.py html           # Studio ヘルプ(6 言語)+ op_help/fig へ PNG/GIF 複製
py -3.11 tools/gen_op_catalog.py        # OP_CATALOG.md(索引の到達性はここ経由)
py -3.11 imgevolve.py index             # OP_INDEX.json(★gen_docs_index_ops より先)
py -3.11 tools/gen_docs_index_ops.py    # docs/README*.md(6 言語)の生成 3 節
py -3.11 tools/gen_examples_readme.py   # examples/README.md
```

`toc` を抜かすと「INDEX.md の指紋が live と違う」「新カテゴリのノートが索引から辿れない」
の 2 門が落ちる(実測)。`imgevolve.py index` を後にすると README の op 数が古いまま出る。

**PoC を足したときも同じ順番が要る**(2026-09-07、CI で発見): op ノートには「この op を使う例」
の節があり(`op_example_index`)、PoC を 1 本足すだけで呼んでいる op のノートが全部古くなる
(8 本足して 13 ノート以上が stale)。展示館の生成器だけ回して push すると `test_opdocs` が落ちる。
PoC バッチの取り込み後は **`opdocs.py md → toc → html → gen_op_catalog → imgevolve.py index →
gen_docs_index_ops → gen_examples_readme → gen_wingpoc_gallery`** を通す(図の再生成は不要)。

### 3. 使い方が 1 行だった 494 本 → 0 本

2 つの原因が重なっていた。

- **3-D 台帳の切り詰め**(構造的): `ops3d._build` は `fn.__doc__` の **1 行目だけ**を
  `doc` に入れ、`tools/opdocs.py` の 3-D 経路がそれを「使い方」に使っていた。
  他の台帳 dim は `inspect.cleandoc(fn.__doc__)` 全文を使う。494 本のうち 3-D の
  多数は **docstring 自体は最初から長かった**(例: `vol_rle_intersect` 629 字、
  `annotate3d_project` 1,564 字)。opdocs の 3-D 経路を全文に変更。
- **本当に 1 行だった op**: 2-D backend 87 本(`hx_*` 62 本など)と台帳 60 本、3-D の
  一部。実装を読んで日本語の本文(引数の写像式・返り値の形・fail-closed 条件・罠・
  前後の op)を足した。**1 行目は 1 バイトも変えていない**(6 言語の要約対訳表が
  1 行目の指紋をキーにしているため)。

いまの実測(`_note_substance`): **使い方 120 字未満 = 0 本**。床 `_WITH_USAGE_FLOOR`
を 1,348 → 1,854 に上げた。

### 4. 例ゼロ 205 本 → 1 本(`identity`)

- **台帳 7 族 58 本**: 例スクリプトを 9 本足した(`dem_geodesy_tour` /
  `dem_terrain_analysis_tour` / `piv_field_analysis_tour` / `profile_frame_tour` /
  `shapestat_landmark_tour` / `shape2d_morph_descriptor_tour` / `blob_split_tour` /
  `annotate_paper_tour` / `gallery2d_bridge`)。どれも合成データに真値を埋めて `assert`
  で検算し、60 秒未満、`examples2d.EXAMPLES` に登録。
- **橋渡し op 147 本(`tb_*`)**: 例は台帳名(`arc_length`)で書かれ、`tb_arc_length` は
  同じ実装を `fn(v, a, b)` に合わせただけ。ノートが台帳側の例を**継承**し、
  「元の台帳 op の例(呼び出し形だけ違う)」と明記する(`opdocs._records` の
  `examples_inherited`)。例索引そのもの(`examples:` frontmatter)は触っていない ——
  そこは「実際に `tb_` 名で呼んだ例」を数える門が別にある。
- `identity` は例を書く意味が無いので残す(理由は §39)。

### 5. docstring の読み合わせで見つかった不具合(直したもの / 記録だけのもの)

**直した(実測で確認)**:

- `imgmetrics._INT_RANGES`: `int8 → 255`、`int16 → 65535` と書かれていた(符号付きの
  最大値は 127 / 32767)。int16 画像の PSNR が 6 dB ずれる。修正 + テスト。
- `backends_typed.OP_KNOB_RANGE`: `tb_wetness` の `wet` は既定 1.0 で定義域 [0,1] なのに
  相対スケール(既定の 1/4〜2 倍)で `a > 0.43` なら 1.125 になり**必ず失敗**していた。
  定義域が分かっている引数は絶対範囲で写す表を足した。
- `hx_disparity_to_xyz`: `a`, `b` を変えても出力が完全一致(`f*baseline` が定数倍で
  最後の正規化に打ち消される)—— **未修正**、ノブが死んでいることを記録。

**報告のみ(Agent の読み合わせ。一次情報で私が確認したのは上の 3 件だけ。残りは
ファイル:行の指摘を残す。採用するときは 1 件ずつ実コードで検証すること)**:

- `backends_halcon_ext.py:265` `_nonmax_suppression_dir` の 45°/135° 隣接対が逆の疑い
  (斜めエッジが細線化されない)。`:850,:1007` 楕円距離の半軸が境界点群では √2 倍ずれる。
  `:915` `polar_trans_contour_xld_inv` が順変換の逆になっていない(往復誤差 60 px)。
- `backends_regions2.py:279` `r2_inner_circle` が距離変換の「背景画素中心まで」の
  距離を使うため描いた円板が領域をはみ出す。`_as_mask` が (H,W,3) を (H,3W) に潰す。
- `match3d.py`: `plane_from_3points` / `distance_line_line` / `intersect_planes` が
  2-D 入力で壊れる(`_vecs` は 2-D を通す)。`cylinder_unwrap` に 2×2 未満の検査が無い。
  `hough_sphere_3d(radii=[])` が生 TypeError。`refract` が法線の向きを検査しない。
- `metrics3d.py:59` `hausdorff_distance` だけ `_require_cloud` を通らない(空点群で
  numpy の生エラー)。`bundle3d.project` が `Z <= 0` を弾かない。`pose_graph.mean_edge_error`
  が添字を検証しない。`symmetry3d.reflect_points` が零法線を `+1e-12` で吸収。
  `mesh_props.mesh_area` が退化三角形を拒否しない(モジュール docstring と矛盾)。
- `demops.dem_viewshed` が NaN セルを可視 1 のまま返す。`measuring1d.gen_measure_arc`
  が `radius=0` を検証しない。`pivops._flow` / `colortransport.transport_plan_1d` が
  有限性を検査しない。`blob2d.blob_seeds` が h-maxima でなく h-dome(残差 > 0)を種にする
  (低い塊にも種が立ち、docstring の「h を大きくすると種が減る」と一致しない)。
  `blob_split` の割れ目が番号の大きい種の側へ食い込む(幾何でなく番号順の偏り)。
- `range_image.bearing_angle_image` の未知 `direction` が黙って列方向に落ちる。
  `photometric.normals_to_gradients` の `nz==0` で勾配が 1e12。`twoview.sampson_distance`
  は二乗値を返す(名前は距離)。`pnp3d._project` が深度 ≤ 0 を割る。
  `regionprops3d._as_binary_3d` が NaN を前景にする。
- `volregion.py:370` の docstring に非 raw の `\ ` がある(py3.12+ で SyntaxWarning)。
- 既存の numpydoc 形式(`Parameters` + 深い字下げ)の docstring は、ノートで Markdown の
  コードブロックに化ける可能性がある(edges3d / recon3d / descriptors3d ほか)。

### 6. 残っている穴(この回でも埋めていない)

- `points` sort の列規約が 2 つ混在(カメラ系 (x, y, z) と `reprconv` の (z, y, x))。
  入口 op は (x, y, z) を採り docstring に書いたが、統一は未着手。
- typed bridge の束縛値(raster 64×64、H 32×32、半径 2.0 …)が入力の大きさに追随しない。
  `DOMAIN_MISMATCH` の 2 本と、点群の尺度規約(`POINTS_BOX`)はその現れ。
- `<img alt>` は英語にした(`input → output`)。図の中の文字も英語のみ。
- 手書きヘルプ 3 本(`gaussian` / `otsu` / `sobel_mag`)に呼び出し形を足した
  (`fs.apply` / `fs.op.<name>` / Studio の 1 行)。

### 7. PoC 展示館の記事(Qiita、ja / en)—— データから組む(2026-09-07)

ユーザー方針: 「PoC シリーズも記事更新もしながらどんどん増やす。記事更新時に追加しやすい
構成」「展示会・博物館くらいの規模と見た目」「Qiita は日本語と英語だけ」「ヘルプの目録への
リンクを貼れば細かい説明はいらない」「Qiita と furuse.work は素材を共用し、Qiita から
furuse.work へ誘導する」。

- **単一真実源** = `docs/articles/exhibits/poc_captions.json`(9 ウィング × 53 展示の題・
  キャプション ja/en・数字の出所・追加日)+ 各 PoC の `docs/articles/assets/poc/<id>/figures.json`
  (`FULLSEYE_FIGURE_DIR` で走らせた PoC 自身の出力。記事のために描いた図は無い)。
  `py -3.11 tools/gen_wingpoc_gallery.py` が `exhibits/wingpoc.{ja,en}.md` と
  `docs/articles/fullseye_poc_museum_qiita_{ja,en}.md` と 720 px サムネ、看板モンタージュ
  (`assets/poc/_hero_montage.jpg`、`meta.hero_tiles` で選ぶ)を生成する。
- **PoC を 1 本足す手順**: `examples/poc_<id>.py` を書く → `examples2d.EXAMPLES` に登録 →
  `FULLSEYE_FIGURE_DIR=docs/articles/assets/poc/poc_<id>` で走らせる → `poc_captions.json` に
  1 エントリ(wing / title / caption / added / numbers_source)→ 生成器を回す。
  `tests/test_wingpoc_gallery.py` が「展示 = examples2d の poc_*」「生成物が最新」「画像が
  全部 repo にある」「ローカルパス無し」を門にする。
- **使用 op の行**は手で書かない: `op_example_index._called` と同じ規則で PoC のソースから
  検出し、`https://furuse.work/ops/<dim>/<cat>/<op>.html` へリンクする(誘導の主経路)。
- **数字は実行ログが正**(docstring と食い違った 5 件はログ側を採用: thermography +627 %、
  moire +202.6 %、document_scan 32x、dem 天空率 2.03 s、water_level -6.4/-6.6/+16.3 cm)。
- **投稿**は `tools/qiita_post_poc.py`(既定 = 限定共有。画像 raw URL の HEAD 200 と
  ローカルパス検査を通らないと書かない。item id は `exhibits/qiita_items.json` に残し
  2 回目以降は PATCH)。公開へ倒すのは `--public` 明示時のみ。
- 末尾に Claude Code の招待リンク(1 週間無料トライアル)と「いいね・ストック」の依頼を
  置いた(ユーザー指示)。文面は `entrance.cta_ja/en`。
- 残り: 図の中の文字が日本語(en 記事ではキャプションで断っている)。PoC ごとの英語版
  図は未着手。

### 8. ノブ生死の門が探針で誤判定していた(2026-09-07)

- `hx_close_edges_length` の `b`(残す最小画素数 2〜22)は配線されているのに「効かない」と
  出た。探針画像(`structured_image`)はしきい値で二値化すると連結成分が数百画素になり、
  短い断片を落とすノブに効く余地が無かった。**探針に「細い断片」画像(長さ 3/6/12/25/40 px)
  を 1 枚足した**(`op_probe.structured_fragments`、既存の探針の種と順序は不変)。
- `r2_smallest_circle` / `xg_area_center` は docstring の「``b`` は<改行>未使用」が
  行の折り返しで「振る」判定に化けていた。判定前に折り返しを 1 行に戻す。
- `tb_wetness` の `b` は `OP_KNOB_RANGE`(ior 1.01〜2.5)で生き返ったので台帳から消した。
- **wheel から `backends_bridge` が落ちていた**(CI の wheel 門 `core (numpy+scipy only)` で
  検出、2026-09-07)。`pyproject.toml` の py-modules に足し忘れ —— 0.1.6(321 op)/ 0.1.9
  (224 op)と同じバグ族の 3 度目。手元の門 `test_every_module_the_registry_actually_loads_is_shipped`
  は正しく落ちる(確認済み)が、backend を足した**後に**回していなかった。教訓: backend
  モジュールを 1 本足したら packaging テストと wheel 門を**その場で**回す。
- **手元で組んだ wheel が 96 MB**(2026-09-07、PyPI 上限 100 MB)。中身は同梱を止めたはずの
  `studio_assets/sample_sources_ai/` 42 MB。最初は「setuptools の探索が git 管理下を全部
  拾う」と読んだが**誤り**で、実際は**古い `build/lib/` のキャッシュ**が詰め直されていた
  (`build/` を消すと 56 MB)。CI はきれいな checkout なので PyPI の 0.1.10 は無事。
  対策: ディレクトリを package の外 `tools/fops_article/sample_sources_ai/` へ移動、
  `exclude-package-data` を保険で明示、`tools/ci_wheel_check.py` が wheel 側の存在を NG に、
  ci.yml に wheel サイズ上限(70 MB)。手順書に「wheel を組む前に build/ を消す」。

### 9. PoC 第 2 バッチ(2026-09-07、7 本)が見つけたライブラリの穴

展示館に足した PoC: `poc_exoplanet_transit` / `poc_metal_grain_size` / `poc_prnu_camera_fingerprint` /
`poc_screw_thread_metrology` / `poc_colocalization_crosstalk` / `poc_mri_bias_field` /
`poc_river_surface_velocity`(全部 exit 0 / PASS、`tests/test_poc_scripts_run.py` 61 件緑)。
書きながら見つかった穴(**未修正**、Agent の報告を実行ログで確認したもの):

- `fs.ledger.synth_starfield` は `(frame, truth)` の frame しか返さない(モジュール直呼びなら
  truth も出る)。真値の供給源なのに公開経路で真値が落ちる。
- `aperture_photometry(supersample=8)` の開口マスクの 1/64 階段が、星が動く小開口(≤1.5σ)で
  雑音源になる(縁 1 画素 = 総光量の 5.5 %、1 段 0.86 ppt)。`supersample=32` で理論比 0.9 に戻る。
- `fit_bspline_surface`(FITPACK)は非矩形の台で `smooth=5` にすると |log b̂| が 2.7e3 に発散し
  警告を握って返す。`dc_homomorphic` は低域利得 0.4 固定 + min-max 正規化で定量補正に使えない。
- `gaussian` op は σ ≤ 3.0、`gauss_image` の a は 0..1 に clamp され σ[px] を指定できない。
  マスク付き大 σ の正規化畳み込みは公開経路に無い。
- `fs.ledger.piv_cross_correlate` は flow だけ返して info(窓中心・valid_fraction・peak_ratio)を
  落とす。4 点対応からホモグラフィを解く op が無い(`warp_by_plane` は使う口だけ、出力形も
  入力形固定)。`piv_synth_sequence` は周期境界が無く、長い列で場外の NaN が
  `_render_particles` の `ValueError` になる(fail-closed でなく内部で落ちる)。
- `xg_regress_contours` は輪郭ごとでなく全輪郭を 1 本に混ぜて残差を返す(平行 2 本で 18.5 px)。
  `fit_line_contours` / `hx_split_contours` は docstring が空。caliper 交点をフランクごとに束ねる
  処理、左右フランク角の半差 → 傾き → caliper へ戻す閉ループは無い。
- 領域限定の多クラス大津(`xsk2_multiotsu` は画像全体のみ)が無く、しきい値を返す経路も無い。
- 起きたこと(手順の穴): 並列 Agent 8 本を同時起動したらセッション上限(429)で全滅、4 本ずつに
  分けて再実行。4 本は成果物を書いた後に報告なしで停止し、JSON 2 本は主が実行ログから書いた。
- (8 本目 `poc_change_detection_misreg`)`fs.ledger.piv_cross_correlate` の docstring は `(flow, info)` と
  書くが ledger 経路は flow だけ(上と同じ穴、2 本目の PoC で再現)。平坦な窓の flow に NaN が混ざり
  `piv_outlier_mask` に渡せない。2-D の位相相関が無く 3-D `match_phase_3d` に (1,H,W) を通した(整数精度)。
  対応点からの 2-D 剛体当てはめ + RANSAC が無い(`procrustes_fit` に z=0 を渡す、`poc_panorama_drift` と
  同じ穴の 2 本目)。`affine_trans_image` は並進不可。`histogram_match` は変化そのものを分布差として消す
  (ずれも照明差も無い対で偽陽性 383 px)。

### 10. PoC 第 3 バッチ(2026-09-07、4 本)が見つけた穴と、Agent 運用の教訓

`poc_leaf_disease_area` / `poc_beam_modal_video` / `poc_bone_trabecular_thickness` /
`poc_weld_radiograph_porosity`(展示館 61 → 65)。

- 可視 3 バンド植生指数(ExG / NGRDI)が無い(`spec_index` は 2 バンド差のみ)。大津の**しきい値の
  値**を返す口が無い(`sk_otsu` は二値だけ)。`remove_small` の最小面積は画像の 1 % から。
  `trans_from_rgb` は 8 bit 経由(a* 1 刻み)。
- 減衰比 ζ(半値幅 / 対数減衰率 / 減衰正弦波当てはめ)、MAC、測点列からのモード形状抽出、1-D の
  理想帯域通過(`temporal_bandpass` は 1×1 を拒む)、スペクトル線のサブビン読みが無い。
  `phase_displacement` の `dy` は画面の上下 8 行で 0.43〜0.99 倍に落ち `valid`/`weight` に出ない。
  `wrap_limit_px`(0.018 px)は実用の限界(3 px でも f_1 +0.011 Hz)と 2 桁ずれている。
- 2-D の局所厚さ(Hildebrand の最大内接円)が無く `blob_distance` を半径ごとに回した。
  `dist_transform` / `cv_dist` / `xsp_chamfer_dist` は最大値で正規化され画素単位の距離は
  `ledger.blob_distance` のみ。`add_noise_white` の σ は 0.02〜0.22 に固定。
- 背景推定 op の窓上限(矩形オープニング 9 px)が気孔の検出範囲を決めていた(2.0 mm から
  50 % を割る)。等級表・キャリパ径など RT 特有の処理は自前。
- **Agent 運用**: 4 本同時でも、成果物を書いた後に報告なしで止まる Agent が 6/12 本。原因は
  Bash の `cat`/heredoc が **stdin 待ちで固まる**(本人の最後のメッセージに「stray `cat` line
  hung on stdin」)。ブリーフに「ファイルは Write ツールで書く。heredoc / 対話コマンド禁止」を
  足すこと。止まった Agent の docstring は改訂途中で、**数字がログと食い違う**(骨梁: 117.6 vs
  104.8 µm、溶接: 等級誤り 90 % → 23 %)。取り込む前に「キャプションの数字が実行ログに
  存在するか」を機械で照合する(scratchpad の check を tools 化する価値あり)。
- ★**`git add -A` は走っている Agent の書きかけを巻き込む**(2026-09-07、master が赤に)。
  第 3 バッチを commit した時点で、第 4 バッチの Agent が書いている途中の
  `examples/poc_fresco_craquelure.py` が index に入り、`examples2d` 未登録のまま push された
  (`test_examples2d` と `test_opdocs` が CI で落ちた)。auto-commit hook も同じ形で書きかけを拾う。
  **対策**: PoC バッチの commit は `git add` に**明示パス**を並べる(`examples/poc_<id>.py`、
  `docs/articles/assets/poc/poc_<id>/`、生成物の docs)。あるいは Agent が全部終わってから add する。

### 11. PoC 第 4 バッチ(2026-09-07、4 本)が見つけた穴

`poc_fresco_craquelure` / `poc_solar_el_inspection` / `poc_tree_ring_dendro` /
`poc_solder_fillet_aoi`(展示館 65 → 69)。

- ★**`otsu` が雑音の無い 2 値画像(0.3 / 0.8)で全画素を前景にする**(4096/4096)。
  `sk_otsu` / `cv_otsu` は正しく 128。256 ビンヒストグラムの端の扱いと見られる(**要修正**)。
- ★`lines_gauss` の XLD は連結成分の画素をラスタ順に並べただけで、`total_length` が
  80√2 px の線分に 825 px(7.3 倍)を返す(`poc_solar_el_inspection` §9(e) に assert)。
- `sk_frangi` / `sk_meijering` / `sk_hessian` は画像ごとの最大値正規化なので、検査用途で
  **絶対しきい値を持てない**(校正線が画像中で最強でないと尺度が定まらない)。
  距離変換(`distance_transform` / `cv_dist` / `xsp_chamfer_dist`)と blackhat も同様に正規化され、
  画素単位の幅が取れない。
- 大窓の背景推定が無い(`gaussian` σ ≤ 3、`rolling_ball` r ≤ 25、ピラミッド 1/16 止まり)。
  「行の関数 × 列の関数」で割る分離可能な格子除去、cos⁴ ビネッティングの当てはめ口も無い。
  `hysteresis_threshold` のしきい値範囲は 0.2–0.5 / 0.5–0.8 に固定。
- 骨格の枝ごとの弧長・弦長(直線度)、分岐点の**次数**(`junctions_skeleton` は位置のみ)、
  枝の向きの異方性、骨格の折れ線長が無い。
- 髄中心の極座標展開は台帳 `polar_unwrap` のみで 1 行ファサードが無い(進化 op
  `polar_trans_image` は中心固定)。測定線の束を一括で置く口、外縁で半径を正規化する
  アンラップ、`find_peaks` の prominence が無い。
- リング光源(仰角窓 × 全方位)を BRDF で積分して「傾き → 色」表を作る口、列方向の
  多値ラベル run-length、混同行列 / ROC の評価器(3 本目の指摘)が無い。
- `trans_from_rgb` の H は OpenCV 8 bit の 0–179 を 255 で割った値(青 220° → 0.431)で、
  docstring からは読めない。

### §41.12 3-D バッチ(展示館 69 → 73)で見つけた穴

`poc_mesh_quality_repair` / `poc_lidar_terrain_change` / `poc_cad_scan_deviation` /
`poc_dfm_thickness_overhang` の 4 本。すべて合成の真値つき(外部データを落とさない)。

**契約違反(直す価値がある)**

- **「台帳アダプタが複数戻り値を切り落とす」は 3 人が別々にバグとして報告してきたが、
  検証したらバグではなかった。** `gicp` は `rmse` / `iterations` を、`grid_coords` は
  `extent` を、`voxel_to_mesh` は `normals` を落とすが、これは `RESULT_ADAPTERS` に
  よる設計(台帳経由は宣言 out 型の値だけを返す = 型忠実な連鎖のため)で、
  `fs.ledger.<名>.raw(...)` という逃げ道も既にあった。**問題は道具ではなく説明**で、
  該当する **85 op(12 族)のノートに一度もその旨が書かれていなかった**。
  3 人が独立に同じ石につまずいたのがその証拠。→ `tools/opdocs.py` の
  `result_adapter_hints()` で、85 op のノートと Studio ヘルプ(6 言語)に
  「台帳経由は `<out>` だけを返す / 本体の返りは `(labels, n)` / 要るときは `.raw`」を
  自動で出すようにした(2026-09-07 に修正済み)。
- `icp_point2point_3d` は numpy を渡しても `torch.Tensor` を返す(入力の型に戻らない)。
- `decimate_qem` は退化三角形(面積ゼロ)を出し、その出力を `vertex_curvature` /
  `face_normals` に渡すと落ちる。しかも「退化」の定義がライブラリ内で 3 通りある。
- `fill_holes` が 2 つある(2-D 領域用と 3-D メッシュ用)。名前だけでは選べない。
- `estimate_normals` は平面上のサンプルで 63 % の法線が裏返る(符号の任意性を
  呼び手が知らないと、傾き = 法線から出す判定がそのまま反転する)。

**軸と単位の規約**

- 点の op は `(N,3) = (x,y,z)`、ボリュームの op は `(depth,row,col)`。同じ PoC で
  両方を使うと入れ替えが要る。どちらの規約かは docstring から読めない。

**無い口(足す価値がある)**

- ~~`sdf_*` のプリミティブは球と直方体だけ~~ → **2026-09-07 に `plane_sdf` /
  `cylinder_sdf` / `torus_sdf` / `capsule_sdf` を追加**(閉形式で厳密。円筒穴・面取り・
  フィレット・掃引体積が CSG で組めるようになった)。
- ~~**面ごとの面積**を返す op が無い~~ → **`face_areas` を追加**(総和が `mesh_area` と
  一致することを門で固定。`face_normals` と同じ並びなので重みとして直接使える)。
- 境界と体積 → **`boundary_vertices`(空なら水密)と `mesh_volume`(発散定理・符号付き。
  巻き順を裏返すと符号が反転する)を追加**。まだ無いのは**縁のループ(周回順)の抽出**と
  **自己交差の検出**。
- ~~点群の変化検出に M3C2 が無い~~ → **`m3c2_distance` を追加**(2026-09-07。
  法線方向の符号つき差 + 検出限界 `lod`)。まだ無いのは点群 → DEM のラスタ化、
  地面点の分類、LoD(詳細度)。
- DFM の判定(オーバーハング面積・自己支持角・工具到達性)そのものが op になって
  いない。材料はすべて揃っているので、族として足せる。
- 1 行ファサード `fs.<名>` に出ていない 3-D op が多い(`face_normals` / `mesh_area` /
  `esdf` / `box_sdf` / `voxel_to_mesh` など。`fs.ledger` からのみ)。

**この 4 本が測ったこと(要点)**

- 合わせると欠陥が消える、が 4 本に共通の主題。位置合わせは反りを姿勢に吸わせて
  中央に実在しない -121.1 µm のへこみを作り(閉形式の予測 -a/3 = -120.5 µm)、
  等値面の平滑化は 45 度に貼りついた面の帰属を変えて要サポート面積の段差を消す
  (距離場から取ると 100 %、σ=1.5 voxel で 12 %)。
- 欠陥の薄まりは深さでなく**広がりの面積**で決まる(深さ 30 倍でも 2.5 % のまま、
  σ 2 → 10 mm で 0.81 → 8.49 %)。
- 肉厚は 2 voxel 刻みに潰れる。「最大内接球なら 1 voxel 刻み」という予想は外れ、
  12 点すべてで侵食と同値だった(2 値格子では直径が量子化される)。

### §41.13 torch が要らないのに必須だった 5 op / 合否を捨てていた門(2026-09-07 夜)

CI の py3.10 / 3.12 は **torch を入れない**(サイズと時間。3.11 だけ入れる)。手元には
torch があるので、**手元で緑・CI で赤**という一番たちの悪い形で出た。

- **torch が要らないのに必須だった 7 op**。`icp_point2point_3d` / `icp_point2plane` /
  `register_fpfh` / `match_phase_3d` / `polar_unwrap` / `cylinder_unwrap` /
  `render_volume_projection`。
  中身は cKDTree の最近傍・3x3 と 6x6 の線形代数・FFT・双線形補間で、**GPU の仕事が
  1 つも無い**のに torch を掴んでいた(`register_fpfh` に至っては**返り値を包むためだけ**)。
  すべて numpy / scipy に書き換え、torch があるときの返り値の型は据え置き
  (`torch.Tensor`)、無ければ同じ値の numpy を返す。torch 版との差は実測で
  R/t が 0、RMSE が 0、双線形は 6.0e-06 と 7.6e-06(float32 の丸めぶん)。
- ★**門が合否を計算した直後に捨てていた**。`tests/test_poc_scripts_run.py` は
  「exit 0 だが PASS を印字していない」を判定しておきながら **0 を返して**いたので、
  すぐ下の `assert code == 0` を必ず通っていた。実測でこの穴に落ちていた PoC が
  3 本(`poc_dic_strain` / `poc_photoelasticity` / `poc_thermography_ndt`)—— いずれも
  **assert がゼロ・PASS 行なし**で、走ってはいるが何も検証していなかった。-2 を返すよう
  直し、3 本には所見を固定する assert を入れた(51 個)。**門は壊して確かめた** ——
  PASS を印字しない捨てスクリプトで code=-2、PASS を出すもので code=0 を実測。
- ★**片側だけ狭い契約**: `esdf` は長さ 3 の異方 `voxel_size` を受けるのに、その出力を
  world 座標で引く `query_distance` は `int(res)` で立方格子限定だった。CT の薄い
  接合層 (30,180,180) では引けない。軸ごとの `res` を受けるよう直した(2026-09-07)。
  **同じ族の入口と出口で契約の広さが違わないか**を、族ごとに一度見ること。
- ★**assert を足したら、本文の主張が実測と食い違っていたのが 5 件出た**(上の 3 本)。
  いちばん重いのは `poc_photoelasticity` §5 で、本文は「壊れる画素はマスクで外せる
  ので、渡さないのは手順の欠落であって道具の限界ではない」と読ませていたが、実測は
  **逆**だった —— マスク無し 97.0 % / 標本化不足だけ外して 97.1 % / **低変調まで外すと
  81.9 %**。外すほど領域が分断され、`unwrap_phase_2d` が島ごとに別の 2π を選ぶ。
  つまり要るのは「捨てる口」ではなく**重みつきアンラップ**。ほかに
  `poc_dic_strain` の「100 µε でも符号と桁は出る」(hs は 22.4 µε = 真値の 1/4)、
  「piv の偏りは 1 桁小さい」(掃引の最大どうしでは 5.9 倍)、`poc_thermography_ndt` の
  「0.3 % 以内」(最悪 0.34 %)、「+59 %〜+612 %」(2 セルは −4 % と −12 %)。
  **assert が無い所見は、いずれ本文だけが独り歩きする。**
- 手元で CI の条件を再現するには `tools/run_without_torch.py <script>`
  (`importlib.util.find_spec("torch")` を None にし、meta_path でも実 import を塞ぐ)。
  これで 77 本すべてを掃いて、上の 5 op を洗い出した。

### §41.14 安全距離・庫内フロー・設備保全の PoC が暴いたもの(2026-09-08)

- ★**`distance_line_line` は無限直線**。離れた 2 線分に 0 を返す(実測 0.0 / 真値 4.0)。
  手足・リンク・配管は有限なので、安全距離では**危険を過小評価する側**に外れる。
  → `distance_segment_segment` を追加(総当たりと完全一致。最近接点も返す)。
- ★**`voxel_to_mesh` の巻き順は内向き**なので、そのまま `mesh_volume` に渡すと
  中身のある形でも負になる(1000 voxel の立方体で -985.67)。両方の docstring に
  相互参照を入れた。**同じ族の 2 op を並べて使う経路は、一度実際に繋いで確かめる**。
- **3-D の形態演算に軸ごと(線)の構造要素が無い**(`vol_erode` / `vol_opening_ball` は
  球のみ)。x-y-t を 1 つのボリュームとして扱う解析は時間軸方向の線が要る。
- **検出列を ID に結ぶ口が無い**(gated NN / Hungarian)。`track_points` は画像ベースの
  Lucas-Kanade で、既にある検出列を軌跡に束ねられない。PoC 2 本が同じ穴を踏んだ。
- **検出と真値の突き合わせ(時間の重なり + 距離)とクラス別再現率**が無い。
  PoC シリーズで**3 回目**の手書き。`fscore` は 2 クラスのみ。
- **`acoustics.stft` の COLA 検査が「1 枠だけ欲しい」を塞ぐ**(`hop=win` で ValueError)。
  1 本の記録の片側振幅スペクトルを出す口が無く、numpy の rfft に落ちる。
- **線分・カプセル ↔ 直方体の距離**、**SDF からの最近接点**、**SDF 上のレイマーチ
  (可視判定)**、**ISO/TS 15066 の分離距離式**がいずれも無い。
- ★**「効かないつまみ」の台帳が版に依存していた**。この台帳は図を作った環境で書かれ、
  テストを走らせる環境で検証される。cv2 の実装は版で変わるので、手元(opencv 5.0)で
  効かないつまみが CI(opencv-contrib 4.x)では効く —— 実測で `xcv_grabcut` の b。
  門は 30 本を間引いて見るので、op が増えて間引きの位置がずれた瞬間に露見した
  (**前から在ったのに、たまたま当たっていなかった**)。第三者バックエンド由来の
  op(`cv_` / `xcv_` / `sk_` / `xsk_`、1058 中 118)は台帳の主張から外した ——
  **狭くて正しい台帳のほうが、広くて嘘のある台帳よりよい**。
- ★**GIF がコマごとに正規化されていた** —— 体積・動画で「軸に沿って何が変わるか」が
  消える。平面の距離場では全コマが画素単位で同一になり PIL が 1 コマに畳んだ。
  列全体で 1 つのスケールに直した。**「1 コマ」を数える門が無ければ気づけなかった**。
- `examplefig.save_grid` はパネル説明が幅に入らないと**図全体を落とす**(例外でなく
  `figs.errors()` にだけ出る)。図が黙って消えるので、呼び手は errors() を必ず読む。

---

## §42 「記録は在るのに、それを読む側が現実から取り残されていた」回(2026-09-08)

この回の発端は 1 件の観察 ——「``examplefig`` は図を書けなかった理由を
``errors()`` に積むが、**誰も読んでいない**」。ユーザーの「同じタイプの問題が
無いか調べておいて」を受けて横断で洗ったところ、**同じ型が 5 つ**出た。
どれも「門が無い」のではなく、**門も記録も在るのに、判定に使う側が古い / 狭い /
読まれない**という形をしている。

### 42.1 図の失敗を溜めるだけで誰も読まない(発端)

``annotate_figure_grid`` はパネル説明が幅に入らないと拒否する —— これは正しい
(切り詰めたら機械が検査できない)。ところが ``examplefig.save_grid`` はその
例外を ``_errors`` に積んで ``None`` を返すだけで、**PoC はそのまま ``PASS`` を
印字する**。29×19 の core 格子や縮小マップは PoC で普通に出るので、担当 2 人が
別々に踏み、**看板に選ばれる ``scene`` 図が 1 枚消えたまま**通った。

* 原因の側: パネルが小さいと題が入らない。エラーは「題を短くしろ」と言うが、
  実際の直し方は「パネルを大きくしろ」。``save_grid`` が**最近傍で整数倍に拡大**
  してから組むようにした(最近傍にするのは、拡大で存在しない中間値を作らないため)。
* 見える側: ``atexit`` で ``_errors`` を必ず標準出力に出す。図が出ない設計
  (``FULLSEYE_FIGURE_DIR`` 未設定)では何も出さない。

### 42.2 探針の門が 17 sort 中 4 つにしか入力を作っていなかった

``tests/test_op_probe_ledger.py`` は「レジストリの全 op を構造つき入力で走らせる」
と謳いながら、``image`` / ``region`` / ``color`` / ``volume`` の 4 sort しか入力を
作っていなかった。``contour`` 65 / ``points`` 57 / ``signal`` 26 / ``video`` 16 …
**217 op(901 本の 24 %)が "uncallable" として素通り**。しかも門の閾値が
``>= 0.7 * len(probe)`` だったので、**その状態が合格として固定**されていた。

``op_probe`` に 8 sort ぶんの構造つき探針(動く円のある動画、純四元数、位相ランプの
複素画像、視差が線形なライトフィールド、既知の 1 目標の FMCW、TCSPC の指数減衰、
既知の楕円上の keypoints、相関のある行列)を足して**到達率 76 % → 100 %**。
閾値は「1 本でも届かなければ失敗」に変えた。

広げた初回に出たもの:

* **``tb_angle_3points``** —— 登録は ``points → measurement`` だが実体は
  ``angle_3points(a, b, c)`` で**3 本のベクトル**を取る。点群 1 本を渡す橋では
  毎回 ValueError になり、fail-soft がもっともらしい float(0.4637)を返していた。
  = **登録されているのに一度も走ったことがない op**。
* **``tb_indices_to_labels``** —— 1-D の選択マスクを返すのに、宣言 out ``labels``
  は ``volume``(ndim 3)に畳まれる。毎回「op returned (93,) but declared out_sort
  'volume'」で fail-soft。全 901 本を掃いて、宣言 out と実際の形が食い違う橋 op は
  **この 1 件だけ**だった。

どちらも ``backends_typed._OP_BRIDGE_SKIP`` へ移した(台帳経由の呼び出しは不変)。
★**記録は在った。しかも 3 つ**:

1. ``tools/gen_op_figures.py`` の ``DOMAIN_MISMATCH`` は 2 本とも「定義域の外」として
   理由つきで挙げていた(ただし「図が出ない」理由としてで、「走れない」理由としてではない)。
2. ``tests/test_backends_typed_liveness.py`` の ``KNOWN_DEAD_BRIDGES`` は
   ``tb_indices_to_labels`` を **「実測 0/60」**、つまり**一度も走っていない**と
   正確に書いていた。直し方(型語彙を『体積のラベル』と『列のラベル』に分ける)まで
   書いてあり、「消費 op の無い型を増やすと袋小路になるので単独では入れない」と
   保留していた —— その判断自体は妥当だが、**保留のあいだ op は登録されたままだった**。
3. op 自身が毎回出していた fail-soft の記録。

それでも探針の門は「レジストリの全 op を構造つき入力で走らせる」と名乗り続けていた。
**知っていることと、判定に使っていることは別**。今回の解は型語彙を増やさない側 ——
橋を架けないこと(``_OP_BRIDGE_SKIP``)で、袋小路の型を作らずに済ませた。

### 42.3 床が古いまま置き去りの門(5 か所)

============================  ======  ======  =======
対象                            床      実測    倍率
============================  ======  ======  =======
``examples2d.EXAMPLES``           57     181     3.2x
``examples/poc_*.py``             31      98     3.2x
``ops3d.OPS3D``                   80     356     4.5x
examples3d ギャラリー             20     117     5.8x
============================  ======  ======  =======

``assert len(_poc_paths()) >= 31`` は「PoC が 98 本から 31 本に消えても緑」という
意味である。床を ``docs/COLLECTION_SIZES.json`` に集約し、
``tests/test_collection_sizes.py`` が (1) 減ったら落ちる (2) **1.25 倍を超えて
育っても落ちる**(台帳の更新を強制する)の両方を見る。増加も摩擦にしないと、
また同じところへ戻る。

### 42.4 畳んだ型の請求書(``TYPE_TO_SORT``)

``backends_typed.TYPE_TO_SORT`` は宣言型を 5 組畳む。畳む判断自体は正しい
(``_SHAPE_OK`` の契約を両方が満たすときだけ畳む、という規約が既にある)が、
**またいだときにどれだけ間違うかが測られていなかった**。実測:

===========================  =========================================  ==========
畳み                          またいだときの実測                          fail-closed
===========================  =========================================  ==========
``sdf`` / ``labels``          ラベルを ``sdf_to_occupancy`` に渡すと      不可
                              背景を内側と数える。真値 1,728 → **9,504**
``image2d`` / ``depth``       正規化した濃淡を深度として渡すと法線が       不可
                              **3.024 度**ずれる(深度なら 0.000)
``points`` / ``normals``      位置の雲を ``normals_to_egi`` に渡すと      **可**
                              非零 bin 1 → 12、**総和はどちらも 200**
``signal`` / ``indices``      連続値は既に ValueError で拒否(手本)       **可**
``counts`` / ``countrate``    2 度掛けると 1.2 → 0.0012 counts            不可
                              (**1,000 倍**、例外なし)
===========================  =========================================  ==========

``docs/TYPE_ALIAS_LEDGER.json`` に 1 行ずつ残し、``tests/test_type_alias_ledger.py``
が「TYPE_TO_SORT から導いた組 == 台帳の組」と「fail_closed と書いた行は実際に
例外が出る」を毎回測る。検出できない 3 件は各 op の docstring に実測値を書いた ——
値だけを見て「深度か濃淡か」「Hz か counts か」を判定する方法は無いので、
そこは検査でなく呼ぶ側の規律で守るしかない、と明示する。

### 42.5 値域 [0,1] の契約が、書いてあるだけだった

``ops.py`` の 1 行目は ``image : gray raster, float64 in [0,1]`` と宣言している。
dtype は 2026-09-03 に fail-closed にしたが、**値域は誰も検査していなかった**。
PoC 2 本が独立に踏んだ: µm 単位の高さ場(値域 0〜50)を ``auto_threshold`` に
渡すと Otsu が「0.5 µm」の位置で切り、blob が 387 個(正解 256)出る。

画像 op 530 本を尺度 ×1000 / ×0.001 で掃引した内訳:

* **SCALE-BOUND 328 本(61.9 %)** —— ``op(k·x)`` が ``op(x)`` から説明できない
  (絶対値のしきい値を内側に持つ)
* 不変 81 本(15.3 %)/ 斉次 65 本(12.3 %)/ 判定不能 56 本

つまり op ごとの罠ではなく**入口の契約の問題**なので、328 本を個別に直すのでは
なく ``api._check_input_range`` を 1 か所に置いた。``extra_checks='on'`` のときだけ
拒否する(``fssystem`` の ``tightens_only`` 規約。進化器は正規化した絵しか流さず、
意図して範囲外を渡している呼び手を既定で壊さないため)。実測の差は
前景 668 → 2,256 画素(3.4 倍)で、これを門の数字として固定した。

### 42.6 editable 側の ``FAILED_BACKENDS`` を誰も読んでいなかった

``tools/ci_wheel_check.py`` は wheel 側の ``failed_backends`` だけを見ていた。
editable の venv は optional 依存が**多い**ので、版の食い違いで backend が import に
失敗しうる。そのとき wheel 側は「依存が無いから最初から居ない」だけで失敗を
記録せず、比較は緑のまま通る —— 落ちた backend の op はレジストリから黙って消える。
両側を見るようにした。

### 42.7 この回に踏んだ「自分の側の」間違い(honest)

* 軸の並びの監査で、最初に **out 型ごとに判定を変えなかった**(volume は「同じ」で
  なく「転置して同じ」が正しい期待)。そのまま報告していたら 37 件を「軸依存」と
  誤報していた。正しい判定に直すと 23 件。
* その 23 件のうち 3 件は**探針の縮退**だった。2 枚目の探針に「傾いた直線 + 柱」を
  選んだが、どちらも共線なので法線の最小固有ベクトルが一意に決まらない。
  箱の 6 面 + 螺旋に替えると 209/210 が一致し、残る 1 点は kNN の同点。
  **探針の縮退を op の欠陥と読み違えない**。
* ``ops3d.OPS3D`` の本数を ``sum(len(v) for v in values())`` で数えて **2,492** と
  出し、台帳に刻む直前に構造を見て気づいた(正しくは 356 = 各 op のメタデータの
  キー数を足していた)。**数える前に、何を数えているかを見る**。

---

## §43 疑似カラーの「種類」を数え直した回(2026-09-08)

ユーザーの一言 ——「疑似カラーの入れ方の種類が少なくないか?」。数えると
palette は 16 あったので、最初は「そこそこ在る」と答えかけた。測ってみると
**足りないのは枚数ではなく軸**だった。

### 43.1 パレットと直交する軸 —— 値をどう色に写すか

``normalize`` は**線形しか無かった**。実務で効くのはこちらのほうで、桁の広い強度、
外れ値 1 個で潰れる場、0 を中央に置きたい発散量は、どのパレットを選んでも
線形のままでは読めない。``NORMS`` として 8 通りを足した(``linear`` / ``log`` /
``symlog`` / ``sqrt`` / ``power`` / ``percentile`` / ``rank`` / ``symmetric``)。

実測(400 点のランプに外れ値 1 個 ``1e6`` を混ぜ、相異なる色の数を数える):

* 線形 —— **10 色未満**(全部が下端に潰れる)
* ``rank``(分位)—— **100 色以上**

★門を書いた初回に「``log`` と ``rank`` が同じ写し方だ」と鳴った。これは**探針の
縮退**で、指数ランプは対数を取ると等間隔なので分位も等間隔になる —— 数学的に
一致するのが正しい。対数正規の標本を 2 枚目に足して「どちらかで違えばよい」に
直した。この回で**探針の縮退を欠陥と読み違えかけたのは 3 度目**(§42.7)。

### 43.2 範囲外と正当な最小値が同じ色だった

``apply_cmap`` は ``[vmin, vmax]`` の外を端の色へ丸めていた。実測: ``vmin`` を
省いても ``-5`` は viridis の下端 ``(0.267, 0.005, 0.329)`` になり、**振り切れたのか
ちょうど下端なのか、図からは区別できない**。``invalid`` は非有限だけを塗るので
ここには効かない。``under`` / ``over`` を足した(既定は従来どおり丸める ——
既存の図を変えないため)。

### 43.3 種類そのものが欠けていた 3 つ

* **巡回**(位相・方位)が ``hsv`` の 1 枚だけ。しかも明度が **5 回**行き来する。
  干渉計・モノジェニック位相・四元数と位相を扱う op が多いのに、位相用の素直な
  マップが無かった。``twilight`` / ``phase`` を追加(端と端の色差 < 0.02 を門にした)。
* **質的**(ラベル)が乱数 RGB だけ。``QUALITATIVE``(``tab10`` / Wong 2011 の
  色覚安全 8 色)と ``colorize_categorical`` を追加。連続マップをラベルに使うと
  **番号の大小が「近さ」に見える** —— ラベル 3 と 4 は隣の領域ではない。
* **等輝度**が無い。明度の動くマップを陰影に重ねると、「明るい = 値が大きい」のか
  「明るい = 南斜面」なのか読者に切り分けられない。``isolum`` を追加。

### 43.4 2 つの量を 1 枚に載せる道具が 1 例だけ焼き込まれていた

``colorize_flow``(向き = 色相、大きさ = 彩度)は二変量マップの 1 例なのに、
一般の口が無かった。``colorize_bivariate``(色 = 値 / 明るさ = 信頼度)と
``colorize_significance``(有意でないセルを灰へ)を足した。
``poc_settlement_significance`` が実測した「平均は -2.43 mm 沈んだ / 有意なのは
49.9 % で、その平均は -4.34 mm」は、まさに 1 枚に畳むと前者しか読めない形。

### 43.5 既定が「構造を捏造する側」だった

``colorize_disparity`` の既定は ``jet`` だった。CIE L* を 256 段で測った明度の
折返し(増減が反転した回数)と、刻みの変動係数:

==============  ==========  ==================
マップ          折返し      刻みの変動係数
==============  ==========  ==================
``hsv``                  5                0.97
``jet``(旧既定)        3                0.60
``turbo``(新既定)      1                0.42
``viridis``              0                0.08
==============  ==========  ==================

折返しは「値が単調に増えているのに明るさが行って戻る」回数で、**無い境目が
見える**原因。虹色という現場の慣習は ``turbo`` で残しつつ既定を変えた
(``name="jet"`` で従来どおり)。``PERCEPTUAL_SAFE`` に折返し 0 のものを列挙して、
「どれを選べばよいか」を道具の側が持つようにした —— 19 個並べて選ばせるのは案内ではない。

### 43.6 ここでも「族の中の契約が片側だけ」だった

``apply_cmap`` は ``vmin`` / ``vmax`` / ``invalid`` を持っていたのに、
``colorize_depth`` / ``colorize_disparity`` という**薄い包みが ``name`` しか
受け取らず**、下の層の契約を落としていた。§42 で 3 回踏んだのと同じ形
(``normals_from_depth`` の ``spacing``、台帳 op の返り値、``failed_backends`` の
editable 側)。``**kw`` で素通しにし、門で確かめる。

---

## §44 実写を初めて通した(2026-09-08)—— 合成では作れない型の躓き

ユーザー「実際の画像でやってみた場合も見てみたいけどね」「実データが得られる
ものはやってみてください。何かダメな部分とか見つかるかも知れない」。

この repo の PoC は**自分で真値を仕込む**規律で書いてある(合成なら答えが
データの外に無く、崖も対照群も設計できる)。ただし合成は**自分が知っている
壊れ方しか作れない**。追加ダウンロード無しで手元にある実写(`scikit-image`
同梱の部分集合。ライセンスは `realdata.SAMPLE_PHOTOS` に 1 件ずつ)を 2 本通したら、
**1 日で 5 件**出た。`examples/poc_real_stereo_depth.py` /
`examples/poc_real_coin_metrology.py`。

### §44.1 「欠測は NaN」という思い込みが 2.4 px の偏りになる

Middlebury 2014 の真値視差は、配布元(skimage)の docstring が
「NaNs denote pixels ... that do not have ground-truth」と書いている。
**実際は NaN が 0 個、+inf が 27,226 個**。`np.nanmax` / `np.nanmedian` は
inf を除かないので、中央視差を 42.55 px でなく **44.97 px** と答える。

★同じ repo の中でも流儀が割れていない側は強い: `fill_disparity` と
`apply_cmap` は `np.isfinite` で判定しているので **+inf を正しく穴として
扱った**(埋めた後の非有限 0 個、既知画素のずれ 0、穴の色は invalid 色 1 種で
有限側と衝突なし)。**nan 系 API を使うところは、inf でも正しいかを別に問う**。

### §44.2 ★★`depth_from_disparity` に主点オフセットが無かった(修正済)

実写の rectified データは `doffs = cx_right - cx_left` を必ず配る
(Middlebury 2014 motorcycle は 31.086 px)。`Z = f*B/d` しか無いと、
**距離が視差ごとに違う倍率でずれる** —— 実測で 1.519〜5.243 倍。
だから後から 1 つの係数を掛けても直らない: 最良の単一スケール 0.3733 を
当ててなお残差 **958.3 mm RMS**(奥行きレンジ 2889 mm の 33.2 %)、
遠い面は +1676 mm 押し出され近い面は -926 mm 引き込まれる。**平面が平面で
なくなる**。`doffs` 引数を追加(既定 0.0 = 従来と完全同一、渡せば閉形式と
最大差 0 mm)。門 = `tests/test_stereo.py::test_depth_from_disparity_honours_the_principal_point_offset`
は「単一スケールでは戻らない」ことまで固定する。

**合成では出なかった理由**: 合成データは自分で生成するので doffs = 0。
**生成器が知らない量は、テストにも現れない**。

### §44.3 既定値が実物の目盛りに届かない

`disparity_map(max_disp=16)` の既定は、真値が 7.33〜59.91 px あるこの場面で
bad2 **95.06 %**。崖は 48(46.79 %)と 64(26.75 %)の間にあり、**測る前に
幾何から言える**(探索範囲に無い視差は表現できない)。80 に広げると 27.11 %
と少し戻る(余分な範囲が偽の一致を拾う)。

### §44.4 ★`hough_circle_trans` の半径がコードに直書きで、`b` が未使用だった(部分修正)

実写のコイン(半径 19〜31 px)に対し、この op は半径 4〜19 しか探していない。
**落ちずに意味の無い累算器を返す**。`b` を半径の上限に配線した
(`radii = arange(4, max(7, round(4 + 32*b)), 3)`、`b=0.5` は従来と完全同一)。
★ただし**引数を足しても足りない**: 非極大抑制して峰を数えると b=0.5 で 13、
b=1.0 でも **19**(真値 24)。半径の刻みが 3 で、しかも全半径の最大に潰して
いるため。**半径を明示できる HALCON の同名 op の代わりにはならない**、と
docstring に書いた。真値の経路は skimage の `hough_circle` に半径を明示して取る。

### §44.5 ★★答えが合っていても、余裕があるとは限らない

`coins` は「照明が斜めなので大域しきい値では駄目」の例として有名で、背景は
確かに行 0.427 -> 0.161 / 列 0.331 -> 0.059 と傾いている。ところが**素の大域
Otsu + 穴埋め + 面積 150 が真値 24 枚をちょうど当てる**(面積の平坦域 50〜800、
半径明示 Hough、Sobel+穴埋めの 3 経路一致 + 円 1 個が成分 1 個に収まる
1 対 1 の検算まで通る)。

**しかし余裕は 0.05** —— 同じ形の勾配をわずかに足すだけで 24 -> 22 枚。
さらに +0.30 では面積の**中央値が -0.27 % しか動かないのに最悪のコインは
-24.20 %**(+0.40 で -46.02 %)、そのずれは行位置と **r = -0.90** で相関する。
真の面積は置き場所に依らないので、**この相関はまるごと誤差**。
代表値 1 個で報告すると、壊れているのに壊れていないように見える。

★24 個のうち 1 個は面積 9076(中央 1501 の 6 倍、Hough 半径の上限から言える
上限 3019 の 3 倍)で背景へにじんでいる —— **「枚数が合った」と「領域が
正しい」は別**。★`gray_tophat` で平坦化すると枚数は粘るが面積の中央値が
0.29 倍になる(**枚数の頑健さと寸法の頑健さは別の話**)。

### §44.6 ついでに確かめたこと(門を壊して確かめる)

`backends_auto.py` を編集中に構文エラーを入れてしまったとき、`import fullseye`
は成功し**レジストリが 979 -> 676 に黙って減った**。既存の門を疑う前に
実際に走らせたところ、`tests/test_fallback_policy.py::test_failed_backend_imports_are_visible`
ほか 4 件が正しく落ちた(`FAILED_BACKENDS` に理由つきで載る)。
**この経路の門は健在**。[[feedback_gate_must_stand_where_the_accident_happens]]
の言う「壊して確かめる」を偶然やる形になった。

### §44.7 実データ層の設計(fail-closed)

`realdata.py`: 追加ダウンロードをしない(回線に依存すると、落ちた理由が実装か
ネットワークか分からなくなる)。データが無いときは**理由を印字して
`SystemExit(1)`** —— 「実データが無かったので何も検査せず PASS」は、この repo が
いちばん嫌う形(§42 の「記録は在るのに誰も読まない門」)そのものなので。
CI は 3 つの matrix すべてに `skimage` extra を入れているので、実データ PoC は
**必ず走る**。公開する図に使うのは CC0 / public domain / no known copyright
restrictions のものだけ(Middlebury は研究・教育目的の引用付き利用、GCPR 2014)。

### §44.8 前日の門が CI で赤になった 2 件(自分の回帰・修正済)

実データ作業とは別に、§42 で入れた門が Linux CI で落ちた。**どちらも
「手元にあるものが CI にも在る」と思い込んだ形**で、
[[feedback_gate_computed_a_verdict_then_discarded_it]] の言う
「手元緑・CI 赤」そのもの。

1. **`tests/test_honest_summary_arithmetic.py`(2 件)** ——
   `data/halcon_operators.json` は 549 KB の外部由来コーパスで**リポジトリに
   入れていない**(再配布の可否を確かめていない)。手元にしか無いものを
   無条件に読んでいた。ファイルが無ければ**理由を言って skip** するようにした。
2. **`tests/test_op_probe_ledger.py::test_no_op_falls_back_or_raises_on_the_structured_probe`**
   —— 探針を全 sort に広げた初回に、torch を要る op(`tb_points_to_voxel`)へ
   **初めて到達した**。torch を入れない py3.10 / py3.12 では
   `ImportError: needs the optional 'torch' backend` になる。
   ★**「壊れている」と「この環境に無い」は別の判定**で、混ぜると環境差が
   実装のバグに化ける。optional backend 起因は非 strict 環境では判定対象外にし、
   満杯の環境(`FULLSEYE_REQUIRE_OPTIONAL=1`)では従来どおり失敗にする
   (両方向に門が立つ、という ci.yml の既存の設計に合わせた)。

**教訓**: 門の到達範囲を広げたら、**広げた先が環境依存でないかを同時に見る**。
到達率 76 % -> 100 % は良い変更だったが、その 24 % には
「この環境には無いから走らない op」も混ざっていた。

### §44.9 実写 3・4 本目 —— 汚染は信頼度も同じ向きに膨らませる / 見張り役の盲点

**`poc_real_sky_photometry`(Hubble Deep Field、public domain)。**
真値は自分で仕込み、**背景だけ本物**にする(合成では作れない要因を 1 つだけ
入れ替える)設計。

* **実写の空は正規分布ではない**。頑健なばらつき 1,474 e- に対し素の標準偏差は
  6,698 e-(**4.54 倍**)。`std` をノイズだと思うと検出限界を 4.5 倍甘く出す。
* **背景は 1 つの数字ではない**。64x64 タイル 195 枚で 3,176〜8,448 e-。
  大域中央値 1 つで引くと最大 3.6σ の系統誤差。
* ★★**空だと思った場所でも開口に一定量が混入する**。回収比は F=2,000 e- で
  4.38 倍、100,000 で 1.058 倍 —— **倍率ではなく足し算**で、`1 + C/(F·frac)` に
  **最大ずれ 0.9 %** で乗る(C = 6,677 e-)。★「偏りが 10 % を切るのは
  67,521 e- から」と**先に予測してから**測ると 1.086(予測 1.100)。
* ★★**信頼度も同じ向きに嘘をつく**。op の SNR 中央値 19.2 に対し、同じ背景から
  の閉形式は 4.2。SNR は**測ったフラックス**から作るので、混入で分子が膨らむと
  S/N も膨らむ —— **S/N を採否の門にすると、汚染された測定ほど通る**。

**`poc_real_stain_unmix`(免疫染色、H + DAB)。**
この PoC のために `stain_unmix` / `stain_recompose` /
`stain_vectors_from_patches` + `STAIN_VECTORS` を新設した(`spec_unmix` は
3 チャネルを**設計上拒否**するので、RGB の染色分離には入口が無かった)。

* **合成では完璧に分かれる**(漏れ 0.0000)。実写では H の濃度が -4.446 まで
  振れ、負の画素 11.51 %。
* ★★**残差チャネルは平面内の誤りに構造的に盲目**。染色ベクトルを平面内で
  ±20 度回すと濃度の中央値は 2.86 倍動くのに、残差の絶対中央値は 0.0345 のまま
  **幅 3.3e-16**。2 本が張る平面は回しても変わらないので、直交成分は定義上
  動かない —— **「あてはまりの良さ」が、いちばん起こりやすい誤りだけを
  見ていない**。
* ★★**回した染色自身の負率も不変**(11.51 %、幅 0)。双対ベクトルの向きが
  変わらず長さだけ変わるので、符号は 1 画素も動かない。**動くのは相方の負率
  だけ**(-20 度 0.00 % -> +20 度 30.38 %)。**見張り役は自分ではなく相方を
  見る**。単調なので片側の上限しか出ない。
* **往復の再構成は最大 1e-06** —— 厳密に閉じるが、上の誤りを何も否定しない。
  **何を検算しているかを言わないと検算にならない**。

### §44.10 実写 5 本目 —— 3 つの物差しに 3 人の勝者

**`poc_real_deblur_honesty`(`camera`、CC0)。** 真値を**実写そのもの**にして、
劣化だけ自分で作る(直線ブレ 11 px・20 度 + 雑音 σ=0.004)。本物の細部に対して
「どれだけ戻せたか」を dB で言える。

* **ゼロ点(何もしない)24.04 dB は強い**。よく使われる `nsr=0.005` の Wiener は
  23.66 dB で**負ける**。
* ★★**そこで止めると相手を弱く見せたことになる**。`nsr` を振ると 19.18 〜
  **25.40 dB**。**ノブを固定した比較は比較ではない** —— この 1 行を書くために
  掃引を足した。
* ★★**ノブのほうが手法より効く**。`nsr` で動く幅 **6.22 dB** に対し、
  脱畳み込みをするかしないかの差は **1.36 dB**(**4.6 倍**)。
  §43 の「配色より写し方(`norm`)が効く」と同じ形が、別の族でも出た。
* ★★**同じ 7 通りに 3 つの物差しを当てると、別々の手法が 1 位になる**。
  PSNR = 正しい PSF の Wiener(25.40 dB)/ 勾配エネルギー = `iv_motion_deblur`
  (0.2986 = **真値 0.1936 の 1.54 倍**。真値より鋭い絵が選ばれる)/
  `sk_blur_effect` = `iv_unsharp_deblur`。**参照なし指標が選ぶ手法は PSNR で
  4.98 dB / 3.26 dB 損**をする。
* ★指標の名誉のために: `blur_effect` は**真値そのもの(0.2885)を全手法より
  良い**と正しく判定する。**「ぼけているか」は測れていて、それでも選ばせると
  損をする** —— 指標が壊れているのではなく、**代理量として使うのが誤り**。
* ★**間違った PSF は中身が悪くなるのに見た目が良くなる**。長さ 11 -> 21 px の
  取り違えで 18.56 dB(ゼロ点より **-5.48 dB**)なのに、勾配は真値の 1.37 倍。
* **崖(雑音)**: +1.52 dB(σ=0)-> **+0.05 dB(σ=0.016)**。1.6 % の雑音で
  脱畳み込みは何も買わない。**崖(ブレ長)は両端で落ちる**: L=3 +0.86 /
  **L=5 +1.59(山)** / L=25 +0.52 —— 小さいブレは取るものが無く、
  大きいブレは情報が消えている(先に予想できる形)。

### §44.11 実写 6 本目 —— 「回転不変」は、それが要らない素材でだけ成り立つ

**`poc_real_texture_invariance`(`brick` / `grass` / `gravel`、いずれも CC0)。**
実写のテクスチャを**既知の角度で回して**、記述子が自分自身からどれだけ離れるかを
測る。★**基準を先に置く** —— 素材どうしの距離のうち最小(草と砂利の
**0.01250**)がこの課題の分解能で、回転で動く量がこれを超えたら
**回した自分より別の素材のほうが近い**。

* ★★**異方な素材だけが壊れる**。brick は 5 度で 0.0433、60 度で 0.1205 =
  分解能の **9.64 倍**。grass / gravel は 0.0005〜0.0024(**0.17 / 0.19 倍**)。
* ★**犯人は補間ではない(対照群 2 つ)**。補間だけ(+7/-7 度の往復)は
  brick 0.03685。**補間ゼロの厳密 90 度(`np.rot90`)でも 0.08501 = 6.80 倍**。
* ★**異方性は独立に測れて順位を説明する**。勾配方向の大域的な偏り R は
  brick **0.309** 対 grass 0.027 / gravel 0.029。10 倍違うのは brick だけで、
  壊れるのも brick だけ。**測る前に予言できる**。
* ★★**「回転不変」な符号化に替えても 1 を割らない**。`default` 9.64 ->
  `ror` 5.49 -> `uniform` **1.72**。等方な 2 つは 0.17 -> 0.02 と **10 倍**
  良くなるのに、brick は 1 を下回らない。LBP の回転不変性は**局所パターンの
  巡回**に対するもので、**素材そのものの向きの分布**は消せないため。
  `nri_uniform`(回転不変でない uniform)が 4.24 なので、「uniform だから」
  ではなく「回転不変だから」効いていることも切り分けられる。
* ★**`sk_lbp` の `b` が未使用で `method` が `'default'` 固定だった**
  (§44.4 の `hough_circle_trans` と**同じ形**、同じ日に 2 件目)。
  **選べなければ下げようがない**ので `b` を符号化の選択に配線した
  (`b=0.5` は従来と完全に同一。閾値は表にしてある ——
  [[feedback_nested_conditionals_use_a_table]])。

**この族について言えるのは**「回転不変です」ではなく、**「等方な素材については
回転不変で、異方な素材については向きの情報がそのまま残る」** ——
前者は回転不変性が要らない場面、後者は要る場面。
[[feedback_invariance_claims_break_at_the_helper]] の新しい形。

### §44.12 CI の到達性の門が「埋もれた新モジュール」を捕まえた(修正済)

py3.11 の全体スイートだけが落ちた(py3.10 / 3.12 / core / lint は緑)。
`tests/test_public_reachability.py` の 2 件:

* `test_no_new_module_becomes_invisible` —— **`realdata` が公開経路
  (`fullseye.<名前>` / `.ledger` / `.op`)のどこからも呼べない**。
* `test_hidden_function_total_does_not_grow` —— 隠れ関数 1229 -> 1231。

この門は「配布物側から数える」設計(`pyproject.toml` の `py-modules` を
走査する)なので、§44.7 で `realdata` を出荷対象にした瞬間に**正しく反応した**。
[[feedback_registered_only_gates_miss_unregistered]] で入れた仕組みが働いた形。

**逃げ道(`_INTERNAL` に理由つきで足す)を取らなかった**。PoC の EXTEND は
利用者に `realdata` を指しており、内部専用ではないから ——
門のメッセージ自身が「利用者に出すなら台帳へ、内部専用なら `_INTERNAL` へ」と
二択を示している。公開する側を選び、ついでに**名前を公開に耐えるものへ改めた**:

    CATALOGUE   -> SAMPLE_PHOTOS          load_gray   -> sample_photo
    require     -> sample_photo_raw       load_rgb    -> sample_photo_rgb
    stereo_pair -> sample_stereo_pair     attribution -> sample_photo_credit

`fullseye.require` や `fullseye.load_gray` は公開名として悪い(何の require か
分からない)。**門に通すためだけの最小変更をせず、通したうえで名前を直す**。
実写 PoC 6 本の呼び出しも合わせて更新し、6 本とも PASS を再確認した。

## §45 外部 AI の市場提案を実物に当ててから PoC 化した回(2026-09-08)

外部 AI(Perplexity)から「fullseye で解ける実課題」の分野横断リスト(20 分野 +
推奨 3 件)が来た。**採る前に一件ずつ実コードで裏を取った**ところ、次が分かった。

### 45.1 提案そのものの検算

| 主張 | 実物 |
|---|---|
| 型付き op 1,500 超 | 登録レジストリ **885**(手元・torch/kornia 込み)/ **859**(Linux CI)、3-D op **356**、公開名 1,112 |
| 挙がったモジュール 49 個 | **46 個実在**。`measure1d` → `opsmeasure1d.py`、`pyramid` → `pyramid_*.py` と名前違い、**`thermal` は不在**(熱は `poc_pv_thermal_survey` / `poc_thermography_ndt` に PoC としてある) |
| 推奨 A「管路の円筒展開 4-D ツイン」 | **実装済み**。`poc_pipe_wall_loss` が展開図・軸ずれ・管底腐食が k=1 に埋まる話まで持っている |
| 推奨 B「リユース品の 3-D 差分査定」 | **実装済み**。`poc_cad_scan_deviation` が同じ骨格(合わせた分だけ欠陥が消える) |
| 推奨 C「データセンターの熱流体ツイン」 | **空白**。既存の熱 PoC はドローン熱画像とパルスサーモグラフィで、疎センサからの場の復元は無い |
| 出典 [1] UNESCO / [2] PMC | 本文と無関係。引用としては採れない |

**教訓は「提案が悪い」ではない** —— 20 分野のうち 2 つは既に作ってあり、3 つは本当に
空いていた。ただし**数字と固有名は 1 つも当てにできない**ので、採否は実物との照合で
決める。この照合に 10 分かけたおかげで、既存 PoC の作り直しを 2 本ぶん回避した。

### 45.2 空いていた 3 つを PoC にした(展示 105 → 108)

- **`poc_rail_corrugation`**(wing_metrology)—— 弦(正矢)測定。
  `|H(λ)| = |1 - cos(πL/λ)|` は λ = L/(2n) で厳密に 0、λ = L/(2n+1) で 2 倍。
  20 通りで予測と実測の差は最大 0.00000。★**予測を 1 つ外した**: 2 本の弦の共通死角は
  λ=1.000 m の 1 点だと思っていたが `λ = gcd(L_A/2, L_B/2)/k` の**櫛**で、仕込んだ
  λ=0.100 m が残ったのは k=10 の歯だった。相対間隔が λ そのものなので短波長ほど詰まり、
  波状摩耗帯(0.03–0.30 m)だけで 30 本ある。**弦を増やして埋める作戦は長波長では
  効くが短波長では原理的に間に合わない**。
- **`poc_web_roll_periodicity`**(wing_industrial)—— ロール to ロールの周期欠陥。
  詳細は 45.3。
- **`poc_datacenter_thermal_field`**(wing_astroenv)—— 疎な温度センサからの 3-D 熱場。
  詳細は 45.4。

### 45.3 ★「0 % を保つ最短の L」は、床ではなく試行数の産物だった

`poc_web_roll_periodicity` は記録長 L を短くして「隣のロールと取り違える崖」を探す。
最初の実装は崖を「**隣へ落ちる割合が 0 % でなくなる L**」で数えており、24 試行では
14000 mm を返して予測 `C²/ΔC = 14137 mm` と 0.99 で一致した —— きれいに見えた。

**試行を 120 に増やすと、いちばん長い 20000 mm でも 2 % 残り、0 % はどこにも無くなった。**
つまり 0 % は床ではなく小標本の産物で、崖の位置は「何試行回したか」で決まっていた。
床(2 %)を先に測り、その 3 倍と 10 % の大きいほうで数え直すと 14000 mm。結論は
変わらなかったが、**変わらなかったことを確かめるまでは、結論ではなく偶然だった**。

同じ形が 2 か所にあった:

- 「最長 2 点の特定成功率は 100 %」という assert —— 120 試行では 97 / 98 %。
  分母が 24 だから 100 % に見えていただけ。95 % 床へ直した。
- 「取り違え先」の説明が `list(bad)[0]`(dict の並び順)で決まっていた。24 試行では
  たまたま正しい答え(冷却ロール、3:2 の整数比)を返し、120 試行では別のロールを
  指した。最頻値を採り、**比が整数比かどうかも実測から判定する**よう直した
  (整数比でなければ「単に周長が近い」と書き分ける)。

[[feedback_gates_go_stale_not_missing]] の親戚で、こちらは**閾値が古い**のではなく
**分母が小さい**。0 % / 100 % という数字が出たら、まず分母を見る。

### 45.4 ★閉形式は当たり、「現場で測れる量」が外れた

`poc_datacenter_thermal_field` の崖は幾何だけで書ける: 間隔 d の 3-D 格子でピークから
いちばん遠い点はセル中心の `d√3/2` なので、σ のガウスは `exp(-3d²/8σ²)` 倍に落ちる。
**幾何だけを取り出した実測との差は 1.2e-15** —— 完全一致。

ところが現場で測れるのは「復元した場のピーク」であって「そのラックの寄与」ではない。
背景の復元誤差が同じ場所に載るので、素朴な実測は予測を最大 **+0.2598 超過**し、
**崖は実際より浅く見える**。σ=0.22 m のラックは d=1.20 m で幾何の回復 0.000014
(消滅)なのに、素朴には 0.1609 残って見える —— 残っているのは背景の誤差。

同じ PoC が予測をもう 2 つ外した:

- 「崖の位置は補間法で動かない」は言い過ぎ。**動かないのは指数**(log 回復 vs d² の
  傾きは 3 手法とも予測の 3.05 % 以内)、**動くのは係数**。薄板スプラインは内挿なのに
  節点の値を超えて 1.372 倍持ち上がり、半減間隔を 0.4777 → 0.6015 m(26 %)ずらす。
- 「持ち上がる手法は偽の峰も同じだけ立てる」も外れ。床は最近傍 0.975 °C(雑音の
  6.5 倍)に対し線形 0.132 / RBF 0.164 で、**持ち上がる側のほうが低い** ——
  最近傍の床は雑音ではなく**滑らかな背景を階段で近似した段差**だった。

### 45.5 記録のみ —— 次に埋める道具の穴

2 本の PoC が独立に同じ形の穴を突いた。**散らばった点から量を作る口が無い**:

1. 散らばった 3-D 点(センサ網・地質・気象)から場を作る補間 op が無い。
   公開されているのは 1-D の `interp_linear` / `interp_cubic` だけで、
   `griddata` / RBF / クリギング / IDW のいずれも無い(公開名 1,112 を全部引いて確認)。
2. 点列(イベント位置)から直接スペクトルを取る口が無い。`spectrum` も `cepstrum` も
   等間隔の信号を要求するので、欠陥地図・パーティクルカウンタ・打痕は自分で
   ヒストグラムに落とすしかない(Lomb–Scargle か binned periodogram)。
3. 1-D の山をサブビンで読む口が無い。`find_peaks` は整数の添字だけ。
   `refine_peak_newton` は**実在するが torch 必須**(`match3d.py`)なので、
   torch 無しの CI では使えない。

### 45.6 ★穴を記録するだけでなく、その日のうちに埋めた —— そして埋めると次の穴が鳴った

45.5 に「次に埋める道具の穴」として 3 件書いた直後に、3 件とも足した。

| 追加 op | 何を解く | 使ってみて分かったこと |
|---|---|---|
| `fs.interp_scattered`(mathops) | 散在 N-D 点 → 任意の問い合わせ点(nearest / linear / rbf) | **凸包の外に出た割合を返り値に入れた**。PoC が測った 71.2 % は黙って `NaN` か別手法に化ける量なので、ログではなく戻り値に居るべきだった |
| `fs.point_spectrum`(dsp) | 点列(事象位置)→ 周期図 | 最初 `scipy.signal.lombscargle` で書いたが、**点過程には誤り**(重みが定数だと平均除去でゼロになる)。点過程の Bartlett 周期図に差し替えた |
| `fs.peak_subbin`(dsp) | 1-D の山を副ビンで読む | `gauss` モードは Gauss 峰に**厳密**、`parabola` は偏る(幅 6.0 / 3.0 / 1.7 / 1.0 で誤差 0.0012 / 0.0047 / 0.0147 / 0.0434)。頂点は**丸めずに返す** —— ±0.5 を超えたら「そこは極大でない」という情報 |

**足したら、門が 4 つ鳴った。**どれも「登録した」と「使える」の差を突いていた:

1. `point_spectrum` の入力型 `positions` を**誰も産まない** → 連鎖ファザーで永久に
   到達不能。種を足した。★種は**一様乱数だけにしない** —— 周期成分が無いと
   「周期を見つける op」の意味のある挙動を一度も踏まないので、周期 17.0 の列に
   12 個の無関係な事象を混ぜた構造データにした。
2. `interp_scattered` に型契約テストの引数が無い → 足したら **1-D で落ちた**。
   docstring は「1-D は (n,1) として受ける」と書いているのに、`Delaunay` も
   `LinearNDInterpolator` も `NearestNDInterpolator` も 2-D 以上しか受けない。
   **書いた契約を試験が踏んで初めて分かった**ので、1-D 専用経路を 3 か所足した
   (1-D の凸包は区間なので、むしろ厳密で速い)。
3. `ops1d` が `opassist._LEDGERS` に無い → docs には出るのに `op_run` /
   `op_assist` / `op_find` から引けない。足した。
4. **`docs/AI_RAG_GUIDE.md` のノート枚数が古い**(1,866 → 1,906)。

### 45.7 ★★ops1d の 39 op は、登録済みなのにノートを 1 枚も持っていなかった

`dsp`(16)と `funct1d`(23)は `ops1d` に登録され `OP_CATALOG` にも出るのに、
`tools/opdocs.py` の `LEDGER_DIMS` に無かったため **`docs/ops` にノートが 1 枚も
無かった** —— つまり「op ごとの型契約・罠・関連 op」を持つ RAG コーパスから
39 op が丸ごと欠けていた。`poc_web_roll_periodicity` が dsp に 2 本足そうとして
気づいた。1 次元(`oned`)を足して 39 枚のノートが出るようになり、日本語要約 40 本を
書いた(原文が英語の op には ja のヘルプが要る、という既存の門が鳴ったため)。

「登録済みを数える門は未登録に盲目」([[feedback_registered_only_gates_miss_unregistered]])
の同型で、こちらは**登録の層が 3 つあり(レジストリ / ノート / opassist)、
3 つとも別々に登録が要る**という形だった。

### 45.8 ★★名前の衝突より、取り違えたときの挙動のほうが重い

`ops1d` を台帳へ繋いだ結果、台帳と 2-D レジストリの同名が `fill_holes` の 1 個から
**`fill_holes` / `lowpass` / `highpass` の 3 個**に増えた。衝突自体は前からあった
(`fs.lowpass` は以前から dsp の 1-D バターワース、`fs.op.lowpass` は 2-D 画像の
周波数フィルタ)。台帳に出したことで門が初めてそれを見せた。

数を数え直すだけで済ませず、**取り違えたときに何が起きるか**を測ったら、非対称だった:

* `fs.ledger.lowpass`(1-D)に 2-D 画像 → **ValueError**(正しく鳴る)。
* `fs.op.lowpass`(2-D)に 1-D 信号 → **鳴らない**。警告 1 本を出して、
  ★素通しですらなく **画像の契約 [0,1] へ切り詰めて返す** —— 最小値が
  -1.0 から 0.0 になり、`max|差| = 1.0`。**負の半分が消えた信号は
  「フィルタした信号」に見える**。

門はこの非対称を数字ごと固定した(方針が変わったら鳴る)。
[[feedback_failsoft_hides_permanently_dead_ops]] の親戚で、こちらは
「死んだ op を隠す」ではなく「**別の型の入力を、もっともらしい別物に変えて返す**」。

## §46 印刷の版ずれ —— 「賛成率 1.00」は正しさではない(2026-09-08)

`poc_print_registration`(展示 109)。CMYK 4 版に慣行のスクリーン角と既知のずれを
仕込み、刷り上がりから版ずれを測る。中心の主張は幾何で、**網点は格子なので相関で
出るのは d ではなく d mod Λ_θ** —— 軸方向 |d| ≤ p/2 = 4.51 px、対角 p/√2 = 6.38 px。
4 版 × 37 点 = 148 点のうち 144 点で予測と実測の差が 0.1096 px 以内、残り 4 点は
基本セルの境界のタイ(セル余裕 ≤ 0.165 px)。格子で簡約すれば全点が合う ——
**推定器は間違えておらず、格子で等価な答えのどれかを返している**。

効き方が具体的: 真値 9.64 px は公差 2.0 px の 4.8 倍なのに、スクリーン角の違いだけで
版ごとに 1.09〜3.32 px に見え、**4 版中 2 版が「合格」に見える**。

### 46.1 ★★`frame_align` は「確信度 1.00」で 80 px 外していた —— 直した

網点を星と見なして `fs.frame_align` に食わせると、`inlier_ratio` **1.00** /
`rms_px` 0.645 を返しながら真値 (0.00, +1.30) に対して **80.85 px** 外す。
しかもその答えは網点格子のベクトルですらないので、格子の不定性とは**別種の失敗**
(星の対応付けが偶然そろっただけ)。

**独立に最小再現した**: 256x256 の 133 lpi 相当・15 度の網点を (0.00, +1.30) px
ずらした対で、推定 (+54.24, +30.12) px・`inlier_ratio` 1.00・`rms_px` 0.78。
星野(128x128、40 星、真値 (+0.59, -0.54))でも `inlier_ratio` は **同じ 1.00** で
推定は正しい。**賛成率では 2 つを区別できない** —— 「同じ答えに賛成した対応の割合」は
「答えが正しい確率」ではなく、繰り返す構造の上では前者が 1.00 になる。

直した内容:

* docstring に「**繰り返し構造には使えない**」を、上の実測値つきで書いた。
* 投票の**2 番手の山 / 1 番手**を `vote_margin` として返すようにした
  (`_vote_translation` の 3 つ目の戻り値)。0 なら単峰、1 に近いほど
  「同じくらいもっともらしい答えが他にもある」。実測は **網点 0.857〜1.000 /
  星野 0.143**。`tests/test_astrostack.py` が両者を並べて固定する。

[[feedback_failsoft_hides_permanently_dead_ops]] の別の面で、こちらは
**自信の数字が、その自信が意味を持たない場面でも 1.00 を返す**という形。

### 46.2 ★予測していなかった 2 件

* **ゼロ点(インク重心)は折り返さない代わりに縮尺が狂う**。応答の傾きは閉形式
  `k = 1 - β`(β = 下地だけのインク量 ÷ 実際のインク量)で予測 0.3983、実測 0.3711。
  ★**直線からの外れ 0.9864 px** はまったく想定していなかった —— 網点ピッチ周期の
  さざ波で、**窓の縁で網点の列が出入りする**ため。テーパ窓の対照群で 0.0048 px に
  落ちて原因が確定した。
* **合成器そのものが罠だった**。1200 dpi / 150 lpi はピッチがちょうど 8.00 px で
  **全網点の標本位相が揃う**ため、0.5 px ずらすたびに重心が 1.4 px 跳ねた。
  133 lpi(p = 9.02)にして解消。**整数比を避けるのが本質**で、スーパーサンプリングでは
  直らない。[[feedback_random_test_data_hides_structural_defects]] の逆向きの例 ——
  こちらは**きれいな数字**(整数比)が構造的な欠陥を作っていた。

### 46.3 ★物差しを 2 つ置くと勝者が入れ替わり、組み合わせると両方取れる

| 手法 | RMS 誤差 [px] | 判定一致率 |
|---|---|---|
| 相関 AM(素) | **0.0071**(1 位) | 67.6 %(最下位) |
| 相関 AM(低域通過) | 0.6680(94 倍悪い) | 89.2 % |
| 二段(粗で代表元 + 密で詰める) | **0.0071** | **94.6 %** |
| 相関 FM(対照群) | 0.0026 | 100.0 % |

二段の成立条件「**粗の誤差 < 基本セルの半径 4.511 px**」も実測で確かめた ——
**二段が壊れた 2 点は、すべて粗の誤差がその半径を超えた点**だった。絵柄をベタに
寄せる(山を 0.45 → 0.06)と 6 点中 3 点で丸ごと 1 格子跳ぶ ——
**同じ手法が、刷る絵柄しだいで壊れたり壊れなかったりする**。

### 46.4 記録のみ —— 印刷の語彙が 4 層のどこにも無い

`halftone` / `screen` / `rosette` / `misregist` / `lpi` / `moire` / `trapping` /
`lattice` の 8 語すべてで、`fs.<名>` / `fs.op.<名>` / `fs.ledger.<名>` /
`fs.op_find(語)` の **4 層すべてに 0 件**。網点の合成、スクリーン角・線数の推定、
版ずれの測定はどれも産業用画像処理の定番。ほかに、2 枚の画像の並進を 1 個返す口、
2-D 画像の相関マップ、2-D 画像の重み付き重心が公開層に無い(いずれも
「ゼロ点に使う道具ほど公開層に要る」形)。

★この族を足すなら、**docstring に 3 節の不定性を測った数字で書くこと**。
「相関で版ずれが測れます」とだけ書いた op を出すと、利用者は 8 節の見落とし
(不合格の版を「合格」と言った回)を静かに踏む。

## §47 在庫量と「見えない底面」—— そして `dem_viewshed` の自己遮蔽(2026-09-08)

`poc_stockpile_volume`(展示 110)。山と地面を別々の式で置き、堆積物の在庫量を
3-D スキャンから出す。**在庫量という 1 個の数字は、誰も測っていない面(山の下の
地面)の仮定で決まる**。

### 47.1 ★★`dem_viewshed` は目線より高いセルを軒並み「見えない」と返していた

平地に置いた円錐の**頂点**が、60 m 先・目線 2.0 m の開けた平地から「見えない」
(可視 0.0)。目線より高い 1541 セルの可視は **0 個**、底面の遮蔽率 0.8863
(閉形式 0.5710)。**独立に最小再現した**: 平地に高さ 10 m の柱を 1 本立てると
可視 0.0、目線より低い 1 m の柱は可視 1.0。凸な立体の最高点は外から必ず見えるので、
これは幾何として誤り。

原因は実装の刻み。視線を `ceil(hypot(H,W))` 等分した最後の標本が `np.rint` で
**目標セル自身**に丸まり、`(z-eye)/(dist*t) > (z-eye)/dist`(t<1)は z > eye なら
必ず真になる。**標本が目標セルに乗った回は数えない**よう直した(`demops.py`)。
直後の実測: 頂点 1.0、遮蔽率 0.5900(PoC 自前 0.5539 / 閉形式 0.5710 ——
**閉形式を挟んで両側**に分かれる。別々の離散化なので一致は求めない)。

### 47.2 ★★門がこれを通した理由 —— 壁の「向こう側」は見ていたが「壁そのもの」は見ていなかった

可視領域の試験は 3 本あった: 平地は全部見える / 壁の**向こう側**は見えない /
観測点は常に見える。**どれも目線より高いセルの可視を一度も見ていない** ——
平地には目線より高いものが無く、壁の試験は「向こう側が 0 か」だけを見ていた。
壁**そのもの**が見えるかを確かめる 1 行があれば、その日に鳴っていた。

[[feedback_gate_must_stand_where_the_accident_happens]] そのもので、
`tests/test_demops.py` に 3 本足した(開けた平地の高い柱 / 壁そのものの可視 /
壁を越えられる高さでだけ見えること)。

### 47.3 ★予測を外した —— 「凹だから過小」は両端が山の上にあるときの話

遮蔽部を線形補間で埋めると体積は**過小**に出ると予測していた(円錐面は凹なので
弦は下を通る)。実測は **+17.20 % の過大**。裏側が法尻まで丸ごと見えないため、
三角形の相手が「山の上」ではなく**山の外の地面**になり、稜線から 30 m 先へ張った
弦の勾配 0.37 m/m が真の斜面 0.75 m/m の**上**を通る。

### 47.4 ★★相殺の罠 —— 汚染された物差しで汚染された対象を測ると誤差が消える

同じ 1 か所スキャンで、**真の地面**を底面にすると +17.20 %、**現場の手**(外周
平均の水平底面)だと **+0.51 %**。良くなったのではなく、外周の高さも同じ補間で
**+0.728 m** 持ち上がって引き算で消えているだけ。証拠: 外周のうち**実際に見えた
点だけ**で底面を決めると **+12.05 %** に戻る。

同じ形が法尻の土手でも出た。**外れ値に強い RANSAC のほうが数字は悪い**
(+2.48 % 対 TLS +0.61 %)が、RANSAC は土手を正しく捨てて「土手なし」の答え
+1.91 % へ戻っただけで、TLS が良く見えるのは土手の持ち上げがうねりの偏りを
たまたま打ち消したから。**「数字が良い」を採用の根拠にすると、この 2 つを
毎回取り違える**。

### 47.5 誤差は足し算にならない

底面の仮定だけ(全周・うねり)+1.79 %、遮蔽だけ(1 か所・平ら・真の底面)
+23.42 %。両方入れると **+0.51 %** で、足し算(-0.70 %)にならない ——
遮蔽の補間が底面を決める外周まで動かすので 2 つは絡む。
**誤差収支を「底面 x % + 遮蔽 y %」と足す報告は、この時点で嘘になる**。

### 47.6 記録のみ —— 次に埋める穴(4 層すべて引いて確認)

* **表面 2 枚のあいだの体積(cut & fill)を出す op が無い**。`mesh_volume`
  (閉メッシュ)と `vol_rle_volume`(voxel 数)はあるが、「z_top と z_base を
  領域 S で積分して m^3 を返す」入口が 4 層のどこにもない。測量・鉱山・建設で
  いちばん出番の多い量。
* 法尻(トゥライン)/ ブレークライン抽出が無い(`toe` / `breakline` は 0 件)。
* 複数観測点の可視域の**和**と走査計画が無い(`dem_viewshed` は 1 点のみ)。
* 体積の不確かさ伝播が無い —— 底面の仮定 ±Δh・点密度・補間の外挿率から
  在庫量の区間を返せると、47.5 の「足し算にならない」を道具側で言える。

## §48 名前は在るのに引けない —— 空白の 3 分野と、探し方そのものの穴(2026-09-08)

展示 111〜113(`poc_multibeam_bathymetry` / `poc_search_sweep_width` /
`poc_livestock_body_volume`)。いずれも展示館に 1 本も無かった分野
(海洋測深・捜索救難・畜産)。**3 本とも「道具が無い」ではなく「在るのに
引けない」という同じ形の穴を掘り当てた**。

### 48.1 ★★`op_find` は和文の複数語クエリに構造的に盲目だった

`poc_search_sweep_width` が踏んだ。点状目標の座標を返す 2-D op は
`star_detect` だけなのに、``op_find("小さい目標 検出")`` /
``("スポット 検出")`` / ``("漂流 捜索")`` はいずれも **0 件**。
名前が天文に閉じているせいだと思って docstring に説明語を足したが、
**それでも 0 件のまま**だった。掛けて見ると原因は 2 つとも探索側にあった:

1. 語の切り出しが ``_WORD_RE = re.compile(r"[a-z0-9]+")`` の **ASCII 限定**。
   ``_WORD_RE.findall("点 検出") == []`` なので語幹の段は空回りし、部分一致は
   **空白ごと含む文字列**を探すので当たらない。→ **和文の複数語クエリは
   必ず 0 件**。
2. 採点に使う ``doc`` は台帳の **1 行目だけ**(``star_detect`` で 30 文字)。
   本文にどれだけ説明語を書いても検索には届かない。

docstring の大半が日本語で、**6 言語を配っている製品**でこれが立っていた。
[[feedback_registered_only_gates_miss_unregistered]] と同じ型 —— 記録は在るのに、
それを読む側が現実に追いついていない。

直し(`opassist.py`): CJK の連なりを語として取り、丸ごと当たらなければ
**文字 2-gram で按分**する段を足した。ただし **既存の点が 0 のときだけ**参照する
追加の段なので、これまでの並び順は変わらない(語幹の段と同じ方針)。採点対象は
docstring 全文へ広げ、**要約(名前 + 1 行 doc)に当たった分を重く**した
(深い本文の一致だけだと同点が並び、順位が名前のアルファベット順になる)。

実測: 「小さい目標 検出」1 位 / 「スポット 検出」2 位 / 「漂流 捜索」1 位。
★**「点 検出」は今も出ない** —— 「点」1 文字は `cv_canny` や `frei_amp` の
説明にも必ず出るので同点に押し出される。**和文の段が効くのは 2 文字以上の語が
効く場合だけ**、という限界は PoC の assert に書いて隠していない。

### 48.2 ★★同じ名前で規約が逆 —— 掴み間違えると例外なく空の hull

`poc_livestock_body_volume` が踏んだ。空間彫刻(`carve` /
`synthesize_silhouette`)が要求する姿勢は OpenCV 規約(``X_cam = R X + t``、
**+Z 前方**)で、それを作る `visualhull.look_at` は
``fs.`` / ``fs.op.`` / ``fs.ledger.`` の**どこからも引けず**、
``op_find("look")`` も **0 件**だった。一方、公開層で `look_at` の名を持つのは
`render3d` の gluLookAt 版(4x4・**−Z 前方**)。その ``M[:3,:3], M[:3,3]`` を
渡すと全点がカメラ後方に落ち、**例外を出さずに空のシルエット**→空の hull が返る。
**カメラ 0 台は `ValueError` で fail-closed なのに、規約違いは無言**だった。

独立に再現した(立方体の点群 8000 点、正しい姿勢で前景 2240 px、
gluLookAt 由来で 0 px)。直し: ① `carve_look_at` を台帳(`ops3d` /
space_carving、型 `pose`)に載せて `fs.ledger` と `op_find("look")` から
引けるようにした —— **名前は譲らない**(同名にすると今度は逆向きに静かに壊れる)。
② 点が 1 つ残らず後方なら `RuntimeWarning`。③ `render3d.look_at` の docstring に
「彫刻には渡すな」を書いた。④ `tests/test_visualhull.py` に 2 本追加し、
既存の「後方の点を棄却する」試験も `pytest.warns` で固定して警告をノイズにしない。

[[feedback_failsoft_hides_permanently_dead_ops]] そのもの。

### 48.3 ★片道の参照 —— 名前の見つけやすい側から辿ると遠回りさせられる

`poc_multibeam_bathymetry` の検証中に出た。ベクトル版 `refract`
(`match3d`)の docstring は「(N,3) バッチも通るが 1 本でも TIR なら全体が
`None`。**バッチで使うなら 1 本ずつ回すこと**」とだけ書いていて、
**光線ごとに TIR を判定して `(方向, マスク)` を返す `refract_rays` が既にある**
ことに触れていなかった(`refract_rays` 側からの参照は在った)。
参照が片道だと、**名前の見つけやすい側から入った人だけが遠回りする**。
両方の docstring に相互参照を書き、音響で使うときの ``eta = 1/c`` も添えた。

### 48.4 展示 111 —— 多ビーム測深: 閉形式は当たり、機械を通すと崖は手前に来る

崖(IHO S-44 Order 1a を割る角度)を**測る前に 2 通り印字**した。厳密な
円弧の閉形式 **48.68 度**は当たり(エコー検出を止めた経路の実測と差
2.0e-11 m)、ラフな展開式 ``Δz ≈ (gD²/2c₀)tan²θ`` は **0.53 度手前に外した**
(45 度まで 3.0 % 以内、70 度で 19.4 % 過大)。

★**予測を外した**: 「エコー検出は無視できる床」と見込んでいたが、**全経路の
崖は 47.95 度**で 0.73 度早い。70 度でビームが照らす帯のエコーが 21396 µs
(直下の 171 倍)に伸びて非対称になり、振幅検出の頂点が手前へ寄る(−0.725 m)。
**実機が外側で位相検出に切り替える理由**が数字で出た。

★**教科書式が実測の 34 %**: 70 度のフットプリントは cos² 式 8.21 m 対 実測
24.14 m。電子的に振った配列はビーム幅が 1/cosθ で広がるので**正しい指数は 3**
(cos³ 式は −0.6 %)。

★**真値なしでできる唯一の検査**(隣接測線の重なり)にも罠がある: 端では
2.697 m 食い違うのに**帯の真ん中では 0.0000 m** —— 両測線とも同じ振れ角で
誤差が同じだけ乗って消える。**端まで見ないと見つからない**。

### 48.5 展示 112 —— 走査幅: 形は消え面積だけが残る。ただし平行捜索では形が効く

走査幅の定義(W = ∫p dx)そのものを実証した: 形の違う 4 本の曲線を同じ面積
256.2 m に揃えると検出割合は 4 つとも予測 0.2562 の 0.8σ 以内。
**形は消え、面積だけが残る**。

★**予測を 4 つ外した**。(1) 実測の p では平行捜索が C=1 で **0.8464** と
1.000 に届かない(`min(1,C)` は定値域則 = 矩形に依存する)。(2)「平らな曲線の
ほうが矩形に近く強い」は**逆**(0.7705 対 0.8464)—— 矩形に近いとは『平ら』では
なく『W の内側に立ち裾を引かない』こと。同じ 2 本が**ランダム捜索では一致**する
(面積しか見ない)。(3)「端は解像度が落ちる」—— ナディア向き中心投影では
**地上分解能は端まで一定**(相対ばらつき 0.0e+00)。(4)「背景を引けば良くなる」——
全体の中央値と σ で割るのは**アフィン変換で順位が変わらない**。

★**見張り役**: 誤検出は端ではなく**直下に集中**する(0–32 m 帯 113 件 /
最外帯 0 件)—— 目標も白波も同じ cos⁴ で暗くなるので、**いちばんよく見える所が
いちばん吠える**。閾値だけで W は 406 → 170 m 動くので、**走査幅は誤検出率と
対でしか語れない**。

★素材側でも 1 件: 点源を画素中心 1 点で標本すると**総フラックスの誤差 4.6e-07
なのにピークが σ=0.9 px で 10.6 % 過大**になり、σ が横距離で変わるので横距離
曲線そのものが傾く。**総和が合っていることは、山の高さが合っている証拠にならない**。

### 48.6 展示 113 —— 視体積交差: 偶数台は半分が無駄で、13 台が 16 台に勝つ

★★**閉形式が現場の目安を訂正した**。「K 台なら K 角形」は正しくない ——
平行投影ではカメラ 1 台が視線に**直交する接線 2 本**を与え、**向かい合う 2 台は
同じ 2 本**しか与えない。接線の本数は偶数 K なら K 本、**奇数 K なら 2K 本**。
独立に検算した面積比(単位円): K=3 と K=6 はともに接線 6 本で 1.10266 と**同一**、
K=4 は 4/π = 1.27324、**K=13(1.00490)が K=16(1.01305)に勝つ**。
「体重 2 % 以内」なら奇数 13 台 / 偶数 24 台で、**偶数台で組む現場は 11 台
足りない見積り**を持つ。

★★展示の中心は**消える誤差と消えない誤差を分けて数える**こと: 脚の間の幽霊は
K=4 → 48 で 7.13 % → 1.37 %(5.2 倍)と素直に減るのに、**背中のくぼみは
カメラ 12 倍で 3.8 ポイントしか減らない**(56.4 % → 52.6 %)。分かれ目は
「その凹みが**輪郭に出るか**」。

★**予想を外した**: 「巻尺は体に巻くから凸包を測っている」→ 3-D 凸包が胸囲に
強いはず、と踏んだが実測 **+55.2 %** で最悪の部類。体全体の凸包は腹の下を
埋めるので縦断面が地面まで伸びる。**「断面の凸包」と「凸包の断面」は別物**。

★カメラ配置の対照(上半球ランダム 8 台 対 等間隔 8 台、120 試行)は平均では
互角なのに**最悪値は 2.4 倍**(+30.20 %)。**危ないのは平均ではなく裾**。

### 48.7 記録のみ —— 次に埋める穴(いずれも 4 層すべて引いて確認済み)

* 音響測深: `svp_ray_trace` / `svp_harmonic_mean` / `iho_s44_tvu` /
  `beamform_snapshot`(レンジ-ドップラーを経由しない素子スナップショット入力)/
  `crossline_discrepancy`。`sonar` / `swath` / `bathym` / `tvu` は op_find 0 件。
  ★`sound_speed` / `footprint` / `crossline` は**件数だけ返るが中身は無関係**
  (`flow_speed` / `sk_local_maxima` / `piv_cross_correlate`)—— 件数を見て
  「在る」と読むと外す。
* 捜索: `draw_point_sources`(位置指定の点源描画。`astrostack` の erf 厳密積分は
  非公開で、公開の `synth_starfield` は**位置が内部乱数**)/ `ncc_map`(相関マップ。
  `ncc_locate` は最良 1 個しか返さない)/ `peak_detect`(`star_detect` の分野中立な別名)。
* 視体積交差: `visual_hull_ring(K, dist, f)` のリグ生成 / `silhouette_erode` /
  `voxel_volume(occ, spacing)`(`vol_rle_volume` は voxel 個数まで)/
  2-D の `convex_perimeter`(実寸の凸包周囲長。`contlength` は 2(H+W) 正規化の無次元値)。

