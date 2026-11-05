#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""実データの例が**門と同じ条件で**実データを読んだかを測り、``docs/real_data_runs.json`` に残す。

    py -3.11 tools/record_real_data_runs.py            # 能力ノートが名指す data: real の例を全部
    py -3.11 tools/record_real_data_runs.py poc_x ...  # 指定した例だけ測り直して台帳に書き戻す
    py -3.11 tools/record_real_data_runs.py --list     # 測る対象だけ見る

## なぜ要るか(2026-11-05、敵対的検証 第 2 巡 D6)

成熟度台帳の ``validated-public-real-data`` は「能力ノートが名指す例が ``data: real`` で、
門がその例を走らせる」だけで決まっていた。ところが実データの多くは repo に入れられず
(ライセンス・容量)、例は ``FULLSEYE_*_DATA`` が無ければ実データの章を飛ばして
**手元で走らせた記録を印字して PASS する**。CI に実データは無いので、門は合成の章しか
見ていない —— それでも台帳は「公開実データで検証済み」と出していた。

読んだかどうかは例の中でしか分からない。そこで例は実データを読み終えた所で
``realdata.mark_read(<データ名>)`` を呼び、この道具は環境変数 ``FULLSEYE_REAL_DATA_LOG``
を立てて**門と同じ条件**で例を走らせ、書かれた印を数える:

* ``PYTHONPATH`` と ``FULLSEYE_*`` を外す(``tests/test_poc_scripts_run.py`` と同じ)
* ``HOME`` / ``USERPROFILE`` / ``FULLSEYE_DATA_DIR`` を空の一時ディレクトリにする
  (CI のランナーには手元の ``~/.cache/fullseye`` が無い。外さないと手元のキャッシュで
  読めてしまい、台帳が CI で起きないことを主張する)
* ダウンロードの許可(``*_DOWNLOAD=1``)は立てない
* ``CI=true`` を立てる(GitHub Actions は自動で立て、多くの PoC はそれで縮めた予算に切り替わり、
  実データの章を最初から飛ばす。立てずに測ると CI で起きない読み込みを記録してしまう)

実行に分単位かかる例があるので ``regen_all`` の鎖には入れず、手で回して commit する
(``tools/regen_all.py`` の EXCLUDED)。記録が古くなる向きの事故は門が拾う:
``tests/test_poc_scripts_run.py`` は全 PoC を走らせるたび、台帳が「読んだ」とする例が
本当に印を出したかを照合する。
"""
from __future__ import annotations

import argparse
import concurrent.futures
import io
import json
import os
import subprocess
import sys
import tempfile

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "tools"))

OUT = os.path.join(_ROOT, "docs", "real_data_runs.json")
TIMEOUT_S = 1800


def targets() -> list:
    """能力ノートが名指す例のうち ``data: real`` のもの(成熟度台帳の判定に効く集合)。"""
    import gen_maturity as GM
    import glob
    out = set()
    for p in sorted(glob.glob(os.path.join(GM.SRC_DIR, "*.md"))):
        meta = GM._front_matter(io.open(p, encoding="utf-8").read(), p)
        for eid in meta["examples"]:
            entry = GM.EX2._BY_ID.get(eid) or GM.EX3._BY_ID.get(eid)
            if entry is not None and entry.get("data") == "real":
                out.add(eid)
    return sorted(out)


def gate_env(tmp: str) -> dict:
    """門と同じ環境(手元のキャッシュとデータ用の環境変数を外す)。"""
    env = {k: v for k, v in os.environ.items()
           if not (k.startswith("FULLSEYE_") or k == "PYTHONPATH")}
    home = os.path.join(tmp, "home")
    data = os.path.join(tmp, "data")
    os.makedirs(home, exist_ok=True)
    os.makedirs(data, exist_ok=True)
    env.update(PYTHONUTF8="1", FULLSEYE_FIGURES="off", FULLSEYE_DEVICE="cpu", CI="true",
               HOME=home, USERPROFILE=home, FULLSEYE_DATA_DIR=data,
               FULLSEYE_REAL_DATA_LOG=os.path.join(tmp, "real_data.log"))
    return env


def run_one(eid: str) -> tuple:
    """例 1 本を門の条件で走らせ ``(id, {exit, printed_pass, datasets_read})`` を返す。"""
    path = os.path.join(_ROOT, "examples", eid + ".py")
    if not os.path.isfile(path):
        raise SystemExit("例 %s のスクリプトが無い: %s" % (eid, path))
    with tempfile.TemporaryDirectory(prefix="realdata_") as tmp:
        env = gate_env(tmp)
        try:
            r = subprocess.run([sys.executable, path], cwd=os.path.dirname(path), env=env,
                               capture_output=True, stdin=subprocess.DEVNULL, timeout=TIMEOUT_S)
            code, out = r.returncode, r.stdout.decode("utf-8", "replace")
        except subprocess.TimeoutExpired:
            code, out = -1, ""
        log = env["FULLSEYE_REAL_DATA_LOG"]
        read = []
        if os.path.exists(log):
            with io.open(log, encoding="utf-8") as fh:
                read = sorted({ln.strip() for ln in fh if ln.strip()})
    return eid, {"exit": code, "printed_pass": "\nPASS" in "\n" + out,
                 "datasets_read": read}


def load(path: str = OUT) -> dict:
    """台帳を読む(無ければ空の形)。"""
    if not os.path.exists(path):
        return {"examples": {}}
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("ids", nargs="*", help="測り直す例(既定: 対象の全部)")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args(argv)
    want = targets()
    if a.list:
        print("\n".join(want))
        return 0
    ids = a.ids or want
    unknown = sorted(set(ids) - set(want))
    if unknown:
        raise SystemExit("能力ノートが名指す data: real の例ではない: %s" % ", ".join(unknown))
    doc = load()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, a.jobs)) as ex:
        for eid, rec in ex.map(run_one, ids):
            doc["examples"][eid] = rec
            print("%-44s exit=%d PASS=%s read=%s" % (eid, rec["exit"], rec["printed_pass"],
                                                    ", ".join(rec["datasets_read"]) or "-"))
    # 対象から外れた例の行は落とす(古い記録を残さない)。
    doc["examples"] = {k: doc["examples"][k] for k in sorted(doc["examples"]) if k in want}
    doc["generated_by"] = "tools/record_real_data_runs.py"
    doc["how"] = ("each example is run like tests/test_poc_scripts_run.py (no PYTHONPATH, no FULLSEYE_* "
                  "variables, CI=true as GitHub Actions sets it) with HOME / USERPROFILE / FULLSEYE_DATA_DIR "
                  "pointing at empty directories, as on a CI runner; datasets_read = the realdata.mark_read() lines it wrote")
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")
    missing = sorted(set(want) - set(doc["examples"]))
    if missing:
        print("[note] まだ測っていない例: %s" % ", ".join(missing))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
