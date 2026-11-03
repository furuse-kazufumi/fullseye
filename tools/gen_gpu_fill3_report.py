#!/usr/bin/env python3
"""GPU 第 3 便の採否表 ``docs/perf/gpu_fill3_2026-11-02.md`` を実測ログと実装台帳から生成する。

入力は ``docs/perf/logs/fill3_{cpu,gpu}_{2d,nary,typed,parity}.json``(``tools/gpu_fill3_bench.py``)と
``accel`` / ``accel_typed`` の実装台帳、対応率は生成物 ``docs/perf/halcon_opencl_parity.json`` と
``docs/perf/GPU_TIERS.md``。数字を手で書かない。採否の規則:

* parity(CPU torch と GPU の両方)< 5e-3、かつ実寸の倍率 >= 5.0x なら採用。
* 計算核を書かない op は ``NOT_PORTED`` の理由を出す。不採用も行を消さない。
* 実装台帳の採用集合と規則の結論が食い違ったら exit 1(手で水増しできない)。

    py -3.11 tools/gen_gpu_fill3_report.py          # 書く
    py -3.11 tools/gen_gpu_fill3_report.py --check  # drift と食い違いの検査
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "docs" / "perf" / "logs"
OUT_MD = ROOT / "docs" / "perf" / "gpu_fill3_2026-11-02.md"
OUT_JSON = ROOT / "docs" / "perf" / "gpu_fill3_decisions.json"
THRESHOLD = 5.0
TOL = 5e-3
#: 第 2 便(be943a01b7)時点の値。after は生成物から読むので、before だけを定数で持つ。
BEFORE = {"n2": 23, "have_gpu": 108, "denom": 2127}

#: HALCON の「対応あり・GPU 経路なし」48 件 -> 計測する Fullseye op(N-ary は @ 付きの形も)
HALCON_48 = {
    "abs_diff_image": ["abs_diff_image"], "abs_image": ["abs_image"], "acos_image": ["acos_image"],
    "add_image": ["add_image"], "affine_trans_image": ["affine_trans_image", "affine_warp"],
    "affine_trans_image_size": ["affine_trans_image_size"], "asin_image": ["asin_image"],
    "atan_image": ["atan_image"], "cfa_to_rgb": ["cfa_to_rgb"],
    "convol_image": ["convol_image@9x9", "convol_image@31x31"], "derivate_gauss": ["derivate_gauss"],
    "div_image": ["div_image"], "edges_sub_pix": [], "exp_image": ["exp_image"], "gamma_image": ["gamma_image"],
    "linear_trans_color": ["linear_trans_color"], "lines_gauss": [], "log_image": ["log_image"],
    "lut_trans": ["f2_lut_trans"], "max_image": ["max_image"], "median_rect": ["median_rect"],
    "min_image": ["min_image"], "mirror_image": ["mirror_image"], "mult_image": ["mult_image"],
    "polar_trans_image_ext": ["polar_trans_image_ext"], "polar_trans_image_inv": ["polar_trans_image_inv"],
    "principal_comp": ["principal_comp"], "rgb1_to_gray": ["rgb1_to_gray"], "rgb3_to_gray": ["rgb3_to_gray"],
    "rotate_image": ["rotate_image", "rotate_img"], "sin_image": ["sin_image"], "sqrt_image": ["sqrt_image"],
    "sub_image": ["sub_image"], "tan_image": ["tan_image"], "texture_laws": ["texture_laws"],
    "trans_from_rgb": ["trans_from_rgb"], "trans_to_rgb": ["trans_to_rgb"],
    "zoom_image_factor": ["rescale_img", "zoom_image_factor"], "zoom_image_size": ["zoom_image_size"],
    "convert_image_type": ["it_convert_image_type"], "crop_domain": ["it_crop_domain"],
    "crop_part": ["it_crop_part"], "crop_rectangle1": ["it_crop_rectangle1"],
    "polar_trans_image": ["polar_trans_image"], "gray_closing_shape": ["gray_closing_shape"],
    "gray_dilation_shape": ["gray_dilation_shape"], "gray_erosion_shape": ["gray_erosion_shape"],
    "gray_opening_shape": ["gray_opening_shape"],
}

#: 計算核を書かなかった op と理由(コードを読んだ事実だけを書く)
NOT_PORTED = {
    # HALCON 48
    "cfa_to_rgb": "包み: 本体は cv2.cvtColor の Bayer 補間(8 bit 経由)",
    "trans_from_rgb": "包み: 本体は cv2.cvtColor(8 bit、Lab/XYZ は OpenCV の固定小数点表)",
    "trans_to_rgb": "包み: 本体は cv2.cvtColor(HSV2RGB、8 bit)",
    "polar_trans_image": "包み: 本体は cv2.warpPolar(座標を 1/32 画素へ丸める固定小数点)",
    "polar_trans_image_ext": "包み: 本体は cv2.warpPolar(polar_trans_image と同じ)",
    "polar_trans_image_inv": "包み: 本体は cv2.warpPolar + WARP_INVERSE_MAP",
    "edges_sub_pix": "出力が可変長の輪郭点列(画素一致の parity が定義できない。前段の勾配だけ GPU にしても点列化が CPU に残る)",
    "lines_gauss": "出力が可変長の輪郭点列。別名の sk_frangi / sk_hessian / sk_meijering は scikit-image の包み",
    # required 名簿
    "tm_radon_forward": "包み: 本体は skimage.transform.radon(in-house の `radon_transform` は別実装で値が違う)",
    "tm_fbp_reconstruct": "包み: 本体は skimage.transform.iradon",
    "tm_sart_reconstruct": "包み: 本体は skimage.transform.iradon_sart",
    "sk_nlm": "包み: 本体は skimage.restoration.denoise_nl_means(計算量は大きいので次便の自前実装候補)",
    "cv_nlmeans": "包み: 本体は cv2.fastNlMeansDenoising(8 bit、整数距離表)",
    "cv_bilateral": "包み: 本体は cv2.bilateralFilter(実測の CPU 秒は下の補足表)",
    "bilateral_filter": "包み: 本体は cv2.bilateralFilter(実測の CPU 秒は下の補足表)",
    "render_optscene_gi": "未着手: 入出力が table のシーン記述で、放射度の反復と可視判定が Python 分岐に絡む。parity の基準場面の設計から要る",
    "render_optscene": "未着手: 入力がシーン記述で、材質ごとの分岐が多い。基準場面の設計から要る",
    "render_transport": "未着手: 投影パターン積は pointwise だが、入口が光輸送行列 table。実寸の行列の用意が要る",
    "transport_matrix_radiosity": "未着手: 密行列の解法(GPU 向き)だが実寸の場面定義が未定",
    "gs_render": "未着手: gsplatnp は numpy の深度順合成で、torch 版 gsplat_torch は別 API・別入力。parity の対応づけが未確認",
    "gs_render_fn": "未着手: gs_render の閉包を返す op(gs_render と同時でないと意味がない)",
    "gs_from_world": "計算が小さい前処理(面にガウシアンを貼る)。GPU 必須の名簿に居る根拠が弱い。名簿の見直し候補",
    "gs_update": "計算が小さい更新式(einsum 1 回)。GPU 必須の名簿に居る根拠が弱い。名簿の見直し候補",
    "photometric_stereo_robust": "未着手: 3 灯部分集合ごとの逐次解 + 中央値/合意。バッチ解は書けるが便の範囲外",
    "icp_point2point_3d": "未着手: 再現性のため _oz.matmul_reproducible(和の順序固定)を使う。float 和の順序が違う GPU とは設計上ぶつかる",
    "icp_point2plane": "未着手: icp_point2point_3d と同じく再現性の固定和を使う",
    "gicp": "未着手: 同じ再現性の固定和 + KD 木の最近傍",
    "register_fpfh": "未着手: KD 木の特徴一致と RANSAC の組で、乱数列まで一致させる parity が要る",
    "register_cpd_rigid": "未着手: 全点対距離の EM は GPU 向きだが便の範囲外",
    "fuse_to_voxel": "未登録のまま: 中身は `points_to_voxel`(第 3 便で測定)を呼ぶ。入力は any で parity の定型入力を決めていない",
    "physarum_transport_image": "未着手: 格子グラフの疎行列解。torch に scipy の疎直接法と一致する解法が無い",
    "physarum_route": "未着手: `_run` は device を受けるが密行列解で、実寸の格子は n^2 × n^2 の密行列が VRAM を超える",
    "graph_physarum_transport": "未着手: 公開 op に device 引数が無い(`_run` 経由の密行列解)。parity 未確認",
    "graph_physarum_path": "未着手: 公開 op に device 引数が無い(`_run` 経由の密行列解)。parity 未確認",
    "robust_gaussian_surface": "未着手: IRLS の畳み込み反復は GPU 向きだが便の範囲外",
    "robust_spline_profile": "原理的に CPU 向き: 本体は帯行列の直接解(linalg.solve_banded)の反復",
    "focus_sweep_surface_video": "未着手: 高さ推定 + 描画の複合 op。部品ごとの計測が要る",
    "solid_angle_sweep": "計算が小さい走査(Python ループ + 数式)。GPU 必須の名簿に居る根拠が弱い。名簿の見直し候補",
    "optical_flow_magnitude_stream": "未着手: 本体は flow.optical_flow_lk のピラミッド LK。stateful な stream の分解が要る",
}

REQUIRED_MEASURED = ("radon_transform", "radon_volume", "backproject_sinogram", "filtered_backprojection",
                     "fbp_volume", "sart_reconstruct", "piv_cross_correlate", "piv_multipass",
                     "piv_ensemble_correlate", "plane_sweep_depth", "joint_bilateral", "temporal_bilateral",
                     "voxel_grid_downsample", "occupancy_grid", "photometric_stereo", "points_to_voxel",
                     "scene_flow_lk")


def _load(mode, stage):
    p = LOG / ("fill3_%s_%s.json" % (mode, stage))
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"rows": {}}


def _row(name, cpu2, gpu2, cpun, gpun, cput, gput, pc, pg):
    """1 op の測定を引き、(ratio, cpu_s, gpu_s, parity_cpu, parity_gpu, 寸法) を返す。"""
    if name in cput or name in gput:
        c, g = cput.get(name, {}), gput.get(name, {})
        cs, gs, size = c.get("cpu_s"), g.get("gpu_s"), c.get("desc") or g.get("desc") or "?"
    else:
        src_c, src_g = (cpun, gpun) if name in cpun or name in gpun else (cpu2, gpu2)
        c, g = src_c.get(name, {}).get("2048", {}), src_g.get(name, {}).get("2048", {})
        cs, gs, size = c.get("cpu_s"), g.get("gpu_s"), "2048² x50"
    ratio = cs / gs if cs and gs else None
    return ratio, cs, gs, pc.get(name, {}).get("inner"), pg.get(name, {}).get("inner"), size


def _decide(ratio, pc, pg):
    if ratio is None or pc is None or pg is None:
        return "測定不能", "GPU 実測なし(測れていない)"
    if max(pc, pg) >= TOL:
        return "不採用", "parity %.1e >= 5e-3" % max(pc, pg)
    if ratio < THRESHOLD:
        return "不採用", "実寸 %.1fx(閾値 5.0x 未満)" % ratio
    return "採用", "実寸 %.1fx" % ratio


def _fmt_s(x):
    return "—" if x is None else ("%.3f" % x if x < 1 else "%.1f" % x)


def _fmt_e(x):
    return "—" if x is None else "%.1e" % x


def build():
    sys.path.insert(0, str(ROOT))
    import accel
    import accel_typed
    cpu2, gpu2 = _load("cpu", "2d")["rows"], _load("gpu", "2d")["rows"]
    cpun, gpun = _load("cpu", "nary")["rows"], _load("gpu", "nary")["rows"]
    cput, gput = _load("cpu", "typed")["rows"], _load("gpu", "typed")["rows"]
    pc, pg = _load("cpu", "parity")["rows"], _load("gpu", "parity")["rows"]
    meta = _load("gpu", "2d")
    rows, seen = {}, set()

    def measure(name):
        ratio, cs, gs, p1, p2, size = _row(name, cpu2, gpu2, cpun, gpun, cput, gput, pc, pg)
        v, why = _decide(ratio, p1, p2)
        return {"op": name, "size": size, "cpu_s": cs, "gpu_s": gs, "ratio": ratio,
                "parity_cpu": p1, "parity_gpu": p2, "verdict": v, "reason": why}

    halcon = []
    for h, names in HALCON_48.items():
        if not names or (len(names) == 1 and names[0] in NOT_PORTED):
            key = names[0] if names else h
            cpu_only = cpu2.get(key, {}).get("2048", {}).get("cpu_s") if names else None
            halcon.append({"halcon": h, "op": key, "size": "2048² x50" if cpu_only else "—", "cpu_s": cpu_only,
                           "gpu_s": None, "ratio": None, "parity_cpu": None, "parity_gpu": None,
                           "verdict": "不採用", "reason": NOT_PORTED[key]})
            continue
        for n in names:
            r = measure(n)
            r["halcon"] = h
            halcon.append(r)
            seen.add(n)
    required = []
    for n in REQUIRED_MEASURED:
        required.append(measure(n))
    return {"halcon": halcon, "required": required, "meta": {"gpu": meta.get("gpu"), "torch": meta.get("torch")},
            "adopted_2d": sorted(accel.FILL3_ADOPTED), "adopted_nary": sorted(accel.NARY_ACCEL),
            "adopted_typed": sorted(accel_typed.TYPED_ADOPTED),
            "cpu_only": {k: cpu2.get(k, {}) for k in ("bilateral_filter", "cv_bilateral")}}


def _required_roster():
    d = json.loads((ROOT / "fullseye" / "data" / "gpu_required.json").read_text(encoding="utf-8"))
    return [n for g in d["required"].values() for n in g]


def consistency(data) -> list:
    """規則の結論と実装台帳の一致。水増し(台帳にあるが規則は不採用)と取りこぼしを両方拒む。"""
    bad = []
    adopted = {r["op"].split("@")[0] for r in data["halcon"] + data["required"] if r["verdict"] == "採用"}
    # convol_image は小さいマスク(9x9)の測定で判断する
    for r in data["halcon"]:
        if r["op"] == "convol_image@9x9" and r["verdict"] != "採用":
            adopted.discard("convol_image")
    ledger = set(data["adopted_2d"]) | set(data["adopted_nary"]) | set(data["adopted_typed"])
    for n in sorted(ledger - adopted):
        bad.append("registered without a passing measurement: %s" % n)
    for n in sorted(adopted - ledger):
        bad.append("passing measurement but not registered: %s" % n)
    measured = {r["op"] for r in data["required"]}
    roster = set(_required_roster())
    import accel
    import accel_match
    import accel_vol
    gpu = {c for _n, (_f, c, _h) in accel.ACCEL.items()} | {c for _n, (_f, c) in accel_vol.VOL_ACCEL.items()} | set(accel_match.MATCH_ACCEL)
    unclassified = sorted(n for n in roster - measured - set(NOT_PORTED) if n not in gpu)
    if unclassified:
        bad.append("required ops without a verdict: %s" % unclassified)
    return bad


def render(data) -> str:
    h = json.loads((ROOT / "docs" / "perf" / "halcon_opencl_parity.json").read_text(encoding="utf-8"))
    tiers = (ROOT / "docs" / "perf" / "GPU_TIERS.md").read_text(encoding="utf-8")
    m = re.search(r"GPU 対応率 = ([\d.]+)%\*\* \((\d+) / (\d+)\)", tiers)
    rate, have, denom = m.group(1), int(m.group(2)), int(m.group(3))
    hal_rows = data["halcon"]
    hal_keys = {}
    for r in hal_rows:
        hal_keys.setdefault(r["halcon"], []).append(r["verdict"])
    hal_ad = sum(1 for v in hal_keys.values() if "採用" in v)
    measured_required = len(data["required"])
    req_ad = sum(1 for r in data["required"] if r["verdict"] == "採用")
    roster = _required_roster()
    roster_rest = [n for n in roster if n in NOT_PORTED]
    L = ["# GPU 穴埋め 第 3 便 — HALCON OpenCL 48 件と required 名簿の採否 — 2026-11-02", "",
         "`tools/gen_gpu_fill3_report.py` が実測ログ(`docs/perf/logs/fill3_*.json`)と実装台帳から生成する。"
         "数字を手で書かない。採用規則は parity 差 < 5e-3(torch CPU と GPU の両方)かつ実寸倍率 >= 5.0x。", "",
         "- 計測機: %s / torch %s" % (data["meta"].get("gpu") or "未計測", data["meta"].get("torch") or "—"),
         "- HALCON 26.05 OpenCL 84 件のうち GPU 経路あり: **%d → %d**(対応あり %d 件中)" % (BEFORE["n2"], h["n2_gpu"], h["n1_fullseye"]),
         "- 全 op の GPU 対応率: **%d 件 → %d 件**、%s%% (%d / %d)" % (BEFORE["have_gpu"], have, rate, have, denom),
         "- HALCON の 48 件の内訳: 採用 **%d** / 不採用・測定不能 **%d**" % (hal_ad, len(hal_keys) - hal_ad),
         "- required 名簿 48 件(GPU 経路なし)の内訳: 計測 %d 件のうち採用 **%d** / 計算核を書かなかった **%d**"
         % (measured_required, req_ad, len(roster_rest)),
         "- 「HALCON より速い」等、測っていない比較は書かない。ここの倍率はすべて Fullseye の CPU 登録経路に対する比。", "",
         "## HALCON OpenCL 48 件", "",
         "| HALCON 名 | Fullseye op | parity 差 CPU/GPU | 寸法 | CPU s | GPU s | 倍率 | 採否 | 理由 |",
         "|---|---|---|---|---:|---:|---:|:---:|---|"]
    for r in hal_rows:
        L.append("| `%s` | `%s` | %s / %s | %s | %s | %s | %s | %s | %s |" % (
            r["halcon"], r["op"], _fmt_e(r["parity_cpu"]), _fmt_e(r["parity_gpu"]), r["size"],
            _fmt_s(r["cpu_s"]), _fmt_s(r["gpu_s"]), "%.1fx" % r["ratio"] if r["ratio"] else "—", r["verdict"], r["reason"]))
    L += ["", "## required 名簿(計測した %d 件)" % measured_required, "",
          "| op | parity 差 CPU/GPU(相対) | 入力 | CPU s | GPU s | 倍率 | 採否 | 理由 |",
          "|---|---|---|---:|---:|---:|:---:|---|"]
    for r in data["required"]:
        L.append("| `%s` | %s / %s | %s | %s | %s | %s | %s | %s |" % (
            r["op"], _fmt_e(r["parity_cpu"]), _fmt_e(r["parity_gpu"]), r["size"], _fmt_s(r["cpu_s"]),
            _fmt_s(r["gpu_s"]), "%.1fx" % r["ratio"] if r["ratio"] else "—", r["verdict"], r["reason"]))
    L += ["", "## required 名簿(計算核を書かなかった %d 件)" % len(roster_rest), "",
          "| op | 理由 |", "|---|---|"]
    for n in roster_rest:
        L.append("| `%s` | %s |" % (n, NOT_PORTED[n]))
    L += ["", "## 補足: cv2 の bilateral", "", "| op | 2048² x50 CPU s |", "|---|---:|"]
    for k, v in data["cpu_only"].items():
        L.append("| `%s` | %s |" % (k, _fmt_s(v.get("2048", {}).get("cpu_s"))))
    L += ["", "転送床(下記)の 5 倍を CPU が下回るので、仮に核を書いても 5.0x に届かない(a=0.5 の窓幅で測定)。", ""]
    L += (ROOT / "docs" / "perf" / "gpu_fill3_notes.txt").read_text(encoding="utf-8").splitlines()
    L.append("")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    data = build()
    bad = consistency(data)
    md = render(data)
    js = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
    if a.check:
        drift = [str(p) for p, t in ((OUT_MD, md), (OUT_JSON, js))
                 if not p.exists() or p.read_text(encoding="utf-8") != t]
        for b in bad + ["DRIFT: %s" % d for d in drift]:
            print("[gpu_fill3] %s" % b)
        return 1 if bad or drift else 0
    OUT_MD.write_text(md, encoding="utf-8")
    OUT_JSON.write_text(js, encoding="utf-8")
    for b in bad:
        print("[gpu_fill3] %s" % b)
    print("[gpu_fill3] wrote %s" % OUT_MD.name)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
