"""Local integrity/link audit; no models, GPU, Slurm or network access."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[3]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, default=ROOT / 'docs/agent-archive/20261005_214213')
    parser.add_argument('--output', type=Path, default=Path(__file__).with_name('integrity.json'))
    args = parser.parse_args()
    originals = json.loads((args.archive / 'original-agent-checksums.json').read_text())
    protected = json.loads((args.archive / 'protected-project-before.json').read_text())
    failures = []
    if (ROOT / '.agent').exists():
        failures.append({'kind': 'legacy-root-recreated', 'path': '.agent'})
    consolidation = json.loads((ROOT / '.agents/consolidation.json').read_text())
    if consolidation.get('active_root') != '.agents' or consolidation.get('removed_active_root') != '.agent':
        failures.append({'kind': 'invalid-consolidation-record'})
    for label, base, mapping in [('original-agent', args.archive / 'original-agent', originals),
                                  ('protected-project', ROOT, protected)]:
        for name, expected in mapping.items():
            p = base / name
            if not p.is_file() or sha(p) != expected:
                failures.append({'kind': label, 'path': str(p), 'reason': 'MISSING_OR_CHANGED'})
    docs = [ROOT / 'AGENTS.md']
    docs += list((ROOT / '.agents').rglob('*.md'))
    docs += [args.archive / 'README.md']
    links = 0
    for p in docs:
        text = p.read_text(encoding='utf-8')
        for target in re.findall(r'!?\[[^\]\n]*\]\(([^)\n]+)\)', text):
            if '://' in target or target.startswith(('mailto:', '#')):
                continue
            target = target.split('#', 1)[0]
            resolved = p.parent / target
            links += 1
            if not resolved.exists():
                failures.append({'kind': 'broken-local-link', 'path': str(p), 'target': target})
    refs = ROOT / '.agents/skills/run-carla-uit-hpc/references'
    metadata = json.loads((refs / 'source-metadata.json').read_text(encoding='utf-8'))
    if sha(refs / 'uit-source-transcript.md') != metadata['transcript_sha256']:
        failures.append({'kind': 'source-transcript-changed'})
    for name, expected in metadata['image_sha256'].items():
        p = refs / 'images' / name
        if not p.exists() or sha(p) != expected:
            failures.append({'kind': 'source-image-changed', 'path': str(p)})
    source = Path(metadata['original_local_path'])
    compared_original_docx = source.is_file()
    if compared_original_docx:
        if sha(source) != metadata['sha256']:
            failures.append({'kind': 'original-docx-changed'})
        with zipfile.ZipFile(source) as z:
            for name in metadata['image_sha256']:
                if z.read('word/media/' + name) != (refs / 'images' / name).read_bytes():
                    failures.append({'kind': 'image-not-identical-to-docx', 'name': name})
    migration = json.loads((args.archive / 'migration-report.json').read_text())
    active_names = sorted(p.name for p in (ROOT / '.agents/skills').iterdir() if p.is_dir())
    expected_names = sorted(migration['retained_adapted_skills'] + [migration['new_skill']])
    if active_names != expected_names:
        failures.append({'kind': 'unexpected-active-inventory', 'actual': active_names})
    status = subprocess.run(['git', 'status', '--short'], cwd=ROOT, capture_output=True,
                            text=True, timeout=5, check=True).stdout
    before = (args.archive / 'git-status-before.txt').read_text()
    before_lines, now_lines = before.splitlines(), status.splitlines()
    # Only the explicitly approved removal of the old configuration root is exempt.
    allowed_removed = {'?? .agent/'} if not (ROOT / '.agent').exists() and consolidation.get('approved_by_user') is True else set()
    missing_old = [line for line in before_lines if line not in now_lines and line not in allowed_removed]
    if missing_old:
        failures.append({'kind': 'pre-existing-status-changed', 'entries': missing_old})
    result = dict(passed=not failures, original_agent_files_checked=len(originals),
                  protected_project_files_checked=len(protected), active_skill_count=len(active_names),
                  excluded_skill_count=len(migration['excluded_skills']), local_links_checked=links,
                  markdown_files_checked=len(docs), source_images_checked=len(metadata['image_sha256']),
                  original_docx_compared=compared_original_docx, source_docx_sha256=metadata['sha256'],
                  active_configuration_root='.agents', legacy_root_absent=not (ROOT / '.agent').exists(),
                  git_status_after=status, failures=failures,
                  limitations=['Link audit checks local existence, not external URL availability/model obedience.',
                               'Original DOCX comparison is skipped if the provenance source path is unavailable.',
                               'Integrity covers the saved file set, not arbitrary filesystem writes by another session.'])
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
