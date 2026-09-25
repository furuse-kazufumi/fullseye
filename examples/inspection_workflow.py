# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""inspection_workflow — フォルダを一括検査し、仕様で判定し、集計・SPC・レポート・監査ログまで出す。

    py -3.11 examples/inspection_workflow.py

【この例が示すこと】
ライン担当が最初に触る形 —— 「画像フォルダ → 前処理レシピ → 計測 → 仕様で良否 → 集計 →
レポート」を、op を 1 本ずつ呼ばずに ``fs.inspect_batch`` 1 回で回す。合成の 1 ロット
(良品 5・欠陥 1・壊れたファイル 1)を書いて、

1. ``judge`` が計測 dict を仕様に照らし、**根拠つき**の Verdict(ok / ng / error)にする
2. ``inspect_batch`` が全枚を回し、各行に入力 sha256・計測・Verdict・所要時間を残す
3. 欠陥の 1 枚だけが ng、壊れた 1 枚は error で **バッチを止めない**
4. 数値の計測列は EWMA(spc_ewma)で工程管理の目安が付く
5. 同じ結果を .md / .jsonl(/ .xlsx)に書き分け、監査ログ(JSON Lines)に追記する
6. 行の Verdict はそのまま PLC 出口 ``signal_verdict`` に渡せる(語彙一致)。
   出口は ``fs.open_driver("io-memory")`` —— **名簿 ``fs.drivers()`` の名前を
   そのまま渡す**。入っていない driver は pip 名を名指しで断る

ことを assert で確かめる(絵に描いたふりをしない)。

EXTEND: ``measure`` を差し替えれば計測は何でもよい(``fs.apply(im, "area")`` 等を束ねる)。
``recipe`` は run_pipeline の stages なので ``[("gaussian", 0.3, 0.5), "otsu"]`` のように
段ごとのノブも書ける。openpyxl があれば .xlsx も出る(``pip install "fullseye[xlsx]"``)。
"""
from __future__ import annotations

import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fullseye as fs  # noqa: E402


def make_lot(folder: str) -> None:
    """64x64 の板。中央の明部が 20x20(=400 px)なら良品、30x30(=900 px)なら欠陥。"""
    rng = np.random.default_rng(0)
    for i in range(6):
        im = 0.30 + 0.02 * rng.standard_normal((64, 64))
        k = 15 if i == 5 else 10
        im[32 - k:32 + k, 32 - k:32 + k] = 0.9
        np.save(os.path.join(folder, "part_%02d.npy" % i), np.clip(im, 0, 1))
    with open(os.path.join(folder, "part_06.npy"), "wb") as fh:      # 壊れたファイル
        fh.write(b"not an image")


def measure(im: np.ndarray) -> dict:
    """計測 op を束ねて dict にする(ここは呼び手が決める)。"""
    return {"mean": float(im.mean()), "bright_px": float((im > 0.5).sum())}


# 仕様は **recipe を通した後の計測** に対して書く: 良品の明部は素の 400 px だが、gaussian が
# 縁をなだらかにして >0.5 の画素は 464 px に広がる(欠陥は 900 → 1004 px)。だから公称は 460。
SPEC = {"mean": {"min": 0.2, "max": 0.6},                 # 下限・上限
        "bright_px": {"nominal": 460.0, "tol": 80.0}}      # 公称 ± 公差(380〜540 が ok)


def main() -> int:
    work = tempfile.mkdtemp(prefix="fullseye_lot_")
    lot = os.path.join(work, "lot")
    os.makedirs(lot)
    make_lot(lot)

    # 1. judge 単体 —— 根拠つきの Verdict
    v = fs.judge({"mean": 0.35, "bright_px": 1004.0}, SPEC)
    print("judge:", v.status, "|", v.detail)
    assert v.status == "ng" and v.result["violations"][0]["key"] == "bright_px"
    assert fs.judge({"mean": 0.35}, SPEC).status == "error"          # 欠損は黙って ok にしない

    # 2-5. 一括検査 → 集計 → レポート → 監査ログ
    md = os.path.join(work, "lot_report.md")
    audit = os.path.join(work, "audit.jsonl")
    out = fs.inspect_batch(lot, ["gaussian"], measure=measure, spec=SPEC,
                           report_path=md, audit_path=audit, title="Lot 0001")
    for r in out["rows"]:
        print("  %-12s %s  %-5s %s" % (os.path.basename(r["path"]), r["hash"],
                                       r["verdict"]["status"], r["verdict"]["detail"][:60]))
    print("summary:", out["summary"])
    assert out["summary"] == {"n": 7, "ok": 5, "ng": 1, "error": 1, "unjudged": 0}
    assert out["rows"][5]["verdict"]["status"] == "ng" and "error" in out["rows"][6]
    print("spc(bright_px):", {k: out["spc"]["bright_px"][k] for k in ("n", "target", "in_control")})
    assert out["spc"]["bright_px"]["n"] == 6

    assert os.path.exists(md) and "part_05.npy" in open(md, encoding="utf-8").read()
    fs.inspect_batch(lot, ["gaussian"], measure=measure, spec=SPEC,
                     report_path=os.path.join(work, "lot_rows.jsonl"))
    rows = fs.from_json_lines(open(os.path.join(work, "lot_rows.jsonl"), encoding="utf-8").read())
    assert len(rows) == 7 and rows[5][0]["status"] == "ng"
    entries = fs.from_json_lines(open(audit, encoding="utf-8").read())
    assert len(entries) == 7 and entries[0][0]["batch"] == "Lot 0001" and entries[0][0]["recipe"] == ["gaussian"]
    print("report:", md, "/ rows .jsonl / audit %d entries" % len(entries))
    try:
        import openpyxl  # noqa: F401
        xlsx = os.path.join(work, "lot_report.xlsx")
        fs.inspect_batch(lot, ["gaussian"], measure=measure, spec=SPEC, report_path=xlsx)
        print("xlsx:", xlsx)
    except ImportError:
        print('xlsx: skip(openpyxl 未導入、pip install "fullseye[xlsx]")')

    # 6. 行の Verdict は PLC 出口にそのまま渡せる。出口は**名簿から開く** ——
    #    `fs.drivers()` に並ぶ名前をそのまま `fs.open_driver` に渡す。
    assert "io-memory" in fs.drivers(), "名簿に試験用の出口が無い"
    io = fs.open_driver("io-memory")                 # ハード無しで動く出口
    assert fs.signal_verdict(io, fs.as_verdict(out["rows"][5])) == "ng"
    print("PLC 出口(one-hot コイル)に ng を出せた")

    #    この install に入っていない driver は、**何を入れればよいかを名指しで**断る
    #    (名簿に載っているのに開き方が分からない、が起きないようにするため)。
    try:
        fs.open_driver("ur-rtde")
    except fs.DeviceError as e:
        assert "ur-rtde" in str(e) and "rtde_control" in str(e)
        print("入っていない driver の断り文句:", e)
    else:
        print("ur-rtde が開けた(この機械には ur_rtde が入っている)")
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
