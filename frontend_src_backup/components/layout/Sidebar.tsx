import Link from "next/link";
import { Home, Settings, LineChart, Wrench, Users, Store, Workflow, KeySquare, CreditCard, Logs, Sparkles } from "lucide-react";

const nav = [
  { href: "/dashboard", label: "Dashboard", icon: Home },
  { href: "/employees", label: "Employees", icon: Users },
  { href: "/builder", label: "Builder", icon: Sparkles },
  { href: "/marketplace", label: "Marketplace", icon: Store },
  { href: "/workflows", label: "Workflows", icon: Workflow },
  { href: "/metrics", label: "Metrics", icon: LineChart },
  { href: "/logs", label: "Logs", icon: Logs },
  { href: "/keys", label: "Keys", icon: KeySquare },
  { href: "/billing", label: "Billing", icon: CreditCard },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  return (
    <aside className="hidden w-56 shrink-0 border-r bg-background p-4 md:block">
      <div className="mb-4 font-semibold">Forge1 Portal</div>
      <nav className="space-y-1">
        {nav.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="flex items-center gap-2 rounded-md px-2 py-2 text-sm hover:bg-muted"
          >
            <item.icon className="h-4 w-4" /> {item.label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}


