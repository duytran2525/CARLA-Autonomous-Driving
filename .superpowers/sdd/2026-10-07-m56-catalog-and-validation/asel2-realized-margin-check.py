import json, glob, re, math, sys
from fractions import Fraction as F
def g(x): return float.fromhex(x['binary64']) if isinstance(x,dict) and 'binary64' in x else float(F(x['numerator'],x['denominator'])) if isinstance(x,dict) else float(x)
def best(s):
    b=None
    for f in sorted(glob.glob(f'm56_v6_pair_*/M56-P-{s}/pair-result.json')):
        d=json.load(open(f,encoding='utf-8'))
        if d.get('status')=='PASS': b=d
    return b
out={}
for s, role in (('O01','EGO'),('O02','EGO'),('O03','EGO'),('I03','EGO'),('I04','EGO'),('C01','NPC'),('C05','NPC'),('C08','NPC')):
    d=best(s); src=d['source_scene_dir']
    frames=[]
    for i in (0,2):
        m=re.search(r'frames=\((\d+)', d['metrics'][i]); frames.append(int(m.group(1)) if m else None)
    obs={}
    for f in glob.glob(str(__import__('pathlib').Path(src)/'run'/'native'/'observation'/'*.json')):
        o=json.load(open(f,encoding='utf-8'))
        if o.get('actors'): obs[o['frame']]=o
    vals=[]
    for fr in frames:
        sp=[]
        for k in range(fr-20, fr+1):
            o=obs.get(k)
            if not o: continue
            a=next(x for x in o['actors'] if x['role']==role)
            v=a['velocity']; v=[g(c) for c in (v if isinstance(v,list) else [v[k2] for k2 in ('x','y','z')])]
            sp.append(math.hypot(v[0],v[1]))
        vals.append(sum(sp)/len(sp) if sp else None)
    out[s]=vals; print(s, role, 'trigger frames', frames, 'mean speed [t-1s,t] A/B', [round(v,4) if v else v for v in vals], 'mean', round(sum(vals)/2,4) if None not in vals else None, flush=True)
k={'O01':1,'O02':2,'O03':3}
m=lambda s: sum(out[s])/2
for a,b in (('O01','O02'),('O02','O03'),('O01','O03'),('I03','I04')):
    d=abs(m(a)-m(b))/max(m(a),m(b)); print(a,b,'realized delta %.4f'%d, 'PASS' if d>=0.2 else 'FAIL (<0.20)')
