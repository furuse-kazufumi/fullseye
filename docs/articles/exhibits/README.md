# 展示(exhibits)―― 記事の「紙面の科学館」章の単一真実源

記事本文の展示章は**ここから生成される**。本文を手で編集しないこと(次の生成で消える)。

## 展示ウィングを 1 つ増やす手順

1. 画像/GIF を作る生成スクリプトを `tools/gen_<id>_gallery.py` に置き、成果物を
   `docs/articles/assets/<id>_<name>.png`(+ `_thumb.jpg`)や
   `docs/articles/assets/media/<id>_<name>.gif` へ出す。**決定的**に(再生成で SHA-256 一致)。
2. キャプション原稿を **`<id>.ja.md` と `<id>.en.md`** の 2 枚として置く。
3. `wings.json` の `wings` に 1 行足す:

   ```json
   { "id": "<id>", "order": 60, "title": { "ja": "...ウィング", "en": "The ... Wing" } }
   ```

4. `py -3.11 tools/build_exhibits.py` を実行。**章見出しの展示点数は自動で数え直される**
   ので、手で書き換えない。

`order` が小さいものから並ぶ。既存ウィングの間に挟みたければ、間の数を使う
(10, 20, 30 … と空けてあるのはそのため)。

## 書式

各展示は「画像 1 行 + キャプション 1 行」の組:

```markdown
[![alt](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/<id>_<name>_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/<id>_<name>.png)

*↑ **タイトル** ―― 1〜3 文の説明(実測値を含める)。使用 op: `a`, `b`。*
```

`####` で小見出しを作って分野ごとに束ねてよい(`museum.ja.md` がそうしている)。

## 機械が拒否するもの(`tools/build_exhibits.py` / `tests/test_exhibits.py`)

展示が増えるほど目視は続かないので、次は生成前に **fail-closed** で止まる。

| 検査 | 理由 |
|---|---|
| 画像 URL が raw ベースで始まっていない | 相対パスは Qiita で表示されない |
| 参照している画像が repo に無い | リンク切れの記事を出さない |
| 画像の直後にキャプションが無い | 「どの op で作った絵か」の分からない展示を作らない |
| ローカルパス(`C:\` など)の混入 | 公開物に手元の環境を書かない |
| キャプションが 1 つも無いウィング | 空の器を並べない |
| `<id>.en.md` が無い | ja だけ足して en を忘れる、が一番起きやすい |
| 本文が生成物と食い違う(drift) | ソースだけ直して再生成を忘れる/本文を手で直す、を防ぐ |

画像 URL に `?v=2` のようなキャッシュ外しを付けるのは可(実在確認では落とされる)。

## 素材の来歴

実データは **CC0 / public domain のみ**(Smithsonian / Met / NASA)。キャプションに出典リンクを
書く。AI 生成の模擬データは**画像内とキャプションの両方に明記**する。ライセンスが本リポジトリと
両立しないものは、たとえ良い絵でも展示から外す。
