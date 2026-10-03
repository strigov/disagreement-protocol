const { readFile } = require('node:fs/promises');
const path = require('node:path');
const { Arch } = require('builder-util');
const { execFileSync } = require('node:child_process');
const { access } = require('node:fs/promises');

module.exports = async (context) => {
  const info = JSON.parse(await readFile(path.join(__dirname, '..', 'build', 'build-info.json'), 'utf8'));
  if (info.platform !== context.electronPlatformName || info.arch !== Arch[context.arch]) {
    throw new Error('Встроенный движок собран для другой ОС/архитектуры. Соберите приложение на целевой платформе.');
  }
  if (context.electronPlatformName === 'darwin') {
    // electron-builder 26 writes NFC CFBundleName but NFD helper names for "й".
    // Electron resolves helpers using CFBundleName. Keep them byte-identical.
    // Upstream fix (v27): https://github.com/electron-userland/electron-builder/pull/9962
    const name = context.packager.appInfo.productFilename;
    const contents = path.join(context.appOutDir, `${name}.app`, 'Contents');
    await access(path.join(contents, 'Frameworks', `${name} Helper.app`));
    execFileSync('/usr/bin/plutil', ['-replace', 'CFBundleName', '-string', name, path.join(contents, 'Info.plist')]);
  }
};
