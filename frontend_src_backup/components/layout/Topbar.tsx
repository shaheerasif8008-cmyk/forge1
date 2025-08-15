"use client";

import { useTheme } from "next-themes";
import { Sun, Moon, ChevronDown, User2 } from "lucide-react";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

type TopbarProps = {
  envLabel?: string;
};

export function Topbar({ envLabel }: TopbarProps) {
  const { theme, setTheme } = useTheme();
  const [tenant] = useState("Default Tenant");
  const buildInfo = useMemo(() => (typeof window !== "undefined" ? window.__BUILD_INFO : undefined), []);

  return (
    <div className="sticky top-0 z-30 flex h-14 items-center justify-between border-b bg-background px-4">
      <div className="flex items-center gap-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="gap-2">
              {tenant}
              <ChevronDown className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start">
            <DropdownMenuLabel>Switch tenant</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>Default Tenant</DropdownMenuItem>
            <DropdownMenuItem>Beta Tenant</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        <div className="flex items-center gap-2">
          {envLabel ? (
            <span className="rounded-md bg-secondary px-2 py-1 text-xs text-secondary-foreground shadow-card">
              {envLabel}
            </span>
          ) : null}
          {buildInfo?.sha ? (
            <span className="rounded-md bg-muted px-2 py-1 text-[10px] text-muted-foreground">
              {buildInfo.sha.slice(0, 7)}
            </span>
          ) : null}
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          aria-label="Toggle theme"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        >
          <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="gap-2">
              <User2 className="h-4 w-4" />
              User
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>Account</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>Profile</DropdownMenuItem>
            <DropdownMenuItem>Settings</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem>Logout</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}


