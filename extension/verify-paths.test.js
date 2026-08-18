// extension/verify-paths.test.js
//
// Static smoke test recommended by the final-review-fix report: confirms
// every file path the extension references (manifest content_scripts /
// web_accessible_resources, plus any chrome.runtime.getURL('...') literal
// in the extension's own JS) actually exists on disk. This would have caught
// C2 (content-script.js importing a path that only resolves against the
// extension's own files, not the page) before it shipped.
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

const EXT_DIR = path.dirname(new URL(import.meta.url).pathname);
const manifest = JSON.parse(fs.readFileSync(path.join(EXT_DIR, 'manifest.json'), 'utf8'));

function resolveExisting(relPath) {
  // web_accessible_resources entries may contain globs like "vendor/fonts/*";
  // for glob entries, just confirm the parent directory exists and is non-empty.
  if (relPath.includes('*')) {
    const dir = path.join(EXT_DIR, path.dirname(relPath));
    return fs.existsSync(dir) && fs.readdirSync(dir).length > 0;
  }
  return fs.existsSync(path.join(EXT_DIR, relPath));
}

describe('manifest.json path references', () => {
  it('every content_scripts js/css file exists on disk', () => {
    for (const entry of manifest.content_scripts) {
      for (const jsPath of entry.js ?? []) {
        expect(resolveExisting(jsPath), `missing content_scripts.js: ${jsPath}`).toBe(true);
      }
      for (const cssPath of entry.css ?? []) {
        expect(resolveExisting(cssPath), `missing content_scripts.css: ${cssPath}`).toBe(true);
      }
    }
  });

  it('every web_accessible_resources file exists on disk', () => {
    for (const entry of manifest.web_accessible_resources) {
      for (const resource of entry.resources) {
        expect(resolveExisting(resource), `missing web_accessible_resource: ${resource}`).toBe(true);
      }
    }
  });

  it('background.service_worker file exists on disk', () => {
    const swPath = manifest.background?.service_worker;
    expect(swPath, 'manifest has no background.service_worker').toBeTruthy();
    expect(resolveExisting(swPath), `missing background.service_worker: ${swPath}`).toBe(true);
  });

  it('every icons.* file exists on disk', () => {
    for (const [size, iconPath] of Object.entries(manifest.icons ?? {})) {
      expect(resolveExisting(iconPath), `missing icons.${size}: ${iconPath}`).toBe(true);
    }
  });

  it('every action.default_icon.* file exists on disk', () => {
    for (const [size, iconPath] of Object.entries(manifest.action?.default_icon ?? {})) {
      expect(resolveExisting(iconPath), `missing action.default_icon.${size}: ${iconPath}`).toBe(true);
    }
  });
});

describe('chrome.runtime.getURL(...) references in extension JS', () => {
  const jsFiles = ['content-script.js', 'panel.js'];

  for (const file of jsFiles) {
    it(`every chrome.runtime.getURL(...) literal in ${file} resolves to a real file`, () => {
      const src = fs.readFileSync(path.join(EXT_DIR, file), 'utf8');
      const matches = [...src.matchAll(/chrome\.runtime\.getURL\(\s*['"]([^'"]+)['"]\s*\)/g)];
      // Sanity check: this test is only meaningful if it actually finds calls
      // to inspect. content-script.js must have at least one (the C2 fix).
      if (file === 'content-script.js') {
        expect(matches.length).toBeGreaterThan(0);
      }
      for (const [, refPath] of matches) {
        expect(resolveExisting(refPath), `missing file referenced by getURL: ${refPath}`).toBe(true);
      }
    });
  }
});
