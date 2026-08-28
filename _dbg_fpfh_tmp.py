import sys
sys.path.insert(0, r"C:/dev/projects/imgevolve")
import numpy as np
from scipy.spatial import cKDTree
import feat_fpfh

def rot(axis, deg):
    a=np.asarray(axis,float); a/=np.linalg.norm(a); th=np.radians(deg)
    K=np.array([[0,-a[2],a[1]],[a[2],0,-a[0]],[-a[1],a[0],0]])
    return np.eye(3)+np.sin(th)*K+(1-np.cos(th))*K@K

def lumpy(n=3000):
    i=np.arange(n)+0.5
    phi=np.arccos(1-2*i/n); gold=np.pi*(1+5**0.5); tha=gold*i
    d=np.stack([np.sin(phi)*np.cos(tha),np.sin(phi)*np.sin(tha),np.cos(phi)],1)
    bumps=[([1,0,0],0.35,0.5),([0,1,0],-0.22,0.4),([0,0,1],0.28,0.6),
           ([-1,0.5,0.3],0.2,0.35),([0.4,-1,0.5],0.26,0.45),([0.2,0.3,-1],-0.16,0.5)]
    r=np.full(n,1.0)
    for c,amp,w in bumps:
        c=np.asarray(c,float); c/=np.linalg.norm(c)
        th=np.arccos(np.clip(d@c,-1,1)); r=r+amp*np.exp(-th**2/(2*w**2))
    return d*r[:,None]

def run(noise_scale, thr, feat_k=60, normal_k=16, tag=""):
    obj=lumpy(3000)
    R=rot([0.3,1,0.2],58.0); t=np.array([2.,-1.,0.5])
    dirn=obj/np.linalg.norm(obj,axis=1,keepdims=True)
    axA=np.array([1.,0.2,0.1]); axA/=np.linalg.norm(axA)
    axB=np.array([0.2,1.,0.3]); axB/=np.linalg.norm(axB)
    maskA=(dirn@axA)>thr; maskB=(dirn@axB)>thr
    idxA=np.where(maskA)[0]; idxB=np.where(maskB)[0]
    res0=float(np.median(cKDTree(obj).query(obj,k=2)[0][:,-1]))
    rng=np.random.default_rng(42)
    viewA=obj[idxA]+rng.normal(0,noise_scale*res0,(len(idxA),3))
    viewB=obj[idxB]@R.T+t+rng.normal(0,noise_scale*res0,(len(idxB),3))
    overlap_g=np.intersect1d(idxA,idxB)
    posA={g:r for r,g in enumerate(idxA)}; posB={g:r for r,g in enumerate(idxB)}
    a_rows=np.array([posA[g] for g in overlap_g])
    gt_pos=obj[overlap_g]
    res=float(np.median(cKDTree(viewA).query(viewA,k=2)[0][:,-1]))
    tol=1.5*res
    nA=feat_fpfh.estimate_point_normals(viewA,k=normal_k,orient_ref=[0,0,0])
    nB=feat_fpfh.estimate_point_normals(viewB,k=normal_k,orient_ref=t)
    fA=feat_fpfh.compute_fpfh(viewA,nA,k=feat_k,n_bins=11)
    fB=feat_fpfh.compute_fpfh(viewB,nB,k=feat_k,n_bins=11)
    # true B row for each overlap g:
    b_rows_true=np.array([posB[g] for g in overlap_g])
    # descriptor dist between true correspondences
    dtrue=np.linalg.norm(fA[a_rows]-fB[b_rows_true],axis=1)
    # NN match
    _,nn=cKDTree(fB).query(fA[a_rows],k=1)
    b_back=(viewB[nn]-t)@R
    err=np.linalg.norm(b_back-gt_pos,axis=1)
    rate=float((err<tol).mean())
    # how often NN == true b row
    exact=float((nn==b_rows_true).mean())
    print(f"[{tag}] noise={noise_scale} thr={thr} fk={feat_k} nk={normal_k}: "
          f"nA={len(idxA)} nB={len(idxB)} ov={len(overlap_g)} res={res:.4f} "
          f"dtrue={dtrue.mean():.4f} exact-Brow={exact:.3f} geomrate={rate:.3f}")

run(0.0, -0.35, tag="noNoise")
run(0.25, -0.35, tag="noise0.25")
run(0.0, -0.35, feat_k=100, tag="noNoise fk100")
run(0.0, 0.0, tag="noNoise thr0")   # bigger overlap interior
run(0.1, -0.35, tag="noise0.1")
run(0.0, -0.35, normal_k=24, feat_k=80, tag="noNoise nk24 fk80")
