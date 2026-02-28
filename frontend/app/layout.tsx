import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "AI Checklist Agent",
  description: "Голосовой агент для заполнения чеклиста созвона"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body className="noise">
        {children}
      </body>
    </html>
  );
}
