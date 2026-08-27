import numpy as np, ransac_fit as R
import sys
sys.path.insert(0,'tests')
# replicate the test fixtures
def u(v): v=np.asarray(v,float); return v/np.linalg.norm(v)

def cyl_cloud(seed=0,n=800,of=0.25,noise=0.01):
    rng=np.random.default_rng(seed)
    axis=u([0.2,0.3,1.0]); radius=1.2; axis_pt=np.array([0.5,-0.4,0.0])
    e1=u(np.cross(axis,[1,0,0])); e2=np.cross(axis,e1)
    n_out=int(n*of); n_in=n-n_out
    th=rng.uniform(0,2*np.pi,n_in); h=rng.uniform(-4,4,n_in)
    radial=np.cos(th)[:,None]*e1+np.sin(th)[:,None]*e2
    inl=axis_pt+radius*radial+h[:,None]*axis+rng.normal(0,noise,(n_in,3))
    n_inl=radial+rng.normal(0,noise,(n_in,3)); n_inl/=np.linalg.norm(n_inl,axis=1,keepdims=True)
    out=axis_pt+rng.uniform(-4,4,(n_out,3))
    nov=rng.normal(0,1,(n_out,3)); nov/=np.linalg.norm(nov,axis=1,keepdims=True)
    P=np.vstack([inl,out]); Nrm=np.vstack([n_inl,nov])
    is_out=np.zeros(n,bool); is_out[n_in:]=True
    perm=rng.permutation(n)
    return P[perm],Nrm[perm],axis,radius,axis_pt,is_out[perm]

print("=== cylinder actual error across seeds ===")
for seed in range(6):
    P,Nrm,axis,radius,axis_pt,is_out=cyl_cloud(seed)
    par,mask,info=R.ransac_cylinder(P,Nrm,thresh=0.05)
    ang=np.degrees(np.arccos(min(1,abs(par['axis']@axis))))
    rerr=abs(par['radius']-radius)
    # axis-point line error: distance between returned axis line and true axis line
    # perpendicular offset of returned point from true axis
    delta=par['point']-axis_pt
    perp=np.linalg.norm(delta-(delta@axis)*axis)
    excl=(~mask[is_out]).mean()
    print(f"seed{seed}: axis_ang={ang:5.2f}deg r_err={rerr:.4f} pt_perp={perp:.4f} out_excl={excl:.2f} n_in={info['n_inliers']}")

print("\n=== plane/sphere/line actual error across seeds ===")
def plane_cloud(seed):
    rng=np.random.default_rng(seed)
    normal=u([0.3,-0.5,1.0]); offset=0.7
    e1=u(np.cross(normal,[1,0,0])); e2=np.cross(normal,e1)
    n=600; n_out=int(n*0.3); n_in=n-n_out
    uv=rng.uniform(-5,5,(n_in,2))
    inl=normal*offset+uv[:,:1]*e1+uv[:,1:]*e2+rng.normal(0,0.01,(n_in,3))
    out=rng.uniform(-5,5,(n_out,3))
    P=np.vstack([inl,out]); perm=rng.permutation(n)
    return P[perm],normal,offset
for seed in range(6):
    P,normal,offset=plane_cloud(seed)
    par,mask,info=R.ransac_plane(P,thresh=0.05)
    ang=np.degrees(np.arccos(min(1,abs(par['normal']@normal))))
    # offset error: |d| should equal offset (since normal.x=offset -> normal.x-offset=0 -> d=-offset)
    derr=abs(abs(par['d'])-offset)
    print(f"plane seed{seed}: ang={ang:.3f}deg offset_err={derr:.4f}")
