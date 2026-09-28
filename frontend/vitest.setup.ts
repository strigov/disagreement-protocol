import "@testing-library/jest-dom";
import { File as NodeFile } from "node:buffer";
import { server } from "./src/mocks/server";

// Node 25+ also exposes localStorage, but it is unavailable without a file.
// Use the actual jsdom storage so browser persistence tests remain isolated.
declare const jsdom: { window: Window };
Object.defineProperty(globalThis, "localStorage", {
  configurable: true,
  value: jsdom.window.localStorage,
});

// Node's fetch (undici) does not recognise jsdom's FormData/File and
// serialises multipart bodies as plain text, so upload tests break.
// jsdom has no fetch of its own, so recover undici's FormData class via
// Response.formData() and expose the native classes globally.
const nativeFormDataClass = await (async () => {
  const res = new Response(
    '--b\r\nContent-Disposition: form-data; name="x"\r\n\r\n1\r\n--b--\r\n',
    { headers: { "content-type": "multipart/form-data; boundary=b" } },
  );
  const fd = await res.formData();
  return fd.constructor as typeof FormData;
})();
globalThis.FormData = nativeFormDataClass;
globalThis.File = NodeFile as unknown as typeof File;

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
