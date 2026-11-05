# 型のつながり ―― 全型の役割と処置

`py -3.11 tools/type_connectivity.py --md docs/TYPE_CONNECTIVITY.md` の生成物。手で編集しない(直すのは `docs/TYPE_ROLES.json` と op の宣言)。門は `tests/test_type_connectivity.py`。

数え方: 入力は **全入力**(`in_sorts`)。「入口から届く」は、入口の型(台帳に `entry` がある型)と引数だけで値を作る op から始め、**全入力がそろった op** の出力を足していく不動点。「終端へ届く」は、受ける op をたどって `terminal` の型に行けること。

```
型 104(うち any 1) / 入口として数える型 30 / 終端として数える型 13
分類: a 5 / b 10 / c 6 / d 10 / ok 73

全入力で数える(この表の基準):
  行き止まり 0(理由なし 0) / 入口なし 1(理由なし 0)
  入口から届かない 0 / 終端へ届かない 0 / 細い型(産 or 受 <= 2) 50
参考: 第 1 入力だけ・image から(最初の数え方):
  行き止まり 1 / 入口なし 0 / image から届かない 14 / 細い型 54
```

## 分類の意味

- **a** —— 型の付け方の揺れ
- **b** —— 受け手か作り手が本当に欠けていた
- **c** —— 終端として正しい
- **d** —— 入口として正しい
- **ok** —— 両側に十分つながっている

## 直したもの・案だけのもの

- この版で直した(b): `frame`, `gradient`, `graph`, `hessian`, `jones`, `keypoints`, `match`, `pointmap`, `positions`, `synapse_table`, `tokens`
- 直していない(案は下の表): `axes`

### 設計の判断が要るもの(実装していない)

型の宣言の変更・新しい型名は CONTRIBUTING で破壊的変更の扱い。1.0 の前に決める。

| 型 | 分類 | 案 |
|---|---|---|
| `axes` | a | moment_axes の出力を新しい型 principal_axes に分ける(影響 1 op、型で通っていた誤った鎖 5 本が消える)。受け手は match_pca / obb の前段として principal_axes -> matrix(主軸)/ position(重心)の 2 本。新しい型名なので 1.0 の前にユーザーが決める。 |
| `gradient` | b | sobel3d の出力を gradient と同じ (gmag, gvec) 形にそろえるか、利得つきの別の型に分ける。いまは受け手が 2 形を見分けて sobel3d の利得 32 を割るので鎖は正しく動くが、利得 1 の 3 本(将来の微分可能レンダラ Mitsuba cuda_ad の勾配など)を渡すと 1/32 に出る —— 形だけでは利得を区別できない。差別化の機会: gradient / hessian を一級の型として受ける op 群(この版で大きさ・面らしさ・行列式・管らしさの 4 本)を、構造テンソルの固有値・主曲率・発散/回転へ広げると、AI が型だけで微分の鎖を安全に組める。AD 勾配をこの型で受けるには、型の値に利得(単位)を持たせる設計が先に要る。 |
| `hessian` | b | 差別化の機会: hessian3d 以外(多尺度ガウス微分・AD の 2 階微分)の Hessian も同じ 6 成分の形で渡せば、管らしさ・塊らしさ・行列式・主曲率を共通に引き出せる。voxel_to_hessian は尺度正規化を引数(scale_normalize、既定は掛けない = hessian3d と同じ 1/voxel²)にした。値そのものに尺度を持たせるかは未決なので、多尺度の受け手は案だけ。 |
| `keypoints` | a | 型を (row, col) と (u, v) の 2 つに分けるか(keypoints_rc を足す等)。分ければ取り違えが型で止まるが、keypoints を返す・受ける op の宣言を全部見直すことになる(産 18 / 受 19)。 |
| `metrologymodel` | d | 差別化の機会: CAD・図面(dxf / 3MF)から計測モデルを組む入口(table -> metrologymodel)があると『設計値から検査を組む』を型で鎖にできる。新しい入口 op の仕様(図面のどの要素を何の計測にするか)が要るので案だけ。 |
| `positions` | b | 名前が position(3-D の 1 点)と 1 文字違いで紛らわしい。event_positions への改名は影響 1 op だが型名の変更なので 1.0 の前にユーザーが決める。 |
| `shapeset` | d | 実データの入口として points を K 本束ねる op(対応が取れていることを形で確かめる)。可変個の入力を取る型の扱いが要るので案だけ。 |
| `simmodel` | d | 差別化の機会(Fullseye の中心: 物理シミュで真値を作り AI に組合せを考えさせる): いまは鎖を dict で手書きする。型つきの op の鎖(engine の段の列)をそのまま simmodel にする入口と、simmodel x design(実験計画)-> images(掃引した合成画像の束)の op があると、『計画 -> 合成 -> 測る -> 校正』が型だけで組める。design 型はもう在る(doe_*)。新しい op の引数の型(段の列)の決め方が要るので案だけ。 |
| `sweep` | d | 差別化の機会: 計測した signal と掃引軸(波長・z)から sweep を作る入口(signal x signal -> sweep)。掃引軸を値に持たせるか(型の中身の変更)を決める必要があるので案だけ。 |
| `tokens` | b | matrix -> tokens の入口(軸の順を引数で名指しさせる形)を足すかどうか。 |
| `volseq` | d | voxel を時間方向に束ねる入口(voxel x k -> volseq)。可変個の入力の扱いが要るので案だけ。 |

## 全型の表

| 型 | 分類 | 産 | 受 | 入口 | 終端 | 処置 | 理由 | 根拠(検索語・確かめた関数) |
|---|---|--:|--:|---|---|---|---|---|
| `angle` | ok | 2 | 2 |  |  | none | matrix_to_angle と angle_to_matrix の往復(opsreprconv algebra)に refine_rotation_z の初期角が載る。細いが族の中で閉じている。 | OP_INDEX 産 2 / 受 2。reprconv.angle_to_matrix の docstring(度)。 |
| `any` | ok | 107 | 147 |  |  | none | 型の付いていない値の総称(identity など素通しの op と、型の宣言が未整理の台帳 op)。到達の計算では『どの型でも満たす』として扱う。 | engine._compatible が any を全型と両立させる。tools/gen_op_facets.py は any を unknown / poly に読み替える。 |
| `attnmap` | ok | 2 | 2 |  |  | none | attention_scores(tokens, tokens) が産み attention_weights / attention_apply が受ける、注意機構の中間値。attention_apply が tokens に戻し、tokens_to_matrix で外へ出られる。 | opsllmcore の score カテゴリ 3 op。 |
| `axes` | a | 2 | 5 |  |  | open | 別物 2 つが同じ型名に同居している: annotate.axes_transform はグラフ描画の座標変換 dict、match3d.moment_axes は点群の (重心 (3,), 主軸 (3,3), 固有値 (3,)) の 3-tuple。受け手 5 op(data_to_pixel / ticks / grid_lines / plot_series / axes_frame)は全部前者を読むので、moment_axes の返りを渡すと型の上では通る鎖が 5 本ある。 | grep '"moment_axes"\/"axes_transform"' ops*.py、annotate.py:1259 と match3d.py:421 の docstring を読んだ。 |
| `beatcube` | ok | 4 | 9 |  |  | none | 干渉の拍の立方体(複素)。産 4 / 受 9、2-D レジストリと台帳の両方にある。 | TYPE_TO_SORT['beatcube']。 |
| `bspline_curve` | ok | 1 | 1 |  |  | none | fit_bspline_curve(points) の係数記録。正直な出口は eval_bspline_curve(-> points)の 1 本で足りる(係数を表にしても下流が無い)。 | opsreprconv の docstring『残した袋小路』と同じ判断。 |
| `bspline_surface` | ok | 1 | 2 |  |  | none | 曲面当てはめの係数記録。出口は eval_bspline_surface(-> image2d)と surface_residual(-> measurement)。 | opsreprconv の docstring『poly_surface / bspline_surface』。 |
| `calresult` | ok | 5 | 5 |  |  | none | simcal_fit が simmodel から作る校正結果。check 系 4 op と simcal_report(-> table)で閉じる。simmodel が入口なので届く。 | opssimcal の fit / check / report。 |
| `cimage` | ok | 10 | 15 |  |  | none | 2-D 複素画像。産 10 / 受 15。 | TYPE_TO_SORT['cimage']。 |
| `color` | ok | 5 | 11 | カラーカメラの取り込み(acquire の RGB)。2-D レジストリの色画像。 |  | none | 2-D レジストリの (H,W,3) 色画像。台帳の rgbimage / rgb とは分けてある(色の符号化が違うと黙って値がずれる。opsimgmetrics.NEW_SORTS の実測)。 | ops.COLOR、opsimgmetrics.NEW_SORTS['rgb']。 |
| `conn_graph` | ok | 6 | 20 |  |  | none | n×n の重みつき有向隣接行列。消費 20。これまで入口は synapse_table だけで、synapse_table を作る op が無かったため画像からも表からも届かなかった。この版で knn_graph_to_conn_graph(graph ->)と synapse_table_from_table(table -> synapse_table)が入口になった。 | opsconngraph の docstring『型語彙』。 |
| `contour` | ok | 43 | 67 |  |  | none | XLD 輪郭 dict。2-D レジストリの主要型(産 43 / 受 66)。 | docs/ADDING_OPS.md の Sort contract。 |
| `coordgrid` | d | 1 | 6 | grid_coords() が引数だけで作る座標格子(SDF を評価する場所)。画像から作るものではない。 |  | none | SDF 族の評価点。入口は合成(grid_coords)が正しい。 | OP_INDEX: grid_coords の in_sorts = []。消費は *_sdf 6 op。 |
| `countrate` | ok | 3 | 3 |  |  | none | 光子のレート [Hz]。counts との往復(gate 時間つき)がある。 | reprconv.countrate_to_counts / counts_to_countrate。 |
| `counts` | ok | 13 | 17 |  |  | none | 光子カウント(非負の 1-D)。産 13 / 受 17。countrate との往復は gate 時間つき。 | TYPE_TO_SORT['counts']、opsphoton の族、reprconv.counts_to_countrate。 |
| `cpoints` | ok | 4 | 8 |  |  | none | 複素平面上の順序つき点列(周回積分用)。産 4 / 受 8。 | opsmath の複素族(cplx_cauchy_value / cplx_contour_integral が受ける)。 |
| `cscalar` | ok | 3 | 1 |  |  | none | 複素スカラ。cscalar_to_polar(-> pairs)が出口。 | reprconv.cscalar_to_polar。 |
| `ctgeometry` | d | 1 | 8 | ct_scan_geometry() が引数(方式・軌道・検出器の寸法)だけで作る CT の幾何。画像から作るものではない。 |  | none | CT のスキャン方式の族(ctscan)の共通の幾何。入口は合成(ct_scan_geometry)が正しい。 | OP_INDEX: ct_scan_geometry の in_sorts = []。消費は ct_forward_project / ct_adjoint_project / fdk・sirt・os_sart・tv_reconstruct / ellipsoid_projections / ct_dual_energy_reconstruct(第 8 便、2026-11-04 の統合で行を足した)。 |
| `curvature` | ok | 4 | 2 |  |  | none | 主曲率。出口は curvature_to_shape_index / curvature_to_table。中身は 3 つの形が同居している(既知、opsreprconv の docstring『実測した既存の型の嘘』)が受け手が両方を読むので、つながりの問題ではない。 | reprconv._principal が 3 形を受ける。 |
| `deformation` | ok | 1 | 2 |  |  | none | tps_fit の変形 dict。tps_warp と deformation_to_points が受ける。 | reprconv.deformation_to_points。 |
| `depth` | ok | 17 | 37 | 距離センサ(RealSense / ZED / OAK / Kinect、acquire の unit=m)。 |  | none | 深度画像 [m]。産 16 / 受 37。 | docs/CONNECTIVITY.md の acquire 表(unit = m)。 |
| `descriptor` | ok | 12 | 3 |  |  | none | 形状記述子。matrix / table への出口がある。 | reprconv.descriptor_to_matrix。 |
| `design` | ok | 8 | 5 | 実験計画(doe_lhs / doe_box_behnken など、引数だけで作る計画表)。 |  | none | 実験計画の表。作るのは引数だけ(計画は測る前に決めるもの)なので入口が正しい。 | opsmultivar の plan カテゴリ 7 op が in_sorts = []。 |
| `efdmodel` | ok | 1 | 4 |  |  | none | 楕円フーリエ記述子のモデル。reconstruct / invariants / normalize / descriptor_distance の 4 出口。 | elliptic_fourier(pairs)。 |
| `entries` | d | 0 | 1 | 凡例の中身 (色, 文字) の列。図を描く人が書く内容で、計算から出てくる値ではない。 |  | none | legend_box の第 2 入力だけが使う型。OP_INDEX の sorts 一覧には載っていない(in_sorts にだけ現れる)。 | annotate.legend_box の docstring(entries: (color, text) の列)。grep 'entries' を op 名・in/out で引き、作り手 0。 |
| `feature` | c | 123 | 1 |  | 2-D レジストリの有限スカラ(面積比・円形度など)。測った結果そのもの。 | none | 産 122 に対して受 1(feature_to_img)。スカラの測定値は終端で正しい。 | ops.FEATURE、docs/ADDING_OPS.md『feature → a scalar float』。 |
| `file` | c | 1 | 2 | ディスク上の音声ファイル(read_wav / read_audio が読む)。 | write_wav の書き出し先(ファイルを作ることが仕事)。 | none | ファイルのパス。書き出しの終端であり、読み込みの入口でもある。 | ops1d: write_wav(signal) -> file、read_wav(file) -> signal。 |
| `fingerprint` | ok | 1 | 2 |  |  | none | センサの PRNU 指紋。fingerprint_correlate / fingerprint_strength_map が受ける。 | opsimgforensics。 |
| `flow2d` | ok | 9 | 21 |  |  | none | 2-D の速度場 (H,W,2)。PIV 族の主要型で、産 8 / 受 20。 | opspiv(piv_cross_correlate が産み piv_divergence などが受ける)。 |
| `flow_dense` | ok | 4 | 2 |  |  | none | 3-D 密フロー (3,D,H,W)。flow_magnitude / flow_to_rgbimage が出口。 | opsreprconv の flow カテゴリ。 |
| `flow_scattered` | ok | 3 | 2 |  |  | none | 散在フロー (N,3)。flow_speed / flow_apply が出口。 | opsreprconv の flow カテゴリ。 |
| `frame` | b | 1 | 1 |  |  | frame_axis(frame, axis) -> normals を足した(T / N / B の 1 本を単位ベクトル列として取り出す。直線区間の不定な行は拒否)。 | frenet_frame の (T, N, B) を受ける op が 1 つも無かった(行き止まり)。 | grep 'frenet\/frame' を op 名・docs/ops 本文で引いて、frame を入力に取る op は無し(axes_frame は図の枠で別物)。curve3d.frenet_frame の返りを実測。 |
| `gaussians` | ok | 1 | 2 |  |  | none | 3DGS 風のガウス群。points との往復と voxel への出口がある。 | opsreprconv の gaussians カテゴリ。 |
| `gradient` | b | 2 | 2 |  |  | gradient_magnitude(-> voxel)と gradient_coherence(構造テンソルの面らしさ、-> voxel)を足した。受け手は 2 形を見分けて sobel3d の利得 32 を割る(reprconv._gradient_field)。sobel3d の宣言を別の型に分けるかは design。 | gradient3d と sobel3d が産むのに受け手が 0(行き止まり)。加えて中身が 2 形: gradient3d = (gmag, gvec (D,H,W,3)) の numpy、sobel3d = 利得 32 の torch 3 本 (1,1,D,H,W)。取り違えると大きさが 32 倍ずれ例外は出ない。 | edges3d.gradient3d と match3d.sobel3d の返りを実測。grep 'gradient' を op 名で引き、voxel を受ける vol_gradient_magnitude / morph_gradient3d はあるが gradient 型を受ける op は 0。 |
| `graph` | b | 1 | 1 |  |  | knn_graph_to_conn_graph(-> conn_graph)を足した。1 本で graph_components / graph_laplacian_spectrum / graph_layout_spectral など 20 op につながる。 | knn_graph の (idx, dist) を受ける op が 0。隣接行列の族(conn_graph、消費 20)は別にあるのに橋が無かった。 | opsconngraph の docstring『既存の graph 種は knn_graph が産むだけで、受ける側が族の外に無い』。geodesic3d.knn_graph の返りを実測。 |
| `hessian` | b | 2 | 2 |  |  | hessian_determinant(det H、-> voxel)と hessian_vesselness(Frangi 1998、-> voxel)を足した。2026-11-05: 産み手が torch の hessian3d だけで、素の pip install(torch なし)では受け手 2 本に入力が届かなかったので、numpy と scipy だけの産み手 reprconv.voxel_to_hessian(voxel -> hessian、ガウス微分の尺度 sigma、sigma=0 は hessian3d と同じ 3 タップ核)を足した。 | hessian3d の 6 成分を受ける op が 0(行き止まり)。vol_frangi / vol_hessian_blobness は体積から自分で Hessian を作るので、与えられた Hessian からは何も計算できなかった。 | match3d.hessian3d の返り(list の torch 6 本)を実測。grep 'hessian\/frangi\/vessel\/eigen' を op 名・HALCON 名で引いた(sk_hessian / xsk_hessian_eig は 2-D の image -> image)。 |
| `histcube` | ok | 1 | 1 |  |  | none | dToF の到達時刻ヒストグラム立方体。dtof_cube_simulate が作り dtof_cube_depth が受ける(実機の入口は SPAD 装置)。 | backends_typed の TYPE_TO_SORT コメント(histcube を既定語彙から外した理由)。 |
| `image` | ok | 460 | 571 | カメラの取り込み(acquire の normalised 画像)と画像ファイル。2-D レジストリの起点。 | 人が見る絵としての出口(Studio・図)。 | none | 2-D レジストリの (H,W) float [0,1]。台帳の image2d と同じ物(alias)。 | SORT_ALIASES(tools/gen_op_facets.py / studio_search.py / tools/gen_capabilities_index.py)で image2d -> image。 |
| `image2d` | a | 275 | 427 | 台帳側の画像の入口(合成・ファイル)。 | 台帳側の絵の出口(図・Studio・ファイルに書き出す画像)。 | none | 2-D レジストリの image と同じ (H,W) float。名前が 2 つあるのは 2 つの登録面(レジストリと型つき台帳)の歴史で、境界ごとに alias で同一視される(TYPE_TO_SORT['image2d'] = 'image')。値の契約の差: image は [0,1]、image2d は値域を持たない(実測値の画像)ので、改名でまとめると契約が崩れる。直さない(揺れとして記録)。 | backends_typed.TYPE_TO_SORT、api._RANGE_CONTRACT_SORTS = {image, color}。 |
| `images` | ok | 20 | 43 | 多フレームの取り込み(同じ視点の束)。 |  | none | 同じ視点の画像の束 (N,H,W)。産 19 / 受 37。 | tools/gen_op_facets.py ACQUIRABLE['images'](多フレームの取り込み)。 |
| `indices` | ok | 10 | 4 |  |  | none | 整数の添字。labels との往復、select_points、この版で indices_to_positions が出口に加わった。 | reprconv.indices_to_labels。 |
| `jones` | b | 2 | 2 |  |  | jones_state(azimuth_deg, ellipticity_deg, amplitude) -> jones を足した。stokes_from_jones の符号の約束に合わせ、stokes_analyze で方位角と楕円率が戻る(実測 10 度 / -15 度が 1e-15 で戻る)。 | Jones ベクトル(長さ 2 の複素 (Ex, Ey))を作れるのは jones_apply だけで、その jones_apply 自身が jones を入力に取る —— 最初の 1 本を作る op が無く、入口から届かなかった(jones_element が作るのは 2x2 の行列 = cimage で、ベクトルではない)。 | optics.jones_apply / jones_element / stokes_from_jones の docstring を読み、grep 'jones' を op 名で引いた。opsoptics のコメント『jones — 長さ 2 固定の complex 1-D』。 |
| `keypoints` | a | 25 | 28 |  |  | keypoints_rowcol_to_uv / keypoints_uv_to_rowcol を足した(向きを op 名に書いた列の入れ替え)。dlt_pose の t が真値に戻ることを門にした。 | 像面の (N,2)。points と別型にした理由は TYPE_TO_SORT のコメント(shape[1] == 3 の契約)。ただし中身に軸の約束が 2 つ同居している: calib.project_3d_point などは (row, col)、project_points / dlt_pose / pnp_ransac は (u, v) = (列, 行)。取り違えても例外は出ず、姿勢が鏡に映ったように出る(レシピの網羅 W2 の実測: t = (-0.565, 0.61, 3.21) のはずが (0.1, -0.05, 3.0))。 | backends_typed.TYPE_TO_SORT['keypoints']、reprconv の docstring『軸と単位』、docs/RECIPE_COVERAGE.md(W2)の落とした鎖 project_3d_point -> dlt_pose。 |
| `lab` | ok | 2 | 3 |  |  | none | CIELAB 画像。ΔE と lab_to_rgb が受ける。 | opsimgmetrics.NEW_SORTS['lab']。 |
| `labels` | ok | 15 | 17 |  |  | none | 整数ラベル(体積または 1-D)。産 15 / 受 17。 | TYPE_TO_SORT['labels']。 |
| `labels2d` | ok | 15 | 33 |  |  | none | 2-D のラベル画像。産 12 / 受 32。 | opssegmentation。 |
| `lightfield` | ok | 4 | 21 | ライトフィールドカメラ(格子状の視点)。 |  | none | 4-D (V,U,H,W) のライトフィールド。産 4 / 受 21。 | tools/gen_op_facets.py ACQUIRABLE['lightfield']、TYPE_TO_SORT['lightfield']。 |
| `lut` | d | 1 | 2 | color_lut() が引数(色の段)だけで作る色の対応表。 |  | none | 第 1 入力の数え方では行き止まりに見えるが、color_bar / color_grade が第 2 入力として受けている。作り方は合成が正しい。 | OP_INDEX: color_bar の in_sorts = [image2d, lut]、color_grade = [rgb, lut]。 |
| `mask` | a | 16 | 28 |  |  | none | 2-D レジストリの region(0/1 の (H,W))と同じ物を blob 族が mask と呼ぶ。境界ごとに alias で同一視される(実測 2026-09-15、gen_capabilities_index のコメント)。直さない(揺れとして記録)。 | SORT_ALIASES の mask -> region。 |
| `match` | b | 8 | 1 |  |  | match_component(match, index) -> measurement を台帳(opsreprconv)に足した。2-D レジストリの候補(進化のゲノム)は動かさないため、レジストリには足していない(tests/test_wave0.py が match の候補数を固定している)。 | 2-D レジストリの 1-D 結果ベクトル(area_center = (面積, 行, 列)、ncc_locate = (相関, 行, 列) など 8 op)を受ける op が 0(行き止まり)。HALCON では Row / Column を個別に次へ渡すのが普通の使い方。 | ops.MATCH、backends_auto の MAT = 'match' のコメント。grep 'match' を op 名・in_sort で引いた。 |
| `matrix` | ok | 94 | 205 | 引数だけで作る行列(内部行列・変換行列・設計行列)。 |  | none | 一般の 2-D 数値行列(線形代数)。産 91 / 受 191。 | ops.MATRIX、OP_INDEX で in_sorts = [] の作り手 13。 |
| `measurehandle` | d | 3 | 4 | gen_measure_rectangle2 / gen_measure_arc が測定窓の幾何(中心・向き・長さ)から作る HALCON の測定ハンドル。 |  | none | ハンドルは引数から作るものなので入口が正しい。 | opsmeasure1d の caliper カテゴリ。 |
| `measurement` | c | 96 | 6 |  | 台帳の数 1 個(長さ・角度・誤差)。測定値そのもの。 | none | 台帳の数 1 個。産 94 / 受 6 で、測った結果そのものなので終端で正しい。 | TYPE_TO_SORT['measurement'] = 'feature'(2-D の feature と同じ席)。 |
| `mesh` | ok | 23 | 49 | メッシュファイル(STL / OBJ / OFF / PLY の読み込み)。 |  | none | 三角メッシュ (vertices, faces)。産 23 / 受 49。 | opsfileio の mesh_read_stl / mesh_read_obj / mesh_read_off。 |
| `metrics` | ok | 2 | 2 |  |  | none | 画質指標の測定記録(条件つき)。metrics_table が出口。 | opsimgmetrics.NEW_SORTS['metrics']。 |
| `metrologymodel` | d | 2 | 7 | create_metrology_model() が空のモデルを作り、add_metrology_object_* で幾何を足す HALCON の流儀。 |  | none | モデルは画像から作るのではなく設計値から組むものなので入口が正しい。 | opsmeasure1d / HALCON create_metrology_model。 |
| `normalmap` | ok | 15 | 33 |  |  | none | 法線画像 (H,W,3)。産 15 / 受 33。 | opsspecular のコメント(pointmap と同形だが別の意味)。 |
| `normals` | ok | 10 | 10 |  |  | none | 点ごとの単位法線 (N,3)。この版で frame_axis が産み手に加わった。 | TYPE_TO_SORT['normals'] = 'points'(TYPE_ALIAS_LEDGER に理由つき)。 |
| `pairs` | ok | 85 | 60 |  |  | none | (x, y) の対 (n,2)。産 85 / 受 58 の主要型。spectrum / surface_psd の対からピークの位置を読む op が無かったので pairs_peak_x(-> measurement)を足した。 | reprconv._n2(2-tuple と (n,2) の 2 形を束ねる)。 |
| `phash` | ok | 2 | 3 |  |  | none | 知覚ハッシュ / 透かしのビット列。hash_distance など 3 受け手。 | opsimgforensics。 |
| `pointmap` | b | 2 | 2 |  |  | pointmap_to_points(-> points)を足した。drop_nonpositive_z=True で depth_to_points と同じ点が同じ順に出る(実測 max/Δ/ = 1.4e-17)。 | depth_to_organized_points / dem_geocentric_grid が産む (H,W,3) を、単独で受ける op が無かった(bump_normals_fbm の第 2 入力だけ)。点群の族(消費 249)へ渡れなかった。 | range_image.depth_to_organized_points の docstring と返りを実測、match3d.depth_to_points と比較。 |
| `points` | ok | 83 | 253 | 距離センサ・3-D スキャナ(XYZ ファイルの読み込みを含む)。 |  | none | 点群 (N,3)。産 79 / 受 249。 | tools/gen_op_facets.py ACQUIRABLE['points']、opsfileio points_read_xyz。 |
| `polsweep` | ok | 4 | 6 | 偏光カメラ・検光子を回した掃引。 |  | none | 偏光の掃引 (N,H,W)。images と分けた理由は opsspecular のコメント(両方向とも黙って間違う)。 | tools/gen_op_facets.py ACQUIRABLE['polsweep']。 |
| `poly_surface` | ok | 1 | 1 |  |  | none | 多項式曲面の係数記録。出口は eval_poly_surface(評価する)が唯一の正直な出口。 | opsreprconv の docstring『残した袋小路』。 |
| `pose` | ok | 17 | 8 |  |  | none | 剛体姿勢 (R, t)。産 16 / 受 7(誤差・バンドル調整・姿勢グラフ)。この版で pose_to_matrix(-> matrix 4x4)を足し、4x4 を受ける rotation_translation_error などへ渡れるようにした。 | ops3d の pose_estimation / registration / pose_graph カテゴリ。 |
| `position` | ok | 12 | 4 |  |  | none | 3-D の 1 点 (z,y,x)。points との往復がある。positions(1-D の事象位置の列)とは別物で、名前が近いだけ。 | reprconv.position_to_points / points_to_position。 |
| `positions` | b | 1 | 1 |  |  | indices_to_positions(indices, spacing, origin) -> positions を足した(find_peaks -> indices_to_positions -> point_spectrum の鎖)。 | point_spectrum が受ける『事象の位置の列』(欠陥・到着の位置)を作る op が 0(入口なし)。signal と分けてある理由は、等間隔標本と事象位置を取り違えると例外なしに別物のスペクトルが出るため(dsp.point_spectrum の docstring)。 | grep 'positions' を op 名・in/out で引き、産み手 0。近い量は find_peaks(-> indices)と peak_subbin(-> signal)。 |
| `primitive` | ok | 33 | 9 |  |  | none | 当てはめた幾何プリミティブ(平面・球・箱)。産 33 / 受 9。 | ops3d の geometry / robust_fit。 |
| `projstack` | ok | 2 | 6 |  |  | none | CT の投影束 (view, V, U)。ct_forward_project / ellipsoid_projections が産み、FDK・反復法の再構成が受けて voxel に戻す。sinostack とは軸の順序が違うので別の型。 | OP_INDEX 産 2(ct_forward_project / ellipsoid_projections)/ 受 6(ct_adjoint_project・fdk・sirt・os_sart・tv_reconstruct・ct_dual_energy_reconstruct)。第 8 便、2026-11-04 の統合で行を足した。 |
| `qimage` | ok | 19 | 24 |  |  | none | 四元数画像(色の回転・フィルタ)。産 19 / 受 24。 | TYPE_TO_SORT['qimage']、opsquat。 |
| `region` | ok | 178 | 136 |  |  | none | 2-D レジストリの 0/1 領域。産 177 / 受 136。 | docs/ADDING_OPS.md の Sort contract。 |
| `rgb` | ok | 58 | 36 | 台帳の描画・合成(gfx2d)の色画像。 | 人が見る色の絵(gfx2d の合成結果・図)。 | none | (H,W,3) の色(符号化を特定しない 3 チャネル)。rgbimage と分けた理由は opsimgmetrics.NEW_SORTS(L* が 32.53 でなく 5.72 と静かに出る実測)。 | opsimgmetrics.NEW_SORTS['rgb']。 |
| `rgba` | ok | 11 | 7 |  | 合成した絵(ストレート α)。 | none | (H,W,4) ストレート α。rgba_premul と分けた理由は opsgfx2d の docstring。 | opsgfx2d の docstring(rgba / rgba_premul を分けた理由)。 |
| `rgba_premul` | ok | 2 | 2 |  |  | none | 乗算済み α。premultiply / unpremultiply の往復で閉じる。 | opsgfx2d の premultiply / unpremultiply / alpha_composite_premul。 |
| `rgbimage` | ok | 42 | 38 |  | 線形 RGB の絵(断面・可視化の出口、Studio で見せる)。 | none | 線形 RGB (H,W,3)。pointmap / normalmap と同形だが意味が違うので分けた(opsspecular のコメント)。 | TYPE_TO_SORT['rgbimage']。 |
| `rgbvideo` | ok | 8 | 4 |  | 展示と Studio へ渡す色動画(opsconngraph の docstring『受ける op は無い(出口)』)。 | none | (F,H,W,3) の色動画。受ける op は無く、展示と Studio へ渡す出口。 | opsconngraph の docstring『rgbvideo』。 |
| `rgbvolume` | ok | 3 | 2 |  |  | none | 色つき体積。断面・MPR の rgbimage が出口。 | opsvolcolor(vol_label_slice_rgb / vol_label_mpr_rgb が受ける)。 |
| `rle_region` | ok | 5 | 7 |  |  | none | ランレングスの 3-D 領域。産 5 / 受 7。 | ops3d rle_region。 |
| `roots` | ok | 1 | 1 |  |  | none | 多項式の解集合(順序に意味が無い)。cpoints へ流さない理由は opsreprconv の docstring。cplx_rational_field が受ける。 | opsreprconv の docstring『roots』。 |
| `rot_scale` | ok | 2 | 1 |  |  | none | 回転角と倍率の対。matrix との往復がある。 | reprconv.rot_scale_to_matrix。 |
| `scalar` | c | 93 | 195 |  | 数 1 個(index・合否・個数)。 | none | 産 89 / 受 195(引数として多く受けられる)。終端でもある。 | gen_capabilities_index の SORT_ALIASES(measurement / feature と連鎖の中では同じ『数 1 個』)。 |
| `score` | ok | 1 | 3 |  |  | none | 相関スコアの体積。score_to_position / score_to_image2d / refine_peak_newton が受ける。 | opsreprconv の score カテゴリ。 |
| `sdf` | ok | 17 | 9 |  |  | none | 符号つき距離場の体積。産 17 / 受 9。 | TYPE_TO_SORT['sdf'] = 'volume'(TYPE_ALIAS_LEDGER に理由つき)。 |
| `shapemodel` | ok | 1 | 5 |  |  | none | 形の PCA モデル。shapeset から作り、5 op が受ける。shapeset が入口なので届く。 | shapestats.shape_pca。 |
| `shapeset` | d | 2 | 3 | 対応の取れた点集合の群 (K,N,3)。いまの作り手は shape_synth_family()(合成)だけで、実データは外から来る。 |  | none | 統計的形状モデルの入力。点の対応(landmark)が前提なので、ばらばらの点群から勝手には作れない。 | shapestats.shape_synth_family / generalized_procrustes の docstring。 |
| `shift` | ok | 2 | 1 |  |  | none | 整数の 3-D 平行移動。vector との往復。 | reprconv.shift_to_vector。 |
| `signal` | ok | 164 | 308 | センサ・音声の時系列(ファイル・取り込み)。 |  | none | 1-D 配列(プロファイル・スペクトル・センサ系列)。産 161 / 受 306。 | ops.SIGNAL、ops1d の docstring(1-D データの源流 3 つ)。 |
| `simmodel` | d | 2 | 5 | simcal_model() が op の鎖とノブ(単位・範囲・雑音)の宣言から作る順モデル。 |  | none | シミュレーションの模型は設計から組むものなので入口が正しい。simcal_observe(simmodel, images)で実測と結びつく。 | simcal.simcal_model の docstring。 |
| `sinogram` | ok | 8 | 10 | CT 装置の投影データ(角度 × 検出器)。 |  | none | CT のサイノグラム(角度 × 検出器)。産 8 / 受 10。 | opstomography(radon / fbp の族)。 |
| `sinostack` | ok | 1 | 1 |  |  | none | 体積のサイノグラム束。radon_volume と fbp_volume の往復で閉じる。 | opstomography の radon_volume / fbp_volume。 |
| `sprites` | ok | 1 | 2 |  |  | none | 同形 rgba の list。tilemap_render / parallax_layers が受ける。 | opsgfx2d の docstring『sprites』。 |
| `stokes` | ok | 3 | 2 |  |  | none | Stokes ベクトル。mueller_apply / stokes_analyze が受ける。 | opsoptics / opsspecular。 |
| `sweep` | d | 2 | 3 | 掃引軸に沿って標本化した強度(白色干渉・クロマティック共焦点)。作り手は *_simulate の合成だけで、実機の分光器・z 走査の出力が入口。 |  | none | 掃引信号は計測器が出すもの。合成の作り手が入口として正しい。 | opsinterferometry のコメント『sweep — 掃引軸に沿って標本化した非負の 1-D 強度』。 |
| `synapse_table` | b | 1 | 1 |  |  | synapse_table_from_table(table, pre, post, count) -> synapse_table を足した(id が 0 以上の整数であることを確かめる)。 | graph_from_synapses が受けるのに作る op が 0(入口なし)。コネクトームは CSV で来るので table から作れるのが自然。 | grep 'synapse' を op 名で引き、作り手 0。opsfileio.table_read_csv(text -> table)はある。 |
| `table` | c | 1266 | 525 | CSV / 設定の表(table_read_csv、引数だけで作る表)。 | 報告書・測定結果の表(列名 -> 配列)。 | none | 産 1166 / 受 482。最も多い終端。dict を返す op の欄を次の op へ渡すつなぎが無かったので、この版で table_field_image2d / _signal / _matrix / _measurement を足した(vx_sobel3x3 -> vx_magnitude、swt_map -> text_candidates、flow_from_depth_motion -> ttc_from_flow、label_extent の width)。 | opsfileio table_read_csv / table_write_csv。 |
| `text` | c | 13 | 29 | ファイルの中身(CSV・OBJ・XYZ の文字列)。 | 書き出す文字列(CSV・G-code・報告)。 | none | 文字列。読み込みの入口であり書き出しの終端。 | opsfileio(*_read_* は text を受け、table_write_csv は text を返す)。 |
| `tokens` | b | 8 | 10 | LLM の活性(Q / K / V の (T, d) 行列)。外のモデルから来る。 |  | tokens_to_matrix(-> matrix)を足した。出る側は一般の行列でよい(mat_cond などが掛かる)。逆向き matrix -> tokens は軸の順を確かめられないので足さない。 | 注意機構の演算族の値。入口は外(d)で正しいが、出口が 1 つも無かった: tokens と attnmap を受ける op は全部 tokens か attnmap を返すので、表・測定値・絵のどれにも出られなかった(終端へ届かない)。 | opsllmcore の _CATALOG 10 op の出力を全部見た。tokens を matrix と分けた理由は opsllmcore の docstring(入る側で転置が黙って通る)。 |
| `transport_plan` | ok | 2 | 2 |  |  | none | 最適輸送の計画。apply_transport / transport_cost が受ける。 | opscolortransport。 |
| `vector` | ok | 7 | 10 |  |  | none | 小さな実ベクトル。shift との往復ほか。 | reprconv.vector_to_shift。 |
| `video` | ok | 40 | 61 | カメラの動画ストリーム(acquire の取り込み)。 | 動画として見せる出口(展示・Studio)。 | none | (T,H,W) の灰色動画。産 40 / 受 61。 | tools/gen_op_facets.py ACQUIRABLE['video']、opsvideostream。 |
| `volseq` | d | 5 | 10 | 4-D の体積の時系列(ライトシート顕微鏡など)。作り手は volseq_synth_* の合成で、実データは外から来る。 |  | none | 体積の時系列は装置が出すもの。合成の作り手が入口として正しい。 | opslive4d の synth カテゴリ。 |
| `volume` | ok | 23 | 17 | CT / MRI の体積取り込み。 |  | none | 2-D レジストリの 3-D float stack。台帳の voxel と同じ物(TYPE_TO_SORT['voxel'] = 'volume')。 | tools/gen_op_facets.py ACQUIRABLE['volume']。 |
| `voxel` | a | 74 | 107 |  |  | none | 2-D レジストリの volume と同じ (D,H,W) を台帳が voxel と呼ぶ。境界で alias される(TYPE_TO_SORT)。sdf / labels も同じ sort に畳まれるが、それは TYPE_ALIAS_LEDGER に理由つきで記録済み。直さない(揺れとして記録)。 | backends_typed.TYPE_TO_SORT、docs/TYPE_ALIAS_LEDGER.json。 |
| `zscan` | ok | 1 | 2 |  |  | none | z 走査の画像束(白色干渉)。csi_contrast_map / csi_height_map が受ける。 | opsinterferometry。 |
