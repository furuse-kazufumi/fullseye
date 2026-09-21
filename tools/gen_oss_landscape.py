# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""既存 OSS の地図 ``docs/literature/OSS_LANDSCAPE.md`` を ``docs/literature/oss_landscape.json`` から描く。

ユーザー(2026-09-21)「既存の OSS も色々探ってみて」。文献層(知識 → op)の隣に「**すでにある道具 → Fullseye とどう繋ぐか**」を置く。
事実の列(名前・URL・ライセンス・最終 push・言語・一行説明)は JSON(GitHub API / 公式サイトで検証した調査結果、``verified`` と
``source`` つき)から機械的に描き、**分野ごとの「Fullseye との繋ぎ方」は人が書く**(``INTEROP``)。Fullseye は他の OSS のコードを
写さない(再実装のみ)ので、繋ぎ方はファイル形式・subprocess・optional import に限る。

    py -3.11 tools/gen_oss_landscape.py            # docs/literature/oss_landscape.json → OSS_LANDSCAPE.md

CHAIN に入れる(入力が repo 内にある)。JSON を直すのは調査した人の仕事で、この生成器は描くだけ。
"""
from __future__ import annotations

import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(_ROOT, "docs", "literature", "oss_landscape.json")
DST = os.path.join(_ROOT, "docs", "literature", "OSS_LANDSCAPE.md")

#: 分野(JSON の category に含まれる語で当てる)→ 見出しと、Fullseye との繋ぎ方(人が書く)
INTEROP: list[tuple[tuple[str, ...], str, str]] = [
    (("cad", "parametric", "implicit"), "CAD カーネル・パラメトリック / 陰関数モデリング",
     "B-rep(履歴つきの立体)は Fullseye の外 —— CadQuery / build123d / FreeCAD / OCCT で作り、**STL / 3MF に書き出して** `read_mesh` / `read_3mf` から "
     "`mesh_*` → `mesh_slice_*` → `gcode_*` → `print_layer_defect_map` へ繋ぐ。陰関数(SDF)側は Fullseye にも `box_sdf` / `sdf_union` などがあるので、"
     "libfive / fogleman の sdf と役割が重なる —— 違いは Fullseye が **検査(肉厚 `vol_wall_thickness`・連結性 `vol_euler_number`)と同じ語彙**で持つこと。"
     "Manifold は堅牢なブーリアンで、メッシュの前処理に subprocess / optional import で使える。"),
    (("mesh", "point cloud", "point-cloud"), "メッシュ・点群",
     "trimesh / Open3D / PCL / pymeshlab / MeshLib は Fullseye の `mesh_*`・3D 計測(`icp_point2plane`、`ransac_plane`、`fit_cone`)と機能が重なる。"
     "Fullseye 側の立ち位置は「numpy だけで動く・型の契約つき・真値で検証済み」。大規模点群の間引きや Poisson 再構成は Open3D に任せ、"
     "**PLY / OBJ / STL を介して** Fullseye の当てはめ・形状差(`chamfer_distance` / `hausdorff_distance`)へ渡すのが自然。"),
    (("slic", "3d printing", "g-code", "gcode", "3mf", "printing"), "スライサ・3D プリンタ・G-code・3MF",
     "本番のスライスは CuraEngine / PrusaSlicer / OrcaSlicer(いずれも AGPL)に任せ、Fullseye の `mesh_slice_contours` / `contours_to_gcode` は"
     "**検査用の期待像を作る最小スライサ**(層の面積が閉形式と一致する真値つき)。それらが出す G-code を `gcode_read` で読み、`gcode_layer_image` で"
     "期待像にし、OctoPrint / Obico のカメラ画像と `print_layer_defect_map` で突き合わせる、が繋ぎ方。lib3mf(BSD)は 3MF の正典で、Fullseye の "
     "`read_3mf` / `write_3mf` は stdlib(zip + XML)の最小実装 —— 拡張(スライス・ビーム格子)は lib3mf へ。Klipper / Marlin の方言は `;LAYER:` 等の"
     "コメントで層を切る(Marlin 仕様に層区切りは無い)。"),
    (("cam", "machining", "cnc"), "CAM・切削",
     "工具経路の生成は opencamlib / FreeCAD CAM / pycam の領域。Fullseye は G-code を **同じ語彙(`gcode_read` の表)で読む**ので、"
     "切削後の面を `roughness` 族(`profile_params` / `surface_psd`)や振動(`stft` / `spectral_kurtosis`)で評価し、経路と対応づける側。"),
    (("metrology", "inspection", "vision"), "計測・検査・ビジョン",
     "OpenCV / scikit-image は Fullseye の 2D op の多くと同じ古典手法(Fullseye はそれらを optional backend としても呼べる)。"
     "anomalib は学習ベースの異常検知で、Fullseye の `dc_rpca_sparse` / `null_distribution`(学習なし・誤報率つき)と**比較対象**。"
     "DICe / µDIC / OpenPIV は DIC / PIV の本格実装で、Fullseye の `piv_*` / `strain_from_displacement` は真値つきの最小版。"
     "TIGRE / ASTRA / tomopy は CT 再構成の本命(GPU)で、Fullseye の `filtered_backprojection` / `sart_reconstruct` は"
     "小さな検証と教材向け —— 大きな体積はこれらへ、アーチファクト補正(`beam_hardening_correct` / `ring_artifact_remove`)と"
     "空隙の計測(`vol_granulometry`)は Fullseye で。Kalibr はカメラ・IMU 校正の標準。"),
    (("robot", "mechatronic", "sensor"), "ロボット・メカトロ・センサ",
     "ROS 2 / MoveIt / Drake / MuJoCo は制御と計画で、Fullseye の外。繋ぎ目は**姿勢と点群**: Fullseye の `pnp_ransac` / `icp_point2plane` / "
     "`segment_rigid_motions` が出す姿勢・流れを ROS のメッセージに載せる(MCP / `comm` 経由)。OpenPnP は SMT の実機で、AOI(`ncc_locate` / "
     "`defect_contrast`)の相手。KISS-ICP / Cartographer は SLAM で、Fullseye の ICP は単発の位置合わせ。"),
    (("spc", "predictive", "signal", "maintenance"), "SPC・予知保全・信号",
     "Python に**保守されている SPC の定番は薄い**(調査結果を参照)—— Fullseye の `spc_*` 5 op(X̄-R / CUSUM / EWMA / Cp・Cpk / Hotelling T²)は"
     "閉形式で検証したもので、その空白を埋める。tsfresh / PyOD / river は特徴量・外れ値・オンライン学習で、`bearing_defect_frequencies` / "
     "`envelope_spectrum` の**後段**に置く。"),
    (("roughness", "surface texture"), "面粗さ・表面性状",
     "ISO 25178 のパラメータ群を実装する Python は surfalize(GPL)が唯一で、SurfaceTopography(MIT)は rms / PSD と計測器ファイルの読み込み、"
     "Gwyddion(GPL、C)は GUI の定番。Fullseye の `roughness` 族(`surface_filter` / `surface_form_remove` / `profile_params` / `surface_params` / "
     "`surface_psd`)は **permissive(Apache-2.0)で ISO 4287 / 25178 の基本量と ISO 16610 のガウスフィルタを閉形式で検証したもの**で、その空白に立つ。"
     "計測器の生ファイル(gwy / OPD / SDF)は SurfaceTopography や gwyfile で読み、高さ場(numpy)にして渡す。"),
    (("diagnosis", "motion magnification", "vibration"), "振動診断・動き拡大",
     "軸受診断(包絡スペクトル・BPFO/BPFI・次数追跡・kurtogram)の保守された permissive Python は見当たらず(調査結果)、Fullseye の `acoustics` 族"
     "(`bearing_defect_frequencies` / `envelope_spectrum` / `spectral_kurtosis` / `order_spectrum` / `angular_resample`)がその空白に立つ。endaq-python / pyOMA2 は"
     "PSD・衝撃・OMA で、後段に置ける。動き拡大(Eulerian / 位相)は実装が多いが permissive なものは数年放置・保守中は AGPL のみ → Fullseye の `motionmag` 族"
     "(線形 + Riesz / 位相、`motion_magnify` / `phase_displacement`)は「保守中・numpy-first」の位置。dToF / SPAD のヒストグラム → 深度も保守中ライブラリは未発見で、"
     "`photon` 族(`dtof_depth` / `spad_deadtime_correct` / `tcspc_*`)が持つ。FLIM の位相解析は PhasorPy(MIT)が充実しており、`lifetime_phasor` は最小版。"),
    (("fea", "simulation"), "FEA・シミュレーション",
     "CalculiX / FEniCSx / Elmer / OpenFOAM / code_aster は Fullseye の外。繋ぎ目は**実測との照合**: FEA の変位場と DIC(`strain_from_displacement`)の"
     "実測、CT(`vol_granulometry`)の空隙分布とモデルの仮定、を同じ格子で比べる。メッシュは STL / OBJ を介す。"),
    (("electronic", "protocol", "industrial", "plc"), "電子・産業プロトコル",
     "KiCad / ngspice は設計側、OpenPLC / open62541(OPC UA)/ pymodbus / EtherCAT master は制御・通信側で、どれも Fullseye の外。"
     "Fullseye の検査結果(Verdict・SPC の統計)を OPC UA / Modbus / MQTT に**載せる**のが繋ぎ目(`docs/CONNECTIVITY.md`、llmesh の産業 IoT)。"),
]

COPYLEFT = ("GPL", "AGPL", "LGPL", "EUPL", "CeCILL")


def _heading_for(category: str) -> tuple[str, str]:
    c = category.lower()
    for keys, head, text in INTEROP:
        if any(k in c for k in keys):
            return head, text
    return category, "(繋ぎ方は未記述 —— 調査結果を読んで足すこと)"


def render(entries: list[dict]) -> str:
    n_ver = sum(1 for e in entries if e.get("verified"))
    out = ["# 既存 OSS の地図 —— すでにある道具と、Fullseye との繋ぎ方\n",
           "<!-- generated by tools/gen_oss_landscape.py from docs/literature/oss_landscape.json; the interop prose lives in INTEROP inside the generator -->\n",
           "ユーザーの問い(2026-09-21)「既存の OSS も色々探ってみて」への答え。製造技術の周辺で**すでにある OSS** を分野ごとに並べ、"
           "Fullseye がそれと**どこで重なり、どこで繋ぐか**を書く。事実の列(ライセンス・最終 push・言語)は GitHub API か公式サイトで確かめた"
           "調査結果(`oss_landscape.json`、`verified` と `source` つき、**%d / %d 本が検証済み**)から描き、繋ぎ方の文は人が書く。"
           "Fullseye は他の OSS のコードを写さない(再実装のみ)ので、繋ぎ方は**ファイル形式・subprocess・optional import** に限る。"
           "ライセンス欄の GPL / AGPL / LGPL は copyleft —— Apache-2.0 の Fullseye はそれらと**リンクせず**、形式とプロセス境界で繋ぐ。\n" % (n_ver, len(entries))]
    by: dict[str, list[dict]] = {}
    order: list[str] = []
    for e in entries:
        head, _ = _heading_for(e.get("category", ""))
        if head not in by:
            by[head] = []
            order.append(head)
        by[head].append(e)
    out.append("## 目次\n")
    for head in order:
        out.append("- %s(%d 本)" % (head, len(by[head])))
    out.append("")
    for head in order:
        _, text = _heading_for(by[head][0].get("category", ""))
        out.append("## %s\n" % head)
        out.append("**Fullseye との繋ぎ方**: %s\n" % text)
        out.append("| OSS | ライセンス | 最終 push | 言語 | 何をするか | 検証 |")
        out.append("|---|---|---|---|---|---|")
        for e in sorted(by[head], key=lambda x: x.get("name", "").lower()):
            lic = e.get("license") or "?"
            mark = " ⚠copyleft" if any(k in lic.upper() for k in COPYLEFT) else ""
            ver = "✓" if e.get("verified") else "未検証"
            out.append("| [%s](%s) | %s%s | %s | %s | %s | %s |" % (
                e.get("name", "?"), e.get("url", ""), lic, mark, (e.get("pushed_at") or "")[:10] or "—", e.get("language") or "—",
                (e.get("what") or "").replace("|", "/"), ver))
        out.append("")
    out.append("## 読み方\n")
    out.append("- **重なる**ところ(メッシュ処理・古典 2D・CT 再構成・DIC)は、Fullseye の側が「numpy だけ・型の契約・真値で検証・検査の語彙」で、"
               "本格実装は OSS に任せて**結果を受け取る**。\n- **Fullseye の外**(B-rep CAD・制御・FEA・通信)は形式(STL / 3MF / G-code / PLY)と"
               "プロセス境界で繋ぐ。\n- **空白**(保守された Python の SPC、面粗さのパラメータ、溶接ビード検査、層カメラの印刷検査)は Fullseye が持つ。"
               "詳しくは調査ノート `oss_landscape_notes.md` の「gaps」。\n")
    return "\n".join(out) + "\n"


def main() -> int:
    if not os.path.isfile(SRC):
        raise SystemExit("missing %s — run the survey first (fail-closed: not writing an empty landscape)" % SRC)
    entries = json.load(open(SRC, encoding="utf-8"))
    if not isinstance(entries, list) or len(entries) < 20:
        raise SystemExit("oss_landscape.json must be a list of >= 20 entries, got %r" % (len(entries) if isinstance(entries, list) else type(entries)))
    for e in entries:
        for k in ("category", "name", "url", "license", "verified", "what"):
            if k not in e:
                raise SystemExit("entry %r lacks %r (fail-closed)" % (e.get("name"), k))
    with open(DST, "w", encoding="utf-8", newline="\n") as f:
        f.write(render(entries))
    print("oss landscape: %d entries (%d verified) -> %s" % (len(entries), sum(1 for e in entries if e.get("verified")), os.path.relpath(DST, _ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
