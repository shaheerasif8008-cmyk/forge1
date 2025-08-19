"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutGrid, Users2, Workflow, Activity, Settings } from "lucide-react";

const nav = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutGrid },
  { href: "/employees", label: "Employees", icon: Users2 },
  { href: "/operations", label: "Tasks", icon: Workflow },
  { href: "/usage", label: "Monitoring", icon: Activity },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function AppSidebar() {
  const pathname = usePathname();
  return (
    <aside className="h-full p-3">
      <div className="h-full rounded-2xl border bg-card">
        <div className="p-3 text-xs text-muted-foreground">Navigation</div>
        <nav className="px-2 pb-3 space-y-1">
          {nav.map((item) => {
            const Icon = item.icon;
            const active = pathname?.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-2 px-3 py-2 rounded-xl text-sm hover:bg-accent hover:text-foreground ${
                  active ? "bg-accent text-foreground" : "text-muted-foreground"
                }`}
              >
                <Icon size={16} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </aside>
  );
}


