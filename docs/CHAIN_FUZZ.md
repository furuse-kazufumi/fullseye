# 連鎖ファザー(chain fuzz)— op を鎖にして揺さぶる第三の品質保証層

`tools/chain_fuzz.py`。単体テスト・敵対的検証に続く 3 番目の層で、狙う不具合は
**「単体では全部通るのに、op を鎖にしたときだけ現れるもの」**です。

- 単体テスト = 1 op の入出力が仕様どおりか
- 敵対的検証 = 1 op の境界・退化・符号・ゼロ割を人(と AI)が攻める
- **連鎖ファザー = op の出力を次の op が食ったときに壊れないか**

型契約の嘘、tuple/list 梱包の不一致、NaN の漏出、想定外の例外種、拡大系の
指数増殖 —— どれも単体テストの視野の外にあります。

## 使い方

```bash
# 拡散: 2000 本の連鎖をランダムに張って署名を集める
py -3.11 tools/chain_fuzz.py --chains 2000 --length 8 --seed 1 --out out/chain_fuzz.jsonl

# 収束: 各発見を「その署名を出す最小の op 列」まで削る
py -3.11 tools/chain_fuzz.py --minimize out/chain_fuzz.jsonl
py -3.11 tools/chain_fuzz.py --minimize out/chain_fuzz.jsonl --only compute_fpfh

# 再走: 最小再現をそのまま実行(デバッガを当てる入口)
py -3.11 tools/chain_fuzz.py --replay 5000312 --script random_dropout,compute_fpfh
```

## 分類(署名の種別)

| 種別 | 意味 | 扱い |
|---|---|---|
| `CONTRACT` | 文書化された `ValueError` | **白**。fail-closed が仕事をした |
| `SUSPECT` | それ以外の例外(TypeError/IndexError/…) | 契約の穴。入口検証を足す |
| `TYPEMISS` | 目録の宣言 out 型と実際の返りが違う | 型の嘘。adapter か宣言を直す |
| `NONFINITE` | 有限入力から NaN/Inf が無言で出た | 毒の漏出。**ただし契約かを先に疑う** |
| `GROWTH` | 産物が pool 上限超(拡大系の指数増殖) | 記録して捨てる(**無言で切らない**) |
| `SLOW` | 1 op が閾値超(既定 10s) | 性能スメル |
| `OPTIONAL` | optional 依存の ImportError | 白(記録しない) |

`NONFINITE` は「非有限を出した op」を責める前に **出所と契約**を追うこと。実例:
`sdf_subtract` の inf は `esdf` の「全自由なら +inf」という文書化済み契約を
min/max 代数が正確に伝播しただけで無実、一方で同family の `sdf_smooth_union`
だけが算術(inf−inf)で全 NaN になる本物のバグでした。契約として正しい非有限は
`NONFINITE_BY_CONTRACT` に **理由つきで**登録します。

## 設計上の要点(なぜこの形か)

### 型付きプール
各 op の宣言(in 型 → out 型)に従ってプールから引数を引き、産物を戻します。
型語彙は目録と共有(`voxel`/`points`/`signal`/`matrix`/`table`/`pairs`/`roots`…)。
`TYPE_CHECKS` が各語彙の判定関数を持ち、**宣言と実際の返りの一致を機械検証**します。

### 連鎖固有 seed
連鎖 *i* は `seed * 1_000_003 + i` で回ります。共有 rng だと「*i* 番目だけを
後から再走する」ことができず、最小化が成り立ちません。

### 引数抽選の乱数を位置から独立させる(最小化の生命線)
候補抽選(どの op を次に引くか)は連鎖 rng、**引数抽選は
`(連鎖 seed, op 名, その op の出現回数)` から導いた別の乱数源**を使います。
これを分けないと、無関係な op を 1 つ落としただけで以降の抽選が全部ずれ、
最小化の再走が原理的に再現しません。**実測: 分離前は再現 48/65(74%)、
分離後は 58/58(100%)**。同じ理由でプールの型選択も `sorted(pool)` に固定
しています(dict の挿入順は op を落とすと変わるため)。

### 上限とストール自己申告
- `MAX_POOL_BYTES`(128MB): 拡大系連鎖の指数増殖を止める。超過は `GROWTH` として
  **記録**(silent cap 禁止)。
- 32MB 超の入力は実行前に `big-input:` を print。万一のストールでもログだけで
  犯人が判る(実測でこれが 2 度役に立った)。

## 運用の型(拡散と収束を繰り返す)

1. 拡散(2000 連鎖)→ 署名一覧を得る
2. `--minimize` で各署名を最小 op 列へ
3. **最小再現を手で実行して実証してから**直す(推測でパッチを当てない)
4. バグ 1 件を直したら、**同クラスを兄弟コードで一掃**する
   (例: float32 桁あふれは 20 箇所の同種キャストに 1e39 を実際に流して、
   該当した 4 op だけを直した — 実測で該当しないものは触らない)
5. 同じ seed で再走し、署名が消えたことを確認

## これまでの戦果(実測)

| 波 | 署名数 | 主な発見 |
|---|---|---|
| 第 3 波 | — | 型の嘘 22 件、`RESULT_ADAPTERS`+`call()` を一級機能化 |
| wave-4 | 103 | TYPEMISS 7 op、SUSPECT 9 種、第 6 家系「小さい入力→巨大な内部割当」(TPS 12GB / PSF 64GB / CPD) |
| wave-5 | 4 | float32 桁あふれの無言 NaN、`sdf_smooth_union` の inf→NaN、入口契約の穴 2 系統 |
| wave-6 | **非 CONTRACT 0** | 収束(白 63 種のみ) |
| math 追加 | 2 | `mat_svd`/`mat_eigh` の型の嘘を初走行で即検出 |

## 拡張するとき

- **新しい op family を catalog に足す**: `catalog()` に目録を追加。型語彙が
  増えるなら `TYPE_CHECKS` と `make_generators()` にも足すこと。
- **返りが宣言型と違う**なら、素の関数は数学/慣習どおりの返り(tuple など)を
  保ったまま、目録側に `RESULT_ADAPTERS` を登録して `call()` が宣言型を返す形に
  します(先例: `mat_svd` → `{"U","s","Vt"}`)。
- 回帰は `tests/test_chain_fuzz_minimize.py`(収束フェーズの契約)と
  `tests/test_chain_type_contracts.py`(宣言型の一致)にあります。
