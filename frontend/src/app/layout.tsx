import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Stock Predictor",
  description: "ML-Powered Japanese Equity Forecast",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ja">
      <body>{children}</body>
    </html>
  );
}
