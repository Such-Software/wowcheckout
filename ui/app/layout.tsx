import type { Metadata } from "next";
import { Crimson_Pro, Space_Grotesk } from "next/font/google";
import "./globals.css";
import { UmamiAnalytics } from "../components/UmamiAnalytics";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-sans",
});

const crimsonPro = Crimson_Pro({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-serif",
});

export const metadata: Metadata = {
  title: {
    default: "WOW Checkout | Home",
    template: "WOW Checkout | %s",
  },
  description: "Non-custodial Wownero checkout with view-only detection.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${spaceGrotesk.variable} ${crimsonPro.variable}`}>
      <body>
        <UmamiAnalytics />
        {children}
      </body>
    </html>
  );
}
