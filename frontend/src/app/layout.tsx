import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import { QueryProvider } from "@/providers/query-provider";
import { ThemeProvider } from "@/providers/theme-provider";
import { Toaster } from "react-hot-toast";
import TopNavClient from "@/components/TopNavClient";
import AppSidebar from "@/components/AppSidebar";

const inter = Inter({ 
  subsets: ["latin"],
  variable: "--font-inter",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
});

export const metadata: Metadata = {
  title: "Forge1 - AI Employee Builder & Deployment Platform",
  description: "Deploy, monitor, and evolve your AI workforce with Forge1",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const envLabel = process.env.NEXT_PUBLIC_ENV_LABEL || "";
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} ${jetbrainsMono.variable} font-sans antialiased`}>
        <ThemeProvider>
          <QueryProvider>
            <AuthProvider>
              {envLabel && (
                <div className="w-full text-center text-xs py-1 bg-warning text-black">{envLabel}</div>
              )}
              <TopNavClient />
              <div className="max-w-screen-2xl mx-auto p-4">
                <div className="grid grid-cols-1 md:grid-cols-[240px_minmax(0,1fr)] gap-4">
                  <div className="md:h-[calc(100dvh-70px)] sticky top-2"><AppSidebar /></div>
                  <main className="rounded-2xl bg-card border shadow-sm min-h-[60vh]">{children}</main>
                </div>
              </div>
              <Toaster
                position="top-right"
                toastOptions={{
                  duration: 4000,
                  style: {
                    background: "hsl(var(--card))",
                    color: "hsl(var(--card-foreground))",
                    border: "1px solid hsl(var(--border))",
                  },
                }}
              />
            </AuthProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}