"""CPU-only family measurement; raw values are intentionally machine dependent."""
from __future__ import annotations
import hashlib, json, math, platform, time, tracemalloc
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
    for n in (256,512,768):
        x=np.random.default_rng(10+n).random((n,n))
        fn(x,.5,.5)  # warm-up is outside timing
        ms=timed(lambda: fn(x,.5,.5))
        tracemalloc.start(); fn(x,.5,.5); _,pk=tracemalloc.get_traced_memory(); tracemalloc.stop()
        times.append({"pixels":n*n,"width":n,"height":n,"ms":ms}); peak=max(peak,pk)
    exponent=float(np.polyfit(np.log([x['pixels'] for x in times]),np.log([max(x['ms'],1e-6) for x in times]),1)[0])
    quality=[]
    for seed in (1,2):
        rng=np.random.default_rng(seed); yy,xx=np.mgrid[:96,:96]; truth=((xx-48)**2+(yy-48)**2<24**2).astype(float)
        inp=np.clip(truth+rng.normal(0,.12,truth.shape),0,1)
        try: out=np.asarray(fn(inp,.5,.5),float)
        except Exception as exc: quality.append({"probe":seed,"status":"error","reason":str(exc)[:120]}); continue
        if out.shape != truth.shape: quality.append({"probe":seed,"status":"shape_mismatch"}); continue
        if family=='denoise':
            mse=float(np.mean((out-truth)**2)); quality.append({"probe":seed,"metric":"psnr","value":-10*math.log10(max(mse,1e-15))})
        elif family=='edge_detection':
            pred=out>np.quantile(out,.8); gy,gx=np.gradient(truth); gt=np.hypot(gx,gy)>0
            tp=np.count_nonzero(pred&gt); precision=tp/max(np.count_nonzero(pred),1); recall=tp/max(np.count_nonzero(gt),1)
            score=float(2*precision*recall/max(precision+recall,1e-15))
            quality.append({"probe":seed,"metric":"boundary_f1","value":score} if score>0 else
                           {"probe":seed,"status":"unmeasured","reason":"synthetic boundary probe produced zero F1"})
        elif family != 'phase_unwrap':
            pred=out>.5; gt=truth>.5; inter=int(np.count_nonzero(pred&gt)); union=int(np.count_nonzero(pred|gt))
            quality.append({"probe":seed,"metric":"iou","value":inter/max(union,1)})
    probe=np.random.default_rng(999).random((96,96)); first=np.asarray(fn(probe,.5,.5)); second=np.asarray(fn(probe,.5,.5))
    deterministic=bool(np.array_equal(first,second,equal_nan=True))
    quality_result={"status":"unmeasured","reason":"no valid synthetic ground-truth metric for phase unwrapping"} if family=='phase_unwrap' else {"status":"measured","probes":quality}
    return {"status":"measured","input_unit":"pixels","sizes":times,"peak_bytes":peak,"complexity_exponent":round(exponent,2),
            "quality":quality_result,"properties":[{"name":"deterministic","value":deterministic,"source":"two actual outputs on identical input"}]}

def sort_measure(name):
    fn=algo_fn(name); rows=[]
    for pattern in ('random','nearly_sorted','reverse','duplicates'):
      for n in (1000,10000,100000):
        rng=np.random.default_rng(n); x=rng.integers(0,32 if pattern=='duplicates' else n,size=n).tolist()
        if pattern=='nearly_sorted': x=sorted(x); x[n//2:n//2+2]=reversed(x[n//2:n//2+2])
        elif pattern=='reverse': x=sorted(x,reverse=True)
        fn(x); ms=timed(lambda: fn(x)); rows.append({"pattern":pattern,"items":n,"ms":ms})
    exponents={}
    for pattern in ('random','nearly_sorted','reverse','duplicates'):
        base=[r for r in rows if r['pattern']==pattern]
        exponents[pattern]=round(float(np.polyfit(np.log([r['items'] for r in base]),np.log([max(r['ms'],1e-6) for r in base]),1)[0]),2)
    class Keyed:
        def __init__(self,key,order): self.key,self.order=key,order
        def __lt__(self,other): return self.key<other.key
        def __le__(self,other): return self.key<=other.key
        def __eq__(self,other): return isinstance(other,Keyed) and self.key==other.key
    keyed=[Keyed(k,i) for i,k in enumerate([1,0,1,0,1,0])]
    stable_out=fn(keyed); stable=all([x.order for x in stable_out if x.key==k]==sorted(x.order for x in keyed if x.key==k) for k in (0,1))
    sample=[5,1,5,2,0]; deterministic=fn(sample)==fn(sample)
    return {"status":"measured","input_unit":"items","cases":rows,"complexity_exponents":exponents,
            "complexity_exponent":exponents['random'],
            "quality":{"status":"measured","probes":[{"pattern":"duplicates","correct":fn([2,1,2,0])==[0,1,2,2]},
                                                          {"pattern":"reverse","correct":fn([3,2,1])==[1,2,3]}]},
            "properties":[{"name":"deterministic","value":deterministic,"source":"two actual outputs on identical input"},
                          {"name":"stable","value":stable,"source":"keyed equal-key order probe"}]}

def main():
    led=json.loads(LEDGER.read_text(encoding='utf8')); measurements={}
    for fam in led['families']:
      for m in fam['members']:
        measurements[m['op']]=sort_measure(m['op']) if fam['name']=='sorting' else image_measure(m['op'],fam['name'])
    code_files=[ROOT/'tools/measure_op_families.py',ROOT/'algo.py',ROOT/'ops.py']
    code_hash=hashlib.sha256(b''.join(p.read_bytes() for p in code_files)).hexdigest()
    obj={"generated_by":"tools/measure_op_families.py","code_sha256":code_hash,"environment":{"platform":platform.platform(),
         "python":platform.python_version(),"numpy":np.__version__},"measurements":measurements}
    OUT.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf8'); print('measured',len(measurements),'ops ->',OUT)
if __name__=='__main__': main()
