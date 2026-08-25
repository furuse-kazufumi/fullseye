# -*- coding: utf-8 -*-
"""Assemble INSERT_MANIFEST.md from _manifest_entries.json."""
import json
import os

OUT = r"C:\dev\projects\onocollo-complete\docs\qiita\20260822_g1_evis\ops"
MAN = os.path.join(OUT, "_manifest_entries.json")

data = json.load(open(MAN, encoding="utf-8"))

# honest fix: gear row in geometry is wavy (off-centre) -> 部分成功
for e in data:
    if e["file"] == "fops_geometry.png" and "evaluation" in e:
        e["evaluation"] = [x.replace("AI 歯車: 歯列が直線状に展開(目視)→ 成功(目視)",
                                     "AI 歯車: 歯列は帯状に展開されるが自動中心推定のずれでうねりが残る(目視)→ 部分成功")
                           for x in e["evaluation"]]
json.dump(data, open(MAN, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# appendix-F order of the category headings
ORDER = ["Tools(82 op)", "Transformations(79 op)", "Image(59 op)", "Filters(58 op)",
         "edges(56 op)", "segmentation(54 op)", "smoothing(48 op)", "gray(40 op)",
         "XLD(35 op)", "geometry(28 op)", "Regions(26 op)", "contour(26 op)",
         "texture(21 op)", "frequency(19 op)", "Segmentation(14 op)", "restoration(12 op)",
         "arithmetic(10 op)", "augmentation(10 op)", "2D Metrology(8 op)", "Inspection(8 op)",
         "color(8 op)", "measure(8 op)", "1D Measuring(7 op)", "flow(7 op)", "detect(5 op)"]
key = {c: i for i, c in enumerate(ORDER)}
data.sort(key=lambda e: key.get(e["category"], 99))

L = []
L.append("# 付録 F 増強画像 — 挿入用マニフェスト\n")
L.append("生成日: 2026-08-23 / 生成: Fullseye(imgevolve)実処理、CPU のみ。")
L.append("全画像は実際に op を実行した出力(想像図なし)。幅 ~900px・400KB 以下・PNG。")
L.append("入力の出所 3 系統: **AI 生成(Gemini gemini-2.5-flash-image)** / **自前合成(真値つき)** / "
         "**定番・実画像(scikit-image 同梱、NASA パブリックドメイン、EHT CC BY 4.0)** — 各項に明記。\n")
L.append("**挿入方法**: 各カテゴリの `#### <カテゴリ見出し>` 直後(説明文の後・表の前)に画像+キャプションを挿入。")
L.append("「既存差し替え」の項は、当該見出し配下の既存 `opdemo_*.png` 画像行を本画像で置き換える。\n")
L.append("---\n")
for e in data:
    L.append(f"## {e['category']}\n")
    L.append(f"- **ファイル**: `{e['file']}`")
    L.append(f"- **区分**: {e.get('kind', '新規')}")
    L.append(f"- **キャプション案**: {e['caption']}")
    L.append(f"- **使用 op とパラメータ**: {e['ops']}")
    L.append(f"- **入力**: {e['inputs']}")
    L.append(f"- **パラメータ方針**: {e.get('params', '')}")
    if e.get("evaluation"):
        L.append("- **評価(op × 入力)**:")
        for line in e["evaluation"]:
            L.append(f"  - {line}")
    if e.get("verdict"):
        L.append(f"- **総合判定**: {e['verdict']}")
    elif e.get("result"):
        L.append(f"- **総合判定**: {e['result']}")
    L.append("")

L.append("---\n")
L.append("## 既存 11 枚の監査結果(同基準での点検)\n")
L.append("| 既存画像 | カテゴリ | 判定 | 理由 / 措置 |")
L.append("|---|---|---|---|")
L.append("| opdemo_14_watersheds.png | segmentation(54 op) | 差し替え | 接触物体の分離を実証していない(非接触コイン+分水嶺線のみ)→ `fops_segmentation.png` |")
L.append("| opdemo_04_canny.png | edges(56 op) | 差し替え | ノイズ下での NMS+ヒステリシスの優位性(核心主張)が見えない → `fops_edges.png` |")
L.append("| opdemo_01_gauss_image.png | Filters(58 op) | 差し替え | 入力にノイズが無く「ノイズをならす」を実証していない → `fops_filters.png` |")
L.append("| opdemo_08_fft_image.png | frequency(19 op) | 差し替え | スペクトル表示のみで課題解決なし → `fops_frequency.png`(縞ノイズ除去) |")
L.append("| opdemo_10_texture_laws.png | texture(21 op) | 差し替え | 「輝度では分離できない」対比なし → `fops_texture.png` |")
L.append("| opdemo_02_median_image.png | rank(23 op) | 合格(留保) | ノイズ入り入力で主張は成立。gauss との対比列があるとなお良い(第 2 陣候補) |")
L.append("| opdemo_05_threshold_label.png | region(76 op) | 合格 | ラベリングの主張を実証 |")
L.append("| opdemo_06_opening_circle.png | morphology(33 op) | 合格 | ノイズ付き二値入力で主張を実証 |")
L.append("| opdemo_12_radial_distortion.png | Calibration(34 op) | 合格 | 直線格子で歪みの主張を実証 |")
L.append("| opdemo_13_area_center.png | features(77 op) | 合格 | 計測値の重畳で実証 |")
L.append("| opdemo_16_depth_to_points.png | 3D Reconstruction(43 op) | 合格 | 深度→点群を実証 |")
L.append("")
L.append("## 入力素材の出所一覧\n")
L.append("- AI 生成(Gemini): parts_tray, gears, fruits, steel_balls, pcb, road, statue, bottle_caps, dark_workshop, "
         "chess_floor, beans_pile, cookies_tray, fundus_like, crack_concrete, dragonfly_wing, feather_macro, "
         "bga_xray_like, thin_section, leaf_veins, tree_rings, otolith, amber_ant, amber_mosquito, amber_beetle "
         "(保存先: `imgevolve/studio_assets/sample_sources_ai/`。Studio サンプル素材として再利用可)")
L.append("- 定番(scikit-image 同梱・再配布実績): camera, coins, page, moon, checkerboard, retina, hubble_deep_field(NASA/ESA)")
L.append("- 実画像: EHT M87*(EHT Collaboration, CC BY 4.0, Wikimedia 経由)/ 火星砂丘 PIA18244(NASA/JPL-Caltech, パブリックドメイン)")
L.append("- 同梱サンプル(imgevolve): blobs, weave_synth, brick_quilt, grain_synth ほか")
L.append("- 自前合成(真値つき): 接触ブロブ、低コントラスト図形、2 テクスチャ、等輝度色パッチ、HDR シーン、"
         "チェッカー射影(既知 H)、サブピクセル円/楕円、同心リング、ブリスターパック(欠陥注入)、BGA(ボイド注入)、弾道連番(dt 既知)")
L.append("")

open(os.path.join(OUT, "INSERT_MANIFEST.md"), "w", encoding="utf-8").write("\n".join(L))
print("INSERT_MANIFEST.md written,", len(data), "entries")
