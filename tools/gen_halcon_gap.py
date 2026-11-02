#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""HALCON 2605 の全 2,313 演算子を 4 分類した台帳を作る。

    py -3.11 tools/gen_halcon_gap.py           # 書き出す
    py -3.11 tools/gen_halcon_gap.py --check   # 差分があれば exit 1

分類(``klass``):

* ``covered``      対応あり。``surface`` が ``op`` なら索引(``docs/OP_INDEX.json``)の ``halcon`` 欄か
  台帳の表から引ける。``function`` はモジュール関数の対応(``halcon_facade_map.json``)だけで、op の
  公開面には無い。
* ``alias``        別の名前で実装済みで、2026-11-02 の棚卸しで対応付けを足した名前。
* ``to_build``     未実装で作るべき。``priority`` 1 が最も高い。
* ``out_of_scope`` 対象外。``reason`` は理由の符号。

★どの規則にも当たらない名前があると止まる。黙って対象外へ落とさないため。
★分類の表はこのファイルに書く。推測で埋めず、名前を 1 つずつ置いた。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

INDEX = ROOT / "docs" / "OP_INDEX.json"
STUBS = ROOT / "fullseye" / "data" / "halcon_stubs.json"
FACADE = ROOT / "fullseye" / "data" / "halcon_facade_map.json"
LEDGER = ROOT / "fullseye" / "data" / "halcon_ledger_map.json"
OUT_MD = ROOT / "docs" / "HALCON_GAP_2026-11-02.md"
OUT_JSON = ROOT / "docs" / "halcon_gap_2026-11-02.json"

#: 別名の実装(棚卸しで見つけ、対応表へ足した名前)→ 実体。
ALIASES = {
    "read_image": "api.read_image", "write_image": "api.write_image",
    "open_framegrabber": "acquire.open_framegrabber", "grab_image": "acquire.grab_image",
    "close_framegrabber": "acquire.close_framegrabber",
    "get_system": "fssystem.get_system", "set_system": "fssystem.set_system",
    "set_color": "drawstyle.set_color", "set_draw": "drawstyle.set_draw",
    "set_line_style": "drawstyle.set_line_style", "set_line_width": "drawstyle.set_line_width",
    "flush_buffer": "drawlist.flush_buffer",
    "tuple_mean": "mathops.stat_describe", "tuple_deviation": "mathops.stat_describe",
    "tuple_min": "mathops.stat_describe", "tuple_max": "mathops.stat_describe",
    "tuple_histo_range": "mathops.stat_histogram",
    "gen_contour_nurbs_xld": "op nurbs_curve", "train_variation_model": "op varmodel_fit",
}

#: 言語の機能で実装済み(FScript の語と Studio の dev_ 命令)。関数が無いので対応表へは足さない。
LANGUAGE = {
    "if": "fscript", "elseif": "fscript", "else": "fscript", "endif": "fscript", "for": "fscript",
    "endfor": "fscript", "while": "fscript", "endwhile": "fscript", "break": "fscript",
    "continue": "fscript", "return": "fscript", "assign": "fscript",
    "dev_set_draw": "studio", "dev_set_color": "studio", "dev_set_line_width": "studio",
    "dev_disp_text": "studio", "dev_display": "studio", "dev_open_window": "studio",
    "dev_close_window": "studio", "dev_clear_window": "studio", "dev_set_lut": "studio",
    "dev_set_part": "studio", "dev_set_window": "studio", "dev_set_window_extents": "studio",
    "dev_update_pc": "studio", "dev_update_time": "studio", "dev_update_var": "studio",
    "dev_update_window": "studio",
}

#: 作るべき演算子: 名前 → (優先度, 公開の出典か手法の要約)。
TO_BUILD = {
    # 優先度 1: 読み取りと検査の実用の口。既存の部品に近い。
    "find_data_code_2d": (1, "QR / Data Matrix の検出と復号(ISO/IEC 18004, 16022)"),
    "create_data_code_2d_model": (1, "2 次元コードの設定の入口"),
    "decode_bar_code_rectangle2": (1, "矩形の中の 1 次元コードの復号(既存の decode_barcode の入口違い)"),
    "find_text": (1, "文字領域の検出(textregion の部品で組む)"),
    "add_texture_inspection_model_image": (1, "テクスチャ検査の学習画像の追加"),
    "train_texture_inspection_model": (1, "ガボール特徴の良品分布の学習"),
    "prepare_variation_model": (1, "変動モデルの上下しきい値画像(varmodel の帯)"),
    "prepare_direct_variation_model": (1, "基準と分散の画像から変動モデルを作る"),
    "get_thresh_images_variation_model": (1, "上下しきい値画像の取り出し"),
    "get_variation_model": (1, "基準と分散の画像の取り出し"),
    "evaluate_class_mlp": (1, "MLP の出力の確率"),
    "evaluate_class_svm": (1, "SVM の判別値"),
    # 優先度 2: 手法は公開されているが、組み立てが大きい。
    "do_ocr_multi_class_mlp": (2, "字の特徴 + 分類器の OCR"), "do_ocr_multi_class_svm": (2, "同上"),
    "do_ocr_multi_class_knn": (2, "同上"), "do_ocr_single_class_mlp": (2, "同上"),
    "do_ocr_single_class_svm": (2, "同上"), "do_ocr_single_class_knn": (2, "同上"),
    "do_ocr_word_mlp": (2, "語の制約つき OCR"), "do_ocr_word_svm": (2, "同上"), "do_ocr_word_knn": (2, "同上"),
    "create_ocr_class_mlp": (2, "OCR 分類器の入口"), "create_ocr_class_svm": (2, "同上"),
    "create_ocr_class_knn": (2, "同上"), "trainf_ocr_class_mlp": (2, "字の学習"),
    "trainf_ocr_class_svm": (2, "同上"), "trainf_ocr_class_knn": (2, "同上"),
    "get_features_ocr_class_mlp": (2, "字の特徴"), "get_features_ocr_class_svm": (2, "同上"),
    "get_features_ocr_class_knn": (2, "同上"),
    "reduce_class_svm": (2, "支持ベクトルの削減"), "get_support_vector_class_svm": (2, "支持ベクトルの取り出し"),
    "get_support_vector_num_class_svm": (2, "同上"),
    "select_feature_set_gmm": (2, "特徴選択(前進選択)"), "select_feature_set_knn": (2, "同上"),
    "select_feature_set_mlp": (2, "同上"), "select_feature_set_svm": (2, "同上"),
    "create_class_lut_gmm": (2, "分類器から 3 次元 LUT を作る"), "create_class_lut_knn": (2, "同上"),
    "create_class_lut_mlp": (2, "同上"), "create_class_lut_svm": (2, "同上"),
    "add_samples_image_class_gmm": (2, "領域から学習標本を集める"), "add_samples_image_class_knn": (2, "同上"),
    "add_samples_image_class_mlp": (2, "同上"), "add_samples_image_class_svm": (2, "同上"),
    "create_component_model": (2, "部品の相対配置のモデル"), "create_trained_component_model": (2, "同上"),
    "find_component_model": (2, "部品の配置の探索"), "gen_initial_components": (2, "部品の初期分割"),
    "train_model_components": (2, "部品の学習"), "cluster_model_components": (2, "部品の統合"),
    "inspect_clustered_components": (2, "部品の統合の確認"),
    "set_fuzzy_measure": (2, "エッジ強度のファジィ所属関数"), "set_fuzzy_measure_norm_pair": (2, "同上(対の幅で正規化)"),
    "reset_fuzzy_measure": (2, "同上の解除"),
    "get_shape_model_clutter": (2, "形状モデルの雑然さの指標"), "set_shape_model_clutter": (2, "同上"),
    "add_deformable_surface_model_sample": (2, "変形面モデルの標本の追加"),
    "add_deformable_surface_model_reference_point": (2, "変形面モデルの基準点"),
    "set_profile_sheet_of_light": (2, "光切断のプロファイルの積み上げ"),
    "approx_chain": (2, "直線と円弧への折れ線近似(Rosin と West)"),
    "approx_chain_simple": (2, "同上の簡易版(gen_polygons_xld と重なる)"),
    "interjacent": (2, "領域の間の点の分類"),
    # 優先度 3: 需要が狭いか、定義の確認が要る。
    "combine_roads_xld": (3, "航空写真の道路の線と縁の統合"),
    "info_edges": (3, "フィルタ係数の情報"), "info_smooth": (3, "平滑の窓幅の情報"),
    "partition_lines": (3, "線分の属性での分割"), "select_lines": (3, "線分の属性での選択"),
    "select_lines_longest": (3, "最長の線分の選択"), "intersection_ll": (3, "線分の交点"),
    "expand_line": (3, "線の周りの領域の成長"), "hamming_change_region": (3, "領域のハミング変更"),
    "gen_struct_elements": (3, "旧来の構造要素の生成"), "fitting": (3, "旧来の形態学の適合"),
    "union_straight_contours_histo_xld": (3, "向きのヒストグラムによる直線の統合"),
    "get_region_index": (3, "座標の入る領域の番号"),
    "set_local_deformable_model_metric": (3, "変形モデルの距離の指定"),
    "set_planar_calib_deformable_model_metric": (3, "同上"), "set_planar_uncalib_deformable_model_metric": (3, "同上"),
    "set_shape_model_metric": (3, "形状モデルの極性の指定"), "train_generic_shape_model": (3, "汎用形状モデルの学習"),
    "traind_ocv_proj": (3, "射影による文字の検証"), "do_ocv_simple": (3, "同上"),
}

#: 章ごとの対象外の理由。
CHAPTER_REASON = {
    "Tuple": "language_data", "Control": "language_control", "Develop": "ide_environment",
    "System": "system_runtime", "File": "file_io", "Graphics": "gui_window",
    "Deep Learning": "dl_wrapper", "Image Source": "acquisition_device", "Object": "object_container",
}

#: 名前の形による対象外の理由(上から順に当てる)。
NAME_RULES = [
    (r"(^|_)(deep|dl)(_|$)|cnn", "dl_wrapper"),
    (r"^(clear|close)_", "handle_lifecycle"),
    (r"^(copy|remove)_(metrology|object_model_3d|calib)", "handle_lifecycle"),
    (r"^(de)?serialize_", "model_serialization"),
    (r"^(read|write|protect|append|concat)_", "model_file_io"),
    (r"^(get|set|query|info|reset)_", "model_parameter_getter_setter"),
    (r"^(add|create|apply|find|run|prepare|optimize)_scene", "gui_window"),
    (r"framegrabber|grab_", "acquisition_device"),
]

#: 名前の形で落ちない個別の対象外(Legacy の旧 API と、OCR の旧学習ファイル)。
INDIVIDUAL = {
    "dev_map_par": "ide_environment", "dev_map_prog": "ide_environment", "dev_map_var": "ide_environment",
    "dev_unmap_par": "ide_environment", "dev_unmap_prog": "ide_environment", "dev_unmap_var": "ide_environment",
    "disp_distribution": "gui_window", "disp_lut": "gui_window", "open_textwindow": "gui_window",
    "clear_rectangle": "gui_window", "move_rectangle": "gui_window", "ifelse": "language_control",
    "slide_image": "gui_window", "do_ocr_multi": "legacy_ocr", "do_ocr_single": "legacy_ocr",
    "create_ocr_class_box": "legacy_ocr", "traind_ocr_class_box": "legacy_ocr",
    "trainf_ocr_class_box": "legacy_ocr", "testd_ocr_class_box": "legacy_ocr",
    "ocr_change_char": "legacy_ocr", "ocr_get_features": "legacy_ocr",
    "create_text_model": "legacy_ocr", "create_text_model_reader": "legacy_ocr",
    "import_lexicon": "model_file_io", "inspect_lexicon": "model_parameter_getter_setter",
    "update_kalman": "model_file_io", "transform_metrology_object": "handle_lifecycle",
    "modify_component_relations": "model_parameter_getter_setter",
    "select_feature_set_trainf_knn": "legacy_ocr", "select_feature_set_trainf_mlp": "legacy_ocr",
    "select_feature_set_trainf_mlp_protected": "legacy_ocr", "select_feature_set_trainf_svm": "legacy_ocr",
    "select_feature_set_trainf_svm_protected": "legacy_ocr", "trainf_ocr_class_mlp_protected": "legacy_ocr",
    "trainf_ocr_class_svm_protected": "legacy_ocr", "reduce_ocr_class_svm": "legacy_ocr",
    "create_class_knn": "model_constructor", "create_class_gmm": "model_constructor",
    "create_class_mlp": "model_constructor", "create_class_svm": "model_constructor",
    "create_class_train_data": "model_constructor", "add_class_train_data_gmm": "model_constructor",
    "add_class_train_data_knn": "model_constructor", "add_class_train_data_mlp": "model_constructor",
    "add_class_train_data_svm": "model_constructor", "add_sample_class_gmm": "model_constructor",
    "add_sample_class_knn": "model_constructor", "add_sample_class_mlp": "model_constructor",
    "add_sample_class_svm": "model_constructor", "add_sample_class_train_data": "model_constructor",
    "select_sub_feature_class_train_data": "model_constructor",
    "create_bar_code_model": "model_constructor", "create_calib_data": "model_constructor",
    "create_camera_setup_model": "model_constructor", "remove_calib_data": "handle_lifecycle",
    "remove_texture_inspection_model_image": "handle_lifecycle",
    "open_scene_engine": "gui_window", "run_scene_engine": "gui_window",
    "reset_sheet_of_light_model": "handle_lifecycle",
    "copy_matrix": "language_data", "optimize_fft_speed": "system_runtime",
    "optimize_rft_speed": "system_runtime",
}

REASON_TEXT = {
    "language_data": "tuple と dict の言語機能。Python と numpy がそのまま担う",
    "language_control": "制御構文。Python と FScript の構文が担う",
    "ide_environment": "HDevelop の環境の操作",
    "system_runtime": "プロセス・スレッド・通信など実行環境の操作",
    "file_io": "ファイルの低水準操作。Python の標準の入出力が担う",
    "gui_window": "ウィンドウ表示と対話の描画。出力の描画は別の op が担う",
    "dl_wrapper": "深層学習の枠組みの包み。古典の視覚アルゴリズムの対象外",
    "acquisition_device": "取り込み機器の操作。acquire.Camera が担う",
    "object_container": "HObject の入れ物の操作。numpy の配列とリストが担う",
    "handle_lifecycle": "ハンドルの破棄と複製。Python のオブジェクトでは要らない",
    "model_serialization": "モデルの直列化。dict を保存すれば足りる",
    "model_file_io": "モデルのファイル入出力。dict を保存すれば足りる",
    "model_parameter_getter_setter": "ハンドルの引数の取得と設定。dict の鍵を読み書きすれば足りる",
    "model_constructor": "ハンドルへ標本を積む口。配列を 1 度に渡す形で不要",
    "legacy_ocr": "旧 OCR の学習ファイルと語彙の口。同じ働きは別の入口にある",
}


def classify(name, chapters, idx, facade, ledger_ops):
    """1 名を分類して dict を返す。どの規則にも当たらなければ ``None``。"""
    chapter = chapters[0] if chapters else "(unclassified)"
    row = {"name": name, "chapter": chapter}
    if name in ALIASES:
        return dict(row, klass="alias", target=ALIASES[name])
    if name in idx:
        return dict(row, klass="covered", surface="op", target=idx[name])
    if name in ledger_ops:
        return dict(row, klass="covered", surface="op", target=ledger_ops[name])
    if name in facade:
        return dict(row, klass="covered", surface="function", target=facade[name])
    if name in TO_BUILD:
        pri, note = TO_BUILD[name]
        return dict(row, klass="to_build", priority=pri, note=note)
    if name in LANGUAGE:
        return dict(row, klass="alias", target="language:" + LANGUAGE[name])
    if name in INDIVIDUAL:
        return dict(row, klass="out_of_scope", reason=INDIVIDUAL[name])
    for ch in chapters:
        if ch in CHAPTER_REASON:
            return dict(row, klass="out_of_scope", reason=CHAPTER_REASON[ch])
    for pattern, reason in NAME_RULES:
        if re.search(pattern, name):
            return dict(row, klass="out_of_scope", reason=reason)
    return None


def build():
    """台帳を組み立てる。規則に当たらない名前があれば SystemExit。"""
    ops = json.loads(INDEX.read_text(encoding="utf-8"))["ops"]
    stubs = json.loads(STUBS.read_text(encoding="utf-8"))["operators"]
    facade = {k: v for k, v in json.loads(FACADE.read_text(encoding="utf-8")).items() if not k.startswith("_")}
    ledger = {v: k for k, v in json.loads(LEDGER.read_text(encoding="utf-8")).items() if not k.startswith("_")}
    idx = {}
    for o in ops:
        if o.get("halcon"):
            idx.setdefault(o["halcon"], o["name"])
    # 表の綴りの誤りは「どの名前にも当たらない行」として黙って効かなくなるので、ここで止める。
    stale = sorted((set(ALIASES) | set(LANGUAGE) | set(TO_BUILD) | set(INDIVIDUAL)) - set(stubs))
    if stale:
        raise SystemExit("gen_halcon_gap: 実在しない名前が表にある: %s" % " ".join(stale))
    rows, unknown = [], []
    for name in sorted(stubs):
        got = classify(name, stubs[name].get("chapters") or [], idx, facade, ledger)
        if got is None:
            unknown.append(name)
        else:
            rows.append(got)
    if unknown:
        raise SystemExit("gen_halcon_gap: 規則に当たらない名前 %d 件: %s" % (len(unknown), " ".join(unknown)))
    return rows


def summarize(rows):
    """件数の表。"""
    klass = Counter(r["klass"] for r in rows)
    return {"total": len(rows), "classes": dict(sorted(klass.items())),
            "covered_surface": dict(sorted(Counter(r["surface"] for r in rows if r["klass"] == "covered").items())),
            "out_of_scope_reason": dict(sorted(Counter(r["reason"] for r in rows if r["klass"] == "out_of_scope").items())),
            "to_build_priority": {str(k): v for k, v in sorted(Counter(
                r["priority"] for r in rows if r["klass"] == "to_build").items())}}


def render_md(rows, summary):
    """人が読む版。"""
    c = summary["classes"]
    L = ["# HALCON 2605 の全 2,313 演算子の棚卸し(2026-11-02)", "",
         "名前の対応だけを整理した台帳で、機能や性能の比較ではない。機械可読版は "
         "`docs/halcon_gap_2026-11-02.json`。生成は `tools/gen_halcon_gap.py`。", "",
         "| 分類 | 件数 |", "|---|---:|",
         "| 対応あり(op の公開面) | %d |" % summary["covered_surface"].get("op", 0),
         "| 対応あり(モジュール関数のみ) | %d |" % summary["covered_surface"].get("function", 0),
         "| 別名で実装済み(対応付け漏れ) | %d |" % c.get("alias", 0),
         "| 未実装で作るべき | %d |" % c.get("to_build", 0),
         "| 対象外(理由つき) | %d |" % c.get("out_of_scope", 0),
         "| 合計 | %d |" % summary["total"], "",
         "「モジュール関数のみ」は実装があるが `fs.ledger` と索引からは引けない。`halcon_facade_map.json` の"
         "対応は名前と関数の実在だけを検査していて、意味の一致は確かめていない。今回 13 件を読み直すと "
         "5 件は意味が違った(下の節)。", "",
         "## 章ごとの内訳", "", "| 章 | 全体 | 対応あり | 別名 | 作るべき | 対象外 |", "|---|---:|---:|---:|---:|---:|"]
    chapters = sorted({r["chapter"] for r in rows})
    for ch in chapters:
        sub = [r for r in rows if r["chapter"] == ch]
        n = Counter(r["klass"] for r in sub)
        L.append("| %s | %d | %d | %d | %d | %d |" % (ch, len(sub), n["covered"], n["alias"], n["to_build"], n["out_of_scope"]))
    L += ["", "## 2026-08 の分類を読み直して変わったこと", "",
          "2026-08 の報告は未対応の残りを「ほぼ boilerplate」と分類した。名前を 1 つずつ見直すと、次は"
          "アルゴリズムの演算だった。", "",
          "- `points_lepetit` は学習型と書かれていたが、検出そのものは円周の比較で学習が要らない。実装した。",
          "- Legacy 章の `morph_skiz`、`morph_hat`、`opening_seg`、`thickening*`、`hit_or_miss_*` は教科書の"
          "形態学。実装した。",
          "- Tools 章の `create_bg_esti` の族はカルマン背景推定、Transformations 章の `get_circle_pose` は"
          "閉形式の姿勢、Classification 章の `train_class_gmm` などは標準の学習。実装した。", "",
          "## 優先度つきの残り", ""]
    for pri in (1, 2, 3):
        names = [r for r in rows if r["klass"] == "to_build" and r.get("priority") == pri]
        L += ["### 優先度 %d(%d 件)" % (pri, len(names)), ""]
        L += ["- `%s`(%s)— %s" % (r["name"], r["chapter"], r["note"]) for r in names]
        L.append("")
    L += ["## 対象外の理由", "", "| 符号 | 件数 | 理由 |", "|---|---:|---|"]
    for key, n in summary["out_of_scope_reason"].items():
        L.append("| `%s` | %d | %s |" % (key, n, REASON_TEXT[key]))
    L += ["", "## 意味が違っていた対応(2026-11-02 に直した)", "",
          "| 名前 | 以前の実体 | 直したこと |", "|---|---|---|",
          "| `map_image` | 灰色値の LUT | 幾何の写像の適用(`mvimage.map_image`)。LUT の関数は消した |",
          "| `image_to_world_plane` | 点の写像(校正族の op) | 画像の平行化を `rectify_to_world_plane` として足した |",
          "| `change_radial_distortion_image` | 多項式の歪み、カメラの引数なし | 除算モデルで 2 つのカメラの間を変換 |",
          "| `gray_projections` | 行と列の和 | 行と列の平均 |",
          "| `find_ncc_models` | 1 モデルの複数検出 | 複数モデルの同時探索(1 モデルの呼び方も残す) |",
          "", "比較に使った情報は演算子名と引数の形だけで、HALCON の出力とは比べていない。", ""]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    rows = build()
    summary = summarize(rows)
    assert summary["total"] == 2313, summary["total"]
    md = render_md(rows, summary)
    js = json.dumps({"summary": summary, "reasons": REASON_TEXT, "rows": rows}, ensure_ascii=False, indent=1) + "\n"
    if args.check:
        drift = [str(p) for p, text in ((OUT_MD, md), (OUT_JSON, js))
                 if not p.exists() or p.read_text(encoding="utf-8") != text]
        if drift:
            print("HALCON gap drift:", drift)
            return 1
        print("HALCON gap ok:", summary["classes"])
        return 0
    OUT_MD.write_text(md, encoding="utf-8", newline="\n")
    OUT_JSON.write_text(js, encoding="utf-8", newline="\n")
    print("wrote", OUT_MD.name, OUT_JSON.name, summary["classes"], summary["covered_surface"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
