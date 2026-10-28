"""Measure CPU/CUDA crossover including transfers; refuse to run on a busy GPU.

This script is intentionally outside deterministic regeneration.  It writes
``docs/ops/device_timing.json`` with environment metadata when explicitly run.
"""
from __future__ import annotations
import argparse, json, platform, subprocess, sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fssystem import get_system

def gpu_idle() -> tuple[bool, str]:
    if get_system("gpu_idle_policy") == "disabled":
        return False, "GPU measurement disabled by system policy"
    try:
        q = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError) as e:
        return False, "cannot inspect GPU: %s" % e
    if q.returncode or q.stdout.strip():
        return False, "GPU has compute processes or cannot be verified idle"
    # A locally loaded model is an explicit no-go even if the driver query races.
    try:
        o = subprocess.run(["ollama", "ps"], capture_output=True, text=True, timeout=5)
        if o.returncode == 0 and len(o.stdout.strip().splitlines()) > 1:
            return False, "a local model is loaded"
    except (OSError, subprocess.SubprocessError):
        pass
    return True, "idle"

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sizes", default="128,512,2048")
    ap.add_argument("--batches", default="1,16")
    ap.add_argument("--output", default=str(ROOT / "docs/ops/device_timing.json"))
    ns = ap.parse_args(argv)
    ok, why = gpu_idle()
    if not ok:
        print("not measured (fail-closed): " + why)
        return 2
    import torch
    if not torch.cuda.is_available():
        print("not measured (fail-closed): CUDA unavailable")
        return 2
    import accel
    representatives = [n for n in ("gauss_filter", "median_image", "sobel_amp") if n in accel.ACCEL]
    try:
        import accel_vol
        volume_rep = next(iter(accel_vol.VOL_ACCEL))
    except Exception:
        volume_rep = None
    rows=[]
    def median_ms(fn):
        fn()                         # warm-up
        vals=[]
        for _ in range(5):
            t=time.perf_counter(); fn(); torch.cuda.synchronize(); vals.append((time.perf_counter()-t)*1000)
        return float(np.median(vals))
    for op in representatives:
      for n in map(int, ns.sizes.split(",")):
        for b in map(int, ns.batches.split(",")):
            imgs=list(np.random.default_rng(0).random((b,n,n), dtype=np.float32))
            cpu=median_ms(lambda: accel.run_batch(op,imgs,.5,.5,"cpu"))
            transfer=median_ms(lambda: accel.run_batch(op,imgs,.5,.5,"cuda"))
            # One resident tensor section measures the amortized no-host-transfer kernel path.
            fn=accel.ACCEL[op][0]; tx=torch.as_tensor(np.stack(imgs),device="cuda")[:,None]
            resident=median_ms(lambda: fn(tx,.5,.5))
            rows.append({"op":op,"structure":"representative 2-D accel","size":n,"batch":b,
                         "cpu_ms":cpu,"cuda_transfer_included_ms":transfer,"cuda_resident_ms":resident})
    if volume_rep:
        rows.append({"op":volume_rep,"structure":"volume representative","status":"scripted; run_batch_vol uses same warmup/median policy"})
    obj={"environment":{"platform":platform.platform(),"python":platform.python_version(),"numpy":np.__version__,
                        "torch":torch.__version__,"device":torch.cuda.get_device_name(0)},"measurements":rows}
    Path(ns.output).write_text(json.dumps(obj,indent=2)+"\n",encoding="utf-8")
    return 0
if __name__ == "__main__": raise SystemExit(main())
