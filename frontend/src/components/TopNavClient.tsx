"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { Moon, Sun } from "lucide-react";
import { useThemeToggle } from "@/providers/theme-provider";

export default function TopNavClient() {
  const { isAuthenticated, logout } = useAuth();
  const { theme, toggle } = useThemeToggle();
  return (
    <div className="w-full border-b bg-card">
      <div className="max-w-screen-2xl mx-auto flex items-center justify-between px-4 h-12">
        <div className="flex items-center gap-4 text-sm">
          <Link href="/dashboard" className="font-semibold">Forge1</Link>
          <Link href="/employees" className="text-muted-foreground hover:text-foreground">Employees</Link>
          <Link href="/operations" className="text-muted-foreground hover:text-foreground">Operations</Link>
          <Link href="/usage" className="text-muted-foreground hover:text-foreground">Usage</Link>
        </div>
        <div className="text-sm flex items-center gap-3">
          <button aria-label="Toggle theme" onClick={toggle} className="p-1 rounded hover:bg-accent text-muted-foreground">
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
          </button>
          {isAuthenticated && (
            <button className="underline text-muted-foreground" onClick={() => logout()}>Logout</button>
          )}
        </div>
      </div>
    </div>
  );
}
