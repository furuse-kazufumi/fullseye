# 次の計画（i18n「全部進めて」の続き / 2026-09-13）

ユーザー指示「全部進めてください」。本セッションで下記まで完了・**master push 済み**（CI 実行中）:
- DESIGN_NOTES ★ 609/609 を 5 言語完訳
- 入口手書き 7 本 + step3 (A) 読み手向け 16 本を英訳（かな 0・指紋・索引反映）
- 光学設計を差別化として README 6 言語明記
- 焦点合成 PoC を半導体ワイヤ・ボンディング場面へ（gray/17枚/距離画像）

## 次セッションで進める（残りの「全部」）
1. **step3 (A) 16 本の zh/tw/ko/de**（英語が済んだ「次段」）。対象=
   BENCH_VS_OPENCV / HDEVELOP_FIDELITY / HDEVELOP_DEV_OPS / HALCON_COVERAGE_HONEST /
   TERRAIN_WALK / GSPLAT_NATIVE_WINDOWS / SAMPLE_IMAGE_REFERENCES / EVIS_VISION_OSS_GAP /
   CHAIN_FUZZ / OP_COMBINATION_MATRIX / FSCRIPT_LANGUAGE / GPU_OPTIMIZATION_PATTERNS /
   UNIFIED_API_REQUIREMENTS / EVOLUTION_ENVIRONMENT / GALLERY / MATCH_3D_MATRIX。
   手順=並列 Agent で `<name>.<lang>.md` を作り `tools/i18n_docs.py --stamp`。
   ★中黒「・」は「·」に（U+30FB は隠れかな扱い＝test_i18n が落ちる）。
2. **入口/README の zh/tw/ko/de**（入口 7 本は現状 en のみ）。
3. **半導体検査 demo 群**（memory `project_fullseye_semiconductor_demo_suite`）:
   ワイヤボンディングに続き BGA/バンプ・TSV・リードフレームの例画像 + 3D モデル、
   光学設計（`lensopt`/`optimize_lens`）と接続して「設計→検査」を一気通貫で見せる。
4. CI 緑を確認（前回 push 34724203881）→ Qiita 更新。

## 対象外（記録済み・訳さない）
i18n の (B) 既英語 / (C) 生成物 / (D) 内部作業ドキュメント（KNOWN_ISSUES 等）。詳細 docs/I18N_PLAN.md。
