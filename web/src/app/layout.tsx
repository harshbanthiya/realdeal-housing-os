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
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"),
  openGraph: {
    siteName: "Real Deal Housing",
    type: "website",
    locale: "en_IN",
    images: [
      {
        url: "https://static.wixstatic.com/media/77ab1a_d965c181dcb1416f823e2738604950c1~mv2.jpg",
        alt: "The view over Goregaon West from Ekta Tripolis",
      },
    ],
  },
  title: {
    default: "Real Deal Housing — Flats in Goregaon West & Andheri West",
    template: "%s — Real Deal Housing",
  },
  description:
    "2, 3 & 4 BHK flats for sale and rent in Ekta Tripolis, Imperial Heights and Kalpataru Radiance, Goregaon West, plus the DLF Westpark launch in Andheri West. 15 years of building-by-building expertise, every fact verified.",
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
