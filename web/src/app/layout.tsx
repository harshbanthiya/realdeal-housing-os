import type { Metadata } from "next";
import { Montserrat, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

const montserrat = Montserrat({
  variable: "--font-manrope",
  subsets: ["latin"],
  display: "swap",
});

const mono = IBM_Plex_Mono({
  variable: "--font-mono-token",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Real Deal Housing — Premium Mumbai Residences",
    template: "%s — Real Deal Housing",
  },
  description:
    "Real Deal Housing — a calmer, verification-first way to evaluate premium Mumbai residences.",
  robots: { index: false, follow: false }, // remove when domain goes live
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${montserrat.variable} ${mono.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-white text-ink">{children}</body>
    </html>
  );
}
