import "./globals.css";
import type { ReactNode } from "react";
import { THEME_INIT_SCRIPT } from "@/lib/theme";

export const metadata = { title: "Протокол разногласий" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    // data-theme уточняет inline-скрипт до первой отрисовки, поэтому атрибуты
    // на сервере и клиенте могут расходиться — это ожидаемо.
    <html lang="ru" data-concept="buro" data-theme="light" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body><a className="skip-link" href="#main-content">К содержимому</a>{children}</body>
    </html>
  );
}
