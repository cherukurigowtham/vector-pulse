import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { ErrorBoundary } from "@/components/ErrorBoundary";

const inter = Inter({ subsets: ['latin'], variable: '--font-sans', display: 'swap' });
const jetbrainsMono = JetBrains_Mono({ subsets: ['latin'], variable: '--font-mono', display: 'swap' });

export const metadata: Metadata = {
  title: "Vantix — Neural Risk Intelligence",
  description: "Global high-fidelity risk intelligence for enterprise fintech. Reduced RTO, blocked fraud, protected revenue.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="scroll-smooth">
      <body className={`antialiased bg-[var(--bg)] text-[var(--text)] transition-colors duration-300 ${inter.variable} ${jetbrainsMono.variable}`}>
        <ErrorBoundary>
          {children}
        </ErrorBoundary>
      </body>
    </html>
  );
}
