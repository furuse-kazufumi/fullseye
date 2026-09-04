# docs/articles — 解説記事 / Long-form articles

Fullseye の設計と使い方を解説する長文記事の原稿置き場。リポジトリの他のドキュメント
(`docs/ops/` の op ノート、各種ガイド)が「引く」ためのものだとすれば、ここは
「読む」ためのもの — 全体像を物語として掴みたい人向けです。
Long-form articles that explain Fullseye's design and usage as a narrative,
complementing the reference docs (`docs/ops/`, guides) meant for lookup.

| ファイル | 内容 | 言語 |
|---|---|---|
| `fullseye_overview_qiita_ja.md` / `fullseye_overview_qiita_en.md` | **総集編**: 設計思想・3層構造・Studio・RAG 運用・正直さの規律・151 の展示 | ja / **en** |
| `exhibits/` | 紙面の科学館 —— op で遊ぶ展示。`_intro` / `museum` / `science` / `wing*`(1D/2D/3D/astro/conv/ct/evo …) | ja / 一部 **en** |
| `qiita_3dgs_sim_native.md` | 物理シミュをそのまま 3D Gaussian Splatting にする(姿勢推定いらず・純 PyTorch) | ja |
| `assets/` | 記事と README で使う図版。**すべて Fullseye 自身の op の実出力**(モックアップなし) | — |

**言語版の置き方**: 対訳は `<name>.en.md` / `<name>.zh.md` を**原文の横に置く**
(`exhibits/` で既にこの形)。翻訳の指針と v1.0.0 までの計画は `docs/I18N.md`。
Translations live next to the source as `<name>.en.md` / `<name>.zh.md`; see `docs/I18N.md`.

図版は `py -3.11 tools/gen_article_assets.py` で誰でも再生成できます(seed 固定・
再現可能)。生成物と生成コードを突き合わせれば、図が実測であることを確認できます。
All figures are regenerable with `py -3.11 tools/gen_article_assets.py`
(fixed seeds) — the images are real operator outputs, verifiable against the code.
