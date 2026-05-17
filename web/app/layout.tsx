import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Next Radio 24/7",
  description: "AI-generated 24/7 radio — fresh content every day",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}
