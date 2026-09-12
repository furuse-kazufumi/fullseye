# 完全な多言語化 — 計画と現在地

> 正本。**セッションを跨いで**進める。数字は測って書く(手で書いた進捗は必ず古びる)。
> 数え直しは `py -3.11 tools/i18n_status.py`。

## 何を「完全」と呼ぶか

読み手が言語を切り替えたとき、**日本語が黙って混ざらない**こと。
未訳を隠さないことが前提 —— 黙って原文に落ちると「訳したつもり」になるので、
未訳は `(ja)` の印を付けて数える。印が出ている状態は「途中」であって「壊れ」ではない。

## 層ごとの現在地(2026-09-09 実測)

| 層 | 量 | 状態 |
|---|---|---|
| op ノート由来の Studio ヘルプ | 10,191 ページ | **6 言語で完了** |
| `docs/ops/INDEX`(コーパスの入口) | 1 本 | **6 言語で完了** |
| `docs/README`(索引) | 1 本 | 6 言語。ただし表の中身に `(ja)` が 44 行 |
| `CAPABILITIES` / `HARDENING` | 2 本 | ja + en |
| `DESIGN_NOTES`(★ コメント集) | 606 件 | 6 言語の器はある。**訳は 5 件** |
| **`docs/` のそれ以外** | **69 本 / 18,632 行** | **日本語のみ** |
| ソースの日本語コメント | 100,786 行 | 訳さない(下記) |

**ソースのコメントは訳さない。** 約 50 万行に膨らみ、編集のたびに 6 か所を直すことになる。
この repo のコメントは測った値を書くので、値が変われば必ずどれかが古びる。
代わりに `★` を付けた 606 件だけを生成物 `DESIGN_NOTES` として訳す
(ソースは日本語のまま単一の正本 —— だから食い違わない)。

## 順序(外から来た人が実際に辿る順)

1. **入口の 10 本** — 手書き 7 本は英訳済み(2026-09-10):
   `GETTING_STARTED` ✓ / `AI_RAG_GUIDE` ✓ / `INSTALL` ✓ / `STUDIO_GUIDE` ✓ /
   `GENERAL_ALGORITHMS` ✓ / `ENGINE` ✓ / `3DGS_USAGE` ✓。
   残り: `MATURITY`(生成物・表内で既に日英併記)/ `EXAMPLES_3D`・`SENSOR_PLAYBOOK`
   (生成物 —— 生成器側 i18n が必要。本文は登録内容=op ノート由来ゆえ step 2 の
   ★/op ノート訳ウェーブに依存)/ `OPERATORS`(既に全文英語)。
   = 手訳可能な入口文書は完了。生成物 3 本は登録内容の訳(step 2)後に生成器で英語化。
2. **`DESIGN_NOTES` の ★ 609 件** — ✓ **完了(2026-09-13)**。5 言語(en/zh/tw/ko/de)
   609/609。並列 Agent で分担→言語別文字種検証で混入除外→冪等 merge、隠れ日本語ゼロ。
3. **残りの文書 = 翻訳スコープを確定した(2026-09-13)**。`.en.md` の無い 63 本を
   種別で分け、**訳すのは読み手向けだけ**にする(全訳はしない —— 内部記録は
   更新が速く、生成物は生成器側の課題、既に英語の文書は訳が不要):

   **(A) 訳す(読み手向け・英語優先)** —— 本文が日本語の実用/参照ドキュメント。
   `BENCH_VS_OPENCV` / `HDEVELOP_FIDELITY` / `HDEVELOP_DEV_OPS` /
   `HALCON_COVERAGE_HONEST` / `TERRAIN_WALK` / `GSPLAT_NATIVE_WINDOWS` /
   `SAMPLE_IMAGE_REFERENCES` / `EVIS_VISION_OSS_GAP` / `CHAIN_FUZZ` /
   `FSCRIPT_LANGUAGE` / `GPU_OPTIMIZATION_PATTERNS` / `UNIFIED_API_REQUIREMENTS` /
   `EVOLUTION_ENVIRONMENT` / `GALLERY` / `MATCH_3D_MATRIX` / `OP_COMBINATION_MATRIX`。
   入口文書と同じく `<name>.en.md`(言語ナビ + 指紋)を作る。英語が済んだら zh/tw/ko/de。

   **(B) 既に英語で書かれている(訳不要)** —— `PERCEPTION` / `PERCEPTION_REALDATA` /
   `PERCEPTION_PHYSICAL_AI` / `EXAMPLES` / `ADDING_OPS` / `REPRODUCE` / `REFERENCES` /
   `CONSUMER_APPLICATIONS` / `STUDIO_UX` / `INTEGRATION` / `PROVENANCE` / `V13` / `V14` /
   `WAVE0_STABLE_SLOTS` / `HALCON_PARITY` / `LIB_COVERAGE` / `PARITY_CROSSBACKEND` /
   `HALCON_COVERAGE` / `ACCURACY_BENCH` / `OPERATORS` ほか。本文が英語なので en は不要
   (将来 ja/他言語版が要るなら別途 —— 英語は参照ドキュメントの lingua franca)。

   **(C) 生成物(生成器側 i18n の課題・別トラック)** —— `MATURITY`(表内日英併記)/
   `EXAMPLES_3D` / `SENSOR_PLAYBOOK` / `CONVERSION_MATRIX` / `OP_CATALOG` /
   `SESSION_SUMMARY`(毎ターン自動生成)/ `CONNECTIVITY`。本文は登録内容(op ノート)
   由来ゆえ、op ノートの多言語化が済んでから生成器で出す。

   **(D) 内部作業ドキュメント(訳さない)** —— 計画・監査・セッションログ・記事下書き・
   チェックリスト・状況: `STATUS` / `NEXT_SESSION` / `I18N` / `I18N_PLAN` / `*_PLAN*` /
   `*_TODO` / `ARTICLE_*` / `RELEASE_CHECKLIST` / `INDUSTRY_SIGNALS` /
   `FSCRIPT_MEASUREMENTS` / `FSCRIPT_DECISION` / `HIGHSPEED_VISION` / `*_2026_*` /
   `FULLSEYE_OP_ARTICLE_SPEC`。読み手が少なく更新が速い —— 訳すと真っ先に古びる。
   `KNOWN_ISSUES`(2,475 行)も同じ理由でここ。

   → **計画の完了 = (A) を訳し切ること**。(B)(C)(D) は上記の理由で翻訳対象外
   (= 決定として記録)。

## 維持できる形にするために置いたもの

* 未訳は `(ja)` と表示され、**黙って日本語に落ちない**(`gen_docs_index_ops._doc_label`、
  `_poc_name`、`gen_design_notes.render`)
* 訳の本数を数えて `docs/design_notes.json` に書き、**減ったら CI が落ちる**
  (`tests/test_design_notes.py` の ratchet)
* 生成器は `tools/regen_all.py` の CHAIN に載せ、**分類されていない生成器があれば
  CI が落ちる**(`tests/test_regen_all.py`)

## やらないと決めたこと

* **機械翻訳を生成時に呼ぶ**ことはしない。生成器は外部 API を叩かない規約で、
  かつ訳の品質を人が見ていない状態で公開物に流すのは、この repo の
  honest disclosure の規律に反する。
* 日本語側を英語に置き換えることはしない。日本語版は正本。
