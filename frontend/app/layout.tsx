import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Pantry-Native Vegan Finder",
  description:
    "Upload a restaurant menu and uncover the vegan-friendly dishes a kitchen can likely make from ingredients already on the menu.",
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
