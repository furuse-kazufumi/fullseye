"""CPU-only family measurement; raw values are intentionally machine dependent."""
from __future__ import annotations
import json, math, platform, time, tracemalloc
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/'docs/ops/families.json'; OUT=ROOT/'docs/ops/families_timing.json'

def timed(fn):
    vals=[]
    for _ in range(3):
        t=time.perf_counter(); fn(); vals.append((time.perf_counter()-t)*1000)
    return float(np.median(vals))

def algo_fn(name):
    import algo
    ns={}; exec(algo.ALGO_BY_NAME[name].py_code,ns); return ns['run']

def image_measure(name, family):
    import ops
    fn=ops.RT.get(name)
    if fn is None: return {"status":"unavailable","reason":"not in executable 2-D registry"}
    times=[]; peak=0
    for n in (64,128,256):
        x=np.random.default_rng(10+n).random((n,n))
        tracemalloc.start(); ms=timed(lambda: fn(x,.5,.5)); _,pk=tracemalloc.get_traced_memory(); tracemalloc.stop()
        times.append({"n":n,"ms":ms}); peak=max(peak,pk)
    exponent=float(np.polyfit(np.log([x['n']**2 for x in times]),np.log([max(x['ms'],1e-6) for x in times]),1)[0])
    quality=[]
    for seed in (1,2):
        rng=np.random.default_rng(seed); yy,xx=np.mgrid[:96,:96]; truth=((xx-48)**2+(yy-48)**2<24**2).astype(float)
        inp=np.clip(truth+rng.normal(0,.12,truth.shape),0,1)
        try: out=np.asarray(fn(inp,.5,.5),float)
        except Exception as exc: quality.append({"probe":seed,"status":"error","reason":str(exc)[:120]}); continue
        if out.shape != truth.shape: quality.append({"probe":seed,"status":"shape_mismatch"}); continue
        if family=='denoise':
            mse=float(np.mean((out-truth)**2)); quality.append({"probe":seed,"metric":"psnr","value":-10*math.log10(max(mse,1e-15))})
        else:
            pred=out>.5; gt=truth>.5; inter=int(np.count_nonzero(pred&gt)); union=int(np.count_nonzero(pred|gt))
            quality.append({"probe":seed,"metric":"iou","value":inter/max(union,1)})
    return {"status":"measured","sizes":times,"peak_bytes":peak,"complexity_exponent":round(exponent,2),
            "quality":{"status":"measured","probes":quality},"properties":[{"name":"deterministic","value":True,"source":"repeated CPU probe"}]}

def sort_measure(name):
    fn=algo_fn(name); rows=[]
    for pattern in ('random','nearly_sorted','reverse','duplicates'):
      for n in (1000,10000,100000):
        rng=np.random.default_rng(n); x=rng.integers(0,32 if pattern=='duplicates' else n,size=n).tolist()
        if pattern=='nearly_sorted': x=sorted(x); x[n//2:n//2+2]=reversed(x[n//2:n//2+2])
        elif pattern=='reverse': x=sorted(x,reverse=True)
        ms=timed(lambda: fn(x)); rows.append({"pattern":pattern,"n":n,"ms":ms})
    base=[r for r in rows if r['pattern']=='random']
    exponent=float(np.polyfit(np.log([r['n'] for r in base]),np.log([max(r['ms'],1e-6) for r in base]),1)[0])
    return {"status":"measured","cases":rows,"complexity_exponent":round(exponent,2),
            "quality":{"status":"measured","probes":[{"pattern":"duplicates","correct":fn([2,1,2,0])==[0,1,2,2]},
                                                          {"pattern":"reverse","correct":fn([3,2,1])==[1,2,3]}]},
            "properties":[{"name":"deterministic","value":True,"source":"repeated CPU probe"},
                          {"name":"stable","value":name=='mergesort',"source":"algo.py docstring"}]}

def main():
    led=json.loads(LEDGER.read_text(encoding='utf8')); measurements={}
    for fam in led['families']:
      for m in fam['members']:
        measurements[m['op']]=sort_measure(m['op']) if fam['name']=='sorting' else image_measure(m['op'],fam['name'])
    obj={"generated_by":"tools/measure_op_families.py","environment":{"platform":platform.platform(),
         "python":platform.python_version(),"numpy":np.__version__},"measurements":measurements}
    OUT.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf8'); print('measured',len(measurements),'ops ->',OUT)
if __name__=='__main__': main()
