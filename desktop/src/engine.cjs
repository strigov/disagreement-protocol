const { spawn } = require('node:child_process');
const { createInterface } = require('node:readline');
const { randomBytes } = require('node:crypto');
const { setTimeout: delay } = require('node:timers/promises');

class Engine {
  constructor(executable, dataDir) {
    this.executable = executable;
    this.dataDir = dataDir;
    this.token = randomBytes(32).toString('hex');
    this.child = null;
    this.stopping = false;
  }

  async start() {
    const child = this.child = spawn(this.executable, ['--data-dir', this.dataDir], {
      env: { ...process.env, DISPROT_DESKTOP_TOKEN: this.token, PYTHONUTF8: '1' },
      windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'], cwd: this.dataDir,
    });
    this.exited = new Promise((resolve) => child.once('close', resolve));
    child.stdin.on('error', () => {});
    // Drain output without logging contract content or local file paths.
    child.stderr.resume();
    const lines = createInterface({ input: child.stdout });
    try {
      const port = await new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error('Движок не запустился за 60 секунд.')), 60_000);
        const finish = (error, value) => { clearTimeout(timer); error ? reject(error) : resolve(value); };
        child.once('error', () => finish(new Error('Не удалось запустить встроенный движок.')));
        child.once('exit', () => finish(new Error('Встроенный движок завершился при запуске.')));
        lines.on('line', (line) => {
          if (!line.startsWith('DISPROT_READY=')) return;
          try {
            const { port } = JSON.parse(line.slice('DISPROT_READY='.length));
            if (Number.isInteger(port) && port > 0 && port < 65536) finish(null, port);
          } catch { /* Non-protocol output is ignored. */ }
        });
      });
      this.url = `http://127.0.0.1:${port}`;
      const deadline = Date.now() + 30_000;
      while (Date.now() < deadline) {
        if (this.stopping || child.exitCode !== null || child.signalCode !== null) throw new Error('Движок завершился при запуске.');
        try {
          const response = await fetch(`${this.url}/health`, {
            headers: { 'x-disprot-token': this.token }, signal: AbortSignal.timeout(1000),
          });
          if (response.ok && (await response.json()).status === 'ok') return;
        } catch { /* The socket can become ready before database startup completes. */ }
        await delay(100);
      }
      throw new Error('Не удалось дождаться готовности движка.');
    } catch (error) { await this.stop(); throw error; }
  }

  async stop() {
    if (!this.child) return;
    if (this.stopping) return this.exited;
    this.stopping = true;
    const child = this.child;
    if (!child.pid || child.exitCode !== null || child.signalCode !== null) return;
    child.stdin.end('shutdown\n');
    let timer;
    await Promise.race([
      this.exited,
      new Promise((resolve) => { timer = setTimeout(() => { child.kill(); resolve(); }, 8000); }),
    ]);
    clearTimeout(timer);
  }
}

module.exports = { Engine };
