# 次セッション引き継ぎ — 堅牢性一掃(2026-09-02)

## 正本
**`out/robustness-audit-2026-09-02/LEDGER.md`** が統合バグ台帳。各項目に
verified(主セッションで再現) / agent-confirmed / plausible のステータス付き。
個別レポート: `test_false_confidence.md` / `runtime_degeneracy.md`(+json) /
`core_review.md` / `recent_ops_adversarial.md` / `studio_ui_audit.md` /
`codereview_A_optics.md` / `_B_measure.md` / `_C_imaging.md` / `_D_geometry3d.md`

## この回でやったこと
8 本の並列監査(テスト偽安心 / 全861op 実行時プローブ / コア経路 / 新op敵対検証 /
Studio UI / CodeReview A-D)を回し、**確定バグ 7 件を修正**(すべて実測で効果確認・
回帰 green。auto-commit 済み)。

修正済み: r3_label_to_region のラベル潰れ(backends_regions3+api) / drizzle×frame_align
符号逆(astrostack) / look_at 180°回転(shapematch) / sinkhorn_divergence が遠い分布に
0.0(colortransport) / tsdf_from_depth の視野外を観測済み扱い(match3d) / panel_grid・
compare_frame の RGBA α(annotate) / cad_pixel_to_surface の bary 頂点順(cadmap)

追加した API: **`astrostack.drizzle_shifts(matrices)`**(符号変換を1箇所に閉じ込め) /
`api._LABEL_READING_OPS`(ラベル読み op の明示登録点)

## 核心的な診断(次の設計判断の土台)
テストは 4417 本あり個々の質は高い(真正 assertion-only は 0.14%)。にもかかわらず
バグが残るのは **fail-soft が3層に重なって沈黙させる構造**:
1. facade `fullseye.apply` がほぼ例外を出さない(不正入力も fallback 出力に化ける)
2. `api.py:958,1000` の GPU 分岐が `except Exception: pass`(CI は CUDA 不在=GPU 実効カバレッジ 0%)
3. `backends._safe` → `backend_safe.fallback` のファネル(壊れた op と働く恒等が区別不能)

修正した 7 件中 6 件が「例外を出さず黙って間違う」型。**新 op の数学自体は堅牢**
(109 の独立検証で摘発ゼロ、機械精度一致)。作りが甘いのではなく、エラーを見せない構造が問題。

## 次にやること(優先順)

### A. 残りの確定バグ
1. `ncc_locate` / `shape_locate` — facade からテンプレート設定不能→常に `[0,0,0]`。
   facade に設定入口を公開する or `op_names()` から外す。
2. `tb_quaternion_to_rgb` — 全入力で恒等、RGB を生成しない。実装修正 +
   liveness test に**sort 跨ぎ恒等**の検査を追加(現行は同 sort 恒等しか見ない盲点)。
3. `api.py:958,1000` GPU `except Exception: pass` の可観測化 — 例外種を絞る
   (ImportError/torch 系のみ)or 初回フォールバック時に警告1回 + strict device モード。
4. `opsimgmetrics.py:68-69` — XYZ を `rgbimage` と宣言(台帳の嘘)。`rgb_to_lab(rgb_to_xyz(x))`
   が例外なしで L*=5.72(正 32.53)。
5. `tomography.py:1130` `_span_weight` — golden スキームで span 162.8°(真 180°)、
   再構成密度が黙って 9.6% 低下。`:815` streak_free_radius_px の単位が mm/rad(正は 1/d_theta)。
6. `complexops.py:375` phase_unwrap が (1,N)/(N,1) で巻いたまま返す(誤差 18.85 rad)。
7. `imgforensics.py:1589` evidence_quantile の beyond_fraction が6段の梯子(doc と別物)。
8. doc の嘘: lf_synthesize(背景層の規則) / motion_magnify の「unwrapped along time」/
   csi_signal_simulate の off-by-one / reprconv angle_to_matrix の 90°方向 /
   opscolortransport の histogram_match「厳密一致」。

### B. Studio UI 規約4本柱(memory `feedback_studio_ui_menu_completeness`)
監査結果: 死にボタン 0・実クラッシュ 0 でアプリは堅牢。真の問題は**入力アフォーダンス不足**。
1. **op パラメータの型適合ウィジェット**(最重要) — 現状は全 op が固定 0..1 の 2 ノブ
   `a,b`(studio.py L2639, L3346-3351, L3436-3446)。**前提として レジストリに param 型
   メタデータが存在しない**(`op_arg_roles` は一部 op の人間可読文字列のみ)。
   → まず per-op param spec(型/範囲/選択肢)をレジストリに足すのが先。
2. **右クリックメニュー** — `setContextMenuPolicy(CustomContextMenu)` はファイル全体で
   1箇所(L6258)・リスト3パネルのみ。`contextMenuEvent` override は 0 箇所。
   ImageView(主/副)・Viewer3D の**全表示系ビューに右クリックが無い**。
3. **副グラフィクス窓の対称化** — 副窓は wheel のみ(Fit/1:1/Save ボタン無し)。
4. **パラメータウィンドウ→スクリプト行生成**(HDevelop 方式) — 現状**経路ゼロ**。
   `b_insert`(L5641)はパイプラインに add_stage するだけでエディタ行を挿入しない。
5. 小物: Ctrl+F をメニュー登録(L3121、唯一のメニュー到達不能操作) / Run メニューの
   二重 run/step/reset 単一化 / step_summary の未丸め float・タプル repr の整形 /
   メインウィンドウ最小サイズ(L3092)。

### C. 恒久対策(再発防止)
- 「呼べた/毎回拒否/引数が組めない」を分けて数えるカバレッジを CI 常設化
  (`runtime_degeneracy.json` のプローブが土台。`out/.../probe_runtime_degeneracy.py`)。
- liveness test に **sort 跨ぎ恒等**と**退化出力**の検査を追加。
- clean checkout で 16/238 ファイルが artifact 不在で丸ごとスキップ、99/238 が
  importorskip 部分ゲート → 「緑=実行済」ではない。スキップ内訳を CI で可視化。

## 保留中の別件
- **raptor upstream 同期**: `C:/dev/tools/raptor` に同期ブランチ `update/upstream-2026-09-02`
  を作成済み(origin/main 起点)。fork main とのマージは **373 ファイル変更/コンフリクト 13 件**
  と計測済みだが、マージは abort して元ブランチ(`feat/worklog-orchestration`)に復帰済み。
  再開は switch → `git merge main`。方針=フレームワークは upstream 優先、fork の
  ワークフロー資産(CLAUDE.md/settings.json/.gitignore)は保全。本家の requirements は
  厳密ピン(no loose deps)なので、同期後に `pip install -r requirements.txt` が Python 更新も兼ねる。
- **HTML化 + awesome-list 入り**: 堅牢性の後段。docs/ops に 1570 md が既にあり、
  MkDocs Material で GitHub Pages 化するのが最短。
- **モデル**: raptor セッションはセキュリティ文脈のため安全分類器が Fable→Opus 4.8 に
  毎ターン再ルートする。Fullseye 作業は raptor の外(imgevolve 直下)で起動すると Fable を維持できる。
