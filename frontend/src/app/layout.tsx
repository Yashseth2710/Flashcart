import type { Metadata } from "next";
import { JetBrains_Mono, Karla, La_Belle_Aurore, Playfair_Display } from "next/font/google";

import { QueryProvider } from "@/providers/query-provider";

import "./globals.css";

const playfair = Playfair_Display({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-playfair",
});

const karla = Karla({
  subsets: ["latin"],
  weight: ["300", "400", "500"],
  variable: "--font-karla",
});

const belleAurore = La_Belle_Aurore({
  subsets: ["latin"],
  weight: "400",
  variable: "--font-belle",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "FlashCart",
  description: "Buy before it's gone. Built to handle the rush.",
};

const fontVariables = [
  playfair.variable,
  karla.variable,
  belleAurore.variable,
  jetbrainsMono.variable,
].join(" ");

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={fontVariables}>
      <body>
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
