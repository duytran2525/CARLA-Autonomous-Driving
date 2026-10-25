"""perf 2026-10-25 (5): _safe_path verifies each ancestor with ONE lstat (link + junction/reparse check) and skips the
costly resolve() when every ancestor still has the identity it had when it was fully verified."""
import os
os.chdir(r'D:/AI/CARLA-Funny-Moments.worktrees/m56-v1')
p = 'm56/evidence.py'; s = open(p, encoding='utf-8').read()
old = """    path=root.joinpath(*parts)
    for parent in (path,*path.parents):
        if parent==root.parent:
            break
        if parent.is_symlink() or (hasattr(parent,'is_junction') and parent.is_junction()):
            raise ValueError('PATH_REJECTED_LINK')
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('PATH_REJECTED')
    return path"""
new = """    path=root.joinpath(*parts)
    # perf 2026-10-25: one lstat per ancestor (symlink or Windows reparse point = junction) instead of is_symlink +
    # is_junction, and the resolve() containment check only when an ancestor is new or changed identity since its
    # last full verification (identity = st_dev, st_ino, st_mode, reparse flag). A directory swapped for a link
    # changes identity and is fully re-verified. ponytail: bounded clear-all cache.
    identities=[]
    for parent in (path,*path.parents):
        if parent==root.parent:
            break
        try:
            st=os.lstat(parent)
        except FileNotFoundError:
            identities.append((str(parent),None));continue
        except OSError:
            raise ValueError('PATH_REJECTED_LINK')
        reparse=bool(getattr(st,'st_file_attributes',0) & 0x400)  # FILE_ATTRIBUTE_REPARSE_POINT
        if stat.S_ISLNK(st.st_mode) or reparse:
            raise ValueError('PATH_REJECTED_LINK')
        identities.append((str(parent),(st.st_dev,st.st_ino,st.st_mode)))
    ancestors=identities[1:]
    if any(i is None for _,i in ancestors) or any(_SAFE_DIRS.get(k)!=i for k,i in ancestors):
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('PATH_REJECTED')
        if len(_SAFE_DIRS)>4096:
            _SAFE_DIRS.clear()
        for k,i in ancestors:
            if i is not None:
                _SAFE_DIRS[k]=i
    return path"""
assert old in s; s = s.replace(old, new)
old = """def _safe_path(root: Path, relative: str) -> Path:"""
new = """_SAFE_DIRS = {}


def _safe_path(root: Path, relative: str) -> Path:"""
assert s.count(old) == 1; s = s.replace(old, new)
if '\nimport stat' not in s and 'import stat\n' not in s:
    s = s.replace('import hashlib', 'import hashlib, stat', 1) if 'import hashlib,' not in s else s.replace('import hashlib,', 'import hashlib, stat,', 1)
open(p, 'w', encoding='utf-8').write(s)

p = 'tests/m56/test_v5_perf_caches.py'; t = open(p, encoding='utf-8').read()
t += '''

def test_safe_path_cache_still_rejects_a_directory_swapped_for_a_junction(tmp_path):
    import os, shutil, subprocess, pytest
    from m56.evidence import _safe_path
    root = tmp_path / 'run'; (root / 'native').mkdir(parents=True)
    assert _safe_path(root, 'native/a.json') == root / 'native' / 'a.json'
    assert _safe_path(root, 'native/b.json') == root / 'native' / 'b.json'  # cached ancestors
    outside = tmp_path / 'outside'; outside.mkdir()
    shutil.rmtree(root / 'native')
    made = subprocess.run(['cmd', '/c', 'mklink', '/J', str(root / 'native'), str(outside)], capture_output=True)
    if made.returncode != 0:
        pytest.skip('junction creation unavailable')
    with pytest.raises(ValueError, match='PATH_REJECTED'):
        _safe_path(root, 'native/c.json')
'''
open(p, 'w', encoding='utf-8').write(t)
print('ok')
