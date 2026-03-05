import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Bush League Co-Pilot",
  description: "Fantasy baseball advisor for the Bush League",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        <header className="bg-navy-dark text-white">
          <div className="max-w-[1440px] mx-auto flex items-center justify-between px-4 h-12">
            <div className="flex items-center gap-3">
              <div className="w-7 h-7 rounded-full bg-mlb-red flex items-center justify-center text-[10px] font-black tracking-tight">
                BL
              </div>
              <span className="text-sm font-bold tracking-wide uppercase">
                Bush League Co-Pilot
              </span>
            </div>
            <div className="flex items-center gap-4 text-xs text-white/60">
              <span>2026 Season</span>
              <span className="w-1.5 h-1.5 rounded-full bg-mlb-green inline-block" />
              <span className="text-white/80">Synthetic Mode</span>
            </div>
          </div>
        </header>
        {children}
      </body>
    </html>
  );
}
