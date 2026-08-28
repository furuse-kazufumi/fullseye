# Fullseye サンプルデータ カタログ

op の動作確認・デバッグに使える**実在**のサンプルデータ源(DL URL / ライセンス / 取得法)。同梱はせず**ユーザー DL 方式**(`fullseye` の `sample_data` / `sample_images`)。fail-closed(未取得なら明示エラー、捏造しない)。

## 3-D / ボリューム(実 DL URL)

| id | 種別 | アクセス | 出典 / DL URL |
|----|------|----------|----------------|
| `triceratops` | mesh | direct | <https://3d-api.si.edu/content/document/3d_package:d8c623be-4ebc-11ea-b77f-2e728ce88125/resources/Triceratops_horridus_Marsh_1889-150k-4096.glb> |
| `bunny` | mesh | direct | <https://graphics.stanford.edu/pub/3Dscanrep/bunny.tar.gz> |
| `dragon` | mesh | direct | <https://graphics.stanford.edu/pub/3Dscanrep/dragon/dragon_recon.tar.gz> |
| `armadillo` | mesh | direct | <https://graphics.stanford.edu/pub/3Dscanrep/armadillo/Armadillo.ply.gz> |
| `itokawa` | mesh | info | <https://sbn.psi.edu/pds/resource/itokawashape.html> |
| `google-scanned` | mesh | info | <https://app.gazebosim.org/GoogleResearch/fuel/collections/Scanned%20Objects%20by%20Google%20Research> |
| `open-scivis` | volume | info | <https://klacansky.com/open-scivis-datasets/> |
| `mvtec-ad` | image | gated | <https://www.mvtec.com/company/research/datasets/mvtec-ad> |

取得: `py -3.11 -c "import sample_data; sample_data.download('bunny', yes=True)"` (`access=direct` のみ自動 DL、`gated`/`info` は出典ページから手動)。

## 2-D 画像(skimage.data(BSD/public)+ 合成)

| name | 出典 | ライセンス |
|------|------|-----------|
| `gradient` | synthetic (Fullseye) | own work |
| `blobs` | synthetic (Fullseye) | own work |
| `shapes` | synthetic (Fullseye) | own work |
| `checker_noisy` | synthetic (Fullseye) | own work |
| `coins` | skimage.data | BSD / public domain (see scikit-image) |
| `camera` | skimage.data | BSD / public domain (see scikit-image) |
| `page` | skimage.data | BSD / public domain (see scikit-image) |
| `cell` | skimage.data | BSD / public domain (see scikit-image) |
| `grain_synth` | synthesized (Fullseye synth.synthesize_like, 1/f grain (spectral synthesis)) | own work |
| `weave_synth` | synthesized (Fullseye synth.synthesize_like, fabric weave (spectral synthesis)) | own work |
| `brick_quilt` | synthesized (Fullseye synth.synthesize_like, brick wall, enlarged (image quilting)) | own work |

2-D は外部 DL 不要(`skimage.data` は pip 導入済、合成は自作)。`import sample_images; sample_images.load('<name>')` で取得。

---
© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
