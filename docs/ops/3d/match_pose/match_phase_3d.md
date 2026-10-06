---
op: match_phase_3d
dim: 3d
category: match_pose
in: voxel × voxel
out: shift
gpu: true
examples: [shape_desc_pose]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.4.0  # fullseye lib version this note was generated for
---

# match_phase_3d — 3D `match_pose` op

- **データ種**: `voxel × voxel` → `shift`
- **呼び出し**: `import fullseye as fs; fs.ledger.match_phase_3d(a, b, device='cpu', window='tukey', whitening=0.25)` (実装を直接呼ぶなら `import match3d; match3d.match_phase_3d(a, b, device='cpu', window='tukey', whitening=0.25)`、台帳から引くなら `ops3d.get("match_phase_3d")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

3D 位相相関(FFT)。b を a に合わせる整数シフト (dz,dy,dx) を返す。

Reddy & Chatterji の 3D 版。相互パワースペクトル R = A·conj(B) を |R|^``whitening`` で割って逆 FFT したピーク = 平行移動。
テンプレート不要・全 volume・O(N log N)。回転/スケールは別途(PCA / log-polar)。

引数: ``a``, ``b`` は同形の 3-D 配列(違えば ValueError)。float32 に落として FFT する。``window``: ``"tukey"``(既定、α 0.5)・
``"hann"``・``None``(掛けない)—— 窓は平均を引いてから掛け、長さ 8 未満の軸には掛けない。``whitening``: |R| の指数(0〜1、
1 = 古典的な位相相関の全白色化、0 = 素の相互相関、既定 0.25)。
返り値: int の tuple ``(dz, dy, dx)``、各軸 ``(−N/2, N/2]`` に折り返し済み。意味は
``np.roll(b, (dz,dy,dx), axis=(0,1,2)) ≈ a``(b をこれだけ動かすと a に重なる)。

★既定を替えた理由(2026-10-06、:func:`filters_freq.phase_correlation_fft` と同じ罠): 0.4.0 までの「窓なし + 全白色化(eps 1e-9)」は、
帯域の限られた volume の **周期的でない切り出し**(重なりが部分的な 2 つの撮像という普通の使い方)で、信号の無い周波数のビン
(切り出しの縁の不連続の漏れと丸め)が白色化で信号のあるビンと同じ重みになり、正しいずれを返さなかった —— 低域通過した 32³ の
切り出しでずれ 10 通りが 0 / 10、64³ でも 0 / 10。np.roll の周期的なずれでは厳密なので、それだけの門では見えなかった。
3 次元では 2 次元(既定 Hann + 0.5)より窓が重なりを削り、白色化が雑音のビンを持ち上げやすい: 測った当たり(ずれ 10 通り × 種 3 組)で、
32³・ずれ ±6 の低域の切り出しは Hann + 0.5 が 11 / 30、Hann + 0.25 が 19 / 30、Tukey + 0.25 が 28 / 30、周期的なずれは
それぞれ 9 / 30・18 / 30・27 / 30(旧 30 / 30)。64³ と (1, 256, 256) では 3 つとも全部当たる(旧は低域の切り出しで 0)。
さらに低い帯域(遮断 0.10)の 32³ はどれも 6 / 10 以下で、ここは苦しいまま。だから既定は Tukey(α 0.5)+ 0.25。
旧の挙動は ``window=None, whitening=1.0``(数値も同じ経路)。
- 循環相関なので、はみ出した部分は反対側から回り込む。シフトが volume の半分を超えると符号が反転して見える。
  窓つきの既定では、小さい volume(32³)の大きな周期的なずれ(辺の 2 割)で外すことがある(上の 27 / 30)—— 周期的なずれだと
  分かっているなら ``window=None, whitening=1.0``。
- 全 0 の volume は 0 になり index 0 を返す。
- 整数精度。サブボクセルは ``refine_translation_lk`` / ``refine_peak_newton`` へ。
- 回転・スケールがあると効かない(``match_logpolar_z`` → 回転補正 → 本 op の順)。
**Raises** ValueError: 形が違う、window の綴り違い、whitening が [0, 1] の外、torch の無い環境で device が cpu 以外。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [shape_desc_pose](../../../../examples_3d/shape_desc_pose.py) — `py -3.11 examples_3d/shape_desc_pose.py`

## 型が繋がる次の op(`shift` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`match_pose`)

[match_pca](match_pca.md) · [moment_axes](moment_axes.md) · [match_logpolar_z](match_logpolar_z.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
