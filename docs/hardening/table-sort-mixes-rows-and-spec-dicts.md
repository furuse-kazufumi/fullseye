---
id: table-sort-mixes-rows-and-spec-dicts
date: 2026-09-21
found_by: tools/chain_fuzz.py
kind: gate-gap
severity: medium
where: [optscene.py, fourierdesc.py, tools/chain_fuzz.py, ops1d.py, opsoptics.py]
ops: [camera_rays, covers_sensor, defocus_blur, diffraction_blur, from_xld, light_wavelengths, optscene_depth, random_defects, peak_subbin, register_light]
gate: [test_table_consumers_refuse_a_list_of_rows_with_the_op_name, test_a_wrong_kind_of_spec_is_refused_too, test_peak_subbin_and_register_light_ledger_out_match_what_they_return, test_nonfinite_allowlist_additions_are_documented_and_really_nonfinite, test_the_eight_suspect_replays_are_white_now]
status: fixed
---

# sort `table` が「行のリスト」と「諸元 dict」の両方を指し、消費 op が口ごもって落ちた

## 症状

連鎖ファザー(`tools/chain_fuzz.py --cover-all`、300 連鎖)の分類 164 件のうち、SUSPECT(契約の穴)8 件が同じ形だった: `vol_edge_probe` の返り(**行のリスト**)が pool の `table` に入り、次の op が `optical_camera` / `lens_spec` / `light_spec` の**dict**を待つ席に受け取る。`camera["K"]` は `TypeError: list indices must be integers or slices, not str`、`lens.get(...)` は `AttributeError: 'list' object has no attribute 'get'` —— 例外は出るが、どの op がどの入力を拒んだのかを言わない。型語彙 `table` は台帳全体で 207 か所に使われ、産む側は list-of-rows(`vol_edge_probe` / `region_props` / `glass_catalog` / `defect_dataset` / `copy_move_regions`)と dict(諸元・統計・設計)の両方がある。

同じ走査で NONFINITE 6 件(lens_system / example_system / bend_singlet / triangulate_column / m3c2_distance / piv_cross_correlate)と TYPEMISS 1 件(peak_subbin)も出た。

## なぜ門が通したか

* `table` を受ける 53 op のうち、raytrace・lensimage・illumdesign・flyvision・optics・gfx2d は専用ヘルパ(`_check_system` / `_check_light` / `_as_lattice` …)で dict を検査していたが、optscene の camera / lens / sensor / light / primitive を受ける 17 op と `fourierdesc.from_xld` は素で添字していた。
* NONFINITE 6 件は replay で全部「非有限が契約」だった: 処方 3 件は `object_mm = inf`(無限遠が既定値)という 1 つの inf、triangulate_column は未確定画素 = NaN、m3c2 は点不足 = nan、piv は峰の立たない窓 = nan(`valid_fraction` を併記)。fuzz の allowlist に無かっただけ。
* peak_subbin は台帳 out が `measurement` だが indices (k,) に対して (k,) を返す(scalar in / scalar out の設計はそのまま)。register_light は `table` 宣言で登録鍵の str を返す。

## 直し

* optscene に `_check_camera` / `_check_spec` / `_check_light_dict` / `_check_primitive` を置き、17 op の docstring 直後で呼ぶ(op 名 + 何を渡すべきかを言う ValueError)。`from_xld` も dict と `cs` と添字範囲を検査。
* chain_fuzz に `NONFINITE_BY_CONTRACT_PRESCRIPTION`(3)と `NONFINITE_BY_CONTRACT_MEASURE`(3)を理由つきで追加(集合を広げすぎると本物の NaN が隠れるので、載せた op は「実際に非有限を返す」ことも門で見る)。
* 台帳: peak_subbin の out を `signal`、register_light の out を `text` に。

## 残したこと

`table` を list-of-rows と dict に分ける(新語 `rows`)のは 207 か所の台帳と生成物に及ぶので今回は見送り、**消費側で止める**に留めた。混ぜると例外(もっともらしい誤答ではない)なので型を割る基準には達していないが、fuzz の述語が両方を通す限り同型の穴は他の族でも起こりうる —— 次に `table` を受ける op を足すときは、dict 前提なら最初の行で検査すること。
