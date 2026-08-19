# Fullseye 3DGS ― 使い方(1コマンド)

MuJoCo の sim シーンを **3D Gaussian Splatting** にして、全周ぐるぐる回せる GIF と新規視点画像を作ります。カメラ姿勢は sim の真値を使うので **COLMAP 不要**。

## いちばん簡単な使い方

imgevolve フォルダで:

```bat
3dgs go2 --open
```

これだけで go2(四足ロボ)を 3DGS 化し、完成した全周 GIF を自動で開きます。

- シーンを変える: `3dgs cassie` / `3dgs apollo` / `3dgs anymal` / `3dgs spot`
- 自分の MJCF: `3dgs C:\path\to\scene.xml`
- 一覧を見る: `3dgs --list`

## 品質プリセット

```bat
3dgs go2 --quality fast       :: 128px / 8千ガウシアン(数秒、下見向け)
3dgs go2 --quality balanced   :: 256px / 2万ガウシアン(既定)
3dgs go2 --quality high       :: 384px / 4.5万ガウシアン(いちばん綺麗)
```

## もっと綺麗に(densify)

```bat
3dgs go2 --quality high --densify --open
```

`--densify` を付けると、学習中に**ガウシアンを自動で増やして細部を上げます**(native gsplat 時のみ)。go2 で 8千 → 5万個ほどに成長し、胴体・脚がより滑らかに。数秒〜十数秒で完了します。

## backend は自動

- **native gsplat**(タイル CUDA)が使えれば自動でそれ(高速・高精細、数百 it/s)
- 無ければ **純 PyTorch** に自動フォールバック(遅いが動く)
- `--backend torch` / `--backend gsplat` で明示指定も可

環境(CUDA/コンパイラ)は launcher が自動設定するので、vcvars 等を意識する必要はありません。

## Studio から

`spikes/studio_app.py` を起動 →「sim モデルを 3D で見る / 3DGS 化」パネルで、
シーン名(チップをクリック or 入力)+ 品質を選び「3DGS 学習 🎇」→ 完了で全周 GIF が開きます。

## 出力

`out/3dgs_<scene>/`(または `--out` 指定先)に:
- `turntable.gif` … 全周プレビュー
- `novelview.png` … 左=正解 / 右=新規視点レンダ
- `gaussians.npz` … 学習済みガウシアン(npz)
- `gaussians.ply` … 3DGS 標準 .ply(native 時)。**SuperSplat 等の Web ビューアにドラッグ&ドロップ**で開けます
- `report.json` … PSNR 等の指標

## 必要環境

- GPU 学習用 venv `.venv-gsplat`(torch cu128)
- native を使うなら `.gsplat-cuda`(CUDA 12.8)+ VS BuildTools の C++ ツール。詳細と再現手順は `docs/GSPLAT_NATIVE_WINDOWS.md`

> honest な注記: `--densify` の効き目はシーン依存です。go2 のような塊は綺麗になりますが、cassie のような細い二足では学習視点に過学習して hold-out がやや softになることがあります。まずは付けずに試し、物足りなければ付けるのがおすすめです。

## 動く姿を再生する(--motion)

```bat
3dgs go2 --motion --open
```

静止ではなく、**動くロボットの 3DGS** を作ります。仕組み:
1. 正準ポーズで 3DGS 学習
2. 各ガウシアンが MuJoCo のどの body(リンク)由来かを **segmentation** で確定してリグ付け
3. 関節を動かし(既定=サイン波)、各フレームの body 姿勢(sim の真値)で剛体スキニング→再描画→`motion.gif`

ロボットは剛体リンクの集合なので、フル 4D-GS を使わず自然に動かせます。`--frames N` でコマ数を変更。

> honest: 既定の動きはデモ用のサイン波(実際の歩行方策ではありません)。sim の姿勢が真値なので破綻はしませんが、足先付近に軽いノイズが出ることがあります(初期化点の body 帰属の境界)。

### 歩容(gait)を自動生成

```bat
3dgs go2 --motion --gait trot --open
```

`--gait trot` で **四足のトロット歩容**(対角脚を同位相で踏み替え)を自動生成して再生します。関節名(FL/FR/RL/RR または LF/RF/LH/RH + thigh/calf)から脚を自動検出するので、go2 や anymal で動きます。検出できないモデルはサイン波にフォールバック。実際の歩行方策の出力を使うなら `--motion-file traj.npy`(qpos 軌道 (F,nq))。
