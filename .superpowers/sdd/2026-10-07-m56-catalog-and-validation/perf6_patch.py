"""perf 2026-10-25 (6): identity digest memo for every deeply frozen m56.model record (and tuples of them); numpy
float prefilter in the exact route projection."""
import os
os.chdir(r'D:/AI/CARLA-Funny-Moments.worktrees/m56-v1')
p = 'm56/catalog.py'; s = open(p, encoding='utf-8').read()
old = """def _digest(record: object) -> str:
    # A CompiledFixture is deeply frozen at construction (model._freeze), so its digest is memoized by identity
    # (strong ref kept) for per-tick online detection. ponytail: bounded clear-all cache.
    if type(record).__name__ in ('CompiledFixture', 'DirectedRoute'):  # DirectedRoute: frozen tuples (perf 2026-10-25)
        hit = _FIXTURE_DIGESTS.get(id(record))
        if hit is not None and hit[0] is record:
            return hit[1]
        if len(_FIXTURE_DIGESTS) > 256:
            _FIXTURE_DIGESTS.clear()
        _FIXTURE_DIGESTS[id(record)] = (record, _encode_digest(record))
        return _FIXTURE_DIGESTS[id(record)][1]
    return _encode_digest(record)"""
new = """def _frozen_record(record: object) -> bool:
    \"\"\"m56.model records are deeply frozen at construction (model.dataclass -> _freeze: tuples, MappingProxyType), so a
    record or a tuple of records never changes after creation.\"\"\"
    if type(record).__module__ == 'm56.model' and hasattr(record, '__dataclass_fields__'):
        return True
    return type(record) is tuple and bool(record) and all(type(x).__module__ == 'm56.model'
                                                           and hasattr(x, '__dataclass_fields__') for x in record)


def _digest(record: object) -> str:
    # Deeply frozen records (model._freeze) are memoized by identity with a strong reference (no id reuse): online
    # detection and offline evaluation digest the same frames/actors/fixture many times (perf 2026-10-25: ~35% of
    # offline evaluation). ponytail: bounded clear-all cache.
    if _frozen_record(record):
        hit = _FIXTURE_DIGESTS.get(id(record))
        if hit is not None and hit[0] is record:
            return hit[1]
        if len(_FIXTURE_DIGESTS) > 65536:
            _FIXTURE_DIGESTS.clear()
        _FIXTURE_DIGESTS[id(record)] = (record, _encode_digest(record))
        return _FIXTURE_DIGESTS[id(record)][1]
    return _encode_digest(record)"""
assert old in s; s = s.replace(old, new)
open(p, 'w', encoding='utf-8').write(s)

p = 'm56/geometry.py'; s = open(p, encoding='utf-8').read()
old = """    table=[(a.x,a.y,a.z,b.x-a.x,b.y-a.y,b.z-a.z) for a,b in zip(route.transforms,route.transforms[1:])]
    _ROUTE_FLOATS[id(route)]=(route,table)
    return table"""
new = """    import numpy as np
    table=[(a.x,a.y,a.z,b.x-a.x,b.y-a.y,b.z-a.z) for a,b in zip(route.transforms,route.transforms[1:])]
    arr=np.array(table,dtype=float).reshape(-1,6)
    finite=bool(np.isfinite(arr).all()) and all(isfinite(v) for t in route.transforms for v in (t.x,t.y,t.z))
    degenerate=[i for i,(_,_,_,dx,dy,dz) in enumerate(table) if dx==0 and dy==0 and dz==0]
    _ROUTE_FLOATS[id(route)]=(route,(table,arr,finite,degenerate))
    return _ROUTE_FLOATS[id(route)][1]"""
assert old in s; s = s.replace(old, new)
old = """    px,py,pz=point;dists=[]
    for sx,sy,sz,dx,dy,dz in _route_floats(route):
        if not all(isfinite(v) for v in (sx,sy,sz,dx,dy,dz,sx+dx,sy+dy,sz+dz)):
            return BlockedFixture(('INVALID_ROUTE_PROJECTION_INPUT',))
        n=dx*dx+dy*dy+dz*dz
        if dx==0 and dy==0 and dz==0:
            return BlockedFixture(('DEGENERATE_ROUTE_SEGMENT',))
        u=((px-sx)*dx+(py-sy)*dy+(pz-sz)*dz)/n if n>0 else 0.
        u=0. if u<0 else 1. if u>1 else u
        qx,qy,qz=sx+u*dx-px,sy+u*dy-py,sz+u*dz-pz
        dists.append(qx*qx+qy*qy+qz*qz)
    m=min(dists)
    # Float error of a squared distance here is ~1e-10 for CARLA coordinates; the margin is orders of magnitude wider.
    margin=1e-6*(1.+m)+1e-6
    keep=[i for i,d in enumerate(dists) if d<=m+margin]"""
new = """    import numpy as np
    px,py,pz=point
    table,arr,finite,degenerate=_route_floats(route)
    if not finite:  # same first-failure order as the scalar scan: the first bad segment decides
        for i,(sx,sy,sz,dx,dy,dz) in enumerate(table):
            if not all(isfinite(v) for v in (sx,sy,sz,dx,dy,dz,sx+dx,sy+dy,sz+dz)):
                return BlockedFixture(('INVALID_ROUTE_PROJECTION_INPUT',))
            if dx==0 and dy==0 and dz==0:
                return BlockedFixture(('DEGENERATE_ROUTE_SEGMENT',))
    if degenerate:
        return BlockedFixture(('DEGENERATE_ROUTE_SEGMENT',))
    S,D=arr[:,:3],arr[:,3:]
    n=D[:,0]*D[:,0]+D[:,1]*D[:,1]+D[:,2]*D[:,2]
    u=np.clip(((px-S[:,0])*D[:,0]+(py-S[:,1])*D[:,1]+(pz-S[:,2])*D[:,2])/n,0.,1.)
    dists=(S[:,0]+u*D[:,0]-px)**2+(S[:,1]+u*D[:,1]-py)**2+(S[:,2]+u*D[:,2]-pz)**2
    m=float(dists.min())
    # Float error of a squared distance here is ~1e-10 for CARLA coordinates; the margin is orders of magnitude wider,
    # so the numpy prefilter (perf 2026-10-25) keeps every segment that can hold the exact minimum.
    margin=1e-6*(1.+m)+1e-6
    keep=np.nonzero(dists<=m+margin)[0].tolist()"""
assert old in s; s = s.replace(old, new)
open(p, 'w', encoding='utf-8').write(s)
print('ok')
