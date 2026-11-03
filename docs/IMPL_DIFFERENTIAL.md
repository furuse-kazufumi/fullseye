# 同じ処理の別実装の突き合わせ(differential testing)

> 生成物 —— 手で直さない。生成器 `tools/impl_differential.py`(表は `docs/impl_differential.json` と `tools/impl_differential_table.py` から)。測り直しは `py -3.11 tools/impl_differential.py --measure`、門は `tests/test_impl_differential.py`。

同じ処理が実装ごとに別の名前で並んでいる組(`canny` / `cv_canny` / `sk_canny` / `xkor_canny` など)を、**同じ入力・同じつまみ (a, b)** で走らせて出力を比べた表。golden(過去の自分)ではなく**実装どうし**を比べる。命名整理 第 2 段(1 つの名前 + `impl` 引数)でまとめてよいかの前提になる。

## 数え方

`docs/OP_INDEX.json` の op 名を `<接頭辞>_<語幹>` に割り、**語幹が同じで接頭辞だけ違う**名前を 1 組にした(接頭辞の無い素の名前も組に入る)。接頭辞は実装・由来を表すもの 32 種だけ(`vol_` `mesh_` `piv_` のような分野の接頭辞は数えない。一覧は末尾)。

| | 件数 |
|---|---:|
| 語幹が同じ組(全部) | 192 |
| うち `tb_X` と台帳の `X` だけの組(同じ関数の別の入口、つまみの写し方の標本だけ見る) | 156 |
| うち実装どうしの組 | 36 |
| 実装どうしの対(3 実装の組は 3 対、4 実装は 6 対) | 55 |

依頼時の目安は 172 組だったが、その数え方は再現できていない(ここの数え方では 192 = 156 + 36)。`tb_` の 156 組のうち 150 組は `naming_phase2/rename_plan.json` の B と同じで、残り 4 組は台帳の `X` と同名の別の関数がレジストリにある名前の衝突(下の「`tb_` の橋渡しの標本」)。

## 比べ方

- 入力: 2-D は `fragments48`・`noisy48`・`smooth_random48`・`structured48`・`structured64`(0〜1)。region は `blobs48`・`structured_region48`、contour はその輪郭(`sk_find_contours`)。
- つまみ (a, b): (0.5, 0.5)・(0.25, 0.75)・(0.75, 0.25)。
- 画像: 端 8 画素を除いた内部の `max|A−B|` ÷ 両者の内部の振れ幅(ptp)の大きい方。**端を含む差**も別の欄に出す。
- 二値(region)と輪郭: 内部の食い違い画素 ÷ 和集合(= 1 − IoU)。疎なエッジでは一致率が背景で水増しされるので使わない。
- スカラー・ベクトル: `|a−b| / max(|a|, |b|)`。
- 値域: 契約の 0〜1 で分類し、**契約外の 0〜255**(float のまま渡す)を別の欄に出す(実装が値域を仮定しているかの手掛かり)。
- 分類: 一致 < 0.005 ≤ 近い < 0.05 ≤ 違う。片方が例外で落ちたら「片方が落ちる」、optional 依存が無ければ「未検証」、入出力の型が違えば「比較不能」。

## 結果の件数

| 分類 | 対の数 |
|---|---:|
| 一致 | 8 |
| 近い | 3 |
| 違う | 34 |
| 片方が落ちる | 0 |
| 未検証 | 0 |
| 比較不能 | 10 |

| 段 2 での扱い(組ごと) | 組の数 |
|---|---:|
| まとめてよい | 4 |
| 一部まとめてよい | 2 |
| つまみを揃えればまとめてよい | 2 |
| 近似としてなら | 1 |
| まとめない | 27 |

**1 つの名前 + `impl` 引数にまとめてよい組(前の 3 種)= 8 組**: `bilateral`、`dog`、`gaussian`、`median`、`meijering`、`skeleton`、`smallest_rectangle1`、`unsharp`。

## 組ごとの表

「内部」「端込み」「0〜255」は 0〜1 の全入力・全つまみでの最悪値。「揃えると」はつまみを揃えた点(下の節)の値。

| 語幹 | 対 | 分類 | 内部 | 端込み | 0〜255 | 揃えると | 原因 | 段 2 |
|---|---|---|---:|---:|---:|---:|---|---|
| `area_center` | `area_center` / `xg_area_center` | 比較不能 | — | — | — | — | 入出力の型が違う: region → match(面積の画素数・重心の行・列)と contour → feature(全輪郭の多角形の面積の和、靴ひも公式)。HALCON でも area_center と area_center_xld は別 op。xg_ の対になる XLD 版 area_center_xld も「最大の輪郭 1 本」と「全輪郭の和」で定義が違う | **まとめない** —— region 版と contour 版(HALCON でも別 op) |
| `bilateral` | `bilateral` / `cv_bilateral` | 違う | 0.055 | 0.05 | 0.00052 | — | 窓・カーネルの形: OpenCV の bilateralFilter(d = 5)は**半径 2 の円**の窓(21 画素)、core は 5×5 の正方形(25 画素)。core の式を円の窓にすると cv_ と内部 1.5e-7 で一致した(確かめた)。つまみの写し方は同じ | **一部まとめてよい** —— bilateral と xkor_bilateral は内部 3e-7 で一致。cv_bilateral は円の窓なので impl='cv' は「近い別実装」と書く |
|  | `bilateral` / `xkor_bilateral` | 一致 | 2.7e-07 | 0.071 | 1.26 | — | 独立な実装どうしの一致 |  |
|  | `cv_bilateral` / `xkor_bilateral` | 違う | 0.055 | 0.054 | 1.26 | — | 窓・カーネルの形: xkor_ は core と同じ 5×5 の正方形、cv_ は半径 2 の円の窓。つまみの写し方は同じ |  |
| `canny` | `canny` / `cv_canny` | 違う | 0.803 | — | 0.803 | — | 定義の違い: core の canny は**非極大抑制もヒステリシスも無い**簡易版(σ = 0.5+1.5a でぼかした Sobel 強度を正規化して 0.1+0.5b で二値化 → 太いエッジ)。cv_canny は 8 bit の本物の Canny で、a, b が勾配の下・上しきい値(50〜150 / 100〜250) | **まとめない** —— core の canny は非極大抑制の無い簡易版。本物の 3 実装もつまみの意味(σ かしきい値か)と尺度が違う |
|  | `canny` / `sk_canny` | 違う | 0.771 | — | 0.793 | — | 定義の違い: core は非極大抑制の無い簡易版。sk_canny は本物の Canny で、a が σ = 0.5+2a、しきい値は skimage の既定 |  |
|  | `canny` / `xkor_canny` | 違う | 0.78 | — | 1 | — | 定義の違い: core は非極大抑制の無い簡易版。xkor_canny は本物の Canny(5×5、σ = 1 固定)で、a, b が 0〜1 の勾配の下・上しきい値 |  |
|  | `cv_canny` / `sk_canny` | 違う | 0.937 | — | 0.898 | — | つまみの写し方: どちらも本物の Canny だが、a の意味が違う(cv_ はしきい値、sk_ は平滑化の σ)。cv_ は平滑化なしの Sobel 3×3・8 bit・L1 勾配、sk_ は L2 勾配・しきい値は既定 |  |
|  | `cv_canny` / `xkor_canny` | 違う | 0.509 | — | 1 | — | 定義の違い: a, b はどちらもしきい値だが尺度が違う(cv_ は 0〜255 の勾配で 50〜250、xkor_ は 0〜1 で 0.1〜0.7)。xkor_ は 5×5・σ = 1 の平滑化つき、cv_ は平滑化なし |  |
|  | `sk_canny` / `xkor_canny` | 違う | 0.941 | — | 1 | — | つまみの写し方: どちらも本物の Canny。sk_ は a が σ、しきい値は既定。xkor_ は σ = 1 固定、a, b がしきい値 |  |
| `clahe` | `clahe` / `cv_clahe` | 違う | 0.611 | 0.877 | 1 | — | つまみの写し方: core の clahe は a がタイル数 2+int(3a) 枚四方、b が clip limit(ビン平均の 256^b 倍)。cv_clahe はタイル 8×8 固定・a が clipLimit = 1+4a・入力を 8 bit に落とす | **まとめない** —— core の clahe はつまみの意味が違う。cv_clahe と xkor_clahe は同じ定義で 8 bit 量子化の差(最大 0.087) |
|  | `clahe` / `xkor_clahe` | 違う | 0.612 | 0.877 | ∞ | — | つまみの写し方: core はタイル数と clip limit を a, b で振る。xkor_clahe はタイル 8×8 固定、a が clip limit = 1+4a |  |
|  | `cv_clahe` / `xkor_clahe` | 違う | 0.087 | 0.086 | 1 | — | 量子化(8 bit): 定義もつまみも同じ(8×8、clip 1+4a)。差は cv_clahe が入力を 8 bit に量子化すること(タイルのヒストグラムと LUT の丸め)。48 px の画像は 1 タイル 6×6 画素で量子化が効き、最大 0.087 |  |
| `clip_contours` | `hx_clip_contours` / `xg_clip_contours` | 違う | 0.632 | — | — | — | 名前だけ同じ別の処理: hx_ は画像の内側の矩形(上下 a×0.4H、左右 b×0.4W の余白)の外の点を消す。xg_ は最長の輪郭の a 倍より短い輪郭を丸ごと捨てる(長さで選別) | **まとめない** —— 矩形で切る / 長さで選ぶ —— 別の処理 |
| `corner_harris` | `cv_corner_harris` / `sk_corner_harris` | 違う | 0.993 | 0.966 | 0.993 | — | 定義の違い: cv_ は blockSize 2 の箱の窓・Sobel 3・k = 0.04 で固定(a, b 未使用)。sk_ はガウシアンの窓 σ = 0.5+2a・k = 0.05。窓の形・k・微分の尺度が違う | **まとめない** —— 窓の形・k・微分の尺度が違い、cv_ はつまみが無い |
| `crop_contours` | `hx_crop_contours` / `xg_crop_contours` | 違う | 0.739 | — | — | — | 名前だけ同じ別の処理: どちらも中央の矩形の内側の点を残すが、窓が違う: hx_ は高さ (0.3+0.6a)H・幅 (0.3+0.6b)W、xg_ は高さ aH・幅 aW(b は未使用) | **まとめない** —— 窓の決め方が違う |
| `curvature_flow` | `curvature_flow` / `xsitk_curvature_flow` | 比較不能 | — | — | — | — | 入出力の型が違う: 台帳の curvature_flow はレベルセット φ(mask)を平均曲率流で動かして経過の表を返す。xsitk_curvature_flow は SimpleITK の CurvatureFlow で画像を平滑化する(image → image) | **まとめない** —— レベルセットの曲線短縮流と画像の平滑化 —— 別の処理 |
| `dog` | `dog` / `sk_dog` | 違う | 1 | 1 | 1 | 5.6e-16 ✓ | つまみの写し方: core は σ1 = 0.5+2a・σ2 = 1+4b、sk_dog は σ1 = 1 固定・σ2 = 1+3a。σ を揃えると(ALIGNED)内部は**差 0**(skimage の DoG も中で scipy の gaussian_filter を呼ぶ = 独立でない)。残る差は端の扱い(core は reflect、skimage は nearest)が画像全体の最大値で割る正規化を通して効く定数倍だけ | **つまみを揃えればまとめてよい** —— σ を揃えると定数倍(端の扱いが正規化に効く分)を除いて一致。impl 引数にするなら σ の写し方を 1 つにする |
|  | `dog` / `xkor_dog` | 違う | 1 | 1 | ∞ | 4.4e-06 ✓ | つまみの写し方: xkor_dog は σ1 = 1.0・σ2 = 1.6 固定(a, b 未使用)。core を a = 0.25・b = 0.15 にすると(ALIGNED)内部は定数倍を除いて 4e-6 で一致(独立: scipy と kornia)。定数倍は端の扱いが正規化に効く分 |  |
|  | `sk_dog` / `xkor_dog` | 違う | 0.513 | 0.513 | 1 | 4.4e-06 ✓ | つまみの写し方: sk_dog を a = 0.2(σ2 = 1.6)にすると xkor_dog と定数倍を除いて 4e-6 で一致(ALIGNED)。定数倍は端の扱い(nearest と reflect)が正規化に効く分 |  |
| `eccentricity` | `eccentricity` / `xg_eccentricity` | 比較不能 | — | — | — | — | 入出力の型が違う: region → match(HALCON の Anisometry / Bulkiness / StructureFactor、面積のモーメントから)とcontour → feature(輪郭点の共分散の固有値から sqrt(1 − λmin/λmax))。量も入力の型も違う | **まとめない** —— region 版と contour 版で量も違う |
| `elliptic_axis` | `elliptic_axis` / `xg_elliptic_axis` | 比較不能 | — | — | — | — | 入出力の型が違う: region → match(Ra, Rb, Phi)と contour → feature(輪郭点の共分散の固有値の比 sqrt(λmax/λmin)) | **まとめない** —— region 版と contour 版で量も違う |
| `felzenszwalb` | `sg_felzenszwalb` / `sk_felzenszwalb` | 違う | 1 | — | 1 | — | つまみの写し方: 同じ skimage.segmentation.felzenszwalb を別の引数で呼ぶ: sg_ は scale = 40+500a・sigma 0.5・min_size = 15+85b・境界 outer、sk_ は scale = 20+200a・sigma 0.8・min_size 20・境界 thick。sigma が固定で違うので、つまみを揃えても一致しない | **まとめない** —— 同じ skimage 関数を別の固定引数(sigma・min_size・境界の取り方)で呼ぶ |
| `full_domain` | `hx_full_domain` / `it_full_domain` | 比較不能 | — | — | — | — | 入出力の型が違う: hx_full_domain は全 1 の region(HALCON の定義域を全面に)、it_full_domain は画像をそのまま返す(image → image、numpy の配列は元から全面が定義域)。どちらも自明で、返す型だけが違う | **まとめない** —— region を返すか画像を返すか(どちらも自明) |
| `gabor` | `gabor` / `hx_gabor` | 違う | 0.717 | 0.567 | ∞ | — | 定義の違い: どちらも a が向き θ = πa、L1 で割る固定尺度。包絡と周波数が違う: core は σ = 2・窓 15×15・周波数 0.1+0.3b、hx_ は σ = 2.2・窓 9×9・0.08+0.35b | **まとめない** —— 包絡・周波数の範囲・つまみの役(向き / 周波数)が実装ごとに違う |
|  | `gabor` / `sk_gabor` | 違う | 0.999 | 0.999 | 1 | — | つまみの写し方: つまみの役が入れ替わっている: core は a が向き・b が周波数、sk_gabor は a が周波数 0.1+0.3a・向きは 0 固定。sk_ は帯域幅 1 から σ を決め、実部の絶対値を画像ごとの最大で割る |  |
|  | `hx_gabor` / `sk_gabor` | 違う | 0.999 | 1 | 1 | — | つまみの写し方: hx_ は a が向き・b が周波数、sk_ は a が周波数・向き 0 固定。包絡・正規化も違う |  |
| `gaussian` | `cv_gaussian` / `gaussian` | 一致 | 7.3e-05 | 0.505 | 7.3e-05 | — | 独立な実装どうしの一致 | **まとめてよい** —— 3 実装が内部で一致(xkor_gaussian は 2026-11-03 に直して一致)。端は gaussian の b で選べる分だけ違う |
|  | `cv_gaussian` / `xkor_gaussian` | 一致 | 7.3e-05 | 0.095 | 1.72 | — | 独立な実装どうしの一致 |  |
|  | `gaussian` / `xkor_gaussian` | 一致 | 3.8e-07 | 0.527 | 1.72 | — | 独立な実装どうしの一致 |  |
| `guided_filter` | `dl_guided_filter` / `guided_filter` | 違う | 0.358 | 0.353 | 1.26 | — | 名前だけ同じ別の処理: dl_guided_filter は本物の self-guided filter(局所線形モデル、r = 1+int(4a)、eps = 0.001+0.05b)。guided_filter は docstring が自認するとおり**中身が bilateral_filter と同一**(cv2.bilateralFilter)の代役で、guided filter ではない | **まとめない** —— guided_filter の中身は bilateral。guided filter は dl_guided_filter だけ |
| `height_width_ratio` | `height_width_ratio` / `xg_height_width_ratio` | 比較不能 | — | — | — | — | 入出力の型が違う: region → feature(画素の外接矩形)と contour → feature(輪郭点の座標の範囲、画素数より 1 小さい)。入力の型が違うので同じ入力で比べられない | **まとめない** —— region 版と contour 版 |
| `hessian` | `sk_hessian` / `xkor_hessian` | 違う | 1 | 1 | 1 | — | 名前だけ同じ別の処理: skimage の filters.hessian は Frangi 系の**管状度**(σ = 1, 2, 3 の多重尺度、白い線で 0)。xkor_hessian は Sobel 5×5 の 2 階微分による **Hessian の行列式** \|Ixx Iyy − Ixy²\| | **まとめない** —— 管状度と行列式 —— 別の量 |
| `inpaint` | `xcv_inpaint` / `xsk_inpaint` | 違う | 0.747 | 0.747 | 2.35 | — | 定義の違い: 欠損の自動マスク(明るすぎ・暗すぎの画素)は同じ発想だが、埋め方が別のアルゴリズム: xcv_ は OpenCV の Telea(高速マーチング)、xsk_ は skimage の biharmonic。しきい値も xcv_ は 8 bit(>235 / <20)、xsk_ は float(>0.92 / <0.08) | **まとめない** —— biharmonic と Telea —— 別のアルゴリズム |
| `laplacian` | `cv_laplacian` / `xkor_laplacian` | 違う | 0.834 | 0.834 | 1 | — | 窓・カーネルの形: cv_ は 3×3 の 4 近傍カーネル [0,1,0;1,−4,1;0,1,0] 固定、xkor_ は kornia の laplacian(3×3 は 8 近傍 [1,1,1;1,−8,1;1,1,1]、a で窓 3〜9)。カーネルが違う | **まとめない** —— 4 近傍と 8 近傍のカーネル |
| `measure_pairs` | `m1_measure_pairs` / `measure_pairs` | 比較不能 | — | — | — | — | 入出力の型が違う: 台帳の measure_pairs は測定ハンドル(線の位置・幅)を受けてエッジの組の表を返す。m1_measure_pairs は中央の 1 本の線で明るい物体(立ち上がり→立ち下がりの組)の数を数える feature(b が相対振幅のしきい値) | **まとめない** —— 台帳の測定ハンドル版と a, b 入口の数え上げ —— 別の入口 |
| `measure_pos` | `m1_measure_pos` / `measure_pos` | 比較不能 | — | — | — | — | 入出力の型が違う: 台帳の measure_pos は測定ハンドルを受けてエッジ位置の表を返す。m1_measure_pos は中央の線上のエッジ点を contour で返す | **まとめない** —— 同上 |
| `median` | `cv_median` / `median` | 違う | 0.993 | 1.04 | 1.74 | 0.0039 ✓<br>0.0039 ✓<br>0.0039 ✓ | つまみの写し方: 窓の写し方が違う: cv_ は 3+2int(3a)、core は _k(a) = (3,5,7,9)[int(4a)](既定 a = 0.5 で 5 と 7)。窓を揃えると(ALIGNED)差は cv_ の 8 bit 量子化の 1/255 だけ | **一部まとめてよい** —— median と xkor_median は内部で一致(端は reflect と 0 埋めで違う)。cv_median は窓の写し方と 8 bit が違う |
|  | `cv_median` / `xkor_median` | 違う | 0.993 | 1.1 | 18 | 0.0039 ✓ | つまみの写し方: xkor_median の窓は core と同じ _k(a)。cv_ と窓を揃えると差は 8 bit 量子化の 1/255 だけ(ALIGNED) |  |
|  | `median` / `xkor_median` | 一致 | 6.5e-08 | 1.02 | 1.74 | — | 独立な実装どうしの一致 |  |
| `meijering` | `sk_meijering` / `xsk_meijering` | 一致 | 0 | 0 | 1 | — | 独立でない: skimage.filters.meijering(sigmas=range(1, 4)) を両方が呼ぶ。xsk_ は入力を [0,1] に clip するだけ(0〜255 の入力でだけ違う)= 重複した op | **まとめてよい** —— 同じ skimage 関数の重複。xsk_meijering は sk_meijering の別名にしてよい |
| `orb_count` | `xcv_orb_count` / `xsk_orb_count` | 違う | 1 | — | 0 | — | 定義の違い: 別実装の ORB で、検出の既定(FAST のしきい値・ピラミッド・端の 31 画素の除外)が違う。OpenCV 版は edgeThreshold = patchSize = 31 なので 48 px の画像では 0 個になる。つまみは上限数だけ | **まとめない** —— ORB の既定(端の除外・FAST)が違い、小さい画像で件数が大きく違う |
| `otsu` | `cv_otsu` / `otsu` | 近い | 0.007 | — | 0.007 | — | 量子化(8 bit): 同じ大津法。cv_ は 8 bit に落としてから 256 段で切る、core は値の範囲を 256 ビンに分けて**ビンの上端**で切る。ビンの境に画素が集まる滑らかな画像で 0.7 % の画素が入れ替わる | **近似としてなら** —— 同じ大津法。しきい値のビン内の位置と 8 bit 量子化で 1 % 前後の画素が入れ替わる |
|  | `cv_otsu` / `sk_otsu` | 近い | 0.012 | — | 0.012 | — | 量子化(8 bit): 同じ大津法。skimage はビンの**中心**をしきい値にして v > t、cv_ は 8 bit の整数で切る |  |
|  | `otsu` / `sk_otsu` | 近い | 0.0052 | — | 0.0052 | — | 定義の違い: 同じ大津法でしきい値をビンのどこに置くかが違う: core は上端(argmax のビンに居る画素を背景に)、skimage は中心。core は 2026-09-26 に中心から上端へ直した(docs/hardening/otsu-threshold-at-the-bin-midpoint.md) |  |
| `regress_contours` | `hx_regress_contours` / `xg_regress_contours` | 違う | 0.997 | — | — | — | 名前だけ同じ別の処理: hx_ は輪郭ごとの直線当てはめの残差 RMS の平均を max(H, W) で割る(無次元)。xg_ は全輪郭の点をまとめた共分散の最小固有値の平方根(画素)。正規化も集め方も違う | **まとめない** —— 正規化と集め方が違う |
| `richardson_lucy` | `iv_richardson_lucy` / `xsk_richardson_lucy` | 違う | 0.887 | 1 | 1 | — | 定義の違い: 同じ Richardson–Lucy だが仮定する PSF が違う: iv_ は σ = 1.2(RL_SIGMA)のガウシアン、xsk_ は 3×3 の箱。反復回数の写し方も違う(iv_ 1+round(14a)、xsk_ 2+int(15a)) | **まとめない** —— 仮定する PSF(ガウシアン / 3×3 の箱)が違う |
| `sart_reconstruct` | `sart_reconstruct` / `tm_sart_reconstruct` | 比較不能 | — | — | — | — | 入出力の型が違う: 台帳の sart_reconstruct は sinogram と角度を受ける(反復 10 回の既定)。tm_sart_reconstruct は画像の行を角度とみなし、反復 1〜5 回・緩和 0.05〜0.4 を a, b に写した入口(skimage の iradon_sart) | **まとめない** —— 台帳の sinogram 版と a, b 入口 —— 入口が違う(同じ名前で残すなら tm_ を別名に) |
| `scharr` | `cv_scharr` / `sk_scharr` | 違う | 0.266 | 0.266 | 0.266 | — | 定義の違い: 勾配の合成が違う: cv_ は \|Gx\| + \|Gy\|(L1)、sk_ は sqrt((Gx² + Gy²)/2)(L2)。どちらも画像ごとの最大で割る | **まとめない** —— 勾配の合成が L1 と L2 |
| `shape_index` | `shape_index` / `sk_shape_index` | 比較不能 | — | — | — | — | 入出力の型が違う: どちらも Koenderink の shape index だが、台帳の shape_index は点群(近傍 k 点の曲率)、sk_shape_index は画像の輝度面(Hessian の固有値) | **まとめない** —— 点群版と画像版 |
| `skeleton` | `sk_skeleton` / `skeleton` | 一致 | 0 | — | — | — | 独立でない: skimage.morphology.skeletonize を両方が呼ぶ。skimage が無い環境の skeleton は numpy_twins.skeletonize に落ち、それも探針の 2 枚で skimage と 1 画素も違わない(門で確かめる) | **まとめてよい** —— 同じ skimage 関数(numpy の双子も一致)。sk_skeleton は skeleton の別名にしてよい |
| `smallest_rectangle1` | `r2_smallest_rectangle1` / `smallest_rectangle1` | 一致 | 0 | — | — | — | 独立・自明: 独立な numpy 実装 2 本(前景画素の行・列の最小・最大で塗る)。定義が自明なので差 0 は当然 | **まとめてよい** —— 段 1 の C1(r2_smallest_rectangle1 → smallest_rectangle1 の別名)と同じ結論 |
| `tophat` | `cv_tophat` / `tophat` | 違う | 1 | 1 | 1 | — | 窓・カーネルの形: 構造要素が違う: cv_ は楕円で大きさ 3+2int(3a)、core は正方形で _k(a) = 3, 5, 7, 9(a の 4 分割)。既定 a = 0.5 で楕円 5×5 と正方形 7×7。同じ構造要素なら scipy と OpenCV は差 0(確かめた) | **まとめない** —— 構造要素の形(楕円 / 正方形)と大きさの写し方が違う |
| `unsharp` | `unsharp` / `xkor_unsharp` | 違う | 0.194 | 0.194 | 1 | 2.9e-07 ✓<br>2.5e-07 ✓<br>3.4e-07 ✓ | つまみの写し方: つまみの意味が違う: core は a が強さ 1.5a 倍・b が σ = 0.5+1.5b、xkor_ は強さ 1 固定(a 未使用)・b が σ = 0.5+2b。揃えると(ALIGNED)画像全体で 3e-7 で一致。2026-11-03 までは xkor_ の窓が 5×5 固定で揃えても一致しなかった(直した) | **つまみを揃えればまとめてよい** —— xkor_unsharp の a を強さに繋げば core と一致する(今は a 未使用・強さ 1 固定) |
| `wiener` | `xsk2_wiener` / `xsp_wiener` | 違う | 0.703 | 0.659 | 1 | — | 名前だけ同じ別の処理: xsk2_wiener は skimage の Wiener **逆畳み込み**(5×5 のガウシアン PSF、σ = 0.5+1.5a を仮定)、xsp_wiener は scipy.signal.wiener の**適応雑音除去**(局所分散、窓 3+2int(3a))。名前の Wiener 以外は別物 | **まとめない** —— 逆畳み込みと適応雑音除去 —— 別の処理 |

## つまみを揃えた点

「差はつまみの写し方だけ」という見立てを、つまみを揃えて確かめた点。期待の量は score(内部の振れ幅比)/ affine(定数倍とずれを除いた残り)/ max_abs(内部の絶対差)。門(`tests/test_impl_differential.py`)が毎回確かめる。

| 対 | a 側の (a, b) | b 側の (a, b) | 期待 | 実測 | |
|---|---|---|---|---:|---|
| `cv_median` / `median` | (0, 0.5) | (0, 0.5) | max_abs ≤ 0.0039 | 0.0039 | ✓ |
| `cv_median` / `median` | (0.4, 0.5) | (0.4, 0.5) | max_abs ≤ 0.0039 | 0.0039 | ✓ |
| `cv_median` / `median` | (0.7, 0.5) | (0.5, 0.5) | max_abs ≤ 0.0039 | 0.0039 | ✓ |
| `cv_median` / `xkor_median` | (0.7, 0.5) | (0.5, 0.5) | max_abs ≤ 0.0039 | 0.0039 | ✓ |
| `dog` / `sk_dog` | (0.25, 0.25) | (0.333333, 0.5) | affine ≤ 1e-09 | 5.6e-16 | ✓ |
| `dog` / `xkor_dog` | (0.25, 0.15) | (0.5, 0.5) | affine ≤ 5e-05 | 4.4e-06 | ✓ |
| `sk_dog` / `xkor_dog` | (0.2, 0.5) | (0.5, 0.5) | affine ≤ 5e-05 | 4.4e-06 | ✓ |
| `unsharp` / `xkor_unsharp` | (0.666667, 0) | (0.5, 0) | score ≤ 1e-05 | 2.9e-07 | ✓ |
| `unsharp` / `xkor_unsharp` | (0.666667, 0.5) | (0.5, 0.375) | score ≤ 1e-05 | 2.5e-07 | ✓ |
| `unsharp` / `xkor_unsharp` | (0.666667, 1) | (0.5, 0.75) | score ≤ 1e-05 | 3.4e-07 | ✓ |

## 異常に良い一致の内訳

差がきっかり 0 の組は、両方が同じ下位関数を呼んでいるだけのことがある。独立な実装どうしの一致と区別する。

- `sk_meijering` / `xsk_meijering`: 独立でない —— skimage.filters.meijering(sigmas=range(1, 4)) を両方が呼ぶ。xsk_ は入力を [0,1] に clip するだけ(0〜255 の入力でだけ違う)= 重複した op
- `sk_skeleton` / `skeleton`: 独立でない —— skimage.morphology.skeletonize を両方が呼ぶ。skimage が無い環境の skeleton は numpy_twins.skeletonize に落ち、それも探針の 2 枚で skimage と 1 画素も違わない(門で確かめる)
- `r2_smallest_rectangle1` / `smallest_rectangle1`: 独立・自明 —— 独立な numpy 実装 2 本(前景画素の行・列の最小・最大で塗る)。定義が自明なので差 0 は当然

独立な実装どうしで一致した対(差が 0 でない = 別々に計算して同じ値になった): `bilateral` / `xkor_bilateral`(2.7e-07)、`cv_gaussian` / `gaussian`(7.3e-05)、`cv_gaussian` / `xkor_gaussian`(7.3e-05)、`gaussian` / `xkor_gaussian`(3.8e-07)、`median` / `xkor_median`(6.5e-08)。

## `tb_` の橋渡しの標本

`tb_X` は台帳の関数 `X` を `op(v, a, b)` に写した入口。つまみ k = 0 / 3/7 / 1(既定の 1/4・1・2 倍、範囲表の引数は lo + (hi−lo)k)で、台帳の関数を自分で呼んだ値と比べた。

| 結果 | 件数 |
|---|---:|
| 一致 | 131 |
| 標本外 | 25 |

標本外(入出力の加工つきで独立な検算にならない): `tb_arc_length`、`tb_box_sdf`、`tb_capsule_sdf`、`tb_cutout`、`tb_cylinder_sdf`、`tb_euclidean_cluster`、`tb_lf_depth_from_focus`、`tb_lf_epi_slope`、`tb_normals_to_egi`、`tb_plane_sdf`、`tb_plane_segmentation`、`tb_project_points`、`tb_radius_outlier_removal`、`tb_random_dropout`、`tb_random_rotation`、`tb_random_scale`、`tb_region_growing`、`tb_resample`、`tb_spectrogram`、`tb_specular_diffuse_split`、`tb_sphere_sdf`、`tb_statistical_outlier_removal`、`tb_temporal_band_power`、`tb_temporal_bandpass`、`tb_torus_sdf`。


**名前の衝突**(台帳の `X` と同名の、**別の関数**のレジストリ op がある。`tb_X` は台帳の方と同じ関数): `tb_companding_mu_law` ↔ レジストリ `companding_mu_law(image → image)`、`tb_highpass` ↔ レジストリ `highpass(image → image)`、`tb_local_std` ↔ レジストリ `local_std(image → image)`、`tb_lowpass` ↔ レジストリ `lowpass(image → image)`。段 1 の C2(`signal_*` へ)と同じ組。

## 接頭辞(実装・由来を表すもの)

| 接頭辞 | 何の実装か | op 数 | 住んでいるモジュール |
|---|---|---:|---|
| `cv_` | OpenCV(backends) | 29 | `backends` 29 |
| `dc_` | 分解(backends_decomp) | 7 | `backends_decomp` 7 |
| `deform_` | 変形(backends_deform) | 3 | `backends_deform` 3 |
| `dl_` | torch 実装(backends_dl) | 2 | `backends_dl` 2 |
| `f2_` | フィルタ 第 2 回(backends_filters2) | 10 | `backends_filters2` 10 |
| `hx_` | HALCON 拡張(backends_halcon_ext) | 81 | `backends_halcon_ext` 81 |
| `it_` | 画像道具(backends_imgtools) | 11 | `backends_imgtools` 11 |
| `iv_` | 逆問題(backends_inverse) | 7 | `backends_inverse` 6、`ledger` 1 |
| `m1_` | 1-D 計測(backends_measure1d) | 5 | `backends_measure1d` 5 |
| `macro_` | 自己拡張マクロ(backends_macro) | 4 | `backends_macro` 4 |
| `ph_` | 物理(backends_physics) | 6 | `backends_physics` 6 |
| `r2_` | 領域 第 2 回(backends_regions2) | 11 | `backends_regions2` 11 |
| `r3_` | 領域 第 3 回(backends_regions3) | 10 | `backends_regions3` 10 |
| `sg_` | 分割 第 2 回(backends_segment2) | 7 | `backends_segment2` 7 |
| `sk_` | scikit-image(backends) | 47 | `backends` 47 |
| `sp_` | サブピクセル(backends_subpix) | 6 | `backends_subpix` 6 |
| `tb_` | 型付き台帳の関数の橋渡し(backends_typed) | 163 | `backends_typed` 163 |
| `tf_` | 変換 第 2 回(backends_transform2) | 12 | `backends_transform2` 7、`ledger` 5 |
| `tm_` | 断層(backends_tomo) | 5 | `backends_tomo` 5 |
| `xcv_` | OpenCV 追加(backends_extra) | 8 | `backends_extra` 8 |
| `xcv2_` | OpenCV 追加 2(backends_cv2b) | 5 | `backends_cv2b` 5 |
| `xcv3_` | OpenCV 追加 3(backends_r3) | 8 | `backends_r3` 8 |
| `xg_` | XLD 幾何(backends_xldgeom) | 10 | `backends_xldgeom` 10 |
| `xkor_` | kornia / torch(backends_kornia) | 12 | `backends_kornia` 12 |
| `xmh_` | mahotas(backends_r3) | 10 | `backends_r3` 10 |
| `xpil_` | Pillow(backends_pil) | 13 | `backends_pil` 13 |
| `xsitk_` | SimpleITK(backends_r3) | 14 | `backends_r3` 14 |
| `xsk_` | scikit-image 追加(backends_extra) | 13 | `backends_extra` 13 |
| `xsk2_` | scikit-image 追加 2(backends_ski2) | 11 | `backends_ski2` 11 |
| `xsk3_` | scikit-image 追加 3(backends_r3) | 15 | `backends_r3` 15 |
| `xsp_` | SciPy(backends_scipy) | 11 | `backends_scipy` 11 |
| `xwt_` | PyWavelets(backends_r3) | 9 | `backends_r3` 9 |

## 測った環境

SimpleITK 2.5.6、cv2 5.0.0、kornia 0.9.0、mahotas 1.4.18、numpy 2.4.6、scipy 1.15.2、skimage 0.26.0、torch 2.11.0+cpu(win32)。値は optional 依存の版と OS で下の桁が揺れるので、測り直しは手で回す(この表の生成は JSON だけから決まる)。
