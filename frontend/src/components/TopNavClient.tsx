"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";

export default function TopNavClient() {
  const { isAuthenticated, logout } = useAuth();
  return (
    <div className="w-full border-b bg-card">
      <div className="max-w-screen-2xl mx-auto flex items-center justify-between px-4 h-12">
        <div className="flex items-center gap-4 text-sm">
          <Link href="/dashboard" className="font-semibold">Forge1</Link>
          <Link href="/employees" className="text-muted-foreground hover:text-foreground">Employees</Link>
          <Link href="/operations" className="text-muted-foreground hover:text-foreground">Operations</Link>
          <Link href="/usage" className="text-muted-foreground hover:text-foreground">Usage</Link>
        </div>
        <div className="text-sm">
          {isAuthenticated && (
            <button className="underline text-muted-foreground" onClick={() => logout()}>Logout</button>
          )}
        </div>
      </div>
    </div>
  );
}