"use client";

import { MainNav } from "./main-nav";
import { ProtectedRoute } from "./protected-route";

interface AuthenticatedLayoutProps {
  children: React.ReactNode;
}

export function AuthenticatedLayout({ children }: AuthenticatedLayoutProps) {
  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-background">
        <MainNav />
        <main className="container mx-auto px-4 py-6">
          {children}
        </main>
      </div>
    </ProtectedRoute>
  );
}