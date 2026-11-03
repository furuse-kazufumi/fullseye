# 評価の枠組み共通層 P0-A 実施報告

## 結果

`fullseye/evaluation/` を、既存の `examplefig`、`fullseye.validation_kit`、`fullseye.golden`、`fullseye.fixture`、`imgmetrics`、`metrics3d` の上に追加した。共有層を新規設計で書き起こさず、重複候補を役割別に比較して単一の基底を選び、不足する契約だけを薄いアダプターとして加えた。

第一波15本はすべて移行済みである。移行前後を別worktreeで実行し、`figures.json` の数値・shape・caption、全PNGの復号後配列、stdoutの`[PASS]`行を比較した。15本すべて一致し、最終の対測定では実行時間もすべて移行後が移行前以下だった。40分を超えたPoCとスキップはない。

## 重複候補の比較と基底の選定

基準コミット `c9f46c26f64ea2cf2ed88fd88903158a79dbc891` をASTで再監査した。調査報告時の `gate/check` 116本・117関数に対し、基準コミットでは117本・118関数だった。後から追加されたPoCを含むためである。truth生成28関数、誤差・採点103関数、ローカル`figures` 34関数、動画保存82呼出しも含めた全件の候補×基準表は [P0A_EVALUATION_CANDIDATES.md](P0A_EVALUATION_CANDIDATES.md) に収録した。

| 役割 | 比較した候補 | 選んだ単一の基底 | 選定理由 | 他候補に残した差分 |
|---|---|---|---|---|
| 結果・合否 | 118個のローカル`gate/check`、`validation_kit.aggregate` | `poc_simcal_telecentric.gate` | measured、expected、detailを一つの記録に保持し、既存の表示・終了コードを変えずにアダプター化できる | PoC固有の文言、relation、既定値は呼出し側に残す |
| truth | 28個のtruth生成関数 | `poc_pv_thermal_survey.ground_truth` | 複数fieldを一つに集める形が最も`TruthBundle`に近く、図と判定の双方で実使用されている | 物理式、RAW/ISP段階、座標系、mask意味はPoCから明示して渡す |
| metrics | 103個のローカル採点、`imgmetrics`、`metrics3d`、`validation_kit.aggregate` | 2-Dは`imgmetrics.rmse`、集約は`validation_kit.aggregate`、3-Dは`metrics3d`の3関数 | 共有API、既存試験、使用実績があり、同じ計算を複製せず呼び出せる | mask、NaN、weights、unit、reduction、emptyをアダプター引数として補う |
| artifact | 34個のローカル`figures`、`examplefig`の保存・manifest | `examplefig` | 1,966件の保存実績があり、file、caption、shapeの正本になっている | 図の構成と展示順はPoCに残す |
| video | 82個の保存呼出し、`examplefig.save_video` | `examplefig.save_video` | MP4/GIF、fps、frame数を既に一つのmanifestへ記録する | capture/playback fps、hold、stride、scale、interpolationを`VideoSpec`で明示する |
| 第2段manifest | `figures.json`、`golden.py`、`fixture.py` | `figures.json` | 既存公開形式を壊さず、数値・truth・gate・seed・動画hashを外側に追加できる | goldenの固定・復元は既存`golden`/`fixture`をそのまま使う |

同点の場合は、契約が完全であること、既存テストがあること、複数箇所で使われていること、同じ入力で速いこと、読みやすいことの順で判断した。複数候補の切り貼りはしていない。

## 共通層

| ファイル | 行数 | 基底と責務 |
|---|---:|---|
| `fullseye/evaluation/__init__.py` | 36 | 公開名の集約 |
| `fullseye/evaluation/result.py` | 178 | telecentric PoCのgate記録を基底にした`GateResult`、`CaseResult`、既存表示互換adapter |
| `fullseye/evaluation/truth.py` | 140 | PV thermalの複数field truthを基底に、unit、frame、mask、processing stageを検証 |
| `fullseye/evaluation/metrics.py` | 363 | `imgmetrics`、`validation_kit`、`metrics3d`を呼ぶmask/NaN/empty明示adapter |
| `fullseye/evaluation/artifacts.py` | 70 | `examplefig` manifestから`ArtifactSpec`を復元 |
| `fullseye/evaluation/video.py` | 111 | `examplefig.save_video`を呼ぶ`VideoSpec` |
| `fullseye/evaluation/manifest.py` | 241 | 数値、array要約、truth、gate、figure、動画先頭・中央・末尾hash、seedの第2段manifest |
| **合計** | **1,139** | |

既存の`examplefig`、`validation_kit`、`golden`、`fixture`の公開APIは変更していない。

## 15本のparity

表の「完全一致」は、`figures.json`の数値・shape・caption、PNGの`np.array_equal`、stdoutの`[PASS]`行、終了コード0をすべて満たすことを示す。時間は同じWindows環境で図・動画保存を有効にした壁時計秒である。

| # | PoC | 移行内容 | parity | before秒 | after秒 | 判定 |
|---:|---|---|---|---:|---:|---|
| 1 | `poc_interferometry_step` | `VideoSpec`経由の動画保存 | 完全一致 | 65.97 | 45.62 | after ≤ before |
| 2 | `poc_polarization_specular` | 共通RMSE | 完全一致 | 19.90 | 12.33 | after ≤ before |
| 3 | `poc_photoelasticity` | `VideoSpec`経由の動画保存 | 完全一致 | 35.35 | 21.77 | after ≤ before |
| 4 | `poc_phase_measuring_deflectometry` | `GateAdapter` | 完全一致 | 90.34 | 69.15 | after ≤ before |
| 5 | `poc_grating_interferometry` | `GateAdapter` | 完全一致 | 41.14 | 32.39 | after ≤ before |
| 6 | `poc_thermography_ndt` | `VideoSpec`経由の動画保存 | 完全一致 | 25.54 | 22.14 | after ≤ before |
| 7 | `poc_thermal_radiometry` | `TruthBundle`と第2段manifest | 完全一致 | 59.41 | 50.52 | after ≤ before |
| 8 | `poc_pv_thermal_survey` | `TruthBundle`と第2段manifest | 完全一致 | 28.91 | 25.50 | after ≤ before |
| 9 | `poc_lens_tolerancing` | `GateAdapter`と`VideoSpec` | 完全一致 | 102.01 | 92.09 | after ≤ before |
| 10 | `poc_simcal_telecentric` | `GateAdapter` | 完全一致 | 157.26 | 120.01 | after ≤ before |
| 11 | `poc_simcal_pixel_shift` | `GateAdapter` | 完全一致 | 194.30 | 164.69 | after ≤ before |
| 12 | `poc_cad_scan_deviation` | `VideoSpec`経由の動画保存 | 完全一致 | 103.44 | 101.71 | after ≤ before |
| 13 | `poc_lidar_terrain_change` | `VideoSpec`経由の動画保存 | 完全一致 | 119.61 | 111.44 | after ≤ before |
| 14 | `poc_focus_stacking` | 共通RMSEと`VideoSpec` | 完全一致 | 29.49 | 28.36 | after ≤ before |
| 15 | `poc_video_physics_consistency` | `GateAdapter` | 完全一致 | 191.92 | 185.72 | after ≤ before |

初回測定では、ffmpeg探索失敗、Windows DLL初期化失敗、他プロセス負荷による時間逆転があった。ffmpeg実体を明示し、対象を単独で対測定して上表を最終値とした。結果の一致判定に測定失敗回は使用していない。

## PoC側の行数

正の値が削減、負の値が増加である。共通契約の宣言とadapter呼出しを追加したため、第一波全体では91行増えた。P0-Aの第一波では既定値、物理式、図、print、CLIを残す制約を優先したためであり、削減できていない事実をそのまま記録する。

| PoC | before | after | 削減行数 |
|---|---:|---:|---:|
| `poc_interferometry_step` | 671 | 677 | -6 |
| `poc_polarization_specular` | 794 | 796 | -2 |
| `poc_photoelasticity` | 650 | 653 | -3 |
| `poc_phase_measuring_deflectometry` | 1,290 | 1,292 | -2 |
| `poc_grating_interferometry` | 572 | 573 | -1 |
| `poc_thermography_ndt` | 807 | 810 | -3 |
| `poc_thermal_radiometry` | 1,691 | 1,714 | -23 |
| `poc_pv_thermal_survey` | 1,429 | 1,466 | -37 |
| `poc_lens_tolerancing` | 218 | 221 | -3 |
| `poc_simcal_telecentric` | 646 | 645 | 1 |
| `poc_simcal_pixel_shift` | 1,191 | 1,190 | 1 |
| `poc_cad_scan_deviation` | 1,686 | 1,689 | -3 |
| `poc_lidar_terrain_change` | 2,084 | 2,087 | -3 |
| `poc_focus_stacking` | 650 | 655 | -5 |
| `poc_video_physics_consistency` | 456 | 458 | -2 |
| **合計** | **14,835** | **14,926** | **-91** |

## PoCに残したもの

| 分類 | 残したもの | 理由 |
|---|---|---|
| 物理 | Planck積分、Fresnel、unwrap、PSF、熱拡散、ICP、LiDAR地形差、運動方程式 | 定理の閉形式、反例、ゼロ点を説明するPoCの主張そのもの |
| 既定値 | PSF境界、unwrap閾値、放射率、帯域、noise順序、座標系、ROC被験単位、capture/playback fps | PoCごとの差を消すと既存の数値・図・captionが変わる |
| 展示 | 図の順番、caption、ローカル`figures()`、print、CLI | 公開出力と展示構成を変えない契約 |
| ドメイン採点 | IoU以外の特殊な幾何・物理量、PoC固有の反例判定 | 3本以上で同じ意味を持つ一般指標ではない |

## 検証

| ゲート | 結果 |
|---|---|
| `tests/test_evaluation_*.py` | 15件成功 |
| `tests/test_suite_hygiene.py` | 成功 |
| 対象ファイルの`ruff check` | 成功 |
| `tests/test_poc_scripts_run.py` 対象15本 | 15件成功、269件deselect |
| `tests/test_poc_scripts_run.py` 全件 | 281件成功。CPU競合下で対象外3本がtimeout/CPU時間門に失敗したが、3本とも単独再実行で成功 |
| `tools/regen_all.py --check` | 成功。「生成物はすべて最新」 |

全PoCゲートの3件は、`poc_dense_bubble_count`と`poc_larval_connectome_reservoir`が600秒timeout、`poc_dual_energy_xray`がCPU時間門超過だった。単独再実行では順に277.26秒、8.91秒、173.37秒で成功した。変更対象15本の失敗ではなく、同時に複数worktreeの全テストが走っていた環境負荷によるものと切り分けた。

## P0-Bへの注意

P0-Bの運転世界へ進む前に、評価契約とscene/truth生成を混ぜない。車両・道路・センサーの物理は既存opまたは明示したrecipeに置き、`TruthBundle`は結果を記述するだけにする。row/colと世界x/y/z、北向き、左手・右手系、RAW前とISP後、valid/ignore/defect maskを必ず別名で宣言する。

使用頻度が3本以上の流れだけをpipeline候補にし、全段が登録opである場合に限って`FullseyeGraph`/`FullseyeEngine`と`RECIPE_INDEX`へ載せる。PoC固有の展示、固定既定値、反例はpipelineへ入れない。新しいsortは、3本以上で共有され、既存sortへ混ぜると単位・座標・段階が黙って失われる場合だけ追加する。
