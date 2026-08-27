import numpy as np, ransac_fit as R
np.seterr(all='ignore')

print("=== ransac degeneracies ===")
rng=np.random.default_rng(0)

# 1. Plane: all collinear points (degenerate plane) -> fit_plane_ls normal ambiguous
P=np.column_stack([np.linspace(0,10,50),np.zeros(50),np.zeros(50)])  # all on x-axis
try:
    par,mask,info=R.ransac_plane(P,thresh=0.01)
    print("collinear plane: normal=",par['normal'],"n_inliers=",info['n_inliers'])
except Exception as e:
    print("collinear plane raised:",type(e).__name__,e)

# 2. thresh=0 (nothing strictly < 0)
P=rng.normal(0,1,(100,3))
par,mask,info=R.ransac_plane(P,thresh=0.0)
print("thresh=0 plane n_inliers=",info['n_inliers'],"(mask all?)",mask.all())

# 3. Sphere: coplanar points (all z=0) -> _fit_sphere_ls returns None often
P=np.column_stack([rng.uniform(-1,1,60),rng.uniform(-1,1,60),np.zeros(60)])
try:
    par,mask,info=R.ransac_sphere(P,thresh=0.05)
    print("coplanar sphere: center=",par['center'],"radius=",par['radius'])
except Exception as e:
    print("coplanar sphere raised:",type(e).__name__,e)

# 4. Line with duplicate points (all same)
P=np.tile([1.0,2,3],(20,1))
try:
    par,mask,info=R.ransac_line(P,thresh=0.01)
    print("identical-pts line: dir=",par['direction'],"n_inliers=",info['n_inliers'])
except Exception as e:
    print("identical-pts line raised:",type(e).__name__,e)

# 5. Cylinder with all-parallel normals (flat sheet, not cylinder)
P=rng.uniform(-1,1,(50,3)); P[:,2]=0
Nrm=np.tile([0,0,1.0],(50,1))
try:
    par,mask,info=R.ransac_cylinder(P,Nrm,thresh=0.05)
    print("parallel-normals cyl: axis=",par['axis'],"r=",par['radius'],"n_in=",info['n_inliers'])
except Exception as e:
    print("parallel-normals cyl raised:",type(e).__name__,e)

# 6. Extreme outliers 60% for plane - does it still recover?
def u(v): v=np.asarray(v,float); return v/np.linalg.norm(v)
normal=u([0.2,-0.3,1.0]); off=0.7
e1=u(np.cross(normal,[1,0,0])); e2=np.cross(normal,e1)
n=600; n_out=int(0.6*n); n_in=n-n_out
uv=rng.uniform(-5,5,(n_in,2))
inl=normal*off+uv[:,:1]*e1+uv[:,1:]*e2+rng.normal(0,0.01,(n_in,3))
out=rng.uniform(-5,5,(n_out,3))
P=np.vstack([inl,out]); perm=rng.permutation(n); P=P[perm]
par,mask,info=R.ransac_plane(P,thresh=0.05)
ang=np.degrees(np.arccos(min(1,abs(par['normal']@normal))))
print(f"60% outliers plane: angle err={ang:.2f} deg n_inliers={info['n_inliers']}")
