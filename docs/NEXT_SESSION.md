# 次セッション引き継ぎ — 徹底敵対レビュー完結(2026-09-03)

## 正本
- 全体記録: raptor memory `project_fullseye_adversarial_review_2026_09_03`
- 構造設計の根拠: `docs/design/TRIZ_DESIGN_PATTERN_MATRIX.md`(TRIZ 40 原理 × パターン / パターン × コンテナ / 原理 × コンテナ、4 軸 + 短所カバー列)
- 利用者向け説明: `docs/KNOWN_ISSUES.md` 末尾「fail-soft の 3 層沈黙」/ `docs/GETTING_STARTED.md` §2
- 前回の台帳(2026-09-02): `out/robustness-audit-2026-09-02/LEDGER.md`(その残 8 件はすべて修正済)

## この回でやったこと(2026-09-02 夜〜09-03)
1. **構造修正**: backends 31 本中 23 本(+ macro/typed の 2 家族)が独自 `_safe` で記録なし → `backend_safe.guard()` に一元化。
   `apply/run_pipeline(on_error="fallback"|"warn"|"raise")`、`fullseye.fallbacks()` 台帳(deque 256、出所 op/gpu/input/import)、
   op ごと 1 回の `FullseyeFallbackWarning`、GPU Circuit Breaker(`reset_gpu()`)、strict は thread-local。
   facade の穴: nary 17 op を `apply([x1,x2], name)` で、`template=`、HALCON 曖昧別名テーブル。Codex 読取レビュー 2 巡目 13 件反映。
2. **敵対レビュー 7 領域 → 修正完了**: fscript 14 / studio 11 / 体積+IO 15 / 計測系 11+細部 / 3D 幾何 7 / 進化+backends 6 / algo+C 8。
   すべて再現手順付き・修正後の数値で確認(各エージェント報告は memory に要約)。
3. **CI 常設**: `tests/test_op_probe_ledger.py` + `docs/OP_PROBE_ALLOWLIST.json`(退化 27 件を理由付き許容、新規は fail)、
   typed liveness に sort 跨ぎ恒等/定数/3ch 検査、OP_CATALOG/SENSOR_PLAYBOOK drift、examples2d 両方向検査、ci.yml `-rs`。
4. **Studio UI 4 本柱**: `param_specs.py`(81 op 手書き検証 + 66 doc 由来)、右クリック全ビュー、副窓対称化、Insert→行生成、Ctrl+F 等。
5. **記事**: 数値を 2D 860 / 3D 310 / HALCON 981(42.4%)へ、`tools/gen_article_assets.py` は記事本文を単一情報源として照合、
   図・サムネ再生成、wingopt サムネのコードスパンをリンク化、`tools/qiita_patch_overview.py`(GET 退避→検査→PATCH→検証)。

## 利用者が気づく挙動変更(要リリースノート)
- `fscript`: `mean_gray/min_gray/max_gray` は 0..1 比率 / 署名済みレシピは digest 変更で再署名要 / `read_image` は `base_dir` 内に限定 / タプル演算・添字・数値字句が厳格化
- `measuring1d`: `amplitude` = 濃度差(旧 勾配ピーク ≈0.32×)、`threshold` も濃度差基準、`row/col/dist` 追加 / `metrology` は実形状で再フィット
- `calib.camera_calibration` は (row,col) 入力 / `caltab.find_marks_and_pose` は失敗で例外(旧 identity)
- `algo`: 番兵 0.0→−1.0(`is_prime`/`segments_intersect`/`edit_distance`/`point_in_polygon`/`lcs_length`)、2^53 超の整数は ValueError、graph n ≤ 5e6
- `imgio.save` は uint8 を彩色しない / 切れた JPEG は ValueError / 偶数線幅が 1px 細く / `to_float01(int16)` はアフィン
- `pnp3d`: 完全平面入力は例外でなく平面経路で解く / `bundle3d` は scale_anchor で尺度固定 / `register(init="auto")`
- `apply` 既定で op ごと 1 回の警告が出る(`warnings.filterwarnings("ignore", category=fullseye.FullseyeFallbackWarning)` で消せる)

## 次にやること(優先順)
1. **git push → Qiita PATCH**(push は ASK FIRST 規約のため未実施)。手順:
   `git push` → `py -3.11 tools/qiita_patch_overview.py --check`(画像 17 件が 200 になること)→ `py -3.11 tools/qiita_patch_overview.py`。
   記事のテスト件数(`6238`/`6,238` の 3 か所 × ja/en と末尾コメント)は最終スイート値に置換済みか確認。
2. PyPI リリース(v0.1.4): 上記「挙動変更」をリリースノートに。`docs/GENERAL_ALGORITHMS.md` 末尾の番兵注記を README にも。
3. TRIZ マトリクスの推奨 Top-5 の未実施分: `fullseye.selfcheck()`(プローブ + 台帳を 1 コマンドに)/ typed ブリッジの `_EMPTY_OF` 欠落 2 sort(lightfield, histcube; wide vocab)/ `tb_euclidean_cluster` 常時ゼロ(tol 配線)。
4. 未対応の細目: `pow_mod/gcd_seq/popcount_total/polygon_area2` の 0.0 番兵衝突 / `xcv2_hitmiss` の knob 未使用 / render_mesh スムーズシェーディング(設計判断待ち)/ ファザー「呼べたが毎回拒否」35 件(合成シーン要)。
5. raptor upstream 同期(`update/upstream-2026-09-02` ブランチ、373 ファイル/13 コンフリクト)は保留のまま。
