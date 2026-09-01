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

## 束ね方は 3 つ(`tools/exhibit_tile.py`)

ありふれた静止画の処理結果を 1 枚ずつ原寸で並べると、記事が縦に伸びて読む速度が落ちる。

| 束ね方 | 使う場面 | API |
|---|---|---|
| **タイル** | 並べて**比べる**もの。パラメータ違い、族の見本帳。3 枚以上あるとき | `contact_sheet` → `save_exhibit` |
| **フリップブック GIF** | **同じ寸法の絵で工程が進む**もの。前処理 → 二値化 → 細線化 → 計測 | `flipbook` → `save_animation` |
| **原寸で 1 枚** | 図中の数値が主役、軸ラベル付きグラフ、前後 2 枚だけの比較 | `save_exhibit` |

```python
import sys; sys.path.insert(0, "tools")
from exhibit_tile import contact_sheet, flipbook, save_exhibit, save_animation, markdown

sheet = contact_sheet([a, b, c, d], ncols=2, labels=["収縮 -18.4%", "膨張 +21.7%", "開", "閉"],
                      title="形態学の 4 兄弟(同じ図形・同じ構造要素)")
save_exhibit(sheet, "wing2d_morphology_four")        # png + _thumb.jpg

book = flipbook(steps, ["読み込み", "二値化", "細線化", "計測"], title="計測までの工程")
save_animation(book, "wing2d_measure_flow")          # gif + thumbs/_thumb.jpg
```

`flipbook` は**寸法が揃っていないと例外**にする ―― 揃っていないものをコマ送りにすると
工程ではなく「別の絵の羅列」になるので、それは `contact_sheet` の仕事。各コマには
工程名と `i/N` の進捗バーが焼き込まれるので、**止まった 1 コマでも意味が分かる**。
`save_animation` は書いた GIF を**読み戻してフレーム数を照合**する。

タイル 1 枚・GIF 1 本は**展示 1 点**と数えてよい(中身の枚数はキャプションに書く)。

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

## 公開前の点検(機械生成物は必ず最後に見る)

自動生成した図は**それらしく見えるのが致命的に簡単**なので、目視だけにも機械だけにも頼らない。

```powershell
py -3.11 tools\check_exhibit_assets.py --strict            # 記事が参照する全画像
py -3.11 tools\check_exhibit_assets.py --prefix wing3d_    # 新しいウィングだけ
```

寸法・容量・GIF のフレーム数に加えて、**真っ黒/真っ白に潰れていないか**、**実質単色でないか**
(生成失敗の典型)、**別名で同じ画像を出していないか**(生成器のコピペ事故)、サムネイルの
欠落を見る。ただしこの点検が言えるのは「**壊れていない**」ことだけで、
**中身が正しいかは人が目で見る**。軸の入れ替わり・単位のずれ・端 1 画素のずれは、
機械が「壊れている」と判定できない形で通ってしまう。

## 素材の来歴

実データは **CC0 / public domain のみ**(Smithsonian / Met / NASA)。キャプションに出典リンクを
書く。AI 生成の模擬データは**画像内とキャプションの両方に明記**する。ライセンスが本リポジトリと
両立しないものは、たとえ良い絵でも展示から外す。
