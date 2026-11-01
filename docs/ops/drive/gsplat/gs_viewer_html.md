---
op: gs_viewer_html
dim: drive
category: gsplat
in: table
out: table
gpu: なし
examples: [gsplat_product_viewer, gsplat_trained_product]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# gs_viewer_html — DRIVE `gsplat` op

- **データ種**: `table` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.gs_viewer_html(gs, out_path=None, *, title='3D Gaussian Splatting', lang=('ja', 'en', 'zh', 'tw', 'ko', 'de', 'hi', 'fr'), note=None, hotspots=None, dims=True, unit_mm: 'float' = 1000.0, up=(0.0, 0.0, 1.0), bg: 'str' = 'gray', max_bytes: 'int' = 16777216, fov_deg: 'float' = 35.0, camera=None, spin: 'bool' = True, spin_deg_per_s: 'float' = 20.0, bake_light=(0.3, -0.5, 0.8), ambient: 'float' = 0.35, max_radius: 'int' = 64, mobile_quality=0.5, mobile_above: 'int' = 300000) -> 'dict'` (実装を直接呼ぶなら `import gsviewer; gsviewer.gs_viewer_html(gs, out_path=None, *, title='3D Gaussian Splatting', lang=('ja', 'en', 'zh', 'tw', 'ko', 'de', 'hi', 'fr'), note=None, hotspots=None, dims=True, unit_mm: 'float' = 1000.0, up=(0.0, 0.0, 1.0), bg: 'str' = 'gray', max_bytes: 'int' = 16777216, fov_deg: 'float' = 35.0, camera=None, spin: 'bool' = True, spin_deg_per_s: 'float' = 20.0, bake_light=(0.3, -0.5, 0.8), ambient: 'float' = 0.35, max_radius: 'int' = 64, mobile_quality=0.5, mobile_above: 'int' = 300000) -> 'dict'`、台帳から引くなら `opsdrive.get("gs_viewer_html")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

3DGS を、ブラウザで回して見られる1 枚で完結する HTML にする(外部 URL 0・CDN 無し・オフラインで動く)。

データは位置 3×u16(軸ごとの範囲)・log 大きさ 3×u16・四元数 4×u8・RGBA 4×u8 = 1 個 20 バイトに量子化し、
gzip → base64 でページに埋める。ブラウザは ``DecompressionStream('gzip')`` で伸ばし、WebGL2 のインスタンス化した
四角形で描く。2-D 共分散は :func:`gsplatnp.gs_render` と同じ Σ' = J W Σ Wᵀ Jᵀ + 0.3 px²(不透明度は
√(det Σ / det(Σ + 0.3 I)) 倍)、窓は中心の丸めから ±⌈3√λ_max⌉ 画素(≤ ``max_radius``)、手前から
C = Σ c_i α_i T_i(半精度の浮動小数のバッファに足してから背景を合成)。前後の並べ替えは Web Worker が
視点の変わったときだけ行う(ガウシアンの中心の深さを 16 bit の桶で数える)。

商品の閲覧の機能: ドラッグで回す(慣性つき)・ホイール / ピンチで拡大・自動の回転台(触ると止まる)・視点のプリセット
(正面 / 側面 / 上 / 斜め)・背景(白 / 灰 / 黒)・注記点(押すと説明が開く、8 言語)・寸法(W × D × H mm)・
不透明度のしきい値・品質つまみ(ガウシアンの数を重要度の高い順に減らす、スマホの既定 ``mobile_quality``)。
URL でも開ける: ``?lang=en&bg=white&view=front&dims=1&hs=0&spin=0&quality=0.5``。

Parameters
----------
gs : dict または パス
    :func:`gsplatnp.gs_read_file` / :func:`gsplatnp.gs_from_world` の dict、または .ply / .splat のパス。
out_path : str または None
    書き出す先。None なら書かずに返り値の ``html`` に入れる。
title, note : str または {lang: str}
    題と、ページの「この表示について」に出す注記(例: 「メッシュから初期化した 3DGS で、写真から学習したものではない」)。
lang : str または 言語の並び
    ``LANGS``(ja, en, zh, tw, ko, de, hi, fr)の部分集合。先頭が既定、``?lang`` と navigator.language で選ぶ。
hotspots : [{"pos": (x, y, z), "label": str|{lang}, "desc": str|{lang}}]
    注記点。辞書で渡すなら要求した言語が全部要る(黙って補わない)。
dims : bool または {"upright", "obb"}
    寸法を出すか。True = ``"upright"``(上向きを H に固定した最小の箱)、``"obb"`` = 向き自由の最小体積の箱。
    どちらも向きは :func:`measure3d.smallest_box3` が決め、大きさは全部の不透明なガウシアンの中心で測る。
unit_mm : float
    座標の 1 単位が何 mm か(既定 1000 = メートル)。
up : (3,)
    上向きの軸(回転台の軸、寸法の H)。
bg : {"white", "gray", "black"}
    最初の背景。
max_bytes : int
    埋め込むデータの上限(base64 後のバイト数、既定 16 MB)。超えたら不透明度・大きさの小さい順に間引く。
fov_deg, camera, spin, spin_deg_per_s :
    縦の画角・最初の視点(``{"yaw", "pitch", "dist", "target"}`` の一部でよい)・回転台を回して開くか・その速さ。
bake_light, ambient :
    gs_from_world の dict のとき、世界の座標の光で陰影を色へ焼き込む(gs_render と同じ Lambert)。None で焼かない。
max_radius : int
    1 個の窓の半径の上限(画素、gs_render の ``max_radius`` と同じ意味)。
mobile_quality, mobile_above : float または None, int
    指で触る端末(``pointer: coarse``)で、ガウシアンが ``mobile_above`` 個を超えるときに最初に描く割合。
    None なら全部。品質つまみは重要度の順(間引きと同じ順)の先頭から描くので、小さな部品から消える。

Returns
-------
dict
    ``path``・``bytes``(HTML の大きさ)・``n_input``・``n_kept``・``n_dropped``・``thinned``・``thinning``(間引きの記録)・
    ``dims_mm``(W, D, H)・``dims``(箱の 8 隅つき)・``camera``・``sh_degree_in``・``sh_degree_used``(= 0)・
    ``sh_dropped``・``embedded_bytes``・``external_urls``(= 0 を確かめた数)。``out_path`` が None なら ``html`` も。

Raises
------
ValueError
    gs が空・形が合わない・非有限、未対応の言語、文言の言語の欠け、bg が 3 色以外、上限に 1 個も入らない。

空の入力(``gs`` が空の dict)は ValueError。

Examples
--------
>>> import gsplatnp, gsviewer
>>> r = gsviewer.gs_viewer_html("scene.ply", "view.html", title="My product")    # doctest: +SKIP
>>> r["n_kept"], r["dims_mm"]                                                    # doctest: +SKIP

CLI: ``py -3.11 -m gsviewer in.ply --out view.html --title "My product"``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [gsplat_product_viewer](../../../../examples/gsplat_product_viewer.py) — `py -3.11 examples/gsplat_product_viewer.py`
- [gsplat_trained_product](../../../../examples/gsplat_trained_product.py) — `py -3.11 examples/gsplat_trained_product.py`

## 型が繋がる次の op(`table` を入力に取れる)

[course_layout](../course/course_layout.md) · [course_occupancy](../course/course_occupancy.md) · [course_contains](../course/course_contains.md) · [world_build](../world/world_build.md) · [world_camera](../world/world_camera.md) · [world_move](../world/world_move.md) · [lidar_scan](../lidar/lidar_scan.md) · [rss_longitudinal_same](../rss/rss_longitudinal_same.md)

## 同カテゴリ(`gsplat`)

[gs_from_world](gs_from_world.md) · [gs_update](gs_update.md) · [gs_render](gs_render.md) · [gs_render_fn](gs_render_fn.md) · [gs_read_file](gs_read_file.md) · [gs_catalog_html](gs_catalog_html.md)

---
*Provenance: gsviewer.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
