const { app, BrowserWindow, dialog, Menu, protocol, session, shell } = require('electron');
const path = require('node:path');
const { mkdir } = require('node:fs/promises');
const { Engine } = require('./engine.cjs');
const { APP_ORIGIN, isAppURL, createRequestHandler } = require('./request-handler.cjs');

app.setName('Strigov — Протокол разногласий');
// Keep existing documents and renderer storage when the visible product name changes.
// Tests and developer runs can still use an isolated profile.
app.setPath('userData', process.env.DISPROT_USER_DATA
  ? path.resolve(process.env.DISPROT_USER_DATA)
  : path.join(app.getPath('appData'), 'DisagreementProtocol'));
protocol.registerSchemesAsPrivileged([{ scheme: 'disprot', privileges: {
  standard: true, secure: true, supportFetchAPI: true, corsEnabled: true,
} }]);

let window;
let engine;
let stopping = false;
let exitReady = false;
const ownsInstance = app.requestSingleInstanceLock();
if (!ownsInstance) app.quit();
else {
  app.on('second-instance', () => {
    if (window) { if (window.isMinimized()) window.restore(); window.show(); window.focus(); }
  });
  app.on('window-all-closed', () => app.quit());
  app.on('before-quit', (event) => {
    if (exitReady) return;
    event.preventDefault();
    // Let the existing beforeunload guard protect unsaved edits first.
    if (window && !window.isDestroyed()) { window.close(); return; }
    if (stopping) return;
    stopping = true;
    Promise.resolve(engine?.stop()).finally(() => { exitReady = true; app.quit(); });
  });

  app.whenReady().then(async () => {
    const resources = app.isPackaged ? process.resourcesPath : path.join(__dirname, '..', 'build');
    const engineDir = app.isPackaged ? path.join(resources, 'engine') : path.join(resources, 'backend', 'disprot-engine');
    const dataDir = path.join(app.getPath('userData'), 'data');
    await mkdir(dataDir, { recursive: true });
    engine = new Engine(path.join(engineDir, process.platform === 'win32' ? 'disprot-engine.exe' : 'disprot-engine'), dataDir);
    await engine.start();
    if (stopping) return;
    protocol.handle('disprot', createRequestHandler({
      uiDir: path.join(resources, 'ui'), backendURL: engine.url, token: engine.token,
    }));
    session.defaultSession.setPermissionRequestHandler((_contents, _permission, callback) => callback(false));
    session.defaultSession.setPermissionCheckHandler(() => false);
    // Keep the renderer offline. Only main-process API forwarding reaches loopback.
    session.defaultSession.webRequest.onBeforeRequest({ urls: ['http://*/*', 'https://*/*', 'ws://*/*', 'wss://*/*'] }, (_details, callback) => callback({ cancel: true }));
    window = new BrowserWindow({
      width: 1320, height: 900, minWidth: 800, minHeight: 600,
      title: 'Strigov — Протокол разногласий', backgroundColor: '#f7f8fc', show: false,
      webPreferences: { nodeIntegration: false, contextIsolation: true, sandbox: true, webviewTag: false, spellcheck: false },
    });
    window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
    window.webContents.on('will-navigate', (event, url) => { if (!isAppURL(url)) event.preventDefault(); });
    window.webContents.on('will-prevent-unload', (event) => {
      const choice = dialog.showMessageBoxSync(window, {
        type: 'warning', title: 'Несохранённые изменения',
        message: 'Есть несохранённые изменения.', detail: 'Вернитесь к протоколу, чтобы сохранить их.',
        buttons: ['Продолжить работу', 'Закрыть без сохранения'], defaultId: 0, cancelId: 0,
      });
      if (choice === 1) event.preventDefault();
    });
    session.defaultSession.on('will-download', (event, item) => {
      if (!item.getURL().startsWith(`blob:${APP_ORIGIN}/`) && !isAppURL(item.getURL())) { event.preventDefault(); return; }
      item.setSaveDialogOptions({ title: 'Сохранить протокол', defaultPath: path.join(app.getPath('documents'), path.basename(item.getFilename())), filters: [{ name: 'Документ Word', extensions: ['docx'] }] });
      item.once('done', (_event, state) => {
        if (state === 'interrupted') dialog.showErrorBox('Не удалось сохранить файл', 'Повторите экспорт и выберите доступную папку.');
      });
    });
    const about = () => dialog.showMessageBox(window, {
      type: 'info', title: 'О приложении', message: 'Strigov — Протокол разногласий',
      detail: `Версия ${app.getVersion()}`,
    });
    Menu.setApplicationMenu(Menu.buildFromTemplate([
      ...(process.platform === 'darwin' ? [{ label: 'Strigov', submenu: [{ label: 'О приложении', click: about }, { type: 'separator' }, { role: 'hide', label: 'Скрыть Strigov' }, { role: 'hideOthers' }, { type: 'separator' }, { role: 'quit', label: 'Завершить' }] }] : []),
      { label: 'Файл', submenu: [{ label: 'Открыть папку данных', click: () => shell.openPath(dataDir) }, { type: 'separator' }, { role: 'close', label: 'Закрыть' }] },
      { label: 'Правка', submenu: [{ role: 'undo', label: 'Отменить' }, { role: 'redo', label: 'Повторить' }, { type: 'separator' }, { role: 'cut', label: 'Вырезать' }, { role: 'copy', label: 'Копировать' }, { role: 'paste', label: 'Вставить' }, { role: 'selectAll', label: 'Выделить всё' }] },
      { label: 'Вид', submenu: [{ role: 'resetZoom', label: 'Исходный масштаб' }, { role: 'zoomIn', label: 'Увеличить' }, { role: 'zoomOut', label: 'Уменьшить' }] },
      { label: 'Помощь', submenu: [{ label: 'О приложении', click: about }] },
    ]));
    engine.child.once('exit', () => {
      if (!engine.stopping && !stopping) dialog.showErrorBox('Обработка документов остановилась', 'Перезапустите приложение, чтобы продолжить работу. Сохранённые изменения не потеряны.');
    });
    window.once('ready-to-show', () => window.show());
    window.on('closed', () => { window = null; });
    await window.loadURL(`${APP_ORIGIN}/`);
  }).catch(async () => {
    if (!stopping) dialog.showErrorBox('Не удалось открыть приложение', 'Не удалось запустить обработку документов. Перезапустите приложение. Если ошибка повторится, переустановите его. Сохранённые документы не удаляются.');
    await engine?.stop();
    exitReady = true;
    app.quit();
  });
}
