"""perf 2026-10-25 (4): numpy batch for the C4 selection (float stations of all component vertices, closest pair)."""
import os
os.chdir(r'D:/AI/CARLA-Funny-Moments.worktrees/m56-v1')
p = 'm56/geometry.py'; s = open(p, encoding='utf-8').read()
old = """def _selected_component(intersections, queries, binding):"""
new = """def _float_stations(points, route):
    \"\"\"Batch _float_station (same formula, same left-to-right operation order, first minimum wins), numpy-vectorized:
    perf 2026-10-25, the per-vertex Python scan made compile_fixture of a disconnected C4 scene take minutes.\"\"\"
    import numpy as np
    t=route.transforms
    A=np.array([(a.x,a.y,a.z) for a in t[:-1]],dtype=float);B=np.array([(b.x,b.y,b.z) for b in t[1:]],dtype=float)
    S=np.array([float(x) for x in route.arc[:-1]]);T=np.array([float(x) for x in route.arc[1:]])
    D=B-A;n=D[:,0]*D[:,0]+D[:,1]*D[:,1]+D[:,2]*D[:,2]
    out=[]
    P=np.array(points,dtype=float).reshape(-1,3)
    for k in range(0,len(P),256):
        Q=P[k:k+256,None,:]-A[None,:,:]
        dot=Q[...,0]*D[None,:,0]+Q[...,1]*D[None,:,1]+Q[...,2]*D[None,:,2]
        with np.errstate(divide='ignore',invalid='ignore'):
            f=np.where(n[None,:]==0,0.,np.maximum(0.,np.minimum(1.,dot/n[None,:])))
        E=(Q[...,0]-f*D[None,:,0])**2+(Q[...,1]-f*D[None,:,1])**2+(Q[...,2]-f*D[None,:,2])**2
        i=np.argmin(E,axis=1);rows=np.arange(len(i))
        out.extend((S[i]+f[rows,i]*(T[i]-S[i])).tolist())
    return out


def _closest_transform_pair(ego, npc):
    \"\"\"First (ego, npc) transform pair with the minimum squared 3D distance (same order as the nested min).\"\"\"
    import numpy as np
    E=np.array([(t.x,t.y,t.z) for t in ego.transforms],dtype=float);N=np.array([(t.x,t.y,t.z) for t in npc.transforms],dtype=float)
    best=None
    for k in range(0,len(E),256):
        d=((E[k:k+256,None,0]-N[None,:,0])**2+(E[k:k+256,None,1]-N[None,:,1])**2)+(E[k:k+256,None,2]-N[None,:,2])**2
        j=int(np.argmin(d));r,c=divmod(j,d.shape[1])
        if best is None or d[r,c]<best[0]:
            best=(d[r,c],k+r,c)
    return ego.transforms[best[1]],npc.transforms[best[2]]


def _selected_component(intersections, queries, binding):"""
assert s.count(old) == 1; s = s.replace(old, new)
old = """    a,b=min(((s,t) for s in ego.transforms for t in npc.transforms),
            key=lambda st:sum((u-v)**2 for u,v in zip((st[0].x,st[0].y,st[0].z),(st[1].x,st[1].y,st[1].z))))"""
new = """    a,b=_closest_transform_pair(ego,npc)"""
assert old in s; s = s.replace(old, new)
old = """            st=[_float_station(v,route) for box in comp for v in box]"""
new = """            st=_float_stations([v for box in comp for v in box],route)"""
assert old in s; s = s.replace(old, new)
open(p, 'w', encoding='utf-8').write(s)

p = 'tests/m56/test_v5_perf_caches.py'; t = open(p, encoding='utf-8').read()
t += '''

def test_vectorized_c4_helpers_equal_the_python_reference():
    import math, random
    from m56.geometry import _float_station, _float_stations, _closest_transform_pair
    rnd = random.Random(4)
    pts = tuple(Transform6(300 + 40 * math.cos(i / 160), -200 + 40 * math.sin(i / 160), .1 * math.sin(i / 50), 0., 0., 0.) for i in range(700))
    arc = [F(0)]
    for a, b in zip(pts, pts[1:]):
        arc.append(arc[-1] + F(str(round(math.dist((a.x, a.y, a.z), (b.x, b.y, b.z)), 6))))
    route = DirectedRoute((), pts, tuple(arc), 'b' * 64, (), arc[-1])
    probe = [(t.x + rnd.uniform(-5, 5), t.y + rnd.uniform(-5, 5), t.z) for t in rnd.sample(pts, 300)]
    assert _float_stations(probe, route) == [_float_station(p, route) for p in probe]
    other = DirectedRoute((), tuple(Transform6(t.x + 3., t.y - 2., t.z, 0., 0., 0.) for t in pts[::3]), tuple(arc[::3]), 'b' * 64, (), arc[-1])
    ref = min(((a, b) for a in route.transforms for b in other.transforms),
              key=lambda st: sum((u - v) ** 2 for u, v in zip((st[0].x, st[0].y, st[0].z), (st[1].x, st[1].y, st[1].z))))
    assert _closest_transform_pair(route, other) == ref
'''
open(p, 'w', encoding='utf-8').write(t)
print('ok')
