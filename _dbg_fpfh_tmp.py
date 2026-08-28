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

obj=lumpy(3000)
R=rot([0.3,1,0.2],58.0); t=np.array([2.,-1.,0.5])
A=obj.copy()
B=obj@R.T+t
nA=feat_fpfh.estimate_point_normals(A,k=16,orient_ref=[0,0,0])
nB=feat_fpfh.estimate_point_normals(B,k=16,orient_ref=t)
nB_pred=(nA@R.T)
cos=np.einsum('ij,ij->i',nB,nB_pred)
print("normal consistency cos (mean,min,frac>0.9):",round(cos.mean(),4),round(cos.min(),4),round(float((cos>0.9).mean()),4))

for fk in (33, 60, 100):
    fA=feat_fpfh.compute_fpfh(A,nA,k=fk,n_bins=11)
    fB=feat_fpfh.compute_fpfh(B,nB,k=fk,n_bins=11)
    dtrue=np.linalg.norm(fA-fB,axis=1)
    rng=np.random.default_rng(0); perm=rng.permutation(len(fB))
    drand=np.linalg.norm(fA-fB[perm],axis=1)
    _,nn=cKDTree(fB).query(fA,k=1)
    res=float(np.median(cKDTree(A).query(A,k=2)[0][:,-1]))
    correct_idx=(nn==np.arange(len(A))).mean()
    b_back=(B[nn]-t)@R
    err=np.linalg.norm(b_back-A,axis=1)
    print(f"fk={fk}: dtrue={dtrue.mean():.4f} drand={drand.mean():.4f} | exact-idx={correct_idx:.3f} geom(1.5res)={float((err<1.5*res).mean()):.3f} geom(3res)={float((err<3*res).mean()):.3f}")
print("res=",round(res,4))
