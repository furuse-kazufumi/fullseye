import numpy as np, ransac_fit as R

def u(v):
    v=np.asarray(v,float); return v/np.linalg.norm(v)

print("=== ransac clean exact-recovery ===")
rng=np.random.default_rng(0)

# --- Plane: clean, no outliers ---
normal=u([0.2,-0.3,1.0]); off=0.7
e1=u(np.cross(normal,[1,0,0])); e2=np.cross(normal,e1)
uv=rng.uniform(-3,3,(200,2))
P=normal*off + uv[:,:1]*e1 + uv[:,1:]*e2
par,mask,info=R.ransac_plane(P,thresh=1e-6)
ang=np.degrees(np.arccos(min(1,abs(par["normal"]@normal))))
print(f"plane angle err={ang:.2e} deg  inliers={info['n_inliers']}/200")
# plane offset: for point on plane normal.x = off, so d should = -off (if normal aligned) 
print(f"plane d={par['d']:.4f} (expect ~ -0.7*sign)  normal={par['normal']}")

# --- Sphere clean ---
c=np.array([1.2,-0.7,2.0]); rad=1.5
v=rng.normal(0,1,(300,3)); v/=np.linalg.norm(v,axis=1,keepdims=True)
P=c+rad*v
par,mask,info=R.ransac_sphere(P,thresh=1e-6)
print(f"sphere center err={np.linalg.norm(par['center']-c):.2e} radius err={abs(par['radius']-rad):.2e}")

# --- Line clean ---
pt=np.array([0.5,-1,0.3]); d=u([1,0.4,-0.2])
t=rng.uniform(-5,5,(200,1))
P=pt+t*d
par,mask,info=R.ransac_line(P,thresh=1e-6)
print(f"line dir |cos|={abs(par['direction']@d):.6f}")
# verify 'point' lies on the true line: (point-pt) parallel to d
delta=par['point']-pt
perp=delta-(delta@d)*d
print(f"line point off-axis dist={np.linalg.norm(perp):.2e}")

# --- Cylinder clean ---
axis=u([0.2,0.3,1.0]); rad=1.2; axpt=np.array([0.5,-0.4,0.0])
e1=u(np.cross(axis,[1,0,0])); e2=np.cross(axis,e1)
th=rng.uniform(0,2*np.pi,400); h=rng.uniform(-4,4,400)
radial=np.cos(th)[:,None]*e1+np.sin(th)[:,None]*e2
P=axpt+rad*radial+h[:,None]*axis
Nrm=radial.copy()
par,mask,info=R.ransac_cylinder(P,Nrm,thresh=1e-4)
print(f"cyl axis |cos|={abs(par['axis']@axis):.6f} radius err={abs(par['radius']-rad):.2e}")
# verify returned 'point' is on the true axis line
delta=par['point']-axpt
perp=delta-(delta@axis)*axis
print(f"cyl point off-axis dist={np.linalg.norm(perp):.4f} (should be ~0 if point on true axis)")
# distance of returned point to axis line vs the true axis:
# The returned point should have same perpendicular position as true axis
