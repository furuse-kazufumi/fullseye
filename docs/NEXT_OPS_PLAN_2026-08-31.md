# 次期 op 拡張計画(2026-08-31 調査、v0.1.4 リリース直後)

2 本の調査(3D 化候補 / GPU 化次バッチ)の確定版。数値は調査時実測。
**採用前検証済みの中核 finding** に ★ を付す(それ以外は実装時に再実測すること)。

---

## A. 2D op の 3D 化候補

### ★ A-0. 最重要: volops の 8 op が ops3d 未登録(検証済み)

`vol_frangi / vol_sato / vol_hessian_blobness / vol_distance_transform /
vol_label / vol_region_props / vol_gradient_magnitude / vol_local_maxima` は
volops.py で実装済み・api.py で公開済みだが、`ops3d._CATALOG` は
`vol_watershed` と `volume_downsample` しか volops から登録していない。
→ 登録が第一手。**ただし op→example 100% カバレッジ invariant(CI 強制)が
あるので、登録 = _CATALOG 行 + example + per-op docs ノート + Studio help の
4 点セット**(「数十分」ではない)。

### A-1. 上位候補(skimage/scipy の 3D 対応は (12,13,14) 配列で実測済み)

1. **voxel 閾値族**: vol_otsu / multiotsu / li / yen / hysteresis / sauvola /
   niblack — skimage 全て 3D OK。現状 3D は手動レベル閾値のみ
2. **3D 領域選別**: fill_holes3d / clear_border3d / remove_small_holes3d /
   select_shape3d(vol_region_props の述語フィルタを被せる)
3. **feature transform 3D**: `distance_transform_edt(return_indices=True)` は
   N-D OK。3D 側は距離「値」のみで最近傍インデックス op が皆無
   (占有格子の ESDF 勾配・肉厚計測に直結)
4. **voxel デノイズ**: TV / NLM / wavelet(skimage 3D OK)+ Perona-Malik
   6 近傍化(自前 10 行)
5. **voxel 幾何変換**: affine / zoom / rotate / 等方リサンプル(ndimage N-D OK)。
   3D に voxel 幾何変換 op が 1 つも無い。**spacing 引数を最初から持たせる**
6. 属性モルフォロジー 3D + granulometry / ball SE 経路 / blob_log 3D /
   CLAHE 3D / マーカー制御分水嶺一括 / FFT 帯域 / inpaint / RL deconv /
   rank・entropy 3D(いずれも skimage/scipy 3D 実測 OK、ラッパ中心)

### A-2. 2D 専用で自前実装が要る(後回し)

canny(実装済 canny3d 流儀で個別移植)/ LBP-3D・GLCM-13方向(需要大・工数大)/
bilateral 3D(27 タップ)/ Golay 3D(正準対応なし)/ cone-beam FDK(大)。

### A-3. 設計注意

- 新規 3D op は `spacing=None` 引数を標準装備(異方性ボクセル対応)
- voxel→voxel op は ops.py VOLUME sort と ops3d の**両方に登録**すると
  進化探索(decode)からも見える

---

## B. GPU 化 次バッチ(accel 系)

### ★ B-0. バグ修正が先(コードで検証済み)

1. **padding 不整合**: `_sep_conv`(accel.py:56)/ `_conv`(:89)/
   `_unfold_reflect`(:160)/ `_std_filter`(:233)が torch `reflect`
   (端非複製)のまま。scipy 既定と一致する `_pad_sym`/`_sep_conv_sym`
   (:66-86)は gaussian 系にしか適用されていない。
   調査実測では sym 化で sobel/laplace/prewitt/unsharp/median/percentile/
   std_filter が full-image 1e-7 級に。**dog「faithful 不可」判定
   (accel.py:493-495 / GPU_ACCEL_PLAN.md:37-39)は誤りで、sym 化で 6.7e-6**
2. **parity ゲートの穴**: `parity()`(accel.py:568)は a=0.5,b=0.4 の 1 点
   + 固定 3px マージン。a≥0.75 で k=9(半径 4px)が食い込む。
   accel_vol の `_op_margin`(accel_vol.py:204-210)方式を移植し
   a∈{0,.25,.5,.75,1} スイープに

### B-1. バッチ順序(調査時 torch プロトタイプで忠実性実測済み)

| Batch | 内容 | 効果 |
|---|---|---|
| 0 | 上記バグ修正 | 既存 7 op が full-image 一致、dog 解禁 |
| 1 | **HALCON 別名 33 op を ACCEL に追記**(実装ほぼ 0。sobel_amp/gauss_filter/gray_*_rect 等が既存 kernel と 1e-7 一致) | 看板例 `["gauss_filter","sobel_amp","otsu"]` が GPU 化へ前進 |
| 2 | **otsu 一族 4 op**(bit-exact 実測)+ canny + adaptive_gauss_thresh + local_max + dyn_threshold | otsu は 20 RECIPES 中 4 に登場する最頻未対応 op。image→region 関門が開き GPU 区間が融合(転送削減)。RECIPES カバレッジ 45%→推定 70%+ |
| 3 | **morphological reconstruction primitive**(測地膨張の不動点)| fill_up/fill_holes ほか recon 一族 ~14 op を 1 kernel で解錠。champion 32/38→34/38 |
| 4 | 終端 reduction: count_obj(ラベル伝播)/ intensity / entropy_gray / xcv2_lap_var | D2H が画像→スカラーに |
| 5 | arithmetic 9 + compass edges 6 + disk graymorph 4 + 拡散 5 | 数の面取り |

### B-2. 配線ミス(実装済みなのに到達不能)

- accel_vol の 3D 二値 morphology 5 kernel(vol_reg_dilate_g 等)は registry に
  対応 op が無く `_seg_kind` が真にならない → ops.py `_DEFS` へ登録が先
- accel_match の 3D NCC 3 本は `MATCH_ACCEL` 未登録(cv2 に 3D matchTemplate は
  無い = 差別化点)

### B-3. 諦める/後回し

幾何変換 wave2(scipy order=3 B-spline の IIR 前置フィルタは torch で bit 一致
不能、bilinear/bicubic とも 5e-3 不通過 — metric-faithful 例外扱いを検討)/
contour・XLD 83 op(ragged・逐次)/ regionprops(count/area 以外)/ EDT /
skeleton 系 / backend ブラックボックス 368 op / color 3ch(_to_batch が
(N,1,H,W) 前提)/ trimmed_mean(rank 規則不一致 4.8e-2、要調査)。

---

## C. 手・指のモーショントラッキング(2026-08-31 ユーザー発案)

> 「手の動きをモーショントラッキングしている事例が結構見られる。指の動きとか、
> 見れるようになると Physical AI への応用が効きやすい」

fullseye ミッション(Physical AI / evis 視覚の統一 I/F)に直結。G1 歩行で実証済みの
「mocap → 模倣 RL」パイプラインの**手版**が本命: 動画 → 手ランドマーク →
evis 手(相反 u + 共収縮 c の 34 次元)へリターゲット → 箸 pick-place の模倣。

候補 op(3 層):

1. **古典層(依存なし・コア方針適合)**: 前景/肌色セグメント → 輪郭 →
   凸包欠陥(convexity defects)で指先候補・指数カウント。HALCON 流でもある。
   既存 op(contour/convex hull/skeleton)の組み合わせ + 新 op 2〜3 個で成立。
   ロバスト性は限定的(デモ・単純背景向け)
2. **学習層(optional extra)**: `hand_landmarks` op — 21 キーポイント + 左右。
   MediaPipe Hands(Apache-2.0、ライセンス適合)を optional backend
   (`pip install mediapipe`)か ONNX 変換で。返り値 (N, 21, 3)。
   身体版 `pose_landmarks`(33 点)も同一機構で追加可
3. **3D 化・下流ブリッジ**: 既存 stereo スイート / D435i depth で 3D リフト →
   `hand_retarget`(21 点 → 関節角、evis 34 次元作動への写像)。
   これは fullseye というより evis 側のブリッジ(所属は実装時に判断)

実装順の提案: 2 → 3(2 が最小工数で最大効果。1 はデモ/教材価値)。

実現可能性の実測(2026-08-31): mediapipe 1.0.1 は py3.11 Windows に**導入済み**。
ただし 1.0 系は legacy solutions 廃止・モデル非同梱で、`HandLandmarker` には
`hand_landmarker.task`(storage.googleapis.com、~8MB、モデルも Apache-2.0)の
DL が 1 回必要 → **着手時にユーザー確認を取ってから**。fail-closed(モデル不在なら
明示エラー+DL 手順提示)の optional extra として設計する。

---

## 実装時の共通規律

- 数値はすべて実装時に再実測してから主張する(この文書の数値は調査時点)
- op 追加は 4 点セット(登録 / example / per-op docs / Studio help)+
  fingerprint drift CI を通す
- GPU 化は忠実性ゲート(5e-3)を**修正後の parity で**通す

## D. 2D→3D ギャップ棚卸し 第2波(2026-08-31 夜、domain/boundary/RLE 実装後)

domain(4op)/ boundary(2op)/ rle_region(5op)/ vol_tiled_map は実装済み。
2D 45 カテゴリ × 3D カタログ(58 カテゴリ 291 op)の概念突き合わせで残る欠け。
数値・用途の根拠は実利用ドメイン(CT/MRI/顕微鏡/産業検査)の定番度で採点。

### 優先度 高(定番なのに voxel 界に無い)

1. **intensity/gray 系(2D は 41 op、3D はゼロ)**
   - `vol_window_level`: CT の HU windowing(放射線科の毎日の操作)。center/width
     で [0,1] へ写像。実装 1 時間・依存なし
   - `vol_equalize` / `vol_gamma` / `vol_stretch`: ヒスト平坦化・ガンマ・
     コントラスト伸長の 3D 版
2. **geometry transform 系(2D は 28 op、3D は形式変換のみ)**
   - `vol_resize`(ndimage.zoom、spacing 再計算を返す)/ `vol_rotate`(軸+角度)
     / `vol_affine`(4x4 行列)。位置合わせ後のリサンプリングに必須。
     match3d 内部に affine 実装は既存(公開されていないだけ)
3. **measure1d の 3D 版(virtual probe)**
   - `vol_profile_line`(2 点間の強度プロファイル、spacing 対応)+
     `vol_edge_probe`(プロファイル上のエッジ対検出=肉厚・壁厚)。産業 CT 計測の核。
     2D measure1d(5op)の縦持ち版
4. **restoration**: `vol_richardson_lucy`(3D デコンボリューション、共焦点顕微鏡の
   定番。skimage.restoration に 2D 実装あり、nD 対応)

### 優先度 中

5. **frequency**: `vol_fft_bandpass` / `vol_fft_lowpass`(3D FFT フィルタ、
   リング/縞アーチファクト除去)。complexops は 2D 専用
6. **arithmetic**(2 volume の add/sub/absdiff/blend): numpy 1 行だが、RAG が
   「引き算で差分検出」を提案できる目録の完備性に価値
7. **noise**(ガウス/ポアズン付加): データ拡張・頑健性試験用
8. **RLE の充実**: run のまま集合演算(union/intersect/difference — HALCON
   region 演算の本体)、成分ごと RLE 化(vol_label → 成分別 VolRLE リスト =
   「数千領域を保持」のユースケース本番)

### 優先度 低(重い/ニッチ)

9. texture 3D(GLCM radiomics)/ tomography 系(xct プロジェクトと重複)/
   vol の histogram 統計(percentile 系)

### 効率化の実測(2026-08-31 夜 PoC、scratchpad/poc_efficiency.py)

- **RLE**: 384^3 部品マスクで dense bool の 1/145、volume 0.08ms vs 23.5ms、
  bbox 0.13ms vs 166ms → **実装採用**(volregion.py、5op)
- **タイル処理**: gaussian σ=2 を overlap=8 で厳密一致(最大差 0.0)、ピーク作業
  メモリはスラブ比例 → **実装採用**(vol_tiled_map)
- **float32 経路**: gaussian で 1.6x 速・半メモリ・相対誤差 7.7e-8 → 保留
  (float64 規約の変更を伴う。opt-in dtype 引数の設計を先に決める)

## E. 実装状況更新(2026-08-31 深夜)+ 1D 監査

§D の高優先はすべて実装済み(実装状態 4 段: **動作実証済み** = 専用テスト+GT example
+フルスイート 6,483 passed):

- ✅ gray 4op(volgray)/ geom_transform 3op(volxform)/ probe 3op(volprobe)
  / frequency 3op(volfreq)/ restoration 2op(volrestore)
- ✅ RLE 集合演算 union/intersect/difference(掃引エンジン、192^3 で 3.1ms 実測)
  + vol_rle_components(run 内ラベル一定の構造事実で run 単位振り分け)
- ✅ vol_tiled_map(z スラブ streaming、局所 op は overlap>=footprint で厳密一致)
- ✅ Studio volume_to_shell_points + _load_3d_file の volume 対応
  (DICOM/NIfTI/NRRD/TIFF → Otsu → 殻点群 → そのまま一人称ウォークスルー)

### 1D 監査(ユーザー発問「1D ももっと op があるべきでは」への答え)

**「足りない」でなく「あるのに接続されていない」が正診**:

- **funct1d.py(23 関数、HALCON funct_1d 対応)が完全な孤児だった**: import 皆無・
  py-modules 非登録(未出荷)・テストなし・カタログ不可視。HALCON funct_1d の
  カバレッジ自体はほぼ完備(smooth/derivate/integrate/zero_crossings/
  local_min_max/compose/match/distance/transform 等)
- dsp.py(信号 16 関数)は出荷済みだが OP_CATALOG 不可視だった
- 対応: funct1d の品質採用(fail-closed 化+テスト+配線)+ **ops1d.py 統一
  レジストリ新設(37op/3 カテゴリ)** + OP_CATALOG に 1-D 節を追加
- 残 backlog: opdocs の per-op ノートに dim="1d" を通す(生成系の次元追加)、
  1D の追加 op 候補(変化点検出/自己相関周期推定/1D median/ロバスト平滑)は
  funct1d 接続後の需要を見て

## F. 数学 op ファミリのロードマップ(2026-08-31 ユーザー方針)

**北極星**: 「数学辞典に載る問題を全て扱えるくらいの op 量」+「岡潔の数学
(多変数複素関数論)まで」— 長期プログラムとして tier で積む。正直な整理:
岡の定理そのもの(連接性・Cousin 問題)は数値 op にならないが、計算可能な
切り口は豊富。台帳 = opsmath.py(OP_CATALOG に Math 節)。

- **tier 1(済・敵対検証済)**: linalg 6 / stats 5 / interp+poly 5 = 16 op。
  数学系 RAD コーパス 4 分野で選定裏取り。敵対検証で complex 無言切り捨て等
  3 バグ修正(53 テスト)
- **tier 2(複素解析の計算可能面)**: ✅ **実装済 10 op**(2026-09-01、mathops
  の `complex` カテゴリ)。輪郭を複素点列(新語彙 `cpoints`)として持つ設計に
  倒し、`cplx_contour_circle` / `cplx_poly_eval` / `cplx_contour_integral` /
  `cplx_winding_number` / `cplx_cauchy_value` / `cplx_argument_principle` /
  `cplx_laurent_coeffs`(留数 = c₋₁)/ `cplx_joukowski` / `cplx_mobius` /
  `cplx_cr_residual`。全 op が閉形式 GT テスト(∮dz/z=2πi の 2 次収束・
  z³−1 の零点数・w=2cos t・1/k!・conj(z)→2)で固定、敵対検証で 3 バグ修正
  (np.gradient 既定の 1 次端点で正則な z² が 2.5% 残差 / Laurent の r^-k
  overflow が無言のゼロ / str が数値として黙って解釈)。**未実装のまま残す**:
  Schwarz–Christoffel 数値写像、Padé 近似・収束半径推定、Poisson 積分・
  調和共役(次の波の候補)
- **tier 2 の正直な限界(記録)**: 巻き数・偏角の原理は標本多角形の量なので
  粗い輪郭では**低く数える**(z⁵ を 4 点円で数えると 1)。原理的に局所検出
  できないため π/2 で `RuntimeWarning` を出し、「分点を倍にして安定するまで」
  を正典として文書化した
- **tier 3**: 最適化(1D 求根 brent・黄金分割 / 多変数 BFGS ラッパ / 線形計画)、
  特殊関数(erf/gamma/bessel = scipy.special の fail-closed 面)、ODE 初期値
- **tier 4**: 確率(分布のあてはめ・検定)、数論の実用切り口(合同・CRT =
  位相 unwrap の親戚)、グラフ理論(最短路 = geodesic3d と接続)
- 規律: 各 tier とも「解析 GT テスト+HALCON/一次文献対応+敵対検証」の
  三点セットを通ってから目録へ。scipy にあるものは「fail-closed の顔」を
  付ける(無言 NaN・無言型強制の封鎖)のが Fullseye の付加価値
