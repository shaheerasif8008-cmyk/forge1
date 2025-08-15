import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { AppProviders } from "@/providers/AppProviders";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";

const fontSans = Inter({ variable: "--font-geist-sans", subsets: ["latin"] });
const fontMono = JetBrains_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Forge1 Client Portal",
  description: "Operations portal for Forge1",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const envLabel = process.env.NEXT_PUBLIC_ENV_LABEL;
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${fontSans.variable} ${fontMono.variable} antialiased`}>
        <AppProviders>
          <div className="flex min-h-screen w-full">
            <Sidebar />
            <main className="flex-1">
              <Topbar envLabel={envLabel} />
              <div className="p-4">{children}</div>
            </main>
          </div>
        </AppProviders>
      </body>
    </html>
  );
}
