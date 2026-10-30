# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0.
"""Bonded 4-mm elastic-layer kernels used by the FingerVision benchmark.

The axisymmetric solver uses bilinear Q4 displacement elements.  Deviatoric
terms are integrated at 2x2 Gauss points and the volumetric term at one point
(selective reduced integration), avoiding the severe locking of ordinary Q4
elements as nu approaches 0.5.  z=0 is bonded; z=h is the contact/marker face.
"""
from __future__ import annotations

from functools import lru_cache
import math
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve


def _shape(xi, eta):
    n = .25*np.array([(1-xi)*(1-eta),(1+xi)*(1-eta),(1+xi)*(1+eta),(1-xi)*(1+eta)])
    d = .25*np.array([[-(1-eta),-(1-xi)],[(1-eta),-(1+xi)],[(1+eta),(1+xi)],[-(1+eta),(1-xi)]])
    return n,d


def _bmat(coords, xi, eta):
    n,d=_shape(xi,eta); jac=d.T@coords; grad=d@np.linalg.inv(jac)
    r=max(float(n@coords[:,0]),1e-9); b=np.zeros((4,8))
    for i in range(4):
        b[0,2*i]=grad[i,0]; b[1,2*i+1]=grad[i,1]; b[2,2*i]=n[i]/r
        b[3,2*i]=grad[i,1]; b[3,2*i+1]=grad[i,0]
    return b,n,r,np.linalg.det(jac)


@lru_cache(maxsize=32)
def axisymmetric_bonded_layer(nu: float, nr: int=64, nz: int=12, load_radius_mm: float=6.,
                              force_n: float=1., e_pa: float=180e3, h_mm: float=4., rmax_mm: float=32.):
    """Return surface ``(r, ur, uz)`` for a Hertz-shaped normal pressure."""
    h=h_mm*1e-3; rmax=rmax_mm*1e-3; a=load_radius_mm*1e-3
    rs=np.linspace(0,rmax,nr+1); zs=np.linspace(0,h,nz+1)
    nodes=np.array([(r,z) for z in zs for r in rs]); elems=[]
    for j in range(nz):
        for i in range(nr):
            q=j*(nr+1)+i; elems.append((q,q+1,q+1+nr+1,q+nr+1))
    mu=e_pa/(2*(1+nu)); bulk=e_pa/(3*(1-2*nu))
    pdev=np.eye(4)-np.outer([1,1,1,0],[1,1,1,0])/3
    ddev=np.diag([2*mu,2*mu,2*mu,mu])@pdev
    dv=bulk*np.outer([1,1,1,0],[1,1,1,0]); rows=[]; cols=[]; vals=[]
    gp=(-1/math.sqrt(3),1/math.sqrt(3))
    for en in elems:
        c=nodes[list(en)]; ke=np.zeros((8,8))
        for x in gp:
            for y in gp:
                b,_,r,det=_bmat(c,x,y); ke += b.T@ddev@b*(2*math.pi*r*det)
        b,_,r,det=_bmat(c,0,0); ke += b.T@dv@b*(2*math.pi*r*det*4)
        dof=np.ravel([[2*q,2*q+1] for q in en])
        for ii,I in enumerate(dof):
            for jj,J in enumerate(dof): rows.append(I); cols.append(J); vals.append(ke[ii,jj])
    nd=2*len(nodes); k=coo_matrix((vals,(rows,cols)),shape=(nd,nd)).tocsr(); f=np.zeros(nd)
    # p(r)=p0 sqrt(1-r^2/a^2), whose integral is 2*pi*p0*a^2/3.
    p0=3*force_n/(2*math.pi*a*a)
    top=nz*(nr+1)
    for i in range(nr):
        r0,r1=rs[i],rs[i+1]
        for x in gp:
            n=np.array([(1-x)/2,(1+x)/2]); r=n@[r0,r1]
            p=p0*math.sqrt(max(0,1-(r/a)**2)) if r<a else 0
            w=math.pi*(r1-r0)*r
            f[2*(top+i)+1]-=n[0]*p*w; f[2*(top+i+1)+1]-=n[1]*p*w
    fixed=[]
    for i in range(nr+1): fixed += [2*i,2*i+1]
    fixed += [2*(j*(nr+1)) for j in range(1,nz+1)]
    free=np.setdiff1d(np.arange(nd),np.unique(fixed)); u=np.zeros(nd); u[free]=spsolve(k[free][:,free],f[free])
    ids=top+np.arange(nr+1)
    return rs, u[2*ids], -u[2*ids+1]


def halfspace_normal(r, nu, force_n=1., e_pa=180e3, load_radius_mm=6.):
    """Boussinesq displacement outside a regularised circular contact."""
    r=np.asarray(r,float); a=load_radius_mm*1e-3; rr=np.sqrt(r*r+a*a/4)
    g=e_pa/(2*(1+nu)); uz=(1-nu)*force_n/(2*math.pi*g*rr)
    ur=(1-2*nu)*(1+nu)*force_n/(4*math.pi*e_pa*rr)
    return ur,uz


def convergence(nu=.48):
    """Successive surface peak and lateral-peak errors for the mesh gate."""
    out=[]; prev=None
    for nr,nz in ((48,10),(72,14),(96,18)):
        r,ur,uz=axisymmetric_bonded_layer(nu,nr,nz)
        val=np.array([np.max(np.abs(ur)),uz[0]])
        out.append((nr,nz,*val,math.nan if prev is None else float(np.max(np.abs(val-prev)/np.maximum(np.abs(val),1e-12)))))
        prev=val
    return out


def normal_kernel(points, source, nu=.48, force_n=1., load_radius_mm=2.):
    """Axisymmetric FEM normal-load column, translated to ``source``."""
    d=np.asarray(points)-np.asarray(source); rr=np.linalg.norm(d,axis=1)
    r,ur,uz=axisymmetric_bonded_layer(float(nu),72,14,float(load_radius_mm),1.)
    ur_i=np.interp(rr,r,ur,left=ur[0],right=0.); uz_i=np.interp(rr,r,uz,left=uz[0],right=0.)
    radial=np.divide(d,rr[:,None],out=np.zeros_like(d),where=rr[:,None]>1e-12)
    return force_n*np.column_stack((radial*ur_i[:,None],uz_i))


def tangential_kernel(points, source, force_xy, nu=.48, e_pa=180e3, h_mm=4., core_mm=1.5):
    """Bonded-layer tangential Green column.

    A regularised Cerruti tensor plus its opposite-sign image at 2h enforces
    the bonded-base displacement to first order.  This is the tangential
    companion of the axisymmetric normal FEM and is used for both forward
    tables and inverse influence columns.
    """
    d=np.asarray(points)-np.asarray(source); f=np.asarray(force_xy,float)
    g=e_pa/(2*(1+nu)); core=core_mm*1e-3; h=h_mm*1e-3
    def term(depth):
        rr=np.sqrt(np.sum(d*d,axis=1)+depth*depth+core*core)
        return (2*(1-nu)*f/rr[:,None]+2*nu*d*np.sum(d*f,axis=1)[:,None]/rr[:,None]**3)/(4*math.pi*g)
    return term(0.)-term(2*h)
