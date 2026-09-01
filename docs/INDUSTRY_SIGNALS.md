# 業界シグナル — 展示会・アワードを op 発想の恒常的な入力にする

**初版 2026-09-01。次回更新の目安は §6。**

論文コーパス(RAD)とは別の信号として、**産業ビジョンの展示会とアワード**を定期的に
読み、op 候補に落とす手順書です。単発の調査記録ではなく、**次回も同じ手順で回せる
こと**を目的に書いてあります。

---

## 1. なぜやるか — 論文とは別の信号だから

RAD が拾うのは「学術的に新規である」と査読者が判断したものです。展示会のアワードが
拾うのは **「今まさに、産業の審査員が金を払う価値があると判断した」もの**で、判定軸が
違います。この違いは実際に効きます。

- **時間差が逆向き**。VISION Award 2021 の受賞は Prophesee の event-based sensing
  でしたが、イベントカメラの論文自体はそれ以前から大量にあります。アワードが示すのは
  「発明された」時点ではなく **「製品として成立し、産業が採用を決めた」時点**です。
  op を作る側にとっては後者のほうが有用で、**仕様が確定していて検証すべき数値が
  ある**という意味になります。
- **落ちるものが見える**。学会は失敗を発表しません。展示会は「去年あったのに今年
  消えた」が観測でき、これは論文からは取れない信号です。
- **fullseye の立ち位置と直交する**。fullseye は numpy ネイティブ・CPU 完結で、
  学習も光線追跡も持ちません。アワードの受賞技術はほとんどが**ハードウェア**か
  **学習モデル**で、そのままは移植できません。だから見るべきは受賞そのものではなく、
  **「その製品が売れるということは、こういう計算が現場で要るということだ」**という
  背後の演算です。Toshiba Teli が光沢面の欠陥検出で 2024 年の VISION Award を
  獲ったという事実は、fullseye にカメラを作れという意味ではなく、
  **鏡面反射の分離が産業的に金になる問題だ**という意味です。

先例として `visiondesign.py` の線引きがあります。Medabsy(2026 ファイナリスト)は
モンテカルロ光輸送で合成学習データを作る製品ですが、fullseye はレンダラを持てません。
そこで**「画像」ではなく「限界」**(分解能・被写界深度・周辺光量・コントラスト伝達)を
閉形式で返す側に倒しました。この文書が探すのは、常にその**閉形式で答えられる切り口**です。

---

## 2. 調査の手順(繰り返し可能な形)

### 2.1 どのイベントを、いつ、どこを見るか

| イベント | 周期 | 次回 | 見る場所 | 出典(取得確認済) |
|---|---|---|---|---|
| **VISION**(シュツットガルト) | **隔年** | 2026-10-06〜08 | Award History / ファイナリスト記事 | `messe-stuttgart.de/vision/en/fair/at-a-glance/`(「Regular cycle: every two years」) |
| VISION Award | VISION と同時 | 2026-10-07 授賞 | `.../programme/vision-award/award-history/` | 同上 |
| **inspect award**(Wiley) | 毎年、VISION 会期中に発表 | 2026 は投票 09-15 締切 | `wileyindustrynews.com/en/award/inspect-award/` | 同 |
| **Vision Systems Design Innovators Awards** | 毎年、Automate 会期中 | 2026 は 06-22 発表済 | 各社プレスリリース(後述の注意) | `vision-systems.com/factory/media-gallery/55389078/...` |
| **Edge AI and Vision Product of the Year** | 毎年 4 月発表、5 月授賞 | — | 配信元 PR(後述の注意) | `natlawreview.com/press-releases/edge-ai-and-vision-alliance-announces-2026-product-award-winners` |
| **Control**(シュツットガルト、品質保証) | **隔年に移行済** | 2027-05-11〜14(2026 は Expert Days 05-20〜21) | Fraunhofer Vision 特別展の出展一覧 | `vision.fraunhofer.de/.../control-special-show-2025.html` |
| **automatica**(ミュンヘン) | 隔年 | 2027-06-22〜25 | フォーカストピック | `automatica-munich.com/en/trade-fair/` |
| **EMVA / VDMA** | 通年 | — | 標準化ニュース、VISION 紹介ページのトレンド記述 | `emva.org/standards-technology/genicam/genicam-news/` |

VISION が隔年である以上、**この文書の主更新も隔年**になります。空き年は inspect
award と VSD が埋めます(どちらも毎年)。

### 2.2 実務上の落とし穴(実測)

今回の調査で実際にぶつかったもので、次回も同じように詰まるはずのものです。

- **`edge-ai-vision.com` は WebFetch に一貫して 403 を返す**。公式の受賞紹介ページは
  読めないので、配信元 PR(natlawreview / EIN Presswire / PR Newswire)を経由します。
- **VSD Innovators Awards の公式一覧はスライドショーで、本文に受賞者名が無い**。
  fetch しても取れません。**受賞各社のプレスリリースを個別に当たる**しかなく、
  結果として網羅リストは作れません。この文書の VSD 欄が歯抜けなのはそのためです。
- **`imveurope.com` の一部記事は登録の壁**があり、見出ししか読めないことがあります。
- **`automate.org` / `excelitas.com` も 403** を返しました。
- **Fraunhofer Vision の Control 特別展ページが、実は最良の一次情報**でした。
  アワードは 1 年に数件しか出ませんが、この特別展は**その年に産業が展示した計測
  モダリティが 10 件以上並ぶ**ので、密度が段違いです。次回はここから読むこと。

### 2.3 fullseye 側の現状をどう測るか(推測で「無い」と書かない)

op の在庫確認は **3 つの表面を全部見ないと間違えます**。今回、実際に間違えかけました。

```powershell
# 表面 1: 型付きカタログ + 進化レジストリ(= 1194 名、実測 2026-09-01)
PYTHONUTF8=1 py -3.11 -c "
import sys; sys.path.insert(0,'tools')
from chain_fuzz import catalog
import ops
names = {n for n,_,_,_,_ in catalog()} | {o.name for o in ops.REGISTRY}
print(len(names))
"

# 表面 2: api.py の公開名(= 463 名、実測)
PYTHONUTF8=1 py -3.11 -c "import api; print(len([x for x in dir(api) if not x.startswith('_')]))"

# 表面 3: ソース全体の def 静的走査(= 7137 名。実装済みだが未登録のものを拾う)
grep -rhoE "^def [a-zA-Z_][a-zA-Z0-9_]*" --include="*.py" . | sed 's/^def //' | sort -u
```

**全モジュールを `importlib` で総当たりするのは失敗します**(実測: 5 分でタイムアウト。
MuJoCo デモを持つモジュールが import 時に重い処理を走らせるため)。静的な `def` 走査を
使うこと。

そして **キーワードは接頭辞で当てる**。今回 `hyperspect` と `spectral` で引いて
「ハイパースペクトルは 0 件」と結論しかけましたが、実体は **`spec_` 接頭辞の 14 op**
(`specops.py`)でした。同じ罠が `lf_`(ライトフィールド 17 関数)、`tac_`(触覚 5)、
`ev_`(例示グループ)、`dtof_`/`tcspc_`/`spad_` にもあります。**1 つの語で 0 件だった
ら、必ず別の綴りと接頭辞で 2 回目を引くこと。**

さらに、名前があっても**中身が方針に合っているとは限りません**。`cfa_to_rgb` は
実在する Bayer デモザイク op ですが、実装は `cv2.cvtColor` の uint8 経路
(`backends_color.py:72`)で、numpy ネイティブでも float でもありません。
**「有る/無い」の 2 値でなく「有るが規約外」を第 3 の状態として記録すること。**

---

## 3. ギャップ表(2026-09-01 実測)

fullseye 側の欄はすべて上記 3 表面の実測です。**登録状態を 3 段で区別**します:
`IN-CATALOG`(型付きカタログ or 進化レジストリに登録済)/ `api-only`(api.py にはあるが
カタログ未登録)/ `module-only`(実装はあるがどちらにも未登録)。

| # | 技術(出典イベント) | fullseye の現状(実測) | ギャップ | 実装可能性(numpy+scipy で閉形式検証できるか) | 優先度 |
|---|---|---|---|---|---|
| 1 | **光沢面・鏡面の欠陥検出 / BRDF**<br>Toshiba Teli OneShotBRDF(**VISION Award 2024 受賞**)/ AIT PHOTODEX(2026 ファイナリスト)/ Opto solino(Control 2025)/ photonicSENS apiCAM(2026、鏡面・透明面) | `photometric_stereo`(IN-CATALOG)、`uncalibrated_photometric_stereo`(module-only)。**ただし `photometric.py` の docstring が自ら「スペキュラは線形性を破る」と明記**。`brdf`/`albedo`/`specular`/`deflect` は**3 表面すべてで 0 件** | 鏡面反射の**分離**と、鏡面下での形状復元が丸ごと無い。Lambertian 前提の外に出る手段がない | **できる。**(a) 二色性反射モデルによる拡散/鏡面分離は色空間の閉形式射影で、合成画像(既知アルベド + 既知ハイライト)から厳密に戻せる。(b) 頑健フォトメトリックステレオ(光源ごとの median / RANSAC)は既存 `photometric_stereo` の最小二乗を差し替えるだけで、**影を人工的に入れた合成データで「素の版が壊れ、頑健版が耐える」ことを数値で示せる**。(c) 偏光による分離は `stokes_analyze` が既にある | **最高**。5 年分のイベントで最も反復して現れた主題で、しかも fullseye が**すでに 8 割の部品を持っている**(photometric + optics + jones/stokes) |
| 2 | **モーション増幅**<br>RDI Iris MX(**VSD 2025 Silver**)+ FASTEC HSi(**同年 Bronze**)— 同一アルゴリズム族で同年 2 件 | `magnif`/`eulerian`/`riesz` は **0 件**。`tf_steerable_filter` と `optical_flow_*` は有るが増幅ではない | 微小変位を可視化・定量化する経路が無い | **できる。** 位相ベース増幅は「複素ステアラブル分解 → 時間帯域通過 → 位相を α 倍 → 再合成」で、依存は FFT のみ。**閉形式の真値がある**: 既知振幅 d の正弦的サブピクセル変位を合成し、増幅後の変位が α·d になることを直接測れる | **高**。同年に 2 社が受賞 = 産業需要が確定。かつ検証が厳密 |
| 3 | **コヒーレント測距 / レンジ-ドップラー**<br>Lidwave Odem(2026 ファイナリスト、**画素ごとの速度**)/ Ambarella 4D radar(Edge AI 2024)/ Balluff Radarimager(inspect 2024)/ TI AWRL6844(2026) | `lidar_scan`/`pseudo_lidar` は有る(MuJoCo レイキャストの**幾何**)。`doppler`/`radar`/`beamform`/`delay_and_sum` は **0 件** | 距離しか出せない。**速度が同時に取れない**。FMCW の信号処理層が無い | **できる。** FMCW のビート信号 → 2D FFT(高速時間軸=距離、低速時間軸=速度)は教科書的な閉形式。**既知の距離 R と速度 v からビート信号を合成し、2D FFT がそのビンを返すことを厳密に検証できる**。遅延和ビームフォーミングも同様(既知到来角 → ピーク角) | **高**。fullseye の Physical AI ミッションに直結し、既存 `lidar_*` の**上の層**として素直に載る |
| 4 | **白色光干渉 / クロマティック共焦点**<br>Mitutoyo WLI(inspect 2025)/ Micro-Epsilon confocalDT IFD2415(inspect 2023、**25kHz・8nm**)/ twip CONSIGNO(Control 2025)/ Evident Lext OLS5500(2026 ノミネート) | `fringe`(`decode_fringe`/`synthesize_fringes`)= **位相シフト干渉法**。`interferomet`/`wli`/`chromatic_conf`/**コヒーレンス包絡線検出は 0 件**。`xsp_hilbert_env` は 1D 信号の包絡線で、走査軸には掛かっていない | 位相ではなく**コヒーレンス包絡線のピーク**で高さを出す経路が無い。これは粗面・段差で位相法が 2π 不定性に負ける場面の正攻法 | **できる。** z 走査信号は「ガウス包絡線 × 搬送波余弦」で、Hilbert 変換の包絡線ピークが表面位置。**既知 z₀ で合成した干渉信号からピークが z₀ を返すことが閉形式の真値**。重心法・多項式当てはめの差も同じ土俵で測れる | **中〜高**。既存 `fringe` / `phase_unwrap` と型で繋がり、`xsp_hilbert_env` の資産が使える |
| 5 | **ハイパースペクトル**<br>**EMVA と VDMA が揃って VISION 2026 のトレンド 3 本柱に明記**(「embedded vision, hyperspectral imaging and deep learning」)/ EVK Alpha G100(inspect 2023)/ DIVE VEpioneer(Control 2025)/ HAIP Blackindustry SWIR | **`spec_` 接頭辞で 14 op 実在**(`specops.py`): `spec_unmix` / `spec_endmembers_ppi` / `spec_angle_mapper` / `spec_mnf` / `spec_pca` / `spec_continuum_removal` / `spec_band_ratio` / `spec_index` / `spec_pansharpen` / `spec_fuse` ほか。**ただし全て `api-only`(型付きカタログ未登録)** | **能力ギャップではなく配線ギャップ**。連鎖ファザーからも進化探索からも Studio のブラウザからも見えない | 実装は既にある。要るのはカタログ登録(+ example + per-op docs + Studio help の 4 点セット) | **中**。協会が名指しする最大トレンドなのに探索から不可視、という状態は歪。ただし**新規性は無く配線作業**なので、1〜4 の後 |
| 6 | **CAD への欠陥登録 / デジタルツイン**<br>Kitov.ai CAD2SCAN(**VISION Award 2022 受賞**)/ AIT PHOTODEX(2026、欠陥を CAD ツインへ登録) | `align_cad_to_scan`(`pipeline3d.py`、FPFH で mesh↔点群、module-only)、ICP 3 種、`ppf` 一式は有る | **姿勢は出せるが、そこで終わり**。「2D 画像上で見つけた欠陥を CAD 面上のどの座標か」に落とす逆写像が無い | **できる。** カメラ内部・外部パラメータと mesh があれば、画素 → 光線 → 三角形交差 → 重心座標、は完全な閉形式。既存 `camera` / `mesh` / `render3d` の部品で組める。**既知の面上の点を投影し、投影像から逆に引いて同じ三角形・同じ重心座標が返ることが厳密な真値** | **中**。VISION Award 受賞主題が 2 回(2022, 2026 候補)出ている。既存 3D 資産の**出口**に当たる |
| 7 | **HDR / 露出ブラケット合成**<br>CSEM LINLOG(VISION Award 2000)/ IDS(2024 トレンド記事で「HDR」を明示) | `tonemap_aces` / `tonemap_reinhard`(IN-CATALOG)、`hdr_scene` / `shade_hdr`。**`debevec`/`bracket`/`exposure_` は 0 件** | **後半(トーンマッピング)だけあって前半(合成)が無い**。複数露出 → 放射輝度の復元経路が欠落 | **できる。** 既知の放射輝度マップと既知露光時間から N 枚を合成し、重み付き合成がスケール倍を除いて元を返すことを厳密に測れる | **中**。穴が明確で工数が小さい |
| 8 | **RAW / ISP 前段**<br>Visionary.ai AI ISP(**Edge AI 2026 Best Camera or Sensor**、RAW ドメイン "Bayer to Bayer") | `cfa_to_rgb` は**実在するが `cv2.cvtColor` の uint8 経路**(`backends_color.py:72`)。`trans_from_rgb` の Lab/XYZ も同じく cv2 uint8。黒レベル・ホワイトバランス・カラー行列は 0 件 | **「有るが規約外」**。numpy ネイティブでも float でもないので、精度を要求する経路で使えない | できる(双線形・Malvar とも閉形式で、定数画像・線形ランプでは厳密復元が真値)。ただし **cv2 依存 op の置き換えは方針判断を伴う**ので、単独では動かさない | **低**。穴ではなく品質改善。他の色 op の float 化とまとめて扱うべき |
| 9 | **イベントベース**<br>Prophesee Metavision(**VISION Award 2021 受賞**)/ LUCID Triton2 EVS(**VSD 2025 Gold** + Control 2025) | `events.py` 一式(`simulate_events`/`event_image`/`event_rate_map`/`contrast_maximization`、api-only)+ `event_camera.py`(MuJoCo デモ) | **ほぼ埋まっている。** 残るのは `spec_` と同じ配線の話(api-only) | — | **低**(§5 参照。既に着手済み扱い) |
| 10 | **ライトフィールド / 光子計数** | `lf_*` 17 関数(`lightfield.py`、module-only)/ `photon_*`・`spad_*`・`tcspc_*`・`dtof_*` 13 関数(`photoncount.py`、module-only) | 別作業者が実装中 | — | **対象外**(§5) |

### fullseye に完全に無い分野(3 表面すべてで 0 件だったもの)

上表のうち、キーワードが**一切引っかからなかった**のはこの 4 つです。他は
「有るが規約外」か「有るが未登録」でした。

1. **鏡面反射の分離 / BRDF**(`brdf` `albedo` `specular` `deflect` = 0)
2. **モーション増幅**(`magnif` `eulerian` `riesz` = 0)
3. **ドップラー / レーダ / ビームフォーミング**(`doppler` `radar` `beamform` `delay_and_sum` = 0)
4. **コヒーレンス走査干渉 / クロマティック共焦点**(`interferomet` `wli` `chromatic_conf` = 0)

**この 4 つが、業界が毎年賞を出しているのに fullseye が一語も持っていない領域です。**

---

## 4. op 候補(上位 5 件)

このリポジトリの規律は **「閉形式の真値で検証できない op は作らない」**です。各案に
必ず検証方法を添えます。添えられないものは §5 へ落としています。

### 候補 1 — 拡散/鏡面分離と頑健フォトメトリックステレオ(最優先)

```
specular_diffuse_split(image_rgb)      -> (diffuse, specular)
photometric_stereo_robust(images, lights, method="median"|"ransac") -> (normals, albedo, inlier_mask)
```

- **根拠**: VISION Award 2024 の受賞主題そのもの。2026 ファイナリスト 5 件中 2 件
  (AIT PHOTODEX / photonicSENS)も同じ問題を別の手段で解いている。
- **閉形式の真値**:
  (a) 既知アルベドの Lambertian 画像に**既知の鏡面成分を加算**して合成し、分離後の
  拡散成分が元と機械精度で一致すること。二色性反射モデルでは鏡面成分が光源色方向の
  1 次元部分空間に載るので、この射影は厳密です。
  (b) 頑健版は **N 枚のうち k 枚を影(N·L<0)で潰した合成データ**を作り、素の
  `photometric_stereo` の法線誤差が発散する一方で `median`/`ransac` 版が真の法線を
  保つことを角度誤差で測る。**「既存版が壊れる」ことも同時に示すのが要点**で、
  そうしないと頑健版を足す理由が測定に現れません。
- **既存資産**: `photometric.py`(Frankot-Chellappa 積分まで完備)、`stokes_analyze`、
  `render_lambertian`(順方向合成でループを閉じられる)。

### 候補 2 — 位相ベースのモーション増幅

```
motion_magnify(frames, alpha, f_lo, f_hi, fps) -> frames_magnified
phase_motion_measure(frames, f_lo, f_hi, fps)  -> displacement_map
```

- **根拠**: VSD 2025 で **同一アルゴリズム族に 2 社が受賞**(RDI Silver / FASTEC Bronze)。
- **閉形式の真値**: 既知の正弦パターンを既知振幅 d(サブピクセル)・既知周波数 f で
  平行移動させた合成動画を作る。増幅後の変位が **α·d** になること、帯域外の周波数
  成分が増幅されないこと(f を通過帯域の外に置いた対照)、の 2 点が厳密に測れます。
- **注意**: 増幅は α を上げるとノイズも同率で増えるので、**SNR の劣化を同時に報告
  しない実装は嘘**になります。返り値に増幅後の推定 SNR を含めること。

### 候補 3 — FMCW レンジ-ドップラー処理

```
fmcw_beat_simulate(ranges, velocities, ...) -> beat_cube
range_doppler_map(beat_cube, ...)           -> (range_axis, doppler_axis, map)
beamform_delay_sum(array_signals, geometry) -> angle_spectrum
```

- **根拠**: Lidwave Odem(2026 ファイナリスト、画素ごとの速度)。加えてレーダ側でも
  Ambarella(Edge AI 2024)、Balluff Radarimager(inspect 2024)、TI AWRL6844(2026)と
  4 年連続で別のイベントに出ている。
- **閉形式の真値**: チャープの傾き S、波長 λ が決まれば、距離 R のビート周波数は
  `2SR/c`、速度 v の位相進みは `4πv T_c/λ` と**解析的に決まります**。既知の (R, v) で
  合成したビート立方体に 2D FFT を掛け、ピークが**その距離ビン・速度ビンに立つ**ことを
  厳密に検証できます。ビン幅・最大非曖昧速度も閉形式なので、`visiondesign.py` と
  同じ「限界を返す」設計(`fmcw_design`)が自然に付きます。
- **なぜ fullseye に合うか**: 既存の `lidar_scan` は幾何(レイキャスト)だけで、
  **信号処理層が空**です。ここは自然な上積みで、既存 op と競合しません。

### 候補 4 — コヒーレンス走査干渉の包絡線検出

```
csi_envelope(scan_signal, axis)  -> (envelope, peak_index)
csi_height_map(scan_stack)       -> height_map
chromatic_confocal_peak(spectra) -> height
```

- **根拠**: inspect award で 2 年(2023 Micro-Epsilon 共焦点 / 2025 Mitutoyo WLI)、
  Control 2025 特別展でも 2 件。産業計測の定番。
- **閉形式の真値**: 走査信号は `exp(-(z-z₀)²/2σ²)·cos(4πz/λ)` の形なので、
  **既知 z₀ で合成した信号から包絡線ピークが z₀ を返す**ことが直接の真値。σ(コヒーレンス
  長)を変えたときの位置推定分散、重心法 vs 放物線当てはめの差も同じ枠で測れます。
- **既存資産**: `xsp_hilbert_env`(1D 包絡線)、`fringe`、`phase_unwrap`。
  **位相シフト法(既存)とコヒーレンス法(新規)を同じ合成表面で突き合わせる**テストが、
  2π 不定性の扱いを検証する唯一の構成になります(光学 op の Jones↔Mueller 突き合わせと
  同じ発想)。

### 候補 5 — 欠陥の CAD 面への逆写像

```
pixel_to_surface(uv, camera, mesh)          -> (face_id, barycentric, point3d)
defect_to_cad(defect_regions, camera, mesh) -> table(face_id, area_mm2, point3d)
```

- **根拠**: Kitov.ai CAD2SCAN が **VISION Award 2022 の受賞**、AIT PHOTODEX が 2026
  ファイナリストで同じ「欠陥を CAD ツインへ登録する」機能を挙げている。
- **閉形式の真値**: mesh 面上の既知の点を既知カメラで投影し、その画素から逆に引いて
  **同じ face_id と同じ重心座標(機械精度)** が返ること。往復可逆性が厳密な真値に
  なります。面積は既知の平面パッチで解析値と一致すること。
- **既存資産**: `align_cad_to_scan`、`camera`/`calib`、`mesh`、`render3d`。
  **既存の 3D スタックの出口**にあたり、新しい依存を増やしません。

---

## 5. 却下したもの(同じ検討を繰り返さないための記録)

**ここが本節の主目的です。**「見たが、やらないと決めた」を残さないと、次回また同じ
往復をします。

| 却下したもの | 出典 | 却下の理由 |
|---|---|---|
| **カメラ伝送インターフェース**(GigE Vision 3.0 / CoaXPress 3.0 / 25Gbps / RDMA / CameraLink HS 1.3 / USB3 Vision) | EMVA GenICam ニュース、IVSM Spring 2026、Baumer(inspect 2025 Vision 1 位)、LUCID Triton10 | **op ではなく転送層**。fullseye は numpy 配列を受け取った時点から始まる。ここに手を出すと守備範囲が壊れる。**恒久的に対象外**(次回も検討しない) |
| **GenICam / EMVA 1288(ISO 24942)対応** | EMVA 標準ページ | EMVA 1288 は**カメラの測定規格**で、対象はハードウェアの特性評価。ソフトウェア op にはならない。ただし **1288 が定義するノイズモデル(量子効率・読み出しノイズ・DSNU/PRNU)は `aug_*` 族の裏付けとして参照価値がある** — 実装ではなく文献参照として `REFERENCES.md` 行き |
| **エッジ AI プロセッサ / NPU / SoC**(Intel Core Ultra、Qualcomm Snapdragon、SiMa.ai Modalix、Expedera NPU IP、ADLINK Jetson) | Edge AI Product of the Year 2024-2026 で毎年複数 | **ハードウェア**。fullseye は CPU + numpy が方針。GPU 化は既に `accel` 系という別の計画(`GPU_ACCEL_PLAN.md`)があり、そちらの土俵 |
| **学習ベースの欠陥分類 / 異常検知**(Maddox AI、DENKweit Denk Match AI、Zebra NS42、MVTec の DL) | inspect award AI カテゴリ(2025・2026 に多数)、VDMA/EMVA のトレンド 3 本柱の 1 つ | **重い依存(torch 等)を必須にしない**という中核方針に反する。加えて**閉形式の真値が無い**ので、このリポジトリの検証規律を通せない。代わりに閉形式で答えられる切り口を採る: 学習の**入力を作る**側(合成欠陥 `defect_*` 4 種 + `aug_*` 族は既に有る)と、**限界を返す**側(`visiondesign.py`) |
| **生成 AI によるロボットプログラミング / VLM エージェント** | automatica 2025、Camio(Edge AI 2025)、Nota Vision Agent(2026) | 同上。加えて視覚 op ですらない |
| **モンテカルロ光輸送レンダラ**(Medabsy Virtual Machine Vision Platform) | VISION Award 2026 ファイナリスト | **正直に「できない」**。パストレーシングは fullseye の依存方針と計算方針の両方に反する。**先例どおり「画像でなく限界」に倒す**線引きを既に `visiondesign.py` で採用済みで、そこから先には進まない |
| **ドメインランダム化スイープ / ピクセル完全アノテーション生成** | Medabsy(同上) | ランダム化そのものは `aug_*` 族と `defect_*`(`defect_blob`/`crack`/`pits`/`scratch`)で**部品が揃っている**。足りないのは「スイープを回す枠」だが、それは op ではなく**ワークフロー**であり、`docs/EVOLUTION_ENVIRONMENT.md` の枠組みと重複する。op としては足さない |
| **超音波 / レーダによる撮像そのもの**(Sonair Adar、Balluff Radarimager) | inspect award 2024・2026 | モダリティ自体は対象外(センサが無い)。**ただし信号処理(遅延和ビームフォーミング)だけは候補 3 に含めた** — こちらは閉形式で検証でき、既存 `lidar_*` と型で繋がるため |
| **X 線 CT / 微焦点 X 線**(Viscom X9000、Hexagon VG-Trainer) | Control 2025、inspect 2025 AI | **xct プロジェクトと重複**。`NEXT_OPS_PLAN_2026-08-31.md` §D-9 で既に「tomography 系は xct と重複」として優先度低に置いており、その判断を踏襲 |
| **サーモグラフィ**(edevis、InfraTec E-LIT) | Control 2025 特別展 | 熱流の逆問題は熱伝導方程式の逆解きで、**閉形式の真値を作るには 1D 半無限体などの解析解に限定される**。可能性はあるが、産業での反復度が上の 4 件より低い。**保留**(却下ではなく、次回再評価) |
| **SWIR / NIR / 冷却センサ**(Balluff、Allied Vision Alecs、Teledyne Lince5M、HAIP、Midwest Optical) | inspect 2026 に多数、VSD 2026 Platinum | **波長帯はハードウェアの属性**で、画像が numpy 配列になった時点では op の違いにならない。band 演算は `spec_band_ratio` / `spec_index` で既にカバー済み。**新規 op なし** |
| **照明技術**(iCore iPulse、Baumer IXG の一体化照明、VISION Award 2016 の VISA 法) | inspect 2025 SME、VISION Award 履歴 | ハードウェア。**ただし「多灯を切り替えて撮る」ことの計算側は候補 1(頑健フォトメトリックステレオ)が受け止める** |
| **Airy3D DepthIQ(TDM 回折マスク単眼深度)** | Edge AI 2025 Best Camera or Sensor | 技術内容の**一次確認ができなかった**(公式が 403)。**確認できていないものを根拠に op を作らない。** 次回、一次情報が取れたら再評価 |

---

## 6. 次回の更新時期

| 時期 | 何を見るか |
|---|---|
| **2026-10 直後** | VISION 2026(10-06〜08)の **VISION Award 受賞者**(10-07 授賞)と **inspect award 2026 受賞者**(初日発表)。§3 の候補 1 が今回の予想どおり評価されるかの答え合わせになる |
| **2027-05 直後** | **Control 2027**(05-11〜14)の Fraunhofer Vision 特別展。§2.2 のとおり、ここが単位面積あたり最も密度の高い一次情報 |
| **2027-06 直後** | **automatica 2027**(06-22〜25)。「Physical AI」が主要トピックに挙がっており、fullseye のミッションと最も近い |
| **毎年 4〜6 月** | Edge AI Product of the Year(4 月発表)と VSD Innovators Awards(Automate 会期)。ただし §2.2 のとおり取得性が悪く、費用対効果は低い |
| **2028-10 頃(推定)** | 次の VISION。**隔年サイクルは確認済だが、2028 の日程は組織側が未公表で確認できていない**。時期が近づいたら `messe-stuttgart.de/vision/en/fair/at-a-glance/` で確認すること |

**更新のときの作法**: §3 のギャップ表は毎回**測り直す**こと(op は増えるので、
前回「無し」だったものが埋まっている)。§5 の却下表は**消さずに追記**する — 却下理由が
無効になった場合(例: 依存方針が変わった、一次情報が取れた)は、行を消さずに
「再評価 <日付>」を追記する形にすること。

---

## 7. 今回の調査で確認できなかったもの(honest disclosure)

次回の出発点にするため、**取れなかったものを明示**します。

- **VISION Award 2026 と inspect award 2026 の受賞者** — どちらも本文書の作成時点で
  未発表(2026-10 の VISION 会期中)。本文書はファイナリスト/ノミネートに基づく。
- **VISION 2028 の日程** — 隔年サイクルは組織の公式ページで確認済だが、2028 の
  具体的な日程を載せたページは見つからなかった。10 月というのは**推定であって事実
  ではない**。
- **VSD Innovators Awards の完全な受賞者一覧**(2024/2025/2026 いずれも) — 公式が
  スライドショーで取得不能。各社プレスリリースで裏が取れた分のみを本文書に採用した。
  **VSD 2025 の Platinum は特定できなかった。**
- **Edge AI and Vision Alliance の公式受賞紹介ページ全般** — 403。技術詳細は配信元
  PR に載っている範囲まで。**Airy3D DepthIQ の TDM 方式は一次確認できていない**
  (§5 で却下理由に明記)。
- **Control Expert Days 2026 の詳細プログラム** — 検索スニペットには AI・センサ
  フュージョン等が現れるが、`control-messe.de` の一次ページには載っていなかった。
  採用しなかった。
- **EMVA Business Conference 2026 のセッション題目** — 公式サイトが総論のみ。
- **inspect award 2022 以前** — 未調査。

---

## 関連

- `docs/NEXT_OPS_PLAN_2026-08-31.md` — 内部由来(2D→3D / GPU / 数学 / 光学)の op 計画。
  **本文書は外部由来**で、両者は入力が違う。§G(光学)の「次の波の候補」と本文書の
  候補 4 は隣接するので、着手時に突き合わせること
- `visiondesign.py` — 「レンダラを持てないなら限界を返す」という線引きの先例
- `docs/EVOLUTION_ENVIRONMENT.md` — 昇格ゲート。ここで挙げた候補も、実装後は
  同じ counterfactual utility の判定を通る
- `docs/CHAIN_FUZZ.md` — 新 op family を足すときの登録手順(型語彙・`OP_ARG_BUILDERS`)
