import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { mkdir, writeFile } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import { createIcons } from './icons.mjs';

const desktop = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const root = path.dirname(desktop);
if (!['win32', 'darwin'].includes(process.platform)) throw new Error('Собирайте установщик на Windows или macOS.');
if (process.env.npm_config_arch && process.env.npm_config_arch !== process.arch) throw new Error('Архитектура сборки должна совпадать с архитектурой встроенного Python.');
const npmCLI = process.env.npm_execpath;
if (!npmCLI) throw new Error('Запустите сборку через npm run prepare:app или npm run dist.');

function run(command, args, cwd) {
  const result = spawnSync(command, args, { cwd, stdio: 'inherit', windowsHide: true });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`${command} завершился с кодом ${result.status}`);
}
const build = path.join(desktop, 'build');
await mkdir(build, { recursive: true });
await createIcons(build);
run(process.execPath, [npmCLI, 'run', 'build'], path.join(root, 'frontend'));
run('uv', [
  'run', '--frozen', '--python', '3.12', '--extra', 'desktop', '--extra', 'dev', 'python', '-m', 'PyInstaller',
  '--noconfirm', '--clean', '--onedir', '--name', 'disprot-engine',
  '--distpath', path.join(build, 'backend'), '--workpath', path.join(build, 'pyinstaller'),
  '--specpath', build,
  '--collect-submodules', 'app', '--collect-data', 'docx',
  '--hidden-import', 'uvicorn.loops.asyncio', '--hidden-import', 'uvicorn.protocols.http.h11_impl',
  '--hidden-import', 'uvicorn.lifespan.on',
  ...(process.platform === 'darwin' && process.env.DISPROT_SIGN_IDENTITY ? ['--codesign-identity', process.env.DISPROT_SIGN_IDENTITY] : []),
  'desktop_entry.py',
], path.join(root, 'backend'));
await writeFile(path.join(build, 'build-info.json'), JSON.stringify({ platform: process.platform, arch: process.arch }, null, 2));
