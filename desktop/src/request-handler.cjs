const path = require('node:path');
const { readFile } = require('node:fs/promises');

const APP_ORIGIN = 'disprot://app';
const CSP = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'";
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.svg': 'image/svg+xml', '.png': 'image/png', '.woff2': 'font/woff2' };

function isAppURL(value) {
  try {
    const url = new URL(value);
    return url.protocol === 'disprot:' && url.host === 'app' && !url.username && !url.password;
  } catch { return false; }
}

function assetPath(rawUrl) {
  if (!isAppURL(rawUrl)) return null;
  let pathname;
  try { pathname = decodeURIComponent(new URL(rawUrl).pathname); } catch { return null; }
  if (pathname.includes('\\') || pathname.includes('\0') || pathname.split('/').includes('..')) return null;
  if (pathname === '/' || /^\/documents\/[a-zA-Z0-9-]+\/(analysis|parties|protocol|export)\/?$/.test(pathname)) return 'index.html';
  if (/^\/fonts\/[a-zA-Z0-9_.-]+\.woff2$/.test(pathname)) return pathname.slice(1);
  if (/^\/assets\/[a-zA-Z0-9_.-]+$/.test(pathname)) return pathname.slice(1);
  return null;
}

function createRequestHandler({ uiDir, backendURL, token, fetchBackend = fetch }) {
  return async (request) => {
    if (!isAppURL(request.url) || (request.initiatorOrigin && request.initiatorOrigin !== APP_ORIGIN)) {
      return new Response('Forbidden', { status: 403 });
    }
    const url = new URL(request.url);
    if (url.pathname.startsWith('/api/')) {
      // Forward only application headers. The credential never reaches renderer code.
      const headers = new Headers({ 'x-disprot-token': token, origin: APP_ORIGIN });
      const contentType = request.headers.get('content-type');
      if (contentType) headers.set('content-type', contentType);
      try {
        const response = await fetchBackend(backendURL + url.pathname + url.search, {
          method: request.method, headers,
          body: ['GET', 'HEAD'].includes(request.method) ? undefined : request.body,
          duplex: 'half', redirect: 'error', signal: request.signal,
        });
        const responseHeaders = new Headers(response.headers);
        responseHeaders.set('cache-control', 'no-store');
        return new Response(response.body, { status: response.status, headers: responseHeaders });
      } catch {
        return Response.json({ detail: 'Движок недоступен. Перезапустите приложение.' }, { status: 503 });
      }
    }
    if (!['GET', 'HEAD'].includes(request.method)) return new Response('', { status: 405 });
    const file = assetPath(request.url);
    if (!file) return new Response('Not found', { status: 404 });
    try {
      const content = await readFile(path.join(uiDir, file));
      return new Response(request.method === 'HEAD' ? null : content, {
        headers: {
          'content-type': TYPES[path.extname(file)] || 'application/octet-stream',
          'content-security-policy': CSP,
          'x-content-type-options': 'nosniff',
          'cache-control': 'no-store',
        },
      });
    } catch { return new Response('Not found', { status: 404 }); }
  };
}

module.exports = { APP_ORIGIN, isAppURL, assetPath, createRequestHandler };
