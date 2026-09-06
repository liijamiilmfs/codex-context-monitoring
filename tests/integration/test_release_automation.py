"""Opt-in checks against the Release Please library used by the pinned action.

Install release-please@17.6.0 in a temporary directory with scripts disabled and
set RELEASE_PLEASE_NODE_MODULES to that directory's node_modules before running.
No network or GitHub requests are made by these tests.
"""

import json
import os
import subprocess
from pathlib import Path

import pytest


@pytest.mark.integration
def test_release_please_updates_only_the_root_lockfile_version() -> None:
    modules = os.environ.get("RELEASE_PLEASE_NODE_MODULES")
    if not modules:
        pytest.skip(
            "Set RELEASE_PLEASE_NODE_MODULES to the temporary Node dependencies"
        )
    root = Path(__file__).parents[2]
    config = (root / "release-please-config.json").read_text(encoding="utf-8")
    result = subprocess.run(
        [
            "node",
            "-e",
            r"""
const assert = require('node:assert/strict');
const path = require('node:path');
const input = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
const config = input.config;
const library = path.join(process.argv[1], 'release-please');
assert.equal(require(path.join(library, 'package.json')).version, '17.6.0');
const {GenericToml} = require(path.join(library, 'build/src/updaters/generic-toml.js'));
const {Version} = require(path.join(library, 'build/src/version.js'));
const {DefaultVersioningStrategy} = require(path.join(library, 'build/src/versioning-strategies/default.js'));
const extra = config.packages['.']['extra-files'] ?? [];
const lock = extra.find(file => file.path === 'uv.lock');
assert.ok(lock, 'Release Please must update uv.lock in its original commit');
assert.equal(lock.type, 'toml');
const fixture = `version = 1
revision = 3
# Keep dependency versions and comments intact.
[[package]]
name = "aaa-dependency"
version = "0.2.0"
[[package]]
name = "codex-context-monitoring"
version = "0.2.0"
source = { editable = "." }
[[package]]
name = "zzz-dependency"
version = "0.2.0"
`;
const updater = new GenericToml(lock.jsonpath, Version.parse('0.3.0'));
const expected = fixture.replace('name = "codex-context-monitoring"\nversion = "0.2.0"',
                                'name = "codex-context-monitoring"\nversion = "0.3.0"');
assert.equal(updater.updateContent(fixture), expected);
assert.equal(updater.updateContent(expected), expected);
const actual = input.lock;
const actualVersion = input.version;
const nextUpdater = new GenericToml(lock.jsonpath, Version.parse('0.4.0'));
assert.equal(nextUpdater.updateContent(actual), actual.replace(
  `name = "codex-context-monitoring"\nversion = "${actualVersion}"`,
  'name = "codex-context-monitoring"\nversion = "0.4.0"'));
assert.equal(config['bump-patch-for-minor-pre-major'], false);
const strategy = new DefaultVersioningStrategy({
  bumpPatchForMinorPreMajor: config['bump-patch-for-minor-pre-major']
});
for (const [type, breaking, expectedVersion] of [
  ['feat', false, '0.3.0'], ['fix', false, '0.2.1'], ['feat', true, '1.0.0']
]) {
  assert.equal(strategy.bump(Version.parse('0.2.0'),
    [{type, breaking, notes: []}]).toString(), expectedVersion);
}
""",
            modules,
        ],
        input=json.dumps(
            {
                "config": json.loads(config),
                "lock": (root / "uv.lock").read_text(encoding="utf-8"),
                "version": json.loads(
                    (root / ".release-please-manifest.json").read_text()
                )["."],
            }
        ),
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
