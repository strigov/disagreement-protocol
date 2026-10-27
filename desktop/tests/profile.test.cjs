const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = readFileSync(path.join(__dirname, '../src/main.cjs'), 'utf8');

for (const override of [undefined, 'isolated-profile']) {
  test(`branding preserves ${override ? 'the explicit profile override' : 'the existing user profile'}`, () => {
    const appData = path.resolve('test-app-data');
    const paths = {};
    const app = {
      setName(name) { this.name = name; },
      getPath(key) { assert.equal(key, 'appData'); return appData; },
      setPath(key, value) { paths[key] = value; },
      requestSingleInstanceLock() { return false; },
      quit() {},
    };
    vm.runInNewContext(source, {
      process: { env: { DISPROT_USER_DATA: override } },
      require(name) {
        if (name === 'electron') return { app, protocol: { registerSchemesAsPrivileged() {} } };
        if (name.startsWith('./')) return {};
        return require(name);
      },
    });
    assert.equal(app.name, 'Strigov — Протокол разногласий');
    assert.equal(paths.userData, override
      ? path.resolve(override)
      : path.join(appData, 'DisagreementProtocol'));
  });
}
