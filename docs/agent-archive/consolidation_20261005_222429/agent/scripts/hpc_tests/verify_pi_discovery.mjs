// Read-only resource-loader integration test. No agent session, model, auth or server job.
// Usage: node verify_pi_discovery.mjs <installed-pi-dist-dir> <archive-dir>
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const dist = process.argv[2];
const archive = process.argv[3];
assert(dist && archive, 'Pass installed Pi dist and original .agent archive directories');
const { DefaultResourceLoader } = await import(pathToFileURL(path.join(dist, 'core/resource-loader.js')).href);
const { SettingsManager } = await import(pathToFileURL(path.join(dist, 'core/settings-manager.js')).href);
const { loadSkillsFromDir, formatSkillsForPrompt } = await import(pathToFileURL(path.join(dist, 'core/skills.js')).href);
const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '../../..');
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'carla-pi-resource-test-'));
const expected = ['agent-engineering', 'code-review-4eyes', 'consulting', 'debugging',
  'docs-seeker', 'documentation', 'problem-solving', 'run-carla-uit-hpc', 'soft-skills'].sort();
const results = [];
const compatibility = loadSkillsFromDir({ dir: path.join(root, '.agent/skills'), source: 'project' });
assert.deepEqual(compatibility.skills.map(s => s.name).sort(), expected, 'Compatibility entry points malformed');
assert.equal(compatibility.diagnostics.length, 0, 'Compatibility frontmatter diagnostics');
try {
  const baseline = path.join(temp, 'baseline');
  fs.mkdirSync(baseline);
  fs.cpSync(path.join(archive, 'original-agent/skills'), path.join(baseline, '.agent/skills'), { recursive: true });
  // Stop project skill ancestor traversal at the controlled repository boundary.
  fs.mkdirSync(path.join(baseline, '.git'));
  for (const [label, cwd, trusted] of [['legacy-baseline', baseline, true],
      ['trusted-root', root, true], ['trusted-nested', path.join(root, '.agent/scripts'), true],
      ['untrusted-root', root, false]]) {
    const loader = new DefaultResourceLoader({ cwd, agentDir: path.join(temp, 'empty-agent'),
      settingsManager: SettingsManager.inMemory({}, { projectTrusted: trusted }),
      noExtensions: true, noPromptTemplates: true, noThemes: true });
    await loader.reload();
    const { skills, diagnostics } = loader.getSkills();
    const canonicalBase = path.join(root, '.agents/skills') + path.sep;
    const local = skills.filter(s => s.filePath.startsWith(canonicalBase));
    const localNames = local.map(s => s.name).sort();
    const rootContexts = loader.getAgentsFiles().agentsFiles.filter(f => f.path === path.join(root, 'AGENTS.md'));
    if (label.startsWith('trusted')) {
      assert.deepEqual(localNames, expected, `${label}: canonical skills not actually discovered`);
      const advertisedNames = [...formatSkillsForPrompt(local).matchAll(/<name>([^<]+)<\/name>/g)].map(m => m[1]).sort();
      assert.deepEqual(advertisedNames, expected, `${label}: canonical skills hidden from model selection`);
      assert.equal(rootContexts.length, 1, `${label}: root policy routing context not loaded`);
      assert.equal(diagnostics.filter(d => d.path?.startsWith(canonicalBase)).length, 0,
        `${label}: canonical skill frontmatter/collision warnings`);
    } else {
      assert.equal(localNames.length, 0, `${label}: project skills unexpectedly loaded`);
      if (label === 'untrusted-root') assert.equal(rootContexts.length, 1,
        'Root AGENTS must warn even before project resource trust');
      if (label === 'legacy-baseline') {
        assert.equal(skills.filter(s => s.filePath.startsWith(baseline + path.sep)).length, 0,
          'Baseline assumption wrong: singular .agent already discovered by default');
      }
    }
    assert(!local.some(s => s.filePath.includes('agent-archive')), 'Archived skills became active');
    results.push({ label, trusted, canonical_names: localNames,
      root_context_loaded: rootContexts.length === 1,
      relevant_diagnostics: diagnostics.filter(d => d.path?.startsWith(canonicalBase)) });
  }
  console.log(JSON.stringify({ passed: true, loader: 'installed Pi DefaultResourceLoader', results }, null, 2));
} finally {
  fs.rmSync(temp, { recursive: true, force: true });
}
