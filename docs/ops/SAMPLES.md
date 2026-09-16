# Fullseye サンプルデータ カタログ

op の動作確認・デバッグに使える**実在**のサンプルデータ源(DL URL / ライセンス / 取得法)。同梱はせず**ユーザー DL 方式**(`fullseye` の `sample_data` / `sample_images`)。fail-closed(未取得なら明示エラー、捏造しない)。

## 3-D / ボリューム(実 DL URL)

| id | 種別 | ライセンス | 商用利用 | 成果公開 | アクセス | 出典 / DL URL |
|----|------|-----------|---------|---------|----------|----------------|
| `triceratops` | mesh | CC0-1.0 | 可 | 可 | direct | <https://3d-api.si.edu/content/document/3d_package:d8c623be-4ebc-11ea-b77f-2e728ce88125/resources/Triceratops_horridus_Marsh_1889-150k-4096.glb> |
| `bunny` | mesh | Stanford 3DSR (research courtesy) | 要確認 | 要確認 | direct | <https://graphics.stanford.edu/pub/3Dscanrep/bunny.tar.gz> |
| `dragon` | mesh | Stanford 3DSR (research courtesy) | 要確認 | 要確認 | direct | <https://graphics.stanford.edu/pub/3Dscanrep/dragon/dragon_recon.tar.gz> |
| `armadillo` | mesh | Stanford 3DSR (research courtesy) | 要確認 | 要確認 | direct | <https://graphics.stanford.edu/pub/3Dscanrep/armadillo/Armadillo.ply.gz> |
| `itokawa` | mesh | Public Domain (JAXA/NASA PDS) | 可 | 可 | info | <https://sbn.psi.edu/pds/resource/itokawashape.html> |
| `google-scanned` | mesh | CC-BY-4.0 | 可 | 可(要表示) | info | <https://app.gazebosim.org/GoogleResearch/fuel/collections/Scanned%20Objects%20by%20Google%20Research> |
| `open-scivis` | volume | per-dataset (see source) | 要確認 | 要確認 | info | <https://klacansky.com/open-scivis-datasets/> |
| `nist-thermography-calib` | reference | U.S. Government work (NIST publication) | 可 | 可 | info | <https://nvlpubs.nist.gov/nistpubs/ir/2016/NIST.IR.8098.pdf> |
| `nist-radiance-temperature` | reference | U.S. Government work (NIST publication) | 可 | 可 | info | <https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication250-43.pdf> |
| `nist-uncertainty-machine` | reference | U.S. Government work (NIST service) | 可 | 可 | info | <https://uncertainty.nist.gov/> |
| `nist-spectral-reflectance` | reference | U.S. Government work (NIST publication) | 可 | 可 | info | <https://tsapps.nist.gov/srmext/certificates/archives/2044a.pdf> |
| `middlebury-stereo` | image | research use (see source page) | 要確認 | 要確認 | info | <https://vision.middlebury.edu/stereo/data/> |
| `eth3d` | image | see source page | 要確認 | 要確認 | info | <https://www.eth3d.net/datasets> |
| `asf-sentinel1` | image | Copernicus open data (see source page) | 要確認 | 要確認 | info | <https://search.asf.alaska.edu/> |
| `gsi-kiban-dem` | volume | 国土地理院コンテンツ利用規約 (出典明示) | 要確認 | 要確認 | gated | <https://service.gsi.go.jp/kiban/app/map/> |
| `dicom-test-data` | volume | per-dataset (see source page) | 要確認 | 要確認 | info | <https://www.aliza-dicom-viewer.com/download/datasets> |
| `empiar` | volume | per-entry (mostly CC0/CC-BY; see entry) | 要確認 | 要確認 | info | <https://www.ebi.ac.uk/empiar/> |
| `rspid-piv` | image | see Zenodo record | 要確認 | 要確認 | info | <https://zenodo.org/records/7832205> |
| `mvtec-ad` | image | CC BY-NC-SA 4.0 (non-commercial) | **不可**(非商用のみ) | 非商用に限る | gated | <https://www.mvtec.com/company/research/datasets/mvtec-ad> |

**3 つの軸は別もの**: 「手元で使う」(アクセス)・「商用に使う」(商用利用)・「派生画像やモデルを外に出す」(成果公開)。**要確認** は「制限が無い」ではなく**こちらで条件を確認していない**という意味 —— 出典ページの規約を読んでから使ってください。成果公開はライセンス本文が言い切っているものだけ「可」にしてあり、それ以外は既定で要確認です。

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
