import warnings; warnings.simplefilter("ignore")
# Manual GPU smoke script (run directly: `py -3.11 test_gsplat_native.py`), not a unit test.
# Skip-guard so a plain `pytest` at the repo root doesn't fail collection on CPU-only /
# no-gsplat environments (the real suite lives under tests/).
import pytest  # noqa: E402
pytest.importorskip("gsplat", reason="gsplat (native CUDA) not installed — GPU-only smoke")
pytest.importorskip("torch", reason="torch not installed")
import torch, gsplat, time  # noqa: E402
print("torch", torch.__version__, "cuda", torch.cuda.is_available(), torch.cuda.get_device_name(0))
print("gsplat", gsplat.__version__)
N=2000
dev="cuda"
means=torch.randn(N,3,device=dev)*0.5
quats=torch.randn(N,4,device=dev); quats=quats/quats.norm(dim=-1,keepdim=True)
scales=torch.rand(N,3,device=dev)*0.05+0.01
opac=torch.rand(N,device=dev)*0.5+0.5
colors=torch.rand(N,3,device=dev)
viewmat=torch.eye(4,device=dev); viewmat[2,3]=3.0
viewmat=viewmat[None]
K=torch.tensor([[[200.,0,128],[0,200.,128],[0,0,1]]],device=dev)
print("compiling+rasterizing (first call triggers JIT build)...", flush=True)
t0=time.time()
out,alpha,meta=gsplat.rasterization(means,quats,scales,opac,colors,viewmat,K,256,256)
torch.cuda.synchronize()
print(f"RASTER OK shape={tuple(out.shape)} mean={float(out.mean()):.4f} in {time.time()-t0:.1f}s (incl compile)")
# 2回目は高速
t0=time.time()
for _ in range(50):
    out,_,_=gsplat.rasterization(means,quats,scales,opac,colors,viewmat,K,256,256)
torch.cuda.synchronize()
print(f"50 rasterizations in {time.time()-t0:.3f}s ({50/(time.time()-t0):.0f}/s) — gsplat NATIVE works")
