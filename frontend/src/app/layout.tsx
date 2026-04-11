import type { Metadata } from "next";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "Diretto — Cerca lavoro senza intermediari",
  description:
    "Piattaforma di ricerca lavoro privacy-first. Solo annunci diretti da aziende reali. Zero agenzie, zero tracciamento. AGPL-3.0.",
  keywords: ["lavoro", "offerte lavoro", "privacy", "open source", "no agenzie"],
  openGraph: {
    title: "Diretto",
    description: "Cerca lavoro senza intermediari. Privacy-first, open source.",
    url: "https://diretto.org",
    siteName: "Diretto",
    locale: "it_IT",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="it">
      <body>{children}</body>
    </html>
  );
}
