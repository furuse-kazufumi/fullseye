# Academic gallery — attribution / 出典とライセンス

`academic_*.png` (tools/gen_academic_gallery.py 生成) の全素材の出典。
**「AI 生成」列が Yes の画像は OpenAI 画像生成モデルによる模擬データであり、実在の標本・スキャン・観測ではない。**
実データはすべて public domain / CC0 / CC-BY のみを使用。

| 画像 | 分野 | 素材 | AI 生成 | 出典 / ライセンス | 使用 op |
|---|---|---|---|---|---|
| `academic_space_carina.png` | 宇宙 | James Webb Space Telescope NIRCam Image of the “Cosmic Cliff | No | [STScI (Webb)](https://images.nasa.gov/details/carina_nebula) — Public domain (NASA) | rgb1_to_gray, cv_clahe, sk_frangi |
| `academic_space_galaxy.png` | 宇宙 | A galactic sunflower | No | [GSFC](https://images.nasa.gov/details/hubble-sees-a-galactic-sunflower_21136469209_o) — Public domain (NASA) | rgb1_to_gray, cv_clahe, cx_fft, cx_magnitude |
| `academic_space_mars.png` | 宇宙 | The Active Dunes of Nili Patera | No | [NASA/JPL-Caltech/Univ. of Arizona](https://images.nasa.gov/details/PIA18244) — Public domain (NASA) | rgb1_to_gray, std_filter, texture_laws |

生成日: 2026-08-30 / スクリプト: `tools/gen_academic_gallery.py`
