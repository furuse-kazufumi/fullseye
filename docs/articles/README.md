# docs/articles — 解説記事 / Long-form articles

Fullseye の設計と使い方を解説する長文記事の原稿置き場。リポジトリの他のドキュメント
(`docs/ops/` の op ノート、各種ガイド)が「引く」ためのものだとすれば、ここは
「読む」ためのもの — 全体像を物語として掴みたい人向けです。
Long-form articles that explain Fullseye's design and usage as a narrative,
complementing the reference docs (`docs/ops/`, guides) meant for lookup.

| ファイル | 内容 |
|---|---|
| `fullseye_overview_qiita_ja.md` | 総集編: 設計思想・3層構造・Studio・RAG 運用・正直さの規律(日本語) |
| `assets/` | 記事とREADME で使う図版。**すべて Fullseye 自身の op の実出力**(モックアップなし) |

図版は `py -3.11 tools/gen_article_assets.py` で誰でも再生成できます(seed 固定・
再現可能)。生成物と生成コードを突き合わせれば、図が実測であることを確認できます。
All figures are regenerable with `py -3.11 tools/gen_article_assets.py`
(fixed seeds) — the images are real operator outputs, verifiable against the code.
