"""perf 2026-10-25 (3): admitted-source index + verified-source memo + trajectory decode memo in m56/evidence.py."""
import os
os.chdir(r'D:/AI/CARLA-Funny-Moments.worktrees/m56-v1')
p = 'm56/evidence.py'; s = open(p, encoding='utf-8').read()
old = '''def _admitted_source(evidence,ref):
    if not isinstance(ref,SourceRef) or ref not in evidence.source or _source_bytes(ref) is None or evidence.manifest is None:
        return False
    try:
        data=_source_bytes(evidence.manifest)
        if data is None:
            return False
        entries=_manifest_entries(data)
        return _sealed_source(ref,Path(evidence.manifest.uri).parent,entries)
    except (ValueError,TypeError,KeyError):
        return False'''
new = '''_VERIFIED_SOURCES = {}
_ADMISSION_INDEX = {}


def _source_ok(ref):
    """_source_bytes(ref) is not None, memoized by (ref, mtime_ns, size): a rewritten file is verified again.
    perf 2026-10-25: the uncached read+sha256 per frame pair dominated offline evaluation. ponytail: clear-all cache."""
    try:
        st=Path(ref.uri).stat()
    except (OSError,TypeError,ValueError):
        return _source_bytes(ref) is not None
    key=(ref,st.st_mtime_ns,st.st_size)
    hit=_VERIFIED_SOURCES.get(key)
    if hit is None:
        if len(_VERIFIED_SOURCES)>65536:
            _VERIFIED_SOURCES.clear()
        hit=_VERIFIED_SOURCES[key]=_source_bytes(ref) is not None
    return hit


def _admission_index(evidence):
    """(source set, manifest root, manifest entries) of one evidence bundle, or None when the manifest does not
    verify or parse; memoized by identity of (source tuple, manifest ref) with strong references."""
    key=(id(evidence.source),id(evidence.manifest))
    hit=_ADMISSION_INDEX.get(key)
    if hit is not None and hit[0] is evidence.source and hit[1] is evidence.manifest:
        return hit[2]
    try:
        data=_source_bytes(evidence.manifest)
        index=None if data is None else (frozenset(evidence.source),Path(evidence.manifest.uri).parent,
                                         _manifest_entries(data))
    except (ValueError,TypeError,KeyError):
        index=None
    if len(_ADMISSION_INDEX)>64:
        _ADMISSION_INDEX.clear()
    _ADMISSION_INDEX[key]=(evidence.source,evidence.manifest,index)
    return index


def _admitted_source(evidence,ref):
    if not isinstance(ref,SourceRef) or evidence.manifest is None:
        return False
    index=_admission_index(evidence)
    if index is None:
        return False
    sources,root,entries=index
    if ref not in sources or not _source_ok(ref):
        return False
    try:
        return _sealed_source(ref,root,entries)
    except (ValueError,TypeError,KeyError):
        return False'''
assert old in s; s = s.replace(old, new)
old = '''def _read_trajectory(ref):
    data=_source_bytes(ref)'''
new = '''_TRAJECTORIES = {}


def _read_trajectory(ref):
    """Memoized by SourceRef for successful reads (a verified trajectory decodes to the same immutable frames);
    perf 2026-10-25: it was decoded 4 times per evaluation (~47 s each). ponytail: bounded clear-all cache."""
    try:
        hit=_TRAJECTORIES.get(ref)
    except TypeError:
        return _read_trajectory_uncached(ref)
    if hit is not None and _source_ok(ref):
        return hit
    result=_read_trajectory_uncached(ref)
    if result is not None:
        if len(_TRAJECTORIES)>16:
            _TRAJECTORIES.clear()
        _TRAJECTORIES[ref]=result
    return result


def _read_trajectory_uncached(ref):
    data=_source_bytes(ref)'''
assert old in s; s = s.replace(old, new)
open(p, 'w', encoding='utf-8').write(s)

p = 'tests/m56/test_v5_perf_caches.py'; t = open(p, encoding='utf-8').read()
t += '''

def test_source_ok_reverifies_a_rewritten_file(tmp_path):
    import os
    from m56.evidence import _source_ok
    path = tmp_path / 'blob.bin'; path.write_bytes(b'abc')
    ref = SourceRef(str(path), hashlib.sha256(b'abc').hexdigest(), 3, '1', 'literal', 'SYNTHETIC_TEST')
    assert _source_ok(ref) and _source_ok(ref)
    path.write_bytes(b'abd'); os.utime(path, ns=(10 ** 18, 10 ** 18))
    assert not _source_ok(ref)
'''
open(p, 'w', encoding='utf-8').write(t)
print('ok')
