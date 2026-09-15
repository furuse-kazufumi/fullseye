# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""円形部品の内径を mm まで測る —— 粗い中心出し → 円当てはめ → 校正 → mm。

    py -3.11 examples/example_inner_diameter_mm.py

【この例が解く問題】
穴の内径を、画素で終わらせずに mm で出す。文書だけを渡した AI は
`apply_metrology_model` の半径 [px] で止まっていた(2026-09-15)ので、
最後の 2 段 `mm_per_px_from_reference` / `pixel_to_world` を含めて 1 本にする
(docs/capabilities/inner-diameter-in-mm.md)。

【グラウンドトゥルース】
画素ピッチの真値 0.050 mm/px で、基準の的(Ø10.00 mm = 半径 100.0 px)と
被測定の穴(Ø6.130 mm = 半径 61.3 px)を、被覆率で描いた円板 + ぼけ σ=1 px +
雑音 σ=0.02 で合成する。どちらも同じ op の連鎖で測り、的から mm/px を出して
穴に適用する。

【この例が示すこと(数字は実行時の実測)】
1. 内径 [mm] は真値の ±0.01 mm(0.2 px)以内で戻る。
2. **校正を公称値で置き換える**(作動距離が 4 % ずれた 0.048 mm/px)と、
   同じ px の測定が 0.25 mm ずれる —— 誤差はサブピクセルの精度の 20 倍。
3. `n`(円周の標本数)は 2πR/3 で頭打ち: それ以上増やしても半径の散らばりは
   下がらない(`add_metrology_object_circle_measure` のノートの表)。
4. 円周の 25 % を欠けさせても半径は返る(失敗を返さない)。欠けは `rms` と
   縁の点数(`edge_points`)の**両方**で見張る —— 欠けの境界で偽の縁を拾えば rms が
   跳ね、拾わなければ rms はむしろ下がる(ノートの表)ので、rms だけでは見えない。

EXTEND: 実写なら `disk()` を撮影画像に、`KNOWN_MM` をリングゲージの校正値に。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fullseye as fs  # noqa: E402

MM_PER_PX_TRUE = 0.050
KNOWN_MM = 10.000                       # 基準の的の直径
REF_R_PX = KNOWN_MM / MM_PER_PX_TRUE / 2  # 100.0 px
DUT_R_PX = 61.3                         # 被測定の穴 → Ø 6.130 mm
NOMINAL_MM_PER_PX = 0.048               # 「公称」倍率(作動距離が 4 % ずれている)
rng = np.random.default_rng(0)


def disk(r_px: float, ss: int = 8, blur: float = 1.0, noise: float = 0.02):
    """暗い穴(半径 r_px)を被覆率で描き、ぼかして雑音を足す。中心は画素中心から外す。"""
    from scipy.ndimage import gaussian_filter

    size = int(2 * r_px + 48)
    cy, cx = size / 2.0 + 0.37, size / 2.0 - 0.21
    n = size * ss
    ax = (np.arange(n) + 0.5) / ss - 0.5
    inside = ((ax[:, None] - cy) ** 2 + (ax[None, :] - cx) ** 2) <= r_px * r_px
    cov = inside.reshape(size, ss, size, ss).mean(axis=(1, 3))
    img = gaussian_filter(0.8 - 0.6 * cov, blur)
    return img + rng.normal(0.0, noise, img.shape), (cy, cx)


def measure_radius(img: np.ndarray) -> tuple[float, float, int]:
    """粗い中心 → 参照円 → サブピクセル当てはめ。(radius_px, rms, エッジ点数)。"""
    sm = fs.apply(img, "gaussian", 0.2, 0.5)
    reg = np.asarray(fs.apply(sm, "otsu", 0.5, 0.5))
    hole = 1.0 - reg if reg.mean() > 0.5 else reg            # 穴(暗い側)を前景に
    _score, r_n, c_n = fs.apply(hole, "area_center", 0.5, 0.5)   # 正規化座標 [0,1]
    row0, col0 = r_n * (img.shape[0] - 1), c_n * (img.shape[1] - 1)
    r0 = float(np.sqrt(hole.sum() / np.pi))                    # 面積から半径の初期値
    n = int(np.clip(round(2 * np.pi * r0 / 3.0), 24, 400))    # 円周 3 px に 1 点で頭打ち
    model = fs.ledger.create_metrology_model()
    fs.ledger.add_metrology_object_circle_measure(model, row0, col0, r0, n=n)
    res = fs.ledger.apply_metrology_model(model, img, measure_length=6.0, sigma=1.0, threshold=0.1)[0]
    assert res["params"] is not None, res.get("error")
    return float(res["params"]["radius"]), float(res["rms"]), int(len(res["edge_points"]))


def main() -> None:
    print("=== 円形部品の内径を mm まで(真値 Ø %.3f mm、%.3f mm/px)" % (2 * DUT_R_PX * MM_PER_PX_TRUE, MM_PER_PX_TRUE))
    ref, _ = disk(REF_R_PX)
    r_ref, rms_ref, n_ref = measure_radius(ref)
    mm_per_px = fs.ledger.mm_per_px_from_reference(2 * r_ref, KNOWN_MM)
    print(f"校正: 的 Ø{KNOWN_MM:.3f} mm → 半径 {r_ref:.3f} px(真値 {REF_R_PX:.1f}、rms {rms_ref:.3f} px、"
          f"縁 {n_ref} 点) → mm/px = {mm_per_px:.5f}(真値 {MM_PER_PX_TRUE:.5f}、"
          f"{(mm_per_px / MM_PER_PX_TRUE - 1) * 100:+.3f} %)")

    dut, _ = disk(DUT_R_PX)
    r_dut, rms_dut, n_dut = measure_radius(dut)
    d_mm = fs.ledger.pixel_to_world(2 * r_dut, mm_per_px)
    d_true = 2 * DUT_R_PX * MM_PER_PX_TRUE
    d_nominal = fs.ledger.pixel_to_world(2 * r_dut, NOMINAL_MM_PER_PX)
    print(f"被測定: 半径 {r_dut:.3f} px(真値 {DUT_R_PX:.1f}、{r_dut - DUT_R_PX:+.3f} px、rms {rms_dut:.3f} px、縁 {n_dut} 点)")
    print(f"  内径 = pixel_to_world(2·r, 校正値) = {d_mm:.4f} mm(真値 {d_true:.3f}、{(d_mm - d_true) * 1000:+.1f} µm)")
    print(f"  公称倍率 {NOMINAL_MM_PER_PX} mm/px で換算すると {d_nominal:.4f} mm({(d_nominal - d_true) * 1000:+.1f} µm)"
          " —— サブピクセルの精度の何十倍もの誤差が校正 1 個から出る")
    rows = fs.ledger.table_px_to_mm(
        fs.ledger.apply_metrology_model(
            _model_for(dut, r_dut), dut, measure_length=6.0, sigma=1.0, threshold=0.1), mm_per_px)
    print(f"  table_px_to_mm: radius_mm {rows[0]['params']['radius_mm']:.4f} / rms_mm {rows[0]['rms_mm']:.4f}")

    # 欠け: 円周の 25 % を背景で塗る —— 半径は返る(rms も下がる)。門は縁の点数。
    cut = dut.copy()
    yy, xx = np.mgrid[0:cut.shape[0], 0:cut.shape[1]]
    cy, cx = cut.shape[0] / 2.0 + 0.37, cut.shape[1] / 2.0 - 0.21
    ang = np.arctan2(yy - cy, xx - cx)
    cut[(ang > -np.pi / 4) & (ang < np.pi / 4)] = 0.8 + rng.normal(0, 0.02, cut[(ang > -np.pi / 4) & (ang < np.pi / 4)].shape)
    r_cut, rms_cut, n_cut = measure_radius(cut)
    print(f"円周の 25 % が欠けた穴: 半径 {r_cut:.3f} px({r_cut - DUT_R_PX:+.3f})、rms {rms_cut:.3f}、縁 {n_cut} 点"
          f"(無傷 {n_dut} 点)")
    print("  粗い中心(area_center)が欠けで動き、欠けの境界で偽の縁を拾うので rms と点数の両方に出る。"
          "中心が正しく境界の縁を拾わない条件では rms が**下がる**(ノートの表)—— 門は rms と点数の両方。")

    assert abs(d_mm - d_true) < 0.010, d_mm                       # ±10 µm
    assert abs(mm_per_px - MM_PER_PX_TRUE) / MM_PER_PX_TRUE < 0.002
    assert abs(d_nominal - d_true) > 0.2                          # 公称倍率の罠
    assert n_cut < 0.85 * n_dut, (n_cut, n_dut)                   # 欠けは縁の点数に出る
    assert abs(r_cut - DUT_R_PX) > 1.0 and rms_cut > 5 * rms_dut  # この条件では rms にも出る
    print("PASS")


def _model_for(img: np.ndarray, r: float):
    reg = np.asarray(fs.apply(fs.apply(img, "gaussian", 0.2, 0.5), "otsu", 0.5, 0.5))
    hole = 1.0 - reg if reg.mean() > 0.5 else reg
    _s, r_n, c_n = fs.apply(hole, "area_center", 0.5, 0.5)
    model = fs.ledger.create_metrology_model()
    fs.ledger.add_metrology_object_circle_measure(model, r_n * (img.shape[0] - 1), c_n * (img.shape[1] - 1), r, n=120)
    return model


if __name__ == "__main__":
    main()
