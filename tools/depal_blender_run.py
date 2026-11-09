# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""混載デパレタイズの PoC が使う Blender(Cycles)の天井カメラのコマを、知覚が要る分だけその場で描く(手元専用)。

    py -3.11 tools/depal_blender_run.py      # 5 条件 × 10 枚(BLENDER と、GPU なら FULLSEYE_GPU_LOCK を環境変数で渡す)
    set DEPAL_DEVICE=CPU & py -3.11 tools/depal_blender_run.py    # GPU が使えないとき(1 コマ約 4 秒)

どのコマが要るかは知覚の結果で決まる(1 個下ろすたびに撮り直す)。そこで場面ごとに Blender を 1 つ
**待ち受け**で立て(``tools/depal_blender_render.py`` の serve)、PoC の ``run_scene`` を全部の設定で回し、
無いコマに出会うたびに待ち受けへ描かせる(``BlenderColor.on_missing`` の口)。PoC 自身は Blender を呼ばない。

描画の置き場は ``FULLSEYE_DEPAL_RENDERS``(既定は ``<作業場>/data/fullseye_poc_real/depal_blender``)。
repo には入れない。Blender の場所は環境変数 ``BLENDER``、GPU のロックは ``FULLSEYE_GPU_LOCK``(未設定なら止まる)。
最初のコマ(積んだまま)だけは深度(Z)も描き、PoC が幾何の深度と照合する。
"""
from __future__ import annotations

import concurrent.futures as cf
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POC = ROOT / "examples" / "poc_mixed_case_depalletizing.py"
RENDER = ROOT / "tools" / "depal_blender_render.py"
#: Blender の実行ファイル(環境変数 BLENDER だけから取る。手元の場所を追跡するファイルに書かない)。
BLENDER = os.environ.get("BLENDER", "").strip()
#: GPU のロックのファイル(環境変数 FULLSEYE_GPU_LOCK。GPU で描くときだけ要る)。
LOCK = Path(os.environ["FULLSEYE_GPU_LOCK"]) if os.environ.get("FULLSEYE_GPU_LOCK", "").strip() else None
EXPORT = Path(tempfile.gettempdir()) / "depal_blender_exports"


def _poc():
    spec = importlib.util.spec_from_file_location("poc_depal", POC)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["poc_depal"] = mod
    spec.loader.exec_module(mod)
    return mod


def renders_root(poc) -> Path:
    r = poc.renders_root()
    if r is not None:
        return r
    if ROOT.parent.name.lower() == "projects":
        return ROOT.parent.parent / "data" / "fullseye_poc_real" / "depal_blender"
    return Path.home() / ".cache" / "fullseye" / "depal_blender"


def _first_frame(poc, cond, seed, out, scene=None):
    """積んだままのコマ(カラーと深度)を描く。``scene`` を渡せば合わせ目の地図の場面も描ける。"""
    scene = scene if scene is not None else poc.make_scene(cond, seed)
    name = poc.scene_dir_name(scene)
    key = sorted(b.id for b in scene.boxes)
    if (out / name / ("rgb_%s.png" % poc.frame_key(key))).is_file() and \
            (out / name / ("depth_%s.npy" % poc.frame_key(key))).is_file():
        return
    exp = EXPORT / (name + "_first")
    poc.export_scene(scene, exp, [tuple(key)])
    r = subprocess.run([BLENDER, "--background", "--factory-startup", "--python", str(RENDER), "--",
                        str(exp), str(out / name), "32"], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=dict(os.environ, DEPAL_DEVICE=os.environ.get("DEPAL_DEVICE", "GPU")))
    if "DEPAL_RENDERED" not in r.stdout:
        sys.stderr.write(r.stdout[-2000:] + r.stderr[-2000:])
        raise SystemExit("Blender could not draw the first frame of %s" % name)


def map_job(cond: str, seed: int, cell: tuple, out: str) -> str:
    """合わせ目の地図の場面(最初のコマだけ)を描く。"""
    poc = _poc()
    dip, gap, tape = cell
    scene = poc.make_scene(cond, seed, flap_map=(dip / 1000.0, gap / 1000.0, tape))
    _first_frame(poc, cond, seed, Path(out), scene)
    return poc.scene_dir_name(scene)


def scene_job(cond: str, seed: int, out: str) -> tuple[str, int, int]:
    """1 枚のパレット: Blender の待ち受けを立て、PoC の繰り返しを全部回す。→ (名前, 描かせた枚数, 足りない枚数)。"""
    poc = _poc()
    out = Path(out)
    _first_frame(poc, cond, seed, out)
    name = "%s_%d" % (cond, seed)
    exp = EXPORT / name
    poc.export_scene(poc.make_scene(cond, seed), exp, [])
    d = out / name
    d.mkdir(parents=True, exist_ok=True)
    for f in d.glob("req_*.json"):
        f.unlink()
    quit_f = d / "quit"
    if quit_f.exists():
        quit_f.unlink()
    log = open(EXPORT / ("serve_%s.log" % name), "w", encoding="utf-8")
    proc = subprocess.Popen([BLENDER, "--background", "--factory-startup", "--python", str(RENDER), "--",
                             str(exp), str(d), "32", "serve"], stdout=log, stderr=subprocess.STDOUT,
                            env=dict(os.environ, DEPAL_DEVICE=os.environ.get("DEPAL_DEVICE", "GPU")))
    n = {"req": 0}

    def on_missing(scene, key, f):
        n["req"] += 1
        req = d / ("req_%06d.json" % n["req"])
        tmp = req.with_suffix(".tmp")
        tmp.write_text(json.dumps(list(key)), encoding="utf-8")
        tmp.replace(req)
        t0 = time.time()
        while not f.is_file():
            if proc.poll() is not None:
                raise RuntimeError("Blender server stopped: %s" % name)
            if time.time() - t0 > 600:
                raise RuntimeError("Blender did not answer in 600 s: %s %s" % (name, key))
            time.sleep(0.05)
        time.sleep(0.05)

    poc.BlenderColor.on_missing = on_missing
    try:
        o = poc.run_scene(cond, seed, 60, True, out, seed == poc.TUNE_SEEDS[0])  # 図の見本のコマも描く
    finally:
        quit_f.write_text("1")
        try:
            proc.wait(timeout=120)
        except subprocess.TimeoutExpired:
            proc.kill()
        log.close()
    return name, n["req"], sum(len(v) for v in o["missing"].values())


def _require_env() -> None:
    """要る環境変数が無ければ、何をすればよいかを書いて止まる(既定の場所は持たない)。"""
    if not BLENDER or not Path(BLENDER).is_file():
        raise SystemExit("set BLENDER to the Blender executable (got %r)" % BLENDER)
    if os.environ.get("DEPAL_DEVICE", "GPU") == "GPU" and LOCK is None:
        raise SystemExit("GPU rendering needs FULLSEYE_GPU_LOCK (the shared GPU lock file); or set DEPAL_DEVICE=CPU")


def _lock() -> bool:
    if os.environ.get("DEPAL_DEVICE", "GPU") != "GPU":
        return False
    if LOCK is None:                                    # 素通りしない(_require_env と二重に止める)
        raise SystemExit("FULLSEYE_GPU_LOCK is not set")
    t0 = time.time()
    while True:                                         # 他者のロックは待つ・消さない
        try:
            fd = os.open(str(LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            # max_hold: 長く握ったロックを持ち主ごと止める見張りに、正当に長く使うことを知らせる(既定 7200 秒 = 2 時間、DEPAL_GPU_MAX_HOLD で変える)
            os.write(fd, ("depal pid=%d %s max_hold=%d\n" % (os.getpid(), time.strftime("%Y-%m-%dT%H:%M:%S"),
                                                             int(os.environ.get("DEPAL_GPU_MAX_HOLD", "7200")))).encode())
            os.close(fd)
            return True
        except FileExistsError:
            if time.time() - t0 > 3600:
                raise SystemExit("GPU lock busy: %s" % LOCK.read_text(errors="replace"))
            time.sleep(5)


def main() -> None:
    _require_env()
    poc = _poc()
    out = renders_root(poc)
    seeds = [int(s) for s in os.environ.get("DEPAL_SEEDS", ",".join(map(str, poc.TUNE_SEEDS + poc.HELD_SEEDS))).split(",")]
    conds = os.environ.get("DEPAL_CONDS", ",".join(poc.CONDITIONS)).split(",")
    held = _lock()
    try:
        with cf.ProcessPoolExecutor(max_workers=int(os.environ.get("DEPAL_WORKERS", "8"))) as ex:
            bad = 0
            if os.environ.get("DEPAL_ONLY_MAP") != "1":
                futs = [ex.submit(scene_job, c, s, str(out)) for c in conds for s in seeds]
                for fu in cf.as_completed(futs):
                    name, nreq, nmiss = fu.result()
                    print("%s: drew %d frames, still missing %d" % (name, nreq, nmiss), flush=True)
                    bad += nmiss
            # 合わせ目の地図の場面(最初のコマだけ。PoC の MAP_* と同じ升目)
            futs = [ex.submit(map_job, c, s, cell, str(out)) for c in poc.MAP_CONDS for s in poc.MAP_SEEDS
                    for cell in poc.map_cells()]
            for fu in cf.as_completed(futs):
                print("map: %s" % fu.result(), flush=True)
    finally:
        if held:
            try:
                if LOCK.read_text().startswith("depal"):
                    LOCK.unlink()
            except OSError:
                pass
    if bad:
        raise SystemExit("frames still missing: %d" % bad)
    print("all frames rendered:", out)


if __name__ == "__main__":
    main()
