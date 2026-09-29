const { test } = require('node:test');
const assert = require('node:assert/strict');
const { mkdtemp, mkdir, writeFile, rm } = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const { createRequestHandler } = require('../src/request-handler.cjs');

test('static routing serves deep links and assets, rejects unrelated files and origins', async (t) => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'disprot-ui-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  await mkdir(path.join(root, 'assets'));
  await writeFile(path.join(root, 'index.html'), '<h1>App</h1>');
  await writeFile(path.join(root, 'assets', 'app.js'), '/* app */');
  const handle = createRequestHandler({ uiDir: root, backendURL: 'http://127.0.0.1:1', token: 'secret' });
  for (const route of ['/', '/documents/123-abc/protocol', '/documents/123-abc/parties']) {
    const response = await handle(new Request(`disprot://app${route}`));
    assert.equal(await response.text(), '<h1>App</h1>');
    assert.match(response.headers.get('content-security-policy'), /connect-src 'self'/);
  }
  assert.match((await handle(new Request('disprot://app/assets/app.js'))).headers.get('content-type'), /javascript/);
  for (const route of ['/package.json', '/assets/%2e%2e%2findex.html', '/assets/%5cindex.html', '/unknown']) {
    assert.equal((await handle(new Request(`disprot://app${route}`))).status, 404);
  }
  assert.equal((await handle(new Request('disprot://other/'))).status, 403);
  const foreign = new Request('disprot://app/api/documents');
  foreign.initiatorOrigin = 'https://example.com';
  assert.equal((await handle(foreign)).status, 403);
  assert.equal((await handle(new Request('disprot://app/', { method: 'POST' }))).status, 405);
});

test('API proxy streams uploads, owns authentication and preserves responses', async () => {
  const bytes = new Uint8Array([0, 255, 31, 65]);
  const handle = createRequestHandler({
    uiDir: '', backendURL: 'http://127.0.0.1:12345', token: 'private-session',
    fetchBackend: async (url, options) => {
      assert.equal(url, 'http://127.0.0.1:12345/api/documents?test=1');
      assert.equal(options.headers.get('x-disprot-token'), 'private-session');
      assert.equal(options.headers.get('origin'), 'disprot://app');
      assert.equal(options.headers.get('cookie'), null);
      assert.equal(options.headers.get('content-type'), 'application/octet-stream');
      assert.equal(options.redirect, 'error');
      assert.deepEqual(new Uint8Array(await new Response(options.body).arrayBuffer()), bytes);
      return Response.json({ id: 'new-document' }, { status: 201 });
    },
  });
  const response = await handle(new Request('disprot://app/api/documents?test=1', {
    method: 'POST', body: bytes,
    headers: { 'content-type': 'application/octet-stream', cookie: 'untrusted', 'x-disprot-token': 'untrusted' },
  }));
  assert.equal(response.status, 201);
  assert.equal(response.headers.get('cache-control'), 'no-store');
  assert.equal(response.headers.has('x-disprot-token'), false);
  assert.deepEqual(await response.json(), { id: 'new-document' });
});

test('API reports a stopped engine and supports empty DELETE responses', async () => {
  const options = { uiDir: '', backendURL: 'http://127.0.0.1:1', token: 'secret' };
  const failed = createRequestHandler({ ...options, fetchBackend: async () => { throw new Error('offline'); } });
  assert.equal((await failed(new Request('disprot://app/api/documents'))).status, 503);
  const empty = createRequestHandler({ ...options, fetchBackend: async () => new Response(null, { status: 204 }) });
  assert.equal((await empty(new Request('disprot://app/api/protocols/1/rows/2', { method: 'DELETE' }))).status, 204);
});
