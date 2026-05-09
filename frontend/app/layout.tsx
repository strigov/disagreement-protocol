import "./globals.css";
import type { ReactNode } from "react";

export const metadata = { title: "Протокол разногласий" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ru">
      <body className="min-h-screen bg-gray-50 text-gray-900">{children}</body>
    </html>
  );
}
