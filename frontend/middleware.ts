import { NextResponse, type NextRequest } from "next/server";

const uiPort = process.env.DISPROT_UI_PORT || "3000";
const allowedOrigins = [`http://localhost:${uiPort}`, `http://127.0.0.1:${uiPort}`];

// Loopback binding alone does not prevent requests from an unrelated website.
export function middleware(request: NextRequest) {
  const host = request.headers.get("host");
  let hostname = "";
  try { hostname = new URL(`http://${host}`).hostname; } catch { /* rejected below */ }
  if (!["localhost", "127.0.0.1", "[::1]"].includes(hostname)) {
    return NextResponse.json({ detail: "Приложение доступно только локально" }, { status: 400 });
  }
  const origin = request.headers.get("origin");
  if ((origin && !allowedOrigins.includes(origin)) ||
      request.headers.get("sec-fetch-site") === "cross-site") {
    return NextResponse.json({ detail: "Запрос с постороннего сайта запрещён" }, { status: 403 });
  }
  if (request.nextUrl.pathname.startsWith("/api/")) {
    const length = request.headers.get("content-length");
    const limit = request.nextUrl.pathname.replace(/\/$/, "") === "/api/documents" ? 26 * 1024 * 1024 : 4 * 1024 * 1024;
    if (length && Number(length) > limit) {
      return NextResponse.json({ detail: "Размер запроса превышает допустимый лимит" }, { status: 413 });
    }
  }
  return NextResponse.next();
}

export const config = { matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"] };
