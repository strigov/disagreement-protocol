import "./globals.css";
import type { ReactNode } from "react";

export const metadata = { title: "Протокол разногласий" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ru">
      <body><a className="skip-link" href="#main-content">К содержимому</a>{children}</body>
    </html>
  );
}
