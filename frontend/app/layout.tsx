import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Pantry-Native Vegan Menu Engine",
  description:
    "Upload a restaurant menu and generate all viable vegan dishes the kitchen can already make from its current pantry.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
